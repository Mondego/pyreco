__FILENAME__ = app
import argparse
import logging
import subprocess
import glob

import pkg_resources

from imhotep.repomanagers import ShallowRepoManager, RepoManager
from .reporters.printing import PrintingReporter
from .reporters.github import CommitReporter, PRReporter
from .diff_parser import DiffContextParser
from .shas import get_pr_info, CommitInfo
from imhotep import http
from .errors import UnknownTools, NoCommitInfo


log = logging.getLogger(__name__)


def run(cmd, cwd='.'):
    log.debug("Running: %s", cmd)
    return subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True, cwd=cwd).communicate()[0]


def find_config(dirname, config_filenames):
    configs = []
    for filename in config_filenames:
        configs += glob.glob('%s/%s' % (dirname, filename))
    return set(configs)


def run_analysis(repo, filenames=set(), linter_configs=set()):
    results = {}
    for tool in repo.tools:
        log.debug("running %s" % tool.__class__.__name__)
        configs = {}
        try:
            configs = tool.get_configs()
        except AttributeError:
            pass
        linter_configs = find_config(repo.dirname, configs)
        log.debug("Tool configs %s, found configs %s", configs, linter_configs)
        run_results = tool.invoke(repo.dirname,
                                  filenames=filenames,
                                  linter_configs=linter_configs)
        results.update(run_results)
    return results


def load_plugins():
    tools = []
    for ep in pkg_resources.iter_entry_points(group='imhotep_linters'):
        klass = ep.load()
        tools.append(klass(run))
    return tools


class Imhotep(object):
    def __init__(self, requester=None, repo_manager=None,
                 repo_name=None, pr_number=None,
                 commit_info=None,
                 commit=None, origin_commit=None, no_post=None, debug=None,
                 filenames=None, shallow_clone=False, **kwargs):
        # TODO(justinabrahms): kwargs exist until we handle cli params better
        # TODO(justinabrahms): This is a sprawling API. Tighten it up.
        self.requester = requester
        self.manager = repo_manager

        self.commit_info = commit_info
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.commit = commit
        self.origin_commit = origin_commit
        self.no_post = no_post
        self.debug = debug
        if filenames is None:
            filenames = []
        self.requested_filenames = set(filenames)
        self.shallow = shallow_clone

        if self.commit is None and self.pr_number is None:
            raise NoCommitInfo()

    def get_reporter(self):
        if self.no_post:
            return PrintingReporter()
        if self.pr_number:
            return PRReporter(self.requester, self.pr_number)
        elif self.commit is not None:
            return CommitReporter(self.requester)

    def get_filenames(self, entries, requested_set=None):
        filenames = set([x.result_filename for x in entries])
        if requested_set is not None and len(requested_set):
            filenames = requested_set.intersection(filenames)
        return list(filenames)

    def invoke(self):
        cinfo = self.commit_info
        reporter = self.get_reporter()

        try:
            repo = self.manager.clone_repo(self.repo_name,
                                           remote_repo=cinfo.remote_repo,
                                           ref=cinfo.ref)
            diff = repo.diff_commit(cinfo.commit,
                                    compare_point=cinfo.origin)

            # Move out to its own thing
            parser = DiffContextParser(diff)
            parse_results = parser.parse()
            filenames = self.get_filenames(parse_results,
                                           self.requested_filenames)
            results = run_analysis(repo,
                                   filenames=filenames)

            error_count = 0
            for entry in parse_results:
                added_lines = [l.number for l in entry.added_lines]
                pos_map = {}
                for x in entry.added_lines:
                    pos_map[x.number] = x.position

                violations = results.get(entry.result_filename, {})
                violating_lines = [int(l) for l in violations.keys()]

                matching_numbers = set(added_lines).intersection(
                    violating_lines)
                for x in matching_numbers:
                    error_count += 1
                    reporter.report_line(
                        repo.name, cinfo.origin, entry.result_filename,
                        x, pos_map[x], violations['%s' % x])

                log.info("%d violations.", error_count)
        finally:
            self.manager.cleanup()


def gen_imhotep(**kwargs):
    # TODO(justinabrahms): Interface should have a "are creds valid?" method
    req = http.BasicAuthRequester(kwargs['github_username'],
                                  kwargs['github_password'])

    plugins = load_plugins()
    tools = get_tools(kwargs['linter'], plugins)

    if kwargs['shallow']:
        Manager = ShallowRepoManager
    else:
        Manager = RepoManager

    manager = Manager(authenticated=kwargs['authenticated'],
                          cache_directory=kwargs['cache_directory'],
                          tools=tools,
                          executor=run)

    if kwargs['pr_number']:
        pr_info = get_pr_info(req, kwargs['repo_name'], kwargs['pr_number'])
        commit_info = pr_info.to_commit_info()
    else:
        # TODO(justinabrahms): origin & remote_repo doesnt work for commits
        commit_info = CommitInfo(kwargs['commit'], None, None, None)

    log.debug('Shallow: %s', kwargs['shallow'])
    shallow_clone = kwargs['shallow'] or False

    return Imhotep(
        requester=req, repo_manager=manager, commit_info=commit_info,
        shallow_clone=shallow_clone, **kwargs)


def get_tools(whitelist, known_plugins):
    """
    Filter all known plugins by a whitelist specified. If the whitelist is
    empty, default to all plugins.
    """
    getpath = lambda c: "%s:%s" % (c.__module__, c.__class__.__name__)

    tools = [x for x in known_plugins if getpath(x) in whitelist]

    if not tools:
        if whitelist:
            raise UnknownTools(map(getpath, known_plugins))
        tools = known_plugins
    return tools


def parse_args(args):
    arg_parser = argparse.ArgumentParser(
        description="Posts static analysis results to github.")
    arg_parser.add_argument(
        '--config-file',
        default="imhotep_config.json",
        type=str,
        help="Configuration file in json.")
    arg_parser.add_argument(
        '--repo_name', required=True,
        help="Github repository name in owner/repo format")
    arg_parser.add_argument(
        '--commit',
        help="The sha of the commit to run static analysis on.")
    arg_parser.add_argument(
        '--origin-commit',
        required=False,
        default='HEAD^',
        help='Commit to use as the comparison point.')
    arg_parser.add_argument(
        '--filenames', nargs="+",
        help="filenames you want static analysis to be limited to.")
    arg_parser.add_argument(
        '--debug',
        action='store_true',
        help="Will dump debugging output and won't clean up after itself.")
    arg_parser.add_argument(
        '--github-username',
        help='Github user to post comments as.')
    arg_parser.add_argument(
        '--github-password',
        help='Github password for the above user.')
    arg_parser.add_argument(
        '--no-post',
        action="store_true",
        help="[DEBUG] will print out comments rather than posting to github.")
    arg_parser.add_argument(
        '--authenticated',
        action="store_true",
        help="Indicates the repository requires authentication")
    arg_parser.add_argument(
        '--pr-number',
        help="Number of the pull request to comment on")
    arg_parser.add_argument(
        '--cache-directory',
        help="Path to directory to cache the repository",
        type=str,
        required=False)
    arg_parser.add_argument(
        '--linter',
        help="Path to linters to run, e.g. 'imhotep.tools:PyLint'",
        type=str,
        nargs="+",
        default=[],
        required=False)
    arg_parser.add_argument(
        '--shallow',
        help="Performs a shallow clone of the repo",
        action="store_true")
    # parse out repo name
    return arg_parser.parse_args(args)

