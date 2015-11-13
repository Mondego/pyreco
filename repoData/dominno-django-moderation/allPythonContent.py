__FILENAME__ = development

from example_project.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django import VERSION

from example_project.example_app.models import ExampleUserProfile

from moderation.admin import ModerationAdmin


class ExampleUserProfileAdmin(ModerationAdmin):
    pass


class UserProfileWithCustomUserAdmin(ModerationAdmin):
    pass


admin.site.register(ExampleUserProfile, ExampleUserProfileAdmin)

if VERSION[:2] >= (1, 5):
    from example_project.example_app.models import UserProfileWithCustomUser,\
        CustomUser

    admin.site.register(UserProfileWithCustomUser,
                        UserProfileWithCustomUserAdmin)

    from django import forms
    from django.contrib import admin
    from django.contrib.auth.admin import UserAdmin
    from django.contrib.auth.forms import ReadOnlyPasswordHashField

    class CustomUserCreationForm(forms.ModelForm):
        """A form for creating new users. Includes all the required
        fields, plus a repeated password."""
        password1 = forms.CharField(label='Password',
                                    widget=forms.PasswordInput)
        password2 = forms.CharField(label='Password confirmation',
                                    widget=forms.PasswordInput)

        class Meta:
            model = CustomUser
            fields = ('username', 'email', 'date_of_birth', )

        def clean_password2(self):
            # Check that the two password entries match
            password1 = self.cleaned_data.get("password1")
            password2 = self.cleaned_data.get("password2")
            if password1 and password2 and password1 != password2:
                raise forms.ValidationError("Passwords don't match")
            return password2

        def save(self, commit=True):
            # Save the provided password in hashed format
            user = super(CustomUserCreationForm, self).save(commit=False)
            user.set_password(self.cleaned_data["password1"])
            if commit:
                user.save()
            return user

    class UserChangeForm(forms.ModelForm):
        """A form for updating users. Includes all the fields on
        the user, but replaces the password field with admin's
        password hash display field.
        """
        password = ReadOnlyPasswordHashField()

        class Meta:
            model = CustomUser

        def clean_password(self):
            # Regardless of what the user provides, return the initial value.
            # This is done here, rather than on the field, because the
            # field does not have access to the initial value
            return self.initial["password"]

    class MyUserAdmin(UserAdmin):
        # The forms to add and change user instances
        form = UserChangeForm
        add_form = CustomUserCreationForm

        # The fields to be used in displaying the User model.
        # These override the definitions on the base UserAdmin
        # that reference specific fields on auth.User.
        list_display = ('username', 'email', 'date_of_birth', 'is_staff')
        list_filter = ('is_staff',)
        fieldsets = (
            (None, {'fields': ('username', 'email', 'password')}),
            ('Personal info', {'fields': ('date_of_birth',)}),
            ('Permissions', {'fields': ('is_staff',)}),
            ('Important dates', {'fields': ('last_login',)}),
        )
        # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
        # overrides get_fieldsets to use this attribute when creating a user.
        add_fieldsets = (
                (None,
                     {
                     'classes': ('wide',),
                     'fields': (
                         'username',
                         'email',
                         'date_of_birth',
                         'password1',
                         'password2'
                )
                }
                ),
        )
        search_fields = ('email',)
        ordering = ('email',)
        filter_horizontal = ()

    # Now register the new UserAdmin...
    admin.site.register(CustomUser, MyUserAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django import VERSION
from django.contrib import admin


class ExampleUserProfile(models.Model):
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))
    description = models.TextField()
    url = models.URLField()
    
    def __unicode__(self):
        return "%s - %s" % (self.user, self.url)
    
    def get_absolute_url(self):
        return '/test/'

if VERSION[:2] >= (1, 5):

    from django.contrib.auth.models import AbstractUser

    class CustomUser(AbstractUser):
        date_of_birth = models.DateField(blank=True, null=True)
        height = models.FloatField(blank=True, null=True)

    class UserProfileWithCustomUser(models.Model):
        user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))
        description = models.TextField()
        url = models.URLField()

        def __unicode__(self):
            return "%s - %s" % (self.user, self.url)

        def get_absolute_url(self):
            return '/test/'

########NEW FILE########
__FILENAME__ = moderator
from django import VERSION

from moderation import moderation
from example_project.example_app.models import ExampleUserProfile


from moderation.moderator import GenericModerator


class UserProfileModerator(GenericModerator):
    notify_user = False
    auto_approve_for_superusers = False
    auto_approve_for_staff = False


moderation.register(ExampleUserProfile)

if VERSION[:2] >= (1, 5):
    from example_project.example_app.models import UserProfileWithCustomUser
    moderation.register(UserProfileWithCustomUser, UserProfileModerator)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.development")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = production

from example_project.settings import *

########NEW FILE########
__FILENAME__ = settings

import os

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example_project.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')

STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Don't share this with anybody.
SECRET_KEY = '4_e*48#6f4&538tnh)+mrix=4!+r4t*eilwwnw(eh%p33_ml@c'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'example_project.urls'
SITE_ID = 1

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'moderation',
    'example_project.example_app',
    #'test_extensions',
)


TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages'
)

AUTH_USER_MODEL = 'example_app.CustomUser'

########NEW FILE########
__FILENAME__ = urls

from django.conf.urls.defaults import patterns, include, handler500, url
from django.conf import settings
from django.contrib import admin
from moderation.helpers import auto_discover
admin.autodiscover()
auto_discover()

handler500 # Pyflakes

urlpatterns = patterns(
    '',
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )

    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.STATIC_ROOT}),
    )
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.forms.models import ModelForm
from django.contrib.contenttypes.models import ContentType
from django.core import urlresolvers
import django

from moderation.models import ModeratedObject, MODERATION_DRAFT_STATE,\
    MODERATION_STATUS_PENDING, MODERATION_STATUS_REJECTED,\
    MODERATION_STATUS_APPROVED

from django.utils.translation import ugettext as _
from moderation.forms import BaseModeratedObjectForm
from moderation.helpers import automoderate
from moderation.diff import get_changes_between_models


def approve_objects(modeladmin, request, queryset):
    for obj in queryset:
        obj.approve(moderated_by=request.user)

approve_objects.short_description = "Approve selected moderated objects"


def reject_objects(modeladmin, request, queryset):
    for obj in queryset:
        obj.reject(moderated_by=request.user)

reject_objects.short_description = "Reject selected moderated objects"


def set_objects_as_pending(modeladmin, request, queryset):
    queryset.update(moderation_status=MODERATION_STATUS_PENDING)

set_objects_as_pending.short_description = "Set selected moderated objects "\
                                           "as Pending"


class ModerationAdmin(admin.ModelAdmin):
    admin_integration_enabled = True

    def get_form(self, request, obj=None):
        if obj and self.admin_integration_enabled:
            self.form = self.get_moderated_object_form(obj.__class__)

        return super(ModerationAdmin, self).get_form(request, obj)

    def change_view(self, request, object_id, extra_context=None):
        if self.admin_integration_enabled:
            self.send_message(request, object_id)

        return super(ModerationAdmin, self).change_view(request, object_id)

    def send_message(self, request, object_id):
        try:
            obj = self.model.unmoderated_objects.get(pk=object_id)
            moderated_obj = ModeratedObject.objects.get_for_instance(obj)
            moderator = moderated_obj.moderator
            msg = self.get_moderation_message(moderated_obj.moderation_status,
                                              moderated_obj.moderation_reason,
                                              moderator.visible_until_rejected)
        except ModeratedObject.DoesNotExist:
            msg = self.get_moderation_message()

        self.message_user(request, msg)

    def save_model(self, request, obj, form, change):
        obj.save()
        automoderate(obj, request.user)

    def get_moderation_message(self, moderation_status=None, reason=None,
                               visible_until_rejected=False):
        if moderation_status == MODERATION_STATUS_PENDING:
            if visible_until_rejected:
                return _(u"Object is viewable on site, "
                         "it will be removed if moderator rejects it")
            else:
                return _(u"Object is not viewable on site, "
                         "it will be visible if moderator accepts it")
        elif moderation_status == MODERATION_STATUS_REJECTED:
            return _(u"Object has been rejected by moderator, "
                     "reason: %s" % reason)
        elif moderation_status == MODERATION_STATUS_APPROVED:
            return _(u"Object has been approved by moderator "
                     "and is visible on site")
        elif moderation_status is None:
            return _("This object is not registered with "
                     "the moderation system.")

    def get_moderated_object_form(self, model_class):

        class ModeratedObjectForm(BaseModeratedObjectForm):

            class Meta:
                model = model_class

        return ModeratedObjectForm


try:
    from moderation.filterspecs import RegisteredContentTypeListFilter
except ImportError:
    # Django < 1.4
    available_filters = ('content_type', 'moderation_status')
else:
    # Django >= 1.4
    available_filters = (
        ('content_type', RegisteredContentTypeListFilter), 'moderation_status')


class ModeratedObjectAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_created'
    list_display = ('content_object', 'content_type', 'date_created',
                    'moderation_status', 'moderated_by', 'moderation_date')
    list_filter = available_filters
    change_form_template = 'moderation/moderate_object.html'
    change_list_template = 'moderation/moderated_objects_list.html'
    actions = [reject_objects, approve_objects, set_objects_as_pending]
    fieldsets = (
        ('Object moderation', {'fields': ('moderation_reason',)}),
    )

    def get_actions(self, request):
        actions = super(ModeratedObjectAdmin, self).get_actions(request)
        # Remove the delete_selected action if it exists
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def content_object(self, obj):
        return unicode(obj.changed_object)

    def queryset(self, request):
        qs = super(ModeratedObjectAdmin, self).queryset(request)

        return qs.exclude(moderation_state=MODERATION_DRAFT_STATE)

    def get_moderated_object_form(self, model_class):

        class ModeratedObjectForm(ModelForm):

            class Meta:
                model = model_class

        return ModeratedObjectForm

    def change_view(self, request, object_id, extra_context=None):
        from moderation import moderation

        moderated_object = ModeratedObject.objects.get(pk=object_id)

        changed_obj = moderated_object.changed_object

        moderator = moderation.get_moderator(changed_obj.__class__)

        if moderator.visible_until_rejected:
            old_object = changed_obj
            new_object = moderated_object.get_object_for_this_type()
        else:
            old_object = moderated_object.get_object_for_this_type()
            new_object = changed_obj

        changes = get_changes_between_models(
            old_object,
            new_object,
            moderator.fields_exclude).values()
        if request.POST:
            admin_form = self.get_form(request, moderated_object)(request.POST)

            if admin_form.is_valid():
                reason = admin_form.cleaned_data['moderation_reason']
                if 'approve' in request.POST:
                    moderated_object.approve(request.user, reason)
                elif 'reject' in request.POST:
                    moderated_object.reject(request.user, reason)

        content_type = ContentType.objects.get_for_model(changed_obj.__class__)
        try:
            object_admin_url = urlresolvers.reverse("admin:%s_%s_change" %
                                                    (content_type.app_label,
                                                     content_type.model),
                                                    args=(changed_obj.pk,))
        except urlresolvers.NoReverseMatch:
            object_admin_url = None

        extra_context = {'changes': changes,
                         'django_version': django.get_version()[:3],
                         'object_admin_url': object_admin_url}
        return super(ModeratedObjectAdmin, self).change_view(
            request,
            object_id,
            extra_context=extra_context)


admin.site.register(ModeratedObject, ModeratedObjectAdmin)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings


MODERATORS = getattr(settings, "DJANGO_MODERATION_MODERATORS", ())

########NEW FILE########
__FILENAME__ = diff
# -*- coding: utf-8 -*-

import re
import difflib

from django.db.models import fields
from django.utils.html import escape


class BaseChange(object):

    def __repr__(self):
        value1, value2 = self.change
        return u'Change object: %s - %s' % (value1, value2)

    def __init__(self, verbose_name, field, change):
        self.verbose_name = verbose_name
        self.field = field
        self.change = change

    def render_diff(self, template, context):
        from django.template.loader import render_to_string

        return render_to_string(template, context)


class TextChange(BaseChange):

    @property
    def diff(self):
        value1, value2 = escape(self.change[0]), escape(self.change[1])
        if value1 == value2:
            return value1

        return self.render_diff(
            'moderation/html_diff.html',
            {'diff_operations': get_diff_operations(*self.change)})


class ImageChange(BaseChange):

    @property
    def diff(self):
        left_image, right_image = self.change
        return self.render_diff(
            'moderation/image_diff.html',
            {'left_image': left_image, 'right_image': right_image})


def get_change(model1, model2, field):
    try:
        value1 = getattr(model1, "get_%s_display" % field.name)()
        value2 = getattr(model2, "get_%s_display" % field.name)()
    except AttributeError:
        value1 = field.value_from_object(model1)
        value2 = field.value_from_object(model2)

    change = get_change_for_type(
        field.verbose_name,
        (value1, value2),
        field,
    )

    return change


def get_changes_between_models(model1, model2, excludes=[]):
    changes = {}

    for field in model1._meta.fields:
        if not (isinstance(field, (fields.AutoField,))):
            if field.name in excludes:
                continue

            name = u"%s__%s" % (model1.__class__.__name__.lower(), field.name)

            changes[name] = get_change(model1, model2, field)

    return changes


def get_diff_operations(a, b):
    operations = []
    a_words = re.split('(\W+)', a)
    b_words = re.split('(\W+)', b)
    sequence_matcher = difflib.SequenceMatcher(None, a_words, b_words)
    for opcode in sequence_matcher.get_opcodes():
        operation, start_a, end_a, start_b, end_b = opcode

        deleted = ''.join(a_words[start_a:end_a])
        inserted = ''.join(b_words[start_b:end_b])

        operations.append({'operation': operation,
                           'deleted': deleted,
                           'inserted': inserted})
    return operations


def html_to_list(html):
    pattern = re.compile(r'&.*?;|(?:<[^<]*?>)|'
                         '(?:\w[\w-]*[ ]*)|(?:<[^<]*?>)|'
                         '(?:\s*[,\.\?]*)', re.UNICODE)

    return [''.join(element) for element in filter(None,
                                                   pattern.findall(html))]


def get_change_for_type(verbose_name, change, field):
    if isinstance(field, fields.files.ImageField):
        change = ImageChange(
            u"Current %(verbose_name)s / "
            u"New %(verbose_name)s" % {'verbose_name': verbose_name},
            field,
            change)
    else:
        value1, value2 = change
        change = TextChange(
            verbose_name,
            field,
            (unicode(value1), unicode(value2)),
        )

    return change

