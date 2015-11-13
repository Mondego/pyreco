__FILENAME__ = add_site_config
#!/usr/bin/env python

# wwwhisper - web access control.
# Copyright (C) 2012, 2013 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Configures wwwhisper for a given site.

Creates site-specific Django settings files. Creates configuration
file for supervisor (http://supervisord.org/), which allows to
start wwwhisper application under the control of the supervisor
daemon. Initializes database to store access control list.
"""

import getopt
import os
import sys
import random
import subprocess

from urlparse import urlparse

SITES_DIR = 'sites'
DJANGO_CONFIG_DIR = 'django'
DJANGO_CONFIG_FILE = 'site_settings.py'
SUPERVISOR_CONFIG_DIR = 'supervisor'
SUPERVISOR_CONFIG_FILE= 'site.conf'
DB_DIR = 'db'
DB_NAME = 'acl_db'

WWWHISPER_USER = 'wwwhisper'
WWWHISPER_GROUP = 'www-data'
DEFAULT_INITIAL_LOCATIONS = ['/', '/wwwhisper/admin/']

def err_quit(errmsg):
    """Prints an error message and quits."""
    print >> sys.stderr, errmsg
    sys.exit(1)

def usage():
    print """

Generates site-specific configuration files and initializes wwwhisper database.

--site-url, --admin-email and --location are only initial settings,
wwwhisper web application can be used to add/remove locations and
grant/revoke access to other users.

Usage:

  %(prog)s
      -s, --site-url A URL of a site to protect in a form
            scheme://domain(:port). Scheme can be https (recomended) or http.
            Port defaults to 443 for https and 80 for http.
      -a, --admin-email An email of a user that will be allowed to access
            initial locations. Multiple emails can be given with multiple
            -a directives.
      -l, --location A location that admin users will be able to access
            initially (defaults to /admin/ and /). Multiple locations can
            be given with mutliple -l directives.
      -o, --output-dir A directory to store configuration (defaults to
            '%(config-dir)s' in the wwwhisper directory).
      -n, --no-supervisor Do not generate config file for supervisord.
""" % {'prog': sys.argv[0], 'config-dir': SITES_DIR}
    sys.exit(1)

def generate_secret_key():
    """Generates a secret key to be used with django setting file.

    Uses cryptographically secure generator. Displays a warning and
    generates a key that does not parse if the system does not provide
    a secure generator.
    """
    try:
        secure_generator = random.SystemRandom()
        allowed_chars='abcdefghijklmnopqrstuvwxyz'\
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'\
            '!@#$%^&*(-_=+'
        key_length = 50
        # This gives log2((26+26+10+14)**50) == 312 bits of entropy
        return ''.join(
            [secure_generator.choice(allowed_chars) for i in range(key_length)])
    except NotImplementedError:
        # The system does not support generation of secure random
        # numbers. Return something that raises parsing error and
        # points the user to a place where secret key needs to be
        # filled manually.
        message = ('Your system does not allow to automatically '
                   'generate secure secret keys.')
        print >> sys.stderr, ('WARNING: You need to edit configuration file '
                              'manually. ' + message)
        return ('\'---' + message + ' Replace this text with a long, '
                'unpredictable secret string (at least 50 characters).')


def write_to_file(dir_path, file_name, file_content):
    """Writes a string to a file with a given name in a given directory.

    If the file does not exist it is created. Dies on error.
    """
    file_path = os.path.join(dir_path, file_name)
    try:
        with open(file_path, 'w') as destination:
            destination.write(file_content)
    except IOError as ex:
        err_quit('Failed to create file %s: %s.' % (file_path, ex))

def create_django_config_file(site_url, emails, locations, django_config_path,
                              db_path):
    """Creates a site specific Django configuration file.

    Settings that are common for all sites reside in the
    wwwhisper_service module.
    """

    settings = """# Don't share this with anybody.
SECRET_KEY = '%s'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '%s',
    }
}

WWWHISPER_INITIAL_SITE_URL = '%s'
WWWHISPER_INITIAL_ADMINS = (%s,)
WWWHISPER_INITIAL_LOCATIONS = (%s,)
""" % (generate_secret_key(),
       os.path.join(db_path, DB_NAME),
       site_url,
       ", ".join("'" + email + "'" for email in emails),
       ", ".join("'" + location + "'" for location in locations))
    write_to_file(django_config_path, '__init__.py', '')
    write_to_file(django_config_path, DJANGO_CONFIG_FILE, settings)

def default_port(scheme):
    """Returns default port for a given scheme (https or http) as string."""
    if scheme == "https":
        return "443"
    elif scheme == "http":
        return "80"
    assert False

def is_default_port(scheme, port):
    """Checks if a port (string) is default for a given scheme."""
    return default_port(scheme) == port

def create_supervisor_config_file(
    site_dir_name, wwwhisper_path, site_config_path, supervisor_config_path):
    """Creates site-specific supervisor config file.

    The file allows to start the wwwhisper application for the site.
    """
    settings = """[program:wwwhisper-%s]
command=%s/run_wwwhisper_for_site.sh -d %s
user=%s
group=%s
autorestart=true
stopwaitsecs=2
stopsignal=INT
stopasgroup=true
""" % (site_dir_name, wwwhisper_path, site_config_path, WWWHISPER_USER,
       WWWHISPER_GROUP)
    write_to_file(
        supervisor_config_path, SUPERVISOR_CONFIG_FILE, settings)

def parse_url(url):
    """Parses and validates a URL.

    URL needs to have scheme://hostname:port format, scheme and hostname
    are mandatory, port is optional. Converts scheme and hostname to
    lower case and returns scheme, hostname, port (as string) tupple.
    Dies if the URL is invalid.
    """

    err_prefix = 'Invalid site address - '
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    if scheme == '' or scheme not in ('https', 'http'):
        err_quit(err_prefix + 'scheme missing. '
                 'URL schould start with https:// (recommended) or http://')
    if parsed_url.hostname is None:
        err_quit(err_prefix + 'host name missing.'
                 'URL should include full host name (like https://foo.org).')
    if parsed_url.path  != '':
        err_quit(err_prefix + 'URL should not include resource path '
                 '(/foo/bar).')
    if parsed_url.params  != '':
        err_quit(err_prefix + 'URL should not include parameters (;foo=bar).')
    if parsed_url.query  != '':
        err_quit(err_prefix + 'URL should not include query (?foo=bar).')
    if parsed_url.fragment  != '':
        err_quit(err_prefix + 'URL should not include query (#foo).')
    if parsed_url.username != None:
        err_quit(err_prefix + 'URL should not include username (foo@).')

    hostname = parsed_url.hostname.lower()
    port = None
    if parsed_url.port is not None:
        port = str(parsed_url.port)
    else:
        port = default_port(scheme)

    return (scheme, hostname, port)

def main():
    site_url = None
    emails = []
    locations = []
    wwwhisper_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    output_path = os.path.join(wwwhisper_path, SITES_DIR)
    need_supervisor = True

    try:
        optlist, _ = getopt.gnu_getopt(
            sys.argv[1:],
            's:a:l:o:nh',
            ['site-url=',
             'admin-email=',
             'locations=',
             'output-dir=',
             'no-supervisor',
             'help'])

    except getopt.GetoptError, ex:
        print 'Arguments parsing error: ', ex,
        usage()

    for opt, arg in optlist:
        if opt in ('-h', '--help'):
            usage()
        elif opt in ('-s', '--site-url'):
            site_url = arg
        elif opt in ('-a', '--admin-email'):
            emails.append(arg)
        elif opt in ('-l', '--location'):
            locations.append(arg)
        elif opt in ('-o', '--output-dir'):
            output_path = arg
        elif opt in ('-n', '--no-supervisor'):
            need_supervisor = False
        else:
            assert False, 'unhandled option'


    if site_url is None:
        err_quit('--site-url is missing.')
    if not emails:
        err_quit('--admin-email is missing.')
    if not locations:
        locations += DEFAULT_INITIAL_LOCATIONS

    (scheme, hostname, port) = parse_url(site_url)
    site_url = scheme + '://' + hostname
    # URL should include the port number only if it is non-default.
    if not is_default_port(scheme, port):
        site_url += ":" + port
    # But settings directory name should always include the port.
    site_dir_name = '.'.join([scheme, hostname, port])

    site_config_path = os.path.join(output_path, site_dir_name)
    django_config_path = os.path.join(site_config_path, DJANGO_CONFIG_DIR)
    db_path = os.path.join(site_config_path, DB_DIR)
    supervisor_config_path = os.path.join(
        site_config_path, SUPERVISOR_CONFIG_DIR)
    try:
        os.umask(067)
        os.makedirs(site_config_path, 0710)
        os.umask(077)
        os.makedirs(django_config_path)
        os.makedirs(db_path)
        if need_supervisor:
            os.makedirs(supervisor_config_path)
    except OSError as ex:
        err_quit('Failed to initialize configuration directory %s: %s.'
                 % (site_config_path, ex))

    create_django_config_file(
        site_url, emails, locations, django_config_path, db_path)

    if need_supervisor:
        create_supervisor_config_file(
            site_dir_name, wwwhisper_path, site_config_path,
            supervisor_config_path)

    manage_path = os.path.join(wwwhisper_path, 'manage.py')
    # Use Python from the virtual environment to run syncdb.
    exit_status = subprocess.call(
        ['/usr/bin/env', 'python', manage_path, 'syncdb',
         '--pythonpath=' + django_config_path])
    if exit_status != 0:
        err_quit('Failed to initialize wwwhisper database.');

    print 'Site configuration successfully created.'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
#
# This script requires path to a directory with site-specific
# settings. It should be run like this:
# python manage.py test --pythonpath=../sites/SCHEME.DOMAIN.PORT/django \
#    wwwhisper_auth wwwhisper_admin
#
# For convenience during development, development version of
# site_settings.py can be put in wwwhisper_service directory.

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "wwwhisper_service.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
"""Nothing here.

