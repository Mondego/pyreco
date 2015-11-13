__FILENAME__ = admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _

from .forms import EmailUserChangeForm, EmailUserCreationForm
from .models import EmailUser


class EmailUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
    )

    # The forms to add and change user instances
    form = EmailUserChangeForm
    add_form = EmailUserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('email', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

# Register the new EmailUserAdmin
admin.site.register(EmailUser, EmailUserAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext_lazy as _


class EmailUserCreationForm(forms.ModelForm):
    """
    A form for creating new users. Includes all the required fields, plus a
    repeated password.
    """
    error_messages = {
        'duplicate_email': _("A user with that email already exists."),
        'password_mismatch': _("The two password fields didn't match."),
    }

    password1 = forms.CharField(label=_("Password"),
        widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."))

    class Meta:
        model = get_user_model()
        fields = ('email',)

    def clean_email(self):
        # Since EmailUser.email is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        email = self.cleaned_data["email"]
        try:
            get_user_model()._default_manager.get(email=email)
        except get_user_model().DoesNotExist:
            return email
        raise forms.ValidationError(
            self.error_messages['duplicate_email'],
            code='duplicate_email',
        )

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(EmailUserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class EmailUserChangeForm(forms.ModelForm):
    """
    A form for updating users. Includes all the fields on the user, but
    replaces the password field with admin's password hash display field.
    """

    password = ReadOnlyPasswordHashField(label=_("Password"),
        help_text=_("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>."))

    class Meta:
        model = get_user_model()
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(EmailUserChangeForm, self).__init__(*args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class EmailUserManager(BaseUserManager):

    def _create_user(self, email, password,
                     is_staff, is_superuser, **extra_fields):
        """
        Creates and saves an EmailUser with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        is_active = extra_fields.pop("is_active", True)
        user = self.model(email=email, is_staff=is_staff, is_active=is_active,
                          is_superuser=is_superuser, last_login=now,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        is_staff = extra_fields.pop("is_staff", False)
        return self._create_user(email, password, is_staff, False,
                                 **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email, password, True, True,
                                 **extra_fields)


class AbstractEmailUser(AbstractBaseUser, PermissionsMixin):
    """
    Abstract User with the same behaviour as Django's default User but
    without a username field. Uses email as the USERNAME_FIELD for
    authentication.

    Use this if you need to extend EmailUser.

    Inherits from both the AbstractBaseUser and PermissionMixin.

    The following attributes are inherited from the superclasses:
        * password
        * last_login
        * is_superuser
    """
    email = models.EmailField(_('email address'), max_length=255,
                              unique=True, db_index=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = EmailUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def get_full_name(self):
        """
        Returns the email.
        """
        return self.email

    def get_short_name(self):
        """
        Returns the email.
        """
        return self.email

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])


class EmailUser(AbstractEmailUser):
    """
    Concrete class of AbstractEmailUser.

    Use this if you don't need to extend EmailUser.
    """
    class Meta(AbstractEmailUser.Meta):
        swappable = 'AUTH_USER_MODEL'

########NEW FILE########
__FILENAME__ = tests
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.forms.fields import Field
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

from .forms import EmailUserChangeForm, EmailUserCreationForm


class UserTest(TestCase):

    user_email = 'newuser@localhost.local'
    user_password = '1234'

    def create_user(self):
        """
        Creates and returns a new user with self.user_email as login and self.user_password as password.
        """
        return get_user_model().objects.create_user(self.user_email, self.user_password)

    def test_user_creation(self):
        # Create a new user saving the time frame
        before_creation = timezone.now()
        self.create_user()
        after_creation = timezone.now()

        # Check user exists and email is correct
        self.assertEqual(get_user_model().objects.all().count(), 1)
        self.assertEqual(get_user_model().objects.all()[0].email, self.user_email)

        # Check date_joined, date_modified and last_login dates
        self.assertLess(before_creation, get_user_model().objects.all()[0].date_joined)
        self.assertLess(get_user_model().objects.all()[0].date_joined, after_creation)

        self.assertLess(before_creation, get_user_model().objects.all()[0].last_login)
        self.assertLess(get_user_model().objects.all()[0].last_login, after_creation)

        # Check flags
        self.assertTrue(get_user_model().objects.all()[0].is_active)
        self.assertFalse(get_user_model().objects.all()[0].is_staff)
        self.assertFalse(get_user_model().objects.all()[0].is_superuser)

    def test_user_get_full_name(self):
        user = self.create_user()
        self.assertEqual(user.get_full_name(), self.user_email)

    def test_user_get_short_name(self):
        user = self.create_user()
        self.assertEqual(user.get_short_name(), self.user_email)

    def test_email_user(self):
        # Email definition
        subject = "Email Subject"
        message = "Email Message"
        from_email = 'from@normal.com'

        user = self.create_user()

        # Test that no message exists
        self.assertEqual(len(mail.outbox), 0)

        # Send test email
        user.email_user(subject, message, from_email)

        # Test that one message has been sent
        self.assertEqual(len(mail.outbox), 1)

        # Verify that the email is correct
        self.assertEqual(mail.outbox[0].subject, subject)
        self.assertEqual(mail.outbox[0].body, message)
        self.assertEqual(mail.outbox[0].from_email, from_email)
        self.assertEqual(mail.outbox[0].to, [user.email])


class UserManagerTest(TestCase):

    def test_create_user(self):
        email_lowercase = 'normal@normal.com'
        user = get_user_model().objects.create_user(email_lowercase)
        self.assertEqual(user.email, email_lowercase)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        email_lowercase = 'normal@normal.com'
        password = 'password1234$%&/'
        user = get_user_model().objects.create_superuser(email_lowercase, password)
        self.assertEqual(user.email, email_lowercase)
        self.assertTrue(user.check_password, password)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_user_creation_is_active(self):
        # Create deactivated user
        email_lowercase = 'normal@normal.com'
        password = 'password1234$%&/'
        user = get_user_model().objects.create_user(email_lowercase, password, is_active=False)
        self.assertFalse(user.is_active)

    def test_user_creation_is_staff(self):
        # Create staff user
        email_lowercase = 'normal@normal.com'
        password = 'password1234$%&/'
        user = get_user_model().objects.create_user(email_lowercase, password, is_staff=True)
        self.assertTrue(user.is_staff)

    def test_create_user_email_domain_normalize_rfc3696(self):
        # According to http://tools.ietf.org/html/rfc3696#section-3
        # the "@" symbol can be part of the local part of an email address
        returned = get_user_model().objects.normalize_email(r'Abc\@DEF@EXAMPLE.com')
        self.assertEqual(returned, r'Abc\@DEF@example.com')

    def test_create_user_email_domain_normalize(self):
        returned = get_user_model().objects.normalize_email('normal@DOMAIN.COM')
        self.assertEqual(returned, 'normal@domain.com')

    def test_create_user_email_domain_normalize_with_whitespace(self):
        returned = get_user_model().objects.normalize_email('email\ with_whitespace@D.COM')
        self.assertEqual(returned, 'email\ with_whitespace@d.com')

    def test_empty_username(self):
        self.assertRaisesMessage(ValueError,
                                 'The given email must be set',
                                 get_user_model().objects.create_user, email='')


@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class EmailUserCreationFormTest(TestCase):

    def setUp(self):
        get_user_model().objects.create_user('testclient@example.com', 'test123')

    def test_user_already_exists(self):
        data = {
            'email': 'testclient@example.com',
            'password1': 'test123',
            'password2': 'test123',
            }
        form = EmailUserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["email"].errors,
                         [force_text(form.error_messages['duplicate_email'])])

    def test_invalid_data(self):
        data = {
            'email': 'testclient',
            'password1': 'test123',
            'password2': 'test123',
            }
        form = EmailUserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['email'].errors, [_('Enter a valid email address.')])

    def test_password_verification(self):
        # The verification password is incorrect.
        data = {
            'email': 'testclient@example.com',
            'password1': 'test123',
            'password2': 'test',
            }
        form = EmailUserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password2"].errors,
                         [force_text(form.error_messages['password_mismatch'])])

    def test_both_passwords(self):
        # One (or both) passwords weren't given
        data = {'email': 'testclient@example.com'}
        form = EmailUserCreationForm(data)
        required_error = [force_text(Field.default_error_messages['required'])]
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, required_error)

        data['password2'] = 'test123'
        form = EmailUserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, [])

    def test_success(self):
        # The success case.
        data = {
            'email': 'jsmith@example.com',
            'password1': 'test123',
            'password2': 'test123',
            }
        form = EmailUserCreationForm(data)
        self.assertTrue(form.is_valid())
        u = form.save()
        self.assertEqual(repr(u), '<%s: jsmith@example.com>' % get_user_model().__name__)


@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class EmailUserChangeFormTest(TestCase):

    def setUp(self):
        testclient = get_user_model().objects.create_user('testclient@example.com')
        testclient.password = 'sha1$6efc0$f93efe9fd7542f25a7be94871ea45aa95de57161'
        testclient.save()
        get_user_model().objects.create_user('empty_password@example.com')

    def test_username_validity(self):
        user = get_user_model().objects.get(email='testclient@example.com')
        data = {'email': 'not valid'}
        form = EmailUserChangeForm(data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['email'].errors, [_('Enter a valid email address.')])

    def test_unsuable_password(self):
        user = get_user_model().objects.get(email='empty_password@example.com')
        user.set_unusable_password()
        user.save()
        form = EmailUserChangeForm(instance=user)
        self.assertIn(_("No password set."), form.as_table())

    def test_bug_19133(self):
        "The change form does not return the password value"
        # Use the form to construct the POST data
        user = get_user_model().objects.get(email='testclient@example.com')
        form_for_data = EmailUserChangeForm(instance=user)
        post_data = form_for_data.initial

        # The password field should be readonly, so anything
        # posted here should be ignored; the form will be
        # valid, and give back the 'initial' value for the
        # password field.
        post_data['password'] = 'new password'
        form = EmailUserChangeForm(instance=user, data=post_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['password'], 'sha1$6efc0$f93efe9fd7542f25a7be94871ea45aa95de57161')

    def test_bug_19349_bound_password_field(self):
        user = get_user_model().objects.get(email='testclient@example.com')
        form = EmailUserChangeForm(data={}, instance=user)
        # When rendering the bound password field,
        # ReadOnlyPasswordHashWidget needs the initial
        # value to render correctly
        self.assertEqual(form.initial['password'], form['password'].value())


class EmailUserAdminTest(TestCase):

    def test_admin(self):
        # Force Django to load ModelAdmin objects
        admin.autodiscover()

########NEW FILE########
__FILENAME__ = models
from custom_user.models import AbstractEmailUser


class MyCustomEmailUser(AbstractEmailUser):
    pass

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
USE_TZ = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'custom_user',
]
SECRET_KEY = 'not_random'
AUTH_USER_MODEL = 'custom_user.EmailUser'

########NEW FILE########
__FILENAME__ = settings_subclass
DEBUG = True
USE_TZ = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'custom_user',
    'test_custom_user_subclass',
]
SECRET_KEY = 'not_random'
AUTH_USER_MODEL = 'test_custom_user_subclass.MyCustomEmailUser'

########NEW FILE########
