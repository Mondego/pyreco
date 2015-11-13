__FILENAME__ = admin
from django import forms, template
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext, ungettext, ugettext_lazy as _
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
from django.forms.formsets import all_valid
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

try:
    from django.contrib.admin import actions
except ImportError:
    actions = False

from authority.models import Permission
from authority.widgets import GenericForeignKeyRawIdWidget
from authority import get_choices_for

class PermissionInline(generic.GenericTabularInline):
    model = Permission
    raw_id_fields = ('user', 'group', 'creator')
    extra = 1

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'codename':
            perm_choices = get_choices_for(self.parent_model)
            kwargs['label'] = _('permission')
            kwargs['widget'] = forms.Select(choices=perm_choices)
        return super(PermissionInline, self).formfield_for_dbfield(db_field, **kwargs)

class ActionPermissionInline(PermissionInline):
    raw_id_fields = ()
    template = 'admin/edit_inline/action_tabular.html'

class ActionErrorList(forms.util.ErrorList):
    def __init__(self, inline_formsets):
        for inline_formset in inline_formsets:
            self.extend(inline_formset.non_form_errors())
            for errors_in_inline_form in inline_formset.errors:
                self.extend(errors_in_inline_form.values())

def edit_permissions(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Check that the user has the permission to edit permissions
    if not (request.user.is_superuser or
            request.user.has_perm('authority.change_permission') or
            request.user.has_perm('authority.change_foreign_permissions')):
        raise PermissionDenied

    inline = ActionPermissionInline(queryset.model, modeladmin.admin_site)
    formsets = []
    for obj in queryset:
        prefixes = {}
        FormSet = inline.get_formset(request, obj)
        prefix = "%s-%s" % (FormSet.get_default_prefix(), obj.pk)
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
        if prefixes[prefix] != 1:
            prefix = "%s-%s" % (prefix, prefixes[prefix])
        if request.POST.get('post'):
            formset = FormSet(data=request.POST, files=request.FILES,
                              instance=obj, prefix=prefix)
        else:
            formset = FormSet(instance=obj, prefix=prefix)
        formsets.append(formset)

    media = modeladmin.media
    inline_admin_formsets = []
    for formset in formsets:
        fieldsets = list(inline.get_fieldsets(request))
        inline_admin_formset = helpers.InlineAdminFormSet(inline, formset, fieldsets)
        inline_admin_formsets.append(inline_admin_formset)
        media = media + inline_admin_formset.media

    ordered_objects = opts.get_ordered_objects()
    if request.POST.get('post'):
        if all_valid(formsets):
            for formset in formsets:
                formset.save()
        else:
            modeladmin.message_user(request, '; '.join(
                err.as_text() for formset in formsets for err in formset.errors
            ))
        # redirect to full request path to make sure we keep filter
        return HttpResponseRedirect(request.get_full_path())

    context = {
        'errors': ActionErrorList(formsets),
        'title': ugettext('Permissions for %s') % force_text(opts.verbose_name_plural),
        'inline_admin_formsets': inline_admin_formsets,
        'app_label': app_label,
        'change': True,
        'ordered_objects': ordered_objects,
        'form_url': mark_safe(''),
        'opts': opts,
        'target_opts': queryset.model._meta,
        'content_type_id': ContentType.objects.get_for_model(queryset.model).id,
        'save_as': False,
        'save_on_top': False,
        'is_popup': False,
        'media': mark_safe(media),
        'show_delete': False,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'queryset': queryset,
        "object_name": force_text(opts.verbose_name),
    }
    template_name = getattr(modeladmin, 'permission_change_form_template', [
        "admin/%s/%s/permission_change_form.html" % (app_label, opts.object_name.lower()),
        "admin/%s/permission_change_form.html" % app_label,
        "admin/permission_change_form.html"
    ])
    return render_to_response(template_name, context,
                              context_instance=template.RequestContext(request))
edit_permissions.short_description = _("Edit permissions for selected %(verbose_name_plural)s")

class PermissionAdmin(admin.ModelAdmin):
    list_display = ('codename', 'content_type', 'user', 'group', 'approved')
    list_filter = ('approved', 'content_type')
    search_fields = ('user__username', 'group__name', 'codename')
    raw_id_fields = ('user', 'group', 'creator')
    generic_fields = ('content_object',)
    actions = ['approve_permissions']
    fieldsets = (
        (None, {'fields': ('codename', ('content_type', 'object_id'))}),
        (_('Permitted'), {'fields': ('approved', 'user', 'group')}),
        (_('Creation'), {'fields': ('creator', 'date_requested', 'date_approved')}),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        # For generic foreign keys marked as generic_fields we use a special widget
        if db_field.name in [f.fk_field for f in self.model._meta.virtual_fields if f.name in self.generic_fields]:
            for gfk in self.model._meta.virtual_fields:
                if gfk.fk_field == db_field.name:
                    kwargs['widget'] = GenericForeignKeyRawIdWidget(
                        gfk.ct_field, self.admin_site._registry.keys())
                    break
        return super(PermissionAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def queryset(self, request):
        user = request.user
        if (user.is_superuser or
                user.has_perm('permissions.change_foreign_permissions')):
            return super(PermissionAdmin, self).queryset(request)
        return super(PermissionAdmin, self).queryset(request).filter(creator=user)

    def approve_permissions(self, request, queryset):
        for permission in queryset:
            permission.approve(request.user)
        message = ungettext("%(count)d permission successfully approved.",
            "%(count)d permissions successfully approved.", len(queryset))
        self.message_user(request, message % {'count': len(queryset)})
    approve_permissions.short_description = _("Approve selected permissions")

admin.site.register(Permission, PermissionAdmin)

if actions:
    admin.site.add_action(edit_permissions)

########NEW FILE########
__FILENAME__ = decorators
import inspect
from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.utils.functional import wraps
from django.db.models import Model, get_model
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME

from authority import get_check
from authority.views import permission_denied

def permission_required(perm, *lookup_variables, **kwargs):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    """
    login_url = kwargs.pop('login_url', settings.LOGIN_URL)
    redirect_field_name = kwargs.pop('redirect_field_name', REDIRECT_FIELD_NAME)
    redirect_to_login = kwargs.pop('redirect_to_login', True)
    def decorate(view_func):
        def decorated(request, *args, **kwargs):
            if request.user.is_authenticated():
                params = []
                for lookup_variable in lookup_variables:
                    if isinstance(lookup_variable, basestring):
                        value = kwargs.get(lookup_variable, None)
                        if value is None:
                            continue
                        params.append(value)
                    elif isinstance(lookup_variable, (tuple, list)):
                        model, lookup, varname = lookup_variable
                        value = kwargs.get(varname, None)
                        if value is None:
                            continue
                        if isinstance(model, basestring):
                            model_class = get_model(*model.split("."))
                        else:
                            model_class = model
                        if model_class is None:
                            raise ValueError(
                                "The given argument '%s' is not a valid model." % model)
                        if (inspect.isclass(model_class) and
                                not issubclass(model_class, Model)):
                            raise ValueError(
                                'The argument %s needs to be a model.' % model)
                        obj = get_object_or_404(model_class, **{lookup: value})
                        params.append(obj)
                check = get_check(request.user, perm)
                granted = False
                if check is not None:
                    granted = check(*params)
                if granted or request.user.has_perm(perm):
                    return view_func(request, *args, **kwargs)
            if redirect_to_login:
                path = urlquote(request.get_full_path())
                tup = login_url, redirect_field_name, path
                return HttpResponseRedirect('%s?%s=%s' % tup)
            return permission_denied(request)
        return wraps(view_func)(decorated)
    return decorate

def permission_required_or_403(perm, *args, **kwargs):
    """
    Decorator that wraps the permission_required decorator and returns a
    permission denied (403) page instead of redirecting to the login URL.
    """
    kwargs['redirect_to_login'] = False
    return permission_required(perm, *args, **kwargs)

########NEW FILE########
__FILENAME__ = exceptions
class AuthorityException(Exception):
    pass

class NotAModel(AuthorityException):
    def __init__(self, object):
        super(NotAModel, self).__init__(
            "Not a model class or instance")

class UnsavedModelInstance(AuthorityException):
    def __init__(self, object):
        super(UnsavedModelInstance, self).__init__(
            "Model instance has no pk, was it saved?")

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from authority import permissions, get_choices_for
from authority.models import Permission
from authority.utils import User


class BasePermissionForm(forms.ModelForm):
    codename = forms.CharField(label=_('Permission'))

    class Meta:
        model = Permission

    def __init__(self, perm=None, obj=None, approved=False, *args, **kwargs):
        self.perm = perm
        self.obj = obj
        self.approved = approved
        if obj and perm:
            self.base_fields['codename'].widget = forms.HiddenInput()
        elif obj and (not perm or not approved):
            perms = get_choices_for(self.obj)
            self.base_fields['codename'].widget = forms.Select(choices=perms)
        super(BasePermissionForm, self).__init__(*args, **kwargs)

    def save(self, request, commit=True, *args, **kwargs):
        self.instance.creator = request.user
        self.instance.content_type = ContentType.objects.get_for_model(self.obj)
        self.instance.object_id = self.obj.id
        self.instance.codename = self.perm
        self.instance.approved = self.approved
        return super(BasePermissionForm, self).save(commit)

class UserPermissionForm(BasePermissionForm):
    user = forms.CharField(label=_('User'))

    class Meta(BasePermissionForm.Meta):
        fields = ('user',)

    def __init__(self, *args, **kwargs):
        if not kwargs.get('approved', False):
            self.base_fields['user'].widget = forms.HiddenInput()
        super(UserPermissionForm, self).__init__(*args, **kwargs)

    def clean_user(self):
        username = self.cleaned_data["user"]
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise forms.ValidationError(
                mark_safe(_("A user with that username does not exist.")))
        check = permissions.BasePermission(user=user)
        error_msg = None
        if user.is_superuser:
            error_msg = _("The user %(user)s do not need to request "
                          "access to any permission as it is a super user.")
        elif check.has_perm(self.perm, self.obj):
            error_msg = _("The user %(user)s already has the permission "
                          "'%(perm)s' for %(object_name)s '%(obj)s'")
        elif check.requested_perm(self.perm, self.obj):
            error_msg = _("The user %(user)s already requested the permission"
                          " '%(perm)s' for %(object_name)s '%(obj)s'")
        if error_msg:
            error_msg = error_msg % {
                'object_name': self.obj._meta.object_name.lower(),
                'perm': self.perm,
                'obj': self.obj,
                'user': user,
            }
            raise forms.ValidationError(mark_safe(error_msg))
        return user


class GroupPermissionForm(BasePermissionForm):
    group = forms.CharField(label=_('Group'))

    class Meta(BasePermissionForm.Meta):
        fields = ('group',)

    def clean_group(self):
        groupname = self.cleaned_data["group"]
        try:
            group = Group.objects.get(name__iexact=groupname)
        except Group.DoesNotExist:
            raise forms.ValidationError(
                mark_safe(_("A group with that name does not exist.")))
        check = permissions.BasePermission(group=group)
        if check.has_perm(self.perm, self.obj):
            raise forms.ValidationError(mark_safe(
                _("This group already has the permission '%(perm)s' for %(object_name)s '%(obj)s'") % {
                    'perm': self.perm,
                    'object_name': self.obj._meta.object_name.lower(),
                    'obj': self.obj,
                }))
        return group

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType


class PermissionManager(models.Manager):

    def get_content_type(self, obj):
        return ContentType.objects.get_for_model(obj)

    def get_for_model(self, obj):
        return self.filter(content_type=self.get_content_type(obj))

    def for_object(self, obj, approved=True):
        return self.get_for_model(obj).select_related(
            'user', 'creator', 'group', 'content_type'
        ).filter(object_id=obj.id, approved=approved)

    def for_user(self, user, obj, check_groups=True):
        perms = self.get_for_model(obj)
        if not check_groups:
            return perms.select_related('user', 'creator').filter(user=user)

        # Hacking user to user__pk to workaround deepcopy bug:
        # http://bugs.python.org/issue2460
        # Which is triggered by django's deepcopy which backports that fix in
        # Django 1.2
        return perms.select_related('user', 'user__groups', 'creator').filter(
            Q(user__pk=user.pk) | Q(group__in=user.groups.all()))

    def user_permissions(
            self, user, perm, obj, approved=True, check_groups=True):
        return self.for_user(
            user,
            obj,
            check_groups,
        ).filter(
            codename=perm,
            approved=approved,
        )

    def group_permissions(self, group, perm, obj, approved=True):
        """
        Get objects that have Group perm permission on
        """
        return self.get_for_model(obj).select_related(
            'user', 'group', 'creator').filter(group=group, codename=perm,
                                               approved=approved)

    def delete_objects_permissions(self, obj):
        """
        Delete permissions related to an object instance
        """
        perms = self.for_object(obj)
        perms.delete()

    def delete_user_permissions(self, user, perm, obj, check_groups=False):
        """
        Remove granular permission perm from user on an object instance
        """
        user_perms = self.user_permissions(user, perm, obj, check_groups=False)
        if not user_perms.filter(object_id=obj.id):
            return
        perms = self.user_permissions(user, perm, obj).filter(object_id=obj.id)
        perms.delete()

########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _

from authority.managers import PermissionManager
from authority.utils import User


class Permission(models.Model):
    """
    A granular permission model, per-object permission in other words.
    This kind of permission is associated with a user/group and an object
    of any content type.
    """
    codename = models.CharField(_('codename'), max_length=100)
    content_type = models.ForeignKey(ContentType, related_name="row_permissions")
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(User, null=True, blank=True, related_name='granted_permissions')
    group = models.ForeignKey(Group, null=True, blank=True)
    creator = models.ForeignKey(User, null=True, blank=True, related_name='created_permissions')

    approved = models.BooleanField(_('approved'), default=False, help_text=_("Designates whether the permission has been approved and treated as active. Unselect this instead of deleting permissions."))

    date_requested = models.DateTimeField(_('date requested'), default=datetime.now)
    date_approved = models.DateTimeField(_('date approved'), blank=True, null=True)

    objects = PermissionManager()

    def __unicode__(self):
        return self.codename

    class Meta:
        unique_together = ("codename", "object_id", "content_type", "user", "group")
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        permissions = (
            ('change_foreign_permissions', 'Can change foreign permissions'),
            ('delete_foreign_permissions', 'Can delete foreign permissions'),
            ('approve_permission_requests', 'Can approve permission requests'),
        )

    def save(self, *args, **kwargs):
        # Make sure the approval date is always set
        if self.approved and not self.date_approved:
            self.date_approved = datetime.now()
        super(Permission, self).save(*args, **kwargs)

    def approve(self, creator):
        """
        Approve granular permission request setting a Permission entry as
        approved=True for a specific action from an user on an object instance.
        """
        self.approved = True
        self.creator = creator
        self.save()

########NEW FILE########
__FILENAME__ = permissions
from django.conf import settings
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.base import Model, ModelBase
from django.template.defaultfilters import slugify

from authority.exceptions import NotAModel, UnsavedModelInstance
from authority.models import Permission


class PermissionMetaclass(type):
    """
    Used to generate the default set of permission checks "add", "change" and
    "delete".
    """
    def __new__(cls, name, bases, attrs):
        new_class = super(
            PermissionMetaclass, cls).__new__(cls, name, bases, attrs)
        if not new_class.label:
            new_class.label = "%s_permission" % new_class.__name__.lower()
        new_class.label = slugify(new_class.label)
        if new_class.checks is None:
            new_class.checks = []
        # force check names to be lower case
        new_class.checks = [check.lower() for check in new_class.checks]
        return new_class


class BasePermission(object):
    """
    Base Permission class to be used to define app permissions.
    """
    __metaclass__ = PermissionMetaclass

    checks = ()
    label = None
    generic_checks = ['add', 'browse', 'change', 'delete']

    def __init__(self, user=None, group=None, *args, **kwargs):
        self.user = user
        self.group = group
        super(BasePermission, self).__init__(*args, **kwargs)

    def _get_user_cached_perms(self):
        """
        Set up both the user and group caches.
        """
        if not self.user:
            return {}, {}
        group_pks = set(self.user.groups.values_list(
            'pk',
            flat=True,
        ))
        perms = Permission.objects.filter(
            Q(user__pk=self.user.pk) | Q(group__pk__in=group_pks),
        )
        user_permissions = {}
        group_permissions = {}
        for perm in perms:
            if perm.user_id == self.user.pk:
                user_permissions[(
                    perm.object_id,
                    perm.content_type_id,
                    perm.codename,
                    perm.approved,
                )] = True
            # If the user has the permission do for something, but perm.user !=
            # self.user then by definition that permission came from the
            # group.
            else:
                group_permissions[(
                    perm.object_id,
                    perm.content_type_id,
                    perm.codename,
                    perm.approved,
                )] = True
        return user_permissions, group_permissions

    def _get_group_cached_perms(self):
        """
        Set group cache.
        """
        if not self.group:
            return {}
        perms = Permission.objects.filter(
            group=self.group,
        )
        group_permissions = {}
        for perm in perms:
            group_permissions[(
                perm.object_id,
                perm.content_type_id,
                perm.codename,
                perm.approved,
            )] = True
        return group_permissions

    def _prime_user_perm_caches(self):
        """
        Prime both the user and group caches and put them on the ``self.user``.
        In addition add a cache filled flag on ``self.user``.
        """
        perm_cache, group_perm_cache = self._get_user_cached_perms()
        self.user._authority_perm_cache = perm_cache
        self.user._authority_group_perm_cache = group_perm_cache
        self.user._authority_perm_cache_filled = True

    def _prime_group_perm_caches(self):
        """
        Prime the group cache and put them on the ``self.group``.
        In addition add a cache filled flag on ``self.group``.
        """
        perm_cache = self._get_group_cached_perms()
        self.group._authority_perm_cache = perm_cache
        self.group._authority_perm_cache_filled = True

    @property
    def _user_perm_cache(self):
        """
        cached_permissions will generate the cache in a lazy fashion.
        """
        # Check to see if the cache has been primed.
        if not self.user:
            return {}
        cache_filled = getattr(
            self.user,
            '_authority_perm_cache_filled',
            False,
        )
        if cache_filled:
            # Don't really like the name for this, but this matches how Django
            # does it.
            return self.user._authority_perm_cache

        # Prime the cache.
        self._prime_user_perm_caches()
        return self.user._authority_perm_cache

    @property
    def _group_perm_cache(self):
        """
        cached_permissions will generate the cache in a lazy fashion.
        """
        # Check to see if the cache has been primed.
        if not self.group:
            return {}
        cache_filled = getattr(
            self.group,
            '_authority_perm_cache_filled',
            False,
        )
        if cache_filled:
            # Don't really like the name for this, but this matches how Django
            # does it.
            return self.group._authority_perm_cache

        # Prime the cache.
        self._prime_group_perm_caches()
        return self.group._authority_perm_cache

    @property
    def _user_group_perm_cache(self):
        """
        cached_permissions will generate the cache in a lazy fashion.
        """
        # Check to see if the cache has been primed.
        if not self.user:
            return {}
        cache_filled = getattr(
            self.user,
            '_authority_perm_cache_filled',
            False,
        )
        if cache_filled:
            return self.user._authority_group_perm_cache

        # Prime the cache.
        self._prime_user_perm_caches()
        return self.user._authority_group_perm_cache

    def invalidate_permissions_cache(self):
        """
        In the event that the Permission table is changed during the use of a
        permission the Permission cache will need to be invalidated and
        regenerated. By calling this method the invalidation will occur, and
        the next time the cached_permissions is used the cache will be
        re-primed.
        """
        if self.user:
            self.user._authority_perm_cache_filled = False
        if self.group:
            self.group._authority_perm_cache_filled = False

    @property
    def use_smart_cache(self):
        use_smart_cache = getattr(settings, 'AUTHORITY_USE_SMART_CACHE', True)
        return (self.user or self.group) and use_smart_cache

    def has_user_perms(self, perm, obj, approved, check_groups=True):
        if not self.user:
            return False
        if self.user.is_superuser:
            return True
        if not self.user.is_active:
            return False

        if self.use_smart_cache:
            content_type_pk = Permission.objects.get_content_type(obj).pk

            def _user_has_perms(cached_perms):
                # Check to see if the permission is in the cache.
                return cached_perms.get((
                    obj.pk,
                    content_type_pk,
                    perm,
                    approved,
                ))

            # Check to see if the permission is in the cache.
            if _user_has_perms(self._user_perm_cache):
                return True

            # Optionally check group permissions
            if check_groups:
                return _user_has_perms(self._user_group_perm_cache)
            return False

        # Actually hit the DB, no smart cache used.
        return Permission.objects.user_permissions(
            self.user,
            perm,
            obj,
            approved,
            check_groups,
        ).filter(
            object_id=obj.pk,
        ).exists()

    def has_group_perms(self, perm, obj, approved):
        """
        Check if group has the permission for the given object
        """
        if not self.group:
            return False

        if self.use_smart_cache:
            content_type_pk = Permission.objects.get_content_type(obj).pk

            def _group_has_perms(cached_perms):
                # Check to see if the permission is in the cache.
                return cached_perms.get((
                    obj.pk,
                    content_type_pk,
                    perm,
                    approved,
                ))

            # Check to see if the permission is in the cache.
            return _group_has_perms(self._group_perm_cache)

        # Actually hit the DB, no smart cache used.
        return Permission.objects.group_permissions(
            self.group,
            perm, obj,
            approved,
        ).filter(
            object_id=obj.pk,
        ).exists()

    def has_perm(self, perm, obj, check_groups=True, approved=True):
        """
        Check if user has the permission for the given object
        """
        if self.user:
            if self.has_user_perms(perm, obj, approved, check_groups):
                return True
        if self.group:
            return self.has_group_perms(perm, obj, approved)
        return False

    def requested_perm(self, perm, obj, check_groups=True):
        """
        Check if user requested a permission for the given object
        """
        return self.has_perm(perm, obj, check_groups, False)

    def can(self, check, generic=False, *args, **kwargs):
        if not args:
            args = [self.model]
        perms = False
        for obj in args:
            # skip this obj if it's not a model class or instance
            if not isinstance(obj, (ModelBase, Model)):
                continue
            # first check Django's permission system
            if self.user:
                perm = self.get_django_codename(check, obj, generic)
                perms = perms or self.user.has_perm(perm)
            perm = self.get_codename(check, obj, generic)
            # then check authority's per object permissions
            if not isinstance(obj, ModelBase) and isinstance(obj, self.model):
                # only check the authority if obj is not a model class
                perms = perms or self.has_perm(perm, obj)
        return perms

    def get_django_codename(
            self, check, model_or_instance, generic=False, without_left=False):
        if without_left:
            perm = check
        else:
            perm = '%s.%s' % (model_or_instance._meta.app_label, check.lower())
        if generic:
            perm = '%s_%s' % (
                perm,
                model_or_instance._meta.object_name.lower(),
            )
        return perm

    def get_codename(self, check, model_or_instance, generic=False):
        perm = '%s.%s' % (self.label, check.lower())
        if generic:
            perm = '%s_%s' % (
                perm,
                model_or_instance._meta.object_name.lower(),
            )
        return perm

    def assign(self, check=None, content_object=None, generic=False):
        """
        Assign a permission to a user.

        To assign permission for all checks: let check=None.
        To assign permission for all objects: let content_object=None.

        If generic is True then "check" will be suffixed with _modelname.
        """
        result = []

        if not content_object:
            content_objects = (self.model,)
        elif not isinstance(content_object, (list, tuple)):
            content_objects = (content_object,)
        else:
            content_objects = content_object

        if not check:
            checks = self.generic_checks + getattr(self, 'checks', [])
        elif not isinstance(check, (list, tuple)):
            checks = (check,)
        else:
            checks = check

        for content_object in content_objects:
            # raise an exception before adding any permission
            # i think Django does not rollback by default
            if not isinstance(content_object, (Model, ModelBase)):
                raise NotAModel(content_object)
            elif isinstance(content_object, Model) and not content_object.pk:
                raise UnsavedModelInstance(content_object)

            content_type = ContentType.objects.get_for_model(content_object)

            for check in checks:
                if isinstance(content_object, Model):
                    # make an authority per object permission
                    codename = self.get_codename(
                        check,
                        content_object,
                        generic,
                    )
                    try:
                        perm = Permission.objects.get(
                            user=self.user,
                            codename=codename,
                            approved=True,
                            content_type=content_type,
                            object_id=content_object.pk,
                        )
                    except Permission.DoesNotExist:
                        perm = Permission.objects.create(
                            user=self.user,
                            content_object=content_object,
                            codename=codename,
                            approved=True,
                        )

                    result.append(perm)

                elif isinstance(content_object, ModelBase):
                    # make a Django permission
                    codename = self.get_django_codename(
                        check,
                        content_object,
                        generic,
                        without_left=True,
                    )
                    try:
                        perm = DjangoPermission.objects.get(codename=codename)
                    except DjangoPermission.DoesNotExist:
                        name = check
                        if '_' in name:
                            name = name[0:name.find('_')]
                        perm = DjangoPermission(
                            name=name,
                            codename=codename,
                            content_type=content_type,
                        )
                        perm.save()
                    self.user.user_permissions.add(perm)
                    result.append(perm)

        return result

########NEW FILE########
__FILENAME__ = sites
from inspect import getmembers, ismethod
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured

from authority.permissions import BasePermission

class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class PermissionSite(object):
    """
    A dictionary that contains permission instances and their labels.
    """
    _registry = {}
    _choices = {}

    def get_permission_by_label(self, label):
        for perm_cls in self._registry.values():
            if perm_cls.label == label:
                return perm_cls
        return None

    def get_permissions_by_model(self, model):
        return [perm for perm in self._registry.values() if perm.model == model]

    def get_check(self, user, label):
        perm_label, check_name = label.split('.')
        perm_cls = self.get_permission_by_label(perm_label)
        if perm_cls is None:
            return None
        perm_instance = perm_cls(user)
        return getattr(perm_instance, check_name, None)

    def get_labels(self):
        return [perm.label for perm in self._registry.values()]

    def get_choices_for(self, obj, default=models.BLANK_CHOICE_DASH):
        model_cls = obj
        if not isinstance(obj, ModelBase):
            model_cls = obj.__class__
        if model_cls in self._choices:
            return self._choices[model_cls]
        choices = [] + default
        for perm in self.get_permissions_by_model(model_cls):
            for name, check in getmembers(perm, ismethod):
                if name in perm.checks:
                    signature = '%s.%s' % (perm.label, name)
                    label = getattr(check, 'short_description', signature)
                    choices.append((signature, label))
        self._choices[model_cls] = choices
        return choices

    def register(self, model_or_iterable, permission_class=None, **options):
        if not permission_class:
            permission_class = BasePermission

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]

        if permission_class.label in self.get_labels():
            raise ImproperlyConfigured(
                "The name of %s conflicts with %s" % (permission_class,
                     self.get_permission_by_label(permission_class.label)))

        for model in model_or_iterable:
            if model in self._registry:
                raise AlreadyRegistered(
                    'The model %s is already registered' % model.__name__)
            if options:
                options['__module__'] = __name__
                permission_class = type("%sPermission" % model.__name__,
                    (permission_class,), options)

            permission_class.model = model
            self.setup(model, permission_class)
            self._registry[model] = permission_class

    def unregister(self, model_or_iterable):
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def setup(self, model, permission):
        for check_name in permission.checks:
            check_func = getattr(permission, check_name, None)
            if check_func is not None:
                func = self.create_check(check_name, check_func)
                func.__name__ = check_name
                func.short_description = getattr(check_func, 'short_description',
                    _("%(object_name)s permission '%(check)s'") % {
                        'object_name': model._meta.object_name,
                        'check': check_name})
                setattr(permission, check_name, func)
            else:
                permission.generic_checks.append(check_name)
        for check_name in permission.generic_checks:
            func = self.create_check(check_name, generic=True)
            object_name = model._meta.object_name
            func_name = "%s_%s" % (check_name, object_name.lower())
            func.short_description = _("Can %(check)s this %(object_name)s") % {
                'object_name': model._meta.object_name.lower(),
                'check': check_name}
            func.check_name = check_name
            if func_name not in permission.checks:
                permission.checks = (list(permission.checks) + [func_name])
            setattr(permission, func_name, func)
        setattr(model, "permissions", PermissionDescriptor())

    def create_check(self, check_name, check_func=None, generic=False):
        def check(self, *args, **kwargs):
            granted = self.can(check_name, generic, *args, **kwargs)
            if check_func and not granted:
                return check_func(self, *args, **kwargs)
            return granted
        return check

class PermissionDescriptor(object):
    def get_content_type(self, obj=None):
        ContentType = models.get_model("contenttypes", "contenttype")
        if obj:
            return ContentType.objects.get_for_model(obj)
        else:
            raise Exception("Invalid arguments given to PermissionDescriptor.get_content_type")

    def __get__(self, instance, owner):
        if instance is None:
            return self
        ct = self.get_content_type(instance)
        return ct.row_permissions.all()

site = PermissionSite()
get_check = site.get_check
get_choices_for = site.get_choices_for
register = site.register
unregister = site.unregister

########NEW FILE########
__FILENAME__ = permissions
from django import template
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse

from authority import get_check
from authority import permissions
from authority.models import Permission
from authority.forms import UserPermissionForm
from authority.utils import User


register = template.Library()


@register.simple_tag
def url_for_obj(view_name, obj):
    return reverse(view_name, kwargs={
            'app_label': obj._meta.app_label,
            'module_name': obj._meta.module_name,
            'pk': obj.pk})

@register.simple_tag
def add_url_for_obj(obj):
    return url_for_obj('authority-add-permission', obj)

@register.simple_tag
def request_url_for_obj(obj):
    return url_for_obj('authority-add-permission-request', obj)


class ResolverNode(template.Node):
    """
    A small wrapper that adds a convenient resolve method.
    """
    def resolve(self, var, context):
        """Resolves a variable out of context if it's not in quotes"""
        if var is None:
            return var
        if var[0] in ('"', "'") and var[-1] == var[0]:
            return var[1:-1]
        else:
            return template.Variable(var).resolve(context)

    @classmethod
    def next_bit_for(cls, bits, key, if_none=None):
        try:
            return bits[bits.index(key)+1]
        except ValueError:
            return if_none


class PermissionComparisonNode(ResolverNode):
    """
    Implements a node to provide an "if user/group has permission on object"
    """
    @classmethod
    def handle_token(cls, parser, token):
        bits = token.contents.split()
        if 5 < len(bits) < 3:
            raise template.TemplateSyntaxError("'%s' tag takes three, "
                                                "four or five arguments" % bits[0])
        end_tag = 'endifhasperm'
        nodelist_true = parser.parse(('else', end_tag))
        token = parser.next_token()
        if token.contents == 'else': # there is an 'else' clause in the tag
            nodelist_false = parser.parse((end_tag,))
            parser.delete_first_token()
        else:
            nodelist_false = template.NodeList()
        if len(bits) == 3: # this tag requires at most 2 objects . None is given
            objs = (None, None)
        elif len(bits) == 4:# one is given
            objs = (bits[3], None)
        else: #two are given
            objs = (bits[3], bits[4])
        return cls(bits[2], bits[1], nodelist_true, nodelist_false, *objs)

    def __init__(self, user, perm, nodelist_true, nodelist_false, *objs):
        self.user = user
        self.objs = objs
        self.perm = perm
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        try:
            user = self.resolve(self.user, context)
            perm = self.resolve(self.perm, context)
            if self.objs:
                objs = []
                for obj in self.objs:
                    if obj is not None:
                        objs.append(self.resolve(obj, context))
            else:
                objs = None
            check = get_check(user, perm)
            if check is not None:
                if check(*objs):
                    # return True if check was successful
                    return self.nodelist_true.render(context)
        # If the app couldn't be found
        except (ImproperlyConfigured, ImportError):
            return ''
        # If either variable fails to resolve, return nothing.
        except template.VariableDoesNotExist:
            return ''
        # If the types don't permit comparison, return nothing.
        except (TypeError, AttributeError):
            return ''
        return self.nodelist_false.render(context)

@register.tag
def ifhasperm(parser, token):
    """
    This function provides functionality for the 'ifhasperm' template tag

    Syntax::

        {% ifhasperm PERMISSION_LABEL.CHECK_NAME USER *OBJS %}
            lalala
        {% else %}
            meh
        {% endifhasperm %}

        {% ifhasperm "poll_permission.change_poll" request.user %}
            lalala
        {% else %}
            meh
        {% endifhasperm %}

    """
    return PermissionComparisonNode.handle_token(parser, token)


class PermissionFormNode(ResolverNode):

    @classmethod
    def handle_token(cls, parser, token, approved):
        bits = token.contents.split()
        tag_name = bits[0]
        kwargs = {
            'obj': cls.next_bit_for(bits, 'for'),
            'perm': cls.next_bit_for(bits, 'using', None),
            'template_name': cls.next_bit_for(bits, 'with', ''),
            'approved': approved,
        }
        return cls(**kwargs)

    def __init__(self, obj, perm=None, approved=False, template_name=None):
        self.obj = obj
        self.perm = perm
        self.approved = approved
        self.template_name = template_name

    def render(self, context):
        obj = self.resolve(self.obj, context)
        perm = self.resolve(self.perm, context)
        if self.template_name:
            template_name = [self.resolve(obj, context) for obj in self.template_name.split(',')]
        else:
            template_name = 'authority/permission_form.html'
        request = context['request']
        extra_context = {}
        if self.approved:
            if (request.user.is_authenticated() and
                    request.user.has_perm('authority.add_permission')):
                extra_context = {
                    'form_url': url_for_obj('authority-add-permission', obj),
                    'next': request.build_absolute_uri(),
                    'approved': self.approved,
                    'form': UserPermissionForm(perm, obj, approved=self.approved,
                                               initial=dict(codename=perm)),
                }
        else:
            if request.user.is_authenticated() and not request.user.is_superuser:
                extra_context = {
                    'form_url': url_for_obj('authority-add-permission-request', obj),
                    'next': request.build_absolute_uri(),
                    'approved': self.approved,
                    'form': UserPermissionForm(perm, obj,
                        approved=self.approved, initial=dict(
                        codename=perm, user=request.user.username)),
                }
        return template.loader.render_to_string(template_name, extra_context,
                            context_instance=template.RequestContext(request))

@register.tag
def permission_form(parser, token):
    """
    Renders an "add permissions" form for the given object. If no object
    is given it will render a select box to choose from.

    Syntax::

        {% permission_form for OBJ using PERMISSION_LABEL.CHECK_NAME [with TEMPLATE] %}
        {% permission_form for lesson using "lesson_permission.add_lesson" %}

    """
    return PermissionFormNode.handle_token(parser, token, approved=True)

@register.tag
def permission_request_form(parser, token):
    """
    Renders an "add permissions" form for the given object. If no object
    is given it will render a select box to choose from.

    Syntax::

        {% permission_request_form for OBJ and PERMISSION_LABEL.CHECK_NAME [with TEMPLATE] %}
        {% permission_request_form for lesson using "lesson_permission.add_lesson" with "authority/permission_request_form.html" %}

    """
    return PermissionFormNode.handle_token(parser, token, approved=False)


class PermissionsForObjectNode(ResolverNode):

    @classmethod
    def handle_token(cls, parser, token, approved, name):
        bits = token.contents.split()
        tag_name = bits[0]
        kwargs = {
            'obj': cls.next_bit_for(bits, tag_name),
            'user': cls.next_bit_for(bits, 'for'),
            'var_name': cls.next_bit_for(bits, 'as', name),
            'approved': approved,
        }
        return cls(**kwargs)

    def __init__(self, obj, user, var_name, approved, perm=None):
        self.obj = obj
        self.user = user
        self.perm = perm
        self.var_name = var_name
        self.approved = approved

    def render(self, context):
        obj = self.resolve(self.obj, context)
        var_name = self.resolve(self.var_name, context)
        user = self.resolve(self.user, context)
        perms = []
        if not isinstance(user, AnonymousUser):
            perms = Permission.objects.for_object(obj, self.approved)
            if isinstance(user, User):
                perms = perms.filter(user=user)
        context[var_name] = perms
        return ''

@register.tag
def get_permissions(parser, token):
    """
    Retrieves all permissions associated with the given obj and user
    and assigns the result to a context variable.
    
    Syntax::

        {% get_permissions obj %}
        {% for perm in permissions %}
            {{ perm }}
        {% endfor %}

        {% get_permissions obj as "my_permissions" %}
        {% get_permissions obj for request.user as "my_permissions" %}

    """
    return PermissionsForObjectNode.handle_token(parser, token, approved=True,
                                                 name='"permissions"')

@register.tag
def get_permission_requests(parser, token):
    """
    Retrieves all permissions requests associated with the given obj and user
    and assigns the result to a context variable.
    
    Syntax::

        {% get_permission_requests obj %}
        {% for perm in permissions %}
            {{ perm }}
        {% endfor %}

        {% get_permission_requests obj as "my_permissions" %}
        {% get_permission_requests obj for request.user as "my_permissions" %}

    """
    return PermissionsForObjectNode.handle_token(parser, token,
                                                 approved=False,
                                                 name='"permission_requests"')

class PermissionForObjectNode(ResolverNode):

    @classmethod
    def handle_token(cls, parser, token, approved, name):
        bits = token.contents.split()
        tag_name = bits[0]
        kwargs = {
            'perm': cls.next_bit_for(bits, tag_name),
            'user': cls.next_bit_for(bits, 'for'),
            'objs': cls.next_bit_for(bits, 'and'),
            'var_name': cls.next_bit_for(bits, 'as', name),
            'approved': approved,
        }
        return cls(**kwargs)

    def __init__(self, perm, user, objs, approved, var_name):
        self.perm = perm
        self.user = user
        self.objs = objs
        self.var_name = var_name
        self.approved = approved

    def render(self, context):
        objs = [self.resolve(obj, context) for obj in self.objs.split(',')]
        var_name = self.resolve(self.var_name, context)
        perm = self.resolve(self.perm, context)
        user = self.resolve(self.user, context)
        granted = False
        if not isinstance(user, AnonymousUser):
            if self.approved:
                check = get_check(user, perm)
                if check is not None:
                    granted = check(*objs)
            else:
                check = permissions.BasePermission(user=user)
                for obj in objs:
                    granted = check.requested_perm(perm, obj)
                    if granted:
                        break
        context[var_name] = granted
        return ''

@register.tag
def get_permission(parser, token):
    """
    Performs a permission check with the given signature, user and objects
    and assigns the result to a context variable.

    Syntax::

        {% get_permission PERMISSION_LABEL.CHECK_NAME for USER and *OBJS [as VARNAME] %}

        {% get_permission "poll_permission.change_poll" for request.user and poll as "is_allowed" %}
        {% get_permission "poll_permission.change_poll" for request.user and poll,second_poll as "is_allowed" %}
        
        {% if is_allowed %}
            I've got ze power to change ze pollllllzzz. Muahahaa.
        {% else %}
            Meh. No power for meeeee.
        {% endif %}

    """
    return PermissionForObjectNode.handle_token(parser, token,
                                                approved=True,
                                                name='"permission"')

@register.tag
def get_permission_request(parser, token):
    """
    Performs a permission request check with the given signature, user and objects
    and assigns the result to a context variable.

    Syntax::

        {% get_permission_request PERMISSION_LABEL.CHECK_NAME for USER and *OBJS [as VARNAME] %}

        {% get_permission_request "poll_permission.change_poll" for request.user and poll as "asked_for_permissio" %}
        {% get_permission_request "poll_permission.change_poll" for request.user and poll,second_poll as "asked_for_permissio" %}
        
        {% if asked_for_permissio %}
            Dude, you already asked for permission!
        {% else %}
            Oh, please fill out this 20 page form and sign here.
        {% endif %}

    """
    return PermissionForObjectNode.handle_token(parser, token,
                                                 approved=False,
                                                 name='"permission_request"')

def base_link(context, perm, view_name):
    return {
        'next': context['request'].build_absolute_uri(),
        'url': reverse(view_name, kwargs={'permission_pk': perm.pk,}),
    }

@register.inclusion_tag('authority/permission_delete_link.html', takes_context=True)
def permission_delete_link(context, perm):
    """
    Renders a html link to the delete view of the given permission. Returns
    no content if the request-user has no permission to delete foreign
    permissions.
    """
    user = context['request'].user
    if user.is_authenticated():
        if user.has_perm('authority.delete_foreign_permissions') \
            or user.pk == perm.creator.pk:
            return base_link(context, perm, 'authority-delete-permission')
    return {'url': None}

@register.inclusion_tag('authority/permission_request_delete_link.html', takes_context=True)
def permission_request_delete_link(context, perm):
    """
    Renders a html link to the delete view of the given permission request. 
    Returns no content if the request-user has no permission to delete foreign
    permissions.
    """
    user = context['request'].user
    if user.is_authenticated():
        link_kwargs = base_link(context, perm,
                                'authority-delete-permission-request')
        if user.has_perm('authority.delete_permission'):
            link_kwargs['is_requestor'] = False
            return link_kwargs
        if not perm.approved and perm.user == user:
            link_kwargs['is_requestor'] = True
            return link_kwargs
    return {'url': None}

@register.inclusion_tag('authority/permission_request_approve_link.html', takes_context=True)
def permission_request_approve_link(context, perm):
    """
    Renders a html link to the approve view of the given permission request. 
    Returns no content if the request-user has no permission to delete foreign
    permissions.
    """
    user = context['request'].user
    if user.is_authenticated():
        if user.has_perm('authority.approve_permission_requests'):
            return base_link(context, perm,
                'authority-approve-permission-request')
    return {'url': None}

########NEW FILE########
__FILENAME__ = tests
from django import VERSION
from django.conf import settings
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.auth.models import Group
from django.db.models import Q
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

import authority
from authority import permissions
from authority.models import Permission
from authority.exceptions import NotAModel, UnsavedModelInstance
from authority.utils import User


if VERSION >= (1, 5):
    FIXTURES = ['tests_custom.json']
    QUERY = Q(email="jezdez@github.com")
else:
    FIXTURES = ['tests.json']
    QUERY = Q(username="jezdez")


class UserPermission(permissions.BasePermission):
    checks = ('browse',)
    label = 'user_permission'
authority.register(User, UserPermission)


class GroupPermission(permissions.BasePermission):
    checks = ('browse',)
    label = 'group_permission'
authority.register(Group, GroupPermission)


class DjangoPermissionChecksTestCase(TestCase):
    """
    Django permission objects have certain methods that are always present,
    test those here.

    self.user will be given:
    - django permission add_user (test_add)
    - authority to delete_user which is him (test_delete)

    This permissions are given in the test case and not in the fixture, for
    later reference.
    """
    fixtures = FIXTURES

    def setUp(self):
        self.user = User.objects.get(QUERY)
        self.check = UserPermission(self.user)

    def test_no_permission(self):
        self.assertFalse(self.check.add_user())
        self.assertFalse(self.check.delete_user())
        self.assertFalse(self.check.delete_user(self.user))

    def test_add(self):
        # setup
        perm = DjangoPermission.objects.get(codename='add_user')
        self.user.user_permissions.add(perm)

        # test
        self.assertTrue(self.check.add_user())

    def test_delete(self):
        perm = Permission(
            user=self.user,
            content_object=self.user,
            codename='user_permission.delete_user',
            approved=True
        )
        perm.save()

        # test
        self.assertFalse(self.check.delete_user())
        self.assertTrue(self.check.delete_user(self.user))


class AssignBehaviourTest(TestCase):
    """
    self.user will be given:
    - permission add_user (test_add),
    - permission delete_user for him (test_delete),
    - all existing codenames permissions: a/b/c/d (test_all),
    """
    fixtures = FIXTURES

    def setUp(self):
        self.user = User.objects.get(QUERY)
        self.check = UserPermission(self.user)

    def test_add(self):
        result = self.check.assign(check='add_user')

        self.assertTrue(isinstance(result[0], DjangoPermission))
        self.assertTrue(self.check.add_user())

    def test_delete(self):
        result = self.check.assign(
            content_object=self.user,
            check='delete_user',
        )

        self.assertTrue(isinstance(result[0], Permission))
        self.assertFalse(self.check.delete_user())
        self.assertTrue(self.check.delete_user(self.user))

    def test_all(self):
        result = self.check.assign(content_object=self.user)
        self.assertTrue(isinstance(result, list))
        self.assertTrue(self.check.browse_user(self.user))
        self.assertTrue(self.check.delete_user(self.user))
        self.assertTrue(self.check.add_user(self.user))
        self.assertTrue(self.check.change_user(self.user))


class GenericAssignBehaviourTest(TestCase):
    """
    self.user will be given:
    - permission add (test_add),
    - permission delete for him (test_delete),
    """
    fixtures = FIXTURES

    def setUp(self):
        self.user = User.objects.get(QUERY)
        self.check = UserPermission(self.user)

    def test_add(self):
        result = self.check.assign(check='add', generic=True)

        self.assertTrue(isinstance(result[0], DjangoPermission))
        self.assertTrue(self.check.add_user())

    def test_delete(self):
        result = self.check.assign(
            content_object=self.user,
            check='delete',
            generic=True,
        )

        self.assertTrue(isinstance(result[0], Permission))
        self.assertFalse(self.check.delete_user())
        self.assertTrue(self.check.delete_user(self.user))


class AssignExceptionsTest(TestCase):
    """
    Tests that exceptions are thrown if assign() was called with inconsistent
    arguments.
    """
    fixtures = FIXTURES

    def setUp(self):
        self.user = User.objects.get(QUERY)
        self.check = UserPermission(self.user)

    def test_unsaved_model(self):
        try:
            self.check.assign(content_object=User())
        except UnsavedModelInstance:
            return True
        self.fail()

    def test_not_model_content_object(self):
        try:
            self.check.assign(content_object='fail')
        except NotAModel:
            return True
        self.fail()


class SmartCachingTestCase(TestCase):
    """
    The base test case for all tests that have to do with smart caching.
    """
    fixtures = FIXTURES

    def setUp(self):
        # Create a user.
        self.user = User.objects.get(QUERY)

        # Create a group.
        self.group = Group.objects.create()
        self.group.user_set.add(self.user)

        # Make the checks
        self.user_check = UserPermission(user=self.user)
        self.group_check = GroupPermission(group=self.group)

        # Ensure we are using the smart cache.
        settings.AUTHORITY_USE_SMART_CACHE = True

    def tearDown(self):
        ContentType.objects.clear_cache()

    def _old_user_permission_check(self):
        # This is what the old, pre-cache system would check to see if a user
        # had a given permission.
        return Permission.objects.user_permissions(
            self.user,
            'foo',
            self.user,
            approved=True,
            check_groups=True,
        )

    def _old_group_permission_check(self):
        # This is what the old, pre-cache system would check to see if a user
        # had a given permission.
        return Permission.objects.group_permissions(
            self.group,
            'foo',
            self.group,
            approved=True,
        )


class PerformanceTest(SmartCachingTestCase):
    """
    Tests that permission are actually cached and that the number of queries
    stays constant.
    """

    def test_has_user_perms(self):
        # Show that when calling has_user_perms multiple times no additional
        # queries are done.

        # Make sure the has_user_perms check does not get short-circuited.
        assert not self.user.is_superuser
        assert self.user.is_active

        # Regardless of how many times has_user_perms is called, the number of
        # queries is the same.
        # Content type and permissions (2 queries)
        with self.assertNumQueries(3):
            for _ in range(5):
                # Need to assert it so the query actually gets executed.
                assert not self.user_check.has_user_perms(
                    'foo',
                    self.user,
                    True,
                    False,
                )

    def test_group_has_perms(self):
        with self.assertNumQueries(2):
            for _ in range(5):
                assert not self.group_check.has_group_perms(
                    'foo',
                    self.group,
                    True,
                )

    def test_has_user_perms_check_group(self):
        # Regardless of the number groups permissions, it should only take one
        # query to check both users and groups.
        # Content type and permissions (2 queries)
        with self.assertNumQueries(3):
            self.user_check.has_user_perms(
                'foo',
                self.user,
                approved=True,
                check_groups=True,
            )

    def test_invalidate_user_permissions_cache(self):
        # Show that calling invalidate_permissions_cache will cause extra
        # queries.
        # For each time invalidate_permissions_cache gets called, you
        # will need to do one query to get content type and one to get
        # the permissions.
        with self.assertNumQueries(6):
            for _ in range(5):
                assert not self.user_check.has_user_perms(
                    'foo',
                    self.user,
                    True,
                    False,
                )

            # Invalidate the cache to show that a query will be generated when
            # checking perms again.
            self.user_check.invalidate_permissions_cache()
            ContentType.objects.clear_cache()

            # One query to re generate the cache.
            for _ in range(5):
                assert not self.user_check.has_user_perms(
                    'foo',
                    self.user,
                    True,
                    False,
                )

    def test_invalidate_group_permissions_cache(self):
        # Show that calling invalidate_permissions_cache will cause extra
        # queries.
        # For each time invalidate_permissions_cache gets called, you
        # will need to do one query to get content type and one to get
        with self.assertNumQueries(4):
            for _ in range(5):
                assert not self.group_check.has_group_perms(
                    'foo',
                    self.group,
                    True,
                )

            # Invalidate the cache to show that a query will be generated when
            # checking perms again.
            self.group_check.invalidate_permissions_cache()
            ContentType.objects.clear_cache()

            # One query to re generate the cache.
            for _ in range(5):
                assert not self.group_check.has_group_perms(
                    'foo',
                    self.group,
                    True,
                )

    def test_has_user_perms_check_group_multiple(self):
        # Create a permission with just a group.
        Permission.objects.create(
            content_type=Permission.objects.get_content_type(User),
            object_id=self.user.pk,
            codename='foo',
            group=self.group,
            approved=True,
        )
        # By creating the Permission objects the Content type cache
        # gets created.

        # Check the number of queries.
        with self.assertNumQueries(2):
            assert self.user_check.has_user_perms('foo', self.user, True, True)

        # Create a second group.
        new_group = Group.objects.create(name='new_group')
        new_group.user_set.add(self.user)

        # Create a permission object for it.
        Permission.objects.create(
            content_type=Permission.objects.get_content_type(User),
            object_id=self.user.pk,
            codename='foo',
            group=new_group,
            approved=True,
        )

        self.user_check.invalidate_permissions_cache()

        # Make sure it is the same number of queries.
        with self.assertNumQueries(2):
            assert self.user_check.has_user_perms('foo', self.user, True, True)


class GroupPermissionCacheTestCase(SmartCachingTestCase):
    """
    Tests that peg expected behaviour
    """

    def test_has_user_perms_with_groups(self):
        perms = self._old_user_permission_check()
        self.assertEqual([], list(perms))

        # Use the new cached user perms to show that the user does not have the
        # perms.
        can_foo_with_group = self.user_check.has_user_perms(
            'foo',
            self.user,
            approved=True,
            check_groups=True,
        )
        self.assertFalse(can_foo_with_group)

        # Create a permission with just that group.
        perm = Permission.objects.create(
            content_type=Permission.objects.get_content_type(User),
            object_id=self.user.pk,
            codename='foo',
            group=self.group,
            approved=True,
        )

        # Old permission check
        perms = self._old_user_permission_check()
        self.assertEqual([perm], list(perms))

        # Invalidate the cache.
        self.user_check.invalidate_permissions_cache()
        can_foo_with_group = self.user_check.has_user_perms(
            'foo',
            self.user,
            approved=True,
            check_groups=True,
        )
        self.assertTrue(can_foo_with_group)

    def test_has_group_perms_no_user(self):
        # Make sure calling has_user_perms on a permission that does not have a
        # user does not throw any errors.
        can_foo_with_group = self.group_check.has_group_perms(
            'foo',
            self.user,
            approved=True,
        )
        self.assertFalse(can_foo_with_group)

        perms = self._old_group_permission_check()
        self.assertEqual([], list(perms))

        # Create a permission with just that group.
        perm = Permission.objects.create(
            content_type=Permission.objects.get_content_type(Group),
            object_id=self.group.pk,
            codename='foo',
            group=self.group,
            approved=True,
        )

        # Old permission check
        perms = self._old_group_permission_check()
        self.assertEqual([perm], list(perms))

        # Invalidate the cache.
        self.group_check.invalidate_permissions_cache()

        can_foo_with_group = self.group_check.has_group_perms(
            'foo',
            self.group,
            approved=True,
        )
        self.assertTrue(can_foo_with_group)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import *
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import *

urlpatterns = patterns('authority.views',
    url(r'^permission/add/(?P<app_label>[\w\-]+)/(?P<module_name>[\w\-]+)/(?P<pk>\d+)/$',
        view='add_permission',
        name="authority-add-permission",
        kwargs={'approved': True}
    ),
    url(r'^permission/delete/(?P<permission_pk>\d+)/$',
        view='delete_permission',
        name="authority-delete-permission",
        kwargs={'approved': True}
    ),
    url(r'^request/add/(?P<app_label>[\w\-]+)/(?P<module_name>[\w\-]+)/(?P<pk>\d+)/$',
        view='add_permission',
        name="authority-add-permission-request",
        kwargs={'approved': False}
    ),
    url(r'^request/approve/(?P<permission_pk>\d+)/$',
        view='approve_permission_request',
        name="authority-approve-permission-request"
    ),
    url(r'^request/delete/(?P<permission_pk>\d+)/$',
        view='delete_permission',
        name="authority-delete-permission-request",
        kwargs={'approved': False}
    ),
)

########NEW FILE########
__FILENAME__ = utils
from django.contrib import auth


def get_user_class():
    if hasattr(auth, "get_user_model"):
        return auth.get_user_model()
    else:
        return auth.models.User


User = get_user_class()
########NEW FILE########
__FILENAME__ = views
from datetime import datetime
from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.db.models.loading import get_model
from django.utils.translation import ugettext as _
from django.template.context import RequestContext
from django.template import loader
from django.contrib.auth.decorators import login_required

from authority.models import Permission
from authority.forms import UserPermissionForm
from authority.templatetags.permissions import url_for_obj

def get_next(request, obj=None):
    next = request.REQUEST.get('next')
    if not next:
        if obj and hasattr(obj, 'get_absolute_url'):
            next = obj.get_absolute_url()
        else:
            next = '/'
    return next

@login_required
def add_permission(request, app_label, module_name, pk, approved=False,
                   template_name = 'authority/permission_form.html',
                   extra_context=None, form_class=UserPermissionForm):
    codename = request.POST.get('codename', None)
    model = get_model(app_label, module_name)
    if model is None:
        return permission_denied(request)
    obj = get_object_or_404(model, pk=pk)
    next = get_next(request, obj)
    if approved:
        if not request.user.has_perm('authority.add_permission'):
            return HttpResponseRedirect(
                url_for_obj('authority-add-permission-request', obj))
        view_name = 'authority-add-permission'
    else:
        view_name = 'authority-add-permission-request'
    if request.method == 'POST':
        if codename is None:
            return HttpResponseForbidden(next)
        form = form_class(data=request.POST, obj=obj, approved=approved,
                          perm=codename, initial=dict(codename=codename))
        if not approved:
            # Limit permission request to current user
            form.data['user'] = request.user
        if form.is_valid():
            permission = form.save(request)
            request.user.message_set.create(
                message=_('You added a permission request.'))
            return HttpResponseRedirect(next)
    else:
        form = form_class(obj=obj, approved=approved, perm=codename,
                          initial=dict(codename=codename))
    context = {
        'form': form,
        'form_url': url_for_obj(view_name, obj),
        'next': next,
        'perm': codename,
        'approved': approved,
    }
    if extra_context:
        context.update(extra_context)
    return render_to_response(template_name, context,
                              context_instance=RequestContext(request))

@login_required
def approve_permission_request(request, permission_pk):
    requested_permission = get_object_or_404(Permission, pk=permission_pk)
    if request.user.has_perm('authority.approve_permission_requests'):
        requested_permission.approve(request.user)
        request.user.message_set.create(
            message=_('You approved the permission request.'))
    next = get_next(request, requested_permission)
    return HttpResponseRedirect(next)

@login_required
def delete_permission(request, permission_pk, approved):
    permission = get_object_or_404(Permission,  pk=permission_pk,
                                   approved=approved)
    if (request.user.has_perm('authority.delete_foreign_permissions')
            or request.user == permission.creator):
        permission.delete()
        if approved:
            msg = _('You removed the permission.')
        else:
            msg = _('You removed the permission request.')
        request.user.message_set.create(message=msg)
    next = get_next(request)
    return HttpResponseRedirect(next)

def permission_denied(request, template_name=None, extra_context=None):
    """
    Default 403 handler.

    Templates: `403.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """
    if template_name is None:
        template_name = ('403.html', 'authority/403.html')
    context = {
        'request_path': request.path,
    }
    if extra_context:
        context.update(extra_context)
    return HttpResponseForbidden(loader.render_to_string(template_name, context,
                                 context_instance=RequestContext(request)))

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

generic_script = """
<script type="text/javascript">
function showGenericRelatedObjectLookupPopup(ct_select, triggering_link, url_base) {
    var url = content_types[ct_select.options[ct_select.selectedIndex].value];
    if (url != undefined) {
        triggering_link.href = url_base + url;
        return showRelatedObjectLookupPopup(triggering_link);
    }
    return false;
}
</script>
"""

class GenericForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    def __init__(self, ct_field, cts=[], attrs=None):
        self.ct_field = ct_field
        self.cts = cts
        forms.TextInput.__init__(self, attrs)

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        related_url = '../../../'
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.iteritems()])
        else:
            url = ''
        if 'class' not in attrs:
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        output = [forms.TextInput.render(self, name, value, attrs)]
        output.append("""%(generic_script)s
            <a href="%(related)s%(url)s" class="related-lookup" id="lookup_id_%(name)s" onclick="return showGenericRelatedObjectLookupPopup(document.getElementById('id_%(ct_field)s'), this, '%(related)s%(url)s');"> """
             % {'generic_script': generic_script, 'related': related_url, 'url': url, 'name': name, 'ct_field': self.ct_field})
        output.append('<img src="%s/admin/img/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (settings.STATIC_URL, _('Lookup')))

        from django.contrib.contenttypes.models import ContentType
        content_types = """
        <script type="text/javascript">
        var content_types = new Array();
        %s
        </script>
        """ % ('\n'.join(["content_types[%s] = '%s/%s/';" % (ContentType.objects.get_for_model(ct).id, ct._meta.app_label, ct._meta.object_name.lower()) for ct in self.cts]))
        return mark_safe(u''.join(output) + content_types)

    def url_parameters(self):
        return {}

########NEW FILE########
__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if len(sys.argv) > 2 and sys.argv[1] == '--version':
    VERSION = ' == %s' % sys.argv[2]
    args = sys.argv[3:] + ['bootstrap']
else:
    VERSION = ''
    args = sys.argv[1:] + ['bootstrap']

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-authority documentation build configuration file, created by
# sphinx-quickstart on Thu Jul  9 10:52:07 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))
#sys.path.append(os.path.join(os.path.dirname(__file__), '../src/'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-authority'
copyright = u'2009, the django-authority team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.8'

# The full version, including alpha/beta/rc tags.
release = '0.8dev'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['.theme']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = '.static/logo.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'favicon.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-authoritydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-authority.tex', u'django-authority Documentation',
   u'The django-authority team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = development

from example.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.admin import FlatPageAdmin
from authority.admin import PermissionInline

admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageAdmin, inlines=[PermissionInline])

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

from authority.forms import UserPermissionForm

class SpecialUserPermissionForm(UserPermissionForm):
    user = forms.CharField(label=_('Special user'), widget=forms.Textarea())

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = permissions
from django.contrib.flatpages.models import FlatPage
from django.utils.translation import ugettext_lazy as _

import authority
from authority.permissions import BasePermission

class FlatPagePermission(BasePermission):
    """
    This class contains a bunch of checks:
    
    1. the default checks 'add_flatpage', 'browse_flatpage',
       'change_flatpage' and 'delete_flatpage'
    2. the custom checks:
        a) 'review_flatpage', which is similar to the default checks
        b) 'top_secret', which is represented by the top_secret method

    You can use those checks in your views directly like::

        def review_flatpage(request, url):
            flatpage = get_object_or_404(url__contains=url)
            check = FlatPagePermission(request.user)
            if check.review_flatpage(obj=flatpage):
                print "yay, you can review this flatpage!"
            return flatpage(request, url)

    Or the same view using the decorator permission_required::

        @permission_required('flatpage_permission.review_flatpage',
            ('flatpages.flatpage', 'url__contains', 'url'))
        def review_flatpage(request, url):
            print "yay, you can review this flatpage!"
            return flatpage(request, url)

    Or you can use this permission in your templates like this::

        {% ifhasperm "flatpage_permission.review_flatpage" request.user flatpage %}
            Yes, you are allowed to review flatpage '{{ flatpage }}', aren't you?
        {% else %}
            Nope, sorry. You aren't allowed to review this flatpage.
        {% endifhasperm %}

    """
    label = 'flatpage_permission'
    checks = ('review', 'top_secret')

    def top_secret(self, flatpage=None, lala=None):
        if flatpage and flatpage.registration_required:
            return self.browse_flatpage(obj=flatpage)
        return False
    top_secret.short_description=_('Is allowed to see top secret flatpages')

authority.register(FlatPage, FlatPagePermission)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
from __future__ import print_function

from django.contrib.flatpages.views import flatpage
from django.contrib.flatpages.models import FlatPage

from authority.decorators import permission_required, permission_required_or_403

# @permission_required('flatpage_permission.top_secret',
#     (FlatPage, 'url__contains', 'url'), (FlatPage, 'url__contains', 'lala'))
# use this to return a 403 page:
@permission_required_or_403('flatpage_permission.top_secret',
    (FlatPage, 'url__contains', 'url'), 'lala')
def top_secret(request, url, lala=None):
    """
    A wrapping view that performs the permission check given in the decorator
    """
    print("secret!")
    return flatpage(request, url)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
import os

from django.core.management import execute_from_command_line

try:
    import settings as settings_mod  # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

sys.path.insert(0, settings_mod.PROJECT_ROOT)
sys.path.insert(0, settings_mod.PROJECT_ROOT + '/../')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'example.settings')

