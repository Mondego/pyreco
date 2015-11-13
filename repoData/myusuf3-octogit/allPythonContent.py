__FILENAME__ = cli
"""
octogit

this file contains all the helper cli commands for octogit

"""
import os
import re
import sys
import requests

from docopt import docopt
from clint import args
from clint.textui import colored, puts, indent

from .core import (get_issues, get_single_issue, create_repository,
                   close_issue, view_issue, create_issue, find_github_remote)
from .config import login, create_config, commit_changes, CONFIG_FILE


GIT_REPO_ENDPOINT = 'https://api.github.com/repos/%s/%s'

def version():
    from . import __version__
    return ".".join(str(x) for x in __version__)


def get_help():
    puts('{0}. version {1} by Mahdi Yusuf {2}'.format(
            colored.blue('octogit'),
            version(),
            colored.green('@myusuf3')))
    puts('{0}: http://github.com/myusuf3/octogit'.format(colored.yellow('source')))

    puts('\n{0}:'.format(colored.cyan('tentacles')))
    with indent(4):
        puts(colored.green('octogit login'))
        puts(colored.green("octogit create <repo> 'description'"))
        puts(colored.green("octogit create <repo> 'description' <organization>"))
        puts(colored.green('octogit issues [--assigned]'))
        puts(colored.green('octogit issues'))
        puts(colored.green("octogit issues create 'issue title' 'description'"))
        puts(colored.green('octogit issues <number>'))
        puts(colored.green('octogit issues <number> close'))
        puts(colored.green('octogit issues <number> view'))
        puts('\n')


def get_parent_repository(username_repo):
    username, repo = username_repo
    url = GIT_REPO_ENDPOINT % (username, repo)
    response = requests.get(url)
    data = response.json()
    try:
        parent = data['parent']['full_name']
        username_repo = parent.split('/')
    except KeyError:
        pass
    return username_repo


def get_username_and_repo(url):

    # matching origin of this type
    # http://www.github.com/myusuf3/delorean
    m = re.match("^.+?github.com/([a-zA-Z0-9_-]*)/([a-zA-Z0-9_-]*)\/?$", url)
    if m:
        return m.groups()
    else:
        # matching origin of this type
        # git@github.com:[/]myusuf3/delorean.git
        username_repo = url.split(':')[1].replace('.git', '').split('/')
        # Handle potential leading slash after :
        if username_repo[0] == '':
            username_repo = username_repo[1:]
        if len(username_repo) == 2:
            info = username_repo
        else:
            # matching url of this type
            # git://github.com/myusuf3/delorean.git
            username_repo = url.split('/')[3:]
            username_repo[1] = username_repo[1].replace('.git', '')
            info = username_repo
    parent_repo = get_parent_repository(info)
    return parent_repo


