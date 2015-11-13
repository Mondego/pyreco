__FILENAME__ = admin
from django.conf import settings
from django.contrib.admin.sites import site
from django.contrib.auth.forms import UserCreationForm, AdminPasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.translation import ugettext, ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from primate.auth.forms import UserChangeForm


csrf_protect_m = method_decorator(csrf_protect)


def autodiscover():
    """
    Auto-discover INSTALLED_APPS admin.py modules and fail silently when
    not present. This forces an import on them to register any admin bits they
    may want.
    """

    import copy
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule

    for app in settings.INSTALLED_APPS:
        if app == 'django.contrib.auth':
            admin.site.register(Group, GroupAdmin)
            continue
        mod = import_module(app)
        # Attempt to import the app's admin module.
        try:
            before_import_registry = copy.copy(site._registry)
            import_module('%s.admin' % app)
        except:
            # Reset the model registry to the state before the last import as
            # this import will have to reoccur on the next request and this
            # could raise NotRegistered and AlreadyRegistered exceptions
            # (see #8245).
            site._registry = before_import_registry

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'admin'):
                raise


class GroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)


class UserAdminBase(admin.ModelAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
        (_('Groups'), {'fields': ('groups',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2')}
        ),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'email', 'name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'name', 'email')
    ordering = ('username',)
    filter_horizontal = ('user_permissions',)

    def __call__(self, request, url):
        # this should not be here, but must be due to the way __call__ routes
        # in ModelAdmin.
        if url is None:
            return self.changelist_view(request)
        if url.endswith('password'):
            return self.user_change_password(request, url.split('/')[0])
        return super(UserAdminBase, self).__call__(request, url)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdminBase, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdminBase, self).get_form(request, obj, **defaults)

    def get_urls(self):
        from django.conf.urls.defaults import patterns
        return patterns('',
            (r'^(\d+)/password/$', self.admin_site.admin_view(self.user_change_password))
        ) + super(UserAdminBase, self).get_urls()

    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404('Your user does not have the "Change user" permission. In order to add users, Django requires that your user account have both the "Add user" and "Change user" permissions set.')
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': self.model._meta.get_field('username').help_text,
        }
        extra_context.update(defaults)
        return super(UserAdminBase, self).add_view(request, form_url, extra_context)

    def user_change_password(self, request, id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = get_object_or_404(self.model, pk=id)
        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                new_user = form.save()
                msg = ugettext('Password changed successfully.')
                messages.success(request, msg)
                return HttpResponseRedirect('..')
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': form.base_fields.keys()})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        return render_to_response(self.change_user_password_template or 'admin/auth/user/change_password.html', {
            'title': _('Change password: %s') % escape(user.username),
            'adminForm': adminForm,
            'form': form,
            'is_popup': '_popup' in request.REQUEST,
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
            'root_path': self.admin_site.root_path,
        }, context_instance=RequestContext(request))

    def response_add(self, request, obj, post_url_continue='../%s/'):
        """
        Determines the HttpResponse for the add_view stage. It mostly defers to
        its superclass implementation but is customized because the User model
        has a slightly different workflow.
        """
        # We should allow further modification of the user just added i.e. the
        # 'Save' button should behave like the 'Save and continue editing'
        # button except in two scenarios:
        # * The user has pressed the 'Save and add another' button
        # * We are adding a user in a popup
        if '_addanother' not in request.POST and '_popup' not in request.POST:
            request.POST['_continue'] = 1
        return super(UserAdminBase, self).response_add(request, obj, post_url_continue)


########NEW FILE########
__FILENAME__ = base
import datetime
from django.contrib import auth
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields import Field
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _
from primate.auth.helpers import *


UNUSABLE_PASSWORD = '!' # This will never be a valid hash


class UserBaseMeta(ModelBase):
    """
    Meta class for abstract class ``UserBase``. This class hides the model
    fields on allocation so that you can pick them up or not in a meta class
    that inherits this.
    """
    base_fields = {}

    def __new__(cls, name, bases, attrs):
        for k, v in attrs.items():
            if isinstance(v, Field):
                cls.base_fields[k] = attrs.pop(k)
        return ModelBase.__new__(cls, name, bases, attrs)


class UserMeta(UserBaseMeta):
    """
    This is what implementing User class need to use
    """
    def __new__(cls, name, bases, attrs):
        # inject UserBase fields
        for k, v in cls.base_fields.items():
            if k not in attrs:
                attrs[k] = cls.base_fields[k]
        return ModelBase.__new__(cls, 'User', bases, attrs)


