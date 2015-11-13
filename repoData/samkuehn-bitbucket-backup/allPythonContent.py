__FILENAME__ = backup
#!/usr/bin/env python

import bitbucket
import os
import argparse
from getpass import getpass
import sys
import datetime
try:
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import HTTPError, URLError


_verbose = False
_quiet = False


def debug(message, output_no_verbose=False):
    """
    Outputs a message to stdout taking into account the options verbose/quiet.
    """
    global _quiet, _verbose
    if not _quiet and (output_no_verbose or _verbose):
        print("{0} - {1}".format(datetime.datetime.now(), message))


def exit(message, code=1):
    """
    Forces script termination using C based error codes.
    By default, it uses error 1 (EPERM - Operation not permitted)
    """
    global _quiet
    if not _quiet and message and len(message) > 0:
        sys.stderr.write("%s (%s)\n" % (message, code))
    sys.exit(code)


def exec_cmd(command):
    """
    Executes an external command taking into account errors and logging.
    """
    global _verbose
    debug("Executing command: %s" % command)
    if not _verbose:
        command = "%s > /dev/null 2>&1" % command
    resp = os.system(command)
    if resp != 0:
        exit("Command [%s] failed" % command, resp)


def compress(repo, location):
    """
    Creates a TAR.GZ file with all contents cloned by this script.
    """
    os.chdir(location)
    debug("Compressing repositories in [%s]..." % (location), True)
    exec_cmd("tar -zcvf bitbucket-backup-%s-%s.tar.gz `ls -d *`" % (repo.get('owner'), datetime.datetime.now().strftime('%Y%m%d%H%m%s')))
    debug("Cleaning up...", True)
    for d in os.listdir(location):
        path = os.path.join(location, d)
        if os.path.isdir(path):
            exec_cmd("rm -rfv %s" % path)


def clone_repo(repo, backup_dir, http, password, mirror=False, with_wiki=False):
    global _quiet, _verbose
    scm = repo.get('scm')
    slug = repo.get('slug')
    username = repo.get('owner')
    command = None
    if scm == 'hg':
        if http:
            command = 'hg clone https://%s:%s@bitbucket.org/%s/%s' % (username, password, username, slug)
        else:
            command = 'hg clone ssh://hg@bitbucket.org/%s/%s' % (username, slug)
    if scm == 'git':
        git_command = 'git clone'
        if mirror:
            git_command = 'git clone --mirror'
        if http:
            command = "%s https://%s:%s@bitbucket.org/%s/%s.git" % (git_command, username, password, username, slug)
        else:
            command = "%s git@bitbucket.org:%s/%s.git" % (git_command, username, slug)
    if not command:
        exit("could not build command (scm [%s] not recognized?)" % scm)
    debug("Cloning %s..." % repo.get('name'))
    exec_cmd("%s %s" % (command, backup_dir))
    if with_wiki and repo.get('has_wiki'):
        debug("Cloning %s's Wiki..." % repo.get('name'))
        exec_cmd("%s/wiki %s_wiki" % (command, backup_dir))