########NEW FILE########
__FILENAME__ = fields
from django.db import models
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist


class SerializedObjectField(models.TextField):
    '''Model field that stores serialized value of model class instance
       and returns deserialized model instance

       >>> from django.db import models
       >>> import SerializedObjectField

       >>> class A(models.Model):
               object = SerializedObjectField(serialize_format='json')

       >>> class B(models.Model):
               field = models.CharField(max_length=10)
       >>> b = B(field='test')
       >>> b.save()
       >>> a = A()
       >>> a.object = b
       >>> a.save()
       >>> a = A.object.get(pk=1)
       >>> a.object
       <B: B object>
       >>> a.object.__dict__
       {'field': 'test', 'id': 1}

    '''

    def __init__(self, serialize_format='json', *args, **kwargs):
        self.serialize_format = serialize_format
        super(SerializedObjectField, self).__init__(*args, **kwargs)

    def _serialize(self, value):
        if not value:
            return ''

        value_set = [value]
        if value._meta.parents:
            value_set += [getattr(value, f.name)
                          for f in value._meta.parents.values()
                          if f is not None]

        return serializers.serialize(self.serialize_format, value_set)

    def _deserialize(self, value):
        obj_generator = serializers.deserialize(
            self.serialize_format,
            value.encode(settings.DEFAULT_CHARSET),
            ignorenonexistent=True)

        obj = obj_generator.next().object
        for parent in obj_generator:
            for f in parent.object._meta.fields:
                try:
                    setattr(obj, f.name, getattr(parent.object, f.name))
                except ObjectDoesNotExist:
                    try:
                        # Try to set non-existant foreign key reference to None
                        setattr(obj, f.name, None)
                    except ValueError:
                        # Return None for changed_object if None not allowed
                        return None
        return obj

    def db_type(self, connection=None):
        return 'text'

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname, None)
        return self._serialize(value)

    def contribute_to_class(self, cls, name):
        self.class_name = cls
        super(SerializedObjectField, self).contribute_to_class(cls, name)
        models.signals.post_init.connect(self.post_init)

    def post_init(self, **kwargs):
        if 'sender' in kwargs and 'instance' in kwargs:
            if kwargs['sender'] == self.class_name and\
               hasattr(kwargs['instance'], self.attname):
                value = self.value_from_object(kwargs['instance'])

                if value:
                    setattr(kwargs['instance'], self.attname,
                            self._deserialize(value))
                else:
                    setattr(kwargs['instance'], self.attname, None)


try:
    from south.modelsinspector import add_introspection_rules

    add_introspection_rules(
        [
            (
                [SerializedObjectField],  # Class(es) these apply to
                [],  # Positional arguments (not used)
                {  # Keyword argument
                    "serialize_format": [
                        "serialize_format",
                        {"default": "json"}],
                },
            ),
        ],
        ["^moderation\.fields\.SerializedObjectField"]
    )
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = filterspecs
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _

import moderation


def _registered_content_types():
    "Return sorted content types for all registered models."
    content_types = []
    registered = moderation.moderation._registered_models.keys()
    registered.sort(key=lambda obj: obj.__name__)
    for model in registered:
        content_types.append(ContentType.objects.get_for_model(model))
    return content_types


try:
    from django.contrib.admin.filters import FieldListFilter
except ImportError:
    # Django < 1.4
    from django.contrib.admin.filterspecs import FilterSpec, RelatedFilterSpec

    class ContentTypeFilterSpec(RelatedFilterSpec):

        def __init__(self, *args, **kwargs):
            super(ContentTypeFilterSpec, self).__init__(*args, **kwargs)
            self.content_types = _registered_content_types()
            self.lookup_choices = map(
                lambda ct: (ct.id, ct.name.capitalize()), self.content_types)

    get_filter = lambda f: getattr(f, 'content_type_filter', False)
    FilterSpec.filter_specs.insert(0, (get_filter, ContentTypeFilterSpec))
else:
    # Django >= 1.4

    class RegisteredContentTypeListFilter(FieldListFilter):

        def __init__(self, field, request, params,
                     model, model_admin, field_path):
            self.lookup_kwarg = '%s' % field_path
            self.lookup_val = request.GET.get(self.lookup_kwarg)
            self.content_types = _registered_content_types()
            super(RegisteredContentTypeListFilter, self).__init__(
                field, request, params, model, model_admin, field_path)

        def expected_parameters(self):
            return [self.lookup_kwarg]

        def choices(self, cl):
            yield {
                'selected': self.lookup_val is None,
                'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
                'display': _('All')}
            for ct_type in self.content_types:
                yield {
                    'selected': smart_unicode(ct_type.id) == self.lookup_val,
                    'query_string': cl.get_query_string({
                        self.lookup_kwarg: ct_type.id}),
                    'display': unicode(ct_type),
                }

########NEW FILE########
__FILENAME__ = forms
from django.forms.models import ModelForm, model_to_dict
from moderation.models import MODERATION_STATUS_PENDING,\
    MODERATION_STATUS_REJECTED
from django.core.exceptions import ObjectDoesNotExist


