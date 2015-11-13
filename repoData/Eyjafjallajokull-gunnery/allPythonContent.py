__FILENAME__ = backend

from django.contrib.auth import get_user_model

_user = get_user_model()


class EmailAuthBackend(object):
    """
    Email Authentication Backend
    
    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
    """

    def authenticate(self, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        try:
            user = _user.objects.get(email=username)
            if user.check_password(password):
                return user
        except _user.DoesNotExist:
            return None

    def get_user(self, user_id):
        """ Get a _user object from the user_id. """
        try:
            return _user.objects.get(pk=user_id)
        except _user.DoesNotExist:
            return None
########NEW FILE########
__FILENAME__ = decorators
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.db.models import get_model
from django.utils.encoding import force_str
from django.utils.six.moves.urllib.parse import urlparse
from django.shortcuts import resolve_url
from django.utils.decorators import available_attrs


def _has_permissions(user, model_name, model_id):
    model = get_model(*model_name.split('.'))
    model.id = model_id
    if model_name == 'core.Department':
        department = model
    elif model_name == 'core.Application':
        department = model.objects.get(pk=model_id).department
    elif model_name == 'core.Server':
        department = model.objects.get(pk=model_id).environment.application.department
    elif model_name == 'task.Execution':
        department = model.objects.get(pk=model_id).environment.application.department
    elif model_name == 'core.Environment':
        department = model.objects.get(pk=model_id).application.department
    elif model_name == 'task.Task':
        department = model.objects.get(pk=model_id).application.department
    else:
        raise RuntimeError('Unknown model')
    return user.has_perm('core.view_department', department)


def _auto_resolve_parameter_name(parameters):
    if len(parameters.keys()) == 0:
        raise RuntimeError('No parameters')
    if len(parameters.keys()) > 1:
        raise RuntimeError('Too many parameters, specify parameter name for has_permissions decorator')
    return parameters.keys()[0]


def has_permissions(model, id_parameter=None):
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if not id_parameter:
                id_parameter_name = _auto_resolve_parameter_name(kwargs)
            else:
                id_parameter_name = id_parameter
            if _has_permissions(request.user, model, kwargs[id_parameter_name]):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            # urlparse chokes on lazy objects in Python 3, force to str
            resolved_login_url = force_str(
                resolve_url(settings.LOGIN_URL))
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            messages.error(request, 'Access forbidden')
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, resolved_login_url, REDIRECT_FIELD_NAME)
        return _wrapped_view
    return decorator
########NEW FILE########
__FILENAME__ = forms
from django.forms import BooleanField, CharField, PasswordInput
from django.contrib.auth import get_user_model

from core.forms import ModalForm, create_form


_user = get_user_model()


class UserForm(ModalForm):
    email = CharField(required=True)
    password = CharField(widget=PasswordInput(render_value=False), required=False, min_length=8)
    name = CharField(label='Name')

    class Meta:
        model = _user
        fields = ['email', 'password', 'name']


class UserSystemForm(ModalForm):
    email = CharField(required=True)
    password = CharField(widget=PasswordInput(render_value=False), required=False, min_length=8)
    name = CharField(label='Name')
    is_superuser = BooleanField(required=False)

    class Meta:
        model = _user
        fields = ['email', 'password', 'name', 'is_superuser']


class UserProfileForm(ModalForm):
    email = CharField(required=True)
    name = CharField(label='Name')

    class Meta:
        model = _user
        fields = ['email', 'name']


class UserPasswordForm(ModalForm):
    password = CharField(widget=PasswordInput(render_value=False), required=False, min_length=8)
    password2 = CharField(widget=PasswordInput(render_value=False), required=False, min_length=8,
                          label="Repeat password")

    class Meta:
        model = _user
        fields = ['password']

    def is_valid(self):
        valid = super(UserPasswordForm, self).is_valid()
        if not valid:
            return valid
        if self.cleaned_data['password'] != self.cleaned_data['password2']:
            self._errors['not_match'] = 'Passwords do not match'
            return False
        return True


