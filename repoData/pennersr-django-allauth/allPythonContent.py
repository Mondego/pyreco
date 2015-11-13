__FILENAME__ = adapter
import warnings
import json

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.contrib import messages

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from ..utils import (import_attribute, get_user_model,
                     generate_unique_username,
                     resolve_url)

from . import app_settings


class DefaultAccountAdapter(object):

    def stash_verified_email(self, request, email):
        request.session['account_verified_email'] = email

    def unstash_verified_email(self, request):
        ret = request.session.get('account_verified_email')
        request.session['account_verified_email'] = None
        return ret

    def is_email_verified(self, request, email):
        """
        Checks whether or not the email address is already verified
        beyond allauth scope, for example, by having accepted an
        invitation before signing up.
        """
        ret = False
        verified_email = request.session.get('account_verified_email')
        if verified_email:
            ret = verified_email.lower() == email.lower()
        return ret

    def format_email_subject(self, subject):
        prefix = app_settings.EMAIL_SUBJECT_PREFIX
        if prefix is None:
            site = Site.objects.get_current()
            prefix = u"[{name}] ".format(name=site.name)
        return prefix + force_text(subject)

    def render_mail(self, template_prefix, email, context):
        """
        Renders an e-mail to `email`.  `template_prefix` identifies the
        e-mail that is to be sent, e.g. "account/email/email_confirmation"
        """
        subject = render_to_string('{0}_subject.txt'.format(template_prefix),
                                   context)
        # remove superfluous line breaks
        subject = " ".join(subject.splitlines()).strip()
        subject = self.format_email_subject(subject)

        bodies = {}
        for ext in ['html', 'txt']:
            try:
                template_name = '{0}_message.{1}'.format(template_prefix, ext)
                bodies[ext] = render_to_string(template_name,
                                               context).strip()
            except TemplateDoesNotExist:
                if ext == 'txt' and not bodies:
                    # We need at least one body
                    raise
        if 'txt' in bodies:
            msg = EmailMultiAlternatives(subject,
                                         bodies['txt'],
                                         settings.DEFAULT_FROM_EMAIL,
                                         [email])
            if 'html' in bodies:
                msg.attach_alternative(bodies['html'], 'text/html')
        else:
            msg = EmailMessage(subject,
                               bodies['html'],
                               settings.DEFAULT_FROM_EMAIL,
                               [email])
            msg.content_subtype = 'html'  # Main content is now text/html
        return msg

    def send_mail(self, template_prefix, email, context):
        msg = self.render_mail(template_prefix, email, context)
        msg.send()

    def get_login_redirect_url(self, request):
        """
        Returns the default URL to redirect to after logging in.  Note
        that URLs passed explicitly (e.g. by passing along a `next`
        GET parameter) take precedence over the value returned here.
        """
        assert request.user.is_authenticated()
        url = getattr(settings, "LOGIN_REDIRECT_URLNAME", None)
        if url:
            warnings.warn("LOGIN_REDIRECT_URLNAME is deprecated, simply"
                          " use LOGIN_REDIRECT_URL with a URL name",
                          DeprecationWarning)
        else:
            url = settings.LOGIN_REDIRECT_URL
        return resolve_url(url)

    def get_logout_redirect_url(self, request):
        """
        Returns the URL to redriect to after the user logs out. Note that
        this method is also invoked if you attempt to log out while no users
        is logged in. Therefore, request.user is not guaranteed to be an
        authenticated user.
        """
        return resolve_url(app_settings.LOGOUT_REDIRECT_URL)

    def get_email_confirmation_redirect_url(self, request):
        """
        The URL to return to after successful e-mail confirmation.
        """
        if request.user.is_authenticated():
            if app_settings.EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL:
                return  \
                    app_settings.EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL
            else:
                return self.get_login_redirect_url(request)
        else:
            return app_settings.EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL

    def is_open_for_signup(self, request):
        """
        Checks whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse
        """
        return True

    def new_user(self, request):
        """
        Instantiates a new User instance.
        """
        user = get_user_model()()
        return user

    def populate_username(self, request, user):
        """
        Fills in a valid username, if required and missing.  If the
        username is already present it is assumed to be valid
        (unique).
        """
        from .utils import user_username, user_email, user_field
        first_name = user_field(user, 'first_name')
        last_name = user_field(user, 'last_name')
        email = user_email(user)
        username = user_username(user)
        if app_settings.USER_MODEL_USERNAME_FIELD:
            user_username(user,
                          username
                          or generate_unique_username([first_name,
                                                       last_name,
                                                       email,
                                                       'user']))

    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the
        signup form.
        """
        from .utils import user_username, user_email, user_field

        data = form.cleaned_data
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        username = data.get('username')
        user_email(user, email)
        user_username(user, username)
        user_field(user, 'first_name', first_name or '')
        user_field(user, 'last_name', last_name or '')
        if 'password1' in data:
            user.set_password(data["password1"])
        else:
            user.set_unusable_password()
        self.populate_username(request, user)
        if commit:
            # Ability not to commit makes it easier to derive from
            # this adapter by adding
            user.save()
        return user

    def clean_username(self, username):
        """
        Validates the username. You can hook into this if you want to
        (dynamically) restrict what usernames can be chosen.
        """
        from django.contrib.auth.forms import UserCreationForm
        USERNAME_REGEX = UserCreationForm().fields['username'].regex
        if not USERNAME_REGEX.match(username):
            raise forms.ValidationError(_("Usernames can only contain "
                                          "letters, digits and @/./+/-/_."))

        # TODO: Add regexp support to USERNAME_BLACKLIST
        if username in app_settings.USERNAME_BLACKLIST:
            raise forms.ValidationError(_("Username can not be used. "
                                          "Please use other username."))
        username_field = app_settings.USER_MODEL_USERNAME_FIELD
        assert username_field
        user_model = get_user_model()
        try:
            query = {username_field + '__iexact': username}
            user_model.objects.get(**query)
        except user_model.DoesNotExist:
            return username
        raise forms.ValidationError(_("This username is already taken. Please "
                                      "choose another."))

    def clean_email(self, email):
        """
        Validates an email value. You can hook into this if you want to
        (dynamically) restrict what email addresses can be chosen.
        """
        return email

    def add_message(self, request, level, message_template,
                    message_context={}, extra_tags=''):
        """
        Wrapper of `django.contrib.messages.add_message`, that reads
        the message text from a template.
        """
        if 'django.contrib.messages' in settings.INSTALLED_APPS:
            try:
                message = render_to_string(message_template,
                                           message_context).strip()
                if message:
                    messages.add_message(request, level, message,
                                         extra_tags=extra_tags)
            except TemplateDoesNotExist:
                pass

    def ajax_response(self, request, response, redirect_to=None, form=None):
        data = {}
        if redirect_to:
            status = 200
            data['location'] = redirect_to
        if form:
            if form.is_valid():
                status = 200
            else:
                status = 400
                data['form_errors'] = form._errors
            if hasattr(response, 'render'):
                response.render()
            data['html'] = response.content.decode('utf8')
        return HttpResponse(json.dumps(data),
                            status=status,
                            content_type='application/json')

    def login(self, request, user):
        from django.contrib.auth import login
        # HACK: This is not nice. The proper Django way is to use an
        # authentication backend
        if not hasattr(user, 'backend'):
            user.backend \
                = "allauth.account.auth_backends.AuthenticationBackend"
        login(request, user)

    def confirm_email(self, request, email_address):
        """
        Marks the email address as confirmed on the db
        """
        email_address.verified = True
        email_address.set_as_primary(conditional=True)
        email_address.save()

    def set_password(self, user, password):
        user.set_password(password)
        user.save()


def get_adapter():
    return import_attribute(app_settings.ADAPTER)()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from .models import EmailConfirmation, EmailAddress
from . import app_settings
from ..utils import get_user_model

User = get_user_model()

class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'primary', 'verified')
    list_filter = ('primary', 'verified')
    search_fields = ['email'] + list(map(lambda a: 'user__' + a,
                                    filter(lambda a: a and hasattr(User(), a),
                                           [app_settings.USER_MODEL_USERNAME_FIELD,
                                            'first_name',
                                            'last_name'])))
    raw_id_fields = ('user',)

class EmailConfirmationAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'created', 'sent', 'key')
    list_filter = ('sent',)
    raw_id_fields = ('email_address',)


admin.site.register(EmailConfirmation, EmailConfirmationAdmin)
admin.site.register(EmailAddress, EmailAddressAdmin)

########NEW FILE########
__FILENAME__ = apps
#  require django >= 1.7
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AccountConfig(AppConfig):
    name = 'allauth.account'
    verbose_name = _('Accounts')

########NEW FILE########
__FILENAME__ = app_settings
class AppSettings(object):

    class AuthenticationMethod:
        USERNAME = 'username'
        EMAIL = 'email'
        USERNAME_EMAIL = 'username_email'

    class EmailVerificationMethod:
        # After signing up, keep the user account inactive until the email
        # address is verified
        MANDATORY = 'mandatory'
        # Allow login with unverified e-mail (e-mail verification is
        # still sent)
        OPTIONAL = 'optional'
        # Don't send e-mail verification mails during signup
        NONE = 'none'

    def __init__(self, prefix):
        self.prefix = prefix
        # If login is by email, email must be required
        assert (not self.AUTHENTICATION_METHOD
                == self.AuthenticationMethod.EMAIL) or self.EMAIL_REQUIRED
        # If login includes email, login must be unique
        assert (self.AUTHENTICATION_METHOD
                == self.AuthenticationMethod.USERNAME) or self.UNIQUE_EMAIL
        assert (self.EMAIL_VERIFICATION
                != self.EmailVerificationMethod.MANDATORY) \
            or self.EMAIL_REQUIRED
        if not self.USER_MODEL_USERNAME_FIELD:
            assert not self.USERNAME_REQUIRED
            assert self.AUTHENTICATION_METHOD \
                not in (self.AuthenticationMethod.USERNAME,
                        self.AuthenticationMethod.USERNAME_EMAIL)

    def _setting(self, name, dflt):
        from django.conf import settings
        getter = getattr(settings,
                         'ALLAUTH_SETTING_GETTER',
                         lambda name, dflt: getattr(settings, name, dflt))
        return getter(self.prefix + name, dflt)

    @property
    def DEFAULT_HTTP_PROTOCOL(self):
        return self._setting("DEFAULT_HTTP_PROTOCOL", "http")

    @property
    def EMAIL_CONFIRMATION_EXPIRE_DAYS(self):
        """
        Determines the expiration date of e-mail confirmation mails (#
        of days)
        """
        from django.conf import settings
        return self._setting("EMAIL_CONFIRMATION_EXPIRE_DAYS",
                             getattr(settings, "EMAIL_CONFIRMATION_DAYS", 3))

    @property
    def EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL(self):
        """
        The URL to redirect to after a successful e-mail confirmation, in
        case of an authenticated user
        """
        return self._setting("EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL",
                             None)

    @property
    def EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL(self):
        """
        The URL to redirect to after a successful e-mail confirmation, in
        case no user is logged in
        """
        from django.conf import settings
        return self._setting("EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL",
                             settings.LOGIN_URL)

    @property
    def EMAIL_REQUIRED(self):
        """
        The user is required to hand over an e-mail address when signing up
        """
        return self._setting("EMAIL_REQUIRED", False)

    @property
    def EMAIL_VERIFICATION(self):
        """
        See e-mail verification method
        """
        ret = self._setting("EMAIL_VERIFICATION",
                            self.EmailVerificationMethod.OPTIONAL)
        # Deal with legacy (boolean based) setting
        if ret is True:
            ret = self.EmailVerificationMethod.MANDATORY
        elif ret is False:
            ret = self.EmailVerificationMethod.OPTIONAL
        return ret

    @property
    def AUTHENTICATION_METHOD(self):
        from django.conf import settings
        if hasattr(settings, "ACCOUNT_EMAIL_AUTHENTICATION"):
            import warnings
            warnings.warn("ACCOUNT_EMAIL_AUTHENTICATION is deprecated,"
                          " use ACCOUNT_AUTHENTICATION_METHOD",
                          DeprecationWarning)
            if getattr(settings, "ACCOUNT_EMAIL_AUTHENTICATION"):
                ret = self.AuthenticationMethod.EMAIL
            else:
                ret = self.AuthenticationMethod.USERNAME
        else:
            ret = self._setting("AUTHENTICATION_METHOD",
                                self.AuthenticationMethod.USERNAME)
        return ret

    @property
    def UNIQUE_EMAIL(self):
        """
        Enforce uniqueness of e-mail addresses
        """
        return self._setting("UNIQUE_EMAIL", True)

    @property
    def SIGNUP_PASSWORD_VERIFICATION(self):
        """
        Signup password verification
        """
        return self._setting("SIGNUP_PASSWORD_VERIFICATION", True)

    @property
    def PASSWORD_MIN_LENGTH(self):
        """
        Minimum password Length
        """
        return self._setting("PASSWORD_MIN_LENGTH", 6)

    @property
    def EMAIL_SUBJECT_PREFIX(self):
        """
        Subject-line prefix to use for email messages sent
        """
        return self._setting("EMAIL_SUBJECT_PREFIX", None)

    @property
    def SIGNUP_FORM_CLASS(self):
        """
        Signup form
        """
        return self._setting("SIGNUP_FORM_CLASS", None)

    @property
    def USERNAME_REQUIRED(self):
        """
        The user is required to enter a username when signing up
        """
        return self._setting("USERNAME_REQUIRED", True)

    @property
    def USERNAME_MIN_LENGTH(self):
        """
        Minimum username Length
        """
        return self._setting("USERNAME_MIN_LENGTH", 1)

    @property
    def USERNAME_BLACKLIST(self):
        """
        List of usernames that are not allowed
        """
        return self._setting("USERNAME_BLACKLIST", [])

    @property
    def PASSWORD_INPUT_RENDER_VALUE(self):
        """
        render_value parameter as passed to PasswordInput fields
        """
        return self._setting("PASSWORD_INPUT_RENDER_VALUE", False)

    @property
    def ADAPTER(self):
        return self._setting('ADAPTER',
                             'allauth.account.adapter.DefaultAccountAdapter')

    @property
    def CONFIRM_EMAIL_ON_GET(self):
        return self._setting('CONFIRM_EMAIL_ON_GET', False)

    @property
    def LOGIN_ON_EMAIL_CONFIRMATION(self):
        """
        Autmatically log the user in once he confirmed his email address
        """
        return self._setting('LOGIN_ON_EMAIL_CONFIRMATION', True)

    @property
    def LOGOUT_REDIRECT_URL(self):
        return self._setting('LOGOUT_REDIRECT_URL', '/')

    @property
    def LOGOUT_ON_GET(self):
        return self._setting('LOGOUT_ON_GET', False)

    @property
    def USER_MODEL_USERNAME_FIELD(self):
        return self._setting('USER_MODEL_USERNAME_FIELD', 'username')

    @property
    def USER_MODEL_EMAIL_FIELD(self):
        return self._setting('USER_MODEL_EMAIL_FIELD', 'email')


# Ugly? Guido recommends this himself ...
# http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
import sys
app_settings = AppSettings('ACCOUNT_')
app_settings.__name__ = __name__
sys.modules[__name__] = app_settings

########NEW FILE########
__FILENAME__ = auth_backends
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from ..utils import get_user_model

from .app_settings import AuthenticationMethod
from . import app_settings

User = get_user_model()


class AuthenticationBackend(ModelBackend):

    def authenticate(self, **credentials):
        ret = None
        if app_settings.AUTHENTICATION_METHOD == AuthenticationMethod.EMAIL:
            ret = self._authenticate_by_email(**credentials)
        elif app_settings.AUTHENTICATION_METHOD \
                == AuthenticationMethod.USERNAME_EMAIL:
            ret = self._authenticate_by_email(**credentials)
            if not ret:
                ret = self._authenticate_by_username(**credentials)
        else:
            ret = self._authenticate_by_username(**credentials)
        return ret

    def _authenticate_by_username(self, **credentials):
        username_field = app_settings.USER_MODEL_USERNAME_FIELD
        username = credentials.get('username')
        password = credentials.get('password')
        if not username_field or username is None or password is None:
            return None
        try:
            # Username query is case insensitive
            query = {username_field+'__iexact': username}
            user = User.objects.get(**query)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def _authenticate_by_email(self, **credentials):
        # Even though allauth will pass along `email`, other apps may
        # not respect this setting. For example, when using
        # django-tastypie basic authentication, the login is always
        # passed as `username`.  So let's place nice with other apps
        # and use username as fallback
        email = credentials.get('email', credentials.get('username'))
        if email:
            users = User.objects.filter(Q(email__iexact=email)
                                        | Q(emailaddress__email__iexact=email))
            for user in users:
                if user.check_password(credentials["password"]):
                    return user
        return None

########NEW FILE########
__FILENAME__ = context_processors
def account(request):
    # We used to have this due to the now removed
    # settings.CONTACT_EMAIL. Let's see if we need a context processor
    # in the future, otherwise, deprecate this context processor
    # completely.
    return { }

########NEW FILE########
__FILENAME__ = decorators
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render

from .models import EmailAddress

from .utils import send_email_confirmation


def verified_email_required(function=None,
                            login_url=None, 
                            redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Even when email verification is not mandatory during signup, there
    may be circumstances during which you really want to prevent
    unverified users to proceed. This decorator ensures the user is
    authenticated and has a verified email address. If the former is
    not the case then the behavior is identical to that of the
    standard `login_required` decorator. If the latter does not hold,
    email verification mails are automatically resend and the user is
    presented with a page informing him he needs to verify his email
    address.
    """
    def decorator(view_func):
        @login_required(redirect_field_name=redirect_field_name,
                        login_url=login_url)
        def _wrapped_view(request, *args, **kwargs):
            if not EmailAddress.objects.filter(user=request.user,
                                               verified=True).exists():
                send_email_confirmation(request, request.user)
                return render(request,
                              'account/verified_email_required.html')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
        
    if function:
        return decorator(function)
    return decorator

########NEW FILE########
__FILENAME__ = forms
from __future__ import absolute_import

import warnings

from django import forms
from django.core.urlresolvers import reverse
from django.core import exceptions
from django.db.models import Q
from django.utils.translation import pgettext, ugettext_lazy as _, ugettext
from django.utils.http import int_to_base36
from django.utils.importlib import import_module

from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site

from ..utils import (email_address_exists, get_user_model,
                     set_form_field_order)

from .models import EmailAddress
from .utils import perform_login, setup_user_email
from .app_settings import AuthenticationMethod
from . import app_settings
from .adapter import get_adapter

User = get_user_model()


class PasswordField(forms.CharField):

    def __init__(self, *args, **kwargs):
        render_value = kwargs.pop('render_value',
                                  app_settings.PASSWORD_INPUT_RENDER_VALUE)
        kwargs['widget'] = forms.PasswordInput(render_value=render_value,
                                               attrs={'placeholder':
                                                      _('Password')})
        super(PasswordField, self).__init__(*args, **kwargs)


class SetPasswordField(PasswordField):

    def clean(self, value):
        value = super(SetPasswordField, self).clean(value)
        min_length = app_settings.PASSWORD_MIN_LENGTH
        if len(value) < min_length:
            raise forms.ValidationError(_("Password must be a minimum of {0} "
                                          "characters.").format(min_length))
        return value


class LoginForm(forms.Form):

    password = PasswordField(label=_("Password"))
    remember = forms.BooleanField(label=_("Remember Me"),
                                  required=False)

    user = None

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        if app_settings.AUTHENTICATION_METHOD == AuthenticationMethod.EMAIL:
            login_widget = forms.TextInput(attrs={'type': 'email',
                                                  'placeholder':
                                                  _('E-mail address'),
                                                  'autofocus': 'autofocus'})
            login_field = forms.EmailField(label=_("E-mail"),
                                           widget=login_widget)
        elif app_settings.AUTHENTICATION_METHOD \
                == AuthenticationMethod.USERNAME:
            login_widget = forms.TextInput(attrs={'placeholder':
                                                  _('Username'),
                                                  'autofocus': 'autofocus'})
            login_field = forms.CharField(label=_("Username"),
                                          widget=login_widget,
                                          max_length=30)
        else:
            assert app_settings.AUTHENTICATION_METHOD \
                == AuthenticationMethod.USERNAME_EMAIL
            login_widget = forms.TextInput(attrs={'placeholder':
                                                  _('Username or e-mail'),
                                                  'autofocus': 'autofocus'})
            login_field = forms.CharField(label=pgettext("field label",
                                                         "Login"),
                                          widget=login_widget)
        self.fields["login"] = login_field
        set_form_field_order(self,  ["login", "password", "remember"])

    def user_credentials(self):
        """
        Provides the credentials required to authenticate the user for
        login.
        """
        credentials = {}
        login = self.cleaned_data["login"]
        if app_settings.AUTHENTICATION_METHOD == AuthenticationMethod.EMAIL:
            credentials["email"] = login
        elif (app_settings.AUTHENTICATION_METHOD
              == AuthenticationMethod.USERNAME):
            credentials["username"] = login
        else:
            if "@" in login and "." in login:
                credentials["email"] = login
            credentials["username"] = login
        credentials["password"] = self.cleaned_data["password"]
        return credentials

    def clean_login(self):
        login = self.cleaned_data['login']
        return login.strip()

    def clean(self):
        if self._errors:
            return
        user = authenticate(**self.user_credentials())
        if user:
            if user.is_active:
                self.user = user
            else:
                raise forms.ValidationError(_("This account is currently"
                                              " inactive."))
        else:
            if app_settings.AUTHENTICATION_METHOD \
                    == AuthenticationMethod.EMAIL:
                error = _("The e-mail address and/or password you specified"
                          " are not correct.")
            elif app_settings.AUTHENTICATION_METHOD \
                    == AuthenticationMethod.USERNAME:
                error = _("The username and/or password you specified are"
                          " not correct.")
            else:
                error = _("The login and/or password you specified are not"
                          " correct.")
            raise forms.ValidationError(error)
        return self.cleaned_data

    def login(self, request, redirect_url=None):
        ret = perform_login(request, self.user,
                            email_verification=app_settings.EMAIL_VERIFICATION,
                            redirect_url=redirect_url)
        if self.cleaned_data["remember"]:
            request.session.set_expiry(60 * 60 * 24 * 7 * 3)
        else:
            request.session.set_expiry(0)
        return ret


class _DummyCustomSignupForm(forms.Form):

    def signup(self, request, user):
        """
        Invoked at signup time to complete the signup of the user.
        """
        pass


def _base_signup_form_class():
    """
    Currently, we inherit from the custom form, if any. This is all
    not very elegant, though it serves a purpose:

    - There are two signup forms: one for local accounts, and one for
      social accounts
    - Both share a common base (BaseSignupForm)

    - Given the above, how to put in a custom signup form? Which form
      would your custom form derive from, the local or the social one?
    """
    if not app_settings.SIGNUP_FORM_CLASS:
        return _DummyCustomSignupForm
    try:
        fc_module, fc_classname = app_settings.SIGNUP_FORM_CLASS.rsplit('.', 1)
    except ValueError:
        raise exceptions.ImproperlyConfigured('%s does not point to a form'
                                              ' class'
                                              % app_settings.SIGNUP_FORM_CLASS)
    try:
        mod = import_module(fc_module)
    except ImportError as e:
        raise exceptions.ImproperlyConfigured('Error importing form class %s:'
                                              ' "%s"' % (fc_module, e))
    try:
        fc_class = getattr(mod, fc_classname)
    except AttributeError:
        raise exceptions.ImproperlyConfigured('Module "%s" does not define a'
                                              ' "%s" class' % (fc_module,
                                                               fc_classname))
    if not hasattr(fc_class, 'signup'):
        if hasattr(fc_class, 'save'):
            warnings.warn("The custom signup form must offer"
                          " a `def signup(self, request, user)` method",
                          DeprecationWarning)
        else:
            raise exceptions.ImproperlyConfigured(
                'The custom signup form must implement a "signup" method')
    return fc_class


class BaseSignupForm(_base_signup_form_class()):
    username = forms.CharField(label=_("Username"),
                               max_length=30,
                               min_length=app_settings.USERNAME_MIN_LENGTH,
                               widget=forms.TextInput(
                                   attrs={'placeholder':
                                          _('Username'),
                                          'autofocus': 'autofocus'}))
    email = forms.EmailField(widget=forms.TextInput(attrs=
                                                    {'type': 'email',
                                                     'placeholder':
                                                     _('E-mail address')}))

    def __init__(self, *args, **kwargs):
        email_required = kwargs.pop('email_required',
                                    app_settings.EMAIL_REQUIRED)
        self.username_required = kwargs.pop('username_required',
                                            app_settings.USERNAME_REQUIRED)
        super(BaseSignupForm, self).__init__(*args, **kwargs)
        # field order may contain additional fields from our base class,
        # so take proper care when reordering...
        field_order = ['email', 'username']
        merged_field_order = list(self.fields.keys())
        if email_required:
            self.fields["email"].label = ugettext("E-mail")
            self.fields["email"].required = True
        else:
            self.fields["email"].label = ugettext("E-mail (optional)")
            self.fields["email"].required = False
            if self.username_required:
                field_order = ['username', 'email']

        # Merge our email and username fields in if they are not
        # currently in the order.  This is to allow others to
        # re-arrange email and username if they desire.  Go in reverse
        # so that we make sure the inserted items are always
        # prepended.
        for field in reversed(field_order):
            if not field in merged_field_order:
                merged_field_order.insert(0, field)
        set_form_field_order(self, merged_field_order)
        if not self.username_required:
            del self.fields["username"]

    def clean_username(self):
        value = self.cleaned_data["username"]
        value = get_adapter().clean_username(value)
        return value

    def clean_email(self):
        value = self.cleaned_data["email"]
        value = get_adapter().clean_email(value)
        if app_settings.UNIQUE_EMAIL:
            if value and email_address_exists(value):
                self.raise_duplicate_email_error()
        return value

    def raise_duplicate_email_error(self):
        raise forms.ValidationError(_("A user is already registered"
                                      " with this e-mail address."))

    def custom_signup(self, request, user):
        custom_form = super(BaseSignupForm, self)
        if hasattr(custom_form, 'signup') and callable(custom_form.signup):
            custom_form.signup(request, user)
        else:
            warnings.warn("The custom signup form must offer"
                          " a `def signup(self, request, user)` method",
                          DeprecationWarning)
            # Historically, it was called .save, but this is confusing
            # in case of ModelForm
            custom_form.save(user)


class SignupForm(BaseSignupForm):

    password1 = SetPasswordField(label=_("Password"))
    password2 = PasswordField(label=_("Password (again)"))
    confirmation_key = forms.CharField(max_length=40,
                                       required=False,
                                       widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        if not app_settings.SIGNUP_PASSWORD_VERIFICATION:
            del self.fields["password2"]

    def clean(self):
        super(SignupForm, self).clean()
        if app_settings.SIGNUP_PASSWORD_VERIFICATION \
                and "password1" in self.cleaned_data \
                and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] \
                    != self.cleaned_data["password2"]:
                raise forms.ValidationError(_("You must type the same password"
                                              " each time."))
        return self.cleaned_data

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        # TODO: Move into adapter `save_user` ?
        setup_user_email(request, user, [])
        return user


class UserForm(forms.Form):

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(UserForm, self).__init__(*args, **kwargs)


class AddEmailForm(UserForm):

    email = forms.EmailField(label=_("E-mail"),
                             required=True,
                             widget=forms.TextInput(attrs={"type": "email",
                                                           "size": "30"}))

    def clean_email(self):
        value = self.cleaned_data["email"]
        value = get_adapter().clean_email(value)
        errors = {
            "this_account": _("This e-mail address is already associated"
                              " with this account."),
            "different_account": _("This e-mail address is already associated"
                                   " with another account."),
        }
        emails = EmailAddress.objects.filter(email__iexact=value)
        if emails.filter(user=self.user).exists():
            raise forms.ValidationError(errors["this_account"])
        if app_settings.UNIQUE_EMAIL:
            if emails.exclude(user=self.user).exists():
                raise forms.ValidationError(errors["different_account"])
        return value

    def save(self, request):
        return EmailAddress.objects.add_email(request,
                                              self.user,
                                              self.cleaned_data["email"],
                                              confirm=True)


class ChangePasswordForm(UserForm):

    oldpassword = PasswordField(label=_("Current Password"))
    password1 = SetPasswordField(label=_("New Password"))
    password2 = PasswordField(label=_("New Password (again)"))

    def clean_oldpassword(self):
        if not self.user.check_password(self.cleaned_data.get("oldpassword")):
            raise forms.ValidationError(_("Please type your current"
                                          " password."))
        return self.cleaned_data["oldpassword"]

    def clean_password2(self):
        if ("password1" in self.cleaned_data
                and "password2" in self.cleaned_data):
            if (self.cleaned_data["password1"]
                    != self.cleaned_data["password2"]):
                raise forms.ValidationError(_("You must type the same password"
                                              " each time."))
        return self.cleaned_data["password2"]

    def save(self):
        get_adapter().set_password(self.user, self.cleaned_data["password1"])


class SetPasswordForm(UserForm):

    password1 = SetPasswordField(label=_("Password"))
    password2 = PasswordField(label=_("Password (again)"))

    def clean_password2(self):
        if ("password1" in self.cleaned_data
                and "password2" in self.cleaned_data):
            if (self.cleaned_data["password1"]
                    != self.cleaned_data["password2"]):
                raise forms.ValidationError(_("You must type the same password"
                                              " each time."))
        return self.cleaned_data["password2"]

    def save(self):
        get_adapter().set_password(self.user, self.cleaned_data["password1"])


class ResetPasswordForm(forms.Form):

    email = forms.EmailField(
        label=_("E-mail"),
        required=True,
        widget=forms.TextInput(attrs={"type": "email", "size": "30"}))

    def clean_email(self):
        email = self.cleaned_data["email"]
        email = get_adapter().clean_email(email)
        self.users = User.objects \
            .filter(Q(email__iexact=email)
                    | Q(emailaddress__email__iexact=email)).distinct()
        if not self.users.exists():
            raise forms.ValidationError(_("The e-mail address is not assigned"
                                          " to any user account"))
        return self.cleaned_data["email"]

    def save(self, **kwargs):

        email = self.cleaned_data["email"]
        token_generator = kwargs.get("token_generator",
                                     default_token_generator)

        for user in self.users:

            temp_key = token_generator.make_token(user)

            # save it to the password reset model
            # password_reset = PasswordReset(user=user, temp_key=temp_key)
            # password_reset.save()

            current_site = Site.objects.get_current()

            # send the password reset email
            path = reverse("account_reset_password_from_key",
                           kwargs=dict(uidb36=int_to_base36(user.id),
                                       key=temp_key))
            url = '%s://%s%s' % (app_settings.DEFAULT_HTTP_PROTOCOL,
                                 current_site.domain,
                                 path)
            context = {"site": current_site,
                       "user": user,
                       "password_reset_url": url}
            get_adapter().send_mail('account/email/password_reset_key',
                                    email,
                                    context)
        return self.cleaned_data["email"]


class ResetPasswordKeyForm(forms.Form):

    password1 = SetPasswordField(label=_("New Password"))
    password2 = PasswordField(label=_("New Password (again)"))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.temp_key = kwargs.pop("temp_key", None)
        super(ResetPasswordKeyForm, self).__init__(*args, **kwargs)

    # FIXME: Inspecting other fields -> should be put in def clean(self) ?
    def clean_password2(self):
        if ("password1" in self.cleaned_data
                and "password2" in self.cleaned_data):
            if (self.cleaned_data["password1"]
                    != self.cleaned_data["password2"]):
                raise forms.ValidationError(_("You must type the same"
                                              " password each time."))
        return self.cleaned_data["password2"]

    def save(self):
        get_adapter().set_password(self.user, self.cleaned_data["password1"])

########NEW FILE########
__FILENAME__ = account_emailconfirmationmigration
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections

from allauth.account import app_settings
from allauth.account.models import EmailAddress, EmailConfirmation

class Command(BaseCommand):
    def handle(self, *args, **options):
        if False:
            EmailAddress.objects.all().delete()

        if EmailAddress.objects.all().exists():
            raise CommandError('New-style EmailAddress objects exist, please delete those first')

        self.migrate_email_address()
        self.migrate_email_confirmation()
        self.reset_sequences()

    def reset_sequences(self):
        connection = connections['default']
        cursor = connection.cursor()
        style = no_style()
        sequence_sql = connection.ops.sequence_reset_sql(style,
                                                         [EmailAddress,
                                                          EmailConfirmation])
        if sequence_sql:
            print("Resetting sequences")
            for line in sequence_sql:
                cursor.execute(line)


    def migrate_email_address(self):
        seen_emails = {}
        # Poor man's conflict handling: prefer latest (hence order by)
        for email_address in EmailAddress.objects.raw('SELECT * from emailconfirmation_emailaddress order by id desc'):
            if app_settings.UNIQUE_EMAIL and email_address.email in seen_emails:
                print('Duplicate e-mail address skipped: %s collides with %s' % (email_address, seen_emails[email_address.email]))
                continue
            seen_emails[email_address.email] = email_address
            email_address.save()

    def migrate_email_confirmation(self):
        seen_keys = set()
        for email_confirmation in EmailConfirmation.objects.raw('SELECT id, email_address_id, sent, confirmation_key as key from emailconfirmation_emailconfirmation'):
            email_confirmation.created = email_confirmation.sent
            if EmailAddress.objects.filter(id=email_confirmation.email_address_id).exists():
                if email_confirmation.key in seen_keys:
                    print('Could not migrate EmailConfirmation %d due to duplicate key' % email_confirmation.id)
                    continue
                seen_keys.add(email_confirmation.key)
                email_confirmation.save()
            else:
                print ('Could not migrate EmailConfirmation %d due to missing EmailAddress' % email_confirmation.id)

########NEW FILE########
__FILENAME__ = account_unsetmultipleprimaryemails
from django.core.management.base import BaseCommand
from django.db.models import Count