def begin():
    """
    Usage:
      octogit [subcommand] [arguments]
      octogit login | -l | --login [(username password)]
      octogit create <repo> [<description>] [<organization>]
      octogit (issues | -i | --issues) [--assigned | -a]
      octogit (issues | -i | --issues) create <issue-title> <description>
      octogit (issues | -i | --issues) <number> [close | view]
      octogit -v | --version
      octogit help | -h | --help

      """

    if os.path.exists(CONFIG_FILE):
        pass
    else:
        # create config file
        create_config()
        # commit changes
        commit_changes()

    arguments = docopt(begin.__doc__, help=None)

    if arguments['--version'] or arguments['-v']:
        puts(version())
        sys.exit(0)

    elif arguments['--help'] or arguments['-h'] or arguments['help']:
        get_help()
        sys.exit(0)

    elif arguments['create']:
        if arguments['<repo>'] == None:
            puts('{0}. {1}'.format(colored.blue('octogit'),
                colored.red('You need to pass both a project name and description')))

        else:
            project_name = arguments['<repo>']
            description = arguments['<description>'] or ''
            organization = arguments['<organization>'] or None
            create_repository(project_name, description, organization=organization)
            sys.exit()

    elif arguments['--issues'] or arguments['-i'] or arguments['issues']:
        url = find_github_remote()
        username, url = get_username_and_repo(url)
        if arguments['create']:
            if ['<issue-title>'] == None:
                puts('{0}. {1}'.format(colored.blue('octogit'),
                    colored.red('You need to pass an issue title')))
                sys.exit(-1)

            else:
                issue_name = arguments['<issue-title>']
                description = arguments['<description>']
                create_issue(username, url, issue_name, description)
                sys.exit(0)

        issue_number = arguments['<number>']

        if issue_number is not None:
            if issue_number.startswith('#'):
                issue_number = issue_number[1:]

            if arguments['close']:
                close_issue(username, url, issue_number)
                sys.exit(0)
            elif arguments['view']:
                view_issue(username, url, issue_number)
                sys.exit(0)
            elif arguments['--assigned']:
                get_issues(username, url, (arguments['-assigned'] or arguments['-a']))
                sys.exit(0)
            else:
                get_single_issue(username, url, issue_number)
                sys.exit(0)
        else:
                get_issues(username, url, False)
                sys.exit(0)

    elif arguments['--login'] or arguments['-l'] or arguments['login']:
        username = arguments['username'] or None
        if username is None:
            username = raw_input("Github username: ")
            if len(username) == 0:
                puts("{0}. {1}".format(
                        colored.blue("octogit"),
                        colored.red("Username was blank")))

        password = arguments['password'] or None
        if password is None:
            import getpass
            password = getpass.getpass("Password for %s: " % username)

        login(username, password)
    else:
        get_help()
        sys.exit(0)

########NEW FILE########
__FILENAME__ = config
import os
import sys
import ConfigParser

import requests
from clint.textui import colored, puts

try:
    import json
except ImportError:
    import simplejson as json  # NOQA

CONFIG_FILE = os.path.expanduser('~/.config/octogit/config.ini')
# ran the first time login in run
config = ConfigParser.ConfigParser()


def commit_changes():
    '''
    Write changes to the config file.
    '''
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


def create_config():
    if os.path.exists(CONFIG_FILE):
        pass
    else:
        os.makedirs(os.path.dirname(CONFIG_FILE))
        open(CONFIG_FILE, 'w').close()
        config.add_section('octogit')
        config.set('octogit', 'username', '')
        config.set('octogit', 'token', '')
        return config

def get_token():
    config.read(CONFIG_FILE)
    # Catch edgecase where user hasn't migrated to tokens
    try:
        return config.get('octogit', 'token')
    except ConfigParser.NoOptionError:
        if get_username() != "":
            puts(colored.green("We're just migrating your account from plaintext passwords to OAuth tokens"))
            login(get_username(), config.get('octogit', 'password'))
            config.remove_option('octogit', 'password')
            puts(colored.green("Pretty spiffy huh?"))
            return config.get('octogit', 'token')
        else:
            raise

def get_username():
    config.read(CONFIG_FILE)
    return config.get('octogit', 'username')

def get_headers(headers=()):
    defaults = {"Authorization": "token %s" % get_token()}
    defaults.update(headers)
    return defaults

def have_credentials():
    return get_username() != '' and get_token() != ''

def set_token(token):
    '''
    Given a config set the token attribute
    in the Octogit section.
    '''
    config.set('octogit', 'token', token)
    commit_changes()


def set_username(username):
    '''
    Given a config set the username attribute
    in the Octogit section.
    '''
    config.set('octogit', 'username', username)
    commit_changes()


def login(username, password):
    body = json.dumps({ "note": "octogit",
                        "note_url": "https://github.com/myusuf3/octogit",
                        "scopes": ["repo"]})
    r = requests.post('https://api.github.com/authorizations',
            auth=(username, password), data=body)
    if r.status_code == 201:
        puts(colored.green('You have successfully been authenticated with Github'))
    else:
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('Do you even have a Github account? Bad Credentials')))
        sys.exit(3)
    data = json.loads(r.content)
    token = data["token"]

    set_username(username)
    set_token(token)

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
octogit

