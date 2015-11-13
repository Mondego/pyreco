__FILENAME__ = admin
from __future__ import unicode_literals

import copy

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from authtools.models import User
from authtools.forms import UserCreationForm, AdminUserChangeForm

USERNAME_FIELD = get_user_model().USERNAME_FIELD

REQUIRED_FIELDS = (USERNAME_FIELD,) + tuple(get_user_model().REQUIRED_FIELDS)

BASE_FIELDS = (None, {
    'fields': REQUIRED_FIELDS + ('password',),
})

SIMPLE_PERMISSION_FIELDS = (_('Permissions'), {
    'fields': ('is_active', 'is_staff', 'is_superuser',),
})

ADVANCED_PERMISSION_FIELDS = copy.deepcopy(SIMPLE_PERMISSION_FIELDS)
ADVANCED_PERMISSION_FIELDS[1]['fields'] += ('groups', 'user_permissions',)

DATE_FIELDS = (_('Important dates'), {
    'fields': ('last_login', 'date_joined',),
})


class StrippedUserAdmin(DjangoUserAdmin):
    # The forms to add and change user instances
    add_form_template = None
    add_form = UserCreationForm
    form = AdminUserChangeForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('is_active', USERNAME_FIELD, 'is_superuser', 'is_staff',)
    list_display_links = (USERNAME_FIELD,)
    list_filter = ('is_superuser', 'is_staff', 'is_active',)
    fieldsets = (
        BASE_FIELDS,
        SIMPLE_PERMISSION_FIELDS,
    )
    add_fieldsets = (
        (None, {
            'fields': REQUIRED_FIELDS + (
                'password1',
                'password2',
            ),
        }),
    )
    search_fields = (USERNAME_FIELD,)
    ordering = None
    filter_horizontal = tuple()
    readonly_fields = ('last_login', 'date_joined')


class StrippedNamedUserAdmin(StrippedUserAdmin):
    list_display = ('is_active', 'email', 'name', 'is_superuser', 'is_staff',)
    list_display_links = ('email', 'name',)
    search_fields = ('email', 'name',)


class UserAdmin(StrippedUserAdmin):
    fieldsets = (
        BASE_FIELDS,
        ADVANCED_PERMISSION_FIELDS,
        DATE_FIELDS,
    )
    filter_horizontal = ('groups', 'user_permissions',)


class NamedUserAdmin(UserAdmin, StrippedNamedUserAdmin):
    pass


# If the model has been swapped, this is basically a noop.
admin.site.register(User, NamedUserAdmin)

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms, VERSION as DJANGO_VERSION
from django.contrib.auth.forms import ReadOnlyPasswordHashField, ReadOnlyPasswordHashWidget
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.html import format_html

User = get_user_model()


def is_password_usable(pw):
    # like Django's is_password_usable, but only checks for unusable
    # passwords, not invalidly encoded passwords too.
    try:
        # 1.5
        from django.contrib.auth.hashers import UNUSABLE_PASSWORD
        return pw != UNUSABLE_PASSWORD
    except ImportError:
        # 1.6
        from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
        return not pw.startswith(UNUSABLE_PASSWORD_PREFIX)


class BetterReadOnlyPasswordHashWidget(ReadOnlyPasswordHashWidget):
    """
    A ReadOnlyPasswordHashWidget that has a less intimidating output.
    """
    def render(self, name, value, attrs):
        from django.forms.util import flatatt
        final_attrs = flatatt(self.build_attrs(attrs))

        if not value or not is_password_usable(value):
            summary = ugettext("No password set.")
        else:
            try:
                identify_hasher(value)
            except ValueError:
                summary = ugettext("Invalid password format or unknown"
                                   " hashing algorithm.")
            else:
                summary = ugettext('*************')

        return format_html('<div{attrs}><strong>{summary}</strong></div>',
                           attrs=final_attrs, summary=summary)


