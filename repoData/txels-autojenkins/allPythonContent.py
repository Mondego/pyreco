__FILENAME__ = ajk_version
__version__ = '0.9.0'

########NEW FILE########
__FILENAME__ = jobs
import sys
import time
import requests
from jinja2 import Template


API = 'api/python'
NEWJOB = '{0}/createItem'
JOB_URL = '{0}/job/{1}'
DELETE = '{0}/job/{1}/doDelete'
BUILD = '{0}/job/{1}/build'
CONFIG = '{0}/job/{1}/config.xml'
JOBINFO = '{0}/job/{1}/' + API
BUILDINFO = '{0}/job/{1}/{2}/' + API
LIST = '{0}/' + API
LAST_SUCCESS = '{0}/job/{1}/lastSuccessfulBuild/' + API
TEST_REPORT = '{0}/job/{1}/lastSuccessfulBuild/testReport/' + API
LAST_BUILD = '{0}/job/{1}/lastBuild/' + API
LAST_REPORT = '{0}/job/{1}/lastBuild/testReport/' + API
ENABLE = '{0}/job/{1}/enable'
DISABLE = '{0}/job/{1}/disable'


class HttpStatusError(Exception):
    pass


class HttpNotFoundError(HttpStatusError):
    pass


HTTP_ERROR_MAP = {
    404: HttpNotFoundError,
}


def _validate(response):
    """
    Verify the status code of the response and raise exception on codes > 400.
    """
    message = 'HTTP Status: {0}'.format(response.status_code)
    if response.status_code >= 400:
        print(message)
        exception_cls = HTTP_ERROR_MAP.get(response.status_code,
                                           HttpStatusError)
        raise exception_cls(message)
    return response


