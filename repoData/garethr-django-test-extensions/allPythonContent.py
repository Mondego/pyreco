__FILENAME__ = common
import os
import re

# Test classes inherit from the Django TestCase
from django.test import TestCase

# If you're wanting to do direct database queries you'll need this
from django.db import connection

# The BeautifulSoup HTML parser is useful for testing markup fragments
from BeautifulSoup import BeautifulSoup as Soup

# needed to login to the admin
from django.contrib.auth.models import User
from django.utils.encoding import smart_str


class Common(TestCase):
    """
    This class contains a number of custom assertions which
    extend the default Django assertions. Use this as the super
    class for you tests rather than django.test.TestCase
    """

    # a list of fixtures for loading data before each test
    fixtures = []

    def setUp(self):
        """
        setUp is run before each test in the class. Use it for
        initilisation and creating mock objects to test
        """
        pass

    def tearDown(self):
        """
        tearDown is run after each test in the class. Use it for
        cleaning up data created during each test
        """
        pass

    # A few useful helpers methods

    def execute_sql(*sql):
        "execute a SQL query and return the cursor"
        cursor = connection.cursor()
        cursor.execute(*sql)
        return cursor

    # Custom assertions

    def assert_equal(self, *args, **kwargs):
        'Assert that two values are equal'

        return self.assertEqual(*args, **kwargs)

    def assert_not_equal(self, *args, **kwargs):
        "Assert that two values are not equal"
        return not self.assertNotEqual(*args, **kwargs)

    def assert_contains(self, needle, haystack, diagnostic=''):
        'Assert that one value (the hasystack) contains another value (the needle)'
        diagnostic = diagnostic + "\nContent should contain `%s' but doesn't:\n%s" % (needle, haystack)
        diagnostic = diagnostic.strip()
        return self.assert_(needle in haystack, diagnostic)

    def assert_doesnt_contain(self, needle, haystack):  #  CONSIDER  deprecate me for deny_contains
        "Assert that one value (the hasystack) does not contain another value (the needle)"
        return self.assert_(needle not in haystack, "Content should not contain `%s' but does:\n%s" % (needle, haystack))

    def deny_contains(self, needle, haystack):
        "Assert that one value (the hasystack) does not contain another value (the needle)"
        return self.assert_(needle not in haystack, "Content should not contain `%s' but does:\n%s" % (needle, haystack))

    def assert_regex_contains(self, pattern, string, flags=None):
        'Assert that the given regular expression matches the string'
        flags = flags or 0
        disposition = re.search(pattern, string, flags)
        self.assertTrue(disposition != None, repr(smart_str(pattern)) + ' should match ' + repr(smart_str(string)))

    def deny_regex_contains(self, pattern, slug):
        'Deny that the given regular expression pattern matches a string'

        r = re.compile(pattern)

        self.assertEqual( None,
                          r.search(smart_str(slug)),
                          pattern + ' should not match ' + smart_str(slug) )

    def assert_count(self, expected, model):
        "Assert that their are the expected number of instances of a given model"
        actual = model.objects.count()
        self.assert_equal(expected, actual, "%s should have %d objects, had %d" % (model.__name__, expected, actual))

    def assert_counts(self, expected_counts, models):
        "Assert than a list of numbers is equal to the number of instances of a list of models"
        if len(expected_counts) != len(models):
            raise("Number of counts and number of models should be equal")
        actual_counts = [model.objects.count() for model in models]
        self.assert_equal(expected_counts, actual_counts, "%s should have counts %s but had %s" % ([m.__name__ for m in models], expected_counts, actual_counts))

    def assert_is_instance(self, model, obj):
        "Assert than a given object is an instance of a model"
        self.assert_(isinstance(obj, model), "%s should be instance of %s" % (obj, model))

    def assert_raises(self, *args, **kwargs):
        "Assert than a given function and arguments raises a given exception"
        return self.assertRaises(*args, **kwargs)

    def assert_attrs(self, obj, **kwargs):
        "Assert a given object has a given set of attribute values"
        for key in sorted(kwargs.keys()):
            expected = kwargs[key]
            actual = getattr(obj, key)
            self.assert_equal(expected, actual, u"Object's %s expected to be `%s', is `%s' instead" % (key, expected, actual))

    def assert_key_exists(self, key, item):
        "Assert than a given key exists in a given item"
        try:
            self.assertTrue(key in item)
        except AssertionError:
            print 'no %s in %s' % (key, item)
            raise AssertionError

    def assert_file_exists(self, file_path):
        "Assert a given file exists"
        self.assertTrue(os.path.exists(file_path), "%s does not exist!" % file_path)

    def assert_has_attr(self, obj, attr):
        "Assert a given object has a give attribute, without checking the values"
        try:
            getattr(obj, attr)
            assert(True)
        except AttributeError:
            assert(False)

    def _xml_to_tree(self, xml, forgiving=False):
        from lxml import etree
        self._xml = xml

        if not isinstance(xml, basestring):
            self._xml = str(xml)  #  TODO  tostring
            return xml

        if '<html' in xml[:200]:
            parser = etree.HTMLParser(recover=forgiving)
            return etree.HTML(str(xml), parser)
        else:
            parser = etree.XMLParser(recover=forgiving)
            return etree.XML(str(xml))

    def assert_xml(self, xml, xpath, **kw):
        'Check that a given extent of XML or HTML contains a given XPath, and return its first node'
        tree = self._xml_to_tree(xml, forgiving=kw.get('forgiving', False))
        nodes = tree.xpath(xpath)
        self.assertTrue(len(nodes) > 0, xpath + ' should match ' + self._xml)
        node = nodes[0]
        if kw.get('verbose', False):
            self.reveal_xml(node)
        return node

    def reveal_xml(self, node):
        'Spews an XML node as source, for diagnosis'
        from lxml import etree
        print etree.tostring(node, pretty_print=True)

    def deny_xml(self, xml, xpath):
        'Check that a given extent of XML or HTML does not contain a given XPath'
        tree = self._xml_to_tree(xml)
        nodes = tree.xpath(xpath)
        self.assertEqual(0, len(nodes), xpath + ' should not appear in ' + self._xml)
########NEW FILE########
__FILENAME__ = django_common
# Test classes inherit from the Django TestCase
from common import Common
import re

# needed to login to the admin
from django.contrib.auth.models import User
from django.utils.encoding import smart_str

from django.template import Template, Context

