__FILENAME__ = admin
from models import ImpostorLog
from django.contrib import admin
from django.shortcuts import render_to_response


class ImpostorAdmin(admin.ModelAdmin):
	fields = ('impostor', 'imposted_as', 'logged_in', 'impostor_ip')
	list_display = ('impostor', 'imposted_as', 'impostor_ip', 'logged_in')
	list_editable = ()
	actions_on_top = False
	actions_on_bottom = False
	ordering = ('-logged_in', 'impostor')
	readonly_fields = ('impostor', 'imposted_as', 'impostor_ip', 'logged_in', 'logged_out')
	search_fields = ('impostor__username', 'imposted_as__username')

	def add_view(self, request, form_url='', extra_context=None):
		request.method = 'GET'
		return super(ImpostorAdmin, self).add_view(request, form_url, extra_context)

	def change_view(self, request, form_url='', extra_context=None):
		request.method = 'GET'
		return super(ImpostorAdmin, self).change_view(request, form_url, extra_context)

	def delete_view(self, request, object_id, extra_context=None):
		model = self.model
		opts = model._meta
		app_label = opts.app_label
		return render_to_response('delete_nono.html', {'app_label': app_label, 'opts': opts})



admin.site.register(ImpostorLog, ImpostorAdmin)

########NEW FILE########
__FILENAME__ = backend
import inspect

import django.contrib.auth as auth
from django.contrib.auth.models import User, Group
from django.http import HttpRequest
from models import ImpostorLog

from django.conf import settings

try:
	IMPOSTOR_GROUP = Group.objects.get(name=settings.IMPOSTOR_GROUP)
except:
	IMPOSTOR_GROUP = None

def find_request():
	'''
	Inspect running environment for request object. There should be one,
	but don't rely on it.
	'''
	frame = inspect.currentframe()
	request = None
	f = frame

	while not request and f:
		if 'request' in f.f_locals and isinstance(f.f_locals['request'], HttpRequest):
			request = f.f_locals['request']
		f = f.f_back

	del frame
	return request


class AuthBackend:
	supports_anonymous_user = False
	supports_object_permissions = False
	supports_inactive_user = False

	def authenticate(self, username=None, password=None):
		auth_user = None
		try:
			# Admin logging as user?
			admin, uuser = [ uname.strip() for uname in username.split(" as ") ]

			# Check if admin exists and authenticates
			admin_obj = User.objects.get(username=admin)
			if (admin_obj.is_superuser or (IMPOSTOR_GROUP and IMPOSTOR_GROUP in admin_obj.groups.all())) and admin_obj.check_password(password):
				try:
					auth_user = User.objects.get(username=uuser)
				except User.DoesNotExist:
					auth_user = User.objects.get(email=uuser)

			if auth_user:
				# Superusers can only be impersonated by other superusers
				if auth_user.is_superuser and not admin_obj.is_superuser:
					auth_user = None
					raise Exception("Superuser can only be impersonated by a superuser.")

				# Try to find request object and maybe be lucky enough to find IP address there
				request = find_request()
				ip_addr = ''
				if request:
					ip_addr = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('HTTP_X_REAL_IP', request.META.get('REMOTE_ADDR', '')))
					# if there are several ip addresses separated by comma
					# like HTTP_X_FORWARDED_FOR returns,
					# take only the first one, which is the client's address
					if ',' in ip_addr:
						ip_addr = ip_addr.split(',', 1)[0].strip()
				log_entry = ImpostorLog.objects.create(impostor=admin_obj, imposted_as=auth_user, impostor_ip=ip_addr)

				if log_entry.token and request:
					request.session['impostor_token'] = log_entry.token

		except: # Nope. Do nothing and let other backends handle it.
			pass
		return auth_user

	def get_user(self, user_id):
		try:
			return User.objects.get(pk=user_id)
		except User.DoesNotExist:
			return None

########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import ugettext_lazy as _

class BigAuthenticationForm(AuthenticationForm):
	username = forms.CharField(label=_("Username"), max_length=70)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