wwwhisper_admin depends on model defined by wwwhisper_auth.
"""

########NEW FILE########
__FILENAME__ = tests_views
# wwwhisper - web access control.
# Copyright (C) 2012 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from wwwhisper_auth.models import Site
from wwwhisper_auth.tests.utils import HttpTestCase
from wwwhisper_auth.tests.utils import TEST_SITE

import json

FAKE_UUID = '41be0192-0fcc-4a9c-935d-69243b75533c'
TEST_USER_EMAIL = 'foo@bar.org'
TEST_LOCATION = '/pub/kika/'
TEST_ALIAS = 'https://foo.example.org'

def uid_regexp():
    return '[0-9a-z-]{36}'

def extract_uuid(urn):
    return urn.replace('urn:uuid:', '')

class AdminViewTestCase(HttpTestCase):

    def add_user(self, user_name=TEST_USER_EMAIL):
        response = self.post('/admin/api/users/', {'email' : user_name})
        self.assertEqual(201, response.status_code)
        return json.loads(response.content)

    def add_location(self):
        response = self.post('/admin/api/locations/', {'path' : TEST_LOCATION})
        self.assertEqual(201, response.status_code)
        return json.loads(response.content)

    def add_alias(self):
        response = self.post('/admin/api/aliases/', {'url' : TEST_ALIAS})
        self.assertEqual(201, response.status_code)
        return json.loads(response.content)


class UserTest(AdminViewTestCase):

    def test_add_user(self):
        response = self.post('/admin/api/users/', {'email' : TEST_USER_EMAIL})
        self.assertEqual(201, response.status_code)

        parsed_response_body = json.loads(response.content)
        user_uuid = extract_uuid(parsed_response_body['id'])

        self.assertRegexpMatches(parsed_response_body['id'],
                                 '^urn:uuid:%s$' % uid_regexp())
        self.assertEqual(TEST_USER_EMAIL, parsed_response_body['email'])
        self_url = '%s/admin/api/users/%s/' % (TEST_SITE, user_uuid)
        self.assertEqual(self_url, parsed_response_body['self'])
        self.assertEqual(self_url, response['Location'])
        self.assertEqual(self_url, response['Content-Location'])

    def test_get_user(self):
        parsed_add_user_response_body = self.add_user()
        get_response = self.get(parsed_add_user_response_body['self'])
        self.assertEqual(200, get_response.status_code)
        parsed_get_response_body = json.loads(get_response.content)
        self.assertEqual(parsed_add_user_response_body,
                         parsed_get_response_body)

    def test_delete_user(self):
        user_url = self.add_user()['self']
        self.assertEqual(204, self.delete(user_url).status_code)
        self.assertEqual(404, self.get(user_url).status_code)

    def test_get_users_list(self):
        self.assertEqual(201, self.post('/admin/api/users/',
                                        {'email' : 'foo@bar.org'}).status_code)
        self.assertEqual(201, self.post('/admin/api/users/',
                                        {'email' : 'baz@bar.org'}).status_code)
        self.assertEqual(201, self.post('/admin/api/users/',
                                        {'email' : 'boo@bar.org'}).status_code)
        response = self.get('/admin/api/users/')
        self.assertEqual(200, response.status_code)
        parsed_response_body = json.loads(response.content)
        self.assertEqual('%s/admin/api/users/' % TEST_SITE,
                         parsed_response_body['self'])

        users = parsed_response_body['users']
        self.assertEqual(3, len(users))
        self.assertItemsEqual(['foo@bar.org', 'baz@bar.org', 'boo@bar.org'],
                              [item['email'] for item in users])

    def test_get_not_existing_user(self):
        response = self.get('/admin/api/users/%s/' % FAKE_UUID)
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content, 'User not found')

    def test_add_user_invalid_email(self):
        response = self.post('/admin/api/users/', {'email' : 'foo.bar'})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Invalid email format')

    def test_add_existing_user(self):
        self.add_user()
        response = self.post('/admin/api/users/', {'email' : TEST_USER_EMAIL})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'User already exists')

    def test_delete_user_twice(self):
        user_url = self.add_user()['self']
        response = self.delete(user_url)
        self.assertEqual(204, response.status_code)

        response = self.delete(user_url)
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content, 'User not found')

    def test_users_limit(self):
        limit = 8
        Site.users_limit = limit
        for i in range(0, limit):
            email = '%s%d' % (TEST_USER_EMAIL, i)
            response = self.post('/admin/api/users/', {'email' : email})
            self.assertEqual(201, response.status_code)

        email = '%s%d' % (TEST_USER_EMAIL, limit)
        response = self.post('/admin/api/users/', {'email' : email})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Users limit exceeded')

class LocationTest(AdminViewTestCase):

    def test_add_location(self):
        response = self.post('/admin/api/locations/', {'path' : TEST_LOCATION})
        self.assertEqual(201, response.status_code)

        parsed_response_body = json.loads(response.content)
        location_uuid = extract_uuid(parsed_response_body['id'])

        self.assertRegexpMatches(parsed_response_body['id'],
                                 '^urn:uuid:%s$' % uid_regexp())
        self.assertEqual(TEST_LOCATION, parsed_response_body['path'])
        self.assertTrue('openAccess' not in parsed_response_body)
        self_url = '%s/admin/api/locations/%s/' % (TEST_SITE, location_uuid)
        self.assertEqual(self_url, parsed_response_body['self'])
        self.assertEqual(self_url, response['Location'])
        self.assertEqual(self_url, response['Content-Location'])

    def test_get_location(self):
        parsed_add_location_response_body = self.add_location()
        get_response = self.get(parsed_add_location_response_body['self'])
        self.assertEqual(200, get_response.status_code)
        parsed_get_response_body = json.loads(get_response.content)
        self.assertEqual(parsed_add_location_response_body,
                         parsed_get_response_body)

    def test_grant_open_access_to_location(self):
        location = self.add_location()
        self.assertTrue('openAccess' not in location)

        open_access_url = location['self'] + 'open-access/'
        put_response = self.put(open_access_url, {'requireLogin' : False})
        parsed_response_body = json.loads(put_response.content)
        self.assertEqual(201, put_response.status_code)
        self.assertEqual(open_access_url, put_response['Location'])
        self.assertEqual(open_access_url, parsed_response_body['self'])
        self.assertFalse(parsed_response_body['requireLogin'])

        # Get location again and make sure openAccess attribute is now true.
        location = json.loads(self.get(location['self']).content)
        self.assertTrue('openAccess' in location)
        self.assertFalse(location['openAccess']['requireLogin'])

    def test_grant_authenticated_open_access_to_location(self):
        location = self.add_location()
        self.assertTrue('openAccess' not in location)

        open_access_url = location['self'] + 'open-access/'
        put_response = self.put(open_access_url, {'requireLogin' : True})
        parsed_response_body = json.loads(put_response.content)
        self.assertEqual(201, put_response.status_code)
        self.assertEqual(open_access_url, put_response['Location'])
        self.assertEqual(open_access_url, parsed_response_body['self'])
        self.assertTrue(parsed_response_body['requireLogin'])

        # Get location again and make sure openAccess attribute is now true.
        location = json.loads(self.get(location['self']).content)
        self.assertTrue(location['openAccess']['requireLogin'])

    def test_grant_open_access_to_location_if_already_granted(self):
        location = self.add_location()
        open_access_url = location['self'] + 'open-access/'
        put_response1 = self.put(open_access_url, {'requireLogin' : False})
        put_response2 = self.put(open_access_url, {'requireLogin' : False})
        self.assertEqual(200, put_response2.status_code)
        self.assertFalse(put_response2.has_header('Location'))
        self.assertEqual(put_response1.content, put_response2.content)

    def test_change_require_login_for_open_location(self):
        location = self.add_location()
        open_access_url = location['self'] + 'open-access/'
        put_response1 = self.put(open_access_url, {'requireLogin' : False})
        put_response2 = self.put(open_access_url, {'requireLogin' : True})
        self.assertEqual(200, put_response2.status_code)
        self.assertFalse(put_response2.has_header('Location'))
        self.assertNotEqual(put_response1.content, put_response2.content)
        parsed_response_body = json.loads(put_response2.content)
        self.assertTrue(parsed_response_body['requireLogin'])

    def test_check_open_access_to_location(self):
        location = self.add_location()
        open_access_url = location['self'] + 'open-access/'
        self.put(open_access_url, {'requireLogin' : False})
        get_response = self.get(open_access_url)
        parsed_response_body = json.loads(get_response.content)
        self.assertEqual(200, get_response.status_code)
        self.assertEqual(open_access_url, parsed_response_body['self'])
        self.assertFalse(parsed_response_body['requireLogin'])

    def test_revoke_open_access_to_location(self):
        location = self.add_location()
        open_access_url = location['self'] + 'open-access/'
        self.put(open_access_url, {'requireLogin' : False})
        delete_response = self.delete(open_access_url)
        self.assertEqual(204, delete_response.status_code)
        get_response = self.get(open_access_url)
        self.assertEqual(404, get_response.status_code)

    def test_revoke_open_access_to_location_if_already_revoked(self):
        location = self.add_location()
        open_access_url = location['self'] + 'open-access/'
        self.put(open_access_url, {'requireLogin' : False})
        self.delete(open_access_url)
        delete_response = self.delete(open_access_url)
        self.assertEqual(404, delete_response.status_code)

    def test_delete_location(self):
        location_url = self.add_location()['self']
        self.assertEqual(204, self.delete(location_url).status_code)
        self.assertEqual(404, self.get(location_url).status_code)

    def test_get_locations_list(self):
        self.assertEqual(201, self.post('/admin/api/locations/',
                                        {'path' : '/foo/bar'}).status_code)
        self.assertEqual(201, self.post('/admin/api/locations/',
                                        {'path' : '/baz/bar'}).status_code)
        self.assertEqual(201, self.post('/admin/api/locations/',
                                        {'path' : '/boo/bar/'}).status_code)
        response = self.get('/admin/api/locations/')
        self.assertEqual(200, response.status_code)
        parsed_response_body = json.loads(response.content)
        self.assertEquals('%s/admin/api/locations/' % TEST_SITE,
                          parsed_response_body['self'])

        locations = parsed_response_body['locations']
        self.assertEqual(3, len(locations))
        self.assertItemsEqual(['/foo/bar', '/baz/bar', '/boo/bar/'],
                              [item['path'] for item in locations])

    def test_get_not_existing_location(self):
        response = self.get('/admin/api/locations/%s/' % FAKE_UUID)
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content, 'Location not found')

    def test_add_location_invalid_path(self):
        response = self.post('/admin/api/locations/', {'path' : '/foo/../bar'})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Path should be absolute and normalized')

    def test_add_existing_location(self):
        self.add_location()
        response = self.post('/admin/api/locations/', {'path' : TEST_LOCATION})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Location already exists')

    def test_delete_location_twice(self):
        location_url = self.add_location()['self']
        response = self.delete(location_url)
        self.assertEqual(204, response.status_code)

        response = self.delete(location_url)
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content, 'Location not found')

    def test_locations_limit(self):
        limit = 7
        Site.locations_limit = limit
        for i in range(0, limit):
            path = '%s%d' % (TEST_LOCATION, i)
            response = self.post('/admin/api/locations/', {'path' : path})
            self.assertEqual(201, response.status_code)
        path = '%s%d' % (TEST_LOCATION, limit)
        response = self.post('/admin/api/locations/', {'path' : path})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Locations limit exceeded')

class AccessControlTest(AdminViewTestCase):

    def can_access(self, location_url, user_uuid):
        response = self.get(location_url + 'allowed-users/' + user_uuid + '/')
        self.assertTrue(response.status_code == 200
                        or response.status_code == 404)
        return response.status_code == 200

    def test_grant_access(self):
        location_url = self.add_location()['self']

        response = self.add_user()
        user_url = response['self']
        user_urn = response['id']
        user_uuid = extract_uuid(user_urn)

        response = self.put(location_url + 'allowed-users/' + user_uuid + '/')
        self.assertEqual(201, response.status_code)

        parsed_response_body = json.loads(response.content)
        resource_url = location_url + 'allowed-users/' + user_uuid + '/'
        self.assertEqual(resource_url, response['Location'])
        self.assertFalse(response.has_header('Content-Location'))
        self.assertEqual(resource_url, parsed_response_body['self'])
        self.assertEqual(user_url, parsed_response_body['user']['self'])
        self.assertEqual(user_urn, parsed_response_body['user']['id'])
        self.assertEqual(TEST_USER_EMAIL, parsed_response_body['user']['email'])

    def test_grant_access_creates_allowed_user_resource(self):
        location_url = self.add_location()['self']

        response = self.add_user()
        user_uuid = extract_uuid(response['id'])

        self.assertFalse(self.can_access(location_url, user_uuid))
        self.put(location_url + 'allowed-users/' + user_uuid + "/")
        self.assertTrue(self.can_access(location_url, user_uuid))

    def test_revoke_access(self):
        location_url = self.add_location()['self']

        response = self.add_user()
        user_uuid = extract_uuid(response['id'])

        # Allow access.
        self.put(location_url + 'allowed-users/' + user_uuid + "/")
        self.assertTrue(self.can_access(location_url, user_uuid))

        # Revoke access.
        response = self.delete(
            location_url + 'allowed-users/' + user_uuid + "/")
        self.assertEqual(204, response.status_code)
        self.assertFalse(self.can_access(location_url, user_uuid))

    def test_location_lists_allowed_users(self):
        location_url = self.add_location()['self']

        # Create two users.
        user1_urn = self.add_user('user1@acme.com')['id']
        user1_uuid = extract_uuid(user1_urn)

        user2_urn = self.add_user('user2@acme.com')['id']
        user2_uuid = extract_uuid(user2_urn)

        self.put(location_url + 'allowed-users/' + user1_uuid + "/")
        self.put(location_url + 'allowed-users/' + user2_uuid + "/")

        response = self.get(location_url)
        parsed_response_body = json.loads(response.content)
        allowed_users = parsed_response_body['allowedUsers']
        self.assertEqual(2, len(allowed_users))
        self.assertItemsEqual(['user1@acme.com', 'user2@acme.com'],
                              [item['email'] for item in allowed_users])
        self.assertItemsEqual([user1_urn, user2_urn],
                              [item['id'] for item in allowed_users])

    def test_grant_access_to_not_existing_location(self):
        location_url = '/admin/api/locations/%s/' % FAKE_UUID
        user_uuid = extract_uuid(self.add_user()['id'])

        response = self.put(location_url + 'allowed-users/' + user_uuid + '/')
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content, 'Location not found')

    def test_grant_access_for_not_existing_user(self):
        location_url = self.add_location()['self']
        user_uuid =  FAKE_UUID

        response = self.put(location_url + 'allowed-users/' + user_uuid + '/')
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content, 'User not found')

    # PUT should be indempontent, granting access for the second time
    # should not return an error.
    def test_grant_access_twice(self):
        location_url = self.add_location()['self']

        response = self.add_user()
        user_url = response['self']
        user_uuid = extract_uuid(response['id'])

        response1 = self.put(location_url + 'allowed-users/' + user_uuid + "/")
        self.assertEqual(201, response1.status_code)
        self.assertTrue(response1.has_header('Location'))

        response2 = self.put(location_url + 'allowed-users/' + user_uuid + "/")
        self.assertEqual(200, response2.status_code)
        self.assertFalse(response2.has_header('Location'))

        self.assertEqual(response1.content, response2.content)

    def test_revoke_access_twice(self):
        location_url = self.add_location()['self']

        response = self.add_user()
        user_url = response['self']
        user_uuid = extract_uuid(response['id'])

        # Allow access.
        self.put(location_url + 'allowed-users/' + user_uuid + "/")
        self.assertTrue(self.can_access(location_url, user_uuid))

        # Revoke access.
        response = self.delete(
            location_url + 'allowed-users/' + user_uuid + "/")
        self.assertEqual(204, response.status_code)

        response = self.delete(
            location_url + 'allowed-users/' + user_uuid + "/")
        self.assertEqual(404, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'User can not access location.')

        self.assertFalse(self.can_access(location_url, user_uuid))


class AliasTest(AdminViewTestCase):

    def test_add_alias(self):
        response = self.post('/admin/api/aliases/', {'url' : TEST_ALIAS})
        self.assertEqual(201, response.status_code)

        parsed_response_body = json.loads(response.content)
        alias_uuid = extract_uuid(parsed_response_body['id'])

        self.assertRegexpMatches(parsed_response_body['id'],
                                 '^urn:uuid:%s$' % uid_regexp())
        self.assertEqual(TEST_ALIAS, parsed_response_body['url'])
        self_url = '%s/admin/api/aliases/%s/' % (TEST_SITE, alias_uuid)
        self.assertEqual(self_url, parsed_response_body['self'])
        self.assertEqual(self_url, response['Location'])
        self.assertEqual(self_url, response['Content-Location'])


    def test_get_alias(self):
        parsed_post_response_body = self.add_alias()
        get_response = self.get(parsed_post_response_body['self'])
        self.assertEqual(200, get_response.status_code)
        parsed_get_response_body = json.loads(get_response.content)
        self.assertEqual(parsed_post_response_body, parsed_get_response_body)

    def test_delete_alias(self):
        alias_url = self.add_alias()['self']
        self.assertEqual(204, self.delete(alias_url).status_code)
        self.assertEqual(404, self.get(alias_url).status_code)

    def test_get_aliases_list(self):
        self.assertEqual(201, self.post('/admin/api/aliases/',
                                        {'url' : 'http://foo.org'}).status_code)
        self.assertEqual(201, self.post('/admin/api/aliases/',
                                        {'url' : 'http://bar.org'}).status_code)
        response = self.get('/admin/api/aliases/')
        self.assertEqual(200, response.status_code)
        parsed_response_body = json.loads(response.content)
        self.assertEqual('%s/admin/api/aliases/' % TEST_SITE,
                         parsed_response_body['self'])

        aliases = parsed_response_body['aliases']
        # Two created aliases + the original one.
        self.assertEqual(3, len(aliases))
        self.assertItemsEqual(['http://foo.org', 'http://bar.org',
                               'https://foo.example.org:8080'],
                              [item['url'] for item in aliases])

class SkinTest(AdminViewTestCase):

    def test_get_skin(self):
        response = self.get('/admin/api/skin/')
        self.assertEqual(200, response.status_code)
        skin = json.loads(response.content)
        self.assertEqual('wwwhisper: Web Access Control', skin['title'])
        self.assertEqual('Protected site', skin['header'])
        self.assertRegexpMatches(skin['message'], 'Access to this site is')
        self.assertTrue(skin['branding'])

    def test_put_skin(self):
        response = self.put('/admin/api/skin/',
                            {'title': 'xyz',
                             'header': 'foo',
                             'message': 'bar',
                             'branding': False})
        self.assertEqual(200, response.status_code)
        skin = json.loads(response.content)
        self.assertEqual('xyz', skin['title'])
        self.assertEqual('foo', skin['header'])
        self.assertRegexpMatches('bar', skin['message'])
        self.assertFalse(skin['branding'])

    def test_put_invalid_skin(self):
        response = self.put('/admin/api/skin/',
                            {'title': 'xyz' * 1000,
                             'header': '',
                             'message': '',
                             'branding': False})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Failed to update login page')

########NEW FILE########
__FILENAME__ = urls
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Urls exposed by the wwwhisper_admin application."""

from django.conf.urls import patterns, url
from views import CollectionView, ItemView, SkinView
from views import OpenAccessView, AllowedUsersView

urlpatterns = patterns(
    'wwwhisper_admin.views',
    url(r'^users/$',
        CollectionView.as_view(collection_name='users')),
    url(r'^users/(?P<uuid>[0-9a-z-]+)/$',
        ItemView.as_view(collection_name='users'),
        name='wwwhisper_user'),
    url(r'^locations/$',
        CollectionView.as_view(collection_name='locations')),
    url(r'^locations/(?P<uuid>[0-9a-z-]+)/$',
        ItemView.as_view(collection_name='locations'),
        name='wwwhisper_location'),
    url(r'^locations/(?P<location_uuid>[0-9a-z-]+)/allowed-users/' +
        '(?P<user_uuid>[0-9a-z-]+)/$',
        AllowedUsersView.as_view(),
        name='wwwhisper_allowed_user'),
    url(r'^locations/(?P<location_uuid>[0-9a-z-]+)/open-access/$',
        OpenAccessView.as_view()),
    url(r'^aliases/$',
        CollectionView.as_view(collection_name='aliases')),
    url(r'^aliases/(?P<uuid>[0-9a-z-]+)/$',
        ItemView.as_view(collection_name='aliases'),
        name='wwwhisper_alias'),
    url(r'^skin/$', SkinView.as_view()),
    )

########NEW FILE########
__FILENAME__ = views
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Views that allow to manage access control list.

Expose REST interface for adding/removing locations and users and for
granting/revoking access to locations.
"""

from django.forms import ValidationError
from functools import wraps
from wwwhisper_auth import http
from wwwhisper_auth.models import LimitExceeded

import logging

logger = logging.getLogger(__name__)

def _full_url(request):
    return request.site_url + request.path

def set_collection(decorated_function):
    @wraps(decorated_function)
    def wrapper(self, request, **kwargs):
        self.collection = getattr(request.site, self.collection_name)
        return decorated_function(self, request, **kwargs)
    return wrapper

class CollectionView(http.RestView):
    """Generic view over a collection of resources.

    Allows to get json representation of all resources in the
    collection and to add new resources to the collection.

    Attributes:
        collection_name: Name of the collection that view represents.
    """

    collection_name = None

    @set_collection
    def post(self, request, **kwargs):
        """Ads a new resource to the collection.

        Args:
            **kwargs: holds collection dependent arguments that are
              used to create the resource.
        Returns json representation of the added resource."""
        try:
            created_item = self.collection.create_item(**kwargs)
        except ValidationError as ex:
            # ex.messages is a list of errors.
            return http.HttpResponseBadRequest(', '.join(ex.messages))
        except LimitExceeded as ex:
            return http.HttpResponseLimitExceeded(str(ex))

        attributes_dict = created_item.attributes_dict(request.site_url)
        response = http.HttpResponseCreated(attributes_dict)
        response['Location'] = attributes_dict['self']
        response['Content-Location'] = attributes_dict['self']
        return response

    @set_collection
    def get(self, request):
        """Returns json representation of all resources in the collection."""
        items_list = [item.attributes_dict(request.site_url)
                      for item in self.collection.all()]
        return http.HttpResponseOKJson({
                'self' : _full_url(request),
                self.collection_name: items_list
                })

class ItemView(http.RestView):
    """Generic view over a single resource stored in a collection.

    Allows to get json representation of the resource and to delete
    the resource.

    Attributes:
        collection_name: Name of the collection that view uses to retrieve
           the resource.
    """

    collection_name = None

    @set_collection
    def get(self, request, uuid):
        """Returns json representation of a resource with a given uuid."""
        item = self.collection.find_item(uuid)
        if item is None:
            return http.HttpResponseNotFound(
                '%s not found' % self.collection.item_name.capitalize())
        return http.HttpResponseOKJson(item.attributes_dict(request.site_url))

    @set_collection
    def delete(self, request, uuid):
        """Deletes a resource with a given uuid."""
        deleted = self.collection.delete_item(uuid)
        if not deleted:
            return http.HttpResponseNotFound(
                '%s not found' % self.collection.item_name.capitalize())
        return http.HttpResponseNoContent()

class OpenAccessView(http.RestView):
    """Manages resources that define if a location is open.

    An open location can be accessed by everyone either without
    authentication (requireLogin is false) or with authentication.
    """

    @staticmethod
    def _attributes_dict(request, location):
        """Attributes representing a resource to which a request is related."""
        return {
            'self' : _full_url(request),
            'requireLogin': location.open_access_requires_login()
            }

    def put(self, request, location_uuid, requireLogin):
        """Creates a resource that enables open access to a given location."""
        location = request.site.locations.find_item(location_uuid)
        if location is None:
            return http.HttpResponseNotFound('Location not found.')

        if location.open_access_granted():
            if (location.open_access_requires_login() != requireLogin):
                location.grant_open_access(requireLogin);
            return http.HttpResponseOKJson(
                self._attributes_dict(request, location))

        location.grant_open_access(require_login=requireLogin)
        response =  http.HttpResponseCreated(
            self._attributes_dict(request, location))
        response['Location'] = _full_url(request)
        return response

    def get(self, request, location_uuid):
        """Check if a resource that enables open access to a location exists."""
        location = request.site.locations.find_item(location_uuid)
        if location is None:
            return http.HttpResponseNotFound('Location not found.')
        if not location.open_access_granted():
            return http.HttpResponseNotFound(
                'Open access to location disallowed.')
        return http.HttpResponseOKJson(
            self._attributes_dict(request, location))

    def delete(self, request, location_uuid):
        """Deletes a resource.

        Disables open access to a given location.
        """
        location = request.site.locations.find_item(location_uuid)
        if location is None:
            return http.HttpResponseNotFound('Location not found.')
        if not location.open_access_granted():
            return http.HttpResponseNotFound(
                'Open access to location already disallowed.')
        location.revoke_open_access()
        return http.HttpResponseNoContent()

class AllowedUsersView(http.RestView):
    """Manages resources that define which users can access locations."""

    def put(self, request, location_uuid, user_uuid):
        """Creates a resource.

        Grants access to a given location by a given user.
        """
        location = request.site.locations.find_item(location_uuid)
        if not location:
            return http.HttpResponseNotFound('Location not found.')
        try:
            (permission, created) = location.grant_access(user_uuid)
            attributes_dict = permission.attributes_dict(request.site_url)
            if created:
                response =  http.HttpResponseCreated(attributes_dict)
                response['Location'] = attributes_dict['self']
            else:
                response = http.HttpResponseOKJson(attributes_dict)
            return response
        except LookupError as ex:
            return http.HttpResponseNotFound(str(ex))

    def get(self, request, location_uuid, user_uuid):
        """Checks if a resource that grants access exists.

        This is not equivalent of checking if the user can access the
        location. If the location is open, but the user is not
        explicitly granted access, not found failure is returned.
        """
        location = request.site.locations.find_item(location_uuid)
        if location is None:
            return http.HttpResponseNotFound('Location not found.')
        try:
            permission = location.get_permission(user_uuid)
            return http.HttpResponseOKJson(
                permission.attributes_dict(request.site_url))
        except LookupError as ex:
            return http.HttpResponseNotFound(str(ex))

    def delete(self, request, location_uuid, user_uuid):
        """Deletes a resource.

        Revokes access to a given location by a given user. If the
        location is open, the user will still be able to access the
        location after this call succeeds.
        """
        location = request.site.locations.find_item(location_uuid)
        if not location:
            return http.HttpResponseNotFound('Location not found.')
        try:
            location.revoke_access(user_uuid)
            return http.HttpResponseNoContent()
        except LookupError as ex:
            return http.HttpResponseNotFound(str(ex))


class SkinView(http.RestView):
    """Configures the login page."""

    def put(self, request, title, header, message, branding):
        try:
            request.site.update_skin(title=title, header=header,
                                     message=message, branding=branding)
        except ValidationError as ex:
            return http.HttpResponseBadRequest(
                'Failed to update login page: ' + ', '.join(ex.messages))
        return http.HttpResponseOKJson(request.site.skin())

    def get(self, request):
        return http.HttpResponseOKJson(request.site.skin())

########NEW FILE########
__FILENAME__ = assets
# wwwhisper - web access control.
# Copyright (C) 2013 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import cache_page
from django.views.generic import View
from wwwhisper_auth import http


class Asset:
    """Stores a static file to be returned by requests."""

    def __init__(self, prefix, *args):
        assert prefix is not None
        self.body = file(os.path.join(prefix, *args)).read()


class StaticFileView(View):
    """ A view to serve a single static file."""

    asset = None

    @method_decorator(cache_control(private=True, max_age=60 * 60 * 5))
    def get(self, request):
        return self.do_get(self.asset.body)

class HtmlFileView(StaticFileView):

    def do_get(self, body):
        return http.HttpResponseOKHtml(body)

class JsFileView(StaticFileView):

    def do_get(self, body):
        return http.HttpResponseOKJs(body)

########NEW FILE########
__FILENAME__ = backend
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Authentication backend used by wwwhisper_auth."""

