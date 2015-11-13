__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = simple
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
__FILENAME__ = finders
from . import storage
from django.contrib.staticfiles import finders


class NamespacedAngularAppDirectoriesFinder(finders.AppDirectoriesFinder):
    """
    A static files finder that looks in the app directory of each app.
    """
    storage_class = storage.NamespacedAngularAppStorage


class NamespacedE2ETestAppDirectoriesFinder(finders.AppDirectoriesFinder):
    """
    A static files finder that looks in the tests/e2e directory of each app.
    """
    storage_class = storage.NamespacedE2ETestAppStorage


class NamespacedLibTestAppDirectoriesFinder(finders.AppDirectoriesFinder):
    """
    A static files finder that looks in the tests/lib directory of each app.
    """
    storage_class = storage.NamespacedLibTestAppStorage
########NEW FILE########
__FILENAME__ = makeangularsite
import os

from djangular import utils
from django.core.management import base, templates


class Command(utils.SiteAndPathUtils, templates.TemplateCommand):
    help = ("Augments a Django site directory with needed Djangular files "
            "for the given site name in the current directory.")
    args = '[site]'
    option_list = base.BaseCommand.option_list

    def handle(self, site_name=None, target=None, *args, **options):
        if site_name is None:
            site_name = self.get_default_site_app()

        # Include djangular_root variable in the template and setup the rest as if the other options existed.
        options.update({
            'djangular_root': self.get_djangular_root(),
            'template': os.path.join(self.get_djangular_root(), 'config', 'angularsite_template'),
            'extensions': [],
            'files': []
        })

        # Override target with site_name, so that we won't get directory already exists errors.
        super(Command, self).handle('site', name=site_name, target=site_name, **options)

        template_path = os.path.join(site_name, 'templates')
        self.stdout.write(
            'Update the Karma config templates in %s to add any additional JS dependencies.' % template_path)


########NEW FILE########
__FILENAME__ = runtestserver
from django.core import management as mgmt
from django.core.management.commands import runserver

class Command(mgmt.base.BaseCommand):
    help = "Starts a lightweight server for end-to-end testing."
    args = runserver.Command.args

    def handle(self, addrport=runserver.DEFAULT_PORT, *args, **options):
        # Hack on the test directories so that the e2e tests can be run.
        from django.conf import settings
        # TODO: Figure out why this prints twice...
        self.stdout.write("Patching settings to include end-to-end test directories...\n")
        new_finders = ['djangular.finders.NamespacedE2ETestAppDirectoriesFinder',
                       'djangular.finders.NamespacedLibTestAppDirectoriesFinder']
        new_finders.extend(settings.STATICFILES_FINDERS)
        settings.STATICFILES_FINDERS = tuple(new_finders)

        # Add port to arguments
        new_args = [addrport]
        new_args.extend(args)
        mgmt.call_command('runserver', *new_args, **options)

########NEW FILE########
__FILENAME__ = startangularapp
import os

from django.core import management as mgmt
from django.core.management.commands import startapp
from djangular import utils


class Command(utils.SiteAndPathUtils, mgmt.base.BaseCommand):
    help = ("Creates a Djangular app directory structure for the given app "
            "name in the current directory or optionally in the given directory.")
    args = startapp.Command.args
    requires_model_validation = False

    def handle(self, app_name=None, target=None, **options):
        # Override the options to setup the template command.
        options.update({
            'template': os.path.join(self.get_djangular_root(), 'config', 'angularapp_template'),
            'extensions': ['.py', '.js'],  # Include JS Files for parsing.
            'files': ['index.html']
        })

        mgmt.call_command('startapp', app_name, target, **options)

########NEW FILE########
__FILENAME__ = testjs
import os
import re
import subprocess
import tempfile

from django import template
from django.core import management as mgmt
from django.conf import settings
from djangular import utils
from optparse import make_option


