__FILENAME__ = admin
"""
Override the add- and change-form in the admin, to hide the username.
"""
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib import admin
from emailusernames.forms import EmailUserCreationForm, EmailUserChangeForm
from django.utils.translation import ugettext_lazy as _


class EmailUserAdmin(UserAdmin):
    add_form = EmailUserCreationForm
    form = EmailUserChangeForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
    )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Groups'), {'fields': ('groups',)}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)


admin.site.unregister(User)
admin.site.register(User, EmailUserAdmin)


def __email_unicode__(self):
    return self.email

########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

from emailusernames.utils import get_user


class EmailAuthBackend(ModelBackend):

    """Allow users to log in with their email address"""

    def authenticate(self, email=None, password=None, **kwargs):
        # Some authenticators expect to authenticate by 'username'
        if email is None:
            email = kwargs.get('username')

        try:
            user = get_user(email)
            if user.check_password(password):
                user.backend = "%s.%s" % (self.__module__, self.__class__.__name__)
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from emailusernames.utils import user_exists


ERROR_MESSAGE = _("Please enter a correct email and password. ")
ERROR_MESSAGE_RESTRICTED = _("You do not have permission to access the admin.")
ERROR_MESSAGE_INACTIVE = _("This account is inactive.")


class EmailAuthenticationForm(AuthenticationForm):
    """
    Override the default AuthenticationForm to force email-as-username behavior.
    """
    email = forms.EmailField(label=_("Email"), max_length=75)
    message_incorrect_password = ERROR_MESSAGE
    message_inactive = ERROR_MESSAGE_INACTIVE

    def __init__(self, request=None, *args, **kwargs):
        super(EmailAuthenticationForm, self).__init__(request, *args, **kwargs)
        del self.fields['username']
        self.fields.keyOrder = ['email', 'password']

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if (self.user_cache is None):
                raise forms.ValidationError(self.message_incorrect_password)
            if not self.user_cache.is_active:
                raise forms.ValidationError(self.message_inactive)
        self.check_for_test_cookie()
        return self.cleaned_data


class EmailAdminAuthenticationForm(AdminAuthenticationForm):
    """
    Override the default AuthenticationForm to force email-as-username behavior.
    """
    email = forms.EmailField(label=_("Email"), max_length=75)
    message_incorrect_password = ERROR_MESSAGE
    message_inactive = ERROR_MESSAGE_INACTIVE
    message_restricted = ERROR_MESSAGE_RESTRICTED

    def __init__(self, *args, **kwargs):
        super(EmailAdminAuthenticationForm, self).__init__(*args, **kwargs)
        del self.fields['username']

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if (self.user_cache is None):
                raise forms.ValidationError(self.message_incorrect_password)
            if not self.user_cache.is_active:
                raise forms.ValidationError(self.message_inactive)
            if not self.user_cache.is_staff:
                raise forms.ValidationError(self.message_restricted)
        self.check_for_test_cookie()
        return self.cleaned_data


class EmailUserCreationForm(UserCreationForm):
    """
    Override the default UserCreationForm to force email-as-username behavior.
    """
    email = forms.EmailField(label=_("Email"), max_length=75)

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super(EmailUserCreationForm, self).__init__(*args, **kwargs)
        del self.fields['username']

    def clean_email(self):
        email = self.cleaned_data["email"]
        if user_exists(email):
            raise forms.ValidationError(_("A user with that email already exists."))
        return email

    def save(self, commit=True):
        # Ensure that the username is set to the email address provided,
        # so the user_save_patch() will keep things in sync.
        self.instance.username = self.instance.email
        return super(EmailUserCreationForm, self).save(commit=commit)


class EmailUserChangeForm(UserChangeForm):
    """
    Override the default UserChangeForm to force email-as-username behavior.
    """
    email = forms.EmailField(label=_("Email"), max_length=75)

    class Meta:
        model = User

    def __init__(self, *args, **kwargs):
        super(EmailUserChangeForm, self).__init__(*args, **kwargs)
        del self.fields['username']

########NEW FILE########
__FILENAME__ = createsuperuser
"""
Management utility to create superusers.
Replace default behaviour to use emails as usernames.
"""

import getpass
import re
import sys
from optparse import make_option
from django.contrib.auth.models import User
from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from emailusernames.utils import get_user, create_superuser