class Jenkins(object):
    """Main class to interact with a Jenkins server."""

    def __init__(self, base_url, auth=None, verify_ssl_cert=True):
        self.ROOT = base_url
        self.auth = auth
        self.verify_ssl_cert = verify_ssl_cert

    def _url(self, command, *args):
        """
        Build the proper Jenkins URL for the command.
        """
        return command.format(self.ROOT, *args)

    def _other_url(self, root, command, *args):
        """
        Build the proper Jenkins URL for the command.
        """
        return command.format(root, *args)

    def _http_get(self, url, **kwargs):
        """
        Perform an HTTP GET request.

        This will add required authentication and SSL verification arguments.
        """
        response = requests.get(url,
                                auth=self.auth,
                                verify=self.verify_ssl_cert,
                                **kwargs)
        return _validate(response)

    def _http_post(self, url, **kwargs):
        """
        Perform an HTTP POST request.

        This will add required authentication and SSL verification arguments.
        """
        response = requests.post(url,
                                 auth=self.auth,
                                 verify=self.verify_ssl_cert,
                                 **kwargs)
        return _validate(response)

    def _build_get(self, url_pattern, *args, **kwargs):
        """
        Build proper URL from pattern and args, and perform an HTTP GET.
        """
        return self._http_get(self._url(url_pattern, *args), **kwargs)

    def _build_post(self, url_pattern, *args, **kwargs):
        """
        Build proper URL from pattern and args, and perform an HTTP POST.
        """
        return self._http_post(self._url(url_pattern, *args), **kwargs)

    def all_jobs(self):
        """
        Get a list of tuples with (name, color) of all jobs in the server.

        Color is ``blue``, ``yellow`` or ``red`` depending on build results
        (SUCCESS, UNSTABLE or FAILED).
        """
        response = self._build_get(LIST)
        jobs = eval(response.content).get('jobs', [])
        return [(job['name'], job['color']) for job in jobs]

    def job_url(self, jobname):
        """
        Get the human-browseable URL for a job.
        """
        return self._url(JOB_URL, jobname)

    def job_info(self, jobname):
        """
        Get all information for a job as a Python object (dicts & lists).
        """
        response = self._build_get(JOBINFO, jobname)
        return eval(response.content)

    def build_info(self, jobname, build_number=None):
        """
        Get information for a build of a job.

        If no build number is specified, defaults to the most recent build.
        """
        if build_number is not None:
            args = (BUILDINFO, jobname, build_number)
        else:
            args = (LAST_BUILD, jobname)
        response = self._build_get(*args)
        return eval(response.content)

    def last_build_info(self, jobname):
        """
        Get information for last build of a job.
        """
        return self.build_info(jobname)

    def last_build_report(self, jobname):
        """
        Get full report of last build.
        """
        response = self._build_get(LAST_REPORT, jobname)
        return eval(response.content)

    def last_result(self, jobname):
        """
        Obtain results from last execution.
        """
        last_result_url = self.job_info(jobname)['lastBuild']['url']
        response = self._http_get(last_result_url + API)
        return eval(response.content)

    def last_success(self, jobname):
        """
        Return information about the last successful build.
        """
        response = self._build_get(LAST_SUCCESS, jobname)
        return eval(response.content)

    def get_config_xml(self, jobname):
        """
        Get the ``config.xml`` file that contains the job definition.
        """
        response = self._build_get(CONFIG, jobname)
        return response.content

    def set_config_xml(self, jobname, config):
        """
        Replace the ``config.xml`` of an existing job.
        """
        return self._build_post(CONFIG, jobname,
                                data=config,
                                headers={'Content-Type': 'application/xml'})

    def create(self, jobname, config_file, **context):
        """
        Create a job from a configuration file.
        """
        params = {'name': jobname}
        with open(config_file) as file:
            content = file.read()

        template = Template(content)
        content = template.render(**context)

        return self._build_post(NEWJOB,
                                data=content,
                                params=params,
                                headers={'Content-Type': 'application/xml'})

    def create_copy(self, jobname, template_job, enable=True, **context):
        """
        Create a job from a template job.
        """
        config = self.get_config_xml(template_job)

        # remove stupid quotes added by Jenkins
        config = config.replace('>&quot;{{', '>{{')
        config = config.replace('}}&quot;<', '}}<')

        template_config = Template(config)
        config = template_config.render(**context)
        if enable:
            config = config.replace('<disabled>true</disabled>',
                                    '<disabled>false</disabled>')

        return self._build_post(NEWJOB,
                                data=config,
                                params={'name': jobname},
                                headers={'Content-Type': 'application/xml'})

    def transfer(self, jobname, to_server):
        """
        Copy a job to another server.
        """
        config = self.get_config_xml(jobname)
        return self._http_post(self._other_url(to_server, NEWJOB),
                               data=config,
                               params={'name': jobname},
                               headers={'Content-Type': 'application/xml'})

    def copy(self, jobname, copy_from='template'):
        """
        Copy a job from another one (by default from one called ``template``).
        """
        params = {'name': jobname, 'mode': 'copy', 'from': copy_from}
        return self._build_post(NEWJOB, params=params)

    def build(self, jobname, wait=False, grace=10):
        """
        Trigger Jenkins to build a job.

        :param wait:
            If ``True``, wait until job completes building before returning
        """
        response = self._build_post(BUILD, jobname)
        if not wait:
            return response
        else:
            time.sleep(grace)
            self.wait_for_build(jobname)
            return self.last_result(jobname)

    def delete(self, jobname):
        """
        Delete a job.
        """
        return self._build_post(DELETE, jobname)

    def enable(self, jobname):
        """
        Trigger Jenkins to enable a job.
        """
        return self._build_post(ENABLE, jobname)

    def disable(self, jobname):
        """
        Trigger Jenkins to disable a job.
        """
        return self._build_post(DISABLE, jobname)

    def is_building(self, jobname):
        """
        Check if a job is building
        """
        return self.last_result(jobname).get('building', True)

    def wait_for_build(self, jobname, poll_interval=3):
        """
        Wait until job has finished building
        """
        while (self.is_building(jobname)):
            time.sleep(poll_interval)
            sys.stdout.write('.')
            sys.stdout.flush()
        print('')

########NEW FILE########
__FILENAME__ = run
import optparse
import sys

from autojenkins import Jenkins

COLOR_MEANING = {
    'blue': ('1;32', 'SUCCESS'),
    'green': ('1;32', 'SUCCESS'),
    'red': ('1;31', 'FAILED'),
    'yellow': ('1;33', 'UNSTABLE'),
    'aborted': ('1;37', 'ABORTED'),
    'disabled': ('0;37', 'DISABLED'),
    'grey': ('1;37', 'NOT BUILT'),
    'notbuilt': ('1;37', 'NOT BUILT'),
}


