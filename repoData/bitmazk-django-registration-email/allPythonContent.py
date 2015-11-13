__FILENAME__ = auth
"""
Custom authentication backends.

Inspired by http://djangosnippets.org/snippets/2463/

"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.validators import validate_email


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows to login with an email address.

    """

    supports_object_permissions = True
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, username=None, password=None):
        try:
            validate_email(username)
        except:
            username_is_email = False
        else:
            username_is_email = True
        if username_is_email:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None
        else:
            #We have a non-email address username we should try username
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = auth_urls
"""
Re-definition of Django's auth URLs.

This is done for convenience. It allows us to save all registration and auth
related templates in the same `/templates/registration/` folder.

"""
from django.conf.urls import url, patterns
from django.contrib.auth import views as auth_views
from registration_email.forms import EmailAuthenticationForm

from .views import login_remember_me


urlpatterns = patterns(
    '',
    url(
        r'^login/$',
        login_remember_me,
        {'template_name': 'registration/login.html',
         'authentication_form': EmailAuthenticationForm, },
        name='auth_login',
    ),
    url(
        r'^logout/$',
        auth_views.logout,
        {'template_name': 'registration/logout.html'},
        name='auth_logout',
    ),
    url(
        r'^password/change/$',
        auth_views.password_change,
        {'template_name': 'registration/password_change_form_custom.html'},
        name='auth_password_change',
    ),
    url(
        r'^password/change/done/$',
        auth_views.password_change_done,
        {'template_name': 'registration/password_change_done_custom.html'},
        name='auth_password_change_done',
    ),
    url(
        r'^password/reset/$',
        auth_views.password_reset,
        {'template_name': 'registration/password_reset_form.html'},
        name='auth_password_reset',
    ),
    url(
        r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        {'template_name': 'registration/password_reset_confirm.html'},
        name='auth_password_reset_confirm',
    ),
    url(
        r'^password/reset/complete/$',
        auth_views.password_reset_complete,
        {'template_name': 'registration/password_reset_complete.html'},  # NOQA
        name='auth_password_reset_complete',
    ),
    url(
        r'^password/reset/done/$',
        auth_views.password_reset_done,
        {'template_name': 'registration/password_reset_done.html'},
        name='auth_password_reset_done',
    ),
)

########NEW FILE########
__FILENAME__ = urls
"""Custom urls.py for django-registration."""
from django.conf import settings
from django.conf.urls import include, url, patterns
from django.views.generic import TemplateView

from registration.backends.default.views import (
    ActivationView,
    RegistrationView,
)
from registration_email.forms import EmailRegistrationForm


urlpatterns = patterns(
    '',
    # django-registration views
    url(r'^activate/complete/$',
        TemplateView.as_view(
            template_name='registration/activation_complete.html'),
        name='registration_activation_complete'),
    url(r'^activate/(?P<activation_key>\w+)/$',
        ActivationView.as_view(
            template_name='registration/activate.html',
            get_success_url=getattr(
                settings, 'REGISTRATION_EMAIL_ACTIVATE_SUCCESS_URL',
                lambda request, user: '/'),
        ),
        name='registration_activate'),
    url(r'^register/$',
        RegistrationView.as_view(
            form_class=EmailRegistrationForm,
            get_success_url=getattr(
                settings, 'REGISTRATION_EMAIL_REGISTER_SUCCESS_URL',
                lambda request, user: '/'),
        ),
        name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),

    # django auth urls
    url(r'', include('registration_email.auth_urls')),
)

########NEW FILE########
__FILENAME__ = urls
"""
URLconf for registration and activation, using django-registration's
one-step backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('registration_email.backends.simple.urls')),

This will also automatically set up the views in
``django.contrib.auth`` at sensible default locations.

If you'd like to customize registration behavior, feel free to set up
your own URL patterns for these views instead.

"""
from django.conf import settings
from django.conf.urls import include, patterns, url
from django.views.generic.base import TemplateView

from registration.backends.simple.views import RegistrationView
from registration_email.forms import EmailRegistrationForm


urlpatterns = patterns(
    '',
    url(r'^register/$',
        RegistrationView.as_view(
            form_class=EmailRegistrationForm,
            get_success_url=getattr(
                settings, 'REGISTRATION_EMAIL_REGISTER_SUCCESS_URL',
                lambda request, user: '/'),
        ),
        name='registration_register'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),
    (r'', include('registration_email.auth_urls')),
)

########NEW FILE########
__FILENAME__ = forms
"""Custom registration forms that expects an email address as a username."""
import hashlib
import os

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = {'class': 'required'}


def get_md5_hexdigest(email):
    """
    Returns an md5 hash for a given email.

    The length is 30 so that it fits into Django's ``User.username`` field.

    """
    if isinstance(email, str):  # for py3
        email = email.encode('utf-8')
    return hashlib.md5(email).hexdigest()[0:30]


def generate_username(email):
    """
    Generates a unique username for the given email.

    The username will be an md5 hash of the given email. If the username exists
    we just append `a` to the email until we get a unique md5 hash.

    """
    try:
        User.objects.get(email=email)
        raise Exception('Cannot generate new username. A user with this email'
                        'already exists.')
    except User.DoesNotExist:
        pass

    username = get_md5_hexdigest(email)
    found_unique_username = False
    while not found_unique_username:
        try:
            User.objects.get(username=username)
            email = '{0}a'.format(email.lower())
            username = get_md5_hexdigest(email)
        except User.DoesNotExist:
            found_unique_username = True
            return username


class EmailAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False,
        label=_('Remember me'),
    )

    def __init__(self, *args, **kwargs):
        super(EmailAuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'] = forms.CharField(
            label=_("Email"), max_length=256)

    def clean_username(self):
        """Prevent case-sensitive erros in email/username."""
        return self.cleaned_data['username'].lower()


class EmailRegistrationForm(forms.Form):
    """
    Form for registering a new user account.

    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.

    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.

    """
    email = forms.EmailField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=256)),
        label=_("Email")
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
        label=_("Password")
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
        label=_("Password (repeat)"))
    your_name = forms.CharField(required=False)

    def clean_email(self):
        """
        Validate that the username is alphanumeric and is not already
        in use.

        """
        email = self.cleaned_data['email'].strip()
        try:
            User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return email.lower()
        raise forms.ValidationError(
            _('A user with that email already exists.'))

    def clean(self):
        """
        Verifiy that the values entered into the two password fields match.

        Note that an error here will end up in ``non_field_errors()`` because
        it doesn't apply to a single field.

        """
        data = self.cleaned_data
        if data.get('your_name'):
            # Bot protection. The name field is not visible for human users.
            raise forms.ValidationError(_('Please enter a valid name.'))
        if not 'email' in data:
            return data
        if ('password1' in data and 'password2' in data):

            if data['password1'] != data['password2']:
                raise forms.ValidationError(
                    _("The two password fields didn't match."))

        self.cleaned_data['username'] = generate_username(data['email'])
        return self.cleaned_data

    class Media:
        css = {
            'all': (os.path.join(
                settings.STATIC_URL, 'registration_email/css/auth.css'), )
        }

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
"""Views for the registration_email app."""
from django.contrib.auth.views import login


def login_remember_me(request, *args, **kwargs):
    """Custom login view that enables "remember me" functionality."""
    if request.method == 'POST':
        if not request.POST.get('remember_me', None):
            request.session.set_expiry(0)
    return login(request, *args, **kwargs)

########NEW FILE########
