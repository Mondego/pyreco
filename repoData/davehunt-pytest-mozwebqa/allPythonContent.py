__FILENAME__ = credentials
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


def read(filename):
    stream = file(filename, 'r')
    import yaml
    return yaml.load(stream)

########NEW FILE########
__FILENAME__ = html_report
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import base64
import cgi
import datetime
import os
import pkg_resources
import py
import time
import sys
import shutil

from py.xml import html
from py.xml import raw

import sauce_labs


class HTMLReport(object):

    def __init__(self, config):
        logfile = os.path.expanduser(os.path.expandvars(config.option.webqa_report_path))
        self.logfile = os.path.normpath(logfile)
        self._debug_path = 'debug'
        self.config = config
        self.test_logs = []
        self.errors = self.failed = 0
        self.passed = self.skipped = 0
        self.xfailed = self.xpassed = 0
        self.resources = ('style.css', 'jquery.js', 'main.js')

    def _debug_paths(self, testclass, testmethod):
        root_path = os.path.join(os.path.dirname(self.logfile), self._debug_path)
        root_path = os.path.normpath(os.path.expanduser(os.path.expandvars(root_path)))
        test_path = os.path.join(testclass.replace('.', '_'), testmethod)
        full_path = os.path.join(root_path, test_path)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        relative_path = os.path.join(self._debug_path, test_path)
        absolute_path = os.path.join(root_path, test_path)
        return (relative_path, full_path)

    def _appendrow(self, result, report):
        import pytest_mozwebqa
        (testclass, testmethod) = pytest_mozwebqa.split_class_and_test_names(report.nodeid)
        time = getattr(report, 'duration', 0.0)

        links = {}
        if hasattr(report, 'debug') and any(report.debug.values()):
            (relative_path, full_path) = self._debug_paths(testclass, testmethod)

            if report.debug['screenshots']:
                filename = 'screenshot.png'
                f = open(os.path.join(full_path, filename), 'wb')
                f.write(base64.decodestring(report.debug['screenshots'][-1]))
                links.update({'Screenshot': os.path.join(relative_path, filename)})

            if report.debug['html']:
                filename = 'html.txt'
                f = open(os.path.join(full_path, filename), 'wb')
                f.write(report.debug['html'][-1])
                links.update({'HTML': os.path.join(relative_path, filename)})

            # Log may contain passwords, etc so we only capture it for tests marked as public
            if report.debug['logs'] and 'public' in report.keywords:
                filename = 'log.txt'
                f = open(os.path.join(full_path, filename), 'wb')
                f.write(report.debug['logs'][-1])
                links.update({'Log': os.path.join(relative_path, filename)})

            if report.debug['network_traffic']:
                filename = 'networktraffic.json'
                f = open(os.path.join(full_path, filename), 'wb')
                f.write(report.debug['network_traffic'][-1])
                links.update({'Network Traffic': os.path.join(relative_path, filename)})

            if report.debug['urls']:
                links.update({'Failing URL': report.debug['urls'][-1]})

        self.sauce_labs_job = None
        if self.config.option.sauce_labs_credentials_file and getattr(report, 'session_id', None):
            self.sauce_labs_job = sauce_labs.Job(report.session_id)
            links['Sauce Labs Job'] = self.sauce_labs_job.url

        links_html = []
        for name, path in links.iteritems():
            links_html.append(html.a(name, href=path, target='_blank'))
            links_html.append(' ')

        additional_html = []

        if not 'Passed' in result:

            if self.sauce_labs_job:
                additional_html.append(self.sauce_labs_job.video_html)

            if 'Screenshot' in links:
                additional_html.append(
                    html.div(
                        html.a(html.img(src=links['Screenshot']),
                               href=links['Screenshot']),
                        class_='screenshot'))

            if report.longrepr:
                log = html.div(class_='log')
                for line in str(report.longrepr).splitlines():
                    separator = line.startswith('_ ' * 10)
                    if separator:
                        log.append(line[:80])
                    else:
                        exception = line.startswith("E   ")
                        if exception:
                            log.append(html.span(raw(cgi.escape(line)),
                                                 class_='error'))
                        else:
                            log.append(raw(cgi.escape(line)))
                    log.append(html.br())
                additional_html.append(log)

        self.test_logs.append(html.tr([
            html.td(result, class_='col-result'),
            html.td(testclass, class_='col-class'),
            html.td(testmethod, class_='col-name'),
            html.td(round(time), class_='col-duration'),
            html.td(links_html, class_='col-links'),
            html.td(additional_html, class_='debug')], class_=result.lower() + ' results-table-row'))

    def _make_report_dir(self):
        logfile_dirname = os.path.dirname(self.logfile)
        if logfile_dirname and not os.path.exists(logfile_dirname):
            os.makedirs(logfile_dirname)
        # copy across the static resources
        for file in self.resources:
            shutil.copyfile(
                pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', file])),
                os.path.abspath(os.path.join(logfile_dirname, file)))
        return logfile_dirname

    def append_pass(self, report):
        self.passed += 1
        self._appendrow('Passed', report)

    def append_failure(self, report):
        if "xfail" in report.keywords:
            self._appendrow('XPassed', report)
            self.xpassed += 1
        else:
            self._appendrow('Failed', report)
            self.failed += 1

    def append_error(self, report):
        self._appendrow('Error', report)
        self.errors += 1

    def append_skipped(self, report):
        if "xfail" in report.keywords:
            self._appendrow('XFailed', report)
            self.xfailed += 1
        else:
            self._appendrow('Skipped', report)
            self.skipped += 1

    def pytest_runtest_logreport(self, report):
        if report.passed:
            if report.when == 'call':
                self.append_pass(report)
        elif report.failed:
            if report.when != "call":
                self.append_error(report)
            else:
                self.append_failure(report)
        elif report.skipped:
            self.append_skipped(report)

    def pytest_sessionstart(self, session):
        self.suite_start_time = time.time()

    def pytest_sessionfinish(self, session, exitstatus, __multicall__):
        self._make_report_dir()
        logfile = py.std.codecs.open(self.logfile, 'w', encoding='utf-8')

        suite_stop_time = time.time()
        suite_time_delta = suite_stop_time - self.suite_start_time
        numtests = self.passed + self.failed + self.xpassed + self.xfailed

        server = self.config.option.sauce_labs_credentials_file and \
                 'Sauce Labs' or 'http://%s:%s' % (self.config.option.host, self.config.option.port)
        browser = self.config.option.browser_name and \
                  self.config.option.browser_version and \
                  self.config.option.platform and \
                  '%s %s on %s' % (str(self.config.option.browser_name).title(),
                                   self.config.option.browser_version,
                                   str(self.config.option.platform).title()) or \
                  self.config.option.environment or \
                  self.config.option.browser

        generated = datetime.datetime.now()
        configuration = {
            'Base URL': self.config.option.base_url,
            'Build': self.config.option.build,
            'Selenium API': self.config.option.api,
            'Driver': self.config.option.driver,
            'Firefox Path': self.config.option.firefox_path,
            'Google Chrome Path': self.config.option.chrome_path,
            'Selenium Server': server,
            'Browser': browser,
            'Timeout': self.config.option.webqatimeout,
            'Capture Network Traffic': self.config.option.capture_network,
            'Credentials': self.config.option.credentials_file,
            'Sauce Labs Credentials': self.config.option.sauce_labs_credentials_file}

        import pytest_mozwebqa
        doc = html.html(
            html.head(
                html.meta(charset='utf-8'),
                html.title('Test Report'),
                html.link(rel='stylesheet', href='style.css'),
                html.script(src='jquery.js'),
                html.script(src='main.js')),
            html.body(
                html.p('Report generated on %s at %s by pytest-mozwebqa %s' % (
                    generated.strftime('%d-%b-%Y'),
                    generated.strftime('%H:%M:%S'),
                    pytest_mozwebqa.__version__)),
                html.h2('Configuration'),
                html.table(
                    [html.tr(html.td(k), html.td(v)) for k, v in sorted(configuration.items()) if v],
                    id='configuration'),
                html.h2('Summary'),
                html.p(
                    '%i tests ran in %i seconds.' % (numtests, suite_time_delta),
                    html.br(),
                    html.span('%i passed' % self.passed, class_='passed'), ', ',
                    html.span('%i skipped' % self.skipped, class_='skipped'), ', ',
                    html.span('%i failed' % self.failed, class_='failed'), ', ',
                    html.span('%i errors' % self.errors, class_='error'), '.',
                    html.br(),
                    html.span('%i expected failures' % self.xfailed, class_='skipped'), ', ',
                    html.span('%i unexpected passes' % self.xpassed, class_='failed'), '.'),
                html.h2('Results'),
                html.table([
                    html.thead(html.tr([
                        html.th('Result', class_='sortable', col='result'),
                        html.th('Class', class_='sortable', col='class'),
                        html.th('Name', class_='sortable', col='name'),
                        html.th('Duration', class_='sortable numeric', col='duration'),
                        html.th('Links')]), id='results-table-head'),
                    html.tbody(*self.test_logs, id='results-table-body')], id='results-table')))

        logfile.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">' + doc.unicode(indent=2))
        logfile.close()