def is_valid_email(value):
    # copied from https://github.com/django/django/blob/1.5.1/django/core/validators.py#L98
    email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    # quoted-string, see also http://tools.ietf.org/html/rfc2822#section-3.2.5
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"'
    r')@((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)$)'  # domain
    r'|\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$', re.IGNORECASE)  # literal form, ipv4 address (SMTP 4.1.3)

    if not email_re.search(value):
        raise exceptions.ValidationError(_('Enter a valid e-mail address.'))


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--email', dest='email', default=None,
            help='Specifies the email address for the superuser.'),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help=('Tells Django to NOT prompt the user for input of any kind. '
                  'You must use --username and --email with --noinput, and '
                  'superusers created with --noinput will not be able to log '
                  'in until they\'re given a valid password.')),
    )
    help = 'Used to create a superuser.'

    def handle(self, *args, **options):
        email = options.get('email', None)
        interactive = options.get('interactive')
        verbosity = int(options.get('verbosity', 1))

        # Do quick and dirty validation if --noinput
        if not interactive:
            if not email:
                raise CommandError("You must use --email with --noinput.")
            try:
                is_valid_email(email)
            except exceptions.ValidationError:
                raise CommandError("Invalid email address.")

        # If not provided, create the user with an unusable password
        password = None

        # Prompt for username/email/password. Enclose this whole thing in a
        # try/except to trap for a keyboard interrupt and exit gracefully.
        if interactive:
            try:
                # Get an email
                while 1:
                    if not email:
                        email = raw_input('E-mail address: ')

                    try:
                        is_valid_email(email)
                    except exceptions.ValidationError:
                        sys.stderr.write("Error: That e-mail address is invalid.\n")
                        email = None
                        continue

                    try:
                        get_user(email)
                    except User.DoesNotExist:
                        break
                    else:
                        sys.stderr.write("Error: That email is already taken.\n")
                        email = None

                # Get a password
                while 1:
                    if not password:
                        password = getpass.getpass()
                        password2 = getpass.getpass('Password (again): ')
                        if password != password2:
                            sys.stderr.write("Error: Your passwords didn't match.\n")
                            password = None
                            continue
                    if password.strip() == '':
                        sys.stderr.write("Error: Blank passwords aren't allowed.\n")
                        password = None
                        continue
                    break
            except KeyboardInterrupt:
                sys.stderr.write("\nOperation cancelled.\n")
                sys.exit(1)

        # Make Django's tests work by accepting a username through
        # call_command() but not through manage.py
        username = options.get('username', None)
        if username is None:
            create_superuser(email, password)
        else:
            User.objects.create_superuser(username, email, password)

        if verbosity >= 1:
            self.stdout.write("Superuser created successfully.\n")

########NEW FILE########
__FILENAME__ = dumpdata
from django.core.management.commands import dumpdata
from emailusernames.models import unmonkeypatch_user, monkeypatch_user


class Command(dumpdata.Command):

    """
    Override the built-in dumpdata command to un-monkeypatch the User
    model before dumping, to allow usernames to be dumped correctly
    """

    def handle(self, *args, **kwargs):
        unmonkeypatch_user()
        ret = super(Command, self).handle(*args, **kwargs)
        monkeypatch_user()
        return ret

########NEW FILE########
__FILENAME__ = loaddata
from django.core.management.commands import loaddata
from emailusernames.models import unmonkeypatch_user, monkeypatch_user


class Command(loaddata.Command):

    """
    Override the built-in loaddata command to un-monkeypatch the User
    model before loading, to allow usernames to be loaded correctly
    """

    def handle(self, *args, **kwargs):
        unmonkeypatch_user()
        ret = super(Command, self).handle(*args, **kwargs)
        monkeypatch_user()
        return ret
        

########NEW FILE########
__FILENAME__ = models
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from emailusernames.forms import EmailAdminAuthenticationForm
from emailusernames.utils import _email_to_username


# Horrible monkey patching.
# User.username always presents as the email, but saves as a hash of the email.
# It would be possible to avoid such a deep level of monkey-patching,
# but Django's admin displays the "Welcome, username" using user.username,
# and there's really no other way to get around it.
def user_init_patch(self, *args, **kwargs):
    super(User, self).__init__(*args, **kwargs)
    self._username = self.username
    if self.username == _email_to_username(self.email):
        # Username should be replaced by email, since the hashes match
        self.username = self.email


def user_save_patch(self, *args, **kwargs):
    email_as_username = (self.username.lower() == self.email.lower())
    if self.pk is not None:
        try:
            old_user = self.__class__.objects.get(pk=self.pk)
            email_as_username = (
                email_as_username or
                ('@' in self.username and old_user.username == old_user.email)
            )
        except self.__class__.DoesNotExist:
            pass

    if email_as_username:
        self.username = _email_to_username(self.email)
    try:
        super(User, self).save_base(*args, **kwargs)
    finally:
        if email_as_username:
            self.username = self.email


original_init = User.__init__
original_save_base = User.save_base


def monkeypatch_user():
    User.__init__ = user_init_patch
    User.save_base = user_save_patch


def unmonkeypatch_user():
    User.__init__ = original_init
    User.save_base = original_save_base


monkeypatch_user()


# Monkey-path the admin site to use a custom login form
AdminSite.login_form = EmailAdminAuthenticationForm
AdminSite.login_template = 'email_usernames/login.html'

########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from emailusernames.utils import create_user


class CreateUserTests(TestCase):
    """
    Tests which create users.
    """
    def setUp(self):
        self.email = 'user@example.com'
        self.password = 'password'

    def test_can_create_user(self):
        user = create_user(self.email, self.password)
        self.assertEquals(list(User.objects.all()), [user])

    def test_can_create_user_with_long_email(self):
        padding = 'a' * 30
        create_user(padding + self.email, self.password)

    def test_created_user_has_correct_details(self):
        user = create_user(self.email, self.password)
        self.assertEquals(user.email, self.email)

    def test_can_create_user_with_explicit_id(self):
        """Regression test for
        https://github.com/dabapps/django-email-as-username/issues/52

        """
        User.objects.create(email=self.email, id=1)



