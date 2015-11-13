__FILENAME__ = admin
from django import forms
from django.contrib import admin
from django.utils.translation import ugettext
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.models import User, Group, Permission
from django.contrib.admin.widgets import FilteredSelectMultiple

from .models import UserPermissionList, GroupPermissionList
from .utils import update_permissions_user, \
     update_user_groups, update_permissions_group


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        exclude = ('user_permissions', 'groups')

class NonrelPermissionUserForm(UserForm):
    user_permissions = forms.MultipleChoiceField(required=False)
    groups = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(NonrelPermissionUserForm, self).__init__(*args, **kwargs)

        self.fields['user_permissions'] = forms.MultipleChoiceField(required=False)
        self.fields['groups'] = forms.MultipleChoiceField(required=False)

        permissions_objs = Permission.objects.all().order_by('name')
        choices = []
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])
        self.fields['user_permissions'].choices = choices

        group_objs = Group.objects.all()
        choices = []
        for group_obj in group_objs:
            choices.append([group_obj.id, group_obj.name])
        self.fields['groups'].choices = choices

        try:
            user_perm_list = UserPermissionList.objects.get(
                user=kwargs['instance'])
            self.fields['user_permissions'].initial = user_perm_list.permission_fk_list
            self.fields['groups'].initial = user_perm_list.group_fk_list
        except (UserPermissionList.DoesNotExist, KeyError):
            self.fields['user_permissions'].initial = list()
            self.fields['groups'].initial = list()


class NonrelPermissionCustomUserAdmin(UserAdmin):
    form = NonrelPermissionUserForm
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    def save_model(self, request, obj, form, change):
        super(NonrelPermissionCustomUserAdmin, self).save_model(request, obj, form, change)
        try:
            if len(form.cleaned_data['user_permissions']) > 0:
                permissions = list(Permission.objects.filter(
                    id__in=form.cleaned_data['user_permissions']).order_by('name'))
            else:
                permissions = []

            update_permissions_user(permissions, obj)
        except KeyError:
            pass

        try:
            if len(form.cleaned_data['groups']) > 0:
                groups = list(Group.objects.filter(
                    id__in=form.cleaned_data['groups']))
            else:
                groups = []

            update_user_groups(obj, groups)
        except KeyError:
            pass


class PermissionAdmin(admin.ModelAdmin):
    ordering = ('name',)


class GroupForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        # Temporarily exclude 'permissions' as it causes an
        # unsupported query to be executed
        original_exclude = self._meta.exclude
        self._meta.exclude = ['permissions',] + (self._meta.exclude if self._meta.exclude else [])

        super(GroupForm, self).__init__(*args, **kwargs)

        self._meta.exclude = original_exclude

        self.fields['permissions'] = forms.MultipleChoiceField(required=False, widget=FilteredSelectMultiple(ugettext('Permissions'), False))

        permissions_objs = Permission.objects.all().order_by('name')
        choices = []
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])
        self.fields['permissions'].choices = choices

        try:
            current_perm_list = GroupPermissionList.objects.get(
                group=kwargs['instance'])
            self.fields['permissions'].initial = current_perm_list.permission_fk_list
        except (GroupPermissionList.DoesNotExist, KeyError):
            self.fields['permissions'].initial = []

    class Meta:
        model = Group
        fields = ('name',)


class CustomGroupAdmin(admin.ModelAdmin):
    form = GroupForm
    fieldsets = None

    def save_model(self, request, obj, form, change):
        super(CustomGroupAdmin, self).save_model(request, obj, form, change)

        if len(form.cleaned_data['permissions']) > 0:
            permissions = list(Permission.objects.filter(
                id__in=form.cleaned_data['permissions']).order_by('name'))
        else:
            permissions = []


        update_permissions_group(permissions, obj)

try:
    admin.site.unregister(User)
except NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

admin.site.register(User, NonrelPermissionCustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Group, CustomGroupAdmin)

########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group

from models import UserPermissionList, GroupPermissionList


