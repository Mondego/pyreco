__FILENAME__ = backends
# -*- coding: utf-8 -*-
import inspect

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, AnonymousUser
from django.utils.importlib import import_module

from models import RulePermission
from exceptions import NotBooleanPermission
from exceptions import NonexistentFieldName
from exceptions import NonexistentPermission
from exceptions import RulesError


class ObjectPermissionBackend(object):
    supports_object_permissions = True
    supports_anonymous_user = True
    supports_inactive_user = True

    def authenticate(self, username, password):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        This method checks if the user_obj has perm on obj. Returns True or False
        Looks for the rule with the code_name = perm and the content_type of the obj
        If it exists returns the value of obj.field_name or obj.field_name() in case
        the field is a method.
        """
        
        if obj is None:
            return False

        if not user_obj.is_authenticated():
            user_obj = User.objects.get(pk=settings.ANONYMOUS_USER_ID)

        # Centralized authorizations
        # You need to define a module in settings.CENTRAL_AUTHORIZATIONS that has a 
        # central_authorizations function inside
        if hasattr(settings, 'CENTRAL_AUTHORIZATIONS'):
            module = getattr(settings, 'CENTRAL_AUTHORIZATIONS')

            try:
                mod = import_module(module)
            except ImportError, e:
                raise RulesError('Error importing central authorizations module %s: "%s"' % (module, e))

            try:
                central_authorizations = getattr(mod, 'central_authorizations')
            except AttributeError:
                raise RulesError('Error module %s does not have a central_authorization function"' % (module))
            
            try:
                is_authorized = central_authorizations(user_obj, perm)
                # If the value returned is a boolean we pass it up and stop checking 
                # If not, we continue checking
                if isinstance(is_authorized, bool):
                    return is_authorized

            except TypeError:
                raise RulesError('central_authorizations should receive 2 parameters: (user_obj, perm)')

        # Note:
        # is_active and is_superuser are checked by default in django.contrib.auth.models
        # lines from 301-306 in Django 1.2.3
	# If this checks dissapear in mainstream, tests will fail, so we won't double check them :)
        ctype = ContentType.objects.get_for_model(obj)

        # We get the rule data and return the value of that rule
        try:
            rule = RulePermission.objects.get(codename = perm, content_type = ctype)
        except RulePermission.DoesNotExist:
            return False

        bound_field = None
        try:
            bound_field = getattr(obj, rule.field_name)
        except AttributeError:
            raise NonexistentFieldName("Field_name %s from rule %s does not longer exist in model %s. \
                                        The rule is obsolete!", (rule.field_name, rule.codename, rule.content_type.model))

        if not isinstance(bound_field, bool) and not callable(bound_field):
            raise NotBooleanPermission("Attribute %s from model %s on rule %s does not return a boolean value",
                                        (rule.field_name, rule.content_type.model, rule.codename))

        if not callable(bound_field):
            is_authorized = bound_field
        else:
            # Otherwise it is a callabe bound_field
            # Let's see if we pass or not user_obj as a parameter
            if (len(inspect.getargspec(bound_field)[0]) == 2):
                is_authorized = bound_field(user_obj)
            else:
                is_authorized = bound_field()

            if not isinstance(is_authorized, bool):
                raise NotBooleanPermission("Callable %s from model %s on rule %s does not return a boolean value",
                                            (rule.field_name, rule.content_type.model, rule.codename))

        return is_authorized

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404
from django.utils.http import urlquote
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.utils.functional import wraps
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import NoReverseMatch, reverse

from exceptions import RulesError
from exceptions import NonexistentPermission
from models import RulePermission
from backends import ObjectPermissionBackend


def object_permission_required(perm, **kwargs):
    """
    Decorator for views that checks whether a user has a particular permission

    The view needs to have a parameter name that matches rule's view_param_pk.
    The value of this parameter will be taken as the primary key of the model.

    :param login_url: if denied, user would be redirected to location set by
      this parameter. Defaults to ``django.conf.settings.LOGIN_URL``.
    :param redirect_field_name: name of the parameter passed if redirected.
      Defaults to ``django.contrib.auth.REDIRECT_FIELD_NAME``.
    :param return_403: if set to ``True`` then instead of redirecting to the
      login page, response with status code 403 is returned (
      ``django.http.HttpResponseForbidden`` instance). Defaults to ``False``.

    Examples::

        # RulePermission.objects.get_or_create(codename='can_ship',...,view_param_pk='paramView')
        @permission_required('can_ship', return_403=True)
        def my_view(request, paramView):
            return HttpResponse('Hello')

    """

    login_url = kwargs.pop('login_url', settings.LOGIN_URL)
    redirect_url = kwargs.pop('redirect_url', "")
    redirect_field_name = kwargs.pop('redirect_field_name', REDIRECT_FIELD_NAME)
    return_403 = kwargs.pop('return_403', False)

    # Check if perm is given as string in order to not decorate
    # view function itself which makes debugging harder
    if not isinstance(perm, basestring):
        raise RulesError("First argument, permission, must be a string")

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            obj = None
            
            try:
                rule = RulePermission.objects.get(codename = perm)
            except RulePermission.DoesNotExist:
                raise NonexistentPermission("Permission %s does not exist" % perm)

            # Only look in kwargs, if the views are entry points through urls Django passes parameters as kwargs
            # We could look in args using  inspect.getcallargs in Python 2.7 or a custom function that 
            # imitates it, but if the view is internal, I think it's better to force the user to pass 
            # parameters as kwargs
            if rule.view_param_pk not in kwargs: 
                raise RulesError("The view does not have a parameter called %s in kwargs" % rule.view_param_pk)
                
            model_class = rule.content_type.model_class()
            obj = get_object_or_404(model_class, pk=kwargs[rule.view_param_pk])

            if not request.user.has_perm(perm, obj):
                if return_403:
                    return HttpResponseForbidden()
                else:
                    if redirect_url:
                        try:
                            path = urlquote(request.get_full_path())
                            redirect_url_reversed = reverse(redirect_url)
                            tup = redirect_url_reversed, redirect_field_name, path
                        except NoReverseMatch:
                            tup = redirect_url, redirect_field_name, path
                    else:
                        path = urlquote(request.get_full_path())
                        tup = login_url, redirect_field_name, path

                    return HttpResponseRedirect("%s?%s=%s" % tup)
            return view_func(request, *args, **kwargs)
        return wraps(view_func)(_wrapped_view)
    return decorator

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""
Exceptions used by django-rules. All internal and rules-specific errors
should extend RulesError class
"""