def update_repo(repo, backup_dir, with_wiki=False):
    scm = repo.get('scm')
    command = None
    os.chdir(backup_dir)
    if scm == 'hg':
        command = 'hg pull -u'
    if scm == 'git':
        command = 'git remote update'
    if not command:
        return
    if not command:
        exit("could not build command (scm [%s] not recognized?)" % scm)
    debug("Updating %s..." % repo.get('name'))
    exec_cmd(command)
    wiki_dir = "%s_wiki" % backup_dir
    if with_wiki and repo.get('has_wiki') and os.path.isdir(wiki_dir):
        os.chdir(wiki_dir)
        debug("Updating %s's Wiki..." % repo.get('name'))
        exec_cmd(command)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Usage: %prog [options] ")
    parser.add_argument("-u", "--username", dest="username", help="Bitbucket username")
    parser.add_argument("-p", "--password", dest="password", help="Bitbucket password")
    parser.add_argument("-t", "--team", dest="team", help="Bitbucket team")
    parser.add_argument("-l", "--location", dest="location", help="Local backup location")
    parser.add_argument("-v", "--verbose", action='store_true', dest="verbose", help="Verbose output of all cloning commands")
    parser.add_argument("-q", "--quiet", action='store_true', dest="quiet", help="No output to stdout")
    parser.add_argument("-c", "--compress", action='store_true', dest="compress", help="Creates a compressed file with all cloned repositories (cleans up location directory)")
    parser.add_argument('--mirror', action='store_true', help="Clone just bare repositories with git clone --mirror (git only)")
    parser.add_argument('--with-wiki', dest="with_wiki", action='store_true', help="Includes wiki")
    parser.add_argument('--http', action='store_true', help="Fetch via https instead of SSH")
    parser.add_argument('--skip-password', dest="skip_password", action='store_true', help="Ignores password prompting if no password is provided (for public repositories)")
    args = parser.parse_args()
    username = args.username
    password = args.password
    owner = args.team if args.team else username
    location = args.location
    _quiet = args.quiet
    _verbose = args.verbose
    _mirror = args.mirror
    _with_wiki = args.with_wiki
    if _quiet:
        _verbose = False  # override in case both are selected
    http = args.http
    if not password:
        if not args.skip_password:
            password = getpass(prompt='Enter your bitbucket password: ')
    if not username or not location:
        parser.error('Please supply a username and backup location (-u <username> -l <backup location>)')

    # ok to proceed
    try:
        bb = bitbucket.BitBucket(username, password, _verbose)
        user = bb.user(owner)
        repos = user.repositories()
        if not repos:
            print("No repositories found. Are you sure you provided the correct password")
        for repo in repos:
            debug("Backing up [%s]..." % repo.get("name"), True)
            backup_dir = os.path.join(location, repo.get("slug"))
            if not os.path.isdir(backup_dir):
                clone_repo(repo, backup_dir, http, password, mirror=_mirror, with_wiki=_with_wiki)
            else:
                debug("Repository [%s] already in place, just updating..." % repo.get("name"))
                update_repo(repo, backup_dir, with_wiki=_with_wiki)
        if args.compress:
            compress(repo, location)
        debug("Finished!", True)
    except HTTPError as err:
        if err.code == 401:
            exit("Unauthorized! Check your credentials and try again.", 22)  # EINVAL - Invalid argument
        else:
            exit("Connection Error! Bitbucket returned HTTP error [%s]." % err.code)
    except URLError as e:
        exit("Unable to reach Bitbucket: %s." % e.reason, 101)  # ENETUNREACH - Network is unreachable
    except (KeyboardInterrupt, SystemExit):
        exit("Operation cancelled. There might be inconsistent data in location directory.", 0)
    except:
        if not _quiet:
            import traceback
            traceback.print_exc()
        exit("Unknown error.", 11)  # EAGAIN - Try again

########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Bitbucket API wrapper.  Written to be somewhat like py-github:

https://github.com/dustin/py-github

"""

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
from functools import wraps
import datetime
import time
import base64

try:
    import json
except ImportError:
    import simplejson as json

__all__ = ['AuthenticationRequired', 'to_datetime', 'BitBucket']

api_toplevel = 'https://api.bitbucket.org/'
api_base = '%s1.0/' % api_toplevel


class AuthenticationRequired(Exception):
    pass


def requires_authentication(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        username = self.bb.username if hasattr(self, 'bb') else self.username
        password = self.bb.password if hasattr(self, 'bb') else self.password
        if not all((username, password)):
            raise AuthenticationRequired("%s requires authentication" % method.__name__)
        return method(self, *args, **kwargs)
    return wrapper


def smart_encode(**kwargs):
    """Urlencode's provided keyword arguments.  If any kwargs are None, it does
    not include those."""
    args = dict(kwargs)
    for k, v in args.items():
        if v is None:
            del args[k]
    if not args:
        return ''
    return urlencode(args)


def to_datetime(timestring):
    """Convert one of the bitbucket API's timestamps to a datetime object."""
    format = '%Y-%m-%d %H:%M:%S'
    timestring = timestring.split('+')[0].strip()
    return datetime.datetime(*time.strptime(timestring, format)[:7])


