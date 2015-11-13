__FILENAME__ = admin
from __future__ import unicode_literals

from django.contrib import admin

from account.models import Account, SignupCode, AccountDeletion, EmailAddress


class SignupCodeAdmin(admin.ModelAdmin):

    list_display = ["code", "max_uses", "use_count", "expiry", "created"]
    search_fields = ["code", "email"]
    list_filter = ["created"]


class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ["user", "email", "verified", "primary"]
    search_fields = ["user", "email"]
    list_filter = ["user"]


admin.site.register(Account)
admin.site.register(SignupCode, SignupCodeAdmin)
admin.site.register(AccountDeletion, list_display=["email", "date_requested", "date_expunged"])
admin.site.register(EmailAddress, EmailAddressAdmin)

########NEW FILE########
__FILENAME__ = auth_backends
from __future__ import unicode_literals

from django.db.models import Q

from django.contrib.auth.backends import ModelBackend

from account.compat import get_user_model, get_user_lookup_kwargs
from account.models import EmailAddress


class UsernameAuthenticationBackend(ModelBackend):

    def authenticate(self, **credentials):
        User = get_user_model()
        lookup_kwargs = get_user_lookup_kwargs({
            "{username}__iexact": credentials["username"]
        })
        try:
            user = User.objects.get(**lookup_kwargs)
        except (User.DoesNotExist, KeyError):
            return None
        else:
            try:
                if user.check_password(credentials["password"]):
                    return user
            except KeyError:
               return None 

class EmailAuthenticationBackend(ModelBackend):

    def authenticate(self, **credentials):
        qs = EmailAddress.objects.filter(Q(primary=True) | Q(verified=True))
        try:
            email_address = qs.get(email__iexact=credentials["username"])
        except (EmailAddress.DoesNotExist, KeyError):
            return None
        else:
            user = email_address.user
            try:
                if user.check_password(credentials["password"]):
                    return user
            except KeyError:
                return None

########NEW FILE########
__FILENAME__ = callbacks
from __future__ import unicode_literals


def account_delete_mark(deletion):
    deletion.user.is_active = False
    deletion.user.save()


def account_delete_expunge(deletion):
    deletion.user.delete()

########NEW FILE########
__FILENAME__ = compat
import django

from django.db.models.signals import class_prepared
from django.utils import six

try:
    from django.contrib.auth import get_user_model as auth_get_user_model
except ImportError:
    auth_get_user_model = None
    from django.contrib.auth.models import User

from account.conf import settings


AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


def get_user_model(*args, **kwargs):
    if auth_get_user_model is not None:
        return auth_get_user_model(*args, **kwargs)
    else:
        return User


def get_user_lookup_kwargs(kwargs):
    result = {}
    username_field = getattr(get_user_model(), "USERNAME_FIELD", "username")
    for key, value in kwargs.items():
        result[key.format(username=username_field)] = value
    return result


def receiver(signal, **kwargs):
    if django.VERSION < (1, 7, 0):
        unresolved_references = {}
        def _resolve_references(sender, **kwargs):
            opts = sender._meta
            reference = (opts.app_label, opts.object_name)
            try:
                receivers = unresolved_references.pop(reference)
            except KeyError:
                pass
            else:
                for signal, func, kwargs in receivers:
                    kwargs["sender"] = sender
                    signal.connect(func, **kwargs)
        class_prepared.connect(_resolve_references, weak=False)
    def _decorator(func):
        if django.VERSION < (1, 7, 0):
            from django.db.models.loading import cache as app_cache
            sender = kwargs.get("sender")
            if isinstance(sender, six.string_types):
                try:
                    app_label, model_name = sender.split(".")
                except ValueError:
                    raise ValueError(
                        "Specified sender must either be a model or a "
                        "model name of the 'app_label.ModelName' form."
                    )
                sender = app_cache.app_models.get(app_label, {}).get(model_name.lower())
                if sender is None:
                    ref = (app_label, model_name)
                    refs = unresolved_references.setdefault(ref, [])
                    refs.append((signal, func, kwargs))
                    return func
                else:
                    kwargs["sender"] = sender
        signal.connect(func, **kwargs)
        return func
    return _decorator

########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.translation import get_language_info

import pytz

from appconf import AppConf


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i+1:]
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing {0}: '{1}'".format(module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '{0}' does not define a '{1}'".format(module, attr))
    return attr


class AccountAppConf(AppConf):

    OPEN_SIGNUP = True
    LOGIN_URL = "account_login"
    SIGNUP_REDIRECT_URL = "/"
    LOGIN_REDIRECT_URL = "/"
    LOGOUT_REDIRECT_URL = "/"
    PASSWORD_CHANGE_REDIRECT_URL = "account_password"
    PASSWORD_RESET_REDIRECT_URL = "account_login"
    REMEMBER_ME_EXPIRY = 60*60*24*365*10
    USER_DISPLAY = lambda user: user.username
    CREATE_ON_SAVE = True
    EMAIL_UNIQUE = True
    EMAIL_CONFIRMATION_REQUIRED = False
    EMAIL_CONFIRMATION_EMAIL = True
    EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
    EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = "account_login"
    EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = None
    SETTINGS_REDIRECT_URL = "account_settings"
    NOTIFY_ON_PASSWORD_CHANGE = True
    DELETION_MARK_CALLBACK = "account.callbacks.account_delete_mark"
    DELETION_EXPUNGE_CALLBACK = "account.callbacks.account_delete_expunge"
    DELETION_EXPUNGE_HOURS = 48
    HOOKSET = "account.hooks.AccountDefaultHookSet"
    TIMEZONES = list(zip(pytz.all_timezones, pytz.all_timezones))
    LANGUAGES = [
        (code, get_language_info(code).get("name_local"))
        for code, lang in settings.LANGUAGES
    ]
    USE_AUTH_AUTHENTICATE = False

    def configure_deletion_mark_callback(self, value):
        return load_path_attr(value)

    def configure_deletion_expunge_callback(self, value):
        return load_path_attr(value)

    def configure_hookset(self, value):
        return load_path_attr(value)()

########NEW FILE########
__FILENAME__ = context_processors
from __future__ import unicode_literals

from account.conf import settings
from account.models import Account


def account(request):
    ctx = {
        "account": Account.for_request(request),
        "ACCOUNT_OPEN_SIGNUP": settings.ACCOUNT_OPEN_SIGNUP,
    }
    return ctx

########NEW FILE########
__FILENAME__ = decorators
from __future__ import unicode_literals

import functools

from django.utils.decorators import available_attrs

from account.utils import handle_redirect_to_login