class RulesError(Exception):
    pass

class NonexistentPermission(RulesError):
    pass

class NonexistentFieldName(RulesError):
    pass

class NotBooleanPermission(RulesError):
    pass

########NEW FILE########
__FILENAME__ = sync_rules
# -*- coding: utf-8 -*-
import sys, os
import imp
from optparse import make_option

from django.conf import settings
from django.utils.importlib import import_module
from django.core.management import call_command
from django.core.management import BaseCommand
from django.db import connections


def import_app(app_label, verbosity):
    # We get the app_path, necessary to use imp module find function
    try:
        app_path = __import__(app_label, {}, {}, [app_label.split('.')[-1]]).__path__
    except AttributeError:
        return
    except ImportError:
        print "Unknown application: %s" % app_label
        print "Stopping synchronization"
        sys.exit(1)
   
    # imp.find_module looks for rules.py within the app
    # It does not import the module, but raises and ImportError
    # if rules.py does not exist, so we continue to next app
    try:
        imp.find_module('rules', app_path)
    except ImportError:
        return

    if verbosity >= 1:
        sys.stderr.write('Syncing rules from %s\n' % app_label)
    
    # Now we import the module, this should bubble up errors
    # if there are any in rules.py Warning the user
    generator = import_module('.rules', app_label)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--fixture", action='store_true', dest="fixture", default=False,
                   help="Generate a fixture of django_rules"),
    )
    help = 'Syncs into database all rules defined in rules.py files'
    args = '[appname ...]'

    def handle(self, *app_labels, **options):
        verbosity = int(options.pop('verbosity', 1))
        fixture = options.pop('fixture')

        if len(app_labels) == 0:
            # We look for a rules.py within every app in INSTALLED_APPS
            # We sync the rules_list against RulePermissions
            for app_label in settings.INSTALLED_APPS:
                import_app(app_label, verbosity)
        else:
            for app_label in app_labels:
                import_app(app_label, verbosity)

        if fixture:
            for alias in connections._connections:
                call_command("dumpdata",
                         'django_rules.rulepermission',
                        **dict(options, verbosity=0, database=alias))

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import inspect
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.contenttypes.models import ContentType