class Command(utils.SiteAndPathUtils, mgmt.base.BaseCommand):
    """
    A base command that calls Karma from the command line, passing the options and arguments directly.
    """
    help = ("Runs the JS Karma tests for the given test type and apps.  If no apps are specified, tests will be "
            "run for every app in INSTALLED_APPS.")
    args = '[type] [appname ...]'
    option_list = mgmt.base.BaseCommand.option_list + (
        make_option('--greedy', action='store_true',
                    help="Run every app in the project, ignoring passed in apps and the INSTALLED_APPS setting.  "
                         "Note that running e2e tests for non-installed apps will most likely cause them to fail."),
    )
    requires_model_validation = False

    default_test_type = 'unit'
    template_dir = 'templates'

    def get_existing_apps_from(self, app_list):
        """
        Retrieves the apps from the given app_list that exist on the file system.
        """
        project_root = self.get_project_root()
        existing_paths = []

        for app_name in app_list:
            app_name_components = app_name.split('.')
            app_path = os.path.join(*app_name_components)
            full_app_path = os.path.join(project_root, app_path)
            if os.path.exists(full_app_path):
                existing_paths.append(app_path)

        if self.verbosity >= 2:
            self.stdout.write("Running %s tests from apps: %s" % (self.test_type, ', '.join(existing_paths)))
        return existing_paths

    def usage(self, subcommand):
        # Default message when templates are missing
        types_message = mgmt.color_style().ERROR(
            "NOTE: You will need to run the following command to create the needed Karma config templates before "
            "running this command.\n"
            "  python manage.py makeangularsite"
        )

        # Check and see if templates exist
        template_path = os.path.join(self.get_default_site_app(), self.template_dir)
        if os.path.exists(template_path) and os.path.isdir(template_path):
            filename_matches = [re.match(r'^karma-(.*).conf.js$', filename)
                                for filename in os.listdir(template_path)]
            template_types = [match.group(1) for match in filename_matches if match]

            if len(template_types):
                types_message = '\n'.join(["The following types of Karma tests are available:"] +
                                          ["  %s%s" % (test_type, '*' if test_type == self.default_test_type else '')
                                           for test_type in template_types] +
                                          ["", "If no apps are listed, tests from all the INSTALLED_APPS will be run."])

        # Append template message to standard usage
        parent_usage = super(Command, self).usage(subcommand)
        return "%s\n\n%s" % (parent_usage, types_message)

    def handle(self, test_type=None, *args, **options):
        self.verbosity = int(options.get('verbosity'))
        self.test_type = test_type or self.default_test_type

        # Determine template location
        karma_config_template = \
            os.path.join(self.get_default_site_app(), self.template_dir, 'karma-%s.conf.js' % self.test_type)
        if self.verbosity >= 2:
            self.stdout.write("Using karma template: %s" % karma_config_template)

        if not os.path.exists(karma_config_template):
            raise IOError("Karma template %s was not found." % karma_config_template)

        # Establish the Context for the template
        if options.get('greedy', False):
            app_paths = ['**']
            if self.verbosity >= 2:
                self.stdout.write("Running %s tests for all applications in the project." % self.test_type)
        elif len(args):
            app_paths = self.get_existing_apps_from(set(args) & set(settings.INSTALLED_APPS))
        else:
            app_paths = self.get_existing_apps_from(settings.INSTALLED_APPS)

        context = template.Context(dict(options, **{
            'app_paths': app_paths,
            'djangular_root': self.get_djangular_root()
        }), autoescape=False)

        # Establish the template content in memory
        with open(karma_config_template, 'rb') as config_template:
            template_content = config_template.read()
            template_content = template_content.decode('utf-8')
            js_template = template.Template(template_content)
            template_content = js_template.render(context)
            template_content = template_content.encode('utf-8')

            if self.verbosity >= 3:
                self.stdout.write("\n")
                self.stdout.write("Karma config contents")
                self.stdout.write("---------------------")
                self.stdout.write(template_content)
                self.stdout.write("\n")

        if not template_content:
            raise IOError("The produced Karma config was empty.")

        # Write the template content to the temp file and close it, so the karma process can read it
        temp_config_file = tempfile.NamedTemporaryFile(suffix='.conf.js', prefix='tmp_karma_',
                                                       dir=self.get_default_site_app(),
                                                       delete=False)  # Manually delete so subprocess can read
        try:
            temp_config_file.write(template_content)
            temp_config_file.close()

            # Start the karma process
            self.stdout.write("\n")
            self.stdout.write("Starting Karma Server (https://github.com/karma-runner/karma)\n")
            self.stdout.write("-------------------------------------------------------------\n")

            subprocess.call(['karma', 'start', temp_config_file.name])

        # When the user kills the karma process, do nothing, then remove the temp file
        except KeyboardInterrupt:
            pass
        finally:
            os.remove(temp_config_file.name)