def create_opts_parser(command, params="[jobname] [options]"):
    """
    Create parser for command-line options
    """
    usage = "Usage: %prog host " + params
    desc = 'Run autojenkins to {0}.'.format(command)
    parser = optparse.OptionParser(description=desc, usage=usage)
    parser.add_option('-u', '--user',
                      help='username')
    parser.add_option('-p', '--password',
                      help='password or token')
    return parser


def get_variables(options):
    """
    Read all variables and values from ``-Dvariable=value`` options
    """
    split_eq = lambda x: x.split('=')
    data = dict(map(split_eq, options.D))
    return data


def get_auth(options):
    """
    Return a tuple of (user, password) or None if no authentication
    """
    if hasattr(options, 'user'):
        return (options.user, getattr(options, 'password', None))
    else:
        return None


def create_job(host, jobname, options):
    """
    Create a new job
    """
    data = get_variables(options)

    print ("""
    Creating job '{0}' from template '{1}' with:
      {2}
    """.format(jobname, options.template, data))

    jenkins = Jenkins(host, auth=get_auth(options))
    response = jenkins.create_copy(jobname, options.template, **data)
    if response.status_code == 200 and options.build:
        print('Triggering build.')
        jenkins.build(jobname)
    print ('Job URL: {0}'.format(jenkins.job_url(jobname)))
    return response.status_code


def build_job(host, jobname, options):
    """
    Trigger build for an existing job.

    If the wait option is specified, wait until build completion

    :returns:

        A boolean value indicating success:

         * If wait: ``True`` if build was successful, ``False`` otherwise
         * If not wait: ``True`` if HTTP status code is not an error code
    """
    print ("Start building job '{0}'".format(jobname))

    jenkins = Jenkins(host, auth=get_auth(options))
    response = jenkins.build(jobname, wait=options.wait)
    if options.wait:
        result = response['result']
        print('Result = "{0}"'.format(result))
        return result == 'SUCCESS'
    else:
        return response.status_code < 400


def delete_jobs(host, jobnames, options):
    """
    Delete existing jobs.
    """
    jenkins = Jenkins(host, auth=get_auth(options))
    for jobname in jobnames:
        print ("Deleting job '{0}'".format(jobname))
        response = jenkins.delete(jobname)
        print(response.status_code)


def list_jobs(host, options, color=True, raw=False):
    """
    List all jobs
    """
    if raw:
        FORMAT = "{1}"
        position = 0
    elif color:
        FORMAT = "\033[{0}m{1}\033[0m"
        position = 0
    else:
        FORMAT = "{0:<10} {1}"
        position = 1
    if not raw:
        print ("All jobs in {0}".format(host))
    jenkins = Jenkins(host, auth=get_auth(options))
    jobs = jenkins.all_jobs()
    for name, color in jobs:
        if '_' in color:
            color = color.split('_')[0]
            building = True
        else:
            building = False
        prefix = '' if raw else '* ' if building else '  '
        out = COLOR_MEANING[color][position]
        print(prefix + FORMAT.format(out, name))


class Commands:
    @staticmethod
    def create():
        parser = create_opts_parser('create a job')
        parser.add_option('-D', metavar='VAR=VALUE',
                          action="append",
                          help='substitution variables to be used in the '
                               'template')
        parser.add_option('-t', '--template', default='template',
                          help='the template job to copy from')
        parser.add_option('-b', '--build',
                          action="store_true", dest="build", default=False,
                          help='start a build right after creation')

        (options, args) = parser.parse_args()

        if len(args) == 2:
            host, jobname = args
            create_job(host, jobname, options)
        else:
            parser.print_help()

    @staticmethod
    def build():
        parser = create_opts_parser('build a job')
        parser.add_option('-w', '--wait',
                          action="store_true", dest="wait", default=False,
                          help='wait until the build completes')

        (options, args) = parser.parse_args()

        if len(args) == 2:
            host, jobname = args
            success = build_job(host, jobname, options)
            if not success:
                sys.exit(1)
        else:
            parser.print_help()

    @staticmethod
    def delete():
        parser = create_opts_parser('delete one or more jobs',
                                    params="[jobname]+ [options]")

        (options, args) = parser.parse_args()

        if len(args) >= 2:
            host, jobnames = args[0], args[1:]
            delete_jobs(host, jobnames, options)
        else:
            parser.print_help()

    @staticmethod
    def list():
        parser = create_opts_parser('list all jobs', params='')
        parser.add_option('-n', '--no-color',
                          action="store_true", dest="color", default=False,
                          help='do not use colored output')
        parser.add_option('-r', '--raw',
                          action="store_true", dest="raw", default=False,
                          help='print raw list of jobs')

        (options, args) = parser.parse_args()

        if len(args) == 1:
            host, = args
            list_jobs(host, options, not options.color, options.raw)
        else:
            parser.print_help()

