__FILENAME__ = backends
# -*- coding: utf-8 -*-
import inspect

from exceptions import NotBooleanPermission
from exceptions import NonexistentFieldName

from rulez import registry

class ObjectPermissionBackend(object):
    supports_object_permissions = True
    supports_anonymous_user = True
    supports_inactive_user = True

    def authenticate(self, username, password): # pragma: no cover
        return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        This method checks if the user_obj has perm on obj. Returns True or False
        Looks for the rule with the code_name = perm and the content_type of the obj
        If it exists returns the value of obj.field_name or obj.field_name() in case
        the field is a method.
        """
        if user_obj and not user_obj.is_anonymous() and not user_obj.is_active:
            # inactive users never have permissions
            return False

        if obj is None:
            return False

        # We get the rule data from our registry
        rule = registry.get(perm, obj.__class__)
        if rule == None:
            return False

        bound_field = None
        try:
            bound_field = getattr(obj, rule.field_name)
        except AttributeError:
            raise NonexistentFieldName(
                "Field_name %s from rule %s does not longer exist in model %s. \
                The rule is obsolete!", (rule.field_name,
                                         rule.codename,
                                         rule.model))

        if not callable(bound_field):
            raise NotBooleanPermission(
                "Attribute %s from model %s on rule %s is not callable",
                (rule.field_name, rule.model, rule.codename))

        # Otherwise it is a callabe bound_field
        # Let's see if we pass or not user_obj as a parameter
        if (len(inspect.getargspec(bound_field)[0]) == 2):
            is_authorized = bound_field(user_obj)
        else:
            is_authorized = bound_field()

        if not isinstance(is_authorized, bool):
            raise NotBooleanPermission(
                "Callable %s from model %s on rule %s does not return a \
                boolean value", (rule.field_name, rule.model, rule.codename))

        return is_authorized

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""
Exceptions used by django-rules. All internal and rules-specific errors
should extend RulesError class
"""

class RulesException(Exception):
    pass


class NonexistentPermission(RulesException):
    pass


class NonexistentFieldName(RulesException):
    pass


class NotBooleanPermission(RulesException):
    pass

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import rolez.signals
########NEW FILE########
__FILENAME__ = registry
# -*- coding: utf-8 -*-
from rulez.exceptions import NonexistentFieldName
from collections import defaultdict


class Rule(object):
    def __init__(self, codename, model, field_name='', view_param_pk='',
                 description=''):
        self.field_name = field_name
        self.description = description
        self.codename = codename
        self.model = model
        self.view_param_pk = view_param_pk


registry = defaultdict(dict)


def register(codename, model, field_name='', view_param_pk='', description=''):
    """
    This should be called from your models.py or wherever after your models are
    declared (think admin registration)
    """

    # Sanity check
    if not field_name:
        field_name = codename

    if not hasattr(model,field_name):
        raise NonexistentFieldName('Field %s does not exist on class %s' % (field_name,model.__name__))

    registry[model].update({codename  : Rule(codename, model, field_name,
                                             view_param_pk, description)})


def get(codename, model):
    return registry.get(model, {}).get(codename, None)

########NEW FILE########
__FILENAME__ = base
#-*- coding: utf-8 -*-

class AbstractRole(object):
    """
    This is an abstract class to show what a role should look like
    """
    @classmethod
    def is_member(cls, user, obj): #pragma: nocover
        raise NotImplemented

########NEW FILE########
__FILENAME__ = cache_helper
#-*- coding: utf-8 -*-

from django.contrib.auth.models import User, AnonymousUser
from django.core.cache import cache
from rulez.exceptions import RulesException
import time

"""
Cache keys:

For the list of roles, per user, per instance:
<prefix>-<user.id>-<user counter>-<obj.type>-<obj.id>-<obj counter>

For the counter , per instance:
<prefix>-<obj.type>-<obj.id>

"""

HOUR = 60*60

