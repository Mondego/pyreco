__FILENAME__ = auth
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Authorization related stuff in Adagios

"""

import adagios.status.utils
import adagios.views

auditors = []
operators = []
administrators = []

# administrator belongs to all the other groups
administrators += operators + auditors

access_list = list()

# Explicitly grant configuration access only to admins
access_list.append(('adagios.objectbrowser', "administrators"))
access_list.append(('adagios.okconfig_', "administrators"))
access_list.append(('adagios.misc.helpers', "administrators"))
access_list.append(('adagios.misc.views.settings', "administrators"))

access_list.append(('adagios.misc.views.gitlog', "administrators"))
access_list.append(('adagios.misc.views.service', "administrators"))
access_list.append(('adagios.rest.status.edit', "administrators"))
access_list.append(('adagios.status.views.contact', "administrators"))
access_list.append(('adagios.status.views.state_history', "administrators"))
access_list.append(('adagios.status.views.log', "administrators"))
access_list.append(('adagios.status.views.servicegroup', "administrators"))
access_list.append(('adagios.rest.status.state_history', "administrators"))
access_list.append(('adagios.rest.status.top_alert_producers', "administrators"))
access_list.append(('adagios.rest.status.update_check_command', "administrators"))
access_list.append(('adagios.rest.status.log_entries', "administrators"))



# Access to rest interface
access_list.append(('adagios.rest.views', "everyone"))
access_list.append(('adagios.rest.status', "everyone"))
access_list.append(('adagios.misc.rest', "everyone"))


# These modules should more or less be considered "safe"
access_list.append(('django.views.static', "everyone"))
access_list.append(('django.views.i18n', "everyone"))
access_list.append(('adagios.views', "everyone"))
access_list.append(('adagios.status', "everyone"))
access_list.append(('adagios.pnp', "everyone"))
access_list.append(('adagios.contrib', "everyone"))
access_list.append(('adagios.bi.views.index', "everyone"))
access_list.append(('adagios.bi.views.view', "everyone"))
access_list.append(('adagios.bi.views.json', "everyone"))
access_list.append(('adagios.bi.views.graphs_json', "everyone"))
access_list.append(('adagios.misc.helpers.needs_reload', "everyone"))


# If no other rule matches, assume administrators have access
access_list.append(('', "administrators"))


def check_access_to_path(request, path):
    """ Raises AccessDenied if user does not have access to path

    path in this case is a full path to a python module name for example: "adagios.objectbrowser.views.index"
    """
    for search_path, role in access_list:
        if path.startswith(search_path):
            if has_role(request, role):
                return None
            else:
                user = request.META.get('REMOTE_USER', 'anonymous')
                message = "You do not have permission to access %s" % (path, )
                raise adagios.exceptions.AccessDenied(user, access_required=role, message=message, path=path)
    else:
        return None


def has_access_to_path(request, path):
    """ Returns True/False if user in incoming request has access to path

     Arguments:
        path  -- string describing a path to a method or module, example: "adagios.objectbrowser.views.index"
    """
    for search_path, role in access_list:
        if path.startswith(search_path):
            return has_role(request, role)
    else:
        return False


def has_role(request, role):
    """ Returns true if the username in current request has access to a specific role """
    user = request.META.get('REMOTE_USER', "anonymous")

    # Allow if everyone is allowed access
    if role == 'everyone':
        return True

    # Deny if nobody is allowed access
    if role == 'nobody':
        return False

    # Allow if role is "contacts" and user is in fact a valid contact
    if role == 'contacts' and adagios.status.utils.get_contacts(None, name=user):
        return True

    # Allow if role is "users" and we are in fact logged in
    if role == 'users' and user != "anonymous":
        return True

    users_and_groups = globals().get(role, None)
    if hasattr(adagios.settings, role):
        for i in str(getattr(adagios.settings, role)).split(','):
            i = i.strip()
            if i not in users_and_groups:
                users_and_groups.append(i)


    # Deny if no role exists with this name
    if not users_and_groups:
        return False

    # Allow if user is mentioned in your role
    if user in users_and_groups:
        return True

    # If it is specifically stated that "everyone" belongs to the group
    if "everyone" in users_and_groups:
        return True

    # Check if user belongs to any contactgroup that has access
    contactgroups = adagios.status.utils.get_contactgroups(None, 'Columns: name', 'Filter: members >= %s' % user)

    # Allow if we find user belongs to one contactgroup that has this role
    for contactgroup in contactgroups:
        if contactgroup['name'] in users_and_groups:
            return True

    # If we get here, the user clearly did not have access
    return False


def check_role(request, role):
    """ Raises AccessDenied if user in request does not have access to role """
    if not has_role(request, role):
        user = request.META.get('REMOTE_USER', 'anonymous')
        message = "User does not have the required role"
        raise adagios.exceptions.AccessDenied(username=user, access_required=role, message=message)


class AuthorizationMiddleWare(object):
    """ Django MiddleWare class. It's responsibility is to check if an adagios user has access

    if user does not have access to a given view, it is given a 403 error.
    """
    def process_request(self, request):
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not adagios.settings.enable_authorization:
            return None

        function_name = view_func.__name__
        module_name = view_func.__module__
        if module_name == "adagios.rest.views" and function_name == 'handle_request':
            module_name = view_kwargs['module_path']
            function_name = view_kwargs['attribute']

        try:
            path = module_name + '.' + function_name
            check_access_to_path(request, path)
        except adagios.exceptions.AccessDenied, e:
            return adagios.views.http_403(request, exception=e)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from django import forms
from django.utils.translation import ugettext as _
import adagios.status.utils
import adagios.bi


class RemoveSubProcessForm(forms.Form):

    """ Remove one specific sub process from a business process
    """
    process_name = forms.CharField(max_length=100, required=True)
    process_type = forms.CharField(max_length=100, required=True)

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(RemoveSubProcessForm, self).__init__(*args, **kwargs)

    def save(self):
        process_name = self.cleaned_data.get('process_name')
        process_type = self.cleaned_data.get('process_type')
        self.bp.remove_process(process_name, process_type)
        self.bp.save()

status_method_choices = map(
    lambda x: (x, x), adagios.bi.BusinessProcess.status_calculation_methods)


class BusinessProcessForm(forms.Form):

    """ Use this form to edit a BusinessProcess """
    name = forms.CharField(max_length=100, required=True,
                           help_text=_("Unique name for this business process."))
    #processes = forms.CharField(max_length=100, required=False)
    display_name = forms.CharField(max_length=100, required=False,
                                   help_text=_("This is the name that will be displayed to users on this process. Usually it is the name of the system this business group represents."))
    notes = forms.CharField(max_length=1000, required=False,
                            help_text=_("Here you can put in any description of the business process you are adding. Its a good idea to write down what the business process is about and who to contact in case of downtimes."))
    status_method = forms.ChoiceField(
        choices=status_method_choices, help_text=_("Here you can choose which method is used to calculate the global status of this business process"))
    state_0 = forms.CharField(max_length=100, required=False,
                              help_text=_("Human friendly text for this respective state. You can type whatever you want but nagios style exit codes indicate that 0 should be 'ok'"))
    state_1 = forms.CharField(max_length=100, required=False,
                              help_text=_("Typically used to represent warning or performance problems"))
    state_2 = forms.CharField(max_length=100, required=False,
                              help_text=_("Typically used to represent critical status"))
    state_3 = forms.CharField(
        max_length=100, required=False, help_text=_("Use this when status is unknown"))
    #graphs = models.ManyToManyField(BusinessProcess, unique=False, blank=True)
    #graphs = models.ManyToManyField(BusinessProcess, unique=False, blank=True)

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(BusinessProcessForm, self).__init__(*args, **kwargs)

    def save(self):
        c = self.cleaned_data
        self.bp.data.update(c)
        self.bp.save()

    def remove(self):
        c = self.data
        process_name = c.get('process_name')
        process_type = c.get('process_type')
        if process_type == 'None':
            process_type = None
        self.bp.remove_process(process_name, process_type)
        self.bp.save()

    def clean(self):
        cleaned_data = super(BusinessProcessForm, self).clean()

        # If name has changed, look if there is another business process with
        # same name.
        new_name = cleaned_data.get('name')
        if new_name and new_name != self.bp.name:
            if new_name in adagios.bi.get_all_process_names():
                raise forms.ValidationError(
                    _("Cannot rename process to %s. Another process with that name already exists") % new_name
                )
        return cleaned_data

    def delete(self):
        """ Delete this business process """
        self.bp.delete()

    def add_process(self):

        process_name = self.data.get('process_name')
        hostgroup_name = self.data.get('hostgroup_name')
        servicegroup_name = self.data.get('servicegroup_name')
        service_name = self.data.get('service_name')

        if process_name:
            self.bp.add_process(process_name, None)
        if hostgroup_name:
            self.bp.add_process(hostgroup_name, None)
        if servicegroup_name:
            self.bp.add_process(servicegroup_name, None)
        if service_name:
            self.bp.add_process(service_name, None)
        self.bp.save()

choices = 'businessprocess', 'hostgroup', 'servicegroup', 'service', 'host'
process_type_choices = map(lambda x: (x, x), choices)


class AddSubProcess(forms.Form):
    process_type = forms.ChoiceField(choices=process_type_choices)
    process_name = forms.CharField(
        widget=forms.HiddenInput(attrs={'style': "width: 300px;"}), max_length=100)
    display_name = forms.CharField(max_length=100, required=False)
    tags = forms.CharField(
        max_length=100, required=False, initial="not critical")

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(AddSubProcess, self).__init__(*args, **kwargs)

    def save(self):
        self.bp.add_process(**self.cleaned_data)
        self.bp.save()


class AddHostgroupForm(forms.Form):
    pass


class AddGraphForm(forms.Form):
    host_name = forms.CharField(max_length=100,)
    service_description = forms.CharField(max_length=100, required=False)
    metric_name = forms.CharField(max_length=100, required=True)
    notes = forms.CharField(max_length=100, required=False,
                            help_text=_("Put here a friendly description of the graph"))

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(AddGraphForm, self).__init__(*args, **kwargs)

    def save(self):
        self.bp.add_pnp_graph(**self.cleaned_data)
        self.bp.save()

########NEW FILE########
__FILENAME__ = models
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import tempfile
import os
import time




from django.test import TestCase
from django.test.client import Client
from django.utils.translation import ugettext as _

from adagios.bi import *
import adagios.utils


class TestBusinessProcess(TestCase):
    def setUp(self):
        fd, filename = tempfile.mkstemp()
        BusinessProcess._default_filename = filename

    def tearDown(self):
        os.remove(BusinessProcess._default_filename)

    def test_save_and_load(self):
        """ This test will test load/save of a business process.

         The procedure is as follows:
         * Load a business process
         * Save it
         * Make changes
         * Load it again, and verify changes were saved.
        """
        bp_name = 'test_business_process'

        b = BusinessProcess(bp_name)
        b.load()

        # Append a dot to the bp name and save
        new_display_name = b.display_name or '' + "."
        b.display_name = new_display_name
        b.save()

        # Load bp again
        b = BusinessProcess(bp_name)
        b.load()

        self.assertEqual(b.display_name, new_display_name)

    def test_add_process(self):
        """ Test adding new processes to a current BP
        """
        bp_name = 'test'
        sub_process_name = 'sub_process'
        sub_process_display_name = 'This is a subprocess of test'
        b = BusinessProcess(bp_name)
        b.add_process(sub_process_name, display_name=sub_process_display_name)
        for i in b.get_processes():
            if i.name == sub_process_name and i.display_name == sub_process_display_name:
                return
        else:
            self.assertTrue(
                False, 'We tried adding a business process but could not find it afterwards')

    def test_hostgroup_bp(self):
        bp_name = 'test'
        hostgroup_name = 'acme-network'
        b = BusinessProcess(bp_name)
        b.add_process(hostgroup_name, 'hostgroup')

    def test_remove_process(self):
        """ Test removing a subprocess from a businessprocess
        """
        bp_name = 'test'
        sub_process_name = 'sub_process'
        sub_process_display_name = 'This is a subprocess of test'
        b = BusinessProcess(bp_name)
        b.add_process(sub_process_name, display_name=sub_process_display_name)
        self.assertNotEqual([], b.processes)
        b.remove_process(sub_process_name)
        self.assertEqual([], b.processes)

    def test_get_all_processes(self):
        get_all_processes()

    def test_macros(self):
        bp = get_business_process('uniq test case', status_method="use_worst_state")

        macros_for_empty_process = {
            'num_problems': 0,
            'num_state_0': 0,
            'num_state_1': 0,
            'num_state_2': 0,
            'num_state_3': 0,
            'current_state': 3,
            'friendly_state': 'unknown',
            'percent_problems': 0,
            'percent_state_3': 0,
            'percent_state_2': 0,
            'percent_state_1': 0,
            'percent_state_0': 0
        }
        self.assertEqual(3, bp.get_status())
        self.assertEqual(macros_for_empty_process, bp.resolve_all_macros())

        bp.add_process("always_ok", status_method="always_ok")
        bp.add_process("always_major", status_method="always_major")

        macros_for_nonempty_process = {
            'num_problems': 1,
            'num_state_0': 1,
            'num_state_1': 0,
            'num_state_2': 1,
            'num_state_3': 0,
            'current_state': 2,
            'friendly_state': 'major problems',
            'percent_problems': 50.0,
            'percent_state_3': 0.0,
            'percent_state_2': 50.0,
            'percent_state_1': 0.0,
            'percent_state_0': 50.0
        }
        self.assertEqual(2, bp.get_status())
        self.assertEqual(macros_for_nonempty_process, bp.resolve_all_macros())

    def testPageLoad(self):
        self.loadPage('/bi')
        self.loadPage('/bi/add')
        self.loadPage('/bi/add/subprocess')
        self.loadPage('/bi/add/graph')

    def loadPage(self, url):
        """ Load one specific page, and assert if return code is not 200 """
        try:
            c = Client()
            response = c.get(url)
            self.assertEqual(response.status_code, 200, _("Expected status code 200 for page %s") % url)
        except Exception, e:
            self.assertEqual(True, "Unhandled exception while loading %s: %s" % (url, e))


class TestBusinessProcessLogic(TestCase):
    """ This class responsible for testing business classes logic """
    def setUp(self):
        self.environment = adagios.utils.FakeAdagiosEnvironment()
        self.environment.create_minimal_environment()
        self.environment.configure_livestatus()
        self.environment.update_adagios_global_variables()
        self.environment.start()

        self.livestatus = self.environment.get_livestatus()
        self.livestatus.test()

        fd, filename = tempfile.mkstemp()
        BusinessProcess._default_filename = filename

    def tearDown(self):
        self.environment.terminate()
        os.remove(BusinessProcess._default_filename)

    def testBestAndWorstState(self):
        s = BusinessProcess("example process")
        s.status_method = 'use_worst_state'
        self.assertEqual(3, s.get_status(), _("Empty bi process should have status unknown"))

        s.add_process(process_name="always_ok", process_type="businessprocess", status_method='always_ok')
        self.assertEqual(0, s.get_status(), _("BI process with one ok subitem, should have state OK"))

        s.add_process("fail subprocess", status_method="always_major")
        self.assertEqual(2, s.get_status(), _("BI process with one failed item should have a critical state"))

        s.status_method = 'use_best_state'
        self.assertEqual(0, s.get_status(), _("BI process using use_best_state should be returning OK"))

    def testBusinessRules(self):
        s = BusinessProcess("example process")
        self.assertEqual(3, s.get_status(), _("Empty bi process should have status unknown"))

        s.add_process(process_name="always_ok", process_type="businessprocess", status_method='always_ok')
        self.assertEqual(0, s.get_status(), _("BI process with one ok subitem, should have state OK"))

        s.add_process("untagged process", status_method="always_major")
        self.assertEqual(0, s.get_status(), _("BI subprocess that is untagged should yield an ok state"))

        s.add_process("not critical process", status_method="always_major", tags="not critical")
        self.assertEqual(1, s.get_status(), _("A Non critical subprocess should yield 'minor problem'"))

        s.add_process("critical process", status_method="always_major", tags="mission critical")
        self.assertEqual(2, s.get_status(), _("A critical process in failed state should yield major problem"))

        s.add_process("another noncritical process", status_method="always_major", tags="not critical")
        self.assertEqual(2, s.get_status(), _("Adding another non critical subprocess should still yield a critical state"))


class TestDomainProcess(TestCase):
    """ Test the Domain business process type
    """
    def setUp(self):
        self.environment = adagios.utils.FakeAdagiosEnvironment()
        self.environment.create_minimal_environment()
        self.environment.configure_livestatus()
        self.environment.update_adagios_global_variables()
        self.environment.start()

        self.livestatus = self.environment.get_livestatus()
        self.livestatus.test()

    def tearDown(self):
        self.environment.terminate()


    def testHost(self):
        domain = get_business_process(process_name='ok.is', process_type='domain')

        # We don't exactly know the status of the domain, but lets run it anyway
        # for smoketesting
        domain.get_status()


class TestServiceProcess(TestCase):
    """ Test Service Business process type """
    def setUp(self):
        self.environment = adagios.utils.FakeAdagiosEnvironment()
        self.environment.create_minimal_environment()
        self.environment.configure_livestatus()
        self.environment.update_adagios_global_variables()
        self.environment.start()

        self.livestatus = self.environment.get_livestatus()
        self.livestatus.test()
    def tearDown(self):
        self.environment.terminate()

    def testService(self):
        service = get_business_process('ok_host/ok service 1', process_type='service')
        status = service.get_status()
        self.assertFalse(service.errors)
        self.assertEqual(0, status, "The service should always have status OK")


class TestHostProcess(TestCase):
    """ Test the Host business process type
    """
    def setUp(self):
        self.environment = adagios.utils.FakeAdagiosEnvironment()
        self.environment.create_minimal_environment()
        self.environment.configure_livestatus()
        self.environment.update_adagios_global_variables()
        self.environment.start()

        self.livestatus = self.environment.get_livestatus()
        self.livestatus.test()

    def tearDown(self):
        self.environment.terminate()

    def testNonExistingHost(self):
        host = get_business_process('non-existant host', process_type='host')
        self.assertEqual(3, host.get_status(), _("non existant host processes should have unknown status"))

    def testExistingHost(self):
        #localhost = self.livestatus.get_hosts('Filter: host_name = ok_host')
        host = get_business_process('ok_host', process_type='host')
        self.assertEqual(0, host.get_status(), _("the host ok_host should always has status ok"))

    def testDomainProcess(self):
        domain = get_business_process(process_name='oksad.is', process_type='domain')
        # We don't exactly know the status of the domain, but lets run it anyway
        # for smoketesting

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('adagios',
                      (r'^/?$', 'bi.views.index'),
                      (r'^/add/?$', 'bi.views.add'),
                      (r'^/add/subprocess/?$', 'bi.views.add_subprocess'),
                      (r'^/add/graph/?$', 'bi.views.add_graph'),
                      (r'^/(?P<process_name>.+)/edit/status_method$', 'bi.views.change_status_calculation_method'),
                      (r'^/edit/(?P<process_type>.+?)/(?P<process_name>.+?)/?$', 'bi.views.edit'),
                      (r'^/json/(?P<process_type>.+?)/(?P<process_name>.+?)/?$', 'bi.views.json'),
                      (r'^/graphs/(?P<process_type>.+?)/(?P<process_name>.+?)/?$', 'bi.views.graphs_json'),
                      (r'^/delete/(?P<process_type>.+?)/(?P<process_name>.+?)/?$', 'bi.views.delete'),
                      (r'^/view/(?P<process_type>.+?)/(?P<process_name>.+?)/?$', 'bi.views.view'),
                      #(r'^/view/(?P<process_name>.+)/?$', 'bi.views.view'),
                       )

########NEW FILE########
__FILENAME__ = views
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import simplejson
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from adagios.pnp.functions import run_pnp
from adagios.views import adagios_decorator

import adagios.bi
import adagios.bi.forms

from adagios.views import adagios_decorator, error_page


@adagios_decorator
def edit(request, process_name, process_type):
    """ Edit one specific business process
    """

    messages = []
    bp = adagios.bi.get_business_process(process_name)
    errors = bp.errors or []
    status = bp.get_status()
    add_subprocess_form = adagios.bi.forms.AddSubProcess(instance=bp)
    form = adagios.bi.forms.BusinessProcessForm(instance=bp, initial=bp.data)
    add_graph_form = adagios.bi.forms.AddGraphForm(instance=bp)
    if request.method == 'GET':
        form = adagios.bi.forms.BusinessProcessForm(
            instance=bp, initial=bp.data)
    elif request.method == 'POST':
        if 'save_process' in request.POST:
            form = adagios.bi.forms.BusinessProcessForm(
                instance=bp, data=request.POST)
            if form.is_valid():
                form.save()
        elif 'remove_process' in request.POST:
            removeform = adagios.bi.forms.RemoveSubProcessForm(
                instance=bp, data=request.POST)
            if removeform.is_valid():
                removeform.save()
        elif 'add_process' in request.POST:
            if form.is_valid():
                form.add_process()
        elif 'add_graph_submit_button' in request.POST:
            add_graph_form = adagios.bi.forms.AddGraphForm(
                instance=bp, data=request.POST)
            if add_graph_form.is_valid():
                add_graph_form.save()
        elif 'add_subprocess_submit_button' in request.POST:
            add_subprocess_form = adagios.bi.forms.AddSubProcess(
                instance=bp, data=request.POST)
            if add_subprocess_form.is_valid():
                add_subprocess_form.save()

            else:
                errors.append(_("failed to add subprocess"))
                add_subprocess_failed = True
        else:
            errors.append(
                _("I don't know what submit button was clicked. please file a bug."))

        # Load the process again, since any of the above probably made changes
        # to it.
        bp = adagios.bi.get_business_process(process_name)

    return render_to_response('business_process_edit.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def add_graph(request):
    """ Add one or more graph to a single business process
    """
    c = {}
    c['errors'] = []
    c.update(csrf(request))
    if request.method == 'GET':
        source = request.GET
    else:
        source = request.POST
    name = source.get('name', None)
    if name:
        c['name'] = name
    bp = adagios.bi.get_business_process(name)
    c['graphs'] = []
    # Convert every graph= in the querystring into
    # host_name,service_description,metric attribute
    graphs = source.getlist('graph')
    for graph in graphs:
        tmp = graph.split(',')
        if len(tmp) != 3:
            c['errors'].append(_("Invalid graph string: %s") % (tmp))
        graph_dict = {}
        graph_dict['host_name'] = tmp[0]
        graph_dict['service_description'] = tmp[1]
        graph_dict['metric_name'] = tmp[2]
        graph_dict['notes'] = tmp[2]
        c['graphs'].append(graph_dict)

    #
    # When we get here, we have parsed all the data from the client, if
    # its a post, lets add the graphs to our business process
    if request.method == 'POST':
        if not name:
            raise Exception(
                _("Booh! you need to supply name= to the querystring"))
        for graph in c['graphs']:
            form = adagios.bi.forms.AddGraphForm(instance=bp, data=graph)
            if form.is_valid():
                form.save()
            else:
                e = form.errors
                raise e
        return redirect('adagios.bi.views.edit', bp.process_type, bp.name)

    return render_to_response('business_process_add_graph.html', c, context_instance=RequestContext(request))


@adagios_decorator
def view(request, process_name, process_type=None):
    """ View one specific business process
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    bp = adagios.bi.get_business_process(
        process_name, process_type=process_type)
    graphs_url = reverse(
        'adagios.bi.views.graphs_json', kwargs={"process_type":process_type, "process_name": process_name})
    c['bp'] = bp
    c['graphs_url'] = graphs_url
    return render_to_response('business_process_view.html', c, context_instance=RequestContext(request))


@adagios_decorator
def json(request, process_name=None, process_type=None):
    """ Returns a list of all processes in json format.

    If process_name is specified, return all sub processes.
    """
    if not process_name:
        processes = adagios.bi.get_all_processes()
    else:
        process = adagios.bi.get_business_process(process_name, process_type)
        processes = process.get_processes()
    result = []
    # Turn processes into nice json
    for i in processes:
        json = {}
        json['state'] = i.get_status()
        json['name'] = i.name
        json['display_name'] = i.display_name
        result.append(json)
    json = simplejson.dumps(result)
    return HttpResponse(json, content_type="application/json")

@adagios_decorator
def graphs_json(request, process_name, process_type):
    """ Get graphs for one specific business process
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    import adagios.businessprocess
    bp = adagios.bi.get_business_process(process_name=process_name, process_type=process_type)

    graphs = []
    if not bp.graphs:
        return HttpResponse('[]')
    for graph in bp.graphs or []:
        if graph.get('graph_type') == 'pnp':
            host_name = graph.get('host_name')
            service_description = graph.get('service_description')
            metric_name = graph.get('metric_name')
            pnp_result = run_pnp('json', host=graph.get(
                'host_name'), srv=graph.get('service_description'))
            json_data = simplejson.loads(pnp_result)
            for i in json_data:
                if i.get('ds_name') == graph.get('metric_name'):
                    notes = graph.get('notes')
                    last_value = bp.get_pnp_last_value(
                        host_name, service_description, metric_name)
                    i['last_value'] = last_value
                    i['notes'] = notes
                    graphs.append(i)
    graph_json = simplejson.dumps(graphs)
    return HttpResponse(graph_json)


@adagios_decorator
def add_subprocess(request):
    """ Add subitems to one specific businessprocess
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c.update(csrf(request))
    process_list, parameters = _business_process_parse_querystring(request)

    if request.method == 'POST':
        if 'name' not in request.POST:
            raise Exception(
                _("You must specify which subprocess to add all these objects to"))
        parameters.pop('name')
        bp = adagios.bi.get_business_process(request.POST.get('name'))
        # Find all subprocesses in the post, can for each one call add_process
        # with all parmas as well
        for i in process_list:
            process_name = i.get('name')
            process_type = i.get('process_type')
            bp.add_process(process_name, process_type, **parameters)
            c['messages'].append('%s: %s added to %s' %
                                 (process_type, process_name, bp.name))
        bp.save()
        return redirect('adagios.bi.views.edit', bp.process_type, bp.name)
    c['subprocesses'] = process_list
    c['parameters'] = parameters
    return render_to_response('business_process_add_subprocess.html', c, context_instance=RequestContext(request))


@adagios_decorator
def add(request):
    """ View one specific business process
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    import adagios.businessprocess
    bp = adagios.bi.BusinessProcess(_("New Business Process"))
    if request.method == 'GET':
        form = adagios.bi.forms.BusinessProcessForm(
            instance=bp, initial=bp.data)
    elif request.method == 'POST':
        form = adagios.bi.forms.BusinessProcessForm(
            instance=bp, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('adagios.bi.views.edit', bp.process_type, bp.name)
    return render_to_response('business_process_edit.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def index(request):
    """ List all configured business processes
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    processes = adagios.bi.get_all_processes()
    return render_to_response('business_process_list.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def delete(request, process_name, process_type):
    """ Delete one specific business process """
    import adagios.businessprocess
    bp = adagios.bi.get_business_process(process_name=process_name, process_type=process_type)
    if request.method == 'POST':
        form = adagios.bi.forms.BusinessProcessForm(
            instance=bp, data=request.POST)
        form.delete()
        return redirect('adagios.bi.views.index')

    return render_to_response('business_process_delete.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def change_status_calculation_method(request, process_name):
    import adagios.businessprocess
    bp = adagios.bi.get_business_process(process_name)
    if request.method == 'POST':
        for i in bp.status_calculation_methods:
            if i in request.POST:
                bp.status_method = i
                bp.save()
        return redirect('adagios.bi.views.index')


def _business_process_parse_querystring(request):
    """ Parses querystring into process_list and parameters

    Returns:
      (parameters,processs_list) where:
         -- process_list is a list of all business processes that were mentioned in the querystring
         -- Parameters is a dict of all other querystrings that were not in process_list and not in exclude list
    """
    ignored_querystring_parameters = ("csrfmiddlewaretoken")
    import adagios.businessprocess
    data = {}
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST
    else:
        raise Exception(_("Booh, use either get or POST"))
    parameters = {}
    process_list = []
    for key in data:
        for value in data.getlist(key):
            if key in ignored_querystring_parameters:
                continue
            type_of_process = adagios.bi.get_class(key, None)

            if type_of_process is None:
                parameters[key] = value
            else:
                process_type = type_of_process.process_type
                process = adagios.bi.get_business_process(
                    value, process_type=process_type)
                process_list.append(process)
    return process_list, parameters

########NEW FILE########
__FILENAME__ = businessprocess
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from adagios.bi import *

########NEW FILE########
__FILENAME__ = context_processors
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pynag.Model
import os
import getpass

from adagios import notifications, settings, add_plugin
from adagios.misc.rest import add_notification, clear_notification

import pynag.Model.EventHandlers
import pynag.Parsers
from pynag.Parsers import Livestatus
import adagios
import adagios.status.utils
from pynag import Model
import time
import datetime
from adagios import __version__
from adagios import userdata

from django.utils.translation import ugettext as _

def on_page_load(request):
    """ Collection of actions that take place every page load """
    results = {}
    for k, v in reload_configfile(request).items():
        results[k] = v
    for k, v in get_httpuser(request).items():
        results[k] = v
    for k, v in get_tagged_comments(request).items():
        results[k] = v
    for k, v in check_nagios_running(request).items():
        results[k] = v
    for k, v in get_notifications(request).items():
        results[k] = v
    for k, v in get_unhandled_problems(request).items():
        results[k] = v
    for k, v in resolve_urlname(request).items():
        results[k] = v
    for k, v in check_selinux(request).items():
        results[k] = v
    for k, v in activate_plugins(request).items():
        results[k] = v
    for k, v in check_destination_directory(request).items():
        results[k] = v
    for k, v in check_nagios_cfg(request).items():
        results[k] = v
    for k, v in get_current_time(request).items():
        results[k] = v
    for k, v in get_okconfig(request).items():
        results[k] = v
    for k, v in get_nagios_url(request).items():
        results[k] = v
    for k, v in get_local_user(request).items():
        results[k] = v
    for k, v in get_current_settings(request).items():
        results[k] = v
    for k, v in get_plugins(request).items():
        results[k] = v
    for k, v in get_current_version(request).items():
        results[k] = v
    for k, v in get_serverside_includes(request).items():
        results[k] = v
    for k, v in get_user_preferences(request).items():
        results[k] = v
    for k, v in get_all_backends(request).items():
        results[k] = v
    for k, v in get_all_nonworking_backends(request).items():
        results[k] = v
    return results


def get_current_time(request):
    """ Make current timestamp available to templates
    """
    result = {}
    try:
        now = datetime.datetime.now()
        result['current_time'] = now.strftime("%b %d %H:%M")
        result['current_timestamp'] = int(time.time())
    except Exception:
        return result
    return result


def get_serverside_includes(request):
    """ Returns a list of serverside includes to include on this page """
    result = {}
    try:
        result['ssi_headers'] = []
        result['ssi_footers'] = []
        dirname = adagios.settings.serverside_includes
        current_url = resolve_urlname(request)
        if not dirname:
            return {}
        if not os.path.isdir(dirname):
            return {}
        files = os.listdir(dirname)
        common_header_file = "common-header.ssi"
        common_footer_file = "common-footer.ssi"
        custom_header_file = "{urlname}-header.ssi".format(urlname=current_url)
        custom_footer_file = "{urlname}-footer.ssi".format(urlname=current_url)
        if common_header_file in files:
            result['ssi_headers'].append(dirname + "/" + common_header_file)
        if common_footer_file in files:
            result['ssi_footers'].append(dirname + "/" + common_footer_file)
        if custom_header_file in files:
            result['ssi_headers'].append(dirname + "/" + custom_header_file)
        if custom_footer_file in files:
            result['ssi_footers'].append(dirname + "/" + custom_footer_file)
    except Exception:
        return {}
    return result


def activate_plugins(request):
    """ Activates any plugins specified in settings.plugins """
    for k, v in settings.plugins.items():
        add_plugin(name=k, modulepath=v)
    return {'misc_menubar_items': adagios.misc_menubar_items, 'menubar_items': adagios.menubar_items}


def get_local_user(request):
    """ Return user that is running the adagios process under apache
    """
    user = getpass.getuser()
    return {'local_user': user}


def get_current_version(request):
    """ Returns current adagios version """
    return {'adagios_version': __version__}

def get_current_settings(request):
    """ Return a copy of adagios.settings
    """
    return {'settings': adagios.settings}


def resolve_urlname(request):
    """Allows us to see what the matched urlname for this
    request is within the template"""
    from django.core.urlresolvers import resolve
    try:
        res = resolve(request.path)
        if res:
            return {'urlname': res.url_name}
    except Exception:
        return {'urlname': 'None'}


def get_httpuser(request):
    """ Get the current user that is authenticating to us and update event handlers"""
    try:
        remote_user = request.META.get('REMOTE_USER', None)
    except Exception:
        remote_user = "anonymous"
    return {'remote_user': remote_user or "anonymous"}


def get_nagios_url(request):
    """ Get url to legasy nagios interface """
    return {'nagios_url': settings.nagios_url}


def get_tagged_comments(request):
    """ (for status view) returns number of comments that mention the remote_user"""
    try:
        remote_user = request.META.get('REMOTE_USER', 'anonymous')
        livestatus = adagios.status.utils.livestatus(request)
        tagged_comments = livestatus.query(
            'GET comments', 'Stats: comment ~ %s' % remote_user, columns=False)[0]
        if tagged_comments > 0:
            return {'tagged_comments': tagged_comments}
        else:
            return {}
    except Exception:
        return {}


def get_unhandled_problems(request):
    """ Get number of any unhandled problems via livestatus """
    results = {}
    try:
        livestatus = adagios.status.utils.livestatus(request)
        num_problems = livestatus.query('GET services',
                                        'Filter: state != 0',
                                        'Filter: acknowledged = 0',
                                        'Filter: host_acknowledged = 0',
                                        'Filter: scheduled_downtime_depth = 0',
                                        'Filter: host_scheduled_downtime_depth = 0',
                                        'Stats: state != 0',
                                        'Stats: host_state != 0',
                                        columns=False)
        results['num_problems'] = num_problems[0] + num_problems[1]
        results['num_unhandled_problems'] = num_problems[0] + num_problems[1]

        result = livestatus.query('GET services',
                                        'Stats: state != 0',
                                        'Stats: state != 0',
                                        'Stats: acknowledged = 0',
                                        'Stats: scheduled_downtime_depth = 0',
                                        'Stats: host_state = 0',
                                        'StatsAnd: 4',
                                        columns=False
                                        )
        num_service_problems_all = result[0]
        num_service_problems_unhandled = result[1]


        result = livestatus.query('GET hosts',
                                        'Stats: state != 0',
                                        'Stats: state != 0',
                                        'Stats: acknowledged = 0',
                                        'Stats: scheduled_downtime_depth = 0',
                                        'Stats: host_state = 1',
                                        'StatsAnd: 4',
                                        columns=False
                                        )
        num_host_problems_all = result[0]
        num_host_problems_unhandled = result[1]

        num_problems_all = num_service_problems_all + num_host_problems_all
        num_problems_unhandled = num_service_problems_unhandled + num_host_problems_unhandled

        num_problems = num_problems_unhandled

        results = locals()
        del results['livestatus']
        del results['result']
        del results['request']

    except Exception:
        pass
    return results


def check_nagios_cfg(request):
    """ Check availability of nagios.cfg """
    return {'nagios_cfg': pynag.Model.config.cfg_file}


def check_destination_directory(request):
    """ Check that adagios has a place to store new objects """
    dest = settings.destination_directory
    dest_dir_was_found = False

    # If there are problems with finding nagios.cfg, we don't
    # need to display any errors here regarding destination_directories
    try:
        Model.config.parse_maincfg()
    except Exception:
        return {}
    for k, v in Model.config.maincfg_values:
        if k != 'cfg_dir':
            continue
        if os.path.normpath(v) == os.path.normpath(dest):
            dest_dir_was_found = True
    if not dest_dir_was_found:
        add_notification(level="warning", notification_id="dest_dir",
                         message=_("Destination for new objects (%s) is not defined in nagios.cfg") % dest)
    elif not os.path.isdir(dest):
        add_notification(level="warning", notification_id="dest_dir",
                         message=_("Destination directory for new objects (%s) is not found. Please create it.") % dest)
    else:
        clear_notification(notification_id="dest_dir")
    return {}


def check_nagios_running(request):
    """ Notify user if nagios is not running """
    try:
        if pynag.Model.config is None:
            pynag.Model.config = pynag.Parsers.config(
                adagios.settings.nagios_config)
        nagios_pid = pynag.Model.config._get_pid()
        return {"nagios_running": (nagios_pid is not None)}
    except Exception:
        return {}


def check_selinux(request):
    """ Check if selinux is enabled and notify user """
    notification_id = "selinux_active"
    if settings.warn_if_selinux_is_active:
        try:
            if open('/sys/fs/selinux/enforce', 'r').readline().strip() == "1":
                add_notification(
                    level="warning",
                    message=_('SELinux is enabled, which is likely to give your monitoring engine problems., see <a href="https://access.redhat.com/knowledge/docs/en-US/Red_Hat_Enterprise_Linux/6/html-single/Security-Enhanced_Linux/index.html#sect-Security-Enhanced_Linux-Enabling_and_Disabling_SELinux-Disabling_SELinux">here</a> for information on how to disable it.'),
                    notification_id=notification_id,
                )
        except Exception:
            pass
    else:
        clear_notification(notification_id)
    return {}


def get_notifications(request):
    """ Returns a hash map of adagios.notifications """
    return {"notifications": notifications}


def get_okconfig(request):
    """ Returns {"okconfig":True} if okconfig module is installed.
    """
    try:
        if "okconfig" in settings.plugins:
            return {"okconfig": True}
        return {}
    except Exception:
        return {}


def get_plugins(request):
    """
    """
    return {'plugins': settings.plugins}


def reload_configfile(request):
    """ Load the configfile from settings.adagios_configfile and put its content in adagios.settings. """
    try:
        clear_notification("configfile")
        locals = {}
        execfile(settings.adagios_configfile, globals(), locals)
        for k, v in locals.items():
            settings.__dict__[k] = v
    except Exception, e:
        add_notification(
            level="warning", message=str(e), notification_id="configfile")
    return {}


def get_user_preferences(request):
    """ Loads the preferences for the logged-in user. """
    def theme_to_themepath(theme):
        return os.path.join(settings.THEMES_FOLDER,
                            theme,
                            settings.THEME_ENTRY_POINT)
    try:
        user = userdata.User(request)
        user.trigger_hooks()
        results = user.to_dict()
    except Exception:
        results = adagios.settings.PREFS_DEFAULT

    theme = results.get('theme', 'default')
    results['theme_path'] = theme_to_themepath(theme)
    return {'user_data': results}

def get_all_backends(request):
    backends = adagios.status.utils.get_all_backends()
    return {'backends': backends}

def get_all_nonworking_backends(request):
    """ Returns the backends which don't answer at the time. """
    b = [x for x in get_all_backends(request)['backends']
         if not Livestatus(x).test(raise_error=False)]
    return {'nonworking_backends': b}

if __name__ == '__main__':
    on_page_load(request=None)

########NEW FILE########
__FILENAME__ = forms
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from django.utils import unittest
from django.test.client import Client

import pynag.Parsers

import tempfile
import os
from adagios.contrib import get_template_name
import pynag.Utils


class ContribTests(unittest.TestCase):
    def setUp(self):
        base_path = tempfile.mkdtemp()
        self.base_path = base_path

    def tearDown(self):
        command = ['rm', '-rf', self.base_path]
        pynag.Utils.runCommand(command=command, shell=False)

    def testGetTemplateFilename(self):
        base_path = self.base_path

        file1 = base_path + '/file1'
        dir1 = base_path + '/dir1'
        file2 = dir1 + '/file2'

        open(file1, 'w').write('this is file1')
        os.mkdir(dir1)
        open(file2, 'w').write('this is file2')

        self.assertEqual(file1, get_template_name(base_path, 'file1'))
        self.assertEqual(file2, get_template_name(base_path, 'dir1', 'file2'))
        self.assertEqual(file2, get_template_name(base_path, 'dir1', 'file2', 'unneeded_argument'))

        # Try to return a filename that is outside base_path
        exception1 = lambda: get_template_name(base_path, '/etc/passwd')
        self.assertRaises(Exception, exception1)

        # Try to return a filename that is outside base_path
        exception2 = lambda: get_template_name(base_path, '/etc/', 'passwd')
        self.assertRaises(Exception, exception2)

        # Try to return a filename that is outside base_path
        exception3 = lambda: get_template_name(base_path, '..', 'passwd')
        self.assertRaises(Exception, exception3)






########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('adagios',
                      (r'^/$', 'contrib.views.index'),
                      (r'^/(?P<arg1>.+)?$', 'contrib.views.contrib'),
                      (r'^/(?P<arg1>.+)/(?P<arg2>.+)/?$', 'contrib.views.contrib'),
                      (r'^/(?P<arg1>.+)(?P<arg2>.+)/(?P<arg3>.+)/?$', 'contrib.views.contrib'),
                      (r'^/(?P<arg1>.+)(?P<arg2>.+)/(?P<arg3>.+)/(?P<arg4>.+)/?$', 'contrib.views.contrib'),
                       )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.shortcuts import HttpResponse
import adagios.settings
import adagios.status.utils
import os

from adagios.views import adagios_decorator, error_page
from django.template import RequestContext
from adagios.contrib import get_template_name
from django import template
from django.utils.translation import ugettext as _


@adagios_decorator
def index(request, contrib_dir=None):
    """ List all available user contributed views in adagios.settings.contrib_dir """
    messages = []
    errors = []

    if not contrib_dir:
        contrib_dir = adagios.settings.contrib_dir
    views = os.listdir(contrib_dir)

    if not views:
        errors.append(_("Directory '%s' is empty") % contrib_dir)
    return render_to_response("contrib_index.html", locals(), context_instance=RequestContext(request))


@adagios_decorator
def contrib(request, arg1, arg2=None, arg3=None, arg4=None):
    messages = []
    errors = []

    full_path = get_template_name(adagios.settings.contrib_dir, arg1, arg2, arg3, arg4)
    if os.path.isdir(full_path):
        return index(request, contrib_dir=full_path)

    with open(full_path) as f:
        content = f.read()

    # Lets populate local namespace with convenient data
    services = lambda: locals().get('services', adagios.status.utils.get_services(request))
    hosts = lambda: locals().get('hosts', adagios.status.utils.get_hosts(request))
    service_problems = lambda: locals().get('service_problems', adagios.status.utils.get_hosts(request, state__isnot='0'))
    host_problems = lambda: locals().get('host_problems', adagios.status.utils.get_hosts(request, state__isnot='0'))
    statistics = lambda: locals().get('statistics', adagios.status.utils.get_statistics(request))

    t = template.Template(content)
    c = RequestContext(request, locals())
    html = t.render(c)
    return HttpResponse(html)

########NEW FILE########
__FILENAME__ = exceptions
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Exceptions that Adagios uses and raises
"""


class AdagiosError(Exception):
    """ Base Class for all Adagios Exceptions """
    pass


class AccessDenied(AdagiosError):
    """ This exception is raised whenever a user tries to access a page he does not have access to. """
    def __init__(self, username, access_required, message, path=None, *args, **kwargs):
        self.username = username
        self.access_required = access_required
        self.message = message
        self.path = path
        super(AccessDenied, self).__init__(message, *args, **kwargs)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.utils.encoding import smart_str
from django import forms

class AdagiosForm(forms.Form):
    """ Base class for all forms in this module. Forms that use pynag in any way should inherit from this one.
    """
    def clean(self):
        cleaned_data = {}
        tmp = super(AdagiosForm, self).clean()
        for k,v in tmp.items():
            if isinstance(k, (unicode)):
                k = smart_str(k)
            if isinstance(v, (unicode)):
                v = smart_str(v)
            cleaned_data[k] = v
        return cleaned_data

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/python
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms

from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

import os.path
from adagios import settings
import adagios.utils
from pynag import Model, Control
from django.core.mail import EmailMultiAlternatives
import pynag.Parsers
import pynag.Control.Command


TOPIC_CHOICES = (
    ('general', _('General Suggestion')),
    ('bug', _('I think i have found a bug')),
    ('suggestion', _('I have a particular task in mind that i would like to do with Adagios')),
    ('easier', _('I have an idea how make a certain task easier to do')),
)

pnp_loglevel_choices = [
    ('0', _('0 - Only Errors')),
    ('1', _('1 - Little logging')),
    ('2', _('2 - Log Everything')),
    ('-1', _('-1 Debug mode (log all and slower processing'))
]
pnp_log_type_choices = [('syslog', 'syslog'), ('file', 'file')]

COMMAND_CHOICES = [('reload', 'reload'), ('status', 'status'),
                   ('restart', 'restart'), ('stop', 'stop'), ('start', 'start')]


initial_paste = """
define service {
    host_name  host01.example.com
    service_description http://host01.example.com
    use     template-http
}

define service {
    name        template-http
    check_command   okc-check_http
}
"""

class ContactUsForm(forms.Form):
    topic = forms.ChoiceField(choices=TOPIC_CHOICES)
    sender = forms.CharField(
        required=False,
        help_text=_("Optional email address if you want feedback from us"),
    )
    message = forms.CharField(
        widget=forms.widgets.Textarea(
            attrs={'rows': 15, 'cols': 40}),
        help_text=_("See below for examples of good suggestions"),
    )

    def save(self):
        from_address = 'adagios@adagios.opensource.is'
        to_address = ["palli@ok.is"]
        subject = _("Suggestion from Adagios")

        sender = self.cleaned_data['sender']
        topic = self.cleaned_data['topic']
        message = self.cleaned_data['message']

        msg = _("""
        topic: %(topic)s
        from: %(sender)s

        %(message)s
        """) % {'topic': topic, 'sender': sender, 'message': message}
        send_mail(subject, msg, from_address, to_address, fail_silently=False)

class UserdataForm(forms.Form):
    language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        required=False
    )
    theme = forms.ChoiceField(
        choices=[(x, x) for x in adagios.utils.get_available_themes()],
        required=False
    )
    refresh_rate = forms.IntegerField(
        help_text="For pages that auto-reload. Set the number of seconds to wait between page refreshes. "
                  "Set refresh rate to 0 to disable automatic refreshing.",
        required=False,
    )


class AdagiosSettingsForm(forms.Form):
    nagios_config = forms.CharField(
        required=False, initial=settings.nagios_config,
        help_text=_("Path to nagios configuration file. i.e. /etc/nagios/nagios.cfg"))
    destination_directory = forms.CharField(
        required=False, initial=settings.destination_directory, help_text=_("Where to save new objects that adagios creates."))
    nagios_url = forms.CharField(required=False, initial=settings.nagios_url,
                                 help_text=_("URL (relative or absolute) to your nagios webcgi. Adagios will use this to make it simple to navigate from a configured host/service directly to the cgi."))
    nagios_init_script = forms.CharField(
        help_text=_("Path to you nagios init script. Adagios will use this when stopping/starting/reloading nagios"))
    nagios_binary = forms.CharField(
        help_text=_("Path to you nagios daemon binary. Adagios will use this to verify config with 'nagios -v nagios_config'"))
    livestatus_path = forms.CharField(
        help_text=_("Path to MK Livestatus socket. If left empty Adagios will try to autodiscover from your nagios.cfg"),
        required=False,
    )
    enable_githandler = forms.BooleanField(
        required=False, initial=settings.enable_githandler, help_text=_("If set. Adagios will commit any changes it makes to git repository."))
    enable_loghandler = forms.BooleanField(
        required=False, initial=settings.enable_loghandler, help_text=_("If set. Adagios will log any changes it makes to a file."))
    enable_authorization = forms.BooleanField(
        required=False, initial=settings.enable_authorization,
        help_text=_("If set. Users in Status view will only see hosts/services they are a contact for. Unset means everyone will see everything."))
    enable_status_view = forms.BooleanField(
        required=False, initial=settings.enable_status_view,
        help_text=_("If set. Enable status view which is an alternative to nagios legacy web interface. You will need to restart web server for the changes to take effect"))
    auto_reload = forms.BooleanField(
        required=False, initial=settings.auto_reload,
        help_text=_("If set. Nagios is reloaded automatically after every change."))
    warn_if_selinux_is_active = forms.BooleanField(
        required=False, help_text=_("Adagios does not play well with SElinux. So lets issue a warning if it is active. Only disable this if you know what you are doing."))
    pnp_filepath = forms.CharField(
        help_text=_("Full path to your pnp4nagios/index.php file. Adagios will use this to generate graphs"))
    pnp_url = forms.CharField(
        help_text=_("Full or relative url to pnp4nagios web interface, adagios can use this to link directly to pnp"))
    map_center = forms.CharField(
        help_text=_("Default coordinates when opening up the world map. This should be in the form of longitude,latitude"))
    map_zoom = forms.CharField(
        help_text=_("Default Zoom level when opening up the world map. 10 is a good default value"))
    language = forms.ChoiceField(choices=settings.LANGUAGES, required=False)
    theme = forms.ChoiceField(required=False, choices=[(x,x) for x in adagios.utils.get_available_themes()])
    refresh_rate = forms.IntegerField(
        help_text="For pages that auto-reload. Set the number of seconds to wait between page refreshes. "
                  "Set refresh rate to 0 to disable automatic refreshing."
    )
    enable_graphite = forms.BooleanField(required=False, help_text="If set. Include graphite graphs in status views")
    graphite_url = forms.CharField(help_text="Path to your graphite install.", required=False)
    graphite_querystring = forms.CharField(help_text="Querystring that is passed into graphite's /render method. {host} is replaced with respective hostname while {host_} will apply common graphite escaping. i.e. example.com -> example_com", required=False)
    graphite_title = forms.CharField(help_text="Use this title on all graphs coming from graphite", required=False)
    include = forms.CharField(
        required=False, help_text=_("Include configuration options from files matching this pattern"))

    def save(self):
        # First of all, if configfile does not exist, lets try to create it:
        if not os.path.isfile(settings.adagios_configfile):
            open(settings.adagios_configfile, 'w').write(
                _("# Autocreated by adagios"))
        for k, v in self.cleaned_data.items():
            Model.config._edit_static_file(
                attribute=k, new_value=v, filename=settings.adagios_configfile)
            self.adagios_configfile = settings.adagios_configfile
            #settings.__dict__[k] = v

    def __init__(self, *args, **kwargs):
        # Since this form is always bound, lets fetch current configfiles and
        # prepare them as post:
        if 'data' not in kwargs or kwargs['data'] == '':
            kwargs['data'] = settings.__dict__
        super(self.__class__, self).__init__(*args, **kwargs)

    def clean_pnp_filepath(self):
        filename = self.cleaned_data['pnp_filepath']
        return self.check_file_exists(filename)

    def clean_destination_directory(self):
        filename = self.cleaned_data['destination_directory']
        return self.check_file_exists(filename)

    def clean_nagios_init_script(self):
        filename = self.cleaned_data['nagios_init_script']
        if filename.startswith('sudo'):
            self.check_file_exists(filename.split()[1])
        else:
            self.check_file_exists(filename)
        return filename

    def clean_nagios_binary(self):
        filename = self.cleaned_data['nagios_binary']
        return self.check_file_exists(filename)

    def clean_nagios_config(self):
        filename = self.cleaned_data['nagios_config']
        return self.check_file_exists(filename)

    def check_file_exists(self, filename):
        """ Raises validation error if filename does not exist """
        if not os.path.exists(filename):
            raise forms.ValidationError('No such file or directory')
        return filename

    def clean(self):
        cleaned_data = super(self.__class__, self).clean()
        for k, v in cleaned_data.items():
            # Convert all unicode to quoted strings
            if type(v) == type(u''):
                cleaned_data[k] = str('''"%s"''' % v)
            # Convert all booleans to True/False strings
            elif type(v) == type(False):
                cleaned_data[k] = str(v)
        return cleaned_data


class EditAllForm(forms.Form):

    """ This form intelligently modifies all attributes of a specific type.


    """

    def __init__(self, object_type, attribute, new_value, *args, **kwargs):
        self.object_type = object_type
        self.attribute = attribute
        self.new_value = new_value
        super(self.__class__, self).__init__(self, args, kwargs)
        search_filter = {}
        search_filter['object_type'] = object_type
        search_filter['%s__isnot' % attribute] = new_value
        items = Model.ObjectDefinition.objects.filter(**search_filter)
        interesting_objects = []
        for i in items:
            if attribute in i._defined_attributes or i.use is None:
                interesting_objects.append(i)
        self.interesting_objects = interesting_objects
        for i in interesting_objects:
            self.fields['modify_%s' % i.get_id()] = forms.BooleanField(
                required=False, initial=True)


class PNPActionUrlForm(forms.Form):

    """ This form handles applying action_url to bunch of hosts and services """
    #apply_action_url = forms.BooleanField(required=False,initial=True,help_text="If set, apply action_url to every service object in nagios")
    action_url = forms.CharField(
        required=False, initial="/pnp4nagios/graph?host=$HOSTNAME$&srv=$SERVICEDESC$",
        help_text=_("Reset the action_url attribute of every service check in your nagios configuration with this one. "))

    def save(self):
        action_url = self.cleaned_data['action_url']
        services = Model.Service.objects.filter(action_url__isnot=action_url)
        self.total_services = len(services)
        self.error_services = 0
        for i in services:
            if 'action_url' in i._defined_attributes or i.use is None:
                i.action_url = action_url
                try:
                    i.save()
                except Exception:
                    self.error_services += 1


class PNPTemplatesForm(forms.Form):

    """ This form manages your pnp4nagios templates """

    def __init__(self, *args, **kwargs):
        self.template_directories = []
        self.templates = []
        tmp = Model.config._load_static_file('/etc/pnp4nagios/config.php')
        for k, v in tmp:
            if k == "$conf['template_dirs'][]":
                # strip all ' and " from directory
                directory = v.strip(";").strip('"').strip("'")
                self.template_directories.append(directory)
                if os.path.isdir(directory):
                    for f in os.listdir(directory):
                        self.templates.append("%s/%s" % (directory, f))

        super(self.__class__, self).__init__(*args, **kwargs)


class PNPConfigForm(forms.Form):

    """ This form handles the npcd.cfg configuration file """
    user = forms.CharField(
        help_text=_("npcd service will have privileges of this group"))
    group = forms.CharField(
        help_text=_("npcd service will have privileges of this user"))
    log_type = forms.ChoiceField(
        widget=forms.RadioSelect, choices=pnp_log_type_choices, help_text=_("Define if you want to log to 'syslog' or 'file'"))
    log_file = forms.CharField(
        help_text=_("If log_type is set to file. Log to this file"))
    max_logfile_size = forms.IntegerField(
        help_text=_("Defines the maximum filesize (bytes) before logfile will rotate."))
    log_level = forms.ChoiceField(
        help_text=_("How much should we log?"), choices=pnp_loglevel_choices)
    perfdata_spool_dir = forms.CharField(
        help_text=_("where we can find the performance data files"))
    perfdata_file_run_cmd = forms.CharField(
        help_text=_("execute following command for each found file in perfdata_spool_dir"))
    perfdata_file_run_cmd_args = forms.CharField(
        required=False, help_text=_("optional arguments to perfdata_file_run_cmd"))
    identify_npcd = forms.ChoiceField(widget=forms.RadioSelect, choices=(
        ('1', 'Yes'), ('0', 'No')), help_text=_("If yes, npcd will append -n to the perfdata_file_run_cmd"))
    npcd_max_threads = forms.IntegerField(
        help_text=_("Define how many parallel threads we should start"))
    sleep_time = forms.IntegerField(
        help_text=_("How many seconds npcd should wait between dirscans"))
    load_threshold = forms.FloatField(
        help_text=_("npcd won't start if load is above this threshold"))
    pid_file = forms.CharField(help_text=_("Location of your pid file"))
    perfdata_file = forms.CharField(
        help_text=_("Where should npcdmod.o write the performance data. Must not be same directory as perfdata_spool_dir"))
    perfdata_spool_filename = forms.CharField(
        help_text=_("Filename for the spooled files"))
    perfdata_file_processing_interval = forms.IntegerField(
        help_text=_("Interval between file processing"))

    def __init__(self, initial=None, *args, **kwargs):
        if not initial:
            initial = {}
        my_initial = {}
        # Lets use PNPBrokerModuleForm to find sensible path to npcd config
        # file
        broker_form = PNPBrokerModuleForm()
        self.npcd_cfg = broker_form.initial.get('config_file')
        npcd_values = Model.config._load_static_file(self.npcd_cfg)
        for k, v in npcd_values:
            my_initial[k] = v
        super(self.__class__, self).__init__(
            initial=my_initial, *args, **kwargs)

    def save(self):
        for i in self.changed_data:
            Model.config._edit_static_file(
                attribute=i, new_value=self.cleaned_data[i], filename=self.npcd_cfg)


class EditFileForm(forms.Form):

    """ Manages editing of a single file """
    filecontent = forms.CharField(widget=forms.Textarea(
        attrs={'wrap': 'off', 'rows': '50', 'cols': '2000'}))

    def __init__(self, filename, initial=None, *args, **kwargs):
        if not initial:
            initial = {}
        self.filename = filename
        my_initial = initial.copy()
        if 'filecontent' not in my_initial:
            my_initial['filecontent'] = open(filename).read()
        super(self.__class__, self).__init__(
            initial=my_initial, *args, **kwargs)

    def save(self):
        if 'filecontent' in self.changed_data:
            data = self.cleaned_data['filecontent']
            open(self.filename, 'w').write(data)


class PNPBrokerModuleForm(forms.Form):

    """ This form is responsible for configuring PNP4Nagios. """
    #enable_pnp= forms.BooleanField(required=False, initial=True,help_text="If set, PNP will be enabled and will graph Nagios Performance Data.")
    broker_module = forms.CharField(
        help_text=_("Full path to your npcdmod.o broker module that shipped with your pnp4nagios installation"))
    config_file = forms.CharField(
        help_text=_("Full path to your npcd.cfg that shipped with your pnp4nagios installation"))
    event_broker_options = forms.IntegerField(
        initial="-1", help_text=_("Nagios's default of -1 is recommended here. PNP Documentation says you will need at least bits 2 and 3. Only change this if you know what you are doing."))
    process_performance_data = forms.BooleanField(
        required=False, initial=True, help_text=_("PNP Needs the nagios option process_performance_data enabled to function. Make sure it is enabled."))
    #apply_action_url = forms.BooleanField(required=False,initial=True,help_text="If set, apply action_url to every service object in nagios")
    #action_url=forms.CharField(required=False,initial="/pnp4nagios/graph?host=$HOSTNAME$&srv=$SERVICEDESC$", help_text="Action url that your nagios objects can use to access perfdata")

    def clean_broker_module(self):
        """ Raises validation error if filename does not exist """
        filename = self.cleaned_data['broker_module']
        if not os.path.exists(filename):
            raise forms.ValidationError('File not found')
        return filename

    def clean_config_file(self):
        """ Raises validation error if filename does not exist """
        filename = self.cleaned_data['config_file']
        if not os.path.exists(filename):
            raise forms.ValidationError('File not found')
        return filename

    def __init__(self, initial=None, *args, **kwargs):
        if not initial:
            initial = {}
        my_initial = {}
        Model.config.parse()
        maincfg_values = Model.config.maincfg_values
        self.nagios_configline = None
        for k, v in Model.config.maincfg_values:
            if k == 'broker_module' and v.find('npcdmod.o') > 0:
                self.nagios_configline = v
                v = v.split()
                my_initial['broker_module'] = v.pop(0)
                for i in v:
                    if i.find('config_file=') > -1:
                        my_initial['config_file'] = i.split('=', 1)[1]
            elif k == "event_broker_options":
                my_initial[k] = v
        # If view specified any initial values, they overwrite ours
        for k, v in initial.items():
            my_initial[k] = v
        if 'broker_module' not in my_initial:
            my_initial['broker_module'] = self.get_suggested_npcdmod_path()
        if 'config_file' not in my_initial:
            my_initial['config_file'] = self.get_suggested_npcd_path()
        super(self.__class__, self).__init__(
            initial=my_initial, *args, **kwargs)

    def get_suggested_npcdmod_path(self):
        """ Returns best guess for full path to npcdmod.o file """
        possible_locations = [
            "/usr/lib/pnp4nagios/npcdmod.o",
            "/usr/lib64/nagios/brokers/npcdmod.o",
        ]
        for i in possible_locations:
            if os.path.isfile(i):
                return i
        return possible_locations[-1]

    def get_suggested_npcd_path(self):
        """ Returns best guess for full path to npcd.cfg file """
        possible_locations = [
            "/etc/pnp4nagios/npcd.cfg"
        ]
        for i in possible_locations:
            if os.path.isfile(i):
                return i
        return possible_locations[-1]

    def save(self):
        if 'broker_module' in self.changed_data or 'config_file' in self.changed_data or self.nagios_configline is None:
            v = "%s config_file=%s" % (
                self.cleaned_data['broker_module'], self.cleaned_data['config_file'])
            Model.config._edit_static_file(
                attribute="broker_module", new_value=v, old_value=self.nagios_configline, append=True)

        # We are supposed to handle process_performance_data attribute.. lets
        # do that here
        process_performance_data = "1" if self.cleaned_data[
            'process_performance_data'] else "0"
        Model.config._edit_static_file(
            attribute="process_performance_data", new_value=process_performance_data)

        # Update event broker only if it has changed
        name = "event_broker_options"
        if name in self.changed_data:
            Model.config._edit_static_file(
                attribute=name, new_value=self.cleaned_data[name])


class PluginOutputForm(forms.Form):
    plugin_output = forms.CharField(
        widget=forms.Textarea(attrs={'wrap': 'off', 'cols': '80'}))

    def parse(self):
        from pynag import Utils
        plugin_output = self.cleaned_data['plugin_output']
        output = Utils.PluginOutput(plugin_output)
        self.results = output


class NagiosServiceForm(forms.Form):

    """ Maintains control of the nagios service / reload / restart / etc """
    #path_to_init_script = forms.CharField(help_text="Path to your nagios init script", initial=NAGIOS_INIT)
    #nagios_binary = forms.CharField(help_text="Path to your nagios binary", initial=NAGIOS_BIN)
    #command = forms.ChoiceField(choices=COMMAND_CHOICES)

    def save(self):
        #nagios_bin = self.cleaned_data['nagios_bin']
        if "reload" in self.data:
            command = "reload"
        elif "restart" in self.data:
            command = "restart"
        elif "stop" in self.data:
            command = "stop"
        elif "start" in self.data:
            command = "start"
        elif "status" in self.data:
            command = "status"
        elif "verify" in self.data:
            command = "verify"
        else:
            raise Exception(_("Unknown command"))
        self.command = command
        nagios_init = settings.nagios_init_script
        nagios_binary = settings.nagios_binary
        nagios_config = settings.nagios_config or pynag.Model.config.cfg_file
        if command == "verify":
            command = "%s -v '%s'" % (nagios_binary, nagios_config)
        else:
            command = "%s %s" % (nagios_init, command)
        code, stdout, stderr = pynag.Utils.runCommand(command)
        self.stdout = stdout or ""
        self.stderr = stderr or ""
        self.exit_code = code

    def verify(self):
        """ Run "nagios -v nagios.cfg" and returns errors/warning

        Returns:
        [
            {'errors': []},
            {'warnings': []}
        ]
        """
        nagios_binary = settings.nagios_binary
        nagios_config = settings.nagios_config
        command = "%s -v '%s'" % (nagios_binary, nagios_config)
        code, stdout, stderr = pynag.Utils.runCommand(command)
        self.stdout = stdout or None
        self.stderr = stderr or None
        self.exit_code = code

        for line in stdout.splitlines():
            line = line.strip()
            warnings = []
            errors = []
            if line.lower.startswith('warning:'):
                warning = {}


class SendEmailForm(forms.Form):

    """ Form used to send email to one or more contacts regarding particular services
    """
    to = forms.CharField(
        required=True,
        help_text=_("E-mail address"),
    )
    message = forms.CharField(
        widget=forms.widgets.Textarea(attrs={'rows': 15, 'cols': 40}),
        required=False,
        help_text=_("Message that is to be sent to recipients"),
    )
    add_myself_to_cc = forms.BooleanField(
        required=False,
        help_text=_("If checked, you will be added automatically to CC")
    )
    acknowledge_all_problems = forms.BooleanField(
        required=False,
        help_text=_("If checked, also acknowledge all problems as they are sent")
    )

    def __init__(self, remote_user, *args, **kwargs):
        """ Create a new instance of SendEmailForm, contact name and email is used as from address.
        """
        self.remote_user = remote_user
        #self.contact_email = contact_email
        self.html_content = _("There is now HTML content with this message.")
        self.services = []
        self.hosts = []
        self.status_objects = []
        self._resolve_remote_user(self.remote_user)
        super(self.__class__, self).__init__(*args, **kwargs)

    def save(self):

        subject = _("%s sent you a a message through adagios") % self.remote_user

        cc_address = []
        from_address = self._resolve_remote_user(self.remote_user)
        # Check if _resolve_remote_user did in fact return an email address - avoid SMTPSenderRefused.
        import re # re built in Py1.5+
        if re.compile('([\w\-\.]+@(\w[\w\-]+\.)+[\w\-]+)').search(from_address) is None:
            from_address = str(from_address) + '@no.domain'
        to_address = self.cleaned_data['to']
        to_address = to_address.split(',')
        text_content = self.cleaned_data['message']
        text_content = text_content.replace('\n','<br>')

        # self.html_content is rendered in misc.views.mail()
        html_content = text_content + "<p></p>" + self.html_content
        if self.cleaned_data['add_myself_to_cc']:
            cc_address.append(from_address)
        if self.cleaned_data['acknowledge_all_problems']:
            comment = _("Sent mail to %s") % self.cleaned_data['to']
            self.acknowledge_all_services(comment)
            self.acknowledge_all_hosts(comment)
        # Here we actually send some email:

        msg = EmailMultiAlternatives(
            subject=subject, body=text_content, from_email=from_address, cc=cc_address, to=to_address)
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    def acknowledge_all_hosts(self, comment):
        """ Acknowledge all problems in self.hosts
        """
        for i in self.hosts:
            host_name = i.get('host_name')
            sticky = "1"
            persistent = "0"
            notify = "0"
            author = self.remote_user

            pynag.Control.Command.acknowledge_host_problem(host_name=host_name,
                                                          sticky=sticky,
                                                          persistent=persistent,
                                                          notify=notify,
                                                          author=author,
                                                          comment=comment)
    def acknowledge_all_services(self, comment):
        """ Acknowledge all problems in self.services
        """
        for i in self.services:
            host_name = i.get('host_name')
            service_description = i.get('description')
            sticky = "1"
            persistent = "0"
            notify = "0"
            author = self.remote_user

            pynag.Control.Command.acknowledge_svc_problem(host_name=host_name,
                                                          service_description=service_description,
                                                          sticky=sticky,
                                                          persistent=persistent,
                                                          notify=notify,
                                                          author=author,
                                                          comment=comment)

    def _resolve_remote_user(self, username):
        """ Returns a valid "Full Name <email@example.com>" for remote http authenticated user.
         If Remote user is a nagios contact, then return: Contact_Alias <contact_email>"
         Else if remote user is a valid email address, return that address
         Else return None
        """
        import adagios.status.utils
        livestatus = adagios.status.utils.livestatus(request=None)
        try:
            contact = livestatus.get_contact(username)
            return "%s <%s>" % (contact.get('alias'), contact.get('email'))
        except IndexError:
            # If we get here, then remote_user does not exist as a contact.
            return username





class PasteForm(forms.Form):
    paste = forms.CharField(initial=initial_paste, widget=forms.Textarea())

    def parse(self):
        c = pynag.Parsers.config()
        self.config = c
        c.reset()
        paste = self.cleaned_data['paste']
        # Also convert raw paste into a string so we can display errors at the
        # right place:
        self.pasted_string = paste.splitlines()
        items = c.parse_string(paste)
        c.pre_object_list = items
        c._post_parse()
        all_objects = []
        for object_type, objects in c.data.items():
            model = pynag.Model.string_to_class.get(
                object_type, pynag.Model.ObjectDefinition)
            for i in objects:
                Class = pynag.Model.string_to_class.get(
                    i['meta']['object_type'])
                my_object = Class(item=i)
                all_objects.append(my_object)
        self.objects = all_objects

########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/python
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

Convenient stateless functions for pynag. This module is used by the /rest/ interface of adagios.

"""


import platform
import re
from pynag import Model
from pynag import Parsers
from pynag import Control
from pynag import Utils
from pynag import __version__
from socket import gethostbyname_ex
import adagios.settings
from django.utils.translation import ugettext as _


#_config = Parsers.config(adagios.settings.nagios_config)
#_config.parse()
version = __version__


def _get_dict(x):
    x.__delattr__('objects')
    return x._original_attributes


def get_objects(object_type=None, with_fields="id,shortname,object_type", **kwargs):
    """ Get any type of object definition in a dict-compatible fashion

        Arguments:
            object_type (optional) -- Return objects of this type
            with_fields (optional) -- comma seperated list of objects to show (default=id,shortname,object_type)
            any other argument is passed on as a filter to pynag
        Examples:
            # show all active hosts and their ip address
            get_objects(object_type="host", register="1", with_fields="host_name,address")
            # show all attributes of all services
            get_objects(object_type="service", with_fields='*')
        Returns:
            List of ObjectDefinition
    """

    tmp = Model.ObjectDefinition.objects.filter(
        object_type=object_type, **kwargs)
    with_fields = with_fields.split(',')
    # return map(lambda x: _get_dict(x), tmp)
    return map(lambda x: object_to_dict(x, attributes=with_fields), tmp)


def servicestatus(with_fields="host_name,service_description,current_state,plugin_output"):
    """ Returns a list of all active services and their current status """
    s = Parsers.status()
    s.parse()
    fields = with_fields.split(',')
    result_list = []
    for serv in s.data['servicestatus']:
        current_object = {}
        for k, v in serv.items():
            if fields == ['*'] or k in fields:
                current_object[k] = v
        result_list.append(current_object)
    return result_list


def object_to_dict(object, attributes="id,shortname,object_type"):
    """ Takes in a specific object definition, returns a hash maps with "attributes" as keys"""
    result = {}
    if not attributes or attributes == '*':
        return object._original_attributes
    elif isinstance(attributes, list):
        pass
    else:
        attributes = attributes.split(',')
    for k in attributes:
        result[k] = object[k]
    return result


def get_object(id, with_fields="id,shortname,object_type"):
    """Returns one specific ObjectDefinition"""
    o = Model.ObjectDefinition.objects.get_by_id(id)
    return object_to_dict(o, attributes=with_fields)


def delete_object(object_id, recursive=False, cleanup_related_items=True):
    """ Delete one specific ObjectDefinition

    Arguments:
      object_id             -- The pynag id of the definition you want to delete
      cleanup_related_items -- If True, clean up references to this object in other definitions
      recursive             -- If True, also remove other objects that depend on this one.
                               For example, when deleting a host, also delete all its services
    Returns:
      True on success. Raises exception on failure.
    """

    o = Model.ObjectDefinition.objects.get_by_id(object_id)
    o.delete(recursive=recursive, cleanup_related_items=cleanup_related_items)
    return True


def get_host_names(invalidate_cache=False):
    """ Returns a list of all hosts """
    if invalidate_cache is True:
        raise NotImplementedError()
    all_hosts = Model.Host.objects.all
    hostnames = []
    for i in all_hosts:
        if not i['host_name'] is None:
            hostnames.append(i['host_name'])
    return sorted(hostnames)


def change_attribute(id, attribute_name, new_value):
    """Changes object with the designated ID to file

    Arguments:
        id                -- object_id of the definition to be saved
        attribute_name    -- name of the attribute (i.e. "host_name")
        new_value         -- new value (i.e. "host.example.com")
    """
    o = Model.ObjectDefinition.objects.get_by_id(id)
    o[attribute_name] = new_value
    o.save()


def change_service_attribute(identifier, new_value):
    """
    Change one service that is identified in the form of:
    host_name::service_description::attribute_name

    Examples:
    >>> change_service_attribute("localhost::Ping::service_description", "Ping2")

    Returns:
        True on success,
    Raises:
        Exception on error
    """
    tmp = identifier.split('::')
    if len(tmp) != 3:
        raise ValueError(
            _("identifier must be in the form of host_name::service_description::attribute_name (got %s)") % identifier)
    host_name, service_description, attribute_name = tmp
    try:
        service = Model.Service.objects.get_by_shortname(
            "%s/%s" % (host_name, service_description))
    except KeyError, e:
        raise KeyError(_("Could not find service %s") % e)
    service[attribute_name] = new_value
    service.save()
    return True


def copy_object(object_id, recursive=False, **kwargs):
    """ Copy one objectdefinition.

    Arguments:
        object_id -- id of the object to be copied
        recursive -- If True, also copy related child objects
        **kwargs  -- Any other argument will be treated as an attribute
                  -- to change on the new object
    Returns:
        "Object successfully copied"
    Examples:
        copy_object(1234567890, host_name=new_hostname)
        "Object successfully copied to <filename>"
    """
    o = Model.ObjectDefinition.objects.get_by_id(object_id)
    new_object = o.copy(recursive=recursive, **kwargs)
    return _("Object successfully copied to %s") % new_object.get_filename()


def run_check_command(object_id):
    """ Runs the check_command for one specified object

    Arguments:
        object_id         -- object_id of the definition (i.e. host or service)
    Returns:
        [return_code,stdout,stderr]
    """
    if platform.node() == 'adagios.opensource.is':
        return 1, _('Running check commands is disabled in demo-environment')
    o = Model.ObjectDefinition.objects.get_by_id(object_id)
    return o.run_check_command()


def set_maincfg_attribute(attribute, new_value, old_value='None', append=False):
    """ Sets specific configuration values of nagios.cfg

        Required Arguments:
                attribute   -- Attribute to change (i.e. process_performance_data)
                new_value   -- New value for the attribute (i.e. "1")

        Optional Arguments:
                old_value   -- Specify this to change specific value
                filename    -- Configuration file to modify (i.e. /etc/nagios/nagios.cfg)
                append      -- Set to 'True' to append a new configuration attribute
        Returns:
                True	-- If any changes were made
                False	-- If no changes were made
        """
    filename = Model.config.cfg_file
    if old_value.lower() == 'none':
        old_value = None
    if new_value.lower() == 'none':
        new_value = None
    if filename.lower() == 'none':
        filename = None
    if append.lower() == 'false':
        append = False
    elif append.lower() == 'true':
        append = True
    elif append.lower() == 'none':
        append = None
    return Model.config._edit_static_file(attribute=attribute, new_value=new_value, old_value=old_value, filename=filename, append=append)


def reload_nagios():
    """ Reloads nagios. Returns "Success" on Success """
    daemon = Control.daemon(
        nagios_cfg=Model.config.cfg_file,
        nagios_init=adagios.settings.nagios_init_script,
        nagios_bin=adagios.settings.nagios_binary
    )
    result = {}
    if daemon.reload() == 0:
        result['status'] = _("success")
        result['message'] = _('Nagios Successfully reloaded')
    else:
        result['status'] = _("error")
        result['message'] = _("Failed to reload nagios (do you have enough permissions?)")
    return result


def needs_reload():
    """ Returns True if Nagios server needs to reload configuration """
    return Model.config.needs_reload()


def dnslookup(host_name):
    try:
        (name, aliaslist, addresslist) = gethostbyname_ex(host_name)
        return {'host': name, 'aliaslist': aliaslist, 'addresslist': addresslist}
    except Exception, e:
        return {'error': str(e)}


def contactgroup_hierarchy(**kwargs):
    result = []
    try:
        groups = Model.Contactgroup.objects.all
        for i in groups:
            display = {}
            display['v'] = i.contactgroup_name
            display['f'] = '%s<div style="color:green; font-style:italic">%s contacts</div>' % (
                i.contactgroup_name, 0)
            arr = [display, i.contactgroup_members or '', str(i)]
            result.append(arr)
        return result
    except Exception, e:
        return {'error': str(e)}


def add_object(object_type, filename=None, **kwargs):
    """ Create one specific object definition and store it in nagios.

    Arguments:
        object_type  -- What kind of object to create (host, service,contactgroup, etc)
        filename     -- Which configuration file to store the object in. If filename=None pynag will decide
                     -- where to store the file
        **kwargs     -- Any other arguments will be treated as an attribute for the new object definition

    Returns:
        {'filename':XXX, 'raw_definition':XXX}
    Examples:
        add_object(object_type=host, host_name="localhost.example", address="127.0.0.1", use="generic-host"
    """
    my_object = Model.string_to_class.get(object_type)()
    if filename is not None:
        my_object.set_filename(filename)
    for k, v in kwargs.items():
        my_object[k] = v
    my_object.save()
    return {"filename": my_object.get_filename(), "raw_definition": str(my_object)}


def check_command(host_name, service_description, name=None, check_command=None, **kwargs):
    """ Returns all macros of a given service/host
        Arguments:
            host_name           -- Name of host
            service_description -- Service description
            check_command       -- Name of check command

            Any **kwargs will be treated as arguments or custom macros that will be changed on-the-fly before returning
        Returns:
            dict similar to the following:
            { 'host_name': ...,
              'service_description': ...,
              'check_command': ...,
              '$ARG1$': ...,
              '$SERVICE_MACROx$': ...,
            }
    """
    if host_name in ('None', None, ''):
        my_object = Model.Service.objects.get_by_name(name)
    elif service_description in ('None', None, '', u''):
        my_object = Model.Host.objects.get_by_shortname(host_name)
    else:
        short_name = "%s/%s" % (host_name, service_description)
        my_object = Model.Service.objects.get_by_shortname(short_name)
    if check_command in (None, '', 'None'):
        command = my_object.get_effective_check_command()
    else:
        command = Model.Command.objects.get_by_shortname(check_command)

    # Lets put all our results in a nice little dict
    macros = {}
    cache = Model.ObjectFetcher._cache_only
    try:
        Model.ObjectFetcher._cache_only = True
        macros['check_command'] = command.command_name
        macros['original_command_line'] = command.command_line
        macros['effective_command_line'] = my_object.get_effective_command_line()

        # Lets get all macros that this check command defines:
        regex = re.compile("(\$\w+\$)")
        macronames = regex.findall(command.command_line)
        for i in macronames:
            macros[i] = my_object.get_macro(i) or ''

        if not check_command:
            # Argument macros are special (ARGX), lets display those as is, without resolving it to the fullest
            ARGs = my_object.check_command.split('!')
            for i, arg in enumerate(ARGs):
                if i == 0:
                    continue

                macronames = regex.findall(arg)
                for m in macronames:
                    macros[m] = my_object.get_macro(m) or ''
                macros['$ARG{i}$'.format(i=i)] = arg
    finally:
        Model.ObjectFetcher._cache_only = cache
    return macros


def verify_configuration():
    """ Verifies nagios configuration and returns the output of nagios -v nagios.cfg
    """
    binary = adagios.settings.nagios_binary
    config = adagios.settings.nagios_config
    command = "%s -v '%s'" % (binary, config)
    code, stdout, stderr = Utils.runCommand(command)

    result = {}
    result['return_code'] = code
    result['output'] = stdout
    result['errors'] = stderr

    return result


def get_object_statistics():
    """ Returns a list of all object_types with total number of configured objects

    Example result:
    [
      {"object_type":"host", "total":50},
      {"object_type":"service", "total":50},
    ]
    """
    object_types = []
    Model.ObjectDefinition.objects.reload_cache()
    for k, v in Model.ObjectFetcher._cached_object_type.items():
        total = len(v)
        object_types.append({"object_type": k, "total": total})
    return object_types


def autocomplete(q):
    """ Returns a list of {'hosts':[], 'hostgroups':[],'services':[]} matching search query q
    """
    if q is None:
        q = ''
    result = {}

    hosts = Model.Host.objects.filter(host_name__contains=q)
    services = Model.Service.objects.filter(service_description__contains=q)
    hostgroups = Model.Hostgroup.objects.filter(hostgroup_name__contains=q)

    result['hosts'] = sorted(set(map(lambda x: x.host_name, hosts)))
    result['hostgroups'] = sorted(set(map(lambda x: x.hostgroup_name, hostgroups)))
    result['services'] = sorted(set(map(lambda x: x.service_description, services)))

    return result

########NEW FILE########
__FILENAME__ = models
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

# Create your models here.


class TestModel(models.Model):
    testField = models.CharField(max_length=100)
    testField2 = models.CharField(max_length=100)


class BusinessProcess(models.Model):
    processes = models.ManyToManyField("self", unique=False, blank=True)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=1000, blank=True)
    #graphs = models.ManyToManyField(BusinessProcess, unique=False, blank=True)
    #graphs = models.ManyToManyField(BusinessProcess, unique=False, blank=True)


class Graph(models.Model):
    host_name = models.CharField(max_length=100)
    service_description = models.CharField(max_length=100)
    metric_name = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = rest
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2012, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

This is a rest interface used by the "/rest/" module that affects adagios directly.

"""

from adagios import __version__, notifications, tasks
from adagios.settings import plugins
from adagios import userdata
from django.utils.translation import ugettext as _

version = __version__


def add_notification(level="info", message="message", notification_id=None, notification_type=None, user=None):
    """ Add a new notification to adagios notification bar.

    Arguments:
      level                      -- pick "info" "success" "error" "danger"
      message                    -- Arbitary text message,
      notification_id (optional) -- Use this if you want to remote
                                 -- remove this notification later via clear_notification()
      notification_type          -- Valid options: "generic" and "show_once"

      user                       -- If specified, only display notification for this specific user.

    Returns:
      None

    Examples:
    >>> add_notification(level="warning", message="Nagios needs to reload")
    """
    if not notification_id:
        notification_id = str(message.__hash__())
    if not notification_type:
        notification_type = "generic"
    notification = locals()
    notifications[notification_id] = notification


def clear_notification(notification_id):
    """ Clear one notification from adagios notification panel """
    if notification_id in notifications:
        del notifications[notification_id]
        return "success"
    return "not found"


def get_notifications(request):
    """ Shows all current notifications """
    result = []
    for k in notifications.keys():
        i = notifications[k]
        if i.get('user') and i.get('user') != request.META.get('remote_user'):
            continue # Skipt this message if it is meant for someone else
        elif i.get('notification_type') == 'show_once':
            del notifications[k]
            pass
        result.append(i)
    return result


def clear_all_notifications():
    """ Removes all notifications from adagios notification panel """
    notifications.clear()
    return "all notifications cleared"


def list_tasks():
    """

    """
    result = []
    for task in tasks:
        current_task = {
            'task_id': task.get_id(),
            'task_status': task.status()
            }
        result.append(current_task)
    return result


def get_task(task_id="someid"):
    """ Return information about one specific background task """
    for task in tasks:
        if str(task.get_id) == str(task_id) or task_id:
            current_task = {
                'task_id': task.get_id(),
                'task_status': task.status()
            }
            return current_task
    raise KeyError(_("Task not '%s' Found") % task_id)

def get_user_preferences(request):
    try:
        user = userdata.User(request)
    except Exception as e:
        raise e
    return user.to_dict()

def set_user_preference(request, **kwargs):
    try:
        user = userdata.User(request)
    except Exception as e:
        raise e
    
    for (k, v) in kwargs.iteritems():
        if not k.startswith('_'):
            user.set_pref(k, v)
    user.save()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.utils import unittest
from django.test.client import Client
import adagios.utils
import os


class FakeAdagiosEnvironment(unittest.TestCase):
    """ Test the features of adagios.utils.FakeAdagiosEnvironment
    """
    @classmethod
    def setUpClass(cls):
        cls.fake_adagios = adagios.utils.FakeAdagiosEnvironment()

    @classmethod
    def tearDownClass(cls):
        cls.fake_adagios.terminate()

    def testFakeAdagiosEnvironment(self):
        fake_adagios = self.fake_adagios

        # Make sure temporary environment gets created
        fake_adagios.create_minimal_environment()
        self.assertTrue(os.path.exists(fake_adagios.adagios_config_file))

        # Make sure adagios.settings is updated
        global_config_file = adagios.settings.adagios_configfile
        fake_adagios.update_adagios_global_variables()

        # Make sure adagios_config_file changed
        self.assertTrue(adagios.settings.adagios_configfile != global_config_file)

        # Make sure the new test is in the tempdir
        self.assertTrue(adagios.settings.adagios_configfile.startswith(fake_adagios.tempdir))

        # Make sure global variables are proparly restored
        fake_adagios.restore_adagios_global_variables()
        self.assertTrue(adagios.settings.adagios_configfile == global_config_file)


class MiscTestCase(unittest.TestCase):

    def setUp(self):
        self.environment = adagios.utils.FakeAdagiosEnvironment()
        self.environment.create_minimal_environment()
        self.environment.update_adagios_global_variables()

    def tearDown(self):
        self.environment.terminate()

    def _testPageLoad(self, url):
        c = Client()
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

    def TestPageLoads(self):
        """ Smoke test views in /misc/
        """
        self.loadPage("/misc/settings")
        self.loadPage("/misc/preferences")
        self.loadPage("/misc/nagios")
        self.loadPage("/misc/settings")
        self.loadPage("/misc/service")
        self.loadPage("/misc/pnp4nagios")
        self.loadPage("/misc/mail")
        self.loadPage("/misc/images")

    def loadPage(self, url):
        """ Load one specific page, and assert if return code is not 200 """
        try:
            c = Client()
            response = c.get(url)
            self.assertEqual(response.status_code, 200, _("Expected status code 200 for page %s") % url)
        except Exception, e:
            self.assertEqual(True, _("Unhandled exception while loading %(url)s: %(e)s") % {'url': url, 'e': e})

    def test_user_preferences(self):
        c = Client()
        response = c.post('/misc/preferences/',
                          {'theme': 'spacelab', 'language': 'fr'})

        assert(response.status_code == 200)
        assert('spacelab/style.css' in response.content)
        assert('(fr)' in response.content)

    def load_get(self, url):
        c = Client()
        response = c.get(url)
        return response
    
    def test_topmenu_highlight(self):
        r = self.load_get('/status/')
        assert '<li class="active">\n  <a href="/status">' in r.content
    
    def test_leftmenu_highlight(self):
        r = self.load_get('/status/problems')
        assert '<li class="active">\n          <a href="/status/problems">' in r.content
    
    def test_app_name(self):
        from adagios import settings
        settings.TOPMENU_HOME = 'Free beer'
        r = self.load_get('/status')
        assert 'Free beer' in r.content


########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
                      (r'^/test/?', 'adagios.misc.views.test'),
                      (r'^/paste/?', 'adagios.misc.views.paste'),
                      (r'^/?$', 'adagios.misc.views.index'),

                      (r'^/settings/?', 'adagios.misc.views.settings'),
                      (r'^/preferences/?', 'adagios.misc.views.preferences'),
                      (r'^/nagios/?', 'adagios.misc.views.nagios'),
                      (r'^/iframe/?', 'adagios.misc.views.iframe'),
                      (r'^/gitlog/?', 'adagios.misc.views.gitlog'),
                      (r'^/service/?', 'adagios.misc.views.nagios_service'),
                      (r'^/pnp4nagios/?$', 'adagios.misc.views.pnp4nagios'),
                      (r'^/pnp4nagios/edit(?P<filename>.+)$', 'adagios.misc.views.pnp4nagios_edit_template'),
                      (r'^/mail', 'adagios.misc.views.mail'),
                       url(r'^/images/(?P<path>.+)$', 'django.views.static.serve', {'document_root': '/usr/share/nagios3/htdocs/images/logos/'}, name="logo"),
                      (r'^/images/?$', 'adagios.misc.views.icons'),
                      )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.core.context_processors import csrf
from django.forms.formsets import BaseFormSet
from django.shortcuts import render_to_response
from django.shortcuts import render
from django.utils.translation import ugettext as _

from django.shortcuts import HttpResponse
from django.template import RequestContext
from adagios.misc import forms
import os
import mimetypes

import pynag.Model
import pynag.Utils
import pynag.Control
import pynag.Model.EventHandlers
import pynag.Utils
import os.path
from time import mktime, sleep
from datetime import datetime
from os.path import dirname
from subprocess import Popen, PIPE

import adagios.settings
import adagios.objectbrowser
from adagios import __version__
import adagios.status.utils
from adagios import userdata

from collections import defaultdict
from adagios.views import adagios_decorator, error_page

state = defaultdict(lambda: "unknown")
state[0] = "ok"
state[1] = "warning"
state[2] = "critical"

@adagios_decorator
def index(request):
    c = {}
    c['nagios_cfg'] = pynag.Model.config.cfg_file
    c['version'] = __version__
    return render_to_response('frontpage.html', c, context_instance=RequestContext(request))

@adagios_decorator
def settings(request):
    c = {}
    c.update(csrf(request))
    c['messages'] = m = []
    c['errors'] = e = []
    if request.method == 'GET':
        form = forms.AdagiosSettingsForm(initial=request.GET)
        form.is_valid()
    elif request.method == 'POST':
        form = forms.AdagiosSettingsForm(data=request.POST)
        if form.is_valid():
            try:
                form.save()
                m.append(_("%s successfully saved.") % form.adagios_configfile)
            except IOError, exc:
                e.append(exc)
    else:
        raise Exception(_("We only support methods GET or POST"))
    c['form'] = form
    return render_to_response('settings.html', c, context_instance=RequestContext(request))


@adagios_decorator
def nagios(request):
    return iframe(request, adagios.settings.nagios_url)

@adagios_decorator
def iframe(request, url=None):
    if not url:
        url = request.GET.get('url', None)
    return render_to_response('iframe.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def gitlog(request):
    """ View that displays a nice log of previous git commits in dirname(config.cfg_file) """
    c = {}
    c.update(csrf(request))
    c['messages'] = m = []
    c['errors'] = []

    # Get information about the committer
    author_name = request.META.get('REMOTE_USER', 'anonymous')
    try:
        contact = pynag.Model.Contact.objects.get_by_shortname(author_name)
        author_email = contact.email or None
    except Exception:
        author_email = None
    nagiosdir = dirname(pynag.Model.config.cfg_file or None)
    git = pynag.Utils.GitRepo(
        directory=nagiosdir, author_name=author_name, author_email=author_email)

    c['nagiosdir'] = nagiosdir
    c['commits'] = []
    if request.method == 'POST':

        try:
            if 'git_init' in request.POST:
                git.init()
            elif 'git_commit' in request.POST:
                filelist = []
                commit_message = request.POST.get(
                    'git_commit_message', _("bulk commit by adagios"))
                for i in request.POST:
                    if i.startswith('commit_'):
                        filename = i[len('commit_'):]
                        git.add(filename)
                        filelist.append(filename)
                if len(filelist) == 0:
                    raise Exception(_("No files selected."))
                git.commit(message=commit_message, filelist=filelist)
                m.append(_("%s files successfully commited.") % len(filelist))
        except Exception, e:
            c['errors'].append(e)
    # Check if nagiosdir has a git repo or not
    try:
        c['uncommited_files'] = git.get_uncommited_files()
    except pynag.Model.EventHandlers.EventHandlerError, e:
        if e.errorcode == 128:
            c['no_git_repo_found'] = True

    # Show git history
    try:
        c['commits'] = git.log()

        commit = request.GET.get('show', False)
        if commit != False:
            c['diff'] = git.show(commit)
            difflines = []
            for i in c['diff'].splitlines():
                if i.startswith('---'):
                    tag = 'hide'
                elif i.startswith('+++'):
                    tag = 'hide'
                elif i.startswith('index'):
                    tag = 'hide'
                elif i.startswith('-'):
                    tag = "alert-danger"
                elif i.startswith('+'):
                    tag = "alert-success"
                elif i.startswith('@@'):
                    tag = 'alert-unknown'
                elif i.startswith('diff'):
                    tag = "filename"
                else:
                    continue
                difflines.append({'tag': tag, 'line': i})
            c['difflines'] = difflines
            c['commit_id'] = commit
    except Exception, e:
        c['errors'].append(e)
    return render_to_response('gitlog.html', c, context_instance=RequestContext(request))


@adagios_decorator
def nagios_service(request):
    """ View to restart / reload nagios service """
    c = {}
    c['errors'] = []
    c['messages'] = []
    nagios_bin = adagios.settings.nagios_binary
    nagios_init = adagios.settings.nagios_init_script
    nagios_cfg = adagios.settings.nagios_config
    if request.method == 'GET':
        form = forms.NagiosServiceForm(initial=request.GET)
    else:
        form = forms.NagiosServiceForm(data=request.POST)
        if form.is_valid():
            form.save()
            c['stdout'] = form.stdout
            c['stderr'] = form.stderr
            c['command'] = form.command

            for i in form.stdout.splitlines():
                if i.strip().startswith('Error:'):
                    c['errors'].append(i)
    c['form'] = form
    service = pynag.Control.daemon(
        nagios_bin=nagios_bin, nagios_cfg=nagios_cfg, nagios_init=nagios_init)
    c['status'] = s = service.status()
    if s == 0:
        c['friendly_status'] = "running"
    elif s == 1:
        c['friendly_status'] = "not running"
    else:
        c['friendly_status'] = 'unknown (exit status %s)' % (s, )
    needs_reload = pynag.Model.config.needs_reload()
    c['needs_reload'] = needs_reload
    return render_to_response('nagios_service.html', c, context_instance=RequestContext(request))


@adagios_decorator
def pnp4nagios(request):
    """ View to handle integration with pnp4nagios """
    c = {}
    c['errors'] = e = []
    c['messages'] = m = []

    c['broker_module'] = forms.PNPBrokerModuleForm(initial=request.GET)
    c['templates_form'] = forms.PNPTemplatesForm(initial=request.GET)
    c['action_url'] = forms.PNPActionUrlForm(initial=request.GET)
    c['pnp_templates'] = forms.PNPTemplatesForm(initial=request.GET)

    try:
        c['npcd_config'] = forms.PNPConfigForm(initial=request.GET)
    except Exception, e:
        c['errors'].append(e)
    #c['interesting_objects'] = form.interesting_objects
    if request.method == 'POST' and 'save_broker_module' in request.POST:
        c['broker_module'] = broker_form = forms.PNPBrokerModuleForm(
            data=request.POST)
        if broker_form.is_valid():
            broker_form.save()
            m.append(_("Broker Module updated in nagios.cfg"))
    elif request.method == 'POST' and 'save_action_url' in request.POST:
        c['action_url'] = forms.PNPActionUrlForm(data=request.POST)
        if c['action_url'].is_valid():
            c['action_url'].save()
            m.append(_('Action_url updated for %s services') %
                     c['action_url'].total_services)
            if c['action_url'].error_services > 0:
                e.append(
                    _("%s services could not be updated (check permissions?)") %
                    c['action_url'].error_services)
    elif request.method == 'POST' and 'save_npcd_config' in request.POST:
        c['npcd_config'] = forms.PNPConfigForm(data=request.POST)
        if c['npcd_config'].is_valid():
            c['npcd_config'].save()
            m.append(_("npcd.cfg updated"))

    return render_to_response('pnp4nagios.html', c, context_instance=RequestContext(request))


@adagios_decorator
def edit_file(request, filename):
    """ This view gives raw read/write access to a given filename.

     Please be so kind as not to give direct url access to this function, because it will allow
     Editing of any file the webserver has access to.
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    try:
        c['form'] = forms.EditFileForm(filename=filename, initial=request.GET)
        c['filename'] = filename
        if request.method == 'POST':
            c['form'] = forms.EditFileForm(
                filename=filename, data=request.POST)
            if c['form'].is_valid():
                c['form'].save()
    except Exception, e:
        c['errors'].append(e)
    return render_to_response('editfile.html', c, context_instance=RequestContext(request))


@adagios_decorator
def edit_nagios_cfg(request):
    """ Allows raw editing of nagios.cfg configfile
    """
    return edit_file(request, filename=adagios.settings.nagios_config)


@adagios_decorator
def pnp4nagios_edit_template(request, filename):
    """ Allows raw editing of a pnp4nagios template.

     Will throw security exception if filename is not a pnp4nagios template
    """

    form = forms.PNPTemplatesForm(initial=request.GET)
    if filename in form.templates:
        return edit_file(request, filename=filename)
    else:
        raise Exception(
            _("Security violation. You are not allowed to edit %s") % filename)


@adagios_decorator
def icons(request, image_name=None):
    """ Use this view to see nagios icons/logos
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    image_path = '/usr/share/nagios3/htdocs/images/logos/'
    filenames = []
    for root, subfolders, files in os.walk(image_path):
        for filename in files:
            filenames.append(os.path.join(root, filename))
    # Cut image_path out of every filename
    filenames = map(lambda x: x[len(image_path):], filenames)

    # Filter out those silly .gd2 files that don't display inside a browser
    filenames = filter(lambda x: not x.lower().endswith('.gd2'), filenames)

    filenames.sort()
    if not image_name:
        # Return a list of images
        c['images'] = filenames
        return render_to_response('icons.html', c, context_instance=RequestContext(request))
    else:
        if image_name in filenames:
            file_extension = image_name.split('.').pop()
            mime_type = mimetypes.types_map.get(file_extension)
            fsock = open("%s/%s" % (image_path, image_name,))
            return HttpResponse(fsock, mimetype=mime_type)
        else:
            raise Exception(_("Not allowed to see this image"))


@adagios_decorator
def mail(request):
    """ Send a notification email to one or more contacts regarding hosts or services """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c.update(csrf(request))
    c['http_referer'] = request.META.get("HTTP_REFERER")
    c['http_origin'] = request.META.get("HTTP_ORIGIN")
    remote_user = request.META.get('REMOTE_USER', 'anonymous adagios user')
    hosts = []
    services = []
    if request.method == 'GET':
        c['form'] = forms.SendEmailForm(remote_user, initial=request.GET)
        hosts = request.GET.getlist('host') or request.GET.getlist('host[]')
        services = request.GET.getlist(
            'service') or request.GET.getlist('service[]')
        if not services and not hosts:
            c['form'].services = adagios.status.utils.get_services(
                request, host_name='localhost')
    elif request.method == 'POST':
        c['form'] = forms.SendEmailForm(remote_user, data=request.POST)
        services = request.POST.getlist('service') or request.POST.getlist('service[]')
        hosts = request.POST.getlist('host') or request.POST.getlist('host[]')
        c['acknowledged_or_not'] = request.POST.get('acknowledge_all_problems') == 'true'

    for host_name in hosts:
        host_object = adagios.status.utils.get_hosts(request, host_name=host_name)
        if not host_object:
            c['errors'].append(
                _("Host %s not found. Maybe a typo or you do not have access to it.") % host_name
            )
            continue
        for item in host_object:
            item['host_name'] = item['name']
            item['description'] = _("Host Status")
            c['form'].status_objects.append(item)
            c['form'].hosts.append(item)

    for i in services:
        try:
            host_name, service_description = i.split('/', 1)
            service = adagios.status.utils.get_services(request,
                                                        host_name=host_name,
                                                        service_description=service_description
                                                        )
            if not service:
                c['errors'].append(
                    _('Service "%s"" not found. Maybe a typo or you do not have access to it ?') % i)
            for x in service:
                c['form'].status_objects.append(x)
                c['form'].services.append(x)
        except AttributeError, e:
            c['errors'].append(_("AttributeError for '%(i)s': %(e)s") % {'i': i, 'e': e})
        except KeyError, e:
            c['errors'].append(_("Error adding service '%(i)s': %(e)s") % {'i': i, 'e': e})

    c['services'] = c['form'].services
    c['hosts'] = c['form'].hosts
    c['status_objects'] = c['form'].status_objects
    c['form'].html_content = render(
        request, "snippets/misc_mail_objectlist.html", c).content
    if request.method == 'POST' and c['form'].is_valid():
        c['form'].save()
    return render_to_response('misc_mail.html', c, context_instance=RequestContext(request))



@adagios_decorator
def test(request):
    """ Generic test view, use this as a sandbox if you like
    """
    c = {}
    c['messages'] = []
    c.update(csrf(request))
    # Get some test data

    if request.method == 'POST':
        c['form'] = forms.PluginOutputForm(data=request.POST)
        if c['form'].is_valid():
            c['form'].parse()
    else:
        c['form'] = forms.PluginOutputForm(initial=request.GET)

    return render_to_response('test.html', c, context_instance=RequestContext(request))


@adagios_decorator
def paste(request):
    """ Generic test view, use this as a sandbox if you like
    """
    c = {}
    c['messages'] = []
    c.update(csrf(request))
    # Get some test data

    if request.method == 'POST':
        c['form'] = forms.PasteForm(data=request.POST)
        if c['form'].is_valid():
            c['form'].parse()
    else:
        c['form'] = forms.PasteForm(initial=request.GET)

    return render_to_response('test2.html', c, context_instance=RequestContext(request))

@adagios_decorator
def preferences(request):
    c = {}
    c['messages'] = []
    c.update(csrf(request))
    
    user = userdata.User(request)
    
    if request.method == 'POST':
        c['form'] = forms.UserdataForm(data=request.POST)
        if c['form'].is_valid():
            for k, v in c['form'].cleaned_data.iteritems():
                user.set_pref(k, v)
            user.save() # will save in json and trigger the hooks
            c['messages'].append(_('Preferences have been saved.'))
    else:
        c['form'] = forms.UserdataForm(initial=user.to_dict())

    return render_to_response('userdata.html', c, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = models
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *

urlpatterns = patterns('adagios',
                      (r'^/?$', 'myapp.views.hello_world'),
                      (r'^/url1?$', 'myapp.views.hello_world'),
                      (r'^/url2?$', 'myapp.views.hello_world'),
                       )

########NEW FILE########
__FILENAME__ = views
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Create your views here.
from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.shortcuts import HttpResponse
from django.shortcuts import RequestContext


def hello_world(request):
    """ This is an example view. """
    c = {}
    return render_to_response("myapp_helloworld.html", c, context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from pynag import Model
from pynag.Utils import AttributeList
from adagios.objectbrowser.help_text import object_definitions
from pynag.Model import ObjectDefinition
from adagios.forms import AdagiosForm
import adagios.misc.rest


# These fields are special, they are a comma seperated list, and may or
# may not have +/- in front of them.
MULTICHOICE_FIELDS = ('servicegroups', 'hostgroups', 'contacts',
                      'contact_groups', 'contactgroups', 'use', 'notification_options')

SERVICE_NOTIFICATION_OPTIONS = (
    ('w', 'warning'),
    ('c', 'critical'),
    ('r', 'recovery'),
    ('u', 'unreachable'),
    ('d', 'downtime'),
    ('f', 'flapping'),
)

HOST_NOTIFICATION_OPTIONS = (
    ('d', 'down'),
    ('u', 'unreachable'),
    ('r', 'recovery'),
    ('f', 'flapping'),
    ('s', 'scheduled_downtime')
)


BOOLEAN_CHOICES = (('', 'not set'), ('1', '1'), ('0', '0'))


class PynagChoiceField(forms.MultipleChoiceField):

    """ multichoicefields that accepts comma seperated input as values """

    def __init__(self, inline_help_text=_("Select some options"), *args, **kwargs):
        self.__prefix = ''
        self.data = kwargs.get('data')
        super(PynagChoiceField, self).__init__(*args, **kwargs)
        self.widget.attrs['data-placeholder'] = inline_help_text

    def clean(self, value):
        """
        Changes list into a comma separated string. Removes duplicates.
        """
        if not value:
            return "null"
        tmp = []
        for i in value:
            if i not in tmp:
                tmp.append(i)
        value = self.__prefix + ','.join(tmp)
        return value

    def prepare_value(self, value):
        """
        Takes a comma separated string, removes + if it is prefixed so. Returns a list
        """
        if isinstance(value, str):
            self.attributelist = AttributeList(value)
            self.__prefix = self.attributelist.operator
            return self.attributelist.fields
        return value


class PynagRadioWidget(forms.widgets.HiddenInput):

    """ Special Widget designed to make Nagios attributes with 0/1 values look like on/off buttons """

    def render(self, name, value, attrs=None):
        output = super(PynagRadioWidget, self).render(name, value, attrs)
        one, zero, unset = "", "", ""
        if value == "1":
            one = "active"
        elif value == "0":
            zero = "active"
        else:
            unset = "active"
        prefix = """
        <div class="btn-group" data-toggle-name="%s" data-toggle="buttons-radio">
          <button type="button" value="1" class="btn btn %s">On</button>
          <button type="button" value="0" class="btn btn %s">Off</button>
          <button type="button" value="" class="btn %s">Not set</button>
        </div>
        """ % (name, one, zero, unset)
        output += prefix
        return mark_safe(output)


class PynagForm(AdagiosForm):

    def clean(self):
        cleaned_data = super(PynagForm, self).clean()
        for k, v in cleaned_data.items():
            # change from unicode to str
            v = cleaned_data[k] = smart_str(v)

            # Empty string, or the string None, means remove the field
            if v in ('', 'None'):
                cleaned_data[k] = v = None

            # Maintain operator (+,-, !) for multichoice fields
            if k in MULTICHOICE_FIELDS and v and v != "null":
                operator = AttributeList(self.pynag_object.get(k, '')).operator or ''
                cleaned_data[k] = "%s%s" % (operator, v)
        return cleaned_data

    def save(self):
        changed_keys = map(lambda x: smart_str(x), self.changed_data)
        for k in changed_keys:

            # Ignore fields that did not appear in the POST at all EXCEPT
            # If it it a pynagchoicefield. That is because multichoicefield that
            # does not appear in the post, means that the user removed every attribute
            # in the multichoice field
            if k not in self.data and not isinstance(self.fields.get(k, None), PynagChoiceField):
                continue

            value = self.cleaned_data[k]

            # Sometimes attributes slide in changed_data without having
            # been modified, lets ignore those
            if self.pynag_object[k] == value:
                continue

            # Multichoice fields have a special restriction, sometimes they contain
            # the same values as before but in a different order.
            if k in MULTICHOICE_FIELDS:
                original = AttributeList(self.pynag_object[k])
                new = AttributeList(value)
                if sorted(original.fields) == sorted(new.fields):
                    continue            # If we reach here, it is save to modify our pynag object.

            # Here we actually make a change to our pynag object
            self.pynag_object[k] = value

            # Additionally, update the field for the return form
            self.fields[k] = self.get_pynagField(k, css_tag="defined")
            self.fields[k].value = value
        self.pynag_object.save()
        adagios.misc.rest.add_notification(message=_("Object successfully saved"), level="success", notification_type="show_once")

    def __init__(self, pynag_object, *args, **kwargs):
        self.pynag_object = pynag_object
        super(PynagForm, self).__init__(*args, **kwargs)
        # Lets find out what attributes to create
        object_type = pynag_object['object_type']
        defined_attributes = sorted(
            self.pynag_object._defined_attributes.keys())
        inherited_attributes = sorted(
            self.pynag_object._inherited_attributes.keys())
        all_attributes = sorted(object_definitions.get(object_type).keys())
        all_attributes += ['name', 'use', 'register']

        # Special hack for macros
        # If this is a post and any post data looks like a nagios macro
        # We will generate a field for it on the fly
        macros = filter(lambda x: x.startswith('$') and x.endswith('$'), self.data.keys())
        for field_name in macros:
            # if field_name.startswith('$ARG'):
            #    self.fields[field_name] = self.get_pynagField(field_name, css_tag='defined')
            if object_type == 'service' and field_name.startswith('$_SERVICE'):
                self.fields[field_name] = self.get_pynagField(
                    field_name, css_tag='defined')
            elif object_type == 'host' and field_name.startswith('$_HOST'):
                self.fields[field_name] = self.get_pynagField(
                    field_name, css_tag='defined')

        # Calculate what attributes are "undefined"
        self.undefined_attributes = []
        for i in all_attributes:
            if i in defined_attributes:
                continue
            if i in inherited_attributes:
                continue
            self.undefined_attributes.append(i)
        # Find out which attributes to show
        for field_name in defined_attributes:
            self.fields[field_name] = self.get_pynagField(
                field_name, css_tag='defined')
        for field_name in inherited_attributes:
            self.fields[field_name] = self.get_pynagField(
                field_name, css_tag="inherited")
        for field_name in self.undefined_attributes:
            self.fields[field_name] = self.get_pynagField(
                field_name, css_tag='undefined')
        return

    def get_pynagField(self, field_name, css_tag="", required=None):
        """ Takes a given field_name and returns a forms.Field that is appropriate for this field

          Arguments:
            field_name  --  Name of the field to add, example "host_name"
            css_tag     --  String will make its way as a css attribute in the resulting html
            required    --  If True, make field required. If None, let pynag decide
        """
        # Lets figure out what type of field this is, default to charfield
        object_type = self.pynag_object['object_type']
        definitions = object_definitions.get(object_type) or {}
        options = definitions.get(field_name) or {}

        # Find out what type of field to create from the field_name.
        # Lets assume charfield in the beginning
        field = forms.CharField()

        if False is True:
            pass
        elif field_name in ('contact_groups', 'contactgroups', 'contactgroup_members'):
                all_groups = Model.Contactgroup.objects.filter(
                    contactgroup_name__contains="")
                choices = sorted(
                    map(lambda x: (x.contactgroup_name, x.contactgroup_name), all_groups))
                field = PynagChoiceField(
                    choices=choices, inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif field_name == 'use':
            all_objects = self.pynag_object.objects.filter(name__contains='')
            choices = map(lambda x: (x.name, x.name), all_objects)
            field = PynagChoiceField(
                choices=sorted(choices), inline_help_text=_("No %s selected") % {'field_name': field_name})
        elif field_name in ('servicegroups', 'servicegroup_members'):
            all_groups = Model.Servicegroup.objects.filter(
                servicegroup_name__contains='')
            choices = map(
                lambda x: (x.servicegroup_name, x.servicegroup_name), all_groups)
            field = PynagChoiceField(
                choices=sorted(choices), inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif field_name in ('hostgroups', 'hostgroup_members', 'hostgroup_name') and object_type != 'hostgroup':
            all_groups = Model.Hostgroup.objects.filter(
                hostgroup_name__contains='')
            choices = map(
                lambda x: (x.hostgroup_name, x.hostgroup_name), all_groups)
            field = PynagChoiceField(
                choices=sorted(choices), inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif field_name == 'members' and object_type == 'hostgroup':
            all_groups = Model.Host.objects.filter(host_name__contains='')
            choices = map(lambda x: (x.host_name, x.host_name), all_groups)
            field = PynagChoiceField(
                choices=sorted(choices), inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif field_name == 'host_name' and object_type == 'service':
            all_groups = Model.Host.objects.filter(host_name__contains='')
            choices = map(lambda x: (x.host_name, x.host_name), all_groups)
            field = PynagChoiceField(
                choices=sorted(choices), inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif field_name in ('contacts', 'members'):
            all_objects = Model.Contact.objects.filter(
                contact_name__contains='')
            choices = map(
                lambda x: (x.contact_name, x.contact_name), all_objects)
            field = PynagChoiceField(
                choices=sorted(choices), inline_help_text=_("No %s selected") % {'field_name': field_name})
        elif field_name.endswith('_period'):
            all_objects = Model.Timeperiod.objects.filter(
                timeperiod_name__contains='')
            choices = [('', '')] + map(
                lambda x: (x.timeperiod_name, x.timeperiod_name), all_objects)
            field = forms.ChoiceField(choices=sorted(choices))
        elif field_name.endswith('notification_commands'):
            all_objects = Model.Command.objects.filter(
                command_name__contains='')
            choices = [('', '')] + map(
                lambda x: (x.command_name, x.command_name), all_objects)
            field = PynagChoiceField(choices=sorted(choices))
        # elif field_name == 'check_command':
        #    all_objects = Model.Command.objects.all
        #    choices = [('','')] + map(lambda x: (x.command_name, x.command_name), all_objects)
        #    field = forms.ChoiceField(choices=sorted(choices))
        elif field_name.endswith('notification_options') and self.pynag_object.object_type == 'host':
            field = PynagChoiceField(
                choices=HOST_NOTIFICATION_OPTIONS, inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif field_name.endswith('notification_options') and self.pynag_object.object_type == 'service':
            field = PynagChoiceField(
                choices=SERVICE_NOTIFICATION_OPTIONS, inline_help_text=_("No %(field_name)s selected") % {'field_name': field_name})
        elif options.get('value') == '[0/1]':
            field = forms.CharField(widget=PynagRadioWidget)

        # Lets see if there is any help text available for our field
        if field_name in object_definitions[object_type]:
            help_text = object_definitions[object_type][field_name].get(
                'help_text', _("No help available for this item"))
            field.help_text = help_text

        # No prettyprint for macros
        if field_name.startswith('_'):
            field.label = field_name

        # If any CSS tag was given, add it to the widget
        self.add_css_tag(field=field, css_tag=css_tag)

        if 'required' in options:
            self.add_css_tag(field=field, css_tag=options['required'])
            field.required = options['required'] == 'required'
        else:
            field.required = False

        # At the moment, our database of required objects is incorrect
        # So if caller did not specify if field is required, we will not
        # make it required
        if required is None:
            field.required = False
        else:
            field.required = required

        # Put inherited value in the placeholder
        inherited_value = self.pynag_object._inherited_attributes.get(
            field_name)
        if inherited_value is not None:
            self.add_placeholder(
                field, _('%(inherited_value)s (inherited from template)') % {'inherited_value': inherited_value})

        if field_name in MULTICHOICE_FIELDS:
            self.add_css_tag(field=field, css_tag="multichoice")

        return field

    def add_css_tag(self, field, css_tag):
        """ Add a CSS tag to the widget of a specific field """
        if not 'class' in field.widget.attrs:
            field.widget.attrs['class'] = ''
            field.css_tag = ''
        field.widget.attrs['class'] += " " + css_tag
        field.css_tag += " " + css_tag

    def add_placeholder(self, field, placeholder=_("Insert some value here")):
        field.widget.attrs['placeholder'] = placeholder
        field.placeholder = placeholder


class AdvancedEditForm(AdagiosForm):

    """ A form for pynag.Model.Objectdefinition

    This form will display a charfield for every attribute of the objectdefinition

    "Every" attribute means:
    * Every defined attribute
    * Every inherited attribute
    * Every attribute that is defined in nagios object definition html

    """
    register = forms.CharField(
        required=False, help_text=_("Set to 1 if you want this object enabled."))
    name = forms.CharField(required=False, label=_("Generic Name"),
                           help_text=_("This name is used if you want other objects to inherit (with the use attribute) what you have defined here."))
    use = forms.CharField(required=False, label=_("Use"),
                          help_text=_("Inherit all settings from another object"))
    __prefix = "advanced"  # This prefix will go on every field

    def save(self):
        for k in self.changed_data:
            # change from unicode to str
            value = smart_str(self.cleaned_data[k])
            # same as original, lets ignore that
            if self.pynag_object[k] == value:
                continue
            if value == '':
                value = None

            # If we reach here, it is save to modify our pynag object.
            self.pynag_object[k] = value
        self.pynag_object.save()

    def clean(self):
        cleaned_data = super(AdvancedEditForm, self).clean()
        for k, v in cleaned_data.items():
            # change from unicode to str
            cleaned_data[k] = smart_str(v)
        return cleaned_data

    def __init__(self, pynag_object, *args, **kwargs):
        self.pynag_object = pynag_object
        super(AdvancedEditForm, self).__init__(
            *args, prefix=self.__prefix, **kwargs)

        # Lets find out what attributes to create
        object_type = pynag_object['object_type']
        all_attributes = sorted(object_definitions.get(object_type).keys())
        for field_name in self.pynag_object.keys() + all_attributes:
            if field_name == 'meta':
                continue
            help_text = ""
            if field_name in object_definitions[object_type]:
                help_text = object_definitions[object_type][field_name].get(
                    'help_text', _("No help available for this item"))
            self.fields[field_name] = forms.CharField(
                required=False, label=field_name, help_text=help_text)
        self.fields.keyOrder = sorted(self.fields.keys())


class GeekEditObjectForm(AdagiosForm):
    definition = forms.CharField(
        widget=forms.Textarea(attrs={'wrap': 'off', 'cols': '80'}))

    def __init__(self, pynag_object=None, *args, **kwargs):
        self.pynag_object = pynag_object
        super(GeekEditObjectForm, self).__init__(*args, **kwargs)

    def clean_definition(self, value=None):
        definition = smart_str(self.cleaned_data['definition'])
        definition = definition.replace('\r\n', '\n')
        definition = definition.replace('\r', '\n')
        if not definition.endswith('\n'):
            definition += '\n'
        return definition

    def save(self):
        definition = self.cleaned_data['definition']
        self.pynag_object.rewrite(str_new_definition=definition)


class DeleteObjectForm(AdagiosForm):

    """ Form used to handle deletion of one single object """

    def __init__(self, pynag_object, *args, **kwargs):
        self.pynag_object = pynag_object
        super(DeleteObjectForm, self).__init__(*args, **kwargs)
        if self.pynag_object.object_type == 'host':
            recursive = forms.BooleanField(
                required=False, initial=True, label=_("Delete Services"),
                help_text=_("Check this box if you also want to delete all services of this host"))
            self.fields['recursive'] = recursive

    def delete(self):
        """ Deletes self.pynag_object. """
        recursive = False
        if 'recursive' in self.cleaned_data and self.cleaned_data['recursive'] is True:
            recursive = True
        self.pynag_object.delete(recursive)


class CopyObjectForm(AdagiosForm):

    """ Form to assist a user to copy a single object definition
    """

    def __init__(self, pynag_object, *args, **kwargs):
        self.pynag_object = pynag_object
        super(CopyObjectForm, self).__init__(*args, **kwargs)
        object_type = pynag_object['object_type']

        # For templates we assume the new copy will have its generic name changed
        # otherwise we display different field depending on what type of an
        # object it is
        if pynag_object['register'] == '0':
            if pynag_object.name is None:
                new_generic_name = "%s-copy" % pynag_object.get_description()
            else:
                new_generic_name = '%s-copy' % pynag_object.name
            self.fields['name'] = forms.CharField(
                initial=new_generic_name, help_text=_("Select a new generic name for this %(object_type)s") % {'object_type': object_type})
        elif object_type == 'host':
            new_host_name = "%s-copy" % pynag_object.get_description()
            self.fields['host_name'] = forms.CharField(
                help_text=_("Select a new host name for this host"), initial=new_host_name)
            self.fields['address'] = forms.CharField(
                help_text=_("Select a new ip address for this host"))
            self.fields['recursive'] = forms.BooleanField(
                required=False, label="Copy Services", help_text=_("Check this box if you also want to copy all services of this host."))
        elif object_type == 'service':
            service_description = "%s-copy" % pynag_object.service_description
            self.fields['host_name'] = forms.CharField(
                help_text=_("Select a new host name for this service"), initial=pynag_object.host_name)
            self.fields['service_description'] = forms.CharField(
                help_text=_("Select new service description for this service"), initial=service_description)
        else:
            field_name = "%s_name" % object_type
            initial = "%s-copy" % pynag_object[field_name]
            help_text = object_definitions[
                object_type][field_name].get('help_text')
            if help_text == '':
                help_text = _("Please specify a new %(field_name)s") % {'field_name': field_name}
            self.fields[field_name] = forms.CharField(
                initial=initial, help_text=help_text)

    def save(self):
        # If copy() returns a single object, lets transform it into a list
        tmp = self.pynag_object.copy(**self.cleaned_data)
        if not type(tmp) == type([]):
            tmp = [tmp]
        self.copied_objects = tmp

    def _clean_shortname(self):
        """ Make sure shortname of a particular object does not exist.

        Raise validation error if shortname is found
        """
        object_type = self.pynag_object.object_type
        field_name = "%s_name" % object_type
        value = smart_str(self.cleaned_data[field_name])
        try:
            self.pynag_object.objects.get_by_shortname(value)
            raise forms.ValidationError(
                _("A %(object_type)s with %(field_name)s='%(value)s' already exists.") % {'object_type': object_type,
                                                                                          'field_name': field_name,
                                                                                          'value': value,
                                                                                         })
        except KeyError:
            return value

    def clean_host_name(self):
        if self.pynag_object.object_type == 'service':
            return smart_str(self.cleaned_data['host_name'])
        return self._clean_shortname()

    def clean_timeperiod_name(self):
        return self._clean_shortname()

    def clean_command_name(self):
        return self._clean_shortname()

    def clean_contactgroup_name(self):
        return self._clean_shortname()

    def clean_hostgroup_name(self):
        return self._clean_shortname()

    def clean_servicegroup_name(self):
        return self._clean_shortname()

    def clean_contact_name(self):
        return self._clean_shortname()


class BaseBulkForm(AdagiosForm):

    """ To make changes to multiple objects at once

    * any POST data that has the name change_<OBJECTID> will be fetched
    and the ObjectDefinition saved in self.changed_objects
    * any POST data that has the name hidden_<OBJECTID> will be fetched
    and the ObjectDefinition saved in self.all_objects
    """

    def __init__(self, objects=None, *args, **kwargs):
        self.objects = []
        self.all_objects = []
        self.changed_objects = []
        if not objects:
            objects = []
        forms.Form.__init__(self, *args, **kwargs)
        for k, v in self.data.items():
            if k.startswith('hidden_'):
                obj = Model.ObjectDefinition.objects.get_by_id(v)
                if obj not in self.all_objects:
                    self.all_objects.append(obj)
            if k.startswith('change_'):
                object_id = k[len("change_"):]
                obj = Model.ObjectDefinition.objects.get_by_id(object_id)
                if obj not in self.changed_objects:
                    self.changed_objects.append(obj)
                if obj not in self.all_objects:
                    self.all_objects.append(obj)

    def clean(self):
        #self.cleaned_data = {}
        for k, v in self.data.items():
            if k.startswith('hidden_'):
                self.cleaned_data[k] = v
                obj = Model.ObjectDefinition.objects.get_by_id(v)
                if obj not in self.all_objects:
                    self.all_objects.append(obj)
            if k.startswith('change_'):
                self.cleaned_data[k] = v
                object_id = k[len("change_"):]
                obj = Model.ObjectDefinition.objects.get_by_id(object_id)
                if obj not in self.changed_objects:
                    self.changed_objects.append(obj)
        for k, v in self.cleaned_data.items():
            self.cleaned_data[k] = smart_str(self.cleaned_data[k])
        return self.cleaned_data


class BulkEditForm(BaseBulkForm):
    attribute_name = forms.CharField()
    new_value = forms.CharField()

    def save(self):
        for i in self.changed_objects:
            key = self.cleaned_data['attribute_name']
            value = self.cleaned_data['new_value']
            i[key] = value
            i.save()


class BulkCopyForm(BaseBulkForm):
    attribute_name = forms.CharField()
    new_value = forms.CharField()

    def __init__(self, *args, **kwargs):
        BaseBulkForm.__init__(self, *args, **kwargs)
        self.fields['attribute_name'].value = "test 2"
        # Lets take a look at the first item to be copied and suggest a field
        # name to change

    def save(self):
        for i in self.changed_objects:
            key = self.cleaned_data['attribute_name']
            value = self.cleaned_data['new_value']
            kwargs = {key: value}
            i.copy(**kwargs)


class BulkDeleteForm(BaseBulkForm):

    """ Form used to delete multiple objects at once """
    yes_i_am_sure = forms.BooleanField(label=_("Yes, I am sure"))

    def delete(self):
        """ Deletes every object in the form """
        for i in self.changed_objects:
            if i.object_type == 'host':
                recursive = True
            else:
                recursive = False
            i.delete(recursive=recursive)


class CheckCommandForm(PynagForm):

    def __init__(self, *args, **kwargs):
        super(AdagiosForm, self).__init__(*args, **kwargs)
        self.pynag_object = Model.Service()
        self.fields['host_name'] = self.get_pynagField('host_name')
        self.fields['service_description'] = self.get_pynagField(
            'service_description')
        self.fields['check_command'] = self.get_pynagField('check_command')


choices_for_all_types = sorted(
    map(lambda x: (x, x), Model.string_to_class.keys()))


class AddTemplateForm(PynagForm):

    """ Use this form to add one template """
    object_type = forms.ChoiceField(choices=choices_for_all_types)
    name = forms.CharField(max_length=100)

    def __init__(self, *args, **kwargs):
        super(PynagForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AddTemplateForm, self).clean()
        if "object_type" not in cleaned_data:
            raise forms.ValidationError(_('Object type is required'))
        object_type = cleaned_data['object_type']
        name = cleaned_data['name']
        if object_type not in Model.string_to_class:
            raise forms.ValidationError(
                _("We dont know nothing about how to add a '%(object_type)s'") % {'object_type': object_type})
        objectdefinition = Model.string_to_class.get(object_type)
        # Check if name already exists
        try:
            objectdefinition.objects.get_by_name(name)
            raise forms.ValidationError(
                _("A %(object_type)s with name='%(name)s' already exists.") % {'object_type': object_type,
                                                                               'name': name,
                                                                               })
        except KeyError:
            pass
        self.pynag_object = objectdefinition()
        self.pynag_object['register'] = "0"

        return cleaned_data


class AddObjectForm(PynagForm):

    def __init__(self, object_type, initial=None, *args, **kwargs):
        self.pynag_object = Model.string_to_class.get(object_type)()
        super(AdagiosForm, self).__init__(*args, **kwargs)
        # Some object types we will suggest a template:
        if object_type in ('host', 'contact', 'service'):
            self.fields['use'] = self.get_pynagField('use')
            self.fields['use'].initial = str('generic-%s' % object_type)
            self.fields['use'].help_text = _("Inherit attributes from this template")
        if object_type == 'host':
            self.fields['host_name'] = self.get_pynagField('host_name', required=True)
            self.fields['address'] = self.get_pynagField('address', required=True)
            self.fields['alias'] = self.get_pynagField('alias', required=False)
        elif object_type == 'service':
            self.fields['service_description'] = self.get_pynagField('service_description', required=True)
            self.fields['host_name'] = self.get_pynagField('host_name', required=False)
            self.fields['host_name'].help_text = _('Tell us which host this service check will be applied to')
            self.fields['hostgroup_name'] = self.get_pynagField('hostgroup_name', required=False)
            self.fields['hostgroup_name'].help_text = _("If you specify any hostgroups, this service will be applied to all hosts in that hostgroup")
        else:
            field_name = "%s_name" % object_type
            self.fields[field_name] = self.get_pynagField(
                field_name, required=True)
        # For some reason calling super()__init__() with initial as a parameter
        # will not work on PynagChoiceFields. This forces initial value to be set:
        initial = initial or {}
        for field_name, field in self.fields.items():
            initial_value = initial.get(field_name, None)
            if initial_value:
                field.initial = str(initial_value)

    def clean(self):
        cleaned_data = super(AddObjectForm, self).clean()
        if self.pynag_object.object_type == 'service':
            host_name = cleaned_data.get('host_name')
            hostgroup_name = cleaned_data.get('hostgroup_name')
            if host_name in (None, 'None', '') and hostgroup_name in (None, 'None', ''):
                raise forms.ValidationError(_("Please specify either hostgroup_name or host_name"))
        return cleaned_data

    def clean_timeperiod_name(self):
        return self._clean_shortname()

    def clean_command_name(self):
        return self._clean_shortname()

    def clean_contactgroup_name(self):
        return self._clean_shortname()

    def clean_servicegroup_name(self):
        return self._clean_shortname()

    def clean_contact_name(self):
        return self._clean_shortname()

    def clean_host_name(self):
        if self.pynag_object.object_type == 'service':
            value = self.cleaned_data['host_name']
            if not value or value == 'null':
                return None
            hosts = value.split(',')
            for i in hosts:
                existing_hosts = Model.Host.objects.filter(host_name=i)
                if not existing_hosts:
                    raise forms.ValidationError(
                        _("Could not find host called '%(i)s'") % {'i': i})
                return smart_str(self.cleaned_data['host_name'])
        return self._clean_shortname()

    def clean_hostgroup_name(self):
        if self.pynag_object.object_type == 'service':
            value = self.cleaned_data['hostgroup_name']
            if value in (None, '', 'null'):
                return None
            groups = value.split(',')
            for i in groups:
                existing_hostgroups = Model.Hostgroup.objects.filter(hostgroup_name=i)
                if not existing_hostgroups:
                    raise forms.ValidationError(
                        _("Could not find hostgroup called '%(i)s'") % {'i': i})
                return smart_str(self.cleaned_data['hostgroup_name'])
        return self._clean_shortname()

    def _clean_shortname(self):
        """ Make sure shortname of a particular object does not exist.

        Raise validation error if shortname is found
        """
        object_type = self.pynag_object.object_type
        field_name = "%s_name" % object_type
        value = smart_str(self.cleaned_data[field_name])
        try:
            self.pynag_object.objects.get_by_shortname(value)
            raise forms.ValidationError(
                _("A %(object_type)s with %(field_name)s='%(value)s' already exists.") % {'object_type': object_type,
                                                                                          'field_name': field_name,
                                                                                          'value': value,
                                                                                          })
        except KeyError:
            return value

########NEW FILE########
__FILENAME__ = help_text
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" objectbrowser/all_attributes.py

This is an extends of pynag's all_attributes with friendly help message for all attributes.
"""

from pynag.Model.all_attributes import object_definitions
from django.utils.translation import ugettext as _


object_definitions["any"]["use"][
    "help_text"] = _("Specifies which object to inherit settings from")
object_definitions["any"]["register"][
    "help_text"] = _("Specifies if object is active (registered) or not")
object_definitions["any"]["name"][
    "help_text"] = _("Generic name of this objects. Only used for templates.")
object_definitions["host"]["host_name"]["help_text"] = _("e.g. web01.example.com")
object_definitions["host"]["alias"]["help_text"] = _("e.g. My Monitored Host")
object_definitions["host"]["display_name"]["help_text"] = _(" ")
object_definitions["host"]["address"]["help_text"] = _("e.g. 127.0.0.1")
object_definitions["host"]["parents"][
    "help_text"] = _("Network parents of this host. No notification will be sent if parent is down.")
object_definitions["host"]["hostgroups"][
    "help_text"] = _("Which hostgroups this host belongs to")
object_definitions["host"]["check_command"][
    "help_text"] = _("Command to execute when this object is checked")
object_definitions["host"]["initial_state"][
    "help_text"] = _('By default Nagios will assume that all hosts are in UP states when it starts. You can override the initial state for a host by using this directive. Valid options are: o = UP, d = DOWN, and u = UNREACHABLE.')
object_definitions["host"]["max_check_attempts"][
    "help_text"] = _("How many failures do occur before notifications will be sent")
object_definitions["host"]["check_interval"][
    "help_text"] = _("How many minutes to wait between checks")
object_definitions["host"]["retry_interval"][
    "help_text"] = _("How many minutes to wait between checks when object goes to warning or critical state")
object_definitions["host"]["active_checks_enabled"][
    "help_text"] = _("Whether Nagios actively checks this host")
object_definitions["host"]["passive_checks_enabled"][
    "help_text"] = _("Whether Nagios passively accepts check results from an external source")
object_definitions["host"]["check_period"][
    "help_text"] = _("When nagios checks for this host")
object_definitions["host"]["obsess_over_host"][
    "help_text"] = _('This directive determines whether or not checks for the host will be "obsessed" over using the ochp_command.')
object_definitions["host"]["check_freshness"]["help_text"] = _(" ")
object_definitions["host"]["freshness_threshold"]["help_text"] = _(" ")
object_definitions["host"]["event_handler"]["help_text"] = _(" ")
object_definitions["host"]["event_handler_enabled"]["help_text"] = _(" ")
object_definitions["host"]["low_flap_threshold"]["help_text"] = _(" ")
object_definitions["host"]["high_flap_threshold"]["help_text"] = _(" ")
object_definitions["host"]["flap_detection_enabled"]["help_text"] = _(" ")
object_definitions["host"]["flap_detection_options"]["help_text"] = _(" ")
object_definitions["host"]["process_perf_data"]["help_text"] = _(" ")
object_definitions["host"]["retain_status_information"]["help_text"] = _(" ")
object_definitions["host"]["retain_nonstatus_information"]["help_text"] = _(" ")
object_definitions["host"]["contacts"]["help_text"] = _(" ")
object_definitions["host"]["contact_groups"]["help_text"] = _(" ")
object_definitions["host"]["notification_interval"]["help_text"] = _(" ")
object_definitions["host"]["first_notification_delay"]["help_text"] = _(" ")
object_definitions["host"]["notification_period"]["help_text"] = _(" ")
object_definitions["host"]["notification_options"]["help_text"] = _(" ")
object_definitions["host"]["notifications_enabled"]["help_text"] = _(" ")
object_definitions["host"]["stalking_options"]["help_text"] = _(" ")
object_definitions["host"]["notes"]["help_text"] = _(" ")
object_definitions["host"]["notes_url"]["help_text"] = _(" ")
object_definitions["host"]["action_url"]["help_text"] = _(" ")
object_definitions["host"]["icon_image"]["help_text"] = _(" ")
object_definitions["host"]["icon_image_alt"]["help_text"] = _(" ")
object_definitions["host"]["vrml_image"]["help_text"] = _(" ")
object_definitions["host"]["statusmap_image"]["help_text"] = _(" ")
object_definitions["host"]["2d_coords"]["help_text"] = _(" ")
object_definitions["host"]["3d_coords"]["help_text"] = _(" ")
object_definitions["hostgroup"]["hostgroup_name"][
    "help_text"] = _("Unique name for this hostgroup (e.g. webservers)")
object_definitions["hostgroup"]["alias"][
    "help_text"] = _("Human friendly name (e.g. My Web Servers)")
object_definitions["hostgroup"]["members"][
    "help_text"] = _("List of hosts that belong to this group")
object_definitions["hostgroup"]["hostgroup_members"][
    "help_text"] = _("List of hostgroups that belong to this group")
object_definitions["hostgroup"]["notes"][
    "help_text"] = _("You can put your custom notes here for your hostgroup")
object_definitions["hostgroup"]["notes_url"][
    "help_text"] = _("Type in an url for example to a documentation site for this hostgroup")
object_definitions["hostgroup"]["action_url"]["help_text"] = _(" ")
object_definitions["service"]["host_name"][
    "help_text"] = _("e.g. web01.example.com")
object_definitions["service"]["hostgroup_name"][
    "help_text"] = _("Hostgroup this service belongs to")
object_definitions["service"]["service_description"][
    "help_text"] = _("e.g. 'Disk Status'")
object_definitions["service"]["display_name"]["help_text"] = _(" ")
object_definitions["service"]["servicegroups"][
    "help_text"] = _("Servicegroups that this service belongs to")
object_definitions["service"]["is_volatile"]["help_text"] = _(" ")
object_definitions["service"]["check_command"][
    "help_text"] = _("Command that is executed when this service is checked")
object_definitions["service"]["initial_state"]["help_text"] = _(" ")
object_definitions["service"]["max_check_attempts"][
    "help_text"] = _("How many times to try before failure notifications are sent out")
object_definitions["service"]["check_interval"][
    "help_text"] = _("How many minutes to wait between checks")
object_definitions["service"]["retry_interval"][
    "help_text"] = _("How many minutes to wait between checks when failure occurs")
object_definitions["service"]["active_checks_enabled"][
    "help_text"] = _("Enable if you want nagios to actively check this service")
object_definitions["service"]["passive_checks_enabled"][
    "help_text"] = _("Enable if you want nagios to passively accept check results from an external source")
object_definitions["service"]["check_period"][
    "help_text"] = _("Period which this service is checked.")
object_definitions["service"]["obsess_over_service"]["help_text"] = _(" ")
object_definitions["service"]["check_freshness"]["help_text"] = _(" ")
object_definitions["service"]["freshness_threshold"]["help_text"] = _(" ")
object_definitions["service"]["event_handler"]["help_text"] = _(" ")
object_definitions["service"]["event_handler_enabled"]["help_text"] = _(" ")
object_definitions["service"]["low_flap_threshold"]["help_text"] = _(" ")
object_definitions["service"]["high_flap_threshold"]["help_text"] = _(" ")
object_definitions["service"]["flap_detection_enabled"]["help_text"] = _(" ")
object_definitions["service"]["flap_detection_options"]["help_text"] = _(" ")
object_definitions["service"]["process_perf_data"]["help_text"] = _(" ")
object_definitions["service"]["retain_status_information"]["help_text"] = _(" ")
object_definitions["service"]["retain_nonstatus_information"]["help_text"] = _(" ")
object_definitions["service"]["notification_interval"]["help_text"] = _(" ")
object_definitions["service"]["first_notification_delay"]["help_text"] = _(" ")
object_definitions["service"]["notification_period"][
    "help_text"] = _("Period which notifications are sent out for this service")
object_definitions["service"]["notification_options"]["help_text"] = _(" ")
object_definitions["service"]["notifications_enabled"]["help_text"] = _(" ")
object_definitions["service"]["contacts"][
    "help_text"] = _("Which contacts to notify if service fails")
object_definitions["service"]["contact_groups"][
    "help_text"] = _("Which contactgroups to send notifications to if service fails")
object_definitions["service"]["stalking_options"]["help_text"] = _(" ")
object_definitions["service"]["notes"]["help_text"] = _(" ")
object_definitions["service"]["notes_url"]["help_text"] = _(" ")
object_definitions["service"]["action_url"]["help_text"] = _(" ")
object_definitions["service"]["icon_image"]["help_text"] = _(" ")
object_definitions["service"]["icon_image_alt"]["help_text"] = _(" ")
object_definitions["servicegroup"]["servicegroup_name"][
    "help_text"] = _("Unique name for this service group")
object_definitions["servicegroup"]["alias"][
    "help_text"] = _("Human friendly name for this servicegroup")
object_definitions["servicegroup"]["members"][
    "help_text"] = _("List of services that belong to this group (Example: localhost,CPU Utilization,localhost,Disk Usage)")
object_definitions["servicegroup"]["servicegroup_members"][
    "help_text"] = _("Servicegroups that are members of this servicegroup")
object_definitions["servicegroup"]["notes"][
    "help_text"] = _("Arbitrary notes or description of this servicegroup")
object_definitions["servicegroup"]["notes_url"][
    "help_text"] = _("Arbitrary url to a site of your choice")
object_definitions["servicegroup"]["action_url"][
    "help_text"] = _("Arbitrary url to a site of your choice")
object_definitions["contact"]["contact_name"][
    "help_text"] = _("Unique name for this contact (e.g. username@domain.com)")
object_definitions["contact"]["alias"][
    "help_text"] = _("Human Friendly Name for this contact (e.g. Full Name)")
object_definitions["contact"]["contactgroups"][
    "help_text"] = _("List of groups that this contact is a member of.")
object_definitions["contact"]["host_notifications_enabled"][
    "help_text"] = _("If this contact will receive host notifications.")
object_definitions["contact"]["service_notifications_enabled"][
    "help_text"] = _("If this contact will receive service notifications.")
object_definitions["contact"]["host_notification_period"][
    "help_text"] = _("When will this contact receive host notifications")
object_definitions["contact"]["service_notification_period"][
    "help_text"] = _("When will this contact receive service notifications")
object_definitions["contact"]["host_notification_options"][
    "help_text"] = _("Which host notifications this contact will receive")
object_definitions["contact"]["service_notification_options"][
    "help_text"] = _("Which service notifications this contact will receive")
object_definitions["contact"]["host_notification_commands"][
    "help_text"] = _("What command will be used to send host notifications to this contact")
object_definitions["contact"]["service_notification_commands"][
    "help_text"] = _("What command will be used to send service notifications to this contact")
object_definitions["contact"]["email"][
    "help_text"] = _("E-mail address of this contact")
object_definitions["contact"]["pager"][
    "help_text"] = _("Pager number of this contact")
object_definitions["contact"]["address"][
    "help_text"] = _("Address of this contact")
object_definitions["contact"]["can_submit_commands"][
    "help_text"] = _("If this contact is able to submit commands to nagios command pipe")
object_definitions["contact"]["retain_status_information"]["help_text"] = _(" ")
object_definitions["contact"]["retain_nonstatus_information"]["help_text"] = _(" ")
object_definitions["contactgroup"]["contactgroup_name"][
    "help_text"] = _("Unique name for this contact group (e.g. 'webservers')")
object_definitions["contactgroup"]["alias"][
    "help_text"] = _("Human Friendly Name (e.g. 'My Web Servers')")
object_definitions["contactgroup"]["members"][
    "help_text"] = _("Every Contact listed here will be a member of this contactgroup")
object_definitions["contactgroup"]["contactgroup_members"][
    "help_text"] = _("Every Contactgroup listed here will be a member of this contactgroup")
object_definitions["timeperiod"]["timeperiod_name"][
    "help_text"] = _("Unique name for this timeperiod (.e.g. 'workhours')")
object_definitions["timeperiod"]["alias"][
    "help_text"] = _("Human Friendly name for this timeperiod")
object_definitions["timeperiod"]["[weekday]"]["help_text"] = _(" ")
object_definitions["timeperiod"]["[exception]"]["help_text"] = _(" ")
object_definitions["timeperiod"]["exclude"]["help_text"] = _(" ")
object_definitions["command"]["command_name"][
    "help_text"] = _("Unique name for this command")
object_definitions["command"]["command_line"][
    "help_text"] = _("Command line of the command that will be executed")
object_definitions["servicedependency"][
    "dependent_host_name"]["help_text"] = _(" ")
object_definitions["servicedependency"][
    "dependent_hostgroup_name"]["help_text"] = _(" ")
object_definitions["servicedependency"][
    "dependent_service_description"]["help_text"] = _(" ")
object_definitions["servicedependency"]["host_name"]["help_text"] = _(" ")
object_definitions["servicedependency"]["hostgroup_name"]["help_text"] = _(" ")
object_definitions["servicedependency"][
    "service_description"]["help_text"] = _(" ")
object_definitions["servicedependency"]["inherits_parent"]["help_text"] = _(" ")
object_definitions["servicedependency"][
    "execution_failure_criteria"]["help_text"] = _(" ")
object_definitions["servicedependency"][
    "notification_failure_criteria"]["help_text"] = _(" ")
object_definitions["servicedependency"]["dependency_period"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["host_name"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["hostgroup_name"]["help_text"] = _(" ")
object_definitions["serviceescalation"][
    "service_description"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["contacts"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["contact_groups"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["first_notification"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["last_notification"]["help_text"] = _(" ")
object_definitions["serviceescalation"][
    "notification_interval"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["escalation_period"]["help_text"] = _(" ")
object_definitions["serviceescalation"]["escalation_options"]["help_text"] = _(" ")
object_definitions["hostdependency"]["dependent_host_name"]["help_text"] = _(" ")
object_definitions["hostdependency"][
    "dependent_hostgroup_name"]["help_text"] = _(" ")
object_definitions["hostdependency"]["host_name"]["help_text"] = _(" ")
object_definitions["hostdependency"]["hostgroup_name"]["help_text"] = _(" ")
object_definitions["hostdependency"]["inherits_parent"]["help_text"] = _(" ")
object_definitions["hostdependency"][
    "execution_failure_criteria"]["help_text"] = _(" ")
object_definitions["hostdependency"][
    "notification_failure_criteria"]["help_text"] = _(" ")
object_definitions["hostdependency"]["dependency_period"]["help_text"] = _(" ")
object_definitions["hostescalation"]["host_name"]["help_text"] = _(" ")
object_definitions["hostescalation"]["hostgroup_name"]["help_text"] = _(" ")
object_definitions["hostescalation"]["contacts"]["help_text"] = _(" ")
object_definitions["hostescalation"]["contact_groups"]["help_text"] = _(" ")
object_definitions["hostescalation"]["first_notification"]["help_text"] = _(" ")
object_definitions["hostescalation"]["last_notification"]["help_text"] = _(" ")
object_definitions["hostescalation"]["notification_interval"]["help_text"] = _(" ")
object_definitions["hostescalation"]["escalation_period"]["help_text"] = _(" ")
object_definitions["hostescalation"]["escalation_options"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["host_name"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["notes"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["notes_url"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["action_url"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["icon_image"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["icon_image_alt"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["vrml_image"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["statusmap_image"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["2d_coords"]["help_text"] = _(" ")
object_definitions["hostextinfo"]["3d_coords"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["host_name"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["service_description"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["notes"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["notes_url"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["action_url"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["icon_image"]["help_text"] = _(" ")
object_definitions["serviceextinfo"]["icon_image_alt"]["help_text"] = _(" ")

########NEW FILE########
__FILENAME__ = models
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

# Create your models here.


class Attribute(models.Model):

    """This class stores info on how attributes are viewed in django"""
    attribute_name = models.CharField(max_length=200)
    attribute_friendlyname = models.CharField(max_length=200)
    attribute_type = models.CharField(max_length=200)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.utils import unittest
from django.test.client import Client
from django.utils.translation import ugettext as _

import pynag.Model
import adagios.settings
pynag.Model.cfg_file = adagios.settings.nagios_config


class TestObjectBrowser(unittest.TestCase):

    def testNagiosConfigFile(self):
        result = pynag.Model.ObjectDefinition.objects.all
        config = pynag.Model.config.cfg_file
        self.assertGreaterEqual(
            len(result), 0, msg=_("Parsed nagios.cfg, but found no objects, are you sure this is the right config file (%(config)s) ? ") % {'config': config})

    def testIndexPage(self):
        c = Client()
        response = c.get('/objectbrowser/')
        self.assertEqual(response.status_code, 200)

    def testPageLoad(self):
        """ Smoke test a bunch of views """

        # TODO: Better tests, at least squeeze out a 200OK for these views
        self.loadPage('/objectbrowser/')
        self.loadPage('/objectbrowser/copy', 404)
        self.loadPage('/objectbrowser/search')
        self.loadPage('/objectbrowser/delete', 404)
        self.loadPage('/objectbrowser/bulk_edit')
        self.loadPage('/objectbrowser/bulk_delete')
        self.loadPage('/objectbrowser/bulk_copy')

        self.loadPage('/objectbrowser/edit_all', 404)
        self.loadPage('/objectbrowser/copy_and_edit', 301)

        self.loadPage('/objectbrowser/confighealth')
        self.loadPage('/objectbrowser/plugins')
        self.loadPage('/objectbrowser/nagios.cfg')
        self.loadPage('/objectbrowser/geek_edit', 404)
        self.loadPage('/objectbrowser/advanced_edit', 404)

        #self.loadPage('/objectbrowser/add_to_group')
        self.loadPage('/objectbrowser/add/host', 200)
        self.loadPage('/objectbrowser/add/hostgroup', 200)
        self.loadPage('/objectbrowser/add/service', 200)
        self.loadPage('/objectbrowser/add/servicegroup', 200)
        self.loadPage('/objectbrowser/add/contact', 200)
        self.loadPage('/objectbrowser/add/contactgroup', 200)
        self.loadPage('/objectbrowser/add/timeperiod', 200)
        self.loadPage('/objectbrowser/add/command', 200)
        self.loadPage('/objectbrowser/add/template', 200)

    def loadPage(self, url, expected_code=200):
        """ Load one specific page, and assert if return code is not 200 """
        try:
            c = Client()
            response = c.get(url)
            self.assertEqual(response.status_code, expected_code, _("Expected status code 200 for page %(url)s") % {'url': url})
        except Exception, e:
            self.assertEqual(True, _("Unhandled exception while loading %(url)s: %(error)s") % {'url': url, 'error': e})

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *


urlpatterns = patterns('adagios',

    url(r'^/$', 'objectbrowser.views.list_object_types', name="objectbrowser"),

    url(r'^/edit_all/(?P<object_type>.+)/(?P<attribute_name>.+)/?$', 'objectbrowser.views.edit_all'),
    url(r'^/search/?$', 'objectbrowser.views.search_objects', name="search"),


    url(r'^/edit/(?P<object_id>.+?)?$', 'objectbrowser.views.edit_object', name="edit_object"),

    url(r'^/edit/?$', 'objectbrowser.views.edit_object'),
    url(r'^/copy_and_edit/(?P<object_id>.+?)?$', 'objectbrowser.views.copy_and_edit_object'),

    url(r'^/copy/(?P<object_id>.+)$', 'objectbrowser.views.copy_object', name="copy_object"),
    url(r'^/delete/(?P<object_id>.+)$', 'objectbrowser.views.delete_object', name="delete_object"),
    url(r'^/delete/(?P<object_type>.+?)/(?P<shortname>.+)/?$', 'objectbrowser.views.delete_object_by_shortname', name="delete_by_shortname"),

    url(r'^/add/(?P<object_type>.+)$', 'objectbrowser.views.add_object', name="addobject"),
    url(r'^/bulk_edit/?$', 'objectbrowser.views.bulk_edit', name='bulk_edit'),
    url(r'^/bulk_delete/?$', 'objectbrowser.views.bulk_delete', name='bulk_delete'),
    url(r'^/bulk_copy/?$', 'objectbrowser.views.bulk_copy', name='bulk_copy'),
    url(r'^/add_to_group/(?P<group_type>.+)/(?P<group_name>.+)/?$', 'objectbrowser.views.add_to_group'),
    url(r'^/add_to_group/(?P<group_type>.+)/?$', 'objectbrowser.views.add_to_group'),
    url(r'^/add_to_group', 'objectbrowser.views.add_to_group'),
    url(r'^/confighealth/?$', 'objectbrowser.views.config_health'),
    url(r'^/plugins/?$', 'objectbrowser.views.show_plugins'),
    url(r'^/nagios.cfg/?$', 'objectbrowser.views.edit_nagios_cfg'),
    url(r'^/nagios.cfg/edit/?$', 'misc.views.edit_nagios_cfg'),
    url(r'^/geek_edit/id=(?P<object_id>.+)$', 'objectbrowser.views.geek_edit'),
    url(r'^/advanced_edit/id=(?P<object_id>.+)$', 'objectbrowser.views.advanced_edit'),

    # Here for backwards compatibility.
    url(r'^/edit/id=(?P<object_id>.+)$', 'objectbrowser.views.edit_object', ),
    url(r'^/id=(?P<object_id>.+)$', 'objectbrowser.views.edit_object', ),

    # These should be deprecated as of 2012-08-27
    url(r'^/copy_object/id=(?P<object_id>.+)$', 'objectbrowser.views.copy_object'),
    url(r'^/delete_object/id=(?P<object_id>.+)$', 'objectbrowser.views.delete_object'),

    )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.shortcuts import render_to_response, redirect, HttpResponse, Http404
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
import os
from os.path import dirname

from pynag.Model import ObjectDefinition, string_to_class
from pynag import Model
from pynag.Parsers import status
import pynag.Utils
from collections import defaultdict, namedtuple
import pynag.Model

from adagios import settings
from adagios.objectbrowser.forms import *
from adagios.views import adagios_decorator


@adagios_decorator
def home(request):
    return redirect('adagios')


@adagios_decorator
def list_object_types(request):
    """ Collects statistics about pynag objects and returns to template """
    c = {}
    return render_to_response('list_object_types.html', c, context_instance=RequestContext(request))


@adagios_decorator
def geek_edit(request, object_id):
    """ Function handles POST requests for the geek edit form """
    c = {}
    c.update(csrf(request))
    c['messages'] = m = []
    c['errors'] = []

    # Get our object
    try:
        o = ObjectDefinition.objects.get_by_id(id=object_id)
    except Exception, e:
        # This is an ugly hack. If unknown object ID was specified and it so happens to
        # Be the same as a brand new empty object definition we will assume that we are
        # to create a new object definition instead of throwing error because ours was
        # not found.
        for i in Model.string_to_class.values():
            if i().get_id() == object_id:
                o = i()
                break
        else:
            c['error_summary'] = _('Unable to find object')
            c['error'] = e
            return render_to_response('error.html', c, context_instance=RequestContext(request))
    c['my_object'] = o
    if request.method == 'POST':
        # Manual edit of the form
        form = GeekEditObjectForm(pynag_object=o, data=request.POST)
        if form.is_valid():
            try:
                form.save()
                m.append("Object Saved manually to '%s'" % o['filename'])
            except Exception, e:
                c['errors'].append(e)
                return render_to_response('edit_object.html', c, context_instance=RequestContext(request))
        else:
            c['errors'].append(_("Problem with saving object"))
            return render_to_response('edit_object.html', c, context_instance=RequestContext(request))
    else:
        form = GeekEditObjectForm(
            initial={'definition': o['meta']['raw_definition'], })

    c['geek_edit'] = form
    # Lets return the user to the general edit_object form
    return HttpResponseRedirect(reverse('edit_object', kwargs={'object_id': o.get_id()}))


@adagios_decorator
def advanced_edit(request, object_id):
    """ Handles POST only requests for the "advanced" object edit form. """
    c = {}
    c.update(csrf(request))
    c['messages'] = m = []
    c['errors'] = []
    # Get our object
    try:
        o = ObjectDefinition.objects.get_by_id(id=object_id)
        c['my_object'] = o
    except Exception, e:
        # This is an ugly hack. If unknown object ID was specified and it so happens to
        # Be the same as a brand new empty object definition we will assume that we are
        # to create a new object definition instead of throwing error because ours was
        # not found.
        for i in Model.string_to_class.values():
            if i().get_id() == object_id:
                o = i()
                break
        else:
            c['error_summary'] = _('Unable to get object')
            c['error'] = e
            return render_to_response('error.html', c, context_instance=RequestContext(request))

    if request.method == 'POST':
        # User is posting data into our form
        c['advanced_form'] = AdvancedEditForm(
            pynag_object=o, initial=o._original_attributes, data=request.POST)
        if c['advanced_form'].is_valid():
            try:
                c['advanced_form'].save()
                m.append(_("Object Saved to %(filename)s") % o)
            except Exception, e:
                c['errors'].append(e)
                return render_to_response('edit_object.html', c, context_instance=RequestContext(request))
    else:
            c['errors'].append(_("Problem reading form input"))
            return render_to_response('edit_object.html', c, context_instance=RequestContext(request))

    return HttpResponseRedirect(reverse('edit_object', args=[o.get_id()]))


@adagios_decorator
def edit_object(request, object_id=None):
    """ Brings up an edit dialog for one specific object.

        If an object_id is specified, bring us to that exact object.

        Otherwise we expect some search arguments to have been provided via querystring
    """
    c = {}
    c.update(csrf(request))
    c['messages'] = []
    c['errors'] = []
    my_object = None  # This is where we store our item that we are editing

    # If object_id was not provided, lets see if anything was given to us in a querystring
    if not object_id:
        objects = pynag.Model.ObjectDefinition.objects.filter(**request.GET)
        if len(objects) == 1:
            my_object = objects[0]
        else:
            return search_objects(request)
    else:
        try:
            my_object = pynag.Model.ObjectDefinition.objects.get_by_id(object_id)
        except KeyError:
            c['error_summary'] = _('Could not find any object with id="%(object_id)s" :/') % {'object_id': object_id}
            c['error_type'] = _("object not found")
            return render_to_response('error.html', c, context_instance=RequestContext(request))

    if request.method == 'POST':
        # User is posting data into our form
        c['form'] = PynagForm(
            pynag_object=my_object,
            initial=my_object._original_attributes,
            data=request.POST
        )
        if c['form'].is_valid():
            try:
                c['form'].save()
                c['messages'].append(_("Object Saved to %(filename)s") % my_object)
                return HttpResponseRedirect(reverse('edit_object', kwargs={'object_id': my_object.get_id()}))
            except Exception, e:
                c['errors'].append(e)
        else:
            c['errors'].append(_("Could not validate form input"))
    if 'form' not in c:
        c['form'] = PynagForm(pynag_object=my_object, initial=my_object._original_attributes)
    c['my_object'] = my_object
    c['geek_edit'] = GeekEditObjectForm(
        initial={'definition': my_object['meta']['raw_definition'], })
    c['advanced_form'] = AdvancedEditForm(
        pynag_object=my_object, initial=my_object._original_attributes)

    try:
        c['effective_hosts'] = my_object.get_effective_hosts()
    except KeyError, e:
        c['errors'].append(_("Could not find host: %(error)s") % {'error': str(e)})
    except AttributeError:
        pass

    try:
        c['effective_parents'] = my_object.get_effective_parents(cache_only=True)
    except KeyError, e:
        c['errors'].append(_("Could not find parent: %(error)s") % {'error': str(e)})

    # Every object type has some special treatment, so lets resort
    # to appropriate helper function
    if False:
        pass
    elif my_object['object_type'] == 'servicegroup':
        return _edit_servicegroup(request, c)
    elif my_object['object_type'] == 'hostdependency':
        return _edit_hostdependency(request, c)
    elif my_object['object_type'] == 'service':
        return _edit_service(request, c)
    elif my_object['object_type'] == 'contactgroup':
        return _edit_contactgroup(request, c)
    elif my_object['object_type'] == 'hostgroup':
        return _edit_hostgroup(request, c)
    elif my_object['object_type'] == 'host':
        return _edit_host(request, c)
    elif my_object['object_type'] == 'contact':
        return _edit_contact(request, c)
    elif my_object['object_type'] == 'command':
        return _edit_command(request, c)
    elif my_object['object_type'] == 'servicedependency':
        return _edit_servicedependency(request, c)
    elif my_object['object_type'] == 'timeperiod':
        return _edit_timeperiod(request, c)
    else:
        return render_to_response('edit_object.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_contact(request, c):
    """ This is a helper function to edit_object """
    try:
        c['effective_contactgroups'] = c[
            'my_object'].get_effective_contactgroups()
    except KeyError, e:
        c['errors'].append(_("Could not find contact: %(error)s") % {'error': str(e)})

    return render_to_response('edit_contact.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_service(request, c):
    """ This is a helper function to edit_object """
    service = c['my_object']
    try:
        c['command_line'] = service.get_effective_command_line()
    except KeyError:
        c['command_line'] = None
    try:
        c['object_macros'] = service.get_all_macros()
    except KeyError:
        c['object_macros'] = None
    # Get the current status from Nagios
    try:
        s = status()
        s.parse()
        c['status'] = s.get_servicestatus(
            service['host_name'], service['service_description'])
        current_state = c['status']['current_state']
        if current_state == "0":
            c['status']['text'] = 'OK'
            c['status']['css_label'] = 'label-success'
        elif current_state == "1":
            c['status']['text'] = 'Warning'
            c['status']['css_label'] = 'label-warning'
        elif current_state == "2":
            c['status']['text'] = 'Critical'
            c['status']['css_label'] = 'label-important'
        else:
            c['status']['text'] = 'Unknown'
            c['status']['css_label'] = 'label-inverse'
    except Exception:
        pass

    try:
        c['effective_servicegroups'] = service.get_effective_servicegroups()
    except KeyError, e:
        c['errors'].append(_("Could not find servicegroup: %(error)s") % {'error': str(e)})

    try:
        c['effective_contacts'] = service.get_effective_contacts()
    except KeyError, e:
        c['errors'].append(_("Could not find contact: %(error)s") % {'error': str(e)})

    try:
        c['effective_contactgroups'] = service.get_effective_contact_groups()
    except KeyError, e:
        c['errors'].append(_("Could not find contact_group: %(error)s") % {'error': str(e)})

    try:
        c['effective_hostgroups'] = service.get_effective_hostgroups()
    except KeyError, e:
        c['errors'].append(_("Could not find hostgroup: %(error)s") % {'error': str(e)})

    try:
        c['effective_command'] = service.get_effective_check_command()
    except KeyError, e:
        if service.check_command is not None:
            c['errors'].append(_("Could not find check_command: %(error)s") % {'error': str(e)})
        elif service.register != '0':
            c['errors'].append(_("You need to define a check command"))

    # For the check_command editor, we inject current check_command and a list
    # of all check_commands
    c['check_command'] = (service.check_command or '').split("!")[0]
    c['command_names'] = map(
        lambda x: x.get("command_name", ''), Model.Command.objects.all)
    if c['check_command'] in (None, '', 'None'):
        c['check_command'] = ''

    if service.hostgroup_name and service.hostgroup_name != 'null':
        c['errors'].append(_("This Service is applied to every host in hostgroup %(hostgroup_name)s") % {'hostgroup_name': service.hostgroup_name})
    host_name = service.host_name or ''
    if ',' in host_name:
        c['errors'].append(_("This Service is applied to multiple hosts"))
    return render_to_response('edit_service.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_contactgroup(request, c):
    """ This is a helper function to edit_object """
    try:
        c['effective_contactgroups'] = c[
            'my_object'].get_effective_contactgroups()
    except KeyError, e:
        c['errors'].append(_("Could not find contact_group: %(error)s") % {'error': str(e)})

    try:
        c['effective_contacts'] = c['my_object'].get_effective_contacts()
    except KeyError, e:
        c['errors'].append("Could not find contact: %s" % str(e))

    try:
        c['effective_memberof'] = Model.Contactgroup.objects.filter(
            contactgroup_members__has_field=c['my_object'].contactgroup_name)
    except Exception, e:
        c['errors'].append(e)
    return render_to_response('edit_contactgroup.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_hostgroup(request, c):
    """ This is a helper function to edit_object """
    hostgroup = c['my_object']
    try:
        c['effective_services'] = sorted(
            hostgroup.get_effective_services(), key=lambda x: x.get_description())
    except KeyError, e:
        c['errors'].append(_("Could not find service: %(error)s") % {'error': str(e)})
    try:
        c['effective_memberof'] = Model.Hostgroup.objects.filter(
            hostgroup_members__has_field=c['my_object'].hostgroup_name)
    except Exception, e:
        c['errors'].append(e)
    return render_to_response('edit_hostgroup.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_servicegroup(request, c):
    """ This is a helper function to edit_object """
    try:
        c['effective_memberof'] = Model.Servicegroup.objects.filter(
            servicegroup_members__has_field=c['my_object'].servicegroup_name)
    except Exception, e:
        c['errors'].append(e)
    return render_to_response('edit_servicegroup.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_command(request, c):
    """ This is a helper function to edit_object """
    return render_to_response('edit_command.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_hostdependency(request, c):
    """ This is a helper function to edit_object """
    return render_to_response('edit_hostdepedency.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_servicedependency(request, c):
    """ This is a helper function to edit_object """
    return render_to_response('_edit_servicedependency.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_timeperiod(request, c):
    """ This is a helper function to edit_object """
    return render_to_response('edit_timeperiod.html', c, context_instance=RequestContext(request))


@pynag.Utils.cache_only
def _edit_host(request, c):
    """ This is a helper function to edit_object """
    host = c['my_object']
    try:
        c['command_line'] = host.get_effective_command_line()
    except KeyError:
        c['command_line'] = None
    try:
        c['object_macros'] = host.get_all_macros()
    except KeyError:
        c['object_macros'] = None

    if not 'errors' in c:
        c['errors'] = []

    try:
        c['effective_services'] = sorted(
            host.get_effective_services(), key=lambda x: x.get_description())
    except KeyError, e:
        c['errors'].append(_("Could not find service: %(error)s") % {'error': str(e)})

    try:
        c['effective_hostgroups'] = host.get_effective_hostgroups()
    except KeyError, e:
        c['errors'].append(_("Could not find hostgroup: %(error)s") % {'error': str(e)})

    try:
        c['effective_contacts'] = host.get_effective_contacts()
    except KeyError, e:
        c['errors'].append(_("Could not find contact: %(error)s") % {'error': str(e)})

    try:
        c['effective_contactgroups'] = host.get_effective_contact_groups()
    except KeyError, e:
        c['errors'].append(_("Could not find contact_group: %(error)s") % {'error': str(e)})

    try:
        c['effective_command'] = host.get_effective_check_command()
    except KeyError, e:
        if host.check_command is not None:
            c['errors'].append(_("Could not find check_command: %(error)s") % {'error': str(e)})
        elif host.register != '0':
            c['errors'].append(_("You need to define a check command"))
    try:
        s = status()
        s.parse()
        c['status'] = s.get_hoststatus(host['host_name'])
        current_state = c['status']['current_state']
        if int(current_state) == 0:
            c['status']['text'] = 'UP'
            c['status']['css_label'] = 'label-success'
        else:
            c['status']['text'] = 'DOWN'
            c['status']['css_label'] = 'label-important'
    except Exception:
        pass

    return render_to_response('edit_host.html', c, context_instance=RequestContext(request))


@adagios_decorator
def config_health(request):
    """ Display possible errors in your nagios config
    """
    c = dict()
    c['messages'] = []
    c['object_health'] = s = {}
    c['booleans'] = {}
    services_no_description = Model.Service.objects.filter(
        register="1", service_description=None)
    hosts_without_contacts = []
    hosts_without_services = []
    objects_with_invalid_parents = []
    services_without_contacts = []
    services_using_hostgroups = []
    services_without_icon_image = []
    c['booleans'][
        _('Nagios Service has been reloaded since last configuration change')] = not Model.config.needs_reload()
    c['booleans'][
        _('Adagios configuration cache is up-to-date')] = not Model.config.needs_reparse()
    for i in Model.config.errors:
        if i.item:
            Class = Model.string_to_class[i.item['meta']['object_type']]
            i.model = Class(item=i.item)
    c['parser_errors'] = Model.config.errors
    try:
        import okconfig
        c['booleans'][
            _('OKConfig is installed and working')] = okconfig.is_valid()
    except Exception:
        c['booleans'][_('OKConfig is installed and working')] = False
    s['Parser errors'] = Model.config.errors
    s['Services with no "service_description"'] = services_no_description
    s['Hosts without any contacts'] = hosts_without_contacts
    s['Services without any contacts'] = services_without_contacts
    s['Objects with invalid "use" attribute'] = objects_with_invalid_parents
    s['Services applied to hostgroups'] = services_using_hostgroups
    s['Services without a logo'] = services_without_icon_image
    s['Hosts without Service Checks'] = hosts_without_services
    if request.GET.has_key('show') and s.has_key(request.GET['show']):
        objects = s[request.GET['show']]
        return search_objects(request, objects=objects)
    else:
        return render_to_response('suggestions.html', c, context_instance=RequestContext(request))


@adagios_decorator
def show_plugins(request):
    """ Finds all command_line arguments, and shows missing plugins """
    c = {}
    missing_plugins = []
    existing_plugins = []
    finished = []
    services = Model.Service.objects.all
    common_interpreters = ['perl', 'python', 'sh', 'bash']
    for s in services:
        if not 'check_command' in s._defined_attributes:
            continue
        check_command = s.check_command.split('!')[0]
        if check_command in finished:
            continue
        finished.append(check_command)
        try:
            command_line = s.get_effective_command_line()
        except KeyError:
            continue
        if command_line is None:
            continue
        command_line = command_line.split()
        command_name = command_line.pop(0)
        if command_name in common_interpreters:
            command_name = command_line.pop(0)
        if os.path.exists(command_name):
            existing_plugins.append((check_command, command_name))
        else:
            missing_plugins.append((check_command, command_name))
    c['missing_plugins'] = missing_plugins
    c['existing_plugins'] = existing_plugins
    return render_to_response('show_plugins.html', c, context_instance=RequestContext(request))


@adagios_decorator
def edit_nagios_cfg(request):
    """ This views is made to make modifications to nagios.cfg
    """
    from pynag.Model.all_attributes import main_config
    c = {'filename': Model.config.cfg_file}
    c['content'] = []

    for conf in sorted(main_config):
        values = []
        Model.config.parse_maincfg()
        for k, v in Model.config.maincfg_values:
            if conf == k:
                values.append(v)
        c['content'].append({
            'doc': main_config[conf]['doc'],
            'title': main_config[conf]['title'],
            'examples': main_config[conf]['examples'],
            'format': main_config[conf]['format'],
            'options': main_config[conf]['options'],
            'key': conf,
            'values': values
        })

    for key, v in Model.config.maincfg_values:
        if key not in main_config:
            c['content'].append({
                'title': _('No documentation found'),
                'key': key,
                'values': [v],
                'doc': _('This seems to be an undefined option and no documentation was found for it. Perhaps it is'
                       'mispelled.')
            })
    c['content'] = sorted(c['content'], key=lambda cfgitem: cfgitem['key'])
    return render_to_response('edit_configfile.html', c, context_instance=RequestContext(request))


@adagios_decorator
def bulk_edit(request):
    """ Edit multiple objects with one post """
    c = {}
    c.update(csrf(request))
    c['messages'] = []
    c['errors'] = []
    c['objects'] = objects = []

    # Newer, alternative way to input items from the post data is in the form of
    # object_type=shortname
    # i.e. timeperiod=24x7, timeperiod=workhours
    for i in _querydict_to_objects(request):
        objects.append(i)

    if request.method == 'GET':
        if len(objects) == 1:
            return HttpResponseRedirect(reverse('edit_object', kwargs={'object_id': objects[0].get_id()}), )
        c['form'] = BulkEditForm(objects=objects)
    if request.method == "POST":
        c['form'] = BulkEditForm(objects=objects, data=request.POST)
        c['objects'] = c['form'].all_objects
        if c['form'].is_valid():
            try:
                c['form'].save()
                for i in c['form'].changed_objects:
                    c['messages'].append(
                        _("saved changes to %(object_type)s '%(description)s'") % {'object_type': i.object_type,
                                                                                   'description': i.get_description(),
                                                                                    })
                c['success'] = "success"
            except IOError, e:
                c['errors'].append(e)

    return render_to_response('bulk_edit.html', c, context_instance=RequestContext(request))

@adagios_decorator
def bulk_delete(request):
    """ Edit delete multiple objects with one post """
    c = {}
    c.update(csrf(request))
    c['messages'] = []
    c['errors'] = []
    c['objects'] = objects = []
    c['form'] = BulkDeleteForm(objects=objects)

    # Newer, alternative way to input items from the post data is in the form of
    # object_type=shortname
    # i.e. timeperiod=24x7, timeperiod=workhours
    for i in _querystring_to_objects(request.GET or request.POST):
        try:
            obj = pynag.Model.string_to_class[i.object_type].objects.get_by_shortname(i.description)
            if obj not in objects:
                objects.append(obj)
        except KeyError:
            c['errors'].append(_("Could not find %(object_type)s '%(description)s' "
                                 "Maybe it has already been deleted.") % {'object_type': i.object_type, 
                                                                          'description': i.description})
    if request.method == "GET" and len(objects) == 1:
        return HttpResponseRedirect(reverse('delete_object', kwargs={'object_id': objects[0].get_id()}), )

    if request.method == "POST":
        # Post items starting with "hidden_" will be displayed on the resulting web page
        # Post items starting with "change_" will be modified
        for i in request.POST.keys():
            if i.startswith('change_'):
                my_id = i[len('change_'):]
                my_obj = ObjectDefinition.objects.get_by_id(my_id)
                if my_obj not in objects:
                    objects.append(my_obj)

        c['form'] = BulkDeleteForm(objects=objects, data=request.POST)
        if c['form'].is_valid():
            try:
                c['form'].delete()
                c['success'] = "Success"
                for i in c['form'].changed_objects:
                    c['messages'].append(
                        "Deleted %s %s" % (i.object_type, i.get_description()))
            except IOError, e:
                c['errors'].append(e)

    return render_to_response('bulk_delete.html', c, context_instance=RequestContext(request))

@adagios_decorator
def bulk_copy(request):
    """ Copy multiple objects with one post """
    c = {}
    c.update(csrf(request))
    c['messages'] = []
    c['errors'] = []
    c['objects'] = objects = []
    c['form'] = BulkCopyForm(objects=objects)

    # Newer, alternative way to input items from the post data is in the form of
    # object_type=shortname
    # i.e. timeperiod=24x7, timeperiod=workhours
    for i in _querystring_to_objects(request.GET or request.POST):
        try:
            obj = pynag.Model.string_to_class[i.object_type].objects.get_by_shortname(i.description)
            if obj not in objects:
                objects.append(obj)
        except KeyError:
            c['errors'].append(_("Could not find %(object_type)s '%(description)s'") % {'object_type': i.object_type,
                                                                                        'description': i.description,
                                                                                       })
    if request.method == "GET" and len(objects) == 1:
        return HttpResponseRedirect(reverse('copy_object', kwargs={'object_id': objects[0].get_id()}), )
    elif request.method == "POST":
        # Post items starting with "hidden_" will be displayed on the resulting web page
        # Post items starting with "change_" will be modified
        for i in request.POST.keys():
            if i.startswith('change_'):
                my_id = i[len('change_'):]
                my_obj = ObjectDefinition.objects.get_by_id(my_id)
                if my_obj not in objects:
                    objects.append(my_obj)

        c['form'] = BulkCopyForm(objects=objects, data=request.POST)
        if c['form'].is_valid():
            try:
                c['form'].save()
                c['success'] = "Success"
                for i in c['form'].changed_objects:
                    c['messages'].append(
                        _("Successfully copied %(object_type)s %(description)s") % {'object_type': i.object_type,
                                                                                    'description': i.get_description()})
            except IOError, e:
                c['errors'].append(e)

    return render_to_response('bulk_copy.html', c, context_instance=RequestContext(request))

@adagios_decorator
def delete_object_by_shortname(request, object_type, shortname):
    """ Same as delete_object() but uses object type and shortname instead of object_id
    """
    obj_type = Model.string_to_class[object_type]
    my_obj = obj_type.objects.get_by_shortname(shortname)
    return delete_object(request, object_id=my_obj.get_id())

@adagios_decorator
def delete_object(request, object_id):
    """ View to Delete a single object definition """
    c = {}
    c.update(csrf(request))
    c['messages'] = []
    c['errors'] = []
    c['object'] = my_obj = Model.ObjectDefinition.objects.get_by_id(object_id)
    c['form'] = DeleteObjectForm(pynag_object=my_obj, initial=request.GET)
    if request.method == 'POST':
        try:
            c['form'] = f = DeleteObjectForm(
                pynag_object=my_obj, data=request.POST)
            if f.is_valid():
                f.delete()
            return HttpResponseRedirect(reverse('objectbrowser') + "#" + my_obj.object_type)
        except Exception, e:
            c['errors'].append(e)
    return render_to_response('delete_object.html', c, context_instance=RequestContext(request))


@adagios_decorator
def copy_object(request, object_id):
    """ View to Copy a single object definition """
    c = {}
    c.update(csrf(request))
    c['messages'] = []
    c['errors'] = []
    c['object'] = my_obj = Model.ObjectDefinition.objects.get_by_id(object_id)

    if request.method == 'GET':
        c['form'] = CopyObjectForm(pynag_object=my_obj, initial=request.GET)
    elif request.method == 'POST':
        c['form'] = f = CopyObjectForm(pynag_object=my_obj, data=request.POST)
        if f.is_valid():
            try:
                f.save()
                c['copied_objects'] = f.copied_objects
                c['success'] = 'success'
            except IndexError, e:
                c['errors'].append(e)
    return render_to_response('copy_object.html', c, context_instance=RequestContext(request))


@adagios_decorator
def add_object(request, object_type):
    """ Friendly wizard on adding a new object of any particular type
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['object_type'] = object_type

    if request.method == 'GET' and object_type == 'template':
        c['form'] = AddTemplateForm(initial=request.GET)
    elif request.method == 'GET':
        c['form'] = AddObjectForm(object_type, initial=request.GET)
    elif request.method == 'POST' and object_type == 'template':
        c['form'] = AddTemplateForm(data=request.POST)
    elif request.method == 'POST':
        c['form'] = AddObjectForm(object_type, data=request.POST)
    else:
        c['errors'].append(_("Something went wrong while calling this form"))

    # This is what happens in post regardless of which type of form it is
    if request.method == 'POST' and 'form' in c:
        # If form is valid, save object and take user to edit_object form.
        if c['form'].is_valid():
            c['form'].save()
            object_id = c['form'].pynag_object.get_id()
            return HttpResponseRedirect(reverse('edit_object', kwargs={'object_id': object_id}), )
        else:
            c['errors'].append(_('Could not validate form input'))

    return render_to_response('add_object.html', c, context_instance=RequestContext(request))


def _querystring_to_objects(dictionary):
    """ Finds all nagios objects in a querystring and returns a list of objects

    >>> dictionary = {'host':('localhost1', 'localhost2'),}
    >>> print _querystring_to_objects
    {'host':('localhost1','localhost2')}
    """
    result = []
    Object = namedtuple('Object', 'object_type description')
    for object_type in string_to_class.keys():
        objects = dictionary.getlist(object_type)
        for i in objects:
            obj = (Object(object_type, i))
            result.append(obj)
    return result


def _querydict_to_objects(request, raise_on_not_found=False):
    """ Finds all object specifications in a querydict and returns a list of pynag objects

    Typically this is used to name specific objects from the querystring.

    Valid input in the request is either id=object_id or object_type=short_name

    Arguments:
        request  - A django request object. Usually the data is in a querystring or POST data
                 - Example: host=localhost,service=localhost/Ping
        raise_on_not_found - Raise ValueError if some object is not found
    Returns:
        List of pynag objects
    """
    result = []
    mydict = request.GET or request.POST

    # Find everything in the querystring in the form of id=[object_ids]
    for object_id in mydict.getlist('id'):
        try:
            my_object = ObjectDefinition.objects.get_by_id(object_id)
            result.append(my_object)
        except Exception, e:
            if raise_on_not_found is True:
                raise e

    # Find everything in querystring in the form of object_type=[shortnames]
    for object_type,Class in string_to_class.items():
        objects = mydict.getlist(object_type)
        for shortname in objects:
            try:
                my_object = Class.objects.get_by_shortname(shortname)
                result.append(my_object)
            except Exception, e:
                # If a service was not found, check if it was registered in
                # some unusual way
                if object_type == 'service' and '/' in shortname:
                    host_name,service_description = shortname.split('/', 1)
                    result.append(_find_service(host_name, service_description))
                if raise_on_not_found is True:
                    raise e
    return result


def _find_service(host_name, service_description):
    """ Returns pynag.Model.Service matching our search filter """
    result = pynag.Model.Service.objects.filter(host_name__has_field=host_name, service_description=service_description)

    if not result:
        host = pynag.Model.Host.objects.get_by_shortname(host_name, cache_only=True)
        for i in host.get_effective_services():
            if i.service_description == service_description:
                result = [i]
                break
    return result[0]


@adagios_decorator
def add_to_group(request, group_type=None, group_name=''):
    """ Add one or more objects into a group
    """

    c = {}
    messages = []
    errors = []
    if not group_type:
        raise Exception(_("Please include group type"))
    if request.method == 'GET':
        objects = _querystring_to_objects(request.GET)
    elif request.method == 'POST':
        objects = _querystring_to_objects(request.GET)
        for i in objects:
            try:
                obj = pynag.Model.string_to_class[i.object_type].objects.get_by_shortname(i.description)
                if group_type == 'contactgroup':
                    obj.add_to_contactgroup(group_name)
                elif group_type == 'hostgroup':
                    obj.add_to_hostgroup(group_name)
                elif group_type == 'servicegroup':
                    obj.add_to_servicegroup(group_name)
                return HttpResponse("Success")
            except Exception, e:
                errortype = e.__dict__.get('__name__') or str(type(e))
                error = str(e)
                return HttpResponse(_("Failed to add object: %(errortype)s %(error)s ") % {'errortype': errortype,
                                                                                           'error': error,
                                                                                           })

    return render_to_response('add_to_group.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def edit_all(request, object_type, attribute_name):
    """  Edit many objects at once, changing only a single attribute

    Example:
        Edit notes_url of all services
    """
    messages = []
    errors = []
    objects = Model.string_to_class.get(object_type).objects.all
    objects = map(lambda x: (x.get_shortname, x.get(attribute_name)), objects)
    return render_to_response('edit_all.html', locals(), context_instance=RequestContext(request))



@adagios_decorator
def search_objects(request, objects=None):
    """ Displays a list of pynag objects, search parameters can be entered via querystring

        Arguments:
            objects -- List of pynag objects to show. If it is not set,
                    -- We will use querystring instead as search arguments
        example:
         /adagios/objectbrowser/search?object_type=host&host_name__startswith=foo


    """
    messages = []
    errors = []
    if not objects:
        objects = pynag.Model.ObjectDefinition.objects.filter(**request.GET)

    # A special case, if no object was found, lets check if user was looking for a service
    # With its host_name / service_description pair, and the service is applied to hostgroup instead
    if not objects and request.GET.get('object_type') == 'service':
        host_name = request.GET.get('host_name')
        service_description = request.GET.get('service_description')
        shortname = request.GET.get('shortname')

        # If shortname was provided instead of host_name / service_description
        if not host_name and not service_description and shortname:
            host_name, service_description = shortname.split('/')

        # If at this point we have found some objects, then lets do a special workaround
        services = [_find_service(host_name, service_description)]
        errors.append(_('be careful'))

    return render_to_response('search_objects.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def copy_and_edit_object(request, object_id):
    """ Create a new object, and open up an edit dialog for it.

    If object_id is provided, that object will be copied into this one.
    """
    kwargs = {}
    for k, v in request.GET.items():
        if v in ('', None, 'None'):
            v = None
        kwargs[k] = v
    o = pynag.Model.ObjectDefinition.objects.get_by_id(object_id)
    o = o.copy(**kwargs)
    o = pynag.Model.ObjectDefinition.objects.filter(shortname=o.get_shortname(), object_type=o.object_type)[0]

    return HttpResponseRedirect(reverse('edit_object', kwargs={'object_id': o.get_id()}))



########NEW FILE########
__FILENAME__ = forms
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
import okconfig
from adagios.misc import helpers
import re
from django.core.exceptions import ValidationError
import socket
from pynag import Model
from adagios.forms import AdagiosForm
from django.utils.translation import ugettext as _


def get_all_hosts():
    return [('', _('Select a host'))] + map(lambda x: (x, x), helpers.get_host_names())


def get_all_templates():
    all_templates = okconfig.get_templates()
    service_templates = filter(lambda x: 'host' not in x, all_templates)
    return map(lambda x: (x, _("Standard %(service_template)s checks") % {"service_template": x}), service_templates)


def get_all_groups():
    return map(lambda x: (x, x), okconfig.get_groups())


def get_inactive_services():
    """ List of all unregistered services (templates) """
    inactive_services = [('', _('Select a service'))]
    inactive_services += map(lambda x: (x.name, x.name),
                             Model.Service.objects.filter(service_description__contains="", name__contains="", register="0"))
    inactive_services.sort()
    return inactive_services


class ScanNetworkForm(AdagiosForm):
    network_address = forms.CharField()

    def clean_network_address(self):
        addr = self.cleaned_data['network_address']
        if addr.find('/') > -1:
            addr, mask = addr.split('/', 1)
            if not mask.isdigit():
                raise ValidationError(_("not a valid netmask"))
            if not self.isValidIPAddress(addr):
                raise ValidationError(_("not a valid ip address"))
        else:
            if not self.isValidIPAddress(addr):
                raise ValidationError(_("not a valid ip address"))
        return self.cleaned_data['network_address']

    def isValidHostname(self, hostname):
        if len(hostname) > 255:
            return False
        if hostname[-1:] == ".":
            # strip exactly one dot from the right, if present
            hostname = hostname[:-1]
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        for x in hostname.split("."):
            if allowed.match(x) is False:
                return False
        return True

    def isValidIPAddress(self, ipaddress):
        try:
            socket.inet_aton(ipaddress)
        except Exception:
            return False
        return True


class AddGroupForm(AdagiosForm):
    group_name = forms.CharField(help_text=_("Example: databases"))
    alias = forms.CharField(help_text=_("Human friendly name for the group"))
    force = forms.BooleanField(
        required=False, help_text=_("Overwrite group if it already exists."))


class AddHostForm(AdagiosForm):
    host_name = forms.CharField(help_text=_("Name of the host to add"))
    address = forms.CharField(help_text=_("IP Address of this host"))
    group_name = forms.ChoiceField(
        initial="default", help_text=_("host/contact group to put this host in"))
    templates = forms.MultipleChoiceField(
        required=False, help_text=_("Add standard template of checks to this host"))
    force = forms.BooleanField(
        required=False, help_text=_("Overwrite host if it already exists."))

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.fields['group_name'].choices = choices = get_all_groups()
        self.fields['templates'].choices = get_all_templates()

    def clean(self):
        cleaned_data = super(AddHostForm, self).clean()
        force = self.cleaned_data.get('force')
        host_name = self.cleaned_data.get('host_name')
        templates = self.cleaned_data.get('templates')
        for i in templates:
            if i not in okconfig.get_templates().keys():
                self._errors['templates'] = self.error_class(
                    [_('template %s was not found') % i])
        if not force and host_name in okconfig.get_hosts():
            self._errors['host_name'] = self.error_class(
                [_('Host name already exists. Use force to overwrite')])
        return cleaned_data


class AddTemplateForm(AdagiosForm):
    # Attributes
    host_name = forms.ChoiceField(help_text=_("Add templates to this host"))
    templates = forms.MultipleChoiceField(
        required=False, help_text=_("Add standard template of checks to this host"))
    force = forms.BooleanField(
        required=False, help_text=_("Overwrites templates if they already exist"))

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.fields['templates'].choices = get_all_templates()
        self.fields['host_name'].choices = get_all_hosts()

    def clean(self):
        cleaned_data = super(AddTemplateForm, self).clean()
        force = self.cleaned_data.get('force')
        host_name = self.cleaned_data.get('host_name')
        templates = self.cleaned_data.get('templates')
        for i in templates:
            if i not in okconfig.get_templates().keys():
                self._errors['templates'] = self.error_class(
                    [_('template %s was not found') % i])
        if not force and host_name not in okconfig.get_hosts():
            self._errors['host_name'] = self.error_class(
                [_('Host name not found Use force to write template anyway')])
        return cleaned_data

    def save(self):
        host_name = self.cleaned_data['host_name']
        templates = self.cleaned_data['templates']
        force = self.cleaned_data['force']
        self.filelist = []
        for i in templates:
            self.filelist += okconfig.addtemplate(
                host_name=host_name, template_name=i, force=force)


class InstallAgentForm(AdagiosForm):
    remote_host = forms.CharField(help_text=_("Host or ip address"))
    install_method = forms.ChoiceField(
        initial='ssh', help_text=_("Make sure firewalls are not blocking ports 22(for ssh) or 445(for winexe)"),
        choices=[(_('auto detect'), _('auto detect')), ('ssh', 'ssh'), ('winexe', 'winexe')])
    username = forms.CharField(
        initial='root', help_text=_("Log into remote machine with as this user"))
    password = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text=_("Leave empty if using kerberos or ssh keys"))
    windows_domain = forms.CharField(
        required=False, help_text=_("If remote machine is running a windows domain"))


class ChooseHostForm(AdagiosForm):
    host_name = forms.ChoiceField(help_text=_("Select which host to edit"))

    def __init__(self, service=Model.Service(), *args, **kwargs):
        super(forms.Form, self).__init__(*args, **kwargs)
        self.fields['host_name'].choices = get_all_hosts()


class AddServiceToHostForm(AdagiosForm):
    host_name = forms.ChoiceField(
        help_text=_("Select host which you want to add service check to"))
    service = forms.ChoiceField(
        help_text=_("Select which service check you want to add to this host"))

    def __init__(self, service=Model.Service(), *args, **kwargs):
        super(forms.Form, self).__init__(*args, **kwargs)
        self.fields['host_name'].choices = get_all_hosts()
        self.fields['service'].choices = get_inactive_services()


class EditTemplateForm(AdagiosForm):

    def __init__(self, service=Model.Service(), *args, **kwargs):
        self.service = service
        super(forms.Form, self).__init__(*args, **kwargs)

        # Run through all the all attributes. Add
        # to form everything that starts with "_"
        self.description = service['service_description']
        fieldname = "%s::%s::%s" % (
            service['host_name'], service['service_description'], 'register')
        self.fields[fieldname] = forms.BooleanField(
            required=False, initial=service['register'] == "1", label='register')
        self.register = fieldname

        macros = []
        self.command_line = None
        try:
            self.command_line = service.get_effective_command_line()
            for macro, value in service.get_all_macros().items():
                if macro.startswith('$_SERVICE') or macro.startswith('S$ARG'):
                    macros.append(macro)
            for k in sorted(macros):
                fieldname = "%s::%s::%s" % (
                    service['host_name'], service['service_description'], k)
                label = k.replace('$_SERVICE', '')
                label = label.replace('_', ' ')
                label = label.replace('$', '')
                label = label.capitalize()
                self.fields[fieldname] = forms.CharField(
                    required=False, initial=service.get_macro(k), label=label)
        # KeyError can occur if service has an invalid check_command
        except KeyError:
            pass

    def save(self):
        for i in self.changed_data:
            # Changed data comes in the format host_name::service_description::$_SERVICE_PING
            # We need to change that to just __PING
            field_name = i.split('::')[2]
            field_name = field_name.replace('$_SERVICE', '_')
            field_name = field_name.replace('$', '')
            data = self.cleaned_data[i]
            if field_name == 'register':
                data = int(data)
            self.service[field_name] = data
        self.service.save()
        self.service.reload_object()
        # Lets also update commandline because form is being returned to the
        # user
        self.command_line = self.service.get_effective_command_line()

########NEW FILE########
__FILENAME__ = models
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.utils import unittest
from django.test.client import Client
from django.utils.translation import ugettext as _

import okconfig
import adagios.settings

okconfig.cfg_file = adagios.settings.nagios_config


class TestOkconfig(unittest.TestCase):

    def testOkconfigVerifies(self):
        result = okconfig.verify()
        for k, v in result.items():
            self.assertTrue(v, msg=_("Failed on test: %s") % k)

    def testIndexPage(self):
        c = Client()
        response = c.get('/okconfig/verify_okconfig')
        self.assertEqual(response.status_code, 200)

    def testPageLoad(self):
        """ Smoketest for the okconfig views """
        self.loadPage('/okconfig/addhost')
        self.loadPage('/okconfig/scan_network')
        self.loadPage('/okconfig/addgroup')
        self.loadPage('/okconfig/addtemplate')
        self.loadPage('/okconfig/addhost')
        self.loadPage('/okconfig/addservice')
        self.loadPage('/okconfig/install_agent')
        self.loadPage('/okconfig/edit')
        self.loadPage('/okconfig/edit/localhost')
        self.loadPage('/okconfig/verify_okconfig')
    def loadPage(self, url):
        """ Load one specific page, and assert if return code is not 200 """
        try:
            c = Client()
            response = c.get(url)
            self.assertEqual(response.status_code, 200, _("Expected status code 200 for page %s") % url)
        except Exception, e:
            self.assertEqual(True, _("Unhandled exception while loading %(url)s: %(e)s") % {'url': url, 'e': e})

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('adagios',

                       #(r'^/?$', 'okconfig_.views.index'),
                      (r'^/scan_network/?', 'okconfig_.views.scan_network'),
                      (r'^/addgroup/?', 'okconfig_.views.addgroup'),
                      (r'^/addtemplate/?', 'okconfig_.views.addtemplate'),
                      (r'^/addhost/?', 'okconfig_.views.addhost'),
                      (r'^/addservice/?', 'okconfig_.views.addservice'),
                      (r'^/install_agent/?', 'okconfig_.views.install_agent'),
                      (r'^/edit/?$', 'okconfig_.views.choose_host'),
                      (r'^/edit/(?P<host_name>.+)$', 'okconfig_.views.edit'),
                      (r'^/verify_okconfig/?',
                       'okconfig_.views.verify_okconfig'),
                       )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.shortcuts import render_to_response, redirect
from django.core import serializers
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.utils import simplejson
from django.core.context_processors import csrf
from django.template import RequestContext
from django.utils.translation import ugettext as _
from adagios.views import adagios_decorator

from django.core.urlresolvers import reverse

from adagios.okconfig_ import forms

import okconfig
import okconfig.network_scan
from pynag import Model


@adagios_decorator
def addcomplete(request, c=None):
    """ Landing page when a new okconfig group has been added
    """
    if not c:
        c = {}
    return render_to_response('addcomplete.html', c, context_instance=RequestContext(request))


@adagios_decorator
def addgroup(request):
    """ Add a new okconfig group

    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    # If there is a problem with the okconfig setup, lets display an error
    if not okconfig.is_valid():
        return verify_okconfig(request)

    if request.method == 'GET':
        f = forms.AddGroupForm(initial=request.GET)
    elif request.method == 'POST':
        f = forms.AddGroupForm(request.POST)
        if f.is_valid():
            group_name = f.cleaned_data['group_name']
            alias = f.cleaned_data['alias']
            force = f.cleaned_data['force']
            try:
                c['filelist'] = okconfig.addgroup(
                    group_name=group_name, alias=alias, force=force)
                c['group_name'] = group_name
                return addcomplete(request, c)
            except Exception, e:
                c['errors'].append(_("error adding group: %s") % e)
        else:
            c['errors'].append(_('Could not validate input'))
    else:
        raise Exception("Sorry i only support GET or POST")
    c['form'] = f
    return render_to_response('addgroup.html', c, context_instance=RequestContext(request))


@adagios_decorator
def addhost(request):
    """ Add a new host from an okconfig template
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    # If there is a problem with the okconfig setup, lets display an error
    if not okconfig.is_valid():
        return verify_okconfig(request)

    if request.method == 'GET':
        f = forms.AddHostForm(initial=request.GET)
    elif request.method == 'POST':
        f = forms.AddHostForm(request.POST)
        if f.is_valid():
            host_name = f.cleaned_data['host_name']
            group_name = f.cleaned_data['group_name']
            address = f.cleaned_data['address']
            templates = f.cleaned_data['templates']
            #description = f.cleaned_data['description']
            force = f.cleaned_data['force']
            try:
                c['filelist'] = okconfig.addhost(host_name=host_name, group_name=group_name, address=address,
                                                 force=force, templates=templates)
                c['host_name'] = host_name
                return addcomplete(request, c)
            except Exception, e:
                c['errors'].append(_("error adding host: %s") % e)
        else:
            c['errors'].append(_('Could not validate input'))
    else:
        raise Exception("Sorry i only support GET or POST")
    c['form'] = f
    return render_to_response('addhost.html', c, context_instance=RequestContext(request))


@adagios_decorator
def addtemplate(request, host_name=None):
    """ Add a new okconfig template to a host

    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    # If there is a problem with the okconfig setup, lets display an error
    if not okconfig.is_valid():
        return verify_okconfig(request)

    c['form'] = forms.AddTemplateForm(initial=request.GET)
    if request.method == 'POST':
        c['form'] = f = forms.AddTemplateForm(request.POST)
        if f.is_valid():
            try:
                f.save()
                c['host_name'] = host_name = f.cleaned_data['host_name']
                c['filelist'] = f.filelist
                c['messages'].append(
                    _("Template was successfully added to host."))
                return HttpResponseRedirect(reverse('adagios.okconfig_.views.edit', args=[host_name]))
            except Exception, e:
                c['errors'].append(e)
        else:
            c['errors'].append(_("Could not validate form"))
    return render_to_response('addtemplate.html', c, context_instance=RequestContext(request))


@adagios_decorator
def addservice(request):
    """ Create a new service derived from an okconfig template
    """
    c = {}
    c.update(csrf(request))
    c['form'] = forms.AddServiceToHostForm()
    c['messages'] = []
    c['errors'] = []
    c['filename'] = Model.config.cfg_file
    if request.method == 'POST':
        c['form'] = form = forms.AddServiceToHostForm(data=request.POST)
        if form.is_valid():
            host_name = form.cleaned_data['host_name']
            host = Model.Host.objects.get_by_shortname(host_name)
            service = form.cleaned_data['service']
            new_service = Model.Service()
            new_service.host_name = host_name
            new_service.use = service
            new_service.set_filename(host.get_filename())
            # new_service.reload_object()
            c['my_object'] = new_service

            # Add custom macros if any were specified
            for k, v in form.data.items():
                if k.startswith("_") or k.startswith('service_description'):
                    new_service[k] = v
            try:
                new_service.save()
                return HttpResponseRedirect(reverse('edit_object', kwargs={'object_id': new_service.get_id()}))
            except IOError, e:
                c['errors'].append(e)
        else:
            c['errors'].append(_("Could not validate form"))
    return render_to_response('addservice.html', c, context_instance=RequestContext(request))


@adagios_decorator
def verify_okconfig(request):
    """ Checks if okconfig is properly set up. """
    c = {}
    c['errors'] = []
    c['okconfig_checks'] = okconfig.verify()
    for i in c['okconfig_checks'].values():
        if i == False:
            c['errors'].append(
                _('There seems to be a problem with your okconfig installation'))
            break
    return render_to_response('verify_okconfig.html', c, context_instance=RequestContext(request))


@adagios_decorator
def install_agent(request):
    """ Installs an okagent on a remote host """
    c = {}
    c['errors'] = []
    c['messages'] = []
    c['form'] = forms.InstallAgentForm(initial=request.GET)
    c['nsclient_installfiles'] = okconfig.config.nsclient_installfiles
    if request.method == 'POST':
        c['form'] = f = forms.InstallAgentForm(request.POST)
        if f.is_valid():
            f.clean()
            host = f.cleaned_data['remote_host']
            user = f.cleaned_data['username']
            passw = f.cleaned_data['password']
            method = f.cleaned_data['install_method']
            domain = f.cleaned_data['windows_domain']
            try:
                status, out, err = okconfig.install_okagent(
                    remote_host=host, domain=domain, username=user, password=passw, install_method=method)
                c['exit_status'] = status
                c['stderr'] = err
                # Do a little cleanup in winexe stdout, it is irrelevant
                out = out.split('\n')
                c['stdout'] = []
                for i in out:
                    if i.startswith(_('Unknown parameter encountered:')):
                        continue
                    elif i.startswith(_('Ignoring unknown parameter')):
                        continue
                    elif 'NT_STATUS_LOGON_FAILURE' in i:
                        c['hint'] = _("NT_STATUS_LOGON_FAILURE usually means there is a problem with username or password. Are you using correct domain ?")
                    elif 'NT_STATUS_DUPLICATE_NAME' in i:
                        c['hint'] = _("The security settings on the remote windows host might forbid logins if the host name specified does not match the computername on the server. Try again with either correct hostname or the ip address of the server.")
                    elif 'NT_STATUS_ACCESS_DENIED' in i:
                        c['hint'] = _("Please make sure that %(admin)s is a local administrator on host %(host)s") % {
                            'admin': user, 'host': host}
                    elif i.startswith('Error: Directory') and i.endswith('not found'):
                        c['hint'] = _("No nsclient copy found ")
                    c['stdout'].append(i)
                c['stdout'] = '\n'.join(c['stdout'])
            except Exception, e:
                c['errors'].append(e)
        else:
            c['errors'].append(_('invalid input'))

    return render_to_response('install_agent.html', c, context_instance=RequestContext(request))


@adagios_decorator
def edit(request, host_name):
    """ Edit all the Service "__MACROS" for a given host """

    c = {}
    c['errors'] = []
    c['messages'] = []
    c.update(csrf(request))
    c['hostname'] = host_name
    c['host_name'] = host_name
    c['forms'] = myforms = []

    try:
        c['myhost'] = Model.Host.objects.get_by_shortname(host_name)
    except KeyError, e:
        c['errors'].append(_("Host %s not found") % e)
        return render_to_response('edittemplate.html', c, context_instance=RequestContext(request))
    # Get all services of that host that contain a service_description
    services = Model.Service.objects.filter(
        host_name=host_name, service_description__contains='')

    if request.method == 'GET':
        for service in services:
            myforms.append(forms.EditTemplateForm(service=service))
    elif request.method == 'POST':
        # All the form fields have an id of HOST::SERVICE::ATTRIBUTE
        for service in services:
            form = forms.EditTemplateForm(service=service, data=request.POST)
            myforms.append(form)
            if form.is_valid():
                try:
                    if form.changed_data != []:
                        form.save()
                        c['messages'].append(
                            _("'%s' successfully saved.") % service.get_description())
                except Exception, e:
                    c['errors'].append(
                        _("Failed to save service %(service)s: %(exc)s") % {'service': service.get_description(), 'exc': e})
            else:
                c['errors'].append(
                    _('invalid data in %s') % service.get_description())
        c['forms'] = myforms
    return render_to_response('edittemplate.html', c, context_instance=RequestContext(request))


@adagios_decorator
def choose_host(request):
    """Simple form that lets you choose one host to edit"""
    c = {}
    c.update(csrf(request))
    if request.method == 'GET':
        c['form'] = forms.ChooseHostForm(initial=request.GET)
    elif request.method == 'POST':
        c['form'] = forms.ChooseHostForm(data=request.POST)
        if c['form'].is_valid():
            host_name = c['form'].cleaned_data['host_name']
            return HttpResponseRedirect(reverse("adagios.okconfig_.views.edit", args=[host_name]))
    return render_to_response('choosehost.html', c, context_instance=RequestContext(request))


@adagios_decorator
def scan_network(request):
    """ Scan a single network and show hosts that are alive
    """
    c = {}
    c['errors'] = []
    if not okconfig.is_valid():
        return verify_okconfig(request)
    if request.method == 'GET':
            if request.GET.has_key('network_address'):
                initial = request.GET
            else:
                my_ip = okconfig.network_scan.get_my_ip_address()
                network_address = "%s/28" % my_ip
                initial = {'network_address': network_address}
            c['form'] = forms.ScanNetworkForm(initial=initial)
    elif request.method == 'POST':
        c['form'] = forms.ScanNetworkForm(request.POST)
        if not c['form'].is_valid():
            c['errors'].append(_("could not validate form"))
        else:
            network = c['form'].cleaned_data['network_address']
            try:
                c['scan_results'] = okconfig.network_scan.get_all_hosts(
                    network)
                for i in c['scan_results']:
                    i.check()
            except Exception, e:
                c['errors'].append(_("Error running scan"))
    return render_to_response('scan_network.html', c, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms


class LiveStatusForm(forms.Form):

    """ This form is used to generate a mk_livestatus query """
    table = forms.ChoiceField()
    columns = forms.MultipleChoiceField()
    filter1 = forms.ChoiceField(required=False)
    filter2 = forms.ChoiceField(required=False)

########NEW FILE########
__FILENAME__ = functions
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

import pynag.Utils
from pynag.Utils import PynagError
from adagios import settings
import subprocess

from django.utils.translation import ugettext as _


def run_pnp(pnp_command, **kwargs):
    """ Run a specific pnp command

    Arguments:
      pnp_command -- examples: image graph json xml export
      host        -- filter results for a specific host
      srv         -- filter results for a specific service
      source      -- Fetch a specific datasource (0,1,2,3, etc)
      view        -- Specific timeframe (0 = 4 hours, 1 = 25 hours, etc)
    Returns:
      Results as they appear from pnp's index.php
    Raises:
      PynagError if command could not be run

    """
    try:
        pnp_path = settings.pnp_path
    except Exception, e1:
        pnp_path = find_pnp_path()
    # Cleanup kwargs
    pnp_arguments = {}
    for k, v in kwargs.items():
        k = str(k)
        if isinstance(v, list):
            v = v[0]
        v = str(v)
        pnp_arguments[k] = v
    querystring = '&'.join(map(lambda x: "%s=%s" % x, pnp_arguments.items()))
    pnp_parameters = pnp_command + "?" + querystring
    command = ['php', pnp_path, pnp_parameters]
    proc = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
    stdout, stderr = proc.communicate('through stdin to stdout')
    result = proc.returncode, stdout, stderr
    return result[1]


def find_pnp_path():
    """ Look through common locations of pnp4nagios, tries to locate it automatically """
    possible_paths = [settings.pnp_filepath]
    possible_paths += [
        "/usr/share/pnp4nagios/html/index.php",
        "/usr/share/nagios/html/pnp4nagios/index.php"
    ]
    for i in possible_paths:
        if os.path.isfile(i):
            return i
    raise PynagError(
        _("Could not find pnp4nagios/index.php. Please specify it in adagios->settings->PNP. Tried %s") % possible_paths)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from django.utils import unittest
from django.test.client import Client
from django.utils.translation import ugettext as _

import pynag.Parsers
from adagios.settings import nagios_config
from adagios.pnp import functions


class PNP4NagiosTestCase(unittest.TestCase):

    def testPnpIsConfigured(self):
        config = pynag.Parsers.config()
        config.parse_maincfg()
        for k, v in config.maincfg_values:
            if k == "broker_module" and v.find('npcd') > 1:
                tmp = v.split()
                self.assertFalse(
                    len(tmp) < 2, _('We think pnp4nagios broker module is incorrectly configured. In nagios.cfg it looks like this: %s') % v)
                module_file = tmp.pop(0)
                self.assertTrue(
                    os.path.exists(module_file), _('npcd broker_module module not found at "%s". Is nagios correctly configured?') % module_file)

                config_file = None
                for i in tmp:
                    if i.startswith('config_file='):
                        config_file = i.split('=', 1)[1]
                        break
                self.assertIsNotNone(
                    config_file, _("npcd broker module has no config_file= argument. Is pnp4nagios correctly configured?"))
                self.assertTrue(
                    os.path.exists(config_file), _('PNP4nagios config file was not found (%s).') % config_file)
                return
        self.assertTrue(
            False, _('Nagios Broker module not found. Is pnp4nagios installed and configured?'))

    def testGetJson(self):
        result = functions.run_pnp('json')
        self.assertGreaterEqual(
            len(result), 0, msg=_("Tried to get json from pnp4nagios but result was improper"))

    def testPageLoad(self):
        c = Client()
        response = c.get('/pnp/json')
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('adagios',
                      (r'^/(?P<pnp_command>.+)?$', 'pnp.views.pnp'),
                       )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.shortcuts import HttpResponse
from adagios.pnp.functions import run_pnp
from adagios.views import adagios_decorator
import json


@adagios_decorator
def pnp(request, pnp_command='image'):
    c = {}
    c['messages'] = []
    c['errors'] = []
    result = run_pnp(pnp_command, **request.GET)
    mimetype = "text"
    if pnp_command == 'image':
        mimetype = "image/png"
    elif pnp_command == 'json':
        mimetype = "application/json"
    return HttpResponse(result, mimetype)

########NEW FILE########
__FILENAME__ = profiling
#!/usr/bin/env python
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Tomas Edwardsson <tommi@tommi.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# Code from https://code.djangoproject.com/wiki/ProfilingDjango

# Documentation at 
# https://github.com/opinkerfi/adagios/wiki/Profiling-Decorators-within-Adagios


import hotshot
import os
import time
import settings
import tempfile
import random

try:
    PROFILE_LOG_BASE = settings.PROFILE_LOG_BASE
except:
    PROFILE_LOG_BASE = tempfile.gettempdir()


def profile(log_file):
    """Profile some callable.

    This decorator uses the hotshot profiler to profile some callable (like
    a view function or method) and dumps the profile data somewhere sensible
    for later processing and examination.

    It takes one argument, the profile log name. If it's a relative path, it
    places it under the PROFILE_LOG_BASE. It also inserts a time stamp into the 
    file name, such that 'my_view.prof' become 'my_view-20100211T170321.prof', 
    where the time stamp is in UTC. This makes it easy to run and compare 
    multiple trials.     
    """

    if not os.path.isabs(log_file):
        log_file = os.path.join(PROFILE_LOG_BASE, log_file)

    def _outer(f):
        def _inner(*args, **kwargs):
            # Add a timestamp to the profile output when the callable
            # is actually called.
            (base, ext) = os.path.splitext(log_file)
            base = base + "-" + time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + str(random.randint(1,9999))
            final_log_file = base + ext

            prof = hotshot.Profile(final_log_file)
            try:
                ret = prof.runcall(f, *args, **kwargs)
            finally:
                prof.close()
            return ret

        return _inner
    return _outer

########NEW FILE########
__FILENAME__ = models
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = objectbrowser
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Temporary wrapper around pynag helpers script

from adagios.misc.helpers import *

########NEW FILE########
__FILENAME__ = status
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This is a wrapper around the rest functionality that exists in
# The status view. We like to keep the actual implementations there
# because we like to keep code close to its apps
from adagios.status.rest import *

########NEW FILE########
__FILENAME__ = tests
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.utils import unittest
from django.test.client import Client
from django.utils.translation import ugettext as _
import json


class LiveStatusTestCase(unittest.TestCase):
    def testPageLoad(self):
        """ Smoke Test for various rest modules """
        self.loadPage('/rest')
        self.loadPage('/rest/status/')
        self.loadPage('/rest/pynag/')
        self.loadPage('/rest/adagios/')
        self.loadPage('/rest/status.js')
        self.loadPage('/rest/pynag.js')
        self.loadPage('/rest/adagios.js')

    def testDnsLookup(self):
        """ Test the DNS lookup rest call
        """
        path = "/rest/pynag/json/dnslookup"
        data = {'host_name': 'localhost'}
        try:
            c = Client()
            response = c.post(path=path, data=data)
            json_data = json.loads(response.content)
            self.assertEqual(response.status_code, 200, _("Expected status code 200 for page %s") % path)
            self.assertEqual(True, 'addresslist' in json_data, _("Expected 'addresslist' to appear in response"))
        except KeyError, e:
            self.assertEqual(True, _("Unhandled exception while loading %(path)s: %(exc)s") % {'path': path, 'exc': e})


    def loadPage(self, url):
        """ Load one specific page, and assert if return code is not 200 """
        try:
            c = Client()
            response = c.get(url)
            self.assertEqual(response.status_code, 200, _("Expected status code 200 for page %s") % url)
        except Exception, e:
            self.assertEqual(True, _("Unhandled exception while loading %(url)s: %(exc)s") % {'url': url, 'exc': e})

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings


urlpatterns = patterns('adagios',
                       url(r'^/?$', 'rest.views.list_modules'),
                       )



# Example:
# rest_modules['module_name'] = 'module_path'
# will make /adagios/rest/module_name/ available and it loads all
# functions from 'module_path'

rest_modules = {}
rest_modules['pynag'] = 'adagios.misc.helpers'
rest_modules['okconfig'] = 'okconfig'
rest_modules['status'] = 'adagios.rest.status'
rest_modules['adagios'] = 'adagios.misc.rest'


# We are going to generate some url patterns, for clarification here is the end result shown for the status module:
#url(r'^/status/$', 'rest.views.index', { 'module_name': 'adagios.rest.status'    }, name="rest/status"),
#url(r'^/status.js$', 'rest.views.javascript', { 'module_name': 'adagios.rest.status'    }, ),
#(r'^/status/(?P<format>.+?)/(?P<attribute>.+?)/?$', 'rest.views.handle_request', { 'module_name': 'adagios.rest.status' }),

for module_name, module_path in rest_modules.items():
    base_pattern = r'^/%s' % module_name
    args = {'module_name': module_name, 'module_path': module_path}
    urlpatterns += patterns('adagios',
        url(base_pattern + '/$',   'rest.views.index', args, name="rest/%s" % module_name),
        url(base_pattern + '.js$', 'rest.views.javascript', args, ),
        url(base_pattern + '/(?P<format>.+?)/(?P<attribute>.+?)/?$', 'rest.views.handle_request', args),
    )

########NEW FILE########
__FILENAME__ = views
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Create your views here.
from django.shortcuts import render_to_response, redirect
from django.core import serializers
from django.http import HttpResponse, HttpResponseServerError
from django.utils import simplejson
#from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.core.urlresolvers import resolve
from adagios.views import adagios_decorator

import inspect
from django import forms
import os
my_module = None
import adagios.rest.urls

def _load(module_path):
    #global my_module
    # if not my_module:
    my_module = __import__(module_path, None, None, [''])
    return my_module


@csrf_exempt
@adagios_decorator
def handle_request(request, module_name, module_path, attribute, format):
    m = _load(module_path)
    # TODO: Only allow function calls if method == POST
    members = {}
    for k, v in inspect.getmembers(m):
        members[k] = v
    item = members[attribute]
    docstring = inspect.getdoc(item)
    if request.method == 'GET':
        if format == 'help':
            result = inspect.getdoc(item)
        elif not inspect.isfunction(item):
            result = item
        else:
            arguments = request.GET
            c = {}
            c['function_name'] = attribute
            c['form'] = CallFunctionForm(function=item, initial=request.GET)
            c['docstring'] = docstring
            c['module_name'] = module_name
            if not request.GET.items():
                return render_to_response('function_form.html', c, context_instance=RequestContext(request))
            # Handle get parameters
            arguments = {}
            for k, v in request.GET.items():
                # TODO: Is it safe to turn all digits to int ?
                #if str(v).isdigit(): v = int(float(v))
                arguments[k.encode('utf-8')] = v.encode('utf-8')
            # Here is a special hack, if the method we are calling has an argument
            # called "request" we will not let the remote user ship it in.
            # instead we give it a django request object
            if 'request' in inspect.getargspec(item)[0]:
                arguments['request'] = request
            result = item(**arguments)
    elif request.method == 'POST':
        item = members[attribute]
        if not inspect.isfunction(item):
            result = item
        else:
            arguments = {}  # request.POST.items()
            for k, v in request.POST.items():
                arguments[k.encode('utf-8')] = v.encode('utf-8')
            # Here is a special hack, if the method we are calling has an argument
            # called "request" we will not let the remote user ship it in.
            # instead we give it a django request object
            if 'request' in inspect.getargspec(item)[0]:
                arguments['request'] = request
            result = item(**arguments)
    else:
        raise BaseException(_("Unsupported operation: %s") % (request.method, ))
    # Everything below is just about formatting the results
    if format == 'json':
        result = simplejson.dumps(
            result, ensure_ascii=False, sort_keys=True, skipkeys=True, indent=4)
        mimetype = 'application/javascript'
    elif format == 'xml':
            # TODO: For some reason Ubuntu does not have this module. Where is
            # it? Should we use lxml instead ?
        import xml.marshal.generic
        result = xml.marshal.generic.dumps(result)
        mimetype = 'application/xml'
    elif format == 'txt':
        result = str(result)
        mimetype = 'text/plain'
    else:
        raise BaseException(
            _("Unsupported format: '%s'. Valid formats: json xml txt") %
            format)
    return HttpResponse(result, mimetype=mimetype)


@adagios_decorator
def list_modules(request):
    """ List all available modules and their basic info

    """
    rest_modules = adagios.rest.urls.rest_modules
    return render_to_response('list_modules.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def index(request, module_name, module_path):
    """ This view is used to display the contents of a given python module
    """
    m = _load(module_path)
    gets, puts = [], []
    blacklist = ('argv', 'environ', 'exit', 'path', 'putenv', 'getenv', )
    for k, v in inspect.getmembers(m):
        if k.startswith('_'):
            continue
        if k in blacklist:
            continue
        if inspect.ismodule(v):
            continue
        elif inspect.isfunction(v):
            puts.append(k)
        else:
            gets.append(k)
    c = {}
    c['module_path'] = module_path
    c['gets'] = gets
    c['puts'] = puts
    c['module_documenation'] = inspect.getdoc(m)
    return render_to_response('index.html', c, context_instance=RequestContext(request))


def javascript(request, module_name, module_path):
    """ Create a javascript library that will wrap around module_path module """
    m = _load(module_path)
    variables, functions = [], []
    blacklist = ('argv', 'environ', 'exit', 'path', 'putenv', 'getenv', )
    members = {}
    for k, v in inspect.getmembers(m):
        if k.startswith('_'):
            continue
        if k in blacklist:
            continue
        if inspect.ismodule(v):
            continue
        if inspect.isfunction(v):
            functions.append(k)
            members[k] = v
        else:
            variables.append(k)
    c = {}
    c['module_path'] = module_path
    c['module_name'] = module_name
    c['gets'] = variables
    c['puts'] = functions
    c['module_documenation'] = inspect.getdoc(m)
    current_url = request.get_full_path()
    baseurl = current_url.replace('.js', '')
    # Find every function, prepare what is needed so template can
    for i in functions:
        argspec = inspect.getargspec(members[i])
        args, varargs, varkw, defaults = argspec
        docstring = inspect.getdoc(members[i])
        if defaults is None:
            defaults = []
        else:
            defaults = list(defaults)
            # Lets create argstring, for the javascript needed
        tmp = [] + args
        argstring = []
        for num, default in enumerate(reversed(defaults)):
            argstring.append('%s=%s' % (tmp.pop(), default))
        argstring.reverse()
        argstring = tmp + argstring
        members[i] = {}
        members[i]['args'] = args
        members[i]['argstring'] = ','.join(args)
        members[i]['varargs'] = varargs
        members[i]['varkw'] = varkw
        members[i]['defaults'] = defaults
        members[i]['docstring'] = docstring
        members[i]['url'] = baseurl + "/json/" + i
        args, varargs, varkw, defaults = argspec
    c['functions'] = members

    return render_to_response('javascript.html', c, mimetype="text/javascript", context_instance=RequestContext(request))


class CallFunctionForm(forms.Form):

    def __init__(self, function, *args, **kwargs):
        super(CallFunctionForm, self).__init__(*args, **kwargs)
        # We will create a field for every function_paramater
        function_paramaters = {}
        # If any paramaters were past via querystring, lets generate fields for
        # them
        if kwargs.has_key('initial'):
            for k, v in kwargs['initial'].items():
                function_paramaters[k] = v
        # Generate fields which resemble our functions default arguments
        argspec = inspect.getargspec(function)
        args, varargs, varkw, defaults = argspec
        self.show_kwargs = varkw is not None
        # We treat the argument 'request' as special. Django request object is going to be
        # passed instead of whatever the user wanted
        if "request" in args:
            args.remove('request')
        if defaults is None:
            defaults = []
        else:
            defaults = list(defaults)
        for i in args:
            self.fields[i] = forms.CharField(label=i)
        for k, v in function_paramaters.items():
            self.fields[k] = forms.CharField(label=k, initial=v)
        while len(defaults) > 0:
            value = defaults.pop()
            field = args.pop()
            self.fields[field].initial = value

########NEW FILE########
__FILENAME__ = settings
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Django settings for adagios project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
USE_TZ = True

# Hack to allow relative template paths
import os
from glob import glob
from warnings import warn
import string

djangopath = os.path.dirname(__file__)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/test',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
# TIME_ZONE = 'Atlantic/Reykjavik'
TIME_ZONE = None
USE_TZ = True

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
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = "%s/media/" % (djangopath)

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'adagios.auth.AuthorizationMiddleWare',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
)

SESSION_ENGINE = 'django.contrib.sessions.backends.file'

LANGUAGES = (
    ('en', 'English'),
    ('fr', 'French'),
)

LOCALE_PATHS = (
    "%s/locale/" % (djangopath),
)

ROOT_URLCONF = 'adagios.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "%s/templates" % (djangopath),
)

INSTALLED_APPS = [
    #'django.contrib.auth',
    #'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'adagios.objectbrowser',
    'adagios.rest',
    'adagios.misc',
    'adagios.pnp',
    'adagios.contrib',
]

TEMPLATE_CONTEXT_PROCESSORS = ('adagios.context_processors.on_page_load',
    #"django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages")


# Themes options #
# To rapidly switch your theme, update THEME_DEFAULT and leave the rest.

# folders in which themes files will be looked up
THEMES_FOLDER = 'themes'  # in 'media/'

# default theme in use, it should be present in the THEMES_FOLDER
# (or at least through a symbolic link)
THEME_DEFAULT = 'default'

# CSS entry-point, in the theme folder
THEME_ENTRY_POINT = 'style.css'

# folder where users preferences are stored
USER_PREFS_PATH = "/etc/adagios/userdata/"


# name displayed in the top left corner
TOPMENU_HOME = 'Adagios'

# items in the top menubar (excluding those coming from %s_menubar.html)
# The identfier is used to recognize active links (which are displayed
# differently).
# The view can begin with '/' (and will go to http://server/...)
# or can be a view name.
# See Nagvis example for direct link, though the template contrib/nagvis.html must be created.
TOPMENU_ITEMS = [
    # Name,        identifier,      view_url,                                icon
    # ('Nagvis',  'nagvis',        '/contrib/nagvis.html',                  'glyph-display'),
    ('Configure', 'objectbrowser', 'objectbrowser.views.list_object_types', 'glyph-edit'),
    ('Nagios',    'nagios',        'misc.views.nagios',                     'glyph-list'),

]

# Graphite #

# the url where to fetch data and images
graphite_url = "http://localhost:9091"

# time ranges for generated graphs
# the CSS identifier only needs to be unique here (it will be prefixed)
GRAPHITE_PERIODS = [
    # Displayed name, CSS identifier, Graphite period
    ('4 hours',       'hours',        '-4h'),
    ('One day',       'day',          '-1d'),
    ('One week',      'week',         '-1w'),
    ('One month',     'month',        '-1mon'),
    ('One year',      'year',         '-1y'),
    ]

# querystring that will be passed on to graphite's render method.
graphite_querystring = "target={host_}.{service_}.{metric_}&width=500&height=200&from={from_}d&lineMode=connected&title={title}&target={host_}.{service_}.{metric_}_warn&target={host_}.{service_}.{metric_}_crit"

# Title format to use on all graphite graphs
graphite_title = "{host} - {service} - {metric}"

# default selected (active) tab, and the one rendered in General-preview
GRAPHITE_DEFAULT_TAB = 'day'

# Adagios specific configuration options. These are just the defaults,
# Anything put in /etc/adagios.d/adagios.conf will overwrite this.
nagios_config = None  # Sensible default is "/etc/nagios/nagios.cfg"
nagios_url = "/nagios"
nagios_init_script = "/etc/init.d/nagios"
nagios_binary = "/usr/bin/nagios"
livestatus_path = None
enable_githandler = False
enable_loghandler = False
enable_authorization = False
enable_status_view = True
enable_bi = True
enable_graphite = False
contrib_dir = "/var/lib/adagios/contrib/"
serverside_includes = "/etc/adagios/ssi"
escape_html_tags = True
warn_if_selinux_is_active = True
destination_directory = "/etc/nagios/adagios/"
administrators = "nagiosadmin,@users"
pnp_url = "/pnp4nagios"
pnp_filepath = "/usr/share/nagios/html/pnp4nagios/index.php"
include = ""
django_secret_key = ""
map_center = "64.119595,-21.655426"
map_zoom = "10"
title_prefix = "Adagios - "
auto_reload = False
refresh_rate = "30"

plugins = {}

# Profiling settings
#
# You can use the @profile("filename") to profile single functions within
# adagios. Not enabled by default on any function.
#
# Documenations at
# https://github.com/opinkerfi/adagios/wiki/Profiling-Decorators-within-Adagios
PROFILE_LOG_BASE = "/var/lib/adagios"

# Load config files from /etc/adagios
# Adagios uses the configuration file in /etc/adagios/adagios.conf by default.
# If it doesn't exist you should create it. Otherwise a adagios.conf will be
# created in the django project root which should be avoided.
adagios_configfile = "/etc/adagios/adagios.conf"


try:
    if not os.path.exists(adagios_configfile):
        alternative_adagios_configfile = "%s/adagios.conf" % djangopath
        message = "Config file '{adagios_configfile}' not found. Using {alternative_adagios_configfile} instead."
        warn(message.format(**locals()))
        adagios_configfile = alternative_adagios_configfile
        open(adagios_configfile, "a").close()

    execfile(adagios_configfile)
    # if config has any default include, lets include that as well
    configfiles = glob(include)
    for configfile in configfiles:
        execfile(configfile)
except IOError, e:
    warn('Unable to open %s: %s' % (adagios_configfile, e.strerror))

try:
    from django.utils.crypto import get_random_string
except ImportError:
    def get_random_string(length, stringset=string.ascii_letters + string.digits + string.punctuation):
        '''
        Returns a string with `length` characters chosen from `stringset`
        >>> len(get_random_string(20)) == 20
        '''
        return ''.join([stringset[i % len(stringset)] for i in [ord(x) for x in os.urandom(length)]])

if not django_secret_key:
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    SECRET_KEY = get_random_string(50, chars)
    try:
        data = "\n# Automaticly generated secret_key\ndjango_secret_key = '%s'\n" % SECRET_KEY
        with open(adagios_configfile, "a") as config_fh:
            config_fh.write(data)
    except Exception, e:
        warn("ERROR: Got %s while trying to save django secret_key in %s" % (type(e), adagios_configfile))

else:
    SECRET_KEY = django_secret_key

ALLOWED_INCLUDE_ROOTS = (serverside_includes,)

if enable_status_view:
    plugins['status'] = 'adagios.status'
if enable_bi:
    plugins['bi'] = 'adagios.bi'

for k, v in plugins.items():
    INSTALLED_APPS.append(v)

import adagios.profiling

# default preferences, for new users or when they are not available
PREFS_DEFAULT = {
    'language': 'en',
    'theme': THEME_DEFAULT,
    'refresh_rate': refresh_rate
}

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.utils.translation import ugettext as _
import adagios.status.utils
import adagios.businessprocess


class LiveStatusForm(forms.Form):

    """ This form is used to generate a mk_livestatus query """
    table = forms.ChoiceField()
    columns = forms.MultipleChoiceField()
    filter1 = forms.ChoiceField(required=False)
    filter2 = forms.ChoiceField(required=False)


class RemoveSubProcessForm(forms.Form):

    """ Remove one specific sub process from a business process
    """
    process_name = forms.CharField(max_length=100, required=True)
    process_type = forms.CharField(max_length=100, required=True)

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(RemoveSubProcessForm, self).__init__(*args, **kwargs)

    def save(self):
        process_name = self.cleaned_data.get('process_name')
        process_type = self.cleaned_data.get('process_type')
        self.bp.remove_process(process_name, process_type)
        self.bp.save()

status_method_choices = map(
    lambda x: (x, x), adagios.businessprocess.BusinessProcess.status_calculation_methods)


class BusinessProcessForm(forms.Form):

    """ Use this form to edit a BusinessProcess """
    name = forms.CharField(max_length=100, required=True,
                           help_text=_("Unique name for this business process."))
    #processes = forms.CharField(max_length=100, required=False)
    display_name = forms.CharField(max_length=100, required=False,
                                   help_text=_("This is the name that will be displayed to users on this process. Usually it is the name of the system this business group represents."))
    notes = forms.CharField(max_length=1000, required=False,
                            help_text=_("Here you can put in any description of the business process you are adding. Its a good idea to write down what the business process is about and who to contact in case of downtimes."))
    status_method = forms.ChoiceField(
        choices=status_method_choices, help_text=_("Here you can choose which method is used to calculate the global status of this business process"))
    state_0 = forms.CharField(max_length=100, required=False,
                              help_text=_("Human friendly text for this respective state. You can type whatever you want but nagios style exit codes indicate that 0 should be 'ok'"))
    state_1 = forms.CharField(max_length=100, required=False,
                              help_text=_("Typically used to represent warning or performance problems"))
    state_2 = forms.CharField(max_length=100, required=False,
                              help_text=_("Typically used to represent critical status"))
    state_3 = forms.CharField(
        max_length=100, required=False, help_text=_("Use this when status is unknown"))
    #graphs = models.ManyToManyField(BusinessProcess, unique=False, blank=True)
    #graphs = models.ManyToManyField(BusinessProcess, unique=False, blank=True)

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(BusinessProcessForm, self).__init__(*args, **kwargs)

    def save(self):
        c = self.cleaned_data
        self.bp.data.update(c)
        self.bp.save()

    def remove(self):
        c = self.data
        process_name = c.get('process_name')
        process_type = c.get('process_type')
        if process_type == 'None':
            process_type = None
        self.bp.remove_process(process_name, process_type)
        self.bp.save()

    def clean(self):
        cleaned_data = super(BusinessProcessForm, self).clean()

        # If name has changed, look if there is another business process with
        # same name.
        new_name = cleaned_data.get('name')
        if new_name and new_name != self.bp.name:
            if new_name in adagios.businessprocess.get_all_process_names():
                raise forms.ValidationError(
                    _("Cannot rename process to %s. Another process with that name already exists") % new_name
                )
        return cleaned_data

    def delete(self):
        """ Delete this business process """
        self.bp.delete()

    def add_process(self):

        process_name = self.data.get('process_name')
        hostgroup_name = self.data.get('hostgroup_name')
        servicegroup_name = self.data.get('servicegroup_name')
        service_name = self.data.get('service_name')

        if process_name:
            self.bp.add_process(process_name, None)
        if hostgroup_name:
            self.bp.add_process(hostgroup_name, None)
        if servicegroup_name:
            self.bp.add_process(servicegroup_name, None)
        if service_name:
            self.bp.add_process(service_name, None)
        self.bp.save()

choices = 'businessprocess', 'hostgroup', 'servicegroup', 'service', 'host'
process_type_choices = map(lambda x: (x, x), choices)


class AddSubProcess(forms.Form):
    process_type = forms.ChoiceField(choices=process_type_choices)
    process_name = forms.CharField(
        widget=forms.HiddenInput(attrs={'style': "width: 300px;"}), max_length=100)
    display_name = forms.CharField(max_length=100, required=False)
    tags = forms.CharField(
        max_length=100, required=False, initial="not critical")

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(AddSubProcess, self).__init__(*args, **kwargs)

    def save(self):
        self.bp.add_process(**self.cleaned_data)
        self.bp.save()


class AddHostgroupForm(forms.Form):
    pass


class AddGraphForm(forms.Form):
    host_name = forms.CharField(max_length=100,)
    service_description = forms.CharField(max_length=100, required=False)
    metric_name = forms.CharField(max_length=100, required=True)
    notes = forms.CharField(max_length=100, required=False,
                            help_text=_("Put here a friendly description of the graph"))

    def __init__(self, instance, *args, **kwargs):
        self.bp = instance
        super(AddGraphForm, self).__init__(*args, **kwargs)

    def save(self):
        self.bp.add_pnp_graph(**self.cleaned_data)
        self.bp.save()

########NEW FILE########
__FILENAME__ = graphite
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Matthieu Caneill <matthieu.caneill@savoirfairelinux.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
import adagios.settings

ILLEGAL_CHAR = re.compile(r'[^\w-]')


def _get_graphite_url(base, host, service, metric, from_):
    """ Constructs an URL for Graphite.

    Args:
      - base (str): base URL for Graphite access
      - host (str): hostname
      - service (str): service, e.g. HTTP
      - metric (str): metric, e.g. size, time
      - from_ (str): Graphite time period

    Returns: str
    """
    host_ = _compliant_name(host)
    service_ = _compliant_name(service)
    metric_ = _compliant_name(metric)
    base = base.rstrip('/')
    title = adagios.settings.graphite_title.format(**locals())

    url = "{base}/render?" + adagios.settings.graphite_querystring
    url = url.format(**locals())
    return url


def _compliant_name(name):
    """ Makes the necessary replacements for Graphite. """
    if name == '_HOST_':
        return '__HOST__'
    name = ILLEGAL_CHAR.sub('_', name)
    return name


def get(base, host, service, metrics, units):
    """ Returns a data structure containg URLs for Graphite.

    The structure looks like:
    [{'name': 'One day',
      'css_id' : 'day',
      'metrics': {'size': 'http://url-of-size-metric',
                  'time': 'http://url-of-time-metric'}
     },
     {...}]

    Args:
      - base (str): base URL for Graphite access
      - host (str): hostname
      - service (str): service, e.g. HTTP
      - metrics (list): list of metrics, e.g. ["size", "time"]
      - units (list): a list of <name,css_id,unit>,
        see adagios.settings.GRAPHITE_PERIODS

    Returns: list
    """
    graphs = []

    for name, css_id, unit in units:
        m = {}
        for metric in metrics:
            m[metric] = _get_graphite_url(base, host, service, metric, unit)
        graph = dict(name=name, css_id=css_id, metrics=m)
        graphs.append(graph)

    return graphs

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = rest
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

Convenient stateless functions for the status module. These are meant for programs to interact
with status of Nagios.

"""

import time
import pynag.Control.Command
import pynag.Model
import pynag.Utils
import adagios.status.utils
import pynag.Parsers
import collections

from django.utils.translation import ugettext as _
from adagios import userdata

def hosts(request, fields=None, **kwargs):
    """ Get List of hosts. Any parameters will be passed straight throught to pynag.Utils.grep()

        Arguments:
            fields -- If specified, a list of attributes to return. If unspecified, all fields are returned.

            Any **kwargs will be treated as a pynag.Utils.grep()-style filter
    """
    return adagios.status.utils.get_hosts(request=request, fields=fields, **kwargs)


def services(request, fields=None, **kwargs):
    """ Similar to hosts(), is a wrapper around adagios.status.utils.get_services()
    """
    return adagios.status.utils.get_services(request=request, fields=fields, **kwargs)

def services_dt(request, fields=None, **kwargs):
    """ Similar to hosts(), is a wrapper around adagios.status.utils.get_services()
    """
    services = adagios.status.utils.get_services(request=request, fields='host_name,description')

    result = {
        'sEcho': len(services),
	'iTotalRecords': len(services),
        'aaData': []
    }
    for service in services:
        result['aaData'].append(service.values())
    return result


def contacts(request, fields=None, *args, **kwargs):
    """ Wrapper around pynag.Parsers.mk_livestatus.get_contacts()
    """
    l = adagios.status.utils.livestatus(request)
    return l.get_contacts(*args, **kwargs)


def emails(request, *args, **kwargs):
    """ Returns a list of all emails of all contacts
    """
    l = adagios.status.utils.livestatus(request)
    return map(lambda x: x['email'], l.get_contacts('Filter: email !='))


def acknowledge_many(hostlist, servicelist, sticky=1, notify=1, persistent=0, author="adagios", comment="acknowledged by Adagios"):
    """ Same as acknowledge, but for acknowledge on many hosts services at a time.

     Arguments:
        hostlist    -- string in the format of host1;host2;host3
        servicelist -- string in the format of host1,service1;host2,service2
    """
    items = []
    for i in hostlist.split(';'):
        if not i: continue
        items.append((i, None))

    for i in servicelist.split(';'):
        if not i: continue
        host_name,service_description = i.split(',')
        items.append((host_name, service_description))
    for i in items:
        acknowledge(
                host_name=i[0],
                service_description=i[1],
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                author=author,
                comment=comment
        )
    return _("Success")


def acknowledge(host_name, service_description=None, sticky=1, notify=1, persistent=0, author='adagios', comment='acknowledged by Adagios'):
    """ Acknowledge one single host or service check """
    if service_description in (None, '', u'', '_HOST_'):
        pynag.Control.Command.acknowledge_host_problem(host_name=host_name,
                                                       sticky=sticky,
                                                       notify=notify,
                                                       persistent=persistent,
                                                       author=author,
                                                       comment=comment,
                                                       )
    else:
        pynag.Control.Command.acknowledge_svc_problem(host_name=host_name,
                                                      service_description=service_description,
                                                      sticky=sticky,
                                                      notify=notify,
                                                      persistent=persistent,
                                                      author=author,
                                                      comment=comment,
                                                      )


def downtime_many(hostlist, servicelist, hostgrouplist, start_time=None, end_time=None, fixed=1, trigger_id=0, duration=7200, author='adagios', comment='Downtime scheduled by adagios', all_services_on_host=False, hostgroup_name=None):
    """ Same as downtime, but for acknowledge on many hosts services at a time.

     Arguments:
        hostlist    -- string in the format of host1;host2;host3
        hostgrouplist -- string in the format of hostgroup1;hostgroup2;hostgroup3
        servicelist -- string in the format of host1,service1;host2,service2
    """
    items = []
    for i in hostlist.split(';'):
        if not i: continue
        items.append((i, None, None))
    for i in hostgrouplist.split(';'):
        if not i: continue
        items.append((None, None, i))

    for i in servicelist.split(';'):
        if not i: continue
        host_name, service_description = i.split(',')
        items.append((host_name, service_description, None))
    for i in items:
        host_name = i[0]
        service_description = i[1]
        hostgroup_name = i[2]
        downtime(
            host_name=host_name,
            service_description=service_description,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
            all_services_on_host=all_services_on_host,
            hostgroup_name=hostgroup_name
        )


def downtime(host_name=None, service_description=None, start_time=None, end_time=None, fixed=1, trigger_id=0, duration=7200, author='adagios', comment='Downtime scheduled by adagios', all_services_on_host=False, hostgroup_name=None):
    """ Schedule downtime for a host or a service """
    if fixed in (1, '1') and start_time in (None, ''):
        start_time = time.time()
    if fixed in (1, '1') and end_time in (None, ''):
        end_time = int(start_time) + int(duration)
    if all_services_on_host == 'false':
        all_services_on_host = False
    elif all_services_on_host == 'true':
        all_services_on_host = True

    # Check if we are supposed to schedule downtime for a whole hostgroup:
    if hostgroup_name:
        result1 = pynag.Control.Command.schedule_hostgroup_host_downtime(
            hostgroup_name=hostgroup_name,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
        ),
        result2 = pynag.Control.Command.schedule_hostgroup_svc_downtime(
            hostgroup_name=hostgroup_name,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
        )
        return result1, result2
    # Check if we are recursively scheduling downtime for host and all its services:
    elif all_services_on_host:
        result1 = pynag.Control.Command.schedule_host_svc_downtime(
            host_name=host_name,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
        ),
        result2 = pynag.Control.Command.schedule_host_downtime(
            host_name=host_name,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
        )
        return result1, result2
    # Otherwise, if this is a host
    elif service_description in (None, '', u'', '_HOST_'):
        return pynag.Control.Command.schedule_host_downtime(
            host_name=host_name,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
        )
    # otherwise it must be a service:
    else:
        return pynag.Control.Command.schedule_svc_downtime(
            host_name=host_name,
            service_description=service_description,
            start_time=start_time,
            end_time=end_time,
            fixed=fixed,
            trigger_id=trigger_id,
            duration=duration,
            author=author,
            comment=comment,
        )

import adagios.utils


def reschedule_many(request, hostlist, servicelist, check_time=None, **kwargs):
    """ Same as reschedule() but takes a list of hosts/services as input

    Arguments:
      hostlist    -- semicolon seperated list of hosts to schedule checks for. Same as multiple calls with host_name=
      servicelist -- Same as hostlist but for services. Format is: host_name,service_description;host_name,service_description
    """
    #task = adagios.utils.Task()
    #WaitCondition = "last_check > %s" % int(time.time()- 1)
    for i in hostlist.split(';'):
        if not i: continue
        reschedule(request, host_name=i, service_description=None, check_time=check_time)
        #task.add(wait, 'hosts', i, WaitCondition)
    for i in servicelist.split(';'):
        if not i: continue
        host_name,service_description = i.split(',')
        reschedule(request, host_name=host_name, service_description=service_description, check_time=check_time)
        #WaitObject = "{h};{s}".format(h=host_name, s=service_description)
        #task.add(wait, 'services', WaitObject, WaitCondition)
    return {'message': _("command sent successfully")}


def reschedule(request, host_name=None, service_description=None, check_time=None, wait=0, hostlist='', servicelist=''):
    """ Reschedule a check of this service/host

    Arguments:
      host_name -- Name of the host
      service_description -- Name of the service check. If left empty, host check will be rescheduled
      check_time -- timestamp of when to execute this check, if left empty, execute right now
      wait -- If set to 1, function will not return until check has been rescheduled
    """

    if check_time is None or check_time is '':
        check_time = time.time()
    if service_description in (None, '', u'', '_HOST_', 'undefined'):
        service_description = ""
        pynag.Control.Command.schedule_forced_host_check(
            host_name=host_name, check_time=check_time)
        if wait == "1":
            livestatus = adagios.status.utils.livestatus(request)
            livestatus.query("GET hosts",
                             "WaitObject: %s " % host_name,
                             "WaitCondition: last_check > %s" % check_time,
                             "WaitTrigger: check",
                             "Filter: host_name = %s" % host_name,
                             )
    else:
        pynag.Control.Command.schedule_forced_svc_check(
            host_name=host_name, service_description=service_description, check_time=check_time)
        if wait == "1":
            livestatus = adagios.status.utils.livestatus(request)
            livestatus.query("GET services",
                             "WaitObject: %s %s" % (
                                 host_name, service_description),
                             "WaitCondition: last_check > %s" % check_time,
                             "WaitTrigger: check",
                             "Filter: host_name = %s" % host_name,
                             )
    return "ok"


def comment(author, comment, host_name, service_description=None, persistent=1):
    """ Adds a comment to a particular service.

    If the "persistent" field is set to zero (0), the comment will be deleted the next time Nagios is restarted.
    Otherwise, the comment will persist across program restarts until it is deleted manually. """

    if service_description in (None, '', u'', '_HOST_'):
        pynag.Control.Command.add_host_comment(
            host_name=host_name, persistent=persistent, author=author, comment=comment)
    else:
        pynag.Control.Command.add_svc_comment(
            host_name=host_name, service_description=service_description, persistent=persistent, author=author, comment=comment)
    return "ok"


def delete_comment(comment_id, object_type=None, host_name=None, service_description=None):
    """
    """
    if not host_name:
        # TODO host_name is not used here, why do we need it ?
        pass
    if object_type == "host" or service_description in (None, '', u'', '_HOST_'):
        pynag.Control.Command.del_host_comment(comment_id=comment_id)
    else:
        pynag.Control.Command.del_svc_comment(comment_id=comment_id)
    return "ok"


def edit(object_type, short_name, attribute_name, new_value):
    """ Change one single attribute for one single object.

    Arguments:
      object_type    -- Type of object to change (i.e. "host","service", etc)
      short_name      -- Short Name of the object f.e. the host_name of a host
      attribute_name -- Name of attribute to change .. f.e. 'address'
      new_value      -- New value of the object .. f.e. '127.0.0.1'
    Examples:
      edit('host','localhost','address','127.0.0.1')
      edit('service', 'localhost/Ping', 'contactgroups', 'None')
    """
    # TODO : MK Livestatus access acording to remote_user
    c = pynag.Model.string_to_class[object_type]
    my_obj = c.objects.get_by_shortname(short_name)
    my_obj[attribute_name] = new_value
    my_obj.save()
    return str(my_obj)


def get_map_data(request, host_name=None):
    """ Returns a list of (host_name,2d_coords). If host_name is provided, returns a list with only that host """
    livestatus = adagios.status.utils.livestatus(request)
    all_hosts = livestatus.query('GET hosts', )
    hosts_with_coordinates = pynag.Model.Host.objects.filter(
        **{'2d_coords__exists': True})
    hosts = []
    connections = []
    for i in all_hosts:
        name = i['name']
        if host_name in (None, '', name):
            # If x does not have any coordinates, break
            coords = None
            for x in hosts_with_coordinates:
                if x.host_name == name:
                    coords = x['2d_coords']
                    break
            if coords is None:
                continue

            tmp = coords.split(',')
            if len(tmp) != 2:
                continue

            x, y = tmp
            host = {}
            host['host_name'] = name
            host['state'] = i['state']
            i['x_coordinates'] = x
            i['y_coordinates'] = y

            hosts.append(i)

    # For all hosts that have network parents, lets return a proper line for
    # those two
    for i in hosts:
        # Loop through all network parents. If network parent is also in our hostlist
        # Then create a connection between the two
        for parent in i.get('parents'):
            for x in hosts:
                if x.get('name') == parent:
                    connection = {}
                    connection['parent_x_coordinates'] = x.get('x_coordinates')
                    connection['parent_y_coordinates'] = x.get('y_coordinates')
                    connection['child_x_coordinates'] = i.get('x_coordinates')
                    connection['child_y_coordinates'] = i.get('y_coordinates')
                    connection['state'] = i.get('state')
                    connection['description'] = i.get('name')
                    connections.append(connection)
    result = {}
    result['hosts'] = hosts
    result['connections'] = connections
    return result


def change_host_coordinates(host_name, latitude, longitude):
    """ Updates longitude and latitude for one specific host """
    host = pynag.Model.Host.objects.get_by_shortname(host_name)
    coords = "%s,%s" % (latitude, longitude)
    host['2d_coords'] = coords
    host.save()


def autocomplete(request, q):
    """ Returns a list of {'hosts':[], 'hostgroups':[],'services':[]} matching search query q
    """
    if q is None:
        q = ''
    result = {}

    hosts = adagios.status.utils.get_hosts(request, host_name__contains=q)
    services = adagios.status.utils.get_services(request, service_description__contains=q)
    hostgroups = adagios.status.utils.get_hostgroups(request, hostgroup_name__contains=q)

    result['hosts'] = sorted(set(map(lambda x: x['name'], hosts)))
    result['hostgroups'] = sorted(set(map(lambda x: x['name'], hostgroups)))
    result['services'] = sorted(set(map(lambda x: x['description'], services)))

    return result


def delete_downtime(downtime_id, is_service=True):
    """ Delete one specific downtime with id that matches downtime_id.

    Arguments:
      downtime_id -- Id of the downtime to be deleted
      is_service  -- If set to True or 1, then this is assumed to be a service downtime, otherwise assume host downtime
    """
    if is_service in (True, 1, '1'):
        pynag.Control.Command.del_svc_downtime(downtime_id)
    else:
        pynag.Control.Command.del_host_downtime(downtime_id)
    return "ok"

def top_alert_producers(limit=5, start_time=None, end_time=None):
    """ Return a list of ["host_name",number_of_alerts]

     Arguments:
        limit      -- Limit output to top n hosts (default 5)
        start_time -- Search log starting with start_time (default since last log rotation)
    """
    if start_time == '':
        start_time = None
    if end_time == '':
        end_time = None
    l = pynag.Parsers.LogFiles()
    log = l.get_state_history(start_time=start_time, end_time=end_time)
    top_alert_producers = collections.defaultdict(int)
    for i in log:
        if 'host_name' in i and 'state' in i and i['state'] > 0:
            top_alert_producers[i['host_name']] += 1
    top_alert_producers = top_alert_producers.items()
    top_alert_producers.sort(cmp=lambda a, b: cmp(a[1], b[1]), reverse=True)
    if limit > len(top_alert_producers):
        top_alert_producers = top_alert_producers[:int(limit)]
    return top_alert_producers


def log_entries(*args, **kwargs):
    """ Same as pynag.Parsers.Logfiles().get_log_entries()

    Arguments:
   start_time -- unix timestamp. if None, return all entries from today
   end_time -- If specified, only fetch log entries older than this (unix timestamp)
   strict   -- If True, only return entries between start_time and end_time, if False,
            -- then return entries that belong to same log files as given timeset
   search   -- If provided, only return log entries that contain this string (case insensitive)
   kwargs   -- All extra arguments are provided as filter on the log entries. f.e. host_name="localhost"
    Returns:
   List of dicts

    """
    l = pynag.Parsers.LogFiles()
    return l.get_log_entries(*args, **kwargs)


def state_history(start_time=None, end_time=None, object_type=None, host_name=None, service_description=None, hostgroup_name=None):
    """ Returns a list of dicts, with the state history of hosts and services. Parameters behaves similar to get_log_entries

    """
    if start_time == '':
        start_time = None
    if end_time == '':
        end_time = None
    if host_name == '':
        host_name = None
    if service_description == '':
        service_description = None
    l = pynag.Parsers.LogFiles()
    log_entries = l.get_state_history(start_time=start_time, end_time=end_time, host_name=host_name, service_description=service_description)
    if object_type == 'host' or object_type == 'service':
        pass
    elif object_type == 'hostgroup':
        hg = pynag.Model.Hostgroup.objects.get_by_shortname(hostgroup_name)
        hosts = hg.get_effective_hosts()
        hostnames = map(lambda x: x.host_name, hosts)
        log_entries = filter(lambda x: x['host_name'] in hostnames, log_entries)
    else:
        raise Exception(_("Unsupported object type: %s") % object_type)

    # Add some css-hints for and duration of each state history entry as percent of duration
    # this is used by all views that have state history and on top of it a progress bar which shows
    # Up/downtime totals.
    c = {'log': log_entries }
    if len(c['log']) > 0:
        log = c['log']
        c['start_time'] = start_time = log[0]['time']
        c['end_time'] = log[-1]['time']
        now = time.time()

        total_duration = now - start_time
        css_hint = {}
        css_hint[0] = 'success'
        css_hint[1] = 'warning'
        css_hint[2] = 'danger'
        css_hint[3] = 'info'
        for i in log:
            i['duration_percent'] = 100 * i['duration'] / total_duration
            i['bootstrap_status'] = css_hint[i['state']]

    return log_entries

def _get_service_model(host_name, service_description=None):
    """ Return one pynag.Model.Service object for one specific service as seen

    from status point of view. That means it will do its best to return a service
    that was assigned to hostgroup but the caller requested a specific host.

    Returns:
        pynag.Model.Service object
    Raises:
        KeyError if not found
    """
    try:
        return pynag.Model.Service.objects.get_by_shortname("%s/%s" % (host_name, service_description))
    except KeyError, e:
        host = pynag.Model.Host.objects.get_by_shortname(host_name)
        for i in host.get_effective_services():
            if i.service_description == service_description:
                return i
        raise e


def command_line(host_name, service_description=None):
    """ Returns effective command line for a host or a service (i.e. resolves check_command) """
    try:
        obj = _get_host_or_service(host_name, service_description)
        return obj.get_effective_command_line(host_name=host_name)
    except KeyError:
        return _("Could not resolve commandline. Object not found")


def _get_host_or_service(host_name, service_description=None):
    """ Return a pynag.Model.Host or pynag.Model.Service or raise exception if none are found """
    host = pynag.Model.Host.objects.get_by_shortname(host_name)
    if not service_description or service_description == '_HOST_':
        return host
    else:
        search_result = pynag.Model.Service.objects.filter(host_name=host_name, service_description=service_description)
        if search_result:
            return search_result[0]
        # If no services were found, the service might be applied to a hostgroup
        for service in host.get_effective_services():
            if service.service_description == service_description:
                return service
    raise KeyError(_("Object not found"))


def update_check_command(host_name, service_description=None, **kwargs):
    """ Saves all custom variables of a given service
    """
    try:
        for k, v in kwargs.items():
            if service_description is None or service_description == '':
                obj = pynag.Model.Host.objects.get_by_shortname(host_name)
            else:
                obj = pynag.Model.Service.objects.get_by_shortname(
                    "%s/%s" % (host_name, service_description))
            if k.startswith("$_SERVICE") or k.startswith('$ARG') or k.startswith('$_HOST'):
                obj.set_macro(k, v)
                obj.save()
        return _("Object saved")
    except KeyError:
        raise Exception(_("Object not found"))


def get_business_process_names():
    """ Returns all configured business processes
    """
    import adagios.businessprocess
    return map(lambda x: x.name, adagios.businessprocess.get_all_processes())


def get(request, object_type, *args, **kwargs):
    livestatus_arguments = pynag.Utils.grep_to_livestatus(*args, **kwargs)
    if not object_type.endswith('s'):
        object_type += 's'
    if 'name__contains' in kwargs and object_type == 'services':
        name = str(kwargs['name__contains'])
        livestatus_arguments = filter(
            lambda x: x.startswith('name'), livestatus_arguments)
        livestatus_arguments.append('Filter: host_name ~ %s' % name)
        livestatus_arguments.append('Filter: description ~ %s' % name)
        livestatus_arguments.append('Or: 2')
    livestatus = adagios.status.utils.livestatus(request)
    results = livestatus.query('GET %s' % object_type, *livestatus_arguments)

    if object_type == 'service':
        for i in results:
            i['name'] = i.get('host_name') + "/" + i.get('description')
    return results


def get_business_process(process_name=None, process_type=None):
    """ Returns a list of all processes in json format.

    If process_name is specified, return all sub processes.
    """
    import adagios.bi
    if not process_name:
        processes = adagios.bi.get_all_processes()
    else:
        process = adagios.bi.get_business_process(str(process_name), process_type)
        processes = process.get_processes()
    result = []
    # Turn processes into nice json
    for i in processes:
        json = {}
        json['state'] = i.get_status()
        json['name'] = i.name
        json['display_name'] = i.display_name
        json['subprocess_count'] = len(i.processes)
        json['process_type'] = i.process_type
        result.append(json)
    return result


def remove_downtime(request, host_name, service_description=None, downtime_id=None):
    """ Remove downtime for one specific host or service """
    downtimes_to_remove = []
    # If downtime_id is not provided, remove all downtimes of that service or host
    if downtime_id:
        downtimes_to_remove.append(downtime_id)
    else:
        livestatus = adagios.status.utils.livestatus(request)
        query_parameters = list()
        query_parameters.append('GET downtimes')
        query_parameters.append('Filter: host_name = {host_name}'.format(**locals()))
        if service_description:
            query_parameters.append('Filter: service_description = {service_description}'.format(**locals()))
        result = livestatus.query(*query_parameters)
        for i in result:
            downtime_id = i['id']
            downtimes_to_remove.append(downtime_id)

    if service_description:
        for i in downtimes_to_remove:
            pynag.Control.Command.del_svc_downtime(downtime_id=i)
    else:
        for i in downtimes_to_remove:
            pynag.Control.Command.del_host_downtime(downtime_id=i)
    return "ok"


def remove_acknowledgement(host_name, service_description=None):
    """ Remove downtime for one specific host or service """
    if not service_description:
        pynag.Control.Command.remove_host_acknowledgement(host_name=host_name)
    else:
        pynag.Control.Command.remove_svc_acknowledgement(host_name=host_name, service_description=service_description)
    return "ok"


def submit_check_result(request, host_name, service_description=None, autocreate=False, status_code=3, plugin_output=_("No message was entered"), performance_data=""):
    """ Submit a passive check_result for a given host or a service

    Arguments:
        host_name           -- Name of the host you want to submit check results for
        service_description -- If provided, submit a result for service this service instead of a host
        autocreate          -- If this is set to True, and host/service does not exist. It will be created
        status_code              -- Nagios style status for the check (0,1,2,3 which means ok,warning,critical, etc)
        plugin_output       -- The text output of the check to display in a web interface
        performance_data    -- Optional, If there are any performance metrics to display
    """
    livestatus = adagios.status.utils.livestatus(request)
    result = {}
    output = plugin_output + " | " + performance_data
    if not service_description:
        object_type = 'host'
        args = pynag.Utils.grep_to_livestatus(host_name=host_name)
        objects = livestatus.get_hosts(*args)
    else:
        object_type = 'service'
        args = pynag.Utils.grep_to_livestatus(host_name=host_name, service_description=service_description)
        objects = livestatus.get_services(*args)

    if not objects and autocreate is True:
        raise Exception(_("Autocreate not implemented yet"))
    elif not objects:
        result['error'] = 'No %s with that name' % object_type
    else:
        if object_type == 'host':
            pynag.Control.Command.process_host_check_result(host_name, status_code, output)
        else:
            pynag.Control.Command.process_service_check_result(host_name, service_description, status_code, output)
        result['message'] = _("Command has been submitted.")
    return result


def statistics(request, **kwargs):
    """ Returns a dict with various statistics on status data. """
    return adagios.status.utils.get_statistics(request, **kwargs)


def metrics(request, **kwargs):
    """ Returns a list of dicts which contain service perfdata metrics
    """
    result = []
    fields = "host_name description perf_data state host_state".split()
    services = adagios.status.utils.get_services(request, fields=fields, **kwargs)
    for service in services:
        metrics = pynag.Utils.PerfData(service['perf_data']).metrics
        metrics = filter(lambda x: x.is_valid(), metrics)
        for metric in metrics:
            metric_dict = {
                'host_name': service['host_name'],
                'service_description': service['description'],
                'state': service['state'],
                'host_state': service['host_state'],
                'label': metric.label,
                'value': metric.value,
                'uom': metric.uom,
                'warn': metric.warn,
                'crit': metric.crit,
                'min': metric.min,
                'max': metric.max,
            }
            result.append(metric_dict)
    return result

def metric_names(request, **kwargs):
    """ Returns the names of all perfdata metrics that match selected request """
    metric_names = set()
    fields = "host_name description perf_data state host_state".split()
    services = adagios.status.utils.get_services(request, fields=fields, **kwargs)
    for service in services:
        metrics = pynag.Utils.PerfData(service['perf_data']).metrics
        metrics = filter(lambda x: x.is_valid(), metrics)
        for metric in metrics:
            metric_names.add(metric.label)

    result = {
        'services that match filter': len(services),
        'filter': kwargs,
        'metric_names': sorted(list(metric_names)),
    }
    return result

def wait(table, WaitObject, WaitCondition=None, WaitTrigger='check', **kwargs):
    print _("Lets wait for"), locals()
    if not WaitCondition:
        WaitCondition = "last_check > %s" % int(time.time()-1)
    livestatus = adagios.status.utils.livestatus(None)
    print _("livestatus ok")
    result = livestatus.get(table, 'Stats: state != 999', WaitObject=WaitObject, WaitCondition=WaitCondition, WaitTrigger=WaitTrigger, **kwargs)
    print _("ok no more waiting for "), WaitObject
    return result


def wait_many(hostlist, servicelist, WaitCondition=None, WaitTrigger='check', **kwargs):
    if not WaitCondition:
        WaitCondition = "last_check > %s" % int(time.time()-1)
    livestatus = adagios.status.utils.livestatus(None)
    for host in hostlist.split(';'):
        if not host:
            continue
        WaitObject = host
        livestatus.get('hosts', WaitObject=WaitObject, WaitCondition=WaitCondition, WaitTrigger=WaitTrigger, **kwargs)
        print WaitObject
    for service in servicelist.split(';'):
        if not service:
            continue
        WaitObject = service.replace(',', ';')
        livestatus.get('services', WaitObject=WaitObject, WaitCondition=WaitCondition, WaitTrigger=WaitTrigger, **kwargs)
        print WaitObject


def toggle_backend_visibility(request, backend_name):
    """ Toggles a backend in user preferences.

    Args:
      request: a Django request
      backend_name (str): The name of the backend.
    """
    user = userdata.User(request)
    if not user.disabled_backends:
        user.disabled_backends = []
    if backend_name in user.disabled_backends:
        user.disabled_backends.remove(backend_name)
    else:
        user.disabled_backends.append(backend_name)
    
    user.save()

########NEW FILE########
__FILENAME__ = adagiostags
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import math
from datetime import datetime, timedelta
from django import template
from django.utils.timesince import timesince
from django.utils.translation import ugettext as _

register = template.Library()

@register.filter("timestamp")
def timestamp(value):
    try:
        return datetime.fromtimestamp(value)
    except AttributeError:
        return ''

@register.filter("duration")
def duration(value):
    """ Used as a filter, returns a human-readable duration.
    'value' must be in seconds.
    """
    zero = datetime.min
    return timesince(zero, zero + timedelta(0, value))

@register.filter("hash")
def hash(h, key):
    return h[key]



########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.utils import unittest
from django.test.client import Client
from django.utils.translation import ugettext as _

import pynag.Parsers
import os
from django.test.client import RequestFactory
import adagios.status
import adagios.status.utils
import adagios.status.graphite
import adagios.settings
import adagios.utils


class LiveStatusTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nagios_config = adagios.settings.nagios_config
        cls.environment = adagios.utils.FakeAdagiosEnvironment()
        cls.environment.create_minimal_environment()
        cls.environment.configure_livestatus()
        cls.environment.update_adagios_global_variables()
        cls.environment.start()
        cls.livestatus = cls.environment.get_livestatus()

        cls.factory = RequestFactory()

    @classmethod
    def tearDownClass(cls):
        cls.environment.terminate()

    def testLivestatusConnectivity(self):
        requests = self.livestatus.query('GET status', 'Columns: requests')
        self.assertEqual(
            1, len(requests), _("Could not get status.requests from livestatus"))

    def testLivestatusConfigured(self):
        config = pynag.Parsers.config(cfg_file=self.nagios_config)
        config.parse_maincfg()
        for k, v in config.maincfg_values:
            if k == "broker_module" and v.find('livestatus') > 1:
                tmp = v.split()
                self.assertFalse(
                    len(tmp) < 2, _(' We think livestatus is incorrectly configured. In nagios.cfg it looks like this: %s') % v)
                module_file = tmp[0]
                socket_file = tmp[1]
                self.assertTrue(
                    os.path.exists(module_file), _(' Livestatus Broker module not found at "%s". Is nagios correctly configured?') % module_file)
                self.assertTrue(
                    os.path.exists(socket_file), _(' Livestatus socket file was not found (%s). Make sure nagios is running and that livestatus module is loaded') % socket_file)
                return
        self.assertTrue(
            False, _('Nagios Broker module not found. Is livestatus installed and configured?'))

    def testPageLoad(self):
        """ Loads a bunch of status pages, looking for a crash """
        self.loadPage('/status/')
        self.loadPage('/status/hosts')
        self.loadPage('/status/services')
        self.loadPage('/status/contacts')
        self.loadPage('/status/parents')
        self.loadPage('/status/state_history')
        self.loadPage('/status/log')
        self.loadPage('/status/comments')
        self.loadPage('/status/downtimes')
        self.loadPage('/status/hostgroups')
        self.loadPage('/status/servicegroups')
        self.loadPage('/status/map')
        self.loadPage('/status/dashboard')

    def test_status_detail(self):
        """ Tests for /status/detail """
        tmp = self.loadPage('/status/detail?contact_name=nagiosadmin')
        self.assertTrue('nagiosadmin belongs to the following' in tmp.content)

        tmp = self.loadPage('/status/detail?host_name=ok_host')
        self.assertTrue('ok_host' in tmp.content)

        tmp = self.loadPage('/status/detail?host_name=ok_host&service_description=ok%20service%201')
        self.assertTrue('ok_host' in tmp.content)

        tmp = self.loadPage('/status/detail?contactgroup_name=admins')
        self.assertTrue('nagiosadmin' in tmp.content)

        
    def testStateHistory(self):
        request = self.factory.get('/status/state_history')
        adagios.status.views.state_history(request)

    def loadPage(self, url, expected_status_code=200):
        """ Load one specific page, and assert if return code is not 200 """
        c = Client()
        response = c.get(url)
        self.assertEqual(response.status_code, expected_status_code, _("Expected status code %(code)s for page %(url)s") % {'code': expected_status_code, 'url': url})
        return response

    def testSubmitCommand(self):
        """ Test adagios.rest.status.submit_check_results
        """
        c = Client()
        data = {}
        data['host_name'] = 'adagios test host'
        data['service_description'] = 'nonexistant'
        data['status_code'] = "0"
        data['plugin_output'] = 'test message'
        data['performance_data'] = ''
        response = c.post('/rest/status/json/submit_check_result', data=data)
        self.assertEqual(200, response.status_code)


class Graphite(unittest.TestCase):
    def test__get_graphite_url(self):
        """ Smoketest for  adagios.status.graphite._get_graphite_url() """
        base = "http://localhost/graphite"
        host = "localhost"
        service = "Ping"
        metric = "packetloss"
        from_ = "-1d"
        parameters = locals()
        parameters.pop('self', None)
        result = adagios.status.graphite._get_graphite_url(**parameters)
        self.assertTrue(result.startswith(base))
        self.assertTrue(host in result)
        self.assertTrue(service in result)
        self.assertTrue(metric in result)

    def test_get(self):
        """ Smoketest for adagios.status.graphite.get() """
        base = "http://localhost/graphite"
        host = "localhost"
        service = "Ping"
        metrics = ["packetloss", "rta"]
        units = [("test", "test", "-1d")]
        parameters = locals()
        parameters.pop('self', None)
        result = adagios.status.graphite.get(**parameters)
        self.assertTrue(result)
        self.assertTrue(len(result) == 1)
        self.assertTrue('rta' in result[0]['metrics'])
        self.assertTrue('packetloss' in result[0]['metrics'])

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('adagios',
                        url(r'^/?$', 'status.views.status_index'),
                        url(r'^/acknowledgements/?$', 'status.views.acknowledgement_list'),
                        url(r'^/error/?$', 'status.views.error_page'),
                        url(r'^/comments/?$', 'status.views.comment_list'),
                        url(r'^/contacts/?$', 'status.views.contact_list'),
                        url(r'^/contactgroups/?$', 'status.views.contactgroups'),
                        url(r'^/dashboard/?$', 'status.views.dashboard'),
                        url(r'^/detail/?$', 'status.views.detail'),
                        url(r'^/downtimes/?$', 'status.views.downtime_list'),
                        url(r'^/hostgroups/?$', 'status.views.status_hostgroups'),
                        url(r'^/hosts/?$', 'status.views.hosts'),
                        url(r'^/log/?$', 'status.views.log'),
                        url(r'^/map/?', 'status.views.map_view'),
                        url(r'^/parents/?$', 'status.views.network_parents'),
                        url(r'^/perfdata/?$', 'status.views.perfdata'),
                        url(r'^/perfdata2/?$', 'status.views.perfdata2'),
                        url(r'^/problems/?$', 'status.views.problems'),
                        url(r'^/servicegroups/?$', 'status.views.status_servicegroups'),
                        url(r'^/services/?$', 'status.views.services'),
                        url(r'^/state_history/?$', 'status.views.state_history'),
                        url(r'^/backends/?$', 'status.views.backends'),



                        # Misc snippets
                        url(r'^/snippets/log/?$', 'status.views.snippets_log'),
                        url(r'^/snippets/services/?$', 'status.views.snippets_services'),
                        url(r'^/snippets/hosts/?$', 'status.views.snippets_hosts'),

                        # Misc tests
                        url(r'^/test/services/?$', 'status.views.services_js'),
                        url(r'^/test/status_dt/?$', 'status.views.status_dt'),
                        url(r'^/test/livestatus/?$', 'status.views.test_livestatus'),

                        # Deprecated as of 2013-03-23
                        url(r'^/contacts/(?P<contact_name>.+)/?$', 'status.views.contact_detail'),
                        url(r'^/hostgroups/(?P<hostgroup_name>.+)/?$', 'status.views.status_hostgroup'),
                        url(r'^/contactgroups/(?P<contactgroup_name>.+)/?$', 'status.views.contactgroup_detail'),
                        url(r'^/servicegroups/(?P<servicegroup_name>.+)/?$', 'status.views.servicegroup_detail'),
                        url(r'^/services_old/?$', 'status.views.status'),


                        )

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Utility functions for the status app. These are mostly used by
# adagios.status.views

import pynag.Utils
import pynag.Parsers
import adagios.settings
from adagios.misc.rest import add_notification, clear_notification
import simplejson as json

from collections import defaultdict
from adagios import userdata

state = defaultdict(lambda: "unknown")
state[0] = "ok"
state[1] = "warning"
state[2] = "critical"

def get_all_backends():
    # TODO: Properly support multiple instances, using split here is not a good idea
    backends = adagios.settings.livestatus_path or ''
    backends = backends.split(',')
    backends = map(lambda x: x.strip(), backends)
    return backends


def livestatus(request):
    """ Returns a new pynag.Parsers.mk_livestatus() object with authauser automatically set from request.META['remoteuser']
    """

    if request is None:
        authuser = None
    elif adagios.settings.enable_authorization and not adagios.auth.has_role(request, 'administrators') and not adagios.auth.has_role(request, 'operators'):
        authuser = request.META.get('REMOTE_USER', None)
    else:
        authuser = None
    
    backends = get_all_backends()
    # we remove the disabled backends
    if backends is not None:
        try:
            user = userdata.User(request)
            if user.disabled_backends is not None:
                backends = filter(lambda x: x not in user.disabled_backends, backends)
            clear_notification("userdata problem")
        except Exception as e:
            message = "%s: %s" % (type(e), str(e))
            add_notification(level="warning", notification_id="userdata problem", message=message)

    livestatus = pynag.Parsers.MultiSite(
        nagios_cfg_file=adagios.settings.nagios_config,
        livestatus_socket_path=adagios.settings.livestatus_path,
        authuser=authuser)
    
    for i in backends:
        livestatus.add_backend(path=i, name=i)
    
    return livestatus


def query(request, *args, **kwargs):
    """ Wrapper around pynag.Parsers.mk_livestatus().query(). Any authorization logic should be performed here. """
    l = livestatus(request)
    return l.query(*args, **kwargs)


def get_hostgroups(request, *args, **kwargs):
    """ Get a list of hostgroups from mk_livestatus
    """
    l = livestatus(request)
    return l.get_hostgroups(*args, **kwargs)


def get_hosts(request, tags=None, fields=None, *args, **kwargs):
    """ Get a list of hosts from mk_livestatus

     This is a wrapper around pynag.Parsers.mk_livestatus().query()

     Arguments:
        request  - Not in use
        tags     - Not in use
        fields   - If fields=None, return all columns, otherwise return only the columns provided

        Any *args will be passed directly to livestatus
        Any **kwargs will be converted to livestatus "'Filter:' style strings

     Returns:
        A list of dict (hosts)
    """
    if 'q' in kwargs:
        q = kwargs.get('q')
        del kwargs['q']
        if not isinstance(q, list):
            q = [q]
    else:
        q = []

    # Often search filters include description, which we will skip
    kwargs.pop('description', None)

    if 'host_state' in kwargs:
        kwargs['state'] = kwargs.pop('host_state')

    # If keyword "unhandled" is in kwargs, then we will fetch unhandled
    # hosts only
    if 'unhandled' in kwargs:
        del kwargs['unhandled']
        kwargs['state'] = 1
        kwargs['acknowledged'] = 0
        kwargs['scheduled_downtime_depth'] = 0
        #kwargs['host_scheduled_downtime_depth'] = 0
        #kwargs['host_acknowledged'] = 0

    arguments = pynag.Utils.grep_to_livestatus(*args, **kwargs)
    # if "q" came in from the querystring, lets filter on host_name
    for i in q:
        arguments.append('Filter: name ~~ %s' % i)
        arguments.append('Filter: address ~~ %s' % i)
        arguments.append('Filter: plugin_output ~~ %s' % i)
        arguments.append('Or: 3')
    if fields is None:
        fields = [
            'name', 'plugin_output', 'last_check', 'state', 'services', 'services_with_info', 'services_with_state',
            'parents', 'childs', 'address', 'last_state_change', 'acknowledged', 'downtimes', 'comments_with_info',
            'scheduled_downtime_depth', 'num_services_crit', 'num_services_warn', 'num_services_unknown',
            'num_services_ok', 'num_services_pending']
    # fields should be a list, lets create a Column: query for livestatus
    if isinstance(fields, (str, unicode)):
        fields = fields.split(',')
    if len(fields) > 0:
        argument = 'Columns: %s' % (' '.join(fields))
        arguments.append(argument)
    l = livestatus(request)
    result = l.get_hosts(*arguments)

    # Add statistics to every hosts:
    for host in result:
        try:
            host['num_problems'] = host['num_services_crit'] + \
                host['num_services_warn'] + host['num_services_unknown']
            host['children'] = host['services_with_state']

            if host.get('last_state_change') == 0:
                host['state'] = 3
            host['status'] = state[host['state']]

            ok = host.get('num_services_ok')
            warn = host.get('num_services_warn')
            crit = host.get('num_services_crit')
            pending = host.get('num_services_pending')
            unknown = host.get('num_services_unknown')
            total = ok + warn + crit + pending + unknown
            host['total'] = total
            host['problems'] = warn + crit + unknown
            try:
                total = float(total)
                host['health'] = float(ok) / total * 100.0
                host['percent_ok'] = ok / total * 100
                host['percent_warn'] = warn / total * 100
                host['percent_crit'] = crit / total * 100
                host['percent_unknown'] = unknown / total * 100
                host['percent_pending'] = pending / total * 100
            except ZeroDivisionError:
                host['health'] = 'n/a'
        except Exception:
            pass

    # Sort by host and service status
    result.sort(reverse=True, cmp=lambda a, b: cmp(a.get('num_problems'), b.get('num_problems')))
    result.sort(reverse=True, cmp=lambda a, b: cmp(a.get('state'), b.get('state')))
    return result


def get_services(request=None, tags=None, fields=None, *args, **kwargs):
    """ Get a list of services from mk_livestatus.

        This is a wrapper around pynag.Parsers.mk_livestatus().query()

        Arguments:
            requests - Not in use
            tags     - List of 'tags' that will be passed on as a filter to the services.
                       Example of service tags are: problem, unhandled, ishandled,
            fields   - If fields=None, return all columns, otherwise return only the columns provided.
                       fields can be either a list or a comma seperated string
        Any *args will be passed directly to livestatus

        Any **kwargs passed in will be converted to livestatus 'Filter:' strings

        Examples:
        get_services(host_name='localhost') # same as livestatus.query('GET services','Filter: host_name = localhost')

        get_services('Authuser: admin', host_name='localhost')

    """
    if 'q' in kwargs:
        q = kwargs.get('q')
        del kwargs['q']
    else:
        q = []
    if not isinstance(q, list):
        q = [q]

    # If keyword "unhandled" is in kwargs, then we will fetch unhandled
    # services only
    if 'unhandled' in kwargs:
        del kwargs['unhandled']
        kwargs['state__isnot'] = 0
        kwargs['acknowledged'] = 0
        kwargs['scheduled_downtime_depth'] = 0
        kwargs['host_scheduled_downtime_depth'] = 0
        kwargs['host_acknowledged'] = 0
        kwargs['host_state'] = 0
    arguments = pynag.Utils.grep_to_livestatus(*args, **kwargs)

    # If q was added, it is a fuzzy filter on services
    for i in q:
        arguments.append('Filter: host_name ~~ %s' % i)
        arguments.append('Filter: description ~~ %s' % i)
        arguments.append('Filter: plugin_output ~~ %s' % i)
        arguments.append('Filter: host_address ~~ %s' % i)
        arguments.append('Or: 4')

    if fields is None:
        fields = [
            'host_name', 'description', 'plugin_output', 'last_check', 'host_state', 'state', 'scheduled_downtime_depth',
            'last_state_change', 'acknowledged', 'downtimes', 'host_downtimes', 'comments_with_info']
    # fields should be a list, lets create a Column: query for livestatus
    if isinstance(fields, (str, unicode)):
        fields = fields.split(',')
    if len(fields) > 0:
        argument = 'Columns: %s' % (' '.join(fields))
        arguments.append(argument)
    l = livestatus(request)
    result = l.get_services(*arguments)

    # Add custom tags to our service list
    try:
        for service in result:
            # Tag the service with tags such as problems and unhandled
            service_tags = []
            if service['state'] != 0:
                service_tags.append('problem')
                service_tags.append('problems')
                if service['acknowledged'] == 0 and service['downtimes'] == [] and service['host_downtimes'] == []:
                    service_tags.append('unhandled')
                    service['unhandled'] = "unhandled"
                else:
                    service_tags.append('ishandled')
                    service['handled'] = "handled"
            elif service.get('last_state_change') == 0:
                service['state'] = 3
                service_tags.append('pending')
            else:
                service_tags.append('ok')
            if service['acknowledged'] == 1:
                service_tags.append('acknowledged')
            if service['downtimes'] != []:
                service_tags.append('downtime')
            service['tags'] = ' '.join(service_tags)
            service['status'] = state[service['state']]

        if isinstance(tags, str):
            tags = [tags]
        if isinstance(tags, list):
            result = pynag.Utils.grep(result, tags__contains=tags)
    except Exception:
        pass
    return result


def get_contacts(request, *args, **kwargs):
    l = livestatus(request)
    return l.get_contacts(*args, **kwargs)


def get_contactgroups(request, *args, **kwargs):
    l = livestatus(request)
    return l.get_contactgroups(*args, **kwargs)


def get_statistics(request, *args, **kwargs):
    """ Return a list of dict. That contains various statistics from mk_livestatus (like service totals and host totals)
    """
    c = {}
    l = livestatus(request)
    arguments = pynag.Utils.grep_to_livestatus(*args, **kwargs)

    # Get service totals as an array of [ok,warn,crit,unknown]
    c['service_totals'] = l.get_services(
        'Stats: state = 0',
        'Stats: state = 1',
        'Stats: state = 2',
        'Stats: state = 3',
        *arguments
    ) or [0, 0, 0, 0]

    # Get host totals as an array of [up,down,unreachable]
    c['host_totals'] = l.get_hosts(
        'Stats: state = 0',
        'Stats: state = 1',
        'Stats: state = 2',
        *arguments
    ) or [0, 0, 0]

    # Get total number of host/ host_problems
    c['total_hosts'] = sum(c['host_totals'])
    c['total_host_problems'] = c['total_hosts'] - c['host_totals'][0]

    # Get total number of services/ service_problems
    c['total_services'] = sum(c['service_totals'])
    c['total_service_problems'] = c['total_services'] - c['service_totals'][0]

    # Calculate percentage of hosts/services that are "ok"
    try:
        c['service_totals_percent'] = map(lambda x: float(100.0 * x / c['total_services']), c['service_totals'])
    except ZeroDivisionError:
        c['service_totals_percent'] = [0, 0, 0, 0]
    try:
        c['host_totals_percent'] = map(lambda x: float(100.0 * x / c['total_hosts']), c['host_totals'])
    except ZeroDivisionError:
        c['host_totals_percent'] = [0, 0, 0, 0]
    
    unhandled_services = l.get_services(
        'Stats: state > 0',
        acknowledged=0,
        scheduled_downtime_depth=0,
        host_state=0,
        *arguments
    ) or [0]

    unhandled_hosts = l.get_hosts(
        'Stats: state = 1',
        acknowledged=0,
        scheduled_downtime_depth=0,
        *arguments
    ) or [0]

    c['unhandled_services'] = unhandled_services[0]
    c['unhandled_hosts'] = unhandled_hosts[0]

    total_unhandled_network_problems = l.get_hosts(
        'Filter: childs != ',
        'Stats: state = 1',
        acknowledged=0,
        scheduled_downtime_depth=0,
        *arguments
    ) or [0]
    c['total_unhandled_network_problems'] = total_unhandled_network_problems[0]

    tmp = l.get_hosts(
        'Filter: childs != ',
        'Stats: state >= 0',
        'Stats: state > 0',
        *arguments
    ) or [0, 0]

    c['total_network_parents'], c['total_network_problems'] = tmp
    return c


def grep_to_livestatus(object_type, *args, **kwargs):
    """ Take querystring parameters from django request object, and returns list of livestatus queries

        Should support both hosts and services.

        It does minimal support for views have hosts and services in same view and user wants to
        enter some querystring parameters for both.

    """
    result = []
    for key in kwargs:
        if hasattr(kwargs, 'getlist'):
            values = kwargs.getlist(key)
        else:
            values = [kwargs.get(key)]

        if object_type == 'host' and key.startswith('service_'):
            continue
        if object_type == 'host' and key == 'description':
            continue
        if object_type == 'host' and key in ('host_scheduled_downtime_depth', 'host_acknowledged', 'host_state'):
            key = key[len('host_'):]
        if object_type == 'service' and key in ('service_state', 'service_description'):
            key = key[len('service_'):]

        if object_type == 'service' and key == 'unhandled':
            tmp = {}
            tmp['state__isnot'] = 0
            tmp['acknowledged'] = 0
            tmp['scheduled_downtime_depth'] = 0
            tmp['host_scheduled_downtime_depth'] = 0
            tmp['host_acknowledged'] = 0
            tmp['host_state'] = 0
            result += pynag.Utils.grep_to_livestatus(**kwargs)
        elif object_type == 'host' and key == 'unhandled':
            tmp = {}
            tmp['state__isnot'] = 0
            tmp['acknowledged'] = 0
            tmp['scheduled_downtime_depth'] = 0
        elif object_type == 'host' and key == 'q':
            for i in values:
                result.append('Filter: name ~~ %s' % i)
                result.append('Filter: address ~~ %s' % i)
                result.append('Filter: plugin_output ~~ %s' % i)
                result.append('Or: 3')
        elif object_type == 'service' and key == 'q':
            for i in values:
                result.append('Filter: host_name ~~ %s' % i)
                result.append('Filter: description ~~ %s' % i)
                result.append('Filter: plugin_output ~~ %s' % i)
                result.append('Filter: host_address ~~ %s' % i)
                result.append('Or: 4')
        else:
            for value in values:
                result += pynag.Utils.grep_to_livestatus(**{key: value})

    return list(args) + result


########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2010, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpResponse

import time
from os.path import dirname
from collections import defaultdict
import json
import traceback

from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.utils.encoding import smart_str
from django.core.context_processors import csrf
from django.utils.translation import ugettext as _

import pynag.Model
import pynag.Utils
import pynag.Control
import pynag.Plugins
import pynag.Model.EventHandlers
from pynag.Parsers import ParserError

import adagios.settings
from adagios.pnp.functions import run_pnp
from adagios.status import utils
import adagios.status.rest
import adagios.status.forms
import adagios.businessprocess
from django.core.urlresolvers import reverse
from adagios.status import graphite

state = defaultdict(lambda: "unknown")
state[0] = "ok"
state[1] = "warning"
state[2] = "critical"

from adagios.views import adagios_decorator, error_page


@adagios_decorator
def detail(request):
    """ Return status detail view for a single given host, hostgroup,service, contact, etc """
    host_name = request.GET.get('host_name')
    service_description = request.GET.get('service_description')
    contact_name = request.GET.get('contact_name')
    hostgroup_name = request.GET.get('hostgroup_name')
    contactgroup_name = request.GET.get('contactgroup_name')
    servicegroup_name = request.GET.get('servicegroup_name')
    if service_description:
        return service_detail(request, host_name=host_name, service_description=service_description)
    elif host_name:
        return host_detail(request, host_name=host_name)
    elif contact_name:
        return contact_detail(request, contact_name=contact_name)
    elif contactgroup_name:
        return contactgroup_detail(request, contactgroup_name=contactgroup_name)
    elif hostgroup_name:
        return hostgroup_detail(request, hostgroup_name=hostgroup_name)
    elif servicegroup_name:
        return servicegroup_detail(request, servicegroup_name=servicegroup_name)

    raise Exception(_("You have to provide an item via querystring so we know what to give you details for"))


@adagios_decorator
def status_parents(request):
    """ Here for backwards compatibility """
    return network_parents(request)


@adagios_decorator
def network_parents(request):
    """ List of hosts that are network parents """
    c = {}
    c['messages'] = []
    authuser = request.GET.get('contact_name', None)
    livestatus = utils.livestatus(request)
    fields = "name childs state scheduled_downtime_depth address last_check last_state_change acknowledged downtimes services services_with_info".split()
    hosts = utils.get_hosts(request, 'Filter: childs !=', fields=fields, **request.GET)
    host_dict = {}
    map(lambda x: host_dict.__setitem__(x['name'], x), hosts)
    c['hosts'] = []

    for i in hosts:
        if i['childs']:

            c['hosts'].append(i)
            ok = 0
            crit = 0
            i['child_hosts'] = []
            for x in i['childs']:
                i['child_hosts'].append(host_dict[x])
                if host_dict[x]['state'] == 0:
                    ok += 1
                else:
                    crit += 1
            total = float(len(i['childs']))
            i['health'] = float(ok) / total * 100.0
            i['percent_ok'] = ok / total * 100
            i['percent_crit'] = crit / total * 100

    return render_to_response('status_parents.html', c, context_instance=RequestContext(request))


@adagios_decorator
def status(request):
    """ Compatibility layer around status.views.services
    """
    # return render_to_response('status.html', c, context_instance=RequestContext(request))
    # Left here for compatibility reasons:
    return services(request)


@adagios_decorator
def services(request):
    """ This view handles list of services  """
    c = {}
    c['messages'] = []
    c['errors'] = []
    fields = [
        'host_name', 'description', 'plugin_output', 'last_check', 'host_state', 'state',
        'last_state_change', 'acknowledged', 'downtimes', 'host_downtimes', 'comments_with_info']
    c['services'] = utils.get_services(request, fields=fields, **request.GET)
    return render_to_response('status_services.html', c, context_instance=RequestContext(request))

@adagios_decorator
def services_js(request):
    """ This view handles list of services  """
    c = {}
    c['messages'] = []
    c['errors'] = []
    fields = [
        'host_name', 'description', 'plugin_output', 'last_check', 'host_state', 'state',
        'last_state_change', 'acknowledged', 'downtimes', 'host_downtimes', 'comments_with_info']
    c['services'] = json.dumps(utils.get_services(request, fields=fields, **request.GET))
    return render_to_response('status_services_js.html', c, context_instance=RequestContext(request))


@adagios_decorator
def status_dt(request):
    """ This view handles list of services  """
    c = {}
    return render_to_response('status_dt.html', c, context_instance=RequestContext(request))


@adagios_decorator
def snippets_services(request):
    """ Returns a html stub with only the services view """
    c = {}
    c['messages'] = []
    c['errors'] = []
    fields = [
        'host_name', 'description', 'plugin_output', 'last_check', 'host_state', 'state',
        'last_state_change', 'acknowledged', 'downtimes', 'host_downtimes', 'comments_with_info']
    c['services'] = utils.get_services(request, fields=fields, **request.GET)
    return render_to_response('snippets/status_servicelist_snippet.html', c, context_instance=RequestContext(request))

@adagios_decorator
def snippets_hosts(request):
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['hosts'] = utils.get_hosts(request, **request.GET)
    c['host_name'] = request.GET.get('detail', None)
    return render_to_response('snippets/status_hostlist_snippet.html', c, context_instance=RequestContext(request))


@adagios_decorator
def snippets_log(request):
    """ Returns a html stub with the  snippet_statehistory_snippet.html
    """
    host_name = request.GET.get('host_name')
    service_description = request.GET.get('service_description')
    hostgroup_name = request.GET.get('hostgroup_name')

    if service_description == "_HOST_":
        service_description = None

    l = pynag.Parsers.LogFiles(maincfg=adagios.settings.nagios_config)
    log = l.get_state_history(host_name=host_name, service_description=service_description)

    # If hostgroup_name was specified, lets get all log entries that belong to that hostgroup
    if host_name and service_description:
        object_type = 'service'
    elif hostgroup_name:
        object_type = "hostgroup"
        hg = pynag.Model.Hostgroup.objects.get_by_shortname(hostgroup_name)
        hosts = hg.get_effective_hosts()
        hostnames = map(lambda x: x.host_name, hosts)
        log = filter(lambda x: x['host_name'] in hostnames, log)
    elif host_name:
        object_type = "host"
    else:
        raise Exception(_("Need either a host_name or hostgroup_name parameter"))

    c = {'log':log}
    c['object_type'] = object_type
    # Create some state history progress bar from our logs:
    if len(c['log']) > 0:
        log = c['log']
        c['start_time'] = start_time = log[0]['time']
        c['end_time'] = end_time = log[-1]['time']
        now = time.time()

        total_duration = now - start_time
        state_hist = []
        start = start_time
        last_item = None
        css_hint = {}
        css_hint[0] = 'success'
        css_hint[1] = 'warning'
        css_hint[2] = 'danger'
        css_hint[3] = 'unknown'
        for i in log:
            i['duration_percent'] = 100 * i['duration'] / total_duration
            i['bootstrap_status'] = css_hint[i['state']]

    return render_to_response('snippets/status_statehistory_snippet.html', locals(), context_instance=RequestContext(request))


@adagios_decorator
def host_detail(request, host_name):
    """ Return status detail view for a single host """
    return service_detail(request, host_name=host_name, service_description=None)


@adagios_decorator
def service_detail(request, host_name, service_description):
    """ Displays status details for one host or service """
    c = {}
    c['messages'] = []
    c['errors'] = []

    livestatus = utils.livestatus(request)
    backend = request.GET.get('backend')
    c['pnp_url'] = adagios.settings.pnp_url
    c['nagios_url'] = adagios.settings.nagios_url
    c['request'] = request
    now = time.time()
    seconds_in_a_day = 60 * 60 * 24
    seconds_passed_today = now % seconds_in_a_day
    today = now - seconds_passed_today  # midnight of today

    try:
        c['host'] = my_host = livestatus.get_host(host_name, backend)
        my_host['object_type'] = 'host'
        my_host['short_name'] = my_host['name']
    except IndexError:
        c['errors'].append(_("Could not find any host named '%s'") % host_name)
        return error_page(request, c)

    if service_description is None:
        tmp = request.GET.get('service_description')
        if tmp is not None:
            return service_detail(request, host_name, service_description=tmp)
        primary_object = my_host
        c['service_description'] = '_HOST_'
        #c['log'] = pynag.Parsers.LogFiles(maincfg=adagios.settings.nagios_config).get_state_history(
        #    host_name=host_name, service_description=None)
    else:
        try:
            c['service'] = my_service = livestatus.get_service(
                host_name, service_description, backend=backend)
            my_service['object_type'] = 'service'
            c['service_description'] = service_description
            my_service['short_name'] = "%s/%s" % (
                my_service['host_name'], my_service['description'])
            primary_object = my_service
            #c['log'] = pynag.Parsers.LogFiles(maincfg=adagios.settings.nagios_config).get_state_history(
            #    host_name=host_name, service_description=service_description)
        except IndexError:
            c['errors'].append(
                _("Could not find any service named '%s'") % service_description)
            return error_page(request, c)

    c['my_object'] = primary_object
    c['object_type'] = primary_object['object_type']

    # Friendly statusname (i.e. turn 2 into "critical")
    primary_object['status'] = state[primary_object['state']]

    # Plugin longoutput comes to us with special characters escaped. lets undo
    # that:
    primary_object['long_plugin_output'] = primary_object[
        'long_plugin_output'].replace('\\n', '\n')

    # Service list on the sidebar should be sorted
    my_host['services_with_info'] = sorted(
        my_host.get('services_with_info', []))
    c['host_name'] = host_name

    perfdata = primary_object['perf_data']
    perfdata = pynag.Utils.PerfData(perfdata)
    for i, datum in enumerate(perfdata.metrics):
        datum.i = i
        try:
            datum.status = state[datum.get_status()]
        except pynag.Utils.PynagError:
            datum.status = state[3]
    c['perfdata'] = perfdata.metrics
    
    # Get a complete list of network parents
    try:
        c['network_parents'] = reversed(_get_network_parents(request, host_name))
    except Exception, e:
        c['errors'].append(e)

    # Lets get some graphs
    try:
        tmp = run_pnp("json", host=host_name)
        tmp = json.loads(tmp)
    except Exception, e:
        tmp = []
        c['pnp4nagios_error'] = e
    c['graph_urls'] = tmp
    
    if adagios.settings.enable_graphite:
        metrics = [x.label for x in perfdata.metrics]
        service = c['service_description'].replace(' ', '_')
        c['graphite'] = graphite.get(adagios.settings.graphite_url,
                                     c['host_name'],
                                     service,
                                     metrics,
                                     adagios.settings.GRAPHITE_PERIODS,
                                     )
        # used in the General tab - preview
        for graph in c['graphite']:
            if graph['css_id'] == adagios.settings.GRAPHITE_DEFAULT_TAB:
                default = {}
                for k,v in graph['metrics'].items():
                    default[k] = v
                c['graphite_default'] = default
    
    return render_to_response('status_detail.html', c, context_instance=RequestContext(request))


def _get_network_parents(request, host_name):
    """ Returns a list of hosts that are network parents (or grandparents) to host_name

     Every item in the list is a host dictionary from mk_livestatus

     Returns:
        List of lists

     Example:
        _get_network_parents('remotehost.example.com')
        [
            ['gateway.example.com', 'mod_gearman.example.com'],
            ['localhost'],
        ]
    """
    result = []
    backend = request.GET.get('backend', None)
    livestatus = adagios.status.utils.livestatus(request)
    if isinstance(host_name, unicode):
        host_name = smart_str(host_name)

    if isinstance(host_name, str):
        host = livestatus.get_host(host_name, backend)
    elif isinstance(host_name, dict):
        host = host_name
    else:
        raise KeyError(
            'host_name must be str or dict (got %s)' % type(host_name))
    parent_names = host['parents']
    while len(parent_names) > 0:
        parents = map(lambda x: livestatus.get_host(x, backend), parent_names)

        # generate a list of grandparent names:
        grand_parents = set()
        for i in parents:
            map(lambda x: grand_parents.add(x), i.get('parents'))
        result.append(parents)
        parent_names = list(grand_parents)
    return result


@adagios_decorator
def hostgroup_detail(request, hostgroup_name):
    """ Status detail for one specific hostgroup  """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['hostgroup_name'] = hostgroup_name
    c['object_type'] = 'hostgroup'
    livestatus = adagios.status.utils.livestatus(request)

    my_hostgroup = pynag.Model.Hostgroup.objects.get_by_shortname(
        hostgroup_name)
    c['my_hostgroup'] = livestatus.get_hostgroups(
        'Filter: name = %s' % hostgroup_name)[0]

    _add_statistics_to_hostgroups([c['my_hostgroup']])
    # Get information about child hostgroups
    subgroups = my_hostgroup.hostgroup_members or ''
    subgroups = subgroups.split(',')
    if subgroups == ['']:
        subgroups = []
    c['hostgroups'] = map(lambda x: livestatus.get_hostgroups('Filter: name = %s' % x)[0], subgroups)
    _add_statistics_to_hostgroups(c['hostgroups'])

    return render_to_response('status_hostgroup.html', c, context_instance=RequestContext(request))


def _add_statistics_to_hostgroups(hostgroups):
    """ Enriches a list of hostgroup dicts with information about subgroups and parentgroups
    """
    # Lets establish a good list of all hostgroups and parentgroups
    all_hostgroups = pynag.Model.Hostgroup.objects.all
    all_subgroups = set()  # all hostgroups that belong in some other hostgroup
    # "subgroup":['master1','master2']
    hostgroup_parentgroups = defaultdict(set)
    hostgroup_childgroups = pynag.Model.ObjectRelations.hostgroup_hostgroups

    for hostgroup, subgroups in hostgroup_childgroups.items():
        map(lambda x: hostgroup_parentgroups[x].add(hostgroup), subgroups)

    for i in hostgroups:
        i['child_hostgroups'] = hostgroup_childgroups[i['name']]
        i['parent_hostgroups'] = hostgroup_parentgroups[i['name']]

    # Extra statistics for our hostgroups
    for hg in hostgroups:
        ok = hg.get('num_services_ok')
        warn = hg.get('num_services_warn')
        crit = hg.get('num_services_crit')
        pending = hg.get('num_services_pending')
        unknown = hg.get('num_services_unknown')
        total = ok + warn + crit + pending + unknown
        hg['total'] = total
        hg['problems'] = warn + crit + unknown
        try:
            total = float(total)
            hg['health'] = float(ok) / total * 100.0
            hg['health'] = float(ok) / total * 100.0
            hg['percent_ok'] = ok / total * 100
            hg['percent_warn'] = warn / total * 100
            hg['percent_crit'] = crit / total * 100
            hg['percent_unknown'] = unknown / total * 100
            hg['percent_pending'] = pending / total * 100
        except ZeroDivisionError:
            pass


@adagios_decorator
def status_servicegroups(request):
    c = {}
    c['messages'] = []
    c['errors'] = []
    servicegroup_name = None
    livestatus = utils.livestatus(request)
    servicegroups = livestatus.get_servicegroups()
    c['servicegroup_name'] = servicegroup_name
    c['request'] = request
    c['servicegroups'] = servicegroups
    return render_to_response('status_servicegroups.html', c, context_instance=RequestContext(request))


@adagios_decorator
def status_hostgroups(request):
    c = {}
    c['messages'] = []
    c['errors'] = []
    hostgroup_name = None
    livestatus = utils.livestatus(request)
    hostgroups = livestatus.get_hostgroups()
    c['hostgroup_name'] = hostgroup_name
    c['request'] = request

    # Lets establish a good list of all hostgroups and parentgroups
    all_hostgroups = pynag.Model.Hostgroup.objects.all
    all_subgroups = set()  # all hostgroups that belong in some other hostgroup
    # "subgroup":['master1','master2']
    hostgroup_parentgroups = defaultdict(set)
    hostgroup_childgroups = pynag.Model.ObjectRelations.hostgroup_hostgroups

    for hostgroup, subgroups in hostgroup_childgroups.items():
        map(lambda x: hostgroup_parentgroups[x].add(hostgroup), subgroups)

    for i in hostgroups:
        i['child_hostgroups'] = hostgroup_childgroups[i['name']]
        i['parent_hostgroups'] = hostgroup_parentgroups[i['name']]

    if hostgroup_name is None:
        # If no hostgroup was specified. Lets only show "root hostgroups"
        c['hosts'] = livestatus.get_hosts()
        my_hostgroups = []
        for i in hostgroups:
            if len(i['parent_hostgroups']) == 0:
                my_hostgroups.append(i)
        my_hostgroups.sort()
        c['hostgroups'] = my_hostgroups

    else:
        my_hostgroup = pynag.Model.Hostgroup.objects.get_by_shortname(
            hostgroup_name)
        subgroups = my_hostgroup.hostgroup_members or ''
        subgroups = subgroups.split(',')
        # Strip out any group that is not a subgroup of hostgroup_name
        right_hostgroups = []
        for group in hostgroups:
            if group.get('name', '') in subgroups:
                right_hostgroups.append(group)
        c['hostgroups'] = right_hostgroups

        # If a hostgroup was specified lets also get all the hosts for it
        c['hosts'] = livestatus.query(
            'GET hosts', 'Filter: host_groups >= %s' % hostgroup_name)
    for host in c['hosts']:
        ok = host.get('num_services_ok')
        warn = host.get('num_services_warn')
        crit = host.get('num_services_crit')
        pending = host.get('num_services_pending')
        unknown = host.get('num_services_unknown')
        total = ok + warn + crit + pending + unknown
        host['total'] = total
        host['problems'] = warn + crit + unknown
        try:
            total = float(total)
            host['health'] = float(ok) / total * 100.0
            host['percent_ok'] = ok / total * 100
            host['percent_warn'] = warn / total * 100
            host['percent_crit'] = crit / total * 100
            host['percent_unknown'] = unknown / total * 100
            host['percent_pending'] = pending / total * 100
        except ZeroDivisionError:
            host['health'] = 'n/a'
    # Extra statistics for our hostgroups
    for hg in c['hostgroups']:
        ok = hg.get('num_services_ok')
        warn = hg.get('num_services_warn')
        crit = hg.get('num_services_crit')
        pending = hg.get('num_services_pending')
        unknown = hg.get('num_services_unknown')
        total = ok + warn + crit + pending + unknown
        hg['total'] = total
        hg['problems'] = warn + crit + unknown
        try:
            total = float(total)
            hg['health'] = float(ok) / total * 100.0
            hg['health'] = float(ok) / total * 100.0
            hg['percent_ok'] = ok / total * 100
            hg['percent_warn'] = warn / total * 100
            hg['percent_crit'] = crit / total * 100
            hg['percent_unknown'] = unknown / total * 100
            hg['percent_pending'] = pending / total * 100
        except ZeroDivisionError:
            pass
    return render_to_response('status_hostgroups.html', c, context_instance=RequestContext(request))


@adagios_decorator
def status_host(request):
    """ Here for backwards compatibility """
    return hosts(request)


@adagios_decorator
def hosts(request):
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['hosts'] = utils.get_hosts(request, **request.GET)
    c['host_name'] = request.GET.get('detail', None)
    return render_to_response('status_host.html', c, context_instance=RequestContext(request))


@adagios_decorator
def problems(request):
    c = {}
    c['messages'] = []
    c['errors'] = []
    search_filter = request.GET.copy()
    if 'state__isnot' not in search_filter and 'state' not in search_filter:
        search_filter['state__isnot'] = '0'
    c['hosts'] = utils.get_hosts(request, **search_filter)
    c['services'] = utils.get_services(request, **search_filter)
    return render_to_response('status_problems.html', c, context_instance=RequestContext(request))



def get_related_objects(object_id):
    my_object = pynag.Model.ObjectDefinition.objects.get_by_id(object_id)
    result = []
    if my_object.register == '0':
        result += my_object.get_effective_children()
        return result
    if my_object.object_type == 'hostgroup':
        result += my_object.get_effective_hostgroups()
        result += my_object.get_effective_hosts()
    if my_object.object_type == 'contactgroup':
        result += my_object.get_effective_contactgroups()
        result += my_object.get_effective_contacts()
    if my_object.object_type == 'host':
        result += my_object.get_effective_network_children()
        result += my_object.get_effective_services()
    return result


def _add_statistics_to_hosts(hosts):
    """ Takes a list of dict hosts, and adds to the list statistics
     Following is an example of attributes added to the dicts:
     num_services_ok
     num_services_warn
     problems (number of problems)
     health (percent of services ok)
     percent_problems
    """
    for host in hosts:
        ok = host.get('num_services_ok')
        warn = host.get('num_services_warn')
        crit = host.get('num_services_crit')
        pending = host.get('num_services_pending')
        unknown = host.get('num_services_unknown')
        total = ok + warn + crit + pending + unknown
        host['total'] = total
        host['problems'] = warn + crit + unknown
        host['num_problems'] = warn + crit + unknown
        try:
            total = float(total)
            host['health'] = float(ok) / total * 100.0
            host['percent_ok'] = ok / total * 100
            host['percent_warn'] = warn / total * 100
            host['percent_crit'] = crit / total * 100
            host['percent_unknown'] = unknown / total * 100
            host['percent_pending'] = pending / total * 100
        except ZeroDivisionError:
            host['health'] = 'n/a'
            host['percent_ok'] = 0
            host['percent_warn'] = 0
            host['percent_crit'] = 0
            host['percent_unknown'] = 0
            host['percent_pending'] = 0


@adagios_decorator
def status_index(request):
    c = adagios.status.utils.get_statistics(request)
    c['services'] = adagios.status.utils.get_services(request, 'unhandled')
    #c['top_alert_producers'] = adagios.status.rest.top_alert_producers(limit=5)

    return render_to_response('status_index.html', c, context_instance=RequestContext(request))


@adagios_decorator
def test_livestatus(request):
    """ This view is a test on top of mk_livestatus which allows you to enter your own queries """
    c = {}
    c['messages'] = []
    c['table'] = table = request.GET.get('table')

    livestatus = adagios.status.utils.livestatus(request)
    if table is not None:
        columns = livestatus.query('GET columns', 'Filter: table = %s' % table)
        c['columns'] = columns

        columns = ""
        limit = request.GET.get('limit')
        run_query = False
        for k, v in request.GET.items():
            if k == "submit":
                run_query = True
            if k.startswith('check_'):
                columns += " " + k[len("check_"):]
        # Any columns checked means we return a query
        query = ['GET %s' % table]
        if len(columns) > 0:
            query.append("Columns: %s" % columns)
        if limit != '' and limit > 0:
            query.append("Limit: %s" % limit)
        if run_query is True:
            c['results'] = livestatus.query(*query)
            c['query'] = livestatus.last_query
            c['header'] = c['results'][0].keys()

    return render_to_response('test_livestatus.html', c, context_instance=RequestContext(request))


def _status_combined(request, optimized=False):
    """ Returns a combined status of network outages, host problems and service problems

    If optimized is True, fewer attributes are loaded it, makes it run faster but with less data
    """
    c = {}
    livestatus = adagios.status.utils.livestatus(request)
    if optimized == True:
        hosts = livestatus.get_hosts(
            'Columns: name state acknowledged downtimes childs parents')
        services = livestatus.get_services(
            'Columns: host_name description state acknowledged downtimes host_state')
    else:
        hosts = livestatus.get_hosts()
        services = livestatus.get_services()
    hosts_that_are_down = []
    hostnames_that_are_down = []
    service_status = [0, 0, 0, 0]
    host_status = [0, 0, 0, 0]
    parents = []
    for host in hosts:
        host_status[host["state"]] += 1
        if len(host['childs']) > 0:
            parents.append(host)
        if host['state'] != 0 and host['acknowledged'] == 0 and host['downtimes'] == []:
            hostnames_that_are_down.append(host['name'])
            hosts_that_are_down.append(host)

    network_problems = []
    host_problems = []
    service_problems = []

    # Do nothing if host parent is also down.
    for host in hosts_that_are_down:
        for i in host['parents']:
            if i in hostnames_that_are_down:
                break
        else:
            if len(host['childs']) == 0:
                host_problems.append(host)
            else:
                network_problems.append(host)
    for service in services:
        service_status[service["state"]] += 1
        if service['state'] != 0 and service['acknowledged'] == 0 and len(service['downtimes']) == 0 and service['host_state'] == 0:
            service_problems.append(service)
    c['network_problems'] = network_problems
    c['host_problems'] = host_problems
    c['service_problems'] = service_problems
    c['hosts'] = hosts
    c['services'] = services
    c['parents'] = parents
    service_totals = float(sum(service_status))
    host_totals = float(sum(host_status))
    if service_totals == 0:
        c['service_status'] = 0
    else:
        c['service_status'] = map(
            lambda x: 100 * x / service_totals, service_status)
    if host_totals == 0:
        c['host_status'] = 0
    else:
        c['host_status'] = map(lambda x: 100 * x / host_totals, host_status)
    #l = pynag.Parsers.LogFiles(maincfg=adagios.settings.nagios_config)
    #c['log'] = reversed(l.get_state_history())
    return c


@adagios_decorator
def status_problems(request):
    return dashboard(request)


@adagios_decorator
def dashboard(request):

    # Get statistics
    c = adagios.status.utils.get_statistics(request)

    c['messages'] = []
    c['errors'] = []

    c['host_problems'] = utils.get_hosts(request, state='1', unhandled='', **request.GET)

    # Service problems
    c['service_problems'] = utils.get_services(request, host_state="0", unhandled='', **request.GET)

    # Sort problems by state and last_check as secondary sort field
    c['service_problems'].sort(
        reverse=True, cmp=lambda a, b: cmp(a['last_check'], b['last_check']))
    c['service_problems'].sort(
        reverse=True, cmp=lambda a, b: cmp(a['state'], b['state']))
    return render_to_response('status_dashboard.html', c, context_instance=RequestContext(request))


@adagios_decorator
def state_history(request):
    c = {}
    c['messages'] = []
    c['errors'] = []

    livestatus = adagios.status.utils.livestatus(request)
    start_time = request.GET.get('start_time', None)
    end_time = request.GET.get('end_time', None)
    if end_time is None:
        end_time = time.time()
    end_time = int(float(end_time))
    if start_time is None:
        seconds_in_a_day = 60 * 60 * 24
        seconds_today = end_time % seconds_in_a_day  # midnight of today
        start_time = end_time - seconds_today
    start_time = int(start_time)

    l = pynag.Parsers.LogFiles(maincfg=adagios.settings.nagios_config)
    c['log'] = log = l.get_state_history(start_time=start_time, end_time=end_time,strict=False)
    total_duration = end_time - start_time
    c['total_duration'] = total_duration
    css_hint = {}
    css_hint[0] = 'success'
    css_hint[1] = 'warning'
    css_hint[2] = 'danger'
    css_hint[3] = 'info'
    last_item = None

    services = {}
    search_filter = request.GET.copy()
    search_filter.pop('start_time', None)
    search_filter.pop('end_time', None)
    search_filter.pop('start_time_picker', None)
    search_filter.pop('start_hours', None)
    search_filter.pop('end_time_picker', None)
    search_filter.pop('end_hours', None)
    search_filter.pop('submit', None)

    log = pynag.Utils.grep(log, **search_filter)
    for i in log:
        short_name = "%s/%s" % (i['host_name'], i['service_description'])
        if short_name not in services:
            s = {}
            s['host_name'] = i['host_name']
            s['service_description'] = i['service_description']
            s['log'] = []
            s['worst_logfile_state'] = 0
            #s['log'] = [{'time':start_time,'state':3, 'plugin_output':'Unknown value here'}]
            services[short_name] = s

        services[short_name]['log'].append(i)
        services[short_name]['worst_logfile_state'] = max(
            services[short_name]['worst_logfile_state'], i['state'])
    for service in services.values():
        last_item = None
        service['sla'] = float(0)
        service['num_problems'] = 0
        service['duration'] = 0
        for i in service['log']:
            i['bootstrap_status'] = css_hint[i['state']]
            if i['time'] < start_time:
                i['time'] = start_time
            if last_item is not None:
                last_item['end_time'] = i['time']
                #last_item['time'] = max(last_item['time'], start_time)
                last_item['duration'] = duration = last_item[
                    'end_time'] - last_item['time']
                last_item['duration_percent'] = 100 * float(
                    duration) / total_duration
                service['duration'] += last_item['duration_percent']
                if last_item['state'] == 0:
                    service['sla'] += last_item['duration_percent']
                else:
                    service['num_problems'] += 1
            last_item = i
        if not last_item is None:
            last_item['end_time'] = end_time
            last_item['duration'] = duration = last_item[
                'end_time'] - last_item['time']
            last_item['duration_percent'] = 100 * duration / total_duration
            service['duration'] += last_item['duration_percent']
            if last_item['state'] == 0:
                service['sla'] += last_item['duration_percent']
            else:
                service['num_problems'] += 1
    c['services'] = services
    c['start_time'] = start_time
    c['end_time'] = end_time
    return render_to_response('state_history.html', c, context_instance=RequestContext(request))


def _status_log(request):
    """ Helper function to any status view that requires log access """
    c = {}
    c['messages'] = []
    c['errors'] = []
    start_time = request.GET.get('start_time', '')
    end_time = request.GET.get('end_time', '')
    host_name = request.GET.get('host_name', '')
    service_description = request.GET.get('service_description', '')
    limit = request.GET.get('limit', '')

    if end_time == '':
        end_time = None
    else:
        end_time = float(end_time)

    if start_time == '':
        now = time.time()
        seconds_in_a_day = 60 * 60 * 24
        seconds_today = now % seconds_in_a_day  # midnight of today
        start_time = now - seconds_today
    else:
        start_time = float(start_time)

    if limit == '':
        limit = 2000
    else:
        limit = int(limit)

    # Any querystring parameters we will treat as a search string to get_log_entries, but we need to massage them
    # a little bit first
    kwargs = {}
    for k, v in request.GET.items():
        if k == 'search':
            k = 'search'
        elif k in (
            'start_time', 'end_time', 'start_time_picker', 'end_time_picker', 'limit',
            'start_hours', 'end_hours'):
            continue
        elif v is None or len(v) == 0:
            continue
        k = str(k)
        v = str(v)
        kwargs[k] = v
    l = pynag.Parsers.LogFiles(maincfg=adagios.settings.nagios_config)
    c['log'] = l.get_log_entries(
        start_time=start_time, end_time=end_time, **kwargs)[-limit:]
    c['log'].reverse()
    c['logs'] = {'all': []}
    for line in c['log']:
        if line['class_name'] not in c['logs'].keys():
            c['logs'][line['class_name']] = []
        c['logs'][line['class_name']].append(line)
        c['logs']['all'].append(line)
    c['start_time'] = start_time
    c['end_time'] = end_time
    return c


@adagios_decorator
def log(request):
    c = _status_log(request)
    c['request'] = request
    c['log'].reverse()
    return render_to_response('status_log.html', c, context_instance=RequestContext(request))


@adagios_decorator
def comment_list(request):
    """ Display a list of all comments """
    c = {}
    c['messages'] = []
    c['errors'] = []
    l = adagios.status.utils.livestatus(request)
    args = pynag.Utils.grep_to_livestatus(**request.GET)
    c['comments'] = l.query('GET comments', *args)
    return render_to_response('status_comments.html', c, context_instance=RequestContext(request))


@adagios_decorator
def downtime_list(request):
    """ Display a list of all comments """
    c = {}
    c['messages'] = []
    c['errors'] = []
    l = adagios.status.utils.livestatus(request)
    args = pynag.Utils.grep_to_livestatus(**request.GET)
    c['downtimes'] = l.query('GET downtimes', *args)
    return render_to_response('status_downtimes.html', c, context_instance=RequestContext(request))

@adagios_decorator
def acknowledgement_list(request):
    """ Display a list of all comments """
    c = {}
    c['messages'] = []
    c['errors'] = []
    l = adagios.status.utils.livestatus(request)
    args = pynag.Utils.grep_to_livestatus(**request.GET)
    c['acknowledgements'] = l.query('GET comments', 'Filter: entry_type = 4', *args)
    return render_to_response('status_acknowledgements.html', c, context_instance=RequestContext(request))


@adagios_decorator
def perfdata(request):
    """ Display a list of perfdata
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    fields = "host_name description perf_data state host_state scheduled_downtime_depth host_scheduled_downtime_depth host_acknowledged acknowledged downtimes host_downtimes".split()
    perfdata = utils.get_services(request, fields=fields, **request.GET)
    for i in perfdata:
        metrics = pynag.Utils.PerfData(i['perf_data']).metrics
        metrics = filter(lambda x: x.is_valid(), metrics)
        i['metrics'] = metrics

    c['perfdata'] = perfdata
    return render_to_response('status_perfdata.html', c, context_instance=RequestContext(request))


@adagios_decorator
def contact_list(request):
    """ Display a list of active contacts
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['contacts'] = adagios.status.utils.get_contacts(request, **request.GET)
    return render_to_response('status_contacts.html', c, context_instance=RequestContext(request))


@adagios_decorator
def contact_detail(request, contact_name):
    """ Detailed information for one specific contact
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['contact_name'] = contact_name
    l = adagios.status.utils.livestatus(request)
    backend = request.GET.get('backend', None)

    # Fetch contact and basic information
    try:
        contact = l.get_contact(contact_name, backend)
        c['contact'] = contact
    except IndexError:
        raise Exception("Contact named '%s' was not found." % contact_name)

    # Active comments
    c['comments'] = l.query(
        'GET comments', 'Filter: comment ~ %s' % contact_name,)
    for i in c['comments']:
        if i.get('type') == 1:
            i['state'] = i['host_state']
        else:
            i['state'] = i['service_state']

    # Services this contact can see
    c['services'] = l.query(
        'GET services', "Filter: contacts >= %s" % contact_name)

    # Activity log
    c['log'] = pynag.Parsers.LogFiles(
        maincfg=adagios.settings.nagios_config).get_log_entries(search=str(contact_name))

    # Contact groups
    c['groups'] = l.query(
        'GET contactgroups', 'Filter: members >= %s' % contact_name)

    # Git audit logs
    nagiosdir = dirname(adagios.settings.nagios_config or pynag.Model.config.guess_cfg_file())
    git = pynag.Utils.GitRepo(directory=nagiosdir)
    c['gitlog'] = git.log(author_name=contact_name)
    return render_to_response('status_contact.html', c, context_instance=RequestContext(request))


@adagios_decorator
def map_view(request):
    c = {}
    livestatus = adagios.status.utils.livestatus(request)
    c['hosts'] = livestatus.get_hosts()
    c['map_center'] = adagios.settings.map_center
    c['map_zoom'] = adagios.settings.map_zoom

    return render_to_response('status_map.html', c, context_instance=RequestContext(request))


@adagios_decorator
def servicegroup_detail(request, servicegroup_name):
    """ Detailed information for one specific servicegroup """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['servicegroup_name'] = servicegroup_name

    search_conditions = request.GET.copy()
    search_conditions.pop('servicegroup_name')

    c['services'] = adagios.status.utils.get_services(request, groups__has_field=servicegroup_name, **search_conditions)
    return render_to_response('status_servicegroup.html', c, context_instance=RequestContext(request))

@adagios_decorator
def contactgroups(request):
    """ Display a list of active contacts
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    l = adagios.status.utils.livestatus(request)
    c['contactgroups'] = l.get_contactgroups(**request.GET)
    return render_to_response('status_contactgroups.html', c, context_instance=RequestContext(request))


@adagios_decorator
def contactgroup_detail(request, contactgroup_name):
    """ Detailed information for one specific contactgroup
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    c['contactgroup_name'] = contactgroup_name
    l = adagios.status.utils.livestatus(request)

    # Fetch contact and basic information
    result = l.query("GET contactgroups", "Filter: name = %s" %
                     contactgroup_name)
    if result == []:
        c['errors'].append(
            "Contactgroup named '%s' was not found." % contactgroup_name)
    else:
        contactgroup = result[0]
        c['contactgroup'] = contactgroup

    # Services this contact can see
    c['services'] = l.query(
        'GET services', "Filter: contact_groups >= %s" % contactgroup_name)

    # Services this contact can see
    c['hosts'] = l.query(
        'GET hosts', "Filter: contact_groups >= %s" % contactgroup_name)

    # Contact groups
    #c['contacts'] = l.query('GET contacts', 'Filter: contactgroup_ >= %s' % contact_name)

    return render_to_response('status_contactgroup.html', c, context_instance=RequestContext(request))



@adagios_decorator
def perfdata2(request):
    """ Just a test method, feel free to remove it
    """
    c = {}
    c['messages'] = []
    c['errors'] = []
    columns = 'Columns: host_name description perf_data state host_state'
    l = adagios.status.utils.livestatus(request)

    # User can specify from querystring a filter of which services to fetch
    # we convert querystring into livestatus filters.
    # User can also specify specific metrics to watch, so we extract from
    # querystring as well
    querystring = request.GET.copy()
    interesting_metrics = querystring.pop('metrics', [''])[0].strip(',')
    arguments = pynag.Utils.grep_to_livestatus(**querystring)
    if not arguments:
        services = []
    else:
        services = l.query('GET services', columns, *arguments)

    # If no metrics= was specified on querystring, we take the string
    # from first service in our search result
    if not interesting_metrics and services:
        metric_set = set()
        for i in services:
            perfdata = pynag.Utils.PerfData(i.get('perf_data', ''))
            map(lambda x: metric_set.add(x.label), perfdata.metrics)
        interesting_metrics = sorted(list(metric_set))
    else:
        interesting_metrics = interesting_metrics.split(',')

    # Iterate through all the services and parse perfdata
    for service in services:
        perfdata = pynag.Utils.PerfData(service['perf_data'])
        null_metric = pynag.Utils.PerfDataMetric()
        metrics = map(lambda x: perfdata.get_perfdatametric(
            x) or null_metric, interesting_metrics)
        #metrics = filter(lambda x: x.is_valid(), metrics)
        service['metrics'] = metrics

    c['metrics'] = interesting_metrics
    c['services'] = services

    return render_to_response('status_perfdata2.html', c, context_instance=RequestContext(request))


def acknowledge(request):
    """ Acknowledge

    """
    if request.method != 'POST':
        raise Exception("Only use POST to this url")

    sticky = request.POST.get('sticky', 1)
    persistent = request.POST.get('persistent', 0)
    author = request.META.get('REMOTE_USER', 'anonymous')
    comment = request.POST.get('comment', 'acknowledged by Adagios')

    hostlist = request.POST.getlist('host', [])
    servicelist = request.POST.getlist('service', [])


@adagios_decorator
def status_hostgroup(request, hostgroup_name):
    """ Here for backwards compatibility """
    return hostgroup_detail(request, hostgroup_name=hostgroup_name)


@adagios_decorator
def status_detail(request):
    """ Here for backwards compatibility """
    return detail(request)

@adagios_decorator
def backends(request):
    """ Display a list of available backends and their connection status """
    livestatus = adagios.status.utils.livestatus(request)
    backends = livestatus.get_backends()
    for i, v in backends.items():
        v.test(raise_error=False)
    return render_to_response('status_backends.html', locals(), context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = urls
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *

from django.conf import settings

from django.views.static import serve

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    url(r'^$', 'adagios.views.index', name="home"),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}, name="media"),
    url(r'^403', 'adagios.views.http_403'),
    url(r'^objectbrowser', include('adagios.objectbrowser.urls')),
    url(r'^misc', include('adagios.misc.urls')),
    url(r'^pnp', include('adagios.pnp.urls')),
    url(r'^media(?P<path>.*)$',         serve, {'document_root': settings.MEDIA_ROOT }),
    url(r'^rest', include('adagios.rest.urls')),
    url(r'^contrib', include('adagios.contrib.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    
    # Internationalization
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog'),
)

########NEW FILE########
__FILENAME__ = userdata
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Matthieu Caneill <matthieu.caneill@savoirfairelinux.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import json
import collections

import settings

class User(object):
    """ Handles authentified users, provides preferences management. """
    def __init__(self, request, autosave=False):
        """ Instantiates one user's preferences.

        Args:
          request (Request): The incoming Django request.

        Kwargs:
          autosave (bool): if True, preferences are automatically saved.
        """
        self._request = request
        self._autosave = autosave
        try:
            self._username = request.META.get('REMOTE_USER', 'anonymous')
        except Exception:
            self._username = 'anonymous'
        self._conffile = self._get_prefs_location()
        self._check_path(self._conffile)
        # sets the preferences as attributes:
        for k, v in self._get_conf().iteritems():
            self.__dict__[k] = v

    def _check_path(self, path):
        """ Checks the userdata folder, try to create it if it doesn't
        exist."""
        folder = os.path.dirname(path)
        # does the folder exist?
        if not os.path.isdir(folder):
            try:
                os.makedirs(folder)
            except:
                raise Exception("Folder %s can't be created. Be sure Adagios "
                                "has write access on its parent." % folder)
    
    def _get_prefs_location(self):
        """ Returns the location of the preferences file of the
        specified user. """
        try:
            user_prefs_path = settings.USER_PREFS_PATH
        except:
            raise Exception('You must define USER_PREFS_PATH in settings.py')

        return os.path.join(user_prefs_path, self._username + '.json')

    def _get_default_conf(self):
        try:
            d = settings.PREFS_DEFAULT
        except:
            d = dict()
        return d
    
    def _get_conf(self):
        """ Returns the json preferences for the specified user. """
        try:
            with open(self._conffile) as f:
                conf = json.loads(f.read())
        except IOError:
            conf = self._get_default_conf()
        except ValueError:
            conf = self._get_default_conf()
        return conf
    
    def __getattr__(self, name):
        """ Provides None as a default value. """
        if name not in self.__dict__.keys():
            return None
        return self.__dict__[name]

    def __setattr__(self, name, value):
        """ Saves the preferences if autosave is set. """
        self.__dict__[name] = value
        if self._autosave and not name.startswith('_'):
            self.save()

    def set_pref(self, name, value):
        """ Explicitly sets a user preference. """
        self.__dict__[name] = value

    def to_dict(self):
        d = {}
        for k in filter(lambda x: not(x.startswith('_')), self.__dict__.keys()):
            d[k] = self.__dict__[k]
        return d
    
    def save(self):
        """ Saves  the preferences in JSON format. """
        d = self.to_dict()
        try:
            with open(self._conffile, 'w') as f:
                f.write(json.dumps(d))
        except IOError:
            raise Exception("Couldn't write settings into file %s. Be sure to "
                            "have write permissions on the parent folder."
                            % self._conffile)
        self.trigger_hooks()

    def trigger_hooks(self):
        """ Triggers the hooks when preferences are changed. """
        # language preference
        from django.utils import translation
        try:
            self._request.session['django_language'] = self.language
            # newer versions of Django: s/django_language/_language
            translation.activate(self.language)
        except Exception as e:
            pass

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import multiprocessing
import adagios.status.utils
import time
import adagios
import pynag.Model
import adagios.exceptions
import adagios.settings
import os
import pynag.Utils.misc

from django.utils.translation import ugettext as _


def wait(object_type, WaitObject, WaitCondition, WaitTrigger, **kwargs):
    livestatus = adagios.status.utils.livestatus(None)
    livestatus.get(object_type, WaitObject=WaitObject, WaitCondition=WaitCondition, WaitTrigger=WaitTrigger, **kwargs)
    print WaitObject

def wait_for_objects(object_type, object_list, condition=None, trigger='check'):
    if not condition:
        condition = "last_check > %s" % int(0)
    callback = lambda x: wait(object_type, WaitObject=x, WaitCondition=condition, WaitTrigger=trigger)
    for WaitObject in object_list:
        callback(WaitObject)

def wait_for_service(host_name, service_description, condition='last_check >= 0', trigger='check'):
    livestatus = adagios.status.utils.livestatus(None)
    waitobject = "%s;%s" % (host_name, service_description)
    livestatus.get_services(
        host_name=host_name,
        service_description=service_description,
        WaitCondition=condition,
        WaitObject=waitobject
    )

from multiprocessing.pool import ThreadPool


class Task(object):
    def __init__(self, num_processes=5):
        self._tasks = []
        adagios.tasks.append(self)
        self._pool = ThreadPool(processes=num_processes)

    def add(self, function, *args, **kwargs):
        print "Adding Task:", locals()
        result = self._pool.apply_async(function, args, kwargs)
        self._tasks.append(result)
        #print result.get()

    def status(self):
        all_tasks = self._tasks
        for i in all_tasks:
            print i.ready()
        completed_tasks = filter(lambda x: x.ready(), all_tasks)
        return "{done}/{total} done.".format(done=len(completed_tasks), total=len(all_tasks))

    def get_id(self):
        return hash(self)

    def ready(self):
        """ Returns True if all the Tasks in this class have finished running. """
        return max(map(lambda x: x.ready(), self._tasks))


def update_eventhandlers(request):
    """ Iterates through all pynag eventhandler and informs them who might be making a change
    """
    remote_user = request.META.get('REMOTE_USER', 'anonymous')
    for i in pynag.Model.eventhandlers:
        i.modified_by = remote_user

    # if okconfig is installed, make sure okconfig is notified of git
    # settings
    try:
        from pynag.Utils import GitRepo
        import okconfig
        okconfig.git = GitRepo(directory=os.path.dirname(
            adagios.settings.nagios_config), auto_init=False, author_name=remote_user)
    except Exception:
        pass


def get_available_themes():
    """ Returns a tuple with the name of themes that are available in media/theme directory """
    theme_dir = os.path.join(adagios.settings.MEDIA_ROOT, adagios.settings.THEMES_FOLDER)

    result = []
    for root, dirs, files in os.walk(theme_dir):
        if adagios.settings.THEME_ENTRY_POINT in files:
            result.append(os.path.basename(root))

    return result


def reload_config_file(adagios_configfile=None):
    """ Reloads adagios.conf and populates updates adagios.settings accordingly.

    Args:
        adagios_configfile: Full path to adagios.conf. If None then use settings.adagios_configfile
    """
    if not adagios_configfile:
        adagios_configfile = adagios.settings.adagios_configfile

    # Using execfile might not be optimal outside strict settings.py usage, but
    # lets do things exactly like settings.py does it.
    execfile(adagios_configfile)
    config_values = locals()
    adagios.settings.__dict__.update(config_values)


class FakeAdagiosEnvironment(pynag.Utils.misc.FakeNagiosEnvironment):
    _adagios_settings_copy = None

    def __init__(self, *args, **kwargs):
        super(FakeAdagiosEnvironment, self).__init__(*args, **kwargs)

    def update_adagios_global_variables(self):
        """ Updates common adagios.settings to point to a temp directory.

         If you are are doing unit tests which require specific changes, feel free to update
         adagios.settings manually after calling this method.
        """
        self._adagios_settings_copy = adagios.settings.__dict__.copy()
        adagios.settings.adagios_configfile = self.adagios_config_file
        adagios.settings.USER_PREFS_PATH = self.adagios_config_dir + "/userdata"
        adagios.settings.nagios_config = self.cfg_file
        adagios.settings.livestatus_path = self.livestatus_socket_path
        reload_config_file(self.adagios_config_file)

    def restore_adagios_global_variables(self):
        """ Restores adagios.settings so it looks like before update_adagios_global_variables() was called
        """
        adagios.settings.__dict__.clear()
        adagios.settings.__dict__.update(self._adagios_settings_copy)

    def create_minimal_environment(self):
        """ Behaves like FakeNagiosEnvironment except also creates adagios config directory """

        super(FakeAdagiosEnvironment, self).create_minimal_environment()
        self.adagios_config_dir = os.path.join(self.tempdir, 'adagios')
        self.adagios_config_file = os.path.join(self.adagios_config_dir, 'adagios.conf')

        os.makedirs(self.adagios_config_dir)
        with open(self.adagios_config_file, 'w') as f:
            f.write('')

    def terminate(self):
        """ Behaves like FakeNagiosEnvironment except also restores adagios.settings module """
        if self._adagios_settings_copy:
            self.restore_adagios_global_variables()
        super(FakeAdagiosEnvironment, self).terminate()


########NEW FILE########
__FILENAME__ = views
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpResponse
import traceback
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext, loader
from django import template
from django.utils.translation import ugettext as _
import time
import logging
import adagios.settings
import adagios.utils
from adagios.exceptions import AccessDenied


def adagios_decorator(view_func):
    """ This is a python decorator intented for all views in the status module.

     It catches all unhandled exceptions and displays them on a generic web page.

     Kind of what the django exception page does when debug mode is on.
    """
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        try:
            if request.method == 'POST':
                adagios.utils.update_eventhandlers(request)
            result = view_func(request, *args, **kwargs)
            end_time = time.time()
            time_now = time.ctime()
            duration = end_time - start_time
            return result
        except Exception, e:
            c = {}
            c['exception'] = str(e)
            c['exception_type'] = str(type(e).__name__)
            c['traceback'] = traceback.format_exc()
            return error_page(request, context=c)
    wrapper.__name__ = view_func.__name__
    wrapper.__module__ = view_func.__module__
    return wrapper


def error_page(request, context=None):
    if context is None:
        context = {}
        context['errors'] = []
        context['errors'].append('Error occured, but no error messages provided, what happened?')
    if request.META.get('CONTENT_TYPE') == 'application/json':
        context.pop('request', None)
        content = str(context)
        response = HttpResponse(content=content, content_type='application/json')
    else:
        response = render_to_response('status_error.html', context, context_instance=RequestContext(request))
    response.status_code = 500
    return response


def index(request):
    """ This view is our frontpage """
    # If status view is enabled, redirect to frontpage of the status page:
    if adagios.settings.enable_status_view:
        return redirect('adagios.status.views.status_index', permanent=True)
    else:
        return redirect('objectbrowser', permanent=True)


def http_403(request, exception=None):
    context = {}
    context['exception'] = exception
    if request.META.get('CONTENT_TYPE') == 'application/json':
        c = {}
        c['exception_type'] = exception.__class__
        c['message'] = str(exception.message)
        c['access_required'] = exception.access_required
        response = HttpResponse(content=str(c), content_type='application/json')
    else:
        response = render_to_response('403.html', context, context_instance=RequestContext(request))
    response.status_code = 403
    return response

########NEW FILE########
__FILENAME__ = wsgi
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'adagios.settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = static_businessprocess
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Adagios is a web based Nagios configuration interface
#
# Copyright (C) 2014, Pall Sigurdsson <palli@opensource.is>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
static_businessprocesses .. This script loads a business process and staticly writes html view for it
"""

#source_template = "/usr/lib/python2.6/site-packages/adagios/status/templates/business_process_view.html"
source_template = "/etc/adagios/pages.d/bi_process.html"
destination_directory = "/var/www/iceland.adagios.org"
pnp_parameters = "&graph_width=350&graph_height=30"

import os
os.environ['DJANGO_SETTINGS_MODULE'] = "adagios.settings"
import simplejson as json

from django.shortcuts import render
from django import template
from django.test.client import Client
from optparse import OptionParser


import adagios.bi
import django.http
from adagios.pnp.functions import run_pnp


# Start by parsing some arguments
parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")

parser.add_option('--all', help="Parse all business processes", dest="all", action="store_true", default=False)
parser.add_option('--graphs', help="", dest="graphs", action="store_true", default=False)
parser.add_option('--destination', help="destination to write static html into", dest="destination", default=destination_directory)
parser.add_option('--source-template', help="Source template used to render business processes", dest="source", default=source_template)
parser.add_option('--verbose', help="verbose output", dest="verbose", action="store_true", default=False)


(options, args) = parser.parse_args()


def verbose(message):
    if options.verbose:
        print message


def businessprocess_to_html(process_name, process_type='businessprocess'):
    bp = adagios.bi.get_business_process(process_name=process_name, process_type=process_type)
    verbose("Rendering business process %s" % bp.name)
    c = {}
    c['bp'] = bp
    c['csrf_token'] = ''
    c['graphs_url'] = "graphs.json"
    c['static'] = True

    directory = "%s/%s" % (options.destination, bp.name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    if options.graphs:
        graphs = bi_graphs_to_json(process_name, process_type)
        for i in graphs:
            url = i.get('image_url')
            client = Client()
            verbose("Saving image %s" % url)
            image = client.get("/pnp/image?%s&%s" % (url, pnp_parameters)).content
            graph_filename = "%s/%s.png" % (directory, url)
            open(graph_filename, 'w').write(image)
        graph_json_file = "%s/graphs.json" % (directory)
        for i in graphs:
            i['image_url'] = i['image_url'] + '.png'
        graph_json = json.dumps(graphs, indent=4)
        open(graph_json_file, 'w').write(graph_json)

    content = open(options.source, 'r').read()
    t = template.Template(content)
    c = template.Context(c)
    
    html = t.render(c)
    destination_file = "%s/index.html" % directory
    open(destination_file, 'w').write(html.encode('utf-8'))


def bi_graphs_to_json(process_name, process_type='businessprocess'):
    c = {}
    c['messages'] = []
    c['errors'] = []
    bp = adagios.bi.get_business_process(process_name=process_name, process_type=process_type)

    graphs = []
    if not bp.graphs:
        return []
    for graph in bp.graphs or []:
        if graph.get('graph_type') == 'pnp':
            host_name = graph.get('host_name')
            service_description = graph.get('service_description')
            metric_name = graph.get('metric_name')
            pnp_result = run_pnp('json', host=graph.get('host_name'), srv=graph.get('service_description'))
            json_data = json.loads(pnp_result)
            for i in json_data:
                if i.get('ds_name') == graph.get('metric_name'):
                    notes = graph.get('notes')
                    last_value = bp.get_pnp_last_value(host_name, service_description, metric_name)
                    i['last_value'] = last_value
                    i['notes'] = notes
                    graphs.append(i)
    return graphs


if options.all:
    processlist = adagios.bi.get_all_process_names()
else:
    processlist = args

if not processlist:
    parser.error("Either provide business process name or specify --all")

for i in processlist:
    print "doing ", i
    businessprocess_to_html(i)

########NEW FILE########