########NEW FILE########
__FILENAME__ = middleware

class AngularJsonVulnerabilityMiddleware(object):
    """
    A middleware that inserts the AngularJS JSON Vulnerability request on JSON responses.
    """
    # The AngularJS JSON Vulnerability content prefix. See http://docs.angularjs.org/api/ng.$http
    CONTENT_PREFIX = b")]}',\n"

    # Make this class easy to extend by allowing class level access.
    VALID_STATUS_CODES = [200, 201, 202]
    VALID_CONTENT_TYPES = ['application/json']

    def process_response(self, request, response):
        if response.status_code in self.VALID_STATUS_CODES and response['Content-Type'] in self.VALID_CONTENT_TYPES:
            response.content = self.CONTENT_PREFIX + response.content

        return response
########NEW FILE########
__FILENAME__ = models
# No models needed.
########NEW FILE########
__FILENAME__ = storage
import os
from re import sub
from django.contrib.staticfiles.storage import AppStaticStorage


class NamespacedAngularAppStorage(AppStaticStorage):
    """
    A file system storage backend that takes an app module and works
    for the ``app`` directory of it.  The app module will be included
    in the url for the content.
    """
    source_dir = 'app'

    def __init__(self, app, *args, **kwargs):
        """
        Returns a static file storage if available in the given app.
        """
        # app is the actual app module
        self.prefix = os.path.join(*(app.split('.')))
        super(NamespacedAngularAppStorage, self).__init__(app, *args, **kwargs)

    def path(self, name):
        name = sub('^' + self.prefix + os.sep, '', name)
        return super(NamespacedAngularAppStorage, self).path(name)


class NamespacedE2ETestAppStorage(AppStaticStorage):
    """
    A file system storage backend that takes an app module and works
    for the ``tests/e2e`` directory of it.  The app module will be included
    in the url for the content.  NOTE: This should only be used for
    end-to-end testing.
    """
    source_dir = os.path.join('tests', 'e2e')

    def __init__(self, app, *args, **kwargs):
        """
        Returns a static file storage if available in the given app.
        """
        # app is the actual app module
        prefix_args = [self.source_dir] + app.split('.')
        self.prefix = os.path.join(*prefix_args)
        super(NamespacedE2ETestAppStorage, self).__init__(app, *args, **kwargs)


class NamespacedLibTestAppStorage(AppStaticStorage):
    """
    A file system storage backend that takes an app module and works
    for the ``tests/lib`` directory of it.  The app module will be included
    in the url for the content.  NOTE: This should only be used for
    end-to-end testing.
    """
    source_dir = os.path.join('tests', 'lib')

    def __init__(self, app, *args, **kwargs):
        """
        Returns a static file storage if available in the given app.
        """
        # app is the actual app module
        prefix_args = app.split('.') + ['lib']
        self.prefix = os.path.join(*prefix_args)
        super(NamespacedLibTestAppStorage, self).__init__(app, *args, **kwargs)

########NEW FILE########
__FILENAME__ = base
import os

