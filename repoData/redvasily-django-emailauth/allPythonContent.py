__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin
from emailauth.models import UserEmail


class UserEmailAdmin(admin.ModelAdmin):
    model = UserEmail
    list_display = ['user', 'email', 'verified',]

try:
    admin.site.register(UserEmail, UserEmailAdmin)
except admin.sites.AlreadyRegistered:
    pass

########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

from emailauth.models import UserEmail


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            email = UserEmail.objects.get(email=username, verified=True)
            if email.user.check_password(password):
                return email.user
        except UserEmail.DoesNotExist:
            return None


class FallbackBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(username=username)
            if (user.check_password(password) and
                not UserEmail.objects.filter(user=user).count()):

                return user

        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User

from emailauth.models import UserEmail

attrs_dict = {}

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict)))
    password = forms.CharField(widget=forms.PasswordInput(attrs=dict(attrs_dict),
        render_value=False))

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct email and "
                    "password. Note that both fields are case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))

        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


def get_max_length(model, field_name):
    field = model._meta.get_field_by_name(field_name)[0]
    return field.max_length


def clean_password2(self):
    data = self.cleaned_data
    if 'password1' in data and 'password2' in data:
        if data['password1'] != data['password2']:
            raise forms.ValidationError(_(
                u'You must type the same password each time.'))
    if 'password2' in data:
        return data['password2']


class RegistrationForm(forms.Form):
    email = forms.EmailField(label=_(u'email address'))
    first_name = forms.CharField(label=_(u'first name'),
        max_length=get_max_length(User, 'first_name'),
        help_text=_(u"That's how we'll call you in emails"))
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password (again)'))
    
    clean_password2 = clean_password2

    def clean_email(self):
        email = self.cleaned_data['email']

        try:
            user = UserEmail.objects.get(email=email)
            raise forms.ValidationError(_(u'This email is already taken.'))
        except UserEmail.DoesNotExist:
            pass
        return email
        

    def save(self):
        data = self.cleaned_data
        user = User()
        user.email = data['email']
        user.first_name = data['name']
        user.set_password(data['password1'])
        user.save()

        desired_username = 'id_%d_%s' % (user.id, user.email)
        user.username = desired_username[:get_max_length(User, 'username')]
        user.is_active = False
        user.save()
        
        registration_profile = (
            RegistrationProfile.objects.create_inactive_profile(user))
        registration_profile.save()

        profile = Account()
        profile.user = user
        profile.save()

        return user, registration_profile


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label=_(u'your email address'))

    def clean_email(self):
        data = self.cleaned_data
        try:
            user_email = UserEmail.objects.get(email=data['email'])
            return data['email']
        except UserEmail.DoesNotExist:
            raise forms.ValidationError(_(u'Unknown email'))


class PasswordResetForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password (again)'))
    
    clean_password2 = clean_password2


class AddEmailForm(forms.Form):
    email = forms.EmailField(label=_(u'new email address'))

    def clean_email(self):
        email = self.cleaned_data['email']

        try:
            user = UserEmail.objects.get(email=email)
            raise forms.ValidationError(_(u'This email is already taken.'))
        except UserEmail.DoesNotExist:
            pass
        return email


class DeleteEmailForm(forms.Form):
    yes = forms.BooleanField(required=True)

    def __init__(self, user, *args, **kwds):
        self.user = user
        super(DeleteEmailForm, self).__init__(*args, **kwds)

    def clean(self):
        count = UserEmail.objects.filter(user=self.user).count()
        if UserEmail.objects.filter(user=self.user, verified=True).count() < 2:
            raise forms.ValidationError(_('You can not delete your last verified '
                'email.'))
        return self.cleaned_data


class ConfirmationForm(forms.Form):
    yes = forms.BooleanField(required=True)

########NEW FILE########
__FILENAME__ = cleanupemailauth
from django.core.management.base import NoArgsCommand

from emailauth.models import UserEmail


class Command(NoArgsCommand):
    help = "Delete expired UserEmail objects from the database"

    def handle_noargs(self, **options):
        UserEmail.objects.delete_expired()

########NEW FILE########
__FILENAME__ = models
import datetime
import random

import django.core.mail

from django.db import models
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from django.template.loader import render_to_string