#from django.contrib.auth.signals import user_logged_in, user_logged_outs
import hashlib, time

# Create your models here.

class ImpostorLog(models.Model):
	impostor = models.ForeignKey(User, related_name='impostor', db_index=True)
	imposted_as = models.ForeignKey(User, related_name='imposted_as', verbose_name='Logged in as', db_index=True)
	impostor_ip =  models.IPAddressField(verbose_name="Impostor's IP address", null=True, blank=True)
	logged_in = models.DateTimeField(auto_now_add=True, verbose_name='Logged on')
	# These last two will come into play with Django 1.3+, but are here now for easier migration
	logged_out = models.DateTimeField(null=True, blank=True)
	token = models.CharField(max_length=32, blank=True, db_index=True)

	def save(self, *args, **kwargs):
		if not self.token and self.impostor:
			self.token = hashlib.sha1(self.impostor.username+str(time.time())).hexdigest()[:32]
		super(ImpostorLog, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from models import ImpostorLog
from forms import BigAuthenticationForm
import datetime

admin_username = 'real_test_admin'
admin_pass = 'admin_pass'
user_username = 'real_test_user'
user_email = 'real@mail.com'
user_pass = 'user_pass'

class TestImpostorLogin(TestCase):
	def setUp(self):
		real_admin = User.objects.create(username=admin_username, password=admin_pass)
		real_admin.is_superuser = True
		real_admin.set_password(admin_pass)
		real_admin.save()

		real_user = User.objects.create(username=user_username, email=user_email, password=user_pass)
		real_user.set_password(user_pass)
		real_user.save()


	def test_login_user(self):
		u = authenticate(username=user_username, password=user_pass)
		real_user = User.objects.get(username=user_username)

		self.failUnlessEqual(u, real_user)

	def test_login_user_with_email(self):
		u = authenticate(email=user_email, password=user_pass)
		real_user = User.objects.get(email=user_email)

		self.failUnlessEqual(u, real_user)

	def test_login_admin(self):
		u = authenticate(username=admin_username, password=admin_pass)
		real_admin = User.objects.get(username=admin_username)

		self.failUnlessEqual(u, real_admin)


	def test_login_admin_as_user(self):
		no_logs_entries = len(ImpostorLog.objects.all())
		self.failUnlessEqual(no_logs_entries, 0)

		u = authenticate(username="%s as %s" % (admin_username, user_username), password=admin_pass)
		real_user = User.objects.get(username=user_username)

		self.failUnlessEqual(u, real_user)

		# Check if logs contain an entry now
		logs_entries = ImpostorLog.objects.all()
		self.failUnlessEqual(len(logs_entries), 1)

		entry = logs_entries[0]
		today = datetime.date.today()
		lin = entry.logged_in
		self.failUnlessEqual(entry.impostor.username, admin_username)
		self.failUnlessEqual(entry.imposted_as.username, user_username)
		self.assertTrue(lin.year == today.year and lin.month == today.month and lin.day == today.day)
		self.assertTrue(entry.token and entry.token.strip() != "")


	def test_form(self):
		initial = { 'username': user_username, 'password': user_pass}
		form = BigAuthenticationForm(data=initial)
		self.assertTrue(form.is_valid())
		self.failUnlessEqual(form.cleaned_data['username'], user_username)
		self.failUnlessEqual(form.cleaned_data['password'], user_pass)

		new_uname = "%s as %s" % (admin_username, user_username) # Longer than contrib.auth default of 30 chars
		initial = { 'username': new_uname, 'password': admin_pass }
		form = BigAuthenticationForm(data=initial)
		self.assertTrue(form.is_valid())
		self.failUnlessEqual(form.cleaned_data['username'], new_uname)
		self.failUnlessEqual(form.cleaned_data['password'], admin_pass)

		del initial['password']
		form = BigAuthenticationForm(data=initial)
		self.assertFalse(form.is_valid())

########NEW FILE########
