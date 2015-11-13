__FILENAME__ = _mypath
import os.path, sys
thisdir = os.path.dirname(__file__)
libdir = os.path.join(thisdir, '..')
libdir = os.path.abspath(libdir)

if libdir not in sys.path:
    sys.path.insert(0, libdir)

########NEW FILE########
__FILENAME__ = build-mechanize
#! /usr/bin/env python
import sys
import pprint
from pony_client import BuildCommand, TestCommand, do, send, \
     TempDirectoryContext, SetupCommand, SvnCheckout, check, parse_cmdline

options, args = parse_cmdline()
if args:
    print 'ignoring command line args: ', args

repo_url = 'http://wwwsearch.sourceforge.net/mechanize/src/mechanize-0.1.11.tar.gz'

python_exe = 'python'
if args:
    python_exe = args[0]

name = 'mechanize'
tags = ['mechanize']
server_url = options.server_url

if not options.force_build:
    if not check(name, server_url, tags=tags):
        print 'check build says no need to build; bye'
        sys.exit(0)

commands = [ SvnCheckout('mechanize', repo_url, name='checkout'),
             BuildCommand([python_exe, 'setup.py', 'test'])
             ]

context = TempDirectoryContext()
results = do(name, commands, context=context)
client_info, reslist, files = results

if options.report:
    print 'result: %s; sending' % (client_info['success'],)
    send(server_url, results, tags=tags)
else:
    print 'build result:'
    pprint.pprint(client_info)
    pprint.pprint(reslist)
    
    print '(NOT SENDING BUILD RESULT TO SERVER)'

if not client_info['success']:
    sys.exit(-1)

########NEW FILE########
__FILENAME__ = pony_client
"""
Client library + simple command-line script for pony-build.

See http://github.com/ctb/pony-build/.
"""

import sys
import subprocess
import xmlrpclib
import tempfile
import shutil
import os, os.path
import time
import urlparse
import urllib
import traceback
from optparse import OptionParser
import pprint
import glob
import datetime
import signal

pb_servers = {
    'pb-dev' : 'http://lyorn.idyll.org/ctb/pb-dev/',
    'local' : 'http://localhost:8000/'
    }
pb_servers['default'] = pb_servers['pb-dev']


###

DEBUG_LEVEL = 5
INFO_LEVEL = 3
WARNING_LEVEL = 2
CRITICAL_LEVEL = 1
_log_level = WARNING_LEVEL

def log_debug(*args):
    log(DEBUG_LEVEL, *args)
    
def log_info(*args):
    log(INFO_LEVEL, *args)

def log_warning(*args):
    log(WARNING_LEVEL, *args)
    
def log_critical(*args):
    log(CRITICAL_LEVEL, *args)

def log(level, *what):
    if level <= _log_level:
        sys.stdout.write(" ".join([ str(x) for x in what]) + "\n")

def set_log_level(level):
    global _log_level
    _log_level = level

###

DEFAULT_CACHE_DIR='~/.pony-build'
def guess_cache_dir(dirname):
    """Return the full path of the VCS cache directory for the given pkg."""
    parent = os.environ.get('PONY_BUILD_CACHE', DEFAULT_CACHE_DIR)
    parent = os.path.expanduser(parent)
    result = os.path.join(parent, dirname)

    return (parent, result)

def create_cache_dir(cache_dir, dirname):
    # trim the pkg name so we can create the main cache_dir and not the 
    # repo dir. I believe it has to be done this way to handle different
    # user PATH setup (OS's, custom stuff etc)

    # @CTB can't we use os.path.split here, instead?
    # @CTB refactor create_cache_dir to check to see if it exists, maybe?
    
    pkglen = len(dirname) 
    cache_dir = cache_dir[:-pkglen]
    
    if os.path.isdir(cache_dir):
        log_info('VCS cache_dir %s exists already!' % cache_dir)
    else:
        try:
            log_info('created new VCS cache dir: %s' % cache_dir)
            os.mkdir(cache_dir)
        except OSError:
            log_critical('Unable to create VCS cache_dir: %s' % cache_dir)
            raise

###

def _replace_variables(cmd, variables_d):
    if cmd.startswith('PB:'):
        cmd = variables_d[cmd[3:]]
    return cmd


def _run_command(command_list, cwd=None, variables=None, extra_kwargs={},
                 verbose=False):

    if variables:
        x = []
        for cmd in command_list:
            cmd = _replace_variables(cmd, variables)
            x.append(cmd)
        command_list = x

    default_kwargs = dict(shell=False, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if extra_kwargs:
        default_kwargs.update(extra_kwargs)

    log_debug('_run_command cwd', os.getcwd())
    log_debug('_run_command running in ->', cwd)
    log_debug('_run_command command list:', command_list)
    log_debug('_run_command default kwargs:', default_kwargs)

    try:
        p = subprocess.Popen(command_list, cwd=cwd, **default_kwargs)

        out, err = p.communicate()
        ret = p.returncode
    except:
        out = ''
        err = traceback.format_exc()
        ret = -1

    log_debug('_run_command status', str(ret))
    log_debug('_run_command stdout', out)
    log_debug('_run_command stderr', err)

    return (ret, out, err)

class FileToUpload(object):
    def __init__(self, filename, location, description, visible):
        """
        filename - name to publish as
        location - full location on build system (not sent to server)
        description - brief description of file/arch for server
        """
        
        self.data = open(location, 'rb').read()
        self.filename = filename
        self.description = description
        self.visible = visible

    def __repr__(self):
        return "<FileToUpload('%s', '%s')>" % (self.filename,
                                               self.description)

class Context(object):
    def __init__(self):
        self.history = []
        self.start_time = self.end_time = None
        self.build_dir = None
        self.files = []

    def initialize(self):
        self.start_time = time.time()

    def finish(self):
        self.end_time = time.time()

    def start_command(self, command):
        if self.build_dir:
            os.chdir(self.build_dir)

    def end_command(self, command):
        self.history.append(command)

    def update_client_info(self, info):
        info['duration'] = self.end_time - self.start_time

    def add_file_to_upload(self, name, location, description, visible):
        o = FileToUpload(name, location, description, visible)
        self.files.append(o)

class TempDirectoryContext(Context):
    def __init__(self, cleanup=True):
        Context.__init__(self)
        self.cleanup = cleanup

    def initialize(self):
        Context.initialize(self)
        self.tempdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()

        log_info('changing to temp directory:', self.tempdir)
        os.chdir(self.tempdir)

    def finish(self):
        os.chdir(self.cwd)
        try:
            Context.finish(self)
        finally:
            if self.cleanup:
                log_info('removing', self.tempdir)
                shutil.rmtree(self.tempdir, ignore_errors=True)

    def update_client_info(self, info):
        Context.update_client_info(self, info)
        info['tempdir'] = self.tempdir

class VirtualenvContext(Context):
    """
    A context that works within a new virtualenv.

    VirtualenvContext works by modifying the path to the Python executable.
    """
    def __init__(self, always_cleanup=True, dependencies=[], optional=[],
                 python='python', include_site_packages=False):
        Context.__init__(self)
        self.cleanup = always_cleanup
        self.dependencies = dependencies
        self.optional = optional        # optional dependencies
        self.python = python

        # Create the virtualenv. Have to do this here so that commands can use
        # VirtualenvContext.python (etc) to get at the right python.
        import virtualenv

        self.tempdir = tempfile.mkdtemp()

        log_info('creating virtualenv')

        cmdlist = list([python, '-m', 'virtualenv'])
        if not include_site_packages:
            cmdlist.append('--no-site-packages')

        cmdlist.append(self.tempdir)

        (ret, out, err) = _run_command(cmdlist)

        if ret != 0:
            raise Exception("error in running virtualenv: %s, %s" % (out, err))

        # calculate where a few things live so we can easily shell out to 'em
        bindir = os.path.join(self.tempdir, 'bin')

        self.python = os.path.join(bindir, 'python')
        self.easy_install = os.path.join(bindir, 'easy_install')
        self.pip = os.path.join(bindir, 'pip')

        os.environ['PATH'] = bindir + os.pathsep + os.environ['PATH']
        log_debug("modified PATH to include virtualenv bindir: '%s'" % bindir)

    def initialize(self):
        Context.initialize(self)
        
        log_info('changing to temp directory:', self.tempdir)
        
        self.cwd = os.getcwd()
        os.chdir(self.tempdir)

        # install pip, then use it to install any packages desired
        log_info('installing pip')

        (ret, out, err) = _run_command([self.easy_install, '-U', 'pip'])
        if ret != 0:
            raise Exception("error in installing pip: %s, %s" % (out, err))
        
        for dep in self.dependencies:
            log_info('installing dependency:', dep)
            (ret, out, err) = _run_command([self.pip, 'install', '-U', '-I',
                                            dep])

            if ret != 0:
                raise Exception("pip cannot install req dependency: %s" % dep)
            
        for dep in self.optional:
            log_info("installing optional dependency:", dep)
            (ret, out, err) = _run_command([self.pip, 'install', '-U', '-I',
                                            dep])

            # @CTB should record failed installs of optional packages
            # to client?
            if ret != 0:
                log_warning("pip cannot install optional dependency: %s" % dep)

    def finish(self):
        os.chdir(self.cwd)
        try:
            Context.finish(self)
        finally:
            if self.cleanup:
                log_info("VirtualenvContext: removing", self.tempdir)
                shutil.rmtree(self.tempdir, ignore_errors=True)

    def update_client_info(self, info):
        Context.update_client_info(self, info)
        info['tempdir'] = self.tempdir
        info['virtualenv'] = True
        info['dependencies'] = self.dependencies
        info['optional'] = self.optional


class UploadAFile(object):
    """
    A build command that arranges to upload a specific file to the server.
    
    @CTB add glob support!
    """
    def __init__(self, filepath, public_name, description, visible=True):
        self.filepath = os.path.realpath(filepath)
        self.public_name = public_name
        self.description = description
        self.visible = visible

    def success(self):
        return os.path.exists(self.filepath)

    def run(self, context):
        context.add_file_to_upload(self.public_name, self.filepath,
                                   self.description, self.visible)

    def get_results(self):
        try:
            filesize = os.path.getsize(self.filepath)
        except OSError:
            filesize = -1

        results = dict(type='file_upload',
                       description=self.description,
                       filesize=filesize,
                       errout="", # @CTB should be unnecessary!
                       status=0) # @CTB should be unnecessary!
        return results

class BaseCommand(object):
    def __init__(self, command_list, name='', run_cwd=None,
                 subprocess_kwargs=None, ignore_failure=False):
        self.command_list = command_list
        if name:
            self.command_name = name
        self.run_cwd = run_cwd

        self.status = None
        self.output = None
        self.errout = None
        self.duration = None

        self.variables = None

        self.subprocess_kwargs = {}
        if subprocess_kwargs:
            self.subprocess_kwargs = dict(subprocess_kwargs)

        self.ignore_failure = ignore_failure

    def __repr__(self):
        return "%s (%s)" % (self.command_name, self.command_type)

    def set_variables(self, v):
        self.variables = dict(v)

    def run(self, context):
        start = time.time()
        (ret, out, err) = _run_command(self.command_list, cwd=self.run_cwd,
                                       variables=self.variables,
                                       extra_kwargs=self.subprocess_kwargs)

        self.status = ret
        self.output = out
        self.errout = err
        end = time.time()

        self.duration = end - start

    def success(self):
        return self.ignore_failure or (self.status == 0)

    def get_results(self):
        results = dict(status=self.status,
                       output=self.output,
                       errout=self.errout,
                       command=str(self.command_list),
                       type=self.command_type,
                       name=self.command_name,
                       duration=self.duration)
        return results

class SetupCommand(BaseCommand):
    command_type = 'setup'
    command_name = 'setup'

class BuildCommand(BaseCommand):
    command_type = 'build'
    command_name = 'build'

class TestCommand(BaseCommand):
    command_type = 'test'
    command_name = 'test'

class CopyLocalDir(BuildCommand):
    def __init__(self, fromdir, to_name):
        self.ignore_failure = False
        self.fromdir = fromdir
        self.to_name = to_name
        self.results_dict = dict(fromdir=fromdir, to_name=to_name)
        
    def run(self, context):
        self.results_dict['out'] = self.results_dict['errout'] = ''

        try:
            shutil.copytree(self.fromdir, self.to_name)
            context.build_dir = os.path.join(os.getcwd(), 'Caper')
            self.status = 0
        except Exception, e:
            self.errout = str(e)
            self.status = 1

    def get_results(self):
        self.results_dict['status'] = self.status
        self.results_dict['type'] = self.command_type
        self.results_dict['name'] = self.command_name

        return self.results_dict
            


class PythonPackageEgg(BaseCommand):
    command_type = 'package'
    command_name = 'package_egg'

    def __init__(self, python_exe='python'):
        BaseCommand.__init__(self, [python_exe, 'setup.py', 'bdist_egg'],
                             name='build an egg')

    def run(self, context):
        BaseCommand.run(self, context)
        if self.status == 0: # success?
            eggfiles = os.path.join('dist', '*.egg')
            eggfiles = glob.glob(eggfiles)

            for filename in eggfiles:
                context.add_file_to_upload(os.path.basename(filename),
                                           filename,
                                           'an egg installation file',
                                           visible=True)

class _VersionControlClientBase(SetupCommand):
    """
    Base class for version control clients.

    Subclasses should define:

      - get_dirname()
      - update_repository()
      - create_repository(url, dirname, step='stepname')
      - record_repository_info(dirname)

    and optionally override 'get_results()'.
    
    """
    
    def __init__(self, use_cache=True, **kwargs):
        SetupCommand.__init__(self, [], **kwargs)
        self.use_cache = use_cache

        self.duration = -1
        self.version_info = ''
        self.results_dict = {}

    def run(self, context):
        # dirname is the directory created by a succesful checkout.
        dirname = self.get_dirname()

        # cwd is the directory we're going to ultimately put dirname under.
        cwd = os.getcwd()

        # NOTE: we flat out don't like the situation where the
        # directory already exists.  Force a clean checkout.
        assert not os.path.exists(dirname)
        
        if self.use_cache:
            # 'repo_dir' is the full cache directory containing the repo.
            # this will be something like '~/.pony-build/<dirname>'.
            #
            # 'cache_dir' is the parent dir.
            
            cache_dir, repo_dir = guess_cache_dir(dirname)
            
            # does the repo already exist?
            if os.path.exists(repo_dir):              # YES
                os.chdir(repo_dir)
                log_info('changed to: ', repo_dir, 'to do fetch.')
                self.update_repository()
            else:                                     # NO
                # do a clone to create the repo dir
                log_info('changing to: ' + cache_dir + ' to make new repo dir')
                os.chdir(cache_dir)

                self.create_repository(self.repository, dirname,
                                       step='create cache')
                assert os.path.isdir(repo_dir)
                
            os.chdir(cwd)

            log_info('Using the local cache at %s for cloning' % repo_dir)
            location = repo_dir
        else:
            location = self.repository

        self.create_repository(location, dirname, step='clone')

        if not os.path.exists(dirname) and os.path.isdir(dirname):
            log_critical('wrong guess; %s does not exist. whoops' % (dirname,))
            raise Exception

        # get some info on what our repository version is
        self.record_repository_info(dirname)
        # record the build directory, too.
        context.build_dir = os.path.join(os.getcwd(), dirname)
        # signal success!
        self.status = 0

    def get_results(self):
        self.results_dict['out'] = self.results_dict['errout'] = ''
        self.results_dict['status'] = self.status
        self.results_dict['type'] = self.command_type
        self.results_dict['name'] = self.command_name

        return self.results_dict

class GitClone(_VersionControlClientBase):
    """Check out and/or update a git repository."""
    
    command_name = 'checkout'

    def __init__(self, repository, branch='master', use_cache=True, **kwargs):
        _VersionControlClientBase.__init__(self, use_cache=use_cache, **kwargs)
        
        self.repository = repository
        self.branch = branch

    def get_dirname(self):
        "Calculate the directory name resulting from a successful checkout."
        p = urlparse.urlparse(self.repository)
        path = p[2]                     # urlparse -> path

        dirname = path.rstrip('/').split('/')[-1]
        if dirname.endswith('.git'):
            dirname = dirname[:-4]
            
        log_info('git checkout dirname guessed as: %s' % (dirname,))
        return dirname

    def update_repository(self):
        branchspec = '%s:%s' % (self.branch, self.branch)
        cmdlist = ['git', 'fetch', '-ufv', self.repository, branchspec]
        print '***', cmdlist
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_update'] = dict(status=ret, output=out,
                                                 errout=err,
                                                 command=str(cmdlist))

        if ret != 0:
            raise Exception("cannot update cache: %s" % repo_dir)

        cmdlist = ['git', 'checkout', '-f', self.branch]
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_checkout_head'] = dict(status=ret, output=out,
                                                        errout=err,
                                                        command=str(cmdlist))

        if ret != 0:
            raise Exception("cannot reset cache: %s" % repo_dir)

    def create_repository(self, url, dirname, step='clone'):
        cmdlist = ['git', 'clone', url]
        (ret, out, err) = _run_command(cmdlist)

       	self.results_dict[step] = dict(status=ret, output=out, errout=err,
                                          command=str(cmdlist))

        if ret != 0:
            cwd = os.getcwd()
            raise Exception("cannot clone repository %s in %s" % (url, cwd))

        if self.branch != 'master':
            # fetch the right branch
            branchspec = '%s:%s' % (self.branch, self.branch)
            cmdlist = ['git', 'fetch', '-ufv', self.repository, branchspec]
            (ret, out, err) = _run_command(cmdlist, dirname)
            assert ret == 0, (out, err)

            # check out the right branch
            cmdlist = ['git', 'checkout', '-f', self.branch]
            (ret, out, err) = _run_command(cmdlist, dirname)
            assert ret == 0, (out, err)

    def record_repository_info(self, repo_dir):
        cmdlist = ['git', 'log', '-1', '--pretty=oneline']
        (ret, out, err) = _run_command(cmdlist, repo_dir)

        assert ret == 0, (cmdlist, ret, out, err)

        self.version_info = out.strip()

    def get_results(self):
        # first, update basic
        _VersionControlClientBase.get_results(self)
        
        self.results_dict['version_type'] = 'git'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info

        self.results_dict['command'] = 'GitClone(%s, %s)' % (self.repository,
                                                             self.branch)

        return self.results_dict

class HgClone(_VersionControlClientBase):
    """Check out or update an Hg (Mercurial) repository."""
    command_name = 'checkout'

    def __init__(self, repository, branch='default', use_cache=True, **kwargs):
        _VersionControlClientBase.__init__(self, use_cache=use_cache, **kwargs)
        self.repository = repository
        self.branch = branch
        assert branch == 'default'

    def get_dirname(self):
        "Calculate the directory name resulting from a successful checkout."
        p = urlparse.urlparse(self.repository)
        path = p[2]                     # urlparse -> path

        dirname = path.rstrip('/').split('/')[-1]
        log_info('hg checkout dirname guessed as: %s' % (dirname,))
        return dirname

    def update_repository(self):
        cmdlist = ['hg', 'pull', self.repository]
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_pull'] = dict(status=ret, output=out,
                                               errout=err,
                                               command=str(cmdlist))

        if ret != 0:
            raise Exception, "cannot pull from %s" % self.repository

        cmdlist = ['hg', 'update', '-C']
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_update'] = \
             dict(status=ret, output=out, errout=err,
                  command=str(cmdlist))

        assert ret == 0, (out, err)

    def create_repository(self, url, dirname, step='clone'):
        cmdlist = ['hg', 'clone', url]
        (ret, out, err) = _run_command(cmdlist)

       	self.results_dict[step] = dict(status=ret, output=out, errout=err,
                                       command=str(cmdlist))

        if ret != 0:
            cwd = os.getcwd()
            raise Exception("cannot clone repository %s in %s" % (url, cwd))

        if self.branch != 'default':
            # update to the right branch
            branchspec = '%s:%s' % (self.branch, self.branch)
            cmdlist = ['hg', 'update', branchspec]
            (ret, out, err) = _run_command(cmdlist, dirname)
            assert ret == 0, (out, err)
            
    def record_repository_info(self, repo_dir):
        # get some info on what our HEAD is
        cmdlist = ['hg', 'id', '-nib']
        (ret, out, err) = _run_command(cmdlist, repo_dir)
        assert ret == 0, (cmdlist, ret, out, err)
        self.version_info = out.strip()

    def get_results(self):
        # first, update basic
        _VersionControlClientBase.get_results(self)
        
        self.results_dict['command'] = 'HgCheckout(%s, %s)' % (self.repository,
                                                               self.branch)
        self.results_dict['version_type'] = 'hg'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info

        return self.results_dict

class SvnCheckout(_VersionControlClientBase):
    """Check out or update a subversion repository."""
    command_name = 'checkout'

    def __init__(self, dirname, repository, use_cache=True, **kwargs):
        _VersionControlClientBase.__init__(self, use_cache=use_cache)
        
        self.dirname = dirname
        self.repository = repository

    def get_dirname(self):
        return self.dirname

    def update_repository(self):
        # adding '--accept', 'theirs-full' is a good idea for newer versions
        # of svn; this automatically accepts dodgy security certs.
        cmdlist = ['svn', 'update']
        
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['svn update'] = dict(status=ret, output=out,
                                               errout=err,
                                               command=str(cmdlist))

        if ret != 0:
            log_critical("cannot svn update")
            raise Exception, (cmdlist, ret, out, err)

    def create_repository(self, url, dirname, step='clone'):
        if os.path.isdir(url):          # local dir? COPY.
            shutil.copytree(url, dirname)
        else:                           # remote repo? CO.
            cmdlist = ['svn', 'co', url, dirname]
            (ret, out, err) = _run_command(cmdlist)

            self.results_dict[step] = dict(status=ret, output=out, errout=err,
                                           command=str(cmdlist))

            if ret != 0:
                log_critical("cannot svn checkout %s into %s" % (url, dirname))
                raise Exception, "cannot svn checkout %s into %s" % (url, dirname)

    def record_repository_info(self, repo_dir):
        cmdlist = ['svnversion']
        (ret, out, err) = _run_command(cmdlist, repo_dir)
        assert ret == 0, (cmdlist, ret, out, err)
        self.version_info = out.strip()

    def get_results(self):
        # first, update basic
        _VersionControlClientBase.get_results(self)
        
        self.results_dict['command'] = 'SvnCheckout(%s, %s)' %(self.repository,
                                                               self.dirname)
        self.results_dict['version_type'] = 'hg'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info

        return self.results_dict

###

def get_hostname():
    import socket
    return socket.gethostname()

def get_arch():
    import distutils.util
    return distutils.util.get_platform()

###

def _send(server, info, results):
    log_info('connecting to', server)
    s = xmlrpclib.ServerProxy(server, allow_none=True)
    (result_key, auth_key) = s.add_results(info, results)
    return str(auth_key)

def _upload_file(server_url, fileobj, auth_key):
    # @CTB make sure files can't be uploaded from elsewhere on system?

    # @CTB hack hack
    assert server_url.endswith('xmlrpc')
    upload_url = server_url[:-6] + 'upload'

    if fileobj.visible:
        visible='yes'
    else:
        visible = 'no'

    qs = urllib.urlencode(dict(description=fileobj.description,
                               filename=fileobj.filename,
                               auth_key=str(auth_key),
                               visible=visible))
    upload_url += '?' + qs

    try:
        http_result = urllib.urlopen(upload_url, fileobj.data)
    except:
        log_warning('file upload failed:', str(fileobj))
        log_warning(traceback.format_exc())

def do(name, commands, context=None, arch=None, stop_if_failure=True):
    reslist = []
    init_status = True
    
    if context:
        try:
            context.initialize()
        except:
            init_status = False

    if init_status:
        for c in commands:
            log_debug('running:', str(c))
            if context:
                context.start_command(c)
            try:
                c.run(context)
            except:
                break
            if context:
                context.end_command(c)

            reslist.append(c.get_results())
        
            if stop_if_failure and not c.success():
                break

    if context:
        context.finish()

    if arch is None:
        arch = get_arch()

    success = True
    for c in commands:
        if not c.success():
            success = False
            break

    client_info = dict(package=name, arch=arch, success=success)
    files_to_upload = None

    if context:
        context.update_client_info(client_info)

        if context.files:
            files_to_upload = context.files

    return (client_info, reslist, files_to_upload)

def send(server_url, x, hostname=None, tags=()):
    client_info, reslist, files_to_upload = x
    if hostname is None:
        import socket
        hostname = socket.gethostname()

    client_info['host'] = hostname
    client_info['tags'] = tags

    server_url = get_server_url(server_url)
    log_info('using server URL:', server_url)
    auth_key = _send(server_url, client_info, reslist)

    if files_to_upload:
        for fileobj in files_to_upload:
            log_debug('uploading', str(fileobj))
            _upload_file(server_url, fileobj, auth_key)

def check(name, server_url, tags=(), hostname=None, arch=None, reserve_time=0):
    import socket
    
    if hostname is None:
        hostname = get_hostname()

    if arch is None:
        arch = get_arch()

    client_info = dict(package=name, host=hostname, arch=arch, tags=tags)
    server_url = get_server_url(server_url)
    s = xmlrpclib.ServerProxy(server_url, allow_none=True)
    try:
        (flag, reason) = s.check_should_build(client_info, True, reserve_time)
    except socket.error:
        log_critical('cannot connect to pony-build server: %s' % server_url)
        sys.exit(-1)
        
    return flag

def get_server_url(server_name):
    try_url = urlparse.urlparse(server_name)
    if try_url[0]:                      # urlparse -> scheme
        server_url = urlparse.urljoin(server_name, 'xmlrpc')
    else: # not a URL?
        server_temp = pb_servers[server_name]
        server_url = urlparse.urljoin(server_temp, 'xmlrpc')
    return server_url

def get_tagsets_for_package(server, package):
    server = get_server_url(server)
    s = xmlrpclib.ServerProxy(server, allow_none=True)
    return s.get_tagsets_for_package(package)

###