def login_required(func=None, redirect_field_name="next", login_url=None):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log in page if necessary.
    """
    def decorator(view_func):
        @functools.wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated():
                return view_func(request, *args, **kwargs)
            return handle_redirect_to_login(
                request,
                redirect_field_name=redirect_field_name,
                login_url=login_url
            )
        return _wrapped_view
    if func:
        return decorator(func)
    return decorator

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals

from django.db import models
from django.utils import six

from account.conf import settings

HAS_SOUTH = True
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    HAS_SOUTH = False


class TimeZoneField(six.with_metaclass(models.SubfieldBase, models.CharField)):

    def __init__(self, *args, **kwargs):
        defaults = {
            "max_length": 100,
            "default": "",
            "choices": settings.ACCOUNT_TIMEZONES,
            "blank": True,
        }
        defaults.update(kwargs)
        return super(TimeZoneField, self).__init__(*args, **defaults)


if HAS_SOUTH:
    add_introspection_rules([], ["^account\.fields\.TimeZoneField"])

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

import re

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = None

from django import forms
from django.utils.translation import ugettext_lazy as _

from django.contrib import auth

from account.compat import get_user_model, get_user_lookup_kwargs
from account.conf import settings
from account.hooks import hookset
from account.models import EmailAddress


alnum_re = re.compile(r"^\w+$")


class SignupForm(forms.Form):

    username = forms.CharField(
        label=_("Username"),
        max_length=30,
        widget=forms.TextInput(),
        required=True
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(render_value=False)
    )
    password_confirm = forms.CharField(
        label=_("Password (again)"),
        widget=forms.PasswordInput(render_value=False)
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.TextInput(), required=True)

    code = forms.CharField(
        max_length=64,
        required=False,
        widget=forms.HiddenInput()
    )

    def clean_username(self):
        if not alnum_re.search(self.cleaned_data["username"]):
            raise forms.ValidationError(_("Usernames can only contain letters, numbers and underscores."))
        User = get_user_model()
        lookup_kwargs = get_user_lookup_kwargs({
            "{username}__iexact": self.cleaned_data["username"]
        })
        qs = User.objects.filter(**lookup_kwargs)
        if not qs.exists():
            return self.cleaned_data["username"]
        raise forms.ValidationError(_("This username is already taken. Please choose another."))

    def clean_email(self):
        value = self.cleaned_data["email"]
        qs = EmailAddress.objects.filter(email__iexact=value)
        if not qs.exists() or not settings.ACCOUNT_EMAIL_UNIQUE:
            return value
        raise forms.ValidationError(_("A user is registered with this email address."))

    def clean(self):
        if "password" in self.cleaned_data and "password_confirm" in self.cleaned_data:
            if self.cleaned_data["password"] != self.cleaned_data["password_confirm"]:
                raise forms.ValidationError(_("You must type the same password each time."))
        return self.cleaned_data


class LoginForm(forms.Form):

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(render_value=False)
    )
    remember = forms.BooleanField(
        label=_("Remember Me"),
        required=False
    )
    user = None

    def clean(self):
        if self._errors:
            return
        user = auth.authenticate(**self.user_credentials())
        if user:
            if user.is_active:
                self.user = user
            else:
                raise forms.ValidationError(_("This account is inactive."))
        else:
            raise forms.ValidationError(self.authentication_fail_message)
        return self.cleaned_data

    def user_credentials(self):
        return hookset.get_user_credentials(self, self.identifier_field)


class LoginUsernameForm(LoginForm):

    username = forms.CharField(label=_("Username"), max_length=30)
    authentication_fail_message = _("The username and/or password you specified are not correct.")
    identifier_field = "username"

    def __init__(self, *args, **kwargs):
        super(LoginUsernameForm, self).__init__(*args, **kwargs)
        field_order = ["username", "password", "remember"]
        if not OrderedDict or hasattr(self.fields, "keyOrder"):
            self.fields.keyOrder = field_order
        else:
            self.fields = OrderedDict((k, self.fields[k]) for k in field_order)


class LoginEmailForm(LoginForm):

    email = forms.EmailField(label=_("Email"))
    authentication_fail_message = _("The email address and/or password you specified are not correct.")
    identifier_field = "email"

    def __init__(self, *args, **kwargs):
        super(LoginEmailForm, self).__init__(*args, **kwargs)
        field_order = ["email", "password", "remember"]
        if not OrderedDict or hasattr(self.fields, "keyOrder"):
            self.fields.keyOrder = field_order
        else:
            self.fields = OrderedDict((k, self.fields[k]) for k in field_order)


class ChangePasswordForm(forms.Form):

    password_current = forms.CharField(
        label=_("Current Password"),
        widget=forms.PasswordInput(render_value=False)
    )
    password_new = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(render_value=False)
    )
    password_new_confirm = forms.CharField(
        label=_("New Password (again)"),
        widget=forms.PasswordInput(render_value=False)
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def clean_password_current(self):
        if not self.user.check_password(self.cleaned_data.get("password_current")):
            raise forms.ValidationError(_("Please type your current password."))
        return self.cleaned_data["password_current"]

    def clean_password_new_confirm(self):
        if "password_new" in self.cleaned_data and "password_new_confirm" in self.cleaned_data:
            if self.cleaned_data["password_new"] != self.cleaned_data["password_new_confirm"]:
                raise forms.ValidationError(_("You must type the same password each time."))
        return self.cleaned_data["password_new_confirm"]


class PasswordResetForm(forms.Form):

    email = forms.EmailField(label=_("Email"), required=True)

    def clean_email(self):
        value = self.cleaned_data["email"]
        if not EmailAddress.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError(_("Email address can not be found."))
        return value


class PasswordResetTokenForm(forms.Form):

    password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(render_value=False)
    )
    password_confirm = forms.CharField(
        label=_("New Password (again)"),
        widget=forms.PasswordInput(render_value=False)
    )

    def clean_password_confirm(self):
        if "password" in self.cleaned_data and "password_confirm" in self.cleaned_data:
            if self.cleaned_data["password"] != self.cleaned_data["password_confirm"]:
                raise forms.ValidationError(_("You must type the same password each time."))
        return self.cleaned_data["password_confirm"]


class SettingsForm(forms.Form):

    email = forms.EmailField(label=_("Email"), required=True)
    timezone = forms.ChoiceField(
        label=_("Timezone"),
        choices=[("", "---------")] + settings.ACCOUNT_TIMEZONES,
        required=False
    )
    if settings.USE_I18N:
        language = forms.ChoiceField(
            label=_("Language"),
            choices=settings.ACCOUNT_LANGUAGES,
            required=False
        )

    def clean_email(self):
        value = self.cleaned_data["email"]
        if self.initial.get("email") == value:
            return value
        qs = EmailAddress.objects.filter(email__iexact=value)
        if not qs.exists() or not settings.ACCOUNT_EMAIL_UNIQUE:
            return value
        raise forms.ValidationError(_("A user is registered with this email address."))

########NEW FILE########
__FILENAME__ = hooks
import hashlib
import random

from django.core.mail import send_mail
from django.template.loader import render_to_string

from account.conf import settings


class AccountDefaultHookSet(object):

    def send_invitation_email(self, to, ctx):
        subject = render_to_string("account/email/invite_user_subject.txt", ctx)
        message = render_to_string("account/email/invite_user.txt", ctx)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, to)

    def send_confirmation_email(self, to, ctx):
        subject = render_to_string("account/email/email_confirmation_subject.txt", ctx)
        subject = "".join(subject.splitlines()) # remove superfluous line breaks
        message = render_to_string("account/email/email_confirmation_message.txt", ctx)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, to)

    def send_password_change_email(self, to, ctx):
        subject = render_to_string("account/email/password_change_subject.txt", ctx)
        subject = "".join(subject.splitlines())
        message = render_to_string("account/email/password_change.txt", ctx)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, to)

    def send_password_reset_email(self, to, ctx):
        subject = render_to_string("account/email/password_reset_subject.txt", ctx)
        subject = "".join(subject.splitlines())
        message = render_to_string("account/email/password_reset.txt", ctx)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, to)

    def generate_random_token(self, extra=None, hash_func=hashlib.sha256):
        if extra is None:
            extra = []
        bits = extra + [str(random.SystemRandom().getrandbits(512))]
        return hash_func("".join(bits).encode("utf-8")).hexdigest()

    def generate_signup_code_token(self, email=None):
        return self.generate_random_token([email])

    def generate_email_confirmation_token(self, email):
        return self.generate_random_token([email])

    def get_user_credentials(self, form, identifier_field):
        return {
            "username": form.cleaned_data[identifier_field],
            "password": form.cleaned_data["password"],
        }


class HookProxy(object):

    def __getattr__(self, attr):
        return getattr(settings.ACCOUNT_HOOKSET, attr)


hookset = HookProxy()

########NEW FILE########
__FILENAME__ = expunge_deleted
from __future__ import print_function
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from account.models import AccountDeletion


class Command(BaseCommand):

    help = "Expunge accounts deleted more than 48 hours ago."

    def handle(self, *args, **options):
        count = AccountDeletion.expunge()
        print("{0} expunged.".format(count))

########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals

from django.db import models


class EmailAddressManager(models.Manager):

    def add_email(self, user, email, **kwargs):
        confirm = kwargs.pop("confirm", False)
        email_address = self.create(user=user, email=email, **kwargs)
        if confirm and not email_address.verified:
            email_address.send_confirmation()
        return email_address

    def get_primary(self, user):
        try:
            return self.get(user=user, primary=True)
        except self.model.DoesNotExist:
            return None

    def get_users_for(self, email):
        # this is a list rather than a generator because we probably want to
        # do a len() on it right away
        return [address.user for address in self.filter(verified=True, email=email)]


class EmailConfirmationManager(models.Manager):

    def delete_expired_confirmations(self):
        for confirmation in self.all():
            if confirmation.key_expired():
                confirmation.delete()

########NEW FILE########
__FILENAME__ = middleware
from __future__ import unicode_literals

from django.utils import translation, timezone
from django.utils.cache import patch_vary_headers

from account.conf import settings
from account.models import Account


class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context depending on the user's account. This allows pages
    to be dynamically translated to the language the user desires
    (if the language is available, of course).
    """

    def get_language_for_user(self, request):
        if request.user.is_authenticated():
            try:
                account = Account.objects.get(user=request.user)
                return account.language
            except Account.DoesNotExist:
                pass
        return translation.get_language_from_request(request)

    def process_request(self, request):
        translation.activate(self.get_language_for_user(request))
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ("Accept-Language",))
        response["Content-Language"] = translation.get_language()
        translation.deactivate()
        return response