#===============================================================================
# Counter handling
#===============================================================================
def counter_key(obj):
    if obj.__class__ in (User, AnonymousUser,):
        pk = get_user_pk(obj)
    else:
        pk = obj.pk
    obj_type = str(obj.__class__.__name__).lower()
    return "%s-%s" % (obj_type, pk)


def increment_counter(obj):
    """
    Invalidate the cache for the passed object.
    """
    if obj is not None: # If the object is None, do nothing (it's pointless)
        cache.set(counter_key(obj), int(time.time()), 1*HOUR)


def get_counter(obj):
    """
    Returns the cached counter for the given object instance
    """
    counter = cache.get(counter_key(obj))
    if not counter:
        counter = 0
    return counter


def roles_key(user, obj):
    if obj.__class__ in (User, AnonymousUser,):
        obj_id = get_user_pk(obj)
    else:
        obj_id = obj.pk
    obj_type = str(obj.__class__.__name__).lower()
    obj_counter = get_counter(obj)
    user_id = get_user_pk(user)
    user_counter = get_counter(user)
    return "%s-%s-%s-%s-%s" % (user_id, user_counter, obj_type, obj_id,
                               obj_counter)


def get_user_pk(user):
    if not user or (user and user.is_anonymous()):
        return 'anonymous'
    else:
        return user.pk

#===============================================================================
# Main function
#===============================================================================

def get_roles(user, obj):
    """
    Get a list of roles assigned to a user for a specific instance from the
    cache, or builds such a list if it is not found.
    """
    # get roles for the user, if present:
    roles = cache.get(roles_key(user, obj))
    if isinstance(roles, list):
        # Cache hit (a miss returns NoneType rather than an empty list)
        return roles
    else:
        # we need to recompute roles for this model
        user_roles = []
        if not hasattr(obj, 'relevant_roles'):
            raise RulesException(
                'Cannot build roles cache for %s instance. Did you forget to \
                define a "relevant_roles()" method on %s?' % (obj.__class__,
                                                              obj.__class__))

        relevant = obj.relevant_roles()
        for role in relevant:
            if role.is_member(user, obj):
                user_roles.append(role)
        cache.set(roles_key(user, obj), user_roles, 1*HOUR)
        return user_roles

########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
from rulez.rolez.cache_helper import get_roles, get_user_pk, increment_counter


class ModelRoleMixin(object):
    """
    This adds roles-handling methods to the model it's mixed with
    """

    def get_roles(self, user):
        """
        Gets all roles this user has for this object and caches it on the
        instance.
        Without the instance cache every call to has_role() would hit the
        cache backend.
        """
        rolez = getattr(self, '_rolez', {})
        pk = get_user_pk(user)
        if not pk in rolez.keys():
            rolez[pk] = get_roles(user, self)
        self._rolez = rolez
        return self._rolez[pk]

    def has_role(self, user, role):
        """
        Checks wether the passed user is a member of the passed role for the
        passed instance
        """
        roles = self.get_roles(user)
        if role in roles:
            return True
        return False

    def relevant_roles(self):
        """
        Returns a list of roles *classes* relevant to this instance type.
        This is to optimise the building of the user's roles in case of cache 
        miss
        """
        return self.roles

    def rulez_invalidate(self):
        """
        This is the default, simple case where the model is related to user, and
        so invalidating it will force connected users to recalculate their keys

        In some cases you will want to invalidate the related objects here by 
        incrementing counters for other models in your application
        """
        increment_counter(self)

########NEW FILE########
__FILENAME__ = signals
#-*- coding: utf-8 -*-
from django.db.models import signals


def should_we_invalidate_rolez(sender, instance, **kwargs):
    if hasattr(instance, 'rulez_invalidate'):
        instance.rulez_invalidate()


signals.post_save.connect(should_we_invalidate_rolez)
signals.post_delete.connect(should_we_invalidate_rolez)

########NEW FILE########
__FILENAME__ = rulez_perms
from django import template