if __name__ == "__main__":
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = production

from example.settings import *

########NEW FILE########
__FILENAME__ = settings
import os

from django import VERSION

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'example.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Don't share this with anybody.
SECRET_KEY = 'ljlv2lb2d&)#by6th=!v=03-c^(o4lop92i@z4b3f1&ve0yx6d'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

INTERNAL_IPS = ('127.0.0.1',)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

ROOT_URLCONF = 'example.urls'

SITE_ID = 1

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.admin',
    'authority',
    'example.exampleapp',
)

if VERSION >= (1, 5):
    INSTALLED_APPS = INSTALLED_APPS + ('example.users',)
    AUTH_USER_MODEL = 'users.User'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates"),
)

# Use local_settings.py for things to override privately
try:
    from local_settings import *  # noqa
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, handler500, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, include, handler500, url
from django.conf import settings
from django.contrib import admin
import authority

admin.autodiscover()
authority.autodiscover()

handler500 # Pyflakes

from exampleapp.forms import SpecialUserPermissionForm

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    #('^admin/', include(admin.site.urls)),
    url(r'^authority/permission/add/(?P<app_label>[\w\-]+)/(?P<module_name>[\w\-]+)/(?P<pk>\d+)/$',
        view='authority.views.add_permission',
        name="authority-add-permission",
        kwargs={'approved': True, 'form_class': SpecialUserPermissionForm}
    ),
    url(r'^request/add/(?P<app_label>[\w\-]+)/(?P<module_name>[\w\-]+)/(?P<pk>\d+)/$',
        view='authority.views.add_permission',
        name="authority-add-permission-request",
        kwargs={'approved': False, 'form_class': SpecialUserPermissionForm}
    ),
    (r'^authority/', include('authority.urls')),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^(?P<url>[\/0-9A-Za-z]+)$', 'example.exampleapp.views.top_secret', {'lala': 'oh yeah!'}),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
    )

########NEW FILE########
__FILENAME__ = admin
from django.contrib.auth.admin import UserAdmin
from example.users.models import User


admin.site.register(User, UserAdmin)

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    greeting_message = models.TextField()
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

########NEW FILE########
