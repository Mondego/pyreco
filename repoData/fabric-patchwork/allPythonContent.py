__FILENAME__ = auth
from fabric.api import sudo, hide

from patchwork.files import append


def _keyfile(who):
    return "/home/%s/.ssh/authorized_keys" % who


def copy_pubkey(from_, to):
    """
    Copy remote user ``from_``'s authorized keys to user ``to``.

    I.e. allow ``from_`` to SSH into the server as ``to``.
    """
    with hide('stdout'):
        append(
            filename=_keyfile(to),
            # Leading newline to ensure keys stay separate
            text=['\n'] + sudo("cat %s" % _keyfile(from_)).splitlines(),
            runner=sudo
        )

########NEW FILE########
__FILENAME__ = commands
"""
Command execution "super-tasks" - combining put/get/run/sudo, etc.
"""
from __future__ import with_statement

import os

from fabric.api import run, put, settings, cd


def run_script(source, cwd, binary='bash', runner=run):
    """
    Invoke local script file ``source`` in remote directory ``cwd``.

    Works by copying the file remotely, executing it, & removing it. Removal
    will always occur even if execution fails.

    :param source:
        Local path to script file; passed directly to
        ``fabric.operations.get``.
    :param cwd: Remote working directory to copy to & invoke script from.
    :param binary:
        Command to run remotely with the script as its argument. Defaults to
        ``'bash'``, meaning invocation will be e.g. ``bash myscript.sh``.
    :param runner:
        Fabric function call to use when invoking. Defaults to
        ``fabric.operations.run``.
    :rtype: Return value of the execution call.
    """
    fname = os.path.basename(source)
    put(source, cwd)
    with settings(cd(cwd), warn_only=True):
        result = runner("%s %s" % (binary, fname))
        runner("rm %s" % fname)
    return result
        

########NEW FILE########
__FILENAME__ = environment
"""
Shell environment introspection, e.g. binaries in effective $PATH, etc.
"""

from fabric.api import run, settings, hide


def has_binary(name, runner=run):
    with settings(hide('everything'), warn_only=True):
        return runner("which %s" % name).succeeded

########NEW FILE########
__FILENAME__ = files
import re

from fabric.api import run, settings, hide, run


def directory(d, user=None, group=None, mode=None, runner=run):
    """
    Ensure a directory exists and has given user and/or mode
    """
    runner("mkdir -p %s" % d)
    if user is not None:
        group = group or user
        runner("chown %s:%s %s" % (user, group, d))
    if mode is not None:
        runner("chmod %s %s" % (mode, d))


def exists(path, runner=run):
    """
    Return True if given path exists on the current remote host.
    """
    cmd = 'test -e "$(echo %s)"' % path
    with settings(hide('everything'), warn_only=True):
        return runner(cmd).succeeded


def contains(filename, text, exact=False, escape=True, runner=run):
    """
    Return True if ``filename`` contains ``text`` (which may be a regex.)

    By default, this function will consider a partial line match (i.e. where
    ``text`` only makes up part of the line it's on). Specify ``exact=True`` to
    change this behavior so that only a line containing exactly ``text``
    results in a True return value.

    This function leverages ``egrep`` on the remote end (so it may not follow
    Python regular expression syntax perfectly), and skips the usual outer
    ``env.shell`` wrapper that most commands execute with.

    If ``escape`` is False, no extra regular expression related escaping is
    performed (this includes overriding ``exact`` so that no ``^``/``$`` is
    added.)
    """
    if escape:
        text = _escape_for_regex(text)
        if exact:
            text = "^%s$" % text
    with settings(hide('everything'), warn_only=True):
        egrep_cmd = 'egrep "%s" "%s"' % (text, filename)
        return runner(egrep_cmd, shell=False).succeeded


