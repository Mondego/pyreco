__FILENAME__ = core
"""
Core functionality for Domainr.
"""

from argparse import ArgumentParser

import requests
import simplejson as json
from termcolor import colored


class Domain(object):
    """Main class for interacting with the domains API."""

    def environment(self):
        """Parse any command line arguments."""
        parser = ArgumentParser()
        parser.add_argument('query', type=str, nargs='+',
                            help="Your domain name query.")
        parser.add_argument('-i', '--info', action='store_true',
                            help="Get information for a domain name.")
        parser.add_argument('--ascii', action='store_true',
                            help="Use ASCII characters for domain availability.")
        parser.add_argument('--available', action='store_true',
                            help="Only show domain names that are currently available.")
        parser.add_argument('--tld', action='store_true',
                            help="Only check for top-level domains.")
        args = parser.parse_args()
        return args

    def search(self, env):
        """Use domainr to get information about domain names."""
        if env.info:
            url = "https://domai.nr/api/json/info"
        else:
            url = "https://domai.nr/api/json/search"
        query = " ".join(env.query)
        json_data = requests.get(url, params={'q': query})
        data = self.parse(json_data.content, env)
        return data

    def parse(self, content, env):
        """Parse the relevant data from JSON."""
        data = json.loads(content)
        if not env.info:
            # Then we're dealing with a domain name search.
            output = []
            results = data['results']
            for domain in results:
                name = domain['domain']
                availability = domain['availability']
                if availability == 'available':
                    name = colored(name, 'blue', attrs=['bold'])
                    symbol = colored(u"\u2713", 'green')
                    if env.ascii:
                        symbol = colored('A', 'green')
                else:
                    symbol = colored(u"\u2717", 'red')
                    if env.ascii:
                        symbol = colored('X', 'red')
                    # The available flag should skip these.
                    if env.available:
                        continue
                string = "%s  %s" % (symbol, name)
                # Now, a few sanity checks before we add it to the output.
                if env.tld:
                    if self._tld_check(domain['domain']):
                        output.append(string)
                else:
                    output.append(string)
            return '\n'.join(output)
        # Then the user wants information on a domain name.
        return data

    def _tld_check(self, name):
        """Make sure we're dealing with a top-level domain."""
        if name.endswith(".com") or name.endswith(".net") or name.endswith(".org"):
            return True
        return False

    def main(self):
        args = self.environment()
        print self.search(args)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import sys
import unittest
import simplejson as json
from argparse import Namespace
from mock import MagicMock
from domainr import Domain

content = '{"query":"google","results":[{"domain":"google","host":"","subdomain":"google","path":"","availability":"tld","register_url":"http://domai.nr/google/register"},{"domain":"google.com","host":"","subdomain":"google.com","path":"","availability":"taken","register_url":"http://domai.nr/google.com/register"},{"domain":"google.net","host":"","subdomain":"google.net","path":"","availability":"taken","register_url":"http://domai.nr/google.net/register"},{"domain":"google.org","host":"","subdomain":"google.org","path":"","availability":"taken","register_url":"http://domai.nr/google.org/register"},{"domain":"google.co","host":"","subdomain":"google.co","path":"","availability":"taken","register_url":"http://domai.nr/google.co/register"},{"domain":"goo.gle","host":"","subdomain":"goo.gle","path":"","availability":"unavailable","register_url":"http://domai.nr/goo.gle/register"},{"domain":"goo.gl","host":"","subdomain":"goo.gl","path":"/e","availability":"unavailable","register_url":"http://domai.nr/goo.gl/register"},{"domain":"go.gle","host":"","subdomain":"go.gle","path":"","availability":"unavailable","register_url":"http://domai.nr/go.gle/register"},{"domain":"goog","host":"","subdomain":"goog","path":"/le","availability":"tld","register_url":"http://domai.nr/goog/register"},{"domain":"go.gl","host":"","subdomain":"go.gl","path":"/e","availability":"unavailable","register_url":"http://domai.nr/go.gl/register"},{"domain":"g.gle","host":"","subdomain":"g.gle","path":"","availability":"unavailable","register_url":"http://domai.nr/g.gle/register"},{"domain":"goo","host":"","subdomain":"goo","path":"/gle","availability":"tld","register_url":"http://domai.nr/goo/register"},{"domain":"g.gl","host":"","subdomain":"g.gl","path":"/e","availability":"unavailable","register_url":"http://domai.nr/g.gl/register"},{"domain":"gg","host":"","subdomain":"gg","path":"/le","availability":"tld","register_url":"http://domai.nr/gg/register"}]}'
parse_false_response = u'\x1b[31m\u2717\x1b[0m  google\n\x1b[31m\u2717\x1b[0m  google.com\n\x1b[31m\u2717\x1b[0m  google.net\n\x1b[31m\u2717\x1b[0m  google.org\n\x1b[31m\u2717\x1b[0m  google.co\n\x1b[31m\u2717\x1b[0m  goo.gle\n\x1b[31m\u2717\x1b[0m  goo.gl\n\x1b[31m\u2717\x1b[0m  go.gle\n\x1b[31m\u2717\x1b[0m  goog\n\x1b[31m\u2717\x1b[0m  go.gl\n\x1b[31m\u2717\x1b[0m  g.gle\n\x1b[31m\u2717\x1b[0m  goo\n\x1b[31m\u2717\x1b[0m  g.gl\n\x1b[31m\u2717\x1b[0m  gg'
info_data = {'domain': 'google', 'whois_url': 'http://domai.nr/google/whois', 'subregistration_permitted': False, 'register_url': 'http://domai.nr/google/register', 'tld': {'domain': 'google', 'wikipedia_url': 'http://domai.nr/google/wikipedia', 'iana_url': 'http://domai.nr/google/iana'}, 'registrars': [], 'subdomains': [], 'host': '', 'path': '', 'www_url': 'http://domai.nr/google/www', 'query': 'google', 'subdomain': 'google', 'domain_idna': 'google', 'availability': 'tld'}

class TestDomain(unittest.TestCase):


    def setUp(self):
        sys.argv = ['core.py','google']


    def tearDown(self):
        sys.argv = []


    def test_parse_info_false(self):
        domain = Domain()
        result = domain.parse(content, False)
        self.assertEquals(result, parse_false_response)


    def test_parse_info_true(self):
        domain = Domain()
        result = domain.parse(content, True)
        parse_true_response = json.loads(content)
        self.assertEquals(result, parse_true_response)


    def test_search_false(self):
        environment = Namespace(info=False, query=['google'])
        domain = Domain()
        result = domain.search(environment)
        self.assertEquals(result, parse_false_response)


    def test_search_true(self):
        environment = Namespace(info=True, query=['google'])
        domain = Domain()
        result = domain.search(environment)
        self.assertEquals(result, info_data)


    def test_flow(self):
        mock = MagicMock(spec=Domain)
        mock.main()
        mock.environment.assert_called_once()
        mock.search.assert_called_once()
        mock.parse.assert_called_once

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
