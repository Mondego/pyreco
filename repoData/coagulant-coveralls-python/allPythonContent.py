__FILENAME__ = api
# coding: utf-8
import json
import logging
import os
import re
import subprocess

import coverage
import requests
import yaml

from .reporter import CoverallReporter


log = logging.getLogger('coveralls')


class CoverallsException(Exception):
    pass


class Coveralls(object):
    config_filename = '.coveralls.yml'
    api_endpoint = 'https://coveralls.io/api/v1/jobs'
    default_client = 'coveralls-python'

    def __init__(self, **kwargs):
        """ Coveralls!

        * repo_token
          The secret token for your repository, found at the bottom of your repository's
           page on Coveralls.

        * service_name
          The CI service or other environment in which the test suite was run.
          This can be anything, but certain services have special features
          (travis-ci, travis-pro, or coveralls-ruby).

        * [service_job_id]
          A unique identifier of the job on the service specified by service_name.
        """
        self._data = None
        self.config = kwargs
        file_config = self.load_config() or {}
        repo_token = self.config.get('repo_token') or file_config.get('repo_token', None)
        if repo_token:
            self.config['repo_token'] = repo_token

        if os.environ.get('TRAVIS'):
            is_travis = True
            self.config['service_name'] = file_config.get('service_name', None) or 'travis-ci'
            self.config['service_job_id'] = os.environ.get('TRAVIS_JOB_ID')
        else:
            is_travis = False
            self.config['service_name'] = file_config.get('service_name') or self.default_client

        if os.environ.get('COVERALLS_REPO_TOKEN', None):
            self.config['repo_token'] = os.environ.get('COVERALLS_REPO_TOKEN')

        if not self.config.get('repo_token') and not is_travis:
            raise CoverallsException('You have to provide either repo_token in %s, or launch via Travis' % self.config_filename)

    def load_config(self):
        try:
            return yaml.safe_load(open(os.path.join(os.getcwd(), self.config_filename)))
        except (OSError, IOError):
            log.debug('Missing %s file. Using only env variables.', self.config_filename)
            return {}

    def wear(self, dry_run=False):
        """ run! """
        try:
            data = self.create_data()
        except coverage.CoverageException as e:
            return {'message': 'Failure to gather coverage: %s' % str(e)}
        try:
            json_string = json.dumps(data)
        except UnicodeDecodeError as e:
            log.error("ERROR: While preparing JSON received exception: %s" % e)
            self.debug_bad_encoding(data)
            raise
        if not dry_run:
            response = requests.post(self.api_endpoint, files={'json_file': json_string})
            try:
                result = response.json()
            except ValueError:
                result = {'message': 'Failure to submit data. Response [%(status)s]: %(text)s' % {
                    'status': response.status_code,
                    'text': response.text}}
        else:
            result = {}
        json_string = re.sub(r'"repo_token": "(.+?)"', '"repo_token": "[secure]"', json_string)
        log.debug(json_string)
        log.debug("==\nReporting %s files\n==\n" % len(data['source_files']))
        for source_file in data['source_files']:
            log.debug('%s - %s/%s' % (source_file['name'],
                                      sum(filter(None, source_file['coverage'])),
                                      len(source_file['coverage'])))
        return result

    def create_data(self):
        """ Generate object for api.
            Example json:
            {
                "service_job_id": "1234567890",
                "service_name": "travis-ci",
                "source_files": [
                    {
                        "name": "example.py",
                        "source": "def four\n  4\nend",
                        "coverage": [null, 1, null]
                    },
                    {
                        "name": "two.py",
                        "source": "def seven\n  eight\n  nine\nend",
                        "coverage": [null, 1, 0, null]
                    }
                ]
            }
        """
        if not self._data:
            self._data = {'source_files': self.get_coverage()}
            self._data.update(self.git_info())
            self._data.update(self.config)
        return self._data

    def get_coverage(self):
        workman = coverage.coverage(config_file=self.config.get('config_file', True))
        workman.load()
        workman._harvest_data()
        reporter = CoverallReporter(workman, workman.config)
        return reporter.report()

    def git_info(self):
        """ A hash of Git data that can be used to display more information to users.

            Example:
            "git": {
                "head": {
                    "id": "5e837ce92220be64821128a70f6093f836dd2c05",
                    "author_name": "Wil Gieseler",
                    "author_email": "wil@example.com",
                    "committer_name": "Wil Gieseler",
                    "committer_email": "wil@example.com",
                    "message": "depend on simplecov >= 0.7"
                },
                "branch": "master",
                "remotes": [{
                    "name": "origin",
                    "url": "https://github.com/lemurheavy/coveralls-ruby.git"
                }]
            }
        """

        rev = run_command('git', 'rev-parse', '--abbrev-ref', 'HEAD').strip()
        git_info = {'git': {
            'head': {
                'id': gitlog('%H'),
                'author_name': gitlog('%aN'),
                'author_email': gitlog('%ae'),
                'committer_name': gitlog('%cN'),
                'committer_email': gitlog('%ce'),
                'message': gitlog('%s'),
            },
            'branch': os.environ.get('CIRCLE_BRANCH') or os.environ.get('TRAVIS_BRANCH', rev),
            #origin	git@github.com:coagulant/coveralls-python.git (fetch)
            'remotes': [{'name': line.split()[0], 'url': line.split()[1]}
                        for line in run_command('git', 'remote', '-v').splitlines() if '(fetch)' in line]
        }}
        return git_info

    def debug_bad_encoding(self, data):
        """ Let's try to help user figure out what is at fault"""
        at_fault_files = set()
        for source_file_data in data['source_files']:
            for key, value in source_file_data.items():
                try:
                    json.dumps(value)
                except UnicodeDecodeError:
                    at_fault_files.add(source_file_data['name'])
        if at_fault_files:
            log.error("HINT: Following files cannot be decoded properly into unicode."
                      "Check their content: %s" % (', '.join(at_fault_files)))