def append(filename, text, partial=False, escape=True, runner=run):
    """
    Append string (or list of strings) ``text`` to ``filename``.

    When a list is given, each string inside is handled independently (but in
    the order given.)

    If ``text`` is already found in ``filename``, the append is not run, and
    None is returned immediately. Otherwise, the given text is appended to the
    end of the given ``filename`` via e.g. ``echo '$text' >> $filename``.

    The test for whether ``text`` already exists defaults to a full line match,
    e.g. ``^<text>$``, as this seems to be the most sensible approach for the
    "append lines to a file" use case. You may override this and force partial
    searching (e.g. ``^<text>``) by specifying ``partial=True``.

    Because ``text`` is single-quoted, single quotes will be transparently 
    backslash-escaped. This can be disabled with ``escape=False``.
    """
    # Normalize non-list input to be a list
    if isinstance(text, basestring):
        text = [text]
    for line in text:
        regex = '^' + _escape_for_regex(line)  + ('' if partial else '$')
        if (exists(filename, runner=runner) and line
            and contains(filename, regex, escape=False, runner=runner)):
            continue
        line = line.replace("'", r"'\\''") if escape else line
        runner("echo '%s' >> %s" % (line, filename))


def _escape_for_regex(text):
    """Escape ``text`` to allow literal matching using egrep"""
    regex = re.escape(text)
    # Seems like double escaping is needed for \
    regex = regex.replace('\\\\', '\\\\\\')
    # Triple-escaping seems to be required for $ signs
    regex = regex.replace(r'\$', r'\\\$')
    # Whereas single quotes should not be escaped
    regex = regex.replace(r"\'", "'")
    return regex

########NEW FILE########
__FILENAME__ = info
from fabric.contrib.files import exists


def distro_name():
    """
    Return simple Linux distribution name identifier, e.g. ``"fedora"``.

    Uses tools like ``/etc/issue``, and ``lsb_release`` and fits the remote
    system into one of the following:

    * ``fedora``
    * ``rhel``
    * ``centos``
    * ``ubuntu``
    * ``debian``
    * ``other``
    """
    sentinel_files = {
        'fedora': ('fedora-release',),
        'centos': ('centos-release',),
    }
    for name, sentinels in sentinel_files.iteritems():
        for sentinel in sentinels:
            if exists('/etc/%s' % sentinel):
                return name
    return "other"


def distro_family():
    """
    Returns basic "family" ID for the remote system's distribution.

    Currently, options include:

    * ``debian``
    * ``redhat``
    
    If the system falls outside these categories, its specific family or
    release name will be returned instead.
    """
    families = {
        'debian': "debian ubuntu".split(),
        'redhat': "rhel centos fedora".split()
    }
    distro = distro_name()
    for family, members in families.iteritems():
        if distro in members:
            return family
    return distro

########NEW FILE########
__FILENAME__ = source
"""
Functions for configuring/compiling/installing/packaging source distributions.
"""

import posixpath

from fabric.api import run, cd, settings, abort

from ..files import directory, exists
from ..environment import has_binary
from . import package


def _run_step(name, forcing, sentinel=None):
    sentinel_present = exists(sentinel) if sentinel else False
    return forcing[name] or not sentinel_present

_go_msg = "++ %s: forced or sentinel missing, running..."

def clean(runner):
    runner("make clean")

def install(runner, stage_root):
    runner("DESTDIR=%s make install" % stage_root)