class NonrelPermissionBackend(ModelBackend):
    """
    Implements Django's permission system on Django-Nonrel
    """
    supports_object_permissions = False
    supports_anonymous_user = True

    def get_group_permissions(self, user_obj, obj=None, user_perm_list=None):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        """
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_group_perm_cache'):
            perms = set([])
            if not user_perm_list:
                user_perm_list, _ = UserPermissionList.objects.get_or_create(user=user_obj)
            groups = Group.objects.filter(id__in=user_perm_list.group_fk_list)
            group_perm_lists = GroupPermissionList.objects.filter(group__in=list(groups))

            for group_perm_list in group_perm_lists:
                perms.update(group_perm_list.permission_list)

            user_obj._group_perm_cache = perms
        return user_obj._group_perm_cache

    def get_all_permissions(self, user_obj, obj=None):
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            try:
                user_perm_list = UserPermissionList.objects.get(user=user_obj)
                user_obj._perm_cache = set(user_perm_list.permission_list)

            except UserPermissionList.DoesNotExist:
                user_perm_list = None
                user_obj._perm_cache = set()

            user_obj._perm_cache.update(self.get_group_permissions(user_obj, user_perm_list=user_perm_list))
        return user_obj._perm_cache

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User, Group
from django.db import models

from djangotoolbox.fields import ListField


class UserPermissionList(models.Model):
    user = models.ForeignKey(User)

    permission_list = ListField(models.CharField(max_length=64))
    permission_fk_list = ListField(models.CharField(max_length=32))

    group_fk_list = ListField(models.CharField(max_length=32))


class GroupPermissionList(models.Model):
    group = models.ForeignKey(Group)
    permission_list = ListField(models.CharField(max_length=64))
    permission_fk_list = ListField(models.CharField(max_length=32))

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group, Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .models import UserPermissionList, \
     GroupPermissionList
from .utils import add_permission_to_user, \
     add_user_to_group, add_permission_to_group, update_permissions_user, update_user_groups, update_permissions_group


class BackendTest(TestCase):
    def setUp(self):
        self.old_auth_backends = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (
            'permission_backend_nonrel.backends.NonrelPermissionBackend',
           )
        User.objects.create_user('test', 'test@example.com', 'test')

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.old_auth_backends

    def test_update_permissions_user(self):
        content_type = ContentType.objects.get_for_model(User)
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user = User.objects.get(username='test')

        # add a permission
        update_permissions_user([perm], user)
        self.assertEqual(UserPermissionList.objects.count(), 1)
        pl = UserPermissionList.objects.all()[0]
        self.assertEqual(pl.permission_list , ['%s.%s'%(perm.content_type.app_label, perm.codename)])
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perm('auth.test23x'), False)

        # add a duplicated permission
        user = User.objects.get(username='test')
        update_permissions_user([perm], user)
        self.assertEqual(UserPermissionList.objects.count(), 1)
        pl = UserPermissionList.objects.all()[0]
        self.assertEqual(pl.permission_list , ['%s.%s'%(perm.content_type.app_label, perm.codename)])

        # add a list of permissions
        perm1 = Permission.objects.create(name='test1',
                                         content_type=content_type,
                                         codename='test1')
        perm2 = Permission.objects.create(name='test2',
                                         content_type=content_type,
                                         codename='test2')

        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test1'), False)
        self.assertEqual(user.has_perm('auth.test2'), False)
        user = User.objects.get(username='test')
        update_permissions_user([perm1, perm2, perm], user)
        self.assertEqual(user.has_perm('auth.test1'), True)
        self.assertEqual(user.has_perm('auth.test2'), True)
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perm('auth.test23x'), False)


        user = User.objects.get(username='test')
        pl = UserPermissionList.objects.all()[0]
        update_permissions_user([perm], user)
        self.assertEqual(user.has_perm('auth.test1'), False)
        self.assertEqual(user.has_perm('auth.test2'), False)
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perm('auth.test23x'), False)

        # remove all permissions
        user = User.objects.get(username='test')
        update_permissions_user([], user)
        self.assertEqual(UserPermissionList.objects.count(), 1)
        pl = UserPermissionList.objects.all()[0]
        self.assertEqual(pl.permission_list , [])
        self.assertEqual(user.has_perm('auth.test'), False)
        self.assertEqual(user.has_perm('auth.test1'), False)
        self.assertEqual(user.has_perm('auth.test2'), False)


    def test_add_user_to_group(self):
        user = User.objects.get(username='test')
        group = Group.objects.create(name='test_group')
        update_user_groups(user, [group])
        self.assertEqual(UserPermissionList.objects.count(), 1)
        self.assertNotEqual(UserPermissionList.objects.all()[0] , None)


    def test_update_permissions_group(self):
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user = User.objects.get(username='test')
        group = Group.objects.create(name='test_group')
        add_user_to_group(user, group)
        update_permissions_group([perm], group)
        self.assertEqual(GroupPermissionList.objects.count(), 1)
        gl = GroupPermissionList.objects.all()[0]
        self.assertEqual(gl.permission_list , ['%s.%s'%(perm.content_type.app_label, perm.codename)])
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perm('auth.test2312'), False)

        group1= Group.objects.create(name='test_group1')
        perm1 = Permission.objects.create(name='test1',
                                         content_type=content_type,
                                         codename='test1')

        add_user_to_group(user, group1)
        update_permissions_group([perm1], group1)
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perm('auth.test1'), True)

        update_permissions_group([], group1)
        group_list = UserPermissionList.objects.filter(group_fk_list=group1.id)
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perm('auth.test1'), False)

        update_user_groups(user, [group1])
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        self.assertEqual(user.has_perm('auth.test1'), False)

    def test_has_perm(self):
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_staff = True
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_superuser = True
        user.save()
        self.assertEqual(user.has_perm('auth.test'), True)
        user.is_staff = False
        user.is_superuser = False
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = False
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)

    def test_custom_perms(self):
        user = User.objects.get(username='test')
        content_type = ContentType.objects.get_for_model(Permission)
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        # default django way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)

        # reloading user to purge the _perm_cache
        user = User.objects.get(username='test')
        self.assertEqual(user.get_all_permissions() == set([u'auth.test']), True)
        self.assertEqual(user.get_group_permissions(), set([]))
        self.assertEqual(user.has_module_perms('Group'), False)
        self.assertEqual(user.has_module_perms('auth'), True)

        perm = Permission.objects.create(name='test2',
                                         content_type=content_type,
                                         codename='test2')

        # default django way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)

        perm = Permission.objects.create(name='test3',
                                         content_type=content_type,
                                         codename='test3')

        # default django  way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)

        user = User.objects.get(username='test')
        self.assertEqual(user.get_all_permissions(),
                         set([u'auth.test2', u'auth.test', u'auth.test3']))
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), True)

        perm = Permission.objects.create(name='test_group',
                                         content_type=content_type,
                                         codename='test_group')
        group = Group.objects.create(name='test_group')

        # default django way (ManyToManyField)
        #group.permissions.add(perm)

        add_permission_to_group(perm, group)

        # default django way (ManyToManyField)
        #user.groups.add(group)

        add_user_to_group(user, group)

        user = User.objects.get(username='test')
        exp = set([u'auth.test2', u'auth.test',
                   u'auth.test3', u'auth.test_group'])
        self.assertEqual(user.get_all_permissions(), exp)
        self.assertEqual(user.get_group_permissions(),
                         set([u'auth.test_group']))
        self.assertEqual(user.has_perms(['auth.test3', 'auth.test_group']),
                         True)

        user = AnonymousUser()
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), False)

    def test_has_no_object_perm(self):
        """Regressiontest for #12462"""

        user = User.objects.get(username='test')
        content_type = ContentType.objects.get_for_model(Group)
        content_type.save()
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')

        # default django way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)

        self.assertEqual(user.has_perm('auth.test', 'object'), False)
        self.assertEqual(user.get_all_permissions('object'), set([]))
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.get_all_permissions(), set(['auth.test']))

    def test_authenticate(self):
        user = User.objects.get(username='test')
        self.assertEquals(authenticate(username='test', password='test'), user)
        self.assertEquals(authenticate(username='test', password='testNones'),
                          None)