from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _
import django.core.mail

from django.conf import settings

from emailauth.utils import email_verification_days, use_automaintenance

class UserEmailManager(models.Manager):
    def make_random_key(self, email):
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        key = sha_constructor(salt + email).hexdigest()
        return key

    def create_unverified_email(self, email, user=None):
        if use_automaintenance():
            self.delete_expired()
        
        email_obj = UserEmail(email=email, user=user, default=user is None,
            verification_key=self.make_random_key(email))
        return email_obj

    def verify(self, verification_key):
        try:
            email = self.get(verification_key=verification_key)
        except self.model.DoesNotExist:
            return None
        if not email.verification_key_expired():
            email.verification_key = self.model.VERIFIED
            email.verified = True
            email.save()
            return email

    def delete_expired(self):
        date_threshold = (datetime.datetime.now() -
            datetime.timedelta(days=email_verification_days()))
        expired_emails = self.filter(code_creation_date__lt=date_threshold)
    
        for email in expired_emails:
            if not email.verified:
                user = email.user
                emails = user.useremail_set.all()
                if not user.is_active:
                    user.delete()
                else:
                    email.delete()


class UserEmail(models.Model):
    class Meta:
        verbose_name = _('user email')
        verbose_name_plural = _('user emails')

    VERIFIED = 'ALREADY_VERIFIED'

    objects = UserEmailManager()

    user = models.ForeignKey(User, null=True, blank=True, verbose_name=_('user'))
    default = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    verified = models.BooleanField(default=False)
    code_creation_date = models.DateTimeField(default=datetime.datetime.now)
    verification_key = models.CharField(_('verification key'), max_length=40)

    def __init__(self, *args, **kwds):
        super(UserEmail, self).__init__(*args, **kwds)
        self._original_default = self.default

    def __unicode__(self):
        return self.email

    def save(self, *args, **kwds):
        super(UserEmail, self).save(*args, **kwds)
        if self.default and not self._original_default:
            self.user.email = self.email
            self.user.save()
            for email in self.__class__.objects.filter(user=self.user):
                if email.id != self.id and email.default:
                    email.default = False
                    email.save()

    def make_new_key(self):
        self.verification_key = self.__class__.objects.make_random_key(
            self.email)
        self.code_creation_date = datetime.datetime.now()

    def send_verification_email(self, first_name=None):
        current_site = Site.objects.get_current()
        
        subject = render_to_string('emailauth/verification_email_subject.txt',
            {'site': current_site})
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        emails = set()
        if self.user is not None:
            for email in self.__class__.objects.filter(user=self.user):
                emails.add(email.email)
        emails.add(self.email)
        first_email = len(emails) == 1

        if first_name is None:
            first_name = self.user.first_name
        
        message = render_to_string('emailauth/verification_email.txt', {
            'verification_key': self.verification_key,
            'expiration_days': email_verification_days(),
            'site': current_site,
            'first_name': first_name,
            'first_email': first_email,
        })

        self.code_creation_date = datetime.datetime.now()

        django.core.mail.send_mail(subject, message,
            settings.DEFAULT_FROM_EMAIL, [self.email])
        

    def verification_key_expired(self):
        expiration_date = datetime.timedelta(days=email_verification_days())
        return (self.verification_key == self.VERIFIED or
            (self.code_creation_date + expiration_date <= datetime.datetime.now()))

    verification_key_expired.boolean = True

########NEW FILE########
__FILENAME__ = emailauth_tags
# -*- coding: utf-8 -*-
from django import template
from emailauth.forms import LoginForm

register = template.Library()

@register.inclusion_tag('emailauth/loginform.html', takes_context=True)
def loginform(context):
    form = LoginForm()
    user = context['request'].user
    return locals()
########NEW FILE########
__FILENAME__ = tests
import re
from datetime import datetime, timedelta

from django.test.client import Client
from django.test.testcases import TestCase
from django.core import mail
from django.contrib.auth.models import User
from django.conf import settings

from emailauth.models import UserEmail
from emailauth.utils import email_verification_days


class Status:
    OK = 200
    REDIRECT = 302
    NOT_FOUND = 404


