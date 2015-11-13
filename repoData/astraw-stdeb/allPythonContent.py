__FILENAME__ = cli_runner
import sys, os, shutil, subprocess
from ConfigParser import SafeConfigParser
from distutils.util import strtobool
from distutils.fancy_getopt import FancyGetopt, translate_longopt
from stdeb.util import stdeb_cmdline_opts, stdeb_cmd_bool_opts
from stdeb.util import expand_sdist_file, apply_patch
from stdeb import log

from pkg_resources import Requirement, Distribution

class OptObj: pass

def runit(cmd,usage):
    if cmd not in ['sdist_dsc','bdist_deb']:
        raise ValueError('unknown command %r'%cmd)
    # process command-line options
    bool_opts = map(translate_longopt, stdeb_cmd_bool_opts)
    parser = FancyGetopt(stdeb_cmdline_opts+[
        ('help', 'h', "show detailed help message"),
        ])
    optobj = OptObj()
    args = parser.getopt(object=optobj)
    for option in optobj.__dict__:
        value = getattr(optobj,option)
        is_string = type(value) == str
        if option in bool_opts and is_string:
            setattr(optobj, option, strtobool(value))

    if hasattr(optobj,'help'):
        print usage
        parser.set_option_table(stdeb_cmdline_opts)
        parser.print_help("Options:")
        return 0

    if len(args)!=1:
        log.error('not given single argument (distfile), args=%r', args)
        print usage
        return 1

    sdist_file = args[0]

    final_dist_dir = optobj.__dict__.get('dist_dir','deb_dist')
    tmp_dist_dir = os.path.join(final_dist_dir,'tmp_py2dsc')
    if os.path.exists(tmp_dist_dir):
        shutil.rmtree(tmp_dist_dir)
    os.makedirs(tmp_dist_dir)

    if not os.path.isfile(sdist_file):
        log.error("Package %s not found."%sdist_file)
        sys.exit(1)

    patch_file = optobj.__dict__.get('patch_file',None)
    patch_level = int(optobj.__dict__.get('patch_level',0))
    patch_posix = int(optobj.__dict__.get('patch_posix',0))

    expand_dir = os.path.join(tmp_dist_dir,'stdeb_tmp')
    if os.path.exists(expand_dir):
        shutil.rmtree(expand_dir)
    if not os.path.exists(tmp_dist_dir):
        os.mkdir(tmp_dist_dir)
    os.mkdir(expand_dir)

    expand_sdist_file(os.path.abspath(sdist_file),cwd=expand_dir)



    # now the sdist package is expanded in expand_dir
    expanded_root_files = os.listdir(expand_dir)
    assert len(expanded_root_files)==1
    repackaged_dirname = expanded_root_files[0]
    fullpath_repackaged_dirname = os.path.join(tmp_dist_dir,repackaged_dirname)
    base_dir = os.path.join(expand_dir,expanded_root_files[0])
    if os.path.exists(fullpath_repackaged_dirname):
        # prevent weird build errors if this dir exists
        shutil.rmtree(fullpath_repackaged_dirname)
    os.renames(base_dir, fullpath_repackaged_dirname)
    del base_dir # no longer useful

    ##############################################
    if patch_file is not None:
        log.info('py2dsc applying patch %s', patch_file)
        apply_patch(patch_file,
                    posix=patch_posix,
                    level=patch_level,
                    cwd=fullpath_repackaged_dirname)
        patch_already_applied = 1
    else:
        patch_already_applied = 0
    ##############################################


    abs_dist_dir = os.path.abspath(final_dist_dir)

    extra_args = []
    for long in parser.long_opts:
        if long in ['dist-dir=','patch-file=']:
            continue # dealt with by this invocation
        attr = parser.get_attr_name(long).rstrip('=')
        if hasattr(optobj,attr):
            val = getattr(optobj,attr)
            if attr=='extra_cfg_file':
                val = os.path.abspath(val)
            if long in bool_opts or long.replace('-', '_') in bool_opts:
                extra_args.append('--%s' % long)
            else:
                extra_args.append('--'+long+str(val))

    if patch_already_applied == 1:
        extra_args.append('--patch-already-applied')

    if cmd=='bdist_deb':
        extra_args.append('bdist_deb')

    args = [sys.executable,'setup.py','--command-packages','stdeb.command',
            'sdist_dsc','--dist-dir=%s'%abs_dist_dir,
            '--use-premade-distfile=%s'%os.path.abspath(sdist_file)]+extra_args

    log.info('-='*35 + '-')
#    print >> sys.stderr, '-='*20
#    print >> sys.stderr, "Note that the .cfg file(s), if present, have not "\
#          "been read at this stage. If options are necessary, pass them from "\
#          "the command line"
    log.info("running the following command in directory: %s\n%s",
             fullpath_repackaged_dirname, ' '.join(args))
    log.info('-='*35 + '-')

    try:
        returncode = subprocess.call(
            args,cwd=fullpath_repackaged_dirname,
            )
    except:
        log.error('ERROR running: %s', ' '.join(args))
        log.error('ERROR in %s', fullpath_repackaged_dirname)
        raise

    if returncode:
        log.error('ERROR running: %s', ' '.join(args))
        log.error('ERROR in %s', fullpath_repackaged_dirname)
        #log.error('   stderr: %s'res.stderr.read())
        #print >> sys.stderr, 'ERROR running: %s'%(' '.join(args),)
        #print >> sys.stderr, res.stderr.read()
        return returncode
        #raise RuntimeError('returncode %d'%returncode)
    #result = res.stdout.read().strip()

    shutil.rmtree(tmp_dist_dir)
    return returncode

########NEW FILE########
__FILENAME__ = bdist_deb
import os
import stdeb.util as util

from distutils.core import Command

__all__ = ['bdist_deb']

class bdist_deb(Command):
    description = 'distutils command to create debian binary package'

    user_options = []
    boolean_options = []

    def initialize_options (self):
        pass

    def finalize_options (self):
        pass

    def run(self):
        # generate .dsc source pkg
        self.run_command('sdist_dsc')

        # get relevant options passed to sdist_dsc
        sdist_dsc = self.get_finalized_command('sdist_dsc')
        dsc_tree = sdist_dsc.dist_dir

        # execute system command and read output (execute and read output of find cmd)
        target_dirs = []
        for entry in os.listdir(dsc_tree):
            fulldir = os.path.join(dsc_tree,entry)
            if os.path.isdir(fulldir):
                if entry == 'tmp_py2dsc':
                    continue
                target_dirs.append( fulldir )

        if len(target_dirs)>1:
            raise ValueError('More than one directory in deb_dist. '
                             'Unsure which is source directory. All: %r'%(
                target_dirs,))

        if len(target_dirs)==0:
            raise ValueError('could not find debian source directory')

        # define system command to execute (gen .deb binary pkg)
        syscmd = ['dpkg-buildpackage','-rfakeroot','-uc','-b']

        util.process_command(syscmd,cwd=target_dirs[0])


########NEW FILE########
__FILENAME__ = common
import sys, os, shutil

from stdeb import log
from distutils.core import Command
from distutils.errors import DistutilsModuleError

from stdeb.util import DebianInfo, build_dsc, stdeb_cmdline_opts, \
     stdeb_cmd_bool_opts, stdeb_cfg_options

