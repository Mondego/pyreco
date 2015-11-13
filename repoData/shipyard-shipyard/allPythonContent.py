__FILENAME__ = admin
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from accounts.models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserProfile, UserProfileAdmin)

########NEW FILE########
__FILENAME__ = forms
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from django.contrib.auth.models import User

class AccountForm(forms.ModelForm):
    # override the default fields to force them to be required
    # (the django User model doesn't require them)
    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table(u'accounts_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True, null=True)),
        ))
        db.send_create_signal(u'accounts', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table(u'accounts_userprofile')


    models = {
        u'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'unique': 'True', 'null': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = models
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.ForeignKey(User, null=True, unique=True)

    def __unicode__(self):
        return self.user.username

def create_profile(sender, **kwargs):
    user = kwargs.get('instance')
    if kwargs.get('created'):
        profile = UserProfile(user=user)
        profile.save()

# profile creation
post_save.connect(create_profile, sender=User)

# workaround for https://github.com/toastdriven/django-tastypie/issues/937
@receiver(post_save, sender=User)
def create_user_api_key(sender, **kwargs):
     from tastypie.models import create_api_key
     create_api_key(User, **kwargs)

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
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('accounts.views',
    url(r'^login/$', 'login', name='accounts.login'),
    url(r'^logout/$', 'logout', name='accounts.logout'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import (authenticate, login as login_user,
    logout as logout_user)
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _
from accounts.forms import AccountForm
from accounts.models import UserProfile
from datetime import datetime
import random
import string
try:
    import simplejson as json
except ImportError:
    import json

@require_http_methods(["GET", "POST"])
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login_user(request, user)
                return redirect(reverse('index'))
            else:
                messages.error(request, _('Your account is disabled.  Make sure you have activated your account.'))
        else:
            messages.error(request, _('Invalid username/password'))
    return render_to_response('accounts/login.html',
        context_instance=RequestContext(request))

@require_http_methods(["POST"])
@csrf_exempt
def api_login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    data = {}
    status = 200
    if user is not None:
        if user.is_active:
            data['status'] = 'success'
            data['email'] = user.email
            data['api_key'] = user.api_key.key
            data['username'] = username
        else:
            data['status'] = 'account is disabled'
            status = 403
    else:
        data['status'] = 'access denied'
        status = 401
    return HttpResponse(json.dumps(data), status=status)

def logout(request):
    logout_user(request)
    return redirect(reverse('index'))

@login_required
def details(request):
    ctx = {}
    form = AccountForm(instance=request.user)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.info(request, _('Account updated.'))
    ctx['form'] = form
    return render_to_response('accounts/details.html', ctx,
        context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

# Create your tests here.

########NEW FILE########
__FILENAME__ = urls
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('agent.views',
    url(r'^register/$', 'register', name='agent.register'),
    url(r'^containers/$', 'containers', name='agent.containers'),
    url(r'^images/$', 'images', name='agent.images'),
    url(r'^metrics/$', 'metrics', name='agent.metrics'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from functools import wraps
from hosts.models import Host
from containers.models import Container
from images.models import Image
from metrics.models import Metric
import json

def http_401(msg):
    return HttpResponse(msg, status=401)

def get_agent_key(request):
    auth = request.META.get('HTTP_AUTHORIZATION')
    if not auth:
        return None
    key = auth.split(':')[-1]
    return key

def agent_key_required(func):
    """
    Decorator to check for valid agent key

    Expects to have an authorization header in the following format:

        Authorization AgentKey:<key>

    """
    def f(request, *args, **kwargs):
        key = get_agent_key(request)
        try:
            host = Host.objects.get(agent_key=key)
        except Host.DoesNotExist:
            return http_401('unauthorized')
        return func(request, *args, **kwargs)
    return f

@require_http_methods(['POST'])
@csrf_exempt
def register(request):
    form = request.POST
    name = form.get('name')
    port = form.get('port')
    hostname = form.get('hostname')
    h, created = Host.objects.get_or_create(hostname=hostname)
    if created:
        h.name = name
        h.hostname = hostname
        h.enabled = None
        h.port = int(port)
        h.save()
    data = {
        'key': h.agent_key,
    }
    resp = HttpResponse(json.dumps(data), content_type='application/json')
    return resp

@csrf_exempt
@agent_key_required
def containers(request):
    key = get_agent_key(request)
    host = Host.objects.get(agent_key=key)
    host.save() # update last_updated
    if not host.enabled:
        return HttpResponse(status=403)
    container_data = json.loads(request.body)
    for d in container_data:
        if d.get('HostConfig', {}).get('PortBindings'):
            print(d)
        c = d.get('Container')
        meta = d.get('Meta')
        running = meta.get('State', {}).get('Running', False)
        container, created = Container.objects.get_or_create(host=host,
                container_id=c.get('Id'))
        if container.description == '' and meta.get('Names'):
            container.description = meta.get('Names')[0][1:]
        container.meta = json.dumps(meta)
        container.is_running = running
        container.synced = True
        container.save()
    container_ids = [x.get('Container').get('Id') for x in container_data]
    # cleanup old containers
    Container.objects.filter(host=host).exclude(protected=True).exclude(
            container_id__in=container_ids).exclude(synced=False).delete()
    return HttpResponse()

@csrf_exempt
@agent_key_required
def images(request):
    key = get_agent_key(request)
    host = Host.objects.get(agent_key=key)
    host.save() # update last_updated
    if not host.enabled:
        return HttpResponse(status=403)
    image_data = json.loads(request.body)
    for i in image_data:
        image, created = Image.objects.get_or_create(host=host,
                image_id=i.get('Id'))
        image.repository = i.get('RepoTags')[0]
        image.history = json.dumps(image_data)
        image.save()
    # cleanup old images
    image_ids = [x.get('Id') for x in image_data]
    Image.objects.filter(host=host).exclude(image_id__in=image_ids).delete()
    return HttpResponse()

@csrf_exempt
@agent_key_required
def metrics(request):
    key = get_agent_key(request)
    host = Host.objects.get(agent_key=key)
    host.save() # update last_updated
    if not host.enabled:
        return HttpResponse(status=403)
    metrics = json.loads(request.body)
    if metrics:
        for metric in metrics:
            # add counters
            for counter in metric.get('counters'):
                m = Metric()
                m.metric_type = metric.get('type')
                m.source = metric.get('container_id')
                m.counter = counter.get('name')
                m.value = counter.get('value')
                m.unit = counter.get('unit')
                m.save()
    return HttpResponse()


########NEW FILE########
__FILENAME__ = admin
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from applications.models import Application

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'domain_name', 'backend_port',
        'owner')
    search_fields = ('name', 'description', 'domain_name')
    readonly_fields = ('uuid',)

admin.site.register(Application, ApplicationAdmin)

########NEW FILE########
__FILENAME__ = api
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.bundle import Bundle
from tastypie.authorization import Authorization
from tastypie.authentication import (ApiKeyAuthentication,
    SessionAuthentication, MultiAuthentication)
from django.conf.urls import url
from applications.models import Application
from containers.api import ContainerResource

class ApplicationResource(ModelResource):
    containers = fields.ToManyField(ContainerResource, 'containers', null=True, full=True)

    class Meta:
        queryset = Application.objects.all()
        resource_name = 'applications'
        always_return_data = True
        authorization = Authorization()
        authentication = MultiAuthentication(
            ApiKeyAuthentication(), SessionAuthentication())


########NEW FILE########
__FILENAME__ = forms
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from django.utils.translation import ugettext as _
from applications.models import Application
from containers.models import Container
from hosts.models import Host
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Field
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, FormActions
from django.core.urlresolvers import reverse
from applications.models import PROTOCOL_CHOICES

def get_available_hosts():
    return Host.objects.filter(enabled=True)

class ApplicationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ApplicationForm, self).__init__(*args, **kwargs)
        # set height for container select
        container_list_length = len(Container.get_running())
        if container_list_length > 20:
            container_list_length = 20
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                None,
                'name',
                'description',
                'domain_name',
                'host_interface',
                'backend_port',
                'protocol',
                Field('containers', size=container_list_length),
            ),
            FormActions(
                Submit('save', _('Update'), css_class="btn btn-lg btn-success"),
            )
        )
        self.helper.form_id = 'form-create-application'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('applications.views.create')

    def clean(self):
        data = super(ApplicationForm, self).clean()

        if len(data.get('containers', [])) == 0:
            return data

        port = data.get('backend_port')
        interface = data.get('host_interface') or '0.0.0.0'
        for c in data.get('containers', []):
            port_proto = "{0}/tcp".format(port)
            container_ports = c.get_ports()
            if not port_proto in container_ports:
                msg = _(u'Port %s is not available on the selected containers.' % port_proto)
                self._errors['backend_port'] = self.error_class([msg])
            if not container_ports.get(port_proto, {}).get(interface):
                msg = _(u'Port %s is not bound to the interface %s on the selected containers.' % (port_proto, interface))
                self._errors['host_interface'] = self.error_class([msg])

        return data

    class Meta:
        model = Application
        fields = ('name', 'description', 'domain_name', 'host_interface', 'backend_port',
            'protocol', 'containers')

class EditApplicationForm(forms.Form):
    uuid = forms.CharField(required=True, widget=forms.HiddenInput())
    name = forms.CharField(required=True)
    description = forms.CharField(required=False)
    domain_name = forms.CharField(required=True)
    host_interface = forms.CharField(required=False)
    backend_port = forms.CharField(required=True)
    protocol = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super(EditApplicationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-edit-application'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('applications.views.edit')
        self.helper.help_text_inline = True
        self.fields['protocol'].choices = PROTOCOL_CHOICES


########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Application'
        db.create_table(u'applications_application', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('domain_name', self.gf('django.db.models.fields.CharField')(max_length=96, unique=True, null=True, blank=True)),
            ('domain_port', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
        ))
        db.send_create_signal(u'applications', ['Application'])

        # Adding M2M table for field containers on 'Application'
        m2m_table_name = db.shorten_name(u'applications_application_containers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('application', models.ForeignKey(orm[u'applications.application'], null=False)),
            ('container', models.ForeignKey(orm[u'containers.container'], null=False))
        ))
        db.create_unique(m2m_table_name, ['application_id', 'container_id'])


    def backwards(self, orm):
        # Deleting model 'Application'
        db.delete_table(u'applications_application')

        # Removing M2M table for field containers on 'Application'
        db.delete_table(db.shorten_name(u'applications_application_containers'))


    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'domain_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_application_owner
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Application.owner'
        db.add_column(u'applications_application', 'owner',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Application.owner'
        db.delete_column(u'applications_application', 'owner_id')


    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'domain_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_application_protocol
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Application.protocol'
        db.add_column(u'applications_application', 'protocol',
                      self.gf('django.db.models.fields.CharField')(default='http', max_length=6, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Application.protocol'
        db.delete_column(u'applications_application', 'protocol')


    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'domain_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protocol': ('django.db.models.fields.CharField', [], {'default': "'http'", 'max_length': '6', 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']
########NEW FILE########
__FILENAME__ = 0004_auto__del_field_application_domain_port__add_field_application_backend
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Application.domain_port'
        db.delete_column(u'applications_application', 'domain_port')

        # Adding field 'Application.backend_port'
        db.add_column(u'applications_application', 'backend_port',
                      self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Application.domain_port'
        db.add_column(u'applications_application', 'domain_port',
                      self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Application.backend_port'
        db.delete_column(u'applications_application', 'backend_port')


    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'backend_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protocol': ('django.db.models.fields.CharField', [], {'default': "'http'", 'max_length': '6', 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_application_uuid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Application.uuid'
        db.add_column(u'applications_application', 'uuid',
                      self.gf('django.db.models.fields.CharField')(default=None, max_length=36, unique=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Application.uuid'
        db.delete_column(u'applications_application', 'uuid')


    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'backend_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protocol': ('django.db.models.fields.CharField', [], {'default': "'http'", 'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'d10c96d9370b4d69a4a114f920f4fc90'", 'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']

########NEW FILE########
__FILENAME__ = 0006_add_application_uuids
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import uuid

def generate_uuid():
    return str(uuid.uuid4()).replace('-', '')

class Migration(DataMigration):

    def forwards(self, orm):
        for app in orm.Application.objects.all():
            app.uuid = generate_uuid()
            print('Set UUID for {0}: {1}'.format(app.name, app.uuid))
            app.save()

    def backwards(self, orm):
        raise RuntimeError('This will destroy data and you will lose the application UUIDs')

    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'backend_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protocol': ('django.db.models.fields.CharField', [], {'default': "'http'", 'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'870505c4b0e14eb18b2c578274041e30'", 'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_application_host_interface
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Application.host_interface'
        db.add_column(u'applications_application', 'host_interface',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Application.host_interface'
        db.delete_column(u'applications_application', 'host_interface')


    models = {
        u'applications.application': {
            'Meta': {'object_name': 'Application'},
            'backend_port': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True'}),
            'containers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['containers.Container']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'unique': 'True', 'null': 'True'}),
            'host_interface': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protocol': ('django.db.models.fields.CharField', [], {'default': "'http'", 'max_length': '6', 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'f4e4d3b55756482fb1c21b95ebce24af'", 'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protected': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['applications']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.contrib.auth.models import User
from containers.models import Container
from shipyard import utils
from django.utils.translation import ugettext as _
import uuid

PROTOCOL_CHOICES = (
    ('http', _('HTTP')),
    ('https', _('HTTPS')),
    ('tcp', _('TCP')),
)

def generate_uuid():
    return str(uuid.uuid4()).replace('-', '')

class Application(models.Model):
    uuid = models.CharField(max_length=36, null=True, blank=True, unique=True,
        default=generate_uuid)
    name = models.CharField(max_length=64, null=True)
    description = models.TextField(null=True, blank=True)
    domain_name = models.CharField(max_length=96, null=True,
        unique=True)
    host_interface = models.CharField(max_length=128, null=True, blank=True,
        help_text='Host interface your port is bound to or leave blank for default')
    backend_port = models.CharField(max_length=5, null=True)
    protocol = models.CharField(max_length=6, null=True,
        default='http', choices=PROTOCOL_CHOICES)
    containers = models.ManyToManyField(Container, null=True, blank=True,
        limit_choices_to={'is_running': True})
    owner = models.ForeignKey(User, null=True, blank=True)

    def __unicode__(self):
        return self.name

    def get_app_url(self):
        return '{0}://{1}'.format(self.protocol, self.domain_name)

    def get_memory_limit(self):
        mem = 0
        for c in self.containers.all():
            mem += c.get_memory_limit()
        return mem

    def save(self, *args, **kwargs):
        if self.pk is not None:
            original_domain = Application.objects.get(pk=self.pk).domain_name
            # check for changed domain
            if self.domain_name != original_domain:
                # if not original domain, remove hipache config
                utils.remove_hipache_config(original_domain)
        super(Application, self).save(*args, **kwargs)
        self.update_config()

    def update_config(self):
        utils.update_hipache(self.id)

def update_application_config(sender, **kwargs):
    # signal used for updating the manytomany containers field
    app = kwargs.get('instance')
    app.save()
    utils.update_hipache(app.id)

def remove_application_config(sender, **kwargs):
    app = kwargs.get('instance')
    utils.remove_hipache_config(app.domain_name)

m2m_changed.connect(update_application_config, sender=Application.containers.through)
pre_delete.connect(remove_application_config, sender=Application)

########NEW FILE########
__FILENAME__ = tests
import os
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User
from applications.models import Application
from containers.models import Container
from hosts.models import Host

class ApplicationResourceTest(ResourceTestCase):
    #fixtures = ['test_applications.json']

    def setUp(self):
        super(ApplicationResourceTest, self).setUp()
        self.api_list_url = '/api/v1/applications/'
        self.container_list_url = '/api/v1/containers/'
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key
        self.app_data = {
            'name': 'test-app',
            'description': 'test app',
            'domain_name': 'test.example.com',
            'backend_port': 1234,
            'protocol': 'http'
        }
        host = Host()
        host.name = 'local'
        host.hostname = os.getenv('DOCKER_TEST_HOST', '127.0.0.1')
        host.save()
        self.host = host
        self.container_data = {
            'image': 'base',
            'command': '/bin/bash',
            'description': 'test app',
            'ports': ['1234'],
            'hosts': ['/api/v1/hosts/1/']
        }
        resp = self.api_client.post(self.container_list_url, format='json',
            data=self.container_data, authentication=self.get_credentials())
        self.app = Application(**self.app_data)
        self.app.save()

    def tearDown(self):
        # clear apps
        Application.objects.all().delete()
        # remove all test containers
        for c in Container.objects.all():
            c.destroy()

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_get_list_unauthorzied(self):
        """
        Test get without key returns unauthorized
        """
        self.assertHttpUnauthorized(self.api_client.get(self.api_list_url,
            format='json'))

    def test_get_list_json(self):
        """
        Test get application list
        """
        resp = self.api_client.get(self.api_list_url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

    def test_get_detail_json(self):
        """
        Test get application details
        """
        url = '{}1/'.format(self.api_list_url)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        keys = data.keys()
        self.assertTrue('name' in keys)
        self.assertTrue('description' in keys)
        self.assertTrue('domain_name' in keys)
        self.assertTrue('backend_port' in keys)
        self.assertTrue('containers' in keys)

    def test_create_application(self):
        """
        Tests that applications can be created via api
        """
        app_data = self.app_data
        app_data['domain_name'] = 'sample.example.com'
        resp = self.api_client.post(self.api_list_url, format='json',
            data=app_data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        resp = self.api_client.get(self.api_list_url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        d = data.get('objects')[-1]
        self.assertTrue(d.get('name') == app_data.get('name'))
        self.assertTrue(d.get('domain_name') == app_data.get('domain_name'))

    def test_update_application(self):
        """
        Test update application
        """
        url = '{}1/'.format(self.api_list_url)
        data = self.app_data
        app_name = 'app-updated'
        data['name'] = app_name
        resp = self.api_client.put(url, format='json',
            data=data, authentication=self.get_credentials())
        self.assertHttpAccepted(resp)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        self.assertTrue(data.get('name') == app_name)

    def test_update_application_with_containers(self):
        """
        Test update application with containers
        """
        url = '{}1/'.format(self.api_list_url)
        container_url = '{}1/'.format(self.container_list_url)
        data = self.container_data
        data['containers'] = [container_url]
        resp = self.api_client.put(url, format='json',
            data=data, authentication=self.get_credentials())
        self.assertHttpAccepted(resp)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        self.assertTrue(data.get('name') == self.app_data.get('name'))
        self.assertTrue(container_url == data.get('containers')[0].get('resource_uri'))

    def test_delete_application(self):
        """
        Test delete application
        """
        url = '{}1/'.format(self.api_list_url)
        resp = self.api_client.delete(url, format='json',
            authentication=self.get_credentials())
        self.assertHttpAccepted(resp)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertHttpNotFound(resp)

########NEW FILE########
__FILENAME__ = urls
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('applications.views',
    url(r'^$', 'index', name='applications.index'),
    url(r'^create/$', 'create', name='applications.create'),
    url(r'^details/(?P<app_uuid>\w{32})/$', 'details',
        name='applications.details'),
    url(r'^(?P<app_uuid>\w{32})/delete/$', 'delete',
        name='applications.delete'),
    url(r'^(?P<app_uuid>\w{32})/containers/attach/$',
        'attach_containers', name='applications.attach_containers'),
    url(r'^(?P<app_uuid>\w{32})/containers/(?P<container_id>\w{12})/remove/$',
        'remove_container', name='applications.remove_container'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import HttpResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from applications.models import Application
from applications.forms import ApplicationForm, EditApplicationForm
from containers.models import Container

@login_required
def index(request):
    apps = Application.objects.filter(Q(owner=None) |
        Q(owner=request.user))
    ctx = {
        'applications': apps,
    }
    return render_to_response('applications/index.html', ctx,
        context_instance=RequestContext(request))

@login_required
def create(request):
    form = ApplicationForm()
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        form.owner = request.user
        if form.is_valid():
            app = form.save()
            return redirect(reverse('applications.views.index'))
    ctx = {
        'form': form
    }
    return render_to_response('applications/create_application.html', ctx,
        context_instance=RequestContext(request))

@login_required
def details(request, app_uuid=None):
    app = Application.objects.get(uuid=app_uuid)
    form = ApplicationForm(instance=app)
    if request.method == 'POST':
        form = ApplicationForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            try:
                app.update_config()
                messages.add_message(request, messages.INFO,
                    _('Application updated'))
                return redirect(reverse('applications.views.index'))
            except KeyError, e:
                messages.add_message(request, messages.ERROR,
                    _('Error updating hipache.  Invalid container port') + \
                        ': {}'.format(e[0]))
    ctx = {
        'application': app,
        'form': ApplicationForm(instance=app),
    }
    return render_to_response('applications/application_details.html', ctx,
        context_instance=RequestContext(request))

@login_required
def _details(request, app_uuid=None):
    app = Application.objects.get(uuid=app_uuid)
    attached_container_ids = [x.container_id for x in app.containers.all()]
    initial = {
        'name': app.name,
        'description': app.description,
        'domain_name': app.domain_name,
        'backend_port': app.backend_port,
        'protocol': app.protocol,
    }
    all_containers = Container.objects.filter(Q(owner=None) |
        Q(owner=request.user)) \
        .exclude(container_id__in=attached_container_ids)
    containers = [c for c in all_containers if c.get_meta().get('State', {}) \
        .get('Running') == True]
    ctx = {
        'application': app,
        'form_edit_application': EditApplicationForm(initial=initial),
        'containers': containers,
    }
    return render_to_response('applications/application_details.html', ctx,
        context_instance=RequestContext(request))

@login_required
#@owner_required # TODO
def delete(request, app_uuid=None):
    app = Application.objects.get(uuid=app_uuid)
    app.delete()
    return redirect(reverse('applications.views.index'))

@login_required
#@owner_required # TODO
def attach_containers(request, app_uuid=None):
    app = Application.objects.get(uuid=app_uuid)
    data = request.POST
    container_ids = data.getlist('containers', [])
    if container_ids:
        for i in container_ids:
            c = Container.objects.get(container_id=i)
            app.containers.add(c)
        app.save()
    return redirect(reverse('applications.views.details',
        kwargs={'app_uuid': app_uuid}))

@login_required
#@owner_required # TODO
def remove_container(request, app_uuid=None, container_id=None):
    app = Application.objects.get(uuid=app_uuid)
    c = Container.objects.get(container_id=container_id)
    app.containers.remove(c)
    app.save()
    return redirect(reverse('applications.views.details',
        kwargs={'app_uuid': app_uuid}))


########NEW FILE########
__FILENAME__ = admin
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from containers.models import Container

class ContainerAdmin(admin.ModelAdmin):
    list_display = ('container_id', 'host', 'owner')
    list_display_filter = ('is_running',)
    search_fields = ('container_id', 'host__hostname')

admin.site.register(Container, ContainerAdmin)

########NEW FILE########
__FILENAME__ = api
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.http import Http404, HttpResponse
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.bundle import Bundle
from tastypie.authorization import Authorization
from tastypie.authentication import (ApiKeyAuthentication,
    SessionAuthentication, MultiAuthentication)
from django.conf.urls import url
from tastypie.utils import trailing_slash
from containers.models import Container
from hosts.models import Host
from hosts.api import HostResource
from django.contrib.auth.models import User
from shipyard import utils
import time
import socket

class ContainerResource(ModelResource):
    host = fields.ToOneField(HostResource, 'host', full=True)
    meta = fields.DictField(attribute='get_meta')

    class Meta:
        queryset = Container.objects.all()
        resource_name = 'containers'
        always_return_data = True
        authorization = Authorization()
        authentication = MultiAuthentication(
            ApiKeyAuthentication(), SessionAuthentication())
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'delete']
        filtering = {
            'container_id': ALL,
            'is_running': ALL,
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/restart%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('restart'), name="api_restart"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/stop%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('stop'), name="api_stop"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/start%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('start'), name="api_start"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/destroy%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('destroy'), name="api_destroy"),
        ]
    
    def _container_action(self, action, request, **kwargs):
        """
        Container actions

        :param action: Action to perform (restart, stop, destroy)
        :param request: Request object

        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        c_id = kwargs.get('pk')
        if not c_id:
            return HttpResponse(status=404)
        container = None
        # try to get by model id
        try:
            container = Container.objects.get(id=c_id)
        except:
            pass
        # search if container not specified
        if container is None:
            # try to find by container id
            c = Container.objects.filter(container_id__contains=c_id)
            if not c:
                return HttpResponse("Invalid container", status=404)
            if len(c) > 1:
                return HttpResponse("Multiple containers found", status=400)
            container = c[0]
        actions = {
            'restart': container.restart,
            'stop': container.stop,
            'start': container.restart,
            'destroy': container.destroy,
            }
        actions[action]()
        self.log_throttled_access(request)
        return HttpResponse(status=204)
        
    def restart(self, request, **kwargs):
        """
        Custom view for restarting containers

        """
        return self._container_action('restart', request, **kwargs)

    def stop(self, request, **kwargs):
        """
        Custom view for stopping containers

        """
        return self._container_action('stop', request, **kwargs)

    def start(self, request, **kwargs):
        """
        Custom view for starting containers

        """
        return self._container_action('start', request, **kwargs)


    def destroy(self, request, **kwargs):
        """
        Custom view for destroying containers

        """
        return self._container_action('destroy', request, **kwargs)

    def detail_uri_kwargs(self, bundle_or_obj, **kwargs):
        kwargs = {}
        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id
        return kwargs

    def obj_create(self, bundle, request=None, **kwargs):
        """
        Override obj_create to launch containers and return metadata

        """
        # HACK: get host id -- this should probably be some type of
        # reverse lookup from tastypie
        if not bundle.data.has_key('hosts'):
            raise StandardError('You must specify hosts')
        host_urls = bundle.data.get('hosts')
        # remove 'hosts' from data and pass rest to create_container
        del bundle.data['hosts']
        containers = []
        # launch on hosts
        for host_url in host_urls:
            host_id = host_url.split('/')[-2]
            host = Host.objects.get(id=host_id)
            data = bundle.data
            c_id, status = host.create_container(**data)
            obj = Container.objects.get(container_id=c_id)
            bundle.obj = obj
            containers.append(obj)
        # wait for containers if port is specified and requested
        if bundle.request.GET.has_key('wait') == True:
            # check for timeout override
            try:
                timeout = int(bundle.request.GET.get('wait'))
            except Exception, e:
                timeout = 60
            ids = []
            for c in containers:
                # wait for port to be available
                count = 0
                c_id = c.container_id
                while True:
                    if count > timeout:
                        break
                    # reload meta to get NAT port
                    c = Container.objects.get(container_id=c_id)
                    if c.is_available():
                        break
                    count += 1
                    time.sleep(1)
        bundle = self.full_hydrate(bundle)
        return bundle

    def obj_delete(self, request=None, **kwargs):
        id = kwargs.get('pk')
        c = Container.objects.get(id=id)
        h = c.host
        h.destroy_container(c.container_id)

    def obj_delete_list(self, request=None, **kwargs):
        for c in Container.objects.all():
            h = c.host
            h.destroy_container(c.container_id)

########NEW FILE########
__FILENAME__ = forms
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from hosts.models import Host
from images.models import Image
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Button
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, FormActions
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

def get_available_hosts():
    return Host.objects.filter(enabled=True)

def get_image_choices():
    hosts = get_available_hosts()
    choices = []
    images = Image.objects.filter(host__in=hosts).order_by('repository').values_list(
            'repository', flat=True).order_by('repository').distinct()
    for i in images:
        repo = i
        if repo.find('<none>') == -1:
            d = (repo, repo)
            choices.append(d)
    return choices

class CreateContainerForm(forms.Form):
    image = forms.ChoiceField(required=True)
    name = forms.CharField(required=False, help_text=_('container name (used in links)'))
    hostname = forms.CharField(required=False)
    description = forms.CharField(required=False)
    command = forms.CharField(required=False)
    memory = forms.CharField(required=False, max_length=8,
        help_text='Memory in MB')
    environment = forms.CharField(required=False,
        help_text='key=value space separated pairs')
    ports = forms.CharField(required=False, help_text=_('space separated (i.e. 8000 8001:8001 127.0.0.1:80:80 )'))
    links = forms.CharField(required=False, help_text=_('space separated (i.e. redis:db)'))
    volume = forms.CharField(required=False, help_text='container volume (i.e. /mnt/volume)')
    volumes_from = forms.CharField(required=False,
        help_text='mount volumes from specified container')
    hosts = forms.MultipleChoiceField(required=True)
    private = forms.BooleanField(required=False)
    privileged = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateContainerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                None,
                'image',
                'name',
                'hostname',
                'command',
                'description',
                'memory',
                'environment',
                'ports',
                'links',
                'volume',
                'volumes_from',
                'hosts',
                'private',
                'privileged',
            ),
            FormActions(
                Submit('save', _('Create'), css_class="btn btn-lg btn-success"),
            )
        )
        self.helper.form_id = 'form-create-container'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.create_container')
        self.helper.help_text_inline = True
        self.fields['image'].choices = [('', '----------')] + \
            [x for x in get_image_choices()]
        self.fields['hosts'].choices = \
            [(x.id, x.name) for x in get_available_hosts()]

class ImportRepositoryForm(forms.Form):
    repository = forms.CharField(help_text='i.e. ehazlett/logstash')
    hosts = forms.MultipleChoiceField()

    def __init__(self, *args, **kwargs):
        super(ImportRepositoryForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-import-repository'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.import_image')
        self.helper.help_text_inline = True
        self.fields['hosts'].choices = \
            [(x.id, x.name) for x in get_available_hosts()]

class ContainerForm(forms.Form):
    image = forms.ChoiceField()
    command = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateContainerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-create-container'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.create_container')
        self.helper.help_text_inline = True
        self.fields['image'].widget.attrs['readonly'] = True

class ImageBuildForm(forms.Form):
    dockerfile = forms.FileField(required=False)
    url = forms.URLField(help_text='Dockerfile URL', required=False)
    tag = forms.CharField(help_text='i.e. app-v1', required=False)
    hosts = forms.MultipleChoiceField()

    def __init__(self, *args, **kwargs):
        super(ImageBuildForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-build-image'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.build_image')
        self.helper.help_text_inline = True
        self.fields['hosts'].choices = \
            [(x.id, x.name) for x in get_available_hosts()]


########NEW FILE########
__FILENAME__ = clear_container_metadata
from django.core.management.base import BaseCommand, CommandError
from containers import models

class Command(BaseCommand):
    help = 'Clears container metadata'

    def handle(self, *args, **options):
        models.Container.objects.all().delete()

########NEW FILE########
__FILENAME__ = purge_containers
from django.core.management.base import BaseCommand, CommandError
from containers.models import Host, Container
from shipyard import utils

class Command(BaseCommand):
    help = 'Purges container metadata for removed containers'

    def handle(self, *args, **options):
        hosts = Host.objects.filter(enabled=True)
        all_containers = [x.container_id for x in Container.objects.all()]
        for host in hosts:
            host_containers = [c.get('Id') \
                for c in host.get_containers(show_all=True)]
            for c in all_containers:
                if c not in host_containers:
                    print('Removing {}'.format(c))
                    Container.objects.get(container_id=c).delete()


########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Host'
        db.create_table(u'containers_host', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, unique=True, null=True, blank=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True, blank=True)),
            ('port', self.gf('django.db.models.fields.SmallIntegerField')(default=4243, null=True, blank=True)),
        ))
        db.send_create_signal(u'containers', ['Host'])


    def backwards(self, orm):
        # Deleting model 'Host'
        db.delete_table(u'containers_host')


    models = {
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_host_enabled
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Host.enabled'
        db.add_column(u'containers_host', 'enabled',
                      self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Host.enabled'
        db.delete_column(u'containers_host', 'enabled')


    models = {
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0003_auto__add_container
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Container'
        db.create_table(u'containers_container', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['containers.Host'], null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal(u'containers', ['Container'])


    def backwards(self, orm):
        # Deleting model 'Container'
        db.delete_table(u'containers_container')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0004_auto__del_field_container_name__add_field_container_container_id
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Container.name'
        db.delete_column(u'containers_container', 'name')

        # Adding field 'Container.container_id'
        db.add_column(u'containers_container', 'container_id',
                      self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Container.name'
        db.add_column(u'containers_container', 'name',
                      self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Container.container_id'
        db.delete_column(u'containers_container', 'container_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_container_meta
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Container.meta'
        db.add_column(u'containers_container', 'meta',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Container.meta'
        db.delete_column(u'containers_container', 'meta')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_container_description
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Container.description'
        db.add_column(u'containers_container', 'description',
                      self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Container.description'
        db.delete_column(u'containers_container', 'description')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0007_auto__del_field_container_user__add_field_container_owner
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Container.user'
        db.delete_column(u'containers_container', 'user_id')

        # Adding field 'Container.owner'
        db.add_column(u'containers_container', 'owner',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Container.user'
        db.add_column(u'containers_container', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Container.owner'
        db.delete_column(u'containers_container', 'owner_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_container_is_running
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Container.is_running'
        db.add_column(u'containers_container', 'is_running',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Container.is_running'
        db.delete_column(u'containers_container', 'is_running')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0009_auto__add_field_container_protected
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Container.protected'
        db.add_column(u'containers_container', 'protected',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Container.protected'
        db.delete_column(u'containers_container', 'protected')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protected': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0010_auto__add_field_host_public_hostname
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Host.public_hostname'
        db.add_column(u'containers_host', 'public_hostname',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Host.public_hostname'
        db.delete_column(u'containers_host', 'public_hostname')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['containers.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protected': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'containers.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = 0011_auto__del_host__chg_field_container_host
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # unset host for all containers ; these will be reset when the agent runs

        # Deleting model 'Host'
        db.delete_table(u'containers_host')


        # Changing field 'Container.host'
        #db.alter_column(u'containers_container', 'host_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['hosts.Host'], null=True))

    def backwards(self, orm):
        # Adding model 'Host'
        db.create_table(u'containers_host', (
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64, null=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128, null=True)),
            ('enabled', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('public_hostname', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('port', self.gf('django.db.models.fields.SmallIntegerField')(default=4243, null=True)),
        ))
        db.send_create_signal(u'containers', ['Host'])


        # Changing field 'Container.host'
        db.alter_column(u'containers_container', 'host_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['containers.Host'], null=True))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hosts.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protected': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['containers']

########NEW FILE########
__FILENAME__ = 0012_auto__add_field_container_synced
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Container.synced'
        db.add_column(u'containers_container', 'synced',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Container.synced'
        db.delete_column(u'containers_container', 'synced')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'containers.container': {
            'Meta': {'object_name': 'Container'},
            'container_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hosts.Host']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'protected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'synced': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'agent_key': ('django.db.models.fields.CharField', [], {'default': "'e8f5beffb6a74f7db7c246ad6d6968a8'", 'max_length': '64', 'null': 'True'}),
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['containers']
########NEW FILE########
__FILENAME__ = models
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.db.models import Q
from shipyard import utils
import json

class Container(models.Model):
    container_id = models.CharField(max_length=96, null=True, blank=True)
    description = models.TextField(blank=True, null=True, default='')
    meta = models.TextField(blank=True, null=True, default='{}')
    is_running = models.BooleanField(default=True)
    host = models.ForeignKey('hosts.Host', null=True, blank=True)
    owner = models.ForeignKey(User, null=True, blank=True)
    protected = models.BooleanField(default=False)
    synced = models.BooleanField(default=False, blank=True,
            help_text='Whether the agent has synced the container info')

    def __unicode__(self):
        d = self.get_short_id()
        if d and self.description:
            d += ' ({0})'.format(self.description)
        return d

    @classmethod
    def get_running(cls, user=None):
        from hosts.models import Host
        hosts = Host.objects.filter(enabled=True)
        containers = Container.objects.filter(is_running=True,
                host__in=hosts)
        return containers

    def is_public(self):
        if self.owner == None:
            return True
        else:
            return False

    def get_meta(self):
        meta = {}
        if self.meta:
            meta = json.loads(self.meta)
        return meta

    def get_short_id(self):
        return self.container_id[:12]

    def get_applications(self):
        from applications.models import Application
        return Application.objects.filter(containers__in=[self])

    def is_available(self):
        """
        This will run through all ExposedPorts and attempt a connect.  If
        successful, returns True.  If there are no ExposedPorts, it is assumed
        that the container has completed and is available.

        """
        meta = self.get_meta()
        exposed_ports = meta.get('Config', {}).get('ExposedPorts', [])
        available = True
        port_checks = []
        host = self.host.get_hostname()
        # attempt to connect to check availability
        meta_net = meta.get('NetworkSettings')
        if meta_net.get('Ports') and len(meta_net.get('Ports')) != 0:
            for e_port in exposed_ports:
                ports = meta_net.get('Ports')
                port_defs = ports[e_port]
                if port_defs:
                    port = port_defs[0].get('HostPort')
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(1)
                        s.connect((host, int(port)))
                        port_checks.append(True)
                        continue
                    except Exception, e:
                        port_checks.append(False)
                        s.close()
            if port_checks and False in port_checks:
                available = False
        return available

    def restart(self):
        return self.host.restart_container(container_id=self.container_id)

    def stop(self):
        return self.host.stop_container(container_id=self.container_id)

    def logs(self):
        return self.host.get_container_logs(container_id=self.container_id)

    def destroy(self):
        return self.host.destroy_container(container_id=self.container_id)

    def get_ports(self):
        meta = self.get_meta()
        network_settings = meta.get('NetworkSettings', {})
        ports = {}
        if self.host.version < '0.6.5':
            # for verions prior to docker v0.6.5
            port_mapping = network_settings.get('PortMapping')
            for proto in port_mapping:
                for port, external_port in port_mapping[proto].items():
                    port_proto = "{0}/{1}".format(port, proto)
                    ports[port_proto] = { '0.0.0.0': external_port }
        else:
            # for versions after docker v0.6.5
            if network_settings.get('Ports') != None:
                for port_proto, host_list in network_settings.get('Ports', {}).items():
                    for host in host_list or []:
                        ports[port_proto] = { host.get('HostIp'): host.get('HostPort') }
        return ports

    def get_memory_limit(self):
        mem = 0
        meta = self.get_meta()
        if meta:
            mem = int(meta.get('Config', {}).get('Memory')) / 1048576
        return mem

    def get_name(self):
        d = self.get_short_id()
        if self.description:
            d = self.description
        return d

########NEW FILE########
__FILENAME__ = tests
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User
from containers.models import Container
from hosts.models import Host
import os

class ContainerResourceTest(ResourceTestCase):

    def setUp(self):
        super(ContainerResourceTest, self).setUp()
        self.api_list_url = '/api/v1/containers/'
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key
        host = Host()
        host.name = 'local'
        host.hostname = os.getenv('DOCKER_TEST_HOST', '127.0.0.1')
        host.save()
        self.host = host
        self.data = {
            'image': 'base',
            'command': '/bin/bash',
            'description': 'test app',
            'ports': [],
            'hosts': ['/api/v1/hosts/1/']
        }
        resp = self.api_client.post(self.api_list_url, format='json',
            data=self.data, authentication=self.get_credentials())

    def tearDown(self):
        for c in Container.objects.all():
            c.destroy()

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_get_list_unauthorzied(self):
        """
        Test get without key returns unauthorized
        """
        self.assertHttpUnauthorized(self.api_client.get(self.api_list_url,
            format='json'))

    def test_get_list_json(self):
        """
        Test get application list
        """
        resp = self.api_client.get(self.api_list_url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        self.assertTrue(len(data.get('objects')) == 1)

    def test_get_detail_json(self):
        """
        Test get application details
        """
        url = '{}1/'.format(self.api_list_url)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        keys = data.keys()
        self.assertTrue('container_id' in keys)
        self.assertTrue('meta' in keys)

    def test_create_container(self):
        """
        Tests create container
        """
        resp = self.api_client.post(self.api_list_url, format='json',
            data=self.data, authentication=self.get_credentials())
        self.assertHttpCreated(resp)

    def test_delete_container(self):
        url = '{}1/'.format(self.api_list_url)
        resp = self.api_client.delete(url, format='json',
            authentication=self.get_credentials())
        self.assertHttpAccepted(resp)

    def test_restart_container(self):
        """
        Test container restart
        """
        url = '{}1/restart/'.format(self.api_list_url)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertHttpAccepted(resp)

    def test_stop_container(self):
        """
        Test container stop
        """
        url = '{}1/stop/'.format(self.api_list_url)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertHttpAccepted(resp)

    def test_destroy_container(self):
        """
        Test container destroy
        """
        url = '{}1/destroy/'.format(self.api_list_url)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertHttpAccepted(resp)


########NEW FILE########
__FILENAME__ = urls
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('containers.views',
    url(r'^$', 'index'),
    url(r'^details/(?P<container_id>.*)/$', 'container_details'),
    url(r'^create/$', 'create_container'),
    url(r'^protect/(?P<host_id>.*)/(?P<container_id>.*)/$',
        'toggle_protect_container'),
    url(r'^logs/(?P<host>.*)/(?P<container_id>.*)/$',
        'container_logs', name='container_logs'),
    url(r'^refresh/$', 'refresh', name='containers.refresh'),
    url(r'^clone/(?P<host>.*)/(?P<container_id>.*)/$',
        'clone_container'),
    url(r'^searchrepository/$', 'search_repository',
        name='containers.search_repository'),
    url(r'^destroycontainer/(?P<host>.*)/(?P<container_id>.*)/$',
        'destroy_container', name='containers.destroy_container'),
    url(r'^attachcontainer/(?P<host>.*)/(?P<container_id>.*)/$',
        'attach_container', name='containers.attach_container'),
    url(r'^restartcontainer/(?P<host>.*)/(?P<container_id>.*)/$',
        'restart_container', name='containers.restart_container'),
    url(r'^stopcontainer/(?P<host>.*)/(?P<container_id>.*)/$',
        'stop_container', name='containers.stop_container'),
    url(r'^containerinfo/$',
        'container_info', name='containers.container_info'),
    url(r'^containerinfo/(?P<container_id>.*)/$',
        'container_info', name='containers.container_info'),
    url(r'^buildimage/$', 'build_image',
        name='containers.build_image'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.db.models import Q
from django.utils.html import strip_tags
from django.core import serializers
from django.shortcuts import render_to_response
from containers.models import Container
from hosts.models import Host
from metrics.models import Metric
from django.template import RequestContext
from containers.forms import (CreateContainerForm,
    ImportRepositoryForm, ImageBuildForm)
from shipyard import utils
from docker import client
import urllib
import random
import json
import tempfile
import shlex

def handle_upload(f):
    tmp_file = tempfile.mktemp()
    with open(tmp_file, 'w') as d:
        for c in f.chunks():
            d.write(c)
    return tmp_file

@login_required
def index(request):
    hosts = Host.objects.filter(enabled=True)
    show_all = True if request.GET.has_key('showall') else False
    containers = Container.objects.filter(host__in=hosts, is_running=True).\
            order_by('description')
    ctx = {
        'hosts': hosts,
        'containers': containers,
        'show_all': show_all,
    }
    return render_to_response('containers/index.html', ctx,
        context_instance=RequestContext(request))

@login_required
def container_details(request, container_id=None):
    c = Container.objects.get(container_id=container_id)
    metrics = Metric.objects.filter(source=c.container_id).order_by('-timestamp')
    cpu_metrics = metrics.filter(counter='cpu')[:30]
    mem_metrics = metrics.filter(counter='memory')[:30]
    # build custom data to use unix timestamp instead of python datetime
    cpu_data = []
    mem_data = []
    for m in cpu_metrics:
        cpu_data.append({
            'counter': m.counter,
            'value': m.value,
            'timestamp': m.unix_timestamp(),
            })
    for m in mem_metrics:
        mem_data.append({
            'counter': m.counter,
            'value': m.value,
            'timestamp': m.unix_timestamp(),
            })
    ctx = {
        'container': c,
        'cpu_metrics': json.dumps(cpu_data),
        'mem_metrics': json.dumps(mem_data),
    }
    return render_to_response('containers/container_details.html', ctx,
        context_instance=RequestContext(request))

@login_required
def create_container(request):
    form = CreateContainerForm()
    if request.method == 'POST':
        # save
        form = CreateContainerForm(request.POST)
        if form.is_valid():
            image = form.data.get('image')
            name = form.data.get('name')
            hostname = form.data.get('hostname')
            description = form.data.get('description')
            environment = form.data.get('environment')
            command = form.data.get('command')
            memory = form.data.get('memory', 0)
            links = form.data.get('links', None)
            volume = form.data.get('volume')
            volumes_from = form.data.get('volumes_from')
            ports = form.data.get('ports', '').split()
            hosts = form.data.getlist('hosts')
            private = form.data.get('private')
            privileged = form.data.get('privileged')
            user = None
            status = False
            for i in hosts:
                host = Host.objects.get(id=i)
                if private:
                    user = request.user
                try:
                    c_id, status = host.create_container(image, command, ports,
                        environment=environment, memory=memory,
                        description=description, volumes=volume,
                        volumes_from=volumes_from, privileged=privileged,
                        links=links, name=name, owner=user,
                        hostname=hostname)
                    messages.add_message(request, messages.INFO, _('Created') + ' {0}'.format(
                        image))
                except Exception, e:
                    print(e)
                    messages.error(request, e)
                    status = False
            if not hosts:
                messages.add_message(request, messages.ERROR, _('No hosts selected'))
            return redirect(reverse('containers.views.index'))
    ctx = {
        'form_create_container': form,
    }
    return render_to_response('containers/create_container.html', ctx,
        context_instance=RequestContext(request))

@login_required
def container_info(request, container_id=None):
    '''
    Gets / Sets container metatdata

    '''
    if request.method == 'POST':
        data = request.POST
        container_id = data.get('container-id')
        c = Container.objects.get(container_id=container_id)
        c.description = data.get('description')
        c.save()
        return redirect(reverse('containers.views.container_details',
            args=(c.container_id,)))
    c = Container.objects.get(container_id=container_id)
    data = serializers.serialize('json', [c], ensure_ascii=False)[1:-1]
    return HttpResponse(data, content_type='application/json')

@login_required
def container_logs(request, host, container_id):
    '''
    Gets the specified container logs

    '''
    h = Host.objects.get(name=host)
    c = Container.objects.get(container_id=container_id)
    logs = h.get_container_logs(container_id).strip()
    # format
    if logs:
        logs = utils.convert_ansi_to_html(logs)
    else:
        logs = None
    ctx = {
        'container': c,
        'logs': logs
    }
    return render_to_response('containers/container_logs.html', ctx,
        context_instance=RequestContext(request))

@login_required
def restart_container(request, host, container_id):
    h = Host.objects.get(name=host)
    h.restart_container(container_id)
    messages.add_message(request, messages.INFO, _('Restarted') + ' {0}'.format(
        container_id))
    return redirect('containers.views.index')

@login_required
def stop_container(request, host, container_id):
    h = Host.objects.get(name=host)
    try:
        h.stop_container(container_id)
        messages.add_message(request, messages.INFO, _('Stopped') + ' {0}'.format(
            container_id))
    except Exception, e:
        messages.add_message(request, messages.ERROR, e)
    return redirect('containers.views.index')

@login_required
def destroy_container(request, host, container_id):
    h = Host.objects.get(name=host)
    try:
        h.destroy_container(container_id)
        messages.add_message(request, messages.INFO, _('Removed') + ' {0}'.format(
            container_id))
    except Exception, e:
        messages.add_message(request, messages.ERROR, e)
    return redirect('containers.views.index')

@login_required
def attach_container(request, host, container_id):
    h = Host.objects.get(name=host)
    c = Container.objects.get(container_id=container_id)
    session_id = utils.generate_console_session(h, c)
    ctx = {
        'container_id': container_id,
        'container_name': c.description or container_id,
        'ws_url': 'ws://{0}/console/{1}/'.format(request.META['HTTP_HOST'], session_id),
    }
    return render_to_response("containers/attach.html", ctx,
        context_instance=RequestContext(request))

@login_required
def clone_container(request, host, container_id):
    h = Host.objects.get(name=host)
    try:
        h.clone_container(container_id)
        messages.add_message(request, messages.INFO, _('Cloned') + ' {0}'.format(
            container_id))
    except Exception, e:
        messages.add_message(request, messages.ERROR, e)
    return redirect('containers.views.index')

@login_required
def refresh(request):
    '''
    Invalidates host cache and redirects to container view

    '''
    for h in Host.objects.filter(enabled=True):
        h.invalidate_cache()
    return redirect('containers.views.index')

@require_http_methods(['GET'])
@login_required
def search_repository(request):
    '''
    Searches the docker index for repositories

    :param query: Query to search for

    '''
    query = request.GET.get('query', {})
    # get random host for query -- just needs a connection
    hosts = Host.objects.filter(enabled=True)
    rnd = random.randint(0, len(hosts)-1)
    host = hosts[rnd]
    url = 'http://{0}:{1}'.format(host.hostname, host.port)
    c = client.Client(url)
    data = c.search(query)
    return HttpResponse(json.dumps(data), content_type='application/json')

@require_http_methods(['POST'])
@login_required
def build_image(request):
    '''
    Builds a container image

    '''
    form = ImageBuildForm(request.POST)
    url = form.data.get('url')
    tag = form.data.get('tag')
    hosts = form.data.getlist('hosts')
    # dockerfile takes precedence
    docker_file = None
    if request.FILES.has_key('dockerfile'):
        docker_file = handle_upload(request.FILES.get('dockerfile'))
    else:
        docker_file = tempfile.mktemp()
        urllib.urlretrieve(url, docker_file)
    for i in hosts:
        host = Host.objects.get(id=i)
        args = (docker_file, tag)
        # TODO: update to celery
        #utils.get_queue('shipyard').enqueue(host.build_image, args=args,
        #    timeout=3600)
    messages.add_message(request, messages.INFO,
        _('Building image from docker file.  This may take a few minutes.'))
    return redirect(reverse('index'))

@csrf_exempt
@require_http_methods(['POST'])
@login_required
def toggle_protect_container(request, host_id, container_id):
    enabled = request.POST.get('enabled')
    host = Host.objects.get(id=host_id)
    container = Container.objects.get(host=host, container_id=container_id)
    if enabled == 'true':
        container.protected = True
    else:
        container.protected = False
    container.save()
    return HttpResponse('done')


########NEW FILE########
__FILENAME__ = help
# Module:   help
# Date:     28th November 2013
# Author:   James Mills, j dot mills at griffith dot edu dot au

"""
Shipyard Deployer

This is a quick method to get a production Shipyard setup deployed.  You will
need the following:

    * Python
    * Fabric (`easy_install fabric` or `pip install fabric`)
    * 2 x Remote Hosts with SSH access and sudo (currently Debian or Ubuntu)

For this deployment method there are two types of nodes: "lb" and "core".  The
"lb" node is the load balancer.  This will be used for the master Redis
instance and the Shipyard Load Balancer.  The "core" node should larger.  It
will be used for the App Router, DB, and the Shipyard UI as well as any other
containers you want.

For a fully automated deployment, run:

    fab -H <docker-host> setup

This will install all components on the two instances and return the login
credentials when finished.

To remove a deployment:

    fab -H <docker-host> teardown

To clean (removes Docker images):

    fab -H <docker-host> clean

There are several fabric "tasks" that you can use to deploy various components.
To see available tasks run "fab -l".  You can run a specific task like:

    fab -H <my_hostname> <task_name>

For example:

    fab -H myhost.domain.com install_docker

If you have issues please do not hesitate to report via Github or visit us
on IRC (freenode #shipyard).
"""


from __future__ import print_function


from fabric import state
from fabric.api import task
from fabric.tasks import Task
from fabric.task_utils import crawl


@task(default=True)
def help(name=None):
    """Display help for a given task

    Options:
        name    - The task to display help on.

    To display a list of available tasks type:

        $ fab -l

    To display help on a specific task type:

        $ fab help:<name>
    """

    if name is None:
        print(__doc__)
        return

    task = crawl(name, state.commands)
    if isinstance(task, Task):
        doc = getattr(task, "__doc__", None)
        if doc is not None:
            print("Help on {0:s}:".format(name))
            print()
            print(doc)
        else:
            print("No help available for {0:s}".format(name))
    else:
        print("No such task {0:s}".format(name))
        print("For a list of tasks type: fab -l")

########NEW FILE########
__FILENAME__ = utils
# Module:   utils
# Date:     03rd April 2013
# Author:   James Mills, j dot mills at griffith dot edu dot au

"""Utilities"""

from functools import wraps
from imp import find_module
from contextlib import contextmanager


from fabric.api import abort, hide, local, puts, quiet, settings, warn


def tobool(s):
    if isinstance(s, bool):
        return s
    return s.lower() in ["yes", "y"]


def toint(s):
    if isinstance(s, int):
        return s
    return int(s)


@contextmanager
def msg(s):
    """Print message given as ``s`` in a context manager

    Prints "{s} ... OK"
    """

    puts("{0:s} ... ".format(s), end="", flush=True)
    with settings(hide("everything")):
        yield
    puts("OK", show_prefix=False, flush=True)


def pip(*args, **kwargs):
    requirements = kwargs.get("requirements", None)
    if requirements is not None:
        local("pip install -U -r {0:s}".format(kwargs["requirements"]))
    else:
        args = list(arg for arg in args if not has_module(arg))
        if args:
            local("pip install {0:s}".format(" ".join(args)))


def has_module(name):
    try:
        return find_module(name)
    except ImportError:
        return False


def has_binary(name):
    with quiet():
        return local("which {0:s}".format(name)).succeeded


def requires(*names, **kwargs):
    """Decorator/Wrapper that aborts if not all requirements are met.

    Aborts if not all requirements are met given a test function (defaulting to :func:`~has_binary`).

    :param kwargs: Optional kwargs. e.g: ``test=has_module``
    :type kwargs: dict

    :returns: None or aborts
    :rtype: None
    """

    test = kwargs.get("test", has_binary)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwds):
            if all(test(name) for name in names):
                return f(*args, **kwds)
            else:
                for name in names:
                    if not test(name):
                        warn("{0:s} not found".format(name))
                abort("requires({0:s}) failed".format(repr(names)))
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = fig_settings
import os
from shipyard.settings import *

########NEW FILE########
__FILENAME__ = admin
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from hosts.models import Host

class HostAdmin(admin.ModelAdmin):
    list_display = ('name', 'hostname', 'port', 'enabled')
    search_fields = ('name', 'hostname', 'port')
    list_filter = ('enabled',)

admin.site.register(Host, HostAdmin)

########NEW FILE########
__FILENAME__ = api
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.authentication import (ApiKeyAuthentication,
    SessionAuthentication, MultiAuthentication)
from tastypie.bundle import Bundle
from django.conf.urls import url
from hosts.models import Host

class HostResource(ModelResource):
    class Meta:
        queryset = Host.objects.all()
        resource_name = 'hosts'
        authorization = Authorization()
        authentication = MultiAuthentication(
            ApiKeyAuthentication(), SessionAuthentication())


########NEW FILE########
__FILENAME__ = forms
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from hosts.models import Host
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Button
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, FormActions
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

class HostForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(HostForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                None,
                'name',
                'hostname',
                'public_hostname',
                'agent_key',
                'port',
            ),
            FormActions(
                Submit('save', _('Save'), css_class="btn btn-lg btn-success"),
            )
        )
        self.helper.form_id = 'form-edit-host'
        self.helper.form_class = 'form-horizontal'

    def clean_hostname(self):
        data = self.cleaned_data['hostname']
        if '/' in data and 'unix' not in data:
            raise forms.ValidationError(_('Please enter a hostname or IP only'))
        return data

    class Meta:
        model = Host
        fields = ('name', 'hostname', 'public_hostname', 'agent_key', 'port')


########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Host'
        db.create_table(u'hosts_host', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, unique=True, null=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True)),
            ('public_hostname', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('port', self.gf('django.db.models.fields.SmallIntegerField')(default=4243, null=True)),
            ('enabled', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
        ))
        db.send_create_signal(u'hosts', ['Host'])


    def backwards(self, orm):
        # Deleting model 'Host'
        db.delete_table(u'hosts_host')


    models = {
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['hosts']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_host_agent_key
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Host.agent_key'
        db.add_column(u'hosts_host', 'agent_key',
                      self.gf('django.db.models.fields.CharField')(default='7148e5296d224298aaab5d2d165e3117', max_length=64, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Host.agent_key'
        db.delete_column(u'hosts_host', 'agent_key')


    models = {
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'agent_key': ('django.db.models.fields.CharField', [], {'default': "'f466ddf07c6e4934959798044965ca26'", 'max_length': '64', 'null': 'True'}),
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['hosts']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_host_last_updated
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Host.last_updated'
        db.add_column(u'hosts_host', 'last_updated',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Host.last_updated'
        db.delete_column(u'hosts_host', 'last_updated')


    models = {
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'agent_key': ('django.db.models.fields.CharField', [], {'default': "'d89a700e3fec4897baa576855d6acd5e'", 'max_length': '64', 'null': 'True'}),
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['hosts']
########NEW FILE########
__FILENAME__ = models
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models
from distutils.version import LooseVersion
from docker import client
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext as _
from shipyard.exceptions import ProtectedContainerError
from uuid import uuid4
from containers.models import Container
import shlex
import hashlib
import requests
import socket
import json

HOST_CACHE_TTL = getattr(settings, 'HOST_CACHE_TTL', 15)
CONTAINER_KEY = '{0}:containers'
IMAGE_KEY = '{0}:images'

def generate_agent_key():
    return str(uuid4()).replace('-', '')

class Host(models.Model):
    name = models.CharField(max_length=64, null=True,
        unique=True)
    hostname = models.CharField(max_length=128, null=True,
            unique=True, help_text=_('Host/IP/Socket to connect to Docker'))
    public_hostname = models.CharField(max_length=128, null=True, blank=True,
            help_text=_('Hostname/IP used for applications (if different from hostname)'))
    port = models.SmallIntegerField(null=True, default=4243)
    agent_key = models.CharField(max_length=64, null=True,
            default=generate_agent_key, help_text=_('Agent Key'))
    last_updated = models.DateTimeField(auto_now=True, null=True,
            help_text=_('Last time agent reported an update'))
    enabled = models.NullBooleanField(null=True, default=False)

    def __unicode__(self):
        return self.name

    @property
    def version(self):
        c = self._get_client()
        data = c.version()
        return LooseVersion(data['Version'])

    def _get_client(self):
        url = self.hostname
        if 'unix' not in url:
            url ='{0}:{1}'.format(self.hostname, self.port)
            if not url.startswith('http'):
                url = 'http://{0}'.format(url)
        return client.Client(base_url=url)

    def _load_container_data(self, container_id):
        c = self._get_client()
        meta = c.inspect_container(container_id)
        m, created = Container.objects.get_or_create(
            container_id=container_id, host=self)
        m.is_running = meta.get('State', {}).get('Running', False)
        m.meta = json.dumps(meta)
        m.save()

    def create_container(self, image=None, command=None, ports=[],
        environment=[], memory=0, description='', volumes=None, volumes_from='',
        privileged=False, binds=None, links=None, name=None, owner=None,
        hostname=None, **kwargs):
        if isinstance(command, str) and command.strip() == '':
            command = None
        if isinstance(environment, str) and environment.strip() == '':
            environment = None
        elif not isinstance(environment, list):
            environment = shlex.split(environment)
        # build volumes
        if not binds:
            binds = None
            if volumes == '':
                volumes = None
            if volumes:
                if volumes.find(':') > -1:
                    mnt, vol = volumes.split(':')
                    volumes = { vol: {}}
                    binds = { mnt: vol }
                else:
                    volumes = { volumes: {}}
        # build links
        c_links = {}
        if links:
            for link in links.split():
                l,n = link.split(':')
                c_links[l] = n
            links = c_links
        # convert memory from MB to bytes
        if memory:
            memory = int(memory) * 1048576
        if isinstance(memory, str) and memory.strip() == '':
            memory = 0
        if isinstance(ports, str):
            ports = ports.split(',')
        if self.version < '0.6.5':
            port_exposes = ports
            port_bindings = None
        else:
            port_exposes = {}
            port_bindings = {}
            for port_str in ports:
                port_parts = port_str.split(':')
                if len(port_parts) == 3:
                    interface, mapping, port = port_parts
		    port_bindings[port] = (interface, mapping)
                    port_exposes[port]
                elif len(port_parts) == 2:
                    mapping, port = port_parts
		    port_bindings[port] = mapping
                else:
                    port = port_str
		    port_bindings[port] = None
                if port.find('/') < 0:
                    port = "{0}/tcp".format(port)
                port_exposes[port_str] = {}
        # convert to bool
        if privileged:
            privileged = True
        c = self._get_client()
        try:
            cnt = c.create_container(image=image, command=command, detach=True,
                    ports=ports, mem_limit=memory, tty=True, stdin_open=True,
                environment=environment, volumes=volumes,
                volumes_from=volumes_from, name=name,
                hostname=hostname, **kwargs)
        except Exception, e:
            raise StandardError('There was an error starting the container: {}'.format(
                e))
        c_id = cnt.get('Id')
        c.start(c_id, binds=binds, port_bindings=port_bindings, links=links,
                privileged=privileged)
        status = False
        # create metadata only if container starts successfully
        if c.inspect_container(c_id).get('State', {}).get('Running'):
            c, created = Container.objects.get_or_create(container_id=c_id,
                host=self)
            c.description = description
            c.owner = owner
            c.save()
            status = True
        return c_id, status

    def restart_container(self, container_id=None):
        from applications.models import Application
        c = self._get_client()
        c.restart(container_id)
        # update hipache
        container = Container.objects.get(
            container_id=container_id)
        apps = Application.objects.filter(containers__in=[container])
        for app in apps:
            app.update_config()

    def stop_container(self, container_id=None):
        c = Container.objects.get(container_id=container_id)
        if c.protected:
            raise ProtectedContainerError(
                _('Unable to stop container.  Container is protected.'))
        c = self._get_client()
        c.stop(container_id)

    def get_container_logs(self, container_id=None):
        c = self._get_client()
        return c.logs(container_id)

    def destroy_container(self, container_id=None):
        c = Container.objects.get(container_id=container_id)
        if c.protected:
            raise ProtectedContainerError(
                _('Unable to destroy container.  Container is protected.'))
        c = self._get_client()
        try:
            c.kill(container_id)
            c.remove_container(container_id)
        except client.APIError:
            # ignore 404s from api if container not found
            pass
        # remove metadata
        Container.objects.filter(container_id=container_id).delete()

    def import_image(self, repository=None):
        c = self._get_client()
        c.pull(repository)

    def build_image(self, path=None, tag=None):
        c = self._get_client()
        if path.startswith('http://') or path.startswith('https://') or \
        path.startswith('git://') or path.startswith('github.com/'):
            f = path
        else:
            f = open(path, 'r')
        c.build(f, tag)

    def remove_image(self, image_id=None):
        c = self._get_client()
        c.remove_image(image_id)

    def get_hostname(self):
        # returns public_hostname if available otherwise default
        host = self.hostname
        if self.public_hostname:
            host = self.public_hostname
        return host

    def clone_container(self, container_id=None):
        c = Container.objects.get(container_id=container_id)
        meta = c.get_meta()
        cfg = meta.get('Config')
        image = cfg.get('Image')
        command = ' '.join(cfg.get('Cmd'))
        # update port spec to specify the original NAT'd port
        port_specs = cfg.get('ExposedPorts', {}).keys()
        ports = []
        for p in port_specs:
            ports.append(p.split('/')[0])
        env = cfg.get('Env')
        mem = cfg.get('Memory')
        hostname = cfg.get('Hostname')
        description = c.description
        volumes = cfg.get('Volumes')
        volumes_from = cfg.get('VolumesFrom')
        privileged = cfg.get('Privileged')
        owner = c.owner
        c_id, status = self.create_container(image, command, ports,
            env, mem, description, volumes, volumes_from, privileged, 
            owner=owner, hostname=hostname)
        # mark as protected if needed
        if c.protected:
            container = Container.objects.get(container_id=c_id)
            container.protected = True
            container.save()
        return c_id, status


########NEW FILE########
__FILENAME__ = tests
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User

class HostResourceTest(ResourceTestCase):
    fixtures = ['test_hosts.json']

    def setUp(self):
        super(HostResourceTest, self).setUp()
        self.api_list_url = '/api/v1/hosts/'
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_get_list_unauthorzied(self):
        """
        Test get without key returns unauthorized
        """
        self.assertHttpUnauthorized(self.api_client.get(self.api_list_url,
            format='json'))

    def test_get_list_json(self):
        """
        Test get application list
        """
        resp = self.api_client.get(self.api_list_url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

    def test_get_detail_json(self):
        """
        Test get application details
        """
        url = '{}1/'.format(self.api_list_url)
        resp = self.api_client.get(url, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)
        data = self.deserialize(resp)
        keys = data.keys()
        self.assertTrue('name' in keys)
        self.assertTrue('hostname' in keys)
        self.assertTrue('port' in keys)
        self.assertTrue('enabled' in keys)


########NEW FILE########
__FILENAME__ = urls
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('hosts.views',
    url(r'^$', 'index'),
    url(r'^edit/(?P<host_id>.*)/$', 'edit_host'),
    url(r'^enable/(?P<host_id>.*)/$', 'enable_host'),
    url(r'^disable/(?P<host_id>.*)/$', 'disable_host'),
    url(r'^remove/(?P<host_id>.*)/$', 'remove_host'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext as _
from hosts.models import Host
from hosts.forms import HostForm

@login_required
def index(request):
    hosts = Host.objects.all()
    ctx = {
        'hosts': hosts
    }
    return render_to_response('hosts/index.html', ctx,
        context_instance=RequestContext(request))

@login_required
def add_host(request):
    form = HostForm()
    if request.method == 'POST':
        form = HostForm(request.POST)
        form.owner = request.user
        if form.is_valid():
            form.save()
            return redirect(reverse('hosts.views.index'))
    ctx = {
        'form': form
    }
    return render_to_response('hosts/add_host.html', ctx,
        context_instance=RequestContext(request))

@login_required
def edit_host(request, host_id):
    h = Host.objects.get(id=host_id)
    form = HostForm(instance=h)
    if request.method == 'POST':
        form = HostForm(request.POST, instance=h)
        form.owner = request.user
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, _('Updated') + ' {0}'.format(
                h.name))
            return redirect(reverse('hosts.views.index'))
    ctx = {
        'form': form
    }
    return render_to_response('hosts/edit_host.html', ctx,
        context_instance=RequestContext(request))

@login_required
def enable_host(request, host_id):
    h = Host.objects.get(id=host_id)
    h.enabled = True
    h.save()
    messages.add_message(request, messages.INFO, _('Enabled') + ' {0}'.format(
        h.name))
    return redirect('hosts.views.index')

@login_required
def disable_host(request, host_id):
    h = Host.objects.get(id=host_id)
    h.enabled = False
    h.save()
    messages.add_message(request, messages.INFO, _('Disabled') + ' {0}'.format(
        h.name))
    return redirect('hosts.views.index')

@login_required
def remove_host(request, host_id):
    h = Host.objects.get(id=host_id)
    h.delete()
    messages.add_message(request, messages.INFO, _('Removed') + ' {0}'.format(
        h.name))
    return redirect('hosts.views.index')


########NEW FILE########
__FILENAME__ = admin
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from images.models import Image

class ImageAdmin(admin.ModelAdmin):
    list_display = ('image_id', 'host')
    search_fields = ('image_id', 'host__hostname')

admin.site.register(Image, ImageAdmin)

########NEW FILE########
__FILENAME__ = api
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.bundle import Bundle
from tastypie.authorization import Authorization
from tastypie.authentication import (ApiKeyAuthentication,
    SessionAuthentication, MultiAuthentication)
from django.conf.urls import url
from images.models import Image
from hosts.api import HostResource

class ImageResource(ModelResource):
    host = fields.ToOneField(HostResource, 'host', full=True)
    history = fields.ListField(attribute='get_history')

    class Meta:
        queryset = Image.objects.exclude(repository__contains='none')
        resource_name = 'images'
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        authorization = Authorization()
        authentication = MultiAuthentication(
            ApiKeyAuthentication(), SessionAuthentication())


########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Image'
        db.create_table(u'images_image', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('image_id', self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True)),
            ('repository', self.gf('django.db.models.fields.CharField')(max_length=96)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['hosts.Host'], null=True)),
            ('meta', self.gf('django.db.models.fields.TextField')(default='{}', null=True, blank=True)),
        ))
        db.send_create_signal(u'images', ['Image'])


    def backwards(self, orm):
        # Deleting model 'Image'
        db.delete_table(u'images_image')


    models = {
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'agent_key': ('django.db.models.fields.CharField', [], {'default': "'aabe70f9ac4743ec85def7b760540f55'", 'max_length': '64', 'null': 'True'}),
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        u'images.image': {
            'Meta': {'object_name': 'Image'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hosts.Host']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'meta': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'repository': ('django.db.models.fields.CharField', [], {'max_length': '96'})
        }
    }

    complete_apps = ['images']
########NEW FILE########
__FILENAME__ = 0002_auto__del_field_image_meta__add_field_image_history
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Image.meta'
        db.delete_column(u'images_image', 'meta')

        # Adding field 'Image.history'
        db.add_column(u'images_image', 'history',
                      self.gf('django.db.models.fields.TextField')(default='{}', null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Image.meta'
        db.add_column(u'images_image', 'meta',
                      self.gf('django.db.models.fields.TextField')(default='{}', null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Image.history'
        db.delete_column(u'images_image', 'history')


    models = {
        u'hosts.host': {
            'Meta': {'object_name': 'Host'},
            'agent_key': ('django.db.models.fields.CharField', [], {'default': "'4db8e9f201f54e33ad16320e2ba5d485'", 'max_length': '64', 'null': 'True'}),
            'enabled': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'default': '4243', 'null': 'True'}),
            'public_hostname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        u'images.image': {
            'Meta': {'object_name': 'Image'},
            'history': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hosts.Host']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'repository': ('django.db.models.fields.CharField', [], {'max_length': '96'})
        }
    }

    complete_apps = ['images']
########NEW FILE########
__FILENAME__ = models
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models
from hosts.models import Host
import json

class Image(models.Model):
    image_id = models.CharField(max_length=96, null=True, blank=True)
    repository = models.CharField(max_length=96)
    host = models.ForeignKey(Host, null=True)
    history = models.TextField(blank=True, null=True, default='{}')

    def __unicode__(self):
        img_id = 'unknown'
        if self.image_id:
            img_id = self.image_id[:12]
        return "{} ({})".format(self.repository, img_id)

    def get_history(self):
        history = {}
        if self.history:
            history = json.loads(self.history)
        return history


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
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('images.views',
    url(r'^$', 'index'),
    url(r'^remove/(?P<host_id>.*)/(?P<image_id>.*)/$',
        'remove_image'),
    url(r'^refresh/$', 'refresh'),
    url(r'^import/$', 'import_image'),
    url(r'^build/$', 'build_image'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext as _
from hosts.models import Host
from images.models import Image
from shipyard import tasks

@login_required
def index(request):
    hosts = Host.objects.filter(enabled=True)
    images = Image.objects.filter(host__in=hosts).exclude(repository__contains='<none>').order_by('repository')
    ctx = {
        'images': images
    }
    return render_to_response('images/index.html', ctx,
        context_instance=RequestContext(request))

@login_required
def remove_image(request, host_id, image_id):
    h = Host.objects.get(id=host_id)
    h.remove_image(image_id)
    messages.add_message(request, messages.INFO, _('Removed') + ' {}'.format(
        image_id))
    return redirect('images.views.index')

@login_required
def refresh(request):
    '''
    Invalidates host cache and redirects to images view

    '''
    for h in Host.objects.filter(enabled=True):
        h._invalidate_image_cache()
    return redirect('images.views.index')

@login_required
def import_image(request):
    repo = request.POST.get('repo_name')
    if repo:
        tasks.import_image.delay(repo)
        messages.add_message(request, messages.INFO, _('Importing') + \
            ' {}'.format(repo) + _('.  This could take a few minutes.'))
    return redirect('images.views.index')

@login_required
def build_image(request):
    path = request.POST.get('path')
    tag = request.POST.get('tag', None)
    if path:
        tasks.build_image.delay(path, tag)
        messages.add_message(request, messages.INFO, _('Building.  This ' \
            'could take a few minutes.'))
    return redirect('images.views.index')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shipyard.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Metric'
        db.create_table(u'metrics_metric', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('metric_type', self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True)),
            ('counter', self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True)),
            ('value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('unit', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal(u'metrics', ['Metric'])


    def backwards(self, orm):
        # Deleting model 'Metric'
        db.delete_table(u'metrics_metric')


    models = {
        u'metrics.metric': {
            'Meta': {'object_name': 'Metric'},
            'counter': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric_type': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['metrics']
########NEW FILE########
__FILENAME__ = models
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models

class Metric(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    metric_type = models.CharField(max_length=96, null=True, blank=True)
    source = models.CharField(max_length=96, null=True, blank=True)
    counter = models.CharField(max_length=96, null=True, blank=True)
    value = models.IntegerField(null=True, blank=True)
    unit = models.CharField(max_length=64, null=True, blank=True)

    def __unicode__(self):
        return '{}: {} {} {}'.format(self.metric_type, self.counter, self.value,
                self.unit)

    def unix_timestamp(self):
        return int(self.timestamp.strftime('%s'))

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

# Create your tests here.

########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
from django.shortcuts import render


########NEW FILE########
__FILENAME__ = context_processors
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf import settings

def app_name(context):
    return { 'APP_NAME': getattr(settings, 'APP_NAME', 'Unknown')}

def app_revision(context):
    return { 'APP_REVISION': getattr(settings, 'APP_REVISION', 'Unknown')}

def google_analytics_code(context):
    return { 'GOOGLE_ANALYTICS_CODE': getattr(settings, 'GOOGLE_ANALYTICS_CODE', None)}

########NEW FILE########
__FILENAME__ = exceptions
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class ProtectedContainerError(Exception):
    pass

class RecoveryThresholdError(Exception):
    pass

########NEW FILE########
__FILENAME__ = create_api_keys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from optparse import make_option

class Command(BaseCommand):
    help = 'Creates missing API keys for users'

    def handle(self, *args, **options):
        from tastypie.models import ApiKey
        users = User.objects.all()
        for user in users:
            try:
                key = user.api_key
            except ApiKey.DoesNotExist:
                print('Creating API key for {}'.format(user.username))
                k = ApiKey()
                k.user = user
                k.save()

########NEW FILE########
__FILENAME__ = update_admin_user
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from optparse import make_option

class Command(BaseCommand):
    help = 'Creates/Updates an Admin user'
    option_list = BaseCommand.option_list + (
        make_option('--username',
            action='store',
            dest='username',
            default=None,
            help='Admin username'),
        ) + (
        make_option('--password',
            action='store',
            dest='password',
            default=None,
            help='Admin password'),
        )

    def handle(self, *args, **options):
        username = options.get('username')
        password = options.get('password')
        if not username or not password:
            raise StandardError('You must specify a username and password')
        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('{0} updated'.format(username))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Django settings for shipyard project.
import os
import subprocess
from datetime import timedelta
from django.contrib.messages import constants as messages
import sys
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '../')

DEBUG = True
TEMPLATE_DEBUG = DEBUG
APP_NAME = 'shipyard'
TESTING = sys.argv[1:2] == ['test']
# app rev
try:
    p = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    APP_REVISION = out[:6]
except OSError:
    APP_REVISION = 'unknown'
GOOGLE_ANALYTICS_CODE = os.environ.get('GOOGLE_ANALYTICS_CODE', None)

ADMINS = (
    #('Admin', 'admin@local.net'),
)

AUTH_PROFILE_MODULE = 'accounts.UserProfile'

MANAGERS = ADMINS

# cache settings
HOST_CACHE_TTL = 30 # seconds to cache container lookup

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'shipyard.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = os.getenv('REDIS_DB', 0)
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
# check for fig
if os.environ.has_key('SHIPYARD_REDIS_1_PORT_6379_TCP_ADDR'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'shipyard',
            'USER': 'shipyard',
            'PASSWORD': 'shipyard',
            'HOST': os.getenv('SHIPYARD_DB_1_PORT_5432_TCP_ADDR'),
            'PORT': int(os.getenv('SHIPYARD_DB_1_PORT_5432_TCP_PORT')),
        }
    }
    REDIS_HOST = os.getenv('SHIPYARD_REDIS_1_PORT_6379_TCP_ADDR')
    REDIS_PORT = int(os.getenv('SHIPYARD_REDIS_1_PORT_6379_TCP_PORT'))
    DEBUG = True

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts

# NOTE: this is a wildcard to help with deployments ; please make sure
# to update to your own if you wish to tighten security
ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

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
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = 'static_root'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'd%iskx#4q%jky6@j!8jk*u)9=2b7mmyz5_8(2i895ulbpk+8ou'

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

ROOT_URLCONF = 'shipyard.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'shipyard.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "shipyard.context_processors.app_name",
    "shipyard.context_processors.app_revision",
    "shipyard.context_processors.google_analytics_code",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'south',
    'djcelery',
    'crispy_forms',
    'tastypie',
    'shipyard',
    'agent',
    'accounts',
    'hosts',
    'containers',
    'applications',
    'images',
    'metrics',
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

CRISPY_TEMPLATE_PACK = 'bootstrap3'
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

# amount of time in seconds to check protected containers
RECOVERY_INTERVAL = int(os.getenv('RECOVERY_INTERVAL', 15))
# number of times to restart a container before aborting
RECOVERY_THRESHOLD = int(os.getenv('RECOVERY_THRESHOLD', 3))
# amount of time in seconds to allow for recovery.  if the container
# goes past the number in RECOVERY_THRESHOLD in this time span
# the container an exception will be raised and it won't be attempted
# to be recovered
RECOVERY_TIME = 60

HIPACHE_ENABLED = not TESTING
CELERY_TIMEZONE = 'UTC'

try:
    from local_settings import *
except ImportError:
    pass

CACHES = {
    "default": {
        "BACKEND": "redis_cache.cache.RedisCache",
        "LOCATION": "{}:{}:{}".format(REDIS_HOST, REDIS_PORT, REDIS_DB),
        "OPTIONS": {
            "CLIENT_CLASS": "redis_cache.client.DefaultClient",
        }
    }
}
# enable the hipache load balancer integration (needed for applications)
HIPACHE_REDIS_HOST = REDIS_HOST
HIPACHE_REDIS_PORT = REDIS_PORT
BROKER_URL = 'redis://'
if REDIS_PASSWORD:
    BROKER_URL += ':{}@'.format(REDIS_PASSWORD)
BROKER_URL += '{}:{}/{}'.format(REDIS_HOST, REDIS_PORT, REDIS_DB)

# celery scheduled tasks
CELERYBEAT_SCHEDULE = {
    'recover_containers': {
        'task': 'shipyard.tasks.recover_containers',
        'schedule': timedelta(seconds=RECOVERY_INTERVAL),
    }
}

# ssl
if os.getenv('FORCE_SSL'):
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
    CSRF_COOKIE_SECURE = True

import djcelery
djcelery.setup_loader()

########NEW FILE########
__FILENAME__ = tasks
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import celery
from django.core.cache import cache
from django.conf import settings
from django.utils.translation import ugettext as _
from containers.models import Container
from hosts.models import Host
from exceptions import RecoveryThresholdError
import utils
import hashlib

@celery.task
def import_image(repo_name=None):
    if not repo_name:
        raise StandardError('You must specify a repo name')
    hosts = Host.objects.filter(enabled=True)
    for h in hosts:
        import_image_to_host.subtask((h, repo_name)).apply_async()
    return True

@celery.task
def import_image_to_host(host, repo_name):
    if not host or not repo_name:
        raise StandardError('You must specify a host and repo name')
    print('Importing {} on {}'.format(repo_name, host.name))
    host.import_image(repo_name)
    return 'Imported {} on {}'.format(repo_name, host.name)

@celery.task
def build_image(path=None, tag=None):
    if not path:
        raise StandardError('You must specify a path')
    hosts = Host.objects.filter(enabled=True)
    for h in hosts:
        build_image_on_host.subtask((h, path, tag)).apply_async()
    return True

@celery.task
def build_image_on_host(host, path, tag):
    if not host or not path:
        raise StandardError('You must specify a host and path')
    print('Building {} on {}'.format(tag, host.name))
    host.build_image(path, tag)
    return 'Built {} on {}'.format(tag, host.name)

@celery.task
def docker_host_info():
    hosts = Host.objects.filter(enabled=True)
    for h in hosts:
        get_docker_host_info.subtask((h.id,)).apply_async()
    return True

@celery.task
def recover_containers():
    protected_containers = Container.objects.filter(protected=True).exclude(
            is_running=True)
    for c in protected_containers:
        host = c.host
        print('Recovering {}'.format(c.get_name()))
        c_id, status = host.clone_container(c.container_id)
        # update container info
        host._load_container_data(c_id)
        import time
        time.sleep(5)
        new_c = Container.objects.get(container_id=c_id)
        # update app
        for app in c.get_applications():
            app.containers.remove(c)
            app.containers.add(new_c)
            app.save()


########NEW FILE########
__FILENAME__ = shipyard
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.translation import ugettext as _
from hosts.models import Host
from datetime import datetime

register = template.Library()

@register.filter
def container_status(value):
    """
    Returns container status as a bootstrap class

    """
    cls = ''
    if value:
        if value.get('Running'):
            cls = 'success'
        elif value.get('ExitCode') == 0:
            cls = 'info'
        else:
            cls = 'important'
    return cls

@register.filter
def container_uptime(value):
    """
    Returns container uptime from date stamp

    """
    if value:
        try:
            tz = value.split('.')[-1]
            ts = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.' + tz)
            return datetime.utcnow().replace(microsecond=0) - ts
        except:
            return ''
    return value

@register.filter
def container_port_link(port, host):
    """
    Returns container port as link

    :param port: Container port
    :param host: Container host name

    """
    ret = port
    if port:
        host = Host.objects.get(name=host)
        host_url = host.hostname
        if 'unix' in host.hostname:
            host_url = '127.0.0.1'
        link = '<a href="http://{0}:{1}" target="_blank">{1}</a>'.format(
            host_url, port)
        ret = link
    return ret

@register.filter
def container_host_url(interface, hostname):
    """
    Returns exposed interface URL, replacing default 0.0.0.0
    with container hostname as url

    :param interface: Port interface
    :param hostname: Container host name

    """
    if interface == '0.0.0.0':
        if 'unix' in hostname:
            host_url = '127.0.0.1'
        else:
            host_url = hostname
    else:
        host_url = interface
    return 'http://{0}'.format(host_url)

@register.filter
@stringfilter
def container_memory_to_mb(value):
    """
    Returns container memory as MB

    """
    if value.strip() and int(value) != 0:
        return '{0} MB'.format(int(value) / 1048576)
    else:
        return _('unlimited')

@register.filter
@stringfilter
def container_cpu(value):
    """
    Returns container memory as MB

    """
    if value.strip() and int(value) != 0:
        return '{}%'.format(value)
    else:
        return _('unlimited')

@register.filter()
def split(value, arg):
    return value.split(arg)

@register.filter()
def get_short_id(value):
    return value[:12]

########NEW FILE########
__FILENAME__ = urls
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, include, url
from tastypie.api import Api
from django.contrib import admin
admin.autodiscover()

from containers.api import ContainerResource
from applications.api import ApplicationResource
from hosts.api import HostResource
from images.api import ImageResource

v1_api = Api(api_name='v1')
v1_api.register(ContainerResource())
v1_api.register(ApplicationResource())
v1_api.register(HostResource())
v1_api.register(ImageResource())

urlpatterns = patterns('',
    url(r'^$', 'shipyard.views.index', name='index'),
    url(r'^api/login', 'accounts.views.api_login', name='api_login'),
    url(r'^api/', include(v1_api.urls)),
    url(r'^agent/', include('agent.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^applications/', include('applications.urls')),
    url(r'^containers/', include('containers.urls')),
    url(r'^images/', include('images.urls')),
    url(r'^hosts/', include('hosts.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = utils
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from ansi2html import Ansi2HTMLConverter
from django.conf import settings
from hashlib import md5
import redis
import uuid


def get_short_id(container_id):
    return container_id[:12]

def convert_ansi_to_html(text, full=False):
    converted = ''
    try:
        conv = Ansi2HTMLConverter(markup_lines=True, linkify=False, escaped=False)
        converted = conv.convert(text.replace('\n', ' <br/>'), full=full)
    except Exception, e:
        converted = text
    return converted

def generate_console_session(host, container):
    session_id = md5(str(uuid.uuid4())).hexdigest()
    
    redis_host = getattr(settings, 'HIPACHE_REDIS_HOST')
    redis_port = getattr(settings, 'HIPACHE_REDIS_PORT')
    rds = redis.Redis(host=redis_host, port=redis_port)
    
    key = 'console:{0}'.format(session_id)
    docker_host = '{0}:{1}'.format(host.hostname, host.port)
    attach_path = '/v1.8/containers/{0}/attach/ws'.format(container.container_id)

    rds.hmset(key, { 'host': docker_host, 'path': attach_path })
    rds.expire(key, 120)
    return session_id

def update_hipache(app_id=None):
    from applications.models import Application
    if getattr(settings, 'HIPACHE_ENABLED'):
        app = Application.objects.get(id=app_id)
        redis_host = getattr(settings, 'HIPACHE_REDIS_HOST')
        redis_port = getattr(settings, 'HIPACHE_REDIS_PORT')
        rds = redis.Redis(host=redis_host, port=redis_port)
        with rds.pipeline() as pipe:
            domain_key = 'frontend:{0}'.format(app.domain_name)
            # remove existing
            pipe.delete(domain_key)
            pipe.rpush(domain_key, app.id)
            # add upstreams
            for c in app.containers.all():
                port_proto = "{0}/tcp".format(app.backend_port)
                host_interface = app.host_interface or '0.0.0.0'
                hostname = c.host.public_hostname or \
                        c.host.hostname if host_interface == '0.0.0.0' else \
                        host_interface
                # check for unix socket
                port = c.get_ports()[port_proto][host_interface]
                upstream = '{0}://{1}:{2}'.format(app.protocol, hostname, port)
                pipe.rpush(domain_key, upstream)
            pipe.execute()
            return True
    return False

def remove_hipache_config(domain_name=None):
    if getattr(settings, 'HIPACHE_ENABLED'):
        redis_host = getattr(settings, 'HIPACHE_REDIS_HOST')
        redis_port = getattr(settings, 'HIPACHE_REDIS_PORT')
        rds = redis.Redis(host=redis_host, port=redis_port)
        domain_key = 'frontend:{0}'.format(domain_name)
        # remove existing
        rds.delete(domain_key)


########NEW FILE########
__FILENAME__ = views
# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import HttpResponse

def index(request):
    if not request.user.is_authenticated():
        return redirect(reverse('accounts.views.login'))
    else:
        return redirect(reverse('containers.views.index'))

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for shipyard project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "shipyard.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shipyard.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = wsgi
from shipyard import wsgi
#import newrelic.agent
application = wsgi.application

#newrelic.agent.initialize('newrelic.ini')
#app = newrelic.agent.wsgi_application()(app)

########NEW FILE########
