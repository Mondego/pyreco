__FILENAME__ = actions
"""
Built-in, globally-available admin actions.
"""

from django import template
from django.core.exceptions import PermissionDenied
from django.contrib.admin import helpers
from django.contrib.admin.util import get_deleted_objects, model_ngettext
from django.db import router
from django.shortcuts import render_to_response
try:
    from django.utils.encoding import force_text as force_unicode
except ImportError:
    from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy, ugettext as _
from django.db import models

from django.contrib.admin.actions import delete_selected as django_delete_selected

def delete_selected(modeladmin, request, queryset):
    if issubclass(modeladmin.model, models.Model):
        return django_delete_selected(modeladmin, request, queryset)
    else:
        return _delete_selected(modeladmin, request, queryset)

def _delete_selected(modeladmin, request, queryset):
    """
    Default action which deletes the selected objects.

    This action first displays a confirmation page whichs shows all the
    deleteable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it delets all selected objects and redirects back to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Check that the user has delete permission for the actual model
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    using = router.db_for_write(modeladmin.model)

    # Populate deletable_objects, a data structure of all related objects that
    # will also be deleted.
    # TODO: Permissions would be so cool...
    deletable_objects, perms_needed, protected = get_deleted_objects(
        queryset, opts, request.user, modeladmin.admin_site, using)

    # The user has already confirmed the deletion.
    # Do the deletion and return a None to display the change list view again.
    if request.POST.get('post'):
        if perms_needed:
            raise PermissionDenied
        n = len(queryset)
        if n:
            for obj in queryset:
                obj_display = force_unicode(obj)
                modeladmin.log_deletion(request, obj, obj_display)
                # call the objects delete method to ensure signals are
                # processed.
                obj.delete()
            # This is what you get if you have to monkey patch every object in a changelist
            # No queryset object, I can tell ya. So we get a new one and delete that. 
            #pk_list = [o.pk for o in queryset]
            #klass = queryset[0].__class__
            #qs = klass.objects.filter(pk__in=pk_list)
            #qs.delete()
            modeladmin.message_user(request, _("Successfully deleted %(count)d %(items)s.") % {
                "count": n, "items": model_ngettext(modeladmin.opts, n)
            })
        # Return None to display the change list page again.
        return None

    if len(queryset) == 1:
        objects_name = force_unicode(opts.verbose_name)
    else:
        objects_name = force_unicode(opts.verbose_name_plural)

    if perms_needed or protected:
        title = _("Cannot delete %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = {
        "title": title,
        "objects_name": objects_name,
        "deletable_objects": [deletable_objects],
        'queryset': queryset,
        "perms_lacking": perms_needed,
        "protected": protected,
        "opts": opts,
        "root_path": modeladmin.admin_site.root_path,
        "app_label": app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }
    
    # Display the confirmation page
    return render_to_response(modeladmin.delete_selected_confirmation_template or [
        "admin/%s/%s/delete_selected_confirmation.html" % (app_label, opts.object_name.lower()),
        "admin/%s/delete_selected_confirmation.html" % app_label,
        "admin/delete_selected_confirmation.html"
    ], context, context_instance=template.RequestContext(request))

delete_selected.short_description = ugettext_lazy("Delete selected %(verbose_name_plural)s")

########NEW FILE########
__FILENAME__ = admin
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.admin import csrf_protect_m
try:
    from django.contrib.auth.admin import sensitive_post_parameters_m
except ImportError:
    from django.utils.decorators import method_decorator
    from django.views.decorators.debug import sensitive_post_parameters
    sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())    
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.http import HttpResponseRedirect, Http404
from django.contrib import admin
from django.utils.html import escape
from django.template.response import TemplateResponse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from mongoengine.django.auth import User
from mongoengine import DoesNotExist
from mongoengine.django.mongo_auth.models import MongoUser

from mongoadmin import site, DocumentAdmin

from .forms import UserCreationForm, UserChangeForm

class MongoUserAdmin(DocumentAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
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
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ()
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    filter_horizontal = ()
    
    def get_user_or_404(self, request, id):
        qs = self.queryset(request)
        try:
            user = qs.filter(pk=id)[0]
        except (IndexError, DoesNotExist):
            raise Http404
        return user

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(MongoUserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super(MongoUserAdmin, self).get_form(request, obj, **defaults)

    def get_urls(self):
        from django.conf.urls import patterns
        return patterns('',
            (r'^([0-9a-f]{24})/password/$',
             self.admin_site.admin_view(self.user_change_password))
        ) + super(MongoUserAdmin, self).get_urls()

    def lookup_allowed(self, lookup, value):
        # See #20078: we don't want to allow any lookups involving passwords.
        if lookup.startswith('password'):
            return False
        return super(MongoUserAdmin, self).lookup_allowed(lookup, value)

    @sensitive_post_parameters_m
    @csrf_protect_m
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
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    'order to add users, Django requires that your user '
                    'account have both the "Add user" and "Change user" '
                    'permissions set.')
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': username_field.help_text,
        }
        extra_context.update(defaults)
        return super(MongoUserAdmin, self).add_view(request, form_url,
                                               extra_context)

    @sensitive_post_parameters_m
    def user_change_password(self, request, id, form_url=''):
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = self.get_user_or_404(request, id)
        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                msg = ugettext('Password changed successfully.')
                messages.success(request, msg)
                return HttpResponseRedirect('..')
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(getattr(user, user.USERNAME_FIELD)),#user.get_username()),
            'adminForm': adminForm,
            'form_url': form_url,
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
        }
        return TemplateResponse(request,
            self.change_user_password_template or
            'admin/auth/user/change_password.html',
            context, current_app=self.admin_site.name)

    def response_add(self, request, obj, post_url_continue=None):
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
        return super(MongoUserAdmin, self).response_add(request, obj,
                                                   post_url_continue)

if MongoUser == get_user_model() and \
        getattr(settings, 'MONGOENGINE_USER_DOCUMENT', '') == 'mongoengine.django.auth.User':
    site.register(User, MongoUserAdmin)

########NEW FILE########
__FILENAME__ = forms
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from mongoengine.django.auth import User

from mongodbforms import DocumentForm

class UserCreationForm(DocumentForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'password_mismatch': _("The two password fields didn't match."),
    }
    username = forms.RegexField(label=_("Username"), max_length=30,
        regex=r'^[\w.@+-]+$',
        help_text=_("Required. 30 characters or fewer. Letters, digits and "
                      "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters.")})
    password1 = forms.CharField(label=_("Password"),
        widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."))

    class Meta:
        model = User
        fields = ("username",)

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        self.instance = user.set_password(self.cleaned_data["password1"])
        return self.instance
        
        
class UserChangeForm(DocumentForm):
    username = forms.RegexField(
        label=_("Username"), max_length=30, regex=r"^[\w.@+-]+$",
        help_text=_("Required. 30 characters or fewer. Letters, digits and "
                      "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters.")})
    password = ReadOnlyPasswordHashField(label=_("Password"),
        help_text=_("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>."))

    class Meta:
        model = User

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
        
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email == '':
            return None
        return email

########NEW FILE########
__FILENAME__ = models
from .utils import has_rel_db, get_model_or_document

if has_rel_db():
    from django.contrib.contenttypes.models import ContentType, ContentTypeManager
else:
    from django.contrib.contenttypes.models import ContentTypeManager as DjangoContentTypeManager
    
    from mongoengine.queryset import QuerySet
    from mongoengine.django.auth import ContentType
    
    from mongodbforms import init_document_options
    from mongodbforms.documentoptions import patch_document
    
    
    class ContentTypeManager(DjangoContentTypeManager):
        def get_query_set(self):
            """Returns a new QuerySet object.  Subclasses can override this method
            to easily customize the behavior of the Manager.
            """
            return QuerySet(self.model, self.model._get_collection())
            
        def contribute_to_class(self, model, name):
            init_document_options(model)
            super(ContentTypeManager, self).contribute_to_class(model, name)
            
    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.model_class().objects.get(**kwargs)
        
    def model_class(self):
        return get_model_or_document(str(self.app_label), str(self.model))
    
    patch_document(get_object_for_this_type, ContentType, bound=False)
    patch_document(model_class, ContentType, bound=False)
    
    manager = ContentTypeManager()
    manager.contribute_to_class(ContentType, 'objects')
    
    try:
        from grappelli.templatetags import grp_tags
        grp_tags.ContentType = ContentType
    except ImportError:
        pass
    
    
    
    
    
########NEW FILE########
__FILENAME__ = utils
import sys

from django.conf import settings
from django.db.models import get_model

from mongoengine.base.common import _document_registry

# if there is a relational db and we can load a content type
# object from it, we simply export Django's stuff and are done.
# Otherwise we roll our own (mostly) compatible version 
# using mongoengine.

def has_rel_db():
    if not getattr(settings, 'MONGOADMIN_CHECK_CONTENTTYPE', True):
        return True
    
    engine = settings.DATABASES.get('default', {}).get('ENGINE', 'django.db.backends.dummy')
    if engine.endswith('dummy'):
        return False
    return True
    
def get_model_or_document(app_label, model):
    if has_rel_db():
        return get_model(app_label, model, only_installed=False)
    else:
        # mongoengine's document registry is case sensitive
        # while all models are stored in lowercase in the
        # content types. So we can't use get_document.
        model = str(model).lower()
        possible_docs = [v for k, v in _document_registry.items() if k.lower() == model]
        if len(possible_docs) == 1:
            return possible_docs[0]
        if len(possible_docs) > 1:
            for doc in possible_docs:
                module = sys.modules[doc.__module__]
                doc_app_label = module.__name__.split('.')[-2]
                if doc_app_label.lower() == app_label.lower():
                    return doc
        return None
########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django import http
from django.contrib.sites.models import Site, get_current_site
from django.utils.translation import ugettext as _

from mongoadmin.contenttypes.models import ContentType

def shortcut(request, content_type_id, object_id):
    """
    Redirect to an object's page based on a content-type ID and an object ID.
    """
    # Look up the object, making sure it's got a get_absolute_url() function.
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
    except (ContentType.DoesNotExist, ValueError):
        raise http.Http404(_("Content type %(ct_id)s object %(obj_id)s doesn't exist") %
                           {'ct_id': content_type_id, 'obj_id': object_id})
    
    if not content_type.model_class():
        raise http.Http404(_("Content type %(ct_id)s object has no associated model") %
                               {'ct_id': content_type_id})
    try:
        obj = content_type.get_object_for_this_type(pk=object_id)
    except (content_type.model_class().DoesNotExist, ValueError):
        raise http.Http404(_("Content type %(ct_id)s object %(obj_id)s doesn't exist") %
                           {'ct_id': content_type_id, 'obj_id': object_id})

    try:
        get_absolute_url = obj.get_absolute_url
    except AttributeError:
        raise http.Http404(_("%(ct_name)s objects don't have a get_absolute_url() method") %
                           {'ct_name': content_type.name})
    absurl = get_absolute_url()

    # Try to figure out the object's domain, so we can do a cross-site redirect
    # if necessary.

    # If the object actually defines a domain, we're done.
    if absurl.startswith('http://') or absurl.startswith('https://'):
        return http.HttpResponseRedirect(absurl)

    # Otherwise, we need to introspect the object's relationships for a
    # relation to the Site object
    object_domain = None

    if Site._meta.installed:
        opts = obj._meta

        # First, look for an many-to-many relationship to Site.
        for field in opts.many_to_many:
            if field.rel.to is Site:
                try:
                    # Caveat: In the case of multiple related Sites, this just
                    # selects the *first* one, which is arbitrary.
                    object_domain = getattr(obj, field.name).all()[0].domain
                except IndexError:
                    pass
                if object_domain is not None:
                    break

        # Next, look for a many-to-one relationship to Site.
        if object_domain is None:
            for field in obj._meta.fields:
                if field.rel and field.rel.to is Site:
                    try:
                        object_domain = getattr(obj, field.name).domain
                    except Site.DoesNotExist:
                        pass
                    if object_domain is not None:
                        break

    # Fall back to the current site (if possible).
    if object_domain is None:
        try:
            object_domain = get_current_site(request).domain
        except Site.DoesNotExist:
            pass

    # If all that malarkey found an object domain, use it. Otherwise, fall back
    # to whatever get_absolute_url() returned.
    if object_domain is not None:
        protocol = 'https' if request.is_secure() else 'http'
        return http.HttpResponseRedirect('%s://%s%s'
                                         % (protocol, object_domain, absurl))
    else:
        return http.HttpResponseRedirect(absurl)
########NEW FILE########
__FILENAME__ = mongohelpers
from django.contrib.admin.helpers import InlineAdminForm as DjangoInlineAdminForm
from django.contrib.admin.helpers import InlineAdminFormSet as DjangoInlineAdminFormSet
from django.contrib.admin.helpers import AdminForm

class InlineAdminFormSet(DjangoInlineAdminFormSet):
    """
    A wrapper around an inline formset for use in the admin system.
    """
    def __iter__(self):
        for form, original in zip(self.formset.initial_forms, self.formset.get_queryset()):
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.opts.prepopulated_fields, original, self.readonly_fields,
                model_admin=self.opts)
        for form in self.formset.extra_forms:
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.opts.prepopulated_fields, None, self.readonly_fields,
                model_admin=self.opts)
        yield InlineAdminForm(self.formset, self.formset.empty_form,
            self.fieldsets, self.opts.prepopulated_fields, None,
            self.readonly_fields, model_admin=self.opts)



class InlineAdminForm(DjangoInlineAdminForm):
    """
    A wrapper around an inline form for use in the admin system.
    """
    def __init__(self, formset, form, fieldsets, prepopulated_fields, original,
      readonly_fields=None, model_admin=None):
        self.formset = formset
        self.model_admin = model_admin
        self.original = original
        self.show_url = original and hasattr(original, 'get_absolute_url')
        AdminForm.__init__(self, form, fieldsets, prepopulated_fields,
            readonly_fields, model_admin)
        
    def pk_field(self):
        # if there is no pk field then it's an embedded form so return none 
        if hasattr(self.formset, "_pk_field"):
            return super(InlineAdminForm, self).pk_field()
        else:
            return None



########NEW FILE########
__FILENAME__ = options
import collections
from functools import partial

from django import forms
from django.forms.models import modelform_defines_fields
from django.contrib.admin.options import ModelAdmin, InlineModelAdmin, get_ul_class
from django.contrib.admin import widgets
from django.contrib.admin.util import flatten_fieldsets
from django.core.exceptions import FieldError, ValidationError
from django.forms.formsets import DELETION_FIELD_NAME
from django.utils.translation import ugettext as _
from django.contrib.admin.util import NestedObjects
from django.utils.text import get_text_list

from mongoengine.fields import (DateTimeField, URLField, IntField, ListField, EmbeddedDocumentField,
                                ReferenceField, StringField, FileField, ImageField)

from mongodbforms.documents import documentform_factory, embeddedformset_factory, DocumentForm, EmbeddedDocumentFormSet, EmbeddedDocumentForm
from mongodbforms.util import load_field_generator, init_document_options

from mongoadmin.util import RelationWrapper, is_django_user_model
from mongoadmin.widgets import ReferenceRawIdWidget, MultiReferenceRawIdWidget

# Defaults for formfield_overrides. ModelAdmin subclasses can change this
# by adding to ModelAdmin.formfield_overrides.
FORMFIELD_FOR_DBFIELD_DEFAULTS = {
    DateTimeField: {
        'form_class': forms.SplitDateTimeField,
        'widget': widgets.AdminSplitDateTime
    },
    URLField:       {'widget': widgets.AdminURLFieldWidget},
    IntField:       {'widget': widgets.AdminIntegerFieldWidget},
    ImageField:     {'widget': widgets.AdminFileWidget},
    FileField:      {'widget': widgets.AdminFileWidget},
}

_fieldgenerator = load_field_generator()()

def formfield(field, form_class=None, **kwargs):
    """
    Returns a django.forms.Field instance for this database Field.
    """
    defaults = {'required': field.required, 'label': forms.forms.pretty_name(field.name)}
    if field.default is not None:
        if isinstance(field.default, collections.Callable):
            defaults['initial'] = field.default()
            defaults['show_hidden_initial'] = True
        else:
            defaults['initial'] = field.default

    if field.choices is not None:
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass
        # the values that TypedChoiceField will understand.
        for k in list(kwargs.keys()):
            if k not in ('coerce', 'empty_value', 'choices', 'required',
                         'widget', 'label', 'initial', 'help_text',
                         'error_messages', 'show_hidden_initial'):
                del kwargs[k]

    defaults.update(kwargs)

    if form_class is not None:
        return form_class(**defaults)
    return _fieldgenerator.generate(field, **defaults)


class MongoFormFieldMixin(object):
    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Hook for specifying the form Field instance for a given database Field
        instance.

        If kwargs are given, they're passed to the form Field's constructor.
        """
        request = kwargs.pop("request", None)

        # If the field specifies choices, we don't need to look for special
        # admin widgets - we just need to use a select widget of some kind.
        if db_field.choices is not None:
            return self.formfield_for_choice_field(db_field, request, **kwargs)

        if isinstance(db_field, ListField) and isinstance(db_field.field, ReferenceField):
            return self.formfield_for_reference_listfield(db_field, request, **kwargs)

        # handle RelatedFields
        if isinstance(db_field, ReferenceField):
            # For non-raw_id fields, wrap the widget with a wrapper that adds
            # extra HTML -- the "add other" interface -- to the end of the
            # rendered output. formfield can be None if it came from a
            # OneToOneField with parent_link=True or a M2M intermediary.
            form_field = self._get_formfield(db_field, **kwargs)
            if db_field.name not in self.raw_id_fields:
                related_modeladmin = self.admin_site._registry.get(db_field.document_type)
                can_add_related = bool(related_modeladmin and
                            related_modeladmin.has_add_permission(request))
                form_field.widget = widgets.RelatedFieldWidgetWrapper(
                            form_field.widget, RelationWrapper(db_field.document_type), self.admin_site,
                            can_add_related=can_add_related)
                return form_field
            elif db_field.name in self.raw_id_fields:
                kwargs['widget'] = ReferenceRawIdWidget(db_field.rel, self.admin_site)
                return self._get_formfield(db_field, **kwargs)

        if isinstance(db_field, StringField):
            if db_field.max_length is None:
                kwargs = dict({'widget': widgets.AdminTextareaWidget}, **kwargs)
            else:
                kwargs = dict({'widget': widgets.AdminTextInputWidget}, **kwargs)
            return self._get_formfield(db_field, **kwargs)

        # For any other type of field, just call its formfield() method.
        return self._get_formfield(db_field, **kwargs)

    def _get_formfield(self, db_field, **kwargs):
        """Return overridden formfield if exists, otherwise default formfield"""
        # If we've got overrides for the formfield defined, use 'em. **kwargs
        # passed to formfield_for_dbfield override the defaults.
        for klass in db_field.__class__.mro():
            if klass in self.formfield_overrides:
                kwargs.update(self.formfield_overrides[klass])
                break
        return formfield(db_field, **kwargs)

    def formfield_for_choice_field(self, db_field, request=None, **kwargs):
        """
        Get a form Field for a database Field that has declared choices.
        """
        # If the field is named as a radio_field, use a RadioSelect
        if db_field.name in self.radio_fields:
            # Avoid stomping on custom widget/choices arguments.
            if 'widget' not in kwargs:
                kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                    'class': get_ul_class(self.radio_fields[db_field.name]),
                })
            if 'choices' not in kwargs:
                kwargs['choices'] = db_field.get_choices(
                    include_blank = db_field.blank,
                    blank_choice=[('', _('None'))]
                )
        return formfield(db_field, **kwargs)


    def formfield_for_reference_listfield(self, db_field, request=None, **kwargs):
        """
        Get a form Field for a ManyToManyField.
        """
        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = MultiReferenceRawIdWidget(db_field.field.rel, self.admin_site)
            kwargs['help_text'] = ''
        elif db_field.name in (list(self.filter_vertical) + list(self.filter_horizontal)):
            kwargs['widget'] = widgets.FilteredSelectMultiple(forms.forms.pretty_name(db_field.name), (db_field.name in self.filter_vertical))

        return formfield(db_field, **kwargs)