def parse_cmdline(argv=[]):
    cmdline = OptionParser()
    cmdline.add_option('-f', '--force-build', dest='force_build',
                       action='store_true', default=False,
                       help="run a build whether or not it's stale")

    cmdline.add_option('-n', '--no-report', dest='report',
                       action='store_false', default=True,
                       help="do not report build results to server")

    cmdline.add_option('-N', '--no-clean-temp', dest='cleanup_temp',
                       action='store_false', default=True,
                       help='do not clean up the temp directory')

    cmdline.add_option('-s', '--server-url', dest='server_url',
                       action='store', default='pb-dev',
                       help='set pony-build server URL for reporting results')

    cmdline.add_option('-v', '--verbose', dest='verbose',
                       action='store_true', default=False,
                       help='set verbose reporting')
                       
    cmdline.add_option('--debug', dest='debug',
                       action='store_true', default=False,
                       help='set debug reporting')
                       
    cmdline.add_option('-e', '--python-executable', dest='python_executable',
                       action='store', default='python',
                       help='override the version of python used to build with')
                       
    cmdline.add_option('-t', '--tagset', dest='tagset',
                       action='store', default=[],
                       help='comma-delimited list of tags to be applied')

    if not argv:
        (options, args) = cmdline.parse_args()
    else:
        (options, args) = cmdline.parse_args(argv)
        
    # parse the tagset
    if options.tagset:
        options.tagset = options.tagset.split(',')
        
    # there should be nothing in args.
    # if there is, print a warning, then crash and burn.
    #if args:
    #    print "Error--unknown arguments detected.  Failing..."
    #    sys.exit(0)

    if options.verbose:
        set_log_level(INFO_LEVEL)

    if options.debug:
        set_log_level(DEBUG_LEVEL)

    if not options.report:
        options.force_build = True

    return options, args


###

class PythonVersionNotFound(Exception):
    def __init__(self, python_exe):
        self.python_exe = python_exe
    def __str__(self):
        return repr(self.python_exe + " not found on system.")


def get_python_version(python_exe='python'):
    """
    Return the major.minor number for the given Python executable.
    """
    
    cmd = python_exe + " -c \"import sys \nprint" \
    " str(sys.version_info[0]) + '.' + str(sys.version_info[1])\""
    
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    
    if not stdout:
        raise PythonVersionNotFound(python_exe)
    
    return stdout.strip()

###

def get_python_config(options, args):
    if not len(args):
        python_ver = 'python2.5'
    else:
        python_ver = args[0]
        print 'setting python version:', python_ver

    tags = [python_ver]

    if len(args) > 1:
        tags.extend(args[1:])

    return dict(python_exe=python_ver, tags=tags)

# PYTHON: generic recipe elements
PYTHON_EXE = 'PB:python_exe'

PythonBuild = BuildCommand([PYTHON_EXE, 'setup.py', 'build'])
PythonBuildInPlace = BuildCommand([PYTHON_EXE, 'setup.py', 'build_ext', '-i'])
PythonTest = TestCommand([PYTHON_EXE, 'setup.py', 'test'])
Python_package_egg = PythonPackageEgg(PYTHON_EXE)

recipes = {
    'pony-build' : (get_python_config,
                    [ GitClone('git://github.com/ctb/pony-build.git'),
                      PythonBuild,
                      PythonTest,
                      Python_package_egg
             ]),
    'scikits.image' : (get_python_config,
                       [ GitClone('git://github.com/stefanv/scikits.image.git'),
                         PythonBuild,
                         PythonTest,
                         Python_package_egg
             ]),
    'twill' : (get_python_config,
               [ SvnCheckout('twill', 'http://twill.googlecode.com/svn/branches/0.9.2-dev/twill', cache_dir='~/.pony-build/twill'),
                 PythonBuild,
                 PythonTest
             ]),
    }

###

if __name__ == '__main__':
    options, args = parse_cmdline()

    package = args[0]
    (config_fn, recipe) = recipes[package]
    variables = config_fn(options, args[1:])

    tags = variables['tags']

    for r in recipe:
        r.set_variables(variables)

    ###

    server_url = options.server_url

    if not options.force_build:
        if not check(package, server_url, tags=tags):
            print 'check build says no need to build; bye'
            sys.exit(0)

    context = TempDirectoryContext()
    results = do(package, recipe, context=context, stop_if_failure=False)
    client_info, reslist, files_list = results

    if options.report:
        print 'result: %s; sending' % (client_info['success'],)
        send(server_url, results, tags=tags)
    else:
        print 'build result:'
        pprint.pprint(client_info)
        pprint.pprint(reslist)

        print '(NOT SENDING BUILD RESULT TO SERVER)'

    if not client_info['success']:
        print 'build failed.'
        sys.exit(-1)

    print 'build succeeded.'
    sys.exit(0)

########NEW FILE########
__FILENAME__ = test_context
import os
from pony_client import Context, BaseCommand, do, TempDirectoryContext
import pony_client

class StubCommand(BaseCommand):
    command_name = 'test command'
    def __init__(self):
        BaseCommand.__init__(self, [])

    def run(self, context):
        self.output = 'some output'
        self.errout = 'some errout'
        self.duration = 0.

class SuccessfulCommand(StubCommand):
    command_type = 'forced_success'
    def run(self, context):
        self.status = 0

class FailedCommand(StubCommand):
    command_type = 'forced_failure'
    def run(self, context):
        self.status = -1
        
class ExceptedCommand(StubCommand):
    command_type = 'forced_exception'
    def run(self, context):
        raise Exception("I suck")

class FailedContextInit(Context):
    def __init__(self, *args, **kwargs):
        Context.__init__(self, *args, **kwargs)
    def initialize(self):
        Context.initialize(self)
        raise Exception("I suck too")

def test_successful_command():
    c = Context()

    (client_info, _, _) = do('foo', [ SuccessfulCommand() ], context=c)
    assert client_info['success']

def test_context_failure():
    c = FailedContextInit()

    (client_info, _, _) = do('foo', [ SuccessfulCommand() ], context=c)
    assert not client_info['success']

def test_failed_command():
    c = Context()

    (client_info, _, _) = do('foo', [ FailedCommand() ], context=c)
    assert not client_info['success']

def test_exception_command():
    c = Context()

    (client_info, _, _) = do('foo', [ ExceptedCommand() ], context=c)
    assert not client_info['success']

def test_misc_TempDirectoryContext_things():

    c = TempDirectoryContext()

    c.initialize()
    # test for temp folder creation
    assert os.path.exists(c.tempdir)

    c.finish()
    # test for temp folder proper deletion
    assert not os.path.exists(c.tempdir)

########NEW FILE########
__FILENAME__ = test_git_client
"""
git VCS client tests.

TODO:
 - test different branches
"""
import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import GitClone, TempDirectoryContext, _run_command

_cwd = None
def setup():
    global _cwd
    _cwd = os.getcwd()

def teardown():
    os.chdir(_cwd)