########NEW FILE########
__FILENAME__ = test_run
from mock import Mock, patch
from nose.tools import assert_equals

from autojenkins.run import delete_jobs


@patch('autojenkins.run.Jenkins')
def test_delete_jobs(jenkins):
    jenkins.return_value = Mock()
    delete_jobs('http://jenkins', ['hello', 'bye'], None)
    jenkins.assert_called_with('http://jenkins', auth=None)
    assert_equals(2, jenkins.return_value.delete.call_count)
    assert_equals(
        [(('hello',), {}), (('bye',), {})],
        jenkins.return_value.delete.call_args_list)


@patch('autojenkins.run.Jenkins')
def test_delete_jobs_authenticated(jenkins):
    jenkins.return_value = Mock()
    options = Mock()
    options.user = 'carles'
    options.password = 'secret'
    delete_jobs('http://jenkins', ['hello'], options)
    jenkins.assert_called_with('http://jenkins', auth=('carles', 'secret'))
    assert_equals(1, jenkins.return_value.delete.call_count)
    assert_equals(
        [(('hello',), {})],
        jenkins.return_value.delete.call_args_list)

########NEW FILE########
__FILENAME__ = test_unit_jobs
from os import path
from unittest import TestCase

from ddt import ddt, data
from mock import Mock, patch

from autojenkins.jobs import Jenkins, HttpNotFoundError, HttpStatusError


fixture_path = path.dirname(__file__)


def load_fixture(name):
    with open(path.join(fixture_path, name)) as f:
        fixture = f.read()
    return fixture


def mock_response(fixture=None, status=200):
    response = Mock()
    if fixture is None:
        response.content = ''
    elif isinstance(fixture, dict):
        response.content = str(fixture)
    else:
        response.content = load_fixture(fixture)
    response.status_code = status
    return response