from django.contrib.auth.backends import ModelBackend
from django.forms import ValidationError
from django_browserid.base import verify
from models import LimitExceeded

class AssertionVerificationException(Exception):
    """Raised when BrowserId assertion was not verified successfully."""
    pass

class BrowserIDBackend(ModelBackend):
    """"Backend that verifies BrowserID assertion.

    Similar backend is defined in django_browserid application. It is not
    used here, because it does not allow to distinguish between an
    assertion verification error and an unknown user.
    """

    # TODO: Put site_url in the model and find it based on id. Allow
    # for aliases.
    def authenticate(self, site, site_url, assertion):
        """Verifies BrowserID assertion

        Returns:
             Object that represents a user with an email verified by
             the assertion. If a user with such email does not exists,
             but there are open locations that require login, the user
             object is created. In other cases, None is returned.

        Raises:
            AssertionVerificationException: verification failed.
        """
        result = verify(assertion=assertion, audience=site_url)
        if not result:
            # TODO: different error if Persona is down.
            raise AssertionVerificationException(
                'BrowserID assertion verification failed.')
        email = result['email']
        user = site.users.find_item_by_email(result['email'])
        if user is not None:
            return user
        try:
            # The site has open locations that require login, every
            # user needs to be allowed.
            #
            # TODO: user objects created in such way should probably
            # be marked and automatically deleted on logout or after
            # some time of inactivity.
            if site.locations.has_open_location_with_login():
                return site.users.create_item(email)
            else:
                return None
        except ValidationError as ex:
            raise AssertionVerificationException(', '.join(ex.messages))
        except LimitExceeded as ex:
            raise AssertionVerificationException(str(ex))

########NEW FILE########
__FILENAME__ = email_re
"""Regexp to validates email that is used by BrowserId.

From node-validator, Copyright (c) 2010 Chris O'Hara:
https://github.com/chriso/node-validator/blob/master/lib/validators.js
https://github.com/chriso/node-validator/blob/master/LICENSE
"""

EMAIL_VALIDATION_RE = r"^(?:[\w\!\#\$\%\&\'\*\+\-\/\=\?\^\`\{\|\}\~]+\.)*[\w\!\#\$\%\&\'\*\+\-\/\=\?\^\`\{\|\}\~]+@(?:(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-](?!\.)){0,61}[a-zA-Z0-9]?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9\-](?!$)){0,61}[a-zA-Z0-9]?)|(?:\[(?:(?:[01]?\d{1,2}|2[0-4]\d|25[0-5])\.){3}(?:[01]?\d{1,2}|2[0-4]\d|25[0-5])\]))$"

########NEW FILE########
__FILENAME__ = http
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Utils to simplify REST style views.

Contains classes representing commonly used HTTP responses with
appropriate content types and encoding.
"""

from django.conf import settings
from django.http import HttpResponse
from django.middleware import csrf
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import patch_cache_control
from django.views.generic import View
from functools import wraps
from wwwhisper_auth import models

import json
import logging
import re
import traceback

logger = logging.getLogger(__name__)

TEXT_MIME_TYPE = 'text/plain; charset=utf-8'
HTML_MIME_TYPE = 'text/html; charset=utf-8'
JSON_MIME_TYPE = 'application/json; charset=utf-8'
JS_MIME_TYPE = 'text/javascript; charset=UTF-8'

_accepts_html_re = re.compile('text/(html|\*)|(\*/\*)')

def accepts_html(accept_header):
    """Checks if the 'Accept' header accepts html response.

    Args:
       accept_header: A string, for example 'audio/*, text/plain, text/*'
    """
    return (accept_header is not None
            and _accepts_html_re.search(accept_header) is not None)

class HttpResponseOK(HttpResponse):
    """"Request succeeded.

    Response contains plain text.
    """

    def __init__(self, message):
        super(HttpResponseOK, self).__init__(
            message,
            content_type=TEXT_MIME_TYPE,
            status=200)


class HttpResponseOKJson(HttpResponse):
    def __init__(self, attributes_dict):
        super(HttpResponseOKJson, self).__init__(
            json.dumps(attributes_dict),
            content_type=JSON_MIME_TYPE,
            status=200)

class HttpResponseOKHtml(HttpResponse):
    def __init__(self, body):
        super(HttpResponseOKHtml, self).__init__(
            body,
            content_type=HTML_MIME_TYPE,
            status=200)

class HttpResponseOKJs(HttpResponse):
    def __init__(self, body):
        super(HttpResponseOKJs, self).__init__(
            body,
            content_type=JS_MIME_TYPE,
            status=200)

class HttpResponseNoContent(HttpResponse):
    """Request succeeded, response body is empty."""

    def __init__(self):
        super(HttpResponseNoContent, self).__init__(status=204)
        self.__delitem__('Content-Type')

class HttpResponseCreated(HttpResponse):
    """Request succeeded, a resource was created.

    Contains json representation of the created resource.
    """

    def __init__(self, attributes_dict):
        """
        Args:
            attributes_dict: A dictionary containing all attributes of
                the created resource. The attributes are serialized to
                json and returned in the response body
        """

        super(HttpResponseCreated, self).__init__(
            json.dumps(attributes_dict),
            content_type=JSON_MIME_TYPE,
            status=201)

class HttpResponseNotAuthenticated(HttpResponse):
    """User is not authenticated.

    Request can be retried after successul authentication.
    """

    def __init__(self, html_response=None):
        """Sets WWW-Authenticate header required by the HTTP standard."""
        if html_response is None:
            body, content_type = 'Authentication required.', TEXT_MIME_TYPE
        else:
            body, content_type = html_response, HTML_MIME_TYPE
        super(HttpResponseNotAuthenticated, self).__init__(
            body, content_type=content_type, status=401)
        self['WWW-Authenticate'] = 'VerifiedEmail'

class HttpResponseNotAuthorized(HttpResponse):
    """User is authenticated but is not authorized to access a resource."""

    def __init__(self, html_response=None):
        if html_response is None:
            body, content_type = 'User not authorized.', TEXT_MIME_TYPE
        else:
            body, content_type = html_response, HTML_MIME_TYPE
        super(HttpResponseNotAuthorized, self).__init__(
            body, content_type=content_type, status=403)

class HttpResponseBadRequest(HttpResponse):
    """Request invalid.

    The most generic error status, returned when none of the more
    specific statuses is appropriate.
    """

    def __init__(self, message):
        logger.debug('Bad request %s' % (message))
        super(HttpResponseBadRequest, self).__init__(
            message, content_type=TEXT_MIME_TYPE, status=400)

class HttpResponseLimitExceeded(HttpResponse):
    """Too many resource are already created, a new one can not be added."""

    def __init__(self, message):
        logger.debug('Limit exceeded %s' % (message))
        super(HttpResponseLimitExceeded, self).__init__(
            message, content_type=TEXT_MIME_TYPE, status=400)

class HttpResponseNotFound(HttpResponse):

    def __init__(self, message):
        logger.debug('Not found %s' % (message))
        super(HttpResponseNotFound, self).__init__(
            message, content_type=TEXT_MIME_TYPE, status=404)

class HttpResponseServiceUnavailable(HttpResponse):

    def __init__(self, message):
        logger.warning('Service unavailable %s' % (message))
        super(HttpResponseServiceUnavailable, self).__init__(
            message, content_type=TEXT_MIME_TYPE, status=503)

class HttpResponseInternalError(HttpResponse):

    def __init__(self, message):
        logger.warning('Internal error %s' % (message))
        super(HttpResponseInternalError, self).__init__(
            message, content_type=TEXT_MIME_TYPE, status=500)

def disallow_cross_site_request(decorated_method):
    """Drops a request if it has any indicators of a cross site request."""
    @wraps(decorated_method)
    def wrapper(self, request, *args, **kwargs):
        # Cross-Origin Resource Sharing allows cross origin Ajax GET
        # requests, each such request must have the 'Origin' header
        # different than the site url. Drop such requests.
        origin = request.META.get('HTTP_ORIGIN', None)
        if origin is not None and origin != request.site_url:
                return HttpResponseBadRequest(
                    'Cross origin requests not allowed.')

        # Validate CSRF token unless test environment disabled CSRF protection.
        if (not getattr(request, '_dont_enforce_csrf_checks', False)
            and not _csrf_token_valid(request)):
            return HttpResponseBadRequest(
                'CSRF token missing or incorrect.')
        return decorated_method(self, request, *args, **kwargs)
    return wrapper

def never_ever_cache(decorated_method):
    """Like Django @never_cache but sets more valid cache disabling headers.

    @never_cache only sets Cache-Control:max-age=0 which is not
    enough. For example, with max-axe=0 Firefox returns cached results
    of GET calls when it is restarted.
    """
    @wraps(decorated_method)
    def wrapper(*args, **kwargs):
        response = decorated_method(*args, **kwargs)
        patch_cache_control(
            response, no_cache=True, no_store=True, must_revalidate=True,
            max_age=0)
        return response
    return wrapper

class RestView(View):
    """A common base class for all REST style views.

    Disallows all cross origin requests. Disables caching of
    responses. For POST and PUT methods, deserializes method arguments
    from a json encoded request body. If a specific method is not
    implemented in a subclass, or if it does not accept arguments
    passed in the body, or if some arguments are missing, an
    appropriate error is returned to the client.
    """

    @disallow_cross_site_request
    @never_ever_cache
    def dispatch(self, request, *args, **kwargs):
        """Dispatches a method to a subclass.

        kwargs contains arguments that are passed as a query string,
        for PUT and POST arguments passed in a json request body are
        added to kwargs, conflicting names result in an error.
        """
        method = request.method.lower()
        # Parse body as json object if it is not empty (empty body
        # contains '--BoUnDaRyStRiNg--')
        if (method == 'post' or method == 'put') \
                and len(request.body) != 0 and request.body[0] != '-':
            try:
                if not _utf8_encoded_json(request):
                    return HttpResponseBadRequest(
                        "Invalid Content-Type (only '%s' is acceptable)."
                        % (JSON_MIME_TYPE))

                json_args = json.loads(request.body)
                for k in json_args:
                    if k in kwargs:
                        return HttpResponseBadRequest(
                            'Invalid argument passed in the request body.')
                    else:
                        kwargs[k] = json_args[k]
                kwargs.update()
            except ValueError as err:
                logger.debug(
                    'Failed to parse the request body a as json object: %s'
                    % (err))
                return HttpResponseBadRequest(
                    'Failed to parse the request body as a json object.')
        try:
            return super(RestView, self).dispatch(request, *args, **kwargs)
        except TypeError as err:
            trace = "".join(traceback.format_exc())
            logger.debug('Invalid arguments, handler not found: %s\n%s'
                         % (err, trace))
            return HttpResponseBadRequest('Invalid request arguments')

def _csrf_token_valid(request):
    """Checks if a valid CSRF token is set in the request header.

    Django CSRF protection middleware is not used directly because it
    allows cross origin GET requests and does strict referer checking
    for HTTPS requests.

    GET request are believed to be safe because they do not modify
    state, but they do require special care to make sure the result is
    not leaked to the calling site. Under some circumstances resulting
    json, when interpreted as script or css, can possibly be
    leaked. The simplest protection is to disallow cross origin GETs.

    Strict referer checking for HTTPS requests is a protection method
    suggested in a study 'Robust Defenses for Cross-Site Request
    Forgery'. According to the study, only 0.2% of users block the
    referer header for HTTPS traffic. Many think the number is low
    enough not to support these users. The methodology used in the
    study had a considerable flaw, and the actual number of users
    blocing the header may be much higher.

    Because all protected methods are called with Ajax, for most
    clients a check that ensures a custom header is set is sufficient
    CSRF protection. No token is needed, because browsers disallow
    setting custom headers for cross origin requests. Unfortunately,
    legacy versions of some plugins did allow such headers. To protect
    users of these plugins a token needs to be used. The problem that
    is left is a protection of a user that is using a legacy plugin in
    a presence of an active network attacker. Such attacker can inject
    his token over HTTP, and exploit the plugin to send the token over
    HTTPS. The impact is mitigated if Strict Transport Security header
    is set (as recommended) for all wwwhisper protected sites (not
    perfect solution, because the header is supported only by the
    newest browsers).
    """
    # TODO: rename this header to WWWHISPER_CRSFTOKEN.
    header_token = request.META.get('HTTP_X_CSRFTOKEN', '')
    cookie_token = request.COOKIES.get(settings.CSRF_COOKIE_NAME, '')
    if (len(header_token) != csrf.CSRF_KEY_LENGTH or
        not constant_time_compare(header_token, cookie_token)):
        return False
    return True

def _utf8_encoded_json(request):
    """Checks if content of the request is defined to be utf-8 encoded json.

    'Content-type' header should be set to 'application/json;
    charset=utf-8'.  The function allows whitespaces around the two
    segments an is case-insensitive.
    """
    content_type = request.META.get('CONTENT_TYPE', '')
    parts = content_type.split(';')
    if (len(parts) != 2 or
        parts[0].strip().lower() != 'application/json' or
        parts[1].strip().lower() != 'charset=utf-8'):
        return False
    return True

########NEW FILE########
__FILENAME__ = middleware
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from wwwhisper_auth import http
from wwwhisper_auth.models import SINGLE_SITE_ID
from wwwhisper_auth import url_utils

import wwwhisper_auth.site_cache
import logging

logger = logging.getLogger(__name__)

SECURE_PROXY_SSL_HEADER = getattr(settings, 'SECURE_PROXY_SSL_HEADER')[0]

class SetSiteMiddleware(object):
    """Associates a request with the only site that is in a db.

    The middleware is used for setups in which a single wwwhisper
    instance serves a single site (all standalone setups). In
    wwwhisper as a service setup, a single wwwhisper instance serves
    multiple sites.
    """

    def __init__(self):
        self.sites = wwwhisper_auth.site_cache.CachingSitesCollection()

    def process_request(self, request):
        request.site = self.sites.find_item(SINGLE_SITE_ID)

class SiteUrlMiddleware(object):
    """Validates and sets site_url for the request.

    A Site-Url header must carry one of site's aliases otherwise a
    request is rejected. If Site-Url contains http://host_foo address
    which is not allowed but https://host_foo is allowed, redirect is
    returned.

    Sets X-Forwarded-Host to match Site-Url. X-Forwarded-Host is used
    by Django to generate redirects.
    """

    def _alias_defined(self, site, url):
        return site.aliases.find_item_by_url(url) is not None

    def _get_full_path(self, request):
        full_path = request.get_full_path()
        auth_request_prefix = reverse('auth-request') + '?path='
        if full_path.startswith(auth_request_prefix):
            full_path = full_path[len(auth_request_prefix):]
        return full_path

    def _needs_https_redirect(self, site, scheme, host):
        return scheme == 'http' and self._alias_defined(site, 'https://' + host)

    def _site_url_invalid(self, request, scheme, host):
        if self._needs_https_redirect(request.site, scheme, host):
            logger.debug('Request over http, redirecting to https')
            return redirect('https://' + host + self._get_full_path(request))
        msg = 'Invalid request URL, you can use wwwhisper admin to allow ' \
            'requests from this address.'
        logger.warning(msg)
        return http.HttpResponseBadRequest(msg)

    def process_request(self, request):
        url = request.META.get('HTTP_SITE_URL', None)
        if url is None:
            return http.HttpResponseBadRequest('Missing Site-Url header')
        url = url_utils.remove_default_port(url)
        parts = url.split('://', 1)
        if len(parts) != 2:
            return http.HttpResponseBadRequest('Site-Url has incorrect format')
        scheme, host = parts
        if not self._alias_defined(request.site, url):
            return self._site_url_invalid(request, scheme, host)
        request.site_url = url
        request.META[SECURE_PROXY_SSL_HEADER] = scheme
        request.META['HTTP_X_FORWARDED_HOST'] = host
        # TODO: use is_secure() instead
        request.https = (scheme == 'https')
        return None


class ProtectCookiesMiddleware(object):
    """Sets 'secure' flag for all cookies if request is over https.

    The flag prevents cookies from being sent with HTTP requests.
    """

    def process_response(self, request, response):
        # response.cookies is SimpleCookie (Python 'Cookie' module).
        for cookie in response.cookies.itervalues():
            if request.https:
                cookie['secure'] = True
        return response


class SecuringHeadersMiddleware(object):
    """Sets headers that impede clickjacking + content sniffing related attacks.
    """

    def process_response(self, request, response):
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

########NEW FILE########
__FILENAME__ = models
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Data model for the site access control rules.

Each site has users, locations (paths) and permissions - rules that
define which user can access which locations. Sites are
isolated. Users and locations are associated with a single site and
are used only for this site. Site has also aliases: urls that can be
used to access the site, only requests from these urls are allowed.

Provides methods that map to REST operations that can be performed on
users, locations and permissions resources. Allows to retrieve
externally visible attributes of these resources, the attributes are
returned as a resource representation by REST methods.

Resources are identified by an externally visible UUIDs. Standard
primary key ids are not used for external identification purposes,
because those ids can be reused after object is deleted.

Makes sure entered emails and paths are valid.
"""

from django.contrib.auth.models import AbstractBaseUser
from django.db import connection
from django.db import models
from django.db import transaction
from django.forms import ValidationError
from functools import wraps
from wwwhisper_auth import  url_utils
from wwwhisper_auth import  email_re

import logging
import random
import re
import threading
import uuid as uuidgen

logger = logging.getLogger(__name__)

class LimitExceeded(Exception):
    pass

class ValidatedModel(models.Model):
    """Base class for all model classes.

    Makes sure all constraints are preserved before changed data is
    saved.
    """

    class Meta:
        """Disables creation of a DB table for ValidatedModel."""
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(ValidatedModel, self).save(*args, **kwargs)

# Id used when wwwhisper servers just a single site.
SINGLE_SITE_ID = 'theone'