def gitlog(format):
    try:
        log = str(run_command('git', '--no-pager', 'log', "-1", '--pretty=format:%s' % format))
    except UnicodeEncodeError:
        log = unicode(run_command('git', '--no-pager', 'log', "-1", '--pretty=format:%s' % format))
    return log


def run_command(*args):
    cmd = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert cmd.wait() == 0
    output = cmd.stdout.read()
    try:
        output = output.decode()
    except UnicodeDecodeError:
        output = output.decode('utf-8')
    return output

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
"""Publish coverage results online via coveralls.io

Puts your coverage results on coveralls.io for everyone to see.
It makes custom report for data generated by coverage.py package and sends it to `json API`_ of coveralls.io service.
All python files in your coverage analysis are posted to this service along with coverage stats,
so please make sure you're not ruining your own security!

Usage:
    coveralls [options]
    coveralls debug  [options]

    Debug mode doesn't send anything, just outputs json to stdout, useful for development.
    It also forces verbose output.

Global options:
    --rcfile=<file>   Specify configuration file. [default: .coveragerc]
    -h --help         Display this help
    -v --verbose      Print extra info, True for debug command

Example:
    $ coveralls
    Submitting coverage to coveralls.io...
    Coverage submitted!
    Job #38.1
    https://coveralls.io/jobs/92059
"""
import logging
from docopt import docopt
from coveralls import Coveralls
from coveralls.api import CoverallsException


log = logging.getLogger('coveralls')