########NEW FILE########
__FILENAME__ = pytest_mozwebqa
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import py
import re
import ConfigParser

import requests

import credentials

__version__ = '1.1'

def pytest_configure(config):
    if not hasattr(config, 'slaveinput'):

        config.addinivalue_line(
            'markers', 'nondestructive: mark the test as nondestructive. ' \
            'Tests are assumed to be destructive unless this marker is ' \
            'present. This reduces the risk of running destructive tests ' \
            'accidentally.')

        if config.option.webqa_report_path:
            from html_report import HTMLReport
            config._html = HTMLReport(config)
            config.pluginmanager.register(config._html)

        if not config.option.run_destructive:
            if config.option.markexpr:
                config.option.markexpr = 'nondestructive and (%s)' % config.option.markexpr
            else:
                config.option.markexpr = 'nondestructive'


def pytest_unconfigure(config):
    html = getattr(config, '_html', None)
    if html:
        del config._html
        config.pluginmanager.unregister(html)


def pytest_sessionstart(session):
    if session.config.option.base_url and not (session.config.option.skip_url_check or session.config.option.collectonly):
        r = requests.get(session.config.option.base_url, verify=False)
        assert r.status_code in (200, 401), 'Base URL did not return status code 200 or 401. (URL: %s, Response: %s)' % (session.config.option.base_url, r.status_code)

    # configure session proxies
    if hasattr(session.config, 'browsermob_session_proxy'):
        session.config.option.proxy_host = session.config.option.bmp_host
        session.config.option.proxy_port = session.config.browsermob_session_proxy.port

    if hasattr(session.config, 'zap'):
        if all([session.config.option.proxy_host, session.config.option.proxy_port]):
            session.config.zap.core.set_option_proxy_chain_name(session.config.option.proxy_host)
            session.config.zap.core.set_option_proxy_chain_port(session.config.option.proxy_port)
        session.config.option.proxy_host = session.config.option.zap_host
        session.config.option.proxy_port = session.config.option.zap_port


def pytest_runtest_setup(item):
    item.debug = {
        'urls': [],
        'screenshots': [],
        'html': [],
        'logs': [],
        'network_traffic': []}
    TestSetup.base_url = item.config.option.base_url

    # configure test proxies
    if hasattr(item.config, 'browsermob_test_proxy'):
        item.config.option.proxy_host = item.config.option.bmp_host
        item.config.option.proxy_port = item.config.browsermob_test_proxy.port

    # consider this environment sensitive if the base url or any redirection
    # history matches the regular expression
    sensitive = False
    if TestSetup.base_url and not item.config.option.skip_url_check:
        r = requests.get(TestSetup.base_url, verify=False)
        urls = [h.url for h in r.history] + [r.url]
        matches = [re.search(item.config.option.sensitive_url, u) for u in urls]
        sensitive = any(matches)

    destructive = 'nondestructive' not in item.keywords

    if (sensitive and destructive):
        first_match = matches[next(i for i, match in enumerate(matches) if match)]

        # skip the test with an appropriate message
        py.test.skip('This test is destructive and the target URL is ' \
                     'considered a sensitive environment. If this test is ' \
                     'not destructive, add the \'nondestructive\' marker to ' \
                     'it. Sensitive URL: %s' % first_match.string)

    if item.config.option.sauce_labs_credentials_file:
        item.sauce_labs_credentials = credentials.read(item.config.option.sauce_labs_credentials_file)

    if item.config.option.credentials_file:
        TestSetup.credentials = credentials.read(item.config.option.credentials_file)

    test_id = '.'.join(split_class_and_test_names(item.nodeid))

    if 'skip_selenium' not in item.keywords:
        if hasattr(item, 'sauce_labs_credentials'):
            from sauce_labs import Client
            TestSetup.selenium_client = Client(
                test_id,
                item.config.option,
                item.keywords,
                item.sauce_labs_credentials)
        else:
            from selenium_client import Client
            TestSetup.selenium_client = Client(
                test_id,
                item.config.option)
        TestSetup.selenium_client.start()
        item.session_id = TestSetup.selenium_client.session_id
        TestSetup.selenium = TestSetup.selenium_client.selenium
        TestSetup.timeout = TestSetup.selenium_client.timeout
        TestSetup.default_implicit_wait = TestSetup.selenium_client.default_implicit_wait
    else:
        TestSetup.timeout = item.config.option.webqatimeout
        TestSetup.selenium = None


