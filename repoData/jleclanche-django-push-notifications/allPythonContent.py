__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import APNSDevice, GCMDevice


class DeviceAdmin(admin.ModelAdmin):
	list_display = ("__unicode__", "device_id", "user", "active", "date_created")
	search_fields = ("name", "device_id", "user__username")
	list_filter = ("active", )
	actions = ("send_message", "send_bulk_message", "enable", "disable")

	def send_message(self, request, queryset):
		ret = []
		errors = []
		r = ""
		for device in queryset:
			try:
				r = device.send_message("Test single notification")
			except Exception as e:
				errors.append(str(e))
			if r:
				ret.append(r)
		if errors:
			self.message_user(request, _("Some messages could not be processed: %r" % ("\n".join(errors))))
		if ret:
			self.message_user(request, _("All messages were sent: %s" % ("\n".join(ret))))
	send_message.short_description = _("Send test message")

	def send_bulk_message(self, request, queryset):
		r = queryset.send_message("Test bulk notification")
		self.message_user(request, _("All messages were sent: %s" % (r)))
	send_bulk_message.short_description = _("Send test message in bulk")

	def enable(self, request, queryset):
		queryset.update(active=True)
	enable.short_description = _("Enable selected devices")

	def disable(self, request, queryset):
		queryset.update(active=False)
	disable.short_description = _("Disable selected devices")


admin.site.register(APNSDevice, DeviceAdmin)
admin.site.register(GCMDevice, DeviceAdmin)

########NEW FILE########
__FILENAME__ = api
from tastypie.authorization import Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.resources import ModelResource
from .models import APNSDevice, GCMDevice


class APNSDeviceResource(ModelResource):
	class Meta:
		authorization = Authorization()
		queryset = APNSDevice.objects.all()
		resource_name = "device/apns"


class GCMDeviceResource(ModelResource):
	class Meta:
		authorization = Authorization()
		queryset = GCMDevice.objects.all()
		resource_name = "device/gcm"


class APNSDeviceAuthenticatedResource(APNSDeviceResource):
	# user = ForeignKey(UserResource, "user")

	class Meta(APNSDeviceResource.Meta):
		authentication = BasicAuthentication()
		# authorization = SameUserAuthorization()

	def obj_create(self, bundle, **kwargs):
		# See https://github.com/toastdriven/django-tastypie/issues/854
		return super(APNSDeviceAuthenticatedResource, self).obj_create(bundle, user=bundle.request.user, **kwargs)


class GCMDeviceAuthenticatedResource(GCMDeviceResource):
	# user = ForeignKey(UserResource, "user")

	class Meta(GCMDeviceResource.Meta):
		authentication = BasicAuthentication()
		# authorization = SameUserAuthorization()

	def obj_create(self, bundle, **kwargs):
		# See https://github.com/toastdriven/django-tastypie/issues/854
		return super(GCMDeviceAuthenticatedResource, self).obj_create(bundle, user=bundle.request.user, **kwargs)

########NEW FILE########
__FILENAME__ = apns
"""
Apple Push Notification Service
Documentation is available on the iOS Developer Library:
https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/ApplePushService.html
"""

import json
import ssl
import struct
import socket
import time
from contextlib import closing
from binascii import unhexlify
from django.core.exceptions import ImproperlyConfigured
from . import NotificationError
from .settings import PUSH_NOTIFICATIONS_SETTINGS as SETTINGS


class APNSError(NotificationError):
	pass


class APNSServerError(APNSError):
	def __init__(self, status, identifier):
		super(APNSServerError, self).__init__(status, identifier)
		self.status = status
		self.identifier = identifier


class APNSDataOverflow(APNSError):
	pass


APNS_MAX_NOTIFICATION_SIZE = 256


def _apns_create_socket():
	certfile = SETTINGS.get("APNS_CERTIFICATE")
	if not certfile:
		raise ImproperlyConfigured(
			'You need to set PUSH_NOTIFICATIONS_SETTINGS["APNS_CERTIFICATE"] to send messages through APNS.'
		)

	try:
		with open(certfile, "r") as f:
			f.read()
	except Exception as e:
		raise ImproperlyConfigured("The APNS certificate file at %r is not readable: %s" % (certfile, e))

	sock = socket.socket()
	sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3, certfile=certfile)
	sock.connect((SETTINGS["APNS_HOST"], SETTINGS["APNS_PORT"]))

	return sock