@ddt
@patch('autojenkins.jobs.requests')
class TestJenkins(TestCase):

    def setUp(self):
        super(TestJenkins, self).setUp()
        self.jenkins = Jenkins('http://jenkins')

    def test_all_jobs(self, requests):
        response = {'jobs': [{'name': 'job1', 'color': 'blue'}]}
        requests.get.return_value = mock_response(response)
        jobs = self.jenkins.all_jobs()
        requests.get.assert_called_once_with('http://jenkins/api/python',
                                             verify=True,
                                             auth=None)
        self.assertEqual(jobs, [('job1', 'blue')])

    def test_get_job_url(self, *args):
        url = self.jenkins.job_url('job123')
        self.assertEqual('http://jenkins/job/job123', url)

    def test_last_result(self, requests, *args):
        second_response = Mock(status_code=200)
        second_response.content = "{'result': 23}"
        requests.get.side_effect = [
            mock_response('job_info.txt'), second_response
        ]
        response = self.jenkins.last_result('name')
        self.assertEqual(23, response['result'])
        self.assertEqual(
            (('https://builds.apache.org/job/Solr-Trunk/1783/api/python',),
             {'auth': None, 'verify': True}),
            requests.get.call_args_list[1]
        )

    @data(
        ('job_info', 'job/{0}/api/python'),
        ('last_build_info', 'job/{0}/lastBuild/api/python'),
        ('last_build_report', 'job/{0}/lastBuild/testReport/api/python'),
        ('last_success', 'job/{0}/lastSuccessfulBuild/api/python'),
        ('get_config_xml', 'job/{0}/config.xml'),
    )
    def test_get_methods_with_jobname(self, case, requests):
        method, url = case
        requests.get.return_value = mock_response('{0}.txt'.format(method))
        response = getattr(self.jenkins, method)('name')
        requests.get.assert_called_once_with(
            'http://jenkins/' + url.format('name'),
            verify=True,
            auth=None)
        getattr(self, 'checks_{0}'.format(method))(response)

    def test_build_info(self, requests):
        url = 'job/name/3/api/python'
        requests.get.return_value = mock_response('last_build_info.txt')
        self.jenkins.build_info('name', 3)
        requests.get.assert_called_once_with(
            'http://jenkins/' + url,
            verify=True,
            auth=None)

    def check_result(self, response, route, value):
        for key in route:
            response = response[key]
        self.assertEqual(response, value)

    def check_results(self, response, values):
        for route, value in values:
            self.check_result(response, route, value)

    def checks_job_info(self, response):
        self.check_results(
            response,
            [(('color',), 'red'),
             (('lastSuccessfulBuild', 'number'), 1778),
             (('lastSuccessfulBuild', 'url'),
              'https://builds.apache.org/job/Solr-Trunk/1778/'),
            ])

    def checks_last_build_info(self, response):
        self.check_results(
            response,
            [(('timestamp',), 1330941036216L),
             (('number',), 1783),
             (('result',), 'FAILURE'),
             (('changeSet', 'kind'), 'svn'),
            ])

    def checks_last_build_report(self, response):
        self.check_results(
            response,
            [(('duration',), 692.3089),
             (('failCount',), 1),
             (('suites', 0, 'name'), 'org.apache.solr.BasicFunctionalityTest'),
            ])

    def checks_last_success(self, response):
        self.check_results(
            response,
            [(('result',), 'SUCCESS'),
             (('building',), False),
             (('artifacts', 0, 'displayPath'),
              'apache-solr-4.0-2012-02-29_09-07-30-src.tgz'),
            ])

    def checks_get_config_xml(self, response):
        self.assertTrue(response.startswith('<?xml'))
        self.assertTrue(response.endswith('</project>'))

    # TODO: test job creation, and set_config_xml

    def test_create(self, requests):
        requests.post.return_value = mock_response()
        config_xml = path.join(fixture_path, 'create_copy.txt')
        self.jenkins.create('job', config_xml, value='2')
        CFG = "<value>2</value><disabled>true</disabled>"
        requests.post.assert_called_once_with(
            'http://jenkins/createItem',
            auth=None,
            headers={'Content-Type': 'application/xml'},
            params={'name': 'job'},
            data=CFG,
            verify=True)

    def test_create_copy(self, requests):
        requests.get.return_value = mock_response('create_copy.txt')
        requests.post.return_value = mock_response()
        self.jenkins.create_copy('job', 'template', value='2')
        CFG = "<value>2</value><disabled>false</disabled>"
        requests.post.assert_called_once_with(
            'http://jenkins/createItem',
            auth=None,
            headers={'Content-Type': 'application/xml'},
            params={'name': 'job'},
            data=CFG,
            verify=True)

    def test_transfer(self, requests):
        requests.get.return_value = mock_response('transfer.txt')
        requests.post.return_value = mock_response()
        self.jenkins.transfer('job', 'http://jenkins2')
        CFG = load_fixture('transfer.txt')
        requests.post.assert_called_once_with(
            'http://jenkins2/createItem',
            auth=None,
            headers={'Content-Type': 'application/xml'},
            params={'name': 'job'},
            data=CFG,
            verify=True)

    @data(
        ('build', 'job/{0}/build'),
        ('delete', 'job/{0}/doDelete'),
        ('enable', 'job/{0}/enable'),
        ('disable', 'job/{0}/disable'),
    )
    def test_post_methods_with_jobname_no_data(self, case, requests):
        method, url = case
        # Jenkins API post methods return status 302 upon success
        requests.post.return_value = mock_response(status=302)
        response = getattr(self.jenkins, method)('name')
        self.assertEqual(302, response.status_code)
        requests.post.assert_called_once_with(
            'http://jenkins/' + url.format('name'),
            auth=None,
            verify=True)

    def test_set_config_xml(self, requests):
        requests.post.return_value = Mock(status_code=200)
        CFG = '<config>x</config>'
        response = self.jenkins.set_config_xml('name', CFG)
        # return value is a pass-trough
        self.assertEqual(requests.post.return_value, response)
        requests.post.assert_called_once_with(
            'http://jenkins/job/name/config.xml',
            headers={'Content-Type': 'application/xml'},
            data=CFG,
            auth=None,
            verify=True)

    @patch('autojenkins.jobs.time')
    @patch('autojenkins.jobs.Jenkins.last_result')
    @patch('autojenkins.jobs.Jenkins.wait_for_build')
    def test_build_with_wait(self, wait_for_build, last_result, time,
                             requests):
        """Test building a job synchronously"""
        requests.post.return_value = mock_response(status=302)
        last_result.return_value = {'result': 'HELLO'}
        result = self.jenkins.build('name', wait=True)
        self.assertEqual({'result': 'HELLO'}, result)
        requests.post.assert_called_once_with(
            'http://jenkins/job/name/build',
            auth=None,
            verify=True)
        last_result.assert_called_once_with('name')
        time.sleep.assert_called_once_with(10)

    @patch('autojenkins.jobs.time')
    @patch('autojenkins.jobs.sys')
    @patch('autojenkins.jobs.Jenkins.is_building')
    def test_wait_for_build(self, is_building, sys, time, requests):
        is_building.side_effect = [True, True, False]
        self.jenkins.wait_for_build('name')
        self.assertEqual(3, is_building.call_count)
        self.assertEqual(2, time.sleep.call_count)
        self.assertEqual(((3,), {}), time.sleep.call_args)

    @patch('autojenkins.jobs.Jenkins.last_result')
    @data(True, False)
    def test_is_building(self, building, last_result, _):
        last_result.return_value = {'building': building}
        result = self.jenkins.is_building('name')
        last_result.assert_called_once_with('name')
        self.assertEqual(building, result)

    def test_404_raises_http_not_found(self, requests):
        http404_response = Mock()
        http404_response.status_code = 404
        requests.get.return_value = http404_response
        with self.assertRaises(HttpNotFoundError):
            self.jenkins.last_build_info('job123')

    def test_500_raises_http_error(self, requests):
        http500_response = Mock()
        http500_response.status_code = 500
        requests.get.return_value = http500_response
        with self.assertRaises(HttpStatusError):
            self.jenkins.last_build_info('job123')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# AutoJenkins documentation build configuration file, created by