from exceptions import NonexistentFieldName
from exceptions import RulesError


class RulePermission(models.Model):
    """
    This model holds the rules for the authorization system
    """
    codename = models.CharField(primary_key=True, max_length=30)
    field_name = models.CharField(max_length=30)
    content_type = models.ForeignKey(ContentType)
    view_param_pk = models.CharField(max_length=30)
    description = models.CharField(max_length=140, null=True)


    def save(self, *args, **kwargs):
        """
        Validates that the field_name exists in the content_type model
        raises ValidationError if it doesn't. We need to restrict security rules creation
        """
        # If not set use codename as field_name as default
        if self.field_name == '':
            self.field_name = self.codename

        # If not set use primary key attribute name as default
        if self.view_param_pk == '':
            self.view_param_pk = self.content_type.model_class()._meta.pk.get_attname()

        # First search for a method or property defined in the model class
        # Then we look in the meta field_names
        # If field_name does not exist a ValidationError is raised
        if not hasattr(self.content_type.model_class(), self.field_name):
            # Search within attributes field names
            if not (self.field_name in self.content_type.model_class()._meta.get_all_field_names()):
                raise NonexistentFieldName("Could not create rule: field_name %s of rule %s does not exist in model %s" %
                                            (self.field_name, self.codename, self.content_type.model))
        else:
            # Check if the method parameters are less than 2 including self in the count
            bound_field = getattr(self.content_type.model_class(), self.field_name)
            if callable(bound_field):
                if len(inspect.getargspec(bound_field)[0]) > 2:
                    raise RulesError("method %s from rule %s in model %s has too many parameters." %
                                        (self.field_name, self.codename, self.content_type.model))
        
        super(RulePermission, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User

class Dummy(models.Model):
    """
    Dummy model for testing permissions
    """
    idDummy = models.AutoField(primary_key = True)
    supplier = models.ForeignKey(User, null = False)
    name = models.CharField(max_length = 20, null = True)

    def canShip(self,user_obj):
        """
        Only the supplier can_ship in our business logic.
        Checks if the user_obj passed is the supplier.
        """
        return self.supplier == user_obj

    @property
    def isDisposable(self):
        """
        It should check some attributes to see if 
        package is disposable
        """
        return True

    def canTrash(self):
        """
        Methods can either have a user_obj parameter
        or no parameters
        """
        return True

    def methodInteger(self):
        """
        This method does not return a boolean value
        """
        return 2

    def invalidNumberParameters(self, param1, param2):
        """
        This method has too many parameters for being a rule
        """
        pass
        


########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
parent = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))

sys.path.insert(0, parent)

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

def runtests():
    DjangoTestSuiteRunner(failfast=False).run_tests([
        'django_rules.BackendTest',
        'django_rules.RulePermissionTest',
        'django_rules.UtilsTest',
        'django_rules.DecoratorsTest'
        ], verbosity=1, interactive=True)

if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = test_core
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.conf import settings

from django_rules.models import RulePermission
from models import Dummy
from django_rules.exceptions import NonexistentFieldName
from django_rules.exceptions import NotBooleanPermission
from django_rules.exceptions import NonexistentPermission
from django_rules.exceptions import RulesError
from django_rules import utils