class BaseTestCase(TestCase):
    def assertStatusCode(self, response, status_code=200):
        self.assertEqual(response.status_code, status_code)

    def checkSimplePage(self, path, params={}):
        client = Client()
        response = client.get(path, params)
        self.assertStatusCode(response)

    def createActiveUser(self, username='username', email='user@example.com',
        password='password'):

        user = User(username=username, email=email, is_active=True)
        user.first_name = 'John'
        user.set_password(password)
        user.save()

        user_email = UserEmail(user=user, email=email, verified=True,
            default=True, verification_key=UserEmail.VERIFIED)
        user_email.save()
        return user, user_email

    def getLoggedInClient(self, email='user@example.com', password='password'):
        client = Client()
        client.login(username=email, password=password)
        return client


class RegisterTest(BaseTestCase):
    def testRegisterGet(self):
        self.checkSimplePage('/register/')

    def testRegisterPost(self):
        client = Client()
        response = client.post('/register/', {
            'email': 'user@example.com',
            'first_name': 'John',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertRedirects(response, '/register/continue/user%40example.com/')

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        verification_url = addr_re.search(email.body).groups()[0]

        response = client.get(verification_url)

        self.assertRedirects(response, '/account/')

        response = client.post('/login/', {
            'email': 'user@example.com',
            'password': 'password',
        })

        self.assertRedirects(response, '/account/')

        user = User.objects.get(email='user@example.com')
        self.assertEqual(user.first_name, 'John')

    def testRegisterSame(self):
        user, user_email = self.createActiveUser()
        client = Client()
        response = client.post('/register/', {
            'email': user_email.email,
            'first_name': 'John',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertContains(response, 'This email is already taken')

        email_obj = UserEmail.objects.create_unverified_email(
            'user@example.org', user)
        email_obj.save()

        response = client.post('/register/', {
            'email': 'user@example.org',
            'first_name': 'John',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertContains(response, 'This email is already taken')
        


class LoginTest(BaseTestCase):
    def testLoginGet(self):
        self.checkSimplePage('/login/')

    def testLoginFail(self):
        user, user_email = self.createActiveUser()
        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.com',
            'password': 'wrongpassword',
        })
        self.assertStatusCode(response, Status.OK)


class PasswordResetTest(BaseTestCase):
    def prepare(self):
        user, user_email = self.createActiveUser() 

        client = Client()
        response = client.post('/resetpassword/', {
            'email': user_email.email,
        })

        self.assertRedirects(response,
            '/resetpassword/continue/user%40example.com/')

        email = mail.outbox[0]
        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        reset_url = addr_re.search(email.body).groups()[0]
        return reset_url, user_email


    def testPasswordReset(self):
        reset_url, user_email = self.prepare()
        client = Client()

        self.checkSimplePage(reset_url)

        response = client.post(reset_url, {
            'password1': 'newpassword',
            'password2': 'newpassword',
        })

        self.assertRedirects(response, '/account/')

        user = User.objects.get(email=user_email.email)
        self.assertTrue(user.check_password('newpassword'))

        response = client.get(reset_url)
        self.assertStatusCode(response, Status.NOT_FOUND)


    def testPasswordResetFail(self):
        reset_url, user_email = self.prepare()
        client = Client()
        user_email.verification_key = UserEmail.VERIFIED
        user_email.save()

        response = client.get(reset_url)
        self.assertStatusCode(response, Status.NOT_FOUND)


    def testPasswordResetFail2(self):
        reset_url, user_email = self.prepare()
        client = Client()
        user_email.code_creation_date = (datetime.now() -
            timedelta(days=email_verification_days() + 1))
        user_email.save()

        response = client.get(reset_url)
        self.assertStatusCode(response, Status.NOT_FOUND)


class TestAddEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testAddEmailGet(self):
        response = self.client.get('/account/addemail/')
        self.assertStatusCode(response, Status.OK)

    def testAddEmail(self):
        response = self.client.post('/account/addemail/', {
            'email': 'user@example.org',
        })
        self.assertRedirects(response, '/account/addemail/continue/user%40example.org/')

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        verification_url = addr_re.search(email.body).groups()[0]

        response = self.client.get(verification_url)

        self.assertRedirects(response, '/account/')

        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.org',
            'password': 'password',
        })

        self.assertRedirects(response, '/account/')

    def testAddSameEmail(self):
        response = self.client.post('/account/addemail/', {
            'email': 'user@example.com',
        })
        self.assertStatusCode(response, Status.OK)

        response = self.client.post('/account/addemail/', {
           'email': 'user@example.org',
        })
        self.assertRedirects(response,
            '/account/addemail/continue/user%40example.org/')

        response = self.client.post('/account/addemail/', {
          'email': 'user@example.org',
        })
        self.assertStatusCode(response, Status.OK)


class TestDeleteEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testDeleteEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='email@example.org', verified=True,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        response = self.client.post('/account/deleteemail/%s/' % user_email.id, {
            'yes': 'yes',
        })

        self.assertRedirects(response, '/account/')

        user_emails = UserEmail.objects.filter(user=self.user)
        self.assertEqual(len(user_emails), 1)

        response = self.client.post('/account/deleteemail/%s/' % user_emails[0].id, {
            'yes': 'yes',
        })

        self.assertStatusCode(response, Status.OK)


class TestSetDefaultEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testSetDefaultEmailGet(self):
        response = self.client.get('/account/setdefaultemail/%s/' %
            self.user_email.id)
        self.assertStatusCode(response, Status.OK)

    def testSetDefaultEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='user@example.org', verified=True,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        response = self.client.post('/account/setdefaultemail/%s/' % user_email.id, {
            'yes': 'yes',
        })

        self.assertRedirects(response, '/account/')

        new_default_email = user_email.email

        for email in UserEmail.objects.filter():
            self.assertEqual(email.default, email.email == new_default_email)

        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.email, new_default_email)

    def testSetDefaultUnverifiedEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='user@example.org', verified=False,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        response = self.client.post('/account/setdefaultemail/%s/' % user_email.id, {
            'yes': 'yes',
        })
        self.assertStatusCode(response, Status.NOT_FOUND)

class TestDeleteEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testDeleteEmail(self):
        user_email = UserEmail(user=self.user, email='user@example.org', verified=True,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        page_url = '/account/deleteemail/%s/' % user_email.id

        response = self.client.get(page_url)
        self.assertStatusCode(response, Status.OK)

        response = self.client.post(page_url, {'yes': 'yes'})
        self.assertRedirects(response, '/account/')

    def testDeleteUnverifiedEmail(self):
        user_email = UserEmail(user=self.user, email='user@example.org', verified=False,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()
        
        response = self.client.post('/account/deleteemail/%s/' % user_email.id, {
            'yes': 'yes',
        })
        self.assertStatusCode(response, Status.NOT_FOUND)


class TestAccountSingleEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()
        settings.EMAILAUTH_USE_SINGLE_EMAIL = True

    def tearDown(self):
        settings.EMAILAUTH_USE_SINGLE_EMAIL = False

    def testAccountGet(self):
        response = self.client.get('/account/')
        self.assertStatusCode(response, Status.OK)

class TestChangeEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()
        settings.EMAILAUTH_USE_SINGLE_EMAIL = True

    def tearDown(self):
        settings.EMAILAUTH_USE_SINGLE_EMAIL = False

    def testEmailChangeWrongMode(self):
        settings.EMAILAUTH_USE_SINGLE_EMAIL = False
        response = self.client.get('/account/changeemail/')
        self.assertStatusCode(response, Status.NOT_FOUND)

    def testEmailChange(self):
        response = self.client.get('/account/changeemail/')
        self.assertStatusCode(response, Status.OK)

        response = self.client.post('/account/changeemail/', {
            'email': 'user@example.org',
        })

        self.assertRedirects(response,
            '/account/changeemail/continue/user%40example.org/')

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        verification_url = addr_re.search(email.body).groups()[0]

        response = self.client.get(verification_url)

        self.assertRedirects(response, '/account/')

        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.org',
            'password': 'password',
        })

        self.assertRedirects(response, '/account/')

        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.email, 'user@example.org')

        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.com',
            'password': 'password',
        })
        self.assertStatusCode(response, Status.OK)


class TestResendEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testResendEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='user@example.org', verified=False,
            default=False, verification_key='abcdef')
        user_email.save()

        response = self.client.get('/account/resendemail/%s/' % user_email.id)
        self.assertRedirects(response,
            '/account/addemail/continue/user%40example.org/')
        self.assertEqual(len(mail.outbox), 1)
        

class TestCleanup(BaseTestCase):
    def testCleanup(self):
        user1 = User(username='user1', email='user1@example.com', is_active=True)
        user1.save()

        old_enough = (datetime.now() - timedelta(days=email_verification_days() + 1))
        not_old_enough = (datetime.now() -
            timedelta(days=email_verification_days() - 1))

        email1 = UserEmail(user=user1, email='user1@example.com',
            verified=True, default=True, 
            verification_key=UserEmail.VERIFIED + 'asd',
            code_creation_date=old_enough)
        email1.save() 

        user2 = User(username='user2', email='user2@example.com', is_active=False)
        user2.save()

        email2 = UserEmail(user=user2, email='user2@example.com',
            verified=False, default=True, 
            verification_key='key1',
            code_creation_date=old_enough)
        email2.save()

        user3 = User(username='user3', email='user3@example.com', is_active=False)
        user3.save()

        email3 = UserEmail(user=user3, email='user3@example.com',
            verified=False, default=True, 
            verification_key='key2',
            code_creation_date=not_old_enough)
        email3.save()

        UserEmail.objects.delete_expired()

        user_ids = [user.id for user in User.objects.all()]
        user_email_ids = [user_email.id for user_email in UserEmail.objects.all()]

        self.assertEqual(list(sorted(user_ids)), list(sorted([user1.id, user3.id])))
        self.assertEqual(list(sorted(user_email_ids)), list(sorted([email1.id, email3.id])))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