def main(argv=None):
    options = docopt(__doc__, argv=argv)
    if options['debug']:
        options['--verbose'] = True
    level = logging.DEBUG if options['--verbose'] else logging.INFO
    log.addHandler(logging.StreamHandler())
    log.setLevel(level)

    try:
        coverallz = Coveralls(config_file=options['--rcfile'])
        if not options['debug']:
            log.info("Submitting coverage to coveralls.io...")
            result = coverallz.wear()
            log.info("Coverage submitted!")
            log.info(result['message'])
            log.info(result['url'])
            log.debug(result)
        else:
            log.info("Testing coveralls-python...")
            coverallz.wear(dry_run=True)
    except KeyboardInterrupt:  # pragma: no cover
        log.info('Aborted')
    except CoverallsException as e:
        log.error(e)
    except KeyError as e:  # pragma: no cover
        log.error(e)
    except Exception:  # pragma: no cover
        raise

########NEW FILE########
__FILENAME__ = reporter
# coding: utf-8
import logging
import sys

from coverage.misc import NoSource, NotPython
from coverage.phystokens import source_encoding
from coverage.report import Reporter


log = logging.getLogger('coveralls')


class CoverallReporter(Reporter):
    """ Custom coverage.py reporter for coveralls.io
    """
    def report(self, morfs=None):
        """ Generate a part of json report for coveralls

        `morfs` is a list of modules or filenames.
        `outfile` is a file object to write the json to.
        """
        self.source_files = []
        self.find_code_units(morfs)

        for cu in self.code_units:
            try:
                self.parse_file(cu, self.coverage._analyze(cu))
            except NoSource:
                if not self.config.ignore_errors:
                    log.warn('No source for %s', cu.name)
            except NotPython:
                # Only report errors for .py files, and only if we didn't
                # explicitly suppress those errors.
                if cu.should_be_python() and not self.config.ignore_errors:
                    log.warn('Source file is not python %s', cu.name)

        return self.source_files

    def get_hits(self, line_num, analysis):
        """ Source file stats for each line.

            * A positive integer if the line is covered,
            representing the number of times the line is hit during the test suite.
            * 0 if the line is not covered by the test suite.
            * null to indicate the line is not relevant to code coverage
              (it may be whitespace or a comment).
        """
        if line_num in analysis.missing:
            return 0
        if line_num in analysis.statements:
            return 1
        return None

    def parse_file(self, cu, analysis):
        """ Generate data for single file """
        filename = cu.file_locator.relative_filename(cu.filename)
        coverage_lines = [self.get_hits(i, analysis) for i in range(1, len(analysis.parser.lines) + 1)]
        source_file = cu.source_file()
        try:
            source = source_file.read()
            if sys.version_info < (3, 0):
                encoding = source_encoding(source)
                if encoding != 'utf-8':
                    source = source.decode(encoding).encode('utf-8')
        finally:
            source_file.close()
        self.source_files.append({
            'name': filename,
            'source': source,
            'coverage': coverage_lines
        })
########NEW FILE########
__FILENAME__ = project
# coding: utf-8


def hello():
    print('world')


class Foo(object):
    """ Bar """


def baz():
    print('this is not tested')
########NEW FILE########
__FILENAME__ = runtests
# coding: utf-8
from project import hello

if __name__ == '__main__':
    hello()
########NEW FILE########
__FILENAME__ = nonunicode
# coding: iso-8859-15

def hello():
    print ('I like P�lya distribution.')
########NEW FILE########
__FILENAME__ = test_api
# coding: utf-8
from __future__ import unicode_literals
import json
import os
from os.path import join, dirname
import re
import shutil
import tempfile
import unittest
import coverage

import sh
from mock import patch
import pytest

from coveralls import Coveralls
from coveralls.api import log


class GitBasedTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        sh.cd(self.dir)
        sh.git.init()
        sh.git('config', 'user.name', '"Daniël"')
        sh.git('config', 'user.email', '"me@here.com"')
        sh.touch('README')
        sh.git.add('README')
        sh.git.commit('-m', 'first commit')
        sh.git('remote', 'add', 'origin', 'https://github.com/username/Hello-World.git')

    def tearDown(self):
        shutil.rmtree(self.dir)