def _apns_pack_frame(token_hex, payload, identifier, expiration, priority):
	token = unhexlify(token_hex)
	# |COMMAND|FRAME-LEN|{token}|{payload}|{id:4}|{expiration:4}|{priority:1}
	frame_len = 3 * 5 + len(token) + len(payload) + 4 + 4 + 1  # 5 items, each 3 bytes prefix, then each item length
	frame_fmt = "!BIBH%ssBH%ssBHIBHIBHB" % (len(token), len(payload))
	frame = struct.pack(
		frame_fmt,
		2, frame_len,
		1, len(token), token,
		2, len(payload), payload,
		3, 4, identifier,
		4, 4, expiration,
		5, 1, priority)

	return frame


def _apns_check_errors(sock):
	timeout = SETTINGS["APNS_ERROR_TIMEOUT"]
	if timeout is None:
		return  # assume everything went fine!
	saved_timeout = sock.gettimeout()
	try:
		sock.settimeout(timeout)
		data = sock.recv(6)
		if data:
			command, status, identifier = struct.unpack("!BBI", data)
			# apple protocol says command is always 8. See http://goo.gl/ENUjXg
			assert command == 8, "Command must be 8!"
			if status != 0:
				raise APNSServerError(status, identifier)
	except socket.timeout:  # py3
		pass
	except ssl.SSLError as e:  # py2
		if "timed out" not in e.message:
			raise
	finally:
		sock.settimeout(saved_timeout)


def _apns_send(token, alert, badge=0, sound=None, content_available=False, action_loc_key=None, loc_key=None,
				loc_args=[], extra={}, identifier=0, expiration=None, priority=10, socket=None):
	data = {}
	aps_data = {}

	if action_loc_key or loc_key or loc_args:
		alert = {"body": alert} if alert else {}
		if action_loc_key:
			alert["action-loc-key"] = action_loc_key
		if loc_key:
			alert["loc-key"] = loc_key
		if loc_args:
			alert["loc-args"] = loc_args

	if alert is not None:
		aps_data["alert"] = alert

	if badge:
		aps_data["badge"] = badge

	if sound is not None:
		aps_data["sound"] = sound

	if content_available:
		aps_data["content-available"] = 1

	data["aps"] = aps_data
	data.update(extra)

	# convert to json, avoiding unnecessary whitespace with separators
	json_data = json.dumps(data, separators=(",", ":"))

	if len(json_data) > APNS_MAX_NOTIFICATION_SIZE:
		raise APNSDataOverflow("Notification body cannot exceed %i bytes" % (APNS_MAX_NOTIFICATION_SIZE))

	# if expiration isn't specified use 1 month from now
	expiration_time = expiration if expiration is not None else int(time.time()) + 2592000

	frame = _apns_pack_frame(token, json_data, identifier, expiration_time, priority)

	if socket:
		socket.write(frame)
	else:
		with closing(_apns_create_socket()) as socket:
			socket.write(frame)
			_apns_check_errors(socket)


def apns_send_message(registration_id, alert, **kwargs):
	"""
	Sends an APNS notification to a single registration_id.
	This will send the notification as form data.
	If sending multiple notifications, it is more efficient to use
	apns_send_bulk_message()

	Note that if set alert should always be a string. If it is not set,
	it won't be included in the notification. You will need to pass None
	to this for silent notifications.
	"""

	return _apns_send(registration_id, alert, **kwargs)


def apns_send_bulk_message(registration_ids, alert, **kwargs):
	"""
	Sends an APNS notification to one or more registration_ids.
	The registration_ids argument needs to be a list.

	Note that if set alert should always be a string. If it is not set,
	it won't be included in the notification. You will need to pass None
	to this for silent notifications.
	"""
	with closing(_apns_create_socket()) as socket:
		for identifier, registration_id in enumerate(registration_ids):
			_apns_send(registration_id, alert, identifier=identifier, socket=socket, **kwargs)
		_apns_check_errors(socket)

########NEW FILE########
__FILENAME__ = fields
import re
import struct
from django import forms
from django.core.validators import RegexValidator
from django.db import models, connection
from django.utils.translation import ugettext_lazy as _

try:
	from django.utils.six import with_metaclass
except ImportError:
	from six import with_metaclass