class Test_GitNonCachingCheckout(object):
    repository_url = 'http://github.com/ctb/pony-build-git-test.git'

    def setup(self):
        # create a context within which to run the GitClone command
        self.context = TempDirectoryContext()
        self.context.initialize()

    def teardown(self):
        self.context.finish()

    def test_basic(self):
        "Run the GitClone command w/o caching and verify it."
        command = GitClone(self.repository_url, use_cache=False)
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
c57591d8cc9ef3c293a2006416a0bb8b2ffed26d secondary commit"""
        assert results_info['version_type'] == 'git'

        # check files
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-git-test', 'test2'))
        
    def test_other_branch(self):
        "Run the GitClone command for another branch."
        
        command = GitClone(self.repository_url, branch='other',
                           use_cache=False)
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
7f8a8e130a3cc631752e275ea57220a1b6e2dddb look ma, another branch\\!"""
        assert results_info['version_type'] == 'git'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert not os.path.exists(os.path.join('pony-build-git-test',
                                                   'test2'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test3'))
        finally:
            os.chdir(cwd)


def create_cache_location(repository_url):
    # use os.environ to specify a new place for VCS cache stuff
    temp_cache_parent = tempfile.mkdtemp()
    temp_cache_location = os.path.join(temp_cache_parent, "the_cache")
    os.environ['PONY_BUILD_CACHE'] = temp_cache_location

    # figure out what the end checkout result should be
    repository_path = urlparse.urlparse(repository_url)[2]
    repository_dirname = repository_path.rstrip('/').split('/')[-1]

    print 'calculated repository dirname as:', repository_dirname

    (_, repository_cache) = pony_client.guess_cache_dir(repository_dirname)
    assert repository_cache.startswith(temp_cache_location)

    # this will create 'the_cache' directory that contains individual
    # pkg caches.
    pony_client.create_cache_dir(repository_cache, repository_dirname)
    assert os.path.isdir(temp_cache_location)

    return (temp_cache_parent, temp_cache_location)


class Test_GitCachingCheckout(object):
    repository_url = 'http://github.com/ctb/pony-build-git-test.git'

    def setup(self):
        # create a context within which to run the GitClone command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the GitClone command and verify that it produces the right repo."
        command = GitClone(self.repository_url)
        command.run(self.context)

        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
c57591d8cc9ef3c293a2006416a0bb8b2ffed26d secondary commit"""
        assert results_info['version_type'] == 'git'

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test2'))
        finally:
            os.chdir(cwd)

    def test_other_branch(self):
        "Run the GitClone command for another branch."
        
        command = GitClone(self.repository_url, branch='other')
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
7f8a8e130a3cc631752e275ea57220a1b6e2dddb look ma, another branch\\!"""
        assert results_info['version_type'] == 'git'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert not os.path.exists(os.path.join('pony-build-git-test',
                                                   'test2'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test3'))
        finally:
            os.chdir(cwd)


class Test_GitCachingUpdate(object):
    repository_url = 'http://github.com/ctb/pony-build-git-test.git'

    def setup(self):
        # create a context within which to run the GitClone command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

        cwd = os.getcwd()                       # save current directory

        #
        # next, we want to set up the cached repository so that it contains an
        # old checkout.
        #
        
        os.chdir(cache_dir)

        # now, check out the test git repository.
        (ret, out, err) = _run_command(['git', 'clone', self.repository_url])
        assert ret == 0, (out, err)

        # forcibly check out the first revision, instead of the second.
        (ret, out, err) = _run_command(['git', 'checkout', '0a59ded1fc'],
                                       cwd='pony-build-git-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
        assert not os.path.exists(os.path.join('pony-build-git-test', 'test2'))

        os.chdir(cwd)                           # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the GitClone command and verify that it produces an updated repo."
        command = GitClone(self.repository_url)
        command.run(self.context)

        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
c57591d8cc9ef3c293a2006416a0bb8b2ffed26d secondary commit"""
        assert results_info['version_type'] == 'git'

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test2'))
        finally:
            os.chdir(cwd)
        
    def test_other_branch(self):
        "Run the GitClone command for another branch."
        
        command = GitClone(self.repository_url, branch='other')
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
7f8a8e130a3cc631752e275ea57220a1b6e2dddb look ma, another branch\\!"""
        assert results_info['version_type'] == 'git'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert not os.path.exists(os.path.join('pony-build-git-test',
                                                   'test2'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test3'))
        finally:
            os.chdir(cwd)

########NEW FILE########
__FILENAME__ = test_hg_client
import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse
 
import pony_client
from pony_client import HgClone, TempDirectoryContext, _run_command
 
_cwd = None
def setup():
    global _cwd
    _cwd = os.getcwd()
 
def teardown():
    os.chdir(_cwd)
 
class Test_MercurialNonCachingCheckout(object):
    repository_url = 'http://bitbucket.org/cherkf/pony-build-hg-test/'
 
    def setup(self):
        # create a context within which to run the HgClone command
        self.context = TempDirectoryContext()
        self.context.initialize()
 
    def teardown(self):
        self.context.finish()
 
    def test_basic(self):
        "Run the HgClone command w/o caching and verify it."
        command = HgClone(self.repository_url, use_cache=False)
        command.verbose = True
        command.run(self.context)
 
        pprint.pprint(command.get_results()) # debugging output
 
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))
 
 
def create_cache_location(repository_url):
    # use os.environ to specify a new place for VCS cache stuff
    temp_cache_parent = tempfile.mkdtemp()
    temp_cache_location = os.path.join(temp_cache_parent, "the_cache")
    os.environ['PONY_BUILD_CACHE'] = temp_cache_location
 
    # figure out what the end checkout result should be
    repository_path = urlparse.urlparse(repository_url)[2]
    repository_dirname = repository_path.rstrip('/').split('/')[-1]
 
    print 'calculated repository dirname as:', repository_dirname
 
    (_, repository_cache) = pony_client.guess_cache_dir(repository_dirname)
    assert repository_cache.startswith(temp_cache_location)
 
    # this will create 'the_cache' directory that contains individual
    # pkg caches.
    pony_client.create_cache_dir(repository_cache, repository_dirname)
    assert os.path.isdir(temp_cache_location)
 
    return (temp_cache_parent, temp_cache_location)
 
 
class Test_MercurialCachingCheckout(object):
    repository_url = 'http://bitbucket.org/cherkf/pony-build-hg-test/'
 
    def setup(self):
        # create a context within which to run the HgClone command
        self.context = TempDirectoryContext()
        self.context.initialize()
 
        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent
 
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']
 
        shutil.rmtree(self.cache_parent)
 
    def test_basic(self):
        "Run the HgClone command and verify that it produces the right repo."
        command = HgClone(self.repository_url)
        command.verbose = True
        command.run(self.context)
 
        pprint.pprint(command.get_results()) # debugging output
 
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))
        
    def test_other_branch(self):
        "Run the HgClone command for another branch."
         
        command = HgClone('http://bitbucket.org/cherkf/pony-build-hg-test/')
        command.run(self.context)
        #commands.getoutput('hg', 'update', 'extrabranch')
        
        #pprint.pprint(cmdlist.get_results()) #debugging output

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == '949a4d660f2e 2 default'
        assert results_info['version_type'] == 'hg'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
            assert  os.path.exists(os.path.join('pony-build-hg-test',
                                                   'test2'))
          #  assert os.path.exists(os.path.join('pony-build-hg-test', 'test4'))
        finally:
            os.chdir(cwd)
 
 
class Test_MercurialCachingUpdate(object):
    repository_url = 'http://bitbucket.org/cherkf/pony-build-hg-test/'
 
    def setup(self):
        # create a context within which to run the HgClone command
        self.context = TempDirectoryContext()
        self.context.initialize()
 
        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent
 
        cwd = os.getcwd() # save current directory
 
        #
        # next, we want to set up the cached repository so that it contains an
        # old checkout.
        #
        
        os.chdir(cache_dir)
 
        # now, check out the test hg repository.
        (ret, out, err) = _run_command(['hg', 'clone', self.repository_url])
        assert ret == 0, (out, err)
 
        # forcibly check out revision 7 instead of revision 1.
        (ret, out, err) = _run_command(['hg', 'checkout', '7'],
                                       cwd='pony-build-hg-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert  os.path.exists(os.path.join('pony-build-hg-test', 'test4.py'))
 
        os.chdir(cwd) # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']
 
        shutil.rmtree(self.cache_parent)
 
    def test_basic(self):
        "Run the HgClone command and verify that it produces an updated repo."
        command = HgClone(self.repository_url)
        command.verbose = True
        command.run(self.context)
 
        pprint.pprint(command.get_results()) # debugging output
 
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))
    def test_other_branch(self):
        "Run the HgClone command for another branch."
        
        command = HgClone(self.repository_url)
        command.run(self.context)
         # forcibly check out revision 7 instead of revision 1.
        (ret, out, err) = _run_command(['hg', 'checkout', '7'],
                                       cwd='pony-build-hg-test')
        (ret, out, err) = _run_command(['hg', 'identify'],
                                       cwd='pony-build-hg-test')
 
        #os.chdir(cwd) # return to working dir.
        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == '949a4d660f2e 2 default'
        assert results_info['version_type'] == 'hg'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
             assert ret == 0, (out, err)
             assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
             assert os.path.exists(os.path.join('pony-build-hg-test',
                                                   'test2'))
             assert os.path.exists(os.path.join('pony-build-hg-test', 'test4.py'))
        finally:
            os.chdir(cwd)
 
        
 

########NEW FILE########
__FILENAME__ = test_misc
import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import HgClone, TempDirectoryContext, _run_command

def test_create_cache_dir():
    """
    Test to make sure that create_cache_dir() does the right path calculation.
    """
    
    # build a fake cache_dir location
    tempdir = tempfile.mkdtemp()
    fake_dir = os.path.join(tempdir, 'CACHE_DIR')
    fake_pkg = os.path.join(fake_dir, 'SOME_PACKAGE')
    
    # use dependency injection to replace 'os.path.isdir' and 'os.mkdir'
    # in order to test create_cache_dir.
    def false(X):
        return False

    def noop(Y, expected_dirname=fake_dir):
        print 'NOOP GOT', Y
        Y = Y.rstrip(os.path.sep)
        expected_dirname = expected_dirname.rstrip(os.path.sep)
        
        assert Y == expected_dirname, \
               'fake mkdir got %s, expected %s' % (Y, expected_dirname)

    # replace stdlib functions
    _old_isdir, os.path.isdir = os.path.isdir, false
    _old_mkdir, os.mkdir = os.mkdir, noop

    try:
        pony_client.create_cache_dir(fake_pkg, 'SOME_PACKAGE')
        # here, the 'noop' function is actually doing the test.
    finally:
        # put stdlib functions back
        os.path.isdir, os.mkdir = _old_isdir, _old_mkdir
        shutil.rmtree(tempdir)

########NEW FILE########
__FILENAME__ = test_svn_client
"""
svn VCS client tests.
"""
import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import SvnCheckout, TempDirectoryContext, _run_command

_cwd = None
def setup():
    global _cwd
    _cwd = os.getcwd()

def teardown():
    os.chdir(_cwd)

class Test_SvnNonCachingCheckout(object):
    repository_url = 'http://pony-build.googlecode.com/svn/pony-build-svn-test'

    def setup(self):
        # create a context within which to run the SvnCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

    def teardown(self):
        self.context.finish()

    def test_basic(self):
        "Run the SvnCheckout command w/o caching and verify it."
        command = SvnCheckout('pony-build-svn-test', self.repository_url,
                              use_cache=False)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-svn-test', 'test2'))


def create_cache_location(repository_url):
    # use os.environ to specify a new place for VCS cache stuff
    temp_cache_parent = tempfile.mkdtemp()
    temp_cache_location = os.path.join(temp_cache_parent, "the_cache")
    os.environ['PONY_BUILD_CACHE'] = temp_cache_location

    # figure out what the end checkout result should be
    repository_path = urlparse.urlparse(repository_url)[2]
    repository_dirname = repository_path.rstrip('/').split('/')[-1]

    print 'calculated repository dirname as:', repository_dirname

    (_, repository_cache) = pony_client.guess_cache_dir(repository_dirname)
    assert repository_cache.startswith(temp_cache_location)

    # this will create 'the_cache' directory that contains individual
    # pkg caches.
    pony_client.create_cache_dir(repository_cache, repository_dirname)
    assert os.path.isdir(temp_cache_location)

    return (temp_cache_parent, temp_cache_location)


class Test_SvnCachingCheckout(object):
    repository_url = 'http://pony-build.googlecode.com/svn/pony-build-svn-test'

    def setup(self):
        # create a context within which to run the SvnCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the SvnCheckout command and verify that it works."
        command = SvnCheckout('pony-build-svn-test', self.repository_url)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test2'))
        finally:
            os.chdir(cwd)


class Test_SvnCachingUpdate(object):
    repository_url = 'http://pony-build.googlecode.com/svn/pony-build-svn-test'

    def setup(self):
        # create a context within which to run the SvnCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

        cwd = os.getcwd()                       # save current directory

        #
        # next, we want to set up the cached repository so that it contains an
        # old checkout.
        #
        
        os.chdir(cache_dir)

        # now, check out the test svn repository.
        (ret, out, err) = _run_command(['svn', 'checkout',
                                        self.repository_url,
                                        'pony-build-svn-test'])
        assert ret == 0, (out, err)

        # forcibly check out the first revision, instead of the second.
        (ret, out, err) = _run_command(['svn', 'update', '-r2'],
                                       cwd='pony-build-svn-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
        assert not os.path.exists(os.path.join('pony-build-svn-test', 'test2'))

        os.chdir(cwd)                           # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the SvnCheckout command and verify that it updates right."
        command = SvnCheckout('pony-build-svn-test', self.repository_url)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test2'))
        finally:
            os.chdir(cwd)
        

        
                   

########NEW FILE########
__FILENAME__ = test-post-github-notify
#! /usr/bin/env python
import sys
import httplib
from urlparse import urlparse
import urllib

url = sys.argv[1]

package = open('github-notify.json').read()
d = dict(payload=package)

print urllib.urlencode(d)

print urllib.urlopen(url, urllib.urlencode(d)).read()

########NEW FILE########
__FILENAME__ = feedparser
#!/usr/bin/env python
"""Universal feed parser

Handles RSS 0.9x, RSS 1.0, RSS 2.0, CDF, Atom 0.3, and Atom 1.0 feeds

Visit http://feedparser.org/ for the latest version
Visit http://feedparser.org/docs/ for the latest documentation

Required: Python 2.1 or later
Recommended: Python 2.3 or later
Recommended: CJKCodecs and iconv_codec <http://cjkpython.i18n.org/>
"""

__version__ = "4.1"# + "$Revision: 1.92 $"[11:15] + "-cvs"
__license__ = """Copyright (c) 2002-2006, Mark Pilgrim, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""
__author__ = "Mark Pilgrim <http://diveintomark.org/>"
__contributors__ = ["Jason Diamond <http://injektilo.org/>",
                    "John Beimler <http://john.beimler.org/>",
                    "Fazal Majid <http://www.majid.info/mylos/weblog/>",
                    "Aaron Swartz <http://aaronsw.com/>",
                    "Kevin Marks <http://epeus.blogspot.com/>"]
_debug = 0

# HTTP "User-Agent" header to send to servers when downloading feeds.
# If you are embedding feedparser in a larger application, you should
# change this to your application name and URL.
USER_AGENT = "UniversalFeedParser/%s +http://feedparser.org/" % __version__

# HTTP "Accept" header to send to servers when downloading feeds.  If you don't
# want to send an Accept header, set this to None.
ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

# List of preferred XML parsers, by SAX driver name.  These will be tried first,
# but if they're not installed, Python will keep searching through its own list
# of pre-installed parsers until it finds one that supports everything we need.
PREFERRED_XML_PARSERS = ["drv_libxml2"]

# If you want feedparser to automatically run HTML markup through HTML Tidy, set
# this to 1.  Requires mxTidy <http://www.egenix.com/files/python/mxTidy.html>
# or utidylib <http://utidylib.berlios.de/>.
TIDY_MARKUP = 0

# List of Python interfaces for HTML Tidy, in order of preference.  Only useful
# if TIDY_MARKUP = 1
PREFERRED_TIDY_INTERFACES = ["uTidy", "mxTidy"]

# ---------- required modules (should come with any Python distribution) ----------
import sgmllib, re, sys, copy, urlparse, time, rfc822, types, cgi, urllib, urllib2
try:
    from cStringIO import StringIO as _StringIO
except:
    from StringIO import StringIO as _StringIO

# ---------- optional modules (feedparser will work without these, but with reduced functionality) ----------

# gzip is included with most Python distributions, but may not be available if you compiled your own
try:
    import gzip
except:
    gzip = None
try:
    import zlib
except:
    zlib = None

# If a real XML parser is available, feedparser will attempt to use it.  feedparser has
# been tested with the built-in SAX parser, PyXML, and libxml2.  On platforms where the
# Python distribution does not come with an XML parser (such as Mac OS X 10.2 and some
# versions of FreeBSD), feedparser will quietly fall back on regex-based parsing.
try:
    import xml.sax
    xml.sax.make_parser(PREFERRED_XML_PARSERS) # test for valid parsers
    from xml.sax.saxutils import escape as _xmlescape
    _XML_AVAILABLE = 1
except:
    _XML_AVAILABLE = 0
    def _xmlescape(data):
        data = data.replace('&', '&amp;')
        data = data.replace('>', '&gt;')
        data = data.replace('<', '&lt;')
        return data

# base64 support for Atom feeds that contain embedded binary data
try:
    import base64, binascii
except:
    base64 = binascii = None

# cjkcodecs and iconv_codec provide support for more character encodings.
# Both are available from http://cjkpython.i18n.org/
try:
    import cjkcodecs.aliases
except:
    pass
try:
    import iconv_codec
except:
    pass

# chardet library auto-detects character encodings
# Download from http://chardet.feedparser.org/
try:
    import chardet
    if _debug:
        import chardet.constants
        chardet.constants._debug = 1
except:
    chardet = None

# ---------- don't touch these ----------
class ThingsNobodyCaresAboutButMe(Exception): pass
class CharacterEncodingOverride(ThingsNobodyCaresAboutButMe): pass
class CharacterEncodingUnknown(ThingsNobodyCaresAboutButMe): pass
class NonXMLContentType(ThingsNobodyCaresAboutButMe): pass
class UndeclaredNamespace(Exception): pass

sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
sgmllib.special = re.compile('<!')
sgmllib.charref = re.compile('&#(x?[0-9A-Fa-f]+)[^0-9A-Fa-f]')

SUPPORTED_VERSIONS = {'': 'unknown',
                      'rss090': 'RSS 0.90',
                      'rss091n': 'RSS 0.91 (Netscape)',
                      'rss091u': 'RSS 0.91 (Userland)',
                      'rss092': 'RSS 0.92',
                      'rss093': 'RSS 0.93',
                      'rss094': 'RSS 0.94',
                      'rss20': 'RSS 2.0',
                      'rss10': 'RSS 1.0',
                      'rss': 'RSS (unknown version)',
                      'atom01': 'Atom 0.1',
                      'atom02': 'Atom 0.2',
                      'atom03': 'Atom 0.3',
                      'atom10': 'Atom 1.0',
                      'atom': 'Atom (unknown version)',
                      'cdf': 'CDF',
                      'hotrss': 'Hot RSS'
                      }

try:
    UserDict = dict
except NameError:
    # Python 2.1 does not have dict
    from UserDict import UserDict
    def dict(aList):
        rc = {}
        for k, v in aList:
            rc[k] = v
        return rc

class FeedParserDict(UserDict):
    keymap = {'channel': 'feed',
              'items': 'entries',
              'guid': 'id',
              'date': 'updated',
              'date_parsed': 'updated_parsed',
              'description': ['subtitle', 'summary'],
              'url': ['href'],
              'modified': 'updated',
              'modified_parsed': 'updated_parsed',
              'issued': 'published',
              'issued_parsed': 'published_parsed',
              'copyright': 'rights',
              'copyright_detail': 'rights_detail',
              'tagline': 'subtitle',
              'tagline_detail': 'subtitle_detail'}
    def __getitem__(self, key):
        if key == 'category':
            return UserDict.__getitem__(self, 'tags')[0]['term']
        if key == 'categories':
            return [(tag['scheme'], tag['term']) for tag in UserDict.__getitem__(self, 'tags')]
        realkey = self.keymap.get(key, key)
        if type(realkey) == types.ListType:
            for k in realkey:
                if UserDict.has_key(self, k):
                    return UserDict.__getitem__(self, k)
        if UserDict.has_key(self, key):
            return UserDict.__getitem__(self, key)
        return UserDict.__getitem__(self, realkey)

    def __setitem__(self, key, value):
        for k in self.keymap.keys():
            if key == k:
                key = self.keymap[k]
                if type(key) == types.ListType:
                    key = key[0]
        return UserDict.__setitem__(self, key, value)

    def get(self, key, default=None):
        if self.has_key(key):
            return self[key]
        else:
            return default

    def setdefault(self, key, value):
        if not self.has_key(key):
            self[key] = value
        return self[key]
        
    def has_key(self, key):
        try:
            return hasattr(self, key) or UserDict.has_key(self, key)
        except AttributeError:
            return False
        
    def __getattr__(self, key):
        try:
            return self.__dict__[key]
        except KeyError:
            pass
        try:
            assert not key.startswith('_')
            return self.__getitem__(key)
        except:
            raise AttributeError, "object has no attribute '%s'" % key

    def __setattr__(self, key, value):
        if key.startswith('_') or key == 'data':
            self.__dict__[key] = value
        else:
            return self.__setitem__(key, value)

    def __contains__(self, key):
        return self.has_key(key)

def zopeCompatibilityHack():
    global FeedParserDict
    del FeedParserDict
    def FeedParserDict(aDict=None):
        rc = {}
        if aDict:
            rc.update(aDict)
        return rc

_ebcdic_to_ascii_map = None
def _ebcdic_to_ascii(s):
    global _ebcdic_to_ascii_map
    if not _ebcdic_to_ascii_map:
        emap = (
            0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
            16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
            128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
            144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
            32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
            38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
            45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
            186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
            195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,201,
            202,106,107,108,109,110,111,112,113,114,203,204,205,206,207,208,
            209,126,115,116,117,118,119,120,121,122,210,211,212,213,214,215,
            216,217,218,219,220,221,222,223,224,225,226,227,228,229,230,231,
            123,65,66,67,68,69,70,71,72,73,232,233,234,235,236,237,
            125,74,75,76,77,78,79,80,81,82,238,239,240,241,242,243,
            92,159,83,84,85,86,87,88,89,90,244,245,246,247,248,249,
            48,49,50,51,52,53,54,55,56,57,250,251,252,253,254,255
            )
        import string
        _ebcdic_to_ascii_map = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
    return s.translate(_ebcdic_to_ascii_map)

_urifixer = re.compile('^([A-Za-z][A-Za-z0-9+-.]*://)(/*)(.*?)')
def _urljoin(base, uri):
    uri = _urifixer.sub(r'\1\3', uri)
    return urlparse.urljoin(base, uri)

class _FeedParserMixin:
    namespaces = {'': '',
                  'http://backend.userland.com/rss': '',
                  'http://blogs.law.harvard.edu/tech/rss': '',
                  'http://purl.org/rss/1.0/': '',
                  'http://my.netscape.com/rdf/simple/0.9/': '',
                  'http://example.com/newformat#': '',
                  'http://example.com/necho': '',
                  'http://purl.org/echo/': '',
                  'uri/of/echo/namespace#': '',
                  'http://purl.org/pie/': '',
                  'http://purl.org/atom/ns#': '',
                  'http://www.w3.org/2005/Atom': '',
                  'http://purl.org/rss/1.0/modules/rss091#': '',
                  
                  'http://webns.net/mvcb/':                               'admin',
                  'http://purl.org/rss/1.0/modules/aggregation/':         'ag',
                  'http://purl.org/rss/1.0/modules/annotate/':            'annotate',
                  'http://media.tangent.org/rss/1.0/':                    'audio',
                  'http://backend.userland.com/blogChannelModule':        'blogChannel',
                  'http://web.resource.org/cc/':                          'cc',
                  'http://backend.userland.com/creativeCommonsRssModule': 'creativeCommons',
                  'http://purl.org/rss/1.0/modules/company':              'co',
                  'http://purl.org/rss/1.0/modules/content/':             'content',
                  'http://my.theinfo.org/changed/1.0/rss/':               'cp',
                  'http://purl.org/dc/elements/1.1/':                     'dc',
                  'http://purl.org/dc/terms/':                            'dcterms',
                  'http://purl.org/rss/1.0/modules/email/':               'email',
                  'http://purl.org/rss/1.0/modules/event/':               'ev',
                  'http://rssnamespace.org/feedburner/ext/1.0':           'feedburner',
                  'http://freshmeat.net/rss/fm/':                         'fm',
                  'http://xmlns.com/foaf/0.1/':                           'foaf',
                  'http://www.w3.org/2003/01/geo/wgs84_pos#':             'geo',
                  'http://postneo.com/icbm/':                             'icbm',
                  'http://purl.org/rss/1.0/modules/image/':               'image',
                  'http://www.itunes.com/DTDs/PodCast-1.0.dtd':           'itunes',
                  'http://example.com/DTDs/PodCast-1.0.dtd':              'itunes',
                  'http://purl.org/rss/1.0/modules/link/':                'l',
                  'http://search.yahoo.com/mrss':                         'media',
                  'http://madskills.com/public/xml/rss/module/pingback/': 'pingback',
                  'http://prismstandard.org/namespaces/1.2/basic/':       'prism',
                  'http://www.w3.org/1999/02/22-rdf-syntax-ns#':          'rdf',
                  'http://www.w3.org/2000/01/rdf-schema#':                'rdfs',
                  'http://purl.org/rss/1.0/modules/reference/':           'ref',
                  'http://purl.org/rss/1.0/modules/richequiv/':           'reqv',
                  'http://purl.org/rss/1.0/modules/search/':              'search',
                  'http://purl.org/rss/1.0/modules/slash/':               'slash',
                  'http://schemas.xmlsoap.org/soap/envelope/':            'soap',
                  'http://purl.org/rss/1.0/modules/servicestatus/':       'ss',
                  'http://hacks.benhammersley.com/rss/streaming/':        'str',
                  'http://purl.org/rss/1.0/modules/subscription/':        'sub',
                  'http://purl.org/rss/1.0/modules/syndication/':         'sy',
                  'http://purl.org/rss/1.0/modules/taxonomy/':            'taxo',
                  'http://purl.org/rss/1.0/modules/threading/':           'thr',
                  'http://purl.org/rss/1.0/modules/textinput/':           'ti',
                  'http://madskills.com/public/xml/rss/module/trackback/':'trackback',
                  'http://wellformedweb.org/commentAPI/':                 'wfw',
                  'http://purl.org/rss/1.0/modules/wiki/':                'wiki',
                  'http://www.w3.org/1999/xhtml':                         'xhtml',
                  'http://www.w3.org/XML/1998/namespace':                 'xml',
                  'http://schemas.pocketsoap.com/rss/myDescModule/':      'szf'
}
    _matchnamespaces = {}

    can_be_relative_uri = ['link', 'id', 'wfw_comment', 'wfw_commentrss', 'docs', 'url', 'href', 'comments', 'license', 'icon', 'logo']
    can_contain_relative_uris = ['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description']
    can_contain_dangerous_markup = ['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description']
    html_types = ['text/html', 'application/xhtml+xml']
    
    def __init__(self, baseuri=None, baselang=None, encoding='utf-8'):
        if _debug: sys.stderr.write('initializing FeedParser\n')
        if not self._matchnamespaces:
            for k, v in self.namespaces.items():
                self._matchnamespaces[k.lower()] = v
        self.feeddata = FeedParserDict() # feed-level data
        self.encoding = encoding # character encoding
        self.entries = [] # list of entry-level data
        self.version = '' # feed type/version, see SUPPORTED_VERSIONS
        self.namespacesInUse = {} # dictionary of namespaces defined by the feed

        # the following are used internally to track state;
        # this is really out of control and should be refactored
        self.infeed = 0
        self.inentry = 0
        self.incontent = 0
        self.intextinput = 0
        self.inimage = 0
        self.inauthor = 0
        self.incontributor = 0
        self.inpublisher = 0
        self.insource = 0
        self.sourcedata = FeedParserDict()
        self.contentparams = FeedParserDict()
        self._summaryKey = None
        self.namespacemap = {}
        self.elementstack = []
        self.basestack = []
        self.langstack = []
        self.baseuri = baseuri or ''
        self.lang = baselang or None
        if baselang:
            self.feeddata['language'] = baselang

    def unknown_starttag(self, tag, attrs):
        if _debug: sys.stderr.write('start %s with %s\n' % (tag, attrs))
        # normalize attrs
        attrs = [(k.lower(), v) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        
        # track xml:base and xml:lang
        attrsD = dict(attrs)
        baseuri = attrsD.get('xml:base', attrsD.get('base')) or self.baseuri
        self.baseuri = _urljoin(self.baseuri, baseuri)
        lang = attrsD.get('xml:lang', attrsD.get('lang'))
        if lang == '':
            # xml:lang could be explicitly set to '', we need to capture that
            lang = None
        elif lang is None:
            # if no xml:lang is specified, use parent lang
            lang = self.lang
        if lang:
            if tag in ('feed', 'rss', 'rdf:RDF'):
                self.feeddata['language'] = lang
        self.lang = lang
        self.basestack.append(self.baseuri)
        self.langstack.append(lang)
        
        # track namespaces
        for prefix, uri in attrs:
            if prefix.startswith('xmlns:'):
                self.trackNamespace(prefix[6:], uri)
            elif prefix == 'xmlns':
                self.trackNamespace(None, uri)

        # track inline content
        if self.incontent and self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = 'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == 'application/xhtml+xml':
            # Note: probably shouldn't simply recreate localname here, but
            # our namespace handling isn't actually 100% correct in cases where
            # the feed redefines the default namespace (which is actually
            # the usual case for inline content, thanks Sam), so here we
            # cheat and just reconstruct the element based on localname
            # because that compensates for the bugs in our namespace handling.
            # This will horribly munge inline content with non-empty qnames,
            # but nobody actually does that, so I'm not fixing it.
            tag = tag.split(':')[-1]
            return self.handle_data('<%s%s>' % (tag, ''.join([' %s="%s"' % t for t in attrs])), escape=0)

        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'

        # special hack for better tracking of empty textinput/image elements in illformed feeds
        if (not prefix) and tag not in ('title', 'link', 'description', 'name'):
            self.intextinput = 0
        if (not prefix) and tag not in ('title', 'link', 'description', 'url', 'href', 'width', 'height'):
            self.inimage = 0
        
        # call special handler (if defined) or default handler
        methodname = '_start_' + prefix + suffix
        try:
            method = getattr(self, methodname)
            return method(attrsD)
        except AttributeError:
            return self.push(prefix + suffix, 1)

    def unknown_endtag(self, tag):
        if _debug: sys.stderr.write('end %s\n' % tag)
        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'

        # call special handler (if defined) or default handler
        methodname = '_end_' + prefix + suffix
        try:
            method = getattr(self, methodname)
            method()
        except AttributeError:
            self.pop(prefix + suffix)

        # track inline content
        if self.incontent and self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = 'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == 'application/xhtml+xml':
            tag = tag.split(':')[-1]
            self.handle_data('</%s>' % tag, escape=0)

        # track xml:base and xml:lang going out of scope
        if self.basestack:
            self.basestack.pop()
            if self.basestack and self.basestack[-1]:
                self.baseuri = self.basestack[-1]
        if self.langstack:
            self.langstack.pop()
            if self.langstack: # and (self.langstack[-1] is not None):
                self.lang = self.langstack[-1]

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        if not self.elementstack: return
        ref = ref.lower()
        if ref in ('34', '38', '39', '60', '62', 'x22', 'x26', 'x27', 'x3c', 'x3e'):
            text = '&#%s;' % ref
        else:
            if ref[0] == 'x':
                c = int(ref[1:], 16)
            else:
                c = int(ref)
            text = unichr(c).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        if not self.elementstack: return
        if _debug: sys.stderr.write('entering handle_entityref with %s\n' % ref)
        if ref in ('lt', 'gt', 'quot', 'amp', 'apos'):
            text = '&%s;' % ref
        else:
            # entity resolution graciously donated by Aaron Swartz
            def name2cp(k):
                import htmlentitydefs
                if hasattr(htmlentitydefs, 'name2codepoint'): # requires Python 2.3
                    return htmlentitydefs.name2codepoint[k]
                k = htmlentitydefs.entitydefs[k]
                if k.startswith('&#') and k.endswith(';'):
                    return int(k[2:-1]) # not in latin-1
                return ord(k)
            try: name2cp(ref)
            except KeyError: text = '&%s;' % ref
            else: text = unichr(name2cp(ref)).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_data(self, text, escape=1):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        if not self.elementstack: return
        if escape and self.contentparams.get('type') == 'application/xhtml+xml':
            text = _xmlescape(text)
        self.elementstack[-1][2].append(text)

    def handle_comment(self, text):
        # called for each comment, e.g. <!-- insert message here -->
        pass

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        pass

    def handle_decl(self, text):
        pass

    def parse_declaration(self, i):
        # override internal declaration handler to handle CDATA blocks
        if _debug: sys.stderr.write('entering parse_declaration\n')
        if self.rawdata[i:i+9] == '<![CDATA[':
            k = self.rawdata.find(']]>', i)
            if k == -1: k = len(self.rawdata)
            self.handle_data(_xmlescape(self.rawdata[i+9:k]), 0)
            return k+3
        else:
            k = self.rawdata.find('>', i)
            return k+1

    def mapContentType(self, contentType):
        contentType = contentType.lower()
        if contentType == 'text':
            contentType = 'text/plain'
        elif contentType == 'html':
            contentType = 'text/html'
        elif contentType == 'xhtml':
            contentType = 'application/xhtml+xml'
        return contentType
    
    def trackNamespace(self, prefix, uri):
        loweruri = uri.lower()
        if (prefix, loweruri) == (None, 'http://my.netscape.com/rdf/simple/0.9/') and not self.version:
            self.version = 'rss090'
        if loweruri == 'http://purl.org/rss/1.0/' and not self.version:
            self.version = 'rss10'
        if loweruri == 'http://www.w3.org/2005/atom' and not self.version:
            self.version = 'atom10'
        if loweruri.find('backend.userland.com/rss') <> -1:
            # match any backend.userland.com namespace
            uri = 'http://backend.userland.com/rss'
            loweruri = uri
        if self._matchnamespaces.has_key(loweruri):
            self.namespacemap[prefix] = self._matchnamespaces[loweruri]
            self.namespacesInUse[self._matchnamespaces[loweruri]] = uri
        else:
            self.namespacesInUse[prefix or ''] = uri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri or '', uri)
    
    def decodeEntities(self, element, data):
        return data

    def push(self, element, expectingText):
        self.elementstack.append([element, expectingText, []])

    def pop(self, element, stripWhitespace=1):
        if not self.elementstack: return
        if self.elementstack[-1][0] != element: return
        
        element, expectingText, pieces = self.elementstack.pop()
        output = ''.join(pieces)
        if stripWhitespace:
            output = output.strip()
        if not expectingText: return output

        # decode base64 content
        if base64 and self.contentparams.get('base64', 0):
            try:
                output = base64.decodestring(output)
            except binascii.Error:
                pass
            except binascii.Incomplete:
                pass
                
        # resolve relative URIs
        if (element in self.can_be_relative_uri) and output:
            output = self.resolveURI(output)
        
        # decode entities within embedded markup
        if not self.contentparams.get('base64', 0):
            output = self.decodeEntities(element, output)

        # remove temporary cruft from contentparams
        try:
            del self.contentparams['mode']
        except KeyError:
            pass
        try:
            del self.contentparams['base64']
        except KeyError:
            pass

        # resolve relative URIs within embedded markup
        if self.mapContentType(self.contentparams.get('type', 'text/html')) in self.html_types:
            if element in self.can_contain_relative_uris:
                output = _resolveRelativeURIs(output, self.baseuri, self.encoding)
        
        # sanitize embedded markup
        if self.mapContentType(self.contentparams.get('type', 'text/html')) in self.html_types:
            if element in self.can_contain_dangerous_markup:
                output = _sanitizeHTML(output, self.encoding)

        if self.encoding and type(output) != type(u''):
            try:
                output = unicode(output, self.encoding)
            except:
                pass

        # categories/tags/keywords/whatever are handled in _end_category
        if element == 'category':
            return output
        
        # store output in appropriate place(s)
        if self.inentry and not self.insource:
            if element == 'content':
                self.entries[-1].setdefault(element, [])
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                self.entries[-1][element].append(contentparams)
            elif element == 'link':
                self.entries[-1][element] = output
                if output:
                    self.entries[-1]['links'][-1]['href'] = output
            else:
                if element == 'description':
                    element = 'summary'
                self.entries[-1][element] = output
                if self.incontent:
                    contentparams = copy.deepcopy(self.contentparams)
                    contentparams['value'] = output
                    self.entries[-1][element + '_detail'] = contentparams
        elif (self.infeed or self.insource) and (not self.intextinput) and (not self.inimage):
            context = self._getContext()
            if element == 'description':
                element = 'subtitle'
            context[element] = output
            if element == 'link':
                context['links'][-1]['href'] = output
            elif self.incontent:
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                context[element + '_detail'] = contentparams
        return output

    def pushContent(self, tag, attrsD, defaultContentType, expectingText):
        self.incontent += 1
        self.contentparams = FeedParserDict({
            'type': self.mapContentType(attrsD.get('type', defaultContentType)),
            'language': self.lang,
            'base': self.baseuri})
        self.contentparams['base64'] = self._isBase64(attrsD, self.contentparams)
        self.push(tag, expectingText)

    def popContent(self, tag):
        value = self.pop(tag)
        self.incontent -= 1
        self.contentparams.clear()
        return value
        
    def _mapToStandardPrefix(self, name):
        colonpos = name.find(':')
        if colonpos <> -1:
            prefix = name[:colonpos]
            suffix = name[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            name = prefix + ':' + suffix
        return name
        
    def _getAttribute(self, attrsD, name):
        return attrsD.get(self._mapToStandardPrefix(name))

    def _isBase64(self, attrsD, contentparams):
        if attrsD.get('mode', '') == 'base64':
            return 1
        if self.contentparams['type'].startswith('text/'):
            return 0
        if self.contentparams['type'].endswith('+xml'):
            return 0
        if self.contentparams['type'].endswith('/xml'):
            return 0
        return 1

    def _itsAnHrefDamnIt(self, attrsD):
        href = attrsD.get('url', attrsD.get('uri', attrsD.get('href', None)))
        if href:
            try:
                del attrsD['url']
            except KeyError:
                pass
            try:
                del attrsD['uri']
            except KeyError:
                pass
            attrsD['href'] = href
        return attrsD
    
    def _save(self, key, value):
        context = self._getContext()
        context.setdefault(key, value)

    def _start_rss(self, attrsD):
        versionmap = {'0.91': 'rss091u',
                      '0.92': 'rss092',
                      '0.93': 'rss093',
                      '0.94': 'rss094'}
        if not self.version:
            attr_version = attrsD.get('version', '')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            elif attr_version.startswith('2.'):
                self.version = 'rss20'
            else:
                self.version = 'rss'
    
    def _start_dlhottitles(self, attrsD):
        self.version = 'hotrss'

    def _start_channel(self, attrsD):
        self.infeed = 1
        self._cdf_common(attrsD)
    _start_feedinfo = _start_channel

    def _cdf_common(self, attrsD):
        if attrsD.has_key('lastmod'):
            self._start_modified({})
            self.elementstack[-1][-1] = attrsD['lastmod']
            self._end_modified()
        if attrsD.has_key('href'):
            self._start_link({})
            self.elementstack[-1][-1] = attrsD['href']
            self._end_link()
    
    def _start_feed(self, attrsD):
        self.infeed = 1
        versionmap = {'0.1': 'atom01',
                      '0.2': 'atom02',
                      '0.3': 'atom03'}
        if not self.version:
            attr_version = attrsD.get('version')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            else:
                self.version = 'atom'

    def _end_channel(self):
        self.infeed = 0
    _end_feed = _end_channel
    
    def _start_image(self, attrsD):
        self.inimage = 1
        self.push('image', 0)
        context = self._getContext()
        context.setdefault('image', FeedParserDict())
            
    def _end_image(self):
        self.pop('image')
        self.inimage = 0

    def _start_textinput(self, attrsD):
        self.intextinput = 1
        self.push('textinput', 0)
        context = self._getContext()
        context.setdefault('textinput', FeedParserDict())
    _start_textInput = _start_textinput
    
    def _end_textinput(self):
        self.pop('textinput')
        self.intextinput = 0
    _end_textInput = _end_textinput

    def _start_author(self, attrsD):
        self.inauthor = 1
        self.push('author', 1)
    _start_managingeditor = _start_author
    _start_dc_author = _start_author
    _start_dc_creator = _start_author
    _start_itunes_author = _start_author

    def _end_author(self):
        self.pop('author')
        self.inauthor = 0
        self._sync_author_detail()
    _end_managingeditor = _end_author
    _end_dc_author = _end_author
    _end_dc_creator = _end_author
    _end_itunes_author = _end_author

    def _start_itunes_owner(self, attrsD):
        self.inpublisher = 1
        self.push('publisher', 0)

    def _end_itunes_owner(self):
        self.pop('publisher')
        self.inpublisher = 0
        self._sync_author_detail('publisher')

    def _start_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('contributor', 0)

    def _end_contributor(self):
        self.pop('contributor')
        self.incontributor = 0

    def _start_dc_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('name', 0)

    def _end_dc_contributor(self):
        self._end_name()
        self.incontributor = 0

    def _start_name(self, attrsD):
        self.push('name', 0)
    _start_itunes_name = _start_name

    def _end_name(self):
        value = self.pop('name')
        if self.inpublisher:
            self._save_author('name', value, 'publisher')
        elif self.inauthor:
            self._save_author('name', value)
        elif self.incontributor:
            self._save_contributor('name', value)
        elif self.intextinput:
            context = self._getContext()
            context['textinput']['name'] = value
    _end_itunes_name = _end_name

    def _start_width(self, attrsD):
        self.push('width', 0)

    def _end_width(self):
        value = self.pop('width')
        try:
            value = int(value)
        except:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['image']['width'] = value

    def _start_height(self, attrsD):
        self.push('height', 0)

    def _end_height(self):
        value = self.pop('height')
        try:
            value = int(value)
        except:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['image']['height'] = value

    def _start_url(self, attrsD):
        self.push('href', 1)
    _start_homepage = _start_url
    _start_uri = _start_url

    def _end_url(self):
        value = self.pop('href')
        if self.inauthor:
            self._save_author('href', value)
        elif self.incontributor:
            self._save_contributor('href', value)
        elif self.inimage:
            context = self._getContext()
            context['image']['href'] = value
        elif self.intextinput:
            context = self._getContext()
            context['textinput']['link'] = value
    _end_homepage = _end_url
    _end_uri = _end_url

    def _start_email(self, attrsD):
        self.push('email', 0)
    _start_itunes_email = _start_email

    def _end_email(self):
        value = self.pop('email')
        if self.inpublisher:
            self._save_author('email', value, 'publisher')
        elif self.inauthor:
            self._save_author('email', value)
        elif self.incontributor:
            self._save_contributor('email', value)
    _end_itunes_email = _end_email

    def _getContext(self):
        if self.insource:
            context = self.sourcedata
        elif self.inentry:
            context = self.entries[-1]
        else:
            context = self.feeddata
        return context

    def _save_author(self, key, value, prefix='author'):
        context = self._getContext()
        context.setdefault(prefix + '_detail', FeedParserDict())
        context[prefix + '_detail'][key] = value
        self._sync_author_detail()

    def _save_contributor(self, key, value):
        context = self._getContext()
        context.setdefault('contributors', [FeedParserDict()])
        context['contributors'][-1][key] = value

    def _sync_author_detail(self, key='author'):
        context = self._getContext()
        detail = context.get('%s_detail' % key)
        if detail:
            name = detail.get('name')
            email = detail.get('email')
            if name and email:
                context[key] = '%s (%s)' % (name, email)
            elif name:
                context[key] = name
            elif email:
                context[key] = email
        else:
            author = context.get(key)
            if not author: return
            emailmatch = re.search(r'''(([a-zA-Z0-9\_\-\.\+]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?))''', author)
            if not emailmatch: return
            email = emailmatch.group(0)
            # probably a better way to do the following, but it passes all the tests
            author = author.replace(email, '')
            author = author.replace('()', '')
            author = author.strip()
            if author and (author[0] == '('):
                author = author[1:]
            if author and (author[-1] == ')'):
                author = author[:-1]
            author = author.strip()
            context.setdefault('%s_detail' % key, FeedParserDict())
            context['%s_detail' % key]['name'] = author
            context['%s_detail' % key]['email'] = email

    def _start_subtitle(self, attrsD):
        self.pushContent('subtitle', attrsD, 'text/plain', 1)
    _start_tagline = _start_subtitle
    _start_itunes_subtitle = _start_subtitle

    def _end_subtitle(self):
        self.popContent('subtitle')
    _end_tagline = _end_subtitle
    _end_itunes_subtitle = _end_subtitle
            
    def _start_rights(self, attrsD):
        self.pushContent('rights', attrsD, 'text/plain', 1)
    _start_dc_rights = _start_rights
    _start_copyright = _start_rights

    def _end_rights(self):
        self.popContent('rights')
    _end_dc_rights = _end_rights
    _end_copyright = _end_rights

    def _start_item(self, attrsD):
        self.entries.append(FeedParserDict())
        self.push('item', 0)
        self.inentry = 1
        self.guidislink = 0
        id = self._getAttribute(attrsD, 'rdf:about')
        if id:
            context = self._getContext()
            context['id'] = id
        self._cdf_common(attrsD)
    _start_entry = _start_item
    _start_product = _start_item

    def _end_item(self):
        self.pop('item')
        self.inentry = 0
    _end_entry = _end_item

    def _start_dc_language(self, attrsD):
        self.push('language', 1)
    _start_language = _start_dc_language

    def _end_dc_language(self):
        self.lang = self.pop('language')
    _end_language = _end_dc_language

    def _start_dc_publisher(self, attrsD):
        self.push('publisher', 1)
    _start_webmaster = _start_dc_publisher

    def _end_dc_publisher(self):
        self.pop('publisher')
        self._sync_author_detail('publisher')
    _end_webmaster = _end_dc_publisher

    def _start_published(self, attrsD):
        self.push('published', 1)
    _start_dcterms_issued = _start_published
    _start_issued = _start_published

    def _end_published(self):
        value = self.pop('published')
        self._save('published_parsed', _parse_date(value))
    _end_dcterms_issued = _end_published
    _end_issued = _end_published

    def _start_updated(self, attrsD):
        self.push('updated', 1)
    _start_modified = _start_updated
    _start_dcterms_modified = _start_updated
    _start_pubdate = _start_updated
    _start_dc_date = _start_updated

    def _end_updated(self):
        value = self.pop('updated')
        parsed_value = _parse_date(value)
        self._save('updated_parsed', parsed_value)
    _end_modified = _end_updated
    _end_dcterms_modified = _end_updated
    _end_pubdate = _end_updated
    _end_dc_date = _end_updated

    def _start_created(self, attrsD):
        self.push('created', 1)
    _start_dcterms_created = _start_created

    def _end_created(self):
        value = self.pop('created')
        self._save('created_parsed', _parse_date(value))
    _end_dcterms_created = _end_created

    def _start_expirationdate(self, attrsD):
        self.push('expired', 1)

    def _end_expirationdate(self):
        self._save('expired_parsed', _parse_date(self.pop('expired')))

    def _start_cc_license(self, attrsD):
        self.push('license', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('license')
        
    def _start_creativecommons_license(self, attrsD):
        self.push('license', 1)

    def _end_creativecommons_license(self):
        self.pop('license')

    def _addTag(self, term, scheme, label):
        context = self._getContext()
        tags = context.setdefault('tags', [])
        if (not term) and (not scheme) and (not label): return
        value = FeedParserDict({'term': term, 'scheme': scheme, 'label': label})
        if value not in tags:
            tags.append(FeedParserDict({'term': term, 'scheme': scheme, 'label': label}))

    def _start_category(self, attrsD):
        if _debug: sys.stderr.write('entering _start_category with %s\n' % repr(attrsD))
        term = attrsD.get('term')
        scheme = attrsD.get('scheme', attrsD.get('domain'))
        label = attrsD.get('label')
        self._addTag(term, scheme, label)
        self.push('category', 1)
    _start_dc_subject = _start_category
    _start_keywords = _start_category
        
    def _end_itunes_keywords(self):
        for term in self.pop('itunes_keywords').split():
            self._addTag(term, 'http://www.itunes.com/', None)
        
    def _start_itunes_category(self, attrsD):
        self._addTag(attrsD.get('text'), 'http://www.itunes.com/', None)
        self.push('category', 1)
        
    def _end_category(self):
        value = self.pop('category')
        if not value: return
        context = self._getContext()
        tags = context['tags']
        if value and len(tags) and not tags[-1]['term']:
            tags[-1]['term'] = value
        else:
            self._addTag(value, None, None)
    _end_dc_subject = _end_category
    _end_keywords = _end_category
    _end_itunes_category = _end_category

    def _start_cloud(self, attrsD):
        self._getContext()['cloud'] = FeedParserDict(attrsD)
        
    def _start_link(self, attrsD):
        attrsD.setdefault('rel', 'alternate')
        attrsD.setdefault('type', 'text/html')
        attrsD = self._itsAnHrefDamnIt(attrsD)
        if attrsD.has_key('href'):
            attrsD['href'] = self.resolveURI(attrsD['href'])
        expectingText = self.infeed or self.inentry or self.insource
        context = self._getContext()
        context.setdefault('links', [])
        context['links'].append(FeedParserDict(attrsD))
        if attrsD['rel'] == 'enclosure':
            self._start_enclosure(attrsD)
        if attrsD.has_key('href'):
            expectingText = 0
            if (attrsD.get('rel') == 'alternate') and (self.mapContentType(attrsD.get('type')) in self.html_types):
                context['link'] = attrsD['href']
        else:
            self.push('link', expectingText)
    _start_producturl = _start_link

    def _end_link(self):
        value = self.pop('link')
        context = self._getContext()
        if self.intextinput:
            context['textinput']['link'] = value
        if self.inimage:
            context['image']['link'] = value
    _end_producturl = _end_link

    def _start_guid(self, attrsD):
        self.guidislink = (attrsD.get('ispermalink', 'true') == 'true')
        self.push('id', 1)

    def _end_guid(self):
        value = self.pop('id')
        self._save('guidislink', self.guidislink and not self._getContext().has_key('link'))
        if self.guidislink:
            # guid acts as link, but only if 'ispermalink' is not present or is 'true',
            # and only if the item doesn't already have a link element
            self._save('link', value)

    def _start_title(self, attrsD):
        self.pushContent('title', attrsD, 'text/plain', self.infeed or self.inentry or self.insource)
    _start_dc_title = _start_title
    _start_media_title = _start_title

    def _end_title(self):
        value = self.popContent('title')
        context = self._getContext()
        if self.intextinput:
            context['textinput']['title'] = value
        elif self.inimage:
            context['image']['title'] = value
    _end_dc_title = _end_title
    _end_media_title = _end_title

    def _start_description(self, attrsD):
        context = self._getContext()
        if context.has_key('summary'):
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self.pushContent('description', attrsD, 'text/html', self.infeed or self.inentry or self.insource)

    def _start_abstract(self, attrsD):
        self.pushContent('description', attrsD, 'text/plain', self.infeed or self.inentry or self.insource)

    def _end_description(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            value = self.popContent('description')
            context = self._getContext()
            if self.intextinput:
                context['textinput']['description'] = value
            elif self.inimage:
                context['image']['description'] = value
        self._summaryKey = None
    _end_abstract = _end_description

    def _start_info(self, attrsD):
        self.pushContent('info', attrsD, 'text/plain', 1)
    _start_feedburner_browserfriendly = _start_info

    def _end_info(self):
        self.popContent('info')
    _end_feedburner_browserfriendly = _end_info

    def _start_generator(self, attrsD):
        if attrsD:
            attrsD = self._itsAnHrefDamnIt(attrsD)
            if attrsD.has_key('href'):
                attrsD['href'] = self.resolveURI(attrsD['href'])
        self._getContext()['generator_detail'] = FeedParserDict(attrsD)
        self.push('generator', 1)

    def _end_generator(self):
        value = self.pop('generator')
        context = self._getContext()
        if context.has_key('generator_detail'):
            context['generator_detail']['name'] = value
            
    def _start_admin_generatoragent(self, attrsD):
        self.push('generator', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('generator')
        self._getContext()['generator_detail'] = FeedParserDict({'href': value})

    def _start_admin_errorreportsto(self, attrsD):
        self.push('errorreportsto', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('errorreportsto')
        
    def _start_summary(self, attrsD):
        context = self._getContext()
        if context.has_key('summary'):
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self._summaryKey = 'summary'
            self.pushContent(self._summaryKey, attrsD, 'text/plain', 1)
    _start_itunes_summary = _start_summary

    def _end_summary(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            self.popContent(self._summaryKey or 'summary')
        self._summaryKey = None
    _end_itunes_summary = _end_summary
        
    def _start_enclosure(self, attrsD):
        attrsD = self._itsAnHrefDamnIt(attrsD)
        self._getContext().setdefault('enclosures', []).append(FeedParserDict(attrsD))
        href = attrsD.get('href')
        if href:
            context = self._getContext()
            if not context.get('id'):
                context['id'] = href
            
    def _start_source(self, attrsD):
        self.insource = 1

    def _end_source(self):
        self.insource = 0
        self._getContext()['source'] = copy.deepcopy(self.sourcedata)
        self.sourcedata.clear()

    def _start_content(self, attrsD):
        self.pushContent('content', attrsD, 'text/plain', 1)
        src = attrsD.get('src')
        if src:
            self.contentparams['src'] = src
        self.push('content', 1)

    def _start_prodlink(self, attrsD):
        self.pushContent('content', attrsD, 'text/html', 1)

    def _start_body(self, attrsD):
        self.pushContent('content', attrsD, 'application/xhtml+xml', 1)
    _start_xhtml_body = _start_body

    def _start_content_encoded(self, attrsD):
        self.pushContent('content', attrsD, 'text/html', 1)
    _start_fullitem = _start_content_encoded

    def _end_content(self):
        copyToDescription = self.mapContentType(self.contentparams.get('type')) in (['text/plain'] + self.html_types)
        value = self.popContent('content')
        if copyToDescription:
            self._save('description', value)
    _end_body = _end_content
    _end_xhtml_body = _end_content
    _end_content_encoded = _end_content
    _end_fullitem = _end_content
    _end_prodlink = _end_content

    def _start_itunes_image(self, attrsD):
        self.push('itunes_image', 0)
        self._getContext()['image'] = FeedParserDict({'href': attrsD.get('href')})
    _start_itunes_link = _start_itunes_image
        
    def _end_itunes_block(self):
        value = self.pop('itunes_block', 0)
        self._getContext()['itunes_block'] = (value == 'yes') and 1 or 0

    def _end_itunes_explicit(self):
        value = self.pop('itunes_explicit', 0)
        self._getContext()['itunes_explicit'] = (value == 'yes') and 1 or 0

if _XML_AVAILABLE:
    class _StrictFeedParser(_FeedParserMixin, xml.sax.handler.ContentHandler):
        def __init__(self, baseuri, baselang, encoding):
            if _debug: sys.stderr.write('trying StrictFeedParser\n')
            xml.sax.handler.ContentHandler.__init__(self)
            _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
            self.bozo = 0
            self.exc = None
        
        def startPrefixMapping(self, prefix, uri):
            self.trackNamespace(prefix, uri)
        
        def startElementNS(self, name, qname, attrs):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if lowernamespace.find('backend.userland.com/rss') <> -1:
                # match any backend.userland.com namespace
                namespace = 'http://backend.userland.com/rss'
                lowernamespace = namespace
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = None
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if givenprefix and (prefix == None or (prefix == '' and lowernamespace == '')) and not self.namespacesInUse.has_key(givenprefix):
                    raise UndeclaredNamespace, "'%s' is not associated with a namespace" % givenprefix
            if prefix:
                localname = prefix + ':' + localname
            localname = str(localname).lower()
            if _debug: sys.stderr.write('startElementNS: qname = %s, namespace = %s, givenprefix = %s, prefix = %s, attrs = %s, localname = %s\n' % (qname, namespace, givenprefix, prefix, attrs.items(), localname))

            # qname implementation is horribly broken in Python 2.1 (it
            # doesn't report any), and slightly broken in Python 2.2 (it
            # doesn't report the xml: namespace). So we match up namespaces
            # with a known list first, and then possibly override them with
            # the qnames the SAX parser gives us (if indeed it gives us any
            # at all).  Thanks to MatejC for helping me test this and
            # tirelessly telling me that it didn't work yet.
            attrsD = {}
            for (namespace, attrlocalname), attrvalue in attrs._attrs.items():
                lowernamespace = (namespace or '').lower()
                prefix = self._matchnamespaces.get(lowernamespace, '')
                if prefix:
                    attrlocalname = prefix + ':' + attrlocalname
                attrsD[str(attrlocalname).lower()] = attrvalue
            for qname in attrs.getQNames():
                attrsD[str(qname).lower()] = attrs.getValueByQName(qname)
            self.unknown_starttag(localname, attrsD.items())

        def characters(self, text):
            self.handle_data(text)

        def endElementNS(self, name, qname):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = ''
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if prefix:
                localname = prefix + ':' + localname
            localname = str(localname).lower()
            self.unknown_endtag(localname)

        def error(self, exc):
            self.bozo = 1
            self.exc = exc
            
        def fatalError(self, exc):
            self.error(exc)
            raise exc

class _BaseHTMLProcessor(sgmllib.SGMLParser):
    elements_no_end_tag = ['area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
      'img', 'input', 'isindex', 'link', 'meta', 'param']
    
    def __init__(self, encoding):
        self.encoding = encoding
        if _debug: sys.stderr.write('entering BaseHTMLProcessor, encoding=%s\n' % self.encoding)
        sgmllib.SGMLParser.__init__(self)
        
    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'
        
    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        #data = re.sub(r'<(\S+?)\s*?/>', self._shorttag_replace, data) # bug [ 1399464 ] Bad regexp for _shorttag_replace
        data = re.sub(r'<([^<\s]+?)\s*/>', self._shorttag_replace, data) 
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        if self.encoding and type(data) == type(u''):
            data = data.encode(self.encoding)
        sgmllib.SGMLParser.feed(self, data)

    def normalize_attrs(self, attrs):
        # utility method to be called by descendants
        attrs = [(k.lower(), v) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        return attrs

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class='screen'>, tag='pre', attrs=[('class', 'screen')]
        if _debug: sys.stderr.write('_BaseHTMLProcessor, unknown_starttag, tag=%s\n' % tag)
        uattrs = []
        # thanks to Kevin Marks for this breathtaking hack to deal with (valid) high-bit attribute values in UTF-8 feeds
        for key, value in attrs:
            if type(value) != type(u''):
                value = unicode(value, self.encoding)
            uattrs.append((unicode(key, self.encoding), value))
        strattrs = u''.join([u' %s="%s"' % (key, value) for key, value in uattrs]).encode(self.encoding)
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%(tag)s%(strattrs)s />' % locals())
        else:
            self.pieces.append('<%(tag)s%(strattrs)s>' % locals())

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be 'pre'
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%(tag)s>" % locals())

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        self.pieces.append('&#%(ref)s;' % locals())
        
    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        self.pieces.append('&%(ref)s;' % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        if _debug: sys.stderr.write('_BaseHTMLProcessor, handle_text, text=%s\n' % text)
        self.pieces.append(text)
        
    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%(text)s-->' % locals())
        
    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%(text)s>' % locals())

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%(text)s>' % locals())
        
    _new_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9:]*\s*').match
    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = self._new_declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return name.lower(), m.end()
        else:
            self.handle_data(rawdata)
#            self.updatepos(declstartpos, i)
            return None, -1

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join([str(p) for p in self.pieces])

class _LooseFeedParser(_FeedParserMixin, _BaseHTMLProcessor):
    def __init__(self, baseuri, baselang, encoding):
        sgmllib.SGMLParser.__init__(self)
        _FeedParserMixin.__init__(self, baseuri, baselang, encoding)

    def decodeEntities(self, element, data):
        data = data.replace('&#60;', '&lt;')
        data = data.replace('&#x3c;', '&lt;')
        data = data.replace('&#62;', '&gt;')
        data = data.replace('&#x3e;', '&gt;')
        data = data.replace('&#38;', '&amp;')
        data = data.replace('&#x26;', '&amp;')
        data = data.replace('&#34;', '&quot;')
        data = data.replace('&#x22;', '&quot;')
        data = data.replace('&#39;', '&apos;')
        data = data.replace('&#x27;', '&apos;')
        if self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            data = data.replace('&lt;', '<')
            data = data.replace('&gt;', '>')
            data = data.replace('&amp;', '&')
            data = data.replace('&quot;', '"')
            data = data.replace('&apos;', "'")
        return data
        
class _RelativeURIResolver(_BaseHTMLProcessor):
    relative_uris = [('a', 'href'),
                     ('applet', 'codebase'),
                     ('area', 'href'),
                     ('blockquote', 'cite'),
                     ('body', 'background'),
                     ('del', 'cite'),
                     ('form', 'action'),
                     ('frame', 'longdesc'),
                     ('frame', 'src'),
                     ('iframe', 'longdesc'),
                     ('iframe', 'src'),
                     ('head', 'profile'),
                     ('img', 'longdesc'),
                     ('img', 'src'),
                     ('img', 'usemap'),
                     ('input', 'src'),
                     ('input', 'usemap'),
                     ('ins', 'cite'),
                     ('link', 'href'),
                     ('object', 'classid'),
                     ('object', 'codebase'),
                     ('object', 'data'),
                     ('object', 'usemap'),
                     ('q', 'cite'),
                     ('script', 'src')]

    def __init__(self, baseuri, encoding):
        _BaseHTMLProcessor.__init__(self, encoding)
        self.baseuri = baseuri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri, uri)
    
    def unknown_starttag(self, tag, attrs):
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, ((tag, key) in self.relative_uris) and self.resolveURI(value) or value) for key, value in attrs]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)
        
def _resolveRelativeURIs(htmlSource, baseURI, encoding):
    if _debug: sys.stderr.write('entering _resolveRelativeURIs\n')
    p = _RelativeURIResolver(baseURI, encoding)
    p.feed(htmlSource)
    return p.output()

class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em', 'fieldset',
      'font', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input',
      'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol', 'optgroup',
      'option', 'p', 'pre', 'q', 's', 'samp', 'select', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th',
      'thead', 'tr', 'tt', 'u', 'ul', 'var']

    acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
      'char', 'charoff', 'charset', 'checked', 'cite', 'class', 'clear', 'cols',
      'colspan', 'color', 'compact', 'coords', 'datetime', 'dir', 'disabled',
      'enctype', 'for', 'frame', 'headers', 'height', 'href', 'hreflang', 'hspace',
      'id', 'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
      'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
      'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape', 'size',
      'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title', 'type',
      'usemap', 'valign', 'value', 'vspace', 'width']

    unacceptable_elements_with_end_tag = ['script', 'applet']

    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0
        
    def unknown_starttag(self, tag, attrs):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1
            return
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, value) for key, value in attrs if key in self.acceptable_attributes]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)
        
    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)

def _sanitizeHTML(htmlSource, encoding):
    p = _HTMLSanitizer(encoding)
    p.feed(htmlSource)
    data = p.output()
    if TIDY_MARKUP:
        # loop through list of preferred Tidy interfaces looking for one that's installed,
        # then set up a common _tidy function to wrap the interface-specific API.
        _tidy = None
        for tidy_interface in PREFERRED_TIDY_INTERFACES:
            try:
                if tidy_interface == "uTidy":
                    from tidy import parseString as _utidy
                    def _tidy(data, **kwargs):
                        return str(_utidy(data, **kwargs))
                    break
                elif tidy_interface == "mxTidy":
                    from mx.Tidy import Tidy as _mxtidy
                    def _tidy(data, **kwargs):
                        nerrors, nwarnings, data, errordata = _mxtidy.tidy(data, **kwargs)
                        return data
                    break
            except:
                pass
        if _tidy:
            utf8 = type(data) == type(u'')
            if utf8:
                data = data.encode('utf-8')
            data = _tidy(data, output_xhtml=1, numeric_entities=1, wrap=0, char_encoding="utf8")
            if utf8:
                data = unicode(data, 'utf-8')
            if data.count('<body'):
                data = data.split('<body', 1)[1]
                if data.count('>'):
                    data = data.split('>', 1)[1]
            if data.count('</body'):
                data = data.split('</body', 1)[0]
    data = data.strip().replace('\r\n', '\n')
    return data

class _FeedURLHandler(urllib2.HTTPDigestAuthHandler, urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        if ((code / 100) == 3) and (code != 304):
            return self.http_error_302(req, fp, code, msg, headers)
        infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        return infourl

    def http_error_302(self, req, fp, code, msg, headers):
        if headers.dict.has_key('location'):
            infourl = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        else:
            infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        if not hasattr(infourl, 'status'):
            infourl.status = code
        return infourl

    def http_error_301(self, req, fp, code, msg, headers):
        if headers.dict.has_key('location'):
            infourl = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        else:
            infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        if not hasattr(infourl, 'status'):
            infourl.status = code
        return infourl

    http_error_300 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
        
    def http_error_401(self, req, fp, code, msg, headers):
        # Check if
        # - server requires digest auth, AND
        # - we tried (unsuccessfully) with basic auth, AND
        # - we're using Python 2.3.3 or later (digest auth is irreparably broken in earlier versions)
        # If all conditions hold, parse authentication information
        # out of the Authorization header we sent the first time
        # (for the username and password) and the WWW-Authenticate
        # header the server sent back (for the realm) and retry
        # the request with the appropriate digest auth headers instead.
        # This evil genius hack has been brought to you by Aaron Swartz.
        host = urlparse.urlparse(req.get_full_url())[1]
        try:
            assert sys.version.split()[0] >= '2.3.3'
            assert base64 != None
            user, passw = base64.decodestring(req.headers['Authorization'].split(' ')[1]).split(':')
            realm = re.findall('realm="([^"]*)"', headers['WWW-Authenticate'])[0]
            self.add_password(realm, host, user, passw)
            retry = self.http_error_auth_reqed('www-authenticate', host, req, headers)
            self.reset_retry_count()
            return retry
        except:
            return self.http_error_default(req, fp, code, msg, headers)

def _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers):
    """URL, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it must be a tuple of 9 integers
    as returned by gmtime() in the standard Python time module. This MUST
    be in GMT (Greenwich Mean Time). The formatted date/time will be used
    as the value of an If-Modified-Since request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.

    If handlers is supplied, it is a list of handlers used to build a
    urllib2 opener.
    """

    if hasattr(url_file_stream_or_string, 'read'):
        return url_file_stream_or_string

    if url_file_stream_or_string == '-':
        return sys.stdin

    if urlparse.urlparse(url_file_stream_or_string)[0] in ('http', 'https', 'ftp'):
        if not agent:
            agent = USER_AGENT
        # test for inline user:password for basic auth
        auth = None
        if base64:
            urltype, rest = urllib.splittype(url_file_stream_or_string)
            realhost, rest = urllib.splithost(rest)
            if realhost:
                user_passwd, realhost = urllib.splituser(realhost)
                if user_passwd:
                    url_file_stream_or_string = '%s://%s%s' % (urltype, realhost, rest)
                    auth = base64.encodestring(user_passwd).strip()
        # try to open with urllib2 (to use optional headers)
        request = urllib2.Request(url_file_stream_or_string)
        request.add_header('User-Agent', agent)
        if etag:
            request.add_header('If-None-Match', etag)
        if modified:
            # format into an RFC 1123-compliant timestamp. We can't use
            # time.strftime() since the %a and %b directives can be affected
            # by the current locale, but RFC 2616 states that dates must be
            # in English.
            short_weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            request.add_header('If-Modified-Since', '%s, %02d %s %04d %02d:%02d:%02d GMT' % (short_weekdays[modified[6]], modified[2], months[modified[1] - 1], modified[0], modified[3], modified[4], modified[5]))
        if referrer:
            request.add_header('Referer', referrer)
        if gzip and zlib:
            request.add_header('Accept-encoding', 'gzip, deflate')
        elif gzip:
            request.add_header('Accept-encoding', 'gzip')
        elif zlib:
            request.add_header('Accept-encoding', 'deflate')
        else:
            request.add_header('Accept-encoding', '')
        if auth:
            request.add_header('Authorization', 'Basic %s' % auth)
        if ACCEPT_HEADER:
            request.add_header('Accept', ACCEPT_HEADER)
        request.add_header('A-IM', 'feed') # RFC 3229 support
        opener = apply(urllib2.build_opener, tuple([_FeedURLHandler()] + handlers))
        opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
        try:
            return opener.open(request)
        finally:
            opener.close() # JohnD
    
    # try to open with native open function (if url_file_stream_or_string is a filename)
    try:
        return open(url_file_stream_or_string)
    except:
        pass

    # treat url_file_stream_or_string as string
    return _StringIO(str(url_file_stream_or_string))

_date_handlers = []
def registerDateHandler(func):
    '''Register a date handler function (takes string, returns 9-tuple date in GMT)'''
    _date_handlers.insert(0, func)
    
# ISO-8601 date parsing routines written by Fazal Majid.
# The ISO 8601 standard is very convoluted and irregular - a full ISO 8601
# parser is beyond the scope of feedparser and would be a worthwhile addition
# to the Python library.
# A single regular expression cannot parse ISO 8601 date formats into groups
# as the standard is highly irregular (for instance is 030104 2003-01-04 or
# 0301-04-01), so we use templates instead.
# Please note the order in templates is significant because we need a
# greedy match.
_iso8601_tmpl = ['YYYY-?MM-?DD', 'YYYY-MM', 'YYYY-?OOO',
                'YY-?MM-?DD', 'YY-?OOO', 'YYYY', 
                '-YY-?MM', '-OOO', '-YY',
                '--MM-?DD', '--MM',
                '---DD',
                'CC', '']
_iso8601_re = [
    tmpl.replace(
    'YYYY', r'(?P<year>\d{4})').replace(
    'YY', r'(?P<year>\d\d)').replace(
    'MM', r'(?P<month>[01]\d)').replace(
    'DD', r'(?P<day>[0123]\d)').replace(
    'OOO', r'(?P<ordinal>[0123]\d\d)').replace(
    'CC', r'(?P<century>\d\d$)')
    + r'(T?(?P<hour>\d{2}):(?P<minute>\d{2})'
    + r'(:(?P<second>\d{2}))?'
    + r'(?P<tz>[+-](?P<tzhour>\d{2})(:(?P<tzmin>\d{2}))?|Z)?)?'
    for tmpl in _iso8601_tmpl]
del tmpl
_iso8601_matches = [re.compile(regex).match for regex in _iso8601_re]
del regex
def _parse_date_iso8601(dateString):
    '''Parse a variety of ISO-8601-compatible formats like 20040105'''
    m = None
    for _iso8601_match in _iso8601_matches:
        m = _iso8601_match(dateString)
        if m: break
    if not m: return
    if m.span() == (0, 0): return
    params = m.groupdict()
    ordinal = params.get('ordinal', 0)
    if ordinal:
        ordinal = int(ordinal)
    else:
        ordinal = 0
    year = params.get('year', '--')
    if not year or year == '--':
        year = time.gmtime()[0]
    elif len(year) == 2:
        # ISO 8601 assumes current century, i.e. 93 -> 2093, NOT 1993
        year = 100 * int(time.gmtime()[0] / 100) + int(year)
    else:
        year = int(year)
    month = params.get('month', '-')
    if not month or month == '-':
        # ordinals are NOT normalized by mktime, we simulate them
        # by setting month=1, day=ordinal
        if ordinal:
            month = 1
        else:
            month = time.gmtime()[1]
    month = int(month)
    day = params.get('day', 0)
    if not day:
        # see above
        if ordinal:
            day = ordinal
        elif params.get('century', 0) or \
                 params.get('year', 0) or params.get('month', 0):
            day = 1
        else:
            day = time.gmtime()[2]
    else:
        day = int(day)
    # special case of the century - is the first year of the 21st century
    # 2000 or 2001 ? The debate goes on...
    if 'century' in params.keys():
        year = (int(params['century']) - 1) * 100 + 1
    # in ISO 8601 most fields are optional
    for field in ['hour', 'minute', 'second', 'tzhour', 'tzmin']:
        if not params.get(field, None):
            params[field] = 0
    hour = int(params.get('hour', 0))
    minute = int(params.get('minute', 0))
    second = int(params.get('second', 0))
    # weekday is normalized by mktime(), we can ignore it
    weekday = 0
    # daylight savings is complex, but not needed for feedparser's purposes
    # as time zones, if specified, include mention of whether it is active
    # (e.g. PST vs. PDT, CET). Using -1 is implementation-dependent and
    # and most implementations have DST bugs
    daylight_savings_flag = 0
    tm = [year, month, day, hour, minute, second, weekday,
          ordinal, daylight_savings_flag]
    # ISO 8601 time zone adjustments
    tz = params.get('tz')
    if tz and tz != 'Z':
        if tz[0] == '-':
            tm[3] += int(params.get('tzhour', 0))
            tm[4] += int(params.get('tzmin', 0))
        elif tz[0] == '+':
            tm[3] -= int(params.get('tzhour', 0))
            tm[4] -= int(params.get('tzmin', 0))
        else:
            return None
    # Python's time.mktime() is a wrapper around the ANSI C mktime(3c)
    # which is guaranteed to normalize d/m/y/h/m/s.
    # Many implementations have bugs, but we'll pretend they don't.
    return time.localtime(time.mktime(tm))
registerDateHandler(_parse_date_iso8601)
    
# 8-bit date handling routines written by ytrewq1.
_korean_year  = u'\ub144' # b3e2 in euc-kr
_korean_month = u'\uc6d4' # bff9 in euc-kr
_korean_day   = u'\uc77c' # c0cf in euc-kr
_korean_am    = u'\uc624\uc804' # bfc0 c0fc in euc-kr
_korean_pm    = u'\uc624\ud6c4' # bfc0 c8c4 in euc-kr

_korean_onblog_date_re = \
    re.compile('(\d{4})%s\s+(\d{2})%s\s+(\d{2})%s\s+(\d{2}):(\d{2}):(\d{2})' % \
               (_korean_year, _korean_month, _korean_day))
_korean_nate_date_re = \
    re.compile(u'(\d{4})-(\d{2})-(\d{2})\s+(%s|%s)\s+(\d{,2}):(\d{,2}):(\d{,2})' % \
               (_korean_am, _korean_pm))
def _parse_date_onblog(dateString):
    '''Parse a string according to the OnBlog 8-bit date format'''
    m = _korean_onblog_date_re.match(dateString)
    if not m: return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': m.group(4), 'minute': m.group(5), 'second': m.group(6),\
                 'zonediff': '+09:00'}
    if _debug: sys.stderr.write('OnBlog date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_onblog)

def _parse_date_nate(dateString):
    '''Parse a string according to the Nate 8-bit date format'''
    m = _korean_nate_date_re.match(dateString)
    if not m: return
    hour = int(m.group(5))
    ampm = m.group(4)
    if (ampm == _korean_pm):
        hour += 12
    hour = str(hour)
    if len(hour) == 1:
        hour = '0' + hour
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': hour, 'minute': m.group(6), 'second': m.group(7),\
                 'zonediff': '+09:00'}
    if _debug: sys.stderr.write('Nate date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_nate)

_mssql_date_re = \
    re.compile('(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})(\.\d+)?')
def _parse_date_mssql(dateString):
    '''Parse a string according to the MS SQL date format'''
    m = _mssql_date_re.match(dateString)
    if not m: return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': m.group(4), 'minute': m.group(5), 'second': m.group(6),\
                 'zonediff': '+09:00'}
    if _debug: sys.stderr.write('MS SQL date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_mssql)

# Unicode strings for Greek date strings
_greek_months = \
  { \
   u'\u0399\u03b1\u03bd': u'Jan',       # c9e1ed in iso-8859-7
   u'\u03a6\u03b5\u03b2': u'Feb',       # d6e5e2 in iso-8859-7
   u'\u039c\u03ac\u03ce': u'Mar',       # ccdcfe in iso-8859-7
   u'\u039c\u03b1\u03ce': u'Mar',       # cce1fe in iso-8859-7
   u'\u0391\u03c0\u03c1': u'Apr',       # c1f0f1 in iso-8859-7
   u'\u039c\u03ac\u03b9': u'May',       # ccdce9 in iso-8859-7
   u'\u039c\u03b1\u03ca': u'May',       # cce1fa in iso-8859-7
   u'\u039c\u03b1\u03b9': u'May',       # cce1e9 in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bd': u'Jun', # c9effded in iso-8859-7
   u'\u0399\u03bf\u03bd': u'Jun',       # c9efed in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bb': u'Jul', # c9effdeb in iso-8859-7
   u'\u0399\u03bf\u03bb': u'Jul',       # c9f9eb in iso-8859-7
   u'\u0391\u03cd\u03b3': u'Aug',       # c1fde3 in iso-8859-7
   u'\u0391\u03c5\u03b3': u'Aug',       # c1f5e3 in iso-8859-7
   u'\u03a3\u03b5\u03c0': u'Sep',       # d3e5f0 in iso-8859-7
   u'\u039f\u03ba\u03c4': u'Oct',       # cfeaf4 in iso-8859-7
   u'\u039d\u03bf\u03ad': u'Nov',       # cdefdd in iso-8859-7
   u'\u039d\u03bf\u03b5': u'Nov',       # cdefe5 in iso-8859-7
   u'\u0394\u03b5\u03ba': u'Dec',       # c4e5ea in iso-8859-7
  }

_greek_wdays = \
  { \
   u'\u039a\u03c5\u03c1': u'Sun', # caf5f1 in iso-8859-7
   u'\u0394\u03b5\u03c5': u'Mon', # c4e5f5 in iso-8859-7
   u'\u03a4\u03c1\u03b9': u'Tue', # d4f1e9 in iso-8859-7
   u'\u03a4\u03b5\u03c4': u'Wed', # d4e5f4 in iso-8859-7
   u'\u03a0\u03b5\u03bc': u'Thu', # d0e5ec in iso-8859-7
   u'\u03a0\u03b1\u03c1': u'Fri', # d0e1f1 in iso-8859-7
   u'\u03a3\u03b1\u03b2': u'Sat', # d3e1e2 in iso-8859-7   
  }

_greek_date_format_re = \
    re.compile(u'([^,]+),\s+(\d{2})\s+([^\s]+)\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+([^\s]+)')

def _parse_date_greek(dateString):
    '''Parse a string according to a Greek 8-bit date format.'''
    m = _greek_date_format_re.match(dateString)
    if not m: return
    try:
        wday = _greek_wdays[m.group(1)]
        month = _greek_months[m.group(3)]
    except:
        return
    rfc822date = '%(wday)s, %(day)s %(month)s %(year)s %(hour)s:%(minute)s:%(second)s %(zonediff)s' % \
                 {'wday': wday, 'day': m.group(2), 'month': month, 'year': m.group(4),\
                  'hour': m.group(5), 'minute': m.group(6), 'second': m.group(7),\
                  'zonediff': m.group(8)}
    if _debug: sys.stderr.write('Greek date parsed as: %s\n' % rfc822date)
    return _parse_date_rfc822(rfc822date)
registerDateHandler(_parse_date_greek)

# Unicode strings for Hungarian date strings
_hungarian_months = \
  { \
    u'janu\u00e1r':   u'01',  # e1 in iso-8859-2
    u'febru\u00e1ri': u'02',  # e1 in iso-8859-2
    u'm\u00e1rcius':  u'03',  # e1 in iso-8859-2
    u'\u00e1prilis':  u'04',  # e1 in iso-8859-2
    u'm\u00e1ujus':   u'05',  # e1 in iso-8859-2
    u'j\u00fanius':   u'06',  # fa in iso-8859-2
    u'j\u00falius':   u'07',  # fa in iso-8859-2
    u'augusztus':     u'08',
    u'szeptember':    u'09',
    u'okt\u00f3ber':  u'10',  # f3 in iso-8859-2
    u'november':      u'11',
    u'december':      u'12',
  }

_hungarian_date_format_re = \
  re.compile(u'(\d{4})-([^-]+)-(\d{,2})T(\d{,2}):(\d{2})((\+|-)(\d{,2}:\d{2}))')

def _parse_date_hungarian(dateString):
    '''Parse a string according to a Hungarian 8-bit date format.'''
    m = _hungarian_date_format_re.match(dateString)
    if not m: return
    try:
        month = _hungarian_months[m.group(2)]
        day = m.group(3)
        if len(day) == 1:
            day = '0' + day
        hour = m.group(4)
        if len(hour) == 1:
            hour = '0' + hour
    except:
        return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s%(zonediff)s' % \
                {'year': m.group(1), 'month': month, 'day': day,\
                 'hour': hour, 'minute': m.group(5),\
                 'zonediff': m.group(6)}
    if _debug: sys.stderr.write('Hungarian date parsed as: %s\n' % w3dtfdate)
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_hungarian)

# W3DTF-style date parsing adapted from PyXML xml.utils.iso8601, written by
# Drake and licensed under the Python license.  Removed all range checking
# for month, day, hour, minute, and second, since mktime will normalize
# these later
def _parse_date_w3dtf(dateString):
    def __extract_date(m):
        year = int(m.group('year'))
        if year < 100:
            year = 100 * int(time.gmtime()[0] / 100) + int(year)
        if year < 1000:
            return 0, 0, 0
        julian = m.group('julian')
        if julian:
            julian = int(julian)
            month = julian / 30 + 1
            day = julian % 30 + 1
            jday = None
            while jday != julian:
                t = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
                jday = time.gmtime(t)[-2]
                diff = abs(jday - julian)
                if jday > julian:
                    if diff < day:
                        day = day - diff
                    else:
                        month = month - 1
                        day = 31
                elif jday < julian:
                    if day + diff < 28:
                       day = day + diff
                    else:
                        month = month + 1
            return year, month, day
        month = m.group('month')
        day = 1
        if month is None:
            month = 1
        else:
            month = int(month)
            day = m.group('day')
            if day:
                day = int(day)
            else:
                day = 1
        return year, month, day

    def __extract_time(m):
        if not m:
            return 0, 0, 0
        hours = m.group('hours')
        if not hours:
            return 0, 0, 0
        hours = int(hours)
        minutes = int(m.group('minutes'))
        seconds = m.group('seconds')
        if seconds:
            seconds = int(seconds)
        else:
            seconds = 0
        return hours, minutes, seconds

    def __extract_tzd(m):
        '''Return the Time Zone Designator as an offset in seconds from UTC.'''
        if not m:
            return 0
        tzd = m.group('tzd')
        if not tzd:
            return 0
        if tzd == 'Z':
            return 0
        hours = int(m.group('tzdhours'))
        minutes = m.group('tzdminutes')
        if minutes:
            minutes = int(minutes)
        else:
            minutes = 0
        offset = (hours*60 + minutes) * 60
        if tzd[0] == '+':
            return -offset
        return offset

    __date_re = ('(?P<year>\d\d\d\d)'
                 '(?:(?P<dsep>-|)'
                 '(?:(?P<julian>\d\d\d)'
                 '|(?P<month>\d\d)(?:(?P=dsep)(?P<day>\d\d))?))?')
    __tzd_re = '(?P<tzd>[-+](?P<tzdhours>\d\d)(?::?(?P<tzdminutes>\d\d))|Z)'
    __tzd_rx = re.compile(__tzd_re)
    __time_re = ('(?P<hours>\d\d)(?P<tsep>:|)(?P<minutes>\d\d)'
                 '(?:(?P=tsep)(?P<seconds>\d\d(?:[.,]\d+)?))?'
                 + __tzd_re)
    __datetime_re = '%s(?:T%s)?' % (__date_re, __time_re)
    __datetime_rx = re.compile(__datetime_re)
    m = __datetime_rx.match(dateString)
    if (m is None) or (m.group() != dateString): return
    gmt = __extract_date(m) + __extract_time(m) + (0, 0, 0)
    if gmt[0] == 0: return
    return time.gmtime(time.mktime(gmt) + __extract_tzd(m) - time.timezone)
registerDateHandler(_parse_date_w3dtf)

def _parse_date_rfc822(dateString):
    '''Parse an RFC822, RFC1123, RFC2822, or asctime-style date'''
    data = dateString.split()
    if data[0][-1] in (',', '.') or data[0].lower() in rfc822._daynames:
        del data[0]
    if len(data) == 4:
        s = data[3]
        i = s.find('+')
        if i > 0:
            data[3:] = [s[:i], s[i+1:]]
        else:
            data.append('')
        dateString = " ".join(data)
    if len(data) < 5:
        dateString += ' 00:00:00 GMT'
    tm = rfc822.parsedate_tz(dateString)
    if tm:
        return time.gmtime(rfc822.mktime_tz(tm))
# rfc822.py defines several time zones, but we define some extra ones.
# 'ET' is equivalent to 'EST', etc.
_additional_timezones = {'AT': -400, 'ET': -500, 'CT': -600, 'MT': -700, 'PT': -800}
rfc822._timezones.update(_additional_timezones)
registerDateHandler(_parse_date_rfc822)    

def _parse_date(dateString):
    '''Parses a variety of date formats into a 9-tuple in GMT'''
    for handler in _date_handlers:
        try:
            date9tuple = handler(dateString)
            if not date9tuple: continue
            if len(date9tuple) != 9:
                if _debug: sys.stderr.write('date handler function must return 9-tuple\n')
                raise ValueError
            map(int, date9tuple)
            return date9tuple
        except Exception, e:
            if _debug: sys.stderr.write('%s raised %s\n' % (handler.__name__, repr(e)))
            pass
    return None

def _getCharacterEncoding(http_headers, xml_data):
    '''Get the character encoding of the XML document

    http_headers is a dictionary
    xml_data is a raw string (not Unicode)
    
    This is so much trickier than it sounds, it's not even funny.
    According to RFC 3023 ('XML Media Types'), if the HTTP Content-Type
    is application/xml, application/*+xml,
    application/xml-external-parsed-entity, or application/xml-dtd,
    the encoding given in the charset parameter of the HTTP Content-Type
    takes precedence over the encoding given in the XML prefix within the
    document, and defaults to 'utf-8' if neither are specified.  But, if
    the HTTP Content-Type is text/xml, text/*+xml, or
    text/xml-external-parsed-entity, the encoding given in the XML prefix
    within the document is ALWAYS IGNORED and only the encoding given in
    the charset parameter of the HTTP Content-Type header should be
    respected, and it defaults to 'us-ascii' if not specified.

    Furthermore, discussion on the atom-syntax mailing list with the
    author of RFC 3023 leads me to the conclusion that any document
    served with a Content-Type of text/* and no charset parameter
    must be treated as us-ascii.  (We now do this.)  And also that it
    must always be flagged as non-well-formed.  (We now do this too.)
    
    If Content-Type is unspecified (input was local file or non-HTTP source)
    or unrecognized (server just got it totally wrong), then go by the
    encoding given in the XML prefix of the document and default to
    'iso-8859-1' as per the HTTP specification (RFC 2616).
    
    Then, assuming we didn't find a character encoding in the HTTP headers
    (and the HTTP Content-type allowed us to look in the body), we need
    to sniff the first few bytes of the XML data and try to determine
    whether the encoding is ASCII-compatible.  Section F of the XML
    specification shows the way here:
    http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info

    If the sniffed encoding is not ASCII-compatible, we need to make it
    ASCII compatible so that we can sniff further into the XML declaration
    to find the encoding attribute, which will tell us the true encoding.

    Of course, none of this guarantees that we will be able to parse the
    feed in the declared character encoding (assuming it was declared
    correctly, which many are not).  CJKCodecs and iconv_codec help a lot;
    you should definitely install them if you can.
    http://cjkpython.i18n.org/
    '''

    def _parseHTTPContentType(content_type):
        '''takes HTTP Content-Type header and returns (content type, charset)

        If no charset is specified, returns (content type, '')
        If no content type is specified, returns ('', '')
        Both return parameters are guaranteed to be lowercase strings
        '''
        content_type = content_type or ''
        content_type, params = cgi.parse_header(content_type)
        return content_type, params.get('charset', '').replace("'", '')

    sniffed_xml_encoding = ''
    xml_encoding = ''
    true_encoding = ''
    http_content_type, http_encoding = _parseHTTPContentType(http_headers.get('content-type'))
    # Must sniff for non-ASCII-compatible character encodings before
    # searching for XML declaration.  This heuristic is defined in
    # section F of the XML specification:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info
    try:
        if xml_data[:4] == '\x4c\x6f\xa7\x94':
            # EBCDIC
            xml_data = _ebcdic_to_ascii(xml_data)
        elif xml_data[:4] == '\x00\x3c\x00\x3f':
            # UTF-16BE
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16BE with BOM
            sniffed_xml_encoding = 'utf-16be'
            xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x3f\x00':
            # UTF-16LE
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
        elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and (xml_data[2:4] != '\x00\x00'):
            # UTF-16LE with BOM
            sniffed_xml_encoding = 'utf-16le'
            xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
        elif xml_data[:4] == '\x00\x00\x00\x3c':
            # UTF-32BE
            sniffed_xml_encoding = 'utf-32be'
            xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
        elif xml_data[:4] == '\x3c\x00\x00\x00':
            # UTF-32LE
            sniffed_xml_encoding = 'utf-32le'
            xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
        elif xml_data[:4] == '\x00\x00\xfe\xff':
            # UTF-32BE with BOM
            sniffed_xml_encoding = 'utf-32be'
            xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
        elif xml_data[:4] == '\xff\xfe\x00\x00':
            # UTF-32LE with BOM
            sniffed_xml_encoding = 'utf-32le'
            xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
        elif xml_data[:3] == '\xef\xbb\xbf':
            # UTF-8 with BOM
            sniffed_xml_encoding = 'utf-8'
            xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
        else:
            # ASCII-compatible
            pass
        xml_encoding_match = re.compile('^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
    except:
        xml_encoding_match = None
    if xml_encoding_match:
        xml_encoding = xml_encoding_match.groups()[0].lower()
        if sniffed_xml_encoding and (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode', 'iso-10646-ucs-4', 'ucs-4', 'csucs4', 'utf-16', 'utf-32', 'utf_16', 'utf_32', 'utf16', 'u16')):
            xml_encoding = sniffed_xml_encoding
    acceptable_content_type = 0
    application_content_types = ('application/xml', 'application/xml-dtd', 'application/xml-external-parsed-entity')
    text_content_types = ('text/xml', 'text/xml-external-parsed-entity')
    if (http_content_type in application_content_types) or \
       (http_content_type.startswith('application/') and http_content_type.endswith('+xml')):
        acceptable_content_type = 1
        true_encoding = http_encoding or xml_encoding or 'utf-8'
    elif (http_content_type in text_content_types) or \
         (http_content_type.startswith('text/')) and http_content_type.endswith('+xml'):
        acceptable_content_type = 1
        true_encoding = http_encoding or 'us-ascii'
    elif http_content_type.startswith('text/'):
        true_encoding = http_encoding or 'us-ascii'
    elif http_headers and (not http_headers.has_key('content-type')):
        true_encoding = xml_encoding or 'iso-8859-1'
    else:
        true_encoding = xml_encoding or 'utf-8'
    return true_encoding, http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type
    
def _toUTF8(data, encoding):
    '''Changes an XML data stream on the fly to specify a new encoding

    data is a raw sequence of bytes (not Unicode) that is presumed to be in %encoding already
    encoding is a string recognized by encodings.aliases
    '''
    if _debug: sys.stderr.write('entering _toUTF8, trying encoding %s\n' % encoding)
    # strip Byte Order Mark (if present)
    if (len(data) >= 4) and (data[:2] == '\xfe\xff') and (data[2:4] != '\x00\x00'):
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-16be':
                sys.stderr.write('trying utf-16be instead\n')
        encoding = 'utf-16be'
        data = data[2:]
    elif (len(data) >= 4) and (data[:2] == '\xff\xfe') and (data[2:4] != '\x00\x00'):
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-16le':
                sys.stderr.write('trying utf-16le instead\n')
        encoding = 'utf-16le'
        data = data[2:]
    elif data[:3] == '\xef\xbb\xbf':
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-8':
                sys.stderr.write('trying utf-8 instead\n')
        encoding = 'utf-8'
        data = data[3:]
    elif data[:4] == '\x00\x00\xfe\xff':
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-32be':
                sys.stderr.write('trying utf-32be instead\n')
        encoding = 'utf-32be'
        data = data[4:]
    elif data[:4] == '\xff\xfe\x00\x00':
        if _debug:
            sys.stderr.write('stripping BOM\n')
            if encoding != 'utf-32le':
                sys.stderr.write('trying utf-32le instead\n')
        encoding = 'utf-32le'
        data = data[4:]
    newdata = unicode(data, encoding)
    if _debug: sys.stderr.write('successfully converted %s data to unicode\n' % encoding)
    declmatch = re.compile('^<\?xml[^>]*?>')
    newdecl = '''<?xml version='1.0' encoding='utf-8'?>'''
    if declmatch.search(newdata):
        newdata = declmatch.sub(newdecl, newdata)
    else:
        newdata = newdecl + u'\n' + newdata
    return newdata.encode('utf-8')

def _stripDoctype(data):
    '''Strips DOCTYPE from XML document, returns (rss_version, stripped_data)

    rss_version may be 'rss091n' or None
    stripped_data is the same XML document, minus the DOCTYPE
    '''
    entity_pattern = re.compile(r'<!ENTITY([^>]*?)>', re.MULTILINE)
    data = entity_pattern.sub('', data)
    doctype_pattern = re.compile(r'<!DOCTYPE([^>]*?)>', re.MULTILINE)
    doctype_results = doctype_pattern.findall(data)
    doctype = doctype_results and doctype_results[0] or ''
    if doctype.lower().count('netscape'):
        version = 'rss091n'
    else:
        version = None
    data = doctype_pattern.sub('', data)
    return version, data
    
def parse(url_file_stream_or_string, etag=None, modified=None, agent=None, referrer=None, handlers=[]):
    '''Parse a feed from a URL, file, stream, or string'''
    result = FeedParserDict()
    result['feed'] = FeedParserDict()
    result['entries'] = []
    if _XML_AVAILABLE:
        result['bozo'] = 0
    if type(handlers) == types.InstanceType:
        handlers = [handlers]
    try:
        f = _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers)
        data = f.read()
    except Exception, e:
        result['bozo'] = 1
        result['bozo_exception'] = e
        data = ''
        f = None

    # if feed is gzip-compressed, decompress it
    if f and data and hasattr(f, 'headers'):
        if gzip and f.headers.get('content-encoding', '') == 'gzip':
            try:
                data = gzip.GzipFile(fileobj=_StringIO(data)).read()
            except Exception, e:
                # Some feeds claim to be gzipped but they're not, so
                # we get garbage.  Ideally, we should re-request the
                # feed without the 'Accept-encoding: gzip' header,
                # but we don't.
                result['bozo'] = 1
                result['bozo_exception'] = e
                data = ''
        elif zlib and f.headers.get('content-encoding', '') == 'deflate':
            try:
                data = zlib.decompress(data, -zlib.MAX_WBITS)
            except Exception, e:
                result['bozo'] = 1
                result['bozo_exception'] = e
                data = ''

    # save HTTP headers
    if hasattr(f, 'info'):
        info = f.info()
        result['etag'] = info.getheader('ETag')
        last_modified = info.getheader('Last-Modified')
        if last_modified:
            result['modified'] = _parse_date(last_modified)
    if hasattr(f, 'url'):
        result['href'] = f.url
        result['status'] = 200
    if hasattr(f, 'status'):
        result['status'] = f.status
    if hasattr(f, 'headers'):
        result['headers'] = f.headers.dict
    if hasattr(f, 'close'):
        f.close()

    # there are four encodings to keep track of:
    # - http_encoding is the encoding declared in the Content-Type HTTP header
    # - xml_encoding is the encoding declared in the <?xml declaration
    # - sniffed_encoding is the encoding sniffed from the first 4 bytes of the XML data
    # - result['encoding'] is the actual encoding, as per RFC 3023 and a variety of other conflicting specifications
    http_headers = result.get('headers', {})
    result['encoding'], http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type = \
        _getCharacterEncoding(http_headers, data)
    if http_headers and (not acceptable_content_type):
        if http_headers.has_key('content-type'):
            bozo_message = '%s is not an XML media type' % http_headers['content-type']
        else:
            bozo_message = 'no Content-type specified'
        result['bozo'] = 1
        result['bozo_exception'] = NonXMLContentType(bozo_message)
        
    result['version'], data = _stripDoctype(data)

    baseuri = http_headers.get('content-location', result.get('href'))
    baselang = http_headers.get('content-language', None)

    # if server sent 304, we're done
    if result.get('status', 0) == 304:
        result['version'] = ''
        result['debug_message'] = 'The feed has not changed since you last checked, ' + \
            'so the server sent no data.  This is a feature, not a bug!'
        return result

    # if there was a problem downloading, we're done
    if not data:
        return result

    # determine character encoding
    use_strict_parser = 0
    known_encoding = 0
    tried_encodings = []
    # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
    for proposed_encoding in (result['encoding'], xml_encoding, sniffed_xml_encoding):
        if not proposed_encoding: continue
        if proposed_encoding in tried_encodings: continue
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
            break
        except:
            pass
    # if no luck and we have auto-detection library, try that
    if (not known_encoding) and chardet:
        try:
            proposed_encoding = chardet.detect(data)['encoding']
            if proposed_encoding and (proposed_encoding not in tried_encodings):
                tried_encodings.append(proposed_encoding)
                data = _toUTF8(data, proposed_encoding)
                known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck and we haven't tried utf-8 yet, try that
    if (not known_encoding) and ('utf-8' not in tried_encodings):
        try:
            proposed_encoding = 'utf-8'
            tried_encodings.append(proposed_encoding)
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck and we haven't tried windows-1252 yet, try that
    if (not known_encoding) and ('windows-1252' not in tried_encodings):
        try:
            proposed_encoding = 'windows-1252'
            tried_encodings.append(proposed_encoding)
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck, give up
    if not known_encoding:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingUnknown( \
            'document encoding unknown, I tried ' + \
            '%s, %s, utf-8, and windows-1252 but nothing worked' % \
            (result['encoding'], xml_encoding))
        result['encoding'] = ''
    elif proposed_encoding != result['encoding']:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingOverride( \
            'documented declared as %s, but parsed as %s' % \
            (result['encoding'], proposed_encoding))
        result['encoding'] = proposed_encoding

    if not _XML_AVAILABLE:
        use_strict_parser = 0
    if use_strict_parser:
        # initialize the SAX parser
        feedparser = _StrictFeedParser(baseuri, baselang, 'utf-8')
        saxparser = xml.sax.make_parser(PREFERRED_XML_PARSERS)
        saxparser.setFeature(xml.sax.handler.feature_namespaces, 1)
        saxparser.setContentHandler(feedparser)
        saxparser.setErrorHandler(feedparser)
        source = xml.sax.xmlreader.InputSource()
        source.setByteStream(_StringIO(data))
        if hasattr(saxparser, '_ns_stack'):
            # work around bug in built-in SAX parser (doesn't recognize xml: namespace)
            # PyXML doesn't have this problem, and it doesn't have _ns_stack either
            saxparser._ns_stack.append({'http://www.w3.org/XML/1998/namespace':'xml'})
        try:
            saxparser.parse(source)
        except Exception, e:
            if _debug:
                import traceback
                traceback.print_stack()
                traceback.print_exc()
                sys.stderr.write('xml parsing failed\n')
            result['bozo'] = 1
            result['bozo_exception'] = feedparser.exc or e
            use_strict_parser = 0
    if not use_strict_parser:
        feedparser = _LooseFeedParser(baseuri, baselang, known_encoding and 'utf-8' or '')
        feedparser.feed(data)
    result['feed'] = feedparser.feeddata
    result['entries'] = feedparser.entries
    result['version'] = result['version'] or feedparser.version
    result['namespaces'] = feedparser.namespacesInUse
    return result

if __name__ == '__main__':
    if not sys.argv[1:]:
        print __doc__
        sys.exit(0)
    else:
        urls = sys.argv[1:]
    zopeCompatibilityHack()
    from pprint import pprint
    for url in urls:
        print url
        print
        result = parse(url)
        pprint(result)
        print

#REVISION HISTORY
#1.0 - 9/27/2002 - MAP - fixed namespace processing on prefixed RSS 2.0 elements,
#  added Simon Fell's test suite
#1.1 - 9/29/2002 - MAP - fixed infinite loop on incomplete CDATA sections
#2.0 - 10/19/2002
#  JD - use inchannel to watch out for image and textinput elements which can
#  also contain title, link, and description elements
#  JD - check for isPermaLink='false' attribute on guid elements
#  JD - replaced openAnything with open_resource supporting ETag and
#  If-Modified-Since request headers
#  JD - parse now accepts etag, modified, agent, and referrer optional
#  arguments
#  JD - modified parse to return a dictionary instead of a tuple so that any
#  etag or modified information can be returned and cached by the caller
#2.0.1 - 10/21/2002 - MAP - changed parse() so that if we don't get anything
#  because of etag/modified, return the old etag/modified to the caller to
#  indicate why nothing is being returned
#2.0.2 - 10/21/2002 - JB - added the inchannel to the if statement, otherwise its
#  useless.  Fixes the problem JD was addressing by adding it.
#2.1 - 11/14/2002 - MAP - added gzip support
#2.2 - 1/27/2003 - MAP - added attribute support, admin:generatorAgent.
#  start_admingeneratoragent is an example of how to handle elements with
#  only attributes, no content.
#2.3 - 6/11/2003 - MAP - added USER_AGENT for default (if caller doesn't specify);
#  also, make sure we send the User-Agent even if urllib2 isn't available.
#  Match any variation of backend.userland.com/rss namespace.
#2.3.1 - 6/12/2003 - MAP - if item has both link and guid, return both as-is.
#2.4 - 7/9/2003 - MAP - added preliminary Pie/Atom/Echo support based on Sam Ruby's
#  snapshot of July 1 <http://www.intertwingly.net/blog/1506.html>; changed
#  project name
#2.5 - 7/25/2003 - MAP - changed to Python license (all contributors agree);
#  removed unnecessary urllib code -- urllib2 should always be available anyway;
#  return actual url, status, and full HTTP headers (as result['url'],
#  result['status'], and result['headers']) if parsing a remote feed over HTTP --
#  this should pass all the HTTP tests at <http://diveintomark.org/tests/client/http/>;
#  added the latest namespace-of-the-week for RSS 2.0
#2.5.1 - 7/26/2003 - RMK - clear opener.addheaders so we only send our custom
#  User-Agent (otherwise urllib2 sends two, which confuses some servers)
#2.5.2 - 7/28/2003 - MAP - entity-decode inline xml properly; added support for
#  inline <xhtml:body> and <xhtml:div> as used in some RSS 2.0 feeds
#2.5.3 - 8/6/2003 - TvdV - patch to track whether we're inside an image or
#  textInput, and also to return the character encoding (if specified)
#2.6 - 1/1/2004 - MAP - dc:author support (MarekK); fixed bug tracking
#  nested divs within content (JohnD); fixed missing sys import (JohanS);
#  fixed regular expression to capture XML character encoding (Andrei);
#  added support for Atom 0.3-style links; fixed bug with textInput tracking;
#  added support for cloud (MartijnP); added support for multiple
#  category/dc:subject (MartijnP); normalize content model: 'description' gets
#  description (which can come from description, summary, or full content if no
#  description), 'content' gets dict of base/language/type/value (which can come
#  from content:encoded, xhtml:body, content, or fullitem);
#  fixed bug matching arbitrary Userland namespaces; added xml:base and xml:lang
#  tracking; fixed bug tracking unknown tags; fixed bug tracking content when
#  <content> element is not in default namespace (like Pocketsoap feed);
#  resolve relative URLs in link, guid, docs, url, comments, wfw:comment,
#  wfw:commentRSS; resolve relative URLs within embedded HTML markup in
#  description, xhtml:body, content, content:encoded, title, subtitle,
#  summary, info, tagline, and copyright; added support for pingback and
#  trackback namespaces
#2.7 - 1/5/2004 - MAP - really added support for trackback and pingback
#  namespaces, as opposed to 2.6 when I said I did but didn't really;
#  sanitize HTML markup within some elements; added mxTidy support (if
#  installed) to tidy HTML markup within some elements; fixed indentation
#  bug in _parse_date (FazalM); use socket.setdefaulttimeout if available
#  (FazalM); universal date parsing and normalization (FazalM): 'created', modified',
#  'issued' are parsed into 9-tuple date format and stored in 'created_parsed',
#  'modified_parsed', and 'issued_parsed'; 'date' is duplicated in 'modified'
#  and vice-versa; 'date_parsed' is duplicated in 'modified_parsed' and vice-versa
#2.7.1 - 1/9/2004 - MAP - fixed bug handling &quot; and &apos;.  fixed memory
#  leak not closing url opener (JohnD); added dc:publisher support (MarekK);
#  added admin:errorReportsTo support (MarekK); Python 2.1 dict support (MarekK)
#2.7.4 - 1/14/2004 - MAP - added workaround for improperly formed <br/> tags in
#  encoded HTML (skadz); fixed unicode handling in normalize_attrs (ChrisL);
#  fixed relative URI processing for guid (skadz); added ICBM support; added
#  base64 support
#2.7.5 - 1/15/2004 - MAP - added workaround for malformed DOCTYPE (seen on many
#  blogspot.com sites); added _debug variable
#2.7.6 - 1/16/2004 - MAP - fixed bug with StringIO importing
#3.0b3 - 1/23/2004 - MAP - parse entire feed with real XML parser (if available);
#  added several new supported namespaces; fixed bug tracking naked markup in
#  description; added support for enclosure; added support for source; re-added
#  support for cloud which got dropped somehow; added support for expirationDate
#3.0b4 - 1/26/2004 - MAP - fixed xml:lang inheritance; fixed multiple bugs tracking
#  xml:base URI, one for documents that don't define one explicitly and one for
#  documents that define an outer and an inner xml:base that goes out of scope
#  before the end of the document
#3.0b5 - 1/26/2004 - MAP - fixed bug parsing multiple links at feed level
#3.0b6 - 1/27/2004 - MAP - added feed type and version detection, result['version']
#  will be one of SUPPORTED_VERSIONS.keys() or empty string if unrecognized;
#  added support for creativeCommons:license and cc:license; added support for
#  full Atom content model in title, tagline, info, copyright, summary; fixed bug
#  with gzip encoding (not always telling server we support it when we do)
#3.0b7 - 1/28/2004 - MAP - support Atom-style author element in author_detail
#  (dictionary of 'name', 'url', 'email'); map author to author_detail if author
#  contains name + email address
#3.0b8 - 1/28/2004 - MAP - added support for contributor
#3.0b9 - 1/29/2004 - MAP - fixed check for presence of dict function; added
#  support for summary
#3.0b10 - 1/31/2004 - MAP - incorporated ISO-8601 date parsing routines from
#  xml.util.iso8601
#3.0b11 - 2/2/2004 - MAP - added 'rights' to list of elements that can contain
#  dangerous markup; fiddled with decodeEntities (not right); liberalized
#  date parsing even further
#3.0b12 - 2/6/2004 - MAP - fiddled with decodeEntities (still not right);
#  added support to Atom 0.2 subtitle; added support for Atom content model
#  in copyright; better sanitizing of dangerous HTML elements with end tags
#  (script, frameset)
#3.0b13 - 2/8/2004 - MAP - better handling of empty HTML tags (br, hr, img,
#  etc.) in embedded markup, in either HTML or XHTML form (<br>, <br/>, <br />)
#3.0b14 - 2/8/2004 - MAP - fixed CDATA handling in non-wellformed feeds under
#  Python 2.1
#3.0b15 - 2/11/2004 - MAP - fixed bug resolving relative links in wfw:commentRSS;
#  fixed bug capturing author and contributor URL; fixed bug resolving relative
#  links in author and contributor URL; fixed bug resolvin relative links in
#  generator URL; added support for recognizing RSS 1.0; passed Simon Fell's
#  namespace tests, and included them permanently in the test suite with his
#  permission; fixed namespace handling under Python 2.1
#3.0b16 - 2/12/2004 - MAP - fixed support for RSS 0.90 (broken in b15)
#3.0b17 - 2/13/2004 - MAP - determine character encoding as per RFC 3023
#3.0b18 - 2/17/2004 - MAP - always map description to summary_detail (Andrei);
#  use libxml2 (if available)
#3.0b19 - 3/15/2004 - MAP - fixed bug exploding author information when author
#  name was in parentheses; removed ultra-problematic mxTidy support; patch to
#  workaround crash in PyXML/expat when encountering invalid entities
#  (MarkMoraes); support for textinput/textInput
#3.0b20 - 4/7/2004 - MAP - added CDF support
#3.0b21 - 4/14/2004 - MAP - added Hot RSS support
#3.0b22 - 4/19/2004 - MAP - changed 'channel' to 'feed', 'item' to 'entries' in
#  results dict; changed results dict to allow getting values with results.key
#  as well as results[key]; work around embedded illformed HTML with half
#  a DOCTYPE; work around malformed Content-Type header; if character encoding
#  is wrong, try several common ones before falling back to regexes (if this
#  works, bozo_exception is set to CharacterEncodingOverride); fixed character
#  encoding issues in BaseHTMLProcessor by tracking encoding and converting
#  from Unicode to raw strings before feeding data to sgmllib.SGMLParser;
#  convert each value in results to Unicode (if possible), even if using
#  regex-based parsing
#3.0b23 - 4/21/2004 - MAP - fixed UnicodeDecodeError for feeds that contain
#  high-bit characters in attributes in embedded HTML in description (thanks
#  Thijs van de Vossen); moved guid, date, and date_parsed to mapped keys in
#  FeedParserDict; tweaked FeedParserDict.has_key to return True if asking
#  about a mapped key
#3.0fc1 - 4/23/2004 - MAP - made results.entries[0].links[0] and
#  results.entries[0].enclosures[0] into FeedParserDict; fixed typo that could
#  cause the same encoding to be tried twice (even if it failed the first time);
#  fixed DOCTYPE stripping when DOCTYPE contained entity declarations;
#  better textinput and image tracking in illformed RSS 1.0 feeds
#3.0fc2 - 5/10/2004 - MAP - added and passed Sam's amp tests; added and passed
#  my blink tag tests
#3.0fc3 - 6/18/2004 - MAP - fixed bug in _changeEncodingDeclaration that
#  failed to parse utf-16 encoded feeds; made source into a FeedParserDict;
#  duplicate admin:generatorAgent/@rdf:resource in generator_detail.url;
#  added support for image; refactored parse() fallback logic to try other
#  encodings if SAX parsing fails (previously it would only try other encodings
#  if re-encoding failed); remove unichr madness in normalize_attrs now that
#  we're properly tracking encoding in and out of BaseHTMLProcessor; set
#  feed.language from root-level xml:lang; set entry.id from rdf:about;
#  send Accept header
#3.0 - 6/21/2004 - MAP - don't try iso-8859-1 (can't distinguish between
#  iso-8859-1 and windows-1252 anyway, and most incorrectly marked feeds are
#  windows-1252); fixed regression that could cause the same encoding to be
#  tried twice (even if it failed the first time)
#3.0.1 - 6/22/2004 - MAP - default to us-ascii for all text/* content types;
#  recover from malformed content-type header parameter with no equals sign
#  ('text/xml; charset:iso-8859-1')
#3.1 - 6/28/2004 - MAP - added and passed tests for converting HTML entities
#  to Unicode equivalents in illformed feeds (aaronsw); added and
#  passed tests for converting character entities to Unicode equivalents
#  in illformed feeds (aaronsw); test for valid parsers when setting
#  XML_AVAILABLE; make version and encoding available when server returns
#  a 304; add handlers parameter to pass arbitrary urllib2 handlers (like
#  digest auth or proxy support); add code to parse username/password
#  out of url and send as basic authentication; expose downloading-related
#  exceptions in bozo_exception (aaronsw); added __contains__ method to
#  FeedParserDict (aaronsw); added publisher_detail (aaronsw)
#3.2 - 7/3/2004 - MAP - use cjkcodecs and iconv_codec if available; always
#  convert feed to UTF-8 before passing to XML parser; completely revamped
#  logic for determining character encoding and attempting XML parsing
#  (much faster); increased default timeout to 20 seconds; test for presence
#  of Location header on redirects; added tests for many alternate character
#  encodings; support various EBCDIC encodings; support UTF-16BE and
#  UTF16-LE with or without a BOM; support UTF-8 with a BOM; support
#  UTF-32BE and UTF-32LE with or without a BOM; fixed crashing bug if no
#  XML parsers are available; added support for 'Content-encoding: deflate';
#  send blank 'Accept-encoding: ' header if neither gzip nor zlib modules
#  are available
#3.3 - 7/15/2004 - MAP - optimize EBCDIC to ASCII conversion; fix obscure
#  problem tracking xml:base and xml:lang if element declares it, child
#  doesn't, first grandchild redeclares it, and second grandchild doesn't;
#  refactored date parsing; defined public registerDateHandler so callers
#  can add support for additional date formats at runtime; added support
#  for OnBlog, Nate, MSSQL, Greek, and Hungarian dates (ytrewq1); added
#  zopeCompatibilityHack() which turns FeedParserDict into a regular
#  dictionary, required for Zope compatibility, and also makes command-
#  line debugging easier because pprint module formats real dictionaries
#  better than dictionary-like objects; added NonXMLContentType exception,
#  which is stored in bozo_exception when a feed is served with a non-XML
#  media type such as 'text/plain'; respect Content-Language as default
#  language if not xml:lang is present; cloud dict is now FeedParserDict;
#  generator dict is now FeedParserDict; better tracking of xml:lang,
#  including support for xml:lang='' to unset the current language;
#  recognize RSS 1.0 feeds even when RSS 1.0 namespace is not the default
#  namespace; don't overwrite final status on redirects (scenarios:
#  redirecting to a URL that returns 304, redirecting to a URL that
#  redirects to another URL with a different type of redirect); add
#  support for HTTP 303 redirects
#4.0 - MAP - support for relative URIs in xml:base attribute; fixed
#  encoding issue with mxTidy (phopkins); preliminary support for RFC 3229;
#  support for Atom 1.0; support for iTunes extensions; new 'tags' for
#  categories/keywords/etc. as array of dict
#  {'term': term, 'scheme': scheme, 'label': label} to match Atom 1.0
#  terminology; parse RFC 822-style dates with no time; lots of other
#  bug fixes
#4.1 - MAP - removed socket timeout; added support for chardet library

########NEW FILE########
__FILENAME__ = parse_pony_build_rss
import feedparser
from datetime import datetime
from HTMLParser import HTMLParser

date_format = "%a, %d %b %Y %H:%M:%S GMT"

class _ExtractedInfo(HTMLParser):
    def __init__(self, content):
        HTMLParser.__init__(self)
        self.values = {}

        self.feed(content)
        self.close()
        
    def handle_data(self, data):
        k, v = data.split(': ', 1)
        self.values[k] = v

class PonyBuildRSSParser(object):
    def __init__(self):
        pass

    def consume_feed(self, content):
        # extract the most recent entry, return datetime, entry, k/v dict
        
        d = feedparser.parse(content)

        extract_date = lambda entry: datetime.strptime(entry.date, date_format)
        entries = sorted(d.entries, key=extract_date, reverse=True)

        latest_entry = entries[0]
        dt = datetime.strptime(latest_entry.date, date_format)
        p = _ExtractedInfo(latest_entry.summary_detail.value)

        return dt, latest_entry, p.values

if __name__ == '__main__':
    import sys

    p = PonyBuildRSSParser()
    dt, entry, values = p.consume_feed(open(sys.argv[1]))

    print dt
    print entry
    print values

    print entry.title_detail.value
    print entry.link

########NEW FILE########
__FILENAME__ = test-post-rss
#! /usr/bin/env python
import sys
import httplib
from urlparse import urlparse

url = urlparse(sys.argv[1])

print url.hostname, url.port, url.path

data = open('rss-test-example.rss').read()
h = httplib.HTTPConnection(url.hostname, url.port)
h.request('POST', url.path, data)
print h.getresponse().read()

########NEW FILE########
__FILENAME__ = coordinator
"""
The XML-RPC & internal API for pony-build.

You can get the current coordinator object by calling
pony_build.server.get_coordinator().
"""

import time
from datetime import datetime, timedelta
import UserDict
import os, os.path
import uuid

from .file_storage import UploadedFile, sweep, get_file_catalog

# default duration allocated to a build
DEFAULT_BUILD_DURATION=60*60            # in seconds <== 1 hr

# the maximum request for a build allowance
MAX_BUILD_ALLOWANCE=4*60*60               # in seconds <== 1 hr

class IntDictWrapper(object, UserDict.DictMixin):
    def __init__(self, d):
        self.d = d

    def __getitem__(self, k):
        k = str(int(k))
        return self.d[k]

    def __setitem__(self, k, v):
        k = str(int(k))
        self.d[k] = v

    def __delitem__(self, k):
        k = str(int(k))
        self.d.__delitem__(k)

    def keys(self):
        return [ int(x) for x in self.d.keys() ]

    def sync(self):
        if hasattr(self.d, 'sync'):
            self.d.sync()

    def close(self):
        if hasattr(self.d, 'close'):
            self.d.close()

def build_tagset(client_info, no_arch=False, no_host=False):
    arch = client_info['arch']
    host = client_info['host']
    package = client_info['package']

    if client_info['tags'] is not None:
        tags = list(client_info['tags'])
    else:
        tags = []

    tags.append('__package=' + package)
    if not no_arch:
        tags.append('__arch=' + arch)
    if not no_host:
        tags.append('__host=' + host)

    tagset = frozenset(tags)
    return tagset

class PonyBuildCoordinator(object):
    def __init__(self, db=None):
        self.db = db

        self._process_results()
        self.request_build = {}
        self.is_building = {}
        self.listeners = []
        self.change_consumers = {}

        # @CTB another database hack; yay?
        self.files = IntDictWrapper(get_file_catalog())

        self.auth_keys = {}             # map uuids to result keys

    def add_listener(self, x):
        self.listeners.append(x)

    def notify_build(self, package, client_info, requested_allowance=None):
        tagset = build_tagset(client_info)
        self.is_building[tagset] = (time.time(), requested_allowance)

    def add_results(self, client_ip, client_info, results):
#        print client_ip
#        print client_info
#        print results
#        print '---'
        receipt = dict(time=time.time(), client_ip=client_ip)

        key = self.db_add_result(receipt, client_ip, client_info, results)
        self._process_results()

        for x in self.listeners:
            x.notify_result_added(key)

        # only allow modifications (e.g. file uploads) using this auth key,
        # which is (in theory) unpredictable.  Tie it to the results key.
        unique_id = uuid.uuid4().hex
        self.auth_keys[unique_id] = key
        
        return (key, unique_id)

    def set_request_build(self, client_info, value):
        # note: setting value=False is a way to override value=True.
        tagset = build_tagset(client_info)
        self.request_build[tagset] = value

    def check_should_build(self, client_info, keep_request=False):
        """
        Returns tuple: ('should_build_flag, reason')
        """
        package = client_info['package']
        tagset = build_tagset(client_info)
        
        last_build = self.get_unique_tagsets_for_package(package)

        if self.request_build.get(tagset, False):
            if not keep_request:
                self.request_build.pop(tagset)
            return True, 'build requested'
        
        if tagset in self.is_building:
            (last_t, requested) = self.is_building[tagset]
            last_t = datetime.fromtimestamp(last_t)
            
            now = datetime.now()
            diff = now - last_t

            if not requested:
                requested = DEFAULT_BUILD_DURATION
                if tagset in last_build:
                    requested = last_build[tagset][1].get('duration',
                                                          requested)
            requested = timedelta(0, requested) # seconds

            if diff < requested:
                return False, 'may be in build now'
                
        if tagset in last_build:
            last_t = last_build[tagset][0]['time']
            last_t = datetime.fromtimestamp(last_t)
            
            now = datetime.now()
            diff = now - last_t
            if diff >= timedelta(1): # 1 day, default
                return True, 'last build was %s ago; do build!' % (diff,)

            # was it successful?
            success = last_build[tagset][1]['success']
            if not success:
                return True, 'last build was unsuccessful; go!'
        else:
            # tagset not in last_build
            return True, 'no build recorded for %s; build!' % (tagset,)

        return False, "build up to date"

    def _process_results(self):
        self._hosts = hosts = {}
        self._archs = archs = {}
        self._packages = packages = {}

        now = datetime.now()
        a_week = timedelta(days=7)

        keys = list(reversed(sorted(self.db.keys())))
        kept_count = 0
        for k in keys:
            (receipt, client_info, results_list) = self.db[k]

            t = receipt['time']
            t = datetime.fromtimestamp(t)

            if now - t > a_week:
                break
            
            kept_count += 1

            host = client_info['host']
            arch = client_info['arch']
            pkg = client_info['package']

            l = hosts.get(host, [])
            l.insert(0, k)
            hosts[host] = l

            l = archs.get(arch, [])
            l.insert(0, k)
            archs[arch] = l

            l = packages.get(pkg, [])
            l.insert(0, k)
            packages[pkg] = l

        print 'discarded', len(keys) - kept_count, 'week+-old results of', len(keys)

    def db_get_result_info(self, result_id):
        return self.db[result_id]

    def db_add_result(self, receipt, client_ip, client_info, results):
        next_key = 0
        if self.db:
            next_key = max(self.db.keys()) + 1

        receipt['result_key'] = str(next_key)
                
        self.db[next_key] = (receipt, client_info, results)
        self.db.sync()

        return next_key

    def db_add_uploaded_file(self, auth_key, filename, content, description,
                             visible):
        if auth_key not in self.auth_keys:
            return False
        
        result_key = self.auth_keys[auth_key]

        subdir = str(result_key)
        fileobj = UploadedFile(subdir, filename, description, visible)
        fileobj.make_subdir()
        fp = fileobj.open('wb')
        fp.write(content)
        fp.close()

        file_list = self.files.get(result_key, [])
        file_list.append(fileobj)
        self.files[result_key] = file_list
        self.files.sync()

        sweep()

        return True

    def notify_of_changes(self, package, format, change_info):
        x = self.change_consumers.get(package)
        if x:
            for consumer in x:
                try:
                    consumer(package, format, change_info)
                except:
                    print 'ERROR on calling', consumer
                    print 'parameters:', package, format
                    traceback.print_exc()
            
        print 'XXX', package, format, change_info

    def add_change_consumer(self, package, consumer):
        x = self.change_consumers.get(package, [])
        x.append(consumer)
        self.change_consumers[package] = x

    def get_files_for_result(self, key):
        return self.files.get(key, [])

    def get_all_packages(self):
        k = self._packages.keys()
        k.sort()
        return k

    def get_last_result_for_package(self, package):
        x = self._packages.get(package)
        if x:
            return x[-1]
        return None

    def get_all_results_for_package(self, package):
        l = self._packages.get(package, [])
        if l:
            return [ self.db[n] for n in l ]
        return []

    def get_all_archs(self):
        k = self._archs.keys()
        k.sort()
        return k

    def get_last_result_for_arch(self, arch):
        x = self._archs.get(arch)
        if x:
            return x[-1]
        return None
    

    def get_all_hosts(self):
        k = self._hosts.keys()
        k.sort()
        return k

    def get_last_result_for_host(self, host):
        x = self._hosts.get(host)
        if x:
            return x[-1]
        return None

    def get_latest_arch_result_for_package(self, package):
        d = {}
        for arch, l in self._archs.iteritems():
            for n in l:
                receipt, client_info, results = self.db[n]
                if client_info['package'] == package:
                    d[arch] = (receipt, client_info, results)

        return d

    def get_unique_tagsets_for_package(self, package,
                                      no_host=False, no_arch=False):
        """
        Get the 'unique' set of latest results for the given package,
        based on tags, host, and architecture.  'no_host' says to
        collapse multiple hosts, 'no_arch' says to ignore multiple
        archs.

        Returns a dictionary of (receipt, client_info, results_list)
        tuples indexed by the set of keys used for 'uniqueness',
        i.e. an ImmutableSet of the tags + host + arch.  For display
        purposes, anything beginning with a '__' should be filtered
        out of the keys.
        
        """
        result_indices = self._packages.get(package)
        if not result_indices:
            return {}

        d = {}
        for n in result_indices:
            receipt, client_info, results_list = self.db[n]
            key = build_tagset(client_info, no_host=no_host, no_arch=no_arch)
            
            # check if already stored
            if key in d:
                receipt2, _, _ = d[key]
                # store the more recent one...
                if receipt['time'] > receipt2['time']:
                    d[key] = receipt, client_info, results_list
            else:
                d[key] = receipt, client_info, results_list

        return d

    def get_tagsets_for_package(self, package, no_host=False, no_arch=False):
        result_indices = self._packages.get(package)
        if not result_indices:
            return []

        x = set()
        for n in result_indices:
            receipt, client_info, results_list = self.db[n]
            key = build_tagset(client_info, no_host=no_host, no_arch=no_arch)

            x.add(key)

        return list(x)

    def get_last_result_for_tagset(self, package, tagset):
        result_indices = self._packages.get(package)
        if not result_indices:
            return 0

        result_indices.reverse()
        for n in result_indices:
            receipt, client_info, results_list = self.db[n]
            key = build_tagset(client_info)

            if set(tagset) == set(key):
                return (receipt, client_info, results_list)

        return 0

########NEW FILE########
__FILENAME__ = dbsqlite
''' Dbm based on sqlite -- Needed to support shelves

Issues:

    # ??? how to coordinate with whichdb
    # ??? Any difference between blobs and text
    # ??? does default encoding affect str-->bytes or PySqlite3 always use UTF-8
    # ??? what is the correct isolation mode

'''

__all__ = ['error', 'open']

import sqlite3
from UserDict import DictMixin
import collections
from operator import itemgetter
import shelve

error = sqlite3.DatabaseError

class SQLhash(object, DictMixin):
    def __init__(self, filename=':memory:', flags='r', mode=None,
                 tablename='shelf'):
        # XXX add flag/mode handling
        #   c -- create if it doesn't exist
        #   n -- new empty
        #   w -- open existing
        #   r -- readonly

        self.tablename = tablename

        MAKE_SHELF = 'CREATE TABLE IF NOT EXISTS %s (key TEXT PRIMARY KEY, value TEXT NOT NULL)' % self.tablename
        self.conn = sqlite3.connect(filename)
        self.conn.text_factory = str
        self.conn.execute(MAKE_SHELF)
        self.conn.commit()

    def __len__(self):
        GET_LEN = 'SELECT COUNT(*) FROM %s' % self.tablename
        return self.conn.execute(GET_LEN).fetchone()[0]

    def __bool__(self):
        # returns None if count is zero
        GET_BOOL = 'SELECT MAX(ROWID) FROM %s' % self.tablename
        return self.conn.execute(GET_BOOL).fetchone()[0] is not None

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def __iter__(self):
        return self.iterkeys()

    def iterkeys(self):
        GET_KEYS = 'SELECT key FROM %s ORDER BY ROWID' % self.tablename
        return iter(SQLHashIterator(self.conn, GET_KEYS, (0,)))

    def itervalues(self):
        GET_VALUES = 'SELECT value FROM %s ORDER BY ROWID' % self.tablename
        return iter(SQLHashIterator(self.conn, GET_VALUES, (0,)))

    def iteritems(self):
        GET_ITEMS = 'SELECT key, value FROM %s ORDER BY ROWID' % self.tablename
        return iter(SQLHashIterator(self.conn, GET_ITEMS, (0, 1)))

    def __contains__(self, key):
        HAS_ITEM = 'SELECT 1 FROM %s WHERE key = ?' % self.tablename
        return self.conn.execute(HAS_ITEM, (key,)).fetchone() is not None

    def __getitem__(self, key):
        GET_ITEM = 'SELECT value FROM %s WHERE key = ?' % self.tablename
        item = self.conn.execute(GET_ITEM, (key,)).fetchone()
        if item is None:
            raise KeyError(key)

        return item[0]

    def __setitem__(self, key, value):       
        ADD_ITEM = 'REPLACE INTO %s (key, value) VALUES (?,?)' % self.tablename
        self.conn.execute(ADD_ITEM, (key, value))
        #self.conn.commit()

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        DEL_ITEM = 'DELETE FROM %s WHERE key = ?' % self.tablename
        self.conn.execute(DEL_ITEM, (key,))
        #self.conn.commit()

    def update(self, items=(), **kwds):
        try:
            items = items.items()
        except AttributeError:
            pass

        UPDATE_ITEMS = 'REPLACE INTO %s (key, value) VALUES (?, ?)' % \
                       self.tablename

        self.conn.executemany(UPDATE_ITEMS, items)
        self.conn.commit()
        if kwds:
            self.update(kwds)

    def clear(self):        
        CLEAR_ALL = 'DELETE FROM %s; VACUUM;' % self.tablename
        self.conn.executescript(CLEAR_ALL)
        self.conn.commit()

    def sync(self):
        if self.conn is not None:    
            self.conn.commit()

    def close(self):
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def __del__(self):
        self.close()

def open(file=None, *args):
    if file is not None:
        return SQLhash(file)
    return SQLhash()

def open_shelf(file=None, *args):
    _db = open(file, *args)
    return shelve.Shelf(_db)

class SQLHashIterator(object):
    def __init__(self, conn, stmt, indices):
        c = conn.cursor()
        c.execute(stmt)
        
        self.iter = iter(c)
        self.getter = itemgetter(*indices)

    def __iter__(self):
        return self

    def next(self):
        return self.getter(self.iter.next())

if __name__ in '__main___':
    for d in SQLhash(), SQLhash('example'):
        list(d)
        print(list(d), "start")
        d['abc'] = 'lmno'
        print(d['abc'])    
        d['abc'] = 'rsvp'
        d['xyz'] = 'pdq'
        print(d.items())
        print(d.values())
        print('***', d.keys())
        print(list(d), 'list')
        d.update(p='x', q='y', r='z')
        print(d.items())
        
        del d['abc']
        try:
            print(d['abc'])
        except KeyError:
            pass
        else:
            raise Exception('oh noooo!')
        
        try:
            del d['abc']
        except KeyError:
            pass
        else:
            raise Exception('drat!')

        print(list(d))
        print(bool(d), True)        
        d.clear()
        print(bool(d), False)
        print(list(d))
        d.update(p='x', q='y', r='z')
        print(list(d))
        d['xyz'] = 'pdq'

        print()
        d.close()

########NEW FILE########
__FILENAME__ = file_storage
"""
A KISS file storage system for tracking and expiring uploaded files.

Stores files under '.files' in the directory above the pony-build main,
OR wherever is specified by the 'PONY_BUILD_FILES' environment variable.

@CTB both 'open' and 'sweep' need to lock in multithreading situations.

"""
import os
from os.path import join, getsize, getmtime
import shutil
import urllib

###

FILE_LIMIT = 50*1000*1000

### files location

if 'PONY_BUILD_FILES' in os.environ:
    files_dir = os.path.abspath(os.environ['PONY_BUILD_FILES'])
else:
    files_dir = os.path.dirname(__file__)
    files_dir = os.path.join(files_dir, '..', '.files')
    files_dir = os.path.abspath(files_dir)

if not os.path.exists(files_dir):
    os.mkdir(files_dir)

print 'putting uploaded files into %s' % files_dir

def get_file_catalog():
    import dbsqlite
    return dbsqlite.open_shelf(os.path.join(files_dir, 'catalog.sqlite'))

def sweep():
    """
    Expire files based on oldest-dir-first, once the total is over the limit.

    For small caches, files from infrequently-updated packages may be
    entirely eliminated in favor keeping uploads from regularly
    updated packages. A smarter way to do this would be to group files
    by package and do an initial sweep within all the packages.

    Or you could just increase the disk space you've allocated to the cache ;)
    
    """
    print '** sweeping uploaded_files cache'
    sizes = {}
    times = {}
    for root, dirs, files in os.walk(files_dir):
        if root == files_dir:
            continue

        sizes[root] = sum(getsize(join(root, name)) for name in files)
        times[root] = os.path.getmtime(root)

    times = times.items()
    times = sorted(times, key = lambda x: x[1], reverse=True)

    sumsize = 0
    rm_list = []
    for path, _ in times:
        sumsize += sizes[path]

        if sumsize > FILE_LIMIT:
            rm_list.append(path)

    if rm_list:
        for path in rm_list:
            print 'REMOVING', path
            shutil.rmtree(path)
    else:
        print '** nothing to remove'

###

class UploadedFile(object):
    """
    Provide storage, file path munging and safety checks for uploaded files.
    """
    def __init__(self, subdir, filename, description, visible):
        self.subdir = subdir
        self.filename = filename
        self.description = description
        self.visible = visible

    def make_subdir(self):
        """
        Make sure the specified subdirectory exists, and make it if not.
        """
        subdir = os.path.join(files_dir, self.subdir)
        subdir = os.path.abspath(subdir)
        if not os.path.isdir(subdir):
            os.mkdir(subdir)

    def _make_abspath(self):
        """
        Munge the file path us urllib.quote_plus, and make sure it's under
        the right directory.
        """
        safe_path = urllib.quote_plus(self.filename)
        fullpath = os.path.join(files_dir, self.subdir, safe_path)
        fullpath = os.path.abspath(fullpath)
        if not fullpath.startswith(files_dir):
            raise Exception("security warning: %s not under %s" % \
                            (self.filename, files_dir))
        return fullpath

    def exists(self):
        "Check to see if the file still exists."
        return os.path.isfile(self._make_abspath())

    def size(self):
        "Return the size, in bytes, of the file."
        return os.path.getsize(self._make_abspath())

    def open(self, mode='rb'):
        "Provide a handle to the file contents.  Make sure to use binary..."
        return open(self._make_abspath(), mode)

########NEW FILE########
__FILENAME__ = pubsubhubbub_publish
#!/usr/bin/env python
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Simple Publisher client for PubSubHubbub.

Example usage:

  from pubsubhubbub_publish import *
  try:
    publish('http://pubsubhubbub.appspot.com',
            'http://example.com/feed1/atom.xml',
            'http://example.com/feed2/atom.xml',
            'http://example.com/feed3/atom.xml')
  except PublishError, e:
    # handle exception...

Set the 'http_proxy' environment variable on *nix or Windows to use an
HTTP proxy.
"""

__author__ = 'bslatkin@gmail.com (Brett Slatkin)'

import urllib
import urllib2


class PublishError(Exception):
  """An error occurred while trying to publish to the hub."""


URL_BATCH_SIZE = 100


def publish(hub, *urls):
  """Publishes an event to a hub.

  Args:
    hub: The hub to publish the event to.
    **urls: One or more URLs to publish to. If only a single URL argument is
      passed and that item is an iterable that is not a string, the contents of
      that iterable will be used to produce the list of published URLs. If
      more than URL_BATCH_SIZE URLs are supplied, this function will batch them
      into chunks across multiple requests.

  Raises:
    PublishError if anything went wrong during publishing.
  """
  if len(urls) == 1 and not isinstance(urls[0], basestring):
    urls = list(urls[0])

  for i in xrange(0, len(urls), URL_BATCH_SIZE):
    chunk = urls[i:i+URL_BATCH_SIZE]
    data = urllib.urlencode(
        {'hub.url': chunk, 'hub.mode': 'publish'}, doseq=True)
    try:
      response = urllib2.urlopen(hub, data)
    except (IOError, urllib2.HTTPError), e:
      if hasattr(e, 'code') and e.code == 204:
        continue
      error = ''
      if hasattr(e, 'read'):
        error = e.read()
      raise PublishError('%s, Response: "%s"' % (e, error))

########NEW FILE########
__FILENAME__ = PyRSS2Gen
"""PyRSS2Gen - A Python library for generating RSS 2.0 feeds."""

__name__ = "PyRSS2Gen"
__version__ = (1, 0, 0)
__author__ = "Andrew Dalke <dalke@dalkescientific.com>"

_generator_name = __name__ + "-" + ".".join(map(str, __version__))

import datetime

# Could make this the base class; will need to add 'publish'
class WriteXmlMixin:
    def write_xml(self, outfile, encoding = "iso-8859-1"):
        from xml.sax import saxutils
        handler = saxutils.XMLGenerator(outfile, encoding)
        handler.startDocument()
        self.publish(handler)
        handler.endDocument()

    def to_xml(self, encoding = "iso-8859-1"):
        try:
            import cStringIO as StringIO
        except ImportError:
            import StringIO
        f = StringIO.StringIO()
        self.write_xml(f, encoding)
        return f.getvalue()


def _element(handler, name, obj, d = {}):
    if isinstance(obj, basestring) or obj is None:
        # special-case handling to make the API easier
        # to use for the common case.
        handler.startElement(name, d)
        if obj is not None:
            handler.characters(obj)
        handler.endElement(name)
    else:
        # It better know how to emit the correct XML.
        obj.publish(handler)

def _opt_element(handler, name, obj):
    if obj is None:
        return
    _element(handler, name, obj)


def _format_date(dt):
    """convert a datetime into an RFC 822 formatted date

    Input date must be in GMT.
    """
    # Looks like:
    #   Sat, 07 Sep 2002 00:00:01 GMT
    # Can't use strftime because that's locale dependent
    #
    # Isn't there a standard way to do this for Python?  The
    # rfc822 and email.Utils modules assume a timestamp.  The
    # following is based on the rfc822 module.
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()],
            dt.day,
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month-1],
            dt.year, dt.hour, dt.minute, dt.second)

        