import emailauth.views

urlpatterns = patterns('',
    url(r'^account/$', 'emailauth.views.account', name='emailauth_account'),

    url(r'^register/$', 'emailauth.views.register',
        name='register'),

    url(r'^register/continue/(?P<email>.+)/$',
        'emailauth.views.register_continue',
        name='emailauth_register_continue'),

    url(r'^verify/(?P<verification_key>\w+)/$', 'emailauth.views.verify',
        name='emailauth_verify'),

    url(r'^resetpassword/$', 'emailauth.views.request_password_reset',
        name='emailauth_request_password_reset'),
    url(r'^resetpassword/continue/(?P<email>.+)/$',
        'emailauth.views.request_password_reset_continue',
        name='emailauth_request_password_reset_continue'),
    url(r'^resetpassword/(?P<reset_code>\w+)/$',
        'emailauth.views.reset_password', name='emailauth_reset_password'),

    url(r'^account/addemail/$', 'emailauth.views.add_email',
        name='emailauth_add_email'),
    url(r'^account/addemail/continue/(?P<email>.+)/$',
        'emailauth.views.add_email_continue',
        name='emailauth_add_email_continue'),
    url(r'^account/resendemail/(\d+)/$',
        'emailauth.views.resend_verification_email',
        name='emailauth_resend_verification_email'),

    url(r'^account/changeemail/$', 'emailauth.views.change_email',
        name='emailauth_change_email'),
    url(r'^account/changeemail/continue/(?P<email>.+)/$',
        'emailauth.views.change_email_continue',
        name='emailauth_change_email_continue'),

    url(r'^account/deleteemail/(\d+)/$', 'emailauth.views.delete_email',
        name='emailauth_delete_email'),

    url(r'^account/setdefaultemail/(\d+)/$',
        'emailauth.views.set_default_email',
        name='emailauth_set_default_email'),

    url(r'^login/$', 'emailauth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/',
        'template_name': 'logged_out.html'}, name='logout'),
)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.http import Http404
from django.utils.functional import curry

def email_verification_days():
    return getattr(settings, 'EMAILAUTH_VERIFICATION_DAYS', 3)

def use_single_email():
    return getattr(settings, 'EMAILAUTH_USE_SINGLE_EMAIL', True)

def use_automaintenance():
    return getattr(settings, 'EMAILAUTH_USE_AUTOMAINTENANCE', True)

def require_emailauth_mode(func, emailauth_use_singe_email):
    def wrapper(*args, **kwds):
        if use_single_email() == emailauth_use_singe_email:
            return func(*args, **kwds)
        else:
            raise Http404()
    return wrapper

requires_single_email_mode = curry(require_emailauth_mode,
    emailauth_use_singe_email=True)