def pytest_runtest_teardown(item):
    if hasattr(TestSetup, 'selenium') and TestSetup.selenium and 'skip_selenium' not in item.keywords:
        TestSetup.selenium_client.stop()


def pytest_runtest_makereport(__multicall__, item, call):
    report = __multicall__.execute()
    if report.when == 'call':
        report.session_id = getattr(item, 'session_id', None)
        if hasattr(TestSetup, 'selenium') and TestSetup.selenium and not 'skip_selenium' in item.keywords:
            if report.skipped and 'xfail' in report.keywords or report.failed and 'xfail' not in report.keywords:
                url = TestSetup.selenium_client.url
                url and item.debug['urls'].append(url)
                screenshot = TestSetup.selenium_client.screenshot
                screenshot and item.debug['screenshots'].append(screenshot)
                html = TestSetup.selenium_client.html
                html and item.debug['html'].append(html)
                log = TestSetup.selenium_client.log
                log and item.debug['logs'].append(log)
                report.sections.append(('pytest-mozwebqa', _debug_summary(item.debug)))
            network_traffic = TestSetup.selenium_client.network_traffic
            network_traffic and item.debug['network_traffic'].append(network_traffic)
            report.debug = item.debug
            if hasattr(item, 'sauce_labs_credentials') and report.session_id:
                result = {'passed': report.passed or (report.failed and 'xfail' in report.keywords)}
                import sauce_labs
                sauce_labs.Job(report.session_id).send_result(
                    result,
                    item.sauce_labs_credentials)
    return report


def pytest_funcarg__mozwebqa(request):
    return TestSetup(request)


def pytest_addoption(parser):
    config = ConfigParser.ConfigParser(defaults={
        'baseurl': '',
        'api': 'webdriver'
    })
    config.read('mozwebqa.cfg')

    group = parser.getgroup('selenium', 'selenium')
    group._addoption('--baseurl',
                     action='store',
                     dest='base_url',
                     default=config.get('DEFAULT', 'baseurl'),
                     metavar='url',
                     help='base url for the application under test.')
    group._addoption('--skipurlcheck',
                     action='store_true',
                     dest='skip_url_check',
                     default=False,
                     help='skip the base url and sensitivity checks. (default: %default)')
    group._addoption('--api',
                     action='store',
                     default=config.get('DEFAULT', 'api'),
                     metavar='api',
                     help="version of selenium api to use. 'rc' uses selenium rc. 'webdriver' uses selenium webdriver. (default: %default)")
    group._addoption('--host',
                     action='store',
                     default='localhost',
                     metavar='str',
                     help='host that selenium server is listening on. (default: %default)')
    group._addoption('--port',
                     action='store',
                     type='int',
                     default=4444,
                     metavar='num',
                     help='port that selenium server is listening on. (default: %default)')
    group._addoption('--driver',
                     action='store',
                     dest='driver',
                     default='Remote',
                     metavar='str',
                     help='webdriver implementation. (default: %default)')
    group._addoption('--capability',
                     action='append',
                     dest='capabilities',
                     metavar='str',
                     help='additional capability to set in format "name:value" (webdriver).')
    group._addoption('--chromepath',
                     action='store',
                     dest='chrome_path',
                     metavar='path',
                     help='path to the google chrome driver executable.')
    group._addoption('--firefoxpath',
                     action='store',
                     dest='firefox_path',
                     metavar='path',
                     help='path to the target firefox binary.')
    group._addoption('--firefoxpref',
                     action='append',
                     dest='firefox_preferences',
                     metavar='str',
                     help='firefox preference name and value to set in format "name:value" (webdriver).')
    group._addoption('--profilepath',
                     action='store',
                     dest='profile_path',
                     metavar='str',
                     help='path to the firefox profile to use (webdriver).')
    group._addoption('--extension',
                     action='append',
                     dest='extension_paths',
                     metavar='str',
                     help='path to browser extension to install (webdriver).')
    group._addoption('--chromeopts',
                     action='store',
                     dest='chrome_options',
                     metavar='str',
                     help='json string of google chrome options to set (webdriver).')
    group._addoption('--operapath',
                     action='store',
                     dest='opera_path',
                     metavar='path',
                     help='path to the opera driver.')
    group._addoption('--browser',
                     action='store',
                     dest='browser',
                     metavar='str',
                     help='target browser (standalone rc server).')
    group._addoption('--environment',
                     action='store',
                     dest='environment',
                     metavar='str',
                     help='target environment (grid rc).')
    group._addoption('--browsername',
                     action='store',
                     dest='browser_name',
                     metavar='str',
                     help='target browser name (webdriver).')
    group._addoption('--browserver',
                     action='store',
                     dest='browser_version',
                     metavar='str',
                     help='target browser version (webdriver).')
    group._addoption('--platform',
                     action='store',
                     metavar='str',
                     help='target platform (webdriver).')
    group._addoption('--webqatimeout',
                     action='store',
                     type='int',
                     default=60,
                     metavar='num',
                     help='timeout (in seconds) for page loads, etc. (default: %default)')
    group._addoption('--capturenetwork',
                     action='store_true',
                     dest='capture_network',
                     default=False,
                     help='capture network traffic to test_method_name.json (selenium rc). (default: %default)')
    group._addoption('--build',
                     action='store',
                     dest='build',
                     metavar='str',
                     help='build identifier (for continuous integration).')
    group._addoption('--untrusted',
                     action='store_true',
                     dest='assume_untrusted',
                     default=False,
                     help='assume that all certificate issuers are untrusted. (default: %default)')
    group._addoption('--proxyhost',
                     action='store',
                     dest='proxy_host',
                     metavar='str',
                     help='use a proxy running on this host.')
    group._addoption('--proxyport',
                     action='store',
                     dest='proxy_port',
                     metavar='int',
                     help='use a proxy running on this port.')
    group._addoption('--eventlistener',
                     action='store',
                     dest='event_listener',
                     metavar='str',
                     help='selenium eventlistener class, e.g. package.module.EventListenerClassName (webdriver)')

    group = parser.getgroup('safety', 'safety')
    group._addoption('--sensitiveurl',
                     action='store',
                     dest='sensitive_url',
                     default='(firefox\.com)|(mozilla\.(com|org))',
                     metavar='str',
                     help='regular expression for identifying sensitive urls. (default: %default)')
    group._addoption('--destructive',
                     action='store_true',
                     dest='run_destructive',
                     default=False,
                     help='include destructive tests (tests not explicitly marked as \'nondestructive\'). (default: %default)')

    group = parser.getgroup('credentials', 'credentials')
    group._addoption("--credentials",
                     action="store",
                     dest='credentials_file',
                     metavar='path',
                     help="location of yaml file containing user credentials.")
    group._addoption('--saucelabs',
                     action='store',
                     dest='sauce_labs_credentials_file',
                     metavar='path',
                     help='credendials file containing sauce labs username and api key.')

    group = parser.getgroup("terminal reporting")
    group.addoption('--webqareport',
                    action='store',
                    dest='webqa_report_path',
                    metavar='path',
                    default='results/index.html',
                    help='create mozilla webqa custom report file at given path. (default: %default)')