class BackendTest(TestCase):
    def setUp(self):
        try:
            self.anonymous = User.objects.get_or_create(id=settings.ANONYMOUS_USER_ID, username='anonymous', is_active=True)[0]
        except Exception:
            self.fail("You need to define an ANONYMOUS_USER_ID in your settings file")
        
        self.user = User.objects.get_or_create(username='javier', is_active=True)[0]
        self.otherUser = User.objects.get_or_create(username='juan', is_active=True)[0]
        self.superuser = User.objects.get_or_create(username='miguel', is_active=True, is_superuser=True)[0]
        self.not_active_superuser = User.objects.get_or_create(username='rebeca', is_active=False, is_superuser=True)[0]
        self.obj = Dummy.objects.get_or_create(supplier=self.user)[0]
        self.ctype = ContentType.objects.get_for_model(self.obj)
        
        self.rule = RulePermission.objects.get_or_create(codename='can_ship', field_name='canShip', content_type=self.ctype, view_param_pk='idDummy',
                                            description="Only supplier have the authorization to ship")[0]

    
    def test_regularuser_has_perm(self):
        self.assertTrue(self.user.has_perm('can_ship', self.obj))
    
    def test_regularuser_has_not_perm(self):
        self.assertFalse(self.otherUser.has_perm('can_ship', self.obj))
    
    def test_regularuser_has_property_perm(self):
        """
        Checks that the backend can work with properties
        """
        RulePermission.objects.get_or_create(codename='can_trash', field_name='isDisposable', content_type=self.ctype, view_param_pk='idDummy',
                                            description="Checks if a user can trash a package")

        try:
            self.user.has_perm('can_trash',self.obj)
        except:
            self.fail("Something when wrong when checking a property rule")
        
    def test_superuser_has_perm(self):
        self.assertTrue(self.superuser.has_perm('invented_perm', self.obj))

    def test_object_none(self):
        self.assertFalse(self.user.has_perm('can_ship'))
    
    def test_anonymous_user(self):
        anonymous_user = AnonymousUser()
        self.assertFalse(anonymous_user.has_perm('can_ship', self.obj))

    def test_not_active_superuser(self):
        self.assertFalse(self.not_active_superuser.has_perm('can_ship', self.obj))

    def test_nonexistent_perm(self):
        self.assertFalse(self.user.has_perm('nonexistent_perm', self.obj))

    def test_nonboolean_attribute(self):
        RulePermission.objects.get_or_create(codename='wrong_rule', field_name='name', content_type=self.ctype, view_param_pk='idDummy',
                                            description="Wrong rule. The field_name exists so It is created, but it does not return True or False")
        
        self.assertRaises(NotBooleanPermission, lambda:self.user.has_perm('wrong_rule', self.obj))

    def test_nonboolean_method(self):
        RulePermission.objects.get_or_create(codename='wrong_rule', field_name='methodInteger', content_type=self.ctype, view_param_pk='idDummy',
                                            description="Wrong rule. The field_name exists so It is created, but it does not return True or False")
        
        self.assertRaises(NotBooleanPermission, lambda:self.user.has_perm('wrong_rule', self.obj))
    
    def test_nonexistent_field_name(self):
        # Dinamycally removing canShip from class Dummy to test an already existent rule that doesn't have a valid field_name anymore
        fun = Dummy.canShip
        del Dummy.canShip
        self.assertRaises(NonexistentFieldName, lambda:self.user.has_perm('can_ship', self.obj))
        Dummy.canShip = fun

    def test_has_perm_method_no_parameters(self):
        RulePermission.objects.get_or_create(codename='canTrash', field_name='canTrash', content_type=self.ctype, view_param_pk='idDummy',
                                            description="Rule created from a method that gets no parameters")

        self.assertTrue(self.user.has_perm('canTrash', self.obj))

    def test_central_authorizations_right_module_checked_within(self):
        settings.CENTRAL_AUTHORIZATIONS = 'utils'
        self.assertTrue(self.otherUser.has_perm('all_can_pass', self.obj))
        del settings.CENTRAL_AUTHORIZATIONS

    def test_central_authorizations_right_module_passes_over(self):
        settings.CENTRAL_AUTHORIZATIONS = 'utils'
        self.assertFalse(self.otherUser.has_perm('can_ship', self.obj))
        del settings.CENTRAL_AUTHORIZATIONS

    def test_central_authorizations_wrong_module(self):
        settings.CENTRAL_AUTHORIZATIONS = 'noexistent'
        self.assertRaises(RulesError, lambda:self.user.has_perm('can_ship', self.obj))
        del settings.CENTRAL_AUTHORIZATIONS

    def test_central_authorizations_right_module_nonexistent_function(self):
        settings.CENTRAL_AUTHORIZATIONS = 'utils2'
        self.assertRaises(RulesError, lambda:self.user.has_perm('can_ship', self.obj))
        del settings.CENTRAL_AUTHORIZATIONS

    def test_central_authorizations_right_module_wrong_number_parameters(self):
        settings.CENTRAL_AUTHORIZATIONS = 'utils3'
        self.assertRaises(RulesError, lambda:self.user.has_perm('can_ship', self.obj))
        del settings.CENTRAL_AUTHORIZATIONS