class common_debian_package_command(Command):
    def initialize_options (self):
        self.patch_already_applied = 0
        self.remove_expanded_source_dir = 0
        self.patch_posix = 0
        self.dist_dir = None
        self.extra_cfg_file = None
        self.patch_file = None
        self.patch_level = None
        self.ignore_install_requires = None
        self.debian_version = None
        self.force_buildsystem = None
        self.no_backwards_compatibility = None
        self.guess_conflicts_provides_replaces = None

        # deprecated options
        self.default_distribution = None
        self.default_maintainer = None

        # make distutils happy by filling in default values
        for longopt, shortopt, description in stdeb_cfg_options:
            assert longopt.endswith('=')
            name = longopt[:-1]
            name = name.replace('-','_')
            setattr( self, name, None )

    def finalize_options(self):
        def str_to_bool(mystr):
            if mystr.lower() == 'false':
                return False
            elif mystr.lower() == 'true':
                return True
            else:
                raise ValueError('bool string "%s" is not "true" or "false"'%mystr)
        if self.dist_dir is None:
            self.dist_dir = 'deb_dist'
        if self.patch_level is not None:
            self.patch_level = int(self.patch_level)

        if self.force_buildsystem is not None:
            self.force_buildsystem = str_to_bool(self.force_buildsystem)

        if self.force_buildsystem is None:
            self.force_buildsystem = True

        if self.guess_conflicts_provides_replaces is None:
            # the default
            self.guess_conflicts_provides_replaces = False
        else:
            self.guess_conflicts_provides_replaces = str_to_bool(
                self.guess_conflicts_provides_replaces)

    def get_debinfo(self):
        ###############################################
        # 1. setup initial variables
        #    A. create config defaults
        module_name = self.distribution.get_name()

        if 1:
            # set default maintainer
            if (self.distribution.get_maintainer() != 'UNKNOWN' and
                self.distribution.get_maintainer_email() != 'UNKNOWN'):
                guess_maintainer = "%s <%s>"%(
                    self.distribution.get_maintainer(),
                    self.distribution.get_maintainer_email())
            elif (self.distribution.get_author() != 'UNKNOWN' and
                  self.distribution.get_author_email() != 'UNKNOWN'):
                guess_maintainer = "%s <%s>"%(
                    self.distribution.get_author(),
                    self.distribution.get_author_email())
            else:
                guess_maintainer = "unknown <unknown@unknown>"
        if self.default_maintainer is not None:
            log.warn('Deprecation warning: you are using the '
                     '--default-maintainer option. '
                     'Switch to the --maintainer option.')
            guess_maintainer = self.default_maintainer

        #    B. find config files (if any)
        cfg_files = []
        if self.extra_cfg_file is not None:
            cfg_files.append(self.extra_cfg_file)

        use_setuptools = True
        try:
            ei_cmd = self.distribution.get_command_obj('egg_info')
        except DistutilsModuleError, err:
            use_setuptools = False

        have_script_entry_points = None

        config_fname = 'stdeb.cfg'
        # Distutils fails if not run from setup.py dir, so this is OK.
        if os.path.exists(config_fname):
            cfg_files.append(config_fname)

        if use_setuptools:
            self.run_command('egg_info')
            egg_info_dirname = ei_cmd.egg_info

            # Pickup old location of stdeb.cfg
            config_fname = os.path.join(egg_info_dirname,'stdeb.cfg')
            if os.path.exists(config_fname):
                log.warn('Deprecation warning: stdeb detected old location of '
                         'stdeb.cfg in %s. This file will be used, but you '
                         'should move it alongside setup.py.' %egg_info_dirname)
                cfg_files.append(config_fname)

            egg_module_name = egg_info_dirname[:egg_info_dirname.index('.egg-info')]
            egg_module_name = egg_module_name.split(os.sep)[-1]

            if 1:
                # determine whether script specifies setuptools entry_points
                ep_fname = os.path.join(egg_info_dirname,'entry_points.txt')
                if os.path.exists(ep_fname):
                    entry_points = open(ep_fname,'rU').readlines()
                else:
                    entry_points = ''
                entry_points = [ep.strip() for ep in entry_points]

                if ('[console_scripts]' in entry_points or
                    '[gui_scripts]' in entry_points):
                    have_script_entry_points = True
        else:
            # We don't have setuptools, so guess egg_info_dirname to
            # find old stdeb.cfg.

            entries = os.listdir(os.curdir)
            for entry in entries:
                if not (entry.endswith('.egg-info') and os.path.isdir(entry)):
                    continue
                # Pickup old location of stdeb.cfg
                config_fname = os.path.join(entry,'stdeb.cfg')
                if os.path.exists(config_fname):
                    log.warn('Deprecation warning: stdeb detected '
                             'stdeb.cfg in %s. This file will be used, but you '
                             'should move it alongside setup.py.' % entry)
                    cfg_files.append(config_fname)

        if have_script_entry_points is None:
            have_script_entry_points = self.distribution.has_scripts()

        debinfo = DebianInfo(
            cfg_files=cfg_files,
            module_name = module_name,
            default_distribution=self.default_distribution,
            guess_maintainer=guess_maintainer,
            upstream_version = self.distribution.get_version(),
            has_ext_modules = self.distribution.has_ext_modules(),
            description = self.distribution.get_description()[:60],
            long_description = self.distribution.get_long_description(),
            patch_file = self.patch_file,
            patch_level = self.patch_level,
            debian_version = self.debian_version,
            force_buildsystem=self.force_buildsystem,
            have_script_entry_points = have_script_entry_points,
            setup_requires = (), # XXX How do we get the setup_requires?
            use_setuptools = use_setuptools,
            guess_conflicts_provides_replaces=self.guess_conflicts_provides_replaces,
            sdist_dsc_command = self,
        )
        return debinfo

########NEW FILE########
__FILENAME__ = debianize
from distutils.core import Command
from common import common_debian_package_command

from stdeb.util import DebianInfo, build_dsc, stdeb_cmdline_opts, \
     stdeb_cmd_bool_opts, stdeb_cfg_options

class debianize(common_debian_package_command):
    description = "distutils command to create a debian directory"

    user_options = stdeb_cmdline_opts + stdeb_cfg_options
    boolean_options = stdeb_cmd_bool_opts

    def run(self):
        debinfo = self.get_debinfo()
        if debinfo.patch_file != '':
            raise RuntimeError('Patches cannot be applied in debianize command')

        dist_dir = None
        repackaged_dirname = None

        build_dsc(debinfo,
                  dist_dir,
                  repackaged_dirname,
                  debian_dir_only=True,
                  )

########NEW FILE########
__FILENAME__ = install_deb
import os, glob
import stdeb.util as util

from distutils.core import Command

__all__ = ['install_deb']

class install_deb(Command):
    description = 'distutils command to install debian binary package'

    user_options = []
    boolean_options = []

    def initialize_options (self):
        pass

    def finalize_options (self):
        pass

    def run(self):
        # generate .deb file
        self.run_command('bdist_deb')

        # get relevant options passed to sdist_dsc
        sdist_dsc = self.get_finalized_command('sdist_dsc')

        # execute system command and read output (execute and read output of find cmd)
        target_dirs = []
        target_debs = glob.glob( os.path.join( sdist_dsc.dist_dir, '*.deb' ) )

        if len(target_debs)>1:
            raise ValueError('More than one .deb file in deb_dist. '
                             'Unsure which is desired. All: %r'%(
                target_debs,))

        if len(target_debs)==0:
            raise ValueError('could not find .deb file')

        # define system command to execute (gen .deb binary pkg)
        syscmd = ['dpkg','--install',target_debs[0]]

        util.process_command(syscmd)

########NEW FILE########
__FILENAME__ = sdist_dsc
import sys, os, shutil, tempfile

from stdeb import log
from stdeb.util import expand_sdist_file, recursive_hardlink
from stdeb.util import DebianInfo, build_dsc, stdeb_cmdline_opts, \
     stdeb_cmd_bool_opts, stdeb_cfg_options
from stdeb.util import repack_tarball_with_debianized_dirname
from common import common_debian_package_command

__all__ = ['sdist_dsc']

class sdist_dsc(common_debian_package_command):
    description = "distutils command to create a debian source distribution"

    user_options = stdeb_cmdline_opts + [
        ('use-premade-distfile=','P',
         'use .zip or .tar.gz file already made by sdist command'),
        ] + stdeb_cfg_options

    boolean_options = stdeb_cmd_bool_opts

    def initialize_options(self):
        self.use_premade_distfile = None
        common_debian_package_command.initialize_options(self)

    def run(self):
        debinfo = self.get_debinfo()
        if debinfo.patch_file != '' and self.patch_already_applied:
            raise RuntimeError('A patch was already applied, but another '
                               'patch is requested.')

        repackaged_dirname = debinfo.source+'-'+debinfo.upstream_version
        fullpath_repackaged_dirname = os.path.join(self.dist_dir,
                                                   repackaged_dirname)

        cleanup_dirs = []
        if self.use_premade_distfile is None:
            # generate original tarball
            sdist_cmd = self.distribution.get_command_obj('sdist')
            self.run_command('sdist')

            source_tarball = None
            for archive_file in sdist_cmd.get_archive_files():
                if archive_file.endswith('.tar.gz'):
                    source_tarball = archive_file

            if source_tarball is None:
                raise RuntimeError('sdist did not produce .tar.gz file')

            # make copy of source tarball in deb_dist/
            local_source_tarball = os.path.split(source_tarball)[-1]
            shutil.copy2( source_tarball, local_source_tarball )
            source_tarball = local_source_tarball
            self.use_premade_distfile = source_tarball
        else:
            source_tarball = self.use_premade_distfile

        # Copy source tree assuming that package-0.1.tar.gz contains
        # single top-level path 'package-0.1'. The contents of this
        # directory are then used.

        if os.path.exists(fullpath_repackaged_dirname):
            shutil.rmtree(fullpath_repackaged_dirname)

        tmpdir = tempfile.mkdtemp()
        expand_sdist_file( os.path.abspath(source_tarball),
                           cwd=tmpdir )
        expanded_base_files = os.listdir(tmpdir)
        assert len(expanded_base_files)==1
        actual_package_dirname = expanded_base_files[0]
        expected_package_dirname = debinfo.module_name + '-' + debinfo.upstream_version
        assert actual_package_dirname==expected_package_dirname
        shutil.move( os.path.join( tmpdir, actual_package_dirname ),
                     fullpath_repackaged_dirname)

        if self.use_premade_distfile is not None:
        # ensure premade sdist can actually be used
            self.use_premade_distfile = os.path.abspath(self.use_premade_distfile)
            expand_dir = os.path.join(self.dist_dir,'tmp_sdist_dsc')
            cleanup_dirs.append(expand_dir)
            if os.path.exists(expand_dir):
                shutil.rmtree(expand_dir)
            if not os.path.exists(self.dist_dir):
                os.mkdir(self.dist_dir)
            os.mkdir(expand_dir)

            expand_sdist_file(self.use_premade_distfile,cwd=expand_dir)

            is_tgz=False
            if self.use_premade_distfile.lower().endswith('.tar.gz'):
                is_tgz=True

            # now the sdist package is expanded in expand_dir
            expanded_root_files = os.listdir(expand_dir)
            assert len(expanded_root_files)==1
            distname_in_premade_distfile = expanded_root_files[0]
            debianized_dirname = repackaged_dirname
            original_dirname = os.path.split(distname_in_premade_distfile)[-1]
            do_repack=False
            if is_tgz:
                source_tarball = self.use_premade_distfile
            else:
                log.warn('WARNING: .orig.tar.gz will be generated from sdist '
                         'archive ("%s") because it is not a .tar.gz file',
                         self.use_premade_distfile)
                do_repack=True

            if do_repack:
                tmp_dir = os.path.join(self.dist_dir, 'tmp_repacking_dir' )
                os.makedirs( tmp_dir )
                cleanup_dirs.append(tmp_dir)
                source_tarball = os.path.join(tmp_dir,'repacked_sdist.tar.gz')
                repack_tarball_with_debianized_dirname(self.use_premade_distfile,
                                                       source_tarball,
                                                       debianized_dirname,
                                                       original_dirname )
            if source_tarball is not None:
                # Because we deleted all .pyc files above, if the
                # original source dist has them, we will have
                # (wrongly) deleted them. So, quit loudly rather
                # than fail silently.
                for root, dirs, files in os.walk(fullpath_repackaged_dirname):
                    for name in files:
                        if name.endswith('.pyc'):
                            raise RuntimeError('original source dist cannot '
                                               'contain .pyc files')

        ###############################################
        # 3. Find all directories

        for pkgdir in self.distribution.packages or []:
            debinfo.dirlist += ' ' + pkgdir.replace('.', '/')

        ###############################################
        # 4. Build source tree and rename it to be in self.dist_dir

        build_dsc(debinfo,
                  self.dist_dir,
                  repackaged_dirname,
                  orig_sdist=source_tarball,
                  patch_posix = self.patch_posix,
                  remove_expanded_source_dir=self.remove_expanded_source_dir,
                  )

        for rmdir in cleanup_dirs:
            shutil.rmtree(rmdir)