from django.test import SimpleTestCase

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def test_with_angularapp_template_as_python_module(test_fn):
    def fn(self):
        config_module_file = None
        try:
            # Temporarily make config a python module by adding the __init__.py file.
            config_module_file = open('{0}/../config/__init__.py'.format(BASE_DIR), 'w')
            config_module_file.close()

        except Exception as e:
            self.fail('Could not create files due to {0}'.format(e.message))

        else:
            test_fn(self)

        finally:
            if config_module_file:
                if os.path.exists(config_module_file.name):
                    os.remove(config_module_file.name)

                compiled_file_name = '{0}c'.format(config_module_file.name)
                if os.path.exists(compiled_file_name):
                    os.remove(compiled_file_name)

    return fn


class TestAngularAppAsPythonModuleTest(SimpleTestCase):

    @test_with_angularapp_template_as_python_module
    def test_init_py_created(self):
        self.assertTrue(os.path.exists('{0}/../config/__init__.py'.format(BASE_DIR)))
########NEW FILE########
__FILENAME__ = finders
import os

from . import base
from djangular import finders
from django.test import TestCase

APP_BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))


class NamespacedAngularAppDirectoriesFinderTest(TestCase):
    @base.test_with_angularapp_template_as_python_module
    def test_find(self):
        finder = finders.NamespacedAngularAppDirectoriesFinder(apps=['djangular.config.angularapp_template'])
        self.assertEqual(
            finder.find('djangular/config/angularapp_template/index.html'),
            '{0}/config/angularapp_template/app/index.html'.format(APP_BASE_DIR)
        )


class NamespacedE2ETestAppDirectoriesFinderTest(TestCase):
    @base.test_with_angularapp_template_as_python_module
    def test_find(self):
        finder = finders.NamespacedE2ETestAppDirectoriesFinder(apps=['djangular.config.angularapp_template'])
        self.assertEqual(
            finder.find('tests/e2e/djangular/config/angularapp_template/runner.html'),
            '{0}/config/angularapp_template/tests/e2e/runner.html'.format(APP_BASE_DIR)
        )


class NamespacedLibTestAppDirectoriesFinderTest(TestCase):
    @base.test_with_angularapp_template_as_python_module
    def test_find(self):
        finder = finders.NamespacedE2ETestAppDirectoriesFinder(apps=['djangular.config.angularapp_template'])
        self.assertEqual(
            finder.find('tests/e2e/djangular/config/angularapp_template/runner.html'),
            '{0}/config/angularapp_template/tests/e2e/runner.html'.format(APP_BASE_DIR)
        )

########NEW FILE########
__FILENAME__ = middleware
from djangular import middleware

from django.test import TestCase
from django.http import request, response

class AngularJsonVulnerabilityMiddlewareTest(TestCase):

    def test_that_middleware_does_nothing_to_html_requests(self):
        resp = response.HttpResponse(mimetype='text/html', content='<html></html>')
        mware = middleware.AngularJsonVulnerabilityMiddleware()
        mware.process_response(request.HttpRequest(), resp)

        self.assertEqual(resp.content, '<html></html>')

    def test_that_middleware_does_nothing_to_js_requests(self):
        resp = response.HttpResponse(mimetype='text/javascript', content='var blah = [];')
        mware = middleware.AngularJsonVulnerabilityMiddleware()
        mware.process_response(request.HttpRequest(), resp)

        self.assertEqual(resp.content, 'var blah = [];')

    def test_that_middleware_does_nothing_to_invalid_json_requests(self):
        resp = response.HttpResponse(mimetype='application/json', content='[1, 2, 3]', status=400)
        mware = middleware.AngularJsonVulnerabilityMiddleware()
        mware.process_response(request.HttpRequest(), resp)

        self.assertEqual(resp.content, '[1, 2, 3]')

    def test_that_middleware_adds_prefix_to_valid_json_requests(self):
        resp = response.HttpResponse(mimetype='application/json', content='[1, 2, 3]')
        mware = middleware.AngularJsonVulnerabilityMiddleware()
        mware.process_response(request.HttpRequest(), resp)

        self.assertEqual(resp.content, mware.CONTENT_PREFIX + '[1, 2, 3]')