class TimezoneMiddleware(object):
    """
    This middleware sets the timezone used to display dates in
    templates to the user's timezone.
    """

    def process_request(self, request):
        try:
            account = getattr(request.user, "account", None)
        except Account.DoesNotExist:
            pass
        else:
            if account:
                tz = settings.TIME_ZONE if not account.timezone else account.timezone
                timezone.activate(tz)

########NEW FILE########
__FILENAME__ = mixins
from __future__ import unicode_literals

from account.conf import settings
from account.utils import handle_redirect_to_login


class LoginRequiredMixin(object):

    redirect_field_name = "next"
    login_url = None

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        if request.user.is_authenticated():
            return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
        return self.redirect_to_login()

    def get_login_url(self):
        return self.login_url or settings.ACCOUNT_LOGIN_URL

    def get_next_url(self):
        return self.request.get_full_path()

    def redirect_to_login(self):
        return handle_redirect_to_login(
            self.request,
            redirect_field_name=self.redirect_field_name,
            login_url=self.get_login_url(),
            next_url=self.get_next_url(),
        )

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

import datetime
import operator

try:
    from urllib.parse import urlencode
except ImportError: # python 2
    from urllib import urlencode

from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils import timezone, translation, six
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site

import pytz

from account import signals
from account.compat import AUTH_USER_MODEL, receiver
from account.conf import settings
from account.fields import TimeZoneField
from account.hooks import hookset
from account.managers import EmailAddressManager, EmailConfirmationManager
from account.signals import signup_code_sent, signup_code_used


class Account(models.Model):

    user = models.OneToOneField(AUTH_USER_MODEL, related_name="account", verbose_name=_("user"))
    timezone = TimeZoneField(_("timezone"))
    language = models.CharField(_("language"),
        max_length=10,
        choices=settings.ACCOUNT_LANGUAGES,
        default=settings.LANGUAGE_CODE
    )

    @classmethod
    def for_request(cls, request):
        if request.user.is_authenticated():
            try:
                account = Account._default_manager.get(user=request.user)
            except Account.DoesNotExist:
                account = AnonymousAccount(request)
        else:
            account = AnonymousAccount(request)
        return account

    @classmethod
    def create(cls, request=None, **kwargs):
        create_email = kwargs.pop("create_email", True)
        confirm_email = kwargs.pop("confirm_email", None)
        account = cls(**kwargs)
        if "language" not in kwargs:
            if request is None:
                account.language = settings.LANGUAGE_CODE
            else:
                account.language = translation.get_language_from_request(request, check_path=True)
        account.save()
        if create_email and account.user.email:
            kwargs = {"primary": True}
            if confirm_email is not None:
                kwargs["confirm"] = confirm_email
            EmailAddress.objects.add_email(account.user, account.user.email, **kwargs)
        return account

    def __str__(self):
        return str(self.user)

    def now(self):
        """
        Returns a timezone aware datetime localized to the account's timezone.
        """
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone("UTC"))
        timezone = settings.TIME_ZONE if not self.timezone else self.timezone
        return now.astimezone(pytz.timezone(timezone))

    def localtime(self, value):
        """
        Given a datetime object as value convert it to the timezone of
        the account.
        """
        timezone = settings.TIME_ZONE if not self.timezone else self.timezone
        if value.tzinfo is None:
            value = pytz.timezone(settings.TIME_ZONE).localize(value)
        return value.astimezone(pytz.timezone(timezone))


@receiver(post_save, sender=AUTH_USER_MODEL)
def user_post_save(sender, **kwargs):
    """
    After User.save is called we check to see if it was a created user. If so,
    we check if the User object wants account creation. If all passes we
    create an Account object.

    We only run on user creation to avoid having to check for existence on
    each call to User.save.
    """
    user, created = kwargs["instance"], kwargs["created"]
    disabled = getattr(user, "_disable_account_creation", not settings.ACCOUNT_CREATE_ON_SAVE)
    if created and not disabled:
        Account.create(user=user)


class AnonymousAccount(object):

    def __init__(self, request=None):
        self.user = AnonymousUser()
        self.timezone = settings.TIME_ZONE
        if request is None:
            self.language = settings.LANGUAGE_CODE
        else:
            self.language = translation.get_language_from_request(request, check_path=True)

    def __unicode__(self):
        return "AnonymousAccount"