register = template.Library()

class RulezPermsNode(template.Node):
    def __init__(self, codename, objname, varname):
        self.codename = codename
        self.objname = objname
        self.varname = varname

    def render(self, context):
        user_obj = template.resolve_variable('user', context)
        obj = template.resolve_variable(self.objname, context)
        context[self.varname] = user_obj.has_perm(self.codename, obj)
        return ''

def rulez_perms(parser, token):
    '''
    Template tag to check for permission against an object.
    Built out of a need to use permissions with anonymous users at an
    object level.

    Usage:
        {% load rulez_perms %}

        {% for VARNAME in QUERYRESULT %}
            {% rulez_perms CODENAME VARNAME as BOOLEANVARNAME %}
            {% if BOOLEANVARNAME %}
                I DO
            {% else %}
                I DON'T
            {% endif %}
            have permission for {{ VARNAME }}.{{ CODENAME }}!!
        {% endfor %}
    '''
    bits = token.split_contents()
    if len(bits) != 5:
        raise template.TemplateSyntaxError(
            'tag requires exactly three arguments')
    if bits[3] != 'as':
        raise template.TemplateSyntaxError(
            "third argument to tag must be 'as'")
    return RulezPermsNode(bits[1], bits[2], bits[4])

rulez_perms = register.tag(rulez_perms)

########NEW FILE########
__FILENAME__ = backend
#-*- coding: utf-8 -*-
from django.test.testcases import TestCase
from rulez import registry
from rulez.backends import ObjectPermissionBackend
from rulez.exceptions import NonexistentFieldName, NotBooleanPermission
from rulez.registry import Rule


class MockModel():
    pk = 999
    not_callable = 'whatever'

    def __init__(self):
        self.attr_permission = True
        self.attr_wrong_permission = "I'm not a boolean"

    def mock_permission(self, user):
        return True

    def mock_simple_permission(self):
        # just a callable, no "user" parameter
        return True

    def mock_non_boolean_permission(self, user):
        return "Whatever"


class MockUser():
    def __init__(self, is_active=True):
        self.pk=666
        self.is_active = is_active
    def is_anonymous(self):
        return False


class BackendTestCase(TestCase):

    def create_fixtures(self):
        self.user = MockUser()
        self.inactive_user = MockUser(is_active=False)
        self.model = MockModel()

    def test_user_is_tested_for_rule(self):
        self.create_fixtures()
        registry.register('mock_permission', MockModel)
        back = ObjectPermissionBackend()
        res = back.has_perm(self.user, 'mock_permission', self.model)
        self.assertEqual(res, True)

    def test_rules_returns_False_for_None_obj(self):
        self.create_fixtures()
        registry.register('mock_permission', MockModel)
        back = ObjectPermissionBackend()
        res = back.has_perm(self.user, 'mock_permission', None)
        self.assertEqual(res, False)

    def test_rules_returns_False_for_inexistant_rule(self):
        self.create_fixtures()
        registry.register('mock_permission', MockModel)
        back = ObjectPermissionBackend()
        res = back.has_perm(self.user, 'whatever_permission', self.model)
        self.assertEqual(res, False)

    def test_user_is_tested_for_simple_rule(self):
        self.create_fixtures()
        registry.register('mock_simple_permission', MockModel)
        back = ObjectPermissionBackend()
        res = back.has_perm(self.user, 'mock_simple_permission', self.model)
        self.assertEqual(res, True)

    def test_user_is_tested_for_simple_rule_by_field_name(self):
        self.create_fixtures()
        registry.register(
            'mock_permission', MockModel, field_name='mock_simple_permission')
        back = ObjectPermissionBackend()
        res = back.has_perm(self.user, 'mock_permission', self.model)
        self.assertEqual(res, True)

    def test_non_existant_filenames_are_caught(self):
        self.create_fixtures()
        codename = 'mock_permission'
        rule = Rule(codename, MockModel, field_name='I_do_not_exist')
        registry.registry[MockModel].update({codename : rule})
        back = ObjectPermissionBackend()
        self.assertRaises(
            NonexistentFieldName, back.has_perm, self.user, 'mock_permission',
            self.model)

    def test_inactive_user_can_never_have_any_permissions(self):
        self.create_fixtures()
        registry.register('mock_permission', MockModel)
        back = ObjectPermissionBackend()
        res = back.has_perm(self.inactive_user, 'mock_permission', self.model)
        self.assertEqual(res, False)

    def test_non_boolean_permissions_raises(self):
        self.create_fixtures()
        registry.register('mock_non_boolean_permission', MockModel)
        back = ObjectPermissionBackend()
        self.assertRaises(
            NotBooleanPermission, back.has_perm, self.user,
            'mock_non_boolean_permission', self.model)

    def test_non_callable_permission_raises(self):
        self.create_fixtures()
        registry.register('not_callable', MockModel)
        back = ObjectPermissionBackend()
        self.assertRaises(
            NotBooleanPermission, back.has_perm, self.user,
            'not_callable', self.model)