class BaseModeratedObjectForm(ModelForm):

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)

        if instance:
            try:
                if instance.moderated_object.moderation_status in\
                   [MODERATION_STATUS_PENDING, MODERATION_STATUS_REJECTED] and\
                   not instance.moderated_object.moderator.\
                   visible_until_rejected:
                    initial = model_to_dict(
                        instance.moderated_object.changed_object)
                    kwargs.setdefault('initial', {})
                    kwargs['initial'].update(initial)
            except ObjectDoesNotExist:
                pass

        super(BaseModeratedObjectForm, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = helpers
from moderation.register import RegistrationError


def automoderate(instance, user):
    '''
    Auto moderates given model instance on user. Returns moderation status:
    0 - Rejected
    1 - Approved
    '''
    try:
        status = instance.moderated_object.automoderate(user)
    except AttributeError:
        msg = u"%s has been registered with Moderation." % instance.__class__
        raise RegistrationError(msg)

    return status


def import_moderator(app):
    '''
    Import moderator module and register all models it contains with moderation
    '''
    from django.utils.importlib import import_module
    import imp

    try:
        app_path = import_module(app).__path__
    except AttributeError:
        return None

    try:
        imp.find_module('moderator', app_path)
    except ImportError:
        return None

    module = import_module("%s.moderator" % app)

    return module


def auto_discover():
    '''
    Auto register all apps that have module moderator with moderation
    '''
    from django.conf import settings

    for app in settings.INSTALLED_APPS:
        import_moderator(app)

########NEW FILE########
__FILENAME__ = managers
from django.db.models.manager import Manager
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist


class MetaClass(type):

    def __new__(cls, name, bases, attrs):
        return super(MetaClass, cls).__new__(cls, name, bases, attrs)


class ModerationObjectsManager(Manager):

    def __call__(self, base_manager, *args, **kwargs):
        return MetaClass(
            self.__class__.__name__,
            (self.__class__, base_manager),
            {'use_for_related_fields': True})

    def filter_moderated_objects(self, query_set):
        from moderation.models import MODERATION_STATUS_PENDING

        exclude_pks = []

        from models import ModeratedObject

        mobjs_set = ModeratedObject.objects.filter(
            content_type=ContentType.objects.get_for_model(query_set.model),
            object_pk__in=query_set.values_list('pk', flat=True))

        # TODO: Load this query in chunks to avoid huge RAM usage spikes
        mobjects = dict(
            [(mobject.object_pk, mobject) for mobject in mobjs_set])

        full_query_set = super(ModerationObjectsManager, self).get_query_set()\
            .filter(pk__in=query_set.values_list('pk', flat=True))

        for obj in full_query_set:
            try:
                # We cannot use dict.get() here!
                mobject = mobjects[obj.pk] if obj.pk in mobjects else \
                    obj.moderated_object

                if mobject.moderation_status == MODERATION_STATUS_PENDING and \
                   not mobject.moderation_date:
                    exclude_pks.append(obj.pk)
            except ObjectDoesNotExist:
                pass

        return query_set.exclude(pk__in=exclude_pks)

    def exclude_objs_by_visibility_col(self, query_set):
        from moderation.models import MODERATION_STATUS_REJECTED

        kwargs = {}
        kwargs[self.moderator.visibility_column] =\
            bool(MODERATION_STATUS_REJECTED)

        return query_set.exclude(**kwargs)

    def get_query_set(self):
        query_set = super(ModerationObjectsManager, self).get_query_set()

        if self.moderator.visibility_column:
            return self.exclude_objs_by_visibility_col(query_set)

        return self.filter_moderated_objects(query_set)

    @property
    def moderator(self):
        from moderation import moderation

        return moderation.get_moderator(self.model)


class ModeratedObjectManager(Manager):

    def get_for_instance(self, instance):
        '''Returns ModeratedObject for given model instance'''
        return self.get(
            object_pk=instance.pk,
            content_type=ContentType.objects.get_for_model(instance.__class__))

########NEW FILE########
__FILENAME__ = message_backends
from django.conf import settings
from django.core.mail import send_mail


class BaseMessageBackend(object):

    def send(self, **kwargs):
        raise NotImplementedError


class SyncMessageBackend(BaseMessageBackend):
    """Synchronous backend"""


class AsyncMessageBackend(BaseMessageBackend):
    """Asynchronous backend"""


class EmailMessageBackend(SyncMessageBackend):
    """
    Send the message through an email on the main thread
    """

    def send(self, **kwargs):
        subject = kwargs.get('subject', None)
        message = kwargs.get('message', None)
        recipient_list = kwargs.get('recipient_list', None)

        send_mail(subject=subject,
                  message=message,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=recipient_list,
                  fail_silently=True)

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

USER_MODEL = "%s.%s" % (User._meta.app_label, User._meta.object_name)


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'ModeratedObject'
        db.create_table('moderation_moderatedobject', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('object_pk', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('moderation_state', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('moderation_status', self.gf('django.db.models.fields.SmallIntegerField')(default=2)),
            ('moderated_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='moderated_by_set', null=True, to=orm[USER_MODEL])),
            ('moderation_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('moderation_reason', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('changed_object', self.gf('moderation.fields.SerializedObjectField')()),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='changed_by_set', null=True, to=orm[USER_MODEL])),
        ))
        db.send_create_signal('moderation', ['ModeratedObject'])

    def backwards(self, orm):

        # Deleting model 'ModeratedObject'
        db.delete_table('moderation_moderatedobject')

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
        # this should replace "auth.user"
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
        'Meta': {'object_name': User.__name__},
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
        'moderation.moderatedobject': {
            'Meta': {'ordering': "['moderation_status', 'date_created']", 'object_name': 'ModeratedObject'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'changed_by_set'", 'null': 'True', 'to': "orm['%s']" % USER_MODEL}),
            'changed_object': ('moderation.fields.SerializedObjectField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'moderated_by_set'", 'null': 'True', 'to': "orm['%s']" % USER_MODEL}),
            'moderation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'moderation_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'moderation_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'moderation_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '2'}),
            'object_pk': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['moderation']

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from moderation.diff import get_changes_between_models
from moderation.fields import SerializedObjectField
from moderation.signals import post_moderation, pre_moderation
from moderation.managers import ModeratedObjectManager

import datetime


MODERATION_READY_STATE = 0
MODERATION_DRAFT_STATE = 1

MODERATION_STATUS_REJECTED = 0
MODERATION_STATUS_APPROVED = 1
MODERATION_STATUS_PENDING = 2

MODERATION_STATES = (
    (MODERATION_READY_STATE, 'Ready for moderation'),
    (MODERATION_DRAFT_STATE, 'Draft'),
)

STATUS_CHOICES = (
    (MODERATION_STATUS_APPROVED, "Approved"),
    (MODERATION_STATUS_PENDING, "Pending"),
    (MODERATION_STATUS_REJECTED, "Rejected"),
)


class ModeratedObject(models.Model):
    content_type = models.ForeignKey(ContentType, null=True, blank=True,
                                     editable=False)
    object_pk = models.PositiveIntegerField(null=True, blank=True,
                                            editable=False)
    content_object = generic.GenericForeignKey(ct_field="content_type",
                                               fk_field="object_pk")
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    moderation_state = models.SmallIntegerField(choices=MODERATION_STATES,
                                                default=MODERATION_READY_STATE,
                                                editable=False)
    moderation_status = models.SmallIntegerField(
        choices=STATUS_CHOICES,
        default=MODERATION_STATUS_PENDING,
        editable=False)
    moderated_by = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), 
        blank=True, null=True, editable=False, 
        related_name='moderated_by_set')
    moderation_date = models.DateTimeField(editable=False, blank=True,
                                           null=True)
    moderation_reason = models.TextField(blank=True, null=True)
    changed_object = SerializedObjectField(serialize_format='json',
                                           editable=False)
    changed_by = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), 
        blank=True, null=True, editable=True, 
        related_name='changed_by_set')

    objects = ModeratedObjectManager()

    content_type.content_type_filter = True

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('content_object')
        super(ModeratedObject, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u"%s" % self.changed_object

    def save(self, *args, **kwargs):
        if self.instance:
            self.changed_object = self.instance

        super(ModeratedObject, self).save(*args, **kwargs)

    class Meta:
        ordering = ['moderation_status', 'date_created']

    def automoderate(self, user=None):
        '''Auto moderate object for given user.
          Returns status of moderation.
        '''
        if user is None:
            user = self.changed_by
        else:
            self.changed_by = user
            self.save()

        if self.moderator.visible_until_rejected:
            changed_object = self.get_object_for_this_type()
        else:
            changed_object = self.changed_object
        moderate_status, reason = self._get_moderation_status_and_reason(
            changed_object,
            user)

        if moderate_status == MODERATION_STATUS_REJECTED:
            self.reject(moderated_by=self.moderated_by, reason=reason)
        elif moderate_status == MODERATION_STATUS_APPROVED:
            self.approve(moderated_by=self.moderated_by, reason=reason)

        return moderate_status

    def _get_moderation_status_and_reason(self, obj, user):
        '''
        Returns tuple of moderation status and reason for auto moderation
        '''
        reason = self.moderator.is_auto_reject(obj, user)
        if reason:
            return MODERATION_STATUS_REJECTED, reason
        else:
            reason = self.moderator.is_auto_approve(obj, user)
            if reason:
                return MODERATION_STATUS_APPROVED, reason

        return MODERATION_STATUS_PENDING, None

    def get_object_for_this_type(self):
        pk = self.object_pk
        obj = self.content_type.model_class()._default_manager.get(pk=pk)
        return obj

    def get_absolute_url(self):
        if hasattr(self.changed_object, 'get_absolute_url'):
            return self.changed_object.get_absolute_url()
        return None

    def get_admin_moderate_url(self):
        return u"/admin/moderation/moderatedobject/%s/" % self.pk

    @property
    def moderator(self):
        from moderation import moderation

        model_class = self.content_object.__class__

        return moderation.get_moderator(model_class)

    def _moderate(self, status, moderated_by, reason):
        self.moderation_status = status
        self.moderation_date = datetime.datetime.now()
        self.moderated_by = moderated_by
        self.moderation_reason = reason

        if status == MODERATION_STATUS_APPROVED:
            if self.moderator.visible_until_rejected:
                try:
                    obj_class = self.changed_object.__class__
                    pk = self.changed_object.pk
                    unchanged_obj = obj_class._default_manager.get(pk=pk)
                except obj_class.DoesNotExist:
                    unchanged_obj = None
                self.changed_object = unchanged_obj

            if self.moderator.visibility_column:
                setattr(self.changed_object, self.moderator.visibility_column,
                        True)

            self.save()
            self.changed_object.save()

        else:
            self.save()
        if status == MODERATION_STATUS_REJECTED and\
           self.moderator.visible_until_rejected:
            self.changed_object.save()

        if self.changed_by:
            self.moderator.inform_user(self.content_object, self.changed_by)

    def has_object_been_changed(self, original_obj, fields_exclude=None):
        if fields_exclude is None:
            fields_exclude = self.moderator.fields_exclude
        changes = get_changes_between_models(original_obj,
                                             self.changed_object,
                                             fields_exclude)

        for change in changes:
            left_change, right_change = changes[change].change
            if left_change != right_change:
                return True

        return False

    def approve(self, moderated_by=None, reason=None):
        pre_moderation.send(sender=self.changed_object.__class__,
                            instance=self.changed_object,
                            status=MODERATION_STATUS_APPROVED)

        self._moderate(MODERATION_STATUS_APPROVED, moderated_by, reason)

        post_moderation.send(sender=self.content_object.__class__,
                             instance=self.content_object,
                             status=MODERATION_STATUS_APPROVED)

    def reject(self, moderated_by=None, reason=None):
        pre_moderation.send(sender=self.changed_object.__class__,
                            instance=self.changed_object,
                            status=MODERATION_STATUS_REJECTED)
        self._moderate(MODERATION_STATUS_REJECTED, moderated_by, reason)
        post_moderation.send(sender=self.content_object.__class__,
                             instance=self.content_object,
                             status=MODERATION_STATUS_REJECTED)

########NEW FILE########
__FILENAME__ = moderator
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import BooleanField
from django.db.models.manager import Manager
from django.template.loader import render_to_string

from moderation.managers import ModerationObjectsManager
from moderation.message_backends import BaseMessageBackend, EmailMessageBackend


class GenericModerator(object):

    """
    Encapsulates moderation options for a given model.
    """
    manager_names = ['objects']
    moderation_manager_class = ModerationObjectsManager
    bypass_moderation_after_approval = False
    visible_until_rejected = False

    fields_exclude = []

    visibility_column = None

    auto_approve_for_superusers = True
    auto_approve_for_staff = True
    auto_approve_for_groups = None

    auto_reject_for_anonymous = True
    auto_reject_for_groups = None

    notify_moderator = True
    notify_user = True

    message_backend_class = EmailMessageBackend
    subject_template_moderator = \
        'moderation/notification_subject_moderator.txt'
    message_template_moderator = \
        'moderation/notification_message_moderator.txt'
    subject_template_user = 'moderation/notification_subject_user.txt'
    message_template_user = 'moderation/notification_message_user.txt'

    def __init__(self, model_class):
        self.model_class = model_class
        self._validate_options()
        self.base_managers = self._get_base_managers()

        moderated_fields = getattr(model_class, 'moderated_fields', None)
        if moderated_fields:
            for field in model_class._meta.fields:
                if field.name not in moderated_fields:
                    self.fields_exclude.append(field.name)

    def is_auto_approve(self, obj, user):
        '''
        Checks if change on obj by user need to be auto approved
        Returns False if change is not auto approve or reason(Unicode) if
        change need to be auto approved.

        Overwrite this method if you want to provide your custom logic.
        '''
        if self.auto_approve_for_groups and \
           self._check_user_in_groups(user, self.auto_approve_for_groups):
            return self.reason(u'Auto-approved: User in allowed group')
        if self.auto_approve_for_superusers and user.is_superuser:
            return self.reason(u'Auto-approved: Superuser')
        if self.auto_approve_for_staff and user.is_staff:
            return self.reason(u'Auto-approved: Staff')

        return False

    def is_auto_reject(self, obj, user):
        '''
        Checks if change on obj by user need to be auto rejected
        Returns False if change is not auto reject or reason(Unicode) if
        change need to be auto rejected.

        Overwrite this method if you want to provide your custom logic.
        '''
        if self.auto_reject_for_groups and \
           self._check_user_in_groups(user, self.auto_reject_for_groups):
            return self.reason(u'Auto-rejected: User in disallowed group')
        if self.auto_reject_for_anonymous and user.is_anonymous():
            return self.reason(u'Auto-rejected: Anonymous User')

        return False

    def reason(self, reason, user=None, obj=None):
        '''Returns moderation reason for auto moderation.  Optional user
        and object can be passed for a more custom reason.
        '''
        return reason

    def _check_user_in_groups(self, user, groups):
        for group in groups:
            try:
                group = Group.objects.get(name=group)
            except ObjectDoesNotExist:
                return False

            if group in user.groups.all():
                return True

        return False

    def get_message_backend(self):
        if not issubclass(self.message_backend_class, BaseMessageBackend):
            raise TypeError("The message backend used '%s' needs to "
                            "inherit from the BaseMessageBakend "
                            "class" % self.message_backend_class)
        return self.message_backend_class()

    def send(self, content_object, subject_template, message_template,
             recipient_list, extra_context=None):
        context = {
            'moderated_object': content_object.moderated_object,
            'content_object': content_object,
            'site': Site.objects.get_current(),
            'content_type': content_object.moderated_object.content_type}

        if extra_context:
            context.update(extra_context)

        message = render_to_string(message_template, context)
        subject = render_to_string(subject_template, context)

        backend = self.get_message_backend()
        backend.send(
            subject=subject,
            message=message,
            recipient_list=recipient_list)

    def inform_moderator(self,
                         content_object,
                         extra_context=None):
        '''Send notification to moderator'''
        from moderation.conf.settings import MODERATORS

        if self.notify_moderator:
            self.send(
                content_object=content_object,
                subject_template=self.subject_template_moderator,
                message_template=self.message_template_moderator,
                recipient_list=MODERATORS)

    def inform_user(self, content_object,
                    user,
                    extra_context=None):
        '''Send notification to user when object is approved or rejected'''
        if extra_context:
            extra_context.update({'user': user})
        else:
            extra_context = {'user': user}
        if self.notify_user:
            self.send(
                content_object=content_object,
                subject_template=self.subject_template_user,
                message_template=self.message_template_user,
                recipient_list=[user.email],
                extra_context=extra_context)

    def _get_base_managers(self):
        base_managers = []

        for manager_name in self.manager_names:
            base_managers.append(
                (
                    manager_name,
                    self._get_base_manager(self.model_class, manager_name)))
        return base_managers

    def _get_base_manager(self, model_class, manager_name):
        """Returns base manager class for given model class """
        if hasattr(model_class, manager_name):
            base_manager = getattr(model_class, manager_name).__class__
        else:
            base_manager = Manager

        return base_manager

    def _validate_options(self):
        if self.visibility_column:
            field_type = type(self.model_class._meta.get_field_by_name(
                self.visibility_column)[0])

            if field_type != BooleanField:
                msg = "visibility_column field: %s on model %s should "\
                      "be BooleanField type but is %s"
                msg %= (
                    self.moderator.visibility_column,
                    self.changed_object.__class__,
                    field_type)
                raise AttributeError(msg)

########NEW FILE########
__FILENAME__ = register
from moderation.models import ModeratedObject, MODERATION_STATUS_PENDING,\
    MODERATION_STATUS_APPROVED
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes import generic
from moderation.moderator import GenericModerator


class RegistrationError(Exception):
    """Exception thrown when registration with Moderation goes wrong."""


class ModerationManagerSingleton(type):

    def __init__(cls, name, bases, dict):
        super(ModerationManagerSingleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(ModerationManagerSingleton, cls)\
                .__call__(*args, **kw)

        return cls.instance


class ModerationManager(object):
    __metaclass__ = ModerationManagerSingleton

    def __init__(self, *args, **kwargs):
        """Initializes the moderation manager."""
        self._registered_models = {}

        super(ModerationManager, self).__init__(*args, **kwargs)

    def register(self, model_class, moderator_class=None):
        """Registers model class with moderation"""
        if model_class in self._registered_models:
            msg = u"%s has been registered with Moderation." % model_class
            raise RegistrationError(msg)
        if not moderator_class:
            moderator_class = GenericModerator

        if not issubclass(moderator_class, GenericModerator):
            msg = 'moderator_class must subclass '\
                  'GenericModerator class, found %s' % moderator_class
            raise AttributeError(msg)

        self._registered_models[model_class] = moderator_class(model_class)

        self._and_fields_to_model_class(self._registered_models[model_class])
        self._connect_signals(model_class)

    def _connect_signals(self, model_class):
        from django.db.models import signals

        signals.pre_save.connect(self.pre_save_handler,
                                 sender=model_class)
        signals.post_save.connect(self.post_save_handler,
                                  sender=model_class)

    def _add_moderated_object_to_class(self, model_class):
        if hasattr(model_class, '_relation_object'):
            relation_object = getattr(model_class, '_relation_object')
        else:
            relation_object = generic.GenericRelation(
                ModeratedObject,
                object_id_field='object_pk')

        model_class.add_to_class('_relation_object', relation_object)

        def get_moderated_object(self):
            if not hasattr(self, '_moderated_object'):
                self._moderated_object = getattr(self,
                                                 '_relation_object').get()
            return self._moderated_object

        model_class.add_to_class('moderated_object',
                                 property(get_moderated_object))

    def _and_fields_to_model_class(self, moderator_class_instance):
        """Sets moderation manager on model class,
           adds generic relation to ModeratedObject,
           sets _default_manager on model class as instance of
           ModerationObjectsManager
        """
        model_class = moderator_class_instance.model_class
        base_managers = moderator_class_instance.base_managers
        moderation_manager_class = moderator_class_instance.\
            moderation_manager_class

        for manager_name, mgr_class in base_managers:
            ModerationObjectsManager = moderation_manager_class()(mgr_class)
            manager = ModerationObjectsManager()
            model_class.add_to_class('unmoderated_%s' % manager_name,
                                     mgr_class())
            model_class.add_to_class(manager_name, manager)

        self._add_moderated_object_to_class(model_class)

    def unregister(self, model_class):
        """Unregister model class from moderation"""
        try:
            moderator_instance = self._registered_models.pop(model_class)
        except KeyError:
            msg = "%r has not been registered with Moderation." % model_class
            raise RegistrationError(msg)

        self._remove_fields(moderator_instance)
        self._disconnect_signals(model_class)

    def _remove_fields(self, moderator_class_instance):
        """Removes fields from model class and disconnects signals"""

        model_class = moderator_class_instance.model_class
        base_managers = moderator_class_instance.base_managers

        for manager_name, manager_class in base_managers:
            manager = manager_class()
            delattr(model_class, 'unmoderated_%s' % manager_name)
            model_class.add_to_class(manager_name, manager)

        delattr(model_class, 'moderated_object')

    def _disconnect_signals(self, model_class):
        from django.db.models import signals

        signals.pre_save.disconnect(self.pre_save_handler, model_class)
        signals.post_save.disconnect(self.post_save_handler, model_class)

    def pre_save_handler(self, sender, instance, **kwargs):
        """Update moderation object when moderation object for
           existing instance of model does not exists
        """
        # check if object was loaded from fixture, bypass moderation if so
        if kwargs['raw']:
            return

        unchanged_obj = self._get_unchanged_object(instance)
        moderator = self.get_moderator(sender)
        if unchanged_obj:
            moderated_obj = self._get_or_create_moderated_object(instance,
                                                                 unchanged_obj,
                                                                 moderator)
            if moderated_obj.moderation_status != \
               MODERATION_STATUS_APPROVED and \
               not moderator.bypass_moderation_after_approval:
                moderated_obj.save()

    def _get_unchanged_object(self, instance):
        if instance.pk is None:
            return None
        pk = instance.pk
        try:
            unchanged_obj = instance.__class__._default_manager.get(pk=pk)
            return unchanged_obj
        except ObjectDoesNotExist:
            return None

    def _get_or_create_moderated_object(self, instance,
                                        unchanged_obj, moderator):
        """
        Get or create ModeratedObject instance.
        If moderated object is not equal instance then serialize unchanged
        in moderated object in order to use it later in post_save_handler
        """
        try:
            moderated_object = ModeratedObject.objects.\
                get_for_instance(instance)

        except ObjectDoesNotExist:
            moderated_object = ModeratedObject(content_object=unchanged_obj)
            moderated_object.changed_object = unchanged_obj

        else:
            if moderated_object.has_object_been_changed(instance):
                if moderator.visible_until_rejected:
                    moderated_object.changed_object = instance
                else:
                    moderated_object.changed_object = unchanged_obj

        return moderated_object

    def get_moderator(self, model_class):
        try:
            moderator_instance = self._registered_models[model_class]
        except KeyError:
            msg = "%r has not been registered with Moderation." % model_class
            raise RegistrationError(msg)

        return moderator_instance

    def post_save_handler(self, sender, instance, **kwargs):
        """
        Creates new moderation object if instance is created,
        If instance exists and is only updated then save instance as
        content_object of moderated_object
        """
        # check if object was loaded from fixture, bypass moderation if so

        if kwargs['raw']:
            return

        pk = instance.pk
        moderator = self.get_moderator(sender)

        if kwargs['created']:
            old_object = sender._default_manager.get(pk=pk)
            moderated_obj = ModeratedObject(content_object=old_object)
            moderated_obj.save()
            moderator.inform_moderator(instance)
        else:
            moderated_obj = ModeratedObject.objects.\
                get_for_instance(instance)

            if moderated_obj.moderation_status == \
               MODERATION_STATUS_APPROVED and \
               moderator.bypass_moderation_after_approval:
                return

            if moderated_obj.has_object_been_changed(instance):
                copied_instance = self._copy_model_instance(instance)

                if not moderator.visible_until_rejected:
                    # save instance with data from changed_object
                    moderated_obj.changed_object.save_base(raw=True)

                    # save new data in moderated object
                    moderated_obj.changed_object = copied_instance

                moderated_obj.moderation_status = MODERATION_STATUS_PENDING
                moderated_obj.save()
                moderator.inform_moderator(instance)
                instance._moderated_object = moderated_obj

    def _copy_model_instance(self, obj):
        initial = dict(
            [(f.name, getattr(obj, f.name)) for f in obj._meta.fields])
        return obj.__class__(**initial)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

pre_moderation = django.dispatch.Signal(providing_args=["instance", "status"])

post_moderation = django.dispatch.Signal(providing_args=["instance", "status"])

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
import os
from os.path import dirname, abspath
from optparse import OptionParser

from django.conf import settings, global_settings

# For convenience configure settings if they are not pre-configured or if we
# haven't been provided settings to use by environment variable.
if not settings.configured and not os.environ.get('DJANGO_SETTINGS_MODULE'):
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',

            'moderation',
            'tests',
        ],
        SERIALIZATION_MODULES = {},
        MEDIA_URL = '/media/',
        STATIC_URL = '/static/',
        ROOT_URLCONF = 'tests.urls.default',

        DJANGO_MODERATION_MODERATORS = (
            'test@example.com',
        ),
        DEBUG=True,
        SITE_ID=1,
    )

from django.test.simple import DjangoTestSuiteRunner


def runtests(*test_args, **kwargs):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['tests']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    test_runner = DjangoTestSuiteRunner(verbosity=kwargs.get('verbosity', 1), interactive=kwargs.get('interactive', False), failfast=kwargs.get('failfast'))
    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--failfast', action='store_true', default=False, dest='failfast')

    (options, args) = parser.parse_args()

    runtests(failfast=options.failfast, *args)
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from moderation.admin import ModerationAdmin
from .models import Book


class BookAdmin(ModerationAdmin):
    pass

admin.site.register(Book, BookAdmin)

########NEW FILE########
__FILENAME__ = models
"""
Test models used in django-moderations tests
"""
from django.conf import settings
from django.db import models
from django.db.models.manager import Manager
from django import VERSION


class UserProfile(models.Model):
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), 
                             related_name='user_profile_set')
    description = models.TextField()
    url = models.URLField()

    def __unicode__(self):
        return "%s - %s" % (self.user, self.url)