class Site(ValidatedModel):
    """A site to which access is protected.

    Site has locations, users and aliases.

    Attributes:
      site_id: Can be a domain or any other string.

      mod_id: Changed after any modification of site-related data (not
         only Site itself but also site's locations, permissions or
         users). Allows to determine when Django processes need to
         update cached data.
    """
    site_id = models.TextField(primary_key=True, db_index=True, editable=False)
    mod_id = models.IntegerField(default=0)

    # Default values for texts on a login page (used when custom texts
    # are set to empty values).
    _default_skin = {
        'title': 'wwwhisper: Web Access Control',
        'header': 'Protected site',
        'message': 'Access to this site is restricted. ' + \
            'Please sign in with your email:',
    }

    title = models.CharField(max_length=80, blank=True)
    header = models.CharField(max_length=100, blank=True)
    message = models.CharField(max_length=500, blank=True)
    branding = models.BooleanField(default=True)

    aliases_limit = None
    users_limit = None
    locations_limit = None

    def __init__(self, *args, **kwargs):
        super(Site, self).__init__(*args, **kwargs)
        # Synchronizes mod id that can be read by a cache updating
        # thread.
        self.mod_id_lock = threading.Lock()

    def heavy_init(self):
        """Creates collections of all site-related data.

        This is a resource intensive operation that retrieves all site
        related data from the database. It is only performed if the site
        was modified since it was last retrieved.
        """
        self.locations = LocationsCollection(self)
        self.users = UsersCollection(self)
        self.aliases = AliasesCollection(self)

    def site_modified(self):
        """Increases the site modification id.

        This causes the site to be refreshed in web processes caches.
        """
        cursor = connection.cursor()
        cursor.execute(
            'UPDATE wwwhisper_auth_site '
            'SET mod_id = mod_id + 1 WHERE site_id = %s', [self.site_id])
        cursor.close()
        mod_id = self.mod_id_from_db()
        with self.mod_id_lock:
            self.mod_id = mod_id

    def skin(self):
        """Dictionary with settings that configure the site's login page."""
        # Dict comprehensions not used to support python 2.6.
        result = dict([(attr, getattr(self, attr) or self._default_skin[attr])
                       for attr in self._default_skin.iterkeys()])
        result['branding'] = self.branding
        return result

    def update_skin(self, title, header, message, branding):
        for attr in self._default_skin.iterkeys():
            arg = locals()[attr].strip()
            if arg == self._default_skin[attr]:
                arg = ''
            setattr(self, attr, arg)
        self.branding = branding
        self.save()
        self.site_modified()

    def get_mod_id_ts(self):
        """This method can be safely invoked by a non main thread"""
        with self.mod_id_lock:
            return self.mod_id

    def mod_id_from_db(self):
        """Retrieves from the DB a current modification identifier for the site.

        Returns None if the site no longer exists in the DB.
        """
        cursor = connection.cursor()
        cursor.execute(
            'SELECT mod_id FROM wwwhisper_auth_site WHERE site_id = %s',
            [self.site_id])
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return row[0]

def modify_site(decorated_method):
    """Must decorate all methods that change data associated with the site.

    Makes sure site is marked as modified and other Django processes
    will retrieve new data from the DB instead of using cached data.
    """

    @wraps(decorated_method)
    def wrapper(self, *args, **kwargs):
        result = decorated_method(self, *args, **kwargs)
        # If no exception.
        self.site.site_modified()
        return result
    return wrapper


class SitesCollection(object):
    def create_item(self, site_id, **kwargs):
        """Creates a new Site object.

        Args:
           site_id: A domain or other id of the created site.
        Raises:
           ValidationError if a site with a given id already exists.
        """
        site =  Site.objects.create(site_id=site_id, **kwargs)
        site.heavy_init()
        return site

    def find_item(self, site_id):
        site = _find(Site, site_id=site_id)
        if site is not None:
            site.heavy_init()
        return site

    def delete_item(self, site_id):
        site = self.find_item(site_id)
        if site is None:
            return False
        # Users, Locations and Permissions have foreign key to the Site
        # and are deleted automatically.
        site.delete()
        return True

class User(AbstractBaseUser):
    # Site to which the user belongs.
    site = models.ForeignKey(Site, related_name='+')

    # Externally visible UUID of the user. Allows to identify a REST
    # resource representing the user.
    uuid = models.CharField(max_length=36, db_index=True,
                            editable=False, unique=True)
    email = models.EmailField(db_index=True)

    USERNAME_FIELD = 'uuid'
    REQUIRED_FIELDS = ['email', 'site']

    def attributes_dict(self, site_url):
        """Returns externally visible attributes of the user resource."""
        return _add_common_attributes(self, site_url, {'email': self.email})

    @models.permalink
    def get_absolute_url(self):
        return ('wwwhisper_user', (), {'uuid' : self.uuid})

class Location(ValidatedModel):
    """A location for which access control rules are defined.

    Location is uniquely identified by its canonical path. All access
    control rules defined for a location apply also to sub-paths,
    unless a more specific location exists. In such case the more
    specific location takes precedence over the more generic one.

    For example, if a location with a path /pub is defined and a user
    foo@example.com is granted access to this location, the user can
    access /pub and all sub path of /pub. But if a location with a
    path /pub/beer is added, and the user foo@example.com is not
    granted access to this location, the user won't be able to access
    /pub/beer and all its sub-paths.

    Attributes:
      site: Site to which the location belongs.
      path: Canonical path of the location.
      uuid: Externally visible UUID of the location, allows to identify a REST
          resource representing the location.

      open_access: can be:
        disabled ('n') - only explicitly allowed users can access a location;
        enabled ('y') - everyone can access a location, no login is required;
        enabled with authentication ('a') - everyone can access a location
          but login is required.
    """
    OPEN_ACCESS_CHOICES = (
        ('n', 'no open access'),
        ('y', 'open access'),
        ('a', 'open access, login required'),
        )
    site = models.ForeignKey(Site, related_name='+')
    path = models.TextField(db_index=True)
    uuid = models.CharField(max_length=36, db_index=True,
                            editable=False, unique=True)
    open_access = models.CharField(max_length=2, choices=OPEN_ACCESS_CHOICES,
                                   default='n')

    def __init__(self, *args, **kwargs):
        super(Location, self).__init__(*args, **kwargs)

    def permissions(self):
        # Does not run a query to get permissions if not needed.
        return self.site.locations.get_permissions(self.id)

    def __unicode__(self):
        return "%s" % (self.path)

    @models.permalink
    def get_absolute_url(self):
        """Constructs URL of the location resource."""
        return ('wwwhisper_location', (), {'uuid' : self.uuid})

    @modify_site
    def grant_open_access(self, require_login):
        """Allows open access to the location."""
        if require_login:
            self.open_access = 'a'
        else:
            self.open_access = 'y'
        self.save()

    def open_access_granted(self):
        return self.open_access in ('y', 'a')

    def open_access_requires_login(self):
        return self.open_access == 'a'

    @modify_site
    def revoke_open_access(self):
        """Disables open access to the location."""
        self.open_access = 'n'
        self.save()

    def can_access(self, user):
        """Determines if a user can access the location.

        Returns:
            True if the user is granted permission to access the
            location or it the location is open.
        """
        # Sanity check (this should normally be ensured by the caller).
        if user.site_id != self.site_id:
            return False
        return (self.open_access_granted()
                or self.permissions().get(user.id) != None)

    @modify_site
    def grant_access(self, user_uuid):
        """Grants access to the location to a given user.

        Args:
            user_uuid: string UUID of a user.

        Returns:
            (new Permission object, True) if access to the location was
                successfully granted.
            (existing Permission object, False) if user already had
                granted access to the location.

        Raises:
            LookupError: A site to which location belongs has no user
                with a given UUID.
        """
        user = self.site.users.find_item(uuid=user_uuid)
        if user is None:
            raise LookupError('User not found')
        permission = self.permissions().get(user.id)
        created = False
        if permission is None:
            created = True
            permission = Permission.objects.create(
                http_location_id=self.id, user_id=user.id, site_id=self.site_id)
        return (permission, created)

    @modify_site
    def revoke_access(self, user_uuid):
        """Revokes access to the location from a given user.

        Args:
            user_uuid: string UUID of a user.

        Raises:
            LookupError: Site has no user with a given UUID or the
                user can not access the location.
        """
        permission = self.get_permission(user_uuid)
        permission.delete()

    def get_permission(self, user_uuid):
        """Gets Permission object for a given user.

        Args:
            user_uuid: string UUID of a user.

        Raises:
            LookupError: No user with a given UUID or the user can not
                access the location.
        """
        user = self.site.users.find_item(uuid=user_uuid)
        if user is None:
            raise LookupError('User not found.')
        permission = self.permissions().get(user.id)
        if permission is None:
            raise LookupError('User can not access location.')
        return permission

    def allowed_users(self):
        """"Returns a list of users that can access the location."""
        # The code could access permission.user like this:
        # [perm.user for perm in self.permissions().itervalues()]
        # but this involves a single DB query per allowed user, going
        # through cached site.users involves no queries.
        return [self.site.users.find_item_by_pk(user_id)
                for user_id in self.permissions().iterkeys()]

    def attributes_dict(self, site_url):
        """Returns externally visible attributes of the location resource."""
        result = {
            'path': self.path,
            'allowedUsers': [
                user.attributes_dict(site_url) for user in self.allowed_users()
                ],
            }
        if self.open_access_granted():
            result['openAccess'] = {
                'requireLogin' : self.open_access_requires_login()
                }
        return _add_common_attributes(self, site_url, result)

class Permission(ValidatedModel):
    """Connects a location with a user that can access the location.

    Attributes:
        http_location: The location to which the Permission object gives access.
        user: The user that is given access to the location.
    """

    http_location = models.ForeignKey(Location, related_name='+')
    site = models.ForeignKey(Site, related_name='+')
    user = models.ForeignKey(User, related_name='+')

    def __unicode__(self):
        return "%s, %s" % (self.http_location, self.user.email)

    @models.permalink
    def get_absolute_url(self):
        """Constructs URL of the permission resource."""
        return ('wwwhisper_allowed_user', (),
                {'location_uuid' : self.http_location.uuid,
                 'user_uuid': self.user.uuid})

    def attributes_dict(self, site_url):
        """Returns externally visible attributes of the permission resource."""
        return _add_common_attributes(
            self, site_url, {'user': self.user.attributes_dict(site_url)})

class Alias(ValidatedModel):
    """One of urls that can be used to access the site.

    Attributes:
      site: Site to which the alias belongs.
      url: Has form http(s)://domain[:port], default ports (80 for http,
         443 for https) are always stripped.
      uuid: Externally visible UUID of the alias.
    """

    site = models.ForeignKey(Site, related_name='+')
    url = models.TextField(db_index=True)
    uuid = models.CharField(max_length=36, db_index=True,
                            editable=False, unique=True)
    force_ssl = models.BooleanField(default=False)


    @models.permalink
    def get_absolute_url(self):
        return ('wwwhisper_alias', (), {'uuid' : self.uuid})

    def attributes_dict(self, site_url):
        return _add_common_attributes(self, site_url, {'url': self.url})


class Collection(object):
    """A common base class for managing a collection of resources.

    All resources in a collection belong to a common site and only
    this site can manipulate the resouces.

    Resources in the collection are of the same type and need to be
    identified by an UUID.

    Attributes (Need to be defined in subclasses):
        item_name: Name of a resource stored in the collection.
        model_class: Class that manages storage of resources.
    """

    def __init__(self, site):
        self.site = site
        self.update_cache()

    def update_cache(self):
        self._cached_items_dict = {}
        self._cached_items_list = []
        for item in self.model_class.objects.filter(site_id=self.site.site_id):
            self._cached_items_dict[item.id] = item
            self._cached_items_list.append(item)
            # Use already retrieved site, do not retrieve it again.
            item.site = self.site
        self.cache_mod_id = self.site.mod_id

    def is_cache_obsolete(self):
        return self.site.mod_id != self.cache_mod_id

    def all(self):
        if self.is_cache_obsolete():
            self.update_cache()
        return self._cached_items_list

    def all_dict(self):
        if self.is_cache_obsolete():
            self.update_cache()
        return self._cached_items_dict

    def count(self):
        return len(self.all())

    def get_unique(self, filter_fun):
        """Finds a unique item that satisfies a given filter.

        Returns:
           The item or None if not found.
        """
        result = filter(filter_fun, self.all())
        count = len(result)
        assert count <= 1
        if count == 0:
            return None
        return result[0]

    def find_item(self, uuid):
        return self.get_unique(lambda item: item.uuid == uuid)

    def find_item_by_pk(self, pk):
        return self.all_dict().get(pk, None)

    @modify_site
    def delete_item(self, uuid):
        """Deletes an item with a given UUID.

        Returns:
           True if the item existed and was deleted, False if not found.
        """
        item = self.find_item(uuid)
        if item is None:
            return False
        item.delete()
        return True

    def _do_create_item(self, *args, **kwargs):
        """Only to be called by subclasses."""
        item = self.model_class.objects.create(
            site=self.site, uuid=str(uuidgen.uuid4()), **kwargs)
        item.site = self.site
        return item

class UsersCollection(Collection):
    """Collection of users resources."""

    item_name = 'user'
    model_class = User

    @modify_site
    def create_item(self, email):
        """Creates a new User object for the site.

        There may be two different users with the same email but for
        different sites.

        Raises:
            ValidationError if the email is invalid or if a site
            already has a user with such email.
            LimitExceeded if the site defines a maximum number of
            users and adding a new one would exceed this number.
        """
        users_limit = self.site.users_limit
        if (users_limit is not None and self.count() >= users_limit):
            raise LimitExceeded('Users limit exceeded')

        encoded_email = _encode_email(email)
        if encoded_email is None:
            raise ValidationError('Invalid email format.')
        if self.find_item_by_email(encoded_email) is not None:
            raise ValidationError('User already exists.')
        return self._do_create_item(email=encoded_email)

    def find_item_by_email(self, email):
        encoded_email = _encode_email(email)
        if encoded_email is None:
            return None
        return self.get_unique(lambda user: user.email == encoded_email)

class LocationsCollection(Collection):
    """Collection of locations resources."""

    # Can be safely risen to whatever value is needed.
    PATH_LEN_LIMIT = 300

    # TODO: These should rather also be all caps.
    item_name = 'location'
    model_class = Location

    def update_cache(self):
        super(LocationsCollection, self).update_cache()
        # Retrieves permissions for all locations of the site with a
        # single query.
        self._cached_permissions = {}
        for p in Permission.objects.filter(site=self.site):
            self._cached_permissions.setdefault(
                p.http_location_id, {})[p.user_id] = p

    def get_permissions(self, location_id):
        """Returns permissions for a given location of the site."""
        if self.is_cache_obsolete():
            self.update_cache()
        return self._cached_permissions.get(location_id, {})

    @modify_site
    def create_item(self, path):
        """Creates a new Location object for the site.

        The location path should be canonical and should not contain
        parts that are not used for access control (query, fragment,
        parameters). Location should not contain non-ascii characters.

        Raises:
            ValidationError if the path is invalid or if a site
            already has a location with such path.
            LimitExceeded if the site defines a maximum number of
            locations and adding a new one would exceed this number.
        """

        locations_limit = self.site.locations_limit
        if (locations_limit is not None and self.count() >= locations_limit):
            raise LimitExceeded('Locations limit exceeded')

        if not url_utils.is_canonical(path):
            raise ValidationError(
                'Path should be absolute and normalized (starting with / '\
                    'without /../ or /./ or //).')
        if len(path) > self.PATH_LEN_LIMIT:
            raise ValidationError('Path too long')
        if url_utils.contains_fragment(path):
            raise ValidationError(
                "Path should not contain fragment ('#' part).")
        if url_utils.contains_query(path):
            raise ValidationError(
                "Path should not contain query ('?' part).")
        if url_utils.contains_params(path):
            raise ValidationError(
                "Path should not contain parameters (';' part).")
        try:
            path.encode('ascii')
        except UnicodeError:
            raise ValidationError(
                'Path should contain only ascii characters.')

        if self.get_unique(lambda item: item.path == path) is not None:
            raise ValidationError('Location already exists.')

        return self._do_create_item(path=path)


    def find_location(self, canonical_path):
        """Finds a location that defines access to a given path on the site.

        Args:
            canonical_path: The path for which matching location is searched.

        Returns:
            The most specific location with path matching a given path or None
            if no matching location exists.
        """
        canonical_path_len = len(canonical_path)
        longest_matched_location = None
        longest_matched_location_len = -1

        for location in self.all():
            probed_path = location.path
            probed_path_len = len(probed_path)
            trailing_slash_index = None
            if probed_path[probed_path_len - 1] == '/':
                trailing_slash_index = probed_path_len - 1
            else:
                trailing_slash_index = probed_path_len

            if (canonical_path.startswith(probed_path) and
                probed_path_len > longest_matched_location_len and
                (probed_path_len == canonical_path_len or
                 canonical_path[trailing_slash_index] == '/')) :
                longest_matched_location_len = probed_path_len
                longest_matched_location = location
        return longest_matched_location

    def has_open_location_with_login(self):
        for location in self.all():
            if (location.open_access_granted() and
                location.open_access_requires_login()):
                return True
        return False
    def has_open_location(self):
        for location in self.all():
            if location.open_access_granted():
                return True
        return False

class AliasesCollection(Collection):
    item_name = 'alias'
    model_class = Alias
    # RFC 1035
    ALIAS_LEN_LIMIT = 8 + 253 + 6

    @modify_site
    def create_item(self, url):
        aliases_limit = self.site.aliases_limit
        if (aliases_limit is not None and self.count() >= aliases_limit):
            raise LimitExceeded('Aliases limit exceeded')
        if len(url) > self.ALIAS_LEN_LIMIT:
            raise ValidationError('Url too long')

        url = url.strip().lower()
        (valid, error) = url_utils.validate_site_url(url)
        if not valid:
            raise ValidationError('Invalid url: ' + error)
        if self.find_item_by_url(url):
            raise ValidationError('Alias with this url already exists')
        return self._do_create_item(url=url_utils.remove_default_port(url))

    def find_item_by_url(self, url):
        return self.get_unique(lambda item: item.url == url)

def _uuid2urn(uuid):
    return 'urn:uuid:' + uuid

def _add_common_attributes(item, site_url, attributes_dict):
    """Inserts common attributes of an item to a given dict.

    Attributes that are common for different resource types are a
    'self' link and an 'id' field.
    """
    attributes_dict['self'] = site_url + item.get_absolute_url()
    if hasattr(item, 'uuid'):
        attributes_dict['id'] = _uuid2urn(item.uuid)
    return attributes_dict

def _find(model_class, **kwargs):
    """Finds a single item satisfying a given expression.

    Args:
        model_class: Model that manages stored items.
        **kwargs: Filtering expression, at most one element can satisfy it.
    Returns:
        An item that satisfies expression or None.
    """
    items = [item for item in model_class.objects.filter(**kwargs)]
    count = len(items)
    assert count <= 1
    if count == 0:
        return None
    return items[0]

def _encode_email(email):
    """Encodes and validates email address.

    Email is converted to a lower case not to require emails to be added
    to the access control list with the same capitalization that the
    user signs-in with.
    """
    encoded_email = email.lower()
    if not _is_email_valid(encoded_email):
        return None
    return encoded_email

def _is_email_valid(email):
    return re.match(email_re.EMAIL_VALIDATION_RE, email)