from allauth.account.utils import user_email
from allauth.utils import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in self.get_users_with_multiple_primary_email():
            self.unprimary_extra_primary_emails(user)

    def get_users_with_multiple_primary_email(self):
        user_pks = []
        for email_address_dict in EmailAddress.objects.filter(
                primary=True).values('user').annotate(
                            Count('user')).filter(user__count__gt=1):
            user_pks.append(email_address_dict['user'])
        return User.objects.filter(pk__in=user_pks)

    def unprimary_extra_primary_emails(self, user):
        primary_email_addresses = EmailAddress.objects.filter(
                user=user, primary=True)

        for primary_email_address in primary_email_addresses:
            if primary_email_address.email == user_email(user):
                break
        else:
            # Didn't find the main email addresses and break the for loop
            print ("WARNING: Multiple primary without a user.email match for"
                   "user pk %s; (tried: %s, using: %s)") % (
                                    user.pk,
                                    ", ".join([email_address.email
                                               for email_address
                                               in primary_email_addresses]),
                                    primary_email_address)

        primary_email_addresses.exclude(pk=primary_email_address.pk
                ).update(primary=False)




########NEW FILE########
__FILENAME__ = managers
from datetime import timedelta

from django.utils import timezone
from django.db import models, IntegrityError
from django.db.models import Q

from . import app_settings


class EmailAddressManager(models.Manager):

    def add_email(self, request, user, email, 
                  confirm=False, signup=False):
        try:
            email_address = self.get(user=user, email__iexact=email)
        except self.model.DoesNotExist:
            email_address = self.create(user=user, email=email)
            if confirm:
                email_address.send_confirmation(request,
                                                signup=signup)
        return email_address

    def get_primary(self, user):
        try:
            return self.get(user=user, primary=True)
        except self.model.DoesNotExist:
            return None

    def get_users_for(self, email):
        # this is a list rather than a generator because we probably want to
        # do a len() on it right away
        return [address.user for address in self.filter(verified=True,
                                                        email__iexact=email)]

    def fill_cache_for_user(self, user, addresses):
        """
        In a multi-db setup, inserting records and re-reading them later
        on may result in not being able to find newly inserted
        records. Therefore, we maintain a cache for the user so that
        we can avoid database access when we need to re-read..
        """
        user._emailaddress_cache = addresses

    def get_for_user(self, user, email):
        cache_key = '_emailaddress_cache'
        addresses = getattr(user, cache_key, None)
        if addresses is None:
            return self.get(user=user,
                            email__iexact=email)
        else:
            for address in addresses:
                if address.email.lower() == email.lower():
                    return address
            raise self.model.DoesNotExist()


class EmailConfirmationManager(models.Manager):

    def all_expired(self):
        return self.filter(self.expired_q())

    def all_valid(self):
        return self.exclude(self.expired_q())

    def expired_q(self):
        sent_threshold = timezone.now() \
            - timedelta(days=app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS)
        return Q(sent__lt=sent_threshold)

    def delete_expired_confirmations(self):
        self.all_expired().delete()

########NEW FILE########
__FILENAME__ = models
import datetime

from django.core.urlresolvers import reverse
from django.db import models
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib.sites.models import Site
from django.utils.encoding import python_2_unicode_compatible

from .. import app_settings as allauth_app_settings
from . import app_settings
from . import signals

from .utils import random_token, user_email
from .managers import EmailAddressManager, EmailConfirmationManager
from .adapter import get_adapter


@python_2_unicode_compatible
class EmailAddress(models.Model):

    user = models.ForeignKey(allauth_app_settings.USER_MODEL,
                             verbose_name=_('user'))
    email = models.EmailField(unique=app_settings.UNIQUE_EMAIL,
                              verbose_name=_('e-mail address'))
    verified = models.BooleanField(verbose_name=_('verified'), default=False)
    primary = models.BooleanField(verbose_name=_('primary'), default=False)

    objects = EmailAddressManager()

    class Meta:
        verbose_name = _("email address")
        verbose_name_plural = _("email addresses")
        if not app_settings.UNIQUE_EMAIL:
            unique_together = [("user", "email")]

    def __str__(self):
        return u"%s (%s)" % (self.email, self.user)

    def set_as_primary(self, conditional=False):
        old_primary = EmailAddress.objects.get_primary(self.user)
        if old_primary:
            if conditional:
                return False
            old_primary.primary = False
            old_primary.save()
        self.primary = True
        self.save()
        user_email(self.user, self.email)
        self.user.save()
        return True

    def send_confirmation(self, request, signup=False):
        confirmation = EmailConfirmation.create(self)
        confirmation.send(request, signup=signup)
        return confirmation

    def change(self, request, new_email, confirm=True):
        """
        Given a new email address, change self and re-confirm.
        """
        with transaction.commit_on_success():
            user_email(self.user, new_email)
            self.user.save()
            self.email = new_email
            self.verified = False
            self.save()
            if confirm:
                self.send_confirmation(request)


@python_2_unicode_compatible
class EmailConfirmation(models.Model):

    email_address = models.ForeignKey(EmailAddress,
                                      verbose_name=_('e-mail address'))
    created = models.DateTimeField(verbose_name=_('created'),
                                   default=timezone.now)
    sent = models.DateTimeField(verbose_name=_('sent'), null=True)
    key = models.CharField(verbose_name=_('key'), max_length=64, unique=True)

    objects = EmailConfirmationManager()

    class Meta:
        verbose_name = _("email confirmation")
        verbose_name_plural = _("email confirmations")

    def __str__(self):
        return u"confirmation for %s" % self.email_address

    @classmethod
    def create(cls, email_address):
        key = random_token([email_address.email])
        return cls._default_manager.create(email_address=email_address,
                                           key=key)

    def key_expired(self):
        expiration_date = self.sent \
            + datetime.timedelta(days=app_settings
                                 .EMAIL_CONFIRMATION_EXPIRE_DAYS)
        return expiration_date <= timezone.now()
    key_expired.boolean = True

    def confirm(self, request):
        if not self.key_expired() and not self.email_address.verified:
            email_address = self.email_address
            get_adapter().confirm_email(request, email_address)
            signals.email_confirmed.send(sender=self.__class__,
                                         request=request,
                                         email_address=email_address)
            return email_address

    def send(self, request, signup=False, **kwargs):
        current_site = kwargs["site"] if "site" in kwargs \
            else Site.objects.get_current()
        activate_url = reverse("account_confirm_email", args=[self.key])
        activate_url = request.build_absolute_uri(activate_url)
        ctx = {
            "user": self.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "key": self.key,
        }
        if signup:
            email_template = 'account/email/email_confirmation_signup'
        else:
            email_template = 'account/email/email_confirmation'
        get_adapter().send_mail(email_template,
                                self.email_address.email,
                                ctx)
        self.sent = timezone.now()
        self.save()
        signals.email_confirmation_sent.send(sender=self.__class__,
                                             confirmation=self)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

user_logged_in = Signal(providing_args=["request", "user"])

# Typically followed by `user_logged_in` (unless, e-mail verification kicks in)
user_signed_up = Signal(providing_args=["request", "user"])

password_set = Signal(providing_args=["request", "user"])
password_changed = Signal(providing_args=["request", "user"])
password_reset = Signal(providing_args=["request", "user"])

email_confirmed = Signal(providing_args=["email_address"])
email_confirmation_sent = Signal(providing_args=["confirmation"])

email_changed = Signal(providing_args=["request", "user",
                            "from_email_address", "to_email_address"])
email_added = Signal(providing_args=["request", "user", "email_address"])
email_removed = Signal(providing_args=["request", "user", "email_address"])

########NEW FILE########
__FILENAME__ = account
from django import template

from allauth.account.utils import user_display

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
        return display


@register.tag(name="user_display")
def do_user_display(parser, token):
    """
    Example usage::
    
        {% user_display user %}
    
    or if you need to use in a {% blocktrans %}::
    
        {% user_display user as user_display %}
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
        raise template.TemplateSyntaxError("'%s' takes either two or four arguments" % bits[0])
    
    return UserDisplayNode(user, as_var)

########NEW FILE########
__FILENAME__ = account_tags
import warnings

warnings.warn("{% load account_tags %} is deprecated, use {% load account %}",
              DeprecationWarning)

from account import *

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import
import json

from datetime import timedelta

from django.utils.timezone import now
from django.test.utils import override_settings
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.core import mail
from django.contrib.sites.models import Site
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser

from allauth.account.forms import BaseSignupForm
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.utils import get_user_model

from . import app_settings

from .adapter import get_adapter

User = get_user_model()


@override_settings(
    ACCOUNT_DEFAULT_HTTP_PROTOCOL='https',
    ACCOUNT_EMAIL_VERIFICATION=app_settings.EmailVerificationMethod.MANDATORY,
    ACCOUNT_AUTHENTICATION_METHOD=app_settings.AuthenticationMethod.USERNAME,
    ACCOUNT_SIGNUP_FORM_CLASS=None,
    ACCOUNT_EMAIL_SUBJECT_PREFIX=None,
    LOGIN_REDIRECT_URL='/accounts/profile/',
    ACCOUNT_ADAPTER='allauth.account.adapter.DefaultAccountAdapter',
    ACCOUNT_USERNAME_REQUIRED=True)
class AccountTests(TestCase):
    def setUp(self):
        if 'allauth.socialaccount' in settings.INSTALLED_APPS:
            # Otherwise ImproperlyConfigured exceptions may occur
            from ..socialaccount.models import SocialApp
            sa = SocialApp.objects.create(name='testfb',
                                          provider='facebook')
            sa.sites.add(Site.objects.get_current())

    @override_settings(
        ACCOUNT_AUTHENTICATION_METHOD=app_settings.AuthenticationMethod
        .USERNAME_EMAIL)
    def test_username_containing_at(self):
        user = User.objects.create(username='@raymond.penners')
        user.set_password('psst')
        user.save()
        EmailAddress.objects.create(user=user,
                                    email='raymond.penners@gmail.com',
                                    primary=True,
                                    verified=True)
        resp = self.client.post(reverse('account_login'),
                                {'login': '@raymond.penners',
                                 'password': 'psst'})
        self.assertEqual(resp['location'],
                         'http://testserver'+settings.LOGIN_REDIRECT_URL)

    def test_signup_same_email_verified_externally(self):
        user = self._test_signup_email_verified_externally('john@doe.com',
                                                           'john@doe.com')
        self.assertEqual(EmailAddress.objects.filter(user=user).count(),
                         1)
        EmailAddress.objects.get(verified=True,
                                 email='john@doe.com',
                                 user=user,
                                 primary=True)

    def test_signup_other_email_verified_externally(self):
        """
        John is invited on john@work.com, but signs up via john@home.com.
        E-mail verification is by-passed, his home e-mail address is
        used as a secondary.
        """
        user = self._test_signup_email_verified_externally('john@home.com',
                                                           'john@work.com')
        self.assertEqual(EmailAddress.objects.filter(user=user).count(),
                         2)
        EmailAddress.objects.get(verified=False,
                                 email='john@home.com',
                                 user=user,
                                 primary=False)
        EmailAddress.objects.get(verified=True,
                                 email='john@work.com',
                                 user=user,
                                 primary=True)

    def _test_signup_email_verified_externally(self, signup_email,
                                               verified_email):
        username = 'johndoe'
        request = RequestFactory().post(reverse('account_signup'),
                                        {'username': username,
                                         'email': signup_email,
                                         'password1': 'johndoe',
                                         'password2': 'johndoe'})
        # Fake stash_verified_email
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        SessionMiddleware().process_request(request)
        MessageMiddleware().process_request(request)
        request.user = AnonymousUser()
        request.session['account_verified_email'] = verified_email
        from .views import signup
        resp = signup(request)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['location'],
                         get_adapter().get_login_redirect_url(request))
        self.assertEqual(len(mail.outbox), 0)
        return User.objects.get(username=username)

    def _create_user_and_login(self):
        user = User.objects.create(username='john',
                                   is_active=True)
        user.set_password('doe')
        user.save()
        self.client.login(username='john', password='doe')
        return user

    def test_redirect_when_authenticated(self):
        self._create_user_and_login()
        c = self.client
        resp = c.get(reverse('account_login'))
        self.assertEqual(302, resp.status_code)
        self.assertEqual('http://testserver/accounts/profile/',
                         resp['location'])

    def test_password_set_redirect(self):
        resp = self._password_set_or_reset_redirect('account_set_password',
                                                    True)
        self.assertEqual(resp.status_code, 302)

    def test_password_reset_no_redirect(self):
        resp = self._password_set_or_reset_redirect('account_change_password',
                                                    True)
        self.assertEqual(resp.status_code, 200)

    def test_password_set_no_redirect(self):
        resp = self._password_set_or_reset_redirect('account_set_password',
                                                    False)
        self.assertEqual(resp.status_code, 200)

    def test_password_reset_redirect(self):
        resp = self._password_set_or_reset_redirect('account_change_password',
                                                    False)
        self.assertEqual(resp.status_code, 302)

    def _password_set_or_reset_redirect(self, urlname, usable_password):
        user = self._create_user_and_login()
        c = self.client
        if not usable_password:
            user.set_unusable_password()
            user.save()
        resp = c.get(reverse(urlname))
        return resp

    def test_password_forgotten_url_protocol(self):
        c = Client()
        user = User.objects.create(username='john',
                                   email='john@doe.org',
                                   is_active=True)
        user.set_password('doe')
        user.save()
        resp = c.post(reverse('account_reset_password'),
                      data={'email': 'john@doe.org'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['john@doe.org'])
        body = mail.outbox[0].body
        self.assertGreater(body.find('https://'), 0)
        url = body[body.find('/password/reset/'):].split()[0]
        resp = c.get(url)
        self.assertTemplateUsed(resp, 'account/password_reset_from_key.html')
        c.post(url, {'password1': 'newpass123',
                     'password2': 'newpass123'})
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.check_password('newpass123'))
        return resp

    def test_email_verification_mandatory(self):
        c = Client()
        # Signup
        resp = c.post(reverse('account_signup'),
                      {'username': 'johndoe',
                       'email': 'john@doe.com',
                       'password1': 'johndoe',
                       'password2': 'johndoe'},
                      follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mail.outbox[0].to, ['john@doe.com'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertTemplateUsed(resp,
                                'account/verification_sent.html')
        # Attempt to login, unverified
        for attempt in [1, 2]:
            resp = c.post(reverse('account_login'),
                          {'login': 'johndoe',
                           'password': 'johndoe'},
                          follow=True)
            # is_active is controlled by the admin to manually disable
            # users. I don't want this flag to flip automatically whenever
            # users verify their email adresses.
            self.assertTrue(User.objects.filter(username='johndoe',
                                                is_active=True).exists())
            self.assertTemplateUsed(resp,
                                    'account/verification_sent.html')
            # Attempt 1: no mail is sent due to cool-down ,
            # but there was already a mail in the outbox.
            self.assertEqual(len(mail.outbox), attempt)
            self.assertEqual(EmailConfirmation.objects
                             .filter(email_address__email=
                                     'john@doe.com').count(),
                             attempt)
            # Wait for cooldown
            EmailConfirmation.objects.update(sent=now()
                                             - timedelta(days=1))
        # Verify, and re-attempt to login.
        confirmation = EmailConfirmation \
            .objects \
            .filter(email_address__user__username='johndoe')[:1] \
            .get()
        resp = c.get(reverse('account_confirm_email',
                             args=[confirmation.key]))
        self.assertTemplateUsed(resp, 'account/email_confirm.html')
        c.post(reverse('account_confirm_email',
                       args=[confirmation.key]))
        resp = c.post(reverse('account_login'),
                      {'login': 'johndoe',
                       'password': 'johndoe'})
        self.assertEqual(resp['location'],
                         'http://testserver'+settings.LOGIN_REDIRECT_URL)

    def test_email_escaping(self):
        site = Site.objects.get_current()
        site.name = '<enc&"test>'
        site.save()
        u = User.objects.create(username='test',
                                email='foo@bar.com')
        request = RequestFactory().get('/')
        EmailAddress.objects.add_email(request, u, u.email, confirm=True)
        self.assertTrue(mail.outbox[0].subject[1:].startswith(site.name))

    def test_login_view(self):
        c = Client()
        c.get(reverse('account_login'))
        # TODO: Actually test something

    def test_ajax_login_fail(self):
        resp = self.client.post(reverse('account_login'),
                                {},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content.decode('utf8'))
        # TODO: Actually test something

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION=app_settings.EmailVerificationMethod
        .OPTIONAL,
        ACCOUNT_AUTHENTICATION_METHOD=app_settings.AuthenticationMethod
        .USERNAME)
    def test_ajax_login_success(self):
        user = User.objects.create(username='john',
                                   is_active=True)
        user.set_password('doe')
        user.save()
        resp = self.client.post(reverse('account_login'),
                                {'login': 'john',
                                 'password': 'doe'},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf8'))
        self.assertEqual(data['location'], '/accounts/profile/')

    def test_email_view(self):
        self._create_user_and_login()
        self.client.get(reverse('account_email'))
        # TODO: Actually test something

    @override_settings(ACCOUNT_LOGOUT_ON_GET=True)
    def test_logout_view_on_get(self):
        c, resp = self._logout_view('get')
        self.assertTemplateUsed(resp, 'account/messages/logged_out.txt')

    @override_settings(ACCOUNT_LOGOUT_ON_GET=False)
    def test_logout_view_on_post(self):
        c, resp = self._logout_view('get')
        self.assertTemplateUsed(resp, 'account/logout.html')
        resp = c.post(reverse('account_logout'))
        self.assertTemplateUsed(resp, 'account/messages/logged_out.txt')

    def _logout_view(self, method):
        c = Client()
        user = User.objects.create(username='john',
                                   is_active=True)
        user.set_password('doe')
        user.save()
        c = Client()
        c.login(username='john', password='doe')
        return c, getattr(c, method)(reverse('account_logout'))

    @override_settings(ACCOUNT_EMAIL_VERIFICATION=app_settings
                       .EmailVerificationMethod.OPTIONAL)
    def test_optional_email_verification(self):
        c = Client()
        # Signup
        c.get(reverse('account_signup'))
        resp = c.post(reverse('account_signup'),
                      {'username': 'johndoe',
                       'email': 'john@doe.com',
                       'password1': 'johndoe',
                       'password2': 'johndoe'})
        # Logged in
        self.assertEqual(resp['location'],
                         'http://testserver'+settings.LOGIN_REDIRECT_URL)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(mail.outbox[0].to, ['john@doe.com'])
        self.assertEqual(len(mail.outbox), 1)
        # Logout & login again
        c.logout()
        # Wait for cooldown
        EmailConfirmation.objects.update(sent=now() - timedelta(days=1))
        # Signup
        resp = c.post(reverse('account_login'),
                      {'login': 'johndoe',
                       'password': 'johndoe'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['location'],
                         'http://testserver'+settings.LOGIN_REDIRECT_URL)
        self.assertEqual(mail.outbox[0].to, ['john@doe.com'])
        # There was an issue that we sent out email confirmation mails
        # on each login in case of optional verification. Make sure
        # this is not the case:
        self.assertEqual(len(mail.outbox), 1)


class BaseSignupFormTests(TestCase):

    @override_settings(
        ACCOUNT_USERNAME_REQUIRED=True,
        ACCOUNT_USERNAME_BLACKLIST=['username'])
    def test_username_in_blacklist(self):
        data = {
            'username': 'username',
            'email': 'user@example.com',
        }
        form = BaseSignupForm(data, email_required=True)
        self.assertFalse(form.is_valid())

    @override_settings(
        ACCOUNT_USERNAME_REQUIRED=True,
        ACCOUNT_USERNAME_BLACKLIST=['username'])
    def test_username_not_in_blacklist(self):
        data = {
            'username': 'theusername',
            'email': 'user@example.com',
        }
        form = BaseSignupForm(data, email_required=True)
        self.assertTrue(form.is_valid())

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from . import views

urlpatterns = patterns(
    "",
    url(r"^signup/$", views.signup, name="account_signup"),
    url(r"^login/$", views.login, name="account_login"),
    url(r"^logout/$", views.logout, name="account_logout"),

    url(r"^password/change/$", views.password_change,
        name="account_change_password"),
    url(r"^password/set/$", views.password_set, name="account_set_password"),

    url(r"^inactive/$", views.account_inactive, name="account_inactive"),

    # E-mail
    url(r"^email/$", views.email, name="account_email"),
    url(r"^confirm-email/$", views.email_verification_sent,
        name="account_email_verification_sent"),
    url(r"^confirm-email/(?P<key>\w+)/$", views.confirm_email,
        name="account_confirm_email"),
    # Handle old redirects
    url(r"^confirm_email/(?P<key>\w+)/$",
        RedirectView.as_view(url='/accounts/confirm-email/%(key)s/')),

    # password reset
    url(r"^password/reset/$", views.password_reset,
        name="account_reset_password"),
    url(r"^password/reset/done/$", views.password_reset_done,
        name="account_reset_password_done"),
    url(r"^password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        views.password_reset_from_key,
        name="account_reset_password_from_key"),
    url(r"^password/reset/key/done/$", views.password_reset_from_key_done,
        name="account_reset_password_from_key_done"),
)

########NEW FILE########
__FILENAME__ = utils
import hashlib
import random

from datetime import timedelta
try:
    from django.utils.timezone import now
except ImportError:
    from datetime import datetime
    now = datetime.now

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.http import urlencode, is_safe_url
from django.utils.datastructures import SortedDict
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from ..utils import (import_callable, valid_email_or_none,
                     get_user_model)

from . import signals

from .app_settings import EmailVerificationMethod
from . import app_settings
from .adapter import get_adapter


def get_next_redirect_url(request, redirect_field_name="next"):
    """
    Returns the next URL to redirect to, if it was explicitly passed
    via the request.
    """
    redirect_to = request.REQUEST.get(redirect_field_name)
    if not is_safe_url(redirect_to):
        redirect_to = None
    return redirect_to


def get_login_redirect_url(request, url=None, redirect_field_name="next"):
    redirect_url \
        = (url
           or get_next_redirect_url(request,
                                    redirect_field_name=redirect_field_name)
           or get_adapter().get_login_redirect_url(request))
    return redirect_url

_user_display_callable = None


def default_user_display(user):
    if app_settings.USER_MODEL_USERNAME_FIELD:
        return getattr(user, app_settings.USER_MODEL_USERNAME_FIELD)
    else:
        return force_text(user)


def user_display(user):
    global _user_display_callable
    if not _user_display_callable:
        f = getattr(settings, "ACCOUNT_USER_DISPLAY",
                    default_user_display)
        _user_display_callable = import_callable(f)
    return _user_display_callable(user)


def user_field(user, field, *args):
    """
    Gets or sets (optional) user model fields. No-op if fields do not exist.
    """
    if field and hasattr(user, field):
        if args:
            # Setter
            v = args[0]
            if v:
                User = get_user_model()
                v = v[0:User._meta.get_field(field).max_length]
            setattr(user, field, v)
        else:
            # Getter
            return getattr(user, field)


def user_username(user, *args):
    return user_field(user, app_settings.USER_MODEL_USERNAME_FIELD, *args)


def user_email(user, *args):
    return user_field(user, app_settings.USER_MODEL_EMAIL_FIELD, *args)


def perform_login(request, user, email_verification,
                  redirect_url=None, signal_kwargs={},
                  signup=False):
    """
    Keyword arguments:

    signup -- Indicates whether or not sending the
    email is essential (during signup), or if it can be skipped (e.g. in
    case email verification is optional and we are only logging in).
    """
    from .models import EmailAddress
    has_verified_email = EmailAddress.objects.filter(user=user,
                                                     verified=True).exists()
    if email_verification == EmailVerificationMethod.NONE:
        pass
    elif email_verification == EmailVerificationMethod.OPTIONAL:
        # In case of OPTIONAL verification: send on signup.
        if not has_verified_email and signup:
            send_email_confirmation(request, user, signup=signup)
    elif email_verification == EmailVerificationMethod.MANDATORY:
        if not has_verified_email:
            send_email_confirmation(request, user, signup=signup)
            return HttpResponseRedirect(
                reverse('account_email_verification_sent'))
    # Local users are stopped due to form validation checking
    # is_active, yet, adapter methods could toy with is_active in a
    # `user_signed_up` signal. Furthermore, social users should be
    # stopped anyway.
    if not user.is_active:
        return HttpResponseRedirect(reverse('account_inactive'))
    get_adapter().login(request, user)
    signals.user_logged_in.send(sender=user.__class__,
                                request=request,
                                user=user,
                                **signal_kwargs)
    get_adapter().add_message(request,
                              messages.SUCCESS,
                              'account/messages/logged_in.txt',
                              {'user': user})

    return HttpResponseRedirect(get_login_redirect_url(request, redirect_url))


def complete_signup(request, user, email_verification, success_url,
                    signal_kwargs={}):
    signals.user_signed_up.send(sender=user.__class__,
                                request=request,
                                user=user,
                                **signal_kwargs)
    return perform_login(request, user,
                         email_verification=email_verification,
                         signup=True,
                         redirect_url=success_url,
                         signal_kwargs=signal_kwargs)


def cleanup_email_addresses(request, addresses):
    """
    Takes a list of EmailAddress instances and cleans it up, making
    sure only valid ones remain, without multiple primaries etc.

    Order is important: e.g. if multiple primary e-mail addresses
    exist, the first one encountered will be kept as primary.
    """
    from .models import EmailAddress
    adapter = get_adapter()
    # Let's group by `email`
    e2a = SortedDict()  # maps email to EmailAddress
    primary_addresses = []
    verified_addresses = []
    primary_verified_addresses = []
    for address in addresses:
        # Pick up only valid ones...
        email = valid_email_or_none(address.email)
        if not email:
            continue
        # ... and non-conflicting ones...
        if (app_settings.UNIQUE_EMAIL
                and EmailAddress.objects
                .filter(email__iexact=email)
                .exists()):
            continue
        a = e2a.get(email.lower())
        if a:
            a.primary = a.primary or address.primary
            a.verified = a.verified or address.verified
        else:
            a = address
            a.verified = a.verified or adapter.is_email_verified(request,
                                                                 a.email)
            e2a[email.lower()] = a
        if a.primary:
            primary_addresses.append(a)
            if a.verified:
                primary_verified_addresses.append(a)
        if a.verified:
            verified_addresses.append(a)
    # Now that we got things sorted out, let's assign a primary
    if primary_verified_addresses:
        primary_address = primary_verified_addresses[0]
    elif verified_addresses:
        # Pick any verified as primary
        primary_address = verified_addresses[0]
    elif primary_addresses:
        # Okay, let's pick primary then, even if unverified
        primary_address = primary_addresses[0]
    elif e2a:
        # Pick the first
        primary_address = e2a.keys()[0]
    else:
        # Empty
        primary_address = None
    # There can only be one primary
    for a in e2a.values():
        a.primary = primary_address.email.lower() == a.email.lower()
    return list(e2a.values()), primary_address


def setup_user_email(request, user, addresses):
    """
    Creates proper EmailAddress for the user that was just signed
    up. Only sets up, doesn't do any other handling such as sending
    out email confirmation mails etc.
    """
    from .models import EmailAddress

    assert EmailAddress.objects.filter(user=user).count() == 0
    priority_addresses = []
    # Is there a stashed e-mail?
    adapter = get_adapter()
    stashed_email = adapter.unstash_verified_email(request)
    if stashed_email:
        priority_addresses.append(EmailAddress(user=user,
                                               email=stashed_email,
                                               primary=True,
                                               verified=True))
    email = user_email(user)
    if email:
        priority_addresses.append(EmailAddress(user=user,
                                               email=email,
                                               primary=True,
                                               verified=False))
    addresses, primary = cleanup_email_addresses(request,
                                                 priority_addresses
                                                 + addresses)
    for a in addresses:
        a.user = user
        a.save()
    EmailAddress.objects.fill_cache_for_user(user, addresses)
    if (primary
            and email
            and email.lower() != primary.email.lower()):
        user_email(user, primary.email)
        user.save()
    return primary


def send_email_confirmation(request, user, signup=False):
    """
    E-mail verification mails are sent:
    a) Explicitly: when a user signs up
    b) Implicitly: when a user attempts to log in using an unverified
    e-mail while EMAIL_VERIFICATION is mandatory.

    Especially in case of b), we want to limit the number of mails
    sent (consider a user retrying a few times), which is why there is
    a cooldown period before sending a new mail.
    """
    from .models import EmailAddress, EmailConfirmation

    COOLDOWN_PERIOD = timedelta(minutes=3)
    email = user_email(user)
    if email:
        try:
            email_address = EmailAddress.objects.get_for_user(user, email)
            if not email_address.verified:
                send_email = not EmailConfirmation.objects \
                    .filter(sent__gt=now() - COOLDOWN_PERIOD,
                            email_address=email_address) \
                    .exists()
                if send_email:
                    email_address.send_confirmation(request,
                                                    signup=signup)
            else:
                send_email = False
        except EmailAddress.DoesNotExist:
            send_email = True
            email_address = EmailAddress.objects.add_email(request,
                                                           user,
                                                           email,
                                                           signup=signup,
                                                           confirm=True)
            assert email_address
        # At this point, if we were supposed to send an email we have sent it.
        if send_email:
            get_adapter().add_message(request,
                                      messages.INFO,
                                      'account/messages/'
                                      'email_confirmation_sent.txt',
                                      {'email': email})
    if signup:
        request.session['account_user'] = user.pk


def sync_user_email_addresses(user):
    """
    Keep user.email in sync with user.emailaddress_set.

    Under some circumstances the user.email may not have ended up as
    an EmailAddress record, e.g. in the case of manually created admin
    users.
    """
    from .models import EmailAddress
    email = user_email(user)
    if email and not EmailAddress.objects.filter(user=user,
                                                 email__iexact=email).exists():
        if app_settings.UNIQUE_EMAIL \
                and EmailAddress.objects.filter(email__iexact=email).exists():
            # Bail out
            return
        EmailAddress.objects.create(user=user,
                                    email=email,
                                    primary=False,
                                    verified=False)


def random_token(extra=None, hash_func=hashlib.sha256):
    if extra is None:
        extra = []
    bits = extra + [str(random.SystemRandom().getrandbits(512))]
    return hash_func("".join(bits).encode('utf-8')).hexdigest()


def passthrough_next_redirect_url(request, url, redirect_field_name):
    assert url.find("?") < 0  # TODO: Handle this case properly
    next_url = get_next_redirect_url(request, redirect_field_name)
    if next_url:
        url = url + '?' + urlencode({redirect_field_name: next_url})
    return url

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.sites.models import Site
from django.http import (HttpResponseRedirect, Http404,
                         HttpResponsePermanentRedirect)
from django.shortcuts import get_object_or_404
from django.utils.http import base36_to_int
from django.views.generic.base import TemplateResponseMixin, View, TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect

from ..exceptions import ImmediateHttpResponse
from ..utils import get_user_model

from .utils import (get_next_redirect_url, complete_signup,
                    get_login_redirect_url, perform_login,
                    passthrough_next_redirect_url)
from .forms import AddEmailForm, ChangePasswordForm
from .forms import LoginForm, ResetPasswordKeyForm
from .forms import ResetPasswordForm, SetPasswordForm, SignupForm
from .utils import sync_user_email_addresses
from .models import EmailAddress, EmailConfirmation

from . import signals
from . import app_settings

from .adapter import get_adapter

User = get_user_model()


def _ajax_response(request, response, form=None):
    if request.is_ajax():
        if (isinstance(response, HttpResponseRedirect)
                or isinstance(response, HttpResponsePermanentRedirect)):
            redirect_to = response['Location']
        else:
            redirect_to = None
        response = get_adapter().ajax_response(request,
                                               response,
                                               form=form,
                                               redirect_to=redirect_to)
    return response


class RedirectAuthenticatedUserMixin(object):
    def dispatch(self, request, *args, **kwargs):
        # WORKAROUND: https://code.djangoproject.com/ticket/19316
        self.request = request
        # (end WORKAROUND)
        if request.user.is_authenticated():
            redirect_to = self.get_authenticated_redirect_url()
            response = HttpResponseRedirect(redirect_to)
            return response
        else:
            response = super(RedirectAuthenticatedUserMixin,
                             self).dispatch(request,
                                            *args,
                                            **kwargs)
        return response

    def get_authenticated_redirect_url(self):
        redirect_field_name = self.redirect_field_name
        return get_login_redirect_url(self.request,
                                      url=self.get_success_url(),
                                      redirect_field_name=redirect_field_name)


class AjaxCapableProcessFormViewMixin(object):

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            response = self.form_valid(form)
        else:
            response = self.form_invalid(form)
        return _ajax_response(self.request, response, form=form)


class LoginView(RedirectAuthenticatedUserMixin,
                AjaxCapableProcessFormViewMixin,
                FormView):
    form_class = LoginForm
    template_name = "account/login.html"
    success_url = None
    redirect_field_name = "next"

    def form_valid(self, form):
        success_url = self.get_success_url()
        return form.login(self.request, redirect_url=success_url)

    def get_success_url(self):
        # Explicitly passed ?next= URL takes precedence
        ret = (get_next_redirect_url(self.request,
                                     self.redirect_field_name)
               or self.success_url)
        return ret

    def get_context_data(self, **kwargs):
        ret = super(LoginView, self).get_context_data(**kwargs)
        signup_url = passthrough_next_redirect_url(self.request,
                                                   reverse("account_signup"),
                                                   self.redirect_field_name)
        redirect_field_value = self.request.REQUEST \
            .get(self.redirect_field_name)
        ret.update({"signup_url": signup_url,
                    "site": Site.objects.get_current(),
                    "redirect_field_name": self.redirect_field_name,
                    "redirect_field_value": redirect_field_value})
        return ret

login = LoginView.as_view()


class CloseableSignupMixin(object):
    template_name_signup_closed = "account/signup_closed.html"

    def dispatch(self, request, *args, **kwargs):
        # WORKAROUND: https://code.djangoproject.com/ticket/19316
        self.request = request
        # (end WORKAROUND)
        try:
            if not self.is_open():
                return self.closed()
        except ImmediateHttpResponse as e:
            return e.response
        return super(CloseableSignupMixin, self).dispatch(request,
                                                          *args,
                                                          **kwargs)

    def is_open(self):
        return get_adapter().is_open_for_signup(self.request)

    def closed(self):
        response_kwargs = {
            "request": self.request,
            "template": self.template_name_signup_closed,
        }
        return self.response_class(**response_kwargs)


class SignupView(RedirectAuthenticatedUserMixin, CloseableSignupMixin,
                 AjaxCapableProcessFormViewMixin, FormView):
    template_name = "account/signup.html"
    form_class = SignupForm
    redirect_field_name = "next"
    success_url = None

    def get_success_url(self):
        # Explicitly passed ?next= URL takes precedence
        ret = (get_next_redirect_url(self.request,
                                     self.redirect_field_name)
               or self.success_url)
        return ret

    def form_valid(self, form):
        user = form.save(self.request)
        return complete_signup(self.request, user,
                               app_settings.EMAIL_VERIFICATION,
                               self.get_success_url())

    def get_context_data(self, **kwargs):
        form = kwargs['form']
        form.fields["email"].initial = self.request.session \
            .get('account_verified_email', None)
        ret = super(SignupView, self).get_context_data(**kwargs)
        login_url = passthrough_next_redirect_url(self.request,
                                                  reverse("account_login"),
                                                  self.redirect_field_name)
        redirect_field_name = self.redirect_field_name
        redirect_field_value = self.request.REQUEST.get(redirect_field_name)
        ret.update({"login_url": login_url,
                    "redirect_field_name": redirect_field_name,
                    "redirect_field_value": redirect_field_value})
        return ret

signup = SignupView.as_view()


class ConfirmEmailView(TemplateResponseMixin, View):

    def get_template_names(self):
        if self.request.method == 'POST':
            return ["account/email_confirmed.html"]
        else:
            return ["account/email_confirm.html"]

    def get(self, *args, **kwargs):
        try:
            self.object = self.get_object()
            if app_settings.CONFIRM_EMAIL_ON_GET:
                return self.post(*args, **kwargs)
        except Http404:
            self.object = None
        ctx = self.get_context_data()
        return self.render_to_response(ctx)

    def post(self, *args, **kwargs):
        self.object = confirmation = self.get_object()
        confirmation.confirm(self.request)
        get_adapter().add_message(self.request,
                                  messages.SUCCESS,
                                  'account/messages/email_confirmed.txt',
                                  {'email': confirmation.email_address.email})
        if app_settings.LOGIN_ON_EMAIL_CONFIRMATION:
            resp = self.login_on_confirm(confirmation)
            if resp:
                return resp
        # Don't -- allauth doesn't touch is_active so that sys admin can
        # use it to block users et al
        #
        # user = confirmation.email_address.user
        # user.is_active = True
        # user.save()
        redirect_url = self.get_redirect_url()
        if not redirect_url:
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        return redirect(redirect_url)

    def login_on_confirm(self, confirmation):
        """
        Simply logging in the user may become a security issue. If you
        do not take proper care (e.g. don't purge used email
        confirmations), a malicious person that got hold of the link
        will be able to login over and over again and the user is
        unable to do anything about it. Even restoring his own mailbox
        security will not help, as the links will still work. For
        password reset this is different, this mechanism works only as
        long as the attacker has access to the mailbox. If he no
        longer has access he cannot issue a password request and
        intercept it. Furthermore, all places where the links are
        listed (log files, but even Google Analytics) all of a sudden
        need to be secured. Purging the email confirmation once
        confirmed changes the behavior -- users will not be able to
        repeatedly confirm (in case they forgot that they already
        clicked the mail).

        All in all, opted for storing the user that is in the process
        of signing up in the session to avoid all of the above.  This
        may not 100% work in case the user closes the browser (and the
        session gets lost), but at least we're secure.
        """
        user_pk = self.request.session.pop('account_user', None)
        user = confirmation.email_address.user
        if user_pk == user.pk and self.request.user.is_anonymous():
            return perform_login(self.request,
                                 user,
                                 app_settings.EmailVerificationMethod.NONE)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        try:
            return queryset.get(key=self.kwargs["key"].lower())
        except EmailConfirmation.DoesNotExist:
            raise Http404()

    def get_queryset(self):
        qs = EmailConfirmation.objects.all_valid()
        qs = qs.select_related("email_address__user")
        return qs

    def get_context_data(self, **kwargs):
        ctx = kwargs
        ctx["confirmation"] = self.object
        return ctx

    def get_redirect_url(self):
        return get_adapter().get_email_confirmation_redirect_url(self.request)

confirm_email = ConfirmEmailView.as_view()


class EmailView(FormView):
    template_name = "account/email.html"
    form_class = AddEmailForm
    success_url = reverse_lazy('account_email')

    def dispatch(self, request, *args, **kwargs):
        sync_user_email_addresses(request.user)
        return super(EmailView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(EmailView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        email_address = form.save(self.request)
        get_adapter().add_message(self.request,
                                  messages.INFO,
                                  'account/messages/'
                                  'email_confirmation_sent.txt',
                                  {'email': form.cleaned_data["email"]})
        signals.email_added.send(sender=self.request.user.__class__,
                                 request=self.request,
                                 user=self.request.user,
                                 email_address=email_address)
        return super(EmailView, self).form_valid(form)

    def post(self, request, *args, **kwargs):
        res = None
        if "action_add" in request.POST:
            res = super(EmailView, self).post(request, *args, **kwargs)
        elif request.POST.get("email"):
            if "action_send" in request.POST:
                res = self._action_send(request)
            elif "action_remove" in request.POST:
                res = self._action_remove(request)
            elif "action_primary" in request.POST:
                res = self._action_primary(request)
            # TODO: Ugly. But if we .get() here the email is used as
            # initial for the add form, whereas the user was not
            # interacting with that form..
            res = res or HttpResponseRedirect(reverse('account_email'))
        return res or self.get(request, *args, **kwargs)

    def _action_send(self, request, *args, **kwargs):
        email = request.POST["email"]
        try:
            email_address = EmailAddress.objects.get(
                user=request.user,
                email=email,
            )
            get_adapter().add_message(request,
                                      messages.INFO,
                                      'account/messages/'
                                      'email_confirmation_sent.txt',
                                      {'email': email})
            email_address.send_confirmation(request)
            return HttpResponseRedirect(self.get_success_url())
        except EmailAddress.DoesNotExist:
            pass

    def _action_remove(self, request, *args, **kwargs):
        email = request.POST["email"]
        try:
            email_address = EmailAddress.objects.get(
                user=request.user,
                email=email
            )
            if email_address.primary:
                get_adapter().add_message(request,
                                          messages.ERROR,
                                          'account/messages/'
                                          'cannot_delete_primary_email.txt',
                                          {"email": email})
            else:
                email_address.delete()
                signals.email_removed.send(sender=request.user.__class__,
                                           request=request,
                                           user=request.user,
                                           email_address=email_address)
                get_adapter().add_message(request,
                                          messages.SUCCESS,
                                          'account/messages/email_deleted.txt',
                                          {"email": email})
                return HttpResponseRedirect(self.get_success_url())
        except EmailAddress.DoesNotExist:
            pass

    def _action_primary(self, request, *args, **kwargs):
        email = request.POST["email"]
        try:
            email_address = EmailAddress.objects.get(
                user=request.user,
                email=email,
            )
            # Not primary=True -- Slightly different variation, don't
            # require verified unless moving from a verified
            # address. Ignore constraint if previous primary email
            # address is not verified.
            if not email_address.verified and \
                    EmailAddress.objects.filter(user=request.user,
                                                verified=True).exists():
                get_adapter().add_message(request,
                                          messages.ERROR,
                                          'account/messages/'
                                          'unverified_primary_email.txt')
            else:
                # Sending the old primary address to the signal
                # adds a db query.
                try:
                    from_email_address = EmailAddress.objects \
                        .get(user=request.user, primary=True)
                except EmailAddress.DoesNotExist:
                    from_email_address = None
                email_address.set_as_primary()
                get_adapter() \
                    .add_message(request,
                                 messages.SUCCESS,
                                 'account/messages/primary_email_set.txt')
                signals.email_changed \
                    .send(sender=request.user.__class__,
                          request=request,
                          user=request.user,
                          from_email_address=from_email_address,
                          to_email_address=email_address)
                return HttpResponseRedirect(self.get_success_url())
        except EmailAddress.DoesNotExist:
            pass

    def get_context_data(self, **kwargs):
        ret = super(EmailView, self).get_context_data(**kwargs)
        # NOTE: For backwards compatibility
        ret['add_email_form'] = ret.get('form')
        # (end NOTE)
        return ret

email = login_required(EmailView.as_view())


class PasswordChangeView(FormView):
    template_name = "account/password_change.html"
    form_class = ChangePasswordForm
    success_url = reverse_lazy("account_change_password")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_usable_password():
            return HttpResponseRedirect(reverse('account_set_password'))
        return super(PasswordChangeView, self).dispatch(request, *args,
                                                        **kwargs)

    def get_form_kwargs(self):
        kwargs = super(PasswordChangeView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        get_adapter().add_message(self.request,
                                  messages.SUCCESS,
                                  'account/messages/password_changed.txt')
        signals.password_changed.send(sender=self.request.user.__class__,
                                      request=self.request,
                                      user=self.request.user)
        return super(PasswordChangeView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        ret = super(PasswordChangeView, self).get_context_data(**kwargs)
        # NOTE: For backwards compatibility
        ret['password_change_form'] = ret.get('form')
        # (end NOTE)
        return ret

password_change = login_required(PasswordChangeView.as_view())


class PasswordSetView(FormView):
    template_name = "account/password_set.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("account_set_password")

    def dispatch(self, request, *args, **kwargs):
        if request.user.has_usable_password():
            return HttpResponseRedirect(reverse('account_change_password'))
        return super(PasswordSetView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(PasswordSetView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        get_adapter().add_message(self.request,
                                  messages.SUCCESS,
                                  'account/messages/password_set.txt')
        signals.password_set.send(sender=self.request.user.__class__,
                                  request=self.request, user=self.request.user)
        return super(PasswordSetView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        ret = super(PasswordSetView, self).get_context_data(**kwargs)
        # NOTE: For backwards compatibility
        ret['password_set_form'] = ret.get('form')
        # (end NOTE)
        return ret

password_set = login_required(PasswordSetView.as_view())


class PasswordResetView(FormView):
    template_name = "account/password_reset.html"
    form_class = ResetPasswordForm
    success_url = reverse_lazy("account_reset_password_done")

    def form_valid(self, form):
        form.save()
        return super(PasswordResetView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        ret = super(PasswordResetView, self).get_context_data(**kwargs)
        # NOTE: For backwards compatibility
        ret['password_reset_form'] = ret.get('form')
        # (end NOTE)
        return ret

password_reset = PasswordResetView.as_view()


class PasswordResetDoneView(TemplateView):
    template_name = "account/password_reset_done.html"

password_reset_done = PasswordResetDoneView.as_view()


class PasswordResetFromKeyView(FormView):
    template_name = "account/password_reset_from_key.html"
    form_class = ResetPasswordKeyForm
    token_generator = default_token_generator
    success_url = reverse_lazy("account_reset_password_from_key_done")

    def _get_user(self, uidb36):
        # pull out user
        try:
            uid_int = base36_to_int(uidb36)
        except ValueError:
            raise Http404
        return get_object_or_404(User, id=uid_int)

    def dispatch(self, request, uidb36, key, **kwargs):
        self.request = request
        self.uidb36 = uidb36
        self.key = key
        self.reset_user = self._get_user(uidb36)
        if not self.token_generator.check_token(self.reset_user, key):
            return self._response_bad_token(request, uidb36, key, **kwargs)
        else:
            return super(PasswordResetFromKeyView, self).dispatch(request,
                                                                  uidb36,
                                                                  key,
                                                                  **kwargs)

    def get_form_kwargs(self):
        kwargs = super(PasswordResetFromKeyView, self).get_form_kwargs()
        kwargs["user"] = self.reset_user
        kwargs["temp_key"] = self.key
        return kwargs

    def form_valid(self, form):
        form.save()
        get_adapter().add_message(self.request,
                                  messages.SUCCESS,
                                  'account/messages/password_changed.txt')
        signals.password_reset.send(sender=self.reset_user.__class__,
                                    request=self.request,
                                    user=self.reset_user)
        return super(PasswordResetFromKeyView, self).form_valid(form)

    def _response_bad_token(self, request, uidb36, key, **kwargs):
        return self.render_to_response(self.get_context_data(token_fail=True))

password_reset_from_key = PasswordResetFromKeyView.as_view()


class PasswordResetFromKeyDoneView(TemplateView):
    template_name = "account/password_reset_from_key_done.html"

password_reset_from_key_done = PasswordResetFromKeyDoneView.as_view()


class LogoutView(TemplateResponseMixin, View):

    template_name = "account/logout.html"
    redirect_field_name = "next"

    def get(self, *args, **kwargs):
        if app_settings.LOGOUT_ON_GET:
            return self.post(*args, **kwargs)
        if not self.request.user.is_authenticated():
            return redirect(self.get_redirect_url())
        ctx = self.get_context_data()
        return self.render_to_response(ctx)

    def post(self, *args, **kwargs):
        url = self.get_redirect_url()
        if self.request.user.is_authenticated():
            self.logout()
        return redirect(url)

    def logout(self):
        get_adapter().add_message(self.request,
                                  messages.SUCCESS,
                                  'account/messages/logged_out.txt')
        auth_logout(self.request)

    def get_context_data(self, **kwargs):
        ctx = kwargs
        redirect_field_value = self.request.REQUEST \
            .get(self.redirect_field_name)
        ctx.update({
            "redirect_field_name": self.redirect_field_name,
            "redirect_field_value": redirect_field_value})
        return ctx

    def get_redirect_url(self):
        return (get_next_redirect_url(self.request,
                                      self.redirect_field_name)
                or get_adapter().get_logout_redirect_url(self.request))

logout = LogoutView.as_view()


class AccountInactiveView(TemplateView):
    template_name = 'account/account_inactive.html'

account_inactive = AccountInactiveView.as_view()


class EmailVerificationSentView(TemplateView):
    template_name = 'account/verification_sent.html'

email_verification_sent = EmailVerificationSentView.as_view()

########NEW FILE########
__FILENAME__ = app_settings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SOCIALACCOUNT_ENABLED = 'allauth.socialaccount' in settings.INSTALLED_APPS

if SOCIALACCOUNT_ENABLED:
    if 'allauth.socialaccount.context_processors.socialaccount' \
            not in settings.TEMPLATE_CONTEXT_PROCESSORS:
        raise ImproperlyConfigured("socialaccount context processor "
                    "not found in settings.TEMPLATE_CONTEXT_PROCESSORS."
                    "See settings.py instructions here: "
                    "https://github.com/pennersr/django-allauth#installation")

LOGIN_REDIRECT_URL = getattr(settings, 'LOGIN_REDIRECT_URL', '/')

USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

########NEW FILE########
__FILENAME__ = exceptions
class ImmediateHttpResponse(Exception):
    """
    This exception is used to interrupt the flow of processing to immediately
    return a custom HttpResponse.
    """
    def __init__(self, response):
        self.response = response

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = adapter
from __future__ import absolute_import

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

from ..utils import (import_attribute,
                     email_address_exists,
                     valid_email_or_none)
from ..account.utils import user_email, user_username, user_field
from ..account.models import EmailAddress
from ..account.adapter import get_adapter as get_account_adapter
from ..account import app_settings as account_settings
from ..account.app_settings import EmailVerificationMethod

from . import app_settings


class DefaultSocialAccountAdapter(object):

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        (and before the pre_social_login signal is emitted).

        You can use this hook to intervene, e.g. abort the login by
        raising an ImmediateHttpResponse

        Why both an adapter hook and the signal? Intervening in
        e.g. the flow from within a signal handler is bad -- multiple
        handlers may be active and are executed in undetermined order.
        """
        pass

    def new_user(self, request, sociallogin):
        """
        Instantiates a new User instance.
        """
        return get_account_adapter().new_user(request)

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login. In case of auto-signup,
        the signup form is not available.
        """
        u = sociallogin.account.user
        u.set_unusable_password()
        if form:
            get_account_adapter().save_user(request, u, form)
        else:
            get_account_adapter().populate_username(request, u)
        sociallogin.save(request)
        return u

    def populate_user(self,
                      request,
                      sociallogin,
                      data):
        """
        Hook that can be used to further populate the user instance.

        For convenience, we populate several common fields.

        Note that the user instance being populated represents a
        suggested User instance that represents the social user that is
        in the process of being logged in.

        The User instance need not be completely valid and conflict
        free. For example, verifying whether or not the username
        already exists, is not a responsibility.
        """
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        name = data.get('name')
        user = sociallogin.account.user
        user_username(user, username or '')
        user_email(user, valid_email_or_none(email) or '')
        name_parts = (name or '').partition(' ')
        user_field(user, 'first_name', first_name or name_parts[0])
        user_field(user, 'last_name', last_name or name_parts[2])
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the default URL to redirect to after successfully
        connecting a social account.
        """
        assert request.user.is_authenticated()
        url = reverse('socialaccount_connections')
        return url

    def validate_disconnect(self, account, accounts):
        """
        Validate whether or not the socialaccount account can be
        safely disconnected.
        """
        if len(accounts) == 1:
            # No usable password would render the local account unusable
            if not account.user.has_usable_password():
                raise ValidationError(_("Your account has no password set"
                                        " up."))
            # No email address, no password reset
            if app_settings.EMAIL_VERIFICATION \
                    == EmailVerificationMethod.MANDATORY:
                if EmailAddress.objects.filter(user=account.user,
                                               verified=True).count() == 0:
                    raise ValidationError(_("Your account has no verified"
                                            " e-mail address."))

    def is_auto_signup_allowed(self, request, sociallogin):
        # If email is specified, check for duplicate and if so, no auto signup.
        auto_signup = app_settings.AUTO_SIGNUP
        if auto_signup:
            email = user_email(sociallogin.account.user)
            # Let's check if auto_signup is really possible...
            if email:
                if account_settings.UNIQUE_EMAIL:
                    if email_address_exists(email):
                        # Oops, another user already has this address.  We
                        # cannot simply connect this social account to the
                        # existing user. Reason is that the email adress may
                        # not be verified, meaning, the user may be a hacker
                        # that has added your email address to his account in
                        # the hope that you fall in his trap.  We cannot check
                        # on 'email_address.verified' either, because
                        # 'email_address' is not guaranteed to be verified.
                        auto_signup = False
                        # FIXME: We redirect to signup form -- user will
                        # see email address conflict only after posting
                        # whereas we detected it here already.
            elif app_settings.EMAIL_REQUIRED:
                # Nope, email is required and we don't have it yet...
                auto_signup = False
        return auto_signup

    def is_open_for_signup(self, request, sociallogin):
        """
        Checks whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse
        """
        return get_account_adapter().is_open_for_signup(request)