########NEW FILE########
__FILENAME__ = utils
from copy import copy

from .models import UserPermissionList, GroupPermissionList


def add_perm_to(obj, list_cls, filter):
    obj_list, created = list_cls.objects.get_or_create(**filter)
    obj_list.permission_list.append('%s.%s' % (obj.content_type.app_label,\
                                               obj.codename))
    obj_list.permission_fk_list.append(obj.id)
    obj_list.save()

def add_permission_to_user(perm, user):
    add_perm_to(perm, UserPermissionList,  {'user': user })

def add_user_to_group(user, group):
    obj_list, created = UserPermissionList.objects.get_or_create(user=user)
    obj_list.group_fk_list.append(group.id)
    obj_list.save()

def add_permission_to_group(perm, group):
    add_perm_to(perm, GroupPermissionList, {'group': group})

def update_list(perm_objs, list_cls, filter):
    """
    updates a list of permissions
    list_cls can be GroupPermissionList or UserPermissionList
    """

    list_obj, created = list_cls.objects.get_or_create(**filter)
    old_perms = copy(list_obj.permission_list)

    perm_strs = ['%s.%s' % (perm.content_type.app_label, perm.codename) \
                 for perm in perm_objs]
    perm_ids = [perm.id for perm in perm_objs]

    for perm in old_perms:
        try:
            perm_strs.index(perm)
        except ValueError:
            i = list_obj.permission_list.index(perm)
            list_obj.permission_list.pop(i)
            list_obj.permission_fk_list.pop(i)

    i = 0
    for perm in perm_strs:
        try:
            old_perms.index(perm)
        except ValueError:
            list_obj.permission_list.append(perm)
            list_obj.permission_fk_list.append(perm_ids[i])
        i += 1

    list_obj.save()

def update_permissions_user(perms, user):
    update_list(perms, UserPermissionList, {'user': user})

def update_permissions_group(perms, group):
    update_list(perms, GroupPermissionList, {'group': group})

def update_user_groups(user, groups):
    new_group_ids = [ group.id for group in groups]
    pl, created = UserPermissionList.objects.get_or_create(user=user)
    old_group_ids = copy(pl.group_fk_list)

    for group_id in old_group_ids:
        try:
            new_group_ids.index(group_id)
        except ValueError:
            pl.group_fk_list.remove(group_id)

    for group_id in new_group_ids:
        try:
            old_group_ids.index(group_id)
        except ValueError:
            pl.group_fk_list.append(group_id)

    pl.save()

########NEW FILE########