########NEW FILE########
__FILENAME__ = registry
#-*- coding: utf-8 -*-
from django.test.testcases import TestCase
from rulez import registry
from rulez.exceptions import NonexistentFieldName


class MockModel():
    pk = 999

    def mock_permission(self):
        return True


class MockUser():
    def __init__(self):
        self.pk=666
    def is_anonymous(self):
        return False


class RegistryTestCase(TestCase):
    def test_rule_is_registered(self):
        registry.register('mock_permission', MockModel)
        # if it's been registered properly we should be able to get() something
        res = registry.get('mock_permission', MockModel)
        self.assertNotEqual(res, None)
        self.assertNotEqual(res, {})

    def test_registration_raises_non_existant_field_names(self):
        self.assertRaises(NonexistentFieldName, registry.register,
            'mock_permission', MockModel, field_name='inexistant'
        )

########NEW FILE########
__FILENAME__ = roles_helpers
#-*- coding: utf-8 -*-
from __future__ import with_statement
from django.contrib.auth.models import AnonymousUser, User
from django.core import cache
from django.test.testcases import TestCase
from rulez.exceptions import RulesException
from rulez.rolez.base import AbstractRole
from rulez.rolez.cache_helper import get_counter, increment_counter, get_roles, \
    get_user_pk, roles_key
from rulez.rolez.models import ModelRoleMixin


class Mock():
    pk = 999


class MockUser():
    def __init__(self):
        self.pk=666
    def is_anonymous(self):
        return False


# Testing the model inheritence
class Tester(AbstractRole):
    @classmethod
    def is_member(cls, user, obj):
        return getattr(user, 'member', False)


class TestModel(ModelRoleMixin):
    pk = 1 # Just to emulate a Django model
    roles = [Tester]