########NEW FILE########
__FILENAME__ = downloader
import os
import xmlrpclib
import requests
import hashlib
import warnings
from stdeb.transport import RequestsTransport

def myprint(mystr,fd=None):
    if fd is None:
        print mystr
    else:
        print >> fd, mystr

USER_AGENT = 'pypi-install/0.7.1 ( https://github.com/astraw/stdeb )'

def find_tar_gz(package_name, pypi_url = 'https://pypi.python.org/pypi',
                verbose=0, release=None):
    transport = RequestsTransport()
    transport.user_agent = USER_AGENT
    if pypi_url.startswith('https://'):
        transport.use_https = True
    pypi = xmlrpclib.ServerProxy(pypi_url, transport=transport)

    download_url = None
    expected_md5_digest = None

    if verbose >= 2:
        myprint( 'querying PyPI (%s) for package name "%s"' % (pypi_url,
                                                               package_name) )

    show_hidden=True
    all_releases = pypi.package_releases(package_name,show_hidden)
    if release is not None:
        # A specific release is requested.
        if verbose >= 2:
            myprint( 'found all available releases: %s' % (', '.join(all_releases),) )

        if release not in all_releases:
            raise ValueError('your desired release %r is not among available '
                             'releases %r'%(release,all_releases))
        version = release
    else:
        default_releases = pypi.package_releases(package_name)
        if len(default_releases)!=1:
            raise RuntimeError('Expected one and only one release. '
                               'Non-hidden: %r. All: %r'%(
                default_releases,all_releases))
        default_release = default_releases[0]
        if verbose >= 2:
            myprint( 'found default release: %s' % (', '.join(default_releases),) )

        version = default_release

    urls = pypi.release_urls( package_name,version)
    for url in urls:
        if url['packagetype']=='sdist':
            assert url['python_version']=='source', 'how can an sdist not be a source?'
            if url['url'].endswith('.tar.gz'):
                download_url = url['url']
                if 'md5_digest' in url:
                    expected_md5_digest = url['md5_digest']
                break

    if download_url is None:
        # PyPI doesn't have package. Is download URL provided?
        result = pypi.release_data(package_name,version)
        if result['download_url'] != 'UNKNOWN':
            download_url = result['download_url']
            # no download URL provided, see if PyPI itself has download
            urls = pypi.release_urls( result['name'], result['version'] )
    if download_url is None:
        raise ValueError('no package "%s" was found'%package_name)
    return download_url, expected_md5_digest

def get_source_tarball(package_name,verbose=0,allow_unsafe_download=False,
                       release=None):
    download_url, expected_md5_digest = find_tar_gz(package_name,
                                                    verbose=verbose,
                                                    release=release)
    if not download_url.startswith('https://'):
        if allow_unsafe_download:
            warnings.warn('downloading from unsafe url: %r' % download_url)
        else:
            raise ValueError('PYPI returned unsafe url: %r' % download_url)

    fname = download_url.split('/')[-1]
    if expected_md5_digest is not None:
        if os.path.exists(fname):
            m = hashlib.md5()
            m.update(open(fname,mode='r').read())
            actual_md5_digest = m.hexdigest()
            if actual_md5_digest == expected_md5_digest:
                if verbose >= 1:
                    myprint( 'Download URL: %s' % download_url )
                    myprint( 'File "%s" already exists with correct checksum.' % fname )
                return fname
            else:
                raise ValueError('File "%s" exists but has wrong checksum.'%fname)
    if verbose >= 1:
        myprint( 'downloading %s' % download_url )
    headers = {'User-Agent': USER_AGENT }
    r = requests.get(download_url, headers=headers)
    r.raise_for_status()
    package_tar_gz = r.content
    if verbose >= 1:
        myprint( 'done downloading %d bytes.' % ( len(package_tar_gz), ) )
    if expected_md5_digest is not None:
        m = hashlib.md5()
        m.update(package_tar_gz)
        actual_md5_digest = m.hexdigest()
        if verbose >= 2:
            myprint( 'md5:   actual %s\n     expected %s' % (actual_md5_digest,
                                                             expected_md5_digest))
        if actual_md5_digest != expected_md5_digest:
            raise ValueError('actual and expected md5 digests do not match')
    else:
        warnings.warn('no md5 digest found -- cannot verify source file')

    fd = open(fname,mode='wb')
    fd.write( package_tar_gz )
    fd.close()
    return fname

########NEW FILE########
__FILENAME__ = transport
# -*- coding: utf-8 -*-
"""
A replacement transport for Python xmlrpc library.

Usage:

    >>> import xmlrpclib
    >>> from transport import RequestsTransport
    >>> s = xmlrpclib.ServerProxy('http://yoursite.com/xmlrpc', transport=RequestsTransport())
    >>> s.demo.sayHello()
    Hello!
"""
try:
    import xmlrpc.client as xmlrpc
except ImportError:
    import xmlrpclib as xmlrpc

import requests
import requests.utils

import sys
from distutils.version import StrictVersion
import warnings

class RequestsTransport(xmlrpc.Transport):
    """
    Drop in Transport for xmlrpclib that uses Requests instead of httplib
    """
    # change our user agent to reflect Requests
    user_agent = "Python XMLRPC with Requests (python-requests.org)"

    # override this if you'd like to https
    use_https = False

    def request(self, host, handler, request_body, verbose):
        """
        Make an xmlrpc request.
        """
        headers = {'User-Agent': self.user_agent,
                   'Content-Type': 'text/xml',
                   }
        url = self._build_url(host, handler)
        kwargs = {}
        if StrictVersion(requests.__version__) >= StrictVersion('0.8.8'):
            kwargs['verify']=True
        else:
            if self.use_https:
                warnings.warn('using https transport but no certificate '
                              'verification. (Hint: upgrade requests package.)')
        try:
            resp = requests.post(url, data=request_body, headers=headers,
                                 **kwargs)
        except ValueError:
            raise
        except Exception:
            raise # something went wrong
        else:
            try:
                resp.raise_for_status()
            except requests.RequestException as e:
                raise xmlrpc.ProtocolError(url, resp.status_code, 
                                                        str(e), resp.headers)
            else:
                return self.parse_response(resp)

    def parse_response(self, resp):
        """
        Parse the xmlrpc response.
        """
        p, u = self.getparser()

        if hasattr(resp,'text'):
            # modern requests will do this for us
            text = resp.text # this is unicode(py2)/str(py3)
        else:

            encoding = requests.utils.get_encoding_from_headers(resp.headers)
            if encoding is None:
                encoding='utf-8' # FIXME: what to do here?

            if sys.version_info[0]==2:
                text = unicode(resp.content, encoding, errors='replace')
            else:
                assert sys.version_info[0]==3
                text = str(resp.content, encoding, errors='replace')
        p.feed(text)
        p.close()
        return u.close()

    def _build_url(self, host, handler):
        """
        Build a url for our request based on the host, handler and use_http
        property
        """
        scheme = 'https' if self.use_https else 'http'
        return '%s://%s/%s' % (scheme, host, handler)
########NEW FILE########
__FILENAME__ = util
#
# This module contains most of the code of stdeb.
#
import re, sys, os, shutil, select
import ConfigParser
import subprocess
import tempfile
import stdeb
from stdeb import log, __version__ as __stdeb_version__