requires_multi_emails_mode = curry(require_emailauth_mode,
    emailauth_use_singe_email=False)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from urllib import urlencode, quote_plus

import django.core.mail
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.contrib.sites.models import Site, RequestSite
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django import forms
import django.forms.forms
import django.forms.util

from django.utils.translation import ugettext_lazy as _

from emailauth.forms import (LoginForm, RegistrationForm,
    PasswordResetRequestForm, PasswordResetForm, AddEmailForm, DeleteEmailForm,
    ConfirmationForm)
from emailauth.models import UserEmail

from emailauth.utils import (use_single_email, requires_single_email_mode,
    requires_multi_emails_mode, email_verification_days)


def login(request, template_name='emailauth/login.html',
    redirect_field_name=REDIRECT_FIELD_NAME):

    redirect_to = request.REQUEST.get(redirect_field_name, '')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import login
            login(request, form.get_user())

            if request.get_host() == 'testserver':
                if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                    redirect_to = settings.LOGIN_REDIRECT_URL
                return HttpResponseRedirect(redirect_to)

            request.session.set_test_cookie()

            return HttpResponseRedirect(settings.LOGIN_URL + '?' + urlencode({
                'testcookiesupport': '',
                redirect_field_name: redirect_to,
            }))
    elif 'testcookiesupport' in request.GET:
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            return HttpResponseRedirect(redirect_to)
        else:
            form = LoginForm()
            errorlist = forms.util.ErrorList()
            errorlist.append(_("Your Web browser doesn't appear to "
                "have cookies enabled. Cookies are required for logging in."))
            form._errors = forms.util.ErrorDict()
            form._errors[forms.forms.NON_FIELD_ERRORS] = errorlist
    else:
        form = LoginForm()

    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)

    return render_to_response(template_name, {
            'form': form,
            redirect_field_name: redirect_to,
            'site_name': current_site.name,
        },
        context_instance=RequestContext(request))


@login_required
def account(request, template_name=None):
    context = RequestContext(request)

    if template_name is None:
        if use_single_email():
            template_name = 'emailauth/account_single_email.html'
        else:
            template_name = 'emailauth/account.html'

    # Maybe move this emails into context processors?
    extra_emails = UserEmail.objects.filter(user=request.user, default=False,
        verified=True)
    unverified_emails = UserEmail.objects.filter(user=request.user,
        default=False, verified=False)

    return render_to_response(template_name, 
        {
            'extra_emails': extra_emails,
            'unverified_emails': unverified_emails,
        },
        context_instance=context)


def get_max_length(model, field_name):
    field = model._meta.get_field_by_name(field_name)[0]
    return field.max_length


def default_register_callback(form, email):
    data = form.cleaned_data
    user = User()
    user.first_name = data['first_name']
    user.is_active = False
    user.email = email.email
    user.set_password(data['password1'])
    user.save()
    user.username = ('id_%d_%s' % (user.id, user.email))[
        :get_max_length(User, 'username')]
    user.save()
    email.user = user


def register(request, callback=default_register_callback):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email_obj = UserEmail.objects.create_unverified_email(
                form.cleaned_data['email'])
            email_obj.send_verification_email(form.cleaned_data['first_name'])

            if callback is not None:
                callback(form, email_obj)

            site = Site.objects.get_current()
            email_obj.user.message_set.create(message='Welcome to %s.' % site.name)

            email_obj.save()
            return HttpResponseRedirect(reverse('emailauth_register_continue',
                args=[quote_plus(email_obj.email)]))
    else:
        form = RegistrationForm()

    return render_to_response('emailauth/register.html', {'form': form},
        RequestContext(request))


def register_continue(request, email,
    template_name='emailauth/register_continue.html'):

    return render_to_response(template_name, {'email': email},
        RequestContext(request))


def default_verify_callback(request, email):
    email.user.is_active = True
    email.user.save()

    if request.user.is_anonymous():
        from django.contrib.auth import login
        user = email.user
        user.backend = 'emailauth.backends.EmailBackend'
        login(request, user)
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    else:
        return HttpResponseRedirect(reverse('emailauth_account'))