class DjangoCommon(Common):
    """
    This class contains a number of custom assertions which
    extend the default Django assertions. Use this as the super
    class for you tests rather than django.test.TestCase
    """

    # a list of fixtures for loading data before each test
    fixtures = []

    def setUp(self):
        """
        setUp is run before each test in the class. Use it for
        initilisation and creating mock objects to test
        """
        pass

    def tearDown(self):
        """
        tearDown is run after each test in the class. Use it for
        cleaning up data created during each test
        """
        pass

    # A few useful helpers methods

    def login_as_admin(self):
        "Create, then login as, an admin user"
        # Only create the user if they don't exist already ;)
        try:
            User.objects.get(username="admin")
        except User.DoesNotExist:
            user = User.objects.create_user('admin', 'admin@example.com', 'password')
            user.is_staff = True
            user.is_superuser = True
            user.save()

        if not self.client.login(username='admin', password='password'):
            raise Exception("Login failed")

    # Some assertions need to know which template tag libraries to load
    # so we provide a list of templatetag libraries
    template_tag_libraries = []

    def render(self, template, **kwargs):
        "Return the rendering of a given template including loading of template tags"
        template = "".join(["{%% load %s %%}" % lib for lib in self.template_tag_libraries]) + template
        return Template(template).render(Context(kwargs)).strip()

    # Custom assertions

    def assert_response_contains(self, fragment, response):
        "Assert that a response object contains a given string"
        self.assert_(fragment in response.content, "Response should contain `%s' but doesn't:\n%s" % (fragment, response.content))

    def assert_response_doesnt_contain(self, fragment, response):
        "Assert that a response object does not contain a given string"
        self.assert_(fragment not in response.content, "Response should not contain `%s' but does:\n%s" % (fragment, response.content))

    def assert_render_matches(self, template, match_regexp, vars={}):
        "Assert than the output from rendering a given template with a given context matches a given regex"
        r = re.compile(match_regexp)
        actual = Template(template).render(Context(vars))
        self.assert_(r.match(actual), "Expected: %s\nGot: %s" % (
            match_regexp, actual
        ))

    def assert_code(self, response, code):
        "Assert that a given response returns a given HTTP status code"
        self.assertEqual(code, response.status_code, "HTTP Response status code should be %d, and is %d" % (code, response.status_code))

    def assertNotContains(self, response, text, status_code=200):  # overrides Django's assertion, because all diagnostics should be stated positively!!!
        """
        Asserts that a response indicates that a page was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` doesn't occurs in the content of the response.
        """
        self.assertEqual(response.status_code, status_code,
            "Retrieving page: Response code was %d (expected %d)'" %
                (response.status_code, status_code))
        text = smart_str(text, response._charset)
        self.assertEqual(response.content.count(text),
             0, "Response should not contain '%s'" % text)

    def assert_render(self, expected, template, **kwargs):
        "Asserts than a given template and context render a given fragment"
        self.assert_equal(expected, self.render(template, **kwargs))

    def assert_render_matches(self, match_regexp, template, vars={}):
        r = re.compile(match_regexp)
        actual = Template(template).render(Context(vars))
        self.assert_(r.match(actual), "Expected: %s\nGot: %s" % (
            match_regexp, actual
        ))

    def assert_doesnt_render(self, expected, template, **kwargs):
        "Asserts than a given template and context don't render a given fragment"
        self.assert_not_equal(expected, self.render(template, **kwargs))

    def assert_render_contains(self, expected, template, **kwargs):
        "Asserts than a given template and context rendering contains a given fragment"
        self.assert_contains(expected, self.render(template, **kwargs))

    def assert_render_doesnt_contain(self, expected, template, **kwargs):
        "Asserts than a given template and context rendering does not contain a given fragment"
        self.assert_doesnt_contain(expected, self.render(template, **kwargs))

    def assert_mail(self, funk):
        '''
        checks that the called block shouts out to the world

        returns either a single mail object or a list of more than one
        '''

        from django.core import mail
        previous_mails = len(mail.outbox)
        funk()
        mails = mail.outbox[ previous_mails : ]
        assert [] != mails, 'the called block produced no mails'
        if len(mails) == 1:  return mails[0]
        return mails

    def assert_latest(self, query_set, lamb):
        pks = list(query_set.values_list('pk', flat=True).order_by('-pk'))
        high_water_mark = (pks+[0])[0]
        lamb()

          # NOTE we ass-ume the database generates primary keys in monotonic order.
          #         Don't use these techniques in production,
          #          or in the presence of a pro DBA

        nu_records = list(query_set.filter(pk__gt=high_water_mark).order_by('pk'))
        if len(nu_records) == 1:  return nu_records[0]
        if nu_records:  return nu_records  #  treating the returned value as a scalar or list
                                           #  implicitly asserts it is a scalar or list
        source = open(lamb.func_code.co_filename, 'r').readlines()[lamb.func_code.co_firstlineno - 1]
        source = source.replace('lambda:', '').strip()
        model_name = str(query_set.model)

        self.assertFalse(True, 'The called block, `' + source +
                               '` should produce new ' + model_name + ' records')

    def deny_mail(self, funk):
        '''checks that the called block keeps its opinions to itself'''

        from django.core import mail
        previous_mails = len(mail.outbox)
        funk()
        mails = mail.outbox[ previous_mails : ]
        assert [] == mails, 'the called block should produce no mails'

    def assert_model_changes(self, mod, item, frum, too, lamb):
        source = open(lamb.func_code.co_filename, 'r').readlines()[lamb.func_code.co_firstlineno - 1]
        source = source.replace('lambda:', '').strip()
        model  = str(mod.__class__).replace("'>", '').split('.')[-1]

        should = '%s.%s should equal `%s` before your activation line, `%s`' % \
                  (model, item, frum, source)

        self.assertEqual(frum, mod.__dict__[item], should)
        lamb()
        mod = mod.__class__.objects.get(pk=mod.pk)

        should = '%s.%s should equal `%s` after your activation line, `%s`' % \
                  (model, item, too, source)

        self.assertEqual(too, mod.__dict__[item], should)
        return mod

########NEW FILE########
__FILENAME__ = examples
from test_extensions.common import Common

class Examples(Common):
    """
    This class contains a number of example tests using the common custom assertions.
    Note that these tests won't run as they refer to code that does not exist. Note also
    that all tests begin with test_. This ensures the test runner picks them up.
    """
        
    def test_always_pass(self):
        "Demonstration of how to pass a test based on logic"
        self.assertTrue(True)
    
    def test_always_fail(self):
        "Demonstration of how to fail a test based on logic"
        self.assertFalse(False, "Something went wrong")
    
    def test_presense_of_management_command(self):
        "Check to see whether a given management commands is available"
        try:
            call_command('management_command_name')
        except Exception:
            self.assert_("management_command_name management command missing")    

    def test_object_type(self):
        "Simple test to check a given object type"
        example = Object()
        self.assert_is_instance(Object,example)        

    def test_assert_raises(self):
        "Test whether a given function raises a given exception"
        path = os.path.join('/example_directory', 'invalid_file_name')
        self.assert_raises(ExampleException, example_function, path)

    def test_assert_attrs(self):
        "Demonstration of assert_attrs, checks that a given object has a given set of attributes"
        event = Event(title="Title",description="Description")
        self.assert_attrs(event,
          title = 'Title',
          description = 'Description'
        )

    def test_assert_counts(self):
        "Demonstration of assert_counts using a set of fictional objects"
        self.assert_counts([1, 1, 1, 1], [Object1, Object2, Object3, Object4])
  
    def test_assert_code(self):
        "Use the HTTP client to make a request and then check the HTTP status code in the response"
        response = self.client.get('/')
        self.assert_code(response, 200)
        
    def test_creation_of_objects_in_admin(self):
        "Demonstration of an admin test to check successful object creation"
        form = {
            'title':       'title',
            'description': 'description',
        }
        self.login_as_admin()
        self.assert_counts([0], [Object])
        response = self.client.post('/admin/objects/object/add/', form)
        self.assert_code(response, 302)
        self.assert_counts([1], [Object])
            
    def test_you_can_delete_objects_you_created(self):
        "Test object deletion via the admin"
        self.login_as_admin()
        form = {
            'title':       'title',
            'description': 'description',
        }
        self.assert_counts([0], [Object])
        self.client.post('/admin/objects/object/add/', form)
        self.assert_counts([1], [Object])
        response = self.client.post('/admin/objects/object/%d/delete/' % Object.objects.get().id, {'post':'yes'})
        self.assert_counts([0], [Object])
                
    def test_assert_renders(self):
        "Example template tag test to check correct rendering"
        expected = 'output of template tag'
        self.assert_renders('{% load templatetag %}{% templatetag %}', expected)
        
    def test_assert_render_matches(self):
        "Example of testing template tags using regex match"
        self.assert_render_matches(
            r'^/assets/a/common/blah.js\?cachebust=[\d\.]+$',
            '{% load static %}{% static "a/common/blah.js" %}',
        )
        
    def test_simple_addition(self):
        "Pattern for testing input/output of a function"
        for (augend, addend, result, msg) in [
              (1,  2,  3, "1+2=3"),
              (1,  3,  4, "1+3=4"),
            ]:
            self.assert_equal(result,augend.plus(addend))

    def test_response_contains(self):
        "Example of a test for content on a given view"
        response = self.client.get('/example/')
        self.assert_response_contains('<h1>', response)
        self.assert_response_doesnt_contain("Not on page", response)

    def test_using_beautiful_soup(self):
        "Example test for content on a given view, this time using the BeautifulSoup parser"
        response = self.client.get('/example/')
        soup = BeautifulSoup(response.content)
        self.assert_equal("Page Title", soup.find("title").string.strip())
        
    def test_get_tables_that_should_exist(self):
        "Useful pattern for checking for the existence of all required tables"
        tables_that_exist = [row[0] for row in _execute("SHOW TABLES").fetchall()]
        self.assert_equal(True, 'objects_object' in tables_that_exist)
