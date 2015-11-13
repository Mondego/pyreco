__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = fpcli
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2008, Mickaël Guérin <kael@crocobox.org>
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University of California, Berkeley nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
Friendpaste
=======

Paste your code to Friendpaste' services like friendpaste.com

The last paste Id is saved in ~/.friednpaste or $APPDATA\_friendpaste
in order to use the -u flag to update it.

Copy to clipboard code (copy_url) taken from LodgeIt shell script (lodgeit.pocoo.org)
"""

import httplib
import os
import re
import socket
import sys

import json

FRIENDPASTE_SERVER = os.environ.get("FRIENDPASTE_SERVER", "friendpaste.com")
DEFAULT_LANG = os.environ.get("FRIENDPASTE_DEFAULT_LANG", "text")

build_url_withrev = lambda (base_url, nb_revision): ('%s?rev=%s' %
        (base_url, nb_revision))
if os.name == 'nt' and 'APPDATA' in os.environ:
    IDFILE_PATH = os.path.expandvars(r'$APPDATA\_friendpaste')
else:
    IDFILE_PATH = os.path.expanduser('~/.friendpaste')

def handle_errors(f):
    """
    decorator to drop the exceptions
    """
    def _temp(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (httplib.HTTPException, socket.error, socket.herror, socket.gaierror), e:
            print >> sys.stderr, 'HTTP error: %s' % e
        except Exception, e:
            print >> sys.stderr, 'Error while decoding response: %s' % e
        return None
    return _temp

@handle_errors
def save_last_snippet_id(paste_id):
    fd = file(IDFILE_PATH, 'w')
    fd.write(paste_id)
    fd.close

@handle_errors
def read_last_snippet_id():
    fd = file(IDFILE_PATH, 'r')
    paste_id = fd.read()
    fd.close
    return paste_id

def copy_url(url):
    """Copy the url into the clipboard."""
    if sys.platform == 'darwin':
        url = re.escape(url)
        os.system(r"echo %s | pbcopy" % url)
        return True

    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(url)
        win32clipboard.CloseClipboard()
        return True
    except ImportError:
        try:
            if os.environ.get('DISPLAY'):
                import pygtk
                pygtk.require('2.0')
                import gtk
                import gobject
                gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(url)
                gobject.idle_add(gtk.main_quit)
                gtk.main()
                return True
        except:
            pass
    return False
@handle_errors
def get_languages():
    c = httplib.HTTPConnection(FRIENDPASTE_SERVER)
    c.request('GET','/_all_languages', None, {'Accept': 'application/json'})
    languages = json.load(c.getresponse())
    c.close()
    return languages

@handle_errors
def paste(title, snippet, language, paste_id=None):
    if language not in [l for l, d in get_languages()]:
        raise Exception("Language '%s' unavailable" % language)
    paste_data = {'title': title, 'snippet': snippet, 'language': language}
    if paste_id:
        import re
        m = re.compile(r'(.*/)?(?P<paste_id>[a-zA-Z0-9]+)(\?rev=.*)?').match(paste_id)
        if m:
            paste_id = m.group('paste_id')
        else:
            raise Exception('invalid Id while updating snippet')
    c = httplib.HTTPConnection(FRIENDPASTE_SERVER)
    if paste_id:
        # update a paste
        c.request('PUT','/%s' % paste_id, json.dumps(paste_data),
                {'Accept': 'application/json',
                    'Content-Type': 'application/json'})
    else:
        # new paste
        c.request('POST','/', json.dumps(paste_data),
                {'Accept': 'application/json',
                    'Content-Type': 'application/json'})
    resp = json.load(c.getresponse())
    c.close()
    return resp

def main():
    # parse command line
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--languages', action='store_true',
            dest='print_languages',
            help='print the list of supported languages')
    parser.add_option('-t', '--title', action='store',
            dest="title",
            default='', help='title')
    parser.add_option('-l', '--language', action='store',
            dest="language",
            default=DEFAULT_LANG, help='language used for syntax coloration')
    parser.add_option('-i', '--update-id', action='store',
            dest="paste_id",
            default=None, help='update the snippet with this id')
    parser.add_option('-u', '--update-last', action='store_true',
            dest="update_last",
            default=False, help='update your last snippet')
    (options, args) = parser.parse_args()

    if len(args) > 1:
        print >> sys.stderr, 'Too many parameters'
        sys.exit(1)

    if options.print_languages:
        languages = get_languages()
        for language, description in languages:
            print "\t%12s   %s" % (language, description)
        sys.exit(0)

    # create a new paste
    if args:
        fd = file(args[0], 'r')
    else:
        fd = sys.stdin
    data = fd.read().strip()
    fd.close()

    if not data:
        print >> sys.stderr, 'Error: empty snippet'
        sys.exit(1)

    paste_id = None
    if options.paste_id:
        paste_id = options.paste_id
    elif options.update_last:
        paste_id = read_last_snippet_id()

    resp = paste(options.title, data, options.language, paste_id=paste_id)
    if not resp:
        sys.exit(1)

    if resp['ok']:
        if options.paste_id:
            print '%s  ->  %s' % (resp['url'],
                    build_url_withrev((resp['url'],resp['nb_revision'])))
        else:
            print '%s' % (resp['url'])
        copy_url(resp['url'])
        save_last_snippet_id(resp['id'])
    else:
        print >> sys.stderr, 'An error occured: %s' % resp['reason']

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = profiles
from glob import glob
import os

__doc__ = """
profiles documentation
"""

TITLE = """
%(title)s
%(sep)s