##
# A couple simple wrapper objects for the fields which
# take a simple value other than a string.
class IntElement:
    """implements the 'publish' API for integers

    Takes the tag name and the integer value to publish.
    
    (Could be used for anything which uses str() to be published
    to text for XML.)
    """
    element_attrs = {}
    def __init__(self, name, val):
        self.name = name
        self.val = val
    def publish(self, handler):
        handler.startElement(self.name, self.element_attrs)
        handler.characters(str(self.val))
        handler.endElement(self.name)

class DateElement:
    """implements the 'publish' API for a datetime.datetime

    Takes the tag name and the datetime to publish.

    Converts the datetime to RFC 2822 timestamp (4-digit year).
    """
    def __init__(self, name, dt):
        self.name = name
        self.dt = dt
    def publish(self, handler):
        _element(handler, self.name, _format_date(self.dt))
####

class Category:
    """Publish a category element"""
    def __init__(self, category, domain = None):
        self.category = category
        self.domain = domain
    def publish(self, handler):
        d = {}
        if self.domain is not None:
            d["domain"] = self.domain
        _element(handler, "category", self.category, d)

class Cloud:
    """Publish a cloud"""
    def __init__(self, domain, port, path,
                 registerProcedure, protocol):
        self.domain = domain
        self.port = port
        self.path = path
        self.registerProcedure = registerProcedure
        self.protocol = protocol
    def publish(self, handler):
        _element(handler, "cloud", None, {
            "domain": self.domain,
            "port": str(self.port),
            "path": self.path,
            "registerProcedure": self.registerProcedure,
            "protocol": self.protocol})