########NEW FILE########
__FILENAME__ = site_cache
# wwwhisper - web access control.
# Copyright (C) 2013 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Cache for sites with all associated data.

If the site was not modified since it was stored in the cache all data
(locations, users and permissions) are taken from the cache.

Majority of wwwhisper request are performance critical
auth-requests. Because these requests are read only, caching is very
efficient (cached data rarely needs to be updated).
"""

import logging
from wwwhisper_auth.models import SitesCollection

logger = logging.getLogger(__name__)

class CacheUpdater(object):
    """Checks if the cached site needs to be updated.

    This is a simple, database agnostic implementation that runs a
    single query against the site table to check if the site
    modification token has changed.
    """

    def is_obsolete(self, site):
        mod_id = site.mod_id_from_db()
        return mod_id is None or mod_id != site.mod_id

class SiteCache(object):
    def __init__(self, updater):
        self._updater = updater
        self._items = {}

    def insert(self, site):
        self._items[site.site_id] = site

    def get(self, site_id):
        site = self._items.get(site_id, None)
        if site is None:
            return None
        if self._updater.is_obsolete(site):
            self.delete(site_id)
            return None
        return site

    def delete(self, site_id):
        self._items.pop(site_id, None)

class CachingSitesCollection(SitesCollection):
    """Like models.SitesCollection but returns cached results when possible."""

    def __init__(self, site_cache=None):
        if site_cache is None:
            site_cache = SiteCache(CacheUpdater())
        self.site_cache = site_cache

    def create_item(self, site_id, **kwargs):
        site = super(CachingSitesCollection, self).create_item(
            site_id=site_id, **kwargs)
        self.site_cache.insert(site)
        return site

    def find_item(self, site_id):
        site = self.site_cache.get(site_id)
        if site is not None:
            return site
        site = super(CachingSitesCollection, self).find_item(site_id=site_id)
        if site is not None:
            self.site_cache.insert(site)
        return site

    def delete_item(self, site_id):
        rv = super(CachingSitesCollection, self).delete_item(site_id=site_id)
        self.site_cache.delete(site_id)
        return rv

# TODO: using this leads to problems in unit tests (a single test
# creates sites that are visible to other tests).
sites = CachingSitesCollection()

########NEW FILE########
__FILENAME__ = tests_http
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import Client
from wwwhisper_auth.http import accepts_html
from wwwhisper_auth.http import RestView
from wwwhisper_auth.tests.utils import HttpTestCase
from wwwhisper_auth.tests.utils import TEST_SITE

class TestView(RestView):
    def get(self, request):
        return HttpResponse(status=267)

    def post(self, request, ping_message):
        return HttpResponse(ping_message, status=277)

class TestView2(RestView):
    def get(self, request, url_arg):
        return HttpResponse(url_arg, status=288)

    def post(self, request, url_arg):
        return HttpResponse(url_arg, status=298)

urlpatterns = patterns(
    '',
    url(r'^testview/$', TestView.as_view()),
    url(r'^testview2/(?P<url_arg>[a-z]+)/$', TestView2.as_view()))

class RestViewTest(HttpTestCase):
    urls = 'wwwhisper_auth.tests.tests_http'

    def test_method_dispatched(self):
        response = self.get('/testview/')
        self.assertEqual(267, response.status_code)

    def test_method_with_json_argument_in_body_dispatched(self):
        response = self.post('/testview/', {'ping_message' : 'hello world'})
        self.assertEqual(277, response.status_code)
        self.assertEqual('hello world', response.content)

    def test_method_with_missing_json_argument_in_body_dispatched(self):
        response = self.post('/testview/', {})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Invalid request arguments')

    def test_method_with_incorrect_json_argument_in_body(self):
        response = self.post('/testview/', {'pong_message' : 'hello world'})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Invalid request arguments')

    def test_method_with_incorrectly_formated_json_argument_in_body(self):
        response = self.client.post('/testview/',
                                    "{{ 'ping_message' : 'hello world' }",
                                    'application/json ;  charset=UTF-8',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                                    HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content, 'Failed to parse the '
                                 'request body as a json object.')

    def test_incorrect_method(self):
        response = self.delete('/testview/')
        self.assertEqual(405, response.status_code)
        # 'The response MUST include an Allow header containing a list
        # of valid methods for the requested resource.' (rfc2616)
        self.assertItemsEqual(['GET', 'POST', 'HEAD', 'OPTIONS'],
                              response['Allow'].split(', '))

    def test_method_with_argument_in_url_dispatched(self):
        response = self.get('/testview2/helloworld/')
        self.assertEqual(288, response.status_code)
        self.assertEqual('helloworld', response.content)


    def test_argument_in_body_cannot_overwrite_argument_in_url(self):
        response = self.post('/testview2/helloworld/',
                             {'url_arg': 'hello-world'})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(
            response.content, 'Invalid argument passed in the request body.')

    def test_content_type_validation(self):
        response = self.client.post(
            '/testview/', '{"ping_message" : "hello world"}', 'text/json',
            HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Invalid Content-Type')

        response = self.client.post(
            '/testview/', '{"ping_message" : "hello world"}',
            'application/json; charset=UTF-16',
            HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Invalid Content-Type')

        # Content-Type header should be case-insensitive.
        response = self.client.post(
            '/testview/', '{"ping_message" : "hello world"}',
            'application/JSON; charset=UTF-8',
            HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(277, response.status_code)

    def test_csrf_protection(self):
        self.client = Client(enforce_csrf_checks=True)

        # No CSRF tokens.
        response = self.client.get('/testview/', HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'CSRF token missing or incorrect')

        # Too short CSRF tokens.
        self.client.cookies[settings.CSRF_COOKIE_NAME] = 'a'
        response = self.client.get('/testview/', HTTP_X_CSRFTOKEN='a',
                                   HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'CSRF token missing or incorrect')

        # Not matching CSRF tokens.
        self.client.cookies[settings.CSRF_COOKIE_NAME] = \
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        response = self.client.get(
            '/testview/', HTTP_X_CSRFTOKEN='xxxxxxxxxxxxxxxOxxxxxxxxxxxxxxxx',
            HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'CSRF token missing or incorrect')

        # Matching CSRF tokens.
        self.client.cookies[settings.CSRF_COOKIE_NAME] = \
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        response = self.client.get(
            '/testview/', HTTP_X_CSRFTOKEN='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            HTTP_SITE_URL=TEST_SITE)
        self.assertEqual(267, response.status_code)

    def test_caching_disabled_for_rest_view_results(self):
        response = self.get('/testview/')
        self.assertTrue(response.has_header('Cache-Control'))
        control = response['Cache-Control']
        # index throws ValueError if not found.
        control.index('no-cache')
        control.index('no-store')
        control.index('must-revalidate')
        control.index('max-age=0')


class AcceptHeaderUtilsTest(TestCase):
    def test_accepts_html(self):
        self.assertTrue(accepts_html('text/html'))
        self.assertTrue(accepts_html('text/*'))
        self.assertTrue(accepts_html('*/*'))
        self.assertTrue(accepts_html('audio/*, text/plain, text/*'))
        self.assertTrue(accepts_html(
                'text/*;q=0.3, text/html;q=0.7, text/html;level=1, ' +
                'text/html;level=2;q=0.4, */*;q=0.5'))

        self.assertFalse(accepts_html('text/plain'))
        self.assertFalse(accepts_html('audio/*'))
        self.assertFalse(accepts_html('text/x-dvi; q=0.8, text/x-c'))
        self.assertFalse(accepts_html(None))

########NEW FILE########
__FILENAME__ = tests_middleware
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpRequest
from django.test import TestCase
from wwwhisper_auth import http
from wwwhisper_auth.middleware import SecuringHeadersMiddleware
from wwwhisper_auth.middleware import ProtectCookiesMiddleware
from wwwhisper_auth.middleware import SetSiteMiddleware
from wwwhisper_auth.middleware import SiteUrlMiddleware
from wwwhisper_auth.models import SitesCollection
from wwwhisper_auth.models import SINGLE_SITE_ID

class SetSiteMiddlewareTest(TestCase):
    def test_site_set_if_exists(self):
        site = SitesCollection().create_item(SINGLE_SITE_ID)
        middleware = SetSiteMiddleware()
        r = HttpRequest()
        self.assertIsNone(middleware.process_request(r))
        self.assertEqual(SINGLE_SITE_ID, r.site.site_id)

    def test_site_not_set_if_missing(self):
        middleware = SetSiteMiddleware()
        r = HttpRequest()
        self.assertIsNone(middleware.process_request(r))
        self.assertIsNone(r.site)

class SiteUrlMiddlewareTest(TestCase):
    def setUp(self):
        self.middleware = SiteUrlMiddleware()
        self.request = HttpRequest()
        self.sites = SitesCollection()
        self.request.site = self.sites.create_item(SINGLE_SITE_ID)
        self.site_url = 'https://foo.example.com'
        self.request.site.aliases.create_item(self.site_url)

    def test_allowed_site_url_https(self):
        self.request.META['HTTP_SITE_URL'] = self.site_url
        self.assertIsNone(self.middleware.process_request(self.request))
        self.assertEqual(self.site_url, self.request.site_url)
        self.assertEqual('foo.example.com', self.request.get_host())
        self.assertTrue(self.request.https)
        self.assertTrue(self.request.is_secure())

    def test_allowed_site_url_http(self):
        url = 'http://bar.example.com'
        self.request.site.aliases.create_item(url)
        self.request.META['HTTP_SITE_URL'] = url
        self.assertIsNone(self.middleware.process_request(self.request))
        self.assertEqual(url, self.request.site_url)
        self.assertEqual('bar.example.com', self.request.get_host())
        self.assertFalse(self.request.https)
        self.assertFalse(self.request.is_secure())

    def test_allowed_site_url_with_port(self):
        url = 'http://bar.example.com:123'
        self.request.site.aliases.create_item(url)
        self.request.META['HTTP_SITE_URL'] = url
        self.assertIsNone(self.middleware.process_request(self.request))
        self.assertEqual(url, self.request.site_url)
        self.assertEqual('bar.example.com:123', self.request.get_host())
        self.assertFalse(self.request.https)
        self.assertFalse(self.request.is_secure())

    def test_not_allowed_site_url(self):
        self.request.META['HTTP_SITE_URL'] = 'https://bar.example.com'
        response = self.middleware.process_request(self.request)
        self.assertIsNotNone(response)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Invalid request URL')

    def test_not_allowed_site_url2(self):
        self.request.META['HTTP_SITE_URL'] = 'https://foo.example.com:80'
        response = self.middleware.process_request(self.request)
        self.assertIsNotNone(response)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Invalid request URL')

    def test_missing_site_url(self):
        response = self.middleware.process_request(self.request)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Missing Site-Url header')

    def test_invalid_site_url(self):
        self.request.META['HTTP_SITE_URL'] = 'foo.example.org'
        response = self.middleware.process_request(self.request)
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Site-Url has incorrect format')

    def test_allowed_site_with_explicit_port(self):
        # Request with correct explicit port should be accepted, port
        # should be removed.
        self.request.META['HTTP_SITE_URL'] = self.site_url + ':443'
        self.assertIsNone(self.middleware.process_request(self.request))
        self.assertEqual(self.site_url, self.request.site_url)
        self.assertEqual('foo.example.com', self.request.get_host())
        self.assertTrue(self.request.https)
        self.assertTrue(self.request.is_secure())

    def test_not_allowed_http_site_redirects_to_https_if_exists(self):
        self.request.META['HTTP_SITE_URL'] = 'http://foo.example.com'
        self.request.path = '/bar?baz=true'
        response = self.middleware.process_request(self.request)
        self.assertIsNotNone(response)
        self.assertEqual(302, response.status_code)
        self.assertEqual('https://foo.example.com/bar?baz=true',
                         response['Location'])

    def test_https_redirects_for_auth_request(self):
        self.request.META['HTTP_SITE_URL'] = 'http://foo.example.com'
        self.request.path = '/auth/api/is-authorized/?path=/foo/bar/baz'
        response = self.middleware.process_request(self.request)
        self.assertIsNotNone(response)
        self.assertEqual(302, response.status_code)
        self.assertEqual('https://foo.example.com/foo/bar/baz',
                         response['Location'])

class ProtectCookiesMiddlewareTest(TestCase):

    def test_secure_flag_set_for_https_request(self):
        middleware = ProtectCookiesMiddleware()
        request = HttpRequest()
        request.https = True
        response = http.HttpResponseNoContent()
        response.set_cookie('session', value='foo', secure=None)

        self.assertFalse(response.cookies['session']['secure'])
        response = middleware.process_response(request, response)
        self.assertTrue(response.cookies['session']['secure'])

    def test_secure_flag_not_set_for_http_request(self):
        middleware = ProtectCookiesMiddleware()
        request = HttpRequest()
        request.https = False
        response = http.HttpResponseNoContent()
        response.set_cookie('session', value='foo', secure=None)

        self.assertFalse(response.cookies['session']['secure'])
        response = middleware.process_response(request, response)
        self.assertFalse(response.cookies['session']['secure'])


class SecuringHeadersMiddlewareTest(TestCase):

    def test_different_origin_framing_not_allowed(self):
        middleware = SecuringHeadersMiddleware()
        request = HttpRequest()
        response = http.HttpResponseNoContent()
        self.assertFalse('X-Frame-Options' in response)
        self.assertFalse('X-Content-Type-Options' in response)
        response = middleware.process_response(request, response)
        self.assertEqual('SAMEORIGIN', response['X-Frame-Options'])
        self.assertEqual('nosniff', response['X-Content-Type-Options'])

########NEW FILE########
__FILENAME__ = tests_models
# coding=utf-8

# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.forms import ValidationError
from django.test import TestCase
from contextlib import contextmanager
from functools import wraps
from wwwhisper_auth.models import LimitExceeded
from wwwhisper_auth.models import SitesCollection

FAKE_UUID = '41be0192-0fcc-4a9c-935d-69243b75533c'
TEST_SITE = 'https://example.com'
TEST_SITE2 = 'https://example.org'
TEST_USER_EMAIL = 'foo@bar.com'
TEST_LOCATION = '/pub/kika'

class ModelTestCase(TestCase):
    def setUp(self):
        self.sites = SitesCollection()
        self.site = self.sites.create_item(TEST_SITE)
        self.site2 = self.sites.create_item(TEST_SITE2)
        self.aliases = self.site.aliases
        self.locations = self.site.locations
        self.users = self.site.users

    @contextmanager
    def assert_site_modified(self, site):
        mod_id = site.mod_id
        yield
        self.assertNotEqual(mod_id, site.mod_id)
        self.assertEqual(site.mod_id, site.get_mod_id_ts())

    @contextmanager
    def assert_site_not_modified(self, site):
        mod_id = site.mod_id
        yield
        self.assertEqual(mod_id,  site.mod_id)

# Test testing infrastructure.
class SiteModifiedTest(ModelTestCase):
    def test_assert_site_modified(self):
        with self.assert_site_modified(self.site):
            self.site.site_modified()
        # Should not raise anything

    def test_assert_site_not_modified(self):
        with self.assert_site_not_modified(self.site):
            pass
        # Should not raise anything

    def test_assert_site_modified_raises(self):
        try:
            with self.assert_site_modified(self.site):
                pass
        except AssertionError as er:
            pass # Expected.
        else:
            self.fail('Assertion not raised')

    def test_assert_site_not_modified_raises(self):
        try:
            with self.assert_site_not_modified(self.site):
                self.site.site_modified()
        except AssertionError as er:
            pass # Expected.
        else:
            self.fail('Assertion not raised')

class SitesTest(ModelTestCase):
    def test_create_site(self):
        self.assertEqual(TEST_SITE, self.site.site_id)
        self.assertIsNotNone(self.site.locations.site)
        self.assertIsNotNone(self.site.users.site)

    def test_create_site_twice(self):
        self.assertRaisesRegexp(ValidationError,
                                'Site .* already exists.',
                                self.sites.create_item,
                                TEST_SITE)

    def test_find_site(self):
        site2 = self.sites.find_item(TEST_SITE)
        self.assertIsNotNone(site2)
        self.assertEqual(self.site, site2)

    def test_delete_site(self):
        self.assertTrue(self.sites.delete_item(TEST_SITE))
        self.assertIsNone(self.sites.find_item(TEST_SITE))

    def test_default_skin(self):
        skin = self.site.skin()
        self.assertEqual('wwwhisper: Web Access Control', skin['title'])
        self.assertEqual('Protected site', skin['header'])
        self.assertRegexpMatches(skin['message'], 'Access to this site is')
        self.assertTrue(skin['branding'])

    def test_update_skin(self):
        with self.assert_site_modified(self.site):
            self.site.update_skin(title='BarFoo', header='', message='hello',
                                  branding=False)
        with self.assert_site_not_modified(self.site):
            skin = self.site.skin()
        self.assertEqual('BarFoo', skin['title'])
        self.assertEqual('Protected site', skin['header'])
        self.assertEqual('hello', skin['message'])
        self.assertFalse(skin['branding'])

        # If default value is used, it should not be saved to a db,
        # but it should still be returned in the skin dict.
        self.site.update_skin(title='wwwhisper: Web Access Control ', header='',
                              message='', branding=False)
        self.assertEqual('', self.site.title)
        self.assertEqual('wwwhisper: Web Access Control',
                         self.site.skin()['title'])

class UsersCollectionTest(ModelTestCase):
    def test_create_user(self):
        with self.assert_site_modified(self.site):
            user = self.users.create_item(TEST_USER_EMAIL)
        self.assertEqual(TEST_USER_EMAIL, user.email)
        self.assertEqual(TEST_SITE, user.site_id)

    def test_find_user_by_uuid(self):
        user1 = self.users.create_item(TEST_USER_EMAIL)
        with self.assert_site_not_modified(self.site):
            user2 = self.users.find_item(user1.uuid)
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_find_user_by_pk(self):
        user1 = self.users.create_item(TEST_USER_EMAIL)
        with self.assert_site_not_modified(self.site):
            user2 = self.users.find_item_by_pk(user1.id)
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_find_user_different_site(self):
        user1 = self.users.create_item(TEST_USER_EMAIL)
        self.assertIsNone(self.site2.users.find_item(user1.uuid))

    def test_delete_site_deletes_user(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        self.assertEqual(1, user.__class__.objects.filter(id=user.id).count())
        self.assertTrue(self.sites.delete_item(self.site.site_id))
        self.assertEqual(0, user.__class__.objects.filter(id=user.id).count())

    def test_find_user_by_email(self):
        self.assertIsNone(self.users.find_item_by_email(TEST_USER_EMAIL))
        user1 = self.users.create_item(TEST_USER_EMAIL)
        with self.assert_site_not_modified(self.site):
            user2 = self.users.find_item_by_email(TEST_USER_EMAIL)
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_find_user_by_email_different_site(self):
        self.users.create_item(TEST_USER_EMAIL)
        self.assertIsNone(self.site2.users.find_item_by_email(TEST_USER_EMAIL))

    def test_find_user_by_email_is_case_insensitive(self):
        user1 = self.users.create_item('foo@bar.com')
        user2 = self.users.find_item_by_email('FOo@bar.com')
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_delete_user(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        with self.assert_site_modified(self.site):
            self.assertTrue(self.users.delete_item(user.uuid))
        self.assertIsNone(self.users.find_item(user.uuid))

    def test_create_user_twice(self):
        self.users.create_item(TEST_USER_EMAIL)
        self.assertRaisesRegexp(ValidationError,
                                'User already exists',
                                self.users.create_item,
                                TEST_USER_EMAIL)

        # Make sure user lookup is case insensitive.
        self.users.create_item('uSeR@bar.com')
        with self.assert_site_not_modified(self.site):
            self.assertRaisesRegexp(ValidationError,
                                    'User already exists',
                                    self.users.create_item,
                                    'UsEr@bar.com')

    def test_create_user_twice_for_different_sites(self):
        self.users.create_item(TEST_USER_EMAIL)
        with self.assert_site_not_modified(self.site):
            with self.assert_site_modified(self.site2):
                self.site2.users.create_item(TEST_USER_EMAIL)
        # Should not raise

    def test_delete_user_twice(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        self.assertTrue(self.users.delete_item(user.uuid))
        self.assertFalse(self.users.delete_item(user.uuid))

    def test_delete_user_different_site(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        self.assertFalse(self.site2.users.delete_item(user.uuid))

    def test_get_all_users(self):
        user1 = self.users.create_item('foo@example.com')
        user2 = self.users.create_item('bar@example.com')
        user3 = self.site2.users.create_item('baz@example.com')
        self.assertEqual(2, self.users.count())
        self.assertEqual(1, self.site2.users.count())
        with self.assert_site_not_modified(self.site):
            self.assertItemsEqual(
                ['foo@example.com', 'bar@example.com'],
                [u.email for u in self.users.all()])
        self.users.delete_item(user1.uuid)
        self.assertItemsEqual(
            ['bar@example.com'],
            [u.email for u in self.users.all()])
        self.assertEqual(1, self.users.count())

    def test_get_all_users_when_empty(self):
        self.assertEqual(0, self.users.count())
        self.assertListEqual([], list(self.users.all()))

    def test_email_validation(self):
        """Test strings taken from BrowserId tests."""
        self.assertIsNotNone(self.users.create_item('x@y.z'))
        self.assertIsNotNone(self.users.create_item('x@y.z.w'))
        self.assertIsNotNone(self.users.create_item('x.v@y.z.w'))
        self.assertIsNotNone(self.users.create_item('x_v@y.z.w'))
        # Valid tricky characters.
        self.assertIsNotNone(self.users.create_item(
                r'x#!v$we*df+.|{}@y132.wp.a-s.012'))

        with self.assert_site_not_modified(self.site):
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    'x')
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    'x@y')
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    '@y.z')
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    'z@y.z@y.z')
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    '')
            # Invalid tricky character.
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    r'a\b@b.c.d')
            # Too long.
            self.assertRaisesRegexp(ValidationError,
                                    'Invalid email format',
                                    self.users.create_item,
                                    'foo@bar.com.' + ('z' * 100) )

    def test_email_normalization(self):
        email = self.users.create_item('x@y.z').email
        self.assertEqual('x@y.z', email)

        email = self.users.create_item('aBc@y.z').email
        self.assertEqual('abc@y.z', email)

    def test_users_limit(self):
        limit = 10
        self.site.users_limit = limit
        for i in range(0, limit):
            self.users.create_item('foo%d@bar.com' % (i))
        self.assertRaisesRegexp(LimitExceeded,
                                'Users limit exceeded',
                                self.users.create_item,
                                'foo10@bar.com')

class LocationsCollectionTest(ModelTestCase):
    def test_create_location(self):
        with self.assert_site_modified(self.site):
            location = self.locations.create_item(TEST_LOCATION)
            self.assertEqual(TEST_LOCATION, location.path)
            self.assertEqual(TEST_SITE, location.site_id)

    def test_delete_site_deletes_location(self):
        location = self.locations.create_item(TEST_LOCATION)
        self.assertEqual(
            1, location.__class__.objects.filter(id=location.id).count())
        self.assertTrue(self.sites.delete_item(self.site.site_id))
        self.assertEqual(
            0, location.__class__.objects.filter(id=location.id).count())

    def test_find_location_by_uuid(self):
        location1 = self.locations.create_item(TEST_LOCATION)
        with self.assert_site_not_modified(self.site):
            location2 = self.locations.find_item(location1.uuid)
        self.assertIsNotNone(location2)
        self.assertEqual(location1.path, location2.path)
        self.assertEqual(location1.uuid, location2.uuid)

    def test_find_location_by_pk(self):
        location1 = self.locations.create_item(TEST_LOCATION)
        with self.assert_site_not_modified(self.site):
            location2 = self.locations.find_item_by_pk(location1.id)
        self.assertIsNotNone(location2)
        self.assertEqual(location1.path, location2.path)
        self.assertEqual(location1.uuid, location2.uuid)

    def test_delete_location(self):
        location = self.locations.create_item(TEST_LOCATION)
        self.assertIsNotNone(self.locations.find_item(location.uuid))
        with self.assert_site_modified(self.site):
            self.assertTrue(self.locations.delete_item(location.uuid))
        self.assertIsNone(self.locations.find_item(location.uuid))

    def test_create_location_twice(self):
        self.locations.create_item(TEST_LOCATION)
        with self.assert_site_not_modified(self.site):
            self.assertRaisesRegexp(ValidationError,
                                    'Location already exists',
                                    self.locations.create_item,
                                    TEST_LOCATION)

    def test_create_location_twice_for_different_sites(self):
        self.locations.create_item(TEST_LOCATION)
        with self.assert_site_not_modified(self.site):
            with self.assert_site_modified(self.site2):
                self.site2.locations.create_item(TEST_LOCATION)

    def test_delete_location_twice(self):
        location = self.locations.create_item(TEST_LOCATION)
        self.assertTrue(self.locations.delete_item(location.uuid))
        self.assertFalse(self.locations.delete_item(location.uuid))

    def test_get_all_locations(self):
        location1 = self.locations.create_item('/foo')
        location2 = self.locations.create_item('/foo/bar')
        self.site2.locations.create_item('/foo/baz')
        self.assertEqual(2, self.locations.count())
        self.assertEqual(1, self.site2.locations.count())
        with self.assert_site_not_modified(self.site):
            self.assertItemsEqual(['/foo/bar', '/foo'],
                                  [l.path for l
                                   in self.locations.all()])
        self.locations.delete_item(location1.uuid)
        self.assertItemsEqual(['/foo/bar'],
                              [l.path for l
                               in self.locations.all()])
        self.assertEqual(1, self.locations.count())

    def test_get_all_locations_when_empty(self):
        self.assertEqual(0, self.locations.count())
        self.assertListEqual([], list(self.locations.all()))

    def test_grant_access(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        with self.assert_site_not_modified(self.site):
            self.assertFalse(location.can_access(user))
        with self.assert_site_modified(self.site):
            (perm, created) = location.grant_access(user.uuid)
        self.assertTrue(created)
        self.assertIsNotNone(perm)
        self.assertTrue(location.can_access(user))

    def test_grant_access_for_not_existing_user(self):
        location = self.locations.create_item(TEST_LOCATION)
        self.assertRaisesRegexp(LookupError,
                                'User not found',
                                location.grant_access,
                                FAKE_UUID)

    def test_grant_access_for_user_of_different_site(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.site2.locations.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user))
        self.assertRaisesRegexp(LookupError,
                                'User not found',
                                location.grant_access,
                                user.uuid)

    def test_grant_access_if_already_granted(self):
        location = self.locations.create_item(TEST_LOCATION)
        user = self.users.create_item(TEST_USER_EMAIL)
        (permission1, created1) = location.grant_access(user.uuid)
        self.assertTrue(created1)
        (permission2, created2) = location.grant_access(user.uuid)
        self.assertFalse(created2)
        self.assertEqual(permission1, permission2)
        self.assertEqual(TEST_USER_EMAIL, permission1.user.email)
        self.assertTrue(location.can_access(user))

    def test_grant_access_to_deleted_location(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        self.assertTrue(self.locations.delete_item(location.uuid))
        self.assertRaises(ValidationError,
                          location.grant_access,
                          user.uuid)

    def test_revoke_access(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        location.grant_access(user.uuid)
        self.assertTrue(location.can_access(user))
        with self.assert_site_modified(self.site):
            location.revoke_access(user.uuid)
        self.assertFalse(location.can_access(user))

    def test_revoke_not_granted_access(self):
        location = self.locations.create_item(TEST_LOCATION)
        user = self.users.create_item(TEST_USER_EMAIL)
        with self.assert_site_not_modified(self.site):
            self.assertRaisesRegexp(LookupError,
                                    'User can not access location.',
                                    location.revoke_access,
                                    user.uuid)

    def test_revoke_access_to_deleted_location(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        location.grant_access(user.uuid)
        self.assertTrue(self.locations.delete_item(location.uuid))
        self.assertRaisesRegexp(LookupError,
                                'User can not access location.',
                                location.revoke_access,
                                user.uuid)

    def test_deleting_user_revokes_access(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user))
        location.grant_access(user.uuid)
        self.assertTrue(location.can_access(user))
        self.users.delete_item(user.uuid)
        self.assertFalse(location.can_access(user))

    def test_deleting_location_revokes_access(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user))
        location.grant_access(user.uuid)
        self.assertTrue(location.can_access(user))
        self.locations.delete_item(location.uuid)
        self.assertFalse(location.can_access(user))

    def test_revoke_access_for_not_existing_user(self):
        location = self.locations.create_item(TEST_LOCATION)
        self.assertRaisesRegexp(LookupError,
                                'User not found',
                                location.revoke_access,
                                FAKE_UUID)

    def test_get_permission(self):
        location = self.locations.create_item(TEST_LOCATION)
        user1 = self.users.create_item(TEST_USER_EMAIL)
        self.assertRaisesRegexp(LookupError,
                                'User can not access',
                                location.get_permission,
                                user1.uuid)
        location.grant_access(user1.uuid)
        self.assertIsNotNone(location.get_permission(user1.uuid))

        user2 = self.site2.users.create_item(TEST_USER_EMAIL)
        # User does not belong to the site.
        self.assertRaisesRegexp(LookupError,
                                'User not found',
                                location.get_permission,
                                user2.uuid)

    def test_find_location_by_path(self):
        location = self.locations.create_item('/foo/bar')
        with self.assert_site_not_modified(self.site):
            self.assertEqual(location, self.locations.find_location('/foo/bar'))
            self.assertIsNone(self.site2.locations.find_location('/foo/bar'))

        self.assertEqual(
            location, self.locations.find_location('/foo/bar/'))
        self.assertIsNone(self.site2.locations.find_location('/foo/bar/'))

        self.assertEqual(
            location, self.locations.find_location('/foo/bar/b'))
        self.assertIsNone(self.site2.locations.find_location('/foo/bar/b'))

        self.assertEqual(
            location, self.locations.find_location('/foo/bar/baz'))
        self.assertIsNone(self.site2.locations.find_location('/foo/bar/baz'))

        self.assertEqual(
            location, self.locations.find_location('/foo/bar/baz/bar/'))
        self.assertIsNone(
            self.site2.locations.find_location('/foo/bar/baz/bar/'))

        self.assertIsNone(self.locations.find_location('/foo/ba'))
        self.assertIsNone(self.locations.find_location('/foo/barr'))
        self.assertIsNone(self.locations.find_location('/foo/foo/bar'))

    def test_more_specific_location_takes_precedence_over_generic(self):
        location1 = self.locations.create_item('/foo/bar')
        user = self.users.create_item('foo@example.com')
        location1.grant_access(user.uuid)

        location2 = self.locations.create_item('/foo/bar/baz')
        self.assertEqual(
            location1, self.locations.find_location('/foo/bar'))
        self.assertEqual(
            location1, self.locations.find_location('/foo/bar/ba'))
        self.assertEqual(
            location1, self.locations.find_location('/foo/bar/bazz'))

        self.assertEqual(
            location2, self.locations.find_location('/foo/bar/baz'))
        self.assertEqual(
            location2, self.locations.find_location('/foo/bar/baz/'))
        self.assertEqual(
            location2, self.locations.find_location('/foo/bar/baz/bam'))
        self.assertFalse(location2.can_access(user))

    def test_trailing_slash_respected(self):
        location = self.locations.create_item('/foo/bar/')
        self.assertIsNone(self.locations.find_location('/foo/bar'))

    def test_grant_access_to_root(self):
        location = self.locations.create_item('/')
        user = self.users.create_item('foo@example.com')
        location.grant_access(user.uuid)

        self.assertEqual(location, self.locations.find_location('/'))
        self.assertEqual(location, self.locations.find_location('/f'))
        self.assertEqual(
            location, self.locations.find_location('/foo/bar/baz'))

    def test_grant_open_access(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        self.assertFalse(location.open_access_granted())
        self.assertFalse(location.open_access_requires_login())
        self.assertFalse(location.can_access(user))

        with self.assert_site_modified(self.site):
            location.grant_open_access(require_login=False)
        with self.assert_site_not_modified(self.site):
            self.assertTrue(location.open_access_granted())
            self.assertFalse(location.open_access_requires_login())
            self.assertTrue(location.can_access(user))

        with self.assert_site_modified(self.site):
            location.revoke_open_access()
        self.assertFalse(location.open_access_granted())
        self.assertFalse(location.can_access(user))

    def test_user_of_different_site_can_not_access_even_if_open_location(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.site2.locations.create_item(TEST_LOCATION)
        location.grant_open_access(require_login=True)
        self.assertFalse(location.can_access(user))

    def test_grant_authenticated_open_access(self):
        user = self.users.create_item(TEST_USER_EMAIL)
        location = self.locations.create_item(TEST_LOCATION)
        self.assertFalse(location.open_access_granted())
        self.assertFalse(location.open_access_requires_login())
        self.assertFalse(location.can_access(user))

        with self.assert_site_modified(self.site):
            location.grant_open_access(require_login=True)
        self.assertTrue(location.open_access_granted())
        self.assertTrue(location.open_access_requires_login())
        self.assertTrue(location.can_access(user))

        location.revoke_open_access()
        self.assertFalse(location.open_access_granted())
        self.assertFalse(location.can_access(user))

    def test_has_open_location(self):
        self.assertFalse(self.locations.has_open_location())
        self.locations.create_item('/bar')
        self.assertFalse(self.locations.has_open_location())
        location = self.locations.create_item('/foo')
        location.grant_open_access(False)
        self.assertTrue(self.locations.has_open_location())
        location.grant_open_access(True)
        self.assertTrue(self.locations.has_open_location())
        self.assertFalse(self.site2.locations.has_open_location())
        location.revoke_open_access()
        self.assertFalse(self.locations.has_open_location())

    def test_has_open_location_with_login(self):
        self.assertFalse(self.locations.has_open_location_with_login())
        self.locations.create_item('/bar')
        self.assertFalse(self.locations.has_open_location_with_login())
        location = self.locations.create_item('/foo')
        location.grant_open_access(False)
        self.assertFalse(self.locations.has_open_location_with_login())
        location.grant_open_access(True)
        self.assertTrue(self.locations.has_open_location_with_login())
        self.assertFalse(self.site2.locations.has_open_location_with_login())

    def test_get_allowed_users(self):
        location1 = self.locations.create_item('/foo/bar')
        location2 = self.locations.create_item('/foo/baz')

        user1 = self.users.create_item('foo@example.com')
        user2 = self.users.create_item('bar@example.com')
        user3 = self.users.create_item('baz@example.com')

        location1.grant_access(user1.uuid)
        location1.grant_access(user2.uuid)
        location2.grant_access(user3.uuid)

        with self.assert_site_not_modified(self.site):
            self.assertItemsEqual(['foo@example.com', 'bar@example.com'],
                                  [u.email for u in location1.allowed_users()])
            self.assertItemsEqual(['baz@example.com'],
                                  [u.email for u in location2.allowed_users()])

        location1.revoke_access(user1.uuid)
        self.assertItemsEqual(['bar@example.com'],
                              [u.email for u in location1.allowed_users()])

    def test_get_allowed_users_when_empty(self):
        location = self.locations.create_item(TEST_LOCATION)
        self.assertEqual([], location.allowed_users())

    def test_location_path_validation(self):
        with self.assert_site_not_modified(self.site):
            self.assertRaisesRegexp(ValidationError,
                                    'should be absolute and normalized',
                                    self.locations.create_item,
                                    '/foo/../bar')
            self.assertRaisesRegexp(ValidationError,
                                    'should not contain parameters',
                                    self.locations.create_item,
                                    '/foo;bar')
            self.assertRaisesRegexp(ValidationError,
                                    'should not contain query',
                                    self.locations.create_item,
                                    '/foo?s=bar')
            self.assertRaisesRegexp(ValidationError,
                                    'should not contain fragment',
                                    self.locations.create_item,
                                    '/foo#bar')
            self.assertRaisesRegexp(ValidationError,
                                    'should contain only ascii',
                                    self.locations.create_item,
                                    u'/żbik')
            long_path = '/a' * (self.locations.PATH_LEN_LIMIT / 2) + 'a'
            self.assertRaisesRegexp(ValidationError,
                                    'too long',
                                    self.locations.create_item,
                                    long_path)

    """Path passed to create_location is expected to be saved verbatim."""
    def test_location_path_not_encoded(self):
        self.assertEqual(
            '/foo%20bar', self.locations.create_item('/foo%20bar').path)
        self.assertEqual(
            '/foo~', self.locations.create_item('/foo~').path)
        self.assertEqual(
            '/foo/bar!@7*', self.locations.create_item('/foo/bar!@7*').path)

    def test_locations_limit(self):
        limit = 10
        self.site.locations_limit = limit
        for i in range(0, limit):
            self.locations.create_item('/foo%d' % (i))
        self.assertRaisesRegexp(LimitExceeded,
                                'Locations limit exceeded',
                                self.locations.create_item,
                                '/foo10')

class AliasesCollectionTest(ModelTestCase):

    def test_add_alias(self):
        with self.assert_site_modified(self.site):
            alias = self.aliases.create_item(TEST_SITE)
        self.assertEqual(TEST_SITE, alias.url)
        self.assertFalse(alias.force_ssl)
        self.assertTrue(len(alias.uuid) > 20)

    def test_add_alias_invalid_url(self):
        self.assertRaisesRegexp(ValidationError,
                                'missing scheme',
                                self.aliases.create_item,
                                'foo.example.com')

    def test_default_port_removed(self):
        with self.assert_site_modified(self.site):
            alias = self.aliases.create_item('http://example.org:80')
        self.assertEqual('http://example.org', alias.url)

    def test_normalized(self):
        with self.assert_site_modified(self.site):
            alias = self.aliases.create_item('  hTtp://eXamPlE.org')
        self.assertEqual('http://example.org', alias.url)


    def test_alias_must_be_unique(self):
        self.aliases.create_item('http://example.org:123')
        self.assertRaisesRegexp(ValidationError,
                                'already exists',
                                self.aliases.create_item,
                                'http://example.org:123')

    def test_alias_for_different_site_can_duplicate(self):
        alias = self.aliases.create_item('http://example.org:123')
        self.assertIsNotNone(alias)
        alias = self.site2.aliases.create_item('http://example.org:123')
        self.assertIsNotNone(alias)

    def test_find_alias_by_url(self):
        self.assertIsNone(self.aliases.find_item_by_url(TEST_SITE))
        alias1 = self.aliases.create_item(TEST_SITE)
        with self.assert_site_not_modified(self.site):
            alias2 = self.aliases.find_item_by_url(TEST_SITE)
        self.assertIsNotNone(alias2)
        self.assertEqual(alias1, alias2)

    def test_find_alias_by_url_different_site(self):
        self.aliases.create_item(TEST_SITE)
        self.assertIsNone(self.site2.aliases.find_item_by_url(TEST_SITE))

    def test_aliases_limit(self):
        limit = 10
        self.site.aliases_limit = limit
        for i in range(0, limit):
            self.aliases.create_item('http://foo%d.org' % (i))
        self.assertRaisesRegexp(LimitExceeded,
                                'Aliases limit exceeded',
                                self.aliases.create_item,
                                'http://foo10.org')

    def test_alias_length_limit(self):
        long_url = 'https://%s.org' % ('x' * self.aliases.ALIAS_LEN_LIMIT)
        self.assertRaisesRegexp(ValidationError,
                                'Url too long',
                                self.aliases.create_item,
                                long_url)

########NEW FILE########
__FILENAME__ = tests_site_cache
# wwwhisper - web access control.
# Copyright (C) 2013 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.test import TestCase
from mock import Mock
from wwwhisper_auth.site_cache import CachingSitesCollection
from wwwhisper_auth.site_cache import SiteCache

TEST_SITE = 'https://example.com'

class FakeCacheUpdater(object):
    def __init__(self):
        self.return_value = False

    def is_obsolete(self, site):
        return self.return_value

class SiteCacheTest(TestCase):

    def setUp(self):
        self.updater = FakeCacheUpdater()
        self.cache = SiteCache(self.updater)

    def test_cache(self):
        site = Mock()
        site.site_id = 'foo'
        self.assertIsNone(self.cache.get('foo'))
        self.cache.insert(site)
        self.assertEqual(site, self.cache.get('foo'))
        self.assertIsNone(self.cache.get('bar'))
        self.cache.delete('foo')
        self.assertIsNone(self.cache.get('foo'))

    def test_cache_obsolete(self):
        site = Mock()
        site.site_id = 'foo'
        self.cache.insert(site)
        self.assertEqual(site, self.cache.get('foo'))
        # Configure cache updater to obsolete the cached element.
        self.updater.return_value = True
        self.assertIsNone(self.cache.get('foo'))


class CachingSitesCollectionTest(TestCase):

    def setUp(self):
        self.sites = CachingSitesCollection()

    def test_find_returns_cached_item_if_not_modified(self):
        site = self.sites.create_item(TEST_SITE)
        site2 = self.sites.find_item(TEST_SITE)
        self.assertTrue(site is site2)

    def test_find_rereads_item_if_externally_modified(self):
        site = self.sites.create_item(TEST_SITE)
        orig_mod_id = site.mod_id
        # Simulate modification by an external process, not visible to
        # the current one.
        site.site_modified()
        site.mod_id = orig_mod_id
        site2 = self.sites.find_item(TEST_SITE)
        self.assertTrue(site is not site2)

    def test_delete_removes_cached_item(self):
        site = self.sites.create_item(TEST_SITE)
        self.assertTrue(self.sites.delete_item(TEST_SITE))
        self.assertIsNone(self.sites.find_item(TEST_SITE))

########NEW FILE########
__FILENAME__ = tests_url_utils
# wwwhisper - web access control.
# Copyright (C) 2012 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.test import TestCase
from wwwhisper_auth.url_utils import collapse_slashes
from wwwhisper_auth.url_utils import contains_fragment
from wwwhisper_auth.url_utils import contains_params
from wwwhisper_auth.url_utils import contains_query
from wwwhisper_auth.url_utils import decode
from wwwhisper_auth.url_utils import is_canonical
from wwwhisper_auth.url_utils import validate_site_url
from wwwhisper_auth.url_utils import remove_default_port
from wwwhisper_auth.url_utils import strip_query

class PathTest(TestCase):

    def test_is_canonical(self):
        self.assertTrue(is_canonical('/'))
        self.assertTrue(is_canonical('/foo/bar'))
        self.assertTrue(is_canonical('/foo/bar/'))
        self.assertTrue(is_canonical('/foo/bar/  '))


        self.assertFalse(is_canonical(''))
        self.assertFalse(is_canonical('foo'))
        self.assertFalse(is_canonical('//'))
        self.assertFalse(is_canonical(' /'))
        self.assertFalse(is_canonical(' //'))
        self.assertFalse(is_canonical('//foo'))
        self.assertFalse(is_canonical('/foo/bar/..'))
        self.assertFalse(is_canonical('/foo//bar'))
        self.assertFalse(is_canonical('/foo/bar//'))
        self.assertFalse(is_canonical('/foo/bar/./foo'))

    def test_collapse_slashes(self):
        self.assertEqual(collapse_slashes('/'), '/')
        self.assertEqual(collapse_slashes('/foo/'), '/foo/')
        self.assertEqual(collapse_slashes('/foo'), '/foo')

        self.assertEqual(collapse_slashes('//'), '/')
        self.assertEqual(collapse_slashes('///'), '/')
        self.assertEqual(collapse_slashes('///foo//////bar//'), '/foo/bar/')
        self.assertEqual(collapse_slashes('///foo// ///bar//'), '/foo/ /bar/')

    def test_decode(self):
        self.assertEqual('/foo bar#', decode('/foo%20bar%23'))
        self.assertEqual('/FoO', decode('%2F%46%6f%4F'))
        self.assertEqual('/', decode('/'))
        self.assertEqual('/foo', decode('/foo'))
        self.assertEqual('/foo/', decode('/foo/'))

    def test_strip_query(self):
        self.assertEqual('/foo/', strip_query('/foo/?bar=abc'))
        self.assertEqual('/foo', strip_query('/foo?'))
        self.assertEqual('/foo', strip_query('/foo?bar=abc?baz=xyz'))

    def test_contains_fragment(self):
        self.assertTrue(contains_fragment('/foo#123'))
        self.assertTrue(contains_fragment('/foo#'))
        # Encoded '#' should not be treated as fragment separator.
        self.assertFalse(contains_fragment('/foo%23'))

    def test_contains_query(self):
        self.assertTrue(contains_query('/foo?'))
        self.assertFalse(contains_query('/foo'))

    def test_contains_fragment(self):
        self.assertTrue(contains_params('/foo;'))
        self.assertFalse(contains_params('/foo'))

class SiteUrlTest(TestCase):

    def assertInvalid(self, result, errorRegexp):
        self.assertEqual(False, result[0])
        self.assertRegexpMatches(result[1], errorRegexp)

    def assertValid(self, result):
        self.assertEqual((True, None), result)

    def test_validation(self):
        self.assertInvalid(
            validate_site_url('example.com'), 'missing scheme')
        self.assertInvalid(
            validate_site_url('ftp://example.com'), 'incorrect scheme')
        self.assertInvalid(
            validate_site_url('http://'), 'missing domain')
        self.assertInvalid(
            validate_site_url('http://example.com/foo'), 'contains path')
        self.assertInvalid(
            validate_site_url('http://example.com/'), 'contains path')
        self.assertInvalid(
            validate_site_url('http://example.com?a=b'), 'contains query')
        self.assertInvalid(
            validate_site_url('http://example.com#boo'), 'contains fragment')
        self.assertInvalid(
            validate_site_url('http://alice@example.com'), 'contains username')
        self.assertInvalid(
            validate_site_url('http://:pass@example.com'), 'contains password')

        self.assertValid(validate_site_url('http://example.com'))
        self.assertValid(validate_site_url('http://example.com:80'))
        self.assertValid(validate_site_url('https://example.com'))
        self.assertValid(validate_site_url('https://example.com:123'))


    def test_remove_default_port(self):
        self.assertEqual('http://example.com',
                         remove_default_port('http://example.com'))
        self.assertEqual('http://example.com:56',
                         remove_default_port('http://example.com:56'))

        self.assertEqual('https://example.com',
                         remove_default_port('https://example.com:443'))
        self.assertEqual('http://example.com:443',
                         remove_default_port('http://example.com:443'))

        self.assertEqual('http://example.com',
                         remove_default_port('http://example.com:80'))
        self.assertEqual('https://example.com:80',
                         remove_default_port('https://example.com:80'))

########NEW FILE########
__FILENAME__ = tests_views
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from wwwhisper_auth import backend
from wwwhisper_auth.tests.utils import HttpTestCase
from wwwhisper_auth.tests.utils import TEST_SITE

import json
import wwwhisper_auth.urls

INCORRECT_ASSERTION = "ThisAssertionIsFalse"

class FakeAssertionVeryfingBackend(ModelBackend):
    def authenticate(self, assertion, site, site_url=TEST_SITE):
        if assertion == INCORRECT_ASSERTION:
            raise backend.AssertionVerificationException(
                'Assertion verification failed.')
        return site.users.find_item_by_email(assertion)

class AuthTestCase(HttpTestCase):
    def setUp(self):
        settings.AUTHENTICATION_BACKENDS = (
            'wwwhisper_auth.tests.FakeAssertionVeryfingBackend',)
        super(AuthTestCase, self).setUp()

    def login(self, email, site=None):
        if site is None:
            site = self.site
        self.assertTrue(self.client.login(assertion=email, site=site))
        # Login needs to set user_id in session.
        user = site.users.find_item_by_email(email)
        self.assertIsNotNone(user)
        # Session must be stored in a temporary variable, otherwise
        # updating does not work.
        s = self.client.session
        s['user_id'] = user.id
        s.save()

class LoginTest(AuthTestCase):
    def test_login_requires_assertion(self):
        response = self.post('/auth/api/login/', {})
        self.assertEqual(400, response.status_code)

    def test_login_fails_if_unknown_user(self):
        response = self.post('/auth/api/login/',
                             {'assertion' : 'foo@example.com'})
        self.assertEqual(403, response.status_code)

    def test_login_fails_if_incorrect_assertion(self):
        response = self.post('/auth/api/login/',
                             {'assertion' : INCORRECT_ASSERTION})
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(
            response.content, 'Assertion verification failed')

    def test_login_succeeds_if_known_user(self):
        self.site.users.create_item('foo@example.com')
        response = self.post('/auth/api/login/',
                             {'assertion' : 'foo@example.com'})
        self.assertEqual(204, response.status_code)

class AuthTest(AuthTestCase):
    def test_is_authorized_requires_path_parameter(self):
        response = self.get('/auth/api/is-authorized/?pat=/foo')
        self.assertEqual(400, response.status_code)

    def test_is_authorized_if_not_authenticated(self):
        location = self.site.locations.create_item('/foo/')
        response = self.get('/auth/api/is-authorized/?path=/foo/')
        self.assertEqual(401, response.status_code)
        self.assertTrue(response.has_header('WWW-Authenticate'))
        self.assertFalse(response.has_header('User'))
        self.assertEqual('VerifiedEmail', response['WWW-Authenticate'])
        self.assertRegexpMatches(response['Content-Type'], "text/plain")
        self.assertEqual('Authentication required.', response.content)

    def test_is_authorized_if_not_authorized(self):
        self.site.users.create_item('foo@example.com')
        self.login('foo@example.com')
        response = self.get('/auth/api/is-authorized/?path=/foo/')
        # For an authenticated user 'User' header should be always returned.
        self.assertEqual(403, response.status_code)
        self.assertEqual('foo@example.com', response['User'])
        self.assertRegexpMatches(response['Content-Type'], "text/plain")
        self.assertEqual('User not authorized.', response.content)

    def test_is_authorized_if_authorized(self):
        user = self.site.users.create_item('foo@example.com')
        location = self.site.locations.create_item('/foo/')
        location.grant_access(user.uuid)
        self.login('foo@example.com')
        response = self.get('/auth/api/is-authorized/?path=/foo/')
        self.assertEqual(200, response.status_code)
        self.assertEqual('foo@example.com', response['User'])

    def test_is_authorized_if_user_of_other_site(self):
        site2 = self.sites.create_item('somesite')
        user = site2.users.create_item('foo@example.com')
        location = self.site.locations.create_item('/foo/')
        self.login('foo@example.com', site2)
        response = self.get('/auth/api/is-authorized/?path=/foo/')

    def test_is_authorized_if_open_location(self):
        location = self.site.locations.create_item('/foo/')
        location.grant_open_access(require_login=False)
        response = self.get('/auth/api/is-authorized/?path=/foo/')
        self.assertFalse(response.has_header('User'))
        self.assertEqual(200, response.status_code)

    def test_is_authorized_if_open_location_and_authenticated(self):
        user = self.site.users.create_item('foo@example.com')
        self.login('foo@example.com')
        location = self.site.locations.create_item('/foo/')
        location.grant_open_access(require_login=False)
        response = self.get('/auth/api/is-authorized/?path=/foo/')
        self.assertEqual(200, response.status_code)
        self.assertEqual('foo@example.com', response['User'])

    def test_is_authorized_if_invalid_path(self):
        user = self.site.users.create_item('foo@example.com')
        location = self.site.locations.create_item('/foo/')
        location.grant_access(user.uuid)
        self.login('foo@example.com')

        response = self.get('/auth/api/is-authorized/?path=/bar/../foo/')
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Path should be absolute and normalized')

        response = self.get('/auth/api/is-authorized/?path=.')
        self.assertEqual(400, response.status_code)
        self.assertRegexpMatches(response.content,
                                 'Path should be absolute and normalized')

    def test_is_authorized_decodes_path(self):
        location = self.site.locations.create_item('/f/')
        location.grant_open_access(require_login=False)
        response = self.get('/auth/api/is-authorized/?path=%2F%66%2F')
        self.assertEqual(200, response.status_code)

        response = self.get('/auth/api/is-authorized/?path=%2F%66')
        self.assertEqual(401, response.status_code)

    def test_is_authorized_collapses_slashes(self):
        location = self.site.locations.create_item('/f/')
        location.grant_open_access(require_login=False)
        response = self.get('/auth/api/is-authorized/?path=///f/')
        self.assertEqual(200, response.status_code)

    def test_is_authorized_does_not_allow_requests_with_user_header(self):
        user = self.site.users.create_item('foo@example.com')
        location = self.site.locations.create_item('/foo/')
        location.grant_access(user.uuid)
        self.login('foo@example.com')
        response = self.get('/auth/api/is-authorized/?path=/foo/',
                            HTTP_USER='bar@example.com')
        self.assertEqual(400, response.status_code)

    def test_caching_disabled_for_auth_request_results(self):
        response = self.get('/auth/api/is-authorized/?path=/foo/')
        self.assertTrue(response.has_header('Cache-Control'))
        control = response['Cache-Control']
        # index throws ValueError if not found.
        control.index('no-cache')
        control.index('no-store')
        control.index('must-revalidate')
        control.index('max-age=0')

    # Make sure HTML responses are returned when request accepts HTML.

    def test_is_authorized_if_not_authenticated_html_response(self):
        location = self.site.locations.create_item('/foo/')
        response = self.get('/auth/api/is-authorized/?path=/foo/',
                            HTTP_ACCEPT='text/plain, text/html')
        self.assertEqual(401, response.status_code)
        self.assertRegexpMatches(response['Content-Type'], 'text/html')
        self.assertRegexpMatches(response.content, '<body')

        response = self.get('/auth/api/is-authorized/?path=/foo/',
                            HTTP_ACCEPT='text/plain')
        self.assertEqual(401, response.status_code)
        self.assertRegexpMatches(response['Content-Type'], 'text/plain')

    def test_is_authorized_if_not_authenticated_custom_html_response(self):
        self.site.update_skin(
            title='Foo', header='Bar', message='Baz', branding=False)
        response = self.get('/auth/api/is-authorized/?path=/foo/',
                            HTTP_ACCEPT='*/*')
        self.assertEqual(401, response.status_code)
        self.assertRegexpMatches(response['Content-Type'], 'text/html')
        self.assertRegexpMatches(response.content, '<title>Foo</title>')
        self.assertRegexpMatches(response.content, '<h1>Bar</h1>')
        self.assertRegexpMatches(response.content, 'class="lead">Baz')

    def test_is_authorized_if_not_authorized_html_response(self):
        self.site.users.create_item('foo@example.com')
        self.login('foo@example.com')
        response = self.get('/auth/api/is-authorized/?path=/foo/',
                            HTTP_ACCEPT='*/*')
        self.assertEqual(403, response.status_code)
        self.assertRegexpMatches(response['Content-Type'], 'text/html')
        self.assertRegexpMatches(response.content, '<body')

        response = self.get('/auth/api/is-authorized/?path=/foo/',
                            HTTP_ACCEPT='text/plain, audio/*')
        self.assertEqual(403, response.status_code)
        self.assertRegexpMatches(response['Content-Type'], 'text/plain')

class LogoutTest(AuthTestCase):
    def test_authentication_requested_after_logout(self):
        user = self.site.users.create_item('foo@example.com')
        self.post('/auth/api/login/', {'assertion' : 'foo@example.com'})

        response = self.get('/auth/api/is-authorized/?path=/bar/')
        # Not authorized
        self.assertEqual(403, response.status_code)

        response = self.post('/auth/api/logout/', {})
        self.assertEqual(204, response.status_code)

        response = self.get('/auth/api/is-authorized/?path=/bar/')
        # Not authenticated
        self.assertEqual(401, response.status_code)


class WhoAmITest(AuthTestCase):
    def test_whoami_returns_email_of_logged_in_user(self):
        self.site.users.create_item('foo@example.com')

        # Not authorized.
        response = self.get('/auth/api/whoami/')
        self.assertEqual(401, response.status_code)

        self.post('/auth/api/login/', {'assertion' : 'foo@example.com'})
        response = self.get('/auth/api/whoami/')
        self.assertEqual(200, response.status_code)
        parsed_response_body = json.loads(response.content)
        self.assertEqual('foo@example.com', parsed_response_body['email'])

    def test_whoami_for_user_of_differen_site(self):
        site2 = self.sites.create_item('somesite')
        site2.users.create_item('foo@example.com')
        self.login('foo@example.com', site2)
        # Not authorized.
        # Request is run for TEST_SITE, but user belongs to site2_id.
        response = self.get('/auth/api/whoami/')
        self.assertEqual(401, response.status_code)

class CsrfTokenTest(AuthTestCase):

    def test_token_returned_in_cookie(self):
        response = self.get('/auth/api/csrftoken/')
        self.assertEqual(204, response.status_code)
        self.assertTrue(
            len(response.cookies[settings.CSRF_COOKIE_NAME].coded_value) > 20)

    # Ensures that ProtectCookiesMiddleware is applied.
    def test_csrf_cookie_http_only(self):
        response = self.get('/auth/api/csrftoken/')
        self.assertTrue(response.cookies[settings.CSRF_COOKIE_NAME]['secure'])


class SessionCacheTest(AuthTestCase):
    def test_user_cached_in_session(self):
        user = self.site.users.create_item('foo@example.com')
        response = self.post('/auth/api/login/',
                             {'assertion' : 'foo@example.com'})
        self.assertEqual(204, response.status_code)
        s = self.client.session
        user_id = s['user_id']
        self.assertIsNotNone(user_id)
        self.assertEqual(user_id, user.id)

########NEW FILE########
__FILENAME__ = utils
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Utilities to simplify testing."""