def verify(request, verification_key, template_name='emailauth/verify.html',
    extra_context=None, callback=default_verify_callback):

    verification_key = verification_key.lower() # Normalize before trying anything with it.
    email = UserEmail.objects.verify(verification_key)

    
    if email is not None:
        email.user.message_set.create(message=_('%s email confirmed.') % email.email)

        if use_single_email():
            email.default = True
            email.save()
            UserEmail.objects.filter(user=email.user, default=False).delete()

    if email is not None and callback is not None:
        cb_result = callback(request, email)
        if cb_result is not None:
            return cb_result

    context = RequestContext(request)
    if extra_context is not None:
        for key, value in extra_context.items():
            context[key] = value() if callable(value) else value

    return render_to_response(template_name,
        {
            'email': email,
            'expiration_days': email_verification_days(),
        },
        context_instance=context)


def request_password_reset(request,
    template_name='emailauth/request_password.html'):

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user_email = UserEmail.objects.get(email=email)
            user_email.make_new_key()
            user_email.save()

            current_site = Site.objects.get_current()

            subject = render_to_string(
                'emailauth/request_password_email_subject.txt',
                {'site': current_site})
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())

            message = render_to_string('emailauth/request_password_email.txt', {
                'reset_code': user_email.verification_key,
                'expiration_days': email_verification_days(),
                'site': current_site,
                'first_name': user_email.user.first_name,
            })

            django.core.mail.send_mail(subject, message,
                settings.DEFAULT_FROM_EMAIL, [email])

            return HttpResponseRedirect(
                reverse('emailauth_request_password_reset_continue',
                args=[quote_plus(email)]))
    else:
        form = PasswordResetRequestForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {
            'form': form,
            'expiration_days': email_verification_days(),
        },
        context_instance=context)


def request_password_reset_continue(request, email,
    template_name='emailauth/reset_password_continue.html'):

    return render_to_response(template_name,
        {'email': email},
        context_instance=RequestContext(request))


def reset_password(request, reset_code,
    template_name='emailauth/reset_password.html'):

    user_email = get_object_or_404(UserEmail, verification_key=reset_code)
    if (user_email.verification_key == UserEmail.VERIFIED or
        user_email.code_creation_date +
        timedelta(days=email_verification_days()) < datetime.now()):

        raise Http404()

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            user = user_email.user
            user.set_password(form.cleaned_data['password1'])
            user.save()

            user_email.verification_key = UserEmail.VERIFIED
            user_email.save()

            from django.contrib.auth import login
            user.backend = 'emailauth.backends.EmailBackend'
            login(request, user)
            return HttpResponseRedirect(reverse('emailauth_account'))
    else:
        form = PasswordResetForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form},
        context_instance=context)


@requires_multi_emails_mode
@login_required
def add_email(request, template_name='emailauth/add_email.html'):
    if request.method == 'POST':
        form = AddEmailForm(request.POST)
        if form.is_valid():
            email_obj = UserEmail.objects.create_unverified_email(
                form.cleaned_data['email'], user=request.user)
            email_obj.send_verification_email()
            email_obj.save()
            return HttpResponseRedirect(reverse('emailauth_add_email_continue',
                args=[quote_plus(email_obj.email)]))
    else:
        form = AddEmailForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form},
        context_instance=context)


@requires_multi_emails_mode
@login_required
def add_email_continue(request, email,
    template_name='emailauth/add_email_continue.html'):

    return render_to_response(template_name,
        {'email': email},
        context_instance=RequestContext(request))


@requires_single_email_mode
@login_required
def change_email(request, template_name='emailauth/change_email.html'):
    if request.method == 'POST':
        form = AddEmailForm(request.POST)
        if form.is_valid():
            UserEmail.objects.filter(user=request.user, default=False).delete()

            email_obj = UserEmail.objects.create_unverified_email(
                form.cleaned_data['email'], user=request.user)
            email_obj.send_verification_email()
            email_obj.save()

            return HttpResponseRedirect(reverse('emailauth_change_email_continue',
                args=[quote_plus(email_obj.email)]))
    else:
        form = AddEmailForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form},
        context_instance=context)


@requires_single_email_mode
@login_required
def change_email_continue(request, email,
    template_name='emailauth/change_email_continue.html'):

    return render_to_response(template_name,
        {'email': email},
        context_instance=RequestContext(request))