class UserCreationForm(forms.ModelForm):
    """
    A form for creating new users. Includes all the required
    fields, plus a repeated password.
    """

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'duplicate_username': _("A user with that %(username)s already exists."),
    }

    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
                                widget=forms.PasswordInput,
                                help_text=_("Enter the same password as above,"
                                            " for verification."))

    class Meta:
        model = User
        fields = (User.USERNAME_FIELD,) + tuple(User.REQUIRED_FIELDS)

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)

        def validate_uniqueness_of_username_field(value):
            # Since User.username is unique, this check is redundant,
            # but it sets a nicer error message than the ORM. See #13147.
            try:
                User._default_manager.get_by_natural_key(value)
            except User.DoesNotExist:
                return value
            raise forms.ValidationError(self.error_messages['duplicate_username'] % {
                'username': User.USERNAME_FIELD,
            })

        self.fields[User.USERNAME_FIELD].validators.append(validate_uniqueness_of_username_field)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(self.error_messages['password_mismatch'])
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """
    A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(label=_("Password"),
        widget=BetterReadOnlyPasswordHashWidget)

    class Meta:
        model = User
        if DJANGO_VERSION >= (1, 6):
            fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class AdminUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(AdminUserChangeForm, self).__init__(*args, **kwargs)
        if not self.fields['password'].help_text:
            self.fields['password'].help_text = _(
                "Raw passwords are not stored, so there is no way to see this"
                " user's password, but you can change the password using"
                " <a href=\"password/\">this form</a>.")

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.core.mail import send_mail
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **kwargs):
        email = self.normalize_email(email)
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, **kwargs):
        user = self.create_user(**kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class AbstractEmailUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), max_length=255, unique=True,
                              db_index=True,)

    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active.  Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        abstract = True
        ordering = ['email']

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

@python_2_unicode_compatible
class AbstractNamedUser(AbstractEmailUser):
    name = models.CharField(_('name'), max_length=255)

    REQUIRED_FIELDS = ['name']

    class Meta:
        abstract = True
        ordering = ['name', 'email']

    def __str__(self):
        return '{name} <{email}>'.format(
            name=self.name,
            email=self.email,
        )

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name


class User(AbstractNamedUser):
    class Meta(AbstractNamedUser.Meta):
        swappable = 'AUTH_USER_MODEL'
        verbose_name = _('user')
        verbose_name_plural = _('users')

########NEW FILE########
__FILENAME__ = urls
import django
from django.conf.urls import patterns, url


urlpatterns = patterns('authtools.views',
    url(r'^login/$', 'login', name='login'),
    url(r'^logout/$', 'logout', name='logout'),
    url(r'^password_change/$', 'password_change', name='password_change'),
    url(r'^password_change/done/$', 'password_change_done', name='password_change_done'),
    url(r'^password_reset/$', 'password_reset', name='password_reset'),
    url(r'^password_reset/done/$', 'password_reset_done', name='password_reset_done'),
    url(r'^reset/done/$', 'password_reset_complete', name='password_reset_complete'),
)

if django.VERSION < (1, 6):
    urlpatterns += patterns('authtools.views',
        url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            'password_reset_confirm',
            name='password_reset_confirm'),
    )
else:
    urlpatterns += patterns('authtools.views',
        url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            'password_reset_confirm_uidb36'),
        url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            'password_reset_confirm',
            name='password_reset_confirm'),
    )

########NEW FILE########
__FILENAME__ = views
"""
Mostly equivalent to the views from django.contrib.auth.views, but
implemented as class-based views.
"""
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model, REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (AuthenticationForm, SetPasswordForm,
                                       PasswordChangeForm, PasswordResetForm)
from django.contrib.auth.tokens import default_token_generator
from django.contrib import auth
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect, resolve_url
from django.utils.functional import lazy
from django.utils.http import base36_to_int, is_safe_url
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView, TemplateView, RedirectView


User = get_user_model()

resolve_url_lazy = lazy(resolve_url, str)


class WithCurrentSiteMixin(object):
    def get_current_site(self):
        return get_current_site(self.request)

    def get_context_data(self, **kwargs):
        kwargs = super(WithCurrentSiteMixin, self).get_context_data(**kwargs)
        current_site = self.get_current_site()
        kwargs.update({
            'site': current_site,
            'site_name': current_site.name,
        })
        return kwargs


class WithNextUrlMixin(object):
    redirect_field_name = REDIRECT_FIELD_NAME
    success_url = None

    def get_next_url(self):
        if self.redirect_field_name in self.request.REQUEST:
            redirect_to = self.request.REQUEST[self.redirect_field_name]
            if is_safe_url(redirect_to, host=self.request.get_host()):
                return redirect_to

    # This mixin can be mixed with FormViews and RedirectViews. They
    # each use a different method to get the URL to redirect to, so we
    # need to provide both methods.
    def get_success_url(self):
        return self.get_next_url() or super(WithNextUrlMixin, self).get_success_url()

    def get_redirect_url(self, **kwargs):
        return self.get_next_url() or super(WithNextUrlMixin, self).get_redirect_url(**kwargs)


def DecoratorMixin(decorator):
    """
    Converts a decorator written for a function view into a mixin for a
    class-based view.

    ::

        LoginRequiredMixin = DecoratorMixin(login_required)

        class MyView(LoginRequiredMixin):
            pass

        class SomeView(DecoratorMixin(some_decorator),
                       DecoratorMixin(something_else)):
            pass

    """

    class Mixin(object):
        __doc__ = decorator.__doc__

        @classmethod
        def as_view(cls, *args, **kwargs):
            view = super(Mixin, cls).as_view(*args, **kwargs)
            return decorator(view)

    Mixin.__name__ = str('DecoratorMixin(%s)' % decorator.__name__)
    return Mixin


NeverCacheMixin = DecoratorMixin(never_cache)
CsrfProtectMixin = DecoratorMixin(csrf_protect)
LoginRequiredMixin = DecoratorMixin(login_required)
SensitivePostParametersMixin = DecoratorMixin(
    sensitive_post_parameters('password', 'old_password', 'password1',
                              'password2', 'new_password1', 'new_password2')
)

class AuthDecoratorsMixin(NeverCacheMixin, CsrfProtectMixin, SensitivePostParametersMixin):
    pass


class LoginView(AuthDecoratorsMixin, WithCurrentSiteMixin, WithNextUrlMixin, FormView):
    form_class = AuthenticationForm
    template_name = 'registration/login.html'
    disallow_authenticated = True
    success_url = resolve_url_lazy(settings.LOGIN_REDIRECT_URL)

    def dispatch(self, *args, **kwargs):
        if self.disallow_authenticated and self.request.user.is_authenticated():
            return redirect(self.get_success_url())
        return super(LoginView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        auth.login(self.request, form.get_user())
        return super(LoginView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs = super(LoginView, self).get_context_data(**kwargs)
        kwargs.update({
            self.redirect_field_name: self.request.REQUEST.get(
                self.redirect_field_name, '',
            ),
        })
        return kwargs

login = LoginView.as_view()


class LogoutView(NeverCacheMixin, WithCurrentSiteMixin, WithNextUrlMixin, TemplateView, RedirectView):
    template_name = 'registration/logged_out.html'
    permanent = False

    def get(self, *args, **kwargs):
        auth.logout(self.request)
        # If we have a url to redirect to, do it. Otherwise render the logged-out template.
        if self.get_redirect_url(**kwargs):
            return RedirectView.get(self, *args, **kwargs)
        else:
            return TemplateView.get(self, *args, **kwargs)

logout = LogoutView.as_view()
logout_then_login = LogoutView.as_view(
    url=reverse_lazy('login')
)


class PasswordChangeView(LoginRequiredMixin, AuthDecoratorsMixin, FormView):
    template_name = 'registration/password_change_form.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('password_change_done')

    def get_form_kwargs(self):
        kwargs = super(PasswordChangeView, self).get_form_kwargs()
        kwargs['user'] = self.get_user()
        return kwargs

    def get_user(self):
        return self.request.user

    def form_valid(self, form):
        form.save()
        return super(PasswordChangeView, self).form_valid(form)

password_change = PasswordChangeView.as_view()


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/password_change_done.html'

password_change_done = PasswordChangeDoneView.as_view()


# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and
#   prompts for a new password
# - password_reset_complete shows a success message for the above


class PasswordResetView(CsrfProtectMixin, FormView):
    template_name = 'registration/password_reset_form.html'
    token_generator = default_token_generator
    success_url = reverse_lazy('password_reset_done')
    domain_override = None
    subject_template_name = 'registration/password_reset_subject.txt'
    email_template_name = 'registration/password_reset_email.html'
    from_email = None
    form_class = PasswordResetForm

    def form_valid(self, form):
        form.save(
            domain_override=self.domain_override,
            subject_template_name=self.subject_template_name,
            email_template_name=self.email_template_name,
            token_generator=self.token_generator,
            from_email=self.from_email,
            request=self.request,
        )
        return super(PasswordResetView, self).form_valid(form)

password_reset = PasswordResetView.as_view()


class PasswordResetDoneView(TemplateView):
    template_name = 'registration/password_reset_done.html'

password_reset_done = PasswordResetDoneView.as_view()


class PasswordResetConfirmView(AuthDecoratorsMixin, FormView):
    template_name = 'registration/password_reset_confirm.html'
    token_generator = default_token_generator
    form_class = SetPasswordForm
    success_url = reverse_lazy('password_reset_complete')

    def dispatch(self, *args, **kwargs):
        assert self.kwargs.get('token') is not None
        self.user = self.get_user()
        return super(PasswordResetConfirmView, self).dispatch(*args, **kwargs)

    def get_user(self):
        # django 1.5 uses uidb36, django 1.6 uses uidb64
        uidb36 = self.kwargs.get('uidb36')
        uidb64 = self.kwargs.get('uidb64')
        assert bool(uidb36) ^ bool(uidb64)
        try:
            if uidb36:
                uid = base36_to_int(uidb36)
            else:
                # urlsafe_base64_decode is not available in django 1.5
                from django.utils.http import urlsafe_base64_decode
                uid = urlsafe_base64_decode(uidb64)
            return User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def valid_link(self):
        user = self.user
        return user is not None and self.token_generator.check_token(user, self.kwargs.get('token'))

    def get_form_kwargs(self):
        kwargs = super(PasswordResetConfirmView, self).get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(PasswordResetConfirmView, self).get_context_data(**kwargs)
        if self.valid_link():
            kwargs['validlink'] = True
        else:
            kwargs['validlink'] = False
            kwargs['form'] = None
        return kwargs

    def form_valid(self, form):
        if not self.valid_link():
            return self.form_invalid(form)
        self.save_form(form)
        return super(PasswordResetConfirmView, self).form_valid(form)

    def save_form(self, form):
        return form.save()


password_reset_confirm = PasswordResetConfirmView.as_view()

# Django 1.6 added this as a temporary shim, see #14881. Since our view
# works with base 36 or base 64, we can use the same view for both.
password_reset_confirm_uidb36 = PasswordResetConfirmView.as_view()


class PasswordResetConfirmAndLoginView(PasswordResetConfirmView):
    success_url = resolve_url_lazy(settings.LOGIN_REDIRECT_URL)

    def save_form(self, form):
        ret = super(PasswordResetConfirmAndLoginView, self).save_form(form)
        user = auth.authenticate(username=self.user.get_username(),
                                 password=form.cleaned_data['new_password1'])
        auth.login(self.request, user)
        return ret

password_reset_confirm_and_login = PasswordResetConfirmAndLoginView.as_view()


class PasswordResetCompleteView(TemplateView):
    template_name = 'registration/password_reset_complete.html'
    login_url = settings.LOGIN_URL

    def get_login_url(self):
        return resolve_url(self.login_url)

    def get_context_data(self, **kwargs):
        kwargs = super(PasswordResetCompleteView, self).get_context_data(**kwargs)
        kwargs['login_url'] = self.get_login_url()
        return kwargs

password_reset_complete = PasswordResetCompleteView.as_view()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-authtools documentation build configuration file, created by
# sphinx-quickstart on Thu May 23 14:33:19 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.append(os.path.abspath('_themes'))
sys.path.append(os.path.abspath('_ext'))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode',
              'sphinx.ext.intersphinx', 'djangodocs']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-authtools'
copyright = u'2013, Fusionbox, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1.0'

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'kr'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
htmlhelp_basename = 'django-authtoolsdoc'


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
    ('index', 'django-authtools.tex', u'django-authtools Documentation',
     u'Fusionbox, Inc.', 'manual'),
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
    ('index', 'django-authtools', u'django-authtools Documentation',
     [u'Fusionbox, Inc.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'django-authtools', u'django-authtools Documentation',
     u'Fusionbox, Inc.', 'django-authtools', 'A custom User model for everybody!',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

intersphinx_mapping = {
    'django': ('https://docs.djangoproject.com/en/1.5/', 'https://docs.djangoproject.com/en/1.5/_objects/'),
}

sys.path.insert(0, os.path.abspath('../tests'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.utils.crypto import get_random_string

from authtools.admin import NamedUserAdmin
from authtools.forms import UserCreationForm

User = get_user_model()


class UserCreationForm(UserCreationForm):
    """
    A UserCreationForm with optional password inputs.
    """

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        # If one field gets autocompleted but not the other, our 'neither
        # password or both password' validation will be triggered.
        self.fields['password1'].widget.attrs['autocomplete'] = 'off'
        self.fields['password2'].widget.attrs['autocomplete'] = 'off'

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = super(UserCreationForm, self).clean_password2()
        if bool(password1) ^ bool(password2):
            raise forms.ValidationError("Fill out both fields")
        return password2


class UserAdmin(NamedUserAdmin):
    """
    A UserAdmin that sends a password-reset email when creating a new user,
    unless a password was entered.
    """
    add_form = UserCreationForm
    add_fieldsets = (
        (None, {
            'description': (
                "Enter the new user's name and email address and click save."
                " The user will be emailed a link allowing them to login to"
                " the site and set their password."
            ),
            'fields': ('email', 'name',),
        }),
        ('Password', {
            'description': "Optionally, you may set the user's password here.",
            'fields': ('password1', 'password2'),
            'classes': ('collapse', 'collapse-closed'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.has_usable_password():
            # Django's PasswordResetForm won't let us reset an unusable
            # password. We set it above super() so we don't have to save twice.
            obj.set_password(get_random_string())
            reset_password = True
        else:
            reset_password = False

        super(UserAdmin, self).save_model(request, obj, form, change)

        if reset_password:
            reset_form = PasswordResetForm({'email': obj.email})
            assert reset_form.is_valid()
            reset_form.save(
                subject_template_name='registration/account_creation_subject.txt',
                email_template_name='registration/account_creation_email.html',
            )

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

########NEW FILE########
__FILENAME__ = djangodocs
def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys
import warnings

warnings.simplefilter('error')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from authtools.models import AbstractEmailUser


class User(AbstractEmailUser):
    full_name = models.CharField('full name', max_length=255, blank=True)
    preferred_name = models.CharField('preferred name', max_length=255,
                                      blank=True)

    REQUIRED_FIELDS = ['full_name', 'preferred_name']

    class Meta:
        # We need this line to prevent manage.py validate clashes.
        swappable = 'AUTH_USER_MODEL'

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.preferred_name

########NEW FILE########
__FILENAME__ = settings
from __future__ import print_function

import os

SECRET_KEY = 'w6bidenrf5q%byf-q82b%pli50i0qmweus6gt_3@k$=zg7ymd3'

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'tests',
    'authtools',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite_database',
    }
}

ROOT_URLCONF = 'tests.urls'

STATIC_URL = '/static/'
DEBUG = True

AUTH_USER_MODEL = os.environ.get('AUTH_USER_MODEL', 'auth.User')

print('Using %s as the AUTH_USER_MODEL.' % AUTH_USER_MODEL)

########NEW FILE########
__FILENAME__ = sqlite_test_settings
from __future__ import absolute_import

from tests.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '',
    }
}

########NEW FILE########
__FILENAME__ = tests
"""
We're able to borrow most of django's auth view tests.