# The actual test case
class RolesCacheHelperTestCase(TestCase):

    def setUp(self):
        cache.cache.clear()

    def test_incrementing_counter_works(self):
        obj = Mock()
        first = get_counter(obj)
        self.assertEqual(first, 0)
        increment_counter(obj)
        second = get_counter(obj)
        self.assertNotEqual(second, first)

    def test_incrementing_counter_works_for_none(self):
        increment_counter(None)

    def test_get_roles_for_None_raises(self):
        with self.assertRaises(AttributeError):
            res = get_counter(None)
            self.assertEqual(res, None)

    def test_rulez_invalidate_works(self):
        model = TestModel()
        user = MockUser()
        first = get_counter(model)
        self.assertEqual(first, 0)
        model.rulez_invalidate()
        second = get_counter(model)
        self.assertNotEqual(second, first)

    def test_get_empty_roles_works(self):
        model = TestModel()
        user = MockUser()
        res = get_roles(user, model)
        self.assertEqual(res, [])

    def test_user_with_role_works(self):
        # Now let's make the user a member!
        model = TestModel()
        user = MockUser()
        setattr(user, 'member', True)
        res = get_roles(user, model)
        self.assertEqual(len(res), 1)

    def test_get_roles_cache_works(self):
        # Now let's assert the cache works.
        model = TestModel()
        user = MockUser()
        setattr(user, 'member', True)
        res = get_roles(user, model)
        self.assertEqual(len(res), 1)
        res2 = get_roles(user, model)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res, res2)

    def test_has_role_works(self):
        model = TestModel()
        user = MockUser()
        setattr(user, 'member', True)
        res = model.has_role(user, Tester)
        self.assertEqual(res, True)

    def test_has_role_caches_on_instance(self):
        model = TestModel()
        user = MockUser()
        setattr(user, 'member', True)
        self.assertFalse(hasattr(model, "_rolez"))
        res = model.has_role(user, Tester)
        self.assertEqual(res, True)
        self.assertTrue(hasattr(model, "_rolez"))
        self.assertEqual(1, len(model._rolez))
        res = model.has_role(user, Tester)
        self.assertEqual(res, True)
        self.assertTrue(hasattr(model, "_rolez"))
        self.assertEqual(1, len(model._rolez))

    def test_doesnt_have_role_works(self):
        model = TestModel()
        user = MockUser()
        res = model.has_role(user, Tester)
        self.assertEqual(res, False)

    def test_get_anonymous_user_works(self):
        anon = AnonymousUser()
        res = get_user_pk(anon)
        self.assertEqual(res, 'anonymous')

    def test_get_roles_works_for_anonymous(self):
        model = TestModel()
        user = AnonymousUser()
        res = model.has_role(user, Tester)
        self.assertEqual(res, False)

    def test_get_counter_does_not_return_spaces(self):
        obj = Mock()
        user = MockUser()
        roles_key(user, obj) # The first time, the counter == 0
        increment_counter(obj) # Now there should be a timestamp
        res = roles_key(user, obj)
        self.assertTrue(' ' not in res)

    def test_roles_for_users_on_users_raises_without_relevant_roles(self):
        # If for some reasons you want to enforce rules on users...
        django_user = User.objects.create(username="test",
                                          email="test@example.com",
                                          first_name="Test",
                                          last_name = "Tester")
        user = MockUser() # That's faster
        setattr(user, 'member', True)
        with self.assertRaises(RulesException):
            res = get_roles(user, django_user)
            self.assertEqual(len(res), 1)

    def test_roles_for_users_on_users_works_with_relevant_roles(self):
        # If for some reasons you want to enforce rules on users...
        django_user = User.objects.create(username="test",
                                          email="test@example.com",
                                          first_name="Test",
                                          last_name = "Tester")
        setattr(django_user, 'relevant_roles', lambda : [Tester])
        user = MockUser() # That's faster
        setattr(user, 'member', True)
        res = get_roles(user, django_user)
        self.assertEqual(len(res), 1)

########NEW FILE########
__FILENAME__ = signals
#-*- coding: utf-8 -*-
from django.test.testcases import TestCase
from rulez.rolez.signals import should_we_invalidate_rolez

class MockInstance(object):
    def __init__(self):
        self.called = False
    def rulez_invalidate(self):
        self.called = True

class SignalsTestCase(TestCase):
    def test_handling_forwards_properly(self):
        inst = MockInstance()
        should_we_invalidate_rolez(self, inst)
        self.assertEqual(inst.called, True)
########NEW FILE########
__FILENAME__ = templatetags
#-*- coding: utf-8 -*-

from django.test.testcases import TestCase
from django.contrib.auth.models import AnonymousUser, User
from django.template import Template, Context, TemplateSyntaxError

from rulez import registry
from rulez.tests.backend import MockUser


class MockModel(object):
    pk = 999

    def mock_positive_permission(self, user):
        return True

    def mock_negative_permission(self, user):
        return False