class SignupCode(models.Model):

    class AlreadyExists(Exception):
        pass

    class InvalidCode(Exception):
        pass

    code = models.CharField(max_length=64, unique=True)
    max_uses = models.PositiveIntegerField(default=0)
    expiry = models.DateTimeField(null=True, blank=True)
    inviter = models.ForeignKey(AUTH_USER_MODEL, null=True, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    sent = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(default=timezone.now, editable=False)
    use_count = models.PositiveIntegerField(editable=False, default=0)

    def __unicode__(self):
        if self.email:
            return "{0} [{1}]".format(self.email, self.code)
        else:
            return self.code

    @classmethod
    def exists(cls, code=None, email=None):
        checks = []
        if code:
            checks.append(Q(code=code))
        if email:
            checks.append(Q(email=code))
        return cls._default_manager.filter(six.moves.reduce(operator.or_, checks)).exists()

    @classmethod
    def create(cls, **kwargs):
        email, code = kwargs.get("email"), kwargs.get("code")
        if kwargs.get("check_exists", True) and cls.exists(code=code, email=email):
            raise cls.AlreadyExists()
        expiry = timezone.now() + datetime.timedelta(hours=kwargs.get("expiry", 24))
        if not code:
            code = hookset.generate_signup_code_token(email)
        params = {
            "code": code,
            "max_uses": kwargs.get("max_uses", 0),
            "expiry": expiry,
            "inviter": kwargs.get("inviter"),
            "notes": kwargs.get("notes", "")
        }
        if email:
            params["email"] = email
        return cls(**params)

    @classmethod
    def check_code(cls, code):
        try:
            signup_code = cls._default_manager.get(code=code)
        except cls.DoesNotExist:
            raise cls.InvalidCode()
        else:
            if signup_code.max_uses and signup_code.max_uses <= signup_code.use_count:
                raise cls.InvalidCode()
            else:
                if signup_code.expiry and timezone.now() > signup_code.expiry:
                    raise cls.InvalidCode()
                else:
                    return signup_code

    def calculate_use_count(self):
        self.use_count = self.signupcoderesult_set.count()
        self.save()

    def use(self, user):
        """
        Add a SignupCode result attached to the given user.
        """
        result = SignupCodeResult()
        result.signup_code = self
        result.user = user
        result.save()
        signup_code_used.send(sender=result.__class__, signup_code_result=result)

    def send(self, **kwargs):
        protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
        current_site = kwargs["site"] if "site" in kwargs else Site.objects.get_current()
        if "signup_url" not in kwargs:
            signup_url = "{0}://{1}{2}?{3}".format(
                protocol,
                current_site.domain,
                reverse("account_signup"),
                urlencode({"code": self.code})
            )
        else:
            signup_url = kwargs["signup_url"]
        ctx = {
            "signup_code": self,
            "current_site": current_site,
            "signup_url": signup_url,
        }
        ctx.update(kwargs.get("extra_ctx", {}))
        hookset.send_invitation_email([self.email], ctx)
        self.sent = timezone.now()
        self.save()
        signup_code_sent.send(sender=SignupCode, signup_code=self)


class SignupCodeResult(models.Model):

    signup_code = models.ForeignKey(SignupCode)
    user = models.ForeignKey(AUTH_USER_MODEL)
    timestamp = models.DateTimeField(default=timezone.now)

    def save(self, **kwargs):
        super(SignupCodeResult, self).save(**kwargs)
        self.signup_code.calculate_use_count()


class EmailAddress(models.Model):

    user = models.ForeignKey(AUTH_USER_MODEL)
    email = models.EmailField(unique=settings.ACCOUNT_EMAIL_UNIQUE)
    verified = models.BooleanField(default=False)
    primary = models.BooleanField(default=False)

    objects = EmailAddressManager()

    class Meta:
        verbose_name = _("email address")
        verbose_name_plural = _("email addresses")
        if not settings.ACCOUNT_EMAIL_UNIQUE:
            unique_together = [("user", "email")]

    def __unicode__(self):
        return "{0} ({1})".format(self.email, self.user)

    def set_as_primary(self, conditional=False):
        old_primary = EmailAddress.objects.get_primary(self.user)
        if old_primary:
            if conditional:
                return False
            old_primary.primary = False
            old_primary.save()
        self.primary = True
        self.save()
        self.user.email = self.email
        self.user.save()
        return True

    def send_confirmation(self, **kwargs):
        confirmation = EmailConfirmation.create(self)
        confirmation.send(**kwargs)
        return confirmation

    def change(self, new_email, confirm=True):
        """
        Given a new email address, change self and re-confirm.
        """
        with transaction.commit_on_success():
            self.user.email = new_email
            self.user.save()
            self.email = new_email
            self.verified = False
            self.save()
            if confirm:
                self.send_confirmation()


class EmailConfirmation(models.Model):

    email_address = models.ForeignKey(EmailAddress)
    created = models.DateTimeField(default=timezone.now())
    sent = models.DateTimeField(null=True)
    key = models.CharField(max_length=64, unique=True)

    objects = EmailConfirmationManager()

    class Meta:
        verbose_name = _("email confirmation")
        verbose_name_plural = _("email confirmations")

    def __unicode__(self):
        return "confirmation for {0}".format(self.email_address)

    @classmethod
    def create(cls, email_address):
        key = hookset.generate_email_confirmation_token(email_address.email)
        return cls._default_manager.create(email_address=email_address, key=key)

    def key_expired(self):
        expiration_date = self.sent + datetime.timedelta(days=settings.ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS)
        return expiration_date <= timezone.now()
    key_expired.boolean = True

    def confirm(self):
        if not self.key_expired() and not self.email_address.verified:
            email_address = self.email_address
            email_address.verified = True
            email_address.set_as_primary(conditional=True)
            email_address.save()
            signals.email_confirmed.send(sender=self.__class__, email_address=email_address)
            return email_address

    def send(self, **kwargs):
        current_site = kwargs["site"] if "site" in kwargs else Site.objects.get_current()
        protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
        activate_url = "{0}://{1}{2}".format(
            protocol,
            current_site.domain,
            reverse("account_confirm_email", args=[self.key])
        )
        ctx = {
            "email_address": self.email_address,
            "user": self.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "key": self.key,
        }
        hookset.send_confirmation_email([self.email_address.email], ctx)
        self.sent = timezone.now()
        self.save()
        signals.email_confirmation_sent.send(sender=self.__class__, confirmation=self)


class AccountDeletion(models.Model):

    user = models.ForeignKey(AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    date_requested = models.DateTimeField(default=timezone.now)
    date_expunged = models.DateTimeField(null=True, blank=True)

    @classmethod
    def expunge(cls, hours_ago=None):
        if hours_ago is None:
            hours_ago = settings.ACCOUNT_DELETION_EXPUNGE_HOURS
        before = timezone.now() - datetime.timedelta(hours=hours_ago)
        count = 0
        for account_deletion in cls.objects.filter(date_requested__lt=before, user__isnull=False):
            settings.ACCOUNT_DELETION_EXPUNGE_CALLBACK(account_deletion)
            account_deletion.date_expunged = timezone.now()
            account_deletion.save()
            count += 1
        return count

    @classmethod
    def mark(cls, user):
        account_deletion, created = cls.objects.get_or_create(user=user)
        account_deletion.email = user.email
        account_deletion.save()
        settings.ACCOUNT_DELETION_MARK_CALLBACK(account_deletion)
        return account_deletion

########NEW FILE########
__FILENAME__ = signals
from __future__ import unicode_literals

import django.dispatch


user_signed_up = django.dispatch.Signal(providing_args=["user", "form"])
user_sign_up_attempt = django.dispatch.Signal(providing_args=["username",  "email", "result"])
user_logged_in = django.dispatch.Signal(providing_args=["user", "form"])
user_login_attempt = django.dispatch.Signal(providing_args=["username", "result"])
signup_code_sent = django.dispatch.Signal(providing_args=["signup_code"])
signup_code_used = django.dispatch.Signal(providing_args=["signup_code_result"])
email_confirmed = django.dispatch.Signal(providing_args=["email_address"])
email_confirmation_sent = django.dispatch.Signal(providing_args=["confirmation"])
password_changed = django.dispatch.Signal(providing_args=["user"])

########NEW FILE########
__FILENAME__ = account_tags
from __future__ import unicode_literals

from django import template
from django.utils.html import conditional_escape

from account.utils import user_display


register = template.Library()


class UserDisplayNode(template.Node):

    def __init__(self, user, as_var=None):
        self.user_var = template.Variable(user)
        self.as_var = as_var

    def render(self, context):
        user = self.user_var.resolve(context)
        
        display = user_display(user)
        
        if self.as_var:
            context[self.as_var] = display
            return ""
        return conditional_escape(display)


@register.tag(name="user_display")
def do_user_display(parser, token):
    """
    Example usage::

        {% user_display user %}

    or if you need to use in a {% blocktrans %}::

        {% user_display user as user_display}
        {% blocktrans %}{{ user_display }} has sent you a gift.{% endblocktrans %}

    """
    bits = token.split_contents()
    if len(bits) == 2:
        user = bits[1]
        as_var = None
    elif len(bits) == 4:
        user = bits[1]
        as_var = bits[3]
    else:
        raise template.TemplateSyntaxError("'{0}' takes either two or four arguments".format(bits[0]))
    return UserDisplayNode(user, as_var)

########NEW FILE########
__FILENAME__ = test_views
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import unittest

from django.contrib.auth.models import AnonymousUser, User

from account.forms import SignupForm, LoginUsernameForm
from account.views import SignupView, LoginView


class SignupEnabledView(SignupView):

    def is_open(self):
        return True


class SignupViewTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_get(self):
        request = self.factory.get(reverse("account_signup"))
        request.user = AnonymousUser()
        response = SignupEnabledView.as_view()(request)
        self.assertEqual(response.status_code, 200)


class LoginViewTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_get(self):
        request = self.factory.get(reverse("account_login"))
        request.user = AnonymousUser()
        response = LoginView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ["account/login.html"])

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from account.views import SignupView, LoginView, LogoutView, DeleteView
from account.views import ConfirmEmailView
from account.views import ChangePasswordView, PasswordResetView, PasswordResetTokenView
from account.views import SettingsView


urlpatterns = patterns("",
    url(r"^signup/$", SignupView.as_view(), name="account_signup"),
    url(r"^login/$", LoginView.as_view(), name="account_login"),
    url(r"^logout/$", LogoutView.as_view(), name="account_logout"),
    url(r"^confirm_email/(?P<key>\w+)/$", ConfirmEmailView.as_view(), name="account_confirm_email"),
    url(r"^password/$", ChangePasswordView.as_view(), name="account_password"),
    url(r"^password/reset/$", PasswordResetView.as_view(), name="account_password_reset"),
    url(r"^password/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$", PasswordResetTokenView.as_view(), name="account_password_reset_token"),
    url(r"^settings/$", SettingsView.as_view(), name="account_settings"),
    url(r"^delete/$", DeleteView.as_view(), name="account_delete"),
)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import functools
try:
    from urllib.parse import urlparse, urlunparse
except ImportError: # python 2
    from urlparse import urlparse, urlunparse

from django.core import urlresolvers
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponseRedirect, QueryDict

from account.conf import settings


def default_redirect(request, fallback_url, **kwargs):
    redirect_field_name = kwargs.get("redirect_field_name", "next")
    next_url = request.REQUEST.get(redirect_field_name)
    if not next_url:
        # try the session if available
        if hasattr(request, "session"):
            session_key_value = kwargs.get("session_key_value", "redirect_to")
            if session_key_value in request.session:
                next_url = request.session[session_key_value]
                del request.session[session_key_value]
    is_safe = functools.partial(
        ensure_safe_url,
        allowed_protocols=kwargs.get("allowed_protocols"),
        allowed_host=request.get_host()
    )
    if next_url and is_safe(next_url):
        return next_url
    else:
        try:
            fallback_url = urlresolvers.reverse(fallback_url)
        except urlresolvers.NoReverseMatch:
            if callable(fallback_url):
                raise
            if "/" not in fallback_url and "." not in fallback_url:
                raise
        # assert the fallback URL is safe to return to caller. if it is
        # determined unsafe then raise an exception as the fallback value comes
        # from the a source the developer choose.
        is_safe(fallback_url, raise_on_fail=True)
        return fallback_url


def user_display(user):
    return settings.ACCOUNT_USER_DISPLAY(user)


def ensure_safe_url(url, allowed_protocols=None, allowed_host=None, raise_on_fail=False):
    if allowed_protocols is None:
        allowed_protocols = ["http", "https"]
    parsed = urlparse(url)
    # perform security checks to ensure no malicious intent
    # (i.e., an XSS attack with a data URL)
    safe = True
    if parsed.scheme and parsed.scheme not in allowed_protocols:
        if raise_on_fail:
            raise SuspiciousOperation("Unsafe redirect to URL with protocol '{0}'".format(parsed.scheme))
        safe = False
    if allowed_host and parsed.netloc and parsed.netloc != allowed_host:
        if raise_on_fail:
            raise SuspiciousOperation("Unsafe redirect to URL not matching host '{0}'".format(allowed_host))
        safe = False
    return safe


def handle_redirect_to_login(request, **kwargs):
    login_url = kwargs.get("login_url")
    redirect_field_name = kwargs.get("redirect_field_name")
    next_url = kwargs.get("next_url")
    if login_url is None:
        login_url = settings.ACCOUNT_LOGIN_URL
    if next_url is None:
        next_url = request.get_full_path()
    try:
        login_url = urlresolvers.reverse(login_url)
    except urlresolvers.NoReverseMatch:
        if callable(login_url):
            raise
        if "/" not in login_url and "." not in login_url:
            raise
    url_bits = list(urlparse(login_url))
    if redirect_field_name:
        querystring = QueryDict(url_bits[4], mutable=True)
        querystring[redirect_field_name] = next_url
        url_bits[4] = querystring.urlencode(safe="/")
    return HttpResponseRedirect(urlunparse(url_bits))

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404
from django.utils.http import base36_to_int, int_to_base36
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import FormView

from django.contrib import auth, messages
from django.contrib.sites.models import get_current_site
from django.contrib.auth.tokens import default_token_generator

from account import signals
from account.compat import get_user_model
from account.conf import settings
from account.forms import SignupForm, LoginUsernameForm
from account.forms import ChangePasswordForm, PasswordResetForm, PasswordResetTokenForm
from account.forms import SettingsForm
from account.hooks import hookset
from account.mixins import LoginRequiredMixin
from account.models import SignupCode, EmailAddress, EmailConfirmation, Account, AccountDeletion
from account.utils import default_redirect


class SignupView(FormView):

    template_name = "account/signup.html"
    template_name_ajax = "account/ajax/signup.html"
    template_name_email_confirmation_sent = "account/email_confirmation_sent.html"
    template_name_email_confirmation_sent_ajax = "account/ajax/email_confirmation_sent.html"
    template_name_signup_closed = "account/signup_closed.html"
    template_name_signup_closed_ajax = "account/ajax/signup_closed.html"
    form_class = SignupForm
    form_kwargs = {}
    redirect_field_name = "next"
    identifier_field = "username"
    messages = {
        "email_confirmation_sent": {
            "level": messages.INFO,
            "text": _("Confirmation email sent to {email}.")
        },
        "invalid_signup_code": {
            "level": messages.WARNING,
            "text": _("The code {code} is invalid.")
        }
    }

    def __init__(self, *args, **kwargs):
        self.created_user = None
        kwargs["signup_code"] = None
        super(SignupView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.setup_signup_code()
        return super(SignupView, self).dispatch(request, *args, **kwargs)

    def setup_signup_code(self):
        code = self.get_code()
        if code:
            try:
                self.signup_code = SignupCode.check_code(code)
            except SignupCode.InvalidCode:
                self.signup_code = None
            self.signup_code_present = True
        else:
            self.signup_code = None
            self.signup_code_present = False

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return redirect(default_redirect(self.request, settings.ACCOUNT_LOGIN_REDIRECT_URL))
        if not self.is_open():
            return self.closed()
        return super(SignupView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if not self.is_open():
            return self.closed()
        return super(SignupView, self).post(*args, **kwargs)

    def get_initial(self):
        initial = super(SignupView, self).get_initial()
        if self.signup_code:
            initial["code"] = self.signup_code.code
            if self.signup_code.email:
                initial["email"] = self.signup_code.email
        return initial

    def get_template_names(self):
        if self.request.is_ajax():
            return [self.template_name_ajax]
        else:
            return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            "redirect_field_name": redirect_field_name,
            "redirect_field_value": self.request.REQUEST.get(redirect_field_name, ""),
        })
        return ctx

    def get_form_kwargs(self):
        kwargs = super(SignupView, self).get_form_kwargs()
        kwargs.update(self.form_kwargs)
        return kwargs

    def form_invalid(self, form):
        signals.user_sign_up_attempt.send(
            sender=SignupForm,
            username=form.data.get("username"),
            email=form.data.get("email"),
            result=form.is_valid()
        )
        return super(SignupView, self).form_invalid(form)

    def form_valid(self, form):
        self.created_user = self.create_user(form, commit=False)
        # prevent User post_save signal from creating an Account instance
        # we want to handle that ourself.
        self.created_user._disable_account_creation = True
        self.created_user.save()
        self.use_signup_code(self.created_user)
        email_address = self.create_email_address(form)
        if settings.ACCOUNT_EMAIL_CONFIRMATION_REQUIRED and not email_address.verified:
            self.created_user.is_active = False
            self.created_user.save()
        self.create_account(form)
        self.after_signup(form)
        if settings.ACCOUNT_EMAIL_CONFIRMATION_EMAIL and not email_address.verified:
            self.send_email_confirmation(email_address)
        if settings.ACCOUNT_EMAIL_CONFIRMATION_REQUIRED and not email_address.verified:
            return self.email_confirmation_required_response()
        else:
            show_message = [
                settings.ACCOUNT_EMAIL_CONFIRMATION_EMAIL,
                self.messages.get("email_confirmation_sent"),
                not email_address.verified
            ]
            if all(show_message):
                messages.add_message(
                    self.request,
                    self.messages["email_confirmation_sent"]["level"],
                    self.messages["email_confirmation_sent"]["text"].format(**{
                        "email": form.cleaned_data["email"]
                    })
                )
            # attach form to self to maintain compatibility with login_user
            # API. this should only be relied on by d-u-a and it is not a stable
            # API for site developers.
            self.form = form
            self.login_user()
        return redirect(self.get_success_url())

    def get_success_url(self, fallback_url=None, **kwargs):
        if fallback_url is None:
            fallback_url = settings.ACCOUNT_SIGNUP_REDIRECT_URL
        kwargs.setdefault("redirect_field_name", self.get_redirect_field_name())
        return default_redirect(self.request, fallback_url, **kwargs)

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def create_user(self, form, commit=True, **kwargs):
        user = get_user_model()(**kwargs)
        username = form.cleaned_data.get("username")
        if username is None:
            username = self.generate_username(form)
        user.username = username
        user.email = form.cleaned_data["email"].strip()
        password = form.cleaned_data.get("password")
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user

    def create_account(self, form):
        return Account.create(request=self.request, user=self.created_user, create_email=False)

    def generate_username(self, form):
        raise NotImplementedError("Unable to generate username by default. "
            "Override SignupView.generate_username in a subclass.")

    def create_email_address(self, form, **kwargs):
        kwargs.setdefault("primary", True)
        kwargs.setdefault("verified", False)
        if self.signup_code:
            kwargs["verified"] = self.signup_code.email and self.created_user.email == self.signup_code.email
        return EmailAddress.objects.add_email(self.created_user, self.created_user.email, **kwargs)

    def use_signup_code(self, user):
        if self.signup_code:
            self.signup_code.use(user)

    def send_email_confirmation(self, email_address):
        email_address.send_confirmation(site=get_current_site(self.request))

    def after_signup(self, form):
        signals.user_signed_up.send(sender=SignupForm, user=self.created_user, form=form)

    def login_user(self):
        user = self.created_user
        if settings.ACCOUNT_USE_AUTH_AUTHENTICATE:
            # call auth.authenticate to ensure we set the correct backend for
            # future look ups using auth.get_user().
            user = auth.authenticate(**self.user_credentials())
        else:
            # set auth backend to ModelBackend, but this may not be used by
            # everyone. this code path is deprecated and will be removed in
            # favor of using auth.authenticate above.
            user.backend = "django.contrib.auth.backends.ModelBackend"
        auth.login(self.request, user)
        self.request.session.set_expiry(0)

    def user_credentials(self):
        return hookset.get_user_credentials(self.form, self.identifier_field)

    def get_code(self):
        return self.request.REQUEST.get("code")

    def is_open(self):
        if self.signup_code:
            return True
        else:
            if self.signup_code_present:
                if self.messages.get("invalid_signup_code"):
                    messages.add_message(
                        self.request,
                        self.messages["invalid_signup_code"]["level"],
                        self.messages["invalid_signup_code"]["text"].format(**{
                            "code": self.get_code(),
                        })
                    )
        return settings.ACCOUNT_OPEN_SIGNUP

    def email_confirmation_required_response(self):
        if self.request.is_ajax():
            template_name = self.template_name_email_confirmation_sent_ajax
        else:
            template_name = self.template_name_email_confirmation_sent
        response_kwargs = {
            "request": self.request,
            "template": template_name,
            "context": {
                "email": self.created_user.email,
                "success_url": self.get_success_url(),
            }
        }
        return self.response_class(**response_kwargs)

    def closed(self):
        if self.request.is_ajax():
            template_name = self.template_name_signup_closed_ajax
        else:
            template_name = self.template_name_signup_closed
        response_kwargs = {
            "request": self.request,
            "template": template_name,
        }
        return self.response_class(**response_kwargs)


class LoginView(FormView):

    template_name = "account/login.html"
    template_name_ajax = "account/ajax/login.html"
    form_class = LoginUsernameForm
    form_kwargs = {}
    redirect_field_name = "next"

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return redirect(self.get_success_url())
        return super(LoginView, self).get(*args, **kwargs)

    def get_template_names(self):
        if self.request.is_ajax():
            return [self.template_name_ajax]
        else:
            return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            "redirect_field_name": redirect_field_name,
            "redirect_field_value": self.request.REQUEST.get(redirect_field_name, ""),
        })
        return ctx

    def get_form_kwargs(self):
        kwargs = super(LoginView, self).get_form_kwargs()
        kwargs.update(self.form_kwargs)
        return kwargs

    def form_invalid(self, form):
        signals.user_login_attempt.send(
            sender=LoginView,
            username=form.data.get(form.identifier_field),
            result=form.is_valid()
        )
        return super(LoginView, self).form_invalid(form)

    def form_valid(self, form):
        self.login_user(form)
        self.after_login(form)
        return redirect(self.get_success_url())

    def after_login(self, form):
        signals.user_logged_in.send(sender=LoginView, user=form.user, form=form)

    def get_success_url(self, fallback_url=None, **kwargs):
        if fallback_url is None:
            fallback_url = settings.ACCOUNT_LOGIN_REDIRECT_URL
        kwargs.setdefault("redirect_field_name", self.get_redirect_field_name())
        return default_redirect(self.request, fallback_url, **kwargs)

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def login_user(self, form):
        auth.login(self.request, form.user)
        expiry = settings.ACCOUNT_REMEMBER_ME_EXPIRY if form.cleaned_data.get("remember") else 0
        self.request.session.set_expiry(expiry)