if hasattr(os,'link'):
    link_func = os.link
else:
    # matplotlib deletes link from os namespace, expected distutils workaround
    link_func = shutil.copyfile

__all__ = ['DebianInfo','build_dsc','expand_tarball','expand_zip',
           'stdeb_cmdline_opts','stdeb_cmd_bool_opts','recursive_hardlink',
           'apply_patch','repack_tarball_with_debianized_dirname',
           'expand_sdist_file','stdeb_cfg_options']

DH_MIN_VERS = '7'       # Fundamental to stdeb >= 0.4
DH_IDEAL_VERS = '7.4.3' # fixes Debian bug 548392

PYTHON_ALL_MIN_VERS = '2.6.6-3'

import exceptions
class CalledProcessError(exceptions.Exception): pass
class CantSatisfyRequirement(exceptions.Exception): pass

def check_call(*popenargs, **kwargs):
    retcode = subprocess.call(*popenargs, **kwargs)
    if retcode == 0:
        return
    raise CalledProcessError(retcode)

stdeb_cmdline_opts = [
    ('dist-dir=', 'd',
     "directory to put final built distributions in (default='deb_dist')"),
    ('patch-already-applied','a',
     'patch was already applied (used when py2dsc calls sdist_dsc)'),
    ('default-distribution=', None,
     "deprecated (see --suite)"),
    ('suite=', 'z',
     "distribution name to use if not specified in .cfg (default='unstable')"),
    ('default-maintainer=', None,
     'deprecated (see --maintainer)'),
    ('maintainer=', 'm',
     'maintainer name and email to use if not specified in .cfg '
     '(default from setup.py)'),
    ('extra-cfg-file=','x',
     'additional .cfg file (in addition to stdeb.cfg if present)'),
    ('patch-file=','p',
     'patch file applied before setup.py called '
     '(incompatible with file specified in .cfg)'),
    ('patch-level=','l',
     'patch file applied before setup.py called '
     '(incompatible with file specified in .cfg)'),
    ('patch-posix','q',
     'apply the patch with --posix mode'),
    ('remove-expanded-source-dir','r',
     'remove the expanded source directory'),
    ('ignore-install-requires', 'i',
     'ignore the requirements from requires.txt in the egg-info directory'),
    ('pycentral-backwards-compatibility=',None,
     'This option has no effect, is here for backwards compatibility, and may '
     'be removed someday.'),
    ('workaround-548392=',None,
     'This option has no effect, is here for backwards compatibility, and may '
     'be removed someday.'),
    ('force-buildsystem=',None,
     "If True, pass '--buildsystem=python_distutils' to dh sequencer"),
    ('no-backwards-compatibility',None,
     'This option has no effect, is here for backwards compatibility, and may '
     'be removed someday.'),
    ('guess-conflicts-provides-replaces=',None,
     'If True, attempt to guess Conflicts/Provides/Replaces in debian/control '
     'based on apt-cache output. (Default=False).'),
    ]

# old entries from stdeb.cfg:

# These should be settable as distutils command options, but in case
# we want to support other packaging methods, they should also be
# settable outside distutils. Consequently, we keep the ability to
# parse ConfigParser files (specified with --extra-cfg-file). TODO:
# Also, some (most, in fact) of the above options should also be
# settable in the ConfigParser file.

stdeb_cfg_options = [
    # With defaults
    ('source=',None,
     'debian/control Source: (Default: <source-debianized-setup-name>)'),
    ('package=',None,
     'debian/control Package: (Default: python-<debianized-setup-name>)'),
    ('suite=',None,
     'suite (e.g. stable, lucid) in changelog (Default: unstable)'),
    ('maintainer=',None,
     'debian/control Maintainer: (Default: <setup-maintainer-or-author>)'),
    ('debian-version=',None,'debian version (Default: 1)'),
    ('section=',None,'debian/control Section: (Default: python)'),

    # With no defaults
    ('epoch=',None,'version epoch'),
    ('forced-upstream-version=',None,'forced upstream version'),
    ('upstream-version-prefix=',None,'upstream version prefix'),
    ('upstream-version-suffix=',None,'upstream version suffix'),
    ('uploaders=',None,'uploaders'),
    ('copyright-file=',None,'copyright file'),
    ('build-depends=',None,'debian/control Build-Depends:'),
    ('build-conflicts=',None,'debian/control Build-Conflicts:'),
    ('stdeb-patch-file=',None,'file containing patches for stdeb to apply'),
    ('stdeb-patch-level=',None,'patch level provided to patch command'),
    ('depends=',None,'debian/control Depends:'),
    ('suggests=',None,'debian/control Suggests:'),
    ('recommends=',None,'debian/control Recommends:'),
    ('xs-python-version=',None,'debian/control XS-Python-Version:'),
    ('dpkg-shlibdeps-params=',None,'parameters passed to dpkg-shlibdeps'),
    ('conflicts=',None,'debian/control Conflicts:'),
    ('provides=',None,'debian/control Provides:'),
    ('replaces=',None,'debian/control Replaces:'),
    ('mime-desktop-files=',None,'MIME desktop files'),
    ('mime-file=',None,'MIME file'),
    ('shared-mime-file=',None,'shared MIME file'),
    ('setup-env-vars=',None,'environment variables passed to setup.py'),
    ('udev-rules=',None,'file with rules to install to udev'),
    ]

stdeb_cmd_bool_opts = [
    'patch-already-applied',
    'remove-expanded-source-dir',
    'patch-posix',
    'ignore-install-requires',
    'no-backwards-compatibility',
    ]

class NotGiven: pass

def process_command(args, cwd=None):
    if not isinstance(args, (list, tuple)):
        raise RuntimeError, "args passed must be in a list"
    check_call(args, cwd=cwd)

def recursive_hardlink(src,dst):
    dst = os.path.abspath(dst)
    orig_dir = os.path.abspath(os.curdir)
    os.chdir(src)
    try:
        for root,dirs,files in os.walk(os.curdir):
            for file in files:
                fullpath = os.path.normpath(os.path.join(root,file))
                dirname, fname = os.path.split(fullpath)
                dstdir = os.path.normpath(os.path.join(dst,dirname))
                if not os.path.exists(dstdir):
                    os.makedirs(dstdir)
                newpath = os.path.join(dstdir,fname)
                if os.path.exists(newpath):
                    if os.path.samefile(fullpath,newpath):
                        continue
                    else:
                        os.unlink(newpath)
                #print 'linking %s -> %s'%(fullpath,newpath)
                link_func(fullpath,newpath)
    finally:
        os.chdir(orig_dir)

def debianize_name(name):
    "make name acceptable as a Debian (binary) package name"
    name = name.replace('_','-')
    name = name.lower()
    return name

def source_debianize_name(name):
    "make name acceptable as a Debian source package name"
    name = name.replace('_','-')
    name = name.replace('.','-')
    name = name.lower()
    return name

def debianize_version(name):
    "make name acceptable as a Debian package name"
    name = name.replace('_','-')

    # XXX should use setuptools' version sorting and do this properly:
    name = name.replace('.dev','~dev')

    name = name.lower()
    return name

def dpkg_compare_versions(v1,op,v2):
    args = ['/usr/bin/dpkg','--compare-versions',v1,op,v2]
    cmd = subprocess.Popen(args)
    returncode = cmd.wait()
    if returncode:
        return False
    else:
        return True

def get_cmd_stdout(args):
    cmd = subprocess.Popen(args,stdout=subprocess.PIPE)
    returncode = cmd.wait()
    if returncode:
        log.error('ERROR running: %s', ' '.join(args))
        raise RuntimeError('returncode %d', returncode)
    return cmd.stdout.read()

def get_date_822():
    """return output of 822-date command"""
    cmd = '/bin/date'
    if not os.path.exists(cmd):
        raise ValueError('%s command does not exist.'%cmd)
    args = [cmd,'-R']
    result = get_cmd_stdout(args).strip()
    return result

def get_version_str(pkg):
    args = ['/usr/bin/dpkg-query','--show',
           '--showformat=${Version}',pkg]
    stdout = get_cmd_stdout(args)
    return stdout.strip()

def load_module(name,fname):
    import imp

    suffix = '.py'
    found = False
    for description in imp.get_suffixes():
        if description[0]==suffix:
            found = True
            break
    assert found

    fd = open(fname,mode='r')
    try:
        module = imp.load_module(name,fd,fname,description)
    finally:
        fd.close()
    return module