This file contains stuff for github api
"""

import os
import io
import re
import sys
import subprocess
import webbrowser
import requests
from clint.textui import colored, puts, columns

from .config import get_username, get_headers, have_credentials

try:
    import json
except ImportError:
    import simplejson as json  # NOQA


ISSUES_ENDPOINT = 'https://api.github.com/repos/%s/%s/issues?page=%s'
CREATE_ISSUE_ENDPOINT = 'https://api.github.com/repos/%s/%s/issues'
SINGLE_ISSUE_ENDPOINT = 'https://api.github.com/repos/%s/%s/issues/%s'
ISSUES_PAGE = 'https://github.com/%s/%s/issues'
SINGLE_ISSUE_PAGE = 'https://github.com/%s/%s/issues/%s'

UPDATE_ISSUE = 'https://api.github.com/repos/%s/%s/issues/%s'


def valid_credentials():
    r = requests.get('https://api.github.com', headers=get_headers())
    if r.status_code == 200:
        return True
    else:
        return False


def push_to_master():
    cmd = ['git', 'push', '-u', 'origin', 'master']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()


def create_octogit_readme():
    with io.open('README.rst', 'w') as fp:
        fp.write(u"""========
Octogit
========

This repository has been created with Octogit.

.. image:: http://myusuf3.github.com/octogit/assets/img/readme_image.png

