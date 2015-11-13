__FILENAME__ = multiple
#!/usr/bin/env python
from Exscript            import Host
from Exscript.util.file  import get_hosts_from_file, get_accounts_from_file
from Exscript.util.start import start

def one(job, host, conn):
    # You can add a safehold based on the guess_os() method.
    if conn.guess_os() != 'ios':
        raise Exception('unsupported os: ' + repr(conn.guess_os()))

    # autoinit() automatically executes commands to make the remote
    # system behave more script-friendly. The specific commands depend
    # on the detected operating system, i.e. on what guess_os() returns.
    conn.autoinit()

    # Execute a simple command.
    conn.execute('show ip int brie')
    print "myvariable is", conn.get_host().get('myvariable')

def two(job, host, conn):
    conn.autoinit()
    conn.execute('show interface POS1/0')

accounts = get_accounts_from_file('accounts.cfg')

# Start on one host.
host = Host('localhost')
host.set('myvariable', 'foobar')
start(accounts, host1, one)

# Start on many hosts. In this case, the accounts from accounts.cfg
# are only used if the host url does not contain a username and password.
# The "max_threads" keyword indicates the maximum number of concurrent
# connections.
hosts = get_hosts_from_file('hostlist.txt')
start(accounts, hosts, two, max_threads = 2)

########NEW FILE########
__FILENAME__ = quickstart
#!/usr/bin/env python
from Exscript.util.match    import any_match
from Exscript.util.template import eval_file
from Exscript.util.start    import quickstart

def do_something(job, host, conn):
    conn.execute('ls -1')
    files = any_match(conn, r'(\S+)')
    print "Files found:", files

# Open a connection (Telnet, by default) to each of the hosts, and run
# do_something(). To open the connection via SSH, you may prefix the
# hostname by the protocol, e.g.: 'ssh://hostname', 'telnet://hostname',
# etc.
quickstart(('localhost', 'otherhost'), do_something)

########NEW FILE########
__FILENAME__ = report
#!/usr/bin/env python
from Exscript                import Queue, Logger
from Exscript.util.log       import log_to
from Exscript.util.decorator import autologin
from Exscript.util.file      import get_hosts_from_file, get_accounts_from_file
from Exscript.util.report    import status, summarize

logger = Logger() # Logs everything to memory.

@log_to(logger)
@autologin()
def do_something(job, host, conn):
    conn.execute('show ip int brie')

# Read input data.
accounts = get_accounts_from_file('accounts.cfg')
hosts    = get_hosts_from_file('hostlist.txt')

# Run do_something on each of the hosts. The given accounts are used
# round-robin. "verbose = 0" instructs the queue to not generate any
# output on stdout.
queue = Queue(verbose = 5, max_threads = 5)
queue.add_account(accounts)     # Adds one or more accounts.
queue.run(hosts, do_something)  # Asynchronously enqueues all hosts.
queue.shutdown()                # Waits until all hosts are completed.

# Print a short report.
print status(logger)
print summarize(logger)

########NEW FILE########
__FILENAME__ = simple
from Exscript.util.interact import read_login
from Exscript.protocols import SSH2

account = read_login()

conn = SSH2()
conn.connect('localhost')
conn.login(account)
conn.execute('ls -l')

print "Response was:", repr(conn.response)

conn.send('exit\r')
conn.close()

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
from Exscript.util.template import eval_file
from Exscript.util.start    import quickstart

def do_something(job, host, conn):
    assert conn.guess_os() == 'shell'
    conn.execute('ls -1')
    eval_file(conn, 'template.exscript', foobar = 'hello-world')

quickstart('ssh://xpc3', do_something)

########NEW FILE########
__FILENAME__ = mkapidoc
#!/usr/bin/env python
# Generates the *public* API documentation.
# Remember to hide your private parts, people!
import os, re, sys

project  = 'Exscript'
base_dir = os.path.join('..', 'src')
doc_dir  = 'api'

# Create the documentation directory.
if not os.path.exists(doc_dir):
    os.makedirs(doc_dir)

# Generate the API documentation.
cmd = 'epydoc ' + ' '.join(['--name', project,
                            r'--exclude ^Exscript\.AccountManager$',
                            r'--exclude ^Exscript\.Log$',
                            r'--exclude ^Exscript\.Logfile$',
                            r'--exclude ^Exscript\.LoggerProxy$',
                            r'--exclude ^Exscript\.external$',
                            r'--exclude ^Exscript\.interpreter$',
                            r'--exclude ^Exscript\.parselib$',
                            r'--exclude ^Exscript\.protocols\.OsGuesser$',
                            r'--exclude ^Exscript\.protocols\.telnetlib$',
                            r'--exclude ^Exscript\.stdlib$',
                            r'--exclude ^Exscript\.workqueue$',
                            r'--exclude ^Exscript\.version$',
                            r'--exclude-introspect ^Exscript\.util\.sigintcatcher$',
                            r'--exclude ^Exscriptd\.Config$',
                            r'--exclude ^Exscriptd\.ConfigReader$',
                            r'--exclude ^Exscriptd\.Daemon$',
                            r'--exclude ^Exscriptd\.DBObject$',
                            r'--exclude ^Exscriptd\.HTTPDaemon$',
                            r'--exclude ^Exscriptd\.HTTPDigestServer$',
                            r'--exclude ^Exscriptd\.OrderDB$',
                            r'--exclude ^Exscriptd\.PythonService$',
                            r'--exclude ^Exscriptd\.Service$',
                            r'--exclude ^Exscriptd\.Task$',
                            r'--exclude ^Exscriptd\.config$',
                            r'--exclude ^Exscriptd\.daemonize$',
                            r'--exclude ^Exscriptd\.util$',
                            r'--exclude ^Exscriptd\.pidutil$',
                            r'--exclude ^TkExscript\.compat$',
                            '--html',
                            '--no-private',
                            '--introspect-only',
                            '--no-source',
                            '--no-frames',
                            '--inheritance=included',
                            '-v',
                            '-o %s' % doc_dir,
                            os.path.join(base_dir, project),
                            os.path.join(base_dir, 'Exscriptd'),
                            os.path.join(base_dir, 'TkExscript')])
print cmd
os.system(cmd)

########NEW FILE########
__FILENAME__ = Account
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Representing user accounts.
"""
import threading
from Exscript.util.event import Event
from Exscript.util.impl import Context

class Account(object):
    """
    This class represents a user account.
    """

    def __init__(self, name, password = '', password2 = None, key = None):
        """
        Constructor.

        The authorization password is only required on hosts that
        separate the authentication from the authorization procedure.
        If an authorization password is not given, it defaults to the
        same value as the authentication password.

        @type  name: string
        @param name: A username.
        @type  password: string
        @param password: The authentication password.
        @type  password2: string
        @param password2: The authorization password, if required.
        @type  key: PrivateKey
        @param key: A private key, if required.
        """
        self.acquired_event         = Event()
        self.released_event         = Event()
        self.changed_event          = Event()
        self.name                   = name
        self.password               = password
        self.authorization_password = password2
        self.key                    = key
        self.synclock               = threading.Condition(threading.Lock())
        self.lock                   = threading.Lock()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, thetype, value, traceback):
        self.release()

    def context(self):
        """
        When you need a 'with' context for an already-acquired account.
        """
        return Context(self)

    def acquire(self, signal = True):
        """
        Locks the account.

        @type  signal: bool
        @param signal: Whether to emit the acquired_event signal.
        """
        with self.synclock:
            while not self.lock.acquire(False):
                self.synclock.wait()
            if signal:
                self.acquired_event(self)
            self.synclock.notify_all()

    def release(self, signal = True):
        """
        Unlocks the account.

        @type  signal: bool
        @param signal: Whether to emit the released_event signal.
        """
        with self.synclock:
            self.lock.release()
            if signal:
                self.released_event(self)
            self.synclock.notify_all()

    def set_name(self, name):
        """
        Changes the name of the account.

        @type  name: string
        @param name: The account name.
        """
        self.name = name
        self.changed_event.emit(self)

    def get_name(self):
        """
        Returns the name of the account.

        @rtype:  string
        @return: The account name.
        """
        return self.name

    def set_password(self, password):
        """
        Changes the password of the account.

        @type  password: string
        @param password: The account password.
        """
        self.password = password
        self.changed_event.emit(self)

    def get_password(self):
        """
        Returns the password of the account.

        @rtype:  string
        @return: The account password.
        """
        return self.password

    def set_authorization_password(self, password):
        """
        Changes the authorization password of the account.

        @type  password: string
        @param password: The new authorization password.
        """
        self.authorization_password = password
        self.changed_event.emit(self)

    def get_authorization_password(self):
        """
        Returns the authorization password of the account.

        @rtype:  string
        @return: The account password.
        """
        return self.authorization_password or self.password

    def get_key(self):
        """
        Returns the key of the account, if any.

        @rtype:  PrivateKey|None
        @return: A key object.
        """
        return self.key

########NEW FILE########
__FILENAME__ = AccountManager
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Manages user accounts.
"""
from Exscript.AccountPool import AccountPool

class AccountManager(object):
    """
    Keeps track of available user accounts and assigns them to the
    worker threads.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.default_pool = None
        self.pools        = None
        self.reset()

    def reset(self):
        """
        Removes all account pools.
        """
        self.default_pool = AccountPool()
        self.pools        = []

    def add_pool(self, pool, match = None):
        """
        Adds a new account pool. If the given match argument is
        None, the pool the default pool. Otherwise, the match argument is
        a callback function that is invoked to decide whether or not the
        given pool should be used for a host.

        When Exscript logs into a host, the account is chosen in the following
        order:

            # Exscript checks whether an account was attached to the
            L{Host} object using L{Host.set_account()}), and uses that.

            # If the L{Host} has no account attached, Exscript walks
            through all pools that were passed to L{Queue.add_account_pool()}.
            For each pool, it passes the L{Host} to the function in the
            given match argument. If the return value is True, the account
            pool is used to acquire an account.
            (Accounts within each pool are taken in a round-robin
            fashion.)

            # If no matching account pool is found, an account is taken
            from the default account pool.

            # Finally, if all that fails and the default account pool
            contains no accounts, an error is raised.

        Example usage::

            def do_nothing(conn):
                conn.autoinit()

            def use_this_pool(host):
                return host.get_name().startswith('foo')

            default_pool = AccountPool()
            default_pool.add_account(Account('default-user', 'password'))

            other_pool = AccountPool()
            other_pool.add_account(Account('user', 'password'))

            queue = Queue()
            queue.account_manager.add_pool(default_pool)
            queue.account_manager.add_pool(other_pool, use_this_pool)

            host = Host('localhost')
            queue.run(host, do_nothing)

        In the example code, the host has no account attached. As a result,
        the queue checks whether use_this_pool() returns True. Because the
        hostname does not start with 'foo', the function returns False, and
        Exscript takes the 'default-user' account from the default pool.

        @type  pool: AccountPool
        @param pool: The account pool that is added.
        @type  match: callable
        @param match: A callback to check if the pool should be used.
        """
        if match is None:
            self.default_pool = pool
        else:
            self.pools.append((match, pool))

    def add_account(self, account):
        """
        Adds the given account to the default account pool that Exscript uses
        to log into all hosts that have no specific L{Account} attached.

        @type  account: Account
        @param account: The account that is added.
        """
        self.default_pool.add_account(account)

    def get_account_from_hash(self, account_hash):
        """
        Returns the account with the given hash, if it is contained in any
        of the pools. Returns None otherwise.

        @type  account_hash: str
        @param account_hash: The hash of an account object.
        """
        for _, pool in self.pools:
            account = pool.get_account_from_hash(account_hash)
            if account is not None:
                return account
        return self.default_pool.get_account_from_hash(account_hash)

    def acquire_account(self, account = None, owner = None):
        """
        Acquires the given account. If no account is given, one is chosen
        from the default pool.

        @type  account: Account
        @param account: The account that is added.
        @type  owner: object
        @param owner: An optional descriptor for the owner.
        @rtype:  L{Account}
        @return: The account that was acquired.
        """
        if account is not None:
            for _, pool in self.pools:
                if pool.has_account(account):
                    return pool.acquire_account(account, owner)

            if not self.default_pool.has_account(account):
                # The account is not in any pool.
                account.acquire()
                return account

        return self.default_pool.acquire_account(account, owner)

    def acquire_account_for(self, host, owner = None):
        """
        Acquires an account for the given host and returns it.
        The host is passed to each of the match functions that were
        passed in when adding the pool. The first pool for which the
        match function returns True is chosen to assign an account.

        @type  host: L{Host}
        @param host: The host for which an account is acquired.
        @type  owner: object
        @param owner: An optional descriptor for the owner.
        @rtype:  L{Account}
        @return: The account that was acquired.
        """
        # Check whether a matching account pool exists.
        for match, pool in self.pools:
            if match(host) is True:
                return pool.acquire_account(owner = owner)

        # Else, choose an account from the default account pool.
        return self.default_pool.acquire_account(owner = owner)

    def release_accounts(self, owner):
        """
        Releases all accounts that were acquired by the given owner.

        @type  owner: object
        @param owner: The owner descriptor as passed to acquire_account().
        """
        for _, pool in self.pools:
            pool.release_accounts(owner)
        self.default_pool.release_accounts(owner)

########NEW FILE########
__FILENAME__ = AccountPool
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A collection of user accounts.
"""
import threading
from collections import deque, defaultdict
from Exscript.util.cast import to_list

class AccountPool(object):
    """
    This class manages a collection of available accounts.
    """

    def __init__(self, accounts = None):
        """
        Constructor.

        @type  accounts: Account|list[Account]
        @param accounts: Passed to add_account()
        """
        self.accounts          = set()
        self.unlocked_accounts = deque()
        self.owner2account     = defaultdict(list)
        self.account2owner     = dict()
        self.unlock_cond       = threading.Condition(threading.RLock())
        if accounts:
            self.add_account(accounts)

    def _on_account_acquired(self, account):
        with self.unlock_cond:
            if account not in self.accounts:
                msg = 'attempt to acquire unknown account %s' % account
                raise Exception(msg)
            if account not in self.unlocked_accounts:
                raise Exception('account %s is already locked' % account)
            self.unlocked_accounts.remove(account)
            self.unlock_cond.notify_all()
        return account

    def _on_account_released(self, account):
        with self.unlock_cond:
            if account not in self.accounts:
                msg = 'attempt to acquire unknown account %s' % account
                raise Exception(msg)
            if account in self.unlocked_accounts:
                raise Exception('account %s should be locked' % account)
            self.unlocked_accounts.append(account)
            owner = self.account2owner.get(account)
            if owner is not None:
                self.account2owner.pop(account)
                self.owner2account[owner].remove(account)
            self.unlock_cond.notify_all()
        return account

    def get_account_from_hash(self, account_hash):
        """
        Returns the account with the given hash, or None if no such
        account is included in the account pool.
        """
        for account in self.accounts:
            if account.__hash__() == account_hash:
                return account
        return None

    def has_account(self, account):
        """
        Returns True if the given account exists in the pool, returns False
        otherwise.

        @type  account: Account
        @param account: The account object.
        """
        return account in self.accounts

    def add_account(self, accounts):
        """
        Adds one or more account instances to the pool.

        @type  accounts: Account|list[Account]
        @param accounts: The account to be added.
        """
        with self.unlock_cond:
            for account in to_list(accounts):
                account.acquired_event.listen(self._on_account_acquired)
                account.released_event.listen(self._on_account_released)
                self.accounts.add(account)
                self.unlocked_accounts.append(account)
            self.unlock_cond.notify_all()

    def _remove_account(self, accounts):
        """
        @type  accounts: Account|list[Account]
        @param accounts: The accounts to be removed.
        """
        for account in to_list(accounts):
            if account not in self.accounts:
                msg = 'attempt to remove unknown account %s' % account
                raise Exception(msg)
            if account not in self.unlocked_accounts:
                raise Exception('account %s should be unlocked' % account)
            account.acquired_event.disconnect(self._on_account_acquired)
            account.released_event.disconnect(self._on_account_released)
            self.accounts.remove(account)
            self.unlocked_accounts.remove(account)

    def reset(self):
        """
        Removes all accounts.
        """
        with self.unlock_cond:
            for owner in self.owner2account:
                self.release_accounts(owner)
            self._remove_account(self.accounts.copy())
            self.unlock_cond.notify_all()

    def get_account_from_name(self, name):
        """
        Returns the account with the given name.

        @type  name: string
        @param name: The name of the account.
        """
        for account in self.accounts:
            if account.get_name() == name:
                return account
        return None

    def n_accounts(self):
        """
        Returns the number of accounts that are currently in the pool.
        """
        return len(self.accounts)

    def acquire_account(self, account = None, owner = None):
        """
        Waits until an account becomes available, then locks and returns it.
        If an account is not passed, the next available account is returned.

        @type  account: Account
        @param account: The account to be acquired, or None.
        @type  owner: object
        @param owner: An optional descriptor for the owner.
        @rtype:  L{Account}
        @return: The account that was acquired.
        """
        with self.unlock_cond:
            if len(self.accounts) == 0:
                raise ValueError('account pool is empty')

            if account:
                # Specific account requested.
                while account not in self.unlocked_accounts:
                    self.unlock_cond.wait()
                self.unlocked_accounts.remove(account)
            else:
                # Else take the next available one.
                while len(self.unlocked_accounts) == 0:
                    self.unlock_cond.wait()
                account = self.unlocked_accounts.popleft()

            if owner is not None:
                self.owner2account[owner].append(account)
                self.account2owner[account] = owner
            account.acquire(False)
            self.unlock_cond.notify_all()
            return account

    def release_accounts(self, owner):
        """
        Releases all accounts that were acquired by the given owner.

        @type  owner: object
        @param owner: The owner descriptor as passed to acquire_account().
        """
        with self.unlock_cond:
            for account in self.owner2account[owner]:
                self.account2owner.pop(account)
                account.release(False)
                self.unlocked_accounts.append(account)
            self.owner2account.pop(owner)
            self.unlock_cond.notify_all()

########NEW FILE########
__FILENAME__ = AccountProxy
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A remote object that acquires/releases an account via a pipe.
"""
from Exscript.util.impl import Context

class AccountProxy(object):
    """
    An object that has a 1:1 relation to an account object in another
    process.
    """
    def __init__(self, parent):
        """
        Constructor.

        @type  parent: multiprocessing.Connection
        @param parent: A pipe to the associated account manager.
        """
        self.parent                 = parent
        self.account_hash           = None
        self.host                   = None
        self.user                   = None
        self.password               = None
        self.authorization_password = None
        self.key                    = None

    @staticmethod
    def for_host(parent, host):
        """
        Returns a new AccountProxy that has an account acquired. The
        account is chosen based on what the connected AccountManager
        selects for the given host.
        """
        account = AccountProxy(parent)
        account.host = host
        if account.acquire():
            return account
        return None

    @staticmethod
    def for_account_hash(parent, account_hash):
        """
        Returns a new AccountProxy that acquires the account with the
        given hash, if such an account is known to the account manager.
        It is an error if the account manager does not have such an
        account.
        """
        account = AccountProxy(parent)
        account.account_hash = account_hash
        if account.acquire():
            return account
        return None

    @staticmethod
    def for_random_account(parent):
        """
        Returns a new AccountProxy that has an account acquired. The
        account is chosen by the connected AccountManager.
        """
        account = AccountProxy(parent)
        if account.acquire():
            return account
        return None

    def __hash__(self):
        """
        Returns the hash of the currently acquired account.
        """
        return self.account_hash

    def __enter__(self):
        """
        Like L{acquire()}.
        """
        return self.acquire()

    def __exit__(self, thetype, value, traceback):
        """
        Like L{release()}.
        """
        return self.release()

    def context(self):
        """
        When you need a 'with' context for an already-acquired account.
        """
        return Context(self)

    def acquire(self):
        """
        Locks the account. Returns True on success, False if the account
        is thread-local and must not be locked.
        """
        if self.host:
            self.parent.send(('acquire-account-for-host', self.host))
        elif self.account_hash:
            self.parent.send(('acquire-account-from-hash', self.account_hash))
        else:
            self.parent.send(('acquire-account'))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        if response is None:
            return False

        self.account_hash, \
        self.user, \
        self.password, \
        self.authorization_password, \
        self.key = response
        return True

    def release(self):
        """
        Unlocks the account.
        """
        self.parent.send(('release-account', self.account_hash))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response

        if response != 'ok':
            raise ValueError('unexpected response: ' + repr(response))

    def get_name(self):
        """
        Returns the name of the account.

        @rtype:  string
        @return: The account name.
        """
        return self.user

    def get_password(self):
        """
        Returns the password of the account.

        @rtype:  string
        @return: The account password.
        """
        return self.password

    def get_authorization_password(self):
        """
        Returns the authorization password of the account.

        @rtype:  string
        @return: The account password.
        """
        return self.authorization_password or self.password

    def get_key(self):
        """
        Returns the key of the account, if any.

        @rtype:  PrivateKey|None
        @return: A key object.
        """
        return self.key

########NEW FILE########
__FILENAME__ = CommandSet
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Defines the behavior of commands by mapping commands to functions.
"""
import re

class CommandSet(object):
    """
    A set of commands to be used by the Dummy adapter.
    """

    def __init__(self, strict = True):
        """
        Constructor.
        """
        self.strict        = strict
        self.response_list = []

    def add(self, command, response):
        """
        Register a command/response pair.

        The command may be either a string (which is then automatically
        compiled into a regular expression), or a pre-compiled regular
        expression object.

        If the given response handler is a string, it is sent as the
        response to any command that matches the given regular expression.
        If the given response handler is a function, it is called
        with the command passed as an argument.

        @type  command: str|regex
        @param command: A string or a compiled regular expression.
        @type  response: function|str
        @param response: A reponse, or a response handler.
        """
        if isinstance(command, str):
            command = re.compile(command)
        elif not hasattr(command, 'search'):
            raise TypeError('command argument must be str or a regex')
        self.response_list.append((command, response))

    def add_from_file(self, filename, handler_decorator = None):
        """
        Wrapper around add() that reads the handlers from the
        file with the given name. The file is a Python script containing
        a list named 'commands' of tuples that map command names to
        handlers.

        @type  filename: str
        @param filename: The name of the file containing the tuples.
        @type  handler_decorator: function
        @param handler_decorator: A function that is used to decorate
               each of the handlers in the file.
        """
        args = {}
        execfile(filename, args)
        commands = args.get('commands')
        if commands is None:
            raise Exception(filename + ' has no variable named "commands"')
        elif not hasattr(commands, '__iter__'):
            raise Exception(filename + ': "commands" is not iterable')
        for key, handler in commands:
            if handler_decorator:
                handler = handler_decorator(handler)
            self.add(key, handler)

    def eval(self, command):
        """
        Evaluate the given string against all registered commands and
        return the defined response.

        @type  command: str
        @param command: The command that is evaluated.
        @rtype:  str or None
        @return: The response, if one was defined.
        """
        for cmd, response in self.response_list:
            if not cmd.match(command):
                continue
            if response is None:
                return None
            elif isinstance(response, str):
                return response
            else:
                return response(command)
        if self.strict:
            raise Exception('Undefined command: ' + repr(command))
        return None

########NEW FILE########
__FILENAME__ = IOSEmulator
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Cisco IOS emulator.
"""
import re
from Exscript.emulators import VirtualDevice

iosbanner = '''
Connected to %s.
Escape character is '^]'.


Unauthorized access prohibited!


%s line 2 


at '%s' port '/dev/vty0' from '12.34.56.78'
'''

def show_diag(data):
    slot = re.search(r'(\d+)', data).groups()[0]
    return """
SLOT %s  (RP/LC 0 ): 16 Port ISE Packet Over SONET OC-3c/STM-1 Single Mode/IR LC connector
  MAIN: type 79,  800-19733-08 rev A0
        Deviation: 0
        HW config: 0x01    SW key: 00-00-00
  PCA:  73-7614-07 rev A0 ver 1
        Design Release 1.0  S/N SAL1026SSZX
  MBUS: Embedded Agent
        Test hist: 0x00    RMA#: 00-00-00    RMA hist: 0x00
  DIAG: Test count: 0x00000000    Test results: 0x00000000
  FRU:  Linecard/Module: 16OC3X/POS-IR-LC-B=
        Processor Memory: MEM-LC-ISE-1024=
        Packet Memory: MEM-LC1-PKT-512=(Non-Replaceable)
  L3 Engine: 3 - ISE OC48 (2.5 Gbps)
  MBUS Agent Software version 2.68 (RAM) (ROM version is 3.66)
  ROM Monitor version 18.0
  Fabric Downloader version used 7.1 (ROM version is 7.1)
  Primary clock is CSC 1
  Board is analyzed 
  Board State is Line Card Enabled (IOS  RUN )
  Insertion time: 00:00:30 (36w1d ago)
  Processor Memory size: 1073741824 bytes
  TX Packet Memory size: 268435456 bytes, Packet Memory pagesize: 16384 bytes
  RX Packet Memory size: 268435456 bytes, Packet Memory pagesize: 16384 bytes
  0 crashes since restart
""" % slot

commands = (
('show version', """
Cisco Internetwork Operating System Software 
IOS (tm) GS Software (C12KPRP-P-M), Version 12.0(32)SY6c, RELEASE SOFTWARE (fc3)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2008 by cisco Systems, Inc.
Compiled Mon 08-Sep-08 15:31 by leccese
Image text-base: 0x00010000, data-base: 0x055CD000

ROM: System Bootstrap, Version 12.0(20040128:214555) [assafb-PRP1P_20040101 1.8dev(2.83)] DEVELOPMENT SOFTWARE
BOOTLDR: GS Software (C12KPRP-P-M), Version 12.0(32)SY6c, RELEASE SOFTWARE (fc3)

 S-EA1 uptime is 36 weeks, 1 day, 15 hours, 9 minutes
Uptime for this control processor is 36 weeks, 1 day, 14 hours, 30 minutes
System returned to ROM by reload at 03:32:54 MET Mon Feb 16 2009
System restarted at 03:25:22 MET Tue Mar 10 2009
System image file is "disk0:c12kprp-p-mz.120-32.SY6c.bin"

cisco 12416/PRP (MPC7457) processor (revision 0x00) with 1048576K bytes of memory.
MPC7457 CPU at 1263Mhz, Rev 1.1, 512KB L2, 2048KB L3 Cache
Last reset from power-on
Channelized E1, Version 1.0.

2 Route Processor Cards
2 Clock Scheduler Cards
3 Switch Fabric Cards
4 T1/E1 BITS controllers
1 Quad-port OC3c ATM controller (4 ATM).
2 16-port OC3 POS controllers (32 POS).
2 four-port OC12 POS controllers (8 POS).
2 twelve-port E3 controllers (24 E3).
1 Four Port Gigabit Ethernet/IEEE 802.3z controller (4 GigabitEthernet).
4 OC12 channelized to STS-12c/STM-4, STS-3c/STM-1 or DS-3/E3 controllers
4 ISE 10G SPA Interface Cards (12000-SIP-601)
3 Ethernet/IEEE 802.3 interface(s)
56 FastEthernet/IEEE 802.3 interface(s)
14 GigabitEthernet/IEEE 802.3 interface(s)
111 Serial network interface(s)
4 ATM network interface(s)
50 Packet over SONET network interface(s)
2043K bytes of non-volatile configuration memory.

250880K bytes of ATA PCMCIA card at slot 0 (Sector size 512 bytes).
65536K bytes of Flash internal SIMM (Sector size 256K).
Configuration register is 0x2102
""".lstrip()),

(r'sh\S* ip int\S* brie\S*', """
Interface     IP-Address     OK?  Method  Status                  Protocol
Ethernet0     10.108.00.5    YES  NVRAM   up                      up      
Ethernet1     unassigned     YES  unset   administratively down   down    
Loopback0     10.108.200.5   YES  NVRAM   up                      up      
Serial0       10.108.100.5   YES  NVRAM   up                      up      
Serial1       10.108.40.5    YES  NVRAM   up                      up      
Serial2       10.108.100.5   YES  manual  up                      up      
Serial3       unassigned     YES  unset   administratively down   down 
""".lstrip()),

('show interface.*', """
FastEthernet0/2 is administratively down, line protocol is down 
  Hardware is i82545, address is 0001.c9f4.c418 (bia 0001.c9f4.c418)
  MTU 1500 bytes, BW 100000 Kbit, DLY 100 usec, rely 255/255, load 1/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Half-duplex, Auto Speed
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input never, output never, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     0 packets input, 0 bytes
     Received 0 broadcasts, 0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 0 multicast
     0 input packets with dribble condition detected
     0 packets output, 0 bytes, 0 underruns
     1 output errors, 0 collisions, 0 interface resets
     0 babbles, 0 late collision, 0 deferred
     1 lost carrier, 0 no carrier
     0 output buffer failures, 0 output buffers swapped out
"""),

(r'show diag \d+', show_diag),

(r'^!.*', '')
)

class IOSEmulator(VirtualDevice):
    def __init__(self,
                 hostname,
                 echo       = True,
                 login_type = VirtualDevice.LOGIN_TYPE_BOTH,
                 strict     = True,
                 banner     = None):
        thebanner = iosbanner % (hostname, hostname, hostname)
        VirtualDevice.__init__(self,
                               hostname,
                               echo       = echo,
                               login_type = login_type,
                               strict     = strict,
                               banner     = banner or thebanner)
        self.user_prompt     = 'Username: '
        self.password_prompt = 'Password: '
        self.prompt          = hostname + '#'
        for command, handler in commands:
            self.add_command(command, handler)

########NEW FILE########
__FILENAME__ = VirtualDevice
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Defines the behavior of a device, as needed by L{Exscript.servers}.
"""
from Exscript.emulators import CommandSet

class VirtualDevice(object):
    """
    An object that emulates a remote device.
    """
    LOGIN_TYPE_PASSWORDONLY, \
    LOGIN_TYPE_USERONLY, \
    LOGIN_TYPE_BOTH, \
    LOGIN_TYPE_NONE = range(1, 5)

    PROMPT_STAGE_USERNAME, \
    PROMPT_STAGE_PASSWORD, \
    PROMPT_STAGE_CUSTOM = range(1, 4)

    def __init__(self,
                 hostname,
                 echo       = True,
                 login_type = LOGIN_TYPE_BOTH,
                 strict     = True,
                 banner     = None):
        """
        @type  hostname: str
        @param hostname: The hostname, used for the prompt.

        @keyword banner: A string to show as soon as the connection is opened.
        @keyword login_type: integer constant, one of LOGIN_TYPE_PASSWORDONLY,
            LOGIN_TYPE_USERONLY, LOGIN_TYPE_BOTH, LOGIN_TYPE_NONE.
        @keyword echo: whether to echo the command in a response.
        @keyword strict: Whether to raise when a given command has no handler.
        """
        self.hostname        = hostname
        self.banner          = banner or 'Welcome to %s!\n' % str(hostname)
        self.echo            = echo
        self.login_type      = login_type
        self.prompt          = hostname + '> '
        self.logged_in       = False
        self.commands        = CommandSet(strict = strict)
        self.user_prompt     = 'User: '
        self.password_prompt = 'Password: '
        self.init()

    def _get_prompt(self):
        if self.prompt_stage == self.PROMPT_STAGE_USERNAME:
            if self.login_type == self.LOGIN_TYPE_USERONLY:
                self.prompt_stage = self.PROMPT_STAGE_CUSTOM
            else:
                self.prompt_stage = self.PROMPT_STAGE_PASSWORD
            return self.user_prompt
        elif self.prompt_stage == self.PROMPT_STAGE_PASSWORD:
            self.prompt_stage = self.PROMPT_STAGE_CUSTOM
            return self.password_prompt
        elif self.prompt_stage == self.PROMPT_STAGE_CUSTOM:
            self.logged_in = True
            return self.prompt
        else:
            raise Exception('invalid prompt stage')

    def _create_autoprompt_handler(self, handler):
        if isinstance(handler, str):
            return lambda x: handler + '\n' + self._get_prompt()
        else:
            return lambda x: handler(x) + '\n' + self._get_prompt()

    def get_prompt(self):
        """
        Returns the prompt of the device.

        @rtype:  str
        @return: The current command line prompt.
        """
        return self.prompt

    def set_prompt(self, prompt):
        """
        Change the prompt of the device.

        @type  prompt: str
        @param prompt: The new command line prompt.
        """
        self.prompt = prompt

    def add_command(self, command, handler, prompt = True):
        """
        Registers a command.

        The command may be either a string (which is then automatically
        compiled into a regular expression), or a pre-compiled regular
        expression object.

        If the given response handler is a string, it is sent as the
        response to any command that matches the given regular expression.
        If the given response handler is a function, it is called
        with the command passed as an argument.

        @type  command: str|regex
        @param command: A string or a compiled regular expression.
        @type  handler: function|str
        @param handler: A string, or a response handler.
        @type  prompt: bool
        @param prompt: Whether to show a prompt after completing the command.
        """
        if prompt:
            thehandler = self._create_autoprompt_handler(handler)
        else:
            thehandler = handler
        self.commands.add(command, thehandler)

    def add_commands_from_file(self, filename, autoprompt = True):
        """
        Wrapper around add_command_handler that reads the handlers from the
        file with the given name. The file is a Python script containing
        a list named 'commands' of tuples that map command names to
        handlers.

        @type  filename: str
        @param filename: The name of the file containing the tuples.
        @type  autoprompt: bool
        @param autoprompt: Whether to append a prompt to each response.
        """
        if autoprompt:
            deco = self._create_autoprompt_handler
        else:
            deco = None
        self.commands.add_from_file(filename, deco)

    def init(self):
        """
        Init or reset the virtual device.

        @rtype:  str
        @return: The initial response of the virtual device.
        """
        self.logged_in = False

        if self.login_type == self.LOGIN_TYPE_PASSWORDONLY:
            self.prompt_stage = self.PROMPT_STAGE_PASSWORD
        elif self.login_type == self.LOGIN_TYPE_NONE:
            self.prompt_stage = self.PROMPT_STAGE_CUSTOM
        else:
            self.prompt_stage = self.PROMPT_STAGE_USERNAME

        return self.banner + self._get_prompt()

    def do(self, command):
        """
        "Executes" the given command on the virtual device, and returns
        the response.

        @type  command: str
        @param command: The command to be executed.
        @rtype:  str
        @return: The response of the virtual device.
        """
        echo = self.echo and command or ''
        if not self.logged_in:
            return echo + '\n' + self._get_prompt()

        response = self.commands.eval(command)
        if response is None:
            return echo + '\n' + self._get_prompt()
        return echo + response

########NEW FILE########
__FILENAME__ = AppendixB
"""
PyOTP, the Python One-Time Password module.

AppendixB.py: the standard dictionary for RFC2889 one-time passwords
encoded as six word sequences. 

<insert Python license here>
"""

__version__ = '$Revision: 1.4 $'

DefaultDictionary = [
         "A",     "ABE",   "ACE",   "ACT",   "AD",    "ADA",   "ADD",
"AGO",   "AID",   "AIM",   "AIR",   "ALL",   "ALP",   "AM",    "AMY",
"AN",    "ANA",   "AND",   "ANN",   "ANT",   "ANY",   "APE",   "APS",
"APT",   "ARC",   "ARE",   "ARK",   "ARM",   "ART",   "AS",    "ASH",
"ASK",   "AT",    "ATE",   "AUG",   "AUK",   "AVE",   "AWE",   "AWK",
"AWL",   "AWN",   "AX",  "AYE",   "BAD",   "BAG",   "BAH",   "BAM",
"BAN",   "BAR",   "BAT",   "BAY",   "BE",    "BED",   "BEE",   "BEG",
"BEN",   "BET",   "BEY",   "BIB",   "BID",   "BIG",   "BIN",   "BIT",
"BOB",   "BOG",   "BON",   "BOO",   "BOP",   "BOW",   "BOY",   "BUB",
"BUD",   "BUG",   "BUM",   "BUN",   "BUS",   "BUT",   "BUY",   "BY",
"BYE",   "CAB",   "CAL",   "CAM",   "CAN",   "CAP",   "CAR",   "CAT",
"CAW",   "COD",   "COG",   "COL",   "CON",   "COO",   "COP",   "COT",
"COW",   "COY",   "CRY",   "CUB",   "CUE",   "CUP",   "CUR",   "CUT",
"DAB",   "DAD",   "DAM",   "DAN",   "DAR",   "DAY",   "DEE",   "DEL",
"DEN",   "DES",   "DEW",   "DID",   "DIE",   "DIG",   "DIN",   "DIP",
"DO",    "DOE",   "DOG",   "DON",   "DOT",   "DOW",   "DRY",   "DUB",
"DUD",   "DUE",   "DUG",   "DUN",   "EAR",   "EAT",   "ED",    "EEL",
"EGG",   "EGO",   "ELI",   "ELK",   "ELM",   "ELY",   "EM",    "END",
"EST",   "ETC",   "EVA",   "EVE",   "EWE",   "EYE",   "FAD",   "FAN",
"FAR",   "FAT",   "FAY",   "FED",   "FEE",   "FEW",   "FIB",   "FIG",
"FIN",   "FIR",   "FIT",   "FLO",   "FLY",   "FOE",   "FOG",   "FOR",
"FRY",   "FUM",   "FUN",   "FUR",   "GAB",   "GAD",   "GAG",   "GAL",
"GAM",   "GAP",   "GAS",   "GAY",   "GEE",   "GEL",   "GEM",   "GET",
"GIG",   "GIL",   "GIN",   "GO",    "GOT",   "GUM",   "GUN",   "GUS",
"GUT",   "GUY",   "GYM",   "GYP",   "HA",    "HAD",   "HAL",   "HAM",
"HAN",   "HAP",   "HAS",   "HAT",   "HAW",   "HAY",   "HE",    "HEM",
"HEN",   "HER",   "HEW",   "HEY",   "HI",    "HID",   "HIM",   "HIP",
"HIS",   "HIT",   "HO",   "HOB",   "HOC",   "HOE",   "HOG",   "HOP",
"HOT",   "HOW",   "HUB",   "HUE",   "HUG",   "HUH",   "HUM",   "HUT",
"I",     "ICY",   "IDA",   "IF",    "IKE",   "ILL",   "INK",   "INN",
"IO",    "ION",   "IQ",   "IRA",   "IRE",   "IRK",   "IS",    "IT",
"ITS",   "IVY",   "JAB",   "JAG",   "JAM",   "JAN",   "JAR",   "JAW",
"JAY",   "JET",   "JIG",   "JIM",   "JO",    "JOB",   "JOE",   "JOG",
"JOT",   "JOY",   "JUG",   "JUT",   "KAY",   "KEG",   "KEN",   "KEY",
"KID",   "KIM",   "KIN",   "KIT",   "LA",    "LAB",   "LAC",   "LAD",
"LAG",   "LAM",   "LAP",   "LAW",   "LAY",   "LEA",   "LED",   "LEE",
"LEG",   "LEN",   "LEO",   "LET",   "LEW",   "LID",   "LIE",   "LIN",
"LIP",   "LIT",   "LO",   "LOB",   "LOG",   "LOP",   "LOS",   "LOT",
"LOU",   "LOW",   "LOY",   "LUG",   "LYE",   "MA",    "MAC",   "MAD",
"MAE",   "MAN",   "MAO",   "MAP",   "MAT",   "MAW",   "MAY",   "ME",
"MEG",   "MEL",   "MEN",   "MET",   "MEW",   "MID",   "MIN",   "MIT",
"MOB",   "MOD",   "MOE",   "MOO",   "MOP",   "MOS",   "MOT",   "MOW",
"MUD",   "MUG",   "MUM",   "MY",    "NAB",   "NAG",   "NAN",   "NAP",
"NAT",   "NAY",   "NE",   "NED",   "NEE",   "NET",   "NEW",   "NIB",
"NIL",   "NIP",   "NIT",   "NO",    "NOB",   "NOD",   "NON",   "NOR",
"NOT",   "NOV",   "NOW",   "NU",    "NUN",   "NUT",   "O",     "OAF",
"OAK",   "OAR",   "OAT",   "ODD",   "ODE",   "OF",    "OFF",   "OFT",
"OH",    "OIL",   "OK",   "OLD",   "ON",    "ONE",   "OR",    "ORB",
"ORE",   "ORR",   "OS",   "OTT",   "OUR",   "OUT",   "OVA",   "OW",
"OWE",   "OWL",   "OWN",   "OX",    "PA",    "PAD",   "PAL",   "PAM",
"PAN",   "PAP",   "PAR",   "PAT",   "PAW",   "PAY",   "PEA",   "PEG",
"PEN",   "PEP",   "PER",   "PET",   "PEW",   "PHI",   "PI",    "PIE",
"PIN",   "PIT",   "PLY",   "PO",    "POD",   "POE",   "POP",   "POT",
"POW",   "PRO",   "PRY",   "PUB",   "PUG",   "PUN",   "PUP",   "PUT",
"QUO",   "RAG",   "RAM",   "RAN",   "RAP",   "RAT",   "RAW",   "RAY",
"REB",   "RED",   "REP",   "RET",   "RIB",   "RID",   "RIG",   "RIM",
"RIO",   "RIP",   "ROB",   "ROD",   "ROE",   "RON",   "ROT",   "ROW",
"ROY",   "RUB",   "RUE",   "RUG",   "RUM",   "RUN",   "RYE",   "SAC",
"SAD",   "SAG",   "SAL",   "SAM",   "SAN",   "SAP",   "SAT",   "SAW",
"SAY",   "SEA",   "SEC",   "SEE",   "SEN",   "SET",   "SEW",   "SHE",
"SHY",   "SIN",   "SIP",   "SIR",   "SIS",   "SIT",   "SKI",   "SKY",
"SLY",   "SO",    "SOB",   "SOD",   "SON",   "SOP",   "SOW",   "SOY",
"SPA",   "SPY",   "SUB",   "SUD",   "SUE",   "SUM",   "SUN",   "SUP",
"TAB",   "TAD",   "TAG",   "TAN",   "TAP",   "TAR",   "TEA",   "TED",
"TEE",   "TEN",   "THE",   "THY",   "TIC",   "TIE",   "TIM",   "TIN",
"TIP",   "TO",    "TOE",   "TOG",   "TOM",   "TON",   "TOO",   "TOP",
"TOW",   "TOY",   "TRY",   "TUB",   "TUG",   "TUM",   "TUN",   "TWO",
"UN",    "UP",    "US",   "USE",   "VAN",   "VAT",   "VET",   "VIE",
"WAD",   "WAG",   "WAR",   "WAS",   "WAY",   "WE",    "WEB",   "WED",
"WEE",   "WET",   "WHO",   "WHY",   "WIN",   "WIT",   "WOK",   "WON",
"WOO",   "WOW",   "WRY",   "WU",    "YAM",   "YAP",   "YAW",   "YE",
"YEA",   "YES",   "YET",   "YOU",   "ABED",  "ABEL",  "ABET",  "ABLE",
"ABUT",  "ACHE",  "ACID",  "ACME",  "ACRE",  "ACTA",  "ACTS",  "ADAM",
"ADDS",  "ADEN",  "AFAR",  "AFRO",  "AGEE",  "AHEM",  "AHOY",  "AIDA",
"AIDE",  "AIDS",  "AIRY",  "AJAR",  "AKIN",  "ALAN",  "ALEC",  "ALGA",
"ALIA",  "ALLY",  "ALMA",  "ALOE",  "ALSO",  "ALTO",  "ALUM",  "ALVA",
"AMEN",  "AMES",  "AMID",  "AMMO",  "AMOK",  "AMOS",  "AMRA",  "ANDY",
"ANEW",  "ANNA",  "ANNE",  "ANTE",  "ANTI",  "AQUA",  "ARAB",  "ARCH",
"AREA",  "ARGO",  "ARID",  "ARMY",  "ARTS",  "ARTY",  "ASIA",  "ASKS",
"ATOM",  "AUNT",  "AURA",  "AUTO",  "AVER",  "AVID",  "AVIS",  "AVON",
"AVOW",  "AWAY",  "AWRY",  "BABE",  "BABY",  "BACH",  "BACK",  "BADE",
"BAIL",  "BAIT",  "BAKE",  "BALD",  "BALE",  "BALI",  "BALK",  "BALL",
"BALM",  "BAND",  "BANE",  "BANG",  "BANK",  "BARB",  "BARD",  "BARE",
"BARK",  "BARN",  "BARR",  "BASE",  "BASH",  "BASK",  "BASS",  "BATE",
"BATH",  "BAWD",  "BAWL",  "BEAD",  "BEAK",  "BEAM",  "BEAN",  "BEAR",
"BEAT",  "BEAU",  "BECK",  "BEEF",  "BEEN",  "BEER",  "BEET",  "BELA",
"BELL",  "BELT",  "BEND",  "BENT",  "BERG",  "BERN",  "BERT",  "BESS",
"BEST",  "BETA",  "BETH",  "BHOY",  "BIAS",  "BIDE",  "BIEN",  "BILE",
"BILK",  "BILL",  "BIND",  "BING",  "BIRD",  "BITE",  "BITS",  "BLAB",
"BLAT",  "BLED",  "BLEW",  "BLOB",  "BLOC",  "BLOT",  "BLOW",  "BLUE",
"BLUM",  "BLUR",  "BOAR",  "BOAT",  "BOCA",  "BOCK",  "BODE",  "BODY",
"BOGY",  "BOHR",  "BOIL",  "BOLD",  "BOLO",  "BOLT",  "BOMB",  "BONA",
"BOND",  "BONE",  "BONG",  "BONN",  "BONY",  "BOOK",  "BOOM",  "BOON",
"BOOT",  "BORE",  "BORG",  "BORN",  "BOSE",  "BOSS",  "BOTH",  "BOUT",
"BOWL",  "BOYD",  "BRAD",  "BRAE",  "BRAG",  "BRAN",  "BRAY",  "BRED",
"BREW",  "BRIG",  "BRIM",  "BROW",  "BUCK",  "BUDD",  "BUFF",  "BULB",
"BULK",  "BULL",  "BUNK",  "BUNT",  "BUOY",  "BURG",  "BURL",  "BURN",
"BURR",  "BURT",  "BURY",  "BUSH",  "BUSS",  "BUST",  "BUSY",  "BYTE",
"CADY",  "CAFE",  "CAGE",  "CAIN",  "CAKE",  "CALF",  "CALL",  "CALM",
"CAME",  "CANE",  "CANT",  "CARD",  "CARE",  "CARL",  "CARR",  "CART",
"CASE",  "CASH",  "CASK",  "CAST",  "CAVE",  "CEIL",  "CELL",  "CENT",
"CERN",  "CHAD",  "CHAR",  "CHAT",  "CHAW",  "CHEF",  "CHEN",  "CHEW",
"CHIC",  "CHIN",  "CHOU",  "CHOW",  "CHUB",  "CHUG",  "CHUM",  "CITE",
"CITY",  "CLAD",  "CLAM",  "CLAN",  "CLAW",  "CLAY",  "CLOD",  "CLOG",
"CLOT",  "CLUB",  "CLUE",  "COAL",  "COAT",  "COCA",  "COCK",  "COCO",
"CODA",  "CODE",  "CODY",  "COED",  "COIL",  "COIN",  "COKE",  "COLA",
"COLD",  "COLT",  "COMA",  "COMB",  "COME",  "COOK",  "COOL",  "COON",
"COOT",  "CORD",  "CORE",  "CORK",  "CORN",  "COST",  "COVE",  "COWL",
"CRAB",  "CRAG",  "CRAM",  "CRAY",  "CREW",  "CRIB",  "CROW",  "CRUD",
"CUBA",  "CUBE",  "CUFF",  "CULL",  "CULT",  "CUNY",  "CURB",  "CURD",
"CURE",  "CURL",  "CURT",  "CUTS",  "DADE",  "DALE",  "DAME",  "DANA",
"DANE",  "DANG",  "DANK",  "DARE",  "DARK",  "DARN",  "DART",  "DASH",
"DATA",  "DATE",  "DAVE",  "DAVY",  "DAWN",  "DAYS",  "DEAD",  "DEAF",
"DEAL",  "DEAN",  "DEAR",  "DEBT",  "DECK",  "DEED",  "DEEM",  "DEER",
"DEFT",  "DEFY",  "DELL",  "DENT",  "DENY",  "DESK",  "DIAL",  "DICE",
"DIED",  "DIET",  "DIME",  "DINE",  "DING",  "DINT",  "DIRE",  "DIRT",
"DISC",  "DISH",  "DISK",  "DIVE",  "DOCK",  "DOES",  "DOLE",  "DOLL",
"DOLT",  "DOME",  "DONE",  "DOOM",  "DOOR",  "DORA",  "DOSE",  "DOTE",
"DOUG",  "DOUR",  "DOVE",  "DOWN",  "DRAB",  "DRAG",  "DRAM",  "DRAW",
"DREW",  "DRUB",  "DRUG",  "DRUM",  "DUAL",  "DUCK",  "DUCT",  "DUEL",
"DUET",  "DUKE",  "DULL",  "DUMB",  "DUNE",  "DUNK",  "DUSK",  "DUST",
"DUTY",  "EACH",  "EARL",  "EARN",  "EASE",  "EAST",  "EASY",  "EBEN",
"ECHO",  "EDDY",  "EDEN",  "EDGE",  "EDGY",  "EDIT",  "EDNA",  "EGAN",
"ELAN",  "ELBA",  "ELLA",  "ELSE",  "EMIL",  "EMIT",  "EMMA",  "ENDS",
"ERIC",  "EROS",  "EVEN",  "EVER",  "EVIL",  "EYED",  "FACE",  "FACT",
"FADE",  "FAIL",  "FAIN",  "FAIR",  "FAKE",  "FALL",  "FAME",  "FANG",
"FARM",  "FAST",  "FATE",  "FAWN",  "FEAR",  "FEAT",  "FEED",  "FEEL",
"FEET",  "FELL",  "FELT",  "FEND",  "FERN",  "FEST",  "FEUD",  "FIEF",
"FIGS",  "FILE",  "FILL",  "FILM",  "FIND",  "FINE",  "FINK",  "FIRE",
"FIRM",  "FISH",  "FISK",  "FIST",  "FITS",  "FIVE",  "FLAG",  "FLAK",
"FLAM",  "FLAT",  "FLAW",  "FLEA",  "FLED",  "FLEW",  "FLIT",  "FLOC",
"FLOG",  "FLOW",  "FLUB",  "FLUE",  "FOAL",  "FOAM",  "FOGY",  "FOIL",
"FOLD",  "FOLK",  "FOND",  "FONT",  "FOOD",  "FOOL",  "FOOT",  "FORD",
"FORE",  "FORK",  "FORM",  "FORT",  "FOSS",  "FOUL",  "FOUR",  "FOWL",
"FRAU",  "FRAY",  "FRED",  "FREE",  "FRET",  "FREY",  "FROG",  "FROM",
"FUEL",  "FULL",  "FUME",  "FUND",  "FUNK",  "FURY",  "FUSE",  "FUSS",
"GAFF",  "GAGE",  "GAIL",  "GAIN",  "GAIT",  "GALA",  "GALE",  "GALL",
"GALT",  "GAME",  "GANG",  "GARB",  "GARY",  "GASH",  "GATE",  "GAUL",
"GAUR",  "GAVE",  "GAWK",  "GEAR",  "GELD",  "GENE",  "GENT",  "GERM",
"GETS",  "GIBE",  "GIFT",  "GILD",  "GILL",  "GILT",  "GINA",  "GIRD",
"GIRL",  "GIST",  "GIVE",  "GLAD",  "GLEE",  "GLEN",  "GLIB",  "GLOB",
"GLOM",  "GLOW",  "GLUE",  "GLUM",  "GLUT",  "GOAD",  "GOAL",  "GOAT",
"GOER",  "GOES",  "GOLD",  "GOLF",  "GONE",  "GONG",  "GOOD",  "GOOF",
"GORE",  "GORY",  "GOSH",  "GOUT",  "GOWN",  "GRAB",  "GRAD",  "GRAY",
"GREG",  "GREW",  "GREY",  "GRID",  "GRIM",  "GRIN",  "GRIT",  "GROW",
"GRUB",  "GULF",  "GULL",  "GUNK",  "GURU",  "GUSH",  "GUST",  "GWEN",
"GWYN",  "HAAG",  "HAAS",  "HACK",  "HAIL",  "HAIR",  "HALE",  "HALF",
"HALL",  "HALO",  "HALT",  "HAND",  "HANG",  "HANK",  "HANS",  "HARD",
"HARK",  "HARM",  "HART",  "HASH",  "HAST",  "HATE",  "HATH",  "HAUL",
"HAVE",  "HAWK",  "HAYS",  "HEAD",  "HEAL",  "HEAR",  "HEAT",  "HEBE",
"HECK",  "HEED",  "HEEL",  "HEFT",  "HELD",  "HELL",  "HELM",  "HERB",
"HERD",  "HERE",  "HERO",  "HERS",  "HESS",  "HEWN",  "HICK",  "HIDE",
"HIGH",  "HIKE",  "HILL",  "HILT",  "HIND",  "HINT",  "HIRE",  "HISS",
"HIVE",  "HOBO",  "HOCK",  "HOFF",  "HOLD",  "HOLE",  "HOLM",  "HOLT",
"HOME",  "HONE",  "HONK",  "HOOD",  "HOOF",  "HOOK",  "HOOT",  "HORN",
"HOSE",  "HOST",  "HOUR",  "HOVE",  "HOWE",  "HOWL",  "HOYT",  "HUCK",
"HUED",  "HUFF",  "HUGE",  "HUGH",  "HUGO",  "HULK",  "HULL",  "HUNK",
"HUNT",  "HURD",  "HURL",  "HURT",  "HUSH",  "HYDE",  "HYMN",  "IBIS",
"ICON",  "IDEA",  "IDLE",  "IFFY",  "INCA",  "INCH",  "INTO",  "IONS",
"IOTA",  "IOWA",  "IRIS",  "IRMA",  "IRON",  "ISLE",  "ITCH",  "ITEM",
"IVAN",  "JACK",  "JADE",  "JAIL",  "JAKE",  "JANE",  "JAVA",  "JEAN",
"JEFF",  "JERK",  "JESS",  "JEST",  "JIBE",  "JILL",  "JILT",  "JIVE",
"JOAN",  "JOBS",  "JOCK",  "JOEL",  "JOEY",  "JOHN",  "JOIN",  "JOKE",
"JOLT",  "JOVE",  "JUDD",  "JUDE",  "JUDO",  "JUDY",  "JUJU",  "JUKE",
"JULY",  "JUNE",  "JUNK",  "JUNO",  "JURY",  "JUST",  "JUTE",  "KAHN",
"KALE",  "KANE",  "KANT",  "KARL",  "KATE",  "KEEL",  "KEEN",  "KENO",
"KENT",  "KERN",  "KERR",  "KEYS",  "KICK",  "KILL",  "KIND",  "KING",
"KIRK",  "KISS",  "KITE",  "KLAN",  "KNEE",  "KNEW",  "KNIT",  "KNOB",
"KNOT",  "KNOW",  "KOCH",  "KONG",  "KUDO",  "KURD",  "KURT",  "KYLE",
"LACE",  "LACK",  "LACY",  "LADY",  "LAID",  "LAIN",  "LAIR",  "LAKE",
"LAMB",  "LAME",  "LAND",  "LANE",  "LANG",  "LARD",  "LARK",  "LASS",
"LAST",  "LATE",  "LAUD",  "LAVA",  "LAWN",  "LAWS",  "LAYS",  "LEAD",
"LEAF",  "LEAK",  "LEAN",  "LEAR",  "LEEK",  "LEER",  "LEFT",  "LEND",
"LENS",  "LENT",  "LEON",  "LESK",  "LESS",  "LEST",  "LETS",  "LIAR",
"LICE",  "LICK",  "LIED",  "LIEN",  "LIES",  "LIEU",  "LIFE",  "LIFT",
"LIKE",  "LILA",  "LILT",  "LILY",  "LIMA",  "LIMB",  "LIME",  "LIND",
"LINE",  "LINK",  "LINT",  "LION",  "LISA",  "LIST",  "LIVE",  "LOAD",
"LOAF",  "LOAM",  "LOAN",  "LOCK",  "LOFT",  "LOGE",  "LOIS",  "LOLA",
"LONE",  "LONG",  "LOOK",  "LOON",  "LOOT",  "LORD",  "LORE",  "LOSE",
"LOSS",  "LOST",  "LOUD",  "LOVE",  "LOWE",  "LUCK",  "LUCY",  "LUGE",
"LUKE",  "LULU",  "LUND",  "LUNG",  "LURA",  "LURE",  "LURK",  "LUSH",
"LUST",  "LYLE",  "LYNN",  "LYON",  "LYRA",  "MACE",  "MADE",  "MAGI",
"MAID",  "MAIL",  "MAIN",  "MAKE",  "MALE",  "MALI",  "MALL",  "MALT",
"MANA",  "MANN",  "MANY",  "MARC",  "MARE",  "MARK",  "MARS",  "MART",
"MARY",  "MASH",  "MASK",  "MASS",  "MAST",  "MATE",  "MATH",  "MAUL",
"MAYO",  "MEAD",  "MEAL",  "MEAN",  "MEAT",  "MEEK",  "MEET",  "MELD",
"MELT",  "MEMO",  "MEND",  "MENU",  "MERT",  "MESH",  "MESS",  "MICE",
"MIKE",  "MILD",  "MILE",  "MILK",  "MILL",  "MILT",  "MIMI",  "MIND",
"MINE",  "MINI",  "MINK",  "MINT",  "MIRE",  "MISS",  "MIST",  "MITE",
"MITT",  "MOAN",  "MOAT",  "MOCK",  "MODE",  "MOLD",  "MOLE",  "MOLL",
"MOLT",  "MONA",  "MONK",  "MONT",  "MOOD",  "MOON",  "MOOR",  "MOOT",
"MORE",  "MORN",  "MORT",  "MOSS",  "MOST",  "MOTH",  "MOVE",  "MUCH",
"MUCK",  "MUDD",  "MUFF",  "MULE",  "MULL",  "MURK",  "MUSH",  "MUST",
"MUTE",  "MUTT",  "MYRA",  "MYTH",  "NAGY",  "NAIL",  "NAIR",  "NAME",
"NARY",  "NASH",  "NAVE",  "NAVY",  "NEAL",  "NEAR",  "NEAT",  "NECK",
"NEED",  "NEIL",  "NELL",  "NEON",  "NERO",  "NESS",  "NEST",  "NEWS",
"NEWT",  "NIBS",  "NICE",  "NICK",  "NILE",  "NINA",  "NINE",  "NOAH",
"NODE",  "NOEL",  "NOLL",  "NONE",  "NOOK",  "NOON",  "NORM",  "NOSE",
"NOTE",  "NOUN",  "NOVA",  "NUDE",  "NULL",  "NUMB",  "OATH",  "OBEY",
"OBOE",  "ODIN",  "OHIO",  "OILY",  "OINT",  "OKAY",  "OLAF",  "OLDY",
"OLGA",  "OLIN",  "OMAN",  "OMEN",  "OMIT",  "ONCE",  "ONES",  "ONLY",
"ONTO",  "ONUS",  "ORAL",  "ORGY",  "OSLO",  "OTIS",  "OTTO",  "OUCH",
"OUST",  "OUTS",  "OVAL",  "OVEN",  "OVER",  "OWLY",  "OWNS",  "QUAD",
"QUIT",  "QUOD",  "RACE",  "RACK",  "RACY",  "RAFT",  "RAGE",  "RAID",
"RAIL",  "RAIN",  "RAKE",  "RANK",  "RANT",  "RARE",  "RASH",  "RATE",
"RAVE",  "RAYS",  "READ",  "REAL",  "REAM",  "REAR",  "RECK",  "REED",
"REEF",  "REEK",  "REEL",  "REID",  "REIN",  "RENA",  "REND",  "RENT",
"REST",  "RICE",  "RICH",  "RICK",  "RIDE",  "RIFT",  "RILL",  "RIME",
"RING",  "RINK",  "RISE",  "RISK",  "RITE",  "ROAD",  "ROAM",  "ROAR",
"ROBE",  "ROCK",  "RODE",  "ROIL",  "ROLL",  "ROME",  "ROOD",  "ROOF",
"ROOK",  "ROOM",  "ROOT",  "ROSA",  "ROSE",  "ROSS",  "ROSY",  "ROTH",
"ROUT",  "ROVE",  "ROWE",  "ROWS",  "RUBE",  "RUBY",  "RUDE",  "RUDY",
"RUIN",  "RULE",  "RUNG",  "RUNS",  "RUNT",  "RUSE",  "RUSH",  "RUSK",
"RUSS",  "RUST",  "RUTH",  "SACK",  "SAFE",  "SAGE",  "SAID",  "SAIL",
"SALE",  "SALK",  "SALT",  "SAME",  "SAND",  "SANE",  "SANG",  "SANK",
"SARA",  "SAUL",  "SAVE",  "SAYS",  "SCAN",  "SCAR",  "SCAT",  "SCOT",
"SEAL",  "SEAM",  "SEAR",  "SEAT",  "SEED",  "SEEK",  "SEEM",  "SEEN",
"SEES",  "SELF",  "SELL",  "SEND",  "SENT",  "SETS",  "SEWN",  "SHAG",
"SHAM",  "SHAW",  "SHAY",  "SHED",  "SHIM",  "SHIN",  "SHOD",  "SHOE",
"SHOT",  "SHOW",  "SHUN",  "SHUT",  "SICK",  "SIDE",  "SIFT",  "SIGH",
"SIGN",  "SILK",  "SILL",  "SILO",  "SILT",  "SINE",  "SING",  "SINK",
"SIRE",  "SITE",  "SITS",  "SITU",  "SKAT",  "SKEW",  "SKID",  "SKIM",
"SKIN",  "SKIT",  "SLAB",  "SLAM",  "SLAT",  "SLAY",  "SLED",  "SLEW",
"SLID",  "SLIM",  "SLIT",  "SLOB",  "SLOG",  "SLOT",  "SLOW",  "SLUG",
"SLUM",  "SLUR",  "SMOG",  "SMUG",  "SNAG",  "SNOB",  "SNOW",  "SNUB",
"SNUG",  "SOAK",  "SOAR",  "SOCK",  "SODA",  "SOFA",  "SOFT",  "SOIL",
"SOLD",  "SOME",  "SONG",  "SOON",  "SOOT",  "SORE",  "SORT",  "SOUL",
"SOUR",  "SOWN",  "STAB",  "STAG",  "STAN",  "STAR",  "STAY",  "STEM",
"STEW",  "STIR",  "STOW",  "STUB",  "STUN",  "SUCH",  "SUDS",  "SUIT",
"SULK",  "SUMS",  "SUNG",  "SUNK",  "SURE",  "SURF",  "SWAB",  "SWAG",
"SWAM",  "SWAN",  "SWAT",  "SWAY",  "SWIM",  "SWUM",  "TACK",  "TACT",
"TAIL",  "TAKE",  "TALE",  "TALK",  "TALL",  "TANK",  "TASK",  "TATE",
"TAUT",  "TEAL",  "TEAM",  "TEAR",  "TECH",  "TEEM",  "TEEN",  "TEET",
"TELL",  "TEND",  "TENT",  "TERM",  "TERN",  "TESS",  "TEST",  "THAN",
"THAT",  "THEE",  "THEM",  "THEN",  "THEY",  "THIN",  "THIS",  "THUD",
"THUG",  "TICK",  "TIDE",  "TIDY",  "TIED",  "TIER",  "TILE",  "TILL",
"TILT",  "TIME",  "TINA",  "TINE",  "TINT",  "TINY",  "TIRE",  "TOAD",
"TOGO",  "TOIL",  "TOLD",  "TOLL",  "TONE",  "TONG",  "TONY",  "TOOK",
"TOOL",  "TOOT",  "TORE",  "TORN",  "TOTE",  "TOUR",  "TOUT",  "TOWN",
"TRAG",  "TRAM",  "TRAY",  "TREE",  "TREK",  "TRIG",  "TRIM",  "TRIO",
"TROD",  "TROT",  "TROY",  "TRUE",  "TUBA",  "TUBE",  "TUCK",  "TUFT",
"TUNA",  "TUNE",  "TUNG",  "TURF",  "TURN",  "TUSK",  "TWIG",  "TWIN",
"TWIT",  "ULAN",  "UNIT",  "URGE",  "USED",  "USER",  "USES",  "UTAH",
"VAIL",  "VAIN",  "VALE",  "VARY",  "VASE",  "VAST",  "VEAL",  "VEDA",
"VEIL",  "VEIN",  "VEND",  "VENT",  "VERB",  "VERY",  "VETO",  "VICE",
"VIEW",  "VINE",  "VISE",  "VOID",  "VOLT",  "VOTE",  "WACK",  "WADE",
"WAGE",  "WAIL",  "WAIT",  "WAKE",  "WALE",  "WALK",  "WALL",  "WALT",
"WAND",  "WANE",  "WANG",  "WANT",  "WARD",  "WARM",  "WARN",  "WART",
"WASH",  "WAST",  "WATS",  "WATT",  "WAVE",  "WAVY",  "WAYS",  "WEAK",
"WEAL",  "WEAN",  "WEAR",  "WEED",  "WEEK",  "WEIR",  "WELD",  "WELL",
"WELT",  "WENT",  "WERE",  "WERT",  "WEST",  "WHAM",  "WHAT",  "WHEE",
"WHEN",  "WHET",  "WHOA",  "WHOM",  "WICK",  "WIFE",  "WILD",  "WILL",
"WIND",  "WINE",  "WING",  "WINK",  "WINO",  "WIRE",  "WISE",  "WISH",
"WITH",  "WOLF",  "WONT",  "WOOD",  "WOOL",  "WORD",  "WORE",  "WORK",
"WORM",  "WORN",  "WOVE",  "WRIT",  "WYNN",  "YALE",  "YANG",  "YANK",
"YARD",  "YARN",  "YAWL",  "YAWN",  "YEAH",  "YEAR",  "YELL",  "YOGA",
"YOKE"]

def WordFromNumber(number):
    return DefaultDictionary[number] 

ReverseDefaultDictionary = {}
for i in range(0, len(DefaultDictionary)):
    ReverseDefaultDictionary[DefaultDictionary[i]] = i

def NumberFromWord(word):
    return ReverseDefaultDictionary[word.upper()]

########NEW FILE########
__FILENAME__ = keywrangling
"""
PyOTP, the Python One-Time Password module.

keywrangling.py: key handling routines for the otp module. 

<insert Python license here>
"""

__version__ = '$Revision: 1.4 $'

import types
from AppendixB import DefaultDictionary, WordFromNumber, NumberFromWord

def keyformat(key):
    """Return the type of a key or list of keys (all of which must
    be in the same format).
    
    Result: 'sixword', 'hex', 'long', 'raw', or None for an
    unrecognised key format.
    
    LIMITATIONS: This routine doesn't go to nearly enough effort
    to double- and triple-check key types. For example, any string
    of length 16 will be treated as a hex key. More checks should
    be added in the future."""
    
    if type(key) == types.ListType:
        return keyformat(key[0])
    if type(key) == types.LongType:
        return 'long'
    elif type(key) == types.StringType:
        if len(key) == 8:
            return 'raw'
        elif len(key) == 19 and len(key.split(' ')) == 4:
            return 'hex'
        elif len(key.split(' ')) == 6:
            return 'sixword'
        else:
            return None
    else:
        return None

def long_from_raw(hash):
    """Fold to a long, a digest supplied as a string."""
    
    hashnum = 0L
    for h in hash:
        hashnum <<= 8
        hashnum |= ord(h)
        
    return hashnum

def sixword_from_raw(key, dictionary=DefaultDictionary):
    return sixword_from_long(long_from_raw(key), dictionary)

def sixword_from_hex(key, dictionary=DefaultDictionary):
    return sixword_from_long(long_from_hex(key), dictionary)

def hex_from_long(key):
    k = '%016x' % key
    return ' '.join( [ k[0:4], k[4:8], k[8:12], k[12:16] ] ).upper()

def hex_from_raw(key):
    return hex_from_long(long_from_raw(key))

def hex_from_sixword(key):
    return hex_from_long(long_from_sixword(key))

def long_from_hex(key):
    return long(''.join(key.split(' ')).lower(), 16)

def checksummed_long(key):
    sum, k = 0, key
    for i in range(0, 32):
        sum = sum + ( k % 4 )
        k = k >> 2
    return ( key << 2 ) | ( sum % 4 )
    
def sixword_from_long(key, dictionary=DefaultDictionary):
    key = checksummed_long(key)
    
    words = []
    for i in range(0,6):
        words = [dictionary[key % 2048]] + words
        key = key >> 11
    return ' '.join(words)

def long_from_sixword(key):
    # no alternative dictionary format yet! 
    words = key.split(' ')
    for w in words:
        wordIndex = NumberFromWord(w)
        try:
            wordCheck = WordFromNumber(wordIndex)
        except:
            wordCheck = None
        print wordIndex, wordCheck

_KEYCONVERSIONTABLE = {
    'sixword' : { 'raw'     : sixword_from_raw ,
                  'long'    : sixword_from_long ,
                  'hex'     : sixword_from_hex }, 
    'long' :    { 'raw'     : long_from_raw ,
                  'sixword' : long_from_sixword,
                  'hex'     : long_from_hex },
    'hex' :     { 'raw'     : hex_from_raw ,
                  'sixword' : hex_from_sixword,
                  'long'    : hex_from_long }
    }

def convertkey(format, key_or_keylist):
    """Convert a key or a list of keys from one format to another.

    format         -- 'sixword', 'hex', or 'long'
    key_or_keylist -- either a key, or a list of keys ALL OF THE
                      SAME FORMAT."""
    
    originalformat = keyformat(key_or_keylist)
    if originalformat == format: # just in case! 
        return key_or_keylist
    
    conversionfunction = _KEYCONVERSIONTABLE[format][originalformat]
    if type(key_or_keylist) == types.ListType:
        return map(conversionfunction, key_or_keylist)
    else:
        return conversionfunction(key_or_keylist)

########NEW FILE########
__FILENAME__ = otp
"""
The otp module implements the RFC2289 (previously RFC1938) standard
for One-Time Passwords.

For details of RFC2289 adherence, module limitations, and a to-do list,
please see __init__.py 

<insert Python license here>
"""

__version__ = '$Revision: 1.4 $'

import string, random
from Crypto.Hash import MD4
try:
    from hashlib import sha1 as SHA
    from hashlib import md5 as MD5
except ImportError:
    from Crypto.Hash import SHA, MD5
from AppendixB import DefaultDictionary
from keywrangling import keyformat, convertkey

_VALIDSEEDCHARACTERS = string.letters + string.digits

_HASHMODULE = { 'md4': MD4, 'md5' : MD5, 'sha' : SHA }

def _fold_md5(digest):
    result = ''
    if len(digest)<16:
        print digest
        raise AssertionError
    for i in range(0,8):
        result = result + chr(ord(digest[i]) ^ ord(digest[i+8]))
    return result
    
def _fold_sha(hash):
    # BROKEN
    ordhash = map(ord, hash)
    result = [0, 0, 0, 0, 0, 0, 0, 0]
    
    result[3] = ordhash[0] ^ ordhash[8] ^  ordhash[16] 
    result[2] = ordhash[1] ^ ordhash[9] ^  ordhash[17]
    result[1] = ordhash[2] ^ ordhash[10] ^ ordhash[18]
    result[0] = ordhash[3] ^ ordhash[11] ^ ordhash[19]
    result[7] = ordhash[4] ^ ordhash[12]
    result[6] = ordhash[5] ^ ordhash[13]
    result[5] = ordhash[6] ^ ordhash[14]
    result[4] = ordhash[7] ^ ordhash[15]

    return ''.join(map(chr, result))

_FOLDFUNCTION = { 'md4': _fold_md5, 'md5' : _fold_md5, 'sha' : _fold_sha }

def generate(passphrase, seed,
             startkey=0, numkeys=499, hashfunction='md5',
             keyformat = 'hex'):
    """Generate a sequence of OTP keys from a pass phrase and seed
    using the specified hash function. Results are returned as a
    list of long integers suitable for conversion to six-word or
    hexadecimal one-time passwords. 
    
    passphrase   -- the shared secret pass phrase as supplied by the
                    user over a secure connection and stored by the
                    OTP server. 
    seed         -- the seed phrase used both to initialize keys and
                    sent in the clear by OTP servers as part of the
                    OTP challenge.
    startkey     -- the number of iterations to run before the first
                    key in the result list is taken.
    numkeys      -- the number of keys to return in the result list.
    hashfunction -- the hash function to use when generating keys.
    keyformat    -- the key format to generate
    """
    
    # check arguments for validity and standards compliance
    if hashfunction not in _HASHMODULE.keys():
        raise Exception, 'hashfunction'
    if len(passphrase) not in range(4,64):
        raise Exception, 'passphrase length'
    if len(seed) not in range(1,17):
        raise Exception, 'seed length'
    for x in seed:
        if not x in _VALIDSEEDCHARACTERS:
            raise Exception, 'seed composition'
    if startkey < 0:
        raise Exception, 'startkey'
    if numkeys < 1:
        raise Exception, 'numkeys'
    # not checked: argument types, startkey and numkeys out of range
    
    hashmodule = _HASHMODULE[hashfunction]
    folder = _FOLDFUNCTION[hashfunction]
    
    hash = folder(hashmodule.new(seed + passphrase).digest())
    
    # discard the first <startkey> keys    
    for iterations in range(0, startkey):
        hash = folder(hashmodule.new(hash).digest())
        
    # generate the results
    keylist = []
    
    for keys in range(0, numkeys):
        keylist.append(hash)
        hash = folder(hashmodule.new(hash).digest())
        
    return convertkey(keyformat,keylist)    

def generateseed(length=5):
    """Generate a random, valid seed of a given length."""
    # check standards compliance of arguments
    if length not in range(1,11):
        raise Exception, 'length'
    seed = ''
    vsclen = len(_VALIDSEEDCHARACTERS)
    bignum = 2L**32 - 1
    for i in range(0, length):
        index = long(random.random() * bignum) % vsclen
        seed = seed + _VALIDSEEDCHARACTERS[index]
    return seed

########NEW FILE########
__FILENAME__ = FileLogger
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Logging to the file system.
"""
import os
from Exscript.Logfile import Logfile
from Exscript.Logger import Logger

class FileLogger(Logger):
    """
    A Logger that stores logs into files.
    """

    def __init__(self,
                 logdir,
                 mode     = 'a',
                 delete   = False,
                 clearmem = True):
        """
        The logdir argument specifies the location where the logs
        are stored. The mode specifies whether to append the existing logs
        (if any). If delete is True, the logs are deleted after they are
        completed, unless they have an error in them.
        If clearmem is True, the logger does not store a reference to
        the log in it. If you want to use the functions from
        L{Exscript.util.report} with the logger, clearmem must be False.
        """
        Logger.__init__(self)
        self.logdir   = logdir
        self.mode     = mode
        self.delete   = delete
        self.clearmem = clearmem
        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

    def add_log(self, job_id, name, attempt):
        if attempt > 1:
            name += '_retry%d' % (attempt - 1)
        filename = os.path.join(self.logdir, name + '.log')
        log      = Logfile(name, filename, self.mode, self.delete)
        log.started()
        self.logs[job_id].append(log)
        return log

    def log_aborted(self, job_id, exc_info):
        Logger.log_aborted(self, job_id, exc_info)
        if self.clearmem:
            self.logs.pop(job_id)

    def log_succeeded(self, job_id):
        Logger.log_succeeded(self, job_id)
        if self.clearmem:
            self.logs.pop(job_id)

########NEW FILE########
__FILENAME__ = Host
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Representing a device to connect with.
"""
from Exscript.Account   import Account
from Exscript.util.cast import to_list
from Exscript.util.ipv4 import is_ip, clean_ip
from Exscript.util.url  import Url

def _is_ip(string):
    # Adds IPv6 support.
    return ':' in string or is_ip(string)

class Host(object):
    """
    Represents a device on which to open a connection.
    """
    __slots__ = ('protocol',
                 'vars',
                 'account',
                 'name',
                 'address',
                 'tcp_port',
                 'options')

    def __init__(self, uri, default_protocol = 'telnet'):
        """
        Constructor. The given uri is passed to Host.set_uri().
        The default_protocol argument defines the protocol that is used
        in case the given uri does not specify it.

        @type  uri: string
        @param uri: A hostname; see set_uri() for more info.
        @type  default_protocol: string
        @param default_protocol: The protocol name.
        """
        self.protocol = default_protocol
        self.vars     = None    # To save memory, do not init with a dict.
        self.account  = None
        self.name     = None
        self.address  = None
        self.tcp_port = None
        self.options  = None
        self.set_uri(uri) 

    def __copy__(self):
        host = Host(self.get_uri())
        host.set_name(self.get_name())
        return host

    def set_uri(self, uri):
        """
        Defines the protocol, hostname/address, TCP port number, username,
        and password from the given URL. The hostname may be URL formatted,
        so the following formats are all valid:

            - myhostname
            - myhostname.domain
            - ssh:hostname
            - ssh:hostname.domain
            - ssh://hostname
            - ssh://user@hostname
            - ssh://user:password@hostname
            - ssh://user:password@hostname:21

        For a list of supported protocols please see set_protocol().

        @type  uri: string
        @param uri: An URL formatted hostname.
        """
        try:
            uri = Url.from_string(uri, self.protocol)
        except ValueError:
            raise ValueError('Hostname parse error: ' + repr(uri))
        hostname = uri.hostname or ''
        name     = uri.path and hostname + uri.path or hostname
        self.set_protocol(uri.protocol)
        self.set_tcp_port(uri.port)
        self.set_name(name)
        self.set_address(name)

        if uri.username is not None \
           or uri.password1 is not None \
           or uri.password2:
            account = Account(uri.username, uri.password1, uri.password2)
            self.set_account(account)

        for key, val in uri.vars.iteritems():
            self.set(key, val)

    def get_uri(self):
        """
        Returns a URI formatted representation of the host, including all
        of it's attributes except for the name. Uses the
        address, not the name of the host to build the URI.

        @rtype:  str
        @return: A URI.
        """
        url = Url()
        url.protocol = self.get_protocol()
        url.hostname = self.get_address()
        url.port     = self.get_tcp_port()
        url.vars     = dict((k, to_list(v))
                            for (k, v) in self.get_all().iteritems()
                            if isinstance(v, str) or isinstance(v, list))

        if self.account:
            url.username  = self.account.get_name()
            url.password1 = self.account.get_password()
            url.password2 = self.account.authorization_password

        return str(url)

    def get_dict(self):
        """
        Returns a dict containing the host's attributes. The following
        keys are contained:

            - hostname
            - address
            - protocol
            - port

        @rtype:  dict
        @return: The resulting dictionary.
        """
        return {'hostname': self.get_name(),
                'address':  self.get_address(),
                'protocol': self.get_protocol(),
                'port':     self.get_tcp_port()}

    def set_name(self, name):
        """
        Set the hostname of the remote host without
        changing username, password, protocol, and TCP port number.

        @type  name: string
        @param name: A hostname or IP address.
        """
        self.name = name

    def get_name(self):
        """
        Returns the name.

        @rtype:  string
        @return: The hostname excluding the name.
        """
        return self.name

    def set_address(self, address):
        """
        Set the address of the remote host the is contacted, without
        changing hostname, username, password, protocol, and TCP port
        number.
        This is the actual address that is used to open the connection.

        @type  address: string
        @param address: A hostname or IP name.
        """
        if is_ip(address):
            self.address = clean_ip(address)
        else:
            self.address = address

    def get_address(self):
        """
        Returns the address that is used to open the connection.

        @rtype:  string
        @return: The address that is used to open the connection.
        """
        return self.address

    def set_protocol(self, protocol):
        """
        Defines the protocol. The following protocols are currently
        supported:

            - telnet: Telnet
            - ssh1: SSH version 1
            - ssh2: SSH version 2
            - ssh: Automatically selects the best supported SSH version
            - dummy: A virtual device that accepts any command, but that
              does not respond anything useful.
            - pseudo: A virtual device that loads a file with the given
              "hostname". The given file is a Python file containing
              information on how the virtual device shall respond to
              commands. For more information please refer to the
              documentation of
              protocols.Dummy.load_command_handler_from_file().

        @type  protocol: string
        @param protocol: The protocol name.
        """
        self.protocol = protocol

    def get_protocol(self):
        """
        Returns the name of the protocol.

        @rtype:  string
        @return: The protocol name.
        """
        return self.protocol

    def set_option(self, name, value):
        """
        Defines a (possibly protocol-specific) option for the host.
        Possible options include:

            verify_fingerprint: bool

        @type  name: str
        @param name: The option name.
        @type  value: object
        @param value: The option value.
        """
        if name not in ('debug', 'verify_fingerprint',):
            raise TypeError('No such option: ' + repr(name))
        if self.options is None:
            self.options = {}
        self.options[name] = value

    def get_option(self, name, default = None):
        """
        Returns the value of the given option if it is defined, returns
        the given default value otherwise.

        @type  name: str
        @param name: The option name.
        @type  default: object
        @param default: A default value.
        """
        if self.options is None:
            return default
        return self.options.get(name, default)

    def get_options(self):
        """
        Return a dictionary containing all defined options.

        @rtype:  dict
        @return: The options.
        """
        if self.options is None:
            return {}
        return self.options

    def set_tcp_port(self, tcp_port):
        """
        Defines the TCP port number.

        @type  tcp_port: int
        @param tcp_port: The TCP port number.
        """
        if tcp_port is None:
            self.tcp_port = None
            return
        self.tcp_port = int(tcp_port)

    def get_tcp_port(self):
        """
        Returns the TCP port number.

        @rtype:  string
        @return: The TCP port number.
        """
        return self.tcp_port

    def set_account(self, account):
        """
        Defines the account that is used to log in.

        @type  account: L{Exscript.Account}
        @param account: The account.
        """
        self.account = account

    def get_account(self):
        """
        Returns the account that is used to log in.

        @rtype:  Account
        @return: The account.
        """
        return self.account

    def set(self, name, value):
        """
        Stores the given variable/value in the object for later retrieval.

        @type  name: string
        @param name: The name of the variable.
        @type  value: object
        @param value: The value of the variable.
        """
        if self.vars is None:
            self.vars = {}
        self.vars[name] = value

    def set_all(self, variables):
        """
        Like set(), but replaces all variables by using the given
        dictionary. In other words, passing an empty dictionary
        results in all variables being removed.

        @type  variables: dict
        @param variables: The dictionary with the variables.
        """
        self.vars = dict(variables)

    def append(self, name, value):
        """
        Appends the given value to the list variable with the given name.

        @type  name: string
        @param name: The name of the variable.
        @type  value: object
        @param value: The appended value.
        """
        if self.vars is None:
            self.vars = {}
        if name in self.vars:
            self.vars[name].append(value)
        else:
            self.vars[name] = [value]

    def set_default(self, name, value):
        """
        Like set(), but only sets the value if the variable is not already
        defined.

        @type  name: string
        @param name: The name of the variable.
        @type  value: object
        @param value: The value of the variable.
        """
        if self.vars is None:
            self.vars = {}
        if name not in self.vars:
            self.vars[name] = value

    def has_key(self, name):
        """
        Returns True if the variable with the given name is defined, False
        otherwise.

        @type  name: string
        @param name: The name of the variable.
        @rtype:  bool
        @return: Whether the variable is defined.
        """
        if self.vars is None:
            return False
        return name in self.vars

    def get(self, name, default = None):
        """
        Returns the value of the given variable, or the given default
        value if the variable is not defined.

        @type  name: string
        @param name: The name of the variable.
        @type  default: object
        @param default: The default value.
        @rtype:  object
        @return: The value of the variable.
        """
        if self.vars is None:
            return default
        return self.vars.get(name, default)

    def get_all(self):
        """
        Returns a dictionary containing all variables.

        @rtype:  dict
        @return: The dictionary with the variables.
        """
        if self.vars is None:
            self.vars = {}
        return self.vars

########NEW FILE########
__FILENAME__ = Append
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib         import Token
from Exscript.interpreter.Term import Term

class Append(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Append', lexer, parser, parent)

        # First expect an expression.
        lexer.expect(self, 'keyword', 'append')
        lexer.expect(self, 'whitespace')
        self.expr = Term(lexer, parser, parent)

        # Expect "to" keyword.
        lexer.expect(self, 'whitespace')
        lexer.expect(self, 'keyword', 'to')

        # Expect a variable name.
        lexer.expect(self, 'whitespace')
        _, self.varname = lexer.token()
        lexer.expect(self, 'varname')
        self.parent.define(**{self.varname: []})

        self.mark_end()

    def value(self, context):
        existing = self.parent.get(self.varname)
        args     = {self.varname: existing + self.expr.value(context)}
        self.parent.define(**args)
        return 1

    def dump(self, indent = 0):
        print (' ' * indent) + self.name, "to", self.varname
        self.expr.dump(indent + 1)

########NEW FILE########
__FILENAME__ = Assign
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Expression
from Exscript.parselib import Token

class Assign(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Assign', lexer, parser, parent)

        # Extract the variable name.
        _, self.varname = lexer.token()
        lexer.expect(self, 'varname')
        lexer.expect(self, 'whitespace')
        lexer.expect(self, 'assign')
        lexer.expect(self, 'whitespace')

        if self.varname.startswith('__'):
            msg = 'Assignment to internal variable ' + self.varname
            lexer.syntax_error(msg, self)

        self.expression = Expression.Expression(lexer, parser, parent)
        self.parent.define(**{self.varname: None})


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.varname, 'start'
        self.expression.dump(indent + 1)
        print (' ' * indent) + self.name, self.varname, 'start'

    def value(self, context):
        result = self.expression.value(context)
        self.parent.define(**{self.varname: result})
        return result

########NEW FILE########
__FILENAME__ = Code
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
import Template
from Exscript.interpreter.Scope        import Scope
from Exscript.interpreter.Append       import Append
from Exscript.interpreter.Assign       import Assign
from Exscript.interpreter.Enter        import Enter
from Exscript.interpreter.Extract      import Extract
from Exscript.interpreter.Fail         import Fail
from Exscript.interpreter.FunctionCall import FunctionCall
from Exscript.interpreter.IfCondition  import IfCondition
from Exscript.interpreter.Loop         import Loop
from Exscript.interpreter.Try          import Try
from Exscript.interpreter.String       import varname_re

varname  = varname_re.pattern
keywords = ['append',
            'as',
            'else',
            'end',
            'enter',
            'extract',
            'fail',
            'false',
            'from',
            'if',
            'into',
            'loop',
            'try',
            'to',
            'true',
            'until',
            'when',
            'while']
operators = ['in',
             r'not\s+in',
             r'is\s+not',
             'is',
             'ge',
             'gt',
             'le',
             'lt',
             'matches']

grammar = (
    ('escaped_data',        r'\\.'),
    ('regex_delimiter',     r'/'),
    ('string_delimiter',    r'"'),
    ('open_curly_bracket',  r'{'),
    ('close_curly_bracket', r'}'),
    ('close_bracket',       r'\)'),
    ('comma',               r','),
    ('whitespace',          r'[ \t]+'),
    ('keyword',             r'\b(?:' + '|'.join(keywords)  + r')\b'),
    ('assign',              r'='),
    ('octal_number',        r'0\d+'),
    ('hex_number',          r'0x(?:\w\w)+'),
    ('comparison',          r'\b(?:' + '|'.join(operators) + r')\b'),
    ('arithmetic_operator', r'(?:\*|\+|-|%|\.)'),
    ('logical_operator',    r'\b(?:and|or|not)\b'),
    ('open_function_call',  varname + r'(?:\.' + varname + r')*\('),
    ('varname',             varname),
    ('number',              r'\d+'),
    ('newline',             r'[\r\n]'),
    ('raw_data',            r'[^\r\n{}]+')
)

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))

class Code(Scope):
    def __init__(self, lexer, parser, parent):
        Scope.__init__(self, 'Code', lexer, parser, parent)
        lexer.set_grammar(grammar_c)
        while True:
            lexer.skip(['whitespace', 'newline'])
            if lexer.next_if('close_curly_bracket'):
                if isinstance(parent, Template.Template):
                    break
                self.add(Template.Template(lexer, parser, self))
            elif lexer.current_is('keyword', 'append'):
                self.add(Append(lexer, parser, self))
            elif lexer.current_is('keyword', 'extract'):
                self.add(Extract(lexer, parser, self))
            elif lexer.current_is('keyword', 'fail'):
                self.add(Fail(lexer, parser, self))
            elif lexer.current_is('keyword', 'if'):
                self.add(IfCondition(lexer, parser, self))
            elif lexer.current_is('keyword', 'loop'):
                self.add(Loop(lexer, parser, self))
            elif lexer.current_is('varname'):
                self.add(Assign(lexer, parser, self))
            elif lexer.current_is('keyword', 'try'):
                self.add(Try(lexer, parser, self))
            elif lexer.current_is('keyword', 'enter'):
                self.add(Enter(lexer, parser, self))
            elif lexer.current_is('keyword', 'else'):
                if not isinstance(parent, Code):
                    lexer.syntax_error('"end" without a scope start', self)
                break
            elif lexer.next_if('keyword', 'end'):
                if not isinstance(parent, Code):
                    lexer.syntax_error('"end" without a scope start', self)
                lexer.skip(['whitespace', 'newline'])
                break
            elif lexer.current_is('open_function_call'):
                self.add(FunctionCall(lexer, parser, self))
            else:
                lexer.syntax_error('Unexpected %s "%s"' % lexer.token(), self)
        lexer.restore_grammar()

########NEW FILE########
__FILENAME__ = Enter
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib            import Token
from Exscript.interpreter.Execute import Execute

class Enter(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Enter', lexer, parser, parent)

        lexer.expect(self, 'keyword', 'enter')
        lexer.skip(['whitespace', 'newline'])

        self.execute = Execute(lexer, parser, parent, '')

    def value(self, context):
        return self.execute.value(context)

    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.execute.dump(indent + 1)

########NEW FILE########
__FILENAME__ = Exception
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
class ExscriptException(Exception):
    pass

class FailException(ExscriptException):
    """
    This exception type is used if the "fail" command was used in a template.
    """
    pass

class PermissionError(ExscriptException):
    """
    Raised if an insecure function was called when the parser is in secure
    mode.
    """
    pass

########NEW FILE########
__FILENAME__ = Execute
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib           import Token
from Exscript.interpreter.String import String, string_re

class Execute(String):
    def __init__(self, lexer, parser, parent, command):
        Token.__init__(self, 'Execute', lexer, parser, parent)
        self.string        = command
        self.no_prompt     = parser.no_prompt
        self.strip_command = parser.strip_command

        # The lexer has parsed the command, including a newline.
        # Make the debugger point to the beginning of the command.
        self.start -= len(command) + 1
        self.mark_end(self.start + len(command))

        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, command)
        self.parent.define(__response__ = [])

    def value(self, context):
        if not self.parent.is_defined('__connection__'):
            error = 'Undefined variable "__connection__"'
            self.lexer.runtime_error(error, self)
        conn = self.parent.get('__connection__')

        # Substitute variables in the command for values.
        command = string_re.sub(self.variable_sub_cb, self.string)
        command = command.lstrip()

        # Execute the command.
        if self.no_prompt:
            conn.send(command + '\r')
            response = ''
        else:
            conn.execute(command)
            response = conn.response.replace('\r\n', '\n')
            response = response.replace('\r', '\n').split('\n')

        if self.strip_command:
            response = response[1:]
        if len(response) == 0:
            response = ['']

        self.parent.define(__response__ = response)
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.string

########NEW FILE########
__FILENAME__ = Expression
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib                   import Token
from Exscript.interpreter.ExpressionNode import ExpressionNode

class Expression(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Expression', lexer, parser, parent)

        # Parse the expression.
        self.root = ExpressionNode(lexer, parser, parent)

        # Reorder the tree according to the operator priorities.
        self.prioritize(self.root)
        self.mark_end()


    def prioritize(self, start, prio = 1):
        #print "Prioritizing from", start.op, "with prio", prio, (start.lft, start.rgt)
        if prio == 6:
            return
        root = start
        while root is not None and root.priority() <= prio:
            root = root.rgt
        if root is None:
            self.prioritize(start, prio + 1)
            return

        # Find the next node that has the current priority.
        previous = root
        current  = root.rgt
        while current is not None and current.priority() != prio:
            previous = current
            current  = current.rgt
        if current is None:
            self.prioritize(start, prio + 1)
            return

        # Reparent the expressions.
        #print "Prio of", root.op, 'is higher than', current.op
        previous.rgt = current.lft
        current.lft  = root

        # Change the pointer of the parent of the root node.
        # If this was the root of the entire tree we need to change that as
        # well.
        if root.parent_node is None:
            self.root = current
        elif root.parent_node.lft == root:
            root.parent_node.lft = current
        elif root.parent_node.rgt == root:
            root.parent_node.rgt = current

        root.parent_node = current

        # Go ahead prioritizing the children.
        self.prioritize(current.lft, prio + 1)
        self.prioritize(current.rgt, prio)

    def value(self, context):
        return self.root.value(context)

    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.root.dump(indent + 1)
        print (' ' * indent) + self.name, 'end.'

########NEW FILE########
__FILENAME__ = ExpressionNode
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Term
from Exscript.parselib import Token

class ExpressionNode(Token):
    def __init__(self, lexer, parser, parent, parent_node = None):
        # Skip whitespace before initializing the token to make sure that self.start
        # points to the beginning of the expression (which makes for prettier error
        # messages).
        lexer.skip(['whitespace', 'newline'])

        Token.__init__(self, 'ExpressionNode', lexer, parser, parent)
        self.lft         = None
        self.rgt         = None
        self.op          = None
        self.op_type     = None
        self.parent_node = parent_node

        # The "not" operator requires special treatment because it is
        # positioned left of the term.
        if not lexer.current_is('logical_operator', 'not'):
            self.lft = Term.Term(lexer, parser, parent)

            # The expression may end already (a single term is also an
            # expression).
            lexer.skip(['whitespace', 'newline'])
            if not lexer.current_is('arithmetic_operator') and \
               not lexer.current_is('logical_operator') and \
               not lexer.current_is('comparison') and \
               not lexer.current_is('regex_delimiter'):
                self.mark_end()
                return

        # Expect the operator.
        self.op_type, self.op = lexer.token()
        if not lexer.next_if('arithmetic_operator') and \
           not lexer.next_if('logical_operator') and \
           not lexer.next_if('comparison') and \
           not lexer.next_if('regex_delimiter'):
            self.mark_end()
            msg = 'Expected operator but got %s' % self.op_type
            lexer.syntax_error(msg, self)

        # Expect the second term.
        self.rgt = ExpressionNode(lexer, parser, parent, self)
        self.mark_end()


    def priority(self):
        if self.op is None:
            return 8
        elif self.op_type == 'arithmetic_operator' and self.op == '%':
            return 7
        elif self.op_type == 'arithmetic_operator' and self.op == '*':
            return 6
        elif self.op_type == 'regex_delimiter':
            return 6
        elif self.op_type == 'arithmetic_operator' and self.op != '.':
            return 5
        elif self.op == '.':
            return 4
        elif self.op_type == 'comparison':
            return 3
        elif self.op == 'not':
            return 2
        elif self.op_type == 'logical_operator':
            return 1
        else:
            raise Exception('Invalid operator.')


    def value(self, context):
        # Special behavior where we only have one term.
        if self.op is None:
            return self.lft.value(context)
        elif self.op == 'not':
            return [not self.rgt.value(context)[0]]

        # There are only two types of values: Regular expressions and lists.
        # We also have to make sure that empty lists do not cause an error.
        lft_lst = self.lft.value(context)
        if type(lft_lst) == type([]):
            if len(lft_lst) > 0:
                lft = lft_lst[0]
            else:
                lft = ''
        rgt_lst = self.rgt.value(context)
        if type(rgt_lst) == type([]):
            if len(rgt_lst) > 0:
                rgt = rgt_lst[0]
            else:
                rgt = ''

        if self.op_type == 'arithmetic_operator' and self.op != '.':
            error = 'Operand for %s is not a number' % (self.op)
            try:
                lft = int(lft)
            except ValueError:
                self.lexer.runtime_error(error, self.lft)
            try:
                rgt = int(rgt)
            except ValueError:
                self.lexer.runtime_error(error, self.rgt)

        # Two-term expressions.
        if self.op == 'is':
            return [lft == rgt]
        elif self.op == 'matches':
            regex = rgt_lst
            # The "matches" keyword requires a regular expression as the right hand
            # operand. The exception throws if "regex" does not have a match() method.
            try:
                regex.match(str(lft))
            except AttributeError:
                error = 'Right hand operator is not a regular expression'
                self.lexer.runtime_error(error, self.rgt)
            for line in lft_lst:
                if regex.search(str(line)):
                    return [1]
            return [0]
        elif self.op == 'is not':
            #print "LFT: '%s', RGT: '%s', RES: %s" % (lft, rgt, [lft != rgt])
            return [lft != rgt]
        elif self.op == 'in':
            return [lft in rgt_lst]
        elif self.op == 'not in':
            return [lft not in rgt_lst]
        elif self.op == 'ge':
            return [int(lft) >= int(rgt)]
        elif self.op == 'gt':
            return [int(lft) > int(rgt)]
        elif self.op == 'le':
            return [int(lft) <= int(rgt)]
        elif self.op == 'lt':
            return [int(lft) < int(rgt)]
        elif self.op == 'and':
            return [lft and rgt]
        elif self.op == 'or':
            return [lft or rgt]
        elif self.op == '*':
            return [int(lft) * int(rgt)]
        elif self.op == '/':
            return [int(lft) / int(rgt)]
        elif self.op == '%':
            return [int(lft) % int(rgt)]
        elif self.op == '.':
            return [str(lft) + str(rgt)]
        elif self.op == '+':
            return [int(lft) + int(rgt)]
        elif self.op == '-':
            return [int(lft) - int(rgt)]


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.op, 'start'
        if self.lft is not None:
            self.lft.dump(indent + 1)
        print (' ' * (indent + 1)) + 'Operator', self.op
        if self.rgt is not None:
            self.rgt.dump(indent + 1)
        print (' ' * indent) + self.name, self.op, 'end.'

########NEW FILE########
__FILENAME__ = Extract
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib          import Token
from Exscript.interpreter.Regex import Regex
from Exscript.interpreter.Term  import Term

class Extract(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Extract', lexer, parser, parent)
        self.varnames  = []
        self.variables = {}
        self.append    = False
        self.source    = None

        if parser.no_prompt: 
            msg = "'extract' keyword does not work with --no-prompt"
            lexer.syntax_error(msg, self)

        # First expect a regular expression.
        lexer.expect(self, 'keyword', 'extract')
        lexer.expect(self, 'whitespace')
        self.regex = Regex(lexer, parser, parent)

        # Expect "as" keyword.
        lexer.expect(self, 'whitespace')
        if lexer.next_if('keyword', 'as'):
            self.append = False
        elif lexer.next_if('keyword', 'into'):
            self.append = True
        else:
            _, token = lexer.token()
            msg      = 'Expected "as" or "into" but got %s' % token
            lexer.syntax_error(msg, self)

        # Expect a list of variable names.
        while 1:
            # Variable name.
            lexer.expect(self, 'whitespace')
            _, token = lexer.token()
            lexer.expect(self, 'varname')
            if token in self.variables:
                lexer.syntax_error('Duplicate variable name %s', self)
            self.varnames.append(token)
            self.variables[token] = []

            # Comma.
            if lexer.next_if('comma'):
                continue
            break
        self.parent.define(**self.variables)

        if len(self.varnames) != self.regex.n_groups:
            count = (len(self.varnames), self.regex.n_groups)
            error = '%s variables, but regex has %s groups' % count
            lexer.syntax_error(error, self)

        # Handle the "from" keyword.
        lexer.skip('whitespace')
        if lexer.next_if('keyword', 'from'):
            lexer.expect(self, 'whitespace')
            self.source = Term(lexer, parser, parent)
        self.mark_end()

    def extract(self, context):
        # Re-initialize the variable content, because this method
        # might be called multiple times.
        for varname in self.varnames:
            self.variables[varname] = []

        if self.source is None:
            buffer = self.parent.get('__response__')
        else:
            buffer = self.source.value(context)
        #print "Buffer contains", buffer

        # Walk through all lines, matching each one against the regular
        # expression.
        for line in buffer:
            match = self.regex.value(context).search(line)
            if match is None:
                continue

            # If there was a match, store the extracted substrings in our
            # list variables.
            i = 0
            for varname in self.varnames:
                i += 1
                try:
                    value = match.group(i)
                except IndexError:
                    # This happens if the user provided a regex with less 
                    # groups in it than the number of variables.
                    msg  = 'Extract: %s variables, but regular expression' % i
                    msg += '\ncontains only %s groups.' % (i - 1)
                    self.lexer.runtime_error(msg, self)
                self.variables[varname].append(value)

    def value(self, context):
        self.extract(context)
        if not self.append:
            self.parent.define(**self.variables)
        else:
            for key in self.variables:
                existing = self.parent.get(key)
                self.parent.define(**{key: existing + self.variables[key]})
        return 1


    def dump(self, indent = 0):
        mode = self.append and 'into' or 'as'
        source = self.source is not None and self.source or 'buffer'
        print (' ' * indent) + self.name, self.regex.string,
        print mode, self.varnames, "from", source

########NEW FILE########
__FILENAME__ = Fail
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib               import Token
from Exscript.interpreter.Expression import Expression
from Exscript.interpreter.Exception  import FailException

class Fail(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Fail', lexer, parser, parent)
        self.expression = None

        # "fail" keyword.
        lexer.expect(self, 'keyword', 'fail')
        lexer.expect(self, 'whitespace')
        self.msg = Expression(lexer, parser, parent)

        # 'If' keyword with an expression.
        #token = lexer.token()
        if lexer.next_if('keyword', 'if'):
            lexer.expect(self, 'whitespace')
            self.expression = Expression(lexer, parser, parent)

        # End of expression.
        self.mark_end()
        lexer.skip(['whitespace', 'newline'])

    def value(self, context):
        if self.expression is None or self.expression.value(context)[0]:
            raise FailException(self.msg.value(context)[0])
        return 1

    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.msg.dump(indent + 1)
        self.expression.dump(indent + 1)
        print (' ' * indent) + self.name, 'end.'

########NEW FILE########
__FILENAME__ = FunctionCall
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Expression
from Exscript.parselib              import Token
from Exscript.interpreter.Exception import PermissionError

class FunctionCall(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'FunctionCall', lexer, parser, parent)
        self.funcname  = None
        self.arguments = []

        # Extract the function name.
        _, token = lexer.token()
        lexer.expect(self, 'open_function_call')
        self.funcname = token[:-1]
        function      = self.parent.get(self.funcname)
        if function is None:
            lexer.syntax_error('Undefined function %s' % self.funcname, self)

        # Parse the argument list.
        _, token = lexer.token()
        while 1:
            if lexer.next_if('close_bracket'):
                break
            self.arguments.append(Expression.Expression(lexer, parser, parent))
            ttype, token = lexer.token()
            if not lexer.next_if('comma') and not lexer.current_is('close_bracket'):
                error = 'Expected separator or argument list end but got %s'
                lexer.syntax_error(error % ttype, self)

        if parser.secure_only and not hasattr(function, '_is_secure'):
            msg = 'Use of insecure function %s is not permitted' % self.funcname
            lexer.error(msg, self, PermissionError)

        self.mark_end()

    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.funcname, 'start'
        for argument in self.arguments:
            argument.dump(indent + 1)
        print (' ' * indent) + self.name, self.funcname, 'end.'

    def value(self, context):
        argument_values = [arg.value(context) for arg in self.arguments]
        function        = self.parent.get(self.funcname)
        if function is None:
            self.lexer.runtime_error('Undefined function %s' % self.funcname, self)
        return function(self.parent, *argument_values)

########NEW FILE########
__FILENAME__ = IfCondition
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Code
from Exscript.parselib               import Token
from Exscript.interpreter.Expression import Expression

class IfCondition(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'If-condition', lexer, parser, parent)

        # Expect an expression.
        lexer.expect(self, 'keyword', 'if')
        lexer.expect(self, 'whitespace')
        self.expression = Expression(lexer, parser, parent)
        self.mark_end()

        # Body of the if block.
        self.if_block    = Code.Code(lexer, parser, parent)
        self.elif_blocks = []
        self.else_block  = None

        # If there is no "else" statement, just return.
        lexer.skip(['whitespace', 'newline'])
        if not lexer.next_if('keyword', 'else'):
            return

        # If the "else" statement is followed by an "if" (=elif),
        # read the next if condition recursively and return.
        lexer.skip(['whitespace', 'newline'])
        if lexer.current_is('keyword', 'if'):
            self.else_block = IfCondition(lexer, parser, parent)
            return

        # There was no "elif", so we handle a normal "else" condition here.
        self.else_block = Code.Code(lexer, parser, parent)

    def value(self, context):
        if self.expression.value(context)[0]:
            self.if_block.value(context)
        elif self.else_block is not None:
            self.else_block.value(context)
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.expression.dump(indent + 1)
        self.if_block.dump(indent + 1)
        if self.else_block is not None:
            self.else_block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end.'

########NEW FILE########
__FILENAME__ = Loop
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Code
from Exscript.parselib               import Token
from Exscript.interpreter.Term       import Term
from Exscript.interpreter.Expression import Expression

class Loop(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Loop', lexer, parser, parent)
        self.during         = None
        self.until          = None
        self.thefrom        = None
        self.theto          = None
        self.list_variables = []
        self.iter_varnames  = []

        # Expect one ore more lists.
        lexer.expect(self, 'keyword', 'loop')
        lexer.expect(self, 'whitespace')
        if not lexer.current_is('keyword', 'while') and \
           not lexer.current_is('keyword', 'until') and \
           not lexer.current_is('keyword', 'from'):
            self.list_variables = [Term(lexer, parser, parent)]
            lexer.next_if('whitespace')
            while lexer.next_if('comma'):
                lexer.skip(['whitespace', 'newline'])
                self.list_variables.append(Term(lexer, parser, parent))
                lexer.skip(['whitespace', 'newline'])

            # Expect the "as" keyword.
            lexer.expect(self, 'keyword', 'as')

            # The iterator variable.
            lexer.next_if('whitespace')
            _, iter_varname = lexer.token()
            lexer.expect(self, 'varname')
            parent.define(**{iter_varname: []})
            self.iter_varnames = [iter_varname]
            lexer.next_if('whitespace')
            while lexer.next_if('comma'):
                lexer.skip(['whitespace', 'newline'])
                _, iter_varname = lexer.token()
                lexer.expect(self, 'varname')
                parent.define(**{iter_varname: []})
                self.iter_varnames.append(iter_varname)
                lexer.skip(['whitespace', 'newline'])

            if len(self.iter_varnames) != len(self.list_variables):
                error = '%s lists, but only %s iterators in loop' % (len(self.iter_varnames),
                                                                     len(self.list_variables))
                lexer.syntax_error(error, self)

        # Check if this is a "from ... to ..." loop.
        if lexer.next_if('keyword', 'from'):
            lexer.expect(self, 'whitespace')
            self.thefrom = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')
            lexer.expect(self, 'keyword', 'to')
            self.theto = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')

            if lexer.next_if('keyword', 'as'):
                lexer.next_if('whitespace')
                _, iter_varname = lexer.token()
                lexer.expect(self, 'varname')
                lexer.next_if('whitespace')
            else:
                iter_varname = 'counter'
            parent.define(**{iter_varname: []})
            self.iter_varnames = [iter_varname]
        
        # Check if this is a "while" loop.
        if lexer.next_if('keyword', 'while'):
            lexer.expect(self, 'whitespace')
            self.during = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')
        
        # Check if this is an "until" loop.
        if lexer.next_if('keyword', 'until'):
            lexer.expect(self, 'whitespace')
            self.until = Expression(lexer, parser, parent)
            lexer.next_if('whitespace')
        
        # End of statement.
        self.mark_end()

        # Body of the loop block.
        lexer.skip(['whitespace', 'newline'])
        self.block = Code.Code(lexer, parser, parent)


    def value(self, context):
        if len(self.list_variables) == 0 and not self.thefrom:
            # If this is a "while" loop, iterate as long as the condition is True.
            if self.during is not None:
                while self.during.value(context)[0]:
                    self.block.value(context)
                return 1

            # If this is an "until" loop, iterate until the condition is True.
            if self.until is not None:
                while not self.until.value(context)[0]:
                    self.block.value(context)
                return 1

        # Retrieve the lists from the list terms.
        if self.thefrom:
            start = self.thefrom.value(context)[0]
            stop  = self.theto.value(context)[0]
            lists = [range(start, stop)]
        else:
            lists = [var.value(context) for var in self.list_variables]
        vars  = self.iter_varnames
        
        # Make sure that all lists have the same length.
        for list in lists:
            if len(list) != len(lists[0]):
                msg = 'All list variables must have the same length'
                self.lexer.runtime_error(msg, self)

        # Iterate.
        for i in xrange(len(lists[0])):
            f = 0
            for list in lists:
                self.block.define(**{vars[f]: [list[i]]})
                f += 1
            if self.until is not None and self.until.value(context)[0]:
                break
            if self.during is not None and not self.during.value(context)[0]:
                break
            self.block.value(context)
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name,
        print self.list_variables, 'as', self.iter_varnames, 'start'
        if self.during is not None:
            self.during.dump(indent + 1)
        if self.until is not None:
            self.until.dump(indent + 1)
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end.'

########NEW FILE########
__FILENAME__ = Number
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
class Number(object):
    def __init__(self, number):
        self.number = int(number)

    def value(self, context):
        return [self.number]

    def dump(self, indent = 0):
        print (' ' * indent) + 'Number', self.number

########NEW FILE########
__FILENAME__ = Parser
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import copy
from Exscript.parselib            import Lexer
from Exscript.interpreter.Program import Program

class Parser(object):
    def __init__(self, **kwargs):
        self.no_prompt     = kwargs.get('no_prompt',     False)
        self.strip_command = kwargs.get('strip_command', True)
        self.secure_only   = kwargs.get('secure',        False)
        self.debug         = kwargs.get('debug',         0)
        self.variables     = {}

    def define(self, **kwargs):
        for key, value in kwargs.iteritems():
            if hasattr(value, '__iter__') or hasattr(value, '__call__'):
                self.variables[key] = value
            else:
                self.variables[key] = [value]

    def define_object(self, **kwargs):
        self.variables.update(kwargs)

    def _create_lexer(self):
        variables = copy.deepcopy(self.variables)
        return Lexer(Program, self, variables, debug = self.debug)

    def parse(self, string, filename = None):
        lexer = self._create_lexer()
        return lexer.parse(string, filename)

    def parse_file(self, filename):
        lexer = self._create_lexer()
        return lexer.parse_file(filename)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        filename = 'test.exscript'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        sys.exit(1)
    parser   = Parser(debug = 5)
    compiled = parser.parse_file(filename)
    compiled.dump()

########NEW FILE########
__FILENAME__ = Program
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import copy
from Exscript.interpreter.Template import Template
from Exscript.interpreter.Scope    import Scope

class Program(Scope):
    def __init__(self, lexer, parser, variables, **kwargs):
        Scope.__init__(self, 'Program', lexer, parser, None, **kwargs)
        self.variables      = variables
        self.init_variables = variables
        self.add(Template(lexer, parser, self))

    def init(self, *args, **kwargs):
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_'):
                continue
            if type(kwargs[key]) == type([]):
                self.init_variables[key] = kwargs[key]
            else:
                self.init_variables[key] = [kwargs[key]]

    def execute(self, *args, **kwargs):
        self.variables = copy.copy(self.init_variables)
        if 'variables' in kwargs:
            self.variables.update(kwargs.get('variables'))
        self.value(self)
        return self.variables

########NEW FILE########
__FILENAME__ = Regex
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
from Exscript.interpreter.String import String

# Matches any opening parenthesis that is neither preceeded by a backslash
# nor has a "?:" or "?<" appended.
bracket_re = re.compile(r'(?<!\\)\((?!\?[:<])', re.I)

modifier_grammar = (
    ('modifier',     r'[i]'),
    ('invalid_char', r'.'),
)

modifier_grammar_c = []
for thetype, regex in modifier_grammar:
    modifier_grammar_c.append((thetype, re.compile(regex, re.M|re.S)))

class Regex(String):
    def __init__(self, lexer, parser, parent):
        self.delimiter = lexer.token()[1]
        # String parser collects the regex.
        String.__init__(self, lexer, parser, parent)
        self.n_groups = len(bracket_re.findall(self.string))
        self.flags    = 0

        # Collect modifiers.
        lexer.set_grammar(modifier_grammar_c)
        while lexer.current_is('modifier'):
            if lexer.next_if('modifier', 'i'):
                self.flags = self.flags | re.I
            else:
                modifier = lexer.token()[1]
                error    = 'Invalid regular expression modifier "%s"' % modifier
                lexer.syntax_error(error, self)
        lexer.restore_grammar()

        # Compile the regular expression.
        try:
            re.compile(self.string, self.flags)
        except Exception, e:
            error = 'Invalid regular expression %s: %s' % (repr(self.string), e)
            lexer.syntax_error(error, self)

    def _escape(self, token):
        char = token[1]
        if char == self.delimiter:
            return char
        return token

    def value(self, context):
        pattern = String.value(self, context)[0]
        return re.compile(pattern, self.flags)


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.string

########NEW FILE########
__FILENAME__ = Scope
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from copy              import deepcopy
from Exscript.parselib import Token

class Scope(Token):
    def __init__(self, name, lexer, parser, parent = None, *args, **kwargs):
        Token.__init__(self, name, lexer, parser, parent)
        self.variables      = kwargs.get('variables', {})
        self.children       = []
        self.exit_requested = 0
        for key in self.variables:
            if key.find('.') < 0 and not key.startswith('_'):
                assert type(self.variables[key]) == type([])

    def exit_request(self):
        self.exit_requested = 1

    def define(self, **kwargs):
        if self.parent is not None:
            return self.parent.define(**kwargs)
        for key in kwargs:
            if key.find('.') >= 0 or key.startswith('_') \
              or type(kwargs[key]) == type([]):
                self.variables[key] = kwargs[key]
            else:
                self.variables[key] = [kwargs[key]]

    def define_object(self, **kwargs):
        self.variables.update(kwargs)

    def is_defined(self, name):
        if name in self.variables:
            return 1
        if self.parent is not None:
            return self.parent.is_defined(name)
        return 0

    def get_vars(self):
        """
        Returns a complete dict of all variables that are defined in this 
        scope, including the variables of the parent.
        """
        if self.parent is None:
            vars = {}
            vars.update(self.variables)
            return vars
        vars = self.parent.get_vars()
        vars.update(self.variables)
        return vars

    def copy_public_vars(self):
        """
        Like get_vars(), but does not include any private variables and
        deep copies each variable.
        """
        vars = self.get_vars()
        vars = dict([k for k in vars.iteritems() if not k[0].startswith('_')])
        return deepcopy(vars)

    def get(self, name, default = None):
        if name in self.variables:
            return self.variables[name]
        if self.parent is None:
            return default
        return self.parent.get(name, default)

    def value(self, context):
        result = 1
        for child in self.children:
            result = child.value(context)
        return result

    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        for child in self.children:
            child.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'

    def dump1(self):
        if self.parent is not None:
            self.parent.dump1()
            return
        print "Scope:", self.variables

########NEW FILE########
__FILENAME__ = String
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
from Exscript.parselib import Token

varname_re = re.compile(r'((?:__)?[a-zA-Z][\w_]*(?:__)?)')
string_re  = re.compile(r'(\\?)\$([\w_]*)')

grammar = [
    ('escaped_data', r'\\.'),
]

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))

class String(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Create a grammar depending on the delimiting character.
        tok_type, delimiter = lexer.token()
        escaped_delimiter   = '\\' + delimiter
        data                = r'[^\r\n\\' + escaped_delimiter + ']+'
        delimiter_re        = re.compile(escaped_delimiter)
        data_re             = re.compile(data)
        grammar_with_delim  = grammar_c[:]
        grammar_with_delim.append(('string_data',      data_re))
        grammar_with_delim.append(('string_delimiter', delimiter_re))
        lexer.set_grammar(grammar_with_delim)

        # Begin parsing the string.
        lexer.expect(self, 'string_delimiter')
        self.string = ''
        while 1:
            if lexer.current_is('string_data'):
                self.string += lexer.token()[1]
                lexer.next()
            elif lexer.current_is('escaped_data'):
                self.string += self._escape(lexer.token()[1])
                lexer.next()
            elif lexer.next_if('string_delimiter'):
                break
            else:
                ttype = lexer.token()[0]
                lexer.syntax_error('Expected string but got %s' % ttype, self)

        # Make sure that any variables specified in the command are declared.
        string_re.sub(self.variable_test_cb, self.string)
        self.mark_end()
        lexer.restore_grammar()

    def _escape(self, token):
        char = token[1]
        if char == 'n':
            return '\n'
        elif char == 'r':
            return '\r'
        elif char == '$': # Escaping is done later, in variable_sub_cb.
            return token
        return char

    def _variable_error(self, field, msg):
        self.start += self.string.find(field)
        self.end    = self.start + len(field)
        self.lexer.runtime_error(msg, self)

    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def variable_sub_cb(self, match):
        field   = match.group(0)
        escape  = match.group(1)
        varname = match.group(2)
        value   = self.parent.get(varname)

        # Check the variable name syntax.
        if escape:
            return '$' + varname
        elif varname == '':
            return '$'
        if not varname_re.match(varname):
            msg = '%s is not a variable name' % repr(varname)
            self._variable_error(field, msg)

        # Check the variable value.
        if value is None:
            msg = 'Undefined variable %s' % repr(varname)
            self._variable_error(field, msg)
        elif hasattr(value, 'func_name'):
            msg = '%s is a function, not a variable name' % repr(varname)
            self._variable_error(field, msg)
        elif isinstance(value, list):
            if len(value) > 0:
                value = '\n'.join([str(v) for v in value])
            else:
                value = ''
        return str(value)

    # Tokens that include variables in a string may use this callback to
    # make sure that the variable is already declared.
    def variable_test_cb(self, match):
        self.variable_sub_cb(match)
        return match.group(0)

    def value(self, context):
        return [string_re.sub(self.variable_sub_cb, self.string)]

    def dump(self, indent = 0):
        print (' ' * indent) + 'String "' + self.string + '"'

########NEW FILE########
__FILENAME__ = Template
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
from Exscript.interpreter.Scope   import Scope
from Exscript.interpreter.Code    import Code
from Exscript.interpreter.Execute import Execute

grammar = (
    ('escaped_data',        r'\\.'),
    ('open_curly_bracket',  '{'),
    ('close_curly_bracket', '}'),
    ('newline',             r'[\r\n]'),
    ('raw_data',            r'[^\r\n{}\\]+')
)

grammar_c = []
for thetype, regex in grammar:
    grammar_c.append((thetype, re.compile(regex)))

class Template(Scope):
    def __init__(self, lexer, parser, parent, *args, **kwargs):
        Scope.__init__(self, 'Template', lexer, parser, parent, **kwargs)
        lexer.set_grammar(grammar_c)
        #print "Opening Scope:", lexer.token()
        buffer = ''
        while 1:
            if self.exit_requested or lexer.current_is('EOF'):
                break
            elif lexer.next_if('open_curly_bracket'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer))
                    buffer = ''
                if isinstance(parent, Code):
                    break
                self.add(Code(lexer, parser, self))
            elif lexer.current_is('raw_data'):
                if lexer.token()[1].lstrip().startswith('#'):
                    while not lexer.current_is('newline'):
                        lexer.next()
                    continue
                buffer += lexer.token()[1]
                lexer.next()
            elif lexer.current_is('escaped_data'):
                token = lexer.token()[1]
                if token[1] == '$':
                    # An escaped $ is handeled by the Execute() token, so
                    # we do not strip the \ here.
                    buffer += token
                else:
                    buffer += token[1]
                lexer.next()
            elif lexer.next_if('newline'):
                if buffer.strip() != '':
                    self.add(Execute(lexer, parser, self, buffer))
                    buffer = ''
            else:
                ttype = lexer.token()[0]
                lexer.syntax_error('Unexpected %s' % ttype, self)
        lexer.restore_grammar()

    def execute(self):
        return self.value(self)

########NEW FILE########
__FILENAME__ = Term
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib                 import Token
from Exscript.interpreter.Variable     import Variable
from Exscript.interpreter.Number       import Number
from Exscript.interpreter.FunctionCall import FunctionCall
from Exscript.interpreter.String       import String
from Exscript.interpreter.Regex        import Regex

class Term(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Term', lexer, parser, parent)
        self.term = None
        self.lft  = None
        self.rgt  = None
        self.op   = None

        # Expect a term.
        ttype, token = lexer.token()
        if lexer.current_is('varname'):
            if not parent.is_defined(token):
                lexer.error('Undeclared variable %s' % token, self, ValueError)
            self.term = Variable(lexer, parser, parent)
        elif lexer.current_is('open_function_call'):
            self.term = FunctionCall(lexer, parser, parent)
        elif lexer.current_is('string_delimiter'):
            self.term = String(lexer, parser, parent)
        elif lexer.next_if('number'):
            self.term = Number(token)
        elif lexer.next_if('keyword', 'false'):
            self.term = Number(0)
        elif lexer.next_if('keyword', 'true'):
            self.term = Number(1)
        elif lexer.next_if('octal_number'):
            self.term = Number(int(token[1:], 8))
        elif lexer.next_if('hex_number'):
            self.term = Number(int(token[2:], 16))
        elif lexer.current_is('regex_delimiter'):
            self.term = Regex(lexer, parser, parent)
        else:
            lexer.syntax_error('Expected term but got %s' % ttype, self)
        self.mark_end()

    def priority(self):
        return 6

    def value(self, context):
        return self.term.value(context)

    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.term.dump(indent + 1)

########NEW FILE########
__FILENAME__ = Try
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import Code
from Exscript.protocols.Exception import ProtocolException
from Exscript.interpreter.Scope   import Scope

class Try(Scope):
    def __init__(self, lexer, parser, parent):
        Scope.__init__(self, 'Try', lexer, parser, parent)

        lexer.next_if('whitespace')
        lexer.expect(self, 'keyword', 'try')
        lexer.skip(['whitespace', 'newline'])
        self.block = Code.Code(lexer, parser, parent)

    def value(self, context):
        try:
            self.block.value(context)
        except ProtocolException, e:
            return 1
        return 1

    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'

########NEW FILE########
__FILENAME__ = Variable
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib import Token

class Variable(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Variable', lexer, parser, parent)
        self.varname = lexer.token()[1]
        lexer.expect(self, 'varname')
        self.mark_end()

    def value(self, context):
        val = self.parent.get(self.varname)
        if val is None:
            msg = 'Undefined variable %s' % self.varname
            self.lexer.runtime_error(msg, self)
        return val

    def dump(self, indent = 0):
        print (' ' * indent) + 'Variable', self.varname, '.'

########NEW FILE########
__FILENAME__ = Log
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from StringIO import StringIO
from Exscript.util.impl import format_exception

class Log(object):
    def __init__(self, name):
        self.name     = name
        self.data     = StringIO('')
        self.exc_info = None
        self.did_end  = False

    def __str__(self):
        return self.data.getvalue()

    def __len__(self):
        return len(str(self))

    def get_name(self):
        return self.name

    def write(self, *data):
        self.data.write(' '.join(data))

    def get_error(self, include_tb = True):
        if self.exc_info is None:
            return None
        if include_tb:
            return format_exception(*self.exc_info)
        if str(self.exc_info[1]):
            return str(self.exc_info[1])
        return self.exc_info[0].__name__

    def started(self):
        """
        Called by a logger to inform us that logging may now begin.
        """
        self.did_end = False

    def aborted(self, exc_info):
        """
        Called by a logger to log an exception.
        """
        self.exc_info = exc_info
        self.did_end = True
        self.write(format_exception(*self.exc_info))

    def succeeded(self):
        """
        Called by a logger to inform us that logging is complete.
        """
        self.did_end = True

    def has_error(self):
        return self.exc_info is not None

    def has_ended(self):
        return self.did_end

########NEW FILE########
__FILENAME__ = Logfile
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Represents the logfiles for one specific action.
"""
import os
import errno
from Exscript.Log import Log
from Exscript.util.impl import format_exception

class Logfile(Log):
    """
    This class logs to two files: The raw log, and sometimes a separate
    log containing the error message with a traceback.
    """

    def __init__(self, name, filename, mode = 'a', delete = False):
        Log.__init__(self, name)
        self.filename  = filename
        self.errorname = filename + '.error'
        self.mode      = mode
        self.delete    = delete
        self.do_log    = True
        dirname        = os.path.dirname(filename)
        if dirname:
            try:
                os.mkdir(dirname)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise

    def __str__(self):
        data = ''
        if os.path.isfile(self.filename):
            with open(self.filename, 'r') as thefile:
                data += thefile.read()
        if os.path.isfile(self.errorname):
            with open(self.errorname, 'r') as thefile:
                data += thefile.read()
        return data

    def _write_file(self, filename, *data):
        if not self.do_log:
            return
        try:
            with open(filename, self.mode) as thefile:
                thefile.write(' '.join(data))
        except Exception, e:
            print 'Error writing to %s: %s' % (filename, e)
            self.do_log = False
            raise

    def write(self, *data):
        return self._write_file(self.filename, *data)

    def _write_error(self, *data):
        return self._write_file(self.errorname, *data)

    def started(self):
        self.write('')  # Creates the file.

    def aborted(self, exc_info):
        self.exc_info = exc_info
        self.did_end = True
        self.write('ERROR:', str(exc_info[1]), '\n')
        self._write_error(format_exception(*self.exc_info))

    def succeeded(self):
        if self.delete and not self.has_error():
            os.remove(self.filename)
            return
        Log.succeeded(self)

########NEW FILE########
__FILENAME__ = Logger
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Logging to memory.
"""
import weakref
from itertools import chain, ifilter
from collections import defaultdict
from Exscript.Log import Log

logger_registry = weakref.WeakValueDictionary() # Map id(logger) to Logger.

class Logger(object):
    """
    A QueueListener that implements logging for the queue.
    Logs are kept in memory, and not written to the disk.
    """

    def __init__(self):
        """
        Creates a new logger instance. Use the L{Exscript.util.log.log_to}
        decorator to send messages to the logger.
        """
        logger_registry[id(self)] = self
        self.logs    = defaultdict(list)
        self.started = 0
        self.success = 0
        self.failed  = 0

    def _reset(self):
        self.logs = defaultdict(list)

    def get_succeeded_actions(self):
        """
        Returns the number of jobs that were completed successfully.
        """
        return self.success

    def get_aborted_actions(self):
        """
        Returns the number of jobs that were aborted.
        """
        return self.failed

    def get_logs(self):
        return list(chain.from_iterable(self.logs.itervalues()))

    def get_succeeded_logs(self):
        func = lambda x: x.has_ended() and not x.has_error()
        return list(ifilter(func, self.get_logs()))

    def get_aborted_logs(self):
        func = lambda x: x.has_ended() and x.has_error()
        return list(ifilter(func, self.get_logs()))

    def _get_log(self, job_id):
        return self.logs[job_id][-1]

    def add_log(self, job_id, name, attempt):
        log = Log(name)
        log.started()
        self.logs[job_id].append(log)
        self.started += 1
        return log

    def log(self, job_id, message):
        # This method is called whenever a sub thread sends a log message
        # via a pipe. (See LoggerProxy and Queue.PipeHandler)
        log = self._get_log(job_id)
        log.write(message)

    def log_aborted(self, job_id, exc_info):
        log = self._get_log(job_id)
        log.aborted(exc_info)
        self.failed += 1

    def log_succeeded(self, job_id):
        log = self._get_log(job_id)
        log.succeeded()
        self.success += 1

########NEW FILE########
__FILENAME__ = LoggerProxy
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

class LoggerProxy(object):
    """
    An object that has a 1:1 relation to a Logger object in another
    process.
    """
    def __init__(self, parent, logger_id):
        """
        Constructor.

        @type  parent: multiprocessing.Connection
        @param parent: A pipe to the associated pipe handler.
        """
        self.parent    = parent
        self.logger_id = logger_id

    def add_log(self, job_id, name, attempt):
        self.parent.send(('log-add', (self.logger_id, job_id, name, attempt)))
        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        return response

    def log(self, job_id, message):
        self.parent.send(('log-message', (self.logger_id, job_id, message)))

    def log_aborted(self, job_id, exc_info):
        self.parent.send(('log-aborted', (self.logger_id, job_id, exc_info)))

    def log_succeeded(self, job_id):
        self.parent.send(('log-succeeded', (self.logger_id, job_id)))

########NEW FILE########
__FILENAME__ = Exception
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
class LexerException(Exception):
    """
    Fallback exception that is called when the error type is not known.
    """
    pass

class CompileError(LexerException):
    """
    Raised during the compilation procedure if the template contained
    a syntax error.
    """
    pass

class ExecuteError(LexerException):
    """
    Raised during the execution of the compiled template whenever any
    error occurs.
    """
    pass

########NEW FILE########
__FILENAME__ = Lexer
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.parselib.Exception import LexerException, \
                                        CompileError, \
                                        ExecuteError

class Lexer(object):
    def __init__(self, parser_cls, *args, **kwargs):
        """
        The given args are passed to the parser_cls constructor.
        """
        self.parser_cls      = parser_cls
        self.parser_cls_args = args
        self.filename        = None
        self.input           = ''
        self.input_length    = 0
        self.current_char    = 0
        self.last_char       = 0
        self.token_buffer    = None
        self.grammar         = []
        self.debug           = kwargs.get('debug', False)

    def set_grammar(self, grammar):
        self.grammar.append(grammar)
        self.token_buffer = None

    def restore_grammar(self):
        self.grammar.pop()
        self.token_buffer = None

    def match(self):
        if self.current_char >= self.input_length:
            self.token_buffer = ('EOF', '')
            return
        for token_type, token_regex in self.grammar[-1]:
            match = token_regex.match(self.input, self.current_char)
            if match is not None:
                self.token_buffer = (token_type, match.group(0))
                #print "Match:", self.token_buffer
                return
        end   = self.input.find('\n', self.current_char + 2)
        error = 'Invalid syntax: %s' % repr(self.input[self.current_char:end])
        self.syntax_error(error)

    def _get_line_number_from_char(self, char):
        return self.input[:char].count('\n') + 1

    def _get_current_line_number(self):
        return self._get_line_number_from_char(self.current_char)

    def _get_line(self, number):
        return self.input.split('\n')[number - 1]

    def get_current_line(self):
        line = self._get_current_line_number()
        return self._get_line(line)

    def _get_line_from_char(self, char):
        line = self._get_line_number_from_char(char)
        return self._get_line(line)

    def _get_line_position_from_char(self, char):
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        return line_start, line_end

    def _error(self, exc_cls, error, sender = None):
        if not sender:
            raise exc_cls('\n' + error)
        start, end  = self._get_line_position_from_char(sender.end)
        line_number = self._get_line_number_from_char(sender.end)
        line        = self._get_line(line_number)
        offset      = sender.start - start
        token_len   = sender.end   - sender.start
        output      = line + '\n'
        if token_len <= 1:
            output += (' ' * offset) + '^\n'
        else:
            output += (' ' * offset) + "'" + ('-' * (token_len - 2)) + "'\n"
        output += '%s in %s:%s' % (error, self.filename, line_number)
        raise exc_cls('\n' + output)

    def error(self, error, sender = None, exc_cls = LexerException):
        self._error(exc_cls, error, sender)

    def syntax_error(self, error, sender = None):
        self._error(CompileError, error, sender)

    def runtime_error(self, error, sender = None):
        self._error(ExecuteError, error, sender)

    def forward(self, chars = 1):
        self.last_char     = self.current_char
        self.current_char += chars
        self.token_buffer  = None

    def next(self):
        if self.token_buffer:
            self.forward(len(self.token_buffer[1]))

    def next_if(self, types, token = None):
        if token is not None:
            if self.current_is(types, token):
                self.next()
                return 1
            return 0

        if type(types) != type([]):
            types = [types]
        for t in types:
            if self.current_is(t, token):
                self.next()
                return 1
        return 0

    def skip(self, types, token = None):
        while self.next_if(types, token):
            pass

    def expect(self, sender, type, token = None):
        cur_type, cur_token = self.token()
        if self.next_if(type, token):
            return
        if token:
            error = 'Expected "%s" but got %s %s'
            error = error % (token, cur_type, repr(cur_token))
        else:
            error = 'Expected %s but got %s (%s)'
            error = error % (type, cur_type, repr(cur_token))
        # In this case we do not point to the token that raised the error,
        # but to the actual position of the lexer.
        sender.start = self.current_char
        sender.end   = self.current_char + 1
        self.syntax_error(error, sender)

    def current_is(self, type, token = None):
        if self.token_buffer is None:
            self.match()
        if self.token_buffer[0] != type:
            return 0
        if token is None:
            return 1
        if self.token_buffer[1] == token:
            return 1
        return 0

    def token(self):
        if self.token_buffer is None:
            self.match()
        return self.token_buffer

    def parse(self, string, filename = None):
        # Re-initialize, so that the same lexer instance may be used multiple
        # times.
        self.filename     = filename
        self.input        = string
        self.input_length = len(string)
        self.current_char = 0
        self.last_char    = 0
        self.token_buffer = None
        self.grammar      = []
        compiled          = self.parser_cls(self, *self.parser_cls_args)
        if self.debug > 3:
            compiled.dump()
        return compiled

    def parse_file(self, filename):
        with open(filename) as fp:
            return self.parse(fp.read(), filename)

########NEW FILE########
__FILENAME__ = Token
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

class Token(object):
    """
    Abstract base class for all tokens.
    """

    class Iterator(object):
        """
        A tree iterator that walks through all tokens.
        """
        def __init__(self, current):
            """
            Constructor.
            """
            self.path = [current]

        def __iter__(self):
            return self

        def _next(self):
            # Make sure that the end is not yet reached.
            if len(self.path) == 0:
                raise StopIteration()

            # If the current token has children, the first child is the next item.
            current  = self.path[-1]
            children = current.get_children()
            if len(children) > 0:
                self.path.append(children[0])
                return current

            # Ending up here, this task has no children. Crop the path until we
            # reach a task that has unvisited children, or until we hit the end.
            while True:
                old_child = self.path.pop(-1)
                if len(self.path) == 0:
                    break

                # If this task has a sibling, choose it.
                parent   = self.path[-1]
                children = parent.get_children()
                pos      = children.index(old_child)
                if len(children) > pos + 1:
                    self.path.append(children[pos + 1])
                    break
            return current

        def next(self):
            # By using this loop we avoid an (expensive) recursive call.
            while True:
                next = self._next()
                if next is not None:
                    return next

    def __init__(self, name, lexer, parser, parent = None):
        self.lexer    = lexer
        self.parser   = parser
        self.parent   = parent
        self.name     = name
        self.children = []
        self.start    = lexer.current_char
        self.end      = lexer.current_char + 1

    def value(self, context):
        for child in self.get_children():
            child.value(context)

    def mark_start(self):
        self.start = self.lexer.current_char
        if self.start >= self.end:
            self.end = self.start + 1

    def mark_end(self, char = None):
        self.end = char and char or self.lexer.current_char

    def __iter__(self):
        """
        Returns an iterator that points to the first token.
        """
        return Token.Iterator(self)

    def add(self, child):
        self.children.append(child)

    def get_children(self):
        return self.children

    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        for child in self.get_children():
            child.dump(indent + 1)

########NEW FILE########
__FILENAME__ = PrivateKey
# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Represents a private key.
"""
from paramiko import RSAKey, DSSKey
from paramiko.ssh_exception import SSHException

class PrivateKey(object):
    """
    Represents a cryptographic key, and may be used to authenticate
    useing L{Exscript.protocols}.
    """
    keytypes = set()

    def __init__(self, keytype = 'rsa'):
        """
        Constructor. Supported key types are provided by their respective
        protocol adapters and can be retrieved from the PrivateKey.keytypes
        class attribute.

        @type  keytype: string
        @param keytype: The key type.
        """
        if keytype not in self.keytypes:
            raise TypeError('unsupported key type: ' + repr(keytype))
        self.keytype  = keytype
        self.filename = None
        self.password = None

    @staticmethod
    def from_file(filename, password = '', keytype = None):
        """
        Returns a new PrivateKey instance with the given attributes.
        If keytype is None, we attempt to automatically detect the type.

        @type  filename: string
        @param filename: The key file name.
        @type  password: string
        @param password: The key password.
        @type  keytype: string
        @param keytype: The key type.
        @rtype:  PrivateKey
        @return: The new key.
        """
        if keytype is None:
            try:
                key = RSAKey.from_private_key_file(filename)
                keytype = 'rsa'
            except SSHException, e:
                try:
                    key = DSSKey.from_private_key_file(filename)
                    keytype = 'dss'
                except SSHException, e:
                    msg = 'not a recognized private key: ' + repr(filename)
                    raise ValueError(msg)
        key          = PrivateKey(keytype)
        key.filename = filename
        key.password = password
        return key

    def get_type(self):
        """
        Returns the type of the key, e.g. RSA or DSA.

        @rtype:  string
        @return: The key type
        """
        return self.keytype

    def set_filename(self, filename):
        """
        Sets the name of the key file to use.

        @type  filename: string
        @param filename: The key filename.
        """
        self.filename = filename

    def get_filename(self):
        """
        Returns the name of the key file.

        @rtype:  string
        @return: The key password.
        """
        return self.filename

    def set_password(self, password):
        """
        Defines the password used for decrypting the key.

        @type  password: string
        @param password: The key password.
        """
        self.password = password

    def get_password(self):
        """
        Returns the password for the key.

        @rtype:  string
        @return: The key password.
        """
        return self.password

########NEW FILE########
__FILENAME__ = aix
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for AIX.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'[\r\n]Authorized Login: $')]
_password_re = [re.compile(r'[\r\n]\w+\'s Password: $')]
_aix_re      = re.compile(r'\bAIX\b')

class AIXDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'aix')
        self.user_re     = _user_re
        self.password_re = _password_re

    def check_head_for_os(self, string):
        if _user_re[0].search(string):
            return 70
        if _aix_re.search(string):
            return 75
        return 0

########NEW FILE########
__FILENAME__ = arbor_peakflow
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Peakflow SP by Arbor Networks.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'(user|login): $', re.I)]
_password_re = [re.compile(r'Password: $')]
_prompt_re   = [re.compile(r'[\r\n][\-\w+\._]+@[\-\w+\._~]+:(?:/\w*)+[#%] $'),
                re.compile(r'Exit anyway\? \[.\] $')]
_os_re       = re.compile(r'\b(peakflow\b.*\barbor|arbos)\b', re.I | re.S)

class ArborPeakflowDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'arbor_peakflow')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _os_re.search(string):
            return 97
        return 0

########NEW FILE########
__FILENAME__ = aruba
"""
A driver for Aruba.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re = [re.compile(r'user ?name: ?$', re.I)]
_password_re = [re.compile(r'(?:[\r\n]Password: ?|last resort password:)$')]
_tacacs_re = re.compile(r'[\r\n]s\/key[\S ]+\r?%s' % _password_re[0].pattern)
_prompt_re = [re.compile(r'[\r\n]\(\w+\) [>#] ?$')]
_error_re = [re.compile(r'%Error'),
             re.compile(r'invalid input', re.I),
             re.compile(r'(?:incomplete|ambiguous) command', re.I),
             re.compile(r'connection timed out', re.I),
             re.compile(r'[^\r\n]+ not found', re.I)]


class ArubaDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'aruba')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string):
        return 88

    def init_terminal(self, conn):
        conn.execute('no paging')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = brocade
# Copyright (C) 2012 Job Snijders <job.snijders@atrato-ip.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Brocade XMR/MLX devices.
"""

import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'[\r\n](Please Enter Login Name: |User Name:)$')]
_password_re = [re.compile(r'[\r\n](Please Enter Password: |Password:)$')]
_warning     = r'(?:Warning: \d+ user\(s\) already in config mode\.)'
_prompt      = r'[\r\n]?(telnet|SSH)@[\-\w+\.:]+(?:\([\-\/\w]+\))?[>#]$'
_prompt_re   = [re.compile(_warning + r'?' + _prompt)]                                                                                                                         
_error_re    = [re.compile(r'%Error'),
                re.compile(r'Invalid input', re.I),
                re.compile(r'(?:incomplete|ambiguous) command', re.I),
                re.compile(r'connection timed out', re.I),
                re.compile(r'[^\r\n]+ not found', re.I)]

class BrocadeDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'brocade')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self.error_re    = _error_re

    def check_head_for_os(self, string):
        if 'User Access Verification\r\n\r\nPlease Enter Login Name' in string:
            return 95
        if _prompt_re[0].search(string):
            return 90
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal length 0')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = driver
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Base class for all drivers.
"""
import re, string

_flags          = re.I
_printable      = re.escape(string.printable)
_unprintable    = r'[^' + _printable + r']'
_unprintable_re = re.compile(_unprintable)
_ignore         = r'[\x1b\x07\x00]'
_nl             = r'[\r\n]'
_prompt_start   = _nl + r'(?:' + _unprintable + r'*|' + _ignore + '*)'
_prompt_chars   = r'[\-\w\(\)@:~]'
_filename       = r'(?:[\w\+\-\._]+)'
_path           = r'(?:(?:' + _filename + r')?(?:/' + _filename + r')*/?)'
_any_path       = r'(?:' + _path + r'|~' + _path + r'?)'
_host           = r'(?:[\w+\-\.]+)'
_user           = r'(?:[\w+\-]+)'
_user_host      = r'(?:(?:' + _user + r'\@)?' + _host + r')'
_prompt_re      = [re.compile(_prompt_start                 \
                            + r'[\[\<]?'                    \
                            + r'\w+'                        \
                            + _user_host + r'?'             \
                            + r':?'                         \
                            + _any_path + r'?'              \
                            + r'[: ]?'                      \
                            + _any_path + r'?'              \
                            + r'(?:\(' + _filename + '\))?' \
                            + r'[\]\-]?'                    \
                            + r'[#>%\$\]] ?'                \
                            + _unprintable + r'*'           \
                            + r'\Z', _flags)]

_user_re    = [re.compile(r'(user ?name|user|login): *$', _flags)]
_pass_re    = [re.compile(r'password:? *$',               _flags)]
_errors     = [r'error',
               r'invalid',
               r'incomplete',
               r'unrecognized',
               r'unknown command',
               r'connection timed out',
               r'[^\r\n]+ not found']
_error_re   = [re.compile(r'^%?\s*(?:' + '|'.join(_errors) + r')', _flags)]
_login_fail = [r'bad secrets',
               r'denied',
               r'invalid',
               r'too short',
               r'incorrect',
               r'connection timed out',
               r'failed']
_login_fail_re = [re.compile(_nl          \
                           + r'[^\r\n]*'  \
                           + r'(?:' + '|'.join(_login_fail) + r')', _flags)]

class Driver(object):
    def __init__(self, name):
        self.name           = name
        self.user_re        = _user_re
        self.password_re    = _pass_re
        self.prompt_re      = _prompt_re
        self.error_re       = _error_re
        self.login_error_re = _login_fail_re

    def check_head_for_os(self, string):
        return 0

    def _check_head(self, string):
        return self.name, self.check_head_for_os(string)

    def check_response_for_os(self, string):
        return 0

    def _check_response(self, string):
        return self.name, self.check_response_for_os(string)

    def clean_response_for_re_match(self, response):
        return response, ''

    def init_terminal(self, conn):
        pass

    def supports_auto_authorize(self):
        return self.__class__.auto_authorize != Driver.auto_authorize

    def auto_authorize(self, conn, account, flush, bailout):
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = enterasys
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Enterasys devices.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re      = [re.compile(r'[\r\n]Username: $')]
_password_re  = [re.compile(r'[\r\n]Password: $')]
_prompt_re    = [re.compile(r'[\r\n][\-\w+\.]+(?:\([^\)]+\))?-?[>#] ?$')]
_enterasys_re = re.compile(r'\benterasys\b', re.I)

class EnterasysDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'enterasys')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _enterasys_re.search(string):
            return 80
        return 0

########NEW FILE########
__FILENAME__ = generic
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
The default driver that is used when the OS is not recognized.
"""
from Exscript.protocols.drivers.driver import Driver

class GenericDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'generic')

########NEW FILE########
__FILENAME__ = hp_pro_curve
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for HP ProCurve switches.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re       = [re.compile(r'[\r\n]Username: ?$')]
_password_re   = [re.compile(r'[\r\n]Password: ?$')]
_prompt_re     = [re.compile(r'[\r\n][\-\w+\.:/]+[>#] ?$')]
_error_re      = [re.compile(r'(?:invalid|incomplete|ambiguous) input:', re.I)]
_login_fail_re = [re.compile(r'[\r\n]invalid password', re.I),
                  re.compile(r'unable to verify password', re.I),
                  re.compile(r'unable to login', re.I)]
_clean_res_re  = [(re.compile(r'\x1bE'), "\r\n"), (re.compile(r'(?:\x1b\[|\x9b)[\x30-\x3f]*[\x40-\x7e]'), "")]

class HPProCurveDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'hp_pro_curve')
        self.user_re        = _user_re
        self.password_re    = _password_re
        self.prompt_re      = _prompt_re
        self.error_re       = _error_re
        self.login_error_re = _login_fail_re
        self.clean_res_re   = _clean_res_re

    def check_head_for_os(self, string):
        if 'ProCurve' in string:
            return 95
        if 'Hewlett-Packard' in string:
            return 50
        return 0

    def clean_response_for_re_match(self, response):
        start = response[:10].find('\x1b')
        if start != -1:
            response = response[start:]
        for regexp, sub in self.clean_res_re:
            response = regexp.subn(sub, response)[0]
        i = response.find('\x1b')
        if i > -1:
            return response[:i], response[i:]
        return response, ''

    def init_terminal(self, conn):
        conn.execute('\r\n')

########NEW FILE########
__FILENAME__ = ios
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Cisco IOS (not IOS XR).
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'user ?name: ?$', re.I)]
_password_re = [re.compile(r'(?:[\r\n]Password: ?|last resort password:)$')]
_tacacs_re   = re.compile(r'[\r\n]s\/key[\S ]+\r?%s' % _password_re[0].pattern)
_prompt_re   = [re.compile(r'[\r\n][\-\w+\.:/]+(?:\([^\)]+\))?[>#] ?$')]
_error_re    = [re.compile(r'%Error'),
                re.compile(r'invalid input', re.I),
                re.compile(r'(?:incomplete|ambiguous) command', re.I),
                re.compile(r'connection timed out', re.I),
                re.compile(r'[^\r\n]+ not found', re.I)]

class IOSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'ios')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self.error_re    = _error_re

    def check_head_for_os(self, string):
        if 'User Access Verification' in string:
            return 60
        if _tacacs_re.search(string):
            return 50
        if _user_re[0].search(string):
            return 30
        return 0

    def init_terminal(self, conn):
        conn.execute('term len 0')
        conn.execute('term width 0')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = ios_xr
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Cisco IOS XR.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'[\r\n]Username: $')]
_password_re = [re.compile(r'[\r\n]Password: $')]
_prompt_re   = [re.compile(r'[\r\n]RP/\d+/(?:RS?P)?\d+\/CPU\d+:[^#]+(?:\([^\)]+\))?#$')]

class IOSXRDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'ios_xr')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_response_for_os(self, string):
        if _prompt_re[0].search(string):
            return 95
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal exec prompt no-timestamp')
        conn.execute('terminal len 0')
        conn.execute('terminal width 0')

########NEW FILE########
__FILENAME__ = junos
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for devices running JunOS (by Juniper).
"""
import re
from Exscript.protocols.drivers.driver import Driver

# JunOS prompt examples:
#   sab@DD-EA3>
#
#   [edit]
#   sab@DD-EA3>
#
#   {backup}
#   sab@DD-EA3>
#
#   {backup}[edit]
#   sab@DD-EA3>
#
#   {backup}[edit interfaces]
#   sab@DD-EA3>
#
#   {master:3}
#   pheller@sw3>
#
#   {primary:node0}
#   pheller@fw1>
#

_user_re     = [re.compile(r'[\r\n]login: $')]
_password_re = [re.compile(r'[\r\n](Local )?[Pp]assword: ?$')]
_mb          = r'(?:\{master(?::\d+)?\}|\{backup(?::\d+)?\})'
_ps          = r'(?:\{primary:node\d+\}|\{secondary:node\d+\})'
_re_re       = r'(?:'+ _mb + r'|' + _ps + r')'
_edit        = r'(?:\[edit[^\]\r\n]*\])'
_prefix      = r'(?:[\r\n]+' + _re_re + r'?' + _edit + r'?)'
_prompt      = r'[\r\n]+[\w\-]+@[\-\w+\.:]+[%>#] $'
_prompt_re   = [re.compile(_prefix + r'?' + _prompt)]
_error_re    = [re.compile('^(unknown|invalid|error)', re.I)]
_junos_re    = re.compile(r'\bjunos\b', re.I)

class JunOSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'junos')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re
        self.error_re    = _error_re

    def check_head_for_os(self, string):
        if _junos_re.search(string):
            return 80
        if _user_re[0].search(string):
            return 35
        return 0

    def init_terminal(self, conn):
        conn.execute('set cli screen-length 0')
        conn.execute('set cli screen-width 0')
        conn.execute('set cli terminal ansi')

########NEW FILE########
__FILENAME__ = junos_erx
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for devices running Juniper ERX OS.
"""
import re
from Exscript.protocols.drivers.driver import Driver
from Exscript.protocols.drivers.ios    import _prompt_re

_user_re     = [re.compile(r'[\r\n]User: $')]
_password_re = [re.compile(r'[\r\n](Telnet password:|Password:) $')]
_junos_re    = re.compile(r'\bJuniper Networks\b', re.I)

class JunOSERXDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'junos_erx')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _junos_re.search(string):
            return 75
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal length 60')
        conn.execute('terminal width 150')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable 15\r')
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = one_os
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for OneOS (OneAccess).
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re         = [re.compile(r'[\r\n]Username:$')]
_password_re     = [re.compile(r'[\r\n]Password:$')]
_first_prompt_re = re.compile(r'\r?\n\r?\n[\-\w+\.]+[>#]$')
_prompt_re       = [re.compile(r'[\r\n][\-\w+\.]+(?:\([^\)]+\))?[>#] ?$')]

class OneOSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'one_os')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _first_prompt_re.search(string):
            return 40
        return 0

    def init_terminal(self, conn):
        conn.execute('term len 0')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = shell
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A generic shell driver that handles unknown unix shells.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'(user|login): $', re.I)]
_password_re = [re.compile(r'Password: ?$')]
_linux_re    = re.compile(r'\blinux\b', re.I)

class ShellDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'shell')
        self.user_re     = _user_re
        self.password_re = _password_re

    def check_head_for_os(self, string):
        if _linux_re.search(string):
            return 70
        if _user_re[0].search(string):
            return 20
        return 0

########NEW FILE########
__FILENAME__ = smart_edge_os
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Redback Smart Edge OS.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'[\r\n]login: ')]
_password_re = [re.compile(r'[\r\n]Password: $')]
_prompt_re   = [re.compile(r'[\r\n]\[\w+\][\-\w+\.]+(?:\([^\)]+\))?[>#] ?$')]
_model_re    = re.compile(r'[\r\n][^\r\n]+-se800[\r\n]')

class SmartEdgeOSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'smart_edge_os')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _model_re.search(string):
            return 60
        if self.user_re[0].search(string):
            return 20
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal length 0')
        conn.execute('terminal width 65536')

    def auto_authorize(self, conn, account, flush, bailout):
        conn.send('enable\r')
        conn.app_authorize(account, flush, bailout)

########NEW FILE########
__FILENAME__ = sros
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for Alcatel SROS.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_prompt_re = [re.compile(r'[\r\n][*]?(?:A|B):[\-\w\.>]+[#\$] ?$')]

class SROSDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'sros')
        self.prompt_re = _prompt_re

    def check_head_for_os(self, string):
        if _prompt_re[0].search(string):
            return 95
        return 0

    def init_terminal(self, conn):
        conn.execute('environment no more')
        conn.execute('environment reduced-prompt 2')
        conn.execute('environment no saved-ind-prompt')

########NEW FILE########
__FILENAME__ = vrp
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A driver for devices running VRP (by Huawei).
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re     = [re.compile(r'user ?name: ', re.I)]
_password_re = [re.compile(r'[\r\n]Password: $')]
_prompt_re   = [re.compile(r'[\r\n][\-\w+\.]+(?:\([^\)]+\))?[>#] ?$')]
_huawei_re   = re.compile(r'\bhuawei\b', re.I)

class VRPDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'vrp')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _huawei_re.search(string):
            return 80
        return 0

########NEW FILE########
__FILENAME__ = Dummy
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A client that talks to a L{Exscript.emulators.VirtualDevice}.
"""
from Exscript.emulators           import VirtualDevice
from Exscript.protocols.Protocol  import Protocol
from Exscript.protocols.Exception import TimeoutException, \
                                         DriverReplacedException, \
                                         ExpectCancelledException

class Dummy(Protocol):
    """
    This protocol adapter does not open a network connection, but talks to
    a L{Exscript.emulators.VirtualDevice} internally.
    """

    def __init__(self, device = None, **kwargs):
        """
        @note: Also supports all keyword arguments that L{Protocol} supports.

        @keyword device: The L{Exscript.emulators.VirtualDevice} with
            which to communicate.
        """
        Protocol.__init__(self, **kwargs)
        self.device    = device
        self.init_done = False
        self.cancel    = False
        self.response  = None
        if not self.device:
            self.device = VirtualDevice('dummy', strict = False)

    def is_dummy(self):
        return True

    def _expect_any(self, prompt_list, flush = True):
        self._doinit()

        # Cancelled by a callback during self._say().
        if self.cancel:
            self.cancel = False
            return -2, None, self.response

        # Look for a match in the buffer.
        for i, prompt in enumerate(prompt_list):
            matches = prompt.search(str(self.buffer))
            if matches is not None:
                self.response = self.buffer.head(matches.start())
                if flush:
                    self.buffer.pop(matches.end())
                return i, matches, self.response

        # "Timeout".
        return -1, None, self.response

    def _say(self, string):
        self._receive_cb(string)
        self.buffer.append(string)

    def cancel_expect(self):
        self.cancel = True

    def _connect_hook(self, hostname, port):
        # To more correctly mimic the behavior of a network device, we
        # do not send the banner here, but in authenticate() instead.
        self.buffer.clear()
        return True

    def _doinit(self):
        if not self.init_done:
            self.init_done = True
            self._say(self.device.init())

    def _protocol_authenticate(self, user, password):
        self._doinit()

    def _protocol_authenticate_by_key(self, user, key):
        self._doinit()

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        self._say(self.device.do(data))

    def _domatch(self, prompt, flush):
        # Wait for a prompt.
        result, match, self.response = self._expect_any(prompt, flush)

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
        else:
            self._dbg(2, "No prompt match")

        self._dbg(5, "Response was %s" % repr(str(self.buffer)))

        if result == -1:
            error = 'Error while waiting for response from device'
            raise TimeoutException(error)
        if result == -2:
            if self.driver_replaced:
                self.driver_replaced = False
                raise DriverReplacedException()
            else:
                raise ExpectCancelledException()

        return result, match

    def close(self, force = False):
        self._say('\n')
        self.buffer.clear()

########NEW FILE########
__FILENAME__ = Exception
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Network related error types.
"""

class ProtocolException(Exception):
    """
    Default exception that is thrown on most protocol related errors.
    """
    pass

class TimeoutException(ProtocolException):
    """
    An exception that is thrown if the connected host did not
    respond for too long.
    """
    pass

class ExpectCancelledException(ProtocolException):
    """
    An exception that is thrown if Protocol.cancel_expect()
    was called.
    """
    pass

class DriverReplacedException(ProtocolException):
    """
    An exception that is thrown if the protocol driver
    was switched during a call to expect().
    """
    pass

class LoginFailure(ProtocolException):
    """
    An exception that is thrown if the response of a connected host looked
    like it was trying to signal a login error during the authentication
    procedure.
    """
    pass

class InvalidCommandException(ProtocolException):
    """
    An exception that is thrown if the response of a connected host contained
    a string that looked like an error.
    """
    pass

########NEW FILE########
__FILENAME__ = OsGuesser
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.protocols.drivers import drivers

class OsGuesser(object):
    """
    The OsGuesser monitors everything that happens on a Protocol,
    and attempts to collect data out of the network activity.
    It watches for specific patterns in the network traffic to decide
    what operating system a connected host is running.
    It is completely passive, and attempts no changes on the protocol
    adapter. However, the protocol adapter may request information
    from the OsGuesser, and perform changes based on the information
    provided.
    """

    def __init__(self):
        self.info        = {}
        self.debug       = False
        self.auth_os_map = [d._check_head for d in drivers]
        self.os_map      = [d._check_response for d in drivers]
        self.auth_buffer = ''
        self.set('os', 'unknown', 0)

    def reset(self):
        self.__init__()

    def set(self, key, value, confidence = 100):
        """
        Defines the given value with the given confidence, unless the same
        value is already defined with a higher confidence level.
        """
        if value is None:
            return
        if key in self.info:
            old_confidence, old_value = self.info.get(key)
            if old_confidence >= confidence:
                return
        self.info[key] = (confidence, value)

    def set_from_match(self, key, regex_list, string):
        """
        Given a list of functions or three-tuples (regex, value, confidence),
        this function walks through them and checks whether any of the
        items in the list matches the given string.
        If the list item is a function, it must have the following
        signature::

            func(string) : (string, int)

        Where the return value specifies the resulting value and the
        confidence of the match.
        If a match is found, and the confidence level is higher
        than the currently defined one, the given value is defined with
        the given confidence.
        """
        for item in regex_list:
            if hasattr(item, '__call__'):
                self.set(key, *item(string))
            else:
                regex, value, confidence = item
                if regex.search(string):
                    self.set(key, value, confidence)

    def get(self, key, confidence = 0):
        """
        Returns the info with the given key, if it has at least the given
        confidence. Returns None otherwise.
        """
        if key not in self.info:
            return None
        conf, value = self.info.get(key)
        if conf >= confidence:
            return value
        return None

    def data_received(self, data, app_authentication_done):
        # If the authentication procedure is complete, use the normal
        # "runtime" matchers.
        if app_authentication_done:
            # Stop looking if we are already 80 percent certain.
            if self.get('os', 80) in ('unknown', None):
                self.set_from_match('os', self.os_map, data)
            return

        # Else, check the head that we collected so far.
        self.auth_buffer += data
        if self.debug:
            print "DEBUG: Matching buffer:", repr(self.auth_buffer)
        self.set_from_match('os', self.auth_os_map, self.auth_buffer)
        self.set_from_match('os', self.os_map,      self.auth_buffer)

########NEW FILE########
__FILENAME__ = Protocol
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
An abstract base class for all protocols.
"""
import re
import sys
import select
import socket
import signal
import errno
import os
from functools import partial
from Exscript.util.impl import Context, _Context
from Exscript.util.buffer import MonitoredBuffer
from Exscript.util.crypt import otp
from Exscript.util.event import Event
from Exscript.util.cast import to_regexs
from Exscript.util.tty import get_terminal_size
from Exscript.protocols.drivers import driver_map, isdriver
from Exscript.protocols.OsGuesser import OsGuesser
from Exscript.protocols.Exception import InvalidCommandException, \
                                         LoginFailure, \
                                         TimeoutException, \
                                         DriverReplacedException, \
                                         ExpectCancelledException

try:
    import termios
    import tty
    _have_termios = True
except ImportError:
    _have_termios = False

_skey_re = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)')

class Protocol(object):
    """
    This is the base class for all protocols; it defines the common portions
    of the API.

    The goal of all protocol classes is to provide an interface that
    is unified accross protocols, such that the adapters may be used
    interchangably without changing any other code.

    In order to achieve this, the main challenge are the differences
    arising from the authentication methods that are used.
    The reason is that many devices may support the following variety
    authentification/authorization methods:

        1. Protocol level authentification, such as SSH's built-in
           authentication.

                - p1: password only
                - p2: username
                - p3: username + password
                - p4: username + key
                - p5: username + key + password

        2. App level authentification, such that the authentification may
           happen long after a connection is already accepted.
           This type of authentication is normally used in combination with
           Telnet, but some SSH hosts also do this (users have reported
           devices from Enterasys). These devices may also combine
           protocol-level authentification with app-level authentification.
           The following types of app-level authentication exist:

                - a1: password only
                - a2: username
                - a3: username + password

        3. App level authorization: In order to implement the AAA protocol,
           some devices ask for two separate app-level logins, whereas the
           first serves to authenticate the user, and the second serves to
           authorize him.
           App-level authorization may support the same methods as app-level
           authentification:

                - A1: password only
                - A2: username
                - A3: username + password

    We are assuming that the following methods are used:

        - Telnet:

          - p1 - p5: never
          - a1 - a3: optional
          - A1 - A3: optional

        - SSH:

          - p1 - p5: optional
          - a1 - a3: optional
          - A1 - A3: optional

    To achieve authentication method compatibility accross different
    protocols, we must hide all this complexity behind one single API
    call, and figure out which ones are supported.

    As a use-case, our goal is that the following code will always work,
    regardless of which combination of authentication methods a device
    supports::

        key = PrivateKey.from_file('~/.ssh/id_rsa', 'my_key_password')

        # The user account to use for protocol level authentification.
        # The key defaults to None, in which case key authentication is
        # not attempted.
        account = Account(name     = 'myuser',
                          password = 'mypassword',
                          key      = key)

        # The account to use for app-level authentification.
        # password2 defaults to password.
        app_account = Account(name      = 'myuser',
                              password  = 'my_app_password',
                              password2 = 'my_app_password2')

        # app_account defaults to account.
        conn.login(account, app_account = None, flush = True)

    Another important consideration is that once the login is complete, the
    device must be in a clearly defined state, i.e. we need to
    have processed the data that was retrieved from the connected host.

    More precisely, the buffer that contains the incoming data must be in
    a state such that the following call to expect_prompt() will either
    always work, or always fail.

    We jhide the following methods behind the login() call::

        # Protocol level authentification.
        conn.protocol_authenticate(...)
        # App-level authentification.
        conn.app_authenticate(...)
        # App-level authorization.
        conn.app_authorize(...)

    The code produces the following result::

        Telnet:
            conn.protocol_authenticate -> NOP
            conn.app_authenticate
                -> waits for username or password prompt, authenticates,
                   returns after a CLI prompt was seen.
            conn.app_authorize
                -> calls driver.enable(), waits for username or password
                   prompt, authorizes, returns after a CLI prompt was seen.

        SSH:
            conn.protocol_authenticate -> authenticates using user/key/password
            conn.app_authenticate -> like Telnet
            conn.app_authorize -> like Telnet

    We can see the following:

        - protocol_authenticate() must not wait for a prompt, because else
          app_authenticate() has no way of knowing whether an app-level
          login is even necessary.

        - app_authenticate() must check the buffer first, to see if
          authentication has already succeeded. In the case that
          app_authenticate() is not necessary (i.e. the buffer contains a
          CLI prompt), it just returns.

          app_authenticate() must NOT eat the prompt from the buffer, because
          else the result may be inconsistent with devices that do not do
          any authentication; i.e., when app_authenticate() is not called.

        - Since the prompt must still be contained in the buffer,
          conn.driver.app_authorize() needs to eat it before it sends the
          command for starting the authorization procedure.

          This has a drawback - if a user attempts to call app_authorize()
          at a time where there is no prompt in the buffer, it would fail.
          So we need to eat the prompt only in cases where we know that
          auto_app_authorize() will attempt to execute a command. Hence
          the driver requires the Driver.supports_auto_authorize() method.

          However, app_authorize() must not eat the CLI prompt that follows.

        - Once all logins are processed, it makes sense to eat the prompt
          depending on the wait parameter. Wait should default to True,
          because it's better that the connection stalls waiting forever,
          than to risk that an error is not immediately discovered due to
          timing issues (this is a race condition that I'm not going to
          detail here).
    """

    def __init__(self,
                 driver             = None,
                 stdout             = None,
                 stderr             = None,
                 debug              = 0,
                 timeout            = 30,
                 logfile            = None,
                 termtype           = 'dumb',
                 verify_fingerprint = True,
                 account_factory    = None):
        """
        Constructor.
        The following events are provided:

          - data_received_event: A packet was received from the connected host.
          - otp_requested_event: The connected host requested a
          one-time-password to be entered.

        @keyword driver: passed to set_driver().
        @keyword stdout: Where to write the device response. Defaults to
            os.devnull.
        @keyword stderr: Where to write debug info. Defaults to stderr.
        @keyword debug: An integer between 0 (no debugging) and 5 (very
            verbose debugging) that specifies the amount of debug info
            sent to the terminal. The default value is 0.
        @keyword timeout: See set_timeout(). The default value is 30.
        @keyword logfile: A file into which a log of the conversation with the
            device is dumped.
        @keyword termtype: The terminal type to request from the remote host,
            e.g. 'vt100'.
        @keyword verify_fingerprint: Whether to verify the host's fingerprint.
        @keyword account_factory: A function that produces a new L{Account}.
        """
        self.data_received_event   = Event()
        self.otp_requested_event   = Event()
        self.os_guesser            = OsGuesser()
        self.auto_driver           = driver_map[self.guess_os()]
        self.proto_authenticated   = False
        self.app_authenticated     = False
        self.app_authorized        = False
        self.manual_user_re        = None
        self.manual_password_re    = None
        self.manual_prompt_re      = None
        self.manual_error_re       = None
        self.manual_login_error_re = None
        self.driver_replaced       = False
        self.host                  = None
        self.port                  = None
        self.last_account          = None
        self.termtype              = termtype
        self.verify_fingerprint    = verify_fingerprint
        self.manual_driver         = driver
        self.debug                 = debug
        self.timeout               = timeout
        self.logfile               = logfile
        self.response              = None
        self.buffer                = MonitoredBuffer()
        self.account_factory       = account_factory
        if stdout is None:
            self.stdout = open(os.devnull, 'w')
        else:
            self.stdout = stdout
        if stderr is None:
            self.stderr = sys.stderr
        else:
            self.stderr = stderr
        if logfile is None:
            self.log = None
        else:
            self.log = open(logfile, 'a')

    def __copy__(self):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @rtype:  Protocol
        @return: self
        """
        return self

    def __deepcopy__(self, memo):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @type  memo: object
        @param memo: Please refer to Python's standard library documentation.
        @rtype:  Protocol
        @return: self
        """
        return self

    def _driver_replaced_notify(self, old, new):
        self.driver_replaced = True
        self.cancel_expect()
        msg = 'Protocol: driver replaced: %s -> %s' % (old.name, new.name)
        self._dbg(1, msg)

    def _receive_cb(self, data, remove_cr = True):
        # Clean the data up.
        if remove_cr:
            text = data.replace('\r', '')
        else:
            text = data

        # Write to a logfile.
        self.stdout.write(text)
        self.stdout.flush()
        if self.log is not None:
            self.log.write(text)

        # Check whether a better driver is found based on the incoming data.
        old_driver = self.get_driver()
        self.os_guesser.data_received(data, self.is_app_authenticated())
        self.auto_driver = driver_map[self.guess_os()]
        new_driver       = self.get_driver()
        if old_driver != new_driver:
            self._driver_replaced_notify(old_driver, new_driver)

        # Send signals to subscribers.
        self.data_received_event(data)

    def is_dummy(self):
        """
        Returns True if the adapter implements a virtual device, i.e.
        it isn't an actual network connection.

        @rtype:  Boolean
        @return: True for dummy adapters, False for network adapters.
        """
        return False

    def _dbg(self, level, msg):
        if self.debug < level:
            return
        self.stderr.write(self.get_driver().name + ': ' + msg + '\n')

    def set_driver(self, driver = None):
        """
        Defines the driver that is used to recognize prompts and implement
        behavior depending on the remote system.
        The driver argument may be an subclass of protocols.drivers.Driver,
        a known driver name (string), or None.
        If the driver argument is None, the adapter automatically chooses
        a driver using the the guess_os() function.

        @type  driver: Driver|str
        @param driver: The pattern that, when matched, causes an error.
        """
        if driver is None:
            self.manual_driver = None
        elif isinstance(driver, str):
            if driver not in driver_map:
                raise TypeError('no such driver:' + repr(driver))
            self.manual_driver = driver_map[driver]
        elif isdriver(driver):
            self.manual_driver = driver
        else:
            raise TypeError('unsupported argument type:' + type(driver))

    def get_driver(self):
        """
        Returns the currently used driver.

        @rtype:  Driver
        @return: A regular expression.
        """
        if self.manual_driver:
            return self.manual_driver
        return self.auto_driver

    def autoinit(self):
        """
        Make the remote host more script-friendly by automatically executing
        one or more commands on it.
        The commands executed depend on the currently used driver.
        For example, the driver for Cisco IOS would execute the
        following commands::

            term len 0
            term width 0
        """
        self.get_driver().init_terminal(self)

    def set_username_prompt(self, regex = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a username prompt.

        @type  regex: RegEx
        @param regex: The pattern that, when matched, causes an error.
        """
        if regex is None:
            self.manual_user_re = regex
        else:
            self.manual_user_re = to_regexs(regex)

    def get_username_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for a username prompt.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_user_re:
            return self.manual_user_re
        return self.get_driver().user_re

    def set_password_prompt(self, regex = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host for a password prompt.

        @type  regex: RegEx
        @param regex: The pattern that, when matched, causes an error.
        """
        if regex is None:
            self.manual_password_re = regex
        else:
            self.manual_password_re = to_regexs(regex)

    def get_password_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for a username prompt.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_password_re:
            return self.manual_password_re
        return self.get_driver().password_re

    def set_prompt(self, prompt = None):
        """
        Defines a pattern that is waited for when calling the expect_prompt()
        method.
        If the set_prompt() method is not called, or if it is called with the
        prompt argument set to None, a default prompt is used that should
        work with many devices running Unix, IOS, IOS-XR, or Junos and others.

        @type  prompt: RegEx
        @param prompt: The pattern that matches the prompt of the remote host.
        """
        if prompt is None:
            self.manual_prompt_re = prompt
        else:
            self.manual_prompt_re = to_regexs(prompt)

    def get_prompt(self):
        """
        Returns the regular expressions that is matched against the host
        response when calling the expect_prompt() method.

        @rtype:  list(re.RegexObject)
        @return: A list of regular expression objects.
        """
        if self.manual_prompt_re:
            return self.manual_prompt_re
        return self.get_driver().prompt_re

    def set_error_prompt(self, error = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host. If the pattern matches (any time the expect() or
        expect_prompt() methods are used), an error is raised.

        @type  error: RegEx
        @param error: The pattern that, when matched, causes an error.
        """
        if error is None:
            self.manual_error_re = error
        else:
            self.manual_error_re = to_regexs(error)

    def get_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for errors.

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_error_re:
            return self.manual_error_re
        return self.get_driver().error_re

    def set_login_error_prompt(self, error = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host during the authentication procedure.
        If the pattern matches an error is raised.

        @type  error: RegEx
        @param error: The pattern that, when matched, causes an error.
        """
        if error is None:
            self.manual_login_error_re = error
        else:
            self.manual_login_error_re = to_regexs(error)

    def get_login_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for login errors; this is only used during
        the login procedure, i.e. app_authenticate() or app_authorize().

        @rtype:  regex
        @return: A regular expression.
        """
        if self.manual_login_error_re:
            return self.manual_login_error_re
        return self.get_driver().login_error_re

    def set_timeout(self, timeout):
        """
        Defines the maximum time that the adapter waits before a call to
        L{expect()} or L{expect_prompt()} fails.

        @type  timeout: int
        @param timeout: The maximum time in seconds.
        """
        self.timeout = int(timeout)

    def get_timeout(self):
        """
        Returns the current timeout in seconds.

        @rtype:  int
        @return: The timeout in seconds.
        """
        return self.timeout

    def _connect_hook(self, host, port):
        """
        Should be overwritten.
        """
        raise NotImplementedError()

    def connect(self, hostname = None, port = None):
        """
        Opens the connection to the remote host or IP address.

        @type  hostname: string
        @param hostname: The remote host or IP address.
        @type  port: int
        @param port: The remote TCP port number.
        """
        if hostname is not None:
            self.host = hostname
        return self._connect_hook(self.host, port)

    def _get_account(self, account):
        if isinstance(account, Context) or isinstance(account, _Context):
            return account.context()
        if account is None:
            account = self.last_account
        if self.account_factory:
            account = self.account_factory(account)
        else:
            if account is None:
                raise TypeError('An account is required')
            account.__enter__()
        self.last_account = account
        return account.context()

    def login(self, account = None, app_account = None, flush = True):
        """
        Log into the connected host using the best method available.
        If an account is not given, default to the account that was
        used during the last call to login(). If a previous call was not
        made, use the account that was passed to the constructor. If that
        also fails, raise a TypeError.

        The app_account is passed to L{app_authenticate()} and
        L{app_authorize()}.
        If app_account is not given, default to the value of the account
        argument.

        @type  account: Account
        @param account: The account for protocol level authentification.
        @type  app_account: Account
        @param app_account: The account for app level authentification.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        """
        with self._get_account(account) as account:
            if app_account is None:
                app_account = account
            self.authenticate(account, flush = False)
            if self.get_driver().supports_auto_authorize():
                self.expect_prompt()
            self.auto_app_authorize(app_account, flush = flush)

    def authenticate(self, account = None, app_account = None, flush = True):
        """
        Like login(), but skips the authorization procedure.

        @note: If you are unsure whether to use L{authenticate()} or
            L{login()}, stick with L{login}.

        @type  account: Account
        @param account: The account for protocol level authentification.
        @type  app_account: Account
        @param app_account: The account for app level authentification.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        """
        with self._get_account(account) as account:
            if app_account is None:
                app_account = account

            self.protocol_authenticate(account)
            self.app_authenticate(app_account, flush = flush)

    def _protocol_authenticate(self, user, password):
        pass

    def _protocol_authenticate_by_key(self, user, key):
        pass

    def protocol_authenticate(self, account = None):
        """
        Low-level API to perform protocol-level authentification on protocols
        that support it.

        @note: In most cases, you want to use the login() method instead, as
           it automatically chooses the best login method for each protocol.

        @type  account: Account
        @param account: An account object, like login().
        """
        with self._get_account(account) as account:
            user     = account.get_name()
            password = account.get_password()
            key      = account.get_key()
            if key is None:
                self._dbg(1, "Attempting to authenticate %s." % user)
                self._protocol_authenticate(user, password)
            else:
                self._dbg(1, "Authenticate %s with key." % user)
                self._protocol_authenticate_by_key(user, key)
        self.proto_authenticated = True

    def is_protocol_authenticated(self):
        """
        Returns True if the protocol-level authentication procedure was
        completed, False otherwise.

        @rtype:  bool
        @return: Whether the authentication was completed.
        """
        return self.proto_authenticated

    def _app_authenticate(self,
                          account,
                          password,
                          flush   = True,
                          bailout = False):
        user = account.get_name()

        while True:
            # Wait for any prompt. Once a match is found, we need to be able
            # to find out which type of prompt was matched, so we build a
            # structure to allow for mapping the match index back to the
            # prompt type.
            prompts = (('login-error', self.get_login_error_prompt()),
                       ('username',    self.get_username_prompt()),
                       ('skey',        [_skey_re]),
                       ('password',    self.get_password_prompt()),
                       ('cli',         self.get_prompt()))
            prompt_map  = []
            prompt_list = []
            for section, sectionprompts in prompts:
                for prompt in sectionprompts:
                    prompt_map.append((section, prompt))
                    prompt_list.append(prompt)

            # Wait for the prompt.
            try:
                index, match = self._waitfor(prompt_list)
            except TimeoutException:
                if self.response is None:
                    self.response = ''
                msg = "Buffer: %s" % repr(self.response)
                raise TimeoutException(msg)
            except DriverReplacedException:
                # Driver replaced, retry.
                self._dbg(1, 'Protocol.app_authenticate(): driver replaced')
                continue
            except ExpectCancelledException:
                self._dbg(1, 'Protocol.app_authenticate(): expect cancelled')
                raise
            except EOFError:
                self._dbg(1, 'Protocol.app_authenticate(): EOF')
                raise

            # Login error detected.
            section, prompt = prompt_map[index]
            if section == 'login-error':
                raise LoginFailure("Login failed")

            # User name prompt.
            elif section == 'username':
                self._dbg(1, "Username prompt %s received." % index)
                self.expect(prompt) # consume the prompt from the buffer
                self.send(user + '\r')
                continue

            # s/key prompt.
            elif section == 'skey':
                self._dbg(1, "S/Key prompt received.")
                self.expect(prompt) # consume the prompt from the buffer
                seq  = int(match.group(1))
                seed = match.group(2)
                self.otp_requested_event(account, seq, seed)
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp(password, seed, seq)

                # A password prompt is now required.
                self.expect(self.get_password_prompt())
                self.send(phrase + '\r')
                self._dbg(1, "Password sent.")
                if bailout:
                    break
                continue

            # Cleartext password prompt.
            elif section == 'password':
                self._dbg(1, "Cleartext password prompt received.")
                self.expect(prompt) # consume the prompt from the buffer
                self.send(password + '\r')
                if bailout:
                    break
                continue

            # Shell prompt.
            elif section == 'cli':
                self._dbg(1, 'Shell prompt received.')
                if flush:
                    self.expect_prompt()
                break

            else:
                assert False # No such section

    def app_authenticate(self, account = None, flush = True, bailout = False):
        """
        Attempt to perform application-level authentication. Application
        level authentication is needed on devices where the username and
        password are requested from the user after the connection was
        already accepted by the remote device.

        The difference between app-level authentication and protocol-level
        authentication is that in the latter case, the prompting is handled
        by the client, whereas app-level authentication is handled by the
        remote device.

        App-level authentication comes in a large variety of forms, and
        while this method tries hard to support them all, there is no
        guarantee that it will always work.

        We attempt to smartly recognize the user and password prompts;
        for a list of supported operating systems please check the
        Exscript.protocols.drivers module.

        Returns upon finding the first command line prompt. Depending
        on whether the flush argument is True, it also removes the
        prompt from the incoming buffer.

        @type  account: Account
        @param account: An account object, like login().
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  bailout: bool
        @param bailout: Whether to wait for a prompt after sending the password.
        """
        with self._get_account(account) as account:
            user     = account.get_name()
            password = account.get_password()
            self._dbg(1, "Attempting to app-authenticate %s." % user)
            self._app_authenticate(account, password, flush, bailout)
        self.app_authenticated = True

    def is_app_authenticated(self):
        """
        Returns True if the application-level authentication procedure was
        completed, False otherwise.

        @rtype:  bool
        @return: Whether the authentication was completed.
        """
        return self.app_authenticated

    def app_authorize(self, account = None, flush = True, bailout = False):
        """
        Like app_authenticate(), but uses the authorization password
        of the account.

        For the difference between authentication and authorization
        please google for AAA.

        @type  account: Account
        @param account: An account object, like login().
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  bailout: bool
        @param bailout: Whether to wait for a prompt after sending the password.
        """
        with self._get_account(account) as account:
            user     = account.get_name()
            password = account.get_authorization_password()
            if password is None:
                password = account.get_password()
            self._dbg(1, "Attempting to app-authorize %s." % user)
            self._app_authenticate(account, password, flush, bailout)
        self.app_authorized = True

    def auto_app_authorize(self, account = None, flush = True, bailout = False):
        """
        Like authorize(), but instead of just waiting for a user or
        password prompt, it automatically initiates the authorization
        procedure by sending a driver-specific command.

        In the case of devices that understand AAA, that means sending
        a command to the device. For example, on routers running Cisco
        IOS, this command executes the 'enable' command before expecting
        the password.

        In the case of a device that is not recognized to support AAA, this
        method does nothing.

        @type  account: Account
        @param account: An account object, like login().
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  bailout: bool
        @param bailout: Whether to wait for a prompt after sending the password.
        """
        with self._get_account(account) as account:
            self._dbg(1, 'Calling driver.auto_authorize().')
            self.get_driver().auto_authorize(self, account, flush, bailout)

    def is_app_authorized(self):
        """
        Returns True if the application-level authorization procedure was
        completed, False otherwise.

        @rtype:  bool
        @return: Whether the authorization was completed.
        """
        return self.app_authorized

    def send(self, data):
        """
        Sends the given data to the remote host.
        Returns without waiting for a response.

        @type  data: string
        @param data: The data that is sent to the remote host.
        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        raise NotImplementedError()

    def execute(self, command):
        """
        Sends the given data to the remote host (with a newline appended)
        and waits for a prompt in the response. The prompt attempts to use
        a sane default that works with many devices running Unix, IOS,
        IOS-XR, or Junos and others. If that fails, a custom prompt may
        also be defined using the set_prompt() method.
        This method also modifies the value of the response (self.response)
        attribute, for details please see the documentation of the
        expect() method.

        @type  command: string
        @param command: The data that is sent to the remote host.
        @rtype:  int, re.MatchObject
        @return: The index of the prompt regular expression that matched,
          and the match object.
        """
        self.send(command + '\r')
        return self.expect_prompt()

    def _domatch(self, prompt, flush):
        """
        Should be overwritten.
        """
        raise NotImplementedError()

    def _waitfor(self, prompt):
        re_list  = to_regexs(prompt)
        patterns = [p.pattern for p in re_list]
        self._dbg(2, 'waiting for: ' + repr(patterns))
        result = self._domatch(re_list, False)
        return result

    def waitfor(self, prompt):
        """
        Monitors the data received from the remote host and waits until
        the response matches the given prompt.
        Once a match has been found, the buffer containing incoming data
        is NOT changed. In other words, consecutive calls to this function
        will always work, e.g.::

            conn.waitfor('myprompt>')
            conn.waitfor('myprompt>')
            conn.waitfor('myprompt>')

        will always work. Hence in most cases, you probably want to use
        expect() instead.

        This method also stores the received data in the response
        attribute (self.response).

        Returns the index of the regular expression that matched.

        @type  prompt: str|re.RegexObject|list(str|re.RegexObject)
        @param prompt: One or more regular expressions.
        @rtype:  int, re.MatchObject
        @return: The index of the regular expression that matched,
          and the match object.

        @raise TimeoutException: raised if the timeout was reached.
        @raise ExpectCancelledException: raised when cancel_expect() was
            called in a callback.
        @raise ProtocolException: on other internal errors.
        @raise Exception: May raise other exceptions that are caused
            within the underlying protocol implementations.
        """
        while True:
            try:
                result = self._waitfor(prompt)
            except DriverReplacedException:
                continue # retry
            return result

    def _expect(self, prompt):
        result = self._domatch(to_regexs(prompt), True)
        return result

    def expect(self, prompt):
        """
        Like waitfor(), but also removes the matched string from the buffer
        containing the incoming data. In other words, the following may not
        alway complete::

            conn.expect('myprompt>')
            conn.expect('myprompt>') # timeout

        Returns the index of the regular expression that matched.

        @note: May raise the same exceptions as L{waitfor}.

        @type  prompt: str|re.RegexObject|list(str|re.RegexObject)
        @param prompt: One or more regular expressions.
        @rtype:  int, re.MatchObject
        @return: The index of the regular expression that matched,
          and the match object.
        """
        while True:
            try:
                result = self._expect(prompt)
            except DriverReplacedException:
                continue # retry
            return result

    def expect_prompt(self):
        """
        Monitors the data received from the remote host and waits for a
        prompt in the response. The prompt attempts to use
        a sane default that works with many devices running Unix, IOS,
        IOS-XR, or Junos and others. If that fails, a custom prompt may
        also be defined using the set_prompt() method.
        This method also stores the received data in the response
        attribute (self.response).

        @rtype:  int, re.MatchObject
        @return: The index of the prompt regular expression that matched,
          and the match object.
        """
        result = self.expect(self.get_prompt())

        # We skip the first line because it contains the echo of the command
        # sent.
        self._dbg(5, "Checking %s for errors" % repr(self.response))
        for line in self.response.split('\n')[1:]:
            for prompt in self.get_error_prompt():
                if not prompt.search(line):
                    continue
                args = repr(prompt.pattern), repr(line)
                self._dbg(5, "error prompt (%s) matches %s" % args)
                raise InvalidCommandException('Device said:\n' + self.response)

        return result

    def add_monitor(self, pattern, callback, limit = 80):
        """
        Calls the given function whenever the given pattern matches the
        incoming data.

        @note: If you want to catch all incoming data regardless of a
        pattern, use the L{Protocol.on_data_received} event instead.

        Arguments passed to the callback are the protocol instance, the
        index of the match, and the match object of the regular expression.

        @type  pattern: str|re.RegexObject|list(str|re.RegexObject)
        @param pattern: One or more regular expressions.
        @type  callback: callable
        @param callback: The function that is called.
        @type  limit: int
        @param limit: The maximum size of the tail of the buffer
                      that is searched, in number of bytes.
        """
        self.buffer.add_monitor(pattern, partial(callback, self), limit)

    def cancel_expect(self):
        """
        Cancel the current call to L{expect()} as soon as control returns
        to the protocol adapter. This method may be used in callbacks to
        the events emitted by this class, e.g. Protocol.data_received_event.
        """
        raise NotImplementedError()

    def _call_key_handlers(self, key_handlers, data):
        if key_handlers is not None:
            for key, func in key_handlers.iteritems():
                if data == key:
                    func(self)
                    return True
        return False

    def _set_terminal_size(self, rows, cols):
        raise NotImplementedError()

    def _open_posix_shell(self,
                          channel,
                          key_handlers,
                          handle_window_size):
        # We need to make sure to use an unbuffered stdin, else multi-byte
        # chars (such as arrow keys) won't work properly.
        stdin  = os.fdopen(sys.stdin.fileno(), 'r', 0)
        oldtty = termios.tcgetattr(stdin)

        # Update the terminal size whenever the size changes.
        if handle_window_size:
            def handle_sigwinch(signum, frame):
                rows, cols = get_terminal_size()
                self._set_terminal_size(rows, cols)
            signal.signal(signal.SIGWINCH, handle_sigwinch)
            handle_sigwinch(None, None)

        # Read from stdin and write to the network, endlessly.
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            channel.settimeout(0.0)

            while True:
                try:
                    r, w, e = select.select([channel, stdin], [], [])
                except select.error, e:
                    code, message = e
                    if code == errno.EINTR:
                        # This may happen when SIGWINCH is called
                        # during the select; we just retry then.
                        continue
                    raise

                if channel in r:
                    try:
                        data = channel.recv(1024)
                    except socket.timeout:
                        pass
                    if not data:
                        self._dbg(1, 'EOF from remote')
                        break
                    self._receive_cb(data, False)
                    self.buffer.append(data)
                if stdin in r:
                    data = stdin.read(1)
                    self.buffer.clear()
                    if len(data) == 0:
                        break

                    # Temporarily revert stdin behavior while callbacks are
                    # active.
                    curtty = termios.tcgetattr(stdin)
                    termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)
                    is_handled = self._call_key_handlers(key_handlers, data)
                    termios.tcsetattr(stdin, termios.TCSADRAIN, curtty)

                    if not is_handled:
                        channel.send(data)
        finally:
            termios.tcsetattr(stdin, termios.TCSADRAIN, oldtty)

    def _open_windows_shell(self, channel, key_handlers):
        import threading

        def writeall(sock):
            while True:
                data = sock.recv(256)
                if not data:
                    self._dbg(1, 'EOF from remote')
                    break
                self._receive_cb(data)

        writer = threading.Thread(target=writeall, args=(channel,))
        writer.start()

        try:
            while True:
                data = sys.stdin.read(1)
                if not data:
                    break
                if not self._call_key_handlers(key_handlers, data):
                    channel.send(data)
        except EOFError:
            self._dbg(1, 'User hit ^Z or F6')

    def _open_shell(self, channel, key_handlers, handle_window_size):
        if _have_termios:
            return self._open_posix_shell(channel, key_handlers, handle_window_size)
        else:
            return self._open_windows_shell(channel, key_handlers, handle_window_size)

    def interact(self, key_handlers = None, handle_window_size = True):
        """
        Opens a simple interactive shell. Returns when the remote host
        sends EOF.
        The optional key handlers are functions that are called whenever
        the user presses a specific key. For example, to catch CTRL+y::

            conn.interact({'\031': mycallback})

        @type  key_handlers: dict(str: callable)
        @param key_handlers: A dictionary mapping chars to a functions.
        @type  handle_window_size: bool
        @param handle_window_size: Whether the connected host is notified
          when the terminal size changes.
        """
        raise NotImplementedError()

    def close(self, force = False):
        """
        Closes the connection with the remote host.
        """
        raise NotImplementedError()

    def get_host(self):
        """
        Returns the name or address of the currently connected host.

        @rtype:  string
        @return: A name or an address.
        """
        return self.host

    def guess_os(self):
        """
        Returns an identifer that specifies the operating system that is
        running on the remote host. This OS is obtained by watching the
        response of the remote host, such as any messages retrieved during
        the login procedure.

        The OS is also a wild guess that often depends on volatile
        information, so there is no guarantee that this will always work.

        @rtype:  string
        @return: A string to help identify the remote operating system.
        """
        return self.os_guesser.get('os')

########NEW FILE########
__FILENAME__ = SSH2
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
SSH version 2 support, based on paramiko.
"""
import os
import time
import select
import socket
import paramiko
import Crypto
from binascii               import hexlify
from paramiko               import util
from paramiko.resource      import ResourceManager
from paramiko.ssh_exception import SSHException, \
                                   AuthenticationException, \
                                   BadHostKeyException
from Exscript.util.tty            import get_terminal_size
from Exscript.PrivateKey          import PrivateKey
from Exscript.protocols.Protocol  import Protocol
from Exscript.protocols.Exception import ProtocolException, \
                                         LoginFailure, \
                                         TimeoutException, \
                                         DriverReplacedException, \
                                         ExpectCancelledException

# Workaround for paramiko error; avoids a warning message.
util.log_to_file(os.devnull)

# Register supported key types.
keymap = {'rsa': paramiko.RSAKey, 'dss': paramiko.DSSKey}
for key in keymap:
    PrivateKey.keytypes.add(key)

class SSH2(Protocol):
    """
    The secure shell protocol version 2 adapter, based on Paramiko.
    """
    KEEPALIVE_INTERVAL = 2.5 * 60    # Two and a half minutes

    def __init__(self, **kwargs):
        Protocol.__init__(self, **kwargs)
        self.client = None
        self.shell  = None
        self.cancel = False

        # Since each protocol may be created in it's own thread, we must
        # re-initialize the random number generator to make sure that
        # child threads have no way of guessing the numbers of the parent.
        # If we don't, PyCrypto generates an error message for security
        # reasons.
        try:
            Crypto.Random.atfork()
        except AttributeError:
            # pycrypto versions that have no "Random" module also do not
            # detect the missing atfork() call, so they do not raise.
            pass

        # Paramiko client stuff.
        self._system_host_keys   = paramiko.HostKeys()
        self._host_keys          = paramiko.HostKeys()
        self._host_keys_filename = None

        if self.verify_fingerprint:
            self._missing_host_key = self._reject_host_key
        else:
            self._missing_host_key = self._add_host_key

    def _reject_host_key(self, key):
        name = key.get_name()
        fp   = hexlify(key.get_fingerprint())
        msg  = 'Rejecting %s host key for %s: %s' % (name, self.host, fp)
        self._dbg(1, msg)

    def _add_host_key(self, key):
        name = key.get_name()
        fp   = hexlify(key.get_fingerprint())
        msg  = 'Adding %s host key for %s: %s' % (name, self.host, fp)
        self._dbg(1, msg)
        self._host_keys.add(self.host, name, key)
        if self._host_keys_filename is not None:
            self._save_host_keys()

    def _save_host_keys(self):
        with open(self._host_keys_filename, 'w') as file:
            file.write('# SSH host keys collected by Exscript\n')
            for hostname, keys in self._host_keys.iteritems():
                for keytype, key in keys.iteritems():
                    line = ' '.join((hostname, keytype, key.get_base64()))
                    file.write(line + '\n')

    def _load_system_host_keys(self, filename = None):
        """
        Load host keys from a system (read-only) file.  Host keys read with
        this method will not be saved back by L{save_host_keys}.

        This method can be called multiple times.  Each new set of host keys
        will be merged with the existing set (new replacing old if there are
        conflicts).

        If C{filename} is left as C{None}, an attempt will be made to read
        keys from the user's local "known hosts" file, as used by OpenSSH,
        and no exception will be raised if the file can't be read.  This is
        probably only useful on posix.

        @param filename: the filename to read, or C{None}
        @type filename: str

        @raise IOError: if a filename was provided and the file could not be
            read
        """
        if filename is None:
            # try the user's .ssh key file, and mask exceptions
            filename = os.path.expanduser('~/.ssh/known_hosts')
            try:
                self._system_host_keys.load(filename)
            except IOError:
                pass
            return
        self._system_host_keys.load(filename)

    def _paramiko_connect(self):
        # Find supported address families.
        addrinfo = socket.getaddrinfo(self.host, self.port)
        for family, socktype, proto, canonname, sockaddr in addrinfo:
            af = family
            addr = sockaddr
            if socktype == socket.SOCK_STREAM:
                break

        # Open a socket.
        sock = socket.socket(af, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout or None)
        except:
            pass
        sock.connect(addr)

        # Init the paramiko protocol.
        t = paramiko.Transport(sock)
        t.start_client()
        ResourceManager.register(self, t)

        # Check system host keys.
        server_key = t.get_remote_server_key()
        keytype = server_key.get_name()
        our_server_key = self._system_host_keys.get(self.host, {}).get(keytype, None)
        if our_server_key is None:
            our_server_key = self._host_keys.get(self.host, {}).get(keytype, None)
        if our_server_key is None:
            self._missing_host_key(server_key)
            # if the callback returns, assume the key is ok
            our_server_key = server_key
        if server_key != our_server_key:
            raise BadHostKeyException(self.host, server_key, our_server_key)

        t.set_keepalive(self.KEEPALIVE_INTERVAL)
        return t

    def _paramiko_auth_none(self, username, password = None):
        self.client.auth_none(username)

    def _paramiko_auth_password(self, username, password):
        self.client.auth_password(username, password or '')

    def _paramiko_auth_agent(self, username, password = None):
        keys = paramiko.Agent().get_keys()
        if not keys:
            raise AuthenticationException('auth agent found no keys')

        saved_exception = AuthenticationException(
            'Failed to authenticate with given username')

        for key in keys:
            try:
                fp = hexlify(key.get_fingerprint())
                self._dbg(1, 'Trying SSH agent key %s' % fp)
                self.client.auth_publickey(username, key)
                return
            except SSHException, e:
                saved_exception = e
        raise saved_exception

    def _paramiko_auth_key(self, username, keys, password):
        if password is None:
            password = ''

        saved_exception = AuthenticationException(
            'Failed to authenticate with given username and password/key')

        for pkey_class, filename in keys:
            try:
                key = pkey_class.from_private_key_file(filename, password)
                fp  = hexlify(key.get_fingerprint())
                self._dbg(1, 'Trying key %s in %s' % (fp, filename))
                self.client.auth_publickey(username, key)
                return
            except SSHException, e:
                saved_exception = e
            except IOError, e:
                saved_exception = e
        raise saved_exception

    def _paramiko_auth_autokey(self, username, password):
        keyfiles = []
        for cls, file in ((paramiko.RSAKey, '~/.ssh/id_rsa'), # Unix
                          (paramiko.DSSKey, '~/.ssh/id_dsa'), # Unix
                          (paramiko.RSAKey, '~/ssh/id_rsa'),  # Windows
                          (paramiko.DSSKey, '~/ssh/id_dsa')): # Windows
            file = os.path.expanduser(file)
            if os.path.isfile(file):
                keyfiles.append((cls, file))
        self._paramiko_auth_key(username, keyfiles, password)

    def _paramiko_auth(self, username, password):
        for method in (self._paramiko_auth_password,
                       self._paramiko_auth_agent,
                       self._paramiko_auth_autokey,
                       self._paramiko_auth_none):
            self._dbg(1, 'Authenticating with %s' % method.__name__)
            try:
                method(username, password)
                return
            except BadHostKeyException, e:
                self._dbg(1, 'Bad host key!')
                last_exception = e
            except AuthenticationException, e:
                self._dbg(1, 'Authentication with %s failed' % method.__name__)
                last_exception = e
            except SSHException, e:
                self._dbg(1, 'Missing host key.')
                last_exception = e
        raise LoginFailure('Login failed: ' + str(last_exception))

    def _paramiko_shell(self):
        rows, cols = get_terminal_size()

        try:
            self.shell = self.client.open_session()
            self.shell.get_pty(self.termtype, cols, rows)
            self.shell.invoke_shell()
        except SSHException, e:
            self._dbg(1, 'Failed to open shell.')
            raise LoginFailure('Failed to open shell: ' + str(e))

    def _connect_hook(self, hostname, port):
        self.host   = hostname
        self.port   = port or 22
        self.client = self._paramiko_connect()
        self._load_system_host_keys()
        return True

    def _protocol_authenticate(self, user, password):
        self._paramiko_auth(user, password)
        self._paramiko_shell()

    def _protocol_authenticate_by_key(self, user, key):
        # Allow multiple key files.
        key_file = key.get_filename()
        if key_file is None:
            key_file = []
        elif isinstance(key_file, (str, unicode)):
            key_file = [key_file]

        # Try each key.
        keys = []
        for file in key_file:
            keys.append((keymap[key.get_type()], file))
        self._dbg(1, 'authenticating using _paramiko_auth_key().')
        self._paramiko_auth_key(user, keys, key.get_password())

        self._paramiko_shell()

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        self.shell.sendall(data)

    def _wait_for_data(self):
        end = time.time() + self.timeout
        while True:
            readable, writeable, excp = select.select([self.shell], [], [], 1)
            if readable:
                return True
            if time.time() > end:
                return False

    def _fill_buffer(self):
        # Wait for a response of the device.
        if not self._wait_for_data():
            error = 'Timeout while waiting for response from device'
            raise TimeoutException(error)

        # Read the response.
        data = self.shell.recv(200)
        if not data:
            return False
        self._receive_cb(data)
        self.buffer.append(data)
        return True

    def _domatch(self, prompt, flush):
        self._dbg(1, "Expecting a prompt")
        self._dbg(2, "Expected pattern: " + repr(p.pattern for p in prompt))
        search_window_size = 150
        while not self.cancel:
            # Check whether what's buffered matches the prompt.
            driver        = self.get_driver()
            search_window = self.buffer.tail(search_window_size)
            search_window, incomplete_tail = driver.clean_response_for_re_match(search_window)
            match         = None
            for n, regex in enumerate(prompt):
                match = regex.search(search_window)
                if match is not None:
                    break

            if not match:
                if not self._fill_buffer():
                    error = 'EOF while waiting for response from device'
                    raise ProtocolException(error)
                continue

            end = self.buffer.size() - len(search_window) + match.end()
            if flush:
                self.response = self.buffer.pop(end)
            else:
                self.response = self.buffer.head(end)
            return n, match

        # Ending up here, self.cancel_expect() was called.
        self.cancel = False
        if self.driver_replaced:
            self.driver_replaced = False
            raise DriverReplacedException()
        raise ExpectCancelledException()

    def cancel_expect(self):
        self.cancel = True

    def _set_terminal_size(self, rows, cols):
        self.shell.resize_pty(cols, rows)

    def interact(self, key_handlers = None, handle_window_size = True):
        return self._open_shell(self.shell, key_handlers, handle_window_size)

    def close(self, force = False):
        if self.shell is None:
            return
        if not force:
            self._fill_buffer()
        self.shell.close()
        self.shell = None
        self.client.close()
        self.client = None
        self.buffer.clear()

########NEW FILE########
__FILENAME__ = Telnet
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
The Telnet protocol.
"""
from Exscript.util.tty            import get_terminal_size
from Exscript.protocols           import telnetlib
from Exscript.protocols.Protocol  import Protocol
from Exscript.protocols.Exception import ProtocolException, \
                                         TimeoutException, \
                                         DriverReplacedException, \
                                         ExpectCancelledException

class Telnet(Protocol):
    """
    The Telnet protocol adapter.
    """

    def __init__(self, **kwargs):
        Protocol.__init__(self, **kwargs)
        self.tn = None

    def _telnetlib_received(self, data):
        self._receive_cb(data)
        self.buffer.append(data)

    def _connect_hook(self, hostname, port):
        assert self.tn is None
        rows, cols = get_terminal_size()
        self.tn = telnetlib.Telnet(hostname,
                                   port or 23,
                                   termsize         = (rows, cols),
                                   termtype         = self.termtype,
                                   stderr           = self.stderr,
                                   receive_callback = self._telnetlib_received)
        if self.debug >= 5:
            self.tn.set_debuglevel(1)
        if self.tn is None:
            return False
        return True

    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        try:
            self.tn.write(data)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise

    def _domatch(self, prompt, flush):
        if flush:
            func = self.tn.expect
        else:
            func = self.tn.waitfor

        # Wait for a prompt.
        clean = self.get_driver().clean_response_for_re_match
        self.response = None
        try:
            result, match, self.response = func(prompt, self.timeout, cleanup = clean)
        except Exception:
            self._dbg(1, 'Error while waiting for ' + repr(prompt))
            raise

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
            self.buffer.pop(len(self.response))

        self._dbg(5, "Response was %s" % repr(self.response))

        if result == -1:
            error = 'Error while waiting for response from device'
            raise TimeoutException(error)
        if result == -2:
            if self.driver_replaced:
                self.driver_replaced = False
                raise DriverReplacedException()
            else:
                raise ExpectCancelledException()
        if self.response is None:
            raise ProtocolException('whoops - response is None')

        return result, match

    def cancel_expect(self):
        self.tn.cancel_expect = True

    def _set_terminal_size(self, rows, cols):
        self.tn.set_window_size(rows, cols)

    def interact(self, key_handlers = None, handle_window_size = True):
        return self._open_shell(self.tn.sock, key_handlers, handle_window_size)

    def close(self, force = False):
        if self.tn is None:
            return
        if not force:
            try:
                self.response = self.tn.read_all()
            except Exception:
                pass
        self.tn.close()
        self.tn = None
        self.buffer.clear()

########NEW FILE########
__FILENAME__ = telnetlib
"""TELNET client class.

Based on RFC 854: TELNET Protocol Specification, by J. Postel and
J. Reynolds

Example:

>>> from telnetlib import Telnet
>>> tn = Telnet('www.python.org', 79)   # connect to finger port
>>> tn.write('guido\r\n')
>>> print tn.read_all()
Login       Name               TTY         Idle    When    Where
guido    Guido van Rossum      pts/2        <Dec  2 11:10> snag.cnri.reston..

>>>

Note that read_all() won't read until eof -- it just reads some data
-- but it guarantees to read at least one byte unless EOF is hit.

It is possible to pass a Telnet object to select.select() in order to
wait until more data is available.  Note that in this case,
read_eager() may return '' even if there was data on the socket,
because the protocol negotiation may have eaten the data.  This is why
EOFError is needed in some cases to distinguish between "no data" and
"connection closed" (since the socket also appears ready for reading
when it is closed).

Bugs:
- may hang when connection is slow in the middle of an IAC sequence

To do:
- option negotiation
- timeout should be intrinsic to the connection object instead of an
  option on one of the read calls only

"""


# Imported modules
import sys
import time
import socket
import select
import struct
from cStringIO import StringIO

__all__ = ["Telnet"]

# Tunable parameters
DEBUGLEVEL = 0

# Telnet protocol defaults
TELNET_PORT = 23

# Telnet protocol characters (don't change)
IAC  = chr(255) # "Interpret As Command"
DONT = chr(254)
DO   = chr(253)
WONT = chr(252)
WILL = chr(251)
SB   = chr(250)
SE   = chr(240)
theNULL = chr(0)

# Telnet protocol options code (don't change)
# These ones all come from arpa/telnet.h
BINARY = chr(0) # 8-bit data path
ECHO = chr(1) # echo
RCP = chr(2) # prepare to reconnect
SGA = chr(3) # suppress go ahead
NAMS = chr(4) # approximate message size
STATUS = chr(5) # give status
TM = chr(6) # timing mark
RCTE = chr(7) # remote controlled transmission and echo
NAOL = chr(8) # negotiate about output line width
NAOP = chr(9) # negotiate about output page size
NAOCRD = chr(10) # negotiate about CR disposition
NAOHTS = chr(11) # negotiate about horizontal tabstops
NAOHTD = chr(12) # negotiate about horizontal tab disposition
NAOFFD = chr(13) # negotiate about formfeed disposition
NAOVTS = chr(14) # negotiate about vertical tab stops
NAOVTD = chr(15) # negotiate about vertical tab disposition
NAOLFD = chr(16) # negotiate about output LF disposition
XASCII = chr(17) # extended ascii character set
LOGOUT = chr(18) # force logout
BM = chr(19) # byte macro
DET = chr(20) # data entry terminal
SUPDUP = chr(21) # supdup protocol
SUPDUPOUTPUT = chr(22) # supdup output
SNDLOC = chr(23) # send location
TTYPE = chr(24) # terminal type
EOR = chr(25) # end or record
TUID = chr(26) # TACACS user identification
OUTMRK = chr(27) # output marking
TTYLOC = chr(28) # terminal location number
VT3270REGIME = chr(29) # 3270 regime
X3PAD = chr(30) # X.3 PAD
NAWS = chr(31) # window size
TSPEED = chr(32) # terminal speed
LFLOW = chr(33) # remote flow control
LINEMODE = chr(34) # Linemode option
XDISPLOC = chr(35) # X Display Location
OLD_ENVIRON = chr(36) # Old - Environment variables
AUTHENTICATION = chr(37) # Authenticate
ENCRYPT = chr(38) # Encryption option
NEW_ENVIRON = chr(39) # New - Environment variables
# the following ones come from
# http://www.iana.org/assignments/telnet-options
# Unfortunately, that document does not assign identifiers
# to all of them, so we are making them up
TN3270E = chr(40) # TN3270E
XAUTH = chr(41) # XAUTH
CHARSET = chr(42) # CHARSET
RSP = chr(43) # Telnet Remote Serial Port
COM_PORT_OPTION = chr(44) # Com Port Control Option
SUPPRESS_LOCAL_ECHO = chr(45) # Telnet Suppress Local Echo
TLS = chr(46) # Telnet Start TLS
KERMIT = chr(47) # KERMIT
SEND_URL = chr(48) # SEND-URL
FORWARD_X = chr(49) # FORWARD_X
PRAGMA_LOGON = chr(138) # TELOPT PRAGMA LOGON
SSPI_LOGON = chr(139) # TELOPT SSPI LOGON
PRAGMA_HEARTBEAT = chr(140) # TELOPT PRAGMA HEARTBEAT
EXOPL = chr(255) # Extended-Options-List

SEND_TTYPE = chr(1)

class Telnet:
    """Telnet interface class.

    An instance of this class represents a connection to a telnet
    server.  The instance is initially not connected; the open()
    method must be used to establish a connection.  Alternatively, the
    host name and optional port number can be passed to the
    constructor, too.

    Don't try to reopen an already connected instance.

    This class has many read_*() methods.  Note that some of them
    raise EOFError when the end of the connection is read, because
    they can return an empty string for other reasons.  See the
    individual doc strings.

    read_all()
        Read all data until EOF; may block.

    read_some()
        Read at least one byte or EOF; may block.

    read_very_eager()
        Read all data available already queued or on the socket,
        without blocking.

    read_eager()
        Read either data already queued or some data available on the
        socket, without blocking.

    read_lazy()
        Read all data in the raw queue (processing it first), without
        doing any socket I/O.

    read_very_lazy()
        Reads all data in the cooked queue, without doing any socket
        I/O.
    """

    def __init__(self, host=None, port=0, **kwargs):
        """Constructor.

        When called without arguments, create an unconnected instance.
        With a hostname argument, it connects the instance; a port
        number is optional.

        """
        self.debuglevel = DEBUGLEVEL
        self.can_naws = False
        self.host = host
        self.port = port
        self.sock = None
        self.cancel_expect = False
        self.rawq = ''
        self.irawq = 0
        self.cookedq = StringIO()
        self.eof = 0
        self.window_size          = kwargs.get('termsize')
        self.stdout               = kwargs.get('stdout',           sys.stdout)
        self.stderr               = kwargs.get('stderr',           sys.stderr)
        self.termtype             = kwargs.get('termtype',         'dumb')
        self.data_callback        = kwargs.get('receive_callback', None)
        self.data_callback_kwargs = {}
        if host:
            self.open(host, port)

    def open(self, host, port=0):
        """Connect to a host.

        The optional second argument is the port number, which
        defaults to the standard telnet port (23).

        Don't try to reopen an already connected instance.

        """
        self.eof = 0
        if not port:
            port = TELNET_PORT
        self.host = host
        self.port = port
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg

    def msg(self, msg, *args):
        """Print a debug message, when the debug level is > 0.

        If extra arguments are present, they are substituted in the
        message using the standard string formatting operator.

        """
        if self.debuglevel > 0:
            self.stderr.write('Telnet(%s,%d): ' % (self.host, self.port))
            if args:
                self.stderr.write(msg % args)
            else:
                self.stderr.write(msg)
            self.stderr.write('\n')

    def set_debuglevel(self, debuglevel):
        """Set the debug level.

        The higher it is, the more debug output you get (on stdout).

        """
        self.debuglevel = debuglevel

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
        self.sock = 0
        self.eof = 1

    def get_socket(self):
        """Return the socket object used internally."""
        return self.sock

    def fileno(self):
        """Return the fileno() of the socket object used internally."""
        return self.sock.fileno()

    def write(self, buffer):
        """Write a string to the socket, doubling any IAC characters.

        Can block if the connection is blocked.  May raise
        socket.error if the connection is closed.

        """
        if type(buffer) == type(0):
            buffer = chr(buffer)
        elif isinstance(buffer, str) and IAC in buffer:
            buffer = buffer.replace(IAC, IAC+IAC)
        self.msg("send %s", `buffer`)
        self.sock.send(buffer)

    def read_all(self):
        """Read all data until EOF; block until connection closed."""
        self.process_rawq()
        while not self.eof:
            self.fill_rawq()
            self.process_rawq()
        buf = self.cookedq.getvalue()
        self.cookedq.seek(0)
        self.cookedq.truncate()
        return buf

    def read_some(self):
        """Read at least one byte of cooked data unless EOF is hit.

        Return '' if EOF is hit.  Block if no data is immediately
        available.

        """
        self.process_rawq()
        while self.cookedq.tell() == 0 and not self.eof:
            self.fill_rawq()
            self.process_rawq()
        buf = self.cookedq.getvalue()
        self.cookedq.seek(0)
        self.cookedq.truncate()
        return buf

    def read_very_eager(self):
        """Read everything that's possible without blocking in I/O (eager).

        Raise EOFError if connection closed and no cooked data
        available.  Return '' if no cooked data available otherwise.
        Don't block unless in the midst of an IAC sequence.

        """
        self.process_rawq()
        while not self.eof and self.sock_avail():
            self.fill_rawq()
            self.process_rawq()
        return self.read_very_lazy()

    def read_eager(self):
        """Read readily available data.

        Raise EOFError if connection closed and no cooked data
        available.  Return '' if no cooked data available otherwise.
        Don't block unless in the midst of an IAC sequence.

        """
        self.process_rawq()
        while self.cookedq.tell() == 0 and not self.eof and self.sock_avail():
            self.fill_rawq()
            self.process_rawq()
        return self.read_very_lazy()

    def read_lazy(self):
        """Process and return data that's already in the queues (lazy).

        Raise EOFError if connection closed and no data available.
        Return '' if no cooked data available otherwise.  Don't block
        unless in the midst of an IAC sequence.

        """
        self.process_rawq()
        return self.read_very_lazy()

    def read_very_lazy(self):
        """Return any data available in the cooked queue (very lazy).

        Raise EOFError if connection closed and no data available.
        Return '' if no cooked data available otherwise.  Don't block.

        """
        buf = self.cookedq.getvalue()
        self.cookedq.seek(0)
        self.cookedq.truncate()
        if not buf and self.eof and not self.rawq:
            raise EOFError, 'telnet connection closed'
        return buf

    def set_receive_callback(self, callback, *args, **kwargs):
        """The callback function called after each receipt of any data."""
        self.data_callback        = callback
        self.data_callback_kwargs = kwargs

    def set_window_size(self, rows, cols):
        """
        Change the size of the terminal window, if the remote end supports
        NAWS. If it doesn't, the method returns silently.
        """
        if not self.can_naws:
            return
        self.window_size = rows, cols
        size = struct.pack('!HH', cols, rows)
        self.sock.send(IAC + SB + NAWS + size + IAC + SE)

    def process_rawq(self):
        """Transfer from raw queue to cooked queue.

        Set self.eof when connection is closed.  Don't block unless in
        the midst of an IAC sequence.
        """
        buf = ''
        try:
            while self.rawq:
                # Handle non-IAC first (normal data).
                char = self.rawq_getchar()
                if char != IAC:
                    buf = buf + char
                    continue

                # Interpret the command byte that follows after the IAC code.
                command = self.rawq_getchar()
                if command == theNULL:
                    self.msg('IAC NOP')
                    continue
                elif command == IAC:
                    self.msg('IAC DATA')
                    buf = buf + command
                    continue

                # DO: Indicates the request that the other party perform,
                # or confirmation that you are expecting the other party
                # to perform, the indicated option.
                elif command == DO:
                    opt = self.rawq_getchar()
                    self.msg('IAC DO %s', ord(opt))
                    if opt == TTYPE:
                        self.sock.send(IAC + WILL + opt)
                    elif opt == NAWS:
                        self.sock.send(IAC + WILL + opt)
                        self.can_naws = True
                        if self.window_size:
                            self.set_window_size(*self.window_size)
                    else:
                        self.sock.send(IAC + WONT + opt)

                # DON'T: Indicates the demand that the other party stop
                # performing, or confirmation that you are no longer
                # expecting the other party to perform, the indicated
                # option.
                elif command == DONT:
                    opt = self.rawq_getchar()
                    self.msg('IAC DONT %s', ord(opt))
                    self.sock.send(IAC + WONT + opt)

                # SB: Indicates that what follows is subnegotiation of the
                # indicated option.
                elif command == SB:
                    opt = self.rawq_getchar()
                    self.msg('IAC SUBCOMMAND %d', ord(opt))

                    # We only handle the TTYPE command, so skip all other
                    # commands.
                    if opt != TTYPE:
                        while self.rawq_getchar() != SE:
                            pass
                        continue

                    # We also only handle the SEND_TTYPE option of TTYPE,
                    # so skip everything else.
                    subopt = self.rawq_getchar()
                    if subopt != SEND_TTYPE:
                        while self.rawq_getchar() != SE:
                            pass
                        continue

                    # Mandatory end of the IAC subcommand.
                    iac = self.rawq_getchar()
                    end = self.rawq_getchar()
                    if (iac, end) != (IAC, SE):
                        # whoops, that's an unexpected response...
                        self.msg('expected IAC SE, but got %d %d', ord(iac), ord(end))
                    self.msg('IAC SUBCOMMAND_END')

                    # Send the next supported terminal.
                    ttype = self.termtype
                    self.msg('indicating support for terminal type %s', ttype)
                    self.sock.send(IAC + SB + TTYPE + theNULL + ttype + IAC + SE)
                elif command in (WILL, WONT):
                    opt = self.rawq_getchar()
                    self.msg('IAC %s %d',
                             command == WILL and 'WILL' or 'WONT', ord(opt))
                    if opt == ECHO:
                        self.sock.send(IAC + DO + opt)
                    else:
                        self.sock.send(IAC + DONT + opt)
                else:
                    self.msg('IAC %d not recognized' % ord(command))
        except EOFError: # raised by self.rawq_getchar()
            pass
        self.cookedq.write(buf)
        if self.data_callback is not None:
            self.data_callback(buf, **self.data_callback_kwargs)

    def rawq_getchar(self):
        """Get next char from raw queue.

        Block if no data is immediately available.  Raise EOFError
        when connection is closed.

        """
        if not self.rawq:
            self.fill_rawq()
            if self.eof:
                raise EOFError
        c = self.rawq[self.irawq]
        self.irawq = self.irawq + 1
        if self.irawq >= len(self.rawq):
            self.rawq = ''
            self.irawq = 0
        return c

    def fill_rawq(self):
        """Fill raw queue from exactly one recv() system call.

        Block if no data is immediately available.  Set self.eof when
        connection is closed.

        """
        if self.irawq >= len(self.rawq):
            self.rawq = ''
            self.irawq = 0
        # The buffer size should be fairly small so as to avoid quadratic
        # behavior in process_rawq() above.
        buf = self.sock.recv(64)
        self.msg("recv %s", `buf`)
        self.eof = (not buf)
        self.rawq = self.rawq + buf

    def sock_avail(self):
        """Test whether data is available on the socket."""
        return select.select([self], [], [], 0) == ([self], [], [])

    def interact(self):
        """Interaction function, emulates a very dumb telnet client."""
        if sys.platform == "win32":
            self.mt_interact()
            return
        while 1:
            rfd, wfd, xfd = select.select([self, sys.stdin], [], [])
            if self in rfd:
                try:
                    text = self.read_eager()
                except EOFError:
                    print '*** Connection closed by remote host ***'
                    break
                if text:
                    self.stdout.write(text)
                    self.stdout.flush()
            if sys.stdin in rfd:
                line = sys.stdin.readline()
                if not line:
                    break
                self.write(line)

    def mt_interact(self):
        """Multithreaded version of interact()."""
        import thread
        thread.start_new_thread(self.listener, ())
        while 1:
            line = sys.stdin.readline()
            if not line:
                break
            self.write(line)

    def listener(self):
        """Helper for mt_interact() -- this executes in the other thread."""
        while 1:
            try:
                data = self.read_eager()
            except EOFError:
                print '*** Connection closed by remote host ***'
                return
            if data:
                self.stdout.write(data)
            else:
                self.stdout.flush()

    def _wait_for_data(self, timeout):
        end = time.time() + timeout
        while True:
            readable, writeable, excp = select.select([self.sock], [], [], 1)
            if readable:
                return True
            if time.time() > end:
                return False

    def _waitfor(self, list, timeout=None, flush=False, cleanup=None):
        re = None
        list = list[:]
        indices = range(len(list))
        search_window_size = 150
        head_loockback_size = 10
        for i in indices:
            if not hasattr(list[i], "search"):
                if not re: import re
                list[i] = re.compile(list[i])
        self.msg("Expecting %s" % [l.pattern for l in list])
        incomplete_tail = ''
        clean_sw_size = search_window_size
        while 1:
            self.process_rawq()
            if self.cancel_expect:
                self.cancel_expect = False
                self.msg('cancelling expect()')
                return -2, None, ''
            qlen = self.cookedq.tell()
            if cleanup:
                while 1:
                    self.cookedq.seek(qlen - clean_sw_size - len(incomplete_tail) - head_loockback_size)
                    search_window = self.cookedq.read()
                    search_window, incomplete_tail = cleanup(search_window)
                    if clean_sw_size > qlen or len(search_window) >= search_window_size:
                        search_window = search_window[-search_window_size:]
                        if len(search_window) > search_window_size:
                            clean_sw_size = clean_sw_size - search_window_size
                        break
                    else:
                        clean_sw_size = clean_sw_size + search_window_size
            else:
                self.cookedq.seek(qlen - search_window_size)
                search_window = self.cookedq.read()
            for i in indices:
                m = list[i].search(search_window)
                if m is not None:
                    e    = len(m.group())
                    e    = qlen - e + 1
                    self.cookedq.seek(0)
                    text = self.cookedq.read(e)
                    if flush:
                        self.cookedq.seek(0)
                        self.cookedq.truncate()
                        self.cookedq.write(search_window[m.end():])
                    else:
                        self.cookedq.seek(qlen)
                    return i, m, text
            if self.eof:
                break
            if timeout is not None:
                if not self._wait_for_data(timeout): # Workaround for the problem with select() below.
                    break
                # The following will sometimes lock even if data is available
                # and I have no idea why. Do NOT reverse this unless you are sure
                # that you found the reason. The error is rare, but it does happen.
                #r, w, x = select.select([self.sock], [], [], timeout)
                #if not r:
                #    break
            self.fill_rawq()
        text = self.read_very_lazy()
        if not text and self.eof:
            raise EOFError
        return -1, None, text

    def waitfor(self, list, timeout=None, cleanup=None):
        """Read until one from a list of a regular expressions matches.

        The first argument is a list of regular expressions, either
        compiled (re.RegexObject instances) or uncompiled (strings).
        The optional second argument is a timeout, in seconds; default
        is no timeout.

        Return a tuple of three items: the index in the list of the
        first regular expression that matches; the match object
        returned; and the text read up till and including the match.

        If EOF is read and no text was read, raise EOFError.
        Otherwise, when nothing matches, return (-1, None, text) where
        text is the text received so far (may be the empty string if a
        timeout happened).

        If a regular expression ends with a greedy match (e.g. '.*')
        or if more than one expression can match the same input, the
        results are undeterministic, and may depend on the I/O timing.
        """
        return self._waitfor(list, timeout, False, cleanup)

    def expect(self, list, timeout=None, cleanup=None):
        """
        Like waitfor(), but removes the matched data from the incoming
        buffer.
        """
        return self._waitfor(list, timeout, True, cleanup = cleanup)


def test():
    """Test program for telnetlib.

    Usage: python telnetlib.py [-d] ... [host [port]]

    Default host is localhost; default port is 23.

    """
    debuglevel = 0
    while sys.argv[1:] and sys.argv[1] == '-d':
        debuglevel = debuglevel+1
        del sys.argv[1]
    host = 'localhost'
    if sys.argv[1:]:
        host = sys.argv[1]
    port = 0
    if sys.argv[2:]:
        portstr = sys.argv[2]
        try:
            port = int(portstr)
        except ValueError:
            port = socket.getservbyname(portstr, 'tcp')
    tn = Telnet()
    tn.set_debuglevel(debuglevel)
    tn.open(host, port)
    tn.interact()
    tn.close()

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = Queue
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
The heart of Exscript.
"""
import sys
import os
import gc
import select
import threading
import weakref
from functools import partial
from multiprocessing import Pipe
from Exscript.Logger import logger_registry
from Exscript.LoggerProxy import LoggerProxy
from Exscript.util.cast import to_hosts
from Exscript.util.tty import get_terminal_size
from Exscript.util.impl import format_exception, serializeable_sys_exc_info
from Exscript.util.decorator import get_label
from Exscript.AccountManager import AccountManager
from Exscript.workqueue import WorkQueue, Task
from Exscript.AccountProxy import AccountProxy
from Exscript.protocols import prepare

def _account_factory(accm, host, account):
    if account is None:
        account = host.get_account()

    # Specific account requested?
    if account:
        acquired = AccountProxy.for_account_hash(accm, account.__hash__())
    else:
        acquired = AccountProxy.for_host(accm, host)

    # Thread-local accounts don't need a remote proxy.
    if acquired:
        return acquired
    account.acquire()
    return account

def _prepare_connection(func):
    """
    A decorator that unpacks the host and connection from the job argument
    and passes them as separate arguments to the wrapped function.
    """
    def _wrapped(job, *args, **kwargs):
        job_id    = id(job)
        to_parent = job.data['pipe']
        host      = job.data['host']

        # Create a protocol adapter.
        mkaccount = partial(_account_factory, to_parent, host)
        pargs     = {'account_factory': mkaccount,
                     'stdout':          job.data['stdout']}
        pargs.update(host.get_options())
        conn = prepare(host, **pargs)

        # Connect and run the function.
        log_options = get_label(func, 'log_to')
        if log_options is not None:
            # Enable logging.
            proxy  = LoggerProxy(to_parent, log_options['logger_id'])
            log_cb = partial(proxy.log, job_id)
            proxy.add_log(job_id, job.name, job.failures + 1)
            conn.data_received_event.listen(log_cb)
            try:
                conn.connect(host.get_address(), host.get_tcp_port())
                result = func(job, host, conn, *args, **kwargs)
                conn.close(force = True)
            except:
                proxy.log_aborted(job_id, serializeable_sys_exc_info())
                raise
            else:
                proxy.log_succeeded(job_id)
            finally:
                conn.data_received_event.disconnect(log_cb)
        else:
            conn.connect(host.get_address(), host.get_tcp_port())
            result = func(job, host, conn, *args, **kwargs)
            conn.close(force = True)
        return result

    return _wrapped

def _is_recoverable_error(cls):
    # Hack: We can't use isinstance(), because the classes may
    # have been created by another python process; apparently this
    # will cause isinstance() to return False.
    return cls.__name__ in ('CompileError', 'FailException')

def _call_logger(funcname, logger_id, *args):
    logger = logger_registry.get(logger_id)
    if not logger:
        return
    return getattr(logger, funcname)(*args)

class _PipeHandler(threading.Thread):
    """
    Each PipeHandler holds an open pipe to a subprocess, to allow the
    sub-process to access the accounts and communicate status information.
    """
    def __init__(self, account_manager):
        threading.Thread.__init__(self)
        self.daemon = True
        self.accm   = account_manager
        self.to_child, self.to_parent = Pipe()

    def _send_account(self, account):
        if account is None:
            self.to_child.send(account)
            return
        response = (account.__hash__(),
                    account.get_name(),
                    account.get_password(),
                    account.get_authorization_password(),
                    account.get_key())
        self.to_child.send(response)

    def _handle_request(self, request):
        try:
            command, arg = request
            if command == 'acquire-account-for-host':
                account = self.accm.acquire_account_for(arg, self)
                self._send_account(account)
            elif command == 'acquire-account-from-hash':
                account = self.accm.get_account_from_hash(arg)
                if account is not None:
                    account = self.accm.acquire_account(account, self)
                self._send_account(account)
            elif command == 'acquire-account':
                account = self.accm.acquire_account(owner = self)
                self._send_account(account)
            elif command == 'release-account':
                account = self.accm.get_account_from_hash(arg)
                account.release()
                self.to_child.send('ok')
            elif command == 'log-add':
                log = _call_logger('add_log', *arg)
                self.to_child.send(log)
            elif command == 'log-message':
                _call_logger('log', *arg)
            elif command == 'log-aborted':
                _call_logger('log_aborted', *arg)
            elif command == 'log-succeeded':
                _call_logger('log_succeeded', *arg)
            else:
                raise Exception('invalid command on pipe: ' + repr(command))
        except Exception, e:
            self.to_child.send(e)
            raise

    def run(self):
        while True:
            try:
                request = self.to_child.recv()
            except (EOFError, IOError):
                self.accm.release_accounts(self)
                break
            self._handle_request(request)

class Queue(object):
    """
    Manages hosts/tasks, accounts, connections, and threads.
    """

    def __init__(self,
                 domain      = '',
                 verbose     = 1,
                 mode        = 'threading',
                 max_threads = 1,
                 stdout      = sys.stdout,
                 stderr      = sys.stderr):
        """
        Constructor. All arguments should be passed as keyword arguments.
        Depending on the verbosity level, the following types
        of output are written to stdout/stderr (or to whatever else is
        passed in the stdout/stderr arguments):

          - S = status bar
          - L = live conversation
          - D = debug messages
          - E = errors
          - ! = errors with tracebacks
          - F = fatal errors with tracebacks

        The output types are mapped depending on the verbosity as follows:

          - verbose = -1: stdout = None, stderr = F
          - verbose =  0: stdout = None, stderr = EF
          - verbose =  1, max_threads = 1: stdout = L, stderr = EF
          - verbose =  1, max_threads = n: stdout = S, stderr = EF
          - verbose >=  2, max_threads = 1: stdout = DL, stderr = !F
          - verbose >=  2, max_threads = n: stdout = DS, stderr = !F

        @type  domain: str
        @param domain: The default domain of the contacted hosts.
        @type  verbose: int
        @param verbose: The verbosity level.
        @type  mode: str
        @param mode: 'multiprocessing' or 'threading'
        @type  max_threads: int
        @param max_threads: The maximum number of concurrent threads.
        @type  stdout: file
        @param stdout: The output channel, defaults to sys.stdout.
        @type  stderr: file
        @param stderr: The error channel, defaults to sys.stderr.
        """
        self.workqueue         = WorkQueue(mode = mode)
        self.account_manager   = AccountManager()
        self.pipe_handlers     = weakref.WeakValueDictionary()
        self.domain            = domain
        self.verbose           = verbose
        self.stdout            = stdout
        self.stderr            = stderr
        self.devnull           = open(os.devnull, 'w')
        self.channel_map       = {'fatal_errors': self.stderr,
                                  'debug':        self.stdout}
        self.completed         = 0
        self.total             = 0
        self.failed            = 0
        self.status_bar_length = 0
        self.set_max_threads(max_threads)

        # Listen to what the workqueue is doing.
        self.workqueue.job_init_event.listen(self._on_job_init)
        self.workqueue.job_started_event.listen(self._on_job_started)
        self.workqueue.job_error_event.listen(self._on_job_error)
        self.workqueue.job_succeeded_event.listen(self._on_job_succeeded)
        self.workqueue.job_aborted_event.listen(self._on_job_aborted)

    def _update_verbosity(self):
        if self.verbose < 0:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.devnull
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 0:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 1 and self.get_max_threads() == 1:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.stdout
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose == 1:
            self.channel_map['status_bar'] = self.stdout
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.devnull
        elif self.verbose >= 2 and self.get_max_threads() == 1:
            self.channel_map['status_bar'] = self.devnull
            self.channel_map['connection'] = self.stdout
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.stderr
        elif self.verbose >= 2:
            self.channel_map['status_bar'] = self.stdout
            self.channel_map['connection'] = self.devnull
            self.channel_map['errors']     = self.stderr
            self.channel_map['tracebacks'] = self.stderr

    def _write(self, channel, msg):
        self.channel_map[channel].write(msg)
        self.channel_map[channel].flush()

    def _create_pipe(self):
        """
        Creates a new pipe and returns the child end of the connection.
        To request an account from the pipe, use::

            pipe = queue._create_pipe()

            # Let the account manager choose an account.
            pipe.send(('acquire-account-for-host', host))
            account = pipe.recv()
            ...
            pipe.send(('release-account', account.id()))

            # Or acquire a specific account.
            pipe.send(('acquire-account', account.id()))
            account = pipe.recv()
            ...
            pipe.send(('release-account', account.id()))

            pipe.close()
        """
        child = _PipeHandler(self.account_manager)
        self.pipe_handlers[id(child)] = child
        child.start()
        return child.to_parent

    def _del_status_bar(self):
        if self.status_bar_length == 0:
            return
        self._write('status_bar', '\b \b' * self.status_bar_length)
        self.status_bar_length = 0

    def get_progress(self):
        """
        Returns the progress in percent.

        @rtype:  float
        @return: The progress in percent.
        """
        if self.total == 0:
            return 0.0
        return 100.0 / self.total * self.completed

    def _print_status_bar(self, exclude = None):
        if self.total == 0:
            return
        percent  = 100.0 / self.total * self.completed
        progress = '%d/%d (%d%%)' % (self.completed, self.total, percent)
        jobs     = self.workqueue.get_running_jobs()
        running  = '|'.join([j.name for j in jobs if j.name != exclude])
        if not running:
            self.status_bar_length = 0
            return
        rows, cols = get_terminal_size()
        text       = 'In progress: [%s] %s' % (running, progress)
        overflow   = len(text) - cols
        if overflow > 0:
            cont      = '...'
            overflow += len(cont) + 1
            strlen    = len(running)
            partlen   = (strlen / 2) - (overflow / 2)
            head      = running[:partlen]
            tail      = running[-partlen:]
            running   = head + cont + tail
            text      = 'In progress: [%s] %s' % (running, progress)
        self._write('status_bar', text)
        self.status_bar_length = len(text)

    def _print(self, channel, msg):
        self._del_status_bar()
        self._write(channel, msg + '\n')
        self._print_status_bar()

    def _dbg(self, level, msg):
        if level > self.verbose:
            return
        self._print('debug', msg)

    def _on_job_init(self, job):
        if job.data is None:
            job.data = {}
        job.data['pipe']   = self._create_pipe()
        job.data['stdout'] = self.channel_map['connection']

    def _on_job_destroy(self, job):
        job.data['pipe'].close()

    def _on_job_started(self, job):
        self._del_status_bar()
        self._print_status_bar()

    def _on_job_error(self, job, exc_info):
        msg   = job.name + ' error: ' + str(exc_info[1])
        trace = ''.join(format_exception(*exc_info))
        self._print('errors', msg)
        if _is_recoverable_error(exc_info[0]):
            self._print('tracebacks', trace)
        else:
            self._print('fatal_errors', trace)

    def _on_job_succeeded(self, job):
        self._on_job_destroy(job)
        self.completed += 1
        self._print('status_bar', job.name + ' succeeded.')
        self._dbg(2, job.name + ' job is done.')
        self._del_status_bar()
        self._print_status_bar(exclude = job.name)

    def _on_job_aborted(self, job):
        self._on_job_destroy(job)
        self.completed += 1
        self.failed    += 1
        self._print('errors', job.name + ' finally failed.')
        self._del_status_bar()
        self._print_status_bar(exclude = job.name)

    def set_max_threads(self, n_connections):
        """
        Sets the maximum number of concurrent connections.

        @type  n_connections: int
        @param n_connections: The maximum number of connections.
        """
        self.workqueue.set_max_threads(n_connections)
        self._update_verbosity()

    def get_max_threads(self):
        """
        Returns the maximum number of concurrent threads.

        @rtype:  int
        @return: The maximum number of connections.
        """
        return self.workqueue.get_max_threads()

    def add_account_pool(self, pool, match = None):
        """
        Adds a new account pool. If the given match argument is
        None, the pool the default pool. Otherwise, the match argument is
        a callback function that is invoked to decide whether or not the
        given pool should be used for a host.

        When Exscript logs into a host, the account is chosen in the following
        order:

            # Exscript checks whether an account was attached to the
            L{Host} object using L{Host.set_account()}), and uses that.

            # If the L{Host} has no account attached, Exscript walks
            through all pools that were passed to L{Queue.add_account_pool()}.
            For each pool, it passes the L{Host} to the function in the
            given match argument. If the return value is True, the account
            pool is used to acquire an account.
            (Accounts within each pool are taken in a round-robin
            fashion.)

            # If no matching account pool is found, an account is taken
            from the default account pool.

            # Finally, if all that fails and the default account pool
            contains no accounts, an error is raised.

        Example usage::

            def do_nothing(conn):
                conn.autoinit()

            def use_this_pool(host):
                return host.get_name().startswith('foo')

            default_pool = AccountPool()
            default_pool.add_account(Account('default-user', 'password'))

            other_pool = AccountPool()
            other_pool.add_account(Account('user', 'password'))

            queue = Queue()
            queue.add_account_pool(default_pool)
            queue.add_account_pool(other_pool, use_this_pool)

            host = Host('localhost')
            queue.run(host, do_nothing)

        In the example code, the host has no account attached. As a result,
        the queue checks whether use_this_pool() returns True. Because the
        hostname does not start with 'foo', the function returns False, and
        Exscript takes the 'default-user' account from the default pool.

        @type  pool: AccountPool
        @param pool: The account pool that is added.
        @type  match: callable
        @param match: A callback to check if the pool should be used.
        """
        self.account_manager.add_pool(pool, match)

    def add_account(self, account):
        """
        Adds the given account to the default account pool that Exscript uses
        to log into all hosts that have no specific L{Account} attached.

        @type  account: Account
        @param account: The account that is added.
        """
        self.account_manager.add_account(account)

    def is_completed(self):
        """
        Returns True if the task is completed, False otherwise.
        In other words, this methods returns True if the queue is empty.

        @rtype:  bool
        @return: Whether all tasks are completed.
        """
        return self.workqueue.get_length() == 0

    def join(self):
        """
        Waits until all jobs are completed.
        """
        self._dbg(2, 'Waiting for the queue to finish.')
        self.workqueue.wait_until_done()
        for child in self.pipe_handlers.values():
            child.join()
        self._del_status_bar()
        self._print_status_bar()
        gc.collect()

    def shutdown(self, force = False):
        """
        Stop executing any further jobs. If the force argument is True,
        the function does not wait until any queued jobs are completed but
        stops immediately.

        After emptying the queue it is restarted, so you may still call run()
        after using this method.

        @type  force: bool
        @param force: Whether to wait until all jobs were processed.
        """
        if not force:
            self.join()

        self._dbg(2, 'Shutting down queue...')
        self.workqueue.shutdown(True)
        self._dbg(2, 'Queue shut down.')
        self._del_status_bar()

    def destroy(self, force = False):
        """
        Like shutdown(), but also removes all accounts, hosts, etc., and
        does not restart the queue. In other words, the queue can no longer
        be used after calling this method.

        @type  force: bool
        @param force: Whether to wait until all jobs were processed.
        """
        try:
            if not force:
                self.join()
        finally:
            self._dbg(2, 'Destroying queue...')
            self.workqueue.destroy()
            self.account_manager.reset()
            self.completed         = 0
            self.total             = 0
            self.failed            = 0
            self.status_bar_length = 0
            self._dbg(2, 'Queue destroyed.')
            self._del_status_bar()

    def reset(self):
        """
        Remove all accounts, hosts, etc.
        """
        self._dbg(2, 'Resetting queue...')
        self.account_manager.reset()
        self.workqueue.shutdown(True)
        self.completed         = 0
        self.total             = 0
        self.failed            = 0
        self.status_bar_length = 0
        self._dbg(2, 'Queue reset.')
        self._del_status_bar()

    def _run(self, hosts, callback, queue_function, *args):
        hosts       = to_hosts(hosts, default_domain = self.domain)
        self.total += len(hosts)
        callback    = _prepare_connection(callback)
        task        = Task(self.workqueue)
        for host in hosts:
            name   = host.get_name()
            data   = {'host': host}
            job_id = queue_function(callback, name, *args, data = data)
            if job_id is not None:
                task.add_job_id(job_id)

        if task.is_completed():
            self._dbg(2, 'No jobs enqueued.')
            return None

        self._dbg(2, 'All jobs enqueued.')
        return task

    def run(self, hosts, function, attempts = 1):
        """
        Add the given function to a queue, and call it once for each host
        according to the threading options.
        Use decorators.bind() if you also want to pass additional
        arguments to the callback function.

        Returns an object that represents the queued task, and that may be
        passed to is_completed() to check the status.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @type  attempts: int
        @param attempts: The number of attempts on failure.
        @rtype:  object
        @return: An object representing the task.
        """
        return self._run(hosts, function, self.workqueue.enqueue, attempts)

    def run_or_ignore(self, hosts, function, attempts = 1):
        """
        Like run(), but only appends hosts that are not already in the
        queue.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @type  attempts: int
        @param attempts: The number of attempts on failure.
        @rtype:  object
        @return: A task object, or None if all hosts were duplicates.
        """
        return self._run(hosts,
                         function,
                         self.workqueue.enqueue_or_ignore,
                         attempts)

    def priority_run(self, hosts, function, attempts = 1):
        """
        Like run(), but adds the task to the front of the queue.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @type  attempts: int
        @param attempts: The number of attempts on failure.
        @rtype:  object
        @return: An object representing the task.
        """
        return self._run(hosts,
                         function,
                         self.workqueue.priority_enqueue,
                         False,
                         attempts)

    def priority_run_or_raise(self, hosts, function, attempts = 1):
        """
        Like priority_run(), but if a host is already in the queue, the
        existing host is moved to the top of the queue instead of enqueuing
        the new one.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @type  attempts: int
        @param attempts: The number of attempts on failure.
        @rtype:  object
        @return: A task object, or None if all hosts were duplicates.
        """
        return self._run(hosts,
                         function,
                         self.workqueue.priority_enqueue_or_raise,
                         False,
                         attempts)

    def force_run(self, hosts, function, attempts = 1):
        """
        Like priority_run(), but starts the task immediately even if that
        max_threads is exceeded.

        @type  hosts: string|list(string)|Host|list(Host)
        @param hosts: A hostname or Host object, or a list of them.
        @type  function: function
        @param function: The function to execute.
        @type  attempts: int
        @param attempts: The number of attempts on failure.
        @rtype:  object
        @return: An object representing the task.
        """
        return self._run(hosts,
                         function,
                         self.workqueue.priority_enqueue,
                         True,
                         attempts)

    def enqueue(self, function, name = None, attempts = 1):
        """
        Places the given function in the queue and calls it as soon
        as a thread is available. To pass additional arguments to the
        callback, use Python's functools.partial().

        @type  function: function
        @param function: The function to execute.
        @type  name: string
        @param name: A name for the task.
        @type  attempts: int
        @param attempts: The number of attempts on failure.
        @rtype:  object
        @return: An object representing the task.
        """
        self.total += 1
        task   = Task(self.workqueue)
        job_id = self.workqueue.enqueue(function, name, attempts)
        if job_id is not None:
            task.add_job_id(job_id)
        self._dbg(2, 'Function enqueued.')
        return task

########NEW FILE########
__FILENAME__ = HTTPd
# Copyright (C) 2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A threaded HTTP server with support for HTTP/Digest authentication.
"""
import sys
import time
import urllib
from urlparse import urlparse
from traceback import format_exc
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

if sys.version_info < (2, 5):
    import md5
    def md5hex(x):
        return md5.md5(x).hexdigest()
else:
    import hashlib
    def md5hex(x):
        return hashlib.md5(x).hexdigest()

if sys.version_info < (2, 6):
    from cgi import parse_qs
else:
    from urlparse import parse_qs

# Selective imports only for urllib2 because 2to3 will not replace the
# urllib2.<method> calls below. Also, 2to3 will throw an error if we
# try to do a from _ import _.
if sys.version_info[0] < 3:
    import urllib2
    parse_http_list = urllib2.parse_http_list
    parse_keqv_list = urllib2.parse_keqv_list
else:
    from urllib.request import parse_http_list, parse_keqv_list

default_realm = 'exscript'

# This is convoluted because there's no way to tell 2to3 to insert a
# byte literal.
_HEADER_NEWLINES = [x.encode('ascii') for x in (u'\r\n', u'\n', u'')]

def _parse_url(path):
    """Given a urlencoded path, returns the path and the dictionary of
    query arguments, all in Unicode."""

    # path changes from bytes to Unicode in going from Python 2 to
    # Python 3.
    if sys.version_info[0] < 3:
        o = urlparse(urllib.unquote_plus(path).decode('utf8'))
    else:
        o = urlparse(urllib.unquote_plus(path))

    path = o.path
    args = {}

    # Convert parse_qs' str --> [str] dictionary to a str --> str
    # dictionary since we never use multi-value GET arguments
    # anyway.
    multiargs = parse_qs(o.query, keep_blank_values=True)
    for arg, value in multiargs.items():
        args[arg] = value[0]

    return path, args

def _error_401(handler, msg):
    handler.send_response(401)
    realm = handler.server.realm
    nonce = (u"%d:%s" % (time.time(), realm)).encode('utf8')
    handler.send_header('WWW-Authenticate',
                        'Digest realm="%s",'
                        'qop="auth",'
                        'algorithm="MD5",'
                        'nonce="%s"' % (realm, nonce))
    handler.end_headers()
    handler.rfile.read()
    handler.rfile.close()
    handler.wfile.write(msg.encode('utf8'))
    handler.wfile.close()

def _require_authenticate(func):
    '''A decorator to add digest authorization checks to HTTP Request Handlers'''

    def wrapped(self):
        if not hasattr(self, 'authenticated'):
            self.authenticated = None
        if self.authenticated:
            return func(self)

        auth = self.headers.get(u'Authorization')
        if auth is None:
            msg = u"You are not allowed to access this page. Please login first!"
            return _error_401(self, msg)

        token, fields = auth.split(' ', 1)
        if token != 'Digest':
            return _error_401(self, 'Unsupported authentication type')

        # Check the header fields of the request.
        cred = parse_http_list(fields)
        cred = parse_keqv_list(cred)
        keys = u'realm', u'username', u'nonce', u'uri', u'response'
        if not all(cred.get(key) for key in keys):
            return _error_401(self, 'Incomplete authentication header')
        if cred['realm'] != self.server.realm:
            return _error_401(self, 'Incorrect realm')
        if 'qop' in cred and ('nc' not in cred or 'cnonce' not in cred):
            return _error_401(self, 'qop with missing nc or cnonce')

        # Check the username.
        username = cred['username']
        password = self.server.get_password(username)
        if not username or password is None:
            return _error_401(self, 'Invalid username or password')

        # Check the digest string.
        location = u'%s:%s' % (self.command, self.path)
        location = md5hex(location.encode('utf8'))
        pwhash   = md5hex('%s:%s:%s' % (username, self.server.realm, password))

        if 'qop' in cred:
            info = (cred['nonce'],
                    cred['nc'],
                    cred['cnonce'],
                    cred['qop'],
                    location)
        else:
            info = cred['nonce'], location

        expect = u'%s:%s' % (pwhash, ':'.join(info))
        expect = md5hex(expect.encode('utf8'))
        if expect != cred['response']:
            return _error_401(self, 'Invalid username or password')

        # Success!
        self.authenticated = True
        return func(self)

    return wrapped

class HTTPd(ThreadingMixIn, HTTPServer):
    """
    An HTTP server, derived from Python's HTTPServer but with added
    support for HTTP/Digest. Usage::

        from Exscript.servers import HTTPd, RequestHandler
        class MyHandler(RequestHandler):
            def handle_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write('You opened ' + self.path)

        server = HTTPd(('', 8080), MyHandler)
        server.add_account('testuser', 'testpassword')
        print 'started httpserver...'
        server.serve_forever()
    """
    daemon_threads = True

    def __init__(self, addr, handler_cls, user_data = None):
        """
        Constructor.

        @type  address: (str, int)
        @param address: The address and port number on which to bind.
        @type  handler_cls: L{RequestHandler}
        @param handler_cls: The RequestHandler to use.
        @type  user_data: object
        @param user_data: Optional data that, stored in self.user_data.
        """
        self.debug     = False
        self.realm     = default_realm
        self.accounts  = {}
        self.user_data = user_data
        HTTPServer.__init__(self, addr, handler_cls)

    def add_account(self, username, password):
        """
        Adds a username/password pair that HTTP clients may use to log in.

        @type  username: str
        @param username: The name of the user.
        @type  password: str
        @param password: The user's password.
        """
        self.accounts[username] = password

    def get_password(self, username):
        """
        Returns the password of the user with the given name.

        @type  username: str
        @param username: The name of the user.
        """
        return self.accounts.get(username)

    def _dbg(self, msg):
        if self.debug:
            print(msg)

class RequestHandler(BaseHTTPRequestHandler):
    """
    A drop-in replacement for Python's BaseHTTPRequestHandler that
    handles HTTP/Digest.
    """

    def _do_POSTGET(self, handler):
        """handle an HTTP request"""
        # at first, assume that the given path is the actual path and there are no arguments
        self.server._dbg(self.path)

        self.path, self.args = _parse_url(self.path)

        # Extract POST data, if any. Clumsy syntax due to Python 2 and
        # 2to3's lack of a byte literal.
        self.data = u"".encode()
        length = self.headers.get('Content-Length')
        if length and length.isdigit():
            self.data = self.rfile.read(int(length))

        # POST data gets automatically decoded into Unicode. The bytestring
        # will still be available in the bdata attribute.
        self.bdata = self.data
        try:
            self.data = self.data.decode('utf8')
        except UnicodeDecodeError:
            self.data = None

        # Run the handler.
        try:
            handler()
        except:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(format_exc().encode('utf8'))

    @_require_authenticate
    def do_POST(self):
        """
        Do not overwrite; instead, overwrite handle_POST().
        """
        self._do_POSTGET(self.handle_POST)

    @_require_authenticate
    def do_GET(self):
        """
        Do not overwrite; instead, overwrite handle_GET().
        """
        self._do_POSTGET(self.handle_GET)

    def handle_POST(self):
        """
        Overwrite this method to handle a POST request. The default
        action is to respond with "error 404 (not found)".
        """
        self.send_response(404)
        self.end_headers()
        self.wfile.write('not found'.encode('utf8'))

    def handle_GET(self):
        """
        Overwrite this method to handle a GET request. The default
        action is to respond with "error 404 (not found)".
        """
        self.send_response(404)
        self.end_headers()
        self.wfile.write('not found'.encode('utf8'))

    def send_response(self, code):
        """
        See Python's BaseHTTPRequestHandler.send_response().
        """
        BaseHTTPRequestHandler.send_response(self, code)
        self.send_header("Connection", "close")

if __name__ == '__main__':
    try:
        server = HTTPd(('', 8123), RequestHandler)
        server.add_account('test', 'fo')
        print 'started httpserver...'
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

########NEW FILE########
__FILENAME__ = Server
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Base class for all servers.
"""
import select
import socket
from multiprocessing import Process, Pipe

class Server(Process):
    """
    Base class of the Telnet and SSH servers. Servers are intended to be
    used for tests and attempt to emulate a device using the behavior of
    the associated L{Exscript.emulators.VirtualDevice}. Sample usage::

        device = VirtualDevice('myhost')
        daemon = Telnetd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.
    """

    def __init__(self, host, port, device):
        """
        Constructor.

        @type  host: str
        @param host: The address against which the daemon binds.
        @type  port: str
        @param port: The TCP port on which to listen.
        @type  device: VirtualDevice
        @param device: A virtual device instance.
        """
        Process.__init__(self, target = self._run)
        self.host    = host
        self.port    = int(port)
        self.timeout = .5
        self.dbg     = 0
        self.running = False
        self.buf     = ''
        self.socket  = None
        self.device  = device
        self.parent_conn, self.child_conn = Pipe()

    def _dbg(self, level, msg):
        if self.dbg >= level:
            print self.host + ':' + str(self.port), '-',
            print msg

    def _poll_child_process(self):
        if not self.child_conn.poll():
            return False
        if not self.running:
            return False
        try:
            msg = self.child_conn.recv()
        except socket.error:
            self.running = False
            return False
        if msg == 'shutdown':
            self.running = False
            return False
        return True

    def _shutdown_notify(self, conn):
        raise NotImplementedError()

    def _handle_connection(self, conn):
        raise NotImplementedError()

    def _run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True

        while self.running:
            self._poll_child_process()

            r, w, x = select.select([self.socket], [], [], self.timeout)
            if not r:
                continue

            conn, addr = self.socket.accept()
            try:
                self._handle_connection(conn)
            except socket.error:
                pass # network error
            finally:
                self._shutdown_notify(conn)
                conn.close()

        self.socket.close()

    def exit(self):
        """
        Stop the daemon without waiting for the thread to terminate.
        """
        self.parent_conn.send('shutdown')

    def exit_command(self, cmd):
        """
        Like exit(), but may be used as a handler in add_command.

        @type  cmd: str
        @param cmd: The command that causes the server to exit.
        """
        self.exit()
        return ''

########NEW FILE########
__FILENAME__ = SSHd
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
An SSH2 server.
"""
import os
import base64
import socket
import threading
import Crypto
import paramiko
from paramiko                import ServerInterface
from Exscript.servers.Server import Server

class _ParamikoServer(ServerInterface):
    # 'data' is the output of base64.encodestring(str(key))
    data = 'AAAAB3NzaC1yc2EAAAABIwAAAIEAyO4it3fHlmGZWJaGrfeHOVY7RWO3P9M7hp' + \
           'fAu7jJ2d7eothvfeuoRFtJwhUmZDluRdFyhFY/hFAh76PJKGAusIqIQKlkJxMC' + \
           'KDqIexkgHAfID/6mqvmnSJf0b5W8v5h2pI/stOSwTQ+pxVhwJ9ctYDhRSlF0iT' + \
           'UWT10hcuO4Ks8='
    good_pub_key = paramiko.RSAKey(data = base64.decodestring(data))

    def __init__(self):
        self.event = threading.Event()

        # Since each server is created in it's own thread, we must
        # re-initialize the random number generator to make sure that
        # child threads have no way of guessing the numbers of the parent.
        # If we don't, PyCrypto generates an error message for security
        # reasons.
        try:
            Crypto.Random.atfork()
        except AttributeError:
            # pycrypto versions that have no "Random" module also do not
            # detect the missing atfork() call, so they do not raise.
            pass

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL # TODO: paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self,
                                  channel,
                                  term,
                                  width,
                                  height,
                                  pixelwidth,
                                  pixelheight,
                                  modes):
        return True

class SSHd(Server):
    """
    A SSH2 server. Usage::

        device = VirtualDevice('myhost')
        daemon = SSHd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.

    @keyword key: An Exscript.PrivateKey object.
    """

    def __init__(self, host, port, device, key = None):
        Server.__init__(self, host, port, device)
        if key:
            keyfile = key.get_filename()
        else:
            keyfile = os.path.expanduser('~/.ssh/id_rsa')
        self.host_key = paramiko.RSAKey(filename = keyfile)
        self.channel  = None

    def _recvline(self):
        while not '\n' in self.buf:
            self._poll_child_process()
            if not self.running:
                return None
            try:
                data = self.channel.recv(1024)
            except socket.timeout:
                continue
            if not data:
                self.running = False
                return None
            self.buf += data.replace('\r\n', '\n').replace('\r', '\n')
        lines    = self.buf.split('\n')
        self.buf = '\n'.join(lines[1:])
        return lines[0] + '\n'

    def _shutdown_notify(self, conn):
        if self.channel:
            self.channel.send('Server is shutting down.\n')

    def _handle_connection(self, conn):
        t = paramiko.Transport(conn)
        try:
            t.load_server_moduli()
        except:
            self._dbg(1, 'Failed to load moduli, gex will be unsupported.')
            raise
        t.add_server_key(self.host_key)
        server = _ParamikoServer()
        t.start_server(server = server)

        # wait for auth
        self.channel = t.accept(20)
        if self.channel is None:
            self._dbg(1, 'Client disappeared before requesting channel.')
            t.close()
            return
        self.channel.settimeout(self.timeout)

        # wait for shell request
        server.event.wait(10)
        if not server.event.isSet():
            self._dbg(1, 'Client never asked for a shell.')
            t.close()
            return

        # send the banner
        self.channel.send(self.device.init())

        # accept commands
        while self.running:
            line = self._recvline()
            if not line:
                continue
            response = self.device.do(line)
            if response:
                self.channel.send(response)
        t.close()

########NEW FILE########
__FILENAME__ = Telnetd
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A Telnet server.
"""
import select
from Exscript.servers.Server import Server

class Telnetd(Server):
    """
    A Telnet server. Usage::

        device = VirtualDevice('myhost')
        daemon = Telnetd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.
    """

    def _recvline(self, conn):
        while not '\n' in self.buf:
            self._poll_child_process()
            r, w, x = select.select([conn], [], [], self.timeout)
            if not self.running:
                return None
            if not r:
                continue
            buf = conn.recv(1024)
            if not buf:
                self.running = False
                return None
            self.buf += buf.replace('\r\n', '\n').replace('\r', '\n')
        lines    = self.buf.split('\n')
        self.buf = '\n'.join(lines[1:])
        return lines[0] + '\n'

    def _shutdown_notify(self, conn):
        try:
            conn.send('Server is shutting down.\n')
        except Exception:
            pass

    def _handle_connection(self, conn):
        conn.send(self.device.init())

        while self.running:
            line = self._recvline(conn)
            if not line:
                continue
            response = self.device.do(line)
            if response:
                conn.send(response)

########NEW FILE########
__FILENAME__ = connection
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript             import Account
from Exscript.stdlib.util import secure_function

@secure_function
def authenticate(scope):
    """
    Looks for any username/password prompts on the current connection
    and logs in using the login information that was passed to Exscript.
    """
    scope.get('__connection__').app_authenticate()
    return True

@secure_function
def authenticate_user(scope, user = [None], password = [None]):
    """
    Like authenticate(), but logs in using the given user and password.
    If a user and password are not given, the function uses the same
    user and password that were used at the last login attempt; it is
    an error if no such attempt was made before.

    @type  user: string
    @param user: A username.
    @type  password: string
    @param password: A password.
    """
    conn = scope.get('__connection__')
    user = user[0]
    if user is None:
        conn.app_authenticate()
    else:
        account = Account(user, password[0])
        conn.app_authenticate(account)
    return True

@secure_function
def authorize(scope, password = [None]):
    """
    Looks for a password prompt on the current connection
    and enters the given password.
    If a password is not given, the function uses the same
    password that was used at the last login attempt; it is
    an error if no such attempt was made before.

    @type  password: string
    @param password: A password.
    """
    conn     = scope.get('__connection__')
    password = password[0]
    if password is None:
        conn.app_authorize()
    else:
        account = Account('', password)
        conn.app_authorize(account)
    return True

@secure_function
def auto_authorize(scope, password = [None]):
    """
    Executes a command on the remote host that causes an authorization
    procedure to be started, then authorizes using the given password
    in the same way in which authorize() works.
    Depending on the detected operating system of the remote host the
    following commands are started:

      - on IOS, the "enable" command is executed.
      - nothing on other operating systems yet.

    @type  password: string
    @param password: A password.
    """
    conn     = scope.get('__connection__')
    password = password[0]
    if password is None:
        conn.auto_app_authorize()
    else:
        account = Account('', password)
        conn.auto_app_authorize(account)
    return True

@secure_function
def autoinit(scope):
    """
    Make the remote host more script-friendly by automatically executing
    one or more commands on it.
    The commands executed depend on the currently used driver.
    For example, the driver for Cisco IOS would execute the
    following commands::

        term len 0
        term width 0
    """
    scope.get('__connection__').autoinit()
    return True

@secure_function
def close(scope):
    """
    Closes the existing connection with the remote host. This function is
    rarely used, as normally Exscript closes the connection automatically
    when the script has completed.
    """
    conn = scope.get('__connection__')
    conn.close(1)
    scope.define(__response__ = conn.response)
    return True

@secure_function
def exec_(scope, data):
    """
    Sends the given data to the remote host and waits until the host
    has responded with a prompt.
    If the given data is a list of strings, each item is sent, and
    after each item a prompt is expected.

    This function also causes the response of the command to be stored
    in the built-in __response__ variable.

    @type  data: string
    @param data: The data that is sent.
    """
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.send(line)
        conn.expect_prompt()
        response += conn.response.split('\n')[1:]
    scope.define(__response__ = response)
    return True

@secure_function
def execline(scope, data):
    """
    Like exec(), but appends a newline to the command in data before sending
    it.

    @type  data: string
    @param data: The data that is sent.
    """
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.execute(line)
        response += conn.response.split('\n')[1:]
    scope.define(__response__ = response)
    return True

@secure_function
def guess_os(scope):
    """
    Guesses the operating system of the connected host.

    The recognition is based on the past conversation that has happened
    on the host; Exscript looks for known patterns and maps them to specific
    operating systems.

    @rtype:  string
    @return: The operating system.
    """
    conn = scope.get('__connection__')
    return [conn.guess_os()]

@secure_function
def send(scope, data):
    """
    Like exec(), but does not wait for a response of the remote host after
    sending the command.

    @type  data: string
    @param data: The data that is sent.
    """
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line)
    return True

@secure_function
def sendline(scope, data):
    """
    Like execline(), but does not wait for a response of the remote host after
    sending the command.

    @type  data: string
    @param data: The data that is sent.
    """
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line + '\r')
    return True

@secure_function
def wait_for(scope, prompt):
    """
    Waits until the response of the remote host contains the given pattern.

    @type  prompt: regex
    @param prompt: The prompt pattern.
    """
    conn = scope.get('__connection__')
    conn.expect(prompt)
    scope.define(__response__ = conn.response)
    return True

@secure_function
def set_prompt(scope, prompt = None):
    """
    Defines the pattern that is recognized at any future time when Exscript
    needs to wait for a prompt.
    In other words, whenever Exscript waits for a prompt, it searches the
    response of the host for the given pattern and continues as soon as the
    pattern is found.

    Exscript waits for a prompt whenever it sends a command (unless the send()
    method was used). set_prompt() redefines as to what is recognized as a
    prompt.

    @type  prompt: regex
    @param prompt: The prompt pattern.
    """
    conn = scope.get('__connection__')
    conn.set_prompt(prompt)
    return True

@secure_function
def set_error(scope, error_re = None):
    """
    Defines a pattern that, whenever detected in the response of the remote
    host, causes an error to be raised.

    In other words, whenever Exscript waits for a prompt, it searches the
    response of the host for the given pattern and raises an error if the
    pattern is found.

    @type  error_re: regex
    @param error_re: The error pattern.
    """
    conn = scope.get('__connection__')
    conn.set_error_prompt(error_re)
    return True

@secure_function
def set_timeout(scope, timeout):
    """
    Defines the time after which Exscript fails if it does not receive a
    prompt from the remote host.

    @type  timeout: int
    @param timeout: The timeout in seconds.
    """
    conn = scope.get('__connection__')
    conn.set_timeout(int(timeout[0]))
    return True

########NEW FILE########
__FILENAME__ = crypt
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.util        import crypt
from Exscript.stdlib.util import secure_function

@secure_function
def otp(scope, password, seed, seqs):
    """
    Calculates a one-time password hash using the given password, seed, and
    sequence number and returns it.
    Uses the md4/sixword algorithm as supported by TACACS+ servers.

    @type  password: string
    @param password: A password.
    @type  seed: string
    @param seed: A username.
    @type  seqs: int
    @param seqs: A sequence number, or a list of sequence numbers.
    @rtype:  string
    @return: A hash, or a list of hashes.
    """
    return [crypt.otp(password[0], seed[0], int(seq)) for seq in seqs]

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
from Exscript.stdlib.util import secure_function

def chmod(scope, filename, mode):
    """
    Changes the permissions of the given file (or list of files)
    to the given mode. You probably want to use an octal representation
    for the integer, e.g. "chmod(myfile, 0644)".

    @type  filename: string
    @param filename: A filename.
    @type  mode: int
    @param mode: The access permissions.
    """
    for file in filename:
        os.chmod(file, mode[0])
    return True

def clear(scope, filename):
    """
    Clear the contents of the given file. The file is created if it does
    not exist.

    @type  filename: string
    @param filename: A filename.
    """
    file = open(filename[0], 'w')
    file.close()
    return True

@secure_function
def exists(scope, filename):
    """
    Returns True if the file with the given name exists, False otherwise.
    If a list of files is given, the function returns True only if ALL of
    the files exist.

    @type  filename: string
    @param filename: A filename.
    @rtype:  bool
    @return: The operating system of the remote device.
    """
    return [os.path.exists(f) for f in filename]

def mkdir(scope, dirname, mode = None):
    """
    Creates the given directory (or directories). The optional access
    permissions are set to the given mode, and default to whatever
    is the umask on your system defined.

    @type  dirname: string
    @param dirname: A filename, or a list of dirnames.
    @type  mode: int
    @param mode: The access permissions.
    """
    for dir in dirname:
        if mode is None:
            os.makedirs(dir)
        else:
            os.makedirs(dir, mode[0])
    return True

def read(scope, filename):
    """
    Reads the given file and returns the result.
    The result is also stored in the built-in __response__ variable.

    @type  filename: string
    @param filename: A filename.
    @rtype:  string
    @return: The content of the file.
    """
    file  = open(filename[0], 'r')
    lines = file.readlines()
    file.close()
    scope.define(__response__ = lines)
    return lines

def rm(scope, filename):
    """
    Deletes the given file (or files) from the file system.

    @type  filename: string
    @param filename: A filename, or a list of filenames.
    """
    for file in filename:
        os.remove(file)
    return True

def write(scope, filename, lines, mode = ['a']):
    """
    Writes the given string into the given file.
    The following modes are supported:

      - 'a': Append to the file if it already exists.
      - 'w': Replace the file if it already exists.

    @type  filename: string
    @param filename: A filename.
    @type  lines: string
    @param lines: The data that is written into the file.
    @type  mode: string
    @param mode: Any of the above listed modes.
    """
    file = open(filename[0], mode[0])
    file.writelines(['%s\n' % line.rstrip() for line in lines])
    file.close()
    return True

########NEW FILE########
__FILENAME__ = ipv4
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.util        import ipv4
from Exscript.stdlib.util import secure_function

@secure_function
def in_network(scope, prefixes, destination, default_pfxlen = [24]):
    """
    Returns True if the given destination is in the network range that is
    defined by the given prefix (e.g. 10.0.0.1/22). If the given prefix
    does not have a prefix length specified, the given default prefix length
    is applied. If no such prefix length is given, the default length is
    /24.

    If a list of prefixes is passed, this function returns True only if
    the given destination is in ANY of the given prefixes.

    @type  prefixes: string
    @param prefixes: A prefix, or a list of IP prefixes.
    @type  destination: string
    @param destination: An IP address.
    @type  default_pfxlen: int
    @param default_pfxlen: The default prefix length.
    @rtype:  True
    @return: Whether the given destination is in the given network.
    """
    needle = ipv4.ip2int(destination[0])
    for prefix in prefixes:
        network, pfxlen = ipv4.parse_prefix(prefix, default_pfxlen[0])
        mask            = ipv4.pfxlen2mask_int(pfxlen)
        if needle & mask == ipv4.ip2int(network) & mask:
            return [True]
    return [False]

@secure_function
def mask(scope, ips, mask):
    """
    Applies the given IP mask (e.g. 255.255.255.0) to the given IP address
    (or list of IP addresses) and returns it.

    @type  ips: string
    @param ips: A prefix, or a list of IP prefixes.
    @type  mask: string
    @param mask: An IP mask.
    @rtype:  string
    @return: The network(s) that result(s) from applying the mask.
    """
    mask = ipv4.ip2int(mask[0])
    return [ipv4.int2ip(ipv4.ip2int(ip) & mask) for ip in ips]

@secure_function
def mask2pfxlen(scope, masks):
    """
    Converts the given IP mask(s) (e.g. 255.255.255.0) to prefix length(s).

    @type  masks: string
    @param masks: An IP mask, or a list of masks.
    @rtype:  string
    @return: The prefix length(s) that result(s) from converting the mask.
    """
    return [ipv4.mask2pfxlen(mask) for mask in masks]

@secure_function
def pfxlen2mask(scope, pfxlen):
    """
    Converts the given prefix length(s) (e.g. 30) to IP mask(s).

    @type  pfxlen: int
    @param pfxlen: An IP prefix length.
    @rtype:  string
    @return: The mask(s) that result(s) from converting the prefix length.
    """
    return [ipv4.pfxlen2mask(pfx) for pfx in pfxlen]

@secure_function
def network(scope, prefixes):
    """
    Given a prefix, this function returns the corresponding network address.

    @type  prefixes: string
    @param prefixes: An IP prefix.
    @rtype:  string
    @return: The network address(es) of the prefix length(s).
    """
    return [ipv4.network(pfx) for pfx in prefixes]

@secure_function
def broadcast(scope, prefixes):
    """
    Given a prefix, this function returns the corresponding broadcast address.

    @type  prefixes: string
    @param prefixes: An IP prefix.
    @rtype:  string
    @return: The broadcast address(es) of the prefix length(s).
    """
    return [ipv4.broadcast(pfx) for pfx in prefixes]

@secure_function
def pfxmask(scope, ips, pfxlen):
    """
    Applies the given prefix length to the given ips, resulting in a
    (list of) IP network addresses.

    @type  ips: string
    @param ips: An IP address, or a list of IP addresses.
    @type  pfxlen: int
    @param pfxlen: An IP prefix length.
    @rtype:  string
    @return: The mask(s) that result(s) from converting the prefix length.
    """
    mask = ipv4.pfxlen2mask_int(pfxlen[0])
    return [ipv4.int2ip(ipv4.ip2int(ip) & mask) for ip in ips]

@secure_function
def remote_ip(scope, local_ips):
    """
    Given an IP address, this function calculates the remaining available
    IP address under the assumption that it is a /30 network.
    In other words, given one link net address, this function returns the
    other link net address.

    @type  local_ips: string
    @param local_ips: An IP address, or a list of IP addresses.
    @rtype:  string
    @return: The other IP address of the link address pair.
    """
    return [ipv4.remote_ip(ip) for ip in local_ips]

########NEW FILE########
__FILENAME__ = list
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.stdlib.util import secure_function

@secure_function
def new(scope):
    """
    Returns a new, empty list.

    @rtype:  string
    @return: The model of the remote device.
    """
    return []

@secure_function
def length(scope, mylist):
    """
    Returns the number of items in the list.

    @rtype:  string
    @return: The model of the remote device.
    """
    return [len(mylist)]

@secure_function
def get(scope, source, index):
    """
    Returns a copy of the list item with the given index.
    It is an error if an item with teh given index does not exist.

    @type  source: string
    @param source: A list of strings.
    @type  index: string
    @param index: A list of strings.
    @rtype:  string
    @return: The cleaned up list of strings.
    """
    try:
        index = int(index[0])
    except IndexError:
        raise ValueError('index variable is required')
    except ValueError:
        raise ValueError('index is not an integer')
    try:
        return [source[index]]
    except IndexError:
        raise ValueError('no such item in the list')

@secure_function
def unique(scope, source):
    """
    Returns a copy of the given list in which all duplicates are removed
    such that one of each item remains in the list.

    @type  source: string
    @param source: A list of strings.
    @rtype:  string
    @return: The cleaned up list of strings.
    """
    return dict(map(lambda a: (a, 1), source)).keys()

########NEW FILE########
__FILENAME__ = mysys
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import time
import sys
from subprocess import Popen, PIPE, STDOUT
from Exscript.stdlib.util import secure_function

def execute(scope, command):
    """
    Executes the given command locally.

    @type  command: string
    @param command: A shell command.
    """
    process = Popen(command[0],
                    shell     = True,
                    stdin     = PIPE,
                    stdout    = PIPE,
                    stderr    = STDOUT,
                    close_fds = True)
    scope.define(__response__ = process.stdout.read())
    return True

@secure_function
def message(scope, string):
    """
    Writes the given string to stdout.

    @type  string: string
    @param string: A string, or a list of strings.
    """
    sys.stdout.write(''.join(string) + '\n')
    return True

@secure_function
def wait(scope, seconds):
    """
    Waits for the given number of seconds.

    @type  seconds: int
    @param seconds: The wait time in seconds.
    """
    time.sleep(int(seconds[0]))
    return True

########NEW FILE########
__FILENAME__ = string
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.stdlib.util import secure_function

@secure_function
def replace(scope, strings, source, dest):
    """
    Returns a copy of the given string (or list of strings) in which all
    occurrences of the given source are replaced by the given dest.

    @type  strings: string
    @param strings: A string, or a list of strings.
    @type  source: string
    @param source: What to replace.
    @type  dest: string
    @param dest: What to replace it with.
    @rtype:  string
    @return: The resulting string, or list of strings.
    """
    return [s.replace(source[0], dest[0]) for s in strings]

@secure_function
def tolower(scope, strings):
    """
    Returns the given string in lower case.

    @type  strings: string
    @param strings: A string, or a list of strings.
    @rtype:  string
    @return: The resulting string, or list of strings in lower case.
    """
    return [s.lower() for s in strings]

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from functools import wraps

def secure_function(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)
    wrapper._is_secure = True
    return wrapper

########NEW FILE########
__FILENAME__ = buffer
# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A buffer object.
"""
from StringIO           import StringIO
from Exscript.util.cast import to_regexs

class MonitoredBuffer(object):
    """
    A specialized string buffer that allows for monitoring
    the content using regular expression-triggered callbacks.
    """

    def __init__(self, io = None):
        """
        Constructor.
        The data is stored in the given file-like object. If no object is
        given, or the io argument is None, a new StringIO is used.

        @type  io: file-like object
        @param io: A file-like object that is used for storing the data.
        """
        if io is None:
            self.io = StringIO('')
        else:
            self.io = io
        self.monitors = []
        self.clear()

    def __str__(self):
        """
        Returns the content of the buffer.
        """
        return self.io.getvalue()

    def size(self):
        """
        Returns the size of the buffer.

        @rtype: int
        @return: The size of the buffer in bytes.
        """
        return self.io.tell()

    def head(self, bytes):
        """
        Returns the number of given bytes from the head of the buffer.
        The buffer remains unchanged.

        @type  bytes: int
        @param bytes: The number of bytes to return.
        """
        oldpos = self.io.tell()
        self.io.seek(0)
        head = self.io.read(bytes)
        self.io.seek(oldpos)
        return head

    def tail(self, bytes):
        """
        Returns the number of given bytes from the tail of the buffer.
        The buffer remains unchanged.

        @type  bytes: int
        @param bytes: The number of bytes to return.
        """
        self.io.seek(self.size() - bytes)
        return self.io.read()

    def pop(self, bytes):
        """
        Like L{head()}, but also removes the head from the buffer.

        @type  bytes: int
        @param bytes: The number of bytes to return and remove.
        """
        self.io.seek(0)
        head = self.io.read(bytes)
        tail = self.io.read()
        self.io.seek(0)
        self.io.write(tail)
        self.io.truncate()
        return head

    def append(self, data):
        """
        Appends the given data to the buffer, and triggers all connected
        monitors, if any of them match the buffer content.

        @type  data: str
        @param data: The data that is appended.
        """
        self.io.write(data)
        if not self.monitors:
            return

        # Check whether any of the monitoring regular expressions matches.
        # If it does, we need to disable that monitor until the matching
        # data is no longer in the buffer. We accomplish this by keeping
        # track of the position of the last matching byte.
        buf = str(self)
        for item in self.monitors:
            regex_list, callback, bytepos, limit = item
            bytepos = max(bytepos, len(buf) - limit)
            for i, regex in enumerate(regex_list):
                match = regex.search(buf, bytepos)
                if match is not None:
                    item[2] = match.end()
                    callback(i, match)

    def clear(self):
        """
        Removes all data from the buffer.
        """
        self.io.seek(0)
        self.io.truncate()
        for item in self.monitors:
            item[2] = 0

    def add_monitor(self, pattern, callback, limit = 80):
        """
        Calls the given function whenever the given pattern matches the
        buffer.

        Arguments passed to the callback are the index of the match, and
        the match object of the regular expression.

        @type  pattern: str|re.RegexObject|list(str|re.RegexObject)
        @param pattern: One or more regular expressions.
        @type  callback: callable
        @param callback: The function that is called.
        @type  limit: int
        @param limit: The maximum size of the tail of the buffer
                      that is searched, in number of bytes.
        """
        self.monitors.append([to_regexs(pattern), callback, 0, limit])

########NEW FILE########
__FILENAME__ = cast
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Handy shortcuts for converting types.
"""
import re
import Exscript

def to_list(item):
    """
    If the given item is iterable, this function returns the given item.
    If the item is not iterable, this function returns a list with only the
    item in it.

    @type  item: object
    @param item: Any object.
    @rtype:  list
    @return: A list with the item in it.
    """
    if hasattr(item, '__iter__'):
        return item
    return [item]

def to_host(host, default_protocol = 'telnet', default_domain = ''):
    """
    Given a string or a Host object, this function returns a Host object.

    @type  host: string|Host
    @param host: A hostname (may be URL formatted) or a Host object.
    @type  default_protocol: str
    @param default_protocol: Passed to the Host constructor.
    @type  default_domain: str
    @param default_domain: Appended to each hostname that has no domain.
    @rtype:  Host
    @return: The Host object.
    """
    if host is None:
        raise TypeError('None can not be cast to Host')
    if hasattr(host, 'get_address'):
        return host
    if default_domain and not '.' in host:
        host += '.' + default_domain
    return Exscript.Host(host, default_protocol = default_protocol)

def to_hosts(hosts, default_protocol = 'telnet', default_domain = ''):
    """
    Given a string or a Host object, or a list of strings or Host objects,
    this function returns a list of Host objects.

    @type  hosts: string|Host|list(string)|list(Host)
    @param hosts: One or more hosts or hostnames.
    @type  default_protocol: str
    @param default_protocol: Passed to the Host constructor.
    @type  default_domain: str
    @param default_domain: Appended to each hostname that has no domain.
    @rtype:  list[Host]
    @return: A list of Host objects.
    """
    return [to_host(h, default_protocol, default_domain)
            for h in to_list(hosts)]

def to_regex(regex, flags = 0):
    """
    Given a string, this function returns a new re.RegexObject.
    Given a re.RegexObject, this function just returns the same object.

    @type  regex: string|re.RegexObject
    @param regex: A regex or a re.RegexObject
    @type  flags: int
    @param flags: See Python's re.compile().
    @rtype:  re.RegexObject
    @return: The Python regex object.
    """
    if regex is None:
        raise TypeError('None can not be cast to re.RegexObject')
    if hasattr(regex, 'match'):
        return regex
    return re.compile(regex, flags)

def to_regexs(regexs):
    """
    Given a string or a re.RegexObject, or a list of strings or
    re.RegexObjects, this function returns a list of re.RegexObjects.

    @type  regexs: str|re.RegexObject|list(str|re.RegexObject)
    @param regexs: One or more regexs or re.RegexObjects.
    @rtype:  list(re.RegexObject)
    @return: A list of re.RegexObjects.
    """
    return [to_regex(r) for r in to_list(regexs)]

########NEW FILE########
__FILENAME__ = crypt
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Encryption related utilities.
"""
from Exscript.external.otp import generate

def otp(password, seed, sequence):
    """
    Calculates a one-time password hash using the given password, seed, and
    sequence number and returns it.
    Uses the MD4/sixword algorithm as supported by TACACS+ servers.

    @type  password: string
    @param password: A password.
    @type  seed: string
    @param seed: A username.
    @type  sequence: int
    @param sequence: A sequence number.
    @rtype:  string
    @return: A hash.
    """
    return generate(password, seed, sequence, 1, 'md4', 'sixword')[0]

########NEW FILE########
__FILENAME__ = daemonize
# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Daemonizing a process.
"""
import sys
import os

def _redirect_output(filename):
    out_log  = open(filename, 'a+', 0)
    err_log  = open(filename, 'a+', 0)
    dev_null = open(os.devnull, 'r')
    os.close(sys.stdin.fileno())
    os.close(sys.stdout.fileno())
    os.close(sys.stderr.fileno())
    os.dup2(out_log.fileno(), sys.stdout.fileno())
    os.dup2(err_log.fileno(), sys.stderr.fileno())
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

def daemonize():
    """
    Forks and daemonizes the current process. Does not automatically track
    the process id; to do this, use L{Exscript.util.pidutil}.
    """
    sys.stdout.flush()
    sys.stderr.flush()

    # UNIX double-fork magic. We need to fork before any threads are
    # created.
    pid = os.fork()
    if pid > 0:
        # Exit first parent.
        sys.exit(0)

    # Decouple from parent environment.
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # Now fork again.
    pid = os.fork()
    if pid > 0:
        # Exit second parent.
        sys.exit(0)

    _redirect_output(os.devnull)

########NEW FILE########
__FILENAME__ = decorator
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Decorators for callbacks passed to Queue.run().
"""
from impl import add_label, get_label, copy_labels
from Exscript.protocols.Exception import LoginFailure

def bind(function, *args, **kwargs):
    """
    Wraps the given function such that when it is called, the given arguments
    are passed in addition to the connection argument.

    @type  function: function
    @param function: The function that's ought to be wrapped.
    @type  args: list
    @param args: Passed on to the called function.
    @type  kwargs: dict
    @param kwargs: Passed on to the called function.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorated(*inner_args, **inner_kwargs):
        kwargs.update(inner_kwargs)
        return function(*(inner_args + args), **kwargs)
    copy_labels(function, decorated)
    return decorated

def os_function_mapper(map):
    """
    When called with an open connection, this function uses the
    conn.guess_os() function to guess the operating system
    of the connected host.
    It then uses the given map to look up a function name that corresponds
    to the operating system, and calls it. Example::

        def ios_xr(job, host, conn):
            pass # Do something.

        def junos(job, host, conn):
            pass # Do something else.

        def shell(job, host, conn):
            pass # Do something else.

        Exscript.util.start.quickrun('myhost', os_function_mapper(globals()))

    An exception is raised if a matching function is not found in the map.

    @type  conn: Exscript.protocols.Protocol
    @param conn: The open connection.
    @type  map: dict
    @param map: A dictionary mapping operating system name to a function.
    @type  args: list
    @param args: Passed on to the called function.
    @type  kwargs: dict
    @param kwargs: Passed on to the called function.
    @rtype:  object
    @return: The return value of the called function.
    """
    def decorated(job, host, conn, *args, **kwargs):
        os   = conn.guess_os()
        func = map.get(os)
        if func is None:
            raise Exception('No handler for %s found.' % os)
        return func(job, host, conn, *args, **kwargs)
    return decorated

def autologin(flush = True, attempts = 1):
    """
    Wraps the given function such that conn.login() is executed
    before calling it. Example::

        @autologin(attempts = 2)
        def my_func(job, host, conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', my_func)

    @type  flush: bool
    @param flush: Whether to flush the last prompt from the buffer.
    @type  attempts: int
    @param attempts: The number of login attempts if login fails.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorator(function):
        def decorated(job, host, conn, *args, **kwargs):
            failed = 0
            while True:
                try:
                    conn.login(flush = flush)
                except LoginFailure, e:
                    failed += 1
                    if failed >= attempts:
                        raise
                    continue
                break
            return function(job, host, conn, *args, **kwargs)
        copy_labels(function, decorated)
        return decorated
    return decorator

########NEW FILE########
__FILENAME__ = event
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A simple signal/event mechanism.
"""
from threading     import Lock
from Exscript.util import weakmethod

class Event(object):
    """
    A simple signal/event mechanism, to be used like this::

        def mycallback(arg, **kwargs):
            print arg, kwargs['foo']

        myevent = Event()
        myevent.connect(mycallback)
        myevent.emit('test', foo = 'bar')
        # Or just: myevent('test', foo = 'bar')
    """

    def __init__(self):
        """
        Constructor.
        """
        # To save memory, we do NOT init the subscriber attributes with
        # lists. Unfortunately this makes a lot of the code in this class
        # more messy than it should be, but events are used so widely in
        # Exscript that this change makes a huge difference to the memory
        # footprint.
        self.lock             = None
        self.weak_subscribers = None
        self.hard_subscribers = None

    def __call__(self, *args, **kwargs):
        """
        Like emit().
        """
        return self.emit(*args, **kwargs)

    def connect(self, callback, *args, **kwargs):
        """
        Connects the event with the given callback.
        When the signal is emitted, the callback is invoked.

        @note: The signal handler is stored with a hard reference, so you
        need to make sure to call L{disconnect()} if you want the handler
        to be garbage collected.

        @type  callback: object
        @param callback: The callback function.
        @type  args: tuple
        @param args: Optional arguments passed to the callback.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callback.
        """
        if self.is_connected(callback):
            raise AttributeError('callback is already connected')
        if self.hard_subscribers is None:
            self.hard_subscribers = []
        self.hard_subscribers.append((callback, args, kwargs))

    def listen(self, callback, *args, **kwargs):
        """
        Like L{connect()}, but uses a weak reference instead of a
        normal reference.
        The signal is automatically disconnected as soon as the handler
        is garbage collected.

        @note: Storing signal handlers as weak references means that if
        your handler is a local function, it may be garbage collected. To
        prevent this, use L{connect()} instead.

        @type  callback: object
        @param callback: The callback function.
        @type  args: tuple
        @param args: Optional arguments passed to the callback.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callback.
        @rtype:  L{Exscript.util.weakmethod.WeakMethod}
        @return: The newly created weak reference to the callback.
        """
        if self.lock is None:
            self.lock = Lock()
        with self.lock:
            if self.is_connected(callback):
                raise AttributeError('callback is already connected')
            if self.weak_subscribers is None:
                self.weak_subscribers = []
            ref = weakmethod.ref(callback, self._try_disconnect)
            self.weak_subscribers.append((ref, args, kwargs))
        return ref

    def n_subscribers(self):
        """
        Returns the number of connected subscribers.

        @rtype:  int
        @return: The number of subscribers.
        """
        hard = self.hard_subscribers and len(self.hard_subscribers) or 0
        weak = self.weak_subscribers and len(self.weak_subscribers) or 0
        return hard + weak

    def _hard_callbacks(self):
        return [s[0] for s in self.hard_subscribers]

    def _weakly_connected_index(self, callback):
        if self.weak_subscribers is None:
            return None
        weak = [s[0].get_function() for s in self.weak_subscribers]
        try:
            return weak.index(callback)
        except ValueError:
            return None

    def is_connected(self, callback):
        """
        Returns True if the event is connected to the given function.

        @type  callback: object
        @param callback: The callback function.
        @rtype:  bool
        @return: Whether the signal is connected to the given function.
        """
        index = self._weakly_connected_index(callback)
        if index is not None:
            return True
        if self.hard_subscribers is None:
            return False
        return callback in self._hard_callbacks()

    def emit(self, *args, **kwargs):
        """
        Emits the signal, passing the given arguments to the callbacks.
        If one of the callbacks returns a value other than None, no further
        callbacks are invoked and the return value of the callback is
        returned to the caller of emit().

        @type  args: tuple
        @param args: Optional arguments passed to the callbacks.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callbacks.
        @rtype:  object
        @return: Returns None if all callbacks returned None. Returns
                 the return value of the last invoked callback otherwise.
        """
        if self.hard_subscribers is not None:
            for callback, user_args, user_kwargs in self.hard_subscribers:
                kwargs.update(user_kwargs)
                result = callback(*args + user_args, **kwargs)
                if result is not None:
                    return result

        if self.weak_subscribers is not None:
            for callback, user_args, user_kwargs in self.weak_subscribers:
                kwargs.update(user_kwargs)

                # Even though WeakMethod notifies us when the underlying
                # function is destroyed, and we remove the item from the
                # the list of subscribers, there is no guarantee that
                # this notification has already happened because the garbage
                # collector may run while this loop is executed.
                # Disabling the garbage collector temporarily also does
                # not work, because other threads may be trying to do
                # the same, causing yet another race condition.
                # So the only solution is to skip such functions.
                function = callback.get_function()
                if function is None:
                    continue
                result = function(*args + user_args, **kwargs)
                if result is not None:
                    return result

    def _try_disconnect(self, ref):
        """
        Called by the weak reference when its target dies.
        In other words, we can assert that self.weak_subscribers is not
        None at this time.
        """
        with self.lock:
            weak = [s[0] for s in self.weak_subscribers]
            try:
                index = weak.index(ref)
            except ValueError:
                # subscriber was already removed by a call to disconnect()
                pass
            else:
                self.weak_subscribers.pop(index)

    def disconnect(self, callback):
        """
        Disconnects the signal from the given function.

        @type  callback: object
        @param callback: The callback function.
        """
        if self.weak_subscribers is not None:
            with self.lock:
                index = self._weakly_connected_index(callback)
                if index is not None:
                    self.weak_subscribers.pop(index)[0]
        if self.hard_subscribers is not None:
            try:
                index = self._hard_callbacks().index(callback)
            except ValueError:
                pass
            else:
                self.hard_subscribers.pop(index)

    def disconnect_all(self):
        """
        Disconnects all connected functions from all signals.
        """
        self.hard_subscribers = None
        self.weak_subscribers = None

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Utilities for reading data from files.
"""
import re
import os
import base64
import codecs
import imp
from Exscript import Account
from Exscript.util.cast import to_host

def get_accounts_from_file(filename):
    """
    Reads a list of user/password combinations from the given file
    and returns a list of Account instances. The file content
    has the following format::

        [account-pool]
        user1 = cGFzc3dvcmQ=
        user2 = cGFzc3dvcmQ=

    Note that "cGFzc3dvcmQ=" is a base64 encoded password.
    If the input file contains extra config sections other than
    "account-pool", they are ignored.
    Each password needs to be base64 encrypted. To encrypt a password,
    you may use the following command::

        python -c 'import base64; print base64.b64encode("thepassword")'

    @type  filename: string
    @param filename: The name of the file containing the list of accounts.
    @rtype:  list[Account]
    @return: The newly created account instances.
    """
    accounts           = []
    cfgparser          = __import__('ConfigParser', {}, {}, [''])
    parser             = cfgparser.RawConfigParser()
    parser.optionxform = str
    parser.read(filename)
    for user, password in parser.items('account-pool'):
        accounts.append(Account(user, base64.decodestring(password)))
    return accounts


def get_hosts_from_file(filename,
                        default_protocol  = 'telnet',
                        default_domain    = '',
                        remove_duplicates = False,
                        encoding          = 'utf-8'):
    """
    Reads a list of hostnames from the file with the given name.

    @type  filename: string
    @param filename: A full filename.
    @type  default_protocol: str
    @param default_protocol: Passed to the Host constructor.
    @type  default_domain: str
    @param default_domain: Appended to each hostname that has no domain.
    @type  remove_duplicates: bool
    @param remove_duplicates: Whether duplicates are removed.
    @type  encoding: str
    @param encoding: The encoding of the file.
    @rtype:  list[Host]
    @return: The newly created host instances.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise IOError('No such file: %s' % filename)

    # Read the hostnames.
    have  = set()
    hosts = []
    with codecs.open(filename, 'r', encoding) as file_handle:
        for line in file_handle:
            hostname = line.split('#')[0].strip()
            if hostname == '':
                continue
            if remove_duplicates and hostname in have:
                continue
            have.add(hostname)
            hosts.append(to_host(hostname, default_protocol, default_domain))

    return hosts


def get_hosts_from_csv(filename,
                       default_protocol = 'telnet',
                       default_domain   = '',
                       encoding         = 'utf-8'):
    """
    Reads a list of hostnames and variables from the tab-separated .csv file
    with the given name. The first line of the file must contain the column
    names, e.g.::

        address	testvar1	testvar2
        10.0.0.1	value1	othervalue
        10.0.0.1	value2	othervalue2
        10.0.0.2	foo	bar

    For the above example, the function returns *two* host objects, where
    the 'testvar1' variable of the first host holds a list containing two
    entries ('value1' and 'value2'), and the 'testvar1' variable of the
    second host contains a list with a single entry ('foo').

    Both, the address and the hostname of each host are set to the address
    given in the first column. If you want the hostname set to another value,
    you may add a second column containing the hostname::

        address	hostname	testvar
        10.0.0.1	myhost	value
        10.0.0.2	otherhost	othervalue

    @type  filename: string
    @param filename: A full filename.
    @type  default_protocol: str
    @param default_protocol: Passed to the Host constructor.
    @type  default_domain: str
    @param default_domain: Appended to each hostname that has no domain.
    @type  encoding: str
    @param encoding: The encoding of the file.
    @rtype:  list[Host]
    @return: The newly created host instances.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise IOError('No such file: %s' % filename)

    with codecs.open(filename, 'r', encoding) as file_handle:
        # Read and check the header.
        header = file_handle.readline().rstrip()
        if re.search(r'^(?:hostname|address)\b', header) is None:
            msg  = 'Syntax error in CSV file header:'
            msg += ' File does not start with "hostname" or "address".'
            raise Exception(msg)
        if re.search(r'^(?:hostname|address)(?:\t[^\t]+)*$', header) is None:
            msg  = 'Syntax error in CSV file header:'
            msg += ' Make sure to separate columns by tabs.'
            raise Exception(msg)
        varnames = [str(v) for v in header.split('\t')]
        varnames.pop(0)

        # Walk through all lines and create a map that maps hostname to
        # definitions.
        last_uri = ''
        line_re  = re.compile(r'[\r\n]*$')
        hosts    = []
        for line in file_handle:
            if line.strip() == '':
                continue

            line   = line_re.sub('', line)
            values = line.split('\t')
            uri    = values.pop(0).strip()

            # Add the hostname to our list.
            if uri != last_uri:
                #print "Reading hostname", hostname_url, "from csv."
                host     = to_host(uri, default_protocol, default_domain)
                last_uri = uri
                hosts.append(host)

            # Define variables according to the definition.
            for i, varname in enumerate(varnames):
                try:
                    value = values[i]
                except IndexError:
                    value = ''
                if varname == 'hostname':
                    host.set_name(value)
                else:
                    host.append(varname, value)

    return hosts


def load_lib(filename):
    """
    Loads a Python file containing functions, and returns the
    content of the __lib__ variable. The __lib__ variable must contain
    a dictionary mapping function names to callables.

    Returns a dictionary mapping the namespaced function names to
    callables. The namespace is the basename of the file, without file
    extension.

    The result of this function can later be passed to run_template::

        functions = load_lib('my_library.py')
        run_template(conn, 'foo.exscript', **functions)

    @type  filename: string
    @param filename: A full filename.
    @rtype:  dict[string->object]
    @return: The loaded functions.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise IOError('No such file: %s' % filename)

    name = os.path.splitext(os.path.basename(filename))[0]
    module = imp.load_source(name, filename)

    return dict((name + '.' + k, v) for (k, v) in module.__lib__.iteritems())

########NEW FILE########
__FILENAME__ = impl
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Development tools.
"""
import sys
import warnings
import traceback
from functools import wraps

def add_label(obj, name, **kwargs):
    """
    Labels an object such that it can later be checked with
    L{has_label()}.

    @type  obj: object
    @param obj: The object that is labeled.
    @type  name: str
    @param name: A label.
    @type  kwargs: dict
    @param kwargs: Optional values to store with the label.
    @rtype:  object
    @return: The labeled function.
    """
    labels = obj.__dict__.setdefault('_labels', dict())
    labels[name] = kwargs
    return obj

def get_label(obj, name):
    """
    Checks whether an object has the given label attached (see
    L{mark_function()}) and returns the associated options.

    @type  obj: object
    @param obj: The object to check for the label.
    @type  name: str
    @param name: A label.
    @rtype:  dict or None
    @return: The optional values if the label is attached, None otherwise.
    """
    labels = obj.__dict__.get('_labels')
    if labels is None:
        return None
    return labels.get(name)

def copy_labels(src, dst):
    """
    Copies all labels of one object to another object.

    @type  src: object
    @param src: The object to check read the labels from.
    @type  dst: object
    @param dst: The object into which the labels are copied.
    """
    labels = src.__dict__.get('_labels')
    if labels is None:
        return
    dst.__dict__['_labels'] = labels.copy()

def serializeable_exc_info(thetype, ex, tb):
    """
    Since traceback objects can not be pickled, this function manipulates
    exception info tuples before they are passed accross process
    boundaries.
    """
    return thetype, ex, ''.join(traceback.format_exception(thetype, ex, tb))

def serializeable_sys_exc_info():
    """
    Convenience wrapper around serializeable_exc_info, equivalent to
    serializeable_exc_info(sys.exc_info()).
    """
    return serializeable_exc_info(*sys.exc_info())

def format_exception(thetype, ex, tb):
    """
    This function is a drop-in replacement for Python's
    traceback.format_exception().

    Since traceback objects can not be pickled, Exscript is forced to
    manipulate them before they are passed accross process boundaries.
    This leads to the fact the Python's traceback.format_exception()
    no longer works for those objects.

    This function works with any traceback object, regardless of whether
    or not Exscript manipulated it.
    """
    if isinstance(tb, str):
        return tb
    return ''.join(traceback.format_exception(thetype, ex, tb))

def deprecation(msg):
    """
    Prints a deprecation warning.
    """
    warnings.warn('deprecated',
                  category   = DeprecationWarning,
                  stacklevel = 2)

def deprecated(func):
    """
    A decorator for marking functions as deprecated. Results in
    a printed warning message when the function is used.
    """
    def decorated(*args, **kwargs):
        warnings.warn('Call to deprecated function %s.' % func.__name__,
                      category   = DeprecationWarning,
                      stacklevel = 2)
        return func(*args, **kwargs)
    decorated.__name__ = func.__name__
    decorated.__doc__  = func.__doc__
    decorated.__dict__.update(func.__dict__)
    return decorated

def synchronized(func):
    """
    Decorator for synchronizing method access.
    """
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            rlock = self._sync_lock
        except AttributeError:
            from multiprocessing import RLock
            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        with rlock:
            return func(self, *args, **kwargs)
    return wrapped

def debug(func):
    """
    Decorator that prints a message whenever a function is entered or left.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        arg = repr(args) + ' ' + repr(kwargs)
        sys.stdout.write('Entering ' + func.__name__ + arg + '\n')
        try:
            result = func(*args, **kwargs)
        except:
            sys.stdout.write('Traceback caught:\n')
            sys.stdout.write(format_exception(*sys.exc_info()))
            raise
        arg = repr(result)
        sys.stdout.write('Leaving ' + func.__name__ + '(): ' + arg + '\n')
        return result
    return wrapped

class Decorator(object):
    def __init__(self, obj):
        self.__dict__['obj'] = obj

    def __setattr__(self, name, value):
        if name in self.__dict__.keys():
            self.__dict__[name] = value
        else:
            setattr(self.obj, name, value)

    def __getattr__(self, name):
        if name in self.__dict__.keys():
            return self.__dict__[name]
        return getattr(self.obj, name)

class _Context(Decorator):
    def __enter__(self):
        return self

    def __exit__(self, thetype, value, traceback):
        pass

class Context(_Context):
    def __exit__(self, thetype, value, traceback):
        return self.release()

    def context(self):
        return _Context(self)

########NEW FILE########
__FILENAME__ = interact
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Tools for interacting with the user on the command line.
"""
import os
import sys
import getpass
import ConfigParser
import shutil
from tempfile           import NamedTemporaryFile
from Exscript           import Account
from Exscript.util.cast import to_list

class InputHistory(object):
    """
    When prompting a user for input it is often useful to record his
    input in a file, and use previous input as a default value.
    This class allows for recording user input in a config file to
    allow for such functionality.
    """

    def __init__(self,
                 filename = '~/.exscript_history',
                 section  = os.path.basename(sys.argv[0])):
        """
        Constructor. The filename argument allows for listing on or
        more config files, and is passed to Python's RawConfigParser; please
        consult the documentation of RawConfigParser.read() if you require
        more information.
        The optional section argument allows to specify
        a section under which the input is stored in the config file.
        The section defaults to the name of the running script.

        Silently creates a tempfile if the given file can not be opened,
        such that the object behavior does not change, but the history
        is not remembered across instances.

        @type  filename: str|list(str)
        @param filename: The config file.
        @type  section: str
        @param section: The section in the configfile.
        """
        self.section = section
        self.parser  = ConfigParser.RawConfigParser()
        filename     = os.path.expanduser(filename)

        try:
            self.file = open(filename, 'a+')
        except IOError:
            import warnings
            warnings.warn('could not open %s, using tempfile' % filename)
            self.file = NamedTemporaryFile()

        self.parser.readfp(self.file)
        if not self.parser.has_section(self.section):
            self.parser.add_section(self.section)

    def get(self, key, default = None):
        """
        Returns the input with the given key from the section that was
        passed to the constructor. If either the section or the key
        are not found, the default value is returned.

        @type  key: str
        @param key: The key for which to return a value.
        @type  default: str|object
        @param default: The default value that is returned.
        @rtype:  str|object
        @return: The value from the config file, or the default.
        """
        if not self.parser:
            return default
        try:
            return self.parser.get(self.section, key)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def set(self, key, value):
        """
        Saves the input with the given key in the section that was
        passed to the constructor. If either the section or the key
        are not found, they are created.

        Does nothing if the given value is None.

        @type  key: str
        @param key: The key for which to define a value.
        @type  value: str|None
        @param value: The value that is defined, or None.
        @rtype:  str|None
        @return: The given value.
        """
        if value is None:
            return None

        self.parser.set(self.section, key, value)
        with NamedTemporaryFile(delete = False) as tmpfile:
            self.parser.write(tmpfile)

        self.file.close()
        shutil.move(tmpfile.name, self.file.name)
        self.file = open(self.file.name)
        return value

def prompt(key,
           message,
           default = None,
           strip   = True,
           check   = None,
           history = None):
    """
    Prompt the user for input. This function is similar to Python's built
    in raw_input, with the following differences:

        - You may specify a default value that is returned if the user
          presses "enter" without entering anything.
        - The user's input is recorded in a config file, and offered
          as the default value the next time this function is used
          (based on the key argument).

    The config file is based around the L{InputHistory}. If a history object
    is not passed in the history argument, a new one will be created.

    The key argument specifies under which name the input is saved in the
    config file.

    The given default value is only used if a default was not found in the
    history.

    The strip argument specifies that the returned value should be stripped
    of whitespace (default).

    The check argument allows for validating the input; if the validation
    fails, the user is prompted again before the value is stored in the
    InputHistory. Example usage::

        def validate(input):
            if len(input) < 4:
                return 'Please enter at least 4 characters!'
        value = prompt('test', 'Enter a value', 'My Default', check = validate)
        print 'You entered:', value

    This leads to the following output::

        Please enter a value [My Default]: abc
        Please enter at least 4 characters!
        Please enter a value [My Default]: Foobar
        You entered: Foobar

    The next time the same code is started, the input 'Foobar' is remembered::

        Please enter a value [Foobar]:        (enters nothing)
        You entered: Foobar

    @type  key: str
    @param key: The key under which to store the input in the L{InputHistory}.
    @type  message: str
    @param message: The user prompt.
    @type  default: str|None
    @param default: The offered default if none was found in the history.
    @type  strip: bool
    @param strip: Whether to remove whitespace from the input.
    @type  check: callable
    @param check: A function that is called for validating the input.
    @type  history: L{InputHistory}|None
    @param history: The history used for recording default values, or None.
    """
    if history is None:
        history = InputHistory()
    default = history.get(key, str(default))
    while True:
        if default is None:
            value = raw_input('%s: ' % message)
        else:
            value = raw_input('%s [%s]: ' % (message, default)) or default
        if strip:
            value = value.strip()
        if not check:
            break
        errors = check(value)
        if errors:
            print '\n'.join(to_list(errors))
        else:
            break
    history.set(key, value)
    return value

def get_filename(key, message, default = None, history = None):
    """
    Like L{prompt()}, but only accepts the name of an existing file
    as an input.

    @type  key: str
    @param key: The key under which to store the input in the L{InputHistory}.
    @type  message: str
    @param message: The user prompt.
    @type  default: str|None
    @param default: The offered default if none was found in the history.
    @type  history: L{InputHistory}|None
    @param history: The history used for recording default values, or None.
    """
    def _validate(string):
        if not os.path.isfile(string):
            return 'File not found. Please enter a filename.'
    return prompt(key, message, default, True, _validate, history)

def get_user():
    """
    Prompts the user for his login name, defaulting to the USER environment
    variable. Returns a string containing the username.
    May throw an exception if EOF is given by the user.

    @rtype:  string
    @return: A username.
    """
    # Read username and password.
    try:
        env_user = getpass.getuser()
    except KeyError:
        env_user = ''
    if env_user is None or env_user == '':
        user = raw_input('Please enter your user name: ')
    else:
        user = raw_input('Please enter your user name [%s]: ' % env_user)
        if user == '':
            user = env_user
    return user

def get_login():
    """
    Prompts the user for the login name using get_user(), and also asks for
    the password.
    Returns a tuple containing the username and the password.
    May throw an exception if EOF is given by the user.

    @rtype:  (string, string)
    @return: A tuple containing the username and the password.
    """
    user     = get_user()
    password = getpass.getpass('Please enter your password: ')
    return user, password

def read_login():
    """
    Like get_login(), but returns an Account object.

    @rtype:  Account
    @return: A new account.
    """
    user, password = get_login()
    return Account(user, password)

########NEW FILE########
__FILENAME__ = ip
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Wrapper around the ipv4 and ipv6 modules to handle both, ipv4 and ipv6.
"""
from Exscript.util import ipv4
from Exscript.util import ipv6

def is_ip(string):
    """
    Returns True if the given string is an IPv4 or IPv6 address, False
    otherwise.

    @type  string: string
    @param string: Any string.
    @rtype:  bool
    @return: True if the string is an IP address, False otherwise.
    """
    return ipv4.is_ip(string) or ipv6.is_ip(string)

def _call_func(funcname, ip, *args):
    if ipv4.is_ip(ip):
        return ipv4.__dict__[funcname](ip, *args)
    elif ipv6.is_ip(ip):
        return ipv6.__dict__[funcname](ip, *args)
    raise ValueError('neither ipv4 nor ipv6: ' + repr(ip))

def normalize_ip(ip):
    """
    Transform the address into a fixed-length form, such as:

        192.168.0.1 -> 192.168.000.001
        1234::A -> 1234:0000:0000:0000:0000:0000:0000:000a

    @type  ip: string
    @param ip: An IP address.
    @rtype:  string
    @return: The normalized IP.
    """
    return _call_func('normalize_ip', ip)

def clean_ip(ip):
    """
    Cleans the ip address up, useful for removing leading zeros, e.g.::

        192.168.010.001 -> 192.168.10.1
        1234:0000:0000:0000:0000:0000:0000:000A -> 1234::a

    @type  ip: string
    @param ip: An IP address.
    @rtype:  string
    @return: The cleaned up IP.
    """
    return _call_func('clean_ip', ip)

########NEW FILE########
__FILENAME__ = ipv4
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
IPv4 address calculation and conversion.
"""
import socket
import struct
import math
import re

def _least_bit(number):
    for i in range(0, 32):
        if number & (0x00000001l << i) != 0:
            return i
    return 32

def _highest_bit(number):
    if number == 0:
        return 0
    number -= 1
    number |= number >> 1
    number |= number >> 2
    number |= number >> 4
    number |= number >> 8
    number |= number >> 16
    number += 1
    return math.sqrt(number)

def is_ip(string):
    """
    Returns True if the given string is an IPv4 address, False otherwise.

    @type  string: string
    @param string: Any string.
    @rtype:  bool
    @return: True if the string is an IP address, False otherwise.
    """
    mo = re.match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', string)
    if mo is None:
        return False
    for group in mo.groups():
        if int(group) not in range(0, 256):
            return False
    return True

def normalize_ip(ip):
    """
    Transform the address into a fixed-length form, such as:

        192.168.0.1 -> 192.168.000.001

    @type  ip: string
    @param ip: An IP address.
    @rtype:  string
    @return: The normalized IP.
    """
    theip = ip.split('.')
    if len(theip) != 4:
        raise ValueError('ip should be 4 tuples')
    return '.'.join(str(int(l)).rjust(3, '0') for l in theip)

def clean_ip(ip):
    """
    Cleans the ip address up, useful for removing leading zeros, e.g.::

        192.168.010.001 -> 192.168.10.1

    @type  ip: string
    @param ip: An IP address.
    @rtype:  string
    @return: The cleaned up IP.
    """
    return '.'.join(str(int(i)) for i in ip.split('.'))

def ip2int(ip):
    """
    Converts the given IP address to a 4 byte integer value.

    @type  ip: string
    @param ip: An IP address.
    @rtype:  long
    @return: The IP, converted to a number.
    """
    if ip == '255.255.255.255':
        return 0xFFFFFFFFl
    return struct.unpack('!L', socket.inet_aton(ip))[0]

def int2ip(number):
    """
    Converts the given integer value to an IP address.

    @type  number: long
    @param number: An IP as a number.
    @rtype:  string
    @return: The IP address.
    """
    number &= 0xFFFFFFFFl
    return socket.inet_ntoa(struct.pack('!L', number))

def pfxlen2mask_int(pfxlen):
    """
    Converts the given prefix length to an IP mask value.

    @type  pfxlen: int
    @param pfxlen: A prefix length.
    @rtype:  long
    @return: The mask, as a long value.
    """
    return 0xFFFFFFFFl << (32 - int(pfxlen))

def pfxlen2mask(pfxlen):
    """
    Converts the given prefix length to an IP mask.

    @type  pfxlen: int
    @param pfxlen: A prefix length.
    @rtype:  string
    @return: The mask.
    """
    return int2ip(pfxlen2mask_int(pfxlen))

def mask2pfxlen(mask):
    """
    Converts the given IP mask to a prefix length.

    @type  mask: string
    @param mask: An IP mask.
    @rtype:  long
    @return: The mask, as a long value.
    """
    return 32 - _least_bit(ip2int(mask))

def parse_prefix(prefix, default_length = 24):
    """
    Splits the given IP prefix into a network address and a prefix length.
    If the prefix does not have a length (i.e., it is a simple IP address),
    it is presumed to have the given default length.

    @type  prefix: string
    @param prefix: An IP mask.
    @type  default_length: long
    @param default_length: The default ip prefix length.
    @rtype:  string, int
    @return: A tuple containing the IP address and prefix length.
    """
    if '/' in prefix:
        network, pfxlen = prefix.split('/')
    else:
        network = prefix
        pfxlen  = default_length
    return network, int(pfxlen)

def network(prefix, default_length = 24):
    """
    Given a prefix, this function returns the corresponding network
    address.

    @type  prefix: string
    @param prefix: An IP prefix.
    @type  default_length: long
    @param default_length: The default ip prefix length.
    @rtype:  string
    @return: The IP network address.
    """
    address, pfxlen = parse_prefix(prefix, default_length)
    ip              = ip2int(address)
    return int2ip(ip & pfxlen2mask_int(pfxlen))

def broadcast(prefix, default_length = 24):
    """
    Given a prefix, this function returns the corresponding broadcast
    address.

    @type  prefix: string
    @param prefix: An IP prefix.
    @type  default_length: long
    @param default_length: The default ip prefix length.
    @rtype:  string
    @return: The IP broadcast address.
    """
    address, pfxlen = parse_prefix(prefix, default_length)
    ip              = ip2int(address)
    return int2ip(ip | ~pfxlen2mask_int(pfxlen))

def remote_ip(local_ip):
    """
    Given an IP address, this function calculates the remaining available
    IP address under the assumption that it is a /30 network.
    In other words, given one link net address, this function returns the
    other link net address.

    @type  local_ip: string
    @param local_ip: An IP address.
    @rtype:  string
    @return: The other IP address of the link address pair.
    """
    local_ip = ip2int(local_ip)
    network  = local_ip & pfxlen2mask_int(30)
    return int2ip(network + 3 - (local_ip - network))

def sort(iterable):
    """
    Given an IP address list, this function sorts the list.

    @type  iterable: Iterator
    @param iterable: An IP address list.
    @rtype:  list
    @return: The sorted IP address list.
    """
    ips = sorted(normalize_ip(ip) for ip in iterable)
    return [clean_ip(ip) for ip in ips]

########NEW FILE########
__FILENAME__ = ipv6
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
IPv6 address calculation and conversion.
"""

def is_ip(string):
    """
    Returns True if the given string is an IPv6 address, False otherwise.

    @type  string: string
    @param string: Any string.
    @rtype:  bool
    @return: True if the string is an IP address, False otherwise.
    """
    try:
        normalize_ip(string)
    except ValueError:
        return False
    return True

def normalize_ip(ip):
    """
    Transform the address into a standard, fixed-length form, such as:

        1234:0:01:02:: -> 1234:0000:0001:0002:0000:0000:0000:0000
        1234::A -> 1234:0000:0000:0000:0000:0000:0000:000a

    @type  ip: string
    @param ip: An IP address.
    @rtype:  string
    @return: The normalized IP.
    """
    theip = ip
    if theip.startswith('::'):
        theip = '0' + theip
    if theip.endswith('::'):
        theip += '0'
    segments = theip.split(':')
    if len(segments) == 1:
        raise ValueError('no colons in ipv6 address: ' + repr(ip))
    fill = 8 - len(segments)
    if fill < 0:
        raise ValueError('ipv6 address has too many segments: ' + repr(ip))
    result = []
    for segment in segments:
        if segment == '':
            if fill == 0:
                raise ValueError('unexpected double colon: ' + repr(ip))
            for n in range(fill + 1):
                result.append('0000')
            fill = 0
        else:
            try:
                int(segment, 16)
            except ValueError:
                raise ValueError('invalid hex value in ' + repr(ip))
            result.append(segment.rjust(4, '0'))
    return ':'.join(result).lower()

def clean_ip(ip):
    """
    Cleans the ip address up, useful for removing leading zeros, e.g.::

        1234:0:01:02:: -> 1234:0:1:2::
        1234:0000:0000:0000:0000:0000:0000:000A -> 1234::a
        1234:0000:0000:0000:0001:0000:0000:0000 -> 1234:0:0:0:1::
        0000:0000:0000:0000:0001:0000:0000:0000 -> ::1:0:0:0

    @type  ip: string
    @param ip: An IP address.
    @rtype:  string
    @return: The cleaned up IP.
    """
    theip    = normalize_ip(ip)
    segments = ['%x' % int(s, 16) for s in theip.split(':')]

    # Find the longest consecutive sequence of zeroes.
    seq      = {0: 0}
    start    = None
    count    = 0
    for n, segment in enumerate(segments):
        if segment != '0':
            start = None
            count = 0
            continue
        if start is None:
            start = n
        count += 1
        seq[count] = start

    # Replace those zeroes by a double colon.
    count  = max(seq)
    start  = seq[count]
    result = []
    for n, segment in enumerate(segments):
        if n == start and count > 1:
            if n == 0:
                result.append('')
            result.append('')
            if n == 7:
                result.append('')
            continue
        elif start < n < start + count:
            if n == 7:
                result.append('')
            continue
        result.append(segment)
    return ':'.join(result)

def parse_prefix(prefix, default_length = 128):
    """
    Splits the given IP prefix into a network address and a prefix length.
    If the prefix does not have a length (i.e., it is a simple IP address),
    it is presumed to have the given default length.

    @type  prefix: string
    @param prefix: An IP mask.
    @type  default_length: long
    @param default_length: The default ip prefix length.
    @rtype:  string, int
    @return: A tuple containing the IP address and prefix length.
    """
    if '/' in prefix:
        network, pfxlen = prefix.split('/')
    else:
        network = prefix
        pfxlen  = default_length
    return network, int(pfxlen)

########NEW FILE########
__FILENAME__ = log
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Logging utilities.
"""
from Exscript.FileLogger import FileLogger
from Exscript.util.impl import add_label

_loggers = []

def log_to(logger):
    """
    Wraps a function that has a connection passed such that everything that
    happens on the connection is logged using the given logger.

    @type  logger: Logger
    @param logger: The logger that handles the logging.
    """
    logger_id = id(logger)
    def decorator(function):
        func = add_label(function, 'log_to', logger_id = logger_id)
        return func
    return decorator

def log_to_file(logdir, mode = 'a', delete = False, clearmem = True):
    """
    Like L{log_to()}, but automatically creates a new FileLogger
    instead of having one passed.
    Note that the logger stays alive (in memory) forever. If you need
    to control the lifetime of a logger, use L{log_to()} instead.
    """
    logger = FileLogger(logdir, mode, delete, clearmem)
    _loggers.append(logger)
    return log_to(logger)

########NEW FILE########
__FILENAME__ = mail
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Sending and formatting emails.
"""
import time
import re
import socket
import smtplib
import mimetypes
from getpass              import getuser
from email                import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.audio     import MIMEAudio
from email.mime.base      import MIMEBase
from email.mime.image     import MIMEImage
from email.mime.text      import MIMEText
from Exscript.util.event  import Event

###########################################################
# Helpers. (non-public)
###########################################################
_varname_re = re.compile(r'[a-z][\w_]*',     re.I)
_string_re  = re.compile(r'(\\?){([\w_]+)}', re.I)

class _TemplateParser(object):
    """
    This exists for backward compatibility; Python 2.3 does not come
    with a similar way for string substitution yet.
    """
    def __init__(self):
        self.tmpl_vars = None

    # Tokens that include variables in a string may use this callback to
    # substitute the variable against its value.
    def _variable_sub_cb(self, match):
        escape  = match.group(1)
        varname = match.group(2)
        if escape == '\\':
            return '$' + varname
        if not _varname_re.match(varname):
            raise Exception('%s is not a variable name' % varname)
        value = self.tmpl_vars.get(varname)
        if value is None:
            raise Exception('Undefined value for %s' % varname)
        elif hasattr(value, '__iter__'):
            value = '\n'.join([str(v) for v in value])
        return str(value)

    def parse(self, template, **kwargs):
        self.tmpl_vars = kwargs
        output         = ''
        for line in template.split('\n'):
            if line.endswith(' '):
                output += line
            else:
                output += line + '\n'
        return _string_re.sub(self._variable_sub_cb, output)

def _render_template(string, **vars):
    default = {'date': time.strftime('%Y-%m-%d'),
               'user': getuser()}
    default.update(vars)
    parser = _TemplateParser()
    return parser.parse(string, **default)

def _is_header_line(line):
    return re.match(r'^\w+: .+$', line) is not None

def _get_var_from_header_line(line):
    match = re.match(r'^(\w+): (.+)$', line)
    return match.group(1).strip().lower(), match.group(2).strip()

def _cleanup_mail_addresses(receipients):
    if not isinstance(receipients, str):
        receipients = ','.join(receipients)
    rcpt = re.split(r'\s*[,;]\s*', receipients.lower())
    return [r for r in rcpt if r.strip()]

###########################################################
# Public.
###########################################################
class Mail(object):
    """
    Represents an email.
    """

    def __init__(self,
                 sender  = None,
                 to      = '',
                 cc      = '',
                 bcc     = '',
                 subject = '',
                 body    = ''):
        """
        Creates a new email with the given values.
        If the given sender is None, one will be automatically chosen
        using getpass.getuser().

        @type  sender: string
        @param sender: The email address of the sender.
        @type  to: string|list(string)
        @param to: A list of email addresses, passed to set_to().
        @type  cc: string|list(string)
        @param cc: A list of email addresses, passed to set_cc().
        @type  bcc: string|list(string)
        @param bcc: A list of email addresses, passed to set_bcc().
        @type  subject: string
        @param subject: A subject line, passed to set_subject().
        @type  body: string
        @param body: The email body, passed to set_body().
        """
        self.changed_event = Event()
        self.files         = []
        self.sender        = None
        self.cc            = None
        self.bcc           = None
        self.to            = None
        self.subject       = None
        self.body          = None
        if not sender:
            domain = socket.getfqdn('localhost')
            sender = getuser() + '@' + domain
        self.set_sender(sender)
        self.set_to(to)
        self.set_cc(cc)
        self.set_bcc(bcc)
        self.set_subject(subject)
        self.set_body(body)

    def set_from_template_string(self, string):
        """
        Reads the given template (SMTP formatted) and sets all fields
        accordingly.

        @type  string: string
        @param string: The template.
        """
        in_header = True
        body      = ''
        for line in string.split('\n'):
            if not in_header:
                body += line + '\n'
                continue
            if not _is_header_line(line):
                body += line + '\n'
                in_header = False
                continue
            key, value = _get_var_from_header_line(line)
            if key == 'from':
                self.set_sender(value)
            elif key == 'to':
                self.add_to(value)
            elif key == 'cc':
                self.add_cc(value)
            elif key == 'bcc':
                self.add_bcc(value)
            elif key == 'subject':
                self.set_subject(value)
            else:
                raise Exception('Invalid header field "%s"' % key)
        self.set_body(body.strip())

    def set_sender(self, sender):
        """
        Defines the value of the "From:" field.

        @type  sender: string
        @param sender: The email address of the sender.
        """
        self.sender = sender
        self.changed_event()

    def get_sender(self):
        """
        Returns the value of the "From:" field.

        @rtype:  string
        @return: The email address of the sender.
        """
        return self.sender

    def set_to(self, to):
        """
        Replaces the current list of receipients in the 'to' field by
        the given value. The value may be one of the following:

          - A list of strings (email addresses).
          - A comma separated string containing one or more email addresses.

        @type  to: string|list(string)
        @param to: The email addresses for the 'to' field.
        """
        self.to = _cleanup_mail_addresses(to)
        self.changed_event()

    def add_to(self, to):
        """
        Adds the given list of receipients to the 'to' field.
        Accepts the same argument types as set_to().

        @type  to: string|list(string)
        @param to: The list of email addresses.
        """
        self.to += _cleanup_mail_addresses(to)
        self.changed_event()

    def get_to(self):
        """
        Returns the value of the "to" field.

        @rtype:  list(string)
        @return: The email addresses in the 'to' field.
        """
        return self.to

    def set_cc(self, cc):
        """
        Like set_to(), but for the 'cc' field.

        @type  cc: string|list(string)
        @param cc: The email addresses for the 'cc' field.
        """
        self.cc = _cleanup_mail_addresses(cc)
        self.changed_event()

    def add_cc(self, cc):
        """
        Like add_to(), but for the 'cc' field.

        @type  cc: string|list(string)
        @param cc: The list of email addresses.
        """
        self.cc += _cleanup_mail_addresses(cc)
        self.changed_event()

    def get_cc(self):
        """
        Returns the value of the "cc" field.

        @rtype:  list(string)
        @return: The email addresses in the 'cc' field.
        """
        return self.cc

    def set_bcc(self, bcc):
        """
        Like set_to(), but for the 'bcc' field.

        @type  bcc: string|list(string)
        @param bcc: The email addresses for the 'bcc' field.
        """
        self.bcc = _cleanup_mail_addresses(bcc)
        self.changed_event()

    def add_bcc(self, bcc):
        """
        Like add_to(), but for the 'bcc' field.

        @type  bcc: string|list(string)
        @param bcc: The list of email addresses.
        """
        self.bcc += _cleanup_mail_addresses(bcc)
        self.changed_event()

    def get_bcc(self):
        """
        Returns the value of the "bcc" field.

        @rtype:  list(string)
        @return: The email addresses in the 'bcc' field.
        """
        return self.bcc

    def get_receipients(self):
        """
        Returns a list of all receipients (to, cc, and bcc).

        @rtype:  list(string)
        @return: The email addresses of all receipients.
        """
        return self.get_to() + self.get_cc() + self.get_bcc()

    def set_subject(self, subject):
        """
        Defines the subject line.

        @type  subject: string
        @param subject: The new subject line.
        """
        self.subject = subject
        self.changed_event()

    def get_subject(self):
        """
        Returns the subject line.

        @rtype:  string
        @return: The subject line.
        """
        return self.subject

    def set_body(self, body):
        """
        Defines the body of the mail.

        @type  body: string
        @param body: The new email body.
        """
        self.body = body
        self.changed_event()

    def get_body(self):
        """
        Returns the body of the mail.

        @rtype:  string
        @return: The body of the mail.
        """
        return self.body

    def get_smtp_header(self):
        """
        Returns the SMTP formatted header of the line.

        @rtype:  string
        @return: The SMTP header.
        """
        header  = "From: %s\r\n"    % self.get_sender()
        header += "To: %s\r\n"      % ',\r\n '.join(self.get_to())
        header += "Cc: %s\r\n"      % ',\r\n '.join(self.get_cc())
        header += "Bcc: %s\r\n"     % ',\r\n '.join(self.get_bcc())
        header += "Subject: %s\r\n" % self.get_subject()
        return header

    def get_smtp_mail(self):
        """
        Returns the SMTP formatted email, as it may be passed to sendmail.

        @rtype:  string
        @return: The SMTP formatted mail.
        """
        header = self.get_smtp_header()
        body   = self.get_body().replace('\n', '\r\n')
        return header + '\r\n' + body + '\r\n'

    def add_attachment(self, filename):
        """
        Adds the file with the given name as an attachment.

        @type  filename: string
        @param filename: A filename.
        """
        self.files.append(filename)

    def get_attachments(self):
        """
        Returns a list of attached files.

        @rtype:  list[string]
        @return: The list of filenames.
        """
        return self.files


def from_template_string(string, **kwargs):
    """
    Reads the given SMTP formatted template, and creates a new Mail object
    using the information.

    @type  string: str
    @param string: The SMTP formatted template.
    @type  kwargs: str
    @param kwargs: Variables to replace in the template.
    @rtype:  Mail
    @return: The resulting mail.
    """
    tmpl = _render_template(string, **kwargs)
    mail = Mail()
    mail.set_from_template_string(tmpl)
    return mail

def from_template(filename, **kwargs):
    """
    Like from_template_string(), but reads the template from the file with
    the given name instead.

    @type  filename: string
    @param filename: The name of the template file.
    @type  kwargs: str
    @param kwargs: Variables to replace in the template.
    @rtype:  Mail
    @return: The resulting mail.
    """
    tmpl = open(filename).read()
    return from_template_string(tmpl, **kwargs)

def _get_mime_object(filename):
    # Guess the content type based on the file's extension.  Encoding
    # is ignored, although we should check for simple things like
    # gzip'd or compressed files.
    ctype, encoding = mimetypes.guess_type(filename)
    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'

    maintype, subtype = ctype.split('/', 1)
    if maintype == 'text':
        fp  = open(filename)
        msg = MIMEText(fp.read(), _subtype = subtype)
    elif maintype == 'image':
        fp  = open(filename, 'rb')
        msg = MIMEImage(fp.read(), _subtype = subtype)
    elif maintype == 'audio':
        fp  = open(filename, 'rb')
        msg = MIMEAudio(fp.read(), _subtype = subtype)
    else:
        fp  = open(filename, 'rb')
        msg = MIMEBase(maintype, subtype)
        msg.set_payload(fp.read())
        encoders.encode_base64(msg)
    fp.close()

    # Set the filename parameter
    msg.add_header('Content-Disposition', 'attachment', filename = filename)
    return msg

def send(mail, server = 'localhost'):
    """
    Sends the given mail.

    @type  mail: Mail
    @param mail: The mail object.
    @type  server: string
    @param server: The address of the mailserver.
    """
    sender             = mail.get_sender()
    rcpt               = mail.get_receipients()
    session            = smtplib.SMTP(server)
    message            = MIMEMultipart()
    message['Subject'] = mail.get_subject()
    message['From']    = mail.get_sender()
    message['To']      = ', '.join(mail.get_to())
    message['Cc']      = ', '.join(mail.get_cc())
    message.preamble   = 'Your mail client is not MIME aware.'

    body = MIMEText(mail.get_body())
    body.add_header('Content-Disposition', 'inline')
    message.attach(body)

    for filename in mail.get_attachments():
        message.attach(_get_mime_object(filename))

    session.sendmail(sender, rcpt, message.as_string())

########NEW FILE########
__FILENAME__ = match
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Shorthands for regular expression matching.
"""
import re
from Exscript.protocols import Protocol

def _first_match(string, compiled):
    match = compiled.search(string)
    if match is None and compiled.groups <= 1:
        return None
    elif match is None:
        return (None,) * compiled.groups
    elif compiled.groups == 0:
        return string
    elif compiled.groups == 1:
        return match.groups(1)[0]
    else:
        return match.groups(0)

def first_match(string, regex, flags = re.M):
    """
    Matches the given string against the given regex.

      - If no match is found and the regular expression has zero or one
      groups, this function returns None.

      - If no match is found and the regular expression has more than one
      group, this function returns a tuple of None. The number of elements
      in the tuple equals the number of groups in the regular expression.

      - If a match is found and the regular expression has no groups,
      the entire string is returned.

      - If a match is found and the regular expression has one group,
      the matching string from the group is returned.

      - If a match is found and the regular expression has multiple groups,
      a tuple containing the matching strings from the groups is returned.

    This behavior ensures that the following assignments can never fail::

       foo   = 'my test'
       match = first_match(foo, r'aaa')         # Returns None
       match = first_match(foo, r'\S+')         # Returns 'my test'
       match = first_match(foo, r'(aaa)')       # Returns None
       match = first_match(foo, r'(\S+)')       # Returns 'my'
       match = first_match(foo, r'(aaa) (\S+)') # Returns (None, None)
       match = first_match(foo, r'(\S+) (\S+)') # Returns ('my', 'foo')

    @type  string: string|Exscript.protocols.Protocol
    @param string: The string that is matched, or a Protocol object.
    @type  regex: string
    @param regex: A regular expression.
    @type  flags: int
    @param flags: The flags for compiling the regex; e.g. re.I
    @rtype:  string|tuple
    @return: A match, or a tuple of matches.
    """
    if isinstance(string, Protocol):
        string = string.response
    return _first_match(string, re.compile(regex, flags))

def any_match(string, regex, flags = re.M):
    """
    Matches the given string against the given regex.

      - If no match is found, this function returns an empty list.

      - If a match is found and the regular expression has no groups,
      a list of matching lines returned.

      - If a match is found and the regular expression has one group,
      a list of matching strings is returned.

      - If a match is found and the regular expression has multiple groups,
      a list containing tuples of matching strings is returned.

    This behavior ensures that the following can never fail::

        foo = '1 uno\\n2 due'
        for m in any_match(foo, r'aaa'):         # Returns []
            print m

        for m in any_match(foo, r'\S+'):         # Returns ['1 uno', '2 due']
            print m

        for m in any_match(foo, r'(aaa)'):       # Returns []
            print m

        for m in any_match(foo, r'(\S+)'):       # Returns ['1', '2']
            print m

        for one, two in any_match(foo, r'(aaa) (\S+)'): # Returns []
            print m

        for one, two in any_match(foo, r'(\S+) (\S+)'): # Returns [('1', 'uno'), ('2', 'due')]
            print m

    @type  string: string|Exscript.protocols.Protocol
    @param string: The string that is matched, or a Protocol object.
    @type  regex: string
    @param regex: A regular expression.
    @type  flags: int
    @param flags: The flags for compiling the regex; e.g. re.I
    @rtype:  list[string|tuple]
    @return: A list of strings, or a list of tuples.
    """
    if isinstance(string, Protocol):
        string = string.response
    compiled = re.compile(regex, flags)
    results  = []
    if compiled.groups <= 1:
        for line in string.split('\n'):
            match = _first_match(line, compiled)
            if match is None:
                continue
            results.append(match)
    else:
        for line in string.split('\n'):
            match = _first_match(line, compiled)
            if match[0] is None:
                continue
            results.append(match)
    return results

########NEW FILE########
__FILENAME__ = pidutil
# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Handling PID (process id) files.
"""
import os
import logging
import fcntl
import errno

def read(path):
    """
    Returns the process id from the given file if it exists, or None
    otherwise. Raises an exception for all other types of OSError
    while trying to access the file.

    @type  path: str
    @param path: The name of the pidfile.
    @rtype:  int or None
    @return: The PID, or none if the file was not found.
    """
    # Try to read the pid from the pidfile.
    logging.info("Checking pidfile '%s'", path)
    try:
        return int(open(path).read())
    except IOError, (code, text):
        if code == errno.ENOENT: # no such file or directory
            return None
        raise

def isalive(path):
    """
    Returns True if the file with the given name contains a process
    id that is still alive.
    Returns False otherwise.

    @type  path: str
    @param path: The name of the pidfile.
    @rtype:  bool
    @return: Whether the process is alive.
    """
    # try to read the pid from the pidfile
    pid = read(path)
    if pid is None:
        return False

    # Check if a process with the given pid exists.
    try:
        os.kill(pid, 0) # Signal 0 does not kill, but check.
    except OSError, (code, text):
        if code == errno.ESRCH: # No such process.
            return False
    return True

def kill(path):
    """
    Kills the process, if it still exists.

    @type  path: str
    @param path: The name of the pidfile.
    """
    # try to read the pid from the pidfile
    pid = read(path)
    if pid is None:
        return

    # Try to kill the process.
    logging.info("Killing PID %s", pid)
    try:
        os.kill(pid, 9)
    except OSError, (code, text):
        # re-raise if the error wasn't "No such process"
        if code != errno.ESRCH:
            raise

def write(path):
    """
    Writes the current process id to the given pidfile.

    @type  path: str
    @param path: The name of the pidfile.
    """
    pid = os.getpid()
    logging.info("Writing PID %s to '%s'", pid, path)
    try:
        pidfile = open(path, 'wb')
        # get a non-blocking exclusive lock
        fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # clear out the file
        pidfile.seek(0)
        pidfile.truncate(0)
        # write the pid
        pidfile.write(str(pid))
    finally:
        try:
            pidfile.close()
        except:
            pass

def remove(path):
    """
    Deletes the pidfile if it exists.

    @type  path: str
    @param path: The name of the pidfile.
    """
    logging.info("Removing pidfile '%s'", path)
    try:
        os.unlink(path)
    except IOError:
        pass

########NEW FILE########
__FILENAME__ = report
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Formatting logs into human readable reports.
"""

def _underline(text, line = '-'):
    return [text, line * len(text)]

def status(logger):
    """
    Creates a one-line summary on the actions that were logged by the given
    Logger.

    @type  logger: Logger
    @param logger: The logger that recorded what happened in the queue.
    @rtype:  string
    @return: A string summarizing the status.
    """
    aborted   = logger.get_aborted_actions()
    succeeded = logger.get_succeeded_actions()
    total     = aborted + succeeded
    if total == 0:
        return 'No actions done'
    elif total == 1 and succeeded == 1:
        return 'One action done (succeeded)'
    elif total == 1 and succeeded == 0:
        return 'One action done (failed)'
    elif total == succeeded:
        return '%d actions total (all succeeded)' % total
    elif succeeded == 0:
        return '%d actions total (all failed)' % total
    else:
        msg = '%d actions total (%d failed, %d succeeded)'
        return msg % (total, aborted, succeeded)

def summarize(logger):
    """
    Creates a short summary on the actions that were logged by the given
    Logger.

    @type  logger: Logger
    @param logger: The logger that recorded what happened in the queue.
    @rtype:  string
    @return: A string summarizing the status of every performed task.
    """
    summary = []
    for log in logger.get_logs():
        thestatus = log.has_error() and log.get_error(False) or 'ok'
        name      = log.get_name()
        summary.append(name + ': ' + thestatus)
    return '\n'.join(summary)

def format(logger,
           show_successful = True,
           show_errors     = True,
           show_traceback  = True):
    """
    Prints a report of the actions that were logged by the given Logger.
    The report contains a list of successful actions, as well as the full
    error message on failed actions.

    @type  logger: Logger
    @param logger: The logger that recorded what happened in the queue.
    @rtype:  string
    @return: A string summarizing the status of every performed task.
    """
    output = []

    # Print failed actions.
    errors = logger.get_aborted_actions()
    if show_errors and errors:
        output += _underline('Failed actions:')
        for log in logger.get_aborted_logs():
            if show_traceback:
                output.append(log.get_name() + ':')
                output.append(log.get_error())
            else:
                output.append(log.get_name() + ': ' + log.get_error(False))
        output.append('')

    # Print successful actions.
    if show_successful:
        output += _underline('Successful actions:')
        for log in logger.get_succeeded_logs():
            output.append(log.get_name())
        output.append('')

    return '\n'.join(output).strip()

########NEW FILE########
__FILENAME__ = sigint
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A class for catching SIGINT, such that CTRL+c works.
"""
import os
import sys
import signal

class SigIntWatcher(object):
    """
    This class solves two problems with multithreaded programs in Python:

      - A signal might be delivered to any thread and
      - if the thread that gets the signal is waiting, the signal
        is ignored (which is a bug).

    This class forks and catches sigint for Exscript.

    The watcher is a concurrent process (not thread) that waits for a
    signal and the process that contains the threads.
    Works on Linux, Solaris, MacOS, and AIX. Known not to work
    on Windows.
    """
    def __init__(self):
        """
        Creates a child process, which returns. The parent
        process waits for a KeyboardInterrupt and then kills
        the child process.
        """
        try:
            self.child = os.fork()
        except AttributeError:  # platforms that don't have os.fork
            pass
        except RuntimeError:
            pass # prevent "not holding the import lock" on some systems.
        if self.child == 0:
            return
        else:
            self.watch()

    def watch(self):
        try:
            pid, status = os.wait()
        except KeyboardInterrupt:
            print '********** SIGINT RECEIVED - SHUTTING DOWN! **********'
            self.kill()
            sys.exit(1)
        sys.exit(status >> 8)

    def kill(self):
        try:
            os.kill(self.child, signal.SIGKILL)
        except OSError:
            pass

########NEW FILE########
__FILENAME__ = sigintcatcher
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
When imported, this module catches KeyboardInterrupt (SIGINT).
It is a convenience wrapper around sigint.SigIntWatcher()
such that all that is required for the change to take effect
is the following statement::

  import Exscript.util.sigintcatcher

Be warned that this way of importing breaks on some systems, because a
fork during an import may cause the following error::

  RuntimeError: not holding the import lock

So in general it is recommended to use the L{sigint.SigIntWatcher()}
class directly.
"""
from Exscript.util.sigint import SigIntWatcher
_watcher = SigIntWatcher()

########NEW FILE########
__FILENAME__ = start
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Quickstart methods for the Exscript queue.
"""
from Exscript import Queue
from Exscript.util.interact import read_login
from Exscript.util.decorator import autologin

def run(users, hosts, func, **kwargs):
    """
    Convenience function that creates an Exscript.Queue instance, adds
    the given accounts, and calls Queue.run() with the given
    hosts and function as an argument.

    If you also want to pass arguments to the given function, you may use
    util.decorator.bind() like this::

      def my_callback(job, host, conn, my_arg, **kwargs):
          print my_arg, kwargs.get('foo')

      run(account,
          host,
          bind(my_callback, 'hello', foo = 'world'),
          max_threads = 10)

    @type  users: Account|list[Account]
    @param users: The account(s) to use for logging in.
    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  kwargs: dict
    @param kwargs: Passed to the Exscript.Queue constructor.
    """
    queue = Queue(**kwargs)
    queue.add_account(users)
    queue.run(hosts, func)
    queue.destroy()

def quickrun(hosts, func, **kwargs):
    """
    A wrapper around run() that creates the account by asking the user
    for entering his login information.

    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  kwargs: dict
    @param kwargs: Passed to the Exscript.Queue constructor.
    """
    run(read_login(), hosts, func, **kwargs)

def start(users, hosts, func, **kwargs):
    """
    Like run(), but automatically logs into the host before passing
    the host to the callback function.

    @type  users: Account|list[Account]
    @param users: The account(s) to use for logging in.
    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  kwargs: dict
    @param kwargs: Passed to the Exscript.Queue constructor.
    """
    run(users, hosts, autologin()(func), **kwargs)

def quickstart(hosts, func, **kwargs):
    """
    Like quickrun(), but automatically logs into the host before passing
    the connection to the callback function.

    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  kwargs: dict
    @param kwargs: Passed to the Exscript.Queue constructor.
    """
    quickrun(hosts, autologin()(func), **kwargs)

########NEW FILE########
__FILENAME__ = syslog
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Send messages to a syslog server.
"""
import os
import sys
import imp
import socket

# This way of loading a module prevents Python from looking in the
# current directory. (We need to avoid it due to the syslog module
# name collision.)
syslog = imp.load_module('syslog', *imp.find_module('syslog'))

def netlog(message,
           source   = None,
           host     = 'localhost',
           port     = 514,
           priority = syslog.LOG_DEBUG,
           facility = syslog.LOG_USER):
    """
    Python's built in syslog module does not support networking, so
    this is the alternative.
    The source argument specifies the message source that is
    documented on the receiving server. It defaults to "scriptname[pid]",
    where "scriptname" is sys.argv[0], and pid is the current process id.
    The priority and facility arguments are equivalent to those of
    Python's built in syslog module.

    @type  source: str
    @param source: The source address.
    @type  host: str
    @param host: The IP address or hostname of the receiving server.
    @type  port: str
    @param port: The TCP port number of the receiving server.
    @type  priority: int
    @param priority: The message priority.
    @type  facility: int
    @param facility: The message facility.
    """
    if not source:
        source = '%s[%s]' + (sys.argv[0], os.getpid())
    data = '<%d>%s: %s' % (priority + facility, source, message)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, (host, port))
    sock.close()

########NEW FILE########
__FILENAME__ = template
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Executing Exscript templates on a connection.
"""
from Exscript             import stdlib
from Exscript.interpreter import Parser

def _compile(conn, filename, template, parser_kwargs, **kwargs):
    if conn:
        hostname = conn.get_host()
        account  = conn.last_account
        username = account is not None and account.get_name() or None
    else:
        hostname = 'undefined'
        username = None

    # Init the parser.
    parser = Parser(**parser_kwargs)
    parser.define(**kwargs)

    # Define the built-in variables and functions.
    builtin = dict(__filename__   = [filename or 'undefined'],
                   __username__   = [username],
                   __hostname__   = [hostname],
                   __connection__ = conn)
    parser.define_object(**builtin)
    parser.define_object(**stdlib.functions)

    # Compile the template.
    return parser.parse(template, builtin.get('__filename__')[0])

def _run(conn, filename, template, parser_kwargs, **kwargs):
    compiled = _compile(conn, filename, template, parser_kwargs, **kwargs)
    return compiled.execute()

def test(string, **kwargs):
    """
    Compiles the given template, and raises an exception if that
    failed. Does nothing otherwise.

    @type  string: string
    @param string: The template to compile.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    """
    _compile(None, None, string, {}, **kwargs)

def test_secure(string, **kwargs):
    """
    Like test(), but makes sure that each function that is used in
    the template has the Exscript.stdlib.util.safe_function decorator.
    Raises Exscript.interpreter.Exception.PermissionError if any
    function lacks the decorator.

    @type  string: string
    @param string: The template to compile.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    """
    _compile(None, None, string, {'secure': True}, **kwargs)

def test_file(filename, **kwargs):
    """
    Convenience wrapper around test() that reads the template from a file
    instead.

    @type  filename: string
    @param filename: The name of the template file.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    """
    _compile(None, filename, open(filename).read(), {}, **kwargs)

def eval(conn, string, strip_command = True, **kwargs):
    """
    Compiles the given template and executes it on the given
    connection.
    Raises an exception if the compilation fails.

    if strip_command is True, the first line of each response that is
    received after any command sent by the template is stripped. For
    example, consider the following template::

        ls -1{extract /(\S+)/ as filenames}
        {loop filenames as filename}
            touch $filename
        {end}

    If strip_command is False, the response, (and hence, the `filenames'
    variable) contains the following::

        ls -1
        myfile
        myfile2
        [...]

    By setting strip_command to True, the first line is ommitted.

    @type  conn: Exscript.protocols.Protocol
    @param conn: The connection on which to run the template.
    @type  string: string
    @param string: The template to compile.
    @type  strip_command: bool
    @param strip_command: Whether to strip the command echo from the response.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    @rtype:  dict
    @return: The variables that are defined after execution of the script.
    """
    parser_args = {'strip_command': strip_command}
    return _run(conn, None, string, parser_args, **kwargs)

def eval_file(conn, filename, strip_command = True, **kwargs):
    """
    Convenience wrapper around eval() that reads the template from a file
    instead.

    @type  conn: Exscript.protocols.Protocol
    @param conn: The connection on which to run the template.
    @type  filename: string
    @param filename: The name of the template file.
    @type  strip_command: bool
    @param strip_command: Whether to strip the command echo from the response.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    """
    template    = open(filename, 'r').read()
    parser_args = {'strip_command': strip_command}
    return _run(conn, filename, template, parser_args, **kwargs)

def paste(conn, string, **kwargs):
    """
    Compiles the given template and executes it on the given
    connection. This function differs from eval() such that it does not
    wait for a prompt after sending each command to the connected host.
    That means that the script can no longer read the response of the
    host, making commands such as `extract' or `set_prompt' useless.

    The function raises an exception if the compilation fails, or if
    the template contains a command that requires a response from the
    host.

    @type  conn: Exscript.protocols.Protocol
    @param conn: The connection on which to run the template.
    @type  string: string
    @param string: The template to compile.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    @rtype:  dict
    @return: The variables that are defined after execution of the script.
    """
    return _run(conn, None, string, {'no_prompt': True}, **kwargs)

def paste_file(conn, filename, **kwargs):
    """
    Convenience wrapper around paste() that reads the template from a file
    instead.

    @type  conn: Exscript.protocols.Protocol
    @param conn: The connection on which to run the template.
    @type  filename: string
    @param filename: The name of the template file.
    @type  kwargs: dict
    @param kwargs: Variables to define in the template.
    """
    template = open(filename, 'r').read()
    return _run(conn, None, template, {'no_prompt': True}, **kwargs)

########NEW FILE########
__FILENAME__ = tty
# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
TTY utilities.
"""
import os
import sys
import struct
from subprocess import Popen, PIPE

def _get_terminal_size(fd):
    try:
        import fcntl
        import termios
    except ImportError:
        return None
    s = struct.pack('HHHH', 0, 0, 0, 0)
    try:
        x = fcntl.ioctl(fd, termios.TIOCGWINSZ, s)
    except IOError: # Window size ioctl not supported.
        return None
    try:
        rows, cols, x_pixels, y_pixels = struct.unpack('HHHH', x)
    except struct.error:
        return None
    return rows, cols

def get_terminal_size(default_rows = 25, default_cols = 80):
    """
    Returns the number of lines and columns of the current terminal.
    It attempts several strategies to determine the size and if all fail,
    it returns (80, 25).

    @rtype:  int, int
    @return: The rows and columns of the terminal.
    """
    # Collect a list of viable input channels that may tell us something
    # about the terminal dimensions.
    fileno_list = []
    try:
        fileno_list.append(sys.stdout.fileno())
    except AttributeError:
        # Channel was redirected to an object that has no fileno()
        pass
    try:
        fileno_list.append(sys.stdin.fileno())
    except AttributeError:
        pass
    try:
        fileno_list.append(sys.stderr.fileno())
    except AttributeError:
        pass

    # Ask each channel for the terminal window size.
    for fd in fileno_list:
        try:
            rows, cols = _get_terminal_size(fd)
        except TypeError:
            # _get_terminal_size() returned None.
            pass
        else:
            return rows, cols

    # Try os.ctermid()
    try:
        fd = os.open(os.ctermid(), os.O_RDONLY)
    except AttributeError:
        # os.ctermid does not exist on Windows.
        pass
    except OSError:
        # The device pointed to by os.ctermid() does not exist.
        pass
    else:
        try:
            rows, cols = _get_terminal_size(fd)
        except TypeError:
            # _get_terminal_size() returned None.
            pass
        else:
            return rows, cols
        finally:
            os.close(fd)

    # Try `stty size`
    devnull = open(os.devnull, 'w')
    try:
        process = Popen(['stty', 'size'], stderr = devnull, stdout = PIPE)
    except OSError:
        pass
    else:
        errcode = process.wait()
        output  = process.stdout.read()
        devnull.close()
        try:
            rows, cols = output.split()
            return int(rows), int(cols)
        except (ValueError, TypeError):
            pass

    # Try environment variables.
    try:
        return tuple(int(os.getenv(var)) for var in ('LINES', 'COLUMNS'))
    except (ValueError, TypeError):
        pass

    # Give up.
    return default_rows, default_cols

########NEW FILE########
__FILENAME__ = url
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Working with URLs (as used in URL formatted hostnames).
"""
import re
from urllib      import urlencode, quote
from urlparse    import urlparse, urlsplit
from collections import defaultdict

def _make_hexmap():
    hexmap = dict()
    for i in range(256):
        hexmap['%02x' % i] = chr(i)
        hexmap['%02X' % i] = chr(i)
    return hexmap

_HEXTOCHR = _make_hexmap()

_WELL_KNOWN_PORTS = {
    'ftp':    21,
    'ssh':    22,
    'ssh1':   22,
    'ssh2':   22,
    'telnet': 23,
    'smtp':   25,
    'http':   80,
    'pop3':  110,
    'imap':  143
}

###############################################################
# utils
###############################################################
def _unquote(string):
    """_unquote('abc%20def') -> 'abc def'."""
    result = string.split('%')
    for i, item in enumerate(result[1:]):
        i += 1
        try:
            result[i] = _HEXTOCHR[item[:2]] + item[2:]
        except KeyError:
            result[i] = '%' + item
        except UnicodeDecodeError:
            result[i] = unichr(int(item[:2], 16)) + item[2:]
    return ''.join(result)

def _urlparse_qs(url):
    """
    Parse a URL query string and return the components as a dictionary.

    Based on the cgi.parse_qs method.This is a utility function provided
    with urlparse so that users need not use cgi module for
    parsing the url query string.

    Arguments:

      - url: URL with query string to be parsed
    """
    # Extract the query part from the URL.
    querystring = urlparse(url)[4]

    # Split the query into name/value pairs.
    pairs = [s2 for s1 in querystring.split('&') for s2 in s1.split(';')]

    # Split the name/value pairs.
    result = defaultdict(list)
    for name_value in pairs:
        pair = name_value.split('=', 1)
        if len(pair) != 2:
            continue

        if len(pair[1]) > 0:
            name  = _unquote(pair[0].replace('+', ' '))
            value = _unquote(pair[1].replace('+', ' '))
            result[name].append(value)

    return result

###############################################################
# public api
###############################################################
class Url(object):
    """
    Represents a URL.
    """
    def __init__(self):
        self.protocol  = None
        self.username  = None
        self.password1 = None
        self.password2 = None
        self.hostname  = None
        self.port      = None
        self.path      = None
        self.vars      = None

    def __str__(self):
        """
        Like L{to_string()}.

        @rtype:  str
        @return: A URL.
        """
        url = ''
        if self.protocol is not None:
            url += self.protocol + '://'
        if self.username is not None or \
           self.password1 is not None or \
           self.password2 is not None:
            if self.username is not None:
                url += quote(self.username, '')
            if self.password1 is not None or self.password2 is not None:
                url += ':'
            if self.password1 is not None:
                url += quote(self.password1, '')
            if self.password2 is not None:
                url += ':' + quote(self.password2, '')
            url += '@'
        url += self.hostname
        if self.port:
            url += ':' + str(self.port)
        if self.path:
            url += '/' + self.path

        if self.vars:
            pairs = []
            for key, values in self.vars.iteritems():
                for value in values:
                    pairs.append((key, value))
            url += '?' + urlencode(pairs)
        return url

    def to_string(self):
        """
        Returns the URL, including all attributes, as a string.

        @rtype:  str
        @return: A URL.
        """
        return str(self)

    @staticmethod
    def from_string(url, default_protocol = 'telnet'):
        """
        Parses the given URL and returns an URL object. There are some
        differences to Python's built-in URL parser:

          - It is less strict, many more inputs are accepted. This is
          necessary to allow for passing a simple hostname as a URL.
          - You may specify a default protocol that is used when the http://
          portion is missing.
          - The port number defaults to the well-known port of the given
          protocol.
          - The query variables are parsed into a dictionary (Url.vars).

        @type  url: string
        @param url: A URL.
        @type  default_protocol: string
        @param default_protocol: A protocol name.
        @rtype:  Url
        @return: The Url object contructed from the given URL.
        """
        if url is None:
            raise TypeError('Expected string but got' + type(url))

        # Extract the protocol name from the URL.
        result = Url()
        match  = re.match(r'(\w+)://', url)
        if match:
            result.protocol = match.group(1)
        else:
            result.protocol = default_protocol

        # Now remove the query from the url.
        query = ''
        if '?' in url:
            url, query = url.split('?', 1)
        result.vars = _urlparse_qs('http://dummy/?' + query)

        # Substitute the protocol name by 'http', because Python's urlsplit
        # fails on our protocol names otherwise.
        prefix = result.protocol + '://'
        if url.startswith(prefix):
            url = url[len(prefix):]
        url = 'http://' + url

        # Parse the remaining url.
        parsed = urlsplit(url, 'http', False)
        netloc = parsed[1]

        # Parse username and password.
        auth = ''
        if '@' in netloc:
            auth, netloc = netloc.split('@')
            auth = auth.split(':')
            try:
                result.username  = _unquote(auth[0])
                result.password1 = _unquote(auth[1])
                result.password2 = _unquote(auth[2])
            except IndexError:
                pass

        # Parse hostname and port number.
        result.hostname = netloc + parsed.path
        result.port     = _WELL_KNOWN_PORTS.get(result.protocol)
        if ':' in netloc:
            result.hostname, port = netloc.split(':')
            result.port           = int(port)

        return result

########NEW FILE########
__FILENAME__ = weakmethod
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Weak references to bound and unbound methods.
"""
import weakref

class DeadMethodCalled(Exception):
    """
    Raised by L{WeakMethod} if it is called when the referenced object
    is already dead.
    """
    pass

class WeakMethod(object):
    """
    Do not create this class directly; use L{ref()} instead.
    """
    __slots__ = 'name', 'callback'

    def __init__(self, name, callback):
        """
        Constructor. Do not use directly, use L{ref()} instead.
        """
        self.name     = name
        self.callback = callback

    def _dead(self, ref):
        if self.callback is not None:
            self.callback(self)

    def get_function(self):
        """
        Returns the referenced method/function if it is still alive.
        Returns None otherwise.

        @rtype:  callable|None
        @return: The referenced function if it is still alive.
        """
        raise NotImplementedError()

    def isalive(self):
        """
        Returns True if the referenced function is still alive, False
        otherwise.

        @rtype:  bool
        @return: Whether the referenced function is still alive.
        """
        return self.get_function() is not None

    def __call__(self, *args, **kwargs):
        """
        Proxied to the underlying function or method. Raises L{DeadMethodCalled}
        if the referenced function is dead.

        @rtype:  object
        @return: Whatever the referenced function returned.
        """
        method = self.get_function()
        if method is None:
            raise DeadMethodCalled('method called on dead object ' + self.name)
        method(*args, **kwargs)

class _WeakMethodBound(WeakMethod):
    __slots__ = 'name', 'callback', 'f', 'c'

    def __init__(self, f, callback):
        name = f.__self__.__class__.__name__ + '.' + f.__func__.__name__
        WeakMethod.__init__(self, name, callback)
        self.f = f.__func__
        self.c = weakref.ref(f.__self__, self._dead)

    def get_function(self):
        cls = self.c()
        if cls is None:
            return None
        return getattr(cls, self.f.__name__)

class _WeakMethodFree(WeakMethod):
    __slots__ = 'name', 'callback', 'f'

    def __init__(self, f, callback):
        WeakMethod.__init__(self, f.__class__.__name__, callback)
        self.f = weakref.ref(f, self._dead)

    def get_function(self):
        return self.f()

def ref(function, callback = None):
    """
    Returns a weak reference to the given method or function.
    If the callback argument is not None, it is called as soon
    as the referenced function is garbage deleted.

    @type  function: callable
    @param function: The function to reference.
    @type  callback: callable
    @param callback: Called when the function dies.
    """
    try:
        function.__func__
    except AttributeError:
        return _WeakMethodFree(function, callback)
    return _WeakMethodBound(function, callback)

########NEW FILE########
__FILENAME__ = version
"""
Warning: This file is automatically generated.
"""
__version__ = 'DEVELOPMENT'

########NEW FILE########
__FILENAME__ = DBPipeline
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import sqlalchemy as sa
from multiprocessing import Condition, RLock

def _transaction(function, *args, **kwargs):
    def wrapper(self, *args, **kwargs):
        with self.engine.contextual_connect(close_with_result = True).begin():
            return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    wrapper.__dict__ = function.__dict__
    wrapper.__doc__  = function.__doc__
    return wrapper

class DBPipeline(object):
    """
    Like L{Exscript.workqueue.Pipeline}, but keeps all queued objects
    in a database, instead of using in-memory data structures.
    """
    def __init__(self, engine, max_working = 1):
        self.condition     = Condition(RLock())
        self.engine        = engine
        self.max_working   = max_working
        self.running       = False
        self.paused        = False
        self.metadata      = sa.MetaData(self.engine)
        self._table_prefix = 'exscript_pipeline_'
        self._table_map    = {}
        self.__update_table_names()
        self.clear()

    def __add_table(self, table):
        """
        Adds a new table to the internal table list.
        
        @type  table: Table
        @param table: An sqlalchemy table.
        """
        pfx = self._table_prefix
        self._table_map[table.name[len(pfx):]] = table

    def __update_table_names(self):
        """
        Adds all tables to the internal table list.
        """
        pfx = self._table_prefix
        self.__add_table(sa.Table(pfx + 'job', self.metadata,
            sa.Column('id',     sa.Integer, primary_key = True),
            sa.Column('name',   sa.String(150), index = True),
            sa.Column('status', sa.String(50), index = True),
            sa.Column('job',    sa.PickleType()),
            mysql_engine = 'INNODB'
        ))

    @synchronized
    def install(self):
        """
        Installs (or upgrades) database tables.
        """
        self.metadata.create_all()

    @synchronized
    def uninstall(self):
        """
        Drops all tables from the database. Use with care.
        """
        self.metadata.drop_all()

    @synchronized
    def clear_database(self):
        """
        Drops the content of any database table used by this library.
        Use with care.

        Wipes out everything, including types, actions, resources and acls.
        """
        delete = self._table_map['job'].delete()
        delete.execute()

    def debug(self, debug = True):
        """
        Enable/disable debugging.

        @type  debug: bool
        @param debug: True to enable debugging.
        """
        self.engine.echo = debug

    def set_table_prefix(self, prefix):
        """
        Define a string that is prefixed to all table names in the database.

        @type  prefix: string
        @param prefix: The new prefix.
        """
        self._table_prefix = prefix
        self.__update_table_names()

    def get_table_prefix(self):
        """
        Returns the current database table prefix.
        
        @rtype:  string
        @return: The current prefix.
        """
        return self._table_prefix

    def __len__(self):
        return self._table_map['job'].count().execute().fetchone()[0]

    def __contains__(self, item):
        return self.has_id(id(item))

    def get_from_name(self, name):
        """
        Returns the item with the given name, or None if no such item
        is known.
        """
        with self.condition:
            tbl_j = self._table_map['job']
            query = tbl_j.select(tbl_j.c.name == name)
            row   = query.execute().fetchone()
            if row is None:
                return None
            return row.job

    def has_id(self, item_id):
        """
        Returns True if the queue contains an item with the given id.
        """
        tbl_j = self._table_map['job']
        query = tbl_j.select(tbl_j.c.id == item_id).count()
        return query.execute().fetchone()[0] > 0

    def task_done(self, item):
        with self.condition:
            self.working.remove(item)
            self.all.remove(id(item))
            self.condition.notify_all()

    def append(self, item):
        with self.condition:
            self.queue.append(item)
            self.all.add(id(item))
            self.condition.notify_all()

    def appendleft(self, item, force = False):
        with self.condition:
            if force:
                self.force.append(item)
            else:
                self.queue.appendleft(item)
            self.all.add(id(item))
            self.condition.notify_all()

    def prioritize(self, item, force = False):
        """
        Moves the item to the very left of the queue.
        """
        with self.condition:
            # If the job is already running (or about to be forced),
            # there is nothing to be done.
            if item in self.working or item in self.force:
                return
            self.queue.remove(item)
            self.appendleft(item, force)
            self.condition.notify_all()

    def clear(self):
        with self.condition:
            self.queue    = deque()
            self.force    = deque()
            self.sleeping = set()
            self.working  = set()
            self.all      = set()
            self.condition.notify_all()

    def stop(self):
        """
        Force the next() method to return while in another thread.
        The return value of next() will be None.
        """
        with self.condition:
            self.running = False
            self.condition.notify_all()

    def pause(self):
        with self.condition:
            self.paused = True
            self.condition.notify_all()

    def unpause(self):
        with self.condition:
            self.paused = False
            self.condition.notify_all()

    def sleep(self, item):
        assert id(item) in self.all
        with self.condition:
            self.sleeping.add(item)
            self.condition.notify_all()

    def wake(self, item):
        assert id(item) in self.all
        assert item in self.sleeping
        with self.condition:
            self.sleeping.remove(item)
            self.condition.notify_all()

    def wait_for_id(self, item_id):
        with self.condition:
            while self.has_id(item_id):
                self.condition.wait()

    def wait(self):
        """
        Waits for all currently running tasks to complete.
        """
        with self.condition:
            while self.working:
                self.condition.wait()

    def wait_all(self):
        """
        Waits for all queued and running tasks to complete.
        """
        with self.condition:
            while len(self) > 0:
                self.condition.wait()

    def with_lock(self, function, *args, **kwargs):
        with self.condition:
            return function(self, *args, **kwargs)

    def set_max_working(self, max_working):
        with self.condition:
            self.max_working = int(max_working)
            self.condition.notify_all()

    def get_max_working(self):
        return self.max_working

    def get_working(self):
        return list(self.working)

    def _popleft_sleeping(self):
        sleeping = []
        while True:
            try:
                node = self.queue[0]
            except IndexError:
                break
            if node not in self.sleeping:
                break
            sleeping.append(node)
            self.queue.popleft()
        return sleeping

    def _get_next(self):
        # We need to leave sleeping items in the queue because else we
        # would not know their original position after they wake up.
        # So we need to temporarily remove sleeping items from the top of
        # the queue here.
        sleeping = self._popleft_sleeping()

        # Get the first non-sleeping item from the queue.
        try:
            next = self.queue.popleft()
        except IndexError:
            next = None

        # Re-insert sleeping items.
        self.queue.extendleft(sleeping)
        return next

    def next(self):
        with self.condition:
            self.running = True
            while self.running:
                if self.paused:
                    self.condition.wait()
                    continue

                # Wait until enough slots are available.
                if len(self.working) - \
                   len(self.sleeping) - \
                   len(self.force) >= self.max_working:
                    self.condition.wait()
                    continue

                # Forced items are returned regardless of how many tasks
                # are already working.
                try:
                    next = self.force.popleft()
                except IndexError:
                    pass
                else:
                    self.working.add(next)
                    return next

                # Return the first non-sleeping task.
                next = self._get_next()
                if next is None:
                    self.condition.wait()
                    continue
                self.working.add(next)
                return next

########NEW FILE########
__FILENAME__ = Job
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import sys
import threading
import multiprocessing
from copy import copy
from functools import partial
from multiprocessing import Pipe
from Exscript.util.impl import serializeable_sys_exc_info

class _ChildWatcher(threading.Thread):
    def __init__(self, child, callback):
        threading.Thread.__init__(self)
        self.child = child
        self.cb    = callback

    def __copy__(self):
        watcher = _ChildWatcher(copy(self.child), self.cb)
        return watcher

    def run(self):
        to_child, to_self = Pipe()
        try:
            self.child.start(to_self)
            result = to_child.recv()
            self.child.join()
        except:
            result = sys.exc_info()
        finally:
            to_child.close()
            to_self.close()
        if result == '':
            self.cb(None)
        else:
            self.cb(result)

def _make_process_class(base, clsname):
    class process_cls(base):
        def __init__(self, id, function, name, data):
            base.__init__(self, name = name)
            self.id       = id
            self.pipe     = None
            self.function = function
            self.failures = 0
            self.data     = data

        def run(self):
            """
            Start the associated function.
            """
            try:
                self.function(self)
            except:
                self.pipe.send(serializeable_sys_exc_info())
            else:
                self.pipe.send('')
            finally:
                self.pipe = None

        def start(self, pipe):
            self.pipe = pipe
            base.start(self)
    process_cls.__name__ = clsname
    return process_cls

Thread = _make_process_class(threading.Thread, 'Thread')
Process = _make_process_class(multiprocessing.Process, 'Process')

class Job(object):
    __slots__ = ('id',
                 'func',
                 'name',
                 'times',
                 'failures',
                 'data',
                 'child',
                 'watcher')

    def __init__(self, function, name, times, data):
        self.id       = None
        self.func     = function
        self.name     = name is None and str(id(function)) or name
        self.times    = times
        self.failures = 0
        self.data     = data
        self.child    = None
        self.watcher  = None

    def start(self, child_cls, on_complete):
        self.child = child_cls(self.id, self.func, self.name, self.data)
        self.child.failures = self.failures
        self.watcher = _ChildWatcher(self.child, partial(on_complete, self))
        self.watcher.start()

    def join(self):
        self.watcher.join()
        self.child = None

########NEW FILE########
__FILENAME__ = MainLoop
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import threading
import multiprocessing
from Exscript.util.event import Event
from Exscript.workqueue.Job import Job

# See http://bugs.python.org/issue1731717
multiprocessing.process._cleanup = lambda: None

class MainLoop(threading.Thread):
    def __init__(self, collection, job_cls):
        threading.Thread.__init__(self)
        self.job_init_event      = Event()
        self.job_started_event   = Event()
        self.job_error_event     = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event   = Event()
        self.queue_empty_event   = Event()
        self.collection          = collection
        self.job_cls             = job_cls
        self.debug               = 5
        self.daemon              = True

    def _dbg(self, level, msg):
        if self.debug >= level:
            print msg

    def enqueue(self, function, name, times, data):
        job    = Job(function, name, times, data)
        job.id = self.collection.append(job)
        return job.id

    def enqueue_or_ignore(self, function, name, times, data):
        def conditional_append(queue):
            if queue.get_from_name(name) is not None:
                return None
            job    = Job(function, name, times, data)
            job.id = queue.append(job, name)
            return job.id
        return self.collection.with_lock(conditional_append)

    def priority_enqueue(self, function, name, force_start, times, data):
        job    = Job(function, name, times, data)
        job.id = self.collection.appendleft(job, name, force = force_start)
        return job.id

    def priority_enqueue_or_raise(self,
                                  function,
                                  name,
                                  force_start,
                                  times,
                                  data):
        def conditional_append(queue):
            job = queue.get_from_name(name)
            if job is None:
                job    = Job(function, name, times, data)
                job.id = queue.append(job, name)
                return job.id
            queue.prioritize(job, force = force_start)
            return None
        return self.collection.with_lock(conditional_append)

    def wait_for(self, job_id):
        self.collection.wait_for_id(job_id)

    def get_queue_length(self):
        return len(self.collection)

    def _on_job_completed(self, job, exc_info):
        # This function is called in a sub-thread, so we need to be
        # careful that we are not in a lock while sending an event.
        self._dbg(1, 'Job "%s" called completed()' % job.name)

        try:
            # Notify listeners of the error
            # *before* removing the job from the queue.
            # This is because wait_until_done() depends on
            # get_queue_length() being 0, and we don't want a listener
            # to get a signal from a queue that already already had
            # wait_until_done() completed.
            if exc_info:
                self._dbg(1, 'Error in job "%s"' % job.name)
                job.failures += 1
                self.job_error_event(job.child, exc_info)
                if job.failures >= job.times:
                    self._dbg(1, 'Job "%s" finally failed' % job.name)
                    self.job_aborted_event(job.child)
            else:
                self._dbg(1, 'Job "%s" succeeded.' % job.name)
                self.job_succeeded_event(job.child)

        finally:
            # Remove the watcher from the queue, and re-enque if needed.
            if exc_info and job.failures < job.times:
                self._dbg(1, 'Restarting job "%s"' % job.name)
                job.start(self.job_cls, self._on_job_completed)
                self.job_started_event(job.child)
            else:
                self.collection.task_done(job)

    def run(self):
        while True:
            # Get the next job from the queue. This blocks until a task
            # is available or until self.collection.stop() is called.
            job = self.collection.next()
            if len(self.collection) <= 0:
                self.queue_empty_event()
            if job is None:
                break  # self.collection.stop() was called.

            self.job_init_event(job)
            job.start(self.job_cls, self._on_job_completed)
            self.job_started_event(job.child)
            self._dbg(1, 'Job "%s" started.' % job.name)
        self._dbg(2, 'Main loop terminated.')

########NEW FILE########
__FILENAME__ = Pipeline
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from uuid import uuid4
from collections import deque
from multiprocessing import Condition, RLock

class Pipeline(object):
    """
    A collection that is similar to Python's Queue object, except
    it also tracks items that are currently sleeping or in progress.
    """
    def __init__(self, max_working = 1):
        self.condition   = Condition(RLock())
        self.max_working = max_working
        self.running     = True
        self.paused      = False
        self.queue       = None
        self.force       = None
        self.sleeping    = None
        self.working     = None
        self.item2id     = None
        self.id2item     = None # for performance reasons
        self.name2id     = None
        self.id2name     = None
        self.clear()

    def __len__(self):
        with self.condition:
            return len(self.id2item)

    def __contains__(self, item):
        with self.condition:
            return item in self.item2id

    def _register_item(self, name, item):
        uuid               = uuid4().hex
        self.id2item[uuid] = item
        self.item2id[item] = uuid
        if name is None:
            return uuid
        if name in self.name2id:
            msg = 'an item named %s is already queued' % repr(name)
            raise AttributeError(msg)
        self.name2id[name] = uuid
        self.id2name[uuid] = name
        return uuid

    def get_from_name(self, name):
        """
        Returns the item with the given name, or None if no such item
        is known.
        """
        with self.condition:
            try:
                item_id = self.name2id[name]
            except KeyError:
                return None
            return self.id2item[item_id]
        return None

    def has_id(self, item_id):
        """
        Returns True if the queue contains an item with the given id.
        """
        return item_id in self.id2item

    def task_done(self, item):
        with self.condition:
            try:
                self.working.remove(item)
            except KeyError:
                # This may happen if we receive a notification from a
                # thread that was previously enqueued, but then the
                # workqueue was forcefully stopped without waiting for
                # child threads to complete.
                self.condition.notify_all()
                return
            item_id = self.item2id.pop(item)
            self.id2item.pop(item_id)
            try:
                name = self.id2name.pop(item_id)
            except KeyError:
                pass
            else:
                self.name2id.pop(name)
            self.condition.notify_all()

    def append(self, item, name = None):
        """
        Adds the given item to the end of the pipeline.
        """
        with self.condition:
            self.queue.append(item)
            uuid = self._register_item(name, item)
            self.condition.notify_all()
            return uuid

    def appendleft(self, item, name = None, force = False):
        with self.condition:
            if force:
                self.force.append(item)
            else:
                self.queue.appendleft(item)
            uuid = self._register_item(name, item)
            self.condition.notify_all()
            return uuid

    def prioritize(self, item, force = False):
        """
        Moves the item to the very left of the queue.
        """
        with self.condition:
            # If the job is already running (or about to be forced),
            # there is nothing to be done.
            if item in self.working or item in self.force:
                return
            self.queue.remove(item)
            if force:
                self.force.append(item)
            else:
                self.queue.appendleft(item)
            self.condition.notify_all()

    def clear(self):
        with self.condition:
            self.queue    = deque()
            self.force    = deque()
            self.sleeping = set()
            self.working  = set()
            self.item2id  = dict()
            self.id2item  = dict()
            self.name2id  = dict()
            self.id2name  = dict()
            self.condition.notify_all()

    def stop(self):
        """
        Force the next() method to return while in another thread.
        The return value of next() will be None.
        """
        with self.condition:
            self.running = False
            self.condition.notify_all()

    def start(self):
        with self.condition:
            self.running = True
            self.condition.notify_all()

    def pause(self):
        with self.condition:
            self.paused = True
            self.condition.notify_all()

    def unpause(self):
        with self.condition:
            self.paused = False
            self.condition.notify_all()

    def sleep(self, item):
        with self.condition:
            self.sleeping.add(item)
            self.condition.notify_all()

    def wake(self, item):
        assert item in self.sleeping
        with self.condition:
            self.sleeping.remove(item)
            self.condition.notify_all()

    def wait_for_id(self, item_id):
        with self.condition:
            while self.has_id(item_id):
                self.condition.wait()

    def wait(self):
        """
        Waits for all currently running tasks to complete.
        """
        with self.condition:
            while self.working:
                self.condition.wait()

    def wait_all(self):
        """
        Waits for all queued and running tasks to complete.
        """
        with self.condition:
            while len(self) > 0:
                self.condition.wait()

    def with_lock(self, function, *args, **kwargs):
        with self.condition:
            return function(self, *args, **kwargs)

    def set_max_working(self, max_working):
        with self.condition:
            self.max_working = int(max_working)
            self.condition.notify_all()

    def get_max_working(self):
        return self.max_working

    def get_working(self):
        return list(self.working)

    def _popleft_sleeping(self):
        sleeping = []
        while True:
            try:
                node = self.queue[0]
            except IndexError:
                break
            if node not in self.sleeping:
                break
            sleeping.append(node)
            self.queue.popleft()
        return sleeping

    def _get_next(self, pop = True):
        # We need to leave sleeping items in the queue because else we
        # would not know their original position after they wake up.
        # So we need to temporarily remove sleeping items from the top of
        # the queue here.
        sleeping = self._popleft_sleeping()

        # Get the first non-sleeping item from the queue.
        if pop:
            try:
                next = self.queue.popleft()
            except IndexError:
                next = None
        else:
            try:
                next = self.queue[0]
            except IndexError:
                next = None

        # Re-insert sleeping items.
        self.queue.extendleft(sleeping)
        return next

    def try_next(self):
        """
        Like next(), but only returns the item that would be selected
        right now, without locking and without changing the queue.
        """
        with self.condition:
            try:
                return self.force[0]
            except IndexError:
                pass

            return self._get_next(False)

    def next(self):
        with self.condition:
            while self.running:
                if self.paused:
                    self.condition.wait()
                    continue

                # Wait until enough slots are available.
                if len(self.working) - \
                   len(self.sleeping) - \
                   len(self.force) >= self.max_working:
                    self.condition.wait()
                    continue

                # Forced items are returned regardless of how many tasks
                # are already working.
                try:
                    next = self.force.popleft()
                except IndexError:
                    pass
                else:
                    self.working.add(next)
                    return next

                # Return the first non-sleeping task.
                next = self._get_next()
                if next is None:
                    self.condition.wait()
                    continue
                self.working.add(next)
                return next
        return None

########NEW FILE########
__FILENAME__ = Task
# Copyright (C) 2007-2011 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Represents a batch of enqueued actions.
"""
from Exscript.util.event import Event

class Task(object):
    """
    Represents a batch of running actions.
    """
    def __init__(self, workqueue):
        self.done_event = Event()
        self.workqueue  = workqueue
        self.job_ids    = set()
        self.completed  = 0
        self.workqueue.job_succeeded_event.listen(self._on_job_done)
        self.workqueue.job_aborted_event.listen(self._on_job_done)

    def _on_job_done(self, job):
        if job.id not in self.job_ids:
            return
        self.completed += 1
        if self.is_completed():
            self.done_event()

    def is_completed(self):
        """
        Returns True if all actions in the task are completed, returns
        False otherwise.

        @rtype:  bool
        @return: Whether the task is completed.
        """
        return self.completed == len(self.job_ids)

    def wait(self):
        """
        Waits until all actions in the task have completed.
        Does not use any polling.
        """
        for theid in self.job_ids:
            self.workqueue.wait_for(theid)

    def add_job_id(self, theid):
        """
        Adds a job to the task.

        @type  theid: int
        @param theid: The id of the job.
        """
        self.job_ids.add(theid)

########NEW FILE########
__FILENAME__ = WorkQueue
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.util.event import Event
from Exscript.workqueue.Job import Thread, Process
from Exscript.workqueue.Pipeline import Pipeline
from Exscript.workqueue.MainLoop import MainLoop

class WorkQueue(object):
    """
    This class implements the asynchronous workqueue and is the main API
    for using the workqueue module.
    """
    def __init__(self,
                 collection = None,
                 debug = 0,
                 max_threads = 1,
                 mode = 'threading'):
        """
        Constructor.

        @type  debug: int
        @param debug: The debug level.
        @type  max_threads: int
        @param max_threads: The maximum number of concurrent threads.
        """
        if mode == 'threading':
            self.job_cls = Thread
        elif mode == 'multiprocessing':
            self.job_cls = Process
        else:
            raise TypeError('invalid "mode" argument: ' + repr(mode))
        if collection is None:
            self.collection = Pipeline(max_threads)
        else:
            self.collection = collection
            collection.set_max_working(max_threads)
        self.job_init_event      = Event()
        self.job_started_event   = Event()
        self.job_error_event     = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event   = Event()
        self.queue_empty_event   = Event()
        self.debug               = debug
        self.main_loop           = None
        self._init()

    def _init(self):
        self.main_loop       = MainLoop(self.collection, self.job_cls)
        self.main_loop.debug = self.debug
        self.main_loop.job_init_event.listen(self.job_init_event)
        self.main_loop.job_started_event.listen(self.job_started_event)
        self.main_loop.job_error_event.listen(self.job_error_event)
        self.main_loop.job_succeeded_event.listen(self.job_succeeded_event)
        self.main_loop.job_aborted_event.listen(self.job_aborted_event)
        self.main_loop.queue_empty_event.listen(self.queue_empty_event)
        self.main_loop.start()

    def _check_if_ready(self):
        if self.main_loop is None:
            raise Exception('main loop is already destroyed')

    def set_debug(self, debug = 1):
        """
        Set the debug level.

        @type  debug: int
        @param debug: The debug level.
        """
        self._check_if_ready()
        self.debug           = debug
        self.main_loop.debug = debug

    def get_max_threads(self):
        """
        Returns the maximum number of concurrent threads.

        @rtype:  int
        @return: The number of threads.
        """
        self._check_if_ready()
        return self.collection.get_max_working()

    def set_max_threads(self, max_threads):
        """
        Set the maximum number of concurrent threads.

        @type  max_threads: int
        @param max_threads: The number of threads.
        """
        if max_threads is None:
            raise TypeError('max_threads must not be None.')
        self._check_if_ready()
        self.collection.set_max_working(max_threads)

    def enqueue(self, function, name = None, times = 1, data = None):
        """
        Appends a function to the queue for execution. The times argument
        specifies the number of attempts if the function raises an exception.
        If the name argument is None it defaults to whatever id(function)
        returns.

        @type  function: callable
        @param function: The function that is executed.
        @type  name: str
        @param name: Stored in Job.name.
        @type  times: int
        @param times: The maximum number of attempts.
        @type  data: object
        @param data: Optional data to store in Job.data.
        @rtype:  int
        @return: The id of the new job.
        """
        self._check_if_ready()
        return self.main_loop.enqueue(function, name, times, data)

    def enqueue_or_ignore(self, function, name = None, times = 1, data = None):
        """
        Like enqueue(), but does nothing if a function with the same name
        is already in the queue.
        Returns a job id if a new job was added, returns None otherwise.

        @type  function: callable
        @param function: The function that is executed.
        @type  name: str
        @param name: Stored in Job.name.
        @type  times: int
        @param times: The maximum number of attempts.
        @type  data: object
        @param data: Optional data to store in Job.data.
        @rtype:  int or None
        @return: The id of the new job.
        """
        self._check_if_ready()
        return self.main_loop.enqueue_or_ignore(function, name, times, data)

    def priority_enqueue(self,
                         function,
                         name        = None,
                         force_start = False,
                         times       = 1,
                         data        = None):
        """
        Like L{enqueue()}, but adds the given function at the top of the
        queue.
        If force_start is True, the function is immediately started even when
        the maximum number of concurrent threads is already reached.

        @type  function: callable
        @param function: The function that is executed.
        @type  name: str
        @param name: Stored in Job.name.
        @type  force_start: bool
        @param force_start: Whether to start execution immediately.
        @type  times: int
        @param times: The maximum number of attempts.
        @type  data: object
        @param data: Optional data to store in Job.data.
        @rtype:  int
        @return: The id of the new job.
        """
        self._check_if_ready()
        return self.main_loop.priority_enqueue(function,
                                               name,
                                               force_start,
                                               times,
                                               data)

    def priority_enqueue_or_raise(self,
                                  function,
                                  name        = None,
                                  force_start = False,
                                  times       = 1,
                                  data        = None):
        """
        Like priority_enqueue(), but if a function with the same name is
        already in the queue, the existing function is moved to the top of
        the queue and the given function is ignored.
        Returns a job id if a new job was added, returns None otherwise.

        @type  function: callable
        @param function: The function that is executed.
        @type  name: str
        @param name: Stored in Job.name.
        @type  times: int
        @param times: The maximum number of attempts.
        @type  data: object
        @param data: Optional data to store in Job.data.
        @rtype:  int or None
        @return: The id of the new job.
        """
        self._check_if_ready()
        return self.main_loop.priority_enqueue_or_raise(function,
                                                        name,
                                                        force_start,
                                                        times,
                                                        data)

    def unpause(self):
        """
        Restart the execution of enqueued jobs after pausing them.
        This method is the opposite of pause().
        This method is asynchronous.
        """
        self.collection.unpause()

    def pause(self):
        """
        Stop the execution of enqueued jobs.
        Executing may later be resumed by calling unpause().
        This method is asynchronous.
        """
        self.collection.pause()

    def wait_for(self, job_id):
        """
        Waits until the job with the given id is completed.

        @type  job_id: int
        @param job_id: The job that is executed.
        """
        self._check_if_ready()
        self.main_loop.wait_for(job_id)

    def wait_until_done(self):
        """
        Waits until the queue is empty.
        """
        self.collection.wait_all()

    def shutdown(self, restart = True):
        """
        Stop the execution of enqueued jobs, and wait for all running
        jobs to complete. This method is synchronous and returns as soon
        as all jobs are terminated (i.e. all threads are stopped).

        If restart is True, the workqueue is restarted and paused,
        so you may fill it with new jobs.

        If restart is False, the WorkQueue can no longer be used after calling
        this method.

        @type  restart: bool
        @param restart: Whether to restart the queue after shutting down.
        """
        self._check_if_ready()
        self.collection.stop()
        self.collection.wait()
        self.main_loop.join()
        self.main_loop = None
        self.collection.clear()
        if restart:
            self.collection.start()
            self._init()

    def destroy(self):
        """
        Like shutdown(), but does not restart the queue and does not
        wait for already started jobs to complete.
        """
        self._check_if_ready()
        self.collection.stop()
        self.main_loop.join()
        self.main_loop = None
        self.collection.clear()

    def is_paused(self):
        """
        Returns True if the queue is currently active (i.e. not
        paused and not shut down), False otherwise.

        @rtype:  bool
        @return: Whether enqueued jobs are currently executed.
        """
        if self.main_loop is None:
            return True
        return self.collection.paused

    def get_running_jobs(self):
        """
        Returns a list of all jobs that are currently in progress.

        @rtype:  list[Job]
        @return: A list of running jobs.
        """
        return self.collection.get_working()

    def get_length(self):
        """
        Returns the number of currently non-completed jobs.

        @rtype:  int
        @return: The length of the queue.
        """
        return len(self.collection)

########NEW FILE########
__FILENAME__ = Client
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Places orders and requests the status from a server.
"""
import json
#HACK: the return value of opener.open(url) does not support
# __enter__ and __exit__ for Python's "with" in older versions
# of Python.
import urllib
urllib.addinfourl.__enter__ = lambda x: x
urllib.addinfourl.__exit__ = lambda s, *x: s.close()
#END HACK
from datetime import datetime
from urllib import urlencode
from urllib2 import HTTPDigestAuthHandler, build_opener, HTTPError
from lxml import etree
from Exscript.servers.HTTPd import default_realm
from Exscriptd.Order import Order
from Exscriptd.Task import Task

class Client(object):
    """
    An Exscriptd client that communicates via HTTP.
    """

    def __init__(self, address, user, password):
        """
        Constructor. Any operations performed with an
        instance of a client are directed to the server with the
        given address, using the given login data.

        @type  address: str
        @param address: The base url of the server.
        @type  user: str
        @param user: The login name on the server.
        @type  password: str
        @param password: The password of the user.
        """
        self.address = 'http://' + address
        self.handler = HTTPDigestAuthHandler()
        self.opener  = build_opener(self.handler)
        self.handler.add_password(realm  = default_realm,
                                  uri    = self.address,
                                  user   = user,
                                  passwd = password)

    def place_order(self, order):
        """
        Sends the given order to the server, and updates the status
        of the order accordingly.

        @type  order: Order
        @param order: The order that is placed.
        """
        if order.status != 'new':
            msg = 'order status is "%s", should be "new"' % order.status
            raise ValueError(msg)
        if not order.is_valid():
            raise ValueError('incomplete or invalid order')

        order.status = 'accepted'
        url          = self.address + '/order/'
        xml          = order.toxml()
        data         = urlencode({'xml': xml})
        try:
            with self.opener.open(url, data) as result:
                if result.getcode() != 200:
                    raise Exception(result.read())
                order.id = json.loads(result.read())
        except HTTPError, e:
            if hasattr(e, 'read'):
                raise Exception(str(e) + ' with ' + e.read())
            else:
                raise Exception(str(e))

    def get_order_from_id(self, id):
        """
        Returns the order with the given id.

        @type  id: str
        @param id: The id of the order.
        @rtype:  Order
        @return: The order if it exists, None otherwise.
        """
        args   = 'id=%d' % id
        url    = self.address + '/order/get/?' + args
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            return Order.from_xml(result.read())

    def get_order_status_from_id(self, order_id):
        """
        Returns a tuple containing the status of the order with the given
        id if it exists. Raises an exception otherwise. The tuple contains
        the following elements::

            status, progress, closed

        where 'status' is a human readable string, progress is a
        floating point number between 0.0 and 1.0, and closed is the
        time at which the order was closed.

        @type  order_id: str
        @param order_id: The id of the order.
        @rtype:  (str, float, datetime.timestamp)
        @return: The status and progress of the order.
        """
        url = self.address + '/order/status/?id=%s' % order_id
        with self.opener.open(url) as result:
            response = result.read()
            if result.getcode() != 200:
                raise Exception(response)
        data   = json.loads(response)
        closed = data['closed']
        if closed is not None:
            closed = closed.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
        return data['status'], data['progress'], closed

    def count_orders(self,
                     order_id    = None,
                     service     = None,
                     description = None,
                     status      = None,
                     created_by  = None):
        """
        Returns the total number of orders.

        @rtype:  int
        @return: The number of orders.
        @type  kwargs: dict
        @param kwargs: See L{get_order_list()}
        """
        args = {}
        if order_id:
            args['order_id'] = order_id
        if service:
            args['service'] = service
        if description:
            args['description'] = description
        if status:
            args['status'] = status
        if created_by:
            args['created_by'] = created_by
        url = self.address + '/order/count/?' + urlencode(args)
        with self.opener.open(url) as result:
            response = result.read()
            if result.getcode() != 200:
                raise Exception(response)
        return json.loads(response)

    def get_order_list(self,
                       order_id    = None,
                       service     = None,
                       description = None,
                       status      = None,
                       created_by  = None,
                       offset      = 0,
                       limit       = 0):
        """
        Returns a list of currently running orders.

        @type  offset: int
        @param offset: The number of orders to skip.
        @type  limit: int
        @param limit: The maximum number of orders to return.
        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - order_id - the order id (str)
                         - service - the service name (str)
                         - description - the order description (str)
                         - status - the status (str)
                         - created_by - the user name (str)
        @rtype:  list[Order]
        @return: A list of orders.
        """
        args = {'offset': offset, 'limit': limit}
        if order_id:
            args['order_id'] = order_id
        if service:
            args['service'] = service
        if description:
            args['description'] = description
        if status:
            args['status'] = status
        if created_by:
            args['created_by'] = created_by
        url = self.address + '/order/list/?' + urlencode(args)
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            xml = etree.parse(result)
        return [Order.from_etree(n) for n in xml.iterfind('order')]

    def count_tasks(self, order_id = None):
        """
        Returns the total number of tasks.

        @rtype:  int
        @return: The number of tasks.
        """
        args = ''
        if order_id:
            args += '?order_id=%d' % order_id
        url = self.address + '/task/count/' + args
        with self.opener.open(url) as result:
            response = result.read()
            if result.getcode() != 200:
                raise Exception(response)
        return json.loads(response)

    def get_task_list(self, order_id, offset = 0, limit = 0):
        """
        Returns a list of currently running orders.

        @type  offset: int
        @param offset: The number of orders to skip.
        @type  limit: int
        @param limit: The maximum number of orders to return.
        @rtype:  list[Order]
        @return: A list of orders.
        """
        args = 'order_id=%d&offset=%d&limit=%d' % (order_id, offset, limit)
        url  = self.address + '/task/list/?' + args
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            xml = etree.parse(result)
        return [Task.from_etree(n) for n in xml.iterfind('task')]

    def get_task_from_id(self, id):
        """
        Returns the task with the given id.

        @type  id: int
        @param id: The id of the task.
        @rtype:  Task
        @return: The task with the given id.
        """
        args = 'id=%d' % id
        url  = self.address + '/task/get/?' + args
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            return Task.from_xml(result.read())

    def get_log_from_task_id(self, task_id):
        """
        Returns the content of the logfile for the given task.

        @type  task_id: int
        @param task_id: The task id.
        @rtype:  str
        @return: The file content.
        """
        args = 'task_id=%d' % task_id
        url  = self.address + '/log/?' + args
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            return result.read()

    def get_trace_from_task_id(self, task_id):
        """
        Returns the content of the trace file for the given task.

        @type  task_id: int
        @param task_id: The task id.
        @rtype:  str
        @return: The file content.
        """
        args = 'task_id=%d' % task_id
        url  = self.address + '/trace/?' + args
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            return result.read()

########NEW FILE########
__FILENAME__ = AccountPoolConfig
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class AccountPoolConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.pool_name = None
        self.filename  = None
        self.config    = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add or configure account pools'

    @staticmethod
    def get_commands():
        return (('add',  'add a new account pool'),
                ('edit', 'replace an existing account pool'))

    def prepare_add(self, parser, pool_name, filename):
        self.pool_name = pool_name
        self.filename  = filename
        if not os.path.isfile(filename):
            parser.error('invalid file: ' + filename)
        if self.config.has_account_pool(self.pool_name):
            parser.error('account pool already exists')

    def start_add(self):
        self.config.add_account_pool_from_file(self.pool_name, self.filename)
        print 'Account pool added.'

    def prepare_edit(self, parser, pool_name, filename):
        self.pool_name = pool_name
        self.filename  = filename
        if not os.path.isfile(filename):
            parser.error('invalid file: ' + filename)
        if not self.config.has_account_pool(self.pool_name):
            parser.error('account pool not found')

    def start_edit(self):
        self.config.add_account_pool_from_file(self.pool_name, self.filename)
        print 'Account pool configured.'

########NEW FILE########
__FILENAME__ = BaseConfig
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import stat
import re
from Exscriptd.Config import Config, default_log_dir
from Exscriptd.config.ConfigSection import ConfigSection

__dirname__ = os.path.dirname(__file__)
spool_dir   = os.path.join('/var', 'spool', 'exscriptd')
pidfile     = os.path.join('/var', 'run', 'exscriptd.pid')
init_dir    = os.path.join('/etc', 'init.d')

class BaseConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.config = None

    def _read_config(self):
        self.config = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'global base configuration'

    @staticmethod
    def get_commands():
        return (('install', 'install exscriptd base config'),
                ('edit',    'change the base config'))

    def _generate(self, infilename, outfilename):
        if not self.options.overwrite and os.path.isfile(outfilename):
            self.info('file exists, skipping.\n')
            return

        vars = {'@CFG_DIR@':    self.global_options.config_dir,
                '@LOG_DIR@':    self.options.log_dir,
                '@SPOOL_DIR@':  spool_dir,
                '@SCRIPT_DIR@': self.script_dir,
                '@PYTHONPATH@': os.environ.get('PYTHONPATH'),
                '@PIDFILE@':    self.options.pidfile,
                '@INIT_DIR@':   init_dir}
        sub_re = re.compile('(' + '|'.join(vars.keys()) + ')+')

        with open(infilename) as infile:
            content = infile.read()
        subst   = lambda s: vars[s.group(0)]
        content = sub_re.sub(subst, content)
        with open(outfilename, 'w') as outfile:
            outfile.write(content)
        self.info('done.\n')

    def getopt_install(self, parser):
        self.getopt_edit(parser)
        parser.add_option('--overwrite',
                          dest    = 'overwrite',
                          action  = 'store_true',
                          default = False,
                          help    = 'overwrite existing files')
        parser.add_option('--pidfile',
                          dest    = 'pidfile',
                          metavar = 'STRING',
                          default = pidfile,
                          help    = 'the location of the pidfile')

    def _make_executable(self, filename):
        self.info('making %s executable...\n' % filename)
        mode = os.stat(filename).st_mode
        os.chmod(filename, mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

    def _create_directories(self):
        log_dir = self.options.log_dir
        self.info('creating log directory %s... ' % log_dir)
        self._mkdir(log_dir)
        self.info('creating spool directory %s... ' % spool_dir)
        self._mkdir(spool_dir)
        cfg_dir = self.global_options.config_dir
        self.info('creating config directory %s... ' % cfg_dir)
        self._mkdir(cfg_dir)
        service_dir = os.path.join(cfg_dir, 'services')
        self.info('creating service directory %s... ' % service_dir)
        self._mkdir(service_dir)

    def start_install(self):
        # Install the init script.
        init_template = os.path.join(__dirname__, 'exscriptd.in')
        init_file     = os.path.join('/etc', 'init.d', 'exscriptd')
        self.info('creating init-file at %s... ' % init_file)
        self._generate(init_template, init_file)
        self._make_executable(init_file)

        # Create directories.
        self._create_directories()

        # Install the default config file.
        cfg_tmpl = os.path.join(__dirname__, 'main.xml.in')
        cfg_file = os.path.join(self.global_options.config_dir, 'main.xml')
        self.info('creating config file %s... ' % cfg_file)
        self._generate(cfg_tmpl, cfg_file)

    def getopt_edit(self, parser):
        parser.add_option('--log-dir',
                          dest    = 'log_dir',
                          default = default_log_dir,
                          metavar = 'FILE',
                          help    = 'where to place log files')

    def prepare_edit(self, parser):
        self._read_config()
        cfg_file = os.path.join(self.global_options.config_dir, 'main.xml')
        if not os.path.exists(cfg_file):
            parser.error('no existing base installation found')

    def start_edit(self):
        self._create_directories()
        self.config.set_logdir(self.options.log_dir)
        print 'Base configuration saved.'

########NEW FILE########
__FILENAME__ = ConfigSection
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import sys

class ConfigSection(object):
    def __init__(self, global_options, script_dir):
        self.global_options = global_options
        self.options        = None
        self.script_dir     = script_dir

    @staticmethod
    def get_description():
        raise NotImplementedError()

    @staticmethod
    def get_commands():
        raise NotImplementedError()

    def _mkdir(self, dirname):
        if os.path.isdir(dirname):
            self.info('directory exists, skipping.\n')
        else:
            os.makedirs(dirname)
            self.info('done.\n')

    def info(self, *args):
        sys.stdout.write(' '.join(str(a) for a in args))

    def error(self, *args):
        sys.stderr.write(' '.join(str(a) for a in args))

########NEW FILE########
__FILENAME__ = DaemonConfig
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscriptd.Config import Config
from Exscriptd.config.ConfigSection import ConfigSection

class DaemonConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.daemon_name = None
        self.config      = None

    def _read_config(self):
        self.config = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'daemon-specific configuration'

    @staticmethod
    def get_commands():
        return (('add',  'configure a new daemon'),
                ('edit', 'configure an existing daemon'))

    def getopt_add(self, parser):
        parser.add_option('--address',
                          dest    = 'address',
                          metavar = 'STRING',
                          help    = 'the address to listen on, all by default')
        parser.add_option('--port',
                          dest    = 'port',
                          metavar = 'INT',
                          default = 8132,
                          help    = 'the TCP port number')
        parser.add_option('--database',
                          dest    = 'database',
                          metavar = 'STRING',
                          help    = 'name of the order database')
        parser.add_option('--account-pool',
                          dest    = 'account_pool',
                          metavar = 'STRING',
                          help    = 'the account pool used for authenticating' \
                                  + 'HTTP clients')

    def prepare_add(self, parser, daemon_name):
        self.daemon_name = daemon_name
        self._read_config()
        if self.config.has_daemon(self.daemon_name):
            parser.error('daemon already exists')

    def start_add(self):
        self.config.add_daemon(self.daemon_name,
                               self.options.address,
                               self.options.port,
                               self.options.account_pool,
                               self.options.database)
        print 'Daemon added.'

    def getopt_edit(self, parser):
        self.getopt_add(parser)

    def prepare_edit(self, parser, daemon_name):
        self.daemon_name = daemon_name
        self._read_config()
        if not self.config.has_daemon(self.daemon_name):
            parser.error('daemon not found')
        if not self.config.has_database(self.options.database):
            parser.error('database not found')

    def start_edit(self):
        self.config.add_daemon(self.daemon_name,
                               self.options.address,
                               self.options.port,
                               self.options.account_pool,
                               self.options.database)
        print 'Daemon configured.'

########NEW FILE########
__FILENAME__ = DatabaseConfig
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class DatabaseConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.db_name = None
        self.dbn     = None
        self.config  = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add, edit, or remove databases'

    @staticmethod
    def get_commands():
        return (('add',  'configure a new database'),
                ('edit', 'configure an existing database'))

    def prepare_add(self, parser, db_name, dbn):
        self.db_name = db_name
        self.dbn     = dbn
        if self.config.has_database(self.db_name):
            parser.error('database already exists')

    def start_add(self):
        self.config.add_database(self.db_name, self.dbn)
        print 'Database added.'

    def prepare_edit(self, parser, db_name, dbn):
        self.db_name = db_name
        self.dbn     = dbn
        if not self.config.has_database(self.db_name):
            parser.error('database not found')

    def start_edit(self):
        if self.config.add_database(self.db_name, self.dbn):
            print 'Database configured.'
        else:
            print 'No changes were made.'

########NEW FILE########
__FILENAME__ = QueueConfig
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class QueueConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.queue_name = None
        self.config     = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add, edit, or remove queues'

    @staticmethod
    def get_commands():
        return (('add',  'create a new queue'),
                ('edit', 'edit an existing queue'))

    def getopt_add(self, parser):
        parser.add_option('--account-pool',
                          dest    = 'account_pool',
                          metavar = 'STRING',
                          help    = 'the account pool that is used')
        parser.add_option('--max-threads',
                          dest    = 'max_threads',
                          metavar = 'INT',
                          default = 5,
                          help    = 'the name of the new queue')

    def prepare_add(self, parser, queue_name):
        self.queue_name = queue_name
        if self.config.has_queue(self.queue_name):
            parser.error('queue already exists')

    def start_add(self):
        self.config.add_queue(self.queue_name,
                              self.options.account_pool,
                              self.options.max_threads)
        print 'Queue added.'

    def getopt_edit(self, parser):
        self.getopt_add(parser)

    def prepare_edit(self, parser, queue_name):
        self.queue_name = queue_name
        if not self.config.has_queue(self.queue_name):
            parser.error('queue not found')

    def start_edit(self):
        if self.config.add_queue(self.queue_name,
                                 self.options.account_pool,
                                 self.options.max_threads):
            print 'Queue configured.'
        else:
            print 'No changes were made.'

########NEW FILE########
__FILENAME__ = ServiceConfig
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import sys
from Exscriptd.util                 import find_module_recursive
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class ServiceConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.service_name = None
        self.module_name  = None
        self.varname      = None
        self.value        = None
        self.config       = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add or configure services'

    @staticmethod
    def get_commands():
        return (('add',   'configure a new service'),
                ('edit',  'configure an existing service'),
                ('set',   'define a service variable'),
                ('unset', 'remove a service variable'))

    def _assert_module_exists(self, parser, module_name):
        try:
            file, module_path, desc = find_module_recursive(module_name)
        except ImportError:
            args = repr(module_name), sys.path
            msg  = 'service %s not found. sys.path is %s' % args
            parser.error(msg)

    def getopt_add(self, parser):
        parser.add_option('--daemon',
                          dest    = 'daemon',
                          metavar = 'STRING',
                          help    = 'the daemon that is used')
        parser.add_option('--queue',
                          dest    = 'queue',
                          metavar = 'STRING',
                          help    = 'the queue that is used')

    def prepare_add(self, parser, service_name, module_name):
        self.service_name = service_name
        self.module_name  = module_name
        self._assert_module_exists(parser, module_name)
        if self.config.has_service(self.service_name):
            parser.error('service already exists')

    def start_add(self):
        self.config.add_service(self.service_name,
                                self.module_name,
                                self.options.daemon,
                                self.options.queue)
        print 'Service added.'

    def getopt_edit(self, parser):
        self.getopt_add(parser)

    def prepare_edit(self, parser, service_name):
        self.service_name = service_name
        if not self.config.has_service(self.service_name):
            parser.error('service not found')

    def start_edit(self):
        if self.config.add_service(self.service_name,
                                   None,
                                   self.options.daemon,
                                   self.options.queue):
            print 'Service configured.'
        else:
            print 'No changes were made.'

    def prepare_set(self, parser, service_name, varname, value):
        self.service_name = service_name
        self.varname      = varname
        self.value        = value

    def start_set(self):
        self.config.set_service_variable(self.service_name,
                                         self.varname,
                                         self.value)
        print 'Variable set.'

    def prepare_unset(self, parser, service_name, varname):
        self.service_name = service_name
        self.varname      = varname

    def start_unset(self):
        self.config.unset_service_variable(self.service_name, self.varname)
        print 'Variable removed.'

########NEW FILE########
__FILENAME__ = Config
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import base64
import shutil
import logging
import logging.handlers
from functools import partial
from lxml import etree
from Exscript import Queue
from Exscript.AccountPool import AccountPool
from Exscript.util.file import get_accounts_from_file
from Exscriptd.OrderDB import OrderDB
from Exscriptd.HTTPDaemon import HTTPDaemon
from Exscriptd.Service import Service
from Exscriptd.ConfigReader import ConfigReader
from Exscriptd.util import find_module_recursive
from Exscriptd.xml import get_accounts_from_etree, add_accounts_to_etree

default_config_dir = os.path.join('/etc', 'exscriptd')
default_log_dir    = os.path.join('/var', 'log', 'exscriptd')

cache = {}
def cache_result(func):
    def wrapped(*args, **kwargs):
        key = func.__name__, repr(args), repr(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    return wrapped

class Config(ConfigReader):
    def __init__(self,
                 cfg_dir           = default_config_dir,
                 resolve_variables = True):
        self.cfg_dir     = cfg_dir
        self.service_dir = os.path.join(cfg_dir, 'services')
        filename         = os.path.join(cfg_dir, 'main.xml')
        self.logdir      = default_log_dir
        ConfigReader.__init__(self, filename, resolve_variables)

        logdir_elem = self.cfgtree.find('exscriptd/logdir')
        if logdir_elem is not None:
            self.logdir = logdir_elem.text

    def _get_account_list_from_name(self, name):
        element = self.cfgtree.find('account-pool[@name="%s"]' % name)
        return get_accounts_from_etree(element)

    @cache_result
    def _init_account_pool_from_name(self, name):
        print 'Creating account pool "%s"...' % name
        accounts = self._get_account_list_from_name(name)
        return AccountPool(accounts)

    @cache_result
    def _init_queue_from_name(self, name):
        # Create the queue first.
        element     = self.cfgtree.find('queue[@name="%s"]' % name)
        max_threads = element.find('max-threads').text
        queue       = Queue(verbose = 0, max_threads = max_threads)

        # Assign account pools to the queue.
        def match_cb(condition, host):
            return eval(condition, host.get_dict())

        for pool_elem in element.iterfind('account-pool'):
            pname = pool_elem.text
            pool  = self._init_account_pool_from_name(pname)
            cond  = pool_elem.get('for')
            if cond is None:
                print 'Assigning default account pool "%s" to "%s"...' % (pname, name)
                queue.add_account_pool(pool)
                continue

            print 'Assigning account pool "%s" to "%s"...' % (pname, name)
            condition = compile(cond, 'config', 'eval')
            queue.add_account_pool(pool, partial(match_cb, condition))

        return queue

    def get_logdir(self):
        return self.logdir

    def set_logdir(self, logdir):
        self.logdir = logdir
        # Create an XML segment for the database.
        changed     = False
        xml         = self.cfgtree.getroot()
        global_elem = xml.find('exscriptd')
        if global_elem is None:
            raise Exception('missing section in config file: <exscriptd>')

        # Add the dbn the the XML.
        if self._add_or_update_elem(global_elem, 'logdir', logdir):
            changed = True

        # Write the resulting XML.
        if not changed:
            return False
        self.save()
        return True

    def get_queues(self):
        names = [e.get('name') for e in self.cfgtree.iterfind('queue')]
        return dict((name, self._init_queue_from_name(name))
                    for name in names)

    def _init_database_from_dbn(self, dbn):
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
        #print 'Creating database connection for', dbn
        return create_engine(dbn, poolclass = NullPool)

    def _init_daemon(self, element, dispatcher):
        # Init the order database for the daemon.
        name    = element.get('name')
        address = element.find('address').text or ''
        port    = int(element.find('port').text)

        # Create log directories for the daemon.
        logdir  = os.path.join(self.logdir, 'daemons', name)
        logfile = os.path.join(logdir, 'access.log')
        if not os.path.isdir(logdir):
            os.makedirs(logdir)

        # Set up logging.
        logger = logging.getLogger('exscriptd_' + name)
        logger.setLevel(logging.INFO)

        # Set up logfile rotation.
        handler = logging.handlers.RotatingFileHandler(logfile,
                                                       maxBytes    = 200000,
                                                       backupCount = 5)

        # Define the log format.
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Create the daemon (this does not start it).
        daemon = HTTPDaemon(dispatcher, name, logger, address, port)

        # Add some accounts, if any.
        account_pool = element.find('account-pool')
        for account in self._get_account_list_from_name(account_pool.text):
            daemon.add_account(account)

        return daemon

    def _get_service_files(self):
        """
        Searches the config directory for service configuration files,
        and returns a list of path names.
        """
        files = []
        for file in os.listdir(self.service_dir):
            config_dir = os.path.join(self.service_dir, file)
            if not os.path.isdir(config_dir):
                continue
            config_file = os.path.join(config_dir, 'config.xml')
            if not os.path.isfile(config_file):
                continue
            files.append(config_file)
        return files

    def _get_service_file_from_name(self, name):
        """
        Searches the config directory for service configuration files,
        and returns the name of the first file that defines a service
        with the given name.
        """
        for file in self._get_service_files():
            xml     = etree.parse(file)
            element = xml.find('service[@name="%s"]' % name)
            if element is not None:
                return file
        return None

    def _get_service_file_from_folder(self, folder):
        """
        Searches the config directory for service configuration files,
        and returns the name of the first file lying in the folder
        with the given name.
        """
        for file in self._get_service_files():
            if os.path.basename(os.path.dirname(file)) == folder:
                return file
        return None

    def _init_service_file(self, filename, dispatcher):
        services    = []
        service_dir = os.path.dirname(filename)
        cfgtree     = ConfigReader(filename).cfgtree
        for element in cfgtree.iterfind('service'):
            name = element.get('name')
            print 'Loading service "%s"...' % name

            module     = element.find('module').text
            queue_elem = element.find('queue')
            queue_name = queue_elem is not None and queue_elem.text
            service    = Service(dispatcher,
                                 name,
                                 module,
                                 service_dir,
                                 self,
                                 queue_name)
            print 'Service "%s" initialized.' % name
            services.append(service)
        return services

    def get_services(self, dispatcher):
        services = []
        for file in self._get_service_files():
            services += self._init_service_file(file, dispatcher)
        return services

    def has_account_pool(self, name):
        return self.cfgtree.find('account-pool[@name="%s"]' % name) is not None

    def add_account_pool_from_file(self, name, filename):
        # Remove the pool if it exists.
        xml       = self.cfgtree.getroot()
        pool_elem = xml.find('account-pool[@name="%s"]' % name)
        if pool_elem is not None:
            xml.remove(pool_elem)

        # Import the new pool from the given file.
        pool_elem = etree.SubElement(xml, 'account-pool', name = name)
        accounts  = get_accounts_from_file(filename)
        add_accounts_to_etree(pool_elem, accounts)

        self.save()

    def has_queue(self, name):
        return self.cfgtree.find('queue[@name="%s"]' % name) is not None

    def has_database(self, name):
        return self.cfgtree.find('database[@name="%s"]' % name) is not None

    def add_database(self, db_name, dbn):
        # Create an XML segment for the database.
        changed = False
        xml     = self.cfgtree.getroot()
        db_elem = xml.find('database[@name="%s"]' % db_name)
        if db_elem is None:
            changed = True
            db_elem = etree.SubElement(xml, 'database', name = db_name)

        # Add the dbn the the XML.
        if self._add_or_update_elem(db_elem, 'dbn', dbn):
            changed = True

        # Write the resulting XML.
        if not changed:
            return False
        self.save()
        return True

    @cache_result
    def get_database_from_name(self, name):
        element = self.cfgtree.find('database[@name="%s"]' % name)
        dbn     = element.find('dbn').text
        return self._init_database_from_dbn(dbn)

    @cache_result
    def get_order_db(self):
        db_elem = self.cfgtree.find('exscriptd/order-db')
        if db_elem is None:
            engine = self._init_database_from_dbn('sqlite://')
        else:
            engine = self.get_database_from_name(db_elem.text)
        db = OrderDB(engine)
        db.install()
        return db

    def add_queue(self, queue_name, account_pool, max_threads):
        # Create an XML segment for the queue.
        changed    = False
        xml        = self.cfgtree.getroot()
        queue_elem = xml.find('queue[@name="%s"]' % queue_name)
        if queue_elem is None:
            changed    = True
            queue_elem = etree.SubElement(xml, 'queue', name = queue_name)

        # Create an XML reference to the account pool.
        acc_elem = queue_elem.find('account-pool')
        if account_pool is None and acc_elem is not None:
            changed = True
            queue_elem.remove(acc_elem)
        elif account_pool is not None:
            try:
                self._init_account_pool_from_name(account_pool)
            except AttributeError:
                raise Exception('no such account pool: %s' % account_pool)

            if self._add_or_update_elem(queue_elem,
                                        'account-pool',
                                        account_pool):
                changed = True

        # Define the number of threads.
        if self._add_or_update_elem(queue_elem, 'max-threads', max_threads):
            changed = True

        if not changed:
            return False

        # Write the resulting XML.
        self.save()
        return True

    def has_service(self, service_name):
        return self._get_service_file_from_name(service_name) is not None

    def add_service(self,
                    service_name,
                    module_name = None,
                    daemon_name = None,
                    queue_name  = None):
        pathname = self._get_service_file_from_name(service_name)
        changed  = False

        if not pathname:
            if not module_name:
                raise Exception('module name is required')

            # Find the installation path of the module.
            file, module_path, desc = find_module_recursive(module_name)

            # Create a directory for the new service, if it does not
            # already exist.
            service_dir = os.path.join(self.service_dir, service_name)
            if not os.path.isdir(service_dir):
                os.makedirs(service_dir)

            # Copy the default config file.
            cfg_file = os.path.join(module_path, 'config.xml.tmpl')
            pathname = os.path.join(service_dir, 'config.xml')
            if not os.path.isfile(pathname):
                shutil.copy(cfg_file, pathname)
            changed = True

        # Create an XML segment for the service.
        doc         = etree.parse(pathname)
        xml         = doc.getroot()
        service_ele = xml.find('service[@name="%s"]' % service_name)
        if service_ele is None:
            changed = True
            service_ele = etree.SubElement(xml, 'service', name = service_name)

        # By default, use the first daemon defined in the main config file.
        if daemon_name is None:
            daemon_name = self.cfgtree.find('daemon').get('name')
        if self._add_or_update_elem(service_ele, 'daemon', daemon_name):
            changed = True

        # Add an XML statement pointing to the module.
        if module_name is not None:
            if self._add_or_update_elem(service_ele, 'module', module_name):
                changed = True

        # By default, use the first queue defined in the main config file.
        if queue_name is None:
            queue_name = self.cfgtree.find('queue').get('name')
        if not self.has_queue(queue_name):
            raise Exception('no such queue: ' + queue_name)
        if self._add_or_update_elem(service_ele, 'queue', queue_name):
            changed = True

        if not changed:
            return False

        # Write the resulting XML.
        self._write_xml(xml, pathname)
        return True

    def _get_service_var_elem(self, service):
        pathname = self._get_service_file_from_folder(service)
        if pathname is None:
            pathname = self._get_service_file_from_name(service)
        doc      = etree.parse(pathname)
        xml      = doc.getroot()
        return pathname, xml, xml.find('variables')

    def set_service_variable(self, service, varname, value):
        path, xml, var_elem = self._get_service_var_elem(service)
        elem                = var_elem.find(varname)
        if elem is None:
            elem = etree.SubElement(var_elem, varname)
        elem.text = value
        self._write_xml(xml, path)

    def unset_service_variable(self, service, varname):
        path, xml, var_elem = self._get_service_var_elem(service)
        elem                = var_elem.find(varname)
        if elem is not None:
            var_elem.remove(elem)
        self._write_xml(xml, path)

    def has_daemon(self, name):
        return self.cfgtree.find('daemon[@name="%s"]' % name) is not None

    def add_daemon(self,
                   name,
                   address,
                   port,
                   account_pool,
                   database):
        daemon_elem = self.cfgtree.find('daemon[@name="%s"]' % name)
        changed     = False
        if daemon_elem is None:
            changed     = True
            daemon_elem = etree.SubElement(self.cfgtree.getroot(),
                                           'daemon',
                                           name = name)

        if self._add_or_update_elem(daemon_elem, 'address', address):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'port', port):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'account-pool', account_pool):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'database', database):
            changed = True

        if not changed:
            return False
        self.save()
        return changed

    @cache_result
    def get_daemon_from_name(self, name, dispatcher):
        # Create the daemon.
        element = self.cfgtree.find('daemon[@name="%s"]' % name)
        return self._init_daemon(element, dispatcher)

    def get_daemon(self, dispatcher):
        name = self.cfgtree.find('exscriptd/daemon').text
        return self.get_daemon_from_name(name, dispatcher)

########NEW FILE########
__FILENAME__ = ConfigReader
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import inspect
import shutil
from lxml           import etree
from Exscriptd.util import resolve_variables

class ConfigReader(object):
    def __init__(self, filename, resolve_variables = True, parent = None):
        clsfile        = inspect.getfile(self.__class__)
        self.resolve   = resolve_variables
        self.cfgtree   = etree.parse(filename)
        self.filename  = filename
        self.parent    = parent
        self.variables = os.environ.copy()
        self.variables['INSTALL_DIR'] = os.path.dirname(clsfile)
        self._clean_tree()

    def _resolve(self, text):
        if not self.resolve:
            return text
        if text is None:
            return None
        return resolve_variables(self.variables, text.strip())

    def _clean_tree(self):
        # Read all variables.
        variables = self.cfgtree.find('variables')
        if variables is not None:
            for element in variables:
                varname = element.tag.strip()
                value   = resolve_variables(self.variables, element.text)
                self.variables[varname] = value

        # Resolve variables everywhere.
        for element in self.cfgtree.iter():
            if element.tag is etree.Comment:
                continue
            element.text = self._resolve(element.text)
            for attr in element.attrib:
                value                = element.attrib[attr]
                element.attrib[attr] = self._resolve(value)

    def _add_or_update_elem(self, parent, name, text):
        child_elem = parent.find(name)
        changed    = False
        if child_elem is None:
            changed    = True
            child_elem = etree.SubElement(parent, name)
        if str(child_elem.text) != str(text):
            changed         = True
            child_elem.text = str(text)
        return changed

    def _write_xml(self, tree, filename):
        if os.path.isfile(filename):
            shutil.move(filename, filename + '.old')
        with open(filename, 'w') as fp:
            fp.write(etree.tostring(tree, pretty_print = True))

    def _findelem(self, selector):
        elem = self.cfgtree.find(selector)
        if elem is not None:
            return elem
        if self.parent is None:
            return None
        return self.parent._findelem(selector)

    def save(self):
        self._write_xml(self.cfgtree, self.filename)

########NEW FILE########
__FILENAME__ = DBObject
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

class DBObject(object):
    def __init__(self, obj = None):
        # Since we override setattr below, we can't access our properties
        # directly.
        self.__dict__['__object__']  = obj
        self.__dict__['__changed__'] = True

    def __setattr__(self, name, value):
        """
        Overwritten to proxy any calls to the associated object
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @type  value: string
        @param value: The attribute value.
        """
        if self.__dict__.get('__object__') is None:
            self.__dict__[name] = value
        if name in self.__dict__.keys():
            self.__dict__[name] = value
        else:
            setattr(self.__object__, name, value)

    def __getattr__(self, name):
        """
        Overwritten to proxy any calls to the associated object
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @rtype:  object
        @return: Whatever the protocol adapter returns.
        """
        if self.__dict__.get('__object__') is None:
            return self.__dict__[name]
        if name in self.__dict__.keys():
            return self.__dict__[name]
        return getattr(self.__object__, name)

    def touch(self):
        self.__dict__['__changed__'] = True

    def untouch(self):
        self.__dict__['__changed__'] = False

    def is_dirty(self):
        return self.__dict__['__changed__']

########NEW FILE########
__FILENAME__ = Dispatcher
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import logging
from functools import partial
from collections import defaultdict
from threading import Thread, Lock
from Exscriptd.util import synchronized
from Exscriptd import Task

class _AsyncFunction(Thread):
    def __init__ (self, function, *args, **kwargs):
        Thread.__init__(self)
        self.function = function
        self.args     = args
        self.kwargs   = kwargs

    def run(self):
        self.function(*self.args, **self.kwargs)

class Dispatcher(object):
    def __init__(self, order_db, queues, logger, logdir):
        self.order_db = order_db
        self.queues   = {}
        self.logger   = logger
        self.loggers  = defaultdict(list) # map order id to loggers
        self.logdir   = logdir
        self.lock     = Lock()
        self.services = {}
        self.daemons  = {}
        self.logger.info('Closing all open orders.')
        self.order_db.close_open_orders()

        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        for name, queue in queues.iteritems():
            self.add_queue(name, queue)

    def get_queue_from_name(self, name):
        return self.queues[name]

    def add_queue(self, name, queue):
        self.queues[name] = queue
        wq = queue.workqueue
        wq.job_init_event.connect(partial(self._on_job_event, name, 'init'))
        wq.job_started_event.connect(partial(self._on_job_event,
                                             name,
                                             'started'))
        wq.job_error_event.connect(partial(self._on_job_event,
                                           name,
                                           'error'))
        wq.job_succeeded_event.connect(partial(self._on_job_event,
                                               name,
                                               'succeeded'))
        wq.job_aborted_event.connect(partial(self._on_job_event,
                                             name,
                                             'aborted'))

    def _set_task_status(self, job_id, queue_name, status):
        # Log the status change.
        task = self.order_db.get_task(job_id = job_id)
        msg  = '%s/%s: %s' % (queue_name, job_id, status)
        if task is None:
            self.logger.info(msg + ' (untracked)')
            return
        self.logger.info(msg + ' (order id ' + str(task.order_id) + ')')

        # Update the task in the database.
        if status == 'succeeded':
            task.completed()
        elif status == 'started':
            task.set_status('running')
        elif status == 'aborted':
            task.close(status)
        else:
            task.set_status(status)
        self.order_db.save_task(task)

        # Check whether the order can now be closed.
        if task.get_closed_timestamp() is not None:
            order = self.order_db.get_order(id = task.order_id)
            self._update_order_status(order)

    def _on_job_event(self, queue_name, status, job, *args):
        self._set_task_status(job.id, queue_name, status)

    def set_job_name(self, job_id, name):
        task = self.order_db.get_task(job_id = job_id)
        task.set_name(name)
        self.order_db.save_task(task)

    def set_job_progress(self, job_id, progress):
        task = self.order_db.get_task(job_id = job_id)
        task.set_progress(progress)
        self.order_db.save_task(task)

    def get_order_logdir(self, order):
        orders_logdir = os.path.join(self.logdir, 'orders')
        order_logdir  = os.path.join(orders_logdir, str(order.get_id()))
        if not os.path.isdir(order_logdir):
            os.makedirs(order_logdir)
        return order_logdir

    def get_logger(self, order, name, level = logging.INFO):
        """
        Creates a logger that logs to a file in the order's log directory.
        """
        order_logdir = self.get_order_logdir(order)
        logfile      = os.path.join(order_logdir, name)
        logger       = logging.getLogger(logfile)
        handler      = logging.FileHandler(logfile)
        format       = r'%(asctime)s - %(levelname)s - %(message)s'
        formatter    = logging.Formatter(format)
        logger.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.loggers[order.get_id()].append(logger)
        return logger

    def _free_logger(self, logger):
        # hack to work around the fact that Python's logging module
        # provides no documented way to delete loggers.
        del logger.manager.loggerDict[logger.name]
        logger.manager = None

    def service_added(self, service):
        """
        Called by a service when it is initialized.
        """
        service.parent = self
        self.services[service.name] = service

    def daemon_added(self, daemon):
        """
        Called by a daemon when it is initialized.
        """
        daemon.parent = self
        self.daemons[daemon.name] = daemon
        daemon.order_incoming_event.listen(self.place_order, daemon.name)

    def log(self, order, message):
        msg = '%s/%s: %s' % (order.get_service_name(),
                             order.get_id(),
                             message)
        self.logger.info(msg)

    def get_order_db(self):
        return self.order_db

    def _update_order_status(self, order):
        remaining = self.order_db.count_tasks(order_id = order.id,
                                              closed   = None)
        if remaining == 0:
            total = self.order_db.count_tasks(order_id = order.id)
            if total == 1:
                task = self.order_db.get_task(order_id = order.id)
                order.set_description(task.get_name())
            order.close()
            self.set_order_status(order, 'completed')
            for logger in self.loggers.pop(order.get_id(), []):
                self._free_logger(logger)

    def _on_task_changed(self, task):
        self.order_db.save_task(task)

    def create_task(self, order, name):
        task = Task(order.id, name)
        task.changed_event.listen(self._on_task_changed)
        self.order_db.save_task(task)
        return task

    def set_order_status(self, order, status):
        order.status = status
        self.order_db.save_order(order)
        self.log(order, 'Status is now "%s"' % status)

    def place_order(self, order, daemon_name):
        self.logger.debug('Incoming order from ' + daemon_name)

        # Store it in the database.
        self.set_order_status(order, 'incoming')

        # Loop the requested service up.
        service = self.services.get(order.get_service_name())
        if not service:
            order.close()
            self.set_order_status(order, 'service-not-found')
            return

        # Notify the service of the new order.
        try:
            accepted = service.check(order)
        except Exception, e:
            self.log(order, 'Exception: %s' % e)
            order.close()
            self.set_order_status(order, 'error')
            raise

        if not accepted:
            order.close()
            self.set_order_status(order, 'rejected')
            return
        self.set_order_status(order, 'accepted')

        # Save the order, including the data that was passed.
        # For performance reasons, use a new thread.
        func = _AsyncFunction(self._enter_order, service, order)
        func.start()

    def _enter_order(self, service, order):
        # Note: This method is called asynchronously.
        # Store the order in the database.
        self.set_order_status(order, 'saving')
        self.order_db.save_order(order)

        self.set_order_status(order, 'starting')
        with self.lock:
            # We must stop the queue while new jobs are placed,
            # else the queue might start processing a job before
            # it was attached to a task.
            for queue in self.queues.itervalues():
                queue.workqueue.pause()

            try:
                service.enter(order)
            except Exception, e:
                self.log(order, 'Exception: %s' % e)
                order.close()
                self.set_order_status(order, 'error')
                raise
            finally:
                # Re-enable the workqueue.
                for queue in self.queues.itervalues():
                    queue.workqueue.unpause()
        self.set_order_status(order, 'running')

        # If the service did not enqueue anything, it may already be completed.
        self._update_order_status(order)

########NEW FILE########
__FILENAME__ = HTTPDaemon
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import json
import logging
from traceback import format_exc
from urlparse import parse_qs
from lxml import etree
from Exscript import Host
from Exscript.servers.HTTPd import HTTPd, RequestHandler
from Exscript.util.event import Event
from Exscriptd.Order import Order

"""
URL list:

  Path                            Method  Function
  order/                          POST    Place an XML formatted order
  order/get/?id=1234              GET     Returns order 1234
  order/status/?id=1234           GET     Status and progress for order 1234
  order/count/                    GET     Get the total number of orders
  order/count/?service=grabber    GET     Number of orders matching the name
  order/list/?offset=10&limit=25  GET     Get a list of orders
  order/list/?service=grabber     GET     Filter list of orders by service name
  order/list/?description=foobar  GET     Filter list of orders by description
  order/list/?status=completed    GET     Filter list of orders by status
  task/get/?id=1234               GET     Returns task 1234
  task/count/?order_id=1234       GET     Get the number of tasks for order 1234
  task/list/?order_id=1234        GET     Get a list of tasks for order 1234
  log/?task_id=4567               GET     Returns the content of the logfile
  trace/?task_id=4567             GET     Returns the content of the trace file
  services/                       GET     Service overview   (not implemented)
  services/foo/                   GET     Get info for the "foo" service   (not implemented)

To test with curl:

  curl --digest --user exscript-http:exscript-http --data @postorder localhost:8123/order/
"""

class HTTPHandler(RequestHandler):
    def get_response(self):
        data     = parse_qs(self.data)
        logger   = self.daemon.logger
        order_db = self.daemon.parent.get_order_db()

        if self.path == '/order/':
            logger.debug('Parsing order from HTTP request.')
            order = Order.from_xml(data['xml'][0])
            logger.debug('XML order parsed complete.')
            self.daemon.order_incoming_event(order)
            return 'application/json', json.dumps(order.get_id())

        elif self.path == '/order/get/':
            id    = int(self.args.get('id'))
            order = order_db.get_order(id = id)
            return order.toxml()

        elif self.path == '/order/count/':
            order_id   = self.args.get('order_id')
            service    = self.args.get('service')
            descr      = self.args.get('description')
            status     = self.args.get('status')
            created_by = self.args.get('created_by')
            n_orders   = order_db.count_orders(id          = order_id,
                                               service     = service,
                                               description = descr,
                                               status      = status,
                                               created_by  = created_by)
            return 'application/json', json.dumps(n_orders)

        elif self.path == '/order/status/':
            order_id = int(self.args['id'])
            order    = order_db.get_order(id = order_id)
            progress = order_db.get_order_progress_from_id(order_id)
            if not order:
                raise Exception('no such order id')
            closed = order.get_closed_timestamp()
            if closed is not None:
                closed = str(closed)
            response = {'status':   order.get_status(),
                        'progress': progress,
                        'closed':   closed}
            return 'application/json', json.dumps(response)

        elif self.path == '/order/list/':
            # Fetch the orders.
            offset     = int(self.args.get('offset', 0))
            limit      = min(100, int(self.args.get('limit', 100)))
            order_id   = self.args.get('order_id')
            service    = self.args.get('service')
            descr      = self.args.get('description')
            status     = self.args.get('status')
            created_by = self.args.get('created_by')
            orders     = order_db.get_orders(id          = order_id,
                                             service     = service,
                                             description = descr,
                                             status      = status,
                                             created_by  = created_by,
                                             offset      = offset,
                                             limit       = limit)

            # Assemble an XML document containing the orders.
            xml = etree.Element('xml')
            for order in orders:
                xml.append(order.toetree())
            return etree.tostring(xml, pretty_print = True)

        elif self.path == '/task/get/':
            id   = int(self.args.get('id'))
            task = order_db.get_task(id = id)
            return task.toxml()

        elif self.path == '/task/count/':
            order_id = self.args.get('order_id')
            if order_id:
                n_tasks = order_db.count_tasks(order_id = int(order_id))
            else:
                n_tasks = order_db.count_tasks()
            return 'application/json', json.dumps(n_tasks)

        elif self.path == '/task/list/':
            # Fetch the tasks.
            order_id = int(self.args.get('order_id'))
            offset   = int(self.args.get('offset', 0))
            limit    = min(100, int(self.args.get('limit', 100)))
            tasks    = order_db.get_tasks(order_id = order_id,
                                          offset   = offset,
                                          limit    = limit)

            # Assemble an XML document containing the orders.
            xml = etree.Element('xml')
            for task in tasks:
                xml.append(task.toetree())
            return etree.tostring(xml, pretty_print = True)

        elif self.path == '/log/':
            task_id  = int(self.args.get('task_id'))
            task     = order_db.get_task(id = task_id)
            filename = task.get_logfile()
            if filename and os.path.isfile(filename):
                with open(filename) as file:
                    return file.read()
            else:
                return ''

        elif self.path == '/trace/':
            task_id  = int(self.args.get('task_id'))
            task     = order_db.get_task(id = task_id)
            filename = task.get_tracefile()
            if filename and os.path.isfile(filename):
                with open(filename) as file:
                    return file.read()
            else:
                return ''

        else:
            raise Exception('no such API call')

    def handle_POST(self):
        self.daemon = self.server.user_data
        self.daemon.logger.debug('Receiving HTTP request.')
        try:
            response = self.get_response()
        except Exception, e:
            tb = format_exc()
            print tb
            self.send_response(500)
            self.end_headers()
            self.wfile.write(tb.encode('utf8'))
            self.daemon.logger.error('Exception: %s' % tb)
        else:
            self.send_response(200)
            try:
                mime_type, response = response
            except ValueError:
                self.daemon.logger.debug('Sending HTTP/text response.')
            else:
                self.daemon.logger.debug('Sending HTTP/json response.')
                self.send_header('Content-type', mime_type)
            self.end_headers()
            self.wfile.write(response)
        self.daemon.logger.debug('HTTP call complete.')

    def handle_GET(self):
        self.handle_POST()

    def log_message(self, format, *args):
        daemon = self.server.user_data
        daemon.logger.info(self.address_string() + ' - ' + format % args)

class HTTPDaemon(object):
    def __init__(self,
                 parent,
                 name,
                 logger,
                 address = '',
                 port    = 80):
        self.parent               = parent
        self.name                 = name
        self.logger               = logger
        self.order_incoming_event = Event()
        self.address              = address
        self.port                 = port
        addr                      = self.address, self.port
        self.server               = HTTPd(addr, HTTPHandler, self)
        self.parent.daemon_added(self)

    def log(self, order, message, level = logging.INFO):
        msg = '%s/%s/%s: %s' % (self.name,
                                order.get_service_name(),
                                order.get_id(),
                                message)
        self.logger.log(level, msg)

    def add_account(self, account):
        user     = account.get_name()
        password = account.get_password()
        self.server.add_account(user, password)

    def run(self):
        address  = (self.address or '*') + ':' + str(self.port)
        nameaddr = self.name, address
        self.logger.info('HTTPDaemon %s/%s starting.' % nameaddr)
        try:
            self.logger.info('HTTPDaemon %s/%s listening' % nameaddr)
            self.server.serve_forever()
        except KeyboardInterrupt:
            print '^C received, shutting down server'
            self.logger.info('Shutting down normally.')
            self.server.socket.close()

########NEW FILE########
__FILENAME__ = Order
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Represents a call to a service.
"""
import os
from getpass            import getuser
from datetime           import datetime
from tempfile           import NamedTemporaryFile
from lxml               import etree
from Exscript.util.file import get_hosts_from_csv
from Exscriptd.DBObject import DBObject
from Exscriptd.xml      import add_hosts_to_etree

class Order(DBObject):
    """
    An order includes all information that is required to make a
    service call.
    """

    def __init__(self, service_name):
        """
        Constructor. The service_name defines the service to whom
        the order is delivered. In other words, this is the
        service name is assigned in the config file of the server.

        @type  service_name: str
        @param service_name: The service that handles the order.
        """
        DBObject.__init__(self)
        self.id         = None
        self.status     = 'new'
        self.service    = service_name
        self.descr      = ''
        self.created    = datetime.utcnow()
        self.closed     = None
        self.progress   = .0
        self.created_by = getuser()
        self.xml        = etree.Element('order', service = self.service)

    def __repr__(self):
        return "<Order('%s','%s','%s')>" % (self.id, self.service, self.status)

    @staticmethod
    def from_etree(order_node):
        """
        Creates a new instance by parsing the given XML.

        @type  order_node: lxml.etree.Element
        @param order_node: The order node of an etree.
        @rtype:  Order
        @return: A new instance of an order.
        """
        # Parse required attributes.
        descr_node       = order_node.find('description')
        order_id         = order_node.get('id')
        order            = Order(order_node.get('service'))
        order.xml        = order_node
        order.id         = order_id is not None and int(order_id) or None
        order.status     = order_node.get('status',     order.status)
        order.created_by = order_node.get('created-by', order.created_by)
        created          = order_node.get('created')
        closed           = order_node.get('closed')
        progress         = order_node.get('progress')
        if descr_node is not None:
            order.descr = descr_node.text
        if created:
            created = created.split('.', 1)[0]
            created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
            order.created = created
        if closed:
            closed = closed.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
            order.closed = closed
        if progress is not None:
            order.progress = float(progress)
        return order

    @staticmethod
    def from_xml(xml):
        """
        Creates a new instance by parsing the given XML.

        @type  xml: str
        @param xml: A string containing an XML formatted order.
        @rtype:  Order
        @return: A new instance of an order.
        """
        xml = etree.fromstring(xml)
        return Order.from_etree(xml.find('order'))

    @staticmethod
    def from_xml_file(filename):
        """
        Creates a new instance by reading the given XML file.

        @type  filename: str
        @param filename: A file containing an XML formatted order.
        @rtype:  Order
        @return: A new instance of an order.
        """
        # Parse required attributes.
        xml = etree.parse(filename)
        return Order.from_etree(xml.find('order'))

    @staticmethod
    def from_csv_file(service, filename, encoding = 'utf-8'):
        """
        Creates a new instance by reading the given CSV file.

        @type  service: str
        @param service: The service name.
        @type  filename: str
        @param filename: A file containing a CSV formatted list of hosts.
        @type  encoding: str
        @param encoding: The name of the encoding.
        @rtype:  Order
        @return: A new instance of an order.
        """
        order = Order(service)
        hosts = get_hosts_from_csv(filename, encoding = encoding)
        add_hosts_to_etree(order.xml, hosts)
        return order

    def toetree(self):
        """
        Returns the order as an lxml etree.

        @rtype:  lxml.etree
        @return: The resulting tree.
        """
        if self.id:
            self.xml.attrib['id'] = str(self.id)
        if self.status:
            self.xml.attrib['status'] = str(self.status)
        if self.created:
            self.xml.attrib['created'] = str(self.created)
        if self.closed:
            self.xml.attrib['closed'] = str(self.closed)
        if self.progress:
            self.xml.attrib['progress'] = str(self.progress)
        if self.descr:
            etree.SubElement(self.xml, 'description').text = str(self.descr)
        if self.created_by:
            self.xml.attrib['created-by'] = str(self.created_by)
        return self.xml

    def toxml(self, pretty = True):
        """
        Returns the order as an XML formatted string.

        @type  pretty: bool
        @param pretty: Whether to format the XML in a human readable way.
        @rtype:  str
        @return: The XML representing the order.
        """
        xml   = etree.Element('xml')
        order = self.toetree()
        xml.append(order)
        return etree.tostring(xml, pretty_print = pretty)

    def todict(self):
        """
        Returns the order's attributes as one flat dictionary.

        @rtype:  dict
        @return: A dictionary representing the order.
        """
        values = dict(service     = self.get_service_name(),
                      status      = self.get_status(),
                      description = self.get_description(),
                      progress    = self.get_progress(),
                      created     = self.get_created_timestamp(),
                      closed      = self.get_closed_timestamp(),
                      created_by  = self.get_created_by())
        if self.id:
            values['id'] = self.get_id()
        return values

    def write(self, thefile):
        """
        Export the order as an XML file.

        @type  thefile: str or file object
        @param thefile: XML
        """
        if hasattr(thefile, 'write'):
            thefile.write(self.toxml())
            return

        dirname = os.path.dirname(thefile)
        with NamedTemporaryFile(dir    = dirname,
                                prefix = '.',
                                delete = False) as tmpfile:
            tmpfile.write(self.toxml())
            tmpfile.flush()
            os.chmod(tmpfile.name, 0644)
            os.rename(tmpfile.name, thefile)

    def is_valid(self):
        """
        Returns True if the order validates, False otherwise.

        @rtype:  bool
        @return: True if the order is valid, False otherwise.
        """
        return True #FIXME

    def get_id(self):
        """
        Returns the order id.

        @rtype:  str
        @return: The id of the order.
        """
        return self.id

    def set_service_name(self, name):
        """
        Set the name of the service that is ordered.

        @type  name: str
        @param name: The service name.
        """
        self.service = name

    def get_service_name(self):
        """
        Returns the name of the service that is ordered.

        @rtype:  str
        @return: The service name.
        """
        return self.service

    def get_status(self):
        """
        Returns the order status.

        @rtype:  str
        @return: The order status.
        """
        return self.status

    def set_description(self, description):
        """
        Sets a freely defined description on the order.

        @type  description: str
        @param description: The new description.
        """
        self.descr = description and str(description) or ''

    def get_description(self):
        """
        Returns the description of the order.

        @rtype:  str
        @return: The description.
        """
        return self.descr

    def get_created_timestamp(self):
        """
        Returns the time at which the order was created.

        @rtype:  datetime.datetime
        @return: The timestamp.
        """
        return self.created

    def get_closed_timestamp(self):
        """
        Returns the time at which the order was closed, or None if the
        order is still open.

        @rtype:  datetime.datetime|None
        @return: The timestamp or None.
        """
        return self.closed

    def get_created_by(self):
        """
        Returns the username of the user who opened the order. Defaults
        to whatever getpass.getuser() returns.

        @rtype:  str
        @return: The value of the 'created-by' field.
        """
        return self.created_by

    def get_progress(self):
        """
        Returns the progress of the order.

        @rtype:  float|None
        @return: The progress (1.0 is max).
        """
        return self.progress

    def get_progress_percent(self):
        """
        Returns the progress as a string, in percent.

        @rtype:  str
        @return: The progress in percent.
        """
        return '%.1f' % (self.progress * 100.0)

    def close(self):
        """
        Marks the order closed.
        """
        self.closed = datetime.utcnow()

########NEW FILE########
__FILENAME__ = OrderDB
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from datetime import datetime
import sqlalchemy as sa
from Exscript.util.cast import to_list
from Exscript.util.impl import synchronized
from Exscriptd.Order import Order
from Exscriptd.Task import Task

# Note: The synchronized decorator is used because
# sqlite does not support concurrent writes, so we need to
# do this to have graceful locking (rather than sqlite's
# hard locking).

class OrderDB(object):
    """
    The main interface for accessing the database.
    """

    def __init__(self, engine):
        """
        Instantiates a new OrderDB.
        
        @type  engine: object
        @param engine: An sqlalchemy database engine.
        @rtype:  OrderDB
        @return: The new instance.
        """
        self.engine        = engine
        self.metadata      = sa.MetaData(self.engine)
        self._table_prefix = 'exscriptd_'
        self._table_map    = {}
        self.__update_table_names()

    def __add_table(self, table):
        """
        Adds a new table to the internal table list.
        
        @type  table: Table
        @param table: An sqlalchemy table.
        """
        pfx = self._table_prefix
        self._table_map[table.name[len(pfx):]] = table

    def __update_table_names(self):
        """
        Adds all tables to the internal table list.
        """
        pfx = self._table_prefix
        self.__add_table(sa.Table(pfx + 'order', self.metadata,
            sa.Column('id',          sa.Integer,    primary_key = True),
            sa.Column('service',     sa.String(50), index = True),
            sa.Column('status',      sa.String(20), index = True),
            sa.Column('description', sa.String(150)),
            sa.Column('created',     sa.DateTime,   default = datetime.utcnow),
            sa.Column('closed',      sa.DateTime),
            sa.Column('created_by',  sa.String(50)),
            mysql_engine = 'INNODB'
        ))

        self.__add_table(sa.Table(pfx + 'task', self.metadata,
            sa.Column('id',        sa.Integer,     primary_key = True),
            sa.Column('order_id',  sa.Integer,     index = True),
            sa.Column('job_id',    sa.String(33),  index = True),
            sa.Column('name',      sa.String(150), index = True),
            sa.Column('status',    sa.String(150), index = True),
            sa.Column('progress',  sa.Float,       default = 0.0),
            sa.Column('started',   sa.DateTime,    default = datetime.utcnow),
            sa.Column('closed',    sa.DateTime,    index = True),
            sa.Column('logfile',   sa.String(250)),
            sa.Column('tracefile', sa.String(250)),
            sa.Column('vars',      sa.PickleType()),
            sa.ForeignKeyConstraint(['order_id'], [pfx + 'order.id'], ondelete = 'CASCADE'),
            mysql_engine = 'INNODB'
        ))


    @synchronized
    def install(self):
        """
        Installs (or upgrades) database tables.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        self.metadata.create_all()
        return True

    @synchronized
    def uninstall(self):
        """
        Drops all tables from the database. Use with care.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        self.metadata.drop_all()
        return True

    @synchronized
    def clear_database(self):
        """
        Drops the content of any database table used by this library.
        Use with care.

        Wipes out everything, including types, actions, resources and acls.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        delete = self._table_map['order'].delete()
        delete.execute()
        return True

    def debug(self, debug = True):
        """
        Enable/disable debugging.

        @type  debug: Boolean
        @param debug: True to enable debugging.
        """
        self.engine.echo = debug

    def set_table_prefix(self, prefix):
        """
        Define a string that is prefixed to all table names in the database.
        Default is 'guard_'.

        @type  prefix: string
        @param prefix: The new prefix.
        """
        self._table_prefix = prefix
        self.__update_table_names()

    def get_table_prefix(self):
        """
        Returns the current database table prefix.
        
        @rtype:  string
        @return: The current prefix.
        """
        return self._table_prefix

    @synchronized
    def __add_task(self, task):
        """
        Inserts the given task into the database.
        """
        if task is None:
            raise AttributeError('task argument must not be None')
        if task.order_id is None:
            raise AttributeError('order_id must not be None')

        if not task.is_dirty():
            return

        # Insert the task
        insert  = self._table_map['task'].insert()
        result  = insert.execute(**task.todict())
        task_id = result.last_inserted_ids()[0]

        task.untouch()
        return task_id

    @synchronized
    def __save_task(self, task):
        """
        Inserts or updates the given task into the database.
        """
        if task is None:
            raise AttributeError('task argument must not be None')
        if task.order_id is None:
            raise AttributeError('order_id must not be None')

        if not task.is_dirty():
            return

        # Insert or update the task.
        tbl_t  = self._table_map['task']
        fields = task.todict()
        if task.id is None:
            query   = tbl_t.insert()
            result  = query.execute(**fields)
            task.id = result.last_inserted_ids()[0]
        else:
            query   = tbl_t.update(tbl_t.c.id == task.id)
            result  = query.execute(**fields)

        task.untouch()
        return task.id

    def __get_task_from_row(self, row):
        assert row is not None
        tbl_t          = self._table_map['task']
        task           = Task(row[tbl_t.c.order_id], row[tbl_t.c.name])
        task.id        = row[tbl_t.c.id]
        task.job_id    = row[tbl_t.c.job_id]
        task.status    = row[tbl_t.c.status]
        task.progress  = row[tbl_t.c.progress]
        task.started   = row[tbl_t.c.started]
        task.closed    = row[tbl_t.c.closed]
        task.logfile   = row[tbl_t.c.logfile]
        task.tracefile = row[tbl_t.c.tracefile]
        task.vars      = row[tbl_t.c.vars]
        task.untouch()
        return task

    def __get_tasks_from_query(self, query):
        """
        Returns a list of tasks.
        """
        assert query is not None
        result = query.execute()
        return [self.__get_task_from_row(row) for row in result]

    def __get_tasks_cond(self, **kwargs):
        tbl_t = self._table_map['task']

        # Search conditions.
        where = None
        for field in ('id',
                      'order_id',
                      'job_id',
                      'name',
                      'status',
                      'opened',
                      'closed'):
            if field in kwargs:
                cond = None
                for value in to_list(kwargs.get(field)):
                    cond = sa.or_(cond, tbl_t.c[field] == value)
                where = sa.and_(where, cond)

        return where

    def __get_tasks_query(self, fields, offset, limit, **kwargs):
        tbl_t = self._table_map['task']
        where = self.__get_tasks_cond(**kwargs)
        return sa.select(fields,
                         where,
                         from_obj = [tbl_t],
                         order_by = [sa.desc(tbl_t.c.id)],
                         offset   = offset,
                         limit    = limit)

    def __get_orders_cond(self, **kwargs):
        tbl_o = self._table_map['order']

        # Search conditions.
        where = None
        for field in ('id', 'service', 'description', 'status', 'created_by'):
            values = kwargs.get(field)
            if values is not None:
                cond = None
                for value in to_list(values):
                    cond = sa.or_(cond, tbl_o.c[field].like(value))
                where = sa.and_(where, cond)

        return where

    def __get_orders_query(self, offset = 0, limit = None, **kwargs):
        tbl_o  = self._table_map['order']
        tbl_t  = self._table_map['task']
        where  = self.__get_orders_cond(**kwargs)
        fields = list(tbl_o.c)
        table  = tbl_o.outerjoin(tbl_t, tbl_t.c.order_id == tbl_o.c.id)
        fields.append(sa.func.avg(tbl_t.c.progress).label('avg_progress'))
        return sa.select(fields,
                         where,
                         from_obj   = [table],
                         group_by   = [tbl_o.c.id],
                         order_by   = [sa.desc(tbl_o.c.id)],
                         offset     = offset,
                         limit      = limit)

    @synchronized
    def __add_order(self, order):
        """
        Inserts the given order into the database.
        """
        if order is None:
            raise AttributeError('order argument must not be None')

        # Insert the order
        insert   = self._table_map['order'].insert()
        fields   = dict(k for k in order.todict().iteritems()
                        if k[0] not in ('id', 'created', 'progress'))
        result   = insert.execute(**fields)
        order.id = result.last_inserted_ids()[0]
        return order.id

    @synchronized
    def __save_order(self, order):
        """
        Updates the given order in the database. Does nothing if the
        order is not yet in the database.

        @type  order: Order
        @param order: The order to be saved.
        """
        if order is None:
            raise AttributeError('order argument must not be None')

        # Check if the order already exists.
        if order.id:
            theorder = self.get_order(id = order.get_id())
        else:
            theorder = None

        # Insert or update it.
        if not theorder:
            return self.add_order(order)
        table  = self._table_map['order']
        fields = dict(k for k in order.todict().iteritems()
                      if k[0] not in ('id', 'created', 'progress'))
        query  = table.update(table.c.id == order.get_id())
        query.execute(**fields)

    def __get_order_from_row(self, row):
        assert row is not None
        tbl_a            = self._table_map['order']
        order            = Order(row[tbl_a.c.service])
        order.id         = row[tbl_a.c.id]
        order.status     = row[tbl_a.c.status]
        order.created    = row[tbl_a.c.created]
        order.closed     = row[tbl_a.c.closed]
        order.created_by = row[tbl_a.c.created_by]
        order.set_description(row[tbl_a.c.description])
        try:
            order.progress = float(row.avg_progress)
        except TypeError: # Order has no tasks
            if order.closed:
                order.progress = 1.0
            else:
                order.progress = .0
        return order

    def __get_orders_from_query(self, query):
        """
        Returns a list of orders.
        """
        assert query is not None
        result = query.execute()
        return [self.__get_order_from_row(row) for row in result]

    def count_orders(self, **kwargs):
        """
        Returns the total number of orders matching the given criteria.

        @rtype:  int
        @return: The number of orders.
        @type  kwargs: dict
        @param kwargs: For a list of allowed keys see get_orders().
        """
        tbl_o = self._table_map['order']
        where = self.__get_orders_cond(**kwargs)
        return tbl_o.count(where).execute().fetchone()[0]

    def get_order(self, **kwargs):
        """
        Like get_orders(), but
          - Returns None, if no match was found.
          - Returns the order, if exactly one match was found.
          - Raises an error if more than one match was found.

        @type  kwargs: dict
        @param kwargs: For a list of allowed keys see get_orders().
        @rtype:  Order
        @return: The order or None.
        """
        result = self.get_orders(0, 2, **kwargs)
        if len(result) == 0:
            return None
        elif len(result) > 1:
            raise IndexError('Too many results')
        return result[0]

    def get_orders(self, offset = 0, limit = None, **kwargs):
        """
        Returns all orders that match the given criteria.

        @type  offset: int
        @param offset: The offset of the first item to be returned.
        @type  limit: int
        @param limit: The maximum number of items that is returned.
        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - id - the id of the order (str)
                         - service - the service name (str)
                         - description - the order description (str)
                         - status - the status (str)
                       All values may also be lists (logical OR).
        @rtype:  list[Order]
        @return: The list of orders.
        """
        select = self.__get_orders_query(avg    = True,
                                         offset = offset,
                                         limit  = limit,
                                         **kwargs)
        return self.__get_orders_from_query(select)

    def add_order(self, orders):
        """
        Inserts the given order into the database.

        @type  orders: Order|list[Order]
        @param orders: The orders to be added.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')
        with self.engine.contextual_connect(close_with_result = True).begin():
            for order in to_list(orders):
                self.__add_order(order)

    def close_open_orders(self):
        """
        Sets the 'closed' timestamp of all orders that have none, without
        changing the status field.
        """
        closed = datetime.utcnow()
        tbl_o  = self._table_map['order']
        tbl_t  = self._table_map['task']
        query1 = tbl_t.update(tbl_t.c.closed == None)
        query2 = tbl_o.update(tbl_o.c.closed == None)
        query1.execute(closed = closed)
        query2.execute(closed = closed)

    def save_order(self, orders):
        """
        Updates the given orders in the database. Does nothing if
        the order doesn't exist.

        @type  orders: Order|list[Order]
        @param orders: The order to be saved.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')

        with self.engine.contextual_connect(close_with_result = True).begin():
            for order in to_list(orders):
                self.__save_order(order)

    def get_order_progress_from_id(self, id):
        """
        Returns the progress of the order in percent.

        @type  id: int
        @param id: The id of the order.
        @rtype:  float
        @return: A float between 0.0 and 1.0
        """
        order = self.get_order(id = id)
        return order.get_progress()

    def count_tasks(self, **kwargs):
        """
        Returns the number of matching tasks in the DB.

        @type  kwargs: dict
        @param kwargs: See L{get_tasks()}.
        @rtype:  int
        @return: The number of tasks.
        """
        tbl_t = self._table_map['task']
        where = self.__get_tasks_cond(**kwargs)
        query = tbl_t.count(where)
        return query.execute().fetchone()[0]

    def get_task(self, **kwargs):
        """
        Like get_tasks(), but
          - Returns None, if no match was found.
          - Returns the task, if exactly one match was found.
          - Raises an error if more than one match was found.

        @type  kwargs: dict
        @param kwargs: For a list of allowed keys see get_tasks().
        @rtype:  Task
        @return: The task or None.
        """
        result = self.get_tasks(0, 2, **kwargs)
        if len(result) == 0:
            return None
        elif len(result) > 1:
            raise IndexError('Too many results')
        return result[0]

    def get_tasks(self, offset = 0, limit = None, **kwargs):
        """
        Returns all tasks that match the given criteria.

        @type  offset: int
        @param offset: The offset of the first item to be returned.
        @type  limit: int
        @param limit: The maximum number of items that is returned.
        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - id - the id of the task (int)
                         - order_id - the order id of the task (int)
                         - job_id - the job id of the task (str)
                         - name - the name (str)
                         - status - the status (str)
                       All values may also be lists (logical OR).
        @rtype:  list[Task]
        @return: The list of tasks.
        """
        tbl_t  = self._table_map['task']
        fields = list(tbl_t.c)
        query  = self.__get_tasks_query(fields, offset, limit, **kwargs)
        return self.__get_tasks_from_query(query)

    def save_task(self, task):
        """
        Inserts or updates the given task in the database.

        @type  order: Order
        @param order: The order for which a task is added.
        @type  task: Task
        @param task: The task to be saved.
        """
        if task is None:
            raise AttributeError('task argument must not be None')
        if task.order_id is None:
            raise AttributeError('order id must not be None')

        if not task.is_dirty():
            return

        return self.__save_task(task)

    @synchronized
    def mark_tasks(self, new_status, offset = 0, limit = None, **kwargs):
        """
        Returns all tasks that match the given criteria and changes
        their status to the given value.

        @type  new_status: str
        @param new_status: The new status.
        @type  offset: int
        @param offset: The offset of the first item to be returned.
        @type  limit: int
        @param limit: The maximum number of items that is returned.
        @type  kwargs: dict
        @param kwargs: See L{get_tasks()}.
        @rtype:  list[Task]
        @return: The list of tasks.
        """
        tbl_t = self._table_map['task']

        # Find the ids of the matching tasks.
        where     = self.__get_tasks_cond(**kwargs)
        id_select = sa.select([tbl_t.c.id],
                              where,
                              from_obj = [tbl_t],
                              order_by = [tbl_t.c.id],
                              offset   = offset,
                              limit    = limit)
        id_list = [row.id for row in id_select.execute()]

        # Update the status of those tasks.
        query  = tbl_t.update(tbl_t.c.id.in_(id_list))
        result = query.execute(status = new_status)

        # Now create a Task object for each of those tasks.
        all_select = tbl_t.select(tbl_t.c.id.in_(id_list),
                                  order_by = [tbl_t.c.id])
        return self.__get_tasks_from_query(all_select)

########NEW FILE########
__FILENAME__ = Service
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import __builtin__
import sys
import os
from Exscriptd.util import find_module_recursive
from Exscriptd.ConfigReader import ConfigReader

class Service(object):
    def __init__(self,
                 parent,
                 name,
                 module,
                 cfg_dir,
                 main_cfg,
                 queue_name = None):
        self.parent     = parent
        self.name       = name
        self.cfg_dir    = cfg_dir
        self.main_cfg   = main_cfg
        self.queue_name = queue_name
        self.parent.service_added(self)

        try:
            fp, filename, description = find_module_recursive(module)
        except ImportError:
            raise Exception('invalid module name: %s' % module)
        filename = os.path.join(filename, 'service.py')
        with open(filename) as file:
            content = file.read()
        code                       = compile(content, filename, 'exec')
        self.vars                  = {}
        self.vars['__builtin__']   = __builtin__
        self.vars['__file__']      = filename
        self.vars['__module__']    = module
        self.vars['__service__']   = self
        self.vars['__exscriptd__'] = parent
        self.vars['__main_cfg__']  = self.main_cfg

        # Load the module using evil path manipulation, but oh well...
        # can't think of a sane way to do this.
        sys.path.insert(0, os.path.dirname(filename))
        result = eval(code, self.vars)
        sys.path.pop(0)

        self.check_func = self.vars.get('check')
        self.enter_func = self.vars.get('enter')

        if not self.enter_func:
            msg = filename + ': required function enter() not found.'
            raise Exception(msg)

    def get_queue_name(self):
        return self.queue_name

    def read_config(self, name, parser = ConfigReader):
        filename = os.path.join(self.cfg_dir, name)
        return parser(filename, parent = self.main_cfg)

    def check(self, order):
        if self.check_func:
            return self.check_func(order)
        return True

    def enter(self, order):
        return self.enter_func(order)

    def run_function(self, name, *args):
        return self.vars.get(name)(*args)

########NEW FILE########
__FILENAME__ = Task
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Represents an activity within an order.
"""
import os
import sys
from datetime import datetime
from lxml import etree
from Exscriptd.DBObject import DBObject
from Exscript.util.event import Event

class Task(DBObject):
    def __init__(self, order_id, name):
        DBObject.__init__(self)
        self.id            = None
        self.order_id      = order_id
        self.job_id        = None   # reference to Exscript.workqueue.Job.id
        self.name          = name
        self.status        = 'new'
        self.progress      = .0
        self.started       = datetime.utcnow()
        self.closed        = None
        self.logfile       = None
        self.tracefile     = None
        self.vars          = {}
        self.changed_event = Event()

    @staticmethod
    def from_etree(task_node):
        """
        Creates a new instance by parsing the given XML.

        @type  task_node: lxml.etree.Element
        @param task_node: The task node of an etree.
        @rtype:  Task
        @return: A new instance of an task.
        """
        # Parse required attributes.
        name           = task_node.find('name').text
        order_id       = task_node.get('order_id')
        task           = Task(order_id, name)
        task.id        = int(task_node.get('id'))
        task.status    = task_node.find('status').text
        task.progress  = float(task_node.find('progress').text)
        started_node   = task_node.find('started')
        closed_node    = task_node.find('closed')
        logfile_node   = task_node.find('logfile')
        tracefile_node = task_node.find('tracefile')
        if started_node is not None:
            started = started_node.text.split('.', 1)[0]
            started = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
            task.started = started
        if closed_node is not None:
            closed = closed_node.text.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
            task.closed = closed
        if logfile_node is not None:
            task.logfile = logfile_node.text
        if tracefile_node is not None:
            task.tracefile = tracefile_node.text
        return task

    @staticmethod
    def from_xml(xml):
        """
        Creates a new instance by parsing the given XML.

        @type  xml: str
        @param xml: A string containing an XML formatted task.
        @rtype:  Task
        @return: A new instance of an task.
        """
        xml = etree.fromstring(xml)
        return Task.from_etree(xml.find('task'))

    def toetree(self):
        """
        Returns the task as an lxml etree.

        @rtype:  lxml.etree
        @return: The resulting tree.
        """
        task = etree.Element('task',
                             id       = str(self.id),
                             order_id = str(self.order_id))
        etree.SubElement(task, 'name').text     = str(self.name)
        etree.SubElement(task, 'status').text   = str(self.status)
        etree.SubElement(task, 'progress').text = str(self.progress)
        if self.started:
            etree.SubElement(task, 'started').text = str(self.started)
        if self.closed:
            etree.SubElement(task, 'closed').text = str(self.closed)
        if self.logfile:
            etree.SubElement(task, 'logfile').text = str(self.logfile)
        if self.tracefile:
            etree.SubElement(task, 'tracefile').text = str(self.tracefile)
        return task

    def toxml(self, pretty = True):
        """
        Returns the task as an XML formatted string.

        @type  pretty: bool
        @param pretty: Whether to format the XML in a human readable way.
        @rtype:  str
        @return: The XML representing the task.
        """
        xml  = etree.Element('xml')
        task = self.toetree()
        xml.append(task)
        return etree.tostring(xml, pretty_print = pretty)

    def todict(self):
        result = dict(order_id  = self.order_id,
                      job_id    = self.get_job_id(),
                      name      = self.get_name(),
                      status    = self.get_status(),
                      progress  = self.get_progress(),
                      started   = self.get_started_timestamp(),
                      closed    = self.get_closed_timestamp(),
                      logfile   = self.get_logfile(),
                      tracefile = self.get_tracefile(),
                      vars      = self.vars)
        if self.id is not None:
            result['id'] = self.id
        return result

    def get_id(self):
        """
        Returns the task id.

        @rtype:  str
        @return: The id of the task.
        """
        return self.id

    def set_job_id(self, job_id):
        """
        Associate the task with the Exscript.workqueue.Job with the given
        id.

        @type  job_id: int
        @param job_id: The id of the job.
        """
        self.touch()
        self.job_id = job_id
        self.set_status('queued')

    def get_job_id(self):
        """
        Returns the associated Exscript.workqueue.Job, or None.

        @type  job_id: str
        @param job_id: The id of the task.
        """
        return self.job_id

    def set_name(self, name):
        """
        Change the task name.

        @type  name: string
        @param name: A human readable name.
        """
        self.touch()
        self.name = name

    def get_name(self):
        """
        Returns the current name as a string.

        @rtype:  string
        @return: A human readable name.
        """
        return self.name

    def set_status(self, status):
        """
        Change the current status.

        @type  status: string
        @param status: A human readable status.
        """
        self.touch()
        self.status = status
        self.changed_event(self)

    def get_status(self):
        """
        Returns the current status as a string.

        @rtype:  string
        @return: A human readable status.
        """
        return self.status

    def set_progress(self, progress):
        """
        Change the current progress.

        @type  progress: float
        @param progress: The new progress.
        """
        self.touch()
        self.progress = progress

    def get_progress(self):
        """
        Returns the progress as a float between 0.0 and 1.0.

        @rtype:  float
        @return: The progress.
        """
        return self.progress

    def get_progress_percent(self):
        """
        Returns the progress as a string, in percent.

        @rtype:  str
        @return: The progress in percent.
        """
        return '%.1f' % (self.progress * 100.0)

    def get_started_timestamp(self):
        """
        Returns the time at which the task was started.

        @rtype:  datetime.datetime
        @return: The timestamp.
        """
        return self.started

    def close(self, status = None):
        """
        Marks the task closed.

        @type  status: string
        @param status: A human readable status, or None to leave unchanged.
        """
        self.touch()
        self.closed = datetime.utcnow()
        if status:
            self.set_status(status)

    def completed(self):
        """
        Like close(), but sets the status to 'completed' and the progress
        to 100%.
        """
        self.close('completed')
        self.set_progress(1.0)

    def get_closed_timestamp(self):
        """
        Returns the time at which the task was closed, or None if the
        task is still open.

        @rtype:  datetime.datetime|None
        @return: The timestamp or None.
        """
        return self.closed

    def set_logfile(self, *logfile):
        """
        Set the name of the logfile, and set the name of the tracefile
        to the same name with '.error' appended.

        @type  logfile: string
        @param logfile: A filename.
        """
        self.touch()
        self.logfile   = os.path.join(*logfile)
        self.tracefile = self.logfile + '.error'

    def get_logfile(self):
        """
        Returns the name of the logfile as a string.

        @rtype:  string|None
        @return: A filename, or None.
        """
        return self.logfile

    def set_tracefile(self, tracefile):
        """
        Set the name of the tracefile.

        @type  tracefile: string
        @param tracefile: A filename.
        """
        self.touch()
        self.tracefile = os.path.join(*tracefile)

    def get_tracefile(self):
        """
        Returns the name of the tracefile as a string.

        @rtype:  string|None
        @return: A filename, or None.
        """
        return self.tracefile

    def set(self, key, value):
        """
        Defines a variable that is carried along with the task.
        The value *must* be pickleable.
        """
        self.vars[key] = value

    def get(self, key, default = None):
        """
        Returns the value as previously defined by L{Task.set()}.
        """
        return self.vars.get(key, default)

########NEW FILE########
__FILENAME__ = util
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
import imp

def resolve_variables(variables, string):
    def variable_sub_cb(match):
        field   = match.group(0)
        escape  = match.group(1)
        varname = match.group(2)
        value   = variables.get(varname)

        # Check the variable name syntax.
        if escape:
            return '$' + varname
        elif varname == '':
            return '$'

        # Check the variable value.
        if value is None:
            msg = 'Undefined variable %s' % repr(varname)
            raise Exception(msg)
        return str(value)

    string_re = re.compile(r'(\\?)\$([\w_]*)')
    return string_re.sub(variable_sub_cb, string)

def find_module_recursive(name, path = None):
    if not '.' in name:
        return imp.find_module(name, path)
    parent, children = name.split('.', 1)
    module = imp.find_module(parent, path)
    path   = module[1]
    return find_module_recursive(children, [path])

def synchronized(func):
    """
    Decorator for synchronizing method access.
    """
    def wrapped(self, *args, **kwargs):
        try:
            rlock = self._sync_lock
        except AttributeError:
            from threading import RLock
            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        with rlock:
            return func(self, *args, **kwargs)

    wrapped.__name__ = func.__name__
    wrapped.__dict__ = func.__dict__
    wrapped.__doc__ = func.__doc__
    return wrapped

########NEW FILE########
__FILENAME__ = xml
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Utilities for serializing/deserializing XML.
"""
from lxml import etree
import base64
import Exscript
from Exscript import PrivateKey

def get_list_from_etree(node):
    """
    Given a <list> node, this function looks for child elements
    and returns a list of strings::

        <list name="mylist">
          <list-item>foo</list-item>
          <list-item>bar</list-item>
        </list>

    @type  node: lxml.etree.ElementNode
    @param node: A node containing list-item elements.
    @rtype:  list(str)
    @return: A list of strings.
    """
    items = node.iterfind('list-item')
    if items is None:
        return []
    return [i.text.strip() for i in items if i.text is not None]

def add_list_to_etree(root, tag, thelist, name = None):
    """
    Given a list, this function creates the syntax shown in
    get_list_from_etree() and adds it to the given node.
    Returns the new list element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  thelist: list(str)
    @param thelist: A list of strings.
    @type  name: str
    @param name: The name attribute of the new node.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    if name:
        list_elem = etree.SubElement(root, tag, name = name)
    else:
        list_elem = etree.SubElement(root, tag)
    for value in thelist:
        item = etree.SubElement(list_elem, 'list-item')
        item.text = value
    return list_elem

def get_dict_from_etree(node):
    """
    Given a parent node, this function looks for child elements
    and returns a dictionary of arguments::

        <argument-list name="myargs">
          <variable name="myvar">myvalue</variable>
          <list name="mylist">
            <list-item>foo</list-item>
            <list-item>bar</list-item>
          </list>
        </argument-list>

    @type  node: lxml.etree.ElementNode
    @param node: A node containing variable elements.
    @rtype:  dict
    @return: A map of variables.
    """
    if node is None:
        return {}
    args = {}
    for child in node:
        name = child.get('name').strip()
        if child.tag == 'variable':
            args[name] = child.text.strip()
        elif child.tag == 'list':
            args[name] = get_list_from_etree(child)
        elif child.tag == 'map':
            args[name] = get_dict_from_etree(child)
        else:
            raise Exception('Invalid XML tag: %s' % child.tag)
    return args

def add_dict_to_etree(root, tag, thedict, name = None):
    """
    Given a dictionary, this function creates the syntax shown in
    get_dict_from_etree() and adds it to the given node.
    Returns the new dictionary element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  thedict: dict(str|list)
    @param thedict: A dictionary containing strings or lists.
    @type  name: str
    @param name: The name attribute of the new node.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    if name:
        arg_elem = etree.SubElement(root, tag, name = name)
    else:
        arg_elem = etree.SubElement(root, tag)
    for name, value in thedict.iteritems():
        if isinstance(value, list):
            add_list_to_etree(arg_elem, 'list', value, name = name)
        elif isinstance(value, dict):
            add_dict_to_etree(arg_elem, 'map', value, name = name)
        elif isinstance(value, str) or isinstance(value, unicode):
            variable = etree.SubElement(arg_elem, 'variable', name = name)
            variable.text = value
        else:
            raise ValueError('unknown variable type: ' + repr(value))
    return arg_elem

def get_host_from_etree(node):
    """
    Given a <host> node, this function returns a Exscript.Host instance.
    The following XML syntax is expected, whereby the <argument-list>
    element is optional::

        <host name="otherhost" address="10.0.0.2">
          <protocol>telnet</protocol>
          <tcp-port>23</tcp-port>
          <account>
            ...
          </account>
          <argument-list>
            <list name="mylist">
              <list-item>foo</list-item>
              <list-item>bar</list-item>
            </list>
          </argument-list>
        </host>

    The arguments are parsed using get_dict_from_etree() and attached
    to the host using Exscript.Host.set_all().

    @type  node: lxml.etree.ElementNode
    @param node: A <host> element.
    @rtype:  Exscript.Host
    @return: The resulting host.
    """
    name     = node.get('name', '').strip()
    address  = node.get('address', name).strip()
    protocol = node.findtext('protocol')
    tcp_port = node.findtext('tcp-port')
    arg_elem = node.find('argument-list')
    acc_elem = node.find('account')
    args     = get_dict_from_etree(arg_elem)
    host     = Exscript.Host(address)
    if not address:
        raise TypeError('host element without name or address')
    if name:
        host.set_name(name)
    if protocol:
        host.set_protocol(protocol)
    if tcp_port:
        host.set_tcp_port(int(tcp_port))
    if acc_elem is not None:
        account = get_account_from_etree(acc_elem)
        host.set_account(account)
    host.set_all(args)
    return host

def add_host_to_etree(root, tag, host):
    """
    Given a dictionary, this function creates the syntax shown in
    get_host_from_etree() and adds it to the given node.
    Returns the new host element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  host: Exscript.Host
    @param host: The host that is added.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    elem = etree.SubElement(root,
                            tag,
                            address = host.get_address(),
                            name    = host.get_name())
    if host.get_protocol() is not None:
        etree.SubElement(elem, 'protocol').text = host.get_protocol()
    if host.get_tcp_port() is not None:
        etree.SubElement(elem, 'tcp-port').text = str(host.get_tcp_port())
    account = host.get_account()
    if account:
        add_account_to_etree(elem, 'account', account)
    if host.get_all():
        add_dict_to_etree(elem, 'argument-list', host.get_all())
    return elem

def get_hosts_from_etree(node):
    """
    Given an lxml.etree node, this function looks for <host> tags and
    returns a list of Exscript.Host instances. The following XML syntax
    is expected, whereby the <argument-list> element is optional::

        <root>
           <host name="localhost" address="10.0.0.1"/>
           <host name="otherhost" address="10.0.0.2">
             <argument-list>
               <list name="mylist">
                 <list-item>foo</list-item>
                 <list-item>bar</list-item>
               </list>
             </argument-list>
           </host>
        </root>

    The arguments are parsed using get_arguments_from_etree() and attached
    to the host using Exscript.Host.set().

    @type  node: lxml.etree.ElementNode
    @param node: A node containing <host> elements.
    @rtype:  list(Exscript.Host)
    @return: A list of hosts.
    """
    hosts = []
    for host_elem in node.iterfind('host'):
        host = get_host_from_etree(host_elem)
        hosts.append(host)
    return hosts

def add_hosts_to_etree(root, hosts):
    """
    Given a list of hosts, this function creates the syntax shown in
    get_hosts_from_etree() and adds it to the given node.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new elements are added.
    @type  hosts: list(Exscript.Host)
    @param hosts: A list of hosts.
    """
    for host in hosts:
        add_host_to_etree(root, 'host', host)

def _get_password_from_node(node):
    if node is None:
        return None
    thetype  = node.get('type', 'cleartext')
    password = node.text
    if password is None:
        return None
    if thetype == 'base64':
        return base64.decodestring(password)
    elif thetype == 'cleartext':
        return password
    else:
        raise ValueError('invalid password type: ' + thetype)

def _add_password_node(parent, password, tag = 'password'):
    node = etree.SubElement(parent, tag, type = 'base64')
    if password is not None:
        node.text = base64.encodestring(password).strip()
    return node

def get_account_from_etree(node):
    """
    Given a <account> node, this function returns a Exscript.Account instance.
    The following XML syntax is expected, whereby the children of <account>
    are all optional::

        <account name="myaccount">
          <password type="base64">Zm9v</password>
          <authorization-password type="cleartext">bar</authorization-password>
          <keyfile>/path/to/my/ssh/key</keyfile>
        </account>

    The <password> and <authorization-password> tags have an optional type
    attribute defaulting to 'cleartext'. Allowed values are 'cleartext'
    and 'base64'.

    @type  node: lxml.etree.ElementNode
    @param node: A <account> element.
    @rtype:  Exscript.Account
    @return: The resulting account.
    """
    name           = node.get('name', '').strip()
    password1_elem = node.find('password')
    password2_elem = node.find('authorization-password')
    keyfile        = node.findtext('keyfile')
    if keyfile is None:
        key = None
    else:
        key = PrivateKey.from_file(keyfile)
    account = Exscript.Account(name, key = key)
    account.set_password(_get_password_from_node(password1_elem))
    account.set_authorization_password(_get_password_from_node(password2_elem))
    return account

def add_account_to_etree(root, tag, account):
    """
    Given an account object, this function creates the syntax shown in
    get_host_from_etree() and adds it to the given node.
    Returns the new host element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  account: Exscript.Account
    @param account: The account that is added.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    elem = etree.SubElement(root, tag, name = account.get_name())
    _add_password_node(elem, account.get_password())
    _add_password_node(elem,
                       account.get_authorization_password(),
                       tag = 'authorization-password')
    key = account.get_key()
    if key is not None:
        etree.SubElement(elem, 'keyfile').text = key.get_filename()
    return elem

def get_accounts_from_etree(node):
    """
    Given an lxml.etree node, this function looks for <account> tags and
    returns a list of Exscript.Account instances. The following XML syntax
    is expected::

        <root>
           <account name="one"/>
           <account name="two">
             ...
           </account>
           ...
        </root>

    The individual accounts are parsed using L{get_account_from_etree()}.

    @type  node: lxml.etree.ElementNode
    @param node: A node containing <account> elements.
    @rtype:  list(Exscript.Account)
    @return: A list of accounts.
    """
    accounts = []
    for account_elem in node.iterfind('account'):
        account = get_account_from_etree(account_elem)
        accounts.append(account)
    return accounts

def add_accounts_to_etree(root, accounts):
    """
    Given a list of accounts, this function creates the syntax shown in
    get_accounts_from_etree() and adds it to the given node.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new elements are added.
    @type  accounts: list(Exscript.Account)
    @param accounts: A list of accounts.
    """
    for account in accounts:
        add_account_to_etree(root, 'account', account)

########NEW FILE########
__FILENAME__ = tkCommonDialog
#
# Instant Python
# tkCommonDialog.py,v 1.2 1997/08/14 14:17:26 guido Exp
#
# base class for tk common dialogues
#
# this module provides a base class for accessing the common
# dialogues available in Tk 4.2 and newer.  use tkFileDialog,
# tkColorChooser, and tkMessageBox to access the individual
# dialogs.
#
# written by Fredrik Lundh, May 1997
#
from Tkinter import *
class Dialog:
    command  = None
    def __init__(self, master=None, **options):
        # FIXME: should this be placed on the module level instead?
        if TkVersion < 4.2:
            raise TclError, "this module requires Tk 4.2 or newer"
        self.master  = master
        self.options = options
    def _fixoptions(self):
        pass # hook
    def _fixresult(self, widget, result):
        return result # hook
    def show(self, **options):
        # update instance options
        for k, v in options.items():
            self.options[k] = v
        self._fixoptions()
        # we need a dummy widget to properly process the options
        # (at least as long as we use Tkinter 1.63)
        w = Frame(self.master)
        try:
            s = apply(w.tk.call, (self.command,) + w._options(self.options))
            s = self._fixresult(w, s)
        finally:
            try:
                # get rid of the widget
                w.destroy()
            except:
                pass
        return s

########NEW FILE########
__FILENAME__ = tkMessageBox
#
# Instant Python
# tkMessageBox.py,v 1.1 1997/07/19 20:02:36 guido Exp
#
# tk common message boxes
#
# this module provides an interface to the native message boxes
# available in Tk 4.2 and newer.
#
# written by Fredrik Lundh, May 1997
#
#
# options (all have default values):
#
# - default: which button to make default (one of the reply codes)
#
# - icon: which icon to display (see below)
#
# - message: the message to display
#
# - parent: which window to place the dialog on top of
#
# - title: dialog title
#
# - type: dialog type; that is, which buttons to display (see below)
#
from TkExscript.compat.tkCommonDialog import Dialog
#
# constants
# icons
ERROR = "error"
INFO = "info"
QUESTION = "question"
WARNING = "warning"
# types
ABORTRETRYIGNORE = "abortretryignore"
OK = "ok"
OKCANCEL = "okcancel"
RETRYCANCEL = "retrycancel"
YESNO = "yesno"
YESNOCANCEL = "yesnocancel"
# replies
ABORT = "abort"
RETRY = "retry"
IGNORE = "ignore"
OK = "ok"
CANCEL = "cancel"
YES = "yes"
NO = "no"
#
# message dialog class
class Message(Dialog):
    "A message box"
    command  = "tk_messageBox"
#
# convenience stuff
def _show(title=None, message=None, icon=None, type=None, **options):
    if icon:    options["icon"] = icon
    if type:    options["type"] = type
    if title:   options["title"] = title
    if message: options["message"] = message
    return apply(Message, (), options).show()
def showinfo(title=None, message=None, **options):
    "Show an info message"
    return apply(_show, (title, message, INFO, OK), options)
def showwarning(title=None, message=None, **options):
    "Show a warning message"
    return apply(_show, (title, message, WARNING, OK), options)
def showerror(title=None, message=None, **options):
    "Show an error message"
    return apply(_show, (title, message, ERROR, OK), options)
def askquestion(title=None, message=None, **options):
    "Ask a question"
    return apply(_show, (title, message, QUESTION, YESNO), options)
def askokcancel(title=None, message=None, **options):
    "Ask if operation should proceed; return true if the answer is ok"
    s = apply(_show, (title, message, QUESTION, OKCANCEL), options)
    return s == OK
def askyesno(title=None, message=None, **options):
    "Ask a question; return true if the answer is yes"
    s = apply(_show, (title, message, QUESTION, YESNO), options)
    return s == YES
def askretrycancel(title=None, message=None, **options):
    "Ask if operation should be retried; return true if the answer is yes"
    s = apply(_show, (title, message, WARNING, RETRYCANCEL), options)
    return s == RETRY
# --------------------------------------------------------------------
# test stuff
if __name__ == "__main__":
    print "info", showinfo("Spam", "Egg Information")
    print "warning", showwarning("Spam", "Egg Warning")
    print "error", showerror("Spam", "Egg Alert")
    print "question", askquestion("Spam", "Question?")
    print "proceed", askokcancel("Spam", "Proceed?")
    print "yes/no", askyesno("Spam", "Got it?")
    print "try again", askretrycancel("Spam", "Try again?")

########NEW FILE########
__FILENAME__ = LoginWidget
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A widget for entering username and password.
"""
from Tkinter  import *
from Exscript import Account

class LoginWidget(Frame):
    """
    A widget that asks for username and password.
    """

    def __init__(self, parent, account = None, show_authorization = False):
        """
        A simple login widget with a username and password field.

        @type  parent: tkinter.Frame
        @param parent: The parent widget.
        @type  account: Exscript.Account
        @param account: An optional account that is edited.
        @type  show_authorization: bool
        @param show_authorization: Whether to show the "Authorization" entry.
        """
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, pad = 6)
        self.columnconfigure(1, weight = 1)
        row = -1

        # Username field.
        self.label_user = Label(self, text = 'User:')
        self.entry_user = Entry(self)
        row += 1
        self.rowconfigure(row, pad = row > 0 and 6 or 0)
        self.label_user.grid(row = row, column = 0, sticky = W)
        self.entry_user.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
        self.entry_user.bind('<Key>', self._on_field_changed)

        # Password field.
        self.label_password1 = Label(self, text = 'Password:')
        self.entry_password1 = Entry(self, show = '*')
        row += 1
        self.rowconfigure(row, pad = row > 0 and 6 or 0)
        self.label_password1.grid(row = row, column = 0, sticky = W)
        self.entry_password1.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
        self.entry_password1.bind('<Key>', self._on_field_changed)

        # Authorization password field.
        self.label_password2 = Label(self, text = 'Authorization:')
        self.entry_password2 = Entry(self, show = '*')
        if show_authorization:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_password2.grid(row = row, column = 0, sticky = W)
            self.entry_password2.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_password2.bind('<Key>', self._on_field_changed)

        self.locked  = False
        self.account = None
        self.attach(account and account or Account())

    def _on_field_changed(self, event):
        if self.locked:
            return
        # No idea if there is another way to receive a key event AFTER it
        # has completed, so this hack works for now.
        self.after(1, self._update_account)

    def _on_subject_changed(self, event):
        if self.locked:
            return
        self._on_field_changed(event)

    def _update_account(self):
        if self.locked:
            return
        self.locked = True
        self.account.set_name(self.entry_user.get())
        self.account.set_password(self.entry_password1.get())
        self.account.set_authorization_password(self.entry_password2.get())
        self.locked = False

    def _account_changed(self, account):
        if self.locked:
            return
        self.locked = True
        self.entry_user.delete(0, END)
        self.entry_user.insert(END, account.get_name())

        self.entry_password1.delete(0, END)
        self.entry_password1.insert(END, account.get_password())

        self.entry_password2.delete(0, END)
        self.entry_password2.insert(END, account.get_authorization_password())
        self.locked = False

    def attach(self, account):
        """
        Attaches the given account to the widget, such that any changes
        that are made in the widget are automatically reflected in the
        given account.

        @type  account: Exscript.Account
        @param account: The account object to attach.
        """
        if self.account:
            self.account.changed_event.disconnect(self._account_changed)
        self.account = account
        self.account.changed_event.connect(self._account_changed)
        self._account_changed(account)

    def get_account(self):
        """
        Returns the attached account object.

        @rtype:  Exscript.Account
        @return: The account that is currently edited.
        """
        return self.account

########NEW FILE########
__FILENAME__ = LoginWindow
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A window containing a LoginWidget.
"""
from Tkinter                import *
from TkExscript.LoginWidget import LoginWidget

class _ButtonBar(Frame):
    def __init__(self, parent, on_cancel = None, on_start = None, **kwargs):
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, pad = 12)
        self.columnconfigure(2, pad = 12)

        send = Button(self, text = 'Start', command = on_start)
        send.grid(row = 0, column = 2, sticky = E)
        send = Button(self, text = 'Cancel', command = on_cancel)
        send.grid(row = 0, column = 1, sticky = E)

class LoginWindow(Frame):
    """
    A simple TkFrame that shows a LoginWidget.
    This class supports all of the same methods that LoginWidget supports;
    any calls are proxied directly to the underlying widget.
    """

    def __init__(self,
                 account            = None,
                 show_authorization = False,
                 on_start           = None):
        """
        Create a new login window. All arguments are passed to the
        underlying LoginWidget.

        @type  account: Exscript.Account
        @param account: An optional account that is edited.
        @type  show_authorization: bool
        @param show_authorization: Whether to show the "Authorization" entry.
        @type  on_start: function
        @param on_start: Called when the start button is clicked.
        """
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)

        self.widget = LoginWidget(self,
                                  account,
                                  show_authorization = show_authorization)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)

        self.buttons = _ButtonBar(self,
                                  on_cancel = self.quit,
                                  on_start  = self._on_start)
        self.buttons.pack(expand = False, fill = X, padx = 6, pady = 3)

        self._on_start_cb = on_start

    def __getattr__(self, name):
        return getattr(self.widget, name)

    def _on_start(self):
        self._on_start_cb(self)

########NEW FILE########
__FILENAME__ = MailWidget
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A simple email editor.
"""
from Tkinter            import *
from Exscript.util.mail import Mail, send
try:
    import tkMessageBox
except ImportError:
    from TkExscript.compat import tkMessageBox

class _ButtonBar(Frame):
    def __init__(self, parent, on_cancel = None, on_send = None, **kwargs):
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, pad = 12)
        self.columnconfigure(2, pad = 12)

        send = Button(self, text = 'Send', command = on_send)
        send.grid(row = 0, column = 2, sticky = E)
        send = Button(self, text = 'Cancel', command = on_cancel)
        send.grid(row = 0, column = 1, sticky = E)

class MailWidget(Frame):
    """
    A widget for editing and sending a mail.
    """

    def __init__(self,
                 parent,
                 mail               = None,
                 server             = 'localhost',
                 show_to            = True,
                 show_cc            = True,
                 show_bcc           = False,
                 on_subject_changed = None):
        """
        A simple editor for sending emails. If the given mail is None, a
        new mail is created, else it is passed to attach().

        @type  parent: tkinter.Frame
        @param parent: The parent widget.
        @type  mail: Exscript.util.mail.Mail
        @param mail: The email object to attach.
        @type  server: string
        @param server: The address of the mailserver.
        @type  show_to: bool
        @param show_to: Whether to show the "To:" entry box.
        @type  show_cc: bool
        @param show_cc: Whether to show the "Cc:" entry box.
        @type  show_bcc: bool
        @param show_bcc: Whether to show the "Bcc:" entry box.
        @type  on_subject_changed: function
        @param on_subject_changed: Called whenever the subject changes.
        """
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, pad = 6)
        self.columnconfigure(1, weight = 1)

        row = -1
        self.label_to = Label(self, text = 'To:')
        self.entry_to = Entry(self)
        if show_to:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_to.grid(row = row, column = 0, sticky = W)
            self.entry_to.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_to.bind('<Key>', self._on_field_changed)

        self.label_cc = Label(self, text = 'Cc:')
        self.entry_cc = Entry(self)
        if show_cc:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_cc.grid(row = row, column = 0, sticky = W)
            self.entry_cc.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_cc.bind('<Key>', self._on_field_changed)

        self.label_bcc = Label(self, text = 'Bcc:')
        self.entry_bcc = Entry(self)
        if show_bcc:
            row += 1
            self.rowconfigure(row, pad = row > 0 and 6 or 0)
            self.label_bcc.grid(row = row, column = 0, sticky = W)
            self.entry_bcc.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
            self.entry_bcc.bind('<Key>', self._on_field_changed)

        row += 1
        self.rowconfigure(row, pad = row > 0 and 6 or 0)
        self.label_subject = Label(self, text = 'Subject:')
        self.label_subject.grid(row = row, column = 0, sticky = W)
        self.entry_subject = Entry(self)
        self.entry_subject.grid(row = row, column = 1, columnspan = 2, sticky = W+E)
        self.entry_subject.bind('<Key>', self._on_subject_changed)

        row += 1
        self.rowconfigure(row, pad = 6, weight = 1)
        scrollbar = Scrollbar(self, takefocus = 0)
        scrollbar.grid(row = row, column = 2, sticky = N+S)
        self.text_widget = Text(self)
        self.text_widget.grid(row        = row,
                              column     = 0,
                              columnspan = 2,
                              sticky     = N+S+E+W)
        self.text_widget.config(yscrollcommand = scrollbar.set)
        self.text_widget.bind('<Key>', self._on_field_changed)
        scrollbar.config(command = self.text_widget.yview)

        row += 1
        self.rowconfigure(row, pad = 6)
        self.buttons = _ButtonBar(self,
                                  on_cancel = parent.quit,
                                  on_send   = self._on_send)
        self.buttons.grid(row = row, column = 0, columnspan = 3, sticky = E)

        self.server                = server
        self.on_subject_changed_cb = on_subject_changed
        self.locked                = False
        self.mail                  = None
        self.attach(mail and mail or Mail())

    def _on_field_changed(self, event):
        if self.locked:
            return
        # No idea if there is another way to receive a key event AFTER it
        # has completed, so this hack works for now.
        self.after(1, self._update_mail)

    def _on_subject_changed(self, event):
        if self.locked:
            return
        self._on_field_changed(event)
        # No idea if there is another way to receive a key event AFTER it
        # has completed, so this hack works for now.
        if self.on_subject_changed_cb:
            self.after(1, self.on_subject_changed_cb)

    def _update_mail(self):
        if self.locked:
            return
        self.locked = True
        self.mail.set_to(self.entry_to.get())
        self.mail.set_cc(self.entry_cc.get())
        self.mail.set_bcc(self.entry_bcc.get())
        self.mail.set_subject(self.entry_subject.get())
        self.mail.set_body(self.text_widget.get('0.0', END))
        self.locked = False

    def _update_ui(self):
        if self.locked:
            return
        self.locked = True
        self.entry_to.delete(0, END)
        self.entry_to.insert(END, ', '.join(self.mail.get_to()))

        self.entry_cc.delete(0, END)
        self.entry_cc.insert(END, ', '.join(self.mail.get_cc()))

        self.entry_bcc.delete(0, END)
        self.entry_bcc.insert(END, ', '.join(self.mail.get_bcc()))

        self.entry_subject.delete(0, END)
        self.entry_subject.insert(END, self.mail.get_subject())

        self.text_widget.delete('0.0', END)
        self.text_widget.insert(END, self.mail.get_body())
        self.locked = False

    def attach(self, mail):
        """
        Attaches the given email to the editor, such that any changes
        that are made in the editor are automatically reflected in the
        given email.

        @type  mail: Exscript.util.mail.Mail
        @param mail: The email object to attach.
        """
        if self.mail:
            self.mail.changed_event.disconnect(self._update_ui)
        self.mail = mail
        self.mail.changed_event.connect(self._update_ui)
        self._update_ui()

    def get_mail(self):
        """
        Returns the attached email object.

        @rtype:  Exscript.util.mail.Mail
        @return: The mail that is currently edited.
        """
        return self.mail

    def _on_send(self):
        try:
            send(self.mail, server = self.server)
        except Exception, e:
            title    = 'Send failed'
            message  = 'The email could not be sent using %s.' % self.server
            message += ' This was the error:\n'
            message += str(e)
            if tkMessageBox.askretrycancel(title, message):
                self.after(1, self._on_send)
            return
        self.quit()

########NEW FILE########
__FILENAME__ = MailWindow
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A window containing a MailWidget.
"""
from Tkinter               import *
from TkExscript.MailWidget import MailWidget

class MailWindow(Frame):
    """
    A simple TkFrame that shows a MailWidget.
    This class supports all of the same methods that MailWidget supports;
    any calls are proxied directly to the underlying widget.
    """

    def __init__(self,
                 mail     = None,
                 server   = 'localhost',
                 show_to  = True,
                 show_cc  = True,
                 show_bcc = False):
        """
        Create a new editor window. All arguments are passed to the
        underlying MailWidget.

        @type  mail: Exscript.util.mail.Mail
        @param mail: An optional email object to attach.
        @type  server: string
        @param server: The address of the mailserver.
        @type  show_to: bool
        @param show_to: Whether to show the "To:" entry box.
        @type  show_cc: bool
        @param show_cc: Whether to show the "Cc:" entry box.
        @type  show_bcc: bool
        @param show_bcc: Whether to show the "Bcc:" entry box.
        """
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)

        self.widget = MailWidget(self,
                                 mail,
                                 server             = server,
                                 show_to            = show_to,
                                 show_cc            = show_cc,
                                 show_bcc           = show_bcc,
                                 on_subject_changed = self._update_subject)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)
        self._on_subject_changed(None)

    def _update_subject(self):
        subject = self.widget.get_mail().get_subject()
        if subject:
            self.master.title(subject)
        else:
            self.master.title('Send a mail')

    def __getattr__(self, name):
        return getattr(self.widget, name)

########NEW FILE########
__FILENAME__ = Notebook
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A notebook widget.
"""
import Tkinter as tk

class Notebook(tk.Frame):
    """
    A notebook widget for Tkinter applications.
    """
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.active_page  = None
        self.new_tab_side = tk.LEFT
        self.tabgroup     = tk.IntVar(0)
        self.tabs         = []
        self.tab_buttons  = []
        self.tab_area     = tk.Frame(self)
        self.count        = 0
        self.tab_area.pack(fill = tk.BOTH, side = tk.TOP)

    def _display_page(self, pg):
        """
        Shows the selected page, hides former page
        """
        if self.active_page:
            self.active_page.forget()
        pg.pack(fill = tk.BOTH, expand = True)
        self.active_page = pg

    def append_page(self, title):
        """
        Adds a new page to the notebook and returns it.
        """
        self.count += 1
        pos    = len(self.tabs)
        page   = tk.Frame(self)
        button = tk.Radiobutton(self.tab_area,
                                text        = title,
                                indicatoron = False,
                                variable    = self.tabgroup,
                                value       = self.count,
                                relief      = tk.RIDGE,
                                offrelief   = tk.RIDGE,
                                borderwidth = 1,
                                command     = lambda: self._display_page(page))
        button.pack(fill = tk.BOTH,
                    side = self.new_tab_side,
                    padx = 0,
                    pady = 0)
        self.tabs.append(page)
        self.tab_buttons.append(button)
        if self.active_page is None:
            self.select(pos)
        return page

    def remove_page(self, page):
        """
        Removes the given page from the notebook.
        """
        pageno = self.tabs.index(page)
        button = self.tab_buttons[pageno]
        page.forget()
        button.forget()
        self.tabs.remove(page)
        self.tab_buttons.remove(button)
        if self.tabs:
            newpage = min(pageno, len(self.tabs) - 1)
            self.select(min(pageno, len(self.tabs) - 1))

    def select_page(self, page):
        """
        Selects the given page.
        """
        self.select(self.tabs.index(page))

    def select(self, page_number):
        """
        Selects the page with the given number.
        """
        self.tab_buttons[page_number].select()
        self._display_page(self.tabs[page_number])

########NEW FILE########
__FILENAME__ = ProgressBar
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A progress bar widget.
"""
from Tkinter import *

class ProgressBar(Frame):
    '''
    A simple progress bar widget.
    '''

    def __init__(self,
                 parent,
                 fillcolor = 'orchid1',
                 text      = '',
                 height    = 20,
                 value     = 0.0):
        Frame.__init__(self, parent, bg = 'white', height = height)
        self.pack(expand = True, fill = BOTH)
        self.canvas = Canvas(self,
                             bg     = self['bg'],
                             height = self['height'],
                             highlightthickness = 0,
                             relief = 'flat',
                             bd     = 0)
        self.canvas.pack(fill = BOTH, expand = True)
        self.rect = self.canvas.create_rectangle(0, 0, 0, 0, fill = fillcolor, outline = '')
        self.text = self.canvas.create_text(0, 0, text='')
        self.set(value, text)

    def set(self, value = 0.0, text = None):
        value = max(value, 0.0)
        value = min(value, 1.0)

        # Update the progress bar.
        height = self.canvas.winfo_height()
        width  = self.canvas.winfo_width()
        self.canvas.coords(self.rect, 0, 0, width * value, height)

        # Update the text.
        if text == None:
            text = str(int(round(100 * value))) + ' %'
        self.canvas.coords(self.text, width / 2, height / 2)
        self.canvas.itemconfigure(self.text, text = text)

########NEW FILE########
__FILENAME__ = QueueWidget
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A simple email editor.
"""
import Queue
from Tkinter                import *
from TkExscript.Notebook    import Notebook
from TkExscript.ProgressBar import ProgressBar

class _ConnectionWatcherWidget(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        scrollbar = Scrollbar(parent, takefocus = 0)
        scrollbar.pack(fill = BOTH, side = RIGHT)
        self.text_widget = Text(parent)
        self.text_widget.pack(fill='both', expand=True)
        self.text_widget.config(yscrollcommand = scrollbar.set)
        scrollbar.config(command = self.text_widget.yview)

        self.data_queue = Queue.Queue()
        self._update()

    def _update(self):
        try:
            while True:
                func, args = self.data_queue.get_nowait()
                func(*args)
                self.update_idletasks()
        except Queue.Empty:
            pass
        self.text_widget.see(END)
        self.after(100, self._update)

class _ConnectionWatcher(object):
    def __init__(self, conn):
        self.buffer = ''
        self.widget = None
        self.conn   = conn
        self.conn.data_received_event.connect(self._on_data_received)

    def _show_data(self, data):
        data = data.replace('\r\n', '\n')
        func = self.widget.text_widget.insert
        self.widget.data_queue.put((func, (END, data)))

    def create_widget(self, parent):
        self.widget = _ConnectionWatcherWidget(parent)
        self._show_data(self.buffer)
        self.buffer = ''

    def _on_data_received(self, data):
        if self.widget:
            self._show_data(data)
        else:
            self.buffer += data

class QueueWidget(Frame):
    """
    A widget for watching Exscript.Queue.
    """

    def __init__(self, parent, queue):
        """
        Create the widget.

        @type  parent: tkinter.Frame
        @param parent: The parent widget.
        @type  queue: Exscript.Queue
        @param queue: The watched queue.
        """
        Frame.__init__(self, parent)
        self.pack(expand = True, fill = BOTH)
        self.columnconfigure(0, pad = 6)
        self.columnconfigure(1, weight = 1)
        row = -1

        # Progress bar.
        row += 1
        self.rowconfigure(row, weight = 0)
        self.label_progress = Label(self, text = 'Progress:')
        self.progress_bar   = ProgressBar(self)
        self.label_progress.grid(row = row, column = 0, sticky = W)
        self.progress_bar.grid(row = row, column = 1, sticky = W+E)

        # Padding.
        row += 1
        self.rowconfigure(row, pad = 6)
        padding = Frame(self)
        padding.grid(row = row, column = 0, sticky = W)

        row += 1
        self.rowconfigure(row, weight = 1)
        self.notebook = Notebook(self)
        self.notebook.grid(row        = row,
                           column     = 0,
                           columnspan = 2,
                           sticky     = N+S+E+W)

        self.data_queue = Queue.Queue()
        self.pages      = {}
        self.queue      = queue
        self.queue.workqueue.job_started_event.connect(self._on_job_started)
        self.queue.workqueue.job_error_event.connect(self._on_job_error)
        self.queue.workqueue.job_succeeded_event.connect(self._on_job_succeeded)
        self.queue.workqueue.job_aborted_event.connect(self._on_job_aborted)
        self._update()

    def _update_progress(self):
        self.progress_bar.set(self.queue.get_progress() / 100)

    def _create_page(self, action, watcher):
        page = self.notebook.append_page(action.get_name())
        self.pages[action] = page
        watcher.create_widget(page)

    def _remove_page(self, action):
        page = self.pages[action]
        del self.pages[action]
        self.notebook.remove_page(page)

    def _update(self):
        try:
            while True:
                func, args = self.data_queue.get_nowait()
                func(*args)
                self.update_idletasks()
        except Queue.Empty:
            pass
        self._update_progress()
        self.after(100, self._update)

    def _on_job_started(self, job):
        watcher = _ConnectionWatcher(conn)
        self.data_queue.put((self._create_page, (job, watcher)))

    def _on_job_error(self, job, e):
        self.data_queue.put((self._remove_page, (job,)))

    def _on_job_succeeded(self, job):
        self.data_queue.put((self._remove_page, (job,)))

    def _on_job_aborted(self, job):
        pass

########NEW FILE########
__FILENAME__ = QueueWindow
# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A window containing a MailWatcher.
"""
from Tkinter                import *
from TkExscript.QueueWidget import QueueWidget

class QueueWindow(Frame):
    def __init__(self, queue, **kwargs):
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)
        self.widget = QueueWidget(self, queue)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)

        if kwargs.get('autoclose', False):
            queue.queue_empty_event.connect(self._on_queue_empty)

    def _on_queue_empty(self):
        self.after(1, self.quit)

########NEW FILE########
__FILENAME__ = AccountManagerTest
import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.Account import Account
from Exscript.AccountPool import AccountPool
from Exscript.AccountManager import AccountManager

class AccountManagerTest(unittest.TestCase):
    CORRELATE = AccountManager

    def setUp(self):
        self.am      = AccountManager()
        self.data    = {}
        self.account = Account('user', 'test')

    def testConstructor(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())

    def testReset(self):
        self.testAddAccount()
        self.am.reset()
        self.assertEqual(self.am.default_pool.n_accounts(), 0)

    def testAddAccount(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())
        account = Account('user', 'test')
        self.am.add_account(account)
        self.assertEqual(1, self.am.default_pool.n_accounts())

    def testAddPool(self):
        self.assertEqual(0, self.am.default_pool.n_accounts())
        account = Account('user', 'test')
        self.am.add_account(account)
        self.assertEqual(1, self.am.default_pool.n_accounts())

        def match_cb(host):
            self.data['match-called'] = True
            self.data['host'] = host
            return True

        # Replace the default pool.
        pool1 = AccountPool()
        self.am.add_pool(pool1)
        self.assertEqual(self.am.default_pool, pool1)

        # Add another pool, making sure that it does not replace
        # the default pool.
        pool2 = AccountPool()
        pool2.add_account(self.account)
        self.am.add_pool(pool2, match_cb)
        self.assertEqual(self.am.default_pool, pool1)

    def testGetAccountFromHash(self):
        pool1 = AccountPool()
        acc1  = Account('user1')
        pool1.add_account(acc1)
        self.am.add_pool(pool1)

        acc2 = Account('user2')
        self.am.add_account(acc2)
        self.assertEqual(self.am.get_account_from_hash(acc1.__hash__()), acc1)
        self.assertEqual(self.am.get_account_from_hash(acc2.__hash__()), acc2)

    def testAcquireAccount(self):
        account1 = Account('user1', 'test')
        self.assertRaises(ValueError, self.am.acquire_account)
        self.am.add_account(account1)
        self.assertEqual(self.am.acquire_account(), account1)
        account1.release()

        account2 = Account('user2', 'test')
        self.am.add_account(account2)
        self.assertEqual(self.am.acquire_account(account2), account2)
        account2.release()
        account = self.am.acquire_account()
        self.assertNotEqual(account, None)
        account.release()

        account3 = Account('user3', 'test')
        pool = AccountPool()
        pool.add_account(account3)
        self.am.add_pool(pool)
        self.assertEqual(self.am.acquire_account(account2), account2)
        account2.release()
        self.assertEqual(self.am.acquire_account(account3), account3)
        account3.release()
        account = self.am.acquire_account()
        self.assertNotEqual(account, None)
        account.release()

    def testAcquireAccountFor(self):
        self.testAddPool()

        def start_cb(data, conn):
            data['start-called'] = True

        # Make sure that pool2 is chosen (because the match function
        # returns True).
        account = self.am.acquire_account_for('myhost')
        account.release()
        self.assertEqual(self.data, {'match-called': True, 'host': 'myhost'})
        self.assertEqual(self.account, account)

    def testReleaseAccounts(self):
        account1 = Account('foo')
        pool = AccountPool()
        pool.add_account(account1)
        pool.acquire_account(account1, 'one')
        self.am.add_pool(pool, lambda x: None)

        account2 = Account('bar')
        self.am.add_account(account2)
        self.am.acquire_account(account2, 'two')

        self.assert_(account1 not in pool.unlocked_accounts)
        self.assert_(account2 not in self.am.default_pool.unlocked_accounts)

        self.am.release_accounts('two')
        self.assert_(account1 not in pool.unlocked_accounts)
        self.assert_(account2 in self.am.default_pool.unlocked_accounts)

        self.am.release_accounts('one')
        self.assert_(account1 in pool.unlocked_accounts)
        self.assert_(account2 in self.am.default_pool.unlocked_accounts)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountManagerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = AccountPoolTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript             import Account
from Exscript.AccountPool import AccountPool
from Exscript.util.file   import get_accounts_from_file

class AccountPoolTest(unittest.TestCase):
    CORRELATE = AccountPool

    def setUp(self):
        self.user1     = 'testuser1'
        self.password1 = 'test1'
        self.account1  = Account(self.user1, self.password1)
        self.user2     = 'testuser2'
        self.password2 = 'test2'
        self.account2  = Account(self.user2, self.password2)
        self.accm      = AccountPool()

    def testConstructor(self):
        accm = AccountPool()
        self.assertEqual(accm.n_accounts(), 0)

        accm = AccountPool([self.account1, self.account2])
        self.assertEqual(accm.n_accounts(), 2)

    def testAddAccount(self):
        self.assertEqual(self.accm.n_accounts(), 0)
        self.accm.add_account(self.account1)
        self.assertEqual(self.accm.n_accounts(), 1)

        self.accm.add_account(self.account2)
        self.assertEqual(self.accm.n_accounts(), 2)

    def testReset(self):
        self.testAddAccount()
        self.accm.reset()
        self.assertEqual(self.accm.n_accounts(), 0)

    def testHasAccount(self):
        self.assertEqual(self.accm.has_account(self.account1), False)
        self.accm.add_account(self.account1)
        self.assertEqual(self.accm.has_account(self.account1), True)

    def testGetAccountFromHash(self):
        account = Account('user', 'test')
        thehash = account.__hash__()
        self.accm.add_account(account)
        self.assertEqual(self.accm.get_account_from_hash(thehash), account)

    def testGetAccountFromName(self):
        self.testAddAccount()
        self.assertEqual(self.account2,
                         self.accm.get_account_from_name(self.user2))

    def testNAccounts(self):
        self.testAddAccount()

    def testAcquireAccount(self):
        self.testAddAccount()
        self.accm.acquire_account(self.account1)
        self.account1.release()
        self.accm.acquire_account(self.account1)
        self.account1.release()

        # Add three more accounts.
        filename = os.path.join(os.path.dirname(__file__), 'account_pool.cfg')
        self.accm.add_account(get_accounts_from_file(filename))
        self.assert_(self.accm.n_accounts() == 5)

        for i in range(0, 2000):
            # Each time an account is acquired a different one should be 
            # returned.
            acquired = {}
            for n in range(0, 5):
                account = self.accm.acquire_account()
                self.assert_(account is not None)
                self.assert_(not acquired.has_key(account.get_name()))
                acquired[account.get_name()] = account

            # Release one account.
            acquired['abc'].release()

            # Acquire one account.
            account = self.accm.acquire_account()
            self.assert_(account.get_name() == 'abc')

            # Release all accounts.
            for account in acquired.itervalues():
                account.release()

    def testReleaseAccounts(self):
        account1 = Account('foo')
        account2 = Account('bar')
        pool = AccountPool()
        pool.add_account(account1)
        pool.add_account(account2)
        pool.acquire_account(account1, 'one')
        pool.acquire_account(account2, 'two')

        self.assert_(account1 not in pool.unlocked_accounts)
        self.assert_(account2 not in pool.unlocked_accounts)
        pool.release_accounts('one')
        self.assert_(account1 in pool.unlocked_accounts)
        self.assert_(account2 not in pool.unlocked_accounts)
        pool.release_accounts('one')
        self.assert_(account1 in pool.unlocked_accounts)
        self.assert_(account2 not in pool.unlocked_accounts)
        pool.release_accounts('two')
        self.assert_(account1 in pool.unlocked_accounts)
        self.assert_(account2 in pool.unlocked_accounts)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountPoolTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = AccountTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript import Account, PrivateKey

class AccountTest(unittest.TestCase):
    CORRELATE = Account

    def setUp(self):
        self.user      = 'testuser'
        self.password1 = 'test1'
        self.password2 = 'test2'
        self.key       = PrivateKey()
        self.account   = Account(self.user,
                                 self.password1,
                                 self.password2,
                                 self.key)

    def testConstructor(self):
        key     = PrivateKey()
        account = Account(self.user, self.password1, key = key)
        self.assertEqual(account.get_key(), key)
        self.assertEqual(account.get_password(),
                         account.get_authorization_password())

        account = Account(self.user, self.password1, self.password2)
        self.failIfEqual(account.get_password(),
                         account.get_authorization_password())

    def testContext(self):
        with self.account as account:
            account.release()
            account.acquire()

        self.account.acquire()
        with self.account.context() as context:
            context.release()
            context.acquire()
            with context.context() as subcontext:
                subcontext.release()
                subcontext.acquire()
                with subcontext.context() as subsubcontext:
                    subsubcontext.release()
                    subsubcontext.acquire()

        with self.account:
            pass

    def testAcquire(self):
        self.account.acquire()
        self.account.release()
        self.account.acquire()
        self.account.release()

    def testRelease(self):
        self.assertRaises(Exception, self.account.release)

    def testSetName(self):
        self.assertEqual(self.user, self.account.get_name())
        self.account.set_name('foo')
        self.assertEqual('foo', self.account.get_name())

    def testGetName(self):
        self.assertEqual(self.user, self.account.get_name())

    def testSetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())
        self.account.set_password('foo')
        self.assertEqual('foo', self.account.get_password())

    def testGetPassword(self):
        self.assertEqual(self.password1, self.account.get_password())

    def testSetAuthorizationPassword(self):
        self.assertEqual(self.password2,
                         self.account.get_authorization_password())
        self.account.set_authorization_password('foo')
        self.assertEqual('foo', self.account.get_authorization_password())

    def testGetAuthorizationPassword(self):
        self.assertEqual(self.password2,
                         self.account.get_authorization_password())

    def testGetKey(self):
        self.assertEqual(self.key, self.account.get_key())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(AccountTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = CommandSetTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.emulators import CommandSet

class CommandSetTest(unittest.TestCase):
    CORRELATE = CommandSet

    def testConstructor(self):
        CommandSet()
        CommandSet(strict = True)
        CommandSet(strict = False)

    def testAdd(self):
        cs = CommandSet()
        self.assertRaises(Exception, cs.eval, 'foo')

        cs = CommandSet(strict = False)
        self.assertEqual(cs.eval('foo'), None)

        cs = CommandSet(strict = True)
        self.assertRaises(Exception, cs.eval, 'foo')
        cs.add('foo', 'bar')
        self.assertEqual(cs.eval('foo'), 'bar')

        def sayhello(cmd):
            return 'hello'
        cs.add('hi', sayhello)
        self.assertEqual(cs.eval('hi'), 'hello')

    def testAddFromFile(self):
        pass # FIXME

    def testEval(self):
        pass # See testAdd()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(CommandSetTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = IOSEmulatorTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from VirtualDeviceTest              import VirtualDeviceTest
from Exscript.emulators             import IOSEmulator
from Exscript.emulators.IOSEmulator import iosbanner

class IOSEmulatorTest(VirtualDeviceTest):
    CORRELATE    = IOSEmulator
    cls          = IOSEmulator
    banner       = iosbanner % ('myhost', 'myhost', 'myhost')
    prompt       = 'myhost#'
    userprompt   = 'Username: '
    passwdprompt = 'Password: '

    def testAddCommand(self):
        VirtualDeviceTest.testAddCommand(self)

        cs = self.cls('myhost',
                      strict     = True,
                      echo       = False,
                      login_type = self.cls.LOGIN_TYPE_NONE)

        response = cs.do('show version')
        self.assert_(response.startswith('Cisco Internetwork Operating'), response)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IOSEmulatorTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = run_suite
../run_suite.py
########NEW FILE########
__FILENAME__ = VirtualDeviceTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.emulators import VirtualDevice

class VirtualDeviceTest(unittest.TestCase):
    CORRELATE    = VirtualDevice
    cls          = VirtualDevice
    banner       = 'Welcome to myhost!\n'
    prompt       = 'myhost> '
    userprompt   = 'User: '
    passwdprompt = 'Password: '

    def testConstructor(self):
        self.cls('myhost')

    def testGetPrompt(self):
        v = self.cls('myhost')
        self.assertEqual(v.get_prompt(), self.prompt)
        v.set_prompt('foo# ')
        self.assertEqual(v.get_prompt(), 'foo# ')

    def testSetPrompt(self):
        self.testGetPrompt()

    def testAddCommand(self):
        cs = self.cls('myhost',
                      strict     = True,
                      echo       = False,
                      login_type = self.cls.LOGIN_TYPE_NONE)
        self.assertRaises(Exception, cs.do, 'foo')
        cs.add_command('foo', 'bar')
        self.assertEqual(cs.do('foo'), 'bar\n' + self.prompt)

        def sayhello(cmd):
            return 'hello'
        cs.add_command('hi$', sayhello)
        self.assertEqual(cs.do('hi'), 'hello\n' + self.prompt)
        cs.add_command('hi2$', sayhello, prompt = False)
        self.assertEqual(cs.do('hi2'), 'hello')

    def testAddCommandsFromFile(self):
        pass # FIXME

    def testInit(self):
        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_PASSWORDONLY)
        self.assertEqual(cs.init(), self.banner + self.passwdprompt)

        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_USERONLY)
        self.assertEqual(cs.init(), self.banner + self.userprompt)

        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_BOTH)
        self.assertEqual(cs.init(), self.banner + self.userprompt)

        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_NONE)
        self.assertEqual(cs.init(), self.banner + self.prompt)

    def testDo(self):
        pass # See testAddCommand()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(VirtualDeviceTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = FileLoggerTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile import mkdtemp
from shutil import rmtree
from Exscript import Host
from Exscript.FileLogger import FileLogger
from LoggerTest import LoggerTest, FakeJob

class FakeError(Exception):
    pass

class FileLoggerTest(LoggerTest):
    CORRELATE = FileLogger

    def setUp(self):
        self.tempdir = mkdtemp()
        self.logdir  = os.path.join(self.tempdir, 'non-existent')
        self.logger  = FileLogger(self.logdir, clearmem = False)
        self.job     = FakeJob('fake')
        self.logfile = os.path.join(self.logdir, 'fake.log')
        self.errfile = self.logfile + '.error'

    def tearDown(self):
        LoggerTest.tearDown(self)
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assert_(os.path.isdir(self.tempdir))
        self.failIf(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errfile))

    def testAddLog(self):
        log = LoggerTest.testAddLog(self)
        self.assert_(os.path.isfile(self.logfile), 'No such file: ' + self.logfile)
        self.failIf(os.path.exists(self.errfile))
        return log

    def testLog(self):
        log = LoggerTest.testLog(self)
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        return log

    def testLogAborted(self):
        log = LoggerTest.testLogAborted(self)
        self.assert_(os.path.isfile(self.logfile))
        self.assert_(os.path.isfile(self.errfile))
        return log

    def testLogSucceeded(self):
        log = LoggerTest.testLogSucceeded(self)
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.isfile(self.errfile))
        return log

    def testAddLog2(self):
        # Like testAddLog(), but with attempt = 2.
        self.logfile = os.path.join(self.logdir, self.job.name + '_retry1.log')
        self.errfile = self.logfile + '.error'
        self.failIf(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        self.logger.add_log(id(self.job), self.job.name, 2)
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        content = open(self.logfile).read()
        self.assertEqual(content, '')

    def testLog2(self):
        # Like testLog(), but with attempt = 2.
        self.testAddLog2()
        self.logger.log(id(self.job), 'hello world')
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))
        content = open(self.logfile).read()
        self.assertEqual(content, 'hello world')

    def testLogSucceeded2(self):
        # With attempt = 2.
        self.testLog2()
        self.logger.log_succeeded(id(self.job))
        self.assert_(os.path.isfile(self.logfile))
        self.failIf(os.path.exists(self.errfile))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FileLoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = HostTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript          import Host, Account
from Exscript.util.url import Url
from util.urlTest      import urls

class HostTest(unittest.TestCase):
    CORRELATE = Host

    def setUp(self):
        self.host = Host('localhost')
        self.host.set_all(dict(testarg = 1))

    def testConstructor(self):
        host = Host('localhost')
        self.assertEqual(host.get_protocol(), 'telnet')
        host = Host('localhost', default_protocol = 'foo')
        self.assertEqual(host.get_protocol(), 'foo')

        for url, result in urls:
            host = Host(url)
            uri  = Url.from_string(url)
            self.assertEqual(host.get_name(),    uri.hostname)
            self.assertEqual(host.get_address(), uri.hostname)
            self.assertEqual(host.get_uri(), str(uri))

    def testSetUri(self):
        for url, result in urls:
            self.host.set_uri(url)
            uri = Url.from_string(url)
            self.assertEqual(self.host.get_name(),    uri.hostname)
            self.assertEqual(self.host.get_address(), uri.hostname)

    def testGetUri(self):
        for url, result in urls:
            host = Host(url)
            uri  = Url.from_string(url)
            self.assertEqual(host.get_uri(), str(uri))

    def testGetDict(self):
        host = Host('foo')
        host.set_address('foo2')
        self.assertEqual(host.get_dict(), {'hostname': 'foo',
                                           'address':  'foo2',
                                           'protocol': 'telnet',
                                           'port':     23})

    def testSetAddress(self):
        self.host.set_protocol('dummy')
        self.host.set_address('test.org')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'localhost')
        self.assertEqual(self.host.get_address(),  'test.org')

        self.host.set_address('001.002.003.004')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'localhost')
        self.assertEqual(self.host.get_address(),  '1.2.3.4')

    def testGetAddress(self):
        self.assertEqual(self.host.get_address(), 'localhost')
        # Additional tests are in testSetAddress().

    def testSetName(self):
        self.assertEqual(self.host.get_name(), 'localhost')
        self.host.set_protocol('dummy')
        self.host.set_name('test.org')
        self.assertEqual(self.host.get_protocol(), 'dummy')
        self.assertEqual(self.host.get_name(),     'test.org')
        self.assertEqual(self.host.get_address(),  'localhost')
        self.host.set_name('testhost')
        self.assertEqual(self.host.get_name(), 'testhost')

    def testGetName(self):
        pass # Tested in testSetName().

    def testSetProtocol(self):
        self.assertEqual(self.host.get_protocol(), 'telnet')
        self.host.set_protocol('dummy')
        self.assertEqual(self.host.get_protocol(), 'dummy')

    def testGetProtocol(self):
        pass # Tested in testSetProtocol().

    def testSetOption(self):
        self.assertRaises(TypeError, self.host.set_option, 'test', True)
        self.assertEqual(self.host.get_options(), {})
        self.assertEqual(self.host.get_option('verify_fingerprint'), None)
        self.assertEqual(self.host.get_option('verify_fingerprint', False), False)
        self.host.set_option('verify_fingerprint', True)
        self.assertEqual(self.host.get_option('verify_fingerprint'), True)
        self.assertEqual(self.host.get_options(), {'verify_fingerprint': True})

    def testGetOption(self):
        pass # Tested in testSetOption().

    def testGetOptions(self):
        pass # Tested in testSetOption().

    def testSetTcpPort(self):
        self.assertEqual(self.host.get_tcp_port(), 23)
        self.host.set_protocol('ssh')
        self.assertEqual(self.host.get_tcp_port(), 23)
        self.host.set_tcp_port(123)
        self.assertEqual(self.host.get_tcp_port(), 123)

    def testGetTcpPort(self):
        pass # Tested in testSetTcpPort().

    def testSetAccount(self):
        account = Account('test')
        self.assertEqual(self.host.get_account(), None)
        self.host.set_account(account)
        self.assertEqual(self.host.get_account(), account)

    def testGetAccount(self):
        pass # Tested in testSetAccount().

    def testSet(self):
        self.assertEqual(self.host.get('test'), None)
        self.host.set('test', 3)
        self.assertEqual(self.host.get('test'), 3)

    def testSetAll(self):
        self.testSet()
        self.host.set_all({'test1': 1, 'test2': 2})
        self.assertEqual(self.host.get('test'),  None)
        self.assertEqual(self.host.get('test1'), 1)
        self.assertEqual(self.host.get('test2'), 2)

    def testGetAll(self):
        self.assertEqual(self.host.get_all(), {'testarg': 1})
        self.testSetAll()
        self.assertEqual(self.host.get_all(), {'test1': 1, 'test2': 2})

        host = Host('localhost')
        self.assertEqual(host.get_all(), {})

    def testAppend(self):
        self.assertEqual(self.host.get('test'), None)
        self.host.append('test', 3)
        self.assertEqual(self.host.get('test'), [3])
        self.host.append('test', 4)
        self.assertEqual(self.host.get('test'), [3, 4])

    def testSetDefault(self):
        self.testSet()
        self.assertEqual(self.host.get('test'),  3)
        self.assertEqual(self.host.get('test2'), None)
        self.host.set_default('test',  5)
        self.host.set_default('test2', 1)
        self.assertEqual(self.host.get('test'),  3)
        self.assertEqual(self.host.get('test2'), 1)

    def testHasKey(self):
        self.testSet()
        self.assert_(self.host.has_key('test'))
        self.failIf(self.host.has_key('test2'))

    def testGet(self):
        self.testSet()
        self.assertEqual(self.host.get('test'),     3)
        self.assertEqual(self.host.get('test2'),    None)
        self.assertEqual(self.host.get('test',  1), 3)
        self.assertEqual(self.host.get('test2', 1), 1)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HostTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = LogfileTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile         import mkdtemp
from shutil           import rmtree
from LogTest          import LogTest
from Exscript.Logfile import Logfile

class LogfileTest(LogTest):
    CORRELATE = Logfile

    def setUp(self):
        self.tempdir   = mkdtemp()
        self.logfile   = os.path.join(self.tempdir, 'test.log')
        self.errorfile = self.logfile + '.error'
        self.log       = Logfile('testme', self.logfile)

    def tearDown(self):
        rmtree(self.tempdir)

    def testConstructor(self):
        self.assertEqual('testme', self.log.get_name())
        self.assertEqual('', str(self.log))
        self.failIf(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errorfile))

    def testStarted(self):
        LogTest.testStarted(self)
        self.assert_(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errorfile))

    def testAborted(self):
        LogTest.testAborted(self)
        self.assert_(os.path.exists(self.logfile))
        self.assert_(os.path.exists(self.errorfile))

    def testSucceeded(self):
        LogTest.testSucceeded(self)
        self.assert_(os.path.exists(self.logfile))
        self.failIf(os.path.exists(self.errorfile))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogfileTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = LoggerTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import gc
from itertools import islice
from tempfile import mkdtemp
from shutil import rmtree
from Exscript.Log import Log
from Exscript.Logger import Logger
from LogTest import FakeError
from util.reportTest import FakeJob

def count(iterable):
    return sum(1 for _ in iterable)

def nth(iterable, n, default = None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)

class LoggerTest(unittest.TestCase):
    CORRELATE = Logger

    def setUp(self):
        self.logger = Logger()
        self.job    = FakeJob('fake')

    def tearDown(self):
        # Needed to make sure that events are disconnected.
        self.logger = None

    def testConstructor(self):
        logger = Logger()

    def testGetSucceededActions(self):
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        job1 = FakeJob()
        job2 = FakeJob()
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.logger.add_log(id(job1), job1.name, 1)
        self.logger.add_log(id(job2), job2.name, 1)
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.logger.log_succeeded(id(job1))
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job2), sys.exc_info())
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        job = FakeJob()
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.logger.log_succeeded(id(job))
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(self.logger.get_aborted_actions(), 1)

    def testGetLogs(self):
        self.assertEqual(count(self.logger.get_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_logs(), 0), Log))

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_logs()), 1)

        self.logger.log_succeeded(id(job))
        self.assertEqual(count(self.logger.get_logs()), 1)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(count(self.logger.get_logs()), 1)

    def testGetSucceededLogs(self):
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.log_succeeded(id(job))
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_succeeded_logs(), 0), Log))

    def testGetAbortedLogs(self):
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs()), 1)
        self.assert_(isinstance(nth(self.logger.get_aborted_logs(), 0), Log))

    def testAddLog(self):
        self.assertEqual(count(self.logger.get_logs()), 0)
        log = self.logger.add_log(id(self.job), self.job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertEqual(str(log), '')
        return log

    def testLog(self):
        log = self.testAddLog()
        self.logger.log(id(self.job), 'hello world')
        self.assertEqual(str(log), 'hello world')
        return log

    def testLogAborted(self):
        log = self.testLog()
        try:
            raise FakeError()
        except Exception:
            self.logger.log_aborted(id(self.job), sys.exc_info())
        self.assert_('FakeError' in str(log))
        return log

    def testLogSucceeded(self):
        log = self.testLog()
        self.logger.log_succeeded(id(self.job))
        self.assertEqual(str(log), 'hello world')
        return log

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoggerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = LogTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.Log    import Log
from Exscript        import Host
from util.reportTest import FakeError

class LogTest(unittest.TestCase):
    CORRELATE = Log

    def setUp(self):
        self.log = Log('testme')

    def testConstructor(self):
        self.assertEqual('', str(self.log))

    def testGetError(self):
        self.assertEqual(self.log.get_error(), None)
        self.log.started()
        self.assertEqual(self.log.get_error(), None)
        try:
            raise FakeError()
        except FakeError:
            self.log.aborted(sys.exc_info())
        self.assert_('FakeError' in self.log.get_error())

    def testGetName(self):
        self.assertEqual(self.log.get_name(), 'testme')
        self.log.started()
        self.assertEqual(self.log.get_name(), 'testme')

    def testWrite(self):
        self.assertEqual('', str(self.log))
        self.log.write('test', 'me', 'please')
        self.assertEqual(str(self.log), 'test me please')

    def testStarted(self):
        self.assertEqual('', str(self.log))
        self.log.started()
        self.assertEqual(self.log.did_end, False)
        self.assertEqual('', str(self.log))

    def testAborted(self):
        self.testStarted()
        before = str(self.log)
        try:
            raise FakeError()
        except FakeError:
            self.log.aborted(sys.exc_info())
        self.assert_(str(self.log).startswith(before))
        self.assert_('FakeError' in str(self.log), str(self.log))

    def testSucceeded(self):
        self.testStarted()
        self.failIf(self.log.has_ended())
        self.log.succeeded()
        self.assertEqual(str(self.log), '')
        self.assert_(self.log.has_ended())
        self.failIf(self.log.has_error())

    def testHasError(self):
        self.failIf(self.log.has_error())
        self.testAborted()
        self.assert_(self.log.has_error())

    def testHasEnded(self):
        self.failIf(self.log.has_ended())
        self.testSucceeded()
        self.assert_(self.log.has_ended())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(LogTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = memtest
# This script is not meant to provide a fully automated test, it's
# merely a hack/starting point for investigating memory consumption
# manually. The behavior also depends heavily on the version of meliae.
import gc
import re
from Exscript.protocols import connect
from Exscript.util.decorator import bind
from Exscript import Queue, Account, Host

objnames = ('count_calls',)
follow_modules = False

def count_calls(conn, thedata, **kwargs):
    thedata['n_calls'] += 1

def foobar():
    pass

queue = Queue()
data  = {'n_calls': 0}
func  = bind(count_calls, data)
task  = queue.run(['t1', 't2', 't3', 't4', 't5', 't6'], func)
task.wait()
queue.shutdown()
queue.destroy()

del func

# Test memory consumption.
from meliae import scanner
gc.collect()
scanner.dump_all_objects("test.dump")
from meliae import loader
om = loader.load('test.dump')
om.remove_expensive_references()
om.collapse_instance_dicts()
om.compute_referrers()
om.compute_total_size()
#print om.summarize()

from pprint import pprint as pp

def larger(x, y):
    return om[y].total_size - om[x].total_size

def larger(x, y):
    return int(y.total_size - x.total_size)

objs = sorted(om.objs.itervalues(), larger)

def is_builtin(o):
    return o.type_str in ('builtin_function_or_method',)

def contains_builtin(reflist):
    for ref in reflist:
        if is_builtin(om[ref]):
            return True
    return False

def is_basic_type(o):
    return o.type_str in ('int', 'str', 'bool', 'NoneType')

def print_obj(lbl, o, indent = 0):
    print (" " * indent) + lbl, o.address, o.type_str, o.name, o.total_size, o.referrers

def print_ref(o, indent = 0, done = None):
    if o.type_str == '<ex-reference>':
        return
    if not is_basic_type(o):
        print_obj('Ref:', o, indent)
        #for ref in o.referrers:
        #    print_obj_recursive(om[ref], indent + 1, done)

def print_obj_recursive(o, indent = 0, done = None):
    if o.type_str == 'frame':
        print_obj('Frame:', o, indent)
        return
    if o.type_str == 'module' and not follow_modules:
        print_obj('Module:', o, indent)
        return

    if done is None:
        done = set()
    elif o.address in done:
        print_obj('Did that:', o, indent)
        return
    done.add(o.address)

    builtin = contains_builtin(o.ref_list)
    if builtin:
        print_obj('Builtin:', o, indent)
    else:
        print_obj('Obj:', o, indent)

    for ref in o.referrers:
        child = om[ref]
        print_obj_recursive(child, indent + 1, done)

    if not builtin:
        for ref in o.ref_list:
            print_ref(om[ref], indent + 1, done)

for obj in objs:
    if obj.type_str in objnames:
        print_obj_recursive(obj)
    if obj.name and obj.name in objnames:
        print_obj_recursive(obj)

#for addr in sorted(set(thedict.ref_list), larger):
#    print om[addr]

########NEW FILE########
__FILENAME__ = memtest_host
# This script is not meant to provide a fully automated test, it's
# merely a hack/starting point for investigating memory consumption
# manually. The behavior also depends heavily on the version of meliae.
from meliae import scanner, loader
from Exscript import Account, Host

hostlist = [Host(str(i)) for i in range(1, 10000)]
#accountlist = [Account(str(i)) for i in range(1, 10000)]

scanner.dump_all_objects('test.dump')
om = loader.load('test.dump')
print om.summarize()

########NEW FILE########
__FILENAME__ = PrivateKeyTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript import PrivateKey

class PrivateKeyTest(unittest.TestCase):
    CORRELATE = PrivateKey

    def setUp(self):
        self.filename = 'my.key'
        self.password = 'test1'
        self.key      = None

    def testConstructor(self):
        self.key = PrivateKey()
        self.assertRaises(TypeError, PrivateKey, 'foo')
        PrivateKey('rsa')
        PrivateKey('dss')

    def testFromFile(self):
        self.key = PrivateKey.from_file(self.filename, self.password, 'dss')
        self.assertEqual(self.key.get_type(), 'dss')
        self.assertEqual(self.filename, self.key.get_filename())
        self.assertEqual(self.password, self.key.get_password())

    def testGetType(self):
        self.testConstructor()
        self.assertEqual(self.key.get_type(), 'rsa')
        self.key = PrivateKey('dss')
        self.assertEqual(self.key.get_type(), 'dss')

    def testGetFilename(self):
        self.testConstructor()
        self.assertEqual(None, self.key.get_filename())
        self.key.set_filename(self.filename)
        self.assertEqual(self.filename, self.key.get_filename())

    def testSetFilename(self):
        self.testGetFilename()

    def testGetPassword(self):
        self.testConstructor()
        self.assertEqual(None, self.key.get_password())
        self.key.set_password(self.password)
        self.assertEqual(self.password, self.key.get_password())

    def testSetPassword(self):
        self.testGetPassword()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(PrivateKeyTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = DummyTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ProtocolTest       import ProtocolTest
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy

class DummyTest(ProtocolTest):
    CORRELATE = Dummy

    def createProtocol(self):
        self.protocol = Dummy(device = self.device)

    def testConstructor(self):
        self.assert_(isinstance(self.protocol, Dummy))

    def testIsDummy(self):
        self.assert_(self.protocol.is_dummy())

    def _create_dummy_and_eat_banner(self, device, port = None):
        protocol = Dummy(device = device)
        protocol.connect(device.hostname, port)
        self.assertEqual(str(protocol.buffer), '')
        self.assertEqual(protocol.response, None)
        protocol.expect(re.compile(re.escape(self.banner)))
        self.assertEqual(protocol.response, '')
        return protocol

    def testDummy(self):
        # Test simple instance with banner.
        protocol = Dummy(device = self.device)
        protocol.connect('testhost')
        self.assertEqual(str(protocol.buffer), '')
        self.assertEqual(protocol.response, None)
        protocol.close()

        # Test login.
        protocol = Dummy(device = self.device)
        protocol.connect('testhost')
        self.assertEqual(str(protocol.buffer), '')
        self.assertEqual(protocol.response, None)
        protocol.login(self.account, flush = False)
        self.assertEqual(protocol.buffer.tail(len(self.prompt)), self.prompt)
        protocol.close()

        # Test login with user prompt.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_USERONLY)
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol.buffer), 'User: ')
        protocol.login(self.account, flush = False)
        self.assertEqual(protocol.buffer.tail(len(self.prompt)), self.prompt)
        protocol.close()

        # Test login with password prompt.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_PASSWORDONLY)
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol.buffer), 'Password: ')
        protocol.login(self.account, flush = False)
        self.assertEqual(protocol.buffer.tail(len(self.prompt)), self.prompt)
        protocol.close()

        # Test login without user/password prompt.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_NONE)
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol.buffer), self.prompt)
        protocol.close()

        # Test login with user prompt and wait parameter.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_USERONLY)
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol.buffer), 'User: ')
        protocol.login(self.account)
        self.assertEqual(str(protocol.buffer), '')
        self.assertEqual(protocol.response, self.user + '\r')
        protocol.close()

        # Test login with password prompt and wait parameter.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_PASSWORDONLY)
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol.buffer), 'Password: ')
        protocol.login(self.account)
        self.assertEqual(str(protocol.buffer),   '')
        self.assertEqual(protocol.response, self.password + '\r')
        protocol.close()

        # Test login with port number.
        protocol = self._create_dummy_and_eat_banner(device, 1234)
        self.assertEqual(str(protocol.buffer), 'Password: ')
        protocol.login(self.account)
        self.assertEqual(str(protocol.buffer), '')
        self.assertEqual(protocol.response, self.password + '\r')
        protocol.close()

        # Test a custom response.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_NONE)
        protocol = Dummy(device = device)
        command  = re.compile(r'testcommand')
        response = 'hello world\r\n%s> ' % self.hostname
        device.add_command(command, response, prompt = False)
        protocol.set_prompt(re.compile(r'> $'))
        protocol.connect('testhost')
        protocol.expect(re.compile(re.escape(self.banner)))
        self.assertEqual(protocol.response, '')
        self.assertEqual(str(protocol.buffer), self.prompt)
        protocol.expect_prompt()
        self.assertEqual(str(protocol.buffer), '')
        self.assertEqual(protocol.response, self.hostname)
        protocol.execute('testcommand')
        expected = 'testcommand\rhello world\r\n' + self.hostname
        self.assertEqual(protocol.response, expected)
        self.assertEqual(str(protocol.buffer), '')
        protocol.close()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DummyTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = OsGuesserTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.protocols.OsGuesser import OsGuesser

class OsGuesserTest(unittest.TestCase):
    CORRELATE = OsGuesser

    def setUp(self):
        self.sa = OsGuesser()

    def testConstructor(self):
        osg = OsGuesser()
        self.assert_(isinstance(osg, OsGuesser))

    def testReset(self):
        self.testSet()
        self.sa.reset()
        self.testSet()

    def testSet(self):
        self.assertEqual(self.sa.get('test'),      None)
        self.assertEqual(self.sa.get('test', 0),   None)
        self.assertEqual(self.sa.get('test', 50),  None)
        self.assertEqual(self.sa.get('test', 100), None)

        self.sa.set('test', 'foo', 0)
        self.assertEqual(self.sa.get('test'),     'foo')
        self.assertEqual(self.sa.get('test', 0),  'foo')
        self.assertEqual(self.sa.get('test', 10), None)

        self.sa.set('test', 'foo', 10)
        self.assertEqual(self.sa.get('test'),     'foo')
        self.assertEqual(self.sa.get('test', 0),  'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

        self.sa.set('test', 'foo', 5)
        self.assertEqual(self.sa.get('test'),     'foo')
        self.assertEqual(self.sa.get('test', 0),  'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

    def testSetFromMatch(self):
        match_list = ((re.compile('on'),  'uno',  50),
                      (re.compile('two'), 'doe',  0),
                      (re.compile('one'), 'eins', 90))
        self.assertEqual(self.sa.get('test'), None)

        self.sa.set_from_match('test', match_list, '2two2')
        self.assertEqual(self.sa.get('test'), 'doe')

        self.sa.set_from_match('test', match_list, '2one2')
        self.assertEqual(self.sa.get('test'), 'eins')

    def testGet(self):
        pass # See testSet().

    def testDataReceived(self):
        dirname    = os.path.dirname(__file__)
        banner_dir = os.path.join(dirname, 'banners')
        for file in os.listdir(banner_dir):
            if file.startswith('.'):
                continue
            osname = file.split('.')[0]
            file   = os.path.join(banner_dir, file)
            banner = open(file).read().rstrip('\n')
            osg    = OsGuesser()
            for char in banner:
                osg.data_received(char, False)
            self.assertEqual(osg.get('os'), osname)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OsGuesserTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = ProtocolTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import time
from functools import partial
from ConfigParser                 import RawConfigParser
from Exscript                     import Account, PrivateKey
from Exscript.emulators           import VirtualDevice
from Exscript.protocols.Exception import TimeoutException, \
                                         InvalidCommandException, \
                                         ExpectCancelledException
from Exscript.protocols.Protocol import Protocol

class ProtocolTest(unittest.TestCase):
    """
    Since protocols.Protocol is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    CORRELATE = Protocol

    def setUp(self):
        self.hostname = '127.0.0.1'
        self.port     = 1236
        self.user     = 'user'
        self.password = 'password'
        self.account  = Account(self.user, password = self.password)
        self.daemon   = None

        self.createVirtualDevice()
        self.createDaemon()
        if self.daemon is not None:
            self.daemon.start()
            time.sleep(.2)
        self.createProtocol()

    def tearDown(self):
        if self.daemon is not None:
            self.daemon.exit()
            self.daemon.join()

    def createVirtualDevice(self):
        self.banner = 'Welcome to %s!\n' % self.hostname
        self.prompt = self.hostname + '> '
        self.device = VirtualDevice(self.hostname, echo = True)
        ls_response = '-rw-r--r--  1 sab  nmc    1628 Aug 18 10:02 file'
        self.device.add_command('ls',   ls_response)
        self.device.add_command('df',   'foobar')
        self.device.add_command('exit', '')
        self.device.add_command('this-command-causes-an-error',
                                '\ncommand not found')

    def createDaemon(self):
        pass

    def createProtocol(self):
        self.protocol = Protocol()

    def doConnect(self):
        self.protocol.connect(self.hostname, self.port)

    def doLogin(self, flush = True):
        self.doConnect()
        self.protocol.login(self.account, flush = flush)

    def doProtocolAuthenticate(self, flush = True):
        self.doConnect()
        self.protocol.protocol_authenticate(self.account)

    def doAppAuthenticate(self, flush = True):
        self.protocol.app_authenticate(self.account, flush)

    def doAppAuthorize(self, flush = True):
        self.protocol.app_authorize(self.account, flush)

    def _trymatch(self, prompts, string):
        for regex in prompts:
            match = regex.search(string)
            if match:
                return match
        return None

    def testPrompts(self):
        prompts = ('[sam123@home ~]$',
                   '[MyHost-A1]',
                   '<MyHost-A1>',
                   'sam@knip:~/Code/exscript$',
                   'sam@MyHost-X123>',
                   'sam@MyHost-X123#',
                   'MyHost-ABC-CDE123>',
                   'MyHost-A1#',
                   'S-ABC#',
                   '0123456-1-1-abc#',
                   '0123456-1-1-a>',
                   'MyHost-A1(config)#',
                   'MyHost-A1(config)>',
                   'RP/0/RP0/CPU0:A-BC2#',
                   'FA/0/1/2/3>',
                   'FA/0/1/2/3(config)>',
                   'FA/0/1/2/3(config)#',
                   'ec-c3-c27s99(su)->',
                   'foobar:0>',
                   'admin@s-x-a6.a.bc.de.fg:/# ',
                   'admin@s-x-a6.a.bc.de.fg:/% ')
        notprompts = ('one two',
                      ' [MyHost-A1]',
                      '[edit]\r',
                      '[edit]\n',
                      '[edit foo]\r',
                      '[edit foo]\n',
                      '[edit foo]\r\n',
                      '[edit one two]')
        prompt_re = self.protocol.get_prompt()
        for prompt in prompts:
            if not self._trymatch(prompt_re, '\n' + prompt):
                self.fail('Prompt %s does not match exactly.' % prompt)
            if not self._trymatch(prompt_re, 'this is a test\r\n' + prompt):
                self.fail('Prompt %s does not match.' % prompt)
            if self._trymatch(prompt_re, 'some text ' + prompt):
                self.fail('Prompt %s matches incorrectly.' % repr(prompt))
        for prompt in notprompts:
            if self._trymatch(prompt_re, prompt):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))
            if self._trymatch(prompt_re, prompt + ' '):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))
            if self._trymatch(prompt_re, '\n' + prompt):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))

    def testConstructor(self):
        self.assert_(isinstance(self.protocol, Protocol))

    def testCopy(self):
        self.assertEqual(self.protocol, self.protocol.__copy__())

    def testDeepcopy(self):
        self.assertEqual(self.protocol, self.protocol.__deepcopy__({}))

    def testIsDummy(self):
        self.assertEqual(self.protocol.is_dummy(), False)

    def testSetDriver(self):
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        self.protocol.set_driver()
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        self.protocol.set_driver('ios')
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'ios')

        self.protocol.set_driver()
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

    def testGetDriver(self):
        pass # Already tested in testSetDriver()

    def testAutoinit(self):
        self.protocol.autoinit()

    def _test_prompt_setter(self, getter, setter):
        initial_regex = getter()
        self.assert_(isinstance(initial_regex, list))
        self.assert_(hasattr(initial_regex[0], 'groups'))

        my_re = re.compile(r'% username')
        setter(my_re)
        regex = getter()
        self.assert_(isinstance(regex, list))
        self.assert_(hasattr(regex[0], 'groups'))
        self.assertEqual(regex[0], my_re)

        setter()
        regex = getter()
        self.assertEqual(regex, initial_regex)

    def testSetUsernamePrompt(self):
        self._test_prompt_setter(self.protocol.get_username_prompt,
                                 self.protocol.set_username_prompt)

    def testGetUsernamePrompt(self):
        pass # Already tested in testSetUsernamePrompt()

    def testSetPasswordPrompt(self):
        self._test_prompt_setter(self.protocol.get_password_prompt,
                                 self.protocol.set_password_prompt)

    def testGetPasswordPrompt(self):
        pass # Already tested in testSetPasswordPrompt()

    def testSetPrompt(self):
        self._test_prompt_setter(self.protocol.get_prompt,
                                 self.protocol.set_prompt)

    def testGetPrompt(self):
        pass # Already tested in testSetPrompt()

    def testSetErrorPrompt(self):
        self._test_prompt_setter(self.protocol.get_error_prompt,
                                 self.protocol.set_error_prompt)

    def testGetErrorPrompt(self):
        pass # Already tested in testSetErrorPrompt()

    def testSetLoginErrorPrompt(self):
        self._test_prompt_setter(self.protocol.get_login_error_prompt,
                                 self.protocol.set_login_error_prompt)

    def testGetLoginErrorPrompt(self):
        pass # Already tested in testSetLoginErrorPrompt()

    def testSetTimeout(self):
        self.assert_(self.protocol.get_timeout() == 30)
        self.protocol.set_timeout(60)
        self.assert_(self.protocol.get_timeout() == 60)

    def testGetTimeout(self):
        pass # Already tested in testSetTimeout()

    def testConnect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.connect)
            return
        self.assertEqual(self.protocol.response, None)
        self.doConnect()
        self.assertEqual(self.protocol.response, None)
        self.assertEqual(self.protocol.get_host(), self.hostname)

    def testLogin(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.login,
                              self.account)
            return
        # Password login.
        self.doLogin(flush = False)
        self.assert_(self.protocol.response is not None)
        self.assert_(len(self.protocol.response) > 0)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key     = PrivateKey.from_file('foo', keytype = 'rsa')
        account = Account(self.user, self.password, key = key)
        self.doConnect()
        self.failIf(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())
        self.protocol.login(account, flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.authenticate,
                              self.account)
            return
        self.doConnect()

        # Password login.
        self.failIf(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())
        self.protocol.authenticate(self.account, flush = False)
        self.assert_(self.protocol.response is not None)
        self.assert_(len(self.protocol.response) > 0)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key     = PrivateKey.from_file('foo', keytype = 'rsa')
        account = Account(self.user, self.password, key = key)
        self.doConnect()
        self.failIf(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())
        self.protocol.authenticate(account, flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

    def testProtocolAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.protocol.protocol_authenticate(self.account)
            return
        # There is no guarantee that the device provided any response
        # during protocol level authentification.
        self.doProtocolAuthenticate(flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

    def testIsProtocolAuthenticated(self):
        pass # See testProtocolAuthenticate()

    def testAppAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.app_authenticate,
                              self.account)
            return
        self.testProtocolAuthenticate()
        self.doAppAuthenticate(flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

    def testIsAppAuthenticated(self):
        pass # See testAppAuthenticate()

    def testAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.app_authorize)
            return
        self.doProtocolAuthenticate(flush = False)
        self.doAppAuthenticate(flush = False)
        response = self.protocol.response

        # Authorize should see that a prompt is still in the buffer,
        # and do nothing.
        self.doAppAuthorize(flush = False)
        self.assertEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

        self.doAppAuthorize(flush = True)
        self.failUnlessEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testAutoAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(TypeError, self.protocol.auto_app_authorize)
            return

        self.testAppAuthenticate()
        response = self.protocol.response

        # This should do nothing, because our test host does not
        # support AAA. Can't think of a way to test against a
        # device using AAA.
        self.protocol.auto_app_authorize(self.account, flush = False)
        self.failUnlessEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

        self.protocol.auto_app_authorize(self.account, flush = True)
        self.failUnlessEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testIsAppAuthorized(self):
        pass # see testAppAuthorize()

    def testSend(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.send, 'ls')
            return
        self.doLogin()
        self.protocol.execute('ls')

        self.protocol.send('df\r')
        self.assert_(self.protocol.response is not None)
        self.assert_(self.protocol.response.startswith('ls'))

        self.protocol.send('exit\r')
        self.assert_(self.protocol.response is not None)
        self.assert_(self.protocol.response.startswith('ls'))

    def testExecute(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.execute, 'ls')
            return
        self.doLogin()
        self.protocol.execute('ls')
        self.assert_(self.protocol.response is not None)
        self.assert_(self.protocol.response.startswith('ls'))

        # Make sure that we raise an error if the device responds
        # with something that matches any of the error prompts.
        self.protocol.set_error_prompt('.')
        self.assertRaises(InvalidCommandException,
                          self.protocol.execute,
                          'this-command-causes-an-error')

    def testWaitfor(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.waitfor, 'ls')
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.protocol.waitfor(re.compile(r'[\r\n]'))
        self.failIfEqual(oldresponse, self.protocol.response)
        oldresponse = self.protocol.response
        self.protocol.waitfor(re.compile(r'[\r\n]'))
        self.assertEqual(oldresponse, self.protocol.response)

    def testExpect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.expect, 'ls')
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.protocol.expect(re.compile(r'[\r\n]'))
        self.failIfEqual(oldresponse, self.protocol.response)

    def testExpectPrompt(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.expect, 'ls')
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.protocol.expect_prompt()
        self.failIfEqual(oldresponse, self.protocol.response)

    def testAddMonitor(self):
        # Set the monitor callback up.
        def monitor_cb(thedata, *args, **kwargs):
            thedata['args']   = args
            thedata['kwargs'] = kwargs
        data = {}
        self.protocol.add_monitor('abc', partial(monitor_cb, data))

        # Simulate some non-matching data.
        self.protocol.buffer.append('aaa')
        self.assertEqual(data, {})

        # Simulate some matching data.
        self.protocol.buffer.append('abc')
        self.assertEqual(len(data.get('args')), 3)
        self.assertEqual(data.get('args')[0], self.protocol)
        self.assertEqual(data.get('args')[1], 0)
        self.assertEqual(data.get('args')[2].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

    def testGetBuffer(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.assertEqual(str(self.protocol.buffer), '')
        self.doLogin()
        # Depending on whether the connected host sends a banner,
        # the buffer may or may not contain anything now.

        before = str(self.protocol.buffer)
        self.protocol.send('ls\r')
        self.protocol.waitfor(self.protocol.get_prompt())
        self.assertNotEqual(str(self.protocol.buffer), before)

    def _cancel_cb(self, data):
        self.protocol.cancel_expect()

    def testCancelExpect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.data_received_event.connect(self._cancel_cb)
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.assertRaises(ExpectCancelledException,
                          self.protocol.expect,
                          'notgoingtohappen')

    def testInteract(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.interact)
            return
        # Can't really be tested.

    def testClose(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.close)
            return
        self.doConnect()
        self.protocol.close(True)

    def testGetHost(self):
        self.assert_(self.protocol.get_host() is None)
        if self.protocol.__class__ == Protocol:
            return
        self.doConnect()
        self.assertEqual(self.protocol.get_host(), self.hostname)

    def testGuessOs(self):
        self.assertEqual('unknown', self.protocol.guess_os())
        # Other tests can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.close)
            return
        self.doConnect()
        self.assertEqual('unknown', self.protocol.guess_os())
        self.protocol.login(self.account)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())
        self.assertEqual('shell', self.protocol.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ProtocolTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
('show version', """
Cisco Internetwork Operating System Software 
IOS (tm) GS Software (C12KPRP-P-M), Version 12.0(32)SY6c, RELEASE SOFTWARE (fc3)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2008 by cisco Systems, Inc.
Compiled Mon 08-Sep-08 15:31 by leccese
Image text-base: 0x00010000, data-base: 0x055CD000

ROM: System Bootstrap, Version 12.0(20040128:214555) [assafb-PRP1P_20040101 1.8dev(2.83)] DEVELOPMENT SOFTWARE
BOOTLDR: GS Software (C12KPRP-P-M), Version 12.0(32)SY6c, RELEASE SOFTWARE (fc3)

 S-EA1 uptime is 36 weeks, 1 day, 15 hours, 9 minutes
Uptime for this control processor is 36 weeks, 1 day, 14 hours, 30 minutes
System returned to ROM by reload at 03:32:54 MET Mon Feb 16 2009
System restarted at 03:25:22 MET Tue Mar 10 2009
System image file is "disk0:c12kprp-p-mz.120-32.SY6c.bin"

cisco 12416/PRP (MPC7457) processor (revision 0x00) with 1048576K bytes of memory.
MPC7457 CPU at 1263Mhz, Rev 1.1, 512KB L2, 2048KB L3 Cache
Last reset from power-on
Channelized E1, Version 1.0.

2 Route Processor Cards
2 Clock Scheduler Cards
3 Switch Fabric Cards
4 T1/E1 BITS controllers
1 Quad-port OC3c ATM controller (4 ATM).
2 16-port OC3 POS controllers (32 POS).
2 four-port OC12 POS controllers (8 POS).
2 twelve-port E3 controllers (24 E3).
1 Four Port Gigabit Ethernet/IEEE 802.3z controller (4 GigabitEthernet).
4 OC12 channelized to STS-12c/STM-4, STS-3c/STM-1 or DS-3/E3 controllers
4 ISE 10G SPA Interface Cards (12000-SIP-601)
3 Ethernet/IEEE 802.3 interface(s)
56 FastEthernet/IEEE 802.3 interface(s)
14 GigabitEthernet/IEEE 802.3 interface(s)
111 Serial network interface(s)
4 ATM network interface(s)
50 Packet over SONET network interface(s)
2043K bytes of non-volatile configuration memory.

250880K bytes of ATA PCMCIA card at slot 0 (Sector size 512 bytes).
65536K bytes of Flash internal SIMM (Sector size 256K).
Configuration register is 0x2102
"""),

(r'show diag \d+', """
SLOT 0  (RP/LC 0 ): 16 Port ISE Packet Over SONET OC-3c/STM-1 Single Mode/IR LC connector
  MAIN: type 79,  800-19733-08 rev A0
        Deviation: 0
        HW config: 0x01    SW key: 00-00-00
  PCA:  73-7614-07 rev A0 ver 1
        Design Release 1.0  S/N SAL1026SSZX
  MBUS: Embedded Agent
        Test hist: 0x00    RMA#: 00-00-00    RMA hist: 0x00
  DIAG: Test count: 0x00000000    Test results: 0x00000000
  FRU:  Linecard/Module: 16OC3X/POS-IR-LC-B=
        Processor Memory: MEM-LC-ISE-1024=
        Packet Memory: MEM-LC1-PKT-512=(Non-Replaceable)
  L3 Engine: 3 - ISE OC48 (2.5 Gbps)
  MBUS Agent Software version 2.68 (RAM) (ROM version is 3.66)
  ROM Monitor version 18.0
  Fabric Downloader version used 7.1 (ROM version is 7.1)
  Primary clock is CSC 1
  Board is analyzed 
  Board State is Line Card Enabled (IOS  RUN )
  Insertion time: 00:00:30 (36w1d ago)
  Processor Memory size: 1073741824 bytes
  TX Packet Memory size: 268435456 bytes, Packet Memory pagesize: 16384 bytes
  RX Packet Memory size: 268435456 bytes, Packet Memory pagesize: 16384 bytes
  0 crashes since restart
"""),
)

########NEW FILE########
__FILENAME__ = run_suite
../run_suite.py
########NEW FILE########
__FILENAME__ = SSH2Test
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ProtocolTest       import ProtocolTest
from Exscript.servers   import SSHd
from Exscript.protocols import SSH2
from Exscript import PrivateKey

keyfile = os.path.join(os.path.dirname(__file__), 'id_rsa')
key = PrivateKey.from_file(keyfile)

class SSH2Test(ProtocolTest):
    CORRELATE = SSH2

    def createDaemon(self):
        self.daemon = SSHd(self.hostname, self.port, self.device, key = key)

    def createProtocol(self):
        self.protocol = SSH2()

    def testConstructor(self):
        self.assert_(isinstance(self.protocol, SSH2))

    def testLogin(self):
        self.assertRaises(IOError, ProtocolTest.testLogin, self)

    def testAuthenticate(self):
        self.assertRaises(IOError, ProtocolTest.testAuthenticate, self)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSH2Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = TelnetTest
import sys, unittest, re, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ProtocolTest       import ProtocolTest
from Exscript           import Account
from Exscript.servers   import Telnetd
from Exscript.protocols import Telnet

class TelnetTest(ProtocolTest):
    CORRELATE = Telnet

    def createDaemon(self):
        self.daemon = Telnetd(self.hostname, self.port, self.device)

    def createProtocol(self):
        self.protocol = Telnet()

    def testConstructor(self):
        self.assert_(isinstance(self.protocol, Telnet))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = QueueTest
import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

warnings.simplefilter('ignore', DeprecationWarning)

import shutil
import time
import ctypes
from functools import partial
from tempfile import mkdtemp
from multiprocessing import Value
from multiprocessing.managers import BaseManager
from Exscript import Queue, Account, AccountPool, FileLogger
from Exscript.protocols import Protocol, Dummy
from Exscript.interpreter.Exception import FailException
from Exscript.util.decorator import bind
from Exscript.util.log import log_to

def count_calls(job, data, **kwargs):
    assert hasattr(job, 'start')
    assert kwargs.has_key('testarg')
    data.value += 1

def count_calls2(job, host, conn, data, **kwargs):
    assert isinstance(conn, Protocol)
    count_calls(job, data, **kwargs)

def count_and_fail(job, data, **kwargs):
    count_calls(job, data, **kwargs)
    raise FailException('intentional error')

def spawn_subtask(job, host, conn, queue, data, **kwargs):
    count_calls2(job, host, conn, data, **kwargs)
    func  = bind(count_calls2, data, testarg = 1)
    task  = queue.priority_run('subtask', func)
    task.wait()

def do_nothing(job, host, conn):
    pass

def say_hello(job, host, conn):
    conn.send('hello')

def error(job, host, conn):
    say_hello(job, host, conn)
    raise FailException('intentional error')

def fatal_error(job, host, conn):
    say_hello(job, host, conn)
    raise Exception('intentional fatal error')

class MyProtocol(Dummy):
    pass

def raise_if_not_myprotocol(job, host, conn):
    if not isinstance(conn, MyProtocol):
        raise Exception('not a MyProtocol instance')

class Log(object):
    data = ''

    def write(self, data):
        self.data += data

    def flush(self):
        pass

    def read(self):
        return self.data

class LogManager(BaseManager):
    pass
LogManager.register('Log', Log)

class QueueTest(unittest.TestCase):
    CORRELATE = Queue
    mode = 'threading'

    def createQueue(self, logdir = None, **kwargs):
        if self.queue:
            self.queue.destroy()
        self.out   = self.manager.Log()
        self.err   = self.manager.Log()
        self.queue = Queue(mode   = self.mode,
                           stdout = self.out,
                           stderr = self.err,
                           **kwargs)
        self.accm  = self.queue.account_manager
        if logdir is not None:
            self.logger = FileLogger(logdir)

    def setUp(self):
        self.tempdir = mkdtemp()
        self.queue   = None
        self.logger  = None
        self.manager = LogManager()
        self.manager.start()
        self.createQueue(verbose = -1, logdir = self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        try:
            self.queue.destroy()
        except:
            pass # queue already destroyed
        self.manager.shutdown()

    def assertVerbosity(self, channel, expected):
        data = channel.read()
        if expected == 'no_tb':
            self.assert_('error' in data, data)
            self.assert_('Traceback' not in data)
        elif expected == 'tb':
            self.assert_('error' in data, data)
            self.assert_('Traceback' in data)
        elif expected == '':
            self.assertEqual(data, '')
        else:
            msg = repr(expected) + ' not in ' + repr(data)
            self.assert_(expected in data, msg)

    def testConstructor(self):
        self.assertEqual(1, self.queue.get_max_threads())

        # Test all verbosity levels.
        levels = (
            (-1, 1, ('',      ''), ('',      ''),      ('',      'tb')),
            (-1, 2, ('',      ''), ('',      ''),      ('',      'tb')),
            (0,  1, ('',      ''), ('',      'no_tb'), ('',      'tb')),
            (0,  2, ('',      ''), ('',      'no_tb'), ('',      'tb')),
            (1,  1, ('hello', ''), ('hello', 'no_tb'), ('hello', 'tb')),
            (1,  2, ('[',     ''), ('[',     'no_tb'), ('[',     'tb')),
            (2,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (2,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
            (3,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (3,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
            (4,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (4,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
            (5,  1, ('hello', ''), ('hello', 'tb'),    ('hello', 'tb')),
            (5,  2, ('[',     ''), ('[',     'tb'),    ('[',     'tb')),
        )
        for level, max_threads, with_simple, with_error, with_fatal in levels:
            #print "S:", level, max_threads, with_simple, with_error, with_fatal
            stdout, stderr = with_simple
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy://mytest', say_hello)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            #print "E:", level, max_threads, with_simple, with_error, with_fatal
            stdout, stderr = with_error
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy://mytest', error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

            #print "F:", level, max_threads, with_simple, with_error, with_fatal
            stdout, stderr = with_fatal
            self.createQueue(verbose = level, max_threads = max_threads)
            self.queue.run('dummy://mytest', fatal_error)
            self.queue.join()
            self.assertVerbosity(self.out, stdout)
            self.assertVerbosity(self.err, stderr)

    def testCreatePipe(self):
        account = Account('user', 'test')
        self.accm.add_account(account)
        pipe = self.queue._create_pipe()
        pipe.send(('acquire-account', None))
        response = pipe.recv()
        expected = (account.__hash__(),
                    account.get_name(),
                    account.get_password(),
                    account.get_authorization_password(),
                    account.get_key())
        self.assertEqual(response, expected)
        pipe.send(('release-account', account.__hash__()))
        response = pipe.recv()
        self.assertEqual(response, 'ok')
        pipe.close()

    def testSetMaxThreads(self):
        self.assertEqual(1, self.queue.get_max_threads())
        self.queue.set_max_threads(2)
        self.assertEqual(2, self.queue.get_max_threads())

    def testGetMaxThreads(self):
        pass # Already tested in testSetMaxThreads().

    def testGetProgress(self):
        self.assertEqual(0.0, self.queue.get_progress())
        self.testIsCompleted()
        self.assertEqual(100.0, self.queue.get_progress())

    def testAddAccount(self):
        self.assertEqual(0, self.accm.default_pool.n_accounts())
        account = Account('user', 'test')
        self.queue.add_account(account)
        self.assertEqual(1, self.accm.default_pool.n_accounts())

    def testAddAccountPool(self):
        self.assertEqual(0, self.accm.default_pool.n_accounts())
        account = Account('user', 'test')
        self.queue.add_account(account)
        self.assertEqual(1, self.accm.default_pool.n_accounts())

        def match_cb(data, host):
            data['match-called'].value = True
            return True

        def start_cb(data, job, host, conn):
            account = conn.account_factory(None)
            data['start-called'].value = True
            data['account-hash'].value = account.__hash__()
            account.release()

        # Replace the default pool.
        pool1 = AccountPool()
        self.queue.add_account_pool(pool1)
        self.assertEqual(self.accm.default_pool, pool1)

        # Add another pool, making sure that it does not replace
        # the default pool.
        pool2    = AccountPool()
        account2 = Account('user', 'test')
        pool2.add_account(account2)

        match_called = Value(ctypes.c_bool, False)
        start_called = Value(ctypes.c_bool, False)
        account_hash = Value(ctypes.c_long, 0)
        data = {'match-called': match_called,
                'start-called': start_called,
                'account-hash': account_hash}
        self.queue.add_account_pool(pool2, partial(match_cb, data))
        self.assertEqual(self.accm.default_pool, pool1)

        # Make sure that pool2 is chosen (because the match function
        # returns True).
        self.queue.run('dummy://dummy', partial(start_cb, data))
        self.queue.shutdown()
        data = dict((k, v.value) for (k, v) in data.iteritems())
        self.assertEqual(data, {'match-called': True,
                                'start-called': True,
                                'account-hash': account2.__hash__()})

    def startTask(self):
        self.testAddAccount()
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        task  = self.queue.run(hosts, log_to(self.logger)(do_nothing))
        self.assert_(task is not None)
        return task

    def testIsCompleted(self):
        self.assert_(self.queue.is_completed())
        task = self.startTask()
        self.failIf(self.queue.is_completed())
        task.wait()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())

    def testJoin(self):
        task = self.startTask()
        self.queue.join()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())

    def testShutdown(self):
        task = self.startTask()   # this also adds an account
        self.queue.shutdown()
        self.assert_(task.is_completed())
        self.assert_(self.queue.is_completed())
        self.assertEqual(self.accm.default_pool.n_accounts(), 1)

    def testDestroy(self):
        task = self.startTask()   # this also adds an account
        self.queue.destroy()
        self.assert_(self.queue.is_completed())
        self.assertEqual(self.accm.default_pool.n_accounts(), 0)

    def testReset(self):
        self.testAddAccount()
        self.queue.reset()
        self.assertEqual(self.accm.default_pool.n_accounts(), 0)

    def testRun(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        func  = bind(count_calls2, data, testarg = 1)
        self.queue.run(hosts,    func)
        self.queue.run('dummy://dummy3', func)
        self.queue.shutdown()
        self.assertEqual(data.value, 3)

        self.queue.run('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 4)

    def testRunOrIgnore(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2', 'dummy://dummy1']
        func  = bind(count_calls2, data, testarg = 1)
        self.queue.workqueue.pause()
        self.queue.run_or_ignore(hosts,    func)
        self.queue.run_or_ignore('dummy://dummy2', func)
        self.queue.workqueue.unpause()
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.run_or_ignore('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 3)

    def testPriorityRun(self):
        def write(data, value, *args):
            data.value = value

        data = Value('i', 0)
        self.queue.workqueue.pause()
        self.queue.enqueue(partial(write, data, 1))
        self.queue.priority_run('dummy://dummy', partial(write, data, 2))
        self.queue.workqueue.unpause()
        self.queue.destroy()

        # The 'dummy' job should run first, so the value must
        # be overwritten by the other process.
        self.assertEqual(data.value, 1)

    def testPriorityRunOrRaise(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2', 'dummy://dummy1']
        func  = bind(count_calls2, data, testarg = 1)
        self.queue.workqueue.pause()
        self.queue.priority_run_or_raise(hosts,    func)
        self.queue.priority_run_or_raise('dummy://dummy2', func)
        self.queue.workqueue.unpause()
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.priority_run_or_raise('dummy://dummy4', func)
        self.queue.destroy()
        self.assertEqual(data.value, 3)

    def testForceRun(self):
        data  = Value('i', 0)
        hosts = ['dummy://dummy1', 'dummy://dummy2']
        func  = bind(count_calls2, data, testarg = 1)

        # By setting max_threads to 0 we ensure that the 'force' part is
        # actually tested; the thread should run regardless.
        self.queue.set_max_threads(0)
        self.queue.force_run(hosts, func)
        self.queue.destroy()
        self.assertEqual(data.value, 2)

    def testEnqueue(self):
        data = Value('i', 0)
        func = bind(count_calls, data, testarg = 1)
        self.queue.enqueue(func)
        self.queue.enqueue(func)
        self.queue.shutdown()
        self.assertEqual(data.value, 2)

        self.queue.enqueue(func)
        self.queue.shutdown()
        self.assertEqual(data.value, 3)

        func = bind(count_and_fail, data, testarg = 1)
        self.queue.enqueue(func, attempts = 7)
        self.queue.destroy()
        self.assertEqual(data.value, 10)

    #FIXME: Not a method test; this should probably be elsewhere.
    def testLogging(self):
        task = self.startTask()
        while not task.is_completed():
            time.sleep(.1)

        # The following function is not synchronous with the above, so add
        # a timeout to avoid races.
        time.sleep(.1)
        self.assert_(self.queue.is_completed())

        logfiles = os.listdir(self.tempdir)
        self.assertEqual(2, len(logfiles))
        self.assert_('dummy1.log' in logfiles)
        self.assert_('dummy2.log' in logfiles)
        for file in logfiles:
            content = open(os.path.join(self.tempdir, file)).read()

class QueueTestMultiProcessing(QueueTest):
    mode = 'multiprocessing'

def suite():
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(QueueTest)
    suite2 = loader.loadTestsFromTestCase(QueueTestMultiProcessing)
    return unittest.TestSuite((suite1, suite2))
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = run_suite
#!/usr/bin/env python
import os, sys, unittest, glob, fnmatch, re
from inspect import isfunction, ismodule, isclass

def uppercase(match):
    return match.group(1).upper()

correlated = dict()

def correlate_class(theclass):
    """
    Checks the given testcase for missing test methods.
    """
    if not hasattr(theclass, 'CORRELATE'):
        return

    # Collect all functions in the class or module.
    for name, value in theclass.CORRELATE.__dict__.iteritems():
        if not isfunction(value):
            continue
        elif name == '__init__':
            name = 'Constructor'
        elif name.startswith('_'):
            continue

        # Format the function names.
        testname   = re.sub(r'_(\w)',  uppercase, name)
        testname   = re.sub(r'(\d\w)', uppercase, testname)
        testname   = 'test' + re.sub(r'^(\w)', uppercase, testname)
        testmethod = theclass.__name__ + '.' + testname
        method     = theclass.CORRELATE.__name__ + '.' + name
        both       = testmethod + ' (' + method + ')'

        # Throw an error if the function does not have a test.
        if testname in dir(theclass):
            continue
        if ismodule(theclass.CORRELATE) and \
          value.__module__ != theclass.CORRELATE.__name__:
            continue # function was imported.
        if both in correlated:
            continue
        correlated[both] = True
        if ismodule(theclass.CORRELATE):
            sys.stderr.write('!!!! WARNING: Untested function: ' + both + '\n')
        elif isclass(theclass.CORRELATE):
            sys.stderr.write('!!!! WARNING: Untested method: ' + both + '\n')

def correlate_module(module):
    """
    Checks all testcases in the module for missing test methods.
    """
    for name, item in module.__dict__.iteritems():
        if isclass(item):
            correlate_class(item)

def find(dirname, pattern):
    output = []
    for root, dirs, files in os.walk(dirname):
        for file in files:
            if fnmatch.fnmatchcase(file, pattern):
                output.append(os.path.join(root, file))
    return output

def load_suite(files):
    modules    = [os.path.splitext(f)[0] for f in files]
    all_suites = []
    for name in modules:
        name   = name.lstrip('.').lstrip('/').replace('/', '.')
        module = __import__(name, globals(), locals(), [''])
        all_suites.append(module.suite())
        correlate_module(module)
    if correlated:
        sys.stderr.write('Error: Untested methods found.\n')
        sys.exit(1)
    return unittest.TestSuite(all_suites)

def suite():
    pattern = os.path.join(os.path.dirname(__file__), '*Test.py')
    files   = glob.glob(pattern)
    return load_suite([os.path.basename(f) for f in files])

def recursive_suite():
    return load_suite(find('.', '*Test.py'))

if __name__ == '__main__':
    # Parse CLI options.
    if len(sys.argv) == 1:
        verbosity = 2
    elif len(sys.argv) == 2:
        verbosity = int(sys.argv[1])
    else:
        print 'Syntax:', sys.argv[0], '[verbosity]'
        print 'Default verbosity is 2'
        sys.exit(1)

    # Run.
    unittest.TextTestRunner(verbosity = verbosity).run(recursive_suite())

########NEW FILE########
__FILENAME__ = run_suite
../run_suite.py
########NEW FILE########
__FILENAME__ = ServerTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import time
from Exscript           import Account
from Exscript.servers   import Server
from Exscript.emulators import VirtualDevice

class ServerTest(unittest.TestCase):
    CORRELATE = Server.Server

    def setUp(self):
        self.host   = 'localhost'
        self.port   = 1235
        self.device = VirtualDevice(self.host, echo = False)
        self.daemon = Server.Server(self.host, self.port, self.device)
        self.device.set_prompt(self.host + ':' + str(self.port) + '> ')

    def tearDown(self):
        if self.daemon:
            self.daemon.exit()
        if self.daemon.__class__ != Server.Server:
            self.daemon.join()

    def _create_daemon(self):
        raise NotImplementedError()

    def _create_client(self):
        raise NotImplementedError()

    def _add_commands(self):
        self.device.add_command('exit', self.daemon.exit_command)
        self.device.add_command('ls',   'ok1')
        self.device.add_command('ll',   'ok2\nfoobar:1>', prompt = False)
        self.device.add_command('.+',   'Unknown command.')

    def testConstructor(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server.Server:
            return
        self._create_daemon()
        self.daemon.start()
        time.sleep(1)

    def testStart(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server.Server:
            return
        self._create_daemon()
        self._add_commands()
        self.daemon.start()
        time.sleep(1)

        client = self._create_client()
        client.set_prompt(re.compile(r'\w+:\d+> ?'))
        client.connect(self.host, self.port)
        client.login(Account('user', 'password'))
        client.execute('ls')
        self.assertEqual(client.response, 'ok1\n')
        client.execute('ll')
        self.assertEqual(client.response, 'ok2\n')
        client.send('exit\r')

    def testExitCommand(self):
        pass # tested in testExit()

    def testExit(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server.Server:
            return
        self.testStart()
        # Since testStart() sent an "exit" command to the server,
        # it should be shutting down even without us calling
        # self.daemon.exit().
        self.daemon.join()
        self.testConstructor()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ServerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = SSHdTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ServerTest         import ServerTest
from Exscript.servers   import SSHd
from Exscript.protocols import SSH2

class SSHdTest(ServerTest):
    CORRELATE = SSHd

    def _create_daemon(self):
        self.daemon = SSHd(self.host, self.port, self.device)

    def _create_client(self):
        return SSH2()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SSHdTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = TelnetdTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ServerTest         import ServerTest
from Exscript.servers   import Telnetd
from Exscript.protocols import Telnet

class TelnetdTest(ServerTest):
    CORRELATE = Telnetd

    def _create_daemon(self):
        self.daemon = Telnetd(self.host, self.port, self.device)

    def _create_client(self):
        return Telnet()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TelnetdTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = TemplateTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Queue, Account, Logger, protocols
from Exscript.util           import template
from Exscript.util.decorator import bind
from Exscript.util.log       import log_to
from Exscript.util.report    import format
from Exscript.protocols      import Dummy
from Exscript.emulators      import IOSEmulator

test_dir = '../templates'

class Log(object):
    data = ''
    def collect(self, data):
        self.data += data
        return data

def dummy_cb(job, host, conn, template_test):
    # Warning: Assertions raised in this function happen in a subprocess!
    # Create a log object.
    log = Log()
    conn.data_received_event.connect(log.collect)

    # Connect and load the test template.
    conn.connect(host.get_address(), host.get_tcp_port())
    test_name = host.get_address()
    if host.get_protocol() == 'ios':
        dirname = os.path.join(test_dir, test_name)
    else:
        dirname = os.path.dirname(test_name)
    tmpl     = os.path.join(dirname, 'test.exscript')
    expected = os.path.join(dirname, 'expected')

    # Go.
    conn.login(flush = True)
    try:
        template.eval_file(conn, tmpl, slot = 10)
    except Exception, e:
        print log.data
        raise
    log.data = re.sub(r'\r\n', r'\n', log.data)
    #open(expected, 'w').write(log.data)
    if log.data != open(expected).read():
        print
        print "Got:", log.data
        print "---------------------------------------------"
        print "Expected:", open(expected).read()
    template_test.assertEqual(log.data, open(expected).read())

class IOSDummy(Dummy):
    def __init__(self, *args, **kwargs):
        device = IOSEmulator('dummy', strict = False)
        Dummy.__init__(self, device = device, **kwargs)
protocols.protocol_map['ios'] = IOSDummy

class TemplateTest(unittest.TestCase):
    def setUp(self):
        account     = Account('sab', '')
        self.queue  = Queue(verbose = 0, max_threads = 1)
        self.logger = Logger()
        self.queue.add_account(account)

    def tearDown(self):
        self.queue.destroy()

    def testTemplates(self):
        callback = bind(log_to(self.logger)(dummy_cb), self)
        for test in os.listdir(test_dir):
            pseudo = os.path.join(test_dir, test, 'pseudodev.py')
            if os.path.exists(pseudo):
                self.queue.run('pseudo://' + pseudo, callback)
            else:
                self.queue.run('ios://' + test, callback)
        self.queue.shutdown()

        # Unfortunately, unittest.TestCase does not fail if self.assert()
        # was called from a subthread, so this is our workaround...
        failed = self.logger.get_aborted_logs()
        report = format(self.logger, show_successful = False)
        self.assert_(not failed, report)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TemplateTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = bufferTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tempfile import TemporaryFile
from functools import partial
from Exscript.util.buffer import MonitoredBuffer

class bufferTest(unittest.TestCase):
    CORRELATE = MonitoredBuffer

    def testConstructor(self):
        MonitoredBuffer()
        with TemporaryFile() as f:
            MonitoredBuffer(f)

    def testSize(self):
        b = MonitoredBuffer()
        self.assertEqual(b.size(), 0)
        b.append('foo')
        self.assertEqual(b.size(), 3)
        b.append('bar')
        self.assertEqual(b.size(), 6)

    def testHead(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        self.assertEqual(b.head(0), '')
        self.assertEqual(b.head(10), '')

        b.append('foobar')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.head(0), '')
        self.assertEqual(b.head(1), 'f')
        self.assertEqual(b.head(6), 'foobar')
        self.assertEqual(b.head(10), 'foobar')

    def testTail(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        self.assertEqual(b.tail(0), '')
        self.assertEqual(b.tail(10), '')

        b.append('foobar')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.tail(0), '')
        self.assertEqual(b.tail(1), 'r')
        self.assertEqual(b.tail(6), 'foobar')
        self.assertEqual(b.tail(10), 'foobar')

    def testPop(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        self.assertEqual(b.pop(0), '')
        self.assertEqual(str(b), '')
        self.assertEqual(b.pop(10), '')
        self.assertEqual(str(b), '')

        b.append('foobar')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.pop(0), '')
        self.assertEqual(str(b), 'foobar')
        self.assertEqual(b.pop(2), 'fo')
        self.assertEqual(str(b), 'obar')

        b.append('doh')
        self.assertEqual(b.pop(10), 'obardoh')
        self.assertEqual(str(b), '')

    def testAppend(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        b.append('foo')
        self.assertEqual(str(b), 'foo')
        b.append('bar')
        self.assertEqual(str(b), 'foobar')
        b.append('doh')
        self.assertEqual(str(b), 'foobardoh')

    def testClear(self):
        b = MonitoredBuffer()
        self.assertEqual(str(b), '')
        b.append('foo')
        self.assertEqual(str(b), 'foo')
        b.clear()
        self.assertEqual(str(b), '')
        b.clear()
        self.assertEqual(str(b), '')

    def testAddMonitor(self):
        b = MonitoredBuffer()

        # Set the monitor callback up.
        def monitor_cb(thedata, *args, **kwargs):
            thedata['args']   = args
            thedata['kwargs'] = kwargs
        data = {}
        b.add_monitor('abc', partial(monitor_cb, data))

        # Test some non-matching data.
        b.append('aaa')
        self.assertEqual(data, {})
        b.append('aaa')
        self.assertEqual(data, {})

        # Test some matching data.
        b.append('abc')
        self.assertEqual(len(data.get('args')), 2)
        self.assertEqual(data.get('args')[0], 0)
        self.assertEqual(data.get('args')[1].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

        # Make sure that the same monitor is not called again.
        data.pop('args')
        data.pop('kwargs')
        b.append('bbb')
        self.assertEqual(data, {})

        # Test some matching data.
        b.append('abc')
        self.assertEqual(len(data.get('args')), 2)
        self.assertEqual(data.get('args')[0], 0)
        self.assertEqual(data.get('args')[1].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(bufferTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = castTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.cast
import re
from Exscript         import Host
from Exscript.Log     import Log
from Exscript.Logfile import Logfile

class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.cast

    def testToList(self):
        from Exscript.util.cast import to_list
        self.assertEqual(to_list(None),     [None])
        self.assertEqual(to_list([]),       [])
        self.assertEqual(to_list('test'),   ['test'])
        self.assertEqual(to_list(['test']), ['test'])

    def testToHost(self):
        from Exscript.util.cast import to_host
        self.assert_(isinstance(to_host('localhost'),       Host))
        self.assert_(isinstance(to_host(Host('localhost')), Host))
        self.assertRaises(TypeError, to_host, None)

    def testToHosts(self):
        from Exscript.util.cast import to_hosts
        self.assertRaises(TypeError, to_hosts, None)

        result = to_hosts([])
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 0)

        result = to_hosts('localhost')
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(isinstance(result[0], Host))

        result = to_hosts(Host('localhost'))
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(isinstance(result[0], Host))

        hosts  = ['localhost', Host('1.2.3.4')]
        result = to_hosts(hosts)
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 2)
        self.assert_(isinstance(result[0], Host))
        self.assert_(isinstance(result[1], Host))

    def testToRegex(self):
        from Exscript.util.cast import to_regex
        self.assert_(hasattr(to_regex('regex'), 'match'))
        self.assert_(hasattr(to_regex(re.compile('regex')), 'match'))
        self.assertRaises(TypeError, to_regex, None)

    def testToRegexs(self):
        from Exscript.util.cast import to_regexs
        self.assertRaises(TypeError, to_regexs, None)

        result = to_regexs([])
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 0)

        result = to_regexs('regex')
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(hasattr(result[0], 'match'))

        result = to_regexs(re.compile('regex'))
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(hasattr(result[0], 'match'))

        regexs = ['regex1', re.compile('regex2')]
        result = to_regexs(regexs)
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 2)
        self.assert_(hasattr(result[0], 'match'))
        self.assert_(hasattr(result[1], 'match'))
        self.assertEqual(result[0].pattern, 'regex1')
        self.assertEqual(result[1].pattern, 'regex2')

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = cryptTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.crypt

class cryptTest(unittest.TestCase):
    CORRELATE = Exscript.util.crypt

    def testOtp(self):
        from Exscript.util.crypt import otp
        hash = otp('password', 'abc123', 9999)
        self.assertEqual('ACTA AMMO CAR WEB BIN YAP', hash)
        hash = otp('password', 'abc123', 9998)
        self.assertEqual('LESS CLUE LISA MEAT MAGI USER', hash)
        hash = otp('pass', 'abc123', 9998)
        self.assertEqual('DRAB LEER VOTE RICH NEWS FRAU', hash)
        hash = otp('pass', 'abc888', 9998)
        self.assertEqual('DEBT BOON ASKS ORAL MEN WEE', hash)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(cryptTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = decoratorTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from functools import partial
import Exscript.util.decorator
from Exscript.util.impl import get_label
from Exscript import Host, Account
from Exscript.protocols import Protocol
from Exscript.protocols.Exception import LoginFailure
from util.reportTest import FakeJob
from multiprocessing import Value

class FakeConnection(object):
    def __init__(self, os = None):
        self.os   = os
        self.data = {}
        self.host = None

    def connect(self, hostname, port):
        self.host = hostname

    def get_host(self):
        return self.host

    def login(self, flush = True):
        self.logged_in     = True
        self.login_flushed = flush

    def close(self, force):
        self.connected    = False
        self.close_forced = force

    def guess_os(self):
        return self.os

class decoratorTest(unittest.TestCase):
    CORRELATE = Exscript.util.decorator

    def bind_cb(self, job, bound_arg1, bound_arg2, **kwargs):
        self.assert_(isinstance(job, FakeJob))
        self.assertEqual(bound_arg1, 'one')
        self.assertEqual(bound_arg2, 'two')
        self.assertEqual(kwargs.get('three'), 3)
        return 123

    def testBind(self):
        from Exscript.util.decorator import bind
        bound  = bind(self.bind_cb, 'one', 'two', three = 3)
        result = bound(FakeJob())
        self.assert_(result == 123, result)

    def ios_cb(self, job, *args):
        return 'hello ios'

    def junos_cb(self, job, *args):
        return 'hello junos'

    def testOsFunctionMapper(self):
        from Exscript.util.decorator import os_function_mapper
        cb_map = {'ios': self.ios_cb, 'junos': self.junos_cb}
        mapper = os_function_mapper(cb_map)
        job    = FakeJob()
        host   = object()

        # Test with 'ios'.
        conn   = FakeConnection(os = 'ios')
        result = mapper(job, host, conn)
        self.assertEqual(result, 'hello ios')

        # Test with 'junos'.
        conn   = FakeConnection(os = 'junos')
        result = mapper(job, host, conn)
        self.assertEqual(result, 'hello junos')

        # Test with unsupported OS.
        conn = FakeConnection(os = 'unknown')
        self.assertRaises(Exception, mapper, job, host, conn)

    def autologin_cb(self, job, host, conn, *args, **kwargs):
        self.assertEqual(conn.logged_in, True)
        self.assertEqual(conn.login_flushed, False)
        return self.bind_cb(job, *args, **kwargs)

    def testAutologin(self):
        from Exscript.util.decorator import autologin
        job  = FakeJob()
        host = job.data['host']
        conn = job.data['conn'] = FakeConnection()

        # Test simple login.
        decor  = autologin(flush = False)
        bound  = decor(self.autologin_cb)
        result = bound(job, host, conn, 'one', 'two', three = 3)
        self.assertEqual(result, 123)

        # Monkey patch the fake connection such that the login fails.
        conn = FakeConnection()
        data = Value('i', 0)
        def fail(data, *args, **kwargs):
            data.value += 1
            raise LoginFailure('intended login failure')
        conn.login = partial(fail, data)

        # Test retry functionality.
        decor = autologin(flush = False, attempts = 5)
        bound = decor(self.autologin_cb)
        job   = FakeJob()
        job.data['conn'] = conn
        self.assertRaises(LoginFailure,
                          bound,
                          job,
                          host,
                          conn,
                          'one',
                          'two',
                          three = 3)
        self.assertEqual(data.value, 5)

    def testDeprecated(self):
        pass #not really needed.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(decoratorTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = eventTest
import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.util.event import Event

class eventTest(unittest.TestCase):
    CORRELATE = Event

    def setUp(self):
        self.event  = Event()
        self.args   = None
        self.kwargs = None

    def callback(self, *args, **kwargs):
        self.args   = args
        self.kwargs = kwargs

    def callback2(self, *args, **kwargs):
        self.callback(*args, **kwargs)

    def testConstructor(self):
        event = Event()

    def testConnect(self):
        self.event.connect(self.callback)
        self.assertEqual(self.event.n_subscribers(), 1)
        self.assertRaises(AttributeError, self.event.connect, self.callback)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)

    def testListen(self):
        import gc
        from Exscript.util.weakmethod import WeakMethod
        def thefunction():
            pass
        ref = self.event.listen(thefunction)
        self.assert_(isinstance(ref, WeakMethod))
        self.assertEqual(self.event.n_subscribers(), 1)
        self.assertRaises(AttributeError, self.event.listen, thefunction)
        del thefunction
        gc.collect()
        self.assertEqual(self.event.n_subscribers(), 0)

    def testNSubscribers(self):
        self.assertEqual(self.event.n_subscribers(), 0)
        self.event.connect(self.callback)
        self.assertEqual(self.event.n_subscribers(), 1)
        self.event.listen(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)

    def testIsConnected(self):
        self.assertEqual(self.event.is_connected(self.callback), False)
        self.event.connect(self.callback)
        self.assertEqual(self.event.is_connected(self.callback), True)

        self.assertEqual(self.event.is_connected(self.callback2), False)
        self.event.listen(self.callback2)
        self.assertEqual(self.event.is_connected(self.callback2), True)

    def testEmit(self):
        self.event.connect(self.callback)
        self.assertEqual(self.args,   None)
        self.assertEqual(self.kwargs, None)

        self.event.emit()
        self.assertEqual(self.args,   ())
        self.assertEqual(self.kwargs, {})

        self.event.emit('test')
        self.assertEqual(self.args,   ('test',))
        self.assertEqual(self.kwargs, {})

        self.event.emit('test', foo = 'bar')
        self.assertEqual(self.args,   ('test',))
        self.assertEqual(self.kwargs, {'foo': 'bar'})
        self.event.disconnect(self.callback)

        self.event.listen(self.callback)
        self.args   = None
        self.kwargs = None

        self.event.emit()
        self.assertEqual(self.args,   ())
        self.assertEqual(self.kwargs, {})

        self.event.emit('test')
        self.assertEqual(self.args,   ('test',))
        self.assertEqual(self.kwargs, {})

        self.event.emit('test', foo = 'bar')
        self.assertEqual(self.args,   ('test',))
        self.assertEqual(self.kwargs, {'foo': 'bar'})
        self.event.disconnect(self.callback)

    def testDisconnect(self):
        self.assertEqual(self.event.n_subscribers(), 0)
        self.event.connect(self.callback)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)
        self.event.disconnect(self.callback)
        self.assertEqual(self.event.n_subscribers(), 1)
        self.event.disconnect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 0)

    def testDisconnectAll(self):
        self.assertEqual(self.event.n_subscribers(), 0)
        self.event.connect(self.callback)
        self.event.connect(self.callback2)
        self.assertEqual(self.event.n_subscribers(), 2)
        self.event.disconnect_all()
        self.assertEqual(self.event.n_subscribers(), 0)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(eventTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = fileTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import base64
import Exscript.util.file
from tempfile import NamedTemporaryFile

account_pool = [('user1', 'password1'),
                ('user2', 'password2'),
                ('user3', 'password3'),
                ('user4', 'password4')]

hosts          = ['localhost', '1.2.3.4', 'ssh://test', 'ssh1://another:23']
expected_hosts = ['localhost', '1.2.3.4', 'test',       'another']

class fileTest(unittest.TestCase):
    CORRELATE = Exscript.util.file

    def setUp(self):
        data  = '[account-pool]\n'
        data += 'user1='   + base64.encodestring('password1') + '\n'
        data += 'user2:'   + base64.encodestring('password2') + '\n'
        data += 'user3 = ' + base64.encodestring('password3') + '\n'
        data += 'user4 : ' + base64.encodestring('password4') + '\n'
        self.account_file = NamedTemporaryFile()
        self.account_file.write(data)
        self.account_file.flush()

        self.host_file = NamedTemporaryFile()
        self.host_file.write('\n'.join(hosts))
        self.host_file.flush()

        self.csv_host_file = NamedTemporaryFile()
        self.csv_host_file.write('hostname	test\n')
        self.csv_host_file.write('\n'.join([h + '	blah' for h in hosts]))
        self.csv_host_file.flush()

        self.lib_file = NamedTemporaryFile()
        self.lib_file.write('__lib__ = {"test": object}\n')
        self.lib_file.flush()

    def tearDown(self):
        self.account_file.close()
        self.host_file.close()
        self.csv_host_file.close()

    def testGetAccountsFromFile(self):
        from Exscript.util.file import get_accounts_from_file
        accounts = get_accounts_from_file(self.account_file.name)
        result   = [(a.get_name(), a.get_password()) for a in accounts]
        result.sort()
        self.assertEqual(account_pool, result)

    def testGetHostsFromFile(self):
        from Exscript.util.file import get_hosts_from_file
        result = get_hosts_from_file(self.host_file.name)
        self.assertEqual([h.get_name() for h in result], expected_hosts)

    def testGetHostsFromCsv(self):
        from Exscript.util.file import get_hosts_from_csv
        result    = get_hosts_from_csv(self.csv_host_file.name)
        hostnames = [h.get_name() for h in result]
        testvars  = [h.get('test')[0] for h in result]
        self.assertEqual(hostnames, expected_hosts)
        self.assertEqual(testvars, ['blah' for h in result])

    def testLoadLib(self):
        from Exscript.util.file import load_lib
        functions = load_lib(self.lib_file.name)
        name = os.path.splitext(os.path.basename(self.lib_file.name))[0]
        self.assertEqual({name + '.test': object}, functions)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(fileTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = interactTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tempfile import NamedTemporaryFile
import Exscript.util.interact
from Exscript.util.interact import InputHistory

class InputHistoryTest(unittest.TestCase):
    CORRELATE = InputHistory

    def setUp(self):
        t = NamedTemporaryFile()
        self.history = InputHistory(t.name)

    def testConstructor(self):
        t = NamedTemporaryFile()
        h = InputHistory()
        h = InputHistory(t.name)
        h = InputHistory(t.name, 'foo')
        h.set('aaa', 'bbb')
        self.assertEqual(open(t.name).read(), '[foo]\naaa = bbb\n\n')

    def testGet(self):
        self.assertEqual(self.history.get('bar'), None)
        self.assertEqual(self.history.get('bar', None), None)
        self.assertEqual(self.history.get('bar', '...'), '...')
        self.history.set('bar', 'myvalue')
        self.assertEqual(self.history.get('bar'), 'myvalue')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue')
        self.assertEqual(self.history.get('bar', None), 'myvalue')

    def testSet(self):
        self.testGet()
        self.history.set('bar', 'myvalue2')
        self.assertEqual(self.history.get('bar'), 'myvalue2')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue2')
        self.assertEqual(self.history.get('bar', None), 'myvalue2')
        self.history.set('bar', None)
        self.assertEqual(self.history.get('bar'), 'myvalue2')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue2')
        self.assertEqual(self.history.get('bar', None), 'myvalue2')

class interactTest(unittest.TestCase):
    CORRELATE = Exscript.util.interact

    def testPrompt(self):
        from Exscript.util.interact import prompt
        # Can't really be tested, as it is interactive.

    def testGetFilename(self):
        from Exscript.util.interact import get_filename
        # Can't really be tested, as it is interactive.

    def testGetUser(self):
        from Exscript.util.interact import get_user
        # Can't really be tested, as it is interactive.

    def testGetLogin(self):
        from Exscript.util.interact import get_login
        # Can't really be tested, as it is interactive.

    def testReadLogin(self):
        from Exscript.util.interact import read_login
        # Can't really be tested, as it is interactive.

def suite():
    loader   = unittest.TestLoader()
    thesuite = unittest.TestSuite()
    thesuite.addTest(loader.loadTestsFromTestCase(InputHistoryTest))
    thesuite.addTest(loader.loadTestsFromTestCase(interactTest))
    return thesuite
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = ipTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.ip

class ipTest(unittest.TestCase):
    CORRELATE = Exscript.util.ip

    def testIsIp(self):
        from Exscript.util.ip import is_ip
        self.assert_(is_ip('0.0.0.0'))
        self.assert_(is_ip('::'))
        self.assert_(not is_ip('1'))

    def testNormalizeIp(self):
        from Exscript.util.ip import normalize_ip
        self.assertEqual(normalize_ip('0.128.255.0'), '000.128.255.000')
        self.assertEqual(normalize_ip('1234:0:01:02::'),
                         '1234:0000:0001:0002:0000:0000:0000:0000')

    def testCleanIp(self):
        from Exscript.util.ip import clean_ip
        self.assertEqual(clean_ip('192.168.010.001'), '192.168.10.1')
        self.assertEqual(clean_ip('1234:0:0:0:0:0:0:000A'), '1234::a')

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = ipv4Test
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.ipv4

class ipv4Test(unittest.TestCase):
    CORRELATE = Exscript.util.ipv4

    def testIsIp(self):
        from Exscript.util.ipv4 import is_ip
        self.assert_(is_ip('0.0.0.0'))
        self.assert_(is_ip('255.255.255.255'))
        self.assert_(is_ip('1.2.3.4'))
        self.assert_(not is_ip(''))
        self.assert_(not is_ip('1'))
        self.assert_(not is_ip('1.2.3.'))
        self.assert_(not is_ip('.1.2.3'))
        self.assert_(not is_ip('1.23.4'))
        self.assert_(not is_ip('1..3.4'))

    def testNormalizeIp(self):
        from Exscript.util.ipv4 import normalize_ip
        self.assertEqual(normalize_ip('0.0.0.0'),         '000.000.000.000')
        self.assertEqual(normalize_ip('255.255.255.255'), '255.255.255.255')
        self.assertEqual(normalize_ip('001.002.003.004'), '001.002.003.004')
        self.assertEqual(normalize_ip('192.168.010.001'), '192.168.010.001')
        self.assertEqual(normalize_ip('0.128.255.0'),     '000.128.255.000')

    def testCleanIp(self):
        from Exscript.util.ipv4 import clean_ip
        self.assertEqual(clean_ip('0.0.0.0'),         '0.0.0.0')
        self.assertEqual(clean_ip('255.255.255.255'), '255.255.255.255')
        self.assertEqual(clean_ip('001.002.003.004'), '1.2.3.4')
        self.assertEqual(clean_ip('192.168.010.001'), '192.168.10.1')
        self.assertEqual(clean_ip('0.128.255.0'),     '0.128.255.0')

    def testIp2Int(self):
        from Exscript.util.ipv4 import ip2int
        self.assertEqual(ip2int('0.0.0.0'),         0x00000000l)
        self.assertEqual(ip2int('255.255.255.255'), 0xFFFFFFFFl)
        self.assertEqual(ip2int('255.255.255.0'),   0xFFFFFF00l)
        self.assertEqual(ip2int('0.255.255.0'),     0x00FFFF00l)
        self.assertEqual(ip2int('0.128.255.0'),     0x0080FF00l)

    def testInt2Ip(self):
        from Exscript.util.ipv4 import int2ip, ip2int
        for ip in ('0.0.0.0',
                   '255.255.255.255',
                   '255.255.255.0',
                   '0.255.255.0',
                   '0.128.255.0'):
            self.assertEqual(int2ip(ip2int(ip)), ip)

    def testPfxlen2MaskInt(self):
        from Exscript.util.ipv4 import pfxlen2mask_int, int2ip
        self.assertEqual(int2ip(pfxlen2mask_int(32)), '255.255.255.255')
        self.assertEqual(int2ip(pfxlen2mask_int(31)), '255.255.255.254')
        self.assertEqual(int2ip(pfxlen2mask_int(30)), '255.255.255.252')
        self.assertEqual(int2ip(pfxlen2mask_int(2)),  '192.0.0.0')
        self.assertEqual(int2ip(pfxlen2mask_int(1)),  '128.0.0.0')
        self.assertEqual(int2ip(pfxlen2mask_int(0)),  '0.0.0.0')

    def testPfxlen2Mask(self):
        from Exscript.util.ipv4 import pfxlen2mask
        self.assertEqual(pfxlen2mask(32), '255.255.255.255')
        self.assertEqual(pfxlen2mask(31), '255.255.255.254')
        self.assertEqual(pfxlen2mask(30), '255.255.255.252')
        self.assertEqual(pfxlen2mask(2),  '192.0.0.0')
        self.assertEqual(pfxlen2mask(1),  '128.0.0.0')
        self.assertEqual(pfxlen2mask(0),  '0.0.0.0')

    def testMask2Pfxlen(self):
        from Exscript.util.ipv4 import mask2pfxlen
        self.assertEqual(32, mask2pfxlen('255.255.255.255'))
        self.assertEqual(31, mask2pfxlen('255.255.255.254'))
        self.assertEqual(30, mask2pfxlen('255.255.255.252'))
        self.assertEqual(2,  mask2pfxlen('192.0.0.0'))
        self.assertEqual(1,  mask2pfxlen('128.0.0.0'))
        self.assertEqual(0,  mask2pfxlen('0.0.0.0'))

    def testParsePrefix(self):
        from Exscript.util.ipv4 import parse_prefix
        self.assertEqual(('1.2.3.4', 24), parse_prefix('1.2.3.4'))
        self.assertEqual(('1.2.3.4', 32), parse_prefix('1.2.3.4',    32))
        self.assertEqual(('1.2.3.4', 15), parse_prefix('1.2.3.4/15'))
        self.assertEqual(('1.2.3.4', 15), parse_prefix('1.2.3.4/15', 32))

    def testNetwork(self):
        from Exscript.util.ipv4 import network
        self.assertEqual(network('10.0.0.0/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.1/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.2/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.3/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.0/24'), '10.0.0.0')
        self.assertEqual(network('10.0.0.255/24'), '10.0.0.0')

    def testBroadcast(self):
        from Exscript.util.ipv4 import broadcast
        self.assertEqual(broadcast('10.0.0.0/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.1/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.2/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.3/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.0/24'), '10.0.0.255')
        self.assertEqual(broadcast('10.0.0.255/24'), '10.0.0.255')

    def testRemoteIp(self):
        from Exscript.util.ipv4 import remote_ip
        self.assertEqual(remote_ip('10.0.0.0'), '10.0.0.3')
        self.assertEqual(remote_ip('10.0.0.1'), '10.0.0.2')
        self.assertEqual(remote_ip('10.0.0.2'), '10.0.0.1')
        self.assertEqual(remote_ip('10.0.0.3'), '10.0.0.0')

    def testSort(self):
        from Exscript.util.ipv4 import sort
        import random
        ip_list = ['0.0.0.0',
                   '0.0.0.255',
                   '1.2.3.4',
                   '255.255.0.255',
                   '255.255.255.255',
                   '255.255.255.255']
        ip_list_copy = ip_list[:]
        for i in range(50):
            random.shuffle(ip_list_copy)
            self.assertEqual(ip_list, sort(ip_list_copy))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipv4Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = ipv6Test
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.ipv6

class ipv6Test(unittest.TestCase):
    CORRELATE = Exscript.util.ipv6

    def testIsIp(self):
        from Exscript.util.ipv6 import is_ip
        self.assert_(is_ip('::'))
        self.assert_(is_ip('1::'))
        self.assert_(is_ip('::A'))
        self.assert_(is_ip('1234::2222'))
        self.assert_(is_ip('1234:0:01:02::'))
        self.assert_(is_ip('1:2:3:4:5:6:7:8'))
        self.failIf(is_ip(':::'))
        self.failIf(is_ip('1:2:3:4:5:6:7:8:9'))
        self.failIf(is_ip('1::A::2'))
        self.failIf(is_ip('1::A::'))
        self.failIf(is_ip('::A::'))
        self.failIf(is_ip('::A::1'))
        self.failIf(is_ip('A'))
        self.failIf(is_ip('X::'))

    def testNormalizeIp(self):
        from Exscript.util.ipv6 import normalize_ip
        self.assertEqual(normalize_ip('::'),
                         '0000:0000:0000:0000:0000:0000:0000:0000')
        self.assertEqual(normalize_ip('1::'),
                         '0001:0000:0000:0000:0000:0000:0000:0000')
        self.assertEqual(normalize_ip('::A'),
                         '0000:0000:0000:0000:0000:0000:0000:000a')
        self.assertEqual(normalize_ip('1234::2222'),
                         '1234:0000:0000:0000:0000:0000:0000:2222')
        self.assertEqual(normalize_ip('1234:0:01:02::'),
                         '1234:0000:0001:0002:0000:0000:0000:0000')

    def testCleanIp(self):
        from Exscript.util.ipv6 import clean_ip

        self.assertEqual(clean_ip('1234:0:0:0:0:0:0:000A'), '1234::a')
        self.assertEqual(clean_ip('1234:0:0:0:1:0:0:0'), '1234:0:0:0:1::')
        self.assertEqual(clean_ip('0:0:0:0:0:0:0:0'), '::')
        self.assertEqual(clean_ip('0001:0:0:0:0000:0000:0000:0000'), '1::')
        self.assertEqual(clean_ip('::A'), '::a')
        self.assertEqual(clean_ip('A::A'), 'a::a')
        self.assertEqual(clean_ip('A::'), 'a::')
        self.assertEqual(clean_ip('1234:0:01:02::'), '1234:0:1:2::')

    def testParsePrefix(self):
        from Exscript.util.ipv6 import parse_prefix
        self.assertEqual(('A::A', 24), parse_prefix('A::A/24', 22))
        self.assertEqual(('1:0:1:2::', 128), parse_prefix('1:0:1:2::'))
        self.assertEqual(('1:0:1:2::', 64), parse_prefix('1:0:1:2::', 64))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipv6Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = mailTest
import sys, unittest, re, os.path, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from getpass import getuser
import Exscript.util.mail
from Exscript.util.mail import Mail

vars     = dict(testvar1 = 'blah', testvar2 = 'foo', testvar3 = 'bar')
template = '''
To: user, user2@localhost
Cc: user3
Bcc: user4
Subject: Blah blah {testvar1}

Test body: {testvar2}
{testvar3}
'''.strip()

smtp = '''
From: test
To: user,
 user2@localhost
Cc: user3
Bcc: user4
Subject: Blah blah {testvar1}

Test body: {testvar2}
{testvar3}
'''.strip().replace('\n', '\r\n')

class MailTest(unittest.TestCase):
    CORRELATE = Mail

    def setUp(self):
        self.mail = Mail(sender = 'test')

    def testConstructor(self):
        mail = Mail()
        self.failIfEqual(mail.get_sender(), None)
        self.failIfEqual(mail.get_sender(), '')
        user = getuser()
        self.assert_(mail.get_sender().startswith(user + '@'))

    def testSetFromTemplateString(self):
        self.mail.set_from_template_string(template)
        tmpl = self.mail.get_smtp_mail().strip()
        self.assertEqual(tmpl, smtp)
        head = self.mail.get_smtp_header().strip()
        self.assert_(tmpl.startswith(head))

    def testSetSender(self):
        self.assertEqual(self.mail.get_sender(), 'test')
        self.mail.set_sender('test2')
        self.assertEqual(self.mail.get_sender(), 'test2')

    def testGetSender(self):
        pass # see testSetSender()

    def checkSetAddr(self, set_method, get_method):
        set_method('test')
        self.assertEqual(get_method(), ['test'])

        set_method(['test1', 'test2'])
        self.assertEqual(get_method(), ['test1', 'test2'])

        set_method('test1, test2')
        self.assertEqual(get_method(), ['test1', 'test2'])

    def checkAddAddr(self, add_method, get_method):
        add_method(['test1', 'test2'])
        self.assertEqual(get_method(), ['test1', 'test2'])

        add_method('test3, test4')
        self.assertEqual(get_method(), ['test1', 'test2', 'test3', 'test4'])

    def testSetTo(self):
        self.checkSetAddr(self.mail.set_to, self.mail.get_to)

    def testAddTo(self):
        self.checkAddAddr(self.mail.add_to, self.mail.get_to)

    def testGetTo(self):
        pass # see testSetTo()

    def testSetCc(self):
        self.checkSetAddr(self.mail.set_cc, self.mail.get_cc)

    def testAddCc(self):
        self.checkAddAddr(self.mail.add_cc, self.mail.get_cc)

    def testGetCc(self):
        pass # see testSetCc()

    def testSetBcc(self):
        self.checkSetAddr(self.mail.set_bcc, self.mail.get_bcc)

    def testAddBcc(self):
        self.checkAddAddr(self.mail.add_bcc, self.mail.get_bcc)

    def testGetBcc(self):
        pass # see testSetBcc()

    def testGetReceipients(self):
        self.mail.set_to('test1')
        self.mail.set_cc('test2')
        self.mail.set_bcc('test3')
        self.assertEqual(self.mail.get_receipients(),
                         ['test1', 'test2', 'test3'])

    def testSetSubject(self):
        self.assertEqual(self.mail.get_subject(), '')
        self.mail.set_subject('test')
        self.assertEqual(self.mail.get_subject(), 'test')

    def testGetSubject(self):
        pass # see testSetSubject()

    def testSetBody(self):
        self.assertEqual(self.mail.get_body(), '')
        self.mail.set_body('test')
        self.assertEqual(self.mail.get_body(), 'test')

    def testGetBody(self):
        pass # see testSetBody()

    def testAddAttachment(self):
        self.assertEqual(self.mail.get_attachments(), [])
        self.mail.add_attachment('foo')
        self.assertEqual(self.mail.get_attachments(), ['foo'])
        self.mail.add_attachment('bar')
        self.assertEqual(self.mail.get_attachments(), ['foo', 'bar'])

    def testGetAttachments(self):
        self.testAddAttachment()

    def testGetSmtpHeader(self):
        pass # see testSetFromTemplateString()

    def testGetSmtpMail(self):
        pass # see testSetFromTemplateString()

class mailTest(unittest.TestCase):
    CORRELATE = Exscript.util.mail

    def checkResult(self, mail):
        self.assert_(isinstance(mail, Mail))

        # Remove the "From:" line.
        result   = mail.get_smtp_mail().split('\n', 1)[1].strip()
        expected = smtp.split('\n', 1)[1].strip()

        # Compare the results.
        for key, value in vars.iteritems():
            expected = expected.replace('{' + key + '}', value)
        self.assertEqual(result, expected)

    def testFromTemplateString(self):
        from Exscript.util.mail import from_template_string
        mail = from_template_string(template, **vars)
        self.checkResult(mail)

    def testFromTemplate(self):
        from Exscript.util.mail import from_template
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write(template)
        tmpfile.flush()
        mail = from_template(tmpfile.name, **vars)
        tmpfile.close()
        self.checkResult(mail)

    def testSend(self):
        pass # no easy way to test without spamming.

def suite():
    mail_cls    = unittest.TestLoader().loadTestsFromTestCase(MailTest)
    mail_module = unittest.TestLoader().loadTestsFromTestCase(mailTest)
    return unittest.TestSuite([mail_cls, mail_module])
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = matchTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.match

class matchTest(unittest.TestCase):
    CORRELATE = Exscript.util.match

    def testFirstMatch(self):
        from Exscript.util.match import first_match

        string = 'my test'
        self.assert_(first_match(string, r'aaa') is None)
        self.assert_(first_match(string, r'\S+') == 'my test')
        self.assert_(first_match(string, r'(aaa)') is None)
        self.assert_(first_match(string, r'(\S+)') == 'my')
        self.assert_(first_match(string, r'(aaa) (\S+)') == (None, None))
        self.assert_(first_match(string, r'(\S+) (\S+)') == ('my', 'test'))

        multi_line = 'hello\nworld\nhello world'
        self.assert_(first_match(multi_line, r'(he)llo') == 'he')

    def testAnyMatch(self):
        from Exscript.util.match import any_match

        string = 'one uno\ntwo due'
        self.assert_(any_match(string, r'aaa')   == [])
        self.assert_(any_match(string, r'\S+')   == ['one uno', 'two due'])
        self.assert_(any_match(string, r'(aaa)') == [])
        self.assert_(any_match(string, r'(\S+)') == ['one', 'two'])
        self.assert_(any_match(string, r'(aaa) (\S+)') == [])
        expected = [('one', 'uno'), ('two', 'due')]
        self.assert_(any_match(string, r'(\S+) (\S+)') == expected)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(matchTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = reportTest
import sys, unittest, re, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import traceback
import Exscript.util.report
from Exscript            import Host
from Exscript            import Logger
from Exscript.util.event import Event
from Exscript.workqueue  import WorkQueue

class FakeQueue(object):
    workqueue = WorkQueue()

class FakeJob(object):
    def __init__(self, name = 'fake'):
        self.function = lambda x: None
        self.name     = name
        self.failures = 0
        self.data     = {'pipe':   0,
                         'stdout': sys.stdout,
                         'host':   Host('foo')}

class FakeError(Exception):
    pass

class reportTest(unittest.TestCase):
    CORRELATE = Exscript.util.report

    def setUp(self):
        self.logger    = Logger()
        self.n_actions = 0

    def createLog(self):
        self.n_actions += 1
        name            = 'fake' + str(self.n_actions)
        job             = FakeJob(name)
        self.logger.add_log(id(job), job.name, 1)
        self.logger.log(id(job), 'hello world')
        return job

    def createAbortedLog(self):
        job = self.createLog()
        try:
            raise FakeError()
        except Exception:
            thetype, exc, tb = sys.exc_info()
            tb = ''.join(traceback.format_exception(thetype, exc, tb))
            self.logger.log_aborted(id(job), (thetype, exc, tb))
        return job

    def createSucceededLog(self):
        job = self.createLog()
        self.logger.log_succeeded(id(job))
        return job

    def testStatus(self):
        from Exscript.util.report import status
        self.createSucceededLog()
        expect = 'One action done (succeeded)'
        self.assertEqual(status(self.logger), expect)

        self.createSucceededLog()
        expect = '2 actions total (all succeeded)'
        self.assertEqual(status(self.logger), expect)

        self.createAbortedLog()
        expect = '3 actions total (1 failed, 2 succeeded)'
        self.assertEqual(status(self.logger), expect)

    def testSummarize(self):
        from Exscript.util.report import summarize
        self.createSucceededLog()
        self.createAbortedLog()
        expected = 'fake1: ok\nfake2: FakeError'
        self.assertEqual(summarize(self.logger), expected)

    def testFormat(self):
        from Exscript.util.report import format
        self.createSucceededLog()
        self.createAbortedLog()
        self.createSucceededLog()
        file     = os.path.splitext(__file__)[0]
        expected = '''
Failed actions:
---------------
fake2:
Traceback (most recent call last):
  File "%s.py", line 44, in createAbortedLog
    raise FakeError()
FakeError


Successful actions:
-------------------
fake1
fake3'''.strip() % file
        self.assertEqual(format(self.logger), expected)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(reportTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = run_suite
../run_suite.py
########NEW FILE########
__FILENAME__ = startTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript
import Exscript.util.start
from multiprocessing import Value

def count_calls(job, host, conn, data, **kwargs):
    # Warning: Assertions raised in this function happen in a subprocess!
    assert kwargs.get('testarg') == 1
    assert isinstance(conn, Exscript.protocols.Protocol)
    data.value += 1

class startTest(unittest.TestCase):
    CORRELATE = Exscript.util.start

    def setUp(self):
        from Exscript import Account
        from Exscript.util.decorator import bind

        self.data     = Value('i', 0)
        self.callback = bind(count_calls, self.data, testarg = 1)
        self.account  = Account('test', 'test')

    def doTest(self, function):
        # Run on zero hosts.
        function(self.account, [], self.callback, verbose = 0)
        self.assertEqual(self.data.value, 0)

        # Run on one host.
        function(self.account, 'dummy://localhost', self.callback, verbose = 0)
        self.assertEqual(self.data.value, 1)

        # Run on multiple hosts.
        hosts = ['dummy://host1', 'dummy://host2']
        function(self.account, hosts, self.callback, verbose = 0)
        self.assertEqual(self.data.value, 3)

        # Run on multiple hosts with multiple threads.
        function(self.account,
                 hosts,
                 self.callback,
                 max_threads = 2,
                 verbose     = 0)
        self.assertEqual(self.data.value, 5)

    def testRun(self):
        from Exscript.util.start import run
        self.doTest(run)

    def testQuickrun(self):
        pass # can't really be tested, as it is user interactive

    def testStart(self):
        from Exscript.util.start import start
        self.doTest(start)

    def testQuickstart(self):
        pass # can't really be tested, as it is user interactive

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(startTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = syslogTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.syslog

class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.syslog

    def testNetlog(self):
        from Exscript.util.syslog import netlog
        #FIXME: dont really know how to test this; we'd need to know
        # how to open a local syslog server.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = ttyTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import tempfile
import Exscript.util.tty

class ttyTest(unittest.TestCase):
    CORRELATE = Exscript.util.tty

    def setUp(self):
        self.tempfile = tempfile.TemporaryFile()
        self.stdout   = sys.stdout
        self.stderr   = sys.stderr
        self.stdin    = sys.stdin
        sys.stdout = sys.stderr = sys.stdin = self.tempfile

    def _unredirect(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        sys.stdin  = self.stdin

    def tearDown(self):
        self._unredirect()
        self.tempfile.close()

    def testGetTerminalSize(self):
        from Exscript.util.tty import get_terminal_size

        # This hack really makes the test incomplete because
        # get_terminal_size() won't be able to check the cterm size,
        # but it is the only way to test at least partially.
        os.ctermid = lambda: '/nosuchfileexists'

        # By deleting PATH we prevent get_terminal_size() from asking
        # the stty unix program.
        oldpath = os.environ['PATH']
        os.environ['PATH'] = ''

        # If the LINES and COLUMNS variables are not set, all methods should
        # now fail, and the default values are returned.
        os.environ['LINES']   = ''
        os.environ['COLUMNS'] = ''
        self.assertEqual(get_terminal_size(),       (25, 80))
        self.assertEqual(get_terminal_size(10, 10), (10, 10))

        # If the LINES and COLUMNS variables are set, they should be used.
        os.environ['LINES']   = '1000'
        os.environ['COLUMNS'] = '1000'
        self.assertEqual(get_terminal_size(),       (1000, 1000))
        self.assertEqual(get_terminal_size(10, 10), (1000, 1000))

        # If the stty program exists, it should be used.
        os.environ['PATH'] = oldpath
        try:
            self.assertNotEqual(get_terminal_size(),       (1000, 1000))
            self.assertNotEqual(get_terminal_size(10, 10), (1000, 1000))
        except OSError:
            pass # "stty" not found.

        # Lastly, if stdin/stderr/stdout exist, they should tell us something.
        os.environ['PATH'] = ''
        self._unredirect()
        self.assertNotEqual(get_terminal_size(),       (1000, 1000))
        self.assertNotEqual(get_terminal_size(10, 10), (1000, 1000))
        os.environ['PATH'] = oldpath

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ttyTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = urlTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.util.url import Url

urls = [
    # No protocol.
    ('testhost',
     'telnet://testhost:23'),
    ('testhost?myvar=testvalue',
     'telnet://testhost:23?myvar=testvalue'),

    # No protocol + empty user.
    ('@testhost',
     'telnet://@testhost:23'),
    ('@testhost?myvar=testvalue',
     'telnet://@testhost:23?myvar=testvalue'),

    # No protocol + user.
    ('user@testhost',
     'telnet://user@testhost:23'),
    ('user:password@testhost',
     'telnet://user:password@testhost:23'),
    ('user:password:password2@testhost',
     'telnet://user:password:password2@testhost:23'),

    # No protocol + empty password 1.
    ('user:@testhost',
     'telnet://user:@testhost:23'),
    ('user::password2@testhost',
     'telnet://user::password2@testhost:23'),
    (':@testhost',
     'telnet://:@testhost:23'),

    # No protocol + empty password 2.
    ('user:password:@testhost',
     'telnet://user:password:@testhost:23'),
    ('user::@testhost',
     'telnet://user::@testhost:23'),
    ('::@testhost',
     'telnet://::@testhost:23'),
    (':password:@testhost',
     'telnet://:password:@testhost:23'),

    # Protocol.
    ('ssh1://testhost',
     'ssh1://testhost:22'),
    ('ssh1://testhost?myvar=testvalue',
     'ssh1://testhost:22?myvar=testvalue'),

    # Protocol + empty user.
    ('ssh://@testhost',
     'ssh://@testhost:22'),
    ('ssh://:password@testhost',
     'ssh://:password@testhost:22'),
    ('ssh://:password:password2@testhost',
     'ssh://:password:password2@testhost:22'),

    # Protocol + user.
    ('ssh://user@testhost',
     'ssh://user@testhost:22'),
    ('ssh://user@testhost?myvar=testvalue',
     'ssh://user@testhost:22?myvar=testvalue'),
    ('ssh://user:password@testhost',
     'ssh://user:password@testhost:22'),
    ('ssh://user:password@testhost?myvar=testvalue',
     'ssh://user:password@testhost:22?myvar=testvalue'),
    ('ssh://user:password@testhost',
     'ssh://user:password@testhost:22'),
    ('ssh://user:password:password2@testhost',
     'ssh://user:password:password2@testhost:22'),

    # Multiple arguments.
    ('ssh://user:password@testhost?myvar=testvalue&myvar2=test%202',
     'ssh://user:password@testhost:22?myvar=testvalue&myvar2=test+2'),
    ('ssh://user:password@testhost?myvar=testvalue&amp;myvar2=test%202',
     'ssh://user:password@testhost:22?myvar=testvalue&myvar2=test+2'),

    # Encoding.
    ('foo://%27M%7B7Zk:%27%2FM%7B7Zyk:C7%26Rt%3Ea@ULM-SZRC1:23',
     'foo://%27M%7B7Zk:%27%2FM%7B7Zyk:C7%26Rt%3Ea@ULM-SZRC1:23'),

    # Pseudo protocol.
    ('pseudo://../my/path',
     'pseudo://../my/path'),
    ('pseudo://../path',
     'pseudo://../path'),
    ('pseudo://filename',
     'pseudo://filename'),
    ('pseudo:///abspath',
     'pseudo:///abspath'),
    ('pseudo:///abs/path',
     'pseudo:///abs/path'),
]

class urlTest(unittest.TestCase):
    CORRELATE = Url

    def testConstructor(self):
        self.assert_(isinstance(Url(), Url))

    def testToString(self):
        for url, expected in urls:
            result = Url.from_string(url)
            error  = 'URL:      ' + url + '\n'
            error += 'Result:   ' + str(result) + '\n'
            error += 'Expected: ' + expected
            self.assert_(isinstance(result, Url))
            self.assert_(result.to_string() == expected, error)

    def testFromString(self):
        for url, expected in urls:
            result = Url.from_string(url)
            error  = 'URL:      ' + url + '\n'
            error += 'Result:   ' + str(result) + '\n'
            error += 'Expected: ' + expected
            self.assert_(isinstance(result, Url))
            self.assert_(str(result) == expected, error)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(urlTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = weakmethodTest
import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.util.weakmethod import ref, WeakMethod, DeadMethodCalled

class TestClass(object):
    def callback(self, *args, **kwargs):
        self.args   = args
        self.kwargs = kwargs

class weakmethodTest(unittest.TestCase):
    CORRELATE = WeakMethod

    def testConstructor(self):
        WeakMethod('foo', lambda x: x)

    def testGetFunction(self):
        # Test with a function.
        f = lambda x: x
        m = ref(f)
        self.assertEqual(m.get_function(), f)
        del f
        self.assertEqual(m.get_function(), None)

        # Test with a method.
        c = TestClass()
        m = ref(c.callback)
        self.assertEqual(m.get_function(), c.callback)
        del c
        self.assertEqual(m.get_function(), None)

    def testIsalive(self):
        # Test with a function.
        f = lambda x: x
        m = ref(f)
        self.assertEqual(m.isalive(), True)
        del f
        self.assertEqual(m.isalive(), False)

        # Test with a method.
        c = TestClass()
        m = ref(c.callback)
        self.assertEqual(m.isalive(), True)
        del c
        self.assertEqual(m.isalive(), False)

    def testCall(self):
        # Test with a function.
        def function(data, *args, **kwargs):
            data['args']   = args
            data['kwargs'] = kwargs
        d = {}
        f = ref(function)
        f(d, 'one', two = True)
        self.assertEqual(d, {'args': ('one',), 'kwargs': {'two': True}})
        del function

        # Test with a method.
        d = {}
        c = TestClass()
        m = ref(c.callback)
        m('one', two = True)
        self.assertEqual(c.args, ('one',))
        self.assertEqual(c.kwargs, {'two': True})

        del c
        self.assertRaises(DeadMethodCalled, m)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(weakmethodTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = JobTest
import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from multiprocessing import Pipe
from Exscript.workqueue.Job import Thread, Process, Job
from tempfile import NamedTemporaryFile
from cPickle import dumps, loads

def do_nothing(job):
    pass

class ThreadTest(unittest.TestCase):
    CORRELATE = Thread

    def testConstructor(self):
        job = self.CORRELATE(1, do_nothing, 'myaction', None)
        self.assertEqual(do_nothing, job.function)

    def testRun(self):
        job = self.CORRELATE(1, do_nothing, 'myaction', None)
        to_child, to_self = Pipe()
        job.start(to_self)
        response = to_child.recv()
        while job.is_alive():
            pass
        job.join()
        self.assertEqual(response, '')

    def testStart(self):
        pass # See testRun()

class ProcessTest(ThreadTest):
    CORRELATE = Process

class JobTest(unittest.TestCase):
    def testConstructor(self):
        job = Job(do_nothing, 'myaction', 1, 'foo')
        self.assertEqual(job.name, 'myaction')
        self.assertEqual(job.times, 1)
        self.assertEqual(job.func, do_nothing)
        self.assertEqual(job.data, 'foo')
        self.assertEqual(job.child, None)

    def testPickle(self):
        job1 = Job(do_nothing, 'myaction', 1, None)
        data = dumps(job1, -1)
        job2 = loads(data)
        self.assertEqual(job1.name, job2.name)

def suite():
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(ThreadTest)
    suite2 = loader.loadTestsFromTestCase(ProcessTest)
    suite3 = loader.loadTestsFromTestCase(JobTest)
    return unittest.TestSuite((suite1, suite2, suite3))
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = MainLoopTest
import sys, unittest, re, os.path, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import MainLoop
from Exscript.workqueue.Pipeline import Pipeline
from Exscript.workqueue.Job import Process

class MainLoopTest(unittest.TestCase):
    CORRELATE = MainLoop

    def setUp(self):
        pass

    def testMainLoop(self):
        lock = threading.Lock()
        data = {'sum': 0, 'randsum': 0}
        ml   = MainLoop.MainLoop(Pipeline(), Process)
        nop  = lambda x: None

        for i in range(12345):
            ml.enqueue(nop, name = 'test', times = 1, data = None)

        self.assertEqual(0, data['sum'])

        # Note: Further testing is done in WorkQueueTest.py

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MainLoopTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = PipelineTest
import sys, unittest, re, os.path, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import time
from threading import Thread
from multiprocessing import Value
from Exscript.workqueue import Pipeline

class PipelineTest(unittest.TestCase):
    CORRELATE = Pipeline

    def setUp(self):
        self.pipeline = Pipeline()

    def testConstructor(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        pipeline = Pipeline(max_working = 10)
        self.assertEqual(pipeline.get_max_working(), 10)

    def testLen(self):
        self.assertEqual(len(self.pipeline), 0)

    def testContains(self):
        item1 = object()
        item2 = object()
        self.assert_(item1 not in self.pipeline)
        self.assert_(item2 not in self.pipeline)

        self.pipeline.append(item1)
        self.assert_(item1 in self.pipeline)
        self.assert_(item2 not in self.pipeline)

        self.pipeline.append(item2)
        self.assert_(item1 in self.pipeline)
        self.assert_(item2 in self.pipeline)

    def testGetFromName(self):
        item1 = object()
        item2 = object()
        self.assertEqual(self.pipeline.get_from_name('foo'), None)

        self.pipeline.append(item1, 'foo')
        self.pipeline.append(item2, 'bar')
        self.assertEqual(self.pipeline.get_from_name('fff'), None)
        self.assertEqual(self.pipeline.get_from_name('foo'), item1)
        self.assertEqual(self.pipeline.get_from_name('bar'), item2)

    def testHasId(self):
        item1 = object()
        item2 = object()
        id1   = 'foo'
        id2   = 'bar'
        self.assertEqual(self.pipeline.has_id(id1), False)
        self.assertEqual(self.pipeline.has_id(id2), False)

        id1 = self.pipeline.append(item1)
        self.assertEqual(self.pipeline.has_id(id1), True)
        self.assertEqual(self.pipeline.has_id(id2), False)

        id2 = self.pipeline.append(item2)
        self.assertEqual(self.pipeline.has_id(id1), True)
        self.assertEqual(self.pipeline.has_id(id2), True)

    def testTaskDone(self):
        self.testNext()

    def testAppend(self):
        self.testContains()

    def testAppendleft(self):
        item1 = object()
        item2 = object()
        item3 = object()
        item4 = object()
        self.assertEqual(self.pipeline.try_next(), None)

        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(self.pipeline.try_next(), item1)

        self.pipeline.appendleft(item3)
        self.assertEqual(self.pipeline.try_next(), item3)

        self.pipeline.appendleft(item4, True)
        self.assertEqual(self.pipeline.try_next(), item4)

    def testPrioritize(self):
        item1 = object()
        item2 = object()
        self.assertEqual(self.pipeline.try_next(), None)

        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(self.pipeline.try_next(), item1)

        self.pipeline.prioritize(item2)
        self.assertEqual(self.pipeline.try_next(), item2)
        self.pipeline.prioritize(item2)
        self.assertEqual(self.pipeline.try_next(), item2)

        self.pipeline.prioritize(item1, True)
        self.assertEqual(self.pipeline.try_next(), item1)
        self.pipeline.prioritize(item1, True)
        self.assertEqual(self.pipeline.try_next(), item1)

    def testClear(self):
        self.testAppendleft()
        self.assertEqual(len(self.pipeline), 4)
        self.pipeline.clear()
        self.assertEqual(len(self.pipeline), 0)

    def testStop(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(len(self.pipeline), 2)

        thread_completed = Value('i', 0)
        class deadlock_until_stop(Thread):
            def run(inner_self):
                self.assertEqual(self.pipeline.next(), item1)
                self.assertEqual(self.pipeline.next(), None) # ***
                thread_completed.value = 1
                self.pipeline.task_done(item1)

        thread = deadlock_until_stop()
        thread.daemon = True
        thread.start()

        time.sleep(0.5) # Hack: Wait until the thread has reached "***"

        self.assertEqual(thread_completed.value, 0)
        self.pipeline.stop()
        thread.join()
        self.assertEqual(thread_completed.value, 1)

    def testStart(self):
        self.testStop()
        self.assertEqual(len(self.pipeline), 1)
        item1 = object()
        self.pipeline.appendleft(item1)
        self.assertEqual(self.pipeline.next(), None)
        self.pipeline.start()
        self.assertEqual(self.pipeline.next(), item1)

    def testPause(self):
        item1 = object()
        self.pipeline.append(item1)
        self.pipeline.pause()

        class complete_all(Thread):
            def run(inner_self):
                while True:
                    task = self.pipeline.next()
                    if task is None:
                        break
                    self.pipeline.task_done(task)

        thread = complete_all()
        thread.daemon = True
        thread.start()

        time.sleep(.2) # hack: wait long enough for the task to complete.
        self.assertEqual(len(self.pipeline), 1) # should not be completed.
        self.pipeline.unpause()
        self.pipeline.wait_all() # now it should not deadlock.

    def testUnpause(self):
        self.testPause()

    def testSleep(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(len(self.pipeline), 2)

        self.assertEqual(self.pipeline.next(), item1)
        self.assertEqual(len(self.pipeline), 2)
        self.pipeline.sleep(item1)
        self.assertEqual(len(self.pipeline), 2)

        # This would normally deadlock if the job were not sleeping,
        # because we have reached the max_working threshold.
        self.assertEqual(self.pipeline.next(), item2)
        self.assertEqual(len(self.pipeline), 2)

        self.pipeline.wake(item1)
        self.assertRaises(Exception, self.pipeline.wake, item2)
        self.assertEqual(len(self.pipeline), 2)

    def testWake(self):
        self.testSleep()

    def testWaitForId(self):
        item1 = object()
        item2 = object()
        id1   = self.pipeline.append(item1)
        id2   = self.pipeline.append(item2)

        item = self.pipeline.next()
        class complete_item(Thread):
            def run(inner_self):
                time.sleep(.1)
                self.pipeline.task_done(item)
        thread = complete_item()
        thread.daemon = True
        thread.start()

        self.assertEqual(len(self.pipeline), 2)
        self.pipeline.wait_for_id(id1) # Must not deadlock.
        self.assertEqual(len(self.pipeline), 1)

    def testWait(self):
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)

        self.assertEqual(len(self.pipeline), 2)
        self.pipeline.wait()
        self.assertEqual(len(self.pipeline), 2)

        item = self.pipeline.next()
        class complete_item(Thread):
            def run(inner_self):
                time.sleep(.1)
                self.pipeline.task_done(item)
        thread = complete_item()
        thread.daemon = True
        thread.start()

        self.pipeline.wait() # Must not deadlock.
        self.assertEqual(len(self.pipeline), 1)

    def testWaitAll(self):
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)

        class complete_all(Thread):
            def run(inner_self):
                while True:
                    task = self.pipeline.next()
                    if task is None:
                        break
                    self.pipeline.task_done(task)
        thread = complete_all()
        thread.daemon = True
        thread.start()

        self.pipeline.wait_all() # Must not deadlock.
        self.assertEqual(len(self.pipeline), 0)

    def testWithLock(self):
        result = self.pipeline.with_lock(lambda p, x: x, 'test')
        self.assertEqual(result, 'test')

    def testSetMaxWorking(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        self.pipeline.set_max_working(2)
        self.assertEqual(self.pipeline.get_max_working(), 2)

    def testGetMaxWorking(self):
        self.testSetMaxWorking()

    def testGetWorking(self):
        item = object()
        self.pipeline.append(item)
        self.assertEqual(self.pipeline.get_working(), [])
        theitem = self.pipeline.next()
        self.assertEqual(self.pipeline.get_working(), [item])
        self.pipeline.task_done(theitem)

    def testTryNext(self):
        pass # used for testing only anyway.

    def testNext(self):
        # Repeat with max_working set to a value larger than the
        # queue length (i.e. no locking).
        self.pipeline.set_max_working(4)
        item1 = object()
        item2 = object()
        item3 = object()
        item4 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.pipeline.appendleft(item3, force = True)
        self.pipeline.appendleft(item4)

        self.assertEqual(self.pipeline.next(), item3)
        self.assertEqual(self.pipeline.next(), item4)
        self.assertEqual(self.pipeline.next(), item1)
        self.assertEqual(self.pipeline.next(), item2)
        self.assert_(item1 in self.pipeline)
        self.assert_(item2 in self.pipeline)
        self.assert_(item3 in self.pipeline)
        self.assert_(item4 in self.pipeline)
        self.assertEqual(len(self.pipeline), 4)
        self.pipeline.clear()
        self.assertEqual(len(self.pipeline), 0)

        # Repeat with max_working = 2.
        self.pipeline.set_max_working(2)
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.pipeline.appendleft(item3, force = True)
        self.pipeline.appendleft(item4)

        self.assertEqual(self.pipeline.next(), item3)
        self.assertEqual(self.pipeline.next(), item4)
        self.assert_(item3 in self.pipeline)
        self.assert_(item4 in self.pipeline)
        self.pipeline.task_done(item4)
        self.assert_(item4 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item1)
        self.assert_(item1 in self.pipeline)
        self.pipeline.task_done(item3)
        self.assert_(item3 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item2)
        self.assert_(item2 in self.pipeline)
        self.pipeline.task_done(item2)
        self.assert_(item2 not in self.pipeline)
        self.pipeline.task_done(item1)
        self.assert_(item1 not in self.pipeline)
        self.assertEqual(len(self.pipeline), 0)

        # Repeat with max_working = 1.
        self.pipeline.set_max_working(1)
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.pipeline.appendleft(item3, force = True)
        self.pipeline.appendleft(item4)

        self.assertEqual(self.pipeline.next(), item3)
        self.assert_(item3 in self.pipeline)
        self.pipeline.task_done(item3)
        self.assert_(item3 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item4)
        self.assert_(item4 in self.pipeline)
        self.pipeline.task_done(item4)
        self.assert_(item4 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item1)
        self.assert_(item1 in self.pipeline)
        self.pipeline.task_done(item1)
        self.assert_(item1 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item2)
        self.assert_(item2 in self.pipeline)
        self.pipeline.task_done(item2)
        self.assert_(item2 not in self.pipeline)
        self.assertEqual(len(self.pipeline), 0)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(PipelineTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = run_suite
../run_suite.py
########NEW FILE########
__FILENAME__ = TaskTest
import sys, unittest, re, os.path, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

warnings.simplefilter('ignore', DeprecationWarning)

from Exscript.workqueue import WorkQueue, Task
from Exscript.workqueue.Job import Thread

class TaskTest(unittest.TestCase):
    CORRELATE = Task

    def setUp(self):
        self.wq = WorkQueue()

    def tearDown(self):
        self.wq.shutdown(True)

    def testConstructor(self):
        task = Task(self.wq)

    def testIsCompleted(self):
        task = Task(self.wq)
        task.add_job_id(123)
        task.wait() # Returns immediately because the id is not known.

    def testWait(self):
        task = Task(self.wq)
        self.assertEqual(task.is_completed(), True)

        job1 = Thread(1, object, 'foo1', None)
        job2 = Thread(2, object, 'foo2', None)
        task.add_job_id(job1.id)
        task.add_job_id(job2.id)
        self.assertEqual(task.is_completed(), False)

        self.wq.job_succeeded_event(job1)
        self.assertEqual(task.is_completed(), False)
        self.wq.job_succeeded_event(job2)
        self.assertEqual(task.is_completed(), True)

    def testAddJobId(self):
        self.testWait()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TaskTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = WorkQueueTest
import sys, unittest, re, os.path, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import random
import time
from multiprocessing import Value, Lock
from Exscript.workqueue import WorkQueue

lock = Lock()

def burn_time(job):
    """
    This function just burns some time using shared data.
    """
    # Manipulate the data.
    with lock:
        job.data.value += 1
    time.sleep(random.random())

nop = lambda x: None

class WorkQueueTest(unittest.TestCase):
    CORRELATE = WorkQueue

    def setUp(self):
        self.wq = WorkQueue()

    def testConstructor(self):
        self.assertEqual(1, self.wq.get_max_threads())
        self.assertEqual(0, self.wq.debug)

    def testSetDebug(self):
        self.assertEqual(0, self.wq.debug)
        self.wq.set_debug(2)
        self.assertEqual(2, self.wq.debug)

    def testGetMaxThreads(self):
        self.assertEqual(1, self.wq.get_max_threads())
        self.wq.set_max_threads(9)
        self.assertEqual(9, self.wq.get_max_threads())

    def testSetMaxThreads(self):
        self.testGetMaxThreads()

    def testEnqueue(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assert_(isinstance(id, str))
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Enqueue a larger number of actions.
        self.assert_(self.wq.is_paused())
        data = Value('i', 0)  # an int in shared memory
        for i in range(222):
            self.wq.enqueue(burn_time, data = data)
        self.assertEqual(222, self.wq.get_length())

        # Run them, using 50 threads in parallel.
        self.wq.set_max_threads(50)
        self.wq.unpause()
        self.wq.wait_until_done()

        # Check whether each has run successfully.
        self.assertEqual(0,   self.wq.get_length())
        self.assertEqual(222, data.value)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

    def testEnqueueOrIgnore(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue_or_ignore(nop, 'one')
        self.assertEqual(1, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.enqueue_or_ignore(nop, 'two')
        self.assertEqual(2, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.enqueue_or_ignore(nop, 'one')
        self.assertEqual(2, self.wq.get_length())
        self.assertEqual(id, None)
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Stress testing from testEnqueue() not repeated here.

    def testPriorityEnqueue(self):
        # Well, this test sucks.
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.priority_enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.priority_enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assert_(isinstance(id, str))

    def testPriorityEnqueueOrRaise(self):
        self.assertEqual(0, self.wq.get_length())

        self.wq.pause()
        id = self.wq.priority_enqueue_or_raise(nop, 'foo')
        self.assertEqual(1, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.priority_enqueue_or_raise(nop, 'bar')
        self.assertEqual(2, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.priority_enqueue_or_raise(nop, 'foo')
        self.assertEqual(2, self.wq.get_length())
        self.assertEqual(id, None)

    def testPause(self):
        pass # See testEnqueue()

    def testWaitFor(self):
        self.wq.pause()
        ids = [self.wq.enqueue(nop) for a in range(4)]
        self.assertEqual(4, self.wq.get_length())
        self.wq.unpause()
        self.wq.wait_for(ids[0])
        self.assert_(self.wq.get_length() < 4)
        for id in ids:
            self.wq.wait_for(id)
        self.assertEqual(0, self.wq.get_length())

    def testUnpause(self):
        pass # See testEnqueue()

    def testWaitUntilDone(self):
        pass # See testEnqueue()

    def testShutdown(self):
        pass # See testEnqueue()

    def testDestroy(self):
        self.wq.pause()
        self.assertEqual(0, self.wq.get_length())
        id = self.wq.enqueue(nop)
        self.assertEqual(1, self.wq.get_length())
        self.assert_(isinstance(id, str))
        id = self.wq.enqueue(nop)
        self.assertEqual(2, self.wq.get_length())
        self.assert_(isinstance(id, str))
        self.wq.destroy()
        self.assertEqual(0, self.wq.get_length())

    def testIsPaused(self):
        self.failIf(self.wq.is_paused())
        self.wq.pause()
        self.assert_(self.wq.is_paused())
        self.wq.unpause()
        self.failIf(self.wq.is_paused())
        self.wq.pause()
        self.assert_(self.wq.is_paused())

    def testGetRunningJobs(self):
        def function(job):
            self.assertEqual(self.wq.get_running_jobs(), [job])
        self.assertEqual(self.wq.get_running_jobs(), [])
        self.wq.enqueue(function)
        self.wq.shutdown(True)
        self.assertEqual(self.wq.get_running_jobs(), [])

    def testGetLength(self):
        pass # See testEnqueue()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkQueueTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = OrderDBTest
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile          import NamedTemporaryFile
from getpass           import getuser
from sqlalchemy        import create_engine
from Exscriptd.Order   import Order
from Exscriptd.Task    import Task
from Exscriptd.OrderDB import OrderDB

def testfunc(foo):
    pass

class OrderDBTest(unittest.TestCase):
    CORRELATE = OrderDB

    def setUp(self):
        from sqlalchemy.pool import NullPool
        self.dbfile = NamedTemporaryFile()
        self.engine = create_engine('sqlite:///' + self.dbfile.name,
                                    poolclass = NullPool)
        self.db     = OrderDB(self.engine)

    def tearDown(self):
        self.dbfile.close()

    def testConstructor(self):
        db = OrderDB(self.engine)

    def testInstall(self):
        self.db.install()

    def testUninstall(self):
        self.testInstall()
        self.db.uninstall()
        self.db.install()

    def testClearDatabase(self):
        self.testAddOrder()
        self.db.clear_database()

        orders = self.db.get_orders()
        self.assert_(len(orders) == 0)

    def testDebug(self):
        self.assert_(not self.engine.echo)
        self.db.debug()
        self.assert_(self.engine.echo)
        self.db.debug(False)
        self.assert_(not self.engine.echo)

    def testSetTablePrefix(self):
        self.assertEqual(self.db.get_table_prefix(), 'exscriptd_')
        self.db.set_table_prefix('foo')
        self.assertEqual(self.db.get_table_prefix(), 'foo')
        self.db.install()
        self.db.uninstall()

    def testGetTablePrefix(self):
        self.testSetTablePrefix()

    def testAddOrder(self):
        self.testInstall()

        order1 = Order('fooservice')
        self.assertEqual(order1.get_created_by(), getuser())
        self.assertEqual(order1.get_description(), '')
        self.assertEqual(order1.get_progress(), .0)
        order1.created_by = 'this test'
        order1.set_description('my description')
        self.assertEqual(order1.get_created_by(), 'this test')
        self.assertEqual(order1.get_description(), 'my description')

        # Save the order.
        self.assert_(order1.get_id() is None)
        self.db.add_order(order1)
        order_id = order1.get_id()
        self.assert_(order_id is not None)

        def assert_progress(value):
            progress = self.db.get_order_progress_from_id(order_id)
            theorder = self.db.get_order(id = order_id)
            self.assertEqual(progress, value)
            self.assertEqual(theorder.get_progress(), value)

        # Check that the order is stored.
        order = self.db.get_order(id = order_id)
        self.assertEqual(order.get_id(), order_id)
        self.assertEqual(order.get_created_by(), 'this test')
        self.assertEqual(order.get_closed_timestamp(), None)
        self.assertEqual(order.get_description(), 'my description')
        assert_progress(.0)

        # Check that an order that has no tasks show progress 100% when
        # it is closed.
        order.close()
        self.db.save_order(order)
        assert_progress(1.0)

        # Add some sub-tasks.
        task1 = Task(order.id, 'my test task')
        self.db.save_task(task1)
        assert_progress(.0)

        task2 = Task(order.id, 'another test task')
        self.db.save_task(task2)
        assert_progress(.0)

        # Change the progress, re-check.
        task1.set_progress(.5)
        self.db.save_task(task1)
        assert_progress(.25)

        task2.set_progress(.5)
        self.db.save_task(task2)
        assert_progress(.5)

        task1.set_progress(1.0)
        self.db.save_task(task1)
        assert_progress(.75)

        task2.set_progress(1.0)
        self.db.save_task(task2)
        assert_progress(1.0)

    def testSaveOrder(self):
        self.testInstall()

        order1 = Order('fooservice')

        self.assert_(order1.get_id() is None)
        self.db.save_order(order1)

        # Check that the order is stored.
        order2 = self.db.get_order(id = order1.get_id())
        self.assertEqual(order1.get_id(), order2.get_id())

    def testGetOrderProgressFromId(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)
        id = order.get_id()
        self.assertEqual(self.db.get_order_progress_from_id(id), .0)

        order.close()
        self.db.save_order(order)
        self.assertEqual(self.db.get_order_progress_from_id(id), 1.0)

        task1 = Task(order.id, 'my test task')
        self.db.save_task(task1)
        self.assertEqual(self.db.get_order_progress_from_id(id), .0)

        task2 = Task(order.id, 'another test task')
        self.db.save_task(task2)
        self.assertEqual(self.db.get_order_progress_from_id(id), .0)

        task1.set_progress(.5)
        self.db.save_task(task1)
        self.assertEqual(self.db.get_order_progress_from_id(id), .25)
        task2.set_progress(.5)
        self.db.save_task(task2)
        self.assertEqual(self.db.get_order_progress_from_id(id), .5)
        task1.set_progress(1.0)
        self.db.save_task(task1)
        self.assertEqual(self.db.get_order_progress_from_id(id), .75)
        task2.set_progress(1.0)
        self.db.save_task(task2)
        self.assertEqual(self.db.get_order_progress_from_id(id), 1.0)

    def testGetOrder(self):
        self.testAddOrder()

    def testCountOrders(self):
        self.testInstall()
        self.assertEqual(self.db.count_orders(id = 1), 0)
        self.assertEqual(self.db.count_orders(), 0)
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 1)
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 2)
        self.assertEqual(self.db.count_orders(id = 1), 1)

    def testGetOrders(self):
        self.testAddOrder()
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 2)
        orders = self.db.get_orders()
        self.assertEqual(len(orders), 2)

    def testCloseOpenOrders(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.add_order(order)
        order = self.db.get_orders()[0]
        self.assertEqual(order.closed, None)

        self.db.close_open_orders()
        order = self.db.get_orders()[0]
        self.failIfEqual(order.get_closed_timestamp(), None)

    def testSaveTask(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task = Task(order.id, 'my test task')
        self.assert_(task.id is None)
        self.db.save_task(task)
        self.assert_(task.id is not None)

    def testGetTask(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task1 = Task(order.id, 'my test task')
        self.db.save_task(task1)
        loaded_task = self.db.get_task()
        self.assertEqual(task1.id, loaded_task.id)

        task2 = Task(order.id, 'another test task')
        self.db.save_task(task2)
        self.assertRaises(IndexError, self.db.get_task)

    def testGetTasks(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task1 = Task(order.id, 'my test task')
        task2 = Task(order.id, 'another test task')
        self.db.save_task(task1)
        self.db.save_task(task2)

        id_list1 = sorted([task1.id, task2.id])
        id_list2 = sorted([task.id for task in self.db.get_tasks()])
        self.assertEqual(id_list1, id_list2)

        tasks    = self.db.get_tasks(order_id = order.id)
        id_list2 = sorted([task.id for task in tasks])
        self.assertEqual(id_list1, id_list2)

        id_list2 = [task.id for task in self.db.get_tasks(order_id = 2)]
        self.assertEqual([], id_list2)

    def testCountTasks(self):
        self.testInstall()
        self.assertEqual(self.db.count_tasks(), 0)
        self.testSaveTask()
        self.assertEqual(self.db.count_tasks(), 1)
        self.testSaveTask()
        self.assertEqual(self.db.count_tasks(), 2)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OrderDBTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = test
print "Hello Python-Service!"

def run(conn, order):
    """
    Called whenever a host that is associated with an order was contacted.
    """
    hostname = conn.get_host().get_name()
    print "Hello from python-service run()!", __service__.name, order.id, hostname

def enter(order):
    """
    Called whenever a new order was received.
    If this funtion returns True the order is accepted. Otherwise,
    the order is rejected.
    """
    print "Hello from python-service enter()!", __service__.name, order.id
    callback = bind(run, order)
    __service__.enqueue_hosts(order, order.get_hosts(), callback)
    __service__.set_order_status(order, 'queued')
    return True

########NEW FILE########
__FILENAME__ = run_suite
../Exscript/run_suite.py
########NEW FILE########
__FILENAME__ = pseudodev
commands = (
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
(r'.*', ''),
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
('ls -1.*', """
hello
testme
"""),

('ls -l .+', lambda x: '\n' + x)
)

########NEW FILE########
__FILENAME__ = pseudodev
commands = (
('ls -1.*', """
hello
testme
"""),

('ls -l .+', lambda x: x)
)

########NEW FILE########
__FILENAME__ = LoginWindowTest
from getpass    import getuser
from Exscript   import Account
from TkExscript import LoginWindow

def on_start(window):
    account = window.get_account()
    print "Username:",      account.get_name()
    print "Password:",      account.get_password()
    print "Authorization:", account.get_authorization_password()
    window.quit()

account = Account(getuser())
LoginWindow(account,
            show_authorization = True,
            on_start = on_start).mainloop()

########NEW FILE########
__FILENAME__ = MailWindowTest
from Exscript.util.mail import Mail
from TkExscript         import MailWindow
mail = Mail(subject = 'Test me', body = 'hello world')
MailWindow(mail).mainloop()

########NEW FILE########
__FILENAME__ = QueueWindowTest
import time, Exscript.util.sigintcatcher
from Exscript                import Queue, Account
from Exscript.util.decorator import bind
from TkExscript              import QueueWindow

def do_something(conn, wait):
    conn.connect()
    conn.authenticate()
    for i in range(100):
        conn.execute('test%d' % i)
        time.sleep(wait)
    conn.close()

queue = Queue(max_threads = 4, verbose = 0)
queue.add_account(Account('test', 'test'))
window = QueueWindow(queue)
queue.run('dummy://dummy1', bind(do_something, .02))
queue.run('dummy://dummy2', bind(do_something, .2))
queue.run('dummy://dummy3', bind(do_something, .3))
window.mainloop()
queue.shutdown()

########NEW FILE########