########NEW FILE########
__FILENAME__ = twillexamples
from test_extensions.twill import TwillCommon

class TwillExample(TwillCommon):
    """
    Example Twill tests using the TwillCommon class.
    """

    # set a global url. Note you might do this from a settings file.
    url = "http://www.example.com/"

    def test_for_200_status_code(self):
        "Does the provided url return an HTTP status code of 200"
        self.code("200")

    def test_for_h1(self):
        "Does the url return content which matches the given regex"
        self.find("<h1(.*)<\/h1>")
########NEW FILE########
__FILENAME__ = runtester
from django.core.management.base import BaseCommand
from django.utils import autoreload
import os
import sys
import time

INPROGRESS_FILE = 'testing.inprogress'

def get_test_command():
    """
    Return an instance of the Command class to use.

    This method can be patched in to run a test command other than the on in
    core Django.  For example, to make a runtester for South:

    from django.core.management.commands import runtester
    from django.core.management.commands.runtester import Command

    def get_test_command():
        from south.management.commands.test import Command as TestCommand
        return TestCommand()

    runtester.get_test_command = get_test_command
    """

    from test_extensions.management.commands.test import Command as TestCommand
    return TestCommand()

def my_reloader_thread():
    """
    Wait for a test run to complete before exiting.
    """

    # If a file is saved while tests are being run, the base reloader just
    # kills the process.  This is bad because it wedges the database and then
    # the user is prompted to delete the database.  Instead, wait for
    # INPROGRESS_FILE to disappear, then exit.  Exiting the thread will then
    # rerun the suite.
    while autoreload.RUN_RELOADER:
        if autoreload.code_changed():
            while os.path.exists(INPROGRESS_FILE):
                time.sleep(1)
            sys.exit(3) # force reload
        time.sleep(1)

# monkeypatch the reloader_thread function with the one above
autoreload.reloader_thread = my_reloader_thread

class Command(BaseCommand):
    option_list = BaseCommand.option_list
    help = "Starts a command that tests upon saving files."
    args = '[optional apps to test]'

    # Validation is called explicitly each time the suite is run
    requires_model_validation = False

    def handle(self, *args, **options):
        if os.path.exists(INPROGRESS_FILE):
            os.remove(INPROGRESS_FILE)

        def inner_run():
            try:
                open(INPROGRESS_FILE, 'wb').close()

                test_command = get_test_command()
                test_command.handle(*args, **options)
            finally:
                if os.path.exists(INPROGRESS_FILE):
                    os.remove(INPROGRESS_FILE)

        autoreload.main(inner_run)

########NEW FILE########
__FILENAME__ = test
import sys
from optparse import make_option

from django.core import management
from django.conf import settings
from django.db.models import get_app, get_apps
from django.core.management.base import BaseCommand

# Django versions prior to 1.2 don't include the DjangoTestSuiteRunner class;
# Django versions since 1.2 include multi-database support, which doesn't play
# nicely with the database setup in the XML test runner.
try:
    from django.test.simple import DjangoTestSuiteRunner
    xml_runner = 'test_extensions.testrunners.xmloutput.XMLTestSuiteRunner'
except ImportError:  # We are in a version prior to 1.2
    xml_runner = 'test_extensions.testrunners.xmloutput.run_tests'

skippers = []

class Command(BaseCommand):
    option_list = BaseCommand.option_list

    if '--verbosity' not in [opt.get_opt_string() for opt in BaseCommand.option_list]:
        option_list += \
            make_option('--verbosity', action='store', dest='verbosity',
                default='0',
                type='choice', choices=['0', '1', '2'],
                help='Verbosity level; 0=minimal, 1=normal, 2=all'),

    option_list += (
        make_option('--noinput', action='store_false', dest='interactive',
            default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--callgraph', action='store_true', dest='callgraph',
            default=False,
            help='Generate execution call graph (slow!)'),
        make_option('--coverage', action='store_true', dest='coverage',
            default=False,
            help='Show coverage details'),
        make_option('--coverage_html_only', action='store_true', dest='coverage_html_only',
            default=False,
            help='Supress stdout output if using HTML output. Else, is ignored'),
        make_option('--xmlcoverage', action='store_true', dest='xmlcoverage',
            default=False,
            help='Show coverage details and write them into a xml file'),
        make_option('--figleaf', action='store_true', dest='figleaf',
            default=False,
            help='Produce figleaf coverage report'),
        make_option('--xml', action='store_true', dest='xml', default=False,
            help='Produce JUnit-type xml output'),
        make_option('--nodb', action='store_true', dest='nodb', default=False,
            help='No database required for these tests'),
        make_option('--failfast', action='store_true', dest='failfast',
            default=False,
            help='Tells Django to stop running the test suite after first failed test.'),

    )
    help = """Custom test command which allows for
        specifying different test runners."""
    args = '[appname ...]'

    requires_model_validation = True

    def handle(self, *test_labels, **options):

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)
        callgraph = options.get('callgraph', False)
        failfast = options.get("failfast", False)
        coverage_html_only = options.get("coverage_html_only", False)

        # it's quite possible someone, lets say South, might have stolen
        # the syncdb command from django. For testing purposes we should
        # probably put it back. Migrations don't really make sense
        # for tests. Actually the South test runner does this too.
        management.get_commands()
        management._commands['syncdb'] = 'django.core'

        if options.get('nodb'):
            if options.get('xmlcoverage'):
                test_runner_name = 'test_extensions.testrunners.nodatabase.run_tests_with_xmlcoverage'
            elif options.get('coverage'):
                test_runner_name = 'test_extensions.testrunners.nodatabase.run_tests_with_coverage'
            else:
                test_runner_name = 'test_extensions.testrunners.nodatabase.run_tests'
        elif options.get('xmlcoverage'):
            test_runner_name = 'test_extensions.testrunners.codecoverage.run_tests_xml'
        elif options.get ('coverage'):
            test_runner_name = 'test_extensions.testrunners.codecoverage.run_tests'
        elif options.get('figleaf'):
            test_runner_name = 'test_extensions.testrunners.figleafcoverage.run_tests'
        elif options.get('xml'):
            test_runner_name = xml_runner
        else:
            test_runner_name = settings.TEST_RUNNER

        test_path = test_runner_name.split('.')
        # Allow for Python 2.5 relative paths
        if len(test_path) > 1:
            test_module_name = '.'.join(test_path[:-1])
        else:
            test_module_name = '.'
        test_module = __import__(test_module_name, {}, {}, test_path[-1])
        test_runner = getattr(test_module, test_path[-1])

        if hasattr(settings, 'SKIP_TESTS'):
            if not test_labels:
                test_labels = list()
                for app in get_apps():
                    test_labels.append(app.__name__.split('.')[-2])
            for app in settings.SKIP_TESTS:
                try:
                    test_labels = list(test_labels)
                    test_labels.remove(app)
                except ValueError:
                    pass
                    
        test_options = dict(verbosity=verbosity,
            interactive=interactive)
            
        if options.get('coverage'):
            test_options["callgraph"] = callgraph
            test_options["html_only"] = coverage_html_only
        
        try:
            failures = test_runner(test_labels, **test_options)
        except TypeError: #Django 1.2
            test_options["failfast"] = failfast
            failures = test_runner(**test_options).run_tests(test_labels)
        
        if failures:
            sys.exit(failures)

########NEW FILE########
__FILENAME__ = codecoverage
import coverage
import os, sys
from inspect import getmembers, ismodule

from django.conf import settings
from django.test.simple import run_tests as django_test_runner
from django.db.models import get_app, get_apps
from django.utils.functional import curry

from nodatabase import run_tests as nodatabase_run_tests