__all__ = ["HexadecimalField", "HexIntegerField"]

hex_re = re.compile(r"^0x[0-9a-fA-F]+$")


class HexadecimalField(forms.CharField):
	"""
	A form field that accepts only hexadecimal numbers
	"""
	def __init__(self, *args, **kwargs):
		self.default_validators = [RegexValidator(hex_re, _("Enter a valid hexadecimal number"), "invalid")]
		super(HexadecimalField, self).__init__(*args, **kwargs)


class HexIntegerField(with_metaclass(models.SubfieldBase, models.BigIntegerField)):
	"""
	This field stores a hexadecimal *string* of up to 64 bits as an unsigned integer
	on *all* backends including postgres.

	Reasoning: Postgres only supports signed bigints. Since we don't care about
	signedness, we store it as signed, and cast it to unsigned when we deal with
	the actual value (with struct)

	On sqlite and mysql, native unsigned bigint types are used. In all cases, the
	value we deal with in python is always in hex.
	"""
	def db_type(self, connection):
		engine = connection.settings_dict["ENGINE"]
		if engine == "django.db.backends.mysql":
			return "bigint unsigned"
		elif engine == "django.db.backends.sqlite":
			return "UNSIGNED BIG INT"
		else:
			return super(HexIntegerField, self).db_type(connection)

	def get_prep_value(self, value):
		if value is None or value == "":
			return None
		value = int(value, 16)
		# on postgres only, interpret as signed
		if connection.settings_dict["ENGINE"] == "django.db.backends.postgresql_psycopg2":
			value = struct.unpack("q", struct.pack("Q", value))[0]
		return value

	def to_python(self, value):
		if isinstance(value, str):
			return value
		if value is None:
			return ""
		# on postgres only, re-interpret from signed to unsigned
		if connection.settings_dict["ENGINE"] == "django.db.backends.postgresql_psycopg2":
			value = hex(struct.unpack("Q", struct.pack("q", value))[0])
		return value

	def formfield(self, **kwargs):
		defaults = {"form_class": HexadecimalField}
		defaults.update(kwargs)
		# yes, that super call is right
		return super(models.IntegerField, self).formfield(**defaults)

try:
	from south.modelsinspector import add_introspection_rules
	add_introspection_rules([], ["^push_notifications\.fields\.HexIntegerField"])
except ImportError:
	pass

########NEW FILE########
__FILENAME__ = gcm
"""
Google Cloud Messaging
Previously known as C2DM
Documentation is available on the Android Developer website:
https://developer.android.com/google/gcm/index.html
"""

import json

try:
	from urllib.request import Request, urlopen
	from urllib.parse import urlencode
except ImportError:
	# Python 2 support
	from urllib2 import Request, urlopen
	from urllib import urlencode

from django.core.exceptions import ImproperlyConfigured
from . import NotificationError
from .settings import PUSH_NOTIFICATIONS_SETTINGS as SETTINGS


class GCMError(NotificationError):
	pass


def _chunks(l, n):
	"""
	Yield successive chunks from list \a l with a minimum size \a n
	"""
	for i in range(0, len(l), n):
		yield l[i:i + n]


def _gcm_send(data, content_type):
	key = SETTINGS.get("GCM_API_KEY")
	if not key:
		raise ImproperlyConfigured('You need to set PUSH_NOTIFICATIONS_SETTINGS["GCM_API_KEY"] to send messages through GCM.')

	headers = {
		"Content-Type": content_type,
		"Authorization": "key=%s" % (key),
		"Content-Length": str(len(data)),
	}

	request = Request(SETTINGS["GCM_POST_URL"], data, headers)
	response = urlopen(request)
	result = response.read().decode("utf-8")

	# FIXME: broken for bulk results
	if result.startswith("Error="):
		raise GCMError(result)

	return result


def gcm_send_message(registration_id, data, collapse_key=None, delay_while_idle=False):
	"""
	Sends a GCM notification to a single registration_id.
	This will send the notification as form data.
	If sending multiple notifications, it is more efficient to use
	gcm_send_bulk_message() with a list of registration_ids
	"""

	values = {"registration_id": registration_id}

	if collapse_key:
		values["collapse_key"] = collapse_key

	for k, v in data.items():
		values["data.%s" % (k)] = v.encode("utf-8")

	data = urlencode(values)
	return _gcm_send(data, "application/x-www-form-urlencoded;charset=UTF-8")