class Image:
    """Publish a channel Image"""
    element_attrs = {}
    def __init__(self, url, title, link,
                 width = None, height = None, description = None):
        self.url = url
        self.title = title
        self.link = link
        self.width = width
        self.height = height
        self.description = description
        
    def publish(self, handler):
        handler.startElement("image", self.element_attrs)

        _element(handler, "url", self.url)
        _element(handler, "title", self.title)
        _element(handler, "link", self.link)

        width = self.width
        if isinstance(width, int):
            width = IntElement("width", width)
        _opt_element(handler, "width", width)
        
        height = self.height
        if isinstance(height, int):
            height = IntElement("height", height)
        _opt_element(handler, "height", height)

        _opt_element(handler, "description", self.description)

        handler.endElement("image")

class Guid:
    """Publish a guid

    Defaults to being a permalink, which is the assumption if it's
    omitted.  Hence strings are always permalinks.
    """
    def __init__(self, guid, isPermaLink = 1):
        self.guid = guid
        self.isPermaLink = isPermaLink
    def publish(self, handler):
        d = {}
        if self.isPermaLink:
            d["isPermaLink"] = "true"
        else:
            d["isPermaLink"] = "false"
        _element(handler, "guid", self.guid, d)

class TextInput:
    """Publish a textInput

    Apparently this is rarely used.
    """
    element_attrs = {}
    def __init__(self, title, description, name, link):
        self.title = title
        self.description = description
        self.name = name
        self.link = link

    def publish(self, handler):
        handler.startElement("textInput", self.element_attrs)
        _element(handler, "title", self.title)
        _element(handler, "description", self.description)
        _element(handler, "name", self.name)
        _element(handler, "link", self.link)
        handler.endElement("textInput")
        