class RulePermissionTest(TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username='javier', is_active=True)[0]
        self.obj = Dummy.objects.get_or_create(supplier=self.user)[0]
        self.ctype = ContentType.objects.get_for_model(self.obj)

    def test_invalid_field_name(self):
        self.assertRaises(NonexistentFieldName, lambda:RulePermission.objects.get_or_create(codename='can_ship', field_name='invalidField', content_type=self.ctype, 
                                                                        view_param_pk='idDummy', description="Only supplier have the authorization to ship"))
        
    def test_invalid_field_name(self):
        self.assertRaises(NonexistentFieldName, lambda:RulePermission.objects.get_or_create(codename='can_ship', field_name='invalidField', content_type=self.ctype, 
                                                                        view_param_pk='idDummy', description="Only supplier have the authorization to ship"))
        
    def test_valid_attribute(self):
        self.assertTrue(RulePermission.objects.get_or_create(codename='can_ship', field_name='supplier', content_type=self.ctype, 
                                                                        view_param_pk='idDummy', description="Only supplier have the authorization to ship")[1])

    def test_method_with_parameter(self):
        self.assertTrue(RulePermission.objects.get_or_create(codename='can_ship', field_name='canShip', content_type=self.ctype, 
                                                                        view_param_pk='idDummy', description="Only supplier have the authorization to ship")[1])
    
    def test_method_no_parameters(self):
        self.assertTrue(RulePermission.objects.get_or_create(codename='can_trash', field_name='canTrash', content_type=self.ctype, 
                                                                        view_param_pk='idDummy', description="User can trash a package")[1])

    def test_method_wrong_number_parameters(self):
        self.assertRaises(RulesError, lambda:RulePermission.objects.get_or_create(codename='can_trash', field_name='invalidNumberParameters', content_type=self.ctype, 
                                                                        view_param_pk='idDummy', description="Rule should not be created, too many parameters"))


class UtilsTest(TestCase):
    def test_register_valid_rules(self):
        rules_list = [
            # Dummy model
            {'codename':'can_ship', 'model':'Dummy', 'field_name':'canShip', 'view_param_pk':'idView', 'description':"Only supplier has the authorization to ship"},
        ]

        try:
            for params in rules_list:
                utils.register(app_name="tests", **params)
        except Exception:
            self.fail("test_register_valid_rules failed")

    def test_register_invalid_rules_NonexistentFieldName(self):
        rules_list = [
            # Dummy model
            {'codename':'can_ship', 'model':'Dummy', 'field_name':'canSship', 'view_param_pk':'idView', 'description':"Only supplier has the authorization to ship"},
        ]

        for params in rules_list:
            self.assertRaises(NonexistentFieldName, lambda: utils.register(app_name="tests", **params))

    def test_register_valid_rules_compact_style(self):
        rules_list = [
            # Dummy model
            {'codename':'canShip', 'model':'Dummy'},
        ]

        try:
            for params in rules_list:
                utils.register(app_name="tests", **params)
        except Exception:
            self.fail("test_register_valid_rules_compact_style failed")



########NEW FILE########
__FILENAME__ = test_decorators
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseRedirect

from django_rules.exceptions import RulesError, NonexistentPermission
from django_rules.models import RulePermission
from django_rules.decorators import object_permission_required
from models import Dummy

