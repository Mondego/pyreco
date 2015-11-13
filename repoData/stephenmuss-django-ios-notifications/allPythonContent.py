__FILENAME__ = admin
# -*- coding: utf-8 -*-

try:
    from django.conf.urls import patterns, url
except ImportError:  # deprecated since Django 1.4
    from django.conf.urls.defaults import patterns, url

from django.contrib import admin
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from .models import Device, Notification, APNService, FeedbackService
from .forms import APNServiceForm


class APNServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'hostname')
    form = APNServiceForm


class DeviceAdmin(admin.ModelAdmin):
    fields = ('token', 'is_active', 'service')
    list_display = ('token', 'is_active', 'service', 'last_notified_at', 'platform', 'display', 'os_version', 'added_at', 'deactivated_at')
    list_filter = ('is_active', 'last_notified_at', 'added_at', 'deactivated_at')
    search_fields = ('token', 'platform')


class NotificationAdmin(admin.ModelAdmin):
    exclude = ('last_sent_at',)
    list_display = ('message', 'badge', 'sound', 'custom_payload', 'created_at', 'last_sent_at',)
    list_filter = ('created_at', 'last_sent_at')
    search_fields = ('message', 'custom_payload')
    list_display_links = ('message', 'custom_payload',)

    def get_urls(self):
        urls = super(NotificationAdmin, self).get_urls()
        notification_urls = patterns('',
                                     url(r'^(?P<id>\d+)/push-notification/$', self.admin_site.admin_view(self.admin_push_notification),
                                     name='admin_push_notification'),)
        return notification_urls + urls

    def admin_push_notification(self, request, **kwargs):
        notification = get_object_or_404(Notification, **kwargs)
        num_devices = 0
        if request.method == 'POST':
            service = notification.service
            num_devices = service.device_set.filter(is_active=True).count()
            notification.service.push_notification_to_devices(notification)
        return TemplateResponse(request, 'admin/ios_notifications/notification/push_notification.html',
                                {'notification': notification, 'num_devices': num_devices, 'sent': request.method == 'POST'},
                                current_app='ios_notifications')