# TODO: maybe break this up into fewer, richer args? e.g. objects or dicts.
# Pro: smaller API
# Con: requires boilerplate for simple stuff
# TODO: great candidate for "collection of tasks" class based approach.
# TODO: also re: each step now looking very similar, at LEAST loop.
def build(name, version, iteration, workdir, uri, type_, enable=(), with_=(),
    flagstr="", dependencies=(), sentinels=None, clean=clean, install=install,
    force="", runner=run):
    """
    Build a package from source, using fpm.

    Keyword arguments:

    * ``name``: Shorthand project/package name. Used both for determining what
      file to download, and what the unpacked directory is expected to be.
      Example: ``"php"``, as found in ``"php-5.4.0.tar.gz"``.
    * ``version``: Upstream release version. Example: ``"5.4.0"``.
    * ``iteration``: Your own version for this build. Usually you'll want to
      increment this every time you're ready to actually distribute the package
      for real. Example: ``3``.
    * ``workdir``: Base working directory. Sources will be unpacked inside of
      it in their own directories, and the staging directory is created as a
      child of this directory as well. Example: ``"/opt/build"``.
    * ``uri``: Download URI. May (and probably should) contain interpolation
      syntax using the following keys:
      * ``name``: same as kwarg
      * ``version``: same as kwarg
      * ``package_name``: same as ``"%(name)s-%(version)s"``

      E.g. ``"http://php.net/get/%(package_name)s.tar.bz2/from/us.php.net/mirror"``
      or ``"http://my.mirror/packages/%(name)s/%(name)_%(version)s.tgz"``

    * ``type``: Package type to build. Passed directly to ``fpm``, so should be
      e.g. ``"deb"``, ``"rpm"`` etc.
    * ``enable`` and ``with_``: shorthand for adding configure flags. E.g.
      ``build(..., enable=['foo', 'bar'], with_=['biz'])`` results in adding
      the flags ``--enable-foo``, ``--enable-bar`` and ``--with-biz``.
    * ``flagstr``: Arbitrary additional configure flags to add, e.g.
      ``"--no-bad-stuff --with-blah=/usr/blah"``.
    * ``dependencies``: Package names to ensure are installed prior to
      building, using ``package()``.
    * ``sentinels``: Keys are steps, values should be paths (relative to the
      source directory unless otherwise specified) to files whose existence
      indicates a successful run of that step. For each given step, if
      ``force`` is not set (see below) and its ``sentinel`` value is non-empty
      and the file exists, that step will automatically be skipped.

      Per-step details:

      * ``"configure"``: Default value for this key is ``"Makefile"``. The
        other steps have no default values.
      * ``"stage"``: The path given here is considered relative to the staging
        directory, not the unpacked source directory.
      * ``"package"``: The path given here should be relative to ``workdir``.

    * ``clean``: Callback (given ``runner``) to execute when cleaning is
      needed. Defaults to a function that calls ``runner("make clean")``.
    * ``install``: Callback (given ``runner`` and ``stage_root``) to execute as
      the "install" step. Defaults to a function that calls
      ``runner("DESTDIR=<stage_root> make install")``

    May force a reset to one of the following steps by specifying ``force``:

    * ``"get"``: downloading the sources
    * ``"configure"``: ./configure --flags
    * ``"build"``: make
    * ``"stage"``: make install into staging directory
    * ``"package"``: staging directory => package file

    steps imply later ones, so force=stage will re-stage *and* re-package.
    Forcing will override any sentinel checks.
    """
    package_name = "%s-%s" % (name, version)
    context = {'name': name, 'version': version, 'package_name': package_name}
    uri = uri % context
    source = posixpath.join(workdir, package_name)
    stage = posixpath.join(workdir, 'stage')

    # Make sure we have fpm or the ability to install it
    # TODO: allow actual, non-staged make install which then doesn't need fpm
    # or the package/distribute steps.
    if not has_binary("fpm"):
        gems = " install Rubygems and then" if not has_binary("gem") else ""
        abort("No fpm found! Please%s 'gem install fpm'." % gems)

    # Default to empty dict (can't use in sig, dicts are mutable)
    sentinels = sentinels or {}
    # Fill in empty configure value
    if 'configure' not in sentinels:
        sentinels['configure'] = "Makefile"

    # Dependencies
    package(*dependencies)

    # Handle forcing
    forcing = {}
    force = force.split(',')
    reset = False
    for key in ('get', 'configure', 'build', 'stage', 'package'):
        if key in force:
            reset = True
        forcing[key] = reset

    # Directory
    # TODO: make the chmod an option if users want a "wide open" build dir for
    # manual login user poking around; default to not bothering.
    directory(workdir, mode="777", runner=runner)
    # Download+unpack
    if forcing['get'] or not exists(source):
        with cd(workdir):
            # TODO: make obtainment process overrideable for users who prefer
            # wget, scp, etc
            flag = ""
            if any([x in uri for x in (".tar.gz", ".tgz")]):
                flag = "z"
            elif any([x in uri for x in (".tar.bz2",)]):
                flag = "j"
            runner("curl -L \"%s\" | tar x%sf -" % (uri, flag))

    # Configure
    with_flags = map(lambda x: "--with-%s" % x, with_)
    enable_flags = map(lambda x: "--enable-%s" % x, enable)
    all_flags = " ".join([flagstr] + with_flags + enable_flags)
    with cd(source):
        # If forcing configure or build, clean up first. Leftover artifacts
        # from bad builds can be seriously annoying, especially if they don't
        # cause outright problems.
        if forcing['configure'] and exists('Makefile'):
            clean(runner)
        if _run_step('configure', forcing, sentinels['configure']):
            print _go_msg % 'configure'
            runner("./configure %s" % all_flags)
        else:
            print "!! Skipping configure step: %r exists." % sentinels['configure']

        # Build
        if _run_step('build', forcing, sentinels['build']):
            print _go_msg % 'build'
            runner("make")
        else:
            print "!! Skipping build step: %r exists" % sentinels['build']

        # Stage
        stage_sentinel = sentinels['stage']
        if stage_sentinel is not None:
            stage_sentinel = posixpath.join("..", stage, sentinels['stage'])
        if _run_step('stage', forcing, stage_sentinel):
            print _go_msg % 'stage'
            with settings(warn_only=True):
                # Nuke if forcing -- e.g. if --prefix changed, etc.
                # (Otherwise a prefix change would leave both prefixes in the
                # stage, causing problems on actual package install.)
                if forcing['stage']:
                    runner("rm -rf %s" % stage)
                install(runner=runner, stage_root=stage)
        else:
            print "!! Skipping stage step: %r exists" % sentinels['stage']

    with cd(workdir):
        do_package = _run_step('package', forcing, sentinels['package'])

    with cd(stage):
        # TODO: handle clean fpm integration somehow. probably have nice Python
        # level handles for the stuff like package name, version, iteration,
        # location, and add a new kwarg for rpm or deb specific things.
        # Main thing that needs doing is constructing an explicit package name
        # and making FPM use it, so one can reliably use that same name format
        # in eg Chef or Puppet.
        if do_package:
            print _go_msg % 'package'
            # --package <workdir> to control where package actually goes.
            # Filename format will be the default for the given output type.
            # Target directory is '.' since we're cd'd to stage root. Will then
            # work OK for any potential --prefix the user may have given.
            runner(r"""fpm \
                    -s dir \
                    -t %(type_)s \
                    --name %(name)s \
                    --version %(version)s \
                    --iteration %(iteration)s \
                    --package %(workdir)s \
                    .
            """ % locals()) # Yea, yea. Bite me.
        else:
            print "!! Skipping package step: %r exists" % sentinels['package']


    # TODO: a distribute step? Possibly too user-specific. Or make this a
    # class-based collection of subtasks and let them override that.