from django.test import TestCase
from django.test.client import Client
from wwwhisper_auth.models import SitesCollection
from wwwhisper_auth.models import SINGLE_SITE_ID

import json

TEST_SITE = 'https://foo.example.org:8080'

class HttpTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.sites = SitesCollection()
        # For each test case, test site must exist, so it can be set
        # by SetSiteMiddleware
        self.site = self.sites.create_item(SINGLE_SITE_ID)
        self.site.aliases.create_item(TEST_SITE)

    def post(self, url, args):
        return self.client.post(
            url, json.dumps(args), 'application/json; charset=UTF-8',
            HTTP_SITE_URL=TEST_SITE)

    """ To be used for views that are not contacted via Ajax. """
    def post_form(self, url, args):
        return self.client.post(url, args)

    def get(self, url, **extra_headers):
        return self.client.get(url, HTTP_SITE_URL=TEST_SITE, **extra_headers)

    def put(self, url, args=None):
        if args is None:
            return self.client.put(url, HTTP_SITE_URL=TEST_SITE)
        return self.client.put(
            url, data=json.dumps(args),
            content_type='application/json;  charset=UTF-8',
            HTTP_SITE_URL=TEST_SITE)


    def delete(self, url):
        return self.client.delete(url, HTTP_SITE_URL=TEST_SITE)