@patch.object(Coveralls, 'config_filename', '.coveralls.mock')
class Configration(unittest.TestCase):

    def setUp(self):
        with open('.coveralls.mock', 'w+') as fp:
            fp.write('repo_token: xxx\n')
            fp.write('service_name: jenkins\n')

    def tearDown(self):
        os.remove('.coveralls.mock')

    @patch.dict(os.environ, {}, clear=True)
    def test_local_with_config(self):
        cover = Coveralls()
        assert cover.config['service_name'] == 'jenkins'
        assert cover.config['repo_token'] == 'xxx'
        assert 'service_job_id' not in cover.config


@patch.object(Coveralls, 'config_filename', '.coveralls.mock')
class NoConfig(unittest.TestCase):

    @patch.dict(os.environ, {'TRAVIS': 'True', 'TRAVIS_JOB_ID': '777'}, clear=True)
    def test_travis_no_config(self):
        cover = Coveralls()
        assert cover.config['service_name'] == 'travis-ci'
        assert cover.config['service_job_id'] == '777'
        assert 'repo_token' not in cover.config

    @patch.dict(os.environ, {'TRAVIS': 'True', 'TRAVIS_JOB_ID': '777', 'COVERALLS_REPO_TOKEN': 'yyy'}, clear=True)
    def test_repo_token_from_env(self):
        cover = Coveralls()
        assert cover.config['service_name'] == 'travis-ci'
        assert cover.config['service_job_id'] == '777'
        assert cover.config['repo_token'] == 'yyy'

    @patch.dict(os.environ, {}, clear=True)
    def test_misconfigured(self):
        with pytest.raises(Exception) as excinfo:
            Coveralls()

        assert str(excinfo.value) == 'You have to provide either repo_token in .coveralls.mock, or launch via Travis'


class Git(GitBasedTest):

    @patch.dict(os.environ, {'TRAVIS_BRANCH': 'master'}, clear=True)
    def test_git(self):
        cover = Coveralls(repo_token='xxx')
        git_info = cover.git_info()
        commit_id = git_info['git']['head'].pop('id')

        assert re.match(r'^[a-f0-9]{40}$', commit_id)
        assert git_info == {'git': {
            'head': {
                'committer_email': 'me@here.com',
                'author_email': 'me@here.com',
                'author_name': 'Daniël',
                'message': 'first commit',
                'committer_name': 'Daniël',
            },
            'remotes': [{
                'url': 'https://github.com/username/Hello-World.git',
                'name': 'origin'
            }],
            'branch': 'master'
        }}

class ReporterTest(unittest.TestCase):

    def setUp(self):
        os.chdir(join(dirname(dirname(__file__)), 'example'))
        sh.rm('-f', '.coverage')
        sh.rm('-f', 'extra.py')
        self.cover = Coveralls(repo_token='xxx')

    def test_reporter(self):
        sh.coverage('run', 'runtests.py')
        assert self.cover.get_coverage() == [{
            'source': '# coding: utf-8\n\n\ndef hello():\n    print(\'world\')\n\n\nclass Foo(object):\n    """ Bar """\n\n\ndef baz():\n    print(\'this is not tested\')',
            'name': 'project.py',
            'coverage': [None, None, None, 1, 1, None, None, 1, None, None, None, 1, 0]}, {
            'source': "# coding: utf-8\nfrom project import hello\n\nif __name__ == '__main__':\n    hello()",
            'name': 'runtests.py', 'coverage': [None, 1, None, 1, 1]}]

    def test_missing_file(self):
        sh.echo('print("Python rocks!")', _out="extra.py")
        sh.coverage('run', 'extra.py')
        sh.rm('-f', 'extra.py')
        assert self.cover.get_coverage() == []

    def test_not_python(self):
        sh.echo('print("Python rocks!")', _out="extra.py")
        sh.coverage('run', 'extra.py')
        sh.echo("<h1>This isn't python!</h1>", _out="extra.py")
        assert self.cover.get_coverage() == []


