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
    args.insert(0, 'buildout:accept-buildout-test-releases=true')

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
        if sys.version_info[:2] == (2, 4):
            setup_args['version'] = '0.6.32'
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
if not find_links and options.accept_buildout_test_releases:
    find_links = 'http://downloads.buildout.org/'
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
            if distv >= pkg_resources.parse_version('2dev'):
                continue
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
    requirement += '=='+version
else:
    requirement += '<2dev'

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

# If there isn't already a command in the args, add bootstrap
if not [a for a in args if '=' not in a]:
    args.append('bootstrap')


# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = bootstrap2
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

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

to_reload = False
try:
    import pkg_resources
    import setuptools
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    # XXX use a more permanent ez_setup.py URL when available.
    exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
                ).read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

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
        search_path=[setuptools_path])
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

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = bazaar
from mr.developer import common
import os
import subprocess

logger = common.logger


class BazaarError(common.WCError):
    pass


class BazaarWorkingCopy(common.BaseWorkingCopy):
    def bzr_branch(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        if os.path.exists(path):
            self.output((logger.info,
                'Skipped branching existing package %r.' % name))
            return
        self.output((logger.info, 'Branched %r with bazaar.' % name))
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['bzr', 'branch', '--quiet', url, path],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise BazaarError(
                'bzr branch for %r failed.\n%s' % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def bzr_pull(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        self.output((logger.info, 'Updated %r with bazaar.' % name))
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(['bzr', 'pull', url], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise BazaarError(
                'bzr pull for %r failed.\n%s' % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info,
                    'Skipped checkout of existing package %r.' % name))
            else:
                raise BazaarError(
                    'Source URL for existing package %r differs. '
                    'Expected %r.' % (name, self.source['url']))
        else:
            return self.bzr_branch(**kwargs)

    def matches(self):
        name = self.source['name']
        path = self.source['path']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['bzr', 'info'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise BazaarError(
                'bzr info for %r failed.\n%s' % (name, stderr))
        return (self.source['url'] in stdout.split())

    def status(self, **kwargs):
        path = self.source['path']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['bzr', 'status'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        status = stdout and 'dirty' or 'clean'
        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def update(self, **kwargs):
        name = self.source['name']
        if not self.matches():
            raise BazaarError(
                "Can't update package %r because its URL doesn't match." %
                name)
        if self.status() != 'clean' and not kwargs.get('force', False):
            raise BazaarError(
                "Can't update package %r because it's dirty." % name)
        return self.bzr_pull(**kwargs)

########NEW FILE########
__FILENAME__ = common
try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import logging
import os
import pkg_resources
import platform
try:
    import queue
except ImportError:
    import Queue as queue
import re
import subprocess
import sys
import threading


logger = logging.getLogger("mr.developer")


def print_stderr(s):
    sys.stderr.write(s)
    sys.stderr.write('\n')
    sys.stderr.flush()


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()

try:
    raw_input = raw_input
except NameError:
    raw_input = input


# shameless copy from
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(name_root):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    if platform.system() == 'Windows':
        # http://www.voidspace.org.uk/python/articles/command_line.shtml#pathext
        pathext = os.environ['PATHEXT']
        # example: ['.py', '.pyc', '.pyo', '.pyw', '.COM', '.EXE', '.BAT', '.CMD']
        names = [name_root + ext for ext in pathext.split(';')]
    else:
        names = [name_root]

    for name in names:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, name)
            if is_exe(exe_file):
                return exe_file

    return None


def version_sorted(inp, *args, **kwargs):
    """
    Sorts components versions, it means that numeric parts of version
    treats as numeric and string as string.

    Eg.: version-1-0-1 < version-1-0-2 < version-1-0-10
    """
    num_reg = re.compile(r'([0-9]+)')

    def int_str(val):
        try:
            return int(val)
        except ValueError:
            return val

    def split_item(item):
        return tuple([int_str(j) for j in num_reg.split(item)])

    def join_item(item):
        return ''.join([str(j) for j in item])

    output = [split_item(i) for i in inp]
    return [join_item(i) for i in sorted(output, *args, **kwargs)]


def memoize(f, _marker=[]):
    def g(*args, **kwargs):
        name = '_memoize_%s' % f.__name__
        value = getattr(args[0], name, _marker)
        if value is _marker:
            value = f(*args, **kwargs)
            setattr(args[0], name, value)
        return value
    return g


class WCError(Exception):
    """ A working copy error. """


class BaseWorkingCopy(object):
    def __init__(self, source):
        self._output = []
        self.output = self._output.append
        self.source = source

    def should_update(self, **kwargs):
        offline = kwargs.get('offline', False)
        if offline:
            return False
        update = self.source.get('update', kwargs.get('update', False))
        if not isinstance(update, bool):
            if update.lower() in ('true', 'yes'):
                update = True
            elif update.lower() in ('false', 'no'):
                update = False
            else:
                raise ValueError("Unknown value for 'update': %s" % update)
        return update


def yesno(question, default=True, all=True):
    if default:
        question = "%s [Yes/no" % question
        answers = {
            False: ('n', 'no'),
            True: ('', 'y', 'yes'),
        }
    else:
        question = "%s [yes/No" % question
        answers = {
            False: ('', 'n', 'no'),
            True: ('y', 'yes'),
        }
    if all:
        answers['all'] = ('a', 'all')
        question = "%s/all] " % question
    else:
        question = "%s] " % question
    while 1:
        answer = raw_input(question).lower()
        for option in answers:
            if answer in answers[option]:
                return option
        if all:
            print_stderr("You have to answer with y, yes, n, no, a or all.")
        else:
            print_stderr("You have to answer with y, yes, n or no.")


main_lock = input_lock = output_lock = threading.RLock()


def worker(working_copies, the_queue):
    while True:
        if working_copies.errors:
            return
        try:
            wc, action, kwargs = the_queue.get_nowait()
        except queue.Empty:
            return
        try:
            output = action(**kwargs)
        except WCError:
            output_lock.acquire()
            for lvl, msg in wc._output:
                lvl(msg)
            for l in sys.exc_info()[1].args[0].split('\n'):
                logger.error(l)
            working_copies.errors = True
            output_lock.release()
        else:
            output_lock.acquire()
            for lvl, msg in wc._output:
                lvl(msg)
            if kwargs.get('verbose', False) and output is not None and output.strip():
                print(output)
            output_lock.release()


_workingcopytypes = None


def get_workingcopytypes():
    global _workingcopytypes
    if _workingcopytypes is not None:
        return _workingcopytypes
    group = 'mr.developer.workingcopytypes'
    _workingcopytypes = {}
    addons = {}
    for entrypoint in pkg_resources.iter_entry_points(group=group):
        key = entrypoint.name
        workingcopytype = entrypoint.load()
        if entrypoint.dist.project_name == 'mr.developer':
            _workingcopytypes[key] = workingcopytype
        else:
            if key in addons:
                logger.error("There already is a working copy type addon registered for '%s'.", key)
                sys.exit(1)
            logger.info("Overwriting '%s' with addon from '%s'.", key, entrypoint.dist.project_name)
            addons[key] = workingcopytype
    _workingcopytypes.update(addons)
    return _workingcopytypes


class WorkingCopies(object):
    def __init__(self, sources, threads=5):
        self.sources = sources
        self.threads = threads
        self.errors = False
        self.workingcopytypes = get_workingcopytypes()

    def process(self, the_queue):
        if self.threads < 2:
            worker(self, the_queue)
        else:
            if sys.version_info < (2, 6):
                # work around a race condition in subprocess
                _old_subprocess_cleanup = subprocess._cleanup

                def _cleanup():
                    pass

                subprocess._cleanup = _cleanup

            threads = []

            for i in range(self.threads):
                thread = threading.Thread(target=worker, args=(self, the_queue))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()
            if sys.version_info < (2, 6):
                subprocess._cleanup = _old_subprocess_cleanup
                subprocess._cleanup()

        if self.errors:
            logger.error("There have been errors, see messages above.")
            sys.exit(1)

    def checkout(self, packages, **kwargs):
        the_queue = queue.Queue()
        if 'update' in kwargs:
            if isinstance(kwargs['update'], bool):
                pass
            elif kwargs['update'].lower() in ('true', 'yes', 'on', 'force'):
                if kwargs['update'].lower() == 'force':
                    kwargs['force'] = True
                kwargs['update'] = True
            elif kwargs['update'].lower() in ('false', 'no', 'off'):
                kwargs['update'] = False
            else:
                logger.error("Unknown value '%s' for always-checkout option." % kwargs['update'])
                sys.exit(1)
        kwargs.setdefault('submodules', 'always')
        if kwargs['submodules'] in ['always', 'never', 'checkout']:
            pass
        else:
            logger.error("Unknown value '%s' for update-git-submodules option." % kwargs['submodules'])
            sys.exit(1)
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                logger.error("Checkout failed. No source defined for '%s'." % name)
                sys.exit(1)
            source = self.sources[name]
            kind = source['kind']
            wc = self.workingcopytypes.get(kind)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % kind)
                sys.exit(1)
            update = wc.should_update(**kwargs)
            if not source.exists():
                pass
            elif os.path.islink(source['path']):
                logger.info("Skipped update of linked '%s'." % name)
                continue
            elif update and wc.status() != 'clean' and not kw.get('force', False):
                print_stderr("The package '%s' is dirty." % name)
                answer = yesno("Do you want to update it anyway?", default=False, all=True)
                if answer:
                    kw['force'] = True
                    if answer == 'all':
                        kwargs['force'] = True
                else:
                    logger.info("Skipped update of '%s'." % name)
                    continue
            logger.info("Queued '%s' for checkout.", name)
            the_queue.put_nowait((wc, wc.checkout, kw))
        self.process(the_queue)

    def matches(self, source):
        name = source['name']
        if name not in self.sources:
            logger.error("Checkout failed. No source defined for '%s'." % name)
            sys.exit(1)
        source = self.sources[name]
        try:
            kind = source['kind']
            wc = self.workingcopytypes.get(kind)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % kind)
                sys.exit(1)
            return wc.matches()
        except WCError:
            for l in sys.exc_info()[1].args[0].split('\n'):
                logger.error(l)
            sys.exit(1)

    def status(self, source, **kwargs):
        name = source['name']
        if name not in self.sources:
            logger.error("Status failed. No source defined for '%s'." % name)
            sys.exit(1)
        source = self.sources[name]
        try:
            kind = source['kind']
            wc = self.workingcopytypes.get(kind)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % kind)
                sys.exit(1)
            return wc.status(**kwargs)
        except WCError:
            for l in sys.exc_info()[1].args[0].split('\n'):
                logger.error(l)
            sys.exit(1)

    def update(self, packages, **kwargs):
        the_queue = queue.Queue()
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                continue
            source = self.sources[name]
            kind = source['kind']
            wc = self.workingcopytypes.get(kind)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % kind)
                sys.exit(1)
            if wc.status() != 'clean' and not kw.get('force', False):
                print_stderr("The package '%s' is dirty." % name)
                answer = yesno("Do you want to update it anyway?", default=False, all=True)
                if answer:
                    kw['force'] = True
                    if answer == 'all':
                        kwargs['force'] = True
                else:
                    logger.info("Skipped update of '%s'." % name)
                    continue
            logger.info("Queued '%s' for update.", name)
            the_queue.put_nowait((wc, wc.update, kw))
        self.process(the_queue)


def parse_buildout_args(args):
    settings = dict(
        config_file='buildout.cfg',
        verbosity=0,
        options=[],
        windows_restart=False,
        user_defaults=True,
        debug=False,
    )
    options = []
    version = pkg_resources.get_distribution("zc.buildout").version
    if tuple(version.split('.')[:2]) <= ('1', '4'):
        option_str = 'vqhWUoOnNDA'
    else:
        option_str = 'vqhWUoOnNDAs'
    while args:
        if args[0][0] == '-':
            op = orig_op = args.pop(0)
            op = op[1:]
            while op and op[0] in option_str:
                if op[0] == 'v':
                    settings['verbosity'] = settings['verbosity'] + 10
                elif op[0] == 'q':
                    settings['verbosity'] = settings['verbosity'] - 10
                elif op[0] == 'W':
                    settings['windows_restart'] = True
                elif op[0] == 'U':
                    settings['user_defaults'] = False
                elif op[0] == 'o':
                    options.append(('buildout', 'offline', 'true'))
                elif op[0] == 'O':
                    options.append(('buildout', 'offline', 'false'))
                elif op[0] == 'n':
                    options.append(('buildout', 'newest', 'true'))
                elif op[0] == 'N':
                    options.append(('buildout', 'newest', 'false'))
                elif op[0] == 'D':
                    settings['debug'] = True
                elif op[0] == 's':
                    settings['ignore_broken_dash_s'] = True
                else:
                    raise ValueError("Unkown option '%s'." % op[0])
                op = op[1:]

            if op[:1] in ('c', 't'):
                op_ = op[:1]
                op = op[1:]

                if op_ == 'c':
                    if op:
                        settings['config_file'] = op
                    else:
                        if args:
                            settings['config_file'] = args.pop(0)
                        else:
                            raise ValueError("No file name specified for option", orig_op)
                elif op_ == 't':
                    try:
                        int(args.pop(0))
                    except IndexError:
                        raise ValueError("No timeout value specified for option", orig_op)
                    except ValueError:
                        raise ValueError("No timeout value must be numeric", orig_op)
                    settings['socket_timeout'] = op
            elif op:
                if orig_op == '--help':
                    return 'help'
                raise ValueError("Invalid option", '-' + op[0])
        elif '=' in args[0]:
            option, value = args.pop(0).split('=', 1)
            if len(option.split(':')) != 2:
                raise ValueError('Invalid option:', option)
            section, option = option.split(':')
            options.append((section.strip(), option.strip(), value.strip()))
        else:
            # We've run out of command-line options and option assignnemnts
            # The rest should be commands, so we'll stop here
            break
    return options, settings, args


class Rewrite(object):
    _matcher = re.compile("(?P<option>^\w+) (?P<operator>[~=]{1,2}) (?P<value>.+)$")

    def _iter_prog_lines(self, prog):
        for line in prog.split('\n'):
            line = line.strip()
            if line:
                yield line

    def __init__(self, prog):
        self.rewrites = {}
        lines = self._iter_prog_lines(prog)
        for line in lines:
            match = self._matcher.match(line)
            matchdict = match.groupdict()
            option = matchdict['option']
            if option in ('name', 'path'):
                raise ValueError("Option '%s' not allowed in rewrite:\n%s" % (option, prog))
            operator = matchdict['operator']
            rewrites = self.rewrites.setdefault(option, [])
            if operator == '~':
                try:
                    substitute = advance_iterator(lines)
                except StopIteration:
                    raise ValueError("Missing substitution for option '%s' in rewrite:\n%s" % (option, prog))
                rewrites.append(
                    (operator, re.compile(matchdict['value']), substitute))
            elif operator == '=':
                rewrites.append(
                    (operator, matchdict['value']))
            elif operator == '~=':
                rewrites.append(
                    (operator, re.compile(matchdict['value'])))

    def __call__(self, source):
        for option, operations in self.rewrites.items():
            for operation in operations:
                operator = operation[0]
                if operator == '~':
                    if operation[1].search(source.get(option, '')) is None:
                        return
                elif operator == '=':
                    if operation[1] != source.get(option, ''):
                        return
                elif operator == '~=':
                    if operation[1].search(source.get(option, '')) is None:
                        return
        for option, operations in self.rewrites.items():
            for operation in operations:
                operator = operation[0]
                if operator == '~':
                    orig = source.get(option, '')
                    source[option] = operation[1].sub(operation[2], orig)
                    if source[option] != orig:
                        logger.debug("Rewrote option '%s' from '%s' to '%s'." % (option, orig, source[option]))


class LegacyRewrite(Rewrite):
    def __init__(self, prefix, substitution):
        Rewrite.__init__(self, "url ~ ^%s\n%s" % (prefix, substitution))