def is_wanted_module(mod):
    included = getattr(settings, "COVERAGE_INCLUDE_MODULES", [])
    excluded = getattr(settings, "COVERAGE_EXCLUDE_MODULES", [])
    
    marked_to_include = None 

    for exclude in excluded:
        if exclude.endswith("*"):
            if mod.__name__.startswith(exclude[:-1]):
                marked_to_include = False
        elif mod.__name__ == exclude:
            marked_to_include = False
    
    for include in included:
        if include.endswith("*"):
            if mod.__name__.startswith(include[:-1]):
                marked_to_include = True
        elif mod.__name__ == include:
            marked_to_include = True
    
    # marked_to_include=None handles not user-defined states
    if marked_to_include is None:
        if included and excluded:
            # User defined exactly what they want, so exclude other
            marked_to_include = False
        elif excluded:
            # User could define what the want not, so include other.
            marked_to_include = True
        elif included:
            # User enforced what they want, so exclude other
            marked_to_include = False
        else:
            # Usar said nothing, so include anything
            marked_to_include = True

    return marked_to_include
    

def get_coverage_modules(app_module):
    """
    Returns a list of modules to report coverage info for, given an
    application module.
    """
    app_path = app_module.__name__.split('.')[:-1]
    coverage_module = __import__('.'.join(app_path), {}, {}, app_path[-1])

    return [coverage_module] + [attr for name, attr in
        getmembers(coverage_module) if ismodule(attr) and name != 'tests']

def get_all_coverage_modules(app_module):
    """
    Returns all possible modules to report coverage on, even if they
    aren't loaded.
    """
    # We start off with the imported models.py, so we need to import
    # the parent app package to find the path.
    app_path = app_module.__name__.split('.')[:-1]
    app_package = __import__('.'.join(app_path), {}, {}, app_path[-1])
    app_dirpath = app_package.__path__[-1]

    mod_list = []
    for root, dirs, files in os.walk(app_dirpath):
        root_path = app_path + root[len(app_dirpath):].split(os.path.sep)[1:]
        excludes = getattr(settings, 'EXCLUDE_FROM_COVERAGE', [])
        if app_path[0] not in excludes:
            for file in files:
                if file.lower().endswith('.py'):
                    mod_name = file[:-3].lower()
                    try:
                        mod = __import__('.'.join(root_path + [mod_name]),
                            {}, {}, mod_name)
                    except ImportError:
                        pass
                    else:
                        mod_list.append(mod)

    return mod_list

def run_tests(test_labels, verbosity=1, interactive=True,
        extra_tests=[], nodatabase=False, xml_out=False, callgraph=False, html_only=False):
    """
    Test runner which displays a code coverage report at the end of the
    run.
    """
    cov = coverage.coverage()
    cov.erase()
    cov.use_cache(0)

    test_labels = test_labels or getattr(settings, "TEST_APPS", None)
    cover_branch = getattr(settings, "COVERAGE_BRANCH_COVERAGE", False)
    cov = coverage.coverage(branch=cover_branch, cover_pylib=False)
    cov.use_cache(0)
     
    coverage_modules = []
    if test_labels:
        for label in test_labels:
            # Don't report coverage if you're only running a single
            # test case.
            if '.' not in label:
                app = get_app(label)
                coverage_modules.extend(get_all_coverage_modules(app))
    else:
        for app in get_apps():
            coverage_modules.extend(get_all_coverage_modules(app))

    morfs = filter(is_wanted_module, coverage_modules)

    if callgraph:
        try:
            import pycallgraph
            #_include = [i.__name__ for i in coverage_modules]
            _included = getattr(settings, "COVERAGE_INCLUDE_MODULES", [])
            _excluded = getattr(settings, "COVERAGE_EXCLUDE_MODULES", [])

            _included = [i.strip('*')+'*' for i in _included]
            _excluded = [i.strip('*')+'*' for i in _included]

            _filter_func = pycallgraph.GlobbingFilter(
                include=_included or ['*'],
                #include=['lotericas.*'],
                #exclude=[],
                #max_depth=options.max_depth,
            )

            pycallgraph_enabled = True
        except ImportError:
            pycallgraph_enabled = False
    else:
        pycallgraph_enabled = False

    cov.start()
    
    if pycallgraph_enabled:
        pycallgraph.start_trace(filter_func=_filter_func)

    if nodatabase:
        results = nodatabase_run_tests(test_labels, verbosity, interactive,
            extra_tests)
    else:
        results = django_test_runner(test_labels, verbosity, interactive,
            extra_tests)
    
    if callgraph and pycallgraph_enabled:
        pycallgraph.stop_trace()

    cov.stop()
    
    if getattr(settings, "COVERAGE_HTML_REPORT", False) or \
            os.environ.get("COVERAGE_HTML_REPORT"):
        output_dir = getattr(settings, "COVERAGE_HTML_DIRECTORY", "covhtml")
        report_method = curry(cov.html_report, directory=output_dir)
        if callgraph and pycallgraph_enabled:
            callgraph_path = output_dir + '/' + 'callgraph.png'
            pycallgraph.make_dot_graph(callgraph_path)

        print >>sys.stdout
        print >>sys.stdout, "Coverage HTML reports were output to '%s'" %output_dir
        if callgraph:
            if pycallgraph_enabled:
                print >>sys.stdout, "Call graph was output to '%s'" %callgraph_path
            else:
                print >>sys.stdout, "Call graph was not generated: Install 'pycallgraph' module to do so"

    else:
        report_method = cov.report

    if coverage_modules:
        if xml_out:
            # using the same output directory as the --xml function uses for testing
            if not os.path.isdir(os.path.join("temp", "xml")):
                os.makedirs(os.path.join("temp", "xml"))
            output_filename = 'temp/xml/coverage_output.xml'
            cov.xml_report(morfs=coverage_modules, outfile=output_filename)

        if not html_only:
            cov.report(coverage_modules, show_missing=1)

    return results


def run_tests_xml (test_labels, verbosity=1, interactive=True,
        extra_tests=[], nodatabase=False):
    return run_tests(test_labels, verbosity, interactive,
               extra_tests, nodatabase, xml_out=True)

########NEW FILE########
__FILENAME__ = figleafcoverage
import os
import commands

from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.simple import run_tests as django_test_runner

import figleaf
 
def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    setup_test_environment()
    figleaf.start()
    test_results = django_test_runner(test_labels, verbosity, interactive, extra_tests)
    figleaf.stop()
    if not os.path.isdir(os.path.join("temp", "figleaf")): os.makedirs(os.path.join("temp", "figleaf"))
    file_name = "temp/figleaf/test_output.figleaf"
    figleaf.write_coverage(file_name)
    output = commands.getoutput("figleaf2html " + file_name + " --output-directory=temp/figleaf")
    print output
    return test_results
########NEW FILE########
__FILENAME__ = nodatabase
"""
Test runner that doesn't use the database. Contributed by
Bradley Wright <intranation.com>
"""

import os
import unittest
from glob import glob

from django.test.utils import setup_test_environment, teardown_test_environment
from django.conf import settings
from django.test.simple import get_app, build_test, build_suite

import coverage

def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """
    Run the unit tests for all the test labels in the provided list.
    Labels must be of the form:
     - app.TestClass.test_method
        Run a single specific test method
     - app.TestClass
        Run all the test methods in a given class
     - app
        Search for doctests and unittests in the named application.

    When looking for tests, the test runner will look in the models and
    tests modules for the application.

    A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.

    Returns the number of tests that failed.
    """
    setup_test_environment()

    settings.DEBUG = False
    suite = unittest.TestSuite()

    modules_to_cover = []

    # if passed a list of tests...
    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    # ...otherwise use all installed
    else:
        for app in get_apps():
            # skip apps named "Django" because they use a database
            if not app.__name__.startswith('django'):
                # get the actual app name
                app_name = app.__name__.replace('.models', '')
                # get a list of the files inside that module
                files = glob('%s/*.py' % app_name)
                # remove models because we don't use them, stupid
                new_files = [i for i in files if not i.endswith('models.py')]
                modules_to_cover.extend(new_files)
                # actually test the file
                suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)

    teardown_test_environment()

    return len(result.failures) + len(result.errors)