########NEW FILE########
__FILENAME__ = app_test
from collections import namedtuple
import json

import mock

from .app import (run_analysis, get_tools, UnknownTools, Imhotep, NoCommitInfo,
    run, load_plugins, gen_imhotep, find_config)
from imhotep.main import load_config
from imhotep.testing_utils import fixture_path
from .reporters.printing import PrintingReporter
from .reporters.github import CommitReporter, PRReporter
from .repositories import Repository, ToolsNotFound
from .diff_parser import Entry


repo_name = 'justinabrahms/imhotep'

with open(fixture_path('remote_pr.json')) as f:
    remote_json_fixture = json.loads(f.read())


def test_run():
    with mock.patch("subprocess.Popen") as popen:
        run('test')
        popen.assert_called_with(
            ['test'], cwd='.', stdout=mock.ANY, shell=True)


def test_run_known_cwd():
    with mock.patch("subprocess.Popen") as popen:
        run('test', cwd="/known")
        popen.assert_called_with(
            ['test'], cwd='/known', stdout=mock.ANY, shell=True)


def test_config_loading():
    c = load_config('doesnt_exist')
    assert isinstance(c, dict)

def test_tools_invoked_on_repo():
    m = mock.MagicMock()
    m.invoke.return_value = {}
    repo = Repository('name', 'location', [m], None)
    run_analysis(repo)
    assert m.invoke.called

def test_run_analysis__config_fetch_error_handled():
    mock_tool = mock.Mock()
    mock_tool.get_configs.side_effect = AttributeError()
    mock_tool.invoke.return_value = []

    repo = Repository('name', 'loc', [mock_tool], None)

    assert {} == run_analysis(repo)

def test_tools_merges_tool_results():
    m = mock.MagicMock()
    m.invoke.return_value = {'a': 1}
    m2 = mock.MagicMock()
    m2.invoke.return_value = {'b': 2}
    repo = Repository('name', 'location', [m, m2], None)
    retval = run_analysis(repo)

    assert 'a' in retval
    assert 'b' in retval


def test_tools_errors_on_no_tools():
    try:
        Repository('name', 'location', [], None)
        assert False, "Should error if no tools are given"
    except ToolsNotFound:
        pass


def test_imhotep_instantiation__error_without_commit_info():
    try:
        Imhotep()
        assert False, "Expected a NoCommitInfo exception."
    except NoCommitInfo:
        pass


def test_reporter__printing():
    i = Imhotep(no_post=True, commit="asdf")
    assert type(i.get_reporter()) == PrintingReporter


def test_reporter__pr():
    i = Imhotep(pr_number=1)
    assert type(i.get_reporter()) == PRReporter


def test_reporter__commit():
    i = Imhotep(commit='asdf')
    assert type(i.get_reporter()) == CommitReporter


class Thing1(object):
    pass


class Thing2(object):
    pass


def test_plugin_filtering_throws_if_unfound():
    try:
        get_tools('unknown', [Thing1()])
        assert False, "Should have thrown an UnknownTools exception"
    except UnknownTools:
        pass


def test_plugin_filtering_defaults_to_all():
    plugins = [Thing1(), Thing2()]
    assert plugins == get_tools([], plugins)


def test_plugin_filtering_returns_subset_if_found():
    t1 = Thing1()
    plugins = [t1, Thing2()]
    assert [t1] == get_tools(['imhotep.app_test:Thing1'], plugins)


test_tool = namedtuple('TestTool', ('executor'), )


class EP(object):
    def load(self):
        return test_tool


def test_load_plugins():
    with mock.patch('pkg_resources.iter_entry_points') as ep:
        ep.return_value = [EP(), EP()]
        plugins = load_plugins()
        assert not isinstance(plugins[0], EP)
        assert 2 == len(plugins)