# sphinx-quickstart on Tue Nov  1 15:02:02 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, re

# Specific for readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
docs_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.split(docs_root)[0])

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'AutoJenkins'
copyright = u'2011, Carles Barrobés'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

from ajk_version import __version__
# The short X.Y version.
version = re.match('([0-9]+\.[0-9]+).*', __version__).group(1)
# The full version, including alpha/beta/rc tags.
release = __version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
if on_rtd:
    html_theme = 'default'
else:
    html_theme = 'sphinxdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'AutoJenkinsdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'AutoJenkins.tex', u'AutoJenkins Documentation',
   u'Carles Barrobés', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'autojenkins', u'AutoJenkins Documentation',
     [u'Carles Barrobés'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'AutoJenkins', u'AutoJenkins Documentation',
   u'Carles Barrobés', 'AutoJenkins', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'AutoJenkins'
epub_author = u'Carles Barrobés'
epub_publisher = u'Carles Barrobés'
epub_copyright = u'2011, Carles Barrobés'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
__FILENAME__ = build_wait
from autojenkins import Jenkins

j = Jenkins('http://jenkins.live')
result = j.build('mbf-order-dcs-us677_merge_dev_carles', wait=True)
print('Result = ' + result['result'])

########NEW FILE########
__FILENAME__ = demo_run
from datetime import datetime

from autojenkins import Jenkins


if __name__ == '__main__':
    j = Jenkins('https://builds.apache.org')
    jobs = j.all_jobs()
    print(jobs)
    for job, color in jobs:
        if color in ['red', 'blue', 'yellow']:
            full_info = j.job_info(job)
            last_build = j.last_build_info(job)
            when = datetime.fromtimestamp(last_build['timestamp'] / 1000)
        else:
            when = '(unknown)'
        print("{0!s:<19} {1:<6} {2}".format(when, color, job))

########NEW FILE########