class UserManager(models.Manager):
    def create_user(self, username, email, password=None):
        """
        Creates and saves a User with the given username, e-mail and password.
        """
        now = datetime.datetime.now()

        # Normalize the address by lowercasing the domain part of the email
        # address.
        try:
            email_name, domain_part = email.strip().split('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])

        user = self.model(username=username, email=email, is_staff=False,
                         is_active=True, is_superuser=False, last_login=now,
                         date_joined=now)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        u = self.create_user(username, email, password)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u

    def make_random_password(self, length=10, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        "Generates a random password with the given length and given allowed_chars"
        # Note that default value of allowed_chars does not have "I" or letters
        # that look like it -- just to avoid confusion.
        from random import choice
        return ''.join([choice(allowed_chars) for i in range(length)])


class UserBase(models.Model):
    """
    Users within the Django authentication system are represented by this model.

    Username and password are required. Other fields are optional.
    """
    __metaclass__ = UserBaseMeta
    username = models.CharField(_('username'), max_length=50, unique=True, help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))
    name = models.CharField(_('name'), max_length=100, blank=True)
    email = models.EmailField(_('e-mail address'), blank=True, null=True, unique=True)
    password = models.CharField(_('password'), max_length=128)
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_("Designates whether the user can log into this admin site."))
    is_active = models.BooleanField(_('active'), default=True, help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."))
    is_superuser = models.BooleanField(_('superuser status'), default=False, help_text=_("Designates that this user has all permissions without explicitly assigning them."))
    last_login = models.DateTimeField(_('last login'), default=datetime.datetime.now, editable=False)
    date_joined = models.DateTimeField(_('date joined'), default=datetime.datetime.now, editable=False)
    groups = models.ManyToManyField('auth.Group', verbose_name=_('groups'), blank=True,
        help_text=_("In addition to the permissions manually assigned, this user will also get all permissions granted to each group he/she is in."))
    user_permissions = models.ManyToManyField('auth.Permission', verbose_name=_('user permissions'), blank=True)

    objects = UserManager()

    class Meta:
        abstract = True
        app_label = 'auth'
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __unicode__(self):
        return self.username

    def is_anonymous(self):
        """
        Always returns False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    def get_full_name(self):
        return self.name

    def set_password(self, raw_password):
        if raw_password is None:
            self.set_unusable_password()
        else:
            import random
            algo = 'sha1'
            salt = get_hexdigest(algo, str(random.random()), str(random.random()))[:5]
            hsh = get_hexdigest(algo, salt, raw_password)
            self.password = '%s$%s$%s' % (algo, salt, hsh)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        encryption formats behind the scenes.
        """
        # Backwards-compatibility check. Older passwords won't include the
        # algorithm or salt.
        if '$' not in self.password:
            is_correct = (self.password == get_hexdigest('md5', '', raw_password))
            if is_correct:
                # Convert the password to the new, more secure format.
                self.set_password(raw_password)
                self.save()
            return is_correct
        return check_password(raw_password, self.password)

    def set_unusable_password(self):
        # Sets a value that will never be a valid hash
        self.password = UNUSABLE_PASSWORD

    def has_usable_password(self):
        if self.password is None \
            or self.password == UNUSABLE_PASSWORD:
            return False
        else:
            return True

    def get_group_permissions(self, obj=None):
        """
        Returns a list of permission strings that this user has through
        his/her groups. This method queries all available auth backends.
        If an object is passed in, only permissions matching this object
        are returned.
        """
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                if obj is not None:
                    if backend.supports_object_permissions:
                        permissions.update(
                            backend.get_group_permissions(self, obj)
                        )
                else:
                    permissions.update(backend.get_group_permissions(self))
        return permissions

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object
        is provided, permissions for this specific object are checked.
        """

        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Returns True if the user has each of the specified permissions.
        If object is passed, it checks if the user has all required perms
        for this object.
        """
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, app_label):
        """
        Returns True if the user has any permissions in the given app
        label. Uses pretty much the same logic as has_perm, above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)

    def get_and_delete_messages(self):
        messages = []
        for m in self.message_set.all():
            messages.append(m.message)
            m.delete()
        return messages

    def email_user(self, subject, message, from_email=None):
        "Sends an e-mail to this User."
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, [self.email])

    def get_profile(self):
        return self

    def _get_message_set(self):
        import warnings
        warnings.warn('The user messaging API is deprecated. Please update'
                      ' your code to use the new messages framework.',
                      category=DeprecationWarning)
        return self._message_set
    message_set = property(_get_message_set)



########NEW FILE########
__FILENAME__ = forms
from django.contrib import auth
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


class PassWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        return mark_safe(u'<input type="button" value="%s" onclick="window.location.href=\'password/\'">' % _('Change Password'))


class UserChangeForm(auth.forms.UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        self.fields['password'].widget = PassWidget()


########NEW FILE########
__FILENAME__ = helpers
import datetime
from django.contrib.auth.signals import user_logged_in
from django.contrib import auth
from django.utils.crypto import constant_time_compare
from django.utils.encoding import smart_str
from django.utils.hashcompat import md5_constructor, sha_constructor


__all__ = ('SiteUserNotAvailable', 'get_hexdigest', 'check_password',
           'update_last_login', '_user_get_all_permissions', '_user_has_perm',
           '_user_has_module_perms')


class SiteUserNotAvailable(Exception):
    pass


def get_hexdigest(algorithm, salt, raw_password):
    """
    Returns a string of the hexdigest of the given plaintext password and salt
    using the given algorithm ('md5', 'sha1' or 'crypt').
    """
    raw_password, salt = smart_str(raw_password), smart_str(salt)
    if algorithm == 'crypt':
        try:
            import crypt
        except ImportError:
            raise ValueError('"crypt" password algorithm not supported in this '
                             'environment')
        return crypt.crypt(raw_password, salt)

    if algorithm == 'md5':
        return md5_constructor(salt + raw_password).hexdigest()
    elif algorithm == 'sha1':
        return sha_constructor(salt + raw_password).hexdigest()
    raise ValueError("Got unknown password algorithm type in password.")


def check_password(raw_password, enc_password):
    """
    Returns a boolean of whether the raw_password was correct. Handles
    encryption formats behind the scenes.
    """
    algo, salt, hsh = enc_password.split('$')
    return constant_time_compare(hsh, get_hexdigest(algo, salt, raw_password))


def update_last_login(sender, user, **kwargs):
    """
    A signal receiver which updates the last_login date for
    the user logging in.
    """
    user.last_login = datetime.datetime.now()
    user.save()
user_logged_in.connect(update_last_login)


# A few helper functions for common logic between User and AnonymousUser.
def _user_get_all_permissions(user, obj):
    permissions = set()
    anon = user.is_anonymous()
    for backend in auth.get_backends():
        if not anon or backend.supports_anonymous_user:
            if hasattr(backend, "get_all_permissions"):
                if obj is not None:
                    if backend.supports_object_permissions:
                        permissions.update(
                            backend.get_all_permissions(user, obj)
                        )
                else:
                    permissions.update(backend.get_all_permissions(user))
    return permissions


def _user_has_perm(user, perm, obj):
    anon = user.is_anonymous()
    active = user.is_active
    for backend in auth.get_backends():
        if (not active and not anon and backend.supports_inactive_user) or \
                    (not anon or backend.supports_anonymous_user):
            if hasattr(backend, "has_perm"):
                if obj is not None:
                    if (backend.supports_object_permissions and
                        backend.has_perm(user, perm, obj)):
                        return True
                else:
                    if backend.has_perm(user, perm):
                        return True
    return False


def _user_has_module_perms(user, app_label):
    anon = user.is_anonymous()
    active = user.is_active
    for backend in auth.get_backends():
        if (not active and not anon and backend.supports_inactive_user) or \
                    (not anon or backend.supports_anonymous_user):
            if hasattr(backend, "has_module_perms"):
                if backend.has_module_perms(user, app_label):
                    return True
    return False


########NEW FILE########
__FILENAME__ = mixins
from django.utils.crypto import constant_time_compare as ctcmp
from django.utils.encoding import smart_str


class BcryptMixin(object):
    rounds = 12

    def check_password(self, raw_password):
        import bcrypt
        if self.password.startswith('bcrypt$'):
            hash_ = self.password[6:] # remove bcrypt prefix
            salt = hash_[:29]
            return ctcmp(hash_, bcrypt.hashpw(raw_password, salt))
        if super(BcryptMixin, self).check_password(raw_password):
            # Convert the password to the new, more secure format.
            self.set_password(raw_password)
            self.save()
            return True
        return False

    def set_password(self, raw_password):
        import bcrypt
        if raw_password is None:
            self.set_unusable_password()
        else:
            raw_password = smart_str(raw_password)
            salt = bcrypt.gensalt(self.rounds)
            self.password = 'bcrypt%s' % bcrypt.hashpw(raw_password, salt)


########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.manager import EmptyManager
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _
from primate.auth.helpers import *


def register_user_model():
    from django.conf import settings
    if not getattr(settings, 'AUTH_USER_MODEL', False):
        raise SiteUserNotAvailable(
            'You need to set AUTH_USER_MODEL in your project settings'
        )
    try:
        mod_name, cls_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
        mod = import_module(mod_name)
    except ImportError, e:
        raise SiteUserNotAvailable(e)
    try:
        getattr(mod, cls_name)
    except AttributeError, e:
        raise SiteUserNotAvailable(e)
register_user_model()


class PermissionManager(models.Manager):
    def get_by_natural_key(self, codename, app_label, model):
        return self.get(
            codename=codename,
            content_type=ContentType.objects.get_by_natural_key(app_label, model)
        )


class Permission(models.Model):
    """
    The permissions system provides a way to assign permissions to specific
    users and groups of users.

    The permission system is used by the Django admin site, but may also be
    useful in your own code. The Django admin site uses permissions as follows:

        - The "add" permission limits the user's ability to view the "add" form
          and add an object.
        - The "change" permission limits a user's ability to view the change
          list, view the "change" form and change an object.
        - The "delete" permission limits the ability to delete an object.

    Permissions are set globally per type of object, not per specific object
    instance. It is possible to say "Mary may change news stories," but it's
    not currently possible to say "Mary may change news stories, but only the
    ones she created herself" or "Mary may only change news stories that have a
    certain status or publication date."

    Three basic permissions -- add, change and delete -- are automatically
    created for each Django model.
    """

    name = models.CharField(_('name'), max_length=50)
    content_type = models.ForeignKey(ContentType)
    codename = models.CharField(_('codename'), max_length=100)
    objects = PermissionManager()

    class Meta:
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        unique_together = (('content_type', 'codename'),)
        ordering = ('content_type__app_label', 'content_type__model', 'codename')

    def __unicode__(self):
        return u"%s | %s | %s" % (
            unicode(self.content_type.app_label),
            unicode(self.content_type),
            unicode(self.name))

    def natural_key(self):
        return (self.codename,) + self.content_type.natural_key()
    natural_key.dependencies = ['contenttypes.contenttype']


class Group(models.Model):
    """
    Groups are a generic way of categorizing users to apply permissions, or
    some other label, to those users. A user can belong to any number of
    groups.

    A user in a group automatically has all the permissions granted to that
    group. For example, if the group Site editors has the permission
    can_edit_home_page, any user in that group will have that permission.

    Beyond permissions, groups are a convenient way to categorize users to
    apply some label, or extended functionality, to them. For example, you
    could create a group 'Special users', and you could write code that would
    do special things to those users -- such as giving them access to a
    members-only portion of your site, or sending them members-only e-mail
    messages.
    """

    name = models.CharField(_('name'), max_length=80, unique=True)
    permissions = models.ManyToManyField(Permission, verbose_name=_('permissions'), blank=True)

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __unicode__(self):
        return self.name


class Message(models.Model):
    """
    The message system is a lightweight way to queue messages for given
    users. A message is associated with a User instance (so it is only
    applicable for registered users). There's no concept of expiration or
    timestamps. Messages are created by the Django admin after successful
    actions. For example, "The poll Foo was created successfully." is a
    message.
    """

    user = models.ForeignKey('auth.User', related_name='_message_set')
    message = models.TextField(_('message'))

    def __unicode__(self):
        return self.message


class AnonymousUser(object):
    id = None
    username = ''
    is_staff = False
    is_active = False
    is_superuser = False
    _groups = EmptyManager()
    _user_permissions = EmptyManager()

    def __init__(self):
        pass

    def __unicode__(self):
        return 'AnonymousUser'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return 1 # instances always return the same hash value

    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def _get_groups(self):
        return self._groups
    groups = property(_get_groups)

    def _get_user_permissions(self):
        return self._user_permissions
    user_permissions = property(_get_user_permissions)

    def get_group_permissions(self, obj=None):
        return set()

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj=obj)

    def has_perm(self, perm, obj=None):
        return _user_has_perm(self, perm, obj=obj)

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, module):
        return _user_has_module_perms(self, module)

    def get_and_delete_messages(self):
        return []

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False

########NEW FILE########
__FILENAME__ = models
from primate.auth.base import UserBase, UserMeta
from primate.auth.mixins import BcryptMixin


########NEW FILE########