@requires_multi_emails_mode
@login_required
def delete_email(request, email_id,
    template_name='emailauth/delete_email.html'):

    user_email = get_object_or_404(UserEmail, id=email_id, user=request.user,
        verified=True)

    if request.method == 'POST':
        form = DeleteEmailForm(request.user, request.POST)
        if form.is_valid():
            user_email.delete()

            # Not really sure, where I should redirect from here...
            return HttpResponseRedirect(reverse('emailauth_account'))
    else:
        form = DeleteEmailForm(request.user)

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form, 'email': user_email},
        context_instance=context)


@requires_multi_emails_mode
@login_required
def set_default_email(request, email_id,
    template_name='emailauth/set_default_email.html'):

    user_email = get_object_or_404(UserEmail, id=email_id, user=request.user,
        verified=True)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            user_email.default = True
            user_email.save()
            return HttpResponseRedirect(reverse('emailauth_account'))
    else:
        form = ConfirmationForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form, 'email': user_email},
        context_instance=context)


@login_required
def resend_verification_email(request, email_id):
    user_email = get_object_or_404(UserEmail, id=email_id, user=request.user,
        verified=False)
    user_email.send_verification_email()

    return HttpResponseRedirect(reverse('emailauth_add_email_continue',
        args=[quote_plus(user_email.email)]))


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from os import path, environ
from os.path import abspath, dirname, join
import sys

example_dir = dirname(abspath(__file__))
emailauth_dir = dirname(example_dir)

sys.path.insert(0, example_dir)
sys.path.insert(0, emailauth_dir)

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
__FILENAME__ = middleware
from django.conf import settings
from django.contrib.sites.models import Site

class CurrentSiteMiddleware(object):
    def process_request(self, request):
        site = Site.objects.get(id=settings.SITE_ID)
        if site.domain != request.get_host():
            site.domain = request.get_host()
            site.save()

########NEW FILE########
__FILENAME__ = settings
from os.path import join, dirname, abspath

DEBUG = True
TEMPLATE_DEBUG = DEBUG

PROJECT_ROOT = dirname(abspath(__file__))

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_ENGINE = 'sqlite3'

# Or path to database file if using sqlite3.
DATABASE_NAME = join(PROJECT_ROOT, 'emailauth.db')

# Not used with sqlite3.
DATABASE_USER = ''

# Not used with sqlite3.
DATABASE_PASSWORD = ''

# Set to empty string for localhost. Not used with sqlite3.
DATABASE_HOST = ''

# Set to empty string for default. Not used with sqlite3.
DATABASE_PORT = ''

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
MEDIA_ROOT = join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '-&umm_!rboq^$-ye%v+4rp^+@a&dqou&d=%psw(xvfh)y%p2q-'

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
    'example.middleware.CurrentSiteMiddleware',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    join(PROJECT_ROOT, 'templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'emailauth',
)

AUTHENTICATION_BACKENDS = (
    'emailauth.backends.EmailBackend',
    'emailauth.backends.FallbackBackend',
)

LOGIN_REDIRECT_URL = '/account/'
LOGIN_URL = '/login/'

EMAILAUTH_USE_SINGLE_EMAIL = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

########NEW FILE########
__FILENAME__ = settings_singleemail
from settings import *

EMAILAUTH_USE_SINGLE_EMAIL = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'example.views.index', name='index'),
    (r'', include('emailauth.urls')),
    (r'^admin/(.*)', admin.site.root),
)

urlpatterns += patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {
            'document_root': settings.MEDIA_ROOT,
            'show_indexes': True
        }
    ),
)

########NEW FILE########
__FILENAME__ = views
from os.path import dirname, abspath, join

from django.shortcuts import render_to_response
from django import template
from django.template import RequestContext
from django.contrib.markup.templatetags.markup import restructuredtext

def index(request):
    readme_file = join(dirname(dirname(abspath(__file__))), 'README.rst')
    raw_content = open(readme_file).read()
    try:
        content = restructuredtext(raw_content)
    except template.TemplateSyntaxError:
        content = u'<pre>' + raw_content + u'</pre>'
        
    return render_to_response('index.html', {'content': content},
        context_instance=RequestContext(request))

########NEW FILE########