class Config(object):
    def read_config(self, path):
        config = RawConfigParser()
        config.optionxform = lambda s: s
        config.read(path)
        return config

    def check_invalid_sections(self, path, name):
        config = self.read_config(path)
        for section in ('buildout', 'develop'):
            if config.has_section(section):
                raise ValueError(
                    "The '%s' section is not allowed in '%s'" %
                    (section, name))

    def __init__(self, buildout_dir):
        global_cfg_name = os.path.join('~', '.buildout', 'mr.developer.cfg')
        options_cfg_name = '.mr.developer-options.cfg'
        self.global_cfg_path = os.path.expanduser(global_cfg_name)
        self.options_cfg_path = os.path.join(buildout_dir, options_cfg_name)
        self.cfg_path = os.path.join(buildout_dir, '.mr.developer.cfg')
        self.check_invalid_sections(self.global_cfg_path, global_cfg_name)
        self.check_invalid_sections(self.options_cfg_path, options_cfg_name)
        self._config = self.read_config((
            self.global_cfg_path, self.options_cfg_path, self.cfg_path))
        self.develop = {}
        self.buildout_args = []
        self._legacy_rewrites = []
        self.rewrites = []
        self.threads = 5
        if self._config.has_section('develop'):
            for package, value in self._config.items('develop'):
                value = value.lower()
                if value == 'true':
                    self.develop[package] = True
                elif value == 'false':
                    self.develop[package] = False
                elif value == 'auto':
                    self.develop[package] = 'auto'
                else:
                    raise ValueError("Invalid value in 'develop' section of '%s'" % self.cfg_path)
        if self._config.has_option('buildout', 'args'):
            args = self._config.get('buildout', 'args').split("\n")
            for arg in args:
                arg = arg.strip()
                if arg.startswith("'") and arg.endswith("'"):
                    arg = arg[1:-1].replace("\\'", "'")
                elif arg.startswith('"') and arg.endswith('"'):
                    arg = arg[1:-1].replace('\\"', '"')
                self.buildout_args.append(arg)
        (self.buildout_options, self.buildout_settings, _) = \
            parse_buildout_args(self.buildout_args[1:])
        if self._config.has_option('mr.developer', 'rewrites'):
            for rewrite in self._config.get('mr.developer', 'rewrites').split('\n'):
                if not rewrite.strip():
                    continue
                rewrite_parts = rewrite.split()
                if len(rewrite_parts) != 2:
                    raise ValueError("Invalid legacy rewrite '%s'. Each rewrite must have two parts separated by a space." % rewrite)
                self._legacy_rewrites.append(rewrite_parts)
                self.rewrites.append(LegacyRewrite(*rewrite_parts))
        if self._config.has_option('mr.developer', 'threads'):
            try:
                threads = int(self._config.get('mr.developer', 'threads'))
                if threads < 1:
                    raise ValueError
                self.threads = threads
            except ValueError:
                logger.warning(
                    "Invalid value '%s' for 'threads' option, must be a positive number. Using default value of %s.",
                    self._config.get('mr.developer', 'threads'),
                    self.threads)
        if self._config.has_section('rewrites'):
            for name, rewrite in self._config.items('rewrites'):
                self.rewrites.append(Rewrite(rewrite))

    def save(self):
        self._config.remove_section('develop')
        self._config.add_section('develop')
        for package in sorted(self.develop):
            state = self.develop[package]
            if state is 'auto':
                self._config.set('develop', package, 'auto')
            elif state is True:
                self._config.set('develop', package, 'true')
            elif state is False:
                self._config.set('develop', package, 'false')

        if not self._config.has_section('buildout'):
            self._config.add_section('buildout')
        options, settings, args = parse_buildout_args(self.buildout_args[1:])
        # don't store the options when a command was in there
        if not len(args):
            self._config.set('buildout', 'args', "\n".join(repr(x) for x in self.buildout_args))

        if not self._config.has_section('mr.developer'):
            self._config.add_section('mr.developer')
        self._config.set('mr.developer', 'rewrites', "\n".join(" ".join(x) for x in self._legacy_rewrites))

        self._config.write(open(self.cfg_path, "w"))

########NEW FILE########
__FILENAME__ = cvs
from mr.developer import common
import os
import re
import subprocess

logger = common.logger

RE_ROOT = re.compile(r'(:pserver:)([a-zA-Z0-9]*)(@.*)')


class CVSError(common.WCError):
    pass


def build_cvs_command(command, name, url, tag='', cvs_root='', tag_file=None):
    """
    Create CVS commands.

    Examples::

        >>> build_cvs_command('checkout', 'package.name', 'python/package.name')
        ['cvs', 'checkout', '-P', '-f', '-d', 'package.name', 'python/package.name']
        >>> build_cvs_command('update', 'package.name', 'python/package.name')
        ['cvs', 'update', '-P', '-f', '-d']
        >>> build_cvs_command('checkout', 'package.name', 'python/package.name', tag='package_name_0-1-0')
        ['cvs', 'checkout', '-P', '-r', 'package_name_0-1-0', '-d', 'package.name', 'python/package.name']
        >>> build_cvs_command('update', 'package.name', 'python/package.name', tag='package_name_0-1-0')
        ['cvs', 'update', '-P', '-r', 'package_name_0-1-0', '-d']
        >>> build_cvs_command('checkout', 'package.name', 'python/package.name', cvs_root=':pserver:user@127.0.0.1:/repos')
        ['cvs', '-d', ':pserver:user@127.0.0.1:/repos', 'checkout', '-P', '-f', '-d', 'package.name', 'python/package.name']
        >>> build_cvs_command('status', 'package.name', 'python/package.name')
        ['cvs', '-q', '-n', 'update']
        >>> build_cvs_command('tags', 'package.name', 'python/package.name', tag_file='setup.py')
        ['cvs', '-Q', 'log', 'setup.py']

    """
    if command == 'status':
        return ['cvs', '-q', '-n', 'update']

    cmd = ['cvs']
    if cvs_root:
        cmd.extend(['-d', cvs_root])

    if command == 'tags':
        cmd.extend(['-Q', 'log'])
        if not tag_file:
            tag_file = 'setup.py'
        cmd.append(tag_file)
    else:
        cmd.extend([command, '-P'])
        if tag:
            cmd.extend(['-r', tag])
        else:
            cmd.append('-f')
        cmd.append('-d')
        if command == 'checkout':
            cmd.extend([name, url])
    return cmd


class CVSWorkingCopy(common.BaseWorkingCopy):

    def __init__(self, source):
        super(CVSWorkingCopy, self).__init__(source)
        if self.source.get('newest_tag', '').lower() in ['1', 'true', 'yes']:
            self.source['tag'] = self._get_newest_tag()

    def cvs_command(self, command, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        tag = self.source.get('tag')

        cvs_root = self.source.get('cvs_root')
        tag_file = self.source.get('tag_file')
        self.output((logger.info, 'Running %s %r from CVS.' % (command, name)))
        cmd = build_cvs_command(command, name, url, tag, cvs_root, tag_file)

        # because CVS can not work on absolute paths, we must execute cvs commands
        # in destination or in parent directory of destination
        old_cwd = os.getcwd()
        if command == 'checkout':
            path = os.path.dirname(path)
        os.chdir(path)

        try:
            cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = cmd.communicate()
        finally:
            os.chdir(old_cwd)

        if cmd.returncode != 0:
            raise CVSError('CVS %s for %r failed.\n%s' % (command, name, stderr))
        if command == 'tags':
            return self._format_tags_list(stdout)
        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info, 'Skipped checkout of existing package %r.' % name))
            else:
                raise CVSError(
                    'Source URL for existing package %r differs. '
                    'Expected %r.' % (name, self.source['url']))
        else:
            return self.cvs_command('checkout', **kwargs)

    def matches(self):
        def normalize_root(text):
            """
            Removes username from CVS Root path.
            """
            return RE_ROOT.sub(r'\1\3', text)

        path = self.source['path']

        repo_file = os.path.join(path, 'CVS', 'Repository')
        if not os.path.exists(repo_file):
            raise CVSError('Can not find CVS/Repository file in %s.' % path)
        repo = open(repo_file).read().strip()

        cvs_root = self.source.get('cvs_root')
        if cvs_root:
            root_file = os.path.join(path, 'CVS', 'Root')
            root = open(root_file).read().strip()
            if normalize_root(cvs_root) != normalize_root(root):
                return False

        return (self.source['url'] == repo)

    def status(self, **kwargs):
        path = self.source['path']

        # packages before checkout is clean
        if not os.path.exists(path):
            return 'clean'

        status = 'clean'
        stdout = self.cvs_command('status', verbose=True)
        for line in stdout.split('\n'):
            if not line or line.endswith('.egg-info'):
                continue
            if line[0] == 'C':
                # there is file with conflict
                status = 'conflict'
                break
            if line[0] in ('M', '?', 'A', 'R'):
                # some files are localy modified
                status = 'modified'

        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def update(self, **kwargs):
        name = self.source['name']
        if not self.matches():
            raise CVSError(
                "Can't update package %r, because its URL doesn't match." %
                name)
        if self.status() != 'clean' and not kwargs.get('force', False):
            raise CVSError(
                "Can't update package %r, because it's dirty." % name)
        return self.cvs_command('update', **kwargs)

    def _format_tags_list(self, stdout):
        output = []
        tag_line_re = re.compile(r'([^: ]+): [0-9.]+')
        list_started = False
        for line in stdout.split('\n'):
            if list_started:
                matched = tag_line_re.match(line.strip())
                if matched:
                    output.append(matched.groups()[0])
                else:
                    list_started = False
            elif 'symbolic names:' in line:
                list_started = True
        return list(set(output))

    def _get_newest_tag(self):
        try:
            tags = self.cvs_command('tags')
        except OSError:
            return None
        mask = self.source.get('newest_tag_prefix', self.source.get('newest_tag_mask', ''))
        if mask:
            tags = [t for t in tags if t.startswith(mask)]
        tags = common.version_sorted(tags, reverse=True)
        if not tags:
            return None
        newest_tag = tags[0]
        self.output((logger.info, 'Picked newest tag for %r from CVS: %r.' % (self.source['name'], newest_tag)))
        return newest_tag

########NEW FILE########
__FILENAME__ = darcs
from mr.developer import common
import os
import subprocess


logger = common.logger


class DarcsError(common.WCError):
    pass