class DocumentAdmin(MongoFormFieldMixin, ModelAdmin):
    change_list_template = "admin/change_document_list.html"
    form = DocumentForm

    _embedded_inlines = None

    def __init__(self, model, admin_site):
        super(DocumentAdmin, self).__init__(model, admin_site)

        self.inlines = self._find_embedded_inlines()

    def _find_embedded_inlines(self):
        emb_inlines = []
        exclude = self.exclude or []
        for name in self.model._fields_ordered:
            f = self.model._fields.get(name)
            if not (isinstance(f, ListField) and isinstance(getattr(f, 'field', None), EmbeddedDocumentField)) and not isinstance(f, EmbeddedDocumentField):
                continue
            # Should only reach here if there is an embedded document...
            if f.name in exclude:
                continue
            if hasattr(f, 'field') and f.field is not None:
                embedded_document = f.field.document_type
            elif hasattr(f, 'document_type'):
                embedded_document = f.document_type
            else:
                # For some reason we found an embedded field were either
                # the field attribute or the field's document type is None.
                # This shouldn't happen, but apparently does happen:
                # https://github.com/jschrewe/django-mongoadmin/issues/4
                # The solution for now is to ignore that field entirely.
                continue

            init_document_options(embedded_document)

            embedded_admin_base = EmbeddedStackedDocumentInline
            embedded_admin_name = "%sAdmin" % embedded_document.__class__.__name__
            inline_attrs = {
                'model': embedded_document,
                'parent_field_name': f.name,
            }
            # if f is an EmbeddedDocumentField set the maximum allowed form instances to one
            if isinstance(f, EmbeddedDocumentField):
                inline_attrs['max_num'] = 1
            embedded_admin = type(embedded_admin_name, (embedded_admin_base,), inline_attrs)
            # check if there is an admin for the embedded document in
            # self.inlines. If there is, use this, else use default.
            for inline_class in self.inlines:
                if inline_class.document == embedded_document:
                    embedded_admin = inline_class
            emb_inlines.append(embedded_admin)

            if f.name not in exclude:
                exclude.append(f.name)

        # sort out the declared inlines. Embedded admins take a different
        # set of arguments for init and are stored seperately. So the
        # embedded stuff has to be removed from self.inlines here
        inlines = [i for i in self.inlines if i not in emb_inlines]

        self.exclude = exclude

        return inlines + emb_inlines

    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model.objects.clone()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_changelist(self, request, **kwargs):
        """
        Returns the ChangeList class for use on the changelist page.
        """
        from mongoadmin.views import DocumentChangeList
        return DocumentChangeList

    def get_object(self, request, object_id):
        """
        Returns an instance matching the primary key provided. ``None``  is
        returned if no match is found (or the object_id failed validation
        against the primary key field).
        """
        queryset = self.get_queryset(request)
        model = queryset._document
        try:
            object_id = model._meta.pk.to_python(object_id)
            return queryset.get(pk=object_id)
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields(request, obj))
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # ModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        # if exclude is an empty list we pass None to be consistent with the
        # default on modelform_factory
        exclude = exclude or None
        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": partial(self.formfield_for_dbfield, request=request),
        }
        defaults.update(kwargs)

        if defaults['fields'] is None and not modelform_defines_fields(defaults['form']):
            defaults['fields'] = None

        print(defaults)
        try:
            return documentform_factory(self.model, **defaults)
        except FieldError as e:
            print(e.message)
            raise FieldError('%s. Check fields/fieldsets/exclude attributes of class %s.'
                             % (e, self.__class__.__name__))

    def save_related(self, request, form, formsets, change):
        """
        Given the ``HttpRequest``, the parent ``ModelForm`` instance, the
        list of inline formsets and a boolean value based on whether the
        parent is being added or changed, save the related objects to the
        database. Note that at this point save_form() and save_model() have
        already been called.
        """
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)

    def log_addition(self, request, object):
        """
        Log that an object has been successfully added.

        The default implementation creates an admin LogEntry object.
        """
        if not is_django_user_model(request.user):
            return

        super(DocumentAdmin, self).log_addition(request=request, object=object)


    def log_change(self, request, object, message):
        """
        Log that an object has been successfully changed.

        The default implementation creates an admin LogEntry object.
        """
        if not is_django_user_model(request.user):
            return

        super(DocumentAdmin, self).log_change(request=request, object=object, message=message)

    def log_deletion(self, request, object, object_repr):
        """
        Log that an object has been successfully changed.

        The default implementation creates an admin LogEntry object.
        """
        if not is_django_user_model(request.user):
            return

        super(DocumentAdmin, self).log_deletion(request=request, object=object, object_repr=object_repr)