########NEW FILE########
__FILENAME__ = storage
from . import base

from djangular import storage
from django.test import TestCase

class NamespacedAppAngularStorageTest(TestCase):
    def test_source_dir_is_app(self):
        self.assertEqual(storage.NamespacedAngularAppStorage.source_dir, 'app')

    def test_prefix_is_given_app_name(self):
        app_storage = storage.NamespacedAngularAppStorage('djangular')
        self.assertEqual(app_storage.prefix, 'djangular')

    @base.test_with_angularapp_template_as_python_module
    def test_prefix_is_given_app_name_for_more_complicated_scenario(self):
        app_storage = storage.NamespacedAngularAppStorage('djangular.config.angularapp_template')
        self.assertEqual(app_storage.prefix, 'djangular/config/angularapp_template')


class NamespacedE2ETestAppStorageTest(TestCase):
    def test_source_dir_is_tests(self):
        self.assertEqual(storage.NamespacedE2ETestAppStorage.source_dir, 'tests/e2e')

    def test_prefix_is_given_app_name(self):
        app_storage = storage.NamespacedE2ETestAppStorage('djangular')
        self.assertEqual(app_storage.prefix, 'tests/e2e/djangular')

    @base.test_with_angularapp_template_as_python_module
    def test_prefix_is_given_app_name_for_more_complicated_scenario(self):
        app_storage = storage.NamespacedE2ETestAppStorage('djangular.config.angularapp_template')
        self.assertEqual(app_storage.prefix, 'tests/e2e/djangular/config/angularapp_template')
########NEW FILE########
__FILENAME__ = utils
import os

from djangular import utils
from django.test import SimpleTestCase


class SiteAndPathUtilsTest(SimpleTestCase):

    site_utils = utils.SiteAndPathUtils()

    def test_djangular_root(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        djangular_dir = os.path.dirname(current_dir)
        self.assertEqual(djangular_dir, self.site_utils.get_djangular_root())

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from .views import DjangularModuleTemplateView

urlpatterns = patterns('',
    url(r'^app.js$', DjangularModuleTemplateView.as_view(), name='djangular-module')
)

########NEW FILE########
__FILENAME__ = utils
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class SiteAndPathUtils(object):
    """
    Mixin to get commonly used directories in Djangular Commands
    """
    def get_default_site_app(self):
        """
        Retrieves the name of the django app that contains the site config.
        """
        return os.environ["DJANGO_SETTINGS_MODULE"].replace('.settings', '')

    def get_default_site_path(self):
        """
        Retrieves the name of the django app that contains the site config.
        """
        settings_module = __import__(self.get_default_site_app())
        return settings_module.__path__[0]

    def get_djangular_root(self):
        """
        Returns the absolute path of the djangular app.
        """
        return CURRENT_DIR

    def get_project_root(self):
        """
        Retrieves the root of the project directory without having to have a entry in the settings.
        """
        default_site = self.get_default_site_app()
        path = self.get_default_site_path()
        # Move up one directory per '.' in site path.  Most sites are at the top level, so this is just a precaution.
        for _ in range(len(default_site.split('.'))):
            path = os.path.dirname(path)
        return path

########NEW FILE########
__FILENAME__ = views
from django.views.generic.base import TemplateView


class DjangularModuleTemplateView(TemplateView):
    content_type = 'text/javascript'
    template_name = 'djangular_module.js'
    disable_csrf_headers = False

    def get_context_data(self, **kwargs):
        context = super(DjangularModuleTemplateView, self).get_context_data(**kwargs)
        context['disable_csrf_headers'] = self.disable_csrf_headers
        return context

########NEW FILE########