def get_adapter():
    return import_attribute(app_settings.ADAPTER)()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django import forms

from .models import SocialApp, SocialAccount, SocialToken

from ..account import app_settings
from ..utils import get_user_model

User = get_user_model()


class SocialAppForm(forms.ModelForm):
    class Meta:
        model = SocialApp
        exclude = []
        widgets = {
            'client_id': forms.TextInput(attrs={'size': '100'}),
            'key': forms.TextInput(attrs={'size': '100'}),
            'secret': forms.TextInput(attrs={'size': '100'})
        }


class SocialAppAdmin(admin.ModelAdmin):
    form = SocialAppForm
    list_display = ('name', 'provider',)
    filter_horizontal = ('sites',)


class SocialAccountAdmin(admin.ModelAdmin):
    search_fields = ['user__emailaddress__email'] + \
        list(map(lambda a: 'user__' + a,
             filter(lambda a: a and hasattr(User(), a),
                    [app_settings.USER_MODEL_USERNAME_FIELD,
                     'first_name',
                     'last_name'])))
    raw_id_fields = ('user',)
    list_display = ('user', 'uid', 'provider')
    list_filter = ('provider',)


class SocialTokenAdmin(admin.ModelAdmin):
    raw_id_fields = ('app', 'account',)
    list_display = ('app', 'account', 'truncated_token', 'expires_at')
    list_filter = ('app', 'app__provider', 'expires_at')

    def truncated_token(self, token):
        max_chars = 40
        ret = token.token
        if len(ret) > max_chars:
            ret = ret[0:max_chars] + '...(truncated)'
        return ret
    truncated_token.short_description = 'Token'

admin.site.register(SocialApp, SocialAppAdmin)
admin.site.register(SocialToken, SocialTokenAdmin)
admin.site.register(SocialAccount, SocialAccountAdmin)

########NEW FILE########
__FILENAME__ = apps
#  require django >= 1.7
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SocialAccountConfig(AppConfig):
    name = 'allauth.socialaccount'
    verbose_name = _('Social Accounts')

########NEW FILE########
__FILENAME__ = app_settings
class AppSettings(object):

    def __init__(self, prefix):
        self.prefix = prefix

    def _setting(self, name, dflt):
        from django.conf import settings
        getter = getattr(settings,
                         'ALLAUTH_SETTING_GETTER',
                         lambda name, dflt: getattr(settings, name, dflt))
        return getter(self.prefix + name, dflt)

    @property
    def QUERY_EMAIL(self):
        """
        Request e-mail address from 3rd party account provider?
        E.g. using OpenID AX
        """
        from allauth.account import app_settings as account_settings
        return self._setting("QUERY_EMAIL",
                             account_settings.EMAIL_REQUIRED)

    @property
    def AUTO_SIGNUP(self):
        """
        Attempt to bypass the signup form by using fields (e.g. username,
        email) retrieved from the social account provider. If a conflict
        arises due to a duplicate e-mail signup form will still kick in.
        """
        return self._setting("AUTO_SIGNUP", True)

    @property
    def PROVIDERS(self):
        """
        Provider specific settings
        """
        return self._setting("PROVIDERS", {})

    @property
    def EMAIL_REQUIRED(self):
        """
        The user is required to hand over an e-mail address when signing up
        """
        from allauth.account import app_settings as account_settings
        return self._setting("EMAIL_REQUIRED", account_settings.EMAIL_REQUIRED)

    @property
    def EMAIL_VERIFICATION(self):
        """
        See e-mail verification method
        """
        from allauth.account import app_settings as account_settings
        return self._setting("EMAIL_VERIFICATION",
                             account_settings.EMAIL_VERIFICATION)

    @property
    def ADAPTER(self):
        return self._setting('ADAPTER',
                             'allauth.socialaccount.adapter'
                             '.DefaultSocialAccountAdapter')

# Ugly? Guido recommends this himself ...
# http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
import sys
app_settings = AppSettings('SOCIALACCOUNT_')
app_settings.__name__ = __name__
sys.modules[__name__] = app_settings

########NEW FILE########
__FILENAME__ = context_processors
from . import providers

def socialaccount(request):
    ctx = { 'providers': providers.registry.get_list() }
    return dict(socialaccount=ctx)

########NEW FILE########
__FILENAME__ = fields
# Courtesy of django-social-auth
import json

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import six

try:
    from django.utils.encoding import smart_unicode as smart_text
except ImportError:
    from django.utils.encoding import smart_text


class JSONField(six.with_metaclass(models.SubfieldBase,
                                   models.TextField)):
    """Simple JSON field that stores python structures as JSON strings
    on database.
    """

    def to_python(self, value):
        """
        Convert the input JSON value into python structures, raises
        django.core.exceptions.ValidationError if the data can't be converted.
        """
        if self.blank and not value:
            return None
        if isinstance(value, six.string_types):
            try:
                return json.loads(value)
            except Exception as e:
                raise ValidationError(str(e))
        else:
            return value

    def validate(self, value, model_instance):
        """Check value is a valid JSON string, raise ValidationError on
        error."""
        if isinstance(value, six.string_types):
            super(JSONField, self).validate(value, model_instance)
            try:
                json.loads(value)
            except Exception as e:
                raise ValidationError(str(e))

    def get_prep_value(self, value):
        """Convert value to JSON string before save"""
        try:
            return json.dumps(value)
        except Exception as e:
            raise ValidationError(str(e))

    def value_to_string(self, obj):
        """Return value from object converted to string properly"""
        return smart_text(self.get_prep_value(self._get_val_from_obj(obj)))

    def value_from_object(self, obj):
        """Return value dumped to string."""
        return self.get_prep_value(self._get_val_from_obj(obj))


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^allauth\.socialaccount\.fields\.JSONField"])
except:
    pass

########NEW FILE########
__FILENAME__ = forms
from __future__ import absolute_import

from django import forms
from django.utils.translation import ugettext_lazy as _

from allauth.account.forms import BaseSignupForm
from allauth.account.utils import (user_username, user_email,
                                   user_field)

from .models import SocialAccount
from .adapter import get_adapter
from . import app_settings
from . import signals


class SignupForm(BaseSignupForm):

    def __init__(self, *args, **kwargs):
        self.sociallogin = kwargs.pop('sociallogin')
        user = self.sociallogin.account.user
        # TODO: Should become more generic, not listing
        # a few fixed properties.
        initial = {'email': user_email(user) or '',
                   'username': user_username(user) or '',
                   'first_name': user_field(user, 'first_name') or '',
                   'last_name': user_field(user, 'last_name') or ''}
        kwargs.update({
            'initial': initial,
            'email_required': kwargs.get('email_required',
                                         app_settings.EMAIL_REQUIRED)})
        super(SignupForm, self).__init__(*args, **kwargs)

    def save(self, request):
        adapter = get_adapter()
        user = adapter.save_user(request, self.sociallogin, form=self)
        self.custom_signup(request, user)
        return user

    def raise_duplicate_email_error(self):
        raise forms.ValidationError(
            _("An account already exists with this e-mail address."
              " Please sign in to that account first, then connect"
              " your %s account.")
            % self.sociallogin.account.get_provider().name)


class DisconnectForm(forms.Form):
    account = forms.ModelChoiceField(queryset=SocialAccount.objects.none(),
                                     widget=forms.RadioSelect,
                                     required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.accounts = SocialAccount.objects.filter(user=self.request.user)
        super(DisconnectForm, self).__init__(*args, **kwargs)
        self.fields['account'].queryset = self.accounts

    def clean(self):
        cleaned_data = super(DisconnectForm, self).clean()
        account = cleaned_data.get('account')
        if account:
            get_adapter().validate_disconnect(account, self.accounts)
        return cleaned_data

    def save(self):
        account = self.cleaned_data['account']
        account.delete()
        signals.social_account_removed.send(sender=SocialAccount,
                                            request=self.request,
                                            socialaccount=account)

########NEW FILE########
__FILENAME__ = helpers
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import render_to_response, render
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.forms import ValidationError
from django.core.urlresolvers import reverse

from allauth.utils import get_user_model
from allauth.account.utils import (perform_login, complete_signup,
                                   user_username)
from allauth.account import app_settings as account_settings
from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.exceptions import ImmediateHttpResponse

from .models import SocialLogin
from . import app_settings
from . import signals
from .adapter import get_adapter

User = get_user_model()


def _process_signup(request, sociallogin):
    auto_signup = get_adapter().is_auto_signup_allowed(request,
                                                       sociallogin)
    if not auto_signup:
        request.session['socialaccount_sociallogin'] = sociallogin.serialize()
        url = reverse('socialaccount_signup')
        ret = HttpResponseRedirect(url)
    else:
        # Ok, auto signup it is, at least the e-mail address is ok.
        # We still need to check the username though...
        if account_settings.USER_MODEL_USERNAME_FIELD:
            username = user_username(sociallogin.account.user)
            try:
                get_account_adapter().clean_username(username)
            except ValidationError:
                # This username is no good ...
                user_username(sociallogin.account.user, '')
        # FIXME: This part contains a lot of duplication of logic
        # ("closed" rendering, create user, send email, in active
        # etc..)
        try:
            if not get_adapter().is_open_for_signup(request,
                                                    sociallogin):
                return render(request,
                              "account/signup_closed.html")
        except ImmediateHttpResponse as e:
            return e.response
        get_adapter().save_user(request, sociallogin, form=None)
        ret = complete_social_signup(request, sociallogin)
    return ret


def _login_social_account(request, sociallogin):
    return perform_login(request, sociallogin.account.user,
                         email_verification=app_settings.EMAIL_VERIFICATION,
                         redirect_url=sociallogin.get_redirect_url(request),
                         signal_kwargs={"sociallogin": sociallogin})


def render_authentication_error(request, extra_context={}):
    return render_to_response(
        "socialaccount/authentication_error.html",
        extra_context, context_instance=RequestContext(request))


def _add_social_account(request, sociallogin):
    if request.user.is_anonymous():
        # This should not happen. Simply redirect to the connections
        # view (which has a login required)
        return HttpResponseRedirect(reverse('socialaccount_connections'))
    level = messages.INFO
    message = 'socialaccount/messages/account_connected.txt'
    if sociallogin.is_existing:
        if sociallogin.account.user != request.user:
            # Social account of other user. For now, this scenario
            # is not supported. Issue is that one cannot simply
            # remove the social account from the other user, as
            # that may render the account unusable.
            level = messages.ERROR
            message = 'socialaccount/messages/account_connected_other.txt'
        else:
            # This account is already connected -- let's play along
            # and render the standard "account connected" message
            # without actually doing anything.
            pass
    else:
        # New account, let's connect
        sociallogin.connect(request, request.user)
        try:
            signals.social_account_added.send(sender=SocialLogin,
                                              request=request,
                                              sociallogin=sociallogin)
        except ImmediateHttpResponse as e:
            return e.response
    default_next = get_adapter() \
        .get_connect_redirect_url(request,
                                  sociallogin.account)
    next_url = sociallogin.get_redirect_url(request) or default_next
    get_account_adapter().add_message(request, level, message)
    return HttpResponseRedirect(next_url)


def complete_social_login(request, sociallogin):
    assert not sociallogin.is_existing
    sociallogin.lookup()
    try:
        get_adapter().pre_social_login(request, sociallogin)
        signals.pre_social_login.send(sender=SocialLogin,
                                      request=request,
                                      sociallogin=sociallogin)
    except ImmediateHttpResponse as e:
        return e.response
    if sociallogin.state.get('process') == 'connect':
        return _add_social_account(request, sociallogin)
    else:
        return _complete_social_login(request, sociallogin)


def _complete_social_login(request, sociallogin):
    if request.user.is_authenticated():
        logout(request)
    if sociallogin.is_existing:
        # Login existing user
        ret = _login_social_account(request, sociallogin)
    else:
        # New social user
        ret = _process_signup(request, sociallogin)
    return ret


def complete_social_signup(request, sociallogin):
    return complete_signup(request,
                           sociallogin.account.user,
                           app_settings.EMAIL_VERIFICATION,
                           sociallogin.get_redirect_url(request),
                           signal_kwargs={'sociallogin': sociallogin})


# TODO: Factor out callable importing functionality
# See: account.utils.user_display
def import_path(path):
    modname, _, attr = path.rpartition('.')
    m = __import__(modname, fromlist=[attr])
    return getattr(m, attr)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration

try:
    from django.contrib.auth import get_user_model
except ImportError: # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SocialAccount'
        db.create_table('socialaccount_socialaccount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=User)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('socialaccount', ['SocialAccount'])


    def backwards(self, orm):
        
        # Deleting model 'SocialAccount'
        db.delete_table('socialaccount_socialaccount')


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
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['socialaccount']

########NEW FILE########
__FILENAME__ = 0002_genericmodels
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SocialToken'
        db.create_table('socialaccount_socialtoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['socialaccount.SocialApp'])),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['socialaccount.SocialAccount'])),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('token_secret', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
        ))
        db.send_create_signal('socialaccount', ['SocialToken'])

        # Adding unique constraint on 'SocialToken', fields ['app', 'account']
        db.create_unique('socialaccount_socialtoken', ['app_id', 'account_id'])

        # Adding model 'SocialApp'
        db.create_table('socialaccount_socialapp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('provider', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('socialaccount', ['SocialApp'])

        # Adding field 'SocialAccount.provider'
        db.add_column('socialaccount_socialaccount', 'provider', self.gf('django.db.models.fields.CharField')(default='', max_length=30, blank=True), keep_default=False)

        # Adding field 'SocialAccount.uid'
        db.add_column('socialaccount_socialaccount', 'uid', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True), keep_default=False)

        # Adding field 'SocialAccount.extra_data'
        db.add_column('socialaccount_socialaccount', 'extra_data', self.gf('allauth.socialaccount.fields.JSONField')(default='{}'), keep_default=False)

        # Changing field 'SocialAccount.last_login'
        db.alter_column('socialaccount_socialaccount', 'last_login', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # Changing field 'SocialAccount.date_joined'
        db.alter_column('socialaccount_socialaccount', 'date_joined', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))


    def backwards(self, orm):
        
        # Removing unique constraint on 'SocialToken', fields ['app', 'account']
        db.delete_unique('socialaccount_socialtoken', ['app_id', 'account_id'])

        # Deleting model 'SocialToken'
        db.delete_table('socialaccount_socialtoken')

        # Deleting model 'SocialApp'
        db.delete_table('socialaccount_socialapp')

        # Deleting field 'SocialAccount.provider'
        db.delete_column('socialaccount_socialaccount', 'provider')

        # Deleting field 'SocialAccount.uid'
        db.delete_column('socialaccount_socialaccount', 'uid')

        # Deleting field 'SocialAccount.extra_data'
        db.delete_column('socialaccount_socialaccount', 'extra_data')

        # Changing field 'SocialAccount.last_login'
        db.alter_column('socialaccount_socialaccount', 'last_login', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'SocialAccount.date_joined'
        db.alter_column('socialaccount_socialaccount', 'date_joined', self.gf('django.db.models.fields.DateTimeField')())


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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']

########NEW FILE########
__FILENAME__ = 0003_auto__add_unique_socialaccount_uid_provider
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration
from django.conf import settings

class Migration(SchemaMigration):
    depends_on = []
    if 'allauth.socialaccount.providers.facebook' in settings.INSTALLED_APPS:
        depends_on.append(('facebook', '0003_tosocialaccount'),)
    if 'allauth.socialaccount.providers.twitter' in settings.INSTALLED_APPS:
        depends_on.append(('twitter', '0003_tosocialaccount'),)
    if 'allauth.socialaccount.providers.openid' in settings.INSTALLED_APPS:
        depends_on.append(('openid', '0002_tosocialaccount'),)

    def forwards(self, orm):

        # Adding unique constraint on 'SocialAccount', fields ['uid', 'provider']
        db.create_unique('socialaccount_socialaccount', ['uid', 'provider'])


    def backwards(self, orm):

        # Removing unique constraint on 'SocialAccount', fields ['uid', 'provider']
        db.delete_unique('socialaccount_socialaccount', ['uid', 'provider'])


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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']

########NEW FILE########
__FILENAME__ = 0004_add_sites
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding M2M table for field sites on 'SocialApp'
        db.create_table('socialaccount_socialapp_sites', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('socialapp', models.ForeignKey(orm['socialaccount.socialapp'], null=False)),
            ('site', models.ForeignKey(orm['sites.site'], null=False))
        ))
        db.create_unique('socialaccount_socialapp_sites', ['socialapp_id', 'site_id'])


    def backwards(self, orm):
        # Removing M2M table for field sites on 'SocialApp'
        db.delete_table('socialaccount_socialapp_sites')


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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['sites.Site']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']
########NEW FILE########
__FILENAME__ = 0005_set_sites
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
        for app in orm.SocialApp.objects.all():
            app.sites.add(app.site)

    def backwards(self, orm):
        "Write your backwards methods here."

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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['sites.Site']"}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0006_auto__del_field_socialapp_site
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'SocialApp.site'
        db.delete_column('socialaccount_socialapp', 'site_id')


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'SocialApp.site'
        raise RuntimeError("Cannot reverse this migration. 'SocialApp.site' and its values cannot be restored.")

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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_socialapp_client_id
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'SocialApp.client_id'
        db.add_column('socialaccount_socialapp', 'client_id', self.gf('django.db.models.fields.CharField')(default='', max_length=100), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'SocialApp.client_id'
        db.delete_column('socialaccount_socialapp', 'client_id')


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 22, 12, 51, 3, 966915)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 22, 12, 51, 3, 966743)'}),
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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'client_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']