class EmbeddedInlineAdmin(MongoFormFieldMixin, InlineModelAdmin):
    parent_field_name = None
    formset = EmbeddedDocumentFormSet
    form = EmbeddedDocumentForm

    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        return getattr(self.parent_model, self.parent_field_name, [])

    def get_formset(self, request, obj=None, **kwargs):
        """Returns a BaseInlineFormSet class for use in admin add/change views."""
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields(request, obj))
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # InlineModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        # if exclude is an empty list we use None, since that's the actual
        # default
        exclude = exclude or None
        can_delete = self.can_delete and self.has_delete_permission(request, obj)
        defaults = {
            "form": self.form,
            "formset": self.formset,
            "embedded_name": self.parent_field_name,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": partial(self.formfield_for_dbfield, request=request),
            "extra": self.get_extra(request, obj, **kwargs),
            "max_num": self.get_max_num(request, obj, **kwargs),
            "can_delete": can_delete,
        }

        defaults.update(kwargs)
        base_model_form = defaults['form']

        class DeleteProtectedModelForm(base_model_form):
            def hand_clean_DELETE(self):
                """
                We don't validate the 'DELETE' field itself because on
                templates it's not rendered using the field information, but
                just using a generic "deletion_field" of the InlineModelAdmin.
                """
                if self.cleaned_data.get(DELETION_FIELD_NAME, False):
                    collector = NestedObjects()
                    collector.collect([self.instance])
                    if collector.protected:
                        objs = []
                        for p in collector.protected:
                            objs.append(
                                # Translators: Model verbose name and instance representation, suitable to be an item in a list
                                _('%(class_name)s %(instance)s') % {
                                    'class_name': p._meta.verbose_name,
                                    'instance': p}
                            )
                        params = {'class_name': self._meta.model._meta.verbose_name,
                                  'instance': self.instance,
                                  'related_objects': get_text_list(objs, _('and'))}
                        msg = _("Deleting %(class_name)s %(instance)s would require "
                                "deleting the following protected related objects: "
                                "%(related_objects)s")
                        raise ValidationError(msg, code='deleting_protected', params=params)

            def is_valid(self):
                result = super(DeleteProtectedModelForm, self).is_valid()
                self.hand_clean_DELETE()
                return result

        defaults['form'] = DeleteProtectedModelForm

        if defaults['fields'] is None and not modelform_defines_fields(defaults['form']):
            defaults['fields'] = None

        return embeddedformset_factory(self.model, self.parent_model, **defaults)