"""

def gendoc():
    """generate profiles documentations"""
    dirname = os.path.abspath(os.path.dirname(__file__))
    dirname = os.path.dirname(dirname)
    docs = os.path.join(dirname, "docs", "profiles.rst")
    match = os.path.join(dirname, "profiles", "*.vim")
    with open(docs, "w") as docs:
        docs.write("=======================\n")
        docs.write("Profiles\n")
        docs.write("=======================\n\n")
        docs.write(".. automodule:: ohmyvim.profiles\n\n")
        for filename in glob(match):
            with open(filename) as fd:
                title, _ = os.path.splitext(os.path.basename(filename))
                docs.write(TITLE % dict(title=title, sep="=" * len(title)))
                data = fd.readlines()
                for i, line in enumerate(data):
                    if line.startswith('"'):
                        docs.write(line.strip('" '))
                    break
                docs.write("\n.. literalinclude:: %s\n" % filename)
                docs.write("   lines: %s\n" % (i + 1,))

if __name__ == "__main__":
    gendoc()


########NEW FILE########
__FILENAME__ = scripts
from os.path import join
from os.path import isdir
from os.path import isfile
from os.path import basename
from ConfigObject import ConfigObject
from urllib import urlopen
from subprocess import Popen
from subprocess import PIPE
from glob import glob
import pkg_resources
import webbrowser
import shutil
import json
import sys
import os

VIMRC = '''
" Added by oh-my-vim

" Change the default leader
" let mapleader = ","

" Skip upgrade of oh-my-vim itself during upgrades
" let g:ohmyvim_skip_upgrade=1

" Use :OhMyVim profiles to list all available profiles with a description
" let profiles = %(profiles)r
let profiles = ['defaults']

" Path to oh-my-vim binary (take care of it if you are using a virtualenv)
let g:ohmyvim="%(binary)s"

" load oh-my-vim
source %(ohmyvim)s

" End of oh-my-vim required stuff

" Put your custom stuff bellow

'''

GVIMRC = '''
" uncomment this to set a font
" set guifont="Menlo Regular:h11"

" no bell
set noerrorbells

" window size
if exists(':win')
    win 150 50
endif

" remove menu and toolbar. see help guioptions
set guioptions=aegirlt
'''

GIT_URL = "https://github.com/gawel/oh-my-vim.git"

TOOLS = join(os.path.dirname(__file__), '..', 'tools')


class Bundle(object):

    def __init__(self, manager, dirname):
        self.manager = manager
        self.dirname = dirname
        self.name = basename(dirname)
        self.use_git = isdir(join(dirname, '.git'))
        self.use_hg = isdir(join(dirname, '.hg'))
        self.valid = self.use_hg or self.use_git
        self.home = os.environ['HOME']

    def log(self, *args):
        self.manager.log(*args)

    @property
    def themes(self):
        themes = []
        if isdir(join(self.dirname, 'colors')):
            themes = os.listdir(join(self.dirname, 'colors'))
            themes = [t[:-4] for t in themes]
        return themes

    @property
    def remote(self):
        os.chdir(self.dirname)
        if self.use_git:
            p = Popen(['git', 'remote', '-v'], stdout=PIPE)
            p.wait()
            remote = p.stdout.read().split('\n')[0]
            remote = remote.split('\t')[1].split(' ')[0]
            return remote
        elif self.use_hg:
            p = Popen(['hg', 'path'], stdout=PIPE)
            p.wait()
            remote = p.stdout.read().split('\n')[0]
            remote = remote.split(' = ')[1].strip()
            return remote

    @property
    def dependencies(self):
        if isfile(join(self.dirname, 'requires.txt')):
            with open(join(self.dirname, 'requires.txt')) as fd:
                return set([d.strip() for d in fd.readlines() if d.strip()])
        return set()

    @classmethod
    def resolve_url(self, url):
        config = get_config()

        url = url.strip()
        url = config.bundles.get(url.lower(), url)
        url = config.vimscripts.get(url.lower(), url)
        return url

    @classmethod
    def install(cls, manager, args, url):
        url = cls.resolve_url(url)

        use_hg = False
        use_git = False

        if url.startswith('hg+'):
            use_hg = True
            url = url[3:]
        elif url.startswith('git+'):
            use_git = True
            url = url[4:]
        elif len(url.split('/')) == 2:
            url = 'https://github.com/%s/%s.git' % tuple(url.split('/'))
        elif '://github.com' in url and not url.endswith('.git'):
            url = url.replace('http://', 'https://').rstrip() + '.git'

        if url.endswith('.git'):
            use_git = True
            use_hg = False

        dirname = cmd = None

        if use_git:
            name = basename(url)[:-4]
            dirname = join(manager.runtime, name)
            cmd = ['git', 'clone', '-q', '-b', 'master', url, dirname]
        elif use_hg:
            name = basename(url.strip('/'))
            dirname = join(manager.runtime, name)
            cmd = ['hg', 'clone', '-q', url, dirname]
        else:
            manager.log('%s is not a valid url', url)

        if dirname and isdir(dirname):
            manager.log('%s already installed.', name)
        elif cmd:
            manager.log('Installing %s...', name)
            Popen(cmd).wait()
            b = cls(manager, dirname)
            if args.full:
                b.post_install()
            return b

    def upgrade(self, args):
        self.log('Upgrading %s...', self.name)
        if self.name.lower() == 'oh-my-vim':
            self.self_upgrade()
        else:
            os.chdir(self.dirname)
            if self.use_git:
                p = Popen(['git', 'pull', '-qn', 'origin', 'master'],
                           stdout=PIPE)
                p.wait()
            elif self.use_hg:
                p = Popen(['hg', 'pull', '-qu'], stdout=PIPE)
                p.wait()
            if args.full:
                self.post_install()

    def get_pip(self):
        install_dir = join(self.home, '.oh-my-vim/')
        if os.path.isdir(install_dir):
            bin_dir = join(install_dir, 'env', 'bin')
        else:
            bin_dir = os.path.dirname(sys.executable)
            pip = join(bin_dir, 'pip')
        pip = join(bin_dir, 'pip')
        if os.path.isfile(pip):
            return pip
        return ''

    def post_install(self):
        script = join(TOOLS, 'post_install', '%s.sh' % self.name)
        if not isfile(script):
            script = join(self.dirname, 'post_install.sh')
        env = os.environ
        if 'PIP' not in env:
            env['PIP'] = self.get_pip()
        env['GIT_DIR'] = self.dirname
        env['NAME'] = self.name
        env['VIM_ENV'] = join(self.home, '.vim', 'ohmyvim', 'env.vim')
        if isfile(script):
            self.log('Running post install script...')
            os.chdir(self.dirname)
            p = Popen([script], env=env)
            p.wait()

    def self_upgrade(self):
        """Try to upgrade itself"""
        branch = "master"
        with open(join(self.home, '.vimrc')) as fd:
            for line in fd:
                line = line.strip()
                if not line.startswith('"'):
                    if 'ohmyvim_skip_upgrade' in line and '=' in line:
                        if int(line.split('=', 1)[1].strip()):
                            line = line.replace('let', '').strip()
                            self.log('Skipping. vimrc contains %s' % line)
                            return
                    elif 'ohmyvim_version' in line:
                        branch = line.split('=').strip()

        if 'BUILDOUT_ORIGINAL_PYTHONPATH' in os.environ:
            self.log('Update your buildout')
            return False

        pip = self.get_pip()

        if pip:
            install_dir = join(self.home, '.oh-my-vim/')
            if os.path.isdir(install_dir):
                bin_dir = join(install_dir, 'env', 'bin')
            else:
                bin_dir = os.path.dirname(sys.executable)
                install_dir = None

            cmd = [pip, 'install', '-q',
                   '--src=%s' % join(self.home, '.vim', 'bundle')]

            if install_dir:
                bin_dir = join(install_dir, 'bin')
                cmd.append(('--install-option='
                            '--script-dir==%s') % bin_dir)

            cmd.extend(['-e',
                        'git+%s@%s#egg=oh-my-vim' % (self.remote, branch)])

            if self.home not in cmd[0]:
                cmd.insert(0, 'sudo')

            self.log('Upgrading to %s' % branch)
            if '__ohmyvim_test__' in os.environ:
                self.log(' '.join(cmd))
                return True
            else:
                p = Popen(cmd)
                p.wait()
                return True

        os.chdir(self.dirname)
        p = Popen(['git', 'pull', '-qn', 'origin', branch], stdout=PIPE)
        p.wait()

        self.log("! Dont know how to upgrade oh-my-vim's python package...")
        self.log('! You may try to update it manualy')


class Manager(object):

    dependencies = {
        'vim-pathogen': 'https://github.com/tpope/vim-pathogen.git',
        'oh-my-vim': GIT_URL,
      }

    def __init__(self):
        self.output = []

        self.home = os.environ['HOME']
        self.vim = join(self.home, '.vim')
        self.vimrc = join(self.home, '.vimrc')
        self.gvimrc = join(self.home, '.gvimrc')
        self.runtime = join(self.vim, 'bundle')
        self.autoload = join(self.vim, 'autoload')
        self.ohmyvim = join(self.vim, 'ohmyvim')

        for dirname in (self.runtime, self.autoload,
                        self.ohmyvim):
            if not isdir(dirname):
                os.makedirs(dirname)

        for name, url in self.dependencies.items():
            if not isdir(join(self.runtime, name)):
                self.log('Installing %s...' % name)
                Popen(['git', 'clone', '-q', url,
                       join(self.runtime, name)]).wait()

        if not isfile(join(self.ohmyvim, 'theme.vim')):
            with open(join(self.ohmyvim, 'theme.vim'), 'w') as fd:
                fd.write('')

        if not isfile(join(self.ohmyvim, 'env.vim')):
            with open(join(self.ohmyvim, 'env.vim'), 'w') as fd:
                fd.write('set path+=$HOME/.oh-my-vim/bin\n')

        ohmyvim = join(self.ohmyvim, 'ohmyvim.vim')
        with open(ohmyvim, 'w') as fd:
            fd.write('source %s\n' % join(self.ohmyvim, 'env.vim'))
            fd.write('source %s\n' % join(self.runtime, 'vim-pathogen',
                                               'autoload', 'pathogen.vim'))
            fd.write('call pathogen#incubate()\n')
            fd.write('source %s\n' % join(self.ohmyvim, 'theme.vim'))
            fd.write('source %s\n' % join(self.runtime, 'oh-my-vim',
                                          'plugin', 'ohmyvim.vim'))

        if 'VIRTUAL_ENV' in os.environ:
            binary = join(os.getenv('VIRTUAL_ENV'), 'bin', 'oh-my-vim')
        else:
            binary = 'oh-my-vim'

        need_update = False
        if not isfile(self.vimrc):
            need_update = True
        else:
            with open(self.vimrc) as fd:
                if ohmyvim not in fd.read():
                    need_update = True

        if need_update:
            if isfile(self.vimrc):
                with open(self.vimrc, 'r') as fd:
                    data = fd.read()
                with open(join(self.ohmyvim, 'vimrc.bak'), 'w') as fd:
                    fd.write(data)
            else:
                data = ''
            kw = dict(
                    ohmyvim=ohmyvim,
                    binary=binary,
                    profiles=self.profiles(None, as_list=True))
            with open(self.vimrc, 'w') as fd:
                fd.write(VIMRC % kw)
                fd.write(data)

        if not isfile(self.gvimrc):
            with open(self.gvimrc, 'w') as fd:
                fd.write(GVIMRC)

    def log(self, value, *args):
        if args:
            value = value % args
        self.output.append(value)
        sys.stdout.write(value + '\n')
        sys.stdout.flush()

    def get_bundles(self):
        bundles = []
        for plugin in os.listdir(self.runtime):
            bundle = Bundle(self, join(self.runtime, plugin))
            if bundle.valid:
                bundles.append(bundle)
        return bundles

    def search(self, args):
        terms = [t.strip() for t in args.term if t.strip()]
        if args.theme_only:
            terms.insert(0, 'colorschemes')
        if not terms:
            terms = ['language%3AVimL']
        terms = '%20'.join(terms)
        url = ("https://github.com/search?"
               "langOverride=&repo=&start_value=1&"
               "type=Repositories&language=VimL&q=") + terms
        if '__ohmyvim_test__' not in os.environ:
            webbrowser.open_new(url)
        else:
            self.log(url)

    def info(self, args):
        url = Bundle.resolve_url(args.bundle)
        if url.endswith('.git'):
            url = url[:-4]
        url += '#readme'
        if '__ohmyvim_test__' not in os.environ:
            webbrowser.open_new(url)
        else:
            self.log(url)

    def list(self, args):
        for b in self.get_bundles():
            if args.raw:
                self.log(b.name)
            else:
                if args.urls:
                    if b.name not in self.dependencies:
                        if b.use_git:
                            self.log('git+%s', b.remote)
                        elif b.use_hg:
                            self.log('hg+%s', b.remote)
                else:
                    self.log('* %s (%s)', b.name, b.remote)
        if args.all:
            config = get_config()
            printed = set()
            bundles = config.bundles.items() + config.vimscripts.items()
            for name, url in bundles:
                if name not in printed:
                    printed.add(name)
                    if args.raw:
                        self.log(name)
                    else:
                        self.log('- %s (%s)', name, url)

    def install(self, args):
        config = get_config()
        requires = join(TOOLS, 'requires')
        if args.raw:
            if args.dist:
                for require in glob(join(requires, '*.txt')):
                    name = basename(require)[:-4]
                    if name != 'gawel':
                        self.log(name)
            else:
                for name in sorted(config.bundles.keys()):
                    self.log(name)
                for name in sorted(config.vimscripts.keys()):
                    self.log(name)
        else:
            if args.dist:
                if not isinstance(args.url, list):
                    args.url = []
                args.url.append(join(requires, '%s.txt' % args.dist))

            dependencies = set()
            for url in args.url:
                if url.endswith('.txt'):
                    if isfile(url):
                        with open(url) as fd:
                            for dep in fd:
                                dep = dep.strip()
                                if dep and not dep.startswith('#'):
                                    dependencies.add(dep)
                    elif url.startswith('http'):
                        fd = urlopen(url)
                        for dep in fd.readlines():
                            dep = dep.strip()
                            if dep and not dep.startswith('#'):
                                dependencies.add(dep)
                else:
                    b = Bundle.install(self, args, url)
                    if b:
                        dependencies = dependencies.union(b.dependencies)
            if dependencies:
                self.log('Processing dependencies...')
                for url in dependencies:
                    if url.strip():
                        b = Bundle.install(self, args, url.strip())

    def upgrade(self, args):
        for b in self.get_bundles():
            if b.name in args.bundle or len(args.bundle) == 0:
                b.upgrade(args)

    def remove(self, args):
        if args.bundle:
            bundles = [b.lower() for b in args.bundle]
            for b in self.get_bundles():
                if b.name.lower() in bundles:
                    if b.name in self.dependencies:
                        self.log("Don't remove %s!", b.name)
                    self.log('Removing %s...', b.name)
                    shutil.rmtree(b.dirname)

    def theme(self, args):
        theme = args.theme
        if theme:
            for b in self.get_bundles():
                if theme in b.themes:
                    self.log('Activate %s theme...', theme)
                    with open(join(self.ohmyvim, 'theme.vim'), 'w') as fd:
                        fd.write(':colo %s\n' % theme)
        else:
            for b in self.get_bundles():
                themes = b.themes
                if themes:
                    if args.raw:
                        for theme in themes:
                            self.log(theme)
                    else:
                        self.log('* %s (%s)', b.name, b.remote)
                        self.log('\t- %s', ', '.join(themes))

    def profiles(self, args, as_list=False):
        profiles = join(self.runtime, 'oh-my-vim', 'profiles')
        profiles = glob(join(profiles, '*.vim'))

        if as_list:
            return sorted([basename(name)[:-4] for name in profiles])

        for profile in sorted(profiles):
            name = basename(profile)[:-4]
            if not name.startswith('.'):
                desc = ''
                with open(profile) as fd:
                    line = fd.readline()
                    if line.startswith('"'):
                        desc += line.strip(' "\n')
                if desc:
                    self.log('* %s - %s', name, desc)
                else:
                    self.log('* %s', name)

    def version(self, args):
        version = pkg_resources.get_distribution('oh-my-vim').version
        self.log(version)


def get_config():
    filename = join(os.path.dirname(__file__), 'config.ini')
    return ConfigObject(filename=filename)


def main(*args):
    import argparse

    manager = Manager()

    parser = argparse.ArgumentParser(description='Oh my Vim!')
    subparsers = parser.add_subparsers(help='sub-command help')

    p = subparsers.add_parser('search')
    p.add_argument('-t', '--theme-only', action='store_true', default=False)
    p.add_argument('term', nargs='*', default='')
    p.set_defaults(action=manager.search)

    p = subparsers.add_parser('info',
                              help='try to open the web page of the bundle')
    p.add_argument('bundle', default='')
    p.set_defaults(action=manager.info)

    p = subparsers.add_parser('list')
    p.add_argument('--raw', action='store_true', default=False)
    p.add_argument('-a', '--all', action='store_true', default=False)
    p.add_argument('-u', '--urls', action='store_true', default=False)
    p.set_defaults(action=manager.list)

    p = subparsers.add_parser('install', help='install a script or bundle')
    p.add_argument('--raw', action='store_true', default=False)
    p.add_argument('-f', '--full', default=None,
                         help="also install required softwares and binaries")
    p.add_argument('-d', '--dist', default=None,
                                   help="install a distribution")
    p.add_argument('url', nargs='*', default='')
    p.set_defaults(action=manager.install)

    p = subparsers.add_parser('upgrade', help='upgrade bundles')
    p.add_argument('-f', '--full', default=None,
                         help="also install required softwares and binaries")
    p.add_argument('bundle', nargs='*', default='')
    p.set_defaults(action=manager.upgrade)

    p = subparsers.add_parser('remove', help='remove a bundle')
    p.add_argument('bundle', nargs='*', default='')
    p.set_defaults(action=manager.remove)

    p = subparsers.add_parser('theme', help='list or activate a theme')
    p.add_argument('--raw', action='store_true', default=False)
    p.add_argument('theme', nargs='?', default='')
    p.set_defaults(action=manager.theme)

    p = subparsers.add_parser('profiles', help='print all available profiles')
    p.set_defaults(action=manager.profiles)

    p = subparsers.add_parser('version', help='print version')
    p.set_defaults(action=manager.version)

    if args:
        args = parser.parse_args(args)
    else:
        args = parser.parse_args()

    args.action(args)

    if '__ohmyvim_test__' in os.environ:
        return manager.output


def update_registry():
    vimscripts = {}
    links = 'https://api.github.com/users/vim-scripts/repos; rel="next"'
    while 'rel="next"' in links:
        url = links.split(';')[0].strip(' <>')
        print('Loading %s...' % url)
        resp = urlopen(url)
        repos = json.loads(resp.read())
        vimscripts.update([(r['name'], r['clone_url']) for r in repos])
        links = resp.headers.get('Link', '')

    config = get_config()
    config.vimscripts = vimscripts
    config.write()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import unittest2 as unittest
from ohmyvim.scripts import main
from os.path import isdir
from os.path import isfile
from os.path import join
import subprocess
import tempfile
import shutil
import os


class Mixin(object):

    def setUpMixin(self):
        self.addCleanup(os.chdir, os.getcwd())
        self.wd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.wd)
        os.environ['HOME'] = self.wd

    def assertIsFile(self, *args):
        filename = join(self.wd, *args)
        if not isfile(filename):
            print(os.listdir(os.path.dirname(filename)))
            self.assertTrue(isfile(filename), filename)

    def assertIsDir(self, *args):
        dirname = join(self.wd, *args)
        if not isdir(dirname):
            print(os.listdir(os.path.dirname(dirname)))
            self.assertTrue(isfile(dirname), dirname)

    def assertResp(self, resp):
        self.assertTrue(len(resp) > 0, resp)


class TestScript(unittest.TestCase, Mixin):

    def setUp(self):
        self.setUpMixin()
        os.environ['__ohmyvim_test__'] = '1'
        self.requires = join(self.wd, 'deps.txt')
        with open(self.requires, 'w') as fd:
            fd.write('https://github.com/vim-scripts/github-theme.git\n\n')

    def main(self, args):
        return main(*args.split(' '))

    def test_ohmyvim(self):
        self.main('install')
        self.assertIn(self.wd, os.path.expanduser('~/'))
        self.assertIsFile('.vim/ohmyvim/ohmyvim.vim')
        self.assertIsDir('.vim/bundle/oh-my-vim')

        url = self.main('search')[0]
        self.assertIn('language%3AVimL', url)

        url = self.main('search -t')[0]
        self.assertIn('colorschemes', url)

        url = self.main('search -t mytheme')[0]
        self.assertIn('colorschemes', url)
        self.assertIn('mytheme', url)

        resp = self.main('profiles')
        self.assertIn('* defaults - some defaults settings', resp)

        resp = self.main('install --raw')
        self.assertIn('github-theme', resp)

        self.main('install')
        resp = self.main('install github-theme')
        self.assertResp(resp)

        resp = self.main(
                'install https://github.com/vim-scripts/github-theme.git')
        self.assertIn('github-theme already installed.', resp)

        resp = self.main('install %s' % self.requires)
        self.assertIn('github-theme already installed.', resp)

        resp = self.main(
                'install scrooloose/nerdtree')
        self.assertIn('Installing nerdtree...', resp)

        resp = self.main(
                'install hg+https://bitbucket.org/sjl/gundo.vim')
        self.assertIn('Installing gundo.vim...', resp)

        resp = self.main('list --raw')
        self.assertIn('github-theme', resp)
        self.assertIn('gundo.vim', resp)

        resp = self.main('list')
        self.assertIn(
           '* github-theme (https://github.com/vim-scripts/github-theme.git)',
           resp)

        resp = self.main('list -u')
        self.assertIn('git+https://github.com/vim-scripts/github-theme.git',
                      resp)

        resp = self.main('theme --raw')
        self.assertIn('github', resp)

        resp = self.main('theme')
        self.assertIn('\t- github', resp)

        resp = self.main('theme github')
        self.assertIn('Activate github theme...', resp)

        resp = self.main('remove')
        self.assertTrue(len(resp) == 0)

        resp = self.main('remove github-theme')
        self.assertNotIn('github-theme', resp)

        resp = self.main('upgrade oh-my-vim')
        self.assertIn('Upgrading oh-my-vim...', resp)

        resp = self.main('info vim-IPython')
        self.assertIn('https://github.com/vim-scripts/vim-ipython#readme',
                      resp)


class TestInstall(unittest.TestCase, Mixin):

    def setUp(self):
        self.setUpMixin()

        def setenv(key, value):
            os.environ[key] = value

        self.addCleanup(setenv, 'PYTHONPATH', os.environ['PYTHONPATH'])
        self.addCleanup(setenv, 'BUILDOUT_ORIGINAL_PYTHONPATH',
                                os.environ['BUILDOUT_ORIGINAL_PYTHONPATH'])
        os.environ['PYTHONPATH'] = ''
        del os.environ['BUILDOUT_ORIGINAL_PYTHONPATH']

    def test_install(self):
        script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'tools', 'install.sh')
        subprocess.Popen('sh %s' % script, shell=True).wait()
        self.assertIsFile('.oh-my-vim/env/bin/python')
        self.assertIsFile('.oh-my-vim/bin/oh-my-vim')
        subprocess.Popen(' '.join(
                       [os.path.join(self.wd, '.oh-my-vim/bin/oh-my-vim'),
                       'upgrade']),
                       shell=True).wait()

########NEW FILE########
__FILENAME__ = tmpl
# -*- coding: utf-8 -*-


########NEW FILE########