def gcm_send_bulk_message(registration_ids, data, collapse_key=None, delay_while_idle=False):
	"""
	Sends a GCM notification to one or more registration_ids. The registration_ids
	needs to be a list.
	This will send the notification as json data.
	"""

	# GCM only allows up to 1000 reg ids per bulk message
	# https://developer.android.com/google/gcm/gcm.html#request
	max_recipients = SETTINGS.get("GCM_MAX_RECIPIENTS")
	if len(registration_ids) > max_recipients:
		ret = []
		for chunk in _chunks(registration_ids, max_recipients):
			ret.append(gcm_send_bulk_message(chunk, data, collapse_key, delay_while_idle))
		return "\n".join(ret)

	values = {"registration_ids": registration_ids}

	if data is not None:
		values["data"] = data

	if collapse_key:
		values["collapse_key"] = collapse_key,

	if delay_while_idle:
		values["delay_while_idle"] = delay_while_idle

	data = json.dumps(values, separators=(",", ":")).encode("utf-8")
	return _gcm_send(data, "application/json")

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration

from django.db import models
from django.conf import settings

try:
	from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
	from django.contrib.auth.models import User
else:
	User = get_user_model()

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class Migration(SchemaMigration):
	def forwards(self, orm):
		# Adding model "GCMDevice"
		db.create_table(u"push_notifications_gcmdevice", (
			("id", self.gf("django.db.models.fields.AutoField")(primary_key=True)),
			("name", self.gf("django.db.models.fields.CharField")(max_length=255, null=True, blank=True)),
			("active", self.gf("django.db.models.fields.BooleanField")(default=True)),
			("user", self.gf("django.db.models.fields.related.ForeignKey")(
				to=orm["%s.%s" % (User._meta.app_label, User._meta.object_name)], null=True, blank=True)),
			("device_id", self.gf("push_notifications.fields.HexIntegerField")(null=True, blank=True)),
			("registration_id", self.gf("django.db.models.fields.TextField")()),
		))
		db.send_create_signal(u"push_notifications", ["GCMDevice"])

		# Adding model "APNSDevice"
		db.create_table(u"push_notifications_apnsdevice", (
			("id", self.gf("django.db.models.fields.AutoField")(primary_key=True)),
			("name", self.gf("django.db.models.fields.CharField")(max_length=255, null=True, blank=True)),
			("active", self.gf("django.db.models.fields.BooleanField")(default=True)),
			("user", self.gf("django.db.models.fields.related.ForeignKey")(
				to=orm["%s.%s" % (User._meta.app_label, User._meta.object_name)], null=True, blank=True)),
			("device_id", self.gf("uuidfield.fields.UUIDField")(max_length=32, null=True, blank=True)),
			("registration_id", self.gf("django.db.models.fields.CharField")(unique=True, max_length=64)),
		))
		db.send_create_signal(u"push_notifications", ["APNSDevice"])

	def backwards(self, orm):
		# Deleting model "GCMDevice"
		db.delete_table(u"push_notifications_gcmdevice")

		# Deleting model "APNSDevice"
		db.delete_table(u"push_notifications_apnsdevice")

	models = {
		u"auth.group": {
			"Meta": {"object_name": "Group"},
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "80"}),
			"permissions": ("django.db.models.fields.related.ManyToManyField", [],
				{"to": u"orm['auth.Permission']", "symmetrical": "False", "blank": "True"})
		},
		u"auth.permission": {
			"Meta": {"ordering": "(u'content_type__app_label', u'content_type__model', u'codename')",
				"unique_together": "((u'content_type', u'codename'),)", "object_name": "Permission"},
			"codename": ("django.db.models.fields.CharField", [], {"max_length": "100"}),
			"content_type": ("django.db.models.fields.related.ForeignKey", [], {"to": u"orm['contenttypes.ContentType']"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "50"})
		},
		"%s.%s" % (User._meta.app_label, User._meta.module_name): {
			"Meta": {"object_name": User.__name__, 'db_table': "'%s'" % User._meta.db_table},
			"date_joined": ("django.db.models.fields.DateTimeField", [], {"default": "datetime.datetime.now"}),
			"email": ("django.db.models.fields.EmailField", [], {"max_length": "75", "blank": "True"}),
			"first_name": ("django.db.models.fields.CharField", [], {"max_length": "30", "blank": "True"}),
			"groups": ("django.db.models.fields.related.ManyToManyField", [],
				{"to": u"orm['auth.Group']", "symmetrical": "False", "blank": "True"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"is_active": ("django.db.models.fields.BooleanField", [], {"default": "True"}),
			"is_staff": ("django.db.models.fields.BooleanField", [], {"default": "False"}),
			"is_superuser": ("django.db.models.fields.BooleanField", [], {"default": "False"}),
			"last_login": ("django.db.models.fields.DateTimeField", [], {"default": "datetime.datetime.now"}),
			"last_name": ("django.db.models.fields.CharField", [], {"max_length": "30", "blank": "True"}),
			"password": ("django.db.models.fields.CharField", [], {"max_length": "128"}),
			"user_permissions": ("django.db.models.fields.related.ManyToManyField", [],
				{"to": u"orm['auth.Permission']", "symmetrical": "False", "blank": "True"}),
			"username": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "30"})
		},
		u"contenttypes.contenttype": {
			"Meta": {"ordering": "('name',)", "unique_together": "(('app_label', 'model'),)", "object_name": "ContentType",
				"db_table": "'django_content_type'"},
			"app_label": ("django.db.models.fields.CharField", [], {"max_length": "100"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"model": ("django.db.models.fields.CharField", [], {"max_length": "100"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "100"})
		},
		u"push_notifications.apnsdevice": {
			"Meta": {"object_name": "APNSDevice"},
			"active": ("django.db.models.fields.BooleanField", [], {"default": "True"}),
			"device_id": ("uuidfield.fields.UUIDField", [], {"max_length": "32", "null": "True", "blank": "True"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "255", "null": "True", "blank": "True"}),
			"registration_id": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "64"}),
			"user": ("django.db.models.fields.related.ForeignKey", [],
				{"to": u"orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), "null": "True", "blank": "True"})
		},
		u"push_notifications.gcmdevice": {
			"Meta": {"object_name": "GCMDevice"},
			"active": ("django.db.models.fields.BooleanField", [], {"default": "True"}),
			"device_id": ("push_notifications.fields.HexIntegerField", [], {"null": "True", "blank": "True"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "255", "null": "True", "blank": "True"}),
			"registration_id": ("django.db.models.fields.TextField", [], {}),
			"user": ("django.db.models.fields.related.ForeignKey", [],
				{"to": u"orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), "null": "True", "blank": "True"})
		}
	}

	complete_apps = ["push_notifications"]

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_apnsdevice_date_created__add_field_gcmdevice_date_created
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

try:
	from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
	from django.contrib.auth.models import User
else:
	User = get_user_model()

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class Migration(SchemaMigration):
	def forwards(self, orm):
		# Adding field "APNSDevice.date_created"
		db.add_column(
			"push_notifications_apnsdevice", "date_created",
			self.gf("django.db.models.fields.DateTimeField")(auto_now_add=True, null=True, blank=True),
			keep_default=False
		)

		# Adding field "GCMDevice.date_created"
		db.add_column(
			"push_notifications_gcmdevice", "date_created",
			self.gf("django.db.models.fields.DateTimeField")(auto_now_add=True, null=True, blank=True),
			keep_default=False
		)

	def backwards(self, orm):
		# Deleting field "APNSDevice.date_created"
		db.delete_column("push_notifications_apnsdevice", "date_created")

		# Deleting field "GCMDevice.date_created"
		db.delete_column("push_notifications_gcmdevice", "date_created")

	models = {
		u"auth.group": {
			"Meta": {"object_name": "Group"},
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "80"}),
			'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
		},
		u'auth.permission': {
			'Meta': {
				'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')",
				'unique_together': "((u'content_type', u'codename'),)",
				"object_name": "Permission"
			},
			"codename": ("django.db.models.fields.CharField", [], {"max_length": "100"}),
			"content_type": ("django.db.models.fields.related.ForeignKey", [], {"to": u"orm['contenttypes.ContentType']"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "50"})
		},
		"%s.%s" % (User._meta.app_label, User._meta.module_name): {
			"Meta": {"object_name": User.__name__, 'db_table': "'%s'" % User._meta.db_table},
			"date_joined": ("django.db.models.fields.DateTimeField", [], {"default": "datetime.datetime.now"}),
			"email": ("django.db.models.fields.EmailField", [], {"max_length": "75", "blank": "True"}),
			"first_name": ("django.db.models.fields.CharField", [], {"max_length": "30", "blank": "True"}),
			"groups": ("django.db.models.fields.related.ManyToManyField", [],
				{"to": u"orm['auth.Group']", "symmetrical": "False", "blank": "True"}),
			u"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"is_active": ("django.db.models.fields.BooleanField", [], {"default": "True"}),
			"is_staff": ("django.db.models.fields.BooleanField", [], {"default": "False"}),
			"is_superuser": ("django.db.models.fields.BooleanField", [], {"default": "False"}),
			"last_login": ("django.db.models.fields.DateTimeField", [], {"default": "datetime.datetime.now"}),
			"last_name": ("django.db.models.fields.CharField", [], {"max_length": "30", "blank": "True"}),
			"password": ("django.db.models.fields.CharField", [], {"max_length": "128"}),
			"user_permissions": ("django.db.models.fields.related.ManyToManyField", [],
				{"to": u"orm['auth.Permission']", "symmetrical": "False", "blank": "True"}),
			"username": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "30"})
		},
		u"contenttypes.contenttype": {
			'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
			"app_label": ("django.db.models.fields.CharField", [], {"max_length": "100"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"model": ("django.db.models.fields.CharField", [], {"max_length": "100"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "100"})
		},
		u'push_notifications.apnsdevice': {
			"Meta": {"object_name": "APNSDevice"},
			"active": ("django.db.models.fields.BooleanField", [], {"default": "True"}),
			"date_created": ("django.db.models.fields.DateTimeField", [], {"auto_now_add": "True", "null": "True", "blank": "True"}),
			"device_id": ("uuidfield.fields.UUIDField", [], {"max_length": "32", "null": "True", "blank": "True"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "255", "null": "True", "blank": "True"}),
			"registration_id": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "64"}),
			"user": ("django.db.models.fields.related.ForeignKey", [],
				{"to": u"orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), "null": "True", "blank": "True"})
		},
		u"push_notifications.gcmdevice": {
			"Meta": {"object_name": "GCMDevice"},
			"active": ("django.db.models.fields.BooleanField", [], {"default": "True"}),
			"date_created": ("django.db.models.fields.DateTimeField", [], {"auto_now_add": "True", "null": "True", "blank": "True"}),
			"device_id": ("push_notifications.fields.HexIntegerField", [], {"null": "True", "blank": "True"}),
			"id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
			"name": ("django.db.models.fields.CharField", [], {"max_length": "255", "null": "True", "blank": "True"}),
			"registration_id": ("django.db.models.fields.TextField", [], {}),
			"user": ("django.db.models.fields.related.ForeignKey", [],
				{"to": u"orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), "null": "True", "blank": "True"})
		}
	}

	complete_apps = ['push_notifications']

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from uuidfield import UUIDField
from .fields import HexIntegerField


# Compatibility with custom user models, while keeping backwards-compatibility with <1.5
AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class Device(models.Model):
	name = models.CharField(max_length=255, verbose_name=_("Name"), blank=True, null=True)
	active = models.BooleanField(verbose_name=_("Is active"), default=True,
		help_text=_("Inactive devices will not be sent notifications"))
	user = models.ForeignKey(AUTH_USER_MODEL, blank=True, null=True)
	date_created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True, null=True)

	class Meta:
		abstract = True

	def __unicode__(self):
		return self.name or str(self.device_id or "") or "%s for %s" % (self.__class__.__name__, self.user or "unknown user")


class GCMDeviceManager(models.Manager):
	def get_queryset(self):
		return GCMDeviceQuerySet(self.model)
	get_query_set = get_queryset  # Django < 1.6 compatiblity


class GCMDeviceQuerySet(models.query.QuerySet):
	def send_message(self, message, **kwargs):
		if self:
			from .gcm import gcm_send_bulk_message
			data = kwargs.pop("extra", {})
			if message is not None:
				data["message"] = message
			return gcm_send_bulk_message(
				registration_ids=list(self.values_list("registration_id", flat=True)),
				data=data)


class GCMDevice(Device):
	# device_id cannot be a reliable primary key as fragmentation between different devices
	# can make it turn out to be null and such:
	# http://android-developers.blogspot.co.uk/2011/03/identifying-app-installations.html
	device_id = HexIntegerField(verbose_name=_("Device ID"), blank=True, null=True,
		help_text="ANDROID_ID / TelephonyManager.getDeviceId() (always as hex)")
	registration_id = models.TextField(verbose_name=_("Registration ID"))

	objects = GCMDeviceManager()

	class Meta:
		verbose_name = _("GCM device")

	def send_message(self, message, **kwargs):
		from .gcm import gcm_send_message
		data = kwargs.pop("extra", {})
		if message is not None:
			data["message"] = message
		return gcm_send_message(registration_id=self.registration_id, data=data, **kwargs)


class APNSDeviceManager(models.Manager):
	def get_queryset(self):
		return APNSDeviceQuerySet(self.model)
	get_query_set = get_queryset  # Django < 1.6 compatiblity


class APNSDeviceQuerySet(models.query.QuerySet):
	def send_message(self, message, **kwargs):
		if self:
			from .apns import apns_send_bulk_message
			return apns_send_bulk_message(registration_ids=list(self.values_list("registration_id", flat=True)), alert=message, **kwargs)


class APNSDevice(Device):
	device_id = UUIDField(verbose_name=_("Device ID"), blank=True, null=True,
		help_text="UDID / UIDevice.identifierForVendor()")
	registration_id = models.CharField(verbose_name=_("Registration ID"), max_length=64, unique=True)

	objects = APNSDeviceManager()

	class Meta:
		verbose_name = _("APNS device")

	def send_message(self, message, **kwargs):
		from .apns import apns_send_message

		return apns_send_message(registration_id=self.registration_id, alert=message, **kwargs)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

PUSH_NOTIFICATIONS_SETTINGS = getattr(settings, "PUSH_NOTIFICATIONS_SETTINGS", {})


# GCM
PUSH_NOTIFICATIONS_SETTINGS.setdefault("GCM_POST_URL", "https://android.googleapis.com/gcm/send")
PUSH_NOTIFICATIONS_SETTINGS.setdefault("GCM_MAX_RECIPIENTS", 1000)


# APNS
PUSH_NOTIFICATIONS_SETTINGS.setdefault("APNS_PORT", 2195)
PUSH_NOTIFICATIONS_SETTINGS.setdefault("APNS_ERROR_TIMEOUT", None)
if settings.DEBUG:
	PUSH_NOTIFICATIONS_SETTINGS.setdefault("APNS_HOST", "gateway.sandbox.push.apple.com")
else:
	PUSH_NOTIFICATIONS_SETTINGS.setdefault("APNS_HOST", "gateway.push.apple.com")

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
import unittest
import django.conf


def setup():
	"""
	set up test environment
	"""

	# add test/src folders to sys path
	test_folder = os.path.abspath(os.path.dirname(__file__))
	src_folder = os.path.abspath(os.path.join(test_folder, os.pardir))
	sys.path.insert(0, test_folder)
	sys.path.insert(0, src_folder)

	# define settings
	os.environ[django.conf.ENVIRONMENT_VARIABLE] = "settings"

	# set up environment
	from django.test.utils import setup_test_environment
	setup_test_environment()

	# set up database
	from django.db import connection
	connection.creation.create_test_db()


def tear_down():
	"""
	tear down test environment
	"""

	# destroy test database
	from django.db import connection
	connection.creation.destroy_test_db("not_needed")

	# teardown environment
	from django.test.utils import teardown_test_environment
	teardown_test_environment()


# fire in the hole!
if __name__ == "__main__":
	setup()

	import tests
	unittest.main(module=tests)

	tear_down()

########NEW FILE########
__FILENAME__ = settings
# assert warnings are enabled
import warnings
warnings.simplefilter("ignore", Warning)

DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.sqlite3",
	}
}