def test_imhotep_get_filenames():
    e1 = Entry('a.txt', 'a.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1])
    assert filenames == ['a.txt']


def test_imhotep_get_filenames_empty():
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([])
    assert filenames == []


def test_imhotep_get_filenames_requested():
    e1 = Entry('a.txt', 'a.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1], set(['a.txt']))
    assert filenames == ['a.txt']


def test_imhotep_get_filenames_requested_non_existent():
    e1 = Entry('a.txt', 'a.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1], set(['non-existent.txt']))
    assert filenames == []


def test_imhotep_get_filenames_requested_destination():
    e1 = Entry('a.txt', 'b.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1], set(['b.txt']))
    assert filenames == ['b.txt']


def gen_imhotep_dict():
    return {
        'github_username': 'username',
        'github_password': 'password',
        'linter': '',
        'shallow': False,
        'authenticated': False,
        'cache_directory': '/tmp',
        'pr_number': None,
    }

def test_gen_imhotep__returns_instance():
    kwargs = gen_imhotep_dict()
    kwargs['commit'] = 'abcdef0'
    retval = gen_imhotep(**kwargs)
    assert isinstance(retval, Imhotep)

def test_gen_imhotep__shallow_pr():
    kwargs = gen_imhotep_dict()
    kwargs['pr_number'] = 10
    kwargs['shallow'] = True
    kwargs['repo_name'] = 'user/repo'

    with mock.patch('imhotep.http.BasicAuthRequester') as mock_gh_req:
        mock_gh_req.return_value.get.return_value.json.return_value = remote_json_fixture
        retval = gen_imhotep(**kwargs)
    assert isinstance(retval, Imhotep)


def test_find_config__glob_no_results():
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.return_value = []
        retval = find_config('dirname', ['configs'])
    assert set() == retval


def test_find_config__glob_multi_results():
    returns = [['setup.py', 'foo.py'], ['bar.py']]
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.side_effect = lambda x: returns.pop(0)
        retval = find_config('dirname', ['configs', 'others'])

    assert retval == set(['setup.py', 'foo.py', 'bar.py'])

def test_find_config__prefix_dirname():
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.return_value = []

        find_config('dirname', ['config'])

        mock_glob.assert_called_once_with('dirname/config')

def test_find_config__called_with_each_config_file():
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.return_value = []

        find_config('dirname', ['config', 'another'])

        mock_glob.assert_has_calls([mock.call.glob('dirname/config'),
                                    mock.call.glob('dirname/another')])

########NEW FILE########
__FILENAME__ = diff_parser
"""
Thanks to @fridgei & @scottjab for the initial version of this code.
"""
from collections import namedtuple
import re

Line = namedtuple("Line", ["number", "position", "contents"])

diff_re = re.compile(
    "@@ \-(?P<removed_start>\d+),(?P<removed_length>\d+) "
    "\+(?P<added_start>\d+),(?P<added_length>\d+) @@"
)


class Entry(object):
    def __init__(self, origin_filename, result_filename):
        self.origin_filename = origin_filename
        self.result_filename = result_filename
        self.origin_lines = []
        self.result_lines = []
        self.added_lines = []
        self.removed_lines = []

    def new_removed(self, line):
        self.removed_lines.append(line)

    def new_added(self, line):
        self.added_lines.append(line)

    def new_origin(self, line):
        self.origin_lines.append(line)

    def new_result(self, line):
        self.result_lines.append(line)

    def is_dirty(self):
        return self.result_lines or self.origin_lines


class DiffContextParser:
    def __init__(self, diff_text):
        self.diff_text = diff_text

    @staticmethod
    def should_skip_line(line):
        # "index oldsha..newsha permissions" line or..
        # "index 0000000..78ce7f6"
        if re.search(r'index \w+..\w+( \d)?', line):
            return True
        # --- a/.gitignore
        # +++ b/.gitignore
        # --- /dev/null
        elif re.search('(-|\+){3} (a|b)?/.*', line):
            return True
        # "new file mode 100644" on new files
        elif re.search('new file mode.*', line):
            return True
        return False

    def parse(self):
        """
        Parses everyting into a datastructure that looks like:

            result = [{
                'origin_filename': '',
                'result_filename': '',
                'origin_lines': [], // all lines of the original file
                'result_lines': [], // all lines of the newest file
                'added_lines': [], // all lines added to the result file
                'removed_lines': [], // all lines removed from the result file
            }, ...]

        """
        result = []

        z = None

        before_line_number, after_line_number = 0, 0
        position = 0

        for line in self.diff_text.splitlines():

            # New File
            match = re.search(r'diff .*a/(?P<origin_filename>.*) '
                              r'b/(?P<result_filename>.*)', line)
            if match is not None:
                if z is not None:
                    result.append(z)
                z = Entry(match.group('origin_filename'),
                          match.group('result_filename'))
                position = 0
                continue

            if self.should_skip_line(line):
                continue

            header = diff_re.search(line)
            if header is not None:
                before_line_number = int(header.group('removed_start'))
                after_line_number = int(header.group('added_start'))
                position += 1
                continue

            # removed line
            if line.startswith('-'):
                z.new_removed(Line(before_line_number, position, line[1:]))
                z.new_origin(Line(before_line_number, position, line[1:]))
                before_line_number += 1

            # added line
            elif line.startswith('+'):
                z.new_added(Line(after_line_number, position, line[1:]))
                z.new_result(Line(after_line_number, position, line[1:]))
                after_line_number += 1

            # untouched context line.
            else:
                z.new_origin(Line(before_line_number, position, line[1:]))
                z.new_result(Line(after_line_number, position, line[1:]))

                before_line_number += 1
                after_line_number += 1

            position += 1

        if z is not None:
            result.append(z)

        return result

########NEW FILE########
__FILENAME__ = diff_parser_test
from imhotep.diff_parser import DiffContextParser, Entry
from imhotep.testing_utils import fixture_path


def test_skip_line__minus():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("--- a/.gitignore")


def test_skip_line__plus():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("+++ b/.gitignore")


def test_skip_line__null():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("--- /dev/null")


def test_skip_line__new_file():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("new file mode 100644")


def test_skip_line__index():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("index 3929bb3..633facf 100644")


def test_skip_line__index_no_permissions():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("index 0000000..78ce7f6")


def test_skip_line__noskip():
    dcp = DiffContextParser("")
    assert not dcp.should_skip_line("+ this is a legit line")


with open(fixture_path('two-block.diff')) as f:
    two_block = f.read()

with open(fixture_path('two-file.diff')) as f:
    two_file = f.read()


def test_multi_block_single_file():
    dcp = DiffContextParser(two_block)
    results = dcp.parse()
    entry = results[0]

    assert len(entry.added_lines) == 5
    assert len(entry.removed_lines) == 1


def test_linum_counting():
    dcp = DiffContextParser(two_block)
    results = dcp.parse()
    entry = results[0]

    assert entry.removed_lines[0].number == 2


def test_position_counting():
    dcp = DiffContextParser(two_block)
    results = dcp.parse()
    entry = results[0]

    # First @@ is 0 and we count from there.
    valid_positions = set([3, 9, 10, 11, 12])
    assert set([x.position for x in entry.added_lines]) == valid_positions


def test_two_file():
    dcp = DiffContextParser(two_file)
    results = dcp.parse()

    entry1, entry2 = results

    assert entry1.origin_filename == '.travis.yml'
    assert entry1.result_filename == '.travis.yml'
    assert entry2.origin_filename == 'requirements.txt'
    assert entry2.result_filename == 'requirements.txt'


def test_entry__clean():
    e = Entry('fna', 'fnb')
    assert not e.is_dirty()


def test_entry__dirty_result():
    e = Entry('fna', 'fnb')
    e.new_result('line')
    assert e.is_dirty()


def test_entry__dirty_result():
    e = Entry('fna', 'fnb')
    e.new_origin('line')
    assert e.is_dirty()

########NEW FILE########
__FILENAME__ = errors
class UnknownTools(Exception):
    def __init__(self, known):
        self.known = known


class NoCommitInfo(Exception):
    pass

########NEW FILE########
__FILENAME__ = http
import json
import logging

import requests
from requests.auth import HTTPBasicAuth


log = logging.getLogger(__name__)


class NoGithubCredentials(Exception):
    pass


class BasicAuthRequester(object):
    """
    Object used for issuing authenticated API calls.
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_auth(self):
        return HTTPBasicAuth(self.username, self.password)

    def get(self, url):
        log.debug("Fetching %s", url)

        response = requests.get(url, auth=self.get_auth())
        if response.status_code > 400:
            log.warning("Error on GET to %s. Response: %s", url,
                        response.content)
        return response

    def delete(self, url):
        log.debug("Deleting %s", url)
        return requests.delete(url, auth=self.get_auth())

    def post(self, url, payload):
        log.debug("Posting %s to %s", payload, url)
        response = requests.post(url, data=json.dumps(payload),
                                 auth=self.get_auth())
        if response.status_code > 400:
            log.warning("Error on POST to %s. Response: %s", url,
                        response.content)
        return response


########NEW FILE########
__FILENAME__ = http_test
import mock
from imhotep.http import BasicAuthRequester


def test_auth():
    ghr = BasicAuthRequester('user', 'pass')
    auth = ghr.get_auth()
    assert auth.username == 'user'
    assert auth.password == 'pass'


def test_get():
    ghr = BasicAuthRequester('user', 'pass')
    with mock.patch('requests.get') as g:
        g.return_value.status_code = 200
        ghr.get('url')
        g.assert_called_with_args('url', auth=mock.ANY)


def test_delete():
    ghr = BasicAuthRequester('user', 'pass')
    with mock.patch('requests.delete') as g:
        ghr.delete('url')
        g.assert_called_with_args('url', auth=mock.ANY)


def test_post():
    ghr = BasicAuthRequester('user', 'pass')
    with mock.patch('requests.post') as g:
        g.return_value.status_code = 200
        ghr.post('url', {"a": 2})
        g.assert_called_with_args('url', data='{"a":2}', auth=mock.ANY)

########NEW FILE########
__FILENAME__ = integration_test
"""
Integration test for imhotep.

1. Run against a known bad pull request.
2. Fetch the list of review comments. Validate the count is the correct number.
3. Delete all review comments.

list comments: GET /repos/:owner/:repo/pulls/:number/comments
               http://developer.github
               .com/v3/pulls/comments/#list-comments-on-a-pull-request

delete comment: DELETE /repos/:owner/:repo/pulls/comments/:number
                http://developer.github.com/v3/pulls/comments/#delete-a-comment
"""
import os

import pytest

from imhotep.http import BasicAuthRequester
from imhotep.reporters.github import PRReporter


ghu = os.getenv('GITHUB_USERNAME')
ghp = os.getenv('GITHUB_PASSWORD')

github_not_set = not ghu or not ghp

require_github_creds = pytest.mark.skipif(
    github_not_set, reason="must specify github credentials as env var")


@require_github_creds
def test_github_post():
    repo = 'imhotepbot/sacrificial-integration-tests'
    pr = 1
    test_str = 'integration test error name'
    req = BasicAuthRequester(ghu, ghp)
    r = PRReporter(req, pr)
    r.report_line(repo, 'da6a127a285ae08d9bfcccb1cb62aef908485769', 'foo.py', 2, 3, test_str)
    comments = req.get('https://api.github.com/repos/%s/pulls/%s/comments' %
                       (repo, pr)).json()
    posted = [x for x in comments if test_str in x['body']]

    try:
        assert len(posted) == 1
    finally:
        for comment in comments:
            req.delete('https://api.github.com/repos/%s/pulls/comments/%s' % (
                repo, comment['id']))


@require_github_creds
def test_dont_post_duplicate_comments():
    repo = 'imhotepbot/sacrificial-integration-tests'
    pr = 1
    test_str = 'integration test error name'
    req = BasicAuthRequester(ghu, ghp)
    r = PRReporter(req, pr)
    args = [repo, 'da6a127a285ae08d9bfcccb1cb62aef908485769', 'foo.py', 2, 3, test_str]

    r.report_line(*args)
    r.report_line(*args)  # should dedupe.

    comment_url = 'https://api.github.com/repos/%s/pulls/%s/comments' % (
        repo, pr)
    comments = req.get(comment_url).json()
    posted = [x for x in comments if test_str in x['body']]

    try:
        assert len(posted) == 1
    finally:
        for comment in comments:
            req.delete('%s/%s' % (comment_url, comment['id']))

########NEW FILE########
__FILENAME__ = main
import json
import logging
import os
import sys

from imhotep import app
from imhotep.errors import NoCommitInfo, UnknownTools
from imhotep.http import NoGithubCredentials


log = logging.getLogger(__name__)


def load_config(filename):
    config = {}
    if filename is not None:
        config_path = os.path.abspath(filename)
        try:
            with open(config_path) as f:
                config = json.loads(f.read())
        except IOError:
            log.error("Could not open config file %s", config_path)
        except ValueError:
            log.error("Could not parse config file %s", config_path)
    return config


def main():
    """
    Main entrypoint for the command-line app.
    """
    args = app.parse_args(sys.argv[1:])
    params = args.__dict__
    params.update(**load_config(args.config_file))

    if params['debug']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()

    try:
        imhotep = app.gen_imhotep(**params)
    except NoGithubCredentials:
        log.error("You must specify a GitHub username or password.")
        return False
    except NoCommitInfo:
        log.error("You must specify a commit or PR number")
        return False
    except UnknownTools as e:
        log.error("Didn't find any of the specified linters.")
        log.error("Known linters: %s", ', '.join(e.known))
        return False

    imhotep.invoke()


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = main_test
import io
import mock

from imhotep.app import parse_args
from imhotep.errors import UnknownTools, NoCommitInfo
from imhotep.http import NoGithubCredentials
from imhotep.main import main, load_config


class MockParserRetval(object):
    def __init__(self):
        self.__dict__ = {
            'config_file': 'foo.json',
            'repo_name': 'repo_name',
            'commit': 'commit',
            'origin_commit': 'origin-commit',
            'filenames': [],
            'debug': True,
            'github_username': 'justinabrahms',
            'github_password': 'notachance',
            'authenticated': True,
            'pr_number': 1,
            'cache_directory': '/tmp',
            'linter': 'path.to:Linter',
        }


def test_repo_required():
    try:
        parse_args([])
        assert False, "Should raise an error if repo_name not provided"
    except (SystemExit,):
        pass


def test_main__sanity():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            main()
            assert mock_gen.called


def test_main__returns_false_if_no_credentials():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            mock_gen.side_effect = NoGithubCredentials()

            assert main() is False


def test_main__returns_false_if_no_commit_info():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            mock_gen.side_effect = NoCommitInfo()

            assert main() is False


def test_main__returns_false_if_missing_tools():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            mock_gen.side_effect = UnknownTools('tools')

            assert main() is False

def test_load_config__returns_json_content():
    with mock.patch('imhotep.main.open', create=True) as mock_open:
        mock_open.return_value = mock.MagicMock(spec=io.IOBase)

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.return_value = '{"valid": "json"}'

        cfg = load_config('filename')

        assert {'valid': 'json'} == cfg


def test_load_config__value_error_handled():
    with mock.patch('imhotep.main.open', create=True) as mock_open:
        mock_open.return_value = mock.MagicMock(spec=io.IOBase)

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.side_effect = ValueError()

        cfg = load_config('filename')

        assert {} == cfg

########NEW FILE########
__FILENAME__ = test_25
from imhotep.diff_parser import DiffContextParser

diff = """diff --git a/foo.py b/foo.py
new file mode 100644
index 0000000..78ce7f6
--- /dev/null
+++ b/foo.py
@@ -0,0 +1,7 @@
+class Foo(object):
+  pass
+
+class Bar(object):
+  pass
+
+print "Works";
"""

def test_file_adds_arent_off():
    parser = DiffContextParser(diff)
    results = parser.parse()
    assert 'class Foo' in results[0].added_lines[0].contents

########NEW FILE########
__FILENAME__ = repomanagers
import logging
import os
from tempfile import mkdtemp

from .repositories import Repository, AuthenticatedRepository

log = logging.getLogger(__name__)


class RepoManager(object):
    """
    Manages creation and deletion of `Repository` objects.
    """
    to_cleanup = {}

    def __init__(self, authenticated=False, cache_directory=None,
                 tools=None, executor=None, shallow_clone=False):
        self.should_cleanup = cache_directory is None
        self.authenticated = authenticated
        self.cache_directory = cache_directory
        self.tools = tools or []
        self.executor = executor
        self.shallow = shallow_clone

    def get_repo_class(self):
        if self.authenticated:
            return AuthenticatedRepository
        return Repository

    def clone_dir(self, repo_name):
        dired_repo_name = repo_name.replace('/', '__')
        if not self.cache_directory:
            dirname = mkdtemp(suffix=dired_repo_name)
        else:
            dirname = os.path.abspath("%s/%s" % (
                self.cache_directory, dired_repo_name))
        return dirname

    def fetch(self, dirname, remote_name, ref):
        log.debug("Fetching %s %s", remote_name, ref)
        self.executor("cd %s && git fetch --depth=1 %s %s" % (dirname,
                                                              remote_name,
                                                              ref))

    def pull(self, dirname):
        log.debug("Pulling all %s", dirname)
        self.executor("cd %s && git pull --all" % dirname)

    def add_remote(self, dirname, name, url):
        log.debug("Adding remote %s url: %s", name, url)
        self.executor("cd %s && git remote add %s %s" % (dirname,
                                                         name,
                                                         url))

    def set_up_clone(self, repo_name, remote_repo):
        """Sets up the working directory and returns a tuple of
        (dirname, repo )"""
        dirname = self.clone_dir(repo_name)
        self.to_cleanup[repo_name] = dirname
        klass = self.get_repo_class()
        repo = klass(repo_name,
                     dirname,
                     self.tools,
                     self.executor,
                     shallow=self.shallow_clone)
        return (dirname, repo)

    def clone_repo(self, repo_name, remote_repo, ref):
        """Clones the given repo and returns the Repository object."""
        self.shallow_clone = False
        dirname, repo = self.set_up_clone(repo_name, remote_repo)
        if os.path.isdir("%s/.git" % dirname):
            log.debug("Updating %s to %s", repo.download_location, dirname)
            self.executor(
                "cd %s && git checkout master" % dirname)
            self.pull(dirname)
        else:
            log.debug("Cloning %s to %s", repo.download_location, dirname)
            self.executor(
                "git clone %s %s" % (repo.download_location, dirname))

        if remote_repo is not None:
            log.debug("Pulling remote branch from %s", remote_repo.url)
            self.add_remote(dirname,
                            remote_repo.name,
                            remote_repo.url)
            self.pull(dirname)
        return repo

    def cleanup(self):
        if self.should_cleanup:
            for repo_dir in self.to_cleanup.values():
                log.debug("Cleaning up %s", repo_dir)
                self.executor('rm -rf %s' % repo_dir)


class ShallowRepoManager(RepoManager):
    def __init__(self, *args, **kwargs):
        super(ShallowRepoManager, self).__init__(*args, **kwargs)

    def clone_repo(self, repo_name, remote_repo, ref):
        self.shallow_clone = True
        dirname, repo = self.set_up_clone(repo_name, remote_repo)
        remote_name = 'origin'
        log.debug("Shallow cloning.")
        download_location = repo.download_location
        log.debug("Creating stub git repo at %s" % (dirname))
        self.executor("mkdir -p %s" % (dirname, ))
        self.executor("cd %s && git init" % (dirname, ))
        log.debug("Adding origin repo %s " % (download_location))
        self.add_remote(dirname, 'origin', download_location)

        if remote_repo:
            self.add_remote(dirname, remote_repo.name, remote_repo.url)
            remote_name = remote_repo.name
        self.fetch(dirname, 'origin', 'HEAD')
        self.fetch(dirname, remote_name, ref)
        return repo
########NEW FILE########
__FILENAME__ = repomanagers_test
import mock
import re
from imhotep.app import find_config

from .testing_utils import calls_matching_re

from .shas import Remote
from .repomanagers import RepoManager, ShallowRepoManager
from .repositories import Repository, AuthenticatedRepository

repo_name = 'justinabrahms/imhotep'


def test_authencticated_repo():
    r = RepoManager(authenticated=True, tools=[None])
    assert AuthenticatedRepository == r.get_repo_class()


def test_unauthencticated_repo():
    r = RepoManager(tools=[None])
    assert Repository == r.get_repo_class()


def test_cleanup_calls_rm():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None])
    r.to_cleanup = {'repo': '/tmp/a_dir'}
    r.cleanup()

    assert m.called_with('rm -rf /tmp/a_dir')


def test_cleanup_doesnt_call_without_clean_files():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None], cache_directory=[])

    r.cleanup()
    assert not m.called

def test_fetch():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None])
    r.fetch('/tmp/a_dir', 'foo', 'newbranch')
    assert m.called_with('cd /tmp/a_dir && git fetch --depth=1 foo')

def test_shallow_clone():
    m = mock.Mock()
    r = ShallowRepoManager(executor=m, tools=[None])
    repo = Repository(repo_name, '/tmp/a_dir', [None], m, shallow=True)
    r.clone_repo(repo_name, Remote("name", "url"), 'foo')

    assert m.called_with('cd /tmp/a_dir && git init')
    assert m.called_with('cd /tmp/a_dir && git remote add name url')

def test_shallow_clone_call():
    m = mock.Mock()
    r = RepoManager(cache_directory="/weeble/wobble/",
                    executor=m,
                    tools=[None],
                    shallow_clone=True)
    r.clone_repo(repo_name, None, 'foo')
    assert m.called_with('cd /weeble/wobble/justinabrahms__imhotep && git init')

def test_clone_dir_nocache():
    # TODO(justinabrahms): this test has side effects which generate temp
    # dirs. Need to fix that.
    r = RepoManager(tools=[None])
    val = r.clone_dir(repo_name)
    assert '/tmp' in val


def test_clone_dir_cached():
    r = RepoManager(cache_directory="/weeble/wobble/", tools=[None])
    val = r.clone_dir(repo_name)
    assert val.startswith('/weeble/wobble/justinabrahms__imhotep')


def test_find_config():
    r = RepoManager(cache_directory="/weeble/wobble/", tools=[None])
    dirname = r.clone_dir(repo_name)
    assert len(find_config(dirname, list())) == 0


def test_clone_adds_to_cleanup_dict():
    m = mock.Mock()
    r = RepoManager(cache_directory="/weeble/wobble/", executor=m,
                    tools=[None])
    r.clone_repo(repo_name, None, None)
    directory = r.clone_dir(repo_name)
    assert directory in r.to_cleanup[repo_name]


def test_updates_if_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])

    with mock.patch('os.path.isdir') as isdir:
        isdir.return_value = True
        r.clone_repo(repo_name, None, None)

    assert len(calls_matching_re(m, finder)) == 0, "Shouldn't git clone"


def test_clones_if_no_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, None, None)

    assert len(calls_matching_re(m, finder)) == 1, "Didn't git clone"


def test_adds_remote_if_pr_is_remote():
    finder = re.compile(r'git remote add name url')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, Remote("name", "url"), None)

    assert len(calls_matching_re(m, finder)) == 1, "Remote not added"


def test_pulls_remote_changes_if_remote():
    finder = re.compile(r'git pull --all')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, Remote("name", "url"), None)

    assert len(calls_matching_re(m, finder)) == 1, "Didn't pull updates"

########NEW FILE########
__FILENAME__ = github
import logging
from six import string_types
from .reporter import Reporter

log = logging.getLogger(__name__)


class GitHubReporter(Reporter):
    def __init__(self, requester):
        self._comments = []
        self.requester = requester

    def clean_already_reported(self, comments, file_name, position,
                               message):
        """
        message is potentially a list of messages to post. This is later
        converted into a string.
        """
        for comment in comments:
            if ((comment['path'] == file_name
                 and comment['position'] == position
                 and comment['user']['login'] == self.requester.username)):

                return [m for m in message if m not in comment['body']]
        return message

    def get_comments(self, report_url):
        if not self._comments:
            log.debug("PR Request: %s", report_url)
            result = self.requester.get(report_url)
            if result.status_code >= 400:
                log.error("Error requesting comments from github. %s",
                          result.json())
                return self._comments
            self._comments = result.json()
        return self._comments

    def convert_message_to_string(self, message):
        """Convert message from list to string for GitHub API."""
        final_message = ''
        for submessage in message:
            final_message += '* {submessage}\n'.format(submessage=submessage)
        return final_message


class CommitReporter(GitHubReporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        report_url = (
            'https://api.github.com/repos/%s/commits/%s/comments'
            % (repo_name, commit))
        comments = self.get_comments(report_url)
        message = self.clean_already_reported(comments, file_name,
                                              position, message)
        payload = {
            'body': self.convert_message_to_string(message),
            'sha': commit,
            'path': file_name,
            'position': position,
            'line': None,
        }
        log.debug("Commit Request: %s", report_url)
        log.debug("Commit Payload: %s", payload)
        self.requester.post(report_url, payload)


class PRReporter(GitHubReporter):
    def __init__(self, requester, pr_number):
        self.pr_number = pr_number
        super(PRReporter, self).__init__(requester)

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        report_url = (
            'https://api.github.com/repos/%s/pulls/%s/comments'
            % (repo_name, self.pr_number))
        comments = self.get_comments(report_url)
        if isinstance(message, string_types):
            message = [message]
        message = self.clean_already_reported(comments, file_name,
                                              position, message)
        if not message:
            log.debug('Message already reported')
            return None
        payload = {
            'body': self.convert_message_to_string(message),
            'commit_id': commit,  # sha
            'path': file_name,  # relative file path
            'position': position,  # line index into the diff
        }
        log.debug("PR Request: %s", report_url)
        log.debug("PR Payload: %s", payload)
        result = self.requester.post(report_url, payload)
        if result.status_code >= 400:
            log.error("Error posting line to github. %s", result.json)
        return result

########NEW FILE########
__FILENAME__ = printing
import logging
from six import string_types
from .reporter import Reporter

log = logging.getLogger(__name__)


class PrintingReporter(Reporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        print("Would have posted the following: \n"
              "commit: %(commit)s\n"
              "position: %(position)s\n"
              "message: %(message)s\n"
              "file: %(filename)s\n"
              "repo: %(repo)s\n" % {
                  'repo': repo_name,
                  'commit': commit,
                  'position': position,
                  'message': message,
                  'filename': file_name
              })


########NEW FILE########
__FILENAME__ = reporter
import logging
from six import string_types

log = logging.getLogger(__name__)


class Reporter(object):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        raise NotImplementedError()


########NEW FILE########
__FILENAME__ = reporters_test
import mock

from imhotep.reporters.github import CommitReporter, GitHubReporter, PRReporter
from imhotep.testing_utils import Requester


def test_commit_url():
    requester = Requester("")
    cr = CommitReporter(requester)
    cr.report_line(repo_name='foo/bar', commit='sha',
                   file_name='setup.py', line_number=10, position=0,
                   message="test")

    assert requester.url == \
           "https://api.github.com/repos/foo/bar/commits/sha/comments"


def test_pr_url():
    requester = Requester("")
    pr = PRReporter(requester, 10)
    pr.report_line(repo_name='justinabrahms/imhotep', commit='sha',
                   file_name='setup.py', line_number=10, position=0,
                   message="test")

    assert requester.url == \
           "https://api.github.com/repos/justinabrahms/imhotep/pulls/10/comments"


def test_pr_already_reported():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    comments = [{'path': 'foo.py',
                'position': 2,
                'body': 'Get that out',
                'user': {'login': 'magicmock'}}]
    pr = PRReporter(requester, 10)
    pr._comments = comments
    result = pr.report_line(repo_name='justinabrahms/imhotep', commit='sha',
                            file_name='foo.py', line_number=2, position=2,
                            message='Get that out')
    assert result is None


def test_get_comments_no_cache():
    return_data = {'foo': 'bar'}
    requester = mock.MagicMock()
    requester.get.return_value.json = lambda: return_data
    requester.get.return_value.status_code = 200
    pr = GitHubReporter(requester)
    result = pr.get_comments('example.com')
    assert result == return_data
    assert pr._comments == return_data
    requester.get.assert_called_with('example.com')


def test_get_comments_cache():
    return_data = {'foo': 'bar'}
    requester = mock.MagicMock()
    pr = GitHubReporter(requester)
    pr._comments = return_data
    result = pr.get_comments('example.com')
    assert result == return_data
    assert not requester.get.called


def test_get_comments_error():
    requester = mock.MagicMock()
    requester.get.return_value.status_code = 400
    pr = GitHubReporter(requester)
    result = pr.get_comments('example.com')
    assert len(result) == 0


def test_clean_already_reported():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    pr = GitHubReporter(requester)
    comments = [{'path': 'foo.py',
                 'position': 2,
                 'body': 'Get that out',
                 'user': {'login': 'magicmock'}},
                {'path': 'foo.py',
                 'position': 2,
                 'body': 'Different comment',
                 'user': {'login': 'magicmock'}}]
    message = ['Get that out', 'New message']
    result = pr.clean_already_reported(comments, 'foo.py',
                                       2, message)
    assert result == ['New message']


def test_convert_message_to_string():
    message = ['foo', 'bar']
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    pr = GitHubReporter(requester)
    result = pr.convert_message_to_string(message)
    assert result == '* foo\n* bar\n'

########NEW FILE########
__FILENAME__ = repositories
import logging

log = logging.getLogger(__name__)


class ToolsNotFound(Exception):
    pass


class Repository(object):
    """
    Represents a github repository (both in the abstract and on disk).
    """

    def __init__(self, name, loc, tools, executor, shallow=False):
        if len(tools) == 0:
            raise ToolsNotFound()

        self.name = name
        self.dirname = loc
        self.tools = tools
        self.executor = executor
        self.shallow = shallow

    @property
    def download_location(self):
        return "git://github.com/%s.git" % self.name

    def apply_commit(self, commit):
        """
        Updates the repository to a given commit.
        """
        self.executor("cd %s && git checkout %s" % (self.dirname, commit))

    def diff_commit(self, commit, compare_point=None):
        """
        Returns a diff as a string from the current HEAD to the given commit.
        """
        # @@@ This is a security hazard as compare-point is user-passed in
        # data. Doesn't matter until we wrap this in a service.
        if compare_point is not None:
            self.apply_commit(compare_point)
        return self.executor("cd %s && git diff %s" % (self.dirname, commit))

    def __unicode__(self):
        return self.name


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return "git@github.com:%s.git" % self.name

########NEW FILE########
__FILENAME__ = repositories_test
import mock
from imhotep.repositories import Repository, AuthenticatedRepository

repo_name = 'justinabrahms/imhotep'


def test_unauthed_download_location():
    uar = Repository(repo_name, None, [None], None)
    loc = uar.download_location
    assert loc == "git://github.com/justinabrahms/imhotep.git"


def test_authed_download_location():
    ar = AuthenticatedRepository(repo_name, None, [None], None)
    assert ar.download_location == "git@github.com:justinabrahms/imhotep.git"


def test_unicode():
    r = Repository(repo_name, None, [None], None)
    assert r.__unicode__() == repo_name


def test_diff_commit():
    executor = mock.Mock()
    uar = Repository(repo_name, '/loc/', [None], executor)
    uar.diff_commit('commit-to-diff')
    executor.assert_called_with("cd /loc/ && git diff commit-to-diff")


def test_diff_commit__compare_point_applied():
    executor = mock.Mock()
    uar = Repository(repo_name, '/loc/', [None], executor)
    uar.diff_commit('commit-to-diff', compare_point='base')
    executor.assert_any_call("cd /loc/ && git checkout base")


def test_apply_commit():
    executor = mock.Mock()
    uar = Repository(repo_name, '/loc/', [None], executor)
    uar.apply_commit('base')
    executor.assert_called_with("cd /loc/ && git checkout base")

########NEW FILE########
__FILENAME__ = shas
from collections import namedtuple

Remote = namedtuple('Remote', ('name', 'url'))
CommitInfo = namedtuple("CommitInfo",
                        ('commit', 'origin', 'remote_repo', 'ref'))


class PRInfo(object):
    def __init__(self, json):
        self.json = json

    @property
    def base_sha(self):
        return self.json['base']['sha']

    @property
    def head_sha(self):
        return self.json['head']['sha']

    @property
    def base_ref(self):
        return self.json['base']['ref']

    @property
    def head_ref(self):
        return self.json['head']['ref']

    @property
    def has_remote_repo(self):
        return self.json['base']['repo']['owner']['login'] != \
               self.json['head']['repo']['owner']['login']

    @property
    def remote_repo(self):
        remote = None
        if self.has_remote_repo:
            remote = Remote(name=self.json['head']['repo']['owner']['login'],
                            url=self.json['head']['repo']['ssh_url'])
        return remote

    def to_commit_info(self):
        return CommitInfo(self.base_sha, self.head_sha, self.remote_repo,
                          self.head_ref)


def get_pr_info(requester, reponame, number):
    "Returns the PullRequest as a PRInfo object"
    resp = requester.get(
        'https://api.github.com/repos/%s/pulls/%s' % (reponame, number))
    return PRInfo(resp.json())

########NEW FILE########
__FILENAME__ = shas_test
import json

from imhotep.testing_utils import fixture_path, Requester
from imhotep.shas import CommitInfo, PRInfo, get_pr_info


# via https://api.github.com/repos/justinabrahms/imhotep/pulls/10
with open(fixture_path('remote_pr.json')) as f:
    remote_json_fixture = json.loads(f.read())

# via https://api.github.com/repos/justinabrahms/imhotep/pulls/1
with open(fixture_path('non_remote_pr.json')) as f:
    not_remote_json = json.loads(f.read())

remote_pr = PRInfo(remote_json_fixture)
non_remote_pr = PRInfo(not_remote_json)


def test_commit_info():
    commit_info = CommitInfo('02c774e4a8d74154468211b14f631748c1d23ef6',
                             '9216c7b61c6dbf547a22e5a5ad282252acc9735f',
                             None,
                             None)
    assert commit_info.commit == '02c774e4a8d74154468211b14f631748c1d23ef6'
    assert commit_info.origin == '9216c7b61c6dbf547a22e5a5ad282252acc9735f'
    assert commit_info.remote_repo is None


def test_pr_info_base_sha():
    assert remote_pr.base_sha == '02c774e4a8d74154468211b14f631748c1d23ef6'


def test_pr_info_head_sha():
    assert remote_pr.head_sha == '9216c7b61c6dbf547a22e5a5ad282252acc9735f'


def test_pr_info_base_ref():
    assert remote_pr.base_ref == 'master'


def test_pr_info_head_ref():
    assert remote_pr.head_ref == 'the-cache-option'


def test_pr_info_has_remote_repo():
    assert remote_pr.has_remote_repo


def test_pr_info_doesnt_have_remote():
    assert not non_remote_pr.has_remote_repo


def test_pr_info_to_commit_info():
    commit_info = remote_pr.to_commit_info()
    assert commit_info.commit == '02c774e4a8d74154468211b14f631748c1d23ef6'
    assert commit_info.origin == '9216c7b61c6dbf547a22e5a5ad282252acc9735f'
    assert commit_info.remote_repo.name == 'scottjab'
    assert commit_info.remote_repo.url == 'git@github.com:scottjab/imhotep.git'


def test_pr_info_to_commit_info_no_remote():
    commit_info = non_remote_pr.to_commit_info()
    assert commit_info.remote_repo is None


def test_pr_info_remote_repo():
    remote = remote_pr.remote_repo
    assert remote.name == 'scottjab'
    assert remote.url == 'git@github.com:scottjab/imhotep.git'


def test_pr_info():
    r = Requester(remote_json_fixture)
    get_pr_info(r, 'justinabrahms/imhotep', 10)
    assert r.url == 'https://api.github.com/repos/justinabrahms/imhotep/pulls/10'

########NEW FILE########
__FILENAME__ = testing_utils
import os
from collections import namedtuple

dir = os.path.dirname(__file__)
fixture_path = lambda s: os.path.join(dir, 'fixtures/', s)

class JsonWrapper(object):
    def __init__(self, json, status):
        self.status_code = status
        self.payload = json

    def json(self):
        return self.payload

class Requester(object):
    def __init__(self, fixture):
        self.fixture = fixture

    def get(self, url):
        self.url = url
        return JsonWrapper(self.fixture, 200)

    def post(self, url, data):
        self.url = url
        self.data = data
        return JsonWrapper(self.fixture, 200)



def calls_matching_re(mockObj, regex):
    matches = []
    for call in mockObj.call_args_list:
        cmd = call[0][0]
        match = regex.search(cmd)
        if match:
            matches.append(call)

    return matches

########NEW FILE########
__FILENAME__ = tools
from collections import defaultdict
import logging

log = logging.getLogger(__name__)


class Tool(object):
    """
    Tool represents a program that runs over source code. It returns a nested
    dictionary structure like:

      {'relative_filename': {'line_number': [error1, error2]}}
      eg: {'imhotep/app.py': {'103': ['line too long']}}
    """

    def __init__(self, command_executor, filenames=set()):
        self.executor = command_executor
        self.filenames = filenames

    def get_configs(self):
        return list()

    def invoke(self, dirname, filenames=set(), linter_configs=set()):
        """
        Main entrypoint for all plugins.

        Returns results in the format of:

        {'filename': {
          'line_number': [
            'error1',
            'error2'
            ]
          }
        }

        """
        retval = defaultdict(lambda: defaultdict(list))
        extensions = ' -o '.join(['-name "*%s"' % ext for ext in
                                  self.get_file_extensions()])

        cmd = 'find %s %s | xargs %s' % (
            dirname, extensions, self.get_command(
                dirname,
                linter_configs=linter_configs))
        result = self.executor(cmd)
        for line in result.split('\n'):
            output = self.process_line(dirname, line)
            if output is not None:
                filename, lineno, messages = output
                if filename.startswith(dirname):
                    filename = filename[len(dirname) + 1:]
                retval[filename][lineno].append(messages)
        return retval

    def process_line(self, dirname, line):
        """
        Processes a line return a 3-element tuple representing (filename,
        line_number, error_messages) or None to indicate no error.

        :param: dirname - directory the code is running in
        """
        raise NotImplementedError()

    def get_file_extensions(self):
        """
        Returns a list of file extensions this tool should run against.

        eg: ['.py', '.js']
        """
        raise NotImplementedError()

    def get_command(self, dirname, linter_configs=set()):
        """
        Returns the command to run for linting. It is piped a list of files to
        run on over stdin.
        """
        raise NotImplementedError()


########NEW FILE########
__FILENAME__ = tools_test
import re

import mock

from .tools import Tool
from .testing_utils import calls_matching_re


class ExampleTool(Tool):
    def process_line(self, dirname, line):
        return None

    def get_file_extensions(self):
        return [".exe"]

    def get_command(self, dirname, linter_configs=set()):
        return "example-cmd"


def test_tool_configs():
    m = mock.Mock()
    t = ExampleTool(m)
    assert len(t.get_configs()) == 0


def test_find_searches_dirname():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile(r'find /woobie/'))) > 0


def test_find_includes_extension():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile(r'-name "\*.exe"'))) > 0


def test_find_includes_multiple_extensions_with_dash_o():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.get_file_extensions = lambda: ['.a', '.b']
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile(r'-name "\*.a" -o -name "\*.b"'))) > 0


def test_invoke_runs_command():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile("example-cmd"))) == 1


def test_calls_process_line_for_each_line():
    m = mock.Mock()
    m.return_value = "1\n2\n3"
    t = ExampleTool(m)
    process_mock = mock.Mock()
    process_mock.return_value = None
    t.process_line = process_mock
    t.invoke('/woobie/')

    assert process_mock.call_count == 3


def test_ignores_none_results_from_process_line():
    m = mock.Mock()
    m.return_value = ""
    process_mock = mock.Mock()
    process_mock.return_value = None
    t = ExampleTool(m)
    t.process_line = process_mock
    retval = t.invoke('/woobie/')

    assert 0 == len(retval.keys())


def test_appends_process_line_results_to_results():
    m = mock.Mock()
    m.return_value = ""
    process_mock = mock.Mock()
    process_mock.return_value = ('filename', 2, 3)
    t = ExampleTool(m)
    t.process_line = process_mock
    retval = t.invoke('/woobie/')

    assert 1 == len(retval.keys())
    assert retval['filename'][2][0] == 3


def test_invoke_removes_dirname_prefix():
    m = mock.Mock()
    m.return_value = ""
    process_mock = mock.Mock()
    process_mock.return_value = ('/my/full/path/and/extras', 2, 3)
    t = ExampleTool(m)
    t.process_line = process_mock
    retval = t.invoke('/my/full/path')

    assert 'and/extras' in retval.keys()

########NEW FILE########
