__FILENAME__ = api
from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from os.path import dirname, isdir, join

from conda import config
from conda import install
#from conda.utils import url_path
from conda.fetch import fetch_index
from conda.compat import iteritems, itervalues
from conda.resolve import Package


def _name_fn(fn):
    assert fn.endswith('.tar.bz2')
    return install.name_dist(fn[:-8])

def _fn2spec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2)[:2])

def _fn2fullspec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2))


def get_index(channel_urls=(), prepend=True, platform=None,
              use_cache=False, unknown=False):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    """
    channel_urls = config.normalize_urls(channel_urls, platform=platform)
    if prepend:
        channel_urls += config.get_channel_urls(platform=platform)
    return fetch_index(tuple(channel_urls), use_cache=use_cache,
                       unknown=unknown)


def app_get_index(all_version=False):
    """
    return the index of available applications on the channels

    By default only the latest version of each app is included in the result,
    unless all_version is set to True.
    """
    index = {fn: info for fn, info in iteritems(get_index())
             if info.get('type') == 'app'}
    if all_version:
        return index

    d = defaultdict(list) # name -> list of Package objects
    for fn, info in iteritems(index):
        d[_name_fn(fn)].append(Package(fn, info))

    res = {}
    for pkgs in itervalues(d):
        pkg = max(pkgs)
        res[pkg.fn] = index[pkg.fn]
    return res


def app_get_icon_url(fn):
    """
    return the URL belonging to the icon for application `fn`.
    """
    index = get_index()
    info = index[fn]
    base_url = dirname(info['channel'].rstrip('/'))
    icon_fn = info['icon']
    #icon_cache_path = join(config.pkgs_dir, 'cache', icon_fn)
    #if isfile(icon_cache_path):
    #    return url_path(icon_cache_path)
    return '%s/icons/%s' % (base_url, icon_fn)


def app_info_packages(fn):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies.
    Returns a list of tuples (pkg_name, pkg_version, size,
    fetched? True or False).
    """
    from conda.resolve import Resolve

    index = get_index()
    r = Resolve(index)
    res = []
    for fn2 in r.solve([_fn2fullspec(fn)]):
        info = index[fn2]
        res.append((info['name'], info['version'], info['size'],
                    any(install.is_fetched(pkgs_dir, fn2[:-8])
                        for pkgs_dir in config.pkgs_dirs)))
    return res


def app_is_installed(fn):
    """
    Return the list of prefix directories in which `fn` in installed into,
    which might be an empty list.
    """
    prefixes = [config.root_dir]
    for envs_dir in config.envs_dirs:
        for fn2 in os.listdir(envs_dir):
            prefix = join(envs_dir, fn2)
            if isdir(prefix):
                prefixes.append(prefix)
    dist = fn[:-8]
    return [prefix for prefix in prefixes if install.is_linked(prefix, dist)]

# It seems to me that we need different types of apps, i.e. apps which
# are preferably installed (or already exist) in existing environments,
# and apps which are more "standalone" (such as firefox).

def app_install(fn, prefix=config.root_dir):
    """
    Install the application `fn` into prefix (which defauts to the root
    environment).
    """
    import conda.plan as plan

    index = get_index()
    actions = plan.install_actions(prefix, index, [_fn2spec(fn)])
    plan.execute_actions(actions, index)


def app_launch(fn, prefix=config.root_dir, additional_args=None):
    """
    Launch the application `fn` (with optional additional command line
    arguments), in the prefix (which defaults to the root environment).
    Returned is the process object (the one returned by subprocess.Popen),
    or None if the application `fn` is not installed in the prefix.
    """
    from conda.misc import launch

    return launch(fn, prefix, additional_args)


def app_uninstall(fn, prefix=config.root_dir):
    """
    Uninstall application `fn` (but not its dependencies).

    Like `conda remove fn`.

    """
    import conda.cli.common as common
    import conda.plan as plan

    index = None
    specs = [_fn2spec(fn)]
    if (plan.is_root_prefix(prefix) and
        common.names_in_specs(common.root_no_rm, specs)):
        raise ValueError("Cannot remove %s from the root environment" %
                         ', '.join(common.root_no_rm))

    actions = plan.remove_actions(prefix, specs)

    if plan.nothing_to_do(actions):
        raise ValueError("Nothing to do")

    plan.execute_actions(actions, index)


if __name__ == '__main__':
    #from pprint import pprint
    for fn in app_get_index():
        print('%s: %s' % (fn, app_is_installed(fn)))
    #pprint(missing_packages('twisted-12.3.0-py27_0.tar.bz2'))
    #print(app_install('twisted-12.3.0-py27_0.tar.bz2'))
    #pprint(get_index())
    #print(app_get_icon_url('spyder-app-2.2.0-py27_0.tar.bz2'))

########NEW FILE########
__FILENAME__ = bundle
from __future__ import print_function, division, absolute_import

import os
import sys
import json
import time
import shutil
import hashlib
import tarfile
import tempfile
from os.path import abspath, expanduser, basename, isdir, isfile, islink, join

import conda.config as config
from conda.api import get_index
from conda.misc import untracked, discard_conda
import conda.install as install
import conda.plan as plan


ISO8601 = "%Y-%m-%d %H:%M:%S %z"
BDP = 'bundle-data/'

warn = []


def add_file(t, path, f):
    t.add(path, f)
    if islink(path):
        link = os.readlink(path)
        if link.startswith('/'):
            warn.append('found symlink to absolute path: %s -> %s' % (f, link))
    elif isfile(path):
        if path.endswith('.egg-link'):
            warn.append('found egg link: %s' % f)

def add_data(t, data_path):
    data_path = abspath(data_path)
    if isfile(data_path):
        f = BDP + basename(data_path)
        add_file(t, data_path, f)
    elif isdir(data_path):
        for root, dirs, files in os.walk(data_path):
            for fn in files:
                if fn.endswith(('~', '.pyc')):
                    continue
                path = join(root, fn)
                f = path[len(data_path) + 1:]
                if f.startswith('.git'):
                    continue
                add_file(t, path, BDP + f)
    else:
        raise RuntimeError('no such file or directory: %s' % data_path)


def add_info_files(t, meta):
    tmp_dir = tempfile.mkdtemp()
    with open(join(tmp_dir, 'index.json'), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)
    with open(join(tmp_dir, 'files'), 'w') as fo:
        for m in t.getmembers():
            fo.write(m.path + '\n')
    for fn in 'index.json', 'files':
        add_file(t, join(tmp_dir, fn), 'info/' + fn)
    shutil.rmtree(tmp_dir)


def get_version(meta):
    s = '%(creator)s:%(bundle_name)s' % meta
    h = hashlib.new('sha1')
    h.update(s.encode('utf-8'))
    return h.hexdigest()


def create_bundle(prefix=None, data_path=None, bundle_name=None,
                  extra_meta=None):
    """
    Create a "bundle" of the environment located in `prefix`,
    and return the full path to the created package, which is going to be
    located in the current working directory, unless specified otherwise.
    """
    meta = dict(
        name = 'bundle',
        build = '0', build_number = 0,
        type = 'bundle',
        bundle_name = bundle_name,
        creator = os.getenv('USER'),
        platform = config.platform,
        arch = config.arch_name,
        ctime = time.strftime(ISO8601),
        depends = [],
    )
    meta['version'] = get_version(meta)

    tar_path = join('bundle-%(version)s-0.tar.bz2' % meta)
    t = tarfile.open(tar_path, 'w:bz2')
    if prefix:
        prefix = abspath(prefix)
        if not prefix.startswith('/opt/anaconda'):
            for f in sorted(untracked(prefix, exclude_self_build=True)):
                if f.startswith(BDP):
                    raise RuntimeError('bad untracked file: %s' % f)
                if f.startswith('info/'):
                    continue
                path = join(prefix, f)
                add_file(t, path, f)
        meta['bundle_prefix'] = prefix
        meta['depends'] = [' '.join(dist.rsplit('-', 2)) for dist in
                           sorted(install.linked(prefix))]

    if data_path:
        add_data(t, data_path)

    if extra_meta:
        meta.update(extra_meta)

    add_info_files(t, meta)
    t.close()
    return tar_path


def clone_bundle(path, prefix=None, bundle_name=None):
    """
    Clone the bundle (located at `path`) by creating a new environment at
    `prefix` (unless prefix is None or the prefix directory already exists)
    """
    try:
        t = tarfile.open(path, 'r:*')
        meta = json.load(t.extractfile('info/index.json'))
    except tarfile.ReadError:
        raise RuntimeError('bad tar archive: %s' % path)
    except KeyError:
        raise RuntimeError("no archive 'info/index.json' in: %s" % (path))

    if prefix and not isdir(prefix):
        for m in t.getmembers():
            if m.path.startswith((BDP, 'info/')):
                continue
            t.extract(m, path=prefix)
        dists = discard_conda('-'.join(s.split())
                              for s in meta.get('depends', []))
        actions = plan.ensure_linked_actions(dists, prefix)
        index = get_index()
        plan.display_actions(actions, index)
        plan.execute_actions(actions, index, verbose=True)

    bundle_dir = abspath(expanduser('~/bundles/%s' %
                                    (bundle_name or meta.get('bundle_name'))))
    for m in t.getmembers():
        if m.path.startswith(BDP):
            targetpath = join(bundle_dir, m.path[len(BDP):])
            t._extract_member(m, targetpath)

    t.close()


if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError:
        path = 'bundle-90809033a16372615e953f6961a6a272a4b35a1a.tar.bz2'
    clone_bundle(path,
                 join(config.envs_dirs[0], 'tc001'))

########NEW FILE########
__FILENAME__ = activate
from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isdir, join, abspath
import errno

from conda.cli.common import find_prefix_name
import conda.config
import conda.install

def help():
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    if sys.argv[1] in ('..activate', '..checkenv'):
        sys.exit("""Usage: source activate ENV

adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    else: # ..deactivate
        sys.exit("""Usage: source deactivate

removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)


def prefix_from_arg(arg):
    if os.sep in arg:
        return abspath(arg)
    prefix = find_prefix_name(arg)
    if prefix is None:
        sys.exit('Error: could not find environment: %s' % arg)
    return prefix


def binpath_from_arg(arg):
    path = join(prefix_from_arg(arg), 'bin')
    if not isdir(path):
        sys.exit("Error: no such directory: %s" % path)
    return path

def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        help()

    if sys.argv[1] == '..activate':
        if len(sys.argv) == 2:
            sys.exit("Error: no environment provided.")
        elif len(sys.argv) == 3:
            binpath = binpath_from_arg(sys.argv[2])
        else:
            sys.exit("Error: did not expect more than one argument")

        paths = [binpath]
        sys.stderr.write("prepending %s to PATH\n" % binpath)

    elif sys.argv[1] == '..deactivate':
        if len(sys.argv) != 2:
            sys.exit("Error: too many arguments.")

        try:
            binpath = binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV', 'root'))
        except SystemExit:
            print(os.environ['PATH'])
            raise
        paths = []
        sys.stderr.write("discarding %s from PATH\n" % binpath)

    elif sys.argv[1] == '..activateroot':
        if len(sys.argv) != 2:
            sys.exit("Error: too many arguments.")

        if 'CONDA_DEFAULT_ENV' not in os.environ:
            sys.exit("Error: No environment to deactivate")
        try:
            binpath = binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV'))
            rootpath = binpath_from_arg(conda.config.root_env_name)
        except SystemExit:
            print(os.environ['PATH'])
            raise
        # deactivate is the same as activate root (except without setting
        # CONDA_DEFAULT_ENV or PS1). XXX: The user might want to put the root
        # env back somewhere in the middle of the PATH, not at the beginning.
        if rootpath not in os.getenv('PATH').split(os.pathsep):
            paths = [rootpath]
        else:
            paths = []
        sys.stderr.write("discarding %s from PATH\n" % binpath)

    elif sys.argv[1] == '..checkenv':
        if len(sys.argv) < 3:
            sys.exit("Error: no environment provided.")
        if len(sys.argv) > 3:
            sys.exit("Error: did not expect more than one argument.")
        binpath = binpath_from_arg(sys.argv[2])
        # Make sure an env always has the conda symlink
        try:
            conda.install.symlink_conda(join(binpath, '..'), conda.config.root_dir)
        except (IOError, OSError) as e:
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                sys.exit("Cannot activate environment {}, do not have write access to write conda symlink".format(sys.argv[2]))
            raise
        sys.exit(0)

    else:
        # This means there is a bug in main.py
        raise ValueError("unexpected command")

    for path in os.getenv('PATH').split(os.pathsep):
        if path != binpath:
            paths.append(path)
    print(os.pathsep.join(paths))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = common
from __future__ import print_function, division, absolute_import

import re
import os
import sys
import argparse
from os.path import abspath, basename, expanduser, isdir, join

import conda.config as config


def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action = "store",
        help = "name of environment (in %s)" %
                            os.pathsep.join(config.envs_dirs),
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action = "store",
        help = "full path to environment prefix (default: %s)" %
                                           config.default_prefix,
        metavar = 'PATH',
    )


def add_parser_yes(p):
    p.add_argument(
        "--yes",
        action = "store_true",
        help = "do not ask for confirmation",
    )
    p.add_argument(
        "--dry-run",
        action = "store_true",
        help = "only display what would have been done",
    )


def add_parser_json(p):
    p.add_argument(
        "--json",
        action = "store_true",
        help = argparse.SUPPRESS,
    )


def add_parser_quiet(p):
    p.add_argument(
        '-q', "--quiet",
        action = "store_true",
        help = "do not display progress bar",
    )

def add_parser_channels(p):
    p.add_argument('-c', '--channel',
        action = "append",
        help = """additional channel to search for packages. These are URLs searched in the order
        they are given (including file:// for local directories).  Then, the defaults
        or channels from .condarc are searched (unless --override-channels is given).  You can use
        'defaults' to get the default packages for conda, and 'system' to get the system
        packages, which also takes .condarc into account.  You can also use any name and the
        .condarc channel_alias value will be prepended.  The default channel_alias
        is http://conda.binstar.org/""" # we can't put , here; invalid syntax
    )
    p.add_argument(
        "--override-channels",
        action = "store_true",
        help = """Do not search default or .condarc channels.  Requires --channel.""",
    )

def add_parser_known(p):
    p.add_argument(
        "--unknown",
        action="store_true",
        default=False,
        dest='unknown',
        help="use index metadata from the local package cache "
             "(which are from unknown channels)",
    )

def add_parser_use_index_cache(p):
    p.add_argument(
        "--use-index-cache",
        action="store_true",
        default=False,
        help = "use cache of channel index files",
    )

def add_parser_install(p):
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action = "store_true",
        help = "force install (even when package already installed), "
               "implies --no-deps",
    )
    p.add_argument(
        "--file",
        action = "store",
        help = "read package versions from FILE",
    )
    add_parser_known(p)
    p.add_argument(
        "--no-deps",
        action = "store_true",
        help = "do not install dependencies",
    )
    p.add_argument(
        '-m', "--mkdir",
        action = "store_true",
        help = "create prefix directory if necessary",
    )
    add_parser_use_index_cache(p)
    p.add_argument(
        "--use-local",
        action="store_true",
        default=False,
        help = "use locally built packages",
    )
    add_parser_no_pin(p)
    add_parser_channels(p)
    add_parser_prefix(p)
    add_parser_quiet(p)
    p.add_argument(
        "--alt-hint",
        action="store_true",
        default=False,
        help="Use an alternate algorithm to generate an unsatisfiable hint")
    p.add_argument(
        'packages',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "package versions to install into conda environment",
    )


def add_parser_no_pin(p):
    p.add_argument(
        "--no-pin",
        action="store_false",
        default=True,
        dest='pinned',
        help="don't use pinned packages",
    )

def ensure_override_channels_requires_channel(args, dashc=True):
    if args.override_channels and not args.channel:
        if dashc:
            sys.exit('Error: --override-channels requires -c/--channel')
        else:
            sys.exit('Error: --override-channels requires --channel')

def confirm(args, message="Proceed", choices=('yes', 'no'), default='yes'):
    assert default in choices, default
    if args.dry_run:
        print("Dry run: exiting")
        sys.exit(0)

    options = []
    for option in choices:
        if option == default:
            options.append('[%s]' % option[0])
        else:
            options.append(option[0])
    message = "%s (%s)? " % (message, '/'.join(options))
    choices = {alt:choice for choice in choices for alt in [choice,
                                                            choice[0]]}
    choices[''] = default
    while True:
        # raw_input has a bug and prints to stderr, not desirable
        sys.stdout.write(message)
        sys.stdout.flush()
        user_choice = sys.stdin.readline().strip().lower()
        if user_choice not in choices:
            print("Invalid choice: %s" % user_choice)
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return choices[user_choice]


def confirm_yn(args, message="Proceed", default='yes', exit_no=True):
    if args.dry_run:
        print("Dry run: exiting")
        sys.exit(0)
    if args.yes or config.always_yes:
        return True
    try:
        choice = confirm(args, message=message, choices=('yes', 'no'),
                         default=default)
    except KeyboardInterrupt:
        # no need to exit by showing the traceback
        sys.exit("\nOperation aborted.  Exiting.")
    if choice == 'yes':
        return True
    if exit_no:
        sys.exit(1)
    return False

# --------------------------------------------------------------------

def ensure_name_or_prefix(args, command):
    if not (args.name or args.prefix):
        sys.exit('Error: either -n NAME or -p PREFIX option required,\n'
                 '       try "conda %s -h" for more details' % command)

def find_prefix_name(name):
    if name == config.root_env_name:
        return config.root_dir
    for envs_dir in config.envs_dirs:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None

def get_prefix(args, search=True):
    if args.name:
        if '/' in args.name:
            sys.exit("Error: '/' not allowed in environment name: %s" %
                     args.name)
        if args.name == config.root_env_name:
            return config.root_dir
        if search:
            prefix = find_prefix_name(args.name)
            if prefix:
                return prefix
        return join(config.envs_dirs[0], args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return config.default_prefix

def inroot_notwritable(prefix):
    """
    return True if the prefix is under root and root is not writeable
    """
    return (abspath(prefix).startswith(config.root_dir) and
            not config.root_writable)

def name_prefix(prefix):
    if abspath(prefix) == config.root_dir:
        return config.root_env_name
    return basename(prefix)

def check_write(command, prefix):
    if inroot_notwritable(prefix):
        from conda.cli.help import root_read_only

        root_read_only(command, prefix)

# -------------------------------------------------------------------------

def arg2spec(arg):
    spec = spec_from_line(arg)
    if spec is None:
        sys.exit('Error: Invalid package specification: %s' % arg)
    parts = spec.split()
    name = parts[0]
    if name in config.disallow:
        sys.exit("Error: specification '%s' is disallowed" % name)
    if len(parts) == 2:
        ver = parts[1]
        if not ver.startswith(('=', '>', '<', '!')):
            if ver.endswith('.0'):
                return '%s %s|%s*' % (name, ver[:-2], ver)
            else:
                return '%s %s*' % (name, ver)
    return spec


def specs_from_args(args):
    return [arg2spec(arg) for arg in args]


spec_pat = re.compile(r'''
(?P<name>[^=<>!\s]+)               # package name
\s*                                # ignore spaces
(
  (?P<cc>=[^=<>!]+(=[^=<>!]+)?)    # conda constraint
  |
  (?P<pc>[=<>!]{1,2}.+)            # new (pip-style) constraint(s)
)?
$                                  # end-of-line
''', re.VERBOSE)
def spec_from_line(line):
    m = spec_pat.match(line)
    if m is None:
        return None
    name, cc, pc = (m.group('name').lower(), m.group('cc'), m.group('pc'))
    if cc:
        return name + cc.replace('=', ' ')
    elif pc:
        return name + ' ' + pc.replace(' ', '')
    else:
        return name


def specs_from_url(url):
    from conda.fetch import TmpDownload

    with TmpDownload(url, verbose=False) as path:
        specs = []
        try:
            for line in open(path):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                spec = spec_from_line(line)
                if spec is None:
                    sys.exit("Error: could not parse '%s' in: %s" %
                             (line, url))
                specs.append(spec)
        except IOError:
            sys.exit('Error: cannot open file: %s' % path)
    return specs


def names_in_specs(names, specs):
    return any(spec.split()[0] in names for spec in specs)


def check_specs(prefix, specs):
    from conda.plan import is_root_prefix

    if len(specs) == 0:
        sys.exit('Error: too few arguments, must supply command line '
                 'package specs or --file')

    if not is_root_prefix(prefix) and names_in_specs(['conda'], specs):
        sys.exit("Error: Package 'conda' may only be installed in the "
                 "root environment")


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')

root_no_rm = 'python', 'pycosat', 'pyyaml', 'conda'

########NEW FILE########
__FILENAME__ = conda_argparse
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
import argparse

from difflib import get_close_matches

from conda.cli.find_commands import find_commands

build_commands = {'build', 'index', 'skeleton', 'package', 'metapackage',
    'pipbuild', 'develop'}

class ArgumentParser(argparse.ArgumentParser):
    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        If only it were made available in the ArgumentError object. It is
        passed as it's first arg...
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if '/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        import re
        import subprocess
        from conda.cli.find_commands import find_executable

        exc = sys.exc_info()[1]
        if exc:
            # this is incredibly lame, but argparse stupidly does not expose
            # reasonable hooks for customizing error handling
            if hasattr(exc, 'argument_name'):
                argument = self._get_action_from_name(exc.argument_name)
            else:
                argument = None
            if argument and argument.dest == "cmd":
                m = re.compile(r"invalid choice: '(\w+)'").match(exc.message)
                if m:
                    cmd = m.group(1)
                    executable = find_executable(cmd)
                    if not executable:
                        if cmd in build_commands:
                            sys.exit("""\
Error: You need to install conda-build in order to use the 'conda %s'
       command.
""" % cmd)
                        else:
                            message = "Error: Could not locate 'conda-%s'" % cmd
                            conda_commands = set(find_commands())
                            close = get_close_matches(cmd,
                                set(argument.choices.keys()) | build_commands | conda_commands)
                            if close:
                                message += '\n\nDid you mean one of these?\n'
                                for s in close:
                                    message += '    %s' % s
                            sys.exit(message)
                    args = [find_executable(cmd)]
                    args.extend(sys.argv[2:])
                    try:
                        p = subprocess.Popen(args)
                        p.communicate()
                    except KeyboardInterrupt:
                        p.wait()
                    finally:
                        sys.exit(p.returncode)
        super(ArgumentParser, self).error(message)

    def print_help(self):
        super(ArgumentParser, self).print_help()

        if sys.argv[1:] in ([], ['help'], ['-h'], ['--help']):
            from conda.cli.find_commands import help
            help()

########NEW FILE########
__FILENAME__ = find_commands
from __future__ import print_function, division, absolute_import

import re
import os
import sys
import subprocess
from os.path import isdir, isfile, join

from conda.utils import memoized

if sys.platform == 'win32':
    dir_paths = [join(sys.prefix, 'Scripts')]
else:
    dir_paths = [join(sys.prefix, 'bin')]

dir_paths.extend(os.environ['PATH'].split(os.pathsep))


def find_executable(cmd):
    executable = 'conda-%s' % cmd
    for dir_path in dir_paths:
        if sys.platform == 'win32':
            for ext in  '.exe', '.bat':
                path = join(dir_path, executable + ext)
                if isfile(path):
                    return path
        else:
            path = join(dir_path, executable)
            if isfile(path):
                return path
    return None

@memoized
def find_commands():
    if sys.platform == 'win32':
        pat = re.compile(r'conda-(\w+)\.(exe|bat)$')
    else:
        pat = re.compile(r'conda-(\w+)$')

    res = set()
    for dir_path in dir_paths:
        if not isdir(dir_path):
            continue
        for fn in os.listdir(dir_path):
            m = pat.match(fn)
            if m:
                res.add(m.group(1))
    return sorted(res)


def filter_descr(cmd):
    args = [find_executable(cmd), '--help']
    try:
        output = subprocess.check_output(args)
    except (OSError, subprocess.CalledProcessError):
        print('failed: %s' % (' '.join(args)))
        return
    pat = re.compile(r'(\r?\n){2}(.*?)(\r?\n){2}')
    m = pat.search(output.decode('utf-8'))
    descr = '<could not extract description>' if m is None else m.group(2)
    print('    %-12s %s' % (cmd, descr))


def help():
    print("\nexternal commands:")
    for cmd in find_commands():
        filter_descr(cmd)


if __name__ == '__main__':
    help()

########NEW FILE########
__FILENAME__ = help
import sys
from os.path import join

import conda.config as config
from conda.cli.common import name_prefix



def read_message(fn):
    res = []
    for envs_dir in config.envs_dirs:
        path = join(envs_dir, '.conda-help', fn)
        try:
            with open(path) as fi:
                s = fi.read().decode('utf-8')
            s = s.replace('${envs_dir}', envs_dir)
            res.append(s)
        except IOError:
            pass
    return ''.join(res)


def root_read_only(command, prefix):
    assert command in {'install', 'update', 'remove'}

    msg = read_message('ro.txt')
    if not msg:
        msg = """\
Error: Missing write permissions in: ${root_dir}
#
# You don't appear to have the necessary permissions to ${command} packages
# into the install area '${root_dir}'.
# However you can clone this environment into your home directory and
# then make changes to it.
# This may be done using the command:
#
# $ conda create -n my_${name} --clone=${prefix}
"""
    msg = msg.replace('${root_dir}', config.root_dir)
    msg = msg.replace('${prefix}', prefix)
    msg = msg.replace('${name}', name_prefix(prefix))
    msg = msg.replace('${command}', command)
    sys.exit(msg)

########NEW FILE########
__FILENAME__ = install
# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
import shutil
import tarfile
import tempfile
from os.path import isdir, join, basename, exists, abspath

import conda.config as config
import conda.plan as plan
from conda.api import get_index
from conda.cli import pscheck
from conda.cli import common
from conda.misc import touch_nonadmin
from conda.resolve import Resolve, MatchSpec
import conda.install as ci


def install_tar(prefix, tar_path, verbose=False):
    from conda.misc import install_local_packages

    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'r')
    t.extractall(path=tmp_dir)
    t.close()

    paths = []
    for root, dirs, files in os.walk(tmp_dir):
        for fn in files:
            if fn.endswith('.tar.bz2'):
                paths.append(join(root, fn))

    install_local_packages(prefix, paths, verbose=verbose)

    shutil.rmtree(tmp_dir)


def check_prefix(prefix):
    from conda.config import root_env_name

    name = basename(prefix)
    if name.startswith('.'):
        sys.exit("Error: environment name cannot start with '.': %s" % name)
    if name == root_env_name:
        sys.exit("Error: '%s' is a reserved environment name" % name)
    if exists(prefix):
        sys.exit("Error: prefix already exists: %s" % prefix)


def clone(src_arg, dst_prefix):
    from conda.misc import clone_env

    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            sys.exit('Error: could such directory: %s' % src_arg)
    else:
        src_prefix = common.find_prefix_name(src_arg)
        if src_prefix is None:
            sys.exit('Error: could not find environment: %s' % src_arg)

    print("src_prefix: %r" % src_prefix)
    print("dst_prefix: %r" % dst_prefix)
    clone_env(src_prefix, dst_prefix)


def print_activate(arg):
    print("#")
    print("# To activate this environment, use:")
    if sys.platform == 'win32':
        print("# > activate %s" % arg)
    else:
        print("# $ source activate %s" % arg)
        print("#")
        print("# To deactivate this environment, use:")
        print("# $ source deactivate")
    print("#")


def get_revision(arg):
    try:
        return int(arg)
    except ValueError:
        sys.exit("Error: expected revision number, not: '%s'" % arg)


def install(args, parser, command='install'):
    """
    conda install, conda update, and conda create
    """
    newenv = bool(command == 'create')
    if newenv:
        common.ensure_name_or_prefix(args, command)
    prefix = common.get_prefix(args, search=not newenv)
    if newenv:
        check_prefix(prefix)

    if command == 'update':
        if args.all:
            if args.packages:
                sys.exit("""Error: --all cannot be used with packages""")
        else:
            if len(args.packages) == 0:
                sys.exit("""Error: no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix)

    if command == 'update':
        linked = ci.linked(prefix)
        for name in args.packages:
            common.arg2spec(name)
            if '=' in name:
                sys.exit("Invalid package name: '%s'" % (name))
            if name not in set(ci.name_dist(d) for d in linked):
                sys.exit("Error: package '%s' is not installed in %s" %
                         (name, prefix))

    if newenv and args.clone:
        if args.packages:
            sys.exit('Error: did not expect any arguments for --clone')
        clone(args.clone, prefix)
        touch_nonadmin(prefix)
        print_activate(args.name if args.name else prefix)
        return

    if newenv and not args.no_default_packages:
        default_packages = config.create_default_packages[:]
        # Override defaults if they are specified at the command line
        for default_pkg in config.create_default_packages:
            if any(pkg.split('=')[0] == default_pkg for pkg in args.packages):
                default_packages.remove(default_pkg)
        args.packages.extend(default_packages)

    common.ensure_override_channels_requires_channel(args)
    channel_urls = args.channel or ()

    if args.file:
        specs = common.specs_from_url(args.file)
    elif getattr(args, 'all', False):
        specs = []
        linked = ci.linked(prefix)
        for pkg in linked:
            name, ver, build = pkg.rsplit('-', 2)
            if name == 'python' and ver.startswith('2'):
                # Oh Python 2...
                specs.append('%s >=%s,<3' % (name, ver))
            else:
                specs.append('%s >=%s' % (name, ver))
    else:
        specs = common.specs_from_args(args.packages)

    if command == 'install' and args.revision:
        get_revision(args.revision)
    else:
        common.check_specs(prefix, specs)

    if args.use_local:
        from conda.fetch import fetch_index
        from conda.utils import url_path
        try:
            from conda_build import config as build_config
        except ImportError:
            sys.exit("Error: you need to have 'conda-build' installed"
                     " to use the --use-local option")
        # remove the cache such that a refetch is made,
        # this is necessary because we add the local build repo URL
        fetch_index.cache = {}
        index = get_index([url_path(build_config.croot)],
                          use_cache=args.use_index_cache,
                          unknown=args.unknown)
    else:
        index = get_index(channel_urls=channel_urls, prepend=not
                          args.override_channels,
                          use_cache=args.use_index_cache,
                          unknown=args.unknown)

    # Don't update packages that are already up-to-date
    if command == 'update' and not args.all:
        r = Resolve(index)
        orig_packages = args.packages[:]
        for name in orig_packages:
            vers_inst = [dist.rsplit('-', 2)[1] for dist in linked
                if dist.rsplit('-', 2)[0] == name]
            build_inst = [dist.rsplit('-', 2)[2].rsplit('.tar.bz2', 1)[0]
                          for dist in linked
                          if dist.rsplit('-', 2)[0] == name]
            assert len(vers_inst) == 1, name
            assert len(build_inst) == 1, name
            pkgs = sorted(r.get_pkgs(MatchSpec(name)))
            if not pkgs:
                # Shouldn't happen?
                continue
            latest = pkgs[-1]
            if latest.version == vers_inst[0] and latest.build == build_inst[0]:
                args.packages.remove(name)
        if not args.packages:
            from conda.cli.main_list import list_packages

            regex = '^(%s)$' % '|'.join(orig_packages)
            print('# All requested packages already installed.')
            list_packages(prefix, regex)
            return

    # handle tar file containing conda packages
    if len(args.packages) == 1:
        tar_path = args.packages[0]
        if tar_path.endswith('.tar'):
            install_tar(prefix, tar_path, verbose=not args.quiet)
            return

    # handle explicit installs of conda packages
    if args.packages and all(s.endswith('.tar.bz2') for s in args.packages):
        from conda.misc import install_local_packages
        install_local_packages(prefix, args.packages, verbose=not args.quiet)
        return

    if any(s.endswith('.tar.bz2') for s in args.packages):
        sys.exit("cannot mix specifications with conda package filenames")

    if args.force:
        args.no_deps = True

    spec_names = set(s.split()[0] for s in specs)
    if args.no_deps:
        only_names = spec_names
    else:
        only_names = None

    if not isdir(prefix) and not newenv:
        if args.mkdir:
            try:
                os.makedirs(prefix)
            except OSError:
                sys.exit("Error: could not create directory: %s" % prefix)
        else:
            sys.exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before installing packages
# into it.
#""" % prefix)

    if command == 'install' and args.revision:
        actions = plan.revert_actions(prefix, get_revision(args.revision))
    else:
        actions = plan.install_actions(prefix, index, specs, force=args.force,
                                       only_names=only_names, pinned=args.pinned, minimal_hint=args.alt_hint)

    if plan.nothing_to_do(actions):
        from conda.cli.main_list import list_packages

        regex = '^(%s)$' % '|'.join(spec_names)
        print('\n# All requested packages already installed.')
        list_packages(prefix, regex)
        return

    print()
    print("Package plan for installation in environment %s:" % prefix)
    plan.display_actions(actions, index)
    if command in {'install', 'update'}:
        common.check_write(command, prefix)

    if not pscheck.main(args):
        common.confirm_yn(args)

    plan.execute_actions(actions, index, verbose=not args.quiet)
    if newenv:
        touch_nonadmin(prefix)
        print_activate(args.name if args.name else prefix)


def check_install(packages, platform=None, channel_urls=(), prepend=True, minimal_hint=False):
    try:
        prefix = tempfile.mkdtemp('conda')
        specs = common.specs_from_args(packages)
        index = get_index(channel_urls=channel_urls, prepend=prepend,
                          platform=platform)
        plan.install_actions(prefix, index, specs, pinned=False, minimal_hint=minimal_hint)
    finally:
        ci.rm_rf(prefix)

########NEW FILE########
__FILENAME__ = main
# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
'''conda is a tool for managing environments and packages.

conda provides the following commands:

    Information
    ===========

    info       : display information about the current install
    list       : list packages linked into a specified environment
    search     : print information about a specified package
    help       : display a list of available conda commands and their help
                 strings

    Package Management
    ==================

    create     : create a new conda environment from a list of specified
                 packages
    install    : install new packages into an existing conda environment
    update     : update packages in a specified conda environment


    Packaging
    =========

    build      : build a package from recipe
    package    : create a conda package in an environment
    index      : updates repodata.json in channel directories

Additional help for each command can be accessed by using:

    conda <command> -h
'''

from __future__ import print_function, division, absolute_import

import sys
import argparse

from conda.cli import conda_argparse
from conda.cli import main_bundle
from conda.cli import main_create
from conda.cli import main_help
from conda.cli import main_init
from conda.cli import main_info
from conda.cli import main_install
from conda.cli import main_list
from conda.cli import main_remove
from conda.cli import main_package
from conda.cli import main_search
from conda.cli import main_update
from conda.cli import main_config
from conda.cli import main_clean

def main():
    if len(sys.argv) > 1:
        argv1 = sys.argv[1]
        if argv1 in ('..activate', '..deactivate', '..activateroot', '..checkenv'):
            import conda.cli.activate as activate
            activate.main()
            return
        if argv1 in ('..changeps1'):
            import conda.cli.misc as misc
            misc.main()
            return
        if argv1 == 'pip':
            sys.exit("""ERROR:
The "conda pip" command has been removed from conda (as of version 1.8) for
the following reasons:
  * users get the wrong impression that you *must* use conda pip (instead
    of simply pip) when using Anaconda
  * there should only be one preferred way to build packages, and that is
    the conda build command
  * the command did too many things at once, i.e. build a package and
    then also install it
  * the command is Python centric, whereas conda (from a package management
    perspective) is Python agnostic
  * packages created with conda pip are not robust, i.e. they will maybe
    not work on other people's systems

In short:
  * use "conda build" if you want to build a conda package
  * use "conda install" if you want to install something
  * use "pip" if you want to install something that is on PyPI for which there
    isn't a conda package.
""")
        if argv1 in ('activate', 'deactivate'):
            sys.stderr.write("Error: '%s' is not a conda command.\n" % argv1)
            if sys.platform != 'win32':
                sys.stderr.write('Did you mean "source %s" ?\n' %
                                 ' '.join(sys.argv[1:]))
            sys.exit(1)

        # for backwards compatibility of conda-api
        if sys.argv[1:4] == ['share', '--json', '--prefix']:
            import json
            from os.path import abspath
            from conda.share import old_create_bundle
            prefix = sys.argv[4]
            path, warnings = old_create_bundle(abspath(prefix))
            json.dump(dict(path=path, warnings=warnings),
                      sys.stdout, indent=2, sort_keys=True)
            return
        if sys.argv[1:4] == ['clone', '--json', '--prefix']:
            import json
            from os.path import abspath
            from conda.share import old_clone_bundle
            prefix, path = sys.argv[4:6]
            old_clone_bundle(path, abspath(prefix))
            json.dump(dict(warnings=[]), sys.stdout, indent=2)
            return

    if len(sys.argv) == 1:
        sys.argv.append('-h')

    import logging
    import conda

    p = conda_argparse.ArgumentParser(
        description='conda is a tool for managing environments and packages.'
    )
    p.add_argument(
        '-V', '--version',
        action = 'version',
        version = 'conda %s' % conda.__version__,
    )
    p.add_argument(
        "--debug",
        action = "store_true",
        help = argparse.SUPPRESS,
    )
    sub_parsers = p.add_subparsers(
        metavar = 'command',
        dest = 'cmd',
    )

    main_info.configure_parser(sub_parsers)
    main_help.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers)
    main_search.configure_parser(sub_parsers)
    main_create.configure_parser(sub_parsers)
    main_install.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)
    main_config.configure_parser(sub_parsers)
    main_init.configure_parser(sub_parsers)
    main_clean.configure_parser(sub_parsers)
    main_package.configure_parser(sub_parsers)
    main_bundle.configure_parser(sub_parsers)

    try:
        import argcomplete
        argcomplete.autocomplete(p)
    except ImportError:
        pass
    except AttributeError:
        # On Python 3.3, argcomplete can be an empty namespace package when
        # we are in the conda-recipes directory.
        pass

    args = p.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if (not main_init.is_initialized() and
        'init' not in sys.argv and 'info' not in sys.argv):
        sys.exit("""Error: conda is not initialized yet, try: conda init
# Note that initializing conda is not the recommended way for setting up your
# system.  The recommended way for setting up a conda system is by installing
# Miniconda, see: http://repo.continuum.io/miniconda/index.html""")

    try:
        args.func(args, p)
    except RuntimeError as e:
        sys.exit("Error: %s" % e)
    except Exception as e:
        if e.__class__.__name__ not in ('ScannerError', 'ParserError'):
            print("""\
An unexpected error has occurred, please consider sending the
following traceback to the conda GitHub issue tracker at:

    https://github.com/conda/conda/issues

Include the output of the command 'conda info' in your report.

""")
        raise  # as if we did not catch it

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = main_bundle
from __future__ import print_function, division, absolute_import

from conda.cli import common
from argparse import RawDescriptionHelpFormatter


descr = 'Create or extract a "bundle package" (EXPERIMENTAL)'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'bundle',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
    )
    cxgroup = p.add_mutually_exclusive_group()
    cxgroup.add_argument('-c', "--create",
                         action = "store_true",
                         help = "create bundle")
    cxgroup.add_argument('-x', "--extract",
                         action = "store",
                         help = "extact bundle located at PATH",
                         metavar = "PATH")
    cxgroup.add_argument("--metadump",
                         action = "store",
                         help = "dump metadata of bundle at PATH",
                         metavar = "PATH")

    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument("--bundle-name",
                   action = "store",
                   help = "name of bundle",
                   metavar = 'NAME',
                   )
    p.add_argument("--data-path",
                   action = "store",
                   help = "path to data to be included in bundle",
                   metavar = "PATH"
                   )
    p.add_argument("--extra-meta",
                   action = "store",
                   help = "path to json file with additional meta-data no",
                   metavar = "PATH",
                   )
    p.add_argument("--no-env",
                   action = "store_true",
                   help = "no environment",
                   )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json

    import conda.bundle as bundle
    from conda.fetch import TmpDownload


    if not (args.create or args.extract or args.metadump):
        sys.exit("""Error:
    either one of the following options is required:
       -c/--create  -x/--extract  --metadump
    (see -h for more details)""")
    prefix = common.get_prefix(args)
    if args.no_env:
        prefix = None

    if args.create:
        if args.extra_meta:
            with open(args.extra_meta) as fi:
                extra = json.load(fi)
            if not isinstance(extra, dict):
                sys.exit('Error: no dictionary in: %s' % args.extra_meta)
        else:
            extra = None

        bundle.warn = []
        out_path = bundle.create_bundle(prefix, args.data_path,
                                        args.bundle_name, extra)
        if args.json:
            d = dict(path=out_path, warnings=bundle.warn)
            json.dump(d, sys.stdout, indent=2, sort_keys=True)
        else:
            print(out_path)


    if args.extract:
        if args.data_path or args.extra_meta:
            sys.exit("""\
Error: -x/--extract does not allow --data-path or --extra-meta""")

        with TmpDownload(args.extract, verbose=not args.quiet) as path:
            bundle.clone_bundle(path, prefix, args.bundle_name)


    if args.metadump:
        import tarfile

        with TmpDownload(args.metadump, verbose=not args.quiet) as path:
            try:
                t = tarfile.open(path, 'r:*')
                f = t.extractfile('info/index.json')
                sys.stdout.write(f.read())
                sys.stdout.write('\n')
            except IOError:
                sys.exit("Error: no such file: %s" % path)
            except tarfile.ReadError:
                sys.exit("Error: bad tar archive: %s" % path)
            except KeyError:
                sys.exit("Error: no archive '%s' in: %s" % (bundle.BMJ, path))
            t.close()

########NEW FILE########
__FILENAME__ = main_clean
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter
import os
import sys

from conda.cli import common
import conda.config as config
from conda.utils import human_bytes

descr = """
Remove unused packages and caches
"""

example = """
examples:
    conda clean --tarballs
"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'clean',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )

    common.add_parser_yes(p)
    p.add_argument(
        "-i", "--index-cache",
        action = "store_true",
        help = "remove index cache",
    )
    p.add_argument(
        "-l", "--lock",
        action = "store_true",
        help = "remove all conda lock files",
    )
    p.add_argument(
        "-t", "--tarballs",
        action = "store_true",
        help = "remove cached package tarballs",
    )
    p.add_argument(
        '-p', '--packages',
        action='store_true',
        help="""remove unused cached packages. Warning: this does not check
    for symlinked packages.""",
    )
    p.set_defaults(func=execute)


def rm_lock():
    from os.path import join

    from conda.lock import LOCKFN

    lock_dirs = config.pkgs_dirs
    lock_dirs += [config.root_dir]
    for envs_dir in config.envs_dirs:
        for fn in os.listdir(envs_dir):
            if os.path.isdir(join(envs_dir, fn)):
                lock_dirs.append(join(envs_dir, fn))

    try:
        from conda_build.config import croot
        lock_dirs.append(croot)
    except ImportError:
        pass

    for dir in lock_dirs:
        if not os.path.exists(dir):
            continue
        for dn in os.listdir(dir):
            if os.path.isdir(join(dir, dn)) and dn.startswith(LOCKFN):
                path = join(dir, dn)
                print('removing: %s' % path)
                os.rmdir(path)


def rm_tarballs(args):
    from os.path import join, getsize

    pkgs_dir = config.pkgs_dirs[0]
    print('Cache location: %s' % pkgs_dir)

    rmlist = []
    for fn in os.listdir(pkgs_dir):
        if fn.endswith('.tar.bz2') or fn.endswith('.tar.bz2.part'):
            rmlist.append(fn)

    if not rmlist:
        print("There are no tarballs to remove")
        sys.exit(0)

    print("Will remove the following tarballs:")
    print()
    totalsize = 0
    maxlen = len(max(rmlist, key=lambda x: len(str(x))))
    fmt = "%-40s %10s"
    for fn in rmlist:
        size = getsize(join(pkgs_dir, fn))
        totalsize += size
        print(fmt % (fn, human_bytes(size)))
    print('-' * (maxlen + 2 + 10))
    print(fmt % ('Total:', human_bytes(totalsize)))
    print()

    common.confirm_yn(args)

    for fn in rmlist:
        print("removing %s" % fn)
        os.unlink(os.path.join(pkgs_dir, fn))

def rm_pkgs(args):
    # TODO: This doesn't handle packages that have hard links to files within
    # themselves, like bin/python3.3 and bin/python3.3m in the Python package
    from os.path import join, isdir
    from os import lstat, walk, listdir
    from conda.install import rm_rf

    pkgs_dir = config.pkgs_dirs[0]
    print('Cache location: %s' % pkgs_dir)

    rmlist = []
    pkgs = [i for i in listdir(pkgs_dir) if isdir(join(pkgs_dir, i)) and
        # Only include actual packages
        isdir(join(pkgs_dir, i, 'info'))]
    for pkg in pkgs:
        breakit = False
        for root, dir, files in walk(join(pkgs_dir, pkg)):
            if breakit:
                break
            for fn in files:
                try:
                    stat = lstat(join(root, fn))
                except OSError as e:
                    print(e)
                    continue
                if stat.st_nlink > 1:
                    # print('%s is installed: %s' % (pkg, join(root, fn)))
                    breakit = True
                    break
        else:
            rmlist.append(pkg)

    if not rmlist:
        print("There are no unused packages to remove")
        sys.exit(0)

    print("Will remove the following packages:")
    print()
    totalsize = 0
    maxlen = len(max(rmlist, key=lambda x: len(str(x))))
    fmt = "%-40s %10s"
    for pkg in rmlist:
        pkgsize = 0
        for root, dir, files in walk(join(pkgs_dir, pkg)):
            for fn in files:
                # We don't have to worry about counting things twice:  by
                # definition these files all have a link count of 1!
                size = lstat(join(root, fn)).st_size
                totalsize += size
                pkgsize += size
        print(fmt % (pkg, human_bytes(pkgsize)))
    print('-' * (maxlen + 2 + 10))
    print(fmt % ('Total:', human_bytes(totalsize)))
    print()

    common.confirm_yn(args)

    for pkg in rmlist:
        print("removing %s" % pkg)
        rm_rf(join(pkgs_dir, pkg))


def rm_index_cache():
    from os.path import join

    from conda.config import pkgs_dirs
    from conda.install import rm_rf

    rm_rf(join(pkgs_dirs[0], 'cache'))


def execute(args, parser):
    if args.lock:
        rm_lock()
    if args.tarballs:
        rm_tarballs(args)
    if args.index_cache:
        rm_index_cache()
    if args.packages:
        rm_pkgs(args)
    if not (args.lock or args.tarballs or args.index_cache or args.packages):
        sys.exit("One of {--lock, --tarballs, --index-cache, --packages} required")

########NEW FILE########
__FILENAME__ = main_config
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

import re
import os
import sys
from argparse import RawDescriptionHelpFormatter
from copy import deepcopy

import conda.config as config

descr = """
Modify configuration values in .condarc.  This is modeled after the git
config command.  Writes to the user .condarc file (%s) by default.
""" % config.user_rc_path

example = """
examples:
    conda config --get channels --system
    conda config --add channels http://conda.binstar.org/foo
"""

class CouldntParse(NotImplementedError):
    def __init__(self, reason):
        self.args = ["""Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: %s""" % reason]

class BoolKey(object):
    def __contains__(self, other):
        # Other is either one of the keys or the boolean
        try:
            import yaml
        except ImportError:
            yaml = False

        ret = other in config.rc_bool_keys
        if yaml:
            ret = ret or isinstance(yaml.load(other), bool)

        return ret

    def __iter__(self):
        for i in config.rc_bool_keys + ['yes', 'no', 'on', 'off', 'true', 'false']:
            yield i

class ListKey(object):
    def __contains__(self, other):
        # We can't check the elements of the list themselves
        return True

    def __iter__(self):
        for i in config.rc_list_keys:
            yield i

class BoolOrListKey(object):
    def __contains__(self, other):
        return other in config.rc_bool_keys or other in config.rc_list_keys

    def __iter__(self):
        for i in config.rc_list_keys:
            yield i
        for i in config.rc_bool_keys:
            yield i

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
        )

    # TODO: use argparse.FileType
    location = p.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action = "store_true",
        help = """\
write to the system .condarc file ({system}). Otherwise writes to the user
        config file ({user}).""".format(system=config.sys_rc_path,
                                        user=config.user_rc_path),
        )
    location.add_argument(
        "--file",
        action = "store",
        help = """\
write to the given file. Otherwise writes to the user config file
        ({user}).""".format(user=config.user_rc_path),
        )

    # XXX: Does this really have to be mutually exclusive. I think the below
    # code will work even if it is a regular group (although combination of
    # --add and --remove with the same keys will not be well-defined).
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--get",
        nargs = '*',
        action = "store",
        help = "get the configuration value",
        default = None,
        metavar = ('KEY'),
        choices=BoolOrListKey()
        )
    action.add_argument(
        "--add",
        nargs = 2,
        action = "append",
        help = """add one configuration value to a list key. The default
        behavior is to prepend.""",
        default = [],
        choices=ListKey(),
        metavar = ('KEY', 'VALUE'),
        )
    action.add_argument(
        "--set",
        nargs = 2,
        action = "append",
        help = "set a boolean key. BOOL_VALUE should be 'yes' or 'no'",
        default = [],
        choices=BoolKey(),
        metavar = ('KEY', 'BOOL_VALUE'),
        )
    action.add_argument(
        "--remove",
        nargs = 2,
        action = "append",
        help = """remove a configuration value from a list key. This removes
    all instances of the value""",
        default = [],
        metavar = ('KEY', 'VALUE'),
        )
    action.add_argument(
        "--remove-key",
        nargs = 1,
        action = "append",
        help = """remove a configuration key (and all its values)""",
        default = [],
        metavar = "KEY",
        )

    p.add_argument(
        "-f", "--force",
        action = "store_true",
        help = """Write to the config file using the yaml parser.  This will
        remove any comments or structure from the file."""
        )

    p.set_defaults(func=execute)


def execute(args, parser):
    try:
        import yaml
    except ImportError:
        sys.exit("Error: pyyaml is required to modify configuration")

    if args.system:
        rc_path = config.sys_rc_path
    elif args.file:
        rc_path = args.file
    else:
        rc_path = config.user_rc_path

    # Create the file if it doesn't exist
    if not os.path.exists(rc_path):
        if args.add and 'channels' in list(zip(*args.add))[0] and not ['channels', 'defaults'] in args.add:
            # If someone adds a channel and their .condarc doesn't exist, make
            # sure it includes the defaults channel, or else they will end up
            # with a broken conda.
            rc_text = """\
channels:
  - defaults
"""
        else:
            rc_text = ""
    else:
        with open(rc_path, 'r') as rc:
            rc_text = rc.read()
    rc_config = yaml.load(rc_text)
    if rc_config is None:
        rc_config = {}

    # Get
    if args.get is not None:
        if args.get == []:
            args.get = sorted(rc_config.keys())
        for key in args.get:
            if key not in config.rc_list_keys + config.rc_bool_keys:
                print("%s is not a valid key" % key, file=sys.stderr)
                continue
            if key not in rc_config:
                continue
            if isinstance(rc_config[key], bool):
                print("--set", key, rc_config[key])
            else:
                # Note, since conda config --add prepends, these are printed in
                # the reverse order so that entering them in this order will
                # recreate the same file
                for item in reversed(rc_config.get(key, [])):
                    # Use repr so that it can be pasted back in to conda config --add
                    print("--add", key, repr(item))


    # PyYaml does not support round tripping, so if we use yaml.dump, it
    # will clear all comments and structure from the configuration file.
    # There are no yaml parsers that do this.  Our best bet is to do a
    # simple parsing of the file ourselves.  We can check the result at
    # the end to see if we did it right.

    # First, do it the pyyaml way
    new_rc_config = deepcopy(rc_config)

    # Add
    for key, item in args.add:
        if item in rc_config.get(key, []):
            # Right now, all list keys should not contain duplicates
            print("Skipping %s: %s, item already exists" % (key, item), file=sys.stderr)
            continue
        new_rc_config.setdefault(key, []).insert(0, item)

    # Set
    for key, item in args.set:
        yamlitem = yaml.load(item)
        if not isinstance(yamlitem, bool):
            sys.exit("Error: %r is not a boolean" % item)

        new_rc_config[key] = yamlitem

    # Remove
    for key, item in args.remove:
        if key not in new_rc_config:
            sys.exit("Error: key %r is not in the config file" % key)
        if item not in new_rc_config[key]:
            sys.exit("Error: %r is not in the %r key of the config file" %
                     (item, key))
        new_rc_config[key] = [i for i in new_rc_config[key] if i != item]

    # Remove Key
    for key, in args.remove_key:
        if key not in new_rc_config:
            sys.exit("Error: key %r is not in the config file" % key)
        del new_rc_config[key]

    if args.force:
        # Note, force will also remove any checking that the keys are in
        # config.rc_keys
        with open(rc_path, 'w') as rc:
            rc.write(yaml.dump(new_rc_config, default_flow_style=False))
        return

    # Now, try to parse the condarc file.

    # Just support "   key:  " for now
    listkeyregexes = {key:re.compile(r"( *)%s *" % key)
        for key in dict(args.add)
        }
    setkeyregexes = {key:re.compile(r"( *)%s( *):( *)" % key)
        for key in dict(args.set)
        }

    new_rc_text = rc_text[:].split("\n")

    for key, item in args.add:
        if key not in config.rc_list_keys:
            sys.exit("Error: key must be one of %s, not %s" %
                     (config.rc_list_keys, key))

        if item in rc_config.get(key, []):
            # Skip duplicates. See above
            continue
        added = False
        for pos, line in enumerate(new_rc_text[:]):
            matched = listkeyregexes[key].match(line)
            if matched:
                leading_space = matched.group(1)
                # TODO: Try to guess how much farther to indent the
                # item. Right now, it is fixed at 2 spaces.
                new_rc_text.insert(pos + 1, "%s  - %s" % (leading_space, item))
                added = True
        if not added:
            if key in rc_config:
                # We should have found it above
                raise CouldntParse("existing list key couldn't be found")
            # TODO: Try to guess the correct amount of leading space for the
            # key. Right now it is zero.
            new_rc_text += ['%s:' % key, '  - %s' % item]
            if key == 'channels' and ['channels', 'defaults'] not in args.add:
                # If channels key is added for the first time, make sure it
                # includes 'defaults'
                new_rc_text += ['  - defaults']
                new_rc_config['channels'].append('defaults')

    for key, item in args.set:
        if key not in config.rc_bool_keys:
            sys.exit("Error key must be one of %s, not %s" %
                     (config.rc_bool_keys, key))
        added = False
        for pos, line in enumerate(new_rc_text[:]):
            matched = setkeyregexes[key].match(line)
            if matched:
                leading_space = matched.group(1)
                precol_space = matched.group(2)
                postcol_space = matched.group(3)
                new_rc_text[pos] = '%s%s%s:%s%s' % (leading_space, key,
                    precol_space, postcol_space, item)
                added = True
        if not added:
            if key in rc_config:
                raise CouldntParse("existing bool key couldn't be found")
            new_rc_text += ['%s: %s' % (key, item)]

    for key, item in args.remove:
        raise NotImplementedError("--remove without --force is not implemented "
            "yet")

    for key, in args.remove_key:
        raise NotImplementedError("--remove-key without --force is not "
            "implemented yet")

    if args.add or args.set:
        # Verify that the new rc text parses to the same thing as if we had
        # used yaml.
        try:
            parsed_new_rc_text = yaml.load('\n'.join(new_rc_text).strip('\n'))
        except yaml.parser.ParserError:
            raise CouldntParse("couldn't parse modified yaml")
        else:
            if not parsed_new_rc_text == new_rc_config:
                raise CouldntParse("modified yaml doesn't match what it "
                                   "should be")

    if args.add or args.set:
        with open(rc_path, 'w') as rc:
            rc.write('\n'.join(new_rc_text).strip('\n'))
            rc.write('\n')

########NEW FILE########
__FILENAME__ = main_create
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common, install


help = "Create a new conda environment from a list of specified packages. "
descr = (help +
         "To use the created environment, use 'source activate "
         "envname' look in that directory first.  This command requires either "
         "the -n NAME or -p PREFIX option.")

example = """
examples:
    conda create -n myenv sqlite

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog  = example,
    )
    common.add_parser_install(p)
    p.add_argument(
        "--clone",
        action = "store",
        help = 'path to (or name of) existing local environment',
        metavar = 'ENV',
    )
    p.add_argument(
        "--no-default-packages",
        action = "store_true",
        help = 'ignore create_default_packages in condarc file',
    )
    p.set_defaults(func=execute)

def execute(args, parser):
    install.install(args, parser, 'create')

########NEW FILE########
__FILENAME__ = main_help
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

descr = "Displays a list of available conda commands and their help strings."

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('help',
                               description = descr,
                               help = descr)
    p.add_argument(
        'command',
        metavar = 'COMMAND',
        action = "store",
        nargs = '?',
        help = "print help information for COMMAND "
               "(same as: conda COMMAND -h)",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.command:
        parser.print_help()
        return

    import sys
    import subprocess

    subprocess.call([sys.executable, sys.argv[0], args.command, '-h'])

########NEW FILE########
__FILENAME__ = main_info
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import sys
from os.path import isfile

from conda.cli import common


help = "Display information about current conda install."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('info',
                               description = help,
                               help = help)
    common.add_parser_json(p)
    p.add_argument(
        '-a', "--all",
        action  = "store_true",
        help    = "show all information, (environments, license, and system "
                  "information")
    p.add_argument(
        '-e', "--envs",
        action  = "store_true",
        help    = "list all known conda environments",
    )
    p.add_argument(
        '-l', "--license",
        action  = "store_true",
        help    = "display information about local conda licenses list",
    )
    p.add_argument(
        '-s', "--system",
        action = "store_true",
        help = "list environment variables",
    )
    p.add_argument(
        'args',
        metavar = 'args',
        action = "store",
        nargs = '*',
        help = "display information about packages or files",
    )
    p.set_defaults(func=execute)


def show_pkg_info(name):
    #import conda.install as install
    from conda.api import get_index
    from conda.resolve import MatchSpec, Resolve

    index = get_index()
    r = Resolve(index)
    print(name)
    if name in r.groups:
        for pkg in sorted(r.get_pkgs(MatchSpec(name))):
            print('    %-15s %15s  %s' % (
                    pkg.version,
                    r.index[pkg.fn]['build'],
                    common.disp_features(r.features(pkg.fn))))
    else:
        print('    not available on channels')
    # TODO


def execute(args, parser):
    if args.args:
        for arg in args.args:
            if isfile(arg):
                from conda.misc import which_package
                path = arg
                for dist in which_package(path):
                    print('%-50s  %s' % (path, dist))
            else:
                show_pkg_info(arg)
        return

    import os
    from os.path import basename, dirname, isdir, join

    import conda
    import conda.config as config
    from conda.cli.main_init import is_initialized

    options = 'envs', 'system', 'license'

    info_dict = dict(platform=config.subdir,
                     conda_version=conda.__version__,
                     root_prefix=config.root_dir,
                     root_writable=config.root_writable,
                     pkgs_dirs=config.pkgs_dirs,
                     envs_dirs=config.envs_dirs,
                     default_prefix=config.default_prefix,
                     channels=config.get_channel_urls(),
                     rc_path=config.rc_path,
                     is_foreign=bool(config.foreign),
                     envs=[],
                     python_version='.'.join(map(str, sys.version_info)),
    )

    if args.all or args.json:
        for option in options:
            setattr(args, option, True)

    t_pat = re.compile(r'binstar\.org/(t/[0-9a-f\-]{4,})')
    info_dict['channels_disp'] = [t_pat.sub('binstar.org/t/<TOKEN>', c)
                                  for c in info_dict['channels']]

    if args.all or all(not getattr(args, opt) for opt in options):
        for key in 'pkgs_dirs', 'envs_dirs', 'channels_disp':
            info_dict['_' + key] = ('\n' + 24 * ' ').join(info_dict[key])
        info_dict['_rtwro'] = ('writable' if info_dict['root_writable'] else
                               'read only')
        print("""\
Current conda install:

             platform : %(platform)s
        conda version : %(conda_version)s
       python version : %(python_version)s
     root environment : %(root_prefix)s  (%(_rtwro)s)
  default environment : %(default_prefix)s
     envs directories : %(_envs_dirs)s
        package cache : %(_pkgs_dirs)s
         channel URLs : %(_channels_disp)s
          config file : %(rc_path)s
    is foreign system : %(is_foreign)s
""" % info_dict)
        if not is_initialized():
            print("""\
# NOTE:
#     root directory '%s' uninitalized,
#     use 'conda init' to initialize.""" % config.root_dir)

    del info_dict['channels_disp']

    if args.envs:
        if not args.json:
            print("# conda environments:")
            print("#")
        def disp_env(prefix):
            fmt = '%-20s  %s  %s'
            default = '*' if prefix == config.default_prefix else ' '
            name = (config.root_env_name if prefix == config.root_dir else
                    basename(prefix))
            if not args.json:
                print(fmt % (name, default, prefix))

        for envs_dir in config.envs_dirs:
            if not isdir(envs_dir):
                continue
            for dn in sorted(os.listdir(envs_dir)):
                if dn.startswith('.'):
                    continue
                prefix = join(envs_dir, dn)
                if isdir(prefix):
                    prefix = join(envs_dir, dn)
                    disp_env(prefix)
                    info_dict['envs'].append(prefix)
        disp_env(config.root_dir)
        print()

    if args.system and not args.json:
        from conda.cli.find_commands import find_commands, find_executable

        print("sys.version: %s..." % (sys.version[:40]))
        print("sys.prefix: %s" % sys.prefix)
        print("sys.executable: %s" % sys.executable)
        print("conda location: %s" % dirname(conda.__file__))
        for cmd in sorted(set(find_commands() + ['build'])):
            print("conda-%s: %s" % (cmd, find_executable(cmd)))
        print()

        evars = ['PATH', 'PYTHONPATH', 'PYTHONHOME', 'CONDA_DEFAULT_ENV',
                 'CIO_TEST', 'CONDA_ENVS_PATH']
        if config.platform == 'linux':
            evars.append('LD_LIBRARY_PATH')
        elif config.platform == 'osx':
            evars.append('DYLD_LIBRARY_PATH')
        for ev in sorted(evars):
            print("%s: %s" % (ev, os.getenv(ev, '<not set>')))
        print()

    if args.license and not args.json:
        try:
            from _license import show_info
            show_info()
        except ImportError:
            print("""\
WARNING: could import _license.show_info
# try:
# $ conda install -n root _license""")

    if args.json:
        common.stdout_json(info_dict)

########NEW FILE########
__FILENAME__ = main_init
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
from os.path import isdir, join

import conda
import conda.config as config


descr = ("Initialize conda into a regular environment (when conda was "
         "installed as a Python package, e.g. using pip).")


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'init',
        description = descr,
        help = descr,
    )
    p.set_defaults(func=execute)


def is_initialized():
    return isdir(join(config.root_dir, 'conda-meta'))


def write_meta(meta_dir, info):
    import json

    info['files'] = []
    with open(join(meta_dir,
                   '%(name)s-%(version)s-0.json' % info), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True)


def initialize(prefix=config.root_dir):
    import os

    meta_dir = join(prefix, 'conda-meta')
    try:
        os.mkdir(meta_dir)
    except OSError:
        sys.exit('Error: could not create: %s' % meta_dir)
    with open(join(meta_dir, 'foreign'), 'w') as fo:
        fo.write('python\n')
        if sys.platform != 'win32':
            fo.write('zlib sqlite readline tk openssl system\n')
    write_meta(meta_dir, dict(name='conda',
                              version=conda.__version__.split('-')[0]))
    write_meta(meta_dir, dict(name='python', version=sys.version[:5]))


def execute(args, parser):
    if is_initialized():
        sys.exit('Error: conda appears to be already initalized in: %s' %
                 config.root_dir)

    print('Initializing conda into: %s' % config.root_dir)
    initialize()

########NEW FILE########
__FILENAME__ = main_install
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common, install


help = "Install a list of packages into a specified conda environment."
descr = help + """
The arguments may be packages specifications (e.g. bitarray=0.8),
or explicit conda packages filesnames (e.g. lxml-3.2.0-py27_0.tar.bz2) which
must exist on the local filesystem.  The two types of arguments cannot be
mixed and the latter implies the --force and --no-deps options.
"""
example = """
examples:
    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    p.add_argument(
        "--revision",
        action = "store",
        help = "revert to the specified REVISION",
        metavar = 'REVISION',
    )
    common.add_parser_install(p)
    p.set_defaults(func=execute)

def execute(args, parser):
    install.install(args, parser, 'install')

########NEW FILE########
__FILENAME__ = main_list
# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import sys
import subprocess
from os.path import isdir, isfile, join

import conda.install as install
import conda.config as config
from conda.cli import common


descr = "List linked packages in a conda environment."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = descr,
        help = descr,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        '-c', "--canonical",
        action = "store_true",
        help = "output canonical names of packages only",
    )
    p.add_argument(
        '-e', "--export",
        action = "store_true",
        help = "output requirement string only "
                  "(output may be used by conda create --file)",
    )
    p.add_argument(
        '-r', "--revisions",
        action = "store_true",
        help = "list the revision history and exit",
    )
    p.add_argument(
        "--no-pip",
        action = "store_false",
        default=True,
        dest="pip",
        help = "Do not include pip-only installed packages")
    p.add_argument(
        'regex',
        action = "store",
        nargs = "?",
        help = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def print_export_header():
    print('# This file may be used to create an environment using:')
    print('# $ conda create --name <env> --file <this file>')
    print('# platform: %s' % config.subdir)


def pip_args(prefix):
    """
    return the arguments required to invoke pip (in prefix), or None if pip
    is not installed
    """
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip-script.py')
        py_path = join(prefix, 'python.exe')
    else:
        pip_path = join(prefix, 'bin', 'pip')
        py_path = join(prefix, 'bin', 'python')
    if isfile(pip_path) and isfile(py_path):
        return [py_path, pip_path]
    else:
        return None


def add_pip_installed(prefix, installed):
    args = pip_args(prefix)
    if args is None:
        return
    args.append('list')
    try:
        pipinst = subprocess.check_output(
                                args, universal_newlines=True).split('\n')
    except Exception as e:
        # Any error should just be ignored
        print("# Warning: subprocess call to pip failed")
        return

    # For every package in pipinst that is not already represented
    # in installed append a fake name to installed with 'pip'
    # as the build string
    conda_names = {d.rsplit('-', 2)[0] for d in installed}
    pat = re.compile('([\w.-]+)\s+\(([\w.]+)')
    for line in pipinst:
        line = line.strip()
        if not line:
            continue
        m = pat.match(line)
        if m is None:
            print('Could not extract name and version from: %r' % line)
            continue
        name, version = m.groups()
        name = name.lower()
        if name not in conda_names:
            installed.add('%s-%s-<pip>' % (name, version))


def list_packages(prefix, regex=None, format='human', piplist=False):
    if not isdir(prefix):
        sys.exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before listing its packages.""" % prefix)
    pat = re.compile(regex, re.I) if regex else None

    if format == 'human':
        print('# packages in environment at %s:' % prefix)
        print('#')
        res = 1
    if format == 'export':
        print_export_header()

    installed = install.linked(prefix)
    if piplist and config.use_pip and format == 'human':
        add_pip_installed(prefix, installed)

    for dist in sorted(installed):
        name = dist.rsplit('-', 2)[0]
        if pat and pat.search(name) is None:
            continue
        res = 0
        if format == 'canonical':
            print(dist)
            continue
        if format == 'export':
            print('='.join(dist.rsplit('-', 2)))
            continue
        try:
            # Returns None if no meta-file found (e.g. pip install)
            info = install.is_linked(prefix, dist)
            features = set(info.get('features', '').split())
            disp = '%(name)-25s %(version)-15s %(build)15s' % info
            disp += '  %s' % common.disp_features(features)
            if config.show_channel_urls:
                disp += '  %s' % config.canonical_channel_name(info.get('url'))
            print(disp)
        except: # (IOError, KeyError, ValueError):
            print('%-25s %-15s %15s' % tuple(dist.rsplit('-', 2)))

    return res


def execute(args, parser):
    prefix = common.get_prefix(args)

    if args.revisions:
        from conda.history import History

        h = History(prefix)
        if isfile(h.path):
            h.print_log()
        else:
            sys.stderr.write("No revision log found: %s\n" % h.path)
        return

    if args.canonical:
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'
    sys.exit(list_packages(prefix, args.regex, format=format, piplist=args.pip))

########NEW FILE########
__FILENAME__ = main_package
# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common


descr = "Low-level conda package utility. (EXPERIMENTAL)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('package', description=descr, help=descr)

    common.add_parser_prefix(p)
    p.add_argument(
        '-w', "--which",
        action = "store_true",
        help = "given some PATH print which conda package the file came from",
    )
    p.add_argument(
        '-L', "--ls-files",
        metavar = 'PKG-NAME',
        action  = "store",
        help    = "list all files belonging to specified package",
    )
    p.add_argument(
        '-r', "--reset",
        action  = "store_true",
        help    = "remove all untracked files and exit",
    )
    p.add_argument(
        '-u', "--untracked",
        action  = "store_true",
        help    = "display all untracked files and exit",
    )
    p.add_argument(
        "--pkg-name",
        action  = "store",
        default = "unknown",
        help    = "package name of the created package",
    )
    p.add_argument(
        "--pkg-version",
        action  = "store",
        default = "0.0",
        help    = "package version of the created package",
    )
    p.add_argument(
        "--pkg-build",
        action  = "store",
        default = 0,
        help    = "package build number of the created package",
    )
    p.add_argument(
        'path',
        metavar = 'PATH',
        action = "store",
        nargs = '*',
    )
    p.set_defaults(func=execute)

def list_package_files(pkg_name=None):
    import os
    import re
    import conda.config as config
    from conda.misc import walk_prefix

    pkgs_dirs = config.pkgs_dirs[0]
    all_dir_names = []
    pattern = re.compile(pkg_name, re.I)

    print('\nINFO: The location for available packages: %s' % (pkgs_dirs))

    for dir in os.listdir(pkgs_dirs):
        ignore_dirs = [ '_cache-0.0-x0', 'cache' ]

        if dir in ignore_dirs:
            continue

        if not os.path.isfile(pkgs_dirs+"/"+dir):
            match = pattern.match(dir)

            if match:
                all_dir_names.append(dir)

    num_of_all_dir_names = len(all_dir_names)
    dir_num_width = len(str(num_of_all_dir_names))

    if num_of_all_dir_names == 0:
        print("\n\tWARN: There is NO '%s' package.\n" % (pkg_name))
        return 1
    elif num_of_all_dir_names >= 2:
        print("\n\tWARN: Ambiguous package name ('%s'), choose one name from below list:\n" % (pkg_name))

        num = 0
        for dir in all_dir_names:
            num += 1
            print("\t[ {num:>{width}} / {total} ]: {dir}".format(num=num, width=dir_num_width, total=num_of_all_dir_names, dir=dir))
        print("")
        return 1

    full_pkg_name = all_dir_names[0]

    print("INFO: All files belonging to '%s' package:\n" % (full_pkg_name))

    pkg_dir = pkgs_dirs+"/"+full_pkg_name

    ret = walk_prefix(pkg_dir, ignore_predefined_files=False)

    for item in ret:
        print(pkg_dir+"/"+item)

def execute(args, parser):
    import sys

    from conda.misc import untracked
    from conda.packup import make_tarbz2, remove


    prefix = common.get_prefix(args)

    if args.which:
        from conda.misc import which_package

        for path in args.path:
            for dist in which_package(path):
                print('%-50s  %s' % (path, dist))
        return

    if args.ls_files:
        if list_package_files(args.ls_files) == 1:
            sys.exit(1)
        else:
            return

    if args.path:
        sys.exit("Error: no positional arguments expected.")

    print('# prefix:', prefix)

    if args.reset:
        remove(prefix, untracked(prefix))
        return

    if args.untracked:
        files = sorted(untracked(prefix))
        print('# untracked files: %d' % len(files))
        for fn in files:
            print(fn)
        return

    make_tarbz2(prefix,
                name = args.pkg_name.lower(),
                version = args.pkg_version,
                build_number = int(args.pkg_build))

########NEW FILE########
__FILENAME__ = main_remove
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common


help = "Remove a list of packages from a specified conda environment."
descr = help + """
Normally, only the specified package is removed, and not the packages
which may depend on the package.  Hence this command should be used
with caution.
"""
example = """
examples:
    conda remove -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'remove',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    common.add_parser_yes(p)
    p.add_argument(
        "--all",
        action = "store_true",
        help = "remove all packages, i.e. the entire environment",
    )
    p.add_argument(
        "--features",
        action = "store_true",
        help = "remove features (instead of packages)",
    )
    common.add_parser_no_pin(p)
    common.add_parser_channels(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'package_names',
        metavar = 'package_name',
        action = "store",
        nargs = '*',
        help = "package names to remove from environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys

    import conda.plan as plan
    from conda.api import get_index
    from conda.cli import pscheck
    from conda.install import rm_rf, linked

    if not (args.all or args.package_names):
        sys.exit('Error: no package names supplied,\n'
                 '       try "conda remove -h" for more details')

    prefix = common.get_prefix(args)
    common.check_write('remove', prefix)

    index = None
    if args.features:
        common.ensure_override_channels_requires_channel(args)
        channel_urls = args.channel or ()
        index = get_index(channel_urls=channel_urls,
                          prepend=not args.override_channels)
        features = set(args.package_names)
        actions = plan.remove_features_actions(prefix, index, features)

    elif args.all:
        if plan.is_root_prefix(prefix):
            sys.exit('Error: cannot remove root environment,\n'
                     '       add -n NAME or -p PREFIX option')

        actions = {plan.PREFIX: prefix,
                   plan.UNLINK: sorted(linked(prefix))}

    else:
        specs = common.specs_from_args(args.package_names)
        if (plan.is_root_prefix(prefix) and
            common.names_in_specs(common.root_no_rm, specs)):
            sys.exit('Error: cannot remove %s from root environment' %
                     ', '.join(common.root_no_rm))
        actions = plan.remove_actions(prefix, specs, pinned=args.pinned)

    if plan.nothing_to_do(actions):
        if args.all:
            rm_rf(prefix)
            return
        sys.exit('Error: no packages found to remove from '
                 'environment: %s' % prefix)

    print()
    print("Package plan for package removal in environment %s:" % prefix)
    plan.display_actions(actions, index)

    if not pscheck.main(args):
        common.confirm_yn(args)

    plan.execute_actions(actions, index, verbose=not args.quiet)

    if args.all:
        rm_rf(prefix)

########NEW FILE########
__FILENAME__ = main_search
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common
from argparse import RawDescriptionHelpFormatter
from conda import config

descr = """Search for packages and display their information. The input is a
regular expression.  To perform a search with a search string that starts with
a -, separate the search from the options with --, like 'conda search -- -h'."""
example = '''
examples:
    conda search -p ~/anaconda/envs/myenv/ scipy

'''

class Platforms(object):
    """
    Tab completion for platforms

    There is no limitation on the platform string, except by what is in the
    repo, but we want to tab complete the most common ones.
    """
    def __contains__(self, other):
        return True

    def __iter__(self):
        for i in ['win-32', 'win-64', 'osx-64', 'linux-32', 'linux-64']:
            yield i

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'search',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        "--canonical",
        action  = "store_true",
        help    = "output canonical names of packages only",
    )
    common.add_parser_known(p)
    common.add_parser_use_index_cache(p)
    p.add_argument(
        '-o', "--outdated",
        action  = "store_true",
        help    = "only display installed but outdated packages",
    )
    p.add_argument(
        '-v', "--verbose",
        action  = "store_true",
        help    = "Show available packages as blocks of data",
    )
    p.add_argument(
        '--platform',
        action='store',
        dest='platform',
        help="""Search the given platform. Should be formatted like 'osx-64', 'linux-32',
        'win-64', and so on. The default is to search the current platform.""",
        choices=Platforms(),
        default=None,
        )
    p.add_argument(
        'regex',
        action  = "store",
        nargs   = "?",
        help    = "package specification or regular expression to search for "
                  "(default: display all packages)",
    )
    common.add_parser_channels(p)
    p.set_defaults(func=execute)

def execute(args, parser):
    import re
    import sys

    from conda.api import get_index
    from conda.resolve import MatchSpec, Resolve

    if args.regex:
        try:
            pat = re.compile(args.regex, re.I)
        except re.error as e:
            sys.exit("Error: %r is not a valid regex pattern (exception: %s)" % 
                            (args.regex, e))
    else:
        pat = None

    prefix = common.get_prefix(args)
    if not args.canonical:
        import conda.config
        import conda.install

        linked = conda.install.linked(prefix)
        extracted = set()
        for pkgs_dir in conda.config.pkgs_dirs:
            extracted.update(conda.install.extracted(pkgs_dir))

    # XXX: Make this work with more than one platform
    platform = args.platform or ''
    if platform and platform != config.subdir:
        args.unknown = False
    common.ensure_override_channels_requires_channel(args, dashc=False)
    channel_urls = args.channel or ()
    index = get_index(channel_urls=channel_urls, prepend=not
                      args.override_channels, platform=args.platform,
                      use_cache=args.use_index_cache,
                      unknown=args.unknown)

    r = Resolve(index)
    for name in sorted(r.groups):
        disp_name = name
        if pat and pat.search(name) is None:
            continue

        if args.outdated:
            vers_inst = [dist.rsplit('-', 2)[1] for dist in linked
                         if dist.rsplit('-', 2)[0] == name]
            if not vers_inst:
                continue
            assert len(vers_inst) == 1, name
            pkgs = sorted(r.get_pkgs(MatchSpec(name)))
            if not pkgs:
                continue
            latest = pkgs[-1]
            if latest.version == vers_inst[0]:
                continue

        for pkg in sorted(r.get_pkgs(MatchSpec(name))):
            dist = pkg.fn[:-8]
            if args.canonical:
                print(dist)
                continue
            if dist in linked:
                inst = '*'
            elif dist in extracted:
                inst = '.'
            else:
                inst = ' '

            print('%-25s %s  %-15s %15s  %-15s %s' % (
                disp_name, inst,
                pkg.version,
                r.index[pkg.fn]['build'],
                config.canonical_channel_name(pkg.channel),
                common.disp_features(r.features(pkg.fn)),
                ))
            disp_name = ''

########NEW FILE########
__FILENAME__ = main_update
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common, install


descr = "Update conda packages."
example = """
examples:
    conda update -p ~/anaconda/envs/myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'update',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    common.add_parser_install(p)
    p.add_argument(
        "--all",
        action="store_true",
        help="Update all installed packages in the environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'update')

########NEW FILE########
__FILENAME__ = misc
from __future__ import print_function, division, absolute_import

import sys

import conda.config
import conda.plan


def main():
    assert sys.argv[1] in ('..changeps1')

    if sys.argv[1] == '..changeps1':
        print(int(conda.config.changeps1))
        sys.exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pscheck
from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import abspath

from conda.cli import conda_argparse
from conda.config import root_dir
from conda.cli.common import confirm, add_parser_yes


try:
    WindowsError
except NameError:
    class WindowsError(Exception):
        pass


def check_processes():
    # Conda should still work if psutil is not installed (it should not be a
    # hard dependency)
    try:
        import psutil
    except ImportError:
        return True

    if psutil.__version__ < '2.':
        # we now require psutil 2.0 or above
        return True

    ok = True
    curpid = os.getpid()
    for n in psutil.get_pid_list():
        if n == curpid: # The Python that conda is running is OK
            continue
        try:
            p = psutil.Process(n)
        except psutil.NoSuchProcess:
            continue
        try:
            if abspath(p.exe()).startswith(root_dir):
                processcmd = ' '.join(p.cmdline())
                if processcmd.startswith('conda '):
                    continue
                print("WARNING: the process %s (%d) is running" %
                      (processcmd, n))
                ok = False
        except (psutil.AccessDenied, WindowsError):
            pass
    if not ok:
        print("""\
WARNING: Continuing installation while the above processes are running is
not recommended.  Please, close all Anaconda programs before installing or
updating things with conda.
""")
    return ok


def main(args, windowsonly=True):
    # Returns True for force, otherwise None
    if sys.platform == 'win32' or not windowsonly:
        if args.yes:
            check_processes()
        else:
            while not check_processes():
                choice = confirm(args, message="Continue (yes/no/force)",
                    choices=('yes', 'no', 'force'), default='no')
                if choice == 'no':
                    sys.exit(1)
                if choice == 'force':
                    return True


if __name__ == '__main__':
    p = conda_argparse.ArgumentParser()
    add_parser_yes(p)
    args = p.parse_args()
    main(args, windowsonly=False)

########NEW FILE########
__FILENAME__ = compat
"""
For compatibility between Python versions.
Taken mostly from six.py by Benjamin Peterson.
"""

import sys
import types
import os

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    input = input
    def lchmod(path, mode):
        try:
            os.chmod(path, mode, follow_symlinks=False)
        except (TypeError, NotImplementedError):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    import configparser
    from io import StringIO
    import urllib.parse as urlparse
    from itertools import zip_longest
    from math import log2, ceil
    from shlex import quote
    from tempfile import TemporaryDirectory
else:
    import ConfigParser as configparser
    from cStringIO import StringIO
    import urlparse
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    input = raw_input
    try:
        lchmod = os.lchmod
    except AttributeError:
        def lchmod(path, mode):
            # On systems that don't allow permissions on symbolic links, skip
            # links entirely.
            if not os.path.islink(path):
                os.chmod(path, mode)
    from itertools import izip_longest as zip_longest
    from math import log
    def log2(x):
        return log(x, 2)
    def ceil(x):
        from math import ceil
        return int(ceil(x))
    from pipes import quote

    # Modified from http://hg.python.org/cpython/file/3.3/Lib/tempfile.py. Don't
    # use the 3.4 one. It uses the new weakref.finalize feature.
    import shutil as _shutil
    import warnings as _warnings
    import os as _os
    from tempfile import mkdtemp

    class TemporaryDirectory(object):
        """Create and return a temporary directory.  This has the same
        behavior as mkdtemp but can be used as a context manager.  For
        example:

            with TemporaryDirectory() as tmpdir:
                ...

        Upon exiting the context, the directory and everything contained
        in it are removed.
        """

        # Handle mkdtemp raising an exception
        name = None
        _closed = False

        def __init__(self, suffix="", prefix='tmp', dir=None):
            self.name = mkdtemp(suffix, prefix, dir)

        def __repr__(self):
            return "<{} {!r}>".format(self.__class__.__name__, self.name)

        def __enter__(self):
            return self.name

        def cleanup(self, _warn=False, _warnings=_warnings):
            if self.name and not self._closed:
                try:
                    _shutil.rmtree(self.name)
                except (TypeError, AttributeError) as ex:
                    if "None" not in '%s' % (ex,):
                        raise
                    self._rmtree(self.name)
                self._closed = True
                if _warn and _warnings.warn:
                    _warnings.warn("Implicitly cleaning up {!r}".format(self),
                                       ResourceWarning)

        def __exit__(self, exc, value, tb):
            self.cleanup()

        def __del__(self):
            # Issue a ResourceWarning if implicit cleanup needed
            self.cleanup(_warn=True)

        def _rmtree(self, path, _OSError=OSError, _sep=_os.path.sep,
                    _listdir=_os.listdir, _remove=_os.remove, _rmdir=_os.rmdir):
            # Essentially a stripped down version of shutil.rmtree.  We can't
            # use globals because they may be None'ed out at shutdown.
            if not isinstance(path, str):
                _sep = _sep.encode()
            try:
                for name in _listdir(path):
                    fullname = path + _sep + name
                    try:
                        _remove(fullname)
                    except _OSError:
                        self._rmtree(fullname)
                _rmdir(path)
            except _OSError:
                pass

if PY3:
    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())

def get_http_value(u, key):
    if PY3:
        return u.headers.get(key)
    else:
        return u.info().getheader(key)

########NEW FILE########
__FILENAME__ = config
# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
import logging
from platform import machine
from os.path import abspath, expanduser, isfile, isdir, join

from conda.compat import urlparse
from conda.utils import try_write


log = logging.getLogger(__name__)


default_python = '%d.%d' % sys.version_info[:2]

# ----- operating system and architecture -----

_sys_map = {'linux2': 'linux', 'linux': 'linux',
            'darwin': 'osx', 'win32': 'win'}
platform = _sys_map.get(sys.platform, 'unknown')
bits = 8 * tuple.__itemsize__

if platform == 'linux' and machine() == 'armv6l':
    subdir = 'linux-armv6l'
    arch_name = 'armv6l'
else:
    subdir = '%s-%d' % (platform, bits)
    arch_name = {64: 'x86_64', 32: 'x86'}[bits]

# ----- rc file -----

# This is used by conda config to check which keys are allowed in the config
# file. Be sure to update it when new keys are added.

#################################################################
# Also update the example condarc file when you add a key here! #
#################################################################

rc_list_keys = [
    'channels',
    'disallow',
    'create_default_packages',
    'track_features',
    'envs_dirs'
    ]

DEFAULT_CHANNEL_ALIAS = 'https://conda.binstar.org/'

rc_bool_keys = [
    'always_yes',
    'allow_softlinks',
    'changeps1',
    'use_pip',
    'binstar_upload',
    'binstar_personal',
    'show_channel_urls',
    'allow_other_channels',
    ]

# Not supported by conda config yet
rc_other = [
    'proxy_servers',
    'root_dir',
    'channel_alias',
    ]

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')
def get_rc_path():
    path = os.getenv('CONDARC')
    if path == ' ':
        return None
    if path:
        return path
    for path in user_rc_path, sys_rc_path:
        if isfile(path):
            return path
    return None

rc_path = get_rc_path()

def load_condarc(path):
    if not path:
        return {}
    try:
        import yaml
    except ImportError:
        sys.exit('Error: could not import yaml (required to read .condarc '
                 'config file: %s)' % path)

    return yaml.load(open(path)) or {}

rc = load_condarc(rc_path)

# ----- local directories -----

# root_dir should only be used for testing, which is why don't mention it in
# the documentation, to avoid confusion (it can really mess up a lot of
# things)
root_dir = abspath(expanduser(os.getenv('CONDA_ROOT',
                                        rc.get('root_dir', sys.prefix))))
root_writable = try_write(root_dir)
root_env_name = 'root'

def _default_envs_dirs():
    lst = [join(root_dir, 'envs')]
    if not root_writable:
        lst.insert(0, '~/envs')
    return lst

def _pathsep_env(name):
    x = os.getenv(name)
    if x is None:
        return []
    res = []
    for path in x.split(os.pathsep):
        if path == 'DEFAULTS':
            for p in rc.get('envs_dirs') or _default_envs_dirs():
                res.append(p)
        else:
            res.append(path)
    return res

envs_dirs = [abspath(expanduser(path)) for path in (
        _pathsep_env('CONDA_ENVS_PATH') or
        rc.get('envs_dirs') or
        _default_envs_dirs()
        )]

def pkgs_dir_from_envs_dir(envs_dir):
    if abspath(envs_dir) == abspath(join(root_dir, 'envs')):
        return join(root_dir, 'pkgs')
    else:
        return join(envs_dir, '.pkgs')

pkgs_dirs = [pkgs_dir_from_envs_dir(envs_dir) for envs_dir in envs_dirs]

# ----- default environment prefix -----

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if _default_env in (None, root_env_name):
    default_prefix = root_dir
elif os.sep in _default_env:
    default_prefix = abspath(_default_env)
else:
    for envs_dir in envs_dirs:
        default_prefix = join(envs_dir, _default_env)
        if isdir(default_prefix):
            break
    else:
        default_prefix = join(envs_dirs[0], _default_env)

# ----- channels -----

# Note, get_default_urls() and get_rc_urls() return unnormalized urls.

def get_default_urls():
    return ['http://repo.continuum.io/pkgs/free',
            'http://repo.continuum.io/pkgs/pro']

def get_rc_urls():
    if 'system' in rc['channels']:
        raise RuntimeError("system cannot be used in .condarc")
    return rc['channels']

def is_url(url):
    return urlparse.urlparse(url).scheme != ""

def normalize_urls(urls, platform=None):
    platform = platform or subdir
    newurls = []
    for url in urls:
        if url == "defaults":
            newurls.extend(normalize_urls(get_default_urls(),
                                          platform=platform))
        elif url == "system":
            if not rc_path:
                newurls.extend(normalize_urls(get_default_urls(),
                                              platform=platform))
            else:
                newurls.extend(normalize_urls(get_rc_urls(),
                                              platform=platform))
        elif not is_url(url):
            moreurls = normalize_urls([rc.get('channel_alias',
                DEFAULT_CHANNEL_ALIAS)+url], platform=platform)
            newurls.extend(moreurls)
        else:
            newurls.append('%s/%s/' % (url.rstrip('/'), platform))
    return newurls

def get_channel_urls(platform=None):
    if os.getenv('CIO_TEST'):
        base_urls = ['http://filer/pkgs/pro',
                     'http://filer/pkgs/free']
        if os.getenv('CIO_TEST') == '2':
            base_urls.insert(0, 'http://filer/test-pkgs')

    elif 'channels' not in rc:
        base_urls = get_default_urls()

    else:
        base_urls = get_rc_urls()

    return normalize_urls(base_urls, platform=platform)

def canonical_channel_name(channel):
    if channel is None:
        return '<unknown>'
    channel_alias = rc.get('channel_alias', DEFAULT_CHANNEL_ALIAS)
    if channel.startswith(channel_alias):
        return channel.split(channel_alias, 1)[1].split('/')[0]
    elif any(channel.startswith(i) for i in get_default_urls()):
        return 'defaults'
    elif channel.startswith('http://filer/'):
        return 'filer'
    else:
        return channel

# ----- allowed channels -----

def get_allowed_channels():
    if not isfile(sys_rc_path):
        return None
    sys_rc = load_condarc(sys_rc_path)
    if sys_rc.get('allow_other_channels', True):
        return None
    if 'channels' in sys_rc:
        base_urls = sys_rc['channels']
    else:
        base_urls = get_default_urls()
    return normalize_urls(base_urls)

allowed_channels = get_allowed_channels()

# ----- proxy -----

def get_proxy_servers():
    res = rc.get('proxy_servers')
    if res is None:
        import requests
        return requests.utils.getproxies()
    if isinstance(res, dict):
        return res
    sys.exit("Error: proxy_servers setting not a mapping")

# ----- foreign -----

try:
    with open(join(root_dir, 'conda-meta', 'foreign')) as fi:
        foreign = fi.read().split()
except IOError:
    foreign = [] if isdir(join(root_dir, 'conda-meta')) else ['python']

# ----- misc -----

always_yes = bool(rc.get('always_yes', False))
changeps1 = bool(rc.get('changeps1', True))
use_pip = bool(rc.get('use_pip', True))
binstar_upload = rc.get('binstar_upload', None) # None means ask
binstar_personal = bool(rc.get('binstar_personal', True))
allow_softlinks = bool(rc.get('allow_softlinks', True))
self_update = bool(rc.get('self_update', True))
# show channel URLs when displaying what is going to be downloaded
show_channel_urls = bool(rc.get('show_channel_urls', False))
# set packages disallowed to be installed
disallow = set(rc.get('disallow', []))
# packages which are added to a newly created environment by default
create_default_packages = list(rc.get('create_default_packages', []))
try:
    track_features = set(rc['track_features'].split())
except KeyError:
    track_features = None

########NEW FILE########
__FILENAME__ = connection
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from logging import getLogger
import re
import mimetypes
import os
import email
import base64
import ftplib
import cgi
from io import BytesIO

from conda.compat import urlparse, StringIO
from conda.config import get_proxy_servers

import requests

RETRIES = 3

log = getLogger(__name__)

# Modified from code in pip/download.py:

# Copyright (c) 2008-2014 The pip developers (see AUTHORS.txt file)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

class CondaSession(requests.Session):

    timeout = None

    def __init__(self, *args, **kwargs):
        retries = kwargs.pop('retries', RETRIES)

        super(CondaSession, self).__init__(*args, **kwargs)

        self.proxies = get_proxy_servers()

        # Configure retries
        if retries:
            http_adapter = requests.adapters.HTTPAdapter(max_retries=retries)
            self.mount("http://", http_adapter)
            self.mount("https://", http_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        # Enable ftp:// urls
        self.mount("ftp://", FTPAdapter())

class LocalFSAdapter(requests.adapters.BaseAdapter):

    def send(self, request, stream=None, timeout=None, verify=None, cert=None,
             proxies=None):
        pathname = url_to_path(request.url)

        resp = requests.models.Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            stats = os.stat(pathname)
        except OSError as exc:
            resp.status_code = 404
            resp.raw = exc
        else:
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            content_type = mimetypes.guess_type(pathname)[0] or "text/plain"
            resp.headers = requests.structures.CaseInsensitiveDict({
                "Content-Type": content_type,
                "Content-Length": stats.st_size,
                "Last-Modified": modified,
            })

            resp.raw = open(pathname, "rb")
            resp.close = resp.raw.close

        return resp

    def close(self):
        pass

def url_to_path(url):
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)
    path = url[len('file:'):].lstrip('/')
    path = urlparse.unquote(path)
    if _url_drive_re.match(path):
        path = path[0] + ':' + path[2:]
    else:
        path = '/' + path
    return path

_url_drive_re = re.compile('^([a-z])[:|]', re.I)

# Taken from requests-ftp
# (https://github.com/Lukasa/requests-ftp/blob/master/requests_ftp/ftp.py)

# Copyright 2012 Cory Benfield

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

class FTPAdapter(requests.adapters.BaseAdapter):
    '''A Requests Transport Adapter that handles FTP urls.'''
    def __init__(self):
        super(FTPAdapter, self).__init__()

        # Build a dictionary keyed off the methods we support in upper case.
        # The values of this dictionary should be the functions we use to
        # send the specific queries.
        self.func_table = {'LIST': self.list,
                           'RETR': self.retr,
                           'STOR': self.stor,
                           'NLST': self.nlst,
                           'GET':  self.retr,}

    def send(self, request, **kwargs):
        '''Sends a PreparedRequest object over FTP. Returns a response object.
        '''
        # Get the authentication from the prepared request, if any.
        auth = self.get_username_password_from_header(request)

        # Next, get the host and the path.
        host, port, path = self.get_host_and_path_from_url(request)

        # Sort out the timeout.
        timeout = kwargs.get('timeout', None)

        # Establish the connection and login if needed.
        self.conn = ftplib.FTP()
        self.conn.connect(host, port, timeout)

        if auth is not None:
            self.conn.login(auth[0], auth[1])
        else:
            self.conn.login()

        # Get the method and attempt to find the function to call.
        resp = self.func_table[request.method](path, request)

        # Return the response.
        return resp

    def close(self):
        '''Dispose of any internal state.'''
        # Currently this is a no-op.
        pass

    def list(self, path, request):
        '''Executes the FTP LIST command on the given path.'''
        data = StringIO()

        # To ensure the StringIO gets cleaned up, we need to alias its close
        # method to the release_conn() method. This is a dirty hack, but there
        # you go.
        data.release_conn = data.close

        self.conn.cwd(path)
        code = self.conn.retrbinary('LIST', data_callback_factory(data))

        # When that call has finished executing, we'll have all our data.
        response = build_text_response(request, data, code)

        # Close the connection.
        self.conn.close()

        return response

    def retr(self, path, request):
        '''Executes the FTP RETR command on the given path.'''
        data = BytesIO()

        # To ensure the BytesIO gets cleaned up, we need to alias its close
        # method. See self.list().
        data.release_conn = data.close

        code = self.conn.retrbinary('RETR ' + path, data_callback_factory(data))

        response = build_binary_response(request, data, code)

        # Close the connection.
        self.conn.close()

        return response

    def stor(self, path, request):
        '''Executes the FTP STOR command on the given path.'''

        # First, get the file handle. We assume (bravely)
        # that there is only one file to be sent to a given URL. We also
        # assume that the filename is sent as part of the URL, not as part of
        # the files argument. Both of these assumptions are rarely correct,
        # but they are easy.
        data = parse_multipart_files(request)

        # Split into the path and the filename.
        path, filename = os.path.split(path)

        # Switch directories and upload the data.
        self.conn.cwd(path)
        code = self.conn.storbinary('STOR ' + filename, data)

        # Close the connection and build the response.
        self.conn.close()

        response = build_binary_response(request, BytesIO(), code)

        return response

    def nlst(self, path, request):
        '''Executes the FTP NLST command on the given path.'''
        data = StringIO()

        # Alias the close method.
        data.release_conn = data.close

        self.conn.cwd(path)
        code = self.conn.retrbinary('NLST', data_callback_factory(data))

        # When that call has finished executing, we'll have all our data.
        response = build_text_response(request, data, code)

        # Close the connection.
        self.conn.close()

        return response

    def get_username_password_from_header(self, request):
        '''Given a PreparedRequest object, reverse the process of adding HTTP
        Basic auth to obtain the username and password. Allows the FTP adapter
        to piggyback on the basic auth notation without changing the control
        flow.'''
        auth_header = request.headers.get('Authorization')

        if auth_header:
            # The basic auth header is of the form 'Basic xyz'. We want the
            # second part. Check that we have the right kind of auth though.
            encoded_components = auth_header.split()[:2]
            if encoded_components[0] != 'Basic':
                raise AuthError('Invalid form of Authentication used.')
            else:
                encoded = encoded_components[1]

            # Decode the base64 encoded string.
            decoded = base64.b64decode(encoded)

            # The string is of the form 'username:password'. Split on the
            # colon.
            components = decoded.split(':')
            username = components[0]
            password = components[1]
            return (username, password)
        else:
            # No auth header. Return None.
            return None

    def get_host_and_path_from_url(self, request):
        '''Given a PreparedRequest object, split the URL in such a manner as to
        determine the host and the path. This is a separate method to wrap some
        of urlparse's craziness.'''
        url = request.url
        # scheme, netloc, path, params, query, fragment = urlparse(url)
        parsed = urlparse.urlparse(url)
        path = parsed.path

        # If there is a slash on the front of the path, chuck it.
        if path[0] == '/':
            path = path[1:]

        host = parsed.hostname
        port = parsed.port or 0

        return (host, port, path)

def data_callback_factory(variable):
    '''Returns a callback suitable for use by the FTP library. This callback
    will repeatedly save data into the variable provided to this function. This
    variable should be a file-like structure.'''
    def callback(data):
        variable.write(data)
        return

    return callback

class AuthError(Exception):
    '''Denotes an error with authentication.'''
    pass

def build_text_response(request, data, code):
    '''Build a response for textual data.'''
    return build_response(request, data, code, 'ascii')

def build_binary_response(request, data, code):
    '''Build a response for data whose encoding is unknown.'''
    return build_response(request, data, code,  None)

def build_response(request, data, code, encoding):
    '''Builds a response object from the data returned by ftplib, using the
    specified encoding.'''
    response = requests.Response()

    response.encoding = encoding

    # Fill in some useful fields.
    response.raw = data
    response.url = request.url
    response.request = request
    response.status_code = code.split()[0]

    # Make sure to seek the file-like raw object back to the start.
    response.raw.seek(0)

    # Run the response hook.
    response = requests.hooks.dispatch_hook('response', request.hooks, response)
    return response

def parse_multipart_files(request):
    '''Given a prepared reqest, return a file-like object containing the
    original data. This is pretty hacky.'''
    # Start by grabbing the pdict.
    _, pdict = cgi.parse_header(request.headers['Content-Type'])

    # Now, wrap the multipart data in a BytesIO buffer. This is annoying.
    buf = BytesIO()
    buf.write(request.body)
    buf.seek(0)

    # Parse the data. Simply take the first file.
    data = cgi.parse_multipart(buf, pdict)
    _, filedata = data.popitem()
    buf.close()

    # Get a BytesIO now, and write the file into it.
    buf = BytesIO()
    buf.write(''.join(filedata))
    buf.seek(0)

    return buf

# Taken from urllib3 (actually
# https://github.com/shazow/urllib3/pull/394). Once it is fully upstreamed to
# requests.packages.urllib3 we can just use that.


def unparse_url(U):
    """
    Convert a :class:`.Url` into a url

    The input can be any iterable that gives ['scheme', 'auth', 'host',
    'port', 'path', 'query', 'fragment']. Unused items should be None.

    This function should more or less round-trip with :func:`.parse_url`. The
    returned url may not be exactly the same as the url inputted to
    :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
    with a blank port).


    Example: ::

        >>> Url = parse_url('http://google.com/mail/')
        >>> unparse_url(Url)
        'http://google.com/mail/'
        >>> unparse_url(['http', 'username:password', 'host.com', 80,
        ... '/path', 'query', 'fragment'])
        'http://username:password@host.com:80/path?query#fragment'
    """
    scheme, auth, host, port, path, query, fragment = U
    url = ''

    # We use "is not None" we want things to happen with empty strings (or 0 port)
    if scheme is not None:
        url = scheme + '://'
    if auth is not None:
        url += auth + '@'
    if host is not None:
        url += host
    if port is not None:
        url += ':' + str(port)
    if path is not None:
        url += path
    if query is not None:
        url += '?' + query
    if fragment is not None:
        url += '#' + fragment

    return url

########NEW FILE########
__FILENAME__ = console
from __future__ import print_function, division, absolute_import

import sys
import logging

from conda.utils import memoized
from conda.progressbar import (Bar, ETA, FileTransferSpeed, Percentage,
                               ProgressBar)


fetch_progress = ProgressBar(
    widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
             FileTransferSpeed()])

progress = ProgressBar(widgets=['', ' ', Bar(), ' ', Percentage()])


class FetchProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'fetch.start':
            filename, maxval = record.msg
            fetch_progress.widgets[0] = filename
            fetch_progress.maxval = maxval
            fetch_progress.start()

        elif record.name == 'fetch.update':
            n = record.msg
            fetch_progress.update(n)

        elif record.name == 'fetch.stop':
            fetch_progress.finish()


class ProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'progress.start':
            progress.maxval = record.msg
            progress.start()

        elif record.name == 'progress.update':
            name, n = record.msg
            progress.widgets[0] = '[%-20s]' % name
            progress.update(n)

        elif record.name == 'progress.stop':
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()


class PrintHandler(logging.Handler):
    def emit(self, record):
        if record.name == 'print':
            print(record.msg)

class DotHandler(logging.Handler):
    def emit(self, record):
        try:
            sys.stdout.write('.')
            sys.stdout.flush()
        except IOError:
            # sys.stdout.flush doesn't work in pythonw
            pass

class SysStdoutWriteHandler(logging.Handler):
    def emit(self, record):
        try:
            sys.stdout.write(record.msg)
            sys.stdout.flush()
        except IOError:
            pass


class SysStderrWriteHandler(logging.Handler):
    def emit(self, record):
        try:
            sys.stderr.write(record.msg)
            sys.stderr.flush()
        except IOError:
            pass

@memoized  # to avoid setting up handlers more than once
def setup_verbose_handlers():
    fetch_prog_logger = logging.getLogger('fetch')
    fetch_prog_logger.setLevel(logging.INFO)
    fetch_prog_logger.addHandler(FetchProgressHandler())

    prog_logger = logging.getLogger('progress')
    prog_logger.setLevel(logging.INFO)
    prog_logger.addHandler(ProgressHandler())

    print_logger = logging.getLogger('print')
    print_logger.setLevel(logging.INFO)
    print_logger.addHandler(PrintHandler())

@memoized
def setup_handlers():
    dotlogger = logging.getLogger('dotupdate')
    dotlogger.setLevel(logging.DEBUG)
    dotlogger.addHandler(DotHandler())

    stdoutlogger = logging.getLogger('stdoutlog')
    stdoutlogger.setLevel(logging.DEBUG)
    stdoutlogger.addHandler(SysStdoutWriteHandler())

    stderrlogger = logging.getLogger('stderrlog')
    stderrlogger.setLevel(logging.DEBUG)
    stderrlogger.addHandler(SysStderrWriteHandler())

########NEW FILE########
__FILENAME__ = fetch
# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import bz2
import json
import shutil
import hashlib
import tempfile
from logging import getLogger
from os.path import basename, isdir, join
import sys
import getpass
# from multiprocessing.pool import ThreadPool

from conda import config
from conda.utils import memoized
from conda.connection import CondaSession, unparse_url
from conda.compat import itervalues, get_http_value, input
from conda.lock import Locked

import requests

log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False


def create_cache_dir():
    cache_dir = join(config.pkgs_dirs[0], 'cache')
    try:
        os.makedirs(cache_dir)
    except OSError:
        pass
    return cache_dir


def cache_fn_url(url):
    return '%s.json' % hashlib.md5(url.encode('utf-8')).hexdigest()


def add_http_value_to_dict(u, http_key, d, dict_key):
    value = get_http_value(u, http_key)
    if value:
        d[dict_key] = value


def fetch_repodata(url, cache_dir=None, use_cache=False, session=None):
    dotlog.debug("fetching repodata: %s ..." % url)

    session = session or CondaSession()

    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))
    try:
        cache = json.load(open(cache_path))
    except (IOError, ValueError):
        cache = {'packages': {}}

    if use_cache:
        return cache

    headers = {}
    if "_tag" in cache:
        headers["If-None-Match"] = cache["_etag"]
    if "_mod" in cache:
        headers["If-Modified-Since"] = cache["_mod"]

    try:
        resp = session.get(url + 'repodata.json.bz2', headers=headers, proxies=session.proxies)
        resp.raise_for_status()
        if resp.status_code != 304:
            cache = json.loads(bz2.decompress(resp.content).decode('utf-8'))

    except ValueError as e:
        raise RuntimeError("Invalid index file: %srepodata.json.bz2: %s" %
            (url, e))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 407: # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)
        msg = "HTTPError: %s: %s\n" % (e, url)
        log.debug(msg)
        raise RuntimeError(msg)

    except requests.exceptions.ConnectionError as e:
        # requests isn't so nice here. For whatever reason, https gives this
        # error and http gives the above error. Also, there is no status_code
        # attribute here. We have to just check if it looks like 407.  See
        # https://github.com/kennethreitz/requests/issues/2061.
        if "407" in str(e): # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)

        msg = "Connection error: %s: %s\n" % (e, url)
        stderrlog.info('Could not connect to %s\n' % url)
        log.debug(msg)
        if fail_unknown_host:
            raise RuntimeError(msg)

    cache['_url'] = url
    try:
        with open(cache_path, 'w') as fo:
            json.dump(cache, fo, indent=2, sort_keys=True)
    except IOError:
        pass

    return cache or None

def handle_proxy_407(url, session):
    """
    Prompts the user for the proxy username and password and modifies the
    proxy in the session object to include it.
    """
    # We could also use HTTPProxyAuth, but this does not work with https
    # proxies (see https://github.com/kennethreitz/requests/issues/2061).
    scheme = requests.packages.urllib3.util.url.parse_url(url).scheme
    username, passwd = get_proxy_username_and_pass(scheme)
    session.proxies[scheme] = add_username_and_pass_to_url(session.proxies[scheme], username, passwd)

def add_username_and_pass_to_url(url, username, passwd):
    urlparts = list(requests.packages.urllib3.util.url.parse_url(url))
    urlparts[1] = username + ':' + passwd
    return unparse_url(urlparts)

def get_proxy_username_and_pass(scheme):
    username = input("\n%s proxy username: " % scheme)
    passwd = getpass.getpass("Password:")
    return username, passwd

@memoized
def fetch_index(channel_urls, use_cache=False, unknown=False):
    log.debug('channel_urls=' + repr(channel_urls))
    # pool = ThreadPool(5)
    index = {}
    stdoutlog.info("Fetching package metadata: ")
    session = CondaSession()
    for url in reversed(channel_urls):
        if config.allowed_channels and url not in config.allowed_channels:
            sys.exit("""
Error: URL '%s' not in allowed channels.

Allowed channels are:
  - %s
""" % (url, '\n  - '.join(config.allowed_channels)))

    repodatas = map(lambda url: (url, fetch_repodata(url,
        use_cache=use_cache, session=session)), reversed(channel_urls))
    for url, repodata in repodatas:
        if repodata is None:
            continue
        new_index = repodata['packages']
        for info in itervalues(new_index):
            info['channel'] = url
        index.update(new_index)
    stdoutlog.info('\n')
    if unknown:
        for pkgs_dir in config.pkgs_dirs:
            if not isdir(pkgs_dir):
                continue
            for dn in os.listdir(pkgs_dir):
                fn = dn + '.tar.bz2'
                if fn in index:
                    continue
                try:
                    with open(join(pkgs_dir, dn, 'info', 'index.json')) as fi:
                        meta = json.load(fi)
                except IOError:
                    continue
                if 'depends' not in meta:
                    continue
                log.debug("adding cached pkg to index: %s" % fn)
                index[fn] = meta

    return index

def fetch_pkg(info, dst_dir=None, session=None):
    '''
    fetch a package given by `info` and store it into `dst_dir`
    '''
    if dst_dir is None:
        dst_dir = config.pkgs_dirs[0]

    session = session or CondaSession()

    fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    url = info['channel'] + fn
    log.debug("url=%r" % url)
    path = join(dst_dir, fn)

    download(url, path, session=session, md5=info['md5'], urlstxt=True)

def download(url, dst_path, session=None, md5=None, urlstxt=False):
    pp = dst_path + '.part'
    dst_dir = os.path.split(dst_path)[0]
    session = session or CondaSession()

    with Locked(dst_dir):
        try:
            resp = session.get(url, stream=True, proxies=session.proxies)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 407: # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5, urlstxt=urlstxt)
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise RuntimeError(msg)

        except requests.exceptions.ConnectionError as e:
            # requests isn't so nice here. For whatever reason, https gives this
            # error and http gives the above error. Also, there is no status_code
            # attribute here. We have to just check if it looks like 407.  See
            # https://github.com/kennethreitz/requests/issues/2061.
            if "407" in str(e): # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5, urlstxt=urlstxt)
        except IOError as e:
            raise RuntimeError("Could not open '%s': %s" % (url, e))

        size = resp.headers.get('Content-Length')
        if size:
            size = int(size)
            fn = basename(dst_path)
            getLogger('fetch.start').info((fn[:14], size))

        n = 0
        if md5:
            h = hashlib.new('md5')
        try:
            with open(pp, 'wb') as fo:
                for chunk in resp.iter_content(2**14):
                    try:
                        fo.write(chunk)
                    except IOError:
                        raise RuntimeError("Failed to write to %r." % pp)
                    if md5:
                        h.update(chunk)
                    n += len(chunk)
                    if size:
                        getLogger('fetch.update').info(n)
        except IOError:
            raise RuntimeError("Could not open %r for writing.  "
                "Permissions problem or missing directory?" % pp)

        if size:
            getLogger('fetch.stop').info(None)

        if md5 and h.hexdigest() != md5:
            raise RuntimeError("MD5 sums mismatch for download: %s (%s != %s)" % (url, h.hexdigest(), md5))

        try:
            os.rename(pp, dst_path)
        except OSError as e:
            raise RuntimeError("Could not rename %r to %r: %r" % (pp,
                dst_path, e))

        if urlstxt:
            try:
                with open(join(dst_dir, 'urls.txt'), 'a') as fa:
                    fa.write('%s\n' % url)
            except IOError:
                pass

class TmpDownload(object):
    """
    Context manager to handle downloads to a tempfile
    """
    def __init__(self, url, verbose=True):
        self.url = url
        self.verbose = verbose

    def __enter__(self):
        if '://' not in self.url:
            # if we provide the file itself, no tmp dir is created
            self.tmp_dir = None
            return self.url
        else:
            if self.verbose:
                from conda.console import setup_handlers
                setup_handlers()
            self.tmp_dir = tempfile.mkdtemp()
            dst = join(self.tmp_dir, basename(self.url))
            download(self.url, dst)
            return dst

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)

########NEW FILE########
__FILENAME__ = history
from __future__ import print_function, division, absolute_import

import os
import re
import sys
import time
from os.path import isdir, isfile, join

from conda import install



def write_head(fo):
    fo.write("==> %s <==\n" % time.strftime('%Y-%m-%d %H:%M:%S'))
    fo.write("# cmd: %s\n" % (' '.join(sys.argv)))

def is_diff(content):
    return any(s.startswith(('-', '+')) for s in content)

def pretty_diff(diff):
    added = {}
    removed = {}
    for s in diff:
        fn = s[1:]
        name, version, unused_build = fn.rsplit('-', 2)
        if s.startswith('-'):
            removed[name.lower()] = version
        elif s.startswith('+'):
            added[name.lower()] = version
    changed = set(added) & set(removed)
    for name in sorted(changed):
        yield ' %s  {%s -> %s}' % (name, removed[name], added[name])
    for name in sorted(set(removed) - changed):
        yield '-%s-%s' % (name, removed[name])
    for name in sorted(set(added) - changed):
        yield '+%s-%s' % (name, added[name])

def pretty_content(content):
    if is_diff(content):
        return pretty_diff(content)
    else:
        return iter(sorted(content))


class History(object):

    def __init__(self, prefix):
        self.prefix = prefix
        self.meta_dir = join(prefix, 'conda-meta')
        self.path = join(self.meta_dir, 'history')

    def __enter__(self):
        self.update()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.update()

    def init_log_file(self, force=False):
        if not force and isfile(self.path):
            return
        self.write_dists(install.linked(self.prefix))

    def update(self):
        """
        update the history file (creating a new one if necessary)
        """
        self.init_log_file()
        last = self.get_state()
        curr = set(install.linked(self.prefix))
        if last == curr:
            return
        self.write_changes(last, curr)

    def parse(self):
        """
        parse the history file and return a list of
        tuples(datetime strings, set of distributions/diffs)
        """
        res = []
        if not isfile(self.path):
            return res
        sep_pat = re.compile(r'==>\s*(.+?)\s*<==')
        for line in open(self.path):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = sep_pat.match(line)
            if m:
                dt = m.group(1)
                res.append((dt, set()))
            else:
                res[-1][1].add(line)
        return res

    def construct_states(self):
        """
        return a list of tuples(datetime strings, set of distributions)
        """
        res = []
        cur = set([])
        for dt, cont in self.parse():
            if not is_diff(cont):
                cur = cont
            else:
                for s in cont:
                    if s.startswith('-'):
                        cur.discard(s[1:])
                    elif s.startswith('+'):
                        cur.add(s[1:])
                    else:
                        raise Exception('Did not expect: %s' % s)
            res.append((dt, cur.copy()))
        return res

    def get_state(self, rev=-1):
        """
        return the state, i.e. the set of distributions, for a given revision,
        defaults to latest (which is the same as the current state when
        the log file is up-to-date)
        """
        states = self.construct_states()
        if not states:
            return set([])
        times, pkgs = zip(*states)
        return pkgs[rev]

    def print_log(self):
        for i, (date, content) in enumerate(self.parse()):
            print('%s  (rev %d)' % (date, i))
            for line in pretty_content(content):
                print('    %s' % line)
            print()

    def write_dists(self, dists):
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)
        with open(self.path, 'w') as fo:
            write_head(fo)
            for dist in sorted(dists):
                fo.write('%s\n' % dist)

    def write_changes(self, last_state, current_state):
        with open(self.path, 'a') as fo:
            write_head(fo)
            for fn in sorted(last_state - current_state):
                fo.write('-%s\n' % fn)
            for fn in sorted(current_state - last_state):
                fo.write('+%s\n' % fn)


if __name__ == '__main__':
    with History(sys.prefix) as h:
        h.print_log()

########NEW FILE########
__FILENAME__ = install
# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' This module contains:
  * all low-level code for extracting, linking and unlinking packages
  * a very simple CLI

These API functions have argument names referring to:

    dist:        canonical package name (e.g. 'numpy-1.6.2-py26_0')

    pkgs_dir:    the "packages directory" (e.g. '/opt/anaconda/pkgs' or
                 '/home/joe/envs/.pkgs')

    prefix:      the prefix of a particular environment, which may also
                 be the "default" environment (i.e. sys.prefix),
                 but is otherwise something like '/opt/anaconda/envs/foo',
                 or even any prefix, e.g. '/home/joe/myenv'

Also, this module is directly invoked by the (self extracting (sfx)) tarball
installer to create the initial environment, therefore it needs to be
standalone, i.e. not import any other parts of `conda` (only depend on
the standard library).
'''

from __future__ import print_function, division, absolute_import

import os
import json
import shutil
import stat
import sys
import subprocess
import tarfile
import traceback
import logging
from os.path import abspath, basename, dirname, isdir, isfile, islink, join

try:
    from conda.lock import Locked
except ImportError:
    # Make sure this still works as a standalone script for the Anaconda
    # installer.
    class Locked(object):
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            pass
        def __exit__(self, exc_type, exc_value, traceback):
            pass

on_win = bool(sys.platform == 'win32')

if on_win:
    import ctypes
    from ctypes import wintypes

    # on Windows we cannot update these packages in the root environment
    # because of the file lock problem
    win_ignore_root = set(['python', 'pycosat', 'menuinst', 'psutil'])

    CreateHardLink = ctypes.windll.kernel32.CreateHardLinkW
    CreateHardLink.restype = wintypes.BOOL
    CreateHardLink.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                               wintypes.LPVOID]
    try:
        CreateSymbolicLink = ctypes.windll.kernel32.CreateSymbolicLinkW
        CreateSymbolicLink.restype = wintypes.BOOL
        CreateSymbolicLink.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       wintypes.DWORD]
    except AttributeError:
        CreateSymbolicLink = None

    def win_hard_link(src, dst):
        "Equivalent to os.link, using the win32 CreateHardLink call."
        if not CreateHardLink(dst, src, None):
            raise OSError('win32 hard link failed')

    def win_soft_link(src, dst):
        "Equivalent to os.symlink, using the win32 CreateSymbolicLink call."
        if CreateSymbolicLink is None:
            raise OSError('win32 soft link not supported')
        if not CreateSymbolicLink(dst, src, isdir(src)):
            raise OSError('win32 soft link failed')


log = logging.getLogger(__name__)

class NullHandler(logging.Handler):
    """ Copied from Python 2.7 to avoid getting
        `No handlers could be found for logger "patch"`
        http://bugs.python.org/issue16539
    """
    def handle(self, record):
        pass
    def emit(self, record):
        pass
    def createLock(self):
        self.lock = None

log.addHandler(NullHandler())

LINK_HARD = 1
LINK_SOFT = 2
LINK_COPY = 3
link_name_map = {
    LINK_HARD: 'hard-link',
    LINK_SOFT: 'soft-link',
    LINK_COPY: 'copy',
}

def _link(src, dst, linktype=LINK_HARD):
    if linktype == LINK_HARD:
        if on_win:
            win_hard_link(src, dst)
        else:
            os.link(src, dst)
    elif linktype == LINK_SOFT:
        if on_win:
            win_soft_link(src, dst)
        else:
            os.symlink(src, dst)
    elif linktype == LINK_COPY:
        # copy relative symlinks as symlinks
        if not on_win and islink(src) and not os.readlink(src).startswith('/'):
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)
    else:
        raise Exception("Did not expect linktype=%r" % linktype)


def rm_rf(path):
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        os.unlink(path)

    elif isdir(path):
        shutil.rmtree(path)

def rm_empty_dir(path):
    """
    Remove the directory `path` if it is a directory and empty.
    If the directory does not exist or is not empty, do nothing.
    """
    try:
        os.rmdir(path)
    except OSError: # directory might not exist or not be empty
        pass


def yield_lines(path):
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield line


prefix_placeholder = ('/opt/anaconda1anaconda2'
                      # this is intentionally split into parts,
                      # such that running this program on itself
                      # will leave it unchanged
                      'anaconda3')
def read_has_prefix(path):
    """
    reads `has_prefix` file and return dict mapping filenames to
    tuples(placeholder, mode)
    """
    res = {}
    try:
        for line in yield_lines(path):
            try:
                placeholder, mode, f = line.split(None, 2)
                res[f] = (placeholder, mode)
            except ValueError:
                res[line] = (prefix_placeholder, 'text')
    except IOError:
        pass
    return res

class PaddingError(Exception):
    pass

def binary_replace(data, a, b):
    """
    Perform a binary replacement of `data`, where the placeholder `a` is
    replaced with `b` and the remaining string is padded with zeros.
    All input arguments are expected to be bytes objects.
    """
    import re

    def replace(match):
        padding = len(match.group()) - len(b) - len(match.group(1))
        if padding < 1:
            raise PaddingError
        return b + match.group(1) + b'\0' * padding
    pat = re.compile(a.replace(b'.', b'\.') + b'([^\0\\s]*?)\0')
    res = pat.sub(replace, data)
    assert len(res) == len(data)
    return res

def update_prefix(path, new_prefix, placeholder=prefix_placeholder,
                  mode='text'):
    path = os.path.realpath(path)
    with open(path, 'rb') as fi:
        data = fi.read()
    if mode == 'text':
        new_data = data.replace(placeholder.encode('utf-8'),
                                new_prefix.encode('utf-8'))
    elif mode == 'binary':
        new_data = binary_replace(data, placeholder.encode('utf-8'),
                                  new_prefix.encode('utf-8'))
    else:
        sys.exit("Invalid mode:" % mode)

    if new_data == data:
        return
    st = os.lstat(path)
    with open(path, 'wb') as fo:
        fo.write(new_data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def name_dist(dist):
    return dist.rsplit('-', 2)[0]


def create_meta(prefix, dist, info_dir, extra_info):
    """
    Create the conda metadata, in a given prefix, for a given package.
    """
    # read info/index.json first
    with open(join(info_dir, 'index.json')) as fi:
        meta = json.load(fi)
    # add extra info
    meta.update(extra_info)
    # write into <env>/conda-meta/<dist>.json
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        os.makedirs(meta_dir)
    with open(join(meta_dir, dist + '.json'), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)


def mk_menus(prefix, files, remove=False):
    if abspath(prefix) != abspath(sys.prefix):
        # we currently only want to create menu items for packages
        # in default environment
        return
    menu_files = [f for f in files
                  if f.startswith('Menu/') and f.endswith('.json')]
    if not menu_files:
        return
    try:
        import menuinst
    except ImportError:
        return
    for f in menu_files:
        try:
            menuinst.install(join(prefix, f), remove, prefix)
        except:
            print("menuinst Exception:")
            traceback.print_exc(file=sys.stdout)


def run_script(prefix, dist, action='post-link', env_prefix=None):
    """
    call the post-link (or pre-unlink) script, and return True on success,
    False on failure
    """
    path = join(prefix, 'Scripts' if on_win else 'bin', '.%s-%s.%s' % (
            name_dist(dist),
            action,
            'bat' if on_win else 'sh'))
    if not isfile(path):
        return True
    if on_win:
        try:
            args = [os.environ['COMSPEC'], '/c', path]
        except KeyError:
            return False
    else:
        args = ['/bin/bash', path]
    env = os.environ
    env['PREFIX'] = env_prefix or prefix
    env['PKG_NAME'], env['PKG_VERSION'], env['PKG_BUILDNUM'] = str(dist).rsplit('-', 2)
    try:
        subprocess.check_call(args, env=env)
    except subprocess.CalledProcessError:
        return False
    return True

def read_url(pkgs_dir, dist):
    try:
        data = open(join(pkgs_dir, 'urls.txt')).read()
        urls = data.split()
        for url in urls[::-1]:
            if url.endswith('/%s.tar.bz2' % dist):
                return url
    except IOError:
        pass
    return None

def read_no_link(info_dir):
    res = set()
    for fn in 'no_link', 'no_softlink':
        try:
            res.update(set(yield_lines(join(info_dir, fn))))
        except IOError:
            pass
    return res

# Should this be an API function?
def symlink_conda(prefix, root_dir):
    root_conda = join(root_dir, 'bin', 'conda')
    root_activate = join(root_dir, 'bin', 'activate')
    root_deactivate = join(root_dir, 'bin', 'deactivate')
    prefix_conda = join(prefix, 'bin', 'conda')
    prefix_activate = join(prefix, 'bin', 'activate')
    prefix_deactivate = join(prefix, 'bin', 'deactivate')
    if not os.path.exists(join(prefix, 'bin')):
        os.makedirs(join(prefix, 'bin'))
    if not os.path.exists(prefix_conda):
        os.symlink(root_conda, prefix_conda)
    if not os.path.exists(prefix_activate):
        os.symlink(root_activate, prefix_activate)
    if not os.path.exists(prefix_deactivate):
        os.symlink(root_deactivate, prefix_deactivate)

# ========================== begin API functions =========================

def try_hard_link(pkgs_dir, prefix, dist):
    src = join(pkgs_dir, dist, 'info', 'index.json')
    dst = join(prefix, '.tmp-%s' % dist)
    assert isfile(src)
    assert not isfile(dst)
    if not isdir(prefix):
        os.makedirs(prefix)
    try:
        _link(src, dst, LINK_HARD)
        return True
    except OSError:
        return False
    finally:
        rm_rf(dst)
        rm_empty_dir(prefix)

# ------- package cache ----- fetched

def fetched(pkgs_dir):
    if not isdir(pkgs_dir):
        return set()
    return set(fn[:-8] for fn in os.listdir(pkgs_dir)
               if fn.endswith('.tar.bz2'))

def is_fetched(pkgs_dir, dist):
    return isfile(join(pkgs_dir, dist + '.tar.bz2'))

def rm_fetched(pkgs_dir, dist):
    with Locked(pkgs_dir):
        path = join(pkgs_dir, dist + '.tar.bz2')
        rm_rf(path)

# ------- package cache ----- extracted

def extracted(pkgs_dir):
    """
    return the (set of canonical names) of all extracted packages
    """
    if not isdir(pkgs_dir):
        return set()
    return set(dn for dn in os.listdir(pkgs_dir)
               if (isfile(join(pkgs_dir, dn, 'info', 'files')) and
                   isfile(join(pkgs_dir, dn, 'info', 'index.json'))))

def extract(pkgs_dir, dist):
    """
    Extract a package, i.e. make a package available for linkage.  We assume
    that the compressed packages is located in the packages directory.
    """
    with Locked(pkgs_dir):
        path = join(pkgs_dir, dist)
        t = tarfile.open(path + '.tar.bz2')
        t.extractall(path=path)
        t.close()
        if sys.platform.startswith('linux') and os.getuid() == 0:
            # When extracting as root, tarfile will by restore ownership
            # of extracted files.  However, we want root to be the owner
            # (our implementation of --no-same-owner).
            for root, dirs, files in os.walk(path):
                for fn in files:
                    p = join(root, fn)
                    os.lchown(p, 0, 0)

def is_extracted(pkgs_dir, dist):
    return (isfile(join(pkgs_dir, dist, 'info', 'files')) and
            isfile(join(pkgs_dir, dist, 'info', 'index.json')))

def rm_extracted(pkgs_dir, dist):
    with Locked(pkgs_dir):
        path = join(pkgs_dir, dist)
        rm_rf(path)

# ------- linkage of packages

def linked(prefix):
    """
    Return the (set of canonical names) of linked packages in prefix.
    """
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        return set()
    return set(fn[:-5] for fn in os.listdir(meta_dir) if fn.endswith('.json'))


def is_linked(prefix, dist):
    """
    Return the install meta-data for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    meta_path = join(prefix, 'conda-meta', dist + '.json')
    try:
        with open(meta_path) as fi:
            return json.load(fi)
    except IOError:
        return None


def link(pkgs_dir, prefix, dist, linktype=LINK_HARD, index=None):
    '''
    Set up a package in a specified (environment) prefix.  We assume that
    the package has been extracted (using extract() above).
    '''
    index = index or {}
    log.debug('pkgs_dir=%r, prefix=%r, dist=%r, linktype=%r' %
              (pkgs_dir, prefix, dist, linktype))
    if (on_win and abspath(prefix) == abspath(sys.prefix) and
              name_dist(dist) in win_ignore_root):
        # on Windows we have the file lock problem, so don't allow
        # linking or unlinking some packages
        print('Ignored: %s' % dist)
        return

    source_dir = join(pkgs_dir, dist)
    if not run_script(source_dir, dist, 'pre-link', prefix):
        sys.exit('Error: pre-link failed: %s' % dist)

    info_dir = join(source_dir, 'info')
    files = list(yield_lines(join(info_dir, 'files')))
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)

    with Locked(prefix), Locked(pkgs_dir):
        for f in files:
            src = join(source_dir, f)
            dst = join(prefix, f)
            dst_dir = dirname(dst)
            if not isdir(dst_dir):
                os.makedirs(dst_dir)
            if os.path.exists(dst):
                log.warn("file already exists: %r" % dst)
                try:
                    os.unlink(dst)
                except OSError:
                    log.error('failed to unlink: %r' % dst)
            lt = linktype
            if f in has_prefix_files or f in no_link or islink(src):
                lt = LINK_COPY
            try:
                _link(src, dst, lt)
            except OSError as e:
                log.error('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                          (src, dst, lt, e))

        if name_dist(dist) == '_cache':
            return

        for f in sorted(has_prefix_files):
            placeholder, mode = has_prefix_files[f]
            try:
                update_prefix(join(prefix, f), prefix, placeholder, mode)
            except PaddingError:
                sys.exit("ERROR: placeholder '%s' too short in: %s\n" %
                         (placeholder, dist))

        mk_menus(prefix, files, remove=False)

        if not run_script(prefix, dist, 'post-link'):
            sys.exit("Error: post-link failed for: %s" % dist)

        meta_dict = index.get(dist + '.tar.bz2', {})
        meta_dict['url'] = read_url(pkgs_dir, dist)
        meta_dict['files'] = files
        meta_dict['link'] = {'source': source_dir,
                             'type': link_name_map.get(linktype)}
        create_meta(prefix, dist, info_dir, meta_dict)

def unlink(prefix, dist):
    '''
    Remove a package from the specified environment, it is an error if the
    package does not exist in the prefix.
    '''
    if (on_win and abspath(prefix) == abspath(sys.prefix) and
              name_dist(dist) in win_ignore_root):
        # on Windows we have the file lock problem, so don't allow
        # linking or unlinking some packages
        print('Ignored: %s' % dist)
        return

    with Locked(prefix):
        run_script(prefix, dist, 'pre-unlink')

        meta_path = join(prefix, 'conda-meta', dist + '.json')
        with open(meta_path) as fi:
            meta = json.load(fi)

        mk_menus(prefix, meta['files'], remove=True)
        dst_dirs1 = set()

        for f in meta['files']:
            dst = join(prefix, f)
            dst_dirs1.add(dirname(dst))
            try:
                os.unlink(dst)
            except OSError: # file might not exist
                log.debug("could not remove file: '%s'" % dst)

        # remove the meta-file last
        os.unlink(meta_path)

        dst_dirs2 = set()
        for path in dst_dirs1:
            while len(path) > len(prefix):
                dst_dirs2.add(path)
                path = dirname(path)
        # in case there is nothing left
        dst_dirs2.add(join(prefix, 'conda-meta'))
        dst_dirs2.add(prefix)

        for path in sorted(dst_dirs2, key=len, reverse=True):
            rm_empty_dir(path)


def messages(prefix):
    path = join(prefix, '.messages.txt')
    try:
        with open(path) as fi:
            sys.stdout.write(fi.read())
    except IOError:
        pass
    finally:
        rm_rf(path)

# =========================== end API functions ==========================

def main():
    from pprint import pprint
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] [TARBALL/NAME]",
        description="low-level conda install tool, by default extracts "
                    "(if necessary) and links a TARBALL")

    p.add_option('-l', '--list',
                 action="store_true",
                 help="list all linked packages")

    p.add_option('--extract',
                 action="store_true",
                 help="extract package in pkgs cache")

    p.add_option('--link',
                 action="store_true",
                 help="link a package")

    p.add_option('--unlink',
                 action="store_true",
                 help="unlink a package")

    p.add_option('-p', '--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")

    p.add_option('--pkgs-dir',
                 action="store",
                 default=join(sys.prefix, 'pkgs'),
                 help="packages directory (defaults to %default)")

    p.add_option('--link-all',
                 action="store_true",
                 help="link all extracted packages")

    p.add_option('-v', '--verbose',
                 action="store_true")

    opts, args = p.parse_args()

    logging.basicConfig()

    if opts.list or opts.extract or opts.link_all:
        if args:
            p.error('no arguments expected')
    else:
        if len(args) == 1:
            dist = basename(args[0])
            if dist.endswith('.tar.bz2'):
                dist = dist[:-8]
        else:
            p.error('exactly one argument expected')

    pkgs_dir = opts.pkgs_dir
    prefix = opts.prefix
    if opts.verbose:
        print("pkgs_dir: %r" % pkgs_dir)
        print("prefix  : %r" % prefix)

    if opts.list:
        pprint(sorted(linked(prefix)))

    elif opts.link_all:
        dists = sorted(extracted(pkgs_dir))
        linktype = (LINK_HARD
                    if try_hard_link(pkgs_dir, prefix, dists[0]) else
                    LINK_COPY)
        if opts.verbose or linktype == LINK_COPY:
            print("linktype: %s" % link_name_map[linktype])
        for dist in dists:
            if opts.verbose or linktype == LINK_COPY:
                print("linking: %s" % dist)
            link(pkgs_dir, prefix, dist, linktype)
        messages(prefix)

    elif opts.extract:
        extract(pkgs_dir, dist)

    elif opts.link:
        link(pkgs_dir, prefix, dist)

    elif opts.unlink:
        unlink(prefix, dist)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = lock
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

"""
Tools for working with locks

A lock is just an empty directory. We use directories because this lets us use
the race condition-proof os.makedirs.

For now, there is one global lock for all of conda, because some things happen
globally (such as downloading packages).

We don't raise an error if the lock is named with the current PID
"""

import os
from os.path import join
import glob
from time import sleep

LOCKFN = '.conda_lock'


class Locked(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, path):
        self.path = path
        self.end = "-" + str(os.getpid())
        self.lock_path = join(self.path, LOCKFN + self.end)
        self.pattern = join(self.path, LOCKFN + '-*')
        self.remove = True

    def __enter__(self):
        retries = 10
        # Keep the string "LOCKERROR" in this string so that external
        # programs can look for it.
        lockstr = ("""\
    LOCKERROR: It looks like conda is already doing something.
    The lock %s was found. Wait for it to finish before continuing.
    If you are sure that conda is not running, remove it and try again.
    You can also use: $ conda clean --lock""" % self.lock_path)
        sleeptime = 1
        while retries:
            files = glob.glob(self.pattern)
            if files and not files[0].endswith(self.end):
                print(lockstr)
                print("Sleeping for %s seconds" % sleeptime)
                sleep(sleeptime)
                sleeptime *= 2
                retries -= 1
            else:
                break
        else:
            print("Exceeded max retries, giving up")
            raise RuntimeError(lockstr)

        if not files:
            try:
                os.makedirs(self.lock_path)
            except OSError:
                pass
        else: # PID lock already here --- someone else will remove it.
            self.remove = False

    def __exit__(self, exc_type, exc_value, traceback):
        if self.remove:
            for path in self.lock_path, self.path:
                try:
                    os.rmdir(path)
                except OSError:
                    pass

########NEW FILE########
__FILENAME__ = logic
# -*- coding: utf-8 -*-
"""
The basic idea to nest logical expressions is instead of trying to denest
things via distribution, we add new variables. So if we have some logical
expression expr, we replace it with x and add expr <-> x to the clauses,
where x is a new variable, and expr <-> x is recursively evaluated in the
same way, so that the final clauses are ORs of atoms.

To us this, create a new Clauses object with the max var, for instance, if you
already have [[1, 2, -3]], you would use C = Clause(3).  All functions return
a new literal, which represents that function, or true or false, which are
custom objects defined in this module, which means that the expression is
identically true or false.. They may also add new clauses to C.clauses, which
should be added to the clauses of the SAT solver.

All functions take atoms as arguments (an atom is an integer, representing a
literal or a negated literal, or the true or false objects defined in this
module), that is, it is the callers' responsibility to do the conversion of
expressions recursively. This is done because we do not have data structures
representing the various logical classes, only atoms.

"""
import sys
from collections import defaultdict
from functools import total_ordering
from itertools import islice
import logging

from conda.compat import log2, ceil
from conda.utils import memoize

dotlog = logging.getLogger('dotupdate')

# Custom classes for true and false. Using True and False is too risky, since
# True == 1, so it might be confused for the literal 1.
@total_ordering
class TrueClass(object):
    def __eq__(self, other):
        return isinstance(other, TrueClass)

    def __neg__(self):
        return false

    def __str__(self):
        return "true"
    __repr__ = __str__

    def __hash__(self):
        return 1

    def __lt__(self, other):
        if isinstance(other, TrueClass):
            return False
        if isinstance(other, FalseClass):
            return False
        return NotImplemented

@total_ordering
class FalseClass(object):
    def __eq__(self, other):
        return isinstance(other, FalseClass)

    def __neg__(self):
        return true

    def __str__(self):
        return "false"
    __repr__ = __str__

    def __hash__(self):
        return 0

    def __lt__(self, other):
        if isinstance(other, FalseClass):
            return False
        if isinstance(other, TrueClass):
            return True
        return NotImplemented

true = TrueClass()
false = FalseClass()

# TODO: Take advantage of polarity, meaning that we can add only one direction
# of the implication, expr -> x or expr <- x, depending on how expr appears.

# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).  The sorter code is in Hardware_sorters.cc.

class Clauses(object):
    def __init__(self, MAX_N=0):
        self.clauses = set()
        self.MAX_N = MAX_N

    def get_new_var(self):
        self.MAX_N += 1
        return self.MAX_N

    @memoize
    def ITE(self, c, t, f):
        """
        if c then t else f

        In this function, if any of c, t, or f are True and False the resulting
        expression is resolved.
        """
        if c == true:
            return t
        if c == false:
            return f
        if t == f:
            return t
        if t == -f:
            return self.Xor(c, f)
        if t == false or t == -c:
            return self.And(-c, f)
        if t == true or t == c:
            return self.Or(c, f)
        if f == false or f == c:
            return self.And(c, t)
        if f == true or f == -c:
            return self.Or(t, -c)

        # TODO: At this point, minisatp has
        # if t < f:
        #     swap(t, f)
        #     c = -c

        # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)
        x = self.get_new_var()
        # "Red" clauses are redundant, but they assist the unit propagation in the
        # SAT solver
        self.clauses |= {
            # Negative
            (-c, -t, x),
            (c, -f, x),
            (-t, -f, x), # Red
            # Positive
            (-c, t, -x),
            (c, f, -x),
            (t, f, -x), # Red
        }

        return x

    @memoize
    def And(self, f, g):
        if f == false or g == false:
            return false
        if f == true:
            return g
        if g == true:
            return f
        if f == g:
            return f
        if f == -g:
            return false

        # if g < f:
        #     swap(f, g)

        x = self.get_new_var()
        self.clauses |= {
            # positive
            # ~f -> ~x, ~g -> ~x
            (-x, f),
            (-x, g),
            # negative
            # (f AND g) -> x
            (x, -f, -g),
            }

        return x

    @memoize
    def Or(self, f, g):
        return -self.And(-f, -g)

    @memoize
    def Xor(self, f, g):
        # Minisatp treats XOR as NOT EQUIV
        if f == false:
            return g
        if f == true:
            return -g
        if g == false:
            return f
        if g == true:
            return -f
        if f == g:
            return false
        if f == -g:
            return true

        # if g < f:
        #     swap(f, g)

        x = self.get_new_var()
        self.clauses |= {
            # Positive
            (-x, f, g),
            (-x, -f, -g),
            # Negative
            (x, -f, g),
            (x, f, -g),
            }
        return x

    # Memoization is done in the function itself
    # TODO: This is a bit slower than the recursive version because it doesn't
    # "jump back" to the call site.
    def build_BDD(self, linear, sum=0):
        call_stack = [(linear, sum)]
        first_stack = call_stack[0]
        ret = {}
        while call_stack:
            linear, sum = call_stack[-1]
            lower_limit = linear.lo - sum
            upper_limit = linear.hi - sum
            if lower_limit <= 0 and upper_limit >= linear.total:
                ret[call_stack.pop()] = true
                continue
            if lower_limit > linear.total or upper_limit < 0:
                ret[call_stack.pop()] = false
                continue

            new_linear = linear[:-1]
            LC = linear.LC
            LA = linear.LA
            # This is handled by the abs() call below. I think it's done this way to
            # aid caching.
            hi_sum = sum if LA < 0 else sum + LC
            lo_sum = sum + LC if LA < 0 else sum
            try:
                hi = ret[(new_linear, hi_sum)]
            except KeyError:
                call_stack.append((new_linear, hi_sum))
                continue

            try:
                lo = ret[(new_linear, lo_sum)]
            except KeyError:
                call_stack.append((new_linear, lo_sum))
                continue

            ret[call_stack.pop()] = self.ITE(abs(LA), hi, lo)

        return ret[first_stack]

    # Reference implementation for testing. The recursion depth gets exceeded
    # for too long formulas, so we use the non-recursive version above.
    @memoize
    def build_BDD_recursive(self, linear, sum=0):
        lower_limit = linear.lo - sum
        upper_limit = linear.hi - sum
        if lower_limit <= 0 and upper_limit >= linear.total:
            return true
        if lower_limit > linear.total or upper_limit < 0:
            return false

        new_linear = linear[:-1]
        LC = linear.LC
        LA = linear.LA
        # This is handled by the abs() call below. I think it's done this way to
        # aid caching.
        hi_sum = sum if LA < 0 else sum + LC
        lo_sum = sum + LC if LA < 0 else sum
        hi = self.build_BDD_recursive(new_linear, hi_sum)
        lo = self.build_BDD_recursive(new_linear, lo_sum)
        ret = self.ITE(abs(LA), hi, lo)

        return ret

    @memoize
    def Cmp(self, a, b):
        """
        Returns [max(a, b), min(a, b)].
        """
        return [self.Or(a, b), self.And(a, b)]

    def odd_even_mergesort(self, A):
        if len(A) == 1:
            return A
        if int(log2(len(A))) != log2(len(A)): # accurate to about 2**48
            raise ValueError("Length of list must be a power of 2 to odd-even merge sort")

        evens = A[::2]
        odds = A[1::2]
        sorted_evens = self.odd_even_mergesort(evens)
        sorted_odds = self.odd_even_mergesort(odds)
        return self.odd_even_merge(sorted_evens, sorted_odds)

    def odd_even_merge(self, A, B):
        if len(A) != len(B):
            raise ValueError("Lists must be of the same length to odd-even merge")
        if len(A) == 1:
            return self.Cmp(A[0], B[0])

        # Guaranteed to have the same length because len(A) is a power of 2
        A_evens = A[::2]
        A_odds = A[1::2]
        B_evens = B[::2]
        B_odds = B[1::2]
        C = self.odd_even_merge(A_evens, B_odds)
        D = self.odd_even_merge(A_odds, B_evens)
        merged = []
        for i, j in zip(C, D):
            merged += self.Cmp(i, j)

        return merged

    def build_sorter(self, linear):
        if not linear:
            return []
        sorter_input = []
        for coeff, atom in linear.equation:
            sorter_input += [atom]*coeff
        next_power_of_2 = 2**ceil(log2(len(sorter_input)))
        sorter_input += [false]*(next_power_of_2 - len(sorter_input))
        return self.odd_even_mergesort(sorter_input)

class Linear(object):
    """
    A (canonicalized) linear constraint

    Canonicalized means all coefficients are positive.
    """
    def __init__(self, equation, rhs, total=None):
        """
        Equation should be a list of tuples of the form (coeff, atom). rhs is
        the number on the right-hand side, or a list [lo, hi].
        """
        self.equation = sorted(equation)
        self.rhs = rhs
        if isinstance(rhs, int):
            self.lo = self.hi = rhs
        else:
            self.lo, self.hi = rhs
        self.total = total or sum([i for i, _ in equation])
        if equation:
            self.LC = self.equation[-1][0]
            self.LA = self.equation[-1][1]
        # self.lower_limit = self.lo - self.total
        # self.upper_limit = self.hi - self.total

    @property
    def coeffs(self):
        if hasattr(self, '_coeffs'):
            return self._coeffs
        self._coeffs = []
        self._atoms = []
        for coeff, atom in self.equation:
            self._coeffs.append(coeff)
            self._atoms.append(atom)
        return self._coeffs

    @property
    def atoms(self):
        if hasattr(self, '_atoms'):
            return self._atoms
        self._coeffs = []
        self._atoms = []
        for coeff, atom in self.equation:
            self._coeffs.append(coeff)
            self._atoms.append(atom)
        return self._atoms

    @property
    def atom2coeff(self):
        return defaultdict(int, {atom: coeff for coeff, atom in self.equation})

    def __call__(self, sol):
        """
        Call a solution to see if it is satisfied
        """
        t = 0
        for s in sol:
            t += self.atom2coeff[s]
        return self.lo <= t <= self.hi

    def __len__(self):
        return len(self.equation)

    def __getitem__(self, key):
        if not isinstance(key, slice):
            raise NotImplementedError("Non-slice indices are not supported")
        if key == slice(None, -1, None):
            total = self.total - self.LC
        else:
            total = None
        return self.__class__(self.equation.__getitem__(key), self.rhs, total=total)

    def __eq__(self, other):
        if not isinstance(other, Linear):
            return False
        return (self.equation == other.equation and self.lo == other.lo and
        self.hi == other.hi)

    @property
    def hashable_equation(self):
        return tuple([tuple([i for i in term]) for term in self.equation])

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash((self.hashable_equation, self.lo, self.hi))
            return self._hash

    def __str__(self):
        return "Linear(%r, %r)" % (self.equation, self.rhs)

    __repr__ = __str__


def generate_constraints(eq, m, rhs, alg='sorter', sorter_cache={}):
    l = Linear(eq, rhs)
    if not l:
        raise StopIteration
    C = Clauses(m)
    if alg == 'BDD':
        yield [C.build_BDD(l)]
    elif alg == 'BDD_recursive':
        yield [C.build_BDD_recursive(l)]
    elif alg == 'sorter':
        if l.hashable_equation in sorter_cache:
            m, C = sorter_cache[l.hashable_equation]
        else:
            m = C.build_sorter(l)
            sorter_cache[l.hashable_equation] = m, C

        if l.rhs[0]:
            # Output must be between lower bound and upper bound, meaning
            # the lower bound of the sorted output must be true and one more
            # than the upper bound should be false.
            yield [m[l.rhs[0]-1]]
            yield [-m[l.rhs[1]]]
        else:
            # The lower bound is zero, which is always true.
            yield [-m[l.rhs[1]]]
    else:
        raise ValueError("alg must be one of 'BDD', 'BDD_recursive', or 'sorter'")

    for clause in C.clauses:
        yield list(clause)

def bisect_constraints(min_rhs, max_rhs, clauses, func, increment=10):
    """
    Bisect the solution space of a constraint, to minimize it.

    func should be a function that is called with the arguments func(lo_rhs,
    hi_rhs) and returns a list of constraints.

    The midpoint of the bisection will not happen more than lo value +
    increment.  To not use it, set a very large increment. The increment
    argument should be used if you expect the optimal solution to be near 0.

    """
    lo, hi = [min_rhs, max_rhs]
    while True:
        mid = min([lo + increment, (lo + hi)//2])
        rhs = [lo, mid]

        dotlog.debug("Building the constraint with rhs: %s" % rhs)
        constraints = func(*rhs)
        if constraints[0] == [false]: # build_BDD returns false if the rhs is
            solutions = []            # too big to be satisfied. XXX: This
            break                     # probably indicates a bug.
        if constraints[0] == [true]:
            constraints = []

        dotlog.debug("Checking for solutions with rhs:  %s" % rhs)
        solutions = sat(clauses + constraints)
        if lo >= hi:
            break
        if solutions:
            if lo == mid:
                break
            # bisect good
            hi = mid
        else:
            # bisect bad
            lo = mid+1
    return constraints

def min_sat(clauses, max_n=1000, N=sys.maxsize):
    """
    Calculate the SAT solutions for the `clauses` for which the number of true
    literals from 1 to N is minimal.  Returned is the list of those solutions.
    When the clauses are unsatisfiable, an empty list is returned.

    This function could be implemented using a Pseudo-Boolean SAT solver,
    which would avoid looping over the SAT solutions, and would therefore
    be much more efficient.  However, for our purpose the current
    implementation is good enough.

    """
    try:
        import pycosat
    except ImportError:
        sys.exit('Error: could not import pycosat (required for dependency '
                 'resolving)')

    min_tl, solutions = sys.maxsize, []
    for sol in islice(pycosat.itersolve(clauses), max_n):
        tl = sum(lit > 0 for lit in sol[:N]) # number of true literals
        if tl < min_tl:
            min_tl, solutions = tl, [sol]
        elif tl == min_tl:
            solutions.append(sol)

    return solutions

def sat(clauses):
    """
    Calculate a SAT solution for `clauses`.

    Returned is the list of those solutions.  When the clauses are
    unsatisfiable, an empty list is returned.

    """
    try:
        import pycosat
    except ImportError:
        sys.exit('Error: could not import pycosat (required for dependency '
                 'resolving)')

    solution = pycosat.solve(clauses)
    if solution == "UNSAT" or solution == "UNKNOWN": # wtf https://github.com/ContinuumIO/pycosat/issues/14
        return []
    return solution

########NEW FILE########
__FILENAME__ = misc
# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import print_function, division, absolute_import

import os
import sys
import shutil
import subprocess
from collections import defaultdict
from distutils.spawn import find_executable
from os.path import (abspath, basename, dirname, expanduser, exists,
                     isdir, isfile, islink, join)

from conda import config
from conda import install
from conda.api import get_index
from conda.plan import (RM_EXTRACTED, EXTRACT, UNLINK, LINK,
                        ensure_linked_actions, execute_actions)
from conda.compat import iteritems



def conda_installed_files(prefix, exclude_self_build=False):
    """
    Return the set of files which have been installed (using conda) into
    a given prefix.
    """
    res = set()
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        if exclude_self_build and 'file_hash' in meta:
            continue
        res.update(set(meta['files']))
    return res


def rel_path(prefix, path):
    res = path[len(prefix) + 1:]
    if sys.platform == 'win32':
        res = res.replace('\\', '/')
    return res


def walk_prefix(prefix, ignore_predefined_files=True):
    """
    Return the set of all files in a given prefix directory.
    """
    res = set()
    prefix = abspath(prefix)
    ignore = {'pkgs', 'envs', 'conda-bld', 'conda-meta', '.conda_lock',
              'users', 'LICENSE.txt', 'info', 'conda-recipes',
              '.index', '.unionfs', '.nonadmin'}
    binignore = {'conda', 'activate', 'deactivate'}
    if sys.platform == 'darwin':
        ignore.update({'python.app', 'Launcher.app'})
    for fn in os.listdir(prefix):
        if ignore_predefined_files:
            if fn in ignore:
                continue
        if isfile(join(prefix, fn)):
            res.add(fn)
            continue
        for root, dirs, files in os.walk(join(prefix, fn)):
            for fn2 in files:
                if ignore_predefined_files:
                    if root == join(prefix, 'bin') and fn2 in binignore:
                        continue
                res.add(rel_path(prefix, join(root, fn2)))
            for dn in dirs:
                path = join(root, dn)
                if islink(path):
                    res.add(rel_path(prefix, path))
    return res


def untracked(prefix, exclude_self_build=False):
    """
    Return (the set) of all untracked files for a given prefix.
    """
    conda_files = conda_installed_files(prefix, exclude_self_build)
    return {path for path in walk_prefix(prefix) - conda_files
            if not (path.endswith('~') or
                     (sys.platform=='darwin' and path.endswith('.DS_Store')) or
                     (path.endswith('.pyc') and path[:-1] in conda_files))}


def which_prefix(path):
    """
    given the path (to a (presumably) conda installed file) return the
    environment prefix in which the file in located
    """
    prefix = abspath(path)
    while True:
        if isdir(join(prefix, 'conda-meta')):
            # we found the it, so let's return it
            return prefix
        if prefix == dirname(prefix):
            # we cannot chop off any more directories, so we didn't find it
            return None
        prefix = dirname(prefix)


def which_package(path):
    """
    given the path (of a (presumably) conda installed file) iterate over
    the conda packages the file came from.  Usually the iteration yields
    only one package.
    """
    path = abspath(path)
    prefix = which_prefix(path)
    if prefix is None:
        raise RuntimeError("could not determine conda prefix from: %s" % path)
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        if any(abspath(join(prefix, f)) == path for f in meta['files']):
            yield dist


def discard_conda(dists):
    return [dist for dist in dists if not install.name_dist(dist) == 'conda']


def touch_nonadmin(prefix):
    """
    Creates $PREFIX/.nonadmin if sys.prefix/.nonadmin exists (on Windows)
    """
    if sys.platform == 'win32' and exists(join(config.root_dir, '.nonadmin')):
        if not isdir(prefix):
            os.makedirs(prefix)
        with open(join(prefix, '.nonadmin'), 'w') as fo:
            fo.write('')


def clone_env(prefix1, prefix2, verbose=True):
    """
    clone existing prefix1 into new prefix2
    """
    untracked_files = untracked(prefix1)
    dists = discard_conda(install.linked(prefix1))
    print('Packages: %d' % len(dists))
    print('Files: %d' % len(untracked_files))

    for f in untracked_files:
        src = join(prefix1, f)
        dst = join(prefix2, f)
        dst_dir = dirname(dst)
        if islink(dst_dir) or isfile(dst_dir):
            os.unlink(dst_dir)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)

        try:
            with open(src, 'rb') as fi:
                data = fi.read()
        except IOError:
            continue

        try:
            s = data.decode('utf-8')
            s = s.replace(prefix1, prefix2)
            data = s.encode('utf-8')
        except UnicodeDecodeError: # data is binary
            pass

        with open(dst, 'wb') as fo:
            fo.write(data)
        shutil.copystat(src, dst)

    actions = ensure_linked_actions(dists, prefix2)
    execute_actions(actions, index=get_index(), verbose=verbose)


def install_local_packages(prefix, paths, verbose=False):
    # copy packages to pkgs dir
    dists = []
    for src_path in paths:
        assert src_path.endswith('.tar.bz2')
        fn = basename(src_path)
        dists.append(fn[:-8])
        dst_path = join(config.pkgs_dirs[0], fn)
        if abspath(src_path) == abspath(dst_path):
            continue
        shutil.copyfile(src_path, dst_path)

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    actions['op_order'] = RM_EXTRACTED, EXTRACT, UNLINK, LINK
    for dist in dists:
        actions[RM_EXTRACTED].append(dist)
        actions[EXTRACT].append(dist)
        if install.is_linked(prefix, dist):
            actions[UNLINK].append(dist)
        actions[LINK].append(dist)
    execute_actions(actions, verbose=verbose)


def launch(fn, prefix=config.root_dir, additional_args=None):
    info = install.is_linked(prefix, fn[:-8])
    if info is None:
        return None

    if not info.get('type') == 'app':
        raise Exception('Not an application: %s' % fn)

    # prepend the bin directory to the path
    fmt = r'%s\Scripts;%s' if sys.platform == 'win32' else '%s/bin:%s'
    env = {'PATH': fmt % (abspath(prefix), os.getenv('PATH'))}
    # copy existing environment variables, but not anything with PATH in it
    for k, v in iteritems(os.environ):
        if 'PATH' not in k:
            env[k] = v
    # allow updating environment variables from metadata
    if 'app_env' in info:
        env.update(info['app_env'])

    # call the entry command
    args = info['app_entry'].split()
    args = [a.replace('${PREFIX}', prefix) for a in args]
    arg0 = find_executable(args[0], env['PATH'])
    if arg0 is None:
        raise Exception('Executable not found: %s' % args[0])
    args[0] = arg0

    cwd = abspath(expanduser('~'))
    if additional_args:
        args.extend(additional_args)
    return subprocess.Popen(args, cwd=cwd , env=env)


if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] DIST/FN [ADDITIONAL ARGS]")
    p.add_option('-p', '--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")
    opts, args = p.parse_args()

    if len(args) == 0:
        p.error('at least one argument expected')

    fn = args[0]
    if not fn.endswith('.tar.bz2'):
        fn += '.tar.bz2'
    p = launch(fn, opts.prefix, args[1:])
    print('PID:', p.pid)

########NEW FILE########
__FILENAME__ = packup
# NOTE:
#     This module is deprecated.  Don't import from this here when writing
#     new code.
from __future__ import print_function, division, absolute_import

import os
import re
import sys
import json
import shutil
import hashlib
import tarfile
import tempfile
from os.path import basename, dirname, isfile, islink, join

import conda.config as config
import conda.install as install
from conda.misc import untracked
from conda.compat import PY3


def get_installed_version(prefix, name):
    for dist in install.linked(prefix):
        n, v, b = dist.rsplit('-', 2)
        if n == name:
            return v
    return None


def remove(prefix, files):
    """
    Remove files for a given prefix.
    """
    dst_dirs = set()
    for f in files:
        dst = join(prefix, f)
        dst_dirs.add(dirname(dst))
        os.unlink(dst)

    for path in sorted(dst_dirs, key=len, reverse=True):
        try:
            os.rmdir(path)
        except OSError: # directory might not be empty
            pass


def create_info(name, version, build_number, requires_py):
    d = dict(
        name = name,
        version = version,
        platform = config.platform,
        arch = config.arch_name,
        build_number = int(build_number),
        build = str(build_number),
        depends = [],
    )
    if requires_py:
        d['build'] = ('py%d%d_' % requires_py) + d['build']
        d['depends'].append('python %d.%d*' % requires_py)
    return d


shebang_pat = re.compile(r'^#!.+$', re.M)
def fix_shebang(tmp_dir, path):
    if open(path, 'rb').read(2) != '#!':
        return False

    with open(path) as fi:
        data = fi.read()
    m = shebang_pat.match(data)
    if not (m and 'python' in m.group()):
        return False

    data = shebang_pat.sub('#!%s/bin/python' % install.prefix_placeholder,
                           data, count=1)
    tmp_path = join(tmp_dir, basename(path))
    with open(tmp_path, 'w') as fo:
        fo.write(data)
    os.chmod(tmp_path, int('755', 8))
    return True


def _add_info_dir(t, tmp_dir, files, has_prefix, info):
    info_dir = join(tmp_dir, 'info')
    os.mkdir(info_dir)
    with open(join(info_dir, 'files'), 'w') as fo:
        for f in files:
            fo.write(f + '\n')

    with open(join(info_dir, 'index.json'), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True)

    if has_prefix:
        with open(join(info_dir, 'has_prefix'), 'w') as fo:
            for f in has_prefix:
                fo.write(f + '\n')

    for fn in os.listdir(info_dir):
        t.add(join(info_dir, fn), 'info/' + fn)


def create_conda_pkg(prefix, files, info, tar_path, update_info=None):
    """
    create a conda package with `files` (in `prefix` and `info` metadata)
    at `tar_path`, and return a list of warning strings
    """
    files = sorted(files)
    warnings = []
    has_prefix = []
    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'w:bz2')
    h = hashlib.new('sha1')
    for f in files:
        assert not (f.startswith('/') or f.endswith('/') or
                    '\\' in f or f == ''), f
        path = join(prefix, f)
        if f.startswith('bin/') and fix_shebang(tmp_dir, path):
            path = join(tmp_dir, basename(path))
            has_prefix.append(f)
        t.add(path, f)
        h.update(f.encode('utf-8'))
        h.update(b'\x00')
        if islink(path):
            link = os.readlink(path)
            if PY3 and isinstance(link, str):
                h.update(bytes(link, 'utf-8'))
            else:
                h.update(link)
            if link.startswith('/'):
                warnings.append('found symlink to absolute path: %s -> %s' %
                                (f, link))
        elif isfile(path):
            h.update(open(path, 'rb').read())
            if path.endswith('.egg-link'):
                warnings.append('found egg link: %s' % f)

    info['file_hash'] = h.hexdigest()
    if update_info:
        update_info(info)
    _add_info_dir(t, tmp_dir, files, has_prefix, info)
    t.close()
    shutil.rmtree(tmp_dir)
    return warnings


def make_tarbz2(prefix, name='unknown', version='0.0', build_number=0,
                files=None):
    if files is None:
        files = untracked(prefix)
    print("# files: %d" % len(files))
    if len(files) == 0:
        print("# failed: nothing to do")
        return None

    if any('/site-packages/' in f for f in files):
        python_version = get_installed_version(prefix, 'python')
        assert python_version is not None
        requires_py = tuple(int(x) for x in python_version[:3].split('.'))
    else:
        requires_py = False

    info = create_info(name, version, build_number, requires_py)
    tarbz2_fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    create_conda_pkg(prefix, files, info, tarbz2_fn)
    print('# success')
    print(tarbz2_fn)
    return tarbz2_fn


if __name__ == '__main__':
    make_tarbz2(sys.prefix)

########NEW FILE########
__FILENAME__ = plan
"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""

from __future__ import print_function, division, absolute_import

import re
import sys
from logging import getLogger
from collections import defaultdict
from os.path import abspath, isfile, join, exists

from conda import config
from conda import install
from conda.fetch import fetch_pkg
from conda.history import History
from conda.resolve import MatchSpec, Resolve
from conda.utils import md5_file, human_bytes

log = getLogger(__name__)

# op codes
FETCH = 'FETCH'
EXTRACT = 'EXTRACT'
UNLINK = 'UNLINK'
LINK = 'LINK'
RM_EXTRACTED = 'RM_EXTRACTED'
RM_FETCHED = 'RM_FETCHED'
PREFIX = 'PREFIX'
PRINT = 'PRINT'
PROGRESS = 'PROGRESS'
SYMLINK_CONDA = 'SYMLINK_CONDA'

progress_cmds = set([EXTRACT, RM_EXTRACTED, LINK, UNLINK])

def print_dists(dists_extras):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for dist, extra in dists_extras:
        line = fmt % tuple(dist.rsplit('-', 1))
        if extra:
            line += extra
        print(line)

def split_linkarg(arg):
    "Return tuple(dist, pkgs_dir, linktype)"
    pat = re.compile(r'\s*(\S+)(?:\s+(.+?)\s+(\d+))?\s*$')
    m = pat.match(arg)
    dist, pkgs_dir, linktype = m.groups()
    if pkgs_dir is None:
        pkgs_dir = config.pkgs_dirs[0]
    if linktype is None:
        linktype = install.LINK_HARD
    return dist, pkgs_dir, int(linktype)

def display_actions(actions, index=None):
    if actions.get(FETCH):
        print("\nThe following packages will be downloaded:\n")

        disp_lst = []
        for dist in actions[FETCH]:
            info = index[dist + '.tar.bz2']
            extra = '%15s' % human_bytes(info['size'])
            if config.show_channel_urls:
                extra += '  %s' % config.canonical_channel_name(
                                       info.get('channel'))
            disp_lst.append((dist, extra))
        print_dists(disp_lst)

        if index and len(actions[FETCH]) > 1:
            print(' ' * 4 + '-' * 60)
            print(" " * 43 + "Total: %14s" %
                  human_bytes(sum(index[dist + '.tar.bz2']['size']
                                  for dist in actions[FETCH])))
    if actions.get(UNLINK):
        print("\nThe following packages will be UN-linked:\n")
        print_dists([
                (dist, None)
                for dist in actions[UNLINK]])
    if actions.get(LINK):
        print("\nThe following packages will be linked:\n")
        lst = []
        for arg in actions[LINK]:
            dist, pkgs_dir, lt = split_linkarg(arg)
            extra = '   %s' % install.link_name_map.get(lt)
            lst.append((dist, extra))
        print_dists(lst)
    print()

# the order matters here, don't change it
action_codes = FETCH, EXTRACT, UNLINK, LINK, SYMLINK_CONDA, RM_EXTRACTED, RM_FETCHED

def nothing_to_do(actions):
    for op in action_codes:
        if actions.get(op):
            return False
    return True

def plan_from_actions(actions):
    if 'op_order' in actions and actions['op_order']:
        op_order = actions['op_order']
    else:
        op_order = action_codes

    assert PREFIX in actions and actions[PREFIX]
    res = ['# plan',
           'PREFIX %s' % actions[PREFIX]]
    for op in op_order:
        if op not in actions:
            continue
        if not actions[op]:
            continue
        if '_' not in op:
            res.append('PRINT %sing packages ...' % op.capitalize())
        if op in progress_cmds:
            res.append('PROGRESS %d' % len(actions[op]))
        for arg in actions[op]:
            res.append('%s %s' % (op, arg))
    return res

def extracted_where(dist):
    for pkgs_dir in config.pkgs_dirs:
        if install.is_extracted(pkgs_dir, dist):
            return pkgs_dir
    return None

def ensure_linked_actions(dists, prefix):
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    for dist in dists:
        if install.is_linked(prefix, dist):
            continue

        extracted_in = extracted_where(dist)
        if extracted_in:
            if install.try_hard_link(extracted_in, prefix, dist):
                lt = install.LINK_HARD
            else:
                lt = (install.LINK_SOFT if (config.allow_softlinks and
                                            sys.platform != 'win32') else
                      install.LINK_COPY)
            actions[LINK].append('%s %s %d' % (dist, extracted_in, lt))
            continue

        actions[LINK].append(dist)
        actions[EXTRACT].append(dist)
        if install.is_fetched(config.pkgs_dirs[0], dist):
            continue
        actions[FETCH].append(dist)
    return actions

def force_linked_actions(dists, index, prefix):
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    actions['op_order'] = (RM_FETCHED, FETCH, RM_EXTRACTED, EXTRACT,
                           UNLINK, LINK)
    for dist in dists:
        fn = dist + '.tar.bz2'
        pkg_path = join(config.pkgs_dirs[0], fn)
        if isfile(pkg_path):
            try:
                if md5_file(pkg_path) != index[fn]['md5']:
                    actions[RM_FETCHED].append(dist)
                    actions[FETCH].append(dist)
            except KeyError:
                sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)
        else:
            actions[FETCH].append(dist)
        actions[RM_EXTRACTED].append(dist)
        actions[EXTRACT].append(dist)
        if isfile(join(prefix, 'conda-meta', dist + '.json')):
            actions[UNLINK].append(dist)
        actions[LINK].append(dist)
    return actions

# -------------------------------------------------------------------

def is_root_prefix(prefix):
    return abspath(prefix) == abspath(config.root_dir)

def dist2spec3v(dist):
    name, version, unused_build = dist.rsplit('-', 2)
    return '%s %s*' % (name, version[:3])

def add_defaults_to_specs(r, linked, specs):
    # TODO: This should use the pinning mechanism. But don't change the API:
    # cas uses it.
    if r.explicit(specs):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {install.name_dist(dist): dist for dist in linked}
    names_ms = {MatchSpec(s).name: MatchSpec(s) for s in specs}

    for name, def_ver in [('python', config.default_python),]:
                         #('numpy', config.default_numpy)]:
        ms = names_ms.get(name)
        if ms and ms.strictness > 1:
            # if any of the specifications mention the Python/Numpy version,
            # we don't need to add the default spec
            log.debug('H1 %s' % name)
            continue

        any_depends_on = any(ms2.name == name
                             for spec in specs
                             for fn in r.get_max_dists(MatchSpec(spec))
                             for ms2 in r.ms_depends(fn))
        log.debug('H2 %s %s' % (name, any_depends_on))

        if not any_depends_on and name not in names_ms:
            # if nothing depends on Python/Numpy AND the Python/Numpy is not
            # specified, we don't need to add the default spec
            log.debug('H2A %s' % name)
            continue

        if (any_depends_on and len(specs) >= 1 and
                  MatchSpec(specs[0]).strictness == 3):
            # if something depends on Python/Numpy, but the spec is very
            # explicit, we also don't need to add the default spec
            log.debug('H2B %s' % name)
            continue

        if name in names_linked:
            # if Python/Numpy is already linked, we add that instead of the
            # default
            log.debug('H3 %s' % name)
            specs.append(dist2spec3v(names_linked[name]))
            continue

        if (name, def_ver) in [('python', '3.3'), ('python', '3.4')]:
            # Don't include Python 3 in the specs if this is the Python 3
            # version of conda.
            continue

        specs.append('%s %s*' % (name, def_ver))
    log.debug('HF specs=%r' % specs)

def get_pinned_specs(prefix):
    pinfile = join(prefix, 'conda-meta', 'pinned')
    if not exists(pinfile):
        return []
    with open(pinfile) as f:
        return list(filter(len, f.read().strip().split('\n')))

def install_actions(prefix, index, specs, force=False, only_names=None, pinned=True, minimal_hint=False):
    r = Resolve(index)
    linked = install.linked(prefix)

    if config.self_update and is_root_prefix(prefix):
        specs.append('conda')
    add_defaults_to_specs(r, linked, specs)
    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        specs += pinned_specs
        # TODO: Improve error messages here

    must_have = {}
    for fn in r.solve(specs, [d + '.tar.bz2' for d in linked],
                      config.track_features, minimal_hint=minimal_hint):
        dist = fn[:-8]
        name = install.name_dist(dist)
        if only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix):
        if install.on_win:
            for name in install.win_ignore_root:
                if name in must_have:
                    del must_have[name]
        for name in config.foreign:
            if name in must_have:
                del must_have[name]
    else:
        # discard conda from other environments
        if 'conda' in must_have:
            sys.exit("Error: 'conda' can only be installed into "
                     "root environment")

    smh = sorted(must_have.values())
    if force:
        actions = force_linked_actions(smh, index, prefix)
    else:
        actions = ensure_linked_actions(smh, prefix)

    if actions[LINK] and sys.platform != 'win32':
        actions[SYMLINK_CONDA] = [config.root_dir]

    for dist in sorted(linked):
        name = install.name_dist(dist)
        if name in must_have and dist != must_have[name]:
            actions[UNLINK].append(dist)

    return actions


def remove_actions(prefix, specs, pinned=True):
    linked = install.linked(prefix)

    mss = [MatchSpec(spec) for spec in specs]

    pinned_specs = get_pinned_specs(prefix)

    actions = defaultdict(list)
    actions[PREFIX] = prefix
    for dist in sorted(linked):
        if any(ms.match('%s.tar.bz2' % dist) for ms in mss):
            if pinned and any(MatchSpec(spec).match('%s.tar.bz2' % dist) for spec in
    pinned_specs):
                raise RuntimeError("Cannot remove %s because it is pinned. Use --no-pin to override." % dist)
            actions[UNLINK].append(dist)

    return actions


def remove_features_actions(prefix, index, features):
    linked = install.linked(prefix)
    r = Resolve(index)

    actions = defaultdict(list)
    actions[PREFIX] = prefix
    _linked = [d + '.tar.bz2' for d in linked]
    to_link = []
    for dist in sorted(linked):
        fn = dist + '.tar.bz2'
        if fn not in index:
            continue
        if r.track_features(fn).intersection(features):
            actions[UNLINK].append(dist)
        if r.features(fn).intersection(features):
            actions[UNLINK].append(dist)
            subst = r.find_substitute(_linked, features, fn)
            if subst:
                to_link.append(subst[:-8])

    if to_link:
        actions.update(ensure_linked_actions(to_link, prefix))
    return actions


def revert_actions(prefix, revision=-1):
    h = History(prefix)
    h.update()
    try:
        state = h.get_state(revision)
    except IndexError:
        sys.exit("Error: no such revision: %d" % revision)

    curr = h.get_state()
    if state == curr:
        return {}

    actions = ensure_linked_actions(state, prefix)
    for dist in curr - state:
        actions[UNLINK].append(dist)

    return actions

# ---------------------------- EXECUTION --------------------------

def fetch(index, dist):
    assert index is not None
    fn = dist + '.tar.bz2'
    fetch_pkg(index[fn])

def link(prefix, arg, index=None):
    dist, pkgs_dir, lt = split_linkarg(arg)
    install.link(pkgs_dir, prefix, dist, lt, index=index)

def cmds_from_plan(plan):
    res = []
    for line in plan:
        log.debug(' %s' % line)
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        res.append(line.split(None, 1))
    return res

def execute_plan(plan, index=None, verbose=False):
    if verbose:
        from conda.console import setup_verbose_handlers
        setup_verbose_handlers()

    # set default prefix
    prefix = config.root_dir
    i = None
    cmds = cmds_from_plan(plan)

    for cmd, arg in cmds:
        if i is not None and cmd in progress_cmds:
            i += 1
            getLogger('progress.update').info((install.name_dist(arg), i))

        if cmd == PREFIX:
            prefix = arg
        elif cmd == PRINT:
            getLogger('print').info(arg)
        elif cmd == FETCH:
            fetch(index, arg)
        elif cmd == PROGRESS:
            i = 0
            maxval = int(arg)
            getLogger('progress.start').info(maxval)
        elif cmd == EXTRACT:
            install.extract(config.pkgs_dirs[0], arg)
        elif cmd == RM_EXTRACTED:
            install.rm_extracted(config.pkgs_dirs[0], arg)
        elif cmd == RM_FETCHED:
            install.rm_fetched(config.pkgs_dirs[0], arg)
        elif cmd == LINK:
            link(prefix, arg, index=index)
        elif cmd == UNLINK:
            install.unlink(prefix, arg)
        elif cmd == SYMLINK_CONDA:
            install.symlink_conda(prefix, arg)
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if i is not None and cmd in progress_cmds and maxval == i:
            i = None
            getLogger('progress.stop').info(None)

    install.messages(prefix)


def execute_actions(actions, index=None, verbose=False):
    plan = plan_from_actions(actions)
    with History(actions[PREFIX]):
        execute_plan(plan, index, verbose)


if __name__ == '__main__':
    # for testing new revert_actions() only
    from pprint import pprint
    pprint(dict(revert_actions(sys.prefix, int(sys.argv[1]))))

########NEW FILE########
__FILENAME__ = compat
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''Compatability methods and classes for the progressbar module'''


# Python 3.x (and backports) use a modified iterator syntax
# This will allow 2.x to behave with 3.x iterators
if not hasattr(__builtins__, 'next'):
    def next(iter):
        try:
            # Try new style iterators
            return iter.__next__()
        except AttributeError:
            # Fallback in case of a "native" iterator
            return iter.next()


# Python < 2.5 does not have "any"
if not hasattr(__builtins__, 'any'):
   def any(iterator):
      for item in iterator:
         if item: return True

      return False

########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''Default ProgressBar widgets'''

from __future__ import print_function, division, absolute_import

import datetime
import math

try:
    from abc import ABCMeta, abstractmethod
    abstractmethod; # silence pyflakes
except ImportError:
    AbstractWidget = object
    abstractmethod = lambda fn: fn
else:
    AbstractWidget = ABCMeta('AbstractWidget', (object,), {})


def format_updatable(updatable, pbar):
    if hasattr(updatable, 'update'): return updatable.update(pbar)
    else: return updatable


class Widget(AbstractWidget):
    '''The base class for all widgets

    The ProgressBar will call the widget's update value when the widget should
    be updated. The widget's size may change between calls, but the widget may
    display incorrectly if the size changes drastically and repeatedly.

    The boolean TIME_SENSITIVE informs the ProgressBar that it should be
    updated more often because it is time sensitive.
    '''

    TIME_SENSITIVE = False
    __slots__ = ()

    @abstractmethod
    def update(self, pbar):
        '''Updates the widget.

        pbar - a reference to the calling ProgressBar
        '''


class WidgetHFill(Widget):
    '''The base class for all variable width widgets.

    This widget is much like the \\hfill command in TeX, it will expand to
    fill the line. You can use more than one in the same line, and they will
    all have the same width, and together will fill the line.
    '''

    @abstractmethod
    def update(self, pbar, width):
        '''Updates the widget providing the total width the widget must fill.

        pbar - a reference to the calling ProgressBar
        width - The total width the widget must fill
        '''


class Timer(Widget):
    'Widget which displays the elapsed seconds.'

    __slots__ = ('format',)
    TIME_SENSITIVE = True

    def __init__(self, format='Elapsed Time: %s'):
        self.format = format

    @staticmethod
    def format_time(seconds):
        'Formats time as the string "HH:MM:SS".'

        return str(datetime.timedelta(seconds=int(seconds)))


    def update(self, pbar):
        'Updates the widget to show the elapsed time.'

        return self.format % self.format_time(pbar.seconds_elapsed)


class ETA(Timer):
    'Widget which attempts to estimate the time of arrival.'

    TIME_SENSITIVE = True

    def update(self, pbar):
        'Updates the widget to show the ETA or total time when finished.'

        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)


class FileTransferSpeed(Widget):
    'Widget for showing the transfer speed (useful for file transfers).'

    prefixes = ' kMGTPEZY'
    __slots__ = ('unit', 'format')

    def __init__(self, unit='B'):
        self.unit = unit
        self.format = '%6.2f %s%s/s'

    def update(self, pbar):
        'Updates the widget with the current SI prefixed speed.'

        if pbar.seconds_elapsed < 2e-6 or pbar.currval < 2e-6: # =~ 0
            scaled = power = 0
        else:
            speed = pbar.currval / pbar.seconds_elapsed
            power = int(math.log(speed, 1000))
            scaled = speed / 1000.**power

        return self.format % (scaled, self.prefixes[power], self.unit)


class AnimatedMarker(Widget):
    '''An animated marker for the progress bar which defaults to appear as if
    it were rotating.
    '''

    __slots__ = ('markers', 'curmark')

    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1

    def update(self, pbar):
        '''Updates the widget to show the next marker or the first marker when
        finished'''

        if pbar.finished: return self.markers[0]

        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]

# Alias for backwards compatibility
RotatingMarker = AnimatedMarker


class Counter(Widget):
    'Displays the current count'

    __slots__ = ('format',)

    def __init__(self, format='%d'):
        self.format = format

    def update(self, pbar):
        return self.format % pbar.currval


class Percentage(Widget):
    'Displays the current percentage as a number with a percent sign.'

    def update(self, pbar):
        return '%3d%%' % pbar.percentage()


class FormatLabel(Timer):
    'Displays a formatted label'

    mapping = {
        'elapsed': ('seconds_elapsed', Timer.format_time),
        'finished': ('finished', None),
        'last_update': ('last_update_time', None),
        'max': ('maxval', None),
        'seconds': ('seconds_elapsed', None),
        'start': ('start_time', None),
        'value': ('currval', None)
    }

    __slots__ = ('format',)
    def __init__(self, format):
        self.format = format

    def update(self, pbar):
        context = {}
        for name, (key, transform) in self.mapping.items():
            try:
                value = getattr(pbar, key)

                if transform is None:
                   context[name] = value
                else:
                   context[name] = transform(value)
            except: pass

        return self.format % context


class SimpleProgress(Widget):
    'Returns progress as a count of the total (e.g.: "5 of 47")'

    __slots__ = ('sep',)

    def __init__(self, sep=' of '):
        self.sep = sep

    def update(self, pbar):
        return '%d%s%d' % (pbar.currval, self.sep, pbar.maxval)


class Bar(WidgetHFill):
    'A progress bar which stretches to fill the line.'

    __slots__ = ('marker', 'left', 'right', 'fill', 'fill_left')

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=True):
        '''Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        self.marker = marker
        self.left = left
        self.right = right
        self.fill = fill
        self.fill_left = fill_left


    def update(self, pbar, width):
        'Updates the progress bar and its subcomponents'

        left, marker, right = (format_updatable(i, pbar) for i in
                               (self.left, self.marker, self.right))

        width -= len(left) + len(right)
        # Marker must *always* have length of 1
        marker *= int(pbar.currval / pbar.maxval * width)

        if self.fill_left:
            return '%s%s%s' % (left, marker.ljust(width, self.fill), right)
        else:
            return '%s%s%s' % (left, marker.rjust(width, self.fill), right)


class ReverseBar(Bar):
    'A bar which has a marker which bounces from side to side.'

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=False):
        '''Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        self.marker = marker
        self.left = left
        self.right = right
        self.fill = fill
        self.fill_left = fill_left


class BouncingBar(Bar):
    def update(self, pbar, width):
        'Updates the progress bar and its subcomponents'

        left, marker, right = (format_updatable(i, pbar) for i in
                               (self.left, self.marker, self.right))

        width -= len(left) + len(right)

        if pbar.finished: return '%s%s%s' % (left, width * marker, right)

        position = int(pbar.currval % (width * 2 - 1))
        if position > width: position = width * 2 - position
        lpad = self.fill * (position - 1)
        rpad = self.fill * (width - len(marker) - len(lpad))

        # Swap if we want to bounce the other way
        if not self.fill_left: rpad, lpad = lpad, rpad

        return '%s%s%s%s%s' % (left, lpad, marker, rpad, right)

########NEW FILE########
__FILENAME__ = resolve
from __future__ import print_function, division, absolute_import

import re
import sys
import logging
from itertools import combinations
from collections import defaultdict

from conda import verlib
from conda.utils import memoize
from conda.compat import itervalues, iteritems
from conda.logic import (false, true, sat, min_sat, generate_constraints,
                         bisect_constraints)
from conda.console import setup_handlers

log = logging.getLogger(__name__)
dotlog = logging.getLogger('dotupdate')
stdoutlog = logging.getLogger('stdoutlog')
stderrlog = logging.getLogger('stderrlog')
setup_handlers()


def normalized_version(version):
    version = version.replace('rc', '.dev99999')
    if version.endswith('.dev'):
        version += '0'
    try:
        return verlib.NormalizedVersion(version)
    except verlib.IrrationalVersionError:
        return version


class NoPackagesFound(RuntimeError):
    def __init__(self, msg, pkgs):
        super(NoPackagesFound, self).__init__(msg)
        self.pkgs = pkgs

const_pat = re.compile(r'([=<>!]{1,2})(\S+)$')
def ver_eval(version, constraint):
    """
    return the Boolean result of a comparison between two versions, where the
    second argument includes the comparison operator.  For example,
    ver_eval('1.2', '>=1.1') will return True.
    """
    a = version
    m = const_pat.match(constraint)
    if m is None:
        raise RuntimeError("Did not recognize version specification: %r" %
                           constraint)
    op, b = m.groups()
    na = normalized_version(a)
    nb = normalized_version(b)
    if op == '==':
        try:
            return na == nb
        except TypeError:
            return a == b
    elif op == '>=':
        try:
            return na >= nb
        except TypeError:
            return a >= b
    elif op == '<=':
        try:
            return na <= nb
        except TypeError:
            return a <= b
    elif op == '>':
        try:
            return na > nb
        except TypeError:
            return a > b
    elif op == '<':
        try:
            return na < nb
        except TypeError:
            return a < b
    elif op == '!=':
        try:
            return na != nb
        except TypeError:
            return a != b
    else:
        raise RuntimeError("Did not recognize version comparison operator: %r" %
                           constraint)


class VersionSpec(object):

    def __init__(self, spec):
        assert '|' not in spec
        if spec.startswith(('=', '<', '>', '!')):
            self.regex = False
            self.constraints = spec.split(',')
        else:
            self.regex = True
            rx = spec.replace('.', r'\.')
            rx = rx.replace('*', r'.*')
            rx = r'(%s)$' % rx
            self.pat = re.compile(rx)

    def match(self, version):
        if self.regex:
            return bool(self.pat.match(version))
        else:
            return all(ver_eval(version, c) for c in self.constraints)


class MatchSpec(object):

    def __init__(self, spec):
        self.spec = spec
        parts = spec.split()
        self.strictness = len(parts)
        assert 1 <= self.strictness <= 3, repr(spec)
        self.name = parts[0]
        if self.strictness == 2:
            self.vspecs = [VersionSpec(s) for s in parts[1].split('|')]
        elif self.strictness == 3:
            self.ver_build = tuple(parts[1:3])

    def match(self, fn):
        assert fn.endswith('.tar.bz2')
        name, version, build = fn[:-8].rsplit('-', 2)
        if name != self.name:
            return False
        if self.strictness == 1:
            return True
        elif self.strictness == 2:
            return any(vs.match(version) for vs in self.vspecs)
        elif self.strictness == 3:
            return bool((version, build) == self.ver_build)

    def to_filename(self):
        if self.strictness == 3:
            return self.name + '-%s-%s.tar.bz2' % self.ver_build
        else:
            return None

    def __eq__(self, other):
        return self.spec == other.spec

    def __hash__(self):
        return hash(self.spec)

    def __repr__(self):
        return 'MatchSpec(%r)' % (self.spec)

    def __str__(self):
        return self.spec


class Package(object):
    """
    The only purpose of this class is to provide package objects which
    are sortable.
    """
    def __init__(self, fn, info):
        self.fn = fn
        self.name = info['name']
        self.version = info['version']
        self.build_number = info['build_number']
        self.build = info['build']
        self.channel = info.get('channel')
        self.norm_version = normalized_version(self.version)

    # http://python3porting.com/problems.html#unorderable-types-cmp-and-cmp
#     def __cmp__(self, other):
#         if self.name != other.name:
#             raise ValueError('cannot compare packages with different '
#                              'names: %r %r' % (self.fn, other.fn))
#         try:
#             return cmp((self.norm_version, self.build_number),
#                       (other.norm_version, other.build_number))
#         except TypeError:
#             return cmp((self.version, self.build_number),
#                       (other.version, other.build_number))

    def __lt__(self, other):
        if self.name != other.name:
            raise TypeError('cannot compare packages with different '
                             'names: %r %r' % (self.fn, other.fn))
        try:
            return ((self.norm_version, self.build_number, other.build) <
                    (other.norm_version, other.build_number, self.build))
        except TypeError:
            return ((self.version, self.build_number) <
                    (other.version, other.build_number))

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        if self.name != other.name:
            return False
        try:
            return ((self.norm_version, self.build_number, self.build) ==
                    (other.norm_version, other.build_number, other.build))
        except TypeError:
            return ((self.version, self.build_number, self.build) ==
                    (other.version, other.build_number, other.build))

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def __repr__(self):
        return '<Package %s>' % self.fn


class Resolve(object):

    def __init__(self, index):
        self.index = index
        self.groups = defaultdict(list) # map name to list of filenames
        for fn, info in iteritems(index):
            self.groups[info['name']].append(fn)
        self.msd_cache = {}

    def find_matches(self, ms):
        for fn in sorted(self.groups[ms.name]):
            if ms.match(fn):
                yield fn

    def ms_depends(self, fn):
        # the reason we don't use @memoize here is to allow resetting the
        # cache using self.msd_cache = {}, which is used during testing
        try:
            res = self.msd_cache[fn]
        except KeyError:
            if not 'depends' in self.index[fn]:
                raise NoPackagesFound('Bad metadata for %s' % fn, [fn])
            depends = self.index[fn]['depends']
            res = self.msd_cache[fn] = [MatchSpec(d) for d in depends]
        return res

    @memoize
    def features(self, fn):
        return set(self.index[fn].get('features', '').split())

    @memoize
    def track_features(self, fn):
        return set(self.index[fn].get('track_features', '').split())

    @memoize
    def get_pkgs(self, ms, max_only=False):
        pkgs = [Package(fn, self.index[fn]) for fn in self.find_matches(ms)]
        if not pkgs:
            raise NoPackagesFound("No packages found matching: %s" % ms, [ms.spec])
        if max_only:
            maxpkg = max(pkgs)
            ret = []
            for pkg in pkgs:
                try:
                    if (pkg.name, pkg.norm_version, pkg.build_number) ==\
                       (maxpkg.name, maxpkg.norm_version, maxpkg.build_number):
                        ret.append(pkg)
                except TypeError:
                    # They are not equal
                    pass
            return ret

        return pkgs

    def get_max_dists(self, ms):
        pkgs = self.get_pkgs(ms, max_only=True)
        if not pkgs:
            raise NoPackagesFound("No packages found matching: %s" % ms, [ms.spec])
        for pkg in pkgs:
            yield pkg.fn

    def all_deps(self, root_fn, max_only=False):
        res = {}

        def add_dependents(fn1, max_only=False):
            for ms in self.ms_depends(fn1):
                found = False
                notfound = []
                for pkg2 in self.get_pkgs(ms, max_only=max_only):
                    if pkg2.fn in res:
                        found = True
                        continue
                    res[pkg2.fn] = pkg2
                    try:
                        if ms.strictness < 3:
                            add_dependents(pkg2.fn, max_only=max_only)
                    except NoPackagesFound as e:
                        for pkg in e.pkgs:
                            if pkg not in notfound:
                                notfound.append(pkg)
                        if pkg2.fn in res:
                            del res[pkg2.fn]
                    else:
                        found = True

                if not found:
                    raise NoPackagesFound("Could not find some dependencies "
                        "for %s: %s" % (ms, ', '.join(notfound)), notfound)

        add_dependents(root_fn, max_only=max_only)
        return res

    def gen_clauses(self, v, dists, specs, features):
        groups = defaultdict(list) # map name to list of filenames
        for fn in dists:
            groups[self.index[fn]['name']].append(fn)

        for filenames in itervalues(groups):
            # ensure packages with the same name conflict
            for fn1 in filenames:
                v1 = v[fn1]
                for fn2 in filenames:
                    v2 = v[fn2]
                    if v1 < v2:
                        # NOT (fn1 AND fn2)
                        # e.g. NOT (numpy-1.6 AND numpy-1.7)
                        yield [-v1, -v2]

        for fn1 in dists:
            for ms in self.ms_depends(fn1):
                # ensure dependencies are installed
                # e.g. numpy-1.7 IMPLIES (python-2.7.3 OR python-2.7.4 OR ...)
                clause = [-v[fn1]]
                for fn2 in self.find_matches(ms):
                    if fn2 in dists:
                        clause.append(v[fn2])
                assert len(clause) > 1, '%s %r' % (fn1, ms)
                yield clause

                for feat in features:
                    # ensure that a package (with required name) which has
                    # the feature is installed
                    # e.g. numpy-1.7 IMPLIES (numpy-1.8[mkl] OR numpy-1.7[mkl])
                    clause = [-v[fn1]]
                    for fn2 in groups[ms.name]:
                         if feat in self.features(fn2):
                             clause.append(v[fn2])
                    if len(clause) > 1:
                        yield clause

        for spec in specs:
            ms = MatchSpec(spec)
            # ensure that a matching package with the feature is installed
            for feat in features:
                # numpy-1.7[mkl] OR numpy-1.8[mkl]
                clause = [v[fn] for fn in self.find_matches(ms)
                          if fn in dists and feat in self.features(fn)]
                if len(clause) > 0:
                    yield clause

            # Don't install any package that has a feature that wasn't requested.
            for fn in self.find_matches(ms):
                if fn in dists and self.features(fn) - features:
                    yield [-v[fn]]

            # finally, ensure a matching package itself is installed
            # numpy-1.7-py27 OR numpy-1.7-py26 OR numpy-1.7-py33 OR
            # numpy-1.7-py27[mkl] OR ...
            clause = [v[fn] for fn in self.find_matches(ms)
                      if fn in dists]
            assert len(clause) >= 1, ms
            yield clause

    def generate_version_eq(self, v, dists, include0=False):
        groups = defaultdict(list) # map name to list of filenames
        for fn in sorted(dists):
            groups[self.index[fn]['name']].append(fn)

        eq = []
        max_rhs = 0
        for filenames in sorted(itervalues(groups)):
            pkgs = sorted(filenames, key=lambda i: dists[i], reverse=True)
            i = 0
            prev = pkgs[0]
            for pkg in pkgs:
                try:
                    if (dists[pkg].name, dists[pkg].norm_version,
                        dists[pkg].build_number) != (dists[prev].name,
                            dists[prev].norm_version, dists[prev].build_number):
                        i += 1
                except TypeError:
                    i += 1
                if i or include0:
                    eq += [(i, v[pkg])]
                prev = pkg
            max_rhs += i

        return eq, max_rhs

    def get_dists(self, specs, max_only=False):
        dists = {}
        for spec in specs:
            found = False
            notfound = []
            for pkg in self.get_pkgs(MatchSpec(spec), max_only=max_only):
                if pkg.fn in dists:
                    found = True
                    continue
                try:
                    dists.update(self.all_deps(pkg.fn, max_only=max_only))
                except NoPackagesFound as e:
                    # Ignore any package that has nonexisting dependencies.
                    for pkg in e.pkgs:
                        if pkg not in notfound:
                            notfound.append(pkg)
                else:
                    dists[pkg.fn] = pkg
                    found = True
            if not found:
                raise NoPackagesFound("Could not find some dependencies for %s: %s" % (spec, ', '.join(notfound)), notfound)

        return dists

    def solve2(self, specs, features, guess=True, alg='sorter',
        returnall=False, minimal_hint=False, unsat_only=False):
        log.debug("Solving for %s" % str(specs))

        # First try doing it the "old way", i.e., just look at the most recent
        # version of each package from the specs. This doesn't handle the more
        # complicated cases that the pseudo-boolean solver does, but it's also
        # much faster when it does work.

        try:
            dists = self.get_dists(specs, max_only=True)
        except NoPackagesFound:
            # Handle packages that are not included because some dependencies
            # couldn't be found.
            pass
        else:
            v = {} # map fn to variable number
            w = {} # map variable number to fn
            i = -1 # in case the loop doesn't run
            for i, fn in enumerate(sorted(dists)):
                v[fn] = i + 1
                w[i + 1] = fn
            m = i + 1

            dotlog.debug("Solving using max dists only")
            clauses = self.gen_clauses(v, dists, specs, features)
            solutions = min_sat(clauses)


            if len(solutions) == 1:
                ret = [w[lit] for lit in solutions.pop(0) if 0 < lit]
                if returnall:
                    return [ret]
                return ret

        dists = self.get_dists(specs)

        v = {} # map fn to variable number
        w = {} # map variable number to fn
        i = -1 # in case the loop doesn't run
        for i, fn in enumerate(sorted(dists)):
            v[fn] = i + 1
            w[i + 1] = fn
        m = i + 1

        clauses = list(self.gen_clauses(v, dists, specs, features))
        if not clauses:
            if returnall:
                return [[]]
            return []
        eq, max_rhs = self.generate_version_eq(v, dists)


        # Second common case, check if it's unsatisfiable
        dotlog.debug("Checking for unsatisfiability")
        solution = sat(clauses)

        if not solution:
            if guess:
                stderrlog.info('\nError: Unsatisfiable package '
                    'specifications.\nGenerating hint: ')
                if minimal_hint:
                    sys.exit(self.minimal_unsatisfiable_subset(clauses, v,
            w))
                else:
                    sys.exit(self.guess_bad_solve(specs, features))
            raise RuntimeError("Unsatisfiable package specifications")

        if unsat_only:
            return True

        def version_constraints(lo, hi):
            return list(generate_constraints(eq, m, [lo, hi], alg=alg))

        log.debug("Bisecting the version constraint")
        constraints = bisect_constraints(0, max_rhs, clauses, version_constraints)

        dotlog.debug("Finding the minimal solution")
        solutions = min_sat(clauses + constraints, N=m+1)
        assert solutions, (specs, features)

        if len(solutions) > 1:
            print('Warning:', len(solutions), "possible package resolutions:")
            for sol in solutions:
                print('\t', [w[lit] for lit in sol if 0 < lit <= m])

        if returnall:
            return [[w[lit] for lit in sol if 0 < lit <= m] for sol in solutions]
        return [w[lit] for lit in solutions.pop(0) if 0 < lit <= m]


    def minimal_unsatisfiable_subset(self, clauses, v, w):
        while True:
            for i in combinations(clauses, len(clauses) - 1):
                if not sat(list(i)):
                    sys.stdout.write('.');sys.stdout.flush()
                    clauses = i
                    break
            else:
                break
        import pprint
        print()
        print("The following set of clauses is unsatisfiable")
        pprint.pprint([[w[j] if j > 0 else 'not ' + w[-j] for j in k] for k in i])

    def guess_bad_solve(self, specs, features):
        # TODO: Check features as well
        hint = []
        # Try to find the largest satisfiable subset
        found = False
        for i in range(len(specs), 0, -1):
            if found:
                break
            for comb in combinations(specs, i):
                try:
                    self.solve2(comb, features, guess=False, unsat_only=True)
                except RuntimeError:
                    pass
                else:
                    rem = set(specs) - set(comb)
                    rem.discard('conda')
                    if len(rem) == 1:
                        hint.append("%s" % rem.pop())
                    else:
                        hint.append("%s" % ' and '.join(rem))

                    found = True
        if not hint:
            return ''
        if len(hint) == 1:
            return ("\nHint: %s has a conflict with the remaining packages" %
                    hint[0])
        return ("""
Hint: the following combinations of packages create a conflict with the
remaining packages:
  - %s""" % '\n  - '.join(hint))

    def explicit(self, specs):
        """
        Given the specifications, return:
          A. if one explicit specification (strictness=3) is given, and
             all dependencies of this package are explicit as well ->
             return the filenames of those dependencies (as well as the
             explicit specification)
          B. if not one explicit specifications are given ->
             return the filenames of those (not thier dependencies)
          C. None in all other cases
        """
        if len(specs) == 1:
            ms = MatchSpec(specs[0])
            fn = ms.to_filename()
            if fn is None:
                return None
            res = [ms2.to_filename() for ms2 in self.ms_depends(fn)]
            res.append(fn)
        else:
            res = [MatchSpec(spec).to_filename() for spec in specs
                   if spec != 'conda']

        if None in res:
            return None
        res.sort()
        log.debug('explicit(%r) finished' % specs)
        return res

    @memoize
    def sum_matches(self, fn1, fn2):
        return sum(ms.match(fn2) for ms in self.ms_depends(fn1))

    def find_substitute(self, installed, features, fn, max_only=False):
        """
        Find a substitute package for `fn` (given `installed` packages)
        which does *NOT* have `features`.  If found, the substitute will
        have the same package name and version and its dependencies will
        match the installed packages as closely as possible.
        If no substitute is found, None is returned.
        """
        name, version, unused_build = fn.rsplit('-', 2)
        candidates = {}
        for pkg in self.get_pkgs(MatchSpec(name + ' ' + version), max_only=max_only):
            fn1 = pkg.fn
            if self.features(fn1).intersection(features):
                continue
            key = sum(self.sum_matches(fn1, fn2) for fn2 in installed)
            candidates[key] = fn1

        if candidates:
            maxkey = max(candidates)
            return candidates[maxkey]
        else:
            return None

    def installed_features(self, installed):
        """
        Return the set of all features of all `installed` packages,
        """
        res = set()
        for fn in installed:
            try:
                res.update(self.features(fn))
            except KeyError:
                pass
        return res

    def update_with_features(self, fn, features):
        with_features = self.index[fn].get('with_features_depends')
        if with_features is None:
            return
        key = ''
        for fstr in with_features:
            fs = set(fstr.split())
            if fs <= features and len(fs) > len(set(key.split())):
                key = fstr
        if not key:
            return
        d = {ms.name: ms for ms in self.ms_depends(fn)}
        for spec in with_features[key]:
            ms = MatchSpec(spec)
            d[ms.name] = ms
        self.msd_cache[fn] = d.values()

    def solve(self, specs, installed=None, features=None, max_only=False,
              minimal_hint=False):
        if installed is None:
            installed = []
        if features is None:
            features = self.installed_features(installed)
        for spec in specs:
            ms = MatchSpec(spec)
            for pkg in self.get_pkgs(ms, max_only=max_only):
                fn = pkg.fn
                features.update(self.track_features(fn))
        log.debug('specs=%r  features=%r' % (specs, features))
        for spec in specs:
            for pkg in self.get_pkgs(MatchSpec(spec), max_only=max_only):
                fn = pkg.fn
                self.update_with_features(fn, features)

        stdoutlog.info("Solving package specifications: ")
        try:
            return self.explicit(specs) or self.solve2(specs, features,
                                                       minimal_hint=minimal_hint)
        except RuntimeError:
            stdoutlog.info('\n')
            raise


if __name__ == '__main__':
    import json
    from pprint import pprint
    from optparse import OptionParser
    from conda.cli.common import arg2spec

    with open('../tests/index.json') as fi:
        r = Resolve(json.load(fi))

    p = OptionParser(usage="usage: %prog [options] SPEC(s)")
    p.add_option("--mkl", action="store_true")
    opts, args = p.parse_args()

    features = set(['mkl']) if opts.mkl else set()
    specs = [arg2spec(arg) for arg in args]
    pprint(r.solve(specs, [], features))

########NEW FILE########
__FILENAME__ = share
# NOTE:
#     This module is deprecated.  Don't import from this here when writing
#     new code.
from __future__ import print_function, division, absolute_import

import os
import re
import json
import hashlib
import tempfile
import shutil
from os.path import abspath, basename, isdir, join

import conda.config as config
from conda.api import get_index
from conda.misc import untracked
from conda.resolve import MatchSpec
import conda.install as install
import conda.plan as plan

from conda.packup import create_conda_pkg


def get_requires(prefix):
    res = []
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        assert meta
        if 'file_hash' not in meta:
            res.append('%(name)s %(version)s %(build)s' % meta)
    res.sort()
    return res

def update_info(info):
    h = hashlib.new('sha1')
    for spec in info['depends']:
        assert MatchSpec(spec).strictness == 3
        h.update(spec.encode('utf-8'))
        h.update(b'\x00')
    h.update(info['file_hash'].encode('utf-8'))
    info['version'] = h.hexdigest()

def old_create_bundle(prefix):
    """
    Create a "bundle package" of the environment located in `prefix`,
    and return the full path to the created package.  This file is
    created in a temp directory, and it is the callers responsibility
    to remove this directory (after the file has been handled in some way).

    This bundle is a regular meta-package which lists (in its requirements)
    all Anaconda packages installed (not packages the user created manually),
    and all files in the prefix which are not installed from Anaconda
    packages.  When putting this packages into a conda repository,
    it can be used to created a new environment using the conda create
    command.
    """
    info = dict(
        name = 'share',
        build = '0',
        build_number = 0,
        platform = config.platform,
        arch = config.arch_name,
        depends = get_requires(prefix),
    )
    tmp_dir = tempfile.mkdtemp()
    tmp_path = join(tmp_dir, 'share.tar.bz2')
    warnings = create_conda_pkg(prefix,
                                untracked(prefix, exclude_self_build=True),
                                info, tmp_path, update_info)

    path = join(tmp_dir, '%(name)s-%(version)s-%(build)s.tar.bz2' % info)
    os.rename(tmp_path, path)
    return path, warnings


def old_clone_bundle(path, prefix):
    """
    Clone the bundle (located at `path`) by creating a new environment at
    `prefix`.
    The directory `path` is located in should be some temp directory or
    some other directory OUTSITE /opt/anaconda (this function handles
    copying the of the file if necessary for you).  After calling this
    funtion, the original file (at `path`) may be removed.
    """
    assert not abspath(path).startswith(abspath(config.root_dir))
    assert not isdir(prefix)
    fn = basename(path)
    assert re.match(r'share-[0-9a-f]{40}-\d+\.tar\.bz2$', fn), fn
    dist = fn[:-8]

    pkgs_dir = config.pkgs_dirs[0]
    if not install.is_extracted(pkgs_dir, dist):
        shutil.copyfile(path, join(pkgs_dir, dist + '.tar.bz2'))
        plan.execute_plan(['%s %s' % (plan.EXTRACT, dist)])
    assert install.is_extracted(pkgs_dir, dist)

    with open(join(pkgs_dir, dist, 'info', 'index.json')) as fi:
        meta = json.load(fi)

    # for backwards compatibility, use "requires" when "depends" is not there
    dists = ['-'.join(r.split())
             for r in meta.get('depends', meta.get('requires', []))
             if not r.startswith('conda ')]
    dists.append(dist)

    actions = plan.ensure_linked_actions(dists, prefix)
    index = get_index()
    plan.execute_actions(actions, index, verbose=False)

    os.unlink(join(prefix, 'conda-meta', dist + '.json'))

########NEW FILE########
__FILENAME__ = utils
from __future__ import print_function, division, absolute_import

import sys
import hashlib
import tempfile
import collections
from functools import partial
from os.path import abspath, isdir


def try_write(dir_path):
    assert isdir(dir_path)
    try:
        with tempfile.TemporaryFile(prefix='.conda-try-write',
                                    dir=dir_path, mode='wb') as fo:
            fo.write(b'This is a test file.\n')
        return True
    except (IOError, OSError):
        return False


def hashsum_file(path, mode='md5'):
    with open(path, 'rb') as fi:
        h = hashlib.new(mode)
        while True:
            chunk = fi.read(262144)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def md5_file(path):
    return hashsum_file(path, 'md5')


def url_path(path):
    path = abspath(path)
    if sys.platform == 'win32':
        path = '/' + path.replace(':', '|')
    return 'file://%s' % path


def human_bytes(n):
    """
    Return the number of bytes n in more human readable form.
    """
    if n < 1024:
        return '%d B' % n
    k = n/1024
    if k < 1024:
        return '%d KB' % round(k)
    m = k/1024
    if m < 1024:
        return '%.1f MB' % m
    g = m/1024
    return '%.2f GB' % g


class memoized(object):
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
    def __call__(self, *args, **kw):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args, **kw)
        key = (args, frozenset(kw.items()))
        if key in self.cache:
            return self.cache[key]
        else:
            value = self.func(*args, **kw)
            self.cache[key] = value
            return value


# For instance methods only
class memoize(object): # 577452
    def __init__(self, func):
        self.func = func
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)
    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res

########NEW FILE########
__FILENAME__ = verlib
# This module implements PEP 386
# 2010-04-20: hg clone http://bitbucket.org/tarek/distutilsversion/
# Public Domain

"""
"Rational" version definition and parsing for DistutilsVersionFight
discussion at PyCon 2009.
"""

from __future__ import print_function, division, absolute_import

import re

from .compat import string_types

class IrrationalVersionError(Exception):
    """This is an irrational version."""
    pass

class HugeMajorVersionNumError(IrrationalVersionError):
    """An irrational version because the major version number is huge
    (often because a year or date was used).

    See `error_on_huge_major_num` option in `NormalizedVersion` for details.
    This guard can be disabled by setting that option False.
    """
    pass

# A marker used in the second and third parts of the `parts` tuple, for
# versions that don't have those segments, to sort properly. An example
# of versions in sort order ('highest' last):
#   1.0b1                 ((1,0), ('b',1), ('f',))
#   1.0.dev345            ((1,0), ('f',),  ('dev', 345))
#   1.0                   ((1,0), ('f',),  ('f',))
#   1.0.post256.dev345    ((1,0), ('f',),  ('f', 'post', 256, 'dev', 345))
#   1.0.post345           ((1,0), ('f',),  ('f', 'post', 345, 'f'))
#                                   ^        ^                 ^
#   'b' < 'f' ---------------------/         |                 |
#                                            |                 |
#   'dev' < 'f' < 'post' -------------------/                  |
#                                                              |
#   'dev' < 'f' ----------------------------------------------/
# Other letters would do, but 'f' for 'final' is kind of nice.
FINAL_MARKER = ('f',)

VERSION_RE = re.compile(r'''
    ^
    (?P<version>\d+\.\d+)          # minimum 'N.N'
    (?P<extraversion>(?:\.\d+)*)   # any number of extra '.N' segments
    (?:
        (?P<prerel>[abc]|rc)       # 'a'=alpha, 'b'=beta, 'c'=release candidate
                                   # 'rc'= alias for release candidate
        (?P<prerelversion>\d+(?:\.\d+)*)
    )?
    (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?
    $''', re.VERBOSE)

class NormalizedVersion(object):
    """A rational version.

    Good:
        1.2         # equivalent to "1.2.0"
        1.2.0
        1.2a1
        1.2.3a2
        1.2.3b1
        1.2.3c1
        1.2.3.4
        TODO: fill this out

    Bad:
        1           # minimum two numbers
        1.2a        # release level must have a release serial
        1.2.3b
    """
    def __init__(self, s, error_on_huge_major_num=True):
        """Create a NormalizedVersion instance from a version string.

        @param s {str} The version string.
        @param error_on_huge_major_num {bool} Whether to consider an
            apparent use of a year or full date as the major version number
            an error. Default True. One of the observed patterns on PyPI before
            the introduction of `NormalizedVersion` was version numbers like this:
                2009.01.03
                20040603
                2005.01
            This guard is here to strongly encourage the package author to
            use an alternate version, because a release deployed into PyPI
            and, e.g. downstream Linux package managers, will forever remove
            the possibility of using a version number like "1.0" (i.e.
            where the major number is less than that huge major number).
        """
        self._parse(s, error_on_huge_major_num)

    @classmethod
    def from_parts(cls, version, prerelease=FINAL_MARKER,
                   devpost=FINAL_MARKER):
        return cls(cls.parts_to_str((version, prerelease, devpost)))

    def _parse(self, s, error_on_huge_major_num=True):
        """Parses a string version into parts."""
        match = VERSION_RE.search(s)
        if not match:
            raise IrrationalVersionError(s)

        groups = match.groupdict()
        parts = []

        # main version
        block = self._parse_numdots(groups['version'], s, False, 2)
        extraversion = groups.get('extraversion')
        if extraversion not in ('', None):
            block += self._parse_numdots(extraversion[1:], s)
        parts.append(tuple(block))

        # prerelease
        prerel = groups.get('prerel')
        if prerel is not None:
            block = [prerel]
            block += self._parse_numdots(groups.get('prerelversion'), s,
                                         pad_zeros_length=1)
            parts.append(tuple(block))
        else:
            parts.append(FINAL_MARKER)

        # postdev
        if groups.get('postdev'):
            post = groups.get('post')
            dev = groups.get('dev')
            postdev = []
            if post is not None:
                postdev.extend([FINAL_MARKER[0], 'post', int(post)])
                if dev is None:
                    postdev.append(FINAL_MARKER[0])
            if dev is not None:
                postdev.extend(['dev', int(dev)])
            parts.append(tuple(postdev))
        else:
            parts.append(FINAL_MARKER)
        self.parts = tuple(parts)
        if error_on_huge_major_num and self.parts[0][0] > 1980:
            raise HugeMajorVersionNumError("huge major version number, %r, "
                "which might cause future problems: %r" % (self.parts[0][0], s))

    def _parse_numdots(self, s, full_ver_str, drop_trailing_zeros=True,
                       pad_zeros_length=0):
        """Parse 'N.N.N' sequences, return a list of ints.

        @param s {str} 'N.N.N..." sequence to be parsed
        @param full_ver_str {str} The full version string from which this
            comes. Used for error strings.
        @param drop_trailing_zeros {bool} Whether to drop trailing zeros
            from the returned list. Default True.
        @param pad_zeros_length {int} The length to which to pad the
            returned list with zeros, if necessary. Default 0.
        """
        nums = []
        for n in s.split("."):
            if len(n) > 1 and n[0] == '0':
                raise IrrationalVersionError("cannot have leading zero in "
                    "version number segment: '%s' in %r" % (n, full_ver_str))
            nums.append(int(n))
        if drop_trailing_zeros:
            while nums and nums[-1] == 0:
                nums.pop()
        while len(nums) < pad_zeros_length:
            nums.append(0)
        return nums

    def __str__(self):
        return self.parts_to_str(self.parts)

    @classmethod
    def parts_to_str(cls, parts):
        """Transforms a version expressed in tuple into its string
        representation."""
        # XXX This doesn't check for invalid tuples
        main, prerel, postdev = parts
        s = '.'.join(str(v) for v in main)
        if prerel is not FINAL_MARKER:
            s += prerel[0]
            s += '.'.join(str(v) for v in prerel[1:])
        if postdev and postdev is not FINAL_MARKER:
            if postdev[0] == 'f':
                postdev = postdev[1:]
            i = 0
            while i < len(postdev):
                if i % 2 == 0:
                    s += '.'
                s += str(postdev[i])
                i += 1
        return s

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def _cannot_compare(self, other):
        raise TypeError("cannot compare %s and %s"
                % (type(self).__name__, type(other).__name__))

    def __eq__(self, other):
        if isinstance(other, string_types):
            try:
                other = NormalizedVersion(other)
            except IrrationalVersionError:
                # if other can't be interpreted by NormalizedVersion,
                # there's no way it can be equal to something that can.
                return False
        if not isinstance(other, NormalizedVersion):
            #print("error: self.parts = {0}, other = {1}".format(self.parts, other))
            self._cannot_compare(other)
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts < other.parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

def suggest_normalized_version(s):
    """Suggest a normalized version close to the given version string.

    If you have a version string that isn't rational (i.e. NormalizedVersion
    doesn't like it) then you might be able to get an equivalent (or close)
    rational version from this function.

    This does a number of simple normalizations to the given string, based
    on observation of versions currently in use on PyPI. Given a dump of
    those version during PyCon 2009, 4287 of them:
    - 2312 (53.93%) match NormalizedVersion without change
    - with the automatic suggestion
    - 3474 (81.04%) match when using this suggestion method

    @param s {str} An irrational version string.
    @returns A rational version string, or None, if couldn't determine one.
    """
    try:
        NormalizedVersion(s)
        return s   # already rational
    except IrrationalVersionError:
        pass

    rs = s.lower()

    # part of this could use maketrans
    for orig, repl in (('-alpha', 'a'), ('-beta', 'b'), ('alpha', 'a'),
                       ('beta', 'b'), ('rc', 'c'), ('-final', ''),
                       ('-pre', 'c'),
                       ('-release', ''), ('.release', ''), ('-stable', ''),
                       ('+', '.'), ('_', '.'), (' ', ''), ('.final', ''),
                       ('final', '')):
        rs = rs.replace(orig, repl)

    # if something ends with dev or pre, we add a 0
    rs = re.sub(r"pre$", r"pre0", rs)
    rs = re.sub(r"dev$", r"dev0", rs)

    # if we have something like "b-2" or "a.2" at the end of the
    # version, that is pobably beta, alpha, etc
    # let's remove the dash or dot
    rs = re.sub(r"([abc|rc])[\-\.](\d+)$", r"\1\2", rs)

    # 1.0-dev-r371 -> 1.0.dev371
    # 0.1-dev-r79 -> 0.1.dev79
    rs = re.sub(r"[\-\.](dev)[\-\.]?r?(\d+)$", r".\1\2", rs)

    # Clean: 2.0.a.3, 2.0.b1, 0.9.0~c1
    rs = re.sub(r"[.~]?([abc])\.?", r"\1", rs)

    # Clean: v0.3, v1.0
    if rs.startswith('v'):
        rs = rs[1:]

    # Clean leading '0's on numbers.
    #TODO: unintended side-effect on, e.g., "2003.05.09"
    # PyPI stats: 77 (~2%) better
    rs = re.sub(r"\b0+(\d+)(?!\d)", r"\1", rs)

    # Clean a/b/c with no version. E.g. "1.0a" -> "1.0a0". Setuptools infers
    # zero.
    # PyPI stats: 245 (7.56%) better
    rs = re.sub(r"(\d+[abc])$", r"\g<1>0", rs)

    # the 'dev-rNNN' tag is a dev tag
    rs = re.sub(r"\.?(dev-r|dev\.r)\.?(\d+)$", r".dev\2", rs)

    # clean the - when used as a pre delimiter
    rs = re.sub(r"-(a|b|c)(\d+)$", r"\1\2", rs)

    # a terminal "dev" or "devel" can be changed into ".dev0"
    rs = re.sub(r"[\.\-](dev|devel)$", r".dev0", rs)

    # a terminal "dev" can be changed into ".dev0"
    rs = re.sub(r"(?![\.\-])dev$", r".dev0", rs)

    # a terminal "final" or "stable" can be removed
    rs = re.sub(r"(final|stable)$", "", rs)

    # The 'r' and the '-' tags are post release tags
    #   0.4a1.r10       ->  0.4a1.post10
    #   0.9.33-17222    ->  0.9.3.post17222
    #   0.9.33-r17222   ->  0.9.3.post17222
    rs = re.sub(r"\.?(r|-|-r)\.?(\d+)$", r".post\2", rs)

    # Clean 'r' instead of 'dev' usage:
    #   0.9.33+r17222   ->  0.9.3.dev17222
    #   1.0dev123       ->  1.0.dev123
    #   1.0.git123      ->  1.0.dev123
    #   1.0.bzr123      ->  1.0.dev123
    #   0.1a0dev.123    ->  0.1a0.dev123
    # PyPI stats:  ~150 (~4%) better
    rs = re.sub(r"\.?(dev|git|bzr)\.?(\d+)$", r".dev\2", rs)

    # Clean '.pre' (normalized from '-pre' above) instead of 'c' usage:
    #   0.2.pre1        ->  0.2c1
    #   0.2-c1         ->  0.2c1
    #   1.0preview123   ->  1.0c123
    # PyPI stats: ~21 (0.62%) better
    rs = re.sub(r"\.?(pre|preview|-c)(\d+)$", r"c\g<2>", rs)


    # Tcl/Tk uses "px" for their post release markers
    rs = re.sub(r"p(\d+)$", r".post\1", rs)

    try:
        NormalizedVersion(rs)
        return rs   # already rational
    except IrrationalVersionError:
        pass
    return None

########NEW FILE########
__FILENAME__ = _version
# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by github's download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"


import subprocess
import sys
import re
import os.path

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%s', no digits" % ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %s" % ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.exe"
    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = ""
parentdir_prefix = "conda-"
versionfile_source = "conda/_version.py"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver


########NEW FILE########
__FILENAME__ = __main__
import sys
from conda.cli import main

sys.exit(main())

########NEW FILE########
__FILENAME__ = execute
import logging
from optparse import OptionParser

from conda.plan import execute_plan
from conda.api import get_index


def main():
    p = OptionParser(
        usage="usage: %prog [options] FILENAME",
        description="execute an conda plan")

    p.add_option('-q', '--quiet',
                 action="store_true")

    opts, args = p.parse_args()

    logging.basicConfig()

    if len(args) != 1:
        p.error('exactly one argument required')

    execute_plan(open(args[0]), get_index(), not opts.quiet)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = helpers
"""
Helpers for the tests
"""
import subprocess
import sys
import os

def raises(exception, func, string=None):
    try:
        a = func()
    except exception as e:
        if string:
            assert string in e.args[0]
        print(e)
        return True
    raise Exception("did not raise, gave %s" % a)

def run_in(command, shell='bash'):
    p = subprocess.Popen([shell, '-c', command], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return (stdout.decode('utf-8').replace('\r\n', '\n'),
        stderr.decode('utf-8').replace('\r\n', '\n'))

python = sys.executable
conda = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'conda')

def run_conda_command(*args):
    env = os.environ.copy()
    # Make sure bin/conda imports *this* conda.
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(__file__))
    env['CONDARC'] = ' '
    p= subprocess.Popen((python, conda,) + args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env)
    stdout, stderr = p.communicate()
    return (stdout.decode('utf-8').replace('\r\n', '\n'),
        stderr.decode('utf-8').replace('\r\n', '\n'))

########NEW FILE########
__FILENAME__ = mk_index
import os
import sys
import json

from conda.api import get_index


assert os.getenv('CIO_TEST') == '2'
assert tuple.__itemsize__ == 8
assert sys.platform.startswith('linux')

index = get_index()
for info in index.itervalues():
    for key in 'md5', 'size', 'channel', 'build_channel', 'build_target':
        try:
            del info[key]
        except KeyError:
            pass

print(len(index))

data = json.dumps(index, indent=2, sort_keys=True)
data = '\n'.join(line.rstrip() for line in data.split('\n'))
if not data.endswith('\n'):
    data += '\n'
with open('index.json', 'w') as fo:
    fo.write(data)

########NEW FILE########
__FILENAME__ = test_activate
from __future__ import print_function, absolute_import

import os
from os.path import dirname, join
import shutil
import stat

from conda.compat import TemporaryDirectory
from conda.config import root_dir
from .helpers import run_in

# Only run these tests for commands that are installed.

shells = []
for shell in ['bash', 'zsh']:
    try:
        stdout, stderr = run_in('echo', shell)
    except OSError:
        pass
    else:
        if not stderr:
            shells.append(shell)

def write_entry_points(envs):
    """
    Write entry points to {envs}/root/bin

    This is needed because the conda in bin/conda uses #!/usr/bin/env python,
    which doesn't work if you remove the root environment from the PATH. So we
    have to use a conda entry point that has the root Python hard-coded in the
    shebang line.
    """
    activate = join(dirname(dirname(__file__)), 'bin', 'activate')
    deactivate = join(dirname(dirname(__file__)), 'bin', 'deactivate')
    os.makedirs(join(envs, 'bin'))
    shutil.copy2(activate, join(envs, 'bin', 'activate'))
    shutil.copy2(deactivate, join(envs, 'bin', 'deactivate'))
    with open(join(envs, 'bin', 'conda'), 'w') as f:
        f.write(CONDA_ENTRY_POINT.format(syspath=syspath))
    os.chmod(join(envs, 'bin', 'conda'), 0o755)
    return (join(envs, 'bin', 'activate'), join(envs, 'bin', 'deactivate'),
        join(envs, 'bin', 'conda'))

# Make sure the subprocess activate calls this python
syspath = join(root_dir, 'bin')
# dirname, which is used in the activate script, is typically installed in
# /usr/bin (not sure if it has to be)
PATH = ':'.join(['/bin', '/usr/bin'])
ROOTPATH = syspath + ':' + PATH
PYTHONPATH = os.path.dirname(os.path.dirname(__file__))

CONDA_ENTRY_POINT="""\
#!{syspath}/python
import sys
from conda.cli import main

sys.exit(main())
"""

command_setup = """\
export PATH="{ROOTPATH}"
export PS1='$'
export PYTHONPATH="{PYTHONPATH}"
export CONDARC=' '
cd {here}
""".format(here=dirname(__file__), ROOTPATH=ROOTPATH, PYTHONPATH=PYTHONPATH)

command_setup = command_setup + """
mkdir -p {envs}/test1/bin
mkdir -p {envs}/test2/bin
"""

def test_activate_test1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

def test_activate_test1_test2():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test2/bin:" + PATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

def test_activate_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test3
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

def test_activate_test1_test3():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PATH
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == envs + "/test1/bin:" + PATH
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)


def test_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {deactivate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: No environment to deactivate\n'


def test_activate_test1_deactivate():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

def test_wrong_args():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate}
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            source {activate} two args
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            source {deactivate} test
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            source {deactivate} {envs}/test
            printf $PATH
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ROOTPATH
            assert stderr == 'Error: too many arguments.\n'

def test_activate_help():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            {activate} {envs}/test1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source activate ENV" in stderr

            commands = (command_setup + """
            source {activate} --help
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source activate ENV" in stderr

            commands = (command_setup + """
            {deactivate}
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source deactivate" in stderr

            commands = (command_setup + """
            source {deactivate} --help
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert "Usage: source deactivate" in stderr

def test_activate_symlinking():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert not stdout
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)
            for f in ['conda', 'activate', 'deactivate']:
                assert os.path.lexists('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                assert os.path.exists('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                s = os.lstat('{envs}/test1/bin/{f}'.format(envs=envs, f=f))
                assert stat.S_ISLNK(s.st_mode)
                assert os.readlink('{envs}/test1/bin/{f}'.format(envs=envs,
                    f=f)) == '{syspath}/{f}'.format(syspath=syspath, f=f)

            try:
                # Test activate when there are no write permissions in the
                # env. There are two cases:
                # - conda/deactivate/activate are already symlinked
                commands = (command_setup + """
                mkdir -p {envs}/test3/bin
                ln -s {activate} {envs}/test3/bin/activate
                ln -s {deactivate} {envs}/test3/bin/deactivate
                ln -s {conda} {envs}/test3/bin/conda
                chmod 555 {envs}/test3/bin
                source {activate} {envs}/test3
                """).format(envs=envs, activate=activate, deactivate=deactivate, conda=conda)
                stdout, stderr = run_in(commands, shell)
                assert not stdout
                assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test3/bin to PATH\n'.format(envs=envs, syspath=syspath)

                # Make sure it stays the same
                for f in ['conda', 'activate', 'deactivate']:
                    assert os.path.lexists('{envs}/test3/bin/{f}'.format(envs=envs, f=f))
                    assert os.path.exists('{envs}/test3/bin/{f}'.format(envs=envs, f=f))
                    s = os.lstat('{envs}/test3/bin/{f}'.format(envs=envs, f=f))
                    assert stat.S_ISLNK(s.st_mode)
                    assert os.readlink('{envs}/test3/bin/{f}'.format(envs=envs,
                        f=f)) == '{f}'.format(f=locals()[f])

                # - conda/deactivate/activate are not symlinked. In this case,
                # activate should fail
                commands = (command_setup + """
                mkdir -p {envs}/test4/bin
                chmod 555 {envs}/test4/bin
                source {activate} {envs}/test4
                echo $PATH
                echo $CONDA_DEFAULT_ENV
                """).format(envs=envs, activate=activate, deactivate=deactivate, conda=conda)

                stdout, stderr = run_in(commands, shell)
                assert stdout == (
                    '{ROOTPATH}\n' # PATH
                    '\n'           # CONDA_DEFAULT_ENV
                    ).format(ROOTPATH=ROOTPATH)
                assert stderr == ('Cannot activate environment {envs}/test4, '
                'do not have write access to write conda symlink\n').format(envs=envs)

            finally:
                # Change the permissions back so that we can delete the directory
                run_in('chmod 777 {envs}/test3/bin'.format(envs=envs), shell)
                run_in('chmod 777 {envs}/test4/bin'.format(envs=envs), shell)

def test_PS1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '({envs}/test1)$'.format(envs=envs)
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '({envs}/test2)$'.format(envs=envs)
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '({envs}/test1)$'.format(envs=envs)
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            source {activate} two args
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            source {deactivate} test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            source {deactivate} {envs}/test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'

def test_PS1_no_changeps1():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            with open(join(envs, '.condarc'), 'w') as f:
                f.write("""\
changeps1: no
""")
            condarc = """
            CONDARC="{envs}/.condarc"
            """
            commands = (command_setup + condarc + """
            source {activate} {envs}/test1
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + condarc + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf $PS1
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + condarc + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + condarc + """
            source {activate}
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + condarc + """
            source {activate} two args
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + condarc + """
            source {deactivate} test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + condarc + """
            source {deactivate} {envs}/test
            printf $PS1
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '$'
            assert stderr == 'Error: too many arguments.\n'

def test_CONDA_DEFAULT_ENV():
    for shell in shells:
        with TemporaryDirectory(prefix='envs', dir=dirname(__file__)) as envs:
            activate, deactivate, conda = write_entry_points(envs)
            commands = (command_setup + """
            source {activate} {envs}/test1
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '{envs}/test1'.format(envs=envs)
            assert stderr == 'discarding {syspath} from PATH\nprepending {envs}/test1/bin to PATH\n'.format(envs=envs, syspath=syspath)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test2
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '{envs}/test2'.format(envs=envs)
            assert stderr == 'discarding {envs}/test1/bin from PATH\nprepending {envs}/test2/bin to PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test3
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {activate} {envs}/test3
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == '{envs}/test1'.format(envs=envs)
            assert stderr == 'Error: no such directory: {envs}/test3/bin\n'.format(envs=envs)

            commands = (command_setup + """
            source {deactivate}
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: No environment to deactivate\n'

            commands = (command_setup + """
            source {activate} {envs}/test1 2> /dev/null
            source {deactivate}
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'discarding {envs}/test1/bin from PATH\n'.format(envs=envs)

            commands = (command_setup + """
            source {activate}
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: no environment provided.\n'

            commands = (command_setup + """
            source {activate} two args
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: did not expect more than one argument.\n'

            commands = (command_setup + """
            source {deactivate} test
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: too many arguments.\n'

            commands = (command_setup + """
            source {deactivate} {envs}/test
            printf "$CONDA_DEFAULT_ENV"
            """).format(envs=envs, deactivate=deactivate, activate=activate)

            stdout, stderr = run_in(commands, shell)
            assert stdout == ''
            assert stderr == 'Error: too many arguments.\n'

            # commands = (command_setup + """
            # source {activate} root
            # printf "$CONDA_DEFAULT_ENV"
            # """).format(envs=envs, deactivate=deactivate, activate=activate)
            #
            # stdout, stderr = run_in(commands, shell)
            # assert stdout == 'root'
            # assert stderr == 'Error: too many arguments.\n'

# TODO:
# - Test activating an env by name
# - Test activating "root"
# - Test activating "root" and then deactivating

########NEW FILE########
__FILENAME__ = test_cli
import unittest

from conda.cli.common import arg2spec, spec_from_line


class TestArg2Spec(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(arg2spec('python'), 'python')
        self.assertEqual(arg2spec('python=2.6'), 'python 2.6*')
        self.assertEqual(arg2spec('ipython=0.13.2'), 'ipython 0.13.2*')
        self.assertEqual(arg2spec('ipython=0.13.0'), 'ipython 0.13|0.13.0*')
        self.assertEqual(arg2spec('foo=1.3.0=3'), 'foo 1.3.0 3')

    def test_pip_style(self):
        self.assertEqual(arg2spec('foo>=1.3'), 'foo >=1.3')
        self.assertEqual(arg2spec('zope.int>=1.3,<3.0'), 'zope.int >=1.3,<3.0')
        self.assertEqual(arg2spec('numpy >=1.9'), 'numpy >=1.9')

    def test_invalid(self):
        self.assertRaises(SystemExit, arg2spec, '!xyz 1.3')


class TestSpecFromLine(unittest.TestCase):

    def test_invalid(self):
        self.assertEqual(spec_from_line('='), None)
        self.assertEqual(spec_from_line('foo 1.0'), None)

    def test_conda_style(self):
        self.assertEqual(spec_from_line('foo'), 'foo')
        self.assertEqual(spec_from_line('foo=1.0'), 'foo 1.0')
        self.assertEqual(spec_from_line('foo=1.0*'), 'foo 1.0*')
        self.assertEqual(spec_from_line('foo=1.0|1.2'), 'foo 1.0|1.2')
        self.assertEqual(spec_from_line('foo=1.0=2'), 'foo 1.0 2')

    def test_pip_style(self):
        self.assertEqual(spec_from_line('foo>=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo >=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('FOO-Bar >=1.0'), 'foo-bar >=1.0')
        self.assertEqual(spec_from_line('foo >= 1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo > 1.0'), 'foo >1.0')
        self.assertEqual(spec_from_line('foo != 1.0'), 'foo !=1.0')
        self.assertEqual(spec_from_line('foo <1.0'), 'foo <1.0')
        self.assertEqual(spec_from_line('foo >=1.0 , < 2.0'), 'foo >=1.0,<2.0')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_config
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import unittest
from os.path import dirname, join
import yaml

import conda.config as config

from .helpers import run_conda_command

# use condarc from source tree to run these tests against
config.rc_path = join(dirname(__file__), 'condarc')

# unset CIO_TEST

try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def __init__(self, *args, **kwargs):
        config.rc = config.load_condarc(config.rc_path)
        super(TestConfig, self).__init__(*args, **kwargs)

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dirs)
        self.assertTrue(config.envs_dirs)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)
        self.assertTrue(config.bits in (32, 64))

    def test_pkgs_dir_from_envs_dir(self):
        root_dir = config.root_dir
        root_pkgs = join(root_dir, 'pkgs')
        for pi, po in [
            (join(root_dir, 'envs'), root_pkgs),
            ('/usr/local/foo/envs', '/usr/local/foo/envs/.pkgs'),
            ]:
            self.assertEqual(config.pkgs_dir_from_envs_dir(pi), po)

    def test_proxy_settings(self):
        self.assertEqual(config.get_proxy_servers(),
                         {'http': 'http://user:pass@corp.com:8080',
                          'https': 'https://user:pass@corp.com:8080'})

    def test_normalize_urls(self):
        current_platform = config.subdir
        assert config.DEFAULT_CHANNEL_ALIAS == 'https://conda.binstar.org/'
        assert config.rc.get('channel_alias') == 'https://your.repo/'

        for channel in config.normalize_urls(['defaults', 'system',
            'https://binstar.org/username', 'file:///Users/username/repo',
            'username']):
            assert channel.endswith('/%s/' % current_platform)
        self.assertEqual(config.normalize_urls([
            'defaults', 'system', 'https://conda.binstar.org/username',
            'file:///Users/username/repo', 'username'
            ], 'osx-64'),
            [
                'http://repo.continuum.io/pkgs/free/osx-64/',
                'http://repo.continuum.io/pkgs/pro/osx-64/',
                'https://your.repo/binstar_username/osx-64/',
                'http://some.custom/channel/osx-64/',
                'http://repo.continuum.io/pkgs/free/osx-64/',
                'http://repo.continuum.io/pkgs/pro/osx-64/',
                'https://conda.binstar.org/username/osx-64/',
                'file:///Users/username/repo/osx-64/',
                'https://your.repo/username/osx-64/',
                ])

test_condarc = os.path.join(os.path.dirname(__file__), 'test_condarc')
def _read_test_condarc():
    with open(test_condarc) as f:
        return f.read()

# Tests for the conda config command
def test_config_command_basics():

    try:
        # Test that creating the file adds the defaults channel
        assert not os.path.exists('test_condarc')
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'test')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
channels:
  - test
  - defaults
"""
        os.unlink(test_condarc)

        # When defaults is explicitly given, it should not be added
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
    'channels', 'test', '--add', 'channels', 'defaults')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
channels:
  - defaults
  - test
"""
        os.unlink(test_condarc)

        # Duplicate keys should not be added twice
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
        'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
        'channels', 'test')
        assert stdout == ''
        assert stderr == "Skipping channels: test, item already exists\n"
        assert _read_test_condarc() == """\
channels:
  - test
  - defaults
"""
        os.unlink(test_condarc)

        # Test creating a new file with --set
        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--set', 'always_yes', 'yes')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
always_yes: yes
"""
        os.unlink(test_condarc)


    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass

def test_config_command_get():
    try:
        # Test --get
        with open(test_condarc, 'w') as f:
            f.write("""\
channels:
  - test
  - defaults

create_default_packages:
  - ipython
  - numpy

changeps1: no

always_yes: yes

invalid_key: yes
""")

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--get')
        assert stdout == """\
--set always_yes True
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'
"""
        assert stderr == "invalid_key is not a valid key\n"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'channels')

        assert stdout == """\
--add channels 'defaults'
--add channels 'test'
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'changeps1')

        assert stdout == """\
--set changeps1 False
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--get', 'changeps1', 'channels')

        assert stdout == """\
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'allow_softlinks')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'track_features')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'invalid_key')

        assert stdout == ""
        assert "invalid choice: 'invalid_key'" in stderr

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'not_valid_key')

        assert stdout == ""
        assert "invalid choice: 'not_valid_key'" in stderr

        os.unlink(test_condarc)


    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass

def test_config_command_parser():
    try:
        # Now test the YAML "parser"
        condarc = """\
 channels : \n\
   -  test
   -  defaults \n\

 create_default_packages:
    - ipython
    - numpy

 changeps1 :  no

# Here is a comment
 always_yes: yes \n\
"""
        # First verify that this itself is valid YAML
        assert yaml.load(condarc) == {'channels': ['test', 'defaults'],
            'create_default_packages': ['ipython', 'numpy'], 'changeps1':
            False, 'always_yes': True}

        with open(test_condarc, 'w') as f:
            f.write(condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--get')

        assert stdout == """\
--set always_yes True
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'
"""
        assert stderr == ''

        # List keys with nonstandard whitespace are not yet supported. For
        # now, just test that it doesn't muck up the file.
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'create_default_packages', 'sympy')
        assert stdout == ''
        assert stderr == """\
Error: Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: modified yaml doesn't match what it should be
"""
        assert _read_test_condarc() == condarc

#         assert _read_test_condarc() == """\
#  channels : \n\
#    -  test
#    -  defaults \n\
#
#  create_default_packages:
#     - sympy
#     - ipython
#     - numpy
#
#  changeps1 :  no
#
# # Here is a comment
#  always_yes: yes \n\
# """

        # New keys when the keys are indented are not yet supported either.
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'disallow', 'perl')
        assert stdout == ''
        assert stderr == """\
Error: Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: couldn't parse modified yaml
"""
        assert _read_test_condarc() == condarc

#         assert _read_test_condarc() == """\
#  channels : \n\
#    -  test
#    -  defaults \n\
#
#  create_default_packages:
#     - sympy
#     - ipython
#     - numpy
#
#  changeps1 :  no
#
# # Here is a comment
#  always_yes: yes \n\
#  disallow:
#    - perl
# """

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'mychannel')
        assert stdout == stderr == ''

        assert _read_test_condarc() == """\
 channels : \n\
   - mychannel
   -  test
   -  defaults \n\

 create_default_packages:
    - ipython
    - numpy

 changeps1 :  no

# Here is a comment
 always_yes: yes \n\
"""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--set', 'changeps1', 'yes')

        assert stdout == stderr == ''

        assert _read_test_condarc() == """\
 channels : \n\
   - mychannel
   -  test
   -  defaults \n\

 create_default_packages:
    - ipython
    - numpy

 changeps1 :  yes

# Here is a comment
 always_yes: yes \n\
"""

        os.unlink(test_condarc)


        # Test adding a new list key. We couldn't test this above because it
        # doesn't work yet with odd whitespace
        condarc = """\
channels:
  - test
  - defaults

always_yes: yes
"""

        with open(test_condarc, 'w') as f:
            f.write(condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'disallow', 'perl')
        assert stdout == stderr == ''
        assert _read_test_condarc() == condarc + """\

disallow:
  - perl
"""
        os.unlink(test_condarc)


    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass

def test_config_command_remove_force():
    try:
        # Finally, test --remove, --remove-key, and --force (right now
        # --remove and --remove-key require --force)
        run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'test')
        run_conda_command('config', '--file', test_condarc, '--set',
            'always_yes', 'yes')
        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove', 'channels', 'test', '--force')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc()) == {'channels': ['defaults'],
            'always_yes': True}

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove', 'channels', 'test', '--force')
        assert stdout == ''
        assert stderr == "Error: 'test' is not in the 'channels' key of the config file\n"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove', 'disallow', 'python', '--force')
        assert stdout == ''
        assert stderr == "Error: key 'disallow' is not in the config file\n"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove-key', 'always_yes', '--force')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc()) == {'channels': ['defaults']}

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove-key', 'always_yes', '--force')

        assert stdout == ''
        assert stderr == "Error: key 'always_yes' is not in the config file\n"
        os.unlink(test_condarc)

    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass

########NEW FILE########
__FILENAME__ = test_import
""" Test if we can import everything from conda.
This basically tests syntax correctness and whether the internal imports work.
Created to test py3k compatibility.
"""

from __future__ import print_function, division, absolute_import

import os
import sys
import unittest
import conda

PREFIX = os.path.dirname(os.path.abspath(conda.__file__))


class TestImportAllConda(unittest.TestCase):

    def _test_import(self, subpackage):
        # Prepare
        prefix = PREFIX
        module_prefix = 'conda'
        if subpackage:
            prefix = os.path.join(prefix, subpackage)
            module_prefix = '%s.%s' % (module_prefix, subpackage)

        # Try importing root
        __import__(module_prefix)

        # Import each module in given (sub)package
        for fname in os.listdir(prefix):
            # Discard files that are not of interest
            if fname.startswith('__'):
                continue
            elif not fname.endswith('.py'):
                continue
            elif fname.startswith('windows') and sys.platform != 'win32':
                continue
            # Import
            modname = module_prefix + '.' + fname.split('.')[0]
            print('importing', modname)
            __import__(modname)


    def test_import_root(self):
        self._test_import('')

    def test_import_cli(self):
        self._test_import('cli')

    def test_import_progressbar(self):
        self._test_import('progressbar')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_info
from __future__ import print_function, absolute_import, division

from conda import config

from .helpers import run_conda_command

def test_info():
    conda_info_out, conda_info_err = run_conda_command('info')
    assert conda_info_err == ''
    for name in ['platform', 'conda version', 'root environment',
        'default environment', 'envs directories', 'package cache',
        'channel URLs', 'config file', 'is foreign system']:
        assert name in conda_info_out

    conda_info_e_out, conda_info_e_err = run_conda_command('info', '-e')
    assert 'root' in conda_info_e_out
    assert conda_info_e_err == ''

    conda_info_s_out, conda_info_s_err = run_conda_command('info', '-s')
    assert conda_info_s_err == ''
    for name in ['sys.version', 'sys.prefix', 'sys.executable', 'conda location',
        'conda-build', 'CIO_TEST', 'CONDA_DEFAULT_ENV', 'PATH', 'PYTHONPATH']:
        assert name in conda_info_s_out
    if config.platform == 'linux':
        assert 'LD_LIBRARY_PATH' in conda_info_s_out
    if config.platform == 'osx':
        assert 'DYLD_LIBRARY_PATH' in conda_info_s_out

    conda_info_all_out, conda_info_all_err = run_conda_command('info', '--all')
    assert conda_info_all_err == ''
    assert conda_info_out in conda_info_all_out
    assert conda_info_e_out in conda_info_all_out
    assert conda_info_s_out in conda_info_all_out

########NEW FILE########
__FILENAME__ = test_install
import shutil
import tempfile
import unittest
from os.path import join

from conda.install import PaddingError, binary_replace, update_prefix


class TestBinaryReplace(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(
            binary_replace(b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbbb'),
                           b'xxxbbbbbxyz\x00zz')

    def test_shorter(self):
        self.assertEqual(
            binary_replace(b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbb'),
                           b'xxxbbbbxyz\x00\x00zz')

    def test_too_long(self):
        self.assertRaises(PaddingError, binary_replace,
                          b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbbbbbb')

    def test_no_extra(self):
        self.assertEqual(binary_replace(b'aaaaa\x00', b'aaaaa', b'bbbbb'),
                                        b'bbbbb\x00')

    def test_two(self):
        self.assertEqual(
            binary_replace(b'aaaaa\x001234aaaaacc\x00\x00', b'aaaaa', b'bbbbb'),
                           b'bbbbb\x001234bbbbbcc\x00\x00')

class FileTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfname = join(self.tmpdir, 'testfile')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_default_text(self):
        with open(self.tmpfname, 'w') as fo:
            fo.write('#!/opt/anaconda1anaconda2anaconda3/bin/python\n'
                     'echo "Hello"\n')
        update_prefix(self.tmpfname, '/usr/local')
        with open(self.tmpfname, 'r') as fi:
            data = fi.read()
            self.assertEqual(data, '#!/usr/local/bin/python\n'
                                   'echo "Hello"\n')

    def test_binary(self):
        with open(self.tmpfname, 'wb') as fo:
            fo.write(b'\x7fELF.../some-placeholder/lib/libfoo.so\0')
        update_prefix(self.tmpfname, '/usr/local',
                      placeholder='/some-placeholder', mode='binary')
        with open(self.tmpfname, 'rb') as fi:
            data = fi.read()
            self.assertEqual(data,
                      b'\x7fELF.../usr/local/lib/libfoo.so\0\0\0\0\0\0\0\0')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_logic
import pycosat

from itertools import product

from conda.compat import log2, ceil
from conda.logic import Linear, Clauses, true, false

from tests.helpers import raises

def my_itersolve(iterable):
    """
    Work around https://github.com/ContinuumIO/pycosat/issues/13
    """
    iterable = [[i for i in j] for j in iterable]
    return pycosat.itersolve(iterable)

# TODO: We test that all the models of the transformed system are models of
# the original, but not that all models of the original are models of the
# transformed system.  Or does testing -x do this?

class NoBool(object):
    # Will only be called if tests are wrong and don't short-circuit correctly
    def __bool__(self):
        raise TypeError
    __nonzero__ = __bool__

def boolize(x):
    if x == true:
        return True
    if x == false:
        return False
    return NoBool()

def test_ITE():
    # Note, pycosat will automatically include all smaller numbers in models,
    # e.g., itersolve([[2]]) gives [[1, 2], [-1, 2]]. This should not be an
    # issue here.

    for c in [true, false, 1]:
        for t in [true, false, 2]:
            for f in [true, false, 3]:
                Cl = Clauses(3)
                x = Cl.ITE(c, t, f)
                if x in [true, false]:
                    if t == f:
                        # In this case, it doesn't matter if c is not boolizable
                        assert boolize(x) == boolize(t)
                    else:
                        assert boolize(x) == (boolize(t) if boolize(c) else
                            boolize(f)), (c, t, f)
                else:

                    for sol in my_itersolve({(x,)} | Cl.clauses):
                        C = boolize(c) if c in [true, false] else (1 in sol)
                        T = boolize(t) if t in [true, false] else (2 in sol)
                        F = boolize(f) if f in [true, false] else (3 in sol)
                        assert T if C else F, (T, C, F, sol, t, c, f)

                    for sol in my_itersolve({(-x,)} | Cl.clauses):
                        C = boolize(c) if c in [true, false] else (1 in sol)
                        T = boolize(t) if t in [true, false] else (2 in sol)
                        F = boolize(f) if f in [true, false] else (3 in sol)
                        assert not (T if C else F)

def test_And_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x = C.And(i*1, j*2)
            for sol in my_itersolve({(x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert f and g
            for sol in my_itersolve({(-x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f and g)

    C = Clauses(1)
    x = C.And(1, -1)
    assert x == false # x and ~x
    assert C.clauses == set([])

    C = Clauses(1)
    x = C.And(1, 1)
    for sol in my_itersolve({(x,)} | C.clauses):
        f = 1 in sol
        assert (f and f)
    for sol in my_itersolve({(-x,)} | C.clauses):
        f = 1 in sol
        assert not (f and f)

def test_And_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x = C.And(f, g)
            assert x == (true if (boolize(f) and boolize(g)) else false)
            assert C.clauses == set([])

        C = Clauses(1)
        x = C.And(f, 1)
        fb = boolize(f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb and NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb and a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb and a)

        C = Clauses(1)
        x = C.And(1, f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb and NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb and a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb and a)


def test_Or_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x = C.Or(i*1, j*2)
            for sol in my_itersolve({(x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert f or g
            for sol in my_itersolve({(-x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f or g)

    C = Clauses(1)
    x = C.Or(1, -1)
    assert x == true # x or ~x
    assert C.clauses == set([])

    C = Clauses(1)
    x = C.Or(1, 1)
    for sol in my_itersolve({(x,)} | C.clauses):
        f = 1 in sol
        assert (f or f)
    for sol in my_itersolve({(-x,)} | C.clauses):
        f = 1 in sol
        assert not (f or f)


def test_Or_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x = C.Or(f, g)
            assert x == (true if (boolize(f) or boolize(g)) else false)
            assert C.clauses == set([])

        C = Clauses(1)
        x = C.Or(f, 1)
        fb = boolize(f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb or NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb or a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb or a)

        C = Clauses(1)
        x = C.Or(1, f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb or NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb or a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb or a)

# Note xor is the same as !=
def test_Xor_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x = C.Xor(i*1, j*2)
            for sol in my_itersolve({(x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert (f != g)
            for sol in my_itersolve({(-x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f != g)

    C = Clauses(1)
    x = C.Xor(1, 1)
    assert x == false # x xor x
    assert C.clauses == set([])

    C = Clauses(1)
    x = C.Xor(1, -1)
    assert x == true # x xor -x
    assert C.clauses == set([])

def test_Xor_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x = C.Xor(f, g)
            assert x == (true if (boolize(f) != boolize(g)) else false)
            assert C.clauses == set([])

        C = Clauses(1)
        x = C.Xor(f, 1)
        fb = boolize(f)
        if x in [true, false]:
            assert False
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb != a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb != a)

        C = Clauses(1)
        x = C.Xor(1, f)
        if x in [true, false]:
            assert False
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert not (fb == a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not not (fb == a)

def test_true_false():
    assert true == true
    assert false == false
    assert true != false
    assert false != true
    assert -true == false
    assert -false == true

    assert false < true
    assert not (true < false)
    assert not (false < false)
    assert not (true < true)
    assert false <= true
    assert true <= true
    assert false <= false
    assert true <= true

    assert not (false > true)
    assert true > false
    assert not (false > false)
    assert not (true > true)
    assert not (false >= true)
    assert (true >= true)
    assert false >= false
    assert true >= true

def test_Linear():
    l = Linear([(3, 1), (2, -4), (4, 5)], 12)
    l2 = Linear([(3, 1), (2, -4), (4, 5)], 12)
    l3 = Linear([(3, 2), (2, -4), (4, 5)], 12)
    l4 = Linear([(3, 1), (2, -4), (4, 5)], 11)
    assert l == l
    assert l == l2
    assert l != l3
    assert l != l4

    assert l.equation == [(2, -4), (3, 1), (4, 5)]
    assert l.lo == l.hi == l.rhs == 12
    assert l.coeffs == [2, 3, 4]
    assert l.atoms == [-4, 1, 5]
    assert l.total == 9

    assert len(l) == 3

    # Remember that the equation is sorted
    assert l[1:] == Linear([(3, 1), (4, 5)], 12)

    assert str(l) == repr(l) == "Linear([(2, -4), (3, 1), (4, 5)], 12)"

    l = Linear([(3, 1), (2, -4), (4, 5)], [3, 5])
    assert l != l2
    assert l != l3
    assert l != l4

    assert l.equation == [(2, -4), (3, 1), (4, 5)]
    assert l.lo == 3
    assert l.hi == 5
    assert l.rhs == [3, 5]
    assert l.coeffs == [2, 3, 4]
    assert l.atoms == [-4, 1, 5]
    assert l.total == 9

    assert len(l) == 3

    assert l([1, 2, 3, 4, 5]) == False
    assert l([1, 2, 3, 4, -5]) == True
    assert l([1, 2, 3, -4, -5]) == True
    assert l([-1, -2, -3, -4, -5]) == False
    assert l([-1, 2, 3, 4, -5]) == False

    # Remember that the equation is sorted
    assert l[1:] == Linear([(3, 1), (4, 5)], [3, 5])

    assert str(l) == repr(l) == "Linear([(2, -4), (3, 1), (4, 5)], [3, 5])"
    l = Linear([], [1, 3])
    assert l.equation == []
    assert l.lo == 1
    assert l.hi == 3
    assert l.coeffs == []
    assert l.atoms == []
    assert l.total == 0
    assert l([1, 2, 3]) == False

def test_BDD():
    L = [
        Linear([(1, 1), (2, 2)], [0, 2]),
        Linear([(1, 1), (2, -2)], [0, 2]),
        Linear([(1, 1), (2, 2), (3, 3)], [3, 3]),
        Linear([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7)], [0, 2])
        ]
    for l in L:
        Cr = Clauses(max(l.atoms))
        xr = Cr.build_BDD_recursive(l)
        C = Clauses(max(l.atoms))
        x = C.build_BDD(l)
        assert x == xr
        assert C.clauses == Cr.clauses
        for sol in my_itersolve({(x,)} | C.clauses):
            assert l(sol)
        for sol in my_itersolve({(-x,)} | C.clauses):
            assert not l(sol)

    # Real life example. There are too many solutions to check them all, just
    # check that building the BDD doesn't take forever
    l = Linear([(1, 15), (2, 16), (3, 17), (4, 18), (5, 6), (5, 19), (6, 7),
    (6, 20), (7, 8), (7, 21), (7, 28), (8, 9), (8, 22), (8, 29), (8, 41), (9,
    10), (9, 23), (9, 30), (9, 42), (10, 1), (10, 11), (10, 24), (10, 31),
    (10, 34), (10, 37), (10, 43), (10, 46), (10, 50), (11, 2), (11, 12), (11,
    25), (11, 32), (11, 35), (11, 38), (11, 44), (11, 47), (11, 51), (12, 3),
    (12, 4), (12, 5), (12, 13), (12, 14), (12, 26), (12, 27), (12, 33), (12,
    36), (12, 39), (12, 40), (12, 45), (12, 48), (12, 49), (12, 52), (12, 53),
    (12, 54)], [192, 204])

    Cr = Clauses(max(l.atoms))
    xr = Cr.build_BDD_recursive(l)
    C = Clauses(max(l.atoms))
    x = C.build_BDD(l)
    assert x == xr
    assert C.clauses == Cr.clauses
    for _, sol in zip(range(20), my_itersolve({(x,)} | C.clauses)):
        assert l(sol)
    for _, sol in zip(range(20), my_itersolve({(-x,)} | C.clauses)):
        assert not l(sol)

    # Another real-life example. This one is too big to be built recursively
    # unless the recursion limit is increased.
    l = Linear([(0, 12), (0, 14), (0, 22), (0, 59), (0, 60), (0, 68), (0,
        102), (0, 105), (0, 164), (0, 176), (0, 178), (0, 180), (0, 182), (1,
            9), (1, 13), (1, 21), (1, 58), (1, 67), (1, 101), (1, 104), (1,
                163), (1, 175), (1, 177), (1, 179), (1, 181), (2, 6), (2, 20),
        (2, 57), (2, 66), (2, 100), (2, 103), (2, 162), (2, 174), (3, 11), (3,
            19), (3, 56), (3, 65), (3, 99), (3, 161), (3, 173), (4, 8), (4,
                18), (4, 55), (4, 64), (4, 98), (4, 160), (4, 172), (5, 5),
        (5, 17), (5, 54), (5, 63), (5, 97), (5, 159), (5, 171), (6, 10), (6,
            16), (6, 52), (6, 62), (6, 96), (6, 158), (6, 170), (7, 7), (7,
                15), (7, 50), (7, 61), (7, 95), (7, 157), (7, 169), (8, 4),
        (8, 48), (8, 94), (8, 156), (8, 168), (9, 3), (9, 46), (9, 93), (9,
            155), (9, 167), (10, 2), (10, 53), (10, 92), (10, 154), (10, 166),
        (11, 1), (11, 51), (11, 91), (11, 152), (11, 165), (12, 49), (12, 90),
        (12, 150), (13, 47), (13, 89), (13, 148), (14, 45), (14, 88), (14,
            146), (15, 39), (15, 87), (15, 144), (16, 38), (16, 86), (16,
                142), (17, 37), (17, 85), (17, 140), (18, 44), (18, 84), (18,
                    138), (19, 43), (19, 83), (19, 153), (20, 42), (20, 82),
        (20, 151), (21, 41), (21, 81), (21, 149), (22, 40), (22, 80), (22,
            147), (23, 36), (23, 79), (23, 145), (24, 32), (24, 70), (24,
                143), (25, 35), (25, 78), (25, 141), (26, 34), (26, 77), (26,
                    139), (27, 31), (27, 76), (27, 137), (28, 30), (28, 75),
        (28, 136), (29, 33), (29, 74), (29, 135), (30, 29), (30, 73), (30,
            134), (31, 28), (31, 72), (31, 133), (32, 27), (32, 71), (32,
                132), (33, 25), (33, 69), (33, 131), (34, 24), (34, 130), (35,
                    26), (35, 129), (36, 23), (36, 128), (37, 125), (38, 124),
        (39, 123), (40, 122), (41, 121), (42, 120), (43, 119), (44, 118), (45,
            117), (46, 116), (47, 115), (48, 114), (49, 113), (50, 127), (51,
                126), (52, 112), (53, 111), (54, 110), (55, 109), (56, 108),
        (57, 107), (58, 106)], [21, 40])

    C = Clauses(max(l.atoms))
    x = C.build_BDD(l)
    for _, sol in zip(range(20), my_itersolve({(x,)} | C.clauses)):
        assert l(sol)
    for _, sol in zip(range(20), my_itersolve({(-x,)} | C.clauses)):
        assert not l(sol)



def test_cmp_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x, y = C.Cmp(i*1, j*2)
            for sol in my_itersolve(C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                M = x in sol
                m = y in sol
                assert M == max(f, g)
                assert m == min(f, g)

    C = Clauses(1)
    x, y = C.Cmp(1, -1)
    assert x, y == [true, false] # true > false
    assert C.clauses == set([])

    C = Clauses(1)
    x, y = C.Cmp(1, 1)
    for sol in my_itersolve(C.clauses):
        f = 1 in sol
        M = x in sol
        m = y in sol
        assert M == max(f, f)
        assert m == min(f, f)

def test_Cmp_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x, y = C.Cmp(f, g)
            assert x == max(f, g)
            assert y == min(f, g)
            assert C.clauses == set([])

        C = Clauses(1)
        x, y = C.Cmp(f, 1)
        fb = boolize(f)
        # No better way to test this without defining true >= 1, which seems
        # like a bad idea. Should represent the order true >= 1 >= false.
        if fb:
            assert [x, y] == [true, 1]
        else:
            assert [x, y] == [1, false]

        C = Clauses(1)
        x, y = C.Cmp(1, f)
        fb = boolize(f)
        if fb:
            assert [x, y] == [true, 1]
        else:
            assert [x, y] == [1, false]

def test_odd_even_merge():
    for n in [1, 2, 4, 8, 16]:
        A = list(range(1, n+1))
        B = list(range(n+1, 2*n+1))
        C = Clauses(n)
        merged = C.odd_even_merge(A, B)
        for i in range(n+1):
            for j in range(n+1):
                # Test all possible mergings of sorted lists, like [1, 1, 0,
                # 0] and [1, 0, 0, 0] -> [1, 1, 1, 0, 0, 0, 0, 0].
                Asigns = [1]*i + [-1]*(n - i)
                Bsigns = [1]*j + [-1]*(n - j)
                As = {(s*a,) for s, a in zip(Asigns, A)}
                Bs = {(s*b,) for s, b in zip(Bsigns, B)}
                for sol in my_itersolve(C.clauses | As | Bs):
                    a = [i in sol for i in A]
                    b = [i in sol for i in B]
                    m = [i in sol for i in merged]
                    # Check we did the above correctly
                    assert a == sorted(a, reverse=True)
                    assert b == sorted(b, reverse=True)
                    # And check that the merge is correct
                    assert m == sorted(a + b, reverse=True)

    assert raises(ValueError, lambda: Clauses(4).odd_even_merge([1, 2], [2, 3, 4]))

def test_odd_even_mergesort():
    for n in [1, 2, 4, 8]:
        A = list(range(1, n+1))
        C = Clauses(n)
        S = C.odd_even_mergesort(A)
        # Note, the zero-one principle states we only need to test lists of
        # 0's and
        # 1's. https://en.wikipedia.org/wiki/Sorting_network#Zero-one_principle.
        for sol in my_itersolve(C.clauses):
            a = [i in sol for i in A]
            s = [i in sol for i in S]
            assert s == sorted(a, reverse=True)

    # TODO: n > 8 takes too long to test all combinations, but maybe we should test
    # some random combinations.

    assert raises(ValueError, lambda: Clauses(5).odd_even_mergesort([1, 2, 3,
    4, 5]))

    # Make sure it works with booleans
    for n in [1, 2, 4]:
        for item in product(*[[true, false]]*n):
            assert list(Clauses(0).odd_even_mergesort(item)) == sorted(item, reverse=True)

    # The most important use-case is extending a non-power of 2 length list
    # with false.
    for n in range(1, 9):
        next_power_of_2 = 2**ceil(log2(n))
        assert n <= next_power_of_2
        for item in product(*[[true, false]]*(next_power_of_2 - n)):

            A = list(range(1, n + 1)) + list(item)
            C = Clauses(n)
            S = C.odd_even_mergesort(A)

            for sol in my_itersolve(C.clauses):
                a = [boolize(i) if isinstance(boolize(i), bool) else
                    i in sol for i in A]
                s = [boolize(i) if isinstance(boolize(i), bool) else
                    i in sol for i in S]

                assert s == sorted(a, reverse=True), (a, s, sol)

def test_sorter():
    L = [
        Linear([(1, 1), (2, 2)], [0, 2]),
        Linear([(1, 1), (2, -2)], [0, 2]),
        Linear([(1, 1), (2, 2), (3, 3)], [3, 3]),
        Linear([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7)], [0, 2])
        ]
    for l in L:
        C = Clauses(max(l.atoms))
        m = C.build_sorter(l)
        if l.rhs[0]:
            x = {(m[l.rhs[0]-1],), (-m[l.rhs[1]],)}
            nx = {(-m[l.rhs[0]-1], m[l.rhs[1]])}
        else:
            x = {(-m[l.rhs[1]],)}
            nx = {(m[l.rhs[1]],)}
        for sol in my_itersolve(x | C.clauses):
            assert l(sol)
        for sol in my_itersolve(nx | C.clauses):
            assert not l(sol)

    l = Linear([(1, 15), (2, 16), (3, 17), (4, 18), (5, 6), (5, 19), (6, 7),
    (6, 20), (7, 8), (7, 21), (7, 28), (8, 9), (8, 22), (8, 29), (8, 41), (9,
    10), (9, 23), (9, 30), (9, 42), (10, 1), (10, 11), (10, 24), (10, 31),
    (10, 34), (10, 37), (10, 43), (10, 46), (10, 50), (11, 2), (11, 12), (11,
    25), (11, 32), (11, 35), (11, 38), (11, 44), (11, 47), (11, 51), (12, 3),
    (12, 4), (12, 5), (12, 13), (12, 14), (12, 26), (12, 27), (12, 33), (12,
    36), (12, 39), (12, 40), (12, 45), (12, 48), (12, 49), (12, 52), (12, 53),
    (12, 54)], [192, 204])

    C = Clauses(max(l.atoms))
    m = C.build_sorter(l)
    if l.rhs[0]:
        x = {(m[l.rhs[0]-1],), (-m[l.rhs[1]],)}
        nx = {(-m[l.rhs[0]-1], m[l.rhs[1]])}
    else:
        x = {(-m[l.rhs[1]],)}
        nx = {(m[l.rhs[1]],)}
    for sol, _ in zip(my_itersolve(x | C.clauses), range(2)):
        assert l(sol)
    for sol, _ in zip(my_itersolve(nx | C.clauses), range(2)):
        assert not l(sol)

    l = Linear([(0, 12), (0, 14), (0, 22), (0, 59), (0, 60), (0, 68), (0,
        102), (0, 105), (0, 164), (0, 176), (0, 178), (0, 180), (0, 182), (1,
            9), (1, 13), (1, 21), (1, 58), (1, 67), (1, 101), (1, 104), (1,
                163), (1, 175), (1, 177), (1, 179), (1, 181), (2, 6), (2, 20),
        (2, 57), (2, 66), (2, 100), (2, 103), (2, 162), (2, 174), (3, 11), (3,
            19), (3, 56), (3, 65), (3, 99), (3, 161), (3, 173), (4, 8), (4,
                18), (4, 55), (4, 64), (4, 98), (4, 160), (4, 172), (5, 5),
        (5, 17), (5, 54), (5, 63), (5, 97), (5, 159), (5, 171), (6, 10), (6,
            16), (6, 52), (6, 62), (6, 96), (6, 158), (6, 170), (7, 7), (7,
                15), (7, 50), (7, 61), (7, 95), (7, 157), (7, 169), (8, 4),
        (8, 48), (8, 94), (8, 156), (8, 168), (9, 3), (9, 46), (9, 93), (9,
            155), (9, 167), (10, 2), (10, 53), (10, 92), (10, 154), (10, 166),
        (11, 1), (11, 51), (11, 91), (11, 152), (11, 165), (12, 49), (12, 90),
        (12, 150), (13, 47), (13, 89), (13, 148), (14, 45), (14, 88), (14,
            146), (15, 39), (15, 87), (15, 144), (16, 38), (16, 86), (16,
                142), (17, 37), (17, 85), (17, 140), (18, 44), (18, 84), (18,
                    138), (19, 43), (19, 83), (19, 153), (20, 42), (20, 82),
        (20, 151), (21, 41), (21, 81), (21, 149), (22, 40), (22, 80), (22,
            147), (23, 36), (23, 79), (23, 145), (24, 32), (24, 70), (24,
                143), (25, 35), (25, 78), (25, 141), (26, 34), (26, 77), (26,
                    139), (27, 31), (27, 76), (27, 137), (28, 30), (28, 75),
        (28, 136), (29, 33), (29, 74), (29, 135), (30, 29), (30, 73), (30,
            134), (31, 28), (31, 72), (31, 133), (32, 27), (32, 71), (32,
                132), (33, 25), (33, 69), (33, 131), (34, 24), (34, 130), (35,
                    26), (35, 129), (36, 23), (36, 128), (37, 125), (38, 124),
        (39, 123), (40, 122), (41, 121), (42, 120), (43, 119), (44, 118), (45,
            117), (46, 116), (47, 115), (48, 114), (49, 113), (50, 127), (51,
                126), (52, 112), (53, 111), (54, 110), (55, 109), (56, 108),
        (57, 107), (58, 106)], [21, 40])

    C = Clauses(max(l.atoms))
    print('building sorter')
    m = C.build_sorter(l)
    if l.rhs[0]:
        x = {(m[l.rhs[0]-1],), (-m[l.rhs[1]],)}
        nx = {(-m[l.rhs[0]-1], m[l.rhs[1]])}
    else:
        x = {(-m[l.rhs[1]],)}
        nx = {(m[l.rhs[1]],)}
    print('checking positive solutions')
    for sol, _ in zip(my_itersolve(x | C.clauses), range(2)):
        assert l(sol)
    print('checking negative solutions')
    for sol, _ in zip(my_itersolve(nx | C.clauses), range(2)):
        assert not l(sol)

    C = Clauses(0)
    assert C.build_sorter([]) == []
    assert not C.clauses

########NEW FILE########
__FILENAME__ = test_misc
import unittest

from conda.fetch import cache_fn_url


class TestMisc(unittest.TestCase):

    def test_cache_fn_url(self):
        url = "http://repo.continuum.io/pkgs/pro/osx-64/"
        self.assertEqual(cache_fn_url(url),
                         '7618c8b65f9329feb96d07caa0751cc6.json')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_plan
import json
import unittest
from os.path import dirname, join

from conda.config import default_python, pkgs_dirs
from conda.install import LINK_HARD
import conda.plan as plan
from conda.resolve import Resolve


with open(join(dirname(__file__), 'index.json')) as fi:
    r = Resolve(json.load(fi))

def solve(specs):
    return [fn[:-8] for fn in r.solve(specs)]


class TestMisc(unittest.TestCase):

    def test_split_linkarg(self):
        for arg, res in [
            ('w3-1.2-0', ('w3-1.2-0', pkgs_dirs[0], LINK_HARD)),
            ('w3-1.2-0 /opt/pkgs 1', ('w3-1.2-0', '/opt/pkgs', 1)),
            (' w3-1.2-0  /opt/pkgs  1  ', ('w3-1.2-0', '/opt/pkgs', 1)),
            (r'w3-1.2-0 C:\A B\pkgs 2', ('w3-1.2-0', r'C:\A B\pkgs', 2))]:
            self.assertEqual(plan.split_linkarg(arg), res)


class TestAddDeaultsToSpec(unittest.TestCase):
    # tests for plan.add_defaults_to_specs(r, linked, specs)

    def check(self, specs, added):
        new_specs = list(specs + added)
        plan.add_defaults_to_specs(r, self.linked, specs)
        self.assertEqual(specs, new_specs)

    def test_1(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        for specs, added in [
            (['python 3*'],  []),
            (['python'],     ['python 2.7*']),
            (['scipy'],      ['python 2.7*']),
            ]:
            self.check(specs, added)

    def test_2(self):
        self.linked = solve(['anaconda 1.5.0', 'python 2.6*', 'numpy 1.6*'])
        for specs, added in [
            (['python'],     ['python 2.6*']),
            (['numpy'],      ['python 2.6*']),
            (['pandas'],     ['python 2.6*']),
            # however, this would then be unsatisfiable
            (['python 3*', 'numpy'], []),
            ]:
            self.check(specs, added)

    def test_3(self):
        self.linked = solve(['anaconda 1.5.0', 'python 3.3*'])
        for specs, added in [
            (['python'],     ['python 3.3*']),
            (['numpy'],      ['python 3.3*']),
            (['scipy'],      ['python 3.3*']),
            ]:
            self.check(specs, added)

    def test_4(self):
        self.linked = []
        ps = ['python 2.7*'] if default_python == '2.7' else []
        for specs, added in [
            (['python'],     ps),
            (['numpy'],      ps),
            (['scipy'],      ps),
            (['anaconda'],   ps),
            (['anaconda 1.5.0 np17py27_0'], []),
            (['sympy 0.7.2 py27_0'], []),
            (['scipy 0.12.0 np16py27_0'], []),
            (['anaconda', 'python 3*'], []),
            ]:
            self.check(specs, added)

########NEW FILE########
__FILENAME__ = test_resolve
from __future__ import print_function, absolute_import
import json
import unittest
from os.path import dirname, join

from conda.resolve import ver_eval, VersionSpec, MatchSpec, Package, Resolve, NoPackagesFound

from .helpers import raises


with open(join(dirname(__file__), 'index.json')) as fi:
    index = json.load(fi)

r = Resolve(index)

f_mkl = set(['mkl'])


class TestVersionSpec(unittest.TestCase):

    def test_ver_eval(self):
        self.assertEqual(ver_eval('1.7.0', '==1.7'), True)
        self.assertEqual(ver_eval('1.7.0', '<1.7'), False)
        self.assertEqual(ver_eval('1.7.0', '>=1.7'), True)
        self.assertEqual(ver_eval('1.6.7', '>=1.7'), False)
        self.assertEqual(ver_eval('2013a', '>2013b'), False)
        self.assertEqual(ver_eval('2013k', '>2013b'), True)
        self.assertEqual(ver_eval('3.0.0', '>2013b'), True)

    def test_ver_eval_errors(self):
        self.assertRaises(RuntimeError, ver_eval, '3.0.0', '><2.4.5')
        self.assertRaises(RuntimeError, ver_eval, '3.0.0', '!!2.4.5')
        self.assertRaises(RuntimeError, ver_eval, '3.0.0', '!')

    def test_match(self):
        for vspec, res in [
            ('1.7*', True),   ('1.7.1', True),    ('1.7.0', False),
            ('1.7', False),   ('1.5*', False),    ('>=1.5', True),
            ('!=1.5', True),  ('!=1.7.1', False), ('==1.7.1', True),
            ('==1.7', False), ('==1.7.2', False), ('==1.7.1.0', True),
            ]:
            m = VersionSpec(vspec)
            self.assertEqual(m.match('1.7.1'), res)


class TestMatchSpec(unittest.TestCase):

    def test_match(self):
        for spec, res in [
            ('numpy 1.7*', True),          ('numpy 1.7.1', True),
            ('numpy 1.7', False),          ('numpy 1.5*', False),
            ('numpy >=1.5', True),         ('numpy >=1.5,<2', True),
            ('numpy >=1.8,<1.9', False),   ('numpy >1.5,<2,!=1.7.1', False),
            ('numpy >1.8,<2|==1.7', False),('numpy >1.8,<2|>=1.7.1', True),
            ('numpy >=1.8|1.7*', True),    ('numpy ==1.7', False),
            ('numpy >=1.5,>1.6', True),    ('numpy ==1.7.1', True),
            ('numpy 1.6*|1.7*', True),     ('numpy 1.6*|1.8*', False),
            ('numpy 1.6.2|1.7*', True),    ('numpy 1.6.2|1.7.1', True),
            ('numpy 1.6.2|1.7.0', False),  ('numpy 1.7.1 py27_0', True),
            ('numpy 1.7.1 py26_0', False), ('python', False),
            ]:
            m = MatchSpec(spec)
            self.assertEqual(m.match('numpy-1.7.1-py27_0.tar.bz2'), res)

    def test_to_filename(self):
        ms = MatchSpec('foo 1.7 52')
        self.assertEqual(ms.to_filename(), 'foo-1.7-52.tar.bz2')

        for spec in 'bitarray', 'pycosat 0.6.0', 'numpy 1.6*':
            ms = MatchSpec(spec)
            self.assertEqual(ms.to_filename(), None)

    def test_hash(self):
        a, b = MatchSpec('numpy 1.7*'), MatchSpec('numpy 1.7*')
        self.assertTrue(a is not b)
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        c, d = MatchSpec('python'), MatchSpec('python 2.7.4')
        self.assertNotEqual(a, c)
        self.assertNotEqual(hash(a), hash(c))


class TestPackage(unittest.TestCase):

    def test_llvm(self):
        ms = MatchSpec('llvm')
        pkgs = [Package(fn, r.index[fn]) for fn in r.find_matches(ms)]
        pkgs.sort()
        self.assertEqual([p.fn for p in pkgs],
                         ['llvm-3.1-0.tar.bz2',
                          'llvm-3.1-1.tar.bz2',
                          'llvm-3.2-0.tar.bz2'])

    def test_different_names(self):
        pkgs = [Package(fn, r.index[fn]) for fn in [
                'llvm-3.1-1.tar.bz2', 'python-2.7.5-0.tar.bz2']]
        self.assertRaises(TypeError, pkgs.sort)


class TestSolve(unittest.TestCase):

    def setUp(self):
        r.msd_cache = {}

    def assert_have_mkl(self, dists, names):
        for fn in dists:
            if fn.rsplit('-', 2)[0] in names:
                self.assertEqual(r.features(fn), f_mkl)

    def test_explicit0(self):
        self.assertEqual(r.explicit([]), [])

    def test_explicit1(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0']), None)
        self.assertEqual(r.explicit(['zlib']), None)
        self.assertEqual(r.explicit(['zlib 1.2.7']), None)
        # because zlib has no dependencies it is also explicit
        self.assertEqual(r.explicit(['zlib 1.2.7 0']),
                         ['zlib-1.2.7-0.tar.bz2'])

    def test_explicit2(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
                                     'zlib 1.2.7 0']),
                         ['pycosat-0.6.0-py27_0.tar.bz2',
                          'zlib-1.2.7-0.tar.bz2'])
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
                                     'zlib 1.2.7']), None)

    def test_empty(self):
        self.assertEqual(r.solve([]), [])

    def test_anaconda_14(self):
        specs = ['anaconda 1.4.0 np17py33_0']
        res = r.explicit(specs)
        self.assertEqual(len(res), 51)
        self.assertEqual(r.solve(specs), res)
        specs.append('python 3.3*')
        self.assertEqual(r.explicit(specs), None)
        self.assertEqual(r.solve(specs), res)

    def test_iopro_nomkl(self):
        self.assertEqual(
            r.solve2(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
                     set(), returnall=True),
            [['iopro-1.4.3-np17py27_p0.tar.bz2',
              'numpy-1.7.1-py27_0.tar.bz2',
              'openssl-1.0.1c-0.tar.bz2',
              'python-2.7.5-0.tar.bz2',
              'readline-6.2-0.tar.bz2',
              'sqlite-3.7.13-0.tar.bz2',
              'system-5.8-1.tar.bz2',
              'tk-8.5.13-0.tar.bz2',
              'unixodbc-2.3.1-0.tar.bz2',
              'zlib-1.2.7-0.tar.bz2']])

    def test_iopro_mkl(self):
        self.assertEqual(
            r.solve2(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
                    f_mkl, returnall=True),
            [['iopro-1.4.3-np17py27_p0.tar.bz2',
              'mkl-rt-11.0-p0.tar.bz2',
              'numpy-1.7.1-py27_p0.tar.bz2',
              'openssl-1.0.1c-0.tar.bz2',
              'python-2.7.5-0.tar.bz2',
              'readline-6.2-0.tar.bz2',
              'sqlite-3.7.13-0.tar.bz2',
              'system-5.8-1.tar.bz2',
              'tk-8.5.13-0.tar.bz2',
              'unixodbc-2.3.1-0.tar.bz2',
                'zlib-1.2.7-0.tar.bz2']])

    def test_mkl(self):
        self.assertEqual(r.solve(['mkl'], set()),
                         r.solve(['mkl'], f_mkl))

    def test_accelerate(self):
        self.assertEqual(
            r.solve(['accelerate'], set()),
            r.solve(['accelerate'], f_mkl))

    def test_scipy_mkl(self):
        dists = r.solve(['scipy', 'python 2.7*', 'numpy 1.7*'],
                        features=f_mkl)
        self.assert_have_mkl(dists, ('numpy', 'scipy'))
        self.assertTrue('scipy-0.12.0-np17py27_p0.tar.bz2' in dists)

    def test_anaconda_nomkl(self):
        dists = r.solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        self.assertEqual(len(dists), 107)
        self.assertTrue('scipy-0.12.0-np17py27_0.tar.bz2' in dists)

    def test_anaconda_mkl_2(self):
        # to test "with_features_depends"
        dists = r.solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'],
                        features=f_mkl)
        self.assert_have_mkl(dists,
                             ('numpy', 'scipy', 'numexpr', 'scikit-learn'))
        self.assertTrue('scipy-0.12.0-np17py27_p0.tar.bz2' in dists)
        self.assertTrue('mkl-rt-11.0-p0.tar.bz2' in dists)
        self.assertEqual(len(dists), 108)

        dists2 = r.solve(['anaconda 1.5.0',
                          'python 2.7*', 'numpy 1.7*', 'mkl'])
        self.assertTrue(set(dists) <= set(dists2))
        self.assertEqual(len(dists2), 110)

    def test_anaconda_mkl_3(self):
        # to test "with_features_depends"
        dists = r.solve(['anaconda 1.5.0', 'python 3*'], features=f_mkl)
        self.assert_have_mkl(dists, ('numpy', 'scipy'))
        self.assertTrue('scipy-0.12.0-np17py33_p0.tar.bz2' in dists)
        self.assertTrue('mkl-rt-11.0-p0.tar.bz2' in dists)
        self.assertEqual(len(dists), 61)


class TestFindSubstitute(unittest.TestCase):

    def setUp(self):
        r.msd_cache = {}

    def test1(self):
        installed = r.solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'],
                            features=f_mkl)
        for old, new in [('numpy-1.7.1-py27_p0.tar.bz2',
                          'numpy-1.7.1-py27_0.tar.bz2'),
                         ('scipy-0.12.0-np17py27_p0.tar.bz2',
                          'scipy-0.12.0-np17py27_0.tar.bz2'),
                         ('mkl-rt-11.0-p0.tar.bz2', None)]:
            self.assertTrue(old in installed)
            self.assertEqual(r.find_substitute(installed, f_mkl, old), new)

def test_pseudo_boolean():
    # The latest version of iopro, 1.5.0, was not built against numpy 1.5
    for alg in ['sorter', 'BDD']: #, 'BDD_recursive']:
        assert r.solve2(['iopro', 'python 2.7*', 'numpy 1.5*'], set(),
            alg=alg, returnall=True) == [[
            'iopro-1.4.3-np15py27_p0.tar.bz2',
            'numpy-1.5.1-py27_4.tar.bz2',
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.7.5-0.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'unixodbc-2.3.1-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
        ]]

    for alg in ['sorter', 'BDD']: #, 'BDD_recursive']:
        assert r.solve2(['iopro', 'python 2.7*', 'numpy 1.5*'], f_mkl,
            alg=alg, returnall=True) == [[
            'iopro-1.4.3-np15py27_p0.tar.bz2',
            'mkl-rt-11.0-p0.tar.bz2',
            'numpy-1.5.1-py27_p4.tar.bz2',
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.7.5-0.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'unixodbc-2.3.1-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
        ]]

def test_get_dists():
    r.msd_cache = {}
    dists = r.get_dists(["anaconda 1.5.0"])
    assert 'anaconda-1.5.0-np17py27_0.tar.bz2' in dists
    assert 'dynd-python-0.3.0-np17py33_0.tar.bz2' in dists
    for d in dists:
        assert dists[d].fn == d

def test_generate_eq():
    r.msd_cache = {}

    dists = r.get_dists(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
    v = {}
    w = {}
    for i, fn in enumerate(sorted(dists)):
        v[fn] = i + 1
        w[i + 1] = fn

    eq, max_rhs = r.generate_version_eq(v, dists, include0=True)
    e = [(i, w[j]) for i, j in eq]
    # Should satisfy the following criteria:
    # - lower versions of the same package should should have higher
    #   coefficients.
    # - the same versions of the same package (e.g., different build strings)
    #   should have the same coefficients.
    # - a package that only has one version should not appear, as it will have
    #   a 0 coefficient. The same is true of the latest version of a package.
    # The actual order may be arbitrary, so we compare sets
    assert e == [
        (0, '_license-1.1-py27_0.tar.bz2'),
        (0, 'anaconda-1.5.0-np16py26_0.tar.bz2'),
        (0, 'anaconda-1.5.0-np16py27_0.tar.bz2'),
        (0, 'anaconda-1.5.0-np17py26_0.tar.bz2'),
        (0, 'anaconda-1.5.0-np17py27_0.tar.bz2'),
        (0, 'anaconda-1.5.0-np17py33_0.tar.bz2'),
        (0, 'argparse-1.2.1-py26_0.tar.bz2'),
        (0, 'astropy-0.2.1-np16py26_0.tar.bz2'),
        (0, 'astropy-0.2.1-np16py27_0.tar.bz2'),
        (0, 'astropy-0.2.1-np17py26_0.tar.bz2'),
        (0, 'astropy-0.2.1-np17py27_0.tar.bz2'),
        (0, 'astropy-0.2.1-np17py33_0.tar.bz2'),
        (0, 'atom-0.2.3-py26_0.tar.bz2'),
        (0, 'atom-0.2.3-py27_0.tar.bz2'),
        (0, 'biopython-1.61-np16py26_0.tar.bz2'),
        (0, 'biopython-1.61-np16py27_0.tar.bz2'),
        (0, 'biopython-1.61-np17py26_0.tar.bz2'),
        (0, 'biopython-1.61-np17py27_0.tar.bz2'),
        (0, 'bitarray-0.8.1-py26_0.tar.bz2'),
        (0, 'bitarray-0.8.1-py27_0.tar.bz2'),
        (0, 'bitarray-0.8.1-py33_0.tar.bz2'),
        (0, 'boto-2.9.2-py26_0.tar.bz2'),
        (0, 'boto-2.9.2-py27_0.tar.bz2'),
        (0, 'cairo-1.12.2-1.tar.bz2'),
        (0, 'casuarius-1.1-py26_0.tar.bz2'),
        (0, 'casuarius-1.1-py27_0.tar.bz2'),
        (0, 'conda-1.5.2-py27_0.tar.bz2'),
        (0, 'cubes-0.10.2-py27_1.tar.bz2'),
        (0, 'curl-7.30.0-0.tar.bz2'),
        (0, 'cython-0.19-py26_0.tar.bz2'),
        (0, 'cython-0.19-py27_0.tar.bz2'),
        (0, 'cython-0.19-py33_0.tar.bz2'),
        (0, 'dateutil-2.1-py26_1.tar.bz2'),
        (0, 'dateutil-2.1-py27_1.tar.bz2'),
        (0, 'dateutil-2.1-py33_1.tar.bz2'),
        (0, 'disco-0.4.4-py26_0.tar.bz2'),
        (0, 'disco-0.4.4-py27_0.tar.bz2'),
        (0, 'distribute-0.6.36-py26_1.tar.bz2'),
        (0, 'distribute-0.6.36-py27_1.tar.bz2'),
        (0, 'distribute-0.6.36-py33_1.tar.bz2'),
        (0, 'docutils-0.10-py26_0.tar.bz2'),
        (0, 'docutils-0.10-py27_0.tar.bz2'),
        (0, 'docutils-0.10-py33_0.tar.bz2'),
        (0, 'dynd-python-0.3.0-np17py26_0.tar.bz2'),
        (0, 'dynd-python-0.3.0-np17py27_0.tar.bz2'),
        (0, 'dynd-python-0.3.0-np17py33_0.tar.bz2'),
        (0, 'enaml-0.7.6-py27_0.tar.bz2'),
        (0, 'erlang-R15B01-0.tar.bz2'),
        (0, 'flask-0.9-py26_0.tar.bz2'),
        (0, 'flask-0.9-py27_0.tar.bz2'),
        (0, 'freetype-2.4.10-0.tar.bz2'),
        (0, 'gevent-0.13.8-py26_0.tar.bz2'),
        (0, 'gevent-0.13.8-py27_0.tar.bz2'),
        (0, 'gevent-websocket-0.3.6-py26_2.tar.bz2'),
        (0, 'gevent-websocket-0.3.6-py27_2.tar.bz2'),
        (0, 'gevent_zeromq-0.2.5-py26_2.tar.bz2'),
        (0, 'gevent_zeromq-0.2.5-py27_2.tar.bz2'),
        (0, 'greenlet-0.4.0-py26_0.tar.bz2'),
        (0, 'greenlet-0.4.0-py27_0.tar.bz2'),
        (0, 'greenlet-0.4.0-py33_0.tar.bz2'),
        (0, 'grin-1.2.1-py26_1.tar.bz2'),
        (0, 'grin-1.2.1-py27_1.tar.bz2'),
        (0, 'h5py-2.1.1-np16py26_0.tar.bz2'),
        (0, 'h5py-2.1.1-np16py27_0.tar.bz2'),
        (0, 'h5py-2.1.1-np17py26_0.tar.bz2'),
        (0, 'h5py-2.1.1-np17py27_0.tar.bz2'),
        (0, 'hdf5-1.8.9-0.tar.bz2'),
        (0, 'imaging-1.1.7-py26_2.tar.bz2'),
        (0, 'imaging-1.1.7-py27_2.tar.bz2'),
        (0, 'ipython-0.13.2-py26_0.tar.bz2'),
        (0, 'ipython-0.13.2-py27_0.tar.bz2'),
        (0, 'ipython-0.13.2-py33_0.tar.bz2'),
        (0, 'jinja2-2.6-py26_0.tar.bz2'),
        (0, 'jinja2-2.6-py27_0.tar.bz2'),
        (0, 'jinja2-2.6-py33_0.tar.bz2'),
        (0, 'jpeg-8d-0.tar.bz2'),
        (0, 'libdynd-0.3.0-0.tar.bz2'),
        (0, 'libevent-2.0.20-0.tar.bz2'),
        (0, 'libnetcdf-4.2.1.1-1.tar.bz2'),
        (0, 'libpng-1.5.13-1.tar.bz2'),
        (0, 'libxml2-2.9.0-0.tar.bz2'),
        (0, 'libxslt-1.1.28-0.tar.bz2'),
        (0, 'llvm-3.2-0.tar.bz2'),
        (0, 'llvmpy-0.11.2-py26_0.tar.bz2'),
        (0, 'llvmpy-0.11.2-py27_0.tar.bz2'),
        (0, 'llvmpy-0.11.2-py33_0.tar.bz2'),
        (0, 'lxml-3.2.0-py26_0.tar.bz2'),
        (0, 'lxml-3.2.0-py27_0.tar.bz2'),
        (0, 'lxml-3.2.0-py33_0.tar.bz2'),
        (0, 'matplotlib-1.2.1-np16py26_1.tar.bz2'),
        (0, 'matplotlib-1.2.1-np16py27_1.tar.bz2'),
        (0, 'matplotlib-1.2.1-np17py26_1.tar.bz2'),
        (0, 'matplotlib-1.2.1-np17py27_1.tar.bz2'),
        (0, 'matplotlib-1.2.1-np17py33_1.tar.bz2'),
        (0, 'mdp-3.3-np16py26_0.tar.bz2'),
        (0, 'mdp-3.3-np16py27_0.tar.bz2'),
        (0, 'mdp-3.3-np17py26_0.tar.bz2'),
        (0, 'mdp-3.3-np17py27_0.tar.bz2'),
        (0, 'mdp-3.3-np17py33_0.tar.bz2'),
        (0, 'meta-0.4.2.dev-py27_0.tar.bz2'),
        (0, 'mkl-10.3-p2.tar.bz2'),
        (1, 'mkl-10.3-p1.tar.bz2'),
        (2, 'mkl-10.3-0.tar.bz2'),
        (0, 'mkl-rt-11.0-p0.tar.bz2'),
        (0, 'mpi4py-1.3-py26_0.tar.bz2'),
        (0, 'mpi4py-1.3-py27_0.tar.bz2'),
        (0, 'mpich2-1.4.1p1-0.tar.bz2'),
        (0, 'netcdf4-1.0.4-np16py26_0.tar.bz2'),
        (0, 'netcdf4-1.0.4-np16py27_0.tar.bz2'),
        (0, 'netcdf4-1.0.4-np17py26_0.tar.bz2'),
        (0, 'netcdf4-1.0.4-np17py27_0.tar.bz2'),
        (0, 'netcdf4-1.0.4-np17py33_0.tar.bz2'),
        (0, 'networkx-1.7-py26_0.tar.bz2'),
        (0, 'networkx-1.7-py27_0.tar.bz2'),
        (0, 'networkx-1.7-py33_0.tar.bz2'),
        (0, 'nltk-2.0.4-np16py26_0.tar.bz2'),
        (0, 'nltk-2.0.4-np16py27_0.tar.bz2'),
        (0, 'nltk-2.0.4-np17py26_0.tar.bz2'),
        (0, 'nltk-2.0.4-np17py27_0.tar.bz2'),
        (0, 'nose-1.3.0-py26_0.tar.bz2'),
        (0, 'nose-1.3.0-py27_0.tar.bz2'),
        (0, 'nose-1.3.0-py33_0.tar.bz2'),
        (1, 'nose-1.2.1-py26_0.tar.bz2'),
        (1, 'nose-1.2.1-py27_0.tar.bz2'),
        (1, 'nose-1.2.1-py33_0.tar.bz2'),
        (2, 'nose-1.1.2-py26_0.tar.bz2'),
        (2, 'nose-1.1.2-py27_0.tar.bz2'),
        (2, 'nose-1.1.2-py33_0.tar.bz2'),
        (0, 'numba-0.8.1-np16py26_0.tar.bz2'),
        (0, 'numba-0.8.1-np16py27_0.tar.bz2'),
        (0, 'numba-0.8.1-np17py26_0.tar.bz2'),
        (0, 'numba-0.8.1-np17py27_0.tar.bz2'),
        (0, 'numba-0.8.1-np17py33_0.tar.bz2'),
        (0, 'numexpr-2.0.1-np16py26_3.tar.bz2'),
        (0, 'numexpr-2.0.1-np16py27_3.tar.bz2'),
        (0, 'numexpr-2.0.1-np17py26_3.tar.bz2'),
        (0, 'numexpr-2.0.1-np17py27_3.tar.bz2'),
        (0, 'numpy-1.7.1-py26_0.tar.bz2'),
        (0, 'numpy-1.7.1-py26_p0.tar.bz2'),
        (0, 'numpy-1.7.1-py27_0.tar.bz2'),
        (0, 'numpy-1.7.1-py27_p0.tar.bz2'),
        (0, 'numpy-1.7.1-py33_0.tar.bz2'),
        (0, 'numpy-1.7.1-py33_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py26_0.tar.bz2'),
        (1, 'numpy-1.7.0-py26_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py27_0.tar.bz2'),
        (1, 'numpy-1.7.0-py27_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py33_0.tar.bz2'),
        (1, 'numpy-1.7.0-py33_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py26_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py26_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py27_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py27_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py33_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py33_p0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py26_ce0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py26_pro0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py27_ce0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py27_pro0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py33_pro0.tar.bz2'),
        (4, 'numpy-1.6.2-py26_4.tar.bz2'),
        (4, 'numpy-1.6.2-py27_4.tar.bz2'),
        (0, 'opencv-2.4.2-np16py26_1.tar.bz2'),
        (0, 'opencv-2.4.2-np16py27_1.tar.bz2'),
        (0, 'opencv-2.4.2-np17py26_1.tar.bz2'),
        (0, 'opencv-2.4.2-np17py27_1.tar.bz2'),
        (0, 'openssl-1.0.1c-0.tar.bz2'),
        (0, 'ordereddict-1.1-py26_0.tar.bz2'),
        (0, 'pandas-0.11.0-np16py26_1.tar.bz2'),
        (0, 'pandas-0.11.0-np16py27_1.tar.bz2'),
        (0, 'pandas-0.11.0-np17py26_1.tar.bz2'),
        (0, 'pandas-0.11.0-np17py27_1.tar.bz2'),
        (0, 'pandas-0.11.0-np17py33_1.tar.bz2'),
        (0, 'pip-1.3.1-py26_1.tar.bz2'),
        (0, 'pip-1.3.1-py27_1.tar.bz2'),
        (0, 'pip-1.3.1-py33_1.tar.bz2'),
        (0, 'pixman-0.26.2-0.tar.bz2'),
        (0, 'ply-3.4-py26_0.tar.bz2'),
        (0, 'ply-3.4-py27_0.tar.bz2'),
        (0, 'ply-3.4-py33_0.tar.bz2'),
        (0, 'psutil-0.7.1-py26_0.tar.bz2'),
        (0, 'psutil-0.7.1-py27_0.tar.bz2'),
        (0, 'psutil-0.7.1-py33_0.tar.bz2'),
        (0, 'py-1.4.12-py26_0.tar.bz2'),
        (0, 'py-1.4.12-py27_0.tar.bz2'),
        (0, 'py2cairo-1.10.0-py26_1.tar.bz2'),
        (0, 'py2cairo-1.10.0-py27_1.tar.bz2'),
        (0, 'pycosat-0.6.0-py26_0.tar.bz2'),
        (0, 'pycosat-0.6.0-py27_0.tar.bz2'),
        (0, 'pycosat-0.6.0-py33_0.tar.bz2'),
        (0, 'pycparser-2.9.1-py26_0.tar.bz2'),
        (0, 'pycparser-2.9.1-py27_0.tar.bz2'),
        (0, 'pycparser-2.9.1-py33_0.tar.bz2'),
        (0, 'pycrypto-2.6-py26_0.tar.bz2'),
        (0, 'pycrypto-2.6-py27_0.tar.bz2'),
        (0, 'pycrypto-2.6-py33_0.tar.bz2'),
        (0, 'pycurl-7.19.0-py26_2.tar.bz2'),
        (0, 'pycurl-7.19.0-py27_2.tar.bz2'),
        (0, 'pyflakes-0.7.2-py26_0.tar.bz2'),
        (0, 'pyflakes-0.7.2-py27_0.tar.bz2'),
        (0, 'pyflakes-0.7.2-py33_0.tar.bz2'),
        (0, 'pygments-1.6-py26_0.tar.bz2'),
        (0, 'pygments-1.6-py27_0.tar.bz2'),
        (0, 'pygments-1.6-py33_0.tar.bz2'),
        (0, 'pyparsing-1.5.6-py26_0.tar.bz2'),
        (0, 'pyparsing-1.5.6-py27_0.tar.bz2'),
        (0, 'pysal-1.5.0-np16py27_1.tar.bz2'),
        (0, 'pysal-1.5.0-np17py27_1.tar.bz2'),
        (0, 'pysam-0.6-py26_0.tar.bz2'),
        (0, 'pysam-0.6-py27_0.tar.bz2'),
        (0, 'pyside-1.1.2-py27_0.tar.bz2'),
        (0, 'pytables-2.4.0-np16py26_0.tar.bz2'),
        (0, 'pytables-2.4.0-np16py27_0.tar.bz2'),
        (0, 'pytables-2.4.0-np17py26_0.tar.bz2'),
        (0, 'pytables-2.4.0-np17py27_0.tar.bz2'),
        (0, 'pytest-2.3.4-py26_1.tar.bz2'),
        (0, 'pytest-2.3.4-py27_1.tar.bz2'),
        (0, 'python-3.3.2-0.tar.bz2'),
        (1, 'python-3.3.1-0.tar.bz2'),
        (2, 'python-3.3.0-4.tar.bz2'),
        (3, 'python-3.3.0-3.tar.bz2'),
        (4, 'python-3.3.0-2.tar.bz2'),
        (5, 'python-3.3.0-pro1.tar.bz2'),
        (6, 'python-3.3.0-pro0.tar.bz2'),
        (7, 'python-2.7.5-0.tar.bz2'),
        (8, 'python-2.7.4-0.tar.bz2'),
        (9, 'python-2.7.3-7.tar.bz2'),
        (10, 'python-2.7.3-6.tar.bz2'),
        (11, 'python-2.7.3-5.tar.bz2'),
        (12, 'python-2.7.3-4.tar.bz2'),
        (13, 'python-2.7.3-3.tar.bz2'),
        (14, 'python-2.7.3-2.tar.bz2'),
        (15, 'python-2.6.8-6.tar.bz2'),
        (16, 'python-2.6.8-5.tar.bz2'),
        (17, 'python-2.6.8-4.tar.bz2'),
        (18, 'python-2.6.8-3.tar.bz2'),
        (19, 'python-2.6.8-2.tar.bz2'),
        (20, 'python-2.6.8-1.tar.bz2'),
        (0, 'pytz-2013b-py26_0.tar.bz2'),
        (0, 'pytz-2013b-py27_0.tar.bz2'),
        (0, 'pytz-2013b-py33_0.tar.bz2'),
        (0, 'pyyaml-3.10-py26_0.tar.bz2'),
        (0, 'pyyaml-3.10-py27_0.tar.bz2'),
        (0, 'pyyaml-3.10-py33_0.tar.bz2'),
        (0, 'pyzmq-2.2.0.1-py26_1.tar.bz2'),
        (0, 'pyzmq-2.2.0.1-py27_1.tar.bz2'),
        (0, 'pyzmq-2.2.0.1-py33_1.tar.bz2'),
        (0, 'qt-4.7.4-0.tar.bz2'),
        (0, 'readline-6.2-0.tar.bz2'),
        (0, 'redis-2.6.9-0.tar.bz2'),
        (0, 'redis-py-2.7.2-py26_0.tar.bz2'),
        (0, 'redis-py-2.7.2-py27_0.tar.bz2'),
        (0, 'requests-1.2.0-py26_0.tar.bz2'),
        (0, 'requests-1.2.0-py27_0.tar.bz2'),
        (0, 'requests-1.2.0-py33_0.tar.bz2'),
        (0, 'rope-0.9.4-py27_0.tar.bz2'),
        (0, 'scikit-image-0.8.2-np16py26_1.tar.bz2'),
        (0, 'scikit-image-0.8.2-np16py27_1.tar.bz2'),
        (0, 'scikit-image-0.8.2-np17py26_1.tar.bz2'),
        (0, 'scikit-image-0.8.2-np17py27_1.tar.bz2'),
        (0, 'scikit-image-0.8.2-np17py33_1.tar.bz2'),
        (0, 'scikit-learn-0.13.1-np16py26_0.tar.bz2'),
        (0, 'scikit-learn-0.13.1-np16py27_0.tar.bz2'),
        (0, 'scikit-learn-0.13.1-np17py26_0.tar.bz2'),
        (0, 'scikit-learn-0.13.1-np17py27_0.tar.bz2'),
        (0, 'scipy-0.12.0-np16py26_0.tar.bz2'),
        (0, 'scipy-0.12.0-np16py27_0.tar.bz2'),
        (0, 'scipy-0.12.0-np17py26_0.tar.bz2'),
        (0, 'scipy-0.12.0-np17py27_0.tar.bz2'),
        (0, 'scipy-0.12.0-np17py33_0.tar.bz2'),
        (0, 'shiboken-1.1.2-py27_0.tar.bz2'),
        (0, 'six-1.3.0-py26_0.tar.bz2'),
        (0, 'six-1.3.0-py27_0.tar.bz2'),
        (0, 'six-1.3.0-py33_0.tar.bz2'),
        (0, 'sphinx-1.1.3-py26_3.tar.bz2'),
        (0, 'sphinx-1.1.3-py27_3.tar.bz2'),
        (0, 'sphinx-1.1.3-py33_3.tar.bz2'),
        (0, 'spyder-2.2.0-py27_0.tar.bz2'),
        (0, 'sqlalchemy-0.8.1-py26_0.tar.bz2'),
        (0, 'sqlalchemy-0.8.1-py27_0.tar.bz2'),
        (0, 'sqlalchemy-0.8.1-py33_0.tar.bz2'),
        (0, 'sqlite-3.7.13-0.tar.bz2'),
        (0, 'statsmodels-0.4.3-np16py26_1.tar.bz2'),
        (0, 'statsmodels-0.4.3-np16py27_1.tar.bz2'),
        (0, 'statsmodels-0.4.3-np17py26_1.tar.bz2'),
        (0, 'statsmodels-0.4.3-np17py27_1.tar.bz2'),
        (0, 'sympy-0.7.2-py26_0.tar.bz2'),
        (0, 'sympy-0.7.2-py27_0.tar.bz2'),
        (0, 'sympy-0.7.2-py33_0.tar.bz2'),
        (0, 'system-5.8-1.tar.bz2'),
        (1, 'system-5.8-0.tar.bz2'),
        (0, 'theano-0.5.0-np16py26_1.tar.bz2'),
        (0, 'theano-0.5.0-np16py27_1.tar.bz2'),
        (0, 'theano-0.5.0-np17py26_1.tar.bz2'),
        (0, 'theano-0.5.0-np17py27_1.tar.bz2'),
        (0, 'tk-8.5.13-0.tar.bz2'),
        (0, 'tornado-3.0.1-py26_0.tar.bz2'),
        (0, 'tornado-3.0.1-py27_0.tar.bz2'),
        (0, 'tornado-3.0.1-py33_0.tar.bz2'),
        (0, 'util-linux-2.21-0.tar.bz2'),
        (0, 'werkzeug-0.8.3-py26_0.tar.bz2'),
        (0, 'werkzeug-0.8.3-py27_0.tar.bz2'),
        (0, 'xlrd-0.9.2-py26_0.tar.bz2'),
        (0, 'xlrd-0.9.2-py27_0.tar.bz2'),
        (0, 'xlrd-0.9.2-py33_0.tar.bz2'),
        (0, 'xlwt-0.7.5-py26_0.tar.bz2'),
        (0, 'xlwt-0.7.5-py27_0.tar.bz2'),
        (0, 'yaml-0.1.4-0.tar.bz2'),
        (0, 'zeromq-2.2.0-1.tar.bz2'),
        (0, 'zlib-1.2.7-0.tar.bz2'),
    ]

    assert max_rhs == 20 + 4 + 2 + 2 + 1

    eq, max_rhs = r.generate_version_eq(v, dists)
    assert all(i > 0 for i, _ in eq)
    e = [(i, w[j]) for i, j in eq]

    assert e == [
        (1, 'mkl-10.3-p1.tar.bz2'),
        (2, 'mkl-10.3-0.tar.bz2'),
        (1, 'nose-1.2.1-py26_0.tar.bz2'),
        (1, 'nose-1.2.1-py27_0.tar.bz2'),
        (1, 'nose-1.2.1-py33_0.tar.bz2'),
        (2, 'nose-1.1.2-py26_0.tar.bz2'),
        (2, 'nose-1.1.2-py27_0.tar.bz2'),
        (2, 'nose-1.1.2-py33_0.tar.bz2'),
        (1, 'numpy-1.7.0-py26_0.tar.bz2'),
        (1, 'numpy-1.7.0-py26_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py27_0.tar.bz2'),
        (1, 'numpy-1.7.0-py27_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py33_0.tar.bz2'),
        (1, 'numpy-1.7.0-py33_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py26_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py26_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py27_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py27_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py33_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py33_p0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py26_ce0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py26_pro0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py27_ce0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py27_pro0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py33_pro0.tar.bz2'),
        (4, 'numpy-1.6.2-py26_4.tar.bz2'),
        (4, 'numpy-1.6.2-py27_4.tar.bz2'),
        (1, 'python-3.3.1-0.tar.bz2'),
        (2, 'python-3.3.0-4.tar.bz2'),
        (3, 'python-3.3.0-3.tar.bz2'),
        (4, 'python-3.3.0-2.tar.bz2'),
        (5, 'python-3.3.0-pro1.tar.bz2'),
        (6, 'python-3.3.0-pro0.tar.bz2'),
        (7, 'python-2.7.5-0.tar.bz2'),
        (8, 'python-2.7.4-0.tar.bz2'),
        (9, 'python-2.7.3-7.tar.bz2'),
        (10, 'python-2.7.3-6.tar.bz2'),
        (11, 'python-2.7.3-5.tar.bz2'),
        (12, 'python-2.7.3-4.tar.bz2'),
        (13, 'python-2.7.3-3.tar.bz2'),
        (14, 'python-2.7.3-2.tar.bz2'),
        (15, 'python-2.6.8-6.tar.bz2'),
        (16, 'python-2.6.8-5.tar.bz2'),
        (17, 'python-2.6.8-4.tar.bz2'),
        (18, 'python-2.6.8-3.tar.bz2'),
        (19, 'python-2.6.8-2.tar.bz2'),
        (20, 'python-2.6.8-1.tar.bz2'),
        (1, 'system-5.8-0.tar.bz2')
    ]

    assert max_rhs == 20 + 4 + 2 + 2 + 1

def test_unsat():
    r.msd_cache = {}

    # scipy 0.12.0b1 is not built for numpy 1.5, only 1.6 and 1.7
    assert raises((RuntimeError, SystemExit), lambda: r.solve(['numpy 1.5*', 'scipy 0.12.0b1']), 'conflict')
    # numpy 1.5 does not have a python 3 package
    assert raises((RuntimeError, SystemExit), lambda: r.solve(['numpy 1.5*', 'python 3*']), 'conflict')
    assert raises((RuntimeError, SystemExit), lambda: r.solve(['numpy 1.5*', 'numpy 1.6*']), 'conflict')

def test_nonexistent():
    r.msd_cache = {}

    assert raises(NoPackagesFound, lambda: r.solve(['notarealpackage 2.0*']), 'No packages found')
    # This exact version of NumPy does not exist
    assert raises(NoPackagesFound, lambda: r.solve(['numpy 1.5']), 'No packages found')

def test_nonexistent_deps():
    index2 = index.copy()
    index2['mypackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    }
    index2['mypackage-1.1-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    }
    index2['anotherpackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.1'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.1'],
        'version': '1.0',
    }
    index2['anotherpackage-2.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    }
    r = Resolve(index2)

    assert set(r.find_matches(MatchSpec('mypackage'))) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
    }
    assert set(r.get_dists(['mypackage']).keys()) == {
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.1.2-py26_0.tar.bz2',
        'nose-1.1.2-py27_0.tar.bz2',
        'nose-1.1.2-py33_0.tar.bz2',
        'nose-1.2.1-py26_0.tar.bz2',
        'nose-1.2.1-py27_0.tar.bz2',
        'nose-1.2.1-py33_0.tar.bz2',
        'nose-1.3.0-py26_0.tar.bz2',
        'nose-1.3.0-py27_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.6.8-1.tar.bz2',
        'python-2.6.8-2.tar.bz2',
        'python-2.6.8-3.tar.bz2',
        'python-2.6.8-4.tar.bz2',
        'python-2.6.8-5.tar.bz2',
        'python-2.6.8-6.tar.bz2',
        'python-2.7.3-2.tar.bz2',
        'python-2.7.3-3.tar.bz2',
        'python-2.7.3-4.tar.bz2',
        'python-2.7.3-5.tar.bz2',
        'python-2.7.3-6.tar.bz2',
        'python-2.7.3-7.tar.bz2',
        'python-2.7.4-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'python-3.3.0-2.tar.bz2',
        'python-3.3.0-3.tar.bz2',
        'python-3.3.0-4.tar.bz2',
        'python-3.3.0-pro0.tar.bz2',
        'python-3.3.0-pro1.tar.bz2',
        'python-3.3.1-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    }

    assert set(r.get_dists(['mypackage'], max_only=True).keys()) == {
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py26_0.tar.bz2',
        'nose-1.3.0-py27_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.6.8-6.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    }

    assert r.solve(['mypackage']) == r.solve(['mypackage 1.1']) == [
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]
    assert raises(NoPackagesFound, lambda: r.solve(['mypackage 1.0']))

    assert r.solve(['anotherpackage 1.0']) == [
        'anotherpackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]

    assert r.solve(['anotherpackage']) == [
        'anotherpackage-2.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]

    # This time, the latest version is messed up
    index3 = index.copy()
    index3['mypackage-1.1-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    }
    index3['mypackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    }
    index3['anotherpackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.0'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.0'],
        'version': '1.0',
    }
    index3['anotherpackage-2.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    }
    r = Resolve(index3)

    assert set(r.find_matches(MatchSpec('mypackage'))) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        }
    assert set(r.get_dists(['mypackage']).keys()) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.1.2-py26_0.tar.bz2',
        'nose-1.1.2-py27_0.tar.bz2',
        'nose-1.1.2-py33_0.tar.bz2',
        'nose-1.2.1-py26_0.tar.bz2',
        'nose-1.2.1-py27_0.tar.bz2',
        'nose-1.2.1-py33_0.tar.bz2',
        'nose-1.3.0-py26_0.tar.bz2',
        'nose-1.3.0-py27_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.6.8-1.tar.bz2',
        'python-2.6.8-2.tar.bz2',
        'python-2.6.8-3.tar.bz2',
        'python-2.6.8-4.tar.bz2',
        'python-2.6.8-5.tar.bz2',
        'python-2.6.8-6.tar.bz2',
        'python-2.7.3-2.tar.bz2',
        'python-2.7.3-3.tar.bz2',
        'python-2.7.3-4.tar.bz2',
        'python-2.7.3-5.tar.bz2',
        'python-2.7.3-6.tar.bz2',
        'python-2.7.3-7.tar.bz2',
        'python-2.7.4-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'python-3.3.0-2.tar.bz2',
        'python-3.3.0-3.tar.bz2',
        'python-3.3.0-4.tar.bz2',
        'python-3.3.0-pro0.tar.bz2',
        'python-3.3.0-pro1.tar.bz2',
        'python-3.3.1-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    }

    assert raises(NoPackagesFound, lambda: r.get_dists(['mypackage'], max_only=True))

    assert r.solve(['mypackage']) == r.solve(['mypackage 1.0']) == [
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]
    assert raises(NoPackagesFound, lambda: r.solve(['mypackage 1.1']))


    assert r.solve(['anotherpackage 1.0']) == [
        'anotherpackage-1.0-py33_0.tar.bz2',
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]

    # If recursive checking is working correctly, this will give
    # anotherpackage 2.0, not anotherpackage 1.0
    assert r.solve(['anotherpackage']) == [
        'anotherpackage-2.0-py33_0.tar.bz2',
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]

def test_circular_dependencies():
    index2 = index.copy()
    index2['package1-1.0-0.tar.bz2'] = {
        'build': '0',
        'build_number': 0,
        'depends': ['package2'],
        'name': 'package1',
        'requires': ['package2'],
        'version': '1.0',
    }
    index2['package2-1.0-0.tar.bz2'] = {
        'build': '0',
        'build_number': 0,
        'depends': ['package1'],
        'name': 'package2',
        'requires': ['package1'],
        'version': '1.0',
    }
    r = Resolve(index2)

    assert set(r.find_matches(MatchSpec('package1'))) == {
        'package1-1.0-0.tar.bz2',
    }
    assert set(r.get_dists(['package1']).keys()) == {
        'package1-1.0-0.tar.bz2',
        'package2-1.0-0.tar.bz2',
    }
    assert r.solve(['package1']) == r.solve(['package2']) == \
        r.solve(['package1', 'package2']) == [
        'package1-1.0-0.tar.bz2',
        'package2-1.0-0.tar.bz2',
    ]


def test_package_ordering():
    sympy_071 = Package('sympy-0.7.1-py27_0.tar.bz2', r.index['sympy-0.7.1-py27_0.tar.bz2'])
    sympy_072 = Package('sympy-0.7.2-py27_0.tar.bz2', r.index['sympy-0.7.2-py27_0.tar.bz2'])
    python_275 = Package('python-2.7.5-0.tar.bz2', r.index['python-2.7.5-0.tar.bz2'])
    numpy = Package('numpy-1.7.1-py27_0.tar.bz2', r.index['numpy-1.7.1-py27_0.tar.bz2'])
    numpy_mkl = Package('numpy-1.7.1-py27_p0.tar.bz2', r.index['numpy-1.7.1-py27_p0.tar.bz2'])

    assert sympy_071 < sympy_072
    assert not sympy_071 < sympy_071
    assert not sympy_072 < sympy_071
    raises(TypeError, lambda: sympy_071 < python_275)

    assert sympy_071 <= sympy_072
    assert sympy_071 <= sympy_071
    assert not sympy_072 <= sympy_071
    assert raises(TypeError, lambda: sympy_071 <= python_275)

    assert sympy_071 == sympy_071
    assert not sympy_071 == sympy_072
    assert (sympy_071 == python_275) is False
    assert (sympy_071 == 1) is False

    assert not sympy_071 != sympy_071
    assert sympy_071 != sympy_072
    assert (sympy_071 != python_275) is True

    assert not sympy_071 > sympy_072
    assert not sympy_071 > sympy_071
    assert sympy_072 > sympy_071
    raises(TypeError, lambda: sympy_071 > python_275)

    assert not sympy_071 >= sympy_072
    assert sympy_071 >= sympy_071
    assert sympy_072 >= sympy_071
    assert raises(TypeError, lambda: sympy_071 >= python_275)

    # The first four are a bit arbitrary. For now, we just test that it
    # doesn't prefer the mkl version.
    assert not numpy < numpy_mkl
    assert not numpy <= numpy_mkl
    assert numpy > numpy_mkl
    assert numpy >= numpy_mkl
    assert (numpy != numpy_mkl) is True
    assert (numpy == numpy_mkl) is False

def test_irrational_version():
    r.msd_cache = {}

    # verlib.NormalizedVersion('2012d') raises IrrationalVersionError.
    assert r.solve2(['pytz 2012d', 'python 3*'], set(), returnall=True) == [[
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'pytz-2012d-py33_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2'
    ]]

def test_no_features():
    # Features that aren't specified shouldn't be selected.
    r.msd_cache = {}

    # Without this, there would be another solution including 'scipy-0.11.0-np16py26_p3.tar.bz2'.
    assert r.solve2(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'], set(),
        returnall=True) == [[
            'numpy-1.6.2-py26_4.tar.bz2',
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.6.8-6.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'scipy-0.11.0-np16py26_3.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]

    assert r.solve2(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'], f_mkl,
        returnall=True) == [[
            'mkl-rt-11.0-p0.tar.bz2',           # This,
            'numpy-1.6.2-py26_p4.tar.bz2',      # this,
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.6.8-6.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'scipy-0.11.0-np16py26_p3.tar.bz2', # and this are different.
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]

########NEW FILE########
__FILENAME__ = smoketest
import os
import subprocess as sp
import sys
import time

from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp

base = mkdtemp()
myenv = join(base, "env")

if 'win' in sys.platform and 'dar' not in sys.platform:
    status = True
    pandas = numba = '0.10.1'
    cython = '0.18'
else:
    status = False
    pandas = '0.8.1'
    numba  = '0.1.1'
    cython = '0.16'


# CIO_TEST needs to be set to 2 if any of the packages tested below are only found in the test repo.

# os.environ['CIO_TEST'] = 2

cmds = [
    "info",
    "list ^m.*lib$",
    "search ^m.*lib$",
    "search -v numpy",
    "search -c numpy",
    "info -e",
    "create --yes -p %s sqlite python=2.6" % myenv,
    "install --yes -p %s pandas=%s" % (myenv, pandas),
    "remove --yes -p %s pandas" % myenv,
    "install --yes -p %s numba=%s" % (myenv, numba),
    "install --yes -p %s cython=%s" % (myenv, cython),
    "remove --yes -p %s cython" % myenv,
    "install --yes -p %s accelerate" % myenv,
    "remove --yes -p %s accelerate" % myenv,
    "install --yes -p %s mkl" % myenv,
    "remove --yes -p %s mkl" % myenv,
    "update --yes -p %s numba" % myenv,
    "remove --yes -p %s numba" % myenv,
    "install --yes -p %s iopro" % myenv,
    "remove --yes -p %s iopro" % myenv,
    "info -e",
    "info -a",
    "info --license",
    "info -s",
]

def tester(commands):
    cmds = commands
    errs  = []
    fails = []
    for cmd in cmds:
        cmd = "conda %s" % cmd
        print("-"*len(cmd))
        print("%s" % cmd)
        print("-"*len(cmd))
        try:
            child = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE, shell=status)
            data, err = child.communicate()
            ret = child.returncode
            if ret != 0:
                print("\nFAILED\n")
                errs.append("\n%s\n \n%s" % (cmd, err))
                fails.append(cmd)
            else:
                print("\nPASSED\n")
        except Exception as e:
            print(e)
            errs.append("\nThe script had the following error running %s: %s" % (cmd, e))

    return (fails, errs)


if __name__ == '__main__':

    TESTLOG = 'conda-testlog.txt'

    if len(sys.argv) > 1:
        options = True

    if options and 'new' in sys.argv:
        if exists(TESTLOG):
            os.remove(TESTLOG)

    fails, errs = tester(cmds)
    if fails:
        print("These commands failed: \n")
        for line, fail in enumerate(fails, 1):
            print("%d: %s\n" % (line, fail))
        header = 'Test Results For %s' % time.asctime()
        if options and 'log' in sys.argv:
            print("Writing failed commands to conda-testlog.txt")
            with open(TESTLOG, "a") as f:
                f.write('%s\n%s\n' % (header, '-'*len(header)))
                for error in errs:
                    f.write(error)

    try:
        rmtree(myenv)
    except:
        pass

########NEW FILE########
__FILENAME__ = win_batlink
# UNUSED MODULE
"""
Generate batch scripts to allow conda to update Python in the root
environment in Windows.  conda cannot do this because it itself runs in
Python, and Windows will not allow writing to a dll that is open.

The scripts should remain as small as possible. Only those things that conda
itself cannot do should be in them. The rest should be done by conda.

The way this works is that when conda comes to an action that it cannot
perform (such as linking Python in the root environment), it serializes the
actions that it cannot perform into a batch script (that's what's done here in
this module), performs the rest of the actions that it can perform, calls this
script, and exits (see conda.plan.execute_plan()).

Implementation wise, the action serialization is just a custom batch file that
does the linking/unlinking of everything in the package list, written to
%PREFIX%\batlink.bat (note, we can assume that we have write permissions to
%PREFIX% because otherwise we wouldn't be able to install in the root
environment anyway (this issue only comes up when installing into the root
environment)). conda calls this script and exits.

Notes:

- `mklink /H` creates a hardlink on Windows NT 6.0 and later (i.e., Windows
Vista or later)
- On older systems, like Windows XP, `fsutil.exe hardlink create` creates
hard links.
- In either case, the order of the arguments is backwards: dest source

"""

from os.path import join, abspath, split
from distutils.spawn import find_executable

# Redirect stderr on the mkdirs to ignore errors about directories that
# already exist
BAT_LINK_HEADER = """\

{mkdirs}


{links}

"""

# Hide stderr for this one because it warns about nonempty directories, like
# C:\Anaconda.
BAT_UNLINK_HEADER = """\
{filedeletes}

{dirdeletes}

"""

WINXP_LINK = "fsutil.exe hardlink create {dest} {source}"

WINVISTA_LINK = "mklink /H {dest} {source}"

MAKE_DIR = "mkdir {dst_dir}"

FILE_DELETE = "del /Q {dest}"

DIR_DELETE = "rmdir /Q {dest}"


def make_bat_link(files, prefix, dist_dir):
    links = []
    has_mklink = find_executable('mklink')
    LINK =  WINVISTA_LINK if has_mklink else WINXP_LINK
    dirs = set()
    for file in files:
        source = abspath(join(dist_dir, file))
        fdn, fbn = split(file)
        dst_dir = join(prefix, fdn)
        dirs.add(abspath(dst_dir))
        dest = abspath(join(dst_dir, fbn))
        links.append(LINK.format(source=source, dest=dest))

    # mkdir will make intermediate directories, so we do not need to care
    # about the order
    mkdirs = [MAKE_DIR.format(dst_dir=dn) for dn in dirs]

    batchfile = BAT_LINK_HEADER.format(links='\n'.join(links),
                                       mkdirs='\n'.join(mkdirs))

    return batchfile


def make_bat_unlink(files, directories, prefix, dist_dir):
    filedeletes = [FILE_DELETE.format(dest=abspath(file)) for file in files]
    dirdeletes = [DIR_DELETE.format(dest=abspath(dir)) for dir in directories]
    batchfile = BAT_UNLINK_HEADER.format(filedeletes='\n'.join(filedeletes),
                                         dirdeletes='\n'.join(dirdeletes))

    return batchfile


def should_do_win_subprocess(cmd, arg, prefix):
    """
    If the cmd needs to call out to a separate process on Windows (because the
    Windows file lock prevents Python from updating itself).
    """
    return (
        cmd in ('LINK', 'UNLINK') and
        install.on_win and
        abspath(prefix) == abspath(sys.prefix) and
        arg.rsplit('-', 2)[0] in install.win_ignore
    )

def win_subprocess_re_sort(plan, prefix):
    # TODO: Fix the progress numbers
    newplan = []
    winplan = []
    for line in plan:
        cmd_arg = cmds_from_plan([line])
        if cmd_arg:
            [[cmd, arg]] = cmd_arg
        else:
            continue
        if should_do_win_subprocess(cmd, arg, prefix=prefix):
            if cmd == LINK:
                # The one post-link action that we need to worry about
                newplan.append("CREATEMETA %s" % arg)
            winplan.append(line)
        else:
            newplan.append(line)

    return newplan, winplan


def test_win_subprocess(prefix):
    """
    Make sure the windows subprocess stuff will work before we try it.
    """
    import subprocess
    from conda.win_batlink import make_bat_link, make_bat_unlink
    from conda.builder.utils import rm_rf

    try:
        print("Testing if we can install certain packages")
        batfiles = ['ping 1.1.1.1 -n 1 -w 3000 > nul']
        dist_dir = join(config.pkgs_dir, 'battest_pkg', 'battest')

        # First create a file in the prefix.
        print("making file in the prefix")
        prefix_battest = join(prefix, 'battest')
        print("making directories")
        os.makedirs(join(prefix, 'battest'))
        print("making file")
        with open(join(prefix_battest, 'battest1'), 'w') as f:
            f.write('test1')
        print("testing file")
        with open(join(prefix_battest, 'battest1')) as f:
            assert f.read() == 'test1'

        # Now unlink it.
        print("making unlink command")
        batfiles.append(make_bat_unlink([join(prefix_battest, 'battest1')],
        [prefix_battest], prefix, dist_dir))

        # Now create a file in the pkgs dir
        print("making file in pkgs dir")
        print("making directories")
        os.makedirs(join(dist_dir, 'battest'))
        print("making file")
        with open(join(dist_dir, 'battest', 'battest2'), 'w') as f:
            f.write('test2')
        print("testing file")
        with open(join(dist_dir, 'battest', 'battest2')) as f:
            assert f.read() == 'test2'

        # And link it
        print("making link command")
        batfiles.append(make_bat_link([join('battest', 'battest2')],
                                      prefix, dist_dir))

        batfile = '\n'.join(batfiles)

        print("writing batlink_test.bat file")
        with open(join(prefix, 'batlink_test.bat'), 'w') as f:
            f.write(batfile)
        print("running batlink_test.bat file")
        subprocess.check_call([join(prefix, 'batlink_test.bat')])

        print("testing result")
        print("testing if old file does not exist")
        assert not os.path.exists(join(prefix_battest, 'battest1'))
        print("testing if new file does exist")
        assert os.path.exists(join(prefix_battest, 'battest2'))
        print("testing content of installed file")
        with open(join(prefix_battest, 'battest2')) as f:
            assert f.read() == 'test2'
        print("testing content of pkg file")
        with open(join(dist_dir, 'battest', 'battest2')) as f:
            assert f.read() == 'test2'

    finally:
        try:
            print("cleaning up")
            rm_rf(join(prefix, 'battest'))
            rm_rf(join(config.pkgs_dir, 'battest_pkg'))
            rm_rf(join(prefix, 'batlink_test.bat'))
        except Exception as e:
            print(e)


def win_subprocess_write_bat(cmd, arg, prefix, plan):
    assert sys.platform == 'win32'

    import json
    from conda.win_batlink import make_bat_link, make_bat_unlink

    dist_dir = join(config.pkgs_dir, arg)
    info_dir = join(dist_dir, 'info')

    if cmd == LINK:
        files = list(install.yield_lines(join(info_dir, 'files')))

        return make_bat_link(files, prefix, dist_dir)

    elif cmd == UNLINK:
        meta_path = join(prefix, 'conda-meta', arg + '.json')
        with open(meta_path) as fi:
            meta = json.load(fi)

        files = set([])
        directories1 = set([])
        for f in meta['files']:
            dst = abspath(join(prefix, f))
            files.add(dst)
            directories1.add(dirname(dst))
        files.add(meta_path)

        directories = set([])
        for path in directories1:
            while len(path) > len(prefix):
                directories.add(path)
                path = dirname(path)
        directories.add(join(prefix, 'conda-meta'))
        directories.add(prefix)

        directories = sorted(directories, key=len, reverse=True)

        return make_bat_unlink(files, directories, prefix, dist_dir)
    else:
        raise ValueError


def do_win_subprocess(batfile, prefix):
    import subprocess
    with open(join(prefix, 'batlink.bat'), 'w') as f:
        f.write(batfile)
    print("running subprocess")
    subprocess.Popen([join(prefix, 'batlink.bat')])
    # If we ever hit a race condition, maybe we should use atexit
    sys.exit(0)

########NEW FILE########
__FILENAME__ = versioneer
#! /usr/bin/python

"""versioneer.py

(like a rocketeer, but for versions)

* https://github.com/warner/python-versioneer
* Brian Warner
* License: Public Domain
* Version: 0.7+

This file helps distutils-based projects manage their version number by just
creating version-control tags.

For developers who work from a VCS-generated tree (e.g. 'git clone' etc),
each 'setup.py version', 'setup.py build', 'setup.py sdist' will compute a
version number by asking your version-control tool about the current
checkout. The version number will be written into a generated _version.py
file of your choosing, where it can be included by your __init__.py

For users who work from a VCS-generated tarball (e.g. 'git archive'), it will
compute a version number by looking at the name of the directory created when
te tarball is unpacked. This conventionally includes both the name of the
project and a version number.

For users who work from a tarball built by 'setup.py sdist', it will get a
version number from a previously-generated _version.py file.

As a result, loading code directly from the source tree will not result in a
real version. If you want real versions from VCS trees (where you frequently
update from the upstream repository, or do new development), you will need to
do a 'setup.py version' after each update, and load code from the build/
directory.

You need to provide this code with a few configuration values:

 versionfile_source:
    A project-relative pathname into which the generated version strings
    should be written. This is usually a _version.py next to your project's
    main __init__.py file. If your project uses src/myproject/__init__.py,
    this should be 'src/myproject/_version.py'. This file should be checked
    in to your VCS as usual: the copy created below by 'setup.py
    update_files' will include code that parses expanded VCS keywords in
    generated tarballs. The 'build' and 'sdist' commands will replace it with
    a copy that has just the calculated version string.

 versionfile_build:
    Like versionfile_source, but relative to the build directory instead of
    the source directory. These will differ when your setup.py uses
    'package_dir='. If you have package_dir={'myproject': 'src/myproject'},
    then you will probably have versionfile_build='myproject/_version.py' and
    versionfile_source='src/myproject/_version.py'.

 tag_prefix: a string, like 'PROJECTNAME-', which appears at the start of all
             VCS tags. If your tags look like 'myproject-1.2.0', then you
             should use tag_prefix='myproject-'. If you use unprefixed tags
             like '1.2.0', this should be an empty string.

 parentdir_prefix: a string, frequently the same as tag_prefix, which
                   appears at the start of all unpacked tarball filenames. If
                   your tarball unpacks into 'myproject-1.2.0', this should
                   be 'myproject-'.

To use it:

 1: include this file in the top level of your project
 2: make the following changes to the top of your setup.py:
     import versioneer
     versioneer.versionfile_source = 'src/myproject/_version.py'
     versioneer.versionfile_build = 'myproject/_version.py'
     versioneer.tag_prefix = '' # tags are like 1.2.0
     versioneer.parentdir_prefix = 'myproject-' # dirname like 'myproject-1.2.0'
 3: add the following arguments to the setup() call in your setup.py:
     version=versioneer.get_version(),
     cmdclass=versioneer.get_cmdclass(),
 4: run 'setup.py update_files', which will create _version.py, and will
    append the following to your __init__.py:
     from _version import __version__
 5: modify your MANIFEST.in to include versioneer.py
 6: add both versioneer.py and the generated _version.py to your VCS
"""

import os
import sys
import re
import subprocess
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None

VCS = "git"
IN_LONG_VERSION_PY = False
GIT = "git"


LONG_VERSION_PY = '''
IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by github's download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"


import subprocess
import sys

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %%s" %% args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %%s (error)" %% args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%%s', no digits" %% ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %%d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %%s" %% ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %%s" %% r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %%s" %% root)
        return {}

    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.exe"
    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%%s' doesn't start with prefix '%%s'" %% (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%%s', but '%%s' doesn't start with prefix '%%s'" %%
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver

'''

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%s', no digits" % ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %s" % ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}


def do_vcs_install(versionfile_source, ipy):
    run_command([GIT, "add", "versioneer.py"])
    run_command([GIT, "add", versionfile_source])
    run_command([GIT, "add", ipy])
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        run_command([GIT, "add", ".gitattributes"])


SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (0.7+) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        f = open(filename)
    except EnvironmentError:
        return versions
    for line in f.readlines():
        mo = re.match("version_version = '([^']+)'", line)
        if mo:
            versions["version"] = mo.group(1)
        mo = re.match("version_full = '([^']+)'", line)
        if mo:
            versions["full"] = mo.group(1)
    return versions

def write_to_version_file(filename, versions):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % versions)
    f.close()
    print("set %s to '%s'" % (filename, versions["version"]))


def get_best_versions(versionfile, tag_prefix, parentdir_prefix,
                      default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    #
    # extract version from first of _version.py, 'git describe', parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature.

    variables = get_expanded_variables(versionfile_source)
    if variables:
        ver = versions_from_expanded_variables(variables, tag_prefix)
        if ver:
            if verbose: print("got version from expanded variable %s" % ver)
            return ver

    ver = versions_from_file(versionfile)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile, ver))
        return ver

    ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if ver:
        if verbose: print("got version from git %s" % ver)
        return ver

    ver = versions_from_parentdir(parentdir_prefix, versionfile_source, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % ver)
    return default

def get_versions(default=DEFAULT, verbose=False):
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    return get_best_versions(versionfile_source, tag_prefix, parentdir_prefix,
                             default=default, verbose=verbose)
def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % versions)
        f.close()

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "modify __init__.py and create _version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        print(" creating %s" % versionfile_source)
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                   "TAG_PREFIX": tag_prefix,
                                   "PARENTDIR_PREFIX": parentdir_prefix,
                                   "VERSIONFILE_SOURCE": versionfile_source,
                                   })
        f.close()
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print(" %s unmodified" % ipy)
        do_vcs_install(versionfile_source, ipy)

def get_cmdclass():
    return {'version': cmd_version,
            'update_files': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }

########NEW FILE########