class EmbeddedStackedDocumentInline(EmbeddedInlineAdmin):
    template = 'admin/edit_inline/stacked.html'


class EmbeddedTabularDocumentInline(EmbeddedInlineAdmin):
    template = 'admin/edit_inline/tabular.html'


########NEW FILE########
__FILENAME__ = sites
from django.contrib.admin import ModelAdmin
from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib.admin.sites import AdminSite, NotRegistered, AlreadyRegistered

from mongoengine.base import TopLevelDocumentMetaclass

from mongodbforms import init_document_options

from mongoadmin import DocumentAdmin

LOGIN_FORM_KEY = 'this_is_the_login_form'

class MongoAdminSite(AdminSite):
    """
    An AdminSite object encapsulates an instance of the Django admin application, ready
    to be hooked in to your URLconf. Models are registered with the AdminSite using the
    register() method, and the get_urls() method can then be used to access Django view
    functions that present a full admin interface for the collection of registered
    models.
    """
    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with the given admin class.

        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.

        If a model is abstract, this will raise ImproperlyConfigured.
        """
        if isinstance(model_or_iterable, ModelBase) and not admin_class:
            admin_class = ModelAdmin
            
        if isinstance(model_or_iterable, TopLevelDocumentMetaclass) and not admin_class:
            admin_class = DocumentAdmin

        # Don't import the humongous validation code unless required
        #if admin_class and settings.DEBUG:
        #    from mongoadmin.validation import validate
        #else:
        validate = lambda model, adminclass: None

        if isinstance(model_or_iterable, ModelBase) or \
                isinstance(model_or_iterable, TopLevelDocumentMetaclass):
            model_or_iterable = [model_or_iterable]

        for model in model_or_iterable:
            if isinstance(model, TopLevelDocumentMetaclass):
                init_document_options(model)
            
            if hasattr(model._meta, 'abstract') and model._meta.abstract:
                raise ImproperlyConfigured('The model %s is abstract, so it '
                      'cannot be registered with admin.' % model.__name__)

            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # Ignore the registration if the model has been
            # swapped out.
            if model._meta.swapped:
                continue

            # If we got **options then dynamically construct a subclass of
            # admin_class with those **options.
            if options:
                # For reasons I don't quite understand, without a __module__
                # the created class appears to "live" in the wrong place,
                # which causes issues later on.
                options['__module__'] = __name__
                admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)

            # Validate (which might be a no-op)
            validate(admin_class, model)

            # Instantiate the admin class to save in the registry
            self._registry[model] = admin_class(model, self)

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase) or \
                isinstance(model_or_iterable, TopLevelDocumentMetaclass):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]


# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = MongoAdminSite()

########NEW FILE########
__FILENAME__ = documenttags
from django.template import Library
from django.contrib.admin.templatetags.admin_list import (result_hidden_fields, ResultList, items_for_result,
                                                          result_headers)
from django.db.models.fields import FieldDoesNotExist

from mongodbforms.documentoptions import patch_document

register = Library()

def serializable_value(self, field_name):
    """
    Returns the value of the field name for this instance. If the field is
    a foreign key, returns the id value, instead of the object. If there's
    no Field object with this name on the model, the model attribute's
    value is returned directly.

    Used to serialize a field's value (in the serializer, or form output,
    for example). Normally, you would just access the attribute directly
    and not use this method.
    """
    try:
        field = self._meta.get_field_by_name(field_name)[0]
    except FieldDoesNotExist:
        return getattr(self, field_name)
    return getattr(self, field.name) 

def results(cl):
    """
    Just like the one from Django. Only we add a serializable_value method to
    the document, because Django expects it and mongoengine doesn't have it.
    """
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            patch_document(serializable_value, res)
            yield ResultList(form, items_for_result(cl, res, form))
    else:
        for res in cl.result_list:
            patch_document(serializable_value, res)
            yield ResultList(None, items_for_result(cl, res, None))

def document_result_list(cl):
    """
    Displays the headers and data list together
    """
    headers = list(result_headers(cl))
    try:
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1
    except KeyError:
        pass
    
    return {'cl': cl,
            'result_hidden_fields': list(result_hidden_fields(cl)),
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'results': list(results(cl))}
result_list = register.inclusion_tag("admin/change_list_results.html")(document_result_list)



########NEW FILE########
__FILENAME__ = mongoadmintags
from django import template
from django.conf import settings

register = template.Library()

class CheckGrappelli(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name
    def render(self, context):
        context[self.var_name] = 'grappelli' in settings.INSTALLED_APPS
        return ''

def check_grappelli(parser, token):
    """
    Checks weather grappelli is in installed apps and sets a variable in the context.
    Unfortunately there is no other way to find out if grappelli is used or not. 
    See: https://github.com/sehmaschine/django-grappelli/issues/32
    
    Usage: {% check_grappelli as <varname> %}
    """
    
    bits = token.contents.split()
    
    if len(bits) != 3:
        raise template.TemplateSyntaxError("'check_grappelli' tag takes exactly two arguments.")
    
    if bits[1] != 'as':
        raise template.TemplateSyntaxError("The second argument to 'check_grappelli' must be 'as'")
    varname = bits[2]
    
    return CheckGrappelli(varname)

register.tag(check_grappelli)

########NEW FILE########
__FILENAME__ = util
from django.utils.encoding import smart_str
try:
    from django.utils.encoding import force_text as force_unicode
except ImportError:
    from django.utils.encoding import force_unicode
try:
    from django.utils.encoding import smart_text as smart_unicode
except ImportError:
    try:
        from django.utils.encoding import smart_unicode
    except ImportError:
        from django.forms.util import smart_unicode
    
from django.forms.forms import pretty_name
from django.db.models.fields import FieldDoesNotExist
from django.utils import formats

from mongoengine import fields

from mongodbforms.util import init_document_options
import collections

class RelationWrapper(object):
    """
    Wraps a document referenced from a ReferenceField with an Interface similiar to
    django's ForeignKeyField.rel 
    """
    def __init__(self, document):
        self.to = init_document_options(document)
        
def is_django_user_model(user):
    """
    Checks if a user model is compatible with Django's
    recent changes. Django requires User models to have 
    an int pk, so we check here if it has (mongoengine hasn't)
    """
    try:
        if hasattr(user, 'pk'):
            int(user.pk)
        else:
            int(user)
    except (ValueError, TypeError):
        return False
    return True

def label_for_field(name, model, model_admin=None, return_attr=False):
    attr = None
    model._meta = init_document_options(model)
    try:
        field = model._meta.get_field_by_name(name)[0]
        label = field.name.replace('_', ' ')
    except FieldDoesNotExist: 
        if name == "__unicode__":
            label = force_unicode(model._meta.verbose_name)
        elif name == "__str__":
            label = smart_str(model._meta.verbose_name)
        else:
            if isinstance(name, collections.Callable):
                attr = name
            elif model_admin is not None and hasattr(model_admin, name):
                attr = getattr(model_admin, name)
            elif hasattr(model, name):
                attr = getattr(model, name)
            else:
                message = "Unable to lookup '%s' on %s" % (name, model._meta.object_name)
                if model_admin:
                    message += " or %s" % (model_admin.__class__.__name__,)
                raise AttributeError(message)


            if hasattr(attr, "short_description"):
                label = attr.short_description
            elif isinstance(attr, collections.Callable):
                if attr.__name__ == "<lambda>":
                    label = "--"
                else:
                    label = pretty_name(attr.__name__)
            else:
                label = pretty_name(name)
    if return_attr:
        return (label, attr)
    else:
        return label

def display_for_field(value, field):
    from django.contrib.admin.templatetags.admin_list import _boolean_icon
    from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE   

    if field.flatchoices:
        return dict(field.flatchoices).get(value, EMPTY_CHANGELIST_VALUE)
    # NullBooleanField needs special-case null-handling, so it comes
    # before the general null test.
    elif isinstance(field, fields.BooleanField):
        return _boolean_icon(value)
    elif value is None:
        return EMPTY_CHANGELIST_VALUE
    elif isinstance(field, fields.DateTimeField):
        return formats.localize(value)
    elif isinstance(field, fields.DecimalField):
        return formats.number_format(value, field.decimal_places)
    elif isinstance(field, fields.FloatField):
        return formats.number_format(value)
    else:
        return smart_unicode(value)

########NEW FILE########
__FILENAME__ = validation
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.contrib.admin.util import get_fields_from_path, NotRelationField
from django.contrib.admin.validation import (check_type, check_isseq, check_isdict,
                                             get_field, BaseValidator)

from mongoengine import ListField, ReferenceField, DateTimeField

from mongodbforms import BaseDocumentForm, BaseDocumentFormSet

"""
Does basic ModelAdmin option validation. Calls custom validation
classmethod in the end if it is provided in cls. The signature of the
custom validation classmethod should be: def validate(cls, model).
"""

__all__ = ['MongoBaseValidator', 'MongoInlineValidator']


class MongoBaseValidator(BaseValidator):
    def validate(self, cls, model):
        for m in dir(self):
            if m.startswith('validate_'):
                getattr(self, m)(cls, model)

    def check_field_spec(self, cls, model, flds, label):
        """
        Validate the fields specification in `flds` from a ModelAdmin subclass
        `cls` for the `model` model. Use `label` for reporting problems to the user.

        The fields specification can be a ``fields`` option or a ``fields``
        sub-option from a ``fieldsets`` option component.
        """
        for fields in flds:
            # The entry in fields might be a tuple. If it is a standalone
            # field, make it into a tuple to make processing easier.
            if type(fields) != tuple:
                fields = (fields,)
            for field in fields:
                if field in cls.readonly_fields:
                    # Stuff can be put in fields that isn't actually a
                    # model field if it's in readonly_fields,
                    # readonly_fields will handle the validation of such
                    # things.
                    continue
                try:
                    model._meta.get_field(field)
                except models.FieldDoesNotExist:
                    # If we can't find a field on the model that matches, it could be an
                    # extra field on the form; nothing to check so move on to the next field.
                    continue

    def validate_raw_id_fields(self, cls, model):
        " Validate that raw_id_fields only contains field names that are listed on the model. "
        if hasattr(cls, 'raw_id_fields'):
            check_isseq(cls, 'raw_id_fields', cls.raw_id_fields)
            for idx, field in enumerate(cls.raw_id_fields):
                f = get_field(cls, model, 'raw_id_fields', field)
                if not is_relation(f):
                    raise ImproperlyConfigured("'%s.raw_id_fields[%d]', '%s' must "
                            "be either a ForeignKey or ManyToManyField."
                            % (cls.__name__, idx, field))

    def validate_form(self, cls, model):
        " Validate that form subclasses BaseModelForm. "
        if hasattr(cls, 'form') and not issubclass(cls.form, BaseDocumentForm):
            raise ImproperlyConfigured("%s.form does not inherit from "
                    "BaseModelForm." % cls.__name__)

    def validate_filter_vertical(self, cls, model):
        " Validate that filter_vertical is a sequence of field names. "
        if hasattr(cls, 'filter_vertical'):
            check_isseq(cls, 'filter_vertical', cls.filter_vertical)
            for idx, field in enumerate(cls.filter_vertical):
                f = get_field(cls, model, 'filter_vertical', field)
                if not is_multi_relation(f):
                    raise ImproperlyConfigured("'%s.filter_vertical[%d]' must be "
                        "a ManyToManyField." % (cls.__name__, idx))

    def validate_filter_horizontal(self, cls, model):
        " Validate that filter_horizontal is a sequence of field names. "
        if hasattr(cls, 'filter_horizontal'):
            check_isseq(cls, 'filter_horizontal', cls.filter_horizontal)
            for idx, field in enumerate(cls.filter_horizontal):
                f = get_field(cls, model, 'filter_horizontal', field)
                if not is_multi_relation(f):
                    raise ImproperlyConfigured("'%s.filter_horizontal[%d]' must be "
                        "a ManyToManyField." % (cls.__name__, idx))

    def validate_radio_fields(self, cls, model):
        " Validate that radio_fields is a dictionary of choice or foreign key fields. "
        from django.contrib.admin.options import HORIZONTAL, VERTICAL
        if hasattr(cls, 'radio_fields'):
            check_isdict(cls, 'radio_fields', cls.radio_fields)
            for field, val in cls.radio_fields.items():
                f = get_field(cls, model, 'radio_fields', field)
                if not (isinstance(f, ReferenceField) or f.choices):
                    raise ImproperlyConfigured("'%s.radio_fields['%s']' "
                            "is neither an instance of ForeignKey nor does "
                            "have choices set." % (cls.__name__, field))
                if not val in (HORIZONTAL, VERTICAL):
                    raise ImproperlyConfigured("'%s.radio_fields['%s']' "
                            "is neither admin.HORIZONTAL nor admin.VERTICAL."
                            % (cls.__name__, field))

    def validate_prepopulated_fields(self, cls, model):
        " Validate that prepopulated_fields if a dictionary  containing allowed field types. "
        # prepopulated_fields
        if hasattr(cls, 'prepopulated_fields'):
            check_isdict(cls, 'prepopulated_fields', cls.prepopulated_fields)
            for field, val in cls.prepopulated_fields.items():
                f = get_field(cls, model, 'prepopulated_fields', field)
                if isinstance(f, DateTimeField) or is_relation(f):
                    raise ImproperlyConfigured("'%s.prepopulated_fields['%s']' "
                            "is either a DateTimeField, ForeignKey or "
                            "ManyToManyField. This isn't allowed."
                            % (cls.__name__, field))
                check_isseq(cls, "prepopulated_fields['%s']" % field, val)
                for idx, f in enumerate(val):
                    get_field(cls, model, "prepopulated_fields['%s'][%d]" % (field, idx), f)


class ModelAdminValidator(BaseValidator):
    def validate_save_as(self, cls, model):
        " Validate save_as is a boolean. "
        check_type(cls, 'save_as', bool)

    def validate_save_on_top(self, cls, model):
        " Validate save_on_top is a boolean. "
        check_type(cls, 'save_on_top', bool)

    def validate_inlines(self, cls, model):
        " Validate inline model admin classes. "
        from django.contrib.admin.options import BaseModelAdmin
        if hasattr(cls, 'inlines'):
            check_isseq(cls, 'inlines', cls.inlines)
            for idx, inline in enumerate(cls.inlines):
                if not issubclass(inline, BaseModelAdmin):
                    raise ImproperlyConfigured("'%s.inlines[%d]' does not inherit "
                            "from BaseModelAdmin." % (cls.__name__, idx))
                if not inline.model:
                    raise ImproperlyConfigured("'model' is a required attribute "
                            "of '%s.inlines[%d]'." % (cls.__name__, idx))
                if not issubclass(inline.model, models.Model):
                    raise ImproperlyConfigured("'%s.inlines[%d].model' does not "
                            "inherit from models.Model." % (cls.__name__, idx))
                inline.validate(inline.model)
                self.check_inline(inline, model)

    def check_inline(self, cls, parent_model):
        " Validate inline class's fk field is not excluded. "
        pass
        #fk = _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name, can_fail=True)
        #if hasattr(cls, 'exclude') and cls.exclude:
        #    if fk and fk.name in cls.exclude:
        #        raise ImproperlyConfigured("%s cannot exclude the field "
        #                "'%s' - this is the foreign key to the parent model "
        #                "%s.%s." % (cls.__name__, fk.name, parent_model._meta.app_label, parent_model.__name__))

    def validate_list_display(self, cls, model):
        " Validate that list_display only contains fields or usable attributes. "
        if hasattr(cls, 'list_display'):
            check_isseq(cls, 'list_display', cls.list_display)
            for idx, field in enumerate(cls.list_display):
                if not callable(field):
                    if not hasattr(cls, field):
                        if not hasattr(model, field):
                            try:
                                model._meta.get_field(field)
                            except models.FieldDoesNotExist:
                                raise ImproperlyConfigured("%s.list_display[%d], %r is not a callable or an attribute of %r or found in the model %r."
                                    % (cls.__name__, idx, field, cls.__name__, model._meta.object_name))
                        else:
                            # getattr(model, field) could be an X_RelatedObjectsDescriptor
                            f = fetch_attr(cls, model, "list_display[%d]" % idx, field)
                            if is_multi_relation(f):
                                raise ImproperlyConfigured("'%s.list_display[%d]', '%s' is a ManyToManyField which is not supported."
                                    % (cls.__name__, idx, field))

    def validate_list_display_links(self, cls, model):
        " Validate that list_display_links either is None or a unique subset of list_display."
        if hasattr(cls, 'list_display_links'):
            if cls.list_display_links is None:
                return
            check_isseq(cls, 'list_display_links', cls.list_display_links)
            for idx, field in enumerate(cls.list_display_links):
                if field not in cls.list_display:
                    raise ImproperlyConfigured("'%s.list_display_links[%d]' "
                            "refers to '%s' which is not defined in 'list_display'."
                            % (cls.__name__, idx, field))

    def validate_list_filter(self, cls, model):
        """
        Validate that list_filter is a sequence of one of three options:
            1: 'field' - a basic field filter, possibly w/ relationships (eg, 'field__rel')
            2: ('field', SomeFieldListFilter) - a field-based list filter class
            3: SomeListFilter - a non-field list filter class
        """
        from django.contrib.admin import ListFilter, FieldListFilter
        if hasattr(cls, 'list_filter'):
            check_isseq(cls, 'list_filter', cls.list_filter)
            for idx, item in enumerate(cls.list_filter):
                if callable(item) and not isinstance(item, models.Field):
                    # If item is option 3, it should be a ListFilter...
                    if not issubclass(item, ListFilter):
                        raise ImproperlyConfigured("'%s.list_filter[%d]' is '%s'"
                                " which is not a descendant of ListFilter."
                                % (cls.__name__, idx, item.__name__))
                    # ...  but not a FieldListFilter.
                    if issubclass(item, FieldListFilter):
                        raise ImproperlyConfigured("'%s.list_filter[%d]' is '%s'"
                                " which is of type FieldListFilter but is not"
                                " associated with a field name."
                                % (cls.__name__, idx, item.__name__))
                else:
                    if isinstance(item, (tuple, list)):
                        # item is option #2
                        field, list_filter_class = item
                        if not issubclass(list_filter_class, FieldListFilter):
                            raise ImproperlyConfigured("'%s.list_filter[%d][1]'"
                                " is '%s' which is not of type FieldListFilter."
                                % (cls.__name__, idx, list_filter_class.__name__))
                    else:
                        # item is option #1
                        field = item
                    # Validate the field string
                    try:
                        get_fields_from_path(model, field)
                    except (NotRelationField, FieldDoesNotExist):
                        raise ImproperlyConfigured("'%s.list_filter[%d]' refers to '%s'"
                                " which does not refer to a Field."
                                % (cls.__name__, idx, field))

    def validate_list_select_related(self, cls, model):
        " Validate that list_select_related is a boolean, a list or a tuple. "
        list_select_related = getattr(cls, 'list_select_related', None)
        if list_select_related:
            types = (bool, tuple, list)
            if not isinstance(list_select_related, types):
                raise ImproperlyConfigured("'%s.list_select_related' should be "
                                           "either a bool, a tuple or a list" %
                                           cls.__name__)

    def validate_list_per_page(self, cls, model):
        " Validate that list_per_page is an integer. "
        check_type(cls, 'list_per_page', int)

    def validate_list_max_show_all(self, cls, model):
        " Validate that list_max_show_all is an integer. "
        check_type(cls, 'list_max_show_all', int)

    def validate_list_editable(self, cls, model):
        """
        Validate that list_editable is a sequence of editable fields from
        list_display without first element.
        """
        if hasattr(cls, 'list_editable') and cls.list_editable:
            check_isseq(cls, 'list_editable', cls.list_editable)
            for idx, field_name in enumerate(cls.list_editable):
                try:
                    field = model._meta.get_field_by_name(field_name)[0]
                except models.FieldDoesNotExist:
                    raise ImproperlyConfigured("'%s.list_editable[%d]' refers to a "
                        "field, '%s', not defined on %s.%s."
                        % (cls.__name__, idx, field_name, model._meta.app_label, model.__name__))
                if field_name not in cls.list_display:
                    raise ImproperlyConfigured("'%s.list_editable[%d]' refers to "
                        "'%s' which is not defined in 'list_display'."
                        % (cls.__name__, idx, field_name))
                if cls.list_display_links is not None:
                    if field_name in cls.list_display_links:
                        raise ImproperlyConfigured("'%s' cannot be in both '%s.list_editable'"
                            " and '%s.list_display_links'"
                            % (field_name, cls.__name__, cls.__name__))
                    if not cls.list_display_links and cls.list_display[0] in cls.list_editable:
                        raise ImproperlyConfigured("'%s.list_editable[%d]' refers to"
                            " the first field in list_display, '%s', which can't be"
                            " used unless list_display_links is set."
                            % (cls.__name__, idx, cls.list_display[0]))
                if not field.editable:
                    raise ImproperlyConfigured("'%s.list_editable[%d]' refers to a "
                        "field, '%s', which isn't editable through the admin."
                        % (cls.__name__, idx, field_name))

    def validate_search_fields(self, cls, model):
        " Validate search_fields is a sequence. "
        if hasattr(cls, 'search_fields'):
            check_isseq(cls, 'search_fields', cls.search_fields)

    def validate_date_hierarchy(self, cls, model):
        " Validate that date_hierarchy refers to DateField or DateTimeField. "
        if cls.date_hierarchy:
            f = get_field(cls, model, 'date_hierarchy', cls.date_hierarchy)
            if not isinstance(f, (models.DateField, models.DateTimeField)):
                raise ImproperlyConfigured("'%s.date_hierarchy is "
                        "neither an instance of DateField nor DateTimeField."
                        % cls.__name__)


class MongoInlineValidator(MongoBaseValidator):
    def validate_fk_name(self, cls, model):
        " Validate that fk_name refers to a ForeignKey. "
        if cls.fk_name:  # default value is None
            f = get_field(cls, model, 'fk_name', cls.fk_name)
            if not isinstance(f, ReferenceField):
                raise ImproperlyConfigured("'%s.fk_name is not an instance of "
                        "models.ForeignKey." % cls.__name__)

    def validate_extra(self, cls, model):
        " Validate that extra is an integer. "
        check_type(cls, 'extra', int)

    def validate_max_num(self, cls, model):
        " Validate that max_num is an integer. "
        check_type(cls, 'max_num', int)

    def validate_formset(self, cls, model):
        " Validate formset is a subclass of BaseModelFormSet. "
        if hasattr(cls, 'formset') and not issubclass(cls.formset, BaseDocumentFormSet):
            raise ImproperlyConfigured("'%s.formset' does not inherit from "
                    "BaseModelFormSet." % cls.__name__)


def is_relation(field):
    if isinstance(field, ReferenceField) or is_multi_relation(field):
        return True
    return False

    
def is_multi_relation(field):
    if isinstance(field, ListField) and isinstance(field.field, ReferenceField):
        return True
    return False


def fetch_attr(cls, model, label, field):
    try:
        return model._meta.get_field(field)
    except models.FieldDoesNotExist:
        pass
    try:
        return getattr(model, field)
    except AttributeError:
        raise ImproperlyConfigured("'%s.%s' refers to '%s' that is neither a field, method or property of model '%s.%s'."
            % (cls.__name__, label, field, model._meta.app_label, model.__name__))
########NEW FILE########
__FILENAME__ = views
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.contrib.admin.views.main import ChangeList, ORDER_VAR
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.paginator import InvalidPage

class DocumentChangeList(ChangeList):
    def get_queryset(self, request):
        # First, we collect all the declared list filters.
        (self.filter_specs, self.has_filters, remaining_lookup_params,
         filters_use_distinct) = self.get_filters(request)

        # Then, we let every list filter modify the queryset to its liking.
        qs = self.root_queryset
        for filter_spec in self.filter_specs:
            new_qs = filter_spec.queryset(request, qs)
            if new_qs is not None:
                qs = new_qs

        try:
            # Finally, we apply the remaining lookup parameters from the query
            # string (i.e. those that haven't already been processed by the
            # filters).
            qs = qs.filter(**remaining_lookup_params)
        except (SuspiciousOperation, ImproperlyConfigured):
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception as e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.
            raise IncorrectLookupParameters(e)

        qs = self.apply_select_related(qs)

        # Set ordering.
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)

        # Apply search results
        qs, search_use_distinct = self.model_admin.get_search_results(
            request, qs, self.query)

        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs
            
            
    def get_ordering(self, request, queryset):
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by ensuring the primary key is used as the last
        ordering field.
        """
        params = self.params
        ordering = list(self.model_admin.get_ordering(request)
                        or self._get_default_ordering())
        if ORDER_VAR in params:
            # Clear ordering and used params
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition('-')
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue # No 'admin_order_field', skip it
                    ordering.append(pfx + order_field)
                except (IndexError, ValueError):
                    continue # Invalid ordering specified, skip it.

        # Add the given query's ordering fields, if any.
        ordering.extend(queryset._ordering)

        # Ensure that the primary key is systematically present in the list of
        # ordering fields so we can guarantee a deterministic order across all
        # database backends.
        pk_name = self.lookup_opts.pk.name
        if not (set(ordering) & set(['pk', '-pk', pk_name, '-' + pk_name])):
            # The two sets do not intersect, meaning the pk isn't present. So
            # we add it.
            ordering.append('-pk')

        return ordering
        
    def get_results(self, request):
        paginator = self.model_admin.get_paginator(request, self.queryset, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        # Get the total number of objects, with no admin filters applied.
        # Perform a slight optimization:
        # full_result_count is equal to paginator.count if no filters
        # were applied
        if self.get_filters_params():
            full_result_count = self.root_queryset.count()
        else:
            full_result_count = result_count
        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = self.queryset.clone()
        else:
            try:
                result_list = paginator.page(self.page_num+1).object_list
            except InvalidPage:
                raise IncorrectLookupParameters

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator
########NEW FILE########
__FILENAME__ = widgets
from django.contrib.admin.widgets import ForeignKeyRawIdWidget, ManyToManyRawIdWidget
from django.utils.html import escape
from django.utils.text import Truncator

from bson.dbref import DBRef

class ReferenceRawIdWidget(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ReferenceFields in the "raw_id" interface rather than
    in a <select> box.
    """
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        if 'style' not in attrs:
            attrs['style'] = 'width:30em;'
        if isinstance(value, DBRef):
            value = value.id
        return super(ReferenceRawIdWidget, self).render(name=name, value=value, attrs=attrs)
    
    def url_parameters(self):
        #from django.contrib.admin.views.main import TO_FIELD_VAR
        params = self.base_url_parameters()
        # There are no reverse relations in mongo. Still need to figure out what
        # the url param does though.
        #params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        return params

    def label_for_value(self, value):
        #key = self.rel.get_related_field().name
        if isinstance(value, DBRef):
            value = value.id
        try:
            obj = self.rel.to.objects().get(**{'pk': value})
            return '&nbsp;<strong>%s</strong>' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, self.rel.to.DoesNotExist):
            return ''
            
class MultiReferenceRawIdWidget(ManyToManyRawIdWidget):
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        if 'style' not in attrs:
            attrs['style'] = 'width:40em;'
        return super(MultiReferenceRawIdWidget, self).render(name=name, value=value, attrs=attrs)
        
        
########NEW FILE########