def split_class_and_test_names(nodeid):
    names = nodeid.split("::")
    names[0] = names[0].replace("/", '.')
    names = [x.replace(".py", "") for x in names if x != "()"]
    classnames = names[:-1]
    classname = ".".join(classnames)
    name = names[-1]
    return (classname, name)


def _debug_summary(debug):
    summary = []
    if debug['urls']:
        summary.append('Failing URL: %s' % debug['urls'][-1])
    return '\n'.join(summary)


class TestSetup:
    '''
        This class is just used for monkey patching
    '''
    def __init__(self, request):
        self.request = request

########NEW FILE########
__FILENAME__ = sauce_labs
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import httplib
import json

import ConfigParser
import pytest
from py.xml import html
from selenium import selenium
from selenium import webdriver

import selenium_client


class Client(selenium_client.Client):

    def __init__(self, test_id, options, keywords, credentials):
        super(Client, self).__init__(test_id, options)

        self.browser_name = options.browser_name
        self.browser_version = options.browser_version
        self.platform = options.platform

        self.keywords = keywords
        self.build = options.build
        self.credentials = credentials

    def check_basic_usage(self):
        super(Client, self).check_basic_usage()

        if not self.credentials['username']:
            raise pytest.UsageError('username must be specified in the sauce labs credentials file.')

        if not self.credentials['api-key']:
            raise pytest.UsageError('api-key must be specified in the sauce labs credentials file.')

    def check_rc_usage(self):
        if not self.browser_name:
            raise pytest.UsageError("--browsername must be specified when using the 'rc' api with sauce labs.")

        if not self.platform:
            raise pytest.UsageError("--platform must be specified when using the 'rc' api with sauce labs.")

    @property
    def common_settings(self):
        config = ConfigParser.ConfigParser(defaults={'tags': ''})
        config.read('mozwebqa.cfg')
        tags = config.get('DEFAULT', 'tags').split(',')
        from _pytest.mark import MarkInfo
        tags.extend([mark for mark in self.keywords.keys() if isinstance(self.keywords[mark], MarkInfo)])
        return {'build': self.build or None,
                'name': self.test_id,
                'tags': tags,
                'public': 'private' not in self.keywords,
                'restricted-public-info': 'public' not in self.keywords}

    def start_webdriver_client(self):
        capabilities = self.common_settings
        capabilities.update({'platform': self.platform,
                             'browserName': self.browser_name})
        if self.browser_version:
            capabilities['version'] = self.browser_version
        for c in self.capabilities:
            name, value = c.split(':')
            # handle integer capabilities
            if value.isdigit():
                value = int(value)
            # handle boolean capabilities
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            capabilities.update({name: value})
        executor = 'http://%s:%s@ondemand.saucelabs.com:80/wd/hub' % (
            self.credentials['username'],
            self.credentials['api-key'])
        self.selenium = webdriver.Remote(command_executor=executor,
                                         desired_capabilities=capabilities)

    def start_rc_client(self):
        settings = self.common_settings
        settings.update({'username': self.credentials['username'],
                         'access-key': self.credentials['api-key'],
                         'os': self.platform,
                         'browser': self.browser_name})
        if self.browser_version:
            settings['browser-version'] = self.browser_version
        self.selenium = selenium('ondemand.saucelabs.com', '80',
                                 json.dumps(settings),
                                 self.base_url)
        self.selenium.start()


class Job(object):

    def __init__(self, session_id):
        self.session_id = session_id

    @property
    def url(self):
        return 'http://saucelabs.com/jobs/%s' % self.session_id

    @property
    def video_html(self):
        flash_vars = 'config={\
            "clip":{\
                "url":"https%%3A//saucelabs.com/jobs/%(session_id)s/video.flv",\
                "provider":"streamer",\
                "autoPlay":false,\
                "autoBuffering":true},\
            "plugins":{\
                "streamer":{\
                    "url":"https://saucelabs.com/flowplayer/flowplayer.pseudostreaming-3.2.5.swf"},\
                "controls":{\
                    "mute":false,\
                    "volume":false,\
                    "backgroundColor":"rgba(0, 0, 0, 0.7)"}},\
            "playerId":"player%(session_id)s",\
            "playlist":[{\
                "url":"https%%3A//saucelabs.com/jobs/%(session_id)s/video.flv",\
                "provider":"streamer",\
                "autoPlay":false,\
                "autoBuffering":true}]}' % {'session_id': self.session_id}

        return html.div(html.object(
            html.param(value='true', name='allowfullscreen'),
            html.param(value='always', name='allowscriptaccess'),
            html.param(value='high', name='quality'),
            html.param(value='true', name='cachebusting'),
            html.param(value='#000000', name='bgcolor'),
            html.param(
                value=flash_vars.replace(' ', ''),
                name='flashvars'),
                width='100%',
                height='100%',
                type='application/x-shockwave-flash',
                data='https://saucelabs.com/flowplayer/flowplayer-3.2.5.swf?0.2930636672245027',
                name='player_api',
                id='player_api'),
            id='player%s' % self.session_id,
            class_='video')

    def send_result(self, result, credentials):
        try:
            basic_authentication = (
                '%s:%s' % (credentials['username'],
                           credentials['api-key'])).encode('base64')[:-1]
            connection = httplib.HTTPConnection('saucelabs.com')
            connection.request(
                'PUT',
                '/rest/v1/%s/jobs/%s' % (credentials['username'], self.session_id),
                json.dumps(result),
                headers={'Authorization': 'Basic %s' % basic_authentication,
                         'Content-Type': 'text/json'})
            connection.getresponse()
        except:
            pass

########NEW FILE########
__FILENAME__ = selenium_client
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

import pytest
from selenium.webdriver.support.event_firing_webdriver import EventFiringWebDriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium import selenium
from selenium import webdriver