INSTALLED_APPS = [
	"django.contrib.admin",
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.sites",
	"push_notifications",
]

SITE_ID = 1
ROOT_URLCONF = "core.urls"

SECRET_KEY = "foobar"

########NEW FILE########
__FILENAME__ = test_apns_push_payload
import mock
from django.test import TestCase
from push_notifications.apns import _apns_send, APNSDataOverflow


class APNSPushPayloadTest(TestCase):
	def test_push_payload(self):
		socket = mock.MagicMock()
		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			_apns_send("123", "Hello world",
				badge=1, sound="chime", extra={"custom_data": 12345}, expiration=3, socket=socket)
			p.assert_called_once_with("123",
				'{"aps":{"sound":"chime","badge":1,"alert":"Hello world"},"custom_data":12345}', 0, 3, 10)

	def test_localised_push_with_empty_body(self):
		socket = mock.MagicMock()
		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			_apns_send("123", None, loc_key="TEST_LOC_KEY", expiration=3, socket=socket)
			p.assert_called_once_with("123", '{"aps":{"alert":{"loc-key":"TEST_LOC_KEY"}}}', 0, 3, 10)

	def test_using_extra(self):
		socket = mock.MagicMock()
		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			_apns_send("123", "sample", extra={"foo": "bar"}, identifier=10, expiration=30, priority=10, socket=socket)
			p.assert_called_once_with("123", '{"aps":{"alert":"sample"},"foo":"bar"}', 10, 30, 10)

	def test_oversized_payload(self):
		socket = mock.MagicMock()
		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			self.assertRaises(APNSDataOverflow, _apns_send, "123", "_" * 257, socket=socket)
			p.assert_has_calls([])