class Enclosure:
    """Publish an enclosure"""
    def __init__(self, url, length, type):
        self.url = url
        self.length = length
        self.type = type
    def publish(self, handler):
        _element(handler, "enclosure", None,
                 {"url": self.url,
                  "length": str(self.length),
                  "type": self.type,
                  })

class Source:
    """Publish the item's original source, used by aggregators"""
    def __init__(self, name, url):
        self.name = name
        self.url = url
    def publish(self, handler):
        _element(handler, "source", self.name, {"url": self.url})

class SkipHours:
    """Publish the skipHours

    This takes a list of hours, as integers.
    """
    element_attrs = {}
    def __init__(self, hours):
        self.hours = hours
    def publish(self, handler):
        if self.hours:
            handler.startElement("skipHours", self.element_attrs)
            for hour in self.hours:
                _element(handler, "hour", str(hour))
            handler.endElement("skipHours")

class SkipDays:
    """Publish the skipDays

    This takes a list of days as strings.
    """
    element_attrs = {}
    def __init__(self, days):
        self.days = days
    def publish(self, handler):
        if self.days:
            handler.startElement("skipDays", self.element_attrs)
            for day in self.days:
                _element(handler, "day", day)
            handler.endElement("skipDays")

class RSS2(WriteXmlMixin):
    """The main RSS class.

    Stores the channel attributes, with the "category" elements under
    ".categories" and the RSS items under ".items".
    """
    
    rss_attrs = {"version": "2.0"}
    element_attrs = {}
    def __init__(self,
                 title,
                 link,
                 description,

                 language = None,
                 copyright = None,
                 managingEditor = None,
                 webMaster = None,
                 pubDate = None,  # a datetime, *in* *GMT*
                 lastBuildDate = None, # a datetime
                 
                 categories = None, # list of strings or Category
                 generator = _generator_name,
                 docs = "http://blogs.law.harvard.edu/tech/rss",
                 cloud = None,    # a Cloud
                 ttl = None,      # integer number of minutes

                 image = None,     # an Image
                 rating = None,    # a string; I don't know how it's used
                 textInput = None, # a TextInput
                 skipHours = None, # a SkipHours with a list of integers
                 skipDays = None,  # a SkipDays with a list of strings

                 items = None,     # list of RSSItems
                 ):
        self.title = title
        self.link = link
        self.description = description
        self.language = language
        self.copyright = copyright
        self.managingEditor = managingEditor

        self.webMaster = webMaster
        self.pubDate = pubDate
        self.lastBuildDate = lastBuildDate
        
        if categories is None:
            categories = []
        self.categories = categories
        self.generator = generator
        self.docs = docs
        self.cloud = cloud
        self.ttl = ttl
        self.image = image
        self.rating = rating
        self.textInput = textInput
        self.skipHours = skipHours
        self.skipDays = skipDays

        if items is None:
            items = []
        self.items = items

    def publish(self, handler):
        handler.startElement("rss", self.rss_attrs)
        handler.startElement("channel", self.element_attrs)
        _element(handler, "title", self.title)
        _element(handler, "link", self.link)
        _element(handler, "description", self.description)

        self.publish_extensions(handler)
        
        _opt_element(handler, "language", self.language)
        _opt_element(handler, "copyright", self.copyright)
        _opt_element(handler, "managingEditor", self.managingEditor)
        _opt_element(handler, "webMaster", self.webMaster)

        pubDate = self.pubDate
        if isinstance(pubDate, datetime.datetime):
            pubDate = DateElement("pubDate", pubDate)
        _opt_element(handler, "pubDate", pubDate)

        lastBuildDate = self.lastBuildDate
        if isinstance(lastBuildDate, datetime.datetime):
            lastBuildDate = DateElement("lastBuildDate", lastBuildDate)
        _opt_element(handler, "lastBuildDate", lastBuildDate)

        for category in self.categories:
            if isinstance(category, basestring):
                category = Category(category)
            category.publish(handler)

        _opt_element(handler, "generator", self.generator)
        _opt_element(handler, "docs", self.docs)

        if self.cloud is not None:
            self.cloud.publish(handler)

        ttl = self.ttl
        if isinstance(self.ttl, int):
            ttl = IntElement("ttl", ttl)
        _opt_element(handler, "tt", ttl)

        if self.image is not None:
            self.image.publish(handler)

        _opt_element(handler, "rating", self.rating)
        if self.textInput is not None:
            self.textInput.publish(handler)
        if self.skipHours is not None:
            self.skipHours.publish(handler)
        if self.skipDays is not None:
            self.skipDays.publish(handler)

        for item in self.items:
            item.publish(handler)

        handler.endElement("channel")
        handler.endElement("rss")

    def publish_extensions(self, handler):
        # Derived classes can hook into this to insert
        # output after the three required fields.
        pass

    
    