class Client(object):

    def __init__(self, test_id, options):
        self.test_id = test_id
        self.host = options.host
        self.port = options.port
        self.base_url = options.base_url
        self.api = options.api.upper()

        self.webdriver = self.api == 'WEBDRIVER'
        self.rc = self.api == 'RC'

        if self.webdriver:
            self.driver = options.driver
            self.capabilities = options.capabilities or []
            self.chrome_path = options.chrome_path
            self.chrome_options = options.chrome_options or '{}'
            self.firefox_path = options.firefox_path
            self.firefox_preferences = options.firefox_preferences or []
            self.profile_path = options.profile_path
            self.extension_paths = options.extension_paths or []
            self.opera_path = options.opera_path
            self.timeout = options.webqatimeout

            if self.driver.upper() == 'REMOTE':
                self.browser_name = options.browser_name
                self.browser_version = options.browser_version
                self.platform = options.platform

            if options.event_listener:
                mod_name, class_name = options.event_listener.rsplit('.', 1)
                mod = __import__(mod_name, fromlist=[class_name])
                self.event_listener = getattr(mod, class_name)
            else:
                self.event_listener = None

        if self.rc:
            self.browser = options.environment or options.browser
            self.timeout = options.webqatimeout * 1000

        self.capture_network = options.capture_network
        self.default_implicit_wait = 10
        self.sauce_labs_credentials = options.sauce_labs_credentials_file
        self.assume_untrusted = options.assume_untrusted
        self.proxy_host = options.proxy_host
        self.proxy_port = options.proxy_port

    def check_usage(self):
        self.check_basic_usage()

        if self.webdriver:
            self.check_webdriver_usage()
        else:
            self.check_rc_usage()

    def check_basic_usage(self):
        if not self.base_url:
            raise pytest.UsageError('--baseurl must be specified.')

    def check_webdriver_usage(self):
        if self.driver.upper() == 'REMOTE':
            if not self.browser_name:
                raise pytest.UsageError("--browsername must be specified when using the 'webdriver' api.")

            if not self.platform:
                raise pytest.UsageError("--platform must be specified when using the 'webdriver' api.")

    def check_rc_usage(self):
        if not self.browser:
            raise pytest.UsageError("--browser or --environment must be specified when using the 'rc' api.")

    def start(self):
        self.check_usage()
        if self.webdriver:
            self.start_webdriver_client()
            self.selenium.implicitly_wait(self.default_implicit_wait)
        else:
            self.start_rc_client()
            self.selenium.set_timeout(self.timeout)
            self.selenium.set_context(self.test_id)

    def start_webdriver_client(self):
        capabilities = {}
        for c in self.capabilities:
            name, value = c.split(':')
            # handle integer capabilities
            if value.isdigit():
                value = int(value)
            # handle boolean capabilities
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            capabilities.update({name: value})
        if self.proxy_host and self.proxy_port:
            proxy = Proxy()
            proxy.http_proxy = '%s:%s' % (self.proxy_host, self.proxy_port)
            proxy.ssl_proxy = proxy.http_proxy
            proxy.add_to_capabilities(capabilities)
        profile = None

        if self.driver.upper() == 'REMOTE':
            capabilities.update(getattr(webdriver.DesiredCapabilities, self.browser_name.upper()))
            if json.loads(self.chrome_options) or self.extension_paths:
                capabilities = self.create_chrome_options(
                    self.chrome_options,
                    self.extension_paths).to_capabilities()
            if self.browser_name.upper() == 'FIREFOX':
                profile = self.create_firefox_profile(
                    self.firefox_preferences,
                    self.profile_path,
                    self.extension_paths)
            if self.browser_version:
                capabilities['version'] = self.browser_version
            capabilities['platform'] = self.platform.upper()
            executor = 'http://%s:%s/wd/hub' % (self.host, self.port)
            try:
                self.selenium = webdriver.Remote(command_executor=executor,
                                                 desired_capabilities=capabilities or None,
                                                 browser_profile=profile)
            except AttributeError:
                valid_browsers = [attr for attr in dir(webdriver.DesiredCapabilities) if not attr.startswith('__')]
                raise AttributeError("Invalid browser name: '%s'. Valid options are: %s" % (self.browser_name, ', '.join(valid_browsers)))

        elif self.driver.upper() == 'CHROME':
            options = None
            if self.chrome_options or self.extension_paths:
                options = self.create_chrome_options(
                    self.chrome_options,
                    self.extension_paths)
            if self.chrome_path:
                self.selenium = webdriver.Chrome(executable_path=self.chrome_path,
                                                 chrome_options=options,
                                                 desired_capabilities=capabilities or None)
            else:
                self.selenium = webdriver.Chrome(chrome_options=options,
                                                 desired_capabilities=capabilities or None)

        elif self.driver.upper() == 'FIREFOX':
            binary = self.firefox_path and FirefoxBinary(self.firefox_path) or None
            profile = self.create_firefox_profile(
                self.firefox_preferences,
                self.profile_path,
                self.extension_paths)
            self.selenium = webdriver.Firefox(
                firefox_binary=binary,
                firefox_profile=profile,
                capabilities=capabilities or None)
        elif self.driver.upper() == 'IE':
            self.selenium = webdriver.Ie()
        elif self.driver.upper() == 'OPERA':
            capabilities.update(webdriver.DesiredCapabilities.OPERA)
            self.selenium = webdriver.Opera(executable_path=self.opera_path,
                                            desired_capabilities=capabilities)
        else:
            self.selenium = getattr(webdriver, self.driver)()

        if self.event_listener is not None and not isinstance(self.selenium, EventFiringWebDriver):
            self.selenium = EventFiringWebDriver(self.selenium, self.event_listener())

    def start_rc_client(self):
        self.selenium = selenium(self.host, str(self.port), self.browser, self.base_url)

        if self.capture_network:
            self.selenium.start('captureNetworkTraffic=true')
        else:
            self.selenium.start()

    @property
    def session_id(self):
        if self.webdriver:
            return self.selenium.session_id
        else:
            return self.selenium.get_eval('selenium.sessionId')

    def create_firefox_profile(self, preferences, profile_path, extensions):
        profile = webdriver.FirefoxProfile(profile_path)
        for p in preferences:
            name, value = p.split(':')
            # handle integer preferences
            if value.isdigit():
                value = int(value)
            # handle boolean preferences
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            profile.set_preference(name, value)
        profile.assume_untrusted_cert_issuer = self.assume_untrusted
        profile.update_preferences()
        for extension in extensions:
            profile.add_extension(extension)
        return profile

    def create_chrome_options(self, preferences, extensions):
        options = webdriver.ChromeOptions()
        options_from_json = json.loads(preferences)

        if 'arguments' in options_from_json:
            for args_ in options_from_json['arguments']:
                options.add_argument(args_)

        if 'binary_location' in options_from_json:
            options.binary_location = options_from_json['binary_location']

        for extension in extensions:
            options.add_extension(extension)

        return options

    @property
    def screenshot(self):
        try:
            if self.webdriver:
                screenshot = self.selenium.get_screenshot_as_base64()
            else:
                screenshot = self.selenium.capture_entire_page_screenshot_to_string('')
            return screenshot
        except:
            return None

    @property
    def html(self):
        try:
            if self.webdriver:
                html = self.selenium.page_source
            else:
                html = self.selenium.get_html_source()
            return html.encode('utf-8')
        except:
            return None

    @property
    def log(self):
        try:
            if self.rc:
                return self.selenium.get_log().encode('utf-8')
        except:
            return None

    @property
    def network_traffic(self):
        try:
            if self.rc and self.capture_network:
                return self.selenium.captureNetworkTraffic('json')
        except:
            return None

    @property
    def url(self):
        try:
            if self.webdriver:
                url = self.selenium.current_url
            else:
                url = self.selenium.get_location()
            return url
        except:
            return None

    def stop(self):
        try:
            if self.webdriver:
                self.selenium.quit()
            else:
                self.selenium.stop()
        except:
            pass