class LogoutView(TemplateResponseMixin, View):

    template_name = "account/logout.html"
    redirect_field_name = "next"

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated():
            return redirect(self.get_redirect_url())
        ctx = self.get_context_data()
        return self.render_to_response(ctx)

    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            auth.logout(self.request)
        return redirect(self.get_redirect_url())

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            "redirect_field_name": redirect_field_name,
            "redirect_field_value": self.request.REQUEST.get(redirect_field_name, ""),
        })
        return ctx

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def get_redirect_url(self, fallback_url=None, **kwargs):
        if fallback_url is None:
            fallback_url = settings.ACCOUNT_LOGOUT_REDIRECT_URL
        kwargs.setdefault("redirect_field_name", self.get_redirect_field_name())
        return default_redirect(self.request, fallback_url, **kwargs)


class ConfirmEmailView(TemplateResponseMixin, View):

    http_method_names = ["get", "post"]
    messages = {
        "email_confirmed": {
            "level": messages.SUCCESS,
            "text": _("You have confirmed {email}.")
        }
    }

    def get_template_names(self):
        return {
            "GET": ["account/email_confirm.html"],
            "POST": ["account/email_confirmed.html"],
        }[self.request.method]

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        ctx = self.get_context_data()
        return self.render_to_response(ctx)

    def post(self, *args, **kwargs):
        self.object = confirmation = self.get_object()
        confirmation.confirm()
        self.after_confirmation(confirmation)
        redirect_url = self.get_redirect_url()
        if not redirect_url:
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        if self.messages.get("email_confirmed"):
            messages.add_message(
                self.request,
                self.messages["email_confirmed"]["level"],
                self.messages["email_confirmed"]["text"].format(**{
                    "email": confirmation.email_address.email
                })
            )
        return redirect(redirect_url)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        try:
            return queryset.get(key=self.kwargs["key"].lower())
        except EmailConfirmation.DoesNotExist:
            raise Http404()

    def get_queryset(self):
        qs = EmailConfirmation.objects.all()
        qs = qs.select_related("email_address__user")
        return qs

    def get_context_data(self, **kwargs):
        ctx = kwargs
        ctx["confirmation"] = self.object
        return ctx

    def get_redirect_url(self):
        if self.request.user.is_authenticated():
            if not settings.ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL:
                return settings.ACCOUNT_LOGIN_REDIRECT_URL
            return settings.ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL
        else:
            return settings.ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL

    def after_confirmation(self, confirmation):
        user = confirmation.email_address.user
        user.is_active = True
        user.save()