Author
======
Mahdi Yusuf (@myusuf3)
""")


def git_init(repo_name):
    cmd = ["git", "init", repo_name]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()


def git_add_remote(username, repo_name):
    url = "git@github.com:%s/%s.git" % (username, repo_name)
    cmd = ["git", "remote", "add", "origin", url]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()


def git_initial_commit():
    cmd = ["git", "commit", "-am", "this repository now with more tentacles care of octogit"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()


def git_add():
    cmd = ["git", "add", "README.rst"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()


def local_already(repo_name):
    # mkdir repo_name
    if os.path.exists('/'.join([os.getcwd(), repo_name])):
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('the repository already exists locally.')))
        return True
    else:
        return False


def create_local_repo(username, repo_name):
    # mkdir repo_name
    if os.path.exists('/'.join([os.getcwd(), repo_name])):
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('the repository already exists locally.')))
    else:
        os.makedirs('/'.join([os.getcwd(), repo_name]))
        # cd repo_name
        os.chdir('/'.join([os.getcwd(), repo_name]))
        #git init
        git_init(os.getcwd())
        # create readme
        create_octogit_readme()
        # add readme
        git_add()
        #initial commit
        git_initial_commit()
        # add remote
        git_add_remote(username, repo_name)
        # push to master
        push_to_master()
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.green('this is your moment of glory; Be a hero.')))


def close_issue(user, repo, number):
    if not have_credentials():
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('in order to create a repository, you need to login.')))
        sys.exit(-1)
    update_issue = UPDATE_ISSUE % (user, repo, number)
    post_dict = {'state': 'close'}
    r = requests.post(update_issue, headers=get_headers(), data=json.dumps(post_dict))
    if r.status_code == 200:
        puts('{0}.'.format(colored.red('closed')))
    else:
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red("You either aren't allowed to close repository or you need to login in silly.")))
        sys.exit(-1)


def view_issue(user, repo, number):
    """
    Displays the specified issue in a browser
    """

    github_view_url = SINGLE_ISSUE_PAGE % (user, repo, number)
    webbrowser.open(github_view_url)


def create_repository(project_name, description, organization=None):
    if not have_credentials():
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('in order to create a repository, you need to login.')))
        sys.exit(1)

    if local_already(project_name):
        sys.exit(1)
    post_dict = {'name': project_name, 'description': description, 'homepage': '', 'private': False, 'has_issues': True, 'has_wiki': True, 'has_downloads': True}
    if organization:
        post_url = 'https://api.github.com/orgs/{0}/repos'.format(organization)
    else:
        post_url = 'https://api.github.com/user/repos'
    r = requests.post(post_url, headers=get_headers(), data=json.dumps(post_dict))
    if r.status_code == 201:
        if organization:
            create_local_repo(organization, project_name)
        else:
            create_local_repo(get_username(), project_name)
    else:
        # Something went wrong
        post_response = json.loads(r.content)
        errors = post_response.get('errors')
        if errors and errors[0]['message'] == 'name already exists on this account':
            puts('{0}. {1}'.format(colored.blue('octogit'),
                colored.red('repository named this already exists on github')))
        else:
            puts('{0}. {1}'.format(colored.blue('octogit'),
                colored.red('something went wrong. perhaps you need to login?')))
            sys.exit(-1)


def find_github_remote():
    cmd = ["git", "remote", "-v"]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, sterr = proc.communicate()

    if not stdout:
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('You need to be inside a valid git repository.')))
        sys.exit(0)

    remotes = stdout.strip().split('\n')
    for line in remotes:
        name, url, _ = line.split()
        if 'github.com' in url and name == 'origin':
            return url
    else:
        puts(colored.red('This repository has no Github remotes'))
        sys.exit(0)


def description_clean(string):
    new_string = ''
    for line in string.split('\n'):
        if line.strip():
            new_string += line + '\n'
    return new_string


def get_single_issue(user, repo, number):
    url = SINGLE_ISSUE_ENDPOINT % (user, repo, number)
    github_single_url = SINGLE_ISSUE_PAGE % (user, repo, number)
    puts('link. {0} \n'.format(colored.green(github_single_url)))
    if valid_credentials():
        connect = requests.get(url, headers=get_headers())
    else:
        connect = requests.get(url)

    issue = json.loads(connect.content)
    width = [[colored.yellow('#'+str(issue['number'])), 5],]
    width.append([colored.red('('+ issue['user']['login']+')'), 15])
    puts(columns(*width))
    description = description_clean(issue['body'].encode('utf-8'))
    puts(description)


def get_issues(user, repo, assigned=None):
    github_issues_url = 'https://api.github.com/repos/%s/%s/issues' % (user, repo)

    params = None
    if assigned:
        params = {'assignee': user}

    link = requests.head(github_issues_url).headers.get('Link', '=1>; rel="last"')
    last = lambda url: int(re.compile('=(\d+)>; rel="last"$').search(url).group(1)) + 1

    for pagenum in xrange(1, last(link)):
        connect = requests.get(github_issues_url + '?page=%s' % pagenum, params=params)

        try:
            data = json.loads(connect.content)
        except ValueError:
            raise ValueError(connect.content)

        if not data:
            puts('{0}. {1}'.format(colored.blue('octogit'),
                colored.cyan('Looks like you are perfect welcome to the club.')))
            break

        elif 'message' in data:
            puts('{0}. {1}'.format(colored.blue('octogit'),
                                   colored.red(data['message'])))
            sys.exit(1)

        for issue in data:
            #skip pull requests
            if issue['pull_request']['html_url']:
                continue
            width = [[colored.yellow('#'+str(issue['number'])), 4],]
            if isinstance(issue['title'], unicode):
                issue['title'] = issue['title'].encode('utf-8')
            width.append([issue['title'], 80])
            width.append([colored.red('('+ issue['user']['login']+')'), None])
            print columns(*width)


def create_issue(user, repo, issue_name, description):
    if not have_credentials():
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('in order to create an issue, you need to login.')))
        sys.exit(1)

    post_url = CREATE_ISSUE_ENDPOINT % (user, repo)
    post_dict = {'title': issue_name, 'body': description}

    r = requests.post(post_url, headers=get_headers(), data=json.dumps(post_dict))
    if r.status_code == 201:
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('New issue created!')))
    else:
        puts('{0}. {1}'.format(colored.blue('octogit'),
            colored.red('something went wrong. perhaps you need to login?')))
        sys.exit(-1)

########NEW FILE########
__FILENAME__ = __main__
from . import cli
cli.begin()

########NEW FILE########
__FILENAME__ = cli
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import unittest

class SimpleTest(unittest.TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = config
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import unittest

class SimpleTest(unittest.TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = core
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import unittest
from octogit.core import get_single_issue

class UTF8Support(unittest.TestCase):

    def assertNotRaises(self, exception_type, called_func, kwargs):
        try:
            called_func(**kwargs)
        except Exception as e:
            if isinstance(e, exception_type):
                self.fail(e)
            else:
                pass

    def test_assert_not_raises_UnicodeEncodeError(self):
        self.assertNotRaises(UnicodeEncodeError, get_single_issue,
            kwargs={'user':'cesarFrias', 'repo':'pomodoro4linux',
            'number':2})


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