########NEW FILE########
__FILENAME__ = transfers
"""
File transfers, both those using Fabric's put/get, and otherwise.
"""

from fabric.api import local, env, hide
from fabric.network import key_filenames, normalize
from fabric.state import output


def rsync(source, target, exclude=(), delete=False, strict_host_keys=True,
    rsync_opts='', ssh_opts=''):
    """
    Convenient wrapper around your friendly local ``rsync``.

    Specifically, it calls your local ``rsync`` program via a subprocess, and
    fills in its arguments with Fabric's current target host/user/port. It
    provides Python level keyword arguments for some common rsync options, and
    allows you to specify custom options via a string if required (see below.)

    For details on how ``rsync`` works, please see its manpage. ``rsync`` must
    be installed on both your local and remote systems in order for this
    function to work correctly.

    This function makes use of Fabric's ``local()`` function and returns its
    output; thus it will exhibit ``failed``/``succeeded``/``stdout``/``stderr``
    attributes, behaves like a string consisting of ``stdout``, and so forth.

    ``rsync()`` takes the following parameters:

    * ``source``: The local location to copy from. Actually a string passed
      verbatim to ``rsync``, and thus may be a single directory
      (``"my_directory"``) or multiple directories (``"dir1 dir2"``). See the
      ``rsync`` documentation for details.
    * ``target``: The path to sync with on the remote server. Due to how
      ``rsync`` is implemented, the exact behavior depends on the value of
      ``source``:

        * If ``source`` ends with a trailing slash, the files will be
          dropped inside of ``target``. E.g.
          ``rsync("foldername/", "/home/username/project")`` will drop
          the contents of ``foldername`` inside of ``/home/username/project``.
        * If ``source`` does **not** end with a trailing slash,
          ``target`` is effectively the "parent" directory, and a new
          directory named after ``source`` will be created inside of it. So
          ``rsync("foldername", "/home/username")`` would create a new
          directory ``/home/username/foldername`` (if needed) and place the
          files there.

    * ``exclude``: optional, may be a single string, or an iterable of strings,
      and is used to pass one or more ``--exclude`` options to ``rsync``.
    * ``delete``: a boolean controlling whether ``rsync``'s ``--delete`` option
      is used. If True, instructs ``rsync`` to remove remote files that no
      longer exist locally. Defaults to False.
    * ``strict_host_keys``: Boolean determining whether to enable/disable the
      SSH-level option ``StrictHostKeyChecking`` (useful for
      frequently-changing hosts such as virtual machines or cloud instances.)
      Defaults to True.
    * ``rsync_opts``: an optional, arbitrary string which you may use to pass
      custom arguments or options to ``rsync``.
    * ``ssh_opts``: Like ``rsync_opts`` but specifically for the SSH options
      string (rsync's ``--rsh`` flag.)

    This function transparently honors Fabric's port and SSH key
    settings. Calling this function when the current host string contains a
    nonstandard port, or when ``env.key_filename`` is non-empty, will use the
    specified port and/or SSH key filename(s).

    For reference, the approximate ``rsync`` command-line call that is
    constructed by this function is the following::

        rsync [--delete] [--exclude exclude[0][, --exclude[1][, ...]]] \\
            -pthrvz [rsync_opts] <source> <host_string>:<target>

    """
    # Turn single-string exclude into a one-item list for consistency
    if not hasattr(exclude, '__iter__'):
        exclude = (exclude,)
    # Create --exclude options from exclude list
    exclude_opts = ' --exclude "%s"' * len(exclude)
    # Double-backslash-escape
    exclusions = tuple([str(s).replace('"', '\\\\"') for s in exclude])
    # Honor SSH key(s)
    key_string = ""
    keys = key_filenames()
    if keys:
        key_string = "-i " + " -i ".join(keys)
    # Port
    user, host, port = normalize(env.host_string)
    port_string = "-p %s" % port
    # Remote shell (SSH) options
    rsh_string = ""
    # Strict host key checking
    disable_keys = '-o StrictHostKeyChecking=no'
    if not strict_host_keys and disable_keys not in ssh_opts:
        ssh_opts += ' %s' % disable_keys
    rsh_parts = [key_string, port_string, ssh_opts]
    if any(rsh_parts):
        rsh_string = "--rsh='ssh %s'" % " ".join(rsh_parts)
    # Set up options part of string
    options_map = {
        'delete': '--delete' if delete else '',
        'exclude': exclude_opts % exclusions,
        'rsh': rsh_string,
        'extra': rsync_opts
    }
    options = "%(delete)s%(exclude)s -pthrvz %(extra)s %(rsh)s" % options_map
    # Create and run final command string
    if env.host.count(':') > 1:
        # Square brackets are mandatory for IPv6 rsync address,
        # even if port number is not specified
        cmd = "rsync %s %s [%s@%s]:%s" % (options, source, user, host, target)
    else:
        cmd = "rsync %s %s %s@%s:%s" % (options, source, user, host, target)
    return local(cmd)

########NEW FILE########
__FILENAME__ = _version
__version_info__ = (0, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

########NEW FILE########