class ChangePasswordView(FormView):

    template_name = "account/password_change.html"
    form_class = ChangePasswordForm
    redirect_field_name = "next"
    messages = {
        "password_changed": {
            "level": messages.SUCCESS,
            "text": _("Password successfully changed.")
        }
    }

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated():
            return redirect("account_password_reset")
        return super(ChangePasswordView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if not self.request.user.is_authenticated():
            return HttpResponseForbidden()
        return super(ChangePasswordView, self).post(*args, **kwargs)

    def change_password(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data["password_new"])
        user.save()

    def after_change_password(self):
        user = self.request.user
        signals.password_changed.send(sender=ChangePasswordView, user=user)
        if settings.ACCOUNT_NOTIFY_ON_PASSWORD_CHANGE:
            self.send_email(user)
        if self.messages.get("password_changed"):
            messages.add_message(
                self.request,
                self.messages["password_changed"]["level"],
                self.messages["password_changed"]["text"]
            )

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {"user": self.request.user, "initial": self.get_initial()}
        if self.request.method in ["POST", "PUT"]:
            kwargs.update({
                "data": self.request.POST,
                "files": self.request.FILES,
            })
        return kwargs

    def form_valid(self, form):
        self.change_password(form)
        self.after_change_password()
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            "redirect_field_name": redirect_field_name,
            "redirect_field_value": self.request.REQUEST.get(redirect_field_name, ""),
        })
        return ctx

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def get_success_url(self, fallback_url=None, **kwargs):
        if fallback_url is None:
            fallback_url = settings.ACCOUNT_PASSWORD_CHANGE_REDIRECT_URL
        kwargs.setdefault("redirect_field_name", self.get_redirect_field_name())
        return default_redirect(self.request, fallback_url, **kwargs)

    def send_email(self, user):
        protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
        current_site = get_current_site(self.request)
        ctx = {
            "user": user,
            "protocol": protocol,
            "current_site": current_site,
        }
        hookset.send_password_change_email([user.email], ctx)