########NEW FILE########
__FILENAME__ = urls
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Urls exposed by the wwwhisper_auth application.

is-authorized/ URL does not need to be exposed by the HTTP server to
the outside world, other views need to be externally accessible.
"""

from django.conf import settings
from django.conf.urls import patterns, url
from wwwhisper_auth.views import Auth, CsrfToken, Login, Logout, WhoAmI

urlpatterns = patterns(
    'wwwhisper_auth.views',
    url(r'^csrftoken/$', CsrfToken.as_view()),
    url(r'^login/$', Login.as_view()),
    url(r'^logout/$', Logout.as_view()),
    url(r'^whoami/$', WhoAmI.as_view()),
    url(r'^is-authorized/$', Auth.as_view(), name='auth-request'),
    )

########NEW FILE########
__FILENAME__ = url_utils
# wwwhisper - web access control.
# Copyright (C) 2012 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Functions that operate on an HTTP resource path."""

import posixpath
import urllib
import re
import urlparse

def strip_query(path):
    """Strips query from a path."""
    query_start = path.find('?')
    if query_start != -1:
        return path[:query_start]
    return path

def decode(path):
    """Decodes URL encoded characters in path."""
    return urllib.unquote_plus(path)

def collapse_slashes(path):
    """Replaces repeated path separators ('/') with a single one."""
    return re.sub('//+', '/', path)