########NEW FILE########
__FILENAME__ = 0008_client_id
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for app in orm.SocialApp.objects.all():
            app.client_id = app.key
            app.key = ''
            app.save()

    def backwards(self, orm):
        "Write your backwards methods here."


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 22, 12, 51, 18, 10544)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 12, 22, 12, 51, 18, 10426)'}),
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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'client_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_socialtoken_expires_at
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'SocialToken.expires_at'
        db.add_column('socialaccount_socialtoken', 'expires_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'SocialToken.expires_at'
        db.delete_column('socialaccount_socialtoken', 'expires_at')


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 13, 16, 17, 12, 942209)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 13, 16, 17, 12, 942095)'}),
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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'client_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']

########NEW FILE########
__FILENAME__ = 0010_auto__chg_field_socialtoken_token
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'SocialToken.token'
        db.alter_column('socialaccount_socialtoken', 'token', self.gf('django.db.models.fields.CharField')(max_length=255))

    def backwards(self, orm):

        # Changing field 'SocialToken.token'
        db.alter_column('socialaccount_socialtoken', 'token', self.gf('django.db.models.fields.CharField')(max_length=200))

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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'client_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']
########NEW FILE########
__FILENAME__ = 0011_auto__chg_field_socialtoken_token
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'SocialToken.token'
        db.alter_column('socialaccount_socialtoken', 'token', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'SocialToken.token'
        db.alter_column('socialaccount_socialtoken', 'token', self.gf('django.db.models.fields.CharField')(max_length=255))

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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'client_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.TextField', [], {}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']
########NEW FILE########
__FILENAME__ = 0012_auto__chg_field_socialtoken_token_secret
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'SocialToken.token_secret'
        db.alter_column(u'socialaccount_socialtoken', 'token_secret', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'SocialToken.token_secret'
        db.alter_column(u'socialaccount_socialtoken', 'token_secret', self.gf('django.db.models.fields.CharField')(max_length=200))

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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'socialaccount.socialaccount': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'client_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['socialaccount.SocialApp']"}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.TextField', [], {}),
            'token_secret': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount']
########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import

from django.core.exceptions import PermissionDenied
from django.db import models
from django.contrib.auth import authenticate
from django.contrib.sites.models import Site
from django.utils.encoding import python_2_unicode_compatible
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

import allauth.app_settings
from allauth.account.models import EmailAddress
from allauth.account.utils import get_next_redirect_url, setup_user_email
from allauth.utils import (get_user_model, serialize_instance,
                           deserialize_instance)

from . import providers
from .fields import JSONField


class SocialAppManager(models.Manager):
    def get_current(self, provider):
        site = Site.objects.get_current()
        return self.get(sites__id=site.id,
                        provider=provider)


@python_2_unicode_compatible
class SocialApp(models.Model):
    objects = SocialAppManager()

    provider = models.CharField(verbose_name=_('provider'),
                                max_length=30,
                                choices=providers.registry.as_choices())
    name = models.CharField(verbose_name=_('name'),
                            max_length=40)
    client_id = models.CharField(verbose_name=_('client id'),
                                 max_length=100,
                                 help_text=_('App ID, or consumer key'))
    secret = models.CharField(verbose_name=_('secret key'),
                              max_length=100,
                              help_text=_('API secret, client secret, or'
                              ' consumer secret'))
    key = models.CharField(verbose_name=_('key'),
                           max_length=100,
                           blank=True,
                           help_text=_('Key'))
    # Most apps can be used across multiple domains, therefore we use
    # a ManyToManyField. Note that Facebook requires an app per domain
    # (unless the domains share a common base name).
    # blank=True allows for disabling apps without removing them
    sites = models.ManyToManyField(Site, blank=True)

    class Meta:
        verbose_name = _('social application')
        verbose_name_plural = _('social applications')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class SocialAccount(models.Model):
    user = models.ForeignKey(allauth.app_settings.USER_MODEL)
    provider = models.CharField(verbose_name=_('provider'),
                                max_length=30,
                                choices=providers.registry.as_choices())
    # Just in case you're wondering if an OpenID identity URL is going
    # to fit in a 'uid':
    #
    # Ideally, URLField(max_length=1024, unique=True) would be used
    # for identity.  However, MySQL has a max_length limitation of 255
    # for URLField. How about models.TextField(unique=True) then?
    # Well, that won't work either for MySQL due to another bug[1]. So
    # the only way out would be to drop the unique constraint, or
    # switch to shorter identity URLs. Opted for the latter, as [2]
    # suggests that identity URLs are supposed to be short anyway, at
    # least for the old spec.
    #
    # [1] http://code.djangoproject.com/ticket/2495.
    # [2] http://openid.net/specs/openid-authentication-1_1.html#limits

    uid = models.CharField(verbose_name=_('uid'), max_length=255)
    last_login = models.DateTimeField(verbose_name=_('last login'),
                                      auto_now=True)
    date_joined = models.DateTimeField(verbose_name=_('date joined'),
                                       auto_now_add=True)
    extra_data = JSONField(verbose_name=_('extra data'), default='{}')

    class Meta:
        unique_together = ('provider', 'uid')
        verbose_name = _('social account')
        verbose_name_plural = _('social accounts')

    def authenticate(self):
        return authenticate(account=self)

    def __str__(self):
        return force_text(self.user)

    def get_profile_url(self):
        return self.get_provider_account().get_profile_url()

    def get_avatar_url(self):
        return self.get_provider_account().get_avatar_url()

    def get_provider(self):
        return providers.registry.by_id(self.provider)

    def get_provider_account(self):
        return self.get_provider().wrap_account(self)


@python_2_unicode_compatible
class SocialToken(models.Model):
    app = models.ForeignKey(SocialApp)
    account = models.ForeignKey(SocialAccount)
    token = models \
        .TextField(verbose_name=_('social account'),
                   help_text=_('"oauth_token" (OAuth1) or access token'
                               ' (OAuth2)'))
    token_secret = models \
        .TextField(blank=True,
                   verbose_name=_('token secret'),
                   help_text=_('"oauth_token_secret" (OAuth1) or refresh'
                   ' token (OAuth2)'))
    expires_at = models.DateTimeField(blank=True, null=True,
                                      verbose_name=_('expires at'))

    class Meta:
        unique_together = ('app', 'account')
        verbose_name = _('social application token')
        verbose_name_plural = _('social application tokens')

    def __str__(self):
        return self.token


class SocialLogin(object):
    """
    Represents a social user that is in the process of being logged
    in. This consists of the following information:

    `account` (`SocialAccount` instance): The social account being
    logged in. Providers are not responsible for checking whether or
    not an account already exists or not. Therefore, a provider
    typically creates a new (unsaved) `SocialAccount` instance. The
    `User` instance pointed to by the account (`account.user`) may be
    prefilled by the provider for use as a starting point later on
    during the signup process.

    `token` (`SocialToken` instance): An optional access token token
    that results from performing a successful authentication
    handshake.

    `state` (`dict`): The state to be preserved during the
    authentication handshake. Note that this state may end up in the
    url -- do not put any secrets in here. It currently only contains
    the url to redirect to after login.

    `email_addresses` (list of `EmailAddress`): Optional list of
    e-mail addresses retrieved from the provider.
    """

    def __init__(self, account=None, token=None, email_addresses=[]):
        if token:
            assert token.account is None or token.account == account
            token.account = account
        self.token = token
        self.account = account
        self.email_addresses = email_addresses
        self.state = {}

    def connect(self, request, user):
        self.account.user = user
        self.save(request, connect=True)

    def serialize(self):
        ret = dict(account=serialize_instance(self.account),
                   user=serialize_instance(self.account.user),
                   state=self.state,
                   email_addresses=[serialize_instance(ea)
                                    for ea in self.email_addresses])
        if self.token:
            ret['token'] = serialize_instance(self.token)
        return ret

    @classmethod
    def deserialize(cls, data):
        account = deserialize_instance(SocialAccount, data['account'])
        user = deserialize_instance(get_user_model(), data['user'])
        account.user = user
        if 'token' in data:
            token = deserialize_instance(SocialToken, data['token'])
        else:
            token = None
        email_addresses = []
        for ea in data['email_addresses']:
            email_address = deserialize_instance(EmailAddress, ea)
            email_addresses.append(email_address)
        ret = SocialLogin()
        ret.token = token
        ret.account = account
        ret.user = user
        ret.email_addresses = email_addresses
        ret.state = data['state']
        return ret

    def save(self, request, connect=False):
        """
        Saves a new account. Note that while the account is new,
        the user may be an existing one (when connecting accounts)
        """
        assert not self.is_existing
        user = self.account.user
        user.save()
        self.account.user = user
        self.account.save()
        if self.token:
            self.token.account = self.account
            self.token.save()
        if connect:
            # TODO: Add any new email addresses automatically?
            pass
        else:
            setup_user_email(request, user, self.email_addresses)

    @property
    def is_existing(self):
        """
        Account is temporary, not yet backed by a database record.
        """
        return self.account.pk

    def lookup(self):
        """
        Lookup existing account, if any.
        """
        assert not self.is_existing
        try:
            a = SocialAccount.objects.get(provider=self.account.provider,
                                          uid=self.account.uid)
            # Update account
            a.extra_data = self.account.extra_data
            self.account = a
            a.save()
            # Update token
            if self.token:
                assert not self.token.pk
                try:
                    t = SocialToken.objects.get(account=self.account,
                                                app=self.token.app)
                    t.token = self.token.token
                    if self.token.token_secret:
                        # only update the refresh token if we got one
                        # many oauth2 providers do not resend the refresh token
                        t.token_secret = self.token.token_secret
                    t.expires_at = self.token.expires_at
                    t.save()
                    self.token = t
                except SocialToken.DoesNotExist:
                    self.token.account = a
                    self.token.save()
        except SocialAccount.DoesNotExist:
            pass

    def get_redirect_url(self, request):
        url = self.state.get('next')
        return url

    @classmethod
    def state_from_request(cls, request):
        state = {}
        next_url = get_next_redirect_url(request)
        if next_url:
            state['next'] = next_url
        state['process'] = request.REQUEST.get('process', 'login')
        return state

    @classmethod
    def stash_state(cls, request):
        state = cls.state_from_request(request)
        verifier = get_random_string()
        request.session['socialaccount_state'] = (state, verifier)
        return verifier

    @classmethod
    def unstash_state(cls, request):
        if 'socialaccount_state' not in request.session:
            raise PermissionDenied()
        state, verifier = request.session.pop('socialaccount_state')
        return state

    @classmethod
    def verify_and_unstash_state(cls, request, verifier):
        if 'socialaccount_state' not in request.session:
            raise PermissionDenied()
        state, verifier2 = request.session.pop('socialaccount_state')
        if verifier != verifier2:
            raise PermissionDenied()
        return state

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class AmazonAccount(ProviderAccount):
    def to_str(self):
        return self.account.extra_data.get('name',
                                           super(AmazonAccount, self).to_str())


class AmazonProvider(OAuth2Provider):
    id = 'amazon'
    name = 'Amazon'
    package = 'allauth.socialaccount.providers.amazon'
    account_class = AmazonAccount

    def get_default_scope(self):
        return ['profile']

    def extract_uid(self, data):
        return str(data['user_id'])

    def extract_common_fields(self, data):
        # Hackish way of splitting the fullname.
        # Asumes no middlenames.
        name = data.get('name', '')
        first_name, last_name = name, ''
        if name and ' ' in name:
            first_name, last_name = name.split(' ', 1)
        return dict(email=data['email'],
                    last_name=last_name,
                    first_name=first_name)

providers.registry.register(AmazonProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import AmazonProvider


class AmazonTests(create_oauth2_tests(registry.by_id(AmazonProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
          "Profile":{
                        "CustomerId":"amzn1.account.K2LI23KL2LK2",
                        "Name":"John Doe",
                        "PrimaryEmail":"johndoe@gmail.com"
                    }
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import AmazonProvider

urlpatterns = default_urlpatterns(AmazonProvider)

########NEW FILE########
__FILENAME__ = views
import requests
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import AmazonProvider

class AmazonOAuth2Adapter(OAuth2Adapter):
    provider_id = AmazonProvider.id
    access_token_url = 'https://api.amazon.com/auth/o2/token'
    authorize_url = 'http://www.amazon.com/ap/oa'
    profile_url = 'https://www.amazon.com/ap/user/profile'
    supports_state = False
    redirect_uri_protocol = 'https'

    def complete_login(self, request, app, token, **kwargs):
        response = requests.get(self.profile_url,
                            params={'access_token': token})
        extra_data = response.json()
        if 'Profile' in extra_data:
            extra_data = {
                'user_id': extra_data['Profile']['CustomerId'],
                'name': extra_data['Profile']['Name'],
                'email': extra_data['Profile']['PrimaryEmail']
            }
        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(AmazonOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(AmazonOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class AngelListAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('angellist_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('image')

    def to_str(self):
        dflt = super(AngelListAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class AngelListProvider(OAuth2Provider):
    id = 'angellist'
    name = 'AngelList'
    package = 'allauth.socialaccount.providers.angellist'
    account_class = AngelListAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    username=data.get('angellist_url').split('/')[-1],
                    name=data.get('name'))


providers.registry.register(AngelListProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import AngelListProvider


class AngelListTests(create_oauth2_tests(registry
                                         .by_id(AngelListProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
{"name":"pennersr","id":424732,"bio":"","follower_count":0,
"angellist_url":"https://angel.co/dsxtst",
"image":"https://angel.co/images/shared/nopic.png",
"email":"raymond.penners@gmail.com","blog_url":null,
"online_bio_url":null,"twitter_url":"https://twitter.com/dsxtst",
"facebook_url":null,"linkedin_url":null,"aboutme_url":null,
"github_url":null,"dribbble_url":null,"behance_url":null,
"what_ive_built":null,"locations":[],"roles":[],"skills":[],
"investor":false,"scopes":["message","talent","dealflow","comment",
"email"]}
""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import AngelListProvider


urlpatterns = default_urlpatterns(AngelListProvider)

########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from .provider import AngelListProvider


class AngelListOAuth2Adapter(OAuth2Adapter):
    provider_id = AngelListProvider.id
    access_token_url = 'https://angel.co/api/oauth/token/'
    authorize_url = 'https://angel.co/api/oauth/authorize/'
    profile_url = 'https://api.angel.co/1/me/'
    supports_state = False

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(AngelListOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(AngelListOAuth2Adapter)

########NEW FILE########
__FILENAME__ = base
from django.utils.encoding import python_2_unicode_compatible

from allauth.socialaccount import app_settings
from allauth.account.models import EmailAddress

from ..models import SocialApp, SocialAccount, SocialLogin
from ..adapter import get_adapter


class AuthProcess(object):
    LOGIN = 'login'
    CONNECT = 'connect'


class AuthAction(object):
    AUTHENTICATE = 'authenticate'
    REAUTHENTICATE = 'reauthenticate'


class Provider(object):
    def get_login_url(self, request, next=None, **kwargs):
        """
        Builds the URL to redirect to when initiating a login for this
        provider.
        """
        raise NotImplementedError("get_login_url() for " + self.name)

    def get_app(self, request):
        return SocialApp.objects.get_current(self.id)

    def media_js(self, request):
        """
        Some providers may require extra scripts (e.g. a Facebook connect)
        """
        return ''

    def wrap_account(self, social_account):
        return self.account_class(social_account)

    def get_settings(self):
        return app_settings.PROVIDERS.get(self.id, {})

    def sociallogin_from_response(self, request, response):
        adapter = get_adapter()
        uid = self.extract_uid(response)
        extra_data = self.extract_extra_data(response)
        common_fields = self.extract_common_fields(response)
        socialaccount = SocialAccount(extra_data=extra_data,
                                      uid=uid,
                                      provider=self.id)
        email_addresses = self.extract_email_addresses(response)
        self.cleanup_email_addresses(common_fields.get('email'),
                                     email_addresses)
        sociallogin = SocialLogin(socialaccount,
                                  email_addresses=email_addresses)
        user = socialaccount.user = adapter.new_user(request, sociallogin)
        user.set_unusable_password()
        adapter.populate_user(request, sociallogin, common_fields)
        return sociallogin

    def extract_extra_data(self, data):
        return data

    def extract_basic_socialaccount_data(self, data):
        """
        Returns a tuple of basic/common social account data.
        For example: ('123', {'first_name': 'John'})
        """
        raise NotImplementedError

    def extract_common_fields(self, data):
        """
        For example:

        {'first_name': 'John'}
        """
        return {}

    def cleanup_email_addresses(self, email, addresses):
        # Move user.email over to EmailAddress
        if (email and email.lower() not in [
                a.email.lower() for a in addresses]):
            addresses.append(EmailAddress(email=email,
                                          verified=False,
                                          primary=True))
        # Force verified emails
        settings = self.get_settings()
        verified_email = settings.get('VERIFIED_EMAIL', False)
        if verified_email:
            for address in addresses:
                address.verified = True

    def extract_email_addresses(self, data):
        """
        For example:

        [EmailAddress(email='john@doe.org',
                      verified=True,
                      primary=True)]
        """
        return []


@python_2_unicode_compatible
class ProviderAccount(object):
    def __init__(self, social_account):
        self.account = social_account

    def get_profile_url(self):
        return None

    def get_avatar_url(self):
        return None

    def get_brand(self):
        """
        Returns a dict containing an id and name identifying the
        brand. Useful when displaying logos next to accounts in
        templates.

        For most providers, these are identical to the provider. For
        OpenID however, the brand can derived from the OpenID identity
        url.
        """
        provider = self.account.get_provider()
        return dict(id=provider.id,
                    name=provider.name)

    def __str__(self):
        return self.to_str()

    def to_str(self):
        """
        Due to the way python_2_unicode_compatible works, this does not work:

            @python_2_unicode_compatible
            class GoogleAccount(ProviderAccount):
                def __str__(self):
                    dflt = super(GoogleAccount, self).__str__()
                    return self.account.extra_data.get('name', dflt)

        It will result in and infinite recursion loop. That's why we
        add a method `to_str` that can be overriden in a conventional
        fashion, without having to worry about @python_2_unicode_compatible
        """
        return self.get_brand()['name']

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class BitbucketAccount(ProviderAccount):
    def get_profile_url(self):
        return 'http://bitbucket.org/' + self.account.extra_data['username']

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar')

    def get_username(self):
        return self.account.extra_data['username']

    def to_str(self):
        return self.get_username()


class BitbucketProvider(OAuthProvider):
    id = 'bitbucket'
    name = 'Bitbucket'
    package = 'allauth.socialaccount.providers.bitbucket'
    account_class = BitbucketAccount

    def extract_uid(self, data):
        return data['username']

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    first_name=data.get('first_name'),
                    username=data.get('username'),
                    last_name=data.get('last_name'))

providers.registry.register(BitbucketProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import BitbucketProvider


class BitbucketTests(create_oauth_tests(registry.by_id(BitbucketProvider.id))):
    def get_mocked_response(self):
        # FIXME: Replace with actual/complete Bitbucket response
        return [MockedResponse(200, r"""
[{"active": true, "email": "raymond.penners@intenct.nl", "primary": true},
 {"active": true, "email": "raymond.penners@gmail.com", "primary": false},
 {"active": true,
  "email": "raymond.penners@jibecompany.com",
  "primary": false}]
        """),
                MockedResponse(200, r"""
{"repositories": [],
 "user": {"avatar": "https://secure.gravatar.com/avatar.jpg",
           "display_name": "pennersr",
           "first_name": "",
           "is_team": false,
           "last_name": "",
           "resource_uri": "/1.0/users/pennersr",
           "username": "pennersr"}}
 """)]  # noqa

    def test_login(self):
        account = super(BitbucketTests, self).test_login()
        bb_account = account.get_provider_account()
        self.assertEqual(bb_account.get_username(),
                         'pennersr')
        self.assertEqual(bb_account.get_avatar_url(),
                         'https://secure.gravatar.com/avatar.jpg')
        self.assertEqual(bb_account.get_profile_url(),
                         'http://bitbucket.org/pennersr')

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import BitbucketProvider

urlpatterns = default_urlpatterns(BitbucketProvider)

########NEW FILE########
__FILENAME__ = views
import json

from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)

from .provider import BitbucketProvider


class BitbucketAPI(OAuth):

    emails_url = 'https://bitbucket.org/api/1.0/emails/'
    users_url = 'https://bitbucket.org/api/1.0/users/'

    def get_user_info(self):
        # TODO: Actually turn these into EmailAddress
        emails = json.loads(self.query(self.emails_url))
        for address in reversed(emails):
            if address['active']:
                email = address['email']
                if address['primary']:
                    break
        data = json.loads(self.query(self.users_url + email))
        user = data['user']
        return user


class BitbucketOAuthAdapter(OAuthAdapter):
    provider_id = BitbucketProvider.id
    request_token_url = 'https://bitbucket.org/api/1.0/oauth/request_token'
    access_token_url = 'https://bitbucket.org/api/1.0/oauth/access_token'
    authorize_url = 'https://bitbucket.org/api/1.0/oauth/authenticate'

    def complete_login(self, request, app, token):
        client = BitbucketAPI(request, app.client_id, app.secret,
                              self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)

oauth_login = OAuthLoginView.adapter_view(BitbucketOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(BitbucketOAuthAdapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class BitlyAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('profile_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('profile_image')

    def to_str(self):
        dflt = super(BitlyAccount, self).to_str()
        return '%s (%s)' % (
            self.account.extra_data.get('full_name', ''),
            dflt,
        )


class BitlyProvider(OAuth2Provider):
    id = 'bitly'
    name = 'Bitly'
    package = 'allauth.socialaccount.providers.bitly'
    account_class = BitlyAccount

    def extract_uid(self, data):
        return str(data['login'])

    def extract_common_fields(self, data):
        return dict(username=data['login'],
                    name=data.get('full_name'))


providers.registry.register(BitlyProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import BitlyProvider

class BitlyTests(create_oauth2_tests(registry.by_id(BitlyProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """{
            "data": {
                "apiKey": "R_f6397a37e765574f2e198dba5bb59522",
                "custom_short_domain": null,
                "display_name": null,
                "full_name": "Bitly API Oauth Demo Account",
                "is_enterprise": false,
                "login": "bitlyapioauthdemo",
                "member_since": 1331567982,
                "profile_image": "http://bitly.com/u/bitlyapioauthdemo.png",
                "profile_url": "http://bitly.com/u/bitlyapioauthdemo",
                "share_accounts": [],
                "tracking_domains": []
            },
            "status_code": 200,
            "status_txt": "OK"
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import BitlyProvider

urlpatterns = default_urlpatterns(BitlyProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import BitlyProvider


class BitlyOAuth2Adapter(OAuth2Adapter):
    provider_id = BitlyProvider.id
    access_token_url = 'https://api-ssl.bitly.com/oauth/access_token'
    authorize_url = 'https://bitly.com/oauth/authorize'
    profile_url = 'https://api-ssl.bitly.com/v3/user/info'
    supports_state = False

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(
            self.profile_url,
            params={'access_token': token.token}
        )
        extra_data = resp.json()['data']
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(BitlyOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BitlyOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class DropboxAccount(ProviderAccount):
    pass


class DropboxProvider(OAuthProvider):
    id = 'dropbox'
    name = 'Dropbox'
    package = 'allauth.socialaccount.providers.dropbox'
    account_class = DropboxAccount

    def extract_uid(self, data):
        return data['uid']

    def extract_common_fields(self, data):
        return dict(username=data.get('display_name'),
                    name=data.get('display_name'),
                    email=data.get('email'))

providers.registry.register(DropboxProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import DropboxProvider


class DropboxTests(create_oauth_tests(registry.by_id(DropboxProvider.id))):
    def get_mocked_response(self):
        # FIXME: Replace with actual/complete Dropbox response
        return [MockedResponse(200, u"""
    { "uid": "123" }
""")]

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns

from .provider import DropboxProvider

urlpatterns = default_urlpatterns(DropboxProvider)

########NEW FILE########
__FILENAME__ = views
import json

from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)

from .provider import DropboxProvider


class DropboxAPI(OAuth):
    """
    Verifying twitter credentials
    """
    url = 'https://api.dropbox.com/1/account/info'

    def get_user_info(self):
        user = json.loads(self.query(self.url))
        return user


class DropboxOAuthAdapter(OAuthAdapter):
    provider_id = DropboxProvider.id
    request_token_url = 'https://api.dropbox.com/1/oauth/request_token'
    access_token_url = 'https://api.dropbox.com/1/oauth/access_token'
    authorize_url = 'https://www.dropbox.com/1/oauth/authorize'

    def complete_login(self, request, app, token):
        client = DropboxAPI(request, app.client_id, app.secret,
                            self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth_login = OAuthLoginView.adapter_view(DropboxOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(DropboxOAuthAdapter)

########NEW FILE########
__FILENAME__ = forms
from django import forms


class FacebookConnectForm(forms.Form):
    access_token = forms.CharField(required=True)

########NEW FILE########
__FILENAME__ = locale
# Default locale mapping for the Facebook JS SDK
# The list of supported locales is at
# https://www.facebook.com/translations/FacebookLocales.xml
import os

from django.utils.translation import get_language, to_locale


def _build_locale_table(filename_or_file):
    """
    Parses the FacebookLocales.xml file and builds a dict relating every
    available language ('en, 'es, 'zh', ...) with a list of available regions
    for that language ('en' -> 'US', 'EN') and an (arbitrary) default region.
    """
    # Require the XML parser module only if we want the default mapping
    from xml.dom.minidom import parse

    dom = parse(filename_or_file)

    reps = dom.getElementsByTagName('representation')
    locs = map(lambda r: r.childNodes[0].data, reps)

    locale_map = {}
    for loc in locs:
        lang, _, reg = loc.partition('_')
        lang_map = locale_map.setdefault(lang, {'regs': [], 'default': reg})
        lang_map['regs'].append(reg)

    # Default region overrides (arbitrary)
    locale_map['en']['default'] = 'US'
    # Special case: Use es_ES for Spain and es_LA for everything else
    locale_map['es']['default'] = 'LA'
    locale_map['zh']['default'] = 'CN'
    locale_map['fr']['default'] = 'FR'
    locale_map['pt']['default'] = 'PT'

    return locale_map


def get_default_locale_callable():
    """
    Wrapper function so that the default mapping is only built when needed
    """
    exec_dir = os.path.dirname(os.path.realpath(__file__))
    xml_path = os.path.join(exec_dir, 'data', 'FacebookLocales.xml')

    fb_locales = _build_locale_table(xml_path)

    def default_locale(request):
        """
        Guess an appropiate FB locale based on the active Django locale.
        If the active locale is available, it is returned. Otherwise,
        it tries to return another locale with the same language. If there
        isn't one avaible, 'en_US' is returned.
        """
        locale = to_locale(get_language())
        lang, _, reg = locale.partition('_')

        lang_map = fb_locales.get(lang)
        if lang_map is not None:
            if reg in lang_map['regs']:
                chosen = lang + '_' + reg
            else:
                chosen = lang + '_' + lang_map['default']
        else:
            chosen = 'en_US'

        return chosen

    return default_locale

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):
    depends_on = (('socialaccount', '0001_initial'),)

    def forwards(self, orm):
        
        # Adding model 'FacebookApp'
        db.create_table('facebook_facebookapp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('application_id', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('api_key', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('application_secret', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('facebook', ['FacebookApp'])

        # Adding model 'FacebookAccount'
        db.create_table('facebook_facebookaccount', (
            ('socialaccount_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['socialaccount.SocialAccount'], unique=True, primary_key=True)),
            ('social_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('facebook', ['FacebookAccount'])


    def backwards(self, orm):
        
        # Deleting model 'FacebookApp'
        db.delete_table('facebook_facebookapp')

        # Deleting model 'FacebookAccount'
        db.delete_table('facebook_facebookaccount')


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
        'facebook.facebookaccount': {
            'Meta': {'object_name': 'FacebookAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'social_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'})
        },
        'facebook.facebookapp': {
            'Meta': {'object_name': 'FacebookApp'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'application_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'application_secret': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['facebook']

########NEW FILE########
__FILENAME__ = 0002_auto__add_facebookaccesstoken__add_unique_facebookaccesstoken_app_acco
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FacebookAccessToken'
        db.create_table('facebook_facebookaccesstoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['facebook.FacebookApp'])),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['facebook.FacebookAccount'])),
            ('access_token', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('facebook', ['FacebookAccessToken'])

        # Adding unique constraint on 'FacebookAccessToken', fields ['app', 'account']
        db.create_unique('facebook_facebookaccesstoken', ['app_id', 'account_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'FacebookAccessToken', fields ['app', 'account']
        db.delete_unique('facebook_facebookaccesstoken', ['app_id', 'account_id'])

        # Deleting model 'FacebookAccessToken'
        db.delete_table('facebook_facebookaccesstoken')


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
        'facebook.facebookaccesstoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'FacebookAccessToken'},
            'access_token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['facebook.FacebookAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['facebook.FacebookApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'facebook.facebookaccount': {
            'Meta': {'object_name': 'FacebookAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'social_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'})
        },
        'facebook.facebookapp': {
            'Meta': {'object_name': 'FacebookApp'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'application_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'application_secret': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['facebook']

########NEW FILE########
__FILENAME__ = 0003_tosocialaccount
# encoding: utf-8
from south.v2 import DataMigration

class Migration(DataMigration):

    depends_on = (('socialaccount', '0002_genericmodels'),)

    def forwards(self, orm):
        # Migrate FB apps
        app_id_to_sapp = {}
        for app in orm.FacebookApp.objects.all():
            sapp = orm['socialaccount.SocialApp'].objects \
                .create(site=app.site,
                        provider='facebook',
                        name=app.name,
                        key=app.application_id,
                        secret=app.application_secret)
            app_id_to_sapp[app.id] = sapp
        # Migrate FB accounts
        acc_id_to_sacc = {}
        for acc in orm.FacebookAccount.objects.all():
            sacc = acc.socialaccount_ptr
            sacc.uid = acc.social_id
            sacc.extra_data = { 'link': acc.link,
                                'name': acc.name }
            sacc.provider = 'facebook'
            sacc.save()
            acc_id_to_sacc[acc.id] = sacc
        # Migrate tokens
        for token in orm.FacebookAccessToken.objects.all():
            sapp = app_id_to_sapp[token.app.id]
            sacc = acc_id_to_sacc[token.account.id]
            orm['socialaccount.SocialToken'].objects \
                .create(app=sapp,
                        account=sacc,
                        token=token.access_token,
                        token_secret='')


    def backwards(self, orm):
        "Write your backwards methods here."


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
        'facebook.facebookaccesstoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'FacebookAccessToken'},
            'access_token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['facebook.FacebookAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['facebook.FacebookApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'facebook.facebookaccount': {
            'Meta': {'object_name': 'FacebookAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'social_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'})
        },
        'facebook.facebookapp': {
            'Meta': {'object_name': 'FacebookApp'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'application_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'application_secret': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount', 'facebook']

########NEW FILE########
__FILENAME__ = 0004_auto__del_facebookapp__del_facebookaccesstoken__del_unique_facebookacc
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'FacebookAccessToken', fields ['app', 'account']
        db.delete_unique('facebook_facebookaccesstoken', ['app_id', 'account_id'])

        # Deleting model 'FacebookApp'
        db.delete_table('facebook_facebookapp')

        # Deleting model 'FacebookAccessToken'
        db.delete_table('facebook_facebookaccesstoken')

        # Deleting model 'FacebookAccount'
        db.delete_table('facebook_facebookaccount')


    def backwards(self, orm):
        
        # Adding model 'FacebookApp'
        db.create_table('facebook_facebookapp', (
            ('application_id', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('api_key', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application_secret', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('facebook', ['FacebookApp'])

        # Adding model 'FacebookAccessToken'
        db.create_table('facebook_facebookaccesstoken', (
            ('access_token', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['facebook.FacebookAccount'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['facebook.FacebookApp'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('facebook', ['FacebookAccessToken'])

        # Adding unique constraint on 'FacebookAccessToken', fields ['app', 'account']
        db.create_unique('facebook_facebookaccesstoken', ['app_id', 'account_id'])

        # Adding model 'FacebookAccount'
        db.create_table('facebook_facebookaccount', (
            ('socialaccount_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['socialaccount.SocialAccount'], unique=True, primary_key=True)),
            ('social_id', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('facebook', ['FacebookAccount'])


    models = {
        
    }

    complete_apps = ['facebook']

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
import json

from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.html import mark_safe, escapejs
from django.utils.crypto import get_random_string

from allauth.utils import import_callable
from allauth.account.models import EmailAddress
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import (ProviderAccount,
                                                  AuthProcess,
                                                  AuthAction)
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.app_settings import QUERY_EMAIL
from allauth.socialaccount.models import SocialApp

from .locale import get_default_locale_callable


NONCE_SESSION_KEY = 'allauth_facebook_nonce'
NONCE_LENGTH = 32


class FacebookAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('link')

    def get_avatar_url(self):
        uid = self.account.uid
        return 'https://graph.facebook.com/%s/picture?type=large&return_ssl_resources=1' % uid  # noqa

    def to_str(self):
        dflt = super(FacebookAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class FacebookProvider(OAuth2Provider):
    id = 'facebook'
    name = 'Facebook'
    package = 'allauth.socialaccount.providers.facebook'
    account_class = FacebookAccount

    def __init__(self):
        self._locale_callable_cache = None
        super(FacebookProvider, self).__init__()

    def get_method(self):
        return self.get_settings().get('METHOD', 'oauth2')

    def get_login_url(self, request, **kwargs):
        method = kwargs.get('method', self.get_method())
        if method == 'js_sdk':
            next = "'%s'" % escapejs(kwargs.get('next') or '')
            process = "'%s'" % escapejs(kwargs.get('process') or AuthProcess.LOGIN)
            action = "'%s'" % escapejs(kwargs.get('action') or AuthAction.AUTHENTICATE)
            ret = "javascript:allauth.facebook.login(%s, %s, %s)" \
                % (next, action, process)
        else:
            assert method == 'oauth2'
            ret = super(FacebookProvider, self).get_login_url(request,
                                                              **kwargs)
        return ret

    def _get_locale_callable(self):
        settings = self.get_settings()
        f = settings.get('LOCALE_FUNC')
        if f:
            f = import_callable(f)
        else:
            f = get_default_locale_callable()
        return f

    def get_locale_for_request(self, request):
        if not self._locale_callable_cache:
            self._locale_callable_cache = self._get_locale_callable()
        return self._locale_callable_cache(request)

    def get_default_scope(self):
        scope = []
        if QUERY_EMAIL:
            scope.append('email')
        return scope

    def get_auth_params(self, request, action):
        ret = super(FacebookProvider, self).get_auth_params(request,
                                                            action)
        if action == AuthAction.REAUTHENTICATE:
            ret['auth_type'] = 'reauthenticate'
        return ret

    def get_fb_login_options(self, request):
        ret = self.get_auth_params(request, 'authenticate')
        ret['scope'] = ','.join(self.get_scope())
        if ret.get('auth_type') == 'reauthenticate':
            ret['auth_nonce'] = self.get_nonce(request, or_create=True)
        return ret

    def media_js(self, request):
        locale = self.get_locale_for_request(request)
        try:
            app = self.get_app(request)
        except SocialApp.DoesNotExist:
            raise ImproperlyConfigured("No Facebook app configured: please"
                                       " add a SocialApp using the Django"
                                       " admin")
        fb_login_options = self.get_fb_login_options(request)
        ctx = {'facebook_app': app,
               'facebook_channel_url':
               request.build_absolute_uri(reverse('facebook_channel')),
               'fb_login_options': mark_safe(json.dumps(fb_login_options)),
               'facebook_jssdk_locale': locale}
        return render_to_string('facebook/fbconnect.html',
                                ctx,
                                RequestContext(request))

    def get_nonce(self, request, or_create=False, pop=False):
        if pop:
            nonce = request.session.pop(NONCE_SESSION_KEY, None)
        else:
            nonce = request.session.get(NONCE_SESSION_KEY)
        if not nonce and or_create:
            nonce = get_random_string(32)
            request.session[NONCE_SESSION_KEY] = nonce
        return nonce

    def extract_uid(self, data):
        return data['id']

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    username=data.get('username'),
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'))

    def extract_email_addresses(self, data):
        ret = []
        email = data.get('email')
        if email:
            # data['verified'] does not imply the email address is
            # verified.
            ret.append(EmailAddress(email=email,
                                    verified=False,
                                    primary=True))
        return ret

providers.registry.register(FacebookProvider)

########NEW FILE########
__FILENAME__ = tests
try:
    from mock import patch
except ImportError:
    from unittest.mock import patch
import json

from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.test.client import RequestFactory

from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount import providers
from allauth.socialaccount.providers import registry
from allauth.account import app_settings as account_settings
from allauth.account.models import EmailAddress
from allauth.utils import get_user_model

from .provider import FacebookProvider


@override_settings(
    SOCIALACCOUNT_AUTO_SIGNUP=True,
    ACCOUNT_SIGNUP_FORM_CLASS=None,
    LOGIN_REDIRECT_URL='/accounts/profile/',
    ACCOUNT_EMAIL_VERIFICATION=account_settings
    .EmailVerificationMethod.NONE,
    SOCIALACCOUNT_PROVIDERS={
        'facebook': {
            'AUTH_PARAMS': {},
            'VERIFIED_EMAIL': False}})
class FacebookTests(create_oauth2_tests(registry.by_id(FacebookProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
           "id": "630595557",
           "name": "Raymond Penners",
           "first_name": "Raymond",
           "last_name": "Penners",
           "email": "raymond.penners@gmail.com",
           "link": "https://www.facebook.com/raymond.penners",
           "username": "raymond.penners",
           "birthday": "07/17/1973",
           "work": [
              {
                 "employer": {
                    "id": "204953799537777",
                    "name": "IntenCT"
                 }
              }
           ],
           "timezone": 1,
           "locale": "nl_NL",
           "verified": true,
           "updated_time": "2012-11-30T20:40:33+0000"
        }""")

    def test_username_conflict(self):
        User = get_user_model()
        User.objects.create(username='raymond.penners')
        self.login(self.get_mocked_response())
        socialaccount = SocialAccount.objects.get(uid='630595557')
        self.assertEqual(socialaccount.user.username, 'raymond')

    def test_username_based_on_provider(self):
        self.login(self.get_mocked_response())
        socialaccount = SocialAccount.objects.get(uid='630595557')
        self.assertEqual(socialaccount.user.username, 'raymond.penners')

    def test_media_js(self):
        provider = providers.registry.by_id(FacebookProvider.id)
        request = RequestFactory().get(reverse('account_login'))
        request.session = {}
        script = provider.media_js(request)
        self.assertTrue("appId: 'app123id'" in script)

    def test_login_by_token(self):
        resp = self.client.get(reverse('account_login'))
        with patch('allauth.socialaccount.providers.facebook.views'
                   '.requests') as requests_mock:
            mocks = [self.get_mocked_response().json()]
            requests_mock.get.return_value.json \
                = lambda: mocks.pop()
            resp = self.client.post(reverse('facebook_login_by_token'),
                                    data={'access_token': 'dummy'})
            self.assertEqual('http://testserver/accounts/profile/',
                             resp['location'])

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            'facebook': {
                'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
                'VERIFIED_EMAIL': False}})
    def test_login_by_token_reauthenticate(self):
        resp = self.client.get(reverse('account_login'))
        nonce = json.loads(resp.context['fb_login_options'])['auth_nonce']
        with patch('allauth.socialaccount.providers.facebook.views'
                   '.requests') as requests_mock:
            mocks = [self.get_mocked_response().json(),
                     {'auth_nonce': nonce}]
            requests_mock.get.return_value.json \
                = lambda: mocks.pop()
            resp = self.client.post(reverse('facebook_login_by_token'),
                                    data={'access_token': 'dummy'})
            self.assertEqual('http://testserver/accounts/profile/',
                             resp['location'])

    def test_channel(self):
        resp = self.client.get(reverse('facebook_channel'))
        self.assertTemplateUsed(resp, 'facebook/channel.html')

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            'facebook': {
                'VERIFIED_EMAIL': True}})
    def test_login_verified(self):
        emailaddress = self._login_verified()
        self.assertTrue(emailaddress.verified)

    def test_login_unverified(self):
        emailaddress = self._login_verified()
        self.assertFalse(emailaddress.verified)

    def _login_verified(self):
        resp = self.login(self.get_mocked_response())
        return EmailAddress.objects.get(email='raymond.penners@gmail.com')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import FacebookProvider
from . import views

urlpatterns = default_urlpatterns(FacebookProvider)

urlpatterns += patterns('',
   url('^facebook/login/token/$', views.login_by_token, 
       name="facebook_login_by_token"),
   url('^facebook/channel/$', views.channel, name='facebook_channel'),
   )

########NEW FILE########
__FILENAME__ = views
import logging
import requests

from django.utils.cache import patch_response_headers
from django.shortcuts import render


from allauth.socialaccount.models import (SocialLogin,
                                          SocialToken)
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .forms import FacebookConnectForm
from .provider import FacebookProvider


logger = logging.getLogger(__name__)


def fb_complete_login(request, app, token):
    resp = requests.get('https://graph.facebook.com/me',
                        params={'access_token': token.token})
    resp.raise_for_status()
    extra_data = resp.json()
    login = providers.registry \
        .by_id(FacebookProvider.id) \
        .sociallogin_from_response(request, extra_data)
    return login


class FacebookOAuth2Adapter(OAuth2Adapter):
    provider_id = FacebookProvider.id

    authorize_url = 'https://www.facebook.com/dialog/oauth'
    access_token_url = 'https://graph.facebook.com/oauth/access_token'
    expires_in_key = 'expires'

    def complete_login(self, request, app, access_token, **kwargs):
        return fb_complete_login(request, app, access_token)


oauth2_login = OAuth2LoginView.adapter_view(FacebookOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(FacebookOAuth2Adapter)


def login_by_token(request):
    ret = None
    if request.method == 'POST':
        form = FacebookConnectForm(request.POST)
        if form.is_valid():
            try:
                provider = providers.registry.by_id(FacebookProvider.id)
                login_options = provider.get_fb_login_options(request)
                app = providers.registry.by_id(FacebookProvider.id) \
                    .get_app(request)
                access_token = form.cleaned_data['access_token']
                if login_options.get('auth_type') == 'reauthenticate':
                    info = requests.get(
                        'https://graph.facebook.com/oauth/access_token_info',
                        params={'client_id': app.client_id,
                                'access_token': access_token}).json()
                    nonce = provider.get_nonce(request, pop=True)
                    ok = nonce and nonce == info.get('auth_nonce')
                else:
                    ok = True
                if ok:
                    token = SocialToken(app=app,
                                        token=access_token)
                    login = fb_complete_login(request, app, token)
                    login.token = token
                    login.state = SocialLogin.state_from_request(request)
                    ret = complete_social_login(request, login)
            except requests.RequestException:
                logger.exception('Error accessing FB user profile')
    if not ret:
        ret = render_authentication_error(request)
    return ret


def channel(request):
    provider = providers.registry.by_id(FacebookProvider.id)
    locale = provider.get_locale_for_request(request)
    response = render(request, 'facebook/channel.html',
                      {'facebook_jssdk_locale': locale})
    cache_expire = 60 * 60 * 24 * 365
    patch_response_headers(response, cache_expire)
    response['Pragma'] = 'Public'
    return response

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from __future__ import unicode_literals

from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class FeedlyAccount(ProviderAccount):
    def get_avatar_url(self):
        return self.account.extra_data.get('picture')

    def to_str(self):
        name = '{0} {1}'.format(self.account.extra_data.get('givenName', ''),
                                self.account.extra_data.get('familyName', ''))
        if name.strip() != '':
            return name
        return super(FeedlyAccount, self).to_str()


class FeedlyProvider(OAuth2Provider):
    id = str('feedly')
    name = 'Feedly'
    package = 'allauth.socialaccount.providers.feedly'
    account_class = FeedlyAccount

    def get_default_scope(self):
        return ['https://cloud.feedly.com/subscriptions']

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    last_name=data.get('familyName'),
                    first_name=data.get('givenName'))

providers.registry.register(FeedlyProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import FeedlyProvider

class FeedlyTests(create_oauth2_tests(registry.by_id(FeedlyProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
          "id": "c805fcbf-3acf-4302-a97e-d82f9d7c897f",
          "email": "jim.smith@gmail.com",
          "givenName": "Jim",
          "familyName": "Smith",
          "picture": "https://www.google.com/profile_images/1771656873/bigger.jpg",
          "gender": "male",
          "locale": "en",
          "reader": "9080770707070700",
          "google": "115562565652656565656",
          "twitter": "jimsmith",
          "facebook": "",
          "wave": "2013.7"
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import FeedlyProvider

urlpatterns = default_urlpatterns(FeedlyProvider)

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import requests
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from .provider import FeedlyProvider


class FeedlyOAuth2Adapter(OAuth2Adapter):
    provider_id = FeedlyProvider.id
    access_token_url = 'https://cloud.feedly.com/v3/auth/token'
    authorize_url = 'https://cloud.feedly.com/v3/auth/auth'
    profile_url = 'https://cloud.feedly.com/v3/profile'

    def complete_login(self, request, app, token, **kwargs):
        headers = {'Authorization': 'OAuth {0}'.format(token.token)}
        resp = requests.get(self.profile_url, headers=headers)
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(FeedlyOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(FeedlyOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class FlickrAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data \
            .get('person').get('profileurl').get('_content')

    def get_avatar_url(self):
        return self.account.extra_data.get('picture-url')

    def to_str(self):
        dflt = super(FlickrAccount, self).to_str()
        name = self.account.extra_data \
            .get('person').get('realname').get('_content', dflt)
        return name


class FlickrProvider(OAuthProvider):
    id = 'flickr'
    name = 'Flickr'
    package = 'allauth.socialaccount.providers.flickr'
    account_class = FlickrAccount

    def get_default_scope(self):
        scope = []
        return scope

    def get_profile_fields(self):
        default_fields = ['id',
                          'first-name',
                          'last-name',
                          'email-address',
                          'picture-url',
                          'public-profile-url']
        fields = self.get_settings().get('PROFILE_FIELDS',
                                         default_fields)
        return fields

    def extract_uid(self, data):
        return data['person']['nsid']

    def extract_common_fields(self, data):
        name = data.get('person').get('realname').get('_content')
        return dict(email=data.get('email-address'),
                    name=name)


providers.registry.register(FlickrProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import FlickrProvider


class FlickrTests(create_oauth_tests(registry.by_id(FlickrProvider.id))):
    def get_mocked_response(self):
        #
        return [
            MockedResponse(200, r"""
 {"stat": "ok", "user": {"username": {"_content": "pennersr"}, "id": "12345678@N00"}}
"""),  # noqa
            MockedResponse(200, r"""
{"person": {"username": {"_content": "pennersr"}, "photosurl": {"_content": "http://www.flickr.com/photos/12345678@N00/"}, "nsid": "12345678@N00", "path_alias": null, "photos": {"count": {"_content": 0}, "firstdatetaken": {"_content": null}, "views": {"_content": "28"}, "firstdate": {"_content": null}}, "iconserver": "0", "description": {"_content": ""}, "mobileurl": {"_content": "http://m.flickr.com/photostream.gne?id=6294613"}, "profileurl": {"_content": "http://www.flickr.com/people/12345678@N00/"}, "mbox_sha1sum": {"_content": "5e5b359c123e54f95236209c8808d607a5cdd21e"}, "ispro": 0, "location": {"_content": ""}, "id": "12345678@N00", "realname": {"_content": "raymond penners"}, "iconfarm": 0}, "stat": "ok"}
""")]  # noqa

    def test_login(self):
        account = super(FlickrTests, self).test_login()
        f_account = account.get_provider_account()
        self.assertEqual(account.user.first_name,
                         'raymond')
        self.assertEqual(account.user.last_name,
                         'penners')
        self.assertEqual(f_account.get_profile_url(),
                         'http://www.flickr.com/people/12345678@N00/')

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import FlickrProvider


urlpatterns = default_urlpatterns(FlickrProvider)

########NEW FILE########
__FILENAME__ = views
import json
from django.utils.http import urlencode

from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (
    OAuthAdapter,
    OAuthLoginView,
    OAuthCallbackView)

from .provider import FlickrProvider


class FlickrAPI(OAuth):

    api_url = 'http://api.flickr.com/services/rest'

    def get_user_info(self):
        default_params = {'nojsoncallback': '1',
                          'format': 'json'}
        p = dict({'method': 'flickr.test.login'},
                 **default_params)
        u = json.loads(self.query(self.api_url + '?' + urlencode(p)))

        p = dict({'method': 'flickr.people.getInfo',
                  'user_id': u['user']['id']},
                 **default_params)
        user = json.loads(
            self.query(self.api_url + '?' + urlencode(p)))
        return user


class FlickrOAuthAdapter(OAuthAdapter):
    provider_id = FlickrProvider.id
    request_token_url = 'http://www.flickr.com/services/oauth/request_token'
    access_token_url = 'http://www.flickr.com/services/oauth/access_token'
    authorize_url = 'http://www.flickr.com/services/oauth/authorize'

    def complete_login(self, request, app, token):
        client = FlickrAPI(request, app.client_id, app.secret,
                           self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)

oauth_login = OAuthLoginView.adapter_view(FlickrOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(FlickrOAuthAdapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class FoursquareAccount(ProviderAccount):
    def get_profile_url(self):
        return 'https://foursquare.com/user/' \
            + self.account.extra_data.get('id')

    def get_avatar_url(self):
        return self.account.extra_data.get('photo')


class FoursquareProvider(OAuth2Provider):
    id = 'foursquare'
    name = 'Foursquare'
    package = 'allauth.socialaccount.providers.foursquare'
    account_class = FoursquareAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(first_name=data.get('firstname'),
                    last_name=data.get('lastname'),
                    email=data.get('contact').get('email'))


providers.registry.register(FoursquareProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import FoursquareProvider

class FoursquareTests(create_oauth2_tests(registry.by_id(FoursquareProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
                              {
                                "notifications": [{"item": {"unreadCount": 0}, "type": "notificationTray"}],
                                "meta": {"code": 200},
                                "response":
                                {
                                    "user":
                                    {
                                        "photo": {"prefix": "https://irs0.4sqi.net/img/user/", "suffix": "/blank_boy.png"},
                                        "pings": false,
                                        "homeCity": "Athens, ESYE31",
                                        "id": "76077726",
                                        "badges": {"count": 0, "items": []},
                                        "referralId": "u-76077726",
                                        "friends":
                                        {
                                            "count": 0,
                                            "groups": [{"count": 0, "items": [], "type": "friends", "name": "Mutual friends"}, {"count": 0, "items": [], "type": "others", "name": "Other friends"}]
                                        },
                                        "createdAt": 1389624445,
                                        "tips": {"count": 0},
                                        "type": "user",
                                        "bio": "",
                                        "relationship": "self",
                                        "lists":
                                        {
                                            "count": 1,
                                            "groups": [{"count": 1, "items": [{"description": "", "collaborative": false, "url": "/user/76077726/list/todos", "editable": false, "listItems": {"count": 0}, "id": "76077726/todos", "followers": {"count": 0}, "user": {"gender": "male", "firstName": "\u03a1\u03c9\u03bc\u03b1\u03bd\u03cc\u03c2", "relationship": "self", "photo": {"prefix": "https://irs0.4sqi.net/img/user/", "suffix": "/blank_boy.png"}, "lastName": "\u03a4\u03c3\u03bf\u03c5\u03c1\u03bf\u03c0\u03bb\u03ae\u03c2", "id": "76077726"}, "public": false, "canonicalUrl": "https://foursquare.com/user/76077726/list/todos", "name": "My to-do list"}], "type": "created"}, {"count": 0, "items": [], "type": "followed"}]
                                        },
                                        "photos": {"count": 0, "items": []},
                                        "checkinPings": "off",
                                        "scores": {"max": 0, "checkinsCount": 0, "goal": 50, "recent": 0},
                                        "checkins": {"count": 0, "items": []},
                                        "firstName": "\u03a1\u03c9\u03bc\u03b1\u03bd\u03cc\u03c2",
                                        "gender": "male",
                                        "contact": {"email": "romdimtsouroplis@gmail.com"},
                                        "lastName": "\u03a4\u03c3\u03bf\u03c5\u03c1\u03bf\u03c0\u03bb\u03ae\u03c2",
                                        "following": {"count": 0, "groups": [{"count": 0, "items": [], "type": "following", "name": "Mutual following"}, {"count": 0, "items": [], "type": "others", "name": "Other following"}]},
                                        "requests": {"count": 0}, "mayorships": {"count": 0, "items": []}}
                                    }
                                 }
""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import FoursquareProvider

urlpatterns = default_urlpatterns(FoursquareProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import FoursquareProvider


class FoursquareOAuth2Adapter(OAuth2Adapter):
    provider_id = FoursquareProvider.id
    access_token_url = 'https://foursquare.com/oauth2/access_token'
    # Issue ?? -- this one authenticates over and over again...
    # authorize_url = 'https://foursquare.com/oauth2/authorize'
    authorize_url = 'https://foursquare.com/oauth2/authenticate'
    profile_url = 'https://api.foursquare.com/v2/users/self'

    def complete_login(self, request, app, token, **kwargs):
        # Foursquare needs a version number for their API requests as documented here https://developer.foursquare.com/overview/versioning
        resp = requests.get(self.profile_url,
                            params={'oauth_token': token.token, 'v': '20140116'})
        extra_data = resp.json()['response']['user']
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(FoursquareOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(FoursquareOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class GitHubAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('html_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar_url')

    def to_str(self):
        dflt = super(GitHubAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class GitHubProvider(OAuth2Provider):
    id = 'github'
    name = 'GitHub'
    package = 'allauth.socialaccount.providers.github'
    account_class = GitHubAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    username=data.get('login'),
                    name=data.get('name'))


providers.registry.register(GitHubProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import GitHubProvider

class GitHubTests(create_oauth2_tests(registry.by_id(GitHubProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
            "type":"User",
            "organizations_url":"https://api.github.com/users/pennersr/orgs",
            "gists_url":"https://api.github.com/users/pennersr/gists{/gist_id}",
            "received_events_url":"https://api.github.com/users/pennersr/received_events",
            "gravatar_id":"8639768262b8484f6a3380f8db2efa5b",
            "followers":16,
            "blog":"http://www.intenct.info",
            "avatar_url":"https://secure.gravatar.com/avatar/8639768262b8484f6a3380f8db2efa5b?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
            "login":"pennersr",
            "created_at":"2010-02-10T12:50:51Z",
            "company":"IntenCT",
            "subscriptions_url":"https://api.github.com/users/pennersr/subscriptions",
            "public_repos":14,
            "hireable":false,
            "url":"https://api.github.com/users/pennersr",
            "public_gists":0,
            "starred_url":"https://api.github.com/users/pennersr/starred{/owner}{/repo}",
            "html_url":"https://github.com/pennersr",
            "location":"The Netherlands",
            "bio":null,
            "name":"Raymond Penners",
            "repos_url":"https://api.github.com/users/pennersr/repos",
            "followers_url":"https://api.github.com/users/pennersr/followers",
            "id":201022,
            "following":0,
            "email":"raymond.penners@intenct.nl",
            "events_url":"https://api.github.com/users/pennersr/events{/privacy}",
            "following_url":"https://api.github.com/users/pennersr/following"
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import GitHubProvider

urlpatterns = default_urlpatterns(GitHubProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from .provider import GitHubProvider


class GitHubOAuth2Adapter(OAuth2Adapter):
    provider_id = GitHubProvider.id
    access_token_url = 'https://github.com/login/oauth/access_token'
    authorize_url = 'https://github.com/login/oauth/authorize'
    profile_url = 'https://api.github.com/user'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(GitHubOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(GitHubOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.account.models import EmailAddress
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import (ProviderAccount,
                                                  AuthAction)
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.app_settings import QUERY_EMAIL
from allauth.account.utils import user_email


class Scope(object):
    USERINFO_PROFILE = 'https://www.googleapis.com/auth/userinfo.profile'
    USERINFO_EMAIL = 'https://www.googleapis.com/auth/userinfo.email'


class GoogleAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('link')

    def get_avatar_url(self):
        return self.account.extra_data.get('picture')

    def to_str(self):
        dflt = super(GoogleAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class GoogleProvider(OAuth2Provider):
    id = 'google'
    name = 'Google'
    package = 'allauth.socialaccount.providers.google'
    account_class = GoogleAccount

    def get_default_scope(self):
        scope = [Scope.USERINFO_PROFILE]
        if QUERY_EMAIL:
            scope.append(Scope.USERINFO_EMAIL)
        return scope

    def get_auth_params(self, request, action):
        ret = super(GoogleProvider, self).get_auth_params(request,
                                                          action)
        if action == AuthAction.REAUTHENTICATE:
            ret['approval_prompt'] = 'force'
        return ret

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    last_name=data.get('family_name'),
                    first_name=data.get('given_name'))

    def extract_email_addresses(self, data):
        ret = []
        email = data.get('email')
        if email and data.get('verified_email'):
            ret.append(EmailAddress(email=email,
                       verified=True,
                       primary=True))
        return ret


providers.registry.register(GoogleProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.importlib import import_module
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.core import mail

from allauth.socialaccount.tests import create_oauth2_tests
from allauth.account import app_settings as account_settings
from allauth.account.models import EmailConfirmation, EmailAddress
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers import registry
from allauth.tests import MockedResponse
from allauth.account.signals import user_signed_up
from allauth.account.adapter import get_adapter

from .provider import GoogleProvider


@override_settings(SOCIALACCOUNT_AUTO_SIGNUP=True,
                   ACCOUNT_SIGNUP_FORM_CLASS=None,
                   ACCOUNT_EMAIL_VERIFICATION \
                   =account_settings.EmailVerificationMethod.MANDATORY)
class GoogleTests(create_oauth2_tests(registry.by_id(GoogleProvider.id))):

    def get_mocked_response(self,
                            family_name='Penners',
                            given_name='Raymond',
                            name='Raymond Penners',
                            email='raymond.penners@gmail.com',
                            verified_email=True):
        return MockedResponse(200, """
              {"family_name": "%s", "name": "%s",
               "picture": "https://lh5.googleusercontent.com/-GOFYGBVOdBQ/AAAAAAAAAAI/AAAAAAAAAGM/WzRfPkv4xbo/photo.jpg",
               "locale": "nl", "gender": "male",
               "email": "%s",
               "link": "https://plus.google.com/108204268033311374519",
               "given_name": "%s", "id": "108204268033311374519",
               "verified_email": %s }
        """ % (family_name,
               name,
               email,
               given_name,
               (repr(verified_email).lower())))

    def test_username_based_on_email(self):
        first_name = u'明'
        last_name = u'小'
        email = 'raymond.penners@gmail.com'
        self.login(self.get_mocked_response(name=first_name + ' ' + last_name,
                                            email=email,
                                            given_name=first_name,
                                            family_name=last_name,
                                            verified_email=True))
        user = User.objects.get(email=email)
        self.assertEqual(user.username, 'raymond.penners')

    def test_email_verified(self):
        test_email = 'raymond.penners@gmail.com'
        self.login(self.get_mocked_response(verified_email=True))
        email_address = EmailAddress.objects \
            .get(email=test_email,
                 verified=True)
        self.assertFalse(EmailConfirmation.objects
                         .filter(email_address__email=test_email)
                         .exists())
        account = email_address.user.socialaccount_set.all()[0]
        self.assertEqual(account.extra_data['given_name'], 'Raymond')

    def test_user_signed_up_signal(self):
        sent_signals = []

        def on_signed_up(sender, request, user, **kwargs):
            sociallogin = kwargs['sociallogin']
            self.assertEqual(sociallogin.account.provider,
                             GoogleProvider.id)
            self.assertEqual(sociallogin.account.user,
                             user)
            sent_signals.append(sender)

        user_signed_up.connect(on_signed_up)
        self.login(self.get_mocked_response(verified_email=True))
        self.assertTrue(len(sent_signals) > 0)

    def test_email_unverified(self):
        test_email = 'raymond.penners@gmail.com'
        resp = self.login(self.get_mocked_response(verified_email=False))
        email_address = EmailAddress.objects \
            .get(email=test_email)
        self.assertFalse(email_address.verified)
        self.assertTrue(EmailConfirmation.objects
                        .filter(email_address__email=test_email)
                        .exists())
        self.assertTemplateUsed(resp,
                                'account/email/email_confirmation_signup_subject.txt')

    def test_email_verified_stashed(self):
        # http://slacy.com/blog/2012/01/how-to-set-session-variables-in-django-unit-tests/
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key
        request = RequestFactory().get('/')
        request.session = self.client.session
        adapter = get_adapter()
        test_email = 'raymond.penners@gmail.com'
        adapter.stash_verified_email(request, test_email)
        request.session.save()

        self.login(self.get_mocked_response(verified_email=False))
        email_address = EmailAddress.objects \
            .get(email=test_email)
        self.assertTrue(email_address.verified)
        self.assertFalse(EmailConfirmation.objects \
                             .filter(email_address__email=test_email) \
                             .exists())


    def test_account_connect(self):
        email = 'some@mail.com'
        user = User.objects.create(username='user',
                                   is_active=True,
                                   email=email)
        user.set_password('test')
        user.save()
        EmailAddress.objects.create(user=user,
                                    email=email,
                                    primary=True,
                                    verified=True)
        self.client.login(username=user.username,
                          password='test')
        self.login(self.get_mocked_response(verified_email=True),
                   process='connect')
        # Check if we connected...
        self.assertTrue(SocialAccount.objects.filter(user=user,
                                                     provider=GoogleProvider.id).exists())
        # For now, we do not pick up any new e-mail addresses on connect
        self.assertEqual(EmailAddress.objects.filter(user=user).count(), 1)
        self.assertEqual(EmailAddress.objects.filter(user=user,
                                                      email=email).count(), 1)

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.MANDATORY,
        SOCIALACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.NONE
    )
    def test_social_email_verification_skipped(self):
        test_email = 'raymond.penners@gmail.com'
        self.login(self.get_mocked_response(verified_email=False))
        email_address = EmailAddress.objects \
            .get(email=test_email)
        self.assertFalse(email_address.verified)
        self.assertFalse(EmailConfirmation.objects \
                            .filter(email_address__email=test_email) \
                            .exists())

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.OPTIONAL,
        SOCIALACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.OPTIONAL
    )
    def test_social_email_verification_optional(self):
        self.login(self.get_mocked_response(verified_email=False))
        self.assertEqual(len(mail.outbox), 1)
        self.login(self.get_mocked_response(verified_email=False))
        self.assertEqual(len(mail.outbox), 1)

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import GoogleProvider

urlpatterns = default_urlpatterns(GoogleProvider)

########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import GoogleProvider


class GoogleOAuth2Adapter(OAuth2Adapter):
    provider_id = GoogleProvider.id
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    authorize_url = 'https://accounts.google.com/o/oauth2/auth'
    profile_url = 'https://www.googleapis.com/oauth2/v1/userinfo'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token,
                                    'alt': 'json'})
        extra_data = resp.json()
        login = self.get_provider() \
            .sociallogin_from_response(request,
                                       extra_data)
        return login


oauth2_login = OAuth2LoginView.adapter_view(GoogleOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(GoogleOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class HubicAccount(ProviderAccount):
    pass


class HubicProvider(OAuth2Provider):
    id = 'hubic'
    name = 'Hubic'
    package = 'allauth.socialaccount.providers.hubic'
    account_class = HubicAccount

    def extract_uid(self, data):
        return str(data['email'])

    def extract_common_fields(self, data):
        return dict(email=data.get('email'),
                    username=data.get('firstname').lower()+data.get('lastname').lower(),
                    first_name=data.get('firstname'),
                    last_name=data.get('lastname'))

providers.registry.register(HubicProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import HubicProvider

class HubicTests(create_oauth2_tests(registry.by_id(HubicProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
{
    "email": "asdf@asdf.com",
    "firstname": "Test",
    "activated": true,
    "creationDate": "2014-04-17T17:04:01+02:00",
    "language": "en",
    "status": "ok",
    "offer": "25g",
    "lastname": "User"
}
""")

    def get_login_response_json(self, with_refresh_token=True):
        return '{\
    "access_token": "testac",\
    "expires_in": "3600",\
    "refresh_token": "testrf",\
    "token_type": "Bearer"\
}'

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import HubicProvider

urlpatterns = default_urlpatterns(HubicProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import HubicProvider


class HubicOAuth2Adapter(OAuth2Adapter):
    provider_id = HubicProvider.id
    access_token_url = 'https://api.hubic.com/oauth/token'
    authorize_url = 'https://api.hubic.com/oauth/auth'
    profile_url = 'https://api.hubic.com/1.0/account'
    redirect_uri_protocol = 'https'

    def complete_login(self, request, app, token, **kwargs):
        token_type = kwargs['response']['token_type']
        resp = requests.get(self.profile_url,
                            headers={'Authorization': '%s %s' % (token_type, token.token)})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(HubicOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(HubicOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class InstagramAccount(ProviderAccount):

    PROFILE_URL = 'http://instagram.com/'

    def get_profile_url(self):
        return self.PROFILE_URL + self.account.extra_data.get('username')

    def get_avatar_url(self):
        return self.account.extra_data.get('profile_picture')

    def to_str(self):
        dflt = super(InstagramAccount, self).to_str()
        return self.account.extra_data.get('username', dflt)


class InstagramProvider(OAuth2Provider):
    id = 'instagram'
    name = 'Instagram'
    package = 'allauth.socialaccount.providers.instagram'
    account_class = InstagramAccount

    def extract_extra_data(self, data):
        return data.get('data', {})

    def get_default_scope(self):
        return ['basic']

    def extract_uid(self, data):
        return str(data['data']['id'])

    def extract_common_fields(self, data):
        return dict(username=data['data'].get('username'))


providers.registry.register(InstagramProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import InstagramProvider

class InstagramTests(create_oauth2_tests(registry.by_id(InstagramProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
          "meta": {
            "code": 200
          },
          "data": {
            "username": "georgewhewell",
            "bio": "",
            "website": "",
            "profile_picture": "http://images.ak.instagram.com/profiles/profile_11428116_75sq_1339547159.jpg",
            "full_name": "georgewhewell",
            "counts": {
              "media": 74,
              "followed_by": 91,
              "follows": 104
            },
            "id": "11428116"
          }
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import InstagramProvider

urlpatterns = default_urlpatterns(InstagramProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from .provider import InstagramProvider


class InstagramOAuth2Adapter(OAuth2Adapter):
    provider_id = InstagramProvider.id
    access_token_url = 'https://instagram.com/oauth/access_token'
    authorize_url = 'https://instagram.com/oauth/authorize'
    profile_url = 'https://api.instagram.com/v1/users/self'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(InstagramOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(InstagramOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider

from allauth.socialaccount import app_settings


class LinkedInAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('public-profile-url')

    def get_avatar_url(self):
        return self.account.extra_data.get('picture-url')

    def to_str(self):
        dflt = super(LinkedInAccount, self).to_str()
        name = self.account.extra_data.get('name', dflt)
        first_name = self.account.extra_data.get('first-name', None)
        last_name = self.account.extra_data.get('last-name', None)
        if first_name and last_name:
            name = first_name+' '+last_name
        return name


class LinkedInProvider(OAuthProvider):
    id = 'linkedin'
    name = 'LinkedIn'
    package = 'allauth.socialaccount.providers.linkedin'
    account_class = LinkedInAccount

    def get_default_scope(self):
        scope = []
        if app_settings.QUERY_EMAIL:
            scope.append('r_emailaddress')
        return scope

    def get_profile_fields(self):
        default_fields = ['id',
                          'first-name',
                          'last-name',
                          'email-address',
                          'picture-url',
                          'public-profile-url']
        fields = self.get_settings().get('PROFILE_FIELDS',
                                         default_fields)
        return fields

    def extract_uid(self, data):
        return data['id']

    def extract_common_fields(self, data):
        return dict(email=data.get('email-address'),
                    first_name=data.get('first-name'),
                    last_name=data.get('last-name'))

providers.registry.register(LinkedInProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import LinkedInProvider


class LinkedInTests(create_oauth_tests(registry.by_id(LinkedInProvider.id))):
    def get_mocked_response(self):
        return [MockedResponse(200, u"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<person>
  <id>oKmTqN2ffc</id>
  <first-name>R@ymØnd</first-name>
  <last-name>Pènnèrs</last-name>
  <email-address>raymond.penners@intenct.nl</email-address>
  <picture-url>http://m.c.lnkd.licdn.com/mpr/mprx/0_e0hbvSLc8QWo3ggPeVKqvaFR860d342Pogq4vakwx8IJOyR1XJrwRmr5mIx9C0DxWpGMsW9Lb8EQ</picture-url>
  <public-profile-url>http://www.linkedin.com/in/intenct</public-profile-url>
</person>
""")]

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import LinkedInProvider

urlpatterns = default_urlpatterns(LinkedInProvider)

########NEW FILE########
__FILENAME__ = views
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

from django.utils import six

from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)

from .provider import LinkedInProvider


class LinkedInAPI(OAuth):
    url = 'https://api.linkedin.com/v1/people/~'

    def get_user_info(self):
        fields = providers.registry \
            .by_id(LinkedInProvider.id) \
            .get_profile_fields()
        url = self.url + ':(%s)' % ','.join(fields)
        raw_xml = self.query(url)
        if not six.PY3:
            raw_xml = raw_xml.encode('utf8')
        try:
            return self.to_dict(ElementTree.fromstring(raw_xml))
        except (ExpatError, KeyError, IndexError):
            return None

    def to_dict(self, xml):
        """
        Convert XML structure to dict recursively, repeated keys
        entries are returned as in list containers.
        """
        children = list(xml)
        if not children:
            return xml.text
        else:
            out = {}
            for node in list(xml):
                if node.tag in out:
                    if not isinstance(out[node.tag], list):
                        out[node.tag] = [out[node.tag]]
                    out[node.tag].append(self.to_dict(node))
                else:
                    out[node.tag] = self.to_dict(node)
            return out


class LinkedInOAuthAdapter(OAuthAdapter):
    provider_id = LinkedInProvider.id
    request_token_url = 'https://api.linkedin.com/uas/oauth/requestToken'
    access_token_url = 'https://api.linkedin.com/uas/oauth/accessToken'
    authorize_url = 'https://www.linkedin.com/uas/oauth/authenticate'

    def complete_login(self, request, app, token):
        client = LinkedInAPI(request, app.client_id, app.secret,
                             self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)

oauth_login = OAuthLoginView.adapter_view(LinkedInOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(LinkedInOAuthAdapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount import app_settings


class LinkedInOAuth2Account(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('publicProfileUrl')

    def get_avatar_url(self):
        return self.account.extra_data.get('pictureUrl')

    def to_str(self):
        dflt = super(LinkedInOAuth2Account, self).to_str()
        name = self.account.extra_data.get('name', dflt)
        first_name = self.account.extra_data.get('firstName', None)
        last_name = self.account.extra_data.get('lastName', None)
        if first_name and last_name:
            name = first_name+' '+last_name
        return name


class LinkedInOAuth2Provider(OAuth2Provider):
    id = 'linkedin_oauth2'
    # Name is displayed to ordinary users -- don't include protocol
    name = 'LinkedIn'
    package = 'allauth.socialaccount.providers.linkedin_oauth2'
    account_class = LinkedInOAuth2Account

    def extract_uid(self, data):
        return str(data['id'])

    def get_profile_fields(self):
        default_fields = ['id',
                          'first-name',
                          'last-name',
                          'email-address',
                          'picture-url',
                          'public-profile-url']
        fields = self.get_settings().get('PROFILE_FIELDS',
                                         default_fields)
        return fields

    def get_default_scope(self):
        scope = []
        if app_settings.QUERY_EMAIL:
            scope.append('r_emailaddress')
        return scope

    def extract_common_fields(self, data):
        return dict(email=data.get('emailAddress'),
                    first_name=data.get('firstName'),
                    last_name=data.get('lastName'))


providers.registry.register(LinkedInOAuth2Provider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import LinkedInOAuth2Provider


class LinkedInOAuth2Tests(create_oauth2_tests(
        registry.by_id(LinkedInOAuth2Provider.id))):

    def get_mocked_response(self):
        return MockedResponse(200, """
{
  "emailAddress": "raymond.penners@intenct.nl",
  "firstName": "Raymond",
  "id": "ZLARGMFT1M",
  "lastName": "Penners",
  "pictureUrl": "http://m.c.lnkd.licdn.com/mpr/mprx/0_e0hbvSLc",
  "publicProfileUrl": "http://www.linkedin.com/in/intenct"
}
""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import LinkedInOAuth2Provider

urlpatterns = default_urlpatterns(LinkedInOAuth2Provider)


########NEW FILE########
__FILENAME__ = views
import requests
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import LinkedInOAuth2Provider

class LinkedInOAuth2Adapter(OAuth2Adapter):
    provider_id = LinkedInOAuth2Provider.id
    access_token_url = 'https://api.linkedin.com/uas/oauth2/accessToken'
    authorize_url = 'https://www.linkedin.com/uas/oauth2/authorization'
    profile_url = 'https://api.linkedin.com/v1/people/~'
    supports_state = False
    # See:
    # http://developer.linkedin.com/forum/unauthorized-invalid-or-expired-token-immediately-after-receiving-oauth2-token?page=1 # noqa
    access_token_method = 'GET'

    def complete_login(self, request, app, token, **kwargs):
        extra_data = self.get_user_info(token)
        return self.get_provider().sociallogin_from_response(request, extra_data)

    def get_user_info(self, token):
        fields = providers.registry \
            .by_id(LinkedInOAuth2Provider.id) \
            .get_profile_fields()
        url = self.profile_url + ':(%s)?format=json' % ','.join(fields)
        resp = requests.get(url, params={'oauth2_access_token': token.token})
        return resp.json()

oauth2_login = OAuth2LoginView.adapter_view(LinkedInOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(LinkedInOAuth2Adapter)

########NEW FILE########
__FILENAME__ = client
"""
Parts derived from socialregistration and authorized by: alen, pinda
Inspired by:
    http://github.com/leah/python-oauth/blob/master/oauth/example/client.py
    http://github.com/facebook/tornado/blob/master/tornado/auth.py
"""

from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from django.utils.translation import gettext as _

try:
    from urllib.parse import parse_qsl, urlparse
except ImportError:
    from urlparse import parse_qsl
    from urlparse import urlparse

import requests
from requests_oauthlib import OAuth1


def get_token_prefix(url):
    """
    Returns a prefix for the token to store in the session so we can hold
    more than one single oauth provider's access key in the session.

    Example:

        The request token url ``http://twitter.com/oauth/request_token``
        returns ``twitter.com``

    """
    return urlparse(url).netloc


class OAuthError(Exception):
    pass


class OAuthClient(object):

    def __init__(self, request, consumer_key, consumer_secret,
                 request_token_url, access_token_url, callback_url,
                 parameters=None, provider=None):

        self.request = request

        self.request_token_url = request_token_url
        self.access_token_url = access_token_url

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        self.parameters = parameters

        self.callback_url = callback_url
        self.provider = provider

        self.errors = []
        self.request_token = None
        self.access_token = None

    def _get_request_token(self):
        """
        Obtain a temporary request token to authorize an access token and to
        sign the request to obtain the access token
        """
        if self.request_token is None:
            get_params = {}
            if self.parameters:
                get_params.update(self.parameters)
            get_params['oauth_callback'] \
                = self.request.build_absolute_uri(self.callback_url)
            rt_url = self.request_token_url + '?' + urlencode(get_params)
            oauth = OAuth1(self.consumer_key,
                           client_secret=self.consumer_secret)
            response = requests.post(url=rt_url, auth=oauth)
            if response.status_code not in [200, 201]:
                raise OAuthError(
                    _('Invalid response while obtaining request token from "%s".') % get_token_prefix(self.request_token_url))
            self.request_token = dict(parse_qsl(response.text))
            self.request.session['oauth_%s_request_token' % get_token_prefix(self.request_token_url)] = self.request_token
        return self.request_token

    def get_access_token(self):
        """
        Obtain the access token to access private resources at the API
        endpoint.
        """
        if self.access_token is None:
            request_token = self._get_rt_from_session()
            oauth = OAuth1(self.consumer_key,
                           client_secret=self.consumer_secret,
                           resource_owner_key=request_token['oauth_token'],
                           resource_owner_secret=request_token['oauth_token_secret'])
            at_url = self.access_token_url
            # Passing along oauth_verifier is required according to:
            # http://groups.google.com/group/twitter-development-talk/browse_frm/thread/472500cfe9e7cdb9#
            # Though, the custom oauth_callback seems to work without it?
            if 'oauth_verifier' in self.request.REQUEST:
                at_url = at_url + '?' + urlencode({'oauth_verifier': self.request.REQUEST['oauth_verifier']})
            response = requests.post(url=at_url, auth=oauth)
            if response.status_code not in [200, 201]:
                raise OAuthError(
                    _('Invalid response while obtaining access token from "%s".') % get_token_prefix(self.request_token_url))
            self.access_token = dict(parse_qsl(response.text))

            self.request.session['oauth_%s_access_token' % get_token_prefix(self.request_token_url)] = self.access_token
        return self.access_token

    def _get_rt_from_session(self):
        """
        Returns the request token cached in the session by
        ``_get_request_token``
        """
        try:
            return self.request.session['oauth_%s_request_token'
                                        % get_token_prefix(
                                            self.request_token_url)]
        except KeyError:
            raise OAuthError(_('No request token saved for "%s".')
                             % get_token_prefix(self.request_token_url))

    def is_valid(self):
        try:
            self._get_rt_from_session()
            self.get_access_token()
        except OAuthError as e:
            self.errors.append(e.args[0])
            return False
        return True

    def get_redirect(self, authorization_url):
        """
        Returns a ``HttpResponseRedirect`` object to redirect the user
        to the URL the OAuth provider handles authorization.
        """
        request_token = self._get_request_token()
        params = {'oauth_token': request_token['oauth_token'],
                  'oauth_callback': self.request.build_absolute_uri(
                      self.callback_url)}
        url = authorization_url + '?' + urlencode(params)
        return HttpResponseRedirect(url)


class OAuth(object):
    """
    Base class to perform oauth signed requests from access keys saved
    in a user's session. See the ``OAuthTwitter`` class below for an
    example.
    """

    def __init__(self, request, consumer_key, secret_key, request_token_url):
        self.request = request
        self.consumer_key = consumer_key
        self.secret_key = secret_key
        self.request_token_url = request_token_url

    def _get_at_from_session(self):
        """
        Get the saved access token for private resources from the session.
        """
        try:
            return self.request.session['oauth_%s_access_token'
                                        % get_token_prefix(
                                            self.request_token_url)]
        except KeyError:
            raise OAuthError(
                _('No access token saved for "%s".')
                % get_token_prefix(self.request_token_url))

    def query(self, url, method="GET", params=dict(), headers=dict()):
        """
        Request a API endpoint at ``url`` with ``params`` being either the
        POST or GET data.
        """
        access_token = self._get_at_from_session()
        oauth = OAuth1(
            self.consumer_key,
            client_secret=self.secret_key,
            resource_owner_key=access_token['oauth_token'],
            resource_owner_secret=access_token['oauth_token_secret'])
        response = getattr(requests, method.lower())(url,
                                                     auth=oauth,
                                                     headers=headers,
                                                     params=params)
        if response.status_code != 200:
            raise OAuthError(
                _('No access to private resources at "%s".')
                % get_token_prefix(self.request_token_url))

        return response.text

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

from allauth.socialaccount.providers.base import Provider


class OAuthProvider(Provider):

    def get_login_url(self, request, **kwargs):
        url = reverse(self.id + "_login")
        if kwargs:
            url = url + '?' + urlencode(kwargs)
        return url

    def get_auth_url(self, request, action):
        # TODO: This is ugly. Move authorization_url away from the
        # adapter into the provider. Hmpf, the line between
        # adapter/provider is a bit too thin here.
        return None

    def get_scope(self):
        settings = self.get_settings()
        scope = settings.get('SCOPE')
        if scope is None:
            scope = self.get_default_scope()
        return scope

    def get_default_scope(self):
        return []

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include


def default_urlpatterns(provider):

    urlpatterns = patterns(provider.package + '.views',
                           url('^login/$', 'oauth_login',
                               name=provider.id + "_login"),
                           url('^login/callback/$', 'oauth_callback',
                               name=provider.id + "_callback"))

    return patterns('', url('^' + provider.id + '/', include(urlpatterns)))

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount.providers.oauth.client import (OAuthClient,
                                                          OAuthError)
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialToken, SocialLogin

from ..base import AuthAction


class OAuthAdapter(object):

    def complete_login(self, request, app):
        """
        Returns a SocialLogin instance
        """
        raise NotImplementedError

    def get_provider(self):
        return providers.registry.by_id(self.provider_id)


class OAuthView(object):
    @classmethod
    def adapter_view(cls, adapter):
        def view(request, *args, **kwargs):
            self = cls()
            self.request = request
            self.adapter = adapter()
            return self.dispatch(request, *args, **kwargs)
        return view

    def _get_client(self, request, callback_url):
        provider = self.adapter.get_provider()
        app = provider.get_app(request)
        scope = ' '.join(provider.get_scope())
        parameters = {}
        if scope:
            parameters['scope'] = scope
        client = OAuthClient(request, app.client_id, app.secret,
                             self.adapter.request_token_url,
                             self.adapter.access_token_url,
                             callback_url,
                             parameters=parameters, provider=provider)
        return client


class OAuthLoginView(OAuthView):
    def dispatch(self, request):
        callback_url = reverse(self.adapter.provider_id + "_callback")
        SocialLogin.stash_state(request)
        action = request.GET.get('action', AuthAction.AUTHENTICATE)
        provider = self.adapter.get_provider()
        auth_url = provider.get_auth_url(request, action) or self.adapter.authorize_url
        client = self._get_client(request, callback_url)
        try:
            return client.get_redirect(auth_url)
        except OAuthError:
            return render_authentication_error(request)


class OAuthCallbackView(OAuthView):
    def dispatch(self, request):
        """
        View to handle final steps of OAuth based authentication where the user
        gets redirected back to from the service provider
        """
        login_done_url = reverse(self.adapter.provider_id + "_callback")
        client = self._get_client(request, login_done_url)
        if not client.is_valid():
            if 'denied' in request.GET:
                return HttpResponseRedirect(reverse('socialaccount_login_cancelled'))
            extra_context = dict(oauth_client=client)
            return render_authentication_error(request, extra_context)
        app = self.adapter.get_provider().get_app(request)
        try:
            access_token = client.get_access_token()
            token = SocialToken(app=app,
                                token=access_token['oauth_token'],
                                token_secret=access_token['oauth_token_secret'])
            login = self.adapter.complete_login(request, app, token)
            token.account = login.account
            login.token = token
            login.state = SocialLogin.unstash_state(request)
            return complete_social_login(request, login)
        except OAuthError:
            return render_authentication_error(request)

########NEW FILE########
__FILENAME__ = client
try:
    from urllib.parse import parse_qsl, urlencode
except ImportError:
    from urllib import urlencode
    from urlparse import parse_qsl
import requests


class OAuth2Error(Exception):
    pass


class OAuth2Client(object):

    def __init__(self, request, consumer_key, consumer_secret,
                 access_token_method,
                 access_token_url,
                 callback_url,
                 scope):
        self.request = request
        self.access_token_method = access_token_method
        self.access_token_url = access_token_url
        self.callback_url = callback_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.scope = ' '.join(scope)
        self.state = None

    def get_redirect_url(self, authorization_url, extra_params):
        params = {
            'client_id': self.consumer_key,
            'redirect_uri': self.callback_url,
            'scope': self.scope,
            'response_type': 'code'
        }
        if self.state:
            params['state'] = self.state
        params.update(extra_params)
        return '%s?%s' % (authorization_url, urlencode(params))

    def get_access_token(self, code):
        data = {'client_id': self.consumer_key,
                'redirect_uri': self.callback_url,
                'grant_type': 'authorization_code',
                'client_secret': self.consumer_secret,
                'scope': self.scope,
                'code': code}
        params = None
        url = self.access_token_url
        if self.access_token_method == 'GET':
            params = data
            data = None
        # TODO: Proper exception handling
        resp = requests.request(self.access_token_method,
                                url,
                                params=params,
                                data=data)
        access_token = None
        if resp.status_code == 200:
            # Weibo sends json via 'text/plain;charset=UTF-8'
            if (resp.headers['content-type'].split(';')[0] == 'application/json'
                or resp.text[:2] == '{"'):
                access_token = resp.json()
            else:
                access_token = dict(parse_qsl(resp.text))
        if not access_token or 'access_token' not in access_token:
            raise OAuth2Error('Error retrieving access token: %s'
                              % resp.content)
        return access_token

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

from allauth.socialaccount.providers.base import Provider


class OAuth2Provider(Provider):
    def get_login_url(self, request, **kwargs):
        url = reverse(self.id + "_login")
        if kwargs:
            url = url + '?' + urlencode(kwargs)
        return url

    def get_auth_params(self, request, action):
        settings = self.get_settings()
        return settings.get('AUTH_PARAMS', {})

    def get_scope(self):
        settings = self.get_settings()
        scope = settings.get('SCOPE')
        if scope is None:
            scope = self.get_default_scope()
        return scope

    def get_default_scope(self):
        return []

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include


def default_urlpatterns(provider):
    urlpatterns = patterns(provider.package + '.views',
                           url('^login/$', 'oauth2_login', 
                               name=provider.id + "_login"),
                           url('^login/callback/$', 'oauth2_callback',
                               name=provider.id + "_callback"))

    return patterns('', url('^' + provider.id + '/', include(urlpatterns)))

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

from datetime import timedelta

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone

from allauth.utils import build_absolute_uri
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.client import (OAuth2Client,
                                                           OAuth2Error)
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialToken, SocialLogin
from ..base import AuthAction


class OAuth2Adapter(object):
    expires_in_key = 'expires_in'
    supports_state = True
    redirect_uri_protocol = None  # None -- don't switch
    access_token_method = 'POST'

    def get_provider(self):
        return providers.registry.by_id(self.provider_id)

    def complete_login(self, request, app, access_token, **kwargs):
        """
        Returns a SocialLogin instance
        """
        raise NotImplementedError

    def parse_token(self, data):
        token = SocialToken(token=data['access_token'])
        token.token_secret = data.get('refresh_token', '')
        expires_in = data.get(self.expires_in_key, None)
        if expires_in:
            token.expires_at = timezone.now() + timedelta(
                seconds=int(expires_in))
        return token


class OAuth2View(object):
    @classmethod
    def adapter_view(cls, adapter):
        def view(request, *args, **kwargs):
            self = cls()
            self.request = request
            self.adapter = adapter()
            return self.dispatch(request, *args, **kwargs)
        return view

    def get_client(self, request, app):
        callback_url = reverse(self.adapter.provider_id + "_callback")
        callback_url = build_absolute_uri(
            request, callback_url,
            protocol=self.adapter.redirect_uri_protocol)
        provider = self.adapter.get_provider()
        client = OAuth2Client(self.request, app.client_id, app.secret,
                              self.adapter.access_token_method,
                              self.adapter.access_token_url,
                              callback_url,
                              provider.get_scope())
        return client


class OAuth2LoginView(OAuth2View):
    def dispatch(self, request):
        provider = self.adapter.get_provider()
        app = provider.get_app(self.request)
        client = self.get_client(request, app)
        action = request.GET.get('action', AuthAction.AUTHENTICATE)
        auth_url = self.adapter.authorize_url
        auth_params = provider.get_auth_params(request, action)
        client.state = SocialLogin.stash_state(request)
        try:
            return HttpResponseRedirect(client.get_redirect_url(auth_url,
                                                                auth_params))
        except OAuth2Error:
            return render_authentication_error(request)


class OAuth2CallbackView(OAuth2View):
    def dispatch(self, request):
        if 'error' in request.GET or not 'code' in request.GET:
            # TODO: Distinguish cancel from error
            return render_authentication_error(request)
        app = self.adapter.get_provider().get_app(self.request)
        client = self.get_client(request, app)
        try:
            access_token = client.get_access_token(request.GET['code'])
            token = self.adapter.parse_token(access_token)
            token.app = app
            login = self.adapter.complete_login(request,
                                                app,
                                                token,
                                                response=access_token)
            token.account = login.account
            login.token = token
            if self.adapter.supports_state:
                login.state = SocialLogin \
                    .verify_and_unstash_state(
                        request,
                        request.REQUEST.get('state'))
            else:
                login.state = SocialLogin.unstash_state(request)
            return complete_social_login(request, login)
        except OAuth2Error:
            return render_authentication_error(request)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from .models import OpenIDStore, OpenIDNonce


class OpenIDStoreAdmin(admin.ModelAdmin):
    pass

class OpenIDNonceAdmin(admin.ModelAdmin):
    pass

admin.site.register(OpenIDStore, OpenIDStoreAdmin)
admin.site.register(OpenIDNonce, OpenIDNonceAdmin)

########NEW FILE########
__FILENAME__ = forms

from django import forms


class LoginForm(forms.Form):
    openid = forms.URLField(label=('OpenID'),
                            help_text='Get an <a href="http://openid.net/get-an-openid/">OpenID</a>')
    next = forms.CharField(widget=forms.HiddenInput,
                           required=False)
    process = forms.CharField(widget=forms.HiddenInput,
                              required=False)


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):
    depends_on = (('socialaccount', '0001_initial'),)

    def forwards(self, orm):
        
        # Adding model 'OpenIDAccount'
        db.create_table('openid_openidaccount', (
            ('socialaccount_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['socialaccount.SocialAccount'], unique=True, primary_key=True)),
            ('identity', self.gf('django.db.models.fields.URLField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('openid', ['OpenIDAccount'])

        # Adding model 'OpenIDStore'
        db.create_table('openid_openidstore', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('server_url', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('handle', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('secret', self.gf('django.db.models.fields.TextField')()),
            ('issued', self.gf('django.db.models.fields.IntegerField')()),
            ('lifetime', self.gf('django.db.models.fields.IntegerField')()),
            ('assoc_type', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('openid', ['OpenIDStore'])

        # Adding model 'OpenIDNonce'
        db.create_table('openid_openidnonce', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('server_url', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('timestamp', self.gf('django.db.models.fields.IntegerField')()),
            ('salt', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('openid', ['OpenIDNonce'])


    def backwards(self, orm):
        
        # Deleting model 'OpenIDAccount'
        db.delete_table('openid_openidaccount')

        # Deleting model 'OpenIDStore'
        db.delete_table('openid_openidstore')

        # Deleting model 'OpenIDNonce'
        db.delete_table('openid_openidnonce')


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
        'openid.openidaccount': {
            'Meta': {'object_name': 'OpenIDAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'identity': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '255'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'})
        },
        'openid.openidnonce': {
            'Meta': {'object_name': 'OpenIDNonce'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'salt': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'timestamp': ('django.db.models.fields.IntegerField', [], {})
        },
        'openid.openidstore': {
            'Meta': {'object_name': 'OpenIDStore'},
            'assoc_type': ('django.db.models.fields.TextField', [], {}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.IntegerField', [], {}),
            'lifetime': ('django.db.models.fields.IntegerField', [], {}),
            'secret': ('django.db.models.fields.TextField', [], {}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['openid']

########NEW FILE########
__FILENAME__ = 0002_tosocialaccount
# encoding: utf-8
from south.v2 import DataMigration

class Migration(DataMigration):

    depends_on = (('socialaccount', '0002_genericmodels'),)

    def forwards(self, orm):
        for acc in orm.OpenIDAccount.objects.all():
            sacc = acc.socialaccount_ptr
            sacc.uid = acc.identity
            sacc.provider = 'openid'
            sacc.save()


    def backwards(self, orm):
        "Write your backwards methods here."


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
        'openid.openidaccount': {
            'Meta': {'object_name': 'OpenIDAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'identity': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '255'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'})
        },
        'openid.openidnonce': {
            'Meta': {'object_name': 'OpenIDNonce'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'salt': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'timestamp': ('django.db.models.fields.IntegerField', [], {})
        },
        'openid.openidstore': {
            'Meta': {'object_name': 'OpenIDStore'},
            'assoc_type': ('django.db.models.fields.TextField', [], {}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.IntegerField', [], {}),
            'lifetime': ('django.db.models.fields.IntegerField', [], {}),
            'secret': ('django.db.models.fields.TextField', [], {}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['socialaccount', 'openid']

########NEW FILE########
__FILENAME__ = 0003_auto__del_openidaccount
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'OpenIDAccount'
        db.delete_table('openid_openidaccount')


    def backwards(self, orm):
        
        # Adding model 'OpenIDAccount'
        db.create_table('openid_openidaccount', (
            ('socialaccount_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['socialaccount.SocialAccount'], unique=True, primary_key=True)),
            ('identity', self.gf('django.db.models.fields.URLField')(max_length=255, unique=True)),
        ))
        db.send_create_signal('openid', ['OpenIDAccount'])


    models = {
        'openid.openidnonce': {
            'Meta': {'object_name': 'OpenIDNonce'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'salt': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'timestamp': ('django.db.models.fields.IntegerField', [], {})
        },
        'openid.openidstore': {
            'Meta': {'object_name': 'OpenIDStore'},
            'assoc_type': ('django.db.models.fields.TextField', [], {}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.IntegerField', [], {}),
            'lifetime': ('django.db.models.fields.IntegerField', [], {}),
            'secret': ('django.db.models.fields.TextField', [], {}),
            'server_url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['openid']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

@python_2_unicode_compatible
class OpenIDStore(models.Model):
    server_url = models.CharField(max_length=255)
    handle = models.CharField(max_length=255)
    secret = models.TextField()
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField()

    def __str__(self):
        return self.server_url


@python_2_unicode_compatible
class OpenIDNonce(models.Model):
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.server_url

########NEW FILE########
__FILENAME__ = provider
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import Provider, ProviderAccount

from .utils import get_email_from_response, get_value_from_response
from .utils import SRegField, OldAXAttribute, AXAttribute


class OpenIDAccount(ProviderAccount):
    def get_brand(self):
        ret = super(OpenIDAccount, self).get_brand()
        domain = urlparse(self.account.uid).netloc
        # FIXME: Instead of hardcoding, derive this from the domains
        # listed in the openid endpoints setting.
        provider_map = {'yahoo': dict(id='yahoo',
                                      name='Yahoo'),
                        'hyves': dict(id='hyves',
                                      name='Hyves'),
                        'google': dict(id='google',
                                       name='Google')}
        for d, p in provider_map.items():
            if domain.lower().find(d) >= 0:
                ret = p
                break
        return ret

    def to_str(self):
        return self.account.uid


class OpenIDProvider(Provider):
    id = 'openid'
    name = 'OpenID'
    package = 'allauth.socialaccount.providers.openid'
    account_class = OpenIDAccount

    def get_login_url(self, request, **kwargs):
        url = reverse('openid_login')
        if kwargs:
            url += '?' + urlencode(kwargs)
        return url

    def get_brands(self):
        # These defaults are a bit too arbitrary...
        default_servers = [dict(id='yahoo',
                                name='Yahoo',
                                openid_url='http://me.yahoo.com'),
                           dict(id='hyves',
                                name='Hyves',
                                openid_url='http://hyves.nl')]
        return self.get_settings().get('SERVERS', default_servers)

    def extract_extra_data(self, response):
        return {}

    def extract_uid(self, response):
        return response.identity_url

    def extract_common_fields(self, response):
        first_name = get_value_from_response(response,
                                             ax_names=[AXAttribute
                                                       .PERSON_FIRST_NAME,
                                                       OldAXAttribute
                                                       .PERSON_FIRST_NAME]) \
            or ''
        last_name = get_value_from_response(response,
                                            ax_names=[AXAttribute
                                                      .PERSON_LAST_NAME,
                                                      OldAXAttribute
                                                      .PERSON_LAST_NAME]) \
            or ''
        name = get_value_from_response(response,
                                       sreg_names=[SRegField.NAME],
                                       ax_names=[AXAttribute.PERSON_NAME,
                                                 OldAXAttribute.PERSON_NAME]) \
            or ''
        return dict(email=get_email_from_response(response),
                    first_name=first_name,
                    last_name=last_name, name=name)


providers.registry.register(OpenIDProvider)

########NEW FILE########
__FILENAME__ = tests
try:
    from mock import Mock, patch
except ImportError:
    from unittest.mock import Mock, patch

from openid.consumer import consumer

from django.test import TestCase
from django.core.urlresolvers import reverse

from allauth.utils import get_user_model

from . import views
from .utils import AXAttribute

class OpenIDTests(TestCase):

    def test_discovery_failure(self):
        """
        This used to generate a server 500:
        DiscoveryFailure: No usable OpenID services found
        for http://www.google.com/
        """
        resp = self.client.post(reverse('openid_login'),
                                dict(openid='http://www.google.com'))
        self.assertTrue('openid' in resp.context['form'].errors)

    def test_login(self):
        resp = self.client.post(reverse(views.login),
                                dict(openid='http://me.yahoo.com'))
        assert 'login.yahooapis' in resp['location']
        with patch('allauth.socialaccount.providers'
                   '.openid.views._openid_consumer') as consumer_mock:
            client = Mock()
            complete = Mock()
            consumer_mock.return_value = client
            client.complete = complete
            complete_response = Mock()
            complete.return_value = complete_response
            complete_response.status = consumer.SUCCESS
            complete_response.identity_url = 'http://dummy/john/'
            with patch('allauth.socialaccount.providers'
                       '.openid.utils.SRegResponse') as sr_mock:
                with patch('allauth.socialaccount.providers'
                           '.openid.utils.FetchResponse') as fr_mock:
                    sreg_mock = Mock()
                    ax_mock = Mock()
                    sr_mock.fromSuccessResponse = sreg_mock
                    fr_mock.fromSuccessResponse = ax_mock
                    sreg_mock.return_value = {}
                    ax_mock.return_value = {AXAttribute.PERSON_FIRST_NAME:
                                            ['raymond']}
                    resp = self.client.post(reverse('openid_callback'))
                    self.assertEqual('http://testserver/accounts/profile/',
                                     resp['location'])
                    get_user_model().objects.get(first_name='raymond')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
                       url('^openid/login/$', views.login,
                           name="openid_login"),
                       url('^openid/callback/$', views.callback,
                           name='openid_callback'),
                       )

########NEW FILE########
__FILENAME__ = utils
import base64
try:
    from UserDict import UserDict
except ImportError:
    from collections import UserDict
import pickle

from openid.store.interface import OpenIDStore as OIDStore
from openid.association import Association as OIDAssociation
from openid.extensions.sreg import SRegResponse
from openid.extensions.ax import FetchResponse

from allauth.utils import valid_email_or_none

from .models import OpenIDStore, OpenIDNonce


class JSONSafeSession(UserDict):
    """
    openid puts e.g. class OpenIDServiceEndpoint in the session.
    Django 1.6 no longer pickles stuff, so we'll need to do some
    hacking here...
    """
    def __init__(self, session):
        UserDict.__init__(self)
        self.data = session

    def __setitem__(self, key, value):
        data = base64.b64encode(pickle.dumps(value)).decode('ascii')
        return UserDict.__setitem__(self, key, data)

    def __getitem__(self, key):
        data = UserDict.__getitem__(self, key)
        return pickle.loads(base64.b64decode(data.encode('ascii')))


class OldAXAttribute:
    PERSON_NAME = 'http://openid.net/schema/namePerson'
    PERSON_FIRST_NAME = 'http://openid.net/schema/namePerson/first'
    PERSON_LAST_NAME = 'http://openid.net/schema/namePerson/last'


class AXAttribute:
    CONTACT_EMAIL = 'http://axschema.org/contact/email'
    PERSON_NAME = 'http://axschema.org/namePerson'
    PERSON_FIRST_NAME = 'http://axschema.org/namePerson/first'
    PERSON_LAST_NAME = 'http://axschema.org/namePerson/last'


AXAttributes = [
    AXAttribute.CONTACT_EMAIL,
    AXAttribute.PERSON_NAME,
    AXAttribute.PERSON_FIRST_NAME,
    AXAttribute.PERSON_LAST_NAME,
    OldAXAttribute.PERSON_NAME,
    OldAXAttribute.PERSON_FIRST_NAME,
    OldAXAttribute.PERSON_LAST_NAME,
]


class SRegField:
    EMAIL = 'email'
    NAME = 'fullname'


SRegFields = [
    SRegField.EMAIL,
    SRegField.NAME,
]


class DBOpenIDStore(OIDStore):
    max_nonce_age = 6 * 60 * 60

    def storeAssociation(self, server_url, assoc=None):
        OpenIDStore.objects.create(
            server_url=server_url,
            handle=assoc.handle,
            secret=base64.encodestring(assoc.secret),
            issued=assoc.issued,
            lifetime=assoc.lifetime,
            assoc_type=assoc.assoc_type
        )

    def getAssociation(self, server_url, handle=None):
        stored_assocs = OpenIDStore.objects.filter(
            server_url=server_url
        )
        if handle:
            stored_assocs = stored_assocs.filter(handle=handle)

        stored_assocs.order_by('-issued')

        if stored_assocs.count() == 0:
            return None

        return_val = None

        for stored_assoc in stored_assocs:
            assoc = OIDAssociation(
                stored_assoc.handle,
                base64.decodestring(stored_assoc.secret.encode('utf-8')),
                stored_assoc.issued, stored_assoc.lifetime,
                stored_assoc.assoc_type
            )

            if assoc.getExpiresIn() == 0:
                stored_assoc.delete()
            else:
                if return_val is None:
                    return_val = assoc

        return return_val

    def removeAssociation(self, server_url, handle):
        stored_assocs = OpenIDStore.objects.filter(
            server_url=server_url
        )
        if handle:
            stored_assocs = stored_assocs.filter(handle=handle)

        stored_assocs.delete()

    def useNonce(self, server_url, timestamp, salt):
        try:
            OpenIDNonce.objects.get(
                server_url=server_url,
                timestamp=timestamp,
                salt=salt
            )
        except OpenIDNonce.DoesNotExist:
            OpenIDNonce.objects.create(
                server_url=server_url,
                timestamp=timestamp,
                salt=salt
            )
            return True

        return False


def get_email_from_response(response):
    email = None
    sreg = SRegResponse.fromSuccessResponse(response)
    if sreg:
        email = valid_email_or_none(sreg.get(SRegField.EMAIL))
    if not email:
        ax = FetchResponse.fromSuccessResponse(response)
        if ax:
            try:
                values = ax.get(AXAttribute.CONTACT_EMAIL)
                if values:
                    email = valid_email_or_none(values[0])
            except KeyError:
                pass
    return email


def get_value_from_response(response, sreg_names=None, ax_names=None):
    value = None
    if sreg_names:
        sreg = SRegResponse.fromSuccessResponse(response)
        if sreg:
            for name in sreg_names:
                value = sreg.get(name)
                if value:
                    break

    if not value and ax_names:
        ax = FetchResponse.fromSuccessResponse(response)
        if ax:
            for name in ax_names:
                try:
                    values = ax.get(name)
                    if values:
                        value = values[0]
                except KeyError:
                    pass
                if value:
                    break
    return value

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from openid.consumer.discover import DiscoveryFailure
from openid.consumer import consumer
from openid.extensions.sreg import SRegRequest
from openid.extensions.ax import FetchRequest, AttrInfo

from allauth.socialaccount.app_settings import QUERY_EMAIL
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount import providers

from .utils import (DBOpenIDStore, SRegFields, AXAttributes,
                    JSONSafeSession)
from .forms import LoginForm
from .provider import OpenIDProvider


def _openid_consumer(request):
    store = DBOpenIDStore()
    client = consumer.Consumer(JSONSafeSession(request.session), store)
    return client


def login(request):
    if 'openid' in request.GET or request.method == 'POST':
        form = LoginForm(request.REQUEST)
        if form.is_valid():
            client = _openid_consumer(request)
            try:
                auth_request = client.begin(form.cleaned_data['openid'])
                if QUERY_EMAIL:
                    sreg = SRegRequest()
                    for name in SRegFields:
                        sreg.requestField(field_name=name,
                                          required=True)
                    auth_request.addExtension(sreg)
                    ax = FetchRequest()
                    for name in AXAttributes:
                        ax.add(AttrInfo(name,
                                        required=True))
                    auth_request.addExtension(ax)
                callback_url = reverse(callback)
                SocialLogin.stash_state(request)
                redirect_url = auth_request.redirectURL(
                    request.build_absolute_uri('/'),
                    request.build_absolute_uri(callback_url))
                return HttpResponseRedirect(redirect_url)
            # UnicodeDecodeError:
            # see https://github.com/necaris/python3-openid/issues/1
            except (UnicodeDecodeError, DiscoveryFailure) as e:
                if request.method == 'POST':
                    form._errors["openid"] = form.error_class([e])
                else:
                    return render_authentication_error(request)
    else:
        form = LoginForm(initial={'next': request.GET.get('next'),
                                  'process': request.GET.get('process')})
    d = dict(form=form)
    return render_to_response('openid/login.html',
                              d, context_instance=RequestContext(request))


@csrf_exempt
def callback(request):
    client = _openid_consumer(request)
    response = client.complete(
        dict(request.REQUEST.items()),
        request.build_absolute_uri(request.path))
    if response.status == consumer.SUCCESS:
        login = providers.registry \
            .by_id(OpenIDProvider.id) \
            .sociallogin_from_response(request, response)
        login.state = SocialLogin.unstash_state(request)
        ret = complete_social_login(request, login)
    elif response.status == consumer.CANCEL:
        ret = HttpResponseRedirect(reverse('socialaccount_login_cancelled'))
    else:
        ret = render_authentication_error(request)
    return ret

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class PaypalAccount(ProviderAccount):
    def get_avatar_url(self):
        return self.account.extra_data.get('picture')

    def to_str(self):
        return self.account.extra_data.get('name',
                                           super(PaypalAccount, self).to_str())


class PaypalProvider(OAuth2Provider):
    id = 'paypal'
    name = 'Paypal'
    package = 'allauth.socialaccount.providers.paypal'
    account_class = PaypalAccount

    def get_default_scope(self):
        # See: https://developer.paypal.com/docs/integration/direct/identity/attributes/  # noqa
        return ['openid', 'email']

    def extract_uid(self, data):
        return str(data['user_id'])

    def extract_common_fields(self, data):
        # See: https://developer.paypal.com/docs/api/#get-user-information
        return dict(first_name=data.get('given_name', ''),
                    last_name=data.get('family_name', ''),
                    email=data['email'])

providers.registry.register(PaypalProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import PaypalProvider

class PaypalTests(create_oauth2_tests(registry.by_id(PaypalProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
            "user_id": "https://www.paypal.com/webapps/auth/server/64ghr894040044",
            "name": "Jane Doe",
            "given_name": "Jane",
            "family_name": "Doe",
            "email": "janedoe@paypal.com"
        }
        """)

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import PaypalProvider

urlpatterns = default_urlpatterns(PaypalProvider)

########NEW FILE########
__FILENAME__ = views
import requests
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import PaypalProvider

class PaypalOAuth2Adapter(OAuth2Adapter):
    provider_id = PaypalProvider.id
    supports_state = False

    @property
    def authorize_url(self):
        path = 'webapps/auth/protocol/openidconnect/v1/authorize'
        return 'https://www.{0}/{1}'.format(self._get_endpoint(), path)

    @property
    def access_token_url(self):
        path = "v1/identity/openidconnect/tokenservice"
        return 'https://api.{0}/{1}'.format(self._get_endpoint(), path)

    @property
    def profile_url(self):
        path = 'v1/identity/openidconnect/userinfo'
        return 'https://api.{0}/{1}'.format(self._get_endpoint(), path)

    def _get_endpoint(self):
        settings = self.get_provider().get_settings()
        if settings.get('MODE') == 'live':
            return 'paypal.com'
        else:
            return 'sandbox.paypal.com'

    def complete_login(self, request, app, token, **kwargs):
        response = requests.post(self.profile_url,
                            params={'schema':'openid',
                                    'access_token':token})
        extra_data = response.json()
        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(PaypalOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(PaypalOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = provider
import json

from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.html import escapejs

from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount, Provider
from allauth.account.models import EmailAddress


class PersonaAccount(ProviderAccount):
    def to_str(self):
        return self.account.uid


class PersonaProvider(Provider):
    id = 'persona'
    name = 'Persona'
    package = 'allauth.socialaccount.providers.persona'
    account_class = PersonaAccount

    def media_js(self, request):
        settings = self.get_settings()
        request_parameters = settings.get('REQUEST_PARAMETERS', {})
        ctx = {'request_parameters': json.dumps(request_parameters)}
        return render_to_string('persona/auth.html',
                                ctx,
                                RequestContext(request))

    def get_login_url(self, request, **kwargs):
        next_url = "'%s'" % escapejs(kwargs.get('next') or '')
        process = "'%s'" % escapejs(kwargs.get('process') or 'login')
        return 'javascript:allauth.persona.login(%s, %s)' % (next_url, process)

    def extract_uid(self, data):
        return data['email']

    def extract_common_fields(self, data):
        return dict(email=data['email'])

    def extract_email_addresses(self, data):
        ret = [EmailAddress(email=data['email'],
                            verified=True,
                            primary=True)]
        return ret


providers.registry.register(PersonaProvider)

########NEW FILE########
__FILENAME__ = tests
try:
    from mock import patch
except ImportError:
    from unittest.mock import patch

from django.test import TestCase
from django.core.urlresolvers import reverse

from allauth.utils import get_user_model


class PersonaTests(TestCase):

    def test_login(self):
        with patch('allauth.socialaccount.providers.persona.views'
                   '.requests') as requests_mock:
            requests_mock.post.return_value.json.return_value = {
                'status': 'okay',
                'email': 'persona@mail.com'
            }
            resp = self.client.post(reverse('persona_login'),
                                    dict(assertion='dummy'))
            self.assertEqual('http://testserver/accounts/profile/',
                             resp['location'])
            get_user_model().objects.get(email='persona@mail.com')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
                       url('^persona/login/$',
                           views.persona_login,
                           name="persona_login"))

########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount import providers

from .provider import PersonaProvider


def persona_login(request):
    assertion = request.POST.get('assertion', '')
    audience = request.build_absolute_uri('/')
    resp = requests.post('https://verifier.login.persona.org/verify',
                         {'assertion': assertion,
                          'audience': audience})
    if resp.json()['status'] != 'okay':
        return render_authentication_error(request)
    extra_data = resp.json()
    login = providers.registry \
        .by_id(PersonaProvider.id) \
        .sociallogin_from_response(request, extra_data)
    login.state = SocialLogin.state_from_request(request)
    return complete_social_login(request, login)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class SoundCloudAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('permalink_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar_url')

    def to_str(self):
        dflt = super(SoundCloudAccount, self).to_str()
        full_name = self.account.extra_data.get('full_name')
        username = self.account.extra_data.get('username')
        return full_name or username or dflt


class SoundCloudProvider(OAuth2Provider):
    id = 'soundcloud'
    name = 'SoundCloud'
    package = 'allauth.socialaccount.providers.soundcloud'
    account_class = SoundCloudAccount


    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(name=data.get('full_name'),
                    username=data.get('username'),
                    email=data.get('email'))


providers.registry.register(SoundCloudProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import SoundCloudProvider

class SoundCloudTests(create_oauth2_tests(registry.by_id(SoundCloudProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
           "website": null,
            "myspace_name": null,
            "public_favorites_count": 0,
            "followings_count": 1,
            "full_name": "",
            "id": 22341947,
            "city": null,
            "track_count": 0,
            "playlist_count": 0,
            "discogs_name": null,
            "private_tracks_count": 0,
            "followers_count": 0,
            "online": true,
            "username": "user187631676",
            "description": null,
            "kind": "user",
            "website_title": null,
            "primary_email_confirmed": false,
            "permalink_url": "http://soundcloud.com/user187631676",
            "private_playlists_count": 0,
            "permalink": "user187631676",
            "country": null,
            "uri": "https://api.soundcloud.com/users/22341947",
            "avatar_url": "https://a1.sndcdn.com/images/default_avatar_large.png?4b4189b",
            "plan": "Free"
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import SoundCloudProvider 

urlpatterns = default_urlpatterns(SoundCloudProvider)

########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from .provider import SoundCloudProvider


class SoundCloudOAuth2Adapter(OAuth2Adapter):
    provider_id = SoundCloudProvider.id
    access_token_url = 'https://api.soundcloud.com/oauth2/token'
    authorize_url = 'https://soundcloud.com/connect'
    profile_url = 'https://api.soundcloud.com/me.json'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url,
                            params={'oauth_token': token.token})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(SoundCloudOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(SoundCloudOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class StackExchangeAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('html_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar_url')

    def to_str(self):
        dflt = super(StackExchangeAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class StackExchangeProvider(OAuth2Provider):
    id = 'stackexchange'
    name = 'Stack Exchange'
    package = 'allauth.socialaccount.providers.stackexchange'
    account_class = StackExchangeAccount

    def get_site(self):
        settings = self.get_settings()
        return settings.get('SITE', 'stackoverflow')

    def extract_uid(self, data):
        # `user_id` varies if you use the same account for
        # e.g. StackOverflow and ServerFault. Therefore, we pick
        # `account_id`.
        uid = str(data['account_id'])
        return uid

    def extract_common_fields(self, data):
        return dict(username=data.get('display_name'))


providers.registry.register(StackExchangeProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import StackExchangeProvider

class StackExchangeTests(create_oauth2_tests(registry.by_id(StackExchangeProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """
        {
          "has_more": false,
           "items": [
              {
                "is_employee": false,
                 "last_access_date": 1356200390,
                 "display_name": "pennersr",
                 "account_id": 291652,
                 "badge_counts": {
                     "bronze": 2,
                     "silver": 2,
                     "gold": 0
                 },
                 "last_modified_date": 1356199552,
                 "profile_image": "http://www.gravatar.com/avatar/053d648486d567d3143d6bad8df8cfeb?d=identicon&r=PG",
                 "user_type": "registered",
                 "creation_date": 1296223711,
                 "reputation_change_quarter": 148,
                 "reputation_change_year": 378,
                 "reputation": 504,
                 "link": "http://stackoverflow.com/users/593944/pennersr",
                 "reputation_change_week": 0,
                 "user_id": 593944,
                 "reputation_change_month": 10,
                 "reputation_change_day": 0
              }
           ],
           "quota_max": 10000,
           "quota_remaining": 9999
        }""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import StackExchangeProvider

urlpatterns = default_urlpatterns(StackExchangeProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from allauth.socialaccount.providers import registry

from .provider import StackExchangeProvider


class StackExchangeOAuth2Adapter(OAuth2Adapter):
    provider_id = StackExchangeProvider.id
    access_token_url = 'https://stackexchange.com/oauth/access_token'
    authorize_url = 'https://stackexchange.com/oauth'
    profile_url = 'https://api.stackexchange.com/2.1/me'

    def complete_login(self, request, app, token, **kwargs):
        provider = registry.by_id(app.provider)
        site = provider.get_site()
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token,
                                    'key': app.key,
                                    'site': site})
        extra_data = resp.json()['items'][0]
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(StackExchangeOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(StackExchangeOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class TumblrAccount(ProviderAccount):
    def get_profile_url_(self):
        return 'http://%s.tumblr.com/' \
            % self.account.extra_data.get('name')

    def to_str(self):
        dflt = super(TumblrAccount, self).to_str()
        name = self.account.extra_data.get('name', dflt)
        return name


class TumblrProvider(OAuthProvider):
    id = 'tumblr'
    name = 'Tumblr'
    package = 'allauth.socialaccount.providers.tumblr'
    account_class = TumblrAccount

    def extract_uid(self, data):
        return data['name']

    def extract_common_fields(self, data):
        return dict(first_name=data.get('name'),)


providers.registry.register(TumblrProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import TumblrProvider


class TumblrTests(create_oauth_tests(registry.by_id(TumblrProvider.id))):
    def get_mocked_response(self):
        return [MockedResponse(200, u"""
{
   "meta": {
      "status": 200,
      "msg": "OK"
   },
   "response": {
     "user": {
       "following": 263,
       "default_post_format": "html",
       "name": "derekg",
       "likes": 606,
       "blogs": [
          {
           "name": "derekg",
           "title": "Derek Gottfrid",
           "url": "http://derekg.org/",
           "tweet": "auto",
           "primary": true,
           "followers": 33004929
          },
          {
           "name": "ihatehipstrz",
           "title": "I Hate Hipstrz"
           }
        ]
     }
} }
""")]

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import TumblrProvider

urlpatterns = default_urlpatterns(TumblrProvider)
########NEW FILE########
__FILENAME__ = views
import json

from django.utils import six

from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)

from .provider import TumblrProvider


class TumblrAPI(OAuth):
    url = 'http://api.tumblr.com/v2/user/info'

    def get_user_info(self):
        data = json.loads(self.query(self.url))
        return data['response']['user']


class TumblrOAuthAdapter(OAuthAdapter):
    provider_id = TumblrProvider.id
    request_token_url = 'https://www.tumblr.com/oauth/request_token'
    access_token_url = 'https://www.tumblr.com/oauth/access_token'
    authorize_url = 'https://www.tumblr.com/oauth/authorize'

    def complete_login(self, request, app, token):
        client = TumblrAPI(request, app.client_id, app.secret,
                           self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth_login = OAuthLoginView.adapter_view(TumblrOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(TumblrOAuthAdapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class TwitchAccount(ProviderAccount):
    def get_profile_url(self):
        return 'http://twitch.tv/' + self.account.extra_data.get('name')

    def get_avatar_url(self):
        return self.account.extra_data.get('logo')

    def to_str(self):
        dflt = super(TwitchAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class TwitchProvider(OAuth2Provider):
    id = 'twitch'
    name = 'Twitch'
    package = 'allauth.socialaccount.providers.twitch'
    account_class = TwitchAccount

    def extract_uid(self, data):
        return str(data['_id'])

    def extract_common_fields(self, data):
        return dict(username=data.get('display_name'),
                    name=data.get('name'),
                    email=data.get('email'))


providers.registry.register(TwitchProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import TwitchProvider

class TwitchTests(create_oauth2_tests(registry.by_id(TwitchProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """{"name":"test_user1","created_at":"2011-06-03T17:49:19Z","updated_at":"2012-06-18T17:19:57Z","_links":{"self":"https://api.twitch.tv/kraken/users/test_user1"},"logo":"http://static-cdn.jtvnw.net/jtv_user_pictures/test_user1-profile_image-62e8318af864d6d7-300x300.jpeg","_id":22761313,"display_name":"test_user1","email":"asdf@asdf.com","partnered":true}

""")


########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import TwitchProvider

urlpatterns = default_urlpatterns(TwitchProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import TwitchProvider


class TwitchOAuth2Adapter(OAuth2Adapter):
    provider_id = TwitchProvider.id
    access_token_url = 'https://api.twitch.tv/kraken/oauth2/token'
    authorize_url = 'https://api.twitch.tv/kraken/oauth2/authorize'
    profile_url = 'https://api.twitch.tv/kraken/user'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(self.profile_url,
                            params={'oauth_token': token.token})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(TwitchOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(TwitchOAuth2Adapter)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):
    depends_on = (('socialaccount', '0001_initial'),)


    def forwards(self, orm):
        
        # Adding model 'TwitterApp'
        db.create_table('twitter_twitterapp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('consumer_key', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('consumer_secret', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('request_token_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('access_token_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('authorize_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('twitter', ['TwitterApp'])

        # Adding model 'TwitterAccount'
        db.create_table('twitter_twitteraccount', (
            ('socialaccount_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['socialaccount.SocialAccount'], unique=True, primary_key=True)),
            ('social_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('profile_image_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('twitter', ['TwitterAccount'])


    def backwards(self, orm):
        
        # Deleting model 'TwitterApp'
        db.delete_table('twitter_twitterapp')

        # Deleting model 'TwitterAccount'
        db.delete_table('twitter_twitteraccount')


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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'twitter.twitteraccount': {
            'Meta': {'object_name': 'TwitterAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'profile_image_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'social_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'twitter.twitterapp': {
            'Meta': {'object_name': 'TwitterApp'},
            'access_token_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'authorize_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'consumer_key': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'consumer_secret': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'request_token_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        }
    }

    complete_apps = ['twitter']

########NEW FILE########
__FILENAME__ = 0002_snowflake
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'TwitterAccount.social_id'
        db.alter_column('twitter_twitteraccount', 'social_id', self.gf('django.db.models.fields.BigIntegerField')(unique=True))


    def backwards(self, orm):
        
        # Changing field 'TwitterAccount.social_id'
        db.alter_column('twitter_twitteraccount', 'social_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True))


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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'twitter.twitteraccount': {
            'Meta': {'object_name': 'TwitterAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'profile_image_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'social_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'twitter.twitterapp': {
            'Meta': {'object_name': 'TwitterApp'},
            'access_token_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'authorize_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'consumer_key': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'consumer_secret': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'request_token_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        }
    }

    complete_apps = ['twitter']

########NEW FILE########
__FILENAME__ = 0003_tosocialaccount
# encoding: utf-8
from south.v2 import DataMigration

class Migration(DataMigration):

    depends_on = (('socialaccount', '0002_genericmodels'),)

    def forwards(self, orm):
        # Migrate apps
        app_id_to_sapp = {}
        for app in orm.TwitterApp.objects.all():
            sapp = orm['socialaccount.SocialApp'].objects \
                .create(site=app.site,
                        provider='twitter',
                        name=app.name,
                        key=app.consumer_key,
                        secret=app.consumer_secret)
            app_id_to_sapp[app.id] = sapp
        # Migrate accounts
        acc_id_to_sacc = {}
        for acc in orm.TwitterAccount.objects.all():
            sacc = acc.socialaccount_ptr
            sacc.uid = str(acc.social_id)
            sacc.extra_data = { 'screen_name': acc.username,
                                'profile_image_url': acc.profile_image_url }
            sacc.provider = 'twitter'
            sacc.save()
            acc_id_to_sacc[acc.id] = sacc


    def backwards(self, orm):
        "Write your backwards methods here."


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
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'socialaccount.socialaccount': {
            'Meta': {'object_name': 'SocialAccount'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('allauth.socialaccount.fields.JSONField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'socialaccount.socialapp': {
            'Meta': {'object_name': 'SocialApp'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'socialaccount.socialtoken': {
            'Meta': {'unique_together': "(('app', 'account'),)", 'object_name': 'SocialToken'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialAccount']"}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['socialaccount.SocialApp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'token_secret': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'twitter.twitteraccount': {
            'Meta': {'object_name': 'TwitterAccount', '_ormbases': ['socialaccount.SocialAccount']},
            'profile_image_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'social_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'socialaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['socialaccount.SocialAccount']", 'unique': 'True', 'primary_key': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'twitter.twitterapp': {
            'Meta': {'object_name': 'TwitterApp'},
            'access_token_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'authorize_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'consumer_key': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'consumer_secret': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'request_token_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        }
    }

    complete_apps = ['socialaccount', 'twitter']

########NEW FILE########
__FILENAME__ = 0004_auto__del_twitteraccount__del_twitterapp
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'TwitterAccount'
        db.delete_table('twitter_twitteraccount')

        # Deleting model 'TwitterApp'
        db.delete_table('twitter_twitterapp')


    def backwards(self, orm):
        
        # Adding model 'TwitterAccount'
        db.create_table('twitter_twitteraccount', (
            ('username', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('social_id', self.gf('django.db.models.fields.BigIntegerField')(unique=True)),
            ('socialaccount_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['socialaccount.SocialAccount'], unique=True, primary_key=True)),
            ('profile_image_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('twitter', ['TwitterAccount'])

        # Adding model 'TwitterApp'
        db.create_table('twitter_twitterapp', (
            ('consumer_secret', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('request_token_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('authorize_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('consumer_key', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('access_token_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
        ))
        db.send_create_signal('twitter', ['TwitterApp'])


    models = {
        
    }

    complete_apps = ['twitter']

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import (ProviderAccount,
                                                  AuthAction)
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class TwitterAccount(ProviderAccount):
    def get_screen_name(self):
        return self.account.extra_data.get('screen_name')

    def get_profile_url(self):
        ret = None
        screen_name = self.get_screen_name()
        if screen_name:
            ret = 'http://twitter.com/' + screen_name
        return ret

    def get_avatar_url(self):
        ret = None
        profile_image_url = self.account.extra_data.get('profile_image_url')
        if profile_image_url:
            # Hmm, hack to get our hands on the large image.  Not
            # really documented, but seems to work.
            ret = profile_image_url.replace('_normal', '')
        return ret

    def to_str(self):
        screen_name = self.get_screen_name()
        return screen_name or super(TwitterAccount, self).to_str()


class TwitterProvider(OAuthProvider):
    id = 'twitter'
    name = 'Twitter'
    package = 'allauth.socialaccount.providers.twitter'
    account_class = TwitterAccount

    def get_auth_url(self, request, action):
        if action == AuthAction.REAUTHENTICATE:
            url = 'https://api.twitter.com/oauth/authorize'
        else:
            url = 'https://api.twitter.com/oauth/authenticate'
        return url

    def extract_uid(self, data):
        return data['id']

    def extract_common_fields(self, data):
        return dict(username=data.get('screen_name'),
                    name=data.get('name'))


providers.registry.register(TwitterProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import TwitterProvider


class TwitterTests(create_oauth_tests(registry.by_id(TwitterProvider.id))):
    def get_mocked_response(self):
        # FIXME: Replace with actual/complete Twitter response
        return [MockedResponse(200, r"""
{"follow_request_sent": false,
 "profile_use_background_image": true,
 "id": 45671919, "verified": false, "profile_text_color": "333333",
 "profile_image_url_https":
       "https://pbs.twimg.com/profile_images/793142149/r_normal.png",
 "profile_sidebar_fill_color": "DDEEF6",
 "is_translator": false, "geo_enabled": false, "entities":
 {"description": {"urls": []}}, "followers_count": 43, "protected": false,
 "location": "The Netherlands", "default_profile_image": false,
 "id_str": "45671919", "status": {"contributors": null, "truncated":
  false, "text": "RT @denibertovic: Okay I'm definitely using django-allauth from now on. So easy to set up, far less time consuming, and it just works. #dja\u2026", "in_reply_to_status_id": null, "id": 400658301702381568, "favorite_count": 0, "source": "<a href=\"http://twitter.com\" rel=\"nofollow\">Twitter Web Client</a>", "retweeted": true, "coordinates": null, "entities": {"symbols": [], "user_mentions": [{"indices": [3, 16], "screen_name": "denibertovic", "id": 23508244, "name": "Deni Bertovic", "id_str": "23508244"}], "hashtags": [{"indices": [135, 139], "text": "dja"}], "urls": []}, "in_reply_to_screen_name": null, "id_str": "400658301702381568", "retweet_count": 6, "in_reply_to_user_id": null, "favorited": false, "retweeted_status": {"lang": "en", "favorited": false, "in_reply_to_user_id": null, "contributors": null, "truncated": false, "text": "Okay I'm definitely using django-allauth from now on. So easy to set up, far less time consuming, and it just works. #django", "created_at": "Sun Jul 28 19:56:26 +0000 2013", "retweeted": true, "in_reply_to_status_id": null, "coordinates": null, "id": 361575897674956800, "entities": {"symbols": [], "user_mentions": [], "hashtags": [{"indices": [117, 124], "text": "django"}], "urls": []}, "in_reply_to_status_id_str": null, "in_reply_to_screen_name": null, "source": "web", "place": null, "retweet_count": 6, "geo": null, "in_reply_to_user_id_str": null, "favorite_count": 8, "id_str": "361575897674956800"}, "geo": null, "in_reply_to_user_id_str": null, "lang": "en", "created_at": "Wed Nov 13 16:15:57 +0000 2013", "in_reply_to_status_id_str": null, "place": null}, "utc_offset": 3600, "statuses_count": 39, "description": "", "friends_count": 83, "profile_link_color": "0084B4", "profile_image_url": "http://pbs.twimg.com/profile_images/793142149/r_normal.png", "notifications": false, "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png", "profile_background_color": "C0DEED", "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png", "name": "Raymond Penners", "lang": "nl", "profile_background_tile": false, "favourites_count": 0, "screen_name": "pennersr", "url": null, "created_at": "Mon Jun 08 21:10:45 +0000 2009", "contributors_enabled": false, "time_zone": "Amsterdam", "profile_sidebar_border_color": "C0DEED", "default_profile": true, "following": false, "listed_count": 1} """)]  # noqa

    def test_login(self):
        account = super(TwitterTests, self).test_login()
        tw_account = account.get_provider_account()
        self.assertEqual(tw_account.get_screen_name(),
                         'pennersr')
        self.assertEqual(tw_account.get_avatar_url(),
                         'http://pbs.twimg.com/profile_images/793142149/r.png')
        self.assertEqual(tw_account.get_profile_url(),
                         'http://twitter.com/pennersr')

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns

from .provider import TwitterProvider

urlpatterns = default_urlpatterns(TwitterProvider)

########NEW FILE########
__FILENAME__ = views
import json

from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)

from .provider import TwitterProvider


class TwitterAPI(OAuth):
    """
    Verifying twitter credentials
    """
    url = 'https://api.twitter.com/1.1/account/verify_credentials.json'

    def get_user_info(self):
        user = json.loads(self.query(self.url))
        return user


class TwitterOAuthAdapter(OAuthAdapter):
    provider_id = TwitterProvider.id
    request_token_url = 'https://api.twitter.com/oauth/request_token'
    access_token_url = 'https://api.twitter.com/oauth/access_token'
    # Issue #42 -- this one authenticates over and over again...
    # authorize_url = 'https://api.twitter.com/oauth/authorize'
    authorize_url = 'https://api.twitter.com/oauth/authenticate'

    def complete_login(self, request, app, token):
        client = TwitterAPI(request, app.client_id, app.secret,
                            self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth_login = OAuthLoginView.adapter_view(TwitterOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(TwitterOAuthAdapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class VimeoAccount(ProviderAccount):
    pass


class VimeoProvider(OAuthProvider):
    id = 'vimeo'
    name = 'Vimeo'
    package = 'allauth.socialaccount.providers.vimeo'
    account_class = VimeoAccount

    def get_default_scope(self):
        scope = []
        return scope

    def extract_uid(self, data):
        return data['id']

    def extract_common_fields(self, data):
        return dict(name=data.get('display_name'),
                    username=data.get('username'))


providers.registry.register(VimeoProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import VimeoProvider

class VimeoTests(create_oauth_tests(registry.by_id(VimeoProvider.id))):
    def get_mocked_response(self):
        return [MockedResponse(200, """
{"generated_in":"0.0137","stat":"ok","person":{"created_on":"2013-04-08 14:24:47","id":"17574504","is_contact":"0","is_plus":"0","is_pro":"0","is_staff":"0","is_subscribed_to":"0","username":"user17574504","display_name":"Raymond Penners","location":"","url":[""],"bio":"","number_of_contacts":"0","number_of_uploads":"0","number_of_likes":"0","number_of_videos":"0","number_of_videos_appears_in":"0","number_of_albums":"0","number_of_channels":"0","number_of_groups":"0","profileurl":"http:\\/\\/vimeo.com\\/user17574504","videosurl":"http:\\/\\/vimeo.com\\/user17574504\\/videos","portraits":{"portrait":[{"height":"30","width":"30","_content":"http:\\/\\/a.vimeocdn.com\\/images_v6\\/portraits\\/portrait_30_yellow.png"},{"height":"75","width":"75","_content":"http:\\/\\/a.vimeocdn.com\\/images_v6\\/portraits\\/portrait_75_yellow.png"},{"height":"100","width":"100","_content":"http:\\/\\/a.vimeocdn.com\\/images_v6\\/portraits\\/portrait_100_yellow.png"},{"height":"300","width":"300","_content":"http:\\/\\/a.vimeocdn.com\\/images_v6\\/portraits\\/portrait_300_yellow.png"}]}}}
""")]

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import VimeoProvider

urlpatterns = default_urlpatterns(VimeoProvider)

########NEW FILE########
__FILENAME__ = views
import json

from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)
from .provider import VimeoProvider


class VimeoAPI(OAuth):
    url = 'http://vimeo.com/api/rest/v2?method=vimeo.people.getInfo'

    def get_user_info(self):
        url = self.url
        data = json.loads(self.query(url, params=dict(format='json')))
        return data['person']


class VimeoOAuthAdapter(OAuthAdapter):
    provider_id = VimeoProvider.id
    request_token_url = 'https://vimeo.com/oauth/request_token'
    access_token_url = 'https://vimeo.com/oauth/access_token'
    authorize_url = 'https://vimeo.com/oauth/authorize'

    def complete_login(self, request, app, token):
        client = VimeoAPI(request, app.client_id, app.secret,
                          self.request_token_url)
        extra_data = client.get_user_info()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth_login = OAuthLoginView.adapter_view(VimeoOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(VimeoOAuthAdapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class VKAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('link')

    def get_avatar_url(self):
        ret = None
        photo_big_url = self.account.extra_data.get('photo_big')
        photo_medium_url = self.account.extra_data.get('photo_medium')
        if photo_big_url:
            return photo_big_url
        elif photo_medium_url:
            return photo_medium_url
        else:
            return ret

    def to_str(self):
        dflt = super(VKAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class VKProvider(OAuth2Provider):
    id = 'vk'
    name = 'VK'
    package = 'allauth.socialaccount.providers.vk'
    account_class = VKAccount

    def extract_uid(self, data):
        return str(data['uid'])

    def extract_common_fields(self, data):
        return dict(last_name=data.get('last_name'),
                    username=data.get('screen_name'),
                    first_name=data.get('first_name'))


providers.registry.register(VKProvider)

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

from allauth.socialaccount.tests import create_oauth2_tests
from allauth.socialaccount.providers import registry
from allauth.tests import MockedResponse

from .provider import VKProvider


class VKTests(create_oauth2_tests(registry.by_id(VKProvider.id))):

    def get_mocked_response(self, verified_email=True):
        return MockedResponse(200, """
{"response": [{"last_name": "Penners", "university_name": "", "photo": "http://vk.com/images/camera_c.gif", "sex": 2, "photo_medium": "http://vk.com/images/camera_b.gif", "relation": "0", "timezone": 1, "photo_big": "http://vk.com/images/camera_a.gif", "uid": 219004864, "universities": [], "city": "1430", "first_name": "Raymond", "faculty_name": "", "online": 1, "counters": {"videos": 0, "online_friends": 0, "notes": 0, "audios": 0, "photos": 0, "followers": 0, "groups": 0, "user_videos": 0, "albums": 0, "friends": 0}, "home_phone": "", "faculty": 0, "nickname": "", "screen_name": "id219004864", "has_mobile": 1, "country": "139", "university": 0, "graduation": 0, "activity": "", "last_seen": {"time": 1377805189}}]}
""")

    def get_login_response_json(self, with_refresh_token=True):
        return '{"user_id": 219004864, "access_token":"testac"}'

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import VKProvider

urlpatterns = default_urlpatterns(VKProvider)

########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from allauth.socialaccount.models import SocialLogin, SocialAccount
from allauth.socialaccount.adapter import get_adapter

from .provider import VKProvider


USER_FIELDS = ['first_name',
               'last_name',
               'nickname',
               'screen_name',
               'sex',
               'bdate',
               'city',
               'country',
               'timezone',
               'photo',
               'photo_medium',
               'photo_big',
               'has_mobile',
               'contacts',
               'education',
               'online',
               'counters',
               'relation',
               'last_seen',
               'activity',
               'universities']


class VKOAuth2Adapter(OAuth2Adapter):
    provider_id = VKProvider.id
    access_token_url = 'https://oauth.vk.com/access_token'
    authorize_url = 'http://oauth.vk.com/authorize'
    profile_url = 'https://api.vk.com/method/users.get'

    def complete_login(self, request, app, token, **kwargs):
        uid = kwargs['response']['user_id']
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token,
                                    'fields': ','.join(USER_FIELDS),
                                    'user_ids': uid})
        resp.raise_for_status()
        extra_data = resp.json()['response'][0]
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(VKOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(VKOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class WeiboAccount(ProviderAccount):
    def get_profile_url(self):
        # profile_url = "u/3195025850"
        return 'http://www.weibo.com/' + self.account.extra_data.get('profile_url')

    def get_avatar_url(self):
        return self.account.extra_data.get('avatar_large')

    def to_str(self):
        dflt = super(WeiboAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)


class WeiboProvider(OAuth2Provider):
    id = 'weibo'
    name = 'Weibo'
    package = 'allauth.socialaccount.providers.weibo'
    account_class = WeiboAccount

    def extract_uid(self, data):
        return data['idstr']

    def extract_common_fields(self, data):
        return dict(username=data.get('screen_name'),
                    name=data.get('name'))


providers.registry.register(WeiboProvider)

########NEW FILE########
__FILENAME__ = tests
from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import WeiboProvider

class WeiboTests(create_oauth2_tests(registry.by_id(WeiboProvider.id))):
    def get_mocked_response(self):
        return MockedResponse(200, """{"bi_followers_count": 0, "domain": "", "avatar_large": "http://tp3.sinaimg.cn/3195025850/180/0/0", "block_word": 0, "star": 0, "id": 3195025850, "city": "1", "verified": false, "follow_me": false, "verified_reason": "", "followers_count": 6, "location": "\u5317\u4eac \u4e1c\u57ce\u533a", "mbtype": 0, "profile_url": "u/3195025850", "province": "11", "statuses_count": 0, "description": "", "friends_count": 0, "online_status": 0, "mbrank": 0, "idstr": "3195025850", "profile_image_url": "http://tp3.sinaimg.cn/3195025850/50/0/0", "allow_all_act_msg": false, "allow_all_comment": true, "geo_enabled": true, "name": "pennersr", "lang": "zh-cn", "weihao": "", "remark": "", "favourites_count": 0, "screen_name": "pennersr", "url": "", "gender": "f", "created_at": "Tue Feb 19 19:43:39 +0800 2013", "verified_type": -1, "following": false}

""")

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import WeiboProvider

urlpatterns = default_urlpatterns(WeiboProvider)


########NEW FILE########
__FILENAME__ = views
import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from .provider import WeiboProvider


class WeiboOAuth2Adapter(OAuth2Adapter):
    provider_id = WeiboProvider.id
    access_token_url = 'https://api.weibo.com/oauth2/access_token'
    authorize_url = 'https://api.weibo.com/oauth2/authorize'
    profile_url = 'https://api.weibo.com/2/users/show.json'

    def complete_login(self, request, app, token, **kwargs):
        uid = kwargs.get('response', {}).get('uid')
        resp = requests.get(self.profile_url,
                            params={'access_token': token.token,
                                    'uid': uid})
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(WeiboOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(WeiboOAuth2Adapter)

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = provider
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth.provider import OAuthProvider


class XingAccount(ProviderAccount):
    def get_profile_url(self):
        return self.account.extra_data.get('permalink')

    def get_avatar_url(self):
        return self.account.extra_data.get(
            'photo_urls', {}).get('large')

    def to_str(self):
        dflt = super(XingAccount, self).to_str()
        first_name = self.account.extra_data.get('first_name', '')
        last_name = self.account.extra_data.get('last_name', '')
        name = ' '.join([first_name, last_name]).strip()
        return name or dflt


class XingProvider(OAuthProvider):
    id = 'xing'
    name = 'Xing'
    package = 'allauth.socialaccount.providers.xing'
    account_class = XingAccount

    def extract_uid(self, data):
        return data['id']

    def extract_common_fields(self, data):
        return dict(email=data.get('active_email'),
                    username=data.get('page_name'),
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'))

providers.registry.register(XingProvider)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from allauth.socialaccount.tests import create_oauth_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import XingProvider


class XingTests(create_oauth_tests(registry.by_id(XingProvider.id))):
    def get_mocked_response(self):
        return [MockedResponse(200, u"""
{"users":[{"id":"20493333_1cd028","active_email":"raymond.penners@gmail.com",
"badges":[],"birth_date":{"year":null,"month":null,"day":null},
"business_address":{"street":null,"zip_code":null,"city":null,"province":null,
"country":"NL","email":null,"fax":null,"phone":null,"mobile_phone":null},
"display_name":"Raymond Penners","educational_background":
{"primary_school_id":null,"schools":[],"qualifications":[]},
"employment_status":"EMPLOYEE","first_name":"Raymond","gender":"m",
"haves":null,"instant_messaging_accounts":{},"interests":null,"languages":
{"nl":null},"last_name":"Penners","organisation_member":null,
"page_name":"Raymond_Penners",
"permalink":"https://www.xing.com/profile/Raymond_Penners",
"photo_urls":{"thumb":"https://www.xing.com/img/n/nobody_m.30x40.jpg",
"large":"https://www.xing.com/img/n/nobody_m.140x185.jpg","mini_thumb":
"https://www.xing.com/img/n/nobody_m.18x24.jpg","maxi_thumb":
"https://www.xing.com/img/n/nobody_m.70x93.jpg","medium_thumb":
"https://www.xing.com/img/n/nobody_m.57x75.jpg"},"premium_services":[],
"private_address":{"street":null,"zip_code":null,"city":null,"province":null,
"country":null,"email":"raymond.penners@gmail.com","fax":null,
"phone":null,"mobile_phone":null},"professional_experience":
{"primary_company":{"name":null,"url":null,"tag":null,"title":null,
"begin_date":null,"end_date":null,"description":null,"industry":"OTHERS",
"company_size":null,"career_level":null},"non_primary_companies":[],
"awards":[]},"time_zone":{"utc_offset":2.0,"name":"Europe/Berlin"},
"wants":null,"web_profiles":{}}]}

""")]

########NEW FILE########
__FILENAME__ = urls
from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import XingProvider

urlpatterns = default_urlpatterns(XingProvider)

########NEW FILE########
__FILENAME__ = views
import json

from allauth.socialaccount.providers.oauth.client import OAuth
from allauth.socialaccount.providers.oauth.views import (OAuthAdapter,
                                                         OAuthLoginView,
                                                         OAuthCallbackView)

from .provider import XingProvider


class XingAPI(OAuth):
    url = 'https://api.xing.com/v1/users/me.json'

    def get_user_info(self):
        user = json.loads(self.query(self.url))
        return user


class XingOAuthAdapter(OAuthAdapter):
    provider_id = XingProvider.id
    request_token_url = 'https://api.xing.com/v1/request_token'
    access_token_url = 'https://api.xing.com/v1/access_token'
    authorize_url = 'https://www.xing.com/v1/authorize'

    def complete_login(self, request, app, token):
        client = XingAPI(request, app.client_id, app.secret,
                         self.request_token_url)
        extra_data = client.get_user_info()['users'][0]
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)

oauth_login = OAuthLoginView.adapter_view(XingOAuthAdapter)
oauth_callback = OAuthCallbackView.adapter_view(XingOAuthAdapter)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

# Sent after a user successfully authenticates via a social provider,
# but before the login is actually processed. This signal is emitted
# for social logins, signups and when connecting additional social
# accounts to an account.
pre_social_login = Signal(providing_args=["request", "sociallogin"])

# Sent after a user connects a social account to a his local account.
social_account_added = Signal(providing_args=["request", "sociallogin"])

# Sent after a user disconnects a social account from his local
# account.
social_account_removed = Signal(providing_args=["request", "socialaccount"])

########NEW FILE########
__FILENAME__ = socialaccount
from django.template.defaulttags import token_kwargs
from django import template

from allauth.socialaccount import providers

register = template.Library()

class ProviderLoginURLNode(template.Node):
    def __init__(self, provider_id, params):
        self.provider_id_var = template.Variable(provider_id)
        self.params = params

    def render(self, context):
        provider_id = self.provider_id_var.resolve(context)
        provider = providers.registry.by_id(provider_id)
        query = dict([(str(name), var.resolve(context)) for name, var
                      in self.params.items()])
        request = context['request']
        if 'next' not in query:
            next = request.REQUEST.get('next')
            if next:
                query['next'] = next
        else:
            if not query['next']:
                del query['next']
        return provider.get_login_url(request, **query)

@register.tag
def provider_login_url(parser, token):
    """
    {% provider_login_url "facebook" next=bla %}
    {% provider_login_url "openid" openid="http://me.yahoo.com" next=bla %}
    """
    bits = token.split_contents()
    provider_id = bits[1]
    params = token_kwargs(bits[2:], parser, support_legacy=False)
    return ProviderLoginURLNode(provider_id, params)
    
class ProvidersMediaJSNode(template.Node):
    def render(self, context):
        request = context['request']
        ret = '\n'.join([p.media_js(request) 
                         for p in providers.registry.get_list()])
        return ret


@register.tag
def providers_media_js(parser, token):
    return ProvidersMediaJSNode()


@register.assignment_tag
def get_social_accounts(user):
    """
    {% get_social_accounts user as accounts %}

    Then:
        {{accounts.twitter}} -- a list of connected Twitter accounts
        {{accounts.twitter.0}} -- the first Twitter account
        {% if accounts %} -- if there is at least one social account
    """
    accounts = {}
    for account in user.socialaccount_set.all().iterator():
        providers = accounts.setdefault(account.provider, [])
        providers.append(account)
    return accounts

########NEW FILE########
__FILENAME__ = socialaccount_tags
import warnings

warnings.warn("{% load socialaccount_tags %} is deprecated, use"
              " {% load socialaccount %}", DeprecationWarning)

from socialaccount import *

########NEW FILE########
__FILENAME__ = tests
import random
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs
import warnings
import json

from django.test.utils import override_settings
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.test.client import RequestFactory
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser

from ..tests import MockedResponse, mocked_response
from ..account import app_settings as account_settings
from ..account.models import EmailAddress
from ..account.utils import user_email
from ..utils import get_user_model

from .models import SocialApp, SocialAccount, SocialLogin
from .helpers import complete_social_login


def create_oauth_tests(provider):

    def get_mocked_response(self):
        pass

    def setUp(self):
        app = SocialApp.objects.create(provider=provider.id,
                                       name=provider.id,
                                       client_id='app123id',
                                       key=provider.id,
                                       secret='dummy')
        app.sites.add(Site.objects.get_current())

    @override_settings(SOCIALACCOUNT_AUTO_SIGNUP=False)
    def test_login(self):
        resp_mocks = self.get_mocked_response()
        if not resp_mocks:
            warnings.warn("Cannot test provider %s, no oauth mock"
                          % self.provider.id)
            return
        resp = self.login(resp_mocks)
        self.assertRedirects(resp, reverse('socialaccount_signup'))
        resp = self.client.get(reverse('socialaccount_signup'))
        sociallogin = resp.context['form'].sociallogin
        data = dict(email=user_email(sociallogin.account.user),
                    username=str(random.randrange(1000, 10000000)))
        resp = self.client.post(reverse('socialaccount_signup'),
                                data=data)
        self.assertEqual('http://testserver/accounts/profile/',
                         resp['location'])
        self.assertFalse(resp.context['user'].has_usable_password())
        return sociallogin.account

    @override_settings(SOCIALACCOUNT_AUTO_SIGNUP=True,
                       SOCIALACCOUNT_EMAIL_REQUIRED=False,
                       ACCOUNT_EMAIL_REQUIRED=False)
    def test_auto_signup(self):
        resp_mocks = self.get_mocked_response()
        if not resp_mocks:
            warnings.warn("Cannot test provider %s, no oauth mock"
                          % self.provider.id)
            return
        resp = self.login(resp_mocks)
        self.assertEqual('http://testserver/accounts/profile/',
                         resp['location'])
        self.assertFalse(resp.context['user'].has_usable_password())

    def login(self, resp_mocks, process='login'):
        with mocked_response(MockedResponse(200,
                                            'oauth_token=token&'
                                            'oauth_token_secret=psst',
                                            {'content-type':
                                             'text/html'})):
            resp = self.client.get(reverse(self.provider.id + '_login'),
                                   dict(process=process))
        p = urlparse(resp['location'])
        q = parse_qs(p.query)
        complete_url = reverse(self.provider.id+'_callback')
        self.assertGreater(q['oauth_callback'][0]
                           .find(complete_url), 0)
        with mocked_response(MockedResponse(200,
                                            'oauth_token=token&'
                                            'oauth_token_secret=psst',
                                            {'content-type':
                                             'text/html'}),
                             *resp_mocks):
            resp = self.client.get(complete_url)
        return resp

    impl = {'setUp': setUp,
            'login': login,
            'test_login': test_login,
            'get_mocked_response': get_mocked_response}
    class_name = 'OAuth2Tests_'+provider.id
    Class = type(class_name, (TestCase,), impl)
    Class.provider = provider
    return Class


def create_oauth2_tests(provider):

    def get_mocked_response(self):
        pass

    def get_login_response_json(self, with_refresh_token=True):
        rt = ''
        if with_refresh_token:
            rt = ',"refresh_token": "testrf"'
        return """{
            "uid":"weibo",
            "access_token":"testac"
            %s }""" % rt

    def setUp(self):
        app = SocialApp.objects.create(provider=provider.id,
                                       name=provider.id,
                                       client_id='app123id',
                                       key=provider.id,
                                       secret='dummy')
        app.sites.add(Site.objects.get_current())

    @override_settings(SOCIALACCOUNT_AUTO_SIGNUP=False)
    def test_login(self):
        resp_mock = self.get_mocked_response()
        if not resp_mock:
            warnings.warn("Cannot test provider %s, no oauth mock"
                          % self.provider.id)
            return
        resp = self.login(resp_mock,)
        self.assertRedirects(resp, reverse('socialaccount_signup'))

    def test_account_tokens(self, multiple_login=False):
        email = 'some@mail.com'
        user = get_user_model().objects.create(
            username='user',
            is_active=True,
            email=email)
        user.set_password('test')
        user.save()
        EmailAddress.objects.create(user=user,
                                    email=email,
                                    primary=True,
                                    verified=True)
        self.client.login(username=user.username,
                          password='test')
        self.login(self.get_mocked_response(), process='connect')
        if multiple_login:
            self.login(
                self.get_mocked_response(),
                with_refresh_token=False,
                process='connect')
        # get account
        sa = SocialAccount.objects.filter(user=user,
                                          provider=self.provider.id).get()
        # get token
        t = sa.socialtoken_set.get()
        # verify access_token and refresh_token
        self.assertEqual('testac', t.token)
        self.assertEqual(t.token_secret,
                         json.loads(self.get_login_response_json(
                             with_refresh_token=True)).get(
                                 'refresh_token', ''))

    def test_account_refresh_token_saved_next_login(self):
        '''
        fails if a login missing a refresh token, deletes the previously
        saved refresh token. Systems such as google's oauth only send
        a refresh token on first login.
        '''
        self.test_account_tokens(multiple_login=True)

    def login(self, resp_mock, process='login',
              with_refresh_token=True):
        resp = self.client.get(reverse(self.provider.id + '_login'),
                               dict(process=process))
        p = urlparse(resp['location'])
        q = parse_qs(p.query)
        complete_url = reverse(self.provider.id+'_callback')
        self.assertGreater(q['redirect_uri'][0]
                           .find(complete_url), 0)
        response_json = self \
            .get_login_response_json(with_refresh_token=with_refresh_token)
        with mocked_response(
                MockedResponse(
                    200,
                    response_json,
                    {'content-type': 'application/json'}),
                resp_mock):
            resp = self.client.get(complete_url,
                                   {'code': 'test',
                                    'state': q['state'][0]})
        return resp

    impl = {'setUp': setUp,
            'login': login,
            'test_login': test_login,
            'test_account_tokens': test_account_tokens,
            'test_account_refresh_token_saved_next_login':
            test_account_refresh_token_saved_next_login,
            'get_login_response_json': get_login_response_json,
            'get_mocked_response': get_mocked_response}
    class_name = 'OAuth2Tests_'+provider.id
    Class = type(class_name, (TestCase,), impl)
    Class.provider = provider
    return Class


class SocialAccountTests(TestCase):

    @override_settings(
        SOCIALACCOUNT_AUTO_SIGNUP=True,
        ACCOUNT_SIGNUP_FORM_CLASS=None,
        ACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.NONE  # noqa
    )
    def test_email_address_created(self):
        factory = RequestFactory()
        request = factory.get('/accounts/login/callback/')
        request.user = AnonymousUser()
        SessionMiddleware().process_request(request)
        MessageMiddleware().process_request(request)

        User = get_user_model()
        user = User()
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, 'test')
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, 'test@test.com')

        account = SocialAccount(user=user, provider='openid', uid='123')
        sociallogin = SocialLogin(account)
        complete_social_login(request, sociallogin)

        user = User.objects.get(
            **{account_settings.USER_MODEL_USERNAME_FIELD: 'test'}
        )
        self.assertTrue(
            SocialAccount.objects.filter(user=user, uid=account.uid).exists()
        )
        self.assertTrue(
            EmailAddress.objects.filter(user=user,
                                        email=user_email(user)).exists()
        )

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url('^login/cancelled/$', views.login_cancelled, 
        name='socialaccount_login_cancelled'),
    url('^login/error/$', views.login_error, name='socialaccount_login_error'),
    url('^signup/$', views.signup, name='socialaccount_signup'),
    url('^connections/$', views.connections, name='socialaccount_connections'))

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.views.generic.base import View, TemplateView
from django.views.generic.edit import FormView

from ..account.views import (CloseableSignupMixin,
                             RedirectAuthenticatedUserMixin)
from ..account.adapter import get_adapter as get_account_adapter
from .adapter import get_adapter
from .models import SocialLogin
from .forms import DisconnectForm, SignupForm
from . import helpers


class SignupView(RedirectAuthenticatedUserMixin, CloseableSignupMixin,
                 FormView):
    form_class = SignupForm
    template_name = 'socialaccount/signup.html'

    def dispatch(self, request, *args, **kwargs):
        self.sociallogin = None
        data = request.session.get('socialaccount_sociallogin')
        if data:
            self.sociallogin = SocialLogin.deserialize(data)
        if not self.sociallogin:
            return HttpResponseRedirect(reverse('account_login'))
        return super(SignupView, self).dispatch(request, *args, **kwargs)

    def is_open(self):
        return get_adapter().is_open_for_signup(self.request,
                                                self.sociallogin)

    def get_form_kwargs(self):
        ret = super(SignupView, self).get_form_kwargs()
        ret['sociallogin'] = self.sociallogin
        return ret

    def form_valid(self, form):
        form.save(self.request)
        return helpers.complete_social_signup(self.request,
                                              self.sociallogin)

    def get_context_data(self, **kwargs):
        ret = super(SignupView, self).get_context_data(**kwargs)
        ret.update(dict(site=Site.objects.get_current(),
                        account=self.sociallogin.account))
        return ret

    def get_authenticated_redirect_url(self):
        return reverse(connections)

signup = SignupView.as_view()


class LoginCancelledView(TemplateView):
    template_name = "socialaccount/login_cancelled.html"

login_cancelled = LoginCancelledView.as_view()


class LoginErrorView(View):
    def get(self, request):
        return helpers.render_authentication_error(request)

login_error = LoginErrorView.as_view()


class ConnectionsView(FormView):
    template_name = "socialaccount/connections.html"
    form_class = DisconnectForm
    success_url = reverse_lazy("socialaccount_connections")

    def get_form_kwargs(self):
        kwargs = super(ConnectionsView, self).get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        get_account_adapter().add_message(self.request,
                                          messages.INFO,
                                          'socialaccount/messages/'
                                          'account_disconnected.txt')
        form.save()
        return super(ConnectionsView, self).form_valid(form)

connections = login_required(ConnectionsView.as_view())

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

import requests
from datetime import datetime, date

from django.test import TestCase
from django.db import models

from . import utils


class MockedResponse(object):
    def __init__(self, status_code, content, headers={}):
        self.status_code = status_code
        self.content = content.encode('utf8')
        self.headers = headers

    def json(self):
        import json
        return json.loads(self.text)

    def raise_for_status(self):
        pass

    @property
    def text(self):
        return self.content.decode('utf8')


class mocked_response:
    def __init__(self, *responses):
        self.responses = list(responses)

    def __enter__(self):
        self.orig_get = requests.get
        self.orig_post = requests.post
        self.orig_request = requests.request

        def mockable_request(f):
            def new_f(*args, **kwargs):
                if self.responses:
                    return self.responses.pop(0)
                return f(*args, **kwargs)
            return new_f
        requests.get = mockable_request(requests.get)
        requests.post = mockable_request(requests.post)
        requests.request = mockable_request(requests.request)

    def __exit__(self, type, value, traceback):
        requests.get = self.orig_get
        requests.post = self.orig_post
        requests.request = self.orig_request


class BasicTests(TestCase):

    def test_generate_unique_username(self):
        examples = [('a.b-c@gmail.com', 'a.b-c'),
                    (u'Üsêrnamê', 'username'),
                    ('User Name', 'user_name'),
                    ('', 'user')]
        for input, username in examples:
            self.assertEqual(utils.generate_unique_username([input]),
                             username)

    def test_email_validation(self):
        s = 'unfortunately.django.user.email.max_length.is.set.to.75.which.is.too.short@bummer.com'
        self.assertEqual(None, utils.valid_email_or_none(s))
        s = 'this.email.address.is.a.bit.too.long.but.should.still.validate.ok@short.com'
        self.assertEqual(s, utils.valid_email_or_none(s))
        s = 'x' + s
        self.assertEqual(None, utils.valid_email_or_none(s))
        self.assertEqual(None, utils.valid_email_or_none("Bad ?"))

    def test_serializer(self):
        class SomeModel(models.Model):
            dt = models.DateTimeField()
            t = models.TimeField()
            d = models.DateField()
        instance = SomeModel(dt=datetime.now(),
                             d=date.today(),
                             t=datetime.now().time())
        instance.nonfield = 'hello'
        data = utils.serialize_instance(instance)
        instance2 = utils.deserialize_instance(SomeModel, data)
        self.assertEqual(instance.nonfield, instance2.nonfield)
        self.assertEqual(instance.d, instance2.d)
        self.assertEqual(instance.dt.date(), instance2.dt.date())
        for t1, t2 in [(instance.t, instance2.t),
                       (instance.dt.time(), instance2.dt.time())]:
            self.assertEqual(t1.hour, t2.hour)
            self.assertEqual(t1.minute, t2.minute)
            self.assertEqual(t1.second, t2.second)
            # AssertionError: datetime.time(10, 6, 28, 705776) != datetime.time(10, 6, 28, 705000)
            self.assertEqual(int(t1.microsecond / 1000),
                             int(t2.microsecond / 1000))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns, include
from django.utils import importlib

from allauth.socialaccount import providers

from . import app_settings

urlpatterns = patterns('', url('^', include('allauth.account.urls')))

if app_settings.SOCIALACCOUNT_ENABLED:
    urlpatterns += patterns('', url('^social/', 
                                    include('allauth.socialaccount.urls')))

for provider in providers.registry.get_list():
    try:
        prov_mod = importlib.import_module(provider.package + '.urls')
    except ImportError:
        continue
    prov_urlpatterns = getattr(prov_mod, 'urlpatterns', None)
    if prov_urlpatterns:
        urlpatterns += prov_urlpatterns

########NEW FILE########
__FILENAME__ = utils
import re
import unicodedata
import json

from django.core.exceptions import ImproperlyConfigured
from django.core.validators import validate_email, ValidationError
from django.core import urlresolvers
from django.db.models import FieldDoesNotExist
from django.db.models.fields import (DateTimeField, DateField,
                                     EmailField, TimeField)
from django.utils import importlib, six, dateparse
from django.utils.datastructures import SortedDict
from django.core.serializers.json import DjangoJSONEncoder
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


def _generate_unique_username_base(txts):
    username = None
    for txt in txts:
        username = unicodedata.normalize('NFKD', force_text(txt))
        username = username.encode('ascii', 'ignore').decode('ascii')
        username = force_text(re.sub('[^\w\s@+.-]', '', username).lower())
        # Django allows for '@' in usernames in order to accomodate for
        # project wanting to use e-mail for username. In allauth we don't
        # use this, we already have a proper place for putting e-mail
        # addresses (EmailAddress), so let's not use the full e-mail
        # address and only take the part leading up to the '@'.
        username = username.split('@')[0]
        username = username.strip()
        username = re.sub('\s+', '_', username)
        if username:
            break
    return username or 'user'


def generate_unique_username(txts):
    from .account.app_settings import USER_MODEL_USERNAME_FIELD
    username = _generate_unique_username_base(txts)
    User = get_user_model()
    try:
        max_length = User._meta.get_field(USER_MODEL_USERNAME_FIELD).max_length
    except FieldDoesNotExist:
        raise ImproperlyConfigured(
            "USER_MODEL_USERNAME_FIELD does not exist in user-model"
        )
    i = 0
    while True:
        try:
            if i:
                pfx = str(i + 1)
            else:
                pfx = ''
            ret = username[0:max_length - len(pfx)] + pfx
            query = {USER_MODEL_USERNAME_FIELD + '__iexact': ret}
            User.objects.get(**query)
            i += 1
        except User.DoesNotExist:
            return ret


def valid_email_or_none(email):
    ret = None
    try:
        if email:
            validate_email(email)
            if len(email) <= EmailField().max_length:
                ret = email
    except ValidationError:
        pass
    return ret


def email_address_exists(email, exclude_user=None):
    from .account import app_settings as account_settings
    from .account.models import EmailAddress

    emailaddresses = EmailAddress.objects
    if exclude_user:
        emailaddresses = emailaddresses.exclude(user=exclude_user)
    ret = emailaddresses.filter(email__iexact=email).exists()
    if not ret:
        email_field = account_settings.USER_MODEL_EMAIL_FIELD
        if email_field:
            users = get_user_model().objects
            if exclude_user:
                users = users.exclude(pk=exclude_user.pk)
            ret = users.filter(**{email_field+'__iexact': email}).exists()
    return ret


def import_attribute(path):
    assert isinstance(path, six.string_types)
    pkg, attr = path.rsplit('.', 1)
    ret = getattr(importlib.import_module(pkg), attr)
    return ret


def import_callable(path_or_callable):
    if not hasattr(path_or_callable, '__call__'):
        ret = import_attribute(path_or_callable)
    else:
        ret = path_or_callable
    return ret

try:
    from django.contrib.auth import get_user_model
except ImportError:
    # To keep compatibility with Django 1.4
    def get_user_model():
        from . import app_settings
        from django.db.models import get_model

        try:
            app_label, model_name = app_settings.USER_MODEL.split('.')
        except ValueError:
            raise ImproperlyConfigured("AUTH_USER_MODEL must be of the"
                                       " form 'app_label.model_name'")
        user_model = get_model(app_label, model_name)
        if user_model is None:
            raise ImproperlyConfigured("AUTH_USER_MODEL refers to model"
                                       " '%s' that has not been installed"
                                       % app_settings.USER_MODEL)
        return user_model


def resolve_url(to):
    """
    Subset of django.shortcuts.resolve_url (that one is 1.5+)
    """
    try:
        return urlresolvers.reverse(to)
    except urlresolvers.NoReverseMatch:
        # If this doesn't "feel" like a URL, re-raise.
        if '/' not in to and '.' not in to:
            raise
    # Finally, fall back and assume it's a URL
    return to


def serialize_instance(instance):
    """
    Since Django 1.6 items added to the session are no longer pickled,
    but JSON encoded by default. We are storing partially complete models
    in the session (user, account, token, ...). We cannot use standard
    Django serialization, as these are models are not "complete" yet.
    Serialization will start complaining about missing relations et al.
    """
    ret = dict([(k, v)
                for k, v in instance.__dict__.items()
                if not k.startswith('_')])
    return json.loads(json.dumps(ret, cls=DjangoJSONEncoder))


def deserialize_instance(model, data):
    ret = model()
    for k, v in data.items():
        if v is not None:
            try:
                f = model._meta.get_field(k)
                if isinstance(f, DateTimeField):
                    v = dateparse.parse_datetime(v)
                elif isinstance(f, TimeField):
                    v = dateparse.parse_time(v)
                elif isinstance(f, DateField):
                    v = dateparse.parse_date(v)
            except FieldDoesNotExist:
                pass
        setattr(ret, k, v)
    return ret


def set_form_field_order(form, fields_order):
    if isinstance(form.fields, SortedDict):
        form.fields.keyOrder = fields_order
    else:
        # Python 2.7+
        from collections import OrderedDict
        assert isinstance(form.fields, OrderedDict)
        form.fields = OrderedDict((f, form.fields[f])
                                  for f in fields_order)


def build_absolute_uri(request, location, protocol=None):
    uri = request.build_absolute_uri(location)
    if protocol:
        uri = protocol + ':' + uri.partition(':')[2]
    return uri

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-allauth documentation build configuration file, created by
# sphinx-quickstart on Wed Jun  6 22:58:42 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-allauth'
copyright = u'2014, Raymond Penners'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.16.1'
# The full version, including alpha/beta/rc tags.
release = '0.16.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-allauthdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-allauth.tex', u'django-allauth Documentation',
   u'Raymond Penners', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-allauth', u'django-allauth Documentation',
     [u'Raymond Penners'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-allauth', u'django-allauth Documentation',
   u'Raymond Penners', 'django-allauth', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = models
import sys

from django.db.models.signals import post_syncdb
from django.contrib.sites.models import Site

from allauth.socialaccount.providers import registry
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth.provider import OAuthProvider
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

def setup_dummy_social_apps(sender, **kwargs):
    """
    `allauth` needs tokens for OAuth based providers. So let's
    setup some dummy tokens
    """
    site = Site.objects.get_current()
    for provider in registry.get_list():
        if (isinstance(provider, OAuth2Provider) 
            or isinstance(provider, OAuthProvider)):
            try:
                SocialApp.objects.get(provider=provider.id,
                                      sites=site)
            except SocialApp.DoesNotExist:
                print ("Installing dummy application credentials for %s."
                       " Authentication via this provider will not work"
                       " until you configure proper credentials via the"
                       " Django admin (`SocialApp` models)" % provider.id)
                app = SocialApp.objects.create(provider=provider.id,
                                               secret='secret',
                                               client_id='client-id',
                                               name='Dummy %s app' % provider.id)
                app.sites.add(site)


# We don't want to interfere with unittests et al
if 'syncdb' in sys.argv:
    post_syncdb.connect(setup_dummy_social_apps, sender=sys.modules[__name__])

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
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
import os

PROJECT_ROOT = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_ROOT, 'example.db'), # Or path to database file if using sqlite3.
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

LOCALE_PATHS = ( os.path.join(PROJECT_ROOT, 'locale'), )


# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
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
SECRET_KEY = 't8_)kj3v!au0!_i56#gre**mkg0&z1df%3bw(#5^#^5e_64!$_'

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
)

AUTHENTICATION_BACKENDS = (
    "allauth.account.auth_backends.AuthenticationBackend",
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",

    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",
)

TEMPLATE_DIRS = (
    # allauth templates: you could copy this directory into your
    # project and tweak it according to your needs
    # os.path.join(PROJECT_ROOT, 'templates', 'uniform', 'allauth'),
    # example project specific templates
    os.path.join(PROJECT_ROOT, 'templates', 'plain', 'example')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.dropbox',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.linkedin',
    'allauth.socialaccount.providers.openid',
    'allauth.socialaccount.providers.persona',
    'allauth.socialaccount.providers.soundcloud',
    'allauth.socialaccount.providers.stackexchange',
    'allauth.socialaccount.providers.twitch',
    'allauth.socialaccount.providers.twitter',
    'allauth.socialaccount.providers.vimeo',
    'allauth.socialaccount.providers.weibo',
    'allauth.socialaccount.providers.xing',

    'example.demo'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
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


try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import TemplateView
admin.autodiscover()

urlpatterns = patterns('',
                       (r'^accounts/', include('allauth.urls')),
                       url(r'^$', TemplateView.as_view(template_name='index.html')),
                       url(r'^accounts/profile/$', TemplateView.as_view(template_name='profile.html')),
                       url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
from django.core import management
if __name__ == "__main__":
    management.execute_from_command_line()

########NEW FILE########
__FILENAME__ = test_settings
# -*- coding: utf-8 -*-

SECRET_KEY = 'psst'
SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

ROOT_URLCONF = 'allauth.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",

    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.amazon',
    'allauth.socialaccount.providers.angellist',
    'allauth.socialaccount.providers.bitbucket',
    'allauth.socialaccount.providers.bitly',
    'allauth.socialaccount.providers.dropbox',
    'allauth.socialaccount.providers.feedly',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.flickr',
    'allauth.socialaccount.providers.foursquare',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.hubic',
    'allauth.socialaccount.providers.instagram',
    'allauth.socialaccount.providers.linkedin',
    'allauth.socialaccount.providers.linkedin_oauth2',
    'allauth.socialaccount.providers.openid',
    'allauth.socialaccount.providers.paypal',
    'allauth.socialaccount.providers.persona',
    'allauth.socialaccount.providers.soundcloud',
    'allauth.socialaccount.providers.stackexchange',
    'allauth.socialaccount.providers.tumblr',
    'allauth.socialaccount.providers.twitch',
    'allauth.socialaccount.providers.twitter',
    'allauth.socialaccount.providers.vimeo',
    'allauth.socialaccount.providers.weibo',
    'allauth.socialaccount.providers.vk',
    'allauth.socialaccount.providers.xing',
)

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

STATIC_ROOT = '/tmp/'  # Dummy
STATIC_URL = '/static/'

########NEW FILE########