def run_tests_with_coverage(test_labels, verbosity=1, interactive=True, extra_tests=[], xml_out=False):
    """
    Run the unit tests for all the test labels in the provided list.
    Labels must be of the form:
     - app.TestClass.test_method
        Run a single specific test method
     - app.TestClass
        Run all the test methods in a given class
     - app
        Search for doctests and unittests in the named application.

    When looking for tests, the test runner will look in the models and
    tests modules for the application.

    A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.

    Returns the number of tests that failed.
    """
    setup_test_environment()

    settings.DEBUG = False
    suite = unittest.TestSuite()

    modules_to_cover = []

    # start doing some coverage action
    cov = coverage.coverage()
    cov.erase()
    cov.start()

    # if passed a list of tests...
    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    # ...otherwise use all installed
    else:
        for app in get_apps():
            # skip apps named "Django" because they use a database
            if not app.__name__.startswith('django'):
                # get the actual app name
                app_name = app.__name__.replace('.models', '')
                # get a list of the files inside that module
                files = glob('%s/*.py' % app_name)
                # remove models because we don't use them, stupid
                new_files = [i for i in files if not i.endswith('models.py')]
                modules_to_cover.extend(new_files)
                # actually test the file
                suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)

    teardown_test_environment()

    # stop coverage
    cov.stop()

    # output results
    print ''
    print '--------------------------'
    print 'Unit test coverage results'
    print '--------------------------'
    print ''
    if xml_out:
        # using the same output directory as the --xml function uses for testing
        if not os.path.isdir(os.path.join("temp", "xml")):
            os.makedirs(os.path.join("temp", "xml"))
        output_filename = 'temp/xml/coverage_output.xml'
        cov.xml_report(morfs=coverage_modules, outfile=output_filename)
    cov.report(modules_to_cover, show_missing=1)

    return len(result.failures) + len(result.errors)

def run_tests_with_xmlcoverage(test_labels, verbosity=1, interactive=True, extra_tests=[]):
   return run_tests_with_coverage(test_labels, verbosity, interactive, extra_tests, xml_out=True) 


########NEW FILE########
__FILENAME__ = xmloutput
import time, traceback, string

from xmlunit.unittest import _WritelnDecorator, XmlTextTestRunner as his_XmlTextTestRunner

from django.test.simple import *
from xml.sax.saxutils import escape

try:
    # The django.utils.unittest alias is available in Django >= 1.3
    from django.utils import unittest
except ImportError:
    import unittest

try:
    class XMLTestSuiteRunner(DjangoTestSuiteRunner):
        def run_suite(self, suite, **kwargs):
            return XMLTestRunner(verbosity=self.verbosity).run(suite)
except NameError:  # DjangoTestSuiteRunner is not available in Django < 1.2
    pass

def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    setup_test_environment()

    settings.DEBUG = False
    suite = unittest.TestSuite()

    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    else:
        for app in get_apps():
            suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    old_name = settings.DATABASE_NAME
    from django.db import connection
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)
    result = XMLTestRunner(verbosity=verbosity).run(suite)
    connection.creation.destroy_test_db(old_name, verbosity)

    teardown_test_environment()

    return len(result.failures) + len(result.errors)


class XMLTestRunner(his_XmlTextTestRunner):
    def _makeResult(self):
        return _XmlTextTestResult(self.testResults, self.descriptions, self.verbosity)

class _XmlTextTestResult(unittest.TestResult):
    """A test result class that can print xml formatted text results to a stream.

    Used by XmlTextTestRunner.
    """
    #separator1 = '=' * 70
    #separator2 = '-' * 70
    def __init__(self, stream, descriptions, verbosity):
        unittest.TestResult.__init__(self)
        self.stream = _WritelnDecorator(stream)
        self.showAll = verbosity > 1
        self.descriptions = descriptions
        self._lastWas = 'success'
        self._errorsAndFailures = ""
        self._startTime = 0.0
        self.params=""

    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):  #  CONSIDER  why are there 2 startTests in here?
        self._startTime = time.time()
        test._extraXML = ''
        test._extraAssertions = []
        unittest.TestResult.startTest(self, test)
        self.stream.write('<testcase classname="%s' % test.__class__.__name__ + '" name="%s' % test.id().split('.')[-1] + '"')
        desc = test.shortDescription()

        if desc:
            desc = _cleanHTML(desc)
            self.stream.write(' desc="%s"' % desc)

    def stopTest(self, test):
        stopTime = time.time()
        deltaTime = stopTime - self._startTime
        unittest.TestResult.stopTest(self, test)
        self.stream.write(' time="%.3f"' % deltaTime)
        self.stream.write('>')
        if self._lastWas != 'success':
            if self._lastWas == 'error':
                self.stream.write(self._errorsAndFailures)
            elif self._lastWas == 'failure':
                self.stream.write(self._errorsAndFailures)
            else:
                assert(False)

        seen = {}

        for assertion in test._extraAssertions:
            if not seen.has_key(assertion):
                self._addAssertion(assertion[:110]) # :110 avoids tl;dr TODO use a lexical truncator
                seen[assertion] = True

        self.stream.write('</testcase>')
        self._errorsAndFailures = ""

        if test._extraXML != '':
            self.stream.write(test._extraXML)

    def _addAssertion(self, diagnostic):
        diagnostic = _cleanHTML(diagnostic)
        self.stream.write('<assert>' + diagnostic + '</assert>')

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self._lastWas = 'success'

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        if err[0] is KeyboardInterrupt:
            self.shouldStop = 1
        self._lastWas = 'error'
        self._errorsAndFailures += '<error type="%s">' % err[0].__name__
        for line in apply(traceback.format_exception, err):
           for l in line.split("\n")[:-1]:
              self._errorsAndFailures += escape(l)
        self._errorsAndFailures += "</error>"

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if err[0] is KeyboardInterrupt:
            self.shouldStop = 1
        self._lastWas = 'failure'
        self._errorsAndFailures += '<failure type="%s">' % err[0].__name__
        for line in apply(traceback.format_exception, err):
           for l in line.split("\n")[:-1]:
              self._errorsAndFailures += escape(l)
        self._errorsAndFailures += "</failure>"

    def printErrors(self):
        pass #assert False

    def printErrorList(self, flavour, errors):
        assert False

def _cleanHTML(whut):
    return whut.replace('"', '&quot;'). \
                replace('<', '&lt;').  \
                replace('>', '&gt;')

########NEW FILE########
__FILENAME__ = unittest
#!/usr/bin/env python
'''
Copyright (c) Members of the EGEE Collaboration. 2004. 
http://www.eu-egee.org

File: unittest.py

Authors: Marc-Elian Begin <Marc-Elian.Begin@cern.ch>

Version info: $Id: unittest.py,v 1.5 2004/10/20 21:22:08 mbegin Exp $
Release: $Name:  $

Revision history:
$Log: unittest.py,v $
Revision 1.5  2004/10/20 21:22:08  mbegin
Attempted to create a generic set of Python tasks, and refactored accordingly

Revision 1.4  2004/10/19 17:56:46  mbegin
Refactoring and fixed bug on total testsuite test time

Revision 1.3  2004/10/19 16:40:54  mbegin
Removed requirement for Python 2.3. Now works with 2.2

Revision 1.2  2004/09/10 12:45:38  mbegin
Upgraded unittest.py such that the new 'writeParameter' method writes xml
elements in the system-out element of the test report.  The new util.py file
provides a function to print the name/value pair for a given test report.

Revision 1.1.1.1  2004/07/22 13:07:25  leanne
Initial import of unit testing tools 



Python unit testing framework, based on Erich Gamma's JUnit and Kent Beck's
Smalltalk testing framework.

This module contains the core framework classes that form the basis of
specific test cases and suites (TestCase, TestSuite etc.), and also a
text-based utility class for running the tests and reporting the results
(TextTestRunner).

Simple usage:

    import unittest

    class IntegerArithmenticTestCase(unittest.TestCase):
        def testAdd(self):  ## test method names begin 'test*'
            self.assertEquals((1 + 2), 3)
            self.assertEquals(0 + 1, 1)
        def testMultiply(self);
            self.assertEquals((0 * 10), 0)
            self.assertEquals((5 * 8), 40)

    if __name__ == '__main__':
        unittest.main()

Further information is available in the bundled documentation, and from

  http://pyunit.sourceforge.net/

Copyright (c) 1999, 2000, 2001 Steve Purcell
This module is free software, and you may redistribute it and/or modify
it under the same terms as Python itself, so long as this copyright message
and disclaimer are retained in their original form.

IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF
THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.

THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS,
AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
'''