def test_non_unicode():
    os.chdir(join(dirname(dirname(__file__)), 'nonunicode'))
    sh.coverage('run', 'nonunicode.py')
    expected_json_part = '"source": "# coding: iso-8859-15\\n\\ndef hello():\\n    print (\'I like P\\u00f3lya distribution.\')"'
    assert expected_json_part in json.dumps(Coveralls(repo_token='xxx').get_coverage())

@patch('coveralls.api.requests')
class WearTest(unittest.TestCase):

    def setUp(self):
        sh.rm('-f', '.coverage')

    def setup_mock(self, mock_requests):
        self.expected_json = {'url': 'https://coveralls.io/jobs/5869', 'message': 'Job #7.1 - 44.58% Covered'}
        mock_requests.post.return_value.json.return_value = self.expected_json

    def test_wet_run(self, mock_requests):
        self.setup_mock(mock_requests)
        result = Coveralls(repo_token='xxx').wear(dry_run=False)
        assert result == self.expected_json

    def test_dry_run(self, mock_requests):
        self.setup_mock(mock_requests)
        result = Coveralls(repo_token='xxx').wear(dry_run=True)
        assert result == {}

    @patch.object(log, 'debug')
    def test_repo_token_in_not_compromised_verbose(self, mock_logger, mock_requests):
        self.setup_mock(mock_requests)
        result = Coveralls(repo_token='xxx').wear(dry_run=True)
        assert 'xxx' not in mock_logger.call_args[0][0]

    def test_coveralls_unavailable(self, mock_requests):
        mock_requests.post.return_value.json.side_effect = ValueError
        mock_requests.post.return_value.status_code = 500
        mock_requests.post.return_value.text = '<html>Http 1./1 500</html>'
        result = Coveralls(repo_token='xxx').wear()
        assert result == {'message': 'Failure to submit data. Response [500]: <html>Http 1./1 500</html>'}

    @patch('coveralls.reporter.CoverallReporter.report')
    def test_no_coverage(self, report_files, mock_requests):
        report_files.side_effect = coverage.CoverageException('No data to report')
        self.setup_mock(mock_requests)
        result = Coveralls(repo_token='xxx').wear()
        assert result == {'message': 'Failure to gather coverage: No data to report'}
########NEW FILE########
__FILENAME__ = test_cli
# coding: utf-8
import os

from mock import patch, call
import pytest

import coveralls
from coveralls.api import CoverallsException
import coveralls.cli


@patch.dict(os.environ, {'TRAVIS': 'True'}, clear=True)
@patch.object(coveralls.cli.log, 'info')
@patch.object(coveralls.Coveralls, 'wear')
def test_debug(mock_wear, mock_log):
    coveralls.cli.main(argv=['debug'])
    mock_wear.assert_called_with(dry_run=True)
    mock_log.assert_has_calls([call("Testing coveralls-python...")])


@patch.object(coveralls.cli.log, 'info')
@patch.object(coveralls.Coveralls, 'wear')
@patch.dict(os.environ, {'TRAVIS': 'True'}, clear=True)
def test_real(mock_wear, mock_log):
    coveralls.cli.main(argv=[])
    mock_wear.assert_called_with()
    mock_log.assert_has_calls([call("Submitting coverage to coveralls.io..."), call("Coverage submitted!")])


@patch.dict(os.environ, {'TRAVIS': 'True'}, clear=True)
@patch('coveralls.cli.Coveralls')
def test_rcfile(mock_coveralls):
    coveralls.cli.main(argv=['--rcfile=coveragerc'])
    mock_coveralls.assert_called_with(config_file='coveragerc')

exc = CoverallsException('bad stuff happened')

@patch.object(coveralls.cli.log, 'error')
@patch.object(coveralls.Coveralls, 'wear', side_effect=exc)
@patch.dict(os.environ, {'TRAVIS': 'True'}, clear=True)
def test_exception(mock_coveralls, mock_log):
    coveralls.cli.main(argv=[])
    mock_log.assert_has_calls([call(exc)])

########NEW FILE########