########NEW FILE########
__FILENAME__ = test_gcm_push_payload
import mock
from django.test import TestCase
from push_notifications.gcm import gcm_send_message, gcm_send_bulk_message


class GCMPushPayloadTest(TestCase):
	def test_push_payload(self):
		with mock.patch("push_notifications.gcm._gcm_send") as p:
			gcm_send_message("abc", {"message": "Hello world"})
			p.assert_called_once_with(
				"registration_id=abc&data.message=Hello+world",
				"application/x-www-form-urlencoded;charset=UTF-8")

	def test_bulk_push_payload(self):
		with mock.patch("push_notifications.gcm._gcm_send") as p:
			gcm_send_bulk_message(["abc", "123"], {"message": "Hello world"})
			p.assert_called_once_with(
				'{"data":{"message":"Hello world"},"registration_ids":["abc","123"]}',
				"application/json")

########NEW FILE########
__FILENAME__ = test_models
import mock
from django.test import TestCase
from django.utils import timezone
from push_notifications.models import GCMDevice, APNSDevice


class ModelTestCase(TestCase):
	def test_can_save_gcm_device(self):
		device = GCMDevice.objects.create(
			registration_id="a valid registration id"
		)
		assert device.id is not None
		assert device.date_created is not None
		assert device.date_created.date() == timezone.now().date()

	def test_can_create_save_device(self):
		device = APNSDevice.objects.create(
			registration_id="a valid registration id"
		)
		assert device.id is not None
		assert device.date_created is not None
		assert device.date_created.date() == timezone.now().date()

	def test_gcm_send_message(self):
		device = GCMDevice.objects.create(
			registration_id="abc",
		)
		with mock.patch("push_notifications.gcm._gcm_send") as p:
			device.send_message("Hello world")
			p.assert_called_once_with(
				"registration_id=abc&data.message=Hello+world",
				"application/x-www-form-urlencoded;charset=UTF-8")

	def test_gcm_send_message_extra(self):
		device = GCMDevice.objects.create(
			registration_id="abc",
		)
		with mock.patch("push_notifications.gcm._gcm_send") as p:
			device.send_message("Hello world", extra={"foo": "bar"})
			p.assert_called_once_with(
				"registration_id=abc&data.foo=bar&data.message=Hello+world",
				"application/x-www-form-urlencoded;charset=UTF-8")

	def test_apns_send_message(self):
		device = APNSDevice.objects.create(
			registration_id="abc",
		)
		socket = mock.MagicMock()
		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			device.send_message("Hello world", socket=socket, expiration=1)
			p.assert_called_once_with("abc", '{"aps":{"alert":"Hello world"}}', 0, 1, 10)

	def test_apns_send_message_extra(self):
		device = APNSDevice.objects.create(
			registration_id="abc",
		)
		socket = mock.MagicMock()
		with mock.patch("push_notifications.apns._apns_pack_frame") as p:
			device.send_message("Hello world", extra={"foo": "bar"}, socket=socket, identifier=1, expiration=2, priority=5)
			p.assert_called_once_with("abc", '{"aps":{"alert":"Hello world"},"foo":"bar"}', 1, 2, 5)

########NEW FILE########
