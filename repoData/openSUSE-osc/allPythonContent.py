__FILENAME__ = babysitter
# Copyright (C) 2008 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.

from __future__ import print_function

import errno
import os.path
import pdb
import sys
import signal
import traceback

from osc import oscerr
from .oscsslexcp import NoSecureSSLError
from osc.util.cpio import CpioError
from osc.util.packagequery import PackageError

try:
    from M2Crypto.SSL.Checker import SSLVerificationError
    from M2Crypto.SSL import SSLError as SSLError
except:
    SSLError = None
    SSLVerificationError = None

try:
    # import as RPMError because the class "error" is too generic
    from rpm import error as RPMError
except:
    # if rpm-python isn't installed (we might be on a debian system):
    RPMError = None

try:
    from http.client import HTTPException, BadStatusLine
    from urllib.error import URLError, HTTPError
except ImportError:
    #python 2.x
    from httplib import HTTPException, BadStatusLine
    from urllib2 import URLError, HTTPError

# the good things are stolen from Matt Mackall's mercurial


def catchterm(*args):
    raise oscerr.SignalInterrupt

for name in 'SIGBREAK', 'SIGHUP', 'SIGTERM':
    num = getattr(signal, name, None)
    if num:
        signal.signal(num, catchterm)


def run(prg, argv=None):
    try:
        try:
            if '--debugger' in sys.argv:
                pdb.set_trace()
            # here we actually run the program:
            return prg.main(argv)
        except:
            # look for an option in the prg.options object and in the config
            # dict print stack trace, if desired
            if getattr(prg.options, 'traceback', None) or getattr(prg.conf, 'config', {}).get('traceback', None) or \
               getattr(prg.options, 'post_mortem', None) or getattr(prg.conf, 'config', {}).get('post_mortem', None):
                traceback.print_exc(file=sys.stderr)
                # we could use http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52215
            # enter the debugger, if desired
            if getattr(prg.options, 'post_mortem', None) or getattr(prg.conf, 'config', {}).get('post_mortem', None):
                if sys.stdout.isatty() and not hasattr(sys, 'ps1'):
                    pdb.post_mortem(sys.exc_info()[2])
                else:
                    print('sys.stdout is not a tty. Not jumping into pdb.', file=sys.stderr)
            raise
    except oscerr.SignalInterrupt:
        print('killed!', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('interrupted!', file=sys.stderr)
        return 1
    except oscerr.UserAbort:
        print('aborted.', file=sys.stderr)
        return 1
    except oscerr.APIError as e:
        print('BuildService API error:', e.msg, file=sys.stderr)
        return 1
    except oscerr.LinkExpandError as e:
        print('Link "%s/%s" cannot be expanded:\n' % (e.prj, e.pac), e.msg, file=sys.stderr)
        print('Use "osc repairlink" to fix merge conflicts.\n', file=sys.stderr)
        return 1
    except oscerr.WorkingCopyWrongVersion as e:
        print(e, file=sys.stderr)
        return 1
    except oscerr.NoWorkingCopy as e:
        print(e, file=sys.stderr)
        if os.path.isdir('.git'):
            print("Current directory looks like git.", file=sys.stderr)
        if os.path.isdir('.hg'):
            print("Current directory looks like mercurial.", file=sys.stderr)
        if os.path.isdir('.svn'):
            print("Current directory looks like svn.", file=sys.stderr)
        if os.path.isdir('CVS'):
            print("Current directory looks like cvs.", file=sys.stderr)
        return 1
    except HTTPError as e:
        print('Server returned an error:', e, file=sys.stderr)
        if hasattr(e, 'osc_msg'):
            print(e.osc_msg, file=sys.stderr)

        try:
            body = e.read()
        except AttributeError:
            body = ''

        if getattr(prg.options, 'debug', None) or \
           getattr(prg.conf, 'config', {}).get('debug', None):
            print(e.hdrs, file=sys.stderr)
            print(body, file=sys.stderr)

        if e.code in [400, 403, 404, 500]:
            if '<summary>' in body:
                msg = body.split('<summary>')[1]
                msg = msg.split('</summary>')[0]
                print(msg, file=sys.stderr)
        if e.code >= 500 and e.code <= 599:
            print('\nRequest: %s' % e.filename)
            print('Headers:')
            for h, v in e.hdrs.items():
                if h != 'Set-Cookie':
                    print("%s: %s" % (h, v))

        return 1
    except BadStatusLine as e:
        print('Server returned an invalid response:', e, file=sys.stderr)
        print(e.line, file=sys.stderr)
        return 1
    except HTTPException as e:
        print(e, file=sys.stderr)
        return 1
    except URLError as e:
        print('Failed to reach a server:\n', e.reason, file=sys.stderr)
        return 1
    except IOError as e:
        # ignore broken pipe
        if e.errno != errno.EPIPE:
            raise
        return 1
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        print(e, file=sys.stderr)
        return 1
    except (oscerr.ConfigError, oscerr.NoConfigfile) as e:
        print(e.msg, file=sys.stderr)
        return 1
    except oscerr.OscIOError as e:
        print(e.msg, file=sys.stderr)
        if getattr(prg.options, 'debug', None) or \
           getattr(prg.conf, 'config', {}).get('debug', None):
            print(e.e, file=sys.stderr)
        return 1
    except (oscerr.WrongOptions, oscerr.WrongArgs) as e:
        print(e, file=sys.stderr)
        return 2
    except oscerr.ExtRuntimeError as e:
        print(e.file + ':', e.msg, file=sys.stderr)
        return 1
    except oscerr.ServiceRuntimeError as e:
        print(e.msg, file=sys.stderr)
    except oscerr.WorkingCopyOutdated as e:
        print(e, file=sys.stderr)
        return 1
    except (oscerr.PackageExists, oscerr.PackageMissing, oscerr.WorkingCopyInconsistent) as e:
        print(e.msg, file=sys.stderr)
        return 1
    except oscerr.PackageInternalError as e:
        print('a package internal error occured\n' \
            'please file a bug and attach your current package working copy ' \
            'and the following traceback to it:', file=sys.stderr)
        print(e.msg, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    except oscerr.PackageError as e:
        print(e.msg, file=sys.stderr)
        return 1
    except PackageError as e:
        print('%s:' % e.fname, e.msg, file=sys.stderr)
        return 1
    except RPMError as e:
        print(e, file=sys.stderr)
        return 1
    except SSLError as e:
        print("SSL Error:", e, file=sys.stderr)
        return 1
    except SSLVerificationError as e:
        print("Certificate Verification Error:", e, file=sys.stderr)
        return 1
    except NoSecureSSLError as e:
        print(e, file=sys.stderr)
        return 1
    except CpioError as e:
        print(e, file=sys.stderr)
        return 1
    except oscerr.OscBaseError as e:
        print('*** Error:', e, file=sys.stderr)
        return 1

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = build
# Copyright (C) 2006 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.

from __future__ import print_function

import os
import re
import sys
import shutil

try:
    from urllib.parse import urlsplit
    from urllib.request import URLError, HTTPError
except ImportError:
    #python 2.x
    from urlparse import urlsplit
    from urllib2 import URLError, HTTPError

from tempfile import NamedTemporaryFile, mkdtemp
from osc.fetch import *
from osc.core import get_buildinfo, store_read_apiurl, store_read_project, store_read_package, meta_exists, quote_plus, get_buildconfig, is_package_dir
from osc.core import get_binarylist, get_binary_file, run_external, raw_input
from osc.util import rpmquery, debquery, archquery
import osc.conf
from . import oscerr
import subprocess
try:
    from xml.etree import cElementTree as ET
except ImportError:
    import cElementTree as ET

from .conf import config, cookiejar

change_personality = {
            'i686':  'linux32',
            'i586':  'linux32',
            'i386':  'linux32',
            'ppc':   'powerpc32',
            's390':  's390',
            'sparc': 'linux32',
            'sparcv8': 'linux32',
        }

# FIXME: qemu_can_build should not be needed anymore since OBS 2.3
qemu_can_build = [ 'armv4l', 'armv5el', 'armv5l', 'armv6l', 'armv7l', 'armv6el', 'armv6hl', 'armv7el', 'armv7hl', 'armv8el',
                   'sh4', 'mips', 'mipsel',
                   'ppc', 'ppc64',
                   's390', 's390x',
                   'sparc64v', 'sparcv9v', 'sparcv9', 'sparcv8', 'sparc',
                   'hppa',
        ]

can_also_build = {
             'aarch64':['aarch64'], # only needed due to used heuristics in build parameter evaluation
             'armv6l' :[                                         'armv4l', 'armv5l', 'armv6l', 'armv5el', 'armv6el'                       ],
             'armv7l' :[                                         'armv4l', 'armv5l', 'armv6l', 'armv7l', 'armv5el', 'armv6el', 'armv7el'            ],
             'armv5el':[                                         'armv4l', 'armv5l', 'armv5el'                                  ], # not existing arch, just for compatibility
             'armv6el':[                                         'armv4l', 'armv5l', 'armv6l', 'armv5el', 'armv6el'                       ], # not existing arch, just for compatibility
             'armv6hl':[                                         'armv4l', 'armv5l', 'armv6l', 'armv5el', 'armv6el'                       ],
             'armv7el':[                                         'armv4l', 'armv5l', 'armv6l', 'armv7l', 'armv5el', 'armv6el', 'armv7el'            ], # not existing arch, just for compatibility
             'armv7hl':[                        'armv7hl'                                                             ], # not existing arch, just for compatibility
             'armv8el':[                                         'armv4l', 'armv5el', 'armv6el', 'armv7el', 'armv8el' ], # not existing arch, just for compatibility
             'armv8l' :[                                         'armv4l', 'armv5el', 'armv6el', 'armv7el', 'armv8el' ], # not existing arch, just for compatibility
             'armv5tel':[                                        'armv4l', 'armv5el',                                 'armv5tel' ], 
             's390x':  ['s390' ],
             'ppc64':  [                        'ppc', 'ppc64', 'ppc64p7', 'ppc64le' ],
             'ppc64le':[ 'ppc64le' ],
             'i586':   [                'i386' ],
             'i686':   [        'i586', 'i386' ],
             'x86_64': ['i686', 'i586', 'i386' ],
             'sparc64': ['sparc64v', 'sparcv9v', 'sparcv9', 'sparcv8', 'sparc'],
             'parisc': ['hppa'],
        }

# real arch of this machine
hostarch = os.uname()[4]
if hostarch == 'i686': # FIXME
    hostarch = 'i586'

if hostarch == 'parisc':
    hostarch = 'hppa'

class Buildinfo:
    """represent the contents of a buildinfo file"""

    def __init__(self, filename, apiurl, buildtype = 'spec', localpkgs = []):
        try:
            tree = ET.parse(filename)
        except:
            print('could not parse the buildinfo:', file=sys.stderr)
            print(open(filename).read(), file=sys.stderr)
            sys.exit(1)

        root = tree.getroot()

        self.apiurl = apiurl

        if root.find('error') != None:
            sys.stderr.write('buildinfo is broken... it says:\n')
            error = root.find('error').text
            sys.stderr.write(error + '\n')
            sys.exit(1)

        if not (apiurl.startswith('https://') or apiurl.startswith('http://')):
            raise URLError('invalid protocol for the apiurl: \'%s\'' % apiurl)

        self.buildtype = buildtype
        self.apiurl = apiurl

        # are we building .rpm or .deb?
        # XXX: shouldn't we deliver the type via the buildinfo?
        self.pacsuffix = 'rpm'
        if self.buildtype == 'dsc':
            self.pacsuffix = 'deb'
        if self.buildtype == 'arch':
            self.pacsuffix = 'arch'

        self.buildarch = root.find('arch').text
        if root.find('hostarch') != None:
            self.hostarch = root.find('hostarch').text
        else:
            self.hostarch = None
        if root.find('release') != None:
            self.release = root.find('release').text
        else:
            self.release = None
        self.downloadurl = root.get('downloadurl')
        self.debuginfo = 0
        if root.find('debuginfo') != None:
            try:
                self.debuginfo = int(root.find('debuginfo').text)
            except ValueError:
                pass

        self.deps = []
        self.projects = {}
        self.keys = []
        self.prjkeys = []
        self.pathes = []
        for node in root.findall('bdep'):
            p = Pac(node, self.buildarch, self.pacsuffix,
                    apiurl, localpkgs)
            if p.project:
                self.projects[p.project] = 1
            self.deps.append(p)
        for node in root.findall('path'):
            self.pathes.append(node.get('project')+"/"+node.get('repository'))

        self.vminstall_list = [ dep.name for dep in self.deps if dep.vminstall ]
        self.preinstall_list = [ dep.name for dep in self.deps if dep.preinstall ]
        self.runscripts_list = [ dep.name for dep in self.deps if dep.runscripts ]
        self.noinstall_list = [ dep.name for dep in self.deps if dep.noinstall ]
        self.installonly_list = [ dep.name for dep in self.deps if dep.installonly ]


    def has_dep(self, name):
        for i in self.deps:
            if i.name == name:
                return True
        return False

    def remove_dep(self, name):
        # we need to iterate over all deps because if this a
        # kiwi build the same package might appear multiple times
        # NOTE: do not loop and remove items, the second same one would not get catched
        self.deps = [i for i in self.deps if not i.name == name]


class Pac:
    """represent a package to be downloaded

    We build a map that's later used to fill our URL templates
    """
    def __init__(self, node, buildarch, pacsuffix, apiurl, localpkgs = []):

        self.mp = {}
        for i in ['binary', 'package',
                  'epoch', 'version', 'release',
                  'project', 'repository',
                  'preinstall', 'vminstall', 'noinstall', 'installonly', 'runscripts',
                 ]:
            self.mp[i] = node.get(i)

        self.mp['buildarch']  = buildarch
        self.mp['pacsuffix']  = pacsuffix

        self.mp['arch'] = node.get('arch') or self.mp['buildarch']
        self.mp['name'] = node.get('name') or self.mp['binary']

        # this is not the ideal place to check if the package is a localdep or not
        localdep = self.mp['name'] in localpkgs # and not self.mp['noinstall']
        if not localdep and not (node.get('project') and node.get('repository')):
            raise oscerr.APIError('incomplete information for package %s, may be caused by a broken project configuration.'
                                  % self.mp['name'] )

        if not localdep:
            self.mp['extproject'] = node.get('project').replace(':', ':/')
            self.mp['extrepository'] = node.get('repository').replace(':', ':/')
        self.mp['repopackage'] = node.get('package') or '_repository'
        self.mp['repoarch'] = node.get('repoarch') or self.mp['buildarch']

        if pacsuffix == 'deb' and not (self.mp['name'] and self.mp['arch'] and self.mp['version']):
            raise oscerr.APIError(
                "buildinfo for package %s/%s/%s is incomplete"
                    % (self.mp['name'], self.mp['arch'], self.mp['version']))

        self.mp['apiurl'] = apiurl

        if pacsuffix == 'deb':
            filename = debquery.DebQuery.filename(self.mp['name'], self.mp['epoch'], self.mp['version'], self.mp['release'], self.mp['arch'])
        elif pacsuffix == 'arch':
            filename = archquery.ArchQuery.filename(self.mp['name'], self.mp['epoch'], self.mp['version'], self.mp['release'], self.mp['arch'])
        else:
            filename = rpmquery.RpmQuery.filename(self.mp['name'], self.mp['epoch'], self.mp['version'], self.mp['release'], self.mp['arch'])

        self.mp['filename'] = node.get('binary') or filename
        if self.mp['repopackage'] == '_repository':
            self.mp['repofilename'] = self.mp['name']
        else:
            # OBS 2.3 puts binary into product bdeps (noinstall ones)
            self.mp['repofilename'] = self.mp['filename']

        # make the content of the dictionary accessible as class attributes
        self.__dict__.update(self.mp)


    def makeurls(self, cachedir, urllist):

        self.urllist = []

        # build up local URL
        # by using the urlgrabber with local urls, we basically build up a cache.
        # the cache has no validation, since the package servers don't support etags,
        # or if-modified-since, so the caching is simply name-based (on the assumption
        # that the filename is suitable as identifier)
        self.localdir = '%s/%s/%s/%s' % (cachedir, self.project, self.repository, self.arch)
        self.fullfilename = os.path.join(self.localdir, self.filename)
        self.url_local = 'file://%s' % self.fullfilename

        # first, add the local URL
        self.urllist.append(self.url_local)

        # remote URLs
        for url in urllist:
            self.urllist.append(url % self.mp)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s" % self.name



def get_built_files(pacdir, pactype):
    if pactype == 'rpm':
        b_built = subprocess.Popen(['find', os.path.join(pacdir, 'RPMS'),
                                    '-name', '*.rpm'],
                                   stdout=subprocess.PIPE).stdout.read().strip()
        s_built = subprocess.Popen(['find', os.path.join(pacdir, 'SRPMS'),
                                    '-name', '*.rpm'],
                                   stdout=subprocess.PIPE).stdout.read().strip()
    elif pactype == 'kiwi':
        b_built = subprocess.Popen(['find', os.path.join(pacdir, 'KIWI'),
                                    '-type', 'f'],
                                   stdout=subprocess.PIPE).stdout.read().strip()
    elif pactype == 'deb':
        b_built = subprocess.Popen(['find', os.path.join(pacdir, 'DEBS'),
                                    '-name', '*.deb'],
                                   stdout=subprocess.PIPE).stdout.read().strip()
        s_built = subprocess.Popen(['find', os.path.join(pacdir, 'SOURCES.DEB'),
                                    '-type', 'f'],
                                   stdout=subprocess.PIPE).stdout.read().strip()
    elif pactype == 'arch':
        b_built = subprocess.Popen(['find', os.path.join(pacdir, 'ARCHPKGS'),
                                    '-name', '*.pkg.tar*'],
                                   stdout=subprocess.PIPE).stdout.read().strip()
        s_built = ''
    else:
        print('WARNING: Unknown package type \'%s\'.' % pactype, file=sys.stderr)
        b_built = ''
        s_built = ''
    return s_built, b_built

def get_repo(path):
    """Walks up path looking for any repodata directories.

    @param path path to a directory
    @return str path to repository directory containing repodata directory
    """
    oldDirectory = None
    currentDirectory = os.path.abspath(path)
    repositoryDirectory = None

    # while there are still parent directories
    while currentDirectory != oldDirectory:
        children = os.listdir(currentDirectory)

        if "repodata" in children:
            repositoryDirectory = currentDirectory
            break

        # ascend
        oldDirectory = currentDirectory
        currentDirectory = os.path.abspath(os.path.join(oldDirectory,
                                                        os.pardir))

    return repositoryDirectory

def get_prefer_pkgs(dirs, wanted_arch, type):
    import glob
    from .util import repodata, packagequery, cpio
    paths = []
    repositories = []

    suffix = '*.rpm'
    if type == 'dsc':
        suffix = '*.deb'
    elif type == 'arch':
        suffix = '*.pkg.tar.xz'

    for dir in dirs:
        # check for repodata
        repository = get_repo(dir)
        if repository is None:
            paths += glob.glob(os.path.join(os.path.abspath(dir), suffix))
        else:
            repositories.append(repository)

    packageQueries = packagequery.PackageQueries(wanted_arch)

    for repository in repositories:
        repodataPackageQueries = repodata.queries(repository)

        for packageQuery in repodataPackageQueries:
            packageQueries.add(packageQuery)

    for path in paths:
        if path.endswith('src.rpm'):
            continue
        if path.find('-debuginfo-') > 0:
            continue
        packageQuery = packagequery.PackageQuery.query(path)
        packageQueries.add(packageQuery)

    prefer_pkgs = dict((name, packageQuery.path())
                       for name, packageQuery in packageQueries.items())

    depfile = create_deps(packageQueries.values())
    cpio = cpio.CpioWrite()
    cpio.add('deps', '\n'.join(depfile))
    return prefer_pkgs, cpio


def create_deps(pkgqs):
    """
    creates a list of requires/provides which corresponds to build's internal
    dependency file format
    """
    depfile = []
    for p in pkgqs:
        id = '%s.%s-0/0/0: ' % (p.name(), p.arch())
        depfile.append('R:%s%s' % (id, ' '.join(p.requires())))
        depfile.append('P:%s%s' % (id, ' '.join(p.provides())))
    return depfile


trustprompt = """Would you like to ...
0 - quit (default)
1 - always trust packages from '%(project)s'
2 - trust packages just this time
? """
def check_trusted_projects(apiurl, projects):
    trusted = config['api_host_options'][apiurl]['trusted_prj']
    tlen = len(trusted)
    for prj in projects:
        if not prj in trusted:
            print("\nThe build root needs packages from project '%s'." % prj)
            print("Note that malicious packages can compromise the build result or even your system.")
            r = raw_input(trustprompt % { 'project':prj })
            if r == '1':
                print("adding '%s' to ~/.oscrc: ['%s']['trusted_prj']" % (prj, apiurl))
                trusted.append(prj)
            elif r != '2':
                print("Well, good good bye then :-)")
                raise oscerr.UserAbort()

    if tlen != len(trusted):
        config['api_host_options'][apiurl]['trusted_prj'] = trusted
        conf.config_set_option(apiurl, 'trusted_prj', ' '.join(trusted))

def main(apiurl, opts, argv):

    repo = argv[0]
    arch = argv[1]
    build_descr = argv[2]
    xp = []
    build_root = None
    cache_dir  = None
    build_uid = ''
    vm_type = config['build-type']

    build_descr = os.path.abspath(build_descr)
    build_type = os.path.splitext(build_descr)[1][1:]
    if os.path.basename(build_descr) == 'PKGBUILD':
        build_type = 'arch'
    if build_type not in ['spec', 'dsc', 'kiwi', 'arch']:
        raise oscerr.WrongArgs(
                'Unknown build type: \'%s\'. Build description should end in .spec, .dsc or .kiwi.' \
                        % build_type)
    if not os.path.isfile(build_descr):
        raise oscerr.WrongArgs('Error: build description file named \'%s\' does not exist.' % build_descr)

    buildargs = []
    if not opts.userootforbuild:
        buildargs.append('--norootforbuild')
    if opts.clean:
        buildargs.append('--clean')
    if opts.noinit:
        buildargs.append('--noinit')
    if opts.nochecks:
        buildargs.append('--no-checks')
    if not opts.no_changelog:
        buildargs.append('--changelog')
    if opts.root:
        build_root = opts.root
    if opts.target:
        buildargs.append('--target=%s' % opts.target)
    if opts.jobs:
        buildargs.append('--jobs=%s' % opts.jobs)
    elif config['build-jobs'] > 1:
        buildargs.append('--jobs=%s' % config['build-jobs'])
    if opts.icecream or config['icecream'] != '0':
        if opts.icecream:
            num = opts.icecream
        else:
            num = config['icecream']

        if int(num) > 0:
            buildargs.append('--icecream=%s' % num)
            xp.append('icecream')
            xp.append('gcc-c++')
    if opts.ccache:
        buildargs.append('--ccache')
        xp.append('ccache')
    if opts.linksources:
        buildargs.append('--linksources')
    if opts.baselibs:
        buildargs.append('--baselibs')
    if opts.debuginfo:
        buildargs.append('--debug')
    if opts._with:
        for o in opts._with:
            buildargs.append('--with=%s' % o)
    if opts.without:
        for o in opts.without:
            buildargs.append('--without=%s' % o)
    if opts.define:
        for o in opts.define:
            buildargs.append('--define=%s' % o)
    if config['build-uid']:
        build_uid = config['build-uid']
    if opts.build_uid:
        build_uid = opts.build_uid
    if build_uid:
        buildidre = re.compile('^[0-9]{1,5}:[0-9]{1,5}$')
        if build_uid == 'caller':
            buildargs.append('--uid=%s:%s' % (os.getuid(), os.getgid()))
        elif buildidre.match(build_uid):
            buildargs.append('--uid=%s' % build_uid)
        else:
            print('Error: build-uid arg must be 2 colon separated numerics: "uid:gid" or "caller"', file=sys.stderr)
            return 1
    if opts.vm_type:
        vm_type = opts.vm_type
    if opts.alternative_project:
        prj = opts.alternative_project
        pac = '_repository'
    else:
        prj = store_read_project(os.curdir)
        if opts.local_package:
            pac = '_repository'
        else:
            pac = store_read_package(os.curdir)
    if opts.shell:
        buildargs.append("--shell")

    # make it possible to override configuration of the rc file
    for var in ['OSC_PACKAGECACHEDIR', 'OSC_SU_WRAPPER', 'OSC_BUILD_ROOT']:
        val = os.getenv(var)
        if val:
            if var.startswith('OSC_'): var = var[4:]
            var = var.lower().replace('_', '-')
            if var in config:
                print('Overriding config value for %s=\'%s\' with \'%s\'' % (var, config[var], val))
            config[var] = val

    pacname = pac
    if pacname == '_repository':
        if not opts.local_package:
            try:
                pacname = store_read_package(os.curdir)
            except oscerr.NoWorkingCopy:
                opts.local_package = True
        if opts.local_package:
            pacname = os.path.splitext(build_descr)[0]
    apihost = urlsplit(apiurl)[1]
    if not build_root:
        try:
            build_root = config['build-root'] % {'repo': repo, 'arch': arch,
                         'project': prj, 'package': pacname, 'apihost': apihost}
        except:
            build_root = config['build-root']

    cache_dir = config['packagecachedir'] % {'apihost': apihost}

    extra_pkgs = []
    if not opts.extra_pkgs:
        extra_pkgs = config['extra-pkgs']
    elif opts.extra_pkgs != ['']:
        extra_pkgs = opts.extra_pkgs

    if xp:
        extra_pkgs += xp

    prefer_pkgs = {}
    build_descr_data = open(build_descr).read()

    # XXX: dirty hack but there's no api to provide custom defines
    if opts.without:
        s = ''
        for i in opts.without:
            s += "%%define _without_%s 1\n" % i
        build_descr_data = s + build_descr_data
    if opts._with:
        s = ''
        for i in opts._with:
            s += "%%define _with_%s 1\n" % i
        build_descr_data = s + build_descr_data
    if opts.define:
        s = ''
        for i in opts.define:
            s += "%%define %s\n" % i
        build_descr_data = s + build_descr_data

    if opts.prefer_pkgs:
        print('Scanning the following dirs for local packages: %s' % ', '.join(opts.prefer_pkgs))
        prefer_pkgs, cpio = get_prefer_pkgs(opts.prefer_pkgs, arch, build_type)
        cpio.add(os.path.basename(build_descr), build_descr_data)
        build_descr_data = cpio.get()

    # special handling for overlay and rsync-src/dest
    specialcmdopts = []
    if opts.rsyncsrc or opts.rsyncdest :
        if not opts.rsyncsrc or not opts.rsyncdest:
            raise oscerr.WrongOptions('When using --rsync-{src,dest} both parameters have to be specified.')
        myrsyncsrc = os.path.abspath(os.path.expanduser(os.path.expandvars(opts.rsyncsrc)))
        if not os.path.isdir(myrsyncsrc):
            raise oscerr.WrongOptions('--rsync-src %s is no valid directory!' % opts.rsyncsrc)
        # can't check destination - its in the target chroot ;) - but we can check for sanity
        myrsyncdest = os.path.expandvars(opts.rsyncdest)
        if not os.path.isabs(myrsyncdest):
            raise oscerr.WrongOptions('--rsync-dest %s is no absolute path (starting with \'/\')!' % opts.rsyncdest)
        specialcmdopts = ['--rsync-src='+myrsyncsrc, '--rsync-dest='+myrsyncdest]
    if opts.overlay:
        myoverlay = os.path.abspath(os.path.expanduser(os.path.expandvars(opts.overlay)))
        if not os.path.isdir(myoverlay):
            raise oscerr.WrongOptions('--overlay %s is no valid directory!' % opts.overlay)
        specialcmdopts += ['--overlay='+myoverlay]

    bi_file = None
    bc_file = None
    bi_filename = '_buildinfo-%s-%s.xml' % (repo, arch)
    bc_filename = '_buildconfig-%s-%s' % (repo, arch)
    if is_package_dir('.') and os.access(osc.core.store, os.W_OK):
        bi_filename = os.path.join(os.getcwd(), osc.core.store, bi_filename)
        bc_filename = os.path.join(os.getcwd(), osc.core.store, bc_filename)
    elif not os.access('.', os.W_OK):
        bi_file = NamedTemporaryFile(prefix=bi_filename)
        bi_filename = bi_file.name
        bc_file = NamedTemporaryFile(prefix=bc_filename)
        bc_filename = bc_file.name
    else:
        bi_filename = os.path.abspath(bi_filename)
        bc_filename = os.path.abspath(bc_filename)

    try:
        if opts.noinit:
            if not os.path.isfile(bi_filename):
                raise oscerr.WrongOptions('--noinit is not possible, no local buildinfo file')
            print('Use local \'%s\' file as buildinfo' % bi_filename)
            if not os.path.isfile(bc_filename):
                raise oscerr.WrongOptions('--noinit is not possible, no local buildconfig file')
            print('Use local \'%s\' file as buildconfig' % bc_filename)
        elif opts.offline:
            if not os.path.isfile(bi_filename):
                raise oscerr.WrongOptions('--offline is not possible, no local buildinfo file')
            print('Use local \'%s\' file as buildinfo' % bi_filename)
            if not os.path.isfile(bc_filename):
                raise oscerr.WrongOptions('--offline is not possible, no local buildconfig file')
        else:
            print('Getting buildinfo from server and store to %s' % bi_filename)
            bi_text = ''.join(get_buildinfo(apiurl,
                                            prj,
                                            pac,
                                            repo,
                                            arch,
                                            specfile=build_descr_data,
                                            addlist=extra_pkgs))
            if not bi_file:
                bi_file = open(bi_filename, 'w')
            # maybe we should check for errors before saving the file
            bi_file.write(bi_text)
            bi_file.flush()
            print('Getting buildconfig from server and store to %s' % bc_filename)
            bc = get_buildconfig(apiurl, prj, repo)
            if not bc_file:
                bc_file = open(bc_filename, 'w')
            bc_file.write(bc)
            bc_file.flush()
    except HTTPError as e:
        if e.code == 404:
            # check what caused the 404
            if meta_exists(metatype='prj', path_args=(quote_plus(prj), ),
                           template_args=None, create_new=False, apiurl=apiurl):
                pkg_meta_e = None
                try:
                    # take care, not to run into double trouble.
                    pkg_meta_e = meta_exists(metatype='pkg', path_args=(quote_plus(prj), 
                                        quote_plus(pac)), template_args=None, create_new=False, 
                                        apiurl=apiurl)
                except:
                    pass

                if pkg_meta_e:
                    print('ERROR: Either wrong repo/arch as parameter or a parse error of .spec/.dsc/.kiwi file due to syntax error', file=sys.stderr)
                else:
                    print('The package \'%s\' does not exists - please ' \
                                        'rerun with \'--local-package\'' % pac, file=sys.stderr)
            else:
                print('The project \'%s\' does not exists - please ' \
                                    'rerun with \'--alternative-project <alternative_project>\'' % prj, file=sys.stderr)
            sys.exit(1)
        else:
            raise

    bi = Buildinfo(bi_filename, apiurl, build_type, list(prefer_pkgs.keys()))

    if bi.debuginfo and not (opts.disable_debuginfo or '--debug' in buildargs):
        buildargs.append('--debug')

    if opts.release:
        bi.release = opts.release

    if bi.release:
        buildargs.append('--release=%s' % bi.release)

    # real arch of this machine
    # vs.
    # arch we are supposed to build for
    if bi.hostarch != None:
        if hostarch != bi.hostarch and not bi.hostarch in can_also_build.get(hostarch, []):
            print('Error: hostarch \'%s\' is required.' % (bi.hostarch), file=sys.stderr)
            return 1
    elif hostarch != bi.buildarch:
        if not bi.buildarch in can_also_build.get(hostarch, []):
            # OBSOLETE: qemu_can_build should not be needed anymore since OBS 2.3
            if vm_type != "emulator" and not bi.buildarch in qemu_can_build:
                print('Error: hostarch \'%s\' cannot build \'%s\'.' % (hostarch, bi.buildarch), file=sys.stderr)
                return 1
            print('WARNING: It is guessed to build on hostarch \'%s\' for \'%s\' via QEMU.' % (hostarch, bi.buildarch), file=sys.stderr)

    rpmlist_prefers = []
    if prefer_pkgs:
        print('Evaluating preferred packages')
        for name, path in prefer_pkgs.items():
            if bi.has_dep(name):
                # We remove a preferred package from the buildinfo, so that the
                # fetcher doesn't take care about them.
                # Instead, we put it in a list which is appended to the rpmlist later.
                # At the same time, this will make sure that these packages are
                # not verified.
                bi.remove_dep(name)
                rpmlist_prefers.append((name, path))
                print(' - %s (%s)' % (name, path))

    print('Updating cache of required packages')

    urllist = []
    if not opts.download_api_only:
        # transform 'url1, url2, url3' form into a list
        if 'urllist' in config:
            if isinstance(config['urllist'], str):
                re_clist = re.compile('[, ]+')
                urllist = [ i.strip() for i in re_clist.split(config['urllist'].strip()) ]
            else:
                urllist = config['urllist']

        # OBS 1.5 and before has no downloadurl defined in buildinfo
        if bi.downloadurl:
            urllist.append(bi.downloadurl + '/%(extproject)s/%(extrepository)s/%(arch)s/%(filename)s')
    if opts.disable_cpio_bulk_download:
        urllist.append( '%(apiurl)s/build/%(project)s/%(repository)s/%(repoarch)s/%(repopackage)s/%(repofilename)s' )

    fetcher = Fetcher(cache_dir,
                      urllist = urllist,
                      api_host_options = config['api_host_options'],
                      offline = opts.noinit or opts.offline,
                      http_debug = config['http_debug'],
                      enable_cpio = not opts.disable_cpio_bulk_download,
                      cookiejar=cookiejar)

    # implicitly trust the project we are building for
    check_trusted_projects(apiurl, [ i for i in bi.projects.keys() if not i == prj ])

    # now update the package cache
    fetcher.run(bi)

    old_pkg_dir = None
    if opts.oldpackages:
        old_pkg_dir = opts.oldpackages
        if not old_pkg_dir.startswith('/') and not opts.offline:
            data = [ prj, pacname, repo, arch]
            if old_pkg_dir == '_link':
                p = osc.core.findpacs(os.curdir)[0]
                if not p.islink():
                    raise oscerr.WrongOptions('package is not a link')
                data[0] = p.linkinfo.project
                data[1] = p.linkinfo.package
                repos = osc.core.get_repositories_of_project(apiurl, data[0])
                # hack for links to e.g. Factory
                if not data[2] in repos and 'standard' in repos:
                    data[2] = 'standard'
            elif old_pkg_dir != '' and old_pkg_dir != '_self':
                a = old_pkg_dir.split('/')
                for i in range(0, len(a)):
                    data[i] = a[i]

            destdir = os.path.join(cache_dir, data[0], data[2], data[3])
            old_pkg_dir = None
            try:
                print("Downloading previous build from %s ..." % '/'.join(data))
                binaries = get_binarylist(apiurl, data[0], data[2], data[3], package=data[1], verbose=True)
            except Exception as e:
                print("Error: failed to get binaries: %s" % str(e))
                binaries = []

            if binaries:
                class mytmpdir:
                    """ temporary directory that removes itself"""
                    def __init__(self, *args, **kwargs):
                        self.name = mkdtemp(*args, **kwargs)
                    def cleanup(self):
                        shutil.rmtree(self.name)
                    def __del__(self):
                        self.cleanup()
                    def __exit__(self):
                        self.cleanup()
                    def __str__(self):
                        return self.name

                old_pkg_dir = mytmpdir(prefix='.build.oldpackages', dir=os.path.abspath(os.curdir))
                if not os.path.exists(destdir):
                    os.makedirs(destdir)
            for i in binaries:
                fname = os.path.join(destdir, i.name)
                os.symlink(fname, os.path.join(str(old_pkg_dir), i.name))
                if os.path.exists(fname):
                    st = os.stat(fname)
                    if st.st_mtime == i.mtime and st.st_size == i.size:
                        continue
                get_binary_file(apiurl,
                                data[0],
                                data[2], data[3],
                                i.name,
                                package = data[1],
                                target_filename = fname,
                                target_mtime = i.mtime,
                                progress_meter = True)

        if old_pkg_dir != None:
            buildargs.append('--oldpackages=%s' % old_pkg_dir)

    # Make packages from buildinfo available as repos for kiwi
    if build_type == 'kiwi':
        if os.path.exists('repos'):
            shutil.rmtree('repos')
        os.mkdir('repos')
        for i in bi.deps:
            if not i.extproject:
                # remove
                bi.deps.remove(i)
                continue
            # project
            pdir = str(i.extproject).replace(':/', ':')
            # repo
            rdir = str(i.extrepository).replace(':/', ':')
            # arch
            adir = i.repoarch
            # project/repo
            prdir = "repos/"+pdir+"/"+rdir
            # project/repo/arch
            pradir = prdir+"/"+adir
            # source fullfilename
            sffn = i.fullfilename
            filename = sffn.split("/")[-1]
            # target fullfilename
            tffn = pradir+"/"+filename
            if not os.path.exists(os.path.join(pradir)):
                os.makedirs(os.path.join(pradir))
            if not os.path.exists(tffn):
                print("Using package: "+sffn)
                if opts.linksources:
                    os.link(sffn, tffn)
                else:
                    os.symlink(sffn, tffn)
            if prefer_pkgs:
                for name, path in prefer_pkgs.items():
                    if name == filename:
                        print("Using prefered package: " + path + "/" + filename)
                        os.unlink(tffn)
                        if opts.linksources:
                            os.link(path + "/" + filename, tffn)
                        else:
                            os.symlink(path + "/" + filename, tffn)
        # Is a obsrepositories tag used?
        try:
            tree = ET.parse(build_descr)
        except:
            print('could not parse the kiwi file:', file=sys.stderr)
            print(open(build_descr).read(), file=sys.stderr)
            sys.exit(1)
        root = tree.getroot()
        # product
        for xml in root.findall('instsource'):
            if xml.find('instrepo').find('source').get('path') == 'obsrepositories:/':
                print("obsrepositories:/ for product builds is not yet supported in osc!")
                sys.exit(1)
        # appliance
        expand_obsrepos=None
        for xml in root.findall('repository'):
            if xml.find('source').get('path') == 'obsrepositories:/':
                expand_obsrepos=True
        if expand_obsrepos:
          buildargs.append('--kiwi-parameter')
          buildargs.append('--ignore-repos')
          for xml in root.findall('repository'):
              if xml.find('source').get('path') == 'obsrepositories:/':
                  for path in bi.pathes:
                      if not os.path.isdir("repos/"+path):
                          continue
                      buildargs.append('--kiwi-parameter')
                      buildargs.append('--add-repo')
                      buildargs.append('--kiwi-parameter')
                      buildargs.append("repos/"+path)
                      buildargs.append('--kiwi-parameter')
                      buildargs.append('--add-repotype')
                      buildargs.append('--kiwi-parameter')
                      buildargs.append('rpm-md')
                      if xml.get('priority'):
                          buildargs.append('--kiwi-parameter')
                          buildargs.append('--add-repoprio='+xml.get('priority'))
              else:
                   m = re.match(r"obs://[^/]+/([^/]+)/(\S+)", xml.find('source').get('path'))
                   if not m:
                       # short path without obs instance name
                       m = re.match(r"obs://([^/]+)/(.+)", xml.find('source').get('path'))
                   project=m.group(1).replace(":",":/")
                   repo=m.group(2)
                   buildargs.append('--kiwi-parameter')
                   buildargs.append('--add-repo')
                   buildargs.append('--kiwi-parameter')
                   buildargs.append("repos/"+project+"/"+repo)
                   buildargs.append('--kiwi-parameter')
                   buildargs.append('--add-repotype')
                   buildargs.append('--kiwi-parameter')
                   buildargs.append('rpm-md')
                   if xml.get('priority'):
                       buildargs.append('--kiwi-parameter')
                       buildargs.append('--add-repopriority='+xml.get('priority'))

    if vm_type == "xen" or vm_type == "kvm" or vm_type == "lxc":
        print('Skipping verification of package signatures due to secure VM build')
    elif bi.pacsuffix == 'rpm':
        if opts.no_verify:
            print('Skipping verification of package signatures')
        else:
            print('Verifying integrity of cached packages')
            verify_pacs(bi)
    elif bi.pacsuffix == 'deb':
        if opts.no_verify or opts.noinit:
            print('Skipping verification of package signatures')
        else:
            print('WARNING: deb packages get not verified, they can compromise your system !')
    else:
        print('WARNING: unknown packages get not verified, they can compromise your system !')

    print('Writing build configuration')

    if build_type == 'kiwi':
        rpmlist = [ '%s %s\n' % (i.name, i.fullfilename) for i in bi.deps if not i.noinstall ]
    else:
        rpmlist = [ '%s %s\n' % (i.name, i.fullfilename) for i in bi.deps ]
    rpmlist += [ '%s %s\n' % (i[0], i[1]) for i in rpmlist_prefers ]

    rpmlist.append('preinstall: ' + ' '.join(bi.preinstall_list) + '\n')
    rpmlist.append('vminstall: ' + ' '.join(bi.vminstall_list) + '\n')
    rpmlist.append('runscripts: ' + ' '.join(bi.runscripts_list) + '\n')
    if build_type != 'kiwi' and bi.noinstall_list:
        rpmlist.append('noinstall: ' + ' '.join(bi.noinstall_list) + '\n')
    if build_type != 'kiwi' and bi.installonly_list:
        rpmlist.append('installonly: ' + ' '.join(bi.installonly_list) + '\n')

    rpmlist_file = NamedTemporaryFile(prefix='rpmlist.')
    rpmlist_filename = rpmlist_file.name
    rpmlist_file.writelines(rpmlist)
    rpmlist_file.flush()

    subst = { 'repo': repo, 'arch': arch, 'project' : prj, 'package' : pacname }
    vm_options = []
    # XXX check if build-device present
    my_build_device = ''
    if config['build-device']:
        my_build_device = config['build-device'] % subst
    else:
        # obs worker uses /root here but that collides with the
        # /root directory if the build root was used without vm
        # before
        my_build_device = build_root + '/img'

    need_root = True
    if vm_type:
        if config['build-swap']:
            my_build_swap = config['build-swap'] % subst
        else:
            my_build_swap = build_root + '/swap'

        vm_options = [ '--vm-type=%s' % vm_type ]
        if vm_type != 'lxc' and vm_type != 'emulator':
            vm_options += [ '--vm-disk=' + my_build_device ]
            vm_options += [ '--vm-swap=' + my_build_swap ]
            vm_options += [ '--logfile=%s/.build.log' % build_root ]
            if vm_type == 'kvm':
                if os.access(build_root, os.W_OK) and os.access('/dev/kvm', os.W_OK):
                    # so let's hope there's also an fstab entry
                    need_root = False
            build_root += '/.mount'

        if config['build-memory']:
            vm_options += [ '--memory=' + config['build-memory'] ]
        if config['build-vmdisk-rootsize']:
            vm_options += [ '--vmdisk-rootsize=' + config['build-vmdisk-rootsize'] ]
        if config['build-vmdisk-swapsize']:
            vm_options += [ '--vmdisk-swapsize=' + config['build-vmdisk-swapsize'] ]
        if config['build-vmdisk-filesystem']:
            vm_options += [ '--vmdisk-filesystem=' + config['build-vmdisk-filesystem'] ]


    if opts.preload:
        print("Preload done for selected repo/arch.")
        sys.exit(0)

    print('Running build')
    cmd = [ config['build-cmd'], '--root='+build_root,
                    '--rpmlist='+rpmlist_filename,
                    '--dist='+bc_filename,
                    '--arch='+bi.buildarch ]
    cmd += specialcmdopts + vm_options + buildargs
    cmd += [ build_descr ]

    if need_root:
        sucmd = config['su-wrapper'].split()
        if sucmd[0] == 'su':
            if sucmd[-1] == '-c':
                sucmd.pop()
            cmd = sucmd + ['-s', cmd[0], 'root', '--' ] + cmd[1:]
        else:
            cmd = sucmd + cmd

    # change personality, if needed
    if hostarch != bi.buildarch and bi.buildarch in change_personality:
        cmd = [ change_personality[bi.buildarch] ] + cmd

    try:
        rc = run_external(cmd[0], *cmd[1:])
        if rc:
            print()
            print('The buildroot was:', build_root)
            sys.exit(rc)
    except KeyboardInterrupt as i:
        print("keyboard interrupt, killing build ...")
        cmd.append('--kill')
        run_external(cmd[0], *cmd[1:])
        raise i

    pacdir = os.path.join(build_root, '.build.packages')
    if os.path.islink(pacdir):
        pacdir = os.readlink(pacdir)
        pacdir = os.path.join(build_root, pacdir)

    if os.path.exists(pacdir):
        (s_built, b_built) = get_built_files(pacdir, bi.pacsuffix)

        print()
        if s_built: print(s_built)
        print()
        print(b_built)

        if opts.keep_pkgs:
            for i in b_built.splitlines() + s_built.splitlines():
                shutil.copy2(i, os.path.join(opts.keep_pkgs, os.path.basename(i)))

    if bi_file:
        bi_file.close()
    if bc_file:
        bc_file.close()
    rpmlist_file.close()

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = checker
from __future__ import print_function

from tempfile import mkdtemp
import os
from shutil import rmtree
import rpm
import base64

class KeyError(Exception):
    def __init__(self, key, *args):
        Exception.__init__(self)
        self.args = args
        self.key = key
    def __str__(self):
        return ''+self.key+' :'+' '.join(self.args)

class Checker:
    def __init__(self):
        self.dbdir = mkdtemp(prefix='oscrpmdb')
        self.imported = {}
        rpm.addMacro('_dbpath', self.dbdir)
        self.ts = rpm.TransactionSet()
        self.ts.initDB()
        self.ts.openDB()
        self.ts.setVSFlags(0)
        #self.ts.Debug(1)

    def readkeys(self, keys=[]):
        rpm.addMacro('_dbpath', self.dbdir)
        for key in keys:
            try:
                self.readkey(key)
            except KeyError as e:
                print(e)

        if not len(self.imported):
            raise KeyError('', "no key imported")

        rpm.delMacro("_dbpath")

# python is an idiot
#    def __del__(self):
#        self.cleanup()

    def cleanup(self):
        self.ts.closeDB()
        rmtree(self.dbdir)

    def readkey(self, file):
        if file in self.imported:
            return

        fd = open(file, "r")
        line = fd.readline()
        if line and line[0:14] == "-----BEGIN PGP":
            line = fd.readline()
            while line and line != "\n":
                line = fd.readline()
            if not line:
                raise KeyError(file, "not a pgp public key")
        else:
            raise KeyError(file, "not a pgp public key")

        key = ''
        line = fd.readline()
        crc = None
        while line:
            if line[0:12] == "-----END PGP":
                break
            line = line.rstrip()
            if (line[0] == '='):
                crc = line[1:]
                line = fd.readline()
                break
            else:
                key += line
                line = fd.readline()
        fd.close()
        if not line or line[0:12] != "-----END PGP":
            raise KeyError(file, "not a pgp public key")

        # TODO: compute and compare CRC, see RFC 2440

        bkey = base64.b64decode(key)

        r = self.ts.pgpImportPubkey(bkey)
        if r != 0:
            raise KeyError(file, "failed to import pubkey")
        self.imported[file] = 1

    def check(self, pkg):
        # avoid errors on non rpm
        if pkg[-4:] != '.rpm': 
            return
        fd = None
        try:
            fd = os.open(pkg, os.O_RDONLY)
            hdr = self.ts.hdrFromFdno(fd)
        finally:
            if fd is not None:
                os.close(fd)

if __name__ == "__main__":
    import sys
    keyfiles = []
    pkgs = []
    for arg in sys.argv[1:]:
        if arg[-4:] == '.rpm':
            pkgs.append(arg)
        else:
            keyfiles.append(arg)

    checker = Checker()
    try:
        checker.readkeys(keyfiles)
        for pkg in pkgs:
            checker.check(pkg)
    except Exception as e:
        checker.cleanup()
        raise e

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = cmdln
# Copyright (c) 2002-2005 ActiveState Corp.
# License: MIT (see LICENSE.txt for license details)
# Author:  Trent Mick (TrentM@ActiveState.com)
# Home:    http://trentm.com/projects/cmdln/

from __future__ import print_function

"""An improvement on Python's standard cmd.py module.

As with cmd.py, this module provides "a simple framework for writing
line-oriented command intepreters."  This module provides a 'RawCmdln'
class that fixes some design flaws in cmd.Cmd, making it more scalable
and nicer to use for good 'cvs'- or 'svn'-style command line interfaces
or simple shells.  And it provides a 'Cmdln' class that add
optparse-based option processing. Basically you use it like this:

    import cmdln

    class MySVN(cmdln.Cmdln):
        name = "svn"

        @cmdln.alias('stat', 'st')
        @cmdln.option('-v', '--verbose', action='store_true'
                      help='print verbose information')
        def do_status(self, subcmd, opts, *paths):
            print "handle 'svn status' command"

        #...

    if __name__ == "__main__":
        shell = MySVN()
        retval = shell.main()
        sys.exit(retval)

See the README.txt or <http://trentm.com/projects/cmdln/> for more
details.
"""

__revision__ = "$Id: cmdln.py 1666 2007-05-09 03:13:03Z trentm $"
__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
import re
import cmd
import optparse
import sys
from pprint import pprint
from datetime import date

# this is python 2.x style
def introspect_handler_2(handler):
    # Extract the introspection bits we need.
    func = handler.im_func
    if func.func_defaults:
        func_defaults = func.func_defaults
    else:
        func_defaults = []
    return \
        func_defaults,   \
        func.func_code.co_argcount, \
        func.func_code.co_varnames, \
        func.func_code.co_flags,    \
        func

def introspect_handler_3(handler):
    defaults = handler.__defaults__
    if not defaults:
        defaults = []
    else:
        defaults = list(handler.__defaults__)
    return \
        defaults,   \
        handler.__code__.co_argcount, \
        handler.__code__.co_varnames, \
        handler.__code__.co_flags,    \
        handler.__func__

if sys.version_info[0] == 2:
    introspect_handler = introspect_handler_2
    bytes = lambda x, *args: x
else:
    introspect_handler = introspect_handler_3


#---- globals

LOOP_ALWAYS, LOOP_NEVER, LOOP_IF_EMPTY = range(3)

# An unspecified optional argument when None is a meaningful value.
_NOT_SPECIFIED = ("Not", "Specified")

# Pattern to match a TypeError message from a call that
# failed because of incorrect number of arguments (see
# Python/getargs.c).
_INCORRECT_NUM_ARGS_RE = re.compile(
    r"(takes [\w ]+ )(\d+)( arguments? \()(\d+)( given\))")

# Static bits of man page
MAN_HEADER = r""".TH %(ucname)s "1" "%(date)s" "%(name)s %(version)s" "User Commands"
.SH NAME
%(name)s \- Program to do useful things.
.SH SYNOPSIS
.B %(name)s
[\fIGLOBALOPTS\fR] \fISUBCOMMAND \fR[\fIOPTS\fR] [\fIARGS\fR...]
.br
.B %(name)s
\fIhelp SUBCOMMAND\fR
.SH DESCRIPTION
"""
MAN_COMMANDS_HEADER = r"""
.SS COMMANDS
"""
MAN_OPTIONS_HEADER = r"""
.SS GLOBAL OPTIONS
"""
MAN_FOOTER = r"""
.SH AUTHOR
This man page is automatically generated.
"""

#---- exceptions

class CmdlnError(Exception):
    """A cmdln.py usage error."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class CmdlnUserError(Exception):
    """An error by a user of a cmdln-based tool/shell."""
    pass



#---- public methods and classes

def alias(*aliases):
    """Decorator to add aliases for Cmdln.do_* command handlers.

    Example:
        class MyShell(cmdln.Cmdln):
            @cmdln.alias("!", "sh")
            def do_shell(self, argv):
                #...implement 'shell' command
    """
    def decorate(f):
        if not hasattr(f, "aliases"):
            f.aliases = []
        f.aliases += aliases
        return f
    return decorate

MAN_REPLACES = [
    (re.compile(r'(^|[ \t\[\'\|])--([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\-\2\-\3\-\4\-\5\-\6'),
    (re.compile(r'(^|[ \t\[\'\|])--([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\-\2\-\3\-\4\-\5'),
    (re.compile(r'(^|[ \t\[\'\|])--([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\-\2\-\3\-\4'),
    (re.compile(r'(^|[ \t\[\'\|])-([^/ \t/,-]*)-([^/ \t/,-]*)-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\2\-\3\-\4'),
    (re.compile(r'(^|[ \t\[\'\|])--([^/ \t/,-]*)-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\-\2\-\3'),
    (re.compile(r'(^|[ \t\[\'\|])-([^/ \t/,-]*)-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\2\-\3'),
    (re.compile(r'(^|[ \t\[\'\|])--([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\-\2'),
    (re.compile(r'(^|[ \t\[\'\|])-([^/ \t/,\|-]*)(?=$|[ \t=\]\'/,\|])'), r'\1\-\2'),
    (re.compile(r"^'"), r" '"),
    ]

def man_escape(text):
    '''
    Escapes text to be included in man page.

    For now it only escapes dashes in command line options.
    '''
    for repl in MAN_REPLACES:
        text = repl[0].sub(repl[1], text)
    return text

class RawCmdln(cmd.Cmd):
    """An improved (on cmd.Cmd) framework for building multi-subcommand
    scripts (think "svn" & "cvs") and simple shells (think "pdb" and
    "gdb").

    A simple example:

        import cmdln

        class MySVN(cmdln.RawCmdln):
            name = "svn"

            @cmdln.aliases('stat', 'st')
            def do_status(self, argv):
                print "handle 'svn status' command"

        if __name__ == "__main__":
            shell = MySVN()
            retval = shell.main()
            sys.exit(retval)

    See <http://trentm.com/projects/cmdln> for more information.
    """
    name = None      # if unset, defaults basename(sys.argv[0])
    prompt = None    # if unset, defaults to self.name+"> "
    version = None   # if set, default top-level options include --version

    # Default messages for some 'help' command error cases.
    # They are interpolated with one arg: the command.
    nohelp = "no help on '%s'"
    unknowncmd = "unknown command: '%s'"

    helpindent = '' # string with which to indent help output

    # Default man page parts, please change them in subclass
    man_header = MAN_HEADER
    man_commands_header = MAN_COMMANDS_HEADER
    man_options_header = MAN_OPTIONS_HEADER
    man_footer = MAN_FOOTER

    def __init__(self, completekey='tab',
                 stdin=None, stdout=None, stderr=None):
        """Cmdln(completekey='tab', stdin=None, stdout=None, stderr=None)

        The optional argument 'completekey' is the readline name of a
        completion key; it defaults to the Tab key. If completekey is
        not None and the readline module is available, command completion
        is done automatically.

        The optional arguments 'stdin', 'stdout' and 'stderr' specify
        alternate input, output and error output file objects; if not
        specified, sys.* are used.

        If 'stdout' but not 'stderr' is specified, stdout is used for
        error output. This is to provide least surprise for users used
        to only the 'stdin' and 'stdout' options with cmd.Cmd.
        """
        if self.name is None:
            self.name = os.path.basename(sys.argv[0])
        if self.prompt is None:
            self.prompt = self.name+"> "
        self._name_str = self._str(self.name)
        self._prompt_str = self._str(self.prompt)
        if stdin is not None:
            self.stdin = stdin
        else:
            self.stdin = sys.stdin
        if stdout is not None:
            self.stdout = stdout
        else:
            self.stdout = sys.stdout
        if stderr is not None:
            self.stderr = stderr
        elif stdout is not None:
            self.stderr = stdout
        else:
            self.stderr = sys.stderr
        self.cmdqueue = []
        self.completekey = completekey
        self.cmdlooping = False

    def get_optparser(self):
        """Hook for subclasses to set the option parser for the
        top-level command/shell.

        This option parser is used retrieved and used by `.main()' to
        handle top-level options.

        The default implements a single '-h|--help' option. Sub-classes
        can return None to have no options at the top-level. Typically
        an instance of CmdlnOptionParser should be returned.
        """
        version = (self.version is not None
                    and "%s %s" % (self._name_str, self.version)
                    or None)
        return CmdlnOptionParser(self, version=version)

    def get_version(self):
        """
        Returns version of program. To be replaced in subclass.
        """
        return __version__

    def postoptparse(self):
        """Hook method executed just after `.main()' parses top-level
        options.

        When called `self.values' holds the results of the option parse.
        """
        pass

    def main(self, argv=None, loop=LOOP_NEVER):
        """A possible mainline handler for a script, like so:

            import cmdln
            class MyCmd(cmdln.Cmdln):
                name = "mycmd"
                ...

            if __name__ == "__main__":
                MyCmd().main()

        By default this will use sys.argv to issue a single command to
        'MyCmd', then exit. The 'loop' argument can be use to control
        interactive shell behaviour.

        Arguments:
            "argv" (optional, default sys.argv) is the command to run.
                It must be a sequence, where the first element is the
                command name and subsequent elements the args for that
                command.
            "loop" (optional, default LOOP_NEVER) is a constant
                indicating if a command loop should be started (i.e. an
                interactive shell). Valid values (constants on this module):
                    LOOP_ALWAYS     start loop and run "argv", if any
                    LOOP_NEVER      run "argv" (or .emptyline()) and exit
                    LOOP_IF_EMPTY   run "argv", if given, and exit;
                                    otherwise, start loop
        """
        if argv is None:
            argv = sys.argv
        else:
            argv = argv[:] # don't modify caller's list

        self.optparser = self.get_optparser()
        if self.optparser: # i.e. optparser=None means don't process for opts
            try:
                self.options, args = self.optparser.parse_args(argv[1:])
            except CmdlnUserError as ex:
                msg = "%s: %s\nTry '%s help' for info.\n"\
                      % (self.name, ex, self.name)
                self.stderr.write(self._str(msg))
                self.stderr.flush()
                return 1
            except StopOptionProcessing as ex:
                return 0
        else:
            self.options, args = None, argv[1:]
        self.postoptparse()

        if loop == LOOP_ALWAYS:
            if args:
                self.cmdqueue.append(args)
            return self.cmdloop()
        elif loop == LOOP_NEVER:
            if args:
                return self.cmd(args)
            else:
                return self.emptyline()
        elif loop == LOOP_IF_EMPTY:
            if args:
                return self.cmd(args)
            else:
                return self.cmdloop()

    def cmd(self, argv):
        """Run one command and exit.

            "argv" is the arglist for the command to run. argv[0] is the
                command to run. If argv is an empty list then the
                'emptyline' handler is run.

        Returns the return value from the command handler.
        """
        assert isinstance(argv, (list, tuple)), \
                "'argv' is not a sequence: %r" % argv
        retval = None
        try:
            argv = self.precmd(argv)
            retval = self.onecmd(argv)
            self.postcmd(argv)
        except:
            if not self.cmdexc(argv):
                raise
            retval = 1
        return retval

    def _str(self, s):
        """Safely convert the given str/unicode to a string for printing."""
        try:
            return str(s)
        except UnicodeError:
            #XXX What is the proper encoding to use here? 'utf-8' seems
            #    to work better than "getdefaultencoding" (usually
            #    'ascii'), on OS X at least.
            #return s.encode(sys.getdefaultencoding(), "replace")
            return s.encode("utf-8", "replace")

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse into an argv, and
        dispatch (via .precmd(), .onecmd() and .postcmd()), passing them
        the argv. In other words, start a shell.

            "intro" (optional) is a introductory message to print when
                starting the command loop. This overrides the class
                "intro" attribute, if any.
        """
        self.cmdlooping = True
        self.preloop()
        if intro is None:
            intro = self.intro
        if intro:
            intro_str = self._str(intro)
            self.stdout.write(intro_str+'\n')
        self.stop = False
        retval = None
        while not self.stop:
            if self.cmdqueue:
                argv = self.cmdqueue.pop(0)
                assert isinstance(argv, (list, tuple)), \
                        "item on 'cmdqueue' is not a sequence: %r" % argv
            else:
                if self.use_rawinput:
                    try:
                        try:
                            #python 2.x
                            line = raw_input(self._prompt_str)
                        except NameError:
                            line = input(self._prompt_str)
                    except EOFError:
                        line = 'EOF'
                else:
                    self.stdout.write(self._prompt_str)
                    self.stdout.flush()
                    line = self.stdin.readline()
                    if not len(line):
                        line = 'EOF'
                    else:
                        line = line[:-1] # chop '\n'
                argv = line2argv(line)
            try:
                argv = self.precmd(argv)
                retval = self.onecmd(argv)
                self.postcmd(argv)
            except:
                if not self.cmdexc(argv):
                    raise
                retval = 1
            self.lastretval = retval
        self.postloop()
        self.cmdlooping = False
        return retval

    def precmd(self, argv):
        """Hook method executed just before the command argv is
        interpreted, but after the input prompt is generated and issued.

            "argv" is the cmd to run.

        Returns an argv to run (i.e. this method can modify the command
        to run).
        """
        return argv

    def postcmd(self, argv):
        """Hook method executed just after a command dispatch is finished.

            "argv" is the command that was run.
        """
        pass

    def cmdexc(self, argv):
        """Called if an exception is raised in any of precmd(), onecmd(),
        or postcmd(). If True is returned, the exception is deemed to have
        been dealt with. Otherwise, the exception is re-raised.

        The default implementation handles CmdlnUserError's, which
        typically correspond to user error in calling commands (as
        opposed to programmer error in the design of the script using
        cmdln.py).
        """
        exc_type, exc, traceback = sys.exc_info()
        if isinstance(exc, CmdlnUserError):
            msg = "%s %s: %s\nTry '%s help %s' for info.\n"\
                  % (self.name, argv[0], exc, self.name, argv[0])
            self.stderr.write(self._str(msg))
            self.stderr.flush()
            return True

    def onecmd(self, argv):
        if not argv:
            return self.emptyline()
        self.lastcmd = argv
        cmdname = self._get_canonical_cmd_name(argv[0])
        if cmdname:
            handler = self._get_cmd_handler(cmdname)
            if handler:
                return self._dispatch_cmd(handler, argv)
        return self.default(argv)

    def _dispatch_cmd(self, handler, argv):
        return handler(argv)

    def default(self, argv):
        """Hook called to handle a command for which there is no handler.

            "argv" is the command and arguments to run.

        The default implementation writes and error message to stderr
        and returns an error exit status.

        Returns a numeric command exit status.
        """
        errmsg = self._str(self.unknowncmd % (argv[0],))
        if self.cmdlooping:
            self.stderr.write(errmsg+"\n")
        else:
            self.stderr.write("%s: %s\nTry '%s help' for info.\n"
                              % (self._name_str, errmsg, self._name_str))
        self.stderr.flush()
        return 1

    def parseline(self, line):
        # This is used by Cmd.complete (readline completer function) to
        # massage the current line buffer before completion processing.
        # We override to drop special '!' handling.
        line = line.strip()
        if not line:
            return None, None, line
        elif line[0] == '?':
            line = 'help ' + line[1:]
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars: 
            i = i+1
        cmd, arg = line[:i], line[i:].strip()
        return cmd, arg, line

    def helpdefault(self, cmd, known):
        """Hook called to handle help on a command for which there is no
        help handler.

            "cmd" is the command name on which help was requested.
            "known" is a boolean indicating if this command is known
                (i.e. if there is a handler for it).

        Returns a return code.
        """
        if known:
            msg = self._str(self.nohelp % (cmd,))
            if self.cmdlooping:
                self.stderr.write(msg + '\n')
            else:
                self.stderr.write("%s: %s\n" % (self.name, msg))
        else:
            msg = self.unknowncmd % (cmd,)
            if self.cmdlooping:
                self.stderr.write(msg + '\n')
            else:
                self.stderr.write("%s: %s\n"
                                  "Try '%s help' for info.\n"
                                  % (self.name, msg, self.name))
        self.stderr.flush()
        return 1


    def do_help(self, argv):
        """${cmd_name}: give detailed help on a specific sub-command

        usage:
            ${name} help [SUBCOMMAND]
        """
        if len(argv) > 1: # asking for help on a particular command
            doc = None
            cmdname = self._get_canonical_cmd_name(argv[1]) or argv[1]
            if not cmdname:
                return self.helpdefault(argv[1], False)
            else:
                helpfunc = getattr(self, "help_"+cmdname, None)
                if helpfunc:
                    doc = helpfunc()
                else:
                    handler = self._get_cmd_handler(cmdname)
                    if handler:
                        doc = handler.__doc__
                    if doc is None:
                        return self.helpdefault(argv[1], handler != None)
        else: # bare "help" command
            doc = self.__class__.__doc__  # try class docstring
            if doc is None:
                # Try to provide some reasonable useful default help.
                if self.cmdlooping: 
                    prefix = ""
                else:
                    prefix = self.name+' '
                doc = """usage:
                    %sSUBCOMMAND [ARGS...]
                    %shelp [SUBCOMMAND]

                ${option_list}
                ${command_list}
                ${help_list}
                """ % (prefix, prefix)
            cmdname = None

        if doc: # *do* have help content, massage and print that
            doc = self._help_reindent(doc)
            doc = self._help_preprocess(doc, cmdname)
            doc = doc.rstrip() + '\n' # trim down trailing space
            self.stdout.write(self._str(doc))
            self.stdout.flush()
    do_help.aliases = ["?"]


    def do_man(self, argv):
        """${cmd_name}: generates a man page

        usage:
            ${name} man
        """
        self.stdout.write(bytes(
            self.man_header % {
                'date': date.today().strftime('%b %Y'),
                'version': self.get_version(),
                'name': self.name,
                'ucname': self.name.upper()
                },
            "utf-8"))

        self.stdout.write(bytes(self.man_commands_header, "utf-8"))
        commands = self._help_get_command_list()
        for command, doc in commands:
            cmdname = command.split(' ')[0]
            text = self._help_preprocess(doc, cmdname)
            lines = []
            for line in text.splitlines(False):
                if line[:8] == ' ' * 8:
                    line = line[8:]
                lines.append(man_escape(line))

            self.stdout.write(bytes(
                '.TP\n\\fB%s\\fR\n%s\n' % (command, '\n'.join(lines)), "utf-8"))

        self.stdout.write(bytes(self.man_options_header, "utf-8"))
        self.stdout.write(bytes(
            man_escape(self._help_preprocess('${option_list}', None)), "utf-8"))

        self.stdout.write(bytes(self.man_footer, "utf-8"))

        self.stdout.flush()

    def _help_reindent(self, help, indent=None):
        """Hook to re-indent help strings before writing to stdout.

            "help" is the help content to re-indent
            "indent" is a string with which to indent each line of the
                help content after normalizing. If unspecified or None
                then the default is use: the 'self.helpindent' class
                attribute. By default this is the empty string, i.e.
                no indentation.

        By default, all common leading whitespace is removed and then
        the lot is indented by 'self.helpindent'. When calculating the
        common leading whitespace the first line is ignored -- hence
        help content for Conan can be written as follows and have the
        expected indentation:

            def do_crush(self, ...):
                '''${cmd_name}: crush your enemies, see them driven before you...

                c.f. Conan the Barbarian'''
        """
        if indent is None:
            indent = self.helpindent
        lines = help.splitlines(0)
        _dedentlines(lines, skip_first_line=True)
        lines = [(indent+line).rstrip() for line in lines]
        return '\n'.join(lines)

    def _help_preprocess(self, help, cmdname):
        """Hook to preprocess a help string before writing to stdout.

            "help" is the help string to process.
            "cmdname" is the canonical sub-command name for which help
                is being given, or None if the help is not specific to a
                command.

        By default the following template variables are interpolated in
        help content. (Note: these are similar to Python 2.4's
        string.Template interpolation but not quite.)

        ${name}
            The tool's/shell's name, i.e. 'self.name'.
        ${option_list}
            A formatted table of options for this shell/tool.
        ${command_list}
            A formatted table of available sub-commands.
        ${help_list}
            A formatted table of additional help topics (i.e. 'help_*'
            methods with no matching 'do_*' method).
        ${cmd_name}
            The name (and aliases) for this sub-command formatted as:
            "NAME (ALIAS1, ALIAS2, ...)".
        ${cmd_usage}
            A formatted usage block inferred from the command function
            signature.
        ${cmd_option_list}
            A formatted table of options for this sub-command. (This is
            only available for commands using the optparse integration,
            i.e.  using @cmdln.option decorators or manually setting the
            'optparser' attribute on the 'do_*' method.)

        Returns the processed help.
        """
        preprocessors = {
            "${name}":            self._help_preprocess_name,
            "${option_list}":     self._help_preprocess_option_list,
            "${command_list}":    self._help_preprocess_command_list,
            "${help_list}":       self._help_preprocess_help_list,
            "${cmd_name}":        self._help_preprocess_cmd_name,
            "${cmd_usage}":       self._help_preprocess_cmd_usage,
            "${cmd_option_list}": self._help_preprocess_cmd_option_list,
        }

        for marker, preprocessor in preprocessors.items():
            if marker in help:
                help = preprocessor(help, cmdname)
        return help

    def _help_preprocess_name(self, help, cmdname=None):
        return help.replace("${name}", self.name)

    def _help_preprocess_option_list(self, help, cmdname=None):
        marker = "${option_list}"
        indent, indent_width = _get_indent(marker, help)
        suffix = _get_trailing_whitespace(marker, help)

        if self.optparser:
            # Setup formatting options and format.
            # - Indentation of 4 is better than optparse default of 2.
            #   C.f. Damian Conway's discussion of this in Perl Best
            #   Practices.
            self.optparser.formatter.indent_increment = 4
            self.optparser.formatter.current_indent = indent_width
            block = self.optparser.format_option_help() + '\n'
        else:
            block = ""

        help_msg = help.replace(indent+marker+suffix, block, 1)
        return help_msg

    def _help_get_command_list(self):
        # Find any aliases for commands.
        token2canonical = self._get_canonical_map()
        aliases = {}
        for token, cmdname in token2canonical.items():
            if token == cmdname: 
                continue
            aliases.setdefault(cmdname, []).append(token)

        # Get the list of (non-hidden) commands and their
        # documentation, if any.
        cmdnames = {} # use a dict to strip duplicates
        for attr in self.get_names():
            if attr.startswith("do_"):
                cmdnames[attr[3:]] = True
        linedata = []
        for cmdname in sorted(cmdnames.keys()):
            if aliases.get(cmdname):
                a = sorted(aliases[cmdname])
                cmdstr = "%s (%s)" % (cmdname, ", ".join(a))
            else:
                cmdstr = cmdname
            doc = None
            try:
                helpfunc = getattr(self, 'help_'+cmdname)
            except AttributeError:
                handler = self._get_cmd_handler(cmdname)
                if handler:
                    doc = handler.__doc__
            else:
                doc = helpfunc()

            # Strip "${cmd_name}: " from the start of a command's doc. Best
            # practice dictates that command help strings begin with this, but
            # it isn't at all wanted for the command list.
            to_strip = "${cmd_name}:"
            if doc and doc.startswith(to_strip):
                #log.debug("stripping %r from start of %s's help string",
                #          to_strip, cmdname)
                doc = doc[len(to_strip):].lstrip()
            if not getattr(self._get_cmd_handler(cmdname), "hidden", None):
                linedata.append( (cmdstr, doc) )

        return linedata

    def _help_preprocess_command_list(self, help, cmdname=None):
        marker = "${command_list}"
        indent, indent_width = _get_indent(marker, help)
        suffix = _get_trailing_whitespace(marker, help)

        linedata = self._help_get_command_list()

        if linedata:
            subindent = indent + ' '*4
            lines = _format_linedata(linedata, subindent, indent_width+4)
            block = indent + "commands:\n" \
                    + '\n'.join(lines) + "\n\n"
            help = help.replace(indent+marker+suffix, block, 1)
        return help

    def _help_preprocess_help_list(self, help, cmdname=None):
        marker = "${help_list}"
        indent, indent_width = _get_indent(marker, help)
        suffix = _get_trailing_whitespace(marker, help)

        # Determine the additional help topics, if any.
        helpnames = {}
        token2cmdname = self._get_canonical_map()
        for attr in self.get_names():
            if not attr.startswith("help_"): 
                continue
            helpname = attr[5:]
            if helpname not in token2cmdname:
                helpnames[helpname] = True

        if helpnames:
            helpnames = sorted(helpnames.keys())
            linedata = [(self.name+" help "+n, "") for n in helpnames]

            subindent = indent + ' '*4
            lines = _format_linedata(linedata, subindent, indent_width+4)
            block = indent + "additional help topics:\n" \
                    + '\n'.join(lines) + "\n\n"
        else:
            block = ''
        help_msg = help.replace(indent+marker+suffix, block, 1)
        return help_msg

    def _help_preprocess_cmd_name(self, help, cmdname=None):
        marker = "${cmd_name}"
        handler = self._get_cmd_handler(cmdname)
        if not handler:
            raise CmdlnError("cannot preprocess '%s' into help string: "
                             "could not find command handler for %r"
                             % (marker, cmdname))
        s = cmdname
        if hasattr(handler, "aliases"):
            s += " (%s)" % (", ".join(handler.aliases))
        help_msg = help.replace(marker, s)
        return help_msg

    #TODO: this only makes sense as part of the Cmdln class.
    #      Add hooks to add help preprocessing template vars and put
    #      this one on that class.
    def _help_preprocess_cmd_usage(self, help, cmdname=None):
        marker = "${cmd_usage}"
        handler = self._get_cmd_handler(cmdname)
        if not handler:
            raise CmdlnError("cannot preprocess '%s' into help string: "
                             "could not find command handler for %r"
                             % (marker, cmdname))
        indent, indent_width = _get_indent(marker, help)
        suffix = _get_trailing_whitespace(marker, help)

        func_defaults, co_argcount, co_varnames, co_flags, _ = introspect_handler(handler)
        CO_FLAGS_ARGS = 4
        CO_FLAGS_KWARGS = 8

        # Adjust argcount for possible *args and **kwargs arguments.
        argcount = co_argcount
        if co_flags & CO_FLAGS_ARGS:   
            argcount += 1
        if co_flags & CO_FLAGS_KWARGS: 
            argcount += 1

        # Determine the usage string.
        usage = "%s %s" % (self.name, cmdname)
        if argcount <= 2:   # handler ::= do_FOO(self, argv)
            usage += " [ARGS...]"
        elif argcount >= 3: # handler ::= do_FOO(self, subcmd, opts, ...)
            argnames = list(co_varnames[3:argcount])
            tail = ""
            if co_flags & CO_FLAGS_KWARGS:
                name = argnames.pop(-1)
                import warnings
                # There is no generally accepted mechanism for passing
                # keyword arguments from the command line. Could
                # *perhaps* consider: arg=value arg2=value2 ...
                warnings.warn("argument '**%s' on '%s.%s' command "
                              "handler will never get values"
                              % (name, self.__class__.__name__,
                                 getattr(func, "__name__", getattr(func, "func_name"))))
            if co_flags & CO_FLAGS_ARGS:
                name = argnames.pop(-1)
                tail = "[%s...]" % name.upper()
            while func_defaults:
                func_defaults.pop(-1)
                name = argnames.pop(-1)
                tail = "[%s%s%s]" % (name.upper(), (tail and ' ' or ''), tail)
            while argnames:
                name = argnames.pop(-1)
                tail = "%s %s" % (name.upper(), tail)
            usage += ' ' + tail

        block_lines = [
            self.helpindent + "Usage:",
            self.helpindent + ' '*4 + usage
        ]
        block = '\n'.join(block_lines) + '\n\n'

        help_msg = help.replace(indent+marker+suffix, block, 1)
        return help_msg

    #TODO: this only makes sense as part of the Cmdln class.
    #      Add hooks to add help preprocessing template vars and put
    #      this one on that class.
    def _help_preprocess_cmd_option_list(self, help, cmdname=None):
        marker = "${cmd_option_list}"
        handler = self._get_cmd_handler(cmdname)
        if not handler:
            raise CmdlnError("cannot preprocess '%s' into help string: "
                             "could not find command handler for %r"
                             % (marker, cmdname))
        indent, indent_width = _get_indent(marker, help)
        suffix = _get_trailing_whitespace(marker, help)
        if hasattr(handler, "optparser"):
            # Setup formatting options and format.
            # - Indentation of 4 is better than optparse default of 2.
            #   C.f. Damian Conway's discussion of this in Perl Best
            #   Practices.
            handler.optparser.formatter.indent_increment = 4
            handler.optparser.formatter.current_indent = indent_width
            block = handler.optparser.format_option_help() + '\n'
        else:
            block = ""

        help_msg = help.replace(indent+marker+suffix, block, 1)
        return help_msg

    def _get_canonical_cmd_name(self, token):
        c_map = self._get_canonical_map()
        return c_map.get(token, None)

    def _get_canonical_map(self):
        """Return a mapping of available command names and aliases to
        their canonical command name.
        """
        cacheattr = "_token2canonical"
        if not hasattr(self, cacheattr):
            # Get the list of commands and their aliases, if any.
            token2canonical = {}
            cmd2funcname = {} # use a dict to strip duplicates
            for attr in self.get_names():
                if attr.startswith("do_"):    
                    cmdname = attr[3:]
                elif attr.startswith("_do_"): 
                    cmdname = attr[4:]
                else:
                    continue
                cmd2funcname[cmdname] = attr
                token2canonical[cmdname] = cmdname
            for cmdname, funcname in cmd2funcname.items(): # add aliases
                func = getattr(self, funcname)
                aliases = getattr(func, "aliases", [])
                for alias in aliases:
                    if alias in cmd2funcname:
                        import warnings
                        warnings.warn("'%s' alias for '%s' command conflicts "
                                      "with '%s' handler"
                                      % (alias, cmdname, cmd2funcname[alias]))
                        continue
                    token2canonical[alias] = cmdname
            setattr(self, cacheattr, token2canonical)
        return getattr(self, cacheattr)

    def _get_cmd_handler(self, cmdname):
        handler = None
        try:
            handler = getattr(self, 'do_' + cmdname)
        except AttributeError:
            try:
                # Private command handlers begin with "_do_".
                handler = getattr(self, '_do_' + cmdname)
            except AttributeError:
                pass
        return handler

    def _do_EOF(self, argv):
        # Default EOF handler
        # Note: an actual EOF is redirected to this command.
        #TODO: separate name for this. Currently it is available from
        #      command-line. Is that okay?
        self.stdout.write('\n')
        self.stdout.flush()
        self.stop = True

    def emptyline(self):
        # Different from cmd.Cmd: don't repeat the last command for an
        # emptyline.
        if self.cmdlooping:
            pass
        else:
            return self.do_help(["help"])


#---- optparse.py extension to fix (IMO) some deficiencies
#
# See the class _OptionParserEx docstring for details.
#

class StopOptionProcessing(Exception):
    """Indicate that option *and argument* processing should stop
    cleanly. This is not an error condition. It is similar in spirit to
    StopIteration. This is raised by _OptionParserEx's default "help"
    and "version" option actions and can be raised by custom option
    callbacks too.

    Hence the typical CmdlnOptionParser (a subclass of _OptionParserEx)
    usage is:

        parser = CmdlnOptionParser(mycmd)
        parser.add_option("-f", "--force", dest="force")
        ...
        try:
            opts, args = parser.parse_args()
        except StopOptionProcessing:
            # normal termination, "--help" was probably given
            sys.exit(0)
    """

class _OptionParserEx(optparse.OptionParser):
    """An optparse.OptionParser that uses exceptions instead of sys.exit.

    This class is an extension of optparse.OptionParser that differs
    as follows:
    - Correct (IMO) the default OptionParser error handling to never
      sys.exit(). Instead OptParseError exceptions are passed through.
    - Add the StopOptionProcessing exception (a la StopIteration) to
      indicate normal termination of option processing.
      See StopOptionProcessing's docstring for details.

    I'd also like to see the following in the core optparse.py, perhaps
    as a RawOptionParser which would serve as a base class for the more
    generally used OptionParser (that works as current):
    - Remove the implicit addition of the -h|--help and --version
      options. They can get in the way (e.g. if want '-?' and '-V' for
      these as well) and it is not hard to do:
        optparser.add_option("-h", "--help", action="help")
        optparser.add_option("--version", action="version")
      These are good practices, just not valid defaults if they can
      get in the way.
    """
    def error(self, msg):
        raise optparse.OptParseError(msg)

    def exit(self, status=0, msg=None):
        if status == 0:
            raise StopOptionProcessing(msg)
        else:
            #TODO: don't lose status info here
            raise optparse.OptParseError(msg)



#---- optparse.py-based option processing support

class CmdlnOptionParser(_OptionParserEx):
    """An optparse.OptionParser class more appropriate for top-level
    Cmdln options. For parsing of sub-command options, see
    SubCmdOptionParser.

    Changes:
    - disable_interspersed_args() by default, because a Cmdln instance
      has sub-commands which may themselves have options.
    - Redirect print_help() to the Cmdln.do_help() which is better
      equiped to handle the "help" action.
    - error() will raise a CmdlnUserError: OptionParse.error() is meant
      to be called for user errors. Raising a well-known error here can
      make error handling clearer.
    - Also see the changes in _OptionParserEx.
    """
    def __init__(self, cmdln, **kwargs):
        self.cmdln = cmdln
        kwargs["prog"] = self.cmdln.name
        _OptionParserEx.__init__(self, **kwargs)
        self.disable_interspersed_args()

    def print_help(self, file=None):
        self.cmdln.onecmd(["help"])

    def error(self, msg):
        raise CmdlnUserError(msg)


class SubCmdOptionParser(_OptionParserEx):
    def set_cmdln_info(self, cmdln, subcmd):
        """Called by Cmdln to pass relevant info about itself needed
        for print_help().
        """
        self.cmdln = cmdln
        self.subcmd = subcmd

    def print_help(self, file=None):
        self.cmdln.onecmd(["help", self.subcmd])

    def error(self, msg):
        raise CmdlnUserError(msg)


def option(*args, **kwargs):
    """Decorator to add an option to the optparser argument of a Cmdln
    subcommand.

    Example:
        class MyShell(cmdln.Cmdln):
            @cmdln.option("-f", "--force", help="force removal")
            def do_remove(self, subcmd, opts, *args):
                #...
    """
    #XXX Is there a possible optimization for many options to not have a
    #    large stack depth here?
    def decorate(f):
        if not hasattr(f, "optparser"):
            f.optparser = SubCmdOptionParser()
        f.optparser.add_option(*args, **kwargs)
        return f
    return decorate

def hide(*args):
    """For obsolete calls, hide them in help listings.

    Example:
        class MyShell(cmdln.Cmdln):
            @cmdln.hide()
            def do_shell(self, argv):
                #...implement 'shell' command
    """
    def decorate(f):
        f.hidden = 1
        return f
    return decorate


class Cmdln(RawCmdln):
    """An improved (on cmd.Cmd) framework for building multi-subcommand
    scripts (think "svn" & "cvs") and simple shells (think "pdb" and
    "gdb").

    A simple example:

        import cmdln

        class MySVN(cmdln.Cmdln):
            name = "svn"

            @cmdln.aliases('stat', 'st')
            @cmdln.option('-v', '--verbose', action='store_true'
                          help='print verbose information')
            def do_status(self, subcmd, opts, *paths):
                print "handle 'svn status' command"

            #...

        if __name__ == "__main__":
            shell = MySVN()
            retval = shell.main()
            sys.exit(retval)

    'Cmdln' extends 'RawCmdln' by providing optparse option processing
    integration.  See this class' _dispatch_cmd() docstring and
    <http://trentm.com/projects/cmdln> for more information.
    """
    def _dispatch_cmd(self, handler, argv):
        """Introspect sub-command handler signature to determine how to
        dispatch the command. The raw handler provided by the base
        'RawCmdln' class is still supported:

            def do_foo(self, argv):
                # 'argv' is the vector of command line args, argv[0] is
                # the command name itself (i.e. "foo" or an alias)
                pass

        In addition, if the handler has more than 2 arguments option
        processing is automatically done (using optparse):

            @cmdln.option('-v', '--verbose', action='store_true')
            def do_bar(self, subcmd, opts, *args):
                # subcmd = <"bar" or an alias>
                # opts = <an optparse.Values instance>
                if opts.verbose:
                    print "lots of debugging output..."
                # args = <tuple of arguments>
                for arg in args:
                    bar(arg)

        TODO: explain that "*args" can be other signatures as well.

        The `cmdln.option` decorator corresponds to an `add_option()`
        method call on an `optparse.OptionParser` instance.

        You can declare a specific number of arguments:

            @cmdln.option('-v', '--verbose', action='store_true')
            def do_bar2(self, subcmd, opts, bar_one, bar_two):
                #...

        and an appropriate error message will be raised/printed if the
        command is called with a different number of args.
        """
        co_argcount = introspect_handler(handler)[1]
        if co_argcount == 2:   # handler ::= do_foo(self, argv)
            return handler(argv)
        elif co_argcount >= 3: # handler ::= do_foo(self, subcmd, opts, ...)
            try:
                optparser = handler.optparser
            except AttributeError:
                optparser = introspect_handler(handler)[4].optparser = SubCmdOptionParser()
            assert isinstance(optparser, SubCmdOptionParser)
            optparser.set_cmdln_info(self, argv[0])
            try:
                opts, args = optparser.parse_args(argv[1:])
            except StopOptionProcessing:
                #TODO: this doesn't really fly for a replacement of
                #      optparse.py behaviour, does it?
                return 0 # Normal command termination

            try:
                return handler(argv[0], opts, *args)
            except TypeError as ex:
                # Some TypeError's are user errors:
                #   do_foo() takes at least 4 arguments (3 given)
                #   do_foo() takes at most 5 arguments (6 given)
                #   do_foo() takes exactly 5 arguments (6 given)
                # Raise CmdlnUserError for these with a suitably
                # massaged error message.
                tb = sys.exc_info()[2] # the traceback object
                if tb.tb_next is not None:
                    # If the traceback is more than one level deep, then the
                    # TypeError do *not* happen on the "handler(...)" call
                    # above. In that we don't want to handle it specially
                    # here: it would falsely mask deeper code errors.
                    raise
                msg = ex.args[0]
                match = _INCORRECT_NUM_ARGS_RE.search(msg)
                if match:
                    msg = list(match.groups())
                    msg[1] = int(msg[1]) - 3
                    if msg[1] == 1:
                        msg[2] = msg[2].replace("arguments", "argument")
                    msg[3] = int(msg[3]) - 3
                    msg = ''.join(map(str, msg))
                    raise CmdlnUserError(msg)
                else:
                    raise
        else:
            raise CmdlnError("incorrect argcount for %s(): takes %d, must "
                             "take 2 for 'argv' signature or 3+ for 'opts' "
                             "signature" % (handler.__name__, co_argcount))



#---- internal support functions

def _format_linedata(linedata, indent, indent_width):
    """Format specific linedata into a pleasant layout.

        "linedata" is a list of 2-tuples of the form:
            (<item-display-string>, <item-docstring>)
        "indent" is a string to use for one level of indentation
        "indent_width" is a number of columns by which the
            formatted data will be indented when printed.

    The <item-display-string> column is held to 15 columns.
    """
    lines = []
    WIDTH = 78 - indent_width
    SPACING = 3
    MAX_NAME_WIDTH = 15

    NAME_WIDTH = min(max([len(s) for s,d in linedata]), MAX_NAME_WIDTH)
    DOC_WIDTH = WIDTH - NAME_WIDTH - SPACING
    for namestr, doc in linedata:
        line = indent + namestr
        if len(namestr) <= NAME_WIDTH:
            line += ' ' * (NAME_WIDTH + SPACING - len(namestr))
        else:
            lines.append(line)
            line = indent + ' ' * (NAME_WIDTH + SPACING)
        line += _summarize_doc(doc, DOC_WIDTH)
        lines.append(line.rstrip())
    return lines

def _summarize_doc(doc, length=60):
    r"""Parse out a short one line summary from the given doclines.

        "doc" is the doc string to summarize.
        "length" is the max length for the summary

    >>> _summarize_doc("this function does this")
    'this function does this'
    >>> _summarize_doc("this function does this", 10)
    'this fu...'
    >>> _summarize_doc("this function does this\nand that")
    'this function does this and that'
    >>> _summarize_doc("this function does this\n\nand that")
    'this function does this'
    """
    if doc is None:
        return ""
    assert length > 3, "length <= 3 is absurdly short for a doc summary"
    doclines = doc.strip().splitlines(0)
    if not doclines:
        return ""

    summlines = []
    for i, line in enumerate(doclines):
        stripped = line.strip()
        if not stripped:
            break
        summlines.append(stripped)
        if len(''.join(summlines)) >= length:
            break

    summary = ' '.join(summlines)
    if len(summary) > length:
        summary = summary[:length-3] + "..."
    return summary


def line2argv(line):
    r"""Parse the given line into an argument vector.

        "line" is the line of input to parse.

    This may get niggly when dealing with quoting and escaping. The
    current state of this parsing may not be completely thorough/correct
    in this respect.

    >>> from cmdln import line2argv
    >>> line2argv("foo")
    ['foo']
    >>> line2argv("foo bar")
    ['foo', 'bar']
    >>> line2argv("foo bar ")
    ['foo', 'bar']
    >>> line2argv(" foo bar")
    ['foo', 'bar']

    Quote handling:

    >>> line2argv("'foo bar'")
    ['foo bar']
    >>> line2argv('"foo bar"')
    ['foo bar']
    >>> line2argv(r'"foo\"bar"')
    ['foo"bar']
    >>> line2argv("'foo bar' spam")
    ['foo bar', 'spam']
    >>> line2argv("'foo 'bar spam")
    ['foo bar', 'spam']
    >>> line2argv("'foo")
    Traceback (most recent call last):
        ...
    ValueError: command line is not terminated: unfinished single-quoted segment
    >>> line2argv('"foo')
    Traceback (most recent call last):
        ...
    ValueError: command line is not terminated: unfinished double-quoted segment
    >>> line2argv('some\tsimple\ttests')
    ['some', 'simple', 'tests']
    >>> line2argv('a "more complex" test')
    ['a', 'more complex', 'test']
    >>> line2argv('a more="complex test of " quotes')
    ['a', 'more=complex test of ', 'quotes']
    >>> line2argv('a more" complex test of " quotes')
    ['a', 'more complex test of ', 'quotes']
    >>> line2argv('an "embedded \\"quote\\""')
    ['an', 'embedded "quote"']
    """
    import string
    line = line.strip()
    argv = []
    state = "default"
    arg = None  # the current argument being parsed
    i = -1
    while True:
        i += 1
        if i >= len(line): 
            break
        ch = line[i]

        if ch == "\\": # escaped char always added to arg, regardless of state
            if arg is None: 
                arg = ""
            i += 1
            arg += line[i]
            continue

        if state == "single-quoted":
            if ch == "'":
                state = "default"
            else:
                arg += ch
        elif state == "double-quoted":
            if ch == '"':
                state = "default"
            else:
                arg += ch
        elif state == "default":
            if ch == '"':
                if arg is None: 
                    arg = ""
                state = "double-quoted"
            elif ch == "'":
                if arg is None: 
                    arg = ""
                state = "single-quoted"
            elif ch in string.whitespace:
                if arg is not None:
                    argv.append(arg)
                arg = None
            else:
                if arg is None: 
                    arg = ""
                arg += ch
    if arg is not None:
        argv.append(arg)
    if state != "default":
        raise ValueError("command line is not terminated: unfinished %s "
                         "segment" % state)
    return argv


def argv2line(argv):
    r"""Put together the given argument vector into a command line.

        "argv" is the argument vector to process.

    >>> from cmdln import argv2line
    >>> argv2line(['foo'])
    'foo'
    >>> argv2line(['foo', 'bar'])
    'foo bar'
    >>> argv2line(['foo', 'bar baz'])
    'foo "bar baz"'
    >>> argv2line(['foo"bar'])
    'foo"bar'
    >>> print argv2line(['foo" bar'])
    'foo" bar'
    >>> print argv2line(["foo' bar"])
    "foo' bar"
    >>> argv2line(["foo'bar"])
    "foo'bar"
    """
    escapedArgs = []
    for arg in argv:
        if ' ' in arg and '"' not in arg:
            arg = '"'+arg+'"'
        elif ' ' in arg and "'" not in arg:
            arg = "'"+arg+"'"
        elif ' ' in arg:
            arg = arg.replace('"', r'\"')
            arg = '"'+arg+'"'
        escapedArgs.append(arg)
    return ' '.join(escapedArgs)


# Recipe: dedent (0.1) in /Users/trentm/tm/recipes/cookbook
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines

        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG:
        print("dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line))
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line:
            continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: 
            print("dedent: indent=%d: %r" % (indent, line))
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG:
        print("dedent: margin=%r" % margin)

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: 
                continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: 
                        print("dedent: %r: EOL -> strip up to EOL" % line)
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print("dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin))
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)


def _get_indent(marker, s, tab_width=8):
    """_get_indent(marker, s, tab_width=8) ->
        (<indentation-of-'marker'>, <indentation-width>)"""
    # Figure out how much the marker is indented.
    INDENT_CHARS = tuple(' \t')
    start = s.index(marker)
    i = start
    while i > 0:
        if s[i-1] not in INDENT_CHARS:
            break
        i -= 1
    indent = s[i:start]
    indent_width = 0
    for ch in indent:
        if ch == ' ':
            indent_width += 1
        elif ch == '\t':
            indent_width += tab_width - (indent_width % tab_width)
    return indent, indent_width

def _get_trailing_whitespace(marker, s):
    """Return the whitespace content trailing the given 'marker' in string 's',
    up to and including a newline.
    """
    suffix = ''
    start = s.index(marker) + len(marker)
    i = start
    while i < len(s):
        if s[i] in ' \t':
            suffix += s[i]
        elif s[i] in '\r\n':
            suffix += s[i]
            if s[i] == '\r' and i+1 < len(s) and s[i+1] == '\n':
                suffix += s[i+1]
            break
        else:
            break
        i += 1
    return suffix


# vim: sw=4 et

########NEW FILE########
__FILENAME__ = commandline
# Copyright (C) 2006 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or version 3 (at your option).

from __future__ import print_function

from . import cmdln
from . import conf
from . import oscerr
import sys
import time
import imp
import inspect
try:
    from urllib.parse import urlsplit
    from urllib.error import HTTPError
    ET_ENCODING = "unicode"
except ImportError:
    #python 2.x
    from urlparse import urlsplit
    from urllib2 import HTTPError
    ET_ENCODING = "utf-8"

from optparse import SUPPRESS_HELP

from .core import *
from .util import safewriter

MAN_HEADER = r""".TH %(ucname)s "1" "%(date)s" "%(name)s %(version)s" "User Commands"
.SH NAME
%(name)s \- openSUSE build service command-line tool.
.SH SYNOPSIS
.B %(name)s
[\fIGLOBALOPTS\fR] \fISUBCOMMAND \fR[\fIOPTS\fR] [\fIARGS\fR...]
.br
.B %(name)s
\fIhelp SUBCOMMAND\fR
.SH DESCRIPTION
openSUSE build service command-line tool.
"""
MAN_FOOTER = r"""
.SH "SEE ALSO"
Type 'osc help <subcommand>' for more detailed help on a specific subcommand.
.PP
For additional information, see
 * http://en.opensuse.org/openSUSE:Build_Service_Tutorial
 * http://en.opensuse.org/openSUSE:OSC
.PP
You can modify osc commands, or roll you own, via the plugin API:
 * http://en.opensuse.org/openSUSE:OSC_plugins
.SH AUTHOR
osc was written by several authors. This man page is automatically generated.
"""

class Osc(cmdln.Cmdln):
    """Usage: osc [GLOBALOPTS] SUBCOMMAND [OPTS] [ARGS...]
    or: osc help SUBCOMMAND

    openSUSE build service command-line tool.
    Type 'osc help <subcommand>' for help on a specific subcommand.

    ${command_list}
    ${help_list}
    global ${option_list}
    For additional information, see
    * http://en.opensuse.org/openSUSE:Build_Service_Tutorial
    * http://en.opensuse.org/openSUSE:OSC

    You can modify osc commands, or roll you own, via the plugin API:
    * http://en.opensuse.org/openSUSE:OSC_plugins
    """
    name = 'osc'
    conf = None

    man_header = MAN_HEADER
    man_footer = MAN_FOOTER

    def __init__(self, *args, **kwargs):
        # the plugins have to be loaded before the
        # superclass' __init__ method is called
        self._load_plugins()
        cmdln.Cmdln.__init__(self, *args, **kwargs)
        cmdln.Cmdln.do_help.aliases.append('h')
        sys.stderr = safewriter.SafeWriter(sys.stderr)
        sys.stdout = safewriter.SafeWriter(sys.stdout)

    def get_version(self):
        return get_osc_version()

    def get_optparser(self):
        """this is the parser for "global" options (not specific to subcommand)"""

        optparser = cmdln.CmdlnOptionParser(self, version=get_osc_version())
        optparser.add_option('--debugger', action='store_true',
                      help='jump into the debugger before executing anything')
        optparser.add_option('--post-mortem', action='store_true',
                      help='jump into the debugger in case of errors')
        optparser.add_option('-t', '--traceback', action='store_true',
                      help='print call trace in case of errors')
        optparser.add_option('-H', '--http-debug', action='store_true',
                      help='debug HTTP traffic (filters some headers)')
        optparser.add_option('--http-full-debug', action='store_true',
                      help='debug HTTP traffic (filters no headers)')
        optparser.add_option('-d', '--debug', action='store_true',
                      help='print info useful for debugging')
        optparser.add_option('-A', '--apiurl', dest='apiurl',
                      metavar='URL/alias',
                      help='specify URL to access API server at or an alias')
        optparser.add_option('-c', '--config', dest='conffile',
                      metavar='FILE',
                      help='specify alternate configuration file')
        optparser.add_option('--no-keyring', action='store_true',
                      help='disable usage of desktop keyring system')
        optparser.add_option('--no-gnome-keyring', action='store_true',
                      help='disable usage of GNOME Keyring')
        optparser.add_option('-v', '--verbose', dest='verbose', action='count', default=0,
                      help='increase verbosity')
        optparser.add_option('-q', '--quiet',   dest='verbose', action='store_const', const=-1,
                      help='be quiet, not verbose')
        return optparser


    def postoptparse(self, try_again = True):
        """merge commandline options into the config"""
        try:
            conf.get_config(override_conffile = self.options.conffile,
                            override_apiurl = self.options.apiurl,
                            override_debug = self.options.debug,
                            override_http_debug = self.options.http_debug,
                            override_http_full_debug = self.options.http_full_debug,
                            override_traceback = self.options.traceback,
                            override_post_mortem = self.options.post_mortem,
                            override_no_keyring = self.options.no_keyring,
                            override_no_gnome_keyring = self.options.no_gnome_keyring,
                            override_verbose = self.options.verbose)
        except oscerr.NoConfigfile as e:
            print(e.msg, file=sys.stderr)
            print('Creating osc configuration file %s ...' % e.file, file=sys.stderr)
            import getpass
            config = {}
            config['user'] = raw_input('Username: ')
            config['pass'] = getpass.getpass()
            if self.options.no_keyring:
                config['use_keyring'] = '0'
            if self.options.no_gnome_keyring:
                config['gnome_keyring'] = '0'
            if self.options.apiurl:
                config['apiurl'] = self.options.apiurl

            conf.write_initial_config(e.file, config)
            print('done', file=sys.stderr)
            if try_again: 
                self.postoptparse(try_again = False)
        except oscerr.ConfigMissingApiurl as e:
            print(e.msg, file=sys.stderr)
            import getpass
            user = raw_input('Username: ')
            passwd = getpass.getpass()
            conf.add_section(e.file, e.url, user, passwd)
            if try_again: 
                self.postoptparse(try_again = False)

        self.options.verbose = conf.config['verbose']
        self.download_progress = None
        if conf.config.get('show_download_progress', False):
            from .meter import TextMeter
            self.download_progress = TextMeter(hide_finished=True)


    def get_cmd_help(self, cmdname):
        doc = self._get_cmd_handler(cmdname).__doc__
        doc = self._help_reindent(doc)
        doc = self._help_preprocess(doc, cmdname)
        doc = doc.rstrip() + '\n' # trim down trailing space
        return self._str(doc)

    def get_api_url(self):
        try:
            localdir = os.getcwd()
        except Exception as e:
            ## check for Stale NFS file handle: '.'
            try:
                os.stat('.')
            except Exception as ee: 
                e = ee
            print("os.getcwd() failed: ", e, file=sys.stderr)
            sys.exit(1)

        if (is_package_dir(localdir) or is_project_dir(localdir)) and not self.options.apiurl:
            return store_read_apiurl(os.curdir)
        else:
            return conf.config['apiurl']

    # overridden from class Cmdln() to use config variables in help texts
    def _help_preprocess(self, help, cmdname):
        help_msg = cmdln.Cmdln._help_preprocess(self, help, cmdname)
        return help_msg % conf.config


    def do_init(self, subcmd, opts, project, package=None):
        """${cmd_name}: Initialize a directory as working copy

        Initialize an existing directory to be a working copy of an
        (already existing) buildservice project/package.

        (This is the same as checking out a package and then copying sources
        into the directory. It does NOT create a new package. To create a
        package, use 'osc meta pkg ... ...')

        You wouldn't normally use this command.

        To get a working copy of a package (e.g. for building it or working on
        it, you would normally use the checkout command. Use "osc help
        checkout" to get help for it.

        usage:
            osc init PRJ
            osc init PRJ PAC
        ${cmd_option_list}
        """

        apiurl = self.get_api_url()

        if not package:
            Project.init_project(apiurl, os.curdir, project, conf.config['do_package_tracking'])
            print('Initializing %s (Project: %s)' % (os.curdir, project))
        else:
            Package.init_package(apiurl, project, package, os.curdir)
            store_write_string(os.curdir, '_files', show_files_meta(apiurl, project, package) + '\n')
            print('Initializing %s (Project: %s, Package: %s)' % (os.curdir, project, package))

    @cmdln.alias('ls')
    @cmdln.alias('ll')
    @cmdln.alias('lL')
    @cmdln.alias('LL')
    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='specify architecture (only for binaries)')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='specify repository (only for binaries)')
    @cmdln.option('-b', '--binaries', action='store_true',
                        help='list built binaries instead of sources')
    @cmdln.option('-e', '--expand', action='store_true',
                        help='expand linked package (only for sources)')
    @cmdln.option('-u', '--unexpand', action='store_true',
                        help='always work with unexpanded (source) packages')
    @cmdln.option('-v', '--verbose', action='store_true',
                        help='print extra information')
    @cmdln.option('-l', '--long', action='store_true', dest='verbose',
                        help='print extra information')
    @cmdln.option('-D', '--deleted', action='store_true',
                        help='show only the former deleted projects or packages')
    @cmdln.option('-M', '--meta', action='store_true',
                        help='list meta data files')
    @cmdln.option('-R', '--revision', metavar='REVISION',
                        help='specify revision (only for sources)')
    def do_list(self, subcmd, opts, *args):
        """${cmd_name}: List sources or binaries on the server

        Examples for listing sources:
           ls                          # list all projects (deprecated)
           ls /                        # list all projects
           ls .                        # take PROJECT/PACKAGE from current dir.
           ls PROJECT                  # list packages in a project
           ls PROJECT PACKAGE          # list source files of package of a project
           ls PROJECT PACKAGE <file>   # list <file> if this file exists
           ls -v PROJECT PACKAGE       # verbosely list source files of package
           ls -l PROJECT PACKAGE       # verbosely list source files of package
           ll PROJECT PACKAGE          # verbosely list source files of package
           LL PROJECT PACKAGE          # verbosely list source files of expanded link

        With --verbose, the following fields will be shown for each item:
           MD5 hash of file
           Revision number of the last commit
           Size (in bytes)
           Date and time of the last commit

        Examples for listing binaries:
           ls -b PROJECT               # list all binaries of a project
           ls -b PROJECT -a ARCH       # list ARCH binaries of a project
           ls -b PROJECT -r REPO       # list binaries in REPO
           ls -b PROJECT PACKAGE REPO ARCH

        Usage:
           ${cmd_name} [PROJECT [PACKAGE]]
           ${cmd_name} -b [PROJECT [PACKAGE [REPO [ARCH]]]]
        ${cmd_option_list}
        """

        args = slash_split(args)
        if subcmd == 'll':
            opts.verbose = True
        if subcmd == 'lL' or subcmd == 'LL':
            opts.verbose = True
            opts.expand = True

        project = None
        package = None
        fname = None
        if len(args) == 0:
            # For consistency with *all* other commands
            # this lists what the server has in the current wd.
            # CAUTION: 'osc ls -b' already works like this.
            pass
        if len(args) > 0:
            project = args[0]
            if project == '/': 
                project = None
            if project == '.':
                cwd = os.getcwd()
                if is_project_dir(cwd):
                    project = store_read_project(cwd)
                elif is_package_dir(cwd):
                    project = store_read_project(cwd)
                    package = store_read_package(cwd)
        if len(args) > 1:
            package = args[1]
        if len(args) > 2:
            if opts.deleted:
                raise oscerr.WrongArgs("Too many arguments when listing deleted packages")
            if opts.binaries:
                if opts.repo:
                    if opts.repo != args[2]:
                        raise oscerr.WrongArgs("conflicting repos specified ('%s' vs '%s')"%(opts.repo, args[2]))
                else:
                    opts.repo = args[2]
            else:
                fname = args[2]

        if len(args) > 3:
            if not opts.binaries:
                raise oscerr.WrongArgs('Too many arguments')
            if opts.arch:
                if opts.arch != args[3]:
                    raise oscerr.WrongArgs("conflicting archs specified ('%s' vs '%s')"%(opts.arch, args[3]))
            else:
                opts.arch = args[3]


        if opts.binaries and opts.expand:
            raise oscerr.WrongOptions('Sorry, --binaries and --expand are mutual exclusive.')

        apiurl = self.get_api_url() 

        # list binaries
        if opts.binaries:
            # ls -b toplevel doesn't make sense, so use info from
            # current dir if available
            if len(args) == 0:
                cwd = os.getcwd()
                if is_project_dir(cwd):
                    project = store_read_project(cwd)
                elif is_package_dir(cwd):
                    project = store_read_project(cwd)
                    package = store_read_package(cwd)

            if not project:
                raise oscerr.WrongArgs('There are no binaries to list above project level.')
            if opts.revision:
                raise oscerr.WrongOptions('Sorry, the --revision option is not supported for binaries.')

            repos = []

            if opts.repo and opts.arch:
                repos.append(Repo(opts.repo, opts.arch))
            elif opts.repo and not opts.arch:
                repos = [repo for repo in get_repos_of_project(apiurl, project) if repo.name == opts.repo]
            elif opts.arch and not opts.repo:
                repos = [repo for repo in get_repos_of_project(apiurl, project) if repo.arch == opts.arch]
            else:
                repos = get_repos_of_project(apiurl, project)

            results = []
            for repo in repos:
                results.append((repo, get_binarylist(apiurl, project, repo.name, repo.arch, package=package, verbose=opts.verbose)))

            for result in results:
                indent = ''
                if len(results) > 1:
                    print('%s/%s' % (result[0].name, result[0].arch))
                    indent = ' '

                if opts.verbose:
                    for f in result[1]:
                        print("%9d %s %-40s" % (f.size, shorttime(f.mtime), f.name))
                else:
                    for f in result[1]:
                        print(indent+f)

        # list sources
        elif not opts.binaries:
            if not args:
                for prj in meta_get_project_list(apiurl, opts.deleted):
                    print(prj)

            elif len(args) == 1:
                if opts.verbose:
                    if self.options.verbose:
                        print('Sorry, the --verbose option is not implemented for projects.', file=sys.stderr)
                if opts.expand:
                    raise oscerr.WrongOptions('Sorry, the --expand option is not implemented for projects.')
                for pkg in meta_get_packagelist(apiurl, project, opts.deleted):
                    print(pkg)

            elif len(args) == 2 or len(args) == 3:
                link_seen = False
                print_not_found = True
                rev = opts.revision
                for i in [ 1, 2 ]:
                    l = meta_get_filelist(apiurl,
                                      project,
                                      package,
                                      verbose=opts.verbose,
                                      expand=opts.expand,
                                      meta=opts.meta,
                                      deleted=opts.deleted,
                                      revision=rev)
                    link_seen = '_link' in l
                    if opts.verbose:
                        out = [ '%s %7s %9d %s %s' % (i.md5, i.rev, i.size, shorttime(i.mtime), i.name) \
                            for i in l if not fname or fname == i.name ]
                        if len(out) > 0:
                            print_not_found = False
                            print('\n'.join(out))
                    elif fname:
                        if fname in l:
                            print(fname)
                            print_not_found = False
                    else:
                        print('\n'.join(l))
                    if opts.expand or opts.unexpand or not link_seen: 
                        break
                    m = show_files_meta(apiurl, project, package)
                    li = Linkinfo()
                    li.read(ET.fromstring(''.join(m)).find('linkinfo'))
                    if li.haserror():
                        raise oscerr.LinkExpandError(project, package, li.error)
                    project, package, rev = li.project, li.package, li.rev
                    if rev:
                        print('# -> %s %s (%s)' % (project, package, rev))
                    else:
                        print('# -> %s %s (latest)' % (project, package))
                    opts.expand = True
                if fname and print_not_found:
                    print('file \'%s\' does not exist' % fname)


    @cmdln.option('-f', '--force', action='store_true',
                        help='force generation of new patchinfo file, do not update existing one.')
    def do_patchinfo(self, subcmd, opts, *args):
        """${cmd_name}: Generate and edit a patchinfo file.

        A patchinfo file describes the packages for an update and the kind of
        problem it solves.

        This command either creates a new _patchinfo or updates an existing one.

        Examples:
            osc patchinfo
            osc patchinfo [PROJECT [PATCH_NAME]]
        ${cmd_option_list}
        """

        apiurl = self.get_api_url() 
        project_dir = localdir = os.getcwd()
        patchinfo = 'patchinfo'
        if len(args) == 0:
            if is_project_dir(localdir):
                project = store_read_project(localdir)
                apiurl = self.get_api_url()
                for p in meta_get_packagelist(apiurl, project):
                    if p.startswith("_patchinfo") or p.startswith("patchinfo"):
                        patchinfo = p
            else:
                if is_package_dir(localdir):
                    project = store_read_project(localdir)
                    patchinfo = store_read_package(localdir)
                    apiurl = self.get_api_url()
                    if not os.path.exists('_patchinfo'):
                        sys.exit('Current checked out package has no _patchinfo. Either call it from project level or specify patch name.')
                else:
                    sys.exit('This command must be called in a checked out project or patchinfo package.')
        else:
            project = args[0]
            if len(args) > 1:
                patchinfo = args[1]

        filelist = None
        if patchinfo:
            try:
                filelist = meta_get_filelist(apiurl, project, patchinfo)
            except HTTPError:
                pass

        if opts.force or not filelist or not '_patchinfo' in filelist:
            print("Creating new patchinfo...")
            query = 'cmd=createpatchinfo&name=' + patchinfo
            if opts.force:
                query += "&force=1"
            url = makeurl(apiurl, ['source', project], query=query)
            f = http_POST(url)
            for p in meta_get_packagelist(apiurl, project):
                if p.startswith("_patchinfo") or p.startswith("patchinfo"):
                    patchinfo = p
        else:
            print("Update existing _patchinfo file...")
            query = 'cmd=updatepatchinfo'
            url = makeurl(apiurl, ['source', project, patchinfo], query=query)
            f = http_POST(url)

        # CAUTION:
        #  Both conf.config['checkout_no_colon'] and conf.config['checkout_rooted'] 
        #  fool this test:
        if is_package_dir(localdir):
            pac = Package(localdir)
            pac.update()
            filename = "_patchinfo"
        else:
            checkout_package(apiurl, project, patchinfo, prj_dir=project_dir)
            filename = project_dir + "/" + patchinfo + "/_patchinfo"

        run_editor(filename)

    @cmdln.alias('bsdevelproject')
    @cmdln.alias('dp')
    @cmdln.option('-r', '--raw', action='store_true', help='deprecated option')
    def do_develproject(self, subcmd, opts, *args):
        """${cmd_name}: print the devel project / package of a package

        Examples:
            osc develproject PRJ PKG
            osc develproject
        ${cmd_option_list}
        """
        args = slash_split(args)
        apiurl = self.get_api_url()

        if len(args) == 0:
            project = store_read_project(os.curdir)
            package = store_read_package(os.curdir)
        elif len(args) == 2:
            project = args[0]
            package = args[1]
        else:
            raise oscerr.WrongArgs('need Project and Package')

        devprj, devpkg = show_devel_project(apiurl, project, package)
        if devprj is None:
            print('%s / %s has no devel project' % (project, package))
        elif devpkg and devpkg != package:
            print("%s %s" % (devprj, devpkg))
        else:
            print(devprj)

    @cmdln.alias('sdp')
    @cmdln.option('-u', '--unset', action='store_true',
                  help='remove devel project')
    def do_setdevelproject(self, subcmd, opts, *args):
        """${cmd_name}: Set the devel project / package of a package

        Examples:
            osc setdevelproject [PRJ PKG] DEVPRJ [DEVPKG]
        ${cmd_option_list}
        """
        args = slash_split(args)
        apiurl = self.get_api_url()

        devprj, devpkg = None, None
        if len(args) == 3 or len(args) == 4:
            project, package = args[0], args[1]
            devprj = args[2]
            if len(args) == 4:
                devpkg = args[3]
        elif len(args) >= 1 and len(args) <= 2:
            project, package = store_read_project(os.curdir), store_read_package(os.curdir)
            devprj = args[0]
            if len(args) == 2:
                devpkg = args[1]
        else:
            if opts.unset:
                project, package = store_read_project(os.curdir), store_read_package(os.curdir)
            else:
                raise oscerr.WrongArgs('need at least DEVPRJ (and possibly DEVPKG)')

        set_devel_project(apiurl, project, package, devprj, devpkg)


    @cmdln.option('-c', '--create', action='store_true',
                        help='Create a new token')
    @cmdln.option('-d', '--delete', metavar='TOKENID',
                        help='Create a new token')
    @cmdln.option('-t', '--trigger', metavar='TOKENID',
                        help='Trigger the action of a token')
    def do_token(self, subcmd, opts, *args):
        """${cmd_name}: Show and manage authentication token

        Authentication token can be used to run specific commands without
        sending credentials.

        Usage:
            osc token
            osc token --create [<PROJECT> <PACKAGE>]
            osc token --delete <TOKENID>
            osc token --trigger <TOKENID>
        ${cmd_option_list}
        """

        args = slash_split(args)

        apiurl = self.get_api_url()
        url = apiurl + "/person/" + conf.get_apiurl_usr(apiurl) + "/token"

        if opts.create:
            print("Create a new token")
            url += "?cmd=create"
            if len(args) > 1:
                url += "&project=" + args[0]
                url += "&package=" + args[1]

            f = http_POST(url)
            while True:
                buf = f.read(16384)
                if not buf:
                    break
                sys.stdout.write(buf)

        elif opts.delete:
            print("Delete token")
            url += "/" + opts.delete
            http_DELETE(url)
        elif opts.trigger:
            print("Trigger token")
            url = apiurl + "/trigger/runservice"
            req = URLRequest(url)
            req.get_method = lambda: "POST"
            req.add_header('Content-Type', 'application/octet-stream')
            req.add_header('Authorization', "Token "+opts.trigger)
            fd = urlopen(req, data=None)
            print(fd.read())
        else:
            # just list token
            for data in streamfile(url, http_GET):
                sys.stdout.write(data)


    @cmdln.option('-a', '--attribute', metavar='ATTRIBUTE',
                        help='affect only a given attribute')
    @cmdln.option('--attribute-defaults', action='store_true',
                        help='include defined attribute defaults')
    @cmdln.option('--attribute-project', action='store_true',
                        help='include project values, if missing in packages ')
    @cmdln.option('-f', '--force', action='store_true',
                        help='force the save operation, allows one to ignores some errors like depending repositories. For prj meta only.')
    @cmdln.option('-F', '--file', metavar='FILE',
                        help='read metadata from FILE, instead of opening an editor. '
                        '\'-\' denotes standard input. ')
    @cmdln.option('-e', '--edit', action='store_true',
                        help='edit metadata')
    @cmdln.option('-c', '--create', action='store_true',
                        help='create attribute without values')
    @cmdln.option('-R', '--remove-linking-repositories', action='store_true',
                        help='Try to remove also all repositories building against remove ones.')
    @cmdln.option('-s', '--set', metavar='ATTRIBUTE_VALUES',
                        help='set attribute values')
    @cmdln.option('--delete', action='store_true',
                        help='delete a pattern or attribute')
    def do_meta(self, subcmd, opts, *args):
        """${cmd_name}: Show meta information, or edit it

        Show or edit build service metadata of type <prj|pkg|prjconf|user|pattern>.

        This command displays metadata on buildservice objects like projects,
        packages, or users. The type of metadata is specified by the word after
        "meta", like e.g. "meta prj".

        prj denotes metadata of a buildservice project.
        prjconf denotes the (build) configuration of a project.
        pkg denotes metadata of a buildservice package.
        user denotes the metadata of a user.
        pattern denotes installation patterns defined for a project.

        To list patterns, use 'osc meta pattern PRJ'. An additional argument
        will be the pattern file to view or edit.

        With the --edit switch, the metadata can be edited. Per default, osc
        opens the program specified by the environmental variable EDITOR with a
        temporary file. Alternatively, content to be saved can be supplied via
        the --file switch. If the argument is '-', input is taken from stdin:
        osc meta prjconf home:user | sed ... | osc meta prjconf home:user -F -

        When trying to edit a non-existing resource, it is created implicitly.


        Examples:
            osc meta prj PRJ
            osc meta pkg PRJ PKG
            osc meta pkg PRJ PKG -e
            osc meta attribute PRJ [PKG [SUBPACKAGE]] [--attribute ATTRIBUTE] [--create|--delete|--set [value_list]]

        Usage:
            osc meta <prj|pkg|prjconf|user|pattern|attribute> ARGS...
            osc meta <prj|pkg|prjconf|user|pattern|attribute> -e|--edit ARGS...
            osc meta <prj|pkg|prjconf|user|pattern|attribute> -F|--file ARGS...
            osc meta pattern --delete PRJ PATTERN
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or args[0] not in metatypes.keys():
            raise oscerr.WrongArgs('Unknown meta type. Choose one of %s.' \
                                               % ', '.join(metatypes))

        cmd = args[0]
        del args[0]

        if cmd in ['pkg']:
            min_args, max_args = 0, 2
        elif cmd in ['pattern']:
            min_args, max_args = 1, 2
        elif cmd in ['attribute']:
            min_args, max_args = 1, 3
        elif cmd in ['prj', 'prjconf']:
            min_args, max_args = 0, 1
        else:
            min_args, max_args = 1, 1

        if len(args) < min_args:
            raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > max_args:
            raise oscerr.WrongArgs('Too many arguments.')

        apiurl = self.get_api_url()

        # Specific arguments
        #
        # If project or package arguments missing, assume to work
        # with project and/or package in current local directory.
        attributepath = []
        if cmd in ['prj', 'prjconf']:
            if len(args) < 1:
                apiurl = store_read_apiurl(os.curdir)
                project = store_read_project(os.curdir)
            else:
                project = args[0]

        elif cmd == 'pkg':
            if len(args) < 2:
                apiurl = store_read_apiurl(os.curdir)
                project = store_read_project(os.curdir)
                if len(args) < 1:
                    package = store_read_package(os.curdir)
                else:
                    package = args[0]
            else:
                project = args[0]
                package = args[1]

        elif cmd == 'attribute':
            project = args[0]
            if len(args) > 1:
                package = args[1]
            else:
                package = None
                if opts.attribute_project:
                    raise oscerr.WrongOptions('--attribute-project works only when also a package is given')
            if len(args) > 2:
                subpackage = args[2]
            else:
                subpackage = None
            attributepath.append('source')
            attributepath.append(project)
            if package:
                attributepath.append(package)
            if subpackage:
                attributepath.append(subpackage)
            attributepath.append('_attribute')
        elif cmd == 'user':
            user = args[0]
        elif cmd == 'pattern':
            project = args[0]
            if len(args) > 1:
                pattern = args[1]
            else:
                pattern = None
                # enforce pattern argument if needed
                if opts.edit or opts.file:
                    raise oscerr.WrongArgs('A pattern file argument is required.')

        # show
        if not opts.edit and not opts.file and not opts.delete and not opts.create and not opts.set:
            if cmd == 'prj':
                sys.stdout.write(''.join(show_project_meta(apiurl, project)))
            elif cmd == 'pkg':
                sys.stdout.write(''.join(show_package_meta(apiurl, project, package)))
            elif cmd == 'attribute':
                sys.stdout.write(''.join(show_attribute_meta(apiurl, project, package, subpackage, 
                                         opts.attribute, opts.attribute_defaults, opts.attribute_project)))
            elif cmd == 'prjconf':
                sys.stdout.write(''.join(show_project_conf(apiurl, project)))
            elif cmd == 'user':
                r = get_user_meta(apiurl, user)
                if r:
                    sys.stdout.write(''.join(r))
            elif cmd == 'pattern':
                if pattern:
                    r = show_pattern_meta(apiurl, project, pattern)
                    if r:
                        sys.stdout.write(''.join(r))
                else:
                    r = show_pattern_metalist(apiurl, project)
                    if r:
                        sys.stdout.write('\n'.join(r) + '\n')

        # edit
        if opts.edit and not opts.file:
            if cmd == 'prj':
                edit_meta(metatype='prj',
                          edit=True,
                          force=opts.force,
                          remove_linking_repositories=opts.remove_linking_repositories,
                          path_args=quote_plus(project),
                          apiurl=apiurl,
                          template_args=({
                                  'name': project,
                                  'user': conf.get_apiurl_usr(apiurl)}))
            elif cmd == 'pkg':
                edit_meta(metatype='pkg',
                          edit=True,
                          path_args=(quote_plus(project), quote_plus(package)),
                          apiurl=apiurl,
                          template_args=({
                                  'name': package,
                                  'user': conf.get_apiurl_usr(apiurl)}))
            elif cmd == 'prjconf':
                edit_meta(metatype='prjconf',
                          edit=True,
                          path_args=quote_plus(project),
                          apiurl=apiurl,
                          template_args=None)
            elif cmd == 'user':
                edit_meta(metatype='user',
                          edit=True,
                          path_args=(quote_plus(user)),
                          apiurl=apiurl,
                          template_args=({'user': user}))
            elif cmd == 'pattern':
                edit_meta(metatype='pattern',
                          edit=True,
                          path_args=(project, pattern),
                          apiurl=apiurl,
                          template_args=None)

        # create attribute entry
        if (opts.create or opts.set) and cmd == 'attribute':
            if not opts.attribute:
                raise oscerr.WrongOptions('no attribute given to create')
            values = ''
            if opts.set:
                opts.set = opts.set.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                for i in opts.set.split(','):
                    values += '<value>%s</value>' % i
            aname = opts.attribute.split(":")
            if len(aname) != 2:
                raise oscerr.WrongOptions('Given attribute is not in "NAMESPACE:NAME" style')
            d = '<attributes><attribute namespace=\'%s\' name=\'%s\' >%s</attribute></attributes>' % (aname[0], aname[1], values)
            url = makeurl(apiurl, attributepath)
            for data in streamfile(url, http_POST, data=d):
                sys.stdout.write(data)

        # upload file
        if opts.file:

            if opts.file == '-':
                f = sys.stdin.read()
            else:
                try:
                    f = open(opts.file).read()
                except:
                    sys.exit('could not open file \'%s\'.' % opts.file)

            if cmd == 'prj':
                edit_meta(metatype='prj',
                          data=f,
                          edit=opts.edit,
                          force=opts.force,
                          remove_linking_repositories=opts.remove_linking_repositories,
                          apiurl=apiurl,
                          path_args=quote_plus(project))
            elif cmd == 'pkg':
                edit_meta(metatype='pkg',
                          data=f,
                          edit=opts.edit,
                          apiurl=apiurl,
                          path_args=(quote_plus(project), quote_plus(package)))
            elif cmd == 'prjconf':
                edit_meta(metatype='prjconf',
                          data=f,
                          edit=opts.edit,
                          apiurl=apiurl,
                          path_args=quote_plus(project))
            elif cmd == 'user':
                edit_meta(metatype='user',
                          data=f,
                          edit=opts.edit,
                          apiurl=apiurl,
                          path_args=(quote_plus(user)))
            elif cmd == 'pattern':
                edit_meta(metatype='pattern',
                          data=f,
                          edit=opts.edit,
                          apiurl=apiurl,
                          path_args=(project, pattern))


        # delete
        if opts.delete:
            path = metatypes[cmd]['path']
            if cmd == 'pattern':
                path = path % (project, pattern)
                u = makeurl(apiurl, [path])
                http_DELETE(u)
            elif cmd == 'attribute':
                if not opts.attribute:
                    raise oscerr.WrongOptions('no attribute given to create')
                attributepath.append(opts.attribute)
                u = makeurl(apiurl, attributepath)
                for data in streamfile(u, http_DELETE):
                    sys.stdout.write(data)
            else:
                raise oscerr.WrongOptions('The --delete switch is only for pattern metadata or attributes.')


    # TODO: rewrite and consolidate the current submitrequest/createrequest "mess"

    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-r', '--revision', metavar='REV',
                  help='specify a certain source revision ID (the md5 sum) for the source package')
    @cmdln.option('-s', '--supersede', metavar='SUPERSEDE',
                  help='Superseding another request by this one')
    @cmdln.option('--nodevelproject', action='store_true',
                  help='do not follow a defined devel project ' \
                       '(primary project where a package is developed)')
    @cmdln.option('--seperate-requests', action='store_true',
                  help='Create multiple request instead of a single one (when command is used for entire project)')
    @cmdln.option('--cleanup', action='store_true',
                  help='remove package if submission gets accepted (default for home:<id>:branch projects)')
    @cmdln.option('--no-cleanup', action='store_true',
                  help='never remove source package on accept, but update its content')
    @cmdln.option('--no-update', action='store_true',
                  help='never touch source package on accept (will break source links)')
    @cmdln.option('-d', '--diff', action='store_true',
                  help='show diff only instead of creating the actual request')
    @cmdln.option('--yes', action='store_true',
                  help='proceed without asking.')
    @cmdln.alias("sr")
    @cmdln.alias("submitreq")
    @cmdln.alias("submitpac")
    def do_submitrequest(self, subcmd, opts, *args):
        """${cmd_name}: Create request to submit source into another Project

        [See http://en.opensuse.org/openSUSE:Build_Service_Collaboration for information
        on this topic.]

        See the "request" command for showing and modifing existing requests.

        usage:
            osc submitreq [OPTIONS]
            osc submitreq [OPTIONS] DESTPRJ [DESTPKG]
            osc submitreq [OPTIONS] SOURCEPRJ SOURCEPKG DESTPRJ [DESTPKG]

            osc submitpac ... is a shorthand for osc submitreq --cleanup ...

        ${cmd_option_list}
        """

        if opts.cleanup and opts.no_cleanup:
            raise oscerr.WrongOptions('\'--cleanup\' and \'--no-cleanup\' are mutually exclusive')

        src_update = conf.config['submitrequest_on_accept_action'] or None
        # we should check here for home:<id>:branch and default to update, but that would require OBS 1.7 server

        if subcmd == 'submitpac' and not opts.no_cleanup:
            opts.cleanup = True

        if opts.cleanup:
            src_update = "cleanup"
        elif opts.no_cleanup:
            src_update = "update"
        elif opts.no_update:
            src_update = "noupdate"

        myreqs = []
        if opts.supersede:
            myreqs = [opts.supersede]

        args = slash_split(args)

        # remove this block later again
        oldcmds = ['create', 'list', 'log', 'show', 'decline', 'accept', 'delete', 'revoke']
        if args and args[0] in oldcmds:
            print("************************************************************************", file=sys.stderr)
            print("* WARNING: It looks that you are using this command with a             *", file=sys.stderr)
            print("*          deprecated syntax.                                          *", file=sys.stderr)
            print("*          Please run \"osc sr --help\" and \"osc rq --help\"              *", file=sys.stderr)
            print("*          to see the new syntax.                                      *", file=sys.stderr)
            print("************************************************************************", file=sys.stderr)
            if args[0] == 'create':
                args.pop(0)
            else:
                sys.exit(1)

        if len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 2 and is_project_dir(os.getcwd()):
            sys.exit('You can not specify a target package when submitting an entire project\n')

        apiurl = self.get_api_url()

        if len(args) < 2 and is_project_dir(os.getcwd()):
            if opts.diff:
                raise oscerr.WrongOptions('\'--diff\' is not supported in a project working copy')
            import cgi
            project = store_read_project(os.curdir)

            sr_ids = []
            # for single request
            actionxml = ""
            options_block = ""
            if src_update:
                options_block = """<options><sourceupdate>%s</sourceupdate></options> """ % (src_update)

            # loop via all packages for checking their state
            for p in meta_get_packagelist(apiurl, project):
                # get _link info from server, that knows about the local state ...
                u = makeurl(apiurl, ['source', project, p])
                f = http_GET(u)
                root = ET.parse(f).getroot()
                target_project = None
                if len(args) == 1:
                    target_project = args[0]
                linkinfo = root.find('linkinfo')
                if linkinfo == None:
                    if len(args) < 1:
                        print("Package ", p, " is not a source link and no target specified.")
                        sys.exit("This is currently not supported.")
                else:
                    if linkinfo.get('error'):
                        print("Package ", p, " is a broken source link.")
                        sys.exit("Please fix this first")
                    t = linkinfo.get('project')
                    if t:
                        if target_project == None:
                            target_project = t
                        if len(root.findall('entry')) > 1: # This is not really correct, but should work mostly
                                                           # Real fix is to ask the api if sources are modificated
                                                           # but there is no such call yet.
                            print("Submitting package ", p)
                        else:
                            print("  Skipping not modified package ", p)
                            continue
                    else:
                        print("Skipping package ", p,  " since it is a source link pointing inside the project.")
                        continue

                serviceinfo = root.find('serviceinfo')
                if serviceinfo != None:
                    if serviceinfo.get('code') != "succeeded":
                        print("Package ", p, " has a ", serviceinfo.get('code'), " source service")
                        sys.exit("Please fix this first")
                    if serviceinfo.get('error'):
                        print("Package ", p, " contains a failed source service.")
                        sys.exit("Please fix this first")

                # submitting this package
                if opts.seperate_requests:
                    # create a single request
                    result = create_submit_request(apiurl, project, p)
                    if not result:
                        sys.exit("submit request creation failed")
                    sr_ids.append(result)
                else:
                    s = """<action type="submit"> <source project="%s" package="%s" /> <target project="%s" package="%s" /> %s </action>"""  % \
                        (project, p, t, p, options_block)
                    actionxml += s

            if actionxml != "":
                xml = """<request> %s <state name="new"/> <description>%s</description> </request> """ % \
                      (actionxml, cgi.escape(opts.message or ""))
                u = makeurl(apiurl, ['request'], query='cmd=create&addrevision=1')
                f = http_POST(u, data=xml)

                root = ET.parse(f).getroot()
                sr_ids.append(root.get('id'))

            print("Request created: ", end=' ')
            for i in sr_ids:
                print(i, end=' ')

            # was this project created by clone request ?
            u = makeurl(apiurl, ['source', project, '_attribute', 'OBS:RequestCloned'])
            f = http_GET(u)
            root = ET.parse(f).getroot()
            value = root.findtext('attribute/value')
            if value and not opts.yes:
                repl = ''
                print('\n\nThere are already following submit request: %s.' % \
                      ', '.join([str(i) for i in myreqs ]))
                repl = raw_input('\nSupersede the old requests? (y/n) ')
                if repl.lower() == 'y':
                    myreqs += [ value ]

            if len(myreqs) > 0:
                for req in myreqs:
                    change_request_state(apiurl, str(req), 'superseded',
                                             'superseded by %s' % result, result)

            sys.exit('Successfully finished')

        elif len(args) <= 2:
            # try using the working copy at hand
            p = findpacs(os.curdir)[0]
            src_project = p.prjname
            src_package = p.name
            apiurl = p.apiurl
            if len(args) == 0 and p.islink():
                dst_project = p.linkinfo.project
                dst_package = p.linkinfo.package
            elif len(args) > 0:
                dst_project = args[0]
                if len(args) == 2:
                    dst_package = args[1]
                else:
                    if p.islink():
                        dst_package = p.linkinfo.package
                    else:
                        dst_package = src_package
            else:
                sys.exit('Package \'%s\' is not a source link, so I cannot guess the submit target.\n'
                         'Please provide it the target via commandline arguments.' % p.name)

            modified = [i for i in p.filenamelist if not p.status(i) in (' ', '?', 'S')]
            if len(modified) > 0 and not opts.yes:
                print('Your working copy has local modifications.')
                repl = raw_input('Proceed without committing the local changes? (y|N) ')
                if repl != 'y':
                    raise oscerr.UserAbort()
        elif len(args) >= 3:
            # get the arguments from the commandline
            src_project, src_package, dst_project = args[0:3]
            if len(args) == 4:
                dst_package = args[3]
            else:
                dst_package = src_package
        else:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('request'))

        # check for running source service
        u = makeurl(apiurl, ['source', src_project, src_package])
        f = http_GET(u)
        root = ET.parse(f).getroot()
        serviceinfo = root.find('serviceinfo')
        if serviceinfo != None:
            if serviceinfo.get('code') != "succeeded":
                print("Package ", src_package, " has a ", serviceinfo.get('code'), " source service")
                sys.exit("Please fix this first")
            if serviceinfo.get('error'):
                print("Package ", src_package, " contains a failed source service.")
                sys.exit("Please fix this first")

        if not opts.nodevelproject:
            devloc = None
            try:
                devloc, _ = show_devel_project(apiurl, dst_project, dst_package)
            except HTTPError:
                print("""\
Warning: failed to fetch meta data for '%s' package '%s' (new package?) """ \
                    % (dst_project, dst_package), file=sys.stderr)

            if devloc and \
               dst_project != devloc and \
               src_project != devloc:
                print("""\
A different project, %s, is defined as the place where development
of the package %s primarily takes place.
Please submit there instead, or use --nodevelproject to force direct submission.""" \
                % (devloc, dst_package))
                if not opts.diff:
                    sys.exit(1)

        rev = opts.revision
        if not rev:
            # get _link info from server, that knows about the local state ...
            u = makeurl(apiurl, ['source', src_project, src_package], query="expand=1")
            f = http_GET(u)
            root = ET.parse(f).getroot()
            linkinfo = root.find('linkinfo')
            if linkinfo == None:
                rev = root.get('rev')
            else:
                if linkinfo.get('project') != dst_project or linkinfo.get('package') != dst_package:
                    # the submit target is not link target. use merged md5sum references to 
                    # avoid not mergable sources when multiple request from same source get created.
                    rev = root.get('srcmd5')

        rdiff = None
        if opts.diff or not opts.message:
            try:
                rdiff = 'old: %s/%s\nnew: %s/%s rev %s\n' % (dst_project, dst_package, src_project, src_package, rev)
                rdiff += server_diff(apiurl,
                                    dst_project, dst_package, None,
                                    src_project, src_package, rev, True)
            except:
                rdiff = ''

        if opts.diff:
            run_pager(rdiff)
            return
        supersede_existing = False
        reqs = []
        if not opts.supersede:
            (supersede_existing, reqs) = check_existing_requests(apiurl,
                                                                 src_project,
                                                                 src_package,
                                                                 dst_project,
                                                                 dst_package)
        if not opts.message:
            difflines = []
            doappend = False
            changes_re = re.compile(r'^--- .*\.changes ')
            for line in rdiff.split('\n'):
                if line.startswith('--- '):
                    if changes_re.match(line):
                        doappend = True
                    else:
                        doappend = False
                if doappend:
                    difflines.append(line)
            opts.message = edit_message(footer=rdiff, template='\n'.join(parse_diff_for_commit_message('\n'.join(difflines))))

        result = create_submit_request(apiurl,
                                       src_project, src_package,
                                       dst_project, dst_package,
                                       opts.message, orev=rev, src_update=src_update)
        if supersede_existing:
            for req in reqs:
                change_request_state(apiurl, req.reqid, 'superseded',
                                     'superseded by %s' % result, result)

        if opts.supersede:
            change_request_state(apiurl, opts.supersede, 'superseded',
                                 opts.message or '', result)

        print('created request id', result)

    def _actionparser(self, opt_str, value, parser):
        value = []
        if not hasattr(parser.values, 'actiondata'):
            setattr(parser.values, 'actiondata', [])
        if parser.values.actions == None:
            parser.values.actions = []

        rargs = parser.rargs
        while rargs:
            arg = rargs[0]
            if ((arg[:2] == "--" and len(arg) > 2) or
                    (arg[:1] == "-" and len(arg) > 1 and arg[1] != "-")):
                break
            else:
                value.append(arg)
                del rargs[0]

        parser.values.actions.append(value[0])
        del value[0]
        parser.values.actiondata.append(value)

    def _submit_request(self, args, opts, options_block):
        actionxml = ""
        apiurl = self.get_api_url()
        if len(args) == 0 and is_project_dir(os.getcwd()):
            # submit requests for multiple packages are currently handled via multiple requests
            # They could be also one request with multiple actions, but that avoids to accepts parts of it.
            project = store_read_project(os.curdir)

            pi = []
            pac = []
            targetprojects = []
            rdiffmsg = []
            # loop via all packages for checking their state
            for p in meta_get_packagelist(apiurl, project):
                if p.startswith("_patchinfo:"):
                    pi.append(p)
                else:
                    # get _link info from server, that knows about the local state ...
                    u = makeurl(apiurl, ['source', project, p])
                    f = http_GET(u)
                    root = ET.parse(f).getroot()
                    linkinfo = root.find('linkinfo')
                    if linkinfo == None:
                        print("Package ", p, " is not a source link.")
                        sys.exit("This is currently not supported.")
                    if linkinfo.get('error'):
                        print("Package ", p, " is a broken source link.")
                        sys.exit("Please fix this first")
                    t = linkinfo.get('project')
                    if t:
                        rdiff = ''
                        try:
                            rdiff = server_diff(apiurl, t, p, opts.revision, project, p, None, True)
                        except:
                            rdiff = ''

                        if rdiff != '':
                            targetprojects.append(t)
                            pac.append(p)
                            rdiffmsg.append("old: %s/%s\nnew: %s/%s\n%s" % (t, p, project, p, rdiff))
                        else:
                            print("Skipping package ", p,  " since it has no difference with the target package.")
                    else:
                        print("Skipping package ", p,  " since it is a source link pointing inside the project.")
            if opts.diff:
                print(''.join(rdiffmsg))
                sys.exit(0)

                if not opts.yes:
                    if pi:
                        print("Submitting patchinfo ", ', '.join(pi), " to ", ', '.join(targetprojects))
                    print("\nEverything fine? Can we create the requests ? [y/n]")
                    if sys.stdin.read(1) != "y":
                        sys.exit("Aborted...")

            # loop via all packages to do the action
            for p in pac:
                s = """<action type="submit"> <source project="%s" package="%s"  rev="%s"/> <target project="%s" package="%s"/> %s </action>"""  % \
                       (project, p, opts.revision or show_upstream_rev(apiurl, project, p), t, p, options_block)
                actionxml += s

            # create submit requests for all found patchinfos
            for p in pi:
                for t in targetprojects:
                    s = """<action type="submit"> <source project="%s" package="%s" /> <target project="%s" package="%s" /> %s </action>"""  % \
                           (project, p, t, p, options_block)
                    actionxml += s

            return actionxml

        elif len(args) <= 2:
            # try using the working copy at hand
            p = findpacs(os.curdir)[0]
            src_project = p.prjname
            src_package = p.name
            if len(args) == 0 and p.islink():
                dst_project = p.linkinfo.project
                dst_package = p.linkinfo.package
            elif len(args) > 0:
                dst_project = args[0]
                if len(args) == 2:
                    dst_package = args[1]
                else:
                    dst_package = src_package
            else:
                sys.exit('Package \'%s\' is not a source link, so I cannot guess the submit target.\n'
                         'Please provide it the target via commandline arguments.' % p.name)

            modified = [i for i in p.filenamelist if p.status(i) != ' ' and p.status(i) != '?']
            if len(modified) > 0:
                print('Your working copy has local modifications.')
                repl = raw_input('Proceed without committing the local changes? (y|N) ')
                if repl != 'y':
                    sys.exit(1)
        elif len(args) >= 3:
            # get the arguments from the commandline
            src_project, src_package, dst_project = args[0:3]
            if len(args) == 4:
                dst_package = args[3]
            else:
                dst_package = src_package
        else:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('request'))

        if not opts.nodevelproject:
            devloc = None
            try:
                devloc, _ = show_devel_project(apiurl, dst_project, dst_package)
            except HTTPError:
                print("""\
Warning: failed to fetch meta data for '%s' package '%s' (new package?) """ \
                    % (dst_project, dst_package), file=sys.stderr)

            if devloc and \
               dst_project != devloc and \
               src_project != devloc:
                print("""\
A different project, %s, is defined as the place where development
of the package %s primarily takes place.
Please submit there instead, or use --nodevelproject to force direct submission.""" \
                % (devloc, dst_package))
                if not opts.diff:
                    sys.exit(1)

        rdiff = None
        if opts.diff:
            try:
                rdiff = 'old: %s/%s\nnew: %s/%s\n' % (dst_project, dst_package, src_project, src_package)
                rdiff += server_diff(apiurl,
                                    dst_project, dst_package, opts.revision,
                                    src_project, src_package, None, True)
            except:
                rdiff = ''
        if opts.diff:
            run_pager(rdiff)
        else:
            reqs = get_request_list(apiurl, dst_project, dst_package, req_type='submit', req_state=['new','review'])
            user = conf.get_apiurl_usr(apiurl)
            myreqs = [ i for i in reqs if i.state.who == user ]
            repl = 'y'
            if len(myreqs) > 0 and not opts.yes:
                print('You already created the following submit request: %s.' % \
                      ', '.join([i.reqid for i in myreqs ]))
                repl = raw_input('Supersede the old requests? (y/n/c) ')
                if repl.lower() == 'c':
                    print('Aborting', file=sys.stderr)
                    sys.exit(1)

            actionxml = """<action type="submit"> <source project="%s" package="%s"  rev="%s"/> <target project="%s" package="%s"/> %s </action>"""  % \
                    (src_project, src_package, opts.revision or show_upstream_rev(apiurl, src_project, src_package), dst_project, dst_package, options_block)
            if repl.lower() == 'y':
                for req in myreqs:
                    change_request_state(apiurl, req.reqid, 'superseded',
                                         'superseded by %s' % result, result)

            if opts.supersede:
                change_request_state(apiurl, opts.supersede, 'superseded',  '', result)

            #print 'created request id', result
            return actionxml

    def _delete_request(self, args, opts):
        if len(args) < 1:
            raise oscerr.WrongArgs('Please specify at least a project.')
        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')

        package = ""
        if len(args) > 1:
            package = """package="%s" """ % (args[1])
        actionxml = """<action type="delete"> <target project="%s" %s/> </action> """ % (args[0], package)
        return actionxml

    def _changedevel_request(self, args, opts):
        if len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 0 and is_package_dir('.') and find_default_project():
            wd = os.curdir
            devel_project = store_read_project(wd)
            devel_package = package = store_read_package(wd)
            project = find_default_project(self.get_api_url(), package)
        else:
            if len(args) < 3:
                raise oscerr.WrongArgs('Too few arguments.')

            devel_project = args[2]
            project = args[0]
            package = args[1]
            devel_package = package
            if len(args) > 3:
                devel_package = args[3]

        actionxml = """ <action type="change_devel"> <source project="%s" package="%s" /> <target project="%s" package="%s" /> </action> """ % \
                (devel_project, devel_package, project, package)

        return actionxml

    def _add_me(self, args, opts):
        if len(args) > 3:
            raise oscerr.WrongArgs('Too many arguments.')
        if len(args) < 2:
            raise oscerr.WrongArgs('Too few arguments.')

        apiurl = self.get_api_url()

        user = conf.get_apiurl_usr(apiurl)
        role = args[0]
        project = args[1]
        actionxml = """ <action type="add_role"> <target project="%s" /> <person name="%s" role="%s" /> </action> """ % \
                (project, user, role)

        if len(args) > 2:
            package = args[2]
            actionxml = """ <action type="add_role"> <target project="%s" package="%s" /> <person name="%s" role="%s" /> </action> """ % \
                (project, package, user, role)

        if get_user_meta(apiurl, user) == None:
            raise oscerr.WrongArgs('osc: an error occured.')

        return actionxml

    def _add_user(self, args, opts):
        if len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')
        if len(args) < 3:
            raise oscerr.WrongArgs('Too few arguments.')

        apiurl = self.get_api_url()

        user = args[0]
        role = args[1]
        project = args[2]
        actionxml = """ <action type="add_role"> <target project="%s" /> <person name="%s" role="%s" /> </action> """ % \
                (project, user, role)

        if len(args) > 3:
            package = args[3]
            actionxml = """ <action type="add_role"> <target project="%s" package="%s" /> <person name="%s" role="%s" /> </action> """ % \
                (project, package, user, role)

        if get_user_meta(apiurl, user) == None:
            raise oscerr.WrongArgs('osc: an error occured.')

        return actionxml

    def _add_group(self, args, opts):
        if len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')
        if len(args) < 3:
            raise oscerr.WrongArgs('Too few arguments.')

        apiurl = self.get_api_url()

        group = args[0]
        role = args[1]
        project = args[2]
        actionxml = """ <action type="add_role"> <target project="%s" /> <group name="%s" role="%s" /> </action> """ % \
                (project, group, role)

        if len(args) > 3:
            package = args[3]
            actionxml = """ <action type="add_role"> <target project="%s" package="%s" /> <group name="%s" role="%s" /> </action> """ % \
                (project, package, group, role)

        if get_group(apiurl, group) == None:
            raise oscerr.WrongArgs('osc: an error occured.')

        return actionxml

    def _set_bugowner(self, args, opts):
        if len(args) > 3:
            raise oscerr.WrongArgs('Too many arguments.')
        if len(args) < 2:
            raise oscerr.WrongArgs('Too few arguments.')

        apiurl = self.get_api_url()

        user = args[0]
        project = args[1]
        package = ""
        if len(args) > 2:
            package =  """package="%s" """ % (args[2])

        if user.startswith('group:'):
            group = user.replace('group:','')
            actionxml = """ <action type="set_bugowner"> <target project="%s" %s /> <group name="%s" /> </action> """ % \
                    (project, package, group)
            if get_group(apiurl, group) == None:
                raise oscerr.WrongArgs('osc: an error occured.')
        else:
            actionxml = """ <action type="set_bugowner"> <target project="%s" %s /> <person name="%s" /> </action> """ % \
                    (project, package, user)
            if get_user_meta(apiurl, user) == None:
                raise oscerr.WrongArgs('osc: an error occured.')


        return actionxml

    @cmdln.option('-a', '--action', action='callback', callback = _actionparser,dest = 'actions',
                  help='specify action type of a request, can be : submit/delete/change_devel/add_role/set_bugowner')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-r', '--revision', metavar='REV',
                  help='for "create", specify a certain source revision ID (the md5 sum)')
    @cmdln.option('-s', '--supersede', metavar='SUPERSEDE',
                  help='Superseding another request by this one')
    @cmdln.option('--nodevelproject', action='store_true',
                  help='do not follow a defined devel project ' \
                       '(primary project where a package is developed)')
    @cmdln.option('--cleanup', action='store_true',
                  help='remove package if submission gets accepted (default for home:<id>:branch projects)')
    @cmdln.option('--no-cleanup', action='store_true',
                  help='never remove source package on accept, but update its content')
    @cmdln.option('--no-update', action='store_true',
                  help='never touch source package on accept (will break source links)')
    @cmdln.option('-d', '--diff', action='store_true',
                  help='show diff only instead of creating the actual request')
    @cmdln.option('--yes', action='store_true',
                  help='proceed without asking.')
    @cmdln.alias("creq")
    def do_createrequest(self, subcmd, opts, *args):
        """${cmd_name}: create multiple requests with a single command

        usage:
            osc creq [OPTIONS] [ 
                -a submit SOURCEPRJ SOURCEPKG DESTPRJ [DESTPKG] 
                -a delete PROJECT [PACKAGE] 
                -a change_devel PROJECT PACKAGE DEVEL_PROJECT [DEVEL_PACKAGE] 
                -a add_me ROLE PROJECT [PACKAGE]
                -a add_group GROUP ROLE PROJECT [PACKAGE]
                -a add_role USER ROLE PROJECT [PACKAGE]
                -a set_bugowner USER PROJECT [PACKAGE]
                ]

            Option -m works for all types of request, the rest work only for submit.
        example:
            osc creq -a submit -a delete home:someone:branches:openSUSE:Tools -a change_devel openSUSE:Tools osc home:someone:branches:openSUSE:Tools -m ok

            This will submit all modified packages under current directory, delete project home:someone:branches:openSUSE:Tools and change the devel project to home:someone:branches:openSUSE:Tools for package osc in project openSUSE:Tools.
        ${cmd_option_list}
        """
        src_update = conf.config['submitrequest_on_accept_action'] or None
        # we should check here for home:<id>:branch and default to update, but that would require OBS 1.7 server
        if opts.cleanup:
            src_update = "cleanup"
        elif opts.no_cleanup:
            src_update = "update"
        elif opts.no_update:
            src_update = "noupdate"

        options_block = ""
        if src_update:
            options_block = """<options><sourceupdate>%s</sourceupdate></options> """ % (src_update)

        args = slash_split(args)

        apiurl = self.get_api_url()
        
        i = 0
        actionsxml = ""
        for ai in opts.actions:
            if ai == 'submit':
                args = opts.actiondata[i]
                i = i+1
                actionsxml += self._submit_request(args, opts, options_block)
            elif ai == 'delete':
                args = opts.actiondata[i]
                actionsxml += self._delete_request(args, opts)
                i = i+1
            elif ai == 'change_devel':
                args = opts.actiondata[i]
                actionsxml += self._changedevel_request(args, opts)
                i = i+1
            elif ai == 'add_me':
                args = opts.actiondata[i]
                actionsxml += self._add_me(args, opts)
                i = i+1
            elif ai == 'add_group':
                args = opts.actiondata[i]
                actionsxml += self._add_group(args, opts)
                i = i+1
            elif ai == 'add_role':
                args = opts.actiondata[i]
                actionsxml += self._add_user(args, opts)
                i = i+1
            elif ai == 'set_bugowner':
                args = opts.actiondata[i]
                actionsxml += self._set_bugowner(args, opts)
                i = i+1
            else:
                raise oscerr.WrongArgs('Unsupported action %s' % ai)
        if actionsxml == "":
            sys.exit('No actions need to be taken.')

        if not opts.message:
            opts.message = edit_message()

        import cgi
        xml = """<request> %s <state name="new"/> <description>%s</description> </request> """ % \
              (actionsxml, cgi.escape(opts.message or ""))
        u = makeurl(apiurl, ['request'], query='cmd=create')
        f = http_POST(u, data=xml)

        root = ET.parse(f).getroot()
        return root.get('id')


    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-r', '--role', metavar='role',
                   help='specify user role (default: maintainer)')
    @cmdln.alias("reqbugownership")
    @cmdln.alias("requestbugownership")
    @cmdln.alias("reqmaintainership")
    @cmdln.alias("reqms")
    @cmdln.alias("reqbs")
    def do_requestmaintainership(self, subcmd, opts, *args):
        """${cmd_name}: requests to add user as maintainer or bugowner

        usage:
            osc requestmaintainership                           # for current user in checked out package
            osc requestmaintainership USER                      # for specified user in checked out package
            osc requestmaintainership PROJECT                   # for current user if cwd is not a checked out package
            osc requestmaintainership PROJECT PACKAGE           # for current user
            osc requestmaintainership PROJECT PACKAGE USER      # request for specified user
           
            osc requestbugownership ...                         # accepts same parameters but uses bugowner role 

        ${cmd_option_list}
        """
        import cgi
        args = slash_split(args)
        apiurl = self.get_api_url()

        if len(args) == 2:
            project = args[0]
            package = args[1]
            user = conf.get_apiurl_usr(apiurl)
        elif len(args) == 3:
            project = args[0]
            package = args[1]
            user = args[2]
        elif len(args) < 2 and is_package_dir(os.curdir):
            project = store_read_project(os.curdir)
            package = store_read_package(os.curdir)
            if len(args) == 0:
                user = conf.get_apiurl_usr(apiurl)
            else:
                user = args[0]
        elif len(args) == 1:
            user = conf.get_apiurl_usr(apiurl)
            project = args[0]
            package = None
        else:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        role = 'maintainer'
        if subcmd in ( 'reqbugownership', 'requestbugownership', 'reqbs' ):
            role = 'bugowner'
        if opts.role:
            role = opts.role
        if not role in ('maintainer', 'bugowner'):
            raise oscerr.WrongOptions('invalid \'--role\': either specify \'maintainer\' or \'bugowner\'')
        if not opts.message:
            opts.message = edit_message()

        r = Request()
        if role == 'bugowner':
            r.add_action('set_bugowner', tgt_project=project, tgt_package=package,
              person_name=user)
        else:
            r.add_action('add_role', tgt_project=project, tgt_package=package,
              person_name=user, person_role=role)
        r.description = cgi.escape(opts.message or '')
        r.create(apiurl)
        print(r.reqid)

    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-r', '--repository', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('--accept-in-hours', metavar='TEXT',
                  help='specify message time when request shall get accepted automatically. Only works with write permissions in target.')
    @cmdln.alias("dr")
    @cmdln.alias("dropreq")
    @cmdln.alias("droprequest")
    @cmdln.alias("deletereq")
    def do_deleterequest(self, subcmd, opts, *args):
        """${cmd_name}: Request to delete (or 'drop') a package or project

        usage:
            osc deletereq [-m TEXT]                     # works in checked out project/package
            osc deletereq [-m TEXT] PROJECT [PACKAGE]
            osc deletereq [-m TEXT] PROJECT [--repository REPOSITORY]
        ${cmd_option_list}
        """
        import cgi

        args = slash_split(args)

        project = None
        package = None
        repository = None

        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')
        elif len(args) == 1:
            project = args[0]
        elif len(args) == 2:
            project = args[0]
            package = args[1]
        elif is_project_dir(os.getcwd()):
            project = store_read_project(os.curdir)
        elif is_package_dir(os.getcwd()):
            project = store_read_project(os.curdir)
            package = store_read_package(os.curdir)
        else: 
            raise oscerr.WrongArgs('Please specify at least a project.')

        if opts.repository:
            repository = opts.repository

        if not opts.message:
            import textwrap
            if package is not None:
                footer = textwrap.TextWrapper(width = 66).fill(
                         'please explain why you like to delete package %s of project %s'
                          % (package,project))
            else:
                footer = textwrap.TextWrapper(width = 66).fill(
                         'please explain why you like to delete project %s' % project)
            opts.message = edit_message(footer)

        r = Request()
        r.add_action('delete', tgt_project=project, tgt_package=package, tgt_repository=repository)
        r.description = cgi.escape(opts.message)
        if opts.accept_in_hours:
          r.accept_at_in_hours(int(opts.accept_in_hours))
        r.create(self.get_api_url())
        print(r.reqid)


    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.alias("cr")
    @cmdln.alias("changedevelreq")
    def do_changedevelrequest(self, subcmd, opts, *args):
        """${cmd_name}: Create request to change the devel package definition.

        [See http://en.opensuse.org/openSUSE:Build_Service_Collaboration 
        for information on this topic.]

        See the "request" command for showing and modifing existing requests.

        osc changedevelrequest PROJECT PACKAGE DEVEL_PROJECT [DEVEL_PACKAGE]
        """
        import cgi

        if len(args) == 0 and is_package_dir('.') and find_default_project():
            wd = os.curdir
            devel_project = store_read_project(wd)
            devel_package = package = store_read_package(wd)
            project = find_default_project(self.get_api_url(), package)
        elif len(args) < 3:
            raise oscerr.WrongArgs('Too few arguments.')
        elif len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')
        else:
            devel_project = args[2]
            project = args[0]
            package = args[1]
            devel_package = package
            if len(args) == 4:
                devel_package = args[3]

        if not opts.message:
            import textwrap
            footer = textwrap.TextWrapper(width = 66).fill(
                     'please explain why you like to change the devel project of %s/%s to %s/%s'
                     % (project,package,devel_project,devel_package))
            opts.message = edit_message(footer)

        r = Request()
        r.add_action('change_devel', src_project=devel_project, src_package=devel_package,
            tgt_project=project, tgt_package=package)
        r.description = cgi.escape(opts.message)
        r.create(self.get_api_url())
        print(r.reqid)


    @cmdln.option('-d', '--diff', action='store_true',
                  help='generate a diff')
    @cmdln.option('-u', '--unified', action='store_true',
                  help='output the diff in the unified diff format')
    @cmdln.option('--no-devel', action='store_true',
                  help='Do not attempt to forward to devel project')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-t', '--type', metavar='TYPE',
                  help='limit to requests which contain a given action type (submit/delete/change_devel)')
    @cmdln.option('-a', '--all', action='store_true',
                        help='all states. Same as\'-s all\'')
    @cmdln.option('-f', '--force', action='store_true',
                        help='enforce state change, can be used to ignore open reviews')
    @cmdln.option('-s', '--state', default='',  # default is 'all' if no args given, 'declined,new,review' otherwise
                        help='only list requests in one of the comma separated given states (new/review/accepted/revoked/declined) or "all" [default="declined,new,review", or "all", if no args given]')
    @cmdln.option('-D', '--days', metavar='DAYS',
                        help='only list requests in state "new" or changed in the last DAYS. [default=%(request_list_days)s]')
    @cmdln.option('-U', '--user', metavar='USER',
                        help='requests or reviews limited for the specified USER')
    @cmdln.option('-G', '--group', metavar='GROUP',
                        help='requests or reviews limited for the specified GROUP')
    @cmdln.option('-P', '--project', metavar='PROJECT',
                        help='requests or reviews limited for the specified PROJECT')
    @cmdln.option('-p', '--package', metavar='PACKAGE',
                        help='requests or reviews limited for the specified PACKAGE, requires also a PROJECT')
    @cmdln.option('-b', '--brief', action='store_true', default=False,
                        help='print output in list view as list subcommand')
    @cmdln.option('-M', '--mine', action='store_true',
                        help='only show requests created by yourself')
    @cmdln.option('-B', '--bugowner', action='store_true',
                        help='also show requests about packages where I am bugowner')
    @cmdln.option('-e', '--edit', action='store_true',
                        help='edit a submit action')
    @cmdln.option('-i', '--interactive', action='store_true',
                        help='interactive review of request')
    @cmdln.option('--or-revoke', action='store_true',
                        help='For automatisation scripts: accepts (if using with accept argument) a request when it is in new or review state. Or revoke it when it got declined. Otherwise just do nothing.')
    @cmdln.option('--non-interactive', action='store_true',
                        help='non-interactive review of request')
    @cmdln.option('--exclude-target-project', action='append',
                        help='exclude target project from request list')
    @cmdln.option('--involved-projects', action='store_true',
                        help='show all requests for project/packages where USER is involved')
    @cmdln.option('--source-buildstatus', action='store_true',
                        help='print the buildstatus of the source package (only works with "show")')
    @cmdln.alias("rq")
    @cmdln.alias("review")
    # FIXME: rewrite this mess and split request and review
    def do_request(self, subcmd, opts, *args):
        """${cmd_name}: Show or modify requests and reviews

        [See http://en.opensuse.org/openSUSE:Build_Service_Collaboration
        for information on this topic.]

        The 'request' command has the following sub commands:

        "list" lists open requests attached to a project or package or person.
        Uses the project/package of the current directory if none of
        -M, -U USER, project/package are given.

        "log" will show the history of the given ID

        "show" will show the request itself, and generate a diff for review, if
        used with the --diff option. The keyword show can be omitted if the ID is numeric.

        "decline" will change the request state to "declined"

        "reopen" will set the request back to new or review.

        "setincident" will direct "maintenance" requests into specific incidents

        "supersede" will supersede one request with another existing one.

        "revoke" will set the request state to "revoked"

        "accept" will change the request state to "accepted" and will trigger
        the actual submit process. That would normally be a server-side copy of
        the source package to the target package.

        "checkout" will checkout the request's source package ("submit" requests only).

        The 'review' command has the following sub commands:

        "list" lists open requests that need to be reviewed by the
        specified user or group 

        "add" adds a person or group as reviewer to a request

        "accept" mark the review positive

        "decline" mark the review negative. A negative review will
        decline the request.

        usage:
            osc request list [-M] [-U USER] [-s state] [-D DAYS] [-t type] [-B] [PRJ [PKG]]
            osc request log ID
            osc request [show] [-d] [-b] ID

            osc request accept [-m TEXT] ID
            osc request decline [-m TEXT] ID
            osc request revoke [-m TEXT] ID
            osc request reopen [-m TEXT] ID
            osc request setincident [-m TEXT] ID INCIDENT
            osc request supersede [-m TEXT] ID SUPERSEDING_ID
            osc request approvenew [-m TEXT] PROJECT

            osc request checkout/co ID
            osc request clone [-m TEXT] ID

            osc review show [-d] [-b] ID
            osc review list [-U USER] [-G GROUP] [-P PROJECT [-p PACKAGE]] [-s state]
            osc review add [-m TEXT] [-U USER] [-G GROUP] [-P PROJECT [-p PACKAGE]] ID
            osc review accept [-m TEXT] [-U USER] [-G GROUP] [-P PROJECT [-p PACKAGE]] ID
            osc review decline [-m TEXT] [-U USER] [-G GROUP] [-P PROJECT [-p PACKAGE]] ID
            osc review reopen [-m TEXT] [-U USER] [-G GROUP] [-P PROJECT [-p PACKAGE]] ID
            osc review supersede [-m TEXT] [-U USER] [-G GROUP] [-P PROJECT [-p PACKAGE]] ID SUPERSEDING_ID

        ${cmd_option_list}
        """

        args = slash_split(args)

        if opts.all and opts.state:
            raise oscerr.WrongOptions('Sorry, the options \'--all\' and \'--state\' ' \
                    'are mutually exclusive.')
        if opts.mine and opts.user:
            raise oscerr.WrongOptions('Sorry, the options \'--user\' and \'--mine\' ' \
                    'are mutually exclusive.')
        if opts.interactive and opts.non_interactive:
            raise oscerr.WrongOptions('Sorry, the options \'--interactive\' and ' \
                    '\'--non-interactive\' are mutually exclusive')

        if not args:
            args = [ 'list' ]
            opts.mine = 1
            if opts.state == '':
                opts.state = 'all'

        if opts.state == '':
            opts.state = 'declined,new,review'

        if args[0] == 'help':
            return self.do_help(['help', 'request'])

        cmds = ['list', 'log', 'show', 'decline', 'reopen', 'clone', 'accept', 'approvenew', 'wipe', 'setincident', 'supersede', 'revoke', 'checkout', 'co']
        if subcmd != 'review' and args[0] not in cmds:
            raise oscerr.WrongArgs('Unknown request action %s. Choose one of %s.' \
                                               % (args[0],', '.join(cmds)))
        cmds = ['show', 'list', 'add', 'decline', 'accept', 'reopen', 'supersede']
        if subcmd == 'review' and args[0] not in cmds:
            raise oscerr.WrongArgs('Unknown review action %s. Choose one of %s.' \
                                               % (args[0],', '.join(cmds)))

        cmd = args[0]
        del args[0]

        apiurl = self.get_api_url()

        if cmd in ['list']:
            min_args, max_args = 0, 2
        elif cmd in ['supersede', 'setincident']:
            min_args, max_args = 2, 2
        else:
            min_args, max_args = 1, 1
        if len(args) < min_args:
            raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > max_args:
            raise oscerr.WrongArgs('Too many arguments.')
        if cmd in ['add'] and not opts.user and not opts.group and not opts.project:
            raise oscerr.WrongArgs('No reviewer specified.')

        reqid = None
        supersedid = None
        if cmd == 'list' or cmd == 'approvenew':
            package = None
            project = None
            if len(args) > 0:
                project = args[0]
            elif not opts.mine and not opts.user:
                try:
                    project = store_read_project(os.curdir)
                    package = store_read_package(os.curdir)
                except oscerr.NoWorkingCopy:
                    pass
            elif opts.project:
                project = opts.project
                if opts.package:
                    package = opts.package

            if len(args) > 1:
                package = args[1]
        elif cmd == 'supersede':
            reqid = args[0]
            supersedid = args[1]
        elif cmd == 'setincident':
            reqid = args[0]
            incident = args[1]
        elif cmd in ['log', 'add', 'show', 'decline', 'reopen', 'clone', 'accept', 'wipe', 'revoke', 'checkout', 'co']:
            reqid = args[0]

        # clone all packages from a given request
        if cmd in ['clone']:
            # should we force a message?
            print('Cloned packages are available in project: %s' % clone_request(apiurl, reqid, opts.message))

        # change incidents
        elif cmd == 'setincident':
            query = { 'cmd': 'setincident', 'incident': incident }
            url = makeurl(apiurl, ['request', reqid], query)
            r = http_POST(url, data=opts.message)
            print(ET.parse(r).getroot().get('code'))

        # add new reviewer to existing request
        elif cmd in ['add'] and subcmd == 'review':
            query = { 'cmd': 'addreview' }
            if opts.user:
                query['by_user'] = opts.user
            if opts.group:
                query['by_group'] = opts.group
            if opts.project:
                query['by_project'] = opts.project
            if opts.package:
                query['by_package'] = opts.package
            url = makeurl(apiurl, ['request', reqid], query)
            if not opts.message:
                opts.message = edit_message()
            r = http_POST(url, data=opts.message)
            print(ET.parse(r).getroot().get('code'))

        # list and approvenew
        elif cmd == 'list' or cmd == 'approvenew':
            states = ('new', 'accepted', 'revoked', 'declined', 'review', 'superseded')
            who = ''
            if cmd == 'approvenew':
                states = ('new')
                results = get_request_list(apiurl, project, package, '', ['new'])
            else:
                state_list = opts.state.split(',')
                if opts.all:
                    state_list = ['all']
                if subcmd == 'review':
                    # is there a special reason why we do not respect the passed states?
                    state_list = ['new']
                elif opts.state == 'all':
                    state_list = ['all']
                else:
                    for s in state_list:
                        if not s in states and not s == 'all':
                            raise oscerr.WrongArgs('Unknown state \'%s\', try one of %s' % (s, ','.join(states)))
                if opts.mine:
                    who = conf.get_apiurl_usr(apiurl)
                if opts.user:
                    who = opts.user

                ## FIXME -B not implemented!
                if opts.bugowner:
                    if (self.options.debug):
                        print('list: option --bugowner ignored: not impl.')

                if subcmd == 'review':
                    # FIXME: do the review list for the user and for all groups he belong to
                    results = get_review_list(apiurl, project, package, who, opts.group, opts.project, opts.package, state_list)
                else:
                    if opts.involved_projects:
                        who = who or conf.get_apiurl_usr(apiurl)
                        results = get_user_projpkgs_request_list(apiurl, who, req_state=state_list,
                                                                 req_type=opts.type, exclude_projects=opts.exclude_target_project or [])
                    else:
                        results = get_request_list(apiurl, project, package, who,
                                                   state_list, opts.type, opts.exclude_target_project or [])

            # Check if project actually exists if result list is empty
            if not results:
                if project:
                    try:
                        show_project_meta(apiurl, project)
                        print('No results for {0}'.format(project))
                    except HTTPError:
                        print('Project {0} does not exist'.format(project))
                else:
                    print('No results')
                return

            results.sort(reverse=True)
            days = opts.days or conf.config['request_list_days']
            since = ''
            try:
                days = float(days)
            except ValueError:
                days = 0
            if days > 0:
                since = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()-days*24*3600))

            skipped = 0
            ## bs has received 2009-09-20 a new xquery compare() function
            ## which allows us to limit the list inside of get_request_list
            ## That would be much faster for coolo. But counting the remainder
            ## would not be possible with current xquery implementation.
            ## Workaround: fetch all, and filter on client side.

            ## FIXME: date filtering should become implemented on server side
            for result in results:
                if days == 0 or result.state.when > since or result.state.name == 'new':
                    if (opts.interactive or conf.config['request_show_interactive']) and not opts.non_interactive:
                        ignore_reviews = subcmd != 'review'
                        request_interactive_review(apiurl, result, group=opts.group, ignore_reviews=ignore_reviews)
                    else:
                        print(result.list_view(), '\n')
                else:
                    skipped += 1
            if skipped:
                print("There are %d requests older than %s days.\n" % (skipped, days))

            if cmd == 'approvenew':
                print("\n *** Approve them all ? [y/n] ***")
                if sys.stdin.read(1) == "y":
    
                    if not opts.message:
                        opts.message = edit_message()
                    for result in results:
                        print(result.reqid, ": ", end=' ')
                        r = change_request_state(apiurl,
                                result.reqid, 'accepted', opts.message or '', force=opts.force)
                        print('Result of change request state: %s' % r)
                else:
                    print('Aborted...', file=sys.stderr)
                    raise oscerr.UserAbort()

        elif cmd == 'log':
            for l in get_request_log(apiurl, reqid):
                print(l)

        # show
        elif cmd == 'show':
            r = get_request(apiurl, reqid)
            if opts.brief:
                print(r.list_view())
            elif opts.edit:
                if not r.get_actions('submit'):
                    raise oscerr.WrongOptions('\'--edit\' not possible ' \
                        '(request has no \'submit\' action)')
                return request_interactive_review(apiurl, r, 'e')
            elif (opts.interactive or conf.config['request_show_interactive']) and not opts.non_interactive:
                ignore_reviews = subcmd != 'review'
                return request_interactive_review(apiurl, r, group=opts.group, ignore_reviews=ignore_reviews)
            else:
                print(r)
            if opts.source_buildstatus:
                sr_actions = r.get_actions('submit')
                if not sr_actions:
                    raise oscerr.WrongOptions( '\'--source-buildstatus\' not possible ' \
                        '(request has no \'submit\' actions)')
                for action in sr_actions:
                    print('Buildstatus for \'%s/%s\':' % (action.src_project, action.src_package))
                    print('\n'.join(get_results(apiurl, action.src_project, action.src_package)))
            if opts.diff:
                diff = ''
                try:
                    # works since OBS 2.1
                    diff = request_diff(apiurl, reqid)
                except HTTPError as e:
                    # for OBS 2.0 and before
                    sr_actions = r.get_actions('submit')
                    if not sr_actions:
                        raise oscerr.WrongOptions('\'--diff\' not possible (request has no \'submit\' actions)')
                    for action in sr_actions:
                        diff += 'old: %s/%s\nnew: %s/%s\n' % (action.src_project, action.src_package,
                            action.tgt_project, action.tgt_package)
                        diff += submit_action_diff(apiurl, action)
                        diff += '\n\n'
                run_pager(diff, tmp_suffix='')

        # checkout
        elif cmd == 'checkout' or cmd == 'co':
            r = get_request(apiurl, reqid)
            sr_actions = r.get_actions('submit', 'maintenance_release')
            if not sr_actions:
                raise oscerr.WrongArgs('\'checkout\' not possible (request has no \'submit\' actions)')
            for action in sr_actions:
                checkout_package(apiurl, action.src_project, action.src_package, \
                    action.src_rev, expand_link=True, prj_dir=action.src_project)

        else:
            state_map = {'reopen' : 'new', 'accept' : 'accepted', 'decline' : 'declined', 'wipe' : 'deleted', 'revoke' : 'revoked', 'supersede' : 'superseded'}
            # Change review state only
            if subcmd == 'review':
                if not opts.message:
                    opts.message = edit_message()
                if cmd in ['accept', 'decline', 'reopen', 'supersede']:
                    if opts.user or opts.group or opts.project or opts.package:
                        r = change_review_state(apiurl, reqid, state_map[cmd], opts.user, opts.group, opts.project,
                                opts.package, opts.message or '', supersed=supersedid)
                        print(r)
                    else:
                        rq = get_request(apiurl, reqid)
                        if rq.state.name in ['new', 'review']:
                            for review in rq.reviews:  # try all, but do not fail on error
                                try:
                                    r = change_review_state(apiurl, reqid, state_map[cmd], review.by_user, review.by_group,
                                            review.by_project, review.by_package, opts.message or '', supersed=supersedid)
                                    print(r)
                                except HTTPError as e:
                                    body = e.read()
                                    if e.code in [403]:
                                       if review.by_user:
                                           print('No permission on review by user %s' % review.by_user)
                                       if review.by_group:
                                           print('No permission on review by group %s' % review.by_group)
                                       if review.by_package:
                                           print('No permission on review by package %s / %s' % (review.by_project, review.by_package))
                                       elif review.by_project:
                                           print('No permission on review by project %s' % review.by_project)
                                    else:
                                        print(e, file=sys.stderr)
                        else:
                            print('Request is closed, please reopen the request first before changing any reviews.')
            # Change state of entire request
            elif cmd in ['reopen', 'accept', 'decline', 'wipe', 'revoke', 'supersede']:
                rq = get_request(apiurl, reqid)
                if opts.or_revoke:
                    if rq.state.name == "declined":
                        cmd = "revoke"
                    elif rq.state.name != "new" and rq.state.name != "review":
                        return 0
                if rq.state.name == state_map[cmd]:
                    repl = raw_input("\n *** The state of the request (#%s) is already '%s'. Change state anyway?  [y/n] *** " % \
                                     (reqid, rq.state.name))
                    if repl.lower() != 'y':
                        print('Aborted...', file=sys.stderr)
                        raise oscerr.UserAbort()
                                            
                if not opts.message:
                    tmpl = change_request_state_template(rq, state_map[cmd])
                    opts.message = edit_message(template=tmpl)
                try:
                    r = change_request_state(apiurl,
                             reqid, state_map[cmd], opts.message or '', supersed=supersedid, force=opts.force)
                    print('Result of change request state: %s' % r)
                except HTTPError as e:
                    print(e, file=sys.stderr)
                    details = e.headers.get('X-Opensuse-Errorcode')
                    if details:
                        print(details, file=sys.stderr)
                    root = ET.fromstring(e.read())
                    summary = root.find('summary')
                    if not summary is None:
                        print(summary.text)
                    if opts.or_revoke:
                        if e.code in [ 400, 403, 404, 500 ]:
                            print('Revoking it ...')
                            r = change_request_state(apiurl,
                                reqid, 'revoked', opts.message or '', supersed=supersedid, force=opts.force)
                    sys.exit(1)


                # check for devel instances after accepted requests
                if cmd in ['accept']:
                    import cgi
                    sr_actions = rq.get_actions('submit')
                    for action in sr_actions:
                        u = makeurl(apiurl, ['/search/package'], {
                              'match' : "([devel/[@project='%s' and @package='%s']])" % (action.tgt_project, action.tgt_package)
                              })
                        f = http_GET(u)
                        root = ET.parse(f).getroot()
                        if root.findall('package') and not opts.no_devel:
                            for node in root.findall('package'):
                                project = node.get('project')
                                package = node.get('name')
                                # skip it when this is anyway a link to me
                                link_url = makeurl(apiurl, ['source', project, package])
                                links_to_project = links_to_package = None
                                try:
                                    file = http_GET(link_url)
                                    root = ET.parse(file).getroot()
                                    link_node = root.find('linkinfo')
                                    if link_node != None:
                                        links_to_project = link_node.get('project') or project
                                        links_to_package = link_node.get('package') or package
                                except HTTPError as e:
                                    if e.code != 404:
                                        print('Cannot get list of files for %s/%s: %s' % (project, package, e), file=sys.stderr)
                                except SyntaxError as e:
                                    print('Cannot parse list of files for %s/%s: %s' % (project, package, e), file=sys.stderr)
                                if links_to_project == action.tgt_project and links_to_package == action.tgt_package:
                                    # links to my request target anyway, no need to forward submit
                                    continue

                                print(project, end=' ')
                                if package != action.tgt_package:
                                    print("/", package, end=' ')
                                repl = raw_input('\nForward this submit to it? ([y]/n)')
                                if repl.lower() == 'y' or repl == '':
                                    (supersede, reqs) = check_existing_requests(apiurl, action.tgt_project, action.tgt_package,
                                                                                project, package)
                                    msg = "%s (forwarded request %s from %s)" % (rq.description, reqid, rq.get_creator())
                                    rid = create_submit_request(apiurl, action.tgt_project, action.tgt_package,
                                                                project, package, cgi.escape(msg))
                                    print(msg)
                                    print("New request #", rid)
                                    for req in reqs:
                                        change_request_state(apiurl, req.reqid, 'superseded',
                                                             'superseded by %s' % rid, rid)

    # editmeta and its aliases are all depracated
    @cmdln.alias("editprj")
    @cmdln.alias("createprj")
    @cmdln.alias("editpac")
    @cmdln.alias("createpac")
    @cmdln.alias("edituser")
    @cmdln.alias("usermeta")
    @cmdln.hide(1)
    def do_editmeta(self, subcmd, opts, *args):
        """${cmd_name}:

        Obsolete command to edit metadata. Use 'meta' now.

        See the help output of 'meta'.

        """

        print('This command is obsolete. Use \'osc meta <metatype> ...\'.', file=sys.stderr)
        print('See \'osc help meta\'.', file=sys.stderr)
        #self.do_help([None, 'meta'])
        return 2


    @cmdln.option('-r', '--revision', metavar='rev',
                  help='use the specified revision.')
    @cmdln.option('-R', '--use-plain-revision', action='store_true',
                  help='Do not expand revision the specified or latest rev')
    @cmdln.option('-u', '--unset', action='store_true',
                  help='remove revision in link, it will point always to latest revision')
    def do_setlinkrev(self, subcmd, opts, *args):
        """${cmd_name}: Updates a revision number in a source link.

        This command adds or updates a specified revision number in a source link.
        The current revision of the source is used, if no revision number is specified.

        usage:
            osc setlinkrev
            osc setlinkrev PROJECT [PACKAGE]
        ${cmd_option_list}
        """

        args = slash_split(args)
        apiurl = self.get_api_url()
        package = None
        rev = parseRevisionOption(opts.revision)[0] or ''
        if opts.unset:
            rev = None

        if len(args) == 0:
            p = findpacs(os.curdir)[0]
            project = p.prjname
            package = p.name
            apiurl = p.apiurl
            if not p.islink():
                sys.exit('Local directory is no checked out source link package, aborting')
        elif len(args) == 2:
            project = args[0]
            package = args[1]
        elif len(args) == 1:
            project = args[0]
        else:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('setlinkrev'))

        if package:
            packages = [package]
        else:
            packages = meta_get_packagelist(apiurl, project)

        for p in packages:
            rev = set_link_rev(apiurl, project, p, revision=rev,
                               expand=not opts.use_plain_revision)
            if rev is None:
                print('removed revision from link')
            else:
                print('set revision to %s for package %s' % (rev, p))


    def do_linktobranch(self, subcmd, opts, *args):
        """${cmd_name}: Convert a package containing a classic link with patch to a branch

        This command tells the server to convert a _link with or without a project.diff
        to a branch. This is a full copy with a _link file pointing to the branched place.

        usage:
            osc linktobranch                    # can be used in checked out package
            osc linktobranch PROJECT PACKAGE
        ${cmd_option_list}
        """
        args = slash_split(args)
        apiurl = self.get_api_url()

        if len(args) == 0:
            wd = os.curdir
            project = store_read_project(wd)
            package = store_read_package(wd)
            update_local_dir = True
        elif len(args) < 2:
            raise oscerr.WrongArgs('Too few arguments (required none or two)')
        elif len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments (required none or two)')
        else:
            project = args[0]
            package = args[1]
            update_local_dir = False

        # execute
        link_to_branch(apiurl, project, package)
        if update_local_dir:
            pac = Package(wd)
            pac.update(rev=pac.latest_rev())


    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    def do_detachbranch(self, subcmd, opts, *args):
        """${cmd_name}: replace a link with its expanded sources

        If a package is a link it is replaced with its expanded sources. The link
        does not exist anymore.

        usage:
            osc detachbranch                    # can be used in package working copy
            osc detachbranch PROJECT PACKAGE
        ${cmd_option_list}
        """
        args = slash_split(args)
        apiurl = self.get_api_url()
        if len(args) == 0:
            project = store_read_project(os.curdir)
            package = store_read_package(os.curdir)
        elif len(args) == 2:
            project, package = args
        elif len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments (required none or two)')
        else:
            raise oscerr.WrongArgs('Too few arguments (required none or two)')

        try:
            copy_pac(apiurl, project, package, apiurl, project, package, expand=True, comment=opts.message)
        except HTTPError as e:
            root = ET.fromstring(show_files_meta(apiurl, project, package, 'latest', expand=False))
            li = Linkinfo()
            li.read(root.find('linkinfo'))
            if li.islink() and li.haserror():
                raise oscerr.LinkExpandError(project, package, li.error)
            elif not li.islink():
                print('package \'%s/%s\' is no link' % (project, package), file=sys.stderr)
            else:
                raise e


    @cmdln.option('-C', '--cicount', choices=['add', 'copy', 'local'],
                  help='cicount attribute in the link, known values are add, copy, and local, default in buildservice is currently add.')
    @cmdln.option('-c', '--current', action='store_true',
                  help='link fixed against current revision.')
    @cmdln.option('-r', '--revision', metavar='rev',
                  help='link the specified revision.')
    @cmdln.option('-f', '--force', action='store_true',
                  help='overwrite an existing link file if it is there.')
    @cmdln.option('-d', '--disable-publish', action='store_true',
                  help='disable publishing of the linked package')
    @cmdln.option('-N', '--new-package', action='store_true',
                  help='create a link to a not yet existing package')
    def do_linkpac(self, subcmd, opts, *args):
        """${cmd_name}: "Link" a package to another package

        A linked package is a clone of another package, but plus local
        modifications. It can be cross-project.

        The DESTPAC name is optional; the source packages' name will be used if
        DESTPAC is omitted.

        Afterwards, you will want to 'checkout DESTPRJ DESTPAC'.

        To add a patch, add the patch as file and add it to the _link file.
        You can also specify text which will be inserted at the top of the spec file.

        See the examples in the _link file.

        NOTE: In case you want to fix or update another package, you should use the 'branch'
              command. A branch has correct repositories (and a link) setup up by default and
              will be cleaned up automatically after it was submitted back.

        usage:
            osc linkpac SOURCEPRJ SOURCEPAC DESTPRJ [DESTPAC]
        ${cmd_option_list}
        """

        args = slash_split(args)
        apiurl = self.get_api_url()

        if not args or len(args) < 3:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('linkpac'))

        rev, dummy = parseRevisionOption(opts.revision)
        vrev = None

        src_project = args[0]
        src_package = args[1]
        dst_project = args[2]
        if len(args) > 3:
            dst_package = args[3]
        else:
            dst_package = src_package

        if src_project == dst_project and src_package == dst_package:
            raise oscerr.WrongArgs('Error: source and destination are the same.')

        if src_project == dst_project and not opts.cicount:
            # in this case, the user usually wants to build different spec
            # files from the same source
            opts.cicount = "copy"

        if opts.current and not opts.new_package:
            rev, vrev = show_upstream_rev_vrev(apiurl, src_project, src_package, expand=True)
            if rev == None or len(rev) < 32:
                # vrev is only needed for srcmd5 and OBS instances < 2.1.17 do not support it
                vrev = None

        if rev and not checkRevision(src_project, src_package, rev):
            print('Revision \'%s\' does not exist' % rev, file=sys.stderr)
            sys.exit(1)

        link_pac(src_project, src_package, dst_project, dst_package, opts.force, rev, opts.cicount, opts.disable_publish, opts.new_package, vrev)

    @cmdln.option('--nosources', action='store_true',
                  help='ignore source packages when copying build results to destination project')
    @cmdln.option('-m', '--map-repo', metavar='SRC=TARGET[,SRC=TARGET]',
                  help='Allows repository mapping(s) to be given as SRC=TARGET[,SRC=TARGET]')
    @cmdln.option('-d', '--disable-publish', action='store_true',
                  help='disable publishing of the aggregated package')
    def do_aggregatepac(self, subcmd, opts, *args):
        """${cmd_name}: "Aggregate" a package to another package

        Aggregation of a package means that the build results (binaries) of a
        package are basically copied into another project.
        This can be used to make packages available from building that are
        needed in a project but available only in a different project. Note
        that this is done at the expense of disk space. See
        http://en.opensuse.org/openSUSE:Build_Service_Tips_and_Tricks#link_and_aggregate
        for more information.

        The DESTPAC name is optional; the source packages' name will be used if
        DESTPAC is omitted.

        usage:
            osc aggregatepac SOURCEPRJ SOURCEPAC DESTPRJ [DESTPAC]
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or len(args) < 3:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('aggregatepac'))

        src_project = args[0]
        src_package = args[1]
        dst_project = args[2]
        if len(args) > 3:
            dst_package = args[3]
        else:
            dst_package = src_package

        if src_project == dst_project and src_package == dst_package:
            raise oscerr.WrongArgs('Error: source and destination are the same.')

        repo_map = {}
        if opts.map_repo:
            for pair in opts.map_repo.split(','):
                src_tgt = pair.split('=')
                if len(src_tgt) != 2:
                    raise oscerr.WrongOptions('map "%s" must be SRC=TARGET[,SRC=TARGET]' % opts.map_repo)
                repo_map[src_tgt[0]] = src_tgt[1]

        aggregate_pac(src_project, src_package, dst_project, dst_package, repo_map, opts.disable_publish, opts.nosources)


    @cmdln.option('-c', '--client-side-copy', action='store_true',
                        help='do a (slower) client-side copy')
    @cmdln.option('-k', '--keep-maintainers', action='store_true',
                        help='keep original maintainers. Default is remove all and replace with the one calling the script.')
    @cmdln.option('-K', '--keep-link', action='store_true',
                        help='keep the source link in target, this also expands the source')
    @cmdln.option('-d', '--keep-develproject', action='store_true',
                        help='keep develproject tag in the package metadata')
    @cmdln.option('-r', '--revision', metavar='rev',
                        help='copy the specified revision.')
    @cmdln.option('-t', '--to-apiurl', metavar='URL',
                        help='URL of destination api server. Default is the source api server.')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify message TEXT')
    @cmdln.option('-e', '--expand', action='store_true',
                        help='if the source package is a link then copy the expanded version of the link')
    def do_copypac(self, subcmd, opts, *args):
        """${cmd_name}: Copy a package

        A way to copy package to somewhere else.

        It can be done across buildservice instances, if the -t option is used.
        In that case, a client-side copy and link expansion are implied.

        Using --client-side-copy always involves downloading all files, and
        uploading them to the target.

        The DESTPAC name is optional; the source packages' name will be used if
        DESTPAC is omitted.

        usage:
            osc copypac SOURCEPRJ SOURCEPAC DESTPRJ [DESTPAC]
        ${cmd_option_list}
        """

        args = slash_split(args)

        if not args or len(args) < 3:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('copypac'))

        src_project = args[0]
        src_package = args[1]
        dst_project = args[2]
        if len(args) > 3:
            dst_package = args[3]
        else:
            dst_package = src_package

        src_apiurl = conf.config['apiurl']
        if opts.to_apiurl:
            dst_apiurl = conf.config['apiurl_aliases'].get(opts.to_apiurl, opts.to_apiurl)
        else:
            dst_apiurl = src_apiurl

        if src_apiurl != dst_apiurl:
            opts.client_side_copy = True
            opts.expand = True

        rev, dummy = parseRevisionOption(opts.revision)

        if opts.message:
            comment = opts.message
        else:
            if not rev:
                rev = show_upstream_rev(src_apiurl, src_project, src_package)
            comment = 'osc copypac from project:%s package:%s revision:%s' % ( src_project, src_package, rev )
            if opts.keep_link:
                comment += ", using keep-link"
            if opts.expand:
                comment += ", using expand"
            if opts.client_side_copy:
                comment += ", using client side copy"

        if src_project == dst_project and \
           src_package == dst_package and \
           not rev and \
           src_apiurl == dst_apiurl:
            raise oscerr.WrongArgs('Source and destination are the same.')

        r = copy_pac(src_apiurl, src_project, src_package,
                     dst_apiurl, dst_project, dst_package,
                     client_side_copy=opts.client_side_copy,
                     keep_maintainers=opts.keep_maintainers,
                     keep_develproject=opts.keep_develproject,
                     expand=opts.expand,
                     revision=rev,
                     comment=comment,
                     keep_link=opts.keep_link)
        print(r)


    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='Release only binaries from the specified repository')
    @cmdln.option('--target-project', metavar='TARGETPROJECT',
                  help='Release only to specified project')
    @cmdln.option('--target-repository', metavar='TARGETREPOSITORY',
                  help='Release only to specified repository')
    @cmdln.option('--set-release', metavar='RELEASETAG',
                  help='rename binaries during release using this release tag')
    def do_release(self, subcmd, opts, *args):
        """${cmd_name}: Release sources and binaries 

        This command is used to transfer sources and binaries without rebuilding them.
        It requires defined release targets set to trigger="manual". Please refer the
        release management chapter in the OBS book for details.

        usage:
            osc release [ SOURCEPROJECT [ SOURCEPACKAGE ] ]

        ${cmd_option_list}
        """
       
        args = slash_split(args)
        apiurl = self.get_api_url()

        source_project = source_package = None

        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 0:
            if is_project_dir(os.curdir):
               source_project = store_read_project(os.curdir)
            elif is_package_dir(os.curdir):
               source_package = store_read_package(wd)
            else:
               raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > 0:
            source_project = args[0]
        if len(args) > 1:
            source_package = args[1]

        query = { 'cmd': 'release' }
        if opts.target_project:
            query["targetproject"] = opts.target_project
        if opts.target_repository:
            query["targetrepository"] = opts.target_repository
        if opts.set_release:
            query["setrelease"] = opts.set_release
        baseurl = ['source', source_project]
        if source_package:
            baseurl.append(source_package)
        url = makeurl(apiurl, baseurl, query=query)
        f = http_POST(url)
        while True:
            buf = f.read(16384)
            if not buf:
                break
            sys.stdout.write(buf)


    @cmdln.option('-m', '--message', metavar='TEXT',
                        help='specify message TEXT')
    def do_releaserequest(self, subcmd, opts, *args):
        """${cmd_name}: Create a request for releasing a maintenance update.

        [See http://doc.opensuse.org/products/draft/OBS/obs-reference-guide_draft/cha.obs.maintenance_setup.html
         for information on this topic.]

        This command is used by the maintence team to start the release process of a maintenance update.
        This includes usually testing based on the defined reviewers of the update project.

        usage:
            osc releaserequest [ SOURCEPROJECT ]

        ${cmd_option_list}
        """
       
        # FIXME: additional parameters can be a certain repo list to create a partitial release

        args = slash_split(args)
        apiurl = self.get_api_url()

        source_project = None

        if len(args) > 1:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 0 and is_project_dir(os.curdir):
            source_project = store_read_project(os.curdir)
        elif len(args) == 0:
            raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > 0:
            source_project = args[0]

        if not opts.message:
            opts.message = edit_message()

        r = create_release_request(apiurl, source_project, opts.message)
        print(r.reqid)



    @cmdln.option('-a', '--attribute', metavar='ATTRIBUTE',
                        help='Use this attribute to find default maintenance project (default is OBS:MaintenanceProject)')
    @cmdln.option('--noaccess', action='store_true',
                        help='Create a hidden project')
    @cmdln.option('-m', '--message', metavar='TEXT',
                        help='specify message TEXT')
    def do_createincident(self, subcmd, opts, *args):
        """${cmd_name}: Create a maintenance incident

        [See http://doc.opensuse.org/products/draft/OBS/obs-reference-guide_draft/cha.obs.maintenance_setup.html
        for information on this topic.]

        This command is asking to open an empty maintence incident. This can usually only be done by a responsible
        maintenance team.
        Please see the "mbranch" command on how to full such a project content and
        the "patchinfo" command how add the required maintenance update information.

        usage:
            osc createincident [ MAINTENANCEPROJECT ]
        ${cmd_option_list}
        """

        args = slash_split(args)
        apiurl = self.get_api_url()
        maintenance_attribute = conf.config['maintenance_attribute']
        if opts.attribute:
            maintenance_attribute = opts.attribute

        source_project = target_project = None

        if len(args) > 1:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 1:
            target_project = args[0]
        else:
            xpath = 'attribute/@name = \'%s\'' % maintenance_attribute
            res = search(apiurl, project_id=xpath)
            root = res['project_id']
            project = root.find('project')
            if project is None:
                sys.exit('Unable to find defined OBS:MaintenanceProject project on server.')
            target_project = project.get('name')
            print('Using target project \'%s\'' % target_project)

        query = { 'cmd': 'createmaintenanceincident' }
        if opts.noaccess:
            query["noaccess"] = 1
        url = makeurl(apiurl, ['source', target_project], query=query)
        r = http_POST(url, data=opts.message)
        project = None
        for i in ET.fromstring(r.read()).findall('data'):
            if i.get('name') == 'targetproject':
                project = i.text.strip()
        if project:
            print("Incident project created: ", project)
        else:
            print(ET.parse(r).getroot().get('code'))
            print(ET.parse(r).getroot().get('error'))


    @cmdln.option('-a', '--attribute', metavar='ATTRIBUTE',
                        help='Use this attribute to find default maintenance project (default is OBS:MaintenanceProject)')
    @cmdln.option('-m', '--message', metavar='TEXT',
                        help='specify message TEXT')
    @cmdln.option('--no-cleanup', action='store_true',
                  help='do not remove source project on accept')
    @cmdln.option('--cleanup', action='store_true',
                  help='do remove source project on accept')
    @cmdln.option('--incident', metavar='INCIDENT',
                        help='specify incident number to merge in')
    @cmdln.option('--incident-project', metavar='INCIDENT_PROJECT',
                        help='specify incident project to merge in')
    @cmdln.alias("mr")
    def do_maintenancerequest(self, subcmd, opts, *args):
        """${cmd_name}: Create a request for starting a maintenance incident.

        [See http://doc.opensuse.org/products/draft/OBS/obs-reference-guide_draft/cha.obs.maintenance_setup.html
        for information on this topic.]

        This command is asking the maintence team to start a maintence incident based on a
        created maintenance update. Please see the "mbranch" command on how to create such a project and
        the "patchinfo" command how add the required maintenance update information.

        usage:
            osc maintenancerequest [ SOURCEPROJECT [ SOURCEPACKAGES RELEASEPROJECT ] ]
        ${cmd_option_list}
        """

        args = slash_split(args)
        apiurl = self.get_api_url()
        maintenance_attribute = conf.config['maintenance_attribute']
        if opts.attribute:
            maintenance_attribute = opts.attribute

        source_project = source_packages = target_project = release_project = opt_sourceupdate = None

        if len(args) == 0 and (is_project_dir(os.curdir) or is_package_dir(os.curdir)):
            source_project = store_read_project(os.curdir)
        elif len(args) == 0:
            raise oscerr.WrongArgs('Too few arguments.')
        if len(args) > 0:
            source_project = args[0]
        if len(args) > 1:
            if len(args) == 2:
                sys.exit('Source package defined, but no release project.')
            source_packages = args[1:]
            release_project = args[-1]
            source_packages.remove(release_project)
        if opts.cleanup:
            opt_sourceupdate = 'cleanup'
        if not opts.no_cleanup:
            default_branch = 'home:%s:branches:' % (conf.get_apiurl_usr(apiurl))
            if source_project.startswith(default_branch):
                opt_sourceupdate = 'cleanup'

        if opts.incident_project:
            target_project = opts.incident_project
        else:
            xpath = 'attribute/@name = \'%s\'' % maintenance_attribute
            res = search(apiurl, project_id=xpath)
            root = res['project_id']
            project = root.find('project')
            if project is None:
                sys.exit('Unable to find defined OBS:MaintenanceProject project on server.')
            target_project = project.get('name')
            if opts.incident:
                target_project += ":" + opts.incident
            print('Using target project \'%s\'' % target_project)

        if not opts.message:
            opts.message = edit_message()

        r = create_maintenance_request(apiurl, source_project, source_packages, target_project, release_project, opt_sourceupdate, opts.message)
        print(r.reqid)


    @cmdln.option('-c', '--checkout', action='store_true',
                        help='Checkout branched package afterwards ' \
                                '(\'osc bco\' is a shorthand for this option)' )
    @cmdln.option('-a', '--attribute', metavar='ATTRIBUTE',
                        help='Use this attribute to find affected packages (default is OBS:Maintained)')
    @cmdln.option('-u', '--update-project-attribute', metavar='UPDATE_ATTRIBUTE',
                        help='Use this attribute to find update projects (default is OBS:UpdateProject) ')
    @cmdln.option('--dryrun', action='store_true',
                        help='Just simulate the action and report back the result.')
    @cmdln.option('--noaccess', action='store_true',
                        help='Create a hidden project')
    @cmdln.option('--nodevelproject', action='store_true',
                        help='do not follow a defined devel project ' \
                             '(primary project where a package is developed)')
    @cmdln.alias('sm')
    @cmdln.alias('maintained')
    def do_mbranch(self, subcmd, opts, *args):
        """${cmd_name}: Search or banch multiple instances of a package

        This command is used for searching all relevant instances of packages
        and creating links of them in one project.
        This is esp. used for maintenance updates. It can also be used to branch
        all packages marked before with a given attribute.

        [See http://en.opensuse.org/openSUSE:Build_Service_Concept_Maintenance
        for information on this topic.]

        The branched package will live in
            home:USERNAME:branches:ATTRIBUTE:PACKAGE
        if nothing else specified.

        usage:
            osc sm [SOURCEPACKAGE] [-a ATTRIBUTE]
            osc mbranch [ SOURCEPACKAGE [ TARGETPROJECT ] ]
        ${cmd_option_list}
        """
        args = slash_split(args)
        apiurl = self.get_api_url()
        tproject = None

        maintained_attribute = conf.config['maintained_attribute']
        if opts.attribute:
            maintained_attribute = opts.attribute
        maintained_update_project_attribute = conf.config['maintained_update_project_attribute']
        if opts.update_project_attribute:
            maintained_update_project_attribute = opts.update_project_attribute

        if not len(args) or len(args) > 2:
            raise oscerr.WrongArgs('Wrong number of arguments.')
        if len(args) >= 1:
            package = args[0]
        if len(args) >= 2:
            tproject = args[1]

        if subcmd == 'sm' or subcmd == 'maintained':
            opts.dryrun = 1

        result = attribute_branch_pkg(apiurl, maintained_attribute, maintained_update_project_attribute, \
                                 package, tproject, noaccess = opts.noaccess, nodevelproject=opts.nodevelproject, dryrun=opts.dryrun)

        if result is None:
            print('ERROR: Attribute branch call came not back with a project.', file=sys.stderr)
            sys.exit(1)

        if opts.dryrun:
            for r in result.findall('package'):
                print("%s/%s"%(r.get('project'), r.get('package')))
            return
        
        apiopt = ''
        if conf.get_configParser().get('general', 'apiurl') != apiurl:
            apiopt = '-A %s ' % apiurl
        print('A working copy of the maintenance branch can be checked out with:\n\n' \
              'osc %sco %s' \
                    % (apiopt, result))

        if opts.checkout:
            Project.init_project(apiurl, result, result, conf.config['do_package_tracking'])
            print(statfrmt('A', result))

            # all packages
            for package in meta_get_packagelist(apiurl, result):
                try:
                    checkout_package(apiurl, result, package, expand_link = True, prj_dir = result)
                except:
                    print('Error while checkout package:\n', package, file=sys.stderr)

            if conf.config['verbose']:
                print('Note: You can use "osc delete" or "osc submitpac" when done.\n')


    @cmdln.alias('branchco')
    @cmdln.alias('bco')
    @cmdln.alias('getpac')
    @cmdln.option('--nodevelproject', action='store_true',
                        help='do not follow a defined devel project ' \
                             '(primary project where a package is developed)')
    @cmdln.option('-c', '--checkout', action='store_true',
                        help='Checkout branched package afterwards using "co -e -S"' \
                                '(\'osc bco\' is a shorthand for this option)' )
    @cmdln.option('-f', '--force', default=False, action="store_true",
                  help='force branch, overwrite target')
    @cmdln.option('--add-repositories', default=False, action="store_true",
                  help='Add repositories to target project (happens by default when project is new)')
    @cmdln.option('--extend-package-names', default=False, action="store_true",
                  help='Extend packages names with project name as suffix')
    @cmdln.option('--noaccess', action='store_true',
                        help='Create a hidden project')
    @cmdln.option('-m', '--message', metavar='TEXT',
                        help='specify message TEXT')
    @cmdln.option('-M', '--maintenance', default=False, action="store_true",
                        help='Create project and package in maintenance mode')
    @cmdln.option('-N', '--new-package', action='store_true',
                  help='create a branch pointing to a not yet existing package')
    @cmdln.option('-r', '--revision', metavar='rev',
                        help='branch against a specific revision')
    def do_branch(self, subcmd, opts, *args):
        """${cmd_name}: Branch a package

        [See http://en.opensuse.org/openSUSE:Build_Service_Collaboration
        for information on this topic.]

        Create a source link from a package of an existing project to a new
        subproject of the requesters home project (home:branches:)

        The branched package will live in
            home:USERNAME:branches:PROJECT/PACKAGE
        if nothing else specified.

        With getpac or bco, the branched package will come from one of
            %(getpac_default_project)s
        (list of projects from oscrc:getpac_default_project)
        if nothing else is specfied on the command line.

        usage:
            osc branch
            osc branch SOURCEPROJECT SOURCEPACKAGE
            osc branch SOURCEPROJECT SOURCEPACKAGE TARGETPROJECT
            osc branch SOURCEPROJECT SOURCEPACKAGE TARGETPROJECT TARGETPACKAGE
            osc getpac SOURCEPACKAGE
            osc bco ...
        ${cmd_option_list}
        """

        if subcmd == 'getpac' or subcmd == 'branchco' or subcmd == 'bco': 
            opts.checkout = True
        args = slash_split(args)
        tproject = tpackage = None

        if (subcmd == 'getpac' or subcmd == 'bco') and len(args) == 1:
            def_p = find_default_project(self.get_api_url(), args[0])
            print('defaulting to %s/%s' % (def_p, args[0]), file=sys.stderr)
            # python has no args.unshift ???
            args = [ def_p, args[0] ]
            
        if len(args) == 0 and is_package_dir('.'):
            args = (store_read_project('.'), store_read_package('.'))

        if len(args) < 2 or len(args) > 4:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        apiurl = self.get_api_url()

        expected = 'home:%s:branches:%s' % (conf.get_apiurl_usr(apiurl), args[0])
        if len(args) >= 3:
            expected = tproject = args[2]
        if len(args) >= 4:
            tpackage = args[3]

        exists, targetprj, targetpkg, srcprj, srcpkg = \
                branch_pkg(apiurl, args[0], args[1],
                           nodevelproject=opts.nodevelproject, rev=opts.revision,
                           target_project=tproject, target_package=tpackage,
                           return_existing=opts.checkout, msg=opts.message or '',
                           force=opts.force, noaccess=opts.noaccess,
                           add_repositories=opts.add_repositories,
                           extend_package_names=opts.extend_package_names,
                           missingok=opts.new_package,
                           maintenance=opts.maintenance)
        if exists:
            print('Using existing branch project: %s' % targetprj, file=sys.stderr)

        devloc = None
        if not exists and (srcprj != args[0] or srcpkg != args[1]):
            try:
                root = ET.fromstring(''.join(show_attribute_meta(apiurl, args[0], None, None,
                    conf.config['maintained_update_project_attribute'], False, False)))
                # this might raise an AttributeError
                uproject = root.find('attribute').find('value').text
                print('\nNote: The branch has been created from the configured update project: %s' \
                    % uproject)
            except (AttributeError, HTTPError) as e:
                devloc = srcprj
                print('\nNote: The branch has been created of a different project,\n' \
                      '              %s,\n' \
                      '      which is the primary location of where development for\n' \
                      '      that package takes place.\n' \
                      '      That\'s also where you would normally make changes against.\n' \
                      '      A direct branch of the specified package can be forced\n' \
                      '      with the --nodevelproject option.\n' % devloc)

        package = targetpkg or args[1]
        if opts.checkout:
            checkout_package(apiurl, targetprj, package, server_service_files=True,
                             expand_link=True, prj_dir=targetprj)
            if conf.config['verbose']:
                print('Note: You can use "osc delete" or "osc submitpac" when done.\n')
        else:
            apiopt = ''
            if conf.get_configParser().get('general', 'apiurl') != apiurl:
                apiopt = '-A %s ' % apiurl
            print('A working copy of the branched package can be checked out with:\n\n' \
                  'osc %sco %s/%s' \
                      % (apiopt, targetprj, package))
        print_request_list(apiurl, args[0], args[1])
        if devloc:
            print_request_list(apiurl, devloc, srcpkg)


    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify log message TEXT')
    def do_undelete(self, subcmd, opts, *args):
        """${cmd_name}: Restores a deleted project or package on the server.

        The server restores a package including the sources and meta configuration.
        Binaries remain to be lost and will be rebuild.

        usage:
           osc undelete PROJECT
           osc undelete PROJECT PACKAGE [PACKAGE ...]

        ${cmd_option_list}
        """

        args = slash_split(args)
        if len(args) < 1:
            raise oscerr.WrongArgs('Missing argument.')

        msg = ''
        if opts.message:
            msg = opts.message
        else:
            msg = edit_message()

        apiurl = self.get_api_url()
        prj = args[0]
        pkgs = args[1:]

        if pkgs:
            for pkg in pkgs:
                undelete_package(apiurl, prj, pkg, msg)
        else:
            undelete_project(apiurl, prj, msg)


    @cmdln.option('-r', '--recursive', action='store_true',
                        help='deletes a project with packages inside')
    @cmdln.option('-f', '--force', action='store_true',
                        help='deletes a project where other depends on')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify log message TEXT')
    def do_rdelete(self, subcmd, opts, *args):
        """${cmd_name}: Delete a project or packages on the server.

        As a safety measure, project must be empty (i.e., you need to delete all
        packages first). Also, packages must have no requests pending (i.e., you need
        to accept/revoke such requests first).
        If you are sure that you want to remove this project and all
        its packages use \'--recursive\' switch.
        It may still not work because other depends on it. If you want to ignore this as
        well use \'--force\' switch.

        usage:
           osc rdelete [-r] [-f] PROJECT [PACKAGE]

        ${cmd_option_list}
        """

        args = slash_split(args)
        if len(args) < 1 or len(args) > 2:
            raise oscerr.WrongArgs('Wrong number of arguments')

        apiurl = self.get_api_url()
        prj = args[0]

        msg = ''
        if opts.message:
            msg = opts.message
        else:
            msg = edit_message()

        # empty arguments result in recursive project delete ...
        if not len(prj):
            raise oscerr.WrongArgs('Project argument is empty')

        if len(args) > 1:
            pkg = args[1]

            if not len(pkg):
                raise oscerr.WrongArgs('Package argument is empty')

            ## FIXME: core.py:commitDelPackage() should have something similar
            rlist = get_request_list(apiurl, prj, pkg)
            for rq in rlist: 
                print(rq)
            if len(rlist) >= 1 and not opts.force:
                print('Package has pending requests. Deleting the package will break them. '\
                      'They should be accepted/declined/revoked before deleting the package. '\
                      'Or just use \'--force\'.', file=sys.stderr)
                sys.exit(1)

            delete_package(apiurl, prj, pkg, opts.force, msg)

        elif (not opts.recursive) and len(meta_get_packagelist(apiurl, prj)) >= 1:
            print('Project contains packages. It must be empty before deleting it. ' \
                                'If you are sure that you want to remove this project and all its ' \
                                'packages use the \'--recursive\' switch.', file=sys.stderr)
            sys.exit(1)
        else:
            delete_project(apiurl, prj, opts.force, msg)


    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify log message TEXT')
    def do_unlock(self, subcmd, opts, *args):
        """${cmd_name}: Unlocks a project or package

        Unlocks a locked project or package. A comment is required.

        usage:
           osc unlock PROJECT [PACKAGE]

        ${cmd_option_list}
        """

        args = slash_split(args)
        if len(args) < 1 or len(args) > 2:
            raise oscerr.WrongArgs('Wrong number of arguments')

        apiurl = self.get_api_url()
        prj = args[0]

        msg = ''
        if opts.message:
            msg = opts.message
        else:
            msg = edit_message()

        # empty arguments result in recursive project delete ...
        if not len(prj):
            raise oscerr.WrongArgs('Project argument is empty')

        if len(args) > 1:
            pkg = args[1]

            if not len(pkg):
                raise oscerr.WrongArgs('Package argument is empty')

            unlock_package(apiurl, prj, pkg, msg)

        else:
            unlock_project(apiurl, prj, msg)


    @cmdln.hide(1)
    def do_deletepac(self, subcmd, opts, *args):
        print("""${cmd_name} is obsolete !

                 Please use either
                   osc delete       for checked out packages or projects
                 or
                   osc rdelete      for server side operations.""")

        sys.exit(1)

    @cmdln.hide(1)
    @cmdln.option('-f', '--force', action='store_true',
                        help='deletes a project and its packages')
    def do_deleteprj(self, subcmd, opts, project):
        """${cmd_name} is obsolete !

                 Please use
                   osc rdelete PROJECT
        """
        sys.exit(1)

    @cmdln.alias('metafromspec')
    @cmdln.alias('updatepkgmetafromspec')
    @cmdln.option('', '--specfile', metavar='FILE',
                      help='Path to specfile. (if you pass more than working copy this option is ignored)')
    def do_updatepacmetafromspec(self, subcmd, opts, *args):
        """${cmd_name}: Update package meta information from a specfile

        ARG, if specified, is a package working copy.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        if opts.specfile and len(args) == 1:
            specfile = opts.specfile
        else:
            specfile = None
        pacs = findpacs(args)
        for p in pacs:
            p.read_meta_from_spec(specfile)
            p.update_package_meta()


    @cmdln.alias('linkdiff')
    @cmdln.alias('ldiff')
    @cmdln.alias('di')
    @cmdln.option('-c', '--change', metavar='rev',
                        help='the change made by revision rev (like -r rev-1:rev).'
                             'If rev is negative this is like -r rev:rev-1.')
    @cmdln.option('-r', '--revision', metavar='rev1[:rev2]',
                        help='If rev1 is specified it will compare your working copy against '
                             'the revision (rev1) on the server. '
                             'If rev1 and rev2 are specified it will compare rev1 against rev2 '
                             '(NOTE: changes in your working copy are ignored in this case)')
    @cmdln.option('-p', '--plain', action='store_true',
                        help='output the diff in plain (not unified) diff format')
    @cmdln.option('-l', '--link', action='store_true',
                        help='(osc linkdiff): compare against the base revision of the link')
    @cmdln.option('--missingok', action='store_true',
                        help='do not fail if the source or target project/package does not exist on the server')
    def do_diff(self, subcmd, opts, *args):
        """${cmd_name}: Generates a diff

        Generates a diff, comparing local changes against the repository
        server.

        ${cmd_usage}
                ARG, if specified, is a filename to include in the diff.
                Default: all files.

            osc diff --link
            osc linkdiff                
                Compare current checkout directory against the link base.

            osc diff --link PROJ PACK      
            osc linkdiff PROJ PACK      
                Compare a package against the link base (ignoring working copy changes).

        ${cmd_option_list}
        """

        if (subcmd == 'ldiff' or subcmd == 'linkdiff'):
            opts.link = True
        args = parseargs(args)
        
        pacs = None
        if not opts.link or not len(args) == 2:
            pacs = findpacs(args)


        if opts.link:
            query = { 'rev': 'latest' }
            if pacs:
                u = makeurl(pacs[0].apiurl, ['source', pacs[0].prjname, pacs[0].name], query=query)
            else:
                u = makeurl(self.get_api_url(), ['source', args[0], args[1]], query=query)
            f = http_GET(u)
            root = ET.parse(f).getroot()
            linkinfo = root.find('linkinfo')
            if linkinfo == None:
                raise oscerr.APIError('package is not a source link')
            baserev = linkinfo.get('baserev')
            opts.revision = baserev
            if pacs:
                print("diff working copy against last commited version\n")
            else:
                print("diff commited package against linked revision %s\n" % baserev)
                run_pager(server_diff(self.get_api_url(), linkinfo.get('project'), linkinfo.get('package'), baserev,
                  args[0], args[1], linkinfo.get('lsrcmd5'), not opts.plain, opts.missingok))
                return

        if opts.change:
            try:
                rev = int(opts.change)
                if rev > 0:
                    rev1 = rev - 1
                    rev2 = rev
                elif rev < 0:
                    rev1 = -rev
                    rev2 = -rev - 1
                else:
                    return
            except:
                print('Revision \'%s\' not an integer' % opts.change, file=sys.stderr)
                return
        else:
            rev1, rev2 = parseRevisionOption(opts.revision)
        diff = ''
        for pac in pacs:
            if not rev2:
                for i in pac.get_diff(rev1):
                    diff += ''.join(i)
            else:
                diff += server_diff_noex(pac.apiurl, pac.prjname, pac.name, rev1,
                                    pac.prjname, pac.name, rev2, not opts.plain, opts.missingok)
        run_pager(diff)


    @cmdln.option('--oldprj', metavar='OLDPRJ',
                  help='project to compare against'
                  ' (deprecated, use 3 argument form)')
    @cmdln.option('--oldpkg', metavar='OLDPKG',
                  help='package to compare against'
                  ' (deprecated, use 3 argument form)')
    @cmdln.option('-M', '--meta', action='store_true',
                        help='diff meta data')
    @cmdln.option('-r', '--revision', metavar='N[:M]',
                  help='revision id, where N = old revision and M = new revision')
    @cmdln.option('-p', '--plain', action='store_true',
                  help='output the diff in plain (not unified) diff format')
    @cmdln.option('-c', '--change', metavar='rev',
                        help='the change made by revision rev (like -r rev-1:rev). '
                             'If rev is negative this is like -r rev:rev-1.')
    @cmdln.option('--missingok', action='store_true',
                        help='do not fail if the source or target project/package does not exist on the server')
    @cmdln.option('-u', '--unexpand', action='store_true',
                        help='diff unexpanded version if sources are linked')
    def do_rdiff(self, subcmd, opts, *args):
        """${cmd_name}: Server-side "pretty" diff of two packages

        Compares two packages (three or four arguments) or shows the
        changes of a specified revision of a package (two arguments)

        If no revision is specified the latest revision is used.

        Note that this command doesn't return a normal diff (which could be
        applied as patch), but a "pretty" diff, which also compares the content
        of tarballs.


        usage:
            osc ${cmd_name} OLDPRJ OLDPAC NEWPRJ [NEWPAC]
            osc ${cmd_name} PROJECT PACKAGE
        ${cmd_option_list}
        """

        args = slash_split(args)
        apiurl = self.get_api_url()

        rev1 = None
        rev2 = None

        old_project = None
        old_package = None
        new_project = None
        new_package = None

        if len(args) == 2:
            new_project = args[0]
            new_package = args[1]
            if opts.oldprj:
                old_project = opts.oldprj
            if opts.oldpkg:
                old_package = opts.oldpkg
        elif len(args) == 3 or len(args) == 4:
            if opts.oldprj or opts.oldpkg:
                raise oscerr.WrongArgs('--oldpkg and --oldprj are only valid with two arguments')
            old_project = args[0]
            new_package = old_package = args[1]
            new_project = args[2]
            if len(args) == 4:
                new_package = args[3]
        elif len(args) == 1 and opts.meta:
            new_project = args[0]
            new_package = '_project'
        else:
            raise oscerr.WrongArgs('Wrong number of arguments')

        if opts.meta:
            opts.unexpand = True

        if opts.change:
            try:
                rev = int(opts.change)
                if rev > 0:
                    rev1 = rev - 1
                    rev2 = rev
                elif rev < 0:
                    rev1 = -rev
                    rev2 = -rev - 1
                else:
                    return
            except:
                print('Revision \'%s\' not an integer' % opts.change, file=sys.stderr)
                return
        else:
            if opts.revision:
                rev1, rev2 = parseRevisionOption(opts.revision)

        rdiff = server_diff_noex(apiurl,
                            old_project, old_package, rev1,
                            new_project, new_package, rev2, not opts.plain, opts.missingok,
                            meta=opts.meta,
                            expand=not opts.unexpand)

        run_pager(rdiff)

    def _pdiff_raise_non_existing_package(self, project, package, msg = None):
        raise oscerr.PackageMissing(project, package, msg or '%s/%s does not exist.' % (project, package))

    def _pdiff_package_exists(self, apiurl, project, package):
        try:
            show_package_meta(apiurl, project, package)
            return True
        except HTTPError as e:
            if e.code != 404:
                print('Cannot check that %s/%s exists: %s' % (project, package, e), file=sys.stderr)
            return False

    def _pdiff_guess_parent(self, apiurl, project, package, check_exists_first = False):
        # Make sure the parent exists
        if check_exists_first and not self._pdiff_package_exists(apiurl, project, package):
            self._pdiff_raise_non_existing_package(project, package)

        if project.startswith('home:'):
            guess = project[len('home:'):]
            # remove user name
            pos = guess.find(':')
            if pos > 0:
                guess = guess[guess.find(':') + 1:]
                if guess.startswith('branches:'):
                    guess = guess[len('branches:'):]
                    return (guess, package)

        return (None, None)

    def _pdiff_get_parent_from_link(self, apiurl, project, package):
        link_url = makeurl(apiurl, ['source', project, package, '_link'])

        try:
            file = http_GET(link_url)
            root = ET.parse(file).getroot()
        except HTTPError as e:
            return (None, None)
        except SyntaxError as e:
            print('Cannot parse %s/%s/_link: %s' % (project, package, e), file=sys.stderr)
            return (None, None)

        parent_project = root.get('project')
        parent_package = root.get('package') or package

        if parent_project is None:
            return (None, None)

        return (parent_project, parent_package)

    def _pdiff_get_exists_and_parent(self, apiurl, project, package):
        link_url = makeurl(apiurl, ['public', 'source', project, package])
        try:
            file = http_GET(link_url)
            root = ET.parse(file).getroot()
        except HTTPError as e:
            if e.code != 404:
                print('Cannot get list of files for %s/%s: %s' % (project, package, e), file=sys.stderr)
            return (None, None, None)
        except SyntaxError as e:
            print('Cannot parse list of files for %s/%s: %s' % (project, package, e), file=sys.stderr)
            return (None, None, None)

        link_node = root.find('linkinfo')
        if link_node is None:
            return (True, None, None)

        parent_project = link_node.get('project')
        parent_package = link_node.get('package') or package

        if parent_project is None:
            raise oscerr.APIError('%s/%s is a link with no parent?' % (project, package))

        return (True, parent_project, parent_package)

    @cmdln.option('-p', '--plain', action='store_true',
                  dest='plain',
                  help='output the diff in plain (not unified) diff format')
    @cmdln.option('-n', '--nomissingok', action='store_true',
                  dest='nomissingok',
                  help='fail if the parent package does not exist on the server')
    def do_pdiff(self, subcmd, opts, *args):
        """${cmd_name}: Quick alias to diff the content of a package with its parent.

        Usage:
            osc pdiff [--plain|-p] [--nomissing-ok|-n]
            osc pdiff [--plain|-p] [--nomissing-ok|-n] PKG
            osc pdiff [--plain|-p] [--nomissing-ok|-n] PRJ PKG

        ${cmd_option_list}
        """

        apiurl = self.get_api_url()
        args = slash_split(args)

        unified = not opts.plain
        noparentok = not opts.nomissingok

        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 0:
            if not is_package_dir(os.getcwd()):
                raise oscerr.WrongArgs('Current directory is not a checked out package. Please specify a project and a package.')
            project = store_read_project(os.curdir)
            package = store_read_package(os.curdir)
        elif len(args) == 1:
            if not is_project_dir(os.getcwd()):
                raise oscerr.WrongArgs('Current directory is not a checked out project. Please specify a project and a package.')
            project = store_read_project(os.curdir)
            package = args[0]
        elif len(args) == 2:
            project = args[0]
            package = args[1]
        else:
            raise RuntimeError('Internal error: bad check for arguments.')

        ## Find parent package

        # Old way, that does one more request to api
        #(parent_project, parent_package) = self._pdiff_get_parent_from_link(apiurl, project, package)
        #if not parent_project:
        #    (parent_project, parent_package) = self._pdiff_guess_parent(apiurl, project, package, check_exists_first = True)
        #    if parent_project and parent_package:
        #        print 'Guessed that %s/%s is the parent package.' % (parent_project, parent_package)

        # New way
        (exists, parent_project, parent_package) = self._pdiff_get_exists_and_parent (apiurl, project, package)
        if not exists:
            self._pdiff_raise_non_existing_package(project, package)
        if not parent_project:
            (parent_project, parent_package) = self._pdiff_guess_parent(apiurl, project, package, check_exists_first = False)
            if parent_project and parent_package:
                print('Guessed that %s/%s is the parent package.' % (parent_project, parent_package))

        if not parent_project or not parent_package:
            print('Cannot find a parent for %s/%s to diff against.' % (project, package), file=sys.stderr)
            return 1

        if not noparentok and not self._pdiff_package_exists(apiurl, parent_project, parent_package):
            self._pdiff_raise_non_existing_package(parent_project, parent_package, 
                                                   msg = 'Parent for %s/%s (%s/%s) does not exist.' % \
                                                   (project, package, parent_project, parent_package))

        rdiff = server_diff(apiurl, parent_project, parent_package, None, project,
                            package, None, unified = unified, missingok = noparentok)

        run_pager(rdiff)

    def _get_branch_parent(self, prj):
        m = re.match('^home:[^:]+:branches:(.+)', prj)
        # OBS_Maintained is a special case
        if m and prj.find(':branches:OBS_Maintained:') == -1:
            return m.group(1)
        return None

    def _prdiff_skip_package(self, opts, pkg):
        if opts.exclude and re.search(opts.exclude, pkg):
            return True

        if opts.include and not re.search(opts.include, pkg):
            return True

        return False

    def _prdiff_output_diff(self, opts, rdiff):
        if opts.diffstat:
            print()
            p = subprocess.Popen("diffstat",
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 close_fds=True)
            p.stdin.write(rdiff.encode())
            p.stdin.close()
            print("".join(x.decode() for x in p.stdout.readlines()))
        elif opts.unified:
            print()
            print(rdiff)
            #run_pager(rdiff)

    def _prdiff_output_matching_requests(self, opts, requests,
                                         srcprj, pkg):
        """
        Search through the given list of requests and output any
        submitrequests which target pkg and originate from srcprj.
        """
        for req in requests:
            for action in req.get_actions('submit'):
                if action.src_project != srcprj:
                    continue

                if action.tgt_package != pkg:
                    continue

                print()
                print(req.list_view())
                break

    @cmdln.alias('projectdiff')
    @cmdln.alias('projdiff')
    @cmdln.option('-r', '--requests', action='store_true',
                  help='show open requests for any packages with differences')
    @cmdln.option('-e', '--exclude',  metavar='REGEXP', dest='exclude',
                  help='skip packages matching REGEXP')
    @cmdln.option('-i', '--include',  metavar='REGEXP', dest='include',
                  help='only consider packages matching REGEXP')
    @cmdln.option('-n', '--show-not-in-old', action='store_true',
                  help='show packages only in the new project')
    @cmdln.option('-o', '--show-not-in-new', action='store_true',
                  help='show packages only in the old project')
    @cmdln.option('-u', '--unified',  action='store_true',
                  help='show full unified diffs of differences')
    @cmdln.option('-d', '--diffstat', action='store_true',
                  help='show diffstat of differences')

    def do_prdiff(self, subcmd, opts, *args):
        """${cmd_name}: Server-side diff of two projects

        Compares two projects and either summarises or outputs the
        differences in full.  In the second form, a project is compared
        with one of its branches inside a home:$USER project (the branch
        is treated as NEWPRJ).  The home branch is optional if the current
        working directory is a checked out copy of it.

        Usage:
            osc prdiff [OPTIONS] OLDPRJ NEWPRJ
            osc prdiff [OPTIONS] [home:$USER:branch:$PRJ]

        ${cmd_option_list}
        """

        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')

        if len(args) == 0:
            if is_project_dir(os.curdir):
                newprj = Project('.', getPackageList=False).name
                oldprj = self._get_branch_parent(newprj)
                if oldprj is None:
                    raise oscerr.WrongArgs('Current directory is not a valid home branch.')
            else:
                raise oscerr.WrongArgs('Current directory is not a project.')
        elif len(args) == 1:
            newprj = args[0]
            oldprj = self._get_branch_parent(newprj)
            if oldprj is None:
                raise oscerr.WrongArgs('Single-argument form must be for a home branch.')
        elif len(args) == 2:
            oldprj, newprj = args
        else:
            raise RuntimeError('BUG in argument parsing, please report.\n'
                               'args: ' + repr(args))

        if opts.diffstat and opts.unified:
            print('error - cannot specify both --diffstat and --unified', file=sys.stderr)
            sys.exit(1)

        apiurl = self.get_api_url()

        old_packages = meta_get_packagelist(apiurl, oldprj)
        new_packages = meta_get_packagelist(apiurl, newprj)

        if opts.requests:
            requests = get_request_list(apiurl, project=oldprj,
                                        req_state=('new', 'review'))

        for pkg in old_packages:
            if self._prdiff_skip_package(opts, pkg):
                continue

            if pkg not in new_packages:
                if opts.show_not_in_new:
                    print("old only:  %s" % pkg)
                continue

            rdiff = server_diff_noex(
                apiurl,
                oldprj, pkg, None,
                newprj, pkg, None,
                unified=True, missingok=False, meta=False, expand=True
                )

            if rdiff:
                print("differs:   %s" % pkg)
                self._prdiff_output_diff(opts, rdiff)

                if opts.requests:
                    self._prdiff_output_matching_requests(opts, requests,
                                                          newprj, pkg)
            else:
                print("identical: %s" % pkg)

        for pkg in new_packages:
            if self._prdiff_skip_package(opts, pkg):
                continue

            if pkg not in old_packages:
                if opts.show_not_in_old:
                    print("new only:  %s" % pkg)

    @cmdln.hide(1)
    @cmdln.alias('in')
    def do_install(self, subcmd, opts, *args):
        """${cmd_name}: install a package after build via zypper in -r

        Not implemented here.  Please try 
        http://software.opensuse.org/search?q=osc-plugin-install&include_home=true


        ${cmd_usage}
        ${cmd_option_list}
        """

        args = slash_split(args)
        args = expand_proj_pack(args)

        ## FIXME:
        ## if there is only one argument, and it ends in .ymp
        ## then fetch it, Parse XML to get the first
        ##  metapackage.group.repositories.repository.url
        ## and construct zypper cmd's for all
        ##  metapackage.group.software.item.name
        ##
        ## if args[0] is already an url, the use it as is.

        cmd = "sudo zypper -p http://download.opensuse.org/repositories/%s/%s --no-refresh -v in %s" % \
              (re.sub(':', ':/', args[0]), 'openSUSE_11.4', args[1])
        print(self.do_install.__doc__)
        print("Example: \n" + cmd)


    def do_repourls(self, subcmd, opts, *args):
        """${cmd_name}: Shows URLs of .repo files

        Shows URLs on which to access the project .repos files (yum-style
        metadata) on download.opensuse.org.

        usage:
           osc repourls [PROJECT]

        ${cmd_option_list}
        """

        apiurl = self.get_api_url()

        if len(args) == 1:
            project = args[0]
        elif len(args) == 0:
            project = store_read_project('.')
        else:
            raise oscerr.WrongArgs('Wrong number of arguments')

        # XXX: API should somehow tell that
        url_tmpl = 'http://download.opensuse.org/repositories/%s/%s/%s.repo'
        repos = get_repositories_of_project(apiurl, project)
        for repo in repos:
            print(url_tmpl % (project.replace(':', ':/'), repo, project))


    @cmdln.option('-r', '--revision', metavar='rev',
                        help='checkout the specified revision. '
                             'NOTE: if you checkout the complete project '
                             'this option is ignored!')
    @cmdln.option('-e', '--expand-link', action='store_true',
                        help='if a package is a link, check out the expanded '
                             'sources (no-op, since this became the default)')
    @cmdln.option('-u', '--unexpand-link', action='store_true',
                        help='if a package is a link, check out the _link file ' \
                             'instead of the expanded sources')
    @cmdln.option('-M', '--meta', action='store_true',
                        help='checkout out meta data instead of sources' )
    @cmdln.option('-c', '--current-dir', action='store_true',
                        help='place PACKAGE folder in the current directory' \
                             'instead of a PROJECT/PACKAGE directory')
    @cmdln.option('-o', '--output-dir', metavar='outdir',
                        help='place package in the specified directory' \
                             'instead of a PROJECT/PACKAGE directory')
    @cmdln.option('-s', '--source-service-files', action='store_true',
                        help='Run source services.' )
    @cmdln.option('-S', '--server-side-source-service-files', action='store_true',
                        help='Use server side generated sources instead of local generation.' )
    @cmdln.option('-l', '--limit-size', metavar='limit_size',
                        help='Skip all files with a given size')
    @cmdln.alias('co')
    def do_checkout(self, subcmd, opts, *args):
        """${cmd_name}: Check out content from the repository

        Check out content from the repository server, creating a local working
        copy.

        When checking out a single package, the option --revision can be used
        to specify a revision of the package to be checked out.

        When a package is a source link, then it will be checked out in
        expanded form. If --unexpand-link option is used, the checkout will
        instead produce the raw _link file plus patches.

        usage:
            osc co PROJECT [PACKAGE] [FILE]
               osc co PROJECT                    # entire project
               osc co PROJECT PACKAGE            # a package
               osc co PROJECT PACKAGE FILE       # single file -> to current dir

            while inside a project directory:
               osc co PACKAGE                    # check out PACKAGE from project
            
            with the result of rpm -q --qf '%%{DISTURL}\\n' PACKAGE
               osc co obs://API/PROJECT/PLATFORM/REVISION-PACKAGE       

        ${cmd_option_list}
        """

        if opts.unexpand_link:
            expand_link = False
        else:
            expand_link = True

        if not args:
            raise oscerr.WrongArgs('Incorrect number of arguments.\n\n' \
                  + self.get_cmd_help('checkout'))

        # XXX: this too openSUSE-setup specific...
        # FIXME: this should go into ~jw/patches/osc/osc.proj_pack_20101201.diff 
        #        to be available to all subcommands via @cmdline.prep(proj_pack)
        # obs://build.opensuse.org/openSUSE:11.3/standard/fc6c25e795a89503e99d59da5dc94a79-screen
        m = re.match(r"obs://([^/]+)/(\S+)/([^/]+)/([A-Fa-f\d]+)\-(\S+)", args[0])
        if m and len(args) == 1:
            apiurl   = "https://" + m.group(1)
            project = project_dir = m.group(2)
            # platform            = m.group(3)
            opts.revision         = m.group(4)
            package               = m.group(5)
            apiurl = apiurl.replace('/build.', '/api.')
            filename = None
        else:
            args = slash_split(args)
            project = package = filename = None
            apiurl = self.get_api_url()
            try:
                project = project_dir = args[0]
                package = args[1]
                filename = args[2]
            except:
                pass

            if len(args) == 1 and is_project_dir(os.curdir):
                project = store_read_project(os.curdir)
                project_dir = os.curdir
                package = args[0]

        rev, dummy = parseRevisionOption(opts.revision)
        if rev == None:
            rev = "latest"

        if rev and rev != "latest" and not checkRevision(project, package, rev):
            print('Revision \'%s\' does not exist' % rev, file=sys.stderr)
            sys.exit(1)

        if filename:
            # Note: same logic as with 'osc cat' (not 'osc ls', which never merges!)
            if expand_link:
                rev = show_upstream_srcmd5(apiurl, project, package, expand=True, revision=rev)
            get_source_file(apiurl, project, package, filename, revision=rev, progress_obj=self.download_progress)

        elif package:
            if opts.current_dir:
                project_dir = None
            checkout_package(apiurl, project, package, rev, expand_link=expand_link, \
                             prj_dir=project_dir, service_files = opts.source_service_files, \
                             server_service_files=opts.server_side_source_service_files, \
                             progress_obj=self.download_progress, size_limit=opts.limit_size, \
                             meta=opts.meta, outdir=opts.output_dir)
            print_request_list(apiurl, project, package)

        elif project:
            prj_dir = project
            if sys.platform[:3] == 'win':
                prj_dir = prj_dir.replace(':', ';')
            if os.path.exists(prj_dir):
                sys.exit('osc: project \'%s\' already exists' % project)

            # check if the project does exist (show_project_meta will throw an exception)
            show_project_meta(apiurl, project)

            Project.init_project(apiurl, prj_dir, project, conf.config['do_package_tracking'])
            print(statfrmt('A', prj_dir))

            # all packages
            for package in meta_get_packagelist(apiurl, project):
                # don't check out local links by default
                try:
                    m = show_files_meta(apiurl, project, package)
                    li = Linkinfo()
                    li.read(ET.fromstring(''.join(m)).find('linkinfo'))
                    if not li.haserror():
                        if li.project == project:
                            print(statfrmt('S', package + " link to package " + li.package))
                            continue
                except:
                    pass

                try:
                    checkout_package(apiurl, project, package, expand_link = expand_link, \
                                     prj_dir = prj_dir, service_files = opts.source_service_files, \
                                     server_service_files = opts.server_side_source_service_files, \
                                     progress_obj=self.download_progress, size_limit=opts.limit_size, \
                                     meta=opts.meta)
                except oscerr.LinkExpandError as e:
                    print('Link cannot be expanded:\n', e, file=sys.stderr)
                    print('Use "osc repairlink" for fixing merge conflicts:\n', file=sys.stderr)
                    # check out in unexpanded form at least
                    checkout_package(apiurl, project, package, expand_link = False, \
                                     prj_dir = prj_dir, service_files = opts.source_service_files, \
                                     server_service_files = opts.server_side_source_service_files, \
                                     progress_obj=self.download_progress, size_limit=opts.limit_size, \
                                     meta=opts.meta)
            print_request_list(apiurl, project)

        else:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('checkout'))


    @cmdln.option('-q', '--quiet', action='store_true',
                        help='print as little as possible')
    @cmdln.option('-v', '--verbose', action='store_true',
                        help='print extra information')
    @cmdln.option('-e', '--show-excluded', action='store_true',
                        help='also show files which are excluded by the ' \
                             '"exclude_glob" config option')
    @cmdln.alias('st')
    def do_status(self, subcmd, opts, *args):
        """${cmd_name}: Show status of files in working copy

        Show the status of files in a local working copy, indicating whether
        files have been changed locally, deleted, added, ...

        The first column in the output specifies the status and is one of the
        following characters:
          ' ' no modifications
          'A' Added
          'C' Conflicted
          'D' Deleted
          'M' Modified
          '?' item is not under version control
          '!' item is missing (removed by non-osc command) or incomplete

        examples:
          osc st
          osc st <directory>
          osc st file1 file2 ...

        usage:
            osc status [OPTS] [PATH...]
        ${cmd_option_list}
        """

        if opts.quiet and opts.verbose:
            raise oscerr.WrongOptions('\'--quiet\' and \'--verbose\' are mutually exclusive')

        args = parseargs(args)
        lines = []
        excl_states = (' ',)
        if opts.quiet:
            excl_states += ('?',)
        elif opts.verbose:
            excl_states = ()
        for arg in args:
            if is_project_dir(arg):
                prj = Project(arg, False)
                # don't exclude packages with state ' ' because the packages
                # might have modified etc. files
                prj_excl = [st for st in excl_states if st != ' ']
                for st, pac in sorted(prj.get_status(*prj_excl), lambda x, y: cmp(x[1], y[1])):
                    p = prj.get_pacobj(pac)
                    if p is None:
                        # state is != ' '
                        lines.append(statfrmt(st, os.path.normpath(os.path.join(prj.dir, pac))))
                        continue
                    if st == ' ' and opts.verbose or st != ' ':
                        lines.append(statfrmt(st, os.path.normpath(os.path.join(prj.dir, pac))))
                    states = p.get_status(opts.show_excluded, *excl_states)
                    for st, filename in sorted(states, lambda x, y: cmp(x[1], y[1])):
                        lines.append(statfrmt(st, os.path.normpath(os.path.join(p.dir, filename))))
            else:
                p = findpacs([arg])[0]
                for st, filename in sorted(p.get_status(opts.show_excluded, *excl_states), lambda x, y: cmp(x[1], y[1])):
                    lines.append(statfrmt(st, os.path.normpath(os.path.join(p.dir, filename))))
        # arrange the lines in order: unknown files first
        # filenames are already sorted
        lines = [l for l in lines if l[0] == '?'] + \
                [l for l in lines if l[0] != '?']
        if lines:
            print('\n'.join(lines))


    def do_add(self, subcmd, opts, *args):
        """${cmd_name}: Mark files to be added upon the next commit

        In case a URL is given the file will get downloaded and registered to be downloaded
        by the server as well via the download_url source service.

        This is recommended for release tar balls to track their source and to help
        others to review your changes esp. on version upgrades.

        usage:
            osc add URL [URL...]
            osc add FILE [FILE...]
        ${cmd_option_list}
        """
        if not args:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('add'))

        # Do some magic here, when adding a url. We want that the server to download the tar ball and to verify it
        for arg in parseargs(args):
            if arg.startswith('http://') or arg.startswith('https://') or arg.startswith('ftp://') or arg.startswith('git://'):
                if arg.endswith('.git'):
                    addGitSource(arg)
                else:
                    addDownloadUrlService(arg)
            else:
                addFiles([arg])


    def do_mkpac(self, subcmd, opts, *args):
        """${cmd_name}: Create a new package under version control

        usage:
            osc mkpac new_package
        ${cmd_option_list}
        """
        if not conf.config['do_package_tracking']:
            print("to use this feature you have to enable \'do_package_tracking\' " \
                                "in the [general] section in the configuration file", file=sys.stderr)
            sys.exit(1)

        if len(args) != 1:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        createPackageDir(args[0])

    @cmdln.option('-r', '--recursive', action='store_true',
                        help='If CWD is a project dir then scan all package dirs as well')
    @cmdln.alias('ar')
    def do_addremove(self, subcmd, opts, *args):
        """${cmd_name}: Adds new files, removes disappeared files

        Adds all files new in the local copy, and removes all disappeared files.

        ARG, if specified, is a package working copy.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        arg_list = args[:]
        for arg in arg_list:
            if is_project_dir(arg) and conf.config['do_package_tracking']:
                prj = Project(arg, False)
                for pac in prj.pacs_unvers:
                    pac_dir = getTransActPath(os.path.join(prj.dir, pac))
                    if os.path.isdir(pac_dir):
                        addFiles([pac_dir], prj)
                for pac in prj.pacs_broken:
                    if prj.get_state(pac) != 'D':
                        prj.set_state(pac, 'D')
                        print(statfrmt('D', getTransActPath(os.path.join(prj.dir, pac))))
                if opts.recursive:
                    for pac in prj.pacs_have:
                        state = prj.get_state(pac)
                        if state != None and state != 'D':
                            pac_dir = getTransActPath(os.path.join(prj.dir, pac))
                            args.append(pac_dir)
                args.remove(arg)
                prj.write_packages()
            elif is_project_dir(arg):
                print('osc: addremove is not supported in a project dir unless ' \
                                    '\'do_package_tracking\' is enabled in the configuration file', file=sys.stderr)
                sys.exit(1)

        pacs = findpacs(args)
        for p in pacs:
            p.todo = list(set(p.filenamelist + p.filenamelist_unvers + p.to_be_added))
            for filename in p.todo:
                if os.path.isdir(filename):
                    continue
                # ignore foo.rXX, foo.mine for files which are in 'C' state
                if os.path.splitext(filename)[0] in p.in_conflict:
                    continue
                state = p.status(filename)
                if state == '?':
                    # TODO: should ignore typical backup files suffix ~ or .orig
                    p.addfile(filename)
                elif state == '!':
                    p.delete_file(filename)
                    print(statfrmt('D', getTransActPath(os.path.join(p.dir, filename))))

    @cmdln.alias('ci')
    @cmdln.alias('checkin')
    @cmdln.option('-m', '--message', metavar='TEXT',
                  help='specify log message TEXT')
    @cmdln.option('-n', '--no-message', default=False, action='store_true',
                  help='do not specify a log message')
    @cmdln.option('-F', '--file', metavar='FILE',
                  help='read log message from FILE, \'-\' denotes standard input.')
    @cmdln.option('-f', '--force', default=False, action="store_true",
                  help='ignored')
    @cmdln.option('--skip-validation', default=False, action="store_true",
                  help='deprecated, don\'t use it')
    @cmdln.option('-v', '--verbose', default=False, action="store_true",
                  help='Run the source services with verbose information')
    @cmdln.option('--skip-local-service-run', '--noservice', default=False, action="store_true",
                  help='Skip service run of configured source services for local run')
    def do_commit(self, subcmd, opts, *args):
        """${cmd_name}: Upload content to the repository server

        Upload content which is changed in your working copy, to the repository
        server.

        examples:
           osc ci                   # current dir
           osc ci <dir>
           osc ci file1 file2 ...

        ${cmd_usage}
        ${cmd_option_list}
        """
        args = parseargs(args)

        if opts.skip_validation:
            print("WARNING: deprecated option --skip-validation ignored.", file=sys.stderr)

        msg = ''
        if opts.message:
            msg = opts.message
        elif opts.file:
            if opts.file == '-':
                msg = sys.stdin.read()
            else:
                try:
                    msg = open(opts.file).read()
                except:
                    sys.exit('could not open file \'%s\'.' % opts.file)
        skip_local_service_run = False
        if not conf.config['local_service_run'] or opts.skip_local_service_run:
            skip_local_service_run = True
        arg_list = args[:]
        for arg in arg_list:
            if conf.config['do_package_tracking'] and is_project_dir(arg):
                try:
                    prj = Project(arg)
                    if not msg and not opts.no_message:
                        msg = edit_message()

                    # check any of the packages is a link, if so, as for branching
                    pacs = (Package(os.path.join(prj.dir, pac))
                            for pac in prj.pacs_have if prj.get_state(pac) == ' ')
                    can_branch = False
                    if any(pac.is_link_to_different_project() for pac in pacs):
                        repl = raw_input('Some of the packages are links to a different project!\n' \
                                         'Create a local branch before commit? (y|N) ')
                        if repl in('y', 'Y'):
                            can_branch = True

                    prj.commit(msg=msg, skip_local_service_run=skip_local_service_run, verbose=opts.verbose, can_branch=can_branch)
                except oscerr.ExtRuntimeError as e:
                    print("ERROR: service run failed", e, file=sys.stderr)
                    return 1
                args.remove(arg)

        pacs = findpacs(args)

        if conf.config['do_package_tracking'] and len(pacs) > 0:
            prj_paths = {}
            single_paths = []
            files = {}
            # XXX: this is really ugly
            pac_objs = {}
            # it is possible to commit packages from different projects at the same
            # time: iterate over all pacs and put each pac to the right project in the dict
            for pac in pacs:
                path = os.path.normpath(os.path.join(pac.dir, os.pardir))
                if is_project_dir(path):
                    pac_path = os.path.basename(os.path.normpath(pac.absdir))
                    prj_paths.setdefault(path, []).append(pac_path)
                    pac_objs.setdefault(path, []).append(pac)
                    files[pac_path] = pac.todo
                else:
                    single_paths.append(pac.dir)
                    if not pac.todo:
                        pac.todo = pac.filenamelist + pac.filenamelist_unvers
                    pac.todo.sort()
            for prj_path, packages in prj_paths.items():
                prj = Project(prj_path)
                if not msg and not opts.no_message:
                    msg = get_commit_msg(prj.absdir, pac_objs[prj_path])

                # check any of the packages is a link, if so, as for branching
                can_branch = False
                if any(pac.is_link_to_different_project() for pac in pacs):
                    repl = raw_input('Some of the packages are links to a different project!\n' \
                                     'Create a local branch before commit? (y|N) ')
                    if repl in('y', 'Y'):
                        can_branch = True

                prj.commit(packages, msg=msg, files=files, skip_local_service_run=skip_local_service_run, verbose=opts.verbose, can_branch=can_branch)
                store_unlink_file(prj.absdir, '_commit_msg')
            for pac in single_paths:
                p = Package(pac)
                if not msg and not opts.no_message:
                    msg = get_commit_msg(p.absdir, [p])
                p.commit(msg, skip_local_service_run=skip_local_service_run, verbose=opts.verbose)
                store_unlink_file(p.absdir, '_commit_msg')
        else:
            for p in pacs:
                p = Package(pac)
                if not p.todo:
                    p.todo = p.filenamelist + p.filenamelist_unvers
                p.todo.sort()
                if not msg and not opts.no_message:
                    msg = get_commit_msg(p.absdir, [p])
                p.commit(msg, skip_local_service_run=skip_local_service_run, verbose=opts.verbose)
                store_unlink_file(p.absdir, '_commit_msg')

    @cmdln.option('-r', '--revision', metavar='REV',
                        help='update to specified revision (this option will be ignored '
                             'if you are going to update the complete project or more than '
                             'one package)')
    @cmdln.option('-u', '--unexpand-link', action='store_true',
                        help='if a package is an expanded link, update to the raw _link file')
    @cmdln.option('-e', '--expand-link', action='store_true',
                        help='if a package is a link, update to the expanded sources')
    @cmdln.option('-s', '--source-service-files', action='store_true',
                        help='Run local source services after update.' )
    @cmdln.option('-S', '--server-side-source-service-files', action='store_true',
                        help='Use server side generated sources instead of local generation.' )
    @cmdln.option('-l', '--limit-size', metavar='limit_size',
                        help='Skip all files with a given size')
    @cmdln.alias('up')
    def do_update(self, subcmd, opts, *args):
        """${cmd_name}: Update a working copy

        examples:

        1. osc up
                If the current working directory is a package, update it.
                If the directory is a project directory, update all contained
                packages, AND check out newly added packages.

                To update only checked out packages, without checking out new
                ones, you might want to use "osc up *" from within the project
                dir.

        2. osc up PAC
                Update the packages specified by the path argument(s)

        When --expand-link is used with source link packages, the expanded
        sources will be checked out. Without this option, the _link file and
        patches will be checked out. The option --unexpand-link can be used to
        switch back to the "raw" source with a _link file plus patch(es).

        ${cmd_usage}
        ${cmd_option_list}
        """

        if (opts.expand_link and opts.unexpand_link) \
            or (opts.expand_link and opts.revision) \
            or (opts.unexpand_link and opts.revision):
            raise oscerr.WrongOptions('Sorry, the options --expand-link, --unexpand-link and '
                     '--revision are mutually exclusive.')

        args = parseargs(args)
        arg_list = args[:]

        for arg in arg_list:
            if is_project_dir(arg):
                prj = Project(arg, progress_obj=self.download_progress)

                if conf.config['do_package_tracking']:
                    prj.update(expand_link=opts.expand_link,
                               unexpand_link=opts.unexpand_link)
                    args.remove(arg)
                else:
                    # if not tracking package, and 'update' is run inside a project dir,
                    # it should do the following:
                    # (a) update all packages
                    args += prj.pacs_have
                    # (b) fetch new packages
                    prj.checkout_missing_pacs(expand_link = not opts.unexpand_link)
                    args.remove(arg)
                print_request_list(prj.apiurl, prj.name)

        args.sort()
        pacs = findpacs(args, progress_obj=self.download_progress)

        if opts.revision and len(args) == 1:
            rev, dummy = parseRevisionOption(opts.revision)
            if not checkRevision(pacs[0].prjname, pacs[0].name, rev, pacs[0].apiurl):
                print('Revision \'%s\' does not exist' % rev, file=sys.stderr)
                sys.exit(1)
        else:
            rev = None

        for p in pacs:
            if len(pacs) > 1:
                print('Updating %s' % p.name)

            # this shouldn't be needed anymore with the new update mechanism
            # an expand/unexpand update is treated like a normal update (there's nothing special)
            # FIXME: ugly workaround for #399247
#            if opts.expand_link or opts.unexpand_link:
#                if [ i for i in p.filenamelist+p.filenamelist_unvers if p.status(i) != ' ' and p.status(i) != '?']:
#                    print >>sys.stderr, 'osc: cannot expand/unexpand because your working ' \
#                                        'copy has local modifications.\nPlease revert/commit them ' \
#                                        'and try again.'
#                    sys.exit(1)

            if not rev:
                if opts.expand_link and p.islink() and not p.isexpanded():
                    rev = p.latest_rev(expand=True)
                    print('Expanding to rev', rev)
                elif opts.unexpand_link and p.islink() and p.isexpanded():
                    rev = show_upstream_rev(p.apiurl, p.prjname, p.name, meta=p.meta)
                    print('Unexpanding to rev', rev)
                elif (p.islink() and p.isexpanded()) or opts.server_side_source_service_files:
                    rev = p.latest_rev(include_service_files=opts.server_side_source_service_files)

            p.update(rev, opts.server_side_source_service_files, opts.limit_size)
            if opts.source_service_files:
                print('Running local source services')
                p.run_source_services()
            if opts.unexpand_link:
                p.unmark_frozen()
            rev = None
            print_request_list(p.apiurl, p.prjname, p.name)


    @cmdln.option('-f', '--force', action='store_true',
                        help='forces removal of entire package and its files')
    @cmdln.alias('rm')
    @cmdln.alias('del')
    @cmdln.alias('remove')
    def do_delete(self, subcmd, opts, *args):
        """${cmd_name}: Mark files or package directories to be deleted upon the next 'checkin'

        usage:
            cd .../PROJECT/PACKAGE
            osc delete FILE [...]
            cd .../PROJECT
            osc delete PACKAGE [...]

        This command works on check out copies. Use "rdelete" for working on server
        side only. This is needed for removing the entire project.

        As a safety measure, projects must be empty (i.e., you need to delete all
        packages first).

        If you are sure that you want to remove a package and all
        its files use \'--force\' switch. Sometimes this also works without --force.

        ${cmd_option_list}
        """

        if not args:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('delete'))

        args = parseargs(args)
        # check if args contains a package which was removed by
        # a non-osc command and mark it with the 'D'-state
        arg_list = args[:]
        for i in arg_list:
            if not os.path.exists(i):
                prj_dir, pac_dir = getPrjPacPaths(i)
                if is_project_dir(prj_dir):
                    prj = Project(prj_dir, False)
                    if i in prj.pacs_broken:
                        if prj.get_state(i) != 'A':
                            prj.set_state(pac_dir, 'D')
                        else:
                            prj.del_package_node(i)
                        print(statfrmt('D', getTransActPath(i)))
                        args.remove(i)
                        prj.write_packages()
        pacs = findpacs(args)

        for p in pacs:
            if not p.todo:
                prj_dir, pac_dir = getPrjPacPaths(p.absdir)
                if is_project_dir(prj_dir):
                    if conf.config['do_package_tracking']:
                        prj = Project(prj_dir, False)
                        prj.delPackage(p, opts.force)
                    else:
                        print("WARNING: package tracking is disabled, operation skipped !", file=sys.stderr)
            else:
                pathn = getTransActPath(p.dir)
                for filename in p.todo:
                    p.clear_from_conflictlist(filename)
                    ret, state = p.delete_file(filename, opts.force)
                    if ret:
                        print(statfrmt('D', os.path.join(pathn, filename)))
                        continue
                    if state == '?':
                        sys.exit('\'%s\' is not under version control' % filename)
                    elif state in ['A', 'M'] and not opts.force:
                        sys.exit('\'%s\' has local modifications (use --force to remove this file)' % filename)
                    elif state == 'S':
                        sys.exit('\'%s\' is marked as skipped and no local file with this name exists' % filename)


    def do_resolved(self, subcmd, opts, *args):
        """${cmd_name}: Remove 'conflicted' state on working copy files

        If an upstream change can't be merged automatically, a file is put into
        in 'conflicted' ('C') state. Within the file, conflicts are marked with
        special <<<<<<< as well as ======== and >>>>>>> lines.

        After manually resolving all conflicting parts, use this command to
        remove the 'conflicted' state.

        Note:  this subcommand does not semantically resolve conflicts or
        remove conflict markers; it merely removes the conflict-related
        artifact files and allows PATH to be committed again.

        usage:
            osc resolved FILE [FILE...]
        ${cmd_option_list}
        """

        if not args:
            raise oscerr.WrongArgs('Missing argument.\n\n' \
                  + self.get_cmd_help('resolved'))

        args = parseargs(args)
        pacs = findpacs(args)

        for p in pacs:
            for filename in p.todo:
                print('Resolved conflicted state of "%s"' % filename)
                p.clear_from_conflictlist(filename)


    @cmdln.alias('dists')
# FIXME: using just ^DISCONTINUED as match is not a general approach and only valid for one instance
#        we need to discuss an api call for that, if we need this
#    @cmdln.option('-d', '--discontinued', action='store_true',
#                        help='show discontinued distributions')
    def do_distributions(self, subcmd, opts, *args):
        """${cmd_name}: Shows all available distributions

        This command shows the available distributions. For active distributions
        it shows the name, project and name of the repository and a suggested default repository name. 

        usage:
            osc distributions                           

        ${cmd_option_list}
        """
        apiurl = self.get_api_url()

        print('\n'.join(get_distibutions(apiurl)))#FIXME:, opts.discontinued))

    @cmdln.hide(1)
    def do_results_meta(self, subcmd, opts, *args):
        print("Command results_meta is obsolete. Please use: osc results --xml")
        sys.exit(1)

    @cmdln.hide(1)
    @cmdln.option('-l', '--last-build', action='store_true',
                        help='show last build results (succeeded/failed/unknown)')
    @cmdln.option('-r', '--repo', action='append', default = [],
                        help='Show results only for specified repo(s)')
    @cmdln.option('-a', '--arch', action='append', default = [],
                        help='Show results only for specified architecture(s)')
    @cmdln.option('', '--xml', action='store_true',
                        help='generate output in XML (former results_meta)')
    def do_rresults(self, subcmd, opts, *args):
        print("Command rresults is obsolete. Running 'osc results' instead")
        self.do_results('results', opts, *args)
        sys.exit(1)


    @cmdln.option('-f', '--force', action='store_true', default=False,
                        help="Don't ask and delete files")
    def do_rremove(self, subcmd, opts, project, package, *files):
        """${cmd_name}: Remove source files from selected package

        ${cmd_usage}
        ${cmd_option_list}
        """
        apiurl = self.get_api_url()

        if len(files) == 0:
            if not '/' in project:
                raise oscerr.WrongArgs("Missing operand, type osc help rremove for help")
            else:
                files = (package, )
                project, package = project.split('/')

        for filename in files:
            if not opts.force:
                resp = raw_input("rm: remove source file `%s' from `%s/%s'? (yY|nN) " % (filename, project, package))
                if resp not in ('y', 'Y'):
                    continue
            try:
                delete_files(apiurl, project, package, (filename, ))
            except HTTPError as e:
                if opts.force:
                    print(e, file=sys.stderr)
                    body = e.read()
                    if e.code in [ 400, 403, 404, 500 ]:
                        if '<summary>' in body:
                            msg = body.split('<summary>')[1]
                            msg = msg.split('</summary>')[0]
                            print(msg, file=sys.stderr)
                else:
                    raise e

    @cmdln.alias('r')
    @cmdln.option('-l', '--last-build', action='store_true',
                        help='show last build results (succeeded/failed/unknown)')
    @cmdln.option('-r', '--repo', action='append', default = [],
                        help='Show results only for specified repo(s)')
    @cmdln.option('-a', '--arch', action='append', default = [],
                        help='Show results only for specified architecture(s)')
    @cmdln.option('-v', '--verbose', action='store_true', default=False,
                        help='more verbose output')
    @cmdln.option('-w', '--watch', action='store_true', default=False,
                        help='watch the results until all finished building')
    @cmdln.option('', '--xml', action='store_true', default=False,
                        help='generate output in XML (former results_meta)')
    @cmdln.option('', '--csv', action='store_true', default=False,
                        help='generate output in CSV format')
    @cmdln.option('', '--format', default='%(repository)s|%(arch)s|%(state)s|%(dirty)s|%(code)s|%(details)s',
                        help='format string for csv output')
    def do_results(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build results of a package or project

        Usage:
            osc results                 # (inside working copy of PRJ or PKG)
            osc results PROJECT [PACKAGE]

        ${cmd_option_list}
        """

        args = slash_split(args)

        apiurl = self.get_api_url()
        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments (required none, one, or two)')
        project = package = None
        wd = os.curdir
        if is_project_dir(wd):
            project = store_read_project(wd)
        elif is_package_dir(wd):
            project = store_read_project(wd)
            package = store_read_package(wd)
        if len(args) > 0:
            project = args[0]
        if len(args) > 1:
            package = args[1]

        if project == None:
            raise oscerr.WrongOptions("No project given")

        if package == None:
            if opts.arch == []:
                opts.arch = None
            if opts.repo == []:
                opts.repo = None
            opts.hide_legend = None
            opts.name_filter = None
            opts.status_filter = None
            opts.vertical = None
            opts.show_non_building = None
            opts.show_excluded = None
            self.do_prjresults('prjresults', opts, *args)
            return

        if opts.xml and opts.csv:
            raise oscerr.WrongOptions("--xml and --csv are mutual exclusive")

        args = [ apiurl, project, package, opts.last_build, opts.repo, opts.arch ]
        if opts.xml:
            print(''.join(show_results_meta(*args)), end=' ')
        elif opts.csv:
            # ignore _oldstate key
            results = [r for r in get_package_results(*args) if not '_oldstate' in r]
            print('\n'.join(format_results(results, opts.format)))
        else:
            args.append(opts.verbose)
            args.append(opts.watch)
            args.append("\n")
            get_results(*args)

    # WARNING: this function is also called by do_results. You need to set a default there
    #          as well when adding a new option!
    @cmdln.option('-q', '--hide-legend', action='store_true',
                        help='hide the legend')
    @cmdln.option('-c', '--csv', action='store_true',
                        help='csv output')
    @cmdln.option('', '--xml', action='store_true', default=False,
                        help='generate output in XML')
    @cmdln.option('-s', '--status-filter', metavar='STATUS',
                        help='show only packages with buildstatus STATUS (see legend)')
    @cmdln.option('-n', '--name-filter', metavar='EXPR',
                        help='show only packages whose names match EXPR')
    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='show results only for specified architecture(s)')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='show results only for specified repo(s)')
    @cmdln.option('-V', '--vertical', action='store_true',
                        help='list packages vertically instead horizontally')
    @cmdln.option('--show-excluded', action='store_true',
                        help='show packages that are excluded in all repos, also hide repos that have only excluded packages')
    @cmdln.alias('pr')
    def do_prjresults(self, subcmd, opts, *args):
        """${cmd_name}: Shows project-wide build results

        Usage:
            osc prjresults (inside working copy)
            osc prjresults PROJECT

        ${cmd_option_list}
        """
        apiurl = self.get_api_url()

        if args:
            if len(args) == 1:
                project = args[0]
            else:
                raise oscerr.WrongArgs('Wrong number of arguments.')
        else:
            wd = os.curdir
            project = store_read_project(wd)

        if opts.xml:
            print(''.join(show_prj_results_meta(apiurl, project)))
            return

        print('\n'.join(get_prj_results(apiurl, project, hide_legend=opts.hide_legend, \
                                        csv=opts.csv, status_filter=opts.status_filter, \
                                        name_filter=opts.name_filter, repo=opts.repo, \
                                        arch=opts.arch, vertical=opts.vertical, \
                                        show_excluded=opts.show_excluded)))

    @cmdln.option('-q', '--hide-legend', action='store_true',
                        help='hide the legend')
    @cmdln.option('-c', '--csv', action='store_true',
                        help='csv output')
    @cmdln.option('-s', '--status-filter', metavar='STATUS',
                        help='show only packages with buildstatus STATUS (see legend)')
    @cmdln.option('-n', '--name-filter', metavar='EXPR',
                        help='show only packages whose names match EXPR')

    @cmdln.hide(1)
    def do_rprjresults(self, subcmd, opts, *args):
        print("Command rprjresults is obsolete. Please use 'osc prjresults'")
        sys.exit(1)

    @cmdln.alias('bl')
    @cmdln.alias('blt')
    @cmdln.alias('buildlogtail')
    @cmdln.option('-l', '--last', action='store_true',
                        help='Show the last finished log file')
    @cmdln.option('-o', '--offset', metavar='OFFSET',
                    help='get log start or end from the offset')
    @cmdln.option('-s', '--strip-time', action='store_true',
                        help='strip leading build time from the log')
    def do_buildlog(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build log of a package

        Shows the log file of the build of a package. Can be used to follow the
        log while it is being written.
        Needs to be called from within a package directory.

        When called as buildlogtail (or blt) it just shows the end of the logfile.
        This is useful to see just a build failure reasons.

        The arguments REPOSITORY and ARCH are the first two columns in the 'osc
        results' output. If the buildlog url is used buildlog command has the
        same behavior as remotebuildlog.

        ${cmd_usage} [REPOSITORY ARCH | BUILDLOGURL]
        ${cmd_option_list}
        """

        repository = arch = None

        apiurl = self.get_api_url()

        if len(args) == 1 and args[0].startswith('http'):
            apiurl, project, package, repository, arch = parse_buildlogurl(args[0])
        elif len(args) < 2:
            self.print_repos()
        elif len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')
        else:
            wd = os.curdir
            package = store_read_package(wd)
            project = store_read_project(wd)
            repository = args[0]
            arch = args[1]

        offset = 0
        if subcmd == "blt" or subcmd == "buildlogtail":
            query = { 'view': 'entry' }
            if opts.last:
                query['last'] = 1
            u = makeurl(self.get_api_url(), ['build', project, repository, arch, package, '_log'], query=query)
            f = http_GET(u)
            root = ET.parse(f).getroot()
            offset = int(root.find('entry').get('size'))
            if opts.offset:
                offset = offset - int(opts.offset)
            else:
                offset = offset - ( 8 * 1024 )
            if offset < 0:
                offset = 0
        elif opts.offset:
            offset = int(opts.offset)
        strip_time = opts.strip_time or conf.config['buildlog_strip_time']
        print_buildlog(apiurl, project, package, repository, arch, offset, strip_time, opts.last)


    def print_repos(self, repos_only=False, exc_class=oscerr.WrongArgs, exc_msg='Missing arguments'):
        wd = os.curdir
        doprint = False
        if is_package_dir(wd):
            msg = "package"
            doprint = True
        elif is_project_dir(wd):
            msg = "project"
            doprint = True

        if doprint:
            print('Valid arguments for this %s are:' % msg)
            print()
            if repos_only:
                self.do_repositories("repos_only", None)
            else:
                self.do_repositories(None, None)
        raise exc_class(exc_msg)

    @cmdln.alias('rbl')
    @cmdln.alias('rbuildlog')
    @cmdln.alias('rblt')
    @cmdln.alias('rbuildlogtail')
    @cmdln.alias('remotebuildlogtail')
    @cmdln.option('-l', '--last', action='store_true',
                        help='Show the last finished log file')
    @cmdln.option('-o', '--offset', metavar='OFFSET',
                    help='get log starting or ending from the offset')
    @cmdln.option('-s', '--strip-time', action='store_true',
                        help='strip leading build time from the log')
    def do_remotebuildlog(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build log of a package

        Shows the log file of the build of a package. Can be used to follow the
        log while it is being written.

        remotebuildlogtail shows just the tail of the log file.

        usage:
            osc remotebuildlog project package repository arch
            or
            osc remotebuildlog project/package/repository/arch
            or
            osc remotebuildlog buildlogurl
        ${cmd_option_list}
        """
        if len(args) == 1 and args[0].startswith('http'):
            apiurl, project, package, repository, arch = parse_buildlogurl(args[0])
        else:
            args = slash_split(args)
            apiurl = self.get_api_url()
            if len(args) < 4:
                raise oscerr.WrongArgs('Too few arguments.')
            elif len(args) > 4:
                raise oscerr.WrongArgs('Too many arguments.')
            else:
                project, package, repository, arch = args

        offset = 0
        if subcmd == "rblt" or subcmd == "rbuildlogtail" or subcmd == "remotebuildlogtail":
            query = { 'view': 'entry' }
            if opts.last:
                query['last'] = 1
            u = makeurl(self.get_api_url(), ['build', project, repository, arch, package, '_log'], query=query)
            f = http_GET(u)
            root = ET.parse(f).getroot()
            offset = int(root.find('entry').get('size'))
            if opts.offset:
                offset = offset - int(opts.offset)
            else:
                offset = offset - ( 8 * 1024 )
            if offset < 0:
                offset = 0
        elif opts.offset:
            offset = int(opts.offset)
        strip_time = opts.strip_time or conf.config['buildlog_strip_time']
        print_buildlog(apiurl, project, package, repository, arch, offset, strip_time, opts.last)

    @cmdln.alias('lbl')
    @cmdln.option('-o', '--offset', metavar='OFFSET',
                  help='get log starting from offset')
    @cmdln.option('-s', '--strip-time', action='store_true',
                        help='strip leading build time from the log')
    def do_localbuildlog(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build log of a local buildchroot

        usage:
            osc lbl [REPOSITORY [ARCH]]
            osc lbl # show log of newest last local build

        ${cmd_option_list}
        """
        if conf.config['build-type']:
            # FIXME: raise Exception instead
            print('Not implemented for VMs', file=sys.stderr)
            sys.exit(1)

        if len(args) == 0 or len(args) == 1:
            package = store_read_package('.')
            import glob
            files = glob.glob(os.path.join(os.getcwd(), store, "_buildinfo-*"))
            if args:
                files = [f for f in files
                         if os.path.basename(f).replace('_buildinfo-', '').startswith(args[0] + '-')]
            if not files:
                self.print_repos()
            cfg = files[0]
            # find newest file
            for f in files[1:]:
                if os.stat(f).st_mtime > os.stat(cfg).st_mtime:
                    cfg = f
            root = ET.parse(cfg).getroot()
            project = root.get("project")
            repo = root.get("repository")
            arch = root.find("arch").text
        elif len(args) == 2:
            project = store_read_project('.')
            package = store_read_package('.')
            repo = args[0]
            arch = args[1]
        else:
            if is_package_dir(os.curdir):
                self.print_repos()
            raise oscerr.WrongArgs('Wrong number of arguments.')

        buildroot = os.environ.get('OSC_BUILD_ROOT', conf.config['build-root'])
        buildroot = buildroot % {'project': project, 'package': package,
                                 'repo': repo, 'arch': arch}
        offset = 0
        if opts.offset:
            offset = int(opts.offset)
        logfile = os.path.join(buildroot, '.build.log')
        if not os.path.isfile(logfile):
            raise oscerr.OscIOError(None, 'logfile \'%s\' does not exist' % logfile)
        f = open(logfile, 'r')
        f.seek(offset)
        data = f.read(BUFSIZE)
        while len(data):
            if opts.strip_time or conf.config['buildlog_strip_time']:
                data = buildlog_strip_time(data)
            sys.stdout.write(data)
            data = f.read(BUFSIZE)
        f.close()

    @cmdln.alias('tr')
    def do_triggerreason(self, subcmd, opts, *args):
        """${cmd_name}: Show reason why a package got triggered to build

        The server decides when a package needs to get rebuild, this command
        shows the detailed reason for a package. A brief reason is also stored
        in the jobhistory, which can be accessed via "osc jobhistory".

        Trigger reasons might be:
          - new build (never build yet or rebuild manually forced)
          - source change (eg. on updating sources)
          - meta change (packages which are used for building have changed)
          - rebuild count sync (In case that it is configured to sync release numbers)

        usage in package or project directory:
            osc reason REPOSITORY ARCH
            osc reason PROJECT PACKAGE REPOSITORY ARCH

        ${cmd_option_list}
        """
        wd = os.curdir
        args = slash_split(args)
        project = package = repository = arch = None

        if len(args) < 2:
            self.print_repos()
        
        apiurl = self.get_api_url()

        if len(args) == 2: # 2
            if is_package_dir('.'):
                package = store_read_package(wd)
            else:
                raise oscerr.WrongArgs('package is not specified.')
            project = store_read_project(wd)
            repository = args[0]
            arch = args[1]
        elif len(args) == 4:
            project = args[0]
            package = args[1]
            repository = args[2]
            arch = args[3]
        else:
            raise oscerr.WrongArgs('Too many arguments.')

        print(apiurl, project, package, repository, arch)
        xml = show_package_trigger_reason(apiurl, project, package, repository, arch)
        root = ET.fromstring(xml)
        reason = root.find('explain').text
        print(reason)
        if reason == "meta change":
            print("changed keys:")
            for package in root.findall('packagechange'):
                print("  ", package.get('change'), package.get('key'))


    # FIXME: the new osc syntax should allow to specify multiple packages
    # FIXME: the command should optionally use buildinfo data to show all dependencies
    @cmdln.alias('whatdependson')
    def do_dependson(self, subcmd, opts, *args):
        """${cmd_name}: Show the build dependencies

        The command dependson and whatdependson can be used to find out what
        will be triggered when a certain package changes.
        This is no guarantee, since the new build might have changed dependencies.

        dependson shows the build dependencies inside of a project, valid for a
        given repository and architecture.
        NOTE: to see all binary packages, which can trigger a build you need to
              refer the buildinfo, since this command shows only the dependencies
              inside of a project.

        The arguments REPOSITORY and ARCH can be taken from the first two columns
        of the 'osc repos' output.

        usage in package or project directory:
            osc dependson REPOSITORY ARCH
            osc whatdependson REPOSITORY ARCH

        usage:
            osc dependson PROJECT [PACKAGE] REPOSITORY ARCH
            osc whatdependson PROJECT [PACKAGE] REPOSITORY ARCH

        ${cmd_option_list}
        """
        wd = os.curdir
        args = slash_split(args)
        project = packages = repository = arch = reverse = None

        if len(args) < 2 and (is_package_dir('.') or is_project_dir('.')):
            self.print_repos()

        if len(args) > 4:
            raise oscerr.WrongArgs('Too many arguments.')

        apiurl = self.get_api_url()

        if len(args) < 3: # 2
            if is_package_dir('.'):
                packages = [store_read_package(wd)]
            elif not is_project_dir('.'):
                raise oscerr.WrongArgs('Project and package is not specified.')
            project = store_read_project(wd)
            repository = args[0]
            arch = args[1]

        if len(args) == 3:
            project = args[0]
            repository = args[1]
            arch = args[2]

        if len(args) == 4:
            project = args[0]
            packages = [args[1]]
            repository = args[2]
            arch = args[3]

        if subcmd == 'whatdependson':
            reverse = 1

        xml = get_dependson(apiurl, project, repository, arch, packages, reverse)

        root = ET.fromstring(xml)
        for package in root.findall('package'):
            print(package.get('name'), ":")
            for dep in package.findall('pkgdep'):
                print("  ", dep.text)


    @cmdln.option('-d', '--debug', action='store_true',
                  help='verbose output of build dependencies')
    @cmdln.option('-x', '--extra-pkgs', metavar='PAC', action='append',
                  help='Add this package when computing the buildinfo')
    @cmdln.option('-p', '--prefer-pkgs', metavar='DIR', action='append',
                  help='Prefer packages from this directory when installing the build-root')
    def do_buildinfo(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build info

        Shows the build "info" which is used in building a package.
        This command is mostly used internally by the 'build' subcommand.
        It needs to be called from within a package directory.

        The BUILD_DESCR argument is optional. BUILD_DESCR is a local RPM specfile
        or Debian "dsc" file. If specified, it is sent to the server, and the
        buildinfo will be based on it. If the argument is not supplied, the
        buildinfo is derived from the specfile which is currently on the source
        repository server.

        The returned data is XML and contains a list of the packages used in
        building, their source, and the expanded BuildRequires.

        The arguments REPOSITORY and ARCH are optional. They can be taken from
        the first two columns of the 'osc repos' output. If not specified,
        REPOSITORY defaults to the 'build_repositoy' config entry in your '.oscrc'
        and ARCH defaults to your host architecture.

        usage:
            in a package working copy:
                osc buildinfo [OPTS] REPOSITORY ARCH BUILD_DESCR
                osc buildinfo [OPTS] REPOSITORY (ARCH = hostarch, BUILD_DESCR is detected automatically)
                osc buildinfo [OPTS] ARCH (REPOSITORY = build_repository (config option), BUILD_DESCR is detected automatically)
                osc buildinfo [OPTS] BUILD_DESCR (REPOSITORY = build_repository (config option), ARCH = hostarch)
                osc buildinfo [OPTS] (REPOSITORY = build_repository (config option), ARCH = hostarch, BUILD_DESCR is detected automatically)
                Note: if BUILD_DESCR does not exist locally the remote BUILD_DESCR is used

            osc buildinfo [OPTS] PROJECT PACKAGE REPOSITORY ARCH [BUILD_DESCR]

        ${cmd_option_list}
        """
        wd = os.curdir
        args = slash_split(args)

        project = package = repository = arch = build_descr = None
        if len(args) <= 3:
            if not is_package_dir('.'):
                raise oscerr.WrongArgs('Incorrect number of arguments (Note: \'.\' is no package wc)')
            project = store_read_project('.')
            package = store_read_package('.')
            repository, arch, build_descr = self.parse_repoarchdescr(args, ignore_descr=True)
        elif len(args) == 4 or len(args) == 5:
            project = args[0]
            package = args[1]
            repository = args[2]
            arch = args[3]
            if len(args) == 5:
                build_descr = args[4]
        else:
            raise oscerr.WrongArgs('Too many arguments.')

        apiurl = self.get_api_url()

        build_descr_data = None
        if not build_descr is None:
            build_descr_data = open(build_descr, 'r').read()
        if opts.prefer_pkgs and build_descr_data is None:
            raise oscerr.WrongArgs('error: a build description is needed if \'--prefer-pkgs\' is used')
        elif opts.prefer_pkgs:
            from .build import get_prefer_pkgs
            print('Scanning the following dirs for local packages: %s' % ', '.join(opts.prefer_pkgs))
            prefer_pkgs, cpio = get_prefer_pkgs(opts.prefer_pkgs, arch, os.path.splitext(args[2])[1])
            cpio.add(os.path.basename(args[2]), build_descr_data)
            build_descr_data = cpio.get()

        print(''.join(get_buildinfo(apiurl,
                                    project, package, repository, arch,
                                    specfile=build_descr_data,
                                    debug=opts.debug,
                                    addlist=opts.extra_pkgs)))


    def do_buildconfig(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build config

        Shows the build configuration which is used in building a package.
        This command is mostly used internally by the 'build' command.

        The returned data is the project-wide build configuration in a format
        which is directly readable by the build script. It contains RPM macros
        and BuildRequires expansions, for example.

        The argument REPOSITORY an be taken from the first column of the 
        'osc repos' output.

        usage:
            osc buildconfig REPOSITORY                      (in pkg or prj dir)
            osc buildconfig PROJECT REPOSITORY
        ${cmd_option_list}
        """

        wd = os.curdir
        args = slash_split(args)

        if len(args) < 1 and (is_package_dir('.') or is_project_dir('.')):
            self.print_repos(True)

        if len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments.')

        apiurl = self.get_api_url()

        if len(args) == 1:
            #FIXME: check if args[0] is really a repo and not a project, need a is_project() function for this
            project = store_read_project(wd)
            repository = args[0]
        elif len(args) == 2:
            project = args[0]
            repository = args[1]
        else:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        print(''.join(get_buildconfig(apiurl, project, repository)))


    @cmdln.alias('repos')
    @cmdln.alias('platforms')
    def do_repositories(self, subcmd, opts, *args):
        """${cmd_name}: shows repositories configured for a project.
                        It skips repositories by default which are disabled for a given package.

        usage:
            osc repos
            osc repos [PROJECT] [PACKAGE]

        ${cmd_option_list}
        """

        apiurl = self.get_api_url()
        project = None
        package = None
        disabled = None

        if len(args) == 1:
            project = args[0]
        elif len(args) == 2:
            project = args[0]
            package = args[1]
        elif len(args) == 0:
            if is_package_dir('.'):
                package = store_read_package('.')
                project = store_read_project('.')
            elif is_project_dir('.'):
                project = store_read_project('.')
        else:
            raise oscerr.WrongArgs('Wrong number of arguments')

        if project is None:
            raise oscerr.WrongArgs('No project specified')

        if package is not None:
            disabled = show_package_disabled_repos(apiurl, project, package)

        if subcmd == 'repos_only':
            for repo in get_repositories_of_project(apiurl, project): 
                if (disabled is None) or ((disabled is not None) and (repo not in disabled)):
                    print(repo)
        else:
            data = []
            for repo in get_repos_of_project(apiurl, project):
                if (disabled is None) or ((disabled is not None) and (repo.name not in disabled)):
                    data += [repo.name, repo.arch]
        
            for row in build_table(2, data, width=2):
                print(row)


    def parse_repoarchdescr(self, args, noinit = False, alternative_project = None, ignore_descr = False, vm_type = None):
        """helper to parse the repo, arch and build description from args"""
        import osc.build
        import glob
        arg_arch = arg_repository = arg_descr = None
        if len(args) < 3:
            # some magic, works only sometimes, but people seem to like it :/
            all_archs = []
            for mainarch in osc.build.can_also_build:
                all_archs.append(mainarch)
                for subarch in osc.build.can_also_build.get(mainarch):
                    all_archs.append(subarch)
            for arg in args:
                if arg.endswith('.spec') or arg.endswith('.dsc') or arg.endswith('.kiwi') or arg == 'PKGBUILD':
                    arg_descr = arg
                else:
                    if (arg == osc.build.hostarch or arg in all_archs) and arg_arch is None:
                        # it seems to be an architecture in general
                        arg_arch = arg
                        if not (arg in osc.build.can_also_build.get(osc.build.hostarch) or arg == osc.build.hostarch):
                            print("WARNING: native compile is not possible, an emulator must be configured!")
                    elif not arg_repository:
                        arg_repository = arg
                    else:
                        raise oscerr.WrongArgs('unexpected argument: \'%s\'' % arg)
        else:
            arg_repository, arg_arch, arg_descr = args

        arg_arch = arg_arch or osc.build.hostarch

        repositories = []
        # store list of repos for potential offline use
        repolistfile = os.path.join(os.getcwd(), osc.core.store, "_build_repositories")
        if noinit:
            if os.path.exists(repolistfile):
                f = open(repolistfile, 'r')
                repositories = [ l.strip()for l in f.readlines()]
                f.close()
        else:
            project = alternative_project or store_read_project('.')
            apiurl = self.get_api_url()
            repositories = get_repositories_of_project(apiurl, project)
            if not len(repositories):
                raise oscerr.WrongArgs('no repositories defined for project \'%s\'' % project)
            try:
                f = open(repolistfile, 'w')
                f.write('\n'.join(repositories) + '\n')
                f.close()
            except:
                pass

        if not arg_repository and len(repositories):
            # Use a default value from config, but just even if it's available
            # unless try standard, or openSUSE_Factory
            arg_repository = repositories[-1]
            for repository in (conf.config['build_repository'], 'standard', 'openSUSE_Factory'):
                if repository in repositories:
                    arg_repository = repository
                    break

        if not arg_repository:
            raise oscerr.WrongArgs('please specify a repository')
        elif noinit == False and not arg_repository in repositories:
            raise oscerr.WrongArgs('%s is not a valid repository, use one of: %s' % (arg_repository, ', '.join(repositories)))

        # can be implemented using
        # reduce(lambda x, y: x + y, (glob.glob(x) for x in ('*.spec', '*.dsc', '*.kiwi')))
        # but be a bit more readable :)
        descr = glob.glob('*.spec') + glob.glob('*.dsc') + glob.glob('*.kiwi') + glob.glob('PKGBUILD')
        
        # FIXME:
        # * request repos from server and select by build type.
        if not arg_descr and len(descr) == 1:
            arg_descr = descr[0]
        elif not arg_descr:
            msg = None
            if len(descr) > 1:
                # guess/prefer build descrs like the following:
                # <pac>-<repo>.<ext> > <pac>.<ext>
                # no guessing for arch's PKGBUILD files (the backend does not do any guessing, too)
                pac = os.path.basename(os.getcwd())
                if is_package_dir(os.getcwd()):
                    pac = store_read_package(os.getcwd())
                extensions = ['spec', 'dsc', 'kiwi']
                cands = [i for i in descr for ext in extensions if i == '%s-%s.%s' % (pac, arg_repository, ext)]
                if len(cands) == 1:
                    arg_descr = cands[0]
                else:
                    cands = [i for i in descr for ext in extensions if i == '%s.%s' % (pac, ext)]
                    if len(cands) == 1:
                        arg_descr = cands[0]
                if not arg_descr:
                    msg = 'Multiple build description files found: %s' % ', '.join(descr)
            elif not ignore_descr:
                msg = 'Missing argument: build description (spec, dsc or kiwi file)'
                try:
                    p = Package('.')
                    if p.islink() and not p.isexpanded():
                        msg += ' (this package is not expanded - you might want to try osc up --expand)'
                except:
                    pass
            if msg:
                raise oscerr.WrongArgs(msg)

        return arg_repository, arg_arch, arg_descr


    @cmdln.option('--clean', action='store_true',
                  help='Delete old build root before initializing it')
    @cmdln.option('-o', '--offline', action='store_true',
                  help='Start with cached prjconf and packages without contacting the api server')
    @cmdln.option('-l', '--preload', action='store_true',
                  help='Preload all files into the cache for offline operation')
    @cmdln.option('--no-changelog', action='store_true',
                  help='don\'t update the package changelog from a changes file')
    @cmdln.option('--rsync-src', metavar='RSYNCSRCPATH', dest='rsyncsrc',
                  help='Copy folder to buildroot after installing all RPMs. Use together with --rsync-dest. This is the path on the HOST filesystem e.g. /tmp/linux-kernel-tree. It defines RSYNCDONE 1 .')
    @cmdln.option('--rsync-dest', metavar='RSYNCDESTPATH', dest='rsyncdest',
                  help='Copy folder to buildroot after installing all RPMs. Use together with --rsync-src. This is the path on the TARGET filesystem e.g. /usr/src/packages/BUILD/linux-2.6 .')
    @cmdln.option('--overlay', metavar='OVERLAY',
                  help='Copy overlay filesystem to buildroot after installing all RPMs .')
    @cmdln.option('--noinit', '--no-init', action='store_true',
                  help='Skip initialization of build root and start with build immediately.')
    @cmdln.option('--nochecks', '--no-checks', action='store_true',
                  help='Do not run build checks on the resulting packages.')
    @cmdln.option('--no-verify', '--noverify', action='store_true',
                  help='Skip signature verification of packages used for build. (Global config in .oscrc: no_verify)')
    @cmdln.option('--noservice', '--no-service', action='store_true',
                  help='Skip run of local source services as specified in _service file.')
    @cmdln.option('-p', '--prefer-pkgs', metavar='DIR', action='append',
                  help='Prefer packages from this directory when installing the build-root')
    @cmdln.option('-k', '--keep-pkgs', metavar='DIR',
                  help='Save built packages into this directory')
    @cmdln.option('-x', '--extra-pkgs', metavar='PAC', action='append',
                  help='Add this package when installing the build-root')
    @cmdln.option('--root', metavar='ROOT',
                  help='Build in specified directory')
    @cmdln.option('-j', '--jobs', metavar='N',
                  help='Compile with N jobs')
    @cmdln.option('--icecream', metavar='N',
                  help='use N parallel build jobs with icecream')
    @cmdln.option('--ccache', action='store_true',
                  help='use ccache to speed up rebuilds')
    @cmdln.option('--with', metavar='X', dest='_with', action='append',
                  help='enable feature X for build')
    @cmdln.option('--without', metavar='X', action='append',
                  help='disable feature X for build')
    @cmdln.option('--define', metavar='\'X Y\'', action='append',
                  help='define macro X with value Y')
    @cmdln.option('--userootforbuild', action='store_true',
                  help='Run build as root. The default is to build as '
                  'unprivileged user. Note that a line "# norootforbuild" '
                  'in the spec file will invalidate this option.')
    @cmdln.option('--build-uid', metavar='uid:gid|"caller"',
                  help='specify the numeric uid:gid pair to assign to the '
                  'unprivileged "abuild" user or use "caller" to use the current user uid:gid')
    @cmdln.option('--local-package', action='store_true',
                  help='build a package which does not exist on the server')
    @cmdln.option('--linksources', action='store_true',
                  help='use hard links instead of a deep copied source')
    @cmdln.option('--vm-type', metavar='TYPE',
                  help='use VM type TYPE (e.g. kvm)')
    @cmdln.option('--target', metavar='TARGET',
                  help='define target platform')
    @cmdln.option('--alternative-project', metavar='PROJECT',
                  help='specify the build target project')
    @cmdln.option('-d', '--debuginfo', action='store_true',
                  help='also build debuginfo sub-packages')
    @cmdln.option('--disable-debuginfo', action='store_true',
                  help='disable build of debuginfo packages')
    @cmdln.option('-b', '--baselibs', action='store_true',
                  help='Create -32bit/-64bit/-x86 rpms for other architectures')
    @cmdln.option('--release', metavar='N',
                  help='set release number of the package to N')
    @cmdln.option('--disable-cpio-bulk-download', action='store_true',
                  help='disable downloading packages as cpio archive from api')
    @cmdln.option('--cpio-bulk-download', action='store_false',
                  dest='disable_cpio_bulk_download', help=SUPPRESS_HELP)
    @cmdln.option('--download-api-only', action='store_true',
                  help='only fetch packages from the api')
    @cmdln.option('--oldpackages', metavar='DIR',
            help='take previous build from DIR (special values: _self, _link)')
    @cmdln.option('--shell', action='store_true',
                  help=SUPPRESS_HELP)
    @cmdln.option('--host', metavar='HOST',
            help='perform the build on a remote server - user@server:~/remote/directory')
    def do_build(self, subcmd, opts, *args):
        """${cmd_name}: Build a package on your local machine

        You need to call the command inside a package directory, which should be a
        buildsystem checkout. (Local modifications are fine.)

        The arguments REPOSITORY and ARCH can be taken from the first two columns
        of the 'osc repos' output. BUILD_DESCR is either a RPM spec file, or a
        Debian dsc file.

        The command honours packagecachedir, build-root and build-uid
        settings in .oscrc, if present. You may want to set su-wrapper = 'sudo'
        in .oscrc, and configure sudo with option NOPASSWD for /usr/bin/build.

        If neither --clean nor --noinit is given, build will reuse an existing
        build-root again, removing unneeded packages and add missing ones. This
        is usually the fastest option.

        If the package doesn't exist on the server please use the --local-package
        option.
        If the project of the package doesn't exist on the server please use the
        --alternative-project <alternative-project> option:
        Example:
            osc build [OPTS] --alternative-project openSUSE:10.3 standard i586 BUILD_DESCR

        usage:
            osc build [OPTS] REPOSITORY ARCH BUILD_DESCR
            osc build [OPTS] REPOSITORY ARCH
            osc build [OPTS] REPOSITORY (ARCH = hostarch, BUILD_DESCR is detected automatically)
            osc build [OPTS] ARCH (REPOSITORY = build_repository (config option), BUILD_DESCR is detected automatically)
            osc build [OPTS] BUILD_DESCR (REPOSITORY = build_repository (config option), ARCH = hostarch)
            osc build [OPTS] (REPOSITORY = build_repository (config option), ARCH = hostarch, BUILD_DESCR is detected automatically)

        # Note:
        # Configuration can be overridden by envvars, e.g.
        # OSC_SU_WRAPPER overrides the setting of su-wrapper.
        # OSC_BUILD_ROOT overrides the setting of build-root.
        # OSC_PACKAGECACHEDIR overrides the setting of packagecachedir.

        ${cmd_option_list}
        """

        import osc.build

        if not os.path.exists('/usr/lib/build/debtransform') \
                and not os.path.exists('/usr/lib/lbuild/debtransform'):
            sys.stderr.write('Error: you need build.rpm with version 2007.3.12 or newer.\n')
            sys.stderr.write('See http://download.opensuse.org/repositories/openSUSE:/Tools/\n')
            return 1

        if opts.debuginfo and opts.disable_debuginfo:
            raise oscerr.WrongOptions('osc: --debuginfo and --disable-debuginfo are mutual exclusive')

        if len(args) > 3:
            raise oscerr.WrongArgs('Too many arguments')

        args = self.parse_repoarchdescr(args, opts.noinit or opts.offline, opts.alternative_project, False, opts.vm_type)

        # check for source services
        r = None
        try:
            if not opts.offline and not opts.noservice:
                p = Package('.')
                r = p.run_source_services(verbose=True)
        except:
            print("WARNING: package is not existing on server yet")
            opts.local_package = True
        
        if opts.offline or opts.local_package or r == None:
            print("WARNING: source service from package or project will not be executed. This may not be the same build as on server!")
        elif (conf.config['local_service_run'] and not opts.noservice) and not opts.noinit:
            if r != 0:
                print('Source service run failed!', file=sys.stderr)
                sys.exit(1)
                # that is currently unreadable on cli, we should not have a backtrace on standard errors:
                #raise oscerr.ServiceRuntimeError('Service run failed: \'%s\'', r)

        if conf.config['no_verify']:
            opts.no_verify = True

        if opts.keep_pkgs and not os.path.isdir(opts.keep_pkgs):
            if os.path.exists(opts.keep_pkgs):
                raise oscerr.WrongOptions('Preferred save location \'%s\' is not a directory' % opts.keep_pkgs)
            else:
                os.makedirs(opts.keep_pkgs)

        if opts.prefer_pkgs:
            for d in opts.prefer_pkgs:
                if not os.path.isdir(d):
                    raise oscerr.WrongOptions('Preferred package location \'%s\' is not a directory' % d)

        if opts.noinit and opts.offline:
            raise oscerr.WrongOptions('--noinit and --offline are mutually exclusive')

        if opts.offline and opts.preload:
            raise oscerr.WrongOptions('--offline and --preload are mutually exclusive')

        print('Building %s for %s/%s' % (args[2], args[0], args[1]))
        if not opts.host:
            return osc.build.main(self.get_api_url(), opts, args)
        else:
            return self._do_rbuild(subcmd, opts, *args)

    def _do_rbuild(self, subcmd, opts, *args):

        # drop the --argument, value tuple from the list
        def drop_arg2(lst, name):
            if not name: 
                return lst
            while name in lst:
                i = lst.index(name)
                lst.pop(i+1)
                lst.pop(i)
            return lst

        # change the local directory to more suitable remote one in hostargs
        # and perform the rsync to such location as well
        def rsync_dirs_2host(hostargs, short_name, long_name, dirs):

            drop_arg2(hostargs, short_name)
            drop_arg2(hostargs, long_name)

            for pdir in dirs:
                # drop the last '/' from pdir name - this is because
                # rsync foo  remote:/bar create /bar/foo on remote machine
                # rsync foo/ remote:/bar copy the content of foo in the /bar
                if pdir[-1:] == os.path.sep:
                    pdir = pdir[:-1]

                hostprefer = os.path.join(
                        hostpath,
                        basename,
                        "%s__" % (long_name.replace('-','_')),
                        os.path.basename(os.path.abspath(pdir)))
                hostargs.append(long_name)
                hostargs.append(hostprefer)

                rsync_prefer_cmd = ['rsync', '-az', '--delete', '-e', 'ssh',
                        pdir,
                        "%s:%s" % (hostname, os.path.dirname(hostprefer))]
                print('Run: %s' % " ".join(rsync_prefer_cmd))
                ret = run_external(rsync_prefer_cmd[0], *rsync_prefer_cmd[1:])
                if ret != 0:
                    return ret

            return 0
            

        cwd = os.getcwd()
        basename = os.path.basename(cwd)
        if not ':' in opts.host:
            hostname = opts.host
            hostpath = "~/"
        else:
            hostname, hostpath = opts.host.split(':', 1)

        # arguments for build: use all arguments behind build and drop --host 'HOST'
        hostargs = sys.argv[sys.argv.index(subcmd)+1:]
        drop_arg2(hostargs, '--host')

        # global arguments: use first '-' up to subcmd
        gi = 0
        for i, a in enumerate(sys.argv):
            if a == subcmd:
                break
            if a[0] == '-':
                gi = i
                break

        if gi:
            hostglobalargs = sys.argv[gi : sys.argv.index(subcmd)+1]
        else:
            hostglobalargs = (subcmd, )

        # keep-pkgs
        hostkeep = None
        if opts.keep_pkgs:
            drop_arg2(hostargs, '-k')
            drop_arg2(hostargs, '--keep-pkgs')
            hostkeep = os.path.join(
                    hostpath,
                    basename,
                    "__keep_pkgs__",
                    "")   # <--- this adds last '/', thus triggers correct rsync behavior
            hostargs.append('--keep-pkgs')
            hostargs.append(hostkeep)

        ### run all commands ###
        # 1.) rsync sources
        rsync_source_cmd = ['rsync', '-az', '--delete', '-e', 'ssh', cwd, "%s:%s" % (hostname, hostpath)]
        print('Run: %s' % " ".join(rsync_source_cmd))
        ret = run_external(rsync_source_cmd[0], *rsync_source_cmd[1:])
        if ret != 0:
            return ret

        # 2.) rsync prefer-pkgs dirs, overlay and rsyns-src
        if opts.prefer_pkgs:
            ret = rsync_dirs_2host(hostargs, '-p', '--prefer-pkgs', opts.prefer_pkgs)
            if ret != 0:
                return ret

        for arg, long_name in ((opts.rsyncsrc, '--rsync-src'), (opts.overlay, '--overlay')):
            if not arg: 
                continue
            ret = rsync_dirs_2host(hostargs, None, long_name, (arg, ))
            if ret != 0:
                return ret

        # 3.) call osc build
        osc_cmd = "osc"
        for var in ('OSC_SU_WRAPPER', 'OSC_BUILD_ROOT', 'OSC_PACKAGECACHEDIR'):
            if os.getenv(var):
                osc_cmd = "%s=%s %s" % (var, os.getenv(var), osc_cmd)

        ssh_cmd = \
            ['ssh', '-t', hostname,
            "cd %(remote_dir)s; %(osc_cmd)s %(global_args)s %(local_args)s" % dict(
            remote_dir = os.path.join(hostpath, basename),
            osc_cmd = osc_cmd,
            global_args = " ".join(hostglobalargs),
            local_args = " ".join(hostargs))
            ]
        print('Run: %s' % " ".join(ssh_cmd))
        build_ret = run_external(ssh_cmd[0], *ssh_cmd[1:])
        if build_ret != 0:
            return build_ret

        # 4.) get keep-pkgs back
        if opts.keep_pkgs:
            ret = rsync_keep_cmd = ['rsync', '-az', '-e', 'ssh', "%s:%s" % (hostname, hostkeep), opts.keep_pkgs]
            print('Run: %s' % " ".join(rsync_keep_cmd))
            ret = run_external(rsync_keep_cmd[0], *rsync_keep_cmd[1:])
            if ret != 0:
                return ret

        return build_ret


    @cmdln.option('--local-package', action='store_true',
                  help='package doesn\'t exist on the server')
    @cmdln.option('--alternative-project', metavar='PROJECT',
                  help='specify the used build target project')
    @cmdln.option('--noinit', '--no-init', action='store_true',
                  help='do not guess/verify specified repository')
    @cmdln.option('-r', '--root', action='store_true',
                  help='login as root instead of abuild')
    @cmdln.option('-o', '--offline', action='store_true',
                  help='Use cached data without contacting the api server')
    def do_chroot(self, subcmd, opts, *args):
        """${cmd_name}: chroot into the buildchroot

        chroot into the buildchroot for the given repository, arch and build description
        (NOTE: this command does not work if "build-type" is set in the config)

        usage:
            osc chroot [OPTS] REPOSITORY ARCH BUILD_DESCR
            osc chroot [OPTS] REPOSITORY (ARCH = hostarch, BUILD_DESCR is detected automatically)
            osc chroot [OPTS] ARCH (REPOSITORY = build_repository (config option), BUILD_DESCR is detected automatically)
            osc chroot [OPTS] BUILD_DESCR (REPOSITORY = build_repository (config option), ARCH = hostarch)
            osc chroot [OPTS] (REPOSITORY = build_repository (config option), ARCH = hostarch, BUILD_DESCR is detected automatically)
        ${cmd_option_list}
        """
        if len(args) > 3:
            raise oscerr.WrongArgs('Too many arguments')
        if conf.config['build-type']:
            print('Not implemented for VMs', file=sys.stderr)
            sys.exit(1)

        user = 'abuild'
        if opts.root:
            user = 'root'
        repository, arch, descr = self.parse_repoarchdescr(args, opts.noinit or opts.offline, opts.alternative_project)
        project = opts.alternative_project or store_read_project('.')
        if opts.local_package:
            package = os.path.splitext(descr)[0]
        else:
            package = store_read_package('.')
        apihost = urlsplit(self.get_api_url())[1]
        buildroot = os.environ.get('OSC_BUILD_ROOT', conf.config['build-root']) \
            % {'repo': repository, 'arch': arch, 'project': project, 'package': package, 'apihost': apihost}
        if not os.path.isdir(buildroot):
            raise oscerr.OscIOError(None, '\'%s\' is not a directory' % buildroot)

        suwrapper = os.environ.get('OSC_SU_WRAPPER', conf.config['su-wrapper'])
        sucmd = suwrapper.split()[0]
        suargs = ' '.join(suwrapper.split()[1:])
        if suwrapper.startswith('su '):
            cmd = [sucmd, '%s chroot "%s" su - %s' % (suargs, buildroot, user)]
        else:
            cmd = [sucmd, 'chroot', buildroot, 'su', '-', user]
            if suargs:
                cmd[1:1] = suargs.split()
        print('running: %s' % ' '.join(cmd))
        os.execvp(sucmd, cmd)


    @cmdln.option('', '--csv', action='store_true',
                        help='generate output in CSV (separated by |)')
    @cmdln.alias('buildhist')
    def do_buildhistory(self, subcmd, opts, *args):
        """${cmd_name}: Shows the build history of a package

        The arguments REPOSITORY and ARCH can be taken from the first two columns
        of the 'osc repos' output.

        usage:
           osc buildhist REPOSITORY ARCHITECTURE
           osc buildhist PROJECT PACKAGE REPOSITORY ARCHITECTURE
        ${cmd_option_list}
        """

        if len(args) < 2 and is_package_dir('.'):
            self.print_repos()

        apiurl = self.get_api_url()

        if len(args) == 4:
            project = args[0]
            package = args[1]
            repository = args[2]
            arch = args[3]
        elif len(args) == 2:
            wd = os.curdir
            package = store_read_package(wd)
            project = store_read_project(wd)
            repository = args[0]
            arch = args[1]
        else:
            raise oscerr.WrongArgs('Wrong number of arguments')

        format = 'text'
        if opts.csv:
            format = 'csv'

        print('\n'.join(get_buildhistory(apiurl, project, package, repository, arch, format)))

    @cmdln.option('', '--csv', action='store_true',
                        help='generate output in CSV (separated by |)')
    @cmdln.option('-l', '--limit', metavar='limit',
                        help='for setting the number of results')
    @cmdln.alias('jobhist')
    def do_jobhistory(self, subcmd, opts, *args):
        """${cmd_name}: Shows the job history of a project

        The arguments REPOSITORY and ARCH can be taken from the first two columns
        of the 'osc repos' output.

        usage:
           osc jobhist REPOSITORY ARCHITECTURE  (in project dir)
           osc jobhist PROJECT [PACKAGE] REPOSITORY ARCHITECTURE
        ${cmd_option_list}
        """
        wd = os.curdir
        args = slash_split(args)

        if len(args) < 2 and (is_project_dir('.') or is_package_dir('.')):
            self.print_repos()

        apiurl = self.get_api_url()

        if len(args) == 4:
            project = args[0]
            package = args[1]
            repository = args[2]
            arch = args[3]
        elif len(args) == 3:
            project = args[0]
            package = None        # skipped = prj
            repository = args[1]
            arch = args[2]
        elif len(args) == 2:
            package = None
            try:
                package = store_read_package(wd)
            except:
                pass
            project = store_read_project(wd)
            repository = args[0]
            arch = args[1]
        else:
            raise oscerr.WrongArgs('Wrong number of arguments')

        format = 'text'
        if opts.csv:
            format = 'csv'

        print_jobhistory(apiurl, project, package, repository, arch, format, opts.limit)

    @cmdln.hide(1)
    def do_rlog(self, subcmd, opts, *args):
        print("Command rlog is obsolete. Please use 'osc log'")
        sys.exit(1)


    @cmdln.option('-r', '--revision', metavar='rev',
                        help='show log of the specified revision')
    @cmdln.option('', '--csv', action='store_true',
                        help='generate output in CSV (separated by |)')
    @cmdln.option('', '--xml', action='store_true',
                        help='generate output in XML')
    @cmdln.option('-D', '--deleted', action='store_true',
                        help='work on deleted package')
    @cmdln.option('-M', '--meta', action='store_true',
                        help='checkout out meta data instead of sources' )
    def do_log(self, subcmd, opts, *args):
        """${cmd_name}: Shows the commit log of a package

        Usage:
            osc log (inside working copy)
            osc log remote_project [remote_package]

        ${cmd_option_list}
        """

        args = slash_split(args)
        apiurl = self.get_api_url()

        if len(args) == 0:
            wd = os.curdir
            if is_project_dir(wd) or is_package_dir(wd):
                project = store_read_project(wd)
                if is_project_dir(wd):
                    package = "_project"
                else:
                    package = store_read_package(wd)
            else:
                raise oscerr.NoWorkingCopy("Error: \"%s\" is not an osc working copy." % os.path.abspath(wd))
        elif len(args) < 1:
            raise oscerr.WrongArgs('Too few arguments (required none or two)')
        elif len(args) > 2:
            raise oscerr.WrongArgs('Too many arguments (required none or two)')
        elif len(args) == 1:
            project = args[0]
            package = "_project"
        else:
            project = args[0]
            package = args[1]

        rev, rev_upper = parseRevisionOption(opts.revision)
        if rev and not checkRevision(project, package, rev, apiurl, opts.meta):
            print('Revision \'%s\' does not exist' % rev, file=sys.stderr)
            sys.exit(1)

        format = 'text'
        if opts.csv:
            format = 'csv'
        if opts.xml:
            format = 'xml'

        log = '\n'.join(get_commitlog(apiurl, project, package, rev, format, opts.meta, opts.deleted, rev_upper))
        run_pager(log)

    def do_service(self, subcmd, opts, *args):
        """${cmd_name}: Handle source services

        Source services can be used to modify sources like downloading files,
        verify files, generating files or modify existing files.

        usage:
            osc service COMMAND (inside working copy)
            osc service run [SOURCE_SERVICE]
            osc service disabledrun
            osc service remoterun [PROJECT PACKAGE]

            COMMAND can be:
            run         r  run defined services locally, it takes an optional parameter to run only a 
                           specified source service. In case parameters exist for this one in _service file
                           they are used.
            disabledrun dr run disabled or server side only services locally and store files as local created
            remoterun   rr trigger a re-run on the server side

        ${cmd_option_list}
        """

        args = slash_split(args)
        project = package = singleservice = mode = None
        apiurl = self.get_api_url()

        if len(args) < 1:
            raise oscerr.WrongArgs('No command given.')
        elif len(args) < 3:
            if is_package_dir(os.curdir):
                project = store_read_project(os.curdir)
                package = store_read_package(os.curdir)
            else:
                raise oscerr.WrongArgs('Too few arguments.')
            if len(args) == 2:
                singleservice = args[1]
        elif len(args) == 3 and args[0] in ('remoterun', 'rr'):
            project = args[1]
            package = args[2]
        else:
            raise oscerr.WrongArgs('Too many arguments.')

        command = args[0]

        if not (command in ( 'run', 'localrun', 'disabledrun', 'remoterun', 'lr', 'dr', 'r', 'rr' )):
            raise oscerr.WrongArgs('Wrong command given.')

        if command == "remoterun" or command == "rr":
            print(runservice(apiurl, project, package))
            return

        if command in ('run', 'localrun', 'disabledrun', 'lr', 'dr', 'r'):
            if not is_package_dir(os.curdir):
                raise oscerr.WrongArgs('Local directory is no package')
            p = Package(".")
            if command == "localrun" or command == "lr":
                mode = "local"
            elif command == "disabledrun" or command == "dr":
                mode = "disabled"

        p.run_source_services(mode, singleservice)

    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='trigger rebuilds for a specific architecture')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='trigger rebuilds for a specific repository')
    @cmdln.option('-f', '--failed', action='store_true',
                  help='rebuild all failed packages')
    @cmdln.option('--all', action='store_true',
                        help='Rebuild all packages of entire project')
    @cmdln.alias('rebuildpac')
    def do_rebuild(self, subcmd, opts, *args):
        """${cmd_name}: Trigger package rebuilds

        Note that it is normally NOT needed to kick off rebuilds like this, because
        they principally happen in a fully automatic way, triggered by source
        check-ins. In particular, the order in which packages are built is handled
        by the build service.

        The arguments REPOSITORY and ARCH can be taken from the first two columns
        of the 'osc repos' output.

        usage:
            osc rebuild [PROJECT [PACKAGE [REPOSITORY [ARCH]]]]
        ${cmd_option_list}
        """

        args = slash_split(args)

        package = repo = arch = code = None
        apiurl = self.get_api_url()

        if opts.repo:
            repo = opts.repo

        if opts.arch:
            arch = opts.arch

        if len(args) < 1:
            if is_package_dir(os.curdir):
                project = store_read_project(os.curdir)
                package = store_read_package(os.curdir)
                apiurl = store_read_apiurl(os.curdir)
            elif is_project_dir(os.curdir):
                project = store_read_project(os.curdir)
                apiurl = store_read_apiurl(os.curdir)
            else:
                raise oscerr.WrongArgs('Too few arguments.')
        else:
            project = args[0]
            if len(args) > 1:
                package = args[1]

        if len(args) > 2:
            repo = args[2]
        if len(args) > 3:
            arch = args[3]

        if opts.failed:
            code = 'failed'

        if not (opts.all or package or repo or arch or code):
            raise oscerr.WrongOptions('No option has been provided. If you want to rebuild all packages of the entire project, use --all option.')

        print(rebuild(apiurl, project, package, repo, arch, code))


    def do_info(self, subcmd, opts, *args):
        """${cmd_name}: Print information about a working copy

        Print information about each ARG (default: '.')
        ARG is a working-copy path.

        ${cmd_usage}
        ${cmd_option_list}
        """

        args = parseargs(args)
        pacs = findpacs(args)

        for p in pacs:
            print(p.info())


    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='Restart builds for a specific architecture')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='Restart builds for a specific repository')
    @cmdln.option('--all', action='store_true',
                        help='Restart all running builds of entire project')
    @cmdln.alias('abortbuild')
    def do_restartbuild(self, subcmd, opts, *args):
        """${cmd_name}: Restart the build of a certain project or package

        usage:
            osc restartbuild [PROJECT [PACKAGE [REPOSITORY [ARCH]]]]
        ${cmd_option_list}
        """
        args = slash_split(args)

        package = repo = arch = code = None
        apiurl = self.get_api_url()

        if opts.repo:
            repo = opts.repo

        if opts.arch:
            arch = opts.arch

        if len(args) < 1:
            if is_package_dir(os.curdir):
                project = store_read_project(os.curdir)
                package = store_read_package(os.curdir)
                apiurl = store_read_apiurl(os.curdir)
            elif is_project_dir(os.curdir):
                project = store_read_project(os.curdir)
                apiurl = store_read_apiurl(os.curdir)
            else:
                raise oscerr.WrongArgs('Too few arguments.')
        else:
            project = args[0]
            if len(args) > 1:
                package = args[1]

        if len(args) > 2:
            repo = args[2]
        if len(args) > 3:
            arch = args[3]

        if not (opts.all or package or repo or arch):
            raise oscerr.WrongOptions('No option has been provided. If you want to restart all packages of the entire project, use --all option.')

        print(cmdbuild(apiurl, subcmd, project, package, opts.arch, opts.repo))


    @cmdln.option('-a', '--arch', metavar='ARCH',
                        help='Delete all binary packages for a specific architecture')
    @cmdln.option('-r', '--repo', metavar='REPO',
                        help='Delete all binary packages for a specific repository')
    @cmdln.option('--build-disabled', action='store_true',
                        help='Delete all binaries of packages for which the build is disabled')
    @cmdln.option('--build-failed', action='store_true',
                        help='Delete all binaries of packages for which the build failed')
    @cmdln.option('--broken', action='store_true',
                        help='Delete all binaries of packages for which the package source is bad')
    @cmdln.option('--unresolvable', action='store_true',
                        help='Delete all binaries of packages which have dependency errors')
    @cmdln.option('--all', action='store_true',
                        help='Delete all binaries regardless of the package status (previously default)')
    def do_wipebinaries(self, subcmd, opts, *args):
        """${cmd_name}: Delete all binary packages of a certain project/package

        With the optional argument <package> you can specify a certain package
        otherwise all binary packages in the project will be deleted.

        usage:
            osc wipebinaries OPTS                       # works in checked out project dir
            osc wipebinaries OPTS PROJECT [PACKAGE]
        ${cmd_option_list}
        """

        args = slash_split(args)

        package = project = None
        apiurl = self.get_api_url()

        # try to get project and package from checked out dirs
        if len(args) < 1:
            if is_project_dir(os.getcwd()):
                project = store_read_project(os.curdir)
            if is_package_dir(os.getcwd()):
                project = store_read_project(os.curdir)
                package = store_read_package(os.curdir)
            if project is  None:
                raise oscerr.WrongArgs('Missing <project> argument.')
        if len(args) > 2:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        # respect given project and package
        if len(args) >= 1:
            project = args[0]

        if len(args) == 2:
            package = args[1]

        codes = []
        if opts.build_disabled:
            codes.append('disabled')
        if opts.build_failed:
            codes.append('failed')
        if opts.broken:
            codes.append('broken')
        if opts.unresolvable:
            codes.append('unresolvable')
        if opts.all or opts.repo or opts.arch:
            codes.append(None)

        if len(codes) == 0:
            raise oscerr.WrongOptions('No option has been provided. If you want to delete all binaries, use --all option.')

        # make a new request for each code= parameter
        for code in codes:
            print(wipebinaries(apiurl, project, package, opts.arch, opts.repo, code))


    @cmdln.option('-q', '--quiet', action='store_true',
                  help='do not show downloading progress')
    @cmdln.option('-d', '--destdir', default='./binaries', metavar='DIR',
                  help='destination directory')
    @cmdln.option('--sources', action="store_true",
                  help='also fetch source packages')
    @cmdln.option('--debug', action="store_true",
                  help='also fetch debug packages')
    def do_getbinaries(self, subcmd, opts, *args):
        """${cmd_name}: Download binaries to a local directory

        This command downloads packages directly from the api server.
        Thus, it directly accesses the packages that are used for building
        others even when they are not "published" yet.

        usage:
           osc getbinaries REPOSITORY                                 # works in checked out project/package (check out all archs in subdirs)
           osc getbinaries REPOSITORY ARCHITECTURE                    # works in checked out project/package
           osc getbinaries PROJECT PACKAGE REPOSITORY ARCHITECTURE
           osc getbinaries PROJECT PACKAGE REPOSITORY ARCHITECTURE FILE
        ${cmd_option_list}
        """

        args = slash_split(args)

        apiurl = self.get_api_url()
        project = None
        package = None
        binary = None

        if len(args) < 1 and is_package_dir('.'):
            self.print_repos()

        architecture = None
        if len(args) == 4 or len(args) == 5:
            project = args[0]
            package = args[1]
            repository   = args[2]
            architecture = args[3]
            if len(args) == 5:
                binary = args[4]
        elif len(args) >= 1 and len(args) <= 2:
            if is_package_dir(os.getcwd()):
                project = store_read_project(os.curdir)
                package = store_read_package(os.curdir)
            elif is_project_dir(os.getcwd()):
                project = store_read_project(os.curdir)
            else:
                raise oscerr.WrongArgs('Missing arguments: either specify <project> and ' \
                                       '<package> or move to a project or package working copy')
            repository   = args[0]
            if len(args) == 2:
                architecture = args[1]
        else:
            raise oscerr.WrongArgs('Need either 1, 2 or 4 arguments')

        repos = list(get_repos_of_project(apiurl, project))
        if not [i for i in repos if repository == i.name]:
            self.print_repos(exc_msg='Invalid repository \'%s\'' % repository)

        arches = [architecture]
        if architecture is None:
            arches = [i.arch for i in repos if repository == i.name]

        if package is None:
            package = meta_get_packagelist(apiurl, project)
        else: 
            package = [package]

        # Set binary target directory and create if not existing
        target_dir = os.path.normpath(opts.destdir)
        if not os.path.isdir(target_dir):
            print('Creating %s' % target_dir)
            os.makedirs(target_dir, 0o755)

        for arch in arches:
            for pac in package:
                binaries = get_binarylist(apiurl, project, repository, arch,
                                          package=pac, verbose=True)
                if not binaries:
                    print('no binaries found: Either the package %s ' \
                                        'does not exist or no binaries have been built.' % pac, file=sys.stderr)
                    continue

                for i in binaries:
                    if binary != None and binary != i.name:
                        continue
                    # skip source rpms
                    if not opts.sources and i.name.endswith('src.rpm'):
                        continue
                    if not opts.debug:
                        if i.name.find('-debuginfo-') >= 0:
                            continue
                        if i.name.find('-debugsource-') >= 0:
                            continue
                    fname = '%s/%s' % (target_dir, i.name)
                    if os.path.exists(fname):
                        st = os.stat(fname)
                        if st.st_mtime == i.mtime and st.st_size == i.size:
                            continue
                    get_binary_file(apiurl,
                                    project,
                                    repository, arch,
                                    i.name,
                                    package = pac,
                                    target_filename = fname,
                                    target_mtime = i.mtime,
                                    progress_meter = not opts.quiet)


    @cmdln.option('-b', '--bugowner', action='store_true',
                        help='restrict listing to items where the user is bugowner')
    @cmdln.option('-m', '--maintainer', action='store_true',
                        help='restrict listing to items where the user is maintainer')
    @cmdln.option('-a', '--all', action='store_true',
                        help='all involvements')
    @cmdln.option('-U', '--user', metavar='USER',
                        help='search for USER instead of yourself')
    @cmdln.option('--exclude-project', action='append',
                        help='exclude requests for specified project')
    @cmdln.option('-v', '--verbose', action='store_true',
                        help='verbose listing')
    @cmdln.option('--maintained', action='store_true',
                        help='limit search results to packages with maintained attribute set.')
    def do_my(self, subcmd, opts, *args):
        """${cmd_name}: show waiting work, packages, projects or requests involving yourself

            Examples:
                # list all open tasks for me
                osc ${cmd_name} [work]
                # list packages where I am bugowner
                osc ${cmd_name} pkg -b
                # list projects where I am maintainer
                osc ${cmd_name} prj -m
                # list request for all my projects and packages
                osc ${cmd_name} rq
                # list requests, excluding project 'foo' and 'bar'
                osc ${cmd_name} rq --exclude-project foo,bar
                # list submitrequests I made
                osc ${cmd_name} sr

            ${cmd_usage}
                where TYPE is one of requests, submitrequests,
                projects or packages (rq, sr, prj or pkg)

            ${cmd_option_list}
        """

        # TODO: please clarify the difference between sr and rq.
        # My first implementeation was to make no difference between requests FROM one 
        # of my projects and TO one of my projects. The current implementation appears to make this difference.
        # The usage above indicates, that sr would be a subset of rq, which is no the case with my tests.
        # jw.

        args_rq = ('requests', 'request', 'req', 'rq', 'work')
        args_sr = ('submitrequests', 'submitrequest', 'submitreq', 'submit', 'sr')
        args_prj = ('projects', 'project', 'projs', 'proj', 'prj')
        args_pkg = ('packages', 'package', 'pack', 'pkgs', 'pkg')
        args_patchinfos = ('patchinfos', 'work')

        if opts.bugowner and opts.maintainer:
            raise oscerr.WrongOptions('Sorry, \'--bugowner\' and \'maintainer\' are mutually exclusive')
        elif opts.all and (opts.bugowner or opts.maintainer):
            raise oscerr.WrongOptions('Sorry, \'--all\' and \'--bugowner\' or \'--maintainer\' are mutually exclusive')

        apiurl = self.get_api_url()

        exclude_projects = []
        for i in opts.exclude_project or []:
            prj = i.split(',')
            if len(prj) == 1:
                exclude_projects.append(i)
            else:
                exclude_projects.extend(prj)
        if not opts.user:
            user = conf.get_apiurl_usr(apiurl)
        else:
            user = opts.user

        what = {'project': '', 'package': ''}
        type = "work"
        if len(args) > 0:
            type = args[0]

        list_patchinfos = list_requests = False
        if type in args_patchinfos:
            list_patchinfos = True
        if type in args_rq:
            list_requests = True
        elif type in args_prj:
            what = {'project': ''}
        elif type in args_sr:
            requests = get_request_list(apiurl, req_who=user, exclude_target_projects=exclude_projects)
            for r in sorted(requests):
                print(r.list_view(), '\n')
            return
        elif not type in args_pkg:
            raise oscerr.WrongArgs("invalid type %s" % type)

        role_filter = ''
        if opts.maintainer:
            role_filter = 'maintainer'
        elif opts.bugowner:
            role_filter = 'bugowner'
        elif list_requests:
            role_filter = 'maintainer'
        if opts.all:
            role_filter = ''

        if list_patchinfos:
            u = makeurl(apiurl, ['/search/package'], {
                'match' : "([kind='patchinfo' and issue/[@state='OPEN' and owner/@login='%s']])" % user
                 })
            f = http_GET(u)
            root = ET.parse(f).getroot()
            if root.findall('package'):
                print("Patchinfos with open bugs assigned to you:\n")
                for node in root.findall('package'):
                    project = node.get('project')
                    package = node.get('name')
                    print(project, "/", package, '\n')
                    p = makeurl(apiurl, ['source', project, package], { 'view': 'issues' })
                    fp = http_GET(p)
                    issues = ET.parse(fp).findall('issue')
                    for issue in issues:
                        if issue.find('state') == None or issue.find('state').text != "OPEN":
                            continue
                        if issue.find('owner') == None or issue.find('owner').find('login').text != user:
                            continue
                        print("  #", issue.find('label').text, ': ', end=' ')
                        desc = issue.find('summary')
                        if desc != None:
                            print(desc.text)
                        else:
                            print("\n")
                print("")

        if list_requests:
            # try api side search as supported since OBS 2.2
            try:
                requests = []
                # open reviews
                u = makeurl(apiurl, ['request'], {
                    'view' : 'collection',
                    'states': 'review',
                    'reviewstates': 'new',
                    'roles': 'reviewer',
                    'user' : user,
                    })
                f = http_GET(u)
                root = ET.parse(f).getroot()
                if root.findall('request'):
                    print("Requests which request a review by you:\n")
                    for node in root.findall('request'):
                        r = Request()
                        r.read(node)
                        print(r.list_view(), '\n')
                    print("")
                # open requests
                u = makeurl(apiurl, ['request'], {
                    'view' : 'collection',
                    'states': 'new',
                    'roles': 'maintainer',
                    'user' : user,
                    })
                f = http_GET(u)
                root = ET.parse(f).getroot()
                if root.findall('request'):
                    print("Requests for your packages:\n")
                    for node in root.findall('request'):
                        r = Request()
                        r.read(node)
                        print(r.list_view(), '\n')
                    print("")
                # declined requests submitted by me
                u = makeurl(apiurl, ['request'], {
                    'view' : 'collection',
                    'states': 'declined',
                    'roles': 'creator',
                    'user' : user,
                    })
                f = http_GET(u)
                root = ET.parse(f).getroot()
                if root.findall('request'):
                    print("Declined requests created by you (revoke, reopen or supersede):\n")
                    for node in root.findall('request'):
                        r = Request()
                        r.read(node)
                        print(r.list_view(), '\n')
                    print("")
                return
            except HTTPError as e:
                if e.code == 400:
                    # skip it ... try again with old style below
                    pass

        res = get_user_projpkgs(apiurl, user, role_filter, exclude_projects,
                                'project' in what, 'package' in what,
                                opts.maintained, opts.verbose)

        # map of project =>[list of packages]
        # if list of packages is empty user is maintainer of the whole project
        request_todo = {}

        roles = {}
        if len(what.keys()) == 2:
            for i in res.get('project_id', res.get('project', {})).findall('project'):
                request_todo[i.get('name')] = []
                roles[i.get('name')] = [p.get('role') for p in i.findall('person') if p.get('userid') == user]
            for i in res.get('package_id', res.get('package', {})).findall('package'):
                prj = i.get('project')
                roles['/'.join([prj, i.get('name')])] = [p.get('role') for p in i.findall('person') if p.get('userid') == user]
                if not prj in request_todo or request_todo[prj] != []:
                    request_todo.setdefault(prj, []).append(i.get('name'))
        else:
            for i in res.get('project_id', res.get('project', {})).findall('project'):
                roles[i.get('name')] = [p.get('role') for p in i.findall('person') if p.get('userid') == user]

        if list_requests:
            # old style, only for OBS 2.1 and before. Should not be used, since it is slow and incomplete
            requests = get_user_projpkgs_request_list(apiurl, user, projpkgs=request_todo)
            for r in sorted(requests):
                print(r.list_view(), '\n')
            if not len(requests):
                print(" -> try also 'osc my sr' to see more.")
        else:
            for i in sorted(roles.keys()):
                out = '%s' % i
                prjpac = i.split('/')
                if type in args_pkg and len(prjpac) == 1 and not opts.verbose:
                    continue
                if opts.verbose:
                    out = '%s (%s)' % (i, ', '.join(sorted(roles[i])))
                    if len(prjpac) == 2:
                        out = '   %s (%s)' % (prjpac[1], ', '.join(sorted(roles[i])))
                print(out)


    @cmdln.option('--repos-baseurl', action='store_true',
                        help='show base URLs of download repositories')
    @cmdln.option('-e', '--exact', action='store_true',
                        help='show only exact matches, this is default now')
    @cmdln.option('-s', '--substring', action='store_true',
                        help='Show also results where the search term is a sub string, slower search')
    @cmdln.option('--package', action='store_true',
                        help='search for a package')
    @cmdln.option('--project', action='store_true',
                        help='search for a project')
    @cmdln.option('--title', action='store_true',
                        help='search for matches in the \'title\' element')
    @cmdln.option('--description', action='store_true',
                        help='search for matches in the \'description\' element')
    @cmdln.option('-a', '--limit-to-attribute', metavar='ATTRIBUTE',
                        help='match only when given attribute exists in meta data')
    @cmdln.option('-v', '--verbose', action='store_true',
                        help='show more information')
    @cmdln.option('-V', '--version', action='store_true', 
                        help='show package version, revision, and srcmd5. CAUTION: This is slow and unreliable')
    @cmdln.option('-i', '--involved', action='store_true',
                        help='show projects/packages where given person (or myself) is involved as bugowner or maintainer')
    @cmdln.option('-b', '--bugowner', action='store_true',
                        help='as -i, but only bugowner')
    @cmdln.option('-m', '--maintainer', action='store_true',
                        help='as -i, but only maintainer')
    @cmdln.option('--maintained', action='store_true',
                        help='OBSOLETE: please use maintained command instead.')
    @cmdln.option('-M', '--mine', action='store_true',
                        help='shorthand for --bugowner --package')
    @cmdln.option('--csv', action='store_true',
                        help='generate output in CSV (separated by |)')
    @cmdln.option('--binary', action='store_true',
                        help='search binary packages')
    @cmdln.option('-B', '--baseproject', metavar='PROJECT',
                        help='search packages built for PROJECT (implies --binary)')
    @cmdln.option('--binaryversion', metavar='VERSION',
                        help='search for binary with specified version (implies --binary)')
    @cmdln.alias('se')
    @cmdln.alias('bse')
    def do_search(self, subcmd, opts, *args):
        """${cmd_name}: Search for a project and/or package.

        If no option is specified osc will search for projects and
        packages which contains the \'search term\' in their name,
        title or description.

        usage:
            osc search \'search term\' <options>
            osc bse ...                         ('osc search --binary')
            osc se 'perl(Foo::Bar)'             ('osc --package perl-Foo-Bar')
        ${cmd_option_list}
        """
        def build_xpath(attr, what, substr = False):
            if substr:
                return 'contains(%s, \'%s\')' % (attr, what)
            else:
                return '%s = \'%s\'' % (attr, what)

        search_term = ''
        if len(args) > 1:
            raise oscerr.WrongArgs('Too many arguments')
        elif len(args) == 0:
            if opts.involved or opts.bugowner or opts.maintainer or opts.mine:
                search_term = conf.get_apiurl_usr(conf.config['apiurl'])
            else:
                raise oscerr.WrongArgs('Too few arguments')
        else:
            search_term = args[0]

        if opts.maintained:
            raise oscerr.WrongOptions('The --maintained option is not anymore supported. Please use the maintained command instead.')

        # XXX: is it a good idea to make this the default?
        # support perl symbols:
        if re.match('^perl\(\w+(::\w+)*\)$', search_term):
            search_term = re.sub('\)', '', re.sub('(::|\()', '-', search_term))
            opts.package = True

        if opts.mine:
            opts.bugowner = True
            opts.package = True

        if (opts.title or opts.description) and (opts.involved or opts.bugowner or opts.maintainer):
            raise oscerr.WrongOptions('Sorry, the options \'--title\' and/or \'--description\' ' \
                                      'are mutually exclusive with \'-i\'/\'-b\'/\'-m\'/\'-M\'')
        if opts.substring and opts.exact:
            raise oscerr.WrongOptions('Sorry, the options \'--substring\' and \'--exact\' are mutually exclusive')

        if not opts.substring:
            opts.exact = True
        if subcmd == 'bse' or opts.baseproject or opts.binaryversion:
            opts.binary = True

        if opts.binary and (opts.title or opts.description or opts.involved or opts.bugowner or opts.maintainer
                            or opts.project or opts.package):
            raise oscerr.WrongOptions('Sorry, \'--binary\' and \'--title\' or \'--description\' or \'--involved ' \
                                      'or \'--bugowner\' or \'--maintainer\' or \'--limit-to-attribute <attr>\ ' \
                                      'or \'--project\' or \'--package\' are mutually exclusive')

        apiurl = self.get_api_url()

        xpath = ''
        if opts.title:
            xpath = xpath_join(xpath, build_xpath('title', search_term, opts.substring), inner=True)
        if opts.description:
            xpath = xpath_join(xpath, build_xpath('description', search_term, opts.substring), inner=True)
        if opts.project or opts.package or opts.binary:
            xpath = xpath_join(xpath, build_xpath('@name', search_term, opts.substring), inner=True)
        # role filter
        role_filter = ''
        if opts.bugowner or opts.maintainer or opts.involved:
            xpath = xpath_join(xpath, 'person/@userid = \'%s\'' % search_term, inner=True)
            role_filter = '%s (%s)' % (search_term, 'person')
        role_filter_xpath = xpath
        if opts.bugowner and not opts.maintainer:
            xpath = xpath_join(xpath, 'person/@role=\'bugowner\'', op='and')
            role_filter = 'bugowner'
        elif not opts.bugowner and opts.maintainer:
            xpath = xpath_join(xpath, 'person/@role=\'maintainer\'', op='and')
            role_filter = 'maintainer'
        if opts.limit_to_attribute:
            xpath = xpath_join(xpath, 'attribute/@name=\'%s\'' % opts.limit_to_attribute, op='and')
        if opts.baseproject:
            xpath = xpath_join(xpath, 'path/@project=\'%s\'' % opts.baseproject, op='and')
        if opts.binaryversion:
            m = re.match(r'(.+)-(.*?)$', opts.binaryversion)
            if m:
                if m.group(2) != '':
                    xpath = xpath_join(xpath, '@versrel=\'%s\'' % opts.binaryversion, op='and')
                else:
                    xpath = xpath_join(xpath, '@version=\'%s\'' % m.group(1), op='and')
            else:
                xpath = xpath_join(xpath, '@version=\'%s\'' % opts.binaryversion, op='and')

        if not xpath:
            xpath = xpath_join(xpath, build_xpath('@name', search_term, opts.substring), inner=True)
            xpath = xpath_join(xpath, build_xpath('title', search_term, opts.substring), inner=True)
            xpath = xpath_join(xpath, build_xpath('description', search_term, opts.substring), inner=True)
        what = {'project': xpath, 'package': xpath}
        if opts.project and not opts.package:
            what = {'project': xpath}
        elif not opts.project and opts.package:
            what = {'package': xpath}
        elif opts.binary:
            what = {'published/binary/id': xpath}
        try:
            res = search(apiurl, **what)
        except HTTPError as e:
            if e.code != 400 or not role_filter:
                raise e
            # backward compatibility: local role filtering
            if opts.limit_to_attribute:
                role_filter_xpath = xpath_join(role_filter_xpath, 'attribute/@name=\'%s\'' % opts.limit_to_attribute, op='and')
            what = dict([[kind, role_filter_xpath] for kind in what.keys()])
            res = search(apiurl, **what)
            filter_role(res, search_term, role_filter)
        if role_filter:
            role_filter = '%s (%s)' % (search_term, role_filter)
        kind_map = {'published/binary/id': 'binary'}
        for kind, root in res.items():
            results = []
            for node in root.findall(kind_map.get(kind, kind)):
                result = []
                project = node.get('project')
                package = None
                if project is None:
                    project = node.get('name')
                else:
                    if kind == 'published/binary/id':
                        package = node.get('package')
                    else:
                        package = node.get('name')

                result.append(project)
                if not package is None:
                    result.append(package)

                if opts.version and package != None:
                    sr = get_source_rev(apiurl, project, package)
                    v = sr.get('version')
                    r = sr.get('rev')
                    s = sr.get('srcmd5')
                    if not v or v == 'unknown':
                        v = '-'
                    if not r:
                        r = '-'
                    if not s:
                        s = '-'
                    result.append(v)
                    result.append(r)
                    result.append(s)

                if opts.verbose:
                    title = node.findtext('title').strip()
                    if len(title) > 60:
                        title = title[:61] + '...'
                    result.append(title)

                if opts.repos_baseurl:
                    # FIXME: no hardcoded URL of instance
                    result.append('http://download.opensuse.org/repositories/%s/' % project.replace(':', ':/'))
                if kind == 'published/binary/id':
                    result.append(node.get('filepath'))
                results.append(result)

            if not len(results):
                print('No matches found for \'%s\' in %ss' % (role_filter or search_term, kind))
                continue
            # construct a sorted, flat list
            # Sort by first column, follwed by second column if we have two columns, else sort by first.
            results.sort(lambda x, y: ( cmp(x[0], y[0]) or 
                                       (len(x)>1 and len(y)>1 and cmp(x[1], y[1])) ))
            new = []
            for i in results:
                new.extend(i)
            results = new
            headline = []
            if kind == 'package' or kind == 'published/binary/id':
                headline = [ '# Project', '# Package' ]
            else:
                headline = [ '# Project' ]
            if opts.version and kind == 'package':
                headline.append('# Ver')
                headline.append('Rev')
                headline.append('Srcmd5')
            if opts.verbose:
                headline.append('# Title')
            if opts.repos_baseurl:
                headline.append('# URL')
            if opts.binary:
                headline.append('# filepath')
            if not opts.csv:
                if len(what.keys()) > 1:
                    print('#' * 68)
                print('matches for \'%s\' in %ss:\n' % (role_filter or search_term, kind))
            for row in build_table(len(headline), results, headline, 2, csv = opts.csv):
                print(row)


    @cmdln.option('-p', '--project', metavar='project',
                        help='specify the path to a project')
    @cmdln.option('-n', '--name', metavar='name',
                        help='specify a package name')
    @cmdln.option('-t', '--title', metavar='title',
                        help='set a title')
    @cmdln.option('-d', '--description', metavar='description',
                        help='set the description of the package')
    @cmdln.option('',   '--delete-old-files', action='store_true',
                        help='delete existing files from the server')
    @cmdln.option('-c',   '--commit', action='store_true',
                        help='commit the new files')
    def do_importsrcpkg(self, subcmd, opts, srpm):
        """${cmd_name}: Import a new package from a src.rpm

        A new package dir will be created inside the project dir
        (if no project is specified and the current working dir is a
        project dir the package will be created in this project). If
        the package does not exist on the server it will be created
        too otherwise the meta data of the existing package will be
        updated (<title /> and <description />).
        The src.rpm will be extracted into the package dir. The files
        won't be committed unless you explicitly pass the --commit switch.

        SRPM is the path of the src.rpm in the local filesystem,
        or an URL.

        ${cmd_usage}
        ${cmd_option_list}
        """
        import glob
        from .util import rpmquery

        if opts.delete_old_files and conf.config['do_package_tracking']:
            # IMHO the --delete-old-files option doesn't really fit into our
            # package tracking strategy
            print('--delete-old-files is not supported anymore', file=sys.stderr)
            print('when do_package_tracking is enabled', file=sys.stderr)
            sys.exit(1)

        if '://' in srpm:
            print('trying to fetch', srpm)
            import urlgrabber
            urlgrabber.urlgrab(srpm)
            srpm = os.path.basename(srpm)

        srpm = os.path.abspath(srpm)
        if not os.path.isfile(srpm):
            print('file \'%s\' does not exist' % srpm, file=sys.stderr)
            sys.exit(1)

        if opts.project:
            project_dir = opts.project
        else:
            project_dir = os.curdir

        if conf.config['do_package_tracking']:
            project = Project(project_dir)
        else:
            project = store_read_project(project_dir)

        rpmq = rpmquery.RpmQuery.query(srpm)
        title, pac, descr, url = rpmq.summary(), rpmq.name(), rpmq.description(), rpmq.url()
        if url is None:
            url = ''

        if opts.title:
            title = opts.title
        if opts.name:
            pac = opts.name
        if opts.description:
            descr = opts.description

        # title and description can be empty
        if not pac:
            print('please specify a package name with the \'--name\' option. ' \
                                'The automatic detection failed', file=sys.stderr)
            sys.exit(1)

        if conf.config['do_package_tracking']:
            createPackageDir(os.path.join(project.dir, pac), project)
        else:
            if not os.path.exists(os.path.join(project_dir, pac)):
                apiurl = store_read_apiurl(project_dir)
                user = conf.get_apiurl_usr(apiurl)
                data = meta_exists(metatype='pkg',
                                   path_args=(quote_plus(project), quote_plus(pac)),
                                   template_args=({
                                       'name': pac,
                                       'user': user}), apiurl=apiurl)
                if data:
                    data = ET.fromstring(''.join(data))
                    data.find('title').text = ''.join(title)
                    data.find('description').text = ''.join(descr)
                    data.find('url').text = url
                    data = ET.tostring(data, encoding=ET_ENCODING)
                else:
                    print('error - cannot get meta data', file=sys.stderr)
                    sys.exit(1)
                edit_meta(metatype='pkg',
                          path_args=(quote_plus(project), quote_plus(pac)),
                          data = data, apiurl=apiurl)
                Package.init_package(apiurl, project, pac, os.path.join(project_dir, pac))
            else:
                print('error - local package already exists', file=sys.stderr)
                sys.exit(1)

        unpack_srcrpm(srpm, os.path.join(project_dir, pac))
        p = Package(os.path.join(project_dir, pac))
        if len(p.filenamelist) == 0 and opts.commit:
            print('Adding files to working copy...')
            addFiles(glob.glob('%s/*' % os.path.join(project_dir, pac)))
            if conf.config['do_package_tracking']:
                project.commit((pac, ))
            else:
                p.update_datastructs()
                p.commit()
        elif opts.commit and opts.delete_old_files:
            for filename in p.filenamelist:
                p.delete_remote_source_file(filename)
            p.update_local_filesmeta()
            print('Adding files to working copy...')
            addFiles(glob.glob('*'))
            p.update_datastructs()
            p.commit()
        else:
            print('No files were committed to the server. Please ' \
                  'commit them manually.')
            print('Package \'%s\' only imported locally' % pac)
            sys.exit(1)

        print('Package \'%s\' imported successfully' % pac)


    @cmdln.option('-X', '-m', '--method', default='GET', metavar='HTTP_METHOD',
                        help='specify HTTP method to use (GET|PUT|DELETE|POST)')
    @cmdln.option('-d', '--data', default=None, metavar='STRING',
                        help='specify string data for e.g. POST')
    @cmdln.option('-T', '-f', '--file', default=None, metavar='FILE',
                        help='specify filename to upload, uses PUT mode by default')
    @cmdln.option('-a', '--add-header', default=None, metavar='NAME STRING',
                        nargs=2, action='append', dest='headers',
                        help='add the specified header to the request')
    def do_api(self, subcmd, opts, url):
        """${cmd_name}: Issue an arbitrary request to the API

        Useful for testing.

        URL can be specified either partially (only the path component), or fully
        with URL scheme and hostname ('http://...').

        Note the global -A and -H options (see osc help).

        Examples:
          osc api /source/home:user
          osc api -X PUT -T /etc/fstab source/home:user/test5/myfstab

        ${cmd_usage}
        ${cmd_option_list}
        """

        apiurl = self.get_api_url()

        if not opts.method in ['GET', 'PUT', 'POST', 'DELETE']:
            sys.exit('unknown method %s' % opts.method)

        # default is PUT when uploading files
        if opts.file and opts.method == 'GET':
            opts.method = 'PUT'

        if not url.startswith('http'):
            if not url.startswith('/'):
                url = '/' + url
            url = apiurl + url

        if opts.headers:
            opts.headers = dict(opts.headers)

        r = http_request(opts.method,
                         url,
                         data=opts.data,
                         file=opts.file,
                         headers=opts.headers)

        out = r.read()
        sys.stdout.write(out)



    @cmdln.option('-b', '--bugowner-only', action='store_true',
                  help='Show only the bugowner')
    @cmdln.option('-B', '--bugowner', action='store_true',
                  help='Show only the bugowner if defined, or maintainer otherwise')
    @cmdln.option('-e', '--email', action='store_true',
                  help='show email addresses instead of user names')
    @cmdln.option('--nodevelproject', action='store_true',
                  help='do not follow a defined devel project ' \
                       '(primary project where a package is developed)')
    @cmdln.option('-v', '--verbose', action='store_true',
                  help='show more information')
    @cmdln.option('-D', '--devel-project', metavar='devel_project',
                  help='define the project where this package is primarily developed')
    @cmdln.option('-a', '--add', metavar='user',
                  help='add a new person for given role ("maintainer" by default)')
    @cmdln.option('-A', '--all', action='store_true',
                  help='list all found entries not just the first one')
    @cmdln.option('-s', '--set-bugowner', metavar='user',
                  help='Set the bugowner to specified person (or group via group: prefix)')
    @cmdln.option('-S', '--set-bugowner-request', metavar='user',
                  help='Set the bugowner to specified person via a request (or group via group: prefix)')
    @cmdln.option('-U', '--user', metavar='USER',
                        help='All official maintained instances for the specified USER')
    @cmdln.option('-G', '--group', metavar='GROUP',
                        help='All official maintained instances for the specified GROUP')
    @cmdln.option('-d', '--delete', metavar='user',
                  help='delete a maintainer/bugowner (can be specified via --role)')
    @cmdln.option('-r', '--role', metavar='role', action='append', default=[],
                  help='Specify user role')
    @cmdln.option('-m', '--message',
                  help='Define message as commit entry or request description')
    @cmdln.alias('bugowner')
    def do_maintainer(self, subcmd, opts, *args):
        """${cmd_name}: Show maintainers according to server side configuration

            # Search for official maintained sources in OBS instance
            osc maintainer BINARY <options>
            osc maintainer -U <user> <options>
            osc maintainer -G <group> <options>

            # Lookup via containers
            osc maintainer <options>
            osc maintainer PRJ <options>
            osc maintainer PRJ PKG <options>
    
        The tool looks up the default responsible person for a certain project or package.
        When using with an OBS 2.4 (or later) server it is doing the lookup for
        a given binary according to the server side configuration of default owners.

        The tool is also looking into devel packages and supports to fallback to the project
        in case a package has no defined maintainer.

        Please use "osc meta pkg" in case you need to know the definition in a specific container.

        PRJ and PKG default to current working-copy path.

        ${cmd_usage}
        ${cmd_option_list}
        """
        def get_maintainer_data(apiurl, maintainer, verbose=False):
            tags = ('email',)
            if maintainer.startswith('group:'):
                group = maintainer.replace('group:', '')
                if verbose:
                    return [maintainer] + get_group_data(apiurl, group, 'title', *tags)
                return get_group_data(apiurl, group, 'email')
            if verbose:
                tags = ('login', 'realname', 'email')
            return get_user_data(apiurl, maintainer, *tags)
        def setBugownerHelper(apiurl, project, package, bugowner):
            try:
                setBugowner(apiurl, project, package, bugowner)
            except HTTPError as e:
                if e.code != 403:
                    raise
                print("No write permission in", project, end=' ')
                if package:
                    print("/", package, end=' ')
                print()
                repl = raw_input('\nCreating a request instead? (y/n) ')
                if repl.lower() == 'y':
                    opts.set_bugowner_request = bugowner
                    opts.set_bugowner = None

        binary = None
        prj = None
        pac = None
        metaroot = None
        searchresult = None
        roles = [ 'bugowner', 'maintainer' ]
        if len(opts.role):
            roles = opts.role
        if opts.bugowner_only or opts.bugowner or subcmd == 'bugowner':
            roles = [ 'bugowner' ]

        args = slash_split(args)
        if opts.user or opts.group:
            if len(args) != 0:
                raise oscerr.WrongArgs('Either search for user or for packages.')
        elif len(args) == 0:
            try:
                pac = store_read_package('.')
            except oscerr.NoWorkingCopy:
                pass
            prj = store_read_project('.')
        elif len(args) == 1:
            # it is unclear if one argument is a binary or a project, try binary first for new OBS 2.4
            binary = prj = args[0]
        elif len(args) == 2:
            prj = args[0]
            pac = args[1]
        else:
            raise oscerr.WrongArgs('Wrong number of arguments.')

        apiurl = self.get_api_url()

        # Try the OBS 2.4 way first. 
        if binary or opts.user or opts.group:
            limit = None
            if opts.all:
                limit = 0
            filterroles = roles
            if filterroles == [ 'bugowner', 'maintainer' ]:
                # use server side configured default
                filterroles = None
            if binary:
                searchresult = owner(apiurl, binary, "binary", usefilter=filterroles, devel=None, limit=limit)
                if not searchresult and (opts.set_bugowner or opts.set_bugowner_request):
                    # filtered search did not succeed, but maybe we want to set an owner initially?
                    searchresult = owner(apiurl, binary, "binary", usefilter="", devel=None, limit=-1)
                    if searchresult:
                        print("WARNING: the binary exists, but has no matching maintainership roles defined.")
                        print("Do you want to set it in the container where the binary appeared first?")
                        result = searchresult.find('owner')
                        print("This is: " + result.get('project'), end=' ')
                        if result.get('package'):
                            print (" / " + result.get('package'))
                        repl = raw_input('\nUse this container? (y/n) ')
                        if repl.lower() != 'y':
                            searchresult = None
            elif opts.user:
                searchresult = owner(apiurl, opts.user, "user", usefilter=filterroles, devel=None)
            elif opts.group:
                searchresult = owner(apiurl, opts.group, "group", usefilter=filterroles, devel=None)
            else:
                raise oscerr.WrongArgs('osc bug, no valid search criteria')

        if opts.add:
            if searchresult:
                for result in searchresult.findall('owner'):
                    for role in roles:
                        addPerson(apiurl, result.get('project'), result.get('package'), opts.add, role)
            else:
                for role in roles:
                    addPerson(apiurl, prj, pac, opts.add, role)
        elif opts.set_bugowner or opts.set_bugowner_request:
            bugowner = opts.set_bugowner or opts.set_bugowner_request
            requestactionsxml = ""
            if searchresult:
                for result in searchresult.findall('owner'):
                    if opts.set_bugowner:
                        setBugownerHelper(apiurl, result.get('project'), result.get('package'), opts.set_bugowner)
                    if opts.set_bugowner_request:
                        args = [bugowner, result.get('project')]
                        if result.get('package'):
                            args = args + [result.get('package')]
                        requestactionsxml += self._set_bugowner(args, opts)

            else:
                if opts.set_bugowner:
                    setBugownerHelper(apiurl, prj, pac, opts.set_bugowner)

                if opts.set_bugowner_request:
                    args = [bugowner, prj]
                    if pac:
                        args = args + [pac]
                    requestactionsxml += self._set_bugowner(args, opts)

            if requestactionsxml != "":
                if opts.message:
                    message = opts.message
                else:
                    message = edit_message()

                import cgi
                xml = """<request> %s <state name="new"/> <description>%s</description> </request> """ % \
                      (requestactionsxml, cgi.escape(message or ""))
                u = makeurl(apiurl, ['request'], query='cmd=create')
                f = http_POST(u, data=xml)

                root = ET.parse(f).getroot()
                print("Request ID:", root.get('id'))

        elif opts.delete:
            if searchresult:
                for result in searchresult.findall('owner'):
                    for role in roles:
                        delPerson(apiurl, result.get('project'), result.get('package'), opts.delete, role)
            else:
                for role in roles:
                    delPerson(apiurl, prj, pac, opts.delete, role)
        elif opts.devel_project:
            # XXX: does it really belong to this command?
            setDevelProject(apiurl, prj, pac, opts.devel_project)
        else:
            if pac:
                m = show_package_meta(apiurl, prj, pac)
                metaroot = ET.fromstring(''.join(m))
                if not opts.nodevelproject:
                    while metaroot.findall('devel'):
                        d = metaroot.find('devel')
                        prj = d.get('project', prj)
                        pac = d.get('package', pac)
                        if opts.verbose:
                            print("Following to the development space: %s/%s" % (prj, pac))
                        m = show_package_meta(apiurl, prj, pac)
                        metaroot = ET.fromstring(''.join(m))
                    if not metaroot.findall('person') and not metaroot.findall('group'):
                        if opts.verbose:
                            print("No dedicated persons in package defined, showing the project persons.")
                        pac = None
                        m = show_project_meta(apiurl, prj)
                        metaroot = ET.fromstring(''.join(m))
            else:
                # fallback to project lookup for old servers
                if prj and not searchresult:
                    m = show_project_meta(apiurl, prj)
                    metaroot = ET.fromstring(''.join(m))

            # extract the maintainers
            projects = []
            # from owner search
            if searchresult:
                for result in searchresult.findall('owner'):
                    maintainers = {}
                    maintainers.setdefault("project", result.get('project'))
                    maintainers.setdefault("package", result.get('package'))
                    for person in result.findall('person'):
                        maintainers.setdefault(person.get('role'), []).append(person.get('name'))
                    for group in result.findall('group'):
                        maintainers.setdefault(group.get('role'), []).append("group:"+group.get('name'))
                    projects = projects + [maintainers]
            # from meta data
            if metaroot:
                # we have just one result
                maintainers = {}
                for person in metaroot.findall('person'):
                    maintainers.setdefault(person.get('role'), []).append(person.get('userid'))
                for group in metaroot.findall('group'):
                    maintainers.setdefault(group.get('role'), []).append("group:"+group.get('groupid'))
                projects = [maintainers]

            # showing the maintainers
            for maintainers in projects:
                indent = ""
                definingproject = maintainers.get("project")
                if definingproject:
                    definingpackage = maintainers.get("package")
                    indent = "  "
                    if definingpackage:
                        print("Defined in package: %s/%s " % (definingproject, definingpackage))
                    else:
                        print("Defined in project: ", definingproject)

                if prj: 
                    # not for user/group search
                    for role in roles:
                        if opts.bugowner and not len(maintainers.get(role, [])):
                            role = 'maintainer'
                        if pac:
                            print("%s%s of %s/%s : " %(indent, role, prj, pac))
                        else:
                            print("%s%s of %s : " %(indent, role, prj))
                        if opts.email:
                            emails = []
                            for maintainer in maintainers.get(role, []):
                                user = get_maintainer_data(apiurl, maintainer, verbose=False)
                                if len(user):
                                    emails.append(''.join(user))
                            print(indent, end=' ')
                            print(', '.join(emails) or '-')
                        elif opts.verbose:
                            userdata = []
                            for maintainer in maintainers.get(role, []):
                                user = get_maintainer_data(apiurl, maintainer, verbose=True)
                                userdata.append(user[0])
                                if user[1] !=  '-':
                                    userdata.append("%s <%s>"%(user[1], user[2]))
                                else:
                                    userdata.append(user[2])
                            for row in build_table(2, userdata, None, 3):
                                print(indent, end=' ')
                                print(row)
                        else:
                            print(indent, end=' ')
                            print(', '.join(maintainers.get(role, [])) or '-')
                        print()

    @cmdln.alias('who')
    @cmdln.alias('user')
    def do_whois(self, subcmd, opts, *usernames):
        """${cmd_name}: Show fullname and email of a buildservice user

        ${cmd_usage}
        ${cmd_option_list}
        """
        apiurl = self.get_api_url()
        if len(usernames) < 1:
            if 'user' not in conf.config['api_host_options'][apiurl]:
                raise oscerr.WrongArgs('your .oscrc does not have your user name.')
            usernames = (conf.config['api_host_options'][apiurl]['user'],)
        for name in usernames:
            user = get_user_data(apiurl, name, 'login', 'realname', 'email')
            if len(user) == 3:
                print("%s: \"%s\" <%s>"%(user[0], user[1], user[2]))


    @cmdln.option('-r', '--revision', metavar='rev',
                  help='print out the specified revision')
    @cmdln.option('-e', '--expand', action='store_true',
                  help='force expansion of linked packages.')
    @cmdln.option('-u', '--unexpand', action='store_true',
                  help='always work with unexpanded packages.')
    @cmdln.option('-M', '--meta', action='store_true',
                        help='list meta data files')
    @cmdln.alias('less')
    def do_cat(self, subcmd, opts, *args):
        """${cmd_name}: Output the content of a file to standard output

        Examples:
            osc cat project package file
            osc cat project/package/file
            osc cat http://api.opensuse.org/build/.../_log
            osc cat http://api.opensuse.org/source/../_link

        ${cmd_usage}
        ${cmd_option_list}
        """

        if len(args) == 1 and (args[0].startswith('http://') or
                               args[0].startswith('https://')):
            opts.method = 'GET'
            opts.headers = None
            opts.data = None
            opts.file = None
            return self.do_api('list', opts, *args)



        args = slash_split(args)
        if len(args) != 3:
            raise oscerr.WrongArgs('Wrong number of arguments.')
        rev, dummy = parseRevisionOption(opts.revision)
        apiurl = self.get_api_url()

        query = { }
        if opts.meta:
            query['meta'] = 1
        if opts.revision:
            query['rev'] = opts.revision
        if opts.expand:
            query['rev'] = show_upstream_srcmd5(apiurl, args[0], args[1], expand=True, revision=opts.revision, meta=opts.meta)
        u = makeurl(apiurl, ['source', args[0], args[1], args[2]], query=query)
        try:
            if subcmd == 'less':
                f = http_GET(u)
                run_pager(''.join(f.readlines()))
            else:
                for data in streamfile(u):
                    sys.stdout.write(data)
        except HTTPError as e:
            if e.code == 404 and not opts.expand and not opts.unexpand:
                print('expanding link...', file=sys.stderr)
                query['rev'] = show_upstream_srcmd5(apiurl, args[0], args[1], expand=True, revision=opts.revision)
                u = makeurl(apiurl, ['source', args[0], args[1], args[2]], query=query)
                if subcmd == "less":
                    f = http_GET(u)
                    run_pager(''.join(f.readlines()))
                else:
                    for data in streamfile(u):
                        sys.stdout.write(data)
            else:
                e.osc_msg = 'If linked, try: cat -e'
                raise e


    # helper function to download a file from a specific revision
    def download(self, name, md5, dir, destfile):
        o = open(destfile, 'wb')
        if md5 != '':
            query = {'rev': dir['srcmd5']}
            u = makeurl(dir['apiurl'], ['source', dir['project'], dir['package'], pathname2url(name)], query=query)
            for buf in streamfile(u, http_GET, BUFSIZE):
                o.write(buf)
        o.close()


    @cmdln.option('-d', '--destdir', default='repairlink', metavar='DIR',
            help='destination directory')
    def do_repairlink(self, subcmd, opts, *args):
        """${cmd_name}: Repair a broken source link

        This command checks out a package with merged source changes. It uses
        a 3-way merge to resolve file conflicts. After reviewing/repairing
        the merge, use 'osc resolved ...' and 'osc ci' to re-create a
        working source link.

        usage:
        * For merging conflicting changes of a checkout package:
            osc repairlink

        * Check out a package and merge changes:
            osc repairlink PROJECT PACKAGE

        * Pull conflicting changes from one project into another one:
            osc repairlink PROJECT PACKAGE INTO_PROJECT [INTO_PACKAGE]

        ${cmd_option_list}
        """

        apiurl = self.get_api_url()
        args = slash_split(args)
        if len(args) >= 3 and len(args) <= 4:
            prj = args[0]
            package = target_package = args[1]
            target_prj = args[2]
            if len(args) == 4:
                target_package = args[3]
        elif len(args) == 2:
            target_prj = prj = args[0]
            target_package = package = args[1]
        elif is_package_dir(os.getcwd()):
            target_prj = prj = store_read_project(os.getcwd())
            target_package = package = store_read_package(os.getcwd())
        else:
            raise oscerr.WrongArgs('Please specify project and package')

        # first try stored reference, then lastworking
        query = { 'rev': 'latest' }
        u = makeurl(apiurl, ['source', prj, package], query=query)
        f = http_GET(u)
        root = ET.parse(f).getroot()
        linkinfo = root.find('linkinfo')
        if linkinfo == None:
            raise oscerr.APIError('package is not a source link')
        if linkinfo.get('error') == None:
            raise oscerr.APIError('source link is not broken')
        workingrev = None

        baserev = linkinfo.get('baserev')
        if baserev != None:
            query = { 'rev': 'latest', 'linkrev': baserev }
            u = makeurl(apiurl, ['source', prj, package], query=query)
            f = http_GET(u)
            root = ET.parse(f).getroot()
            linkinfo = root.find('linkinfo')
            if linkinfo.get('error') == None:
                workingrev = linkinfo.get('xsrcmd5')

        if workingrev == None:
            query = { 'lastworking': 1 }
            u = makeurl(apiurl, ['source', prj, package], query=query)
            f = http_GET(u)
            root = ET.parse(f).getroot()
            linkinfo = root.find('linkinfo')
            if linkinfo == None:
                raise oscerr.APIError('package is not a source link')
            if linkinfo.get('error') == None:
                raise oscerr.APIError('source link is not broken')
            workingrev = linkinfo.get('lastworking')
            if workingrev == None:
                raise oscerr.APIError('source link never worked')
            print("using last working link target")
        else:
            print("using link target of last commit")

        query = { 'expand': 1, 'emptylink': 1 }
        u = makeurl(apiurl, ['source', prj, package], query=query)
        f = http_GET(u)
        meta = f.readlines()
        root_new = ET.fromstring(''.join(meta))
        dir_new = { 'apiurl': apiurl, 'project': prj, 'package': package }
        dir_new['srcmd5'] = root_new.get('srcmd5')
        dir_new['entries'] = [[n.get('name'), n.get('md5')] for n in root_new.findall('entry')]

        query = { 'rev': workingrev }
        u = makeurl(apiurl, ['source', prj, package], query=query)
        f = http_GET(u)
        root_oldpatched = ET.parse(f).getroot()
        linkinfo_oldpatched = root_oldpatched.find('linkinfo')
        if linkinfo_oldpatched == None:
            raise oscerr.APIError('working rev is not a source link?')
        if linkinfo_oldpatched.get('error') != None:
            raise oscerr.APIError('working rev is not working?')
        dir_oldpatched = { 'apiurl': apiurl, 'project': prj, 'package': package }
        dir_oldpatched['srcmd5'] = root_oldpatched.get('srcmd5')
        dir_oldpatched['entries'] = [[n.get('name'), n.get('md5')] for n in root_oldpatched.findall('entry')]

        query = {}
        query['rev'] = linkinfo_oldpatched.get('srcmd5')
        u = makeurl(apiurl, ['source', linkinfo_oldpatched.get('project'), linkinfo_oldpatched.get('package')], query=query)
        f = http_GET(u)
        root_old = ET.parse(f).getroot()
        dir_old = { 'apiurl': apiurl }
        dir_old['project'] = linkinfo_oldpatched.get('project')
        dir_old['package'] = linkinfo_oldpatched.get('package')
        dir_old['srcmd5'] = root_old.get('srcmd5')
        dir_old['entries'] = [[n.get('name'), n.get('md5')] for n in root_old.findall('entry')]

        entries_old = dict(dir_old['entries'])
        entries_oldpatched = dict(dir_oldpatched['entries'])
        entries_new = dict(dir_new['entries'])

        entries = {}
        entries.update(entries_old)
        entries.update(entries_oldpatched)
        entries.update(entries_new)

        destdir = opts.destdir
        if os.path.isdir(destdir):
            shutil.rmtree(destdir)
        os.mkdir(destdir)

        Package.init_package(apiurl, target_prj, target_package, destdir)
        store_write_string(destdir, '_files', ''.join(meta) + '\n')
        store_write_string(destdir, '_linkrepair', '')
        pac = Package(destdir)

        storedir = os.path.join(destdir, store)

        for name in sorted(entries.keys()):
            md5_old = entries_old.get(name, '')
            md5_new = entries_new.get(name, '')
            md5_oldpatched = entries_oldpatched.get(name, '')
            if md5_new != '':
                self.download(name, md5_new, dir_new, os.path.join(storedir, name))
            if md5_old == md5_new:
                if md5_oldpatched == '':
                    pac.put_on_deletelist(name)
                    continue
                print(statfrmt(' ', name))
                self.download(name, md5_oldpatched, dir_oldpatched, os.path.join(destdir, name))
                continue
            if md5_old == md5_oldpatched:
                if md5_new == '':
                    continue
                print(statfrmt('U', name))
                shutil.copy2(os.path.join(storedir, name), os.path.join(destdir, name))
                continue
            if md5_new == md5_oldpatched:
                if md5_new == '':
                    continue
                print(statfrmt('G', name))
                shutil.copy2(os.path.join(storedir, name), os.path.join(destdir, name))
                continue
            self.download(name, md5_oldpatched, dir_oldpatched, os.path.join(destdir, name + '.mine'))
            if md5_new != '':
                shutil.copy2(os.path.join(storedir, name), os.path.join(destdir, name + '.new'))
            else:
                self.download(name, md5_new, dir_new, os.path.join(destdir, name + '.new'))
            self.download(name, md5_old, dir_old, os.path.join(destdir, name + '.old'))

            if binary_file(os.path.join(destdir, name + '.mine')) or \
               binary_file(os.path.join(destdir, name + '.old')) or \
               binary_file(os.path.join(destdir, name + '.new')):
                shutil.copy2(os.path.join(destdir, name + '.new'), os.path.join(destdir, name))
                print(statfrmt('C', name))
                pac.put_on_conflictlist(name)
                continue

            o = open(os.path.join(destdir,  name), 'wb')
            code = run_external('diff3', '-m', '-E',
              '-L', '.mine',
              os.path.join(destdir, name + '.mine'),
              '-L', '.old',
              os.path.join(destdir, name + '.old'),
              '-L', '.new',
              os.path.join(destdir, name + '.new'),
            stdout=o)
            if code == 0:
                print(statfrmt('G', name))
                os.unlink(os.path.join(destdir, name + '.mine'))
                os.unlink(os.path.join(destdir, name + '.old'))
                os.unlink(os.path.join(destdir, name + '.new'))
            elif code == 1:
                print(statfrmt('C', name))
                pac.put_on_conflictlist(name)
            else:
                print(statfrmt('?', name))
                pac.put_on_conflictlist(name)

        pac.write_deletelist()
        pac.write_conflictlist()
        print()
        print('Please change into the \'%s\' directory,' % destdir)
        print('fix the conflicts (files marked with \'C\' above),')
        print('run \'osc resolved ...\', and commit the changes.')


    def do_pull(self, subcmd, opts, *args):
        """${cmd_name}: merge the changes of the link target into your working copy.

        ${cmd_option_list}
        """

        if not is_package_dir('.'):
            raise oscerr.NoWorkingCopy('Error: \'%s\' is not an osc working copy.' % os.path.abspath('.'))
        p = Package('.')
        # check if everything is committed
        for filename in p.filenamelist:
            state = p.status(filename)
            if state != ' ' and state != 'S':
                raise oscerr.WrongArgs('Please commit your local changes first!')
        # check if we need to update
        upstream_rev = p.latest_rev()
        if not (p.isfrozen() or p.ispulled()):
            raise oscerr.WrongArgs('osc pull makes only sense with a detached head, did you mean osc up?')
        if p.rev != upstream_rev:
            raise oscerr.WorkingCopyOutdated((p.absdir, p.rev, upstream_rev))
        elif not p.islink():
            raise oscerr.WrongArgs('osc pull only works on linked packages.')
        elif not p.isexpanded():
            raise oscerr.WrongArgs('osc pull only works on expanded links.')
        linkinfo = p.linkinfo
        baserev = linkinfo.baserev
        if baserev == None:
            raise oscerr.WrongArgs('osc pull only works on links containing a base revision.')

        # get revisions we need
        query = { 'expand': 1, 'emptylink': 1 }
        u = makeurl(p.apiurl, ['source', p.prjname, p.name], query=query)
        f = http_GET(u)
        meta = f.readlines()
        root_new = ET.fromstring(''.join(meta))
        linkinfo_new = root_new.find('linkinfo')
        if linkinfo_new == None:
            raise oscerr.APIError('link is not a really a link?')
        if linkinfo_new.get('error') != None:
            raise oscerr.APIError('link target is broken')
        if linkinfo_new.get('srcmd5') == baserev:
            print("Already up-to-date.")
            p.unmark_frozen()
            return
        dir_new = { 'apiurl': p.apiurl, 'project': p.prjname, 'package': p.name }
        dir_new['srcmd5'] = root_new.get('srcmd5')
        dir_new['entries'] = [[n.get('name'), n.get('md5')] for n in root_new.findall('entry')]

        dir_oldpatched = { 'apiurl': p.apiurl, 'project': p.prjname, 'package': p.name, 'srcmd5': p.srcmd5 }
        dir_oldpatched['entries'] = [[f.name, f.md5] for f in p.filelist]

        query = { 'rev': linkinfo.srcmd5 }
        u = makeurl(p.apiurl, ['source', linkinfo.project, linkinfo.package], query=query)
        f = http_GET(u)
        root_old = ET.parse(f).getroot()
        dir_old = { 'apiurl': p.apiurl, 'project': linkinfo.project, 'package': linkinfo.package, 'srcmd5': linkinfo.srcmd5 }
        dir_old['entries'] = [[n.get('name'), n.get('md5')] for n in root_old.findall('entry')]

        # now do 3-way merge
        entries_old = dict(dir_old['entries'])
        entries_oldpatched = dict(dir_oldpatched['entries'])
        entries_new = dict(dir_new['entries'])
        entries = {}
        entries.update(entries_old)
        entries.update(entries_oldpatched)
        entries.update(entries_new)
        for name in sorted(entries.keys()):
            if name.startswith('_service:') or name.startswith('_service_'):
                continue
            md5_old = entries_old.get(name, '')
            md5_new = entries_new.get(name, '')
            md5_oldpatched = entries_oldpatched.get(name, '')
            if md5_old == md5_new or md5_oldpatched == md5_new:
                continue
            if md5_old == md5_oldpatched:
                if md5_new == '':
                    print(statfrmt('D', name))
                    p.put_on_deletelist(name)
                    os.unlink(name)
                elif md5_old == '':
                    print(statfrmt('A', name))
                    self.download(name, md5_new, dir_new, name)
                    p.put_on_addlist(name)
                else:
                    print(statfrmt('U', name))
                    self.download(name, md5_new, dir_new, name)
                continue
            # need diff3 to resolve issue
            if md5_oldpatched == '':
                open(name, 'w').write('')
            os.rename(name, name + '.mine')
            self.download(name, md5_new, dir_new, name + '.new')
            self.download(name, md5_old, dir_old, name + '.old')
            if binary_file(name + '.mine') or binary_file(name + '.old') or binary_file(name + '.new'):
                shutil.copy2(name + '.new', name)
                print(statfrmt('C', name))
                p.put_on_conflictlist(name)
                continue

            o = open(name, 'wb')
            code = run_external('diff3', '-m', '-E',
              '-L', '.mine', name + '.mine',
              '-L', '.old', name + '.old',
              '-L', '.new', name + '.new',
            stdout=o)
            if code == 0:
                print(statfrmt('G', name))
                os.unlink(name + '.mine')
                os.unlink(name + '.old')
                os.unlink(name + '.new')
            elif code == 1:
                print(statfrmt('C', name))
                p.put_on_conflictlist(name)
            else:
                print(statfrmt('?', name))
                p.put_on_conflictlist(name)
        p.write_deletelist()
        p.write_addlist()
        p.write_conflictlist()
        # store new linkrev
        store_write_string(p.absdir, '_pulled', linkinfo_new.get('srcmd5') + '\n')
        p.unmark_frozen()
        print()
        if len(p.in_conflict):
            print('Please fix the conflicts (files marked with \'C\' above),')
            print('run \'osc resolved ...\', and commit the changes')
            print('to update the link information.')
        else:
            print('Please commit the changes to update the link information.')

    @cmdln.option('--create', action='store_true', default=False,
                  help='create new gpg signing key for this project')
    @cmdln.option('--extend', action='store_true', default=False,
                  help='extend expiration date of the gpg public key for this project')
    @cmdln.option('--delete', action='store_true', default=False,
                  help='delete the gpg signing key in this project')
    @cmdln.option('--notraverse', action='store_true', default=False,
                  help='don\' traverse projects upwards to find key')
    @cmdln.option('--sslcert', action='store_true', default=False,
                  help='fetch SSL certificate instead of GPG key')
    def do_signkey(self, subcmd, opts, *args):
        """${cmd_name}: Manage Project Signing Key

        osc signkey [--create|--delete|--extend] <PROJECT>
        osc signkey [--notraverse] <PROJECT>

        This command is for managing gpg keys. It shows the public key
        by default. There is no way to download or upload the private
        part of a key by design.

        However you can create a new own key. You may want to consider
        to sign the public key with your own existing key.

        If a project has no key, the key from upper level project will
        be used (eg. when dropping "KDE:KDE4:Community" key, the one from
        "KDE:KDE4" will be used).

        WARNING: THE OLD KEY WILL NOT BE RESTORABLE WHEN USING DELETE OR CREATE

        ${cmd_usage}
        ${cmd_option_list}
        """

        apiurl = self.get_api_url()
        f = None

        prj = None
        if len(args) == 0:
            cwd = os.getcwd()
            if is_project_dir(cwd) or is_package_dir(cwd):
                prj = store_read_project(cwd)
        if len(args) == 1:
            prj = args[0]

        if not prj:
            raise oscerr.WrongArgs('Please specify just the project')

        if opts.create:
            url = makeurl(apiurl, ['source', prj], query='cmd=createkey')
            f = http_POST(url)
        elif opts.extend:
            url = makeurl(apiurl, ['source', prj], query='cmd=extendkey')
            f = http_POST(url)
        elif opts.delete:
            url = makeurl(apiurl, ['source', prj, "_pubkey"])
            f = http_DELETE(url)
        else:
            while True:
                try:
                    url = makeurl(apiurl, ['source', prj, '_pubkey'])
                    if opts.sslcert:
                        url = makeurl(apiurl, ['source', prj, '_project', '_sslcert'], 'meta=1')
                    f = http_GET(url)
                    break
                except HTTPError as e:
                    l = prj.rsplit(':', 1)
                    # try key from parent project
                    if not opts.notraverse and len(l) > 1 and l[0] and l[1] and e.code == 404:
                        print('%s has no key, trying %s' % (prj, l[0]))
                        prj = l[0]
                    else:
                        raise

        while True:
            buf = f.read(16384)
            if not buf:
                break
            sys.stdout.write(buf)

    @cmdln.option('-m', '--message',
                  help='add MESSAGE to changes (do not open an editor)')
    @cmdln.option('-F', '--file', metavar='FILE',
                  help='read changes message from FILE (do not open an editor)')
    @cmdln.option('-e', '--just-edit', action='store_true', default=False,
                  help='just open changes (cannot be used with -m)')
    def do_vc(self, subcmd, opts, *args):
        """${cmd_name}: Edit the changes file

        osc vc [-m MESSAGE|-e] [filename[.changes]|path [file_with_comment]]
        If no <filename> is given, exactly one *.changes or *.spec file has to
        be in the cwd or in path.

        The email address used in .changes file is read from BuildService
        instance, or should be defined in ~/.oscrc
        [https://api.opensuse.org/]
        user = login
        pass = password
        email = user@defined.email

        or can be specified via mailaddr environment variable.

        ${cmd_usage}
        ${cmd_option_list}
        """

        from subprocess import Popen
        if opts.message and opts.file:
            raise oscerr.WrongOptions('\'--message\' and \'--file\' are mutually exclusive')
        elif opts.message and opts.just_edit:
            raise oscerr.WrongOptions('\'--message\' and \'--just-edit\' are mutually exclusive')
        elif opts.file and opts.just_edit:
            raise oscerr.WrongOptions('\'--file\' and \'--just-edit\' are mutually exclusive')
        meego_style = False
        if not args:
            import glob, re
            try:
                fn_changelog = glob.glob('*.changes')[0]
                fp = file(fn_changelog)
                titleline = fp.readline()
                fp.close()
                if re.match('^\*\W+(.+\W+\d{1,2}\W+20\d{2})\W+(.+)\W+<(.+)>\W+(.+)$', titleline):
                    meego_style = True
            except IndexError:
                pass

        if meego_style:
            if not os.path.exists('/usr/bin/vc'):
                print('Error: you need meego-packaging-tools for /usr/bin/vc command', file=sys.stderr)
                return 1
            cmd_list = ['/usr/bin/vc']
        else:
            if not os.path.exists('/usr/lib/build/vc'):
                print('Error: you need build.rpm with version 2009.04.17 or newer', file=sys.stderr)
                print('See http://download.opensuse.org/repositories/openSUSE:/Tools/', file=sys.stderr)
                return 1

            cmd_list = ['/usr/lib/build/vc']

        # set user's email if no mailaddr exists
        if 'mailaddr' not in os.environ:

            if len(args) and is_package_dir(args[0]):
                apiurl = store_read_apiurl(args[0])
            else:
                apiurl = self.get_api_url()

            user = conf.get_apiurl_usr(apiurl)

            data = get_user_data(apiurl, user, 'email')
            if data:
                os.environ['mailaddr'] = data[0]
            else:
                print('Try env mailaddr=...', file=sys.stderr)

            # mailaddr can be overrided by config one
            if 'email' in conf.config['api_host_options'][apiurl]:
                os.environ['mailaddr'] = conf.config['api_host_options'][apiurl]['email']

        if meego_style:
            if opts.message or opts.just_edit:
                print('Warning: to edit MeeGo style changelog, opts will be ignored.', file=sys.stderr)
        else:
            if opts.message:
                cmd_list.append("-m")
                cmd_list.append(opts.message)
            if opts.file:
                if not os.path.isfile(opts.file):
                    raise oscerr.WrongOptions('\'%s\': is no file' % opts.file)
                cmd_list.append("-m")
                cmd_list.append(open(opts.file).read().strip())

            if opts.just_edit:
                cmd_list.append("-e")

            cmd_list.extend(args)

        vc = Popen(cmd_list)
        vc.wait()
        sys.exit(vc.returncode)

    @cmdln.option('-f', '--force', action='store_true',
                        help='forces removal of entire package and its files')
    def do_mv(self, subcmd, opts, source, dest):
        """${cmd_name}: Move SOURCE file to DEST and keep it under version control

        ${cmd_usage}
        ${cmd_option_list}
        """

        if not os.path.isfile(source):
            raise oscerr.WrongArgs("Source file '%s' does not exists or is no file" % source)
        if not opts.force and os.path.isfile(dest):
            raise oscerr.WrongArgs("Dest file '%s' already exists" % dest)
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(source))
        src_pkg = findpacs([source])
        tgt_pkg = findpacs([dest])
        if not src_pkg:
            raise oscerr.NoWorkingCopy("Error: \"%s\" is not located in an osc working copy." % os.path.abspath(source))
        if not tgt_pkg:
            raise oscerr.NoWorkingCopy("Error: \"%s\" does not point to an osc working copy." % os.path.abspath(dest))

        os.rename(source, dest)
        try:
            tgt_pkg[0].addfile(os.path.basename(dest))
        except oscerr.PackageFileConflict:
            # file is already tracked
            pass
        src_pkg[0].delete_file(os.path.basename(source), force=opts.force)

    @cmdln.option('-d', '--delete', action='store_true',
                        help='delete option from config or reset option to the default)')
    @cmdln.option('-s', '--stdin', action='store_true',
                        help='indicates that the config value should be read from stdin')
    @cmdln.option('-p', '--prompt', action='store_true',
                        help='prompt for a value')
    @cmdln.option('--no-echo', action='store_true',
                        help='prompt for a value but do not echo entered characters')
    @cmdln.option('--dump', action='store_true',
                        help='dump the complete configuration (without \'pass\' and \'passx\' options)')
    @cmdln.option('--dump-full', action='store_true',
                        help='dump the complete configuration (including \'pass\' and \'passx\' options)')
    def do_config(self, subcmd, opts, *args):
        """${cmd_name}: get/set a config option

        Examples:
            osc config section option (get current value)
            osc config section option value (set to value)
            osc config section option --delete (delete option/reset to the default)
            (section is either an apiurl or an alias or 'general')
            osc config --dump (dump the complete configuration)

        ${cmd_usage}
        ${cmd_option_list}
        """
        if len(args) < 2 and not (opts.dump or opts.dump_full):
            raise oscerr.WrongArgs('Too few arguments')
        elif opts.dump or opts.dump_full:
            cp = conf.get_configParser(conf.config['conffile'])
            for sect in cp.sections():
                print('[%s]' % sect)
                for opt in sorted(cp.options(sect)):
                    if sect == 'general' and opt in conf.api_host_options or \
                        sect != 'general' and not opt in conf.api_host_options:
                        continue
                    if opt in ('pass', 'passx') and not opts.dump_full:
                        continue
                    val = str(cp.get(sect, opt, raw=True))
                    # special handling for continuation lines
                    val = '\n '.join(val.split('\n'))
                    print('%s = %s' % (opt, val))
                print()
            return

        section, opt, val = args[0], args[1], args[2:]
        if len(val) and (opts.delete or opts.stdin or opts.prompt or opts.no_echo):
            raise oscerr.WrongOptions('Sorry, \'--delete\' or \'--stdin\' or \'--prompt\' or \'--no-echo\' ' \
                'and the specification of a value argument are mutually exclusive')
        elif (opts.prompt or opts.no_echo) and opts.stdin:
            raise oscerr.WrongOptions('Sorry, \'--prompt\' or \'--no-echo\' and  \'--stdin\' are mutually exclusive')
        elif opts.stdin:
            # strip lines
            val = [i.strip() for i in sys.stdin.readlines() if i.strip()]
            if not len(val):
                raise oscerr.WrongArgs('error: read empty value from stdin')
        elif opts.no_echo or opts.prompt:
            if opts.no_echo:
                import getpass
                inp = getpass.getpass('Value: ').strip()
            else:
                inp = raw_input('Value: ').strip()
            if not inp:
                raise oscerr.WrongArgs('error: no value was entered')
            val = [inp]
        opt, newval = conf.config_set_option(section, opt, ' '.join(val), delete=opts.delete, update=True)
        if newval is None and opts.delete:
            print('\'%s\': \'%s\' got removed' % (section, opt))
        elif newval is None:
            print('\'%s\': \'%s\' is not set' % (section, opt))
        else:
            if opts.no_echo:
                # supress value
                print('\'%s\': set \'%s\'' % (section, opt))
            elif opt == 'pass' and not conf.config['plaintext_passwd'] and newval == 'your_password':
                opt, newval = conf.config_set_option(section, 'passx')
                print('\'%s\': \'pass\' was rewritten to \'passx\': \'%s\'' % (section, newval))
            else:
                print('\'%s\': \'%s\' is set to \'%s\'' % (section, opt, newval))

    def do_revert(self, subcmd, opts, *files):
        """${cmd_name}: Restore changed files or the entire working copy.

        Examples:
            osc revert <modified file(s)>
            ose revert .
        Note: this only works for package working copies

        ${cmd_usage}
        ${cmd_option_list}
        """
        pacs = findpacs(files)
        for p in pacs:
            if not len(p.todo):
                p.todo = p.filenamelist + p.to_be_added
            for f in p.todo:
                p.revert(f)

    @cmdln.option('--force-apiurl', action='store_true',
                  help='ask once for an apiurl and force this apiurl for all inconsistent projects/packages')
    def do_repairwc(self, subcmd, opts, *args):
        """${cmd_name}: try to repair an inconsistent working copy

        Examples:
            osc repairwc <path>

        Note: if <path> is omitted it defaults to '.' (<path> can be
              a project or package working copy)

        Warning: This command might delete some files in the storedir
        (.osc). Please check the state of the wc afterwards (via 'osc status').

        ${cmd_usage}
        ${cmd_option_list}
        """
        def get_apiurl(apiurls):
            print('No apiurl is defined for this working copy.\n' \
                'Please choose one from the following list (enter the number):')
            for i in range(len(apiurls)):
                print(' %d) %s' % (i, apiurls[i]))
            num = raw_input('> ')
            try:
                num = int(num)
            except ValueError:
                raise oscerr.WrongArgs('\'%s\' is not a number. Aborting' % num)
            if num < 0 or num >= len(apiurls):
                raise oscerr.WrongArgs('number \'%s\' out of range. Aborting' % num)
            return apiurls[num]

        args = parseargs(args)
        pacs = []
        apiurls = list(conf.config['api_host_options'].keys())
        apiurl = ''
        for i in args:
            if is_project_dir(i):
                try:
                    prj = Project(i, getPackageList=False)
                except oscerr.WorkingCopyInconsistent as e:
                    if '_apiurl' in e.dirty_files and (not apiurl or not opts.force_apiurl):
                        apiurl = get_apiurl(apiurls)
                    prj = Project(i, getPackageList=False, wc_check=False)
                    prj.wc_repair(apiurl)
                for p in prj.pacs_have:
                    if p in prj.pacs_broken:
                        continue
                    try:
                        Package(os.path.join(i, p))
                    except oscerr.WorkingCopyInconsistent:
                        pacs.append(os.path.join(i, p))
            elif is_package_dir(i):
                pacs.append(i)
            else:
                print('\'%s\' is neither a project working copy ' \
                    'nor a package working copy' % i, file=sys.stderr)
        for pdir in pacs:
            try:
                p = Package(pdir)
            except oscerr.WorkingCopyInconsistent as e:
                if '_apiurl' in e.dirty_files and (not apiurl or not opts.force_apiurl):
                    apiurl = get_apiurl(apiurls)
                p = Package(pdir, wc_check=False)
                p.wc_repair(apiurl)
                print('done. Please check the state of the wc (via \'osc status %s\').' % i)
            else:
                print('osc: working copy \'%s\' is not inconsistent' % i, file=sys.stderr)

    @cmdln.option('-n', '--dry-run', action='store_true',
                  help='print the results without actually removing a file')
    def do_clean(self, subcmd, opts, *args):
        """${cmd_name}: removes all untracked files from the package working copy

        Examples:
            osc clean <path>

        Note: if <path> is omitted it defaults to '.' (<path> has to
              be a package working copy)

        Warning: This command removes all files with status '?'.

        ${cmd_usage}
        ${cmd_option_list}
        """
        pacs = parseargs(args)
        # do a sanity check first
        for pac in pacs:
            if not is_package_dir(pac):
                raise oscerr.WrongArgs('\'%s\' is no package working copy' % pac)
        for pdir in pacs:
            p = Package(pdir)
            pdir = getTransActPath(pdir)
            for filename in (fname for st, fname in p.get_status() if st == '?'):
                print('Removing: %s' % os.path.join(pdir, filename))
                if not opts.dry_run:
                    os.unlink(os.path.join(p.absdir, filename))

    def _load_plugins(self):
        plugin_dirs = [
            '/usr/lib/osc-plugins',
            '/usr/local/lib/osc-plugins',
            '/var/lib/osc-plugins',  # Kept for backward compatibility
            os.path.expanduser('~/.osc-plugins')]
        for plugin_dir in plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue
            for extfile in os.listdir(plugin_dir):
                if not extfile.endswith('.py'):
                    continue
                try:
                    modname = os.path.splitext(extfile)[0]
                    mod = imp.load_source(modname, os.path.join(plugin_dir, extfile))
                    # restore the old exec semantic
                    mod.__dict__.update(globals())
                    for name in dir(mod):
                        data = getattr(mod, name)
                        # Add all functions (which are defined in the imported module)
                        # to the class (filtering only methods which start with "do_"
                        # breaks the old behavior).
                        # Also add imported modules (needed for backward compatibility).
                        # New plugins should not use "self.<imported modname>.<something>"
                        # to refer to the imported module. Instead use
                        # "<imported modname>.<something>".
                        if (inspect.isfunction(data) and inspect.getmodule(data) == mod
                            or inspect.ismodule(data)):
                            setattr(self.__class__, name, data)
                except (SyntaxError, NameError, ImportError) as e:
                    if (os.environ.get('OSC_PLUGIN_FAIL_IGNORE')):
                        print("%s: %s\n" % (os.path.join(plugin_dir, extfile), e), file=sys.stderr)
                    else:
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        print('\n%s: %s' % (os.path.join(plugin_dir, extfile), e), file=sys.stderr)
                        print("\n Try 'env OSC_PLUGIN_FAIL_IGNORE=1 osc ...'", file=sys.stderr)
                        sys.exit(1)

# fini!
###############################################################################

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = conf
# Copyright (C) 2006-2009 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or version 3 (at your option).

from __future__ import print_function

"""Read osc configuration and store it in a dictionary

This module reads and parses ~/.oscrc. The resulting configuration is stored
for later usage in a dictionary named 'config'.
The .oscrc is kept mode 0600, so that it is not publically readable.
This gives no real security for storing passwords.
If in doubt, use your favourite keyring.
Password is stored on ~/.oscrc as bz2 compressed and base64 encoded, so that is fairly
large and not to be recognized or remembered easily by an occasional spectator.

If information is missing, it asks the user questions.

After reading the config, urllib2 is initialized.

The configuration dictionary could look like this:

{'apisrv': 'https://api.opensuse.org/',
 'user': 'joe',
 'api_host_options': {'api.opensuse.org': {'user': 'joe', 'pass': 'secret'},
                      'apitest.opensuse.org': {'user': 'joe', 'pass': 'secret',
                                               'http_headers':(('Host','api.suse.de'),
                                                               ('User','faye'))},
                      'foo.opensuse.org': {'user': 'foo', 'pass': 'foo'}},
 'build-cmd': '/usr/bin/build',
 'build-root': '/abuild/oscbuild-%(repo)s-%(arch)s',
 'packagecachedir': '/var/cache/osbuild',
 'su-wrapper': 'sudo',
 }

"""

import bz2
import base64
import os
import re
import sys

try:
    from http.cookiejar import LWPCookieJar, CookieJar
    from http.client import HTTPConnection, HTTPResponse
    from io import StringIO
    from urllib.parse import urlsplit
    from urllib.error import URLError
    from urllib.request import HTTPBasicAuthHandler, HTTPCookieProcessor, HTTPPasswordMgrWithDefaultRealm, ProxyHandler
    from urllib.request import AbstractHTTPHandler, build_opener, proxy_bypass
except ImportError:
    #python 2.x
    from cookielib import LWPCookieJar, CookieJar
    from httplib import HTTPConnection, HTTPResponse
    from StringIO import StringIO
    from urlparse import urlsplit
    from urllib2 import URLError, HTTPBasicAuthHandler, HTTPCookieProcessor, HTTPPasswordMgrWithDefaultRealm, ProxyHandler
    from urllib2 import AbstractHTTPHandler, build_opener, proxy_bypass

from . import OscConfigParser
from osc import oscerr
from .oscsslexcp import NoSecureSSLError

GENERIC_KEYRING = False
GNOME_KEYRING = False

try:
    import keyring
    GENERIC_KEYRING = True
except:
    try:
        import gobject
        gobject.set_application_name('osc')
        import gnomekeyring
        if os.environ['GNOME_DESKTOP_SESSION_ID']:
            # otherwise gnome keyring bindings spit out errors, when you have
            # it installed, but you are not under gnome
            # (even though hundreds of gnome-keyring daemons got started in parallel)
            # another option would be to support kwallet here
            GNOME_KEYRING = gnomekeyring.is_available()
    except:
        pass


def _get_processors():
    """
    get number of processors (online) based on
    SC_NPROCESSORS_ONLN (returns 1 if config name does not exist).
    """
    try:
        return os.sysconf('SC_NPROCESSORS_ONLN')
    except ValueError as e:
        return 1

DEFAULTS = {'apiurl': 'https://api.opensuse.org',
            'user': 'your_username',
            'pass': 'your_password',
            'passx': '',
            'packagecachedir': '/var/tmp/osbuild-packagecache',
            'su-wrapper': 'sudo',

            # build type settings
            'build-cmd': '/usr/bin/build',
            'build-type': '',                   # may be empty for chroot, kvm or xen
            'build-root': '/var/tmp/build-root/%(repo)s-%(arch)s',
            'build-uid': '',                    # use the default provided by build
            'build-device': '',                 # required for VM builds
            'build-memory': '',                 # required for VM builds
            'build-swap': '',                   # optional for VM builds
            'build-vmdisk-rootsize': '',        # optional for VM builds
            'build-vmdisk-swapsize': '',        # optional for VM builds
            'build-vmdisk-filesystem': '',        # optional for VM builds

            'build-jobs': _get_processors(),
            'builtin_signature_check': '1',     # by default use builtin check for verify pkgs
            'icecream': '0',

            'buildlog_strip_time': '0',  # strips the build time from the build log

            'debug': '0',
            'http_debug': '0',
            'http_full_debug': '0',
            'http_retries': '3',
            'verbose': '1',
            'traceback': '0',
            'post_mortem': '0',
            'use_keyring': '0',
            'gnome_keyring': '0',
            'cookiejar': '~/.osc_cookiejar',
            # fallback for osc build option --no-verify
            'no_verify': '0',
            # enable project tracking by default
            'do_package_tracking': '1',
            # default for osc build
            'extra-pkgs': '',
            # default repository
            'build_repository': 'openSUSE_Factory',
            # default project for branch or bco
            'getpac_default_project': 'openSUSE:Factory',
            # alternate filesystem layout: have multiple subdirs, where colons were.
            'checkout_no_colon': '0',
            # change filesystem layout: avoid checkout from within a proj or package dir.
            'checkout_rooted': '0',
            # local files to ignore with status, addremove, ....
            'exclude_glob': '.osc CVS .svn .* _linkerror *~ #*# *.orig *.bak *.changes.vctmp.*',
            # whether to keep passwords in plaintext.
            'plaintext_passwd': '1',
            # limit the age of requests shown with 'osc req list'.
            # this is a default only, can be overridden by 'osc req list -D NNN'
            # Use 0 for unlimted.
            'request_list_days': 0,
            # check for unversioned/removed files before commit
            'check_filelist': '1',
            # check for pending requests after executing an action (e.g. checkout, update, commit)
            'check_for_request_on_action': '0',
            # what to do with the source package if the submitrequest has been accepted
            'submitrequest_on_accept_action': '',
            'request_show_interactive': '0',
            # if a review is accepted in interactive mode and a group
            # was specified the review will be accepted for this group
            'review_inherit_group': '0',
            'submitrequest_accepted_template': '',
            'submitrequest_declined_template': '',
            'linkcontrol': '0',
            'include_request_from_project': '1',
            'local_service_run': '1',

            # Maintenance defaults to OBS instance defaults
            'maintained_attribute': 'OBS:Maintained',
            'maintenance_attribute': 'OBS:MaintenanceProject',
            'maintained_update_project_attribute': 'OBS:UpdateProject',
            'show_download_progress': '0',
}

# being global to this module, this dict can be accessed from outside
# it will hold the parsed configuration
config = DEFAULTS.copy()

boolean_opts = ['debug', 'do_package_tracking', 'http_debug', 'post_mortem', 'traceback', 'check_filelist', 'plaintext_passwd',
    'checkout_no_colon', 'checkout_rooted', 'check_for_request_on_action', 'linkcontrol', 'show_download_progress', 'request_show_interactive',
    'review_inherit_group', 'use_keyring', 'gnome_keyring', 'no_verify', 'builtin_signature_check', 'http_full_debug',
    'include_request_from_project', 'local_service_run', 'buildlog_strip_time']

api_host_options = ['user', 'pass', 'passx', 'aliases', 'http_headers', 'email', 'sslcertck', 'cafile', 'capath', 'trusted_prj']

new_conf_template = """
[general]

# URL to access API server, e.g. %(apiurl)s
# you also need a section [%(apiurl)s] with the credentials
apiurl = %(apiurl)s

# Downloaded packages are cached here. Must be writable by you.
#packagecachedir = %(packagecachedir)s

# Wrapper to call build as root (sudo, su -, ...)
#su-wrapper = %(su-wrapper)s

# rootdir to setup the chroot environment
# can contain %%(repo)s, %%(arch)s, %%(project)s, %%(package)s and %%(apihost)s (apihost is the hostname
# extracted from currently used apiurl) for replacement, e.g.
# /srv/oscbuild/%%(repo)s-%%(arch)s or
# /srv/oscbuild/%%(repo)s-%%(arch)s-%%(project)s-%%(package)s
#build-root = %(build-root)s

# compile with N jobs (default: "getconf _NPROCESSORS_ONLN")
#build-jobs = N

# build-type to use - values can be (depending on the capabilities of the 'build' script)
# empty    -  chroot build
# kvm      -  kvm VM build  (needs build-device, build-swap, build-memory)
# xen      -  xen VM build  (needs build-device, build-swap, build-memory)
#   experimental:
#     qemu -  qemu VM build
#     lxc  -  lxc build
#build-type =

# build-device is the disk-image file to use as root for VM builds
# e.g. /var/tmp/FILE.root
#build-device = /var/tmp/FILE.root

# build-swap is the disk-image to use as swap for VM builds
# e.g. /var/tmp/FILE.swap
#build-swap = /var/tmp/FILE.swap

# build-memory is the amount of memory used in the VM
# value in MB - e.g. 512
#build-memory = 512

# build-vmdisk-rootsize is the size of the disk-image used as root in a VM build
# values in MB - e.g. 4096
#build-vmdisk-rootsize = 4096

# build-vmdisk-swapsize is the size of the disk-image used as swap in a VM build
# values in MB - e.g. 1024
#build-vmdisk-swapsize = 1024

# build-vmdisk-filesystem is the file system type of the disk-image used in a VM build
# values are ext3(default) ext4 xfs reiserfs btrfs
#build-vmdisk-filesystem = ext4

# Numeric uid:gid to assign to the "abuild" user in the build-root
# or "caller" to use the current users uid:gid
# This is convenient when sharing the buildroot with ordinary userids
# on the host.
# This should not be 0
# build-uid =

# strip leading build time information from the build log
# buildlog_strip_time = 1

# extra packages to install when building packages locally (osc build)
# this corresponds to osc build's -x option and can be overridden with that
# -x '' can also be given on the command line to override this setting, or
# you can have an empty setting here.
#extra-pkgs = vim gdb strace

# build platform is used if the platform argument is omitted to osc build
#build_repository = %(build_repository)s

# default project for getpac or bco
#getpac_default_project = %(getpac_default_project)s

# alternate filesystem layout: have multiple subdirs, where colons were.
#checkout_no_colon = %(checkout_no_colon)s

# change filesystem layout: avoid checkout within a project or package dir.
#checkout_rooted = %(checkout_rooted)s

# local files to ignore with status, addremove, ....
#exclude_glob = %(exclude_glob)s

# keep passwords in plaintext.
# Set to 0 to obfuscate passwords. It's no real security, just
# prevents most people from remembering your password if they watch
# you editing this file.
#plaintext_passwd = %(plaintext_passwd)s

# limit the age of requests shown with 'osc req list'.
# this is a default only, can be overridden by 'osc req list -D NNN'
# Use 0 for unlimted.
#request_list_days = %(request_list_days)s

# show info useful for debugging
#debug = 1

# show HTTP traffic useful for debugging
#http_debug = 1

# number of retries on HTTP transfer
#http_retries = 3

# Skip signature verification of packages used for build.
#no_verify = 1

# jump into the debugger in case of errors
#post_mortem = 1

# print call traces in case of errors
#traceback = 1

# use KDE/Gnome/MacOS/Windows keyring for credentials if available
#use_keyring = 1

# check for unversioned/removed files before commit
#check_filelist = 1

# check for pending requests after executing an action (e.g. checkout, update, commit)
#check_for_request_on_action = 0

# what to do with the source package if the submitrequest has been accepted. If
# nothing is specified the API default is used
#submitrequest_on_accept_action = cleanup|update|noupdate

# template for an accepted submitrequest
#submitrequest_accepted_template = Hi %%(who)s,\\n
# thanks for working on:\\t%%(tgt_project)s/%%(tgt_package)s.
# SR %%(reqid)s has been accepted.\\n\\nYour maintainers

# template for a declined submitrequest
#submitrequest_declined_template = Hi %%(who)s,\\n
# sorry your SR %%(reqid)s (request type: %%(type)s) for
# %%(tgt_project)s/%%(tgt_package)s has been declined because...

#review requests interactively (default: off)
#request_show_review = 1

# if a review is accepted in interactive mode and a group
# was specified the review will be accepted for this group (default: off)
#review_inherit_group = 1

[%(apiurl)s]
user = %(user)s
pass = %(pass)s
# set aliases for this apiurl
# aliases = foo, bar
# email used in .changes, unless the one from osc meta prj <user> will be used
# email =
# additional headers to pass to a request, e.g. for special authentication
#http_headers = Host: foofoobar,
#       User: mumblegack
# Plain text password
#pass =
# Force using of keyring for this API
#keyring = 1
"""


account_not_configured_text = """
Your user account / password are not configured yet.
You will be asked for them below, and they will be stored in
%s for future use.
"""

config_incomplete_text = """

Your configuration file %s is not complete.
Make sure that it has a [general] section.
(You can copy&paste the below. Some commented defaults are shown.)

"""

config_missing_apiurl_text = """
the apiurl \'%s\' does not exist in the config file. Please enter
your credentials for this apiurl.
"""

cookiejar = None


def parse_apisrv_url(scheme, apisrv):
    if apisrv.startswith('http://') or apisrv.startswith('https://'):
        return urlsplit(apisrv)[0:2]
    elif scheme != None:
        # the split/join is needed to get a proper url (e.g. without a trailing slash)
        return urlsplit(urljoin(scheme, apisrv))[0:2]
    else:
        msg = 'invalid apiurl \'%s\' (specify the protocol (http:// or https://))' % apisrv
        raise URLError(msg)


def urljoin(scheme, apisrv):
    return '://'.join([scheme, apisrv])


def is_known_apiurl(url):
    """returns true if url is a known apiurl"""
    apiurl = urljoin(*parse_apisrv_url(None, url))
    return apiurl in config['api_host_options']


def get_apiurl_api_host_options(apiurl):
    """
    Returns all apihost specific options for the given apiurl, None if
    no such specific optiosn exist.
    """
    # FIXME: in A Better World (tm) there was a config object which
    # knows this instead of having to extract it from a url where it
    # had been mingled into before.  But this works fine for now.

    apiurl = urljoin(*parse_apisrv_url(None, apiurl))
    if is_known_apiurl(apiurl):
        return config['api_host_options'][apiurl]
    raise oscerr.ConfigMissingApiurl('missing credentials for apiurl: \'%s\'' % apiurl,
                                     '', apiurl)


def get_apiurl_usr(apiurl):
    """
    returns the user for this host - if this host does not exist in the
    internal api_host_options the default user is returned.
    """
    # FIXME: maybe there should be defaults not just for the user but
    # for all apihost specific options.  The ConfigParser class
    # actually even does this but for some reason we don't use it
    # (yet?).

    try:
        return get_apiurl_api_host_options(apiurl)['user']
    except KeyError:
        print('no specific section found in config file for host of [\'%s\'] - using default user: \'%s\'' \
            % (apiurl, config['user']), file=sys.stderr)
        return config['user']


# workaround m2crypto issue:
# if multiple SSL.Context objects are created
# m2crypto only uses the last object which was created.
# So we need to build a new opener everytime we switch the
# apiurl (because different apiurls may have different
# cafile/capath locations)
def _build_opener(url):
    from osc.core import __version__
    global config
    apiurl = urljoin(*parse_apisrv_url(None, url))
    if 'last_opener' not in _build_opener.__dict__:
        _build_opener.last_opener = (None, None)
    if apiurl == _build_opener.last_opener[0]:
        return _build_opener.last_opener[1]

    # respect no_proxy env variable
    if proxy_bypass(apiurl):
        # initialize with empty dict
        proxyhandler = ProxyHandler({})
    else:
        # read proxies from env
        proxyhandler = ProxyHandler()

    # workaround for http://bugs.python.org/issue9639
    authhandler_class = HTTPBasicAuthHandler
    if sys.version_info >= (2, 6, 6) and sys.version_info < (2, 7, 1) \
        and not 'reset_retry_count' in dir(HTTPBasicAuthHandler):
        print('warning: your urllib2 version seems to be broken. ' \
            'Using a workaround for http://bugs.python.org/issue9639', file=sys.stderr)

        class OscHTTPBasicAuthHandler(HTTPBasicAuthHandler):
            def http_error_401(self, *args):
                response = HTTPBasicAuthHandler.http_error_401(self, *args)
                self.retried = 0
                return response

            def http_error_404(self, *args):
                self.retried = 0
                return None

        authhandler_class = OscHTTPBasicAuthHandler
    elif sys.version_info >= (2, 6, 6) and sys.version_info < (2, 7, 99):
        class OscHTTPBasicAuthHandler(HTTPBasicAuthHandler):
            def http_error_404(self, *args):
                self.reset_retry_count()
                return None

        authhandler_class = OscHTTPBasicAuthHandler
    elif sys.version_info >= (2, 6, 5) and sys.version_info < (2, 6, 6):
        # workaround for broken urllib2 in python 2.6.5: wrong credentials
        # lead to an infinite recursion
        class OscHTTPBasicAuthHandler(HTTPBasicAuthHandler):
            def retry_http_basic_auth(self, host, req, realm):
                # don't retry if auth failed
                if req.get_header(self.auth_header, None) is not None:
                    return None
                return HTTPBasicAuthHandler.retry_http_basic_auth(self, host, req, realm)

        authhandler_class = OscHTTPBasicAuthHandler

    options = config['api_host_options'][apiurl]
    # with None as first argument, it will always use this username/password
    # combination for urls for which arg2 (apisrv) is a super-url
    authhandler = authhandler_class( \
        HTTPPasswordMgrWithDefaultRealm())
    authhandler.add_password(None, apiurl, options['user'], options['pass'])

    if options['sslcertck']:
        try:
            from . import oscssl
            from M2Crypto import m2urllib2
        except ImportError as e:
            print(e)
            raise NoSecureSSLError('M2Crypto is needed to access %s in a secure way.\nPlease install python-m2crypto.' % apiurl)

        cafile = options.get('cafile', None)
        capath = options.get('capath', None)
        if not cafile and not capath:
            for i in ['/etc/pki/tls/cert.pem', '/etc/ssl/certs']:
                if os.path.isfile(i):
                    cafile = i
                    break
                elif os.path.isdir(i):
                    capath = i
                    break
        if not cafile and not capath:
            raise Exception('No CA certificates found')
        ctx = oscssl.mySSLContext()
        if ctx.load_verify_locations(capath=capath, cafile=cafile) != 1:
            raise Exception('No CA certificates found')
        opener = m2urllib2.build_opener(ctx, oscssl.myHTTPSHandler(ssl_context=ctx, appname='osc'), HTTPCookieProcessor(cookiejar), authhandler, proxyhandler)
    else:
        print("WARNING: SSL certificate checks disabled. Connection is insecure!\n", file=sys.stderr)
        opener = build_opener(HTTPCookieProcessor(cookiejar), authhandler, proxyhandler)
    opener.addheaders = [('User-agent', 'osc/%s' % __version__)]
    _build_opener.last_opener = (apiurl, opener)
    return opener


def init_basicauth(config):
    """initialize urllib2 with the credentials for Basic Authentication"""

    def filterhdrs(meth, ishdr, *hdrs):
        # this is so ugly but httplib doesn't use
        # a logger object or such
        def new_method(self, *args, **kwargs):
            # check if this is a recursive call (note: we do not
            # have to care about thread safety)
            is_rec_call = getattr(self, '_orig_stdout', None) is not None
            try:
                if not is_rec_call:
                    self._orig_stdout = sys.stdout
                    sys.stdout = StringIO()
                meth(self, *args, **kwargs)
                hdr = sys.stdout.getvalue()
            finally:
                # restore original stdout
                if not is_rec_call:
                    sys.stdout = self._orig_stdout
                    del self._orig_stdout
            for i in hdrs:
                if ishdr:
                    hdr = re.sub(r'%s:[^\\r]*\\r\\n' % i, '', hdr)
                else:
                    hdr = re.sub(i, '', hdr)
            sys.stdout.write(hdr)
        new_method.__name__ = meth.__name__
        return new_method

    if config['http_debug'] and not config['http_full_debug']:
        HTTPConnection.send = filterhdrs(HTTPConnection.send, True, 'Cookie', 'Authorization')
        HTTPResponse.begin = filterhdrs(HTTPResponse.begin, False, 'header: Set-Cookie.*\n')

    if sys.version_info < (2, 6):
        # HTTPS proxy is not supported in old urllib2. It only leads to an error
        # or, at best, a warning.
        if 'https_proxy' in os.environ:
            del os.environ['https_proxy']
        if 'HTTPS_PROXY' in os.environ:
            del os.environ['HTTPS_PROXY']

    if config['http_debug']:
        # brute force
        def urllib2_debug_init(self, debuglevel=0):
            self._debuglevel = 1
        AbstractHTTPHandler.__init__ = urllib2_debug_init

    cookie_file = os.path.expanduser(config['cookiejar'])
    global cookiejar
    cookiejar = LWPCookieJar(cookie_file)
    try:
        cookiejar.load(ignore_discard=True)
    except IOError:
        try:
            fd = os.open(cookie_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            os.close(fd)
        except IOError:
            # hmm is any good reason why we should catch the IOError?
            #print 'Unable to create cookiejar file: \'%s\'. Using RAM-based cookies.' % cookie_file
            cookiejar = CookieJar()


def get_configParser(conffile=None, force_read=False):
    """
    Returns an ConfigParser() object. After its first invocation the
    ConfigParser object is stored in a method attribute and this attribute
    is returned unless you pass force_read=True.
    """
    conffile = conffile or os.environ.get('OSC_CONFIG', '~/.oscrc')
    conffile = os.path.expanduser(conffile)
    if 'conffile' not in get_configParser.__dict__:
        get_configParser.conffile = conffile
    if force_read or 'cp' not in get_configParser.__dict__ or conffile != get_configParser.conffile:
        get_configParser.cp = OscConfigParser.OscConfigParser(DEFAULTS)
        get_configParser.cp.read(conffile)
        get_configParser.conffile = conffile
    return get_configParser.cp


def write_config(fname, cp):
    """write new configfile in a safe way"""
    if os.path.exists(fname) and not os.path.isfile(fname):
        # only write to a regular file
        return
    with open(fname + '.new', 'w') as f:
        cp.write(f, comments=True)
    try:
        os.rename(fname + '.new', fname)
        os.chmod(fname, 0o600)
    except:
        if os.path.exists(fname + '.new'):
            os.unlink(fname + '.new')
        raise


def config_set_option(section, opt, val=None, delete=False, update=True, **kwargs):
    """
    Sets a config option. If val is not specified the current/default value is
    returned. If val is specified, opt is set to val and the new value is returned.
    If an option was modified get_config is called with **kwargs unless update is set
    to False (override_conffile defaults to config['conffile']).
    If val is not specified and delete is True then the option is removed from the
    config/reset to the default value.
    """
    cp = get_configParser(config['conffile'])
    # don't allow "internal" options
    general_opts = [i for i in DEFAULTS.keys() if not i in ['user', 'pass', 'passx']]
    if section != 'general':
        section = config['apiurl_aliases'].get(section, section)
        scheme, host = \
            parse_apisrv_url(config.get('scheme', 'https'), section)
        section = urljoin(scheme, host)

    sections = {}
    for url in cp.sections():
        if url == 'general':
            sections[url] = url
        else:
            scheme, host = \
                parse_apisrv_url(config.get('scheme', 'https'), url)
            apiurl = urljoin(scheme, host)
            sections[apiurl] = url

    section = sections.get(section.rstrip('/'), section)
    if not section in cp.sections():
        raise oscerr.ConfigError('unknown section \'%s\'' % section, config['conffile'])
    if section == 'general' and not opt in general_opts or \
       section != 'general' and not opt in api_host_options:
        raise oscerr.ConfigError('unknown config option \'%s\'' % opt, config['conffile'])
    run = False
    if val:
        cp.set(section, opt, val)
        write_config(config['conffile'], cp)
        run = True
    elif delete and cp.has_option(section, opt):
        cp.remove_option(section, opt)
        write_config(config['conffile'], cp)
        run = True
    if run and update:
        kw = {'override_conffile': config['conffile'],
              'override_no_keyring': config['use_keyring'],
              'override_no_gnome_keyring': config['gnome_keyring']}
        kw.update(kwargs)
        get_config(**kw)
    if cp.has_option(section, opt):
        return (opt, cp.get(section, opt, raw=True))
    return (opt, None)

def passx_decode(passx):
    """decode the obfuscated password back to plain text password"""
    return bz2.decompress(base64.b64decode(passx.encode("ascii"))).decode("ascii")

def passx_encode(passwd):
    """encode plain text password to obfuscated form"""
    return base64.b64encode(bz2.compress(passwd.encode('ascii'))).decode("ascii")

def write_initial_config(conffile, entries, custom_template=''):
    """
    write osc's intial configuration file. entries is a dict which contains values
    for the config file (e.g. { 'user' : 'username', 'pass' : 'password' } ).
    custom_template is an optional configuration template.
    """
    conf_template = custom_template or new_conf_template
    config = DEFAULTS.copy()
    config.update(entries)
    # at this point use_keyring and gnome_keyring are str objects
    if config['use_keyring'] == '1' and GENERIC_KEYRING:
        protocol, host = \
            parse_apisrv_url(None, config['apiurl'])
        keyring.set_password(host, config['user'], config['pass'])
        config['pass'] = ''
        config['passx'] = ''
    elif config['gnome_keyring'] == '1' and GNOME_KEYRING:
        protocol, host = \
            parse_apisrv_url(None, config['apiurl'])
        gnomekeyring.set_network_password_sync(
            user=config['user'],
            password=config['pass'],
            protocol=protocol,
            server=host)
        config['user'] = ''
        config['pass'] = ''
        config['passx'] = ''
    if not config['plaintext_passwd']:
        config['pass'] = ''
    else:
        config['passx'] = passx_encode(config['pass'])

    sio = StringIO(conf_template.strip() % config)
    cp = OscConfigParser.OscConfigParser(DEFAULTS)
    cp.readfp(sio)
    write_config(conffile, cp)


def add_section(filename, url, user, passwd):
    """
    Add a section to config file for new api url.
    """
    global config
    cp = get_configParser(filename)
    try:
        cp.add_section(url)
    except OscConfigParser.configparser.DuplicateSectionError:
        # Section might have existed, but was empty
        pass
    if config['use_keyring'] and GENERIC_KEYRING:
        protocol, host = parse_apisrv_url(None, url)
        keyring.set_password(host, user, passwd)
        cp.set(url, 'keyring', '1')
        cp.set(url, 'user', user)
        cp.remove_option(url, 'pass')
        cp.remove_option(url, 'passx')
    elif config['gnome_keyring'] and GNOME_KEYRING:
        protocol, host = parse_apisrv_url(None, url)
        gnomekeyring.set_network_password_sync(
            user=user,
            password=passwd,
            protocol=protocol,
            server=host)
        cp.set(url, 'keyring', '1')
        cp.remove_option(url, 'pass')
        cp.remove_option(url, 'passx')
    else:
        cp.set(url, 'user', user)
        if not config['plaintext_passwd']:
            cp.remove_option(url, 'pass')
            cp.set(url, 'passx', passx_encode(passwd))
        else:
            cp.remove_option(url, 'passx')
            cp.set(url, 'pass', passwd)
    write_config(filename, cp)


def get_config(override_conffile=None,
               override_apiurl=None,
               override_debug=None,
               override_http_debug=None,
               override_http_full_debug=None,
               override_traceback=None,
               override_post_mortem=None,
               override_no_keyring=None,
               override_no_gnome_keyring=None,
               override_verbose=None):
    """do the actual work (see module documentation)"""
    global config

    conffile = override_conffile or os.environ.get('OSC_CONFIG', '~/.oscrc')
    conffile = os.path.expanduser(conffile)

    if not os.path.exists(conffile):
        raise oscerr.NoConfigfile(conffile, \
                                  account_not_configured_text % conffile)

    # okay, we made sure that .oscrc exists

    # make sure it is not world readable, it may contain a password.
    os.chmod(conffile, 0o600)

    cp = get_configParser(conffile)

    if not cp.has_section('general'):
        # FIXME: it might be sufficient to just assume defaults?
        msg = config_incomplete_text % conffile
        msg += new_conf_template % DEFAULTS
        raise oscerr.ConfigError(msg, conffile)

    config = dict(cp.items('general', raw=1))
    config['conffile'] = conffile

    for i in boolean_opts:
        try:
            config[i] = cp.getboolean('general', i)
        except ValueError as e:
            raise oscerr.ConfigError('cannot parse \'%s\' setting: ' % i + str(e), conffile)

    config['packagecachedir'] = os.path.expanduser(config['packagecachedir'])
    config['exclude_glob'] = config['exclude_glob'].split()

    re_clist = re.compile('[, ]+')
    config['extra-pkgs'] = [i.strip() for i in re_clist.split(config['extra-pkgs'].strip()) if i]

    # collect the usernames, passwords and additional options for each api host
    api_host_options = {}

    # Regexp to split extra http headers into a dictionary
    # the text to be matched looks essentially looks this:
    # "Attribute1: value1, Attribute2: value2, ..."
    # there may be arbitray leading and intermitting whitespace.
    # the following regexp does _not_ support quoted commas within the value.
    http_header_regexp = re.compile(r"\s*(.*?)\s*:\s*(.*?)\s*(?:,\s*|\Z)")

    # override values which we were called with
    # This needs to be done before processing API sections as it might be already used there
    if override_no_keyring:
        config['use_keyring'] = False
    if override_no_gnome_keyring:
        config['gnome_keyring'] = False

    aliases = {}
    for url in [x for x in cp.sections() if x != 'general']:
        # backward compatiblity
        scheme, host = parse_apisrv_url(config.get('scheme', 'https'), url)
        apiurl = urljoin(scheme, host)
        user = None
        password = None
        if config['use_keyring'] and GENERIC_KEYRING:
            try:
                # Read from keyring lib if available
                user = cp.get(url, 'user', raw=True)
                password = str(keyring.get_password(host, user))
            except:
                # Fallback to file based auth.
                pass
        elif config['gnome_keyring'] and GNOME_KEYRING:
            # Read from gnome keyring if available
            try:
                gk_data = gnomekeyring.find_network_password_sync(protocol=scheme, server=host)
                if not 'user' in gk_data[0]:
                    raise oscerr.ConfigError('no user found in keyring', conffile)
                user = gk_data[0]['user']
                if 'password' in gk_data[0]:
                    password = str(gk_data[0]['password'])
                else:
                    # this is most likely an error
                    print('warning: no password found in keyring', file=sys.stderr)
            except gnomekeyring.NoMatchError:
                # Fallback to file based auth.
                pass

        if not user is None and len(user) == 0:
            user = None
            print('Warning: blank user in the keyring for the ' \
                'apiurl %s.\nPlease fix your keyring entry.', file=sys.stderr)

        if user is not None and password is None:
            err = ('no password defined for "%s".\nPlease fix your keyring '
                   'entry or gnome-keyring setup.\nAssuming an empty password.'
                   % url)
            print(err, file=sys.stderr)
            password = ''

        # Read credentials from config
        if user is None:
            #FIXME: this could actually be the ideal spot to take defaults
            #from the general section.
            user = cp.get(url, 'user', raw=True)        # need to set raw to prevent '%' expansion
            password = cp.get(url, 'pass', raw=True)    # especially on password!
            try:
                passwordx = passx_decode(cp.get(url, 'passx', raw=True))  # especially on password!
            except:
                passwordx = ''

            if password == None or password == 'your_password':
                password = ''

            if user is None or user == '':
                raise oscerr.ConfigError('user is blank for %s, please delete or complete the "user=" entry in %s.' % (apiurl, config['conffile']), config['conffile'])

            if config['plaintext_passwd'] and passwordx or not config['plaintext_passwd'] and password:
                if config['plaintext_passwd']:
                    if password != passwordx:
                        print('%s: rewriting from encoded pass to plain pass' % url, file=sys.stderr)
                    add_section(conffile, url, user, passwordx)
                    password = passwordx
                else:
                    if password != passwordx:
                        print('%s: rewriting from plain pass to encoded pass' % url, file=sys.stderr)
                    add_section(conffile, url, user, password)

            if not config['plaintext_passwd']:
                password = passwordx

        if cp.has_option(url, 'http_headers'):
            http_headers = cp.get(url, 'http_headers')
            http_headers = http_header_regexp.findall(http_headers)
        else:
            http_headers = []
        if cp.has_option(url, 'aliases'):
            for i in cp.get(url, 'aliases').split(','):
                key = i.strip()
                if key == '':
                    continue
                if key in aliases:
                    msg = 'duplicate alias entry: \'%s\' is already used for another apiurl' % key
                    raise oscerr.ConfigError(msg, conffile)
                aliases[key] = url

        api_host_options[apiurl] = {'user': user,
                                    'pass': password,
                                    'http_headers': http_headers}

        optional = ('email', 'sslcertck', 'cafile', 'capath')
        for key in optional:
            if cp.has_option(url, key):
                if key == 'sslcertck':
                    api_host_options[apiurl][key] = cp.getboolean(url, key)
                else:
                    api_host_options[apiurl][key] = cp.get(url, key)

        if not 'sslcertck' in api_host_options[apiurl]:
            api_host_options[apiurl]['sslcertck'] = True

        if scheme == 'http':
            api_host_options[apiurl]['sslcertck'] = False

        if cp.has_option(url, 'trusted_prj'):
            api_host_options[apiurl]['trusted_prj'] = cp.get(url, 'trusted_prj').split(' ')
        else:
            api_host_options[apiurl]['trusted_prj'] = []

    # add the auth data we collected to the config dict
    config['api_host_options'] = api_host_options
    config['apiurl_aliases'] = aliases

    apiurl = aliases.get(config['apiurl'], config['apiurl'])
    config['apiurl'] = urljoin(*parse_apisrv_url(None, apiurl))
    # backward compatibility
    if 'apisrv' in config:
        apisrv = config['apisrv'].lstrip('http://')
        apisrv = apisrv.lstrip('https://')
        scheme = config.get('scheme', 'https')
        config['apiurl'] = urljoin(scheme, apisrv)
    if 'apisrc' in config or 'scheme' in config:
        print('Warning: Use of the \'scheme\' or \'apisrv\' in ~/.oscrc is deprecated!\n' \
                            'Warning: See README for migration details.', file=sys.stderr)
    if 'build_platform' in config:
        print('Warning: Use of \'build_platform\' config option is deprecated! (use \'build_repository\' instead)', file=sys.stderr)
        config['build_repository'] = config['build_platform']

    config['verbose'] = int(config['verbose'])
    # override values which we were called with
    if override_verbose:
        config['verbose'] = override_verbose + 1

    if override_debug:
        config['debug'] = override_debug
    if override_http_debug:
        config['http_debug'] = override_http_debug
    if override_http_full_debug:
        config['http_debug'] = override_http_full_debug or config['http_debug']
        config['http_full_debug'] = override_http_full_debug
    if override_traceback:
        config['traceback'] = override_traceback
    if override_post_mortem:
        config['post_mortem'] = override_post_mortem
    if override_apiurl:
        apiurl = aliases.get(override_apiurl, override_apiurl)
        # check if apiurl is a valid url
        config['apiurl'] = urljoin(*parse_apisrv_url(None, apiurl))

    # XXX unless config['user'] goes away (and is replaced with a handy function, or
    # config becomes an object, even better), set the global 'user' here as well,
    # provided that there _are_ credentials for the chosen apiurl:
    try:
        config['user'] = get_apiurl_usr(config['apiurl'])
    except oscerr.ConfigMissingApiurl as e:
        e.msg = config_missing_apiurl_text % config['apiurl']
        e.file = conffile
        raise e

    # finally, initialize urllib2 for to use the credentials for Basic Authentication
    init_basicauth(config)


# vim: sw=4 et

########NEW FILE########
__FILENAME__ = core
# Copyright (C) 2006 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or version 3 (at your option).

from __future__ import print_function

__version__ = '0.145git'

# __store_version__ is to be incremented when the format of the working copy
# "store" changes in an incompatible way. Please add any needed migration
# functionality to check_store_version().
__store_version__ = '1.0'

import locale
import os
import os.path
import sys
import shutil
import subprocess
import re
import socket
import errno
import shlex

try:
    from urllib.parse import urlsplit, urlunsplit, urlparse, quote_plus, urlencode, unquote
    from urllib.error import HTTPError
    from urllib.request import pathname2url, install_opener, urlopen
    from urllib.request import Request as URLRequest
    from io import StringIO
except ImportError:
    #python 2.x
    from urlparse import urlsplit, urlunsplit, urlparse
    from urllib import pathname2url, quote_plus, urlencode, unquote
    from urllib2 import HTTPError, install_opener, urlopen
    from urllib2 import Request as URLRequest
    from cStringIO import StringIO


try:
    from xml.etree import cElementTree as ET
except ImportError:
    import cElementTree as ET

from . import oscerr
from . import conf

try:
    # python 2.6 and python 2.7
    unicode
    ET_ENCODING = "utf-8"
    # python 2.6 does not have bytes and python 2.7 reimplements it as alias to
    # str, but in incompatible way as it does not accept the same arguments
    bytes = lambda x, *args: x
except:
    #python3 does not have unicode, so lets reimplement it
    #as void function as it already gets unicode strings
    unicode = lambda x, *args: x
    ET_ENCODING = "unicode"

DISTURL_RE = re.compile(r"^(?P<bs>.*)://(?P<apiurl>.*?)/(?P<project>.*?)/(?P<repository>.*?)/(?P<revision>.*)-(?P<source>.*)$")
BUILDLOGURL_RE = re.compile(r"^(?P<apiurl>https?://.*?)/build/(?P<project>.*?)/(?P<repository>.*?)/(?P<arch>.*?)/(?P<package>.*?)/_log$")
BUFSIZE = 1024*1024
store = '.osc'

new_project_templ = """\
<project name="%(name)s">

  <title></title> <!-- Short title of NewProject -->
  <description></description>
    <!-- This is for a longer description of the purpose of the project -->

  <person role="maintainer" userid="%(user)s" />
  <person role="bugowner" userid="%(user)s" />
<!-- remove this block to publish your packages on the mirrors -->
  <publish>
    <disable />
  </publish>
  <build>
    <enable />
  </build>
  <debuginfo>
    <disable />
  </debuginfo>

<!-- remove this comment to enable one or more build targets

  <repository name="openSUSE_Factory">
    <path project="openSUSE:Factory" repository="snapshot" />
    <arch>x86_64</arch>
    <arch>i586</arch>
  </repository>
  <repository name="openSUSE_11.2">
    <path project="openSUSE:11.2" repository="standard"/>
    <arch>x86_64</arch>
    <arch>i586</arch>
  </repository>
  <repository name="openSUSE_11.1">
    <path project="openSUSE:11.1" repository="standard"/>
    <arch>x86_64</arch>
    <arch>i586</arch>
  </repository>
  <repository name="Fedora_12">
    <path project="Fedora:12" repository="standard" />
    <arch>x86_64</arch>
    <arch>i586</arch>
  </repository>
  <repository name="SLE_11">
    <path project="SUSE:SLE-11" repository="standard" />
    <arch>x86_64</arch>
    <arch>i586</arch>
  </repository>
-->

</project>
"""

new_package_templ = """\
<package name="%(name)s">

  <title></title> <!-- Title of package -->

  <description></description> <!-- for long description -->

<!-- following roles are inherited from the parent project
  <person role="maintainer" userid="%(user)s"/>
  <person role="bugowner" userid="%(user)s"/>
-->
<!--
  <url>PUT_UPSTREAM_URL_HERE</url>
-->

<!--
  use one of the examples below to disable building of this package
  on a certain architecture, in a certain repository,
  or a combination thereof:

  <disable arch="x86_64"/>
  <disable repository="SUSE_SLE-10"/>
  <disable repository="SUSE_SLE-10" arch="x86_64"/>

  Possible sections where you can use the tags above:
  <build>
  </build>
  <debuginfo>
  </debuginfo>
  <publish>
  </publish>
  <useforbuild>
  </useforbuild>

  Please have a look at:
  http://en.opensuse.org/Restricted_formats
  Packages containing formats listed there are NOT allowed to
  be packaged in the openSUSE Buildservice and will be deleted!

-->

</package>
"""

new_attribute_templ = """\
<attributes>
  <attribute namespace="" name="">
    <value><value>
  </attribute>
</attributes>
"""

new_user_template = """\
<person>
  <login>%(user)s</login>
  <email>PUT_EMAIL_ADDRESS_HERE</email>
  <realname>PUT_REAL_NAME_HERE</realname>
  <watchlist>
    <project name="home:%(user)s"/>
  </watchlist>
</person>
"""

info_templ = """\
Project name: %s
Package name: %s
Path: %s
API URL: %s
Source URL: %s
srcmd5: %s
Revision: %s
Link info: %s
"""

new_pattern_template = """\
<!-- See https://github.com/openSUSE/libzypp/tree/master/zypp/parser/yum/schema/patterns.rng -->

<!--
<pattern xmlns="http://novell.com/package/metadata/suse/pattern"
 xmlns:rpm="http://linux.duke.edu/metadata/rpm">
 <name></name>
 <summary></summary>
 <description></description>
 <uservisible/>
 <category lang="en"></category>
 <rpm:requires>
   <rpm:entry name="must-have-package"/>
 </rpm:requires>
 <rpm:recommends>
   <rpm:entry name="package"/>
 </rpm:recommends>
 <rpm:suggests>
   <rpm:entry name="anotherpackage"/>
 </rpm:suggests>
</pattern>
-->
"""

buildstatus_symbols = {'succeeded':       '.',
                       'disabled':        ' ',
                       'expansion error': 'U',  # obsolete with OBS 2.0
                       'unresolvable':    'U',
                       'failed':          'F',
                       'broken':          'B',
                       'blocked':         'b',
                       'building':        '%',
                       'finished':        'f',
                       'scheduled':       's',
                       'locked':          'L',
                       'excluded':        'x',
                       'dispatching':     'd',
                       'signing':         'S',
}


# os.path.samefile is available only under Unix
def os_path_samefile(path1, path2):
    try:
        return os.path.samefile(path1, path2)
    except:
        return os.path.realpath(path1) == os.path.realpath(path2)

class File:
    """represent a file, including its metadata"""
    def __init__(self, name, md5, size, mtime, skipped=False):
        self.name = name
        self.md5 = md5
        self.size = size
        self.mtime = mtime
        self.skipped = skipped
    def __repr__(self):
        return self.name
    def __str__(self):
        return self.name


class Serviceinfo:
    """Source service content
    """
    def __init__(self):
        """creates an empty serviceinfo instance"""
        self.services = None
        self.project  = None
        self.package  = None

    def read(self, serviceinfo_node, append=False):
        """read in the source services <services> element passed as
        elementtree node.
        """
        if serviceinfo_node == None:
            return
        if not append or self.services == None:
            self.services = []
        services = serviceinfo_node.findall('service')

        for service in services:
            name = service.get('name')
            mode = service.get('mode', None)
            data = { 'name' : name, 'mode' : '' }
            if mode:
                data['mode'] = mode
            try:
                for param in service.findall('param'):
                    option = param.get('name', None)
                    value = ""
                    if param.text:
                        value = param.text
                    name += " --" + option + " '" + value + "'"
                data['command'] = name
                self.services.append(data)
            except:
                msg = 'invalid service format:\n%s' % ET.tostring(serviceinfo_node, encoding=ET_ENCODING)
                raise oscerr.APIError(msg)

    def getProjectGlobalServices(self, apiurl, project, package):
        # get all project wide services in one file, we don't store it yet
        u = makeurl(apiurl, ['source', project, package], query='cmd=getprojectservices')
        try:
            f = http_POST(u)
            root = ET.parse(f).getroot()
            self.read(root, True)
            self.project = project
            self.package = package
        except HTTPError as e:
            if e.code != 403 and e.code != 400:
                raise e

    def addVerifyFile(self, serviceinfo_node, filename):
        import hashlib

        f = open(filename, 'r')
        digest = hashlib.sha256(f.read()).hexdigest()
        f.close()

        r = serviceinfo_node
        s = ET.Element( "service", name="verify_file" )
        ET.SubElement(s, "param", name="file").text = filename
        ET.SubElement(s, "param", name="verifier").text  = "sha256"
        ET.SubElement(s, "param", name="checksum").text = digest

        r.append( s )
        return r


    def addDownloadUrl(self, serviceinfo_node, url_string):
        url = urlparse( url_string )
        protocol = url.scheme
        host = url.netloc
        path = url.path

        r = serviceinfo_node
        s = ET.Element( "service", name="download_url" )
        ET.SubElement(s, "param", name="protocol").text = protocol
        ET.SubElement(s, "param", name="host").text     = host
        ET.SubElement(s, "param", name="path").text     = path

        r.append( s )
        return r

    def addGitUrl(self, serviceinfo_node, url_string):
        r = serviceinfo_node
        s = ET.Element( "service", name="tar_scm" )
        ET.SubElement(s, "param", name="url").text = url_string
        ET.SubElement(s, "param", name="scm").text = "git"
        r.append( s )
        return r

    def addRecompressTar(self, serviceinfo_node):
        r = serviceinfo_node
        s = ET.Element( "service", name="recompress" )
        ET.SubElement(s, "param", name="file").text = "*.tar"
        ET.SubElement(s, "param", name="compression").text = "bz2"
        r.append( s )
        return r

    def execute(self, dir, callmode = None, singleservice = None, verbose = None):
        import tempfile

        # cleanup existing generated files
        for filename in os.listdir(dir):
            if filename.startswith('_service:') or filename.startswith('_service_'):
                ent = os.path.join(dir, filename)
                if os.path.isdir(ent):
                    shutil.rmtree(ent)
                else:
                    os.unlink(ent)

        allservices = self.services or []
        if singleservice and not singleservice in allservices:
            # set array to the manual specified singleservice, if it is not part of _service file
            data = { 'name' : singleservice, 'command' : singleservice, 'mode' : '' }
            allservices = [data]

        # set environment when using OBS 2.3 or later
        if self.project != None:
            os.putenv("OBS_SERVICE_PROJECT", self.project)
            os.putenv("OBS_SERVICE_PACKAGE", self.package)

        # recreate files
        ret = 0
        for service in allservices:
            if singleservice and service['name'] != singleservice:
                continue
            if service['mode'] == "serveronly" and callmode != "disabled":
                continue
            if service['mode'] == "disabled" and callmode != "disabled":
                continue
            if service['mode'] != "disabled" and callmode == "disabled":
                continue
            if service['mode'] != "trylocal" and service['mode'] != "localonly" and callmode == "trylocal":
                continue
            call = service['command']
            temp_dir = None
            try:
                temp_dir = tempfile.mkdtemp()
                name = call.split(None, 1)[0]
                if not os.path.exists("/usr/lib/obs/service/"+name):
                    raise oscerr.PackageNotInstalled("obs-service-"+name)
                cmd = "/usr/lib/obs/service/" + call + " --outdir " + temp_dir
                if conf.config['verbose'] > 1 or verbose:
                    print("Run source service:", cmd)
                r = run_external(cmd, shell=True)

                if r != 0:
                    print("Aborting: service call failed: " + cmd)
                    # FIXME: addDownloadUrlService calls si.execute after 
                    #        updating _services.
                    return r

                if service['mode'] == "disabled" or service['mode'] == "trylocal" or service['mode'] == "localonly" or callmode == "local" or callmode == "trylocal":
                    for filename in os.listdir(temp_dir):
                        shutil.move( os.path.join(temp_dir, filename), os.path.join(dir, filename) )
                else:
                    for filename in os.listdir(temp_dir):
                        shutil.move( os.path.join(temp_dir, filename), os.path.join(dir, "_service:"+name+":"+filename) )
            finally:
                if temp_dir is not None:
                    shutil.rmtree(temp_dir)

        return 0

class Linkinfo:
    """linkinfo metadata (which is part of the xml representing a directory
    """
    def __init__(self):
        """creates an empty linkinfo instance"""
        self.project = None
        self.package = None
        self.xsrcmd5 = None
        self.lsrcmd5 = None
        self.srcmd5 = None
        self.error = None
        self.rev = None
        self.baserev = None

    def read(self, linkinfo_node):
        """read in the linkinfo metadata from the <linkinfo> element passed as
        elementtree node.
        If the passed element is None, the method does nothing.
        """
        if linkinfo_node == None:
            return
        self.project = linkinfo_node.get('project')
        self.package = linkinfo_node.get('package')
        self.xsrcmd5 = linkinfo_node.get('xsrcmd5')
        self.lsrcmd5 = linkinfo_node.get('lsrcmd5')
        self.srcmd5  = linkinfo_node.get('srcmd5')
        self.error   = linkinfo_node.get('error')
        self.rev     = linkinfo_node.get('rev')
        self.baserev = linkinfo_node.get('baserev')

    def islink(self):
        """returns True if the linkinfo is not empty, otherwise False"""
        if self.xsrcmd5 or self.lsrcmd5:
            return True
        return False

    def isexpanded(self):
        """returns True if the package is an expanded link"""
        if self.lsrcmd5 and not self.xsrcmd5:
            return True
        return False

    def haserror(self):
        """returns True if the link is in error state (could not be applied)"""
        if self.error:
            return True
        return False

    def __str__(self):
        """return an informatory string representation"""
        if self.islink() and not self.isexpanded():
            return 'project %s, package %s, xsrcmd5 %s, rev %s' \
                    % (self.project, self.package, self.xsrcmd5, self.rev)
        elif self.islink() and self.isexpanded():
            if self.haserror():
                return 'broken link to project %s, package %s, srcmd5 %s, lsrcmd5 %s: %s' \
                        % (self.project, self.package, self.srcmd5, self.lsrcmd5, self.error)
            else:
                return 'expanded link to project %s, package %s, srcmd5 %s, lsrcmd5 %s' \
                        % (self.project, self.package, self.srcmd5, self.lsrcmd5)
        else:
            return 'None'


# http://effbot.org/zone/element-lib.htm#prettyprint
def xmlindent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            xmlindent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class Project:
    """
    Represent a checked out project directory, holding packages.

    :Attributes:
        ``dir``
            The directory path containing the project.

        ``name``
            The name of the project.

        ``apiurl``
            The endpoint URL of the API server.

        ``pacs_available``
            List of names of packages available server-side.
            This is only populated if ``getPackageList`` is set
            to ``True`` in the constructor.

        ``pacs_have``
            List of names of packages which exist server-side
            and exist in the local project working copy (if
            'do_package_tracking' is disabled).
            If 'do_package_tracking' is enabled it represents the
            list names of packages which are tracked in the project
            working copy (that is it might contain packages which
            exist on the server as well as packages which do not
            exist on the server (for instance if the local package
            was added or if the package was removed on the server-side)).

        ``pacs_excluded``
            List of names of packages in the local project directory
            which are excluded by the `exclude_glob` configuration
            variable.  Only set if `do_package_tracking` is enabled.

        ``pacs_unvers``
            List of names of packages in the local project directory
            which are not tracked. Only set if `do_package_tracking`
            is enabled.

        ``pacs_broken``
            List of names of packages which are tracked but do not
            exist in the local project working copy. Only set if
            `do_package_tracking` is enabled.

        ``pacs_missing``
            List of names of packages which exist server-side but
            are not expected to exist in the local project directory.
    """

    REQ_STOREFILES = ('_project', '_apiurl')
    if conf.config['do_package_tracking']:
        REQ_STOREFILES += ('_packages',)

    def __init__(self, dir, getPackageList=True, progress_obj=None, wc_check=True):
        """
        Constructor.

        :Parameters:
            `dir` : str
                The directory path containing the checked out project.

            `getPackageList` : bool
                Set to `False` if you want to skip retrieval from the
                server of the list of packages in the project .

            `wc_check` : bool
        """
        import fnmatch
        self.dir = dir
        self.absdir = os.path.abspath(dir)
        self.progress_obj = progress_obj

        self.name = store_read_project(self.dir)
        self.apiurl = store_read_apiurl(self.dir, defaulturl=not wc_check)

        dirty_files = []
        if wc_check:
            dirty_files = self.wc_check()
        if dirty_files:
            msg = 'Your working copy \'%s\' is in an inconsistent state.\n' \
                'Please run \'osc repairwc %s\' and check the state\n' \
                'of the working copy afterwards (via \'osc status %s\')' % (self.dir, self.dir, self.dir)
            raise oscerr.WorkingCopyInconsistent(self.name, None, dirty_files, msg)

        if getPackageList:
            self.pacs_available = meta_get_packagelist(self.apiurl, self.name)
        else:
            self.pacs_available = []

        if conf.config['do_package_tracking']:
            self.pac_root = self.read_packages().getroot()
            self.pacs_have = [ pac.get('name') for pac in self.pac_root.findall('package') ]
            self.pacs_excluded = [ i for i in os.listdir(self.dir)
                                   for j in conf.config['exclude_glob']
                                   if fnmatch.fnmatch(i, j) ]
            self.pacs_unvers = [ i for i in os.listdir(self.dir) if i not in self.pacs_have and i not in self.pacs_excluded ]
            # store all broken packages (e.g. packages which where removed by a non-osc cmd)
            # in the self.pacs_broken list
            self.pacs_broken = []
            for p in self.pacs_have:
                if not os.path.isdir(os.path.join(self.absdir, p)):
                    # all states will be replaced with the '!'-state
                    # (except it is already marked as deleted ('D'-state))
                    self.pacs_broken.append(p)
        else:
            self.pacs_have = [ i for i in os.listdir(self.dir) if i in self.pacs_available ]

        self.pacs_missing = [ i for i in self.pacs_available if i not in self.pacs_have ]

    def wc_check(self):
        global store
        dirty_files = []
        for fname in Project.REQ_STOREFILES:
            if not os.path.exists(os.path.join(self.absdir, store, fname)):
                dirty_files.append(fname)
        return dirty_files

    def wc_repair(self, apiurl=None):
        global store
        if not os.path.exists(os.path.join(self.dir, store, '_apiurl')) or apiurl:
            if apiurl is None:
                msg = 'cannot repair wc: the \'_apiurl\' file is missing but ' \
                    'no \'apiurl\' was passed to wc_repair'
                # hmm should we raise oscerr.WrongArgs?
                raise oscerr.WorkingCopyInconsistent(self.prjname, self.name, [], msg)
            # sanity check
            conf.parse_apisrv_url(None, apiurl)
            store_write_apiurl(self.dir, apiurl)
            self.apiurl = store_read_apiurl(self.dir, defaulturl=False)

    def checkout_missing_pacs(self, expand_link=False):
        for pac in self.pacs_missing:

            if conf.config['do_package_tracking'] and pac in self.pacs_unvers:
                # pac is not under version control but a local file/dir exists
                msg = 'can\'t add package \'%s\': Object already exists' % pac
                raise oscerr.PackageExists(self.name, pac, msg)
            else:
                print('checking out new package %s' % pac)
                checkout_package(self.apiurl, self.name, pac, \
                                 pathname=getTransActPath(os.path.join(self.dir, pac)), \
                                 prj_obj=self, prj_dir=self.dir, expand_link=expand_link, progress_obj=self.progress_obj)

    def status(self, pac):
        exists = os.path.exists(os.path.join(self.absdir, pac))
        st = self.get_state(pac)
        if st is None and exists:
            return '?'
        elif st is None:
            raise oscerr.OscIOError(None, 'osc: \'%s\' is not under version control' % pac)
        elif st in ('A', ' ') and not exists:
            return '!'
        elif st == 'D' and not exists:
            return 'D'
        else:
            return st

    def get_status(self, *exclude_states):
        res = []
        for pac in self.pacs_have:
            st = self.status(pac)
            if not st in exclude_states:
                res.append((st, pac))
        if not '?' in exclude_states:
            res.extend([('?', pac) for pac in self.pacs_unvers])
        return res

    def get_pacobj(self, pac, *pac_args, **pac_kwargs):
        try:
            st = self.status(pac)
            if st in ('?', '!') or st == 'D' and not os.path.exists(os.path.join(self.dir, pac)):
                return None
            return Package(os.path.join(self.dir, pac), *pac_args, **pac_kwargs)
        except oscerr.OscIOError:
            return None

    def set_state(self, pac, state):
        node = self.get_package_node(pac)
        if node == None:
            self.new_package_entry(pac, state)
        else:
            node.set('state', state)

    def get_package_node(self, pac):
        for node in self.pac_root.findall('package'):
            if pac == node.get('name'):
                return node
        return None

    def del_package_node(self, pac):
        for node in self.pac_root.findall('package'):
            if pac == node.get('name'):
                self.pac_root.remove(node)

    def get_state(self, pac):
        node = self.get_package_node(pac)
        if node != None:
            return node.get('state')
        else:
            return None

    def new_package_entry(self, name, state):
        ET.SubElement(self.pac_root, 'package', name=name, state=state)

    def read_packages(self):
        """
        Returns an ``xml.etree.cElementTree`` object representing the
        parsed contents of the project's ``.osc/_packages`` XML file.
        """
        global store

        packages_file = os.path.join(self.absdir, store, '_packages')
        if os.path.isfile(packages_file) and os.path.getsize(packages_file):
            return ET.parse(packages_file)
        else:
            # scan project for existing packages and migrate them
            cur_pacs = []
            for data in os.listdir(self.dir):
                pac_dir = os.path.join(self.absdir, data)
                # we cannot use self.pacs_available because we cannot guarantee that the package list
                # was fetched from the server
                if data in meta_get_packagelist(self.apiurl, self.name) and is_package_dir(pac_dir) \
                   and Package(pac_dir).name == data:
                    cur_pacs.append(ET.Element('package', name=data, state=' '))
            store_write_initial_packages(self.absdir, self.name, cur_pacs)
            return ET.parse(os.path.join(self.absdir, store, '_packages'))

    def write_packages(self):
        xmlindent(self.pac_root)
        store_write_string(self.absdir, '_packages', ET.tostring(self.pac_root, encoding=ET_ENCODING))

    def addPackage(self, pac):
        import fnmatch
        for i in conf.config['exclude_glob']:
            if fnmatch.fnmatch(pac, i):
                msg = 'invalid package name: \'%s\' (see \'exclude_glob\' config option)' % pac
                raise oscerr.OscIOError(None, msg)
        state = self.get_state(pac)
        if state == None or state == 'D':
            self.new_package_entry(pac, 'A')
            self.write_packages()
            # sometimes the new pac doesn't exist in the list because
            # it would take too much time to update all data structs regularly
            if pac in self.pacs_unvers:
                self.pacs_unvers.remove(pac)
        else:
            raise oscerr.PackageExists(self.name, pac, 'package \'%s\' is already under version control' % pac)

    def delPackage(self, pac, force = False):
        state = self.get_state(pac.name)
        can_delete = True
        if state == ' ' or state == 'D':
            del_files = []
            for filename in pac.filenamelist + pac.filenamelist_unvers:
                filestate = pac.status(filename)
                if filestate == 'M' or filestate == 'C' or \
                   filestate == 'A' or filestate == '?':
                    can_delete = False
                else:
                    del_files.append(filename)
            if can_delete or force:
                for filename in del_files:
                    pac.delete_localfile(filename)
                    if pac.status(filename) != '?':
                        # this is not really necessary
                        pac.put_on_deletelist(filename)
                        print(statfrmt('D', getTransActPath(os.path.join(pac.dir, filename))))
                print(statfrmt('D', getTransActPath(os.path.join(pac.dir, os.pardir, pac.name))))
                pac.write_deletelist()
                self.set_state(pac.name, 'D')
                self.write_packages()
            else:
                print('package \'%s\' has local modifications (see osc st for details)' % pac.name)
        elif state == 'A':
            if force:
                delete_dir(pac.absdir)
                self.del_package_node(pac.name)
                self.write_packages()
                print(statfrmt('D', pac.name))
            else:
                print('package \'%s\' has local modifications (see osc st for details)' % pac.name)
        elif state == None:
            print('package is not under version control')
        else:
            print('unsupported state')

    def update(self, pacs = (), expand_link=False, unexpand_link=False, service_files=False):
        if len(pacs):
            for pac in pacs:
                Package(os.path.join(self.dir, pac), progress_obj=self.progress_obj).update()
        else:
            # we need to make sure that the _packages file will be written (even if an exception
            # occurs)
            try:
                # update complete project
                # packages which no longer exists upstream
                upstream_del = [ pac for pac in self.pacs_have if not pac in self.pacs_available and self.get_state(pac) != 'A']

                for pac in upstream_del:
                    if self.status(pac) != '!':
                        p = Package(os.path.join(self.dir, pac))
                        self.delPackage(p, force = True)
                        delete_storedir(p.storedir)
                        try:
                            os.rmdir(pac)
                        except:
                            pass
                    self.pac_root.remove(self.get_package_node(pac))
                    self.pacs_have.remove(pac)

                for pac in self.pacs_have:
                    state = self.get_state(pac)
                    if pac in self.pacs_broken:
                        if self.get_state(pac) != 'A':
                            checkout_package(self.apiurl, self.name, pac,
                                             pathname=getTransActPath(os.path.join(self.dir, pac)), prj_obj=self, \
                                             prj_dir=self.dir, expand_link=not unexpand_link, progress_obj=self.progress_obj)
                    elif state == ' ':
                        # do a simple update
                        p = Package(os.path.join(self.dir, pac), progress_obj=self.progress_obj)
                        rev = None
                        if expand_link and p.islink() and not p.isexpanded():
                            if p.haslinkerror():
                                try:
                                    rev = show_upstream_xsrcmd5(p.apiurl, p.prjname, p.name, revision=p.rev)
                                except:
                                    rev = show_upstream_xsrcmd5(p.apiurl, p.prjname, p.name, revision=p.rev, linkrev="base")
                                    p.mark_frozen()
                            else:
                                rev = p.linkinfo.xsrcmd5
                            print('Expanding to rev', rev)
                        elif unexpand_link and p.islink() and p.isexpanded():
                            rev = p.linkinfo.lsrcmd5
                            print('Unexpanding to rev', rev)
                        elif p.islink() and p.isexpanded():
                            rev = p.latest_rev()
                        print('Updating %s' % p.name)
                        p.update(rev, service_files)
                        if unexpand_link:
                            p.unmark_frozen()
                    elif state == 'D':
                        # TODO: Package::update has to fixed to behave like svn does
                        if pac in self.pacs_broken:
                            checkout_package(self.apiurl, self.name, pac,
                                             pathname=getTransActPath(os.path.join(self.dir, pac)), prj_obj=self, \
                                             prj_dir=self.dir, expand_link=expand_link, progress_obj=self.progress_obj)
                        else:
                            Package(os.path.join(self.dir, pac), progress_obj=self.progress_obj).update()
                    elif state == 'A' and pac in self.pacs_available:
                        # file/dir called pac already exists and is under version control
                        msg = 'can\'t add package \'%s\': Object already exists' % pac
                        raise oscerr.PackageExists(self.name, pac, msg)
                    elif state == 'A':
                        # do nothing
                        pass
                    else:
                        print('unexpected state.. package \'%s\'' % pac)

                self.checkout_missing_pacs(expand_link=not unexpand_link)
            finally:
                self.write_packages()

    def commit(self, pacs = (), msg = '', files = {}, verbose = False, skip_local_service_run = False, can_branch=False):
        if len(pacs):
            try:
                for pac in pacs:
                    todo = []
                    if pac in files:
                        todo = files[pac]
                    state = self.get_state(pac)
                    if state == 'A':
                        self.commitNewPackage(pac, msg, todo, verbose=verbose, skip_local_service_run=skip_local_service_run)
                    elif state == 'D':
                        self.commitDelPackage(pac)
                    elif state == ' ':
                        # display the correct dir when sending the changes
                        if os_path_samefile(os.path.join(self.dir, pac), os.getcwd()):
                            p = Package('.')
                        else:
                            p = Package(os.path.join(self.dir, pac))
                        p.todo = todo
                        p.commit(msg, verbose=verbose, skip_local_service_run=skip_local_service_run, can_branch=can_branch)
                    elif pac in self.pacs_unvers and not is_package_dir(os.path.join(self.dir, pac)):
                        print('osc: \'%s\' is not under version control' % pac)
                    elif pac in self.pacs_broken:
                        print('osc: \'%s\' package not found' % pac)
                    elif state == None:
                        self.commitExtPackage(pac, msg, todo, verbose=verbose, skip_local_service_run=skip_local_service_run)
            finally:
                self.write_packages()
        else:
            # if we have packages marked as '!' we cannot commit
            for pac in self.pacs_broken:
                if self.get_state(pac) != 'D':
                    msg = 'commit failed: package \'%s\' is missing' % pac
                    raise oscerr.PackageMissing(self.name, pac, msg)
            try:
                for pac in self.pacs_have:
                    state = self.get_state(pac)
                    if state == ' ':
                        # do a simple commit
                        Package(os.path.join(self.dir, pac)).commit(msg, verbose=verbose, skip_local_service_run=skip_local_service_run)
                    elif state == 'D':
                        self.commitDelPackage(pac)
                    elif state == 'A':
                        self.commitNewPackage(pac, msg, verbose=verbose, skip_local_service_run=skip_local_service_run)
            finally:
                self.write_packages()

    def commitNewPackage(self, pac, msg = '', files = [], verbose = False, skip_local_service_run = False):
        """creates and commits a new package if it does not exist on the server"""
        if pac in self.pacs_available:
            print('package \'%s\' already exists' % pac)
        else:
            user = conf.get_apiurl_usr(self.apiurl)
            edit_meta(metatype='pkg',
                      path_args=(quote_plus(self.name), quote_plus(pac)),
                      template_args=({
                              'name': pac,
                              'user': user}),
                      apiurl=self.apiurl)
            # display the correct dir when sending the changes
            olddir = os.getcwd()
            if os_path_samefile(os.path.join(self.dir, pac), os.curdir):
                os.chdir(os.pardir)
                p = Package(pac)
            else:
                p = Package(os.path.join(self.dir, pac))
            p.todo = files
            print(statfrmt('Sending', os.path.normpath(p.dir)))
            p.commit(msg=msg, verbose=verbose, skip_local_service_run=skip_local_service_run)
            self.set_state(pac, ' ')
            os.chdir(olddir)

    def commitDelPackage(self, pac):
        """deletes a package on the server and in the working copy"""
        try:
            # display the correct dir when sending the changes
            if os_path_samefile(os.path.join(self.dir, pac), os.curdir):
                pac_dir = pac
            else:
                pac_dir = os.path.join(self.dir, pac)
            p = Package(os.path.join(self.dir, pac))
            #print statfrmt('Deleting', os.path.normpath(os.path.join(p.dir, os.pardir, pac)))
            delete_storedir(p.storedir)
            try:
                os.rmdir(p.dir)
            except:
                pass
        except OSError:
            pac_dir = os.path.join(self.dir, pac)
        #print statfrmt('Deleting', getTransActPath(os.path.join(self.dir, pac)))
        print(statfrmt('Deleting', getTransActPath(pac_dir)))
        delete_package(self.apiurl, self.name, pac)
        self.del_package_node(pac)

    def commitExtPackage(self, pac, msg, files = [], verbose=False, skip_local_service_run=False):
        """commits a package from an external project"""
        if os_path_samefile(os.path.join(self.dir, pac), os.getcwd()):
            pac_path = '.'
        else:
            pac_path = os.path.join(self.dir, pac)

        project = store_read_project(pac_path)
        package = store_read_package(pac_path)
        apiurl = store_read_apiurl(pac_path, defaulturl=False)
        if not meta_exists(metatype='pkg',
                           path_args=(quote_plus(project), quote_plus(package)),
                           template_args=None, create_new=False, apiurl=apiurl):
            user = conf.get_apiurl_usr(self.apiurl)
            edit_meta(metatype='pkg',
                      path_args=(quote_plus(project), quote_plus(package)),
                      template_args=({'name': pac, 'user': user}), apiurl=apiurl)
        p = Package(pac_path)
        p.todo = files
        p.commit(msg=msg, verbose=verbose, skip_local_service_run=skip_local_service_run)

    def __str__(self):
        r = []
        r.append('*****************************************************')
        r.append('Project %s (dir=%s, absdir=%s)' % (self.name, self.dir, self.absdir))
        r.append('have pacs:\n%s' % ', '.join(self.pacs_have))
        r.append('missing pacs:\n%s' % ', '.join(self.pacs_missing))
        r.append('*****************************************************')
        return '\n'.join(r)

    @staticmethod
    def init_project(apiurl, dir, project, package_tracking=True, getPackageList=True, progress_obj=None, wc_check=True):
        global store

        if not os.path.exists(dir):
            # use makedirs (checkout_no_colon config option might be enabled)
            os.makedirs(dir)
        elif not os.path.isdir(dir):
            raise oscerr.OscIOError(None, 'error: \'%s\' is no directory' % dir)
        if os.path.exists(os.path.join(dir, store)):
            raise oscerr.OscIOError(None, 'error: \'%s\' is already an initialized osc working copy' % dir)
        else:
            os.mkdir(os.path.join(dir, store))

        store_write_project(dir, project)
        store_write_apiurl(dir, apiurl)
        if package_tracking:
            store_write_initial_packages(dir, project, [])
        return Project(dir, getPackageList, progress_obj, wc_check)


class Package:
    """represent a package (its directory) and read/keep/write its metadata"""

    # should _meta be a required file?
    REQ_STOREFILES = ('_project', '_package', '_apiurl', '_files', '_osclib_version')
    OPT_STOREFILES = ('_to_be_added', '_to_be_deleted', '_in_conflict', '_in_update',
        '_in_commit', '_meta', '_meta_mode', '_frozenlink', '_pulled', '_linkrepair',
        '_size_limit', '_commit_msg')

    def __init__(self, workingdir, progress_obj=None, size_limit=None, wc_check=True):
        global store

        self.dir = workingdir
        self.absdir = os.path.abspath(self.dir)
        self.storedir = os.path.join(self.absdir, store)
        self.progress_obj = progress_obj
        self.size_limit = size_limit
        if size_limit and size_limit == 0:
            self.size_limit = None

        check_store_version(self.dir)

        self.prjname = store_read_project(self.dir)
        self.name = store_read_package(self.dir)
        self.apiurl = store_read_apiurl(self.dir, defaulturl=not wc_check)

        self.update_datastructs()
        dirty_files = []
        if wc_check:
            dirty_files = self.wc_check()
        if dirty_files:
            msg = 'Your working copy \'%s\' is in an inconsistent state.\n' \
                'Please run \'osc repairwc %s\' (Note this might _remove_\n' \
                'files from the .osc/ dir). Please check the state\n' \
                'of the working copy afterwards (via \'osc status %s\')' % (self.dir, self.dir, self.dir)
            raise oscerr.WorkingCopyInconsistent(self.prjname, self.name, dirty_files, msg)

        self.todo = []

    def wc_check(self):
        dirty_files = []
        for fname in self.filenamelist:
            if not os.path.exists(os.path.join(self.storedir, fname)) and not fname in self.skipped:
                dirty_files.append(fname)
        for fname in Package.REQ_STOREFILES:
            if not os.path.isfile(os.path.join(self.storedir, fname)):
                dirty_files.append(fname)
        for fname in os.listdir(self.storedir):
            if fname in Package.REQ_STOREFILES or fname in Package.OPT_STOREFILES or \
                fname.startswith('_build'):
                continue
            elif fname in self.filenamelist and fname in self.skipped:
                dirty_files.append(fname)
            elif not fname in self.filenamelist:
                dirty_files.append(fname)
        for fname in self.to_be_deleted[:]:
            if not fname in self.filenamelist:
                dirty_files.append(fname)
        for fname in self.in_conflict[:]:
            if not fname in self.filenamelist:
                dirty_files.append(fname)
        return dirty_files

    def wc_repair(self, apiurl=None):
        if not os.path.exists(os.path.join(self.storedir, '_apiurl')) or apiurl:
            if apiurl is None:
                msg = 'cannot repair wc: the \'_apiurl\' file is missing but ' \
                    'no \'apiurl\' was passed to wc_repair'
                # hmm should we raise oscerr.WrongArgs?
                raise oscerr.WorkingCopyInconsistent(self.prjname, self.name, [], msg)
            # sanity check
            conf.parse_apisrv_url(None, apiurl)
            store_write_apiurl(self.dir, apiurl)
            self.apiurl = store_read_apiurl(self.dir, defaulturl=False)
        # all files which are present in the filelist have to exist in the storedir
        for f in self.filelist:
            # XXX: should we also check the md5?
            if not os.path.exists(os.path.join(self.storedir, f.name)) and not f.name in self.skipped:
                # if get_source_file fails we're screwed up...
                get_source_file(self.apiurl, self.prjname, self.name, f.name,
                    targetfilename=os.path.join(self.storedir, f.name), revision=self.rev,
                    mtime=f.mtime)
        for fname in os.listdir(self.storedir):
            if fname in Package.REQ_STOREFILES or fname in Package.OPT_STOREFILES or \
                fname.startswith('_build'):
                continue
            elif not fname in self.filenamelist or fname in self.skipped:
                # this file does not belong to the storedir so remove it
                os.unlink(os.path.join(self.storedir, fname))
        for fname in self.to_be_deleted[:]:
            if not fname in self.filenamelist:
                self.to_be_deleted.remove(fname)
                self.write_deletelist()
        for fname in self.in_conflict[:]:
            if not fname in self.filenamelist:
                self.in_conflict.remove(fname)
                self.write_conflictlist()

    def info(self):
        source_url = makeurl(self.apiurl, ['source', self.prjname, self.name])
        r = info_templ % (self.prjname, self.name, self.absdir, self.apiurl, source_url, self.srcmd5, self.rev, self.linkinfo)
        return r

    def addfile(self, n):
        if not os.path.exists(os.path.join(self.absdir, n)):
            raise oscerr.OscIOError(None, 'error: file \'%s\' does not exist' % n)
        if n in self.to_be_deleted:
            self.to_be_deleted.remove(n)
#            self.delete_storefile(n)
            self.write_deletelist()
        elif n in self.filenamelist or n in self.to_be_added:
            raise oscerr.PackageFileConflict(self.prjname, self.name, n, 'osc: warning: \'%s\' is already under version control' % n)
#        shutil.copyfile(os.path.join(self.dir, n), os.path.join(self.storedir, n))
        if self.dir != '.':
            pathname = os.path.join(self.dir, n)
        else:
            pathname = n
        self.to_be_added.append(n)
        self.write_addlist()
        print(statfrmt('A', pathname))

    def delete_file(self, n, force=False):
        """deletes a file if possible and marks the file as deleted"""
        state = '?'
        try:
            state = self.status(n)
        except IOError as ioe:
            if not force:
                raise ioe
        if state in ['?', 'A', 'M', 'R', 'C'] and not force:
            return (False, state)
        # special handling for skipped files: if file exists, simply delete it
        if state == 'S':
            exists = os.path.exists(os.path.join(self.dir, n))
            self.delete_localfile(n)
            return (exists, 'S')

        self.delete_localfile(n)
        was_added = n in self.to_be_added
        if state in ('A', 'R') or state == '!' and was_added:
            self.to_be_added.remove(n)
            self.write_addlist()
        elif state == 'C':
            # don't remove "merge files" (*.r, *.mine...)
            # that's why we don't use clear_from_conflictlist
            self.in_conflict.remove(n)
            self.write_conflictlist()
        if not state in ('A', '?') and not (state == '!' and was_added):
            self.put_on_deletelist(n)
            self.write_deletelist()
        return (True, state)

    def delete_storefile(self, n):
        try: os.unlink(os.path.join(self.storedir, n))
        except: pass

    def delete_localfile(self, n):
        try: os.unlink(os.path.join(self.dir, n))
        except: pass

    def put_on_deletelist(self, n):
        if n not in self.to_be_deleted:
            self.to_be_deleted.append(n)

    def put_on_conflictlist(self, n):
        if n not in self.in_conflict:
            self.in_conflict.append(n)

    def put_on_addlist(self, n):
        if n not in self.to_be_added:
            self.to_be_added.append(n)

    def clear_from_conflictlist(self, n):
        """delete an entry from the file, and remove the file if it would be empty"""
        if n in self.in_conflict:

            filename = os.path.join(self.dir, n)
            storefilename = os.path.join(self.storedir, n)
            myfilename = os.path.join(self.dir, n + '.mine')
            if self.islinkrepair() or self.ispulled():
                upfilename = os.path.join(self.dir, n + '.new')
            else:
                upfilename = os.path.join(self.dir, n + '.r' + self.rev)

            try:
                os.unlink(myfilename)
                # the working copy may be updated, so the .r* ending may be obsolete...
                # then we don't care
                os.unlink(upfilename)
                if self.islinkrepair() or self.ispulled():
                    os.unlink(os.path.join(self.dir, n + '.old'))
            except:
                pass

            self.in_conflict.remove(n)

            self.write_conflictlist()

    # XXX: this isn't used at all
    def write_meta_mode(self):
        # XXX: the "elif" is somehow a contradiction (with current and the old implementation
        #      it's not possible to "leave" the metamode again) (except if you modify pac.meta
        #      which is really ugly:) )
        if self.meta:
            store_write_string(self.absdir, '_meta_mode', '')
        elif self.ismetamode():
            os.unlink(os.path.join(self.storedir, '_meta_mode'))

    def write_sizelimit(self):
        if self.size_limit and self.size_limit <= 0:
            try:
                os.unlink(os.path.join(self.storedir, '_size_limit'))
            except:
                pass
        else:
            store_write_string(self.absdir, '_size_limit', str(self.size_limit) + '\n')

    def write_addlist(self):
        self.__write_storelist('_to_be_added', self.to_be_added)

    def write_deletelist(self):
        self.__write_storelist('_to_be_deleted', self.to_be_deleted)

    def delete_source_file(self, n):
        """delete local a source file"""
        self.delete_localfile(n)
        self.delete_storefile(n)

    def delete_remote_source_file(self, n):
        """delete a remote source file (e.g. from the server)"""
        query = 'rev=upload'
        u = makeurl(self.apiurl, ['source', self.prjname, self.name, pathname2url(n)], query=query)
        http_DELETE(u)

    def put_source_file(self, n, tdir, copy_only=False):
        query = 'rev=repository'
        tfilename = os.path.join(tdir, n)
        shutil.copyfile(os.path.join(self.dir, n), tfilename)
        # escaping '+' in the URL path (note: not in the URL query string) is
        # only a workaround for ruby on rails, which swallows it otherwise
        if not copy_only:
            u = makeurl(self.apiurl, ['source', self.prjname, self.name, pathname2url(n)], query=query)
            http_PUT(u, file = tfilename)
        if n in self.to_be_added:
            self.to_be_added.remove(n)

    def __commit_update_store(self, tdir):
        """move files from transaction directory into the store"""
        for filename in os.listdir(tdir):
            os.rename(os.path.join(tdir, filename), os.path.join(self.storedir, filename))

    def __generate_commitlist(self, todo_send):
        root = ET.Element('directory')
        for i in sorted(todo_send.keys()):
            ET.SubElement(root, 'entry', name=i, md5=todo_send[i])
        return root

    def __send_commitlog(self, msg, local_filelist):
        """send the commitlog and the local filelist to the server"""
        query = {'cmd'    : 'commitfilelist',
                 'user'   : conf.get_apiurl_usr(self.apiurl),
                 'comment': msg}
        if self.islink() and self.isexpanded():
            query['keeplink'] = '1'
            if conf.config['linkcontrol'] or self.isfrozen():
                query['linkrev'] = self.linkinfo.srcmd5
            if self.ispulled():
                query['repairlink'] = '1'
                query['linkrev'] = self.get_pulled_srcmd5()
        if self.islinkrepair():
            query['repairlink'] = '1'
        u = makeurl(self.apiurl, ['source', self.prjname, self.name], query=query)
        f = http_POST(u, data=ET.tostring(local_filelist, encoding=ET_ENCODING))
        root = ET.parse(f).getroot()
        return root

    def __get_todo_send(self, server_filelist):
        """parse todo from a previous __send_commitlog call"""
        error = server_filelist.get('error')
        if error is None:
            return []
        elif error != 'missing':
            raise oscerr.PackageInternalError(self.prjname, self.name,
                '__get_todo_send: unexpected \'error\' attr: \'%s\'' % error)
        todo = []
        for n in server_filelist.findall('entry'):
            name = n.get('name')
            if name is None:
                raise oscerr.APIError('missing \'name\' attribute:\n%s\n' % ET.tostring(server_filelist, encoding=ET_ENCODING))
            todo.append(n.get('name'))
        return todo

    def commit(self, msg='', verbose=False, skip_local_service_run=False, can_branch=False):
        # commit only if the upstream revision is the same as the working copy's
        upstream_rev = self.latest_rev()
        if self.rev != upstream_rev:
            raise oscerr.WorkingCopyOutdated((self.absdir, self.rev, upstream_rev))

        if not skip_local_service_run:
            r = self.run_source_services(mode="trylocal", verbose=verbose)
            if r is not 0:
                # FIXME: it is better to raise this in Serviceinfo.execute with more
                # information (like which service/command failed)
                raise oscerr.ServiceRuntimeError('A service failed with error: %d' % r)

        # check if it is a link, if so, branch the package
        if self.is_link_to_different_project():
            if can_branch:
                orgprj = self.get_local_origin_project()
                print("Branching {} from {} to {}".format(self.name, orgprj, self.prjname))
                exists, targetprj, targetpkg, srcprj, srcpkg = branch_pkg(
                    self.apiurl, orgprj, self.name, target_project=self.prjname)
                # update _meta and _files to sychronize the local package
                # to the new branched one in OBS
                self.update_local_pacmeta()
                self.update_local_filesmeta()
            else:
                print("{} Not commited because is link to a different project".format(self.name))
                return 1

        if not self.todo:
            self.todo = [i for i in self.to_be_added if not i in self.filenamelist] + self.filenamelist

        pathn = getTransActPath(self.dir)

        todo_send = {}
        todo_delete = []
        real_send = []
        for filename in self.filenamelist + [i for i in self.to_be_added if not i in self.filenamelist]:
            if filename.startswith('_service:') or filename.startswith('_service_'):
                continue
            st = self.status(filename)
            if st == 'C':
                print('Please resolve all conflicts before committing using "osc resolved FILE"!')
                return 1
            elif filename in self.todo:
                if st in ('A', 'R', 'M'):
                    todo_send[filename] = dgst(os.path.join(self.absdir, filename))
                    real_send.append(filename)
                    print(statfrmt('Sending', os.path.join(pathn, filename)))
                elif st in (' ', '!', 'S'):
                    if st == '!' and filename in self.to_be_added:
                        print('file \'%s\' is marked as \'A\' but does not exist' % filename)
                        return 1
                    f = self.findfilebyname(filename)
                    if f is None:
                        raise oscerr.PackageInternalError(self.prjname, self.name,
                            'error: file \'%s\' with state \'%s\' is not known by meta' \
                            % (filename, st))
                    todo_send[filename] = f.md5
                elif st == 'D':
                    todo_delete.append(filename)
                    print(statfrmt('Deleting', os.path.join(pathn, filename)))
            elif st in ('R', 'M', 'D', ' ', '!', 'S'):
                # ignore missing new file (it's not part of the current commit)
                if st == '!' and filename in self.to_be_added:
                    continue
                f = self.findfilebyname(filename)
                if f is None:
                    raise oscerr.PackageInternalError(self.prjname, self.name,
                        'error: file \'%s\' with state \'%s\' is not known by meta' \
                        % (filename, st))
                todo_send[filename] = f.md5

        if not real_send and not todo_delete and not self.islinkrepair() and not self.ispulled():
            print('nothing to do for package %s' % self.name)
            return 1

        print('Transmitting file data', end=' ')
        filelist = self.__generate_commitlist(todo_send)
        sfilelist = self.__send_commitlog(msg, filelist)
        send = self.__get_todo_send(sfilelist)
        real_send = [i for i in real_send if not i in send]
        # abort after 3 tries
        tries = 3
        tdir = None
        try:
            tdir = os.path.join(self.storedir, '_in_commit')
            if os.path.isdir(tdir):
                shutil.rmtree(tdir)
            os.mkdir(tdir)
            while len(send) and tries:
                for filename in send[:]:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    self.put_source_file(filename, tdir)
                    send.remove(filename)
                tries -= 1
                sfilelist = self.__send_commitlog(msg, filelist)
                send = self.__get_todo_send(sfilelist)
            if len(send):
                raise oscerr.PackageInternalError(self.prjname, self.name,
                    'server does not accept filelist:\n%s\nmissing:\n%s\n' \
                    % (ET.tostring(filelist, encoding=ET_ENCODING), ET.tostring(sfilelist, encoding=ET_ENCODING)))
            # these files already exist on the server
            for filename in real_send:
                self.put_source_file(filename, tdir, copy_only=True)
            # update store with the committed files
            self.__commit_update_store(tdir)
        finally:
            if tdir is not None and os.path.isdir(tdir):
                shutil.rmtree(tdir)
        self.rev = sfilelist.get('rev')
        print()
        print('Committed revision %s.' % self.rev)

        if self.ispulled():
            os.unlink(os.path.join(self.storedir, '_pulled'))
        if self.islinkrepair():
            os.unlink(os.path.join(self.storedir, '_linkrepair'))
            self.linkrepair = False
            # XXX: mark package as invalid?
            print('The source link has been repaired. This directory can now be removed.')

        if self.islink() and self.isexpanded():
            li = Linkinfo()
            li.read(sfilelist.find('linkinfo'))
            if li.xsrcmd5 is None:
                raise oscerr.APIError('linkinfo has no xsrcmd5 attr:\n%s\n' % ET.tostring(sfilelist, encoding=ET_ENCODING))
            sfilelist = ET.fromstring(self.get_files_meta(revision=li.xsrcmd5))
        for i in sfilelist.findall('entry'):
            if i.get('name') in self.skipped:
                i.set('skipped', 'true')
        store_write_string(self.absdir, '_files', ET.tostring(sfilelist, encoding=ET_ENCODING) + '\n')
        for filename in todo_delete:
            self.to_be_deleted.remove(filename)
            self.delete_storefile(filename)
        self.write_deletelist()
        self.write_addlist()
        self.update_datastructs()

        print_request_list(self.apiurl, self.prjname, self.name)

        # FIXME: add testcases for this codepath
        sinfo = sfilelist.find('serviceinfo')
        if sinfo is not None:
            print('Waiting for server side source service run')
            u = makeurl(self.apiurl, ['source', self.prjname, self.name])
            while sinfo is not None and sinfo.get('code') == 'running':
                sys.stdout.write('.')
                sys.stdout.flush()
                # does it make sense to add some delay?
                sfilelist = ET.fromstring(http_GET(u).read())
                # if sinfo is None another commit might have occured in the "meantime"
                sinfo = sfilelist.find('serviceinfo')
            print('')
            rev = self.latest_rev()
            self.update(rev=rev)
        elif self.get_local_meta() is None:
            # if this was a newly added package there is no _meta
            # file
            self.update_local_pacmeta()

    def __write_storelist(self, name, data):
        if len(data) == 0:
            try:
                os.unlink(os.path.join(self.storedir, name))
            except:
                pass
        else:
            store_write_string(self.absdir, name, '%s\n' % '\n'.join(data))

    def write_conflictlist(self):
        self.__write_storelist('_in_conflict', self.in_conflict)

    def updatefile(self, n, revision, mtime=None):
        filename = os.path.join(self.dir, n)
        storefilename = os.path.join(self.storedir, n)
        origfile_tmp = os.path.join(self.storedir, '_in_update', '%s.copy' % n)
        origfile = os.path.join(self.storedir, '_in_update', n)
        if os.path.isfile(filename):
            shutil.copyfile(filename, origfile_tmp)
            os.rename(origfile_tmp, origfile)
        else:
            origfile = None

        get_source_file(self.apiurl, self.prjname, self.name, n, targetfilename=storefilename,
                revision=revision, progress_obj=self.progress_obj, mtime=mtime, meta=self.meta)

        shutil.copyfile(storefilename, filename)
        if mtime:
            utime(filename, (-1, mtime))
        if not origfile is None:
            os.unlink(origfile)

    def mergefile(self, n, revision, mtime=None):
        filename = os.path.join(self.dir, n)
        storefilename = os.path.join(self.storedir, n)
        myfilename = os.path.join(self.dir, n + '.mine')
        upfilename = os.path.join(self.dir, n + '.r' + self.rev)
        origfile_tmp = os.path.join(self.storedir, '_in_update', '%s.copy' % n)
        origfile = os.path.join(self.storedir, '_in_update', n)
        shutil.copyfile(filename, origfile_tmp)
        os.rename(origfile_tmp, origfile)
        os.rename(filename, myfilename)

        get_source_file(self.apiurl, self.prjname, self.name, n,
                        revision=revision, targetfilename=upfilename,
                        progress_obj=self.progress_obj, mtime=mtime, meta=self.meta)

        if binary_file(myfilename) or binary_file(upfilename):
            # don't try merging
            shutil.copyfile(upfilename, filename)
            shutil.copyfile(upfilename, storefilename)
            os.unlink(origfile)
            self.in_conflict.append(n)
            self.write_conflictlist()
            return 'C'
        else:
            # try merging
            # diff3 OPTIONS... MINE OLDER YOURS
            merge_cmd = 'diff3 -m -E %s %s %s > %s' % (myfilename, storefilename, upfilename, filename)
            ret = run_external(merge_cmd, shell=True)

            #   "An exit status of 0 means `diff3' was successful, 1 means some
            #   conflicts were found, and 2 means trouble."
            if ret == 0:
                # merge was successful... clean up
                shutil.copyfile(upfilename, storefilename)
                os.unlink(upfilename)
                os.unlink(myfilename)
                os.unlink(origfile)
                return 'G'
            elif ret == 1:
                # unsuccessful merge
                shutil.copyfile(upfilename, storefilename)
                os.unlink(origfile)
                self.in_conflict.append(n)
                self.write_conflictlist()
                return 'C'
            else:
                raise oscerr.ExtRuntimeError('diff3 failed with exit code: %s' % ret, merge_cmd)

    def update_local_filesmeta(self, revision=None):
        """
        Update the local _files file in the store.
        It is replaced with the version pulled from upstream.
        """
        meta = self.get_files_meta(revision=revision)
        store_write_string(self.absdir, '_files', meta + '\n')

    def get_files_meta(self, revision='latest', skip_service=True):
        fm = show_files_meta(self.apiurl, self.prjname, self.name, revision=revision, meta=self.meta)
        # look for "too large" files according to size limit and mark them
        root = ET.fromstring(fm)
        for e in root.findall('entry'):
            size = e.get('size')
            if size and self.size_limit and int(size) > self.size_limit \
                or skip_service and (e.get('name').startswith('_service:') or e.get('name').startswith('_service_')):
                e.set('skipped', 'true')
        return ET.tostring(root, encoding=ET_ENCODING)

    def get_local_meta(self):
        """Get the local _meta file for the package."""
        meta = store_read_file(self.absdir, '_meta')
        return meta

    def get_local_origin_project(self):
        """Get the originproject from the _meta file."""
        # if the wc was checked out via some old osc version
        # there might be no meta file: in this case we assume
        # that the origin project is equal to the wc's project
        meta = self.get_local_meta()
        if meta is None:
            return self.prjname
        root = ET.fromstring(meta)
        return root.get('project')

    def is_link_to_different_project(self):
        """Check if the package is a link to a different project."""
        orgprj = self.get_local_origin_project()
        return self.prjname != orgprj

    def update_datastructs(self):
        """
        Update the internal data structures if the local _files
        file has changed (e.g. update_local_filesmeta() has been
        called).
        """
        import fnmatch
        files_tree = read_filemeta(self.dir)
        files_tree_root = files_tree.getroot()

        self.rev = files_tree_root.get('rev')
        self.srcmd5 = files_tree_root.get('srcmd5')

        self.linkinfo = Linkinfo()
        self.linkinfo.read(files_tree_root.find('linkinfo'))

        self.filenamelist = []
        self.filelist = []
        self.skipped = []
        for node in files_tree_root.findall('entry'):
            try:
                f = File(node.get('name'),
                         node.get('md5'),
                         int(node.get('size')),
                         int(node.get('mtime')))
                if node.get('skipped'):
                    self.skipped.append(f.name)
                    f.skipped = True
            except:
                # okay, a very old version of _files, which didn't contain any metadata yet...
                f = File(node.get('name'), '', 0, 0)
            self.filelist.append(f)
            self.filenamelist.append(f.name)

        self.to_be_added = read_tobeadded(self.absdir)
        self.to_be_deleted = read_tobedeleted(self.absdir)
        self.in_conflict = read_inconflict(self.absdir)
        self.linkrepair = os.path.isfile(os.path.join(self.storedir, '_linkrepair'))
        self.size_limit = read_sizelimit(self.dir)
        self.meta = self.ismetamode()

        # gather unversioned files, but ignore some stuff
        self.excluded = []
        for i in os.listdir(self.dir):
            for j in conf.config['exclude_glob']:
                if fnmatch.fnmatch(i, j):
                    self.excluded.append(i)
                    break
        self.filenamelist_unvers = [ i for i in os.listdir(self.dir)
                                     if i not in self.excluded
                                     if i not in self.filenamelist ]

    def islink(self):
        """tells us if the package is a link (has 'linkinfo').
        A package with linkinfo is a package which links to another package.
        Returns True if the package is a link, otherwise False."""
        return self.linkinfo.islink()

    def isexpanded(self):
        """tells us if the package is a link which is expanded.
        Returns True if the package is expanded, otherwise False."""
        return self.linkinfo.isexpanded()

    def islinkrepair(self):
        """tells us if we are repairing a broken source link."""
        return self.linkrepair

    def ispulled(self):
        """tells us if we have pulled a link."""
        return os.path.isfile(os.path.join(self.storedir, '_pulled'))

    def isfrozen(self):
        """tells us if the link is frozen."""
        return os.path.isfile(os.path.join(self.storedir, '_frozenlink'))

    def ismetamode(self):
        """tells us if the package is in meta mode"""
        return os.path.isfile(os.path.join(self.storedir, '_meta_mode'))

    def get_pulled_srcmd5(self):
        pulledrev = None
        for line in open(os.path.join(self.storedir, '_pulled'), 'r'):
            pulledrev = line.strip()
        return pulledrev

    def haslinkerror(self):
        """
        Returns True if the link is broken otherwise False.
        If the package is not a link it returns False.
        """
        return self.linkinfo.haserror()

    def linkerror(self):
        """
        Returns an error message if the link is broken otherwise None.
        If the package is not a link it returns None.
        """
        return self.linkinfo.error

    def update_local_pacmeta(self):
        """
        Update the local _meta file in the store.
        It is replaced with the version pulled from upstream.
        """
        meta = show_package_meta(self.apiurl, self.prjname, self.name)
        if meta != "":
            # is empty for _project for example
            meta = ''.join(meta)
            store_write_string(self.absdir, '_meta', meta + '\n')

    def findfilebyname(self, n):
        for i in self.filelist:
            if i.name == n:
                return i

    def get_status(self, excluded=False, *exclude_states):
        global store
        todo = self.todo
        if not todo:
            todo = self.filenamelist + self.to_be_added + \
                [i for i in self.filenamelist_unvers if not os.path.isdir(os.path.join(self.absdir, i))]
            if excluded:
                todo.extend([i for i in self.excluded if i != store])
            todo = set(todo)
        res = []
        for fname in sorted(todo):
            st = self.status(fname)
            if not st in exclude_states:
                res.append((st, fname))
        return res

    def status(self, n):
        """
        status can be:

         file  storefile  file present  STATUS
        exists  exists      in _files

          x       -            -        'A' and listed in _to_be_added
          x       x            -        'R' and listed in _to_be_added
          x       x            x        ' ' if digest differs: 'M'
                                            and if in conflicts file: 'C'
          x       -            -        '?'
          -       x            x        'D' and listed in _to_be_deleted
          x       x            x        'D' and listed in _to_be_deleted (e.g. if deleted file was modified)
          x       x            x        'C' and listed in _in_conflict
          x       -            x        'S' and listed in self.skipped
          -       -            x        'S' and listed in self.skipped
          -       x            x        '!'
          -       -            -        NOT DEFINED

        """

        known_by_meta = False
        exists = False
        exists_in_store = False
        if n in self.filenamelist:
            known_by_meta = True
        if os.path.exists(os.path.join(self.absdir, n)):
            exists = True
        if os.path.exists(os.path.join(self.storedir, n)):
            exists_in_store = True

        if n in self.to_be_deleted:
            state = 'D'
        elif n in self.in_conflict:
            state = 'C'
        elif n in self.skipped:
            state = 'S'
        elif n in self.to_be_added and exists and exists_in_store:
            state = 'R'
        elif n in self.to_be_added and exists:
            state = 'A'
        elif exists and exists_in_store and known_by_meta:
            if dgst(os.path.join(self.absdir, n)) != self.findfilebyname(n).md5:
                state = 'M'
            else:
                state = ' '
        elif n in self.to_be_added and not exists:
            state = '!'
        elif not exists and exists_in_store and known_by_meta and not n in self.to_be_deleted:
            state = '!'
        elif exists and not exists_in_store and not known_by_meta:
            state = '?'
        elif not exists_in_store and known_by_meta:
            # XXX: this codepath shouldn't be reached (we restore the storefile
            #      in update_datastructs)
            raise oscerr.PackageInternalError(self.prjname, self.name,
                'error: file \'%s\' is known by meta but no storefile exists.\n'
                'This might be caused by an old wc format. Please backup your current\n'
                'wc and checkout the package again. Afterwards copy all files (except the\n'
                '.osc/ dir) into the new package wc.' % n)
        else:
            # this case shouldn't happen (except there was a typo in the filename etc.)
            raise oscerr.OscIOError(None, 'osc: \'%s\' is not under version control' % n)

        return state

    def get_diff(self, revision=None, ignoreUnversioned=False):
        import tempfile
        diff_hdr = 'Index: %s\n'
        diff_hdr += '===================================================================\n'
        kept = []
        added = []
        deleted = []
        def diff_add_delete(fname, add, revision):
            diff = []
            diff.append(diff_hdr % fname)
            tmpfile = None
            origname = fname
            if add:
                diff.append('--- %s\t(revision 0)\n' % fname)
                rev = 'revision 0'
                if revision and not fname in self.to_be_added:
                    rev = 'working copy'
                diff.append('+++ %s\t(%s)\n' % (fname, rev))
                fname = os.path.join(self.absdir, fname)
            else:
                diff.append('--- %s\t(revision %s)\n' % (fname, revision or self.rev))
                diff.append('+++ %s\t(working copy)\n' % fname)
                fname = os.path.join(self.storedir, fname)
               
            try:
                if revision is not None and not add:
                    (fd, tmpfile) = tempfile.mkstemp(prefix='osc_diff')
                    get_source_file(self.apiurl, self.prjname, self.name, origname, tmpfile, revision)
                    fname = tmpfile
                if binary_file(fname):
                    what = 'added'
                    if not add:
                        what = 'deleted'
                    diff = diff[:1]
                    diff.append('Binary file \'%s\' %s.\n' % (origname, what))
                    return diff
                tmpl = '+%s'
                ltmpl = '@@ -0,0 +1,%d @@\n'
                if not add:
                    tmpl = '-%s'
                    ltmpl = '@@ -1,%d +0,0 @@\n'
                lines = [tmpl % i for i in open(fname, 'r').readlines()]
                if len(lines):
                    diff.append(ltmpl % len(lines))
                    if not lines[-1].endswith('\n'):
                        lines.append('\n\\ No newline at end of file\n')
                diff.extend(lines)
            finally:
                if tmpfile is not None:
                    os.close(fd)
                    os.unlink(tmpfile)
            return diff

        if revision is None:
            todo = self.todo or [i for i in self.filenamelist if not i in self.to_be_added]+self.to_be_added
            for fname in todo:
                if fname in self.to_be_added and self.status(fname) == 'A':
                    added.append(fname)
                elif fname in self.to_be_deleted:
                    deleted.append(fname)
                elif fname in self.filenamelist:
                    kept.append(self.findfilebyname(fname))
                elif fname in self.to_be_added and self.status(fname) == '!':
                    raise oscerr.OscIOError(None, 'file \'%s\' is marked as \'A\' but does not exist\n'\
                        '(either add the missing file or revert it)' % fname)
                elif not ignoreUnversioned:
                    raise oscerr.OscIOError(None, 'file \'%s\' is not under version control' % fname)
        else:
            fm = self.get_files_meta(revision=revision)
            root = ET.fromstring(fm)
            rfiles = self.__get_files(root)
            # swap added and deleted
            kept, deleted, added, services = self.__get_rev_changes(rfiles)
            added = [f.name for f in added]
            added.extend([f for f in self.to_be_added if not f in kept])
            deleted = [f.name for f in deleted]
            deleted.extend(self.to_be_deleted)
            for f in added[:]:
                if f in deleted:
                    added.remove(f)
                    deleted.remove(f)
#        print kept, added, deleted
        for f in kept:
            state = self.status(f.name)
            if state in ('S', '?', '!'):
                continue
            elif state == ' ' and revision is None:
                continue
            elif revision and self.findfilebyname(f.name).md5 == f.md5 and state != 'M':
                continue
            yield [diff_hdr % f.name]
            if revision is None:
                yield get_source_file_diff(self.absdir, f.name, self.rev)
            else:
                tmpfile = None
                diff = []
                try:
                    (fd, tmpfile) = tempfile.mkstemp(prefix='osc_diff')
                    get_source_file(self.apiurl, self.prjname, self.name, f.name, tmpfile, revision)
                    diff = get_source_file_diff(self.absdir, f.name, revision,
                        os.path.basename(tmpfile), os.path.dirname(tmpfile), f.name)
                finally:
                    if tmpfile is not None:
                        os.close(fd)
                        os.unlink(tmpfile)
                yield diff

        for f in added:
            yield diff_add_delete(f, True, revision)
        for f in deleted:
            yield diff_add_delete(f, False, revision)

    def merge(self, otherpac):
        self.todo += otherpac.todo

    def __str__(self):
        r = """
name: %s
prjname: %s
workingdir: %s
localfilelist: %s
linkinfo: %s
rev: %s
'todo' files: %s
""" % (self.name,
        self.prjname,
        self.dir,
        '\n               '.join(self.filenamelist),
        self.linkinfo,
        self.rev,
        self.todo)

        return r


    def read_meta_from_spec(self, spec = None):
        import glob
        if spec:
            specfile = spec
        else:
            # scan for spec files
            speclist = glob.glob(os.path.join(self.dir, '*.spec'))
            if len(speclist) == 1:
                specfile = speclist[0]
            elif len(speclist) > 1:
                print('the following specfiles were found:')
                for filename in speclist:
                    print(filename)
                print('please specify one with --specfile')
                sys.exit(1)
            else:
                print('no specfile was found - please specify one ' \
                      'with --specfile')
                sys.exit(1)

        data = read_meta_from_spec(specfile, 'Summary', 'Url', '%description')
        self.summary = data.get('Summary', '')
        self.url = data.get('Url', '')
        self.descr = data.get('%description', '')


    def update_package_meta(self, force=False):
        """
        for the updatepacmetafromspec subcommand
            argument force supress the confirm question
        """

        m = ''.join(show_package_meta(self.apiurl, self.prjname, self.name))

        root = ET.fromstring(m)
        root.find('title').text = self.summary
        root.find('description').text = ''.join(self.descr)
        url = root.find('url')
        if url == None:
            url = ET.SubElement(root, 'url')
        url.text = self.url

        u = makeurl(self.apiurl, ['source', self.prjname, self.name, '_meta'])
        mf = metafile(u, ET.tostring(root, encoding=ET_ENCODING))

        if not force:
            print('*' * 36, 'old', '*' * 36)
            print(m)
            print('*' * 36, 'new', '*' * 36)
            print(ET.tostring(root, encoding=ET_ENCODING))
            print('*' * 72)
            repl = raw_input('Write? (y/N/e) ')
        else:
            repl = 'y'

        if repl == 'y':
            mf.sync()
        elif repl == 'e':
            mf.edit()

        mf.discard()

    def mark_frozen(self):
        store_write_string(self.absdir, '_frozenlink', '')
        print()
        print("The link in this package is currently broken. Checking")
        print("out the last working version instead; please use 'osc pull'")
        print("to merge the conflicts.")
        print()

    def unmark_frozen(self):
        if os.path.exists(os.path.join(self.storedir, '_frozenlink')):
            os.unlink(os.path.join(self.storedir, '_frozenlink'))

    def latest_rev(self, include_service_files=False, expand=False):
        # if expand is True the xsrcmd5 will be returned (even if the wc is unexpanded)
        if self.islinkrepair():
            upstream_rev = show_upstream_xsrcmd5(self.apiurl, self.prjname, self.name, linkrepair=1, meta=self.meta, include_service_files=include_service_files)
        elif self.islink() and (self.isexpanded() or expand):
            if self.isfrozen() or self.ispulled():
                upstream_rev = show_upstream_xsrcmd5(self.apiurl, self.prjname, self.name, linkrev=self.linkinfo.srcmd5, meta=self.meta, include_service_files=include_service_files)
            else:
                try:
                    upstream_rev = show_upstream_xsrcmd5(self.apiurl, self.prjname, self.name, meta=self.meta, include_service_files=include_service_files)
                except:
                    try:
                        upstream_rev = show_upstream_xsrcmd5(self.apiurl, self.prjname, self.name, linkrev=self.linkinfo.srcmd5, meta=self.meta, include_service_files=include_service_files)
                    except:
                        upstream_rev = show_upstream_xsrcmd5(self.apiurl, self.prjname, self.name, linkrev="base", meta=self.meta, include_service_files=include_service_files)
                    self.mark_frozen()
        else:
            upstream_rev = show_upstream_rev(self.apiurl, self.prjname, self.name, meta=self.meta, include_service_files=include_service_files)
        return upstream_rev

    def __get_files(self, fmeta_root):
        f = []
        if fmeta_root.get('rev') is None and len(fmeta_root.findall('entry')) > 0:
            raise oscerr.APIError('missing rev attribute in _files:\n%s' % ''.join(ET.tostring(fmeta_root, encoding=ET_ENCODING)))
        for i in fmeta_root.findall('entry'):
            skipped = i.get('skipped') is not None
            f.append(File(i.get('name'), i.get('md5'),
                     int(i.get('size')), int(i.get('mtime')), skipped))
        return f

    def __get_rev_changes(self, revfiles):
        kept = []
        added = []
        deleted = []
        services = []
        revfilenames = []
        for f in revfiles:
            revfilenames.append(f.name)
            # treat skipped like deleted files
            if f.skipped:
                if f.name.startswith('_service:'):
                    services.append(f)
                else:
                    deleted.append(f)
                continue
            # treat skipped like added files
            # problem: this overwrites existing files during the update
            # (because skipped files aren't in self.filenamelist_unvers)
            if f.name in self.filenamelist and not f.name in self.skipped:
                kept.append(f)
            else:
                added.append(f)
        for f in self.filelist:
            if not f.name in revfilenames:
                deleted.append(f)

        return kept, added, deleted, services

    def update(self, rev = None, service_files = False, size_limit = None):
        import tempfile
        rfiles = []
        # size_limit is only temporary for this update
        old_size_limit = self.size_limit
        if not size_limit is None:
            self.size_limit = int(size_limit)
        if os.path.isfile(os.path.join(self.storedir, '_in_update', '_files')):
            print('resuming broken update...')
            root = ET.parse(os.path.join(self.storedir, '_in_update', '_files')).getroot()
            rfiles = self.__get_files(root)
            kept, added, deleted, services = self.__get_rev_changes(rfiles)
            # check if we aborted in the middle of a file update
            broken_file = os.listdir(os.path.join(self.storedir, '_in_update'))
            broken_file.remove('_files')
            if len(broken_file) == 1:
                origfile = os.path.join(self.storedir, '_in_update', broken_file[0])
                wcfile = os.path.join(self.absdir, broken_file[0])
                origfile_md5 = dgst(origfile)
                origfile_meta = self.findfilebyname(broken_file[0])
                if origfile.endswith('.copy'):
                    # ok it seems we aborted at some point during the copy process
                    # (copy process == copy wcfile to the _in_update dir). remove file+continue
                    os.unlink(origfile)
                elif self.findfilebyname(broken_file[0]) is None:
                    # should we remove this file from _in_update? if we don't
                    # the user has no chance to continue without removing the file manually
                    raise oscerr.PackageInternalError(self.prjname, self.name,
                        '\'%s\' is not known by meta but exists in \'_in_update\' dir')
                elif os.path.isfile(wcfile) and dgst(wcfile) != origfile_md5:
                    (fd, tmpfile) = tempfile.mkstemp(dir=self.absdir, prefix=broken_file[0]+'.')
                    os.close(fd)
                    os.rename(wcfile, tmpfile)
                    os.rename(origfile, wcfile)
                    print('warning: it seems you modified \'%s\' after the broken ' \
                          'update. Restored original file and saved modified version ' \
                          'to \'%s\'.' % (wcfile, tmpfile))
                elif not os.path.isfile(wcfile):
                    # this is strange... because it existed before the update. restore it
                    os.rename(origfile, wcfile)
                else:
                    # everything seems to be ok
                    os.unlink(origfile)
            elif len(broken_file) > 1:
                raise oscerr.PackageInternalError(self.prjname, self.name, 'too many files in \'_in_update\' dir')
            tmp = rfiles[:]
            for f in tmp:
                if os.path.exists(os.path.join(self.storedir, f.name)):
                    if dgst(os.path.join(self.storedir, f.name)) == f.md5:
                        if f in kept:
                            kept.remove(f)
                        elif f in added:
                            added.remove(f)
                        # this can't happen
                        elif f in deleted:
                            deleted.remove(f)
            if not service_files:
                services = []
            self.__update(kept, added, deleted, services, ET.tostring(root, encoding=ET_ENCODING), root.get('rev'))
            os.unlink(os.path.join(self.storedir, '_in_update', '_files'))
            os.rmdir(os.path.join(self.storedir, '_in_update'))
        # ok everything is ok (hopefully)...
        fm = self.get_files_meta(revision=rev)
        root = ET.fromstring(fm)
        rfiles = self.__get_files(root)
        store_write_string(self.absdir, '_files', fm + '\n', subdir='_in_update')
        kept, added, deleted, services = self.__get_rev_changes(rfiles)
        if not service_files:
            services = []
        self.__update(kept, added, deleted, services, fm, root.get('rev'))
        os.unlink(os.path.join(self.storedir, '_in_update', '_files'))
        if os.path.isdir(os.path.join(self.storedir, '_in_update')):
            os.rmdir(os.path.join(self.storedir, '_in_update'))
        self.size_limit = old_size_limit

    def __update(self, kept, added, deleted, services, fm, rev):
        pathn = getTransActPath(self.dir)
        # check for conflicts with existing files
        for f in added:
            if f.name in self.filenamelist_unvers:
                raise oscerr.PackageFileConflict(self.prjname, self.name, f.name,
                    'failed to add file \'%s\' file/dir with the same name already exists' % f.name)
        # ok, the update can't fail due to existing files
        for f in added:
            self.updatefile(f.name, rev, f.mtime)
            print(statfrmt('A', os.path.join(pathn, f.name)))
        for f in deleted:
            # if the storefile doesn't exist we're resuming an aborted update:
            # the file was already deleted but we cannot know this
            # OR we're processing a _service: file (simply keep the file)
            if os.path.isfile(os.path.join(self.storedir, f.name)) and self.status(f.name) != 'M':
#            if self.status(f.name) != 'M':
                self.delete_localfile(f.name)
            self.delete_storefile(f.name)
            print(statfrmt('D', os.path.join(pathn, f.name)))
            if f.name in self.to_be_deleted:
                self.to_be_deleted.remove(f.name)
                self.write_deletelist()

        for f in kept:
            state = self.status(f.name)
#            print f.name, state
            if state == 'M' and self.findfilebyname(f.name).md5 == f.md5:
                # remote file didn't change
                pass
            elif state == 'M':
                # try to merge changes
                merge_status = self.mergefile(f.name, rev, f.mtime)
                print(statfrmt(merge_status, os.path.join(pathn, f.name)))
            elif state == '!':
                self.updatefile(f.name, rev, f.mtime)
                print('Restored \'%s\'' % os.path.join(pathn, f.name))
            elif state == 'C':
                get_source_file(self.apiurl, self.prjname, self.name, f.name,
                    targetfilename=os.path.join(self.storedir, f.name), revision=rev,
                    progress_obj=self.progress_obj, mtime=f.mtime, meta=self.meta)
                print('skipping \'%s\' (this is due to conflicts)' % f.name)
            elif state == 'D' and self.findfilebyname(f.name).md5 != f.md5:
                # XXX: in the worst case we might end up with f.name being
                # in _to_be_deleted and in _in_conflict... this needs to be checked
                if os.path.exists(os.path.join(self.absdir, f.name)):
                    merge_status = self.mergefile(f.name, rev, f.mtime)
                    print(statfrmt(merge_status, os.path.join(pathn, f.name)))
                    if merge_status == 'C':
                        # state changes from delete to conflict
                        self.to_be_deleted.remove(f.name)
                        self.write_deletelist()
                else:
                    # XXX: we cannot recover this case because we've no file
                    # to backup
                    self.updatefile(f.name, rev, f.mtime)
                    print(statfrmt('U', os.path.join(pathn, f.name)))
            elif state == ' ' and self.findfilebyname(f.name).md5 != f.md5:
                self.updatefile(f.name, rev, f.mtime)
                print(statfrmt('U', os.path.join(pathn, f.name)))

        # checkout service files
        for f in services:
            get_source_file(self.apiurl, self.prjname, self.name, f.name,
                targetfilename=os.path.join(self.absdir, f.name), revision=rev,
                progress_obj=self.progress_obj, mtime=f.mtime, meta=self.meta)
            print(statfrmt('A', os.path.join(pathn, f.name)))
        store_write_string(self.absdir, '_files', fm + '\n')
        if not self.meta:
            self.update_local_pacmeta()
        self.update_datastructs()

        print('At revision %s.' % self.rev)

    def run_source_services(self, mode=None, singleservice=None, verbose=None):
        if self.name.startswith("_"):
            return 0
        curdir = os.getcwd()
        os.chdir(self.absdir) # e.g. /usr/lib/obs/service/verify_file fails if not inside the project dir.
        si = Serviceinfo()
        if os.path.exists('_service'):
            if self.filenamelist.count('_service') or self.filenamelist_unvers.count('_service'):
                service = ET.parse(os.path.join(self.absdir, '_service')).getroot()
                si.read(service)
        si.getProjectGlobalServices(self.apiurl, self.prjname, self.name)
        r = si.execute(self.absdir, mode, singleservice, verbose)
        os.chdir(curdir)
        return r

    def revert(self, filename):
        if not filename in self.filenamelist and not filename in self.to_be_added:
            raise oscerr.OscIOError(None, 'file \'%s\' is not under version control' % filename)
        elif filename in self.skipped:
            raise oscerr.OscIOError(None, 'file \'%s\' is marked as skipped and cannot be reverted' % filename)
        if filename in self.filenamelist and not os.path.exists(os.path.join(self.storedir, filename)):
            raise oscerr.PackageInternalError('file \'%s\' is listed in filenamelist but no storefile exists' % filename)
        state = self.status(filename)
        if not (state == 'A' or state == '!' and filename in self.to_be_added):
            shutil.copyfile(os.path.join(self.storedir, filename), os.path.join(self.absdir, filename))
        if state == 'D':
            self.to_be_deleted.remove(filename)
            self.write_deletelist()
        elif state == 'C':
            self.clear_from_conflictlist(filename)
        elif state in ('A', 'R') or state == '!' and filename in self.to_be_added:
            self.to_be_added.remove(filename)
            self.write_addlist()

    @staticmethod
    def init_package(apiurl, project, package, dir, size_limit=None, meta=False, progress_obj=None):
        global store

        if not os.path.exists(dir):
            os.mkdir(dir)
        elif not os.path.isdir(dir):
            raise oscerr.OscIOError(None, 'error: \'%s\' is no directory' % dir)
        if os.path.exists(os.path.join(dir, store)):
            raise oscerr.OscIOError(None, 'error: \'%s\' is already an initialized osc working copy' % dir)
        else:
            os.mkdir(os.path.join(dir, store))
        store_write_project(dir, project)
        store_write_string(dir, '_package', package + '\n')
        store_write_apiurl(dir, apiurl)
        if meta:
            store_write_string(dir, '_meta_mode', '')
        if size_limit:
            store_write_string(dir, '_size_limit', str(size_limit) + '\n')
        store_write_string(dir, '_files', '<directory />' + '\n')
        store_write_string(dir, '_osclib_version', __store_version__ + '\n')
        return Package(dir, progress_obj=progress_obj, size_limit=size_limit)


class AbstractState:
    """
    Base class which represents state-like objects (<review />, <state />).
    """
    def __init__(self, tag):
        self.__tag = tag

    def get_node_attrs(self):
        """return attributes for the tag/element"""
        raise NotImplementedError()

    def get_node_name(self):
        """return tag/element name"""
        return self.__tag

    def get_comment(self):
        """return data from <comment /> tag"""
        raise NotImplementedError()

    def to_xml(self):
        """serialize object to XML"""
        root = ET.Element(self.get_node_name())
        for attr in self.get_node_attrs():
            val = getattr(self, attr)
            if not val is None:
                root.set(attr, val)
        if self.get_comment():
            ET.SubElement(root, 'comment').text = self.get_comment()
        return root

    def to_str(self):
        """return "pretty" XML data"""
        root = self.to_xml()
        xmlindent(root)
        return ET.tostring(root, encoding=ET_ENCODING)


class ReviewState(AbstractState):
    """Represents the review state in a request"""
    def __init__(self, review_node):
        if not review_node.get('state'):
            raise oscerr.APIError('invalid review node (state attr expected): %s' % \
                ET.tostring(review_node, encoding=ET_ENCODING))
        AbstractState.__init__(self, review_node.tag)
        self.state = review_node.get('state')
        self.by_user = review_node.get('by_user')
        self.by_group = review_node.get('by_group')
        self.by_project = review_node.get('by_project')
        self.by_package = review_node.get('by_package')
        self.who = review_node.get('who')
        self.when = review_node.get('when')
        self.comment = ''
        if not review_node.find('comment') is None and \
            review_node.find('comment').text:
            self.comment = review_node.find('comment').text.strip()

    def get_node_attrs(self):
        return ('state', 'by_user', 'by_group', 'by_project', 'by_package', 'who', 'when')

    def get_comment(self):
        return self.comment


class RequestState(AbstractState):
    """Represents the state of a request"""
    def __init__(self, state_node):
        if not state_node.get('name'):
            raise oscerr.APIError('invalid request state node (name attr expected): %s' % \
                ET.tostring(state_node, encoding=ET_ENCODING))
        AbstractState.__init__(self, state_node.tag)
        self.name = state_node.get('name')
        self.who = state_node.get('who')
        self.when = state_node.get('when')
        self.comment = ''
        if not state_node.find('comment') is None and \
            state_node.find('comment').text:
            self.comment = state_node.find('comment').text.strip()

    def get_node_attrs(self):
        return ('name', 'who', 'when')

    def get_comment(self):
        return self.comment


class Action:
    """
    Represents a <action /> element of a Request.
    This class is quite common so that it can be used for all different
    action types. Note: instances only provide attributes for their specific
    type.
    Examples:
      r = Action('set_bugowner', tgt_project='foo', person_name='buguser')
      # available attributes: r.type (== 'set_bugowner'), r.tgt_project (== 'foo'), r.tgt_package (== None)
      r.to_str() ->
      <action type="set_bugowner">
        <target project="foo" />
        <person name="buguser" />
      </action>
      ##
      r = Action('delete', tgt_project='foo', tgt_package='bar')
      # available attributes: r.type (== 'delete'), r.tgt_project (== 'foo'), r.tgt_package (=='bar')
      r.to_str() ->
      <action type="delete">
        <target package="bar" project="foo" />
      </action>
    """

    # allowed types + the corresponding (allowed) attributes
    type_args = {'submit': ('src_project', 'src_package', 'src_rev', 'tgt_project', 'tgt_package', 'opt_sourceupdate',
                            'acceptinfo_rev', 'acceptinfo_srcmd5', 'acceptinfo_xsrcmd5', 'acceptinfo_osrcmd5',
                            'acceptinfo_oxsrcmd5', 'opt_updatelink'),
        'add_role': ('tgt_project', 'tgt_package', 'person_name', 'person_role', 'group_name', 'group_role'),
        'set_bugowner': ('tgt_project', 'tgt_package', 'person_name', 'group_name'),
        'maintenance_release': ('src_project', 'src_package', 'src_rev', 'tgt_project', 'tgt_package', 'person_name',
                            'acceptinfo_rev', 'acceptinfo_srcmd5', 'acceptinfo_xsrcmd5', 'acceptinfo_osrcmd5',
                            'acceptinfo_oxsrcmd5'),
        'maintenance_incident': ('src_project', 'src_package', 'src_rev', 'tgt_project', 'tgt_releaseproject', 'person_name', 'opt_sourceupdate'),
        'delete': ('tgt_project', 'tgt_package', 'tgt_repository'),
        'change_devel': ('src_project', 'src_package', 'tgt_project', 'tgt_package'),
        'group': ('grouped_id', )}
    # attribute prefix to element name map (only needed for abbreviated attributes)
    prefix_to_elm = {'src': 'source', 'tgt': 'target', 'opt': 'options'}

    def __init__(self, type, **kwargs):
        if not type in Action.type_args.keys():
            raise oscerr.WrongArgs('invalid action type: \'%s\'' % type)
        self.type = type
        for i in kwargs.keys():
            if not i in Action.type_args[type]:
                raise oscerr.WrongArgs('invalid argument: \'%s\'' % i)
        # set all type specific attributes
        for i in Action.type_args[type]:
            setattr(self, i, kwargs.get(i))

    def to_xml(self):
        """
        Serialize object to XML.
        The xml tag names and attributes are constructed from the instance's attributes.
        Example:
          self.group_name  -> tag name is "group", attribute name is "name"
          self.src_project -> tag name is "source" (translated via prefix_to_elm dict),
                              attribute name is "project"
        Attributes prefixed with "opt_" need a special handling, the resulting xml should
        look like this: opt_updatelink -> <options><updatelink>value</updatelink></options>.
        Attributes which are "None" will be skipped.
        """
        root = ET.Element('action', type=self.type)
        for i in Action.type_args[self.type]:
            prefix, attr = i.split('_', 1)
            vals = getattr(self, i)
            # single, plain elements are _not_ stored in a list
            plain = False
            if vals is None:
                continue
            elif not hasattr(vals, 'append'):
                vals = [vals]
                plain = True
            for val in vals:
                elm = root.find(Action.prefix_to_elm.get(prefix, prefix))
                if elm is None or not plain:
                    elm = ET.Element(Action.prefix_to_elm.get(prefix, prefix))
                    root.append(elm)
                if prefix == 'opt':
                    ET.SubElement(elm, attr).text = val
                else:
                    elm.set(attr, val)
        return root

    def to_str(self):
        """return "pretty" XML data"""
        root = self.to_xml()
        xmlindent(root)
        return ET.tostring(root, encoding=ET_ENCODING)

    @staticmethod
    def from_xml(action_node):
        """create action from XML"""
        if action_node is None or \
            not action_node.get('type') in Action.type_args.keys() or \
            not action_node.tag in ('action', 'submit'):
            raise oscerr.WrongArgs('invalid argument')
        elm_to_prefix = dict([(i[1], i[0]) for i in Action.prefix_to_elm.items()])
        kwargs = {}
        for node in action_node:
            prefix = elm_to_prefix.get(node.tag, node.tag)
            if prefix == 'opt':
                data = [('opt_%s' % opt.tag, opt.text.strip()) for opt in node if opt.text]
            else:
                data = [('%s_%s' % (prefix, k), v) for k, v in node.items()]
            # it would be easier to store everything in a list but in
            # this case we would lose some "structure" (see to_xml)
            for k, v in data:
                if k in kwargs:
                    l = kwargs[k]
                    if not hasattr(l, 'append'):
                        l = [l]
                        kwargs[k] = l
                    l.append(v)
                else:
                    kwargs[k] = v
        return Action(action_node.get('type'), **kwargs)


class Request:
    """Represents a request (<request />)"""

    def __init__(self):
        self._init_attributes()

    def _init_attributes(self):
        """initialize attributes with default values"""
        self.reqid = None
        self.title = ''
        self.description = ''
        self.state = None
        self.accept_at = None
        self.actions = []
        self.statehistory = []
        self.reviews = []

    def read(self, root):
        """read in a request"""
        self._init_attributes()
        if not root.get('id'):
            raise oscerr.APIError('invalid request: %s\n' % ET.tostring(root, encoding=ET_ENCODING))
        self.reqid = root.get('id')
        if root.find('state') is None:
            raise oscerr.APIError('invalid request (state expected): %s\n' % ET.tostring(root, encoding=ET_ENCODING))
        self.state = RequestState(root.find('state'))
        action_nodes = root.findall('action')
        if not action_nodes:
            # check for old-style requests
            for i in root.findall('submit'):
                i.set('type', 'submit')
                action_nodes.append(i)
        for action in action_nodes:
            self.actions.append(Action.from_xml(action))
        for review in root.findall('review'):
            self.reviews.append(ReviewState(review))
        for hist_state in root.findall('history'):
            self.statehistory.append(RequestState(hist_state))
        if not root.find('accept_at') is None and root.find('accept_at').text:
            self.accept_at = root.find('accept_at').text.strip()
        if not root.find('title') is None:
            self.title = root.find('title').text.strip()
        if not root.find('description') is None and root.find('description').text:
            self.description = root.find('description').text.strip()

    def add_action(self, type, **kwargs):
        """add a new action to the request"""
        self.actions.append(Action(type, **kwargs))

    def get_actions(self, *types):
        """
        get all actions with a specific type
        (if types is empty return all actions)
        """
        if not types:
            return self.actions
        return [i for i in self.actions if i.type in types]

    def get_creator(self):
        """return the creator of the request"""
        if len(self.statehistory):
            return self.statehistory[0].who
        return self.state.who

    def to_xml(self):
        """serialize object to XML"""
        root = ET.Element('request')
        if not self.reqid is None:
            root.set('id', self.reqid)
        for action in self.actions:
            root.append(action.to_xml())
        if not self.state is None:
            root.append(self.state.to_xml())
        for review in self.reviews:
            root.append(review.to_xml())
        for hist in self.statehistory:
            root.append(hist.to_xml())
        if self.title:
            ET.SubElement(root, 'title').text = self.title
        if self.description:
            ET.SubElement(root, 'description').text = self.description
        if self.accept_at:
            ET.SubElement(root, 'accept_at').text = self.accept_at
        return root

    def to_str(self):
        """return "pretty" XML data"""
        root = self.to_xml()
        xmlindent(root)
        return ET.tostring(root, encoding=ET_ENCODING)

    def accept_at_in_hours(self, hours):
        """set auto accept_at time"""
        import datetime

        now = datetime.datetime.utcnow()
        now = now + datetime.timedelta(hours=hours)
        self.accept_at = now.isoformat()

    @staticmethod
    def format_review(review, show_srcupdate=False):
        """
        format a review depending on the reviewer's type.
        A dict which contains the formatted str's is returned.
        """

        d = {'state': '%s:' % review.state}
        if review.by_package:
            d['by'] = '%s/%s' % (review.by_project, review.by_package)
            d['type'] = 'Package'
        elif review.by_project:
            d['by'] = '%s' % review.by_project
            d['type'] = 'Project'
        elif review.by_group:
            d['by'] = '%s' % review.by_group
            d['type'] = 'Group'
        else:
            d['by'] = '%s' % review.by_user
            d['type'] = 'User'
        if review.who:
            d['by'] += '(%s)' % review.who
        return d

    def format_action(self, action, show_srcupdate=False):
        """
        format an action depending on the action's type.
        A dict which contains the formatted str's is returned.
        """
        def prj_pkg_join(prj, pkg, repository=None):
            if not pkg:
                if not repository:
                    return prj or ''
                return '%s(%s)' % (prj, repository)
            return '%s/%s' % (prj, pkg)

        d = {'type': '%s:' % action.type}
        if action.type == 'set_bugowner':
            if action.person_name:
                d['source'] = action.person_name
            if action.group_name:
                d['source'] = 'group:%s' % action.group_name
            d['target'] = prj_pkg_join(action.tgt_project, action.tgt_package)
        elif action.type == 'change_devel':
            d['source'] = prj_pkg_join(action.tgt_project, action.tgt_package)
            d['target'] = 'developed in %s' % prj_pkg_join(action.src_project, action.src_package)
        elif action.type == 'maintenance_incident':
            d['source'] = '%s ->' % action.src_project
            if action.src_package:
                d['source'] = '%s' % prj_pkg_join(action.src_project, action.src_package)
                if action.src_rev:
                    d['source'] = d['source'] + '@%s' % action.src_rev
                d['source'] = d['source'] + ' ->'
            d['target'] = action.tgt_project
            if action.tgt_releaseproject:
                d['target'] += " (release in " + action.tgt_releaseproject + ")"
            srcupdate = ' '
            if action.opt_sourceupdate and show_srcupdate:
                srcupdate = '(%s)' % action.opt_sourceupdate
        elif action.type == 'maintenance_release':
            d['source'] = '%s' % prj_pkg_join(action.src_project, action.src_package)
            if action.src_rev:
                d['source'] = d['source'] + '@%s' % action.src_rev
            d['source'] = d['source'] + ' ->'
            d['target'] = prj_pkg_join(action.tgt_project, action.tgt_package)
        elif action.type == 'submit':
            d['source'] = '%s' % prj_pkg_join(action.src_project, action.src_package)
            if action.src_rev:
                d['source'] = d['source'] + '@%s' % action.src_rev
            if action.opt_sourceupdate and show_srcupdate:
                d['source'] = d['source'] + '(%s)' % action.opt_sourceupdate
            d['source'] = d['source'] + ' ->'
            tgt_package = action.tgt_package
            if action.src_package == action.tgt_package:
                tgt_package = ''
            d['target'] = prj_pkg_join(action.tgt_project, tgt_package)
        elif action.type == 'add_role':
            roles = []
            if action.person_name and action.person_role:
                roles.append('person: %s as %s' % (action.person_name, action.person_role))
            if action.group_name and action.group_role:
                roles.append('group: %s as %s' % (action.group_name, action.group_role))
            d['source'] = ', '.join(roles)
            d['target'] = prj_pkg_join(action.tgt_project, action.tgt_package)
        elif action.type == 'delete':
            d['source'] = ''
            d['target'] = prj_pkg_join(action.tgt_project, action.tgt_package, action.tgt_repository)
        elif action.type == 'group':
            l = action.grouped_id
            if l is None:
                # there may be no requests in a group action
                l = ''
            if not hasattr(l, 'append'):
                l = [l]
            d['source'] = ', '.join(l) + ' ->'
            d['target'] = self.reqid
        else:
            raise oscerr.APIError('Unknown action type %s\n' % action.type)
        return d

    def list_view(self):
        """return "list view" format"""
        import textwrap
        lines = ['%6s  State:%-10s By:%-12s When:%-19s' % (self.reqid, self.state.name, self.state.who, self.state.when)]
        tmpl = '        %(type)-16s %(source)-50s %(target)s'
        for action in self.actions:
            lines.append(tmpl % self.format_action(action))
        tmpl = '        Review by %(type)-10s is %(state)-10s %(by)-50s'
        for review in self.reviews:
            lines.append(tmpl % Request.format_review(review))
        history = ['%s(%s)' % (hist.name, hist.who) for hist in self.statehistory]
        if history:
            lines.append('        From: %s' % ' -> '.join(history))
        if self.description:
            lines.append(textwrap.fill(self.description, width=80, initial_indent='        Descr: ',
                subsequent_indent='               '))
        lines.append(textwrap.fill(self.state.comment, width=80, initial_indent='        Comment: ',
                subsequent_indent='               '))
        return '\n'.join(lines)

    def __str__(self):
        """return "detailed" format"""
        lines = ['Request: #%s\n' % self.reqid]
        if self.accept_at and self.state.name in [ 'new', 'review' ]:
            lines.append('    *** This request will get automatically accepted after '+self.accept_at+' ! ***\n')
            
        for action in self.actions:
            tmpl = '  %(type)-13s %(source)s %(target)s'
            if action.type == 'delete':
                # remove 1 whitespace because source is empty
                tmpl = '  %(type)-12s %(source)s %(target)s'
            lines.append(tmpl % self.format_action(action, show_srcupdate=True))
        lines.append('\n\nMessage:')
        if self.description:
            lines.append(self.description)
        else:
            lines.append('<no message>')
        if self.state:
            lines.append('\nState:   %-10s %-12s %s' % (self.state.name, self.state.when, self.state.who))
            lines.append('Comment: %s' % (self.state.comment or '<no comment>'))

        indent = '\n         '
        tmpl = '%(state)-10s %(by)-50s %(when)-12s %(who)-20s  %(comment)s'
        reviews = []
        for review in reversed(self.reviews):
            d = {'state': review.state}
            if review.by_user:
                d['by'] = "User: " + review.by_user
            if review.by_group:
                d['by'] = "Group: " + review.by_group
            if review.by_package:
                d['by'] = "Package: " + review.by_project + "/" + review.by_package 
            elif review.by_project:
                d['by'] = "Project: " + review.by_project
            d['when'] = review.when or ''
            d['who'] = review.who or ''
            d['comment'] = review.comment or ''
            reviews.append(tmpl % d)
        if reviews:
            lines.append('\nReview:  %s' % indent.join(reviews))

        tmpl = '%(name)-10s %(when)-12s %(who)s'
        histories = []
        for hist in reversed(self.statehistory):
            d = {'name': hist.name, 'when': hist.when,
                'who': hist.who}
            histories.append(tmpl % d)
        if histories:
            lines.append('\nHistory: %s' % indent.join(histories))

        return '\n'.join(lines)

    def __cmp__(self, other):
        return cmp(int(self.reqid), int(other.reqid))

    def create(self, apiurl, addrevision=False):
        """create a new request"""
        query = {'cmd'    : 'create' }
        if addrevision:
            query['addrevision'] = "1"
        u = makeurl(apiurl, ['request'], query=query)
        f = http_POST(u, data=self.to_str())
        root = ET.fromstring(f.read())
        self.read(root)

def shorttime(t):
    """format time as Apr 02 18:19
    or                Apr 02  2005
    depending on whether it is in the current year
    """
    import time

    if time.localtime()[0] == time.localtime(t)[0]:
        # same year
        return time.strftime('%b %d %H:%M', time.localtime(t))
    else:
        return time.strftime('%b %d  %Y', time.localtime(t))


def is_project_dir(d):
    global store

    return os.path.exists(os.path.join(d, store, '_project')) and not \
           os.path.exists(os.path.join(d, store, '_package'))


def is_package_dir(d):
    global store

    return os.path.exists(os.path.join(d, store, '_project')) and \
           os.path.exists(os.path.join(d, store, '_package'))

def parse_disturl(disturl):
    """Parse a disturl, returns tuple (apiurl, project, source, repository,
    revision), else raises an oscerr.WrongArgs exception
    """

    global DISTURL_RE

    m = DISTURL_RE.match(disturl)
    if not m:
        raise oscerr.WrongArgs("`%s' does not look like disturl" % disturl)

    apiurl = m.group('apiurl')
    if apiurl.split('.')[0] != 'api':
        apiurl = 'https://api.' + ".".join(apiurl.split('.')[1:])
    return (apiurl, m.group('project'), m.group('source'), m.group('repository'), m.group('revision'))

def parse_buildlogurl(buildlogurl):
    """Parse a build log url, returns a tuple (apiurl, project, package,
    repository, arch), else raises oscerr.WrongArgs exception"""

    global BUILDLOGURL_RE

    m = BUILDLOGURL_RE.match(buildlogurl)
    if not m:
        raise oscerr.WrongArgs('\'%s\' does not look like url with a build log' % buildlogurl)

    return (m.group('apiurl'), m.group('project'), m.group('package'), m.group('repository'), m.group('arch'))

def slash_split(l):
    """Split command line arguments like 'foo/bar' into 'foo' 'bar'.
    This is handy to allow copy/paste a project/package combination in this form.

    Trailing slashes are removed before the split, because the split would
    otherwise give an additional empty string.
    """
    r = []
    for i in l:
        i = i.rstrip('/')
        r += i.split('/')
    return r

def expand_proj_pack(args, idx=0, howmany=0):
    """looks for occurance of '.' at the position idx.
    If howmany is 2, both proj and pack are expanded together
    using the current directory, or none of them, if not possible.
    If howmany is 0, proj is expanded if possible, then, if there
    is no idx+1 element in args (or args[idx+1] == '.'), pack is also
    expanded, if possible.
    If howmany is 1, only proj is expanded if possible.

    If args[idx] does not exists, an implicit '.' is assumed.
    if not enough elements up to idx exist, an error is raised.

    See also parseargs(args), slash_split(args), findpacs(args)
    All these need unification, somehow.
    """

    # print args,idx,howmany

    if len(args) < idx:
        raise oscerr.WrongArgs('not enough argument, expected at least %d' % idx)

    if len(args) == idx:
        args += '.'
    if args[idx+0] == '.':
        if howmany == 0 and len(args) > idx+1:
            if args[idx+1] == '.':
                # we have two dots.
                # remove one dot and make sure to expand both proj and pack
                args.pop(idx+1)
                howmany = 2
            else:
                howmany = 1
        # print args,idx,howmany

        args[idx+0] = store_read_project('.')
        if howmany == 0:
            try:
                package = store_read_package('.')
                args.insert(idx+1, package)
            except:
                pass
        elif howmany == 2:
            package = store_read_package('.')
            args.insert(idx+1, package)
    return args


def findpacs(files, progress_obj=None):
    """collect Package objects belonging to the given files
    and make sure each Package is returned only once"""
    pacs = []
    for f in files:
        p = filedir_to_pac(f, progress_obj)
        known = None
        for i in pacs:
            if i.name == p.name:
                known = i
                break
        if known:
            i.merge(p)
        else:
            pacs.append(p)
    return pacs


def filedir_to_pac(f, progress_obj=None):
    """Takes a working copy path, or a path to a file inside a working copy,
    and returns a Package object instance

    If the argument was a filename, add it onto the "todo" list of the Package """

    if os.path.isdir(f):
        wd = f
        p = Package(wd, progress_obj=progress_obj)
    else:
        wd = os.path.dirname(f) or os.curdir
        p = Package(wd, progress_obj=progress_obj)
        p.todo = [ os.path.basename(f) ]
    return p


def read_filemeta(dir):
    global store

    msg = '\'%s\' is not a valid working copy.' % dir
    filesmeta = os.path.join(dir, store, '_files')
    if not is_package_dir(dir):
        raise oscerr.NoWorkingCopy(msg)
    if not os.path.isfile(filesmeta):
        raise oscerr.NoWorkingCopy('%s (%s does not exist)' % (msg, filesmeta))

    try:
        r = ET.parse(filesmeta)
    except SyntaxError as e:
        raise oscerr.NoWorkingCopy('%s\nWhen parsing .osc/_files, the following error was encountered:\n%s' % (msg, e))
    return r

def store_readlist(dir, name):
    global store

    r = []
    if os.path.exists(os.path.join(dir, store, name)):
        r = [line.rstrip('\n') for line in open(os.path.join(dir, store, name), 'r')]
    return r

def read_tobeadded(dir):
    return store_readlist(dir, '_to_be_added')

def read_tobedeleted(dir):
    return store_readlist(dir, '_to_be_deleted')

def read_sizelimit(dir):
    global store

    r = None
    fname = os.path.join(dir, store, '_size_limit')

    if os.path.exists(fname):
        r = open(fname).readline().strip()

    if r is None or not r.isdigit():
        return None
    return int(r)

def read_inconflict(dir):
    return store_readlist(dir, '_in_conflict')

def parseargs(list_of_args):
    """Convenience method osc's commandline argument parsing.

    If called with an empty tuple (or list), return a list containing the current directory.
    Otherwise, return a list of the arguments."""
    if list_of_args:
        return list(list_of_args)
    else:
        return [os.curdir]


def statfrmt(statusletter, filename):
    return '%s    %s' % (statusletter, filename)


def pathjoin(a, *p):
    """Join two or more pathname components, inserting '/' as needed. Cut leading ./"""
    path = os.path.join(a, *p)
    if path.startswith('./'):
        path = path[2:]
    return path


def makeurl(baseurl, l, query=[]):
    """Given a list of path compoments, construct a complete URL.

    Optional parameters for a query string can be given as a list, as a
    dictionary, or as an already assembled string.
    In case of a dictionary, the parameters will be urlencoded by this
    function. In case of a list not -- this is to be backwards compatible.
    """

    if conf.config['verbose'] > 1:
        print('makeurl:', baseurl, l, query)

    if isinstance(query, type(list())):
        query = '&'.join(query)
    elif isinstance(query, type(dict())):
        query = urlencode(query)

    scheme, netloc = urlsplit(baseurl)[0:2]
    return urlunsplit((scheme, netloc, '/'.join(l), query, ''))


def http_request(method, url, headers={}, data=None, file=None):
    """wrapper around urllib2.urlopen for error handling,
    and to support additional (PUT, DELETE) methods"""
    def create_memoryview(obj):
        if sys.version_info < (2, 7, 99):
            # obj might be a mmap and python 2.7's mmap does not
            # behave like a bytearray (a bytearray in turn can be used
            # to create the memoryview). For now simply return a buffer
            return buffer(obj)
        return memoryview(obj)

    filefd = None

    if conf.config['http_debug']:
        print('\n\n--', method, url, file=sys.stderr)

    if method == 'POST' and not file and not data:
        # adding data to an urllib2 request transforms it into a POST
        data = ''

    req = URLRequest(url)
    api_host_options = {}
    if conf.is_known_apiurl(url):
        # ok no external request
        install_opener(conf._build_opener(url))
        api_host_options = conf.get_apiurl_api_host_options(url)
        for header, value in api_host_options['http_headers']:
            req.add_header(header, value)

    req.get_method = lambda: method

    # POST requests are application/x-www-form-urlencoded per default
    # but sending data requires an octet-stream type
    if method == 'PUT' or (method == 'POST' and (data or file)):
        req.add_header('Content-Type', 'application/octet-stream')

    if isinstance(headers, type({})):
        for i in headers.keys():
            print(headers[i])
            req.add_header(i, headers[i])

    if file and not data:
        size = os.path.getsize(file)
        if size < 1024*512:
            data = open(file, 'rb').read()
        else:
            import mmap
            filefd = open(file, 'rb')
            try:
                if sys.platform[:3] != 'win':
                    data = mmap.mmap(filefd.fileno(), os.path.getsize(file), mmap.MAP_SHARED, mmap.PROT_READ)
                else:
                    data = mmap.mmap(filefd.fileno(), os.path.getsize(file))
                data = create_memoryview(data)
            except EnvironmentError as e:
                if e.errno == 19:
                    sys.exit('\n\n%s\nThe file \'%s\' could not be memory mapped. It is ' \
                             '\non a filesystem which does not support this.' % (e, file))
                elif hasattr(e, 'winerror') and e.winerror == 5:
                    # falling back to the default io
                    data = open(file, 'rb').read()
                else:
                    raise

    if conf.config['debug']: print(method, url, file=sys.stderr)

    try:
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        fd = urlopen(req, data=data)

    finally:
        if hasattr(conf.cookiejar, 'save'):
            conf.cookiejar.save(ignore_discard=True)

    if filefd: filefd.close()

    return fd


def http_GET(*args, **kwargs):    return http_request('GET', *args, **kwargs)
def http_POST(*args, **kwargs):   return http_request('POST', *args, **kwargs)
def http_PUT(*args, **kwargs):    return http_request('PUT', *args, **kwargs)
def http_DELETE(*args, **kwargs): return http_request('DELETE', *args, **kwargs)


def check_store_version(dir):
    global store

    versionfile = os.path.join(dir, store, '_osclib_version')
    try:
        v = open(versionfile).read().strip()
    except:
        v = ''

    if v == '':
        msg = 'Error: "%s" is not an osc package working copy.' % os.path.abspath(dir)
        if os.path.exists(os.path.join(dir, '.svn')):
            msg = msg + '\nTry svn instead of osc.'
        raise oscerr.NoWorkingCopy(msg)

    if v != __store_version__:
        if v in ['0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9', '0.95', '0.96', '0.97', '0.98', '0.99']:
            # version is fine, no migration needed
            f = open(versionfile, 'w')
            f.write(__store_version__ + '\n')
            f.close()
            return
        msg = 'The osc metadata of your working copy "%s"' % dir
        msg += '\nhas __store_version__ = %s, but it should be %s' % (v, __store_version__)
        msg += '\nPlease do a fresh checkout or update your client. Sorry about the inconvenience.'
        raise oscerr.WorkingCopyWrongVersion(msg)


def meta_get_packagelist(apiurl, prj, deleted=None):

    query = {}
    if deleted:
        query['deleted'] = 1

    u = makeurl(apiurl, ['source', prj], query)
    f = http_GET(u)
    root = ET.parse(f).getroot()
    return [ node.get('name') for node in root.findall('entry') ]


def meta_get_filelist(apiurl, prj, package, verbose=False, expand=False, revision=None, meta=False, deleted=False):
    """return a list of file names,
    or a list File() instances if verbose=True"""

    query = {}
    if deleted:
        query['deleted'] = 1
    if expand:
        query['expand'] = 1
    if meta:
        query['meta'] = 1
    if revision:
        query['rev'] = revision
    else:
        query['rev'] = 'latest'

    u = makeurl(apiurl, ['source', prj, package], query=query)
    f = http_GET(u)
    root = ET.parse(f).getroot()

    if not verbose:
        return [ node.get('name') for node in root.findall('entry') ]

    else:
        l = []
        # rev = int(root.get('rev'))    # don't force int. also allow srcmd5 here.
        rev = root.get('rev')
        for node in root.findall('entry'):
            f = File(node.get('name'),
                     node.get('md5'),
                     int(node.get('size')),
                     int(node.get('mtime')))
            f.rev = rev
            l.append(f)
        return l


def meta_get_project_list(apiurl, deleted=None):
    query = {}
    if deleted:
        query['deleted'] = 1

    u = makeurl(apiurl, ['source'], query)
    f = http_GET(u)
    root = ET.parse(f).getroot()
    return sorted([ node.get('name') for node in root if node.get('name')])


def show_project_meta(apiurl, prj):
    url = makeurl(apiurl, ['source', prj, '_meta'])
    f = http_GET(url)
    return f.readlines()


def show_project_conf(apiurl, prj):
    url = makeurl(apiurl, ['source', prj, '_config'])
    f = http_GET(url)
    return f.readlines()


def show_package_trigger_reason(apiurl, prj, pac, repo, arch):
    url = makeurl(apiurl, ['build', prj, repo, arch, pac, '_reason'])
    try:
        f = http_GET(url)
        return f.read()
    except HTTPError as e:
        e.osc_msg = 'Error getting trigger reason for project \'%s\' package \'%s\'' % (prj, pac)
        raise


def show_package_meta(apiurl, prj, pac, meta=False):
    query = {}
    if meta:
        query['meta'] = 1

    # The fake packages _project has no _meta file
    if pac.startswith('_project'):
        return ""

    url = makeurl(apiurl, ['source', prj, pac, '_meta'], query)
    try:
        f = http_GET(url)
        return f.readlines()
    except HTTPError as e:
        e.osc_msg = 'Error getting meta for project \'%s\' package \'%s\'' % (prj, pac)
        raise


def show_attribute_meta(apiurl, prj, pac, subpac, attribute, with_defaults, with_project):
    path = []
    path.append('source')
    path.append(prj)
    if pac:
        path.append(pac)
    if pac and subpac:
        path.append(subpac)
    path.append('_attribute')
    if attribute:
        path.append(attribute)
    query = []
    if with_defaults:
        query.append("with_default=1")
    if with_project:
        query.append("with_project=1")
    url = makeurl(apiurl, path, query)
    try:
        f = http_GET(url)
        return f.readlines()
    except HTTPError as e:
        e.osc_msg = 'Error getting meta for project \'%s\' package \'%s\'' % (prj, pac)
        raise


def show_devel_project(apiurl, prj, pac):
    m = show_package_meta(apiurl, prj, pac)
    node = ET.fromstring(''.join(m)).find('devel')
    if node is None:
        return None, None
    else:
        return node.get('project'), node.get('package', None)


def set_devel_project(apiurl, prj, pac, devprj=None, devpac=None):
    meta = show_package_meta(apiurl, prj, pac)
    root = ET.fromstring(''.join(meta))
    node = root.find('devel')
    if node is None:
        if devprj is None:
            return
        node = ET.Element('devel')
        root.append(node)
    else:
        if devprj is None:
            root.remove(node)
        else:
            node.clear()
    if devprj:
        node.set('project', devprj)
        if devpac:
            node.set('package', devpac)
    url = makeurl(apiurl, ['source', prj, pac, '_meta'])
    mf = metafile(url, ET.tostring(root, encoding=ET_ENCODING))
    mf.sync()


def show_package_disabled_repos(apiurl, prj, pac):
    m = show_package_meta(apiurl, prj, pac)
    #FIXME: don't work if all repos of a project are disabled and only some are enabled since <disable/> is empty
    try:
        root = ET.fromstring(''.join(m))
        elm = root.find('build')
        r = [ node.get('repository') for node in elm.findall('disable')]
        return r
    except:
        return None


def show_pattern_metalist(apiurl, prj):
    url = makeurl(apiurl, ['source', prj, '_pattern'])
    try:
        f = http_GET(url)
        tree = ET.parse(f)
    except HTTPError as e:
        e.osc_msg = 'show_pattern_metalist: Error getting pattern list for project \'%s\'' % prj
        raise
    r = sorted([ node.get('name') for node in tree.getroot() ])
    return r


def show_pattern_meta(apiurl, prj, pattern):
    url = makeurl(apiurl, ['source', prj, '_pattern', pattern])
    try:
        f = http_GET(url)
        return f.readlines()
    except HTTPError as e:
        e.osc_msg = 'show_pattern_meta: Error getting pattern \'%s\' for project \'%s\'' % (pattern, prj)
        raise


class metafile:
    """metafile that can be manipulated and is stored back after manipulation."""
    def __init__(self, url, input, change_is_required=False, file_ext='.xml'):
        import tempfile

        self.url = url
        self.change_is_required = change_is_required
        (fd, self.filename) = tempfile.mkstemp(prefix = 'osc_metafile.', suffix = file_ext)
        f = os.fdopen(fd, 'w')
        f.write(''.join(input))
        f.close()
        self.hash_orig = dgst(self.filename)

    def sync(self):
        if self.change_is_required and self.hash_orig == dgst(self.filename):
            print('File unchanged. Not saving.')
            os.unlink(self.filename)
            return

        print('Sending meta data...')
        # don't do any exception handling... it's up to the caller what to do in case
        # of an exception
        http_PUT(self.url, file=self.filename)
        os.unlink(self.filename)
        print('Done.')

    def edit(self):
        try:
            while True:
                run_editor(self.filename)
                try:
                    self.sync()
                    break
                except HTTPError as e:
                    error_help = "%d" % e.code
                    if e.headers.get('X-Opensuse-Errorcode'):
                        error_help = "%s (%d)" % (e.headers.get('X-Opensuse-Errorcode'), e.code)

                    print('BuildService API error:', error_help, file=sys.stderr)
                    # examine the error - we can't raise an exception because we might want
                    # to try again
                    data = e.read()
                    if '<summary>' in data:
                        print(data.split('<summary>')[1].split('</summary>')[0], file=sys.stderr)
                    ri = raw_input('Try again? ([y/N]): ')
                    if ri not in ['y', 'Y']:
                        break
        finally:
            self.discard()

    def discard(self):
        if os.path.exists(self.filename):
            print('discarding %s' % self.filename)
            os.unlink(self.filename)

# different types of metadata
metatypes = { 'prj':     { 'path': 'source/%s/_meta',
                           'template': new_project_templ,
                           'file_ext': '.xml'
                         },
              'pkg':     { 'path'     : 'source/%s/%s/_meta',
                           'template': new_package_templ,
                           'file_ext': '.xml'
                         },
              'attribute':     { 'path'     : 'source/%s/%s/_meta',
                           'template': new_attribute_templ,
                           'file_ext': '.xml'
                         },
              'prjconf': { 'path': 'source/%s/_config',
                           'template': '',
                           'file_ext': '.txt'
                         },
              'user':    { 'path': 'person/%s',
                           'template': new_user_template,
                           'file_ext': '.xml'
                         },
              'pattern': { 'path': 'source/%s/_pattern/%s',
                           'template': new_pattern_template,
                           'file_ext': '.xml'
                         },
            }

def meta_exists(metatype,
                path_args=None,
                template_args=None,
                create_new=True,
                apiurl=None):

    global metatypes

    if not apiurl:
        apiurl = conf.config['apiurl']
    url = make_meta_url(metatype, path_args, apiurl)
    try:
        data = http_GET(url).readlines()
    except HTTPError as e:
        if e.code == 404 and create_new:
            data = metatypes[metatype]['template']
            if template_args:
                data = StringIO(data % template_args).readlines()
        else:
            raise e

    return data

def make_meta_url(metatype, path_args=None, apiurl=None, force=False, remove_linking_repositories=False):
    global metatypes

    if not apiurl:
        apiurl = conf.config['apiurl']
    if metatype not in metatypes.keys():
        raise AttributeError('make_meta_url(): Unknown meta type \'%s\'' % metatype)
    path = metatypes[metatype]['path']

    if path_args:
        path = path % path_args

    query = {}
    if force:
        query = { 'force': '1' }
    if remove_linking_repositories:
        query['remove_linking_repositories'] = '1'

    return makeurl(apiurl, [path], query)


def edit_meta(metatype,
              path_args=None,
              data=None,
              template_args=None,
              edit=False,
              force=False,
              remove_linking_repositories=False,
              change_is_required=False,
              apiurl=None):

    global metatypes

    if not apiurl:
        apiurl = conf.config['apiurl']
    if not data:
        data = meta_exists(metatype,
                           path_args,
                           template_args,
                           create_new = metatype != 'prjconf', # prjconf always exists, 404 => unknown prj
                           apiurl=apiurl)

    if edit:
        change_is_required = True

    if metatype == 'pkg':
        # check if the package is a link to a different project
        project, package = path_args
        orgprj = ET.fromstring(''.join(data)).get('project')
        if orgprj is not None and unquote(project) != orgprj:
            print('The package is linked from a different project.')
            print('If you want to edit the meta of the package create first a branch.')
            print('  osc branch %s %s %s' % (orgprj, package, unquote(project)))
            print('  osc meta pkg %s %s -e' % (unquote(project), package))
            return

    url = make_meta_url(metatype, path_args, apiurl, force, remove_linking_repositories)
    f = metafile(url, data, change_is_required, metatypes[metatype]['file_ext'])

    if edit:
        f.edit()
    else:
        f.sync()


def show_files_meta(apiurl, prj, pac, revision=None, expand=False, linkrev=None, linkrepair=False, meta=False):
    query = {}
    if revision:
        query['rev'] = revision
    else:
        query['rev'] = 'latest'
    if linkrev:
        query['linkrev'] = linkrev
    elif conf.config['linkcontrol']:
        query['linkrev'] = 'base'
    if meta:
        query['meta'] = 1
    if expand:
        query['expand'] = 1
    if linkrepair:
        query['emptylink'] = 1
    f = http_GET(makeurl(apiurl, ['source', prj, pac], query=query))
    return f.read()

def show_upstream_srcmd5(apiurl, prj, pac, expand=False, revision=None, meta=False, include_service_files=False):
    m = show_files_meta(apiurl, prj, pac, expand=expand, revision=revision, meta=meta)
    et = ET.fromstring(''.join(m))
    if include_service_files:
        try:
            sinfo = et.find('serviceinfo')
            if sinfo != None and sinfo.get('xsrcmd5') and not sinfo.get('error'):
                return sinfo.get('xsrcmd5')
        except:
            pass
    return et.get('srcmd5')


def show_upstream_xsrcmd5(apiurl, prj, pac, revision=None, linkrev=None, linkrepair=False, meta=False, include_service_files=False):
    m = show_files_meta(apiurl, prj, pac, revision=revision, linkrev=linkrev, linkrepair=linkrepair, meta=meta, expand=include_service_files)
    et = ET.fromstring(''.join(m))
    if include_service_files:
        return et.get('srcmd5')
    try:
        # only source link packages have a <linkinfo> element.
        li_node = et.find('linkinfo')
    except:
        return None

    li = Linkinfo()
    li.read(li_node)

    if li.haserror():
        raise oscerr.LinkExpandError(prj, pac, li.error)
    return li.xsrcmd5


def show_upstream_rev_vrev(apiurl, prj, pac, revision=None, expand=False, meta=False):
    m = show_files_meta(apiurl, prj, pac, revision=revision, expand=expand, meta=meta)
    et = ET.fromstring(''.join(m))
    return et.get('rev'), et.get('vrev')

def show_upstream_rev(apiurl, prj, pac, revision=None, expand=False, linkrev=None, meta=False, include_service_files=False):
    m = show_files_meta(apiurl, prj, pac, revision=revision, expand=expand, linkrev=linkrev, meta=meta)
    et = ET.fromstring(''.join(m))
    if include_service_files:
        try:
            sinfo = et.find('serviceinfo')
            if sinfo != None and sinfo.get('xsrcmd5') and not sinfo.get('error'):
                return sinfo.get('xsrcmd5')
        except:
            pass
    return et.get('rev')


def read_meta_from_spec(specfile, *args):
    import codecs, re
    """
    Read tags and sections from spec file. To read out
    a tag the passed argument mustn't end with a colon. To
    read out a section the passed argument must start with
    a '%'.
    This method returns a dictionary which contains the
    requested data.
    """

    if not os.path.isfile(specfile):
        raise oscerr.OscIOError(None, '\'%s\' is not a regular file' % specfile)

    try:
        lines = codecs.open(specfile, 'r', locale.getpreferredencoding()).readlines()
    except UnicodeDecodeError:
        lines = open(specfile).readlines()

    tags = []
    sections = []
    spec_data = {}

    for itm in args:
        if itm.startswith('%'):
            sections.append(itm)
        else:
            tags.append(itm)

    tag_pat = '(?P<tag>^%s)\s*:\s*(?P<val>.*)'
    for tag in tags:
        m = re.compile(tag_pat % tag, re.I | re.M).search(''.join(lines))
        if m and m.group('val'):
            spec_data[tag] = m.group('val').strip()

    section_pat = '^%s\s*?$'
    for section in sections:
        m = re.compile(section_pat % section, re.I | re.M).search(''.join(lines))
        if m:
            start = lines.index(m.group()+'\n') + 1
        data = []
        for line in lines[start:]:
            if line.startswith('%'):
                break
            data.append(line)
        spec_data[section] = data

    return spec_data

def get_default_editor():
    import platform
    system = platform.system()
    if system == 'Windows':
        return 'notepad'
    if system == 'Linux':
        try:
            # Python 2.6
            dist = platform.linux_distribution()[0]
        except AttributeError:
            dist = platform.dist()[0]
        if dist == 'debian':
            return 'editor'
        elif dist == 'fedora':
            return 'vi'
        return 'vim'
    return 'vi'

def get_default_pager():
    import platform
    system = platform.system()
    if system == 'Windows':
        return 'less'
    if system == 'Linux':
        try:
            # Python 2.6
            dist = platform.linux_distribution()[0]
        except AttributeError:
            dist = platform.dist()[0]
        if dist == 'debian':
            return 'pager'
        return 'less'
    return 'more'

def run_pager(message, tmp_suffix=''):
    import tempfile, sys

    if not message:
        return

    if not sys.stdout.isatty():
        print(message)
    else:
        tmpfile = tempfile.NamedTemporaryFile(suffix=tmp_suffix)
        tmpfile.write(message)
        tmpfile.flush()
        pager = os.getenv('PAGER', default=get_default_pager())
        try:
            run_external(pager, tmpfile.name)
        finally:
            tmpfile.close()

def run_editor(filename):
    cmd = _editor_command()
    cmd.append(filename)
    return run_external(cmd[0], *cmd[1:])

def _editor_command():
    editor = os.getenv('EDITOR', default=get_default_editor())
    try:
        cmd = shlex.split(editor)
    except SyntaxError:
        cmd = editor.split()
    return cmd

def _edit_message_open_editor(filename, data, orig_mtime):
    # FIXME: import modules globally
    import tempfile
    editor = _editor_command()
    mtime = os.stat(filename).st_mtime
    if mtime == orig_mtime:
        # prepare file for editors
        if editor[0] in ('vi', 'vim'):
            with tempfile.NamedTemporaryFile() as f:
                f.write(data)
                f.flush()
                editor.extend(['-c', ':r %s' % f.name, filename])
                run_external(editor[0], *editor[1:])
        else:
            with open(filename, 'w') as f:
                f.write(data)
            orig_mtime = os.stat(filename).st_mtime
            run_editor(filename)
    else:
        run_editor(filename)
    return os.stat(filename).st_mtime != orig_mtime

def edit_message(footer='', template='', templatelen=30):
    import tempfile
    delim = '--This line, and those below, will be ignored--\n'
    data = ''
    if template != '':
        if not templatelen is None:
            lines = template.splitlines()
            data = '\n'.join(lines[:templatelen])
            if lines[templatelen:]:
                footer = '%s\n\n%s' % ('\n'.join(lines[templatelen:]), footer)
    data += '\n' + delim + '\n' + footer
    try:
        (fd, filename) = tempfile.mkstemp(prefix='osc-commitmsg', suffix='.diff')
        os.close(fd)
        mtime = os.stat(filename).st_mtime
        while True:
            file_changed = _edit_message_open_editor(filename, data, mtime)
            msg = open(filename).read().split(delim)[0].rstrip()
            if msg and file_changed:
                break
            else:
                reason = 'Log message not specified'
                if template and template == msg:
                    reason = 'Default log message was not changed. Press \'c\' to continue.'
                ri = raw_input('%s\na)bort, c)ontinue, e)dit: ' % reason)
                if ri in 'aA':
                    raise oscerr.UserAbort()
                elif ri in 'cC':
                    break
                elif ri in 'eE':
                    pass
    finally:
        os.unlink(filename)
    return msg

def clone_request(apiurl, reqid, msg=None):
    query = {'cmd': 'branch', 'request': reqid}
    url = makeurl(apiurl, ['source'], query)
    r = http_POST(url, data=msg)
    root = ET.fromstring(r.read())
    project = None
    for i in root.findall('data'):
        if i.get('name') == 'targetproject':
            project = i.text.strip()
    if not project:
        raise oscerr.APIError('invalid data from clone request:\n%s\n' % ET.tostring(root, encoding=ET_ENCODING))
    return project

# create a maintenance release request
def create_release_request(apiurl, src_project, message=''):
    import cgi
    r = Request()
    # api will complete the request
    r.add_action('maintenance_release', src_project=src_project)
    # XXX: clarify why we need the unicode(...) stuff
    r.description = cgi.escape(unicode(message, 'utf8'))
    r.create(apiurl)
    return r

# create a maintenance incident per request
def create_maintenance_request(apiurl, src_project, src_packages, tgt_project, tgt_releaseproject, opt_sourceupdate, message=''):
    import cgi
    r = Request()
    if src_packages:
        for p in src_packages:
            r.add_action('maintenance_incident', src_project=src_project, src_package=p, tgt_project=tgt_project, tgt_releaseproject=tgt_releaseproject, opt_sourceupdate = opt_sourceupdate)
    else:
        r.add_action('maintenance_incident', src_project=src_project, tgt_project=tgt_project, tgt_releaseproject=tgt_releaseproject, opt_sourceupdate = opt_sourceupdate)
    # XXX: clarify why we need the unicode(...) stuff
    r.description = cgi.escape(unicode(message, 'utf8'))
    r.create(apiurl, addrevision=True)
    return r

# This creates an old style submit request for server api 1.0
def create_submit_request(apiurl,
                         src_project, src_package=None,
                         dst_project=None, dst_package=None,
                         message="", orev=None, src_update=None):

    import cgi
    options_block = ""
    package = ""
    if src_package:
        package = """package="%s" """ % (src_package)
    if src_update:
        options_block = """<options><sourceupdate>%s</sourceupdate></options> """ % (src_update)

    # Yes, this kind of xml construction is horrible
    targetxml = ""
    if dst_project:
        packagexml = ""
        if dst_package:
            packagexml = """package="%s" """ % ( dst_package )
        targetxml = """<target project="%s" %s /> """ % ( dst_project, packagexml )
    # XXX: keep the old template for now in order to work with old obs instances
    xml = """\
<request type="submit">
    <submit>
        <source project="%s" %s rev="%s"/>
        %s
        %s
    </submit>
    <state name="new"/>
    <description>%s</description>
</request>
""" % (src_project,
       package,
       orev or show_upstream_rev(apiurl, src_project, src_package),
       targetxml,
       options_block,
       cgi.escape(message))

    # Don't do cgi.escape(unicode(message, "utf8"))) above.
    # Promoting the string to utf8, causes the post to explode with:
    #   uncaught exception: Fatal error: Start tag expected, '&lt;' not found at :1.
    # I guess, my original workaround was not that bad.

    u = makeurl(apiurl, ['request'], query='cmd=create')
    r = None
    try:
        f = http_POST(u, data=xml)
        root = ET.parse(f).getroot()
        r = root.get('id')
    except HTTPError as e:
        if e.headers.get('X-Opensuse-Errorcode') == "submit_request_rejected":
            print("WARNING:")
            print("WARNING: Project does not accept submit request, request to open a NEW maintenance incident instead")
            print("WARNING:")
            xpath = 'maintenance/maintains/@project = \'%s\'' % dst_project
            res = search(apiurl, project_id=xpath)
            root = res['project_id']
            project = root.find('project')
            if project is None:
                raise oscerr.APIError("Server did not define a default maintenance project, can't submit.")
            tproject = project.get('name')
            r = create_maintenance_request(apiurl, src_project, [src_package], tproject, dst_project, src_update, message)
        else:
            raise

    return r


def get_request(apiurl, reqid):
    u = makeurl(apiurl, ['request', reqid])
    f = http_GET(u)
    root = ET.parse(f).getroot()

    r = Request()
    r.read(root)
    return r


def change_review_state(apiurl, reqid, newstate, by_user='', by_group='', by_project='', by_package='', message='', supersed=None):
    query = {'cmd': 'changereviewstate', 'newstate': newstate }
    if by_user:
        query['by_user'] = by_user
    if by_group:
        query['by_group'] = by_group
    if by_project:
        query['by_project'] = by_project
    if by_package:
        query['by_package'] = by_package
    if supersed:
        query['superseded_by'] = supersed
    u = makeurl(apiurl, ['request', reqid], query=query)
    f = http_POST(u, data=message)
    root = ET.parse(f).getroot()
    return root.get('code')

def change_request_state(apiurl, reqid, newstate, message='', supersed=None, force=False):
    query = {'cmd': 'changestate', 'newstate': newstate }
    if supersed:
        query['superseded_by'] = supersed
    if force:
        query['force'] = "1"
    u = makeurl(apiurl,
                ['request', reqid], query=query)
    f = http_POST(u, data=message)

    r = f.read()
    if r.startswith('<status code="'):
        r = r.split('<status code="')[1]
        r = r.split('" />')[0]

    return r

def change_request_state_template(req, newstate):
    if not len(req.actions):
        return ''
    action = req.actions[0]
    tmpl_name = '%srequest_%s_template' % (action.type, newstate)
    tmpl = conf.config.get(tmpl_name, '')
    tmpl = tmpl.replace('\\t', '\t').replace('\\n', '\n')    
    data = {'reqid': req.reqid, 'type': action.type, 'who': req.get_creator()}
    if req.actions[0].type == 'submit':
        data.update({'src_project': action.src_project,
            'src_package': action.src_package, 'src_rev': action.src_rev,
            'dst_project': action.tgt_project, 'dst_package': action.tgt_package,
            'tgt_project': action.tgt_project, 'tgt_package': action.tgt_package})
    try:
        return tmpl % data
    except KeyError as e:
        print('error: cannot interpolate \'%s\' in \'%s\'' % (e.args[0], tmpl_name), file=sys.stderr)
        return ''

def get_review_list(apiurl, project='', package='', byuser='', bygroup='', byproject='', bypackage='', states=('new')):
    # this is so ugly...
    def build_by(xpath, val):
        if 'all' in states:
            return xpath_join(xpath, 'review/%s' % val, op='and')
        elif states:
            s_xp = ''
            for state in states:
                s_xp = xpath_join(s_xp, '@state=\'%s\'' % state, inner=True)
            val = val.strip('[').strip(']')
            return xpath_join(xpath, 'review[%s and (%s)]' % (val, s_xp), op='and')
        return ''

    xpath = ''
    xpath = xpath_join(xpath, 'state/@name=\'review\'', inner=True)
    if not 'all' in states:
        for state in states:
            xpath = xpath_join(xpath, 'review/@state=\'%s\'' % state, inner=True)
    if byuser or bygroup or bypackage or byproject:
        # discard constructed xpath...
        xpath = xpath_join('', 'state/@name=\'review\'', inner=True)
    if byuser:
        xpath = build_by(xpath, '@by_user=\'%s\'' % byuser)
    if bygroup:
        xpath = build_by(xpath, '@by_group=\'%s\'' % bygroup)
    if bypackage:
        xpath = build_by(xpath, '@by_project=\'%s\' and @by_package=\'%s\'' % (byproject, bypackage))
    elif byproject:
        xpath = build_by(xpath, '@by_project=\'%s\'' % byproject)

    # XXX: we cannot use the '|' in the xpath expression because it is not supported
    #      in the backend
    todo = {}
    if project:
        todo['project'] = project
    if package:
        todo['package'] = package
    for kind, val in todo.items():
        xpath_base = 'action/target/@%(kind)s=\'%(val)s\' or ' \
                     'submit/target/@%(kind)s=\'%(val)s\''

        if conf.config['include_request_from_project']:
            xpath_base = xpath_join(xpath_base, 'action/source/@%(kind)s=\'%(val)s\' or ' \
                                                'submit/source/@%(kind)s=\'%(val)s\'', op='or', inner=True)
        xpath = xpath_join(xpath, xpath_base % {'kind': kind, 'val': val}, op='and', nexpr_parentheses=True)

    if conf.config['verbose'] > 1:
        print('[ %s ]' % xpath)
    res = search(apiurl, request=xpath)
    collection = res['request']
    requests = []
    for root in collection.findall('request'):
        r = Request()
        r.read(root)
        requests.append(r)
    return requests

def get_exact_request_list(apiurl, src_project, dst_project, src_package=None, dst_package=None, req_who=None, req_state=('new', 'review', 'declined'), req_type=None):
    xpath = ''
    if not 'all' in req_state:
        for state in req_state:
            xpath = xpath_join(xpath, 'state/@name=\'%s\'' % state, op='or', inner=True)
        xpath = '(%s)' % xpath
    if req_who:
        xpath = xpath_join(xpath, '(state/@who=\'%(who)s\' or history/@who=\'%(who)s\')' % {'who': req_who}, op='and')

    xpath += " and action[source/@project='%s'" % src_project
    if src_package:
        xpath += " and source/@package='%s'" % src_package
    xpath += " and target/@project='%s'" % dst_project
    if src_project:
        xpath += " and target/@package='%s'" % dst_package
    xpath += "]"
    if req_type:
        xpath += " and action/@type=\'%s\'" % req_type

    if conf.config['verbose'] > 1:
        print('[ %s ]' % xpath)

    res = search(apiurl, request=xpath)
    collection = res['request']
    requests = []
    for root in collection.findall('request'):
        r = Request()
        r.read(root)
        requests.append(r)
    return requests

def get_request_list(apiurl, project='', package='', req_who='', req_state=('new', 'review', 'declined'), req_type=None, exclude_target_projects=[]):
    xpath = ''
    if not 'all' in req_state:
        for state in req_state:
            xpath = xpath_join(xpath, 'state/@name=\'%s\'' % state, inner=True)
    if req_who:
        xpath = xpath_join(xpath, '(state/@who=\'%(who)s\' or history/@who=\'%(who)s\')' % {'who': req_who}, op='and')

    # XXX: we cannot use the '|' in the xpath expression because it is not supported
    #      in the backend
    todo = {}
    if project:
        todo['project'] = project
    if package:
        todo['package'] = package
    for kind, val in todo.items():
        xpath_base = 'action/target/@%(kind)s=\'%(val)s\' or ' \
                     'submit/target/@%(kind)s=\'%(val)s\''

        if conf.config['include_request_from_project']:
            xpath_base = xpath_join(xpath_base, 'action/source/@%(kind)s=\'%(val)s\' or ' \
                                                'submit/source/@%(kind)s=\'%(val)s\'', op='or', inner=True)
        xpath = xpath_join(xpath, xpath_base % {'kind': kind, 'val': val}, op='and', nexpr_parentheses=True)

    if req_type:
        xpath = xpath_join(xpath, 'action/@type=\'%s\'' % req_type, op='and')
    for i in exclude_target_projects:
        xpath = xpath_join(xpath, '(not(action/target/@project=\'%(prj)s\' or ' \
                                  'submit/target/@project=\'%(prj)s\'))' % {'prj': i}, op='and')

    if conf.config['verbose'] > 1:
        print('[ %s ]' % xpath)
    res = search(apiurl, request=xpath)
    collection = res['request']
    requests = []
    for root in collection.findall('request'):
        r = Request()
        r.read(root)
        requests.append(r)
    return requests

# old style search, this is to be removed
def get_user_projpkgs_request_list(apiurl, user, req_state=('new', 'review', ), req_type=None, exclude_projects=[], projpkgs={}):
    """OBSOLETE: user involved request search is supported by OBS 2.2 server side in a better way
       Return all running requests for all projects/packages where is user is involved"""
    if not projpkgs:
        res = get_user_projpkgs(apiurl, user, exclude_projects=exclude_projects)
        projects = []
        for i in res['project_id'].findall('project'):
            projpkgs[i.get('name')] = []
            projects.append(i.get('name'))
        for i in res['package_id'].findall('package'):
            if not i.get('project') in projects:
                projpkgs.setdefault(i.get('project'), []).append(i.get('name'))
    xpath = ''
    for prj, pacs in projpkgs.items():
        if not len(pacs):
            xpath = xpath_join(xpath, 'action/target/@project=\'%s\'' % prj, inner=True)
        else:
            xp = ''
            for p in pacs:
                xp = xpath_join(xp, 'action/target/@package=\'%s\'' % p, inner=True)
            xp = xpath_join(xp, 'action/target/@project=\'%s\'' % prj, op='and')
            xpath = xpath_join(xpath, xp, inner=True)
    if req_type:
        xpath = xpath_join(xpath, 'action/@type=\'%s\'' % req_type, op='and')
    if not 'all' in req_state:
        xp = ''
        for state in req_state:
            xp = xpath_join(xp, 'state/@name=\'%s\'' % state, inner=True)
        xpath = xpath_join(xp, xpath, op='and', nexpr_parentheses=True)
    res = search(apiurl, request=xpath)
    result = []
    for root in res['request'].findall('request'):
        r = Request()
        r.read(root)
        result.append(r)
    return result

def get_request_log(apiurl, reqid):
    r = get_request(apiurl, reqid)
    data = []
    frmt = '-' * 76 + '\n%s | %s | %s\n\n%s'
    r.statehistory.reverse()
    # the description of the request is used for the initial log entry
    # otherwise its comment attribute would contain None
    if len(r.statehistory) >= 1:
        r.statehistory[-1].comment = r.description
    else:
        r.state.comment = r.description
    for state in [ r.state ] + r.statehistory:
        s = frmt % (state.name, state.who, state.when, str(state.comment))
        data.append(s)
    return data

def check_existing_requests(apiurl, src_project, src_package, dst_project,
                            dst_package):
    reqs = get_exact_request_list(apiurl, src_project, dst_project,
                                  src_package, dst_package,
                                  req_type='submit',
                                  req_state=['new','review', 'declined'])
    repl = ''
    if reqs:
        print('There are already the following submit request: %s.' % \
              ', '.join([i.reqid for i in reqs]))
        repl = raw_input('Supersede the old requests? (y/n/c) ')
        if repl.lower() == 'c':
            print('Aborting', file=sys.stderr)
            raise oscerr.UserAbort()
    return repl == 'y', reqs

def get_group(apiurl, group):
    u = makeurl(apiurl, ['group', quote_plus(group)])
    try:
        f = http_GET(u)
        return ''.join(f.readlines())
    except HTTPError:
        print('user \'%s\' not found' % group)
        return None

def get_user_meta(apiurl, user):
    u = makeurl(apiurl, ['person', quote_plus(user)])
    try:
        f = http_GET(u)
        return ''.join(f.readlines())
    except HTTPError:
        print('user \'%s\' not found' % user)
        return None


def _get_xml_data(meta, *tags):
    data = []
    if meta != None:
        root = ET.fromstring(meta)
        for tag in tags:
            elm = root.find(tag)
            if elm is None or elm.text is None:
                data.append('-')
            else:
                data.append(elm.text)
    return data


def get_user_data(apiurl, user, *tags):
    """get specified tags from the user meta"""
    meta = get_user_meta(apiurl, user)
    return _get_xml_data(meta, *tags)
    

def get_group_data(apiurl, group, *tags):
    meta = get_group(apiurl, group)
    return _get_xml_data(meta, *tags)


def download(url, filename, progress_obj = None, mtime = None):
    import tempfile, shutil
    global BUFSIZE

    o = None
    try:
        prefix = os.path.basename(filename)
        path = os.path.dirname(filename)
        (fd, tmpfile) = tempfile.mkstemp(dir=path, prefix = prefix, suffix = '.osctmp')
        os.fchmod(fd, 0o644)
        try:
            o = os.fdopen(fd, 'wb')
            for buf in streamfile(url, http_GET, BUFSIZE, progress_obj=progress_obj):
                o.write(bytes(buf,"utf-8"))
            o.close()
            os.rename(tmpfile, filename)
        except:
            os.unlink(tmpfile)
            raise
    finally:
        if o is not None:
            o.close()

    if mtime:
        utime(filename, (-1, mtime))

def get_source_file(apiurl, prj, package, filename, targetfilename=None, revision=None, progress_obj=None, mtime=None, meta=False):
    targetfilename = targetfilename or filename
    query = {}
    if meta:
        query['rev'] = 1
    if revision:
        query['rev'] = revision
    u = makeurl(apiurl, ['source', prj, package, pathname2url(filename.encode(locale.getpreferredencoding(), 'replace'))], query=query)
    download(u, targetfilename, progress_obj, mtime)

def get_binary_file(apiurl, prj, repo, arch,
                    filename,
                    package = None,
                    target_filename = None,
                    target_mtime = None,
                    progress_meter = False):
    progress_obj = None
    if progress_meter:
        from .meter import TextMeter
        progress_obj = TextMeter()

    target_filename = target_filename or filename

    where = package or '_repository'
    u = makeurl(apiurl, ['build', prj, repo, arch, where, filename])
    download(u, target_filename, progress_obj, target_mtime)

def dgst_from_string(str):
    # Python 2.5 depracates the md5 modules
    # Python 2.4 doesn't have hashlib yet
    try:
        import hashlib
        md5_hash = hashlib.md5()
    except ImportError:
        import md5
        md5_hash = md5.new()
    md5_hash.update(str)
    return md5_hash.hexdigest()

def dgst(file):

    #if not os.path.exists(file):
        #return None

    global BUFSIZE

    try:
        import hashlib
        md5 = hashlib
    except ImportError:
        import md5
        md5 = md5
    s = md5.md5()
    f = open(file, 'rb')
    while True:
        buf = f.read(BUFSIZE)
        if not buf: break
        s.update(buf)
    return s.hexdigest()
    f.close()


def binary(s):
    """return true if a string is binary data using diff's heuristic"""
    if s and bytes('\0', "utf-8") in s[:4096]:
        return True
    return False


def binary_file(fn):
    """read 4096 bytes from a file named fn, and call binary() on the data"""
    return binary(open(fn, 'rb').read(4096))


def get_source_file_diff(dir, filename, rev, oldfilename = None, olddir = None, origfilename = None):
    """
    This methods diffs oldfilename against filename (so filename will
    be shown as the new file).
    The variable origfilename is used if filename and oldfilename differ
    in their names (for instance if a tempfile is used for filename etc.)
    """

    import difflib

    global store

    if not oldfilename:
        oldfilename = filename

    if not olddir:
        olddir = os.path.join(dir, store)

    if not origfilename:
        origfilename = filename

    file1 = os.path.join(olddir, oldfilename)   # old/stored original
    file2 = os.path.join(dir, filename)         # working copy
    if binary_file(file1) or binary_file(file2):
        return ['Binary file \'%s\' has changed.\n' % origfilename]

    f1 = f2 = None
    try:
        f1 = open(file1, 'rt')
        s1 = f1.readlines()
        f1.close()

        f2 = open(file2, 'rt')
        s2 = f2.readlines()
        f2.close()
    finally:
        if f1:
            f1.close()
        if f2:
            f2.close()

    d = difflib.unified_diff(s1, s2,
        fromfile = '%s\t(revision %s)' % (origfilename, rev), \
        tofile = '%s\t(working copy)' % origfilename)
    d = list(d)
    # python2.7's difflib slightly changed the format
    # adapt old format to the new format
    if len(d) > 1:
        d[0] = d[0].replace(' \n', '\n')
        d[1] = d[1].replace(' \n', '\n')

    # if file doesn't end with newline, we need to append one in the diff result
    for i, line in enumerate(d):
        if not line.endswith('\n'):
            d[i] += '\n\\ No newline at end of file'
            if i+1 != len(d):
                d[i] += '\n'
    return d

def server_diff(apiurl,
                old_project, old_package, old_revision,
                new_project, new_package, new_revision,
                unified=False, missingok=False, meta=False, expand=True, full=True):
    query = {'cmd': 'diff'}
    if expand:
        query['expand'] = 1
    if old_project:
        query['oproject'] = old_project
    if old_package:
        query['opackage'] = old_package
    if old_revision:
        query['orev'] = old_revision
    if new_revision:
        query['rev'] = new_revision
    if unified:
        query['unified'] = 1
    if missingok:
        query['missingok'] = 1
    if meta:
        query['meta'] = 1
    if full:
        query['filelimit'] = 0
        query['tarlimit'] = 0

    u = makeurl(apiurl, ['source', new_project, new_package], query=query)

    f = http_POST(u)
    return f.read()

def server_diff_noex(apiurl,
                old_project, old_package, old_revision,
                new_project, new_package, new_revision,
                unified=False, missingok=False, meta=False, expand=True):
    try:
        return server_diff(apiurl,
                            old_project, old_package, old_revision,
                            new_project, new_package, new_revision,
                            unified, missingok, meta, expand)
    except HTTPError as e:
        msg = None
        body = None
        try:
            body = e.read()
            if not 'bad link' in body:
                return '# diff failed: ' + body
        except:
            return '# diff failed with unknown error'

        if expand:
            rdiff =  "## diff on expanded link not possible, showing unexpanded version\n"
            try:
                rdiff += server_diff_noex(apiurl,
                    old_project, old_package, old_revision,
                    new_project, new_package, new_revision,
                    unified, missingok, meta, False)
            except:
                elm = ET.fromstring(body).find('summary')
                summary = ''
                if not elm is None:
                    summary = elm.text
                return 'error: diffing failed: %s' % summary
            return rdiff


def request_diff(apiurl, reqid):
    u = makeurl(apiurl, ['request', reqid], query={'cmd': 'diff'} )

    f = http_POST(u)
    return f.read()

def submit_action_diff(apiurl, action):
    """diff a single submit action"""
    # backward compatiblity: only a recent api/backend supports the missingok parameter
    try:
        return server_diff(apiurl, action.tgt_project, action.tgt_package, None,
            action.src_project, action.src_package, action.src_rev, True, True)
    except HTTPError as e:
        if e.code == 400:
            try:
                return server_diff(apiurl, action.tgt_project, action.tgt_package, None,
                    action.src_project, action.src_package, action.src_rev, True, False)
            except HTTPError as e:
                if e.code != 404:
                    raise e
                root = ET.fromstring(e.read())
                return 'error: \'%s\' does not exist' % root.find('summary').text
        elif e.code == 404:
            root = ET.fromstring(e.read())
            return 'error: \'%s\' does not exist' % root.find('summary').text
        raise e

def make_dir(apiurl, project, package, pathname=None, prj_dir=None, package_tracking=True, pkg_path=None):
    """
    creates the plain directory structure for a package dir.
    The 'apiurl' parameter is needed for the project dir initialization.
    The 'project' and 'package' parameters specify the name of the
    project and the package. The optional 'pathname' parameter is used
    for printing out the message that a new dir was created (default: 'prj_dir/package').
    The optional 'prj_dir' parameter specifies the path to the project dir (default: 'project').
    If pkg_path is not None store the package's content in pkg_path (no project structure is created)
    """
    prj_dir = prj_dir or project

    # FIXME: carefully test each patch component of prj_dir,
    # if we have a .osc/_files entry at that level.
    #   -> if so, we have a package/project clash,
    #      and should rename this path component by appending '.proj'
    #      and give user a warning message, to discourage such clashes

    if pkg_path is None:
        pathname = pathname or getTransActPath(os.path.join(prj_dir, package))
        pkg_path = os.path.join(prj_dir, package)
        if is_package_dir(prj_dir):
            # we want this to become a project directory,
            # but it already is a package directory.
            raise oscerr.OscIOError(None, 'checkout_package: package/project clash. Moving myself away not implemented')

        if not is_project_dir(prj_dir):
            # this directory could exist as a parent direory for one of our earlier
            # checked out sub-projects. in this case, we still need to initialize it.
            print(statfrmt('A', prj_dir))
            Project.init_project(apiurl, prj_dir, project, package_tracking)

        if is_project_dir(os.path.join(prj_dir, package)):
            # the thing exists, but is a project directory and not a package directory
            # FIXME: this should be a warning message to discourage package/project clashes
            raise oscerr.OscIOError(None, 'checkout_package: package/project clash. Moving project away not implemented')
    else:
        pathname = pkg_path

    if not os.path.exists(pkg_path):
        print(statfrmt('A', pathname))
        os.mkdir(os.path.join(pkg_path))
#        os.mkdir(os.path.join(prj_dir, package, store))

    return pkg_path


def checkout_package(apiurl, project, package,
                     revision=None, pathname=None, prj_obj=None,
                     expand_link=False, prj_dir=None, server_service_files = None, service_files=None, progress_obj=None, size_limit=None, meta=False, outdir=None):
    try:
        # the project we're in might be deleted.
        # that'll throw an error then.
        olddir = os.getcwd()
    except:
        olddir = os.environ.get("PWD")

    if not prj_dir:
        prj_dir = olddir
    else:
        if sys.platform[:3] == 'win':
            prj_dir = prj_dir[:2] + prj_dir[2:].replace(':', ';')
        else:
            if conf.config['checkout_no_colon']:
                prj_dir = prj_dir.replace(':', '/')

    root_dots = '.'
    if conf.config['checkout_rooted']:
        if prj_dir[:1] == '/':
            if conf.config['verbose'] > 1:
                print("checkout_rooted ignored for %s" % prj_dir)
            # ?? should we complain if not is_project_dir(prj_dir) ??
        else:
            # if we are inside a project or package dir, ascend to parent
            # directories, so that all projects are checked out relative to
            # the same root.
            if is_project_dir(".."):
                # if we are in a package dir, goto parent.
                # Hmm, with 'checkout_no_colon' in effect, we have directory levels that
                # do not easily reveal the fact, that they are part of a project path.
                # At least this test should find that the parent of 'home/username/branches' 
                #  is a project (hack alert). Also goto parent in this case.
                root_dots = "../"
            elif is_project_dir("../.."):
                # testing two levels is better than one.
                # May happen in case of checkout_no_colon, or 
                # if project roots were previously inconsistent 
                root_dots = "../../"
            if is_project_dir(root_dots):
                if conf.config['checkout_no_colon']:
                    oldproj = store_read_project(root_dots)
                    n = len(oldproj.split(':'))
                else:
                    n = 1
                root_dots = root_dots + "../" * n

    if root_dots != '.':
        if conf.config['verbose']:
            print("found root of %s at %s" % (oldproj, root_dots))
        prj_dir = root_dots + prj_dir

    if not pathname:
        pathname = getTransActPath(os.path.join(prj_dir, package))

    # before we create directories and stuff, check if the package actually
    # exists
    show_package_meta(apiurl, project, package, meta)

    isfrozen = False
    if expand_link:
        # try to read from the linkinfo
        # if it is a link we use the xsrcmd5 as the revision to be
        # checked out
        try:
            x = show_upstream_xsrcmd5(apiurl, project, package, revision=revision, meta=meta, include_service_files=server_service_files)
        except:
            x = show_upstream_xsrcmd5(apiurl, project, package, revision=revision, meta=meta, linkrev='base', include_service_files=server_service_files)
            if x:
                isfrozen = True
        if x:
            revision = x
    directory = make_dir(apiurl, project, package, pathname, prj_dir, conf.config['do_package_tracking'], outdir)
    p = Package.init_package(apiurl, project, package, directory, size_limit, meta, progress_obj)
    if isfrozen:
        p.mark_frozen()
    # no project structure is wanted when outdir is used
    if conf.config['do_package_tracking'] and outdir is None:
        # check if we can re-use an existing project object
        if prj_obj is None:
            prj_obj = Project(prj_dir)
        prj_obj.set_state(p.name, ' ')
        prj_obj.write_packages()
    p.update(revision, server_service_files, size_limit)
    if service_files:
        print('Running all source services local')
        p.run_source_services()

def replace_pkg_meta(pkgmeta, new_name, new_prj, keep_maintainers = False,
                     dst_userid = None, keep_develproject = False):
    """
    update pkgmeta with new new_name and new_prj and set calling user as the
    only maintainer (unless keep_maintainers is set). Additionally remove the
    develproject entry (<devel />) unless keep_develproject is true.
    """
    root = ET.fromstring(''.join(pkgmeta))
    root.set('name', new_name)
    root.set('project', new_prj)
    if not keep_maintainers:
        for person in root.findall('person'):
            root.remove(person)
    if not keep_develproject:
        for dp in root.findall('devel'):
            root.remove(dp)
    return ET.tostring(root, encoding=ET_ENCODING)

def link_to_branch(apiurl, project,  package):
    """
     convert a package with a _link + project.diff to a branch
    """

    if '_link' in meta_get_filelist(apiurl, project, package):
        u = makeurl(apiurl, ['source', project, package], 'cmd=linktobranch')
        http_POST(u)
    else:
        raise oscerr.OscIOError(None, 'no _link file inside project \'%s\' package \'%s\'' % (project, package))

def link_pac(src_project, src_package, dst_project, dst_package, force, rev='', cicount='', disable_publish = False, missing_target = False, vrev=''):
    """
    create a linked package
     - "src" is the original package
     - "dst" is the "link" package that we are creating here
    """
    meta_change = False
    dst_meta = ''
    apiurl = conf.config['apiurl']
    try:
        dst_meta = meta_exists(metatype='pkg',
                               path_args=(quote_plus(dst_project), quote_plus(dst_package)),
                               template_args=None,
                               create_new=False, apiurl=apiurl)
        root = ET.fromstring(''.join(dst_meta))
        if root.get('project') != dst_project:
            # The source comes from a different project via a project link, we need to create this instance
            meta_change = True
    except:
        meta_change = True

    if meta_change:
        if missing_target:
            dst_meta = '<package name="%s"><title/><description/></package>' % dst_package
        else:
            src_meta = show_package_meta(apiurl, src_project, src_package)
            dst_meta = replace_pkg_meta(src_meta, dst_package, dst_project)

    if disable_publish:
        meta_change = True
        root = ET.fromstring(''.join(dst_meta))
        elm = root.find('publish')
        if not elm:
            elm = ET.SubElement(root, 'publish')
        elm.clear()
        ET.SubElement(elm, 'disable')
        dst_meta = ET.tostring(root, encoding=ET_ENCODING)

    if meta_change:
        edit_meta('pkg',
                  path_args=(dst_project, dst_package),
                  data=dst_meta)
    # create the _link file
    # but first, make sure not to overwrite an existing one
    if '_link' in meta_get_filelist(apiurl, dst_project, dst_package):
        if force:
            print('forced overwrite of existing _link file', file=sys.stderr)
        else:
            print(file=sys.stderr)
            print('_link file already exists...! Aborting', file=sys.stderr)
            sys.exit(1)

    if rev:
        rev = ' rev="%s"' % rev
    else:
        rev = ''

    if vrev:
        vrev = ' vrev="%s"' % vrev
    else:
        vrev = ''

    missingok = ''
    if missing_target:
        missingok = ' missingok="true"'

    if cicount:
        cicount = ' cicount="%s"' % cicount
    else:
        cicount = ''

    print('Creating _link...', end=' ')

    project = ''
    if src_project != dst_project:
        project = 'project="%s"' % src_project

    link_template = """\
<link %s package="%s"%s%s%s%s>
<patches>
  <!-- <branch /> for a full copy, default case  -->
  <!-- <apply name="patch" /> apply a patch on the source directory  -->
  <!-- <topadd>%%define build_with_feature_x 1</topadd> add a line on the top (spec file only) -->
  <!-- <add name="file.patch" /> add a patch to be applied after %%setup (spec file only) -->
  <!-- <delete name="filename" /> delete a file -->
</patches>
</link>
""" % (project, src_package, missingok, rev, vrev, cicount)

    u = makeurl(apiurl, ['source', dst_project, dst_package, '_link'])
    http_PUT(u, data=link_template)
    print('Done.')

def aggregate_pac(src_project, src_package, dst_project, dst_package, repo_map = {}, disable_publish = False, nosources = False):
    """
    aggregate package
     - "src" is the original package
     - "dst" is the "aggregate" package that we are creating here
     - "map" is a dictionary SRC => TARGET repository mappings
    """
    meta_change = False
    dst_meta = ''
    apiurl = conf.config['apiurl']
    try:
        dst_meta = meta_exists(metatype='pkg',
                               path_args=(quote_plus(dst_project), quote_plus(dst_package)),
                               template_args=None,
                               create_new=False, apiurl=apiurl)
        root = ET.fromstring(''.join(dst_meta))
        if root.get('project') != dst_project:
            # The source comes from a different project via a project link, we need to create this instance
            meta_change = True
    except:
        meta_change = True

    if meta_change:
        src_meta = show_package_meta(apiurl, src_project, src_package)
        dst_meta = replace_pkg_meta(src_meta, dst_package, dst_project)
        meta_change = True

    if disable_publish:
        meta_change = True
        root = ET.fromstring(''.join(dst_meta))
        elm = root.find('publish')
        if not elm:
            elm = ET.SubElement(root, 'publish')
        elm.clear()
        ET.SubElement(elm, 'disable')
        dst_meta = ET.tostring(root, encoding=ET_ENCODING)
    if meta_change:
        edit_meta('pkg',
                  path_args=(dst_project, dst_package),
                  data=dst_meta)

    # create the _aggregate file
    # but first, make sure not to overwrite an existing one
    if '_aggregate' in meta_get_filelist(apiurl, dst_project, dst_package):
        print(file=sys.stderr)
        print('_aggregate file already exists...! Aborting', file=sys.stderr)
        sys.exit(1)

    print('Creating _aggregate...', end=' ')
    aggregate_template = """\
<aggregatelist>
  <aggregate project="%s">
""" % (src_project)

    aggregate_template += """\
    <package>%s</package>
""" % ( src_package)

    if nosources:
        aggregate_template += """\
    <nosources />
"""
    for src, tgt in repo_map.items():
        aggregate_template += """\
    <repository target="%s" source="%s" />
""" % (tgt, src)

    aggregate_template += """\
  </aggregate>
</aggregatelist>
"""

    u = makeurl(apiurl, ['source', dst_project, dst_package, '_aggregate'])
    http_PUT(u, data=aggregate_template)
    print('Done.')


def attribute_branch_pkg(apiurl, attribute, maintained_update_project_attribute, package, targetproject, return_existing=False, force=False, noaccess=False, add_repositories=False, dryrun=False, nodevelproject=False, maintenance=False):
    """
    Branch packages defined via attributes (via API call)
    """
    query = { 'cmd': 'branch' }
    query['attribute'] = attribute
    if targetproject:
        query['target_project'] = targetproject
    if dryrun:
        query['dryrun'] = "1"
    if force:
        query['force'] = "1"
    if noaccess:
        query['noaccess'] = "1"
    if nodevelproject:
        query['ignoredevel'] = '1'
    if add_repositories:
        query['add_repositories'] = "1"
    if maintenance:
        query['maintenance'] = "1"
    if package:
        query['package'] = package
    if maintained_update_project_attribute:
        query['update_project_attribute'] = maintained_update_project_attribute

    u = makeurl(apiurl, ['source'], query=query)
    f = None
    try:
        f = http_POST(u)
    except HTTPError as e:
        msg = ''.join(e.readlines())
        msg = msg.split('<summary>')[1]
        msg = msg.split('</summary>')[0]
        raise oscerr.APIError(msg)

    r = None

    root = ET.fromstring(f.read())
    if dryrun:
        return root
    # TODO: change api here and return parsed XML as class
    if conf.config['http_debug']:
        print(ET.tostring(root, encoding=ET_ENCODING), file=sys.stderr)
    for node in root.findall('data'):
        r = node.get('name')
        if r and r == 'targetproject':
            return node.text

    return r


def branch_pkg(apiurl, src_project, src_package, nodevelproject=False, rev=None, target_project=None, target_package=None, return_existing=False, msg='', force=False, noaccess=False, add_repositories=False, extend_package_names=False, missingok=False, maintenance=False):
    """
    Branch a package (via API call)
    """
    query = { 'cmd': 'branch' }
    if nodevelproject:
        query['ignoredevel'] = '1'
    if force:
        query['force'] = '1'
    if noaccess:
        query['noaccess'] = '1'
    if add_repositories:
        query['add_repositories'] = "1"
    if maintenance:
        query['maintenance'] = "1"
    if missingok:
        query['missingok'] = "1"
    if extend_package_names:
        query['extend_package_names'] = "1"
    if rev:
        query['rev'] = rev
    if target_project:
        query['target_project'] = target_project
    if target_package:
        query['target_package'] = target_package
    if msg:
        query['comment'] = msg
    u = makeurl(apiurl, ['source', src_project, src_package], query=query)
    try:
        f = http_POST(u)
    except HTTPError as e:
        if not return_existing:
            raise
        root = ET.fromstring(e.read())
        summary = root.find('summary')
        if summary is None:
            raise oscerr.APIError('unexpected response:\n%s' % ET.tostring(root, encoding=ET_ENCODING))
        m = re.match(r"branch target package already exists: (\S+)/(\S+)", summary.text)
        if not m:
            e.msg += '\n' + summary.text
            raise
        return (True, m.group(1), m.group(2), None, None)

    if conf.config['http_debug']:
        print(ET.tostring(root, encoding=ET_ENCODING), file=sys.stderr)
    data = {}
    for i in ET.fromstring(f.read()).findall('data'):
        data[i.get('name')] = i.text
    return (False, data.get('targetproject', None), data.get('targetpackage', None),
            data.get('sourceproject', None), data.get('sourcepackage', None))


def copy_pac(src_apiurl, src_project, src_package,
             dst_apiurl, dst_project, dst_package,
             client_side_copy = False,
             keep_maintainers = False,
             keep_develproject = False,
             expand = False,
             revision = None,
             comment = None,
             force_meta_update = None,
             keep_link = None):
    """
    Create a copy of a package.

    Copying can be done by downloading the files from one package and commit
    them into the other by uploading them (client-side copy) --
    or by the server, in a single api call.
    """

    if not (src_apiurl == dst_apiurl and src_project == dst_project \
        and src_package == dst_package):
        src_meta = show_package_meta(src_apiurl, src_project, src_package)
        dst_userid = conf.get_apiurl_usr(dst_apiurl)
        src_meta = replace_pkg_meta(src_meta, dst_package, dst_project, keep_maintainers,
                                    dst_userid, keep_develproject)

        url = make_meta_url('pkg', (quote_plus(dst_project),) + (quote_plus(dst_package),), dst_apiurl)
        found = None
        try:
            found = http_GET(url).readlines()
        except HTTPError as e:
            pass
        if force_meta_update or not found:
            print('Sending meta data...')
            u = makeurl(dst_apiurl, ['source', dst_project, dst_package, '_meta'])
            http_PUT(u, data=src_meta)

    print('Copying files...')
    if not client_side_copy:
        query = {'cmd': 'copy', 'oproject': src_project, 'opackage': src_package }
        if expand or keep_link:
            query['expand'] = '1'
        if keep_link:
            query['keeplink'] = '1'
        if revision:
            query['orev'] = revision
        if comment:
            query['comment'] = comment
        u = makeurl(dst_apiurl, ['source', dst_project, dst_package], query=query)
        f = http_POST(u)
        return f.read()

    else:
        # copy one file after the other
        import tempfile
        query = {'rev': 'upload'}
        revision = show_upstream_srcmd5(src_apiurl, src_project, src_package, expand=expand, revision=revision)
        for n in meta_get_filelist(src_apiurl, src_project, src_package, expand=expand, revision=revision):
            if n.startswith('_service:') or n.startswith('_service_'):
                continue
            print('  ', n)
            tmpfile = None
            try:
                (fd, tmpfile) = tempfile.mkstemp(prefix='osc-copypac')
                get_source_file(src_apiurl, src_project, src_package, n, targetfilename=tmpfile, revision=revision)
                u = makeurl(dst_apiurl, ['source', dst_project, dst_package, pathname2url(n)], query=query)
                http_PUT(u, file = tmpfile)
            finally:
                if not tmpfile is None:
                    os.unlink(tmpfile)
        if comment:
            query['comment'] = comment
        query['cmd'] = 'commit'
        u = makeurl(dst_apiurl, ['source', dst_project, dst_package], query=query)
        http_POST(u)
        return 'Done.'


def unlock_package(apiurl, prj, pac, msg):
    query = {'cmd': 'unlock', 'comment': msg}
    u = makeurl(apiurl, ['source', prj, pac], query)
    http_POST(u)

def unlock_project(apiurl, prj, msg=None):
    query = {'cmd': 'unlock', 'comment': msg}
    u = makeurl(apiurl, ['source', prj], query)
    http_POST(u)


def undelete_package(apiurl, prj, pac, msg=None):
    query = {'cmd': 'undelete'}
    if msg:
        query['comment'] = msg
    else:
        query['comment'] = 'undeleted via osc'
    u = makeurl(apiurl, ['source', prj, pac], query)
    http_POST(u)

def undelete_project(apiurl, prj, msg=None):
    query = {'cmd': 'undelete'}
    if msg:
        query['comment'] = msg
    else:
        query['comment'] = 'undeleted via osc'
    u = makeurl(apiurl, ['source', prj], query)
    http_POST(u)


def delete_package(apiurl, prj, pac, force=False, msg=None):
    query = {}
    if force:
        query['force'] = "1"
    if msg:
        query['comment'] = msg
    u = makeurl(apiurl, ['source', prj, pac], query)
    http_DELETE(u)

def delete_project(apiurl, prj, force=False, msg=None):
    query = {}
    if force:
        query['force'] = "1"
    if msg:
        query['comment'] = msg
    u = makeurl(apiurl, ['source', prj], query)
    http_DELETE(u)

def delete_files(apiurl, prj, pac, files):
    for filename in files:
        u = makeurl(apiurl, ['source', prj, pac, filename], query={'comment': 'removed %s' % (filename, )})
        http_DELETE(u)


# old compat lib call
def get_platforms(apiurl):
    return get_repositories(apiurl)

def get_repositories(apiurl):
    f = http_GET(makeurl(apiurl, ['platform']))
    tree = ET.parse(f)
    r = sorted([ node.get('name') for node in tree.getroot() ])
    return r


def get_distibutions(apiurl, discon=False):
    r = []

    # FIXME: this is just a naming convention on api.opensuse.org, but not a general valid apparoach
    if discon:
        result_line_templ = '%(name)-25s %(project)s'
        f = http_GET(makeurl(apiurl, ['build']))
        root = ET.fromstring(''.join(f))

        for node in root.findall('entry'):
            if node.get('name').startswith('DISCONTINUED:'):
                rmap = {}
                rmap['name'] = node.get('name').replace('DISCONTINUED:','').replace(':', ' ')
                rmap['project'] = node.get('name')
                r.append (result_line_templ % rmap)

        r.insert(0,'distribution              project')
        r.insert(1,'------------              -------')

    else:
        result_line_templ = '%(name)-25s %(project)-25s %(repository)-25s %(reponame)s'
        f = http_GET(makeurl(apiurl, ['distributions']))
        root = ET.fromstring(''.join(f))

        for node in root.findall('distribution'):
            rmap = {}
            for node2 in node.findall('name'):
                rmap['name'] = node2.text
            for node3 in node.findall('project'):
                rmap['project'] = node3.text
            for node4 in node.findall('repository'):
                rmap['repository'] = node4.text
            for node5 in node.findall('reponame'):
                rmap['reponame'] = node5.text
            r.append(result_line_templ % rmap)

        r.insert(0,'distribution              project                   repository                reponame')
        r.insert(1,'------------              -------                   ----------                --------')

    return r


# old compat lib call
def get_platforms_of_project(apiurl, prj):
    return get_repositories_of_project(apiurl, prj)

def get_repositories_of_project(apiurl, prj):
    f = show_project_meta(apiurl, prj)
    root = ET.fromstring(''.join(f))

    r = [ node.get('name') for node in root.findall('repository')]
    return r


class Repo:
    repo_line_templ = '%-15s %-10s'

    def __init__(self, name, arch):
        self.name = name
        self.arch = arch

    def __str__(self):
        return self.repo_line_templ % (self.name, self.arch)

def get_repos_of_project(apiurl, prj):
    f = show_project_meta(apiurl, prj)
    root = ET.fromstring(''.join(f))

    for node in root.findall('repository'):
        for node2 in node.findall('arch'):
            yield Repo(node.get('name'), node2.text)

def get_binarylist(apiurl, prj, repo, arch, package=None, verbose=False):
    what = package or '_repository'
    u = makeurl(apiurl, ['build', prj, repo, arch, what])
    f = http_GET(u)
    tree = ET.parse(f)
    if not verbose:
        return [ node.get('filename') for node in tree.findall('binary')]
    else:
        l = []
        for node in tree.findall('binary'):
            f = File(node.get('filename'),
                     None,
                     int(node.get('size')),
                     int(node.get('mtime')))
            l.append(f)
        return l


def get_binarylist_published(apiurl, prj, repo, arch):
    u = makeurl(apiurl, ['published', prj, repo, arch])
    f = http_GET(u)
    tree = ET.parse(f)
    r = [ node.get('name') for node in tree.findall('entry')]
    return r


def show_results_meta(apiurl, prj, package=None, lastbuild=None, repository=[], arch=[], oldstate=None):
    query = {}
    if package:
        query['package'] = package
    if oldstate:
        query['oldstate'] = oldstate
    if lastbuild:
        query['lastbuild'] = 1
    u = makeurl(apiurl, ['build', prj, '_result'], query=query)
    for repo in repository:
        u = u + '&repository=%s' % repo
    for a in arch:
        u = u + '&arch=%s' % a
    f = http_GET(u)
    return f.readlines()


def show_prj_results_meta(apiurl, prj):
    u = makeurl(apiurl, ['build', prj, '_result'])
    f = http_GET(u)
    return f.readlines()


def get_package_results(apiurl, prj, package, lastbuild=None, repository=[], arch=[], oldstate=None):
    """ return a package results as a list of dicts """
    r = []

    f = show_results_meta(apiurl, prj, package, lastbuild, repository, arch, oldstate)
    root = ET.fromstring(''.join(f))

    r.append( {'_oldstate': root.get('state')} )

    for node in root.findall('result'):
        rmap = {}
        rmap['project'] = rmap['prj'] = prj
        rmap['pkg'] = rmap['package'] = rmap['pac'] = package
        rmap['repository'] = rmap['repo'] = rmap['rep'] = node.get('repository')
        rmap['arch'] = node.get('arch')
        rmap['state'] = node.get('state')
        rmap['dirty'] = node.get('dirty')
        rmap['repostate'] = node.get('code')

        rmap['details'] = ''
        details = None
        statusnode = node.find('status')
        if statusnode != None:
            rmap['code'] = statusnode.get('code', '')
            details = statusnode.find('details')
        else:
            rmap['code'] = ''

        if details != None:
            rmap['details'] = details.text

        rmap['dirty'] = rmap['dirty'] == 'true'

        r.append(rmap)
    return r

def format_results(results, format):
    """apply selected format on each dict in results and return it as a list of strings"""
    return [format % r for r in results]

def get_results(apiurl, prj, package, lastbuild=None, repository=[], arch=[], verbose=False, wait=False, printJoin=None):
    r = []
    result_line_templ = '%(rep)-20s %(arch)-10s %(status)s'
    oldstate = None

    while True:
        waiting = False
        results = r = []
        try:
            results = get_package_results(apiurl, prj, package, lastbuild, repository, arch, oldstate)
        except HTTPError as e:
            # check for simple timeout error and fetch again
            if e.code == 502 or e.code == 504:
                # re-try result request
                continue
            raise

        for res in results:
            if '_oldstate' in res:
                oldstate = res['_oldstate']
                continue
            res['status'] = res['code']
            if verbose and res['details'] != '':
                if res['code'] in ('unresolvable', 'expansion error'):
                    lines = res['details'].split(',')
                    res['status'] += ': ' + '\n     '.join(lines)
                else:
                    res['status'] += ': %s' % (res['details'], )
            if res['dirty']:
                waiting = True
                if verbose:
                    res['status'] = 'outdated (was: %s)' % res['status']
                else:
                    res['status'] += '*'
            elif res['code'] in ('succeeded') and res['repostate'] != "published":
                waiting = True
                if verbose:
                    res['status'] += '(unpublished)'
                else:
                    res['status'] += '*'
            if res['code'] in ('blocked', 'scheduled', 'dispatching', 'building', 'signing', 'finished'):
                waiting = True

            r.append(result_line_templ % res)

        if printJoin:
            print(printJoin.join(r))

        if wait == False or waiting == False:
            break

    return r

def get_prj_results(apiurl, prj, hide_legend=False, csv=False, status_filter=None, name_filter=None, arch=None, repo=None, vertical=None, show_excluded=None):
    #print '----------------------------------------'
    global buildstatus_symbols

    r = []

    f = show_prj_results_meta(apiurl, prj)
    root = ET.fromstring(''.join(f))

    pacs = []
    # sequence of (repo,arch) tuples
    targets = []
    # {package: {(repo,arch): status}}
    status = {}
    if root.find('result') == None:
        return []
    for results in root.findall('result'):
        for node in results:
            pacs.append(node.get('package'))
    pacs = sorted(list(set(pacs)))
    for node in root.findall('result'):
        # filter architecture and repository
        if arch != None and node.get('arch') not in arch:
            continue
        if repo != None and node.get('repository') not in repo:
            continue
        if node.get('dirty') == "true":
            state = "outdated"
        else:
            state = node.get('state')
        tg = (node.get('repository'), node.get('arch'), state)
        targets.append(tg)
        for pacnode in node.findall('status'):
            pac = pacnode.get('package')
            if pac not in status:
                status[pac] = {}
            status[pac][tg] = pacnode.get('code')
    targets.sort()

    # filter option
    if status_filter or name_filter or not show_excluded:

        pacs_to_show = []
        targets_to_show = []

        #filtering for Package Status
        if status_filter:
            if status_filter in buildstatus_symbols.values():
                # a list is needed because if status_filter == "U"
                # we have to filter either an "expansion error" (obsolete)
                # or an "unresolvable" state
                filters = []
                for txt, sym in buildstatus_symbols.items():
                    if sym == status_filter:
                        filters.append(txt)
                for filt_txt in filters:
                    for pkg in status.keys():
                        for repo in status[pkg].keys():
                            if status[pkg][repo] == filt_txt:
                                if not name_filter:
                                    pacs_to_show.append(pkg)
                                    targets_to_show.append(repo)
                                elif name_filter in pkg:
                                    pacs_to_show.append(pkg)

        #filtering for Package Name
        elif name_filter:
            for pkg in pacs:
                if name_filter in pkg:
                    pacs_to_show.append(pkg)

        #filter non building states
        elif not show_excluded:
            enabled = {}
            for pkg in status.keys():
                showpkg = False
                for repo in status[pkg].keys():
                    if status[pkg][repo] != "excluded":
                        enabled[repo] = 1
                        showpkg = True

                if showpkg:
                    pacs_to_show.append(pkg)

            targets_to_show = enabled.keys()

        pacs = [ i for i in pacs if i in pacs_to_show ]
        if len(targets_to_show):
            targets = [ i for i in targets if i in targets_to_show ]

    # csv output
    if csv:
        # TODO: option to disable the table header
        row = ['_'] + ['/'.join(tg) for tg in targets]
        r.append(';'.join(row))
        for pac in pacs:
            row = [pac] + [status[pac][tg] for tg in targets if tg in status[pac]]
            r.append(';'.join(row))
        return r

    if not vertical:
        # human readable output
        max_pacs = 40
        for startpac in range(0, len(pacs), max_pacs):
            offset = 0
            for pac in pacs[startpac:startpac+max_pacs]:
                r.append(' |' * offset + ' ' + pac)
                offset += 1

            for tg in targets:
                line = []
                line.append(' ')
                for pac in pacs[startpac:startpac+max_pacs]:
                    st = ''
                    if pac not in status or tg not in status[pac]:
                        # for newly added packages, status may be missing
                        st = '?'
                    else:
                        try:
                            st = buildstatus_symbols[status[pac][tg]]
                        except:
                            print('osc: warn: unknown status \'%s\'...' % status[pac][tg])
                            print('please edit osc/core.py, and extend the buildstatus_symbols dictionary.')
                            st = '?'
                            buildstatus_symbols[status[pac][tg]] = '?'
                    line.append(st)
                    line.append(' ')
                line.append(' %s %s (%s)' % tg)
                line = ''.join(line)

                r.append(line)

            r.append('')
    else:
        offset = 0
        for tg in targets:
            r.append('| ' * offset + '%s %s (%s)'%tg )
            offset += 1

        for pac in pacs:
            line = []
            for tg in targets:
                st = ''
                if pac not in status or tg not in status[pac]:
                    # for newly added packages, status may be missing
                    st = '?'
                else:
                    try:
                        st = buildstatus_symbols[status[pac][tg]]
                    except:
                        print('osc: warn: unknown status \'%s\'...' % status[pac][tg])
                        print('please edit osc/core.py, and extend the buildstatus_symbols dictionary.')
                        st = '?'
                        buildstatus_symbols[status[pac][tg]] = '?'
                line.append(st)
            line.append(' '+pac)
            r.append(' '.join(line))

        line = []
        for i in range(0, len(targets)):
            line.append(str(i%10))
        r.append(' '.join(line))

        r.append('')

    if not hide_legend and len(pacs):
        r.append(' Legend:')
        legend = []
        for i, j in buildstatus_symbols.items():
            if i == "expansion error":
                continue
            legend.append('%3s %-20s' % (j, i))
        legend.append('  ? buildstatus not available (only new packages)')

        if vertical:
            for i in range(0, len(targets)):
                s = '%1d %s %s (%s)' % (i%10, targets[i][0], targets[i][1], targets[i][2])
                if i < len(legend):
                    legend[i] += s
                else:
                    legend.append(' '*24 + s)

        r += legend

    return r


def streamfile(url, http_meth = http_GET, bufsize=8192, data=None, progress_obj=None, text=None):
    """
    performs http_meth on url and read bufsize bytes from the response
    until EOF is reached. After each read bufsize bytes are yielded to the
    caller.
    """
    cl = ''
    retries = 0
    # Repeat requests until we get reasonable Content-Length header
    # Server (or iChain) is corrupting data at some point, see bnc#656281
    while cl == '':
        if retries >= int(conf.config['http_retries']):
            raise oscerr.OscIOError(None, 'Content-Length is empty for %s, protocol violation' % url)
        retries = retries + 1
        if retries > 1 and conf.config['http_debug']:
            print('\n\nRetry %d --' % (retries - 1), url, file=sys.stderr)
        f = http_meth.__call__(url, data = data)
        cl = f.info().get('Content-Length')

    if cl is not None:
        # sometimes the proxy adds the same header again
        # which yields in value like '3495, 3495'
        # use the first of these values (should be all the same)
        cl = cl.split(',')[0]
        cl = int(cl)

    if progress_obj:
        basename = os.path.basename(urlsplit(url)[2])
        progress_obj.start(basename=basename, text=text, size=cl)
    data = f.read(bufsize)
    read = len(data)
    while len(data):
        if progress_obj:
            progress_obj.update(read)
        yield data
        data = f.read(bufsize)
        read += len(data)
    if progress_obj:
        progress_obj.end(read)
    f.close()

    if not cl is None and read != cl:
        raise oscerr.OscIOError(None, 'Content-Length is not matching file size for %s: %i vs %i file size' % (url, cl, read))


def buildlog_strip_time(data):
    """Strips the leading build time from the log"""
    time_regex = re.compile('^\[\s{0,5}\d+s\]\s', re.M)
    return time_regex.sub('', data)


def print_buildlog(apiurl, prj, package, repository, arch, offset=0, strip_time=False, last=False):
    """prints out the buildlog on stdout"""

    # to protect us against control characters
    import string
    all_bytes = string.maketrans('', '')
    remove_bytes = all_bytes[:9] + all_bytes[11:32] # accept tabs and newlines

    query = {'nostream' : '1', 'start' : '%s' % offset}
    if last:
        query['last'] = 1
    while True:
        query['start'] = offset
        start_offset = offset
        u = makeurl(apiurl, ['build', prj, repository, arch, package, '_log'], query=query)
        for data in streamfile(u):
            offset += len(data)
            if strip_time:
                data = buildlog_strip_time(data)
            sys.stdout.write(data.translate(all_bytes, remove_bytes))
        if start_offset == offset:
            break

def get_dependson(apiurl, project, repository, arch, packages=None, reverse=None):
    query = []
    if packages:
        for i in packages:
            query.append('package=%s' % quote_plus(i))

    if reverse:
        query.append('view=revpkgnames')
    else:
        query.append('view=pkgnames')

    u = makeurl(apiurl, ['build', project, repository, arch, '_builddepinfo'], query=query)
    f = http_GET(u)
    return f.read()

def get_buildinfo(apiurl, prj, package, repository, arch, specfile=None, addlist=None, debug=None):
    query = []
    if addlist:
        for i in addlist:
            query.append('add=%s' % quote_plus(i))
    if debug:
        query.append('debug=1')

    u = makeurl(apiurl, ['build', prj, repository, arch, package, '_buildinfo'], query=query)

    if specfile:
        f = http_POST(u, data=specfile)
    else:
        f = http_GET(u)
    return f.read()


def get_buildconfig(apiurl, prj, repository):
    u = makeurl(apiurl, ['build', prj, repository, '_buildconfig'])
    f = http_GET(u)
    return f.read()

 
def get_source_rev(apiurl, project, package, revision=None):
    # API supports ?deleted=1&meta=1&rev=4
    # but not rev=current,rev=latest,rev=top, or anything like this.
    # CAUTION: We have to loop through all rev and find the highest one, if none given.

    if revision:
        url = makeurl(apiurl, ['source', project, package, '_history'], {'rev':revision})
    else:
        url = makeurl(apiurl, ['source', project, package, '_history'])
    f = http_GET(url)
    xml = ET.parse(f)
    ent = None
    for new in xml.findall('revision'):
        # remember the newest one.
        if not ent:
            ent = new
        elif ent.find('time').text < new.find('time').text:
            ent = new
    if not ent:
        return { 'version': None, 'error':'empty revisionlist: no such package?' }
    e = {}
    for k in ent.keys():
        e[k] = ent.get(k)
    for k in list(ent):
        e[k.tag] = k.text
    return e

def get_buildhistory(apiurl, prj, package, repository, arch, format = 'text'):
    import time
    u = makeurl(apiurl, ['build', prj, repository, arch, package, '_history'])
    f = http_GET(u)
    root = ET.parse(f).getroot()

    r = []
    for node in root.findall('entry'):
        rev = int(node.get('rev'))
        srcmd5 = node.get('srcmd5')
        versrel = node.get('versrel')
        bcnt = int(node.get('bcnt'))
        t = time.localtime(int(node.get('time')))
        t = time.strftime('%Y-%m-%d %H:%M:%S', t)

        if format == 'csv':
            r.append('%s|%s|%d|%s.%d' % (t, srcmd5, rev, versrel, bcnt))
        else:
            r.append('%s   %s %6d    %s.%d' % (t, srcmd5, rev, versrel, bcnt))

    if format == 'text':
        r.insert(0, 'time                  srcmd5                              rev   vers-rel.bcnt')

    return r

def print_jobhistory(apiurl, prj, current_package, repository, arch, format = 'text', limit=20):
    import time
    query = {}
    if current_package:
        query['package'] = current_package
    if limit != None and int(limit) > 0:
        query['limit'] = int(limit)
    u = makeurl(apiurl, ['build', prj, repository, arch, '_jobhistory'], query )
    f = http_GET(u)
    root = ET.parse(f).getroot()

    if format == 'text':
        print("time                 package                                            reason           code              build time      worker")
    for node in root.findall('jobhist'):
        package = node.get('package')
        worker = node.get('workerid')
        reason = node.get('reason')
        if not reason:
            reason = "unknown"
        code = node.get('code')
        rt = int(node.get('readytime'))
        readyt = time.localtime(rt)
        readyt = time.strftime('%Y-%m-%d %H:%M:%S', readyt)
        st = int(node.get('starttime'))
        et = int(node.get('endtime'))
        endtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(et))
        waittm = time.gmtime(et-st)
        if waittm.tm_mday > 1:
            waitbuild = "%1dd %2dh %2dm %2ds" % (waittm.tm_mday-1, waittm.tm_hour, waittm.tm_min, waittm.tm_sec)
        elif waittm.tm_hour:
            waitbuild = "   %2dh %2dm %2ds" % (waittm.tm_hour, waittm.tm_min, waittm.tm_sec)
        else:
            waitbuild = "       %2dm %2ds" % (waittm.tm_min, waittm.tm_sec)

        if format == 'csv':
            print('%s|%s|%s|%s|%s|%s' % (endtime, package, reason, code, waitbuild, worker))
        else:
            print('%s  %-50s %-16s %-16s %-16s %-16s' % (endtime, package[0:49], reason[0:15], code[0:15], waitbuild, worker))


def get_commitlog(apiurl, prj, package, revision, format = 'text', meta = False, deleted = False, revision_upper=None):
    import time

    query = {}
    if deleted:
        query['deleted'] = 1
    if meta:
        query['meta'] = 1

    u = makeurl(apiurl, ['source', prj, package, '_history'], query)
    f = http_GET(u)
    root = ET.parse(f).getroot()

    r = []
    if format == 'xml':
        r.append('<?xml version="1.0"?>')
        r.append('<log>')
    revisions = root.findall('revision')
    revisions.reverse()
    for node in revisions:
        srcmd5 = node.find('srcmd5').text
        try:
            rev = int(node.get('rev'))
            #vrev = int(node.get('vrev')) # what is the meaning of vrev?
            try:
                if revision is not None and revision_upper is not None:
                    if rev > int(revision_upper) or rev < int(revision):
                        continue
                elif revision is not None and rev != int(revision):
                    continue
            except ValueError:
                if revision != srcmd5:
                    continue
        except ValueError:
            # this part should _never_ be reached but...
            return [ 'an unexpected error occured - please file a bug' ]
        version = node.find('version').text
        user = node.find('user').text
        try:
            comment = node.find('comment').text.encode(locale.getpreferredencoding(), 'replace')
        except:
            comment = '<no message>'
        try:
            requestid = node.find('requestid').text.encode(locale.getpreferredencoding(), 'replace')
        except:
            requestid = ""
        t = time.localtime(int(node.find('time').text))
        t = time.strftime('%Y-%m-%d %H:%M:%S', t)

        if format == 'csv':
            s = '%s|%s|%s|%s|%s|%s|%s' % (rev, user, t, srcmd5, version,
                comment.replace('\\', '\\\\').replace('\n', '\\n').replace('|', '\\|'), requestid)
            r.append(s)
        elif format == 'xml':
            r.append('<logentry')
            r.append('   revision="%s" srcmd5="%s">' % (rev, srcmd5))
            r.append('<author>%s</author>' % user)
            r.append('<date>%s</date>' % t)
            r.append('<requestid>%s</requestid>' % requestid)
            r.append('<msg>%s</msg>' %
                comment.replace('&', '&amp;').replace('<', '&gt;').replace('>', '&lt;'))
            r.append('</logentry>')
        else:
            if requestid:
                requestid = "rq" + requestid
            s = '-' * 76 + \
                '\nr%s | %s | %s | %s | %s | %s\n' % (rev, user, t, srcmd5, version, requestid) + \
                '\n' + comment
            r.append(s)

    if format not in ['csv', 'xml']:
        r.append('-' * 76)
    if format == 'xml':
        r.append('</log>')
    return r


def runservice(apiurl, prj, package):
    u = makeurl(apiurl, ['source', prj, package], query={'cmd': 'runservice'})

    try:
        f = http_POST(u)
    except HTTPError as e:
        e.osc_msg = 'could not trigger service run for project \'%s\' package \'%s\'' % (prj, package)
        raise

    root = ET.parse(f).getroot()
    return root.get('code')


def rebuild(apiurl, prj, package, repo, arch, code=None):
    query = { 'cmd': 'rebuild' }
    if package:
        query['package'] = package
    if repo:
        query['repository'] = repo
    if arch:
        query['arch'] = arch
    if code:
        query['code'] = code

    u = makeurl(apiurl, ['build', prj], query=query)
    try:
        f = http_POST(u)
    except HTTPError as e:
        e.osc_msg = 'could not trigger rebuild for project \'%s\' package \'%s\'' % (prj, package)
        raise

    root = ET.parse(f).getroot()
    return root.get('code')


def store_read_project(dir):
    global store

    try:
        p = open(os.path.join(dir, store, '_project')).readlines()[0].strip()
    except IOError:
        msg = 'Error: \'%s\' is not an osc project dir or working copy' % os.path.abspath(dir)
        if os.path.exists(os.path.join(dir, '.svn')):
            msg += '\nTry svn instead of osc.'
        raise oscerr.NoWorkingCopy(msg)
    return p


def store_read_package(dir):
    global store

    try:
        p = open(os.path.join(dir, store, '_package')).readlines()[0].strip()
    except IOError:
        msg = 'Error: \'%s\' is not an osc package working copy' % os.path.abspath(dir)
        if os.path.exists(os.path.join(dir, '.svn')):
            msg += '\nTry svn instead of osc.'
        raise oscerr.NoWorkingCopy(msg)
    return p

def store_read_apiurl(dir, defaulturl=True):
    global store

    fname = os.path.join(dir, store, '_apiurl')
    try:
        url = open(fname).readlines()[0].strip()
        # this is needed to get a proper apiurl
        # (former osc versions may stored an apiurl with a trailing slash etc.)
        apiurl = conf.urljoin(*conf.parse_apisrv_url(None, url))
    except:
        if not defaulturl:
            if is_project_dir(dir):
                project = store_read_project(dir)
                package = None
            elif is_package_dir(dir):
                project = store_read_project(dir)
                package = None
            else:
                msg = 'Error: \'%s\' is not an osc package working copy' % os.path.abspath(dir)
                raise oscerr.NoWorkingCopy(msg)
            msg = 'Your working copy \'%s\' is in an inconsistent state.\n' \
                'Please run \'osc repairwc %s\' (Note this might _remove_\n' \
                'files from the .osc/ dir). Please check the state\n' \
                'of the working copy afterwards (via \'osc status %s\')' % (dir, dir, dir)
            raise oscerr.WorkingCopyInconsistent(project, package, ['_apiurl'], msg)
        apiurl = conf.config['apiurl']
    return apiurl

def store_write_string(dir, file, string, subdir=''):
    global store

    if subdir and not os.path.isdir(os.path.join(dir, store, subdir)):
        os.mkdir(os.path.join(dir, store, subdir))
    fname = os.path.join(dir, store, subdir, file)
    try:
        f = open(fname + '.new', 'w')
        f.write(string)
        f.close()
        os.rename(fname + '.new', fname)
    except:
        if os.path.exists(fname + '.new'):
            os.unlink(fname + '.new')
        raise

def store_write_project(dir, project):
    store_write_string(dir, '_project', project + '\n')

def store_write_apiurl(dir, apiurl):
    store_write_string(dir, '_apiurl', apiurl + '\n')

def store_unlink_file(dir, file):
    global store

    try: os.unlink(os.path.join(dir, store, file))
    except: pass

def store_read_file(dir, file):
    global store

    try:
        content = open(os.path.join(dir, store, file)).read()
        return content
    except:
        return None

def store_write_initial_packages(dir, project, subelements):
    global store

    fname = os.path.join(dir, store, '_packages')
    root = ET.Element('project', name=project)
    for elem in subelements:
        root.append(elem)
    ET.ElementTree(root).write(fname)

def get_osc_version():
    return __version__


def abortbuild(apiurl, project, package=None, arch=None, repo=None):
    return cmdbuild(apiurl, 'abortbuild', project, package, arch, repo)

def restartbuild(apiurl, project, package=None, arch=None, repo=None):
    return cmdbuild(apiurl, 'restartbuild', project, package, arch, repo)

def wipebinaries(apiurl, project, package=None, arch=None, repo=None, code=None):
    return cmdbuild(apiurl, 'wipe', project, package, arch, repo, code)


def cmdbuild(apiurl, cmd, project, package=None, arch=None, repo=None, code=None):
    query = { 'cmd': cmd }
    if package:
        query['package'] = package
    if arch:
        query['arch'] = arch
    if repo:
        query['repository'] = repo
    if code:
        query['code'] = code

    u = makeurl(apiurl, ['build', project], query)
    try:
        f = http_POST(u)
    except HTTPError as e:
        e.osc_msg = '%s command failed for project %s' % (cmd, project)
        if package:
            e.osc_msg += ' package %s' % package
        if arch:
            e.osc_msg += ' arch %s' % arch
        if repo:
            e.osc_msg += ' repository %s' % repo
        if code:
            e.osc_msg += ' code=%s' % code
        raise

    root = ET.parse(f).getroot()
    return root.get('code')


def parseRevisionOption(string):
    """
    returns a tuple which contains the revisions
    """

    if string:
        if ':' in string:
            splitted_rev = string.split(':')
            try:
                for i in splitted_rev:
                    int(i)
                return splitted_rev
            except ValueError:
                print('your revision \'%s\' will be ignored' % string, file=sys.stderr)
                return None, None
        else:
            if string.isdigit():
                return string, None
            elif string.isalnum() and len(string) == 32:
                # could be an md5sum
                return string, None
            else:
                print('your revision \'%s\' will be ignored' % string, file=sys.stderr)
                return None, None
    else:
        return None, None

def checkRevision(prj, pac, revision, apiurl=None, meta=False):
    """
    check if revision is valid revision, i.e. it is not
    larger than the upstream revision id
    """
    if len(revision) == 32:
        # there isn't a way to check this kind of revision for validity
        return True
    if not apiurl:
        apiurl = conf.config['apiurl']
    try:
        if int(revision) > int(show_upstream_rev(apiurl, prj, pac, meta)) \
           or int(revision) <= 0:
            return False
        else:
            return True
    except (ValueError, TypeError):
        return False

def build_table(col_num, data = [], headline = [], width=1, csv = False):
    """
    This method builds a simple table.
    Example1: build_table(2, ['foo', 'bar', 'suse', 'osc'], ['col1', 'col2'], 2)
        col1  col2
        foo   bar
        suse  osc
    """

    longest_col = []
    for i in range(col_num):
        longest_col.append(0)
    if headline and not csv:
        data[0:0] = headline
    # find longest entry in each column
    i = 0
    for itm in data:
        if longest_col[i] < len(itm):
            longest_col[i] = len(itm)
        if i == col_num - 1:
            i = 0
        else:
            i += 1
    # calculate length for each column
    for i, row in enumerate(longest_col):
        longest_col[i] = row + width
    # build rows
    row = []
    table = []
    i = 0
    for itm in data:
        if i % col_num == 0:
            i = 0
            row = []
            table.append(row)
        # there is no need to justify the entries of the last column
        # or when generating csv
        if i == col_num -1 or csv:
            row.append(itm)
        else:
            row.append(itm.ljust(longest_col[i]))
        i += 1
    if csv:
        separator = '|'
    else:
        separator = ''
    return [separator.join(row) for row in table]

def xpath_join(expr, new_expr, op='or', inner=False, nexpr_parentheses=False):
    """
    Join two xpath expressions. If inner is False expr will
    be surrounded with parentheses (unless it's not already
    surrounded). If nexpr_parentheses is True new_expr will be
    surrounded with parentheses.
    """
    if not expr:
        return new_expr
    elif not new_expr:
        return expr
    # NOTE: this is NO syntax check etc. (e.g. if a literal contains a '(' or ')'
    #       the check might fail and expr will be surrounded with parentheses or NOT)
    parentheses = not inner
    if not inner and expr.startswith('(') and expr.endswith(')'):
        parentheses = False
        braces = [i for i in expr if i == '(' or i == ')']
        closed = 0
        while len(braces):
            if braces.pop() == ')':
                closed += 1
                continue
            else:
                closed += -1
            while len(braces):
                if braces.pop() == '(':
                    closed += -1
                else:
                    closed += 1
            if closed != 0:
                parentheses = True
                break
    if parentheses:
        expr = '(%s)' % expr
    if nexpr_parentheses:
        new_expr = '(%s)' % new_expr
    return '%s %s %s' % (expr, op, new_expr)

def search(apiurl, **kwargs):
    """
    Perform a search request. The requests are constructed as follows:
    kwargs = {'kind1' => xpath1, 'kind2' => xpath2, ..., 'kindN' => xpathN}
    GET /search/kind1?match=xpath1
    ...
    GET /search/kindN?match=xpathN
    """
    res = {}
    for urlpath, xpath in kwargs.items():
        path = [ 'search' ]
        path += urlpath.split('_') # FIXME: take underscores as path seperators. I see no other way atm to fix OBS api calls and not breaking osc api
        u = makeurl(apiurl, path, ['match=%s' % quote_plus(xpath)])
        f = http_GET(u)
        res[urlpath] = ET.parse(f).getroot()
    return res

def owner(apiurl, binary, mode="binary", attribute=None, project=None, usefilter=None, devel=None, limit=None):
    """
    Perform a binary package owner search. This is supported since OBS 2.4.
    """
    # find default project, if not specified
    query = { mode: binary }
    if attribute:
        query['attribute'] = attribute
    if project:
        query['project'] = project
    if devel:
        query['devel'] = devel
    if limit != None:
        query['limit'] = limit
    if usefilter != None:
        query['filter'] = ",".join(usefilter)
    u = makeurl(apiurl, [ 'search', 'owner' ], query)
    res = None
    try:
        f = http_GET(u)
        res = ET.parse(f).getroot()
    except HTTPError as e:
        # old server not supporting this search
        pass
    return res

def set_link_rev(apiurl, project, package, revision='', expand=False):
    url = makeurl(apiurl, ['source', project, package, '_link'])
    try:
        f = http_GET(url)
        root = ET.parse(f).getroot()
    except HTTPError as e:
        e.osc_msg = 'Unable to get _link file in package \'%s\' for project \'%s\'' % (package, project)
        raise
    revision = _set_link_rev(apiurl, project, package, root, revision, expand=expand)
    l = ET.tostring(root, encoding=ET_ENCODING)
    http_PUT(url, data=l)
    return revision

def _set_link_rev(apiurl, project, package, root, revision='', expand=False):
    """
    Updates the rev attribute of the _link xml. If revision is set to None
    the rev and vrev attributes are removed from the _link xml.
    updates the rev attribute of the _link xml. If revision is the empty
    string the latest rev of the link's source package is used (or the
    xsrcmd5 if expand is True). If revision is neither None nor the empty
    string the _link's rev attribute is set to this revision (or to the
    xsrcmd5 if expand is True).
    """
    src_project = root.get('project', project)
    src_package = root.get('package', package)
    vrev = None
    if revision is None:
        if 'rev' in root.keys():
            del root.attrib['rev']
        if 'vrev' in root.keys():
            del root.attrib['vrev']
    elif not revision or expand:
        revision, vrev = show_upstream_rev_vrev(apiurl, src_project, src_package, revision=revision, expand=expand)

    if revision:
        root.set('rev', revision)
    # add vrev when revision is a srcmd5
    if vrev is not None and revision is not None and len(revision) >= 32:
        root.set('vrev', vrev)
    return revision


def delete_dir(dir):
    # small security checks
    if os.path.islink(dir):
        raise oscerr.OscIOError(None, 'cannot remove linked dir')
    elif os.path.abspath(dir) == '/':
        raise oscerr.OscIOError(None, 'cannot remove \'/\'')

    for dirpath, dirnames, filenames in os.walk(dir, topdown=False):
        for filename in filenames:
            os.unlink(os.path.join(dirpath, filename))
        for dirname in dirnames:
            os.rmdir(os.path.join(dirpath, dirname))
    os.rmdir(dir)


def delete_storedir(store_dir):
    """
    This method deletes a store dir.
    """
    head, tail = os.path.split(store_dir)
    if tail == '.osc':
        delete_dir(store_dir)

def unpack_srcrpm(srpm, dir, *files):
    """
    This method unpacks the passed srpm into the
    passed dir. If arguments are passed to the \'files\' tuple
    only this files will be unpacked.
    """
    if not is_srcrpm(srpm):
        print('error - \'%s\' is not a source rpm.' % srpm, file=sys.stderr)
        sys.exit(1)
    curdir = os.getcwd()
    if os.path.isdir(dir):
        os.chdir(dir)
    cmd = 'rpm2cpio %s | cpio -i %s &> /dev/null' % (srpm, ' '.join(files))
    ret = run_external(cmd, shell=True)
    if ret != 0:
        print('error \'%s\' - cannot extract \'%s\'' % (ret, srpm), file=sys.stderr)
        sys.exit(1)
    os.chdir(curdir)

def is_rpm(f):
    """check if the named file is an RPM package"""
    try:
        h = open(f, 'rb').read(4)
    except:
        return False

    if h == '\xed\xab\xee\xdb':
        return True
    else:
        return False

def is_srcrpm(f):
    """check if the named file is a source RPM"""

    if not is_rpm(f):
        return False

    try:
        h = open(f, 'rb').read(8)
    except:
        return False

    if h[7] == '\x01':
        return True
    else:
        return False

def addMaintainer(apiurl, prj, pac, user):
    # for backward compatibility only
    addPerson(apiurl, prj, pac, user)

def addPerson(apiurl, prj, pac, user, role="maintainer"):
    """ add a new person to a package or project """
    path = quote_plus(prj),
    kind = 'prj'
    if pac:
        path = path + (quote_plus(pac),)
        kind = 'pkg'
    data = meta_exists(metatype=kind,
                       path_args=path,
                       template_args=None,
                       create_new=False)

    if data and get_user_meta(apiurl, user) != None:
        root = ET.fromstring(''.join(data))
        found = False
        for person in root.getiterator('person'):
            if person.get('userid') == user and person.get('role') == role:
                found = True
                print("user already exists")
                break
        if not found:
            # the xml has a fixed structure
            root.insert(2, ET.Element('person', role=role, userid=user))
            print('user \'%s\' added to \'%s\'' % (user, pac or prj))
            edit_meta(metatype=kind,
                      path_args=path,
                      data=ET.tostring(root, encoding=ET_ENCODING))
    else:
        print("osc: an error occured")

def delMaintainer(apiurl, prj, pac, user):
    # for backward compatibility only
    delPerson(apiurl, prj, pac, user)

def delPerson(apiurl, prj, pac, user, role="maintainer"):
    """ delete a person from a package or project """
    path = quote_plus(prj),
    kind = 'prj'
    if pac:
        path = path + (quote_plus(pac), )
        kind = 'pkg'
    data = meta_exists(metatype=kind,
                       path_args=path,
                       template_args=None,
                       create_new=False)
    if data and get_user_meta(apiurl, user) != None:
        root = ET.fromstring(''.join(data))
        found = False
        for person in root.getiterator('person'):
            if person.get('userid') == user and person.get('role') == role:
                root.remove(person)
                found = True
                print("user \'%s\' removed" % user)
        if found:
            edit_meta(metatype=kind,
                      path_args=path,
                      data=ET.tostring(root, encoding=ET_ENCODING))
        else:
            print("user \'%s\' not found in \'%s\'" % (user, pac or prj))
    else:
        print("an error occured")

def setBugowner(apiurl, prj, pac, user=None, group=None):
    """ delete all bugowners (user and group entries) and set one new one in a package or project """
    path = quote_plus(prj),
    kind = 'prj'
    if pac:
        path = path + (quote_plus(pac), )
        kind = 'pkg'
    data = meta_exists(metatype=kind,
                       path_args=path,
                       template_args=None,
                       create_new=False)
    if user.startswith('group:'):
        group=user.replace('group:','')
        user=None
    if data:
        root = ET.fromstring(''.join(data))
        for group_element in root.getiterator('group'):
            if  group_element.get('role') == "bugowner":
                root.remove(group_element)
        for person_element in root.getiterator('person'):
            if person_element.get('role') == "bugowner":
                root.remove(person_element)
        if user:
            root.insert(2, ET.Element('person', role='bugowner', userid=user))
        elif group:
            root.insert(2, ET.Element('group', role='bugowner', groupid=group))
        else:
            print("Neither user nor group is specified")
        edit_meta(metatype=kind,
                  path_args=path,
                  data=ET.tostring(root, encoding=ET_ENCODING))

def setDevelProject(apiurl, prj, pac, dprj, dpkg=None):
    """ set the <devel project="..."> element to package metadata"""
    path = (quote_plus(prj),) + (quote_plus(pac),)
    data = meta_exists(metatype='pkg',
                       path_args=path,
                       template_args=None,
                       create_new=False)

    if data and show_project_meta(apiurl, dprj) != None:
        root = ET.fromstring(''.join(data))
        if not root.find('devel') != None:
            ET.SubElement(root, 'devel')
        elem = root.find('devel')
        if dprj:
            elem.set('project', dprj)
        else:
            if 'project' in elem.keys():
                del elem.attrib['project']
        if dpkg:
            elem.set('package', dpkg)
        else:
            if 'package' in elem.keys():
                del elem.attrib['package']
        edit_meta(metatype='pkg',
                  path_args=path,
                  data=ET.tostring(root, encoding=ET_ENCODING))
    else:
        print("osc: an error occured")

def createPackageDir(pathname, prj_obj=None):
    """
    create and initialize a new package dir in the given project.
    prj_obj can be a Project() instance.
    """
    prj_dir, pac_dir = getPrjPacPaths(pathname)
    if is_project_dir(prj_dir):
        global store
        if not os.path.exists(pac_dir+store):
            prj = prj_obj or Project(prj_dir, False)
            Package.init_package(prj.apiurl, prj.name, pac_dir, pac_dir)
            prj.addPackage(pac_dir)
            print(statfrmt('A', os.path.normpath(pathname)))
        else:
            raise oscerr.OscIOError(None, 'file or directory \'%s\' already exists' % pathname)
    else:
        msg = '\'%s\' is not a working copy' % prj_dir
        if os.path.exists(os.path.join(prj_dir, '.svn')):
            msg += '\ntry svn instead of osc.'
        raise oscerr.NoWorkingCopy(msg)


def stripETxml(node):
    node.tail = None
    if node.text != None:
        node.text = node.text.replace(" ", "").replace("\n", "")
    for child in node.getchildren():
        stripETxml(child)

def addGitSource(url):
    service_file = os.path.join(os.getcwd(), '_service')
    addfile = False
    if os.path.exists( service_file ):
        services = ET.parse(os.path.join(os.getcwd(), '_service')).getroot()
    else:
        services = ET.fromstring("<services />")
        addfile = True
    stripETxml( services )
    si = Serviceinfo()
    s = si.addGitUrl(services, url)
    s = si.addRecompressTar(services)
    si.read(s)

    # for pretty output
    xmlindent(s)
    f = open(service_file, 'wb')
    f.write(ET.tostring(s, encoding=ET_ENCODING))
    f.close()
    if addfile:
        addFiles( ['_service'] )

def addDownloadUrlService(url):
    service_file = os.path.join(os.getcwd(), '_service')
    addfile = False
    if os.path.exists( service_file ):
        services = ET.parse(os.path.join(os.getcwd(), '_service')).getroot()
    else:
        services = ET.fromstring("<services />")
        addfile = True
    stripETxml( services )
    si = Serviceinfo()
    s = si.addDownloadUrl(services, url)
    si.read(s)

    # for pretty output
    xmlindent(s)
    f = open(service_file, 'wb')
    f.write(ET.tostring(s, encoding=ET_ENCODING))
    f.close()
    if addfile:
        addFiles( ['_service'] )

    # download file
    path = os.getcwd()
    files = os.listdir(path)
    si.execute(path)
    newfiles = os.listdir(path)

    # add verify service for new files
    for filename in files:
        newfiles.remove(filename)

    for filename in newfiles:
        if filename.startswith('_service:download_url:'):
            s = si.addVerifyFile(services, filename)

    # for pretty output
    xmlindent(s)
    f = open(service_file, 'wb')
    f.write(ET.tostring(s, encoding=ET_ENCODING))
    f.close()


def addFiles(filenames, prj_obj = None):
    for filename in filenames:
        if not os.path.exists(filename):
            raise oscerr.OscIOError(None, 'file \'%s\' does not exist' % filename)

    # init a package dir if we have a normal dir in the "filenames"-list
    # so that it will be find by findpacs() later
    pacs = list(filenames)
    for filename in filenames:
        prj_dir, pac_dir = getPrjPacPaths(filename)
        if not is_package_dir(filename) and os.path.isdir(filename) and is_project_dir(prj_dir) \
           and conf.config['do_package_tracking']:
            prj_name = store_read_project(prj_dir)
            prj_apiurl = store_read_apiurl(prj_dir, defaulturl=False)
            Package.init_package(prj_apiurl, prj_name, pac_dir, filename)
        elif is_package_dir(filename) and conf.config['do_package_tracking']:
            raise oscerr.PackageExists(store_read_project(filename), store_read_package(filename),
                                       'osc: warning: \'%s\' is already under version control' % filename)
        elif os.path.isdir(filename) and is_project_dir(prj_dir):
            raise oscerr.WrongArgs('osc: cannot add a directory to a project unless ' \
                                   '\'do_package_tracking\' is enabled in the configuration file')
        elif os.path.isdir(filename):
            print('skipping directory \'%s\'' % filename)
            pacs.remove(filename)
    pacs = findpacs(pacs)
    for pac in pacs:
        if conf.config['do_package_tracking'] and not pac.todo:
            prj = prj_obj or Project(os.path.dirname(pac.absdir), False)
            if pac.name in prj.pacs_unvers:
                prj.addPackage(pac.name)
                print(statfrmt('A', getTransActPath(os.path.join(pac.dir, os.pardir, pac.name))))
                for filename in pac.filenamelist_unvers:
                    if os.path.isdir(os.path.join(pac.dir, filename)):
                        print('skipping directory \'%s\'' % os.path.join(pac.dir, filename))
                    else:
                        pac.todo.append(filename)
            elif pac.name in prj.pacs_have:
                print('osc: warning: \'%s\' is already under version control' % pac.name)
        for filename in pac.todo:
            if filename in pac.skipped:
                continue
            if filename in pac.excluded:
                print('osc: warning: \'%s\' is excluded from a working copy' % filename, file=sys.stderr)
                continue
            pac.addfile(filename)

def getPrjPacPaths(path):
    """
    returns the path for a project and a package
    from path. This is needed if you try to add
    or delete packages:
    Examples:
        osc add pac1/: prj_dir = CWD;
                       pac_dir = pac1
        osc add /path/to/pac1:
                       prj_dir = path/to;
                       pac_dir = pac1
        osc add /path/to/pac1/file
                       => this would be an invalid path
                          the caller has to validate the returned
                          path!
    """
    # make sure we hddave a dir: osc add bar vs. osc add bar/; osc add /path/to/prj_dir/new_pack
    # filename = os.path.join(tail, '')
    prj_dir, pac_dir = os.path.split(os.path.normpath(path))
    if prj_dir == '':
        prj_dir = os.getcwd()
    return (prj_dir, pac_dir)

def getTransActPath(pac_dir):
    """
    returns the path for the commit and update operations/transactions.
    Normally the "dir" attribute of a Package() object will be passed to
    this method.
    """
    if pac_dir != '.':
        pathn = os.path.normpath(pac_dir)
    else:
        pathn = ''
    return pathn

def get_commit_message_template(pac):
    """
    Read the difference in .changes file(s) and put them as a template to commit message.
    """
    diff = []
    template = []

    if pac.todo:
        todo = pac.todo
    else:
        todo = pac.filenamelist + pac.filenamelist_unvers

    files = [i for i in todo if i.endswith('.changes') and pac.status(i) in ('A', 'M')]

    for filename in files:
        if pac.status(filename) == 'M':
            diff += get_source_file_diff(pac.absdir, filename, pac.rev)
        elif pac.status(filename) == 'A':
            f = open(os.path.join(pac.absdir, filename), 'r')
            for line in f:
                diff += '+' + line
            f.close()

    if diff:
        template = parse_diff_for_commit_message(''.join(diff))

    return template

def parse_diff_for_commit_message(diff, template = []):
    date_re = re.compile(r'\+(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2}) ( ?[0-9]|[0-3][0-9]) .*')
    diff = diff.split('\n')

    # The first four lines contains a header of diff
    for line in diff[3:]:
        # this condition is magical, but it removes all unwanted lines from commit message
        if not(line) or (line and line[0] != '+') or \
        date_re.match(line) or \
        line == '+' or line[0:3] == '+++':
            continue

        if line == '+-------------------------------------------------------------------':
            template.append('')
        else:
            template.append(line[1:])

    return template

def get_commit_msg(wc_dir, pacs):
    template = store_read_file(wc_dir, '_commit_msg')
    # open editor for commit message
    # but first, produce status and diff to append to the template
    footer = []
    lines = []
    for p in pacs:
        states = sorted(p.get_status(False, ' ', '?'), lambda x, y: cmp(x[1], y[1]))
        changed = [statfrmt(st, os.path.normpath(os.path.join(p.dir, filename))) for st, filename in states]
        if changed:
            footer += changed
            footer.append('\nDiff for working copy: %s' % p.dir)
            footer.extend([''.join(i) for i in p.get_diff(ignoreUnversioned=True)])
            lines.extend(get_commit_message_template(p))
    if template is None:
        if lines and lines[0] == '':
            del lines[0]
        template = '\n'.join(lines)
    msg = ''
    # if footer is empty, there is nothing to commit, and no edit needed.
    if footer:
        msg = edit_message(footer='\n'.join(footer), template=template)
    if msg:
        store_write_string(wc_dir, '_commit_msg', msg + '\n')
    else:
        store_unlink_file(wc_dir, '_commit_msg')
    return msg

def print_request_list(apiurl, project, package = None, states = ('new', 'review', ), force = False):
    """
    prints list of pending requests for the specified project/package if "check_for_request_on_action"
    is enabled in the config or if "force" is set to True
    """
    if not conf.config['check_for_request_on_action'] and not force:
        return
    requests = get_request_list(apiurl, project, package, req_state=states)
    msg = 'Pending requests for %s: %s (%s)'
    if package is None and len(requests):
        print(msg % ('project', project, len(requests)))
    elif len(requests):
        print(msg % ('package', '/'.join([project, package]), len(requests)))
    for r in requests:
        print(r.list_view(), '\n')

def request_interactive_review(apiurl, request, initial_cmd='', group=None, ignore_reviews=False):
    """review the request interactively"""
    import tempfile, re

    tmpfile = None

    def safe_change_request_state(*args, **kwargs):
        try:
            change_request_state(*args, **kwargs)
            return True
        except HTTPError as e:
            print('Server returned an error:', e, file=sys.stderr)
            print('Try -f to force the state change', file=sys.stderr)
        return False

    def print_request(request):
        print(request)

    print_request(request)
    try:
        prompt = '(a)ccept/(d)ecline/(r)evoke/c(l)one/(s)kip/(c)ancel > '
        editable_actions = request.get_actions('submit', 'maintenance_incident')
        # actions which have sources + buildresults
        src_actions = editable_actions + request.get_actions('maintenance_release')
        if editable_actions:
            prompt = 'd(i)ff/(a)ccept/(d)ecline/(r)evoke/(b)uildstatus/c(l)one/(e)dit/(s)kip/(c)ancel > '
        elif src_actions:
            # no edit for maintenance release requests
            prompt = 'd(i)ff/(a)ccept/(d)ecline/(r)evoke/(b)uildstatus/c(l)one/(s)kip/(c)ancel > '
        editprj = ''
        orequest = None
        while True:
            if initial_cmd:
                repl = initial_cmd
                initial_cmd = ''
            else:
                repl = raw_input(prompt).strip()
            if repl == 'i' and src_actions:
                if not orequest is None and tmpfile:
                    tmpfile.close()
                    tmpfile = None
                if tmpfile is None:
                    tmpfile = tempfile.NamedTemporaryFile(suffix='.diff')
                    try:
                        diff = request_diff(apiurl, request.reqid)
                        tmpfile.write(diff)
                    except HTTPError as e:
                        if e.code != 400:
                            raise
                        # backward compatible diff for old apis
                        for action in src_actions:
                            diff = 'old: %s/%s\nnew: %s/%s\n' % (action.src_project, action.src_package,
                                action.tgt_project, action.tgt_package)
                            diff += submit_action_diff(apiurl, action)
                            diff += '\n\n'
                            tmpfile.write(diff)
                    tmpfile.flush()
                run_editor(tmpfile.name)
                print_request(request)
            elif repl == 's':
                print('skipping: #%s' % request.reqid, file=sys.stderr)
                break
            elif repl == 'c':
                print('Aborting', file=sys.stderr)
                raise oscerr.UserAbort()
            elif repl == 'b' and src_actions:
                for action in src_actions:
                    print('%s/%s:' % (action.src_project, action.src_package))
                    print('\n'.join(get_results(apiurl, action.src_project, action.src_package)))
            elif repl == 'e' and editable_actions:
                # this is only for editable actions
                if not editprj:
                    editprj = clone_request(apiurl, request.reqid, 'osc editrequest')
                    orequest = request
                request = edit_submitrequest(apiurl, editprj, orequest, request)
                src_actions = editable_actions = request.get_actions('submit', 'maintenance_incident')
                print_request(request)
                prompt = 'd(i)ff/(a)ccept/(b)uildstatus/(e)dit/(s)kip/(c)ancel > '
            else:
                state_map = {'a': 'accepted', 'd': 'declined', 'r': 'revoked'}
                mo = re.search('^([adrl])(?:\s+(-f)?\s*-m\s+(.*))?$', repl)
                if mo is None or orequest and mo.group(1) != 'a':
                    print('invalid choice: \'%s\'' % repl, file=sys.stderr)
                    continue
                state = state_map.get(mo.group(1))
                force = mo.group(2) is not None
                msg = mo.group(3)
                footer = ''
                msg_template = ''
                if not (state is None or request.state is None):
                    footer = 'changing request from state \'%s\' to \'%s\'\n\n' \
                        % (request.state.name, state)
                    msg_template = change_request_state_template(request, state)
                footer += str(request)
                if tmpfile is not None:
                    tmpfile.seek(0)
                    # the read bytes probably have a moderate size so the str won't be too large
                    footer += '\n\n' + tmpfile.read()
                if msg is None:
                    try:
                        msg = edit_message(footer = footer, template=msg_template)
                    except oscerr.UserAbort:
                        # do not abort (show prompt again)
                        continue
                else:
                    msg = msg.strip('\'').strip('"')
                if not orequest is None:
                    request.create(apiurl)
                    if not safe_change_request_state(apiurl, request.reqid, 'accepted', msg, force=force):
                        # an error occured
                        continue
                    repl = raw_input('Supersede original request? (y|N) ')
                    if repl in ('y', 'Y'):
                        safe_change_request_state(apiurl, orequest.reqid, 'superseded',
                            'superseded by %s' % request.reqid, request.reqid, force=force)
                elif state is None:
                    clone_request(apiurl, request.reqid, msg)
                else:
                    reviews = [r for r in request.reviews if r.state == 'new']
                    if not reviews or ignore_reviews:
                        if safe_change_request_state(apiurl, request.reqid, state, msg, force=force):
                            break
                        else:
                            # an error occured
                            continue
                    group_reviews = [r for r in reviews if (r.by_group is not None
                                                            and r.by_group == group)]
                    if len(group_reviews) == 1 and conf.config['review_inherit_group']:
                        review = group_reviews[0]
                    else:
                        print('Please chose one of the following reviews:')
                        for i in range(len(reviews)):
                            fmt = Request.format_review(reviews[i])
                            print('(%i)' % i, 'by %(type)-10s %(by)s' % fmt)
                        num = raw_input('> ')
                        try:
                            num = int(num)
                        except ValueError:
                            print('\'%s\' is not a number.' % num)
                            continue
                        if num < 0 or num >= len(reviews):
                            print('number \'%s\' out of range.' % num)
                            continue
                        review = reviews[num]
                    change_review_state(apiurl, request.reqid, state, by_user=review.by_user,
                                        by_group=review.by_group, by_project=review.by_project,
                                        by_package=review.by_package, message=msg)
                break
    finally:
        if tmpfile is not None:
            tmpfile.close()

def edit_submitrequest(apiurl, project, orequest, new_request=None):
    """edit a submit action from orequest/new_request"""
    import tempfile, shutil
    actions = orequest.get_actions('submit')
    oactions = actions
    if new_request is not None:
        actions = new_request.get_actions('submit')
    num = 0
    if len(actions) > 1:
        print('Please chose one of the following submit actions:')
        for i in range(len(actions)):
            # it is safe to use orequest because currently the formatting
            # of a submit action does not need instance specific data
            fmt = orequest.format_action(actions[i])
            print('(%i)' % i, '%(source)s  %(target)s' % fmt)
        num = raw_input('> ')
        try:
            num = int(num)
        except ValueError:
            raise oscerr.WrongArgs('\'%s\' is not a number.' % num)
        if num < 0 or num >= len(orequest.actions):
            raise oscerr.WrongArgs('number \'%s\' out of range.' % num)

    # the api replaced ':' with '_' in prj and pkg names (clone request)
    package = '%s.%s' % (oactions[num].src_package.replace(':', '_'),
        oactions[num].src_project.replace(':', '_'))
    tmpdir = None
    cleanup = True
    try:
        tmpdir = tempfile.mkdtemp(prefix='osc_editsr')
        p = Package.init_package(apiurl, project, package, tmpdir)
        p.update()
        shell = os.getenv('SHELL', default='/bin/sh')
        olddir = os.getcwd()
        os.chdir(tmpdir)
        print('Checked out package \'%s\' to %s. Started a new shell (%s).\n' \
            'Please fix the package and close the shell afterwards.' % (package, tmpdir, shell))
        run_external(shell)
        # the pkg might have uncommitted changes...
        cleanup = False
        os.chdir(olddir)
        # reread data
        p = Package(tmpdir)
        modified = p.get_status(False, ' ', '?', 'S')
        if modified:
            print('Your working copy has the following modifications:')
            print('\n'.join([statfrmt(st, filename) for st, filename in modified]))
            repl = raw_input('Do you want to commit the local changes first? (y|N) ')
            if repl in ('y', 'Y'):
                msg = get_commit_msg(p.absdir, [p])
                p.commit(msg=msg)
        cleanup = True
    finally:
        if cleanup:
            shutil.rmtree(tmpdir)
        else:
            print('Please remove the dir \'%s\' manually' % tmpdir)
    r = Request()
    for action in orequest.get_actions():
        new_action = Action.from_xml(action.to_xml())
        r.actions.append(new_action)
        if new_action.type == 'submit':
            new_action.src_package = '%s.%s' % (action.src_package.replace(':', '_'),
                action.src_project.replace(':', '_'))
            new_action.src_project = project
            # do an implicit cleanup
            new_action.opt_sourceupdate = 'cleanup'
    return r

def get_user_projpkgs(apiurl, user, role=None, exclude_projects=[], proj=True, pkg=True, maintained=False, metadata=False):
    """Return all project/packages where user is involved."""
    xpath = 'person/@userid = \'%s\'' % user
    excl_prj = ''
    excl_pkg = ''
    for i in exclude_projects:
        excl_prj = xpath_join(excl_prj, 'not(@name = \'%s\')' % i, op='and')
        excl_pkg = xpath_join(excl_pkg, 'not(@project = \'%s\')' % i, op='and')
    role_filter_xpath = xpath
    if role:
        xpath = xpath_join(xpath, 'person/@role = \'%s\'' % role, inner=True, op='and')
    xpath_pkg = xpath_join(xpath, excl_pkg, op='and')
    xpath_prj = xpath_join(xpath, excl_prj, op='and')

    if maintained:
        xpath_pkg = xpath_join(xpath_pkg, '(project/attribute/@name=\'%(attr)s\' or attribute/@name=\'%(attr)s\')' % {'attr': conf.config['maintained_attribute']}, op='and')

    what = {}
    if pkg:
        if metadata:
            what['package'] = xpath_pkg
        else:
            what['package_id'] = xpath_pkg
    if proj:
        if metadata:
            what['project'] = xpath_prj
        else:
            what['project_id'] = xpath_prj
    try:
        res = search(apiurl, **what)
    except HTTPError as e:
        if e.code != 400 or not role_filter_xpath:
            raise e
        # backward compatibility: local role filtering
        what = dict([[kind, role_filter_xpath] for kind in what.keys()])
        if 'package' in what:
            what['package'] = xpath_join(role_filter_xpath, excl_pkg, op='and')
        if 'project' in what:
            what['project'] = xpath_join(role_filter_xpath, excl_prj, op='and')
        res = search(apiurl, **what)
        filter_role(res, user, role)
    return res

def raw_input(*args):
    try:
        import builtins
        func = builtins.input
    except ImportError:
        #python 2.7
        import __builtin__
        func = __builtin__.raw_input

    try:
        return func(*args)
    except EOFError:
        # interpret ctrl-d as user abort
        raise oscerr.UserAbort()

def run_external(filename, *args, **kwargs):
    """Executes the program filename via subprocess.call.

    *args are additional arguments which are passed to the
    program filename. **kwargs specify additional arguments for
    the subprocess.call function.
    if no args are specified the plain filename is passed
    to subprocess.call (this can be used to execute a shell
    command). Otherwise [filename] + list(args) is passed
    to the subprocess.call function.

    """
    # unless explicitly specified use shell=False
    kwargs.setdefault('shell', False)
    if args:
        cmd = [filename] + list(args)
    else:
        cmd = filename
    try:
        return subprocess.call(cmd, **kwargs)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        raise oscerr.ExtRuntimeError(e.strerror, filename)

# backward compatibility: local role filtering
def filter_role(meta, user, role):
    """
    remove all project/package nodes if no person node exists
    where @userid=user and @role=role
    """
    for kind, root in meta.items():
        delete = []
        for node in root.findall(kind):
            found = False
            for p in node.findall('person'):
                if p.get('userid') == user and p.get('role') == role:
                    found = True
                    break
            if not found:
                delete.append(node)
        for node in delete:
            root.remove(node)

def find_default_project(apiurl=None, package=None):
    """"
    look though the list of conf.config['getpac_default_project']
    and find the first project where the given package exists in the build service.
    """
    if not len(conf.config['getpac_default_project']):
        return None
    candidates = re.split('[, ]+', conf.config['getpac_default_project'])
    if package is None or len(candidates) == 1:
        return candidates[0]

    # search through the list, where package exists ...
    for prj in candidates:
        try:
            # any fast query will do here.
            show_package_meta(apiurl, prj, package)
            return prj
        except HTTPError: 
            pass
    return None

def utime(filename, arg, ignore_einval=True):
    """wrapper around os.utime which ignore errno EINVAL by default"""
    try:
        # workaround for bnc#857610): if filename resides on a nfs share
        # os.utime might raise EINVAL
        os.utime(filename, arg)
    except OSError as e:
        if e.errno == errno.EINVAL and ignore_einval:
            return
        raise

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = fetch
# Copyright (C) 2006 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.

from __future__ import print_function

import sys, os

try:
    from urllib.parse import quote_plus
    from urllib.request import HTTPBasicAuthHandler, HTTPCookieProcessor, HTTPPasswordMgrWithDefaultRealm, HTTPError
except ImportError:
    #python 2.x
    from urllib import quote_plus
    from urllib2 import HTTPBasicAuthHandler, HTTPCookieProcessor, HTTPPasswordMgrWithDefaultRealm, HTTPError

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.mirror import MirrorGroup
from .core import makeurl, streamfile
from .util import packagequery, cpio
from . import conf
from . import oscerr
import tempfile
import re
try:
    from .meter import TextMeter
except:
    TextMeter = None


def join_url(self, base_url, rel_url):
    """to override _join_url of MirrorGroup, because we want to
    pass full URLs instead of base URL where relative_url is added later...
    IOW, we make MirrorGroup ignore relative_url
    """
    return base_url


class OscFileGrabber(URLGrabber):
    def __init__(self, progress_obj=None):
        # we cannot use super because we still have to support
        # older urlgrabber versions where URLGrabber is an old-style class
        URLGrabber.__init__(self)
        self.progress_obj = progress_obj

    def urlgrab(self, url, filename, text=None, **kwargs):
        if url.startswith('file://'):
            f = url.replace('file://', '', 1)
            if os.path.isfile(f):
                return f
            else:
                raise URLGrabError(2, 'Local file \'%s\' does not exist' % f)
        with file(filename, 'wb') as f:
            try:
                for i in streamfile(url, progress_obj=self.progress_obj,
                                    text=text):
                    f.write(i)
            except HTTPError as e:
                exc = URLGrabError(14, str(e))
                exc.url = url
                exc.exception = e
                exc.code = e.code
                raise exc
            except IOError as e:
                raise URLGrabError(4, str(e))
        return filename


class Fetcher:
    def __init__(self, cachedir='/tmp', api_host_options={}, urllist=[],
            http_debug=False, cookiejar=None, offline=False, enable_cpio=True):
        # set up progress bar callback
        if sys.stdout.isatty() and TextMeter:
            self.progress_obj = TextMeter(fo=sys.stdout)
        else:
            self.progress_obj = None

        self.cachedir = cachedir
        self.urllist = urllist
        self.http_debug = http_debug
        self.offline = offline
        self.cpio = {}
        self.enable_cpio = enable_cpio

        passmgr = HTTPPasswordMgrWithDefaultRealm()
        for host in api_host_options:
            passmgr.add_password(None, host, api_host_options[host]['user'],
                                 api_host_options[host]['pass'])
        openers = (HTTPBasicAuthHandler(passmgr), )
        if cookiejar:
            openers += (HTTPCookieProcessor(cookiejar), )
        self.gr = OscFileGrabber(progress_obj=self.progress_obj)

    def failureReport(self, errobj):
        """failure output for failovers from urlgrabber"""
        if errobj.url.startswith('file://'):
            return {}
        print('Trying openSUSE Build Service server for %s (%s), not found at %s.'
              % (self.curpac, self.curpac.project, errobj.url.split('/')[2]))
        return {}

    def __add_cpio(self, pac):
        prpap = '%s/%s/%s/%s' % (pac.project, pac.repository, pac.repoarch, pac.repopackage)
        self.cpio.setdefault(prpap, {})[pac.repofilename] = pac

    def __download_cpio_archive(self, apiurl, project, repo, arch, package, **pkgs):
        if not pkgs:
            return
        query = ['binary=%s' % quote_plus(i) for i in pkgs]
        query.append('view=cpio')
        try:
            url = makeurl(apiurl, ['build', project, repo, arch, package], query=query)
            sys.stdout.write("preparing download ...\r")
            sys.stdout.flush()
            with tempfile.NamedTemporaryFile(prefix='osc_build_cpio') as tmparchive:
                self.gr.urlgrab(url, filename=tmparchive.name,
                                text='fetching packages for \'%s\'' % project)
                archive = cpio.CpioRead(tmparchive.name)
                archive.read()
                for hdr in archive:
                    # XXX: we won't have an .errors file because we're using
                    # getbinarylist instead of the public/... route
                    # (which is routed to getbinaries)
                    # getbinaries does not support kiwi builds
                    if hdr.filename == '.errors':
                        archive.copyin_file(hdr.filename)
                        raise oscerr.APIError('CPIO archive is incomplete '
                                              '(see .errors file)')
                    if package == '_repository':
                        n = re.sub(r'\.pkg\.tar\..z$', '.arch', hdr.filename)
                        pac = pkgs[n.rsplit('.', 1)[0]]
                    else:
                        # this is a kiwi product
                        pac = pkgs[hdr.filename]

                    # Extract a single file from the cpio archive
                    try:
                        fd, tmpfile = tempfile.mkstemp(prefix='osc_build_file')
                        archive.copyin_file(hdr.filename,
                                            os.path.dirname(tmpfile),
                                            os.path.basename(tmpfile))
                        self.move_package(tmpfile, pac.localdir, pac)
                    finally:
                        os.close(fd)
                        if os.path.exists(tmpfile):
                            os.unlink(tmpfile)

                for pac in pkgs.values():
                    if not os.path.isfile(pac.fullfilename):
                        raise oscerr.APIError('failed to fetch file \'%s\': '
                                              'missing in CPIO archive' %
                                              pac.repofilename)
        except URLGrabError as e:
            if e.errno != 14 or e.code != 414:
                raise
            # query str was too large
            keys = list(pkgs.keys())
            if len(keys) == 1:
                raise oscerr.APIError('unable to fetch cpio archive: '
                                      'server always returns code 414')
            n = len(pkgs) / 2
            new_pkgs = dict([(k, pkgs[k]) for k in keys[:n]])
            self.__download_cpio_archive(apiurl, project, repo, arch,
                                         package, **new_pkgs)
            new_pkgs = dict([(k, pkgs[k]) for k in keys[n:]])
            self.__download_cpio_archive(apiurl, project, repo, arch,
                                         package, **new_pkgs)

    def __fetch_cpio(self, apiurl):
        for prpap, pkgs in self.cpio.items():
            project, repo, arch, package = prpap.split('/', 3)
            self.__download_cpio_archive(apiurl, project, repo, arch, package, **pkgs)

    def fetch(self, pac, prefix=''):
        # for use by the failure callback
        self.curpac = pac

        MirrorGroup._join_url = join_url
        mg = MirrorGroup(self.gr, pac.urllist, failure_callback=(self.failureReport, (), {}))

        if self.http_debug:
            print('\nURLs to try for package \'%s\':' % pac, file=sys.stderr)
            print('\n'.join(pac.urllist), file=sys.stderr)
            print(file=sys.stderr)

        try:
            with tempfile.NamedTemporaryFile(prefix='osc_build',
                                             delete=False) as tmpfile:
                mg.urlgrab(pac.filename, filename=tmpfile.name,
                           text='%s(%s) %s' % (prefix, pac.project, pac.filename))
                self.move_package(tmpfile.name, pac.localdir, pac)
        except URLGrabError as e:
            if self.enable_cpio and e.errno == 256:
                self.__add_cpio(pac)
                return
            print()
            print('Error:', e.strerror, file=sys.stderr)
            print('Failed to retrieve %s from the following locations '
                  '(in order):' % pac.filename, file=sys.stderr)
            print('\n'.join(pac.urllist), file=sys.stderr)
            sys.exit(1)
        finally:
            if os.path.exists(tmpfile.name):
                os.unlink(tmpfile.name)

    def move_package(self, tmpfile, destdir, pac_obj=None):
        import shutil
        pkgq = packagequery.PackageQuery.query(tmpfile, extra_rpmtags=(1044, 1051, 1052))
        if pkgq:
            canonname = pkgq.canonname()
        else:
            if pac_obj is None:
                print('Unsupported file type: ', tmpfile, file=sys.stderr)
                sys.exit(1)
            canonname = pac_obj.binary

        fullfilename = os.path.join(destdir, canonname)
        if pac_obj is not None:
            pac_obj.filename = canonname
            pac_obj.fullfilename = fullfilename
        shutil.move(tmpfile, fullfilename)
        os.chmod(fullfilename, 0o644)

    def dirSetup(self, pac):
        dir = os.path.join(self.cachedir, pac.localdir)
        if not os.path.exists(dir):
            try:
                os.makedirs(dir, mode=0o755)
            except OSError as e:
                print('packagecachedir is not writable for you?', file=sys.stderr)
                print(e, file=sys.stderr)
                sys.exit(1)

    def run(self, buildinfo):
        cached = 0
        all = len(buildinfo.deps)
        for i in buildinfo.deps:
            i.makeurls(self.cachedir, self.urllist)
            if os.path.exists(i.fullfilename):
                cached += 1
        miss = 0
        needed = all - cached
        if all:
            miss = 100.0 * needed / all
        print("%.1f%% cache miss. %d/%d dependencies cached.\n" % (miss, cached, all))
        done = 1
        for i in buildinfo.deps:
            i.makeurls(self.cachedir, self.urllist)
            if not os.path.exists(i.fullfilename):
                if self.offline:
                    raise oscerr.OscIOError(None,
                                            'Missing \'%s\' in cache: '
                                            '--offline not possible.' %
                                            i.fullfilename)
                self.dirSetup(i)
                try:
                    # if there isn't a progress bar, there is no output at all
                    if not self.progress_obj:
                        print('%d/%d (%s) %s' % (done, needed, i.project, i.filename))
                    self.fetch(i)
                    if self.progress_obj:
                        print("  %d/%d\r" % (done, needed), end=' ')
                        sys.stdout.flush()

                except KeyboardInterrupt:
                    print('Cancelled by user (ctrl-c)')
                    print('Exiting.')
                    sys.exit(0)
                done += 1

        self.__fetch_cpio(buildinfo.apiurl)

        prjs = list(buildinfo.projects.keys())
        for i in prjs:
            dest = "%s/%s" % (self.cachedir, i)
            if not os.path.exists(dest):
                os.makedirs(dest, mode=0o755)
            dest += '/_pubkey'

            url = makeurl(buildinfo.apiurl, ['source', i, '_pubkey'])
            try:
                if self.offline and not os.path.exists(dest):
                    # may need to try parent
                    raise URLGrabError(2)
                elif not self.offline:
                    OscFileGrabber().urlgrab(url, dest)
                # not that many keys usually
                if i not in buildinfo.prjkeys:
                    buildinfo.keys.append(dest)
                    buildinfo.prjkeys.append(i)
            except KeyboardInterrupt:
                print('Cancelled by user (ctrl-c)')
                print('Exiting.')
                if os.path.exists(dest):
                    os.unlink(dest)
                sys.exit(0)
            except URLGrabError as e:
                # Not found is okay, let's go to the next project
                if e.errno == 14 and e.code != 404:
                    print("Invalid answer from server", e, file=sys.stderr)
                    sys.exit(1)

                if self.http_debug:
                    print("can't fetch key for %s: %s" % (i, e.strerror), file=sys.stderr)
                    print("url: %s" % url, file=sys.stderr)

                if os.path.exists(dest):
                    os.unlink(dest)

                l = i.rsplit(':', 1)
                # try key from parent project
                if len(l) > 1 and l[1] and not l[0] in buildinfo.projects:
                    prjs.append(l[0])


def verify_pacs_old(pac_list):
    """Take a list of rpm filenames and run rpm -K on them.

       In case of failure, exit.

       Check all packages in one go, since this takes only 6 seconds on my Athlon 700
       instead of 20 when calling 'rpm -K' for each of them.
       """
    import subprocess

    if not pac_list:
        return

    # don't care about the return value because we check the
    # output anyway, and rpm always writes to stdout.

    # save locale first (we rely on English rpm output here)
    saved_LC_ALL = os.environ.get('LC_ALL')
    os.environ['LC_ALL'] = 'en_EN'

    o = subprocess.Popen(['rpm', '-K'] + pac_list, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, close_fds=True).stdout

    # restore locale
    if saved_LC_ALL:
        os.environ['LC_ALL'] = saved_LC_ALL
    else:
        os.environ.pop('LC_ALL')

    for line in o.readlines():

        if 'OK' not in line:
            print()
            print('The following package could not be verified:', file=sys.stderr)
            print(line, file=sys.stderr)
            sys.exit(1)

        if 'NOT OK' in line:
            print()
            print('The following package could not be verified:', file=sys.stderr)
            print(line, file=sys.stderr)

            if 'MISSING KEYS' in line:
                missing_key = line.split('#')[-1].split(')')[0]

                print("""
- If the key (%(name)s) is missing, install it first.
  For example, do the following:
    osc signkey PROJECT > file
  and, as root:
    rpm --import %(dir)s/keyfile-%(name)s

  Then, just start the build again.

- If you do not trust the packages, you should configure osc build for XEN or KVM

- You may use --no-verify to skip the verification (which is a risk for your system).
""" % {'name': missing_key,
       'dir': os.path.expanduser('~')}, file=sys.stderr)

            else:
                print("""
- If the signature is wrong, you may try deleting the package manually
  and re-run this program, so it is fetched again.
""", file=sys.stderr)

            sys.exit(1)


def verify_pacs(bi):
    """Take a list of rpm filenames and verify their signatures.

       In case of failure, exit.
       """

    pac_list = [i.fullfilename for i in bi.deps]
    if conf.config['builtin_signature_check'] is not True:
        return verify_pacs_old(pac_list)

    if not pac_list:
        return

    if not bi.keys:
        raise oscerr.APIError("can't verify packages due to lack of GPG keys")

    print("using keys from", ', '.join(bi.prjkeys))

    from . import checker
    failed = False
    checker = checker.Checker()
    try:
        checker.readkeys(bi.keys)
        for pkg in pac_list:
            try:
                checker.check(pkg)
            except Exception as e:
                failed = True
                print(pkg, ':', e)
    except:
        checker.cleanup()
        raise

    if failed:
        checker.cleanup()
        sys.exit(1)

    checker.cleanup()

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = meter
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the
#      Free Software Foundation, Inc.,
#      59 Temple Place, Suite 330,
#      Boston, MA  02111-1307  USA

# this is basically a copy of python-urlgrabber's TextMeter class,
# with support added for dynamical sizing according to screen size.
# it uses getScreenWidth() scrapped from smart.
# 2007-04-24, poeml

from __future__ import print_function

from urlgrabber.progress import BaseMeter, format_time, format_number
import sys, os

def getScreenWidth():
    import termios, struct, fcntl
    s = struct.pack('HHHH', 0, 0, 0, 0)
    try:
        x = fcntl.ioctl(1, termios.TIOCGWINSZ, s)
    except IOError:
        return 80
    return struct.unpack('HHHH', x)[1]


class TextMeter(BaseMeter):
    def __init__(self, fo=sys.stderr, hide_finished=False):
        BaseMeter.__init__(self)
        self.fo = fo
        self.hide_finished = hide_finished
        try:
            width = int(os.environ['COLUMNS'])
        except (KeyError, ValueError):
            width = getScreenWidth()


        #self.unsized_templ = '\r%-60.60s    %5sB %s '
        self.unsized_templ = '\r%%-%s.%ss    %%5sB %%s ' % (width *2/5, width*3/5)
        #self.sized_templ = '\r%-45.45s %3i%% |%-15.15s| %5sB %8s '
        self.bar_length = width/5
        self.sized_templ = '\r%%-%s.%ss %%3i%%%% |%%-%s.%ss| %%5sB %%8s ' % (width*4/10, width*4/10, self.bar_length, self.bar_length)


    def _do_start(self, *args, **kwargs):
        BaseMeter._do_start(self, *args, **kwargs)
        self._do_update(0)

    def _do_update(self, amount_read, now=None):
        etime = self.re.elapsed_time()
        fetime = format_time(etime)
        fread = format_number(amount_read)
        #self.size = None
        if self.text is not None:
            text = self.text
        else:
            text = self.basename
        if self.size is None:
            out = self.unsized_templ % \
                  (text, fread, fetime)
        else:
            rtime = self.re.remaining_time()
            frtime = format_time(rtime)
            frac = self.re.fraction_read()
            bar = '='*int(self.bar_length * frac)

            out = self.sized_templ % \
                  (text, frac*100, bar, fread, frtime) + 'ETA '

        self.fo.write(out)
        self.fo.flush()

    def _do_end(self, amount_read, now=None):
        total_time = format_time(self.re.elapsed_time())
        total_size = format_number(amount_read)
        if self.text is not None:
            text = self.text
        else:
            text = self.basename
        if self.size is None:
            out = self.unsized_templ % \
                  (text, total_size, total_time)
        else:
            bar = '=' * self.bar_length
            out = self.sized_templ % \
                  (text, 100, bar, total_size, total_time) + '    '
        if self.hide_finished:
            self.fo.write('\r'+ ' '*len(out) + '\r')
        else:
            self.fo.write(out + '\n')
        self.fo.flush()

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = OscConfigParser
# Copyright 2008,2009 Marcus Huewe <suse-tux@gmx.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation;
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

from __future__ import print_function

import sys

if sys.version_info >= ( 3, ):
    import configparser
else:
    #python 2.x
    import ConfigParser as configparser

import re

# inspired from http://code.google.com/p/iniparse/ - although their implementation is
# quite different

class ConfigLineOrder:
    """
    A ConfigLineOrder() instance task is to preserve the order of a config file.
    It keeps track of all lines (including comments) in the _lines list. This list
    either contains SectionLine() instances or CommentLine() instances.
    """
    def __init__(self):
        self._lines = []

    def _append(self, line_obj):
        self._lines.append(line_obj)

    def _find_section(self, section):
        for line in self._lines:
            if line.type == 'section' and line.name == section:
                return line
        return None

    def add_section(self, sectname):
        self._append(SectionLine(sectname))

    def get_section(self, sectname):
        section = self._find_section(sectname)
        if section:
            return section
        section = SectionLine(sectname)
        self._append(section)
        return section

    def add_other(self, sectname, line):
        if sectname:
            self.get_section(sectname).add_other(line)
        else:
            self._append(CommentLine(line))

    def keys(self):
        return [ i.name for i in self._lines if i.type == 'section' ]

    def __setitem__(self, key, value):
        section = SectionLine(key)
        self._append(section)

    def __getitem__(self, key):
        section = self._find_section(key)
        if not section:
            raise KeyError()
        return section

    def __delitem__(self, key):
        line = self._find_section(key)
        if not line:
            raise KeyError(key)
        self._lines.remove(line)

    def __iter__(self):
        #return self._lines.__iter__()
        for line in self._lines:
            if line.type == 'section':
                yield line.name
        raise StopIteration()

class Line:
    """Base class for all line objects"""
    def __init__(self, name, type):
        self.name = name
        self.type = type

class SectionLine(Line):
    """
    This class represents a [section]. It stores all lines which belongs to
    this certain section in the _lines list. The _lines list either contains
    CommentLine() or OptionLine() instances.
    """
    def __init__(self, sectname, dict = {}):
        Line.__init__(self, sectname, 'section')
        self._lines = []
        self._dict = dict

    def _find(self, name):
        for line in self._lines:
            if line.name == name:
                return line
        return None

    def _add_option(self, optname, value = None, line = None, sep = '='):
        if value is None and line is None:
            raise configparser.Error('Either value or line must be passed in')
        elif value and line:
            raise configparser.Error('value and line are mutually exclusive')

        if value is not None:
            line = '%s%s%s' % (optname, sep, value)
        opt = self._find(optname)
        if opt:
            opt.format(line)
        else:
            self._lines.append(OptionLine(optname, line))

    def add_other(self, line):
        self._lines.append(CommentLine(line))

    def copy(self):
        return dict(self.items())

    def items(self):
        return [ (i.name, i.value) for i in self._lines if i.type == 'option' ]

    def keys(self):
        return [ i.name for i in self._lines ]

    def __setitem__(self, key, val):
        self._add_option(key, val)

    def __getitem__(self, key):
        line = self._find(key)
        if not line:
            raise KeyError(key)
        return str(line)

    def __delitem__(self, key):
        line = self._find(key)
        if not line:
            raise KeyError(key)
        self._lines.remove(line)

    def __str__(self):
        return self.name

    # XXX: needed to support 'x' in cp._sections['sectname']
    def __iter__(self):
        for line in self._lines:
            yield line.name
        raise StopIteration()


class CommentLine(Line):
    """Store a commentline"""
    def __init__(self, line):
        Line.__init__(self, line.strip('\n'), 'comment')

    def __str__(self):
        return self.name

class OptionLine(Line):
    """
    This class represents an option. The class' "name" attribute is used
    to store the option's name and the "value" attribute contains the option's
    value. The "frmt" attribute preserves the format which was used in the configuration
    file.
    Example:
        optionx:<SPACE><SPACE>value
        => self.frmt = '%s:<SPACE><SPACE>%s'
        optiony<SPACE>=<SPACE>value<SPACE>;<SPACE>some_comment
        => self.frmt = '%s<SPACE>=<SPACE><SPACE>%s<SPACE>;<SPACE>some_comment
    """

    def __init__(self, optname, line):
        Line.__init__(self, optname, 'option')
        self.name = optname
        self.format(line)

    def format(self, line):
        mo = configparser.ConfigParser.OPTCRE.match(line.strip())
        key, val = mo.group('option', 'value')
        self.frmt = line.replace(key.strip(), '%s', 1)
        pos = val.find(' ;')
        if pos >= 0:
            val = val[:pos]
        self.value = val
        self.frmt = self.frmt.replace(val.strip(), '%s', 1).rstrip('\n')

    def __str__(self):
        return self.value


class OscConfigParser(configparser.SafeConfigParser):
    """
    OscConfigParser() behaves like a normal ConfigParser() object. The
    only differences is that it preserves the order+format of configuration entries
    and that it stores comments.
    In order to keep the order and the format it makes use of the ConfigLineOrder()
    class.
    """
    def __init__(self, defaults={}):
        configparser.SafeConfigParser.__init__(self, defaults)
        self._sections = ConfigLineOrder()

    # XXX: unfortunately we have to override the _read() method from the ConfigParser()
    #      class because a) we need to store comments b) the original version doesn't use
    #      the its set methods to add and set sections, options etc. instead they use a
    #      dictionary (this makes it hard for subclasses to use their own objects, IMHO
    #      a bug) and c) in case of an option we need the complete line to store the format.
    #      This all sounds complicated but it isn't - we only needed some slight changes
    def _read(self, fp, fpname):
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                self._sections.add_other(cursect, line)
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    #cursect[optname] = "%s\n%s" % (cursect[optname], value)
                    #self.set(cursect, optname, "%s\n%s" % (self.get(cursect, optname), value))
                    if cursect == configparser.DEFAULTSECT:
                        self._defaults[optname] = "%s\n%s" % (self._defaults[optname], value)
                    else:
                        # use the raw value here (original version uses raw=False)
                        self._sections[cursect]._find(optname).value = '%s\n%s' % (self.get(cursect, optname, raw=True), value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    elif sectname == configparser.DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        #cursect = {'__name__': sectname}
                        #self._sections[sectname] = cursect
                        self.add_section(sectname)
                        self.set(sectname, '__name__', sectname)
                    # So sections can't start with a continuation line
                    cursect = sectname
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise configparser.MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self.OPTCRE.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if vi in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos != -1 and optval[pos-1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        if cursect == configparser.DEFAULTSECT:
                            self._defaults[optname] = optval
                        else:
                            self._sections[cursect]._add_option(optname, line=line)
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = configparser.ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e # pylint: disable-msg=E0702

    def write(self, fp, comments = False):
        """
        write the configuration file. If comments is True all comments etc.
        will be written to fp otherwise the ConfigParsers' default write method
        will be called.
        """
        if comments:
            fp.write(str(self))
            fp.write('\n')
        else:
            configparser.SafeConfigParser.write(self, fp)

    # XXX: simplify!
    def __str__(self):
        ret = []
        first = True
        for line in self._sections._lines:
            if line.type == 'section':
                if first:
                    first = False
                else:
                    ret.append('')
                ret.append('[%s]' % line.name)
                for sline in line._lines:
                    if sline.name == '__name__':
                        continue
                    if sline.type == 'option':
                        # special handling for continuation lines
                        val = '\n '.join(sline.value.split('\n'))
                        ret.append(sline.frmt % (sline.name, val))
                    elif str(sline) != '':
                        ret.append(str(sline))
            else:
                ret.append(str(line))
        return '\n'.join(ret)

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = oscerr
# Copyright (C) 2008 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.



class OscBaseError(Exception):
    def __init__(self, args=()):
        Exception.__init__(self)
        self.args = args
    def __str__(self):
        return ''.join(self.args)

class UserAbort(OscBaseError):
    """Exception raised when the user requested abortion"""

class ConfigError(OscBaseError):
    """Exception raised when there is an error in the config file"""
    def __init__(self, msg, fname):
        OscBaseError.__init__(self)
        self.msg = msg
        self.file = fname

class ConfigMissingApiurl(ConfigError):
    """Exception raised when a apiurl does not exist in the config file"""
    def __init__(self, msg, fname, url):
        ConfigError.__init__(self, msg, fname)
        self.url = url

class APIError(OscBaseError):
    """Exception raised when there is an error in the output from the API"""
    def __init__(self, msg):
        OscBaseError.__init__(self)
        self.msg = msg

class NoConfigfile(OscBaseError):
    """Exception raised when osc's configfile cannot be found"""
    def __init__(self, fname, msg):
        OscBaseError.__init__(self)
        self.file = fname
        self.msg = msg

class ExtRuntimeError(OscBaseError):
    """Exception raised when there is a runtime error of an external tool"""
    def __init__(self, msg, fname):
        OscBaseError.__init__(self)
        self.msg = msg
        self.file = fname

class ServiceRuntimeError(OscBaseError):
    """Exception raised when the execution of a source service failed"""
    def __init__(self, msg):
        OscBaseError.__init__(self)
        self.msg = msg

class WrongArgs(OscBaseError):
    """Exception raised by the cli for wrong arguments usage"""

class WrongOptions(OscBaseError):
    """Exception raised by the cli for wrong option usage"""
    #def __str__(self):
    #    s = 'Sorry, wrong options.'
    #    if self.args:
    #        s += '\n' + self.args
    #    return s

class NoWorkingCopy(OscBaseError):
    """Exception raised when directory is neither a project dir nor a package dir"""

class WorkingCopyWrongVersion(OscBaseError):
    """Exception raised when working copy's .osc/_osclib_version doesn't match"""

class WorkingCopyOutdated(OscBaseError):
    """Exception raised when the working copy is outdated.
    It takes a tuple with three arguments: path to wc,
    revision that it has, revision that it should have.
    """
    def __str__(self):
        return ('Working copy \'%s\' is out of date (rev %s vs rev %s).\n'
               'Looks as if you need to update it first.' \
                    % (self[0], self[1], self[2]))

class PackageError(OscBaseError):
    """Base class for all Package related exceptions"""
    def __init__(self, prj, pac):
        OscBaseError.__init__(self)
        self.prj = prj
        self.pac = pac

class WorkingCopyInconsistent(PackageError):
    """Exception raised when the working copy is in an inconsistent state"""
    def __init__(self, prj, pac, dirty_files, msg):
        PackageError.__init__(self, prj, pac)
        self.dirty_files = dirty_files
        self.msg = msg

class LinkExpandError(PackageError):
    """Exception raised when source link expansion fails"""
    def __init__(self, prj, pac, msg):
        PackageError.__init__(self, prj, pac)
        self.msg = msg

class OscIOError(OscBaseError):
    def __init__(self, e, msg):
        OscBaseError.__init__(self)
        self.e = e
        self.msg = msg

class PackageNotInstalled(OscBaseError):
    """
    Exception raised when a package is not installed on local system
    """
    def __init__(self, pkg):
        OscBaseError.__init__(self, pkg)

    def __str__(self):
        return 'Package %s is required for this operation' % ''.join(self.args)

class SignalInterrupt(Exception):
    """Exception raised on SIGTERM and SIGHUP."""

class PackageExists(PackageError):
    """
    Exception raised when a local object already exists
    """
    def __init__(self, prj, pac, msg):
        PackageError.__init__(self, prj, pac)
        self.msg = msg

class PackageMissing(PackageError):
    """
    Exception raised when a local object doesn't exist
    """
    def __init__(self, prj, pac, msg):
        PackageError.__init__(self, prj, pac)
        self.msg = msg

class PackageFileConflict(PackageError):
    """
    Exception raised when there's a file conflict.
    Conflict doesn't mean an unsuccessfull merge in this context.
    """
    def __init__(self, prj, pac, file, msg):
        PackageError.__init__(self, prj, pac)
        self.file = file
        self.msg = msg

class PackageInternalError(PackageError):
    def __init__(self, prj, pac, msg):
        PackageError.__init__(self, prj, pac)
        self.msg = msg
# vim: sw=4 et

########NEW FILE########
__FILENAME__ = oscssl
# Copyright (C) 2009 Novell Inc.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.

from __future__ import print_function

import M2Crypto.httpslib
from M2Crypto.SSL.Checker import SSLVerificationError
from M2Crypto import m2, SSL
import M2Crypto.m2urllib2
import socket
import sys

try:
    from urllib.parse import urlparse, splithost, splitport, splittype
    from urllib.request import addinfourl
    from http.client import HTTPSConnection
except ImportError:
    #python 2.x
    from urlparse import urlparse
    from urllib import addinfourl, splithost, splitport, splittype
    from httplib import HTTPSConnection

from .core import raw_input

class TrustedCertStore:
    _tmptrusted = {}

    def __init__(self, host, port, app, cert):

        self.cert = cert
        self.host = host
        if self.host == None:
            raise Exception("empty host")
        if port:
            self.host += "_%d" % port
        import os
        self.dir = os.path.expanduser('~/.config/%s/trusted-certs' % app)
        self.file = self.dir + '/%s.pem' % self.host

    def is_known(self):
        if self.host in self._tmptrusted:
            return True

        import os
        if os.path.exists(self.file):
            return True
        return False

    def is_trusted(self):
        import os
        if self.host in self._tmptrusted:
            cert = self._tmptrusted[self.host]
        else:
            if not os.path.exists(self.file):
                return False
            from M2Crypto import X509
            cert = X509.load_cert(self.file)
        if self.cert.as_pem() == cert.as_pem():
            return True
        else:
            return False

    def trust_tmp(self):
        self._tmptrusted[self.host] = self.cert

    def trust_always(self):
        self.trust_tmp()
        from M2Crypto import X509
        import os
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        self.cert.save_pem(self.file)


# verify_cb is called for each error once
# we only collect the errors and return suceess
# connection will be aborted later if it needs to
def verify_cb(ctx, ok, store):
    if not ctx.verrs:
        ctx.verrs = ValidationErrors()

    try:
        if not ok:
            ctx.verrs.record(store.get_current_cert(), store.get_error(), store.get_error_depth())
        return 1

    except Exception as e:
        print(e, file=sys.stderr)
        return 0

class FailCert:
    def __init__(self, cert):
        self.cert = cert
        self.errs = []

class ValidationErrors:

    def __init__(self):
        self.chain_ok = True
        self.cert_ok = True
        self.failures = {}

    def record(self, cert, err, depth):
        #print "cert for %s, level %d fail(%d)" % ( cert.get_subject().commonName, depth, err )
        if depth == 0:
            self.cert_ok = False
        else:
            self.chain_ok = False

        if not depth in self.failures:
            self.failures[depth] = FailCert(cert)
        else:
            if self.failures[depth].cert.get_fingerprint() != cert.get_fingerprint():
                raise Exception("Certificate changed unexpectedly. This should not happen")
        self.failures[depth].errs.append(err)

    def show(self, out):
        for depth in self.failures.keys():
            cert = self.failures[depth].cert
            print("*** certificate verify failed at depth %d" % depth, file=out)
            print("Subject: ", cert.get_subject(), file=out)
            print("Issuer:  ", cert.get_issuer(), file=out)
            print("Valid: ", cert.get_not_before(), "-", cert.get_not_after(), file=out)
            print("Fingerprint(MD5):  ", cert.get_fingerprint('md5'), file=out)
            print("Fingerprint(SHA1): ", cert.get_fingerprint('sha1'), file=out)

            for err in self.failures[depth].errs:
                reason = "Unknown"
                try:
                    import M2Crypto.Err
                    reason = M2Crypto.Err.get_x509_verify_error(err)
                except:
                    pass
                print("Reason:", reason, file=out)

    # check if the encountered errors could be ignored
    def could_ignore(self):
        if not 0 in self.failures:
            return True

        nonfatal_errors = [
                m2.X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY,
                m2.X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN,
                m2.X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT,
                m2.X509_V_ERR_CERT_UNTRUSTED,
                m2.X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE,

                m2.X509_V_ERR_CERT_NOT_YET_VALID,
                m2.X509_V_ERR_CERT_HAS_EXPIRED,
                m2.X509_V_OK,
                ]

        canignore = True
        for err in self.failures[0].errs:
            if not err in nonfatal_errors:
                canignore = False
                break

        return canignore

class mySSLContext(SSL.Context):

    def __init__(self):
        SSL.Context.__init__(self, 'sslv23')
        self.set_options(m2.SSL_OP_NO_SSLv2 | m2.SSL_OP_NO_SSLv3)
        self.set_cipher_list("ECDHE-RSA-AES128-SHA256:AES128-GCM-SHA256:RC4:HIGH:!MD5:!aNULL:!EDH")
        self.set_session_cache_mode(m2.SSL_SESS_CACHE_CLIENT)
        self.verrs = None
        #self.set_info_callback() # debug
        self.set_verify(SSL.verify_peer | SSL.verify_fail_if_no_peer_cert, depth=9, callback=lambda ok, store: verify_cb(self, ok, store))

class myHTTPSHandler(M2Crypto.m2urllib2.HTTPSHandler):
    handler_order = 499
    saved_session = None

    def __init__(self, *args, **kwargs):
        self.appname = kwargs.pop('appname', 'generic')
        M2Crypto.m2urllib2.HTTPSHandler.__init__(self, *args, **kwargs)

    # copied from M2Crypto.m2urllib2.HTTPSHandler
    # it's sole purpose is to use our myHTTPSHandler/myHTTPSProxyHandler class
    # ideally the m2urllib2.HTTPSHandler.https_open() method would be split into
    # "do_open()" and "https_open()" so that we just need to override
    # the small "https_open()" method...)
    def https_open(self, req):
        host = req.get_host()
        if not host:
            raise M2Crypto.m2urllib2.URLError('no host given: ' + req.get_full_url())

        # Our change: Check to see if we're using a proxy.
        # Then create an appropriate ssl-aware connection.
        full_url = req.get_full_url()
        target_host = urlparse(full_url)[1]

        if (target_host != host):
            h = myProxyHTTPSConnection(host = host, appname = self.appname, ssl_context = self.ctx)
            # M2Crypto.ProxyHTTPSConnection.putrequest expects a fullurl
            selector = full_url
        else:
            h = myHTTPSConnection(host = host, appname = self.appname, ssl_context = self.ctx)
            selector = req.get_selector()
        # End our change
        h.set_debuglevel(self._debuglevel)
        if self.saved_session:
            h.set_session(self.saved_session)

        headers = dict(req.headers)
        headers.update(req.unredirected_hdrs)
        # We want to make an HTTP/1.1 request, but the addinfourl
        # class isn't prepared to deal with a persistent connection.
        # It will try to read all remaining data from the socket,
        # which will block while the server waits for the next request.
        # So make sure the connection gets closed after the (only)
        # request.
        headers["Connection"] = "close"
        try:
            h.request(req.get_method(), selector, req.data, headers)
            s = h.get_session()
            if s:
                self.saved_session = s
            r = h.getresponse()
        except socket.error as err: # XXX what error?
            err.filename = full_url
            raise M2Crypto.m2urllib2.URLError(err)

        # Pick apart the HTTPResponse object to get the addinfourl
        # object initialized properly.

        # Wrap the HTTPResponse object in socket's file object adapter
        # for Windows.  That adapter calls recv(), so delegate recv()
        # to read().  This weird wrapping allows the returned object to
        # have readline() and readlines() methods.

        # XXX It might be better to extract the read buffering code
        # out of socket._fileobject() and into a base class.

        r.recv = r.read
        fp = socket._fileobject(r)

        resp = addinfourl(fp, r.msg, req.get_full_url())
        resp.code = r.status
        resp.msg = r.reason
        return resp

class myHTTPSConnection(M2Crypto.httpslib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        self.appname = kwargs.pop('appname', 'generic')
        M2Crypto.httpslib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self, *args):
        M2Crypto.httpslib.HTTPSConnection.connect(self, *args)
        verify_certificate(self)

    def getHost(self):
        return self.host

    def getPort(self):
        return self.port

class myProxyHTTPSConnection(M2Crypto.httpslib.ProxyHTTPSConnection, HTTPSConnection):
    def __init__(self, *args, **kwargs):
        self.appname = kwargs.pop('appname', 'generic')
        M2Crypto.httpslib.ProxyHTTPSConnection.__init__(self, *args, **kwargs)

    def _start_ssl(self):
        M2Crypto.httpslib.ProxyHTTPSConnection._start_ssl(self)
        verify_certificate(self)

    def endheaders(self, *args, **kwargs):
        if self._proxy_auth is None:
            self._proxy_auth = self._encode_auth()
        HTTPSConnection.endheaders(self, *args, **kwargs)        

    # broken in m2crypto: port needs to be an int
    def putrequest(self, method, url, skip_host=0, skip_accept_encoding=0):
        #putrequest is called before connect, so can interpret url and get
        #real host/port to be used to make CONNECT request to proxy
        proto, rest = splittype(url)
        if proto is None:
            raise ValueError("unknown URL type: %s" % url)
        #get host
        host, rest = splithost(rest)
        #try to get port
        host, port = splitport(host)
        #if port is not defined try to get from proto
        if port is None:
            try:
                port = self._ports[proto]
            except KeyError:
                raise ValueError("unknown protocol for: %s" % url)
        self._real_host = host
        self._real_port = int(port)
        M2Crypto.httpslib.HTTPSConnection.putrequest(self, method, url, skip_host, skip_accept_encoding)

    def getHost(self):
        return self._real_host

    def getPort(self):
        return self._real_port

def verify_certificate(connection):
    ctx = connection.sock.ctx
    verrs = ctx.verrs
    ctx.verrs = None
    cert = connection.sock.get_peer_cert()
    if not cert:
        connection.close()
        raise SSLVerificationError("server did not present a certificate")

    # XXX: should be check if the certificate is known anyways?
    # Maybe it changed to something valid.
    if not connection.sock.verify_ok():

        tc = TrustedCertStore(connection.getHost(), connection.getPort(), connection.appname, cert)

        if tc.is_known():

            if tc.is_trusted(): # ok, same cert as the stored one
                return
            else:
                print("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!", file=sys.stderr)
                print("IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!", file=sys.stderr)
                print("offending certificate is at '%s'" % tc.file, file=sys.stderr)
                raise SSLVerificationError("remote host identification has changed")

        # if http_debug is set we redirect sys.stdout to an StringIO
        # instance in order to do some header filtering (see conf module)
        # so we have to use the "original" stdout for printing
        out = getattr(connection, '_orig_stdout', sys.stdout)
        verrs.show(out)

        print(file=out)

        if not verrs.could_ignore():
            raise SSLVerificationError("Certificate validation error cannot be ignored")

        if not verrs.chain_ok:
            print("A certificate in the chain failed verification", file=out)
        if not verrs.cert_ok:
            print("The server certificate failed verification", file=out)

        while True:
            print("""
Would you like to
0 - quit (default)
1 - continue anyways
2 - trust the server certificate permanently
9 - review the server certificate
""", file=out)

            print("Enter choice [0129]: ", end='', file=out)
            r = raw_input()
            if not r or r == '0':
                connection.close()
                raise SSLVerificationError("Untrusted Certificate")
            elif r == '1':
                tc.trust_tmp()
                return
            elif r == '2':
                tc.trust_always()
                return
            elif r == '9':
                print(cert.as_text(), file=out)

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = oscsslexcp
class NoSecureSSLError(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

# vim: sw=4 et

########NEW FILE########
__FILENAME__ = ar
# Copyright 2009 Marcus Huewe <suse-tux@gmx.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation;
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

from __future__ import print_function

import os
import re
import sys
import stat

#XXX: python 2.7 contains io.StringIO, which needs unicode instead of str
#therefor try to import old stuff before new one here
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# workaround for python24
if not hasattr(os, 'SEEK_SET'):
    os.SEEK_SET = 0

class ArError(Exception):
    """Base class for all ar related errors"""
    def __init__(self, fn, msg):
        Exception.__init__(self)
        self.file = fn
        self.msg = msg

    def __str__(self):
        return 'ar error: %s' % self.msg

class ArHdr:
    """Represents an ar header entry"""
    def __init__(self, fn, date, uid, gid, mode, size, fmag, off):
        self.file = fn.strip()
        self.date = date.strip()
        self.uid = uid.strip()
        self.gid = gid.strip()
        self.mode = stat.S_IMODE(int(mode, 8))
        self.size = int(size)
        self.fmag = fmag
        # data section starts at off and ends at off + size
        self.dataoff = int(off)

    def __str__(self):
        return '%16s %d' % (self.file, self.size)

class ArFile(StringIO):
    """Represents a file which resides in the archive"""
    def __init__(self, fn, uid, gid, mode, buf):
        StringIO.__init__(self, buf)
        self.name = fn
        self.uid = uid
        self.gid = gid
        self.mode = mode

    def saveTo(self, dir = None):
        """
        writes file to dir/filename if dir isn't specified the current
        working dir is used. Additionally it tries to set the owner/group
        and permissions.
        """
        if not dir:
            dir = os.getcwd()
        fn = os.path.join(dir, self.name)
        f = open(fn, 'wb')
        f.write(self.getvalue())
        f.close()
        os.chmod(fn, self.mode)
        uid = self.uid
        if uid != os.geteuid() or os.geteuid() != 0:
            uid = -1
        gid = self.gid
        if not gid in os.getgroups() or os.getegid() != 0:
            gid = -1
        os.chown(fn, uid, gid)

    def __str__(self):
        return '%s %s %s %s' % (self.name, self.uid,
                                self.gid, self.mode)

class Ar:
    """
    Represents an ar archive (only GNU format is supported).
    Readonly access.
    """
    hdr_len = 60
    hdr_pat = re.compile('^(.{16})(.{12})(.{6})(.{6})(.{8})(.{10})(.{2})', re.DOTALL)

    def __init__(self, fn = None, fh = None):
        if fn == None and fh == None:
            raise ArError('either \'fn\' or \'fh\' must be != None')
        if fh != None:
            self.__file = fh
            self.__closefile = False
            self.filename = fh.name
        else:
            # file object: will be closed in __del__()
            self.__file = None
            self.__closefile = True
            self.filename = fn
        self._init_datastructs()

    def __del__(self):
        if self.__file and self.__closefile:
            self.__file.close()

    def _init_datastructs(self):
        self.hdrs = []
        self.ext_fnhdr = None

    def _appendHdr(self, hdr):
        # GNU uses an internal '//' file to store very long filenames
        if hdr.file.startswith('//'):
            self.ext_fnhdr = hdr
        else:
            self.hdrs.append(hdr)

    def _fixupFilenames(self):
        """
        support the GNU approach for very long filenames:
        every filename which exceeds 16 bytes is stored in the data section of a special file ('//')
        and the filename in the header of this long file specifies the offset in the special file's
        data section. The end of such a filename is indicated with a trailing '/'.
        Another special file is the '/' which contains the symbol lookup table.
        """
        for h in self.hdrs:
            if h.file == '/':
                continue
            # remove slashes which are appended by ar
            h.file = h.file.rstrip('/')
            if not h.file.startswith('/'):
                continue
            # handle long filename
            off = int(h.file[1:len(h.file)])
            start = self.ext_fnhdr.dataoff + off
            self.__file.seek(start, os.SEEK_SET)
            # XXX: is it safe to read all the data in one chunk? I assume the '//' data section
            #      won't be too large
            data = self.__file.read(self.ext_fnhdr.size)
            end = data.find('/')
            if end != -1:
                h.file = data[0:end]
            else:
                raise ArError('//', 'invalid data section - trailing slash (off: %d)' % start)

    def _get_file(self, hdr):
        self.__file.seek(hdr.dataoff, os.SEEK_SET)
        return ArFile(hdr.file, hdr.uid, hdr.gid, hdr.mode,
                      self.__file.read(hdr.size))

    def read(self):
        """reads in the archive. It tries to use mmap due to performance reasons (in case of large files)"""
        if not self.__file:
            import mmap
            self.__file = open(self.filename, 'rb')
            try:
                if sys.platform[:3] != 'win':
                    self.__file = mmap.mmap(self.__file.fileno(), os.path.getsize(self.__file.name), prot=mmap.PROT_READ)
                else:
                    self.__file = mmap.mmap(self.__file.fileno(), os.path.getsize(self.__file.name))
            except EnvironmentError as e:
                if e.errno == 19 or ( hasattr(e, 'winerror') and e.winerror == 5 ):
                    print('cannot use mmap to read the file, falling back to the default io', file=sys.stderr)
                else:
                    raise e
        else:
            self.__file.seek(0, os.SEEK_SET)
        self._init_datastructs()
        data = self.__file.read(7)
        if data != '!<arch>':
            raise ArError(self.filename, 'no ar archive')
        pos = 8
        while (len(data) != 0):
            self.__file.seek(pos, os.SEEK_SET)
            data = self.__file.read(self.hdr_len)
            if not data:
                break
            pos += self.hdr_len
            m = self.hdr_pat.search(data)
            if not m:
                raise ArError(self.filename, 'unexpected hdr entry')
            args = m.groups() + (pos, )
            hdr = ArHdr(*args)
            self._appendHdr(hdr)
            # data blocks are 2 bytes aligned - if they end on an odd
            # offset ARFMAG[0] will be used for padding (according to the current binutils code)
            pos += hdr.size + (hdr.size & 1)
        self._fixupFilenames()

    def get_file(self, fn):
        for h in self.hdrs:
            if h.file == fn:
                return self._get_file(h)
        return None

    def __iter__(self):
        for h in self.hdrs:
            if h.file == '/':
                continue
            yield self._get_file(h)
        raise StopIteration()

########NEW FILE########
__FILENAME__ = archquery

from __future__ import print_function

import os.path
import re
import tarfile
from . import packagequery
import subprocess

class ArchError(packagequery.PackageError):
    pass

class ArchQuery(packagequery.PackageQuery):
    def __init__(self, fh):
        self.__file = fh
        self.__path = os.path.abspath(fh.name)
        self.fields = {}
        #self.magic = None
        #self.pkgsuffix = 'pkg.tar.gz'
        self.pkgsuffix = 'arch'

    def read(self, all_tags=True, self_provides=True, *extra_tags):
        # all_tags and *extra_tags are currently ignored
        f = open(self.__path, 'rb')
        #self.magic = f.read(5)
        #if self.magic == '\375\067zXZ':
        #    self.pkgsuffix = 'pkg.tar.xz'
        fn = open('/dev/null', 'wb')
        pipe = subprocess.Popen(['tar', '-O', '-xf', self.__path, '.PKGINFO'], stdout=subprocess.PIPE, stderr=fn).stdout
        for line in pipe.readlines():
            line = line.rstrip().split(' = ', 2)
            if len(line) == 2:
                if not line[0] in self.fields:
                    self.fields[line[0]] = []
                self.fields[line[0]].append(line[1])
        if self_provides:
            prv = '%s = %s' % (self.name(), self.fields['pkgver'][0])
            self.fields.setdefault('provides', []).append(prv)

    def vercmp(self, archq):
        res = cmp(int(self.epoch()), int(archq.epoch()))
        if res != 0:
            return res
        res = ArchQuery.rpmvercmp(self.version(), archq.version())
        if res != None:
            return res
        res = ArchQuery.rpmvercmp(self.release(), archq.release())
        return res

    def name(self):
        return self.fields['pkgname'][0] if 'pkgname' in self.fields else None

    def version(self):
        pkgver = self.fields['pkgver'][0] if 'pkgver' in self.fields else None
        if pkgver != None:
            pkgver = re.sub(r'[0-9]+:', '', pkgver, 1)
            pkgver = re.sub(r'-[^-]*$', '', pkgver)
        return pkgver

    def release(self):
        pkgver = self.fields['pkgver'][0] if 'pkgver' in self.fields else None
        if pkgver != None:
            m = re.search(r'-([^-])*$', pkgver)
            if m:
                return m.group(1)
        return None

    def epoch(self):
        pkgver = self.fields['pkgver'][0] if 'pkgver' in self.fields else None
        if pkgver != None:
            m = re.match(r'([0-9])+:', pkgver)
            if m:
                return m.group(1)
        return None

    def arch(self):
        return self.fields['arch'][0] if 'arch' in self.fields else None

    def description(self):
        return self.fields['pkgdesc'][0] if 'pkgdesc' in self.fields else None

    def path(self):
        return self.__path

    def provides(self):
        return self.fields['provides'] if 'provides' in self.fields else []

    def requires(self):
        return self.fields['depend'] if 'depend' in self.fields else []

    def canonname(self):
        pkgver = self.fields['pkgver'][0] if 'pkgver' in self.fields else None
        return self.name() + '-' + pkgver + '-' + self.arch() + '.' + self.pkgsuffix

    @staticmethod
    def query(filename, all_tags = False, *extra_tags):
        f = open(filename, 'rb')
        archq = ArchQuery(f)
        archq.read(all_tags, *extra_tags)
        f.close()
        return archq

    @staticmethod
    def rpmvercmp(ver1, ver2):
        """
        implementation of RPM's version comparison algorithm
        (as described in lib/rpmvercmp.c)
        """
        if ver1 == ver2:
            return 0
        res = 0
        while res == 0:
            # remove all leading non alphanumeric chars
            ver1 = re.sub('^[^a-zA-Z0-9]*', '', ver1)
            ver2 = re.sub('^[^a-zA-Z0-9]*', '', ver2)
            if not (len(ver1) and len(ver2)):
                break
            # check if we have a digits segment
            mo1 = re.match('(\d+)', ver1)
            mo2 = re.match('(\d+)', ver2)
            numeric = True
            if mo1 is None:
                mo1 = re.match('([a-zA-Z]+)', ver1)
                mo2 = re.match('([a-zA-Z]+)', ver2)
                numeric = False
            # check for different types: alpha and numeric
            if mo2 is None:
                if numeric:
                    return 1
                return -1
            seg1 = mo1.group(0)
            ver1 = ver1[mo1.end(0):]
            seg2 = mo2.group(1)
            ver2 = ver2[mo2.end(1):]
            if numeric:
                # remove leading zeros
                seg1 = re.sub('^0+', '', seg1)
                seg2 = re.sub('^0+', '', seg2)
                # longer digit segment wins - if both have the same length
                # a simple ascii compare decides
                res = len(seg1) - len(seg2) or cmp(seg1, seg2)
            else:
                res = cmp(seg1, seg2)
        if res > 0:
            return 1
        elif res < 0:
            return -1
        return cmp(ver1, ver2)

    @staticmethod
    def filename(name, epoch, version, release, arch):
        if epoch:
            if release:
                return '%s-%s:%s-%s-%s.arch' % (name, epoch, version, release, arch)
            else:
                return '%s-%s:%s-%s.arch' % (name, epoch, version, arch)
        if release:
            return '%s-%s-%s-%s.arch' % (name, version, release, arch)
        else:
            return '%s-%s-%s.arch' % (name, version, arch)


if __name__ == '__main__':
    import sys
    try:
        archq = ArchQuery.query(sys.argv[1])
    except ArchError as e:
        print(e.msg)
        sys.exit(2)
    print(archq.name(), archq.version(), archq.release(), archq.arch())
    print(archq.canonname())
    print(archq.description())
    print('##########')
    print('\n'.join(archq.provides()))
    print('##########')
    print('\n'.join(archq.requires()))

########NEW FILE########
__FILENAME__ = cpio
# Copyright 2009 Marcus Huewe <suse-tux@gmx.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation;
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

from __future__ import print_function

import mmap
import os
import stat
import struct
import sys

# workaround for python24
if not hasattr(os, 'SEEK_SET'):
    os.SEEK_SET = 0

# format implementation is based on src/copyin.c and src/util.c (see cpio sources)

class CpioError(Exception):
    """base class for all cpio related errors"""
    def __init__(self, fn, msg):
        Exception.__init__(self)
        self.file = fn
        self.msg = msg
    def __str__(self):
        return '%s: %s' % (self.file, self.msg)

class CpioHdr:
    """
    Represents a cpio header ("New" portable format and CRC format).
    """
    def __init__(self, mgc, ino, mode, uid, gid, nlink, mtime, filesize,
                 dev_maj, dev_min, rdev_maj, rdev_min, namesize, checksum,
                 off = -1, filename = ''):
        """
        All passed parameters are hexadecimal strings (not NUL terminated) except
        off and filename. They will be converted into normal ints.
        """
        self.ino = ino
        self.mode = mode
        self.uid = uid
        self.gid = gid
        self.nlink = nlink
        self.mtime = mtime
        # 0 indicates FIFO or dir
        self.filesize = filesize
        self.dev_maj = dev_maj
        self.dev_min = dev_min
        # only needed for special block/char files
        self.rdev_maj = rdev_maj
        self.rdev_min = rdev_min
        # length of filename (inluding terminating NUL)
        self.namesize = namesize
        # != 0 indicates CRC format (which we do not support atm)
        self.checksum = checksum
        for k,v in self.__dict__.items():
            self.__dict__[k] = int(v, 16)
        self.filename = filename
        # data starts at dataoff and ends at dataoff+filesize
        self.dataoff = off

    def __str__(self):
        return "%s %s %s %s" % (self.filename, self.filesize, self.namesize, self.dataoff)

class CpioRead:
    """
    Represents a cpio archive.
    Supported formats:
    * ascii SVR4 no CRC also called "new_ascii"
    """

    # supported formats - use name -> mgc mapping to increase readabilty
    sfmt = {
             'newascii' : '070701',
           }

    # header format
    hdr_fmt = '6s8s8s8s8s8s8s8s8s8s8s8s8s8s'
    hdr_len = 110

    def __init__(self, filename):
        self.filename = filename
        self.format = -1
        self.__file = None
        self._init_datastructs()

    def __del__(self):
        if self.__file:
            self.__file.close()

    def __iter__(self):
        for h in self.hdrs:
            yield h

    def _init_datastructs(self):
        self.hdrs = []

    def _calc_padding(self, off):
        """
        skip some bytes after a header or a file.
        based on 'static void tape_skip_padding()' in copyin.c.
        """
        if self._is_format('newascii'):
            return (4 - (off % 4)) % 4

    def _is_format(self, type):
        return self.format == self.sfmt[type]

    def _copyin_file(self, hdr, dest, fn):
        """saves file to disk"""
        # TODO: investigate links (e.g. symbolic links are working)
        # check if we have a regular file
        if not stat.S_ISREG(stat.S_IFMT(hdr.mode)):
            msg = '\'%s\' is no regular file - only regular files are supported atm' % hdr.filename
            raise NotImplementedError(msg)
        fn = os.path.join(dest, fn)
        f = open(fn, 'wb')
        self.__file.seek(hdr.dataoff, os.SEEK_SET)
        f.write(self.__file.read(hdr.filesize))
        f.close()
        os.chmod(fn, hdr.mode)
        uid = hdr.uid
        if uid != os.geteuid() or os.geteuid() != 1:
            uid = -1
        gid = hdr.gid
        if not gid in os.getgroups() or os.getegid() != -1:
            gid = -1
        os.chown(fn, uid, gid)

    def _get_hdr(self, fn):
        for h in self.hdrs:
            if h.filename == fn:
                return h
        return None

    def read(self):
        if not self.__file:
            self.__file = open(self.filename, 'rb')
            try:
                if sys.platform[:3] != 'win':
                    self.__file = mmap.mmap(self.__file.fileno(), os.path.getsize(self.__file.name), prot = mmap.PROT_READ)
                else:
                    self.__file = mmap.mmap(self.__file.fileno(), os.path.getsize(self.__file.name))
            except EnvironmentError as e:
                if e.errno == 19 or ( hasattr(e, 'winerror') and e.winerror == 5 ):
                    print('cannot use mmap to read the file, failing back to default', file=sys.stderr)
                else:
                    raise e
        else:
            self.__file.seek(0, os.SEEK_SET)
        self._init_datastructs()
        data = self.__file.read(6)
        self.format = data
        if not self.format in self.sfmt.values():
            raise CpioError(self.filename, '\'%s\' is not a supported cpio format' % self.format)
        pos = 0
        while (len(data) != 0):
            self.__file.seek(pos, os.SEEK_SET)
            data = self.__file.read(self.hdr_len)
            if not data:
                break
            pos += self.hdr_len
            data = struct.unpack(self.hdr_fmt, data)
            hdr = CpioHdr(*data)
            hdr.filename = self.__file.read(hdr.namesize - 1)
            if hdr.filename == 'TRAILER!!!':
                break
            pos += hdr.namesize
            if self._is_format('newascii'):
                pos += self._calc_padding(hdr.namesize + 110)
            hdr.dataoff = pos
            self.hdrs.append(hdr)
            pos += hdr.filesize + self._calc_padding(hdr.filesize)

    def copyin_file(self, filename, dest = None, new_fn = None):
        """
        copies filename to dest.
        If dest is None the file will be stored in $PWD/filename. If dest points
        to a dir the file will be stored in dest/filename. In case new_fn is specified
        the file will be stored as new_fn.
        """
        hdr = self._get_hdr(filename)
        if not hdr:
            raise CpioError(filename, '\'%s\' does not exist in archive' % filename)
        dest = dest or os.getcwd()
        fn = new_fn or filename
        self._copyin_file(hdr, dest, fn)

    def copyin(self, dest = None):
        """
        extracts the cpio archive to dest.
        If dest is None $PWD will be used.
        """
        dest = dest or os.getcwd()
        for h in self.hdrs:
            self._copyin_file(h, dest, h.filename)

class CpioWrite:
    """cpio archive small files in memory, using new style portable header format"""

    def __init__(self):
        self.cpio = ''

    def add(self, name=None, content=None, perms=0x1a4, type=0x8000):
        namesize = len(name) + 1
        if namesize % 2:
            name += '\0'
        filesize = len(content)
        mode = perms | type

        c = []
        c.append('070701') # magic
        c.append('%08X' % 0) # inode
        c.append('%08X' % mode) # mode
        c.append('%08X' % 0) # uid
        c.append('%08X' % 0) # gid
        c.append('%08X' % 0) # nlink
        c.append('%08X' % 0) # mtime
        c.append('%08X' % filesize)
        c.append('%08X' % 0) # major
        c.append('%08X' % 0) # minor
        c.append('%08X' % 0) # rmajor
        c.append('%08X' % 0) # rminor
        c.append('%08X' % namesize)
        c.append('%08X' % 0) # checksum

        c.append(name + '\0')
        c.append('\0' * (len(''.join(c)) % 4))

        c.append(content)

        c = ''.join(c)
        if len(c) % 4:
            c += '\0' * (4 - len(c) % 4)

        self.cpio += c

    def add_padding(self):
        if len(self.cpio) % 512:
            self.cpio += '\0' * (512 - len(self.cpio) % 512)

    def get(self):
        self.add('TRAILER!!!', '')
        self.add_padding()
        return ''.join(self.cpio)

########NEW FILE########
__FILENAME__ = debquery

from __future__ import print_function

from . import ar
import os.path
import re
import tarfile
from . import packagequery

class DebError(packagequery.PackageError):
    pass

class DebQuery(packagequery.PackageQuery):

    default_tags = ('package', 'version', 'release', 'epoch', 'architecture', 'description',
        'provides', 'depends', 'pre_depends')

    def __init__(self, fh):
        self.__file = fh
        self.__path = os.path.abspath(fh.name)
        self.filename_suffix = 'deb'
        self.fields = {}

    def read(self, all_tags=False, self_provides=True, *extra_tags):
        arfile = ar.Ar(fh = self.__file)
        arfile.read()
        debbin = arfile.get_file('debian-binary')
        if debbin is None:
            raise DebError(self.__path, 'no debian binary')
        if debbin.read() != '2.0\n':
            raise DebError(self.__path, 'invalid debian binary format')
        control = arfile.get_file('control.tar.gz')
        if control is None:
            raise DebError(self.__path, 'missing control.tar.gz')
        # XXX: python2.4 relies on a name
        tar = tarfile.open(name = 'control.tar.gz', fileobj = control)
        try:
            name = './control'
            # workaround for python2.4's tarfile module
            if 'control' in tar.getnames():
                name = 'control'
            control = tar.extractfile(name)
        except KeyError:
            raise DebError(self.__path, 'missing \'control\' file in control.tar.gz')
        self.__parse_control(control, all_tags, self_provides, *extra_tags)

    def __parse_control(self, control, all_tags=False, self_provides=True, *extra_tags):
        data = control.readline().strip()
        while data:
            field, val = re.split(':\s*', data.strip(), 1)
            data = control.readline()
            while data and re.match('\s+', data):
                val += '\n' + data.strip()
                data = control.readline().rstrip()
            field = field.replace('-', '_').lower()
            if field in self.default_tags + extra_tags or all_tags:
                # a hyphen is not allowed in dict keys
                self.fields[field] = val
        versrel = self.fields['version'].rsplit('-', 1)
        if len(versrel) == 2:
            self.fields['version'] = versrel[0]
            self.fields['release'] = versrel[1]
        else:
            self.fields['release'] = None
        verep = self.fields['version'].split(':', 1)
        if len(verep) == 2:
            self.fields['epoch'] = verep[0]
            self.fields['version'] = verep[1]
        else:
            self.fields['epoch'] = '0'
        self.fields['provides'] = [ i.strip() for i in re.split(',\s*', self.fields.get('provides', '')) if i ]
        self.fields['depends'] = [ i.strip() for i in re.split(',\s*', self.fields.get('depends', '')) if i ]
        self.fields['pre_depends'] = [ i.strip() for i in re.split(',\s*', self.fields.get('pre_depends', '')) if i ]
        if self_provides:
            # add self provides entry
            self.fields['provides'].append('%s = %s' % (self.name(), '-'.join(versrel)))

    def vercmp(self, debq):
        res = cmp(int(self.epoch()), int(debq.epoch()))
        if res != 0:
            return res
        res = DebQuery.debvercmp(self.version(), debq.version())
        if res != None:
            return res
        res = DebQuery.debvercmp(self.release(), debq.release())
        return res

    def name(self):
        return self.fields['package']

    def version(self):
        return self.fields['version']

    def release(self):
        return self.fields['release']

    def epoch(self):
        return self.fields['epoch']

    def arch(self):
        return self.fields['architecture']

    def description(self):
        return self.fields['description']

    def path(self):
        return self.__path

    def provides(self):
        return self.fields['provides']

    def requires(self):
        return self.fields['depends']

    def gettag(self, num):
        return self.fields.get(num, None)

    def canonname(self):
        return DebQuery.filename(self.name(), self.epoch(), self.version(), self.release(), self.arch())

    @staticmethod
    def query(filename, all_tags = False, *extra_tags):
        f = open(filename, 'rb')
        debq = DebQuery(f)
        debq.read(all_tags, *extra_tags)
        f.close()
        return debq

    @staticmethod
    def debvercmp(ver1, ver2):
        """
        implementation of dpkg's version comparison algorithm
        """
        # 32 is arbitrary - it is needed for the "longer digit string wins" handling
        # (found this nice approach in Build/Deb.pm (build package))
        ver1 = re.sub('(\d+)', lambda m: (32 * '0' + m.group(1))[-32:], ver1)
        ver2 = re.sub('(\d+)', lambda m: (32 * '0' + m.group(1))[-32:], ver2)
        vers = map(lambda x, y: (x or '', y or ''), ver1, ver2)
        for v1, v2 in vers:
            if v1 == v2:
                continue
            if (v1.isalpha() and v2.isalpha()) or (v1.isdigit() and v2.isdigit()):
                res = cmp(v1, v2)
                if res != 0:
                    return res
            else:
                if v1 == '~' or not v1:
                    return -1
                elif v2 == '~' or not v2:
                    return 1
                ord1 = ord(v1)
                if not (v1.isalpha() or v1.isdigit()):
                    ord1 += 256
                ord2 = ord(v2)
                if not (v2.isalpha() or v2.isdigit()):
                    ord2 += 256
                if ord1 > ord2:
                    return 1
                else:
                    return -1
        return 0

    @staticmethod
    def filename(name, epoch, version, release, arch):
        if release:
            return '%s_%s-%s_%s.deb' % (name, version, release, arch)
        else:
            return '%s_%s_%s.deb' % (name, version, arch)

if __name__ == '__main__':
    import sys
    try:
        debq = DebQuery.query(sys.argv[1])
    except DebError as e:
        print(e.msg)
        sys.exit(2)
    print(debq.name(), debq.version(), debq.release(), debq.arch())
    print(debq.description())
    print('##########')
    print('\n'.join(debq.provides()))
    print('##########')
    print('\n'.join(debq.requires()))

########NEW FILE########
__FILENAME__ = packagequery

from __future__ import print_function

class PackageError(Exception):
    """base class for all package related errors"""
    def __init__(self, fname, msg):
        Exception.__init__(self)
        self.fname = fname
        self.msg = msg

class PackageQueries(dict):
    """Dict of package name keys and package query values.  When assigning a
    package query, to a name, the package is evaluated to see if it matches the
    wanted architecture and if it has a greater version than the current value.
    """

    # map debian arches to common obs arches
    architectureMap = {'i386': ['i586', 'i686'], 'amd64': ['x86_64']}

    def __init__(self, wanted_architecture):
        self.wanted_architecture = wanted_architecture
        super(PackageQueries, self).__init__()

    def add(self, query):
        """Adds package query to dict if it is of the correct architecture and
        is newer (has a greater version) than the currently assigned package.

        @param a PackageQuery
        """
        self.__setitem__(query.name(), query)

    def __setitem__(self, name, query):
        if name != query.name():
            raise ValueError("key '%s' does not match "
                             "package query name '%s'" % (name, query.name()))

        architecture = query.arch()

        if (architecture in [self.wanted_architecture, 'noarch', 'all', 'any']
            or self.wanted_architecture in self.architectureMap.get(architecture,
                                                                [])):
            current_query = self.get(name)

            # if current query does not exist or is older than this new query
            if current_query is None or current_query.vercmp(query) <= 0:
                super(PackageQueries, self).__setitem__(name, query)

class PackageQuery:
    """abstract base class for all package types"""
    def read(self, all_tags = False, *extra_tags):
        raise NotImplementedError

    def name(self):
        raise NotImplementedError

    def version(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    def epoch(self):
        raise NotImplementedError

    def arch(self):
        raise NotImplementedError

    def description(self):
        raise NotImplementedError

    def path(self):
        raise NotImplementedError

    def provides(self):
        raise NotImplementedError

    def requires(self):
        raise NotImplementedError

    def gettag(self):
        raise NotImplementedError

    def vercmp(self, pkgquery):
        raise NotImplementedError

    def canonname(self):
        raise NotImplementedError

    @staticmethod
    def query(filename, all_tags=False, extra_rpmtags=(), extra_debtags=(), self_provides=True):
        f = open(filename, 'rb')
        magic = f.read(7)
        f.seek(0)
        extra_tags = ()
        pkgquery = None
        if magic[:4] == '\xed\xab\xee\xdb':
            from . import rpmquery
            pkgquery = rpmquery.RpmQuery(f)
            extra_tags = extra_rpmtags
        elif magic == '!<arch>':
            from . import debquery
            pkgquery = debquery.DebQuery(f)
            extra_tags = extra_debtags
        elif magic[:5] == '<?xml':
            f.close()
            return None
        elif magic[:5] == '\375\067zXZ' or magic[:2] == '\037\213':
            from . import archquery
            pkgquery = archquery.ArchQuery(f)
        else:
            raise PackageError(filename, 'unsupported package type. magic: \'%s\'' % magic)
        pkgquery.read(all_tags, self_provides, *extra_tags)
        f.close()
        return pkgquery

if __name__ == '__main__':
    import sys
    try:
        pkgq = PackageQuery.query(sys.argv[1])
    except PackageError as e:
        print(e.msg)
        sys.exit(2)
    print(pkgq.name())
    print(pkgq.version())
    print(pkgq.release())
    print(pkgq.description())
    print('##########')
    print('\n'.join(pkgq.provides()))
    print('##########')
    print('\n'.join(pkgq.requires()))

########NEW FILE########
__FILENAME__ = repodata
"""Module for reading repodata directory (created with createrepo) for package
information instead of scanning individual rpms."""

# standard modules
import gzip
import os.path

# cElementTree can be standard or 3rd-party depending on python version
try:
    from xml.etree import cElementTree as ET
except ImportError:
    import cElementTree as ET

# project modules
import osc.util.rpmquery

def namespace(name):
    return "{http://linux.duke.edu/metadata/%s}" % name

OPERATOR_BY_FLAGS = {
    "EQ" : "=",
    "LE" : "<=",
    "GE" : ">="
}

def primaryPath(directory):
    """Returns path to the primary repository data file.

    @param directory repository directory that contains the repodata subdirectory
    @return str path to primary repository data file
    @raise IOError if repomd.xml contains no primary location
    """
    metaDataPath = os.path.join(directory, "repodata", "repomd.xml")
    elementTree = ET.parse(metaDataPath)
    root = elementTree.getroot()

    for dataElement in root:
        if dataElement.get("type") == "primary":
            locationElement = dataElement.find(namespace("repo") + "location")
            # even though the repomd.xml file is under repodata, the location a
            # attribute is relative to parent directory (directory).
            primaryPath = os.path.join(directory, locationElement.get("href"))
            break
    else:
        raise IOError("'%s' contains no primary location" % metaDataPath)

    return primaryPath

def queries(directory):
    """Returns a list of RepoDataQueries constructed from the repodata under
    the directory.

    @param directory path to a repository directory (parent directory of
                     repodata directory)
    @return list of RepoDataQuery instances
    @raise IOError if repomd.xml contains no primary location
    """
    path = primaryPath(directory)

    gunzippedPrimary = gzip.GzipFile(path)
    elementTree = ET.parse(gunzippedPrimary)
    root = elementTree.getroot()

    packageQueries = []
    for packageElement in root:
        packageQuery = RepoDataQuery(directory, packageElement)
        packageQueries.append(packageQuery)

    return packageQueries

class RepoDataQuery(object):
    """PackageQuery that reads in data from the repodata directory files."""

    def __init__(self, directory, element):
        """Creates a RepoDataQuery from the a package Element under a metadata
        Element in a primary.xml file.

        @param directory repository directory path.  Used to convert relative
                         paths to full paths.
        @param element package Element
        """
        self.__directory = os.path.abspath(directory)
        self.__element = element

    def __formatElement(self):
        return self.__element.find(namespace("common") + "format")

    def __parseEntry(self, element):
        entry = element.get("name")
        flags = element.get("flags")

        if flags is not None:
            version = element.get("ver")
            operator = OPERATOR_BY_FLAGS[flags]
            entry += " %s %s" % (operator, version)

            release = element.get("rel")
            if release is not None:
                entry += "-%s" % release

        return entry

    def __parseEntryCollection(self, collection):
        formatElement = self.__formatElement()
        collectionElement = formatElement.find(namespace("rpm") + collection)

        entries = []
        if collectionElement is not None:
            for entryElement in collectionElement.findall(namespace("rpm") +
                                                          "entry"):
                entry = self.__parseEntry(entryElement)
                entries.append(entry)

        return entries

    def __versionElement(self):
        return self.__element.find(namespace("common") + "version")

    def arch(self):
        return self.__element.find(namespace("common") + "arch").text

    def description(self):
        return self.__element.find(namespace("common") + "description").text

    def distribution(self):
        return None

    def epoch(self):
        return self.__versionElement().get("epoch")

    def name(self):
        return self.__element.find(namespace("common") + "name").text

    def path(self):
        locationElement = self.__element.find(namespace("common") + "location")
        relativePath = locationElement.get("href")
        absolutePath = os.path.join(self.__directory, relativePath)

        return absolutePath

    def provides(self):
        return self.__parseEntryCollection("provides")

    def release(self):
        return self.__versionElement().get("rel")

    def requires(self):
        return self.__parseEntryCollection("requires")

    def vercmp(self, other):
        res = osc.util.rpmquery.RpmQuery.rpmvercmp(str(self.epoch()), str(other.epoch()))
        if res != 0:
            return res
        res = osc.util.rpmquery.RpmQuery.rpmvercmp(self.version(), other.version())
        if res != 0:
            return res
        res = osc.util.rpmquery.RpmQuery.rpmvercmp(self.release(), other.release())
        return res

    def version(self):
        return self.__versionElement().get("ver")

########NEW FILE########
__FILENAME__ = rpmquery

from __future__ import print_function

import os
import re
import struct
from . import packagequery

class RpmError(packagequery.PackageError):
    pass

class RpmHeaderError(RpmError):
    pass

class RpmHeader:
    """corresponds more or less to the indexEntry_s struct"""
    def __init__(self, offset, length):
        self.offset = offset
        # length of the data section (without length of indexEntries)
        self.length = length
        self.entries = []

    def append(self, entry):
        self.entries.append(entry)

    def gettag(self, tag):
        for i in self.entries:
            if i.tag == tag:
                return i
        return None

    def __iter__(self):
        for i in self.entries:
            yield i

    def __len__(self):
        return len(self.entries)

class RpmHeaderEntry:
    """corresponds to the entryInfo_s struct (except the data attribute)"""

    # each element represents an int
    ENTRY_SIZE = 16
    def __init__(self, tag, type, offset, count):
        self.tag = tag
        self.type = type
        self.offset = offset
        self.count = count
        self.data = None

class RpmQuery(packagequery.PackageQuery):
    LEAD_SIZE = 96
    LEAD_MAGIC = 0xedabeedb
    HEADER_MAGIC = 0x8eade801
    HEADERSIG_TYPE = 5

    LESS = 1 << 1
    GREATER = 1 << 2
    EQUAL = 1 << 3

    default_tags = (1000, 1001, 1002, 1003, 1004, 1022, 1005, 1020,
        1047, 1112, 1113, # provides
        1049, 1048, 1050 # requires
    )

    def __init__(self, fh):
        self.__file = fh
        self.__path = os.path.abspath(fh.name)
        self.filename_suffix = 'rpm'
        self.header = None

    def read(self, all_tags=False, self_provides=True, *extra_tags):
        # self_provides is unused because a rpm always has a self provides
        self.__read_lead()
        data = self.__file.read(RpmHeaderEntry.ENTRY_SIZE)
        hdrmgc, reserved, il, dl = struct.unpack('!I3i', data)
        if self.HEADER_MAGIC != hdrmgc:
            raise RpmHeaderError(self.__path, 'invalid headermagic \'%s\'' % hdrmgc)
        # skip signature header for now
        size = il * RpmHeaderEntry.ENTRY_SIZE + dl
        # data is 8 byte aligned
        pad = (size + 7) & ~7
        self.__file.read(pad)
        data = self.__file.read(RpmHeaderEntry.ENTRY_SIZE)
        hdrmgc, reserved, il, dl = struct.unpack('!I3i', data)
        self.header = RpmHeader(pad, dl)
        if self.HEADER_MAGIC != hdrmgc:
            raise RpmHeaderError(self.__path, 'invalid headermagic \'%s\'' % hdrmgc)
        data = self.__file.read(il * RpmHeaderEntry.ENTRY_SIZE)
        while len(data) > 0:
            ei = struct.unpack('!4i', data[:RpmHeaderEntry.ENTRY_SIZE])
            self.header.append(RpmHeaderEntry(*ei))
            data = data[RpmHeaderEntry.ENTRY_SIZE:]
        data = self.__file.read(self.header.length)
        for i in self.header:
            if i.tag in self.default_tags + extra_tags or all_tags:
                try: # this may fail for -debug* packages
                    self.__read_data(i, data)
                except: pass

    def __read_lead(self):
        data = self.__file.read(self.LEAD_SIZE)
        leadmgc, = struct.unpack('!I', data[:4])
        if leadmgc != self.LEAD_MAGIC:
            raise RpmError(self.__path, 'invalid lead magic \'%s\'' % leadmgc)
        sigtype, = struct.unpack('!h', data[78:80])
        if sigtype != self.HEADERSIG_TYPE:
            raise RpmError(self.__path, 'invalid header signature \'%s\'' % sigtype)

    def __read_data(self, entry, data):
        off = entry.offset
        if entry.type == 2:
            entry.data = struct.unpack('!%dc' % entry.count, data[off:off + 1 * entry.count])
        if entry.type == 3:
            entry.data = struct.unpack('!%dh' % entry.count, data[off:off + 2 * entry.count])
        elif entry.type == 4:
            entry.data = struct.unpack('!%di' % entry.count, data[off:off + 4 * entry.count])
        elif entry.type == 6 or entry.type == 7:
            # XXX: what to do with binary data? for now treat it as a string
            entry.data = unpack_string(data[off:])
        elif entry.type == 8 or entry.type == 9:
            cnt = entry.count
            entry.data = []
            while cnt > 0:
                cnt -= 1
                s = unpack_string(data[off:])
                # also skip '\0'
                off += len(s) + 1
                entry.data.append(s)
            if entry.type == 8:
                return
            lang = os.getenv('LANGUAGE') or os.getenv('LC_ALL') \
                or os.getenv('LC_MESSAGES') or os.getenv('LANG')
            if lang is None:
                entry.data = entry.data[0]
                return
            # get private i18n table
            table = self.header.gettag(100)
            # just care about the country code
            lang = lang.split('_', 1)[0]
            cnt = 0
            for i in table.data:
                if cnt > len(entry.data) - 1:
                    break
                if i == lang:
                    entry.data = entry.data[cnt]
                    return
                cnt += 1
            entry.data = entry.data[0]
        else:
            raise RpmHeaderError(self.__path, 'unsupported tag type \'%d\' (tag: \'%s\'' % (entry.type, entry.tag))

    def __reqprov(self, tag, flags, version):
        pnames = self.header.gettag(tag).data
        pflags = self.header.gettag(flags).data
        pvers = self.header.gettag(version).data
        if not (pnames and pflags and pvers):
            raise RpmError(self.__path, 'cannot get provides/requires, tags are missing')
        res = []
        for name, flags, ver in zip(pnames, pflags, pvers):
            # RPMSENSE_SENSEMASK = 15 (see rpmlib.h) but ignore RPMSENSE_SERIAL (= 1 << 0) therefore use 14
            if flags & 14:
                name += ' '
                if flags & self.GREATER:
                    name += '>'
                elif flags & self.LESS:
                    name += '<'
                if flags & self.EQUAL:
                    name += '='
                name += ' %s' % ver
            res.append(name)
        return res

    def vercmp(self, rpmq):
        res = RpmQuery.rpmvercmp(str(self.epoch()), str(rpmq.epoch()))
        if res != 0:
            return res
        res = RpmQuery.rpmvercmp(self.version(), rpmq.version())
        if res != 0:
            return res
        res = RpmQuery.rpmvercmp(self.release(), rpmq.release())
        return res

    # XXX: create dict for the tag => number mapping?!
    def name(self):
        return self.header.gettag(1000).data

    def version(self):
        return self.header.gettag(1001).data

    def release(self):
        return self.header.gettag(1002).data

    def epoch(self):
        epoch = self.header.gettag(1003)
        if epoch is None:
            return 0
        return epoch.data[0]

    def arch(self):
        return self.header.gettag(1022).data

    def summary(self):
        return self.header.gettag(1004).data

    def description(self):
        return self.header.gettag(1005).data

    def url(self):
        entry = self.header.gettag(1020)
        if entry is None:
            return None
        return entry.data

    def path(self):
        return self.__path

    def provides(self):
        return self.__reqprov(1047, 1112, 1113)

    def requires(self):
        return self.__reqprov(1049, 1048, 1050)

    def is_src(self):
        # SOURCERPM = 1044
        return self.gettag(1044) is None

    def is_nosrc(self):
        # NOSOURCE = 1051, NOPATCH = 1052
        return self.is_src() and \
            (self.gettag(1051) is not None or self.gettag(1052) is not None)

    def gettag(self, num):
        return self.header.gettag(num)

    def canonname(self):
        if self.is_nosrc():
            arch = 'nosrc'
        elif self.is_src():
            arch = 'src'
        else:
            arch = self.arch()
        return RpmQuery.filename(self.name(), None, self.version(), self.release(), arch)

    @staticmethod
    def query(filename):
        f = open(filename, 'rb')
        rpmq = RpmQuery(f)
        rpmq.read()
        f.close()
        return rpmq

    @staticmethod
    def rpmvercmp(ver1, ver2):
        """
        implementation of RPM's version comparison algorithm
        (as described in lib/rpmvercmp.c)
        """
        if ver1 == ver2:
            return 0
        res = 0
        while res == 0:
            # remove all leading non alphanumeric chars
            ver1 = re.sub('^[^a-zA-Z0-9]*', '', ver1)
            ver2 = re.sub('^[^a-zA-Z0-9]*', '', ver2)
            if not (len(ver1) and len(ver2)):
                break
            # check if we have a digits segment
            mo1 = re.match('(\d+)', ver1)
            mo2 = re.match('(\d+)', ver2)
            numeric = True
            if mo1 is None:
                mo1 = re.match('([a-zA-Z]+)', ver1)
                mo2 = re.match('([a-zA-Z]+)', ver2)
                numeric = False
            # check for different types: alpha and numeric
            if mo2 is None:
                if numeric:
                    return 1
                return -1
            seg1 = mo1.group(0)
            ver1 = ver1[mo1.end(0):]
            seg2 = mo2.group(1)
            ver2 = ver2[mo2.end(1):]
            if numeric:
                # remove leading zeros
                seg1 = re.sub('^0+', '', seg1)
                seg2 = re.sub('^0+', '', seg2)
                # longer digit segment wins - if both have the same length
                # a simple ascii compare decides
                res = len(seg1) - len(seg2) or cmp(seg1, seg2)
            else:
                res = cmp(seg1, seg2)
        if res > 0:
            return 1
        elif res < 0:
            return -1
        return cmp(ver1, ver2)

    @staticmethod
    def filename(name, epoch, version, release, arch):
        return '%s-%s-%s.%s.rpm' % (name, version, release, arch)

def unpack_string(data):
    """unpack a '\\0' terminated string from data"""
    val = ''
    for c in data:
        c, = struct.unpack('!c', c)
        if c == '\0':
            break
        else:
            val += c
    return val

if __name__ == '__main__':
    import sys
    try:
        rpmq = RpmQuery.query(sys.argv[1])
    except RpmError as e:
        print(e.msg)
        sys.exit(2)
    print(rpmq.name(), rpmq.version(), rpmq.release(), rpmq.arch(), rpmq.url())
    print(rpmq.summary())
    print(rpmq.description())
    print('##########')
    print('\n'.join(rpmq.provides()))
    print('##########')
    print('\n'.join(rpmq.requires()))

########NEW FILE########
__FILENAME__ = safewriter
# be careful when debugging this code:
# don't add print statements when setting sys.stdout = SafeWriter(sys.stdout)...
class SafeWriter:
    """
    Safely write an (unicode) str. In case of an "UnicodeEncodeError" the
    the str is encoded with the "encoding" encoding.
    All getattr, setattr calls are passed through to the "writer" instance.
    """
    def __init__(self, writer, encoding='unicode_escape'):
        self.__dict__['writer'] = writer
        self.__dict__['encoding'] = encoding

    def __get_writer(self):
        return self.__dict__['writer']

    def __get_encoding(self):
        return self.__dict__['encoding']

    def write(self, s):
        try:
            self.__get_writer().write(s)
        except UnicodeEncodeError as e:
            self.__get_writer().write(s.encode(self.__get_encoding()))

    def __getattr__(self, name):
        return getattr(self.__get_writer(), name)

    def __setattr__(self, name, value):
        setattr(self.__get_writer(), name, value)

########NEW FILE########
__FILENAME__ = osc-wrapper
#!/usr/bin/env python

# this wrapper exists so it can be put into /usr/bin, but still allows the
# python module to be called within the source directory during development

import locale
import sys

from osc import commandline, babysitter

try:
# this is a hack to make osc work as expected with utf-8 characters,
# no matter how site.py is set...
    reload(sys)
    loc = locale.getpreferredencoding()
    if not loc:
        loc = sys.getpreferredencoding()
    sys.setdefaultencoding(loc)
    del sys.setdefaultencoding
except NameError:
    #reload, neither setdefaultencoding are in python3
    pass

osccli = commandline.Osc()

r = babysitter.run(osccli)
sys.exit(r)

########NEW FILE########
__FILENAME__ = osc_hotshot
#!/usr/bin/env python

import hotshot, hotshot.stats
import tempfile
import os, sys

from osc import commandline


if __name__ == '__main__':

    (fd, filename) = tempfile.mkstemp(prefix = 'osc_profiledata_', dir = '/dev/shm')
    f = os.fdopen(fd)

    try:

        prof = hotshot.Profile(filename)

        prof.runcall(commandline.main)
        print 'run complete. analyzing.'
        prof.close()

        stats = hotshot.stats.load(filename)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(20)

        del stats

    finally:
        f.close()
        os.unlink(filename)

########NEW FILE########
__FILENAME__ = common
import unittest
import osc.core
import shutil
import tempfile
import os
import sys
from xml.etree import cElementTree as ET
EXPECTED_REQUESTS = []

if sys.version_info[0:2] in ((2, 6), (2, 7)):
    bytes = lambda x, *args: x

try:
    #python 2.x
    from cStringIO import StringIO
    from urllib2 import HTTPHandler, addinfourl, build_opener
    from urlparse import urlparse, parse_qs
except ImportError:
    from io import StringIO
    from urllib.request import HTTPHandler, addinfourl, build_opener
    from urllib.parse import urlparse, parse_qs

def urlcompare(url, *args):
    """compare all components of url except query string - it is converted to
    dict, therefor different ordering does not makes url's different, as well
    as quoting of a query string"""

    components = urlparse(url)
    query_args = parse_qs(components.query)
    components = components._replace(query=None)

    if not args:
        return False

    for url in args:
        components2 = urlparse(url)
        query_args2 = parse_qs(components2.query)
        components2 = components2._replace(query=None)

        if  components != components2 or \
            query_args != query_args2:
            return False

    return True

class RequestWrongOrder(Exception):
    """raised if an unexpected request is issued to urllib2"""
    def __init__(self, url, exp_url, method, exp_method):
        Exception.__init__(self)
        self.url = url
        self.exp_url = exp_url
        self.method = method
        self.exp_method = exp_method

    def __str__(self):
        return '%s, %s, %s, %s' % (self.url, self.exp_url, self.method, self.exp_method)

class RequestDataMismatch(Exception):
    """raised if POSTed or PUTed data doesn't match with the expected data"""
    def __init__(self, url, got, exp):
        self.url = url
        self.got = got
        self.exp = exp

    def __str__(self):
        return '%s, %s, %s' % (self.url, self.got, self.exp)

class MyHTTPHandler(HTTPHandler):
    def __init__(self, exp_requests, fixtures_dir):
        HTTPHandler.__init__(self)
        self.__exp_requests = exp_requests
        self.__fixtures_dir = fixtures_dir

    def http_open(self, req):
        r = self.__exp_requests.pop(0)
        if not urlcompare(req.get_full_url(), r[1]) or req.get_method() != r[0]:
            raise RequestWrongOrder(req.get_full_url(), r[1], req.get_method(), r[0])
        if req.get_method() in ('GET', 'DELETE'):
            return self.__mock_GET(r[1], **r[2])
        elif req.get_method() in ('PUT', 'POST'):
            return self.__mock_PUT(req, **r[2])

    def __mock_GET(self, fullurl, **kwargs):
        return self.__get_response(fullurl, **kwargs)

    def __mock_PUT(self, req, **kwargs):
        exp = kwargs.get('exp', None)
        if exp is not None and 'expfile' in kwargs:
            raise RuntimeError('either specify exp or expfile')
        elif 'expfile' in kwargs:
            exp = open(os.path.join(self.__fixtures_dir, kwargs['expfile']), 'r').read()
        elif exp is None:
            raise RuntimeError('exp or expfile required')
        if exp is not None:
            if req.get_data() != bytes(exp, "utf-8"):
                raise RequestDataMismatch(req.get_full_url(), repr(req.get_data()), repr(exp))
        return self.__get_response(req.get_full_url(), **kwargs)

    def __get_response(self, url, **kwargs):
        f = None
        if 'exception' in kwargs:
            raise kwargs['exception']
        if 'text' not in kwargs and 'file' in kwargs:
            f = StringIO(open(os.path.join(self.__fixtures_dir, kwargs['file']), 'r').read())
        elif 'text' in kwargs and 'file' not in kwargs:
            f = StringIO(kwargs['text'])
        else:
            raise RuntimeError('either specify text or file')
        resp = addinfourl(f, {}, url)
        resp.code = kwargs.get('code', 200)
        resp.msg = ''
        return resp

def urldecorator(method, fullurl, **kwargs):
    def decorate(test_method):
        def wrapped_test_method(*args):
            addExpectedRequest(method, fullurl, **kwargs)
            test_method(*args)
        # "rename" method otherwise we cannot specify a TestCaseClass.testName
        # cmdline arg when using unittest.main()
        wrapped_test_method.__name__ = test_method.__name__
        return wrapped_test_method
    return decorate

def GET(fullurl, **kwargs):
    return urldecorator('GET', fullurl, **kwargs)

def PUT(fullurl, **kwargs):
    return urldecorator('PUT', fullurl, **kwargs)

def POST(fullurl, **kwargs):
    return urldecorator('POST', fullurl, **kwargs)

def DELETE(fullurl, **kwargs):
    return urldecorator('DELETE', fullurl, **kwargs)

def addExpectedRequest(method, url, **kwargs):
    global EXPECTED_REQUESTS
    EXPECTED_REQUESTS.append((method, url, kwargs))

class OscTestCase(unittest.TestCase):
    def setUp(self, copytree=True):
        oscrc = os.path.join(self._get_fixtures_dir(), 'oscrc')
        osc.core.conf.get_config(override_conffile=oscrc,
                                 override_no_keyring=True, override_no_gnome_keyring=True)
        os.environ['OSC_CONFIG'] = oscrc

        self.tmpdir = tempfile.mkdtemp(prefix='osc_test')
        if copytree:
            shutil.copytree(os.path.join(self._get_fixtures_dir(), 'osctest'), os.path.join(self.tmpdir, 'osctest'))
        global EXPECTED_REQUESTS
        EXPECTED_REQUESTS = []
        osc.core.conf._build_opener = lambda u: build_opener(MyHTTPHandler(EXPECTED_REQUESTS, self._get_fixtures_dir()))
        self.stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        self.assertTrue(len(EXPECTED_REQUESTS) == 0)
        sys.stdout = self.stdout
        try:
            shutil.rmtree(self.tmpdir)
        except:
            pass

    def _get_fixtures_dir(self):
        raise NotImplementedError('subclasses should implement this method')

    def _change_to_pkg(self, name):
        os.chdir(os.path.join(self.tmpdir, 'osctest', name))

    def _check_list(self, fname, exp):
        fname = os.path.join('.osc', fname)
        self.assertTrue(os.path.exists(fname))
        self.assertEqual(open(fname, 'r').read(), exp)

    def _check_addlist(self, exp):
        self._check_list('_to_be_added', exp)

    def _check_deletelist(self, exp):
        self._check_list('_to_be_deleted', exp)

    def _check_conflictlist(self, exp):
        self._check_list('_in_conflict', exp)

    def _check_status(self, p, fname, exp):
        self.assertEqual(p.status(fname), exp)

    def _check_digests(self, fname, *skipfiles):
        fname = os.path.join(self._get_fixtures_dir(), fname)
        self.assertEqual(open(os.path.join('.osc', '_files'), 'r').read(), open(fname, 'r').read())
        root = ET.parse(fname).getroot()
        for i in root.findall('entry'):
            if i.get('name') in skipfiles:
                continue
            self.assertTrue(os.path.exists(os.path.join('.osc', i.get('name'))))
            self.assertEqual(osc.core.dgst(os.path.join('.osc', i.get('name'))), i.get('md5'))

    def assertEqualMultiline(self, got, exp):
        if (got + exp).find('\n') == -1:
            self.assertEqual(got, exp)
        else:
            start_delim = "\n" + (" 8< ".join(["-----"] * 8)) + "\n"
            end_delim   = "\n" + (" >8 ".join(["-----"] * 8)) + "\n\n"
            self.assertEqual(got, exp,
                             "got:"      + start_delim + got + end_delim +
                             "expected:" + start_delim + exp + end_delim)

########NEW FILE########