def get_deb_depends_from_setuptools_requires(requirements, on_failure="warn"):
    """
    Suppose you can't confidently figure out a .deb which satisfies a given
    requirement.  If on_failure == 'warn', then log a warning.  If on_failure
    == 'raise' then raise CantSatisfyRequirement exception.  If on_failure ==
    'guess' then guess that python-$FOO will satisfy the dependency and that
    the Python version numbers will apply to the Debian packages (in addition
    to logging a warning message).
    """
    assert on_failure in ("raise", "warn", "guess"), on_failure

    import pkg_resources

    depends = [] # This will be the return value from this function.

    parsed_reqs=[]

    for extra,reqs in pkg_resources.split_sections(requirements):
        if extra: continue
        parsed_reqs.extend(pkg_resources.parse_requirements(reqs))

    if not parsed_reqs:
        return depends

    if not os.path.exists('/usr/bin/apt-file'):
        raise ValueError('apt-file not in /usr/bin. Please install '
                         'with: sudo apt-get install apt-file')

    # Ask apt-file for any packages which have a .egg-info file by
    # these names.

    # Note that apt-file appears to think that some packages
    # e.g. setuptools itself have "foo.egg-info/BLAH" files but not a
    # "foo.egg-info" directory.

    egginfore=("(/(%s)(?:-[^/]+)?(?:-py[0-9]\.[0-9.]+)?\.egg-info)"
               % '|'.join(req.project_name.replace('-', '_') for req in parsed_reqs))

    args = ["apt-file", "search", "--ignore-case", "--regexp", egginfore]

    if 1:
        # do dry run on apt-file
        dry_run_args = args[:] + ['--dummy','--non-interactive']
        cmd = subprocess.Popen(dry_run_args,stderr=subprocess.PIPE)
        returncode = cmd.wait()
        if returncode:
            err_output = cmd.stderr.read()
            raise RuntimeError('Error running "apt-file search": ' +
                               err_output.strip())

    try:
        cmd = subprocess.Popen(args, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    except Exception, le:
        # TODO: catch rc=1 and "E: The cache directory is empty. You need to
        # run 'apt-file update' first.", and tell the user to follow those
        # instructions.
        log.error('ERROR running: %s', ' '.join(args))
        raise RuntimeError('exception %s from subprocess %s' % (le,args))
    returncode = cmd.wait()
    if returncode:
        log.error('ERROR running: %s', ' '.join(args))
        raise RuntimeError('returncode %d from subprocess %s' % (returncode,
                                                                 args))

    inlines = cmd.stdout.readlines()

    dd = {} # {pydistname: {pydist: set(debpackagename)}}
    E=re.compile(egginfore, re.I)
    D=re.compile("^([^:]*):", re.I)
    eggsndebs = set()
    for l in inlines:
        if l:
            emo = E.search(l)
            assert emo, l
            dmo = D.search(l)
            assert dmo, l
            eggsndebs.add((emo.group(1), dmo.group(1)))

    for (egginfo, debname) in eggsndebs:
        pydist = pkg_resources.Distribution.from_filename(egginfo)
        try:
            dd.setdefault(
                pydist.project_name.lower(), {}).setdefault(
                pydist, set()).add(debname)
        except ValueError, le:
            log.warn("I got an error parsing a .egg-info file named \"%s\" "
                     "from Debian package \"%s\" as a pkg_resources "
                     "Distribution: %s" % (egginfo, debname, le,))
            pass

    # Now for each requirement, see if a Debian package satisfies it.
    ops = {'<':'<<','>':'>>','==':'=','<=':'<=','>=':'>='}
    for req in parsed_reqs:
        reqname = req.project_name.lower()
        gooddebs = set()
        for pydist, debs in dd.get(reqname, {}).iteritems():
            if pydist in req:
                ## log.info("I found Debian packages \"%s\" which provides "
                ##          "Python package \"%s\", version \"%s\", which "
                ##          "satisfies our version requirements: \"%s\""
                ##          % (', '.join(debs), req.project_name, ver, req)
                gooddebs |= (debs)
            else:
                log.info("I found Debian packages \"%s\" which provides "
                         "Python package \"%s\" which "
                         "does not satisfy our version requirements: "
                         "\"%s\" -- ignoring."
                         % (', '.join(debs), req.project_name, req))
        if not gooddebs:
            if on_failure == 'warn':
                log.warn(
                    "I found no Debian package which provides the required "
                    "Python package \"%s\" with version requirements "
                    "\"%s\"."% (req.project_name, req.specs))
            elif on_failure == "raise":
                raise CantSatisfyRequirement(
                    "I found no Debian package which "
                    "provides the required Python package \"%s\" with version "
                    "requirements \"%s\"." % (req.project_name, req.specs), req)
            elif on_failure == "guess":
                log.warn("I found no Debian package which provides the "
                         "required Python package \"%s\" with version "
                         "requirements \"%s\".  Guessing blindly that the "
                         "name \"python-%s\" will be it, and that the Python "
                         "package version number requirements will apply to "
                         "the Debian package." % (req.project_name,
                                                  req.specs, reqname))
                gooddebs.add("python-" + reqname)
        elif len(gooddebs) == 1:
            log.info("I found a Debian package which provides the require "
                     "Python package.  Python package: \"%s\", "
                     "Debian package: \"%s\";  adding Depends specifications "
                     "for the following version(s): \"%s\""
                     % (req.project_name, tuple(gooddebs)[0], req.specs))
        else:
            log.warn("I found multiple Debian packages which provide the "
                     "Python distribution required.  I'm listing them all "
                     "as alternates.  Candidate debs which claim to provide "
                     "the Python package \"%s\" are: \"%s\""
                     % (req.project_name, ', '.join(gooddebs),))

        alts = []
        for deb in gooddebs:
            added_any_alt = False
            for spec in req.specs:
                # Here we blithely assume that the Debian package
                # versions are enough like the Python package versions
                # that the requirement can be ported straight over...
                alts.append("%s (%s %s)" % (deb, ops[spec[0]], spec[1]))
                added_any_alt = True

            if not added_any_alt:
                # No alternates were added, but we have the name of a
                # good package.
                alts.append("%s"%deb)

        if len(alts):
            depends.append(' | '.join(alts))

    return depends

def make_tarball(tarball_fname,directory,cwd=None):
    "create a tarball from a directory"
    if tarball_fname.endswith('.gz'): opts = 'czf'
    else: opts = 'cf'
    args = ['/bin/tar',opts,tarball_fname,directory]
    process_command(args, cwd=cwd)


def expand_tarball(tarball_fname,cwd=None):
    "expand a tarball"
    if tarball_fname.endswith('.gz'): opts = 'xzf'
    elif tarball_fname.endswith('.bz2'): opts = 'xjf'
    else: opts = 'xf'
    args = ['/bin/tar',opts,tarball_fname]
    process_command(args, cwd=cwd)


def expand_zip(zip_fname,cwd=None):
    "expand a zip"
    unzip_path = '/usr/bin/unzip'
    if not os.path.exists(unzip_path):
        log.error('ERROR: {} does not exist'.format(unzip_path))
        sys.exit(1)
    args = [unzip_path, zip_fname]
    # Does it have a top dir
    res = subprocess.Popen(
        [args[0], '-l', args[1]], cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    contents = []
    for line in res.stdout.readlines()[3:-2]:
        contents.append(line.split()[-1])
    commonprefix = os.path.commonprefix(contents)
    if not commonprefix:
        extdir = os.path.join(cwd, os.path.basename(zip_fname[:-4]))
        args.extend(['-d', os.path.abspath(extdir)])

    process_command(args, cwd=cwd)


def expand_sdist_file(sdist_file,cwd=None):
    lower_sdist_file = sdist_file.lower()
    if lower_sdist_file.endswith('.zip'):
        expand_zip(sdist_file,cwd=cwd)
    elif lower_sdist_file.endswith('.tar.bz2'):
        expand_tarball(sdist_file,cwd=cwd)
    elif lower_sdist_file.endswith('.tar.gz'):
        expand_tarball(sdist_file,cwd=cwd)
    else:
        raise RuntimeError('could not guess format of original sdist file')

def repack_tarball_with_debianized_dirname( orig_sdist_file,
                                            repacked_sdist_file,
                                            debianized_dirname,
                                            original_dirname ):
    working_dir = tempfile.mkdtemp()
    expand_sdist_file( orig_sdist_file, cwd=working_dir )
    fullpath_original_dirname = os.path.join(working_dir,original_dirname)
    fullpath_debianized_dirname = os.path.join(working_dir,debianized_dirname)

    # ensure sdist looks like sdist:
    assert os.path.exists( fullpath_original_dirname )
    assert len(os.listdir(working_dir))==1

    if fullpath_original_dirname != fullpath_debianized_dirname:
        # rename original dirname to debianized dirname
        os.rename(fullpath_original_dirname,
                  fullpath_debianized_dirname)
    make_tarball(repacked_sdist_file,debianized_dirname,cwd=working_dir)
    shutil.rmtree(working_dir)

def dpkg_source(b_or_x,arg1,arg2=None,cwd=None):
    "call dpkg-source -b|x arg1 [arg2]"
    assert b_or_x in ['-b','-x']
    args = ['/usr/bin/dpkg-source',b_or_x,arg1]
    if arg2 is not None:
        args.append(arg2)

    process_command(args, cwd=cwd)

def apply_patch(patchfile,cwd=None,posix=False,level=0):
    """call 'patch -p[level] [--posix] < arg1'

    posix mode is sometimes necessary. It keeps empty files so that
    dpkg-source removes their contents.

    """
    if not os.path.exists(patchfile):
        raise RuntimeError('patchfile "%s" does not exist'%patchfile)
    fd = open(patchfile,mode='r')

    level_str = '-p%d'%level
    args = ['/usr/bin/patch',level_str]
    if posix:
        args.append('--posix')

    log.info('PATCH COMMAND: %s < %s', ' '.join(args), patchfile)
    log.info('  PATCHING in dir: %s', cwd)
#    print >> sys.stderr, 'PATCH COMMAND:',' '.join(args),'<',patchfile
#    print >> sys.stderr, '  PATCHING in dir:',cwd
    res = subprocess.Popen(
        args, cwd=cwd,
        stdin=fd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        )
    returncode=None
    while returncode is None:
        returncode = res.poll()
        ready = select.select( [res.stdout,res.stderr],[],[],0.1)
        # XXX figure out how to do this without reading byte-by-byte
        if res.stdout in ready[0]:
            sys.stdout.write(res.stdout.read(1))
            sys.stdout.flush()
        if res.stderr in ready[0]:
            sys.stderr.write(res.stderr.read(1))
            sys.stderr.flush()
    # finish outputting file
    sys.stdout.write(res.stdout.read())
    sys.stdout.flush()
    sys.stderr.write(res.stderr.read())
    sys.stderr.flush()

    if returncode:
        log.error('ERROR running: %s', ' '.join(args))
        log.error('ERROR in %s', cwd)
#        print >> sys.stderr, 'ERROR running: %s'%(' '.join(args),)
#        print >> sys.stderr, 'ERROR in',cwd
        raise RuntimeError('returncode %d'%returncode)

def parse_vals(cfg,section,option):
    """parse comma separated values in debian control file style from .cfg"""
    try:
        vals = cfg.get(section,option)
    except ConfigParser.NoSectionError, err:
        if section != 'DEFAULT':
            vals = cfg.get('DEFAULT',option)
        else:
            raise err
    vals = vals.split('#')[0]
    vals = vals.strip()
    vals = vals.split(',')
    vals = [v.strip() for v in vals]
    vals = [v for v in vals if len(v)]
    return vals

def parse_val(cfg,section,option):
    """extract a single value from .cfg"""
    vals = parse_vals(cfg,section,option)
    if len(vals)==0:
        return ''
    else:
        assert len(vals)==1, (section, option, vals, type(vals))
    return vals[0]

def apt_cache_info(apt_cache_cmd,package_name):
    if apt_cache_cmd not in ('showsrc','show'):
        raise NotImplementedError(
            "don't know how to run apt-cache command '%s'"%apt_cache_cmd)

    result_list = []
    args = ["apt-cache", apt_cache_cmd, package_name]
    cmd = subprocess.Popen(args,
                           stdin=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    returncode = cmd.wait()
    if returncode:
        errline = cmd.stderr.read()
        if not (returncode == 100 and errline == "E: You must put some 'source' URIs in your sources.list\n"):
            log.error('ERROR running: %s', ' '.join(args))
            raise RuntimeError('returncode %d from subprocess %s' % (returncode,
                                                                 args))
    inlines = cmd.stdout.read()
    version_blocks = inlines.split('\n\n')
    for version_block in version_blocks:
        block_dict = {}

        if len(version_block)==0:
            continue
        version_lines = version_block.split('\n')
        assert version_lines[0].startswith('Package: ')
        block_dict['Package'] = version_lines[0][ len('Package: '): ]

        if apt_cache_cmd == 'showsrc':
            assert version_lines[1].startswith('Binary: ')
            block_dict['Binary'] = version_lines[1][ len('Binary: '): ]
            block_dict['Binary'] = block_dict['Binary'].split(', ')

        elif apt_cache_cmd == 'show':
            for start in ('Provides: ','Conflicts: ','Replaces: '):
                key = start[:-2]
                for line in version_lines[2:]:
                    if line.startswith(start):
                        unsplit_line_result = line[ len(start): ]
                        split_result = unsplit_line_result.split(', ')
                        block_dict[key] = split_result
                if key not in block_dict:
                    block_dict[key] = []
        result_list.append(block_dict)
    return result_list

def check_cfg_files(cfg_files,module_name):
    """check if the configuration files actually specify something

    If config files are given, give warning if they don't contain
    information. This may indicate a wrong module name name, for
    example.
    """

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(cfg_files)
    if cfg.has_section(module_name):
        section_items = cfg.items(module_name)
    else:
        section_items = []
    default_items = cfg.items('DEFAULT')

    n_items = len(section_items) + len(default_items)
    if n_items==0:
        log.warn('configuration files were specified, but no options were '
                 'found in "%s" or "DEFAULT" sections.' % (module_name,) )

class DebianInfo:
    """encapsulate information for Debian distribution system"""
    def __init__(self,
                 cfg_files=NotGiven,
                 module_name=NotGiven,
                 default_distribution=NotGiven,
                 guess_maintainer=NotGiven,
                 upstream_version=NotGiven,
                 has_ext_modules=NotGiven,
                 description=NotGiven,
                 long_description=NotGiven,
                 patch_file=None,
                 patch_level=None,
                 setup_requires=None,
                 debian_version=None,
                 force_buildsystem=None,
                 have_script_entry_points = None,
                 use_setuptools = False,
                 guess_conflicts_provides_replaces = False,
                 sdist_dsc_command = None,
                 ):
        if cfg_files is NotGiven: raise ValueError("cfg_files must be supplied")
        if module_name is NotGiven: raise ValueError(
            "module_name must be supplied")
        if default_distribution is NotGiven: raise ValueError(
            "default_distribution must be supplied")
        if guess_maintainer is NotGiven: raise ValueError(
            "guess_maintainer must be supplied")
        if upstream_version is NotGiven: raise ValueError(
            "upstream_version must be supplied")
        if has_ext_modules is NotGiven: raise ValueError(
            "has_ext_modules must be supplied")
        if description is NotGiven: raise ValueError(
            "description must be supplied")
        if long_description is NotGiven: raise ValueError(
            "long_description must be supplied")

        cfg_defaults = self._make_cfg_defaults(
            module_name=module_name,
            default_distribution=default_distribution,
            guess_maintainer=guess_maintainer,
            )

        if len(cfg_files):
            check_cfg_files(cfg_files,module_name)

        cfg = ConfigParser.SafeConfigParser(cfg_defaults)
        cfg.read(cfg_files)

        if sdist_dsc_command is not None:
            # Allow distutils commands to override config files (this lets
            # command line options beat file options).
            for longopt, shortopt, desc in stdeb_cfg_options:
                opt_name = longopt[:-1]
                name = opt_name.replace('-','_')
                value = getattr( sdist_dsc_command, name )
                if value is not None:
                    if not cfg.has_section(module_name):
                        cfg.add_section(module_name)
                    cfg.set( module_name, opt_name, value )

        self.stdeb_version = __stdeb_version__
        self.module_name = module_name
        self.source = parse_val(cfg,module_name,'Source')
        self.package = parse_val(cfg,module_name,'Package')
        forced_upstream_version = parse_val(cfg,module_name,
                                            'Forced-Upstream-Version')
        if forced_upstream_version == '':
            upstream_version_prefix = parse_val(cfg,module_name,
                                                'Upstream-Version-Prefix')
            upstream_version_suffix = parse_val(cfg,module_name,
                                                'Upstream-Version-Suffix')
            self.upstream_version = (upstream_version_prefix+
                                        debianize_version(upstream_version)+
                                        upstream_version_suffix)
        else:
            if (debianize_version(forced_upstream_version) !=
                forced_upstream_version):
                raise ValueError('forced upstream version ("%s") not a '
                                 'Debian-compatible version (e.g. "%s")'%(
                    forced_upstream_version,
                    debianize_version(forced_upstream_version)))
            self.upstream_version = forced_upstream_version
        self.epoch = parse_val(cfg,module_name,'Epoch')
        if self.epoch != '' and not self.epoch.endswith(':'):
            self.epoch = self.epoch + ':'
        self.packaging_version = parse_val(cfg,module_name,'Debian-Version')
        if debian_version is not None:
            # command-line arg overrides file
            self.packaging_version = debian_version
        self.dsc_version = '%s-%s'%(
            self.upstream_version,
            self.packaging_version)
        self.full_version = '%s%s-%s'%(
            self.epoch,
            self.upstream_version,
            self.packaging_version)
        self.distname = parse_val(cfg,module_name,'Suite')
        self.maintainer = ', '.join(parse_vals(cfg,module_name,'Maintainer'))
        self.uploaders = parse_vals(cfg,module_name,'Uploaders')
        self.date822 = get_date_822()

        build_deps = []
        if use_setuptools:
            build_deps.append('python-setuptools (>= 0.6b3)')
        if setup_requires is not None and len(setup_requires):
            build_deps.extend(
                get_deb_depends_from_setuptools_requires(setup_requires))

        depends = ['${misc:Depends}', '${python:Depends}']
        need_custom_binary_target = False

        if has_ext_modules:
            self.architecture = 'any'
            build_deps.append('python-all-dev (>= %s)'%PYTHON_ALL_MIN_VERS)
            depends.append('${shlibs:Depends}')
        else:
            self.architecture = 'all'
            build_deps.append('python-all (>= %s)'%PYTHON_ALL_MIN_VERS)

        self.copyright_file = parse_val(cfg,module_name,'Copyright-File')
        self.mime_file = parse_val(cfg,module_name,'MIME-File')

        self.shared_mime_file = parse_val(cfg,module_name,'Shared-MIME-File')

        if self.mime_file == '' and self.shared_mime_file == '':
            self.dh_installmime_indep_line = ''
        else:
            need_custom_binary_target = True
            self.dh_installmime_indep_line = '\tdh_installmime'

        mime_desktop_files = parse_vals(cfg,module_name,'MIME-Desktop-Files')
        if len(mime_desktop_files):
            need_custom_binary_target = True
            self.dh_desktop_indep_line = '\tdh_desktop'
        else:
            self.dh_desktop_indep_line = ''

        #    E. any mime .desktop files
        self.install_file_lines = []
        for mime_desktop_file in mime_desktop_files:
            self.install_file_lines.append(
                '%s usr/share/applications'%mime_desktop_file)

        depends.extend(parse_vals(cfg,module_name,'Depends') )
        self.depends = ', '.join(depends)

        self.debian_section = parse_val(cfg,module_name,'Section')

        self.description = description
        if long_description != 'UNKNOWN':
            ld2=[]
            for line in long_description.split('\n'):
                ls = line.strip()
                if len(ls):
                    ld2.append(' '+line)
                else:
                    ld2.append(' .')
            ld2 = ld2[:20]
            self.long_description = '\n'.join(ld2)
        else:
            self.long_description = ''

        if have_script_entry_points:
            build_deps.append( 'debhelper (>= %s)'%DH_IDEAL_VERS )
        else:
            build_deps.append( 'debhelper (>= %s)'%DH_MIN_VERS )

        build_deps.extend( parse_vals(cfg,module_name,'Build-Depends') )
        self.build_depends = ', '.join(build_deps)

        suggests = ', '.join( parse_vals(cfg,module_name,'Suggests') )
        recommends = ', '.join( parse_vals(cfg,module_name,'Recommends') )

        self.source_stanza_extras = ''

        build_conflicts = parse_vals(cfg,module_name,'Build-Conflicts')
        if len(build_conflicts):
            self.source_stanza_extras += ('Build-Conflicts: '+
                                              ', '.join( build_conflicts )+'\n')

        self.patch_file = parse_val(cfg,module_name,'Stdeb-Patch-File')

        if patch_file is not None:
            if self.patch_file != '':
                raise RuntimeError('A patch file was specified on the command '
                                   'line and in .cfg file.')
            else:
                self.patch_file = patch_file

        self.patch_level = parse_val(cfg,module_name,'Stdeb-Patch-Level')
        if self.patch_level != '':
            if patch_level is not None:
                raise RuntimeError('A patch level was specified on the command '
                                   'line and in .cfg file.')
            else:
                self.patch_level = int(self.patch_level)
        else:
            if patch_level is not None:
                self.patch_level = patch_level
            else:
                self.patch_level = 0

        xs_python_version = parse_vals(cfg,module_name,'XS-Python-Version')

        if len(xs_python_version)!=0:
            self.source_stanza_extras += ('X-Python-Version: '+
                                          ', '.join(xs_python_version)+'\n')

        dpkg_shlibdeps_params = parse_val(
            cfg,module_name,'dpkg-shlibdeps-params')
        if dpkg_shlibdeps_params:
            need_custom_binary_target = True
            self.dh_binary_arch_lines = """\tdh binary-arch --before dh_shlibdeps
\tdh_shlibdeps -a --dpkg-shlibdeps-params=%s
\tdh binary --after dh_shlibdeps"""%dpkg_shlibdeps_params
        else:
            self.dh_binary_arch_lines = '\tdh binary-arch'
        self.dh_binary_indep_lines = '\tdh binary-indep'

        conflicts = parse_vals(cfg,module_name,'Conflicts')
        provides = parse_vals(cfg,module_name,'Provides')
        replaces = parse_vals(cfg,module_name,'Replaces')

        if guess_conflicts_provides_replaces:
            # Find list of binaries which we will conflict/provide/replace.

            cpr_binaries = set()

            # Get original Debian information for the package named the same.
            for version_info in apt_cache_info('showsrc',self.package):

                # Remember each of the binary packages produced by the Debian source
                for binary in version_info['Binary']:
                    cpr_binaries.add(binary)

                # TODO: do this for every version available , just the
                # first, or ???
                break

            # Descend each of the original binaries and see what
            # packages they conflict/ provide/ replace:
            for orig_binary in cpr_binaries:
                for version_info in apt_cache_info('show',orig_binary):
                    provides.extend( version_info['Provides'])
                    conflicts.extend(version_info['Conflicts'])
                    replaces.extend( version_info['Replaces'])

            if self.package in cpr_binaries:
                cpr_binaries.remove(self.package) # don't include ourself

            cpr_binaries = list(cpr_binaries) # convert to list

            conflicts.extend( cpr_binaries )
            provides.extend( cpr_binaries )
            replaces.extend( cpr_binaries )

            # round-trip through set to get unique entries
            conflicts = list(set(conflicts))
            provides = list(set(provides))
            replaces = list(set(replaces))

        self.package_stanza_extras = ''

        if len(conflicts):
            self.package_stanza_extras += ('Conflicts: '+
                                              ', '.join( conflicts )+'\n')

        if len(provides):
            self.package_stanza_extras += ('Provides: '+
                                             ', '.join( provides  )+'\n')

        if len(replaces):
            self.package_stanza_extras += ('Replaces: ' +
                                              ', '.join( replaces  )+'\n')
        if len(recommends):
            self.package_stanza_extras += ('Recommends: '+recommends+'\n')

        if len(suggests):
            self.package_stanza_extras += ('Suggests: '+suggests+'\n')

        self.dirlist = ""

        sequencer_options = ['--with python2']
        if force_buildsystem:
            sequencer_options.append('--buildsystem=python_distutils')
        self.sequencer_options = ' '.join(sequencer_options)

        setup_env_vars = parse_vals(cfg,module_name,'Setup-Env-Vars')
        self.force_buildsystem = force_buildsystem
        self.exports = ""
        if len(setup_env_vars):
            self.exports += '\n'
            self.exports += '#exports specified using stdeb Setup-Env-Vars:\n'
            self.exports += '\n'.join(['export %s'%v for v in setup_env_vars])
            self.exports += '\n'
        self.udev_rules = parse_val(cfg,module_name,'Udev-Rules')

        if need_custom_binary_target:
            if self.architecture == 'all':
                self.binary_target_lines = ( \
                    RULES_BINARY_ALL_TARGET%self.__dict__ + \
                    RULES_BINARY_INDEP_TARGET%self.__dict__ )
            else:
                self.binary_target_lines = ( \
                    RULES_BINARY_TARGET%self.__dict__ + \
                    RULES_BINARY_INDEP_TARGET%self.__dict__ + \
                    RULES_BINARY_ARCH_TARGET%self.__dict__ )
        else:
            self.binary_target_lines = ''

    def _make_cfg_defaults(self,
                           module_name=NotGiven,
                           default_distribution=NotGiven,
                           guess_maintainer=NotGiven,
                           ):
        defaults = {}
        default_re = re.compile(r'^.* \(Default: (.*)\)$')
        for longopt,shortopt,description in stdeb_cfg_options:
            assert longopt.endswith('=')
            assert longopt.lower() == longopt
            key = longopt[:-1]
            matchobj = default_re.search( description )
            if matchobj is not None:
                # has a default value
                groups = matchobj.groups()
                assert len(groups)==1
                value = groups[0]
                # A few special cases
                if value == '<source-debianized-setup-name>':
                    assert key=='source'
                    value = source_debianize_name(module_name)
                elif value == 'python-<debianized-setup-name>':
                    assert key=='package'
                    value = 'python-' + debianize_name(module_name)
                elif value == '<setup-maintainer-or-author>':
                    assert key=='maintainer'
                    value = guess_maintainer
                if key=='suite':
                    if default_distribution is not None:
                        value = default_distribution
                        log.warn('Deprecation warning: you are using the '
                                 '--default-distribution option. '
                                 'Switch to the --suite option.')
            else:
                # no default value
                value = ''
            defaults[key] = value
        return defaults

def build_dsc(debinfo,
              dist_dir,
              repackaged_dirname,
              orig_sdist=None,
              patch_posix=0,
              remove_expanded_source_dir=0,
              debian_dir_only=False,
              ):
    """make debian source package"""
    #    A. Find new dirname and delete any pre-existing contents

    # dist_dir is usually 'deb_dist'

    # the location of the copied original source package (it was
    # re-recreated in dist_dir)
    if debian_dir_only:
        fullpath_repackaged_dirname = os.path.abspath(os.curdir)
    else:
        fullpath_repackaged_dirname = os.path.join(dist_dir,repackaged_dirname)

    ###############################################
    # 1. make temporary original source tarball

    #    Note that, for the final tarball, best practices suggest
    #    using "dpkg-source -b".  See
    #    http://www.debian.org/doc/developers-reference/ch-best-pkging-practices.en.html

    # Create the name of the tarball that qualifies as the upstream
    # source. If the original was specified, we'll link to
    # it. Otherwise, we generate our own .tar.gz file from the output
    # of "python setup.py sdist" (done above) so that we avoid
    # packaging .svn directories, for example.

    if not debian_dir_only:
        repackaged_orig_tarball = ('%(source)s_%(upstream_version)s.orig.tar.gz'%
                                   debinfo.__dict__)
        repackaged_orig_tarball_path = os.path.join(dist_dir,
                                                    repackaged_orig_tarball)
        if orig_sdist is not None:
            if os.path.exists(repackaged_orig_tarball_path):
                os.unlink(repackaged_orig_tarball_path)
            link_func(orig_sdist,repackaged_orig_tarball_path)
        else:
            make_tarball(repackaged_orig_tarball,
                         repackaged_dirname,
                         cwd=dist_dir)

        # apply patch
        if debinfo.patch_file != '':
            apply_patch(debinfo.patch_file,
                        posix=patch_posix,
                        level=debinfo.patch_level,
                        cwd=fullpath_repackaged_dirname)

    for fname in ['Makefile','makefile']:
        if os.path.exists(os.path.join(fullpath_repackaged_dirname,fname)):
            sys.stderr.write('*'*1000 + '\n')
            if debinfo.force_buildsystem:
                sys.stderr.write('WARNING: a Makefile exists in this package. '
                                 'stdeb will tell debhelper 7 to use setup.py '
                                 'to build and install the package, and the '
                                 'Makefile will be ignored. You can disable '
                                 'this behavior with the '
                                 '--force-buildsystem=False argument to the '
                                 'stdeb command.\n')
            else:
                sys.stderr.write('WARNING: a Makefile exists in this package. '
                                 'debhelper 7 will attempt to use this rather '
                                 'than setup.py to build and install the '
                                 'package. You can disable this behavior with '
                                 'the --force-buildsystem=True argument to the '
                                 'stdeb command.\n')
            sys.stderr.write('*'*1000 + '\n')


    ###############################################
    # 2. create debian/ directory and contents
    debian_dir = os.path.join(fullpath_repackaged_dirname,'debian')
    if not os.path.exists(debian_dir):
        os.mkdir(debian_dir)

    #    A. debian/changelog
    fd = open( os.path.join(debian_dir,'changelog'), mode='w')
    fd.write("""\
%(source)s (%(full_version)s) %(distname)s; urgency=low

  * source package automatically created by stdeb %(stdeb_version)s

 -- %(maintainer)s  %(date822)s\n"""%debinfo.__dict__)
    fd.close()

    #    B. debian/control
    if debinfo.uploaders:
        debinfo.uploaders = 'Uploaders: %s\n' % ', '.join(debinfo.uploaders)
    else:
        debinfo.uploaders = ''
    control = CONTROL_FILE%debinfo.__dict__
    fd = open( os.path.join(debian_dir,'control'), mode='w')
    fd.write(control)
    fd.close()

    #    C. debian/rules
    debinfo.percent_symbol = '%'
    rules = RULES_MAIN%debinfo.__dict__

    rules = rules.replace('        ','\t')
    rules_fname = os.path.join(debian_dir,'rules')
    fd = open( rules_fname, mode='w')
    fd.write(rules)
    fd.close()
    os.chmod(rules_fname,0755)

    #    D. debian/compat
    fd = open( os.path.join(debian_dir,'compat'), mode='w')
    fd.write('7\n')
    fd.close()

    #    E. debian/package.mime
    if debinfo.mime_file != '':
        if not os.path.exists(debinfo.mime_file):
            raise ValueError(
                'a MIME file was specified, but does not exist: %s'%(
                debinfo.mime_file,))
        link_func( debinfo.mime_file,
                 os.path.join(debian_dir,debinfo.package+'.mime'))
    if debinfo.shared_mime_file != '':
        if not os.path.exists(debinfo.shared_mime_file):
            raise ValueError(
                'a shared MIME file was specified, but does not exist: %s'%(
                debinfo.shared_mime_file,))
        link_func( debinfo.shared_mime_file,
                 os.path.join(debian_dir,
                              debinfo.package+'.sharedmimeinfo'))

    #    F. debian/copyright
    if debinfo.copyright_file != '':
        link_func( debinfo.copyright_file,
                 os.path.join(debian_dir,'copyright'))

    #    H. debian/<package>.install
    if len(debinfo.install_file_lines):
        fd = open( os.path.join(debian_dir,'%s.install'%debinfo.package), mode='w')
        fd.write('\n'.join(debinfo.install_file_lines)+'\n')
        fd.close()

    #    I. debian/<package>.udev
    if debinfo.udev_rules != '':
        fname = debinfo.udev_rules
        if not os.path.exists(fname):
            raise ValueError('udev rules file specified, but does not exist')
        link_func(fname,
                  os.path.join(debian_dir,'%s.udev'%debinfo.package))

    #    J. debian/source/format
    os.mkdir(os.path.join(debian_dir,'source'))
    fd = open( os.path.join(debian_dir,'source','format'), mode='w')
    fd.write('1.0\n')
    fd.close()

    if debian_dir_only:
        return

    ###############################################
    # 3. unpack original source tarball

    debianized_package_dirname = fullpath_repackaged_dirname+'.debianized'
    if os.path.exists(debianized_package_dirname):
        raise RuntimeError('debianized_package_dirname exists: %s' %
                           debianized_package_dirname)
    #    A. move debianized tree away
    os.rename(fullpath_repackaged_dirname, debianized_package_dirname )
    if orig_sdist is not None:
        #    B. expand repackaged original tarball
        tmp_dir = os.path.join(dist_dir,'tmp-expand')
        os.mkdir(tmp_dir)
        try:
            expand_tarball(orig_sdist,cwd=tmp_dir)
            orig_tarball_top_contents = os.listdir(tmp_dir)

            # make sure original tarball has exactly one directory
            assert len(orig_tarball_top_contents)==1
            orig_dirname = orig_tarball_top_contents[0]
            fullpath_orig_dirname = os.path.join(tmp_dir,orig_dirname)

            #    C. move original repackaged tree to .orig
            target = fullpath_repackaged_dirname+'.orig'
            if os.path.exists(target):
                # here from previous invocation, probably
                shutil.rmtree(target)
            os.rename(fullpath_orig_dirname,target)

        finally:
            shutil.rmtree(tmp_dir)

    if 1:
        # check versions of debhelper and python-all
        debhelper_version_str = get_version_str('debhelper')
        if len(debhelper_version_str)==0:
            log.warn('This version of stdeb requires debhelper >= %s, but you '
                     'do not have debhelper installed. '
                     'Could not check compatibility.'%DH_MIN_VERS)
        else:
            if not dpkg_compare_versions(
                debhelper_version_str, 'ge', DH_MIN_VERS ):
                log.warn('This version of stdeb requires debhelper >= %s. '
                         'Use stdeb 0.3.x to generate source packages '
                         'compatible with older versions of debhelper.'%(
                    DH_MIN_VERS,))

        python_defaults_version_str = get_version_str('python-all')
        if len(python_defaults_version_str)==0:
            log.warn('This version of stdeb requires python-all >= %s, '
                     'but you do not have this package installed. '
                     'Could not check compatibility.'%PYTHON_ALL_MIN_VERS)
        else:
            if not dpkg_compare_versions(
                python_defaults_version_str, 'ge', PYTHON_ALL_MIN_VERS):
                log.warn('This version of stdeb requires python-all >= %s. '
                         'Use stdeb 0.6.0 or older to generate source packages '
                         'that use python-support.'%(
                    PYTHON_ALL_MIN_VERS,))

    #    D. restore debianized tree
    os.rename(fullpath_repackaged_dirname+'.debianized',
              fullpath_repackaged_dirname)

    #    Re-generate tarball using best practices see
    #    http://www.debian.org/doc/developers-reference/ch-best-pkging-practices.en.html
    #    call "dpkg-source -b new_dirname orig_dirname"
    log.info('CALLING dpkg-source -b %s %s (in dir %s)'%(
        repackaged_dirname,
        repackaged_orig_tarball,
        dist_dir))

    dpkg_source('-b',repackaged_dirname,
                repackaged_orig_tarball,
                cwd=dist_dir)

    if 1:
        shutil.rmtree(fullpath_repackaged_dirname)

    if not remove_expanded_source_dir:
        # expand the debian source package
        dsc_name = debinfo.source + '_' + debinfo.dsc_version + '.dsc'
        dpkg_source('-x',dsc_name,
                    cwd=dist_dir)

CONTROL_FILE = """\
Source: %(source)s
Maintainer: %(maintainer)s
%(uploaders)sSection: %(debian_section)s
Priority: optional
Build-Depends: %(build_depends)s
Standards-Version: 3.9.1
%(source_stanza_extras)s
Package: %(package)s
Architecture: %(architecture)s
Depends: %(depends)s
%(package_stanza_extras)sDescription: %(description)s
%(long_description)s
"""

RULES_MAIN = """\
#!/usr/bin/make -f

# This file was automatically generated by stdeb %(stdeb_version)s at
# %(date822)s
%(exports)s
%(percent_symbol)s:
        dh $@ %(sequencer_options)s

%(binary_target_lines)s
"""

RULES_BINARY_TARGET = """
binary: binary-arch binary-indep
"""

RULES_BINARY_ALL_TARGET = """
binary: binary-indep
"""

RULES_BINARY_ARCH_TARGET = """
binary-arch: build
%(dh_binary_arch_lines)s
"""

RULES_BINARY_INDEP_TARGET = """
binary-indep: build
%(dh_binary_indep_lines)s
%(dh_installmime_indep_line)s
%(dh_desktop_indep_line)s
"""

########NEW FILE########