class SuperUserProfile(UserProfile):
    super_power = models.TextField()

    def __unicode__(self):
        return "%s - %s - %s" % (self.user, self.url, self.super_power)


class ModelWithSlugField(models.Model):
    slug = models.SlugField(unique=True)


class ModelWithSlugField2(models.Model):
    slug = models.SlugField(unique=True)


class MenManager(Manager):

    def get_query_set(self):
        query_set = super(MenManager, self).get_query_set()
        return query_set.filter(gender=1)


class WomenManager(Manager):

    def get_query_set(self):
        query_set = super(WomenManager, self).get_query_set()
        return query_set.filter(gender=0)


class ModelWithMultipleManagers(models.Model):
    gender = models.SmallIntegerField()
    objects = Manager()
    men = MenManager()
    women = WomenManager()


class ModelWIthDateField(models.Model):
    date = models.DateField(auto_now=True)


class ModelWithVisibilityField(models.Model):
    test = models.CharField(max_length=20)
    is_public = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s - is public %s' % (self.test, self.is_public)


class ModelWithWrongVisibilityField(models.Model):
    test = models.CharField(max_length=20)
    is_public = models.IntegerField()

    def __unicode__(self):
        return u'%s - is public %s' % (self.test, self.is_public)


class ModelWithImage(models.Model):
    image = models.ImageField(upload_to='tmp')


class ModelWithModeratedFields(models.Model):
    moderated = models.CharField(max_length=20)
    also_moderated = models.CharField(max_length=20)
    unmoderated = models.CharField(max_length=20)

    moderated_fields = ('moderated', 'also_moderated')


class ProxyProfile(UserProfile):

    class Meta(object):
        proxy = True


class Book(models.Model):
    title = models.CharField(max_length=20)
    author = models.CharField(max_length=20)


if VERSION[:2] >= (1, 5):

    from django.contrib.auth.models import AbstractUser

    class CustomUser(AbstractUser):
        date_of_birth = models.DateField(blank=True, null=True)
        height = models.FloatField(blank=True, null=True)

    class UserProfileWithCustomUser(models.Model):
        user = models.ForeignKey(CustomUser)
        description = models.TextField()
        url = models.URLField()

        def __unicode__(self):
            return "%s - %s" % (self.user, self.url)

        def get_absolute_url(self):
            return '/test/'

########NEW FILE########
__FILENAME__ = moderator
from moderation import moderation
from models import Book

moderation.register(Book)

########NEW FILE########
__FILENAME__ = auto_discover
from django.test.testcases import TestCase

from tests.utils import setup_moderation, teardown_moderation
from tests.models import Book
from moderation.helpers import auto_discover


class AutoDiscoverAcceptanceTestCase(TestCase):
    '''
    As a developer I want to have a way auto discover all apps that have module
    moderator and register it with moderation.
    '''
    urls = 'tests.urls.auto_discover'

    def setUp(self):
        setup_moderation()

    def tearDown(self):
        teardown_moderation()

    def test_all_app_containing_moderator_module_should_be_registered(self):
        auto_discover()
        from moderation import moderation

        self.assertTrue(Book in moderation._registered_models)

########NEW FILE########
__FILENAME__ = exclude
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from moderation.moderator import GenericModerator
from tests.models import UserProfile,\
    ModelWithModeratedFields
from django.test.testcases import TestCase
from tests.utils import setup_moderation, teardown_moderation


class ExcludeAcceptanceTestCase(TestCase):
    '''
    As developer I want to have way to ignore/exclude model fields from 
    moderation
    '''
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.client.login(username='admin', password='aaaa')

        class UserProfileModerator(GenericModerator):
            fields_exclude = ['url']

        setup_moderation([(UserProfile, UserProfileModerator)])

    def tearDown(self):
        teardown_moderation()

    def test_excluded_field_should_not_be_moderated_when_obj_is_edited(self):
        '''
        Change field that is excluded from moderation,
        go to moderation admin
        '''
        profile = UserProfile.objects.get(user__username='moderator')

        profile.url = 'http://dominno.pl'

        profile.save()

        url = reverse('admin:moderation_moderatedobject_change',
                      args=(profile.moderated_object.pk,))

        response = self.client.get(url, {})

        changes = [change.change for change in response.context['changes']]

        self.assertFalse((u'http://www.google.com',
                          u'http://dominno.pl') in changes)

    def test_non_excluded_field_should_be_moderated_when_obj_is_edited(self):
        '''
        Change field that is not excluded from moderation,
        go to moderation admin
        '''
        profile = UserProfile.objects.get(user__username='moderator')

        profile.description = 'New description'

        profile.save()

        url = reverse('admin:moderation_moderatedobject_change',
                      args=(profile.moderated_object.pk,))

        response = self.client.get(url, {})

        changes = [change.change for change in response.context['changes']]

        self.assertTrue(("Old description", 'New description') in changes)

    def test_excluded_field_should_not_be_moderated_when_obj_is_created(self):
        '''
        Create new object, only non excluded fields are used
        by moderation system
        '''
        profile = UserProfile(description='Profile for new user',
                              url='http://www.dominno.com',
                              user=User.objects.get(username='user1'))
        profile.save()

        url = reverse('admin:moderation_moderatedobject_change',
                      args=(profile.moderated_object.pk,))

        response = self.client.get(url, {})

        changes = [change.change for change in response.context['changes']]

        self.assertFalse((u'http://www.dominno.com',
                          u'http://www.dominno.com') in changes)


class ModeratedFieldsAcceptanceTestCase(TestCase):
    '''
    Test that `moderated_fields` model argument excludes all fields not listed
    '''

    def setUp(self):
        setup_moderation([ModelWithModeratedFields])

    def tearDown(self):
        teardown_moderation()

    def test_moderated_fields_not_added_to_excluded_fields_list(self):
        from moderation import moderation

        moderator = moderation._registered_models[ModelWithModeratedFields]

        self.assertTrue('moderated' not in moderator.fields_exclude)
        self.assertTrue('also_moderated' not in moderator.fields_exclude)

    def test_unmoderated_fields_added_to_excluded_fields_list(self):
        from moderation import moderation

        moderator = moderation._registered_models[ModelWithModeratedFields]

        self.assertTrue('unmoderated' in moderator.fields_exclude)

########NEW FILE########
__FILENAME__ = admin
import mock
from django.contrib.admin.sites import site
from django.contrib.auth.models import User, Permission
from django.test.testcases import TestCase

from tests.utils.request_factory import RequestFactory
from moderation.admin import ModerationAdmin, approve_objects, reject_objects,\
    ModeratedObjectAdmin, set_objects_as_pending
from tests.utils.testcases import WebTestCase
from moderation.moderator import GenericModerator
from moderation.models import ModeratedObject,\
    MODERATION_DRAFT_STATE, MODERATION_STATUS_APPROVED,\
    MODERATION_STATUS_REJECTED, MODERATION_STATUS_PENDING
from tests.models import UserProfile, Book, \
    ModelWithSlugField, ModelWithSlugField2, SuperUserProfile
from tests.utils import setup_moderation, teardown_moderation