admin.site.register(Device, DeviceAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(APNService, APNServiceAdmin)
admin.site.register(FeedbackService)

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
import re

from django.http import HttpResponseNotAllowed, QueryDict
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator

from .models import Device
from .forms import DeviceForm
from .decorators import api_authentication_required
from .http import HttpResponseNotImplemented, JSONResponse


class BaseResource(object):
    """
    The base class for any API Resources.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    @method_decorator(api_authentication_required)
    @csrf_exempt
    def route(self, request, **kwargs):
        method = request.method
        if method in self.allowed_methods:
            if hasattr(self, method.lower()):
                if method == 'PUT':
                    request.PUT = QueryDict(request.raw_post_data).copy()
                return getattr(self, method.lower())(request, **kwargs)

            return HttpResponseNotImplemented()

        return HttpResponseNotAllowed(self.allowed_methods)


class DeviceResource(BaseResource):
    """
    The API resource for ios_notifications.models.Device.

    Allowed HTTP methods are GET, POST and PUT.
    """
    allowed_methods = ('GET', 'POST', 'PUT')

    def get(self, request, **kwargs):
        """
        Returns an HTTP response with the device in serialized JSON format.
        The device token and device service are expected as the keyword arguments
        supplied by the URL.

        If the device does not exist a 404 will be raised.
        """
        device = get_object_or_404(Device, **kwargs)
        return JSONResponse(device)

    def post(self, request, **kwargs):
        """
        Creates a new device or updates an existing one to `is_active=True`.
        Expects two non-options POST parameters: `token` and `service`.
        """
        token = request.POST.get('token')
        if token is not None:
            # Strip out any special characters that may be in the token
            token = re.sub('<|>|\s', '', token)
        devices = Device.objects.filter(token=token,
                                        service__id=int(request.POST.get('service', 0)))
        if devices.exists():
            device = devices.get()
            device.is_active = True
            device.save()
            return JSONResponse(device)
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.is_active = True
            device.save()
            return JSONResponse(device, status=201)
        return JSONResponse(form.errors, status=400)

    def put(self, request, **kwargs):
        """
        Updates an existing device.

        If the device does not exist a 404 will be raised.

        The device token and device service are expected as the keyword arguments
        supplied by the URL.

        Any attributes to be updated should be supplied as parameters in the request
        body of any HTTP PUT request.
        """
        try:
            device = Device.objects.get(**kwargs)
        except Device.DoesNotExist:
            return JSONResponse({'error': 'Device with token %s and service %s does not exist' %
                                (kwargs['token'], kwargs['service__id'])}, status=400)

        if 'users' in request.PUT:
            try:
                user_ids = request.PUT.getlist('users')
                device.users.remove(*[u.id for u in device.users.all()])
                device.users.add(*User.objects.filter(id__in=user_ids))
            except (ValueError, IntegrityError) as e:
                return JSONResponse({'error': e.message}, status=400)
            del request.PUT['users']

        for key, value in request.PUT.items():
            setattr(device, key, value)
        device.save()

        return JSONResponse(device)


class Router(object):
    """
    A simple class for handling URL routes.
    """
    def __init__(self):
        self.device = DeviceResource().route

routes = Router()

########NEW FILE########
__FILENAME__ = decorators
import binascii

from django.contrib.auth import authenticate
from django.conf import settings

from .http import JSONResponse


class InvalidAuthenticationType(Exception):
    pass


# TODO: OAuth
VALID_AUTH_TYPES = ('AuthBasic', 'AuthBasicIsStaff', 'AuthNone')


def api_authentication_required(func):
    """
    Check the value of IOS_NOTIFICATIONS_AUTHENTICATION in settings
    and authenticate the request user appropriately.
    """
    def wrapper(request, *args, **kwargs):
        AUTH_TYPE = getattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', None)
        if AUTH_TYPE is None or AUTH_TYPE not in VALID_AUTH_TYPES:
            raise InvalidAuthenticationType('IOS_NOTIFICATIONS_AUTHENTICATION must be specified in your settings.py file.\
                    Valid options are "AuthBasic", "AuthBasicIsStaff" or "AuthNone"')
        # Basic Authorization
        elif AUTH_TYPE == 'AuthBasic' or AUTH_TYPE == 'AuthBasicIsStaff':
            if 'HTTP_AUTHORIZATION' in request.META:
                auth_type, encoded_user_password = request.META['HTTP_AUTHORIZATION'].split(' ')
                try:
                    userpass = encoded_user_password.decode('base64')
                except binascii.Error:
                    return JSONResponse({'error': 'invalid base64 encoded header'}, status=401)
                try:
                    username, password = userpass.split(':')
                except ValueError:
                    return JSONResponse({'error': 'malformed Authorization header'}, status=401)
                user = authenticate(username=username, password=password)
                if user is not None:
                    if AUTH_TYPE == 'AuthBasic' or user.is_staff:
                        return func(request, *args, **kwargs)
                return JSONResponse({'error': 'authentication error'}, status=401)
            return JSONResponse({'error': 'Authorization header not set'}, status=401)

        # AuthNone: No authorization.
        return func(request, *args, **kwargs)
    return wrapper

########NEW FILE########
__FILENAME__ = exceptions
class NotificationPayloadSizeExceeded(Exception):
    def __init__(self, message='The notification maximum payload size of 256 bytes was exceeded'):
        super(NotificationPayloadSizeExceeded, self).__init__(message)


class NotConnectedException(Exception):
    def __init__(self, message='You must open a socket connection before writing a message'):
        super(NotConnectedException, self).__init__(message)


class InvalidPassPhrase(Exception):
    def __init__(self, message='The passphrase for the private key appears to be invalid'):
        super(InvalidPassPhrase, self).__init__(message)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-

from django import forms
from django.forms.widgets import PasswordInput

import OpenSSL
from .models import Device, APNService


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device


class APNServiceForm(forms.ModelForm):
    class Meta:
        model = APNService

    START_CERT = '-----BEGIN CERTIFICATE-----'
    END_CERT = '-----END CERTIFICATE-----'
    START_KEY = '-----BEGIN RSA PRIVATE KEY-----'
    END_KEY = '-----END RSA PRIVATE KEY-----'
    START_ENCRYPTED_KEY = '-----BEGIN ENCRYPTED PRIVATE KEY-----'
    END_ENCRYPTED_KEY = '-----END ENCRYPTED PRIVATE KEY-----'

    passphrase = forms.CharField(widget=PasswordInput(render_value=True), required=False)

    def clean_certificate(self):
        if not self.START_CERT or not self.END_CERT in self.cleaned_data['certificate']:
            raise forms.ValidationError('Invalid certificate')
        return self.cleaned_data['certificate']

    def clean_private_key(self):
        has_start_phrase = self.START_KEY in self.cleaned_data['private_key'] \
            or self.START_ENCRYPTED_KEY in self.cleaned_data['private_key']
        has_end_phrase = self.END_KEY in self.cleaned_data['private_key'] \
            or self.END_ENCRYPTED_KEY in self.cleaned_data['private_key']
        if not has_start_phrase or not has_end_phrase:
            raise forms.ValidationError('Invalid private key')
        return self.cleaned_data['private_key']

    def clean_passphrase(self):
        passphrase = self.cleaned_data['passphrase']
        if passphrase is not None and len(passphrase) > 0:
            try:
                OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, self.cleaned_data['private_key'], str(passphrase))
            except OpenSSL.crypto.Error:
                raise forms.ValidationError('The passphrase for the private key appears to be invalid')
        return self.cleaned_data['passphrase']

########NEW FILE########
__FILENAME__ = http
import json

from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.core import serializers


class HttpResponseNotImplemented(HttpResponse):
    status_code = 501


class JSONResponse(HttpResponse):
    """
    A subclass of django.http.HttpResponse which serializes its content
    and returns a response with an application/json mimetype.
    """
    def __init__(self, content=None, content_type=None, status=None, mimetype='application/json'):
        content = self.serialize(content) if content is not None else ''
        super(JSONResponse, self).__init__(content, content_type, status, mimetype)

    def serialize(self, obj):
        json_s = serializers.get_serializer('json')()
        if isinstance(obj, QuerySet):
            return json_s.serialize(obj)
        elif isinstance(obj, dict):
            return json.dumps(obj)

        serialized_list = json_s.serialize([obj])
        m = json.loads(serialized_list)[0]
        return json.dumps(m)

########NEW FILE########
__FILENAME__ = call_feedback_service
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from ios_notifications.models import FeedbackService
from optparse import make_option

# TODO: argparse for Python 2.7


class Command(BaseCommand):
    help = 'Calls the Apple Feedback Service to determine which devices are no longer active and deactivates them in the database.'

    option_list = BaseCommand.option_list + (
        make_option('--feedback-service',
            help='The id of the Feedback Service to call',
            dest='service',
            default=None),)

    def handle(self, *args, **options):
        if options['service'] is None:
            raise CommandError('The --feedback-service option is required')
        try:
            service_id = int(options['service'])
        except ValueError:
            raise CommandError('The --feedback-service option should pass an id in integer format as its value')
        try:
            service = FeedbackService.objects.get(pk=service_id)
        except FeedbackService.DoesNotExist:
            raise CommandError('FeedbackService with id %d does not exist' % service_id)

        num_deactivated = service.call()
        output = '%d device%s deactivated.\n' % (num_deactivated, ' was' if num_deactivated == 1 else 's were')
        self.stdout.write(output)

########NEW FILE########
__FILENAME__ = push_ios_notification
# -*- coding: utf-8 -*-

from optparse import make_option
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from ios_notifications.models import Notification, APNService


class Command(BaseCommand):
    help = 'Create and immediately send a push notification to iOS devices'
    option_list = BaseCommand.option_list + (
        make_option('--message',
                    help='The main message to be sent in the notification',
                    dest='message',
                    default=''),
        make_option('--badge',
                    help='The badge number of the notification',
                    dest='badge',
                    default=None),
        make_option('--sound',
                    help='The sound for the notification',
                    dest='sound',
                    default=''),
        make_option('--service',
                    help='The id of the APN Service to send this notification through',
                    dest='service',
                    default=None),
        make_option('--extra',
                    help='Custom notification payload values as a JSON dictionary',
                    dest='extra',
                    default=None),
        make_option('--persist',
                    help='Save the notification in the database after pushing it.',
                    action='store_true',
                    dest='persist',
                    default=None),
        make_option('--no-persist',
                    help='Prevent saving the notification in the database after pushing it.',
                    action='store_false',
                    dest='persist'),  # Note: same dest as --persist; they are mutually exclusive
        make_option('--batch-size',
                    help='Notifications are sent to devices in batches via the APN Service. This controls the batch size. Default is 100.',
                    dest='chunk_size',
                    default=100),
    )

    def handle(self, *args, **options):
        if options['service'] is None:
            raise CommandError('The --service option is required')
        try:
            service_id = int(options['service'])
        except ValueError:
            raise CommandError('The --service option should pass an id in integer format as its value')
        if options['badge'] is not None:
            try:
                options['badge'] = int(options['badge'])
            except ValueError:
                raise CommandError('The --badge option should pass an integer as its value')
        try:
            service = APNService.objects.get(pk=service_id)
        except APNService.DoesNotExist:
            raise CommandError('APNService with id %d does not exist' % service_id)

        message = options['message']
        extra = options['extra']

        if not message and not extra:
            raise CommandError('To send a notification you must provide either the --message or --extra option.')

        notification = Notification(message=options['message'],
                                    badge=options['badge'],
                                    service=service,
                                    sound=options['sound'])

        if options['persist'] is not None:
            notification.persist = options['persist']

        if extra is not None:
            notification.extra = json.loads(extra)

        try:
            chunk_size = int(options['chunk_size'])
        except ValueError:
            raise CommandError('The --batch-size option should be an integer value.')

        if not notification.is_valid_length():
            raise CommandError('Notification exceeds the maximum payload length. Try making your message shorter.')

        service.push_notification_to_devices(notification, chunk_size=chunk_size)
        if 'test' not in sys.argv:
            self.stdout.write('Notification pushed successfully\n')

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'APNService'
        db.create_table('ios_notifications_apnservice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('certificate', self.gf('django.db.models.fields.TextField')()),
            ('private_key', self.gf('django.db.models.fields.TextField')()),
            ('passphrase', self.gf('django_fields.fields.EncryptedCharField')(max_length=101, null=True, cipher='AES', blank=True)),
        ))
        db.send_create_signal('ios_notifications', ['APNService'])

        # Adding unique constraint on 'APNService', fields ['name', 'hostname']
        db.create_unique('ios_notifications_apnservice', ['name', 'hostname'])

        # Adding model 'Notification'
        db.create_table('ios_notifications_notification', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ios_notifications.APNService'])),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('badge', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, null=True)),
            ('sound', self.gf('django.db.models.fields.CharField')(default='default', max_length=30, null=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_sent_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('ios_notifications', ['Notification'])

        # Adding model 'Device'
        db.create_table('ios_notifications_device', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('deactivated_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ios_notifications.APNService'])),
            ('added_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_notified_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('platform', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('display', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('os_version', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
        ))
        db.send_create_signal('ios_notifications', ['Device'])

        # Adding unique constraint on 'Device', fields ['token', 'service']
        db.create_unique('ios_notifications_device', ['token', 'service_id'])

        # Adding M2M table for field users on 'Device'
        db.create_table('ios_notifications_device_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('device', models.ForeignKey(orm['ios_notifications.device'], null=False)),
            (User._meta.module_name, self.gf('django.db.models.fields.related.ForeignKey')(to=User)),
        ))
        db.create_unique('ios_notifications_device_users', ['device_id', '%s_id' % User._meta.module_name])

        # Adding model 'FeedbackService'
        db.create_table('ios_notifications_feedbackservice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('apn_service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ios_notifications.APNService'])),
        ))
        db.send_create_signal('ios_notifications', ['FeedbackService'])

        # Adding unique constraint on 'FeedbackService', fields ['name', 'hostname']
        db.create_unique('ios_notifications_feedbackservice', ['name', 'hostname'])


    def backwards(self, orm):
        # Removing unique constraint on 'FeedbackService', fields ['name', 'hostname']
        db.delete_unique('ios_notifications_feedbackservice', ['name', 'hostname'])

        # Removing unique constraint on 'Device', fields ['token', 'service']
        db.delete_unique('ios_notifications_device', ['token', 'service_id'])

        # Removing unique constraint on 'APNService', fields ['name', 'hostname']
        db.delete_unique('ios_notifications_apnservice', ['name', 'hostname'])

        # Deleting model 'APNService'
        db.delete_table('ios_notifications_apnservice')

        # Deleting model 'Notification'
        db.delete_table('ios_notifications_notification')

        # Deleting model 'Device'
        db.delete_table('ios_notifications_device')

        # Removing M2M table for field users on 'Device'
        db.delete_table('ios_notifications_device_users')

        # Deleting model 'FeedbackService'
        db.delete_table('ios_notifications_feedbackservice')


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
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User._meta.module_name},
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ios_notifications.apnservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'APNService'},
            'certificate': ('django.db.models.fields.TextField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'passphrase': ('django_fields.fields.EncryptedCharField', [], {'max_length': '101', 'null': 'True', 'cipher': "'AES'", 'blank': 'True'}),
            'private_key': ('django.db.models.fields.TextField', [], {})
        },
        'ios_notifications.device': {
            'Meta': {'unique_together': "(('token', 'service'),)", 'object_name': 'Device'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deactivated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'display': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_notified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'platform': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'ios_devices'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name)})
        },
        'ios_notifications.feedbackservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'FeedbackService'},
            'apn_service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'ios_notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'badge': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_sent_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'sound': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '30', 'null': 'True'})
        }
    }

    complete_apps = ['ios_notifications']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_notification_custom_payload__chg_field_notification_so
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Notification.custom_payload'
        db.add_column('ios_notifications_notification', 'custom_payload',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=240, blank=True),
                      keep_default=False)


        # Changing field 'Notification.sound'
        if not db.dry_run:
            for notification in orm['ios_notifications.notification'].objects.all():
                if notification.sound is None:
                    notification.sound = ''
                    notification.save()
        db.alter_column('ios_notifications_notification', 'sound', self.gf('django.db.models.fields.CharField')(default='', max_length=30))

    def backwards(self, orm):
        # Deleting field 'Notification.custom_payload'
        db.delete_column('ios_notifications_notification', 'custom_payload')


        # Changing field 'Notification.sound'
        db.alter_column('ios_notifications_notification', 'sound', self.gf('django.db.models.fields.CharField')(max_length=30, null=True))

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
        'ios_notifications.apnservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'APNService'},
            'certificate': ('django.db.models.fields.TextField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'passphrase': ('django_fields.fields.EncryptedCharField', [], {'max_length': '101', 'null': 'True', 'cipher': "'AES'", 'blank': 'True'}),
            'private_key': ('django.db.models.fields.TextField', [], {})
        },
        'ios_notifications.device': {
            'Meta': {'unique_together': "(('token', 'service'),)", 'object_name': 'Device'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deactivated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'display': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_notified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'platform': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'ios_devices'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"})
        },
        'ios_notifications.feedbackservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'FeedbackService'},
            'apn_service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'ios_notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'badge': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'custom_payload': ('django.db.models.fields.CharField', [], {'max_length': '240', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_sent_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'sound': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        }
    }

    complete_apps = ['ios_notifications']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import socket
import struct
import errno
import json
from binascii import hexlify, unhexlify

from django.db import models
from django.conf import settings

try:
    from django.utils.timezone import now as dt_now
except ImportError:
    import datetime
    dt_now = datetime.datetime.now

from django_fields.fields import EncryptedCharField
import OpenSSL

from .exceptions import NotificationPayloadSizeExceeded, InvalidPassPhrase


class BaseService(models.Model):
    """
    A base service class intended to be subclassed.
    """
    name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    PORT = 0  # Should be overriden by subclass
    connection = None

    def _connect(self, certificate, private_key, passphrase=None):
        """
        Establishes an encrypted SSL socket connection to the service.
        After connecting the socket can be written to or read from.
        """
        # ssl in Python < 3.2 does not support certificates/keys as strings.
        # See http://bugs.python.org/issue3823
        # Therefore pyOpenSSL which lets us do this is a dependancy.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
        args = [OpenSSL.crypto.FILETYPE_PEM, private_key]
        if passphrase is not None:
            args.append(str(passphrase))
        try:
            pkey = OpenSSL.crypto.load_privatekey(*args)
        except OpenSSL.crypto.Error:
            raise InvalidPassPhrase
        context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv3_METHOD)
        context.use_certificate(cert)
        context.use_privatekey(pkey)
        self.connection = OpenSSL.SSL.Connection(context, sock)
        self.connection.connect((self.hostname, self.PORT))
        self.connection.set_connect_state()
        self.connection.do_handshake()

    def _disconnect(self):
        """
        Closes the SSL socket connection.
        """
        if self.connection is not None:
            self.connection.shutdown()
            self.connection.close()

    class Meta:
        abstract = True


class APNService(BaseService):
    """
    Represents an Apple Notification Service either for live
    or sandbox notifications.

    `private_key` is optional if both the certificate and key are provided in
    `certificate`.
    """
    certificate = models.TextField()
    private_key = models.TextField()
    passphrase = EncryptedCharField(
        null=True, blank=True, help_text='Passphrase for the private key',
        block_type='MODE_CBC')

    PORT = 2195
    fmt = '!cH32sH%ds'

    def _connect(self):
        """
        Establishes an encrypted SSL socket connection to the service.
        After connecting the socket can be written to or read from.
        """
        return super(APNService, self)._connect(self.certificate, self.private_key, self.passphrase)

    def push_notification_to_devices(self, notification, devices=None, chunk_size=100):
        """
        Sends the specific notification to devices.
        if `devices` is not supplied, all devices in the `APNService`'s device
        list will be sent the notification.
        """
        if devices is None:
            devices = self.device_set.filter(is_active=True)
        self._write_message(notification, devices, chunk_size)

    def _write_message(self, notification, devices, chunk_size):
        """
        Writes the message for the supplied devices to
        the APN Service SSL socket.
        """
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        if not isinstance(chunk_size, int) or chunk_size < 1:
            raise ValueError('chunk_size must be an integer greater than zero.')

        payload = notification.payload

        # Split the devices into manageable chunks.
        # Chunk sizes being determined by the `chunk_size` arg.
        device_length = devices.count() if isinstance(devices, models.query.QuerySet) else len(devices)
        chunks = [devices[i:i + chunk_size] for i in xrange(0, device_length, chunk_size)]

        for index in xrange(len(chunks)):
            chunk = chunks[index]
            self._connect()

            for device in chunk:
                if not device.is_active:
                    continue
                try:
                    self.connection.send(self.pack_message(payload, device))
                except (OpenSSL.SSL.WantWriteError, socket.error) as e:
                    if isinstance(e, socket.error) and isinstance(e.args, tuple) and e.args[0] != errno.EPIPE:
                        raise e  # Unexpected exception, raise it.
                    self._disconnect()
                    i = chunk.index(device)
                    self.set_devices_last_notified_at(chunk[:i])
                    # Start again from the next device.
                    # We start from the next device since
                    # if the device no longer accepts push notifications from your app
                    # and you send one to it anyways, Apple immediately drops the connection to your APNS socket.
                    # http://stackoverflow.com/a/13332486/1025116
                    self._write_message(notification, chunk[i + 1:], chunk_size)

            self._disconnect()

            self.set_devices_last_notified_at(chunk)

        if notification.pk or notification.persist:
            notification.last_sent_at = dt_now()
            notification.save()

    def set_devices_last_notified_at(self, devices):
        # Rather than do a save on every object,
        # fetch another queryset and use it to update
        # the devices in a single query.
        # Since the devices argument could be a sliced queryset
        # we can't rely on devices.update() even if devices is
        # a queryset object.
        Device.objects.filter(pk__in=[d.pk for d in devices]).update(last_notified_at=dt_now())

    def pack_message(self, payload, device):
        """
        Converts a notification payload into binary form.
        """
        if len(payload) > 256:
            raise NotificationPayloadSizeExceeded
        if not isinstance(device, Device):
            raise TypeError('device must be an instance of ios_notifications.models.Device')

        msg = struct.pack(self.fmt % len(payload), chr(0), 32, unhexlify(device.token), len(payload), payload)
        return msg

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'hostname')


class Notification(models.Model):
    """
    Represents a notification which can be pushed to an iOS device.
    """
    service = models.ForeignKey(APNService)
    message = models.CharField(max_length=200, blank=True, help_text='Alert message to display to the user. Leave empty if no alert should be displayed to the user.')
    badge = models.PositiveIntegerField(null=True, blank=True, help_text='New application icon badge number. Set to None if the badge number must not be changed.')
    sound = models.CharField(max_length=30, blank=True, help_text='Name of the sound to play. Leave empty if no sound should be played.')
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    custom_payload = models.CharField(max_length=240, blank=True, help_text='JSON representation of an object containing custom payload.')

    def __init__(self, *args, **kwargs):
        self.persist = getattr(settings, 'IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS', True)
        super(Notification, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s%s%s' % (self.message, ' ' if self.message and self.custom_payload else '', self.custom_payload)

    @property
    def extra(self):
        """
        The extra property is used to specify custom payload values
        outside the Apple-reserved aps namespace
        http://developer.apple.com/library/mac/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/ApplePushService/ApplePushService.html#//apple_ref/doc/uid/TP40008194-CH100-SW1
        """
        return json.loads(self.custom_payload) if self.custom_payload else None

    @extra.setter
    def extra(self, value):
        if value is None:
            self.custom_payload = ''
        else:
            if not isinstance(value, dict):
                raise TypeError('must be a valid Python dictionary')
            self.custom_payload = json.dumps(value)  # Raises a TypeError if can't be serialized

    def push_to_all_devices(self):
        """
        Pushes this notification to all active devices using the
        notification's related APN service.
        """
        self.service.push_notification_to_devices(self)

    def is_valid_length(self):
        """
        Determines if a notification payload is a valid length.

        returns bool
        """
        return len(self.payload) <= 256

    @property
    def payload(self):
        aps = {}
        if self.message:
            aps['alert'] = self.message
        if self.badge is not None:
            aps['badge'] = self.badge
        if self.sound:
            aps['sound'] = self.sound
        message = {'aps': aps}
        extra = self.extra
        if extra is not None:
            message.update(extra)
        payload = json.dumps(message, separators=(',', ':'))
        return payload


class Device(models.Model):
    """
    Represents an iOS device with unique token.
    """
    token = models.CharField(max_length=64, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    service = models.ForeignKey(APNService)
    users = models.ManyToManyField(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True, blank=True, related_name='ios_devices')
    added_at = models.DateTimeField(auto_now_add=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    platform = models.CharField(max_length=30, blank=True, null=True)
    display = models.CharField(max_length=30, blank=True, null=True)
    os_version = models.CharField(max_length=20, blank=True, null=True)

    def push_notification(self, notification):
        """
        Pushes a ios_notifications.models.Notification instance to an the device.
        For more details see http://developer.apple.com/library/mac/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/ApplePushService/ApplePushService.html
        """
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        self.service.push_notification_to_devices(notification, [self])

    def __unicode__(self):
        return self.token

    class Meta:
        unique_together = ('token', 'service')


class FeedbackService(BaseService):
    """
    The service provided by Apple to inform you of devices which no longer have your app installed
    and to which notifications have failed a number of times. Use this class to check the feedback
    service and deactivate any devices it informs you about.

    https://developer.apple.com/library/ios/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CommunicatingWIthAPS/CommunicatingWIthAPS.html#//apple_ref/doc/uid/TP40008194-CH101-SW3
    """
    apn_service = models.ForeignKey(APNService)

    PORT = 2196

    fmt = '!lh32s'

    def _connect(self):
        """
        Establishes an encrypted socket connection to the feedback service.
        """
        return super(FeedbackService, self)._connect(self.apn_service.certificate, self.apn_service.private_key, self.apn_service.passphrase)

    def call(self):
        """
        Calls the feedback service and deactivates any devices the feedback service mentions.
        """
        self._connect()
        device_tokens = []
        try:
            while True:
                data = self.connection.recv(38)  # 38 being the length in bytes of the binary format feedback tuple.
                timestamp, token_length, token = struct.unpack(self.fmt, data)
                device_token = hexlify(token)
                device_tokens.append(device_token)
        except OpenSSL.SSL.ZeroReturnError:
            # Nothing to receive
            pass
        finally:
            self._disconnect()
        devices = Device.objects.filter(token__in=device_tokens, service=self.apn_service)
        devices.update(is_active=False, deactivated_at=dt_now())
        return devices.count()

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'hostname')

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import subprocess
import struct
import os
import json
import uuid
import StringIO

import django
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseNotAllowed
from django.conf import settings
from django.core import management

try:
    from django.utils.timezone import now as dt_now
except ImportError:
    import datetime
    dt_now = datetime.datetime.now

from .models import APNService, Device, Notification, NotificationPayloadSizeExceeded
from .http import JSONResponse
from .utils import generate_cert_and_pkey
from .forms import APNServiceForm

TOKEN = '0fd12510cfe6b0a4a89dc7369c96df956f991e66131dab63398734e8000d0029'
TEST_PEM = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test.pem'))

SSL_SERVER_COMMAND = ('openssl', 's_server', '-accept', '2195', '-cert', TEST_PEM)


class APNServiceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_server_proc = subprocess.Popen(SSL_SERVER_COMMAND, stdout=subprocess.PIPE)

    def setUp(self):
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='test-service', hostname='127.0.0.1',
                                                 certificate=cert, private_key=key)

        self.device = Device.objects.create(token=TOKEN, service=self.service)
        self.notification = Notification.objects.create(message='Test message', service=self.service)

    def test_invalid_payload_size(self):
        n = Notification(message='.' * 250)
        self.assertRaises(NotificationPayloadSizeExceeded, self.service.pack_message, n.payload, self.device)

    def test_payload_packed_correctly(self):
        fmt = self.service.fmt
        payload = self.notification.payload
        msg = self.service.pack_message(payload, self.device)
        unpacked = struct.unpack(fmt % len(payload), msg)
        self.assertEqual(unpacked[-1], payload)

    def test_pack_message_with_invalid_device(self):
        self.assertRaises(TypeError, self.service.pack_message, None)

    def test_can_connect_and_push_notification(self):
        self.assertIsNone(self.notification.last_sent_at)
        self.assertIsNone(self.device.last_notified_at)
        self.service.push_notification_to_devices(self.notification, [self.device])
        self.assertIsNotNone(self.notification.last_sent_at)
        self.device = Device.objects.get(pk=self.device.pk)  # Refresh the object with values from db
        self.assertIsNotNone(self.device.last_notified_at)

    def test_create_with_passphrase(self):
        cert, key = generate_cert_and_pkey(as_string=True, passphrase='pass')
        form = APNServiceForm({'name': 'test', 'hostname': 'localhost', 'certificate': cert, 'private_key': key, 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())

    def test_create_with_invalid_passphrase(self):
        cert, key = generate_cert_and_pkey(as_string=True, passphrase='correct')
        form = APNServiceForm({'name': 'test', 'hostname': 'localhost', 'certificate': cert, 'private_key': key, 'passphrase': 'incorrect'})
        self.assertFalse(form.is_valid())
        self.assertTrue('passphrase' in form.errors)

    def test_pushing_notification_in_chunks(self):
        devices = []
        for i in xrange(10):
            token = uuid.uuid1().get_hex() * 2
            device = Device.objects.create(token=token, service=self.service)
            devices.append(device)

        started_at = dt_now()
        self.service.push_notification_to_devices(self.notification, devices, chunk_size=2)
        device_count = len(devices)
        self.assertEquals(device_count,
                          Device.objects.filter(last_notified_at__gte=started_at).count())

    @classmethod
    def tearDownClass(cls):
        cls.test_server_proc.kill()


class APITest(TestCase):
    urls = 'ios_notifications.urls'

    def setUp(self):
        self.service = APNService.objects.create(name='sandbox', hostname='gateway.sandbox.push.apple.com')
        self.device_token = TOKEN
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.AUTH = getattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'NotSpecified')
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthNone')
        self.device = Device.objects.create(service=self.service, token='0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029')

    def test_register_device_invalid_params(self):
        """
        Test that sending a POST request to the device API
        without POST parameters `token` and `service` results
        in a 400 bad request response.
        """
        resp = self.client.post(reverse('ios-notifications-device-create'))
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(isinstance(resp, JSONResponse))
        content = json.loads(resp.content)
        keys = content.keys()
        self.assertTrue('token' in keys and 'service' in keys)

    def test_register_device(self):
        """
        Test a device is created when calling the API with the correct
        POST parameters.
        """
        resp = self.client.post(reverse('ios-notifications-device-create'),
                                {'token': self.device_token,
                                 'service': self.service.id})

        self.assertEqual(resp.status_code, 201)
        self.assertTrue(isinstance(resp, JSONResponse))
        content = resp.content
        device_json = json.loads(content)
        self.assertEqual(device_json.get('model'), 'ios_notifications.device')

    def test_disallowed_method(self):
        resp = self.client.delete(reverse('ios-notifications-device-create'))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(isinstance(resp, HttpResponseNotAllowed))

    def test_update_device(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        resp = self.client.put(url, 'users=%d&platform=iPhone' % self.user.id,
                               content_type='application/x-www-form-urlencode')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(isinstance(resp, JSONResponse))
        device_json = json.loads(resp.content)
        self.assertEqual(device_json.get('pk'), self.device.id)
        self.assertTrue(self.user in self.device.users.all())

    def test_get_device_details(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content
        device_json = json.loads(content)
        self.assertEqual(device_json.get('model'), 'ios_notifications.device')

    def tearDown(self):
        if self.AUTH == 'NotSpecified':
            del settings.IOS_NOTIFICATIONS_AUTHENTICATION
        else:
            setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', self.AUTH)


class AuthenticationDecoratorTestAuthBasic(TestCase):
    urls = 'ios_notifications.urls'

    def setUp(self):
        self.service = APNService.objects.create(name='sandbox', hostname='gateway.sandbox.push.apple.com')
        self.device_token = TOKEN
        self.user_password = 'abc123'
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password(self.user_password)
        self.user.is_staff = True
        self.user.save()

        self.AUTH = getattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'NotSpecified')
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        self.device = Device.objects.create(service=self.service, token='0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029')

    def test_basic_authorization_request(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        resp = self.client.get(url, {}, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 200)

    def test_basic_authorization_request_invalid_credentials(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        user_pass = '%s:%s' % (self.user.username, 'invalidpassword')
        auth_header = 'Basic %s' % user_pass.encode('base64')
        url = reverse('ios-notifications-device-create')
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('authentication error' in resp.content)

    def test_basic_authorization_missing_header(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        url = reverse('ios-notifications-device-create')
        resp = self.client.get(url)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('Authorization header not set' in resp.content)

    def test_invalid_authentication_type(self):
        from ios_notifications.decorators import InvalidAuthenticationType
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthDoesNotExist')
        url = reverse('ios-notifications-device-create')
        self.assertRaises(InvalidAuthenticationType, self.client.get, url)

    def test_basic_authorization_is_staff(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasicIsStaff')
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        self.user.is_staff = True
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 200)

    def test_basic_authorization_is_staff_with_non_staff_user(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasicIsStaff')
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        self.user.is_staff = False
        self.user.save()
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('authentication error' in resp.content)

    def tearDown(self):
        if self.AUTH == 'NotSpecified':
            del settings.IOS_NOTIFICATIONS_AUTHENTICATION
        else:
            setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', self.AUTH)


class NotificationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_server_proc = subprocess.Popen(SSL_SERVER_COMMAND, stdout=subprocess.PIPE)

    def setUp(self):
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='service', hostname='127.0.0.1',
                                                 private_key=key, certificate=cert)
        self.service.PORT = 2195  # For ease of use simply change port to default port in test_server
        self.custom_payload = json.dumps({"." * 10: "." * 50})
        self.notification = Notification.objects.create(service=self.service, message='Test message', custom_payload=self.custom_payload)

    def test_valid_length(self):
        self.notification.message = 'test message'
        self.assertTrue(self.notification.is_valid_length())

    def test_invalid_length(self):
        self.notification.message = '.' * 250
        self.assertFalse(self.notification.is_valid_length())

    def test_invalid_length_with_custom_payload(self):
        self.notification.message = '.' * 100
        self.notification.custom_payload = '{"%s":"%s"}' % ("." * 20, "." * 120)
        self.assertFalse(self.notification.is_valid_length())

    def test_extra_property_with_custom_payload(self):
        custom_payload = {"." * 10: "." * 50, "nested": {"+" * 10: "+" * 50}}
        self.notification.extra = custom_payload
        self.assertEqual(self.notification.custom_payload, json.dumps(custom_payload))
        self.assertEqual(self.notification.extra, custom_payload)
        self.assertTrue(self.notification.is_valid_length())

    def test_extra_property_not_dict(self):
        with self.assertRaises(TypeError):
            self.notification.extra = 111

    def test_extra_property_none(self):
        self.notification.extra = None
        self.assertEqual(self.notification.extra, None)
        self.assertEqual(self.notification.custom_payload, '')
        self.assertTrue(self.notification.is_valid_length())

    def test_push_to_all_devices_persist_existing(self):
        self.assertIsNone(self.notification.last_sent_at)
        self.notification.persist = False
        self.notification.push_to_all_devices()
        self.assertIsNotNone(self.notification.last_sent_at)

    def test_push_to_all_devices_persist_new(self):
        notification = Notification(service=self.service, message='Test message (new)')
        notification.persist = True
        notification.push_to_all_devices()
        self.assertIsNotNone(notification.last_sent_at)
        self.assertIsNotNone(notification.pk)

    def test_push_to_all_devices_no_persist(self):
        notification = Notification(service=self.service, message='Test message (new)')
        notification.persist = False
        notification.push_to_all_devices()
        self.assertIsNone(notification.last_sent_at)
        self.assertIsNone(notification.pk)

    @classmethod
    def tearDownClass(cls):
        cls.test_server_proc.kill()


class ManagementCommandPushNotificationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_server_proc = subprocess.Popen(SSL_SERVER_COMMAND, stdout=subprocess.PIPE)

    def setUp(self):
        self.started_at = dt_now()
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='service', hostname='127.0.0.1',
                                                 private_key=key, certificate=cert)
        self.service.PORT = 2195
        self.device = Device.objects.create(token=TOKEN, service=self.service)

        self.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS = getattr(settings, 'IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS', 'NotSpecified')

    def test_call_push_ios_notification_command_persist(self):
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0, 'persist': True})
        self.assertTrue(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_call_push_ios_notification_command_no_persist(self):
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0, 'persist': False})
        self.assertFalse(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_call_push_ios_notification_command_default_persist(self):
        msg = 'some message'
        settings.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS = True
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0})
        self.assertTrue(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_call_push_ios_notification_command_default_no_persist(self):
        msg = 'some message'
        settings.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS = False
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0})
        self.assertFalse(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_call_push_ios_notification_command_default_persist_not_specified(self):
        msg = 'some message'
        if hasattr(settings, 'IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS'):
            del settings.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0})
        self.assertTrue(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_either_message_or_extra_option_required(self):
        # In Django < 1.5 django.core.management.base.BaseCommand.execute
        # catches CommandError and raises SystemExit instead.
        exception = SystemExit if django.VERSION < (1, 5) else management.base.CommandError

        with self.assertRaises(exception):
            management.call_command('push_ios_notification', service=self.service.pk,
                                    verbosity=0, stderr=StringIO.StringIO())

    def tearDown(self):
        if self.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS == 'NotSpecified':
            if hasattr(settings, 'IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS'):
                del settings.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS
        else:
            settings.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS = self.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS

    @classmethod
    def tearDownClass(cls):
        cls.test_server_proc.kill()


class ManagementCommandCallFeedbackService(TestCase):
    pass

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

try:
    from django.conf.urls import patterns, url
except ImportError:  # deprecated since Django 1.4
    from django.conf.urls.defaults import patterns, url

from .api import routes

urlpatterns = patterns('',
    url(r'^device/$', routes.device, name='ios-notifications-device-create'),
    url(r'^device/(?P<token>\w+)/(?P<service__id>\d+)/$', routes.device, name='ios-notifications-device'),
)

########NEW FILE########
__FILENAME__ = utils
import OpenSSL


def generate_cert_and_pkey(as_string=True, passphrase=None):
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    cert = OpenSSL.crypto.X509()
    cert.set_version(3)
    cert.set_serial_number(1)
    cert.get_subject().CN = '127.0.0.1'
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha1')
    if as_string:
        args = [OpenSSL.crypto.FILETYPE_PEM, key]
        if passphrase is not None:
            args += ['DES3', passphrase]
        cert = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        key = OpenSSL.crypto.dump_privatekey(*args)
    return cert, key

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys
sys.path.insert(0, os.path.abspath('./../../'))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
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
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'c8+4^x2s-j3_ucbbh@r2#&)anj&k3#(u(w-)k&7&t)k&3b03#u'

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

ROOT_URLCONF = 'testapp.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'testapp.wsgi.application'

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
    'ios_notifications',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

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
    url(r'^ios-notifications/', include('ios_notifications.urls')),
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^testapp/', include('testapp.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testapp project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "testapp.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