class DecoratorsTest(TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username='javier', is_active=True)[0]
        self.otheruser = User.objects.get_or_create(username='miguel', is_active=True)[0]
        self.obj = Dummy.objects.get_or_create(idDummy=1,supplier=self.user)[0]
        self.ctype = ContentType.objects.get_for_model(self.obj)
        self.rule = RulePermission.objects.get_or_create(codename='can_ship', field_name='canShip', content_type=self.ctype, view_param_pk='idView',
                                                            description="Only supplier have the authorization to ship")
        self.wrong_pk_rule = RulePermission.objects.get_or_create(codename='can_supply', field_name='canShip', content_type=self.ctype, view_param_pk='nonexistent_param',
                                                            description="view_param_pk does not match idView param from dummy_view")

    def _get_request(self, user=None):
        if user is None:
            user = AnonymousUser()
        request = HttpRequest()
        request.user = user
        return request

    def _dummy_view(self, user_obj, dicc, value):
        @object_permission_required(**dicc)
        def dummy_view(request, idView):
            return HttpResponse('success')
        
        request = self._get_request(user_obj)
        return dummy_view(request, idView=value)


    def test_no_args(self):
        try:
            @object_permission_required
            def dummy_view(request):
                return HttpResponse('dummy_view')
        except RulesError:
            pass
        else:
            self.fail("Trying to decorate using permission_required without permission as first argument should raise exception")

    def test_wrong_args(self):
        self.assertRaises(RulesError, lambda:self._dummy_view(self.user,{'perm':2},self.obj.pk))

    def test_with_permission(self):
        response = self._dummy_view(self.user, {'perm':'can_ship'}, self.obj.pk)
        self.assertEqual(response.content, 'success')

    def test_without_permission_403(self):
        response = self._dummy_view(self.otheruser, {'perm':'can_ship','return_403':True}, self.obj.pk)
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_permission(self):
        self.assertRaises(NonexistentPermission, lambda: self._dummy_view(self.user, {'perm':'nonexistent_perm'}, self.obj.pk))

    def test_nonexistent_obj(self):
        last=int(Dummy.objects.latest(field_name='pk').pk)
        self.assertRaises(Http404, lambda: self._dummy_view(self.user, {'perm':'can_ship'}, last+1))

    def test_without_permission_redirection(self):
        response = self._dummy_view(self.otheruser, {'perm':'can_ship','login_url':'/foobar/'}, self.obj.pk)
        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertTrue(response._headers['location'][1].startswith('/foobar/'))

    def test_view_param_pk_not_match_param_in_view(self):
        self.assertRaises(RulesError, lambda: self._dummy_view(self.user, {'perm':'can_supply'}, self.obj.pk))
        


########NEW FILE########
__FILENAME__ = test_settings
import os

BASE_DIR = os.path.dirname(__file__)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django_rules',
    'django_rules.tests',
    )

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_rules.backends.ObjectPermissionBackend',
)

ANONYMOUS_USER_ID = '1'

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
def central_authorizations(user_obj, perm):
    # Central authorizations should go here
    if perm == "all_can_pass":
        return True

########NEW FILE########
__FILENAME__ = utils2
# -*- coding: utf-8 -*-

# There is a typo in the function name
def centralized_authorizations(user, perm):
    return True

########NEW FILE########
__FILENAME__ = utils3
# -*- coding: utf-8 -*-

# Wrong number of parameters
def central_authorizations(user_obj, perm, extra):
    return True

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import sys

from django.contrib.contenttypes.models import ContentType

from models import RulePermission
    
def register(app_name, codename, model, field_name='', view_param_pk='', description=''):
    """
    Call this function in your rules.py to register your RulePermissions
    All registered rules will be synced when sync_rules command is run
    """
    # We get the `ContentType` for that `model` within that `app_name`
    try:
        ctype = ContentType.objects.get(app_label = app_name, model = model.lower())
    except ContentType.DoesNotExist:
        sys.stderr.write('! Rule codenamed %s will not be synced as model %s was not found for app %s\n' % (codename, model, app_name))
        return

    try:
        # We see if the rule's pk exists, if it does then delete and overwrite it
        rule = RulePermission.objects.get(pk = codename)
        rule.delete()
        sys.stderr.write('Careful rule %s being overwritten. Make sure its codename is not repeated in other rules.py files\n' % codename)
        RulePermission.objects.create(codename=codename, field_name=field_name, content_type=ctype,
                    view_param_pk=view_param_pk, description=description)

    except RulePermission.DoesNotExist:
        RulePermission.objects.create(codename=codename, field_name=field_name, content_type=ctype,
                    view_param_pk=view_param_pk, description=description)

########NEW FILE########