__author__ = "Steve Purcell"
__email__ = "stephen_purcell at yahoo dot com"
__version__ = "$Revision: 1.5 $"[11:-2]

import time
import sys
import traceback
import string
import os
import types

##############################################################################
# Test framework core
##############################################################################

class TestResult:
    """Holder for test result information.

    Test results are automatically managed by the TestCase and TestSuite
    classes, and do not need to be explicitly manipulated by writers of tests.

    Each instance holds the total number of tests run, and collections of
    failures and errors that occurred among those test runs. The collections
    contain tuples of (testcase, exceptioninfo), where exceptioninfo is a
    tuple of values as returned by sys.exc_info().
    """
    def __init__(self):
        self.failures = []
        self.errors = []
        self.testsRun = 0
        self.shouldStop = 0
        self.params = ""

    def startTest(self, test):
        "Called when the given test is about to be run"
        self.testsRun = self.testsRun + 1

    def stopTest(self, test):
        "Called when the given test has been run"
        pass

    def addError(self, test, err):
        "Called when an error has occurred"
        self.errors.append((test, err))

    def addFailure(self, test, err):
        "Called when a failure has occurred"
        self.failures.append((test, err))

    def addSuccess(self, test):
        "Called when a test has completed successfully"
        pass

    def wasSuccessful(self):
        "Tells whether or not this result was a success"
        return len(self.failures) == len(self.errors) == 0

    def stop(self):
        "Indicates that the tests should be aborted"
        self.shouldStop = 1

    def __repr__(self):
        return "<%s run=%i errors=%i failures=%i>" % \
               (self.__class__, self.testsRun, len(self.errors),
                len(self.failures))


class TestCase:
    """A class whose instances are single test cases.

    By default, the test code itself should be placed in a method named
    'runTest'.

    If the fixture may be used for many test cases, create as
    many test methods as are needed. When instantiating such a TestCase
    subclass, specify in the constructor arguments the name of the test method
    that the instance is to execute.

    Test authors should subclass TestCase for their own tests. Construction
    and deconstruction of the test's environment ('fixture') can be
    implemented by overriding the 'setUp' and 'tearDown' methods respectively.

    If it is necessary to override the __init__ method, the base class
    __init__ method must always be called. It is important that subclasses
    should not change the signature of their __init__ method, since instances
    of the classes are instantiated automatically by parts of the framework
    in order to be run.
    """

    # This attribute determines which exception will be raised when
    # the instance's assertion methods fail; test methods raising this
    # exception will be deemed to have 'failed' rather than 'errored'

    failureException = AssertionError

    def __init__(self, methodName='runTest'):
        """Create an instance of the class that will use the named test
           method when executed. Raises a ValueError if the instance does
           not have a method with the specified name.
        """
        self.result = TestResult()
        try:
            self.__testMethodName = methodName
            testMethod = getattr(self, methodName)
            self.__testMethodDoc = testMethod.__doc__
        except AttributeError:
            raise ValueError, "no such test method in %s: %s" % \
                  (self.__class__, methodName)

    def setUp(self):
        "Hook method for setting up the test fixture before exercising it."
        pass

    def tearDown(self):
        "Hook method for deconstructing the test fixture after testing it."
        pass

    def countTestCases(self):
        return 1

#    def defaultTestResult(self):
#        return TestResult()

    def shortDescription(self):
        """Returns a one-line description of the test, or None if no
        description has been provided.

        The default implementation of this method returns the first line of
        the specified test method's docstring.
        """
        doc = self.__testMethodDoc
        return doc and string.strip(string.split(doc, "\n")[0]) or None

    def id(self):
        return "%s.%s" % (self.__class__, self.__testMethodName)

    def __str__(self):
        return "%s (%s)" % (self.__testMethodName, self.__class__)

    def __repr__(self):
        return "<%s testMethod=%s>" % \
               (self.__class__, self.__testMethodName)

    def run(self, result=None):
        if result is not None: self.result = result
        return self(result)

    def __call__(self, result=None):
        if result is not None: self.result = result
        result.startTest(self)
        testMethod = getattr(self, self.__testMethodName)
        try:
            try:
                self.setUp()
            except:
                result.addError(self,self.__exc_info())
                return

            ok = 0
            try:
                testMethod()
                ok = 1
            except self.failureException, e:
                result.addFailure(self,self.__exc_info())
            except:
                result.addError(self,self.__exc_info())

            try:
                self.tearDown()
            except:
                result.addError(self,self.__exc_info())
                ok = 0
            if ok: result.addSuccess(self)
        finally:
            result.stopTest(self)

    def debug(self):
        """Run the test without collecting errors in a TestResult"""
        self.setUp()
        getattr(self, self.__testMethodName)()
        self.tearDown()

    def __exc_info(self):
        """Return a version of sys.exc_info() with the traceback frame
           minimised; usually the top level of the traceback frame is not
           needed.
        """
        exctype, excvalue, tb = sys.exc_info()
        if sys.platform[:4] == 'java': ## tracebacks look different in Jython
            return (exctype, excvalue, tb)
        newtb = tb.tb_next
        if newtb is None:
            return (exctype, excvalue, tb)
        return (exctype, excvalue, newtb)

    def fail(self, msg=None):
        """Fail immediately, with the given message."""
        raise self.failureException, msg

    def failIf(self, expr, msg=None):
        "Fail the test if the expression is true."
        if expr: raise self.failureException, msg

    def failUnless(self, expr, msg=None):
        """Fail the test unless the expression is true."""
        if not expr: raise self.failureException, msg

    def failUnlessRaises(self, excClass, callableObj, *args, **kwargs):
        """Fail unless an exception of class excClass is thrown
           by callableObj when invoked with arguments args and keyword
           arguments kwargs. If a different type of exception is
           thrown, it will not be caught, and the test case will be
           deemed to have suffered an error, exactly as for an
           unexpected exception.
        """
        try:
            apply(callableObj, args, kwargs)
        except excClass:
            return
        else:
            if hasattr(excClass,'__name__'): excName = excClass.__name__
            else: excName = str(excClass)
            raise self.failureException, excName

    def failUnlessEqual(self, first, second, msg=None):
        """Fail if the two objects are unequal as determined by the '!='
           operator.
        """
        if first != second:
            raise self.failureException, (msg or '%s != %s' % (first, second))

    def failIfEqual(self, first, second, msg=None):
        """Fail if the two objects are equal as determined by the '=='
           operator.
        """
        if first == second:
            raise self.failureException, (msg or '%s == %s' % (first, second))

    assertEqual = assertEquals = failUnlessEqual

    assertNotEqual = assertNotEquals = failIfEqual

    assertRaises = failUnlessRaises

    assert_ = failUnless

    def writeParameter(self, paramName, paramValue):
        testcase = self.__class__
        testmethod = self.id().split('.')[-1]
        self.result.params += "<parameter name='%s' value='%s' testcase='%s' testmethod='%s' /> " % (paramName, paramValue, testcase, testmethod)


class TestSuite:
    """A test suite is a composite test consisting of a number of TestCases.

    For use, create an instance of TestSuite, then add test case instances.
    When all tests have been added, the suite can be passed to a test
    runner, such as TextTestRunner. It will run the individual test cases
    in the order in which they were added, aggregating the results. When
    subclassing, do not forget to call the base class constructor.
    """
    def __init__(self, tests=()):
        self._tests = []
        self.addTests(tests)

    def __repr__(self):
        return "<%s tests=%s>" % (self.__class__, self._tests)

    __str__ = __repr__

    def countTestCases(self):
        cases = 0
        for test in self._tests:
            cases = cases + test.countTestCases()
        return cases

    def addTest(self, test):
        self._tests.append(test)

    def addTests(self, tests):
        for test in tests:
            self.addTest(test)

    def run(self, result):
        return self(result)

    def __call__(self, result):
        for test in self._tests:
            if result.shouldStop:
                break
            test(result)
        return result

    def debug(self):
        """Run the tests without collecting errors in a TestResult"""
        for test in self._tests: test.debug()