class RSSItem(WriteXmlMixin):
    """Publish an RSS Item"""
    element_attrs = {}
    def __init__(self,
                 title = None,  # string
                 link = None,   # url as string
                 description = None, # string
                 author = None,      # email address as string
                 categories = None,  # list of string or Category
                 comments = None,  # url as string
                 enclosure = None, # an Enclosure
                 guid = None,    # a unique string
                 pubDate = None, # a datetime
                 source = None,  # a Source
                 ):
        
        if title is None and description is None:
            raise TypeError(
                "must define at least one of 'title' or 'description'")
        self.title = title
        self.link = link
        self.description = description
        self.author = author
        if categories is None:
            categories = []
        self.categories = categories
        self.comments = comments
        self.enclosure = enclosure
        self.guid = guid
        self.pubDate = pubDate
        self.source = source
        # It sure does get tedious typing these names three times...

    def publish(self, handler):
        handler.startElement("item", self.element_attrs)
        _opt_element(handler, "title", self.title)
        _opt_element(handler, "link", self.link)
        self.publish_extensions(handler)
        _opt_element(handler, "description", self.description)
        _opt_element(handler, "author", self.author)

        for category in self.categories:
            if isinstance(category, basestring):
                category = Category(category)
            category.publish(handler)
        
        _opt_element(handler, "comments", self.comments)
        if self.enclosure is not None:
            self.enclosure.publish(handler)
        _opt_element(handler, "guid", self.guid)

        pubDate = self.pubDate
        if isinstance(pubDate, datetime.datetime):
            pubDate = DateElement("pubDate", pubDate)
        _opt_element(handler, "pubDate", pubDate)

        if self.source is not None:
            self.source.publish(handler)
        
        handler.endElement("item")

    def publish_extensions(self, handler):
        # Derived classes can hook into this to insert
        # output after the title and link elements
        pass

########NEW FILE########
__FILENAME__ = remote_api
### public XML-RPC API.

class XmlRpcFunctions(object):
    def __init__(self, coordinator, client_ip):
        self.coordinator = coordinator
        self.client_ip = client_ip

    def add_results(self, client_info, results):
        """
        Add build results to the server.

        'client_info' is a dictionary of client information; 'results' is
        a list of dictionaries, with each dict containing build/test info
        for a single step.
        """
        # assert that they have the right methods ;)
        client_info.keys()
        for d in results:
            d.keys()

        client_ip = self.client_ip
        coordinator = self.coordinator

        try:
            key = coordinator.add_results(client_ip, client_info, results)
        except:
            traceback.print_exc()
            raise

        return key

    def get_results(self, results_key):
        x = self.coordinator.db_get_result_info(results_key)
        (receipt, client_info, results) = x

        return x

    def check_should_build(self, client_info, reserve_build=True,
                           build_allowance=0):
        """
        Should a client build, according to the server?

        Returns a tuple (flag, reason).  'flag' is bool; 'reason' is a
        human-readable string.

        A 'yes' (True) could be for several reasons, including no build
        result for this tagset, a stale build result (server
        configurable), or a request to force-build.
        """
        flag, reason = self.coordinator.check_should_build(client_info)
        print (flag, reason)
        if flag:
            if reserve_build:
                print 'RESERVING BUILD'
                self.coordinator.notify_build(client_info['package'],
                                              client_info, build_allowance)
            return True, reason
        return False, reason

    def get_tagsets_for_package(self, package):
        """
        Get the list of tagsets containing build results for the given package.
        """

        # here 'tagsets' will be ImmutableSet objects
        tagsets = self.coordinator.get_tagsets_for_package(package)

        # convert them into lists, then return
        return [ list(x) for x in tagsets ]

    def get_last_result_for_tagset(self, package, tagset):
        """
        Get the most recent result for the given package/tagset combination.
        """
        return self.coordinator.get_last_result_for_tagset(package, tagset)

########NEW FILE########
__FILENAME__ = rss
"""
Functions to help generate RSS2 feeds for pony_build results.

RSS2 and pubsubhubbub (http://code.google.com/p/pubsubhubbub/) are the
core of the notification system built into pony_build; the "officially
correct" way to actively notify interested people of build results is
to publish them via RSS2, push them to a pubsubhubbub server, and let
someone else deal with translating those into e-mail alerts, etc.

This module contains infrastructure for creating and publishing RSS
feeds using Andrew Dalke's PyRSS2Gen, and pushing change notifications
to pubsubhubbub servers via Brett Slatkin's Python module.

The main class to pay attention to is BuildSnooper, ... @CTB ...

Apart from standard UI stuff (creating and managing) RSS feeds, the
remaining bit of trickiness is that any RSS feeds must be served via a
URL and also contain ref URLs, which is the responsibility of the Web
interface.  So the 'generate_rss' function on each BuildSnooper object
must be called from the Web app and requires some input in the form of
canonical URLs

"""

MAX=50

from datetime import datetime, timedelta
import traceback
from cStringIO import StringIO
from .PyRSS2Gen import RSS2, RSSItem, _element, Guid, Source
from .pubsubhubbub_publish import publish as push_publish, PublishError

build_snoopers = {}
build_snoopers_rev = {}

wildcard_snoopers = []
snoopers_per_package = {}

def add_snooper(snooper, key):
    """
    Add a snooper into the forward and reverse key mapping dictionaries.
    
    """
    assert key not in build_snoopers
    build_snoopers[key] = snooper
    build_snoopers_rev[snooper] = key

def register_wildcard_snooper(snooper):
    wildcard_snoopers.append(snooper)