class PasswordResetView(FormView):

    template_name = "account/password_reset.html"
    template_name_sent = "account/password_reset_sent.html"
    form_class = PasswordResetForm
    token_generator = default_token_generator

    def get_context_data(self, **kwargs):
        context = kwargs
        if self.request.method == "POST" and "resend" in self.request.POST:
            context["resend"] = True
        return context

    def form_valid(self, form):
        self.send_email(form.cleaned_data["email"])
        response_kwargs = {
            "request": self.request,
            "template": self.template_name_sent,
            "context": self.get_context_data(form=form)
        }
        return self.response_class(**response_kwargs)

    def send_email(self, email):
        User = get_user_model()
        protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
        current_site = get_current_site(self.request)
        email_qs = EmailAddress.objects.filter(email__iexact=email)
        for user in User.objects.filter(pk__in=email_qs.values("user")):
            uid = int_to_base36(user.id)
            token = self.make_token(user)
            password_reset_url = "{0}://{1}{2}".format(
                protocol,
                current_site.domain,
                reverse("account_password_reset_token", kwargs=dict(uidb36=uid, token=token))
            )
            ctx = {
                "user": user,
                "current_site": current_site,
                "password_reset_url": password_reset_url,
            }
            hookset.send_password_reset_email([user.email], ctx)

    def make_token(self, user):
        return self.token_generator.make_token(user)