class FunctionTestCase(TestCase):
    """A test case that wraps a test function.

    This is useful for slipping pre-existing test functions into the
    PyUnit framework. Optionally, set-up and tidy-up functions can be
    supplied. As with TestCase, the tidy-up ('tearDown') function will
    always be called if the set-up ('setUp') function ran successfully.
    """

    def __init__(self, testFunc, setUp=None, tearDown=None,
                 description=None):
        TestCase.__init__(self)
        self.__setUpFunc = setUp
        self.__tearDownFunc = tearDown
        self.__testFunc = testFunc
        self.__description = description

    def setUp(self):
        if self.__setUpFunc is not None:
            self.__setUpFunc()

    def tearDown(self):
        if self.__tearDownFunc is not None:
            self.__tearDownFunc()

    def runTest(self):
        self.__testFunc()

    def id(self):
        return self.__testFunc.__name__

    def __str__(self):
        return "%s (%s)" % (self.__class__, self.__testFunc.__name__)

    def __repr__(self):
        return "<%s testFunc=%s>" % (self.__class__, self.__testFunc)

    def shortDescription(self):
        if self.__description is not None: return self.__description
        doc = self.__testFunc.__doc__
        return doc and string.strip(string.split(doc, "\n")[0]) or None



##############################################################################
# Locating and loading tests
##############################################################################

class TestLoader:
    """This class is responsible for loading tests according to various
    criteria and returning them wrapped in a Test
    """
    testMethodPrefix = 'test'
    sortTestMethodsUsing = cmp
    suiteClass = TestSuite

    def loadTestsFromTestCase(self, testCaseClass):
        """Return a suite of all tests cases contained in testCaseClass"""
        return self.suiteClass(map(testCaseClass,
                                   self.getTestCaseNames(testCaseClass)))

    def loadTestsFromModule(self, module):
        """Return a suite of all tests cases contained in the given module"""
        tests = []
        for name in dir(module):
            obj = getattr(module, name)
            if type(obj) == types.ClassType and issubclass(obj, TestCase):
                tests.append(self.loadTestsFromTestCase(obj))
        return self.suiteClass(tests)

    def loadTestsFromName(self, name, module=None):
        """Return a suite of all tests cases given a string specifier.

        The name may resolve either to a module, a test case class, a
        test method within a test case class, or a callable object which
        returns a TestCase or TestSuite instance.

        The method optionally resolves the names relative to a given module.
        """
        parts = string.split(name, '.')
        if module is None:
            if not parts:
                raise ValueError, "incomplete test name: %s" % name
            else:
                parts_copy = parts[:]
                while parts_copy:
                    try:
                        module = __import__(string.join(parts_copy,'.'))
                        break
                    except ImportError:
                        del parts_copy[-1]
                        if not parts_copy: raise
                parts = parts[1:]
        obj = module
        for part in parts:
            obj = getattr(obj, part)

        import unittest
        if type(obj) == types.ModuleType:
            return self.loadTestsFromModule(obj)
        elif type(obj) == types.ClassType and issubclass(obj, unittest.TestCase):
            return self.loadTestsFromTestCase(obj)
        elif type(obj) == types.UnboundMethodType:
            return obj.im_class(obj.__name__)
        elif callable(obj):
            test = obj()
            if not isinstance(test, unittest.TestCase) and \
               not isinstance(test, unittest.TestSuite):
                raise ValueError, \
                      "calling %s returned %s, not a test" % (obj,test)
            return test
        else:
            raise ValueError, "don't know how to make test from: %s" % obj

    def loadTestsFromNames(self, names, module=None):
        """Return a suite of all tests cases found using the given sequence
        of string specifiers. See 'loadTestsFromName()'.
        """
        suites = []
        for name in names:
            suites.append(self.loadTestsFromName(name, module))
        return self.suiteClass(suites)

    def getTestCaseNames(self, testCaseClass):
        """Return a sorted sequence of method names found within testCaseClass
        """
        testFnNames = filter(lambda n,p=self.testMethodPrefix: n[:len(p)] == p,
                             dir(testCaseClass))
        for baseclass in testCaseClass.__bases__:
            for testFnName in self.getTestCaseNames(baseclass):
                if testFnName not in testFnNames:  # handle overridden methods
                    testFnNames.append(testFnName)
        if self.sortTestMethodsUsing:
            testFnNames.sort(self.sortTestMethodsUsing)
        return testFnNames



defaultTestLoader = TestLoader()


##############################################################################
# Patches for old functions: these functions should be considered obsolete
##############################################################################

def _makeLoader(prefix, sortUsing, suiteClass=None):
    loader = TestLoader()
    loader.sortTestMethodsUsing = sortUsing
    loader.testMethodPrefix = prefix
    if suiteClass: loader.suiteClass = suiteClass
    return loader

def getTestCaseNames(testCaseClass, prefix, sortUsing=cmp):
    return _makeLoader(prefix, sortUsing).getTestCaseNames(testCaseClass)

def makeSuite(testCaseClass, prefix='test', sortUsing=cmp, suiteClass=TestSuite):
    return _makeLoader(prefix, sortUsing, suiteClass).loadTestsFromTestCase(testCaseClass)

def findTestCases(module, prefix='test', sortUsing=cmp, suiteClass=TestSuite):
    return _makeLoader(prefix, sortUsing, suiteClass).loadTestsFromModule(module)


##############################################################################
# Text UI
##############################################################################

class _WritelnDecorator:
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        return getattr(self.stream,attr)

    def writeln(self, *args):
        if args: apply(self.write, args)
        self.write('\n') # text-mode streams translate to \r\n if needed

class _XmlTextTestResult(TestResult):
    """A test result class that can print xml formatted text results to a stream.

    Used by XmlTextTestRunner.
    """
    def __init__(self, stream, descriptions, verbosity):
        TestResult.__init__(self)
        self.stream = _WritelnDecorator(stream)
        self.showAll = verbosity > 1
        self.descriptions = descriptions
        self._lastWas = 'success'
        self._errorsAndFailures = ""
        self._startTime = 0.0

    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        self._startTime = time.time()
        TestResult.startTest(self, test)
        self.stream.write('<testcase classname="%s' % test.__class__ + '" name="%s' % test.id().split('.')[-1] + '"')

    def stopTest(self, test):
        stopTime = time.time()
        deltaTime = stopTime - self._startTime
        TestResult.stopTest(self, test)
        self.stream.write(' time="%.3f"' % deltaTime)
        if self._lastWas == 'success':
            self.stream.write('/>')
        else:
            self.stream.write('>')
            if self._lastWas == 'error':
                self.stream.write(self._errorsAndFailures)
            elif self._lastWas == 'failure':
                self.stream.write(self._errorsAndFailures)
            else:
                assert(false)
            self.stream.write('</testcase>')
        self._errorsAndFailures = ""

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self._lastWas = 'success'

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        if err[0] is KeyboardInterrupt:
            self.shouldStop = 1
        self._lastWas = 'error'
        self._errorsAndFailures += '<error type="%s">' % err[0]
        for line in apply(traceback.format_exception, err):
           for l in string.split(line,"\n")[:-1]:
              self._errorsAndFailures += "%s" % l
        self._errorsAndFailures += "</error>"

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        if err[0] is KeyboardInterrupt:
            self.shouldStop = 1
        self._lastWas = 'failure'
        self._errorsAndFailures += '<failure type="%s">' % err[0]
        for line in apply(traceback.format_exception, err):
           for l in string.split(line,"\n")[:-1]:
              self._errorsAndFailures += "%s" % l
        self._errorsAndFailures += "</failure>"

    def printErrors(self):
        assert false

    def printErrorList(self, flavour, errors):
        assert false

