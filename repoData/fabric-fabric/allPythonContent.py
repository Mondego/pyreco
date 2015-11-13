__FILENAME__ = tag
from __future__ import with_statement

from contextlib import nested

from fabric.api import abort, hide, local, settings, task

# Need to import this as fabric.version for reload() purposes
import fabric.version
# But nothing is stopping us from making a convenient binding!
_version = fabric.version.get_version

from utils import msg


def _seek_version(cmd, txt):
    with nested(hide('running'), msg(txt)):
        cmd = cmd % _version('short')
        return local(cmd, capture=True)


def current_version_is_tagged():
    return _seek_version(
        'git tag | egrep "^%s$"',
        "Searching for existing tag"
    )


def current_version_is_changelogged(filename):
    return _seek_version(
        'egrep "^\* :release:\`%%s " %s' % filename,
        "Looking for changelog entry"
    )


def update_code(filename, force):
    """
    Update version data structure in-code and commit that change to git.

    Normally, if the version file has not been modified, we abort assuming the
    user quit without saving. Specify ``force=yes`` to override this.
    """
    raw_input("Version update in %r required! Press Enter to load $EDITOR." % filename)
    with hide('running'):
        local("$EDITOR %s" % filename)
    # Try to detect whether user bailed out of the edit
    with hide('running'):
        has_diff = local("git diff -- %s" % filename, capture=True)
    if not has_diff and not force:
        abort("You seem to have aborted the file edit, so I'm aborting too.")
    return filename


def commits_since_last_tag():
    """
    Has any work been done since the last tag?
    """
    with hide('running'):
        return local("git log %s.." % _version('short'), capture=True)


@task(default=True)
def tag(force='no', push='no'):
    """
    Tag a new release.

    Normally, if a Git tag exists matching the current version, and no Git
    commits appear after that tag, we abort assuming the user is making a
    mistake or forgot to commit their work.

    To override this -- i.e. to re-tag and re-upload -- specify ``force=yes``.
    We assume you know what you're doing if you use this.

    By default we do not push the tag remotely; specify ``push=yes`` to force a
    ``git push origin <tag>``.
    """
    force = force.lower() in ['y', 'yes']
    with settings(warn_only=True):
        changed = []
        # Does the current in-code version exist as a Git tag already?
        # If so, this means we haven't updated the in-code version specifier
        # yet, and need to do so.
        if current_version_is_tagged():
            # That is, if any work has been done since. Sanity check!
            if not commits_since_last_tag() and not force:
                abort("No work done since last tag!")
            # Open editor, update version
            version_file = "fabric/version.py"
            changed.append(update_code(version_file, force))
        # If the tag doesn't exist, the user has already updated version info
        # and we can just move on.
        else:
            print("Version has already been updated, no need to edit...")
        # Similar process but for the changelog.
        changelog = "docs/changelog.rst"
        if not current_version_is_changelogged(changelog):
            changed.append(update_code(changelog, force))
        else:
            print("Changelog already updated, no need to edit...")
        # Commit any changes
        if changed:
            with msg("Committing updated version and/or changelog"):
                reload(fabric.version)
                local("git add %s" % " ".join(changed))
                local("git commit -m \"Cut %s\"" % _version('verbose'))
                local("git push")

        # At this point, we've incremented the in-code version and just need to
        # tag it in Git.
        f = 'f' if force else ''
        with msg("Tagging"):
            local("git tag -%sam \"Fabric %s\" %s" % (
                f,
                _version('normal'),
                _version('short')
            ))
        # And push to the central server, if we were told to
        if push.lower() in ['y', 'yes']:
            with msg("Pushing"):
                local("git push origin %s" % _version('short'))

########NEW FILE########
__FILENAME__ = utils
from __future__ import with_statement

from contextlib import contextmanager

from fabric.api import hide, puts


@contextmanager
def msg(txt):
    puts(txt + "...", end='', flush=True)
    with hide('everything'):
        yield
    puts("done.", show_prefix=False, flush=True)

########NEW FILE########
__FILENAME__ = api
"""
Non-init module for doing convenient * imports from.

Necessary because if we did this in __init__, one would be unable to import
anything else inside the package -- like, say, the version number used in
setup.py -- without triggering loads of most of the code. Which doesn't work so
well when you're using setup.py to install e.g. ssh!
"""
from fabric.context_managers import (cd, hide, settings, show, path, prefix,
    lcd, quiet, warn_only, remote_tunnel, shell_env)
from fabric.decorators import (hosts, roles, runs_once, with_settings, task,
        serial, parallel)
from fabric.operations import (require, prompt, put, get, run, sudo, local,
    reboot, open_shell)
from fabric.state import env, output
from fabric.utils import abort, warn, puts, fastprint
from fabric.tasks import execute

########NEW FILE########
__FILENAME__ = auth
"""
Common authentication subroutines. Primarily for internal use.
"""


def get_password(user, host, port):
    from fabric.state import env
    from fabric.network import join_host_strings
    host_string = join_host_strings(user, host, port)
    return env.passwords.get(host_string, env.password)


def set_password(user, host, port, password):
    from fabric.state import env
    from fabric.network import join_host_strings
    host_string = join_host_strings(user, host, port)
    env.password = env.passwords[host_string] = password

########NEW FILE########
__FILENAME__ = colors
"""
.. versionadded:: 0.9.2

Functions for wrapping strings in ANSI color codes.

Each function within this module returns the input string ``text``, wrapped
with ANSI color codes for the appropriate color.

For example, to print some text as green on supporting terminals::

    from fabric.colors import green

    print(green("This text is green!"))

Because these functions simply return modified strings, you can nest them::

    from fabric.colors import red, green

    print(red("This sentence is red, except for " + \
          green("these words, which are green") + "."))

If ``bold`` is set to ``True``, the ANSI flag for bolding will be flipped on
for that particular invocation, which usually shows up as a bold or brighter
version of the original color on most terminals.
"""


def _wrap_with(code):

    def inner(text, bold=False):
        c = code
        if bold:
            c = "1;%s" % c
        return "\033[%sm%s\033[0m" % (c, text)
    return inner

red = _wrap_with('31')
green = _wrap_with('32')
yellow = _wrap_with('33')
blue = _wrap_with('34')
magenta = _wrap_with('35')
cyan = _wrap_with('36')
white = _wrap_with('37')

########NEW FILE########
__FILENAME__ = context_managers
"""
Context managers for use with the ``with`` statement.

.. note:: When using Python 2.5, you will need to start your fabfile
    with ``from __future__ import with_statement`` in order to make use of
    the ``with`` statement (which is a regular, non ``__future__`` feature of
    Python 2.6+.)

.. note:: If you are using multiple directly nested ``with`` statements, it can
    be convenient to use multiple context expressions in one single with
    statement. Instead of writing::

        with cd('/path/to/app'):
            with prefix('workon myvenv'):
                run('./manage.py syncdb')
                run('./manage.py loaddata myfixture')

    you can write::

        with cd('/path/to/app'), prefix('workon myvenv'):
            run('./manage.py syncdb')
            run('./manage.py loaddata myfixture')

    Note that you need Python 2.7+ for this to work. On Python 2.5 or 2.6, you
    can do the following::

        from contextlib import nested

        with nested(cd('/path/to/app'), prefix('workon myvenv')):
            ...

    Finally, note that `~fabric.context_managers.settings` implements
    ``nested`` itself -- see its API doc for details.
"""

from contextlib import contextmanager, nested
import sys
import socket
import select

from fabric.thread_handling import ThreadHandler
from fabric.state import output, win32, connections, env
from fabric import state

if not win32:
    import termios
    import tty


def _set_output(groups, which):
    """
    Refactored subroutine used by ``hide`` and ``show``.
    """
    try:
        # Preserve original values, pull in new given value to use
        previous = {}
        for group in output.expand_aliases(groups):
            previous[group] = output[group]
            output[group] = which
        # Yield control
        yield
    finally:
        # Restore original values
        output.update(previous)


def documented_contextmanager(func):
    wrapper = contextmanager(func)
    wrapper.undecorated = func
    return wrapper


@documented_contextmanager
def show(*groups):
    """
    Context manager for setting the given output ``groups`` to True.

    ``groups`` must be one or more strings naming the output groups defined in
    `~fabric.state.output`. The given groups will be set to True for the
    duration of the enclosed block, and restored to their previous value
    afterwards.

    For example, to turn on debug output (which is typically off by default)::

        def my_task():
            with show('debug'):
                run('ls /var/www')

    As almost all output groups are displayed by default, `show` is most useful
    for turning on the normally-hidden ``debug`` group, or when you know or
    suspect that code calling your own code is trying to hide output with
    `hide`.
    """
    return _set_output(groups, True)


@documented_contextmanager
def hide(*groups):
    """
    Context manager for setting the given output ``groups`` to False.

    ``groups`` must be one or more strings naming the output groups defined in
    `~fabric.state.output`. The given groups will be set to False for the
    duration of the enclosed block, and restored to their previous value
    afterwards.

    For example, to hide the "[hostname] run:" status lines, as well as
    preventing printout of stdout and stderr, one might use `hide` as follows::

        def my_task():
            with hide('running', 'stdout', 'stderr'):
                run('ls /var/www')
    """
    return _set_output(groups, False)


@documented_contextmanager
def _setenv(variables):
    """
    Context manager temporarily overriding ``env`` with given key/value pairs.

    A callable that returns a dict can also be passed. This is necessary when
    new values are being calculated from current values, in order to ensure that
    the "current" value is current at the time that the context is entered, not
    when the context manager is initialized. (See Issue #736.)

    This context manager is used internally by `settings` and is not intended
    to be used directly.
    """
    if callable(variables):
        variables = variables()
    clean_revert = variables.pop('clean_revert', False)
    previous = {}
    new = []
    for key, value in variables.iteritems():
        if key in state.env:
            previous[key] = state.env[key]
        else:
            new.append(key)
        state.env[key] = value
    try:
        yield
    finally:
        if clean_revert:
            for key, value in variables.iteritems():
                # If the current env value for this key still matches the
                # value we set it to beforehand, we are OK to revert it to the
                # pre-block value.
                if key in state.env and value == state.env[key]:
                    if key in previous:
                        state.env[key] = previous[key]
                    else:
                        del state.env[key]
        else:
            state.env.update(previous)
            for key in new:
                del state.env[key]


def settings(*args, **kwargs):
    """
    Nest context managers and/or override ``env`` variables.

    `settings` serves two purposes:

    * Most usefully, it allows temporary overriding/updating of ``env`` with
      any provided keyword arguments, e.g. ``with settings(user='foo'):``.
      Original values, if any, will be restored once the ``with`` block closes.

        * The keyword argument ``clean_revert`` has special meaning for
          ``settings`` itself (see below) and will be stripped out before
          execution.

    * In addition, it will use `contextlib.nested`_ to nest any given
      non-keyword arguments, which should be other context managers, e.g.
      ``with settings(hide('stderr'), show('stdout')):``.

    .. _contextlib.nested: http://docs.python.org/library/contextlib.html#contextlib.nested

    These behaviors may be specified at the same time if desired. An example
    will hopefully illustrate why this is considered useful::

        def my_task():
            with settings(
                hide('warnings', 'running', 'stdout', 'stderr'),
                warn_only=True
            ):
                if run('ls /etc/lsb-release'):
                    return 'Ubuntu'
                elif run('ls /etc/redhat-release'):
                    return 'RedHat'

    The above task executes a `run` statement, but will warn instead of
    aborting if the ``ls`` fails, and all output -- including the warning
    itself -- is prevented from printing to the user. The end result, in this
    scenario, is a completely silent task that allows the caller to figure out
    what type of system the remote host is, without incurring the handful of
    output that would normally occur.

    Thus, `settings` may be used to set any combination of environment
    variables in tandem with hiding (or showing) specific levels of output, or
    in tandem with any other piece of Fabric functionality implemented as a
    context manager.

    If ``clean_revert`` is set to ``True``, ``settings`` will **not** revert
    keys which are altered within the nested block, instead only reverting keys
    whose values remain the same as those given. More examples will make this
    clear; below is how ``settings`` operates normally::

        # Before the block, env.parallel defaults to False, host_string to None
        with settings(parallel=True, host_string='myhost'):
            # env.parallel is True
            # env.host_string is 'myhost'
            env.host_string = 'otherhost'
            # env.host_string is now 'otherhost'
        # Outside the block:
        # * env.parallel is False again
        # * env.host_string is None again

    The internal modification of ``env.host_string`` is nullified -- not always
    desirable. That's where ``clean_revert`` comes in::

        # Before the block, env.parallel defaults to False, host_string to None
        with settings(parallel=True, host_string='myhost', clean_revert=True):
            # env.parallel is True
            # env.host_string is 'myhost'
            env.host_string = 'otherhost'
            # env.host_string is now 'otherhost'
        # Outside the block:
        # * env.parallel is False again
        # * env.host_string remains 'otherhost'

    Brand new keys which did not exist in ``env`` prior to using ``settings``
    are also preserved if ``clean_revert`` is active. When ``False``, such keys
    are removed when the block exits.

    .. versionadded:: 1.4.1
        The ``clean_revert`` kwarg.
    """
    managers = list(args)
    if kwargs:
        managers.append(_setenv(kwargs))
    return nested(*managers)


def cd(path):
    """
    Context manager that keeps directory state when calling remote operations.

    Any calls to `run`, `sudo`, `get`, or `put` within the wrapped block will
    implicitly have a string similar to ``"cd <path> && "`` prefixed in order
    to give the sense that there is actually statefulness involved.

    .. note::
        `cd` only affects *remote* paths -- to modify *local* paths, use
        `~fabric.context_managers.lcd`.

    Because use of `cd` affects all such invocations, any code making use of
    those operations, such as much of the ``contrib`` section, will also be
    affected by use of `cd`.

    Like the actual 'cd' shell builtin, `cd` may be called with relative paths
    (keep in mind that your default starting directory is your remote user's
    ``$HOME``) and may be nested as well.

    Below is a "normal" attempt at using the shell 'cd', which doesn't work due
    to how shell-less SSH connections are implemented -- state is **not** kept
    between invocations of `run` or `sudo`::

        run('cd /var/www')
        run('ls')

    The above snippet will list the contents of the remote user's ``$HOME``
    instead of ``/var/www``. With `cd`, however, it will work as expected::

        with cd('/var/www'):
            run('ls') # Turns into "cd /var/www && ls"

    Finally, a demonstration (see inline comments) of nesting::

        with cd('/var/www'):
            run('ls') # cd /var/www && ls
            with cd('website1'):
                run('ls') # cd /var/www/website1 && ls

    .. note::

        This context manager is currently implemented by appending to (and, as
        always, restoring afterwards) the current value of an environment
        variable, ``env.cwd``. However, this implementation may change in the
        future, so we do not recommend manually altering ``env.cwd`` -- only
        the *behavior* of `cd` will have any guarantee of backwards
        compatibility.

    .. note::

        Space characters will be escaped automatically to make dealing with
        such directory names easier.

    .. versionchanged:: 1.0
        Applies to `get` and `put` in addition to the command-running
        operations.

    .. seealso:: `~fabric.context_managers.lcd`
    """
    return _change_cwd('cwd', path)


def lcd(path):
    """
    Context manager for updating local current working directory.

    This context manager is identical to `~fabric.context_managers.cd`, except
    that it changes a different env var (`lcwd`, instead of `cwd`) and thus
    only affects the invocation of `~fabric.operations.local` and the local
    arguments to `~fabric.operations.get`/`~fabric.operations.put`.

    Relative path arguments are relative to the local user's current working
    directory, which will vary depending on where Fabric (or Fabric-using code)
    was invoked. You can check what this is with `os.getcwd
    <http://docs.python.org/release/2.6/library/os.html#os.getcwd>`_. It may be
    useful to pin things relative to the location of the fabfile in use, which
    may be found in :ref:`env.real_fabfile <real-fabfile>`

    .. versionadded:: 1.0
    """
    return _change_cwd('lcwd', path)


def _change_cwd(which, path):
    path = path.replace(' ', '\ ')
    if state.env.get(which) and not path.startswith('/') and not path.startswith('~'):
        new_cwd = state.env.get(which) + '/' + path
    else:
        new_cwd = path
    return _setenv({which: new_cwd})


def path(path, behavior='append'):
    """
    Append the given ``path`` to the PATH used to execute any wrapped commands.

    Any calls to `run` or `sudo` within the wrapped block will implicitly have
    a string similar to ``"PATH=$PATH:<path> "`` prepended before the given
    command.

    You may customize the behavior of `path` by specifying the optional
    ``behavior`` keyword argument, as follows:

    * ``'append'``: append given path to the current ``$PATH``, e.g.
      ``PATH=$PATH:<path>``. This is the default behavior.
    * ``'prepend'``: prepend given path to the current ``$PATH``, e.g.
      ``PATH=<path>:$PATH``.
    * ``'replace'``: ignore previous value of ``$PATH`` altogether, e.g.
      ``PATH=<path>``.

    .. note::

        This context manager is currently implemented by modifying (and, as
        always, restoring afterwards) the current value of environment
        variables, ``env.path`` and ``env.path_behavior``. However, this
        implementation may change in the future, so we do not recommend
        manually altering them directly.

    .. versionadded:: 1.0
    """
    return _setenv({'path': path, 'path_behavior': behavior})


def prefix(command):
    """
    Prefix all wrapped `run`/`sudo` commands with given command plus ``&&``.

    This is nearly identical to `~fabric.operations.cd`, except that nested
    invocations append to a list of command strings instead of modifying a
    single string.

    Most of the time, you'll want to be using this alongside a shell script
    which alters shell state, such as ones which export or alter shell
    environment variables.

    For example, one of the most common uses of this tool is with the
    ``workon`` command from `virtualenvwrapper
    <http://www.doughellmann.com/projects/virtualenvwrapper/>`_::

        with prefix('workon myvenv'):
            run('./manage.py syncdb')

    In the above snippet, the actual shell command run would be this::

        $ workon myvenv && ./manage.py syncdb

    This context manager is compatible with `~fabric.context_managers.cd`, so
    if your virtualenv doesn't ``cd`` in its ``postactivate`` script, you could
    do the following::

        with cd('/path/to/app'):
            with prefix('workon myvenv'):
                run('./manage.py syncdb')
                run('./manage.py loaddata myfixture')

    Which would result in executions like so::

        $ cd /path/to/app && workon myvenv && ./manage.py syncdb
        $ cd /path/to/app && workon myvenv && ./manage.py loaddata myfixture

    Finally, as alluded to near the beginning,
    `~fabric.context_managers.prefix` may be nested if desired, e.g.::

        with prefix('workon myenv'):
            run('ls')
            with prefix('source /some/script'):
                run('touch a_file')

    The result::

        $ workon myenv && ls
        $ workon myenv && source /some/script && touch a_file

    Contrived, but hopefully illustrative.
    """
    return _setenv(lambda: {'command_prefixes': state.env.command_prefixes + [command]})


@documented_contextmanager
def char_buffered(pipe):
    """
    Force local terminal ``pipe`` be character, not line, buffered.

    Only applies on Unix-based systems; on Windows this is a no-op.
    """
    if win32 or not pipe.isatty():
        yield
    else:
        old_settings = termios.tcgetattr(pipe)
        tty.setcbreak(pipe)
        try:
            yield
        finally:
            termios.tcsetattr(pipe, termios.TCSADRAIN, old_settings)


def shell_env(**kw):
    """
    Set shell environment variables for wrapped commands.

    For example, the below shows how you might set a ZeroMQ related environment
    variable when installing a Python ZMQ library::

        with shell_env(ZMQ_DIR='/home/user/local'):
            run('pip install pyzmq')

    As with `~fabric.context_managers.prefix`, this effectively turns the
    ``run`` command into::

        $ export ZMQ_DIR='/home/user/local' && pip install pyzmq

    Multiple key-value pairs may be given simultaneously.

    .. note::
        If used to affect the behavior of `~fabric.operations.local` when
        running from a Windows localhost, ``SET`` commands will be used to
        implement this feature.
    """
    return _setenv({'shell_env': kw})


def _forwarder(chan, sock):
    # Bidirectionally forward data between a socket and a Paramiko channel.
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()


@documented_contextmanager
def remote_tunnel(remote_port, local_port=None, local_host="localhost",
    remote_bind_address="127.0.0.1"):
    """
    Create a tunnel forwarding a locally-visible port to the remote target.

    For example, you can let the remote host access a database that is
    installed on the client host::

        # Map localhost:6379 on the server to localhost:6379 on the client,
        # so that the remote 'redis-cli' program ends up speaking to the local
        # redis-server.
        with remote_tunnel(6379):
            run("redis-cli -i")

    The database might be installed on a client only reachable from the client
    host (as opposed to *on* the client itself)::

        # Map localhost:6379 on the server to redis.internal:6379 on the client
        with remote_tunnel(6379, local_host="redis.internal")
            run("redis-cli -i")

    ``remote_tunnel`` accepts up to four arguments:

    * ``remote_port`` (mandatory) is the remote port to listen to.
    * ``local_port`` (optional) is the local port to connect to; the default is
      the same port as the remote one.
    * ``local_host`` (optional) is the locally-reachable computer (DNS name or
      IP address) to connect to; the default is ``localhost`` (that is, the
      same computer Fabric is running on).
    * ``remote_bind_address`` (optional) is the remote IP address to bind to
      for listening, on the current target. It should be an IP address assigned
      to an interface on the target (or a DNS name that resolves to such IP).
      You can use "0.0.0.0" to bind to all interfaces.

    .. note::
        By default, most SSH servers only allow remote tunnels to listen to the
        localhost interface (127.0.0.1). In these cases, `remote_bind_address`
        is ignored by the server, and the tunnel will listen only to 127.0.0.1.

    .. versionadded: 1.6
    """
    if local_port is None:
        local_port = remote_port

    sockets = []
    channels = []
    threads = []

    def accept(channel, (src_addr, src_port), (dest_addr, dest_port)):
        channels.append(channel)
        sock = socket.socket()
        sockets.append(sock)

        try:
            sock.connect((local_host, local_port))
        except Exception, e:
            print "[%s] rtunnel: cannot connect to %s:%d (from local)" % (env.host_string, local_host, local_port)
            chan.close()
            return

        print "[%s] rtunnel: opened reverse tunnel: %r -> %r -> %r"\
              % (env.host_string, channel.origin_addr,
                 channel.getpeername(), (local_host, local_port))

        th = ThreadHandler('fwd', _forwarder, channel, sock)
        threads.append(th)

    transport = connections[env.host_string].get_transport()
    transport.request_port_forward(remote_bind_address, remote_port, handler=accept)

    try:
        yield
    finally:
        for sock, chan, th in zip(sockets, channels, threads):
            sock.close()
            chan.close()
            th.thread.join()
            th.raise_if_needed()
        transport.cancel_port_forward(remote_bind_address, remote_port)



quiet = lambda: settings(hide('everything'), warn_only=True)
quiet.__doc__ = """
    Alias to ``settings(hide('everything'), warn_only=True)``.

    Useful for wrapping remote interrogative commands which you expect to fail
    occasionally, and/or which you want to silence.

    Example::

        with quiet():
            have_build_dir = run("test -e /tmp/build").succeeded

    When used in a task, the above snippet will not produce any ``run: test -e
    /tmp/build`` line, nor will any stdout/stderr display, and command failure
    is ignored.

    .. seealso::
        :ref:`env.warn_only <warn_only>`,
        `~fabric.context_managers.settings`,
        `~fabric.context_managers.hide`

    .. versionadded:: 1.5
"""


warn_only = lambda: settings(warn_only=True)
warn_only.__doc__ = """
    Alias to ``settings(warn_only=True)``.

    .. seealso::
        :ref:`env.warn_only <warn_only>`,
        `~fabric.context_managers.settings`,
        `~fabric.context_managers.quiet`
"""

########NEW FILE########
__FILENAME__ = console
"""
Console/terminal user interface functionality.
"""

from fabric.api import prompt


def confirm(question, default=True):
    """
    Ask user a yes/no question and return their response as True or False.

    ``question`` should be a simple, grammatically complete question such as
    "Do you wish to continue?", and will have a string similar to " [Y/n] "
    appended automatically. This function will *not* append a question mark for
    you.

    By default, when the user presses Enter without typing anything, "yes" is
    assumed. This can be changed by specifying ``default=False``.
    """
    # Set up suffix
    if default:
        suffix = "Y/n"
    else:
        suffix = "y/N"
    # Loop till we get something we like
    while True:
        response = prompt("%s [%s] " % (question, suffix)).lower()
        # Default
        if not response:
            return default
        # Yes
        if response in ['y', 'yes']:
            return True
        # No
        if response in ['n', 'no']:
            return False
        # Didn't get empty, yes or no, so complain and loop
        print("I didn't understand you. Please specify '(y)es' or '(n)o'.")

########NEW FILE########
__FILENAME__ = django
"""
.. versionadded:: 0.9.2

These functions streamline the process of initializing Django's settings module
environment variable. Once this is done, your fabfile may import from your
Django project, or Django itself, without requiring the use of ``manage.py``
plugins or having to set the environment variable yourself every time you use
your fabfile.

Currently, these functions only allow Fabric to interact with
local-to-your-fabfile Django installations. This is not as limiting as it
sounds; for example, you can use Fabric as a remote "build" tool as well as
using it locally. Imagine the following fabfile::

    from fabric.api import run, local, hosts, cd
    from fabric.contrib import django

    django.project('myproject')
    from myproject.myapp.models import MyModel

    def print_instances():
        for instance in MyModel.objects.all():
            print(instance)

    @hosts('production-server')
    def print_production_instances():
        with cd('/path/to/myproject'):
            run('fab print_instances')

With Fabric installed on both ends, you could execute
``print_production_instances`` locally, which would trigger ``print_instances``
on the production server -- which would then be interacting with your
production Django database.

As another example, if your local and remote settings are similar, you can use
it to obtain e.g. your database settings, and then use those when executing a
remote (non-Fabric) command. This would allow you some degree of freedom even
if Fabric is only installed locally::

    from fabric.api import run
    from fabric.contrib import django

    django.settings_module('myproject.settings')
    from django.conf import settings

    def dump_production_database():
        run('mysqldump -u %s -p=%s %s > /tmp/prod-db.sql' % (
            settings.DATABASE_USER,
            settings.DATABASE_PASSWORD,
            settings.DATABASE_NAME
        ))

The above snippet will work if run from a local, development environment, again
provided your local ``settings.py`` mirrors your remote one in terms of
database connection info.
"""

import os


def settings_module(module):
    """
    Set ``DJANGO_SETTINGS_MODULE`` shell environment variable to ``module``.

    Due to how Django works, imports from Django or a Django project will fail
    unless the shell environment variable ``DJANGO_SETTINGS_MODULE`` is
    correctly set (see `the Django settings docs
    <http://docs.djangoproject.com/en/dev/topics/settings/>`_.)

    This function provides a shortcut for doing so; call it near the top of
    your fabfile or Fabric-using code, after which point any Django imports
    should work correctly.

    .. note::

        This function sets a **shell** environment variable (via
        ``os.environ``) and is unrelated to Fabric's own internal "env"
        variables.
    """
    os.environ['DJANGO_SETTINGS_MODULE'] = module


def project(name):
    """
    Sets ``DJANGO_SETTINGS_MODULE`` to ``'<name>.settings'``.

    This function provides a handy shortcut for the common case where one is
    using the Django default naming convention for their settings file and
    location.

    Uses `settings_module` -- see its documentation for details on why and how
    to use this functionality.
    """
    settings_module('%s.settings' % name)

########NEW FILE########
__FILENAME__ = files
"""
Module providing easy API for working with remote files and folders.
"""

from __future__ import with_statement

import hashlib
import tempfile
import re
import os
from StringIO import StringIO
from functools import partial

from fabric.api import *
from fabric.utils import apply_lcwd


def exists(path, use_sudo=False, verbose=False):
    """
    Return True if given path exists on the current remote host.

    If ``use_sudo`` is True, will use `sudo` instead of `run`.

    `exists` will, by default, hide all output (including the run line, stdout,
    stderr and any warning resulting from the file not existing) in order to
    avoid cluttering output. You may specify ``verbose=True`` to change this
    behavior.
    """
    func = use_sudo and sudo or run
    cmd = 'test -e %s' % _expand_path(path)
    # If verbose, run normally
    if verbose:
        with settings(warn_only=True):
            return not func(cmd).failed
    # Otherwise, be quiet
    with settings(hide('everything'), warn_only=True):
        return not func(cmd).failed


def is_link(path, use_sudo=False, verbose=False):
    """
    Return True if the given path is a symlink on the current remote host.

    If ``use_sudo`` is True, will use `.sudo` instead of `.run`.

    `.is_link` will, by default, hide all output. Give ``verbose=True`` to change this.
    """
    func = sudo if use_sudo else run
    cmd = 'test -L "$(echo %s)"' % path
    args, kwargs = [], {'warn_only': True}
    if not verbose:
        opts = [hide('everything')]
    with settings(*args, **kwargs):
        return func(cmd).succeeded


def first(*args, **kwargs):
    """
    Given one or more file paths, returns first one found, or None if none
    exist. May specify ``use_sudo`` and ``verbose`` which are passed to `exists`.
    """
    for directory in args:
        if exists(directory, **kwargs):
            return directory


def upload_template(filename, destination, context=None, use_jinja=False,
    template_dir=None, use_sudo=False, backup=True, mirror_local_mode=False,
    mode=None, pty=None):
    """
    Render and upload a template text file to a remote host.

    Returns the result of the inner call to `~fabric.operations.put` -- see its
    documentation for details.

    ``filename`` should be the path to a text file, which may contain `Python
    string interpolation formatting
    <http://docs.python.org/library/stdtypes.html#string-formatting>`_ and will
    be rendered with the given context dictionary ``context`` (if given.)

    Alternately, if ``use_jinja`` is set to True and you have the Jinja2
    templating library available, Jinja will be used to render the template
    instead. Templates will be loaded from the invoking user's current working
    directory by default, or from ``template_dir`` if given.

    The resulting rendered file will be uploaded to the remote file path
    ``destination``.  If the destination file already exists, it will be
    renamed with a ``.bak`` extension unless ``backup=False`` is specified.

    By default, the file will be copied to ``destination`` as the logged-in
    user; specify ``use_sudo=True`` to use `sudo` instead.

    The ``mirror_local_mode`` and ``mode`` kwargs are passed directly to an
    internal `~fabric.operations.put` call; please see its documentation for
    details on these two options.

    The ``pty`` kwarg will be passed verbatim to any internal
    `~fabric.operations.run`/`~fabric.operations.sudo` calls, such as those
    used for testing directory-ness, making backups, etc.

    .. versionchanged:: 1.1
        Added the ``backup``, ``mirror_local_mode`` and ``mode`` kwargs.
    .. versionchanged:: 1.9
        Added the ``pty`` kwarg.
    """
    func = use_sudo and sudo or run
    if pty is not None:
        func = partial(func, pty=pty)
    # Normalize destination to be an actual filename, due to using StringIO
    with settings(hide('everything'), warn_only=True):
        if func('test -d %s' % _expand_path(destination)).succeeded:
            sep = "" if destination.endswith('/') else "/"
            destination += sep + os.path.basename(filename)

    # Use mode kwarg to implement mirror_local_mode, again due to using
    # StringIO
    if mirror_local_mode and mode is None:
        mode = os.stat(filename).st_mode
        # To prevent put() from trying to do this
        # logic itself
        mirror_local_mode = False

    # Process template
    text = None
    if use_jinja:
        try:
            template_dir = template_dir or os.getcwd()
            template_dir = apply_lcwd(template_dir, env)
            from jinja2 import Environment, FileSystemLoader
            jenv = Environment(loader=FileSystemLoader(template_dir))
            text = jenv.get_template(filename).render(**context or {})
            # Force to a byte representation of Unicode, or str()ification
            # within Paramiko's SFTP machinery may cause decode issues for
            # truly non-ASCII characters.
            text = text.encode('utf-8')
        except ImportError:
            import traceback
            tb = traceback.format_exc()
            abort(tb + "\nUnable to import Jinja2 -- see above.")
    else:
        filename = apply_lcwd(filename, env)
        with open(os.path.expanduser(filename)) as inputfile:
            text = inputfile.read()
        if context:
            text = text % context

    # Back up original file
    if backup and exists(destination):
        func("cp %s{,.bak}" % _expand_path(destination))

    # Upload the file.
    return put(
        local_path=StringIO(text),
        remote_path=destination,
        use_sudo=use_sudo,
        mirror_local_mode=mirror_local_mode,
        mode=mode
    )


def sed(filename, before, after, limit='', use_sudo=False, backup='.bak',
    flags='', shell=False):
    """
    Run a search-and-replace on ``filename`` with given regex patterns.

    Equivalent to ``sed -i<backup> -r -e "/<limit>/ s/<before>/<after>/<flags>g"
    <filename>``. Setting ``backup`` to an empty string will, disable backup
    file creation.

    For convenience, ``before`` and ``after`` will automatically escape forward
    slashes, single quotes and parentheses for you, so you don't need to
    specify e.g.  ``http:\/\/foo\.com``, instead just using ``http://foo\.com``
    is fine.

    If ``use_sudo`` is True, will use `sudo` instead of `run`.

    The ``shell`` argument will be eventually passed to `run`/`sudo`. It
    defaults to False in order to avoid problems with many nested levels of
    quotes and backslashes. However, setting it to True may help when using
    ``~fabric.operations.cd`` to wrap explicit or implicit ``sudo`` calls.
    (``cd`` by it's nature is a shell built-in, not a standalone command, so it
    should be called within a shell.)

    Other options may be specified with sed-compatible regex flags -- for
    example, to make the search and replace case insensitive, specify
    ``flags="i"``. The ``g`` flag is always specified regardless, so you do not
    need to remember to include it when overriding this parameter.

    .. versionadded:: 1.1
        The ``flags`` parameter.
    .. versionadded:: 1.6
        Added the ``shell`` keyword argument.
    """
    func = use_sudo and sudo or run
    # Characters to be escaped in both
    for char in "/'":
        before = before.replace(char, r'\%s' % char)
        after = after.replace(char, r'\%s' % char)
    # Characters to be escaped in replacement only (they're useful in regexen
    # in the 'before' part)
    for char in "()":
        after = after.replace(char, r'\%s' % char)
    if limit:
        limit = r'/%s/ ' % limit
    context = {
        'script': r"'%ss/%s/%s/%sg'" % (limit, before, after, flags),
        'filename': _expand_path(filename),
        'backup': backup
    }
    # Test the OS because of differences between sed versions

    with hide('running', 'stdout'):
        platform = run("uname")
    if platform in ('NetBSD', 'OpenBSD', 'QNX'):
        # Attempt to protect against failures/collisions
        hasher = hashlib.sha1()
        hasher.update(env.host_string)
        hasher.update(filename)
        context['tmp'] = "/tmp/%s" % hasher.hexdigest()
        # Use temp file to work around lack of -i
        expr = r"""cp -p %(filename)s %(tmp)s \
&& sed -r -e %(script)s %(filename)s > %(tmp)s \
&& cp -p %(filename)s %(filename)s%(backup)s \
&& mv %(tmp)s %(filename)s"""
    else:
        context['extended_regex'] = '-E' if platform == 'Darwin' else '-r'
        expr = r"sed -i%(backup)s %(extended_regex)s -e %(script)s %(filename)s"
    command = expr % context
    return func(command, shell=shell)


def uncomment(filename, regex, use_sudo=False, char='#', backup='.bak',
    shell=False):
    """
    Attempt to uncomment all lines in ``filename`` matching ``regex``.

    The default comment delimiter is `#` and may be overridden by the ``char``
    argument.

    This function uses the `sed` function, and will accept the same
    ``use_sudo``, ``shell`` and ``backup`` keyword arguments that `sed` does.

    `uncomment` will remove a single whitespace character following the comment
    character, if it exists, but will preserve all preceding whitespace.  For
    example, ``# foo`` would become ``foo`` (the single space is stripped) but
    ``    # foo`` would become ``    foo`` (the single space is still stripped,
    but the preceding 4 spaces are not.)

    .. versionchanged:: 1.6
        Added the ``shell`` keyword argument.
    """
    return sed(
        filename,
        before=r'^([[:space:]]*)%s[[:space:]]?' % char,
        after=r'\1',
        limit=regex,
        use_sudo=use_sudo,
        backup=backup,
        shell=shell
    )


def comment(filename, regex, use_sudo=False, char='#', backup='.bak',
    shell=False):
    """
    Attempt to comment out all lines in ``filename`` matching ``regex``.

    The default commenting character is `#` and may be overridden by the
    ``char`` argument.

    This function uses the `sed` function, and will accept the same
    ``use_sudo``, ``shell`` and ``backup`` keyword arguments that `sed` does.

    `comment` will prepend the comment character to the beginning of the line,
    so that lines end up looking like so::

        this line is uncommented
        #this line is commented
        #   this line is indented and commented

    In other words, comment characters will not "follow" indentation as they
    sometimes do when inserted by hand. Neither will they have a trailing space
    unless you specify e.g. ``char='# '``.

    .. note::

        In order to preserve the line being commented out, this function will
        wrap your ``regex`` argument in parentheses, so you don't need to. It
        will ensure that any preceding/trailing ``^`` or ``$`` characters are
        correctly moved outside the parentheses. For example, calling
        ``comment(filename, r'^foo$')`` will result in a `sed` call with the
        "before" regex of ``r'^(foo)$'`` (and the "after" regex, naturally, of
        ``r'#\\1'``.)

    .. versionadded:: 1.5
        Added the ``shell`` keyword argument.
    """
    carot, dollar = '', ''
    if regex.startswith('^'):
        carot = '^'
        regex = regex[1:]
    if regex.endswith('$'):
        dollar = '$'
        regex = regex[:-1]
    regex = "%s(%s)%s" % (carot, regex, dollar)
    return sed(
        filename,
        before=regex,
        after=r'%s\1' % char,
        use_sudo=use_sudo,
        backup=backup,
        shell=shell
    )


def contains(filename, text, exact=False, use_sudo=False, escape=True,
    shell=False):
    """
    Return True if ``filename`` contains ``text`` (which may be a regex.)

    By default, this function will consider a partial line match (i.e. where
    ``text`` only makes up part of the line it's on). Specify ``exact=True`` to
    change this behavior so that only a line containing exactly ``text``
    results in a True return value.

    This function leverages ``egrep`` on the remote end (so it may not follow
    Python regular expression syntax perfectly), and skips ``env.shell``
    wrapper by default.

    If ``use_sudo`` is True, will use `sudo` instead of `run`.

    If ``escape`` is False, no extra regular expression related escaping is
    performed (this includes overriding ``exact`` so that no ``^``/``$`` is
    added.)

    The ``shell`` argument will be eventually passed to ``run/sudo``. See
    description of the same argumnet in ``~fabric.contrib.sed`` for details.

    .. versionchanged:: 1.0
        Swapped the order of the ``filename`` and ``text`` arguments to be
        consistent with other functions in this module.
    .. versionchanged:: 1.4
        Updated the regular expression related escaping to try and solve
        various corner cases.
    .. versionchanged:: 1.4
        Added ``escape`` keyword argument.
    .. versionadded:: 1.6
        Added the ``shell`` keyword argument.
    """
    func = use_sudo and sudo or run
    if escape:
        text = _escape_for_regex(text)
        if exact:
            text = "^%s$" % text
    with settings(hide('everything'), warn_only=True):
        egrep_cmd = 'egrep "%s" %s' % (text, _expand_path(filename))
        return func(egrep_cmd, shell=shell).succeeded


def append(filename, text, use_sudo=False, partial=False, escape=True,
    shell=False):
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

    If ``use_sudo`` is True, will use `sudo` instead of `run`.

    The ``shell`` argument will be eventually passed to ``run/sudo``. See
    description of the same argumnet in ``~fabric.contrib.sed`` for details.

    .. versionchanged:: 0.9.1
        Added the ``partial`` keyword argument.
    .. versionchanged:: 1.0
        Swapped the order of the ``filename`` and ``text`` arguments to be
        consistent with other functions in this module.
    .. versionchanged:: 1.0
        Changed default value of ``partial`` kwarg to be ``False``.
    .. versionchanged:: 1.4
        Updated the regular expression related escaping to try and solve
        various corner cases.
    .. versionadded:: 1.6
        Added the ``shell`` keyword argument.
    """
    func = use_sudo and sudo or run
    # Normalize non-list input to be a list
    if isinstance(text, basestring):
        text = [text]
    for line in text:
        regex = '^' + _escape_for_regex(line)  + ('' if partial else '$')
        if (exists(filename, use_sudo=use_sudo) and line
            and contains(filename, regex, use_sudo=use_sudo, escape=False,
                         shell=shell)):
            continue
        line = line.replace("'", r"'\\''") if escape else line
        func("echo '%s' >> %s" % (line, _expand_path(filename)))

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

def _expand_path(path):
    return '"$(echo %s)"' % path

########NEW FILE########
__FILENAME__ = project
"""
Useful non-core functionality, e.g. functions composing multiple operations.
"""
from __future__ import with_statement

from os import getcwd, sep
import os.path
from datetime import datetime
from tempfile import mkdtemp

from fabric.network import needs_host, key_filenames, normalize
from fabric.operations import local, run, sudo, put
from fabric.state import env, output
from fabric.context_managers import cd

__all__ = ['rsync_project', 'upload_project']

@needs_host
def rsync_project(
    remote_dir,
    local_dir=None,
    exclude=(),
    delete=False,
    extra_opts='',
    ssh_opts='',
    capture=False,
    upload=True,
    default_opts='-pthrvz'
):
    """
    Synchronize a remote directory with the current project directory via rsync.

    Where ``upload_project()`` makes use of ``scp`` to copy one's entire
    project every time it is invoked, ``rsync_project()`` uses the ``rsync``
    command-line utility, which only transfers files newer than those on the
    remote end.

    ``rsync_project()`` is thus a simple wrapper around ``rsync``; for
    details on how ``rsync`` works, please see its manpage. ``rsync`` must be
    installed on both your local and remote systems in order for this operation
    to work correctly.

    This function makes use of Fabric's ``local()`` operation, and returns the
    output of that function call; thus it will return the stdout, if any, of
    the resultant ``rsync`` call.

    ``rsync_project()`` takes the following parameters:

    * ``remote_dir``: the only required parameter, this is the path to the
      directory on the remote server. Due to how ``rsync`` is implemented, the
      exact behavior depends on the value of ``local_dir``:

        * If ``local_dir`` ends with a trailing slash, the files will be
          dropped inside of ``remote_dir``. E.g.
          ``rsync_project("/home/username/project", "foldername/")`` will drop
          the contents of ``foldername`` inside of ``/home/username/project``.
        * If ``local_dir`` does **not** end with a trailing slash (and this
          includes the default scenario, when ``local_dir`` is not specified),
          ``remote_dir`` is effectively the "parent" directory, and a new
          directory named after ``local_dir`` will be created inside of it. So
          ``rsync_project("/home/username", "foldername")`` would create a new
          directory ``/home/username/foldername`` (if needed) and place the
          files there.

    * ``local_dir``: by default, ``rsync_project`` uses your current working
      directory as the source directory. This may be overridden by specifying
      ``local_dir``, which is a string passed verbatim to ``rsync``, and thus
      may be a single directory (``"my_directory"``) or multiple directories
      (``"dir1 dir2"``). See the ``rsync`` documentation for details.
    * ``exclude``: optional, may be a single string, or an iterable of strings,
      and is used to pass one or more ``--exclude`` options to ``rsync``.
    * ``delete``: a boolean controlling whether ``rsync``'s ``--delete`` option
      is used. If True, instructs ``rsync`` to remove remote files that no
      longer exist locally. Defaults to False.
    * ``extra_opts``: an optional, arbitrary string which you may use to pass
      custom arguments or options to ``rsync``.
    * ``ssh_opts``: Like ``extra_opts`` but specifically for the SSH options
      string (rsync's ``--rsh`` flag.)
    * ``capture``: Sent directly into an inner `~fabric.operations.local` call.
    * ``upload``: a boolean controlling whether file synchronization is
      performed up or downstream. Upstream by default.
    * ``default_opts``: the default rsync options ``-pthrvz``, override if
      desired (e.g. to remove verbosity, etc).

    Furthermore, this function transparently honors Fabric's port and SSH key
    settings. Calling this function when the current host string contains a
    nonstandard port, or when ``env.key_filename`` is non-empty, will use the
    specified port and/or SSH key filename(s).

    For reference, the approximate ``rsync`` command-line call that is
    constructed by this function is the following::

        rsync [--delete] [--exclude exclude[0][, --exclude[1][, ...]]] \\
            [default_opts] [extra_opts] <local_dir> <host_string>:<remote_dir>

    .. versionadded:: 1.4.0
        The ``ssh_opts`` keyword argument.
    .. versionadded:: 1.4.1
        The ``capture`` keyword argument.
    .. versionadded:: 1.8.0
        The ``default_opts`` keyword argument.
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
    # RSH
    rsh_string = ""
    rsh_parts = [key_string, port_string, ssh_opts]
    if any(rsh_parts):
        rsh_string = "--rsh='ssh %s'" % " ".join(rsh_parts)
    # Set up options part of string
    options_map = {
        'delete': '--delete' if delete else '',
        'exclude': exclude_opts % exclusions,
        'rsh': rsh_string,
        'default': default_opts,
        'extra': extra_opts,
    }
    options = "%(delete)s%(exclude)s %(default)s %(extra)s %(rsh)s" % options_map
    # Get local directory
    if local_dir is None:
        local_dir = '../' + getcwd().split(sep)[-1]
    # Create and run final command string
    if host.count(':') > 1:
        # Square brackets are mandatory for IPv6 rsync address,
        # even if port number is not specified
        remote_prefix = "[%s@%s]" % (user, host)
    else:
        remote_prefix = "%s@%s" % (user, host)
    if upload:
        cmd = "rsync %s %s %s:%s" % (options, local_dir, remote_prefix, remote_dir)
    else:
        cmd = "rsync %s %s:%s %s" % (options, remote_prefix, remote_dir, local_dir)

    if output.running:
        print("[%s] rsync_project: %s" % (env.host_string, cmd))
    return local(cmd, capture=capture)


def upload_project(local_dir=None, remote_dir="", use_sudo=False):
    """
    Upload the current project to a remote system via ``tar``/``gzip``.

    ``local_dir`` specifies the local project directory to upload, and defaults
    to the current working directory.

    ``remote_dir`` specifies the target directory to upload into (meaning that
    a copy of ``local_dir`` will appear as a subdirectory of ``remote_dir``)
    and defaults to the remote user's home directory.

    ``use_sudo`` specifies which method should be used when executing commands
    remotely. ``sudo`` will be used if use_sudo is True, otherwise ``run`` will
    be used.

    This function makes use of the ``tar`` and ``gzip`` programs/libraries,
    thus it will not work too well on Win32 systems unless one is using Cygwin
    or something similar. It will attempt to clean up the local and remote
    tarfiles when it finishes executing, even in the event of a failure.

    .. versionchanged:: 1.1
        Added the ``local_dir`` and ``remote_dir`` kwargs.

    .. versionchanged:: 1.7
        Added the ``use_sudo`` kwarg.
    """
    runner = use_sudo and sudo or run

    local_dir = local_dir or os.getcwd()

    # Remove final '/' in local_dir so that basename() works
    local_dir = local_dir.rstrip(os.sep)

    local_path, local_name = os.path.split(local_dir)
    tar_file = "%s.tar.gz" % local_name
    target_tar = os.path.join(remote_dir, tar_file)
    tmp_folder = mkdtemp()

    try:
        tar_path = os.path.join(tmp_folder, tar_file)
        local("tar -czf %s -C %s %s" % (tar_path, local_path, local_name))
        put(tar_path, target_tar, use_sudo=use_sudo)
        with cd(remote_dir):
            try:
                runner("tar -xzf %s" % tar_file)
            finally:
                runner("rm -f %s" % tar_file)
    finally:
        local("rm -rf %s" % tmp_folder)

########NEW FILE########
__FILENAME__ = decorators
"""
Convenience decorators for use in fabfiles.
"""
from __future__ import with_statement

import types
from functools import wraps

from Crypto import Random

from fabric import tasks
from .context_managers import settings


def task(*args, **kwargs):
    """
    Decorator declaring the wrapped function to be a new-style task.

    May be invoked as a simple, argument-less decorator (i.e. ``@task``) or
    with arguments customizing its behavior (e.g. ``@task(alias='myalias')``).

    Please see the :ref:`new-style task <task-decorator>` documentation for
    details on how to use this decorator.

    .. versionchanged:: 1.2
        Added the ``alias``, ``aliases``, ``task_class`` and ``default``
        keyword arguments. See :ref:`task-decorator-arguments` for details.
    .. versionchanged:: 1.5
        Added the ``name`` keyword argument.

    .. seealso:: `~fabric.docs.unwrap_tasks`, `~fabric.tasks.WrappedCallableTask`
    """
    invoked = bool(not args or kwargs)
    task_class = kwargs.pop("task_class", tasks.WrappedCallableTask)
    if not invoked:
        func, args = args[0], ()

    def wrapper(func):
        return task_class(func, *args, **kwargs)

    return wrapper if invoked else wrapper(func)

def _wrap_as_new(original, new):
    if isinstance(original, tasks.Task):
        return tasks.WrappedCallableTask(new)
    return new


def _list_annotating_decorator(attribute, *values):
    def attach_list(func):
        @wraps(func)
        def inner_decorator(*args, **kwargs):
            return func(*args, **kwargs)
        _values = values
        # Allow for single iterable argument as well as *args
        if len(_values) == 1 and not isinstance(_values[0], basestring):
            _values = _values[0]
        setattr(inner_decorator, attribute, list(_values))
        # Don't replace @task new-style task objects with inner_decorator by
        # itself -- wrap in a new Task object first.
        inner_decorator = _wrap_as_new(func, inner_decorator)
        return inner_decorator
    return attach_list


def hosts(*host_list):
    """
    Decorator defining which host or hosts to execute the wrapped function on.

    For example, the following will ensure that, barring an override on the
    command line, ``my_func`` will be run on ``host1``, ``host2`` and
    ``host3``, and with specific users on ``host1`` and ``host3``::

        @hosts('user1@host1', 'host2', 'user2@host3')
        def my_func():
            pass

    `~fabric.decorators.hosts` may be invoked with either an argument list
    (``@hosts('host1')``, ``@hosts('host1', 'host2')``) or a single, iterable
    argument (``@hosts(['host1', 'host2'])``).

    Note that this decorator actually just sets the function's ``.hosts``
    attribute, which is then read prior to executing the function.

    .. versionchanged:: 0.9.2
        Allow a single, iterable argument (``@hosts(iterable)``) to be used
        instead of requiring ``@hosts(*iterable)``.
    """
    return _list_annotating_decorator('hosts', *host_list)


def roles(*role_list):
    """
    Decorator defining a list of role names, used to look up host lists.

    A role is simply defined as a key in `env` whose value is a list of one or
    more host connection strings. For example, the following will ensure that,
    barring an override on the command line, ``my_func`` will be executed
    against the hosts listed in the ``webserver`` and ``dbserver`` roles::

        env.roledefs.update({
            'webserver': ['www1', 'www2'],
            'dbserver': ['db1']
        })

        @roles('webserver', 'dbserver')
        def my_func():
            pass

    As with `~fabric.decorators.hosts`, `~fabric.decorators.roles` may be
    invoked with either an argument list or a single, iterable argument.
    Similarly, this decorator uses the same mechanism as
    `~fabric.decorators.hosts` and simply sets ``<function>.roles``.

    .. versionchanged:: 0.9.2
        Allow a single, iterable argument to be used (same as
        `~fabric.decorators.hosts`).
    """
    return _list_annotating_decorator('roles', *role_list)


def runs_once(func):
    """
    Decorator preventing wrapped function from running more than once.

    By keeping internal state, this decorator allows you to mark a function
    such that it will only run once per Python interpreter session, which in
    typical use means "once per invocation of the ``fab`` program".

    Any function wrapped with this decorator will silently fail to execute the
    2nd, 3rd, ..., Nth time it is called, and will return the value of the
    original run.
    
    .. note:: ``runs_once`` does not work with parallel task execution.
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        if not hasattr(decorated, 'return_value'):
            decorated.return_value = func(*args, **kwargs)
        return decorated.return_value
    decorated = _wrap_as_new(func, decorated)
    # Mark as serial (disables parallelism) and return
    return serial(decorated)


def serial(func):
    """
    Forces the wrapped function to always run sequentially, never in parallel.

    This decorator takes precedence over the global value of :ref:`env.parallel
    <env-parallel>`. However, if a task is decorated with both
    `~fabric.decorators.serial` *and* `~fabric.decorators.parallel`,
    `~fabric.decorators.parallel` wins.

    .. versionadded:: 1.3
    """
    if not getattr(func, 'parallel', False):
        func.serial = True
    return _wrap_as_new(func, func)


def parallel(pool_size=None):
    """
    Forces the wrapped function to run in parallel, instead of sequentially.

    This decorator takes precedence over the global value of :ref:`env.parallel
    <env-parallel>`. It also takes precedence over `~fabric.decorators.serial`
    if a task is decorated with both.

    .. versionadded:: 1.3
    """
    called_without_args = type(pool_size) == types.FunctionType

    def real_decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            # Required for ssh/PyCrypto to be happy in multiprocessing
            # (as far as we can tell, this is needed even with the extra such
            # calls in newer versions of paramiko.)
            Random.atfork()
            return func(*args, **kwargs)
        inner.parallel = True
        inner.serial = False
        inner.pool_size = None if called_without_args else pool_size
        return _wrap_as_new(func, inner)

    # Allow non-factory-style decorator use (@decorator vs @decorator())
    if called_without_args:
        return real_decorator(pool_size)

    return real_decorator


def with_settings(*arg_settings, **kw_settings):
    """
    Decorator equivalent of ``fabric.context_managers.settings``.

    Allows you to wrap an entire function as if it was called inside a block
    with the ``settings`` context manager. This may be useful if you know you
    want a given setting applied to an entire function body, or wish to
    retrofit old code without indenting everything.

    For example, to turn aborts into warnings for an entire task function::

        @with_settings(warn_only=True)
        def foo():
            ...

    .. seealso:: `~fabric.context_managers.settings`
    .. versionadded:: 1.1
    """
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            with settings(*arg_settings, **kw_settings):
                return func(*args, **kwargs)
        return _wrap_as_new(func, inner)
    return outer

########NEW FILE########
__FILENAME__ = docs
from fabric.tasks import WrappedCallableTask


def unwrap_tasks(module, hide_nontasks=False):
    """
    Replace task objects on ``module`` with their wrapped functions instead.

    Specifically, look for instances of `~fabric.tasks.WrappedCallableTask` and
    replace them with their ``.wrapped`` attribute (the original decorated
    function.)

    This is intended for use with the Sphinx autodoc tool, to be run near the
    bottom of a project's ``conf.py``. It ensures that the autodoc extension
    will have full access to the "real" function, in terms of function
    signature and so forth. Without use of ``unwrap_tasks``, autodoc is unable
    to access the function signature (though it is able to see e.g.
    ``__doc__``.)

    For example, at the bottom of your ``conf.py``::

        from fabric.docs import unwrap_tasks
        import my_package.my_fabfile
        unwrap_tasks(my_package.my_fabfile)

    You can go above and beyond, and explicitly **hide** all non-task
    functions, by saying ``hide_nontasks=True``. This renames all objects
    failing the "is it a task?" check so they appear to be private, which will
    then cause autodoc to skip over them.

    ``hide_nontasks`` is thus useful when you have a fabfile mixing in
    subroutines with real tasks and want to document *just* the real tasks.
    
    If you run this within an actual Fabric-code-using session (instead of
    within a Sphinx ``conf.py``), please seek immediate medical attention.

    .. versionadded: 1.5

    .. seealso:: `~fabric.tasks.WrappedCallableTask`, `~fabric.decorators.task`
    """
    set_tasks = []
    for name, obj in vars(module).items():
        if isinstance(obj, WrappedCallableTask):
            setattr(module, obj.name, obj.wrapped)
            # Handle situation where a task's real name shadows a builtin.
            # If the builtin comes after the task in vars().items(), the object
            # we just setattr'd above will get re-hidden :(
            set_tasks.append(obj.name)
            # In the same vein, "privately" named wrapped functions whose task
            # name is public, needs to get renamed so autodoc picks it up.
            obj.wrapped.func_name = obj.name
        else:
            if name in set_tasks:
                continue
            has_docstring = getattr(obj, '__doc__', False)
            if hide_nontasks and has_docstring and not name.startswith('_'):
                setattr(module, '_%s' % name, obj)
                delattr(module, name)

########NEW FILE########
__FILENAME__ = exceptions
"""
Custom Fabric exception classes.

Most are simply distinct Exception subclasses for purposes of message-passing
(though typically still in actual error situations.)
"""


class NetworkError(Exception):
    # Must allow for calling with zero args/kwargs, since pickle is apparently
    # stupid with exceptions and tries to call it as such when passed around in
    # a multiprocessing.Queue.
    def __init__(self, message=None, wrapped=None):
        self.message = message
        self.wrapped = wrapped

    def __str__(self):
        return self.message

    def __repr__(self):
        return "%s(%s) => %r" % (
            self.__class__.__name__, self.message, self.wrapped
        )


class CommandTimeout(Exception):
    pass

########NEW FILE########
__FILENAME__ = io
from __future__ import with_statement

import sys
import time
import re
import socket
from select import select

from fabric.state import env, output, win32
from fabric.auth import get_password, set_password
import fabric.network
from fabric.network import ssh, normalize
from fabric.utils import RingBuffer
from fabric.exceptions import CommandTimeout


if win32:
    import msvcrt


def _endswith(char_list, substring):
    tail = char_list[-1 * len(substring):]
    substring = list(substring)
    return tail == substring


def _has_newline(bytelist):
    return '\r' in bytelist or '\n' in bytelist


def output_loop(*args, **kwargs):
    OutputLooper(*args, **kwargs).loop()


class OutputLooper(object):
    def __init__(self, chan, attr, stream, capture, timeout):
        self.chan = chan
        self.stream = stream
        self.capture = capture
        self.timeout = timeout
        self.read_func = getattr(chan, attr)
        self.prefix = "[%s] %s: " % (
            env.host_string,
            "out" if attr == 'recv' else "err"
        )
        self.printing = getattr(output, 'stdout' if (attr == 'recv') else 'stderr')
        self.linewise = (env.linewise or env.parallel)
        self.reprompt = False
        self.read_size = 4096
        self.write_buffer = RingBuffer([], maxlen=len(self.prefix))

    def _flush(self, text):
        self.stream.write(text)
        # Actually only flush if not in linewise mode.
        # When linewise is set (e.g. in parallel mode) flushing makes
        # doubling-up of line prefixes, and other mixed output, more likely.
        if not env.linewise:
            self.stream.flush()
        self.write_buffer.extend(text)

    def loop(self):
        """
        Loop, reading from <chan>.<attr>(), writing to <stream> and buffering to <capture>.

        Will raise `~fabric.exceptions.CommandTimeout` if network timeouts
        continue to be seen past the defined ``self.timeout`` threshold.
        (Timeouts before then are considered part of normal short-timeout fast
        network reading; see Fabric issue #733 for background.)
        """
        # Internal capture-buffer-like buffer, used solely for state keeping.
        # Unlike 'capture', nothing is ever purged from this.
        _buffer = []

        # Initialize loop variables
        initial_prefix_printed = False
        seen_cr = False
        line = []

        # Allow prefix to be turned off.
        if not env.output_prefix:
            self.prefix = ""

        start = time.time()
        while True:
            # Handle actual read
            try:
                bytelist = self.read_func(self.read_size)
            except socket.timeout:
                elapsed = time.time() - start
                if self.timeout is not None and elapsed > self.timeout:
                    raise CommandTimeout
                continue
            # Empty byte == EOS
            if bytelist == '':
                # If linewise, ensure we flush any leftovers in the buffer.
                if self.linewise and line:
                    self._flush(self.prefix)
                    self._flush("".join(line))
                break
            # A None capture variable implies that we're in open_shell()
            if self.capture is None:
                # Just print directly -- no prefixes, no capturing, nada
                # And since we know we're using a pty in this mode, just go
                # straight to stdout.
                self._flush(bytelist)
            # Otherwise, we're in run/sudo and need to handle capturing and
            # prompts.
            else:
                # Print to user
                if self.printing:
                    printable_bytes = bytelist
                    # Small state machine to eat \n after \r
                    if printable_bytes[-1] == "\r":
                        seen_cr = True
                    if printable_bytes[0] == "\n" and seen_cr:
                        printable_bytes = printable_bytes[1:]
                        seen_cr = False

                    while _has_newline(printable_bytes) and printable_bytes != "":
                        # at most 1 split !
                        cr = re.search("(\r\n|\r|\n)", printable_bytes)
                        if cr is None:
                            break
                        end_of_line = printable_bytes[:cr.start(0)]
                        printable_bytes = printable_bytes[cr.end(0):]

                        if not initial_prefix_printed:
                            self._flush(self.prefix)

                        if _has_newline(end_of_line):
                            end_of_line = ''

                        if self.linewise:
                            self._flush("".join(line) + end_of_line + "\n")
                            line = []
                        else:
                            self._flush(end_of_line + "\n")
                        initial_prefix_printed = False

                    if self.linewise:
                        line += [printable_bytes]
                    else:
                        if not initial_prefix_printed:
                            self._flush(self.prefix)
                            initial_prefix_printed = True
                        self._flush(printable_bytes)

                # Now we have handled printing, handle interactivity
                read_lines = re.split(r"(\r|\n|\r\n)", bytelist)
                for fragment in read_lines:
                    # Store in capture buffer
                    self.capture += fragment
                    # Store in internal buffer
                    _buffer += fragment
                    # Handle prompts
                    expected, response = self._get_prompt_response()
                    if expected:
                        del self.capture[-1 * len(expected):]
                        self.chan.sendall(str(response) + '\n')
                    else:
                        prompt = _endswith(self.capture, env.sudo_prompt)
                        try_again = (_endswith(self.capture, env.again_prompt + '\n')
                            or _endswith(self.capture, env.again_prompt + '\r\n'))
                        if prompt:
                            self.prompt()
                        elif try_again:
                            self.try_again()

        # Print trailing new line if the last thing we printed was our line
        # prefix.
        if self.prefix and "".join(self.write_buffer) == self.prefix:
            self._flush('\n')

    def prompt(self):
        # Obtain cached password, if any
        password = get_password(*normalize(env.host_string))
        # Remove the prompt itself from the capture buffer. This is
        # backwards compatible with Fabric 0.9.x behavior; the user
        # will still see the prompt on their screen (no way to avoid
        # this) but at least it won't clutter up the captured text.
        del self.capture[-1 * len(env.sudo_prompt):]
        # If the password we just tried was bad, prompt the user again.
        if (not password) or self.reprompt:
            # Print the prompt and/or the "try again" notice if
            # output is being hidden. In other words, since we need
            # the user's input, they need to see why we're
            # prompting them.
            if not self.printing:
                self._flush(self.prefix)
                if self.reprompt:
                    self._flush(env.again_prompt + '\n' + self.prefix)
                self._flush(env.sudo_prompt)
            # Prompt for, and store, password. Give empty prompt so the
            # initial display "hides" just after the actually-displayed
            # prompt from the remote end.
            self.chan.input_enabled = False
            password = fabric.network.prompt_for_password(
                prompt=" ", no_colon=True, stream=self.stream
            )
            self.chan.input_enabled = True
            # Update env.password, env.passwords if necessary
            user, host, port = normalize(env.host_string)
            set_password(user, host, port, password)
            # Reset reprompt flag
            self.reprompt = False
        # Send current password down the pipe
        self.chan.sendall(password + '\n')

    def try_again(self):
        # Remove text from capture buffer
        self.capture = self.capture[:len(env.again_prompt)]
        # Set state so we re-prompt the user at the next prompt.
        self.reprompt = True

    def _get_prompt_response(self):
        """
        Iterate through the request prompts dict and return the response and
        original request if we find a match
        """
        for tup in env.prompts.iteritems():
            if _endswith(self.capture, tup[0]):
                return tup
        return None, None


def input_loop(chan, using_pty):
    while not chan.exit_status_ready():
        if win32:
            have_char = msvcrt.kbhit()
        else:
            r, w, x = select([sys.stdin], [], [], 0.0)
            have_char = (r and r[0] == sys.stdin)
        if have_char and chan.input_enabled:
            # Send all local stdin to remote end's stdin
            byte = msvcrt.getch() if win32 else sys.stdin.read(1)
            chan.sendall(byte)
            # Optionally echo locally, if needed.
            if not using_pty and env.echo_stdin:
                # Not using fastprint() here -- it prints as 'user'
                # output level, don't want it to be accidentally hidden
                sys.stdout.write(byte)
                sys.stdout.flush()
        time.sleep(ssh.io_sleep)

########NEW FILE########
__FILENAME__ = job_queue
"""
Sliding-window-based job/task queue class (& example of use.)

May use ``multiprocessing.Process`` or ``threading.Thread`` objects as queue
items, though within Fabric itself only ``Process`` objects are used/supported.
"""

from __future__ import with_statement
import time
import Queue

from fabric.state import env
from fabric.network import ssh
from fabric.context_managers import settings


class JobQueue(object):
    """
    The goal of this class is to make a queue of processes to run, and go
    through them running X number at any given time. 

    So if the bubble is 5 start with 5 running and move the bubble of running
    procs along the queue looking something like this:

        Start
        ...........................
        [~~~~~]....................
        ___[~~~~~].................
        _________[~~~~~]...........
        __________________[~~~~~]..
        ____________________[~~~~~]
        ___________________________
                                End 
    """
    def __init__(self, max_running, comms_queue):
        """
        Setup the class to resonable defaults.
        """
        self._queued = []
        self._running = []
        self._completed = []
        self._num_of_jobs = 0
        self._max = max_running
        self._comms_queue = comms_queue
        self._finished = False
        self._closed = False
        self._debug = False

    def _all_alive(self):
        """
        Simply states if all procs are alive or not. Needed to determine when
        to stop looping, and pop dead procs off and add live ones.
        """
        if self._running:
            return all([x.is_alive() for x in self._running])
        else:
            return False

    def __len__(self):
        """
        Just going to use number of jobs as the JobQueue length.
        """
        return self._num_of_jobs

    def close(self):
        """
        A sanity check, so that the need to care about new jobs being added in
        the last throws of the job_queue's run are negated.
        """
        if self._debug:
            print("job queue closed.")

        self._closed = True

    def append(self, process):
        """
        Add the Process() to the queue, so that later it can be checked up on.
        That is if the JobQueue is still open.

        If the queue is closed, this will just silently do nothing.

        To get data back out of this process, give ``process`` access to a
        ``multiprocessing.Queue`` object, and give it here as ``queue``. Then
        ``JobQueue.run`` will include the queue's contents in its return value.
        """
        if not self._closed:
            self._queued.append(process)
            self._num_of_jobs += 1
            if self._debug:
                print("job queue appended %s." % process.name)

    def run(self):
        """
        This is the workhorse. It will take the intial jobs from the _queue,
        start them, add them to _running, and then go into the main running
        loop.

        This loop will check for done procs, if found, move them out of
        _running into _completed. It also checks for a _running queue with open
        spots, which it will then fill as discovered.

        To end the loop, there have to be no running procs, and no more procs
        to be run in the queue.

        This function returns an iterable of all its children's exit codes.
        """
        def _advance_the_queue():
            """
            Helper function to do the job of poping a new proc off the queue
            start it, then add it to the running queue. This will eventually
            depleate the _queue, which is a condition of stopping the running
            while loop.

            It also sets the env.host_string from the job.name, so that fabric
            knows that this is the host to be making connections on.
            """
            job = self._queued.pop()
            if self._debug:
                print("Popping '%s' off the queue and starting it" % job.name)
            with settings(clean_revert=True, host_string=job.name, host=job.name):
                job.start()
            self._running.append(job)

        # Prep return value so we can start filling it during main loop
        results = {}
        for job in self._queued:
            results[job.name] = dict.fromkeys(('exit_code', 'results'))

        if not self._closed:
            raise Exception("Need to close() before starting.")

        if self._debug:
            print("Job queue starting.")

        while len(self._running) < self._max:
            _advance_the_queue()

        # Main loop!
        while not self._finished:
            while len(self._running) < self._max and self._queued:
                _advance_the_queue()

            if not self._all_alive():
                for id, job in enumerate(self._running):
                    if not job.is_alive():
                        if self._debug:
                            print("Job queue found finished proc: %s." %
                                    job.name)
                        done = self._running.pop(id)
                        self._completed.append(done)

                if self._debug:
                    print("Job queue has %d running." % len(self._running))

            if not (self._queued or self._running):
                if self._debug:
                    print("Job queue finished.")

                for job in self._completed:
                    job.join()

                self._finished = True

            # Each loop pass, try pulling results off the queue to keep its
            # size down. At this point, we don't actually care if any results
            # have arrived yet; they will be picked up after the main loop.
            self._fill_results(results)

            time.sleep(ssh.io_sleep)

        # Consume anything left in the results queue. Note that there is no
        # need to block here, as the main loop ensures that all workers will
        # already have finished.
        self._fill_results(results)

        # Attach exit codes now that we're all done & have joined all jobs
        for job in self._completed:
            results[job.name]['exit_code'] = job.exitcode

        return results

    def _fill_results(self, results):
        """
        Attempt to pull data off self._comms_queue and add to 'results' dict.
        If no data is available (i.e. the queue is empty), bail immediately.
        """
        while True:
            try:
                datum = self._comms_queue.get_nowait()
                results[datum['name']]['results'] = datum['result']
            except Queue.Empty:
                break


#### Sample

def try_using(parallel_type):
    """
    This will run the queue through it's paces, and show a simple way of using
    the job queue.
    """

    def print_number(number):
        """
        Simple function to give a simple task to execute.
        """
        print(number)

    if parallel_type == "multiprocessing":
        from multiprocessing import Process as Bucket

    elif parallel_type == "threading":
        from threading import Thread as Bucket

    # Make a job_queue with a bubble of len 5, and have it print verbosely
    jobs = JobQueue(5)
    jobs._debug = True

    # Add 20 procs onto the stack
    for x in range(20):
        jobs.append(Bucket(
            target=print_number,
            args=[x],
            kwargs={},
            ))

    # Close up the queue and then start it's execution
    jobs.close()
    jobs.run()


if __name__ == '__main__':
    try_using("multiprocessing")
    try_using("threading")

########NEW FILE########
__FILENAME__ = main
"""
This module contains Fab's `main` method plus related subroutines.

`main` is executed as the command line ``fab`` program and takes care of
parsing options and commands, loading the user settings file, loading a
fabfile, and executing the commands given.

The other callables defined in this module are internal only. Anything useful
to individuals leveraging Fabric as a library, should be kept elsewhere.
"""
import getpass
from operator import isMappingType
from optparse import OptionParser
import os
import sys
import types

# For checking callables against the API, & easy mocking
from fabric import api, state, colors
from fabric.contrib import console, files, project

from fabric.network import disconnect_all, ssh
from fabric.state import env_options
from fabric.tasks import Task, execute, get_task_details
from fabric.task_utils import _Dict, crawl
from fabric.utils import abort, indent, warn, _pty_size


# One-time calculation of "all internal callables" to avoid doing this on every
# check of a given fabfile callable (in is_classic_task()).
_modules = [api, project, files, console, colors]
_internals = reduce(lambda x, y: x + filter(callable, vars(y).values()),
    _modules,
    []
)


# Module recursion cache
class _ModuleCache(object):
    """
    Set-like object operating on modules and storing __name__s internally.
    """
    def __init__(self):
        self.cache = set()

    def __contains__(self, value):
        return value.__name__ in self.cache

    def add(self, value):
        return self.cache.add(value.__name__)

    def clear(self):
        return self.cache.clear()

_seen = _ModuleCache()


def load_settings(path):
    """
    Take given file path and return dictionary of any key=value pairs found.

    Usage docs are in sites/docs/usage/fab.rst, in "Settings files."
    """
    if os.path.exists(path):
        comments = lambda s: s and not s.startswith("#")
        settings = filter(comments, open(path, 'r'))
        return dict((k.strip(), v.strip()) for k, _, v in
            [s.partition('=') for s in settings])
    # Handle nonexistent or empty settings file
    return {}


def _is_package(path):
    """
    Is the given path a Python package?
    """
    return (
        os.path.isdir(path)
        and os.path.exists(os.path.join(path, '__init__.py'))
    )


def find_fabfile(names=None):
    """
    Attempt to locate a fabfile, either explicitly or by searching parent dirs.

    Usage docs are in sites/docs/usage/fabfiles.rst, in "Fabfile discovery."
    """
    # Obtain env value if not given specifically
    if names is None:
        names = [state.env.fabfile]
    # Create .py version if necessary
    if not names[0].endswith('.py'):
        names += [names[0] + '.py']
    # Does the name contain path elements?
    if os.path.dirname(names[0]):
        # If so, expand home-directory markers and test for existence
        for name in names:
            expanded = os.path.expanduser(name)
            if os.path.exists(expanded):
                if name.endswith('.py') or _is_package(expanded):
                    return os.path.abspath(expanded)
    else:
        # Otherwise, start in cwd and work downwards towards filesystem root
        path = '.'
        # Stop before falling off root of filesystem (should be platform
        # agnostic)
        while os.path.split(os.path.abspath(path))[1]:
            for name in names:
                joined = os.path.join(path, name)
                if os.path.exists(joined):
                    if name.endswith('.py') or _is_package(joined):
                        return os.path.abspath(joined)
            path = os.path.join('..', path)
    # Implicit 'return None' if nothing was found


def is_classic_task(tup):
    """
    Takes (name, object) tuple, returns True if it's a non-Fab public callable.
    """
    name, func = tup
    try:
        is_classic = (
            callable(func)
            and (func not in _internals)
            and not name.startswith('_')
        )
    # Handle poorly behaved __eq__ implementations
    except (ValueError, TypeError):
        is_classic = False
    return is_classic


def load_fabfile(path, importer=None):
    """
    Import given fabfile path and return (docstring, callables).

    Specifically, the fabfile's ``__doc__`` attribute (a string) and a
    dictionary of ``{'name': callable}`` containing all callables which pass
    the "is a Fabric task" test.
    """
    if importer is None:
        importer = __import__
    # Get directory and fabfile name
    directory, fabfile = os.path.split(path)
    # If the directory isn't in the PYTHONPATH, add it so our import will work
    added_to_path = False
    index = None
    if directory not in sys.path:
        sys.path.insert(0, directory)
        added_to_path = True
    # If the directory IS in the PYTHONPATH, move it to the front temporarily,
    # otherwise other fabfiles -- like Fabric's own -- may scoop the intended
    # one.
    else:
        i = sys.path.index(directory)
        if i != 0:
            # Store index for later restoration
            index = i
            # Add to front, then remove from original position
            sys.path.insert(0, directory)
            del sys.path[i + 1]
    # Perform the import (trimming off the .py)
    imported = importer(os.path.splitext(fabfile)[0])
    # Remove directory from path if we added it ourselves (just to be neat)
    if added_to_path:
        del sys.path[0]
    # Put back in original index if we moved it
    if index is not None:
        sys.path.insert(index + 1, directory)
        del sys.path[0]

    # Actually load tasks
    docstring, new_style, classic, default = load_tasks_from_module(imported)
    tasks = new_style if state.env.new_style_tasks else classic
    # Clean up after ourselves
    _seen.clear()
    return docstring, tasks, default


def load_tasks_from_module(imported):
    """
    Handles loading all of the tasks for a given `imported` module
    """
    # Obey the use of <module>.__all__ if it is present
    imported_vars = vars(imported)
    if "__all__" in imported_vars:
        imported_vars = [(name, imported_vars[name]) for name in \
                         imported_vars if name in imported_vars["__all__"]]
    else:
        imported_vars = imported_vars.items()
    # Return a two-tuple value.  First is the documentation, second is a
    # dictionary of callables only (and don't include Fab operations or
    # underscored callables)
    new_style, classic, default = extract_tasks(imported_vars)
    return imported.__doc__, new_style, classic, default


def extract_tasks(imported_vars):
    """
    Handle extracting tasks from a given list of variables
    """
    new_style_tasks = _Dict()
    classic_tasks = {}
    default_task = None
    if 'new_style_tasks' not in state.env:
        state.env.new_style_tasks = False
    for tup in imported_vars:
        name, obj = tup
        if is_task_object(obj):
            state.env.new_style_tasks = True
            # Use instance.name if defined
            if obj.name and obj.name != 'undefined':
                new_style_tasks[obj.name] = obj
            else:
                obj.name = name
                new_style_tasks[name] = obj
            # Handle aliasing
            if obj.aliases is not None:
                for alias in obj.aliases:
                    new_style_tasks[alias] = obj
            # Handle defaults
            if obj.is_default:
                default_task = obj
        elif is_classic_task(tup):
            classic_tasks[name] = obj
        elif is_task_module(obj):
            docs, newstyle, classic, default = load_tasks_from_module(obj)
            for task_name, task in newstyle.items():
                if name not in new_style_tasks:
                    new_style_tasks[name] = _Dict()
                new_style_tasks[name][task_name] = task
            if default is not None:
                new_style_tasks[name].default = default
    return new_style_tasks, classic_tasks, default_task


def is_task_module(a):
    """
    Determine if the provided value is a task module
    """
    #return (type(a) is types.ModuleType and
    #        any(map(is_task_object, vars(a).values())))
    if isinstance(a, types.ModuleType) and a not in _seen:
        # Flag module as seen
        _seen.add(a)
        # Signal that we need to check it out
        return True


def is_task_object(a):
    """
    Determine if the provided value is a ``Task`` object.

    This returning True signals that all tasks within the fabfile
    module must be Task objects.
    """
    return isinstance(a, Task) and a.use_task_objects


def parse_options():
    """
    Handle command-line options with optparse.OptionParser.

    Return list of arguments, largely for use in `parse_arguments`.
    """
    #
    # Initialize
    #

    parser = OptionParser(
        usage=("fab [options] <command>"
               "[:arg1,arg2=val2,host=foo,hosts='h1;h2',...] ..."))

    #
    # Define options that don't become `env` vars (typically ones which cause
    # Fabric to do something other than its normal execution, such as
    # --version)
    #

    # Display info about a specific command
    parser.add_option('-d', '--display',
        metavar='NAME',
        help="print detailed info about command NAME"
    )

    # Control behavior of --list
    LIST_FORMAT_OPTIONS = ('short', 'normal', 'nested')
    parser.add_option('-F', '--list-format',
        choices=LIST_FORMAT_OPTIONS,
        default='normal',
        metavar='FORMAT',
        help="formats --list, choices: %s" % ", ".join(LIST_FORMAT_OPTIONS)
    )

    parser.add_option('-I', '--initial-password-prompt',
        action='store_true',
        default=False,
        help="Force password prompt up-front"
    )

    # List Fab commands found in loaded fabfiles/source files
    parser.add_option('-l', '--list',
        action='store_true',
        dest='list_commands',
        default=False,
        help="print list of possible commands and exit"
    )

    # Allow setting of arbitrary env vars at runtime.
    parser.add_option('--set',
        metavar="KEY=VALUE,...",
        dest='env_settings',
        default="",
        help="comma separated KEY=VALUE pairs to set Fab env vars"
    )

    # Like --list, but text processing friendly
    parser.add_option('--shortlist',
        action='store_true',
        dest='shortlist',
        default=False,
        help="alias for -F short --list"
    )

    # Version number (optparse gives you --version but we have to do it
    # ourselves to get -V too. sigh)
    parser.add_option('-V', '--version',
        action='store_true',
        dest='show_version',
        default=False,
        help="show program's version number and exit"
    )

    #
    # Add in options which are also destined to show up as `env` vars.
    #

    for option in env_options:
        parser.add_option(option)

    #
    # Finalize
    #

    # Return three-tuple of parser + the output from parse_args (opt obj, args)
    opts, args = parser.parse_args()
    return parser, opts, args


def _is_task(name, value):
    """
    Is the object a task as opposed to e.g. a dict or int?
    """
    return is_classic_task((name, value)) or is_task_object(value)


def _sift_tasks(mapping):
    tasks, collections = [], []
    for name, value in mapping.iteritems():
        if _is_task(name, value):
            tasks.append(name)
        elif isMappingType(value):
            collections.append(name)
    tasks = sorted(tasks)
    collections = sorted(collections)
    return tasks, collections


def _task_names(mapping):
    """
    Flatten & sort task names in a breadth-first fashion.

    Tasks are always listed before submodules at the same level, but within
    those two groups, sorting is alphabetical.
    """
    tasks, collections = _sift_tasks(mapping)
    for collection in collections:
        module = mapping[collection]
        if hasattr(module, 'default'):
            tasks.append(collection)
        join = lambda x: ".".join((collection, x))
        tasks.extend(map(join, _task_names(module)))
    return tasks


def _print_docstring(docstrings, name):
    if not docstrings:
        return False
    docstring = crawl(name, state.commands).__doc__
    if isinstance(docstring, basestring):
        return docstring


def _normal_list(docstrings=True):
    result = []
    task_names = _task_names(state.commands)
    # Want separator between name, description to be straight col
    max_len = reduce(lambda a, b: max(a, len(b)), task_names, 0)
    sep = '  '
    trail = '...'
    max_width = _pty_size()[1] - 1 - len(trail)
    for name in task_names:
        output = None
        docstring = _print_docstring(docstrings, name)
        if docstring:
            lines = filter(None, docstring.splitlines())
            first_line = lines[0].strip()
            # Truncate it if it's longer than N chars
            size = max_width - (max_len + len(sep) + len(trail))
            if len(first_line) > size:
                first_line = first_line[:size] + trail
            output = name.ljust(max_len) + sep + first_line
        # Or nothing (so just the name)
        else:
            output = name
        result.append(indent(output))
    return result


def _nested_list(mapping, level=1):
    result = []
    tasks, collections = _sift_tasks(mapping)
    # Tasks come first
    result.extend(map(lambda x: indent(x, spaces=level * 4), tasks))
    for collection in collections:
        module = mapping[collection]
        # Section/module "header"
        result.append(indent(collection + ":", spaces=level * 4))
        # Recurse
        result.extend(_nested_list(module, level + 1))
    return result

COMMANDS_HEADER = "Available commands"
NESTED_REMINDER = " (remember to call as module.[...].task)"


def list_commands(docstring, format_):
    """
    Print all found commands/tasks, then exit. Invoked with ``-l/--list.``

    If ``docstring`` is non-empty, it will be printed before the task list.

    ``format_`` should conform to the options specified in
    ``LIST_FORMAT_OPTIONS``, e.g. ``"short"``, ``"normal"``.
    """
    # Short-circuit with simple short output
    if format_ == "short":
        return _task_names(state.commands)
    # Otherwise, handle more verbose modes
    result = []
    # Docstring at top, if applicable
    if docstring:
        trailer = "\n" if not docstring.endswith("\n") else ""
        result.append(docstring + trailer)
    header = COMMANDS_HEADER
    if format_ == "nested":
        header += NESTED_REMINDER
    result.append(header + ":\n")
    c = _normal_list() if format_ == "normal" else _nested_list(state.commands)
    result.extend(c)
    return result


def display_command(name):
    """
    Print command function's docstring, then exit. Invoked with -d/--display.
    """
    # Sanity check
    command = crawl(name, state.commands)
    if command is None:
        msg = "Task '%s' does not appear to exist. Valid task names:\n%s"
        abort(msg % (name, "\n".join(_normal_list(False))))
    # Print out nicely presented docstring if found
    if hasattr(command, '__details__'):
        task_details = command.__details__()
    else:
        task_details = get_task_details(command)
    if task_details:
        print("Displaying detailed information for task '%s':" % name)
        print('')
        print(indent(task_details, strip=True))
        print('')
    # Or print notice if not
    else:
        print("No detailed information available for task '%s':" % name)
    sys.exit(0)


def _escape_split(sep, argstr):
    """
    Allows for escaping of the separator: e.g. task:arg='foo\, bar'

    It should be noted that the way bash et. al. do command line parsing, those
    single quotes are required.
    """
    escaped_sep = r'\%s' % sep

    if escaped_sep not in argstr:
        return argstr.split(sep)

    before, _, after = argstr.partition(escaped_sep)
    startlist = before.split(sep)  # a regular split is fine here
    unfinished = startlist[-1]
    startlist = startlist[:-1]

    # recurse because there may be more escaped separators
    endlist = _escape_split(sep, after)

    # finish building the escaped value. we use endlist[0] becaue the first
    # part of the string sent in recursion is the rest of the escaped value.
    unfinished += sep + endlist[0]

    return startlist + [unfinished] + endlist[1:]  # put together all the parts


def parse_arguments(arguments):
    """
    Parse string list into list of tuples: command, args, kwargs, hosts, roles.

    See sites/docs/usage/fab.rst, section on "per-task arguments" for details.
    """
    cmds = []
    for cmd in arguments:
        args = []
        kwargs = {}
        hosts = []
        roles = []
        exclude_hosts = []
        if ':' in cmd:
            cmd, argstr = cmd.split(':', 1)
            for pair in _escape_split(',', argstr):
                result = _escape_split('=', pair)
                if len(result) > 1:
                    k, v = result
                    # Catch, interpret host/hosts/role/roles/exclude_hosts
                    # kwargs
                    if k in ['host', 'hosts', 'role', 'roles', 'exclude_hosts']:
                        if k == 'host':
                            hosts = [v.strip()]
                        elif k == 'hosts':
                            hosts = [x.strip() for x in v.split(';')]
                        elif k == 'role':
                            roles = [v.strip()]
                        elif k == 'roles':
                            roles = [x.strip() for x in v.split(';')]
                        elif k == 'exclude_hosts':
                            exclude_hosts = [x.strip() for x in v.split(';')]
                    # Otherwise, record as usual
                    else:
                        kwargs[k] = v
                else:
                    args.append(result[0])
        cmds.append((cmd, args, kwargs, hosts, roles, exclude_hosts))
    return cmds


def parse_remainder(arguments):
    """
    Merge list of "remainder arguments" into a single command string.
    """
    return ' '.join(arguments)


def update_output_levels(show, hide):
    """
    Update state.output values as per given comma-separated list of key names.

    For example, ``update_output_levels(show='debug,warnings')`` is
    functionally equivalent to ``state.output['debug'] = True ;
    state.output['warnings'] = True``. Conversely, anything given to ``hide``
    sets the values to ``False``.
    """
    if show:
        for key in show.split(','):
            state.output[key] = True
    if hide:
        for key in hide.split(','):
            state.output[key] = False


def show_commands(docstring, format, code=0):
    print("\n".join(list_commands(docstring, format)))
    sys.exit(code)


def main(fabfile_locations=None):
    """
    Main command-line execution loop.
    """
    try:
        # Parse command line options
        parser, options, arguments = parse_options()

        # Handle regular args vs -- args
        arguments = parser.largs
        remainder_arguments = parser.rargs

        # Allow setting of arbitrary env keys.
        # This comes *before* the "specific" env_options so that those may
        # override these ones. Specific should override generic, if somebody
        # was silly enough to specify the same key in both places.
        # E.g. "fab --set shell=foo --shell=bar" should have env.shell set to
        # 'bar', not 'foo'.
        for pair in _escape_split(',', options.env_settings):
            pair = _escape_split('=', pair)
            # "--set x" => set env.x to True
            # "--set x=" => set env.x to ""
            key = pair[0]
            value = True
            if len(pair) == 2:
                value = pair[1]
            state.env[key] = value

        # Update env with any overridden option values
        # NOTE: This needs to remain the first thing that occurs
        # post-parsing, since so many things hinge on the values in env.
        for option in env_options:
            state.env[option.dest] = getattr(options, option.dest)

        # Handle --hosts, --roles, --exclude-hosts (comma separated string =>
        # list)
        for key in ['hosts', 'roles', 'exclude_hosts']:
            if key in state.env and isinstance(state.env[key], basestring):
                state.env[key] = state.env[key].split(',')

        # Feed the env.tasks : tasks that are asked to be executed.
        state.env['tasks'] = arguments

        # Handle output control level show/hide
        update_output_levels(show=options.show, hide=options.hide)

        # Handle version number option
        if options.show_version:
            print("Fabric %s" % state.env.version)
            print("Paramiko %s" % ssh.__version__)
            sys.exit(0)

        # Load settings from user settings file, into shared env dict.
        state.env.update(load_settings(state.env.rcfile))

        # Find local fabfile path or abort
        fabfile = find_fabfile(fabfile_locations)
        if not fabfile and not remainder_arguments:
            abort("""Couldn't find any fabfiles!

Remember that -f can be used to specify fabfile path, and use -h for help.""")

        # Store absolute path to fabfile in case anyone needs it
        state.env.real_fabfile = fabfile

        # Load fabfile (which calls its module-level code, including
        # tweaks to env values) and put its commands in the shared commands
        # dict
        default = None
        if fabfile:
            docstring, callables, default = load_fabfile(fabfile)
            state.commands.update(callables)

        # Handle case where we were called bare, i.e. just "fab", and print
        # a help message.
        actions = (options.list_commands, options.shortlist, options.display,
            arguments, remainder_arguments, default)
        if not any(actions):
            parser.print_help()
            sys.exit(1)

        # Abort if no commands found
        if not state.commands and not remainder_arguments:
            abort("Fabfile didn't contain any commands!")

        # Now that we're settled on a fabfile, inform user.
        if state.output.debug:
            if fabfile:
                print("Using fabfile '%s'" % fabfile)
            else:
                print("No fabfile loaded -- remainder command only")

        # Shortlist is now just an alias for the "short" list format;
        # it overrides use of --list-format if somebody were to specify both
        if options.shortlist:
            options.list_format = 'short'
            options.list_commands = True

        # List available commands
        if options.list_commands:
            show_commands(docstring, options.list_format)

        # Handle show (command-specific help) option
        if options.display:
            display_command(options.display)

        # If user didn't specify any commands to run, show help
        if not (arguments or remainder_arguments or default):
            parser.print_help()
            sys.exit(0)  # Or should it exit with error (1)?

        # Parse arguments into commands to run (plus args/kwargs/hosts)
        commands_to_run = parse_arguments(arguments)

        # Parse remainders into a faux "command" to execute
        remainder_command = parse_remainder(remainder_arguments)

        # Figure out if any specified task names are invalid
        unknown_commands = []
        for tup in commands_to_run:
            if crawl(tup[0], state.commands) is None:
                unknown_commands.append(tup[0])

        # Abort if any unknown commands were specified
        if unknown_commands:
            warn("Command(s) not found:\n%s" \
                % indent(unknown_commands))
            show_commands(None, options.list_format, 1)

        # Generate remainder command and insert into commands, commands_to_run
        if remainder_command:
            r = '<remainder>'
            state.commands[r] = lambda: api.run(remainder_command)
            commands_to_run.append((r, [], {}, [], [], []))

        # Ditto for a default, if found
        if not commands_to_run and default:
            commands_to_run.append((default.name, [], {}, [], [], []))

        # Initial password prompt, if requested
        if options.initial_password_prompt:
            prompt = "Initial value for env.password: "
            state.env.password = getpass.getpass(prompt)

        if state.output.debug:
            names = ", ".join(x[0] for x in commands_to_run)
            print("Commands to run: %s" % names)

        # At this point all commands must exist, so execute them in order.
        for name, args, kwargs, arg_hosts, arg_roles, arg_exclude_hosts in commands_to_run:
            execute(
                name,
                hosts=arg_hosts,
                roles=arg_roles,
                exclude_hosts=arg_exclude_hosts,
                *args, **kwargs
            )
        # If we got here, no errors occurred, so print a final note.
        if state.output.status:
            print("\nDone.")
    except SystemExit:
        # a number of internal functions might raise this one.
        raise
    except KeyboardInterrupt:
        if state.output.status:
            sys.stderr.write("\nStopped.\n")
        sys.exit(1)
    except:
        sys.excepthook(*sys.exc_info())
        # we might leave stale threads if we don't explicitly exit()
        sys.exit(1)
    finally:
        disconnect_all()
    sys.exit(0)

########NEW FILE########
__FILENAME__ = network
"""
Classes and subroutines dealing with network connections and related topics.
"""

from __future__ import with_statement

from functools import wraps
import getpass
import os
import re
import time
import socket
import sys
from StringIO import StringIO


from fabric.auth import get_password, set_password
from fabric.utils import abort, handle_prompt_abort, warn
from fabric.exceptions import NetworkError

try:
    import warnings
    warnings.simplefilter('ignore', DeprecationWarning)
    import paramiko as ssh
except ImportError, e:
    import traceback
    traceback.print_exc()
    msg = """
There was a problem importing our SSH library (see traceback above).
Please make sure all dependencies are installed and importable.
""".rstrip()
    sys.stderr.write(msg + '\n')
    sys.exit(1)


ipv6_regex = re.compile('^\[?(?P<host>[0-9A-Fa-f:]+)\]?(:(?P<port>\d+))?$')


def direct_tcpip(client, host, port):
    return client.get_transport().open_channel(
        'direct-tcpip',
        (host, int(port)),
        ('', 0)
    )


def is_key_load_error(e):
    return (
        e.__class__ is ssh.SSHException
        and 'Unable to parse key file' in str(e)
    )


def _tried_enough(tries):
    from fabric.state import env
    return tries >= env.connection_attempts


def get_gateway(host, port, cache, replace=False):
    """
    Create and return a gateway socket, if one is needed.

    This function checks ``env`` for gateway or proxy-command settings and
    returns the necessary socket-like object for use by a final host
    connection.

    :param host:
        Hostname of target server.

    :param port:
        Port to connect to on target server.

    :param cache:
        A ``HostConnectionCache`` object, in which gateway ``SSHClient``
        objects are to be retrieved/cached.

    :param replace:
        Whether to forcibly replace a cached gateway client object.

    :returns:
        A ``socket.socket``-like object, or ``None`` if none was created.
    """
    from fabric.state import env, output
    sock = None
    proxy_command = ssh_config().get('proxycommand', None)
    if env.gateway:
        gateway = normalize_to_string(env.gateway)
        # ensure initial gateway connection
        if replace or gateway not in cache:
            if output.debug:
                print "Creating new gateway connection to %r" % gateway
            cache[gateway] = connect(*normalize(gateway) + (cache, False))
        # now we should have an open gw connection and can ask it for a
        # direct-tcpip channel to the real target. (bypass cache's own
        # __getitem__ override to avoid hilarity - this is usually called
        # within that method.)
        sock = direct_tcpip(dict.__getitem__(cache, gateway), host, port)
    elif proxy_command:
        sock = ssh.ProxyCommand(proxy_command)
    return sock


class HostConnectionCache(dict):
    """
    Dict subclass allowing for caching of host connections/clients.

    This subclass will intelligently create new client connections when keys
    are requested, or return previously created connections instead.

    It also handles creating new socket-like objects when required to implement
    gateway connections and `ProxyCommand`, and handing them to the inner
    connection methods.

    Key values are the same as host specifiers throughout Fabric: optional
    username + ``@``, mandatory hostname, optional ``:`` + port number.
    Examples:

    * ``example.com`` - typical Internet host address.
    * ``firewall`` - atypical, but still legal, local host address.
    * ``user@example.com`` - with specific username attached.
    * ``bob@smith.org:222`` - with specific nonstandard port attached.

    When the username is not given, ``env.user`` is used. ``env.user``
    defaults to the currently running user at startup but may be overwritten by
    user code or by specifying a command-line flag.

    Note that differing explicit usernames for the same hostname will result in
    multiple client connections being made. For example, specifying
    ``user1@example.com`` will create a connection to ``example.com``, logged
    in as ``user1``; later specifying ``user2@example.com`` will create a new,
    2nd connection as ``user2``.

    The same applies to ports: specifying two different ports will result in
    two different connections to the same host being made. If no port is given,
    22 is assumed, so ``example.com`` is equivalent to ``example.com:22``.
    """
    def connect(self, key):
        """
        Force a new connection to ``key`` host string.
        """
        user, host, port = normalize(key)
        key = normalize_to_string(key)
        self[key] = connect(user, host, port, cache=self)

    def __getitem__(self, key):
        """
        Autoconnect + return connection object
        """
        key = normalize_to_string(key)
        if key not in self:
            self.connect(key)
        return dict.__getitem__(self, key)

    #
    # Dict overrides that normalize input keys
    #

    def __setitem__(self, key, value):
        return dict.__setitem__(self, normalize_to_string(key), value)

    def __delitem__(self, key):
        return dict.__delitem__(self, normalize_to_string(key))

    def __contains__(self, key):
        return dict.__contains__(self, normalize_to_string(key))


def ssh_config(host_string=None):
    """
    Return ssh configuration dict for current env.host_string host value.

    Memoizes the loaded SSH config file, but not the specific per-host results.

    This function performs the necessary "is SSH config enabled?" checks and
    will simply return an empty dict if not. If SSH config *is* enabled and the
    value of env.ssh_config_path is not a valid file, it will abort.

    May give an explicit host string as ``host_string``.
    """
    from fabric.state import env
    dummy = {}
    if not env.use_ssh_config:
        return dummy
    if '_ssh_config' not in env:
        try:
            conf = ssh.SSHConfig()
            path = os.path.expanduser(env.ssh_config_path)
            with open(path) as fd:
                conf.parse(fd)
                env._ssh_config = conf
        except IOError:
            warn("Unable to load SSH config file '%s'" % path)
            return dummy
    host = parse_host_string(host_string or env.host_string)['host']
    return env._ssh_config.lookup(host)


def key_filenames():
    """
    Returns list of SSH key filenames for the current env.host_string.

    Takes into account ssh_config and env.key_filename, including normalization
    to a list. Also performs ``os.path.expanduser`` expansion on any key
    filenames.
    """
    from fabric.state import env
    keys = env.key_filename
    # For ease of use, coerce stringish key filename into list
    if isinstance(env.key_filename, basestring) or env.key_filename is None:
        keys = [keys]
    # Strip out any empty strings (such as the default value...meh)
    keys = filter(bool, keys)
    # Honor SSH config
    conf = ssh_config()
    if 'identityfile' in conf:
        # Assume a list here as we require Paramiko 1.10+
        keys.extend(conf['identityfile'])
    return map(os.path.expanduser, keys)


def key_from_env(passphrase=None):
    """
    Returns a paramiko-ready key from a text string of a private key
    """
    from fabric.state import env, output

    if 'key' in env:
        if output.debug:
            # NOTE: this may not be the most secure thing; OTOH anybody running
            # the process must by definition have access to the key value,
            # so only serious problem is if they're logging the output.
            sys.stderr.write("Trying to honor in-memory key %r\n" % env.key)
        for pkey_class in (ssh.rsakey.RSAKey, ssh.dsskey.DSSKey):
            if output.debug:
                sys.stderr.write("Trying to load it as %s\n" % pkey_class)
            try:
                return pkey_class.from_private_key(StringIO(env.key), passphrase)
            except Exception, e:
                # File is valid key, but is encrypted: raise it, this will
                # cause cxn loop to prompt for passphrase & retry
                if 'Private key file is encrypted' in e:
                    raise
                # Otherwise, it probably means it wasn't a valid key of this
                # type, so try the next one.
                else:
                    pass


def parse_host_string(host_string):
    # Split host_string to user (optional) and host/port
    user_hostport = host_string.rsplit('@', 1)
    hostport = user_hostport.pop()
    user = user_hostport[0] if user_hostport and user_hostport[0] else None

    # Split host/port string to host and optional port
    # For IPv6 addresses square brackets are mandatory for host/port separation
    if hostport.count(':') > 1:
        # Looks like IPv6 address
        r = ipv6_regex.match(hostport).groupdict()
        host = r['host'] or None
        port = r['port'] or None
    else:
        # Hostname or IPv4 address
        host_port = hostport.rsplit(':', 1)
        host = host_port.pop(0) or None
        port = host_port[0] if host_port and host_port[0] else None

    return {'user': user, 'host': host, 'port': port}


def normalize(host_string, omit_port=False):
    """
    Normalizes a given host string, returning explicit host, user, port.

    If ``omit_port`` is given and is True, only the host and user are returned.

    This function will process SSH config files if Fabric is configured to do
    so, and will use them to fill in some default values or swap in hostname
    aliases.
    """
    from fabric.state import env
    # Gracefully handle "empty" input by returning empty output
    if not host_string:
        return ('', '') if omit_port else ('', '', '')
    # Parse host string (need this early on to look up host-specific ssh_config
    # values)
    r = parse_host_string(host_string)
    host = r['host']
    # Env values (using defaults if somehow earlier defaults were replaced with
    # empty values)
    user = env.user or env.local_user
    port = env.port or env.default_port
    # SSH config data
    conf = ssh_config(host_string)
    # Only use ssh_config values if the env value appears unmodified from
    # the true defaults. If the user has tweaked them, that new value
    # takes precedence.
    if user == env.local_user and 'user' in conf:
        user = conf['user']
    if port == env.default_port and 'port' in conf:
        port = conf['port']
    # Also override host if needed
    if 'hostname' in conf:
        host = conf['hostname']
    # Merge explicit user/port values with the env/ssh_config derived ones
    # (Host is already done at this point.)
    user = r['user'] or user
    port = r['port'] or port
    if omit_port:
        return user, host
    return user, host, port


def to_dict(host_string):
    user, host, port = normalize(host_string)
    return {
        'user': user, 'host': host, 'port': port, 'host_string': host_string
    }


def from_dict(arg):
    return join_host_strings(arg['user'], arg['host'], arg['port'])


def denormalize(host_string):
    """
    Strips out default values for the given host string.

    If the user part is the default user, it is removed;
    if the port is port 22, it also is removed.
    """
    from fabric.state import env

    r = parse_host_string(host_string)
    user = ''
    if r['user'] is not None and r['user'] != env.user:
        user = r['user'] + '@'
    port = ''
    if r['port'] is not None and r['port'] != '22':
        port = ':' + r['port']
    host = r['host']
    host = '[%s]' % host if port and host.count(':') > 1 else host
    return user + host + port


def join_host_strings(user, host, port=None):
    """
    Turns user/host/port strings into ``user@host:port`` combined string.

    This function is not responsible for handling missing user/port strings;
    for that, see the ``normalize`` function.

    If ``host`` looks like IPv6 address, it will be enclosed in square brackets

    If ``port`` is omitted, the returned string will be of the form
    ``user@host``.
    """
    if port:
        # Square brackets are necessary for IPv6 host/port separation
        template = "%s@[%s]:%s" if host.count(':') > 1 else "%s@%s:%s"
        return template % (user, host, port)
    else:
        return "%s@%s" % (user, host)


def normalize_to_string(host_string):
    """
    normalize() returns a tuple; this returns another valid host string.
    """
    return join_host_strings(*normalize(host_string))


def connect(user, host, port, cache, seek_gateway=True):
    """
    Create and return a new SSHClient instance connected to given host.

    :param user: Username to connect as.

    :param host: Network hostname.

    :param port: SSH daemon port.

    :param cache:
        A ``HostConnectionCache`` instance used to cache/store gateway hosts
        when gatewaying is enabled.

    :param seek_gateway:
        Whether to try setting up a gateway socket for this connection. Used so
        the actual gateway connection can prevent recursion.
    """
    from state import env, output

    #
    # Initialization
    #

    # Init client
    client = ssh.SSHClient()

    # Load system hosts file (e.g. /etc/ssh/ssh_known_hosts)
    known_hosts = env.get('system_known_hosts')
    if known_hosts:
        client.load_system_host_keys(known_hosts)

    # Load known host keys (e.g. ~/.ssh/known_hosts) unless user says not to.
    if not env.disable_known_hosts:
        client.load_system_host_keys()
    # Unless user specified not to, accept/add new, unknown host keys
    if not env.reject_unknown_hosts:
        client.set_missing_host_key_policy(ssh.AutoAddPolicy())

    #
    # Connection attempt loop
    #

    # Initialize loop variables
    connected = False
    password = get_password(user, host, port)
    tries = 0
    sock = None

    # Loop until successful connect (keep prompting for new password)
    while not connected:
        # Attempt connection
        try:
            tries += 1

            # (Re)connect gateway socket, if needed.
            # Nuke cached client object if not on initial try.
            if seek_gateway:
                sock = get_gateway(host, port, cache, replace=tries > 0)

            # Ready to connect
            client.connect(
                hostname=host,
                port=int(port),
                username=user,
                password=password,
                pkey=key_from_env(password),
                key_filename=key_filenames(),
                timeout=env.timeout,
                allow_agent=not env.no_agent,
                look_for_keys=not env.no_keys,
                sock=sock
            )
            connected = True

            # set a keepalive if desired
            if env.keepalive:
                client.get_transport().set_keepalive(env.keepalive)

            return client
        # BadHostKeyException corresponds to key mismatch, i.e. what on the
        # command line results in the big banner error about man-in-the-middle
        # attacks.
        except ssh.BadHostKeyException, e:
            raise NetworkError("Host key for %s did not match pre-existing key! Server's key was changed recently, or possible man-in-the-middle attack." % host, e)
        # Prompt for new password to try on auth failure
        except (
            ssh.AuthenticationException,
            ssh.PasswordRequiredException,
            ssh.SSHException
        ), e:
            msg = str(e)
            # If we get SSHExceptionError and the exception message indicates
            # SSH protocol banner read failures, assume it's caused by the
            # server load and try again.
            if e.__class__ is ssh.SSHException \
                and msg == 'Error reading SSH protocol banner':
                if _tried_enough(tries):
                    raise NetworkError(msg, e)
                continue

            # For whatever reason, empty password + no ssh key or agent
            # results in an SSHException instead of an
            # AuthenticationException. Since it's difficult to do
            # otherwise, we must assume empty password + SSHException ==
            # auth exception.
            #
            # Conversely: if we get SSHException and there
            # *was* a password -- it is probably something non auth
            # related, and should be sent upwards. (This is not true if the
            # exception message does indicate key parse problems.)
            #
            # This also holds true for rejected/unknown host keys: we have to
            # guess based on other heuristics.
            if e.__class__ is ssh.SSHException \
                and (password or msg.startswith('Unknown server')) \
                and not is_key_load_error(e):
                raise NetworkError(msg, e)

            # Otherwise, assume an auth exception, and prompt for new/better
            # password.

            # Paramiko doesn't handle prompting for locked private
            # keys (i.e.  keys with a passphrase and not loaded into an agent)
            # so we have to detect this and tweak our prompt slightly.
            # (Otherwise, however, the logic flow is the same, because
            # ssh's connect() method overrides the password argument to be
            # either the login password OR the private key passphrase. Meh.)
            #
            # NOTE: This will come up if you normally use a
            # passphrase-protected private key with ssh-agent, and enter an
            # incorrect remote username, because ssh.connect:
            # * Tries the agent first, which will fail as you gave the wrong
            # username, so obviously any loaded keys aren't gonna work for a
            # nonexistent remote account;
            # * Then tries the on-disk key file, which is passphrased;
            # * Realizes there's no password to try unlocking that key with,
            # because you didn't enter a password, because you're using
            # ssh-agent;
            # * In this condition (trying a key file, password is None)
            # ssh raises PasswordRequiredException.
            text = None
            if e.__class__ is ssh.PasswordRequiredException \
                or is_key_load_error(e):
                # NOTE: we can't easily say WHICH key's passphrase is needed,
                # because ssh doesn't provide us with that info, and
                # env.key_filename may be a list of keys, so we can't know
                # which one raised the exception. Best not to try.
                prompt = "[%s] Passphrase for private key"
                text = prompt % env.host_string
            password = prompt_for_password(text)
            # Update env.password, env.passwords if empty
            set_password(user, host, port, password)
        # Ctrl-D / Ctrl-C for exit
        except (EOFError, TypeError):
            # Print a newline (in case user was sitting at prompt)
            print('')
            sys.exit(0)
        # Handle DNS error / name lookup failure
        except socket.gaierror, e:
            raise NetworkError('Name lookup failed for %s' % host, e)
        # Handle timeouts and retries, including generic errors
        # NOTE: In 2.6, socket.error subclasses IOError
        except socket.error, e:
            not_timeout = type(e) is not socket.timeout
            giving_up = _tried_enough(tries)
            # Baseline error msg for when debug is off
            msg = "Timed out trying to connect to %s" % host
            # Expanded for debug on
            err = msg + " (attempt %s of %s)" % (tries, env.connection_attempts)
            if giving_up:
                err += ", giving up"
            err += ")"
            # Debuggin'
            if output.debug:
                sys.stderr.write(err + '\n')
            # Having said our piece, try again
            if not giving_up:
                # Sleep if it wasn't a timeout, so we still get timeout-like
                # behavior
                if not_timeout:
                    time.sleep(env.timeout)
                continue
            # Override eror msg if we were retrying other errors
            if not_timeout:
                msg = "Low level socket error connecting to host %s on port %s: %s" % (
                    host, port, e[1]
                )
            # Here, all attempts failed. Tweak error msg to show # tries.
            # TODO: find good humanization module, jeez
            s = "s" if env.connection_attempts > 1 else ""
            msg += " (tried %s time%s)" % (env.connection_attempts, s)
            raise NetworkError(msg, e)
        # Ensure that if we terminated without connecting and we were given an
        # explicit socket, close it out.
        finally:
            if not connected and sock is not None:
                sock.close()


def _password_prompt(prompt, stream):
    # NOTE: Using encode-to-ascii to prevent (Windows, at least) getpass from
    # choking if given Unicode.
    return getpass.getpass(prompt.encode('ascii', 'ignore'), stream)

def prompt_for_password(prompt=None, no_colon=False, stream=None):
    """
    Prompts for and returns a new password if required; otherwise, returns
    None.

    A trailing colon is appended unless ``no_colon`` is True.

    If the user supplies an empty password, the user will be re-prompted until
    they enter a non-empty password.

    ``prompt_for_password`` autogenerates the user prompt based on the current
    host being connected to. To override this, specify a string value for
    ``prompt``.

    ``stream`` is the stream the prompt will be printed to; if not given,
    defaults to ``sys.stderr``.
    """
    from fabric.state import env
    handle_prompt_abort("a connection or sudo password")
    stream = stream or sys.stderr
    # Construct prompt
    default = "[%s] Login password for '%s'" % (env.host_string, env.user)
    password_prompt = prompt if (prompt is not None) else default
    if not no_colon:
        password_prompt += ": "
    # Get new password value
    new_password = _password_prompt(password_prompt, stream)
    # Otherwise, loop until user gives us a non-empty password (to prevent
    # returning the empty string, and to avoid unnecessary network overhead.)
    while not new_password:
        print("Sorry, you can't enter an empty password. Please try again.")
        new_password = _password_prompt(password_prompt, stream)
    return new_password


def needs_host(func):
    """
    Prompt user for value of ``env.host_string`` when ``env.host_string`` is
    empty.

    This decorator is basically a safety net for silly users who forgot to
    specify the host/host list in one way or another. It should be used to wrap
    operations which require a network connection.

    Due to how we execute commands per-host in ``main()``, it's not possible to
    specify multiple hosts at this point in time, so only a single host will be
    prompted for.

    Because this decorator sets ``env.host_string``, it will prompt once (and
    only once) per command. As ``main()`` clears ``env.host_string`` between
    commands, this decorator will also end up prompting the user once per
    command (in the case where multiple commands have no hosts set, of course.)
    """
    from fabric.state import env
    @wraps(func)
    def host_prompting_wrapper(*args, **kwargs):
        while not env.get('host_string', False):
            handle_prompt_abort("the target host connection string")
            host_string = raw_input("No hosts found. Please specify (single)"
                                    " host string for connection: ")
            env.update(to_dict(host_string))
        return func(*args, **kwargs)
    host_prompting_wrapper.undecorated = func
    return host_prompting_wrapper


def disconnect_all():
    """
    Disconnect from all currently connected servers.

    Used at the end of ``fab``'s main loop, and also intended for use by
    library users.
    """
    from fabric.state import connections, output
    # Explicitly disconnect from all servers
    for key in connections.keys():
        if output.status:
            # Here we can't use the py3k print(x, end=" ")
            # because 2.5 backwards compatibility
            sys.stdout.write("Disconnecting from %s... " % denormalize(key))
        connections[key].close()
        del connections[key]
        if output.status:
            sys.stdout.write("done.\n")

########NEW FILE########
__FILENAME__ = operations
"""

Functions to be used in fabfiles and other non-core code, such as run()/sudo().
"""

from __future__ import with_statement

import os
import os.path
import posixpath
import re
import subprocess
import sys
import time
from glob import glob
from contextlib import closing, contextmanager

from fabric.context_managers import (settings, char_buffered, hide,
    quiet as quiet_manager, warn_only as warn_only_manager)
from fabric.io import output_loop, input_loop
from fabric.network import needs_host, ssh, ssh_config
from fabric.sftp import SFTP
from fabric.state import env, connections, output, win32, default_channel
from fabric.thread_handling import ThreadHandler
from fabric.utils import (
    abort,
    error,
    handle_prompt_abort,
    indent,
    _pty_size,
    warn,
    apply_lcwd
)


def _shell_escape(string):
    """
    Escape double quotes, backticks and dollar signs in given ``string``.

    For example::

        >>> _shell_escape('abc$')
        'abc\\\\$'
        >>> _shell_escape('"')
        '\\\\"'
    """
    for char in ('"', '$', '`'):
        string = string.replace(char, '\%s' % char)
    return string


class _AttributeString(str):
    """
    Simple string subclass to allow arbitrary attribute access.
    """
    @property
    def stdout(self):
        return str(self)


class _AttributeList(list):
    """
    Like _AttributeString, but for lists.
    """
    pass


# Can't wait till Python versions supporting 'def func(*args, foo=bar)' become
# widespread :(
def require(*keys, **kwargs):
    """
    Check for given keys in the shared environment dict and abort if not found.

    Positional arguments should be strings signifying what env vars should be
    checked for. If any of the given arguments do not exist, Fabric will abort
    execution and print the names of the missing keys.

    The optional keyword argument ``used_for`` may be a string, which will be
    printed in the error output to inform users why this requirement is in
    place. ``used_for`` is printed as part of a string similar to::

        "Th(is|ese) variable(s) (are|is) used for %s"

    so format it appropriately.

    The optional keyword argument ``provided_by`` may be a list of functions or
    function names or a single function or function name which the user should
    be able to execute in order to set the key or keys; it will be included in
    the error output if requirements are not met.

    Note: it is assumed that the keyword arguments apply to all given keys as a
    group. If you feel the need to specify more than one ``used_for``, for
    example, you should break your logic into multiple calls to ``require()``.

    .. versionchanged:: 1.1
        Allow iterable ``provided_by`` values instead of just single values.
    """
    # If all keys exist and are non-empty, we're good, so keep going.
    missing_keys = filter(lambda x: x not in env or (x in env and
        isinstance(env[x], (dict, list, tuple, set)) and not env[x]), keys)
    if not missing_keys:
        return
    # Pluralization
    if len(missing_keys) > 1:
        variable = "variables were"
        used = "These variables are"
    else:
        variable = "variable was"
        used = "This variable is"
    # Regardless of kwargs, print what was missing. (Be graceful if used outside
    # of a command.)
    if 'command' in env:
        prefix = "The command '%s' failed because the " % env.command
    else:
        prefix = "The "
    msg = "%sfollowing required environment %s not defined:\n%s" % (
        prefix, variable, indent(missing_keys)
    )
    # Print used_for if given
    if 'used_for' in kwargs:
        msg += "\n\n%s used for %s" % (used, kwargs['used_for'])
    # And print provided_by if given
    if 'provided_by' in kwargs:
        funcs = kwargs['provided_by']
        # non-iterable is given, treat it as a list of this single item
        if not hasattr(funcs, '__iter__'):
            funcs = [funcs]
        if len(funcs) > 1:
            command = "one of the following commands"
        else:
            command = "the following command"
        to_s = lambda obj: getattr(obj, '__name__', str(obj))
        provided_by = [to_s(obj) for obj in funcs]
        msg += "\n\nTry running %s prior to this one, to fix the problem:\n%s"\
            % (command, indent(provided_by))
    abort(msg)


def prompt(text, key=None, default='', validate=None):
    """
    Prompt user with ``text`` and return the input (like ``raw_input``).

    A single space character will be appended for convenience, but nothing
    else. Thus, you may want to end your prompt text with a question mark or a
    colon, e.g. ``prompt("What hostname?")``.

    If ``key`` is given, the user's input will be stored as ``env.<key>`` in
    addition to being returned by `prompt`. If the key already existed in
    ``env``, its value will be overwritten and a warning printed to the user.

    If ``default`` is given, it is displayed in square brackets and used if the
    user enters nothing (i.e. presses Enter without entering any text).
    ``default`` defaults to the empty string. If non-empty, a space will be
    appended, so that a call such as ``prompt("What hostname?",
    default="foo")`` would result in a prompt of ``What hostname? [foo]`` (with
    a trailing space after the ``[foo]``.)

    The optional keyword argument ``validate`` may be a callable or a string:

    * If a callable, it is called with the user's input, and should return the
      value to be stored on success. On failure, it should raise an exception
      with an exception message, which will be printed to the user.
    * If a string, the value passed to ``validate`` is used as a regular
      expression. It is thus recommended to use raw strings in this case. Note
      that the regular expression, if it is not fully matching (bounded by
      ``^`` and ``$``) it will be made so. In other words, the input must fully
      match the regex.

    Either way, `prompt` will re-prompt until validation passes (or the user
    hits ``Ctrl-C``).

    .. note::
        `~fabric.operations.prompt` honors :ref:`env.abort_on_prompts
        <abort-on-prompts>` and will call `~fabric.utils.abort` instead of
        prompting if that flag is set to ``True``. If you want to block on user
        input regardless, try wrapping with
        `~fabric.context_managers.settings`.

    Examples::

        # Simplest form:
        environment = prompt('Please specify target environment: ')

        # With default, and storing as env.dish:
        prompt('Specify favorite dish: ', 'dish', default='spam & eggs')

        # With validation, i.e. requiring integer input:
        prompt('Please specify process nice level: ', key='nice', validate=int)

        # With validation against a regular expression:
        release = prompt('Please supply a release name',
                validate=r'^\w+-\d+(\.\d+)?$')

        # Prompt regardless of the global abort-on-prompts setting:
        with settings(abort_on_prompts=False):
            prompt('I seriously need an answer on this! ')

    """
    handle_prompt_abort("a user-specified prompt() call")
    # Store previous env value for later display, if necessary
    if key:
        previous_value = env.get(key)
    # Set up default display
    default_str = ""
    if default != '':
        default_str = " [%s] " % str(default).strip()
    else:
        default_str = " "
    # Construct full prompt string
    prompt_str = text.strip() + default_str
    # Loop until we pass validation
    value = None
    while value is None:
        # Get input
        value = raw_input(prompt_str) or default
        # Handle validation
        if validate:
            # Callable
            if callable(validate):
                # Callable validate() must raise an exception if validation
                # fails.
                try:
                    value = validate(value)
                except Exception, e:
                    # Reset value so we stay in the loop
                    value = None
                    print("Validation failed for the following reason:")
                    print(indent(e.message) + "\n")
            # String / regex must match and will be empty if validation fails.
            else:
                # Need to transform regex into full-matching one if it's not.
                if not validate.startswith('^'):
                    validate = r'^' + validate
                if not validate.endswith('$'):
                    validate += r'$'
                result = re.findall(validate, value)
                if not result:
                    print("Regular expression validation failed: '%s' does not match '%s'\n" % (value, validate))
                    # Reset value so we stay in the loop
                    value = None
    # At this point, value must be valid, so update env if necessary
    if key:
        env[key] = value
    # Print warning if we overwrote some other value
    if key and previous_value is not None and previous_value != value:
        warn("overwrote previous env variable '%s'; used to be '%s', is now '%s'." % (
            key, previous_value, value
        ))
    # And return the value, too, just in case someone finds that useful.
    return value


@needs_host
def put(local_path=None, remote_path=None, use_sudo=False,
    mirror_local_mode=False, mode=None, use_glob=True, temp_dir=""):
    """
    Upload one or more files to a remote host.

    `~fabric.operations.put` returns an iterable containing the absolute file
    paths of all remote files uploaded. This iterable also exhibits a
    ``.failed`` attribute containing any local file paths which failed to
    upload (and may thus be used as a boolean test.) You may also check
    ``.succeeded`` which is equivalent to ``not .failed``.

    ``local_path`` may be a relative or absolute local file or directory path,
    and may contain shell-style wildcards, as understood by the Python ``glob``
    module (give ``use_glob=False`` to disable this behavior).  Tilde expansion
    (as implemented by ``os.path.expanduser``) is also performed.

    ``local_path`` may alternately be a file-like object, such as the result of
    ``open('path')`` or a ``StringIO`` instance.

    .. note::
        In this case, `~fabric.operations.put` will attempt to read the entire
        contents of the file-like object by rewinding it using ``seek`` (and
        will use ``tell`` afterwards to preserve the previous file position).

    ``remote_path`` may also be a relative or absolute location, but applied to
    the remote host. Relative paths are relative to the remote user's home
    directory, but tilde expansion (e.g. ``~/.ssh/``) will also be performed if
    necessary.

    An empty string, in either path argument, will be replaced by the
    appropriate end's current working directory.

    While the SFTP protocol (which `put` uses) has no direct ability to upload
    files to locations not owned by the connecting user, you may specify
    ``use_sudo=True`` to work around this. When set, this setting causes `put`
    to upload the local files to a temporary location on the remote end
    (defaults to remote user's ``$HOME``; this may be overridden via
    ``temp_dir``), and then use `sudo` to move them to ``remote_path``.

    In some use cases, it is desirable to force a newly uploaded file to match
    the mode of its local counterpart (such as when uploading executable
    scripts). To do this, specify ``mirror_local_mode=True``.

    Alternately, you may use the ``mode`` kwarg to specify an exact mode, in
    the same vein as ``os.chmod`` or the Unix ``chmod`` command.

    `~fabric.operations.put` will honor `~fabric.context_managers.cd`, so
    relative values in ``remote_path`` will be prepended by the current remote
    working directory, if applicable. Thus, for example, the below snippet
    would attempt to upload to ``/tmp/files/test.txt`` instead of
    ``~/files/test.txt``::

        with cd('/tmp'):
            put('/path/to/local/test.txt', 'files')

    Use of `~fabric.context_managers.lcd` will affect ``local_path`` in the
    same manner.

    Examples::

        put('bin/project.zip', '/tmp/project.zip')
        put('*.py', 'cgi-bin/')
        put('index.html', 'index.html', mode=0755)

    .. note::
        If a file-like object such as StringIO has a ``name`` attribute, that
        will be used in Fabric's printed output instead of the default
        ``<file obj>``
    .. versionchanged:: 1.0
        Now honors the remote working directory as manipulated by
        `~fabric.context_managers.cd`, and the local working directory as
        manipulated by `~fabric.context_managers.lcd`.
    .. versionchanged:: 1.0
        Now allows file-like objects in the ``local_path`` argument.
    .. versionchanged:: 1.0
        Directories may be specified in the ``local_path`` argument and will
        trigger recursive uploads.
    .. versionchanged:: 1.0
        Return value is now an iterable of uploaded remote file paths which
        also exhibits the ``.failed`` and ``.succeeded`` attributes.
    .. versionchanged:: 1.5
        Allow a ``name`` attribute on file-like objects for log output
    .. versionchanged:: 1.7
        Added ``use_glob`` option to allow disabling of globbing.
    """
    # Handle empty local path
    local_path = local_path or os.getcwd()

    # Test whether local_path is a path or a file-like object
    local_is_path = not (hasattr(local_path, 'read') \
        and callable(local_path.read))

    ftp = SFTP(env.host_string)

    with closing(ftp) as ftp:
        home = ftp.normalize('.')

        # Empty remote path implies cwd
        remote_path = remote_path or home

        # Expand tildes
        if remote_path.startswith('~'):
            remote_path = remote_path.replace('~', home, 1)

        # Honor cd() (assumes Unix style file paths on remote end)
        if not os.path.isabs(remote_path) and env.get('cwd'):
            remote_path = env.cwd.rstrip('/') + '/' + remote_path

        if local_is_path:
            # Apply lcwd, expand tildes, etc
            local_path = os.path.expanduser(local_path)
            local_path = apply_lcwd(local_path, env)
            if use_glob:
                # Glob local path
                names = glob(local_path)
            else:
                # Check if file exists first so ValueError gets raised
                if os.path.exists(local_path):
                    names = [local_path]
                else:
                    names = []
        else:
            names = [local_path]

        # Make sure local arg exists
        if local_is_path and not names:
            err = "'%s' is not a valid local path or glob." % local_path
            raise ValueError(err)

        # Sanity check and wierd cases
        if ftp.exists(remote_path):
            if local_is_path and len(names) != 1 and not ftp.isdir(remote_path):
                raise ValueError("'%s' is not a directory" % remote_path)

        # Iterate over all given local files
        remote_paths = []
        failed_local_paths = []
        for lpath in names:
            try:
                if local_is_path and os.path.isdir(lpath):
                    p = ftp.put_dir(lpath, remote_path, use_sudo,
                        mirror_local_mode, mode, temp_dir)
                    remote_paths.extend(p)
                else:
                    p = ftp.put(lpath, remote_path, use_sudo, mirror_local_mode,
                        mode, local_is_path, temp_dir)
                    remote_paths.append(p)
            except Exception, e:
                msg = "put() encountered an exception while uploading '%s'"
                failure = lpath if local_is_path else "<StringIO>"
                failed_local_paths.append(failure)
                error(message=msg % lpath, exception=e)

        ret = _AttributeList(remote_paths)
        ret.failed = failed_local_paths
        ret.succeeded = not ret.failed
        return ret


@needs_host
def get(remote_path, local_path=None):
    """
    Download one or more files from a remote host.

    `~fabric.operations.get` returns an iterable containing the absolute paths
    to all local files downloaded, which will be empty if ``local_path`` was a
    StringIO object (see below for more on using StringIO). This object will
    also exhibit a ``.failed`` attribute containing any remote file paths which
    failed to download, and a ``.succeeded`` attribute equivalent to ``not
    .failed``.

    ``remote_path`` is the remote file or directory path to download, which may
    contain shell glob syntax, e.g. ``"/var/log/apache2/*.log"``, and will have
    tildes replaced by the remote home directory. Relative paths will be
    considered relative to the remote user's home directory, or the current
    remote working directory as manipulated by `~fabric.context_managers.cd`.
    If the remote path points to a directory, that directory will be downloaded
    recursively.

    ``local_path`` is the local file path where the downloaded file or files
    will be stored. If relative, it will honor the local current working
    directory as manipulated by `~fabric.context_managers.lcd`. It may be
    interpolated, using standard Python dict-based interpolation, with the
    following variables:

    * ``host``: The value of ``env.host_string``, eg ``myhostname`` or
      ``user@myhostname-222`` (the colon between hostname and port is turned
      into a dash to maximize filesystem compatibility)
    * ``dirname``: The directory part of the remote file path, e.g. the
      ``src/projectname`` in ``src/projectname/utils.py``.
    * ``basename``: The filename part of the remote file path, e.g. the
      ``utils.py`` in ``src/projectname/utils.py``
    * ``path``: The full remote path, e.g. ``src/projectname/utils.py``.

    .. note::
        When ``remote_path`` is an absolute directory path, only the inner
        directories will be recreated locally and passed into the above
        variables. So for example, ``get('/var/log', '%(path)s')`` would start
        writing out files like ``apache2/access.log``,
        ``postgresql/8.4/postgresql.log``, etc, in the local working directory.
        It would **not** write out e.g.  ``var/log/apache2/access.log``.

        Additionally, when downloading a single file, ``%(dirname)s`` and
        ``%(path)s`` do not make as much sense and will be empty and equivalent
        to ``%(basename)s``, respectively. Thus a call like
        ``get('/var/log/apache2/access.log', '%(path)s')`` will save a local
        file named ``access.log``, not ``var/log/apache2/access.log``.

        This behavior is intended to be consistent with the command-line
        ``scp`` program.

    If left blank, ``local_path`` defaults to ``"%(host)s/%(path)s"`` in order
    to be safe for multi-host invocations.

    .. warning::
        If your ``local_path`` argument does not contain ``%(host)s`` and your
        `~fabric.operations.get` call runs against multiple hosts, your local
        files will be overwritten on each successive run!

    If ``local_path`` does not make use of the above variables (i.e. if it is a
    simple, explicit file path) it will act similar to ``scp`` or ``cp``,
    overwriting pre-existing files if necessary, downloading into a directory
    if given (e.g. ``get('/path/to/remote_file.txt', 'local_directory')`` will
    create ``local_directory/remote_file.txt``) and so forth.

    ``local_path`` may alternately be a file-like object, such as the result of
    ``open('path', 'w')`` or a ``StringIO`` instance.

    .. note::
        Attempting to `get` a directory into a file-like object is not valid
        and will result in an error.

    .. note::
        This function will use ``seek`` and ``tell`` to overwrite the entire
        contents of the file-like object, in order to be consistent with the
        behavior of `~fabric.operations.put` (which also considers the entire
        file). However, unlike `~fabric.operations.put`, the file pointer will
        not be restored to its previous location, as that doesn't make as much
        sense here and/or may not even be possible.

    .. note::
        If a file-like object such as StringIO has a ``name`` attribute, that
        will be used in Fabric's printed output instead of the default
        ``<file obj>``

    .. versionchanged:: 1.0
        Now honors the remote working directory as manipulated by
        `~fabric.context_managers.cd`, and the local working directory as
        manipulated by `~fabric.context_managers.lcd`.
    .. versionchanged:: 1.0
        Now allows file-like objects in the ``local_path`` argument.
    .. versionchanged:: 1.0
        ``local_path`` may now contain interpolated path- and host-related
        variables.
    .. versionchanged:: 1.0
        Directories may be specified in the ``remote_path`` argument and will
        trigger recursive downloads.
    .. versionchanged:: 1.0
        Return value is now an iterable of downloaded local file paths, which
        also exhibits the ``.failed`` and ``.succeeded`` attributes.
    .. versionchanged:: 1.5
        Allow a ``name`` attribute on file-like objects for log output
    """
    # Handle empty local path / default kwarg value
    local_path = local_path or "%(host)s/%(path)s"

    # Test whether local_path is a path or a file-like object
    local_is_path = not (hasattr(local_path, 'write') \
        and callable(local_path.write))

    # Honor lcd() where it makes sense
    if local_is_path:
        local_path = apply_lcwd(local_path, env)

    ftp = SFTP(env.host_string)

    with closing(ftp) as ftp:
        home = ftp.normalize('.')
        # Expand home directory markers (tildes, etc)
        if remote_path.startswith('~'):
            remote_path = remote_path.replace('~', home, 1)
        if local_is_path:
            local_path = os.path.expanduser(local_path)

        # Honor cd() (assumes Unix style file paths on remote end)
        if not os.path.isabs(remote_path):
            # Honor cwd if it's set (usually by with cd():)
            if env.get('cwd'):
                remote_path_escaped = env.cwd.rstrip('/')
                remote_path_escaped = remote_path_escaped.replace('\\ ', ' ')
                remote_path = remote_path_escaped + '/' + remote_path
            # Otherwise, be relative to remote home directory (SFTP server's
            # '.')
            else:
                remote_path = posixpath.join(home, remote_path)

        # Track final local destination files so we can return a list
        local_files = []
        failed_remote_files = []

        try:
            # Glob remote path
            names = ftp.glob(remote_path)

            # Handle invalid local-file-object situations
            if not local_is_path:
                if len(names) > 1 or ftp.isdir(names[0]):
                    error("[%s] %s is a glob or directory, but local_path is a file object!" % (env.host_string, remote_path))

            for remote_path in names:
                if ftp.isdir(remote_path):
                    result = ftp.get_dir(remote_path, local_path)
                    local_files.extend(result)
                else:
                    # Perform actual get. If getting to real local file path,
                    # add result (will be true final path value) to
                    # local_files. File-like objects are omitted.
                    result = ftp.get(remote_path, local_path, local_is_path,
                        os.path.basename(remote_path))
                    if local_is_path:
                        local_files.append(result)

        except Exception, e:
            failed_remote_files.append(remote_path)
            msg = "get() encountered an exception while downloading '%s'"
            error(message=msg % remote_path, exception=e)

        ret = _AttributeList(local_files if local_is_path else [])
        ret.failed = failed_remote_files
        ret.succeeded = not ret.failed
        return ret


def _sudo_prefix_argument(argument, value):
    if value is None:
        return ""
    if str(value).isdigit():
        value = "#%s" % value
    return ' %s "%s"' % (argument, value)


def _sudo_prefix(user, group=None):
    """
    Return ``env.sudo_prefix`` with ``user``/``group`` inserted if necessary.
    """
    # Insert env.sudo_prompt into env.sudo_prefix
    prefix = env.sudo_prefix % env
    if user is not None or group is not None:
        return "%s%s%s " % (prefix,
                            _sudo_prefix_argument('-u', user),
                            _sudo_prefix_argument('-g', group))
    return prefix


def _shell_wrap(command, shell_escape, shell=True, sudo_prefix=None):
    """
    Conditionally wrap given command in env.shell (while honoring sudo.)
    """
    # Honor env.shell, while allowing the 'shell' kwarg to override it (at
    # least in terms of turning it off.)
    if shell and not env.use_shell:
        shell = False
    # Sudo plus space, or empty string
    if sudo_prefix is None:
        sudo_prefix = ""
    else:
        sudo_prefix += " "
    # If we're shell wrapping, prefix shell and space. Next, escape the command
    # if requested, and then quote it. Otherwise, empty string.
    if shell:
        shell = env.shell + " "
        if shell_escape:
            command = _shell_escape(command)
        command = '"%s"' % command
    else:
        shell = ""
    # Resulting string should now have correct formatting
    return sudo_prefix + shell + command


def _prefix_commands(command, which):
    """
    Prefixes ``command`` with all prefixes found in ``env.command_prefixes``.

    ``env.command_prefixes`` is a list of strings which is modified by the
    `~fabric.context_managers.prefix` context manager.

    This function also handles a special-case prefix, ``cwd``, used by
    `~fabric.context_managers.cd`. The ``which`` kwarg should be a string,
    ``"local"`` or ``"remote"``, which will determine whether ``cwd`` or
    ``lcwd`` is used.
    """
    # Local prefix list (to hold env.command_prefixes + any special cases)
    prefixes = list(env.command_prefixes)
    # Handle current working directory, which gets its own special case due to
    # being a path string that gets grown/shrunk, instead of just a single
    # string or lack thereof.
    # Also place it at the front of the list, in case user is expecting another
    # prefixed command to be "in" the current working directory.
    cwd = env.cwd if which == 'remote' else env.lcwd
    if cwd:
        prefixes.insert(0, 'cd %s' % cwd)
    glue = " && "
    prefix = (glue.join(prefixes) + glue) if prefixes else ""
    return prefix + command


def _prefix_env_vars(command, local=False):
    """
    Prefixes ``command`` with any shell environment vars, e.g. ``PATH=foo ``.

    Currently, this only applies the PATH updating implemented in
    `~fabric.context_managers.path` and environment variables from
    `~fabric.context_managers.shell_env`.

    Will switch to using Windows style 'SET' commands when invoked by
    ``local()`` and on a Windows localhost.
    """
    env_vars = {}

    # path(): local shell env var update, appending/prepending/replacing $PATH
    path = env.path
    if path:
        if env.path_behavior == 'append':
            path = '$PATH:\"%s\"' % path
        elif env.path_behavior == 'prepend':
            path = '\"%s\":$PATH' % path
        elif env.path_behavior == 'replace':
            path = '\"%s\"' % path

        env_vars['PATH'] = path

    # shell_env()
    env_vars.update(env.shell_env)

    if env_vars:
        set_cmd, exp_cmd = '', ''
        if win32 and local:
            set_cmd = 'SET '
        else:
            exp_cmd = 'export '

        exports = ' '.join(
            '%s%s="%s"' % (set_cmd, k, v if k == 'PATH' else _shell_escape(v))
            for k, v in env_vars.iteritems()
        )
        shell_env_str = '%s%s && ' % (exp_cmd, exports)
    else:
        shell_env_str = ''

    return shell_env_str + command


def _execute(channel, command, pty=True, combine_stderr=None,
    invoke_shell=False, stdout=None, stderr=None, timeout=None):
    """
    Execute ``command`` over ``channel``.

    ``pty`` controls whether a pseudo-terminal is created.

    ``combine_stderr`` controls whether we call ``channel.set_combine_stderr``.
    By default, the global setting for this behavior (:ref:`env.combine_stderr
    <combine-stderr>`) is consulted, but you may specify ``True`` or ``False``
    here to override it.

    ``invoke_shell`` controls whether we use ``exec_command`` or
    ``invoke_shell`` (plus a handful of other things, such as always forcing a
    pty.)

    Returns a three-tuple of (``stdout``, ``stderr``, ``status``), where
    ``stdout``/``stderr`` are captured output strings and ``status`` is the
    program's return code, if applicable.
    """
    # stdout/stderr redirection
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    # Timeout setting control
    timeout = env.command_timeout if (timeout is None) else timeout

    # What to do with CTRl-C?
    remote_interrupt = env.remote_interrupt

    with char_buffered(sys.stdin):
        # Combine stdout and stderr to get around oddball mixing issues
        if combine_stderr is None:
            combine_stderr = env.combine_stderr
        channel.set_combine_stderr(combine_stderr)

        # Assume pty use, and allow overriding of this either via kwarg or env
        # var.  (invoke_shell always wants a pty no matter what.)
        using_pty = True
        if not invoke_shell and (not pty or not env.always_use_pty):
            using_pty = False
        # Request pty with size params (default to 80x24, obtain real
        # parameters if on POSIX platform)
        if using_pty:
            rows, cols = _pty_size()
            channel.get_pty(width=cols, height=rows)

        # Use SSH agent forwarding from 'ssh' if enabled by user
        config_agent = ssh_config().get('forwardagent', 'no').lower() == 'yes'
        forward = None
        if env.forward_agent or config_agent:
            forward = ssh.agent.AgentRequestHandler(channel)

        # Kick off remote command
        if invoke_shell:
            channel.invoke_shell()
            if command:
                channel.sendall(command + "\n")
        else:
            channel.exec_command(command=command)

        # Init stdout, stderr capturing. Must use lists instead of strings as
        # strings are immutable and we're using these as pass-by-reference
        stdout_buf, stderr_buf = [], []
        if invoke_shell:
            stdout_buf = stderr_buf = None

        workers = (
            ThreadHandler('out', output_loop, channel, "recv",
                capture=stdout_buf, stream=stdout, timeout=timeout),
            ThreadHandler('err', output_loop, channel, "recv_stderr",
                capture=stderr_buf, stream=stderr, timeout=timeout),
            ThreadHandler('in', input_loop, channel, using_pty)
        )

        if remote_interrupt is None:
            remote_interrupt = invoke_shell
        if remote_interrupt and not using_pty:
            remote_interrupt = False

        while True:
            if channel.exit_status_ready():
                break
            else:
                # Check for thread exceptions here so we can raise ASAP
                # (without chance of getting blocked by, or hidden by an
                # exception within, recv_exit_status())
                for worker in workers:
                    worker.raise_if_needed()
            try:
                time.sleep(ssh.io_sleep)
            except KeyboardInterrupt:
                if not remote_interrupt:
                    raise
                channel.send('\x03')

        # Obtain exit code of remote program now that we're done.
        status = channel.recv_exit_status()

        # Wait for threads to exit so we aren't left with stale threads
        for worker in workers:
            worker.thread.join()
            worker.raise_if_needed()

        # Close channel
        channel.close()
        # Close any agent forward proxies
        if forward is not None:
            forward.close()

        # Update stdout/stderr with captured values if applicable
        if not invoke_shell:
            stdout_buf = ''.join(stdout_buf).strip()
            stderr_buf = ''.join(stderr_buf).strip()

        # Tie off "loose" output by printing a newline. Helps to ensure any
        # following print()s aren't on the same line as a trailing line prefix
        # or similar. However, don't add an extra newline if we've already
        # ended up with one, as that adds a entire blank line instead.
        if output.running \
            and (output.stdout and stdout_buf and not stdout_buf.endswith("\n")) \
            or (output.stderr and stderr_buf and not stderr_buf.endswith("\n")):
            print("")

        return stdout_buf, stderr_buf, status


@needs_host
def open_shell(command=None):
    """
    Invoke a fully interactive shell on the remote end.

    If ``command`` is given, it will be sent down the pipe before handing
    control over to the invoking user.

    This function is most useful for when you need to interact with a heavily
    shell-based command or series of commands, such as when debugging or when
    fully interactive recovery is required upon remote program failure.

    It should be considered an easy way to work an interactive shell session
    into the middle of a Fabric script and is *not* a drop-in replacement for
    `~fabric.operations.run`, which is also capable of interacting with the
    remote end (albeit only while its given command is executing) and has much
    stronger programmatic abilities such as error handling and stdout/stderr
    capture.

    Specifically, `~fabric.operations.open_shell` provides a better interactive
    experience than `~fabric.operations.run`, but use of a full remote shell
    prevents Fabric from determining whether programs run within the shell have
    failed, and pollutes the stdout/stderr stream with shell output such as
    login banners, prompts and echoed stdin.

    Thus, this function does not have a return value and will not trigger
    Fabric's failure handling if any remote programs result in errors.

    .. versionadded:: 1.0
    """
    _execute(channel=default_channel(), command=command, pty=True,
        combine_stderr=True, invoke_shell=True)


@contextmanager
def _noop():
    yield


def _run_command(command, shell=True, pty=True, combine_stderr=True,
    sudo=False, user=None, quiet=False, warn_only=False, stdout=None,
    stderr=None, group=None, timeout=None, shell_escape=None):
    """
    Underpinnings of `run` and `sudo`. See their docstrings for more info.
    """
    manager = _noop
    if warn_only:
        manager = warn_only_manager
    # Quiet's behavior is a superset of warn_only's, so it wins.
    if quiet:
        manager = quiet_manager
    with manager():
        # Set up new var so original argument can be displayed verbatim later.
        given_command = command

        # Check if shell_escape has been overridden in env
        if shell_escape is None:
            shell_escape = env.get('shell_escape', True)

        # Handle context manager modifications, and shell wrapping
        wrapped_command = _shell_wrap(
            _prefix_commands(_prefix_env_vars(command), 'remote'),
            shell_escape,
            shell,
            _sudo_prefix(user, group) if sudo else None
        )
        # Execute info line
        which = 'sudo' if sudo else 'run'
        if output.debug:
            print("[%s] %s: %s" % (env.host_string, which, wrapped_command))
        elif output.running:
            print("[%s] %s: %s" % (env.host_string, which, given_command))

        # Actual execution, stdin/stdout/stderr handling, and termination
        result_stdout, result_stderr, status = _execute(
            channel=default_channel(), command=wrapped_command, pty=pty,
            combine_stderr=combine_stderr, invoke_shell=False, stdout=stdout,
            stderr=stderr, timeout=timeout)

        # Assemble output string
        out = _AttributeString(result_stdout)
        err = _AttributeString(result_stderr)

        # Error handling
        out.failed = False
        out.command = given_command
        out.real_command = wrapped_command
        if status not in env.ok_ret_codes:
            out.failed = True
            msg = "%s() received nonzero return code %s while executing" % (
                which, status
            )
            if env.warn_only:
                msg += " '%s'!" % given_command
            else:
                msg += "!\n\nRequested: %s\nExecuted: %s" % (
                    given_command, wrapped_command
                )
            error(message=msg, stdout=out, stderr=err)

        # Attach return code to output string so users who have set things to
        # warn only, can inspect the error code.
        out.return_code = status

        # Convenience mirror of .failed
        out.succeeded = not out.failed

        # Attach stderr for anyone interested in that.
        out.stderr = err

        return out


@needs_host
def run(command, shell=True, pty=True, combine_stderr=None, quiet=False,
    warn_only=False, stdout=None, stderr=None, timeout=None, shell_escape=None):
    """
    Run a shell command on a remote host.

    If ``shell`` is True (the default), `run` will execute the given command
    string via a shell interpreter, the value of which may be controlled by
    setting ``env.shell`` (defaulting to something similar to ``/bin/bash -l -c
    "<command>"``.) Any double-quote (``"``) or dollar-sign (``$``) characters
    in ``command`` will be automatically escaped when ``shell`` is True.

    `run` will return the result of the remote program's stdout as a single
    (likely multiline) string. This string will exhibit ``failed`` and
    ``succeeded`` boolean attributes specifying whether the command failed or
    succeeded, and will also include the return code as the ``return_code``
    attribute. Furthermore, it includes a copy of the requested & actual
    command strings executed, as ``.command`` and ``.real_command``,
    respectively.

    Any text entered in your local terminal will be forwarded to the remote
    program as it runs, thus allowing you to interact with password or other
    prompts naturally. For more on how this works, see
    :doc:`/usage/interactivity`.

    You may pass ``pty=False`` to forego creation of a pseudo-terminal on the
    remote end in case the presence of one causes problems for the command in
    question. However, this will force Fabric itself to echo any  and all input
    you type while the command is running, including sensitive passwords. (With
    ``pty=True``, the remote pseudo-terminal will echo for you, and will
    intelligently handle password-style prompts.) See :ref:`pseudottys` for
    details.

    Similarly, if you need to programmatically examine the stderr stream of the
    remote program (exhibited as the ``stderr`` attribute on this function's
    return value), you may set ``combine_stderr=False``. Doing so has a high
    chance of causing garbled output to appear on your terminal (though the
    resulting strings returned by `~fabric.operations.run` will be properly
    separated). For more info, please read :ref:`combine_streams`.

    To ignore non-zero return codes, specify ``warn_only=True``. To both ignore
    non-zero return codes *and* force a command to run silently, specify
    ``quiet=True``.

    To override which local streams are used to display remote stdout and/or
    stderr, specify ``stdout`` or ``stderr``. (By default, the regular
    ``sys.stdout`` and ``sys.stderr`` Python stream objects are used.)

    For example, ``run("command", stderr=sys.stdout)`` would print the remote
    standard error to the local standard out, while preserving it as its own
    distinct attribute on the return value (as per above.) Alternately, you
    could even provide your own stream objects or loggers, e.g. ``myout =
    StringIO(); run("command", stdout=myout)``.

    If you want an exception raised when the remote program takes too long to
    run, specify ``timeout=N`` where ``N`` is an integer number of seconds,
    after which to time out. This will cause ``run`` to raise a
    `~fabric.exceptions.CommandTimeout` exception.

    If you want to disable Fabric's automatic attempts at escaping quotes,
    dollar signs etc., specify ``shell_escape=False``.

    Examples::

        run("ls /var/www/")
        run("ls /home/myuser", shell=False)
        output = run('ls /var/www/site1')
        run("take_a_long_time", timeout=5)

    .. versionadded:: 1.0
        The ``succeeded`` and ``stderr`` return value attributes, the
        ``combine_stderr`` kwarg, and interactive behavior.

    .. versionchanged:: 1.0
        The default value of ``pty`` is now ``True``.

    .. versionchanged:: 1.0.2
        The default value of ``combine_stderr`` is now ``None`` instead of
        ``True``. However, the default *behavior* is unchanged, as the global
        setting is still ``True``.

    .. versionadded:: 1.5
        The ``quiet``, ``warn_only``, ``stdout`` and ``stderr`` kwargs.

    .. versionadded:: 1.5
        The return value attributes ``.command`` and ``.real_command``.

    .. versionadded:: 1.6
        The ``timeout`` argument.

    .. versionadded:: 1.7
        The ``shell_escape`` argument.
    """
    return _run_command(command, shell, pty, combine_stderr, quiet=quiet,
        warn_only=warn_only, stdout=stdout, stderr=stderr, timeout=timeout,
        shell_escape=shell_escape)


@needs_host
def sudo(command, shell=True, pty=True, combine_stderr=None, user=None,
    quiet=False, warn_only=False, stdout=None, stderr=None, group=None,
    timeout=None, shell_escape=None):
    """
    Run a shell command on a remote host, with superuser privileges.

    `sudo` is identical in every way to `run`, except that it will always wrap
    the given ``command`` in a call to the ``sudo`` program to provide
    superuser privileges.

    `sudo` accepts additional ``user`` and ``group`` arguments, which are
    passed to ``sudo`` and allow you to run as some user and/or group other
    than root.  On most systems, the ``sudo`` program can take a string
    username/group or an integer userid/groupid (uid/gid); ``user`` and
    ``group`` may likewise be strings or integers.

    You may set :ref:`env.sudo_user <sudo_user>` at module level or via
    `~fabric.context_managers.settings` if you want multiple ``sudo`` calls to
    have the same ``user`` value. An explicit ``user`` argument will, of
    course, override this global setting.

    Examples::

        sudo("~/install_script.py")
        sudo("mkdir /var/www/new_docroot", user="www-data")
        sudo("ls /home/jdoe", user=1001)
        result = sudo("ls /tmp/")
        with settings(sudo_user='mysql'):
            sudo("whoami") # prints 'mysql'

    .. versionchanged:: 1.0
        See the changed and added notes for `~fabric.operations.run`.

    .. versionchanged:: 1.5
        Now honors :ref:`env.sudo_user <sudo_user>`.

    .. versionadded:: 1.5
        The ``quiet``, ``warn_only``, ``stdout`` and ``stderr`` kwargs.

    .. versionadded:: 1.5
        The return value attributes ``.command`` and ``.real_command``.

    .. versionadded:: 1.7
        The ``shell_escape`` argument.
    """
    return _run_command(
        command, shell, pty, combine_stderr, sudo=True,
        user=user if user else env.sudo_user,
        group=group, quiet=quiet, warn_only=warn_only, stdout=stdout,
        stderr=stderr, timeout=timeout, shell_escape=shell_escape,
    )


def local(command, capture=False, shell=None):
    """
    Run a command on the local system.

    `local` is simply a convenience wrapper around the use of the builtin
    Python ``subprocess`` module with ``shell=True`` activated. If you need to
    do anything special, consider using the ``subprocess`` module directly.

    ``shell`` is passed directly to `subprocess.Popen
    <http://docs.python.org/library/subprocess.html#subprocess.Popen>`_'s
    ``execute`` argument (which determines the local shell to use.)  As per the
    linked documentation, on Unix the default behavior is to use ``/bin/sh``,
    so this option is useful for setting that value to e.g.  ``/bin/bash``.

    `local` is not currently capable of simultaneously printing and
    capturing output, as `~fabric.operations.run`/`~fabric.operations.sudo`
    do. The ``capture`` kwarg allows you to switch between printing and
    capturing as necessary, and defaults to ``False``.

    When ``capture=False``, the local subprocess' stdout and stderr streams are
    hooked up directly to your terminal, though you may use the global
    :doc:`output controls </usage/output_controls>` ``output.stdout`` and
    ``output.stderr`` to hide one or both if desired. In this mode, the return
    value's stdout/stderr values are always empty.

    When ``capture=True``, you will not see any output from the subprocess in
    your terminal, but the return value will contain the captured
    stdout/stderr.

    In either case, as with `~fabric.operations.run` and
    `~fabric.operations.sudo`, this return value exhibits the ``return_code``,
    ``stderr``, ``failed``, ``succeeded``, ``command`` and ``real_command``
    attributes. See `run` for details.

    `~fabric.operations.local` will honor the `~fabric.context_managers.lcd`
    context manager, allowing you to control its current working directory
    independently of the remote end (which honors
    `~fabric.context_managers.cd`).

    .. versionchanged:: 1.0
        Added the ``succeeded`` and ``stderr`` attributes.
    .. versionchanged:: 1.0
        Now honors the `~fabric.context_managers.lcd` context manager.
    .. versionchanged:: 1.0
        Changed the default value of ``capture`` from ``True`` to ``False``.
    .. versionadded:: 1.9
        The return value attributes ``.command`` and ``.real_command``.
    """
    given_command = command
    # Apply cd(), path() etc
    with_env = _prefix_env_vars(command, local=True)
    wrapped_command = _prefix_commands(with_env, 'local')
    if output.debug:
        print("[localhost] local: %s" % (wrapped_command))
    elif output.running:
        print("[localhost] local: " + given_command)
    # Tie in to global output controls as best we can; our capture argument
    # takes precedence over the output settings.
    dev_null = None
    if capture:
        out_stream = subprocess.PIPE
        err_stream = subprocess.PIPE
    else:
        dev_null = open(os.devnull, 'w+')
        # Non-captured, hidden streams are discarded.
        out_stream = None if output.stdout else dev_null
        err_stream = None if output.stderr else dev_null
    try:
        cmd_arg = wrapped_command if win32 else [wrapped_command]
        if shell is not None:
            p = subprocess.Popen(cmd_arg, shell=True, stdout=out_stream,
                                 stderr=err_stream, executable=shell)
        else:
            p = subprocess.Popen(cmd_arg, shell=True, stdout=out_stream,
                                 stderr=err_stream)
        (stdout, stderr) = p.communicate()
    finally:
        if dev_null is not None:
            dev_null.close()
    # Handle error condition (deal with stdout being None, too)
    out = _AttributeString(stdout.strip() if stdout else "")
    err = _AttributeString(stderr.strip() if stderr else "")
    out.command = given_command
    out.real_command = wrapped_command
    out.failed = False
    out.return_code = p.returncode
    out.stderr = err
    if p.returncode not in env.ok_ret_codes:
        out.failed = True
        msg = "local() encountered an error (return code %s) while executing '%s'" % (p.returncode, command)
        error(message=msg, stdout=out, stderr=err)
    out.succeeded = not out.failed
    # If we were capturing, this will be a string; otherwise it will be None.
    return out


@needs_host
def reboot(wait=120, command='reboot'):
    """
    Reboot the remote system.

    Will temporarily tweak Fabric's reconnection settings (:ref:`timeout` and
    :ref:`connection-attempts`) to ensure that reconnection does not give up
    for at least ``wait`` seconds.

    .. note::
        As of Fabric 1.4, the ability to reconnect partway through a session no
        longer requires use of internal APIs.  While we are not officially
        deprecating this function, adding more features to it will not be a
        priority.

        Users who want greater control
        are encouraged to check out this function's (6 lines long, well
        commented) source code and write their own adaptation using different
        timeout/attempt values or additional logic.

    .. versionadded:: 0.9.2
    .. versionchanged:: 1.4
        Changed the ``wait`` kwarg to be optional, and refactored to leverage
        the new reconnection functionality; it may not actually have to wait
        for ``wait`` seconds before reconnecting.
    """
    # Shorter timeout for a more granular cycle than the default.
    timeout = 5
    # Use 'wait' as max total wait time
    attempts = int(round(float(wait) / float(timeout)))
    # Don't bleed settings, since this is supposed to be self-contained.
    # User adaptations will probably want to drop the "with settings()" and
    # just have globally set timeout/attempts values.
    with settings(
        hide('running'),
        timeout=timeout,
        connection_attempts=attempts
    ):
        sudo(command)
        # Try to make sure we don't slip in before pre-reboot lockdown
        time.sleep(5)
        # This is actually an internal-ish API call, but users can simply drop
        # it in real fabfile use -- the next run/sudo/put/get/etc call will
        # automatically trigger a reconnect.
        # We use it here to force the reconnect while this function is still in
        # control and has the above timeout settings enabled.
        connections.connect(env.host_string)
    # At this point we should be reconnected to the newly rebooted server.

########NEW FILE########
__FILENAME__ = sftp
from __future__ import with_statement

import hashlib
import os
import posixpath
import stat
import re
from fnmatch import filter as fnfilter

from fabric.state import output, connections, env
from fabric.utils import warn
from fabric.context_managers import settings


def _format_local(local_path, local_is_path):
    """Format a path for log output"""
    if local_is_path:
        return local_path
    else:
        # This allows users to set a name attr on their StringIO objects
        # just like an open file object would have
        return getattr(local_path, 'name', '<file obj>')


class SFTP(object):
    """
    SFTP helper class, which is also a facade for ssh.SFTPClient.
    """
    def __init__(self, host_string):
        self.ftp = connections[host_string].open_sftp()

    # Recall that __getattr__ is the "fallback" attribute getter, and is thus
    # pretty safe to use for facade-like behavior as we're doing here.
    def __getattr__(self, attr):
        return getattr(self.ftp, attr)

    def isdir(self, path):
        try:
            return stat.S_ISDIR(self.ftp.lstat(path).st_mode)
        except IOError:
            return False

    def islink(self, path):
        try:
            return stat.S_ISLNK(self.ftp.lstat(path).st_mode)
        except IOError:
            return False

    def exists(self, path):
        try:
            self.ftp.lstat(path).st_mode
        except IOError:
            return False
        return True

    def glob(self, path):
        from fabric.state import win32
        dirpart, pattern = os.path.split(path)
        rlist = self.ftp.listdir(dirpart)

        names = fnfilter([f for f in rlist if not f[0] == '.'], pattern)
        ret = [path]
        if len(names):
            s = '/'
            ret = [dirpart.rstrip(s) + s + name.lstrip(s) for name in names]
            if not win32:
                ret = [posixpath.join(dirpart, name) for name in names]
        return ret

    def walk(self, top, topdown=True, onerror=None, followlinks=False):
        from os.path import join

        # We may not have read permission for top, in which case we can't get a
        # list of the files the directory contains. os.path.walk always
        # suppressed the exception then, rather than blow up for a minor reason
        # when (say) a thousand readable directories are still left to visit.
        # That logic is copied here.
        try:
            # Note that listdir and error are globals in this module due to
            # earlier import-*.
            names = self.ftp.listdir(top)
        except Exception, err:
            if onerror is not None:
                onerror(err)
            return

        dirs, nondirs = [], []
        for name in names:
            if self.isdir(join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)

        if topdown:
            yield top, dirs, nondirs

        for name in dirs:
            path = join(top, name)
            if followlinks or not self.islink(path):
                for x in self.walk(path, topdown, onerror, followlinks):
                    yield x
        if not topdown:
            yield top, dirs, nondirs

    def mkdir(self, path, use_sudo):
        from fabric.api import sudo, hide
        if use_sudo:
            with hide('everything'):
                sudo('mkdir "%s"' % path)
        else:
            self.ftp.mkdir(path)

    def get(self, remote_path, local_path, local_is_path, rremote=None):
        # rremote => relative remote path, so get(/var/log) would result in
        # this function being called with
        # remote_path=/var/log/apache2/access.log and
        # rremote=apache2/access.log
        rremote = rremote if rremote is not None else remote_path
        # Handle format string interpolation (e.g. %(dirname)s)
        path_vars = {
            'host': env.host_string.replace(':', '-'),
            'basename': os.path.basename(rremote),
            'dirname': os.path.dirname(rremote),
            'path': rremote
        }
        if local_is_path:
            # Naive fix to issue #711
            escaped_path = re.sub(r'(%[^()]*\w)', r'%\1', local_path)
            local_path = os.path.abspath(escaped_path % path_vars )

            # Ensure we give ssh.SFTPCLient a file by prepending and/or
            # creating local directories as appropriate.
            dirpath, filepath = os.path.split(local_path)
            if dirpath and not os.path.exists(dirpath):
                os.makedirs(dirpath)
            if os.path.isdir(local_path):
                local_path = os.path.join(local_path, path_vars['basename'])
        if output.running:
            print("[%s] download: %s <- %s" % (
                env.host_string,
                _format_local(local_path, local_is_path),
                remote_path
            ))
        # Warn about overwrites, but keep going
        if local_is_path and os.path.exists(local_path):
            msg = "Local file %s already exists and is being overwritten."
            warn(msg % local_path)
        # File-like objects: reset to file seek 0 (to ensure full overwrite)
        # and then use Paramiko's getfo() directly
        getter = self.ftp.get
        if not local_is_path:
            local_path.seek(0)
            getter = self.ftp.getfo
        getter(remote_path, local_path)
        # Return local_path object for posterity. (If mutated, caller will want
        # to know.)
        return local_path

    def get_dir(self, remote_path, local_path):
        # Decide what needs to be stripped from remote paths so they're all
        # relative to the given remote_path
        if os.path.basename(remote_path):
            strip = os.path.dirname(remote_path)
        else:
            strip = os.path.dirname(os.path.dirname(remote_path))

        # Store all paths gotten so we can return them when done
        result = []
        # Use our facsimile of os.walk to find all files within remote_path
        for context, dirs, files in self.walk(remote_path):
            # Normalize current directory to be relative
            # E.g. remote_path of /var/log and current dir of /var/log/apache2
            # would be turned into just 'apache2'
            lcontext = rcontext = context.replace(strip, '', 1).lstrip('/')
            # Prepend local path to that to arrive at the local mirrored
            # version of this directory. So if local_path was 'mylogs', we'd
            # end up with 'mylogs/apache2'
            lcontext = os.path.join(local_path, lcontext)

            # Download any files in current directory
            for f in files:
                # Construct full and relative remote paths to this file
                rpath = posixpath.join(context, f)
                rremote = posixpath.join(rcontext, f)
                # If local_path isn't using a format string that expands to
                # include its remote path, we need to add it here.
                if "%(path)s" not in local_path \
                    and "%(dirname)s" not in local_path:
                    lpath = os.path.join(lcontext, f)
                # Otherwise, just passthrough local_path to self.get()
                else:
                    lpath = local_path
                # Now we can make a call to self.get() with specific file paths
                # on both ends.
                result.append(self.get(rpath, lpath, True, rremote))
        return result

    def put(self, local_path, remote_path, use_sudo, mirror_local_mode, mode,
        local_is_path, temp_dir):
        from fabric.api import sudo, hide
        pre = self.ftp.getcwd()
        pre = pre if pre else ''
        if local_is_path and self.isdir(remote_path):
            basename = os.path.basename(local_path)
            remote_path = posixpath.join(remote_path, basename)
        if output.running:
            print("[%s] put: %s -> %s" % (
                env.host_string,
                _format_local(local_path, local_is_path),
                posixpath.join(pre, remote_path)
            ))
        # When using sudo, "bounce" the file through a guaranteed-unique file
        # path in the default remote CWD (which, typically, the login user will
        # have write permissions on) in order to sudo(mv) it later.
        if use_sudo:
            target_path = remote_path
            hasher = hashlib.sha1()
            hasher.update(env.host_string)
            hasher.update(target_path)
            remote_path = posixpath.join(temp_dir, hasher.hexdigest())
        # Read, ensuring we handle file-like objects correct re: seek pointer
        putter = self.ftp.put
        if not local_is_path:
            old_pointer = local_path.tell()
            local_path.seek(0)
            putter = self.ftp.putfo
        rattrs = putter(local_path, remote_path)
        if not local_is_path:
            local_path.seek(old_pointer)
        # Handle modes if necessary
        if (local_is_path and mirror_local_mode) or (mode is not None):
            lmode = os.stat(local_path).st_mode if mirror_local_mode else mode
            # Cast to octal integer in case of string
            if isinstance(lmode, basestring):
                lmode = int(lmode, 8)
            lmode = lmode & 07777
            rmode = rattrs.st_mode
            # Only bitshift if we actually got an rmode
            if rmode is not None:
                rmode = (rmode & 07777)
            if lmode != rmode:
                if use_sudo:
                    # Temporarily nuke 'cwd' so sudo() doesn't "cd" its mv
                    # command. (The target path has already been cwd-ified
                    # elsewhere.)
                    with settings(hide('everything'), cwd=""):
                        sudo('chmod %o \"%s\"' % (lmode, remote_path))
                else:
                    self.ftp.chmod(remote_path, lmode)
        if use_sudo:
            # Temporarily nuke 'cwd' so sudo() doesn't "cd" its mv command.
            # (The target path has already been cwd-ified elsewhere.)
            with settings(hide('everything'), cwd=""):
                sudo("mv \"%s\" \"%s\"" % (remote_path, target_path))
            # Revert to original remote_path for return value's sake
            remote_path = target_path
        return remote_path

    def put_dir(self, local_path, remote_path, use_sudo, mirror_local_mode,
        mode, temp_dir):
        if os.path.basename(local_path):
            strip = os.path.dirname(local_path)
        else:
            strip = os.path.dirname(os.path.dirname(local_path))

        remote_paths = []

        for context, dirs, files in os.walk(local_path):
            rcontext = context.replace(strip, '', 1)
            # normalize pathname separators with POSIX separator
            rcontext = rcontext.replace(os.sep, '/')
            rcontext = rcontext.lstrip('/')
            rcontext = posixpath.join(remote_path, rcontext)

            if not self.exists(rcontext):
                self.mkdir(rcontext, use_sudo)

            for d in dirs:
                n = posixpath.join(rcontext, d)
                if not self.exists(n):
                    self.mkdir(n, use_sudo)

            for f in files:
                local_path = os.path.join(context, f)
                n = posixpath.join(rcontext, f)
                p = self.put(local_path, n, use_sudo, mirror_local_mode, mode,
                    True, temp_dir)
                remote_paths.append(p)
        return remote_paths

########NEW FILE########
__FILENAME__ = state
"""
Internal shared-state variables such as config settings and host lists.
"""

import os
import sys
from optparse import make_option

from fabric.network import HostConnectionCache, ssh
from fabric.version import get_version
from fabric.utils import _AliasDict, _AttributeDict


#
# Win32 flag
#

# Impacts a handful of platform specific behaviors. Note that Cygwin's Python
# is actually close enough to "real" UNIXes that it doesn't need (or want!) to
# use PyWin32 -- so we only test for literal Win32 setups (vanilla Python,
# ActiveState etc) here.
win32 = (sys.platform == 'win32')


#
# Environment dictionary - support structures
#

# By default, if the user (including code using Fabric as a library) doesn't
# set the username, we obtain the currently running username and use that.
def _get_system_username():
    """
    Obtain name of current system user, which will be default connection user.
    """
    import getpass
    username = None
    try:
        username = getpass.getuser()
    # getpass.getuser supported on both Unix and Windows systems.
    # getpass.getuser may call pwd.getpwuid which in turns may raise KeyError
    # if it cannot find a username for the given UID, e.g. on ep.io
    # and similar "non VPS" style services. Rather than error out, just keep
    # the 'default' username to None. Can check for this value later if needed.
    except KeyError:
        pass
    except ImportError:
        if win32:
            import win32api
            import win32security
            import win32profile
            username = win32api.GetUserName()
    return username

def _rc_path():
    """
    Return platform-specific default file path for $HOME/.fabricrc.
    """
    rc_file = '.fabricrc'
    rc_path = '~/' + rc_file
    expanded_rc_path = os.path.expanduser(rc_path)
    if expanded_rc_path == rc_path and win32:
            from win32com.shell.shell import SHGetSpecialFolderPath
            from win32com.shell.shellcon import CSIDL_PROFILE
            expanded_rc_path = "%s/%s" % (
                SHGetSpecialFolderPath(0, CSIDL_PROFILE),
                rc_file
                )
    return expanded_rc_path

default_port = '22'  # hurr durr
default_ssh_config_path = '~/.ssh/config'

# Options/settings which exist both as environment keys and which can be set on
# the command line, are defined here. When used via `fab` they will be added to
# the optparse parser, and either way they are added to `env` below (i.e.  the
# 'dest' value becomes the environment key and the value, the env value).
#
# Keep in mind that optparse changes hyphens to underscores when automatically
# deriving the `dest` name, e.g. `--reject-unknown-hosts` becomes
# `reject_unknown_hosts`.
#
# Furthermore, *always* specify some sort of default to avoid ending up with
# optparse.NO_DEFAULT (currently a two-tuple)! In general, None is a better
# default than ''.
#
# User-facing documentation for these are kept in sites/docs/env.rst.
env_options = [

    make_option('-a', '--no_agent',
        action='store_true',
        default=False,
        help="don't use the running SSH agent"
    ),

    make_option('-A', '--forward-agent',
        action='store_true',
        default=False,
        help="forward local agent to remote end"
    ),

    make_option('--abort-on-prompts',
        action='store_true',
        default=False,
        help="abort instead of prompting (for password, host, etc)"
    ),

    make_option('-c', '--config',
        dest='rcfile',
        default=_rc_path(),
        metavar='PATH',
        help="specify location of config file to use"
    ),

    make_option('--colorize-errors',
        action='store_true',
        default=False,
        help="Color error output",
    ),

    make_option('-D', '--disable-known-hosts',
        action='store_true',
        default=False,
        help="do not load user known_hosts file"
    ),

    make_option('-e', '--eagerly-disconnect',
        action='store_true',
        default=False,
        help="disconnect from hosts as soon as possible"
    ),

    make_option('-f', '--fabfile',
        default='fabfile',
        metavar='PATH',
        help="python module file to import, e.g. '../other.py'"
    ),

    make_option('-g', '--gateway',
        default=None,
        metavar='HOST',
        help="gateway host to connect through"
    ),

    make_option('--hide',
        metavar='LEVELS',
        help="comma-separated list of output levels to hide"
    ),

    make_option('-H', '--hosts',
        default=[],
        help="comma-separated list of hosts to operate on"
    ),

    make_option('-i',
        action='append',
        dest='key_filename',
        metavar='PATH',
        default=None,
        help="path to SSH private key file. May be repeated."
    ),

    make_option('-k', '--no-keys',
        action='store_true',
        default=False,
        help="don't load private key files from ~/.ssh/"
    ),

    make_option('--keepalive',
        dest='keepalive',
        type=int,
        default=0,
        metavar="N",
        help="enables a keepalive every N seconds"
    ),

    make_option('--linewise',
        action='store_true',
        default=False,
        help="print line-by-line instead of byte-by-byte"
    ),

    make_option('-n', '--connection-attempts',
        type='int',
        metavar='M',
        dest='connection_attempts',
        default=1,
        help="make M attempts to connect before giving up"
    ),

    make_option('--no-pty',
        dest='always_use_pty',
        action='store_false',
        default=True,
        help="do not use pseudo-terminal in run/sudo"
    ),

    make_option('-p', '--password',
        default=None,
        help="password for use with authentication and/or sudo"
    ),

    make_option('-P', '--parallel',
        dest='parallel',
        action='store_true',
        default=False,
        help="default to parallel execution method"
    ),

    make_option('--port',
        default=default_port,
        help="SSH connection port"
    ),

    make_option('-r', '--reject-unknown-hosts',
        action='store_true',
        default=False,
        help="reject unknown hosts"
    ),

    make_option('--system-known-hosts',
        default=None,
        help="load system known_hosts file before reading user known_hosts"
    ),

    make_option('-R', '--roles',
        default=[],
        help="comma-separated list of roles to operate on"
    ),

    make_option('-s', '--shell',
        default='/bin/bash -l -c',
        help="specify a new shell, defaults to '/bin/bash -l -c'"
    ),

    make_option('--show',
        metavar='LEVELS',
        help="comma-separated list of output levels to show"
    ),

    make_option('--skip-bad-hosts',
        action="store_true",
        default=False,
        help="skip over hosts that can't be reached"
    ),

    make_option('--ssh-config-path',
        default=default_ssh_config_path,
        metavar='PATH',
        help="Path to SSH config file"
    ),

    make_option('-t', '--timeout',
        type='int',
        default=10,
        metavar="N",
        help="set connection timeout to N seconds"
    ),

    make_option('-T', '--command-timeout',
        dest='command_timeout',
        type='int',
        default=None,
        metavar="N",
        help="set remote command timeout to N seconds"
    ),

    make_option('-u', '--user',
        default=_get_system_username(),
        help="username to use when connecting to remote hosts"
    ),

    make_option('-w', '--warn-only',
        action='store_true',
        default=False,
        help="warn, instead of abort, when commands fail"
    ),

    make_option('-x', '--exclude-hosts',
        default=[],
        metavar='HOSTS',
        help="comma-separated list of hosts to exclude"
    ),

    make_option('-z', '--pool-size',
            dest='pool_size',
            type='int',
            metavar='INT',
            default=0,
            help="number of concurrent processes to use in parallel mode",
    ),

]


#
# Environment dictionary - actual dictionary object
#


# Global environment dict. Currently a catchall for everything: config settings
# such as global deep/broad mode, host lists, username etc.
# Most default values are specified in `env_options` above, in the interests of
# preserving DRY: anything in here is generally not settable via the command
# line.
env = _AttributeDict({
    'abort_exception': None,
    'again_prompt': 'Sorry, try again.',
    'all_hosts': [],
    'combine_stderr': True,
    'colorize_errors': False,
    'command': None,
    'command_prefixes': [],
    'cwd': '',  # Must be empty string, not None, for concatenation purposes
    'dedupe_hosts': True,
    'default_port': default_port,
    'eagerly_disconnect': False,
    'echo_stdin': True,
    'effective_roles': [],
    'exclude_hosts': [],
    'gateway': None,
    'host': None,
    'host_string': None,
    'lcwd': '',  # Must be empty string, not None, for concatenation purposes
    'local_user': _get_system_username(),
    'output_prefix': True,
    'passwords': {},
    'path': '',
    'path_behavior': 'append',
    'port': default_port,
    'real_fabfile': None,
    'remote_interrupt': None,
    'roles': [],
    'roledefs': {},
    'shell_env': {},
    'skip_bad_hosts': False,
    'ssh_config_path': default_ssh_config_path,
    'ok_ret_codes': [0],     # a list of return codes that indicate success
    # -S so sudo accepts passwd via stdin, -p with our known-value prompt for
    # later detection (thus %s -- gets filled with env.sudo_prompt at runtime)
    'sudo_prefix': "sudo -S -p '%(sudo_prompt)s' ",
    'sudo_prompt': 'sudo password:',
    'sudo_user': None,
    'tasks': [],
    'prompts': {},
    'use_exceptions_for': {'network': False},
    'use_shell': True,
    'use_ssh_config': False,
    'user': None,
    'version': get_version('short')
})

# Fill in exceptions settings
exceptions = ['network']
exception_dict = {}
for e in exceptions:
    exception_dict[e] = False
env.use_exceptions_for = _AliasDict(exception_dict,
    aliases={'everything': exceptions})


# Add in option defaults
for option in env_options:
    env[option.dest] = option.default

#
# Command dictionary
#

# Keys are the command/function names, values are the callables themselves.
# This is filled in when main() runs.
commands = {}


#
# Host connection dict/cache
#

connections = HostConnectionCache()


def _open_session():
    return connections[env.host_string].get_transport().open_session()


def default_channel():
    """
    Return a channel object based on ``env.host_string``.
    """
    try:
        chan = _open_session()
    except ssh.SSHException, err:
        if str(err) == 'SSH session not active':
            connections[env.host_string].close()
            del connections[env.host_string]
            chan = _open_session()
        else:
            raise
    chan.settimeout(0.1)
    chan.input_enabled = True
    return chan


#
# Output controls
#

# Keys are "levels" or "groups" of output, values are always boolean,
# determining whether output falling into the given group is printed or not
# printed.
#
# By default, everything except 'debug' is printed, as this is what the average
# user, and new users, are most likely to expect.
#
# See docs/usage.rst for details on what these levels mean.
output = _AliasDict({
    'status': True,
    'aborts': True,
    'warnings': True,
    'running': True,
    'stdout': True,
    'stderr': True,
    'debug': False,
    'user': True
}, aliases={
    'everything': ['warnings', 'running', 'user', 'output'],
    'output': ['stdout', 'stderr'],
    'commands': ['stdout', 'running']
})

########NEW FILE########
__FILENAME__ = tasks
from __future__ import with_statement

from functools import wraps
import inspect
import sys
import textwrap

from fabric import state
from fabric.utils import abort, warn, error
from fabric.network import to_dict, normalize_to_string, disconnect_all
from fabric.context_managers import settings
from fabric.job_queue import JobQueue
from fabric.task_utils import crawl, merge, parse_kwargs
from fabric.exceptions import NetworkError

if sys.version_info[:2] == (2, 5):
    # Python 2.5 inspect.getargspec returns a tuple
    # instead of ArgSpec namedtuple.
    class ArgSpec(object):
        def __init__(self, args, varargs, keywords, defaults):
            self.args = args
            self.varargs = varargs
            self.keywords = keywords
            self.defaults = defaults
            self._tuple = (args, varargs, keywords, defaults)

        def __getitem__(self, idx):
            return self._tuple[idx]

    def patched_get_argspec(func):
        return ArgSpec(*inspect._getargspec(func))

    inspect._getargspec = inspect.getargspec
    inspect.getargspec = patched_get_argspec


def get_task_details(task):
    details = [
        textwrap.dedent(task.__doc__)
        if task.__doc__
        else 'No docstring provided']
    argspec = inspect.getargspec(task)

    default_args = [] if not argspec.defaults else argspec.defaults
    num_default_args = len(default_args)
    args_without_defaults = argspec.args[:len(argspec.args) - num_default_args]
    args_with_defaults = argspec.args[-1 * num_default_args:]

    details.append('Arguments: %s' % (
        ', '.join(
            args_without_defaults + [
                '%s=%r' % (arg, default)
                for arg, default in zip(args_with_defaults, default_args)
            ])
    ))

    return '\n'.join(details)


def _get_list(env):
    def inner(key):
        return env.get(key, [])
    return inner


class Task(object):
    """
    Abstract base class for objects wishing to be picked up as Fabric tasks.

    Instances of subclasses will be treated as valid tasks when present in
    fabfiles loaded by the :doc:`fab </usage/fab>` tool.

    For details on how to implement and use `~fabric.tasks.Task` subclasses,
    please see the usage documentation on :ref:`new-style tasks
    <new-style-tasks>`.

    .. versionadded:: 1.1
    """
    name = 'undefined'
    use_task_objects = True
    aliases = None
    is_default = False

    # TODO: make it so that this wraps other decorators as expected
    def __init__(self, alias=None, aliases=None, default=False, name=None,
        *args, **kwargs):
        if alias is not None:
            self.aliases = [alias, ]
        if aliases is not None:
            self.aliases = aliases
        if name is not None:
            self.name = name
        self.is_default = default

    def __details__(self):
        return get_task_details(self.run)

    def run(self):
        raise NotImplementedError

    def get_hosts_and_effective_roles(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
        """
        Return a tuple containing the host list the given task should be using
        and the roles being used.

        See :ref:`host-lists` for detailed documentation on how host lists are
        set.

        .. versionchanged:: 1.9
        """
        env = env or {'hosts': [], 'roles': [], 'exclude_hosts': []}
        roledefs = env.get('roledefs', {})
        # Command line per-task takes precedence over anything else.
        if arg_hosts or arg_roles:
            return merge(arg_hosts, arg_roles, arg_exclude_hosts, roledefs), arg_roles
        # Decorator-specific hosts/roles go next
        func_hosts = getattr(self, 'hosts', [])
        func_roles = getattr(self, 'roles', [])
        if func_hosts or func_roles:
            return merge(func_hosts, func_roles, arg_exclude_hosts, roledefs), func_roles
        # Finally, the env is checked (which might contain globally set lists
        # from the CLI or from module-level code). This will be the empty list
        # if these have not been set -- which is fine, this method should
        # return an empty list if no hosts have been set anywhere.
        env_vars = map(_get_list(env), "hosts roles exclude_hosts".split())
        env_vars.append(roledefs)
        return merge(*env_vars), env.get('roles', [])

    def get_pool_size(self, hosts, default):
        # Default parallel pool size (calculate per-task in case variables
        # change)
        default_pool_size = default or len(hosts)
        # Allow per-task override
        # Also cast to int in case somebody gave a string
        from_task = getattr(self, 'pool_size', None)
        pool_size = int(from_task or default_pool_size)
        # But ensure it's never larger than the number of hosts
        pool_size = min((pool_size, len(hosts)))
        # Inform user of final pool size for this task
        if state.output.debug:
            print("Parallel tasks now using pool size of %d" % pool_size)
        return pool_size


class WrappedCallableTask(Task):
    """
    Wraps a given callable transparently, while marking it as a valid Task.

    Generally used via `~fabric.decorators.task` and not directly.

    .. versionadded:: 1.1

    .. seealso:: `~fabric.docs.unwrap_tasks`, `~fabric.decorators.task`
    """
    def __init__(self, callable, *args, **kwargs):
        super(WrappedCallableTask, self).__init__(*args, **kwargs)
        self.wrapped = callable
        # Don't use getattr() here -- we want to avoid touching self.name
        # entirely so the superclass' value remains default.
        if hasattr(callable, '__name__'):
            if self.name == 'undefined':
                self.__name__ = self.name = callable.__name__
            else:
                self.__name__ = self.name
        if hasattr(callable, '__doc__'):
            self.__doc__ = callable.__doc__
        if hasattr(callable, '__module__'):
            self.__module__ = callable.__module__

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.wrapped(*args, **kwargs)

    def __getattr__(self, k):
        return getattr(self.wrapped, k)

    def __details__(self):
        return get_task_details(self.wrapped)


def requires_parallel(task):
    """
    Returns True if given ``task`` should be run in parallel mode.

    Specifically:

    * It's been explicitly marked with ``@parallel``, or:
    * It's *not* been explicitly marked with ``@serial`` *and* the global
      parallel option (``env.parallel``) is set to ``True``.
    """
    return (
        (state.env.parallel and not getattr(task, 'serial', False))
        or getattr(task, 'parallel', False)
    )


def _parallel_tasks(commands_to_run):
    return any(map(
        lambda x: requires_parallel(crawl(x[0], state.commands)),
        commands_to_run
    ))


def _execute(task, host, my_env, args, kwargs, jobs, queue, multiprocessing):
    """
    Primary single-host work body of execute()
    """
    # Log to stdout
    if state.output.running and not hasattr(task, 'return_value'):
        print("[%s] Executing task '%s'" % (host, my_env['command']))
    # Create per-run env with connection settings
    local_env = to_dict(host)
    local_env.update(my_env)
    # Set a few more env flags for parallelism
    if queue is not None:
        local_env.update({'parallel': True, 'linewise': True})
    # Handle parallel execution
    if queue is not None: # Since queue is only set for parallel
        name = local_env['host_string']
        # Wrap in another callable that:
        # * expands the env it's given to ensure parallel, linewise, etc are
        #   all set correctly and explicitly. Such changes are naturally
        #   insulted from the parent process.
        # * nukes the connection cache to prevent shared-access problems
        # * knows how to send the tasks' return value back over a Queue
        # * captures exceptions raised by the task
        def inner(args, kwargs, queue, name, env):
            state.env.update(env)
            def submit(result):
                queue.put({'name': name, 'result': result})
            try:
                key = normalize_to_string(state.env.host_string)
                state.connections.pop(key, "")
                submit(task.run(*args, **kwargs))
            except BaseException, e: # We really do want to capture everything
                # SystemExit implies use of abort(), which prints its own
                # traceback, host info etc -- so we don't want to double up
                # on that. For everything else, though, we need to make
                # clear what host encountered the exception that will
                # print.
                if e.__class__ is not SystemExit:
                    sys.stderr.write("!!! Parallel execution exception under host %r:\n" % name)
                    submit(e)
                # Here, anything -- unexpected exceptions, or abort()
                # driven SystemExits -- will bubble up and terminate the
                # child process.
                raise

        # Stuff into Process wrapper
        kwarg_dict = {
            'args': args,
            'kwargs': kwargs,
            'queue': queue,
            'name': name,
            'env': local_env,
        }
        p = multiprocessing.Process(target=inner, kwargs=kwarg_dict)
        # Name/id is host string
        p.name = name
        # Add to queue
        jobs.append(p)
    # Handle serial execution
    else:
        with settings(**local_env):
            return task.run(*args, **kwargs)

def _is_task(task):
    return isinstance(task, Task)

def execute(task, *args, **kwargs):
    """
    Execute ``task`` (callable or name), honoring host/role decorators, etc.

    ``task`` may be an actual callable object, or it may be a registered task
    name, which is used to look up a callable just as if the name had been
    given on the command line (including :ref:`namespaced tasks <namespaces>`,
    e.g. ``"deploy.migrate"``.

    The task will then be executed once per host in its host list, which is
    (again) assembled in the same manner as CLI-specified tasks: drawing from
    :option:`-H`, :ref:`env.hosts <hosts>`, the `~fabric.decorators.hosts` or
    `~fabric.decorators.roles` decorators, and so forth.

    ``host``, ``hosts``, ``role``, ``roles`` and ``exclude_hosts`` kwargs will
    be stripped out of the final call, and used to set the task's host list, as
    if they had been specified on the command line like e.g. ``fab
    taskname:host=hostname``.

    Any other arguments or keyword arguments will be passed verbatim into
    ``task`` (the function itself -- not the ``@task`` decorator wrapping your
    function!) when it is called, so ``execute(mytask, 'arg1',
    kwarg1='value')`` will (once per host) invoke ``mytask('arg1',
    kwarg1='value')``.

    :returns:
        a dictionary mapping host strings to the given task's return value for
        that host's execution run. For example, ``execute(foo, hosts=['a',
        'b'])`` might return ``{'a': None, 'b': 'bar'}`` if ``foo`` returned
        nothing on host `a` but returned ``'bar'`` on host `b`.

        In situations where a task execution fails for a given host but overall
        progress does not abort (such as when :ref:`env.skip_bad_hosts
        <skip-bad-hosts>` is True) the return value for that host will be the
        error object or message.

    .. seealso::
        :ref:`The execute usage docs <execute>`, for an expanded explanation
        and some examples.

    .. versionadded:: 1.3
    .. versionchanged:: 1.4
        Added the return value mapping; previously this function had no defined
        return value.
    """
    my_env = {'clean_revert': True}
    results = {}
    # Obtain task
    is_callable = callable(task)
    if not (is_callable or _is_task(task)):
        # Assume string, set env.command to it
        my_env['command'] = task
        task = crawl(task, state.commands)
        if task is None:
            abort("%r is not callable or a valid task name" % (task,))
    # Set env.command if we were given a real function or callable task obj
    else:
        dunder_name = getattr(task, '__name__', None)
        my_env['command'] = getattr(task, 'name', dunder_name)
    # Normalize to Task instance if we ended up with a regular callable
    if not _is_task(task):
        task = WrappedCallableTask(task)
    # Filter out hosts/roles kwargs
    new_kwargs, hosts, roles, exclude_hosts = parse_kwargs(kwargs)
    # Set up host list
    my_env['all_hosts'], my_env['effective_roles'] = task.get_hosts_and_effective_roles(hosts, roles,
                                                                                        exclude_hosts, state.env)

    parallel = requires_parallel(task)
    if parallel:
        # Import multiprocessing if needed, erroring out usefully
        # if it can't.
        try:
            import multiprocessing
        except ImportError:
            import traceback
            tb = traceback.format_exc()
            abort(tb + """
    At least one task needs to be run in parallel, but the
    multiprocessing module cannot be imported (see above
    traceback.) Please make sure the module is installed
    or that the above ImportError is fixed.""")
    else:
        multiprocessing = None

    # Get pool size for this task
    pool_size = task.get_pool_size(my_env['all_hosts'], state.env.pool_size)
    # Set up job queue in case parallel is needed
    queue = multiprocessing.Queue() if parallel else None
    jobs = JobQueue(pool_size, queue)
    if state.output.debug:
        jobs._debug = True

    # Call on host list
    if my_env['all_hosts']:
        # Attempt to cycle on hosts, skipping if needed
        for host in my_env['all_hosts']:
            try:
                results[host] = _execute(
                    task, host, my_env, args, new_kwargs, jobs, queue,
                    multiprocessing
                )
            except NetworkError, e:
                results[host] = e
                # Backwards compat test re: whether to use an exception or
                # abort
                if not state.env.use_exceptions_for['network']:
                    func = warn if state.env.skip_bad_hosts else abort
                    error(e.message, func=func, exception=e.wrapped)
                else:
                    raise

            # If requested, clear out connections here and not just at the end.
            if state.env.eagerly_disconnect:
                disconnect_all()

        # If running in parallel, block until job queue is emptied
        if jobs:
            err = "One or more hosts failed while executing task '%s'" % (
                my_env['command']
            )
            jobs.close()
            # Abort if any children did not exit cleanly (fail-fast).
            # This prevents Fabric from continuing on to any other tasks.
            # Otherwise, pull in results from the child run.
            ran_jobs = jobs.run()
            for name, d in ran_jobs.iteritems():
                if d['exit_code'] != 0:
                    if isinstance(d['results'], BaseException):
                        error(err, exception=d['results'])
                    else:
                        error(err)
                results[name] = d['results']

    # Or just run once for local-only
    else:
        with settings(**my_env):
            results['<local-only>'] = task.run(*args, **new_kwargs)
    # Return what we can from the inner task executions

    return results

########NEW FILE########
__FILENAME__ = task_utils
from fabric.utils import abort, indent
from fabric import state


# For attribute tomfoolery
class _Dict(dict):
    pass


def _crawl(name, mapping):
    """
    ``name`` of ``'a.b.c'`` => ``mapping['a']['b']['c']``
    """
    key, _, rest = name.partition('.')
    value = mapping[key]
    if not rest:
        return value
    return _crawl(rest, value)


def crawl(name, mapping):
    try:
        result = _crawl(name, mapping)
        # Handle default tasks
        if isinstance(result, _Dict):
            if getattr(result, 'default', False):
                result = result.default
            # Ensure task modules w/ no default are treated as bad targets
            else:
                result = None
        return result
    except (KeyError, TypeError):
        return None


def merge(hosts, roles, exclude, roledefs):
    """
    Merge given host and role lists into one list of deduped hosts.
    """
    # Abort if any roles don't exist
    bad_roles = [x for x in roles if x not in roledefs]
    if bad_roles:
        abort("The following specified roles do not exist:\n%s" % (
            indent(bad_roles)
        ))

    # Coerce strings to one-item lists
    if isinstance(hosts, basestring):
        hosts = [hosts]

    # Look up roles, turn into flat list of hosts
    role_hosts = []
    for role in roles:
        value = roledefs[role]
        # Handle "lazy" roles (callables)
        if callable(value):
            value = value()
        role_hosts += value

    # Strip whitespace from host strings.
    cleaned_hosts = [x.strip() for x in list(hosts) + list(role_hosts)]
    # Return deduped combo of hosts and role_hosts, preserving order within
    # them (vs using set(), which may lose ordering) and skipping hosts to be
    # excluded.
    # But only if the user hasn't indicated they want this behavior disabled.
    all_hosts = cleaned_hosts
    if state.env.dedupe_hosts:
        deduped_hosts = []
        for host in cleaned_hosts:
            if host not in deduped_hosts and host not in exclude:
                deduped_hosts.append(host)
        all_hosts = deduped_hosts
    return all_hosts


def parse_kwargs(kwargs):
    new_kwargs = {}
    hosts = []
    roles = []
    exclude_hosts = []
    for key, value in kwargs.iteritems():
        if key == 'host':
            hosts = [value]
        elif key == 'hosts':
            hosts = value
        elif key == 'role':
            roles = [value]
        elif key == 'roles':
            roles = value
        elif key == 'exclude_hosts':
            exclude_hosts = value
        else:
            new_kwargs[key] = value
    return new_kwargs, hosts, roles, exclude_hosts

########NEW FILE########
__FILENAME__ = thread_handling
import threading
import sys


class ThreadHandler(object):
    def __init__(self, name, callable, *args, **kwargs):
        # Set up exception handling
        self.exception = None

        def wrapper(*args, **kwargs):
            try:
                callable(*args, **kwargs)
            except BaseException:
                self.exception = sys.exc_info()
        # Kick off thread
        thread = threading.Thread(None, wrapper, name, args, kwargs)
        thread.setDaemon(True)
        thread.start()
        # Make thread available to instantiator
        self.thread = thread

    def raise_if_needed(self):
        if self.exception:
            e = self.exception
            raise e[0], e[1], e[2]

########NEW FILE########
__FILENAME__ = utils
"""
Internal subroutines for e.g. aborting execution with an error message,
or performing indenting on multiline output.
"""
import os
import sys
import textwrap
from traceback import format_exc

def abort(msg):
    """
    Abort execution, print ``msg`` to stderr and exit with error status (1.)

    This function currently makes use of `sys.exit`_, which raises
    `SystemExit`_. Therefore, it's possible to detect and recover from inner
    calls to `abort` by using ``except SystemExit`` or similar.

    .. _sys.exit: http://docs.python.org/library/sys.html#sys.exit
    .. _SystemExit: http://docs.python.org/library/exceptions.html#exceptions.SystemExit
    """
    from fabric.state import output, env
    if not env.colorize_errors:
        red  = lambda x: x
    else:
        from colors import red

    if output.aborts:
        sys.stderr.write(red("\nFatal error: %s\n" % str(msg)))
        sys.stderr.write(red("\nAborting.\n"))

    if env.abort_exception:
        raise env.abort_exception(msg)
    else:
        sys.exit(1)


def warn(msg):
    """
    Print warning message, but do not abort execution.

    This function honors Fabric's :doc:`output controls
    <../../usage/output_controls>` and will print the given ``msg`` to stderr,
    provided that the ``warnings`` output level (which is active by default) is
    turned on.
    """
    from fabric.state import output, env

    if not env.colorize_errors:
        magenta = lambda x: x
    else:
        from colors import magenta

    if output.warnings:
        sys.stderr.write(magenta("\nWarning: %s\n\n" % msg))


def indent(text, spaces=4, strip=False):
    """
    Return ``text`` indented by the given number of spaces.

    If text is not a string, it is assumed to be a list of lines and will be
    joined by ``\\n`` prior to indenting.

    When ``strip`` is ``True``, a minimum amount of whitespace is removed from
    the left-hand side of the given string (so that relative indents are
    preserved, but otherwise things are left-stripped). This allows you to
    effectively "normalize" any previous indentation for some inputs.
    """
    # Normalize list of strings into a string for dedenting. "list" here means
    # "not a string" meaning "doesn't have splitlines". Meh.
    if not hasattr(text, 'splitlines'):
        text = '\n'.join(text)
    # Dedent if requested
    if strip:
        text = textwrap.dedent(text)
    prefix = ' ' * spaces
    output = '\n'.join(prefix + line for line in text.splitlines())
    # Strip out empty lines before/aft
    output = output.strip()
    # Reintroduce first indent (which just got stripped out)
    output = prefix + output
    return output


def puts(text, show_prefix=None, end="\n", flush=False):
    """
    An alias for ``print`` whose output is managed by Fabric's output controls.

    In other words, this function simply prints to ``sys.stdout``, but will
    hide its output if the ``user`` :doc:`output level
    </usage/output_controls>` is set to ``False``.

    If ``show_prefix=False``, `puts` will omit the leading ``[hostname]``
    which it tacks on by default. (It will also omit this prefix if
    ``env.host_string`` is empty.)

    Newlines may be disabled by setting ``end`` to the empty string (``''``).
    (This intentionally mirrors Python 3's ``print`` syntax.)

    You may force output flushing (e.g. to bypass output buffering) by setting
    ``flush=True``.

    .. versionadded:: 0.9.2
    .. seealso:: `~fabric.utils.fastprint`
    """
    from fabric.state import output, env
    if show_prefix is None:
        show_prefix = env.output_prefix
    if output.user:
        prefix = ""
        if env.host_string and show_prefix:
            prefix = "[%s] " % env.host_string
        sys.stdout.write(prefix + str(text) + end)
        if flush:
            sys.stdout.flush()


def fastprint(text, show_prefix=False, end="", flush=True):
    """
    Print ``text`` immediately, without any prefix or line ending.

    This function is simply an alias of `~fabric.utils.puts` with different
    default argument values, such that the ``text`` is printed without any
    embellishment and immediately flushed.

    It is useful for any situation where you wish to print text which might
    otherwise get buffered by Python's output buffering (such as within a
    processor intensive ``for`` loop). Since such use cases typically also
    require a lack of line endings (such as printing a series of dots to
    signify progress) it also omits the traditional newline by default.

    .. note::

        Since `~fabric.utils.fastprint` calls `~fabric.utils.puts`, it is
        likewise subject to the ``user`` :doc:`output level
        </usage/output_controls>`.

    .. versionadded:: 0.9.2
    .. seealso:: `~fabric.utils.puts`
    """
    return puts(text=text, show_prefix=show_prefix, end=end, flush=flush)


def handle_prompt_abort(prompt_for):
    import fabric.state
    reason = "Needed to prompt for %s (host: %s), but %%s" % (
        prompt_for, fabric.state.env.host_string
    )
    # Explicit "don't prompt me bro"
    if fabric.state.env.abort_on_prompts:
        abort(reason % "abort-on-prompts was set to True")
    # Implicit "parallel == stdin/prompts have ambiguous target"
    if fabric.state.env.parallel:
        abort(reason % "input would be ambiguous in parallel mode")


class _AttributeDict(dict):
    """
    Dictionary subclass enabling attribute lookup/assignment of keys/values.

    For example::

        >>> m = _AttributeDict({'foo': 'bar'})
        >>> m.foo
        'bar'
        >>> m.foo = 'not bar'
        >>> m['foo']
        'not bar'

    ``_AttributeDict`` objects also provide ``.first()`` which acts like
    ``.get()`` but accepts multiple keys as arguments, and returns the value of
    the first hit, e.g.::

        >>> m = _AttributeDict({'foo': 'bar', 'biz': 'baz'})
        >>> m.first('wrong', 'incorrect', 'foo', 'biz')
        'bar'

    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            # to conform with __getattr__ spec
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def first(self, *names):
        for name in names:
            value = self.get(name)
            if value:
                return value


class _AliasDict(_AttributeDict):
    """
    `_AttributeDict` subclass that allows for "aliasing" of keys to other keys.

    Upon creation, takes an ``aliases`` mapping, which should map alias names
    to lists of key names. Aliases do not store their own value, but instead
    set (override) all mapped keys' values. For example, in the following
    `_AliasDict`, calling ``mydict['foo'] = True`` will set the values of
    ``mydict['bar']``, ``mydict['biz']`` and ``mydict['baz']`` all to True::

        mydict = _AliasDict(
            {'biz': True, 'baz': False},
            aliases={'foo': ['bar', 'biz', 'baz']}
        )

    Because it is possible for the aliased values to be in a heterogenous
    state, reading aliases is not supported -- only writing to them is allowed.
    This also means they will not show up in e.g. ``dict.keys()``.

    ..note::

        Aliases are recursive, so you may refer to an alias within the key list
        of another alias. Naturally, this means that you can end up with
        infinite loops if you're not careful.

    `_AliasDict` provides a special function, `expand_aliases`, which will take
    a list of keys as an argument and will return that list of keys with any
    aliases expanded. This function will **not** dedupe, so any aliases which
    overlap will result in duplicate keys in the resulting list.
    """
    def __init__(self, arg=None, aliases=None):
        init = super(_AliasDict, self).__init__
        if arg is not None:
            init(arg)
        else:
            init()
        # Can't use super() here because of _AttributeDict's setattr override
        dict.__setattr__(self, 'aliases', aliases)

    def __setitem__(self, key, value):
        # Attr test required to not blow up when deepcopy'd
        if hasattr(self, 'aliases') and key in self.aliases:
            for aliased in self.aliases[key]:
                self[aliased] = value
        else:
            return super(_AliasDict, self).__setitem__(key, value)

    def expand_aliases(self, keys):
        ret = []
        for key in keys:
            if key in self.aliases:
                ret.extend(self.expand_aliases(self.aliases[key]))
            else:
                ret.append(key)
        return ret


def _pty_size():
    """
    Obtain (rows, cols) tuple for sizing a pty on the remote end.

    Defaults to 80x24 (which is also the 'ssh' lib's default) but will detect
    local (stdout-based) terminal window size on non-Windows platforms.
    """
    from fabric.state import win32
    if not win32:
        import fcntl
        import termios
        import struct

    default_rows, default_cols = 24, 80
    rows, cols = default_rows, default_cols
    if not win32 and sys.stdout.isatty():
        # We want two short unsigned integers (rows, cols)
        fmt = 'HH'
        # Create an empty (zeroed) buffer for ioctl to map onto. Yay for C!
        buffer = struct.pack(fmt, 0, 0)
        # Call TIOCGWINSZ to get window size of stdout, returns our filled
        # buffer
        try:
            result = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ,
                buffer)
            # Unpack buffer back into Python data types
            rows, cols = struct.unpack(fmt, result)
            # Fall back to defaults if TIOCGWINSZ returns unreasonable values
            if rows == 0:
                rows = default_rows
            if cols == 0:
                cols = default_cols
        # Deal with e.g. sys.stdout being monkeypatched, such as in testing.
        # Or termios not having a TIOCGWINSZ.
        except AttributeError:
            pass
    return rows, cols


def error(message, func=None, exception=None, stdout=None, stderr=None):
    """
    Call ``func`` with given error ``message``.

    If ``func`` is None (the default), the value of ``env.warn_only``
    determines whether to call ``abort`` or ``warn``.

    If ``exception`` is given, it is inspected to get a string message, which
    is printed alongside the user-generated ``message``.

    If ``stdout`` and/or ``stderr`` are given, they are assumed to be strings
    to be printed.
    """
    import fabric.state
    if func is None:
        func = fabric.state.env.warn_only and warn or abort
    # If debug printing is on, append a traceback to the message
    if fabric.state.output.debug:
        message += "\n\n" + format_exc()
    # Otherwise, if we were given an exception, append its contents.
    elif exception is not None:
        # Figure out how to get a string out of the exception; EnvironmentError
        # subclasses, for example, "are" integers and .strerror is the string.
        # Others "are" strings themselves. May have to expand this further for
        # other error types.
        if hasattr(exception, 'strerror') and exception.strerror is not None:
            underlying = exception.strerror
        else:
            underlying = exception
        message += "\n\nUnderlying exception:\n" + indent(str(underlying))
    if func is abort:
        if stdout and not fabric.state.output.stdout:
            message += _format_error_output("Standard output", stdout)
        if stderr and not fabric.state.output.stderr:
            message += _format_error_output("Standard error", stderr)
    return func(message)


def _format_error_output(header, body):
    term_width = _pty_size()[1]
    header_side_length = (term_width - (len(header) + 2)) / 2
    mark = "="
    side = mark * header_side_length
    return "\n\n%s %s %s\n\n%s\n\n%s" % (
        side, header, side, body, mark * term_width
    )


# TODO: replace with collections.deque(maxlen=xxx) in Python 2.6
class RingBuffer(list):
    def __init__(self, value, maxlen):
        # Heh.
        self._super = super(RingBuffer, self)
        self._maxlen = maxlen
        return self._super.__init__(value)

    def _free(self):
        return self._maxlen - len(self)

    def append(self, value):
        if self._free() == 0:
            del self[0]
        return self._super.append(value)

    def extend(self, values):
        overage = len(values) - self._free()
        if overage > 0:
            del self[0:overage]
        return self._super.extend(values)

    # Paranoia from here on out.
    def insert(self, index, value):
        raise ValueError("Can't insert into the middle of a ring buffer!")

    def __setslice__(self, i, j, sequence):
        raise ValueError("Can't set a slice of a ring buffer!")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            raise ValueError("Can't set a slice of a ring buffer!")
        else:
            return self._super.__setitem__(key, value)


def apply_lcwd(path, env):
    # Apply CWD if a relative path
    if not os.path.isabs(path) and env.lcwd:
        path = os.path.join(env.lcwd, path)
    return path

########NEW FILE########
__FILENAME__ = version
"""
Current Fabric version constant plus version pretty-print method.

This functionality is contained in its own module to prevent circular import
problems with ``__init__.py`` (which is loaded by setup.py during installation,
which in turn needs access to this version information.)
"""
from subprocess import Popen, PIPE
from os.path import abspath, dirname


VERSION = (1, 8, 3, 'final', 0)


def git_sha():
    loc = abspath(dirname(__file__))
    try:
        p = Popen(
            "cd \"%s\" && git log -1 --format=format:%%h" % loc,
            shell=True,
            stdout=PIPE,
            stderr=PIPE
        )
        return p.communicate()[0]
    # OSError occurs on Unix-derived platforms lacking Popen's configured shell
    # default, /bin/sh. E.g. Android.
    except OSError:
        return None


def get_version(form='short'):
    """
    Return a version string for this package, based on `VERSION`.

    Takes a single argument, ``form``, which should be one of the following
    strings:

    * ``branch``: just the major + minor, e.g. "0.9", "1.0".
    * ``short`` (default): compact, e.g. "0.9rc1", "0.9.0". For package
      filenames or SCM tag identifiers.
    * ``normal``: human readable, e.g. "0.9", "0.9.1", "0.9 beta 1". For e.g.
      documentation site headers.
    * ``verbose``: like ``normal`` but fully explicit, e.g. "0.9 final". For
      tag commit messages, or anywhere that it's important to remove ambiguity
      between a branch and the first final release within that branch.
    * ``all``: Returns all of the above, as a dict.
    """
    # Setup
    versions = {}
    branch = "%s.%s" % (VERSION[0], VERSION[1])
    tertiary = VERSION[2]
    type_ = VERSION[3]
    final = (type_ == "final")
    type_num = VERSION[4]
    firsts = "".join([x[0] for x in type_.split()])
    sha = git_sha()
    sha1 = (" (%s)" % sha) if sha else ""

    # Branch
    versions['branch'] = branch

    # Short
    v = branch
    if (tertiary or final):
        v += "." + str(tertiary)
    if not final:
        v += firsts
        if type_num:
            v += str(type_num)
        else:
            v += sha1
    versions['short'] = v

    # Normal
    v = branch
    if tertiary:
        v += "." + str(tertiary)
    if not final:
        if type_num:
            v += " " + type_ + " " + str(type_num)
        else:
            v += " pre-" + type_ + sha1
    versions['normal'] = v

    # Verbose
    v = branch
    if tertiary:
        v += "." + str(tertiary)
    if not final:
        if type_num:
            v += " " + type_ + " " + str(type_num)
        else:
            v += " pre-" + type_ + sha1
    else:
        v += " final"
    versions['verbose'] = v

    try:
        return versions[form]
    except KeyError:
        if form == 'all':
            return versions
        raise TypeError('"%s" is not a valid form specifier.' % form)

__version__ = get_version('short')

if __name__ == "__main__":
    print(get_version('all'))

########NEW FILE########
__FILENAME__ = test_contrib
import os
import types
import re
import sys

from fabric.api import run, local
from fabric.contrib import files, project

from utils import Integration


def tildify(path):
    home = run("echo ~", quiet=True).stdout.strip()
    return path.replace('~', home)

def expect(path):
    assert files.exists(tildify(path))

def expect_contains(path, value):
    assert files.contains(tildify(path), value)

def escape(path):
    return path.replace(' ', r'\ ')


class FileCleaner(Integration):
    def setup(self):
        self.local = []
        self.remote = []

    def teardown(self):
        super(FileCleaner, self).teardown()
        for created in self.local:
            os.unlink(created)
        for created in self.remote:
            run("rm %s" % escape(created))


class TestTildeExpansion(FileCleaner):
    def test_append(self):
        for target in ('~/append_test', '~/append_test with spaces'):
            self.remote.append(target)
            files.append(target, ['line'])
            expect(target)

    def test_exists(self):
        for target in ('~/exists_test', '~/exists test with space'):
            self.remote.append(target)
            run("touch %s" % escape(target))
            expect(target)
     
    def test_sed(self):
        for target in ('~/sed_test', '~/sed test with space'):
            self.remote.append(target)
            run("echo 'before' > %s" % escape(target))
            files.sed(target, 'before', 'after')
            expect_contains(target, 'after')
     
    def test_upload_template(self):
        for i, target in enumerate((
            '~/upload_template_test',
            '~/upload template test with space'
        )):
            src = "source%s" % i
            local("touch %s" % src)
            self.local.append(src)
            self.remote.append(target)
            files.upload_template(src, target)
            expect(target)


class TestIsLink(FileCleaner):
    # TODO: add more of these. meh.
    def test_is_link_is_true_on_symlink(self):
        self.remote.extend(['/tmp/foo', '/tmp/bar'])
        run("touch /tmp/foo")
        run("ln -s /tmp/foo /tmp/bar")
        assert files.is_link('/tmp/bar')

    def test_is_link_is_false_on_non_link(self):
        self.remote.append('/tmp/biz')
        run("touch /tmp/biz")
        assert not files.is_link('/tmp/biz')


rsync_sources = (
    'integration/',
    'integration/test_contrib.py',
    'integration/test_operations.py',
    'integration/utils.py'
)

class TestRsync(Integration):
    def rsync(self, id_, **kwargs):
        return project.rsync_project(
            remote_dir='/tmp/rsync-test-%s/' % id_,
            local_dir='integration',
            ssh_opts='-o StrictHostKeyChecking=no',
            capture=True,
            **kwargs
        )

    def test_existing_default_args(self):
        """
        Rsync uses -v by default
        """
        r = self.rsync(1)
        for x in rsync_sources:
            assert re.search(r'^%s$' % x, r.stdout, re.M), "'%s' was not found in '%s'" % (x, r.stdout)

    def test_overriding_default_args(self):
        """
        Use of default_args kwarg can be used to nuke e.g. -v
        """
        r = self.rsync(2, default_opts='-pthrz')
        for x in rsync_sources:
            assert not re.search(r'^%s$' % x, r.stdout, re.M), "'%s' was found in '%s'" % (x, r.stdout)


class TestUploadTemplate(FileCleaner):
    def test_allows_pty_disable(self):
        src = "source_file"
        target = "remote_file"
        local("touch %s" % src)
        self.local.append(src)
        self.remote.append(target)
        # Just make sure it doesn't asplode. meh.
        files.upload_template(src, target, pty=False)
        expect(target)

########NEW FILE########
__FILENAME__ = test_operations
from __future__ import with_statement

from StringIO import StringIO
import os
import posixpath
import shutil

from fabric.api import run, path, put, sudo, abort, warn_only, env, cd, local
from fabric.contrib.files import exists

from utils import Integration


def assert_mode(path, mode):
    remote_mode = run("stat -c \"%%a\" \"%s\"" % path).stdout
    assert remote_mode == mode, "remote %r != expected %r" % (remote_mode, mode)


class TestOperations(Integration):
    filepath = "/tmp/whocares"
    dirpath = "/tmp/whatever/bin"
    not_owned = "/tmp/notmine"

    def setup(self):
        super(TestOperations, self).setup()
        run("mkdir -p %s" % " ".join([self.dirpath, self.not_owned]))

    def teardown(self):
        super(TestOperations, self).teardown()
        # Revert any chown crap from put sudo tests
        sudo("chown %s ." % env.user)
        # Nuke to prevent bleed
        sudo("rm -rf %s" % " ".join([self.dirpath, self.filepath]))
        sudo("rm -rf %s" % self.not_owned)

    def test_no_trailing_space_in_shell_path_in_run(self):
        put(StringIO("#!/bin/bash\necho hi"), "%s/myapp" % self.dirpath, mode="0755")
        with path(self.dirpath):
            assert run('myapp').stdout == 'hi'

    def test_string_put_mode_arg_doesnt_error(self):
        put(StringIO("#!/bin/bash\necho hi"), self.filepath, mode="0755")
        assert_mode(self.filepath, "755")

    def test_int_put_mode_works_ok_too(self):
        put(StringIO("#!/bin/bash\necho hi"), self.filepath, mode=0755)
        assert_mode(self.filepath, "755")

    def _chown(self, target):
        sudo("chown root %s" % target)

    def _put_via_sudo(self, source=None, target_suffix='myfile', **kwargs):
        # Ensure target dir prefix is not owned by our user (so we fail unless
        # the sudo part of things is working)
        self._chown(self.not_owned)
        source = source if source else StringIO("whatever")
        # Drop temp file into that dir, via use_sudo, + any kwargs
        return put(
            source,
            self.not_owned + '/' + target_suffix,
            use_sudo=True,
            **kwargs
        )

    def test_put_with_use_sudo(self):
        self._put_via_sudo()

    def test_put_with_dir_and_use_sudo(self):
        # Test cwd should be root of fabric source tree. Use our own folder as
        # the source, meh.
        self._put_via_sudo(source='integration', target_suffix='')

    def test_put_with_use_sudo_and_custom_temp_dir(self):
        # TODO: allow dependency injection in sftp.put or w/e, test it in
        # isolation instead.
        # For now, just half-ass it by ensuring $HOME isn't writable
        # temporarily.
        self._chown('.')
        self._put_via_sudo(temp_dir='/tmp')

    def test_put_with_use_sudo_dir_and_custom_temp_dir(self):
        self._chown('.')
        self._put_via_sudo(source='integration', target_suffix='', temp_dir='/tmp')

    def test_put_use_sudo_and_explicit_mode(self):
        # Setup
        target_dir = posixpath.join(self.filepath, 'blah')
        subdir = "inner"
        subdir_abs = posixpath.join(target_dir, subdir)
        filename = "whatever.txt"
        target_file = posixpath.join(subdir_abs, filename)
        run("mkdir -p %s" % subdir_abs)
        self._chown(subdir_abs)
        local_path = os.path.join('/tmp', filename)
        with open(local_path, 'w+') as fd:
            fd.write('stuff\n')
        # Upload + assert
        with cd(target_dir):
            put(local_path, subdir, use_sudo=True, mode='777')
        assert_mode(target_file, '777')

    def test_put_file_to_dir_with_use_sudo_and_mirror_mode(self):
        # Ensure mode of local file, umask varies on eg travis vs various
        # localhosts
        source = 'whatever.txt'
        try:
            local("touch %s" % source)
            local("chmod 644 %s" % source)
            # Target for _put_via_sudo is a directory by default
            uploaded = self._put_via_sudo(
                source=source, mirror_local_mode=True
            )
            assert_mode(uploaded[0], '644')
        finally:
            local("rm -f %s" % source)

    def test_put_directory_use_sudo_and_spaces(self):
        localdir = 'I have spaces'
        localfile = os.path.join(localdir, 'file.txt')
        os.mkdir(localdir)
        with open(localfile, 'w') as fd:
            fd.write('stuff\n')
        try:
            uploaded = self._put_via_sudo(localdir, target_suffix='')
            # Kinda dumb, put() would've died if it couldn't do it, but.
            assert exists(uploaded[0])
            assert exists(posixpath.dirname(uploaded[0]))
        finally:
            shutil.rmtree(localdir)

########NEW FILE########
__FILENAME__ = utils
import os
import sys

# Pull in regular tests' utilities
mod = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests'))
sys.path.insert(0, mod)
from mock_streams import mock_streams
#from utils import FabricTest
# Clean up
del sys.path[0]


class Integration(object):
    def setup(self):
        # Just so subclasses can super() us w/o fear. Meh.
        pass

    def teardown(self):
        # Just so subclasses can super() us w/o fear. Meh.
        pass

########NEW FILE########
__FILENAME__ = conf
# Obtain shared config values
import os, sys
from os.path import abspath, join, dirname
sys.path.append(abspath(join(dirname(__file__), '..')))
sys.path.append(abspath(join(dirname(__file__), '..', '..')))
from shared_conf import *

# Enable autodoc, intersphinx
extensions.extend(['sphinx.ext.autodoc', 'sphinx.ext.intersphinx'])

# Autodoc settings
autodoc_default_flags = ['members', 'special-members']

# Default is 'local' building, but reference the public WWW site when building
# under RTD.
target = join(dirname(__file__), '..', 'www', '_build')
if os.environ.get('READTHEDOCS') == 'True':
    target = 'http://www.fabfile.org/'
# Intersphinx connection to stdlib + www site
intersphinx_mapping = {
    'python': ('http://docs.python.org/2.6', None),
    'www': (target, None),
}

# Sister-site links to WWW
html_theme_options['extra_nav_links'] = {
    "Main website": 'http://www.fabfile.org',
}

########NEW FILE########
__FILENAME__ = shared_conf
from os.path import join
from datetime import datetime

import alabaster


# Alabaster theme + mini-extension
html_theme_path = [alabaster.get_path()]
extensions = ['alabaster']
# Paths relative to invoking conf.py - not this shared file
html_static_path = [join('..', '_shared_static')]
html_theme = 'alabaster'
html_theme_options = {
    'logo': 'logo.png',
    'logo_name': True,
    'logo_text_align': 'center',
    'description': "Pythonic remote execution",
    'github_user': 'fabric',
    'github_repo': 'fabric',
    'travis_button': True,
    'gittip_user': 'bitprophet',
    'analytics_id': 'UA-18486793-1',

    'link': '#3782BE',
    'link_hover': '#3782BE',
}
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'searchbox.html',
        'donate.html',
    ]
}

# Regular settings
project = 'Fabric'
year = datetime.now().year
copyright = '%d Jeff Forcier' % year
master_doc = 'index'
templates_path = ['_templates']
exclude_trees = ['_build']
source_suffix = '.rst'
default_role = 'obj'

########NEW FILE########
__FILENAME__ = conf
# Obtain shared config values
import sys
import os
from os.path import abspath, join, dirname

sys.path.append(abspath(join(dirname(__file__), '..')))
from shared_conf import *


# Releases changelog extension
extensions.append('releases')
releases_github_path = "fabric/fabric"

# Intersphinx for referencing API/usage docs
extensions.append('sphinx.ext.intersphinx')
# Default is 'local' building, but reference the public docs site when building
# under RTD.
target = join(dirname(__file__), '..', 'docs', '_build')
if os.environ.get('READTHEDOCS') == 'True':
    target = 'http://docs.fabfile.org/en/latest/'
intersphinx_mapping = {
    'docs': (target, None),
}

# Sister-site links to API docs
html_theme_options['extra_nav_links'] = {
    "API Docs": 'http://docs.fabfile.org',
}

########NEW FILE########
__FILENAME__ = tasks
from os.path import join

from invocations import docs as _docs

from invoke import Collection


# TODO: move this & paramiko's copy of same into Alabaster?


d = 'sites'

# Usage doc/API site (published as docs.paramiko.org)
docs_path = join(d, 'docs')
docs_build = join(docs_path, '_build')
docs = Collection.from_module(_docs, name='docs', config={
    'sphinx.source': docs_path,
    'sphinx.target': docs_build,
})

# Main/about/changelog site ((www.)?paramiko.org)
www_path = join(d, 'www')
www = Collection.from_module(_docs, name='www', config={
    'sphinx.source': www_path,
    'sphinx.target': join(www_path, '_build'),
})


ns = Collection(docs=docs, www=www)

########NEW FILE########
__FILENAME__ = fake_filesystem
import os
import stat
from StringIO import StringIO
from types import StringTypes

from fabric.network import ssh


class FakeFile(StringIO):

    def __init__(self, value=None, path=None):
        init = lambda x: StringIO.__init__(self, x)
        if value is None:
            init("")
            ftype = 'dir'
            size = 4096
        else:
            init(value)
            ftype = 'file'
            size = len(value)
        attr = ssh.SFTPAttributes()
        attr.st_mode = {'file': stat.S_IFREG, 'dir': stat.S_IFDIR}[ftype]
        attr.st_size = size
        attr.filename = os.path.basename(path)
        self.attributes = attr

    def __str__(self):
        return self.getvalue()

    def write(self, value):
        StringIO.write(self, value)
        self.attributes.st_size = len(self.getvalue())

    def close(self):
        """
        Always hold fake files open.
        """
        pass

    def __cmp__(self, other):
        me = str(self) if isinstance(other, StringTypes) else self
        return cmp(me, other)


class FakeFilesystem(dict):
    def __init__(self, d=None):
        # Replicate input dictionary using our custom __setitem__
        d = d or {}
        for key, value in d.iteritems():
            self[key] = value

    def __setitem__(self, key, value):
        if isinstance(value, StringTypes) or value is None:
            value = FakeFile(value, key)
        super(FakeFilesystem, self).__setitem__(key, value)

    def normalize(self, path):
        """
        Normalize relative paths.

        In our case, the "home" directory is just the root, /.

        I expect real servers do this as well but with the user's home
        directory.
        """
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        return path

    def __getitem__(self, key):
        return super(FakeFilesystem, self).__getitem__(self.normalize(key))

########NEW FILE########
__FILENAME__ = mock_streams
"""
Stand-alone stream mocking decorator for easier imports.
"""
from functools import wraps
import sys
from StringIO import StringIO  # No need for cStringIO at this time


class CarbonCopy(StringIO):
    """
    A StringIO capable of multiplexing its writes to other buffer objects.
    """

    def __init__(self, buffer='', cc=None):
        """
        If ``cc`` is given and is a file-like object or an iterable of same,
        it/they will be written to whenever this StringIO instance is written
        to.
        """
        StringIO.__init__(self, buffer)
        if cc is None:
            cc = []
        elif hasattr(cc, 'write'):
            cc = [cc]
        self.cc = cc

    def write(self, s):
        StringIO.write(self, s)
        for writer in self.cc:
            writer.write(s)


def mock_streams(which):
    """
    Replaces a stream with a ``StringIO`` during the test, then restores after.

    Must specify which stream (stdout, stderr, etc) via string args, e.g.::

        @mock_streams('stdout')
        def func():
            pass

        @mock_streams('stderr')
        def func():
            pass

        @mock_streams('both')
        def func()
            pass

    If ``'both'`` is specified, not only will both streams be replaced with
    StringIOs, but a new combined-streams output (another StringIO) will appear
    at ``sys.stdall``. This StringIO will resemble what a user sees at a
    terminal, i.e. both streams intermingled.
    """
    both = (which == 'both')
    stdout = (which == 'stdout') or both
    stderr = (which == 'stderr') or both

    def mocked_streams_decorator(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            if both:
                sys.stdall = StringIO()
                fake_stdout = CarbonCopy(cc=sys.stdall)
                fake_stderr = CarbonCopy(cc=sys.stdall)
            else:
                fake_stdout, fake_stderr = StringIO(), StringIO()
            if stdout:
                my_stdout, sys.stdout = sys.stdout, fake_stdout
            if stderr:
                my_stderr, sys.stderr = sys.stderr, fake_stderr
            try:
                ret = func(*args, **kwargs)
            finally:
                if stdout:
                    sys.stdout = my_stdout
                if stderr:
                    sys.stderr = my_stderr
                if both:
                    del sys.stdall
        return inner_wrapper
    return mocked_streams_decorator



########NEW FILE########
__FILENAME__ = Python26SocketServer
"""Generic socket server classes.

This module tries to capture the various aspects of defining a server:

For socket-based servers:

- address family:
        - AF_INET{,6}: IP (Internet Protocol) sockets (default)
        - AF_UNIX: Unix domain sockets
        - others, e.g. AF_DECNET are conceivable (see <socket.h>
- socket type:
        - SOCK_STREAM (reliable stream, e.g. TCP)
        - SOCK_DGRAM (datagrams, e.g. UDP)

For request-based servers (including socket-based):

- client address verification before further looking at the request
        (This is actually a hook for any processing that needs to look
         at the request before anything else, e.g. logging)
- how to handle multiple requests:
        - synchronous (one request is handled at a time)
        - forking (each request is handled by a new process)
        - threading (each request is handled by a new thread)

The classes in this module favor the server type that is simplest to
write: a synchronous TCP/IP server.  This is bad class design, but
save some typing.  (There's also the issue that a deep class hierarchy
slows down method lookups.)

There are five classes in an inheritance diagram, four of which represent
synchronous servers of four types:

        +------------+
        | BaseServer |
        +------------+
              |
              v
        +-----------+        +------------------+
        | TCPServer |------->| UnixStreamServer |
        +-----------+        +------------------+
              |
              v
        +-----------+        +--------------------+
        | UDPServer |------->| UnixDatagramServer |
        +-----------+        +--------------------+

Note that UnixDatagramServer derives from UDPServer, not from
UnixStreamServer -- the only difference between an IP and a Unix
stream server is the address family, which is simply repeated in both
unix server classes.

Forking and threading versions of each type of server can be created
using the ForkingMixIn and ThreadingMixIn mix-in classes.  For
instance, a threading UDP server class is created as follows:

        class ThreadingUDPServer(ThreadingMixIn, UDPServer): pass

The Mix-in class must come first, since it overrides a method defined
in UDPServer! Setting the various member variables also changes
the behavior of the underlying server mechanism.

To implement a service, you must derive a class from
BaseRequestHandler and redefine its handle() method.  You can then run
various versions of the service by combining one of the server classes
with your request handler class.

The request handler class must be different for datagram or stream
services.  This can be hidden by using the request handler
subclasses StreamRequestHandler or DatagramRequestHandler.

Of course, you still have to use your head!

For instance, it makes no sense to use a forking server if the service
contains state in memory that can be modified by requests (since the
modifications in the child process would never reach the initial state
kept in the parent process and passed to each child).  In this case,
you can use a threading server, but you will probably have to use
locks to avoid two requests that come in nearly simultaneous to apply
conflicting changes to the server state.

On the other hand, if you are building e.g. an HTTP server, where all
data is stored externally (e.g. in the file system), a synchronous
class will essentially render the service "deaf" while one request is
being handled -- which may be for a very long time if a client is slow
to reqd all the data it has requested.  Here a threading or forking
server is appropriate.

In some cases, it may be appropriate to process part of a request
synchronously, but to finish processing in a forked child depending on
the request data.  This can be implemented by using a synchronous
server and doing an explicit fork in the request handler class
handle() method.

Another approach to handling multiple simultaneous requests in an
environment that supports neither threads nor fork (or where these are
too expensive or inappropriate for the service) is to maintain an
explicit table of partially finished requests and to use select() to
decide which request to work on next (or whether to handle a new
incoming request).  This is particularly important for stream services
where each client can potentially be connected for a long time (if
threads or subprocesses cannot be used).

Future work:
- Standard classes for Sun RPC (which uses either UDP or TCP)
- Standard mix-in classes to implement various authentication
  and encryption schemes
- Standard framework for select-based multiplexing

XXX Open problems:
- What to do with out-of-band data?

BaseServer:
- split generic "request" functionality out into BaseServer class.
  Copyright (C) 2000  Luke Kenneth Casson Leighton <lkcl@samba.org>

  example: read entries from a SQL database (requires overriding
  get_request() to return a table entry from the database).
  entry is processed by a RequestHandlerClass.

"""

# Author of the BaseServer patch: Luke Kenneth Casson Leighton

# XXX Warning!
# There is a test suite for this module, but it cannot be run by the
# standard regression test.
# To run it manually, run Lib/test/test_socketserver.py.

__version__ = "0.4"

import socket
import select
import sys
import os
try:
    import threading
except ImportError:
    import dummy_threading as threading

__all__ = ["TCPServer", "UDPServer", "ForkingUDPServer", "ForkingTCPServer",
           "ThreadingUDPServer", "ThreadingTCPServer", "BaseRequestHandler",
           "StreamRequestHandler", "DatagramRequestHandler",
           "ThreadingMixIn", "ForkingMixIn"]
if hasattr(socket, "AF_UNIX"):
    __all__.extend(["UnixStreamServer", "UnixDatagramServer",
                    "ThreadingUnixStreamServer",
                    "ThreadingUnixDatagramServer"])


class BaseServer:
    """Base class for server classes.

    Methods for the caller:

    - __init__(server_address, RequestHandlerClass)
    - serve_forever(poll_interval=0.5)
    - shutdown()
    - handle_request()  # if you do not use serve_forever()
    - fileno() -> int   # for select()

    Methods that may be overridden:

    - server_bind()
    - server_activate()
    - get_request() -> request, client_address
    - handle_timeout()
    - verify_request(request, client_address)
    - server_close()
    - process_request(request, client_address)
    - close_request(request)
    - handle_error()

    Methods for derived classes:

    - finish_request(request, client_address)

    Class variables that may be overridden by derived classes or
    instances:

    - timeout
    - address_family
    - socket_type
    - allow_reuse_address

    Instance variables:

    - RequestHandlerClass
    - socket

    """

    timeout = None

    def __init__(self, server_address, RequestHandlerClass):
        """Constructor.  May be extended, do not override."""
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.__is_shut_down = threading.Event()
        self.__serving = False

    def server_activate(self):
        """Called by constructor to activate the server.

        May be overridden.

        """
        pass

    def serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until shutdown.

        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            # XXX: Consider using another file descriptor or
            # connecting to the socket to wake this up instead of
            # polling. Polling reduces our responsiveness to a
            # shutdown request and wastes cpu at all other times.
            r, w, e = select.select([self], [], [], poll_interval)
            if r:
                self._handle_request_noblock()
        self.__is_shut_down.set()

    def shutdown(self):
        """Stops the serve_forever loop.

        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will
        deadlock.
        """
        self.__serving = False
        self.__is_shut_down.wait()

    # The distinction between handling, getting, processing and
    # finishing a request is fairly arbitrary.  Remember:
    #
    # - handle_request() is the top-level call.  It calls
    #   select, get_request(), verify_request() and process_request()
    # - get_request() is different for stream or datagram sockets
    # - process_request() is the place that may fork a new process
    #   or create a new thread to finish the request
    # - finish_request() instantiates the request handler class;
    #   this constructor will handle the request all by itself

    def handle_request(self):
        """Handle one request, possibly blocking.

        Respects self.timeout.
        """
        # Support people who used socket.settimeout() to escape
        # handle_request before self.timeout was available.
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        fd_sets = select.select([self], [], [], timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """Handle one request, without blocking.

        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.close_request(request)

    def handle_timeout(self):
        """Called if no new request arrives within self.timeout.

        Overridden by ForkingMixIn.
        """
        pass

    def verify_request(self, request, client_address):
        """Verify the request.  May be overridden.

        Return True if we should proceed with this request.

        """
        return True

    def process_request(self, request, client_address):
        """Call finish_request.

        Overridden by ForkingMixIn and ThreadingMixIn.

        """
        self.finish_request(request, client_address)
        self.close_request(request)

    def server_close(self):
        """Called to clean-up the server.

        May be overridden.

        """
        pass

    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        self.RequestHandlerClass(request, client_address, self)

    def close_request(self, request):
        """Called to clean up an individual request."""
        pass

    def handle_error(self, request, client_address):
        """Handle an error gracefully.  May be overridden.

        The default is to print a traceback and continue.

        """
        print('-' * 40)
        print('Exception happened during processing of request from %s' % (client_address,))
        import traceback
        traceback.print_exc()  # XXX But this goes to stderr!
        print('-' * 40)


class TCPServer(BaseServer):

    """Base class for various socket-based server classes.

    Defaults to synchronous IP stream (i.e., TCP).

    Methods for the caller:

    - __init__(server_address, RequestHandlerClass, bind_and_activate=True)
    - serve_forever(poll_interval=0.5)
    - shutdown()
    - handle_request()  # if you don't use serve_forever()
    - fileno() -> int   # for select()

    Methods that may be overridden:

    - server_bind()
    - server_activate()
    - get_request() -> request, client_address
    - handle_timeout()
    - verify_request(request, client_address)
    - process_request(request, client_address)
    - close_request(request)
    - handle_error()

    Methods for derived classes:

    - finish_request(request, client_address)

    Class variables that may be overridden by derived classes or
    instances:

    - timeout
    - address_family
    - socket_type
    - request_queue_size (only for stream sockets)
    - allow_reuse_address

    Instance variables:

    - server_address
    - RequestHandlerClass
    - socket

    """

    address_family = socket.AF_INET

    socket_type = socket.SOCK_STREAM

    request_queue_size = 5

    allow_reuse_address = False

    def __init__(self, server_address, RequestHandlerClass,
                 bind_and_activate=True):
        """Constructor.  May be extended, do not override."""
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

    def server_bind(self):
        """Called by constructor to bind the socket.

        May be overridden.

        """
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def server_activate(self):
        """Called by constructor to activate the server.

        May be overridden.

        """
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        """Called to clean-up the server.

        May be overridden.

        """
        self.socket.close()

    def fileno(self):
        """Return socket file number.

        Interface required by select().

        """
        return self.socket.fileno()

    def get_request(self):
        """Get the request and client address from the socket.

        May be overridden.

        """
        return self.socket.accept()

    def close_request(self, request):
        """Called to clean up an individual request."""
        request.close()


class UDPServer(TCPServer):

    """UDP server class."""

    allow_reuse_address = False

    socket_type = socket.SOCK_DGRAM

    max_packet_size = 8192

    def get_request(self):
        data, client_addr = self.socket.recvfrom(self.max_packet_size)
        return (data, self.socket), client_addr

    def server_activate(self):
        # No need to call listen() for UDP.
        pass

    def close_request(self, request):
        # No need to close anything.
        pass


class ForkingMixIn:
    """Mix-in class to handle each request in a new process."""

    timeout = 300
    active_children = None
    max_children = 40

    def collect_children(self):
        """Internal routine to wait for children that have exited."""
        if self.active_children is None:
            return
        while len(self.active_children) >= self.max_children:
            # XXX: This will wait for any child process, not just ones
            # spawned by this library. This could confuse other
            # libraries that expect to be able to wait for their own
            # children.
            try:
                pid, status = os.waitpid(0, 0)
            except os.error:
                pid = None
            if pid not in self.active_children:
                continue
            self.active_children.remove(pid)

        # XXX: This loop runs more system calls than it ought
        # to. There should be a way to put the active_children into a
        # process group and then use os.waitpid(-pgid) to wait for any
        # of that set, but I couldn't find a way to allocate pgids
        # that couldn't collide.
        for child in self.active_children:
            try:
                pid, status = os.waitpid(child, os.WNOHANG)
            except os.error:
                pid = None
            if not pid:
                continue
            try:
                self.active_children.remove(pid)
            except ValueError, e:
                raise ValueError('%s. x=%d and list=%r' % \
                                    (e.message, pid, self.active_children))

    def handle_timeout(self):
        """Wait for zombies after self.timeout seconds of inactivity.

        May be extended, do not override.
        """
        self.collect_children()

    def process_request(self, request, client_address):
        """Fork a new subprocess to process the request."""
        self.collect_children()
        pid = os.fork()
        if pid:
            # Parent process
            if self.active_children is None:
                self.active_children = []
            self.active_children.append(pid)
            self.close_request(request)
            return
        else:
            # Child process.
            # This must never return, hence os._exit()!
            try:
                self.finish_request(request, client_address)
                os._exit(0)
            except:
                try:
                    self.handle_error(request, client_address)
                finally:
                    os._exit(1)


class ThreadingMixIn:
    """Mix-in class to handle each request in a new thread."""

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.

        In addition, exception handling is done here.

        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address))
        if self.daemon_threads:
            t.setDaemon(1)
        t.start()


class ForkingUDPServer(ForkingMixIn, UDPServer):
    pass


class ForkingTCPServer(ForkingMixIn, TCPServer):
    pass


class ThreadingUDPServer(ThreadingMixIn, UDPServer):
    pass


class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    pass


if hasattr(socket, 'AF_UNIX'):

    class UnixStreamServer(TCPServer):
        address_family = socket.AF_UNIX

    class UnixDatagramServer(UDPServer):
        address_family = socket.AF_UNIX

    class ThreadingUnixStreamServer(ThreadingMixIn, UnixStreamServer):
        pass

    class ThreadingUnixDatagramServer(ThreadingMixIn, UnixDatagramServer):
        pass


class BaseRequestHandler:

    """Base class for request handler classes.

    This class is instantiated for each request to be handled.  The
    constructor sets the instance variables request, client_address
    and server, and then calls the handle() method.  To implement a
    specific service, all you need to do is to derive a class which
    defines a handle() method.

    The handle() method can find the request as self.request, the
    client address as self.client_address, and the server (in case it
    needs access to per-server information) as self.server.  Since a
    separate instance is created for each request, the handle() method
    can define arbitrary other instance variariables.

    """

    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        try:
            self.setup()
            self.handle()
            self.finish()
        finally:
            sys.exc_traceback = None    # Help garbage collection

    def setup(self):
        pass

    def handle(self):
        pass

    def finish(self):
        pass


# The following two classes make it possible to use the same service
# class for stream or datagram servers.
# Each class sets up these instance variables:
# - rfile: a file object from which receives the request is read
# - wfile: a file object to which the reply is written
# When the handle() method returns, wfile is flushed properly


class StreamRequestHandler(BaseRequestHandler):

    """Define self.rfile and self.wfile for stream sockets."""

    # Default buffer sizes for rfile, wfile.
    # We default rfile to buffered because otherwise it could be
    # really slow for large data (a getc() call per byte); we make
    # wfile unbuffered because (a) often after a write() we want to
    # read and we need to flush the line; (b) big writes to unbuffered
    # files are typically optimized by stdio even when big reads
    # aren't.
    rbufsize = -1
    wbufsize = 0

    def setup(self):
        self.connection = self.request
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)

    def finish(self):
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()


class DatagramRequestHandler(BaseRequestHandler):

    # XXX Regrettably, I cannot get this working on Linux;
    # s.recvfrom() doesn't return a meaningful client address.

    """Define self.rfile and self.wfile for datagram sockets."""

    def setup(self):
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        self.packet, self.socket = self.request
        self.rfile = StringIO(self.packet)
        self.wfile = StringIO()

    def finish(self):
        self.socket.sendto(self.wfile.getvalue(), self.client_address)

########NEW FILE########
__FILENAME__ = server
from __future__ import with_statement

import copy
import itertools
import os
import re
import socket
import stat
import sys
import threading
import time
import types
from StringIO import StringIO
from functools import wraps
from Python26SocketServer import BaseRequestHandler, ThreadingMixIn, TCPServer

from fabric.operations import _sudo_prefix
from fabric.api import env, hide
from fabric.thread_handling import ThreadHandler
from fabric.network import disconnect_all, ssh

from fake_filesystem import FakeFilesystem, FakeFile

#
# Debugging
#

import logging
logging.basicConfig(filename='/tmp/fab.log', level=logging.DEBUG)
logger = logging.getLogger('server.py')


#
# Constants
#

HOST = '127.0.0.1'
PORT = 2200
USER = 'username'
HOME = '/'
RESPONSES = {
    "ls /simple": "some output",
    "ls /": """AUTHORS
FAQ
Fabric.egg-info
INSTALL
LICENSE
MANIFEST
README
build
docs
fabfile.py
fabfile.pyc
fabric
requirements.txt
setup.py
tests""",
    "both_streams": [
        "stdout",
        "stderr"
    ],
}
FILES = FakeFilesystem({
    '/file.txt': 'contents',
    '/file2.txt': 'contents2',
    '/folder/file3.txt': 'contents3',
    '/empty_folder': None,
    '/tree/file1.txt': 'x',
    '/tree/file2.txt': 'y',
    '/tree/subfolder/file3.txt': 'z',
    '/etc/apache2/apache2.conf': 'Include other.conf',
    HOME: None  # So $HOME is a directory
})
PASSWORDS = {
    'root': 'root',
    USER: 'password'
}


def _local_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)

SERVER_PRIVKEY = _local_file('private.key')
CLIENT_PUBKEY = _local_file('client.key.pub')
CLIENT_PRIVKEY = _local_file('client.key')
CLIENT_PRIVKEY_PASSPHRASE = "passphrase"


def _equalize(lists, fillval=None):
    """
    Pad all given list items in ``lists`` to be the same length.
    """
    lists = map(list, lists)
    upper = max(len(x) for x in lists)
    for lst in lists:
        diff = upper - len(lst)
        if diff:
            lst.extend([fillval] * diff)
    return lists


class TestServer(ssh.ServerInterface):
    """
    Test server implementing the 'ssh' lib's server interface parent class.

    Mostly just handles the bare minimum necessary to handle SSH-level things
    such as honoring authentication types and exec/shell/etc requests.

    The bulk of the actual server side logic is handled in the
    ``serve_responses`` function and its ``SSHHandler`` class.
    """
    def __init__(self, passwords, home, pubkeys, files):
        self.event = threading.Event()
        self.passwords = passwords
        self.pubkeys = pubkeys
        self.files = FakeFilesystem(files)
        self.home = home
        self.command = None

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return ssh.OPEN_SUCCEEDED
        return ssh.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        self.command = command
        self.event.set()
        return True

    def check_channel_pty_request(self, *args):
        return True

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_auth_password(self, username, password):
        self.username = username
        passed = self.passwords.get(username) == password
        return ssh.AUTH_SUCCESSFUL if passed else ssh.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        self.username = username
        return ssh.AUTH_SUCCESSFUL if self.pubkeys else ssh.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'


class SSHServer(ThreadingMixIn, TCPServer):
    """
    Threading TCPServer subclass.
    """
    def _socket_info(self, addr_tup):
        """
        Clone of the very top of Paramiko 1.7.6 SSHClient.connect().

        We must use this in order to make sure that our address family matches
        up with the client side (which we cannot control, and which varies
        depending on individual computers and their network settings).
        """
        hostname, port = addr_tup
        addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC,
            socket.SOCK_STREAM)
        for (family, socktype, proto, canonname, sockaddr) in addr_info:
            if socktype == socket.SOCK_STREAM:
                af = family
                addr = sockaddr
                break
        else:
            # some OS like AIX don't indicate SOCK_STREAM support, so just
            # guess. :(
            af, _, _, _, addr = socket.getaddrinfo(hostname, port,
                socket.AF_UNSPEC, socket.SOCK_STREAM)
        return af, addr

    def __init__(
        self, server_address, RequestHandlerClass, bind_and_activate=True
    ):
        # Prevent "address already in use" errors when running tests 2x in a
        # row.
        self.allow_reuse_address = True

        # Handle network family/host addr (see docstring for _socket_info)
        family, addr = self._socket_info(server_address)
        self.address_family = family
        TCPServer.__init__(self, addr, RequestHandlerClass,
            bind_and_activate)


class FakeSFTPHandle(ssh.SFTPHandle):
    """
    Extremely basic way to get SFTPHandle working with our fake setup.
    """
    def chattr(self, attr):
        self.readfile.attributes = attr
        return ssh.SFTP_OK

    def stat(self):
        return self.readfile.attributes


class PrependList(list):
    def prepend(self, val):
        self.insert(0, val)


def expand(path):
    """
    '/foo/bar/biz' => ('/', 'foo', 'bar', 'biz')
    'relative/path' => ('relative', 'path')
    """
    # Base case
    if path in ['', os.path.sep]:
        return [path]
    ret = PrependList()
    directory, filename = os.path.split(path)
    while directory and directory != os.path.sep:
        ret.prepend(filename)
        directory, filename = os.path.split(directory)
    ret.prepend(filename)
    # Handle absolute vs relative paths
    ret.prepend(directory if directory == os.path.sep else '')
    return ret


def contains(folder, path):
    """
    contains(('a', 'b', 'c'), ('a', 'b')) => True
    contains('a', 'b', 'c'), ('f',)) => False
    """
    return False if len(path) >= len(folder) else folder[:len(path)] == path


def missing_folders(paths):
    """
    missing_folders(['a/b/c']) => ['a', 'a/b', 'a/b/c']
    """
    ret = []
    pool = set(paths)
    for path in paths:
        expanded = expand(path)
        for i in range(len(expanded)):
            folder = os.path.join(*expanded[:len(expanded) - i])
            if folder and folder not in pool:
                pool.add(folder)
                ret.append(folder)
    return ret


def canonicalize(path, home):
    ret = path
    if not os.path.isabs(path):
        ret = os.path.normpath(os.path.join(home, path))
    return ret


class FakeSFTPServer(ssh.SFTPServerInterface):
    def __init__(self, server, *args, **kwargs):
        self.server = server
        files = self.server.files
        # Expand such that omitted, implied folders get added explicitly
        for folder in missing_folders(files.keys()):
            files[folder] = None
        self.files = files

    def canonicalize(self, path):
        """
        Make non-absolute paths relative to $HOME.
        """
        return canonicalize(path, self.server.home)

    def list_folder(self, path):
        path = self.files.normalize(path)
        expanded_files = map(expand, self.files)
        expanded_path = expand(path)
        candidates = [x for x in expanded_files if contains(x, expanded_path)]
        children = []
        for candidate in candidates:
            cut = candidate[:len(expanded_path) + 1]
            if cut not in children:
                children.append(cut)
        results = [self.stat(os.path.join(*x)) for x in children]
        bad = not results or any(x == ssh.SFTP_NO_SUCH_FILE for x in results)
        return ssh.SFTP_NO_SUCH_FILE if bad else results

    def open(self, path, flags, attr):
        path = self.files.normalize(path)
        try:
            fobj = self.files[path]
        except KeyError:
            if flags & os.O_WRONLY:
                # Only allow writes to files in existing directories.
                if os.path.dirname(path) not in self.files:
                    return ssh.SFTP_NO_SUCH_FILE
                self.files[path] = fobj = FakeFile("", path)
            # No write flag means a read, which means they tried to read a
            # nonexistent file.
            else:
                return ssh.SFTP_NO_SUCH_FILE
        f = FakeSFTPHandle()
        f.readfile = f.writefile = fobj
        return f

    def stat(self, path):
        path = self.files.normalize(path)
        try:
            fobj = self.files[path]
        except KeyError:
            return ssh.SFTP_NO_SUCH_FILE
        return fobj.attributes

    # Don't care about links right now
    lstat = stat

    def chattr(self, path, attr):
        path = self.files.normalize(path)
        if path not in self.files:
            return ssh.SFTP_NO_SUCH_FILE
        # Attempt to gracefully update instead of overwrite, since things like
        # chmod will call us with an SFTPAttributes object that only exhibits
        # e.g. st_mode, and we don't want to lose our filename or size...
        for which in "size uid gid mode atime mtime".split():
            attname = "st_" + which
            incoming = getattr(attr, attname)
            if incoming is not None:
                setattr(self.files[path].attributes, attname, incoming)
        return ssh.SFTP_OK

    def mkdir(self, path, attr):
        self.files[path] = None
        return ssh.SFTP_OK


def serve_responses(responses, files, passwords, home, pubkeys, port):
    """
    Return a threading TCP based SocketServer listening on ``port``.

    Used as a fake SSH server which will respond to commands given in
    ``responses`` and allow connections for users listed in ``passwords``.
    ``home`` is used as the remote $HOME (mostly for SFTP purposes).

    ``pubkeys`` is a Boolean value determining whether the server will allow
    pubkey auth or not.
    """
    # Define handler class inline so it can access serve_responses' args
    class SSHHandler(BaseRequestHandler):
        def handle(self):
            try:
                self.init_transport()
                self.waiting_for_command = False
                while not self.server.all_done.isSet():
                    # Don't overwrite channel if we're waiting for a command.
                    if not self.waiting_for_command:
                        self.channel = self.transport.accept(1)
                        if not self.channel:
                            continue
                    self.ssh_server.event.wait(10)
                    if self.ssh_server.command:
                        self.command = self.ssh_server.command
                        # Set self.sudo_prompt, update self.command
                        self.split_sudo_prompt()
                        if self.command in responses:
                            self.stdout, self.stderr, self.status = \
                                self.response()
                            if self.sudo_prompt and not self.sudo_password():
                                self.channel.send(
                                    "sudo: 3 incorrect password attempts\n"
                                )
                                break
                            self.respond()
                        else:
                            self.channel.send_stderr(
                                "Sorry, I don't recognize that command.\n"
                            )
                            self.channel.send_exit_status(1)
                        # Close up shop
                        self.command = self.ssh_server.command = None
                        self.waiting_for_command = False
                        time.sleep(0.5)
                        self.channel.close()
                    else:
                        # If we're here, self.command was False or None,
                        # but we do have a valid Channel object. Thus we're
                        # waiting for the command to show up.
                        self.waiting_for_command = True

            finally:
                self.transport.close()

        def init_transport(self):
            transport = ssh.Transport(self.request)
            transport.add_server_key(ssh.RSAKey(filename=SERVER_PRIVKEY))
            transport.set_subsystem_handler('sftp', ssh.SFTPServer,
                sftp_si=FakeSFTPServer)
            server = TestServer(passwords, home, pubkeys, files)
            transport.start_server(server=server)
            self.ssh_server = server
            self.transport = transport

        def split_sudo_prompt(self):
            prefix = re.escape(_sudo_prefix(None, None).rstrip()) + ' +'
            result = re.findall(r'^(%s)?(.*)$' % prefix, self.command)[0]
            self.sudo_prompt, self.command = result

        def response(self):
            result = responses[self.command]
            stderr = ""
            status = 0
            sleep = 0
            if isinstance(result, types.StringTypes):
                stdout = result
            else:
                size = len(result)
                if size == 1:
                    stdout = result[0]
                elif size == 2:
                    stdout, stderr = result
                elif size == 3:
                    stdout, stderr, status = result
                elif size == 4:
                    stdout, stderr, status, sleep = result
            stdout, stderr = _equalize((stdout, stderr))
            time.sleep(sleep)
            return stdout, stderr, status

        def sudo_password(self):
            # Give user 3 tries, as is typical
            passed = False
            for x in range(3):
                self.channel.send(env.sudo_prompt)
                password = self.channel.recv(65535).strip()
                # Spit back newline to fake the echo of user's
                # newline
                self.channel.send('\n')
                # Test password
                if password == passwords[self.ssh_server.username]:
                    passed = True
                    break
                # If here, password was bad.
                self.channel.send("Sorry, try again.\n")
            return passed

        def respond(self):
            for out, err in zip(self.stdout, self.stderr):
                if out is not None:
                    self.channel.send(out)
                if err is not None:
                    self.channel.send_stderr(err)
            self.channel.send_exit_status(self.status)

    return SSHServer((HOST, port), SSHHandler)


def server(
        responses=RESPONSES,
        files=FILES,
        passwords=PASSWORDS,
        home=HOME,
        pubkeys=False,
        port=PORT
    ):
    """
    Returns a decorator that runs an SSH server during function execution.

    Direct passthrough to ``serve_responses``.
    """
    def run_server(func):
        @wraps(func)
        def inner(*args, **kwargs):
            # Start server
            _server = serve_responses(responses, files, passwords, home,
                pubkeys, port)
            _server.all_done = threading.Event()
            worker = ThreadHandler('server', _server.serve_forever)
            # Execute function
            try:
                return func(*args, **kwargs)
            finally:
                # Clean up client side connections
                with hide('status'):
                    disconnect_all()
                # Stop server
                _server.all_done.set()
                _server.shutdown()
                # Why this is not called in shutdown() is beyond me.
                _server.server_close()
                worker.thread.join()
                # Handle subthread exceptions
                e = worker.exception
                if e:
                    raise e[0], e[1], e[2]
        return inner
    return run_server

########NEW FILE########
__FILENAME__ = classbased_task_fabfile
from fabric import tasks

class ClassBasedTask(tasks.Task):
    def run(self, *args, **kwargs):
        pass

foo = ClassBasedTask()

########NEW FILE########
__FILENAME__ = decorated_fabfile
from fabric.decorators import task

@task
def foo():
    pass

def bar():
    pass

########NEW FILE########
__FILENAME__ = decorated_fabfile_with_classbased_task
from fabric import tasks
from fabric.decorators import task

class ClassBasedTask(tasks.Task):
    def __init__(self):
        self.name = "foo"
        self.use_decorated = True

    def run(self, *args, **kwargs):
        pass

foo = ClassBasedTask()

########NEW FILE########
__FILENAME__ = decorated_fabfile_with_modules
from fabric.decorators import task
import module_fabtasks as tasks

@task
def foo():
    pass

def bar():
    pass

########NEW FILE########
__FILENAME__ = decorator_order
from fabric.api import task, hosts, roles


@hosts('whatever')
@task
def foo():
    pass

# There must be at least one unmolested new-style task for the decorator order
# problem to appear.
@task
def caller():
    pass

########NEW FILE########
__FILENAME__ = deep
import submodule

########NEW FILE########
__FILENAME__ = default_tasks
import default_task_submodule as mymodule

########NEW FILE########
__FILENAME__ = default_task_submodule
from fabric.api import task

@task(default=True)
def long_task_name():
    pass

########NEW FILE########
__FILENAME__ = docstring
from fabric.decorators import task

@task
def foo():
    """
    Foos!
    """
    pass

########NEW FILE########
__FILENAME__ = explicit_fabfile
__all__ = ['foo']

def foo():
    pass

def bar():
    pass

########NEW FILE########
__FILENAME__ = flat_alias
from fabric.api import task

@task(alias="foo_aliased")
def foo():
    pass

########NEW FILE########
__FILENAME__ = flat_aliases
from fabric.api import task

@task(aliases=["foo_aliased", "foo_aliased_two"])
def foo():
    pass

########NEW FILE########
__FILENAME__ = implicit_fabfile
def foo():
    pass

def bar():
    pass

########NEW FILE########
__FILENAME__ = mapping
from fabric.tasks import Task

class MappingTask(dict, Task):
    def run(self):
        pass

mapping_task = MappingTask()
mapping_task.name = "mapping_task"

########NEW FILE########
__FILENAME__ = module_fabtasks
def hello():
    print("hello")


def world():
    print("world")

########NEW FILE########
__FILENAME__ = nested_alias
import flat_alias as nested

########NEW FILE########
__FILENAME__ = nested_aliases
import flat_aliases as nested

########NEW FILE########
__FILENAME__ = db
from fabric.api import task


@task
def migrate():
    pass

########NEW FILE########
__FILENAME__ = debian
from fabric.api import task


@task
def update_apt():
    pass

########NEW FILE########
__FILENAME__ = test_context_managers
from __future__ import with_statement

import os
import sys
from StringIO import StringIO

from nose.tools import eq_, ok_

from fabric.state import env, output
from fabric.context_managers import (cd, settings, lcd, hide, shell_env, quiet,
    warn_only, prefix, path)
from fabric.operations import run, local
from utils import mock_streams, FabricTest
from server import server


#
# cd()
#

def test_error_handling():
    """
    cd cleans up after itself even in case of an exception
    """

    class TestException(Exception):
        pass

    try:
        with cd('somewhere'):
            raise TestException('Houston, we have a problem.')
    except TestException:
        pass
    finally:
        with cd('else'):
            eq_(env.cwd, 'else')


def test_cwd_with_absolute_paths():
    """
    cd() should append arg if non-absolute or overwrite otherwise
    """
    existing = '/some/existing/path'
    additional = 'another'
    absolute = '/absolute/path'
    with settings(cwd=existing):
        with cd(absolute):
            eq_(env.cwd, absolute)
        with cd(additional):
            eq_(env.cwd, existing + '/' + additional)


def test_cd_home_dir():
    """
    cd() should work with home directories
    """
    homepath = "~/somepath"
    with cd(homepath):
        eq_(env.cwd, homepath)


def test_cd_nested_home_abs_dirs():
    """
    cd() should work with nested user homedir (starting with ~) paths.

    It should always take the last path if the new path begins with `/` or `~`
    """

    home_path = "~/somepath"
    abs_path = "/some/random/path"
    relative_path = "some/random/path"

    # 2 nested homedir paths
    with cd(home_path):
        eq_(env.cwd, home_path)
        another_path = home_path + "/another/path"
        with cd(another_path):
            eq_(env.cwd, another_path)

    # first absolute path, then a homedir path
    with cd(abs_path):
        eq_(env.cwd, abs_path)
        with cd(home_path):
            eq_(env.cwd, home_path)

    # first relative path, then a homedir path
    with cd(relative_path):
        eq_(env.cwd, relative_path)
        with cd(home_path):
            eq_(env.cwd, home_path)

    # first home path, then a a relative path
    with cd(home_path):
        eq_(env.cwd, home_path)
        with cd(relative_path):
            eq_(env.cwd, home_path + "/" + relative_path)


#
#  prefix
#

def test_nested_prefix():
    """
    prefix context managers can be created outside of the with block and nested
    """
    cm1 = prefix('1')
    cm2 = prefix('2')
    with cm1:
        with cm2:
            eq_(env.command_prefixes, ['1', '2'])


#
# hide/show
#

def test_hide_show_exception_handling():
    """
    hide()/show() should clean up OK if exceptions are raised
    """
    try:
        with hide('stderr'):
            # now it's False, while the default is True
            eq_(output.stderr, False)
            raise Exception
    except Exception:
        # Here it should be True again.
        # If it's False, this means hide() didn't clean up OK.
        eq_(output.stderr, True)


#
# settings()
#

def test_setting_new_env_dict_key_should_work():
    """
    Using settings() with a previously nonexistent key should work correctly
    """
    key = 'thisshouldnevereverexistseriouslynow'
    value = 'a winner is you'
    with settings(**{key: value}):
        ok_(key in env)
    ok_(key not in env)


def test_settings():
    """
    settings() should temporarily override env dict with given key/value pair
    """
    env.testval = "outer value"
    with settings(testval="inner value"):
        eq_(env.testval, "inner value")
    eq_(env.testval, "outer value")


def test_settings_with_multiple_kwargs():
    """
    settings() should temporarily override env dict with given key/value pairS
    """
    env.testval1 = "outer 1"
    env.testval2 = "outer 2"
    with settings(testval1="inner 1", testval2="inner 2"):
        eq_(env.testval1, "inner 1")
        eq_(env.testval2, "inner 2")
    eq_(env.testval1, "outer 1")
    eq_(env.testval2, "outer 2")


def test_settings_with_other_context_managers():
    """
    settings() should take other context managers, and use them with other overrided
    key/value pairs.
    """
    env.testval1 = "outer 1"
    prev_lcwd = env.lcwd

    with settings(lcd("here"), testval1="inner 1"):
        eq_(env.testval1, "inner 1")
        ok_(env.lcwd.endswith("here")) # Should be the side-effect of adding cd to settings

    ok_(env.testval1, "outer 1")
    eq_(env.lcwd, prev_lcwd)


def test_settings_clean_revert():
    """
    settings(clean_revert=True) should only revert values matching input values
    """
    env.modified = "outer"
    env.notmodified = "outer"
    with settings(
        modified="inner",
        notmodified="inner",
        inner_only="only",
        clean_revert=True
    ):
        eq_(env.modified, "inner")
        eq_(env.notmodified, "inner")
        eq_(env.inner_only, "only")
        env.modified = "modified internally"
    eq_(env.modified, "modified internally")
    ok_("inner_only" not in env)


#
# shell_env()
#

def test_shell_env():
    """
    shell_env() sets the shell_env attribute in the env dict
    """
    with shell_env(KEY="value"):
        eq_(env.shell_env['KEY'], 'value')

    eq_(env.shell_env, {})


class TestQuietAndWarnOnly(FabricTest):
    @server()
    @mock_streams('both')
    def test_quiet_hides_all_output(self):
        # Sanity test - normally this is not empty
        run("ls /simple")
        ok_(sys.stdout.getvalue())
        # Reset
        sys.stdout = StringIO()
        # Real test
        with quiet():
            run("ls /simple")
        # Empty output
        ok_(not sys.stdout.getvalue())
        # Reset
        sys.stdout = StringIO()
        # Kwarg test
        run("ls /simple", quiet=True)
        ok_(not sys.stdout.getvalue())

    @server(responses={'barf': [
        "this is my stdout",
        "this is my stderr",
        1
    ]})
    def test_quiet_sets_warn_only_to_true(self):
        # Sanity test to ensure environment
        with settings(warn_only=False):
            with quiet():
                eq_(run("barf").return_code, 1)
            # Kwarg test
            eq_(run("barf", quiet=True).return_code, 1)

    @server(responses={'hrm': ["", "", 1]})
    @mock_streams('both')
    def test_warn_only_is_same_as_settings_warn_only(self):
        with warn_only():
            eq_(run("hrm").failed, True)

    @server()
    @mock_streams('both')
    def test_warn_only_does_not_imply_hide_everything(self):
        with warn_only():
            run("ls /simple")
            assert sys.stdout.getvalue().strip() != ""


# path() (distinct from shell_env)

class TestPathManager(FabricTest):
    def setup(self):
        super(TestPathManager, self).setup()
        self.real = os.environ.get('PATH')

    def via_local(self):
        with hide('everything'):
            return local("echo $PATH", capture=True)

    def test_lack_of_path_has_default_local_path(self):
        """
        No use of 'with path' == default local $PATH
        """
        eq_(self.real, self.via_local())

    def test_use_of_path_appends_by_default(self):
        """
        'with path' appends by default
        """
        with path('foo'):
            eq_(self.via_local(), self.real + ":foo")

########NEW FILE########
__FILENAME__ = test_contrib
# -*- coding: utf-8 -*-
from __future__ import with_statement

import os

from fabric.api import hide, get, show
from fabric.contrib.files import upload_template, contains

from utils import FabricTest, eq_contents
from server import server


class TestContrib(FabricTest):
    # Make sure it knows / is a directory.
    # This is in lieu of starting down the "actual honest to god fake operating
    # system" road...:(
    @server(responses={'test -d "$(echo /)"': ""})
    def test_upload_template_uses_correct_remote_filename(self):
        """
        upload_template() shouldn't munge final remote filename
        """
        template = self.mkfile('template.txt', 'text')
        with hide('everything'):
            upload_template(template, '/')
            assert self.exists_remotely('/template.txt')

    @server()
    def test_upload_template_handles_file_destination(self):
        """
        upload_template() should work OK with file and directory destinations
        """
        template = self.mkfile('template.txt', '%(varname)s')
        local = self.path('result.txt')
        remote = '/configfile.txt'
        var = 'foobar'
        with hide('everything'):
            upload_template(template, remote, {'varname': var})
            get(remote, local)
        eq_contents(local, var)

    @server(responses={
        'egrep "text" "/file.txt"': (
            "sudo: unable to resolve host fabric",
            "",
            1
        )}
    )
    def test_contains_checks_only_succeeded_flag(self):
        """
        contains() should return False on bad grep even if stdout isn't empty
        """
        with hide('everything'):
            result = contains('/file.txt', 'text', use_sudo=True)
            assert result == False

    @server()
    def test_upload_template_handles_jinja_template(self):
        """
        upload_template() should work OK with Jinja2 template
        """
        template = self.mkfile('template_jinja2.txt', '{{ first_name }}')
        template_name = os.path.basename(template)
        template_dir = os.path.dirname(template)
        local = self.path('result.txt')
        remote = '/configfile.txt'
        first_name = u'S\u00E9bastien'
        with hide('everything'):
            upload_template(template_name, remote, {'first_name': first_name},
                use_jinja=True, template_dir=template_dir)
            get(remote, local)
        eq_contents(local, first_name.encode('utf-8'))

    @server()
    def test_upload_template_jinja_and_no_template_dir(self):
        # Crummy doesn't-die test
        fname = "foo.tpl"
        try:
            with hide('everything'):
                with open(fname, 'w+') as fd:
                    fd.write('whatever')
                upload_template(fname, '/configfile.txt', {}, use_jinja=True)
        finally:
            os.remove(fname)

########NEW FILE########
__FILENAME__ = test_decorators
from __future__ import with_statement

import random
import sys

from nose.tools import eq_, ok_, assert_true, assert_false, assert_equal
import fudge
from fudge import Fake, with_fakes, patched_context

from fabric import decorators, tasks
from fabric.state import env
import fabric # for patching fabric.state.xxx
from fabric.tasks import _parallel_tasks, requires_parallel, execute
from fabric.context_managers import lcd, settings, hide

from utils import mock_streams


#
# Support
#

def fake_function(*args, **kwargs):
    """
    Returns a ``fudge.Fake`` exhibiting function-like attributes.

    Passes in all args/kwargs to the ``fudge.Fake`` constructor. However, if
    ``callable`` or ``expect_call`` kwargs are not given, ``callable`` will be
    set to True by default.
    """
    # Must define __name__ to be compatible with function wrapping mechanisms
    # like @wraps().
    if 'callable' not in kwargs and 'expect_call' not in kwargs:
        kwargs['callable'] = True
    return Fake(*args, **kwargs).has_attr(__name__='fake')



#
# @task
#

def test_task_returns_an_instance_of_wrappedfunctask_object():
    def foo():
        pass
    task = decorators.task(foo)
    ok_(isinstance(task, tasks.WrappedCallableTask))


def test_task_will_invoke_provided_class():
    def foo(): pass
    fake = Fake()
    fake.expects("__init__").with_args(foo)
    fudge.clear_calls()
    fudge.clear_expectations()

    foo = decorators.task(foo, task_class=fake)

    fudge.verify()


def test_task_passes_args_to_the_task_class():
    random_vars = ("some text", random.randint(100, 200))
    def foo(): pass

    fake = Fake()
    fake.expects("__init__").with_args(foo, *random_vars)
    fudge.clear_calls()
    fudge.clear_expectations()

    foo = decorators.task(foo, task_class=fake, *random_vars)
    fudge.verify()


def test_passes_kwargs_to_the_task_class():
    random_vars = {
        "msg": "some text",
        "number": random.randint(100, 200),
    }
    def foo(): pass

    fake = Fake()
    fake.expects("__init__").with_args(foo, **random_vars)
    fudge.clear_calls()
    fudge.clear_expectations()

    foo = decorators.task(foo, task_class=fake, **random_vars)
    fudge.verify()


def test_integration_tests_for_invoked_decorator_with_no_args():
    r = random.randint(100, 200)
    @decorators.task()
    def foo():
        return r

    eq_(r, foo())


def test_integration_tests_for_decorator():
    r = random.randint(100, 200)
    @decorators.task(task_class=tasks.WrappedCallableTask)
    def foo():
        return r

    eq_(r, foo())


def test_original_non_invoked_style_task():
    r = random.randint(100, 200)
    @decorators.task
    def foo():
        return r

    eq_(r, foo())



#
# @runs_once
#

@with_fakes
def test_runs_once_runs_only_once():
    """
    @runs_once prevents decorated func from running >1 time
    """
    func = fake_function(expect_call=True).times_called(1)
    task = decorators.runs_once(func)
    for i in range(2):
        task()


def test_runs_once_returns_same_value_each_run():
    """
    @runs_once memoizes return value of decorated func
    """
    return_value = "foo"
    task = decorators.runs_once(fake_function().returns(return_value))
    for i in range(2):
        eq_(task(), return_value)


@decorators.runs_once
def single_run():
    pass

def test_runs_once():
    assert_false(hasattr(single_run, 'return_value'))
    single_run()
    assert_true(hasattr(single_run, 'return_value'))
    assert_equal(None, single_run())



#
# @serial / @parallel
#


@decorators.serial
def serial():
    pass

@decorators.serial
@decorators.parallel
def serial2():
    pass

@decorators.parallel
@decorators.serial
def serial3():
    pass

@decorators.parallel
def parallel():
    pass

@decorators.parallel(pool_size=20)
def parallel2():
    pass

fake_tasks = {
    'serial': serial,
    'serial2': serial2,
    'serial3': serial3,
    'parallel': parallel,
    'parallel2': parallel2,
}

def parallel_task_helper(actual_tasks, expected):
    commands_to_run = map(lambda x: [x], actual_tasks)
    with patched_context(fabric.state, 'commands', fake_tasks):
        eq_(_parallel_tasks(commands_to_run), expected)

def test_parallel_tasks():
    for desc, task_names, expected in (
        ("One @serial-decorated task == no parallelism",
            ['serial'], False),
        ("One @parallel-decorated task == parallelism",
            ['parallel'], True),
        ("One @parallel-decorated and one @serial-decorated task == paralellism",
            ['parallel', 'serial'], True),
        ("Tasks decorated with both @serial and @parallel count as @parallel",
            ['serial2', 'serial3'], True)
    ):
        parallel_task_helper.description = desc
        yield parallel_task_helper, task_names, expected
        del parallel_task_helper.description

def test_parallel_wins_vs_serial():
    """
    @parallel takes precedence over @serial when both are used on one task
    """
    ok_(requires_parallel(serial2))
    ok_(requires_parallel(serial3))

@mock_streams('stdout')
def test_global_parallel_honors_runs_once():
    """
    fab -P (or env.parallel) should honor @runs_once
    """
    @decorators.runs_once
    def mytask():
        print("yolo") # 'Carpe diem' for stupid people!
    with settings(hide('everything'), parallel=True):
        execute(mytask, hosts=['localhost', '127.0.0.1'])
    result = sys.stdout.getvalue()
    eq_(result, "yolo\n")
    assert result != "yolo\nyolo\n"


#
# @roles
#

@decorators.roles('test')
def use_roles():
    pass

def test_roles():
    assert_true(hasattr(use_roles, 'roles'))
    assert_equal(use_roles.roles, ['test'])



#
# @hosts
#

@decorators.hosts('test')
def use_hosts():
    pass

def test_hosts():
    assert_true(hasattr(use_hosts, 'hosts'))
    assert_equal(use_hosts.hosts, ['test'])



#
# @with_settings
#

def test_with_settings_passes_env_vars_into_decorated_function():
    env.value = True
    random_return = random.randint(1000, 2000)
    def some_task():
        return env.value
    decorated_task = decorators.with_settings(value=random_return)(some_task)
    ok_(some_task(), msg="sanity check")
    eq_(random_return, decorated_task())

def test_with_settings_with_other_context_managers():
    """
    with_settings() should take other context managers, and use them with other
    overrided key/value pairs.
    """
    env.testval1 = "outer 1"
    prev_lcwd = env.lcwd

    def some_task():
        eq_(env.testval1, "inner 1")
        ok_(env.lcwd.endswith("here")) # Should be the side-effect of adding cd to settings

    decorated_task = decorators.with_settings(
        lcd("here"),
        testval1="inner 1"
    )(some_task)
    decorated_task()

    ok_(env.testval1, "outer 1")
    eq_(env.lcwd, prev_lcwd)

########NEW FILE########
__FILENAME__ = test_io
from __future__ import with_statement

from nose.tools import eq_

from fabric.io import OutputLooper
from fabric.context_managers import settings


def test_request_prompts():
    """
    Test valid responses from prompts
    """
    def run(txt, prompts):
        with settings(prompts=prompts):
            # try to fulfil the OutputLooper interface, only want to test
            # _get_prompt_response. (str has a method upper)
            ol = OutputLooper(str, 'upper', None, list(txt), None)
            return ol._get_prompt_response()

    prompts = {"prompt2": "response2",
               "prompt1": "response1",
               "prompt": "response"
               }

    eq_(run("this is a prompt for prompt1", prompts), ("prompt1", "response1"))
    eq_(run("this is a prompt for prompt2", prompts), ("prompt2", "response2"))
    eq_(run("this is a prompt for promptx:", prompts), (None, None))
    eq_(run("prompt for promp", prompts), (None, None))

########NEW FILE########
__FILENAME__ = test_main
from __future__ import with_statement

import copy
from functools import partial
from operator import isMappingType
import os
import sys
from contextlib import contextmanager

from fudge import Fake, patched_context, with_fakes
from nose.tools import ok_, eq_

from fabric.decorators import hosts, roles, task
from fabric.context_managers import settings
from fabric.main import (parse_arguments, _escape_split,
        load_fabfile as _load_fabfile, list_commands, _task_names,
        COMMANDS_HEADER, NESTED_REMINDER)
import fabric.state
from fabric.state import _AttributeDict
from fabric.tasks import Task, WrappedCallableTask
from fabric.task_utils import _crawl, crawl, merge

from utils import mock_streams, eq_, FabricTest, fabfile, path_prefix, aborts


# Stupid load_fabfile wrapper to hide newly added return value.
# WTB more free time to rewrite all this with objects :)
def load_fabfile(*args, **kwargs):
    return _load_fabfile(*args, **kwargs)[:2]


#
# Basic CLI stuff
#

def test_argument_parsing():
    for args, output in [
        # Basic 
        ('abc', ('abc', [], {}, [], [], [])),
        # Arg
        ('ab:c', ('ab', ['c'], {}, [], [], [])),
        # Kwarg
        ('a:b=c', ('a', [], {'b':'c'}, [], [], [])),
        # Arg and kwarg
        ('a:b=c,d', ('a', ['d'], {'b':'c'}, [], [], [])),
        # Multiple kwargs
        ('a:b=c,d=e', ('a', [], {'b':'c','d':'e'}, [], [], [])),
        # Host
        ('abc:host=foo', ('abc', [], {}, ['foo'], [], [])),
        # Hosts with single host
        ('abc:hosts=foo', ('abc', [], {}, ['foo'], [], [])),
        # Hosts with multiple hosts
        # Note: in a real shell, one would need to quote or escape "foo;bar".
        # But in pure-Python that would get interpreted literally, so we don't.
        ('abc:hosts=foo;bar', ('abc', [], {}, ['foo', 'bar'], [], [])),

        # Exclude hosts
        ('abc:hosts=foo;bar,exclude_hosts=foo', ('abc', [], {}, ['foo', 'bar'], [], ['foo'])),
        ('abc:hosts=foo;bar,exclude_hosts=foo;bar', ('abc', [], {}, ['foo', 'bar'], [], ['foo','bar'])),
       # Empty string args
        ("task:x=y,z=", ('task', [], {'x': 'y', 'z': ''}, [], [], [])),
        ("task:foo,,x=y", ('task', ['foo', ''], {'x': 'y'}, [], [], [])),
    ]:
        yield eq_, parse_arguments([args]), [output]


def test_escaped_task_arg_split():
    """
    Allow backslashes to escape the task argument separator character
    """
    argstr = r"foo,bar\,biz\,baz,what comes after baz?"
    eq_(
        _escape_split(',', argstr),
        ['foo', 'bar,biz,baz', 'what comes after baz?']
    )


def test_escaped_task_kwarg_split():
    """
    Allow backslashes to escape the = in x=y task kwargs
    """
    argstr = r"cmd:arg,escaped\,arg,nota\=kwarg,regular=kwarg,escaped=regular\=kwarg"
    args = ['arg', 'escaped,arg', 'nota=kwarg']
    kwargs = {'regular': 'kwarg', 'escaped': 'regular=kwarg'}
    eq_(
        parse_arguments([argstr])[0],
        ('cmd', args, kwargs, [], [], []),
    )



#
# Host/role decorators
#

# Allow calling Task.get_hosts as function instead (meh.)
def get_hosts_and_effective_roles(command, *args):
    return WrappedCallableTask(command).get_hosts_and_effective_roles(*args)

def eq_hosts(command, expected_hosts, cli_hosts=None, excluded_hosts=None, env=None, func=set):
    eq_(func(get_hosts_and_effective_roles(command, cli_hosts or [], [], excluded_hosts or [], env)[0]),
        func(expected_hosts))

def eq_effective_roles(command, expected_effective_roles, cli_roles=None, env=None, func=set):
    eq_(func(get_hosts_and_effective_roles(command, [], cli_roles or [], [], env)[1]),
        func(expected_effective_roles))

true_eq_hosts = partial(eq_hosts, func=lambda x: x)

def test_hosts_decorator_by_itself():
    """
    Use of @hosts only
    """
    host_list = ['a', 'b']

    @hosts(*host_list)
    def command():
        pass

    eq_hosts(command, host_list)


fake_roles = {
    'r1': ['a', 'b'],
    'r2': ['b', 'c']
}

def test_roles_decorator_by_itself():
    """
    Use of @roles only
    """
    @roles('r1')
    def command():
        pass
    eq_hosts(command, ['a', 'b'], env={'roledefs': fake_roles})
    eq_effective_roles(command, ['r1'], env={'roledefs': fake_roles})

def test_roles_decorator_overrides_env_roles():
    """
    If @roles is used it replaces any env.roles value
    """
    @roles('r1')
    def command():
        pass
    eq_effective_roles(command, ['r1'], env={'roledefs': fake_roles,
                                             'roles': ['r2']})

def test_cli_roles_override_decorator_roles():
    """
    If CLI roles are provided they replace roles defined in @roles.
    """
    @roles('r1')
    def command():
        pass
    eq_effective_roles(command, ['r2'], cli_roles=['r2'], env={'roledefs': fake_roles})


def test_hosts_and_roles_together():
    """
    Use of @roles and @hosts together results in union of both
    """
    @roles('r1', 'r2')
    @hosts('d')
    def command():
        pass
    eq_hosts(command, ['a', 'b', 'c', 'd'], env={'roledefs': fake_roles})
    eq_effective_roles(command, ['r1', 'r2'], env={'roledefs': fake_roles})

def test_host_role_merge_deduping():
    """
    Use of @roles and @hosts dedupes when merging
    """
    @roles('r1', 'r2')
    @hosts('a')
    def command():
        pass
    # Not ['a', 'a', 'b', 'c'] or etc
    true_eq_hosts(command, ['a', 'b', 'c'], env={'roledefs': fake_roles})

def test_host_role_merge_deduping_off():
    """
    Allow turning deduping off
    """
    @roles('r1', 'r2')
    @hosts('a')
    def command():
        pass
    with settings(dedupe_hosts=False):
        true_eq_hosts(
            command,
            # 'a' 1x host 1x role
            # 'b' 1x r1 1x r2
            ['a', 'a', 'b', 'b', 'c'],
            env={'roledefs': fake_roles}
        )


tuple_roles = {
    'r1': ('a', 'b'),
    'r2': ('b', 'c'),
}

def test_roles_as_tuples():
    """
    Test that a list of roles as a tuple succeeds
    """
    @roles('r1')
    def command():
        pass
    eq_hosts(command, ['a', 'b'], env={'roledefs': tuple_roles})
    eq_effective_roles(command, ['r1'], env={'roledefs': fake_roles})


def test_hosts_as_tuples():
    """
    Test that a list of hosts as a tuple succeeds
    """
    def command():
        pass
    eq_hosts(command, ['foo', 'bar'], env={'hosts': ('foo', 'bar')})


def test_hosts_decorator_overrides_env_hosts():
    """
    If @hosts is used it replaces any env.hosts value
    """
    @hosts('bar')
    def command():
        pass
    eq_hosts(command, ['bar'], env={'hosts': ['foo']})

def test_hosts_decorator_overrides_env_hosts_with_task_decorator_first():
    """
    If @hosts is used it replaces any env.hosts value even with @task
    """
    @task
    @hosts('bar')
    def command():
        pass
    eq_hosts(command, ['bar'], env={'hosts': ['foo']})

def test_hosts_decorator_overrides_env_hosts_with_task_decorator_last():
    @hosts('bar')
    @task
    def command():
        pass
    eq_hosts(command, ['bar'], env={'hosts': ['foo']})

def test_hosts_stripped_env_hosts():
    """
    Make sure hosts defined in env.hosts are cleaned of extra spaces
    """
    def command():
        pass
    myenv = {'hosts': [' foo ', 'bar '], 'roles': [], 'exclude_hosts': []}
    eq_hosts(command, ['foo', 'bar'], env=myenv)


spaced_roles = {
    'r1': [' a ', ' b '],
    'r2': ['b', 'c'],
}

def test_roles_stripped_env_hosts():
    """
    Make sure hosts defined in env.roles are cleaned of extra spaces
    """
    @roles('r1')
    def command():
        pass
    eq_hosts(command, ['a', 'b'], env={'roledefs': spaced_roles})


def test_hosts_decorator_expands_single_iterable():
    """
    @hosts(iterable) should behave like @hosts(*iterable)
    """
    host_list = ['foo', 'bar']

    @hosts(host_list)
    def command():
        pass

    eq_(command.hosts, host_list)

def test_roles_decorator_expands_single_iterable():
    """
    @roles(iterable) should behave like @roles(*iterable)
    """
    role_list = ['foo', 'bar']

    @roles(role_list)
    def command():
        pass

    eq_(command.roles, role_list)


#
# Host exclusion
#

def dummy(): pass

def test_get_hosts_excludes_cli_exclude_hosts_from_cli_hosts():
    eq_hosts(dummy, ['bar'], cli_hosts=['foo', 'bar'], excluded_hosts=['foo'])

def test_get_hosts_excludes_cli_exclude_hosts_from_decorator_hosts():
    @hosts('foo', 'bar')
    def command():
        pass
    eq_hosts(command, ['bar'], excluded_hosts=['foo'])

def test_get_hosts_excludes_global_exclude_hosts_from_global_hosts():
    fake_env = {'hosts': ['foo', 'bar'], 'exclude_hosts': ['foo']}
    eq_hosts(dummy, ['bar'], env=fake_env)



#
# Basic role behavior
#

@aborts
def test_aborts_on_nonexistent_roles():
    """
    Aborts if any given roles aren't found
    """
    merge([], ['badrole'], [], {})

def test_accepts_non_list_hosts():
    """
    Coerces given host string to a one-item list
    """
    assert merge('badhosts', [], [], {}) == ['badhosts']


lazy_role = {'r1': lambda: ['a', 'b']}

def test_lazy_roles():
    """
    Roles may be callables returning lists, as well as regular lists
    """
    @roles('r1')
    def command():
        pass
    eq_hosts(command, ['a', 'b'], env={'roledefs': lazy_role})


#
# Fabfile loading
#

def run_load_fabfile(path, sys_path):
    # Module-esque object
    fake_module = Fake().has_attr(__dict__={})
    # Fake __import__
    importer = Fake(callable=True).returns(fake_module)
    # Snapshot sys.path for restore
    orig_path = copy.copy(sys.path)
    # Update with fake path
    sys.path = sys_path
    # Test for side effects
    load_fabfile(path, importer=importer)
    eq_(sys.path, sys_path)
    # Restore
    sys.path = orig_path

def test_load_fabfile_should_not_remove_real_path_elements():
    for fabfile_path, sys_dot_path in (
        # Directory not in path
        ('subdir/fabfile.py', ['not_subdir']),
        ('fabfile.py', ['nope']),
        # Directory in path, but not at front
        ('subdir/fabfile.py', ['not_subdir', 'subdir']),
        ('fabfile.py', ['not_subdir', '']),
        ('fabfile.py', ['not_subdir', '', 'also_not_subdir']),
        # Directory in path, and at front already
        ('subdir/fabfile.py', ['subdir']),
        ('subdir/fabfile.py', ['subdir', 'not_subdir']),
        ('fabfile.py', ['', 'some_dir', 'some_other_dir']),
    ):
            yield run_load_fabfile, fabfile_path, sys_dot_path


#
# Namespacing and new-style tasks
#

class TestTaskAliases(FabricTest):
    def test_flat_alias(self):
        f = fabfile("flat_alias.py")
        with path_prefix(f):
            docs, funcs = load_fabfile(f)
            eq_(len(funcs), 2)
            ok_("foo" in funcs)
            ok_("foo_aliased" in funcs)

    def test_nested_alias(self):
        f = fabfile("nested_alias.py")
        with path_prefix(f):
            docs, funcs = load_fabfile(f)
            ok_("nested" in funcs)
            eq_(len(funcs["nested"]), 2)
            ok_("foo" in funcs["nested"])
            ok_("foo_aliased" in funcs["nested"])

    def test_flat_aliases(self):
        f = fabfile("flat_aliases.py")
        with path_prefix(f):
            docs, funcs = load_fabfile(f)
            eq_(len(funcs), 3)
            ok_("foo" in funcs)
            ok_("foo_aliased" in funcs)
            ok_("foo_aliased_two" in funcs)

    def test_nested_aliases(self):
        f = fabfile("nested_aliases.py")
        with path_prefix(f):
            docs, funcs = load_fabfile(f)
            ok_("nested" in funcs)
            eq_(len(funcs["nested"]), 3)
            ok_("foo" in funcs["nested"])
            ok_("foo_aliased" in funcs["nested"])
            ok_("foo_aliased_two" in funcs["nested"])


class TestNamespaces(FabricTest):
    def setup(self):
        # Parent class preserves current env
        super(TestNamespaces, self).setup()
        # Reset new-style-tests flag so running tests via Fab itself doesn't
        # muck with it.
        import fabric.state
        if 'new_style_tasks' in fabric.state.env:
            del fabric.state.env['new_style_tasks']

    def test_implicit_discovery(self):
        """
        Default to automatically collecting all tasks in a fabfile module
        """
        implicit = fabfile("implicit_fabfile.py")
        with path_prefix(implicit):
            docs, funcs = load_fabfile(implicit)
            eq_(len(funcs), 2)
            ok_("foo" in funcs)
            ok_("bar" in funcs)

    def test_explicit_discovery(self):
        """
        If __all__ is present, only collect the tasks it specifies
        """
        explicit = fabfile("explicit_fabfile.py")
        with path_prefix(explicit):
            docs, funcs = load_fabfile(explicit)
            eq_(len(funcs), 1)
            ok_("foo" in funcs)
            ok_("bar" not in funcs)

    def test_should_load_decorated_tasks_only_if_one_is_found(self):
        """
        If any new-style tasks are found, *only* new-style tasks should load
        """
        module = fabfile('decorated_fabfile.py')
        with path_prefix(module):
            docs, funcs = load_fabfile(module)
            eq_(len(funcs), 1)
            ok_('foo' in funcs)

    def test_class_based_tasks_are_found_with_proper_name(self):
        """
        Wrapped new-style tasks should preserve their function names
        """
        module = fabfile('decorated_fabfile_with_classbased_task.py')
        from fabric.state import env
        with path_prefix(module):
            docs, funcs = load_fabfile(module)
            eq_(len(funcs), 1)
            ok_('foo' in funcs)

    def test_class_based_tasks_are_found_with_variable_name(self):
        """
        A new-style tasks with undefined name attribute should use the instance
        variable name.
        """
        module = fabfile('classbased_task_fabfile.py')
        from fabric.state import env
        with path_prefix(module):
            docs, funcs = load_fabfile(module)
            eq_(len(funcs), 1)
            ok_('foo' in funcs)
            eq_(funcs['foo'].name, 'foo')

    def test_recursion_steps_into_nontask_modules(self):
        """
        Recursive loading will continue through modules with no tasks
        """
        module = fabfile('deep')
        with path_prefix(module):
            docs, funcs = load_fabfile(module)
            eq_(len(funcs), 1)
            ok_('submodule.subsubmodule.deeptask' in _task_names(funcs))

    def test_newstyle_task_presence_skips_classic_task_modules(self):
        """
        Classic-task-only modules shouldn't add tasks if any new-style tasks exist
        """
        module = fabfile('deep')
        with path_prefix(module):
            docs, funcs = load_fabfile(module)
            eq_(len(funcs), 1)
            ok_('submodule.classic_task' not in _task_names(funcs))

    def test_task_decorator_plays_well_with_others(self):
        """
        @task, when inside @hosts/@roles, should not hide the decorated task.
        """
        module = fabfile('decorator_order')
        with path_prefix(module):
            docs, funcs = load_fabfile(module)
            # When broken, crawl() finds None for 'foo' instead.
            eq_(crawl('foo', funcs), funcs['foo'])


#
# --list output
#

def eq_output(docstring, format_, expected):
    return eq_(
        "\n".join(list_commands(docstring, format_)),
        expected
    )

def list_output(module, format_, expected):
    module = fabfile(module)
    with path_prefix(module):
        docstring, tasks = load_fabfile(module)
        with patched_context(fabric.state, 'commands', tasks):
            eq_output(docstring, format_, expected)

def test_list_output():
    lead = ":\n\n    "
    normal_head = COMMANDS_HEADER + lead
    nested_head = COMMANDS_HEADER + NESTED_REMINDER + lead
    for desc, module, format_, expected in (
        ("shorthand (& with namespacing)", 'deep', 'short', "submodule.subsubmodule.deeptask"),
        ("normal (& with namespacing)", 'deep', 'normal', normal_head + "submodule.subsubmodule.deeptask"),
        ("normal (with docstring)", 'docstring', 'normal', normal_head + "foo  Foos!"),
        ("nested (leaf only)", 'deep', 'nested', nested_head + """submodule:
        subsubmodule:
            deeptask"""),
        ("nested (full)", 'tree', 'nested', nested_head + """build_docs
    deploy
    db:
        migrate
    system:
        install_package
        debian:
            update_apt"""),
    ):
        list_output.description = "--list output: %s" % desc
        yield list_output, module, format_, expected
        del list_output.description


def name_to_task(name):
    t = Task()
    t.name = name
    return t

def strings_to_tasks(d):
    ret = {}
    for key, value in d.iteritems():
        if isMappingType(value):
            val = strings_to_tasks(value)
        else:
            val = name_to_task(value)
        ret[key] = val
    return ret

def test_task_names():
    for desc, input_, output in (
        ('top level (single)', {'a': 5}, ['a']),
        ('top level (multiple, sorting)', {'a': 5, 'b': 6}, ['a', 'b']),
        ('just nested', {'a': {'b': 5}}, ['a.b']),
        ('mixed', {'a': 5, 'b': {'c': 6}}, ['a', 'b.c']),
        ('top level comes before nested', {'z': 5, 'b': {'c': 6}}, ['z', 'b.c']),
        ('peers sorted equally', {'z': 5, 'b': {'c': 6}, 'd': {'e': 7}}, ['z', 'b.c', 'd.e']),
        (
            'complex tree',
            {
                'z': 5,
                'b': {
                    'c': 6,
                    'd': {
                        'e': {
                            'f': '7'
                        }
                    },
                    'g': 8
                },
                'h': 9,
                'w': {
                    'y': 10
                }
            },
            ['h', 'z', 'b.c', 'b.g', 'b.d.e.f', 'w.y']
        ),
    ):
        eq_.description = "task name flattening: %s" % desc
        yield eq_, _task_names(strings_to_tasks(input_)), output
        del eq_.description


def test_crawl():
    for desc, name, mapping, output in (
        ("base case", 'a', {'a': 5}, 5),
        ("one level", 'a.b', {'a': {'b': 5}}, 5),
        ("deep", 'a.b.c.d.e', {'a': {'b': {'c': {'d': {'e': 5}}}}}, 5),
        ("full tree", 'a.b.c', {'a': {'b': {'c': 5}, 'd': 6}, 'z': 7}, 5)
    ):
        eq_.description = "crawling dotted names: %s" % desc
        yield eq_, _crawl(name, mapping), output
        del eq_.description


def test_mapping_task_classes():
    """
    Task classes implementing the mapping interface shouldn't break --list
    """
    list_output('mapping', 'normal', COMMANDS_HEADER + """:\n
    mapping_task""")


def test_default_task_listings():
    """
    @task(default=True) should cause task to also load under module's name
    """
    for format_, expected in (
        ('short', """mymodule
mymodule.long_task_name"""),
        ('normal', COMMANDS_HEADER + """:\n
    mymodule
    mymodule.long_task_name"""),
        ('nested', COMMANDS_HEADER + NESTED_REMINDER + """:\n
    mymodule:
        long_task_name""")
    ):
        list_output.description = "Default task --list output: %s" % format_
        yield list_output, 'default_tasks', format_, expected
        del list_output.description


def test_default_task_loading():
    """
    crawl() should return default tasks where found, instead of module objs
    """
    docs, tasks = load_fabfile(fabfile('default_tasks'))
    ok_(isinstance(crawl('mymodule', tasks), Task))


def test_aliases_appear_in_fab_list():
    """
    --list should include aliases
    """
    list_output('nested_alias', 'short', """nested.foo
nested.foo_aliased""")

########NEW FILE########
__FILENAME__ = test_network
from __future__ import with_statement

from datetime import datetime
import copy
import getpass
import sys

from nose.tools import with_setup, ok_, raises
from fudge import (Fake, clear_calls, clear_expectations, patch_object, verify,
    with_patched_object, patched_context, with_fakes)

from fabric.context_managers import settings, hide, show
from fabric.network import (HostConnectionCache, join_host_strings, normalize,
    denormalize, key_filenames, ssh)
from fabric.io import output_loop
import fabric.network  # So I can call patch_object correctly. Sigh.
from fabric.state import env, output, _get_system_username
from fabric.operations import run, sudo, prompt
from fabric.exceptions import NetworkError
from fabric.tasks import execute
from fabric import utils # for patching

from utils import *
from server import (server, PORT, RESPONSES, PASSWORDS, CLIENT_PRIVKEY, USER,
    CLIENT_PRIVKEY_PASSPHRASE)


#
# Subroutines, e.g. host string normalization
#


class TestNetwork(FabricTest):
    def test_host_string_normalization(self):
        username = _get_system_username()
        for description, input, output_ in (
            ("Sanity check: equal strings remain equal",
                'localhost', 'localhost'),
            ("Empty username is same as get_system_username",
                'localhost', username + '@localhost'),
            ("Empty port is same as port 22",
                'localhost', 'localhost:22'),
            ("Both username and port tested at once, for kicks",
                'localhost', username + '@localhost:22'),
        ):
            eq_.description = "Host-string normalization: %s" % description
            yield eq_, normalize(input), normalize(output_)
            del eq_.description

    def test_normalization_for_ipv6(self):
        """
        normalize() will accept IPv6 notation and can separate host and port
        """
        username = _get_system_username()
        for description, input, output_ in (
            ("Full IPv6 address",
                '2001:DB8:0:0:0:0:0:1', (username, '2001:DB8:0:0:0:0:0:1', '22')),
            ("IPv6 address in short form",
                '2001:DB8::1', (username, '2001:DB8::1', '22')),
            ("IPv6 localhost",
                '::1', (username, '::1', '22')),
            ("Square brackets are required to separate non-standard port from IPv6 address",
                '[2001:DB8::1]:1222', (username, '2001:DB8::1', '1222')),
            ("Username and IPv6 address",
                'user@2001:DB8::1', ('user', '2001:DB8::1', '22')),
            ("Username and IPv6 address with non-standard port",
                'user@[2001:DB8::1]:1222', ('user', '2001:DB8::1', '1222')),
        ):
            eq_.description = "Host-string IPv6 normalization: %s" % description
            yield eq_, normalize(input), output_
            del eq_.description

    def test_normalization_without_port(self):
        """
        normalize() and join_host_strings() omit port if omit_port given
        """
        eq_(
            join_host_strings(*normalize('user@localhost', omit_port=True)),
            'user@localhost'
        )

    def test_ipv6_host_strings_join(self):
        """
        join_host_strings() should use square brackets only for IPv6 and if port is given
        """
        eq_(
            join_host_strings('user', '2001:DB8::1'),
            'user@2001:DB8::1'
        )
        eq_(
            join_host_strings('user', '2001:DB8::1', '1222'),
            'user@[2001:DB8::1]:1222'
        )
        eq_(
            join_host_strings('user', '192.168.0.0', '1222'),
            'user@192.168.0.0:1222'
        )

    def test_nonword_character_in_username(self):
        """
        normalize() will accept non-word characters in the username part
        """
        eq_(
            normalize('user-with-hyphens@someserver.org')[0],
            'user-with-hyphens'
        )

    def test_at_symbol_in_username(self):
        """
        normalize() should allow '@' in usernames (i.e. last '@' is split char)
        """
        parts = normalize('user@example.com@www.example.com')
        eq_(parts[0], 'user@example.com')
        eq_(parts[1], 'www.example.com')

    def test_normalization_of_empty_input(self):
        empties = ('', '', '')
        for description, input in (
            ("empty string", ''),
            ("None", None)
        ):
            template = "normalize() returns empty strings for %s input"
            eq_.description = template % description
            yield eq_, normalize(input), empties
            del eq_.description

    def test_host_string_denormalization(self):
        username = _get_system_username()
        for description, string1, string2 in (
            ("Sanity check: equal strings remain equal",
                'localhost', 'localhost'),
            ("Empty username is same as get_system_username",
                'localhost:22', username + '@localhost:22'),
            ("Empty port is same as port 22",
                'user@localhost', 'user@localhost:22'),
            ("Both username and port",
                'localhost', username + '@localhost:22'),
            ("IPv6 address",
                '2001:DB8::1', username + '@[2001:DB8::1]:22'),
        ):
            eq_.description = "Host-string denormalization: %s" % description
            yield eq_, denormalize(string1), denormalize(string2)
            del eq_.description

    #
    # Connection caching
    #
    @staticmethod
    @with_fakes
    def check_connection_calls(host_strings, num_calls):
        # Clear Fudge call stack
        # Patch connect() with Fake obj set to expect num_calls calls
        patched_connect = patch_object('fabric.network', 'connect',
            Fake('connect', expect_call=True).times_called(num_calls)
        )
        try:
            # Make new cache object
            cache = HostConnectionCache()
            # Connect to all connection strings
            for host_string in host_strings:
                # Obtain connection from cache, potentially calling connect()
                cache[host_string]
        finally:
            # Restore connect()
            patched_connect.restore()

    def test_connection_caching(self):
        for description, host_strings, num_calls in (
            ("Two different host names, two connections",
                ('localhost', 'other-system'), 2),
            ("Same host twice, one connection",
                ('localhost', 'localhost'), 1),
            ("Same host twice, different ports, two connections",
                ('localhost:22', 'localhost:222'), 2),
            ("Same host twice, different users, two connections",
                ('user1@localhost', 'user2@localhost'), 2),
        ):
            TestNetwork.check_connection_calls.description = description
            yield TestNetwork.check_connection_calls, host_strings, num_calls

    def test_connection_cache_deletion(self):
        """
        HostConnectionCache should delete correctly w/ non-full keys
        """
        hcc = HostConnectionCache()
        fake = Fake('connect', callable=True)
        with patched_context('fabric.network', 'connect', fake):
            for host_string in ('hostname', 'user@hostname',
                'user@hostname:222'):
                # Prime
                hcc[host_string]
                # Test
                ok_(host_string in hcc)
                # Delete
                del hcc[host_string]
                # Test
                ok_(host_string not in hcc)


    #
    # Connection loop flow
    #
    @server()
    def test_saved_authentication_returns_client_object(self):
        cache = HostConnectionCache()
        assert isinstance(cache[env.host_string], ssh.SSHClient)

    @server()
    @with_fakes
    def test_prompts_for_password_without_good_authentication(self):
        env.password = None
        with password_response(PASSWORDS[env.user], times_called=1):
            cache = HostConnectionCache()
            cache[env.host_string]


    @aborts
    def test_aborts_on_prompt_with_abort_on_prompt(self):
        """
        abort_on_prompt=True should abort when prompt() is used
        """
        env.abort_on_prompts = True
        prompt("This will abort")


    @server()
    @aborts
    def test_aborts_on_password_prompt_with_abort_on_prompt(self):
        """
        abort_on_prompt=True should abort when password prompts occur
        """
        env.password = None
        env.abort_on_prompts = True
        with password_response(PASSWORDS[env.user], times_called=1):
            cache = HostConnectionCache()
            cache[env.host_string]


    @mock_streams('stdout')
    @server()
    def test_does_not_abort_with_password_and_host_with_abort_on_prompt(self):
        """
        abort_on_prompt=True should not abort if no prompts are needed
        """
        env.abort_on_prompts = True
        env.password = PASSWORDS[env.user]
        # env.host_string is automatically filled in when using server()
        run("ls /simple")


    @mock_streams('stdout')
    @server()
    def test_trailing_newline_line_drop(self):
        """
        Trailing newlines shouldn't cause last line to be dropped.
        """
        # Multiline output with trailing newline
        cmd = "ls /"
        output_string = RESPONSES[cmd]
        # TODO: fix below lines, duplicates inner workings of tested code
        prefix = "[%s] out: " % env.host_string
        expected = prefix + ('\n' + prefix).join(output_string.split('\n'))
        # Create, tie off thread
        with settings(show('everything'), hide('running')):
            result = run(cmd)
            # Test equivalence of expected, received output
            eq_(expected, sys.stdout.getvalue())
            # Also test that the captured value matches, too.
            eq_(output_string, result)

    @server()
    def test_sudo_prompt_kills_capturing(self):
        """
        Sudo prompts shouldn't screw up output capturing
        """
        cmd = "ls /simple"
        with hide('everything'):
            eq_(sudo(cmd), RESPONSES[cmd])

    @server()
    def test_password_memory_on_user_switch(self):
        """
        Switching users mid-session should not screw up password memory
        """
        def _to_user(user):
            return join_host_strings(user, env.host, env.port)

        user1 = 'root'
        user2 = USER
        with settings(hide('everything'), password=None):
            # Connect as user1 (thus populating both the fallback and
            # user-specific caches)
            with settings(
                password_response(PASSWORDS[user1]),
                host_string=_to_user(user1)
            ):
                run("ls /simple")
            # Connect as user2: * First cxn attempt will use fallback cache,
            # which contains user1's password, and thus fail * Second cxn
            # attempt will prompt user, and succeed due to mocked p4p * but
            # will NOT overwrite fallback cache
            with settings(
                password_response(PASSWORDS[user2]),
                host_string=_to_user(user2)
            ):
                # Just to trigger connection
                run("ls /simple")
            # * Sudo call should use cached user2 password, NOT fallback cache,
            # and thus succeed. (I.e. p_f_p should NOT be called here.)
            with settings(
                password_response('whatever', times_called=0),
                host_string=_to_user(user2)
            ):
                sudo("ls /simple")

    @mock_streams('stderr')
    @server()
    def test_password_prompt_displays_host_string(self):
        """
        Password prompt lines should include the user/host in question
        """
        env.password = None
        env.no_agent = env.no_keys = True
        output.everything = False
        with password_response(PASSWORDS[env.user], silent=False):
            run("ls /simple")
        regex = r'^\[%s\] Login password for \'%s\': ' % (env.host_string, env.user)
        assert_contains(regex, sys.stderr.getvalue())

    @mock_streams('stderr')
    @server(pubkeys=True)
    def test_passphrase_prompt_displays_host_string(self):
        """
        Passphrase prompt lines should include the user/host in question
        """
        env.password = None
        env.no_agent = env.no_keys = True
        env.key_filename = CLIENT_PRIVKEY
        output.everything = False
        with password_response(CLIENT_PRIVKEY_PASSPHRASE, silent=False):
            run("ls /simple")
        regex = r'^\[%s\] Login password for \'%s\': ' % (env.host_string, env.user)
        assert_contains(regex, sys.stderr.getvalue())

    def test_sudo_prompt_display_passthrough(self):
        """
        Sudo prompt should display (via passthrough) when stdout/stderr shown
        """
        TestNetwork._prompt_display(True)

    def test_sudo_prompt_display_directly(self):
        """
        Sudo prompt should display (manually) when stdout/stderr hidden
        """
        TestNetwork._prompt_display(False)

    @staticmethod
    @mock_streams('both')
    @server(pubkeys=True, responses={'oneliner': 'result'})
    def _prompt_display(display_output):
        env.password = None
        env.no_agent = env.no_keys = True
        env.key_filename = CLIENT_PRIVKEY
        output.output = display_output
        with password_response(
            (CLIENT_PRIVKEY_PASSPHRASE, PASSWORDS[env.user]),
            silent=False
        ):
            sudo('oneliner')
        if display_output:
            expected = """
[%(prefix)s] sudo: oneliner
[%(prefix)s] Login password for '%(user)s': 
[%(prefix)s] out: sudo password:
[%(prefix)s] out: Sorry, try again.
[%(prefix)s] out: sudo password: 
[%(prefix)s] out: result
""" % {'prefix': env.host_string, 'user': env.user}
        else:
            # Note lack of first sudo prompt (as it's autoresponded to) and of
            # course the actual result output.
            expected = """
[%(prefix)s] sudo: oneliner
[%(prefix)s] Login password for '%(user)s': 
[%(prefix)s] out: Sorry, try again.
[%(prefix)s] out: sudo password: """ % {
    'prefix': env.host_string,
    'user': env.user
}
        eq_(expected[1:], sys.stdall.getvalue())

    @mock_streams('both')
    @server(
        pubkeys=True,
        responses={'oneliner': 'result', 'twoliner': 'result1\nresult2'}
    )
    def test_consecutive_sudos_should_not_have_blank_line(self):
        """
        Consecutive sudo() calls should not incur a blank line in-between
        """
        env.password = None
        env.no_agent = env.no_keys = True
        env.key_filename = CLIENT_PRIVKEY
        with password_response(
            (CLIENT_PRIVKEY_PASSPHRASE, PASSWORDS[USER]),
            silent=False
        ):
            sudo('oneliner')
            sudo('twoliner')
        expected = """
[%(prefix)s] sudo: oneliner
[%(prefix)s] Login password for '%(user)s': 
[%(prefix)s] out: sudo password:
[%(prefix)s] out: Sorry, try again.
[%(prefix)s] out: sudo password: 
[%(prefix)s] out: result
[%(prefix)s] sudo: twoliner
[%(prefix)s] out: sudo password:
[%(prefix)s] out: result1
[%(prefix)s] out: result2
""" % {'prefix': env.host_string, 'user': env.user}
        eq_(sys.stdall.getvalue(), expected[1:])

    @mock_streams('both')
    @server(pubkeys=True, responses={'silent': '', 'normal': 'foo'})
    def test_silent_commands_should_not_have_blank_line(self):
        """
        Silent commands should not generate an extra trailing blank line

        After the move to interactive I/O, it was noticed that while run/sudo
        commands which had non-empty stdout worked normally (consecutive such
        commands were totally adjacent), those with no stdout (i.e. silent
        commands like ``test`` or ``mkdir``) resulted in spurious blank lines
        after the "run:" line. This looks quite ugly in real world scripts.
        """
        env.password = None
        env.no_agent = env.no_keys = True
        env.key_filename = CLIENT_PRIVKEY
        with password_response(CLIENT_PRIVKEY_PASSPHRASE, silent=False):
            run('normal')
            run('silent')
            run('normal')
            with hide('everything'):
                run('normal')
                run('silent')
        expected = """
[%(prefix)s] run: normal
[%(prefix)s] Login password for '%(user)s': 
[%(prefix)s] out: foo
[%(prefix)s] run: silent
[%(prefix)s] run: normal
[%(prefix)s] out: foo
""" % {'prefix': env.host_string, 'user': env.user}
        eq_(expected[1:], sys.stdall.getvalue())

    @mock_streams('both')
    @server(
        pubkeys=True,
        responses={'oneliner': 'result', 'twoliner': 'result1\nresult2'}
    )
    def test_io_should_print_prefix_if_ouput_prefix_is_true(self):
        """
        run/sudo should print [host_string] if env.output_prefix == True
        """
        env.password = None
        env.no_agent = env.no_keys = True
        env.key_filename = CLIENT_PRIVKEY
        with password_response(
            (CLIENT_PRIVKEY_PASSPHRASE, PASSWORDS[USER]),
            silent=False
        ):
            run('oneliner')
            run('twoliner')
        expected = """
[%(prefix)s] run: oneliner
[%(prefix)s] Login password for '%(user)s': 
[%(prefix)s] out: result
[%(prefix)s] run: twoliner
[%(prefix)s] out: result1
[%(prefix)s] out: result2
""" % {'prefix': env.host_string, 'user': env.user}
        eq_(expected[1:], sys.stdall.getvalue())

    @mock_streams('both')
    @server(
        pubkeys=True,
        responses={'oneliner': 'result', 'twoliner': 'result1\nresult2'}
    )
    def test_io_should_not_print_prefix_if_ouput_prefix_is_false(self):
        """
        run/sudo shouldn't print [host_string] if env.output_prefix == False
        """
        env.password = None
        env.no_agent = env.no_keys = True
        env.key_filename = CLIENT_PRIVKEY
        with password_response(
            (CLIENT_PRIVKEY_PASSPHRASE, PASSWORDS[USER]),
            silent=False
        ):
            with settings(output_prefix=False):
                run('oneliner')
                run('twoliner')
        expected = """
[%(prefix)s] run: oneliner
[%(prefix)s] Login password for '%(user)s': 
result
[%(prefix)s] run: twoliner
result1
result2
""" % {'prefix': env.host_string, 'user': env.user}
        eq_(expected[1:], sys.stdall.getvalue())

    @server()
    def test_env_host_set_when_host_prompt_used(self):
        """
        Ensure env.host is set during host prompting
        """
        copied_host_string = str(env.host_string)
        fake = Fake('raw_input', callable=True).returns(copied_host_string)
        env.host_string = None
        env.host = None
        with settings(hide('everything'), patched_input(fake)):
            run("ls /")
        # Ensure it did set host_string back to old value
        eq_(env.host_string, copied_host_string)
        # Ensure env.host is correct
        eq_(env.host, normalize(copied_host_string)[1])


def subtask():
    run("This should never execute")

class TestConnections(FabricTest):
    @aborts
    def test_should_abort_when_cannot_connect(self):
        """
        By default, connecting to a nonexistent server should abort.
        """
        with hide('everything'):
            execute(subtask, hosts=['nope.nonexistent.com'])

    def test_should_warn_when_skip_bad_hosts_is_True(self):
        """
        env.skip_bad_hosts = True => execute() skips current host
        """
        with settings(hide('everything'), skip_bad_hosts=True):
            execute(subtask, hosts=['nope.nonexistent.com'])


class TestSSHConfig(FabricTest):
    def env_setup(self):
        super(TestSSHConfig, self).env_setup()
        env.use_ssh_config = True
        env.ssh_config_path = support("ssh_config")
        # Undo the changes FabricTest makes to env for server support
        env.user = env.local_user
        env.port = env.default_port

    def test_global_user_with_default_env(self):
        """
        Global User should override default env.user
        """
        eq_(normalize("localhost")[0], "satan")

    def test_global_user_with_nondefault_env(self):
        """
        Global User should NOT override nondefault env.user
        """
        with settings(user="foo"):
            eq_(normalize("localhost")[0], "foo")

    def test_specific_user_with_default_env(self):
        """
        Host-specific User should override default env.user
        """
        eq_(normalize("myhost")[0], "neighbor")

    def test_user_vs_host_string_value(self):
        """
        SSH-config derived user should NOT override host-string user value
        """
        eq_(normalize("myuser@localhost")[0], "myuser")
        eq_(normalize("myuser@myhost")[0], "myuser")

    def test_global_port_with_default_env(self):
        """
        Global Port should override default env.port
        """
        eq_(normalize("localhost")[2], "666")

    def test_global_port_with_nondefault_env(self):
        """
        Global Port should NOT override nondefault env.port
        """
        with settings(port="777"):
            eq_(normalize("localhost")[2], "777")

    def test_specific_port_with_default_env(self):
        """
        Host-specific Port should override default env.port
        """
        eq_(normalize("myhost")[2], "664")

    def test_port_vs_host_string_value(self):
        """
        SSH-config derived port should NOT override host-string port value
        """
        eq_(normalize("localhost:123")[2], "123")
        eq_(normalize("myhost:123")[2], "123")

    def test_hostname_alias(self):
        """
        Hostname setting overrides host string's host value
        """
        eq_(normalize("localhost")[1], "localhost")
        eq_(normalize("myalias")[1], "otherhost")

    @with_patched_object(utils, 'warn', Fake('warn', callable=True,
        expect_call=True))
    def test_warns_with_bad_config_file_path(self):
        # use_ssh_config is already set in our env_setup()
        with settings(hide('everything'), ssh_config_path="nope_bad_lol"):
            normalize('foo')

    @server()
    def test_real_connection(self):
        """
        Test-server connection using ssh_config values
        """
        with settings(
            hide('everything'),
            ssh_config_path=support("testserver_ssh_config"),
            host_string='testserver',
        ):
            ok_(run("ls /simple").succeeded)


class TestKeyFilenames(FabricTest):
    def test_empty_everything(self):
        """
        No env.key_filename and no ssh_config = empty list
        """
        with settings(use_ssh_config=False):
            with settings(key_filename=""):
                eq_(key_filenames(), [])
            with settings(key_filename=[]):
                eq_(key_filenames(), [])

    def test_just_env(self):
        """
        Valid env.key_filename and no ssh_config = just env
        """
        with settings(use_ssh_config=False):
            with settings(key_filename="mykey"):
                eq_(key_filenames(), ["mykey"])
            with settings(key_filename=["foo", "bar"]):
                eq_(key_filenames(), ["foo", "bar"])

    def test_just_ssh_config(self):
        """
        No env.key_filename + valid ssh_config = ssh value
        """
        with settings(use_ssh_config=True, ssh_config_path=support("ssh_config")):
            for val in ["", []]:
                with settings(key_filename=val):
                    eq_(key_filenames(), ["foobar.pub"])

    def test_both(self):
        """
        Both env.key_filename + valid ssh_config = both show up w/ env var first
        """
        with settings(use_ssh_config=True, ssh_config_path=support("ssh_config")):
            with settings(key_filename="bizbaz.pub"):
                eq_(key_filenames(), ["bizbaz.pub", "foobar.pub"])
            with settings(key_filename=["bizbaz.pub", "whatever.pub"]):
                expected = ["bizbaz.pub", "whatever.pub", "foobar.pub"]
                eq_(key_filenames(), expected)

########NEW FILE########
__FILENAME__ = test_operations
from __future__ import with_statement

import os
import shutil
import sys
import types
from contextlib import nested
from StringIO import StringIO

import unittest
import random
import types

from nose.tools import raises, eq_, ok_
from fudge import with_patched_object

from fabric.state import env, output
from fabric.operations import require, prompt, _sudo_prefix, _shell_wrap, \
    _shell_escape
from fabric.api import get, put, hide, show, cd, lcd, local, run, sudo, quiet
from fabric.sftp import SFTP
from fabric.exceptions import CommandTimeout

from fabric.decorators import with_settings
from utils import *
from server import (server, PORT, RESPONSES, FILES, PASSWORDS, CLIENT_PRIVKEY,
    USER, CLIENT_PRIVKEY_PASSPHRASE)

#
# require()
#


def test_require_single_existing_key():
    """
    When given a single existing key, require() throws no exceptions
    """
    # 'version' is one of the default values, so we know it'll be there
    require('version')


def test_require_multiple_existing_keys():
    """
    When given multiple existing keys, require() throws no exceptions
    """
    require('version', 'sudo_prompt')


@aborts
def test_require_single_missing_key():
    """
    When given a single non-existent key, require() aborts
    """
    require('blah')


@aborts
def test_require_multiple_missing_keys():
    """
    When given multiple non-existent keys, require() aborts
    """
    require('foo', 'bar')


@aborts
def test_require_mixed_state_keys():
    """
    When given mixed-state keys, require() aborts
    """
    require('foo', 'version')


@mock_streams('stderr')
def test_require_mixed_state_keys_prints_missing_only():
    """
    When given mixed-state keys, require() prints missing keys only
    """
    try:
        require('foo', 'version')
    except SystemExit:
        err = sys.stderr.getvalue()
        assert 'version' not in err
        assert 'foo' in err


@aborts
def test_require_iterable_provided_by_key():
    """
    When given a provided_by iterable value, require() aborts
    """
    # 'version' is one of the default values, so we know it'll be there
    def fake_providing_function():
        pass
    require('foo', provided_by=[fake_providing_function])


@aborts
def test_require_noniterable_provided_by_key():
    """
    When given a provided_by noniterable value, require() aborts
    """
    # 'version' is one of the default values, so we know it'll be there
    def fake_providing_function():
        pass
    require('foo', provided_by=fake_providing_function)


@aborts
def test_require_key_exists_empty_list():
    """
    When given a single existing key but the value is an empty list, require()
    aborts
    """
    # 'hosts' is one of the default values, so we know it'll be there
    require('hosts')


@aborts
@with_settings(foo={})
def test_require_key_exists_empty_dict():
    """
    When given a single existing key but the value is an empty dict, require()
    aborts
    """
    require('foo')


@aborts
@with_settings(foo=())
def test_require_key_exists_empty_tuple():
    """
    When given a single existing key but the value is an empty tuple, require()
    aborts
    """
    require('foo')


@aborts
@with_settings(foo=set())
def test_require_key_exists_empty_set():
    """
    When given a single existing key but the value is an empty set, require()
    aborts
    """
    require('foo')


@with_settings(foo=0, bar=False)
def test_require_key_exists_false_primitive_values():
    """
    When given keys that exist with primitive values that evaluate to False,
    require() throws no exception
    """
    require('foo', 'bar')


@with_settings(foo=['foo'], bar={'bar': 'bar'}, baz=('baz',), qux=set('qux'))
def test_require_complex_non_empty_values():
    """
    When given keys that exist with non-primitive values that are not empty,
    require() throws no exception
    """
    require('foo', 'bar', 'baz', 'qux')


#
# prompt()
#

def p(x):
    sys.stdout.write(x)


@mock_streams('stdout')
@with_patched_input(p)
def test_prompt_appends_space():
    """
    prompt() appends a single space when no default is given
    """
    s = "This is my prompt"
    prompt(s)
    eq_(sys.stdout.getvalue(), s + ' ')


@mock_streams('stdout')
@with_patched_input(p)
def test_prompt_with_default():
    """
    prompt() appends given default value plus one space on either side
    """
    s = "This is my prompt"
    d = "default!"
    prompt(s, default=d)
    eq_(sys.stdout.getvalue(), "%s [%s] " % (s, d))


#
# run()/sudo()
#

def test_sudo_prefix_with_user():
    """
    _sudo_prefix() returns prefix plus -u flag for nonempty user
    """
    eq_(
        _sudo_prefix(user="foo", group=None),
        "%s -u \"foo\" " % (env.sudo_prefix % env)
    )


def test_sudo_prefix_without_user():
    """
    _sudo_prefix() returns standard prefix when user is empty
    """
    eq_(_sudo_prefix(user=None, group=None), env.sudo_prefix % env)


def test_sudo_prefix_with_group():
    """
    _sudo_prefix() returns prefix plus -g flag for nonempty group
    """
    eq_(
        _sudo_prefix(user=None, group="foo"),
        "%s -g \"foo\" " % (env.sudo_prefix % env)
    )


def test_sudo_prefix_with_user_and_group():
    """
    _sudo_prefix() returns prefix plus -u and -g for nonempty user and group
    """
    eq_(
        _sudo_prefix(user="foo", group="bar"),
        "%s -u \"foo\" -g \"bar\" " % (env.sudo_prefix % env)
    )


@with_settings(use_shell=True)
def test_shell_wrap():
    prefix = "prefix"
    command = "command"
    for description, shell, sudo_prefix, result in (
        ("shell=True, sudo_prefix=None",
            True, None, '%s "%s"' % (env.shell, command)),
        ("shell=True, sudo_prefix=string",
            True, prefix, prefix + ' %s "%s"' % (env.shell, command)),
        ("shell=False, sudo_prefix=None",
            False, None, command),
        ("shell=False, sudo_prefix=string",
            False, prefix, prefix + " " + command),
    ):
        eq_.description = "_shell_wrap: %s" % description
        yield eq_, _shell_wrap(command, shell_escape=True, shell=shell, sudo_prefix=sudo_prefix), result
        del eq_.description


@with_settings(use_shell=True)
def test_shell_wrap_escapes_command_if_shell_is_true():
    """
    _shell_wrap() escapes given command if shell=True
    """
    cmd = "cd \"Application Support\""
    eq_(
        _shell_wrap(cmd, shell_escape=True, shell=True),
        '%s "%s"' % (env.shell, _shell_escape(cmd))
    )


@with_settings(use_shell=True)
def test_shell_wrap_does_not_escape_command_if_shell_is_true_and_shell_escape_is_false():
    """
    _shell_wrap() does no escaping if shell=True and shell_escape=False
    """
    cmd = "cd \"Application Support\""
    eq_(
        _shell_wrap(cmd, shell_escape=False, shell=True),
        '%s "%s"' % (env.shell, cmd)
    )


def test_shell_wrap_does_not_escape_command_if_shell_is_false():
    """
    _shell_wrap() does no escaping if shell=False
    """
    cmd = "cd \"Application Support\""
    eq_(_shell_wrap(cmd, shell_escape=True, shell=False), cmd)


def test_shell_escape_escapes_doublequotes():
    """
    _shell_escape() escapes double-quotes
    """
    cmd = "cd \"Application Support\""
    eq_(_shell_escape(cmd), 'cd \\"Application Support\\"')


def test_shell_escape_escapes_dollar_signs():
    """
    _shell_escape() escapes dollar signs
    """
    cmd = "cd $HOME"
    eq_(_shell_escape(cmd), 'cd \$HOME')


def test_shell_escape_escapes_backticks():
    """
    _shell_escape() escapes backticks
    """
    cmd = "touch test.pid && kill `cat test.pid`"
    eq_(_shell_escape(cmd), "touch test.pid && kill \`cat test.pid\`")


class TestCombineStderr(FabricTest):
    @server()
    def test_local_none_global_true(self):
        """
        combine_stderr: no kwarg => uses global value (True)
        """
        output.everything = False
        r = run("both_streams")
        # Note: the exact way the streams are jumbled here is an implementation
        # detail of our fake SSH server and may change in the future.
        eq_("ssttddoeurtr", r.stdout)
        eq_(r.stderr, "")

    @server()
    def test_local_none_global_false(self):
        """
        combine_stderr: no kwarg => uses global value (False)
        """
        output.everything = False
        env.combine_stderr = False
        r = run("both_streams")
        eq_("stdout", r.stdout)
        eq_("stderr", r.stderr)

    @server()
    def test_local_true_global_false(self):
        """
        combine_stderr: True kwarg => overrides global False value
        """
        output.everything = False
        env.combine_stderr = False
        r = run("both_streams", combine_stderr=True)
        eq_("ssttddoeurtr", r.stdout)
        eq_(r.stderr, "")

    @server()
    def test_local_false_global_true(self):
        """
        combine_stderr: False kwarg => overrides global True value
        """
        output.everything = False
        env.combine_stderr = True
        r = run("both_streams", combine_stderr=False)
        eq_("stdout", r.stdout)
        eq_("stderr", r.stderr)


class TestQuietAndWarnKwargs(FabricTest):
    @server(responses={'wat': ["", "", 1]})
    def test_quiet_implies_warn_only(self):
        # Would raise an exception if warn_only was False
        eq_(run("wat", quiet=True).failed, True)

    @server()
    @mock_streams('both')
    def test_quiet_implies_hide_everything(self):
        run("ls /", quiet=True)
        eq_(sys.stdout.getvalue(), "")
        eq_(sys.stderr.getvalue(), "")

    @server(responses={'hrm': ["", "", 1]})
    @mock_streams('both')
    def test_warn_only_is_same_as_settings_warn_only(self):
        eq_(run("hrm", warn_only=True).failed, True)

    @server()
    @mock_streams('both')
    def test_warn_only_does_not_imply_hide_everything(self):
        run("ls /simple", warn_only=True)
        assert sys.stdout.getvalue() != ""


class TestMultipleOKReturnCodes(FabricTest):
    @server(responses={'no srsly its ok': ['', '', 1]})
    def test_expand_to_include_1(self):
        with settings(quiet(), ok_ret_codes=[0, 1]):
            eq_(run("no srsly its ok").succeeded, True)


slow_server = server(responses={'slow': ['', '', 0, 3]})
slow = lambda x: slow_server(raises(CommandTimeout)(x))

class TestRun(FabricTest):
    """
    @server-using generic run()/sudo() tests
    """
    @slow
    def test_command_timeout_via_env_var(self):
        env.command_timeout = 2 # timeout after 2 seconds
        with hide('everything'):
            run("slow")

    @slow
    def test_command_timeout_via_kwarg(self):
        with hide('everything'):
            run("slow", timeout=2)

    @slow
    def test_command_timeout_via_env_var_in_sudo(self):
        env.command_timeout = 2 # timeout after 2 seconds
        with hide('everything'):
            sudo("slow")

    @slow
    def test_command_timeout_via_kwarg_of_sudo(self):
        with hide('everything'):
            sudo("slow", timeout=2)


#
# get() and put()
#

class TestFileTransfers(FabricTest):
    #
    # get()
    #
    @server(files={'/home/user/.bashrc': 'bash!'}, home='/home/user')
    def test_get_relative_remote_dir_uses_home(self):
        """
        get('relative/path') should use remote $HOME
        """
        with hide('everything'):
            # Another if-it-doesn't-error-out-it-passed test; meh.
            eq_(get('.bashrc', self.path()), [self.path('.bashrc')])

    @server()
    def test_get_single_file(self):
        """
        get() with a single non-globbed filename
        """
        remote = 'file.txt'
        local = self.path(remote)
        with hide('everything'):
            get(remote, local)
        eq_contents(local, FILES[remote])

    @server(files={'/base/dir with spaces/file': 'stuff!'})
    def test_get_file_from_relative_path_with_spaces(self):
        """
        get('file') should work when the remote path contains spaces
        """
        # from nose.tools import set_trace; set_trace()
        with hide('everything'):
            with cd('/base/dir with spaces'):
                eq_(get('file', self.path()), [self.path('file')])

    @server()
    def test_get_sibling_globs(self):
        """
        get() with globbed files, but no directories
        """
        remotes = ['file.txt', 'file2.txt']
        with hide('everything'):
            get('file*.txt', self.tmpdir)
        for remote in remotes:
            eq_contents(self.path(remote), FILES[remote])

    @server()
    def test_get_single_file_in_folder(self):
        """
        get() a folder containing one file
        """
        remote = 'folder/file3.txt'
        with hide('everything'):
            get('folder', self.tmpdir)
        eq_contents(self.path(remote), FILES[remote])

    @server()
    def test_get_tree(self):
        """
        Download entire tree
        """
        with hide('everything'):
            get('tree', self.tmpdir)
        leaves = filter(lambda x: x[0].startswith('/tree'), FILES.items())
        for path, contents in leaves:
            eq_contents(self.path(path[1:]), contents)

    @server()
    def test_get_tree_with_implicit_local_path(self):
        """
        Download entire tree without specifying a local path
        """
        dirname = env.host_string.replace(':', '-')
        try:
            with hide('everything'):
                get('tree')
            leaves = filter(lambda x: x[0].startswith('/tree'), FILES.items())
            for path, contents in leaves:
                path = os.path.join(dirname, path[1:])
                eq_contents(path, contents)
                os.remove(path)
        # Cleanup
        finally:
            if os.path.exists(dirname):
                shutil.rmtree(dirname)

    @server()
    def test_get_absolute_path_should_save_relative(self):
        """
        get(/x/y) w/ %(path)s should save y, not x/y
        """
        lpath = self.path()
        ltarget = os.path.join(lpath, "%(path)s")
        with hide('everything'):
            get('/tree/subfolder', ltarget)
        assert self.exists_locally(os.path.join(lpath, 'subfolder'))
        assert not self.exists_locally(os.path.join(lpath, 'tree/subfolder'))

    @server()
    def test_path_formatstr_nonrecursively_is_just_filename(self):
        """
        get(x/y/z) nonrecursively w/ %(path)s should save y, not y/z
        """
        lpath = self.path()
        ltarget = os.path.join(lpath, "%(path)s")
        with hide('everything'):
            get('/tree/subfolder/file3.txt', ltarget)
        assert self.exists_locally(os.path.join(lpath, 'file3.txt'))

    @server()
    @mock_streams('stderr')
    def _invalid_file_obj_situations(self, remote_path):
        with settings(hide('running'), warn_only=True):
            get(remote_path, StringIO())
        assert_contains('is a glob or directory', sys.stderr.getvalue())

    def test_glob_and_file_object_invalid(self):
        """
        Remote glob and local file object is invalid
        """
        self._invalid_file_obj_situations('/tree/*')

    def test_directory_and_file_object_invalid(self):
        """
        Remote directory and local file object is invalid
        """
        self._invalid_file_obj_situations('/tree')

    @server()
    def test_get_single_file_absolutely(self):
        """
        get() a single file, using absolute file path
        """
        target = '/etc/apache2/apache2.conf'
        with hide('everything'):
            get(target, self.tmpdir)
        eq_contents(self.path(os.path.basename(target)), FILES[target])

    @server()
    def test_get_file_with_nonexistent_target(self):
        """
        Missing target path on single file download => effectively a rename
        """
        local = self.path('otherfile.txt')
        target = 'file.txt'
        with hide('everything'):
            get(target, local)
        eq_contents(local, FILES[target])

    @server()
    @mock_streams('stderr')
    def test_get_file_with_existing_file_target(self):
        """
        Clobbering existing local file should overwrite, with warning
        """
        local = self.path('target.txt')
        target = 'file.txt'
        with open(local, 'w') as fd:
            fd.write("foo")
        with hide('stdout', 'running'):
            get(target, local)
        assert "%s already exists" % local in sys.stderr.getvalue()
        eq_contents(local, FILES[target])

    @server()
    def test_get_file_to_directory(self):
        """
        Directory as target path should result in joined pathname

        (Yes, this is duplicated in most of the other tests -- but good to have
        a default in case those tests change how they work later!)
        """
        target = 'file.txt'
        with hide('everything'):
            get(target, self.tmpdir)
        eq_contents(self.path(target), FILES[target])

    @server(port=2200)
    @server(port=2201)
    def test_get_from_multiple_servers(self):
        ports = [2200, 2201]
        hosts = map(lambda x: '127.0.0.1:%s' % x, ports)
        with settings(all_hosts=hosts):
            for port in ports:
                with settings(
                    hide('everything'), host_string='127.0.0.1:%s' % port
                ):
                    tmp = self.path('')
                    local_path = os.path.join(tmp, "%(host)s", "%(path)s")
                    # Top level file
                    path = 'file.txt'
                    get(path, local_path)
                    assert self.exists_locally(os.path.join(
                        tmp, "127.0.0.1-%s" % port, path
                    ))
                    # Nested file
                    get('tree/subfolder/file3.txt', local_path)
                    assert self.exists_locally(os.path.join(
                        tmp, "127.0.0.1-%s" % port, 'file3.txt'
                    ))

    @server()
    def test_get_from_empty_directory_uses_cwd(self):
        """
        get() expands empty remote arg to remote cwd
        """
        with hide('everything'):
            get('', self.tmpdir)
        # Spot checks -- though it should've downloaded the entirety of
        # server.FILES.
        for x in "file.txt file2.txt tree/file1.txt".split():
            assert os.path.exists(os.path.join(self.tmpdir, x))

    @server()
    def _get_to_cwd(self, arg):
        path = 'file.txt'
        with hide('everything'):
            get(path, arg)
        host_dir = os.path.join(
            os.getcwd(),
            env.host_string.replace(':', '-'),
        )
        target = os.path.join(host_dir, path)
        try:
            assert os.path.exists(target)
        # Clean up, since we're not using our tmpdir
        finally:
            shutil.rmtree(host_dir)

    def test_get_to_empty_string_uses_default_format_string(self):
        """
        get() expands empty local arg to local cwd + host + file
        """
        self._get_to_cwd('')

    def test_get_to_None_uses_default_format_string(self):
        """
        get() expands None local arg to local cwd + host + file
        """
        self._get_to_cwd(None)

    @server()
    def test_get_should_accept_file_like_objects(self):
        """
        get()'s local_path arg should take file-like objects too
        """
        fake_file = StringIO()
        target = '/file.txt'
        with hide('everything'):
            get(target, fake_file)
        eq_(fake_file.getvalue(), FILES[target])

    @server()
    def test_get_interpolation_without_host(self):
        """
        local formatting should work w/o use of %(host)s when run on one host
        """
        with hide('everything'):
            tmp = self.path('')
            # dirname, basename
            local_path = tmp + "/%(dirname)s/foo/%(basename)s"
            get('/folder/file3.txt', local_path)
            assert self.exists_locally(tmp + "foo/file3.txt")
            # path
            local_path = tmp + "bar/%(path)s"
            get('/folder/file3.txt', local_path)
            assert self.exists_locally(tmp + "bar/file3.txt")

    @server()
    def test_get_returns_list_of_local_paths(self):
        """
        get() should return an iterable of the local files it created.
        """
        d = self.path()
        with hide('everything'):
            retval = get('tree', d)
        files = ['file1.txt', 'file2.txt', 'subfolder/file3.txt']
        eq_(map(lambda x: os.path.join(d, 'tree', x), files), retval)

    @server()
    def test_get_returns_none_for_stringio(self):
        """
        get() should return None if local_path is a StringIO
        """
        with hide('everything'):
            eq_([], get('/file.txt', StringIO()))

    @server()
    def test_get_return_value_failed_attribute(self):
        """
        get()'s return value should indicate any paths which failed to
        download.
        """
        with settings(hide('everything'), warn_only=True):
            retval = get('/doesnt/exist', self.path())
        eq_(['/doesnt/exist'], retval.failed)
        assert not retval.succeeded

    @server()
    def test_get_should_not_use_windows_slashes_in_remote_paths(self):
        """
        sftp.glob() should always use Unix-style slashes.
        """
        with hide('everything'):
            path = "/tree/file1.txt"
            sftp = SFTP(env.host_string)
            eq_(sftp.glob(path), [path])

    #
    # put()
    #

    @server()
    def test_put_file_to_existing_directory(self):
        """
        put() a single file into an existing remote directory
        """
        text = "foo!"
        local = self.mkfile('foo.txt', text)
        local2 = self.path('foo2.txt')
        with hide('everything'):
            put(local, '/')
            get('/foo.txt', local2)
        eq_contents(local2, text)

    @server()
    def test_put_to_empty_directory_uses_cwd(self):
        """
        put() expands empty remote arg to remote cwd

        Not a terribly sharp test -- we just get() with a relative path and are
        testing to make sure they match up -- but should still suffice.
        """
        text = "foo!"
        local = self.path('foo.txt')
        local2 = self.path('foo2.txt')
        with open(local, 'w') as fd:
            fd.write(text)
        with hide('everything'):
            put(local)
            get('foo.txt', local2)
        eq_contents(local2, text)

    @server()
    def test_put_from_empty_directory_uses_cwd(self):
        """
        put() expands empty local arg to local cwd
        """
        text = 'foo!'
        # Don't use the current cwd since that's a whole lotta files to upload
        old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        # Write out file right here
        with open('file.txt', 'w') as fd:
            fd.write(text)
        with hide('everything'):
            # Put our cwd (which should only contain the file we just created)
            put('', '/')
            # Get it back under a new name (noting that when we use a truly
            # empty put() local call, it makes a directory remotely with the
            # name of the cwd)
            remote = os.path.join(os.path.basename(self.tmpdir), 'file.txt')
            get(remote, 'file2.txt')
        # Compare for sanity test
        eq_contents('file2.txt', text)
        # Restore cwd
        os.chdir(old_cwd)

    @server()
    def test_put_should_accept_file_like_objects(self):
        """
        put()'s local_path arg should take file-like objects too
        """
        local = self.path('whatever')
        fake_file = StringIO()
        fake_file.write("testing file-like objects in put()")
        pointer = fake_file.tell()
        target = '/new_file.txt'
        with hide('everything'):
            put(fake_file, target)
            get(target, local)
        eq_contents(local, fake_file.getvalue())
        # Sanity test of file pointer
        eq_(pointer, fake_file.tell())

    @server()
    @raises(ValueError)
    def test_put_should_raise_exception_for_nonexistent_local_path(self):
        """
        put(nonexistent_file) should raise a ValueError
        """
        put('thisfiledoesnotexist', '/tmp')

    @server()
    def test_put_returns_list_of_remote_paths(self):
        """
        put() should return an iterable of the remote files it created.
        """
        p = 'uploaded.txt'
        f = self.path(p)
        with open(f, 'w') as fd:
            fd.write("contents")
        with hide('everything'):
            retval = put(f, p)
        eq_(retval, [p])

    @server()
    def test_put_returns_list_of_remote_paths_with_stringio(self):
        """
        put() should return a one-item iterable when uploading from a StringIO
        """
        f = 'uploaded.txt'
        with hide('everything'):
            eq_(put(StringIO('contents'), f), [f])

    @server()
    def test_put_return_value_failed_attribute(self):
        """
        put()'s return value should indicate any paths which failed to upload.
        """
        with settings(hide('everything'), warn_only=True):
            f = StringIO('contents')
            retval = put(f, '/nonexistent/directory/structure')
        eq_(["<StringIO>"], retval.failed)
        assert not retval.succeeded

    @server()
    def test_put_sends_all_files_with_glob(self):
        """
        put() should send all items that match a glob.
        """
        paths = ['foo1.txt', 'foo2.txt']
        glob = 'foo*.txt'
        remote_directory = '/'
        for path in paths:
            self.mkfile(path, 'foo!')

        with hide('everything'):
            retval = put(self.path(glob), remote_directory)
        eq_(sorted(retval), sorted([remote_directory + path for path in paths]))

    @server()
    def test_put_sends_correct_file_with_globbing_off(self):
        """
        put() should send a file with a glob pattern in the path, when globbing disabled.
        """
        text = "globbed!"
        local = self.mkfile('foo[bar].txt', text)
        local2 = self.path('foo2.txt')
        with hide('everything'):
            put(local, '/', use_glob=False)
            get('/foo[bar].txt', local2)
        eq_contents(local2, text)


    #
    # Interactions with cd()
    #

    @server()
    def test_cd_should_apply_to_put(self):
        """
        put() should honor env.cwd for relative remote paths
        """
        f = 'test.txt'
        d = '/empty_folder'
        local = self.path(f)
        with open(local, 'w') as fd:
            fd.write('test')
        with nested(cd(d), hide('everything')):
            put(local, f)
        assert self.exists_remotely('%s/%s' % (d, f))

    @server(files={'/tmp/test.txt': 'test'})
    def test_cd_should_apply_to_get(self):
        """
        get() should honor env.cwd for relative remote paths
        """
        local = self.path('test.txt')
        with nested(cd('/tmp'), hide('everything')):
            get('test.txt', local)
        assert os.path.exists(local)

    @server()
    def test_cd_should_not_apply_to_absolute_put(self):
        """
        put() should not prepend env.cwd to absolute remote paths
        """
        local = self.path('test.txt')
        with open(local, 'w') as fd:
            fd.write('test')
        with nested(cd('/tmp'), hide('everything')):
            put(local, '/test.txt')
        assert not self.exists_remotely('/tmp/test.txt')
        assert self.exists_remotely('/test.txt')

    @server(files={'/test.txt': 'test'})
    def test_cd_should_not_apply_to_absolute_get(self):
        """
        get() should not prepend env.cwd to absolute remote paths
        """
        local = self.path('test.txt')
        with nested(cd('/tmp'), hide('everything')):
            get('/test.txt', local)
        assert os.path.exists(local)

    @server()
    def test_lcd_should_apply_to_put(self):
        """
        lcd() should apply to put()'s local_path argument
        """
        f = 'lcd_put_test.txt'
        d = 'subdir'
        local = self.path(d, f)
        os.makedirs(os.path.dirname(local))
        with open(local, 'w') as fd:
            fd.write("contents")
        with nested(lcd(self.path(d)), hide('everything')):
            put(f, '/')
        assert self.exists_remotely('/%s' % f)

    @server()
    def test_lcd_should_apply_to_get(self):
        """
        lcd() should apply to get()'s local_path argument
        """
        d = self.path('subdir')
        f = 'file.txt'
        with nested(lcd(d), hide('everything')):
            get(f, f)
        assert self.exists_locally(os.path.join(d, f))

    @server()
    @mock_streams('stdout')
    def test_stringio_without_name(self):
        file_obj = StringIO(u'test data')
        put(file_obj, '/')
        assert re.search('<file obj>', sys.stdout.getvalue())

    @server()
    @mock_streams('stdout')
    def test_stringio_with_name(self):
        """If a file object (StringIO) has a name attribute, use that in output"""
        file_obj = StringIO(u'test data')
        file_obj.name = 'Test StringIO Object'
        put(file_obj, '/')
        assert re.search(file_obj.name, sys.stdout.getvalue())


#
# local()
#

# TODO: figure out how to mock subprocess, if it's even possible.
# For now, simply test to make sure local() does not raise exceptions with
# various settings enabled/disabled.

def test_local_output_and_capture():
    for capture in (True, False):
        for stdout in (True, False):
            for stderr in (True, False):
                hides, shows = ['running'], []
                if stdout:
                    hides.append('stdout')
                else:
                    shows.append('stdout')
                if stderr:
                    hides.append('stderr')
                else:
                    shows.append('stderr')
                with nested(hide(*hides), show(*shows)):
                    d = "local(): capture: %r, stdout: %r, stderr: %r" % (
                        capture, stdout, stderr
                    )
                    local.description = d
                    yield local, "echo 'foo' >/dev/null", capture
                    del local.description


class TestRunSudoReturnValues(FabricTest):
    @server()
    def test_returns_command_given(self):
        """
        run("foo").command == foo
        """
        with hide('everything'):
            eq_(run("ls /").command, "ls /")

    @server()
    def test_returns_fully_wrapped_command(self):
        """
        run("foo").real_command involves env.shell + etc
        """
        # FabTest turns use_shell off, we must reactivate it.
        # Doing so will cause a failure: server's default command list assumes
        # it's off, we're not testing actual wrapping here so we don't really
        # care. Just warn_only it.
        with settings(hide('everything'), warn_only=True, use_shell=True):
            # Slightly flexible test, we're not testing the actual construction
            # here, just that this attribute exists.
            ok_(env.shell in run("ls /").real_command)

########NEW FILE########
__FILENAME__ = test_parallel
from __future__ import with_statement

from fabric.api import run, parallel, env, hide, execute, settings

from utils import FabricTest, eq_, aborts, mock_streams
from server import server, RESPONSES, USER, HOST, PORT

# TODO: move this into test_tasks? meh.

class OhNoesException(Exception): pass


class TestParallel(FabricTest):
    @server()
    @parallel
    def test_parallel(self):
        """
        Want to do a simple call and respond
        """
        env.pool_size = 10
        cmd = "ls /simple"
        with hide('everything'):
            eq_(run(cmd), RESPONSES[cmd])

    @server(port=2200)
    @server(port=2201)
    def test_env_host_no_user_or_port(self):
        """
        Ensure env.host doesn't get user/port parts when parallel
        """
        @parallel
        def _task():
            run("ls /simple")
            assert USER not in env.host
            assert str(PORT) not in env.host

        host_string = '%s@%s:%%s' % (USER, HOST)
        with hide('everything'):
            execute(_task, hosts=[host_string % 2200, host_string % 2201])

    @server(port=2200)
    @server(port=2201)
    @aborts
    def test_parallel_failures_abort(self):
        with hide('everything'):
            host1 = '127.0.0.1:2200'
            host2 = '127.0.0.1:2201'

            @parallel
            def mytask():
                run("ls /")
                if env.host_string == host2:
                    raise OhNoesException
            
            execute(mytask, hosts=[host1, host2])

    @server(port=2200)
    @server(port=2201)
    @mock_streams('stderr') # To hide the traceback for now
    def test_parallel_failures_honor_warn_only(self):
        with hide('everything'):
            host1 = '127.0.0.1:2200'
            host2 = '127.0.0.1:2201'

            @parallel
            def mytask():
                run("ls /")
                if env.host_string == host2:
                    raise OhNoesException

            with settings(warn_only=True):
                result = execute(mytask, hosts=[host1, host2])
            eq_(result[host1], None)
            assert isinstance(result[host2], OhNoesException)


    @server(port=2200)
    @server(port=2201)
    def test_parallel_implies_linewise(self):
        host1 = '127.0.0.1:2200'
        host2 = '127.0.0.1:2201'

        assert not env.linewise

        @parallel
        def mytask():
            run("ls /")
            return env.linewise

        with hide('everything'):
            result = execute(mytask, hosts=[host1, host2])
        eq_(result[host1], True)
        eq_(result[host2], True)

########NEW FILE########
__FILENAME__ = test_project
import unittest
import os

import fudge
from fudge.inspector import arg

from fabric.contrib import project


class UploadProjectTestCase(unittest.TestCase):
    """Test case for :func: `fabric.contrib.project.upload_project`."""

    fake_tmp = "testtempfolder"


    def setUp(self):
        fudge.clear_expectations()

        # We need to mock out run, local, and put

        self.fake_run = fudge.Fake('project.run', callable=True)
        self.patched_run = fudge.patch_object(
                               project,
                               'run',
                               self.fake_run
                           )

        self.fake_local = fudge.Fake('local', callable=True)
        self.patched_local = fudge.patch_object(
                                 project,
                                 'local',
                                 self.fake_local
                             )

        self.fake_put = fudge.Fake('put', callable=True)
        self.patched_put = fudge.patch_object(
                               project,
                               'put',
                               self.fake_put
                           )

        # We don't want to create temp folders
        self.fake_mkdtemp = fudge.Fake(
                                'mkdtemp',
                                expect_call=True
                            ).returns(self.fake_tmp)
        self.patched_mkdtemp = fudge.patch_object(
                                   project,
                                   'mkdtemp',
                                   self.fake_mkdtemp
                               )


    def tearDown(self):
        self.patched_run.restore()
        self.patched_local.restore()
        self.patched_put.restore()

        fudge.clear_expectations()


    @fudge.with_fakes
    def test_temp_folder_is_used(self):
        """A unique temp folder is used for creating the archive to upload."""

        # Exercise
        project.upload_project()


    @fudge.with_fakes
    def test_project_is_archived_locally(self):
        """The project should be archived locally before being uploaded."""

        # local() is called more than once so we need an extra next_call()
        # otherwise fudge compares the args to the last call to local()
        self.fake_local.with_args(arg.startswith("tar -czf")).next_call()

        # Exercise
        project.upload_project()


    @fudge.with_fakes
    def test_current_directory_is_uploaded_by_default(self):
        """By default the project uploaded is the current working directory."""

        cwd_path, cwd_name = os.path.split(os.getcwd())

        # local() is called more than once so we need an extra next_call()
        # otherwise fudge compares the args to the last call to local()
        self.fake_local.with_args(
            arg.endswith("-C %s %s" % (cwd_path, cwd_name))
        ).next_call()

        # Exercise
        project.upload_project()


    @fudge.with_fakes
    def test_path_to_local_project_can_be_specified(self):
        """It should be possible to specify which local folder to upload."""

        project_path = "path/to/my/project"

        # local() is called more than once so we need an extra next_call()
        # otherwise fudge compares the args to the last call to local()
        self.fake_local.with_args(
            arg.endswith("-C %s %s" % os.path.split(project_path))
        ).next_call()

        # Exercise
        project.upload_project(local_dir=project_path)


    @fudge.with_fakes
    def test_path_to_local_project_can_end_in_separator(self):
        """A local path ending in a separator should be handled correctly."""

        project_path = "path/to/my"
        base = "project"

        # local() is called more than once so we need an extra next_call()
        # otherwise fudge compares the args to the last call to local()
        self.fake_local.with_args(
            arg.endswith("-C %s %s" % (project_path, base))
        ).next_call()

        # Exercise
        project.upload_project(local_dir="%s/%s/" % (project_path, base))


    @fudge.with_fakes
    def test_default_remote_folder_is_home(self):
        """Project is uploaded to remote home by default."""

        local_dir = "folder"

        # local() is called more than once so we need an extra next_call()
        # otherwise fudge compares the args to the last call to local()
        self.fake_put.with_args(
            "%s/folder.tar.gz" % self.fake_tmp, "folder.tar.gz", use_sudo=False
        ).next_call()

        # Exercise
        project.upload_project(local_dir=local_dir)

    @fudge.with_fakes
    def test_path_to_remote_folder_can_be_specified(self):
        """It should be possible to specify which local folder to upload to."""

        local_dir = "folder"
        remote_path = "path/to/remote/folder"

        # local() is called more than once so we need an extra next_call()
        # otherwise fudge compares the args to the last call to local()
        self.fake_put.with_args(
            "%s/folder.tar.gz" % self.fake_tmp, "%s/folder.tar.gz" % remote_path, use_sudo=False
        ).next_call()

        # Exercise
        project.upload_project(local_dir=local_dir, remote_dir=remote_path)


########NEW FILE########
__FILENAME__ = test_server
"""
Tests for the test server itself.

Not intended to be run by the greater test suite, only by specifically
targeting it on the command-line. Rationale: not really testing Fabric itself,
no need to pollute Fab's own test suite. (Yes, if these tests fail, it's likely
that the Fabric tests using the test server may also have issues, but still.)
"""
__test__ = False

from nose.tools import eq_, ok_

from fabric.network import ssh

from server import FakeSFTPServer


class AttrHolder(object):
    pass


def test_list_folder():
    for desc, file_map, arg, expected in (
        (
            "Single file",
            {'file.txt': 'contents'},
            '',
            ['file.txt']
        ),
        (
            "Single absolute file",
            {'/file.txt': 'contents'},
            '/',
            ['file.txt']
        ),
        (
            "Multiple files",
            {'file1.txt': 'contents', 'file2.txt': 'contents2'},
            '',
            ['file1.txt', 'file2.txt']
        ),
        (
            "Single empty folder",
            {'folder': None},
            '',
            ['folder']
        ),
        (
            "Empty subfolders",
            {'folder': None, 'folder/subfolder': None},
            '',
            ['folder']
        ),
        (
            "Non-empty sub-subfolder",
            {'folder/subfolder/subfolder2/file.txt': 'contents'},
            "folder/subfolder/subfolder2",
            ['file.txt']
        ),
        (
            "Mixed files, folders empty and non-empty, in homedir",
            {
                'file.txt': 'contents',
                'file2.txt': 'contents2',
                'folder/file3.txt': 'contents3',
                'empty_folder': None
            },
            '',
            ['file.txt', 'file2.txt', 'folder', 'empty_folder']
        ),
        (
            "Mixed files, folders empty and non-empty, in subdir",
            {
                'file.txt': 'contents',
                'file2.txt': 'contents2',
                'folder/file3.txt': 'contents3',
                'folder/subfolder/file4.txt': 'contents4',
                'empty_folder': None
            },
            "folder",
            ['file3.txt', 'subfolder']
        ),
    ):
        # Pass in fake server obj. (Can't easily clean up API to be more
        # testable since it's all implementing 'ssh' interface stuff.)
        server = AttrHolder()
        server.files = file_map
        interface = FakeSFTPServer(server)
        results = interface.list_folder(arg)
        # In this particular suite of tests, all results should be a file list,
        # not "no files found"
        ok_(results != ssh.SFTP_NO_SUCH_FILE)
        # Grab filename from SFTPAttribute objects in result
        output = map(lambda x: x.filename, results)
        # Yield test generator
        eq_.description = "list_folder: %s" % desc
        yield eq_, set(expected), set(output)
        del eq_.description

########NEW FILE########
__FILENAME__ = test_state
from nose.tools import eq_

from fabric.state import _AliasDict


def test_dict_aliasing():
    """
    Assigning values to aliases updates aliased keys
    """
    ad = _AliasDict(
        {'bar': False, 'biz': True, 'baz': False},
        aliases={'foo': ['bar', 'biz', 'baz']}
    )
    # Before
    eq_(ad['bar'], False)
    eq_(ad['biz'], True)
    eq_(ad['baz'], False)
    # Change
    ad['foo'] = True
    # After
    eq_(ad['bar'], True)
    eq_(ad['biz'], True)
    eq_(ad['baz'], True)


def test_nested_dict_aliasing():
    """
    Aliases can be nested
    """
    ad = _AliasDict(
        {'bar': False, 'biz': True},
        aliases={'foo': ['bar', 'nested'], 'nested': ['biz']}
    )
    # Before
    eq_(ad['bar'], False)
    eq_(ad['biz'], True)
    # Change
    ad['foo'] = True
    # After
    eq_(ad['bar'], True)
    eq_(ad['biz'], True)


def test_dict_alias_expansion():
    """
    Alias expansion
    """
    ad = _AliasDict(
        {'bar': False, 'biz': True},
        aliases={'foo': ['bar', 'nested'], 'nested': ['biz']}
    )
    eq_(ad.expand_aliases(['foo']), ['bar', 'biz'])

########NEW FILE########
__FILENAME__ = test_tasks
from __future__ import with_statement

from contextlib import contextmanager
from fudge import Fake, patched_context, with_fakes
import unittest
from nose.tools import eq_, raises, ok_
import random
import sys

import fabric
from fabric.tasks import WrappedCallableTask, execute, Task, get_task_details
from fabric.main import display_command
from fabric.api import run, env, settings, hosts, roles, hide, parallel, task
from fabric.network import from_dict
from fabric.exceptions import NetworkError

from utils import eq_, FabricTest, aborts, mock_streams
from server import server


def test_base_task_provides_undefined_name():
    task = Task()
    eq_("undefined", task.name)

@raises(NotImplementedError)
def test_base_task_raises_exception_on_call_to_run():
    task = Task()
    task.run()

class TestWrappedCallableTask(unittest.TestCase):
    def test_passes_unused_args_to_parent(self):
        args = [i for i in range(random.randint(1, 10))]

        def foo(): pass
        try:
            task = WrappedCallableTask(foo, *args)
        except TypeError:
            msg = "__init__ raised a TypeError, meaning args weren't handled"
            self.fail(msg)

    def test_passes_unused_kwargs_to_parent(self):
        random_range = range(random.randint(1, 10))
        kwargs = dict([("key_%s" % i, i) for i in random_range])

        def foo(): pass
        try:
            task = WrappedCallableTask(foo, **kwargs)
        except TypeError:
            self.fail(
                "__init__ raised a TypeError, meaning kwargs weren't handled")

    def test_allows_any_number_of_args(self):
        args = [i for i in range(random.randint(0, 10))]
        def foo(): pass
        task = WrappedCallableTask(foo, *args)

    def test_allows_any_number_of_kwargs(self):
        kwargs = dict([("key%d" % i, i) for i in range(random.randint(0, 10))])
        def foo(): pass
        task = WrappedCallableTask(foo, **kwargs)

    def test_run_is_wrapped_callable(self):
        def foo(): pass
        task = WrappedCallableTask(foo)
        eq_(task.wrapped, foo)

    def test_name_is_the_name_of_the_wrapped_callable(self):
        def foo(): pass
        foo.__name__ = "random_name_%d" % random.randint(1000, 2000)
        task = WrappedCallableTask(foo)
        eq_(task.name, foo.__name__)

    def test_name_can_be_overridden(self):
        def foo(): pass
        eq_(WrappedCallableTask(foo).name, 'foo')
        eq_(WrappedCallableTask(foo, name='notfoo').name, 'notfoo')

    def test_reads_double_under_doc_from_callable(self):
        def foo(): pass
        foo.__doc__ = "Some random __doc__: %d" % random.randint(1000, 2000)
        task = WrappedCallableTask(foo)
        eq_(task.__doc__, foo.__doc__)

    def test_dispatches_to_wrapped_callable_on_run(self):
        random_value = "some random value %d" % random.randint(1000, 2000)
        def foo(): return random_value
        task = WrappedCallableTask(foo)
        eq_(random_value, task())

    def test_passes_all_regular_args_to_run(self):
        def foo(*args): return args
        random_args = tuple(
            [random.randint(1000, 2000) for i in range(random.randint(1, 5))]
        )
        task = WrappedCallableTask(foo)
        eq_(random_args, task(*random_args))

    def test_passes_all_keyword_args_to_run(self):
        def foo(**kwargs): return kwargs
        random_kwargs = {}
        for i in range(random.randint(1, 5)):
            random_key = ("foo", "bar", "baz", "foobar", "barfoo")[i]
            random_kwargs[random_key] = random.randint(1000, 2000)
        task = WrappedCallableTask(foo)
        eq_(random_kwargs, task(**random_kwargs))

    def test_calling_the_object_is_the_same_as_run(self):
        random_return = random.randint(1000, 2000)
        def foo(): return random_return
        task = WrappedCallableTask(foo)
        eq_(task(), task.run())


class TestTask(unittest.TestCase):
    def test_takes_an_alias_kwarg_and_wraps_it_in_aliases_list(self):
        random_alias = "alias_%d" % random.randint(100, 200)
        task = Task(alias=random_alias)
        self.assertTrue(random_alias in task.aliases)

    def test_aliases_are_set_based_on_provided_aliases(self):
        aliases = ["a_%d" % i for i in range(random.randint(1, 10))]
        task = Task(aliases=aliases)
        self.assertTrue(all([a in task.aliases for a in aliases]))

    def test_aliases_are_None_by_default(self):
        task = Task()
        self.assertTrue(task.aliases is None)


# Reminder: decorator syntax, e.g.:
#     @foo
#     def bar():...
#
# is semantically equivalent to:
#     def bar():...
#     bar = foo(bar)
#
# this simplifies testing :)

def test_decorator_incompatibility_on_task():
    from fabric.decorators import task, hosts, runs_once, roles
    def foo(): return "foo"
    foo = task(foo)

    # since we aren't setting foo to be the newly decorated thing, its cool
    hosts('me@localhost')(foo)
    runs_once(foo)
    roles('www')(foo)

def test_decorator_closure_hiding():
    """
    @task should not accidentally destroy decorated attributes from @hosts/etc
    """
    from fabric.decorators import task, hosts
    def foo():
        print(env.host_string)
    foo = task(hosts("me@localhost")(foo))
    eq_(["me@localhost"], foo.hosts)



#
# execute()
#

def dict_contains(superset, subset):
    """
    Assert that all key/val pairs in dict 'subset' also exist in 'superset'
    """
    for key, value in subset.iteritems():
        ok_(key in superset)
        eq_(superset[key], value)


class TestExecute(FabricTest):
    @with_fakes
    def test_calls_task_function_objects(self):
        """
        should execute the passed-in function object
        """
        execute(Fake(callable=True, expect_call=True))

    @with_fakes
    def test_should_look_up_task_name(self):
        """
        should also be able to handle task name strings
        """
        name = 'task1'
        commands = {name: Fake(callable=True, expect_call=True)}
        with patched_context(fabric.state, 'commands', commands):
            execute(name)

    @with_fakes
    def test_should_handle_name_of_Task_object(self):
        """
        handle corner case of Task object referrred to by name
        """
        name = 'task2'
        class MyTask(Task):
            run = Fake(callable=True, expect_call=True)
        mytask = MyTask()
        mytask.name = name
        commands = {name: mytask}
        with patched_context(fabric.state, 'commands', commands):
            execute(name)

    @aborts
    def test_should_abort_if_task_name_not_found(self):
        """
        should abort if given an invalid task name
        """
        execute('thisisnotavalidtaskname')

    @with_fakes
    def test_should_pass_through_args_kwargs(self):
        """
        should pass in any additional args, kwargs to the given task.
        """
        task = (
            Fake(callable=True, expect_call=True)
            .with_args('foo', biz='baz')
        )
        execute(task, 'foo', biz='baz')

    @with_fakes
    def test_should_honor_hosts_kwarg(self):
        """
        should use hosts kwarg to set run list
        """
        # Make two full copies of a host list
        hostlist = ['a', 'b', 'c']
        hosts = hostlist[:]
        # Side-effect which asserts the value of env.host_string when it runs
        def host_string():
            eq_(env.host_string, hostlist.pop(0))
        task = Fake(callable=True, expect_call=True).calls(host_string)
        with hide('everything'):
            execute(task, hosts=hosts)

    def test_should_honor_hosts_decorator(self):
        """
        should honor @hosts on passed-in task objects
        """
        # Make two full copies of a host list
        hostlist = ['a', 'b', 'c']
        @hosts(*hostlist[:])
        def task():
            eq_(env.host_string, hostlist.pop(0))
        with hide('running'):
            execute(task)

    def test_should_honor_roles_decorator(self):
        """
        should honor @roles on passed-in task objects
        """
        # Make two full copies of a host list
        roledefs = {'role1': ['a', 'b', 'c']}
        role_copy = roledefs['role1'][:]
        @roles('role1')
        def task():
            eq_(env.host_string, role_copy.pop(0))
        with settings(hide('running'), roledefs=roledefs):
            execute(task)

    @with_fakes
    def test_should_set_env_command_to_string_arg(self):
        """
        should set env.command to any string arg, if given
        """
        name = "foo"
        def command():
            eq_(env.command, name)
        task = Fake(callable=True, expect_call=True).calls(command)
        with patched_context(fabric.state, 'commands', {name: task}):
            execute(name)

    @with_fakes
    def test_should_set_env_command_to_name_attr(self):
        """
        should set env.command to TaskSubclass.name if possible
        """
        name = "foo"
        def command():
            eq_(env.command, name)
        task = (
            Fake(callable=True, expect_call=True)
            .has_attr(name=name)
            .calls(command)
        )
        execute(task)

    @with_fakes
    def test_should_set_all_hosts(self):
        """
        should set env.all_hosts to its derived host list
        """
        hosts = ['a', 'b']
        roledefs = {'r1': ['c', 'd']}
        roles = ['r1']
        exclude_hosts = ['a']
        def command():
            eq_(set(env.all_hosts), set(['b', 'c', 'd']))
        task = Fake(callable=True, expect_call=True).calls(command)
        with settings(hide('everything'), roledefs=roledefs):
            execute(
                task, hosts=hosts, roles=roles, exclude_hosts=exclude_hosts
            )

    @mock_streams('stdout')
    def test_should_print_executing_line_per_host(self):
        """
        should print "Executing" line once per host
        """
        def task():
            pass
        execute(task, hosts=['host1', 'host2'])
        eq_(sys.stdout.getvalue(), """[host1] Executing task 'task'
[host2] Executing task 'task'
""")

    @mock_streams('stdout')
    def test_should_not_print_executing_line_for_singletons(self):
        """
        should not print "Executing" line for non-networked tasks
        """
        def task():
            pass
        with settings(hosts=[]): # protect against really odd test bleed :(
            execute(task)
        eq_(sys.stdout.getvalue(), "")

    def test_should_return_dict_for_base_case(self):
        """
        Non-network-related tasks should return a dict w/ special key
        """
        def task():
            return "foo"
        eq_(execute(task), {'<local-only>': 'foo'})

    @server(port=2200)
    @server(port=2201)
    def test_should_return_dict_for_serial_use_case(self):
        """
        Networked but serial tasks should return per-host-string dict
        """
        ports = [2200, 2201]
        hosts = map(lambda x: '127.0.0.1:%s' % x, ports)
        def task():
            run("ls /simple")
            return "foo"
        with hide('everything'):
            eq_(execute(task, hosts=hosts), {
                '127.0.0.1:2200': 'foo',
                '127.0.0.1:2201': 'foo'
            })

    @server()
    def test_should_preserve_None_for_non_returning_tasks(self):
        """
        Tasks which don't return anything should still show up in the dict
        """
        def local_task():
            pass
        def remote_task():
            with hide('everything'):
                run("ls /simple")
        eq_(execute(local_task), {'<local-only>': None})
        with hide('everything'):
            eq_(
                execute(remote_task, hosts=[env.host_string]),
                {env.host_string: None}
            )

    def test_should_use_sentinel_for_tasks_that_errored(self):
        """
        Tasks which errored but didn't abort should contain an eg NetworkError
        """
        def task():
            run("whoops")
        host_string = 'localhost:1234'
        with settings(hide('everything'), skip_bad_hosts=True):
            retval = execute(task, hosts=[host_string])
        assert isinstance(retval[host_string], NetworkError)

    @server(port=2200)
    @server(port=2201)
    def test_parallel_return_values(self):
        """
        Parallel mode should still return values as in serial mode
        """
        @parallel
        @hosts('127.0.0.1:2200', '127.0.0.1:2201')
        def task():
            run("ls /simple")
            return env.host_string.split(':')[1]
        with hide('everything'):
            retval = execute(task)
        eq_(retval, {'127.0.0.1:2200': '2200', '127.0.0.1:2201': '2201'})

    @with_fakes
    def test_should_work_with_Task_subclasses(self):
        """
        should work for Task subclasses, not just WrappedCallableTask
        """
        class MyTask(Task):
            name = "mytask"
            run = Fake(callable=True, expect_call=True)
        mytask = MyTask()
        execute(mytask)


class TestExecuteEnvInteractions(FabricTest):
    def set_network(self):
        # Don't update env.host/host_string/etc
        pass

    @server(port=2200)
    @server(port=2201)
    def test_should_not_mutate_its_own_env_vars(self):
        """
        internal env changes should not bleed out, but task env changes should
        """
        # Task that uses a handful of features which involve env vars
        @parallel
        @hosts('username@127.0.0.1:2200', 'username@127.0.0.1:2201')
        def mytask():
            run("ls /simple")
        # Pre-assertions
        assertions = {
            'parallel': False,
            'all_hosts': [],
            'host': None,
            'hosts': [],
            'host_string': None
        }
        for key, value in assertions.items():
            eq_(env[key], value)
        # Run
        with hide('everything'):
            result = execute(mytask)
        eq_(len(result), 2)
        # Post-assertions
        for key, value in assertions.items():
            eq_(env[key], value)

    @server()
    def test_should_allow_task_to_modify_env_vars(self):
        @hosts('username@127.0.0.1:2200')
        def mytask():
            run("ls /simple")
            env.foo = "bar"
        with hide('everything'):
            execute(mytask)
        eq_(env.foo, "bar")
        eq_(env.host_string, None)


class TestTaskDetails(unittest.TestCase):
    def test_old_style_task_with_default_args(self):
        def task_old_style(arg1, arg2, arg3=None, arg4='yes'):
            '''Docstring'''
        details = get_task_details(task_old_style)
        eq_("Docstring\n"
            "Arguments: arg1, arg2, arg3=None, arg4='yes'",
            details)

    def test_old_style_task_without_default_args(self):
        def task_old_style(arg1, arg2):
            '''Docstring'''
        details = get_task_details(task_old_style)
        eq_("Docstring\n"
            "Arguments: arg1, arg2",
            details)

    def test_old_style_task_without_args(self):
        def task_old_style():
            '''Docstring'''
        details = get_task_details(task_old_style)
        eq_("Docstring\n"
            "Arguments: ",
            details)

    def test_decorated_task(self):
        @task
        def decorated_task(arg1):
            '''Docstring'''
        eq_("Docstring\n"
            "Arguments: arg1",
            decorated_task.__details__())

    def test_subclassed_task(self):
        class SpecificTask(Task):
            def run(self, arg1, arg2, arg3):
                '''Docstring'''
        eq_("Docstring\n"
            "Arguments: self, arg1, arg2, arg3",
            SpecificTask().__details__())

    @mock_streams('stdout')
    def test_multiline_docstring_indented_correctly(self):
        def mytask(arg1):
            """
            This is a multi line docstring.

            For reals.
            """
        try:
            with patched_context(fabric.state, 'commands', {'mytask': mytask}):
                display_command('mytask')
        except SystemExit: # ugh
            pass
        eq_(
            sys.stdout.getvalue(),
"""Displaying detailed information for task 'mytask':

    This is a multi line docstring.
    
    For reals.
    
    Arguments: arg1

"""
        )

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import with_statement

import sys
from unittest import TestCase

from fudge import Fake, patched_context, with_fakes
from fudge.patcher import with_patched_object
from nose.tools import eq_, raises

from fabric.state import output, env
from fabric.utils import warn, indent, abort, puts, fastprint, error, RingBuffer
from fabric import utils  # For patching
from fabric.context_managers import settings, hide
from fabric.colors import magenta, red
from utils import mock_streams, aborts, FabricTest, assert_contains


@mock_streams('stderr')
@with_patched_object(output, 'warnings', True)
def test_warn():
    """
    warn() should print 'Warning' plus given text
    """
    warn("Test")
    eq_("\nWarning: Test\n\n", sys.stderr.getvalue())


def test_indent():
    for description, input, output in (
        ("Sanity check: 1 line string",
            'Test', '    Test'),
        ("List of strings turns in to strings joined by \\n",
            ["Test", "Test"], '    Test\n    Test'),
    ):
        eq_.description = "indent(): %s" % description
        yield eq_, indent(input), output
        del eq_.description


def test_indent_with_strip():
    for description, input, output in (
        ("Sanity check: 1 line string",
            indent('Test', strip=True), '    Test'),
        ("Check list of strings",
            indent(["Test", "Test"], strip=True), '    Test\n    Test'),
        ("Check list of strings",
            indent(["        Test", "        Test"], strip=True),
            '    Test\n    Test'),
    ):
        eq_.description = "indent(strip=True): %s" % description
        yield eq_, input, output
        del eq_.description


@aborts
def test_abort():
    """
    abort() should raise SystemExit
    """
    abort("Test")

class TestException(Exception):
    pass

@raises(TestException)
def test_abort_with_exception():
    """
    abort() should raise a provided exception
    """
    with settings(abort_exception=TestException):
        abort("Test")


@mock_streams('stderr')
@with_patched_object(output, 'aborts', True)
def test_abort_message():
    """
    abort() should print 'Fatal error' plus exception value
    """
    try:
        abort("Test")
    except SystemExit:
        pass
    result = sys.stderr.getvalue()
    eq_("\nFatal error: Test\n\nAborting.\n", result)


@mock_streams('stdout')
def test_puts_with_user_output_on():
    """
    puts() should print input to sys.stdout if "user" output level is on
    """
    s = "string!"
    output.user = True
    puts(s, show_prefix=False)
    eq_(sys.stdout.getvalue(), s + "\n")


@mock_streams('stdout')
def test_puts_with_user_output_off():
    """
    puts() shouldn't print input to sys.stdout if "user" output level is off
    """
    output.user = False
    puts("You aren't reading this.")
    eq_(sys.stdout.getvalue(), "")


@mock_streams('stdout')
def test_puts_with_prefix():
    """
    puts() should prefix output with env.host_string if non-empty
    """
    s = "my output"
    h = "localhost"
    with settings(host_string=h):
        puts(s)
    eq_(sys.stdout.getvalue(), "[%s] %s" % (h, s + "\n"))


@mock_streams('stdout')
def test_puts_without_prefix():
    """
    puts() shouldn't prefix output with env.host_string if show_prefix is False
    """
    s = "my output"
    h = "localhost"
    puts(s, show_prefix=False)
    eq_(sys.stdout.getvalue(), "%s" % (s + "\n"))

@with_fakes
def test_fastprint_calls_puts():
    """
    fastprint() is just an alias to puts()
    """
    text = "Some output"
    fake_puts = Fake('puts', expect_call=True).with_args(
        text=text, show_prefix=False, end="", flush=True
    )
    with patched_context(utils, 'puts', fake_puts):
        fastprint(text)


class TestErrorHandling(FabricTest):
    @with_patched_object(utils, 'warn', Fake('warn', callable=True,
        expect_call=True))
    def test_error_warns_if_warn_only_True_and_func_None(self):
        """
        warn_only=True, error(func=None) => calls warn()
        """
        with settings(warn_only=True):
            error('foo')

    @with_patched_object(utils, 'abort', Fake('abort', callable=True,
        expect_call=True))
    def test_error_aborts_if_warn_only_False_and_func_None(self):
        """
        warn_only=False, error(func=None) => calls abort()
        """
        with settings(warn_only=False):
            error('foo')

    def test_error_calls_given_func_if_func_not_None(self):
        """
        error(func=callable) => calls callable()
        """
        error('foo', func=Fake(callable=True, expect_call=True))

    @mock_streams('stdout')
    @with_patched_object(utils, 'abort', Fake('abort', callable=True,
        expect_call=True).calls(lambda x: sys.stdout.write(x + "\n")))
    def test_error_includes_stdout_if_given_and_hidden(self):
        """
        error() correctly prints stdout if it was previously hidden
        """
        # Mostly to catch regression bug(s)
        stdout = "this is my stdout"
        with hide('stdout'):
            error("error message", func=utils.abort, stdout=stdout)
        assert_contains(stdout, sys.stdout.getvalue())

    @mock_streams('stderr')
    @with_patched_object(utils, 'abort', Fake('abort', callable=True,
        expect_call=True).calls(lambda x: sys.stderr.write(x + "\n")))
    def test_error_includes_stderr_if_given_and_hidden(self):
        """
        error() correctly prints stderr if it was previously hidden
        """
        # Mostly to catch regression bug(s)
        stderr = "this is my stderr"
        with hide('stderr'):
            error("error message", func=utils.abort, stderr=stderr)
        assert_contains(stderr, sys.stderr.getvalue())

    @mock_streams('stderr')
    def test_warnings_print_magenta_if_colorize_on(self):
        with settings(colorize_errors=True):
            error("oh god", func=utils.warn, stderr="oops")
        # can't use assert_contains as ANSI codes contain regex specialchars
        eq_(magenta("\nWarning: oh god\n\n"), sys.stderr.getvalue())

    @mock_streams('stderr')
    @raises(SystemExit)
    def test_errors_print_red_if_colorize_on(self):
        with settings(colorize_errors=True):
            error("oh god", func=utils.abort, stderr="oops")
        # can't use assert_contains as ANSI codes contain regex specialchars
        eq_(red("\Error: oh god\n\n"), sys.stderr.getvalue())


class TestRingBuffer(TestCase):
    def setUp(self):
        self.b = RingBuffer([], maxlen=5)

    def test_append_empty(self):
        self.b.append('x')
        eq_(self.b, ['x'])

    def test_append_full(self):
        self.b.extend("abcde")
        self.b.append('f')
        eq_(self.b, ['b', 'c', 'd', 'e', 'f'])

    def test_extend_empty(self):
        self.b.extend("abc")
        eq_(self.b, ['a', 'b', 'c'])

    def test_extend_overrun(self):
        self.b.extend("abc")
        self.b.extend("defg")
        eq_(self.b, ['c', 'd', 'e', 'f', 'g'])

    def test_extend_full(self):
        self.b.extend("abcde")
        self.b.extend("fgh")
        eq_(self.b, ['d', 'e', 'f', 'g', 'h'])

########NEW FILE########
__FILENAME__ = test_version
"""
Tests covering Fabric's version number pretty-print functionality.
"""

from nose.tools import eq_

import fabric.version


def test_get_version():
    get_version = fabric.version.get_version
    sha = fabric.version.git_sha()
    sha1 = (" (%s)" % sha) if sha else ""
    for tup, short, normal, verbose in [
        ((0, 9, 0, 'final', 0), '0.9.0', '0.9', '0.9 final'),
        ((0, 9, 1, 'final', 0), '0.9.1', '0.9.1', '0.9.1 final'),
        ((0, 9, 0, 'alpha', 1), '0.9a1', '0.9 alpha 1', '0.9 alpha 1'),
        ((0, 9, 1, 'beta', 1), '0.9.1b1', '0.9.1 beta 1', '0.9.1 beta 1'),
        ((0, 9, 0, 'release candidate', 1),
            '0.9rc1', '0.9 release candidate 1', '0.9 release candidate 1'),
        ((1, 0, 0, 'alpha', 0), '1.0a%s' % sha1, '1.0 pre-alpha%s' % sha1,
            '1.0 pre-alpha%s' % sha1),
    ]:
        fabric.version.VERSION = tup
        yield eq_, get_version('short'), short
        yield eq_, get_version('normal'), normal
        yield eq_, get_version('verbose'), verbose

########NEW FILE########
__FILENAME__ = utils
from __future__ import with_statement

from contextlib import contextmanager
from copy import deepcopy
from fudge.patcher import with_patched_object
from functools import partial
from types import StringTypes
import copy
import getpass
import os
import re
import shutil
import sys
import tempfile

from fudge import Fake, patched_context, clear_expectations, with_patched_object
from nose.tools import raises
from nose import SkipTest

from fabric.context_managers import settings
from fabric.state import env, output
from fabric.sftp import SFTP
import fabric.network
from fabric.network import normalize, to_dict

from server import PORT, PASSWORDS, USER, HOST
from mock_streams import mock_streams


class FabricTest(object):
    """
    Nose-oriented test runner which wipes state.env and provides file helpers.
    """
    def setup(self):
        # Clear Fudge mock expectations
        clear_expectations()
        # Copy env, output for restoration in teardown
        self.previous_env = copy.deepcopy(env)
        # Deepcopy doesn't work well on AliasDicts; but they're only one layer
        # deep anyways, so...
        self.previous_output = output.items()
        # Allow hooks from subclasses here for setting env vars (so they get
        # purged correctly in teardown())
        self.env_setup()
        # Temporary local file dir
        self.tmpdir = tempfile.mkdtemp()

    def set_network(self):
        env.update(to_dict('%s@%s:%s' % (USER, HOST, PORT)))

    def env_setup(self):
        # Set up default networking for test server
        env.disable_known_hosts = True
        self.set_network()
        env.password = PASSWORDS[USER]
        # Command response mocking is easier without having to account for
        # shell wrapping everywhere.
        env.use_shell = False

    def teardown(self):
        env.clear() # In case tests set env vars that didn't exist previously
        env.update(self.previous_env)
        output.update(self.previous_output)
        shutil.rmtree(self.tmpdir)
        # Clear Fudge mock expectations...again
        clear_expectations()

    def path(self, *path_parts):
        return os.path.join(self.tmpdir, *path_parts)

    def mkfile(self, path, contents):
        dest = self.path(path)
        with open(dest, 'w') as fd:
            fd.write(contents)
        return dest

    def exists_remotely(self, path):
        return SFTP(env.host_string).exists(path)

    def exists_locally(self, path):
        return os.path.exists(path)


def password_response(password, times_called=None, silent=True):
    """
    Context manager which patches ``getpass.getpass`` to return ``password``.

    ``password`` may be a single string or an iterable of strings:

    * If single string, given password is returned every time ``getpass`` is
      called.
    * If iterable, iterated over for each call to ``getpass``, after which
      ``getpass`` will error.

    If ``times_called`` is given, it is used to add a ``Fake.times_called``
    clause to the mock object, e.g. ``.times_called(1)``. Specifying
    ``times_called`` alongside an iterable ``password`` list is unsupported
    (see Fudge docs on ``Fake.next_call``).

    If ``silent`` is True, no prompt will be printed to ``sys.stderr``.
    """
    fake = Fake('getpass', callable=True)
    # Assume stringtype or iterable, turn into mutable iterable
    if isinstance(password, StringTypes):
        passwords = [password]
    else:
        passwords = list(password)
    # Optional echoing of prompt to mimic real behavior of getpass
    # NOTE: also echo a newline if the prompt isn't a "passthrough" from the
    # server (as it means the server won't be sending its own newline for us).
    echo = lambda x, y: y.write(x + ("\n" if x != " " else ""))
    # Always return first (only?) password right away
    fake = fake.returns(passwords.pop(0))
    if not silent:
        fake = fake.calls(echo)
    # If we had >1, return those afterwards
    for pw in passwords:
        fake = fake.next_call().returns(pw)
        if not silent:
            fake = fake.calls(echo)
    # Passthrough times_called
    if times_called:
        fake = fake.times_called(times_called)
    return patched_context(getpass, 'getpass', fake)


def _assert_contains(needle, haystack, invert):
    matched = re.search(needle, haystack, re.M)
    if (invert and matched) or (not invert and not matched):
        raise AssertionError("r'%s' %sfound in '%s'" % (
            needle,
            "" if invert else "not ",
            haystack
        ))

assert_contains = partial(_assert_contains, invert=False)
assert_not_contains = partial(_assert_contains, invert=True)


def line_prefix(prefix, string):
    """
    Return ``string`` with all lines prefixed by ``prefix``.
    """
    return "\n".join(prefix + x for x in string.splitlines())


def eq_(result, expected, msg=None):
    """
    Shadow of the Nose builtin which presents easier to read multiline output.
    """
    params = {'expected': expected, 'result': result}
    aka = """

--------------------------------- aka -----------------------------------------

Expected:
%(expected)r

Got:
%(result)r
""" % params
    default_msg = """
Expected:
%(expected)s

Got:
%(result)s
""" % params
    if (repr(result) != str(result)) or (repr(expected) != str(expected)):
        default_msg += aka
    assert result == expected, msg or default_msg


def eq_contents(path, text):
    with open(path) as fd:
        eq_(text, fd.read())


def support(path):
    return os.path.join(os.path.dirname(__file__), 'support', path)

fabfile = support


@contextmanager
def path_prefix(module):
    i = 0
    sys.path.insert(i, os.path.dirname(module))
    yield
    sys.path.pop(i)


def aborts(func):
    return raises(SystemExit)(mock_streams('stderr')(func))


def _patched_input(func, fake):
    return func(sys.modules['__builtin__'], 'raw_input', fake)
patched_input = partial(_patched_input, patched_context)
with_patched_input = partial(_patched_input, with_patched_object)

########NEW FILE########