class PasswordResetTokenView(FormView):

    template_name = "account/password_reset_token.html"
    template_name_fail = "account/password_reset_token_fail.html"
    form_class = PasswordResetTokenForm
    token_generator = default_token_generator
    redirect_field_name = "next"
    messages = {
        "password_changed": {
            "level": messages.SUCCESS,
            "text": _("Password successfully changed.")
        },
    }

    def get(self, request, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ctx = self.get_context_data(form=form)
        if not self.check_token(self.get_user(), self.kwargs["token"]):
            return self.token_fail()
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            "uidb36": self.kwargs["uidb36"],
            "token": self.kwargs["token"],
            "redirect_field_name": redirect_field_name,
            "redirect_field_value": self.request.REQUEST.get(redirect_field_name, ""),
        })
        return ctx

    def change_password(self, form):
        user = self.get_user()
        user.set_password(form.cleaned_data["password"])
        user.save()

    def after_change_password(self):
        user = self.get_user()
        signals.password_changed.send(sender=PasswordResetTokenView, user=user)
        if self.messages.get("password_changed"):
            messages.add_message(
                self.request,
                self.messages["password_changed"]["level"],
                self.messages["password_changed"]["text"]
            )

    def form_valid(self, form):
        self.change_password(form)
        self.after_change_password()
        return redirect(self.get_success_url())

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def get_success_url(self, fallback_url=None, **kwargs):
        if fallback_url is None:
            fallback_url = settings.ACCOUNT_PASSWORD_RESET_REDIRECT_URL
        kwargs.setdefault("redirect_field_name", self.get_redirect_field_name())
        return default_redirect(self.request, fallback_url, **kwargs)

    def get_user(self):
        try:
            uid_int = base36_to_int(self.kwargs["uidb36"])
        except ValueError:
            raise Http404()
        return get_object_or_404(get_user_model(), id=uid_int)

    def check_token(self, user, token):
        return self.token_generator.check_token(user, token)

    def token_fail(self):
        response_kwargs = {
            "request": self.request,
            "template": self.template_name_fail,
            "context": self.get_context_data()
        }
        return self.response_class(**response_kwargs)


class SettingsView(LoginRequiredMixin, FormView):

    template_name = "account/settings.html"
    form_class = SettingsForm
    redirect_field_name = "next"
    messages = {
        "settings_updated": {
            "level": messages.SUCCESS,
            "text": _("Account settings updated.")
        },
    }

    def get_form_class(self):
        # @@@ django: this is a workaround to not having a dedicated method
        # to initialize self with a request in a known good state (of course
        # this only works with a FormView)
        self.primary_email_address = EmailAddress.objects.get_primary(self.request.user)
        return super(SettingsView, self).get_form_class()

    def get_initial(self):
        initial = super(SettingsView, self).get_initial()
        if self.primary_email_address:
            initial["email"] = self.primary_email_address.email
        initial["timezone"] = self.request.user.account.timezone
        initial["language"] = self.request.user.account.language
        return initial

    def form_valid(self, form):
        self.update_settings(form)
        if self.messages.get("settings_updated"):
            messages.add_message(
                self.request,
                self.messages["settings_updated"]["level"],
                self.messages["settings_updated"]["text"]
            )
        return redirect(self.get_success_url())

    def update_settings(self, form):
        self.update_email(form)
        self.update_account(form)

    def update_email(self, form, confirm=None):
        user = self.request.user
        if confirm is None:
            confirm = settings.ACCOUNT_EMAIL_CONFIRMATION_EMAIL
        # @@@ handle multiple emails per user
        email = form.cleaned_data["email"].strip()
        if not self.primary_email_address:
            user.email = email
            EmailAddress.objects.add_email(self.request.user, email, primary=True, confirm=confirm)
            user.save()
        else:
            if email != self.primary_email_address.email:
                self.primary_email_address.change(email, confirm=confirm)

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            "redirect_field_name": redirect_field_name,
            "redirect_field_value": self.request.REQUEST.get(redirect_field_name, ""),
        })
        return ctx

    def update_account(self, form):
        fields = {}
        if "timezone" in form.cleaned_data:
            fields["timezone"] = form.cleaned_data["timezone"]
        if "language" in form.cleaned_data:
            fields["language"] = form.cleaned_data["language"]
        if fields:
            account = self.request.user.account
            for k, v in fields.items():
                setattr(account, k, v)
            account.save()

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def get_success_url(self, fallback_url=None, **kwargs):
        if fallback_url is None:
            fallback_url = settings.ACCOUNT_SETTINGS_REDIRECT_URL
        kwargs.setdefault("redirect_field_name", self.get_redirect_field_name())
        return default_redirect(self.request, fallback_url, **kwargs)


class DeleteView(LogoutView):

    template_name = "account/delete.html"
    messages = {
        "account_deleted": {
            "level": messages.WARNING,
            "text": _("Your account is now inactive and your data will be expunged in the next {expunge_hours} hours.")
        },
    }

    def post(self, *args, **kwargs):
        AccountDeletion.mark(self.request.user)
        auth.logout(self.request)
        messages.add_message(
            self.request,
            self.messages["account_deleted"]["level"],
            self.messages["account_deleted"]["text"].format(**{
                "expunge_hours": settings.ACCOUNT_DELETION_EXPUNGE_HOURS,
            })
        )
        return redirect(self.get_redirect_url())

    def get_context_data(self, **kwargs):
        ctx = super(DeleteView, self).get_context_data()
        ctx.update(kwargs)
        ctx["ACCOUNT_DELETION_EXPUNGE_HOURS"] = settings.ACCOUNT_DELETION_EXPUNGE_HOURS
        return ctx

########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals

import os
import sys


extensions = []
templates_path = []
source_suffix = ".rst"
master_doc = "index"
project = "django-user-accounts"
copyright_holder = "James Tauber and contributors"
copyright = "2013, {0}",format(copyright_holder)
exclude_patterns = ["_build"]
pygments_style = "sphinx"
html_theme = "default"
htmlhelp_basename = "{0}doc".format(project)
latex_documents = [
  ("index", "{0}.tex".format(project), "{0} Documentation".format(project),
   "Pinax", "manual"),
]
man_pages = [
    ("index", project, "{0} Documentation".format(project),
     ["Pinax"], 1)
]

sys.path.insert(0, os.pardir)
m = __import__("account")

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = runtests
import os
import sys

from django.conf import settings


settings.configure(
    DEBUG=True,
    USE_TZ=True,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
        }
    },
    ROOT_URLCONF="account.urls",
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "django.contrib.messages",
        "account",
    ],
    MIDDLEWARE_CLASSES=[
        "django.contrib.messages.middleware.MessageMiddleware",
    ],
    SITE_ID=1,
    TEMPLATE_DIRS=[
        os.path.abspath(os.path.join(os.path.dirname(__file__), "account", "tests", "templates")),
    ]
)

from django_nose import NoseTestSuiteRunner

test_runner = NoseTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(["account"])

if failures:
    sys.exit(failures)

########NEW FILE########