class _TextTestResult(TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by TextTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, descriptions, verbosity):
        TestResult.__init__(self)
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions

    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        TestResult.startTest(self, test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write('.')

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write('E')
        if err[0] is KeyboardInterrupt:
            self.shouldStop = 1

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
        elif self.dots:
            self.stream.write('F')

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
            self.stream.writeln(self.separator2)
            for line in apply(traceback.format_exception, err):
                for l in string.split(line,"\n")[:-1]:
                    self.stream.writeln("%s" % l)


class TextTestRunner:
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1):
        self.stream = _WritelnDecorator(stream)
        self.descriptions = descriptions
        self.verbosity = verbosity

    def _makeResult(self):
        return _TextTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = float(stopTime - startTime)
        result.printErrors()
        self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run == 1 and "" or "s", timeTaken))
        self.stream.writeln()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        else:
            self.stream.writeln("OK")
        return result

class XmlTextTestRunner:
    """A test runner class that displays results in xml form.

    The format is compatible with the Ant junit task xml format.
    """
    
    class _StdOut:
        def __init__(self,std):
            self.reset()
            self._std = std
            return
        
        def write(self, string):
            self._string += string
            self._std.write(string)
            return

        def read(self):
            return self._string
            
        def reset(self):
            self._string = ""

    class _StringStream:
        def __init__(self):
            self.reset()
            return
        
        def write(self, string):
            self._string += string
            return

        def read(self):
            return self._string

        def reset(self):
            self._string = ""
        
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1):
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.stdout = self._StdOut(sys.stdout)
        sys.stdout = self.stdout
        self.stderr = self._StdOut(sys.stderr)
        sys.stderr = self.stderr
        self.testResults = self._StringStream()
        self.totalTime = 0.0
        self.output = None

    def _openOutputFile(self, fileName):
        
        if not os.path.isdir(os.path.join("temp", "xml")): os.makedirs(os.path.join("temp", "xml"))
        
        self.outputFileName = 'temp/xml/test_output.xml'
        self.output = open(self.outputFileName,'w')

    def _makeResult(self):
        return _XmlTextTestResult(self.testResults, self.descriptions, self.verbosity)

    def _resetBuffers(self):
        self.testResults.reset()
        
    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        for t in test._tests:
            # get the name of the unit test file name (!!!)
            size = len(sys.argv[0])
            if sys.argv[0].endswith('.py'):
                (filePath,fileName) = os.path.split(sys.argv[0])
                fileName = fileName.split('.')[0]
            else:
                fileName = "%s" % string.split("%s" % t._tests[0]._tests[0].__class__,'.')[0]
            self._openOutputFile(fileName)
            startTime = time.time()
            t(result)
            stopTime = time.time()
            timeTaken = float(stopTime - startTime)
            self.totalTime += timeTaken
        self._writeReport(result,self.totalTime)
        # ??? this line
        run = result.testsRun
        return result

    def _writeReport(self, result, timeTaken):
        if self.output != None:
            self.output.write('<testsuite ')
            self.output.write('errors="%i" ' % len(result.errors))
            self.output.write('failures="%i" ' % len(result.failures))
            self.output.write('name="%s" ' % "")
            self.output.write('tests="%i" ' % result.testsRun)
            self.output.write('time="%.3f" ' % timeTaken)
            self.output.write(' >')
            self.output.write(self.testResults.read())
            self.output.write('<system-out>')
            self.output.write(result.params)
            self.output.write('<![CDATA[')
            self.output.write(self.stdout.read())
            self.output.write(']]></system-out>')
            self.output.write('<system-err><![CDATA[')
            self.output.write(self.stderr.read())
            self.output.write(']]></system-err>')
            self.output.write('</testsuite>')
            self.output.close()
            self._resetBuffers()
            # Write console report
            print '======================================================================'
            print 'Ran %d test%s in %.3fs' % (result.testsRun, result.testsRun == 1 and '' or 's', timeTaken)
            print '----------------------------------------------------------------------'
            print 'See generated report:', self.outputFileName,'\n'
            msg = ''
            if not result.wasSuccessful():
                msg += "FAILED ("
                failed, errored = map(len, (result.failures, result.errors))
                if failed:
                    msg += "failures=%d" % failed
                if errored:
                    if failed: msg += ", "
                    msg += "errors=%d" % errored
                msg += ")"
            else:
                msg += "OK"
            print msg
        else:
            print '======================================================================'
            print 'No tests to run'
            print '----------------------------------------------------------------------'
        return

##############################################################################
# Facilities for running tests from the command line
##############################################################################

class TestProgram:
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """
    USAGE = """\
Usage: %(progName)s [options] [test] [...]

Options:
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output
  -t, --text       Text output (classic output) - default
  -x, --xml        XML output (same format as JUnit)

Examples:
  %(progName)s                               - run default set of tests
  %(progName)s MyTestSuite                   - run suite 'MyTestSuite'
  %(progName)s MyTestCase.testSomething      - run MyTestCase.testSomething
  %(progName)s MyTestCase                    - run all 'test*' test methods
                                               in MyTestCase
"""
    def __init__(self, module='__main__', defaultTest=None,
                 argv=None, testRunner=None, testLoader=defaultTestLoader):
        if type(module) == type(''):
            self.module = __import__(module)
            for part in string.split(module,'.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        if argv is None:
            argv = sys.argv
        self.verbosity = 2
        self.xmlReport = False
        self.defaultTest = defaultTest
        self.testRunner = testRunner
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        self.parseArgs(argv)
        self.runTests()

    def usageExit(self, msg=None):
        if msg: print msg
        print self.USAGE % self.__dict__
        sys.exit(2)

    def parseArgs(self, argv):
        import getopt
        try:
            options, args = getopt.getopt(argv[1:], 'hHvqxt',
                                          ['help','verbose','quiet','xml','text'])
        except getopt.error, msg:
            self.usageExit(msg)
        for opt, value in options:
            if opt in ('-h','-H','--help'):
                self.usageExit()
            if opt in ('-q','--quiet'):
                self.verbosity = 0
            if opt in ('-v','--verbose'):
                self.verbosity = 2
            if opt in ('-x','--xml'):
                self.xmlReport = True
            if opt in ('-t','--text'):
                self.xmlReport = False
        if os.getenv('PYUNITXMLOUTPUT'):
            self.xmlReport = True
        if len(args) == 0 and self.defaultTest is None:
            self.test = self.testLoader.loadTestsFromModule(self.module)
            return
        if len(args) > 0:
            self.testNames = args
        else:
            print 'Running default test:%s' % self.defaultTest
            self.testNames = (self.defaultTest,)
        self.createTests()

    def createTests(self):
        self.test = self.testLoader.loadTestsFromNames(self.testNames,
                                                       self.module)

    def runTests(self):
        if self.testRunner is None:
            if self.xmlReport == True:
                self.testRunner = XmlTextTestRunner(verbosity=self.verbosity)
            else:
                self.testRunner = TextTestRunner(verbosity=self.verbosity)
        result = self.testRunner.run(self.test)
        sys.exit(not result.wasSuccessful())

main = TestProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)

########NEW FILE########
__FILENAME__ = twill
# Test classes inherit from the Django TestCase
from django.test import TestCase

# Twill provides a simple DSL for a number of functional tasks
import twill as twill
from twill import commands as tc

class TwillCommon(TestCase):
    """
    A Base class for using with Twill commands. Provides a few helper methods and setup.
    """
    def setUp(self):
        "Run before all tests in this class, sets the output to the console"
        twill.set_output(StringIO())

    def find(self,regex):
        """
        By default Twill commands throw exceptions rather than failures when 
        an assertion fails. Here we wrap the Twill find command and return
        the expected response along with a helpful message.     
        """
        try:
            tc.go(self.url)
            tc.find(regex) 
        except TwillAssertionError:
            self.fail("No match to '%s' on %s" % (regex, self.url))

    def code(self,status):
        """
        By default Twill commands throw exceptions rather than failures when 
        an assertion fails. Here we wrap the Twill code command and return
        the expected response along with a helpful message.     
        """
        try:
            tc.go(self.url)
            tc.code(status)
        except TwillAssertionError:
            self.fail("%s did not return a %s" % (self.url, status))
########NEW FILE########