class ModeratedObjectAdminTestCase(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        rf = RequestFactory()
        rf.login(username='admin', password='aaaa')
        self.request = rf.get('/admin/moderation/')
        self.request.user = User.objects.get(username='admin')
        self.admin = ModeratedObjectAdmin(ModeratedObject, site)

        for user in User.objects.all():
            ModeratedObject(content_object=user).save()

    def test_get_actions_should_not_return_delete_selected(self):
        actions = self.admin.get_actions(self.request)
        self.failIfEqual('delete_selected' in actions, True)

    def test_content_object_returns_deserialized_object(self):
        user = User.objects.get(username='admin')
        moderated_object = ModeratedObject(content_object=user)
        moderated_object.save()
        content_object = self.admin.content_object(moderated_object)
        self.assertEqual(content_object, "admin")

    def test_get_moderated_object_form(self):
        form = self.admin.get_moderated_object_form(UserProfile)
        self.assertEqual(repr(form),
                         "<class 'moderation.admin.ModeratedObjectForm'>")


class ModeratedObjectAdminBehaviorTestCase(WebTestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        class BookModerator(GenericModerator):
            auto_approve_for_staff = False
        self.moderation = setup_moderation([(Book, BookModerator)])

        self.user = User.objects.get(username='user1')
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_book'))

        self.book = Book.objects.create(title="Book not modified", 
                                        author="Nico")

    def tearDown(self):
        teardown_moderation()

    def test_set_changed_by_property(self):
        """even_when_auto_approve_for_staff_is_false"""
        self.assertEquals(self.book.moderated_object.changed_by, None)
        page = self.get('/admin/tests/book/1/')
        form = page.form
        form['title'] = "Book modified"
        page = form.submit()
        self.assertIn(page.status_code, [302, 200])
        book = Book._default_manager.get(pk=self.book.pk)  # refetch the obj
        self.assertEquals(book.title, "Book not modified")
        moderated_obj = ModeratedObject.objects.get_for_instance(book)
        self.assertEquals(moderated_obj.changed_object.title, "Book modified")
        self.assertEquals(moderated_obj.changed_by, self.user)


class AdminActionsTestCase(TestCase):
    fixtures = ['test_users.json']
    urls = 'moderation.tests.test_urls'

    def setUp(self):
        rf = RequestFactory()
        rf.login(username='admin', password='aaaa')
        self.request = rf.get('/admin/moderation/')
        self.request.user = User.objects.get(username='admin')
        self.admin = ModeratedObjectAdmin(ModeratedObject, site)

        self.moderation = setup_moderation([User])

        for user in User.objects.all():
            ModeratedObject(content_object=user).save()

        self.moderated_objects = ModeratedObject.objects.all()

    def tearDown(self):
        teardown_moderation()

    def test_queryset_should_return_only_moderation_ready_objects(self):
        qs = self.admin.queryset(self.request)
        qs = qs.filter(moderation_state=MODERATION_DRAFT_STATE)
        self.assertEqual(list(qs), [])

    def test_approve_objects(self):
        approve_objects(self.admin, self.request, self.moderated_objects)

        for obj in ModeratedObject.objects.all():
            self.assertEqual(obj.moderation_status,
                             MODERATION_STATUS_APPROVED)

    def test_reject_objects(self):
        qs = ModeratedObject.objects.all()

        reject_objects(self.admin, self.request, qs)

        for obj in ModeratedObject.objects.all():
            self.assertEqual(obj.moderation_status,
                             MODERATION_STATUS_REJECTED)

    def test_set_objects_as_pending(self):
        for obj in self.moderated_objects:
            obj.approve(moderated_by=self.request.user)

        set_objects_as_pending(self.admin, self.request,
                               self.moderated_objects)

        for obj in ModeratedObject.objects.all():
            self.assertEqual(obj.moderation_status,
                             MODERATION_STATUS_PENDING)


class ModerationAdminSendMessageTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.moderation = setup_moderation([UserProfile])

        rf = RequestFactory()
        rf.login(username='admin', password='aaaa')
        self.request = rf.get('/admin/moderation/')
        self.request.user = User.objects.get(username='admin')
        self.request._messages = mock.Mock()
        self.admin = ModerationAdmin(UserProfile, site)

        self.profile = UserProfile.objects.get(user__username='moderator')
        self.moderated_obj = ModeratedObject(content_object=self.profile)
        self.moderated_obj.save()

    def tearDown(self):
        teardown_moderation()

    def test_send_message_when_object_has_no_moderated_object(self):
        profile = SuperUserProfile(description='Profile for new user',
                                   url='http://www.yahoo.com',
                                   user=User.objects.get(username='user1'),
                                   super_power='text')

        profile.save()

        self.moderation.register(SuperUserProfile)

        self.admin.send_message(self.request, profile.pk)

        args, kwargs = self.request._messages.add.call_args
        level, message, tags = args
        self.assertEqual(unicode(message), u"This object is not registered "
                                           u"with the moderation system.")

    def test_send_message_status_pending(self):
        self.moderated_obj.moderation_status = MODERATION_STATUS_PENDING
        self.moderated_obj.save()

        self.admin.send_message(self.request, self.profile.pk)

        args, kwargs = self.request._messages.add.call_args
        level, message, tags = args
        self.assertEqual(unicode(message),
                         u"Object is not viewable on site, "
                         u"it will be visible if moderator accepts it")

    def test_send_message_status_rejected(self):
        self.moderated_obj.moderation_status = MODERATION_STATUS_REJECTED
        self.moderated_obj.moderation_reason = u'Reason for rejection'
        self.moderated_obj.save()

        self.admin.send_message(self.request, self.profile.pk)

        args, kwargs = self.request._messages.add.call_args
        level, message, tags = args
        self.assertEqual(unicode(message),
                         u"Object has been rejected by "
                         u"moderator, reason: Reason for rejection")

    def test_send_message_status_approved(self):
        self.moderated_obj.moderation_status = MODERATION_STATUS_APPROVED
        self.moderated_obj.save()

        self.admin.send_message(self.request, self.profile.pk)

        args, kwargs = self.request._messages.add.call_args
        level, message, tags = args
        self.assertEqual(unicode(message), "Object has been approved by "
                                           "moderator and is visible on site")


try:
    from moderation.filterspecs import ContentTypeFilterSpec
except ImportError:
    # Django 1.4
    pass
else:

    class ContentTypeFilterSpecTextCase(TestCase):

        fixtures = ['test_users.json', 'test_moderation.json']

        def setUp(self):
            from tests.utils import setup_moderation

            rf = RequestFactory()
            rf.login(username='admin', password='aaaa')
            self.request = rf.get('/admin/moderation/')
            self.request.user = User.objects.get(username='admin')
            self.admin = ModerationAdmin(UserProfile, site)

            models = [ModelWithSlugField2, ModelWithSlugField]
            self.moderation = setup_moderation(models)

            self.m1 = ModelWithSlugField(slug='test')
            self.m1.save()

            self.m2 = ModelWithSlugField2(slug='test')
            self.m2.save()

        def tearDown(self):
            teardown_moderation()

        def test_content_types_and_its_order(self):
            f = ModeratedObject._meta.get_field('content_type')
            filter_spec = ContentTypeFilterSpec(f, self.request, {},
                                                ModeratedObject, self.admin)

            self.assertEqual(
                [x[1] for x in filter_spec.lookup_choices],
                [u'Model with slug field',
                 u'Model with slug field2'])

            self.assertEqual(unicode(filter_spec.content_types),
                             u"[<ContentType: model with slug field>, "
                             "<ContentType: model with slug field2>]")

########NEW FILE########
__FILENAME__ = diff
# -*- coding: utf-8 -*-

import unittest
from moderation.diff import get_changes_between_models, html_to_list,\
    TextChange, get_diff_operations, ImageChange
from django.test.testcases import TestCase
from django.contrib.auth.models import User
from django.db.models import fields
from tests.models import UserProfile, \
    ModelWIthDateField, ModelWithImage
from moderation.models import ModeratedObject
import re


_norm_whitespace_re = re.compile(r'\s+')


def norm_whitespace(s):
    return _norm_whitespace_re.sub(' ', s).strip()


class TextChangeObjectTestCase(unittest.TestCase):

    def setUp(self):
        self.change = TextChange(verbose_name='description',
                                 field=fields.CharField,
                                 change=('test1', 'test2'))

    def test_verbose_name(self):
        self.assertEqual(self.change.verbose_name, 'description')

    def test_field(self):
        self.assertEqual(self.change.field, fields.CharField)

    def test_change(self):
        self.assertEqual(self.change.change, ('test1', 'test2'))

    def test_diff_text_change(self):
        self.assertEqual(
            self.change.diff,
            u'<del class="diff modified">test1'
            u'</del><ins class="diff modified">test2</ins>\n')

    def test_render_diff(self):
        diff_operations = get_diff_operations('test1', 'test2')
        self.assertEqual(
            self.change.render_diff(
                'moderation/html_diff.html',
                {'diff_operations': diff_operations}),
            u'<del class="diff modified">test1'
            u'</del><ins class="diff modified">test2</ins>\n')


class ImageChangeObjectTestCase(unittest.TestCase):

    def setUp(self):
        image1 = ModelWithImage(image='my_image.jpg')
        image1.save()
        image2 = ModelWithImage(image='my_image2.jpg')
        image2.save()
        self.left_image = image1.image
        self.right_image = image2.image
        self.change = ImageChange(verbose_name='image',
                                  field=fields.files.ImageField,
                                  change=(self.left_image, self.right_image))

    def test_verbose_name(self):
        self.assertEqual(self.change.verbose_name, 'image')

    def test_field(self):
        self.assertEqual(self.change.field, fields.files.ImageField)

    def test_change(self):
        self.assertEqual(self.change.change, (self.left_image,
                                              self.right_image))

    def test_diff(self):
        self.assertEqual(norm_whitespace(self.change.diff),
                         norm_whitespace(u'<div class="img-wrapper"> '
                                         u'<img src="/media/my_image.jpg"> '
                                         u'<img src="/media/my_image2.jpg"> '
                                         u'</div>'))


class DiffModeratedObjectTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.profile = UserProfile.objects.get(user__username='moderator')

    def test_get_changes_between_models(self):
        self.profile.description = 'New description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        self.profile = UserProfile.objects.get(user__username='moderator')

        changes = get_changes_between_models(moderated_object.changed_object,
                                             self.profile)

        self.assertEqual(
            unicode(changes),
            u"{u'userprofile__url': Change object: http://www.google.com"
            u" - http://www.google.com, u'userprofile__description': "
            u"Change object: New description - Old description, "
            u"u'userprofile__user': Change object: 1 - 1}")

    def test_foreign_key_changes(self):
        self.profile.user = User.objects.get(username='admin')
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        self.profile = UserProfile.objects.get(user__username='moderator')

        changes = get_changes_between_models(moderated_object.changed_object,
                                             self.profile)

        self.assertEqual(
            unicode(changes),
            u"{u'userprofile__url': Change object: http://www.google.com"
            u" - http://www.google.com, u'userprofile__description': "
            u"Change object: Old description - Old description, "
            u"u'userprofile__user': Change object: 4 - 1}")

    def test_get_changes_between_models_image(self):
        '''Verify proper diff for ImageField fields'''

        image1 = ModelWithImage(image='tmp/test1.jpg')
        image1.save()
        image2 = ModelWithImage(image='tmp/test2.jpg')
        image2.save()

        changes = get_changes_between_models(image1, image2)
        self.assertEqual(
            norm_whitespace(changes['modelwithimage__image'].diff),
            norm_whitespace(u'<div class="img-wrapper"> '
                            u'<img src="/media/tmp/test1.jpg"> '
                            u'<img src="/media/tmp/test2.jpg"> '
                            u'</div>'))

    def test_excluded_fields_should_be_excluded_from_changes(self):
        self.profile.description = 'New description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        self.profile = UserProfile.objects.get(user__username='moderator')

        changes = get_changes_between_models(
            moderated_object.changed_object,
            self.profile, excludes=['description'])

        self.assertEqual(unicode(changes),
                         u"{u'userprofile__url': Change object: "
                         u"http://www.google.com - http://www.google.com, "
                         u"u'userprofile__user': Change object: 1 - 1}")


class DiffTestCase(unittest.TestCase):

    def test_html_to_list(self):
        html = u'<p id="test">text</p><b>some long text \n\t\r text</b>'\
               u'<div class="test">text</div>'
        html_list = [u'<p id="test">',
                     u'text',
                     u'</p>',
                     u'<b>',
                     u'some ',
                     u'long ',
                     u'text ',
                     u'\n\t\r ',
                     u'text',
                     u'</b>',
                     u'<div class="test">',
                     u'text',
                     u'</div>',
                     ]

        self.assertEqual(html_to_list(html), html_list)

    def test_html_to_list_non_ascii(self):
        html = u'<p id="test">text</p><b>Las demás lenguas españolas'\
               u' serán también</b><div class="test">text</div>'

        self.assertEqual(html_to_list(html), ['<p id="test">',
                                              'text',
                                              '</p>',
                                              '<b>',
                                              u'Las ',
                                              u'dem\xe1s ',
                                              u'lenguas ',
                                              u'espa\xf1olas ',
                                              u'ser\xe1n ',
                                              u'tambi\xe9n',
                                              '</b>',
                                              '<div class="test">',
                                              'text',
                                              '</div>',
                                              ])


class DateFieldTestCase(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.obj1 = ModelWIthDateField()
        self.obj2 = ModelWIthDateField()

        self.obj1.save()
        self.obj2.save()

    def test_date_field_in_model_object_should_be_unicode(self):
        '''Test if when model field value is not unicode, then when getting 
           changes between models, all changes should be unicode.
        '''
        changes = get_changes_between_models(self.obj1, self.obj2)

        date_change = changes['modelwithdatefield__date']

        self.assertTrue(isinstance(date_change.change[0], unicode))
        self.assertTrue(isinstance(date_change.change[1], unicode))

    def test_html_to_list_should_return_list(self):
        '''Test if changes dict generated from model that has non unicode field
           is properly used by html_to_list function
        '''
        changes = get_changes_between_models(self.obj1, self.obj2)

        date_change = changes['modelwithdatefield__date']

        changes_list1 = html_to_list(date_change.change[0])
        changes_list2 = html_to_list(date_change.change[1])

        self.assertTrue(isinstance(changes_list1, list))
        self.assertTrue(isinstance(changes_list2, list))

########NEW FILE########
__FILENAME__ = forms
from django.db.models.fields.files import ImageFieldFile
from django.forms import CharField
from django.contrib.auth.models import User
from django.test.testcases import TestCase

from tests.models import UserProfile, ModelWithImage
from moderation.forms import BaseModeratedObjectForm
from tests.utils import setup_moderation, teardown_moderation


class FormsTestCase(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.user = User.objects.get(username='moderator')

        class ModeratedObjectForm(BaseModeratedObjectForm):
            extra = CharField(required=False)

            class Meta:
                model = UserProfile

        self.ModeratedObjectForm = ModeratedObjectForm
        self.moderation = setup_moderation([UserProfile, ModelWithImage])

    def tearDown(self):
        teardown_moderation()

    def test_create_form_class(self):
        form = self.ModeratedObjectForm()
        self.assertEqual(form._meta.model.__name__, 'UserProfile')

    def test_if_form_is_initialized_new_object(self):
        profile = UserProfile(description="New description",
                              url='http://test.com',
                              user=self.user)
        profile.save()

        form = self.ModeratedObjectForm(instance=profile)
        self.assertEqual(form.initial['description'], u'New description')

    def test_if_form_is_initialized_existing_object(self):
        profile = UserProfile(description="old description",
                              url='http://test.com',
                              user=self.user)
        profile.save()

        profile.moderated_object.approve(moderated_by=self.user)

        profile.description = u"Changed description"
        profile.save()

        form = self.ModeratedObjectForm(instance=profile)

        profile = UserProfile.objects.get(id=1)

        self.assertEqual(profile.description, u"old description")
        self.assertEqual(form.initial['description'], u'Changed description')

    def test_if_form_has_image_field_instance_of_image_field_file(self):
        object = ModelWithImage(image='my_image.jpg')
        object.save()

        object = ModelWithImage.unmoderated_objects.get(id=1)
        form = self.ModeratedObjectForm(instance=object)
        self.assertTrue(isinstance(form.initial['image'], ImageFieldFile),
                        'image in form.initial is instance of ImageField File')

    def test_form_when_obj_has_no_moderated_obj(self):
        self.moderation.unregister(UserProfile)
        profile = UserProfile(description="old description",
                              url='http://test.com',
                              user=self.user)
        profile.save()
        self.moderation.register(UserProfile)

        form = self.ModeratedObjectForm(instance=profile)

        self.assertEqual(form.initial['description'], u'old description')

    def test_if_form_is_initialized_new_object_with_initial(self):
        profile = UserProfile(description="New description",
                              url='http://test.com',
                              user=self.user)
        profile.save()

        form = self.ModeratedObjectForm(initial={'extra': 'value'},
                                        instance=profile)

        self.assertEqual(form.initial['description'], u'New description')
        self.assertEqual(form.initial['extra'], u'value')

########NEW FILE########
__FILENAME__ = managers
from django.test.testcases import TestCase
from django.contrib.auth.models import User
from tests.models import UserProfile, \
    ModelWithSlugField2, ModelWithVisibilityField
from moderation.managers import ModerationObjectsManager
from django.db.models.manager import Manager
from moderation.models import ModeratedObject
from django.core.exceptions import MultipleObjectsReturned
from moderation.moderator import GenericModerator
from tests.utils import setup_moderation, teardown_moderation


class ModerationObjectsManagerTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):

        self.user = User.objects.get(username='moderator')
        self.profile = UserProfile.objects.get(user__username='moderator')

        class UserProfileModerator(GenericModerator):
            visibility_column = 'is_public'

        self.moderation = setup_moderation(
            [
                UserProfile,
                (ModelWithVisibilityField, UserProfileModerator)])

    def tearDown(self):
        teardown_moderation()

    def test_moderation_objects_manager(self):
        ManagerClass = ModerationObjectsManager()(Manager)

        self.assertEqual(
            unicode(ManagerClass.__bases__),
            u"(<class 'moderation.managers.ModerationObjectsManager'>"
            u", <class 'django.db.models.manager.Manager'>)")

    def test_filter_moderated_objects_returns_empty_queryset(self):
        """Test filter_moderated_objects returns empty queryset
        for object that has moderated object"""

        ManagerClass = ModerationObjectsManager()(Manager)
        manager = ManagerClass()
        manager.model = UserProfile

        query_set = UserProfile._default_manager.all()
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        self.assertEqual(unicode(manager.filter_moderated_objects(query_set)),
                         u"[]")

    def test_filter_moderated_objects_returns_object(self):
        """Test if filter_moderated_objects return object when object 
        doesn't have moderated object or deserialized object is <> object"""
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()
        moderated_object.approve()

        self.profile.description = "New"
        self.profile.save()

        self.assertEqual(unicode(UserProfile.objects.all()),
                         u'[<UserProfile: moderator - http://www.google.com>]')

    def test_exclude_objs_by_visibility_col(self):
        ManagerClass = ModerationObjectsManager()(Manager)
        manager = ManagerClass()
        manager.model = ModelWithVisibilityField

        ModelWithVisibilityField(test='test 1').save()
        ModelWithVisibilityField(test='test 2', is_public=True).save()

        query_set = ModelWithVisibilityField.objects.all()

        query_set = manager.exclude_objs_by_visibility_col(query_set)

        self.assertEqual(
            unicode(query_set),
            u"[<ModelWithVisibilityField: test 2 - is public True>]")


class ModeratedObjectManagerTestCase(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.moderation = setup_moderation([UserProfile, ModelWithSlugField2])

        self.user = User.objects.get(username='admin')

    def tearDown(self):
        teardown_moderation()

    def test_objects_with_same_object_id(self):
        model1 = ModelWithSlugField2(slug='test')
        model1.save()

        model2 = UserProfile(description='Profile for new user',
                             url='http://www.yahoo.com',
                             user=User.objects.get(username='user1'))

        model2.save()

        self.assertRaises(MultipleObjectsReturned,
                          ModeratedObject.objects.get,
                          object_pk=model2.pk)

        moderated_obj1 = ModeratedObject.objects.get_for_instance(model1)
        moderated_obj2 = ModeratedObject.objects.get_for_instance(model2)

        self.assertEqual(repr(moderated_obj1),
                         u"<ModeratedObject: ModelWithSlugField2 object>")
        self.assertEqual(repr(moderated_obj2),
                         u'<ModeratedObject: user1 - http://www.yahoo.com>')

########NEW FILE########
__FILENAME__ = models
from django.test.testcases import TestCase
from django import VERSION
from django.db import models
from django.contrib.auth.models import User, Group
from django.test.utils import override_settings
from tests.models import UserProfile,\
    SuperUserProfile, ModelWithSlugField2, ProxyProfile
from moderation.models import ModeratedObject, MODERATION_STATUS_APPROVED,\
    MODERATION_STATUS_PENDING, MODERATION_STATUS_REJECTED
from moderation.fields import SerializedObjectField
from moderation.register import ModerationManager, RegistrationError
from moderation.moderator import GenericModerator
from moderation.helpers import automoderate
from tests.utils import setup_moderation, teardown_moderation
from tests.utils import unittest


class SerializationTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.user = User.objects.get(username='moderator')
        self.profile = UserProfile.objects.get(user__username='moderator')

    def test_serialize_of_object(self):
        """Test if object is properly serialized to json"""

        json_field = SerializedObjectField()

        self.assertEqual(
            json_field._serialize(self.profile),
            '[{"pk": 1, "model": "tests.userprofile", "fields": '
            '{"url": "http://www.google.com", "user": 1, '
            '"description": "Old description"}}]',
        )

    def test_serialize_with_inheritance(self):
        """Test if object is properly serialized to json"""

        profile = SuperUserProfile(description='Profile for new super user',
                                   url='http://www.test.com',
                                   user=User.objects.get(username='user1'),
                                   super_power='invisibility')
        profile.save()
        json_field = SerializedObjectField()

        self.assertEqual(
            json_field._serialize(profile),
            '[{"pk": 2, "model": "tests.superuserprofile",'
            ' "fields": {"super_power": "invisibility"}}, '
            '{"pk": 2, "model": "tests.userprofile", "fields":'
            ' {"url": "http://www.test.com", "user": 2,'
            ' "description": "Profile for new super user"}}]')

    def test_deserialize(self):
        value = '[{"pk": 1, "model": "tests.userprofile", "fields": '\
                '{"url": "http://www.google.com", "user": 1, '\
                '"description": "Profile description"}}]'
        json_field = SerializedObjectField()
        object = json_field._deserialize(value)

        self.assertEqual(repr(object),
                         '<UserProfile: moderator - http://www.google.com>')
        self.assertTrue(isinstance(object, UserProfile))

    def test_deserialize_with_inheritance(self):
        value = '[{"pk": 2, "model": "tests.superuserprofile",'\
                ' "fields": {"super_power": "invisibility"}}, '\
                '{"pk": 2, "model": "tests.userprofile", "fields":'\
                ' {"url": "http://www.test.com", "user": 2,'\
                ' "description": "Profile for new super user"}}]'

        json_field = SerializedObjectField()
        object = json_field._deserialize(value)

        self.assertTrue(isinstance(object, SuperUserProfile))
        self.assertEqual(
            repr(object),
            '<SuperUserProfile: user1 - http://www.test.com - invisibility>')

    def test_deserialzed_object(self):
        moderated_object = ModeratedObject(content_object=self.profile)
        self.profile.description = 'New description'
        moderated_object.changed_object = self.profile
        moderated_object.save()
        pk = moderated_object.pk

        moderated_object = ModeratedObject.objects.get(pk=pk)

        self.assertEqual(moderated_object.changed_object.description,
                         'New description')

        self.assertEqual(moderated_object.content_object.description,
                         u'Old description')

    def test_change_of_deserialzed_object(self):
        self.profile.description = 'New description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()
        pk = moderated_object.pk

        self.profile.description = 'New changed description'
        moderated_object.changed_object = self.profile.description
        moderated_object.save()

        moderated_object = ModeratedObject.objects.get(pk=pk)

        self.assertEqual(moderated_object.changed_object.description,
                         'New changed description')

    @unittest.skipIf(VERSION[:2] < (1, 4), "Proxy models require 1.4")
    def test_serialize_proxy_model(self):
        "Handle proxy models in the serialization."
        profile = ProxyProfile(description="I'm a proxy.",
                               url="http://example.com",
                               user=User.objects.get(username='user1'))
        profile.save()
        json_field = SerializedObjectField()

        self.assertEqual(
            json_field._serialize(profile),
            '[{"pk": 2, "model": "tests.proxyprofile", "fields": '
            '{"url": "http://example.com", "user": 2, '
            '"description": "I\'m a proxy."}}]',)

    @unittest.skipIf(VERSION[:2] < (1, 4), "Proxy models require 1.4")
    def test_deserialize_proxy_model(self):
        "Correctly restore a proxy model."
        value = '[{"pk": 2, "model": "tests.proxyprofile", "fields": '\
            '{"url": "http://example.com", "user": 2, '\
            '"description": "I\'m a proxy."}}]'

        json_field = SerializedObjectField()
        profile = json_field._deserialize(value)
        self.assertTrue(isinstance(profile, ProxyProfile))
        self.assertEqual(profile.url, "http://example.com")
        self.assertEqual(profile.description, "I\'m a proxy.")
        self.assertEqual(profile.user_id, 2)


class ModerateTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.user = User.objects.get(username='moderator')
        self.profile = UserProfile.objects.get(user__username='moderator')
        self.moderation = setup_moderation([UserProfile])

    def tearDown(self):
        teardown_moderation()

    def test_approval_status_pending(self):
        """test if before object approval status is pending"""

        self.profile.description = 'New description'
        self.profile.save()

        self.assertEqual(self.profile.moderated_object.moderation_status,
                         MODERATION_STATUS_PENDING)

    def test_moderate(self):
        self.profile.description = 'New description'
        self.profile.save()

        self.profile.moderated_object._moderate(MODERATION_STATUS_APPROVED,
                                                self.user, "Reason")

        self.assertEqual(self.profile.moderated_object.moderation_status,
                         MODERATION_STATUS_APPROVED)
        self.assertEqual(self.profile.moderated_object.moderated_by, self.user)
        self.assertEqual(self.profile.moderated_object.moderation_reason,
                         "Reason")

    def test_approve_moderated_object(self):
        """test if after object approval new data is saved."""
        self.profile.description = 'New description'

        moderated_object = ModeratedObject(content_object=self.profile)

        moderated_object.save()

        moderated_object.approve(moderated_by=self.user)

        user_profile = UserProfile.objects.get(user__username='moderator')

        self.assertEqual(user_profile.description, 'New description')

    def test_approve_moderated_object_new_model_instance(self):
        profile = UserProfile(description='Profile for new user',
                              url='http://www.test.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        profile.moderated_object.approve(self.user)

        user_profile = UserProfile.objects.get(url='http://www.test.com')

        self.assertEqual(user_profile.description, 'Profile for new user')

    def test_reject_moderated_object(self):
        self.profile.description = 'New description'
        self.profile.save()

        self.profile.moderated_object.reject(self.user)

        user_profile = UserProfile.objects.get(user__username='moderator')

        self.assertEqual(user_profile.description, "Old description")
        self.assertEqual(self.profile.moderated_object.moderation_status,
                         MODERATION_STATUS_REJECTED)

    def test_has_object_been_changed_should_be_true(self):
        self.profile.description = 'Old description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()
        moderated_object.approve(moderated_by=self.user)

        user_profile = UserProfile.objects.get(user__username='moderator')

        self.profile.description = 'New description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        value = moderated_object.has_object_been_changed(user_profile)

        self.assertEqual(value, True)

    def test_has_object_been_changed_should_be_false(self):
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        value = moderated_object.has_object_been_changed(self.profile)

        self.assertEqual(value, False)


class AutoModerateTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.moderation = ModerationManager()

        class UserProfileModerator(GenericModerator):
            auto_approve_for_superusers = True
            auto_approve_for_staff = True
            auto_reject_for_groups = ['banned']

        self.moderation.register(UserProfile, UserProfileModerator)

        self.user = User.objects.get(username='moderator')
        self.profile = UserProfile.objects.get(user__username='moderator')

    def tearDown(self):
        teardown_moderation()

    def test_auto_approve_helper_status_approved(self):
        self.profile.description = 'New description'
        self.profile.save()

        status = automoderate(self.profile, self.user)

        self.assertEqual(status, MODERATION_STATUS_APPROVED)

        profile = UserProfile.objects.get(user__username='moderator')
        self.assertEqual(profile.description, 'New description')

    def test_auto_approve_helper_status_rejected(self):
        group = Group(name='banned')
        group.save()
        self.user.groups.add(group)
        self.user.save()

        self.profile.description = 'New description'
        self.profile.save()

        status = automoderate(self.profile, self.user)

        profile = UserProfile.objects.get(user__username='moderator')

        self.assertEqual(status,
                         MODERATION_STATUS_REJECTED)
        self.assertEqual(profile.description, u'Old description')

    def test_model_not_registered_with_moderation(self):
        obj = ModelWithSlugField2(slug='test')
        obj.save()

        self.assertRaises(RegistrationError, automoderate, obj, self.user)


@unittest.skipIf(VERSION[:2] < (1, 5), "Custom auth users require 1.5")
@override_settings(AUTH_USER_MODEL='tests.CustomUser')
class ModerateCustomUserTestCase(TestCase):

    def setUp(self):
        from tests.models import CustomUser,\
            UserProfileWithCustomUser
        from django.conf import settings
        self.user = CustomUser.objects.create(
            username='custom_user',
            password='aaaa')
        self.copy_m = ModeratedObject.moderated_by
        ModeratedObject.moderated_by = models.ForeignKey(
            getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), 
            blank=True, null=True, editable=False,
            related_name='moderated_by_set')

        self.profile = UserProfileWithCustomUser.objects.create(
            user=self.user,
            description='Old description',
            url='http://google.com')
        self.moderation = setup_moderation([UserProfileWithCustomUser])

    def tearDown(self):
        teardown_moderation()
        ModeratedObject.moderated_by = self.copy_m

    def test_approval_status_pending(self):
        """test if before object approval status is pending"""

        self.profile.description = 'New description'
        self.profile.save()

        self.assertEqual(self.profile.moderated_object.moderation_status,
                         MODERATION_STATUS_PENDING)

    def test_moderate(self):
        self.profile.description = 'New description'
        self.profile.save()

        self.profile.moderated_object._moderate(MODERATION_STATUS_APPROVED,
                                                self.user, "Reason")

        self.assertEqual(self.profile.moderated_object.moderation_status,
                         MODERATION_STATUS_APPROVED)
        self.assertEqual(self.profile.moderated_object.moderated_by, self.user)
        self.assertEqual(self.profile.moderated_object.moderation_reason,
                         "Reason")

    def test_approve_moderated_object(self):
        """test if after object approval new data is saved."""
        self.profile.description = 'New description'

        moderated_object = ModeratedObject(content_object=self.profile)

        moderated_object.save()

        moderated_object.approve(moderated_by=self.user)

        user_profile = self.profile.__class__.objects.get(id=self.profile.id)

        self.assertEqual(user_profile.description, 'New description')

    def test_approve_moderated_object_new_model_instance(self):
        profile = self.profile.__class__(description='Profile for new user',
                                         url='http://www.test.com',
                                         user=self.user)

        profile.save()

        profile.moderated_object.approve(self.user)

        user_profile = self.profile.__class__.objects.get(
            url='http://www.test.com')

        self.assertEqual(user_profile.description, 'Profile for new user')

    def test_reject_moderated_object(self):
        self.profile.description = 'New description'
        self.profile.save()

        self.profile.moderated_object.reject(self.user)

        user_profile = self.profile.__class__.objects.get(id=self.profile.id)

        self.assertEqual(user_profile.description, "Old description")
        self.assertEqual(self.profile.moderated_object.moderation_status,
                         MODERATION_STATUS_REJECTED)

    def test_has_object_been_changed_should_be_true(self):
        self.profile.description = 'Old description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()
        moderated_object.approve(moderated_by=self.user)

        user_profile = self.profile.__class__.objects.get(id=self.profile.id)

        self.profile.description = 'New description'
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        value = moderated_object.has_object_been_changed(user_profile)

        self.assertEqual(value, True)

    def test_has_object_been_changed_should_be_false(self):
        moderated_object = ModeratedObject(content_object=self.profile)
        moderated_object.save()

        value = moderated_object.has_object_been_changed(self.profile)

        self.assertEqual(value, False)

########NEW FILE########
__FILENAME__ = moderator
import unittest

from django.test.testcases import TestCase
from tests.models import UserProfile,\
    ModelWithVisibilityField, ModelWithWrongVisibilityField
from moderation.moderator import GenericModerator
from moderation.managers import ModerationObjectsManager
from django.core import mail
from django.contrib.auth.models import User, Group
from moderation.models import ModeratedObject, MODERATION_STATUS_APPROVED
from moderation.message_backends import BaseMessageBackend
from django.db.models.manager import Manager
from tests.utils import setup_moderation, teardown_moderation


class GenericModeratorTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']
    urls = 'django-moderation.test_urls'

    def setUp(self):
        self.user = User.objects.get(username='admin')
        obj = ModeratedObject(content_object=self.user)
        obj.save()
        self.user.moderated_object = obj
        self.moderator = GenericModerator(UserProfile)

    def test_create_generic_moderator(self):
        self.assertEqual(self.moderator.model_class, UserProfile)
        self.assertEqual(self.moderator.manager_names, ['objects'])
        self.assertEqual(self.moderator.moderation_manager_class,
                         ModerationObjectsManager)
        self.assertEqual(self.moderator.auto_approve_for_staff, True)
        self.assertEqual(self.moderator.auto_approve_for_groups, None)
        self.assertEqual(self.moderator.auto_reject_for_groups, None)

    def test_subclass_moderator_class(self):

        class UserProfileModerator(GenericModerator):
            auto_approve_for_staff = False
            auto_approve_for_groups = ['admins', 'moderators']
            auto_reject_for_groups = ['others']

        moderator = UserProfileModerator(UserProfile)
        self.assertEqual(moderator.model_class, UserProfile)
        self.assertEqual(moderator.manager_names, ['objects'])
        self.assertEqual(moderator.moderation_manager_class,
                         ModerationObjectsManager)
        self.assertEqual(moderator.auto_approve_for_staff, False)
        self.assertEqual(moderator.auto_approve_for_groups, ['admins',
                                                             'moderators'])
        self.assertEqual(moderator.auto_reject_for_groups, ['others'])

    def test_custom_message_backend_class(self):
        class CustomMessageBackend(BaseMessageBackend):
            def send(self, **kwargs):
                pass  # silence is gold

        self.moderator.message_backend_class = CustomMessageBackend
        self.moderator.send(
            self.user,
            subject_template=('moderation/'
                              'notification_subject_moderator.txt'),
            message_template=('moderation/'
                              'notification_message_moderator.txt'),
            recipient_list=['test@example.com'])

        # because of the custom message backend
        self.assertEqual(len(mail.outbox), 0)

    def test_partial_custom_message_backend_class_raise_exception(self):
        class CustomMessageBackend(BaseMessageBackend):
            pass

        self.moderator.message_backend_class = CustomMessageBackend
        with self.assertRaises(NotImplementedError):
            self.moderator.send(
                self.user,
                subject_template=('moderation/'
                                  'notification_subject_moderator.txt'),
                message_template=('moderation'
                                  '/notification_message_moderator.txt'),
                recipient_list=['test@example.com'])

    def test_wrong_message_backend_class_raise_exception(self):
        class WrongMessageBackend(object):
            pass

        self.moderator.message_backend_class = WrongMessageBackend
        with self.assertRaises(TypeError):
            self.moderator.send(
                self.user,
                subject_template=('moderation/'
                                  'notification_subject_moderator.txt'),
                message_template=('moderation/'
                                  'notification_message_moderator.txt'),
                recipient_list=['test@example.com'])

    def test_send_notification(self):
        self.moderator.send(
            self.user,
            subject_template='moderation/notification_subject_moderator.txt',
            message_template='moderation/notification_message_moderator.txt',
            recipient_list=['test@example.com'])

        self.assertEqual(len(mail.outbox), 1)

    def test_inform_moderator(self):
        self.moderator = GenericModerator(UserProfile)
        self.moderator.inform_moderator(self.user)

        self.assertEqual(len(mail.outbox), 1)

    def test_inform_user(self):
        self.moderator = GenericModerator(UserProfile)
        self.moderator.inform_user(self.user, self.user)
        self.assertEqual(len(mail.outbox), 1)

    def test_moderator_should_have_field_exclude(self):
        self.assertTrue(hasattr(self.moderator, 'fields_exclude'))


class AutoModerateModeratorTestCase(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.user = User.objects.get(username='admin')
        self.moderator = GenericModerator(UserProfile)
        self.obj = object

    def test_is_auto_approve_user_superuser(self):
        self.moderator.auto_approve_for_superusers = True
        self.user.is_superuser = True
        reason = self.moderator.is_auto_approve(self.obj, self.user)
        self.assertTrue(reason)
        self.assertEqual(reason, 'Auto-approved: Superuser')

    def test_is_auto_approve_user_is_staff(self):
        self.moderator.auto_approve_for_staff = True
        self.user.is_superuser = False
        reason = self.moderator.is_auto_approve(self.obj, self.user)
        self.assertTrue(reason)
        self.assertEqual(reason, 'Auto-approved: Staff')

    def test_is_auto_approve_not_user_superuser(self):
        self.moderator.auto_approve_for_superusers = True
        self.moderator.auto_approve_for_staff = True
        self.user.is_superuser = False
        self.user.is_staff = False
        self.assertFalse(self.moderator.is_auto_approve(self.obj, self.user))

    def test_is_auto_approve_not_user_is_staff(self):
        self.moderator.auto_approve_for_staff = True
        self.user.is_staff = False
        self.user.is_superuser = False
        self.assertFalse(self.moderator.is_auto_approve(self.obj, self.user))

    def test_auto_approve_for_groups_user_in_group(self):
        self.moderator.auto_approve_for_superusers = False
        self.moderator.auto_approve_for_staff = False
        self.moderator.auto_approve_for_groups = ['moderators']
        group = Group(name='moderators')
        group.save()
        self.user.groups.add(group)
        self.user.save()
        reason = self.moderator.is_auto_approve(self.obj, self.user)
        self.assertTrue(reason)
        self.assertEqual(reason, 'Auto-approved: User in allowed group')

    def test_auto_approve_for_groups_user_not_in_group(self):
        self.moderator.auto_approve_for_superusers = False
        self.moderator.auto_approve_for_staff = False
        self.moderator.auto_approve_for_groups = ['banned']
        self.assertFalse(self.moderator.is_auto_approve(self.obj, self.user))

    def test_is_auto_reject_user_is_anonymous(self):
        from mock import Mock

        self.user.is_anonymous = Mock()
        self.user.is_anonymous.return_value = True
        reason = self.moderator.is_auto_reject(self.obj, self.user)
        self.assertTrue(reason)
        self.assertEqual(reason, u'Auto-rejected: Anonymous User')

    def test_is_auto_reject_user_is_not_anonymous(self):
        from mock import Mock

        self.user.is_anonymous = Mock()
        self.user.is_anonymous.return_value = False
        self.assertFalse(self.moderator.is_auto_reject(self.obj, self.user))

    def test_auto_reject_for_groups_user_in_group(self):
        self.moderator.auto_reject_for_groups = ['banned']
        group = Group(name='banned')
        group.save()
        self.user.groups.add(group)
        self.user.save()
        reason = self.moderator.is_auto_reject(self.obj, self.user)
        self.assertTrue(reason)
        self.assertEqual(reason, 'Auto-rejected: User in disallowed group')

    def test_auto_reject_for_groups_user_not_in_group(self):
        self.moderator.auto_reject_for_groups = ['banned']
        self.assertFalse(self.moderator.is_auto_reject(self.obj, self.user))

    def test_overwrite_automoderation_method(self):

        def akismet_spam_check(obj):
            return True

        class UserProfileModerator(GenericModerator):
            # Inside MyModelModerator, which is registered with MyModel

            def is_auto_reject(self, obj, user):
                # Auto reject spam
                if akismet_spam_check(obj):  # Check body of object for spam
                    # Body of object is spam, moderate
                    return self.reason('Auto rejected: SPAM')
                super(UserProfile, self).is_auto_reject(obj, user)

        moderator = UserProfileModerator(UserProfile)
        reason = moderator.is_auto_reject(self.obj, self.user)
        self.assertTrue(reason)
        self.assertEqual(reason, 'Auto rejected: SPAM')


class ByPassModerationTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):

        class UserProfileModerator(GenericModerator):
            bypass_moderation_after_approval = True

        self.moderation = setup_moderation([(UserProfile,
                                             UserProfileModerator)])

        self.user = User.objects.get(username='moderator')
        self.profile = UserProfile.objects.get(user__username='moderator')

    def tearDown(self):
        teardown_moderation()

    def test_bypass_moderation_after_approval(self):
        profile = UserProfile(description='Profile for new user',
                              url='http://www.test.com',
                              user=User.objects.get(username='user1'))
        profile.save()

        profile.moderated_object.approve(self.user)

        profile.description = 'New description'
        profile.save()

        self.assertEqual(profile.moderated_object.moderation_status,
                         MODERATION_STATUS_APPROVED)


class BaseManagerTestCase(unittest.TestCase):

    def setUp(self):
        from django.db import models

        self.moderator = GenericModerator(UserProfile)

        class CustomManager(models.Manager):
            pass

        class ModelClass(models.Model):
            pass

        self.custom_manager = CustomManager
        self.model_class = ModelClass

    def test_get_base_manager(self):
        self.model_class.add_to_class('objects', self.custom_manager())

        base_manager = self.moderator._get_base_manager(self.model_class,
                                                        'objects')

        self.assertEqual(base_manager, self.custom_manager)

        delattr(self.model_class, 'objects')

    def test_get_base_manager_default_manager(self):
        base_manager = self.moderator._get_base_manager(self.model_class,
                                                        'objects')
        self.assertEqual(base_manager, Manager)


class VisibilityColumnTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):

        class UserProfileModerator(GenericModerator):
            visibility_column = 'is_public'

        self.moderation = setup_moderation([(ModelWithVisibilityField,
                                             UserProfileModerator)])

        self.user = User.objects.get(username='moderator')

    def tearDown(self):
        teardown_moderation()

    def _create_userprofile(self):
        profile = ModelWithVisibilityField(test='Profile for new user')
        profile.save()
        return profile

    def test_exclude_of_not_is_public_object(self):
        '''Verify new object with visibility column is accessible by manager'''
        self._create_userprofile()

        objects = ModelWithVisibilityField.objects.all()

        self.assertEqual(list(objects), [])

    def test_approved_obj_should_be_return_by_manager(self):
        '''Verify new object with visibility column is accessible '''\
            '''by manager after approve'''
        profile = self._create_userprofile()
        profile.moderated_object.approve(self.user)

        objects = ModelWithVisibilityField.objects.all()

        self.assertEqual(objects.count(), 1)

    def test_invalid_visibility_column_field_should_rise_exception(self):
        '''Verify correct exception is raised when model has '''\
            '''invalid visibility column'''

        class UserProfileModerator(GenericModerator):
            visibility_column = 'is_public'

        self.assertRaises(AttributeError,
                          self.moderation.register,
                          ModelWithWrongVisibilityField,
                          UserProfileModerator)

    def test_model_should_be_saved_properly(self):
        '''Verify that after approve of object that has visibility column '''\
            '''value is changed from False to True'''
        profile = self._create_userprofile()

        self.assertEqual(profile.is_public, False)

        profile.moderated_object.approve(self.user)

        self.assertEqual(
            ModelWithVisibilityField.unmoderated_objects.get().is_public,
            True)

########NEW FILE########
__FILENAME__ = register
from django.contrib.auth.models import User
from django.core import management
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.manager import Manager
from django.test.testcases import TestCase

from moderation.register import ModerationManager, RegistrationError
from moderation.moderator import GenericModerator
from moderation.managers import ModerationObjectsManager
from moderation.models import ModeratedObject, MODERATION_STATUS_APPROVED
from moderation.signals import pre_moderation, post_moderation
from tests.models import UserProfile, \
    ModelWithSlugField, ModelWithSlugField2, ModelWithMultipleManagers
from tests.utils import setup_moderation
from tests.utils import teardown_moderation
from moderation.helpers import import_moderator
from tests.models import Book

from django.db import IntegrityError


class RegistrationTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.moderation = setup_moderation([UserProfile])
        self.user = User.objects.get(username='moderator')

    def tearDown(self):
        teardown_moderation()

    def test_get_moderator(self):
        moderator = self.moderation.get_moderator(UserProfile)

        self.assertTrue(isinstance(moderator, GenericModerator))

    def test_get_of_new_object_should_raise_exception(self):
        """Tests if after register of model class with moderation, 
           when new object is created and getting of object 
           raise ObjectDoesNotExist"""

        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        self.assertRaises(ObjectDoesNotExist, UserProfile.objects.get,
                          pk=profile.pk)

    def test_creation_of_moderated_object(self):
        """
        Test if after create of new object moderated object should be created
        """
        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        moderated_object = ModeratedObject.objects.get_for_instance(profile)

        self.assertEqual(unicode(moderated_object),
                         u"user1 - http://www.yahoo.com")

    def test_get_of_existing_object_should_return_old_version_of_object(self):
        """Tests if after register of model class with moderation, 
            when existing object is saved, when getting of object returns 
            old version of object"""
        profile = UserProfile.objects.get(user__username='moderator')
        moderated_object = ModeratedObject(content_object=profile)
        moderated_object.save()
        moderated_object.approve(moderated_by=self.user)

        profile.description = "New description"
        profile.save()

        old_profile = UserProfile.objects.get(pk=profile.pk)

        self.assertEqual(old_profile.description, u'Old description')

    def test_register(self):
        """Tests if after creation of new model instance new 
        moderation object is created"""
        UserProfile(description='Profile for new user',
                    url='http://www.yahoo.com',
                    user=User.objects.get(username='user1')).save()

        self.assertEqual(ModeratedObject.objects.all().count(),
                         1,
                         "New moderation object was not created"
                         " after creation of new model instance "
                         "from model class that is registered with moderation")

    def test_exception_is_raised_when_class_is_registered(self):
        self.assertRaises(RegistrationError, self.moderation.register,
                          UserProfile)

    def test_custom_moderator_should_be_registered_with_moderation(self):
        from moderation.moderator import GenericModerator
        from django.db import models

        class MyModel(models.Model):
            pass

        class MyModelModerator(GenericModerator):
            pass

        self.moderation.register(MyModel, MyModelModerator)

        moderator_instance = self.moderation._registered_models[MyModel]

        self.assertTrue(isinstance(moderator_instance, MyModelModerator))


class AutoDiscoverTestCase(TestCase):
    urls = 'tests.urls.auto_register'

    def setUp(self):
        self.moderation = setup_moderation()

    def tearDown(self):
        teardown_moderation()

    def test_models_should_be_registered_if_moderator_in_module(self):
        module = import_moderator('tests')

        try:  # force module reload
            reload(module)
        except:
            pass

        self.assertTrue(Book in self.moderation._registered_models)
        self.assertEqual(module.__name__,
                         'tests.moderator')


class RegisterMultipleManagersTestCase(TestCase):

    def setUp(self):
        self.moderation = ModerationManager()

        class ModelWithMultipleManagersModerator(GenericModerator):
            manager_names = ['objects', 'men', 'women']

        setup_moderation([(ModelWithMultipleManagers,
                           ModelWithMultipleManagersModerator)])

    def tearDown(self):
        teardown_moderation()

    def test_multiple_managers(self):
        obj = ModelWithMultipleManagers(gender=0)
        obj.save()

        obj2 = ModelWithMultipleManagers(gender=1)
        obj2.save()

        men = ModelWithMultipleManagers.men.all()
        women = ModelWithMultipleManagers.women.all()

        self.assertEqual(men.count(), 0)
        self.assertEqual(women.count(), 0)


class IntegrityErrorTestCase(TestCase):

    def setUp(self):
        self.moderation = setup_moderation([ModelWithSlugField])

    def tearDown(self):
        teardown_moderation()

    def test_raise_integrity_error_model_registered_with_moderation(self):
        m1 = ModelWithSlugField(slug='test')
        m1.save()

        self.assertRaises(ObjectDoesNotExist, ModelWithSlugField.objects.get,
                          slug='test')

        m2 = ModelWithSlugField(slug='test')
        self.assertRaises(IntegrityError, m2.save)

        self.assertEqual(ModeratedObject.objects.all().count(), 1)

    def test_raise_integrity_error_model_not_registered_with_moderation(self):
        m1 = ModelWithSlugField2(slug='test')
        m1.save()

        m1 = ModelWithSlugField2.objects.get(slug='test')

        m2 = ModelWithSlugField2(slug='test')
        self.assertRaises(IntegrityError, m2.save)

        self.assertEqual(ModeratedObject.objects.all().count(), 0)


class IntegrityErrorRegressionTestCase(TestCase):

    def setUp(self):
        self.moderation = ModerationManager()
        self.moderation.register(ModelWithSlugField)
        self.filter_moderated_objects = ModelWithSlugField.objects.\
            filter_moderated_objects

        def filter_moderated_objects(query_set):
            from moderation.models import MODERATION_STATUS_PENDING,\
                MODERATION_STATUS_REJECTED

            exclude_pks = []
            for obj in query_set:
                try:
                    if obj.moderated_object.moderation_status\
                       in [MODERATION_STATUS_PENDING,
                           MODERATION_STATUS_REJECTED]\
                       and obj.__dict__ == \
                       obj.moderated_object.changed_object.__dict__:
                        exclude_pks.append(object.pk)
                except ObjectDoesNotExist:
                    pass

            return query_set.exclude(pk__in=exclude_pks)

        setattr(ModelWithSlugField.objects,
                'filter_moderated_objects',
                filter_moderated_objects)

    def tearDown(self):
        self.moderation.unregister(ModelWithSlugField)

    def test_old_version_of_filter_moderated_objects_method(self):
        m1 = ModelWithSlugField(slug='test')
        m1.save()

        m2 = ModelWithSlugField(slug='test')
        self.assertRaises(IntegrityError, m2.save)

        self.assertEqual(ModeratedObject.objects.all().count(), 1)


class ModerationManagerTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):
        self.moderation = setup_moderation()
        self.user = User.objects.get(username='moderator')

    def tearDown(self):
        teardown_moderation()

    def test_unregister(self):
        """Tests if model class is successfully unregistered from moderation"""
        from django.db.models import signals

        old_pre_save_receivers = [r for r in signals.pre_save.receivers]
        old_post_save_receivers = [r for r in signals.post_save.receivers]

        signals.pre_save.receivers = []
        signals.post_save.receivers = []
        self.moderation.register(UserProfile)

        self.assertNotEqual(signals.pre_save.receivers, [])
        self.assertNotEqual(signals.post_save.receivers, [])

        UserProfile(description='Profile for new user',
                    url='http://www.yahoo.com',
                    user=User.objects.get(username='user1')).save()

        self.moderation.unregister(UserProfile)

        self.assertEqual(signals.pre_save.receivers, [])
        self.assertEqual(signals.post_save.receivers, [])

        self.assertEqual(UserProfile.objects.__class__, Manager)
        self.assertEqual(hasattr(UserProfile, 'moderated_object'), False)

        signals.pre_save.receivers = old_pre_save_receivers
        signals.post_save.receivers = old_post_save_receivers

        UserProfile.objects.get(user__username='user1')

        User.objects.get(username='moderator')
        management.call_command('loaddata', 'test_moderation.json',
                                verbosity=0)

    def test_moderation_manager(self):
        moderation = ModerationManager()

        self.assertEqual(moderation._registered_models, {})

    def test_save_new_instance_after_add_and_remove_fields_from_class(self):
        """Test if after removing moderation from model class new 
        instance of model can be created"""

        class CustomManager(Manager):
            pass

        moderator = GenericModerator(UserProfile)
        self.moderation._and_fields_to_model_class(moderator)

        self.moderation._remove_fields(moderator)

        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        up = UserProfile._default_manager.filter(url='http://www.yahoo.com')
        self.assertEqual(up.count(), 1)

    def test_and_fields_to_model_class(self):

        class CustomManager(Manager):
            pass

        moderator = GenericModerator(UserProfile)
        self.moderation._and_fields_to_model_class(moderator)

        manager = ModerationObjectsManager()(CustomManager)()

        self.assertEqual(repr(UserProfile.objects.__class__),
                         repr(manager.__class__))
        self.assertEqual(hasattr(UserProfile, 'moderated_object'), True)

        # clean up
        self.moderation._remove_fields(moderator)

    def test_get_or_create_moderated_object_exist(self):
        self.moderation.register(UserProfile)
        profile = UserProfile.objects.get(user__username='moderator')

        moderator = self.moderation.get_moderator(UserProfile)

        ModeratedObject(content_object=profile).save()

        profile.description = "New description"

        unchanged_obj = self.moderation._get_unchanged_object(profile)
        object = self.moderation._get_or_create_moderated_object(profile,
                                                                 unchanged_obj,
                                                                 moderator)

        self.assertNotEqual(object.pk, None)
        self.assertEqual(object.changed_object.description,
                         u'Old description')

        self.moderation.unregister(UserProfile)

    def test_get_or_create_moderated_object_does_not_exist(self):
        profile = UserProfile.objects.get(user__username='moderator')
        profile.description = "New description"

        self.moderation.register(UserProfile)
        moderator = self.moderation.get_moderator(UserProfile)

        unchanged_obj = self.moderation._get_unchanged_object(profile)

        object = self.moderation._get_or_create_moderated_object(profile,
                                                                 unchanged_obj,
                                                                 moderator)

        self.assertEqual(object.pk, None)
        self.assertEqual(object.changed_object.description,
                         u'Old description')

        self.moderation.unregister(UserProfile)

    def test_get_unchanged_object(self):
        profile = UserProfile.objects.get(user__username='moderator')
        profile.description = "New description"

        object = self.moderation._get_unchanged_object(profile)

        self.assertEqual(object.description,
                         u'Old description')


class LoadingFixturesTestCase(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.new_moderation = setup_moderation([UserProfile])
        self.user = User.objects.get(username='moderator')

    def tearDown(self):
        teardown_moderation()

    def test_loading_fixture_for_moderated_model(self):
        management.call_command('loaddata', 'test_moderation.json',
                                verbosity=0)

        self.assertEqual(UserProfile.objects.all().count(), 1)

    def test_loading_objs_from_fixture_should_not_create_moderated_obj(self):
        management.call_command('loaddata', 'test_moderation.json',
                                verbosity=0)

        profile = UserProfile.objects.get(user__username='moderator')

        self.assertRaises(ObjectDoesNotExist,
                          ModeratedObject.objects.get, object_pk=profile.pk)

    def test_moderated_object_is_created_when_not_loaded_from_fixture(self):
        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        moderated_objs = ModeratedObject.objects.filter(object_pk=profile.pk)
        self.assertEqual(moderated_objs.count(), 1)


class ModerationSignalsTestCase(TestCase):
    fixtures = ['test_users.json', 'test_moderation.json']

    def setUp(self):

        class UserProfileModerator(GenericModerator):

            notify_moderator = False

        self.moderation = setup_moderation(
            [(UserProfile, UserProfileModerator)])

        self.moderation._disconnect_signals(UserProfile)

        self.user = User.objects.get(username='moderator')
        self.profile = UserProfile.objects.get(user__username='moderator')

    def tearDown(self):
        teardown_moderation()

    def test_send_pre_moderation_signal(self):
        """check if custom_approve_handler function was called when """
        """moderation_approve signal was send"""

        def custom_pre_moderation_handler(sender, instance, status, **kwargs):
            # do some stuff with approved instance
            instance.description = 'Change description'
            instance.save()

        pre_moderation.connect(custom_pre_moderation_handler,
                               sender=UserProfile)

        pre_moderation.send(sender=UserProfile, instance=self.profile,
                            status=MODERATION_STATUS_APPROVED)

        self.assertEqual(self.profile.description, 'Change description')

    def test_send_post_moderation_signal(self):
        """check if custom_approve_handler function was called when """
        """moderation_approve signal was send"""

        def custom_post_moderation_handler(sender, instance, status, **kwargs):
            # do some stuff with approved instance
            instance.description = 'Change description'
            instance.save()

        post_moderation.connect(custom_post_moderation_handler,
                                sender=UserProfile)

        post_moderation.send(sender=UserProfile, instance=self.profile,
                             status=MODERATION_STATUS_APPROVED)

        self.assertEqual(self.profile.description, 'Change description')

    def test_connect_and_disconnect_signals(self):
        from django.db.models import signals

        old_pre_save_receivers = [r for r in signals.pre_save.receivers]
        old_post_save_receivers = [r for r in signals.post_save.receivers]

        signals.pre_save.receivers = []
        signals.post_save.receivers = []

        self.moderation._connect_signals(UserProfile)

        self.assertNotEqual(signals.pre_save.receivers, [])
        self.assertNotEqual(signals.post_save.receivers, [])

        self.moderation._disconnect_signals(UserProfile)

        self.assertEqual(signals.pre_save.receivers, [])
        self.assertEqual(signals.post_save.receivers, [])

        signals.pre_save.receivers = old_pre_save_receivers
        signals.post_save.receivers = old_post_save_receivers

    def test_after_disconnecting_signals_moderation_object(self):
        self.moderation._connect_signals(UserProfile)
        self.moderation._disconnect_signals(UserProfile)

        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        self.assertRaises(ObjectDoesNotExist, ModeratedObject.objects.get,
                          object_pk=profile.pk)

    def test_post_save_handler_for_existing_object(self):
        from django.db.models import signals

        signals.pre_save.connect(self.moderation.pre_save_handler,
                                 sender=UserProfile)
        signals.post_save.connect(self.moderation.post_save_handler,
                                  sender=UserProfile)
        profile = UserProfile.objects.get(user__username='moderator')
        moderated_object = ModeratedObject(content_object=profile)
        moderated_object.save()
        moderated_object.approve(moderated_by=self.user)

        profile.description = 'New description of user profile'
        profile.save()

        moderated_object = ModeratedObject.objects.get_for_instance(profile)

        original_object = moderated_object.changed_object
        self.assertEqual(original_object.description,
                         'New description of user profile')
        self.assertEqual(UserProfile.objects.get(pk=profile.pk).description,
                         u'Old description')

        signals.pre_save.disconnect(self.moderation.pre_save_handler,
                                    UserProfile)
        signals.post_save.disconnect(self.moderation.post_save_handler,
                                     UserProfile)

    def test_pre_save_handler_for_existing_object(self):
        from django.db.models import signals

        signals.pre_save.connect(self.moderation.pre_save_handler,
                                 sender=UserProfile)

        profile = UserProfile.objects.get(user__username='moderator')

        profile.description = 'New description of user profile'
        profile.save()

        moderated_object = ModeratedObject.objects.get_for_instance(profile)

        original_object = moderated_object.changed_object
        content_object = moderated_object.content_object

        self.assertEqual(original_object.description,
                         u'Old description')
        self.assertEqual(content_object.description,
                         'New description of user profile')

        signals.pre_save.disconnect(self.moderation.pre_save_handler,
                                    UserProfile)

    def test_post_save_handler_for_new_object(self):
        from django.db.models import signals

        signals.pre_save.connect(self.moderation.pre_save_handler,
                                 sender=UserProfile)
        signals.post_save.connect(self.moderation.post_save_handler,
                                  sender=UserProfile)
        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        moderated_object = ModeratedObject.objects.get_for_instance(profile)

        self.assertEqual(moderated_object.content_object, profile)

        signals.pre_save.disconnect(self.moderation.pre_save_handler,
                                    UserProfile)
        signals.post_save.disconnect(self.moderation.post_save_handler,
                                     UserProfile)

    def test_pre_save_handler_for_new_object(self):
        from django.db.models import signals

        signals.pre_save.connect(self.moderation.pre_save_handler,
                                 sender=UserProfile)
        profile = UserProfile(description='Profile for new user',
                              url='http://www.yahoo.com',
                              user=User.objects.get(username='user1'))

        profile.save()

        self.assertRaises(ObjectDoesNotExist,
                          ModeratedObject.objects.get_for_instance,
                          profile)

        signals.pre_save.disconnect(self.moderation.pre_save_handler,
                                    UserProfile)

########NEW FILE########
__FILENAME__ = auto_discover
from django.conf.urls.defaults import patterns, include, handler500
from django.conf import settings
from django.contrib import admin
from moderation.helpers import auto_discover

admin.autodiscover()
auto_discover()

handler500

urlpatterns = patterns(
    '',
    (r'^admin/', include(admin.site.urls)),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}),
)

########NEW FILE########
__FILENAME__ = default
from django.conf.urls.defaults import patterns, include, handler500
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

handler500

urlpatterns = patterns(
    '',
    (r'^admin/', include(admin.site.urls)),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}),
)

########NEW FILE########
__FILENAME__ = request_factory
"""
RequestFactory mock class,
snippet taken from http://www.djangosnippets.org/snippets/963/
"""
from cStringIO import StringIO
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest


class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.

    Usage:

    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})

    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client

    Once you have a request object you can pass it to any view function, 
    just as if that view had been hooked up using a URLconf.

    """

    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': StringIO(),
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)

########NEW FILE########
__FILENAME__ = testcases
from django_webtest import WebTest


class WebTestCase(WebTest):

    def setUp(self):
        self.user = None

    def get(self, url, **kwargs):
        kwargs.setdefault('user', self.user)
        return self.app.get(url, **kwargs)

    def post(self, url, **kwargs):
        kwargs.setdefault('user', self.user)
        return self.app.post(url, **kwargs)

########NEW FILE########