class TemplatetagTestCase(TestCase):

    def create_fixtures(self):
        self.user = MockUser()
        self.inactive_user = MockUser(is_active=False)
        self.model = MockModel()

    def render_template(self, template, context):
        context = Context(context)
        return Template(template).render(context)

    def assertYesHeCan(self, permission, user):
        registry.register(permission, MockModel)
        rendered = self.render_template(
            "{% load rulez_perms %}"
            "{% rulez_perms " + permission + " object as can %}"
            "{% if can %}yes he can{% else %}no can do{% endif %}",
            {
                "user": user,
                "object": MockModel()
            }
        )
        self.assertEqual(rendered, "yes he can")

    def assertNoHeCant(self, permission, user):
        registry.register(permission, MockModel)
        rendered = self.render_template(
            "{% load rulez_perms %}"
            "{% rulez_perms " + permission + " object as can %}"
            "{% if can %}yes he can{% else %}no he can't{% endif %}",
            {
                "user": user,
                "object": MockModel()
            }
        )
        self.assertEqual(rendered, "no he can't")

    def test_active_user_against_positive_permission(self):
        self.assertYesHeCan("mock_positive_permission", User(is_active=True))

    def test_active_user_for_negative_permission(self):
        self.assertNoHeCant("mock_negative_permission", User(is_active=True))

    def test_inactive_user_against_positive_permission(self):
        self.assertNoHeCant("mock_positive_permission", User(is_active=False))

    def test_inactive_user_against_negative_permission(self):
        self.assertNoHeCant("mock_negative_permission", User(is_active=False))

    def test_anonymous_user_against_positive_permission(self):
        self.assertYesHeCan("mock_positive_permission", AnonymousUser())

    def test_anonymous_user_against_negative_permission(self):
        self.assertNoHeCant("mock_negative_permission", AnonymousUser())

    def test_active_user_against_missing_permission(self):
        permission = "missing"
        rendered = self.render_template(
            "{% load rulez_perms %}"
            "{% rulez_perms " + permission + " object as can %}"
            "{% if can %}yes he can{% else %}no he can't{% endif %}",
            {
                "user": User(is_active=True),
                "object": MockModel()
            }
        )
        self.assertEqual(rendered, "no he can't")

    def test_invalid_user(self):
        self.assertRaisesRegexp((TemplateSyntaxError, AttributeError),
            "'NoneType' object has no attribute 'has_perm'",
            self.render_template,
            "{% load rulez_perms %}{% rulez_perms mock_positive_permission object as can %}", {
                "object": MockModel(), "user": None
            })

    def test_tag_syntax(self):
        registry.register("mock_positive_permission", MockModel)

        # TODO: error messages from template tag a bit are confusing.
        self.assertRaisesRegexp(TemplateSyntaxError, "tag requires exactly three arguments", self.render_template,
            "{% load rulez_perms %}{% rulez_perms mock_positive_permission object %}", {})

        self.assertRaisesRegexp(TemplateSyntaxError, "tag requires exactly three arguments", self.render_template,
            "{% load rulez_perms %}{% rulez_perms mock_positive_permission object can %}", {})

        self.assertRaisesRegexp(TemplateSyntaxError, "third argument to tag must be 'as'", self.render_template,
            "{% load rulez_perms %}{% rulez_perms mock_positive_permission object can can %}", {})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp

#Added for test runner
import os, sys
sys.path.insert(0, os.path.abspath('./../../'))

try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

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
# Django settings for testapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.database',                      # Or path to database file if using sqlite3.
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

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = 'o(ifwru@r&@i!g!%_w85_*oveey7iq3hoq1hfvd^e6(25gd+t2'

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

ROOT_URLCONF = 'testapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'rulez', # The actual rulez package
    'project', # import the test app too
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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

AUTHENTICATION_BACKENDS = [
    "rulez.backends.ObjectPermissionBackend",
]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^testapp/', include('testapp.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