class ExistingUserTests(TestCase):
    """
    Tests which require an existing user.
    """

    def setUp(self):
        self.email = 'user@example.com'
        self.password = 'password'
        self.user = create_user(self.email, self.password)

    def test_user_can_authenticate(self):
        auth = authenticate(email=self.email, password=self.password)
        self.assertEquals(self.user, auth)

    def test_user_can_authenticate_with_case_insensitive_match(self):
        auth = authenticate(email=self.email.upper(), password=self.password)
        self.assertEquals(self.user, auth)

    def test_user_can_authenticate_with_username_parameter(self):
        auth = authenticate(username=self.email, password=self.password)
        self.assertEquals(self.user, auth)
        # Invalid username should be ignored
        auth = authenticate(email=self.email, password=self.password,
                            username='invalid')
        self.assertEquals(self.user, auth)

    def test_user_emails_are_unique(self):
        with self.assertRaises(IntegrityError) as ctx:
            create_user(self.email, self.password)
        self.assertEquals(ctx.exception.message, 'user email is not unique')

    def test_user_emails_are_case_insensitive_unique(self):
        with self.assertRaises(IntegrityError) as ctx:
            create_user(self.email.upper(), self.password)
        self.assertEquals(ctx.exception.message, 'user email is not unique')

    def test_user_unicode(self):
        self.assertEquals(unicode(self.user), self.email)

########NEW FILE########
__FILENAME__ = utils
import base64
import hashlib
import os
import re
import sys

from django.contrib.auth.models import User
from django.db import IntegrityError


# We need to convert emails to hashed versions when we store them in the
# username field.  We can't just store them directly, or we'd be limited
# to Django's username <= 30 chars limit, which is really too small for
# arbitrary emails.
def _email_to_username(email):
    # Emails should be case-insensitive unique
    email = email.lower()
    # Deal with internationalized email addresses
    converted = email.encode('utf8', 'ignore')
    return base64.urlsafe_b64encode(hashlib.sha256(converted).digest())[:30]


def get_user(email, queryset=None):
    """
    Return the user with given email address.
    Note that email address matches are case-insensitive.
    """
    if queryset is None:
        queryset = User.objects
    return queryset.get(username=_email_to_username(email))


def user_exists(email, queryset=None):
    """
    Return True if a user with given email address exists.
    Note that email address matches are case-insensitive.
    """
    try:
        get_user(email, queryset)
    except User.DoesNotExist:
        return False
    return True


_DUPLICATE_USERNAME_ERRORS = (
    'column username is not unique',
    'duplicate key value violates unique constraint "auth_user_username_key"\n'
)


def create_user(email, password=None, is_staff=None, is_active=None):
    """
    Create a new user with the given email.
    Use this instead of `User.objects.create_user`.
    """
    try:
        user = User.objects.create_user(email, email, password)
    except IntegrityError, err:
        regexp = '|'.join(re.escape(e) for e in _DUPLICATE_USERNAME_ERRORS)
        if re.match(regexp, err.message):
            raise IntegrityError('user email is not unique')
        raise

    if is_active is not None or is_staff is not None:
        if is_active is not None:
            user.is_active = is_active
        if is_staff is not None:
            user.is_staff = is_staff
        user.save()
    return user


def create_superuser(email, password):
    """
    Create a new superuser with the given email.
    Use this instead of `User.objects.create_superuser`.
    """
    return User.objects.create_superuser(email, email, password)


def migrate_usernames(stream=None, quiet=False):
    """
    Migrate all existing users to django-email-as-username hashed usernames.
    If any users cannot be migrated an exception will be raised and the
    migration will not run.
    """
    stream = stream or (quiet and open(os.devnull, 'w') or sys.stdout)

    # Check all users can be migrated before applying migration
    emails = set()
    errors = []
    for user in User.objects.all():
        if not user.email:
            errors.append("Cannot convert user '%s' because email is not "
                          "set." % (user._username, ))
        elif user.email.lower() in emails:
            errors.append("Cannot convert user '%s' because email '%s' "
                          "already exists." % (user._username, user.email))
        else:
            emails.add(user.email.lower())

    # Cannot migrate.
    if errors:
        [stream.write(error + '\n') for error in errors]
        raise Exception('django-email-as-username migration failed.')

    # Can migrate just fine.
    total = User.objects.count()
    for user in User.objects.all():
        user.username = _email_to_username(user.email)
        user.save()

    stream.write("Successfully migrated usernames for all %d users\n"
                 % (total, ))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testsettings")

    from django.core.management import execute_from_command_line

    args = sys.argv
    if len(args) == 2 and args[1] == 'test':
        args.append('emailusernames')

    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = testsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'emailusernames',
)

AUTHENTICATION_BACKENDS = (
    'emailusernames.backends.EmailAuthBackend',
)

########NEW FILE########