class DarcsWorkingCopy(common.BaseWorkingCopy):
    def darcs_checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        if os.path.exists(path):
            self.output((logger.info, "Skipped getting of existing package '%s'." % name))
            return
        self.output((logger.info, "Getting '%s' with darcs." % name))
        cmd = ["darcs", "get", "--quiet", "--lazy", url, path]
        cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise DarcsError("darcs get for '%s' failed.\n%s" % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def darcs_update(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        self.output((logger.info, "Updating '%s' with darcs." % name))
        cmd = subprocess.Popen(["darcs", "pull", "-a"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise DarcsError("darcs pull for '%s' failed.\n%s" % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info, "Skipped checkout of existing package '%s'." % name))
            else:
                raise DarcsError("Checkout URL for existing package '%s' differs. Expected '%s'." % (name, self.source['url']))
        else:
            return self.darcs_checkout(**kwargs)

    def _darcs_related_repositories(self):
        name = self.source['name']
        path = self.source['path']
        repos = os.path.join(path, '_darcs', 'prefs', 'repos')
        if os.path.exists(repos):
            for line in open(repos).readlines():
                yield line.strip()
        else:
            cmd = subprocess.Popen(["darcs", "show", "repo"],
                                   cwd=path,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            stdout, stderr = cmd.communicate()
            if cmd.returncode != 0:
                self.output((logger.error, "darcs info for '%s' failed.\n%s" % (name, stderr)))
                return

            lines = stdout.splitlines()
            for line in lines:
                k, v = line.split(':', 1)
                k = k.strip()
                v = v.strip()
                if k == 'Default Remote':
                    yield v
                elif k == 'Cache':
                    for cache in v.split(', '):
                        if cache.startswith('repo:'):
                            yield cache[5:]

    def matches(self):
        return self.source['url'] in self._darcs_related_repositories()

    def status(self, **kwargs):
        path = self.source['path']
        cmd = subprocess.Popen(["darcs", "whatsnew"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        lines = stdout.strip().split('\n')
        if 'No changes' in lines[-1]:
            status = 'clean'
        else:
            status = 'dirty'
        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def update(self, **kwargs):
        name = self.source['name']
        if not self.matches():
            raise DarcsError("Can't update package '%s' because it's URL doesn't match." % name)
        if self.status() != 'clean' and not kwargs.get('force', False):
            raise DarcsError("Can't update package '%s' because it's dirty." % name)
        return self.darcs_update(**kwargs)

########NEW FILE########
__FILENAME__ = develop
from mr.developer.common import logger, memoize, WorkingCopies, Config, yesno
from mr.developer.extension import Extension
from zc.buildout.buildout import Buildout
import argparse
import atexit
import pkg_resources
import errno
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import textwrap


def find_base():
    path = os.getcwd()
    while path:
        if os.path.exists(os.path.join(path, '.mr.developer.cfg')):
            break
        old_path = path
        path = os.path.dirname(path)
        if old_path == path:
            path = None
            break
    if path is None:
        raise IOError(".mr.developer.cfg not found")

    return path


class ChoicesPseudoAction(argparse.Action):

    def __init__(self, *args, **kwargs):
        sup = super(ChoicesPseudoAction, self)
        sup.__init__(dest=args[0], option_strings=list(args), help=kwargs.get('help'), nargs=0)


class ArgumentParser(argparse.ArgumentParser):
    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join([repr(x) for x in sorted(action.choices) if x != 'pony'])
            msg = argparse._('invalid choice: %r (choose from %s)') % tup
            raise argparse.ArgumentError(action, msg)


class HelpFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        return self._fill_text(text, width, "").split("\n")

    def _fill_text(self, text, width, indent):
        result = []
        for line in text.split("\n"):
            for line2 in textwrap.fill(line, width).split("\n"):
                result.append("%s%s" % (indent, line2))
        return "\n".join(result)


class Command(object):
    def __init__(self, develop):
        self.develop = develop

    def get_workingcopies(self, sources):
        return WorkingCopies(sources, threads=self.develop.threads)

    @memoize
    def get_packages(self, args, auto_checkout=False,
                     develop=False, checked_out=False):
        if auto_checkout:
            packages = set(self.develop.auto_checkout)
        else:
            packages = set(self.develop.sources)
        if develop:
            packages = packages.intersection(set(self.develop.develeggs))
        if checked_out:
            for name in set(packages):
                if not self.develop.sources[name].exists():
                    packages.remove(name)
        if not args:
            return packages
        result = set()
        regexp = re.compile("|".join("(%s)" % x for x in args))
        for name in packages:
            if not regexp.search(name):
                continue
            result.add(name)

        if len(result) == 0:
            if len(args) > 1:
                regexps = "%s or '%s'" % (", ".join("'%s'" % x for x in args[:-1]), args[-1])
            else:
                regexps = "'%s'" % args[0]
            logger.error("No package matched %s." % regexps)
            sys.exit(1)

        return result


class CmdActivate(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Add packages to the list of development packages."
        self.parser = self.develop.parsers.add_parser(
            "activate",
            description=description)
        self.develop.parsers._name_parser_map["a"] = self.develop.parsers._name_parser_map["activate"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "activate", "a", help=description))
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-c", "--checked-out", dest="checked_out",
                               action="store_true", default=False,
                               help="""Only considers packages currently checked out. If you don't specify a <package-regexps> then all checked out packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all develop packages are processed.""")
        self.parser.add_argument("package-regexp", nargs="+",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        config = self.develop.config
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     checked_out=args.checked_out,
                                     develop=args.develop)
        changed = False
        for name in sorted(packages):
            source = self.develop.sources[name]
            if not source.exists():
                logger.warning("The package '%s' matched, but isn't checked out." % name)
                continue
            if not source.get('egg', True):
                logger.warning("The package '%s' isn't an egg." % name)
                continue
            config.develop[name] = True
            logger.info("Activated '%s'." % name)
            changed = True
        if changed:
            logger.warn("Don't forget to run buildout again, so the actived packages are actually used.")
        config.save()


class CmdArguments(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Print arguments used by last buildout which will be used with the 'rebuild' command."
        self.parser = self.develop.parsers.add_parser(
            "arguments",
            description=description)
        self.develop.parsers._name_parser_map["args"] = self.develop.parsers._name_parser_map["arguments"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "arguments", "args", help=description))
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        buildout_args = self.develop.config.buildout_args
        print("Last used buildout arguments: %s" % " ".join(buildout_args[1:]))


class CmdCheckout(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        self.parser = self.develop.parsers.add_parser(
            "checkout",
            description="Make a checkout of the packages matching the regular expressions and add them to the list of development packages.")
        self.develop.parsers._name_parser_map["co"] = self.develop.parsers._name_parser_map["checkout"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "checkout", "co", help="Checkout packages"))
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-v", "--verbose", dest="verbose",
                               action="store_true", default=False,
                               help="""Show output of VCS command.""")
        self.parser.add_argument("package-regexp", nargs="+",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        config = self.develop.config
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout)
        try:
            workingcopies = self.get_workingcopies(self.develop.sources)
            workingcopies.checkout(sorted(packages),
                                   verbose=args.verbose,
                                   submodules=self.develop.update_git_submodules,
                                   always_accept_server_certificate=self.develop.always_accept_server_certificate)
            for name in sorted(packages):
                source = self.develop.sources[name]
                if not source.get('egg', True):
                    continue
                config.develop[name] = True
                logger.info("Activated '%s'." % name)
            logger.warn("Don't forget to run buildout again, so the checked out packages are used as develop eggs.")
            config.save()
        except (ValueError, KeyError):
            logger.error(sys.exc_info()[1])
            sys.exit(1)


class CmdDeactivate(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Remove packages from the list of development packages."
        self.parser = self.develop.parsers.add_parser(
            "deactivate",
            description=description)
        self.develop.parsers._name_parser_map["d"] = self.develop.parsers._name_parser_map["deactivate"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "deactivate", "d", help=description))
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-c", "--checked-out", dest="checked_out",
                               action="store_true", default=False,
                               help="""Only considers packages currently checked out. If you don't specify a <package-regexps> then all checked out packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all develop packages are processed.""")
        self.parser.add_argument("package-regexp", nargs="+",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        config = self.develop.config
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     checked_out=args.checked_out,
                                     develop=args.develop)
        changed = False
        for name in sorted(packages):
            source = self.develop.sources[name]
            if not source.exists():
                logger.warning("The package '%s' matched, but isn't checked out." % name)
                continue
            if not source.get('egg', True):
                logger.warning("The package '%s' isn't an egg." % name)
                continue
            if config.develop.get(name) is not False:
                config.develop[name] = False
                logger.info("Deactivated '%s'." % name)
                changed = True
        if changed:
            logger.warn("Don't forget to run buildout again, so the deactived packages are actually not used anymore.")
        config.save()


class CmdHelp(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        self.parser = self.develop.parsers.add_parser(
            "help",
            description="Show help on the given command or about the whole script if none given.")
        self.develop.parsers._name_parser_map["h"] = self.develop.parsers._name_parser_map["help"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "help", "h", help="Show help"))
        self.parser.add_argument("--rst", dest="rst",
                               action="store_true", default=False,
                               help="""Print help for all commands in reStructuredText format.""")
        self.parser.add_argument('-z', '--zsh',
                            action='store_true',
                            help="Print info for zsh autocompletion")
        self.parser.add_argument("command", nargs="?", help="The command you want to see the help of.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        develop = self.develop
        choices = develop.parsers.choices
        if args.zsh:
            choices = [x for x in choices if x != 'pony']
            if args.command is None:
                print("\n".join(choices))
            else:
                if args.command == 'help':
                    print("\n".join(choices))
                elif args.command in ('purge', 'up', 'update'):
                    print("\n".join(self.get_packages(None, checked_out=True)))
                elif args.command not in ('pony', 'rebuild'):
                    print("\n".join(self.get_packages(None)))
            return
        if args.command in choices:
            print(choices[args.command].format_help())
            return
        cmds = {}
        for name in choices:
            if name == 'pony':
                continue
            cmds.setdefault(choices[name], set()).add(name)
        for cmd, names in cmds.items():
            names = list(reversed(sorted(names, key=len)))
            cmds[names[0]] = dict(
                aliases=names[1:],
                cmd=cmd,
            )
            del cmds[cmd]
        if args.rst:
            print("Commands")
            print("========")
            print()
            print("The following is a list of all commands and their options.")
            print()
            for name in sorted(cmds):
                cmd = cmds[name]
                if len(cmd['aliases']):
                    header = "%s (%s)" % (name, ", ".join(cmd['aliases']))
                else:
                    header = name
                print(header)
                print("-" * len(header))
                print()
                print("::")
                print()
                for line in cmd['cmd'].format_help().split('\n'):
                    print("    %s" % line)
                print()
        else:
            print(self.parser.format_help())
            print("Available commands:")
            for name in sorted(cmds):
                cmd = cmds[name]
                if len(cmd['aliases']):
                    print("    %s (%s)" % (name, ", ".join(cmd['aliases'])))
                else:
                    print("    %s" % name)


class CmdInfo(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Lists informations about packages."
        self.parser = self.develop.parsers.add_parser(
            "info",
            help=description,
            description=description)
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-c", "--checked-out", dest="checked_out",
                               action="store_true", default=False,
                               help="""Only considers packages currently checked out. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all declared packages are processed.""")
        info_opts = self.parser.add_argument_group("Output options",
                                              """The following options are used to print just the info you want, the order they are specified reflects the order in which the information will be printed.""")
        info_opts.add_argument("--name", dest="info",
                             action="append_const", const="name",
                             help="""Prints the name of the package.""")
        info_opts.add_argument("-p", "--path", dest="info",
                             action="append_const", const="path",
                             help="""Prints the absolute path of the package.""")
        info_opts.add_argument("--type", dest="info",
                             action="append_const", const="type",
                             help="""Prints the repository type of the package.""")
        info_opts.add_argument("--url", dest="info",
                             action="append_const", const="url",
                             help="""Prints the URL of the package.""")
        self.parser.add_argument_group(info_opts)
        self.parser.add_argument("package-regexp", nargs="*",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     develop=args.develop,
                                     checked_out=args.checked_out)
        for name in sorted(packages):
            source = self.develop.sources[name]
            if args.info:
                info = []
                for key in args.info:
                    if key == 'name':
                        info.append(name)
                    elif key == 'path':
                        info.append(source['path'])
                    elif key == 'type':
                        info.append(source['kind'])
                    elif key == 'url':
                        info.append(source['url'])
                print(" ".join(info))
            else:
                print("Name: %s" % name)
                print("Path: %s" % source['path'])
                print("Type: %s" % source['kind'])
                print("URL: %s" % source['url'])
                print()


class CmdList(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Lists tracked packages."
        self.parser = self.develop.parsers.add_parser(
            "list",
            formatter_class=HelpFormatter,
            description=description)
        self.develop.parsers._name_parser_map["ls"] = self.develop.parsers._name_parser_map["list"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "list", "ls", help=description))
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only show packages in auto-checkout list.""")
        self.parser.add_argument("-c", "--checked-out", dest="checked_out",
                               action="store_true", default=False,
                               help="""Only considers packages currently checked out. If you don't specify a <package-regexps> then all checked out packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all develop packages are processed.""")
        self.parser.add_argument("-l", "--long", dest="long",
                               action="store_true", default=False,
                               help="""Show URL and kind of package.""")
        self.parser.add_argument("-s", "--status", dest="status",
                               action="store_true", default=False,
                               help=textwrap.dedent("""\
                                   Show checkout status.
                                   The first column in the output shows the checkout status:
                                       '#' available for checkout
                                       ' ' in auto-checkout list and checked out
                                       '~' not in auto-checkout list, but checked out
                                       '!' in auto-checkout list, but not checked out
                                       'C' the repository URL doesn't match"""))
        self.parser.add_argument("package-regexp", nargs="*",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        sources = self.develop.sources
        auto_checkout = self.develop.auto_checkout
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     checked_out=args.checked_out,
                                     develop=args.develop)
        workingcopies = self.get_workingcopies(sources)
        for name in sorted(packages):
            source = sources[name]
            info = []
            if args.status:
                if source.exists():
                    if not workingcopies.matches(source):
                        info.append("C")
                    else:
                        if name in auto_checkout:
                            info.append(" ")
                        else:
                            info.append("~")
                else:
                    if name in auto_checkout:
                        info.append("!")
                    else:
                        info.append("#")
            if args.long:
                info.append("(%s) %s %s" % (source['kind'], name, source['url']))
            else:
                info.append(name)
            print(" ".join(info))


class CmdPony(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        self.parser = self.develop.parsers.add_parser(
            "pony",
            description="It should be easy to develop a pony!")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        pony = '''
            .,,.
         ,;;*;;;;,
        .-'``;-');;.
       /'  .-.  /*;;
     .'    \d    \;;               .;;;,
    / o      `    \;    ,__.     ,;*;;;*;,
    \__, _.__,'   \_.-') __)--.;;;;;*;;;;,
     `""`;;;\       /-')_) __)  `\' ';;;;;;
        ;*;;;        -') `)_)  |\ |  ;;;;*;
        ;;;;|        `---`    O | | ;;*;;;
        *;*;\|                 O  / ;;;;;*
       ;;;;;/|    .-------\      / ;*;;;;;
      ;;;*;/ \    |        '.   (`. ;;;*;;;
      ;;;;;'. ;   |          )   \ | ;;;;;;
      ,;*;;;;\/   |.        /   /` | ';;;*;
       ;;;;;;/    |/       /   /__/   ';;;
       '*jgs/     |       /    |      ;*;
            `""""`        `""""`     ;'
'''
        import time
        logger.info("Starting to develop a pony.")
        for line in pony.split("\n"):
            time.sleep(0.25)
            print(line)
        logger.info("Done.")


class CmdPurge(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = textwrap.dedent("""\
            Remove checked out packages which aren't active anymore.

            Only 'svn' packages can be purged, because other repositories may contain unrecoverable files even when not marked as 'dirty'.""")
        self.parser = self.develop.parsers.add_parser(
            "purge",
            formatter_class=HelpFormatter,
            description=description)
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "purge", help=description))
        self.parser.add_argument("-n", "--dry-run", dest="dry_run",
                               action="store_true", default=False,
                               help="""Don't actually remove anything, just print the paths which would be removed.""")
        self.parser.add_argument("-f", "--force", dest="force",
                               action="store_true", default=False,
                               help="""Force purge even if the working copy is dirty or unknown (non-svn).""")
        self.parser.add_argument("package-regexp", nargs="*",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def handle_remove_readonly(self, func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise

    def __call__(self, args):
        buildout_dir = self.develop.buildout_dir
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     checked_out=True)
        packages = packages - self.develop.auto_checkout
        packages = packages - set(self.develop.develeggs)
        force = args.force
        force_all = False
        workingcopies = self.get_workingcopies(self.develop.sources)
        if args.dry_run:
            logger.info("Dry run, nothing will be removed.")
        for name in packages:
            source = self.develop.sources[name]
            path = source['path']
            if path.startswith(buildout_dir):
                path = path[len(buildout_dir) + 1:]
            need_force = False
            if source['kind'] != 'svn':
                need_force = True
                logger.warn("The directory of package '%s' at '%s' might contain unrecoverable files and will not be removed without --force." % (name, path))
            if workingcopies.status(source) != 'clean':
                need_force = True
                logger.warn("The package '%s' is dirty and will not be removed without --force." % name)
            if need_force:
                if not force:
                    continue
                # We only get here when a --force is needed and we
                # have actually added the --force argument on the
                # command line.
                if not force_all:
                    answer = yesno("Do you want to purge it anyway?", default=False, all=True)
                    if not answer:
                        logger.info("Skipped purge of '%s'." % name)
                        continue
                    if answer == 'all':
                        force_all = True

            logger.info("Removing package '%s' at '%s'." % (name, path))
            if not args.dry_run:
                shutil.rmtree(source['path'],
                              ignore_errors=False,
                              onerror=self.handle_remove_readonly)


class CmdRebuild(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Run buildout with the last used arguments."
        self.parser = self.develop.parsers.add_parser(
            "rebuild",
            description=description)
        self.develop.parsers._name_parser_map["rb"] = self.develop.parsers._name_parser_map["rebuild"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "rebuild", "rb", help=description))
        self.parser.add_argument("-n", "--dry-run", dest="dry_run",
                               action="store_true", default=False,
                               help="""DEPRECATED: Use 'arguments' command instead. Don't actually run buildout, just show the last used arguments.""")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        buildout_dir = self.develop.buildout_dir
        buildout_args = self.develop.config.buildout_args
        print("Last used buildout arguments: %s" % " ".join(buildout_args[1:]))
        if args.dry_run:
            logger.warning("Dry run, buildout not invoked.")
            logger.warning("DEPRECATED: The use of '-n' and '--dry-run' is deprecated, use the 'arguments' command instead.")
            return
        else:
            logger.info("Running buildout.")
        os.chdir(buildout_dir)
        subprocess.call(buildout_args)


class CmdReset(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        self.parser = self.develop.parsers.add_parser(
            "reset",
            help="Resets the packages develop status.",
            description="Resets the packages develop status. This is useful when switching to a new buildout configuration.")
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-c", "--checked-out", dest="checked_out",
                               action="store_true", default=False,
                               help="""Only considers packages currently checked out. If you don't specify a <package-regexps> then all checked out packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all develop packages are processed.""")
        self.parser.add_argument("package-regexp", nargs="*",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        config = self.develop.config
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     checked_out=args.checked_out,
                                     develop=args.develop)
        changed = False
        for name in sorted(packages):
            if name in config.develop:
                del config.develop[name]
                logger.info("Reset develop state of '%s'." % name)
                changed = True
        if changed:
            logger.warn("Don't forget to run buildout again, so the deactived packages are actually not used anymore.")
        config.save()


class CmdStatus(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        self.parser = self.develop.parsers.add_parser(
            "status",
            formatter_class=HelpFormatter,
            description=textwrap.dedent("""\
                Shows the status of tracked packages, filtered if <package-regexps> is given.
                The first column in the output shows the checkout status:
                    ' ' in auto-checkout list
                    '~' not in auto-checkout list
                    '!' in auto-checkout list, but not checked out
                    'C' the repository URL doesn't match
                    '?' unknown package (only reported when package-regexp is not specified)
                The second column shows the working copy status:
                    ' ' no changes
                    'M' local modifications or untracked files
                    '>' your local branch is ahead of the remote one
                The third column shows the development status:
                    ' ' activated
                    '-' deactivated
                    '!' deactivated, but the package is in the auto-checkout list
                    'A' activated, but not in list of development packages (run buildout)
                    'D' deactivated, but still in list of development packages (run buildout)"""))
        self.develop.parsers._name_parser_map["stat"] = self.develop.parsers._name_parser_map["status"]
        self.develop.parsers._name_parser_map["st"] = self.develop.parsers._name_parser_map["status"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "status", "stat", "st", help="Shows the status of tracked packages."))
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-c", "--checked-out", dest="checked_out",
                               action="store_true", default=False,
                               help="""Only considers packages currently checked out. If you don't specify a <package-regexps> then all checked out packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all develop packages are processed.""")
        self.parser.add_argument("-v", "--verbose", dest="verbose",
                               action="store_true", default=False,
                               help="""Show output of VCS command.""")
        self.parser.add_argument("package-regexp", nargs="*",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        auto_checkout = self.develop.auto_checkout
        sources_dir = self.develop.sources_dir
        develeggs = self.develop.develeggs
        package_regexp = getattr(args, 'package-regexp')
        packages = self.get_packages(package_regexp,
                                     auto_checkout=args.auto_checkout,
                                     checked_out=args.checked_out,
                                     develop=args.develop)
        workingcopies = self.get_workingcopies(self.develop.sources)
        paths = []
        for name in sorted(packages):
            source = self.develop.sources[name]
            if not source.exists():
                if name in auto_checkout:
                    print("!     %s" % name)
                continue
            paths.append(source['path'])
            info = []
            if not workingcopies.matches(source):
                info.append("C")
            else:
                if name in auto_checkout:
                    info.append(" ")
                else:
                    info.append("~")
            if args.verbose:
                status, output = workingcopies.status(source, verbose=True)
            else:
                status = workingcopies.status(source)
            if status == 'clean':
                info.append(" ")
            elif status == 'ahead':
                info.append(">")
            else:
                info.append("M")
            if self.develop.config.develop.get(name, name in auto_checkout):
                if name in develeggs:
                    info.append(" ")
                else:
                    if source.get('egg', True):
                        info.append("A")
                    else:
                        info.append(" ")
            else:
                if name not in develeggs:
                    if not source.get('egg', True):
                        info.append(" ")
                    elif name in auto_checkout:
                        info.append("!")
                    else:
                        info.append("-")
                else:
                    if source.get('egg', True):
                        info.append("D")
                    else:
                        info.append(" ")
            info.append(name)
            print(" ".join(info))
            if args.verbose:
                output = output.strip()
                if output:
                    for line in output.split('\n'):
                        print("      %s" % line)
                    print()

        # Only report on unknown entries when we have no package regexp.
        if not package_regexp:
            for entry in os.listdir(sources_dir):
                if not os.path.join(sources_dir, entry) in paths:
                    print("?     %s" % entry)


class CmdUpdate(Command):
    def __init__(self, develop):
        Command.__init__(self, develop)
        description = "Updates all known packages currently checked out."
        self.parser = self.develop.parsers.add_parser(
            "update",
            description=description)
        self.develop.parsers._name_parser_map["up"] = self.develop.parsers._name_parser_map["update"]
        self.develop.parsers._choices_actions.append(ChoicesPseudoAction(
            "update", "up", help=description))
        self.parser.add_argument("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only considers packages declared by auto-checkout. If you don't specify a <package-regexps> then all declared packages are processed.""")
        self.parser.add_argument("-d", "--develop", dest="develop",
                               action="store_true", default=False,
                               help="""Only considers packages currently in development mode. If you don't specify a <package-regexps> then all develop packages are processed.""")
        self.parser.add_argument("-f", "--force", dest="force",
                               action="store_true", default=False,
                               help="""Force update even if the working copy is dirty.""")
        self.parser.add_argument("-v", "--verbose", dest="verbose",
                               action="store_true", default=False,
                               help="""Show output of VCS command.""")
        self.parser.add_argument("package-regexp", nargs="*",
                                 help="A regular expression to match package names.")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     checked_out=True,
                                     develop=args.develop)
        workingcopies = self.get_workingcopies(self.develop.sources)
        force = args.force or self.develop.always_checkout
        workingcopies.update(sorted(packages),
                             force=force,
                             verbose=args.verbose,
                             submodules=self.develop.update_git_submodules,
                             always_accept_server_certificate=self.develop.always_accept_server_certificate)


class Develop(object):
    def __call__(self, **kwargs):
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)
        self.parser = ArgumentParser()
        version = pkg_resources.get_distribution("mr.developer").version
        self.parser.add_argument('-v', '--version',
                                 action='version',
                                 version='mr.developer %s' % version)
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")
        CmdActivate(self)
        CmdArguments(self)
        CmdCheckout(self)
        CmdDeactivate(self)
        CmdHelp(self)
        CmdInfo(self)
        CmdList(self)
        CmdPony(self)
        CmdPurge(self)
        CmdRebuild(self)
        CmdReset(self)
        CmdStatus(self)
        CmdUpdate(self)
        args = self.parser.parse_args()

        try:
            self.buildout_dir = find_base()
        except IOError:
            if isinstance(args.func, CmdHelp):
                args.func(args)
                return
            self.parser.print_help()
            print
            logger.error("You are not in a path which has mr.developer installed (%s)." % sys.exc_info()[1])
            return

        self.config = Config(self.buildout_dir)
        self.original_dir = os.getcwd()
        atexit.register(self.restore_original_dir)
        os.chdir(self.buildout_dir)
        buildout = Buildout(self.config.buildout_settings['config_file'],
                            self.config.buildout_options,
                            self.config.buildout_settings['user_defaults'],
                            self.config.buildout_settings['windows_restart'])
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.setLevel(logging.INFO)
        extension = Extension(buildout)
        self.sources = extension.get_sources()
        self.sources_dir = extension.get_sources_dir()
        self.auto_checkout = extension.get_auto_checkout()
        self.always_checkout = extension.get_always_checkout()
        self.update_git_submodules = extension.get_update_git_submodules()
        self.always_accept_server_certificate = extension.get_always_accept_server_certificate()
        develop, self.develeggs, versions = extension.get_develop_info()
        self.threads = extension.get_threads()

        args.func(args)

    def restore_original_dir(self):
        os.chdir(self.original_dir)

    @property
    def commands(self):
        commands = getattr(self, '_commands', None)
        if commands is not None:
            return commands
        self._commands = commands = dict()
        for key in dir(self):
            if key.startswith('cmd_'):
                commands[key[4:]] = getattr(self, key)
            if key.startswith('alias_'):
                commands[key[6:]] = getattr(self, key)
        return commands

    def unknown(self):
        logger.error("Unknown command '%s'." % sys.argv[1])
        logger.info("Type '%s help' for usage." % os.path.basename(sys.argv[0]))
        sys.exit(1)

develop = Develop()

########NEW FILE########
__FILENAME__ = extension
from mr.developer.common import memoize, WorkingCopies, Config, get_workingcopytypes
import logging
import os
import re
import sys


FAKE_PART_ID = '_mr.developer'

logger = logging.getLogger("mr.developer")


class Source(dict):
    def exists(self):
        return os.path.exists(self['path'])


class Extension(object):
    def __init__(self, buildout):
        self.buildout = buildout
        self.buildout_dir = buildout['buildout']['directory']
        self.executable = sys.argv[0]

    @memoize
    def get_config(self):
        return Config(self.buildout_dir)

    def get_workingcopies(self):
        return WorkingCopies(
            self.get_sources(),
            threads=self.get_threads())

    @memoize
    def get_threads(self):
        threads = int(self.buildout['buildout'].get(
            'mr.developer-threads',
            self.get_config().threads))
        return threads

    @memoize
    def get_sources_dir(self):
        sources_dir = self.buildout['buildout'].get('sources-dir', 'src')
        if not os.path.isabs(sources_dir):
            sources_dir = os.path.join(self.buildout_dir, sources_dir)
        if os.path.isdir(self.buildout_dir) and not os.path.isdir(sources_dir):
            logger.info('Creating missing sources dir %s.' % sources_dir)
            os.mkdir(sources_dir)
        return sources_dir

    @memoize
    def get_sources(self):
        sources_dir = self.get_sources_dir()
        sources = {}
        sources_section = self.buildout['buildout'].get('sources', 'sources')
        section = self.buildout.get(sources_section, {})
        workingcopytypes = get_workingcopytypes()
        for name in section:
            info = section[name].split()
            options = []
            option_matcher = re.compile(r'[a-zA-Z0-9-]+=.*')
            for index, item in reversed(list(enumerate(info))):
                if option_matcher.match(item):
                    del info[index]
                    options.append(item)
            options.reverse()
            if len(info) < 2:
                logger.error("The source definition of '%s' needs at least the repository kind and URL." % name)
                sys.exit(1)
            kind = info[0]
            if kind not in workingcopytypes:
                logger.error("Unknown repository type '%s' for source '%s'." % (kind, name))
                sys.exit(1)
            url = info[1]

            path = None
            if len(info) > 2:
                if '=' not in info[2]:
                    logger.warn("You should use 'path=%s' to set the path." % info[2])
                    path = os.path.join(info[2], name)
                    if not os.path.isabs(path):
                        path = os.path.join(self.buildout_dir, path)
                    options[:0] = info[3:]
                else:
                    options[:0] = info[2:]

            if path is None:
                source = Source(kind=kind, name=name, url=url)
            else:
                source = Source(kind=kind, name=name, url=url, path=path)

            for option in options:
                key, value = option.split('=', 1)
                if not key:
                    raise ValueError("Option with no name '%s'." % option)
                if key in source:
                    raise ValueError("Key '%s' already in source info." % key)
                if key == 'path':
                    value = os.path.join(value, name)
                    if not os.path.isabs(value):
                        value = os.path.join(self.buildout_dir, value)
                if key == 'full-path':
                    if not os.path.isabs(value):
                        value = os.path.join(self.buildout_dir, value)
                if key == 'egg':
                    if value.lower() in ('true', 'yes', 'on'):
                        value = True
                    elif value.lower() in ('false', 'no', 'off'):
                        value = False
                source[key] = value
            if 'path' not in source:
                if 'full-path' in source:
                    source['path'] = source['full-path']
                else:
                    source['path'] = os.path.join(sources_dir, name)

            for rewrite in self.get_config().rewrites:
                rewrite(source)

            sources[name] = source

        return sources

    @memoize
    def get_auto_checkout(self):
        packages = set(self.get_sources().keys())

        auto_checkout = set(
            self.buildout['buildout'].get('auto-checkout', '').split()
        )
        if '*' in auto_checkout:
            auto_checkout = packages

        if not auto_checkout.issubset(packages):
            diff = list(sorted(auto_checkout.difference(packages)))
            if len(diff) > 1:
                pkgs = "%s and '%s'" % (", ".join("'%s'" % x for x in diff[:-1]), diff[-1])
                logger.error("The packages %s from auto-checkout have no source information." % pkgs)
            else:
                logger.error("The package '%s' from auto-checkout has no source information." % diff[0])
            sys.exit(1)

        return auto_checkout

    def get_always_checkout(self):
        return self.buildout['buildout'].get('always-checkout', False)

    def get_update_git_submodules(self):
        return self.buildout['buildout'].get('update-git-submodules', 'always')

    def get_develop_info(self):
        auto_checkout = self.get_auto_checkout()
        sources = self.get_sources()
        develop = self.buildout['buildout'].get('develop', '')
        versions_section = self.buildout['buildout'].get('versions')
        versions = self.buildout.get(versions_section, {})
        develeggs = {}
        develeggs_order = []
        for path in develop.split():
            # strip / from end of path
            head, tail = os.path.split(path.rstrip('/'))
            develeggs[tail] = path
            develeggs_order.append(tail)
        config_develop = self.get_config().develop
        for name in sources:
            source = sources[name]
            if source.get('egg', True) and name not in develeggs:
                path = sources[name]['path']
                status = config_develop.get(name, name in auto_checkout)
                if os.path.exists(path) and status:
                    if name in auto_checkout:
                        config_develop.setdefault(name, 'auto')
                    else:
                        if status == 'auto':
                            if name in config_develop:
                                del config_develop[name]
                                continue
                        config_develop.setdefault(name, True)
                    develeggs[name] = path
                    develeggs_order.append(name)
                    if name in versions:
                        del versions[name]
        develop = []
        for path in [develeggs[k] for k in develeggs_order]:
            if path.startswith(self.buildout_dir):
                develop.append(path[len(self.buildout_dir) + 1:])
            else:
                develop.append(path)
        return develop, develeggs, versions

    def get_always_accept_server_certificate(self):
        always_accept_server_certificate = self.buildout['buildout'].get('always-accept-server-certificate', False)
        if isinstance(always_accept_server_certificate, bool):
            pass
        elif always_accept_server_certificate.lower() in ('true', 'yes', 'on'):
            always_accept_server_certificate = True
        elif always_accept_server_certificate.lower() in ('false', 'no', 'off'):
            always_accept_server_certificate = False
        else:
            logger.error("Unknown value '%s' for always-accept-server-certificate option." % always_accept_server_certificate)
            sys.exit(1)
        return always_accept_server_certificate

    def add_fake_part(self):
        if FAKE_PART_ID in self.buildout._raw:
            logger.error("The buildout already has a '%s' section, this shouldn't happen" % FAKE_PART_ID)
            sys.exit(1)
        self.buildout._raw[FAKE_PART_ID] = dict(
            recipe='zc.recipe.egg',
            eggs='mr.developer',
        )
        # insert the fake part
        parts = self.buildout['buildout']['parts'].split()
        parts.insert(0, FAKE_PART_ID)
        self.buildout['buildout']['parts'] = " ".join(parts)

    def __call__(self):
        config = self.get_config()

        # store arguments when running from buildout
        if os.path.split(self.executable)[1] in ('buildout', 'buildout-script.py'):
            config.buildout_args = list(sys.argv)

        auto_checkout = self.get_auto_checkout()

        root_logger = logging.getLogger()
        workingcopies = self.get_workingcopies()
        always_checkout = self.get_always_checkout()
        update_git_submodules = self.get_update_git_submodules()
        always_accept_server_certificate = self.get_always_accept_server_certificate()
        (develop, develeggs, versions) = self.get_develop_info()

        packages = set(auto_checkout)
        sources = self.get_sources()
        for pkg in develeggs:
            if pkg in sources:
                if always_checkout or sources[pkg].get('update'):
                    packages.add(pkg)

        offline = self.buildout['buildout'].get('offline', '').lower() == 'true'
        workingcopies.checkout(sorted(packages),
                               verbose=root_logger.level <= 10,
                               update=always_checkout,
                               submodules=update_git_submodules,
                               always_accept_server_certificate=always_accept_server_certificate,
                               offline=offline)

        # get updated info after checkout
        (develop, develeggs, versions) = self.get_develop_info()

        if versions:
            import zc.buildout.easy_install
            zc.buildout.easy_install.default_versions(dict(versions))

        self.buildout['buildout']['develop'] = "\n".join(develop)
        self.buildout['buildout']['sources-dir'] = self.get_sources_dir()

        self.add_fake_part()

        config.save()


def extension(buildout=None):
    return Extension(buildout)()

########NEW FILE########
__FILENAME__ = filesystem
from mr.developer import common
import os

logger = common.logger


class FilesystemError(common.WCError):
    pass


class FilesystemWorkingCopy(common.BaseWorkingCopy):
    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        if os.path.exists(path):
            if self.matches():
                self.output((logger.info, 'Filesystem package %r doesn\'t need a checkout.' % name))
            else:
                raise FilesystemError(
                    'Directory name for existing package %r differs. '
                    'Expected %r.' % (name, self.source['url']))
        else:
            raise FilesystemError(
                'Directory for package %r doesn\'t exist.' % name)
        return ''

    def matches(self):
        return os.path.split(self.source['path'])[1] == self.source['url']

    def status(self, **kwargs):
        if kwargs.get('verbose', False):
            return 'clean', ''
        return 'clean'

    def update(self, **kwargs):
        name = self.source['name']
        if not self.matches():
            raise FilesystemError(
                'Directory name for existing package %r differs. '
                'Expected %r.' % (name, self.source['url']))
        self.output((logger.info, 'Filesystem package %r doesn\'t need update.' % name))
        return ''

########NEW FILE########
__FILENAME__ = git
# -*- coding: utf-8 -*-

from mr.developer import common
import os
import subprocess
import re
import sys


logger = common.logger

if sys.version_info < (3, 0):
    b = lambda x: x
    s = lambda x: x
else:
    b = lambda x: x.encode('ascii')
    s = lambda x: x.decode('ascii')


class GitError(common.WCError):
    pass


class GitWorkingCopy(common.BaseWorkingCopy):
    """The git working copy.

    Now supports git 1.5 and 1.6+ in a single codebase.
    """

    # TODO: make this configurable? It might not make sense however, as we
    # should make master and a lot of other conventional stuff configurable
    _upstream_name = "origin"

    def __init__(self, source):
        self.git_executable = common.which('git')
        if self.git_executable is None:
            logger.error("Cannot find git executable in PATH")
            sys.exit(1)
        if 'rev' in source and 'revision' in source:
            raise ValueError("The source definition of '%s' contains "
                             "duplicate revision options." % source['name'])
        # 'rev' is canonical
        if 'revision' in source:
            source['rev'] = source['revision']
            del source['revision']
        if 'branch' in source and 'rev' in source:
            logger.error("Cannot specify both branch (%s) and rev/revision "
                         "(%s) in source for %s",
                         source['branch'], source['rev'], source['name'])
            sys.exit(1)
        super(GitWorkingCopy, self).__init__(source)

    @common.memoize
    def git_version(self):
        cmd = self.run_git(['--version'])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            logger.error("Could not determine git version")
            logger.error("'git --version' output was:\n%s\n%s" % (stdout, stderr))
            sys.exit(1)

        m = re.search(b("git version (\d+)\.(\d+)(\.\d+)?(\.\d+)?"), stdout)
        if m is None:
            logger.error("Unable to parse git version output")
            logger.error("'git --version' output was:\n%s\n%s" % (stdout, stderr))
            sys.exit(1)
        version = m.groups()

        if version[3] is not None:
            version = (
                int(version[0]),
                int(version[1]),
                int(version[2][1:]),
                int(version[3][1:])
            )
        elif version[2] is not None:
            version = (
                int(version[0]),
                int(version[1]),
                int(version[2][1:])
            )
        else:
            version = (int(version[0]), int(version[1]))
        if version < (1, 5):
            logger.error(
                "Git version %s is unsupported, please upgrade",
                ".".join([str(v) for v in version]))
            sys.exit(1)
        return version

    @property
    def _remote_branch_prefix(self):
        version = self.git_version()
        if version < (1, 6, 3):
            return self._upstream_name
        else:
            return 'remotes/%s' % self._upstream_name

    def run_git(self, commands, **kwargs):
        commands.insert(0, self.git_executable)
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
        # This should ease things up when multiple processes are trying to send
        # back to the main one large chunks of output
        kwargs['bufsize'] = -1
        return subprocess.Popen(commands, **kwargs)

    def git_merge_rbranch(self, stdout_in, stderr_in):
        path = self.source['path']
        branch = self.source['branch']
        rbp = self._remote_branch_prefix
        cmd = self.run_git(["merge", "%s/%s" % (rbp, branch)], cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git merge of remote branch 'origin/%s' failed.\n%s" % (branch, stderr))
        return (stdout_in + stdout,
                stderr_in + stderr)

    def git_checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        if os.path.exists(path):
            self.output((logger.info, "Skipped cloning of existing package '%s'." % name))
            return
        self.output((logger.info, "Cloned '%s' with git." % name))
        # here, but just on 1.6, if a branch was provided we could checkout it
        # directly via the -b <branchname> option instead of doing a separate
        # checkout later: I however think it outweighs the benefits
        cmd = self.run_git(["clone", "--quiet", url, path])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git cloning of '%s' failed.\n%s" % (name, stderr))
        if 'branch' in self.source or 'rev' in self.source:
            stdout, stderr = self.git_switch_branch(stdout, stderr)
        if 'pushurl' in self.source:
            stdout, stderr = self.git_set_pushurl(stdout, stderr)

        update_git_submodules = self.source.get('submodules', kwargs['submodules'])
        if update_git_submodules in ['always', 'checkout']:
            stdout, stderr, initialized = self.git_init_submodules(stdout, stderr)
            # Update only new submodules that we just registered. this is for safety reasons
            # as git submodule update on modified subomdules may cause code loss
            for submodule in initialized:
                stdout, stderr = self.git_update_submodules(stdout, stderr, submodule=submodule)
                self.output((logger.info, "Initialized '%s' submodule at '%s' with git." % (name, submodule)))

        if kwargs.get('verbose', False):
            return stdout

    def git_switch_branch(self, stdout_in, stderr_in):
        path = self.source['path']
        branch = self.source.get('branch', 'master')
        rbp = self._remote_branch_prefix
        cmd = self.run_git(["branch", "-a"], cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("'git branch -a' failed.\n%s" % stderr)
        stdout_in += stdout
        stderr_in += stderr
        if 'rev' in self.source:
            # A tag or revision was specified instead of a branch
            argv = ["checkout", self.source['rev']]
        elif re.search(b("^(\*| ) %s$" % re.escape(branch)), stdout, re.M):
            # the branch is local, normal checkout will work
            argv = ["checkout", branch]
        elif re.search(b("^  " + re.escape(rbp) + "\/" + re.escape(branch)
                + "$"), stdout, re.M):
            # the branch is not local, normal checkout won't work here
            argv = ["checkout", "-b", branch, "%s/%s" % (rbp, branch)]
        else:
            logger.error("No such branch %r", branch)
            sys.exit(1)
        # runs the checkout with predetermined arguments
        cmd = self.run_git(argv, cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git checkout of branch '%s' failed.\n%s" % (branch, stderr))
        return (stdout_in + stdout,
                stderr_in + stderr)

    def git_update(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        self.output((logger.info, "Updated '%s' with git." % name))
        if 'rev' in self.source:
            # Specific revision, so we only fetch.  Pull is fetch plus
            # merge, which is not possible here.
            argv = ["fetch"]
        else:
            argv = ["pull"]
        cmd = self.run_git(argv, cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git pull of '%s' failed.\n%s" % (name, stderr))
        if 'rev' in self.source:
            stdout, stderr = self.git_switch_branch(stdout, stderr)
        elif 'branch' in self.source:
            stdout, stderr = self.git_switch_branch(stdout, stderr)
            stdout, stderr = self.git_merge_rbranch(stdout, stderr)

        update_git_submodules = self.source.get('submodules', kwargs['submodules'])
        if update_git_submodules in ['always']:
            stdout, stderr, initialized = self.git_init_submodules(stdout, stderr)
            # Update only new submodules that we just registered. this is for safety reasons
            # as git submodule update on modified subomdules may cause code loss
            for submodule in initialized:
                stdout, stderr = self.git_update_submodules(stdout, stderr, submodule=submodule)
                self.output((logger.info, "Initialized '%s' submodule at '%s' with git." % (name, submodule)))

        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info, "Skipped checkout of existing package '%s'." % name))
            else:
                self.output((logger.warning, "Checkout URL for existing package '%s' differs. Expected '%s'." % (name, self.source['url'])))
        else:
            return self.git_checkout(**kwargs)

    def status(self, **kwargs):
        path = self.source['path']
        cmd = self.run_git(["status", "-s", "-b"], cwd=path)
        stdout, stderr = cmd.communicate()
        lines = stdout.strip().split(b('\n'))
        if len(lines) == 1:
            if b('ahead') in lines[0]:
                status = 'ahead'
            else:
                status = 'clean'
        else:
            status = 'dirty'
        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def matches(self):
        name = self.source['name']
        path = self.source['path']
        # This is the old matching code: it does not work on 1.5 due to the
        # lack of the -v switch
        cmd = self.run_git(["remote", "show", "-n", self._upstream_name],
                           cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git remote of '%s' failed.\n%s" % (name, stderr))
        return (self.source['url'] in s(stdout).split())

    def update(self, **kwargs):
        name = self.source['name']
        if not self.matches():
            self.output((logger.warning, "Can't update package '%s' because its URL doesn't match." % name))
        if self.status() != 'clean' and not kwargs.get('force', False):
            raise GitError("Can't update package '%s' because it's dirty." % name)
        return self.git_update(**kwargs)

    def git_set_pushurl(self, stdout_in, stderr_in):
        cmd = self.run_git(
            [
                "config",
                "remote.%s.pushurl" % self._upstream_name,
                self.source['pushurl']],
            cwd=self.source['path'])
        stdout, stderr = cmd.communicate()

        if cmd.returncode != 0:
            raise GitError("git config remote.%s.pushurl %s \nfailed.\n" % (self._upstream_name, self.source['pushurl']))
        return (stdout_in + stdout, stderr_in + stderr)

    def git_init_submodules(self, stdout_in, stderr_in):
        cmd = self.run_git(
            [
                'submodule',
                'init'],
            cwd=self.source['path'])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git submodule init failed.\n")
        initialized_submodules = re.findall(r'Submodule\s+[\'"](.*?)[\'"]\s+\(.+\)', s(stdout))
        return (stdout_in + stdout, stderr_in + stderr, initialized_submodules)

    def git_update_submodules(self, stdout_in, stderr_in, submodule='all'):
        params = ['submodule',
                  'update']
        if submodule != 'all':
            params.append(submodule)
        cmd = self.run_git(
            params,
            cwd=self.source['path'])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git submodule update failed.\n")
        return (stdout_in + stdout, stderr_in + stderr)

########NEW FILE########
__FILENAME__ = gitsvn
from mr.developer import common
from mr.developer.svn import SVNWorkingCopy
import subprocess


logger = common.logger


class GitSVNError(common.WCError):
    pass


class GitSVNWorkingCopy(SVNWorkingCopy):

    def gitify_init(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        self.output((logger.info, "Gitified '%s'." % name))
        cmd = subprocess.Popen(["gitify", "init"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSVNError("gitify init for '%s' failed.\n%s" % (name, stdout))
        if kwargs.get('verbose', False):
            return stdout

    def svn_checkout(self, **kwargs):
        super(GitSVNWorkingCopy, self).svn_checkout(**kwargs)
        return self.gitify_init(**kwargs)

    def svn_switch(self, **kwargs):
        super(GitSVNWorkingCopy, self).svn_switch(**kwargs)
        return self.gitify_init(**kwargs)

    def svn_update(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        self.output((logger.info, "Updated '%s' with gitify." % name))
        cmd = subprocess.Popen(["gitify", "update"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSVNError("gitify update for '%s' failed.\n%s" % (name, stdout))
        if kwargs.get('verbose', False):
            return stdout

    def status(self, **kwargs):
        svn_status = super(GitSVNWorkingCopy, self).status(**kwargs)
        if svn_status == 'clean':
            return common.get_workingcopytypes()['git'](
                self.source).status(**kwargs)
        else:
            if kwargs.get('verbose', False):
                return svn_status, ''
            return svn_status

########NEW FILE########
__FILENAME__ = mercurial
from mr.developer import common
import re
import os
import subprocess
import sys

logger = common.logger


if sys.version_info < (3, 0):
    b = lambda x: x
else:
    b = lambda x: x.encode('ascii')


class MercurialError(common.WCError):
    pass


class MercurialWorkingCopy(common.BaseWorkingCopy):

    def __init__(self, source):
        source.setdefault('branch', 'default')
        source.setdefault('rev')
        super(MercurialWorkingCopy, self).__init__(source)

    def hg_clone(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']

        if os.path.exists(path):
            self.output((logger.info, 'Skipped cloning of existing package %r.' % name))
            return
        rev = self.get_rev()
        self.output((logger.info, 'Cloned %r with mercurial.' % name))
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'clone', '--updaterev', rev, '--quiet', '--noninteractive', url, path],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(
                'hg clone for %r failed.\n%s' % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def get_rev(self):
        branch = self.source['branch']
        rev = self.source['rev']

        if branch != 'default':
            if rev:
                raise ValueError("'branch' and 'rev' parameters cannot be used simultanously")
            else:
                rev = branch
        else:
            rev = rev or 'default'

        if self.source.get('newest_tag', '').lower() in ['1', 'true', 'yes']:
            rev = self._get_newest_tag() or rev
        return rev

    def _update_to_rev(self, rev):
        path = self.source['path']
        name = self.source['name']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'checkout', rev, '-c'],
            cwd=path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode:
            raise MercurialError(
                'hg update for %r failed.\n%s' % (name, stderr))
        self.output((logger.info, 'Switched %r to %s.' % (name, rev)))
        return stdout

    def _get_tags(self):
        path = self.source['path']
        name = self.source['name']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        try:
            cmd = subprocess.Popen(
                ['hg', 'tags'],
                cwd=path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            return []
        stdout, stderr = cmd.communicate()
        if cmd.returncode:
            raise MercurialError(
                'hg update for %r failed.\n%s' % (name, stderr))

        tag_line_re = re.compile(r'([^\s]+)[\s]*.*')

        def get_tag_name(line):
            matched = tag_line_re.match(line)
            if matched:
                return matched.groups()[0]

        tags = (get_tag_name(line) for line in stdout.split("\n"))
        return [tag for tag in tags if tag and tag != 'tip']

    def _get_newest_tag(self):
        mask = self.source.get('newest_tag_prefix', self.source.get('newest_tag_mask', ''))
        name = self.source['name']
        tags = self._get_tags()
        if mask:
            tags = [t for t in tags if t.startswith(mask)]
        tags = common.version_sorted(tags, reverse=True)
        if not tags:
            return None
        newest_tag = tags[0]
        self.output((logger.info, 'Picked newest tag for %r from Mercurial: %r.' % (name, newest_tag)))
        return newest_tag

    def hg_pull(self, **kwargs):
        # NOTE: we don't include the branch here as we just want to update
        # to the head of whatever branch the developer is working on
        # However the 'rev' parameter works differently and forces revision
        name = self.source['name']
        path = self.source['path']
        self.output((logger.info, 'Updated %r with mercurial.' % name))
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'pull', '-u'],
            cwd=path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            # hg v2.1 pull returns non-zero return code in case of
            # no remote changes.
            if 'no changes found' not in stdout:
                raise MercurialError(
                    'hg pull for %r failed.\n%s' % (name, stderr))
        # to find newest_tag hg pull is needed before
        rev = self.get_rev()
        if rev:
            stdout += self._update_to_rev(rev)
        if kwargs.get('verbose', False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info, 'Skipped checkout of existing package %r.' % name))
            else:
                raise MercurialError(
                    'Source URL for existing package %r differs. '
                    'Expected %r.' % (name, self.source['url']))
        else:
            return self.hg_clone(**kwargs)

    def matches(self):
        name = self.source['name']
        path = self.source['path']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'showconfig', 'paths.default'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(
                'hg showconfig for %r failed.\n%s' % (name, stderr))
        # now check that the working branch is the same
        return b(self.source['url'] + '\n') == stdout

    def status(self, **kwargs):
        path = self.source['path']
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        cmd = subprocess.Popen(
            ['hg', 'status'], cwd=path,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        status = stdout and 'dirty' or 'clean'
        if status == 'clean':
            cmd = subprocess.Popen(
                ['hg', 'outgoing'], cwd=path,
                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            outgoing_stdout, stderr = cmd.communicate()
            stdout += b('\n') + outgoing_stdout
            if cmd.returncode == 0:
                status = 'ahead'
        if kwargs.get('verbose', False):
            return status, stdout
        else:
            return status

    def update(self, **kwargs):
        name = self.source['name']
        if not self.matches():
            raise MercurialError(
                "Can't update package %r because its URL doesn't match." %
                name)
        if self.status() != 'clean' and not kwargs.get('force', False):
            raise MercurialError(
                "Can't update package %r because it's dirty." % name)
        return self.hg_pull(**kwargs)

########NEW FILE########
__FILENAME__ = svn
from mr.developer import common
try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse
try:
    import xml.etree.ElementTree as etree
    etree  # shutup pyflakes
except ImportError:
    import elementtree.ElementTree as etree
import getpass
import os
import re
import subprocess
import sys

if sys.version_info < (3, 0):
    b = lambda x: x
    s = lambda x: x
else:
    b = lambda x: x.encode('ascii')
    s = lambda x: x.decode('ascii')


try:
    raw_input = raw_input
except NameError:
    raw_input = input


logger = common.logger


class SVNError(common.WCError):
    pass


class SVNAuthorizationError(SVNError):
    pass


class SVNCertificateError(SVNError):
    pass


class SVNCertificateRejectedError(SVNError):
    pass


_svn_version_warning = False


class SVNWorkingCopy(common.BaseWorkingCopy):
    _svn_info_cache = {}
    _svn_auth_cache = {}
    _svn_cert_cache = {}

    @classmethod
    def _clear_caches(klass):
        klass._svn_info_cache.clear()
        klass._svn_auth_cache.clear()
        klass._svn_cert_cache.clear()

    def _normalized_url_rev(self):
        url = urlparse(self.source['url'])
        rev = None
        if '@' in url[2]:
            path, rev = url[2].split('@', 1)
            url = list(url)
            url[2] = path
        if 'rev' in self.source and 'revision' in self.source:
            raise ValueError("The source definition of '%s' contains duplicate revision options." % self.source['name'])
        if rev is not None and ('rev' in self.source or 'revision' in self.source):
            raise ValueError("The url of '%s' contains a revision and there is an additional revision option." % self.source['name'])
        elif rev is None:
            rev = self.source.get('revision', self.source.get('rev'))
        return urlunparse(url), rev

    def __init__(self, *args, **kwargs):
        common.BaseWorkingCopy.__init__(self, *args, **kwargs)
        self._svn_check_version()

    def _svn_check_version(self):
        global _svn_version_warning
        try:
            cmd = subprocess.Popen(["svn", "--version"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        except OSError:
            if getattr(sys.exc_info()[1], 'errno', None) == 2:
                logger.error("Couldn't find 'svn' executable on your PATH.")
                sys.exit(1)
            raise
        stdout, stderr = cmd.communicate()
        lines = stdout.split(b('\n'))
        version = None
        if len(lines):
            version = re.search(b('(\d+)\.(\d+)(\.\d+)?'), lines[0])
            if version is not None:
                version = version.groups()
                if len(version) == 3:
                    version = (int(version[0]), int(version[1]), int(version[2][1:]))
                else:
                    version = (int(version[0]), int(version[1]))
        if (cmd.returncode != 0) or (version is None):
            logger.error("Couldn't determine the version of 'svn' command.")
            logger.error("Subversion output:\n%s\n%s" % (s(stdout), s(stderr)))
            sys.exit(1)
        if (version < (1, 5)) and not _svn_version_warning:
            logger.warning("The installed 'svn' command is too old. Expected 1.5 or newer, got %s." % ".".join([str(x) for x in version]))
            _svn_version_warning = True

    def _svn_auth_get(self, url):
        for root in self._svn_auth_cache:
            if url.startswith(root):
                return self._svn_auth_cache[root]

    def _svn_accept_invalid_cert_get(self, url):
        for root in self._svn_cert_cache:
            if url.startswith(root):
                return self._svn_cert_cache[root]

    def _svn_error_wrapper(self, f, **kwargs):
        count = 4
        while count:
            count = count - 1
            try:
                return f(**kwargs)
            except SVNAuthorizationError:
                lines = sys.exc_info()[1].args[0].split('\n')
                root = lines[-1].split('(')[-1].strip(')')
                before = self._svn_auth_cache.get(root)
                common.output_lock.acquire()
                common.input_lock.acquire()
                after = self._svn_auth_cache.get(root)
                if before != after:
                    count = count + 1
                    common.input_lock.release()
                    common.output_lock.release()
                    continue
                print("Authorization needed for '%s' at '%s'" % (self.source['name'], self.source['url']))
                user = raw_input("Username: ")
                passwd = getpass.getpass("Password: ")
                self._svn_auth_cache[root] = dict(
                    user=user,
                    passwd=passwd,
                )
                common.input_lock.release()
                common.output_lock.release()
            except SVNCertificateError:
                lines = sys.exc_info()[1].args[0].split('\n')
                root = lines[-1].split('(')[-1].strip(')')
                before = self._svn_cert_cache.get(root)
                common.output_lock.acquire()
                common.input_lock.acquire()
                after = self._svn_cert_cache.get(root)
                if before != after:
                    count = count + 1
                    common.input_lock.release()
                    common.output_lock.release()
                    continue
                print("\n".join(lines[:-1]))
                while 1:
                    answer = raw_input("(R)eject or accept (t)emporarily? ")
                    if answer.lower() in ['r', 't']:
                        break
                    else:
                        print("Invalid answer, type 'r' for reject or 't' for temporarily.")
                if answer == 'r':
                    self._svn_cert_cache[root] = False
                else:
                    self._svn_cert_cache[root] = True
                count = count + 1
                common.input_lock.release()
                common.output_lock.release()

    def _svn_checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url = self.source['url']
        args = ["svn", "checkout", url, path]
        stdout, stderr, returncode = self._svn_communicate(args, url, **kwargs)
        if returncode != 0:
            raise SVNError("Subversion checkout for '%s' failed.\n%s" % (name, s(stderr)))
        if kwargs.get('verbose', False):
            return s(stdout)

    def _svn_communicate(self, args, url, **kwargs):
        auth = self._svn_auth_get(url)
        if auth is not None:
            args[2:2] = ["--username", auth['user'],
                         "--password", auth['passwd']]
        if not kwargs.get('verbose', False):
            args[2:2] = ["--quiet"]
        accept_invalid_cert = self._svn_accept_invalid_cert_get(url)
        if 'always_accept_server_certificate' in kwargs:
            if kwargs['always_accept_server_certificate']:
                accept_invalid_cert = True
        if accept_invalid_cert is True:
            args[2:2] = ["--trust-server-cert"]
        elif accept_invalid_cert is False:
            raise SVNCertificateRejectedError("Server certificate rejected by user.")
        args[2:2] = ["--no-auth-cache"]
        interactive_args = args[:]
        args[2:2] = ["--non-interactive"]
        cmd = subprocess.Popen(args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            lines = stderr.strip().split(b('\n'))
            if 'authorization failed' in lines[-1] or 'Could not authenticate to server' in lines[-1]:
                raise SVNAuthorizationError(stderr.strip())
            if 'Server certificate verification failed: issuer is not trusted' in lines[-1]:
                cmd = subprocess.Popen(interactive_args,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
                stdout, stderr = cmd.communicate('t')
                raise SVNCertificateError(stderr.strip())
        return stdout, stderr, cmd.returncode

    def _svn_info(self):
        name = self.source['name']
        if name in self._svn_info_cache:
            return self._svn_info_cache[name]
        path = self.source['path']
        cmd = subprocess.Popen(["svn", "info", "--non-interactive", "--xml",
                                path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise SVNError("Subversion info for '%s' failed.\n%s" % (name, s(stderr)))
        info = etree.fromstring(stdout)
        result = {}
        entry = info.find('entry')
        if entry is not None:
            rev = entry.attrib.get('revision')
            if rev is not None:
                result['revision'] = rev
            info_url = entry.find('url')
            if info_url is not None:
                result['url'] = info_url.text
        entry = info.find('entry')
        if entry is not None:
            root = entry.find('root')
            if root is not None:
                result['root'] = root.text
        self._svn_info_cache[name] = result
        return result

    def _svn_switch(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url, rev = self._normalized_url_rev()
        args = ["svn", "switch", url, path]
        if rev is not None and not rev.startswith('>'):
            args.insert(2, '-r%s' % rev)
        stdout, stderr, returncode = self._svn_communicate(args, url, **kwargs)
        if returncode != 0:
            raise SVNError("Subversion switch of '%s' failed.\n%s" % (name, s(stderr)))
        if kwargs.get('verbose', False):
            return s(stdout)

    def _svn_update(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        url, rev = self._normalized_url_rev()
        args = ["svn", "update", path]
        if rev is not None and not rev.startswith('>'):
            args.insert(2, '-r%s' % rev)
        stdout, stderr, returncode = self._svn_communicate(args, url, **kwargs)
        if returncode != 0:
            raise SVNError("Subversion update of '%s' failed.\n%s" % (name, s(stderr)))
        if kwargs.get('verbose', False):
            return s(stdout)

    def svn_checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        if os.path.exists(path):
            self.output((logger.info, "Skipped checkout of existing package '%s'." % name))
            return
        self.output((logger.info, "Checked out '%s' with subversion." % name))
        return self._svn_error_wrapper(self._svn_checkout, **kwargs)

    def svn_switch(self, **kwargs):
        name = self.source['name']
        self.output((logger.info, "Switched '%s' with subversion." % name))
        return self._svn_error_wrapper(self._svn_switch, **kwargs)

    def svn_update(self, **kwargs):
        name = self.source['name']
        self.output((logger.info, "Updated '%s' with subversion." % name))
        return self._svn_error_wrapper(self._svn_update, **kwargs)

    def checkout(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            matches = self.matches()
            if matches:
                if update:
                    self.update(**kwargs)
                else:
                    self.output((logger.info, "Skipped checkout of existing package '%s'." % name))
            else:
                if self.status() == 'clean':
                    return self.svn_switch(**kwargs)
                else:
                    raise SVNError("Can't switch package '%s' to '%s' because it's dirty." % (name, self.source['url']))
        else:
            return self.svn_checkout(**kwargs)

    def matches(self):
        info = self._svn_info()
        url, rev = self._normalized_url_rev()
        if url.endswith('/'):
            url = url[:-1]
        if rev is None:
            rev = info.get('revision')
        if rev.startswith('>='):
            return (info.get('url') == url) and (int(info.get('revision')) >= int(rev[2:]))
        elif rev.startswith('>'):
            return (info.get('url') == url) and (int(info.get('revision')) > int(rev[1:]))
        else:
            return (info.get('url') == url) and (info.get('revision') == rev)

    def status(self, **kwargs):
        name = self.source['name']
        path = self.source['path']
        cmd = subprocess.Popen(["svn", "status", "--xml", path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise SVNError("Subversion status for '%s' failed.\n%s" % (name, s(stderr)))
        info = etree.fromstring(stdout)
        clean = True
        for target in info.findall('target'):
            for entry in target.findall('entry'):
                status = entry.find('wc-status')
                if status is not None and status.get('item') != 'external':
                    clean = False
                    break
        if clean:
            status = 'clean'
        else:
            status = 'dirty'
        if kwargs.get('verbose', False):
            cmd = subprocess.Popen(["svn", "status", path],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            stdout, stderr = cmd.communicate()
            if cmd.returncode != 0:
                raise SVNError("Subversion status for '%s' failed.\n%s" % (name, s(stderr)))
            return status, s(stdout)
        else:
            return status

    def update(self, **kwargs):
        name = self.source['name']
        force = kwargs.get('force', False)
        status = self.status()
        if not self.matches():
            if force or status == 'clean':
                return self.svn_switch(**kwargs)
            else:
                raise SVNError("Can't switch package '%s' because it's dirty." % name)
        if status != 'clean' and not force:
            raise SVNError("Can't update package '%s' because it's dirty." % name)
        return self.svn_update(**kwargs)

########NEW FILE########
__FILENAME__ = test_common
from unittest import TestCase


class TestParseBuildoutArgs(TestCase):
    def setUp(self):
        from mr.developer.common import parse_buildout_args
        self.parse_buildout_args = parse_buildout_args

    def checkOptions(self, options):
        for option in options:
            self.assertEquals(len(option), 3)

    def testTimeoutValue(self):
        options, settings, args = self.parse_buildout_args(['-t', '5'])
        self.checkOptions(options)

    def testCommands(self):
        options, settings, args = self.parse_buildout_args(['-t', '5'])
        self.assertEquals(len(args), 0)
        options, settings, args = self.parse_buildout_args(['-t', '5', 'install', 'partname'])
        self.assertEquals(len(args), 2)


class TestRewrites(TestCase):
    def setUp(self):
        from mr.developer.common import Rewrite
        self.Rewrite = Rewrite

    def testMissingSubstitute(self):
        self.assertRaises(ValueError, self.Rewrite, ("url ~ foo"))

    def testInvalidOptions(self):
        self.assertRaises(ValueError, self.Rewrite, ("name ~ foo\nbar"))
        self.assertRaises(ValueError, self.Rewrite, ("path ~ foo\nbar"))

    def testPartialSubstitute(self):
        rewrite = self.Rewrite("url ~ fschulze(/mr.developer.git)\nme\\1")
        source = dict(url="https://github.com/fschulze/mr.developer.git")
        rewrite(source)
        assert source['url'] == "https://github.com/me/mr.developer.git"

    def testExactMatch(self):
        rewrite = self.Rewrite("url ~ fschulze(/mr.developer.git)\nme\\1\nkind = git")
        sources = [
            dict(url="https://github.com/fschulze/mr.developer.git", kind='git'),
            dict(url="https://github.com/fschulze/mr.developer.git", kind='gitsvn'),
            dict(url="https://github.com/fschulze/mr.developer.git", kind='svn')]
        for source in sources:
            rewrite(source)
        assert sources[0]['url'] == "https://github.com/me/mr.developer.git"
        assert sources[1]['url'] == "https://github.com/fschulze/mr.developer.git"
        assert sources[2]['url'] == "https://github.com/fschulze/mr.developer.git"

    def testRegexpMatch(self):
        rewrite = self.Rewrite("url ~ fschulze(/mr.developer.git)\nme\\1\nkind ~= git")
        sources = [
            dict(url="https://github.com/fschulze/mr.developer.git", kind='git'),
            dict(url="https://github.com/fschulze/mr.developer.git", kind='gitsvn'),
            dict(url="https://github.com/fschulze/mr.developer.git", kind='svn')]
        for source in sources:
            rewrite(source)
        assert sources[0]['url'] == "https://github.com/me/mr.developer.git"
        assert sources[1]['url'] == "https://github.com/me/mr.developer.git"
        assert sources[2]['url'] == "https://github.com/fschulze/mr.developer.git"

    def testRegexpMatchAndSubstitute(self):
        rewrite = self.Rewrite("url ~ fschulze(/mr.developer.git)\nme\\1\nurl ~= ^http:")
        sources = [
            dict(url="http://github.com/fschulze/mr.developer.git"),
            dict(url="https://github.com/fschulze/mr.developer.git"),
            dict(url="https://github.com/fschulze/mr.developer.git")]
        for source in sources:
            rewrite(source)
        assert sources[0]['url'] == "http://github.com/me/mr.developer.git"
        assert sources[1]['url'] == "https://github.com/fschulze/mr.developer.git"
        assert sources[2]['url'] == "https://github.com/fschulze/mr.developer.git"


def test_version_sorted():
    from mr.developer.common import version_sorted
    expected = [
        'version-1-0-1',
        'version-1-0-2',
        'version-1-0-10']
    actual = version_sorted([
        'version-1-0-10',
        'version-1-0-2',
        'version-1-0-1'])
    assert expected == actual

########NEW FILE########
__FILENAME__ = test_cvs
import unittest
import doctest
import mr.developer.cvs


def test_suite():
    return unittest.TestSuite([doctest.DocTestSuite(mr.developer.cvs)])

########NEW FILE########
__FILENAME__ = test_develop
from mock import patch
from unittest import TestCase


class MockConfig(object):
    def __init__(self):
        self.develop = {}

    def save(self):
        pass


class MockDevelop(object):
    def __init__(self):
        from mr.developer.develop import ArgumentParser
        self.config = MockConfig()
        self.parser = ArgumentParser()
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")


class MockSource(dict):
    def exists(self):
        return getattr(self, '_exists', True)


class TestCommand(TestCase):
    def setUp(self):
        self.develop = MockDevelop()
        self.develop.sources = ['foo', 'bar', 'baz', 'ham']
        self.develop.auto_checkout = set(['foo', 'ham'])

    def testEmptyMatchList(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages([])
        self.assertEquals(pkgs, set(['foo', 'bar', 'baz', 'ham']))

    def testEmptyMatchListAuto(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages([], auto_checkout=True)
        self.assertEquals(pkgs, set(['foo', 'ham']))

    def testSingleArgMatchingOne(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ha'])
        self.assertEquals(pkgs, set(['ham']))

    def testSingleArgMatchingMultiple(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ba'])
        self.assertEquals(pkgs, set(['bar', 'baz']))

    def testArgsMatchingOne(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ha', 'zap'])
        self.assertEquals(pkgs, set(['ham']))

    def testArgsMatchingMultiple(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ba', 'zap'])
        self.assertEquals(pkgs, set(['bar', 'baz']))

    def testArgsMatchingMultiple2(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ha', 'ba'])
        self.assertEquals(pkgs, set(['bar', 'baz', 'ham']))

    def testSingleArgMatchingOneAuto(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ha'], auto_checkout=True)
        self.assertEquals(pkgs, set(['ham']))

    def testSingleArgMatchingMultipleAuto(self):
        from mr.developer.develop import Command
        self.assertRaises(SystemExit, Command(self.develop).get_packages,
                          ['ba'], auto_checkout=True)

    def testArgsMatchingOneAuto(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ha', 'zap'],
                                                  auto_checkout=True)
        self.assertEquals(pkgs, set(['ham']))

    def testArgsMatchingMultipleAuto(self):
        from mr.developer.develop import Command
        self.assertRaises(SystemExit, Command(self.develop).get_packages,
                          ['ba', 'zap'], auto_checkout=True)

    def testArgsMatchingMultiple2Auto(self):
        from mr.developer.develop import Command
        pkgs = Command(self.develop).get_packages(['ha', 'ba'],
                                                  auto_checkout=True)
        self.assertEquals(pkgs, set(['ham']))


class TestDeactivateCommand(TestCase):
    def setUp(self):
        from mr.developer.develop import CmdDeactivate
        self.develop = MockDevelop()
        self.develop.sources = dict(
            foo=MockSource(),
            bar=MockSource(),
            baz=MockSource(),
            ham=MockSource())
        self.develop.auto_checkout = set(['foo', 'ham'])
        self.develop.config.develop['foo'] = 'auto'
        self.develop.config.develop['ham'] = 'auto'
        self.cmd = CmdDeactivate(self.develop)

    def testDeactivateDeactivatedPackage(self):
        self.develop.config.develop['bar'] = False
        args = self.develop.parser.parse_args(args=['deactivate', 'bar'])
        _logger = patch('mr.developer.develop.logger')
        logger = _logger.__enter__()
        try:
            self.cmd(args)
        finally:
            _logger.__exit__()
        assert self.develop.config.develop == dict(
            bar=False,
            foo='auto',
            ham='auto')
        assert logger.mock_calls == []

    def testDeactivateActivatedPackage(self):
        self.develop.config.develop['bar'] = True
        args = self.develop.parser.parse_args(args=['deactivate', 'bar'])
        _logger = patch('mr.developer.develop.logger')
        logger = _logger.__enter__()
        try:
            self.cmd(args)
        finally:
            _logger.__exit__()
        assert self.develop.config.develop == dict(
            bar=False,
            foo='auto',
            ham='auto')
        assert logger.mock_calls == [
            ('info', ("Deactivated 'bar'.",), {}),
            ('warn', ("Don't forget to run buildout again, so the deactived packages are actually not used anymore.",), {})]

    def testDeactivateAutoCheckoutPackage(self):
        args = self.develop.parser.parse_args(args=['deactivate', 'foo'])
        _logger = patch('mr.developer.develop.logger')
        logger = _logger.__enter__()
        try:
            self.cmd(args)
        finally:
            _logger.__exit__()
        assert self.develop.config.develop == dict(
            foo=False,
            ham='auto')
        assert logger.mock_calls == [
            ('info', ("Deactivated 'foo'.",), {}),
            ('warn', ("Don't forget to run buildout again, so the deactived packages are actually not used anymore.",), {})]

########NEW FILE########
__FILENAME__ = test_extension
from copy import deepcopy
from mock import patch
from unittest import TestCase
import os
import shutil
import tempfile


class MockBuildout(object):
    def __init__(self, config=None):
        if config is None:
            config = dict()
        self._raw = deepcopy(config)

    def __contains__(self, key):
        return key in self._raw

    def __getitem__(self, key):
        return self._raw[key]

    def get(self, key, default=None):
        return self._raw.get(key, default)

    def __repr__(self):
        return repr(self._raw)


class MockConfig(object):
    def __init__(self):
        self.buildout_args = []
        self.develop = {}
        self.rewrites = []

    def save(self):
        return


class MockWorkingCopies(object):
    def __init__(self, sources):
        self.sources = sources
        self._events = []

    def checkout(self, packages, **kwargs):
        self._events.append(('checkout', packages, kwargs))
        return False


class TestExtensionClass(TestCase):
    def setUp(self):
        from mr.developer.extension import memoize, Extension

        self.buildout = MockBuildout(dict(
            buildout=dict(
                directory='/buildout',
                parts='',
            ),
            sources={},
        ))

        class MockExtension(Extension):
            @memoize
            def get_config(self):
                return MockConfig()

            @memoize
            def get_workingcopies(self):
                return MockWorkingCopies(self.get_sources())

        self.extension = MockExtension(self.buildout)

    def testPartAdded(self):
        buildout = self.buildout
        self.failIf('_mr.developer' in buildout['buildout']['parts'])
        self.extension()
        self.failUnless('_mr.developer' in buildout)
        self.failUnless('_mr.developer' in buildout['buildout']['parts'])

    def testPartExists(self):
        self.buildout._raw['_mr.developer'] = {}
        self.assertRaises(SystemExit, self.extension)

    def testArgsIgnoredIfNotBuildout(self):
        self.extension()
        self.assertEquals(self.extension.get_config().buildout_args, [])

    def testBuildoutArgsSaved(self):
        self.extension.executable = 'buildout'
        self.extension()
        self.failUnless(hasattr(self.extension.get_config(), 'buildout_args'))

    def testAutoCheckout(self):
        self.buildout['sources'].update({
            'pkg.foo': 'svn dummy://pkg.foo',
            'pkg.bar': 'svn dummy://pkg.bar',
        })
        self.buildout['buildout']['auto-checkout'] = 'pkg.foo'
        self.extension()
        wcs = self.extension.get_workingcopies()
        self.assertEquals(len(wcs._events), 1)
        self.assertEquals(wcs._events[0][0], 'checkout')
        self.assertEquals(wcs._events[0][1], ['pkg.foo'])

    def testAutoCheckoutMissingSource(self):
        self.buildout['buildout']['auto-checkout'] = 'pkg.foo'
        self.assertRaises(SystemExit, self.extension.get_auto_checkout)

    def testAutoCheckoutMissingSources(self):
        self.buildout['buildout']['auto-checkout'] = 'pkg.foo pkg.bar'
        self.assertRaises(SystemExit, self.extension.get_auto_checkout)

    def testAutoCheckoutWildcard(self):
        self.buildout['sources'].update({
            'pkg.foo': 'svn dummy://pkg.foo',
            'pkg.bar': 'svn dummy://pkg.bar',
        })
        self.buildout['buildout']['auto-checkout'] = '*'
        self.extension()
        wcs = self.extension.get_workingcopies()
        self.assertEquals(len(wcs._events), 1)
        self.assertEquals(wcs._events[0][0], 'checkout')
        self.assertEquals(wcs._events[0][1], ['pkg.bar', 'pkg.foo'])

    def testRewriteSources(self):
        from mr.developer.common import LegacyRewrite
        self.buildout['sources'].update({
            'pkg.foo': 'svn dummy://pkg.foo',
            'pkg.bar': 'svn baz://pkg.bar',
        })
        self.extension.get_config().rewrites.append(
            LegacyRewrite('dummy://', 'ham://'))
        sources = self.extension.get_sources()
        self.assertEquals(sources['pkg.foo']['url'], 'ham://pkg.foo')
        self.assertEquals(sources['pkg.bar']['url'], 'baz://pkg.bar')

    def _testEmptySourceDefinition(self):
        # TODO handle this case
        self.buildout['sources'].update({
            'pkg.foo': '',
        })
        self.extension.get_sources()

    def _testTooShortSourceDefinition(self):
        # TODO handle this case
        self.buildout['sources'].update({
            'pkg.foo': 'svn',
        })
        self.extension.get_sources()

    def testRepositoryKindChecking(self):
        self.buildout['sources'].update({
            'pkg.bar': 'dummy://foo/trunk svn',
        })
        self.assertRaises(SystemExit, self.extension.get_sources)
        self.buildout['sources'].update({
            'pkg.bar': 'foo dummy://foo/trunk',
        })
        self.assertRaises(SystemExit, self.extension.get_sources)

    def testOldSourcePathParsing(self):
        self.buildout['sources'].update({
            'pkg.bar': 'svn dummy://foo/trunk',
            'pkg.ham': 'git dummy://foo/trunk ham',
            'pkg.baz': 'git dummy://foo/trunk other/baz',
            'pkg.foo': 'git dummy://foo/trunk /foo',
        })
        sources = self.extension.get_sources()
        self.assertEqual(sources['pkg.bar']['path'],
                         os.path.join(os.sep, 'buildout', 'src', 'pkg.bar'))
        self.assertEqual(sources['pkg.ham']['path'],
                         os.path.join(os.sep, 'buildout', 'ham', 'pkg.ham'))
        self.assertEqual(sources['pkg.baz']['path'],
                         os.path.join(os.sep, 'buildout', 'other', 'baz', 'pkg.baz'))
        self.assertEqual(sources['pkg.foo']['path'],
                         os.path.join(os.sep, 'foo', 'pkg.foo'))

    def testSourcePathParsing(self):
        self.buildout['sources'].update({
            'pkg.bar': 'svn dummy://foo/trunk',
            'pkg.ham': 'git dummy://foo/trunk path=ham',
            'pkg.baz': 'git dummy://foo/trunk path=other/baz',
            'pkg.foo': 'git dummy://foo/trunk path=/foo',
        })
        sources = self.extension.get_sources()
        self.assertEqual(sources['pkg.bar']['path'],
                         os.path.join(os.sep, 'buildout', 'src', 'pkg.bar'))
        self.assertEqual(sources['pkg.ham']['path'],
                         os.path.join(os.sep, 'buildout', 'ham', 'pkg.ham'))
        self.assertEqual(sources['pkg.baz']['path'],
                         os.path.join(os.sep, 'buildout', 'other', 'baz', 'pkg.baz'))
        self.assertEqual(sources['pkg.foo']['path'],
                         os.path.join(os.sep, 'foo', 'pkg.foo'))

    def testOptionParsing(self):
        self.buildout['sources'].update({
            'pkg.bar': 'svn dummy://foo/trunk revision=456',
            'pkg.ham': 'git dummy://foo/trunk ham rev=456ad138',
            'pkg.foo': 'git dummy://foo/trunk rev=>=456ad138 branch=blubber',
        })
        sources = self.extension.get_sources()

        self.assertEqual(sorted(sources['pkg.bar'].keys()),
                         ['kind', 'name', 'path', 'revision', 'url'])
        self.assertEqual(sources['pkg.bar']['revision'], '456')

        self.assertEqual(sorted(sources['pkg.ham'].keys()),
                         ['kind', 'name', 'path', 'rev', 'url'])
        self.assertEqual(sources['pkg.ham']['path'],
                         os.path.join(os.sep, 'buildout', 'ham', 'pkg.ham'))
        self.assertEqual(sources['pkg.ham']['rev'], '456ad138')

        self.assertEqual(sorted(sources['pkg.foo'].keys()),
                         ['branch', 'kind', 'name', 'path', 'rev', 'url'])
        self.assertEqual(sources['pkg.foo']['branch'], 'blubber')
        self.assertEqual(sources['pkg.foo']['rev'], '>=456ad138')

    def testOptionParsingBeforeURL(self):
        self.buildout['sources'].update({
            'pkg.bar': 'svn revision=456 dummy://foo/trunk',
            'pkg.ham': 'git rev=456ad138 dummy://foo/trunk ham',
            'pkg.foo': 'git rev=>=456ad138 branch=blubber dummy://foo/trunk',
        })
        sources = self.extension.get_sources()

        self.assertEqual(sorted(sources['pkg.bar'].keys()),
                         ['kind', 'name', 'path', 'revision', 'url'])
        self.assertEqual(sources['pkg.bar']['revision'], '456')

        self.assertEqual(sorted(sources['pkg.ham'].keys()),
                         ['kind', 'name', 'path', 'rev', 'url'])
        self.assertEqual(sources['pkg.ham']['path'],
                         os.path.join(os.sep, 'buildout', 'ham', 'pkg.ham'))
        self.assertEqual(sources['pkg.ham']['rev'], '456ad138')

        self.assertEqual(sorted(sources['pkg.foo'].keys()),
                         ['branch', 'kind', 'name', 'path', 'rev', 'url'])
        self.assertEqual(sources['pkg.foo']['branch'], 'blubber')
        self.assertEqual(sources['pkg.foo']['rev'], '>=456ad138')

    def testDuplicateOptionParsing(self):
        self.buildout['sources'].update({
            'pkg.foo': 'git dummy://foo/trunk rev=456ad138 rev=blubber',
        })
        self.assertRaises(ValueError, self.extension.get_sources)

        self.buildout['sources'].update({
            'pkg.foo': 'git dummy://foo/trunk kind=svn',
        })
        self.assertRaises(ValueError, self.extension.get_sources)

    def testInvalidOptionParsing(self):
        self.buildout['sources'].update({
            'pkg.foo': 'git dummy://foo/trunk rev=456ad138 =foo',
        })
        self.assertRaises(ValueError, self.extension.get_sources)

    def testDevelopHonored(self):
        self.buildout['buildout']['develop'] = '/normal/develop ' \
            '/develop/with/slash/'

        (develop, develeggs, versions) = self.extension.get_develop_info()
        self.failUnless('/normal/develop' in develop)
        self.failUnless('/develop/with/slash/' in develop)
        self.failUnless('slash' in develeggs)
        self.failUnless('develop' in develeggs)
        self.assertEqual(develeggs['slash'], '/develop/with/slash/')
        self.assertEqual(develeggs['develop'], '/normal/develop')

    def testDevelopOrder(self):
        self.buildout['buildout']['develop'] = '/normal/develop ' \
            '/develop/with/slash/'

        (develop, develeggs, versions) = self.extension.get_develop_info()
        assert develop == ['/normal/develop', '/develop/with/slash/']

    def testDevelopSourcesMix(self):
        self.buildout['sources'].update({
            'pkg.bar': 'svn dummy://foo/trunk'})
        self.buildout['buildout']['auto-checkout'] = 'pkg.bar'
        self.buildout['buildout']['develop'] = '/normal/develop ' \
            '/develop/with/slash/'

        _exists = patch('os.path.exists')
        exists = _exists.__enter__()
        try:
            exists().return_value = True
            (develop, develeggs, versions) = self.extension.get_develop_info()
        finally:
            _exists.__exit__()
        assert develop == ['/normal/develop', '/develop/with/slash/', 'src/pkg.bar']


class TestExtension(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.buildout = MockBuildout(dict(
            buildout=dict(
                directory=self.tempdir,
                parts='',
            ),
            sources={},
        ))

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def testConfigCreated(self):
        from mr.developer.extension import extension
        extension(self.buildout)
        self.failUnless('.mr.developer.cfg' in os.listdir(self.tempdir))


class TestSourcesDir(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def test_sources_dir_option_set_if_missing(self):
        buildout = MockBuildout(dict(
            buildout={
                'directory': self.tempdir,
                'parts': '',
            },
            sources={},
        ))
        from mr.developer.extension import Extension
        ext = Extension(buildout)
        self.failIf('sources-dir' in buildout['buildout'])
        ext()
        assert buildout['buildout']['sources-dir'] == os.path.join(
            self.tempdir, 'src')

    def test_sources_dir_created(self):
        buildout = MockBuildout(dict(
            buildout={
                'directory': self.tempdir,
                'parts': '',
                'sources-dir': 'develop',
            },
            sources={},
        ))
        from mr.developer.extension import Extension
        self.failIf('develop' in os.listdir(self.tempdir))
        ext = Extension(buildout)
        ext()
        self.failUnless('develop' in os.listdir(self.tempdir))
        self.assertEqual(ext.get_sources_dir(),
                         os.path.join(self.tempdir, 'develop'))

########NEW FILE########
__FILENAME__ = test_git
import argparse
import os
import sys
import shutil

import pytest
from mock import patch

from mr.developer.extension import Source
from mr.developer.tests.utils import Process, JailSetup


if sys.version_info < (3, 0):
    b = lambda x: x
else:
    b = lambda x: x.encode('ascii')


class MockConfig(object):

    def __init__(self):
        self.develop = {}

    def save(self):
        pass


class MockDevelop(object):

    def __init__(self):
        self.always_accept_server_certificate = True
        self.always_checkout = False
        self.auto_checkout = ''
        self.update_git_submodules = 'always'
        self.sources_dir = ''
        self.develeggs = ''
        self.config = MockConfig()
        self.parser = argparse.ArgumentParser()
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")
        self.threads = 1


class GitTests(JailSetup):

    def setUp(self):
        JailSetup.setUp(self)

    def createRepo(self, repo):
        repository = os.path.join(self.tempdir, repo)
        os.mkdir(repository)
        process = Process(cwd=repository)
        rc, lines = process.popen("git init")
        assert rc == 0
        rc, lines = process.popen('git config user.email "florian.schulze@gmx.net"')
        assert rc == 0
        rc, lines = process.popen('git config user.name "Florian Schulze"')
        assert rc == 0
        return repository

    def testUpdateWithRevisionPin(self):
        from mr.developer.develop import CmdCheckout
        from mr.developer.develop import CmdUpdate
        from mr.developer.develop import CmdStatus
        repository = self.createRepo('repository')
        process = Process(cwd=repository)
        foo = os.path.join(repository, 'foo')
        self.mkfile(foo, 'foo')
        rc, lines = process.popen(
            "git add %s" % foo,
            echo=False)
        assert rc == 0

        rc, lines = process.popen(
            "git commit -m 'Initial'",
            echo=False)
        assert rc == 0

        # create branch for testing
        rc, lines = process.popen(
            "git checkout -b test",
            echo=False)
        assert rc == 0

        foo2 = os.path.join(repository, 'foo2')
        self.mkfile(foo2, 'foo2')
        rc, lines = process.popen(
            "git add %s" % foo2,
            echo=False)
        assert rc == 0

        rc, lines = process.popen(
            "git commit -m foo",
            echo=False)
        assert rc == 0

        # get comitted rev
        rc, lines = process.popen(
            "git log",
            echo=False)
        assert rc == 0
        rev = lines[0].split()[1]

        # return to default branch
        rc, lines = process.popen(
            "git checkout master",
            echo=False)
        assert rc == 0

        bar = os.path.join(repository, 'bar')
        self.mkfile(bar, 'bar')
        rc, lines = process.popen(
            "git add %s" % bar,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "git commit -m bar",
            echo=False)
        assert rc == 0
        src = os.path.join(self.tempdir, 'src')
        os.mkdir(src)
        develop = MockDevelop()
        develop.sources_dir = src

        # check rev
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                rev=rev,
                url='%s' % repository,
                path=os.path.join(src, 'egg'))}
        CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.git', 'foo', 'foo2'))
        CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.git', 'foo', 'foo2'))

        shutil.rmtree(os.path.join(src, 'egg'))

        # check branch
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                branch='test',
                url='%s' % repository,
                path=os.path.join(src, 'egg'))}
        CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.git', 'foo', 'foo2'))
        CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.git', 'foo', 'foo2'))

        CmdStatus(develop)(develop.parser.parse_args(['status']))

        # we can't use both rev and branch
        pytest.raises(SystemExit, """
            develop.sources = {
                'egg': Source(
                    kind='git',
                    name='egg',
                    branch='test',
                    rev=rev,
                    url='%s' % repository,
                    path=os.path.join(src, 'egg-failed'))}
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        """)

    def testUpdateWithoutRevisionPin(self):
        from mr.developer.develop import CmdCheckout
        from mr.developer.develop import CmdUpdate
        repository = self.createRepo('repository')
        process = Process(cwd=repository)
        foo = os.path.join(repository, 'foo')
        self.mkfile(foo, 'foo')
        rc, lines = process.popen(
            "git add %s" % foo,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "git commit %s -m foo" % foo,
            echo=False)
        assert rc == 0
        bar = os.path.join(repository, 'bar')
        self.mkfile(bar, 'bar')
        rc, lines = process.popen(
            "git add %s" % bar,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "git commit %s -m bar" % bar,
            echo=False)
        assert rc == 0
        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % repository,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.git', 'bar', 'foo'))
            CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.git', 'bar', 'foo'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Updated 'egg' with git.",), {})]
        finally:
            _log.__exit__()

########NEW FILE########
__FILENAME__ = test_git_submodules
from mock import patch
from mr.developer.extension import Source
from mr.developer.tests.utils import Process, JailSetup
import argparse
import os


class MockConfig(object):
    def __init__(self):
        self.develop = {}

    def save(self):
        pass


class MockDevelop(object):
    def __init__(self):
        self.always_accept_server_certificate = True
        self.always_checkout = False
        self.update_git_submodules = 'always'
        self.config = MockConfig()
        self.parser = argparse.ArgumentParser()
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")
        self.threads = 1


class GITTests(JailSetup):
    def setUp(self):
        JailSetup.setUp(self)

    # Helpers

    def addFileToRepo(self, repository, fname):
        process = Process(cwd=repository)
        repo_file = os.path.join(repository, fname)
        self.mkfile(repo_file, fname)
        rc, lines = process.popen(
            "git add %s" % repo_file,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "git commit %s -m %s" % (repo_file, fname),
            echo=False)
        assert rc == 0

    def createRepo(self, repo):
        repository = os.path.join(self.tempdir, repo)
        os.mkdir(repository)
        process = Process(cwd=repository)
        rc, lines = process.popen("git init")
        assert rc == 0
        self.gitConfigUser(repo)
        return repository

    def gitConfigUser(self, repo):
        repository = os.path.join(self.tempdir, repo)
        process = Process(cwd=repository)
        rc, lines = process.popen('git config user.email "florian.schulze@gmx.net"')
        assert rc == 0
        rc, lines = process.popen('git config user.name "Florian Schulze"')
        assert rc == 0
        return repository

    def addSubmoduleToRepo(self, repository, submodule_path, submodule_name):
        process = Process(cwd=repository)
        rc, lines = process.popen("git submodule add file:///%s %s" % (submodule_path, submodule_name))
        assert rc == 0
        rc, lines = process.popen("git add .gitmodules")
        assert rc == 0
        rc, lines = process.popen("git add %s" % submodule_name)
        assert rc == 0
        rc, lines = process.popen("git commit -m 'Add submodule %s'" % submodule_name)
    # git subomdule tests

    def testCheckoutWithSubmodule(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
        """
        from mr.developer.develop import CmdCheckout
        submodule_name = 'submodule_a'
        submodule_a = self.createRepo(submodule_name)
        self.addFileToRepo(submodule_a, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule_a, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('.git', 'foo'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {})]
        finally:
            _log.__exit__()

    def testCheckoutWithTwoSubmodules(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a'
            and a submodule 'submodule_b' in it.
        """
        from mr.developer.develop import CmdCheckout
        submodule_name = 'submodule_a'
        submodule = self.createRepo(submodule_name)
        submodule_b_name = 'submodule_b'
        submodule_b = self.createRepo(submodule_b_name)

        self.addFileToRepo(submodule, 'foo')
        self.addFileToRepo(submodule_b, 'foo_b')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule, submodule_name)
        self.addSubmoduleToRepo(egg, submodule_b, submodule_b_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', 'submodule_b', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('.git', 'foo'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_b_name))) == set(('.git', 'foo_b'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_b_name,), {})]
        finally:
            _log.__exit__()

    def testUpdateWithSubmodule(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
            Add a new 'submodule_b' to 'egg' and check it succesfully initializes.
        """
        from mr.developer.develop import CmdCheckout, CmdUpdate
        submodule_name = 'submodule_a'
        submodule = self.createRepo(submodule_name)
        self.addFileToRepo(submodule, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('.git', 'foo'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {})]
        finally:
            _log.__exit__()

        submodule_b_name = 'submodule_b'
        submodule_b = self.createRepo(submodule_b_name)
        self.addFileToRepo(submodule_b, 'foo_b')
        self.addSubmoduleToRepo(egg, submodule_b, submodule_b_name)

        log = _log.__enter__()
        try:
            CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', 'submodule_b', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_b_name))) == set(('.git', 'foo_b'))
            assert log.method_calls == [
                ('info', ("Updated 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_b_name,), {})]
        finally:
            _log.__exit__()

    def testCheckoutWithSubmodulesOptionNever(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
            without initializing the submodule, restricted by global 'never'
        """

        from mr.developer.develop import CmdCheckout
        submodule_name = 'submodule_a'
        submodule_a = self.createRepo(submodule_name)
        self.addFileToRepo(submodule_a, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule_a, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.update_git_submodules = 'never'
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set()
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {})]
        finally:
            _log.__exit__()

    def testCheckoutWithSubmodulesOptionNeverSourceAlways(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
            and a module 'egg2' with the same submodule, initializing only the submodule
            on egg that has the 'always' option
        """

        from mr.developer.develop import CmdCheckout
        submodule_name = 'submodule_a'
        submodule_a = self.createRepo(submodule_name)
        self.addFileToRepo(submodule_a, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule_a, submodule_name)

        egg2 = self.createRepo('egg2')
        self.addFileToRepo(egg2, 'bar')
        self.addSubmoduleToRepo(egg2, submodule_a, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.update_git_submodules = 'never'
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'),
                submodules='always'),
            'egg2': Source(
                kind='git',
                name='egg2',
                url='file:///%s' % egg2,
                path=os.path.join(src, 'egg2'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('foo', '.git'))
            assert set(os.listdir(os.path.join(src, 'egg2'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg2/%s' % submodule_name))) == set()

            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {}),
                ('info', ("Cloned 'egg2' with git.",), {})]
        finally:
            _log.__exit__()

    def testCheckoutWithSubmodulesOptionAlwaysSourceNever(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
            and a module 'egg2' with the same submodule, not initializing the submodule
            on egg2 that has the 'never' option

        """
        from mr.developer.develop import CmdCheckout
        submodule_name = 'submodule_a'
        submodule_a = self.createRepo(submodule_name)
        self.addFileToRepo(submodule_a, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule_a, submodule_name)

        egg2 = self.createRepo('egg2')
        self.addFileToRepo(egg2, 'bar')
        self.addSubmoduleToRepo(egg2, submodule_a, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg')),
            'egg2': Source(
                kind='git',
                name='egg2',
                url='file:///%s' % egg2,
                path=os.path.join(src, 'egg2'),
                submodules='never')}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('foo', '.git'))
            assert set(os.listdir(os.path.join(src, 'egg2'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg2/%s' % submodule_name))) == set()

            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {}),
                ('info', ("Cloned 'egg2' with git.",), {})]
        finally:
            _log.__exit__()

    def testUpdateWithSubmoduleCheckout(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
            Add a new 'submodule_b' to 'egg' and check it doesn't get initialized.
        """
        from mr.developer.develop import CmdCheckout, CmdUpdate
        submodule_name = 'submodule_a'
        submodule = self.createRepo(submodule_name)
        self.addFileToRepo(submodule, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'),
                submodules='checkout')}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('.git', 'foo'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {})]
        finally:
            _log.__exit__()

        submodule_b_name = 'submodule_b'
        submodule_b = self.createRepo(submodule_b_name)
        self.addFileToRepo(submodule_b, 'foo_b')
        self.addSubmoduleToRepo(egg, submodule_b, submodule_b_name)

        log = _log.__enter__()
        try:
            CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', 'submodule_b', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_b_name))) == set()
            assert log.method_calls == [
                ('info', ("Updated 'egg' with git.",), {})]
        finally:
            _log.__exit__()

    def testUpdateWithSubmoduleDontUpdatePreviousSubmodules(self):
        """
            Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
            Commits changes in the detached submodule, and checks update didn't break
            the changes.
        """
        from mr.developer.develop import CmdCheckout, CmdUpdate
        submodule_name = 'submodule_a'
        submodule = self.createRepo(submodule_name)
        self.addFileToRepo(submodule, 'foo')
        egg = self.createRepo('egg')
        self.addFileToRepo(egg, 'bar')
        self.addSubmoduleToRepo(egg, submodule, submodule_name)

        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='git',
                name='egg',
                url='file:///%s' % egg,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.git.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('.git', 'foo'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with git.",), {}),
                ('info', ("Initialized 'egg' submodule at '%s' with git." % submodule_name,), {})]
        finally:
            _log.__exit__()

        self.gitConfigUser(os.path.join(src, 'egg/%s' % submodule_name))
        self.addFileToRepo(os.path.join(src, 'egg/%s' % submodule_name), 'newfile')

        log = _log.__enter__()
        try:
            CmdUpdate(develop)(develop.parser.parse_args(['up', '-f', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('submodule_a', '.git', 'bar', '.gitmodules'))
            assert set(os.listdir(os.path.join(src, 'egg/%s' % submodule_name))) == set(('.git', 'foo', 'newfile'))
            assert log.method_calls == [
                ('info', ("Updated 'egg' with git.",), {})]
        finally:
            _log.__exit__()

########NEW FILE########
__FILENAME__ = test_mercurial
import argparse
import os
import sys

import pytest
from mock import patch

from mr.developer.extension import Source
from mr.developer.tests.utils import Process, JailSetup


if sys.version_info < (3, 0):
    b = lambda x: x
else:
    b = lambda x: x.encode('ascii')


class MockConfig(object):

    def __init__(self):
        self.develop = {}

    def save(self):
        pass


class MockDevelop(object):

    def __init__(self):
        self.always_accept_server_certificate = True
        self.always_checkout = False
        self.update_git_submodules = 'always'
        self.config = MockConfig()
        self.parser = argparse.ArgumentParser()
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")
        self.threads = 1


class MercurialTests(JailSetup):

    def setUp(self):
        JailSetup.setUp(self)

    def testUpdateWithoutRevisionPin(self):
        from mr.developer.develop import CmdCheckout
        from mr.developer.develop import CmdUpdate
        repository = os.path.join(self.tempdir, 'repository')
        os.mkdir(repository)
        process = Process(cwd=repository)
        rc, lines = process.popen(
            "hg init %s" % repository)
        assert rc == 0

        foo = os.path.join(repository, 'foo')
        self.mkfile(foo, 'foo')
        rc, lines = process.popen(
            "hg add %s" % foo,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "hg commit %s -m foo -u test" % foo,
            echo=False)
        assert rc == 0
        bar = os.path.join(repository, 'bar')
        self.mkfile(bar, 'bar')
        rc, lines = process.popen(
            "hg add %s" % bar,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "hg commit %s -m bar -u test" % bar,
            echo=False)
        assert rc == 0
        src = os.path.join(self.tempdir, 'src')
        os.mkdir(src)
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='hg',
                name='egg',
                url='%s' % repository,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.mercurial.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.hg', 'bar', 'foo'))
            CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.hg', 'bar', 'foo'))
            assert log.method_calls == [
                ('info', ("Cloned 'egg' with mercurial.",), {}),
                ('info', ("Updated 'egg' with mercurial.",), {}),
                ('info', ("Switched 'egg' to default.",), {})]
        finally:
            _log.__exit__()

    def testUpdateWithRevisionPin(self):
        from mr.developer.develop import CmdCheckout
        from mr.developer.develop import CmdUpdate
        repository = os.path.join(self.tempdir, 'repository')
        os.mkdir(repository)
        process = Process(cwd=repository)
        rc, lines = process.popen(
            "hg init %s" % repository)
        assert rc == 0
        foo = os.path.join(repository, 'foo')
        self.mkfile(foo, 'foo')
        rc, lines = process.popen(
            "hg add %s" % foo,
            echo=False)
        assert rc == 0

        # create branch for testing
        rc, lines = process.popen(
            "hg branch test",
            echo=False)
        assert rc == 0

        rc, lines = process.popen(
            "hg commit %s -m foo -u test" % foo,
            echo=False)
        assert rc == 0

        # get comitted rev
        rc, lines = process.popen(
            "hg log %s" % foo,
            echo=False)
        assert rc == 0
        rev = lines[0].split()[1].split(b(':'))[1]

        # return to default branch
        rc, lines = process.popen(
            "hg branch default",
            echo=False)
        assert rc == 0

        bar = os.path.join(repository, 'bar')
        self.mkfile(bar, 'bar')
        rc, lines = process.popen(
            "hg add %s" % bar,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "hg commit %s -m bar -u test" % bar,
            echo=False)
        assert rc == 0
        src = os.path.join(self.tempdir, 'src')
        os.mkdir(src)
        develop = MockDevelop()

        # check rev
        develop.sources = {
            'egg': Source(
                kind='hg',
                name='egg',
                rev=rev,
                url='%s' % repository,
                path=os.path.join(src, 'egg'))}
        CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.hg', 'foo'))
        CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.hg', 'foo'))

        # check branch
        develop.sources = {
            'egg': Source(
                kind='hg',
                name='egg',
                branch='test',
                url='%s' % repository,
                path=os.path.join(src, 'egg'))}
        CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.hg', 'foo'))
        CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.hg', 'foo'))

        # we can't use both rev and branch
        pytest.raises(SystemExit, """
            develop.sources = {
                'egg': Source(
                    kind='hg',
                    name='egg',
                    branch='test',
                    rev=rev,
                    url='%s' % repository,
                    path=os.path.join(src, 'egg-failed'))}
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        """)

########NEW FILE########
__FILENAME__ = test_svn
from mock import patch
from mr.developer.extension import Source
from mr.developer.tests.utils import Process, JailSetup
import argparse
import os


class MockConfig(object):
    def __init__(self):
        self.develop = {}

    def save(self):
        pass


class MockDevelop(object):
    def __init__(self):
        self.always_accept_server_certificate = True
        self.always_checkout = False
        self.update_git_submodules = 'always'
        self.config = MockConfig()
        self.parser = argparse.ArgumentParser()
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")
        self.threads = 1


class SVNTests(JailSetup):
    def setUp(self):
        JailSetup.setUp(self)
        from mr.developer.svn import SVNWorkingCopy
        SVNWorkingCopy._clear_caches()

    def testUpdateWithoutRevisionPin(self):
        from mr.developer.develop import CmdCheckout
        from mr.developer.develop import CmdUpdate
        process = Process()
        repository = os.path.join(self.tempdir, 'repository')
        rc, lines = process.popen(
            "svnadmin create %s" % repository)
        assert rc == 0
        checkout = os.path.join(self.tempdir, 'checkout')
        rc, lines = process.popen(
            "svn checkout file://%s %s" % (repository, checkout),
            echo=False)
        assert rc == 0
        foo = os.path.join(checkout, 'foo')
        self.mkfile(foo, 'foo')
        rc, lines = process.popen(
            "svn add %s" % foo,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "svn commit %s -m foo" % foo,
            echo=False)
        assert rc == 0
        bar = os.path.join(checkout, 'bar')
        self.mkfile(bar, 'bar')
        rc, lines = process.popen(
            "svn add %s" % bar,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "svn commit %s -m bar" % bar,
            echo=False)
        assert rc == 0
        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='svn',
                name='egg',
                url='file://%s' % repository,
                path=os.path.join(src, 'egg'))}
        _log = patch('mr.developer.svn.logger')
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.svn', 'bar', 'foo'))
            CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
            assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.svn', 'bar', 'foo'))
            assert log.method_calls == [
                ('info', ("Checked out 'egg' with subversion.",), {}),
                ('info', ("Updated 'egg' with subversion.",), {})]
        finally:
            _log.__exit__()

    def testUpdateWithRevisionPin(self):
        from mr.developer.develop import CmdCheckout
        from mr.developer.develop import CmdUpdate
        process = Process()
        repository = os.path.join(self.tempdir, 'repository')
        rc, lines = process.popen(
            "svnadmin create %s" % repository)
        assert rc == 0
        checkout = os.path.join(self.tempdir, 'checkout')
        rc, lines = process.popen(
            "svn checkout file://%s %s" % (repository, checkout),
            echo=False)
        assert rc == 0
        foo = os.path.join(checkout, 'foo')
        self.mkfile(foo, 'foo')
        rc, lines = process.popen(
            "svn add %s" % foo,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "svn commit %s -m foo" % foo,
            echo=False)
        assert rc == 0
        bar = os.path.join(checkout, 'bar')
        self.mkfile(bar, 'bar')
        rc, lines = process.popen(
            "svn add %s" % bar,
            echo=False)
        assert rc == 0
        rc, lines = process.popen(
            "svn commit %s -m bar" % bar,
            echo=False)
        assert rc == 0
        src = os.path.join(self.tempdir, 'src')
        develop = MockDevelop()
        develop.sources = {
            'egg': Source(
                kind='svn',
                name='egg',
                url='file://%s@1' % repository,
                path=os.path.join(src, 'egg'))}
        CmdCheckout(develop)(develop.parser.parse_args(['co', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.svn', 'foo'))
        CmdUpdate(develop)(develop.parser.parse_args(['up', 'egg']))
        assert set(os.listdir(os.path.join(src, 'egg'))) == set(('.svn', 'foo'))

########NEW FILE########
__FILENAME__ = utils
from subprocess import Popen, PIPE
import os
import shutil
import sys
import tempfile
import threading
import unittest


if sys.version_info < (3, 0):
    b = lambda x: x
    s = lambda x: x
else:
    b = lambda x: x.encode('ascii')
    s = lambda x: x.decode('ascii')


def tee(process, filter_func):
    """Read lines from process.stdout and echo them to sys.stdout.

    Returns a list of lines read. Lines are not newline terminated.

    The 'filter_func' is a callable which is invoked for every line,
    receiving the line as argument. If the filter_func returns True, the
    line is echoed to sys.stdout.
    """
    # We simply use readline here, more fancy IPC is not warranted
    # in the context of this package.
    lines = []
    while True:
        line = process.stdout.readline()
        if line:
            stripped_line = line.rstrip()
            if filter_func(stripped_line):
                sys.stdout.write(s(line))
            lines.append(stripped_line)
        elif process.poll() is not None:
            break
    return lines


def tee2(process, filter_func):
    """Read lines from process.stderr and echo them to sys.stderr.

    The 'filter_func' is a callable which is invoked for every line,
    receiving the line as argument. If the filter_func returns True, the
    line is echoed to sys.stderr.
    """
    while True:
        line = process.stderr.readline()
        if line:
            stripped_line = line.rstrip()
            if filter_func(stripped_line):
                sys.stderr.write(s(line))
        elif process.poll() is not None:
            break


class background_thread(object):
    """Context manager to start and stop a background thread."""

    def __init__(self, target, args):
        self.target = target
        self.args = args

    def __enter__(self):
        self._t = threading.Thread(target=self.target, args=self.args)
        self._t.start()
        return self._t

    def __exit__(self, *ignored):
        self._t.join()


def popen(cmd, echo=True, echo2=True, env=None, cwd=None):
    """Run 'cmd' and return a two-tuple of exit code and lines read.

    If 'echo' is True, the stdout stream is echoed to sys.stdout.
    If 'echo2' is True, the stderr stream is echoed to sys.stderr.

    The 'echo' and 'echo2' arguments may also be callables, in which
    case they are used as tee filters.

    The 'env' argument allows to pass a dict replacing os.environ.

    if 'cwd' is not None, current directory will be changed to cwd before execution.
    """
    if not callable(echo):
        if echo:
            echo = On()
        else:
            echo = Off()

    if not callable(echo2):
        if echo2:
            echo2 = On()
        else:
            echo2 = Off()

    process = Popen(
        cmd,
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
        env=env,
        cwd=cwd
    )

    bt = background_thread(tee2, (process, echo2))
    bt.__enter__()
    try:
        lines = tee(process, echo)
    finally:
        bt.__exit__()
    return process.returncode, lines


class On(object):
    """A tee filter printing all lines."""

    def __call__(self, line):
        return True


class Off(object):
    """A tee filter suppressing all lines."""

    def __call__(self, line):
        return False


class Process(object):
    """Process related functions using the tee module."""

    def __init__(self, quiet=False, env=None, cwd=None):
        self.quiet = quiet
        self.env = env
        self.cwd = cwd

    def popen(self, cmd, echo=True, echo2=True, cwd=None):
        # env *replaces* os.environ
        if self.quiet:
            echo = echo2 = False
        return popen(cmd, echo, echo2, env=self.env, cwd=self.cwd or cwd)

    def pipe(self, cmd):
        rc, lines = self.popen(cmd, echo=False)
        if rc == 0 and lines:
            return lines[0]
        return ''

    def system(self, cmd):
        rc, lines = self.popen(cmd)
        return rc

    def os_system(self, cmd):
        # env *updates* os.environ
        if self.quiet:
            cmd = cmd + ' >%s 2>&1' % os.devnull
        if self.env:
            cmd = ''.join('export %s="%s"\n' % (k, v) for k, v in self.env.items()) + cmd
        return os.system(cmd)


class DirStack(object):
    """Stack of current working directories."""

    def __init__(self):
        self.stack = []

    def __len__(self):
        return len(self.stack)

    def push(self, dir):
        """Push cwd on stack and change to 'dir'.
        """
        self.stack.append(os.getcwd())
        os.chdir(dir)

    def pop(self):
        """Pop dir off stack and change to it.
        """
        if len(self.stack):
            os.chdir(self.stack.pop())


class JailSetup(unittest.TestCase):
    """Manage a temporary working directory."""

    dirstack = None
    tempdir = None

    def setUp(self):
        self.dirstack = DirStack()
        try:
            self.tempdir = os.path.realpath(self.mkdtemp())
            self.dirstack.push(self.tempdir)
        except:
            self.cleanUp()
            raise

    def tearDown(self):
        self.cleanUp()

    def cleanUp(self):
        if self.dirstack is not None:
            while self.dirstack:
                self.dirstack.pop()
        if self.tempdir is not None:
            if os.path.isdir(self.tempdir):
                shutil.rmtree(self.tempdir)

    def mkdtemp(self):
        return tempfile.mkdtemp()

    def mkfile(self, name, body=''):
        f = open(name, 'wt')
        try:
            f.write(body)
        finally:
            f.close()

########NEW FILE########