def account_create_form(name, request, id, args={}):
    form_objects = {
        'user': UserForm if not request.user.is_superuser else UserSystemForm,
        'user_profile': UserProfileForm,
        'user_password': UserPasswordForm
    }
    return create_form(form_objects, name, request, id, args)
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CustomUser'
        db.create_table(u'account_customuser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=254)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'account', ['CustomUser'])

        # Adding M2M table for field groups on 'CustomUser'
        m2m_table_name = db.shorten_name(u'account_customuser_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('customuser', models.ForeignKey(orm[u'account.customuser'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(m2m_table_name, ['customuser_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'CustomUser'
        m2m_table_name = db.shorten_name(u'account_customuser_user_permissions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('customuser', models.ForeignKey(orm[u'account.customuser'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(m2m_table_name, ['customuser_id', 'permission_id'])


    def backwards(self, orm):
        # Deleting model 'CustomUser'
        db.delete_table(u'account_customuser')

        # Removing M2M table for field groups on 'CustomUser'
        db.delete_table(db.shorten_name(u'account_customuser_groups'))

        # Removing M2M table for field user_permissions on 'CustomUser'
        db.delete_table(db.shorten_name(u'account_customuser_user_permissions'))


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['account']
########NEW FILE########
__FILENAME__ = 0002_auto__del_field_customuser_is_staff
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'CustomUser.is_staff'
        db.delete_column(u'account_customuser', 'is_staff')


    def backwards(self, orm):
        # Adding field 'CustomUser.is_staff'
        db.add_column(u'account_customuser', 'is_staff',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['account']
########NEW FILE########
__FILENAME__ = modal
from django.contrib.auth import get_user_model

from core.modal import BaseModal
from .forms import account_create_form, UserForm


_user = get_user_model()


class Modal(BaseModal):
    definitions = {
        'user': {
            'form': UserForm,
            'parent': None
        }
    }

    def get_form_creator(self):
        return account_create_form

    def on_form_create_user(self):
        if not self.form.instance.id:
            self.form.fields['password'].required = True

    def on_update_user(self):
        self.instance.save()

    def on_before_save_user(self):
        instance = self.form.instance
        instance.username = instance.email
        if len(instance.password):
            instance.set_password(instance.password)
        else:
            instance.password = _user.objects.get(pk=instance.id).password

    def on_create_user(self):
        self.instance.save()
        from guardian.shortcuts import assign_perm
        from core.models import Department
        assign_perm('core.view_department', self.instance, Department(id=self.request.current_department_id))

    def on_view_user(self):
        self.data['model_name'] = 'User'
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class CustomUserManager(BaseUserManager):
    def _create_user(self, email, password,
                     is_superuser, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, is_active=True,
                          is_superuser=is_superuser, last_login=now,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return self._create_user(email, password, False, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email, password, True, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    A fully featured User model with admin-compliant permissions that uses
    a full-length email field as the username.

    Email and password are required. Other fields are optional.
    """
    email = models.EmailField(_('email address'), max_length=254, unique=True)
    name = models.CharField(_('first name'), max_length=30, blank=True)
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this user should be treated as '
                                                'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_absolute_url(self):
        return "/account/profile/%d/" % self.id

    def get_full_name(self):
        if self.name:
            return self.name
        else:
            return self.email

    def get_short_name(self):
        return self.name

    def email_user(self, subject, message, from_email=None):
        send_mail(subject, message, from_email, [self.email])


########NEW FILE########
__FILENAME__ = fixtures
from factory.django import DjangoModelFactory
import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password


class UserFactory(DjangoModelFactory):
    FACTORY_FOR = get_user_model()

    email = factory.Sequence(lambda n: 'account%s@test.com' % n)
    name = factory.Sequence(lambda n: 'John Doe %s' % n)
    password = factory.LazyAttribute(lambda o: make_password(o.email))
    is_superuser = False
########NEW FILE########
__FILENAME__ = test_views
from django.test import TestCase
from account.tests.fixtures import UserFactory

from core.tests.base import LoggedTestCase, BaseModalTestCase, BaseModalTests


class GuestTest(TestCase):
    def test_login(self):
        response = self.client.get('/account/login/')
        self.assertContains(response, 'Please Sign In')


class CoreModalUserTest(BaseModalTestCase, BaseModalTests):
    object_factory = UserFactory

    @property
    def url(self):
        return '/modal_form/a:account/user/'
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from views import modal_permissions, profile_page


urlpatterns = patterns('',
    url(r'^account/profile/(?P<user_id>[\d]+)/$', profile_page, name='profile'),
    url(r'^account/login/$', 'django.contrib.auth.views.login', {'template_name': 'page/login.html'}),
    url(r'^account/logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),
    url(r'^account/password_reset/$', 'django.contrib.auth.views.password_reset', name='password_reset'),
    url(r'^account/password_reset_done$', 'django.contrib.auth.views.password_reset_done',
       name='password_reset_done'),
    url(r'^account/password_reset_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$',
       'django.contrib.auth.views.password_reset_confirm', name='password_reset_confirm'),
    url(r'^account/password_reset_complete$', 'django.contrib.auth.views.password_reset_complete',
       name='password_reset_complete'),
    url(r'^modal/permissions/(?P<user_id>[\d]+)/$', modal_permissions, name='modal_permissions'),
)
########NEW FILE########
__FILENAME__ = views
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render

from core.views import get_common_page_data
from task.models import Execution
from core.models import Department


def login(request, *args, **kwargs):
    if request.method == 'POST':
        if not request.POST.get('remember', None):
            request.session.set_expiry(0)
    return views.login(request, *args, **kwargs)


@login_required
def profile_page(request, user_id):
    data = get_common_page_data(request)
    user = get_object_or_404(get_user_model(), pk=user_id)
    data['user_profile'] = user
    data['user_executions'] = Execution.get_inline_by_user(user.id)
    return render(request, 'page/profile.html', data)


def on_before_save_user(instance):
    if len(instance.password):
        instance.set_password(instance.password)
    else:
        instance.password = get_user_model().objects.get(pk=instance.id).password

@user_passes_test(lambda u: u.is_superuser)
def modal_permissions(request, user_id):
    user = get_object_or_404(get_user_model(), pk=user_id)
    data = get_common_page_data(request)
    data['user'] = user
    data['form_template'] = 'partial/permissions_form.html'
    data['model_name'] = '%s permissions' % user.name
    data['is_new'] = False
    data['no_delete'] = True
    data['request_path'] = request.path

    data['departments'] = Department.objects.all()

    from core.models import Application, Environment
    from task.models import Task

    models = {
        'department': Department,
        'application': Application,
        'environment': Environment,
        'task': Task,
    }
    if request.method == 'POST':
        from guardian.models import UserObjectPermission
        from guardian.shortcuts import assign_perm

        UserObjectPermission.objects.filter(user_id=user.id).delete()
        for name, value in request.POST.items():
            key = name.split('_')
            if len(key) == 3 and value == 'on':
                action, model, pk = key
                assign_perm('%s_%s' % (action, model), user, models[model].objects.get(pk=pk))
        return render(request, data['form_template'], data)
    else:
        return render(request, 'partial/modal_form.html', data)

########NEW FILE########
__FILENAME__ = securefile
from subprocess import Popen, PIPE, STDOUT
from hashlib import md5
from django.conf import settings
import os


class SecureFileStorage(object):
    """ Handler for storing SSH keys per environment """

    def __init__(self, uid):
        self.files = {
            'private_key': PrivateKey(uid),
            'public_key': PublicKey(uid),
            'known_hosts': KnownHosts(uid),
        }

    def __getattr__(self, name):
        return self.files[name]

    def remove(self):
        for _, secure_file in self.files.items():
            secure_file.remove()


class SecureFile(object):
    """ Base class for secure file """
    prefix = ''

    def __init__(self, uid):
        if isinstance(uid, int):
            uid = str(uid)
        self.uid = uid
        name_hash = md5(settings.SECRET_KEY + self.prefix + uid).hexdigest()
        self.file_name = os.path.join(settings.PRIVATE_DIR, name_hash)

    # if not os.path.exists(self.file_name):
    # 	open(self.file_name, 'w')
    # 	os.chmod(self.file_name, 0700)

    def get_file_name(self):
        return self.file_name

    def read(self):
        return open(self.file_name, 'r').read()

    def remove(self):
        try:
            os.remove(self.file_name)
        except OSError:
            pass


class PrivateKey(SecureFile):
    """ Private key handler """
    prefix = 'private_key'

    def generate(self, comment, remove=True):
        """ Generates private and public key files """
        if remove:
            Popen(['/bin/rm', '-f', self.get_file_name()]).communicate()

        command = 'ssh-keygen -f %s -C %s -N \'\'' % (self.get_file_name(), comment)
        process = Popen(command,
                        shell=True,
                        stdout=PIPE,
                        stderr=STDOUT)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise RuntimeError('%s failed with code %d' % (command, process.returncode))

        command = 'mv %s.pub %s' % (self.get_file_name(), PublicKey(self.uid).get_file_name())
        process = Popen(command,
                        shell=True,
                        stdout=PIPE,
                        stderr=STDOUT)
        stdout, stderr = process.communicate()


class PublicKey(SecureFile):
    """ Public key handler """
    prefix = 'public_key'


class KnownHosts(SecureFile):
    """ Known hosts file key handler """
    prefix = 'known_hosts'

########NEW FILE########
__FILENAME__ = ssh
import select
from paramiko import RSAKey, SSHClient, AutoAddPolicy
from .securefile import SecureFileStorage


class Transport(object):
    def __init__(self, server):
        self.server = server
        self.callback = lambda out: None

    def set_stdout_callback(self, callback):
        self.callback = callback


class SSHTransport(Transport):
    output_timeout = 0.5
    output_buffer = 1024

    def __init__(self, server):
        super(SSHTransport, self).__init__(server)
        self.secure_files = SecureFileStorage(self.server.environment_id)
        self.client = self.create_client()
        self.channel = None

    def run(self, command):
        self.channel = self.client.get_transport().open_session()
        self.channel.get_pty()
        self.channel.exec_command(command)
        while True:
            rl, _, _ = select.select([self.channel], [], [], self.output_timeout)
            if len(rl) > 0:
                output = self.channel.recv(self.output_buffer)
                if output:
                    self.callback(output)
                else:
                    break
        return self.channel.recv_exit_status()

    def create_client(self):
        private = RSAKey(filename=self.get_private_key_file())
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.load_host_keys(self.get_host_keys_file())
        client.connect(self.server.host, pkey=private, look_for_keys=False, port=self.server.port, username=self.server.user)
        return client

    def close_client(self):
        self.client.save_host_keys(self.get_host_keys_file())
        self.channel.close()
        self.client.close()

    def kill(self):
        self.close_client()

    def get_host_keys_file(self):
        return self.secure_files.known_hosts.get_file_name()

    def get_private_key_file(self):
        return self.secure_files.private_key.get_file_name()


class Server(object):
    def __init__(self):
        self.environment_id = None
        self.host = None
        self.port = None
        self.user = None
        self.authentication_method = 'key'

    @staticmethod
    def from_model(model):
        instance = Server()
        instance.environment_id = model.environment_id
        instance.host = model.host
        instance.port = model.port
        instance.user = model.user
        return instance

########NEW FILE########
__FILENAME__ = tasks
from _socket import gaierror, error as socket_error
import logging

from django.conf import settings


from celery import chain, chord
from celery.exceptions import SoftTimeLimitExceeded
from paramiko import AuthenticationException

from gunnery.celery import app
from core.models import Environment, Server
from task.models import Execution, ExecutionLiveLog, ExecutionCommandServer
from .securefile import PrivateKey, PublicKey, KnownHosts, SecureFileStorage
import ssh

logger = logging.getLogger(__name__)


@app.task
def _dummy_callback(*args, **kwargs):
    return


@app.task
def generate_private_key(environment_id):
    """ Generate publi and private key pair for environment """
    environment = Environment.objects.get(pk=environment_id)
    PrivateKey(environment_id).generate('Gunnery-' + environment.application.name + '-' + environment.name)
    open(KnownHosts(environment_id).get_file_name(), 'w').close()


@app.task
def read_public_key(environment_id):
    """ Return public key contents """
    environment = Environment.objects.get(pk=environment_id)
    return PublicKey(environment_id).read()


@app.task
def cleanup_files(environment_id):
    """ Remove public, private and host keys for envirionment """
    SecureFileStorage(environment_id).remove()


class ExecutionTask(app.Task):
    def __init__(self):
        pass

    def run(self, execution_id):
        execution = self._get_execution(execution_id)
        if execution.status == Execution.ABORTED:
            return
        execution.celery_task_id = self.request.id
        execution.save_start()

        ExecutionLiveLog.add(execution_id, 'execution_started', status=execution.status, time_start=execution.time_start)

        chord_chain = []
        for command in execution.commands_ordered():
            tasks = [CommandTask().si(execution_command_server_id=server.id) for server in command.servers.all()]
            if len(tasks):
                chord_chain.append(chord(tasks, _dummy_callback.s()))
        chord_chain.append(ExecutionTaskFinish().si(execution_id))
        chain(chord_chain)()

    def _get_execution(self, execution_id):
        return Execution.objects.get(pk=execution_id)


class ExecutionTaskFinish(app.Task):
    def run(self, execution_id):
        execution = self._get_execution(execution_id)
        if execution.status == Execution.ABORTED:
            return
        failed = False
        for command in execution.commands.all():
            for server in command.servers.all():
                if server.status in [None, server.FAILED]:
                    failed = True
        if failed:
            execution.status = execution.FAILED
        else:
            execution.status = execution.SUCCESS
        execution.save_end()
        ExecutionLiveLog.add(execution_id, 'execution_completed',
                             status=execution.status,
                             time_end=execution.time_end,
                             time=execution.time)

    def _get_execution(self, execution_id):
        return Execution.objects.get(pk=execution_id)


class SoftAbort(Exception):
    pass


class CommandTask(app.Task):
    def __init__(self):
        self.ecs = None
        self.environment_id = None
        self.execution_id = None

    def run(self, execution_command_server_id):
        self._attach_abort_signal()
        self.setup(execution_command_server_id)
        self.execute()
        self.finalize()

    def _attach_abort_signal(self):
        import signal
        signal.signal(signal.SIGALRM, self._sigalrm_handler)

    def _sigalrm_handler(self, signum, frame):
        raise SoftAbort

    def setup(self, execution_command_server_id):
        self.ecs = ExecutionCommandServer.objects.get(pk=execution_command_server_id)
        if self.ecs.execution_command.execution.status == Execution.ABORTED:
            return
        self.ecs.celery_task_id = self.request.id
        self.ecs.save_start()
        execution = self.ecs.execution_command.execution
        self.environment_id = execution.environment.id
        self.execution_id = execution.id
        ExecutionLiveLog.add(self.execution_id, 'command_started', command_server_id=self.ecs.id)

    def execute(self):
        transport = None
        try:
            transport = self.create_transport()
            self.ecs.return_code = transport.run(self.ecs.execution_command.command)
        except AuthenticationException:
            self._output_callback('Key authentication failed')
            self.ecs.return_code = 1026
        except gaierror:
            self._output_callback('Name or service not known')
            self.ecs.return_code = 1027
        except socket_error:
            self._output_callback('Socket error')
            self.ecs.return_code = 1028
        except SoftTimeLimitExceeded:
            line = 'Command failed to finish within time limit (%ds)' % settings.CELERYD_TASK_SOFT_TIME_LIMIT
            self._output_callback(line)
            self.ecs.return_code = 1029
        except SoftAbort:
            if transport:
                logger.info(transport)
                transport.kill()
            self._output_callback('Command execution interrupted by user.')
            self.ecs.return_code = 1025
        except Exception as e:
            logger.error(str(type(e)) + str(e))
            self._output_callback('Unknown error')
            self.ecs.return_code = 1024

    def create_transport(self):
        server = ssh.Server.from_model(self.ecs.server)
        transport = ssh.SSHTransport(server)
        transport.set_stdout_callback(self._output_callback)
        return transport

    def _output_callback(self, output):
        self.ecs.output += output
        ExecutionLiveLog.add(self.execution_id, 'command_output', command_server_id=self.ecs.id, output=output)

    def finalize(self):
        if self.ecs.return_code == 0:
            self.ecs.status = Execution.SUCCESS
        else:
            self.ecs.status = Execution.FAILED
        self.ecs.save_end()

        ExecutionLiveLog.add(self.execution_id, 'command_completed',
                             command_server_id=self.ecs.id,
                             return_code=self.ecs.return_code,
                             status=self.ecs.status,
                             time=self.ecs.time)

        if self.ecs.status == Execution.FAILED:
            raise Exception('command exit code != 0')

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        command_server = ExecutionCommandServer.objects.get(pk=kwargs['execution_command_server_id'])
        kwargs['execution_id'] = command_server.execution_command.execution_id
        ExecutionTaskFinish().run(execution_id=command_server.execution_command.execution_id)


class TestConnectionTask(app.Task):
    def run(self, server_id):
        status = False
        output = ''
        try:
            transport = self.create_transport(server_id)
            status = transport.run('echo test')
        except AuthenticationException:
            output = 'Key authentication failed'
            status = -1
        except gaierror:
            output = 'Name or service not known'
            status = -1
        except socket_error:
            output = 'Socket error'
            status = -1
        except Exception as e:
            logger.error(type(e) + str(e))
            output = 'Unknown error'
            status = -1
        return status == 0, output

    def create_transport(self, server_id):
        server = ssh.Server.from_model(Server.objects.get(pk=server_id))
        transport = ssh.SSHTransport(server)
        return transport
########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm, ModelMultipleChoiceField
from django.forms.widgets import Textarea, SelectMultiple, HiddenInput
from django.http import Http404

from crispy_forms.helper import FormHelper

from .models import (
    Application, Department, Environment, Server, ServerRole)


class ModalForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ModalForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-3'
        self.helper.field_class = 'col-sm-7'
        self.helper.label_size = ' col-sm-offset-3'


class PageForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(PageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-3'
        self.helper.field_class = 'col-sm-7'


class TagSelect(SelectMultiple):
    def __init__(self, *args, **kwargs):
        super(TagSelect, self).__init__(*args, **kwargs)
        self.attrs = {'class': 'chosen-select', 'data-placeholder': ' '}
        if 'attrs' in kwargs and 'data-placeholder' in kwargs['attrs']:
            self.attrs['data-placeholder'] = kwargs['attrs']['data-placeholder']


class ServerRoleField(ModelMultipleChoiceField):
    widget = TagSelect

    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = ServerRole.objects.all()
        super(ServerRoleField, self).__init__(*args, **kwargs)
        self.help_text = ''


class ApplicationForm(ModalForm):
    class Meta:
        model = Application
        fields = ['name', 'description']
        widgets = {'description': Textarea(attrs={'rows': 2})}


class EnvironmentForm(ModalForm):
    class Meta:
        model = Environment
        fields = ['name', 'description', 'application']
        widgets = {'description': Textarea(attrs={'rows': 2}),
                   'application': HiddenInput()}


class ServerForm(ModalForm):
    roles = ServerRoleField()

    class Meta:
        model = Server
        fields = ['name', 'host', 'port', 'user', 'roles', 'environment']
        widgets = {'roles': TagSelect(),
                   'environment': HiddenInput()}


class ServerRoleForm(ModalForm):
    class Meta:
        model = ServerRole
        fields = ['name']


class DepartmentForm(ModalForm):
    class Meta:
        model = Department
        fields = ['name']


def create_form(form_objects, name, request, id, args={}):
    """ Helper function for creating form object """
    if not name in form_objects:
        raise Http404()
    if id:
        instance = form_objects[name].Meta.model.objects.get(pk=id)
        form = form_objects[name](request.POST or None, instance=instance)
    else:
        instance = form_objects[name].Meta.model(**args)
        form = form_objects[name](request.POST or None, instance=instance)
    return form


def core_create_form(name, request, id, args={}):
    """ Helper function for creating core form object """
    form_objects = {
        'application': ApplicationForm,
        'environment': EnvironmentForm,
        'server': ServerForm,
        'serverrole': ServerRoleForm,
        'department': DepartmentForm
    }
    return create_form(form_objects, name, request, id, args)

########NEW FILE########
__FILENAME__ = middleware
from guardian.shortcuts import get_objects_for_user


class CurrentDepartment(object):
    def process_request(self, request):
        if not request.user.is_authenticated():
            return
        if not 'current_department_id' in request.session:
            allowed_departments = get_objects_for_user(request.user, 'core.view_department')
            if allowed_departments.count():
                request.session['current_department_id'] = allowed_departments.first().id
                request.current_department_id = request.session['current_department_id']
            else:
                request.current_department_id = None
        else:
            request.current_department_id = request.session['current_department_id']


########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("account", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Department'
        db.create_table(u'core_department', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
        ))
        db.send_create_signal(u'core', ['Department'])

        # Adding model 'Application'
        db.create_table(u'core_application', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('department', self.gf('django.db.models.fields.related.ForeignKey')(related_name='applications', to=orm['core.Department'])),
        ))
        db.send_create_signal(u'core', ['Application'])

        # Adding unique constraint on 'Application', fields ['department', 'name']
        db.create_unique(u'core_application', ['department_id', 'name'])

        # Adding model 'Environment'
        db.create_table(u'core_environment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(related_name='environments', to=orm['core.Application'])),
            ('is_production', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Environment'])

        # Adding unique constraint on 'Environment', fields ['application', 'name']
        db.create_unique(u'core_environment', ['application_id', 'name'])

        # Adding model 'ServerRole'
        db.create_table(u'core_serverrole', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('department', self.gf('django.db.models.fields.related.ForeignKey')(related_name='serverroles', to=orm['core.Department'])),
        ))
        db.send_create_signal(u'core', ['ServerRole'])

        # Adding model 'Server'
        db.create_table(u'core_server', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('user', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='servers', to=orm['core.Environment'])),
        ))
        db.send_create_signal(u'core', ['Server'])

        # Adding unique constraint on 'Server', fields ['environment', 'name']
        db.create_unique(u'core_server', ['environment_id', 'name'])

        # Adding M2M table for field roles on 'Server'
        m2m_table_name = db.shorten_name(u'core_server_roles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('server', models.ForeignKey(orm[u'core.server'], null=False)),
            ('serverrole', models.ForeignKey(orm[u'core.serverrole'], null=False))
        ))
        db.create_unique(m2m_table_name, ['server_id', 'serverrole_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Server', fields ['environment', 'name']
        db.delete_unique(u'core_server', ['environment_id', 'name'])

        # Removing unique constraint on 'Environment', fields ['application', 'name']
        db.delete_unique(u'core_environment', ['application_id', 'name'])

        # Removing unique constraint on 'Application', fields ['department', 'name']
        db.delete_unique(u'core_application', ['department_id', 'name'])

        # Deleting model 'Department'
        db.delete_table(u'core_department')

        # Deleting model 'Application'
        db.delete_table(u'core_application')

        # Deleting model 'Environment'
        db.delete_table(u'core_environment')

        # Deleting model 'ServerRole'
        db.delete_table(u'core_serverrole')

        # Deleting model 'Server'
        db.delete_table(u'core_server')

        # Removing M2M table for field roles on 'Server'
        db.delete_table(db.shorten_name(u'core_server_roles'))


    models = {
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0002_auto__del_unique_serverrole_name__add_unique_serverrole_department_nam
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'ServerRole', fields ['name']
        db.delete_unique(u'core_serverrole', ['name'])

        # Adding unique constraint on 'ServerRole', fields ['department', 'name']
        db.create_unique(u'core_serverrole', ['department_id', 'name'])


    def backwards(self, orm):
        # Removing unique constraint on 'ServerRole', fields ['department', 'name']
        db.delete_unique(u'core_serverrole', ['department_id', 'name'])

        # Adding unique constraint on 'ServerRole', fields ['name']
        db.create_unique(u'core_serverrole', ['name'])


    models = {
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_server_port
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Server.port'
        db.add_column(u'core_server', 'port',
                      self.gf('django.db.models.fields.IntegerField')(default=22),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Server.port'
        db.delete_column(u'core_server', 'port')


    models = {
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '22'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = modal
import json

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from forms import (
    ApplicationForm, core_create_form, DepartmentForm, EnvironmentForm,
    ServerForm, ServerRoleForm)
from .views import ServerRole


def modal_form(request, form_name, id=None, parent_name=None, parent_id=None, app=None):
    return _get_app_modal(app)(form_name, id, parent_id).render(request)


def modal_delete(request, form_name, id, app='core'):
    return _get_app_modal(app)(form_name, id).delete(request)


def _get_app_modal(app):
    if app == None:
        obj = Modal
    else:
        if app in settings.INSTALLED_APPS:
            obj = __import__(app, fromlist=['modal']).modal.Modal
        else:
            raise Http404()
    return obj


class BaseModal(object):
    """ Base class for modal dialog boxes """

    """ Defines associated types, their models and forms """
    definitions = {}

    def __init__(self, form_name, id=None, parent_id=None):
        self.form_name = form_name
        self.id = id
        self.parent_id = parent_id
        self.data = {'status': True, 'action': 'reload'}
        self.form = None
        self.instance = None
        self.request = None
        if form_name in self.definitions:
            self.definition = self.definitions[form_name]
        else:
            raise ValueError('Modal: Unknown form_name')

    def create_form(self):
        """ Returns form object """
        self.form = self.get_form_creator()(self.form_name, self.request, self.id, self.get_form_args())
        self.trigger_event('form_create')

    def get_form_args(self):
        args = {}
        if self.definition['parent']:
            args[self.definition['parent']] = self.parent_id
        return args

    def render(self, request):
        """ Returns rendered view """
        self.request = request
        self.create_form()
        form_template = 'partial/' + self.form_name + '_form.html'
        is_new = not bool(self.id)
        if request.method == 'POST':
            template = form_template
            if self.form.is_valid():
                try:
                    self.trigger_event('before_save')
                    self.instance = self.form.save()

                    if is_new:
                        self.trigger_event('create')
                        self.message('Created')
                    else:
                        self.trigger_event('update')
                        self.message('Saved')
                    return HttpResponse(json.dumps(self.data), content_type="application/json")
                except IntegrityError as e:
                    from django.forms.util import ErrorList

                    errors = self.form._errors.setdefault("__all__", ErrorList())
                    errors.append('Integrity error')
                    errors.append(e)

        else:
            template = 'partial/modal_form.html'
        self.data = {
            'form': self.form,
            'form_template': form_template,
            'is_new': is_new,
            'instance': self.form.instance,
            'model_name': self.form.Meta.model.__name__,
            'request_path': request.path
        }
        self.trigger_event('view')
        return render(request, template, self.data)

    def message(self, message):
        messages.success(self.request, message)

    def delete(self, request):
        """ Handles delete on modal model """
        self.request = request
        self.create_form()
        self.instance = get_object_or_404(self.form.Meta.model, pk=self.id)
        self.instance.delete()
        self.trigger_event('delete')
        self.message('Deleted')
        return HttpResponse(json.dumps(self.data), content_type="application/json")


    def trigger_event(self, event):
        """ Triggers modal event """
        event = 'on_%s_%s' % (event, self.form_name)
        try:
            callback = getattr(self, event)
            callback()
        except AttributeError:
            pass


class Modal(BaseModal):
    definitions = {
        'application': {
            'form': ApplicationForm,
            'parent': None, },
        'environment': {
            'form': EnvironmentForm,
            'parent': 'application_id', },
        'server': {
            'form': ServerForm,
            'parent': 'environment_id'},
        'serverrole': {
            'form': ServerRoleForm,
            'parent': None},
        'department': {
            'form': DepartmentForm,
            'parent': None}
    }

    def get_form_creator(self):
        return core_create_form

    def on_before_save_application(self):
        instance = self.form.instance
        if not instance.id:
            instance.department_id = self.request.current_department_id

    def on_before_save_serverrole(self):
        instance = self.form.instance
        if not instance.id:
            instance.department_id = self.request.current_department_id


    def on_create_application(self):
        self.data['action'] = 'redirect'
        self.data['target'] = self.instance.get_absolute_url()

    def on_delete_application(self):
        self.data['action'] = 'redirect'
        self.data['target'] = reverse('index')

    def on_delete_environment(self):
        self.data['action'] = 'redirect'
        self.data['target'] = self.instance.application.get_absolute_url()

    def on_view_server(self):
        from backend.tasks import read_public_key
        try:
            self.data['pubkey'] = read_public_key.delay(self.form.instance.environment_id).get()
        except Exception as e:
            self.data['pubkey'] = 'Couldn\'t load'

    def on_form_create_server(self):
        self.form.fields['roles'].queryset = ServerRole.objects.filter(department_id=self.request.current_department_id)

    def on_create_department(self):
        for serverrole in ['app', 'db', 'cache']:
            ServerRole(name=serverrole, department=self.instance).save()

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from datetime import datetime, timedelta


def gunnery_name():
    return RegexValidator(regex='^[a-zA-Z0-9_\.\-]+$', message='Invalid characters')


class Department(models.Model):
    name = models.CharField(blank=False, max_length=128, validators=[gunnery_name()], unique=True)

    class Meta:
        permissions = (
        ("view_department", "Can view department"),
        ("edit_department", "Can edit department"),
        ("execute_department", "Can execute department"),
        ("manage_department", "Can manage department"), )

    def __unicode__(self):
        return self.name


class Application(models.Model):
    name = models.CharField(blank=False, max_length=128, validators=[gunnery_name()])
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, related_name="applications")

    class Meta:
        unique_together = ("department", "name")
        permissions = (
        ("view_application", "Can view application"),
        ("edit_application", "Can edit application"),
        ("execute_application", "Can execute tasks on application"), )

    def get_absolute_url(self):
        return reverse('application_page', args=[str(self.id)])

    def executions_inline(self):
        from task.models import Execution

        return Execution.get_inline_by_application(self.id)


class Environment(models.Model):
    name = models.CharField(blank=False, max_length=128, validators=[gunnery_name()])
    description = models.TextField(blank=True)
    application = models.ForeignKey(Application, related_name="environments")
    is_production = models.BooleanField(default=False)

    class Meta:
        unique_together = ("application", "name")
        permissions = (
        ("view_environment", "Can view environment"),
        ("edit_environment", "Can edit environment"),
        ("execute_environment", "Can execute tasks on environment"), )

    def get_absolute_url(self):
        return reverse('environment_page', args=[str(self.id)])

    def executions_inline(self):
        from task.models import Execution

        return Execution.get_inline_by_environment(self.id)

    @staticmethod
    def generate_keys(sender, instance, created, **kwargs):
        if created:
            from backend.tasks import generate_private_key
            generate_private_key.delay(environment_id=instance.id)

    @staticmethod
    def cleanup_files(sender, instance, **kwargs):
        from backend.tasks import cleanup_files
        cleanup_files.delay(instance.id)

    def stats_count(self):
        return self.application.tasks.\
            filter(executions__environment=self).\
            annotate(avg=models.Avg('executions__time'), count=models.Count('executions'))

    def stats_statues(self):
        return self.executions.\
            filter(time_start__gte=datetime.now()-timedelta(days=30)).\
            values('status').\
            annotate(count=models.Count('status'))


post_save.connect(Environment.generate_keys, sender=Environment)
post_delete.connect(Environment.cleanup_files, sender=Environment)


class ServerRole(models.Model):
    name = models.CharField(blank=False, max_length=32, validators=[gunnery_name()])
    department = models.ForeignKey(Department, related_name="serverroles")

    class Meta:
        unique_together = ("department", "name")

    def __unicode__(self):
        return self.name


class Server(models.Model):
    name = models.CharField(blank=False, max_length=128, validators=[gunnery_name()])
    host = models.CharField(blank=False, max_length=128)
    port = models.IntegerField(blank=False, default=22)
    user = models.CharField(blank=False, max_length=128)
    roles = models.ManyToManyField(ServerRole, related_name="servers")
    environment = models.ForeignKey(Environment, related_name="servers")

    class Meta:
        unique_together = ("environment", "name")

########NEW FILE########
__FILENAME__ = core_extras
from django import template

from task.models import Execution


register = template.Library()

icons_mapping = {
    "dashboard": "dashboard",
    "application": "desktop",
    "environment": "sitemap",
    "server": "puzzle-piece",
    "serverrole": "tags",
    "task": "tasks",
    "execution": "bars",
    "settings": "gear",
    "user": "user",
    "group": "group",
    "department": "building-o",
}

status_mapping = {
    Execution.PENDING: ["default", "clock-o", "Pending"],
    Execution.RUNNING: ["warning", "spinner fa-spin", "Running"],
    Execution.SUCCESS: ["success", "check", "Success"],
    Execution.FAILED: ["danger", "exclamation-triangle", "Failed"],
    Execution.ABORTED: ["warning", "exclamation-triangle", "Aborted"],
}


@register.simple_tag
def model_icon(model):
    if not model in icons_mapping:
        raise ValueError('Invalid icon name')
    return '<i class="fa fa-' + icons_mapping[model] + '"></i>'


@register.simple_tag
def execution_status(status):
    template = '<span class="label label-%s"><i class="fa fa-%s"></i> %s</span>' % tuple(status_mapping[status])
    return template
########NEW FILE########
__FILENAME__ = base
from django.test import TestCase
from guardian.shortcuts import assign_perm
from account.tests.fixtures import UserFactory
from core.tests.fixtures import DepartmentFactory


class LoggedTestCase(TestCase):
    logged_is_superuser = False

    @classmethod
    def setUpClass(cls):
        cls.user = UserFactory(is_superuser=cls.logged_is_superuser)
        cls.setup_department()

    @classmethod
    def setup_department(cls):
        cls.department = DepartmentFactory()
        assign_perm('core.view_department', cls.user, cls.department)

    def setUp(self):
        result = self.client.login(username=self.user.email, password=self.user.email)
        session = self.client.session
        session['current_department_id'] = self.department.id
        session.save()
        self.assertTrue(result, 'Login failed')


class BaseModalTestCase(LoggedTestCase):
    url = None
    object_factory = None

    @classmethod
    def setUpClass(cls):
        super(BaseModalTestCase, cls).setUpClass()
        cls.object = cls.object_factory()


class BaseModalTests(object):
    def test_create_form(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

    def test_edit_form(self):
        response = self.client.get(self.get_url_with_id())
        self.assertEquals(response.status_code, 200)

    def test_delete(self):
        response = self.client.post(self.get_url_with_id())
        self.assertEquals(response.status_code, 200)

    def get_url_with_id(self):
        return self.url + str(self.object.id) + '/'
########NEW FILE########
__FILENAME__ = fixtures
from factory.django import DjangoModelFactory
import factory
from ..models import *


class DepartmentFactory(DjangoModelFactory):
    FACTORY_FOR = Department

    name = factory.Sequence(lambda n: 'Department_%s' % n)


class ApplicationFactory(DjangoModelFactory):
    FACTORY_FOR = Application

    name = factory.Sequence(lambda n: 'Application_%s' % n)
    department = factory.SubFactory(DepartmentFactory)


class EnvironmentFactory(DjangoModelFactory):
    FACTORY_FOR = Environment

    name = factory.Sequence(lambda n: 'Environment_%s' % n)
    application = factory.SubFactory(ApplicationFactory)


class ServerRoleFactory(DjangoModelFactory):
    FACTORY_FOR = ServerRole

    name = factory.Sequence(lambda n: 'ServerRole_%s' % n)
    department = factory.SubFactory(DepartmentFactory)

class ServerFactory(DjangoModelFactory):
    FACTORY_FOR = Server

    name = factory.Sequence(lambda n: 'Server_%s' % n)
    host = 'localhost'
    user = 'user'
    environment = factory.SubFactory(EnvironmentFactory)

    @factory.post_generation
    def roles(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for role in extracted:
                self.roles.add(role)
########NEW FILE########
__FILENAME__ = test_views
from django.test import TestCase
from unittest import skip

from .base import LoggedTestCase, BaseModalTestCase, BaseModalTests
from core.tests.fixtures import *


class GuestTest(TestCase):
    def test_index(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/account/login/?next=/')


class IndexTest(LoggedTestCase):
    def test_index_help_redirect(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/help/')

    def test_index_help_no_redirect(self):
        application = ApplicationFactory(department=self.department)
        response = self.client.get('/')
        self.assertContains(response, application.name)


class ApplicationTest(LoggedTestCase):
    def test_application(self):
        application = ApplicationFactory(department=self.department)
        response = self.client.get('/application/%d/' % application.id)
        self.assertContains(response, application.name)

    def test_application_forbidden(self):
        application = ApplicationFactory(department=DepartmentFactory())
        response = self.client.get('/application/%d/' % application.id)
        self.assertEqual(response.status_code, 302)


class EnvironmentTest(LoggedTestCase):
    def test_environment(self):
        application = ApplicationFactory(department=self.department)
        environment = EnvironmentFactory(application=application)
        response = self.client.get('/environment/%d/' % environment.id)
        self.assertContains(response, environment.name)

    def test_environment_forbidden(self):
        environment = EnvironmentFactory()
        response = self.client.get('/environment/%d/' % environment.id)
        self.assertEqual(response.status_code, 302)


class SettingsTest(LoggedTestCase):
    def test_user_profile(self):
        response = self.client.get('/settings/user/profile/')
        self.assertContains(response, 'Save')

    def test_user_password(self):
        response = self.client.get('/settings/user/password/')
        self.assertContains(response, 'Save')

    def test_department_applications(self):
        application = ApplicationFactory(department=self.department)
        response = self.client.get('/settings/department/applications/')
        self.assertContains(response, application.name)

    def test_department_applications_empty(self):
        response = self.client.get('/settings/department/applications/')
        self.assertContains(response, 'No applications yet.')

    def test_department_users(self):
        response = self.client.get('/settings/department/users/')
        self.assertContains(response, 'Create')

    def test_department_serverroles(self):
        server_role = ServerRoleFactory(department=self.department)
        response = self.client.get('/settings/department/serverroles/')
        self.assertContains(response, server_role.name)

    def test_department_serverroles_empty(self):
        response = self.client.get('/settings/department/serverroles/')
        self.assertContains(response, 'No roles yet.')

    def test_system_departments_forbidden(self):
        response = self.client.get('/settings/system/departments/')
        self.assertEqual(response.status_code, 302)

    def test_system_users_forbidden(self):
        response = self.client.get('/settings/system/users/')
        self.assertEqual(response.status_code, 302)


class SettingsSuperuserTest(LoggedTestCase):
    logged_is_superuser = True

    def test_system_departments(self):
        response = self.client.get('/settings/system/departments/')
        self.assertContains(response, 'Create')

    def test_system_users(self):
        response = self.client.get('/settings/system/users/')
        self.assertContains(response, 'Create')


class SettingsNotStaffTest(LoggedTestCase):
    logged_is_superuser = False

    def test_system_departments(self):
        response = self.client.get('/settings/system/departments/')
        self.assertEqual(response.status_code, 302)

    def test_system_users(self):
        response = self.client.get('/settings/system/users/')
        self.assertEqual(response.status_code, 302)


class HelpTest(LoggedTestCase):
    def test_help(self):
        response = self.client.get('/help/')
        self.assertContains(response, 'Help')


class CoreModalServerroleTest(BaseModalTestCase, BaseModalTests):
    url = '/modal_form/a:/serverrole/'
    object_factory = ServerRoleFactory


class CoreModalApplicationTest(BaseModalTestCase, BaseModalTests):
    url = '/modal_form/a:/application/'
    object_factory = ApplicationFactory


class CoreModalEnvironmentTest(BaseModalTestCase, BaseModalTests):
    url = '/modal_form/a:/environment/'
    object_factory = EnvironmentFactory


class DepartmentSwitcherTest(LoggedTestCase):
    # def test_switch_to_valid_department(self):
    #     response = self.client.get('/department/switch/%d/' % self.department.id)
    #     self.assertRedirects(response, '/')

    def test_switch_to_invalid_department(self):
        department = DepartmentFactory()
        response = self.client.get('/department/switch/%d/' % department.id)
        self.assertRedirects(response, '/account/login/?next=/department/switch/%d/' % department.id)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from .modal import modal_delete, modal_form
from .views import (
    application_page, department_switch, environment_page, help_page, index,
    settings_page, server_test, server_test_ajax)

urlpatterns = patterns('',
    url(r'^$', index, name='index'),
    url(r'^application/(?P<application_id>[\d]+)/$', application_page, name='application_page'),
    url(r'^environment/(?P<environment_id>[\d]+)/$', environment_page, name='environment_page'),
    url(r'^modal/server_test/(?P<server_id>[\d]+)/$', server_test, name='server_test'),
    url(r'^modal/server_test_ajax/(?P<task_id>[\da-z\-]+)/$', server_test_ajax,
       name='server_test_ajax'),

    url(r'^modal_form/a:(?P<app>[a-z]+)?/(?P<form_name>[a-z_]+)/$', modal_form, name='modal_form'),
    url(r'^modal_form/a:(?P<app>[a-z]+)?/(?P<form_name>[a-z_]+)/(?P<id>\d+)/$', modal_form,
       name='modal_form'),
    url(
       r'^modal_form/a:(?P<app>[a-z]+)?/(?P<parent_name>[a-z_]+)/(?P<parent_id>\d+)/(?P<form_name>[a-z_]+)/(?P<id>\d+)?/?$',
       modal_form, name='modal_form'),
    url(r'^modal_delete/a:(?P<app>[a-z]+)?/(?P<form_name>[a-z_]+)/(?P<id>\d+)/$', modal_delete,
       name='modal_delete'),

    url(r'^settings/$', settings_page, name='settings_page'),
    url(r'^settings/(?P<section>[a-z_]+)/$', settings_page, name='settings_page'),
    url(r'^settings/(?P<section>[a-z_]+)/(?P<subsection>[a-z_]+)/$', settings_page,
       name='settings_page'),

    url(r'^department/switch/(?P<id>[\d]+)/$', department_switch, name='department_switch'),

    url(r'^help/', help_page, name='help_page'),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.http import Http404, HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render

from guardian.shortcuts import get_objects_for_user

from account.decorators import has_permissions
from backend.tasks import TestConnectionTask
from .models import Application, Department, Environment, Server, ServerRole


def get_common_page_data(request):
    data = {}
    data['departments'] = get_objects_for_user(request.user, 'core.view_department')
    # data['application_list_sidebar'] = get_objects_for_user(request.user, 'core.view_application'). \
    #     filter(department_id=request.current_department_id).prefetch_related('environments')
    data['application_list_sidebar'] = Application.objects.filter(department_id=request.current_department_id).\
        prefetch_related('environments').order_by('name')
    data['current_department_id'] = request.current_department_id
    data['user'] = request.user
    return data


@login_required
def index(request):
    data = get_common_page_data(request)
    data['application_list'] = data['application_list_sidebar']
    if not data['application_list']:
        return redirect(reverse('help_page'))
    return render(request, 'page/index.html', data)


@has_permissions('core.Application')
def application_page(request, application_id):
    data = get_common_page_data(request)
    data['application'] = get_object_or_404(Application, pk=application_id)
    return render(request, 'page/application.html', data)


@has_permissions('core.Environment')
def environment_page(request, environment_id):
    data = get_common_page_data(request)
    data['environment'] = get_object_or_404(Environment, pk=environment_id)
    data['servers'] = list(Server.objects.filter(environment_id=environment_id).prefetch_related('roles'))
    return render(request, 'page/environment.html', data)


@has_permissions('core.Server')
def server_test(request, server_id):
    data = {}
    data['server'] = get_object_or_404(Server, pk=server_id)
    data['task_id'] = TestConnectionTask().delay(server_id).id
    return render(request, 'partial/server_test.html', data)


@login_required
def server_test_ajax(request, task_id):
    data = {}
    task = TestConnectionTask().AsyncResult(task_id)
    if task.status == 'SUCCESS':
        status, output = task.get()
        data['status'] = status
        data['output'] = output
    elif task.status == 'FAILED':
        data['status'] = False
    else:
        data['status'] = None
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
def help_page(request):
    data = get_common_page_data(request)
    return render(request, 'page/help.html', data)


@login_required
def settings_page(request, section='user', subsection='profile'):
    data = get_common_page_data(request)
    data['section'] = section
    data['subsection'] = subsection
    handler = '_settings_%s_%s' % (section, subsection)
    if section == 'system' and request.user.is_superuser is not True:
        return redirect('index')
    if handler in globals():
        data = globals()[handler](request, data)
    else:
        raise Http404
    return render(request, 'page/settings.html', data)


def _settings_user_profile(request, data):
    data['subsection_template'] = 'partial/account_profile.html'
    from account.forms import account_create_form
    form = account_create_form('user_profile', request, request.user.id)
    form.fields['email'].widget.attrs['readonly'] = True
    data['form'] = form
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            data['user'] = form.instance
    return data


def _settings_user_password(request, data):
    data['subsection_template'] = 'partial/account_password.html'
    from account.forms import account_create_form
    form = account_create_form('user_password', request, request.user.id)
    data['form'] = form
    if request.method == 'POST':
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(user.password)
            user.save()
            data['user'] = form.instance
    return data


def _settings_department_applications(request, data):
    data['subsection_template'] = 'partial/application_list.html'
    data['applications'] = Application.objects.filter(department_id=request.current_department_id)
    data['empty'] = not bool(data['applications'].count())
    return data


def _settings_department_users(request, data):
    data['subsection_template'] = 'partial/user_list.html'
    from guardian.shortcuts import get_users_with_perms
    department = Department.objects.get(pk=request.current_department_id)
    data['users'] = get_users_with_perms(department).order_by('name')
    return data


def _settings_department_serverroles(request, data):
    data['subsection_template'] = 'partial/serverrole_list.html'
    data['serverroles'] = ServerRole.objects.filter(department_id=request.current_department_id)
    data['empty'] = not bool(data['serverroles'].count())
    return data


@user_passes_test(lambda u: u.is_superuser)
def _settings_system_departments(request, data):
    data['subsection_template'] = 'partial/department_list.html'
    data['departments'] = Department.objects.all()
    return data


@user_passes_test(lambda u: u.is_superuser)
def _settings_system_users(request, data):
    data['subsection_template'] = 'partial/user_list.html'
    data['users'] = get_user_model().objects.order_by('name')
    return data


@has_permissions('core.Department')
def department_switch(request, id):
    department = get_object_or_404(Department, pk=id)
    if request.user.has_perm('core.view_department', department):
        request.session['current_department_id'] = int(id)
    return redirect('index')

########NEW FILE########
__FILENAME__ = celery
from __future__ import absolute_import

import os

from celery import Celery

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gunnery.settings')

app = Celery('gunnery')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.update(
    CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend',
    CELERY_RESULT_SERIALIZER="json",
    CELERY_TASK_SERIALIZER="json",
    CELERY_CHORD_PROPAGATES=False,
)
########NEW FILE########
__FILENAME__ = common
"""
Django settings for gunnery project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '6x09uq7d4f&so^q(&akentw^ud=rdu-u94pu9r83$l_!+jus$m'

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    #'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_extensions',
    'guardian',
    'crispy_forms',
    'djcelery',
    'south',
    'core',
    'task',
    'backend',
    'account',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
    'core.middleware.CurrentDepartment'

)

ROOT_URLCONF = 'gunnery.urls'

WSGI_APPLICATION = 'gunnery.wsgi.application'



# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'gunnery',
        'USER': 'gunnery',
        'PASSWORD': 'gunnery',
        'HOST': '127.0.0.1',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = False

USE_TZ = True
DATETIME_FORMAT = 'Y-m-d H:i'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "../static"),
)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

CRISPY_TEMPLATE_PACK = 'bootstrap3'

CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_SERIALIZER = "json"

CELERYD_TASK_TIME_LIMIT = 60 * 60
CELERYD_TASK_SOFT_TIME_LIMIT = 60 * 30

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/'
ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: "/account/profile/%d/" % u.id,
}
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',)
AUTH_USER_MODEL = 'account.CustomUser'
ANONYMOUS_USER_ID = None

PRIVATE_DIR = '/var/gunnery/secure'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(asctime)s - %(levelname)s: %(message)s'
        },
    },
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
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'gunnery': {
            'handlers': ['mail_admins', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

########NEW FILE########
__FILENAME__ = development
from .common import *
ENVIRONMENT = 'development'

DEBUG = True

TEMPLATE_DEBUG = True

INSTALLED_APPS += (
    'debug_toolbar',
    'django_nose',
)

MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

from fnmatch import fnmatch


class glob_list(list):
    def __contains__(self, key):
        for elt in self:
            if fnmatch(key, elt): return True
        return False


INTERNAL_IPS = glob_list(['127.0.0.1', '10.0.*.*'])

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
########NEW FILE########
__FILENAME__ = production
from .common import *
ENVIRONMENT = 'production'

EMAIL_USE_TLS = True
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 25

DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console_error': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console_error'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
########NEW FILE########
__FILENAME__ = test
from .common import *
ENVIRONMENT = 'test'

TEST_DISCOVER_TOP_LEVEL = BASE_DIR
TEST_DISCOVER_ROOT = BASE_DIR
TEST_DISCOVER_PATTERN = "*"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}

CELERY_ALWAYS_EAGER = True
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = patterns('',
                       url(r'^', include('core.urls')),
                       url(r'^', include('task.urls')),
                       url(r'^', include('account.urls')),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
########NEW FILE########
__FILENAME__ = uwsgiapp
"""
WSGI config for gunnery project.

It exposes the WSGI callable as a modulelevel variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gunnery.settings.production")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from django.conf import settings
if settings.ENVIRONMENT == 'development':
    import uwsgi
    from uwsgidecorators import timer
    from django.utils import autoreload

    @timer(3)
    def change_code_gracefull_reload(sig):
        if autoreload.code_changed():
            uwsgi.reload()
########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for gunnery project.

It exposes the WSGI callable as a modulelevel variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gunnery.settings.development")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gunnery.settings.production")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm, TextInput, ValidationError
from django.forms.widgets import Textarea, HiddenInput
from django.forms.models import modelformset_factory, BaseModelFormSet

from .models import (
    Execution, ExecutionParameter, Task, TaskCommand, TaskParameter)
from core.forms import PageForm, TagSelect, create_form


class TaskForm(PageForm):
    class Meta:
        model = Task
        fields = ['name', 'description', 'application']
        widgets = {'description': Textarea(attrs={'rows': 2}),
                   'application': HiddenInput()}


class TaskParameterForm(ModelForm):
    class Meta:
        model = TaskParameter
        fields = ['name', 'description']
        widgets = {'description': TextInput()}


class TaskCommandForm(ModelForm):
    class Meta:
        model = TaskCommand
        fields = ['command', 'roles']
        widgets = {'roles': TagSelect(attrs={'data-placeholder': 'Roles'})}


class ExecutionForm(ModelForm):
    class Meta:
        model = Execution
        fields = ['environment']


class ExecutionParameterForm(ModelForm):
    class Meta:
        model = ExecutionParameter
        fields = ['name', 'value']


class RequireFirst(BaseModelFormSet):
    def clean(self, *args, **kwargs):
        super(RequireFirst, self).clean()
        has_one = False
        for form in self.forms:
            if 'command' in form.cleaned_data and form.cleaned_data['DELETE'] == False:
                has_one = True
        if not has_one:
            raise ValidationError('At least one command must be specified')


TaskParameterFormset = modelformset_factory(TaskParameter,
                                            form=TaskParameterForm,
                                            can_order=True,
                                            can_delete=True,
                                            extra=1)
TaskCommandFormset = modelformset_factory(TaskCommand,
                                          form=TaskCommandForm,
                                          can_order=True,
                                          can_delete=True,
                                          extra=2,
                                          formset=RequireFirst)


def task_create_form(name, request, id, args={}):
    form_objects = {
        'task': TaskForm,
    }
    return create_form(form_objects, name, request, id, args)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("account", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Task'
        db.create_table(u'task_task', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tasks', to=orm['core.Application'])),
        ))
        db.send_create_signal(u'task', ['Task'])

        # Adding unique constraint on 'Task', fields ['application', 'name']
        db.create_unique(u'task_task', ['application_id', 'name'])

        # Adding model 'TaskParameter'
        db.create_table(u'task_taskparameter', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(related_name='parameters', to=orm['task.Task'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('default_value', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'task', ['TaskParameter'])

        # Adding model 'TaskCommand'
        db.create_table(u'task_taskcommand', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(related_name='commands', to=orm['task.Task'])),
            ('command', self.gf('django.db.models.fields.TextField')()),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'task', ['TaskCommand'])

        # Adding M2M table for field roles on 'TaskCommand'
        m2m_table_name = db.shorten_name(u'task_taskcommand_roles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('taskcommand', models.ForeignKey(orm[u'task.taskcommand'], null=False)),
            ('serverrole', models.ForeignKey(orm[u'core.serverrole'], null=False))
        ))
        db.create_unique(m2m_table_name, ['taskcommand_id', 'serverrole_id'])

        # Adding model 'Execution'
        db.create_table(u'task_execution', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(related_name='executions', to=orm['task.Task'])),
            ('time_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('time_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('time_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('time', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='executions', to=orm['core.Environment'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='executions', to=orm['account.CustomUser'])),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=3)),
        ))
        db.send_create_signal(u'task', ['Execution'])

        # Adding model 'ExecutionParameter'
        db.create_table(u'task_executionparameter', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('execution', self.gf('django.db.models.fields.related.ForeignKey')(related_name='parameters', to=orm['task.Execution'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'task', ['ExecutionParameter'])

        # Adding model 'ExecutionCommand'
        db.create_table(u'task_executioncommand', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('execution', self.gf('django.db.models.fields.related.ForeignKey')(related_name='commands', to=orm['task.Execution'])),
            ('command', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'task', ['ExecutionCommand'])

        # Adding M2M table for field roles on 'ExecutionCommand'
        m2m_table_name = db.shorten_name(u'task_executioncommand_roles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('executioncommand', models.ForeignKey(orm[u'task.executioncommand'], null=False)),
            ('serverrole', models.ForeignKey(orm[u'core.serverrole'], null=False))
        ))
        db.create_unique(m2m_table_name, ['executioncommand_id', 'serverrole_id'])

        # Adding model 'ExecutionCommandServer'
        db.create_table(u'task_executioncommandserver', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('execution_command', self.gf('django.db.models.fields.related.ForeignKey')(related_name='servers', to=orm['task.ExecutionCommand'])),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=3)),
            ('time_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('time_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('time', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('return_code', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('server', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Server'])),
            ('output', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'task', ['ExecutionCommandServer'])

        # Adding model 'ExecutionLiveLog'
        db.create_table(u'task_executionlivelog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('execution', self.gf('django.db.models.fields.related.ForeignKey')(related_name='live_logs', to=orm['task.Execution'])),
            ('event', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('data', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'task', ['ExecutionLiveLog'])


    def backwards(self, orm):
        # Removing unique constraint on 'Task', fields ['application', 'name']
        db.delete_unique(u'task_task', ['application_id', 'name'])

        # Deleting model 'Task'
        db.delete_table(u'task_task')

        # Deleting model 'TaskParameter'
        db.delete_table(u'task_taskparameter')

        # Deleting model 'TaskCommand'
        db.delete_table(u'task_taskcommand')

        # Removing M2M table for field roles on 'TaskCommand'
        db.delete_table(db.shorten_name(u'task_taskcommand_roles'))

        # Deleting model 'Execution'
        db.delete_table(u'task_execution')

        # Deleting model 'ExecutionParameter'
        db.delete_table(u'task_executionparameter')

        # Deleting model 'ExecutionCommand'
        db.delete_table(u'task_executioncommand')

        # Removing M2M table for field roles on 'ExecutionCommand'
        db.delete_table(db.shorten_name(u'task_executioncommand_roles'))

        # Deleting model 'ExecutionCommandServer'
        db.delete_table(u'task_executioncommandserver')

        # Deleting model 'ExecutionLiveLog'
        db.delete_table(u'task_executionlivelog')


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        u'task.execution': {
            'Meta': {'object_name': 'Execution'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['core.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['task.Task']"}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['account.CustomUser']"})
        },
        u'task.executioncommand': {
            'Meta': {'object_name': 'ExecutionCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.ServerRole']", 'symmetrical': 'False'})
        },
        u'task.executioncommandserver': {
            'Meta': {'object_name': 'ExecutionCommandServer'},
            'execution_command': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['task.ExecutionCommand']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'return_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Server']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'task.executionlivelog': {
            'Meta': {'object_name': 'ExecutionLiveLog'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'live_logs'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'task.executionparameter': {
            'Meta': {'object_name': 'ExecutionParameter'},
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.task': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Task'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.taskcommand': {
            'Meta': {'object_name': 'TaskCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'commands'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Task']"})
        },
        u'task.taskparameter': {
            'Meta': {'object_name': 'TaskParameter'},
            'default_value': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Task']"})
        }
    }

    complete_apps = ['task']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_executioncommandserver_celery_task_id
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ExecutionCommandServer.celery_task_id'
        db.add_column(u'task_executioncommandserver', 'celery_task_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=36, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ExecutionCommandServer.celery_task_id'
        db.delete_column(u'task_executioncommandserver', 'celery_task_id')


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        u'task.execution': {
            'Meta': {'object_name': 'Execution'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['core.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['task.Task']"}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['account.CustomUser']"})
        },
        u'task.executioncommand': {
            'Meta': {'object_name': 'ExecutionCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.ServerRole']", 'symmetrical': 'False'})
        },
        u'task.executioncommandserver': {
            'Meta': {'object_name': 'ExecutionCommandServer'},
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'execution_command': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['task.ExecutionCommand']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'return_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Server']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'task.executionlivelog': {
            'Meta': {'object_name': 'ExecutionLiveLog'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'live_logs'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'task.executionparameter': {
            'Meta': {'object_name': 'ExecutionParameter'},
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.task': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Task'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.taskcommand': {
            'Meta': {'object_name': 'TaskCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'commands'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Task']"})
        },
        u'task.taskparameter': {
            'Meta': {'object_name': 'TaskParameter'},
            'default_value': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Task']"})
        }
    }

    complete_apps = ['task']
########NEW FILE########
__FILENAME__ = 0003_auto__del_field_executioncommandserver_celery_task_id__add_field_execu
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'ExecutionCommandServer.celery_task_id'
        db.delete_column(u'task_executioncommandserver', 'celery_task_id')

        # Adding field 'Execution.celery_task_id'
        db.add_column(u'task_execution', 'celery_task_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=36, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'ExecutionCommandServer.celery_task_id'
        db.add_column(u'task_executioncommandserver', 'celery_task_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=36, blank=True),
                      keep_default=False)

        # Deleting field 'Execution.celery_task_id'
        db.delete_column(u'task_execution', 'celery_task_id')


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        u'task.execution': {
            'Meta': {'object_name': 'Execution'},
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['core.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['task.Task']"}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['account.CustomUser']"})
        },
        u'task.executioncommand': {
            'Meta': {'object_name': 'ExecutionCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.ServerRole']", 'symmetrical': 'False'})
        },
        u'task.executioncommandserver': {
            'Meta': {'object_name': 'ExecutionCommandServer'},
            'execution_command': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['task.ExecutionCommand']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'return_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Server']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'task.executionlivelog': {
            'Meta': {'object_name': 'ExecutionLiveLog'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'live_logs'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'task.executionparameter': {
            'Meta': {'object_name': 'ExecutionParameter'},
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.task': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Task'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.taskcommand': {
            'Meta': {'object_name': 'TaskCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'commands'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Task']"})
        },
        u'task.taskparameter': {
            'Meta': {'object_name': 'TaskParameter'},
            'default_value': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Task']"})
        }
    }

    complete_apps = ['task']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_executioncommandserver_celery_task_id
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ExecutionCommandServer.celery_task_id'
        db.add_column(u'task_executioncommandserver', 'celery_task_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=36, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ExecutionCommandServer.celery_task_id'
        db.delete_column(u'task_executioncommandserver', 'celery_task_id')


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'task.execution': {
            'Meta': {'object_name': 'Execution'},
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['core.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['task.Task']"}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['account.CustomUser']"})
        },
        u'task.executioncommand': {
            'Meta': {'object_name': 'ExecutionCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.ServerRole']", 'symmetrical': 'False'})
        },
        u'task.executioncommandserver': {
            'Meta': {'object_name': 'ExecutionCommandServer'},
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'execution_command': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['task.ExecutionCommand']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'return_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Server']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'task.executionlivelog': {
            'Meta': {'object_name': 'ExecutionLiveLog'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'live_logs'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'task.executionparameter': {
            'Meta': {'object_name': 'ExecutionParameter'},
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.task': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Task'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.taskcommand': {
            'Meta': {'object_name': 'TaskCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'commands'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Task']"})
        },
        u'task.taskparameter': {
            'Meta': {'object_name': 'TaskParameter'},
            'default_value': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Task']"})
        }
    }

    complete_apps = ['task']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_executioncommand_order
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ExecutionCommand.order'
        db.add_column(u'task_executioncommand', 'order',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ExecutionCommand.order'
        db.delete_column(u'task_executioncommand', 'order')


    models = {
        u'account.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.application': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'Application'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': u"orm['core.Department']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.department': {
            'Meta': {'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'core.environment': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Environment'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_production': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.server': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Server'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['core.Environment']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '22'}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'servers'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'core.serverrole': {
            'Meta': {'unique_together': "(('department', 'name'),)", 'object_name': 'ServerRole'},
            'department': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'serverroles'", 'to': u"orm['core.Department']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'task.execution': {
            'Meta': {'object_name': 'Execution'},
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['core.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['task.Task']"}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executions'", 'to': u"orm['account.CustomUser']"})
        },
        u'task.executioncommand': {
            'Meta': {'object_name': 'ExecutionCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['core.ServerRole']", 'symmetrical': 'False'})
        },
        u'task.executioncommandserver': {
            'Meta': {'object_name': 'ExecutionCommandServer'},
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'execution_command': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'servers'", 'to': u"orm['task.ExecutionCommand']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'return_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Server']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'time_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'task.executionlivelog': {
            'Meta': {'object_name': 'ExecutionLiveLog'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'live_logs'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'task.executionparameter': {
            'Meta': {'object_name': 'ExecutionParameter'},
            'execution': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Execution']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.task': {
            'Meta': {'unique_together': "(('application', 'name'),)", 'object_name': 'Task'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks'", 'to': u"orm['core.Application']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'task.taskcommand': {
            'Meta': {'object_name': 'TaskCommand'},
            'command': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'roles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'commands'", 'symmetrical': 'False', 'to': u"orm['core.ServerRole']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commands'", 'to': u"orm['task.Task']"})
        },
        u'task.taskparameter': {
            'Meta': {'object_name': 'TaskParameter'},
            'default_value': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameters'", 'to': u"orm['task.Task']"})
        }
    }

    complete_apps = ['task']
########NEW FILE########
__FILENAME__ = models
import json

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.timezone import now

from core.models import (
    Application, Environment, gunnery_name, Server, ServerRole)


class Task(models.Model):
    name = models.CharField(blank=False, max_length=128, validators=[gunnery_name()])
    description = models.TextField(blank=True)
    application = models.ForeignKey(Application, related_name="tasks")

    class Meta:
        unique_together = ("application", "name")
        permissions = (
        ("view_task", "Can view task"),
        ("edit_task", "Can edit task"),
        ("execute_task", "Can execute task"), )

    def get_absolute_url(self):
        return reverse('task_page', args=[str(self.id)])

    def executions_inline(self):
        return Execution.get_inline_by_task(self.id)

    def parameters_ordered(self):
        return self.parameters.order_by('order')

    def commands_ordered(self):
        return self.commands.order_by('order')


class TaskParameter(models.Model):
    task = models.ForeignKey(Task, related_name="parameters")
    name = models.CharField(blank=False, max_length=128, validators=[gunnery_name()])
    default_value = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    order = models.IntegerField()


class TaskCommand(models.Model):
    task = models.ForeignKey(Task, related_name="commands")
    command = models.TextField(blank=False)
    roles = models.ManyToManyField(ServerRole, related_name="commands")
    order = models.IntegerField()


class StateMixin(object):
    def save_start(self):
        self.time_start = now()
        self.status = self.RUNNING
        self.save()

    def save_end(self, status=None):
        self.time_end = now()
        if self.time_start:
            self.time = (self.time_end - self.time_start).seconds
        if status:
            self.status = status
        self.save()


class Execution(models.Model, StateMixin):
    PENDING = 3
    RUNNING = 0
    SUCCESS = 1
    FAILED = 2
    ABORTED = 4
    STATUS_CHOICES = (
        (PENDING, 'pending'),
        (RUNNING, 'running'),
        (SUCCESS, 'success'),
        (FAILED, 'failed'),
        (ABORTED, 'aborted'),
    )
    task = models.ForeignKey(Task, related_name="executions")
    time_created = models.DateTimeField(auto_now_add=True)
    time_start = models.DateTimeField(blank=True, null=True)
    time_end = models.DateTimeField(blank=True, null=True)
    time = models.IntegerField(blank=True, null=True)
    environment = models.ForeignKey(Environment, related_name="executions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="executions")
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    celery_task_id = models.CharField(blank=True, max_length=36)

    def get_absolute_url(self):
        return reverse('execution_page', args=[str(self.id)])

    def save(self, *args, **kwargs):
        is_new = not self.id
        super(Execution, self).save(*args, **kwargs)
        if not is_new:
            return
        for command in self.task.commands_ordered():
            self._create_execution_commands(command)

    def start(self):
        from backend.tasks import ExecutionTask

        ExecutionTask().delay(execution_id=self.id)

    def _create_execution_commands(self, command):
        parsed_command = command.command
        execution_command = ExecutionCommand(execution=self, command=parsed_command, order=command.order)
        execution_command.save()
        for role in command.roles.all():
            execution_command.roles.add(role)
        execution_command.save()
        self._create_execution_commands_servers(command, execution_command)

    def _create_execution_commands_servers(self, command, execution_command):
        for server in self.environment.servers.filter(roles__in=command.roles.all()):
            execution_command_server = ExecutionCommandServer(
                execution_command=execution_command,
                server=server)
            execution_command_server.save()

    @staticmethod
    def get_inline_by_query(**kwargs):
        return list(
            Execution.objects.filter(**kwargs).prefetch_related('user').prefetch_related('task').prefetch_related(
                'environment').order_by('-time_created')[:4])

    @staticmethod
    def get_inline_by_application(id):
        return Execution.get_inline_by_query(task__application_id=id)

    @staticmethod
    def get_inline_by_environment(id):
        return Execution.get_inline_by_query(environment_id=id)

    @staticmethod
    def get_inline_by_task(id):
        return Execution.get_inline_by_query(task_id=id)

    @staticmethod
    def get_inline_by_user(id):
        return Execution.get_inline_by_query(user_id=id)

    def commands_ordered(self):
        return self.commands.order_by('order')


class ExecutionParameter(models.Model):
    execution = models.ForeignKey(Execution, related_name="parameters")
    name = models.CharField(blank=False, max_length=128)
    value = models.CharField(max_length=128)


class ExecutionCommand(models.Model):
    execution = models.ForeignKey(Execution, related_name="commands")
    command = models.TextField()
    roles = models.ManyToManyField(ServerRole)
    order = models.IntegerField()


class ExecutionCommandServer(models.Model, StateMixin):
    PENDING = 3
    RUNNING = 0
    SUCCESS = 1
    FAILED = 2
    STATUS_CHOICES = (
        (PENDING, 'pending'),
        (RUNNING, 'running'),
        (SUCCESS, 'success'),
        (FAILED, 'failed'),
    )
    execution_command = models.ForeignKey(ExecutionCommand, related_name="servers")
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    time_start = models.DateTimeField(blank=True, null=True)
    time_end = models.DateTimeField(blank=True, null=True)
    time = models.IntegerField(blank=True, null=True)
    return_code = models.IntegerField(blank=True, null=True)
    server = models.ForeignKey(Server)
    # @todo store host, and ip here instead of relation to Server model
    output = models.TextField(blank=True)
    celery_task_id = models.CharField(blank=True, max_length=36)

    def get_live_log_output(self):
        live_logs = self.live_logs.values_list('output', flat=True)
        return ''.join(live_logs)


class ExecutionLiveLog(models.Model):
    execution = models.ForeignKey(Execution, related_name="live_logs")
    event = models.CharField(max_length=128)
    data = models.TextField(blank=True)

    @staticmethod
    def add(execution_id, name, data={}, **kwargs):
        """ Triggers execution event """
        data = dict(data.items() + kwargs.items())
        for key, value in data.items():
            if key.startswith('time_'):
                data[key] = value.strftime('%Y-%m-%d %H:%I')
        data = json.dumps(data, cls=DjangoJSONEncoder)
        ExecutionLiveLog(execution_id=execution_id, event=name, data=data).save()


class ParameterParser(object):
    parameter_format = '${%s}'
    global_parameters = {
        'gun_application': 'application name',
        'gun_environment': 'environment name',
        'gun_task': 'task name',
        'gun_user': 'user email',
        'gun_time': 'execution start timestamp'
    }

    def __init__(self, execution):
        self.execution = execution
        import calendar

        self.global_parameter_values = {
            'gun_application': self.execution.task.application.name,
            'gun_environment': self.execution.environment.name,
            'gun_task': self.execution.task.name,
            'gun_user': self.execution.user.email,
            'gun_time': str(calendar.timegm(self.execution.time_created.utctimetuple()))
        }

    def process(self, cmd):
        cmd = self._process_global_parameters(cmd)
        cmd = self._process_parameters(cmd)
        return cmd

    def _process_global_parameters(self, cmd):
        for name, value in self.global_parameter_values.items():
            cmd = cmd.replace(self.parameter_format % name, value)
        return cmd

    def _process_parameters(self, cmd):
        execution_params = self.execution.parameters.all()
        for param in execution_params:
            cmd = cmd.replace(self.parameter_format % param.name, param.value)
        return cmd
########NEW FILE########
__FILENAME__ = fixtures
from factory.django import DjangoModelFactory
import factory
from ..models import *
from core.tests.fixtures import ApplicationFactory


class TaskFactory(DjangoModelFactory):
    FACTORY_FOR = Task

    name = factory.Sequence(lambda n: 'Task_%s' % n)
    application = factory.SubFactory(ApplicationFactory)


########NEW FILE########
__FILENAME__ = test_views
from core.tests.base import LoggedTestCase
from .fixtures import *


class TaskTest(LoggedTestCase):
    def setUp(self):
        super(TaskTest, self).setUp()
        application = ApplicationFactory(department=self.department)
        self.task = TaskFactory(application=application)

    def test_task_form(self):
        response = self.client.get('/application/%d/task/' % self.task.application.id)
        self.assertContains(response, 'Add task')

    def test_task(self):
        response = self.client.get('/task/%d/' % self.task.id)
        self.assertContains(response, self.task.name)

    def test_execute(self):
        response = self.client.get('/task/%d/execute/' % self.task.id)
        self.assertContains(response, self.task.name)

    def test_list(self):
        response = self.client.get('/application/%d/' % self.task.application.id)
        self.assertContains(response, self.task.name)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from .views import (
    execution_abort, execution_page, live_log, log_page, task_delete,
    task_execute_page, task_form_page, task_page)


urlpatterns = patterns('',
    url(r'^application/(?P<application_id>[\d]+)/task/$', task_form_page, name='task_add_form_page'),
    url(r'^task/(?P<task_id>[\d]+)/execute/(?P<environment_id>[\d]+)/$', task_execute_page,
       name='task_execute_page'),
    url(r'^task/(?P<task_id>[\d]+)/execute/$', task_execute_page, name='task_execute_page'),
    url(r'^task/(?P<task_id>[\d]+)/edit/$', task_form_page, name='task_form_page'),
    url(r'^task/(?P<task_id>[\d]+)/delete/$', task_delete, name='task_delete'),
    url(r'^task/(?P<task_id>[\d]+)/$', task_page, name='task_page'),
    url(r'^execution/(?P<execution_id>[\d]+)/$', execution_page, name='execution_page'),
    url(r'^execution/live_log/(?P<execution_id>[\d]+)/(?P<last_id>[\d]+)/$', live_log,
       name='live_log'),
    url(r'^execution/(?P<execution_id>[\d]+)/abort/$', execution_abort, name='execution_abort'),

    url(r'^log/(?P<model_name>[a-z_]+)/(?P<id>[\d]+)/$', log_page, name='log'),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from account.decorators import has_permissions

from core.views import get_common_page_data
from .forms import task_create_form, TaskCommandFormset, TaskParameterFormset
from .models import (
    Application, Environment, Execution, ExecutionLiveLog, ExecutionParameter,
    ParameterParser, ServerRole, Task)


@has_permissions('task.Task')
def task_page(request, task_id=None):
    data = get_common_page_data(request)
    data['task'] = get_object_or_404(Task, pk=task_id)
    return render(request, 'page/task.html', data)


@transaction.atomic
@has_permissions('task.Task', 'task_id')
def task_execute_page(request, task_id, environment_id=None):
    data = get_common_page_data(request)
    task = get_object_or_404(Task, pk=task_id)
    data['task'] = task
    if environment_id:
        environment = get_object_or_404(Environment, pk=int(environment_id))
        data['environment'] = environment
        if task.application.id != environment.application.id:
            raise ValueError('task.application.id did not match with environment.application.id')

    if request.method == 'POST':
        parameter_prefix = 'parameter-'
        parameters = {}
        for name, value in request.POST.items():
            if name.startswith(parameter_prefix):
                name = name[len(parameter_prefix):]
                parameters[name] = value

        # @todo validate parameter names

        environment = get_object_or_404(Environment, pk=int(parameters['environment']))
        if task.application.id != environment.application.id:
            raise ValueError('task.application.id did not match with environment.application.id')

        duplicateExecution = Execution.objects.filter(task=task, environment=environment,
                                                      status__in=[Execution.PENDING, Execution.RUNNING])
        if duplicateExecution.count():
            data['duplicate_error'] = True
            data['task'] = task
            data['environment'] = environment
        else:
            execution = Execution(task=task, environment=environment, user=request.user)
            execution.save()

            for name, value in parameters.items():
                if name != 'environment':
                    ExecutionParameter(execution=execution, name=name, value=value).save()

            parameter_parser = ParameterParser(execution)
            for command in execution.commands.all():
                command.command = parameter_parser.process(command.command)
                command.save()
            execution.start()
            return redirect(execution)

    return render(request, 'page/task_execute.html', data)


@has_permissions('core.Application', 'application_id')
def task_form_page(request, application_id=None, task_id=None):
    data = get_common_page_data(request)
    if task_id:
        task = get_object_or_404(Task, pk=task_id)
        application = task.application
        data['task'] = task
        args = {}
    elif application_id:
        application = get_object_or_404(Application, pk=application_id)
        args = {'application_id': application_id}
    form, form_parameters, form_commands = create_forms(request, task_id, args)

    if request.method == 'POST':
        if form.is_valid() and form_parameters.is_valid() and form_commands.is_valid():
            task = form.save(commit=False)
            task.save()
            data['task'] = task
            task_save_formset(form_parameters, task)
            task_save_formset(form_commands, task)
            if task_id == None:
                return redirect(task.get_absolute_url())
            request.method = 'GET'
            form, form_parameters, form_commands = create_forms(request, task_id, args)
            request.method = 'POST'

    data['application'] = application
    data['is_new'] = task_id == None
    data['request'] = request
    data['form'] = form
    data['form_parameters'] = form_parameters
    data['form_commands'] = form_commands
    data['server_roles'] = ServerRole.objects.all()
    data['global_parameters'] = ParameterParser.global_parameters.items()
    return render(request, 'page/task_form.html', data)


def create_forms(request, task_id, args):
    form = task_create_form('task', request, task_id, args)
    form_parameters = create_formset(request, TaskParameterFormset, task_id)
    form_commands = create_formset(request, TaskCommandFormset, task_id)

    for form_command in form_commands.forms:
        form_command.fields['roles'].queryset = ServerRole.objects.filter(department_id=request.current_department_id)
    return (form, form_parameters, form_commands)


def task_save_formset(formset, task):
    formset.save(commit=False)
    for instance in formset.new_objects:
        instance.task_id = task.id
    for form in formset.ordered_forms:
        form.instance.order = form.cleaned_data['ORDER']
        form.instance.save()
    formset.save_m2m()


def create_formset(request, formset, parent_id):
    model = formset.model
    model_queryset = {
        'TaskParameter': model.objects.filter(task_id=parent_id).order_by('order'),
        'TaskCommand': model.objects.filter(task_id=parent_id).order_by('order')
    }
    if request.method == "POST":
        return formset(request.POST,
                       queryset=model_queryset[model.__name__],
                       prefix=model.__name__)
    else:
        return formset(queryset=model_queryset[model.__name__],
                       prefix=model.__name__)


@login_required
def log_page(request, model_name, id):
    #todo add custom permission check
    data = get_common_page_data(request)
    executions = Execution.objects
    if model_name == 'application':
        executions = executions.filter(environment__application_id=id)
        related = get_object_or_404(Application, pk=id)
    elif model_name == 'environment':
        executions = executions.filter(environment_id=id)
        related = get_object_or_404(Environment, pk=id)
    elif model_name == 'task':
        executions = executions.filter(task_id=id)
        related = get_object_or_404(Task, pk=id)
    elif model_name == 'user':
        executions = executions.filter(user_id=id)
        related = get_object_or_404(get_user_model(), pk=id)
    else:
        raise Http404()
    for related_model in ['task', 'user', 'environment', 'parameters']:
        executions = executions.prefetch_related(related_model)
    data['executions'] = executions.order_by('-time_created')
    data['model_name'] = model_name
    data['related'] = related
    return render(request, 'page/log.html', data)


@has_permissions('task.Execution')
def execution_page(request, execution_id):
    data = get_common_page_data(request)
    execution = get_object_or_404(Execution, pk=execution_id)
    data['execution'] = execution
    return render(request, 'page/execution.html', data)


@has_permissions('task.Task')
def task_delete(request, task_id):
    if request.method != 'POST':
        return Http404
    task = get_object_or_404(Task, pk=task_id)
    task.delete()
    data = {
        'status': True,
        'action': 'redirect',
        'target': task.application.get_absolute_url()
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


@has_permissions('task.Execution', 'execution_id')
def live_log(request, execution_id, last_id):
    data = ExecutionLiveLog.objects.filter(execution_id=execution_id, id__gt=last_id).order_by('id').values('id',
                                                                                                            'event',
                                                                                                            'data')
    return HttpResponse(json.dumps(list(data), cls=DjangoJSONEncoder), content_type="application/json")


@has_permissions('task.Execution', 'execution_id')
def execution_abort(request, execution_id):
    # if request.method != 'POST':
    #     return Http404
    execution = get_object_or_404(Execution, pk=execution_id)
    execution.status = execution.ABORTED
    execution.save_end()

    ExecutionLiveLog.add(execution_id, 'execution_completed', status=Execution.ABORTED,
                         time=execution.time,
                         time_end=execution.time_end)

    import signal
    from celery.result import AsyncResult
    if execution.celery_task_id:
        AsyncResult(execution.celery_task_id).revoke()
        for commands in execution.commands.all():
            for server in commands.servers.all():
                if server.celery_task_id:
                    AsyncResult(server.celery_task_id).revoke(terminate=True, signal=signal.SIGALRM)
    data = {}
    return HttpResponse(json.dumps(list(data), cls=DjangoJSONEncoder), content_type="application/json")
########NEW FILE########