def register_snooper_for_package(package, snooper):
    """
    Register a snooper to care about a particular package.
    
    """
    x = snoopers_per_package.get(package, [])
    x.append(snooper)
    snoopers_per_package[package] = x

def check_new_builds(coord, *build_keylist):
    """
    Return the list of snooper keys that care about new builds.

    Briefly, for each build in build_keylist, retrieve the package info and
    see if there are any snoopers interested in that package.  If there are,
    use 'snooper.is_match' to see if any of them care about this particular
    build result.
    
    """
    s = set()
    for result_key in build_keylist:
       receipt, client_info, results =  coord.db_get_result_info(result_key)

       # are there any snoopers interested in this package?
       package = client_info['package']
       x = snoopers_per_package.get(package, [])
       for snooper in x:
           # if is_match returns true, then yes: store key for later return.
           if snooper.is_match(receipt, client_info, results):
               snooper_key = build_snoopers_rev[snooper]
               s.add(snooper_key)

    return list(s)

def notify_pubsubhubbub_server(server, *rss_urls):
    """
    Notify the given pubsubhubbub server that the given RSS URLs have changed.

    Basically the same as pubsubhubbub_publish.publish, but ignore errors.
    
    """
    try:
        push_publish(server, *rss_urls)
        print '*** notifying PuSH server: %s' % server, rss_urls
        return True
    except PublishError, e:
        print 'error notifying PuSH server %s' % (server,)
        traceback.print_exc()
        
    return False

class BuildSnooper(object):
    def generate_rss(self, pb_coord, base_url):
        pass
    
    def is_match(self, receipt, client_info, results):
        pass

class BuildSnooper_All(object):
    def __init__(self, only_failures=False):
        self.report_successes = not only_failures

    def __str__(self):
        modifier = 'failed'
        if self.report_successes:
            modifier = 'all'
        return 'Report on %s builds' % modifier

    def is_match(self, *args):
        (receipt, client_info, results) = args
        success = client_info['success']
        
        if not self.report_successes and success:
            return False
            
        return True

    def generate_rss(self, pb_coord, package_url, per_result_url,
                     source_url=''):

        it = []
        keys = list(reversed(sorted(pb_coord.db.keys())))
        now = datetime.now()
        a_week = timedelta(days=1)
        
        for n, k in enumerate(keys):
            (receipt, client_info, results_list) = pb_coord.db[k]
            tagset = client_info['tags']

            t = receipt['time']
            t = datetime.fromtimestamp(t)

            if now - t > a_week:
                break
            
            it.append((t, (tagset, receipt, client_info, results_list)))

        if not self.report_successes:
            it = [ (t, v) for (t, v) in it if not v[2]['success'] ]
        
        rss_items = []
        for n, (_, v) in enumerate(it):
            if n > MAX:
                break
            
            tagset = sorted([ x for x in list(v[0]) if not x.startswith('__')])
            tagset = ", ".join(tagset)

            _, receipt, client_info, _ = v
            result_key = receipt['result_key']
            status = client_info['success']

            x = []
            if status:
                title = 'Package %s build succeeded (tags %s)' % \
                        (client_info['package'], tagset)
                x.append("status: success")
            else:
                title = 'Package %s build FAILED (tags %s)' % \
                        (client_info['package'], tagset)
                x.append("status: failure")

            x.append("result_key: %s" % (receipt['result_key'],))
            x.append("package: %s" % (client_info['package'],))
            x.append("build host: %s" % (client_info['host'],)) # @CTB XSS
            x.append("build arch: %s" % (client_info['arch'],))

            tags = list(client_info['tags'])
            x.append("tags: %s" % (", ".join(tags)))
            description = "<br>".join(x)

            pubDate = datetime.fromtimestamp(v[1]['time'])

            link = per_result_url % dict(result_key=result_key,
                                         package=client_info['package'])

            source_obj = Source('package build & test information for "%s"' % client_info['package'], source_url)
            
            item = RSSItem(title=title,
                           link=link,
                           description=description,
                           guid=Guid(link),
                           pubDate=pubDate,
                           source=source_obj)

            rss_items.append(item)

        rss = PuSH_RSS2(
            title = "pony-build feed",
            link = 'XXX',
            description = 'all package build & test information',

            lastBuildDate = datetime.now(),
            items=rss_items
          )

        fp = StringIO()
        rss.write_xml(fp)
        return fp.getvalue()
        
class PackageSnooper(BuildSnooper):
    def __init__(self, package_name, only_failures=False, register=True):
        self.package_name = package_name
        self.report_successes = not only_failures
        if register:
            register_snooper_for_package(package_name, self)

    def __str__(self):
        modifier = 'failed'
        if self.report_successes:
            modifier = 'all'
        return "Report on %s builds for package '%s'" % (modifier,
                                                         self.package_name,)

    def generate_rss(self, pb_coord, package_url, per_result_url,
                     source_url=''):
        packages = pb_coord.get_unique_tagsets_for_package(self.package_name)

        def sort_by_timestamp(a, b):
            ta = a[1][0]['time']
            tb = b[1][0]['time']
            return -cmp(ta, tb)

        it = packages.items()

        if not self.report_successes:
            it = [ (k, v) for (k, v) in it if not v[1]['success'] ]
        
        it.sort(sort_by_timestamp)

        rss_items = []
        for k, v in it:
            tagset = sorted([ x for x in list(k) if not x.startswith('__')])
            tagset = ", ".join(tagset)

            receipt, client_info, _ = v
            result_key = receipt['result_key']
            status = client_info['success']

            x = []
            if status:
                title = 'Package %s build succeeded (tags %s)' % \
                        (self.package_name, tagset)
                x.append("status: success")
            else:
                title = 'Package %s build FAILED (tags %s)' % \
                        (self.package_name, tagset)
                x.append("status: failure")

            x.append("result_key: %s" % (receipt['result_key'],))
            x.append("package: %s" % (self.package_name,))
            x.append("build host: %s" % (client_info['host'],)) # @CTB XSS
            x.append("build arch: %s" % (client_info['arch'],))

            tags = list(client_info['tags'])
            x.append("tags: %s" % (", ".join(tags)))
            description = "<br>".join(x)

            pubDate = datetime.fromtimestamp(v[0]['time'])

            link = per_result_url % dict(result_key=result_key,
                                         package=self.package_name)

            source_obj = Source('package build & test information for "%s"' % self.package_name, source_url)
            
            item = RSSItem(title=title,
                           link=link,
                           description=description,
                           guid=Guid(link),
                           pubDate=pubDate,
                           source=source_obj)

            rss_items.append(item)

        rss = PuSH_RSS2(
            title = "pony-build feed for %s" % (self.package_name,),
            link = package_url % dict(package=self.package_name),
            description = 'package build & test information for "%s"' \
                % self.package_name,

            lastBuildDate = datetime.now(),
            items=rss_items
          )

        fp = StringIO()
        rss.write_xml(fp)
        return fp.getvalue()
        
    def is_match(self, *args):
        (receipt, client_info, results) = args
        assert self.package_name == client_info['package']
        success = client_info['success']
        
        if not self.report_successes and success:
            return False
            
        return True

###

class PuSH_RSS2(RSS2):
    def publish_extensions(self, handler):
        pass
        # is this necessary? it breaks Firefoxes RSS reader...
        #_element(handler, "atom:link", "", dict(rel='hub', href='http://pubsubhubbub.appspot.com'))

########NEW FILE########
__FILENAME__ = server
"""
A combined XML-RPC + WSGI server for pony-build, based on wsgiref.

This is a hacked implementation that combines SimpleXMLRPCServer with
a wsgiref WSGIServer, redirecting all requests to '/xmlrpc' into
SimpleXMLRPCServer, handling uploads of raw files into '/upload', and
letting wsgiref pass the rest on to a WSGI application.

One nice feature of this is that you can swap out the Web UI
completely without affecting the RPC functionality; and, since all of
the RPC functionality and data handling is in the PonyBuildCoordinator
class (see 'coordinator.py') you can just write a new Web UI around
that internal interface.
"""
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler, \
     SimpleXMLRPCDispatcher
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, \
     ServerHandler
import json                             # requires python2.6

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

##

from .remote_api import XmlRpcFunctions

###

# various error message:

too_big_message = "403 FORBIDDEN: You're trying to upload %d bytes; we only allow %d per request."
missing_package = "missing 'package' parameter on notification"
no_auth_upload = "you are not authorized to upload files!"
missing_upload_data = 'upload attempt, but missing filename, description, or auth_key!?'

#
# The PonyBuildServer class just pulls together the WSGIServer and the
# SimpleXMLRPCDispatcher so that a single Web server can handle both
# XML-RPC and WSGI duties.
#

class PonyBuildServer(WSGIServer, SimpleXMLRPCDispatcher):
    def __init__(self, *args, **kwargs):
        WSGIServer.__init__(self, *args, **kwargs)
        SimpleXMLRPCDispatcher.__init__(self, False, None)

#
# The RequestHandler class handles all of the file upload, UI and
# XML-RPC Web calls.  It does so by first checking to see if a Web
# call is to the XML-RPC URL, file upload fn, or notify, and, if not,
# then passes it on to the WSGI handler.
#
# The object is to make it really easy to write a new UI without messing
# with the basic server functionality, which includes things like security
# measures to block DoS by uploading large files.
#
# See the handle function for more information.
#

class RequestHandler(WSGIRequestHandler, SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc',)
    
    MAX_CONTENT_LENGTH = 5*1000*1000    # allow only 5 mb at a time.

    def _send_html_response(self, code, message):
        """Send an HTTP response."""
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', str(len(message)))
        self.end_headers()

        self.wfile.write(message)
        self.wfile.close()

    def _handle_upload(self):
        """Handle file upload via POST."""
        
        qs = {}
        if '?' in self.path:
            url, qs = self.path.split('?', 1)
            qs = parse_qs(qs)

        try:
            description = qs.get('description')[0]
            filename = qs.get('filename')[0]
            auth_key = qs.get('auth_key')[0]
            visible = qs.get('visible', ['no'])[0] == 'yes'
        except (TypeError, ValueError, KeyError):
            self._send_http_response(400, missing_upload_data)
            return

        content_length = self.headers.getheader('content-length')
        if content_length:
            content_length = int(content_length)
            data = self.rfile.read(content_length)
            
            code = 401
            message = no_auth_upload

            if _coordinator.db_add_uploaded_file(auth_key,
                                                 filename,
                                                 data,
                                                 description,
                                                 visible):
                code = 200
                message = ''
        else:
            code = 400
            message = 'upload attempt, but no upload content?!'

        self._send_html_response(code, message)
    def handle(self):
        """
        Handle:
          /xmlrpc => SimpleXMLRPCServer
          /upload => self._handle_upload
          all else => WSGI app for Web UI
        """
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return

        content_length = self.headers.getheader('content-length')
        if not content_length:
            content_length = 0
        content_length = int(content_length)

        print 'content length is:', content_length

        if content_length > self.MAX_CONTENT_LENGTH:
            message = too_big_message % (content_length,
                                         self.MAX_CONTENT_LENGTH)
            self._send_html_response(403, message)
            return

        if SimpleXMLRPCRequestHandler.is_rpc_path_valid(self):
            return SimpleXMLRPCRequestHandler.do_POST(self)
        
        elif self.path.startswith('/upload?'):
            return self._handle_upload()

        ## else:

        handler = ServerHandler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ(),
            multithread=False, multiprocess=False
        )
        handler.request_handler = self      # backpointer for logging
        handler.run(self.server.get_app())

    def _dispatch(self, method, params):
        """
        Handle all XML-RPC dispatch (see do_POST call, above).
        """
        client_ip = self.client_address[0]
        
        fn_obj = XmlRpcFunctions(_coordinator, client_ip)
        fn = getattr(fn_obj, method)
        return fn(*params)

###

_coordinator = None

def get_coordinator():
    global _coordinator
    return _coordinator

def create(interface, port, pbs_coordinator, wsgi_app):
    global _coordinator
    
    # Create server
    server = PonyBuildServer((interface, port), RequestHandler)
    
    server.set_app(wsgi_app)
    _coordinator = pbs_coordinator
    
    return server

########NEW FILE########
__FILENAME__ = run
if __name__ == '__main__':
    import nose
    nose.main()

########NEW FILE########
__FILENAME__ = testutil
import os
import sys
import subprocess
import urllib
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import twill
    import quixote

_server_url = None
_server_host = None
_server_port = None

DEFAULT_PORT=8912

def run_server_wsgi_intercept(dbfilename):
    host = 'localhost'
    port = 80
    
    from pony_build import server, coordinator, dbsqlite
    from pony_build.web import create_publisher, urls
    
    dbfile = dbsqlite.open_shelf(dbfilename)
    dbfile = coordinator.IntDictWrapper(dbfile)

    ###

    pbs_app = coordinator.PonyBuildCoordinator(db=dbfile)
    wsgi_app = create_publisher(pbs_app)

    #the_server = server.create(host, port, pbs_app, wsgi_app)
    url = urls.calculate_base_url(host, port)
    urls.set_base_url(url)

    twill.add_wsgi_intercept('localhost', port, lambda: wsgi_app)

    global _server_url, _server_host, _server_port
    _server_host = host
    _server_port = port
    _server_url = 'http://%s:%d/' % (host, port)

def kill_server_wsgi_intercept():
    quixote.publish._publisher = None
    twill.remove_wsgi_intercept(_server_host, _server_port)

def run_server(DB_FILE, PORT=None):
    """
    Run a Quixote simple_server on localhost:PORT with subprocess.
    All output is captured & thrown away.
    """
    global process
    
    import time, tempfile
    global _server_url

    if PORT is None:
        PORT = int(os.environ.get('PB_TEST_PORT', DEFAULT_PORT))

    print 'STARTING:', sys.executable, 'pony_build.web.run', os.getcwd()
    cmdlist = [sys.executable, '-u',
               '-m', 'pony_build.web.run', '-f', DB_FILE,
               '-p', str(PORT)]
    process = subprocess.Popen(cmdlist,
                               stderr=subprocess.STDOUT,
                               stdout=subprocess.PIPE)

    time.sleep(0.5)

    if process.poll() is not None:
        print 'process exited unexpectedly! status:', process.returncode
        x = process.stdout.read()
        print 'stdout/stderr is:', x

    _server_url = 'http://localhost:%d/' % (PORT,)
	
def kill_server():
    """
    Kill the previously started Quixote server.
    """
    global _server_url
    if _server_url != None:
       try:
          fp = urllib.urlopen('%sexit' % (_server_url,))
       except:
          pass

    _server_url = None

########NEW FILE########
__FILENAME__ = test_coordinator
import os
from pony_build import coordinator, dbsqlite
import time

class Test_Coordinator_API(object):
    def setup(self):
        _db = dbsqlite.open_shelf()
        db = coordinator.IntDictWrapper(_db)
        self.coord = coordinator.PonyBuildCoordinator(db)
        
        self.some_client_info = dict(success=True,
                                     tags=['tag1'],
                                     package='package1',
                                     duration=0.1,
                                     host='test-machine',
                                     arch='foo')
        self.tagset = coordinator.build_tagset(self.some_client_info)

    def load_results(self):
        (results_key, auth_key) = self.coord.add_results('127.0.0.1',
                                                         self.some_client_info,
                                                         [])
        return results_key

    def test_get_no_arch(self):
        keys = self.coord.get_all_archs()
        assert len(keys) == 0

    def test_get_arch(self):
        self.load_results()
        keys = self.coord.get_all_archs()
        assert len(keys) == 1
        assert keys[0] == 'foo'

    def test_get_no_packages(self):
        keys = self.coord.get_all_packages()
        assert len(keys) == 0

    def test_get_all_packages(self):
        self.load_results()
        keys = self.coord.get_all_packages()
        assert len(keys) == 1
        assert keys[0] == 'package1'

    def test_get_no_host(self):
        keys = self.coord.get_all_hosts()
        assert len(keys) == 0

    def test_get_host(self):
        self.load_results()
        keys = self.coord.get_all_hosts()
        assert len(keys) == 1
        assert keys[0] == 'test-machine'

    def test_get_unique_tagsets(self):
        """
        We should only have a single tagset for our results.
        """
        
        self.load_results()

        x = self.coord.get_unique_tagsets_for_package('package1')
        x = x.keys()
        
        assert [ self.tagset ] == x

    def test_get_unique_tagsets_is_single(self):
        """
        We should only have a single tagset for our results, even if we
        load twice.
        """
        
        self.load_results()
        self.load_results()

        x = self.coord.get_unique_tagsets_for_package('package1')
        x = x.keys()
        
        assert [ self.tagset ] == x

    def test_check_should_build_no_results(self):
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_too_recent(self):
        self.load_results()
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_too_old(self):
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0             # force "old" result
        self.coord.db[k] = receipt, client_info, results

        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]
        
    def test_check_should_build_unsuccessful(self):
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        client_info['success'] = False             # force fail
        self.coord.db[k] = receipt, client_info, results

        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_force_do_build(self):
        self.load_results()
        self.coord.set_request_build(self.some_client_info, True)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_force_dont_build(self):
        self.load_results()
        self.coord.set_request_build(self.some_client_info, False)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building(self):
        self.coord.notify_build('package1', self.some_client_info)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building_2(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building...
        self.coord.notify_build('package1', self.some_client_info)

        # ...and check immediately.
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building_but_is_slow(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building...
        self.coord.notify_build('package1', self.some_client_info)

        # ...but wait for longer than it took to build the last time.
        time.sleep(0.2)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_is_building_but_requested(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building, and request 0.5 seconds...
        self.coord.notify_build('package1', self.some_client_info, 0.5)

        # ...and wait for longer than it took to build the last time,
        # but less than requested.
        time.sleep(0.2)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building_but_longer_than_requested(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building, and request 0.1 seconds...
        self.coord.notify_build('package1', self.some_client_info, 0.1)

        # ...but wait for longer than requested.
        time.sleep(0.2)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

########NEW FILE########
__FILENAME__ = test_qx_web
import os
import time
import warnings

import testutil
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from twill.commands import *

from pony_build import coordinator, dbsqlite

DB_TEST_FILE=os.path.join(os.path.dirname(__file__), 'tests.db')

def make_db(filename=DB_TEST_FILE):
    try:
        os.unlink(filename)
    except OSError:
        pass

    db = dbsqlite.open_shelf(filename, 'c')
    db = coordinator.IntDictWrapper(db)
    coord = coordinator.PonyBuildCoordinator(db)

    ## CTB: note, make sure to add items to the database in the correct
    ## order: most recently received ==> last.

    # mangle the receipt time in the database, in order to test expiration
    client_info = dict(success=True,
                       tags=['a_tag'],
                       package='test-expire',
                       duration=0.1,
                       host='testhost',
                       arch='fooarch')
    results = [ dict(status=0, name='abc', errout='', output='',
                    command=['foo', 'bar'],
                    type='test_the_test') ]
    (k, _) = coord.add_results('127.0.0.1', client_info, results)
    receipt, client_info, results_list = db[k]
    receipt['time'] = time.time() - 60*60*24 * 10     # -- 10 days ago
    db[k] = receipt, client_info, results_list

    # mangle the receipt time in the database, in order to test stale flag.
    client_info = dict(success=True,
                       tags=['a_tag'],
                       package='test-stale',
                       duration=0.1,
                       host='testhost',
                       arch='fooarch')
    results = [ dict(status=0, name='abc', errout='', output='',
                    command=['foo', 'bar'],
                    type='test_the_test') ]
    (k, _) = coord.add_results('127.0.0.1', client_info, results)
    receipt, client_info, results_list = db[k]
    receipt['time'] = time.time() - 60*60*24 * 2      # -- 2 days ago
    db[k] = receipt, client_info, results_list

    # also add a fresh result
    client_info = dict(success=True,
                       tags=['a_tag'],
                       package='test-underway',
                       duration=0.1,
                       host='testhost',
                       arch='fooarch')
    results = [ dict(status=0, name='abc', errout='', output='',
                    command=['foo', 'bar'],
                    type='test_the_test') ]
    (k, _) = coord.add_results('127.0.0.1', client_info, results)

    del coord
    db.close()

def setup():
    make_db()
    testutil.run_server(DB_TEST_FILE)

def teardown():
    testutil.kill_server()

def test_index():
    go(testutil._server_url)

    title('pony-build main')
    code(200)

def test_package_index():
    go(testutil._server_url)
    code(200)
    
    go('/p/test-underway/')
    title('Build summary for')
    code(200)
    show()
    notfind("Stale build")
    
    follow('view details')
    code(200)
    show()


def test_package_stale():
    go(testutil._server_url)
    code(200)
    
    go('/p/test-stale/')
    title('Build summary for')
    code(200)
    show()

    find("Stale build")

def test_package_expired():
    go(testutil._server_url)
    code(200)
    
    go('/p/test-expire/')
    title('Build summary for')
    code(200)
    show()

    notfind('view details')

########NEW FILE########
__FILENAME__ = test_xmlrpc_api
import os
import shelve
import time

import testutil
from twill.commands import *

from pony_build import coordinator, dbsqlite

###
import sys
clientlib = os.path.join(os.path.dirname(__file__), '..', '..', 'client')
clientlib = os.path.abspath(clientlib)
sys.path.insert(0, clientlib)

import pony_client as pbc
###

rpc_url = None
DB_TEST_FILE=os.path.join(os.path.dirname(__file__), 'tests.db')

###

def make_db(filename=DB_TEST_FILE):
    print 'FILENAME', filename
    try:
        os.unlink(filename)
    except OSError:
        pass

    db = dbsqlite.open_shelf(filename, 'c')
    db = coordinator.IntDictWrapper(db)
    coord = coordinator.PonyBuildCoordinator(db)

    client_info = dict(success=True,
                       tags=['a_tag'],
                       package='test-underway',
                       duration=0.1,
                       host='testhost',
                       arch='fooarch')
    results = [ dict(status=0, name='abc', errout='', output='',
                    command=['foo', 'bar'],
                    type='test_the_test') ]
    coord.add_results('120.0.0.127', client_info, results)
    del coord
    db.close()

def setup():
    make_db()
    testutil.run_server(DB_TEST_FILE)
    assert testutil._server_url
    
    global rpc_url
    rpc_url = testutil._server_url + 'xmlrpc'
    print 'RPC URL:', rpc_url

def teardown():
    testutil.kill_server()

def test_check_fn():
    tags = ['a_tag']
    package = 'test-underway'
    hostname = 'testhost'
    arch = 'fooarch'

    x = pbc.check(package, rpc_url, tags=tags, hostname=hostname, arch=arch)
    assert not x, x

def test_send_fn():
    client_info = dict(package='test-underway2', arch='fooarch2',
                       success=True)
    results = (client_info, [], None)

    x = pbc.get_tagsets_for_package(rpc_url, 'test-underway2')
    assert len(x) == 0
    
    pbc.send(rpc_url, results, hostname='testhost2', tags=('b_tag',))

    x = pbc.get_tagsets_for_package(rpc_url, 'test-underway2')
    assert len(x) == 1

########NEW FILE########
__FILENAME__ = run
from optparse import OptionParser
from .. import web as qx_web

if __name__ == '__main__':
#    import figleaf
#    figleaf.start()
    import sys
    parser = OptionParser()

    parser.add_option('-i', '--interface', dest='interface',
                      help='interface to bind', default='localhost')
    parser.add_option('-p', '--port', dest='port', help='port to bind',
                      type='int', default='8000')
    parser.add_option('-f', '--dbfile', dest='dbfile',
                     help='database filename', type='string',
                      default=':memory:')
    parser.add_option('-u', '--url', dest='url', help='public URL',
                      default=None)
    parser.add_option('-P', '--use-pubsubhubbub', dest='use_pubsubhubbub',
                      help='notify a pubsubhubbub server of changed RSS feeds',
                      action='store_true', default=False)
    parser.add_option('-S', '--set-pubsubhubbub-server', dest='push_server',
                      help='set the pubsubhubbub server to use',
                      type='str', default='http://pubsubhubbub.appspot.com/')
    

    (options, args) = parser.parse_args()

    if args:
        print "pony-build Web server doesn't take any arguments??  Maybe you meant to use '-f'"
        sys.exit(-1)

    push_server = None
    if options.use_pubsubhubbub:
        push_server = options.push_server

    qx_web.run(options.interface, options.port, options.dbfile, public_url=options.url,
               pubsubhubbub_server=push_server)

########NEW FILE########
__FILENAME__ = urls
base_url = None

named_rss_feed_url = '/rss2/%(feedname)s'
generic_rss_feed_root = '/rss2/_generic/%(package)s/'
package_url_template = 'p/%(package)s/'
per_result_url_template = 'p/%(package)s/%(result_key)s/'

def calculate_base_url(host, port, script_name=''):
    if not host.strip():
        host = 'localhost'
    url = 'http://%s:%s' % (host, port)
    if script_name:
        url += '/' + script_name.strip('/')

    return url

def set_base_url(url):
    global base_url
    base_url = url

########NEW FILE########
__FILENAME__ = util
import os.path
import jinja2
import datetime
import math

###

# jinja2 prep

thisdir = os.path.dirname(__file__)
templatesdir = os.path.join(thisdir, 'templates')
templatesdir = os.path.abspath(templatesdir)

loader = jinja2.FileSystemLoader(templatesdir)
env = jinja2.Environment(loader=loader)

###

day_diff = datetime.timedelta(1)
hour_diff = datetime.timedelta(0, 3600)
elevenmin_diff = datetime.timedelta(0, 660)
min_diff = datetime.timedelta(0, 60)

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    now = datetime.datetime.now()
    
    diff = now - dt
    minutesSince = int(math.floor(diff.seconds / 60))

    if diff > day_diff:
        return dt.strftime("%A, %d %B %Y, %I:%M %p")
    elif diff > hour_diff:
        timeSince = (minutesSince / 60) + 1
        if timeSince == 24:
            timeSince = "a day"
        else:
            timeSince = str(timeSince) + " hours"
        return "less than " + timeSince + " ago " + dt.strftime("(%I:%M %p)")
    elif diff > elevenmin_diff:
        timeSince = ((minutesSince / 10) + 1 ) * 10
        if timeSince == 60:
            timeSince = "an hour"
        else:
            timeSince = str(timeSince) + " minutes"
        return "less than " + timeSince + " ago " + dt.strftime("(%I:%M %p)")

    return str(minutesSince) + " minutes ago " + dt.strftime("(%I:%M %p)")
########NEW FILE########