########NEW FILE########
__FILENAME__ = conftest
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from webserver import SimpleWebServer

pytest_plugins = 'pytester'


def pytest_sessionstart(session):
    webserver = SimpleWebServer()
    webserver.start()
    WebServer.webserver = webserver


def pytest_sessionfinish(session, exitstatus):
    WebServer.webserver.stop()


def pytest_internalerror(excrepr):
    if hasattr(WebServer, 'webserver'):
        WebServer.webserver.stop()


def pytest_keyboard_interrupt(excinfo):
    if hasattr(WebServer, 'webserver'):
        WebServer.webserver.stop()


def pytest_funcarg__webserver(request):
    return WebServer.webserver


class WebServer:

    pass

########NEW FILE########
__FILENAME__ = test_credentials
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testCredentials(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        @pytest.mark.nondestructive
        def test_credentials(mozwebqa):
            assert mozwebqa.credentials['default']['username'] == 'aUsername'
            assert mozwebqa.credentials['default']['password'] == 'aPassword'
    """)
    credentials = testdir.makefile('.yaml', credentials="""
        default:
            username: aUsername
            password: aPassword
    """)
    result = testdir.runpytest('--baseurl=http://localhost:%s' % webserver.port,
                               '--credentials=%s' % credentials,
                               '--driver=firefox')
    assert result.ret == 0


def testCredentialsKeyError(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        @pytest.mark.nondestructive
        def test_credentials(mozwebqa):
            assert mozwebqa.credentials['default']['password'] == 'aPassword'
    """)
    credentials = testdir.makefile('.yaml', credentials="""
        default:
            username: aUsername
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--credentials=%s' % credentials,
                                '--driver=firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == "KeyError: 'password'"

########NEW FILE########
__FILENAME__ = test_debug
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]

failure_files = ('screenshot.png', 'html.txt')
log_file = 'log.txt'
network_traffic_file = 'networktraffic.json'


def testDebugOnFail(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') != 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=result.html',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    path = _test_debug_path(str(testdir.tmpdir))
    for file in failure_files:
        assert os.path.exists(os.path.join(path, file))
        assert os.path.isfile(os.path.join(path, file))


def testDebugOnXFail(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.xfail
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') != 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=result.html',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(skipped) == 1
    path = _test_debug_path(str(testdir.tmpdir))
    for file in failure_files:
        assert os.path.exists(os.path.join(path, file))
        assert os.path.isfile(os.path.join(path, file))


def testNoDebugOnPass(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=result.html',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1
    debug_path = os.path.sep.join([str(testdir.tmpdir), 'debug'])
    assert not os.path.exists(debug_path)


def testNoDebugOnXPass(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.xfail
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=result.html',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    debug_path = os.path.sep.join([str(testdir.tmpdir), 'debug'])
    assert not os.path.exists(debug_path)


def testNoDebugOnSkip(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skipif('True')
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=result.html',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(skipped) == 1
    debug_path = os.path.sep.join([str(testdir.tmpdir), 'debug'])
    assert not os.path.exists(debug_path)


def testDebugWithReportSubdirectory(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') != 'Success!'
    """)
    report_subdirectory = 'report'
    reprec = testdir.inline_run(
        '--baseurl=http://localhost:%s' % webserver.port,
        '--api=rc',
        '--browser=*firefox',
        '--webqareport=%s/result.html' % report_subdirectory,
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    path = _test_debug_path(os.path.join(str(testdir.tmpdir),
                                         report_subdirectory))
    for file in failure_files:
        assert os.path.exists(os.path.join(path, file))
        assert os.path.isfile(os.path.join(path, file))


def testLogWhenPublic(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.public
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') != 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=result.html',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    path = _test_debug_path(str(testdir.tmpdir))
    assert os.path.exists(os.path.join(path, log_file))
    assert os.path.isfile(os.path.join(path, log_file))


def testNoLogWhenNotPublic(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') != 'Success!'
    """)
    reprec = testdir.inline_run(
        '--baseurl=http://localhost:%s' % webserver.port,
        '--api=rc',
        '--browser=*firefox',
        '--webqareport=result.html',
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    path = _test_debug_path(str(testdir.tmpdir))
    assert not os.path.exists(os.path.join(path, log_file))


def testNoLogWhenPrivate(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.private
        @pytest.mark.nondestructive
        def test_debug(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') != 'Success!'
    """)
    reprec = testdir.inline_run(
        '--baseurl=http://localhost:%s' % webserver.port,
        '--api=rc',
        '--browser=*firefox',
        '--webqareport=result.html',
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    path = _test_debug_path(str(testdir.tmpdir))
    assert not os.path.exists(os.path.join(path, log_file))


def testCaptureNetworkTraffic(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_capture_network_traffic(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    reprec = testdir.inline_run(
        '--baseurl=http://localhost:%s' % webserver.port,
        '--api=rc',
        '--browser=*firefox',
        '--capturenetwork',
        '--webqareport=index.html',
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1
    path = _test_debug_path(str(testdir.tmpdir))
    json_data = open(os.path.join(path, network_traffic_file))
    import json
    data = json.load(json_data)
    json_data.close()
    assert len(data) > 0


def _test_debug_path(root_path):
    debug_path = os.path.join(root_path, 'debug')
    for i in range(2):
        debug_path = os.path.join(debug_path, os.listdir(debug_path)[0])
    return debug_path

########NEW FILE########
__FILENAME__ = test_destructive
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testDestructiveTestsNotRunByDefault(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port, file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 0


def testNonDestructiveTestsRunByDefault(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port, file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testDestructiveTestsRunWhenForced(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--destructive',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testBothDestructiveAndNonDestructiveTestsRunWhenForced(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        @pytest.mark.nondestructive
        def test_selenium1(mozwebqa):
            assert True
        @pytest.mark.skip_selenium
        def test_selenium2(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--destructive',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 2


def testSkipDestructiveTestsIfForcedAndRunningAgainstSensitiveURL(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--sensitiveurl=localhost',
                                '--destructive',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(skipped) == 1


@pytest.mark.parametrize('baseurl', [
    'http://addons.mozilla.org',
    'http://www.mozilla.com',
    'http://marketplace.firefox.com'])
def testSkipDestructiveTestsIfForcedAndRunningAgainstDefaultSensitiveURL(testdir, baseurl):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.skip_selenium
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=%s' % baseurl,
                                '--destructive',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(skipped) == 1

########NEW FILE########
__FILENAME__ = test_rc_client
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testStartRCClientUsingEnvironment(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--environment=*firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testStartRCClientUsingBrowser(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

########NEW FILE########
__FILENAME__ = test_report
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testReportWithoutDirectory(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_report(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    report = 'result.html'
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=%s' % report,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1
    report_file = os.path.sep.join([str(testdir.tmpdir), report])
    assert os.path.exists(report_file)
    assert os.path.isfile(report_file)


def testReportWithDirectory(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_report(mozwebqa):
            mozwebqa.selenium.open('/')
            assert mozwebqa.selenium.get_text('css=h1') == 'Success!'
    """)
    report = 'report/result.html'
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqareport=%s' % report,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1
    report_file = os.path.sep.join([str(testdir.tmpdir), report])
    assert os.path.exists(report_file)
    assert os.path.isfile(report_file)

########NEW FILE########
__FILENAME__ = test_timeout
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testWebDriverWithDefaultTimeout(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_timeout(mozwebqa):
            assert mozwebqa.timeout == 60
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=webdriver',
                                '--driver=firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testWebDriverWithCustomTimeout(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_timeout(mozwebqa):
            assert mozwebqa.timeout == 30
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=webdriver',
                                '--driver=firefox',
                                '--webqatimeout=30',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testRCWithDefaultTimeout(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_timeout(mozwebqa):
            assert mozwebqa.timeout == 60000
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testRCWithCustomTimeout(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_timeout(mozwebqa):
            assert mozwebqa.timeout == 30000
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--browser=*firefox',
                                '--webqatimeout=30',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

########NEW FILE########
__FILENAME__ = test_usage
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testShouldFailWithoutBaseURL(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run(file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: --baseurl must be specified.'


def testShouldFailWithoutBrowserNameWhenUsingWebDriverAPI(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port, file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: --browsername must be specified when using ' \
                  "the 'webdriver' api."


def testShouldFailWithoutPlatformWhenUsingWebDriverAPI(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--browsername=firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: --platform must be specified when using the ' \
                  "'webdriver' api."


def testShouldFailWithoutSauceLabsUser(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    sauce_labs_credentials = testdir.makefile('.yaml', sauce_labs="""
        api-key: api-key
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--saucelabs=%s' % sauce_labs_credentials,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == "KeyError: 'username'"


def testShouldFailWithoutSauceLabsKey(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    sauce_labs_credentials = testdir.makefile('.yaml', sauce_labs="""
        username: username
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--saucelabs=%s' % sauce_labs_credentials,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == "KeyError: 'api-key'"


def testShouldFailWithBlankSauceLabsUser(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    sauce_labs_credentials = testdir.makefile('.yaml', sauce_labs="""
        username:
        api-key: api-key
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--saucelabs=%s' % sauce_labs_credentials,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: username must be specified in the sauce labs ' \
                  'credentials file.'


def testShouldFailWithBlankSauceLabsKey(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    sauce_labs_credentials = testdir.makefile('.yaml', sauce_labs="""
        username: username
        api-key:
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--saucelabs=%s' % sauce_labs_credentials,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: api-key must be specified in the sauce labs ' \
                  'credentials file.'


def testShouldFailWithoutBrowserNameWhenUsingSauceWithRCAPI(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    sauce_labs_credentials = testdir.makefile('.yaml', sauce_labs="""
        username: username
        api-key: api-key
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--saucelabs=%s' % sauce_labs_credentials,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: --browsername must be specified when using ' \
                  "the 'rc' api with sauce labs."


def testShouldFailWithoutPlatformWhenUsingSauceWithRCAPI(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    sauce_labs_credentials = testdir.makefile('.yaml', sauce_labs="""
        username: username
        api-key: api-key
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                '--saucelabs=%s' % sauce_labs_credentials,
                                '--browsername=firefox',
                                '--browserver=10',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: --platform must be specified when using the ' \
                  "'rc' api with sauce labs."


def testShouldFailWithoutBrowserOrEnvironmentWhenUsingRCAPI(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=rc',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    assert out == 'UsageError: --browser or --environment must be specified ' \
                  "when using the 'rc' api."


def testShouldErrorThatItCantFindTheChromeBinary(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            assert True
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--driver=chrome',
                                '--chromeopts={"binary_location":"foo"}',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(failed) == 1
    out = failed[0].longrepr.reprcrash.message
    if 'ChromeDriver executable needs to be available in the path' in out:
        pytest.fail('You must have Chrome Driver installed on your path for this test to run correctly. '
                    'For further information see pytest-mozwebqa documentation.')
    assert 'Could not find Chrome binary at: foo' in out

########NEW FILE########
__FILENAME__ = test_webdriver_client
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from selenium.webdriver.support.abstract_event_listener import AbstractEventListener

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]


def testStartWebDriverClient(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get(mozwebqa.base_url)
            header = mozwebqa.selenium.find_element_by_tag_name('h1')
            assert header.text == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=webdriver',
                                '--driver=firefox',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testSpecifyingFirefoxProfile(testdir, webserver):
    """Test that a specified profile is used when starting firefox.
        The profile changes the colors in the browser, which are then reflected when calling
        value_of_css_property.
    """
    profile = testdir.tmpdir.mkdir('profile')
    profile.join('prefs.js').write(
        'user_pref("browser.anchor_color", "#FF69B4");'
        'user_pref("browser.display.foreground_color", "#FF0000");'
        'user_pref("browser.display.use_document_colors", false);')
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get(mozwebqa.base_url)
            header = mozwebqa.selenium.find_element_by_tag_name('h1')
            anchor = mozwebqa.selenium.find_element_by_tag_name('a')
            header_color = header.value_of_css_property('color')
            anchor_color = anchor.value_of_css_property('color')
            assert header_color == 'rgba(255, 0, 0, 1)'
            assert anchor_color == 'rgba(255, 105, 180, 1)'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=webdriver',
                                '--driver=firefox',
                                '--profilepath=%s' % profile,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testSpecifyingFirefoxProfileAndOverridingPreferences(testdir, webserver):
    """Test that a specified profile is used when starting firefox.
        The profile changes the colors in the browser, which are then reflected when calling
        value_of_css_property. The test checks that the color of the h1 tag is overridden by
        the profile, while the color of the a tag is overridden by the preference.
    """
    profile = testdir.tmpdir.mkdir('profile')
    profile.join('prefs.js').write(
        'user_pref("browser.anchor_color", "#FF69B4");'
        'user_pref("browser.display.foreground_color", "#FF0000");'
        'user_pref("browser.display.use_document_colors", false);')
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get(mozwebqa.base_url)
            header = mozwebqa.selenium.find_element_by_tag_name('h1')
            anchor = mozwebqa.selenium.find_element_by_tag_name('a')
            header_color = header.value_of_css_property('color')
            anchor_color = anchor.value_of_css_property('color')
            assert header_color == 'rgba(255, 0, 0, 1)'
            assert anchor_color == 'rgba(255, 0, 0, 1)'
    """)
    reprec = testdir.inline_run(
        '--baseurl=http://localhost:%s' % webserver.port,
        '--api=webdriver',
        '--driver=firefox',
        '--firefoxpref=extensions.checkCompatibility.nightly:false',
        '--firefoxpref=browser.anchor_color:#FF0000',
        '--profilepath=%s' % profile,
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1


def testAddingFirefoxExtension(testdir, webserver):
    """Test that a firefox extension can be added when starting firefox."""
    import os
    path_to_extensions_folder = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'testing')
    extension = os.path.join(path_to_extensions_folder, 'empty.xpi')
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get('about:support')
            extensions = mozwebqa.selenium.find_element_by_id('extensions-tbody').text
            assert 'Test Extension (empty)' in extensions
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=webdriver',
                                '--driver=firefox',
                                '--extension=''%s''' % extension,
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

def testFirefoxProxy(testdir, webserver):
    """Test that a proxy can be set for firefox."""
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get('http://example.com')
            header = mozwebqa.selenium.find_element_by_tag_name('h1')
            assert header.text == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
        '--api=webdriver',
        '--driver=firefox',
        '--proxyhost=localhost',
        '--proxyport=%s' % webserver.port,
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

@pytest.mark.chrome
def testChromeProxy(testdir, webserver):
    """Test that a proxy can be set for chrome."""
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get('http://example.com')
            header = mozwebqa.selenium.find_element_by_tag_name('h1')
            assert header.text == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
        '--api=webdriver',
        '--driver=chrome',
        '--proxyhost=localhost',
        '--proxyport=%s' % webserver.port,
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

@pytest.mark.opera
def testOperaProxy(testdir, webserver):
    """Test that a proxy can be set for opera."""
    file_test = testdir.makepyfile("""
        import pytest
        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            mozwebqa.selenium.get('http://example.com')
            header = mozwebqa.selenium.find_element_by_tag_name('h1')
            assert header.text == 'Success!'
    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
        '--api=webdriver',
        '--driver=opera',
        '--proxyhost=localhost',
        '--proxyport=%s' % webserver.port,
        file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

def testEventListeningWebDriverClientHook(testdir, webserver):
    file_test = testdir.makepyfile("""
        import pytest
        from selenium.webdriver.support.event_firing_webdriver import EventFiringWebDriver

        @pytest.mark.nondestructive
        def test_selenium(mozwebqa):
            # Make sure the webdriver client was wrapped
            assert isinstance(mozwebqa.selenium, EventFiringWebDriver)
            with pytest.raises(Exception) as e:
                mozwebqa.selenium.get(mozwebqa.base_url)
            # Make sure the event hook explodes as expected
            assert 'before_navigate_to' in e.exconly()

    """)
    reprec = testdir.inline_run('--baseurl=http://localhost:%s' % webserver.port,
                                '--api=webdriver',
                                '--driver=firefox',
                                '--eventlistener=test_webdriver_client.ConcreteEventListener',
                                file_test)
    passed, skipped, failed = reprec.listoutcomes()
    assert len(passed) == 1

class ConcreteEventListener(AbstractEventListener):
    def before_navigate_to(self, url, driver):
        raise Exception('before_navigate_to')

########NEW FILE########
__FILENAME__ = webserver
# Copyright 2008-2009 WebDriver committers
# Copyright 2008-2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A simple web server for testing purposes."""

import logging
import os
import socket
import threading
import urllib
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 8000


class HtmlOnlyHandler(BaseHTTPRequestHandler):
    """Http handler."""

    def do_GET(self):
        """GET method handler."""

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('<html><body><h1>Success!</h1><a href="#">Anchor text</a></body></html>')

    def log_message(self, format, *args):
        """Override default to avoid trashing stderr"""
        pass


class SimpleWebServer(object):
    """A very basic web server."""

    def __init__(self, port=DEFAULT_PORT):
        self.stop_serving = False
        port = port
        while True:
            try:
                self.server = HTTPServer(
                    ('', port), HtmlOnlyHandler)
                self.port = port
                break
            except socket.error:
                LOGGER.debug("port %d is in use, trying to use next one"
                              % port)
                port += 1

        self.thread = threading.Thread(target=self._run_web_server)

    def _run_web_server(self):
        """Runs the server loop."""
        LOGGER.debug("web server started")
        while not self.stop_serving:
            self.server.handle_request()
        self.server.server_close()

    def start(self):
        """Starts the server."""
        self.thread.start()

    def stop(self):
        """Stops the server."""
        self.stop_serving = True
        try:
            # This is to force stop the server loop
            urllib.URLopener().open("http://localhost:%d" % self.port)
        except Exception:
            pass
        LOGGER.info("Shutting down the webserver")
        self.thread.join()


def main(argv=None):
    from optparse import OptionParser
    from time import sleep

    if argv is None:
        import sys
        argv = sys.argv

    parser = OptionParser("%prog [options]")
    parser.add_option("-p", "--port", dest="port", type="int",
            help="port to listen (default: %s)" % DEFAULT_PORT,
            default=DEFAULT_PORT)

    opts, args = parser.parse_args(argv[1:])
    if args:
        parser.error("wrong number of arguments")  # Will exit

    server = SimpleWebServer(opts.port)
    server.start()
    print "Server started on port %s, hit CTRL-C to quit" % opts.port
    try:
        while 1:
            sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

########NEW FILE########