"""

from django.core import mail
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site, RequestSite
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.utils.http import urlquote
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import unittest
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.forms.fields import Field
from django.conf import settings

try:
    # Django 1.6
    from django.contrib.auth.tests.test_views import (
        AuthViewNamedURLTests,
        PasswordResetTest,
        ChangePasswordTest,
        LoginTest,
        LoginURLSettings,
        LogoutTest,
    )
except ImportError:
    # Django 1.5
    from django.contrib.auth.tests.views import (
        AuthViewNamedURLTests,
        PasswordResetTest,
        ChangePasswordTest,
        LoginTest,
        LoginURLSettings,
        LogoutTest,
    )

from authtools.admin import BASE_FIELDS
from authtools.forms import UserCreationForm, UserChangeForm
from authtools.views import PasswordResetCompleteView

User = get_user_model()


def skipIfNotCustomUser(test_func):
    return unittest.skipIf(settings.AUTH_USER_MODEL == 'auth.User', 'Built-in User model in use')(test_func)


class AuthViewNamedURLTests(AuthViewNamedURLTests):
    urls = 'authtools.urls'


class PasswordResetTest(PasswordResetTest):
    urls = 'tests.urls'

    # these use custom, test-specific urlpatterns that we don't have
    test_admin_reset = None
    test_reset_custom_redirect = None
    test_reset_custom_redirect_named = None
    test_email_found_custom_from = None
    test_confirm_redirect_custom = None
    test_confirm_redirect_custom_named = None

    def test_user_only_fetched_once(self):
        url, confirm_path = self._test_confirm_start()
        with self.assertNumQueries(1):
            # the confirm view is only allowed to fetch the user object a
            # single time
            self.client.get(confirm_path)

    def test_confirm_invalid_path(self):
        # django has a similar test, but it tries to test an invalid path AND
        # an invalid form at the same time. We need a test case with an invalid
        # path, but valid form.
        url, path = self._test_confirm_start()
        path = path[:-5] + ("0" * 4) + path[-1]

        self.client.post(path, {
            'new_password1': 'anewpassword',
            'new_password2': 'anewpassword',
        })
        # Check the password has not been changed
        u = User.objects.get(email='staffmember@example.com')
        self.assertTrue(not u.check_password("anewpassword"))

    def test_confirm_done(self):
        """
        Password reset complete page should be rendered with 'login_url'
        in its context.
        """
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)

        response = self.client.get(response['Location'])

        self.assertIn('login_url', response.context)

    def test_confirm_login_url_resolves(self):
        complete_view = PasswordResetCompleteView.as_view(login_url='login_required')
        request_factory = RequestFactory()
        response = complete_view(request_factory.get('/xxx/'))
        self.assertEqual(response.context_data['login_url'], reverse('login_required'))

        complete_view2 = PasswordResetCompleteView.as_view(login_url='/dont-change-me/')
        response = complete_view2(request_factory.get('/xxx/'))
        self.assertEqual(response.context_data['login_url'], '/dont-change-me/')

    def test_confirm_and_login(self):
        url, path = self._test_confirm_start()
        path = path.replace('reset', 'reset_and_login')
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)

        # verify that we're actually logged in
        response = self.client.get('/login_required/')
        self.assertEqual(response.status_code, 200)


class ChangePasswordTest(ChangePasswordTest):
    urls = 'authtools.urls'

    test_password_change_redirect_custom = None
    test_password_change_redirect_custom_named = None

    # the builtin test doesn't logout after the password is changed, so
    # fail_login doesn't do anything when disallow_authenticated is True.
    def test_password_change_succeeds(self):
        self.login()
        self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.logout()
        self.fail_login()
        self.login(password='password1')


class LoginTest(LoginTest):
    urls = 'authtools.urls'

    # the built-in tests depend on the django urlpatterns (they reverse
    # django.contrib.auth.views.login)
    def test_current_site_in_context_after_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        if Site._meta.installed:
            site = Site.objects.get_current()
            self.assertEqual(response.context['site'], site)
            self.assertEqual(response.context['site_name'], site.name)
        else:
            self.assertIsInstance(response.context['site'], RequestSite)
        self.assertTrue(isinstance(response.context['form'], AuthenticationForm),
                        'Login form is not an AuthenticationForm')

    def test_security_check(self, password='password'):
        login_url = reverse('login')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '//example.com'):

            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': login_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urlquote(bad_url),
            }
            response = self.client.post(nasty_url, {
                'username': 'testclient',
                'password': password,
            })
            self.assertEqual(response.status_code, 302)
            self.assertFalse(bad_url in response['Location'],
                             "%s should be blocked" % bad_url)

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https:///',
                         '//testserver/',
                         '/url%20with%20spaces/'):  # see ticket #12534
            safe_url = '%(url)s?%(next)s=%(good_url)s' % {
                'url': login_url,
                'next': REDIRECT_FIELD_NAME,
                'good_url': urlquote(good_url),
            }
            response = self.client.post(safe_url, {
                'username': 'testclient',
                'password': password,
            })
            self.assertEqual(response.status_code, 302)
            self.assertTrue(good_url in response['Location'],
                            "%s should be allowed" % good_url)


class LoginURLSettings(LoginURLSettings):
    urls = 'tests.urls'


class LogoutTest(LogoutTest):
    urls = 'tests.urls'

    test_logout_with_overridden_redirect_url = None
    test_logout_with_next_page_specified = None
    test_logout_with_custom_redirect_argument = None
    test_logout_with_named_redirect = None
    test_logout_with_custom_redirect_argument = None

    # the built-in tests depend on the django urlpatterns (they reverse
    # django.contrib.auth.views.login)
    def test_security_check(self, password='password'):
        logout_url = reverse('logout_then_login')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '//example.com'):
            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urlquote(bad_url),
            }
            self.login()
            response = self.client.get(nasty_url)
            self.assertEqual(response.status_code, 302)
            self.assertFalse(bad_url in response['Location'],
                             "%s should be blocked" % bad_url)
            self.confirm_logged_out()

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https:///',
                         '//testserver/',
                         '/url%20with%20spaces/'):  # see ticket #12534
            safe_url = '%(url)s?%(next)s=%(good_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'good_url': urlquote(good_url),
            }
            self.login()
            response = self.client.get(safe_url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(good_url in response['Location'],
                            "%s should be allowed" % good_url)
            self.confirm_logged_out()


class UserCreationFormTest(TestCase):
    def setUp(self):
        # in built-in UserManager, the order of arguments is:
        #     username, email, password
        # in authtools UserManager, the order of arguments is:
        #     USERNAME_FIELD, password
        User.objects.create_user('testclient@example.com', password='test123')
        self.username = User.USERNAME_FIELD

    def test_user_already_exists(self):
        # The benefit of the custom validation message is only available if the
        # messages are translated.  We won't be able to translate all the
        # strings if we don't know what the username will be ahead of time.
        data = {
            self.username: 'testclient@example.com',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form[self.username].errors, [
            force_text(form.error_messages['duplicate_username']) % {'username': self.username}])

    def test_password_verification(self):
        # The verification password is incorrect.
        data = {
            self.username: 'jsmith',
            'password1': 'test123',
            'password2': 'test',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password2"].errors,
                         [force_text(form.error_messages['password_mismatch'])])

    def test_both_passwords(self):
        # One (or both) passwords weren't given
        data = {self.username: 'jsmith'}
        form = UserCreationForm(data)
        required_error = [force_text(Field.default_error_messages['required'])]
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, required_error)

        data['password2'] = 'test123'
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, [])

    def test_success(self):
        # The success case.
        data = {
            self.username: 'jsmith@example.com',
            'password1': 'test123',
            'password2': 'test123',
        }

        if settings.AUTH_USER_MODEL == 'authtools.User':
            data['name'] = 'John Smith'

        form = UserCreationForm(data)
        self.assertTrue(form.is_valid())
        u = form.save()
        self.assertEqual(getattr(u, self.username), 'jsmith@example.com')
        self.assertTrue(u.check_password('test123'))
        self.assertEqual(u, User._default_manager.get_by_natural_key('jsmith@example.com'))

    def test_generated_fields_list(self):
        if settings.AUTH_USER_MODEL == 'auth.User':
            fields = ('username', 'email', 'password1', 'password2')
        elif settings.AUTH_USER_MODEL == 'authtools.User':
            fields = ('email', 'name', 'password1', 'password2')
        elif settings.AUTH_USER_MODEL == 'tests.User':
            fields = ('email', 'full_name', 'preferred_name', 'password1', 'password2')
        else:
            assert False, "I don't know your user model"

        form = UserCreationForm()
        self.assertSequenceEqual(list(form.fields.keys()), fields)


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class UserChangeFormTest(TestCase):
    fixtures = ['authtestdata.json']

    def test_bug_14242(self):
        # A regression test, introduce by adding an optimization for the
        # UserChangeForm.

        class MyUserForm(UserChangeForm):
            def __init__(self, *args, **kwargs):
                super(MyUserForm, self).__init__(*args, **kwargs)
                self.fields['groups'].help_text = 'These groups give users different permissions'

            class Meta(UserChangeForm.Meta):
                fields = ('groups',)

        # Just check we can create it
        MyUserForm({})

    def test_unsuable_password(self):
        user = User.objects.get(username='empty_password')
        user.set_unusable_password()
        user.save()
        form = UserChangeForm(instance=user)
        self.assertIn(_("No password set."), form.as_table())

    def test_bug_17944_empty_password(self):
        user = User.objects.get(username='empty_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("No password set."), form.as_table())

    def test_bug_17944_unmanageable_password(self):
        user = User.objects.get(username='unmanageable_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("Invalid password format or unknown hashing algorithm."),
                      form.as_table())

    def test_bug_17944_unknown_password_algorithm(self):
        user = User.objects.get(username='unknown_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("Invalid password format or unknown hashing algorithm."),
                      form.as_table())

    def test_bug_19133(self):
        "The change form does not return the password value"
        # Use the form to construct the POST data
        user = User.objects.get(username='testclient')
        form_for_data = UserChangeForm(instance=user)
        post_data = form_for_data.initial

        # The password field should be readonly, so anything
        # posted here should be ignored; the form will be
        # valid, and give back the 'initial' value for the
        # password field.
        post_data['password'] = 'new password'
        form = UserChangeForm(instance=user, data=post_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['password'], 'sha1$6efc0$f93efe9fd7542f25a7be94871ea45aa95de57161')

    def test_bug_19349_bound_password_field(self):
        user = User.objects.get(username='testclient')
        form = UserChangeForm(data={}, instance=user)
        # When rendering the bound password field,
        # ReadOnlyPasswordHashWidget needs the initial
        # value to render correctly
        self.assertEqual(form.initial['password'], form['password'].value())

    def test_better_readonly_password_widget(self):
        user = User.objects.get(username='testclient')
        form = UserChangeForm(instance=user)

        self.assertIn(_('*************'), form.as_table())


class UserAdminTest(TestCase):
    def test_generated_fieldsets(self):
        if settings.AUTH_USER_MODEL == 'auth.User':
            fields = ('username', 'email', 'password')
        elif settings.AUTH_USER_MODEL == 'authtools.User':
            fields = ('email', 'name', 'password')
        elif settings.AUTH_USER_MODEL == 'tests.User':
            fields = ('email', 'full_name', 'preferred_name', 'password')
        else:
            assert False, "I don't know your user model"

        self.assertSequenceEqual(BASE_FIELDS[1]['fields'], fields)


class UserManagerTest(TestCase):
    def test_create_user(self):
        u = User._default_manager.create_user(**{
            User.USERNAME_FIELD: 'newuser@example.com',
            'password': 'test123',
        })

        self.assertEqual(getattr(u, User.USERNAME_FIELD), 'newuser@example.com')
        self.assertTrue(u.check_password('test123'))
        self.assertEqual(u, User._default_manager.get_by_natural_key('newuser@example.com'))
        self.assertTrue(u.is_active)
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)

    @skipIfNotCustomUser
    def test_create_superuser(self):
        u = User._default_manager.create_superuser(**{
            User.USERNAME_FIELD: 'newuser@example.com',
            'password': 'test123',
        })

        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)


class UserModelTest(TestCase):
    @unittest.skipUnless(settings.AUTH_USER_MODEL == 'authtools.User',
                         "only check authuser's ordering")
    def test_default_ordering(self):
        self.assertSequenceEqual(['name', 'email'], User._meta.ordering)

    def test_send_mail(self):
        abstract_user = User(email='foo@bar.com')
        abstract_user.email_user(subject="Subject here",
            message="This is a message", from_email="from@domain.com")
        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        # Verify that test email contains the correct attributes:
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Subject here")
        self.assertEqual(message.body, "This is a message")
        self.assertEqual(message.from_email, "from@domain.com")
        self.assertEqual(message.to, [abstract_user.email])

########NEW FILE########
__FILENAME__ = urls
import django
from django.conf.urls import patterns, include, url
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import admin

admin.autodiscover()


def dumbview(request):
    return HttpResponse('dumbview')


if django.VERSION < (1, 6):
    urlpatterns = patterns('authtools.views',
        url('^reset_and_login/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'password_reset_confirm_and_login'),
    )
else:
    urlpatterns = patterns('authtools.views',
        url(r'^reset_and_login/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'password_reset_confirm_and_login'),
    )

urlpatterns += patterns('',
    url('^logout-then-login/$', 'authtools.views.logout_then_login', name='logout_then_login'),
    url('^login_required/$', login_required(dumbview), name='login_required'),
    url('^', include('authtools.urls')),
)

########NEW FILE########