def is_canonical(path):
    """True if path is absolute and normalized.

    Canonical path is unique, i.e. two different such paths are never
    equivalent.
    """
    # Posix recognizes '//' as a normalized path, but it is not
    # canonical (it is the same as '/').
    if path == '' or not posixpath.isabs(path) or path.startswith('//'):
        return False
    # Normpath removes trailing '/'.
    normalized_path =  posixpath.normpath(path)
    if (normalized_path != path and normalized_path + '/' != path):
        return False
    return True


def contains_fragment(path):
    """True if path contains fragment id ('#' part)."""
    return path.count('#') != 0

def contains_query(path):
    """True if path contains query string ('?' part)."""
    return path.count('?') != 0

def contains_params(path):
    """True if path contains params (';' part)."""
    return path.count(';') != 0


def validate_site_url(url):
    parsed_url = urlparse.urlparse(url)
    if parsed_url.scheme == '':
        return (False, 'missing scheme (http:// or https://)')
    if parsed_url.scheme not in ('http', 'https'):
        return (False, 'incorrect scheme (should be http:// or https://)')
    if parsed_url.netloc == '':
        return (False, 'missing domain')

    for attr in ['path', 'username', 'query', 'params', 'fragment', 'password']:
        val = getattr(parsed_url, attr, None)
        if val is not None and val != '':
            return (False, 'contains ' + attr)
    return (True, None)

def remove_default_port(url):
    parts = url.split(':')
    if len(parts) != 3:
        return url
    scheme, rest, port = parts
    if ((scheme == 'https' and port == '443') or
        (scheme == 'http' and port == '80')):
        return "%s:%s" % (scheme, rest)
    return url

########NEW FILE########
__FILENAME__ = views
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Views that handle user authentication and authorization."""

from django.contrib import auth
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View
from wwwhisper_auth import http
from wwwhisper_auth import url_utils
from wwwhisper_auth.backend import AssertionVerificationException

import logging

logger = logging.getLogger(__name__)

def get_user(request):
    """Retrieves a user object associated with a given request.

    The user id of a logged in user is stored in the session key-value store.
    """
    user_id = request.session.get('user_id', None)
    if user_id is not None:
        return request.site.users.get_unique(lambda user: user.id == user_id)
    return None

class Auth(View):
    """Handles auth request from the HTTP server.

    Auth request determines whether a user is authorized to access a
    given location. It must be sent by the HTTP server for each
    request to wwwhisper protected location. Auth request includes all
    headers of the original request and a path the original request is
    trying to access. The result of the request determines the action
    to be performed by the HTTP server:

      401: The user is not authenticated (no valid session cookie
           set).

      403: The user is authenticated (the request contains a valid
           session cookie) but is not authorized to access the
           location. The error should be passed to the user. The
           'User' header in the returned response containts email of
           the user.

      400: Request is malformed (suspicious path format, 'User' header
           set in the request, ...).

      200: User is authenticated and authorized to access the location
           or the location does not require authorization. The
           original request should be allowed. The 'User' header in
           the returned response containts email of the user.

      Any other result code should be passed to the user without
      granting access.

      Auth view does not need to be externally accessible.
    """

    @http.never_ever_cache
    def get(self, request):
        """Invoked by the HTTP server with a single path argument.

        The HTTP server should pass the path argument verbatim,
        without any transformations or decoding. Access control
        mechanism should work on user visible paths, not paths after
        internal rewrites performed by the server.

        At the moment, the path is allowed to contain a query part,
        which is ignored (this is because nginx does not expose
        encoded path without the query part).

        The method follows be conservative in what you accept
        principle. The path should be absolute and normalized, without
        fragment id, otherwise access is denied. Browsers in normal
        operations perform path normalization and do not send fragment
        id. Multiple consecutive '/' separators are permitted, because
        these are not normalized by browsers, and are used by
        legitimate applications.  Paths with '/./' and '/../', should
        not be normally sent by browsers and can be a sign of
        something suspicious happening. It is extremely important that
        wwwhisper does not perform any path transformations that are
        not be compatible with transformations done by the HTTP
        server.
       """
        encoded_path = self._extract_encoded_path_argument(request)
        if encoded_path is None:
            return http.HttpResponseBadRequest(
                "Auth request should have 'path' argument.")

        # Do not allow requests that contain the 'User' header. The
        # header is passed to backends and must be guaranteed to be
        # set by wwwhisper.
        # This check should already be performed by HTTP server.
        if 'HTTP_USER' in request.META:
            return http.HttpResponseBadRequest(
                "Client can not set the 'User' header")

        debug_msg = "Auth request to '%s'" % (encoded_path)

        path_validation_error = None
        if url_utils.contains_fragment(encoded_path):
            path_validation_error = "Path should not include fragment ('#')"
        else:
            stripped_path = url_utils.strip_query(encoded_path)
            decoded_path = url_utils.decode(stripped_path)
            decoded_path = url_utils.collapse_slashes(decoded_path)
            if not url_utils.is_canonical(decoded_path):
                path_validation_error = 'Path should be absolute and ' \
                    'normalized (starting with / without /../ or /./ or //).'
        if path_validation_error is not None:
            logger.debug('%s: incorrect path.' % (debug_msg))
            return http.HttpResponseBadRequest(path_validation_error)

        user = get_user(request)
        location = request.site.locations.find_location(decoded_path)
        if user is not None:

            debug_msg += " by '%s'" % (user.email)
            respone = None

            if location is not None and location.can_access(user):
                logger.debug('%s: access granted.' % (debug_msg))
                response =  http.HttpResponseOK('Access granted.')
            else:
                logger.debug('%s: access denied.' % (debug_msg))
                response = http.HttpResponseNotAuthorized(
                    self._html_or_none(request, 'not_authorized.html',
                                       {'email' : user.email}))
            response['User'] = user.email
            return response

        if (location is not None and location.open_access_granted() and
            not location.open_access_requires_login()):
            logger.debug('%s: authentication not required, access granted.'
                         % (debug_msg))
            return http.HttpResponseOK('Access granted.')
        logger.debug('%s: user not authenticated.' % (debug_msg))
        return http.HttpResponseNotAuthenticated(
            self._html_or_none(request, 'login.html', request.site.skin()))

    def _html_or_none(self, request, template, context={}):
        """Renders html response string from a given template.

        Returns None if request does not accept html response type.
        """
        if (http.accepts_html(request.META.get('HTTP_ACCEPT'))):
            return render_to_string(template, context)
        return None

    @staticmethod
    def _extract_encoded_path_argument(request):
        """Get 'path' argument or None.

        Standard Django mechanism for accessing arguments is not used
        because path is needed in a raw, encoded form. Django would
        decode it, making it impossible to correctly recognize the
        query part and to determine if the path contains fragment.
        """
        request_path_and_args = request.get_full_path()
        assert request_path_and_args.startswith(request.path)
        args = request_path_and_args[len(request.path):]
        if not args.startswith('?path='):
            return None
        return args[len('?path='):]

class CsrfToken(View):
    """Establishes Cross Site Request Forgery protection token."""

    @http.never_ever_cache
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """Sets a cookie with CSRF protection token.

        The method must be called if the cookie is missing before any
        CSRF protected HTTP method is called (all HTTP methods of
        views that extend RestView). Returned token must be set in
        'X-CSRFToken' header when the protected method is called,
        otherwise the call fails. It is enough to get the token once
        and reuse it for all subsequent calls to CSRF protected
        methods.
        """
        return http.HttpResponseNoContent()

class Login(http.RestView):
    """Allows a user to authenticates with BrowserID."""

    def post(self, request, assertion):
        """Logs a user in (establishes a session cookie).

        Verifies BrowserID assertion and check that a user with an
        email verified by the BrowserID is known (added to users
        list).
        """
        if assertion == None:
            return http.HttpResponseBadRequest('BrowserId assertion not set.')
        try:
            user = auth.authenticate(site=request.site,
                                     site_url=request.site_url,
                                     assertion=assertion)
        except AssertionVerificationException as ex:
            logger.debug('Assertion verification failed.')
            return http.HttpResponseBadRequest(str(ex))
        if user is not None:
            auth.login(request, user)

            # Store all user data needed by Auth view in session, this
            # way, user table does not need to be queried during the
            # performance critical request (sessions are cached).
            request.session['user_id'] = user.id
            logger.debug('%s successfully logged.' % (user.email))
            return http.HttpResponseNoContent()
        else:
            # Unkown user.
            # Return not authorized because request was well formed (400
            # doesn't seem appropriate).
            return http.HttpResponseNotAuthorized()

class Logout(http.RestView):
    """Allows a user to logout."""

    def post(self, request):
        """Logs a user out (invalidates a session cookie)."""
        auth.logout(request)
        # TODO: send a message to all processes to discard cached user session.
        response = http.HttpResponseNoContent()
        return response

class WhoAmI(http.RestView):
    """Allows to obtain an email of a currently logged in user."""

    def get(self, request):
        """Returns an email or an authentication required error."""
        user = get_user(request)
        if user is not None:
            return http.HttpResponseOKJson({'email': user.email})
        return http.HttpResponseNotAuthenticated()

########NEW FILE########
__FILENAME__ = cdn_container
# Allows to server static files from a separate CDN server. Can be
# empty.
CDN_CONTAINER=""

########NEW FILE########
__FILENAME__ = settings
# Django settings for wwwhisper_service project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG


# If WWWHISPER_STATIC is set, wwwhisper serves static html resources
# needed for login and for the admin application (this is not needed
# if these resources are served directly by a frontend server).
WWWHISPER_STATIC = None
# Serve all wwwhisper resources from /wwwhisper/ prefix (/wwwhisper/auth/,
# /wwwhisper/admin/)
WWWHISPER_PATH_PREFIX = 'wwwhisper/'
# Static files are also served from /wwwhisper/ prefix.
import cdn_container
STATIC_URL = cdn_container.CDN_CONTAINER + '/' + 'wwwhisper/'

import os
import sys

TESTING = sys.argv[1:2] == ['test']

if TESTING:
    from test_site_settings import *
else:
    from site_settings import *


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#        'LOCATION': 'unique-snowflake'
    }
}

if DEBUG:
    INTERNAL_IPS = ('127.0.0.1',)

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
# Site-Url from frontend server is validated by wwwhisper (checked
# against a list of aliases that are stored in the DB) and set in the
# X-Forwarded-Host. Host header is not used.
ALLOWED_HOSTS = ['*']

MIDDLEWARE_CLASSES = (
    #'wwwhisper_service.profile.ProfileMiddleware',
    # Must go before CommonMiddleware, to set a correct url to which
    # CommonMiddleware redirects.
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'wwwhisper_auth.middleware.SetSiteMiddleware',
    'wwwhisper_auth.middleware.SiteUrlMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Must be placed before session middleware to alter session cookies.
    'wwwhisper_auth.middleware.ProtectCookiesMiddleware',
    'wwwhisper_auth.middleware.SecuringHeadersMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

# Don't use just sessionid, to avoid collision with apps protected by wwwhisper.
SESSION_COOKIE_NAME = 'wwwhisper-sessionid'
CSRF_COOKIE_NAME = 'wwwhisper-csrftoken'

# Make session cookie valid only until a browser closes.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

ROOT_URLCONF = 'wwwhisper_service.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wwwhisper_service.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django_browserid',
    'wwwhisper_auth',
    'wwwhisper_admin'
)

if DEBUG:
    INSTALLED_APPS += ('debug_toolbar',)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates'),
)

AUTH_USER_MODEL = 'wwwhisper_auth.User'

AUTHENTICATION_BACKENDS = (
    'wwwhisper_auth.backend.BrowserIDBackend',
)

BROWSERID_VERIFICATION_URL = 'https://verifier.login.persona.org/verify'

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: "/admin/api/users/%s/" % u.username,
}

handler = 'logging.StreamHandler' if not TESTING \
    else 'django.utils.log.NullHandler'
level = 'INFO' if not DEBUG else 'DEBUG'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
            },
        # See http://docs.python.org/2/library/logging.html#logrecord-attributes
        'simple': {
            'format': '%(levelname)s %(name)s %(message)s'
            },
        },
    'handlers': {
        'console':{
            'level': level,
            'class': handler,
            'formatter': 'simple'
            },
        },
    'loggers': {
        'django_browserid': {
            'handlers': ['console'],
            'propagate': True,
            'level': level,
            },
        'wwwhisper_service': {
            'handlers': ['console'],
            'propagate': True,
            'level': level,
            },
        'wwwhisper_auth': {
            'handlers': ['console'],
            'propagate': True,
            'level': level,
            },
        'wwwhisper_admin': {
            'handlers': ['console'],
            'propagate': True,
            'level': level,
            },
        'django.request': {
            'handlers': ['console'],
            'propagate': True,
            'level': level,
            },
        'django.db': {
            'handlers': ['console'],
            'propagate': True,
            'level': level,
            },
        }
    }

if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY environment variable not set')

########NEW FILE########
__FILENAME__ = test_site_settings
print "Using testing configuration."

SECRET_KEY = 'RVh*fxg-hH2vJaTxbmXOvYn@iasPr5yKSE=tLckE5!fzEKj@NU'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/wwwhisper_test_db',
    }
}

WWWHISPER_PATH_PREFIX = ''

########NEW FILE########
__FILENAME__ = urls
# wwwhisper - web access control.
# Copyright (C) 2012, 2013, 2014 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf import settings
from wwwhisper_auth.assets import Asset, HtmlFileView, JsFileView

import logging

logger = logging.getLogger(__name__)

def _add_suffix(suffix):
    return r'^%s%s' % (settings.WWWHISPER_PATH_PREFIX, suffix)

def _url(path, *args):
    return url(_add_suffix(path), *args)

urlpatterns = patterns(
    '',
    _url(r'auth/api/', include('wwwhisper_auth.urls')),
    _url(r'admin/api/', include('wwwhisper_admin.urls')),
    )

if settings.WWWHISPER_STATIC is not None:
    logger.debug('wwwhisper configured to serve static files.')
    admin = Asset(settings.WWWHISPER_STATIC, 'admin', 'index.html')
    overlay = Asset(settings.WWWHISPER_STATIC, 'auth', 'overlay.html')
    iframe = Asset(settings.WWWHISPER_STATIC, 'auth', 'iframe.js')
    logout = Asset(settings.WWWHISPER_STATIC, 'auth', 'logout.html')
    goodbye = Asset(settings.WWWHISPER_STATIC, 'auth', 'goodbye.html')

    urlpatterns += patterns(
        '',
        _url('admin/$', HtmlFileView.as_view(asset=admin)),
        _url('auth/overlay.html$', HtmlFileView.as_view(asset=overlay)),
        _url('auth/iframe.js$', JsFileView.as_view(asset=iframe)),
        _url('auth/logout/$', HtmlFileView.as_view(asset=logout)),
        _url('auth/logout.html$', HtmlFileView.as_view(asset=logout)),
        _url('auth/goodbye.html$', HtmlFileView.as_view(asset=goodbye)),
        )


########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for service project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wwwhisper_service.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
# Apply WSGI middleware here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