class BitBucket(object):

    """Main bitbucket class.  Use an instantiated version of this class
    to make calls against the REST API."""

    def __init__(self, username='', password='', verbose=False):
        self.username = username
        self.password = password
        self.verbose = verbose

    def build_request(self, url, method="GET", data=None):
        if not all((self.username, self.password)):
            return Request(url)
        auth = '%s:%s' % (self.username, self.password)
        auth = {'Authorization': 'Basic %s' % (base64.b64encode(auth.encode("utf_8")).decode("utf_8").strip())}
        request = Request(url, data, auth)
        request.get_method = lambda: method
        return request

    def load_url(self, url, method="GET", data=None):
        if self.verbose:
            print("Sending request to: [{0}]".format(url))
        request = self.build_request(url, method=method, data=data)
        result = urlopen(request).read()
        if self.verbose:
            print("Response data: [{0}]".format(result))
        return result

    def user(self, username):
        return User(self, username)

    def repository(self, username, slug):
        return Repository(self, username, slug)

    @requires_authentication
    def emails(self):
        """Returns a list of configured email addresses for the authenticated user."""
        url = api_base + 'emails/'
        return json.loads(self.load_url(url))

    @requires_authentication
    def create_repo(self, repo_data):
        url = api_base + 'repositories/'
        return json.loads(self.load_url(url, method="POST", data=urlencode(repo_data)))

    def __repr__(self):
        extra = ''
        if all((self.username, self.password)):
            extra = ' (auth: %s)' % self.username
        return '<BitBucket API%s>' % extra


class User(object):

    """API encapsulation for user related bitbucket queries."""

    def __init__(self, bb, username):
        self.bb = bb
        self.username = username

    def repository(self, slug):
        return Repository(self.bb, self.username, slug)

    def repositories(self):
        user_data = self.get()
        return user_data['repositories']

    def events(self, start=None, limit=None):
        query = smart_encode(start=start, limit=limit)
        url = api_base + 'users/%s/events/' % self.username
        if query:
            url += '?%s' % query
        return json.loads(self.bb.load_url(url))

    def get(self):
        url = api_base + 'users/%s/' % self.username
        return json.loads(self.bb.load_url(url).decode('utf-8'))

    def __repr__(self):
        return '<User: %s>' % self.username


class Repository(object):

    def __init__(self, bb, username, slug):
        self.bb = bb
        self.username = username
        self.slug = slug
        self.base_url = api_base + 'repositories/%s/%s/' % (self.username, self.slug)

    def get(self):
        return json.loads(self.bb.load_url(self.base_url).decode('utf-8'))

    def changeset(self, revision):
        """Get one changeset from a repos."""
        url = self.base_url + 'changesets/%s/' % (revision)
        return json.loads(self.bb.load_url(url))

    def changesets(self, limit=None):
        """Get information about changesets on a repository."""
        url = self.base_url + 'changesets/'
        query = smart_encode(limit=limit)
        if query:
            url += '?%s' % query
        return json.loads(self.bb.load_url(url))

    def tags(self):
        """Get a list of tags for a repository."""
        url = self.base_url + 'tags/'
        return json.loads(self.bb.load_url(url))

    def branches(self):
        """Get a list of branches for a repository."""
        url = self.base_url + 'branches/'
        return json.loads(self.bb.load_url(url))

    def issue(self, number):
        return Issue(self.bb, self.username, self.slug, number)

    def issues(self, start=None, limit=None):
        url = self.base_url + 'issues/'
        query = smart_encode(start=start, limit=limit)
        if query:
            url += '?%s' % query
        return json.loads(self.bb.load_url(url))

    def events(self):
        url = self.base_url + 'events/'
        return json.loads(self.bb.load_url(url))

    def followers(self):
        url = self.base_url + 'followers/'
        return json.loads(self.bb.load_url(url))

    @requires_authentication
    def save(self, repo_data):
        url = self.base_url
        return json.loads(self.bb.load_url(url, method="PUT", data=urlencode(repo_data)))

    def __repr__(self):
        return '<Repository: %s\'s %s>' % (self.username, self.slug)


class Issue(object):

    def __init__(self, bb, username, slug, number):
        self.bb = bb
        self.username = username
        self.slug = slug
        self.number = number
        self.base_url = api_base + 'repositories/%s/%s/issues/%s/' % (username, slug, number)

    def get(self):
        return json.loads(self.bb.load_url(self.base_url).decode('utf-8'))

    def followers(self):
        url = self.base_url + 'followers/'
        return json.loads(self.bb.load_url(url))

    def __repr__(self):
        return '<Issue #%s on %s\'s %s>' % (self.number, self.username, self.slug)

########NEW FILE########
