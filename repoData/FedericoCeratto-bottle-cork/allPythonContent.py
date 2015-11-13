__FILENAME__ = backends
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Backends API - used to make backends available for importing
#
from json_backend import JsonBackend
from mongodb_backend import MongoDBBackend
from sqlalchemy_backend import SqlAlchemyBackend
from sqlite_backend import SQLiteBackend

########NEW FILE########
__FILENAME__ = base_backend
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Base Backend.
#

class BackendIOException(Exception):
    """Generic Backend I/O Exception"""
    pass

def ni(*args, **kwargs):
    raise NotImplementedError

class Backend(object):
    """Base Backend class - to be subclassed by real backends."""
    save_users = ni
    save_roles = ni
    save_pending_registrations = ni

class Table(object):
    """Base Table class - to be subclassed by real backends."""
    __len__ = ni
    __contains__ = ni
    __setitem__ = ni
    __getitem__ = ni
    __iter__ = ni
    iteritems = ni


########NEW FILE########
__FILENAME__ = cork
#!/usr/bin/env python
#
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
#
# This package is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from base64 import b64encode, b64decode
from beaker import crypto
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging import getLogger
from smtplib import SMTP, SMTP_SSL
from threading import Thread
from time import time
import bottle
import os
import re
import uuid

try:
    import scrypt
    scrypt_available = True
except ImportError:  # pragma: no cover
    scrypt_available = False

from backends import JsonBackend

log = getLogger(__name__)


class AAAException(Exception):
    """Generic Authentication/Authorization Exception"""
    pass

class AuthException(AAAException):
    """Authentication Exception: incorrect username/password pair"""
    pass


class Cork(object):

    def __init__(self, directory=None, backend=None, email_sender=None,
        initialize=False, session_domain=None, smtp_server=None,
        smtp_url='localhost'):
        """Auth/Authorization/Accounting class

        :param directory: configuration directory
        :type directory: str.
        :param users_fname: users filename (without .json), defaults to 'users'
        :type users_fname: str.
        :param roles_fname: roles filename (without .json), defaults to 'roles'
        :type roles_fname: str.
        """
        if smtp_server:
            smtp_url = smtp_server
        self.mailer = Mailer(email_sender, smtp_url)
        self.password_reset_timeout = 3600 * 24
        self.session_domain = session_domain
        self.preferred_hashing_algorithm = 'PBKDF2'

        # Setup JsonBackend by default for backward compatibility.
        if backend is None:
            self._store = JsonBackend(directory, users_fname='users',
                roles_fname='roles', pending_reg_fname='register',
                initialize=initialize)

        else:
            self._store = backend

    def login(self, username, password, success_redirect=None,
        fail_redirect=None):
        """Check login credentials for an existing user.
        Optionally redirect the user to another page (typically /login)

        :param username: username
        :type username: str.
        :param password: cleartext password
        :type password: str.
        :param success_redirect: redirect authorized users (optional)
        :type success_redirect: str.
        :param fail_redirect: redirect unauthorized users (optional)
        :type fail_redirect: str.
        :returns: True for successful logins, else False
        """
        assert isinstance(username, str), "the username must be a string"
        assert isinstance(password, str), "the password must be a string"

        if username in self._store.users:
            if self._verify_password(username, password,
                    self._store.users[username]['hash']):
                # Setup session data
                self._setup_cookie(username)
                self._store.users[username]['last_login'] = str(datetime.utcnow())
                self._store.save_users()
                if success_redirect:
                    bottle.redirect(success_redirect)
                return True

        if fail_redirect:
            bottle.redirect(fail_redirect)

        return False

    def logout(self, success_redirect='/login', fail_redirect='/login'):
        """Log the user out, remove cookie

        :param success_redirect: redirect the user after logging out
        :type success_redirect: str.
        :param fail_redirect: redirect the user if it is not logged in
        :type fail_redirect: str.
        """
        try:
            session = self._beaker_session
            session.delete()
        except Exception, e:
            log.debug("Exception %s while logging out." % repr(e))
            bottle.redirect(fail_redirect)

        bottle.redirect(success_redirect)

    def require(self, username=None, role=None, fixed_role=False,
        fail_redirect=None):
        """Ensure the user is logged in has the required role (or higher).
        Optionally redirect the user to another page (typically /login)
        If both `username` and `role` are specified, both conditions need to be
        satisfied.
        If none is specified, any authenticated user will be authorized.
        By default, any role with higher level than `role` will be authorized;
        set fixed_role=True to prevent this.

        :param username: username (optional)
        :type username: str.
        :param role: role
        :type role: str.
        :param fixed_role: require user role to match `role` strictly
        :type fixed_role: bool.
        :param redirect: redirect unauthorized users (optional)
        :type redirect: str.
        """
        # Parameter validation
        if username is not None:
            if username not in self._store.users:
                raise AAAException("Nonexistent user")

        if fixed_role and role is None:
            raise AAAException(
                """A role must be specified if fixed_role has been set""")

        if role is not None and role not in self._store.roles:
            raise AAAException("Role not found")

        # Authentication
        try:
            cu = self.current_user
        except AAAException:
            if fail_redirect is None:
                raise AuthException("Unauthenticated user")
            else:
                bottle.redirect(fail_redirect)

        # Authorization
        if cu.role not in self._store.roles:
            raise AAAException("Role not found for the current user")

        if username is not None:
            if username != self.current_user.username:
                if fail_redirect is None:
                    raise AuthException("Unauthorized access: incorrect"
                        " username")
                else:
                    bottle.redirect(fail_redirect)

        if fixed_role:
            if role == self.current_user.role:
                return

            if fail_redirect is None:
                raise AuthException("Unauthorized access: incorrect role")
            else:
                bottle.redirect(fail_redirect)

        else:
            if role is not None:
                # Any role with higher level is allowed
                current_lvl = self._store.roles[self.current_user.role]
                threshold_lvl = self._store.roles[role]
                if current_lvl >= threshold_lvl:
                    return

                if fail_redirect is None:
                    raise AuthException("Unauthorized access: ")
                else:
                    bottle.redirect(fail_redirect)

        return

    def create_role(self, role, level):
        """Create a new role.

        :param role: role name
        :type role: str.
        :param level: role level (0=lowest, 100=admin)
        :type level: int.
        :raises: AuthException on errors
        """
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized to ")
        if role in self._store.roles:
            raise AAAException("The role is already existing")
        try:
            int(level)
        except ValueError:
            raise AAAException("The level must be numeric.")
        self._store.roles[role] = level
        self._store.save_roles()

    def delete_role(self, role):
        """Deleta a role.

        :param role: role name
        :type role: str.
        :raises: AuthException on errors
        """
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized to ")
        if role not in self._store.roles:
            raise AAAException("Nonexistent role.")
        self._store.roles.pop(role)
        self._store.save_roles()

    def list_roles(self):
        """List roles.

        :returns: (role, role_level) generator (sorted by role)
        """
        for role in sorted(self._store.roles):
            yield (role, self._store.roles[role])

    def create_user(self, username, role, password, email_addr=None,
        description=None):
        """Create a new user account.
        This method is available to users with level>=100

        :param username: username
        :type username: str.
        :param role: role
        :type role: str.
        :param password: cleartext password
        :type password: str.
        :param email_addr: email address (optional)
        :type email_addr: str.
        :param description: description (free form)
        :type description: str.
        :raises: AuthException on errors
        """
        assert username, "Username must be provided."
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized" \
                " to create users.")

        if username in self._store.users:
            raise AAAException("User is already existing.")
        if role not in self._store.roles:
            raise AAAException("Nonexistent user role.")
        tstamp = str(datetime.utcnow())
        self._store.users[username] = {
            'role': role,
            'hash': self._hash(username, password),
            'email_addr': email_addr,
            'desc': description,
            'creation_date': tstamp,
            'last_login': tstamp
        }
        self._store.save_users()

    def delete_user(self, username):
        """Delete a user account.
        This method is available to users with level>=100

        :param username: username
        :type username: str.
        :raises: Exceptions on errors
        """
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized to ")
        if username not in self._store.users:
            raise AAAException("Nonexistent user.")
        self.user(username).delete()

    def list_users(self):
        """List users.

        :return: (username, role, email_addr, description) generator (sorted by
            username)
        """
        for un in sorted(self._store.users):
            d = self._store.users[un]
            yield (un, d['role'], d['email_addr'], d['desc'])

    @property
    def current_user(self):
        """Current autenticated user

        :returns: User() instance, if authenticated
        :raises: AuthException otherwise
        """
        session = self._beaker_session
        username = session.get('username', None)
        if username is None:
            raise AuthException("Unauthenticated user")
        if username is not None and username in self._store.users:
            return User(username, self, session=session)
        raise AuthException("Unknown user: %s" % username)

    @property
    def user_is_anonymous(self):
        """Check if the current user is anonymous.

        :returns: True if the user is anonymous, False otherwise
        :raises: AuthException if the session username is unknown
        """
        try:
            username = self._beaker_session['username']
        except KeyError:
            return True

        if username not in self._store.users:
            raise AuthException("Unknown user: %s" % username)

        return False

    def user(self, username):
        """Existing user

        :returns: User() instance if the user exist, None otherwise
        """
        if username is not None and username in self._store.users:
            return User(username, self)
        return None

    def register(self, username, password, email_addr, role='user',
        max_level=50, subject="Signup confirmation",
        email_template='views/registration_email.tpl',
        description=None):
        """Register a new user account. An email with a registration validation
        is sent to the user.
        WARNING: this method is available to unauthenticated users

        :param username: username
        :type username: str.
        :param password: cleartext password
        :type password: str.
        :param role: role (optional), defaults to 'user'
        :type role: str.
        :param max_level: maximum role level (optional), defaults to 50
        :type max_level: int.
        :param email_addr: email address
        :type email_addr: str.
        :param subject: email subject
        :type subject: str.
        :param email_template: email template filename
        :type email_template: str.
        :param description: description (free form)
        :type description: str.
        :raises: AssertError or AAAException on errors
        """
        assert username, "Username must be provided."
        assert password, "A password must be provided."
        assert email_addr, "An email address must be provided."
        if username in self._store.users:
            raise AAAException("User is already existing.")
        if role not in self._store.roles:
            raise AAAException("Nonexistent role")
        if self._store.roles[role] > max_level:
            raise AAAException("Unauthorized role")

        registration_code = uuid.uuid4().hex
        creation_date = str(datetime.utcnow())

        # send registration email
        email_text = bottle.template(email_template,
            username=username,
            email_addr=email_addr,
            role=role,
            creation_date=creation_date,
            registration_code=registration_code
        )
        self.mailer.send_email(email_addr, subject, email_text)

        # store pending registration
        self._store.pending_registrations[registration_code] = {
            'username': username,
            'role': role,
            'hash': self._hash(username, password),
            'email_addr': email_addr,
            'desc': description,
            'creation_date': creation_date,
        }
        self._store.save_pending_registrations()

    def validate_registration(self, registration_code):
        """Validate pending account registration, create a new account if
        successful.

        :param registration_code: registration code
        :type registration_code: str.
        """
        try:
            data = self._store.pending_registrations.pop(registration_code)
        except KeyError:
            raise AuthException("Invalid registration code.")

        username = data['username']
        if username in self._store.users:
            raise AAAException("User is already existing.")

        # the user data is moved from pending_registrations to _users
        self._store.users[username] = {
            'role': data['role'],
            'hash': data['hash'],
            'email_addr': data['email_addr'],
            'desc': data['desc'],
            'creation_date': data['creation_date'],
            'last_login': str(datetime.utcnow())
        }
        self._store.save_users()

    def send_password_reset_email(self, username=None, email_addr=None,
        subject="Password reset confirmation",
        email_template='views/password_reset_email'):
        """Email the user with a link to reset his/her password
        If only one parameter is passed, fetch the other from the users
        database. If both are passed they will be matched against the users
        database as a security check.

        :param username: username
        :type username: str.
        :param email_addr: email address
        :type email_addr: str.
        :param subject: email subject
        :type subject: str.
        :param email_template: email template filename
        :type email_template: str.
        :raises: AAAException on missing username or email_addr,
            AuthException on incorrect username/email_addr pair
        """
        if username is None:
            if email_addr is None:
                raise AAAException("At least `username` or `email_addr` must" \
                    " be specified.")

            # only email_addr is specified: fetch the username
            for k, v in self._store.users.iteritems():
                if v['email_addr'] == email_addr:
                    username = k
                    break
            else:    
                raise AAAException("Email address not found.")

        else:  # username is provided
            if username not in self._store.users:
                raise AAAException("Nonexistent user.")
            if email_addr is None:
                email_addr = self._store.users[username].get('email_addr', None)
                if not email_addr:
                    raise AAAException("Email address not available.")
            else:
                # both username and email_addr are provided: check them
                stored_email_addr = self._store.users[username]['email_addr']
                if email_addr != stored_email_addr:
                    raise AuthException("Username/email address pair not found.")

        # generate a reset_code token
        reset_code = self._reset_code(username, email_addr)

        # send reset email
        email_text = bottle.template(email_template,
            username=username,
            email_addr=email_addr,
            reset_code=reset_code
        )
        self.mailer.send_email(email_addr, subject, email_text)

    def reset_password(self, reset_code, password):
        """Validate reset_code and update the account password
        The username is extracted from the reset_code token

        :param reset_code: reset token
        :type reset_code: str.
        :param password: new password
        :type password: str.
        :raises: AuthException for invalid reset tokens, AAAException
        """
        try:
            reset_code = b64decode(reset_code)
            username, email_addr, tstamp, h = reset_code.split(':', 3)
            tstamp = int(tstamp)
        except (TypeError, ValueError):
            raise AuthException("Invalid reset code.")
        if time() - tstamp > self.password_reset_timeout:
            raise AuthException("Expired reset code.")
        if not self._verify_password(username, email_addr, h):
            raise AuthException("Invalid reset code.")
        user = self.user(username)
        if user is None:
            raise AAAException("Nonexistent user.")
        user.update(pwd=password)

    def make_auth_decorator(self, username=None, role=None, fixed_role=False, fail_redirect='/login'):
        '''
        Create a decorator to be used for authentication and authorization

        :param username: A resource can be protected for a specific user
        :param role: Minimum role level required for authorization
        :param fixed_role: Only this role gets authorized
        :param fail_redirect: The URL to redirect to if a login is required.
        '''
        session_manager = self
        def auth_require(username=username, role=role, fixed_role=fixed_role,
                         fail_redirect=fail_redirect):
            def decorator(func):
                import functools
                @functools.wraps(func)
                def wrapper(*a, **ka):
                    session_manager.require(username=username, role=role, fixed_role=fixed_role,
                        fail_redirect=fail_redirect)
                    return func(*a, **ka)
                return wrapper
            return decorator
        return(auth_require)


    ## Private methods

    @property
    def _beaker_session(self):
        """Get Beaker session"""
        return bottle.request.environ.get('beaker.session')

    def _setup_cookie(self, username):
        """Setup cookie for a user that just logged in"""
        session = self._beaker_session
        session['username'] = username
        if self.session_domain is not None:
            session.domain = self.session_domain
        session.save()

    def _hash(self, username, pwd, salt=None, algo=None):
        """Hash username and password, generating salt value if required
        """
        if algo is None:
            algo = self.preferred_hashing_algorithm

        if algo == 'PBKDF2':
            return self._hash_pbkdf2(username, pwd, salt=salt)

        if algo == 'scrypt':
            return self._hash_scrypt(username, pwd, salt=salt)

        raise RuntimeError("Unknown hashing algorithm requested: %s" % algo)

    @staticmethod
    def _hash_scrypt(username, pwd, salt=None):
        """Hash username and password, generating salt value if required
        Use scrypt.

        :returns: base-64 encoded str.
        """
        if not scrypt_available:
            raise Exception("scrypt.hash required."
                " Please install the scrypt library.")

        if salt is None:
            salt = os.urandom(32)

        assert len(salt) == 32, "Incorrect salt length"

        cleartext = "%s\0%s" % (username, pwd)
        h = scrypt.hash(cleartext, salt)

        # 's' for scrypt
        return b64encode('s' + salt + h)

    @staticmethod
    def _hash_pbkdf2(username, pwd, salt=None):
        """Hash username and password, generating salt value if required
        Use PBKDF2 from Beaker

        :returns: base-64 encoded str.
        """
        if salt is None:
            salt = os.urandom(32)
        assert len(salt) == 32, "Incorrect salt length"

        cleartext = "%s\0%s" % (username, pwd)
        h = crypto.generateCryptoKeys(cleartext, salt, 10)
        if len(h) != 32:
            raise RuntimeError("The PBKDF2 hash is %d bytes long instead"
                "of 32. The pycrypto library might be missing." % len(h))

        # 'p' for PBKDF2
        return b64encode('p' + salt + h)

    def _verify_password(self, username, pwd, salted_hash):
        """Verity username/password pair against a salted hash

        :returns: bool
        """
        decoded = b64decode(salted_hash)
        hash_type = decoded[0]
        salt = decoded[1:33]

        if hash_type == 'p':  # PBKDF2
            h = self._hash_pbkdf2(username, pwd, salt)
            return salted_hash == h

        if hash_type == 's':  # scrypt
            h = self._hash_scrypt(username, pwd, salt)
            return salted_hash == h

        raise RuntimeError("Unknown hashing algorithm: %s" % hash_type)

    def _purge_expired_registrations(self, exp_time=96):
        """Purge expired registration requests.

        :param exp_time: expiration time (hours)
        :type exp_time: float.
        """
        for uuid, data in self._store.pending_registrations.items():
            creation = datetime.strptime(data['creation_date'],
                "%Y-%m-%d %H:%M:%S.%f")
            now = datetime.utcnow()
            maxdelta = timedelta(hours=exp_time)
            if now - creation > maxdelta:
                self._store.pending_registrations.pop(uuid)

    def _reset_code(self, username, email_addr):
        """generate a reset_code token

        :param username: username
        :type username: str.
        :param email_addr: email address
        :type email_addr: str.
        :returns: Base-64 encoded token
        """
        h = self._hash(username, email_addr)
        t = "%d" % time()
        reset_code = ':'.join((username, email_addr, t, h))
        return b64encode(reset_code)


class User(object):

    def __init__(self, username, cork_obj, session=None):
        """Represent an authenticated user, exposing useful attributes:
        username, role, level, description, email_addr, session_creation_time,
        session_accessed_time, session_id. The session-related attributes are
        available for the current user only.

        :param username: username
        :type username: str.
        :param cork_obj: instance of :class:`Cork`
        """
        self._cork = cork_obj
        assert username in self._cork._store.users, "Unknown user"
        self.username = username
        user_data = self._cork._store.users[username]
        self.role = user_data['role']
        self.description = user_data['desc']
        self.email_addr = user_data['email_addr']
        self.level = self._cork._store.roles[self.role]

        if session is not None:
            try:
                self.session_creation_time = session['_creation_time']
                self.session_accessed_time = session['_accessed_time']
                self.session_id = session['_id']
            except:
                pass

    def update(self, role=None, pwd=None, email_addr=None):
        """Update an user account data

        :param role: change user role, if specified
        :type role: str.
        :param pwd: change user password, if specified
        :type pwd: str.
        :param email_addr: change user email address, if specified
        :type email_addr: str.
        :raises: AAAException on nonexistent user or role.
        """
        username = self.username
        if username not in self._cork._store.users:
            raise AAAException("User does not exist.")

        if role is not None:
            if role not in self._cork._store.roles:
                raise AAAException("Nonexistent role.")

            self._cork._store.users[username]['role'] = role

        if pwd is not None:
            self._cork._store.users[username]['hash'] = self._cork._hash(
                username, pwd)

        if email_addr is not None:
            self._cork._store.users[username]['email_addr'] = email_addr

        self._cork._store.save_users()

    def delete(self):
        """Delete user account

        :raises: AAAException on nonexistent user.
        """
        try:
            self._cork._store.users.pop(self.username)
        except KeyError:
            raise AAAException("Nonexistent user.")
        self._cork._store.save_users()


class Mailer(object):

    def __init__(self, sender, smtp_url, join_timeout=5):
        """Send emails asyncronously

        :param sender: Sender email address
        :type sender: str.
        :param smtp_server: SMTP server
        :type smtp_server: str.
        """
        self.sender = sender
        self.join_timeout = join_timeout
        self._threads = []
        self._conf = self._parse_smtp_url(smtp_url)

    def _parse_smtp_url(self, url):
        """Parse SMTP URL"""
        match = re.match(r"""
            (                                   # Optional protocol
                (?P<proto>smtp|starttls|ssl)    # Protocol name
                ://
            )?
            (                                   # Optional user:pass@
                (?P<user>[^:]*)                 # Match every char except ':'
                (: (?P<pass>.*) )? @            # Optional :pass
            )?
            (?P<fqdn>                           # Required FQDN on IP address
                ()|                             # Empty string
                (                               # FQDN
                    [a-zA-Z_\-]                 # First character cannot be a number
                    [a-zA-Z0-9_\-\.]{,254}
                )
                |(                              # IPv4
                    ([0-9]{1,3}\.){3}
                    [0-9]{1,3}
                 )
                |(                              # IPv6
                    \[                          # Square brackets
                        ([0-9a-f]{,4}:){1,8}
                        [0-9a-f]{,4}
                    \]
                )
            )
            (                                   # Optional :port
                :
                (?P<port>[0-9]{,5})             # Up to 5-digits port
            )?
            [/]?
            $
        """, url, re.VERBOSE)

        if not match:
            raise RuntimeError("SMTP URL seems incorrect")

        d = match.groupdict()
        if d['proto'] is None:
            d['proto'] = 'smtp'

        if d['port'] is None:
            d['port'] = 25
        else:
            d['port'] = int(d['port'])

        if not 0 < d['port'] < 65536:
            raise RuntimeError("Incorrect SMTP port")

        return d

    def send_email(self, email_addr, subject, email_text):
        """Send an email

        :param email_addr: email address
        :type email_addr: str.
        :param subject: subject
        :type subject: str.
        :param email_text: email text
        :type email_text: str.
        :raises: AAAException if smtp_server and/or sender are not set
        """
        if not (self._conf['fqdn'] and self.sender):
            raise AAAException("SMTP server or sender not set")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = email_addr
        part = MIMEText(email_text, 'html')
        msg.attach(part)

        log.debug("Sending email using %s" % self._conf['fqdn'])
        thread = Thread(target=self._send, args=(email_addr, msg.as_string()))
        thread.start()
        self._threads.append(thread)

    def _send(self, email_addr, msg):
        """Deliver an email using SMTP

        :param email_addr: recipient
        :type email_addr: str.
        :param msg: email text
        :type msg: str.
        """
        proto = self._conf['proto']
        assert proto in ('smtp', 'starttls', 'ssl'), \
            "Incorrect protocol: %s" % proto

        try:
            if proto == 'ssl':
                log.debug("Setting up SSL")
                session = SMTP_SSL(self._conf['fqdn'], self._conf['port'])
            else:
                session = SMTP(self._conf['fqdn'], self._conf['port'])

            if proto == 'starttls':
                log.debug('Sending EHLO and STARTTLS')
                session.ehlo()
                session.starttls()
                session.ehlo()

            if self._conf['user'] is not None:
                log.debug('Performing login')
                session.login(self._conf['user'], self._conf['pass'])

            log.debug('Sending')
            session.sendmail(self.sender, email_addr, msg)
            session.quit()
            log.info('Email sent')

        except Exception as e:  # pragma: no cover
            log.error("Error sending email: %s" % e, exc_info=True)

    def join(self):
        """Flush email queue by waiting the completion of the existing threads

        :returns: None
        """
        return [t.join(self.join_timeout) for t in self._threads]

    def __del__(self):
        """Class destructor: wait for threads to terminate within a timeout"""
        self.join()

########NEW FILE########
__FILENAME__ = flaskcork
#!/usr/bin/env python
#
# Cork - Authentication module for the Flask web framework
#
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
#
# This package is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from base64 import b64encode, b64decode
from beaker import crypto
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging import getLogger
from smtplib import SMTP, SMTP_SSL
from threading import Thread
from time import time
import flask
import os
import re
import uuid

try:
    import scrypt
    scrypt_available = True
except ImportError:  # pragma: no cover
    scrypt_available = False

from backends import JsonBackend

log = getLogger(__name__)


class AAAException(Exception):
    """Generic Authentication/Authorization Exception"""
    pass

class AuthException(AAAException):
    """Authentication Exception: incorrect username/password pair"""
    pass

class Redirect(Exception):
    pass

def redirect(path):
    raise Redirect(path)

class FlaskCork(object):

    def __init__(self, directory=None, backend=None, email_sender=None,
        initialize=False, session_domain=None, smtp_server=None,
        smtp_url='localhost'):
        """Auth/Authorization/Accounting class

        :param directory: configuration directory
        :type directory: str.
        :param users_fname: users filename (without .json), defaults to 'users'
        :type users_fname: str.
        :param roles_fname: roles filename (without .json), defaults to 'roles'
        :type roles_fname: str.
        """
        if smtp_server:
            smtp_url = smtp_server
        self.mailer = Mailer(email_sender, smtp_url)
        self.password_reset_timeout = 3600 * 24
        self.session_domain = session_domain
        self.preferred_hashing_algorithm = 'PBKDF2'

        # Setup JsonBackend by default for backward compatibility.
        if backend is None:
            self._store = JsonBackend(directory, users_fname='users',
                roles_fname='roles', pending_reg_fname='register',
                initialize=initialize)

        else:
            self._store = backend

    def login(self, username, password, success_redirect=None,
        fail_redirect=None):
        """Check login credentials for an existing user.
        Optionally redirect the user to another page (typically /login)

        :param username: username
        :type username: str.
        :param password: cleartext password
        :type password: str.
        :param success_redirect: redirect authorized users (optional)
        :type success_redirect: str.
        :param fail_redirect: redirect unauthorized users (optional)
        :type fail_redirect: str.
        :returns: True for successful logins, else False
        """
        assert isinstance(username, str), "the username must be a string"
        assert isinstance(password, str), "the password must be a string"

        if username in self._store.users:
            if self._verify_password(username, password,
                    self._store.users[username]['hash']):
                # Setup session data
                self._setup_cookie(username)
                self._store.users[username]['last_login'] = str(datetime.utcnow())
                self._store.save_users()
                if success_redirect:
                    redirect(success_redirect)
                return True

        if fail_redirect:
            redirect(fail_redirect)

        return False

    def logout(self, success_redirect='/login', fail_redirect='/login'):
        """Log the user out, remove cookie

        :param success_redirect: redirect the user after logging out
        :type success_redirect: str.
        :param fail_redirect: redirect the user if it is not logged in
        :type fail_redirect: str.
        """
        try:
            session = self._beaker_session
            session.pop('username', None)

        except Exception, e:
            log.debug("Exception %s while logging out." % repr(e))
            redirect(fail_redirect)

        redirect(success_redirect)

    def require(self, username=None, role=None, fixed_role=False,
        fail_redirect=None):
        """Ensure the user is logged in has the required role (or higher).
        Optionally redirect the user to another page (typically /login)
        If both `username` and `role` are specified, both conditions need to be
        satisfied.
        If none is specified, any authenticated user will be authorized.
        By default, any role with higher level than `role` will be authorized;
        set fixed_role=True to prevent this.

        :param username: username (optional)
        :type username: str.
        :param role: role
        :type role: str.
        :param fixed_role: require user role to match `role` strictly
        :type fixed_role: bool.
        :param redirect: redirect unauthorized users (optional)
        :type redirect: str.
        """
        # Parameter validation
        if username is not None:
            if username not in self._store.users:
                raise AAAException("Nonexistent user")

        if fixed_role and role is None:
            raise AAAException(
                """A role must be specified if fixed_role has been set""")

        if role is not None and role not in self._store.roles:
            raise AAAException("Role not found")

        # Authentication
        try:
            cu = self.current_user
        except AAAException:
            if fail_redirect is None:
                raise AuthException("Unauthenticated user")
            else:
                redirect(fail_redirect)

        # Authorization
        if cu.role not in self._store.roles:
            raise AAAException("Role not found for the current user")

        if username is not None:
            if username != self.current_user.username:
                if fail_redirect is None:
                    raise AuthException("Unauthorized access: incorrect"
                        " username")
                else:
                    redirect(fail_redirect)

        if fixed_role:
            if role == self.current_user.role:
                return

            if fail_redirect is None:
                raise AuthException("Unauthorized access: incorrect role")
            else:
                redirect(fail_redirect)

        else:
            if role is not None:
                # Any role with higher level is allowed
                current_lvl = self._store.roles[self.current_user.role]
                threshold_lvl = self._store.roles[role]
                if current_lvl >= threshold_lvl:
                    return

                if fail_redirect is None:
                    raise AuthException("Unauthorized access: ")
                else:
                    redirect(fail_redirect)

        return

    def create_role(self, role, level):
        """Create a new role.

        :param role: role name
        :type role: str.
        :param level: role level (0=lowest, 100=admin)
        :type level: int.
        :raises: AuthException on errors
        """
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized to ")
        if role in self._store.roles:
            raise AAAException("The role is already existing")
        try:
            int(level)
        except ValueError:
            raise AAAException("The level must be numeric.")
        self._store.roles[role] = level
        self._store.save_roles()

    def delete_role(self, role):
        """Deleta a role.

        :param role: role name
        :type role: str.
        :raises: AuthException on errors
        """
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized to ")
        if role not in self._store.roles:
            raise AAAException("Nonexistent role.")
        self._store.roles.pop(role)
        self._store.save_roles()

    def list_roles(self):
        """List roles.

        :returns: (role, role_level) generator (sorted by role)
        """
        for role in sorted(self._store.roles):
            yield (role, self._store.roles[role])

    def create_user(self, username, role, password, email_addr=None,
        description=None):
        """Create a new user account.
        This method is available to users with level>=100

        :param username: username
        :type username: str.
        :param role: role
        :type role: str.
        :param password: cleartext password
        :type password: str.
        :param email_addr: email address (optional)
        :type email_addr: str.
        :param description: description (free form)
        :type description: str.
        :raises: AuthException on errors
        """
        assert username, "Username must be provided."
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized" \
                " to create users.")

        if username in self._store.users:
            raise AAAException("User is already existing.")
        if role not in self._store.roles:
            raise AAAException("Nonexistent user role.")
        tstamp = str(datetime.utcnow())
        self._store.users[username] = {
            'role': role,
            'hash': self._hash(username, password),
            'email_addr': email_addr,
            'desc': description,
            'creation_date': tstamp,
            'last_login': tstamp
        }
        self._store.save_users()

    def delete_user(self, username):
        """Delete a user account.
        This method is available to users with level>=100

        :param username: username
        :type username: str.
        :raises: Exceptions on errors
        """
        if self.current_user.level < 100:
            raise AuthException("The current user is not authorized to ")
        if username not in self._store.users:
            raise AAAException("Nonexistent user.")
        self.user(username).delete()

    def list_users(self):
        """List users.

        :return: (username, role, email_addr, description) generator (sorted by
            username)
        """
        for un in sorted(self._store.users):
            d = self._store.users[un]
            yield (un, d['role'], d['email_addr'], d['desc'])

    @property
    def current_user(self):
        """Current autenticated user

        :returns: User() instance, if authenticated
        :raises: AuthException otherwise
        """
        session = self._beaker_session
        username = session.get('username', None)
        if username is None:
            raise AuthException("Unauthenticated user")
        if username is not None and username in self._store.users:
            return User(username, self, session=session)
        raise AuthException("Unknown user: %s" % username)

    @property
    def user_is_anonymous(self):
        """Check if the current user is anonymous.

        :returns: True if the user is anonymous, False otherwise
        :raises: AuthException if the session username is unknown
        """
        try:
            username = self._beaker_session['username']
        except KeyError:
            return True

        if username not in self._store.users:
            raise AuthException("Unknown user: %s" % username)

        return False

    def user(self, username):
        """Existing user

        :returns: User() instance if the user exist, None otherwise
        """
        if username is not None and username in self._store.users:
            return User(username, self)
        return None

    def register(self, username, password, email_addr, role='user',
        max_level=50, subject="Signup confirmation",
        email_template='views/registration_email.tpl',
        description=None):
        """Register a new user account. An email with a registration validation
        is sent to the user.
        WARNING: this method is available to unauthenticated users

        :param username: username
        :type username: str.
        :param password: cleartext password
        :type password: str.
        :param role: role (optional), defaults to 'user'
        :type role: str.
        :param max_level: maximum role level (optional), defaults to 50
        :type max_level: int.
        :param email_addr: email address
        :type email_addr: str.
        :param subject: email subject
        :type subject: str.
        :param email_template: email template filename
        :type email_template: str.
        :param description: description (free form)
        :type description: str.
        :raises: AssertError or AAAException on errors
        """
        assert username, "Username must be provided."
        assert password, "A password must be provided."
        assert email_addr, "An email address must be provided."
        if username in self._store.users:
            raise AAAException("User is already existing.")
        if role not in self._store.roles:
            raise AAAException("Nonexistent role")
        if self._store.roles[role] > max_level:
            raise AAAException("Unauthorized role")

        registration_code = uuid.uuid4().hex
        creation_date = str(datetime.utcnow())

        # send registration email
        email_text = bottle.template(email_template,
            username=username,
            email_addr=email_addr,
            role=role,
            creation_date=creation_date,
            registration_code=registration_code
        )
        self.mailer.send_email(email_addr, subject, email_text)

        # store pending registration
        self._store.pending_registrations[registration_code] = {
            'username': username,
            'role': role,
            'hash': self._hash(username, password),
            'email_addr': email_addr,
            'desc': description,
            'creation_date': creation_date,
        }
        self._store.save_pending_registrations()

    def validate_registration(self, registration_code):
        """Validate pending account registration, create a new account if
        successful.

        :param registration_code: registration code
        :type registration_code: str.
        """
        try:
            data = self._store.pending_registrations.pop(registration_code)
        except KeyError:
            raise AuthException("Invalid registration code.")

        username = data['username']
        if username in self._store.users:
            raise AAAException("User is already existing.")

        # the user data is moved from pending_registrations to _users
        self._store.users[username] = {
            'role': data['role'],
            'hash': data['hash'],
            'email_addr': data['email_addr'],
            'desc': data['desc'],
            'creation_date': data['creation_date'],
            'last_login': str(datetime.utcnow())
        }
        self._store.save_users()

    def send_password_reset_email(self, username=None, email_addr=None,
        subject="Password reset confirmation",
        email_template='views/password_reset_email'):
        """Email the user with a link to reset his/her password
        If only one parameter is passed, fetch the other from the users
        database. If both are passed they will be matched against the users
        database as a security check.

        :param username: username
        :type username: str.
        :param email_addr: email address
        :type email_addr: str.
        :param subject: email subject
        :type subject: str.
        :param email_template: email template filename
        :type email_template: str.
        :raises: AAAException on missing username or email_addr,
            AuthException on incorrect username/email_addr pair
        """
        if username is None:
            if email_addr is None:
                raise AAAException("At least `username` or `email_addr` must" \
                    " be specified.")

            # only email_addr is specified: fetch the username
            for k, v in self._store.users.iteritems():
                if v['email_addr'] == email_addr:
                    username = k
                    break
            else:    
                raise AAAException("Email address not found.")

        else:  # username is provided
            if username not in self._store.users:
                raise AAAException("Nonexistent user.")
            if email_addr is None:
                email_addr = self._store.users[username].get('email_addr', None)
                if not email_addr:
                    raise AAAException("Email address not available.")
            else:
                # both username and email_addr are provided: check them
                stored_email_addr = self._store.users[username]['email_addr']
                if email_addr != stored_email_addr:
                    raise AuthException("Username/email address pair not found.")

        # generate a reset_code token
        reset_code = self._reset_code(username, email_addr)

        # send reset email
        email_text = bottle.template(email_template,
            username=username,
            email_addr=email_addr,
            reset_code=reset_code
        )
        self.mailer.send_email(email_addr, subject, email_text)

    def reset_password(self, reset_code, password):
        """Validate reset_code and update the account password
        The username is extracted from the reset_code token

        :param reset_code: reset token
        :type reset_code: str.
        :param password: new password
        :type password: str.
        :raises: AuthException for invalid reset tokens, AAAException
        """
        try:
            reset_code = b64decode(reset_code)
            username, email_addr, tstamp, h = reset_code.split(':', 3)
            tstamp = int(tstamp)
        except (TypeError, ValueError):
            raise AuthException("Invalid reset code.")
        if time() - tstamp > self.password_reset_timeout:
            raise AuthException("Expired reset code.")
        if not self._verify_password(username, email_addr, h):
            raise AuthException("Invalid reset code.")
        user = self.user(username)
        if user is None:
            raise AAAException("Nonexistent user.")
        user.update(pwd=password)

    def make_auth_decorator(self, username=None, role=None, fixed_role=False, fail_redirect='/login'):
        '''
        Create a decorator to be used for authentication and authorization

        :param username: A resource can be protected for a specific user
        :param role: Minimum role level required for authorization
        :param fixed_role: Only this role gets authorized
        :param fail_redirect: The URL to redirect to if a login is required.
        '''
        session_manager = self
        def auth_require(username=username, role=role, fixed_role=fixed_role,
                         fail_redirect=fail_redirect):
            def decorator(func):
                import functools
                @functools.wraps(func)
                def wrapper(*a, **ka):
                    session_manager.require(username=username, role=role, fixed_role=fixed_role,
                        fail_redirect=fail_redirect)
                    return func(*a, **ka)
                return wrapper
            return decorator
        return(auth_require)


    ## Private methods

    @property
    def _beaker_session(self):
        """Get Beaker session"""
        return flask.session

    def _setup_cookie(self, username):
        """Setup cookie for a user that just logged in"""
        session = self._beaker_session
        session['username'] = username
        if self.session_domain is not None:
            session.domain = self.session_domain

        if not hasattr(session, 'on_update'):
            #FIXME: use a better way to differentiate Bottle vs Flask
            session.save()

    def _hash(self, username, pwd, salt=None, algo=None):
        """Hash username and password, generating salt value if required
        """
        if algo is None:
            algo = self.preferred_hashing_algorithm

        if algo == 'PBKDF2':
            return self._hash_pbkdf2(username, pwd, salt=salt)

        if algo == 'scrypt':
            return self._hash_scrypt(username, pwd, salt=salt)

        raise RuntimeError("Unknown hashing algorithm requested: %s" % algo)

    @staticmethod
    def _hash_scrypt(username, pwd, salt=None):
        """Hash username and password, generating salt value if required
        Use scrypt.

        :returns: base-64 encoded str.
        """
        if not scrypt_available:
            raise Exception("scrypt.hash required."
                " Please install the scrypt library.")

        if salt is None:
            salt = os.urandom(32)

        assert len(salt) == 32, "Incorrect salt length"

        cleartext = "%s\0%s" % (username, pwd)
        h = scrypt.hash(cleartext, salt)

        # 's' for scrypt
        return b64encode('s' + salt + h)

    @staticmethod
    def _hash_pbkdf2(username, pwd, salt=None):
        """Hash username and password, generating salt value if required
        Use PBKDF2 from Beaker

        :returns: base-64 encoded str.
        """
        if salt is None:
            salt = os.urandom(32)
        assert len(salt) == 32, "Incorrect salt length"

        cleartext = "%s\0%s" % (username, pwd)
        h = crypto.generateCryptoKeys(cleartext, salt, 10)
        if len(h) != 32:
            raise RuntimeError("The PBKDF2 hash is %d bytes long instead"
                "of 32. The pycrypto library might be missing." % len(h))

        # 'p' for PBKDF2
        return b64encode('p' + salt + h)

    def _verify_password(self, username, pwd, salted_hash):
        """Verity username/password pair against a salted hash

        :returns: bool
        """
        decoded = b64decode(salted_hash)
        hash_type = decoded[0]
        salt = decoded[1:33]

        if hash_type == 'p':  # PBKDF2
            h = self._hash_pbkdf2(username, pwd, salt)
            return salted_hash == h

        if hash_type == 's':  # scrypt
            h = self._hash_scrypt(username, pwd, salt)
            return salted_hash == h

        raise RuntimeError("Unknown hashing algorithm: %s" % hash_type)

    def _purge_expired_registrations(self, exp_time=96):
        """Purge expired registration requests.

        :param exp_time: expiration time (hours)
        :type exp_time: float.
        """
        for uuid, data in self._store.pending_registrations.items():
            creation = datetime.strptime(data['creation_date'],
                "%Y-%m-%d %H:%M:%S.%f")
            now = datetime.utcnow()
            maxdelta = timedelta(hours=exp_time)
            if now - creation > maxdelta:
                self._store.pending_registrations.pop(uuid)

    def _reset_code(self, username, email_addr):
        """generate a reset_code token

        :param username: username
        :type username: str.
        :param email_addr: email address
        :type email_addr: str.
        :returns: Base-64 encoded token
        """
        h = self._hash(username, email_addr)
        t = "%d" % time()
        reset_code = ':'.join((username, email_addr, t, h))
        return b64encode(reset_code)


class User(object):

    def __init__(self, username, cork_obj, session=None):
        """Represent an authenticated user, exposing useful attributes:
        username, role, level, description, email_addr, session_creation_time,
        session_accessed_time, session_id. The session-related attributes are
        available for the current user only.

        :param username: username
        :type username: str.
        :param cork_obj: instance of :class:`Cork`
        """
        self._cork = cork_obj
        assert username in self._cork._store.users, "Unknown user"
        self.username = username
        user_data = self._cork._store.users[username]
        self.role = user_data['role']
        self.description = user_data['desc']
        self.email_addr = user_data['email_addr']
        self.level = self._cork._store.roles[self.role]

        if session is not None:
            try:
                self.session_creation_time = session['_creation_time']
                self.session_accessed_time = session['_accessed_time']
                self.session_id = session['_id']
            except:
                pass

    def update(self, role=None, pwd=None, email_addr=None):
        """Update an user account data

        :param role: change user role, if specified
        :type role: str.
        :param pwd: change user password, if specified
        :type pwd: str.
        :param email_addr: change user email address, if specified
        :type email_addr: str.
        :raises: AAAException on nonexistent user or role.
        """
        username = self.username
        if username not in self._cork._store.users:
            raise AAAException("User does not exist.")

        if role is not None:
            if role not in self._cork._store.roles:
                raise AAAException("Nonexistent role.")

            self._cork._store.users[username]['role'] = role

        if pwd is not None:
            self._cork._store.users[username]['hash'] = self._cork._hash(
                username, pwd)

        if email_addr is not None:
            self._cork._store.users[username]['email_addr'] = email_addr

        self._cork._store.save_users()

    def delete(self):
        """Delete user account

        :raises: AAAException on nonexistent user.
        """
        try:
            self._cork._store.users.pop(self.username)
        except KeyError:
            raise AAAException("Nonexistent user.")
        self._cork._store.save_users()


class Mailer(object):

    def __init__(self, sender, smtp_url, join_timeout=5):
        """Send emails asyncronously

        :param sender: Sender email address
        :type sender: str.
        :param smtp_server: SMTP server
        :type smtp_server: str.
        """
        self.sender = sender
        self.join_timeout = join_timeout
        self._threads = []
        self._conf = self._parse_smtp_url(smtp_url)

    def _parse_smtp_url(self, url):
        """Parse SMTP URL"""
        match = re.match(r"""
            (                                   # Optional protocol
                (?P<proto>smtp|starttls|ssl)    # Protocol name
                ://
            )?
            (                                   # Optional user:pass@
                (?P<user>[^:]*)                 # Match every char except ':'
                (: (?P<pass>.*) )? @            # Optional :pass
            )?
            (?P<fqdn>                           # Required FQDN on IP address
                ()|                             # Empty string
                (                               # FQDN
                    [a-zA-Z_\-]                 # First character cannot be a number
                    [a-zA-Z0-9_\-\.]{,254}
                )
                |(                              # IPv4
                    ([0-9]{1,3}\.){3}
                    [0-9]{1,3}
                 )
                |(                              # IPv6
                    \[                          # Square brackets
                        ([0-9a-f]{,4}:){1,8}
                        [0-9a-f]{,4}
                    \]
                )
            )
            (                                   # Optional :port
                :
                (?P<port>[0-9]{,5})             # Up to 5-digits port
            )?
            [/]?
            $
        """, url, re.VERBOSE)

        if not match:
            raise RuntimeError("SMTP URL seems incorrect")

        d = match.groupdict()
        if d['proto'] is None:
            d['proto'] = 'smtp'

        if d['port'] is None:
            d['port'] = 25
        else:
            d['port'] = int(d['port'])

        if not 0 < d['port'] < 65536:
            raise RuntimeError("Incorrect SMTP port")

        return d

    def send_email(self, email_addr, subject, email_text):
        """Send an email

        :param email_addr: email address
        :type email_addr: str.
        :param subject: subject
        :type subject: str.
        :param email_text: email text
        :type email_text: str.
        :raises: AAAException if smtp_server and/or sender are not set
        """
        if not (self._conf['fqdn'] and self.sender):
            raise AAAException("SMTP server or sender not set")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = email_addr
        part = MIMEText(email_text, 'html')
        msg.attach(part)

        log.debug("Sending email using %s" % self._conf['fqdn'])
        thread = Thread(target=self._send, args=(email_addr, msg.as_string()))
        thread.start()
        self._threads.append(thread)

    def _send(self, email_addr, msg):
        """Deliver an email using SMTP

        :param email_addr: recipient
        :type email_addr: str.
        :param msg: email text
        :type msg: str.
        """
        proto = self._conf['proto']
        assert proto in ('smtp', 'starttls', 'ssl'), \
            "Incorrect protocol: %s" % proto

        try:
            if proto == 'ssl':
                log.debug("Setting up SSL")
                session = SMTP_SSL(self._conf['fqdn'], self._conf['port'])
            else:
                session = SMTP(self._conf['fqdn'], self._conf['port'])

            if proto == 'starttls':
                log.debug('Sending EHLO and STARTTLS')
                session.ehlo()
                session.starttls()
                session.ehlo()

            if self._conf['user'] is not None:
                log.debug('Performing login')
                session.login(self._conf['user'], self._conf['pass'])

            log.debug('Sending')
            session.sendmail(self.sender, email_addr, msg)
            session.quit()
            log.info('Email sent')

        except Exception as e:  # pragma: no cover
            log.error("Error sending email: %s" % e, exc_info=True)

    def join(self):
        """Flush email queue by waiting the completion of the existing threads

        :returns: None
        """
        return [t.join(self.join_timeout) for t in self._threads]

    def __del__(self):
        """Class destructor: wait for threads to terminate within a timeout"""
        self.join()

########NEW FILE########
__FILENAME__ = json_backend
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# JSON file-based storage backend.
#

import shutil
import os
from logging import getLogger
try:
    import json
except ImportError:  # pragma: no cover
    import simplejson as json

import base_backend
from base_backend import BackendIOException

log = getLogger(__name__)

class JsonBackend(object):
    """JSON file-based storage backend."""

    def __init__(self, directory, users_fname='users',
            roles_fname='roles', pending_reg_fname='register', initialize=False):
        """Data storage class. Handles JSON files

        :param users_fname: users file name (without .json)
        :type users_fname: str.
        :param roles_fname: roles file name (without .json)
        :type roles_fname: str.
        :param pending_reg_fname: pending registrations file name (without .json)
        :type pending_reg_fname: str.
        :param initialize: create empty JSON files (defaults to False)
        :type initialize: bool.
        """
        assert directory, "Directory name must be valid"
        self._directory = directory
        self.users = {}
        self._users_fname = users_fname
        self.roles = {}
        self._roles_fname = roles_fname
        self._mtimes = {}
        self._pending_reg_fname = pending_reg_fname
        self.pending_registrations = {}
        if initialize:
            self._initialize_storage()
        self._refresh()  # load users and roles

    def _initialize_storage(self):
        """Create empty JSON files"""
        self._savejson(self._users_fname, {})
        self._savejson(self._roles_fname, {})
        self._savejson(self._pending_reg_fname, {})

    def _refresh(self):
        """Load users and roles from JSON files, if needed"""
        self._loadjson(self._users_fname, self.users)
        self._loadjson(self._roles_fname, self.roles)
        self._loadjson(self._pending_reg_fname, self.pending_registrations)

    def _loadjson(self, fname, dest):
        """Load JSON file located under self._directory, if needed

        :param fname: short file name (without path and .json)
        :type fname: str.
        :param dest: destination
        :type dest: dict
        """
        try:
            fname = "%s/%s.json" % (self._directory, fname)
            mtime = os.stat(fname).st_mtime

            if self._mtimes.get(fname, 0) == mtime:
                # no need to reload the file: the mtime has not been changed
                return

            with open(fname) as f:
                json_data = f.read()
        except Exception as e:
            raise BackendIOException("Unable to read json file %s: %s" % (fname, e))

        try:
            json_obj = json.loads(json_data)
            dest.clear()
            dest.update(json_obj)
            self._mtimes[fname] = os.stat(fname).st_mtime
        except Exception as e:
            raise BackendIOException("Unable to parse JSON data from %s: %s" \
                % (fname, e))

    def _savejson(self, fname, obj):
        """Save obj in JSON format in a file in self._directory"""
        fname = "%s/%s.json" % (self._directory, fname)
        try:
            s = json.dumps(obj)
            with open("%s.tmp" % fname, 'wb') as f:
                f.write(s)
                f.flush()
            shutil.move("%s.tmp" % fname, fname)
        except Exception as e:
            raise BackendIOException("Unable to save JSON file %s: %s" \
                % (fname, e))

    def save_users(self):
        """Save users in a JSON file"""
        self._savejson(self._users_fname, self.users)

    def save_roles(self):
        """Save roles in a JSON file"""
        self._savejson(self._roles_fname, self.roles)

    def save_pending_registrations(self):
        """Save pending registrations in a JSON file"""
        self._savejson(self._pending_reg_fname, self.pending_registrations)

########NEW FILE########
__FILENAME__ = mongodb_backend
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# MongoDB storage backend.
#

from logging import getLogger
log = getLogger(__name__)

from .base_backend import Backend, Table

try:
    import pymongo
    try:
        from pymongo import MongoClient
    except ImportError:  # pragma: no cover
        # Backward compatibility with PyMongo 2.2
        from pymongo import Connection as MongoClient

    pymongo_available = True
except ImportError:  # pragma: no cover
    pymongo_available = False



class MongoTable(Table):
    """Abstract MongoDB Table.
    Allow dictionary-like access.
    """
    def __init__(self, name, key_name, collection):
        self._name = name
        self._key_name = key_name
        self._coll = collection

    def create_index(self):
        """Create collection index."""
        self._coll.create_index(
            self._key_name,
            drop_dups=True,
            unique=True,
        )

    def __len__(self):
        return self._coll.count()

    def __contains__(self, value):
        r = self._coll.find_one({self._key_name: value})
        return r is not None

    def __iter__(self):
        """Iter on dictionary keys"""
        r = self._coll.find(fields=[self._key_name,])
        return (i[self._key_name] for i in r)

    def iteritems(self):
        """Iter on dictionary items.

        :returns: generator of (key, value) tuples
        """
        r = self._coll.find()
        for i in r:
            d = i.copy()
            d.pop(self._key_name)
            d.pop('_id')
            yield (i[self._key_name], d)

    def pop(self, key_val):
        """Remove a dictionary item"""
        r = self[key_val]
        self._coll.remove({self._key_name: key_val}, safe=True)
        return r


class MongoSingleValueTable(MongoTable):
    """MongoDB table accessible as a simple key -> value dictionary.
    Used to store roles.
    """
    # Values are stored in a MongoDB "column" named "val"
    def __init__(self, *args, **kw):
        super(MongoSingleValueTable, self).__init__(*args, **kw)

    def __setitem__(self, key_val, data):
        assert not isinstance(data, dict)
        spec = {self._key_name: key_val}
        data = {self._key_name: key_val, 'val': data}
        self._coll.update(spec, data, upsert=True, safe=True)

    def __getitem__(self, key_val):
        r = self._coll.find_one({self._key_name: key_val})
        if r is None:
            raise KeyError(key_val)

        return r['val']

class MongoMutableDict(dict):
    """Represent an item from a Table. Acts as a dictionary.
    """
    def __init__(self, parent, root_key, d):
        """Create a MongoMutableDict instance.
        :param parent: Table instance
        :type parent: :class:`MongoTable`
        """
        super(MongoMutableDict, self).__init__(d)
        self._parent = parent
        self._root_key = root_key

    def __setitem__(self, k, v):
        super(MongoMutableDict, self).__setitem__(k, v)
        self._parent[self._root_key] = self


class MongoMultiValueTable(MongoTable):
    """MongoDB table accessible as a dictionary.
    """
    def __init__(self, *args, **kw):
        super(MongoMultiValueTable, self).__init__(*args, **kw)

    def __setitem__(self, key_val, data):
        assert isinstance(data, dict)
        key_name = self._key_name
        if key_name in data:
            assert data[key_name] == key_val
        else:
            data[key_name] = key_val

        spec = {key_name: key_val}
        self._coll.update(spec, data, upsert=True)

    def __getitem__(self, key_val):
        r = self._coll.find_one({self._key_name: key_val})
        if r is None:
            raise KeyError(key_val)

        return MongoMutableDict(self, key_val, r)


class MongoDBBackend(Backend):
    def __init__(self, db_name='cork', hostname='localhost', port=27017, initialize=False):
        """Initialize MongoDB Backend"""
        connection = MongoClient(host=hostname, port=port)
        db = connection[db_name]
        self.users = MongoMultiValueTable('users', 'login', db.users)
        self.pending_registrations = MongoMultiValueTable(
            'pending_registrations',
            'pending_registration',
            db.pending_registrations
        )
        self.roles = MongoSingleValueTable('roles', 'role', db.roles)

        if initialize:
            self._initialize_storage()

    def _initialize_storage(self):
        """Create MongoDB indexes."""
        for c in (self.users, self.roles, self.pending_registrations):
            c.create_index()

    def save_users(self):
        pass

    def save_roles(self):
        pass

    def save_pending_registrations(self):
        pass

########NEW FILE########
__FILENAME__ = sqlalchemy_backend
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# SQLAlchemy storage backend.
#

import base_backend
from logging import getLogger
log = getLogger(__name__)

try:
    from sqlalchemy import create_engine, delete, func, select, \
        Column, ForeignKey, Integer, MetaData, String, Table
    sqlalchemy_available = True
except ImportError:  # pragma: no cover
    sqlalchemy_available = False


class SqlRowProxy(dict):
    def __init__(self, sql_dict, key, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.sql_dict = sql_dict
        self.key = key

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if self.sql_dict is not None:
            self.sql_dict[self.key] = {key: value}


class SqlTable(base_backend.Table):
    """Provides dictionary-like access to an SQL table."""

    def __init__(self, engine, table, key_col_name):
        self._engine = engine
        self._table = table
        self._key_col = table.c[key_col_name]

    def _row_to_value(self, row):
        row_key = row[self._key_col]
        row_value = SqlRowProxy(self, row_key,
            ((k, row[k]) for k in row.keys() if k != self._key_col.name))
        return row_key, row_value

    def __len__(self):
        query = self._table.count()
        c = self._engine.execute(query).scalar()
        return int(c)

    def __contains__(self, key):
        query = select([self._key_col], self._key_col == key)
        row = self._engine.execute(query).fetchone()
        return row is not None

    def __setitem__(self, key, value):
        if key in self:
            values = value
            query = self._table.update().where(self._key_col == key)

        else:
            values = {self._key_col.name: key}
            values.update(value)
            query = self._table.insert()

        self._engine.execute(query.values(**values))

    def __getitem__(self, key):
        query = select([self._table], self._key_col == key)
        row = self._engine.execute(query).fetchone()
        if row is None:
            raise KeyError(key)
        return self._row_to_value(row)[1]

    def __iter__(self):
        """Iterate over table index key values"""
        query = select([self._key_col])
        result = self._engine.execute(query)
        for row in result:
            key = row[0]
            yield key

    def iteritems(self):
        """Iterate over table rows"""
        query = select([self._table])
        result = self._engine.execute(query)
        for row in result:
            key = row[0]
            d = self._row_to_value(row)[1]
            yield (key, d)

    def pop(self, key):
        query = select([self._table], self._key_col == key)
        row = self._engine.execute(query).fetchone()
        if row is None:
            raise KeyError

        query = delete(self._table, self._key_col == key)
        self._engine.execute(query)
        return row

    def insert(self, d):
        query = self._table.insert(d)
        self._engine.execute(query)
        log.debug("%s inserted" % repr(d))

    def empty_table(self):
        query = self._table.delete()
        self._engine.execute(query)
        log.info("Table purged")


class SqlSingleValueTable(SqlTable):
    def __init__(self, engine, table, key_col_name, col_name):
        SqlTable.__init__(self, engine, table, key_col_name)
        self._col_name = col_name

    def _row_to_value(self, row):
        return row[self._key_col], row[self._col_name]

    def __setitem__(self, key, value):
        SqlTable.__setitem__(self, key, {self._col_name: value})



class SqlAlchemyBackend(base_backend.Backend):

    def __init__(self, db_full_url, users_tname='users', roles_tname='roles',
            pending_reg_tname='register', initialize=False):

        if not sqlalchemy_available:
            raise RuntimeError("The SQLAlchemy library is not available.")

        self._metadata = MetaData()
        if initialize:
            # Create new database if needed.
            db_url, db_name = db_full_url.rsplit('/', 1)
            self._engine = create_engine(db_url)
            try:
                self._engine.execute("CREATE DATABASE %s" % db_name)
            except Exception, e:
                log.info("Failed DB creation: %s" % e)

            # SQLite in-memory database URL: "sqlite://:memory:"
            if db_name != ':memory:':
                self._engine.execute("USE %s" % db_name)

        else:
            self._engine = create_engine(db_full_url)


        self._users = Table(users_tname, self._metadata,
            Column('username', String(128), primary_key=True),
            Column('role', ForeignKey(roles_tname + '.role')),
            Column('hash', String(256), nullable=False),
            Column('email_addr', String(128)),
            Column('desc', String(128)),
            Column('creation_date', String(128), nullable=False),
            Column('last_login', String(128), nullable=False)

        )
        self._roles = Table(roles_tname, self._metadata,
            Column('role', String(128), primary_key=True),
            Column('level', Integer, nullable=False)
        )
        self._pending_reg = Table(pending_reg_tname, self._metadata,
            Column('code', String(128), primary_key=True),
            Column('username', String(128), nullable=False),
            Column('role', ForeignKey(roles_tname + '.role')),
            Column('hash', String(256), nullable=False),
            Column('email_addr', String(128)),
            Column('desc', String(128)),
            Column('creation_date', String(128), nullable=False)
        )

        self.users = SqlTable(self._engine, self._users, 'username')
        self.roles = SqlSingleValueTable(self._engine, self._roles, 'role', 'level')
        self.pending_registrations = SqlTable(self._engine, self._pending_reg, 'code')

        if initialize:
            self._initialize_storage(db_name)
            log.debug("Tables created")


    def _initialize_storage(self, db_name):
        self._metadata.create_all(self._engine)

    def _drop_all_tables(self):
        for table in reversed(self._metadata.sorted_tables):
            log.info("Dropping table %s" % repr(table.name))
            self._engine.execute(table.delete())

    def save_users(self): pass
    def save_roles(self): pass
    def save_pending_registrations(self): pass

########NEW FILE########
__FILENAME__ = sqlite_backend
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# SQLite storage backend.
#

import base_backend
from logging import getLogger
log = getLogger(__name__)


class SqlRowProxy(dict):
    def __init__(self, table, key, row):
        li = ((k, v) for (k, ktype), v in zip(table._columns[1:], row[1:]))
        dict.__init__(self, li)
        self._table = table
        self._key = key

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self._table[self._key] = self


class Table(base_backend.Table):
    """Provides dictionary-like access to an SQL table."""

    def __init__(self, backend, table_name):
        self._backend = backend
        self._engine = backend.connection
        self._table_name = table_name
        self._column_names = zip(*self._columns)[0]
        self._key_col_num = 0
        self._key_col_name = self._column_names[self._key_col_num]
        self._key_col = self._column_names[self._key_col_num]

    def _row_to_value(self, key, row):
        assert isinstance(row, tuple)
        row_key = row[self._key_col_num]
        row_value = SqlRowProxy(self, key, row)
        return row_key, row_value

    def __len__(self):
        query = "SELECT count() FROM %s" % self._table_name
        ret = self._backend.run_query(query)
        return ret.fetchone()[0]

    def __contains__(self, key):
        #FIXME: count()
        query = "SELECT * FROM %s WHERE %s='%s'" % \
            (self._table_name, self._key_col, key)
        row = self._backend.fetch_one(query)
        return row is not None

    def __setitem__(self, key, value):
        """Create or update a row"""
        assert isinstance(value, dict)
        v, cn = set(value), set(self._column_names[1:])
        assert not v - cn, repr(v - cn)
        assert not cn - v, repr(cn - v)

        assert set(value) == set(self._column_names[1:]), "%s %s" % \
            (repr(set(value)), repr(set(self._column_names[1:])))

        col_values = [key] + [value[k] for k in self._column_names[1:]]

        col_names = ', '.join(self._column_names)
        question_marks = ', '.join('?' for x in col_values)
        query = "INSERT OR REPLACE INTO %s (%s) VALUES (%s)" % \
            (self._table_name, col_names, question_marks)

        ret = self._backend.run_query_using_conversion(query, col_values)


    def __getitem__(self, key):
        query = "SELECT * FROM %s WHERE %s='%s'" % \
            (self._table_name, self._key_col, key)
        row = self._backend.fetch_one(query)
        if row is None:
            raise KeyError(key)

        return self._row_to_value(key, row)[1]
        #return dict(zip(self._column_names, row))

    def __iter__(self):
        """Iterate over table index key values"""
        query = "SELECT %s FROM %s" % (self._key_col, self._table_name)
        result = self._backend.run_query(query)
        for row in result:
            yield row[0]

    def iteritems(self):
        """Iterate over table rows"""
        query = "SELECT * FROM %s" % self._table_name
        result = self._backend.run_query(query)
        for row in result:
            d = dict(zip(self._column_names, row))
            d.pop(self._key_col)

            yield (self._key_col, d)

    def pop(self, key):
        d = self.__getitem__(key)
        query = "DELETE FROM %s WHERE %s='%s'" % \
            (self._table_name, self._key_col, key)
        self._backend.fetch_one(query)
        #FIXME: check deletion
        return d

    def insert(self, d):
        raise NotImplementedError

    def empty_table(self):
        raise NotImplementedError

    def create_table(self):
        """Issue table creation"""
        cc = []
        for col_name, col_type in self._columns:
            if col_type == int:
                col_type = 'INTEGER'
            elif col_type == str:
                col_type = 'TEXT'

            if col_name == self._key_col:
                extras = 'PRIMARY KEY ASC'
            else:
                extras = ''

            cc.append("%s %s %s" % (col_name, col_type, extras))

        cc = ','.join(cc)
        query = "CREATE TABLE %s (%s)" % (self._table_name, cc)
        self._backend.run_query(query)


class SingleValueTable(Table):
    def __init__(self, *args):
        super(SingleValueTable, self).__init__(*args)
        self._value_col = self._column_names[1]

    def __setitem__(self, key, value):
        """Create or update a row"""
        assert not isinstance(value, dict)
        query = "INSERT OR REPLACE INTO %s (%s, %s) VALUES (?, ?)" % \
            (self._table_name, self._key_col, self._value_col)

        col_values = (key, value)
        ret = self._backend.run_query_using_conversion(query, col_values)

    def __getitem__(self, key):
        query = "SELECT %s FROM %s WHERE %s='%s'" % \
            (self._value_col, self._table_name, self._key_col, key)
        row = self._backend.fetch_one(query)
        if row is None:
            raise KeyError(key)

        return row[0]

class UsersTable(Table):
    def __init__(self, *args, **kwargs):
        self._columns = (
            ('username', str),
            ('role', str),
            ('hash', str),
            ('email_addr', str),
            ('desc', str),
            ('creation_date', str),
            ('last_login', str)
        )
        super(UsersTable, self).__init__(*args, **kwargs)

class RolesTable(SingleValueTable):
    def __init__(self, *args, **kwargs):
        self._columns = (
            ('role', str),
            ('level', int)
        )
        super(RolesTable, self).__init__(*args, **kwargs)

class PendingRegistrationsTable(Table):
    def __init__(self, *args, **kwargs):
        self._columns = (
            ('code', str),
            ('username', str),
            ('role', str),
            ('hash', str),
            ('email_addr', str),
            ('desc', str),
            ('creation_date', str)
        )
        super(PendingRegistrationsTable, self).__init__(*args, **kwargs)




class SQLiteBackend(base_backend.Backend):

    def __init__(self, filename, users_tname='users', roles_tname='roles',
            pending_reg_tname='register', initialize=False):

        self._filename = filename

        self.users = UsersTable(self, users_tname)
        self.roles = RolesTable(self, roles_tname)
        self.pending_registrations = PendingRegistrationsTable(self, pending_reg_tname)

        if initialize:
            self.users.create_table()
            self.roles.create_table()
            self.pending_registrations.create_table()
            log.debug("Tables created")

    @property
    def connection(self):
        try:
            return self._connection
        except AttributeError:
            import sqlite3
            self._connection = sqlite3.connect(self._filename)
            return self._connection

    def run_query(self, query):
        return self._connection.execute(query)

    def run_query_using_conversion(self, query, args):
        return self._connection.execute(query, args)

    def fetch_one(self, query):
        return self._connection.execute(query).fetchone()

    def _initialize_storage(self, db_name):
        raise NotImplementedError

    def _drop_all_tables(self):
        raise NotImplementedError

    def save_users(self): pass
    def save_roles(self): pass
    def save_pending_registrations(self): pass

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cork documentation build configuration file, created by
# sphinx-quickstart on Sun Apr  8 13:40:17 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import pkg_resources
import time

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../'))

__version__ = '0.10a'

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinxcontrib.blockdiag',
    'sphinxcontrib.issuetracker',
    'sphinxcontrib.spelling',
]

### Extensions configuration

issuetracker = 'github'
issuetracker_project = 'FedericoCeratto/bottle-cork'

### End of extensions configuration

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cork'
copyright = u"%s, Federico Ceratto" % time.strftime('%Y')

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(__version__.split(".")[:2])
# The full version, including alpha/beta/rc tags.
release = __version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
#pygments_style = 'bw'
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

autoclass_content = "both"
autodoc_default_flags = ['show-inheritance','members','undoc-members']
autodoc_member_order = 'bysource'

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'bw'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "github_ribbon": True,
    "github_ribbon_link": "https://github.com/FedericoCeratto/bottle-cork",
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [pkg_resources.resource_filename('bw_sphinxtheme', 'themes')]


# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Corkdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Cork.tex', u'Cork Documentation',
   u'Federico Ceratto', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cork', u'Cork Documentation',
     [u'Federico Ceratto'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Cork', u'Cork Documentation',
   u'Federico Ceratto', 'Cork', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = recreate_example_conf
#!/usr/bin/env python
#
#
# Regenerate files in example_conf

from datetime import datetime
from cork import Cork

def populate_conf_directory():
    cork = Cork('example_conf', initialize=True)

    cork._store.roles['admin'] = 100
    cork._store.roles['editor'] = 60
    cork._store.roles['user'] = 50
    cork._store.save_roles()

    tstamp = str(datetime.utcnow())
    username = password = 'admin'
    cork._store.users[username] = {
        'role': 'admin',
        'hash': cork._hash(username, password),
        'email_addr': username + '@localhost.local',
        'desc': username + ' test user',
        'creation_date': tstamp
    }
    username = password = ''
    cork._store.users[username] = {
        'role': 'user',
        'hash': cork._hash(username, password),
        'email_addr': username + '@localhost.local',
        'desc': username + ' test user',
        'creation_date': tstamp
    }
    cork._store.save_users()

if __name__ == '__main__':
    populate_conf_directory()


########NEW FILE########
__FILENAME__ = simple_webapp
#!/usr/bin/env python
#
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Cork example web application
#
# The following users are already available:
#  admin/admin, demo/demo

import bottle
from beaker.middleware import SessionMiddleware
from cork import Cork
import logging

logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)
bottle.debug(True)

# Use users.json and roles.json in the local example_conf directory
aaa = Cork('example_conf', email_sender='federico.ceratto@gmail.com', smtp_url='smtp://smtp.magnet.ie')

app = bottle.app()
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': 'please use a random key and keep it secret!',
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}
app = SessionMiddleware(app, session_opts)


# #  Bottle methods  # #

def postd():
    return bottle.request.forms


def post_get(name, default=''):
    return bottle.request.POST.get(name, default).strip()


@bottle.post('/login')
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/login')

@bottle.route('/user_is_anonymous')
def user_is_anonymous():
    if aaa.user_is_anonymous:
        return 'True'

    return 'False'

@bottle.route('/logout')
def logout():
    aaa.logout(success_redirect='/login')


@bottle.post('/register')
def register():
    """Send out registration email"""
    aaa.register(post_get('username'), post_get('password'), post_get('email_address'))
    return 'Please check your mailbox.'


@bottle.route('/validate_registration/:registration_code')
def validate_registration(registration_code):
    """Validate registration, create user account"""
    aaa.validate_registration(registration_code)
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.post('/reset_password')
def send_password_reset_email():
    """Send out password reset email"""
    aaa.send_password_reset_email(
        username=post_get('username'),
        email_addr=post_get('email_address')
    )
    return 'Please check your mailbox.'


@bottle.route('/change_password/:reset_code')
@bottle.view('password_change_form')
def change_password(reset_code):
    """Show password change form"""
    return dict(reset_code=reset_code)


@bottle.post('/change_password')
def change_password():
    """Change password"""
    aaa.reset_password(post_get('reset_code'), post_get('password'))
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.route('/')
def index():
    """Only authenticated users can see this"""
    aaa.require(fail_redirect='/login')
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'


@bottle.route('/restricted_download')
def restricted_download():
    """Only authenticated users can download this file"""
    aaa.require(fail_redirect='/login')
    return bottle.static_file('static_file', root='.')


@bottle.route('/my_role')
def show_current_user_role():
    """Show current user role"""
    session = bottle.request.environ.get('beaker.session')
    print "Session from simple_webapp", repr(session)
    aaa.require(fail_redirect='/login')
    return aaa.current_user.role


# Admin-only pages

@bottle.route('/admin')
@bottle.view('admin_page')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/sorry_page')
    return dict(
        current_user=aaa.current_user,
        users=aaa.list_users(),
        roles=aaa.list_roles()
    )


@bottle.post('/create_user')
def create_user():
    try:
        aaa.create_user(postd().username, postd().role, postd().password)
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_user')
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return dict(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return dict(ok=False, msg=e.message)


@bottle.post('/create_role')
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_role')
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


# Static pages

@bottle.route('/login')
@bottle.view('login_form')
def login_form():
    """Serve login form"""
    return {}


@bottle.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


# #  Web application main  # #

def main():

    # Start the Bottle webapp
    bottle.debug(True)
    bottle.run(app=app, quiet=False, reloader=True)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = simple_webapp_decorated
#!/usr/bin/env python
#
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Cork example web application
#
# The following users are already available:
#  admin/admin, demo/demo

import bottle
from beaker.middleware import SessionMiddleware
from cork import Cork
import logging

logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)
bottle.debug(True)

# Use users.json and roles.json in the local example_conf directory
aaa = Cork('example_conf', email_sender='federico.ceratto@gmail.com', smtp_url='smtp://smtp.magnet.ie')

# alias the authorization decorator with defaults
authorize = aaa.make_auth_decorator(fail_redirect="/login", role="user")

import datetime
app = bottle.app()
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': 'please use a random key and keep it secret!',
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}
app = SessionMiddleware(app, session_opts)


# #  Bottle methods  # #

def postd():
    return bottle.request.forms


def post_get(name, default=''):
    return bottle.request.POST.get(name, default).strip()


@bottle.post('/login')
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/login')

@bottle.route('/user_is_anonymous')
def user_is_anonymous():
    if aaa.user_is_anonymous:
        return 'True'

    return 'False'

@bottle.route('/logout')
def logout():
    aaa.logout(success_redirect='/login')


@bottle.post('/register')
def register():
    """Send out registration email"""
    aaa.register(post_get('username'), post_get('password'), post_get('email_address'))
    return 'Please check your mailbox.'


@bottle.route('/validate_registration/:registration_code')
def validate_registration(registration_code):
    """Validate registration, create user account"""
    aaa.validate_registration(registration_code)
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.post('/reset_password')
def send_password_reset_email():
    """Send out password reset email"""
    aaa.send_password_reset_email(
        username=post_get('username'),
        email_addr=post_get('email_address')
    )
    return 'Please check your mailbox.'


@bottle.route('/change_password/:reset_code')
@bottle.view('password_change_form')
def change_password(reset_code):
    """Show password change form"""
    return dict(reset_code=reset_code)


@bottle.post('/change_password')
def change_password():
    """Change password"""
    aaa.reset_password(post_get('reset_code'), post_get('password'))
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.route('/')
@authorize()
def index():
    """Only authenticated users can see this"""
    #session = bottle.request.environ.get('beaker.session')
    #aaa.require(fail_redirect='/login')
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'


# Resources used by tests designed to test decorators specifically

@bottle.route('/for_kings_only')
@authorize(role="king")
def page_for_kings():
    """
    This resource is used to test a non-existing role.
    Only kings or higher (e.g. gods) can see this
    """
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'

@bottle.route('/page_for_specific_user_admin')
@authorize(username="admin")
def page_for_username_admin():
    """Only a user named 'admin' can see this"""
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'

@bottle.route('/page_for_specific_user_fred_who_doesnt_exist')
@authorize(username="fred")
def page_for_user_fred():
    """Only authenticated users by the name of 'fred' can see this"""
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'

@bottle.route('/page_for_admins')
@authorize(role="admin")
def page_for_role_admin():
    """Only authenticated users (role=user or role=admin) can see this"""
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'



@bottle.route('/restricted_download')
@authorize()
def restricted_download():
    """Only authenticated users can download this file"""
    #aaa.require(fail_redirect='/login')
    return bottle.static_file('static_file', root='.')


@bottle.route('/my_role')
def show_current_user_role():
    """Show current user role"""
    session = bottle.request.environ.get('beaker.session')
    print "Session from simple_webapp", repr(session)
    aaa.require(fail_redirect='/login')
    return aaa.current_user.role


# Admin-only pages

@bottle.route('/admin')
@authorize(role="admin", fail_redirect='/sorry_page')
@bottle.view('admin_page')
def admin():
    """Only admin users can see this"""
    #aaa.require(role='admin', fail_redirect='/sorry_page')
    return dict(
        current_user = aaa.current_user,
        users = aaa.list_users(),
        roles = aaa.list_roles()
    )


@bottle.post('/create_user')
def create_user():
    try:
        aaa.create_user(postd().username, postd().role, postd().password)
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_user')
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return dict(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return dict(ok=False, msg=e.message)


@bottle.post('/create_role')
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_role')
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


# Static pages

@bottle.route('/login')
@bottle.view('login_form')
def login_form():
    """Serve login form"""
    return {}


@bottle.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


# #  Web application main  # #

def main():

    # Start the Bottle webapp
    bottle.debug(True)
    bottle.run(app=app, quiet=False, reloader=True)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = simple_webapp_flask
#!/usr/bin/env python
#
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Cork example web application
#
# The following users are already available:
#  admin/admin, demo/demo

import flask
from beaker.middleware import SessionMiddleware
from cork import FlaskCork
import logging
import os

logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)

# Use users.json and roles.json in the local example_conf directory
aaa = FlaskCork('example_conf', email_sender='federico.ceratto@gmail.com', smtp_url='smtp://smtp.magnet.ie')

app = flask.Flask(__name__)
app.debug = True
app.options = {} #FIXME

from flask import jsonify

#session_opts = {
#    'session.cookie_expires': True,
#    'session.encrypt_key': 'please use a random key and keep it secret!',
#    'session.httponly': True,
#    'session.timeout': 3600 * 24,  # 1 day
#    'session.type': 'cookie',
#    'session.validate_key': True,
#}
#app = SessionMiddleware(app, session_opts)


# #  Bottle methods  # #

def post_get(name, default=''):
    v = flask.request.form.get(name, default).strip()
    return str(v)

from cork import Redirect
@app.errorhandler(Redirect)
def redirect_exception_handler(e):
    return flask.redirect(e.message)


@app.route('/login', methods=['POST'])
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/login')

@app.route('/user_is_anonymous')
def user_is_anonymous():
    if aaa.user_is_anonymous:
        return 'True'

    return 'False'

@app.route('/logout')
def logout():
    aaa.logout(success_redirect='/login')


@app.route('/register', methods=['POST'])
def register():
    """Send out registration email"""
    aaa.register(post_get('username'), post_get('password'), post_get('email_address'))
    return 'Please check your mailbox.'


@app.route('/validate_registration/:registration_code')
def validate_registration(registration_code):
    """Validate registration, create user account"""
    aaa.validate_registration(registration_code)
    return 'Thanks. <a href="/login">Go to login</a>'


@app.route('/reset_password', methods=['POST'])
def send_password_reset_email():
    """Send out password reset email"""
    aaa.send_password_reset_email(
        username=post_get('username'),
        email_addr=post_get('email_address')
    )
    return 'Please check your mailbox.'


@app.route('/change_password/:reset_code')
def change_password(reset_code):
    """Show password change form"""
    return flask.render_template('password_change_form',
        reset_code=reset_code)


@app.route('/change_password', methods=['POST'])
def do_change_password():
    """Change password"""
    aaa.reset_password(post_get('reset_code'), post_get('password'))
    return 'Thanks. <a href="/login">Go to login</a>'


@app.route('/')
def index():
    """Only authenticated users can see this"""
    aaa.require(fail_redirect='/login')
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'


@app.route('/restricted_download')
def restricted_download():
    """Only authenticated users can download this file"""
    aaa.require(fail_redirect='/login')
    return flask.static_file('static_file', root='.')


@app.route('/my_role')
def show_current_user_role():
    """Show current user role"""
    session = flask.request.environ.get('beaker.session')
    print "Session from simple_webapp", repr(session)
    aaa.require(fail_redirect='/login')
    return aaa.current_user.role


# Admin-only pages

@app.route('/admin')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/sorry_page')
    return flask.render_template('admin_page.html',
        current_user=aaa.current_user,
        users=aaa.list_users(),
        roles=aaa.list_roles()
    )


@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        aaa.create_user(post_get('username'), post_get('role'),
            post_get('password'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        return jsonify(ok=False, msg=e.message)


@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return jsonify(ok=False, msg=e.message)


@app.route('/create_role', methods=['POST'])
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        return jsonify(ok=False, msg=e.message)


@app.route('/delete_role', methods=['POST'])
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        return jsonify(ok=False, msg=e.message)


# Static pages

@app.route('/login')
def login_form():
    """Serve login form"""
    return flask.render_template('login_form.html')


@app.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


# #  Web application main  # #

app.secret_key = os.urandom(24) #FIXME: why
def main():

    # Start the Bottle webapp
    #bottle.debug(True)
    app.secret_key = os.urandom(24)
    app.run(debug=True, use_reloader=True)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = simple_webapp_using_mongodb
#!/usr/bin/env python
#
#
# Cork example web application
#
# The following users are already available:
#  admin/admin, demo/demo

import bottle
from beaker.middleware import SessionMiddleware
from cork import Cork
from cork.backends import MongoDBBackend
import logging

logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)
bottle.debug(True)


def populate_mongodb_backend():
    mb = MongoDBBackend(db_name='cork-example', initialize=True)
    mb.users._coll.insert({
        "login": "admin",
        "email_addr": "admin@localhost.local",
        "desc": "admin test user",
        "role": "admin",
        "hash": "cLzRnzbEwehP6ZzTREh3A4MXJyNo+TV8Hs4//EEbPbiDoo+dmNg22f2RJC282aSwgyWv/O6s3h42qrA6iHx8yfw=",
        "creation_date": "2012-10-28 20:50:26.286723"
    })
    mb.roles._coll.insert({'role': 'admin', 'val': 100})
    mb.roles._coll.insert({'role': 'editor', 'val': 60})
    mb.roles._coll.insert({'role': 'user', 'val': 50})
    return mb

mb = populate_mongodb_backend()
aaa = Cork(backend=mb, email_sender='federico.ceratto@gmail.com', smtp_url='smtp://smtp.magnet.ie')

app = bottle.app()
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': 'please use a random key and keep it secret!',
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}
app = SessionMiddleware(app, session_opts)


# #  Bottle methods  # #

def postd():
    return bottle.request.forms


def post_get(name, default=''):
    return bottle.request.POST.get(name, default).strip()


@bottle.post('/login')
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/login')

@bottle.route('/user_is_anonymous')
def user_is_anonymous():
    if aaa.user_is_anonymous:
        return 'True'

    return 'False'

@bottle.route('/logout')
def logout():
    aaa.logout(success_redirect='/login')


@bottle.post('/register')
def register():
    """Send out registration email"""
    aaa.register(post_get('username'), post_get('password'), post_get('email_address'))
    return 'Please check your mailbox.'


@bottle.route('/validate_registration/:registration_code')
def validate_registration(registration_code):
    """Validate registration, create user account"""
    aaa.validate_registration(registration_code)
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.post('/reset_password')
def send_password_reset_email():
    """Send out password reset email"""
    aaa.send_password_reset_email(
        username=post_get('username'),
        email_addr=post_get('email_address')
    )
    return 'Please check your mailbox.'


@bottle.route('/change_password/:reset_code')
@bottle.view('password_change_form')
def change_password(reset_code):
    """Show password change form"""
    return dict(reset_code=reset_code)


@bottle.post('/change_password')
def change_password():
    """Change password"""
    aaa.reset_password(post_get('reset_code'), post_get('password'))
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.route('/')
def index():
    """Only authenticated users can see this"""
    aaa.require(fail_redirect='/login')
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'


@bottle.route('/restricted_download')
def restricted_download():
    """Only authenticated users can download this file"""
    aaa.require(fail_redirect='/login')
    return bottle.static_file('static_file', root='.')


@bottle.route('/my_role')
def show_current_user_role():
    """Show current user role"""
    session = bottle.request.environ.get('beaker.session')
    print "Session from simple_webapp", repr(session)
    aaa.require(fail_redirect='/login')
    return aaa.current_user.role


# Admin-only pages

@bottle.route('/admin')
@bottle.view('admin_page')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/sorry_page')
    return dict(
        current_user=aaa.current_user,
        users=aaa.list_users(),
        roles=aaa.list_roles()
    )


@bottle.post('/create_user')
def create_user():
    try:
        aaa.create_user(postd().username, postd().role, postd().password)
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_user')
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return dict(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return dict(ok=False, msg=e.message)


@bottle.post('/create_role')
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_role')
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


# Static pages

@bottle.route('/login')
@bottle.view('login_form')
def login_form():
    """Serve login form"""
    return {}


@bottle.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


# #  Web application main  # #

def main():

    # Start the Bottle webapp
    bottle.debug(True)
    bottle.run(app=app, quiet=False, reloader=True)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = simple_webapp_using_sqlite
#!/usr/bin/env python
#
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under GPLv3+ license, see LICENSE.txt
#
# Cork example web application
#
# The following users are already available:
#  admin/admin, demo/demo

import bottle
from beaker.middleware import SessionMiddleware
from cork import Cork
from cork.backends import SQLiteBackend
import logging

logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)
bottle.debug(True)

def populate_backend():
    b = SQLiteBackend('example.db', initialize=True)
    b.connection.executescript("""
        INSERT INTO users (username, email_addr, desc, role, hash, creation_date) VALUES
        (
            'admin',
            'admin@localhost.local',
            'admin test user',
            'admin',
            'cLzRnzbEwehP6ZzTREh3A4MXJyNo+TV8Hs4//EEbPbiDoo+dmNg22f2RJC282aSwgyWv/O6s3h42qrA6iHx8yfw=',
            '2012-10-28 20:50:26.286723'
        );
        INSERT INTO roles (role, level) VALUES ('special', 200);
        INSERT INTO roles (role, level) VALUES ('admin', 100);
        INSERT INTO roles (role, level) VALUES ('editor', 60);
        INSERT INTO roles (role, level) VALUES ('user', 50);
    """)
    return b

b = populate_backend()
aaa = Cork(backend=b, email_sender='federico.ceratto@gmail.com', smtp_url='smtp://smtp.magnet.ie')



app = bottle.app()
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': 'please use a random key and keep it secret!',
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}
app = SessionMiddleware(app, session_opts)


# #  Bottle methods  # #

def postd():
    return bottle.request.forms


def post_get(name, default=''):
    return bottle.request.POST.get(name, default).strip()


@bottle.post('/login')
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/login')

@bottle.route('/user_is_anonymous')
def user_is_anonymous():
    if aaa.user_is_anonymous:
        return 'True'

    return 'False'

@bottle.route('/logout')
def logout():
    aaa.logout(success_redirect='/login')


@bottle.post('/register')
def register():
    """Send out registration email"""
    aaa.register(post_get('username'), post_get('password'), post_get('email_address'))
    return 'Please check your mailbox.'


@bottle.route('/validate_registration/:registration_code')
def validate_registration(registration_code):
    """Validate registration, create user account"""
    aaa.validate_registration(registration_code)
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.post('/reset_password')
def send_password_reset_email():
    """Send out password reset email"""
    aaa.send_password_reset_email(
        username=post_get('username'),
        email_addr=post_get('email_address')
    )
    return 'Please check your mailbox.'


@bottle.route('/change_password/:reset_code')
@bottle.view('password_change_form')
def change_password(reset_code):
    """Show password change form"""
    return dict(reset_code=reset_code)


@bottle.post('/change_password')
def change_password():
    """Change password"""
    aaa.reset_password(post_get('reset_code'), post_get('password'))
    return 'Thanks. <a href="/login">Go to login</a>'


@bottle.route('/')
def index():
    """Only authenticated users can see this"""
    aaa.require(fail_redirect='/login')
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'


@bottle.route('/restricted_download')
def restricted_download():
    """Only authenticated users can download this file"""
    aaa.require(fail_redirect='/login')
    return bottle.static_file('static_file', root='.')


@bottle.route('/my_role')
def show_current_user_role():
    """Show current user role"""
    session = bottle.request.environ.get('beaker.session')
    print "Session from simple_webapp", repr(session)
    aaa.require(fail_redirect='/login')
    return aaa.current_user.role


# Admin-only pages

@bottle.route('/admin')
@bottle.view('admin_page')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/sorry_page')
    return dict(
        current_user=aaa.current_user,
        users=aaa.list_users(),
        roles=aaa.list_roles()
    )


@bottle.post('/create_user')
def create_user():
    try:
        aaa.create_user(postd().username, postd().role, postd().password)
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_user')
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return dict(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return dict(ok=False, msg=e.message)


@bottle.post('/create_role')
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@bottle.post('/delete_role')
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


# Static pages

@bottle.route('/login')
@bottle.view('login_form')
def login_form():
    """Serve login form"""
    return {}


@bottle.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


# #  Web application main  # #

def main():

    # Start the Bottle webapp
    bottle.debug(True)
    bottle.run(app=app, quiet=False, reloader=False)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_local_webapp
#
# Functional testing using Mechanize.
# A local instance of the example webapp needs to be run on port 8080.
#

import mechanize
import cookielib

class TestUsingMechanize(object):
    def setup(self):
        self.local_url = "http://127.0.0.1:8080%s"
        br = mechanize.Browser()
        # Cookie Jar
        self.cj = cookielib.LWPCookieJar()
        br.set_cookiejar(self.cj)
        # Browser options
        br.set_handle_equiv(True)
        br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)
        # Want debugging messages?
        #br.set_debug_http(True)
        br.set_debug_redirects(True)
        br.set_debug_responses(True)

        self.br = br

    def teardown(self):
        del(self.local_url)
        del(self.br)
        del(self.cj)

    def openurl(self, path, data=None):
        """Perform GET or POST request"""
        if path in ('', None):
            path = '/'

        if data is not None:
            # Prepare for POST
            for k, v in data.iteritems():
                #FIXME: test POST
                self.br[k] = v

        res = self.br.open(self.local_url % path)
        assert self.br.viewing_html()
        return res

    def submit_form(self, formname, data):
        """Select and submit a form"""
        self.br.select_form(name=formname)

        # Prepare for POST
        for k, v in data.iteritems():
            self.br[k] = v

        res = self.br.submit()
        assert not hasattr(self.br, k)
        return res

    @property
    def cookies(self):
        """Return a list of cookies"""
        return list(self.cj)

    def test_login_and_logout(self):

        assert not self.cookies

        res = self.openurl('/')
        assert not self.cookies

        res = self.submit_form('login', {
            'username': 'admin',
            'password': 'admin',
        })
        assert 'Welcome!' in res.get_data()

        assert len(self.cookies) == 1
        assert self.cookies[0].name == 'beaker.session.id'

        res = self.openurl('/logout')
        assert not self.cookies



########NEW FILE########
__FILENAME__ = simple_webapp
../examples/simple_webapp.py
########NEW FILE########
__FILENAME__ = simple_webapp_decorated
../examples/simple_webapp_decorated.py
########NEW FILE########
__FILENAME__ = simple_webapp_flask
#!/usr/bin/env python
#
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Cork example web application
#
# The following users are already available:
#  admin/admin, demo/demo

import flask
from beaker.middleware import SessionMiddleware
from cork import FlaskCork
import logging
import os

logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)

# Use users.json and roles.json in the local example_conf directory
aaa = FlaskCork('example_conf', email_sender='federico.ceratto@gmail.com', smtp_url='smtp://smtp.magnet.ie')

app = flask.Flask(__name__)
app.debug = True
app.options = {} #FIXME

from flask import jsonify

#session_opts = {
#    'session.cookie_expires': True,
#    'session.encrypt_key': 'please use a random key and keep it secret!',
#    'session.httponly': True,
#    'session.timeout': 3600 * 24,  # 1 day
#    'session.type': 'cookie',
#    'session.validate_key': True,
#}
#app = SessionMiddleware(app, session_opts)


# #  Bottle methods  # #

def post_get(name, default=''):
    v = flask.request.form.get(name, default).strip()
    return str(v)

from cork import Redirect
@app.errorhandler(Redirect)
def redirect_exception_handler(e):
    return flask.redirect(e.message)


@app.route('/login', methods=['POST'])
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/login')

@app.route('/user_is_anonymous')
def user_is_anonymous():
    if aaa.user_is_anonymous:
        return 'True'

    return 'False'

@app.route('/logout')
def logout():
    aaa.logout(success_redirect='/login')


@app.route('/register', methods=['POST'])
def register():
    """Send out registration email"""
    aaa.register(post_get('username'), post_get('password'), post_get('email_address'))
    return 'Please check your mailbox.'


@app.route('/validate_registration/:registration_code')
def validate_registration(registration_code):
    """Validate registration, create user account"""
    aaa.validate_registration(registration_code)
    return 'Thanks. <a href="/login">Go to login</a>'


@app.route('/reset_password', methods=['POST'])
def send_password_reset_email():
    """Send out password reset email"""
    aaa.send_password_reset_email(
        username=post_get('username'),
        email_addr=post_get('email_address')
    )
    return 'Please check your mailbox.'


@app.route('/change_password/:reset_code')
def change_password(reset_code):
    """Show password change form"""
    return flask.render_template('password_change_form',
        reset_code=reset_code)


@app.route('/change_password', methods=['POST'])
def do_change_password():
    """Change password"""
    aaa.reset_password(post_get('reset_code'), post_get('password'))
    return 'Thanks. <a href="/login">Go to login</a>'


@app.route('/')
def index():
    """Only authenticated users can see this"""
    aaa.require(fail_redirect='/login')
    return 'Welcome! <a href="/admin">Admin page</a> <a href="/logout">Logout</a>'


@app.route('/restricted_download')
def restricted_download():
    """Only authenticated users can download this file"""
    aaa.require(fail_redirect='/login')
    return flask.static_file('static_file', root='.')


@app.route('/my_role')
def show_current_user_role():
    """Show current user role"""
    session = flask.request.environ.get('beaker.session')
    print "Session from simple_webapp", repr(session)
    aaa.require(fail_redirect='/login')
    return aaa.current_user.role


# Admin-only pages

@app.route('/admin')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/sorry_page')
    return flask.render_template('admin_page.html',
        current_user=aaa.current_user,
        users=aaa.list_users(),
        roles=aaa.list_roles()
    )


@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        aaa.create_user(post_get('username'), post_get('role'),
            post_get('password'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        return jsonify(ok=False, msg=e.message)


@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return jsonify(ok=False, msg=e.message)


@app.route('/create_role', methods=['POST'])
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        return jsonify(ok=False, msg=e.message)


@app.route('/delete_role', methods=['POST'])
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return jsonify(ok=True, msg='')
    except Exception, e:
        return jsonify(ok=False, msg=e.message)


# Static pages

@app.route('/login')
def login_form():
    """Serve login form"""
    return flask.render_template('login_form.html')


@app.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


# #  Web application main  # #

app.secret_key = os.urandom(24) #FIXME: why
def main():

    # Start the Bottle webapp
    #bottle.debug(True)
    app.secret_key = os.urandom(24)
    app.run(debug=True, use_reloader=True)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Unit testing
#

from base64 import b64encode, b64decode
from nose import SkipTest
from nose.tools import assert_raises, raises, with_setup
from time import time
import mock
import os
import shutil

from cork import Cork, JsonBackend, AAAException, AuthException
from cork import Mailer
from cork.base_backend import BackendIOException
import testutils

testdir = None  # Test directory
aaa = None  # global Cork instance
cookie_name = None  # global variable to track cookie status

tmproot = testutils.pick_temp_directory()


class RoAttrDict(dict):
    """Read-only attribute-accessed dictionary.
    Used to mock beaker's session objects
    """
    def __getattr__(self, name):
        return self[name]


class MockedAdminCork(Cork):
    """Mocked module where the current user is always 'admin'"""
    @property
    def _beaker_session(self):
        return RoAttrDict(username='admin')

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


class MockedUnauthenticatedCork(Cork):
    """Mocked module where the current user not set"""
    @property
    def _beaker_session(self):
        return RoAttrDict()

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


def setup_empty_dir():
    """Setup test directory without JSON files"""
    global testdir
    tstamp = "%f" % time()
    testdir = "%s/fl_%s" % (tmproot, tstamp)
    os.mkdir(testdir)
    os.mkdir(testdir + '/view')
    print("setup done in %s" % testdir)


def setup_dir():
    """Setup test directory with valid JSON files"""
    global testdir
    tstamp = "%f" % time()
    testdir = "%s/fl_%s" % (tmproot, tstamp)
    os.mkdir(testdir)
    os.mkdir(testdir + '/views')
    with open("%s/users.json" % testdir, 'w') as f:
        f.write("""{"admin": {"email_addr": null, "desc": null, "role": "admin", "hash": "69f75f38ac3bfd6ac813794f3d8c47acc867adb10b806e8979316ddbf6113999b6052efe4ba95c0fa9f6a568bddf60e8e5572d9254dbf3d533085e9153265623", "creation_date": "2012-04-09 14:22:27.075596"}}""")
    with open("%s/roles.json" % testdir, 'w') as f:
        f.write("""{"special": 200, "admin": 100, "user": 50}""")
    with open("%s/register.json" % testdir, 'w') as f:
        f.write("""{}""")
    with open("%s/views/registration_email.tpl" % testdir, 'w') as f:
        f.write("""Username:{{username}} Email:{{email_addr}} Code:{{registration_code}}""")
    with open("%s/views/password_reset_email.tpl" % testdir, 'w') as f:
        f.write("""Username:{{username}} Email:{{email_addr}} Code:{{reset_code}}""")
    print("setup done in %s" % testdir)


def setup_mockedadmin():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    setup_dir()
    aaa = MockedAdminCork(testdir, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None


def setup_mocked_unauthenticated():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    setup_dir()
    aaa = MockedUnauthenticatedCork(testdir)
    cookie_name = None


def teardown_dir():
    global cookie_name
    global testdir
    if testdir:
        shutil.rmtree(testdir)
        testdir = None
    cookie_name = None


@with_setup(setup_dir, teardown_dir)
def test_init():
    Cork(testdir)


@with_setup(setup_dir, teardown_dir)
def test_initialize_storage():
    jb = JsonBackend(testdir, initialize=True)
    Cork(backend=jb)
    with open("%s/users.json" % testdir) as f:
        assert f.readlines() == ['{}']
    with open("%s/roles.json" % testdir) as f:
        assert f.readlines() == ['{}']
    with open("%s/register.json" % testdir) as f:
        assert f.readlines() == ['{}']
    with open("%s/views/registration_email.tpl" % testdir) as f:
        assert f.readlines() == [
            'Username:{{username}} Email:{{email_addr}} Code:{{registration_code}}']
    with open("%s/views/password_reset_email.tpl" % testdir) as f:
        assert f.readlines() == [
            'Username:{{username}} Email:{{email_addr}} Code:{{reset_code}}']


@raises(BackendIOException)
@with_setup(setup_dir, teardown_dir)
def test_unable_to_save():
    bogus_dir = '/___inexisting_directory___'
    Cork(bogus_dir, initialize=True)


@with_setup(setup_mockedadmin, teardown_dir)
def test_mockedadmin():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    assert 'admin' in aaa._store.users, repr(aaa._store.users)

@raises(BackendIOException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_loadjson_missing_file():
    aaa._store._loadjson('nonexistent_file', {})

@raises(BackendIOException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_loadjson_broken_file():
    with open(testdir + '/broken_file.json', 'w') as f:
        f.write('-----')
    aaa._store._loadjson('broken_file', {})


@with_setup(setup_mockedadmin, teardown_dir)
def test_loadjson_unchanged():
    # By running _refresh with unchanged files the files should not be reloaded
    mtimes = aaa._store._mtimes
    aaa._store._refresh()
    # The test simply ensures that no mtimes have been updated
    assert mtimes == aaa._store._mtimes


# Test PBKDF2-based password hashing

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_known_hash():
    salt = 's' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    assert shash == 'cHNzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzax44AxQgK6uD9q1YWxLos1ispCe1Z7T7pOFK1PwdWEs='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_known_hash_2():
    salt = '\0' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    assert shash == 'cAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/8Uh4pyEOHoRz4j0lDzAmqb7Dvmo8GpeXwiKTDsuYFw='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_known_hash_3():
    salt = 'x' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    assert shash == 'cHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4MEaIU5Op97lmvwX5NpVSTBP8jg8OlrN7c2K8K8tnNks='

@raises(AssertionError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_incorrect_hash_len():
    salt = 'x' * 31 # Incorrect length
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_incorrect_hash_value():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt)
    assert hash1 != hash2, "Hash collision"

# Test scrypt-based password hashing

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt():
    shash = aaa._hash('user_foo', 'bogus_pwd', algo='scrypt')
    assert len(shash) == 132, "hash length should be 132 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_known_hash():
    salt = 's' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    assert shash == 'c3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3NzeLt/2Ta8vJOVqimNpN9G1WWxN1hxlUOJDPgH+0wqPpG20XQHFHLlksDIUo2BL4P8BMLBZj7F+cq6UP6pc304LQ=='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_known_hash_2():
    salt = '\0' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    assert shash == 'cwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAmu5jQskr2/yX13Yxmc4TYL0MIuSxwo41SVJwn/QueiDdLGkNaEsxlKL37i98YofXxs8xJJAJlC3Xj/9Nx0RNBw=='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_known_hash_3():
    salt = 'x' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    assert shash == 'c3h4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4yKuT1e8lovFZnaaOctivIvYBPkLoKDXX72kf5/nRuGIgyyhiKxxKE4LVYFKFCeVNPQM5m/+LulQkWhO0aB89lA=='

@raises(AssertionError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_incorrect_hash_len():
    salt = 'x' * 31 # Incorrect length
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_incorrect_hash_value():
    shash = aaa._hash('user_foo', 'bogus_pwd', algo='scrypt')
    assert len(shash) == 132, "hash length should be 132 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"


@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt, algo='scrypt')
    assert hash1 != hash2, "Hash collision"

# Test password hashing for inexistent algorithms

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_bogus_algo():
    aaa._hash('user_foo', 'bogus_pwd', algo='bogus_algo')

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_bogus_algo_during_verify():
    # Incorrect hash type (starts with "X")
    shash = b64encode('X' + 'bogusstring')
    aaa._verify_password('user_foo', 'bogus_pwd', shash)

# End of password hashing tests


@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_create_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_role, 'user', 33)


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_existing_role():
    assert_raises(AAAException, aaa.create_role, 'user', 33)


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_create_role_with_incorrect_level():
    aaa.create_role('new_user', 'not_a_number')


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_role():
    assert len(aaa._store.roles) == 3, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._roles_fname)
    with open(fname) as f:
        data = f.read()
        assert 'user33' in data, repr(data)

@SkipTest
@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_create_empty_role():
    aaa.create_role('', 42)

@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_delete_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_role, 'user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_delete_nonexistent_role():
    assert_raises(AAAException, aaa.delete_role, 'user123')


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_delete_role():
    assert len(aaa._store.roles) == 3, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._roles_fname)
    with open(fname) as f:
        data = f.read()
        assert 'user33' in data, repr(data)
    assert aaa._store.roles['user33'] == 33
    aaa.delete_role('user33')
    assert len(aaa._store.roles) == 3, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, teardown_dir)
def test_list_roles():
    roles = list(aaa.list_roles())
    assert len(roles) == 3, "Incorrect. Users are: %s" % repr(aaa._store.roles)


@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_create_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_user, 'phil', 'user', 'hunter123')

@with_setup(setup_mockedadmin, teardown_dir)
def test_create_existing_user():
    assert_raises(AAAException, aaa.create_user, 'admin', 'admin', 'bogus')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_create_user_with_wrong_role():
    aaa.create_user('admin2', 'nonexistent_role', 'bogus')


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.create_user('phil', 'user', 'user')
    assert len(aaa._store.users) == 2, repr(aaa._store.users)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._users_fname)
    with open(fname) as f:
        data = f.read()
        assert 'phil' in data, repr(data)


@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_delete_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_user, 'phil')


@with_setup(setup_mockedadmin, teardown_dir)
def test_delete_nonexistent_user():
    assert_raises(AAAException, aaa.delete_user, 'not_an_user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_delete_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.delete_user('admin')
    assert len(aaa._store.users) == 0, repr(aaa._store.users)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._users_fname)
    with open(fname) as f:
        data = f.read()
        assert 'admin' not in data, "'admin' must not be in %s" % repr(data)


@with_setup(setup_mockedadmin, teardown_dir)
def test_list_users():
    users = list(aaa.list_users())
    assert len(users) == 1, "Incorrect. Users are: %s" % repr(aaa._store.users)


@with_setup(setup_mockedadmin, teardown_dir)
def test_failing_login():
    login = aaa.login('phil', 'hunter123')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, teardown_dir)
def test_login_nonexistent_user_empty_password():
    login = aaa.login('IAmNotHome', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, teardown_dir)
def test_login_existing_user_empty_password():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_and_validate_user():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    global cookie_name
    assert cookie_name == 'phil'


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_failing_username():
    # The user exists, but I'm 'admin'
    aaa.create_user('phil', 'user', 'hunter123')
    assert_raises(AuthException, aaa.require, username='phil')


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_nonexistent_username():
    assert_raises(AAAException, aaa.require, username='no_such_user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_failing_role_fixed():
    assert_raises(AuthException, aaa.require, role='user', fixed_role=True)


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_require_missing_parameter():
    aaa.require(fixed_role=True)


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_nonexistent_role():
    assert_raises(AAAException, aaa.require, role='clown')


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_failing_role():
    # Requesting level >= 100
    assert_raises(AuthException, aaa.require, role='special')


@with_setup(setup_mockedadmin, teardown_dir)
def test_successful_require_role():
    aaa.require(username='admin')
    aaa.require(username='admin', role='admin')
    aaa.require(username='admin', role='admin', fixed_role=True)
    aaa.require(username='admin', role='user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_authenticated_is_not__anonymous():
    assert not aaa.user_is_anonymous


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_nonexistent_role():
    assert_raises(AAAException, aaa.current_user.update, role='clown')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_update_nonexistent_user():
    aaa._store.users.pop('admin')
    aaa.current_user.update(role='user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_role():
    aaa.current_user.update(role='user')
    assert aaa._store.users['admin']['role'] == 'user'


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_pwd():
    aaa.current_user.update(pwd='meow')


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_email():
    aaa.current_user.update(email_addr='foo')
    assert aaa._store.users['admin']['email_addr'] == 'foo'


@raises(AAAException)
@with_setup(setup_mocked_unauthenticated, teardown_dir)
def test_get_current_user_unauth():
    aaa.current_user['username']


@with_setup(setup_mocked_unauthenticated, teardown_dir)
def test_unauth_is_anonymous():
    assert aaa.user_is_anonymous


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_get_current_user_nonexistent():
    # The current user 'admin' is not in the user table
    aaa._store.users.pop('admin')
    aaa.current_user


@with_setup(setup_mockedadmin, teardown_dir)
def test_get_nonexistent_user():
    assert aaa.user('nonexistent_user') is None


@with_setup(setup_mockedadmin, teardown_dir)
def test_get_user_description_field():
    admin = aaa.user('admin')
    for field in ['description', 'email_addr']:
        assert field in admin.__dict__


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_user():
    assert_raises(AssertionError, aaa.register, None, 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_pwd():
    assert_raises(AssertionError, aaa.register, 'foo', None, 'a@a.a')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_email():
    assert_raises(AssertionError, aaa.register, 'foo', 'pwd', None)


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_already_existing():
    assert_raises(AAAException, aaa.register, 'admin', 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_role():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='clown')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_role_too_high():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='admin')


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_register(mocked):
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('foo', 'pwd', 'a@a.a')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_1():
    c = aaa.mailer._parse_smtp_url('')
    assert c['proto'] == 'smtp'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == ''
    assert c['port'] == 25


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_2():
    c = aaa.mailer._parse_smtp_url('starttls://foo')
    assert c['proto'] == 'starttls'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == 'foo'
    assert c['port'] == 25

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_3():
    c = aaa.mailer._parse_smtp_url('foo:443')
    assert c['proto'] == 'smtp'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_4():
    c = aaa.mailer._parse_smtp_url('ssl://user:pass@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'user'
    assert c['pass'] == 'pass'
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_5():
    c = aaa.mailer._parse_smtp_url('smtp://smtp.magnet.ie')
    assert c['proto'] == 'smtp'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == 'smtp.magnet.ie'
    assert c['port'] == 25


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_email_as_username_no_password():
    # the username contains an at sign '@'
    c = aaa.mailer._parse_smtp_url('ssl://us.er@somewhere.net@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'us.er@somewhere.net', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == None
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_email_as_username():
    # the username contains an at sign '@'
    c = aaa.mailer._parse_smtp_url('ssl://us.er@somewhere.net:pass@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'us.er@somewhere.net', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == 'pass'
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_at_sign_in_password():
    # the password contains at signs '@'
    c = aaa.mailer._parse_smtp_url('ssl://username:pass@w@rd@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'username', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == 'pass@w@rd', \
        "Password is incorrectly parsed as '%s'" % c['pass']
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_email_as_username_2():
    # both the username and the password contains an at sign '@'
    c = aaa.mailer._parse_smtp_url('ssl://us.er@somewhere.net:pass@word@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'us.er@somewhere.net', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == 'pass@word', \
        "Password is incorrectly parsed as '%s'" % c['pass']
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_port():
    c = aaa.mailer._parse_smtp_url(':99999')

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_port_len():
    c = aaa.mailer._parse_smtp_url(':123456')

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_len():
    c = aaa.mailer._parse_smtp_url('a' * 256)

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_syntax():
    c = aaa.mailer._parse_smtp_url('::')

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_IPv4():
    c = aaa.mailer._parse_smtp_url('127.0.0.1')
    assert c['fqdn'] == '127.0.0.1'

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_IPv6():
    c = aaa.mailer._parse_smtp_url('[2001:0:0123:4567:89ab:cdef]')
    assert c['fqdn'] == '[2001:0:0123:4567:89ab:cdef]'


# Patch the SMTP class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP')
def test_send_email_SMTP(SMTP):
    SMTP.return_value = msession = mock.Mock() # session instance

    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP.assert_called_once_with('localhost', 25)
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 2

# Patch the SMTP_SSL class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP_SSL')
def test_send_email_SMTP_SSL(SMTP_SSL):
    SMTP_SSL.return_value = msession = mock.Mock() # session instance

    aaa.mailer._conf['proto'] = 'ssl'
    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP_SSL.assert_called_once_with('localhost', 25)
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 2

# Patch the SMTP_SSL class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP_SSL')
def test_send_email_SMTP_SSL_with_login(SMTP_SSL):
    SMTP_SSL.return_value = msession = mock.Mock() # session instance

    aaa.mailer._conf['proto'] = 'ssl'
    aaa.mailer._conf['user'] = 'username'
    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP_SSL.assert_called_once_with('localhost', 25)
    assert msession.login.call_count == 1
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 3

# Patch the SMTP_SSL class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP')
def test_send_email_SMTP_STARTTLS(SMTP):
    SMTP.return_value = msession = mock.Mock() # session instance

    aaa.mailer._conf['proto'] = 'starttls'
    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP.assert_called_once_with('localhost', 25)
    assert msession.ehlo.call_count == 2
    assert msession.starttls.call_count == 1
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 5


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_do_not_send_email():
    aaa.mailer._conf['fqdn'] = None  # disable email delivery
    aaa.mailer.send_email('address', 'sbj', 'text')
    aaa.mailer.join()


@with_setup(setup_mockedadmin, teardown_dir)
def test_validate_registration_no_code():
    assert_raises(AAAException, aaa.validate_registration, 'not_a_valid_code')


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_validate_registration(mocked):
    # create registration
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('user_foo', 'pwd', 'a@a.a')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)
    # get the registration code, and run validate_registration
    code = aaa._store.pending_registrations.keys()[0]
    user_data = aaa._store.pending_registrations[code]
    aaa.validate_registration(code)
    assert user_data['username'] in aaa._store.users, "Account should have been added"
    # test login
    login = aaa.login('user_foo', 'pwd')
    assert login == True, "Login must succeed"
    # The registration should have been removed
    assert len(aaa._store.pending_registrations) == 0, repr(aaa._store.pending_registrations)


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_purge_expired_registration(mocked):
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('foo', 'pwd', 'a@a.a')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 1, "The registration should" \
        " be present"
    aaa._purge_expired_registrations()
    assert len(aaa._store.pending_registrations) == 1, "The registration should " \
        "be still there"
    aaa._purge_expired_registrations(exp_time=0)
    assert len(aaa._store.pending_registrations) == 0, "The registration should " \
        "have been removed"


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_prevent_double_registration(mocked):
    # Create two registration requests, then validate them.
    # The first should succeed, the second one fail as the account has been created.

    # create first registration
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('user_foo', 'first_pwd', 'a@a.a')
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)
    first_registration_code = aaa._store.pending_registrations.keys()[0]

    # create second registration
    aaa.register('user_foo', 'second_pwd', 'b@b.b')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 2, repr(aaa._store.pending_registrations)
    registration_codes = aaa._store.pending_registrations.keys()
    if first_registration_code == registration_codes[0]:
        second_registration_code = registration_codes[1]
    else:
        second_registration_code = registration_codes[0]

    # Only the 'admin' account exists
    assert len(aaa._store.users) == 1

    # Run validate_registration with the first registration
    aaa.validate_registration(first_registration_code)
    assert 'user_foo' in aaa._store.users, "Account should have been added"
    assert len(aaa._store.users) == 2

    # After the first registration only one pending registration should be left
    # The registration having 'a@a.a' email address should be gone
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)
    pr_code, pr_data = aaa._store.pending_registrations.items()[0]
    assert pr_data['email_addr'] == 'b@b.b', "Incorrect registration in the datastore"

    # Logging in using the first login should succeed
    login = aaa.login('user_foo', 'first_pwd')
    assert login == True, "Login must succed"
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)

    # Run validate_registration with the second registration code
    # The second registration should fail as the user account exists
    assert_raises(AAAException, aaa.validate_registration, second_registration_code)
    # test login
    login = aaa.login('user_foo', 'second_pwd')
    assert login == False, "Login must fail"


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_no_params(mocked):
    aaa.send_password_reset_email()


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_incorrect_addr(mocked):
    aaa.send_password_reset_email(email_addr='incorrect_addr')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_incorrect_user(mocked):
    aaa.send_password_reset_email(username='bogus_name')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_missing_email_addr(mocked):
    aaa.send_password_reset_email(username='admin')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_incorrect_pair(mocked):
    aaa.send_password_reset_email(username='admin', email_addr='incorrect_addr')


@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_by_email_addr(mocked):
    aaa._store.users['admin']['email_addr'] = 'admin@localhost.local'
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.send_password_reset_email(email_addr='admin@localhost.local')
    os.chdir(old_dir)
    #TODO: add UT


@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_by_username(mocked):
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa._store.users['admin']['email_addr'] = 'admin@localhost.local'
    assert not mocked.called
    aaa.send_password_reset_email(username='admin')
    aaa.mailer.join()
    os.chdir(old_dir)
    assert mocked.called
    assert mocked.call_args[0][0] == 'admin@localhost.local'


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_invalid():
    aaa.reset_password('bogus', 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_timed_out():
    aaa.password_reset_timeout = 0
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_nonexistent_user():
    token = aaa._reset_code('admin_bogus', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


# The following test should fail
# an user can change the password reset timestamp by b64-decoding the token,
# editing the field and b64-encoding it
@SkipTest
@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_mangled_timestamp():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    tstamp = str(int(tstamp) + 100)
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_mangled_username():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    username += "mangled_username"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_mangled_email():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    email_addr += "mangled_email"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset():
    old_dir = os.getcwd()
    os.chdir(testdir)
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')
    os.chdir(old_dir)

########NEW FILE########
__FILENAME__ = testutils
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Unit testing - utility functions.
#
import bottle
import os
import shutil
import sys
import tempfile


def pick_temp_directory():
    """Select a temporary directory for the test files.
    Set the tmproot global variable.
    """
    if os.environ.get('TRAVIS', False):
        return tempfile.mkdtemp()

    if sys.platform == 'linux2':
        # In-memory filesystem allows faster testing.
        return "/dev/shm"

    return tempfile.mkdtemp()


def purge_temp_directory(test_dir):
    """Remove the test directory"""
    assert test_dir
    shutil.rmtree(test_dir)

def assert_is_redirect(e, path):
    """Check if an HTTPResponse is a redirect.

    :param path: relative path without leading slash.
    :type path: str
    """
    assert isinstance(e, bottle.HTTPResponse), "Incorrect exception type passed to assert_is_redirect"
    assert e.status_code == 302, "HTTPResponse status should be 302 but is '%s'" % e.status
    redir_location = e.headers['Location'].rsplit('/', 1)[1]
    assert redir_location == path, "Redirected to %s instead of %s" % (redir_location, path)




########NEW FILE########
__FILENAME__ = test_flask
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Unit testing
#

from base64 import b64encode, b64decode
from nose import SkipTest
from nose.tools import assert_raises, raises, with_setup
from time import time
import mock
import os
import shutil

from cork import Cork, JsonBackend, AAAException, AuthException
from cork import Mailer
from cork.base_backend import BackendIOException
import testutils

testdir = None  # Test directory
aaa = None  # global Cork instance
cookie_name = None  # global variable to track cookie status

tmproot = testutils.pick_temp_directory()


class RoAttrDict(dict):
    """Read-only attribute-accessed dictionary.
    Used to mock beaker's session objects
    """
    def __getattr__(self, name):
        return self[name]


class MockedAdminCork(Cork):
    """Mocked module where the current user is always 'admin'"""
    @property
    def _beaker_session(self):
        return RoAttrDict(username='admin')

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


class MockedUnauthenticatedCork(Cork):
    """Mocked module where the current user not set"""
    @property
    def _beaker_session(self):
        return RoAttrDict()

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


def setup_empty_dir():
    """Setup test directory without JSON files"""
    global testdir
    tstamp = "%f" % time()
    testdir = "%s/fl_%s" % (tmproot, tstamp)
    os.mkdir(testdir)
    os.mkdir(testdir + '/view')
    print("setup done in %s" % testdir)


def setup_dir():
    """Setup test directory with valid JSON files"""
    global testdir
    tstamp = "%f" % time()
    testdir = "%s/fl_%s" % (tmproot, tstamp)
    os.mkdir(testdir)
    os.mkdir(testdir + '/views')
    with open("%s/users.json" % testdir, 'w') as f:
        f.write("""{"admin": {"email_addr": null, "desc": null, "role": "admin", "hash": "69f75f38ac3bfd6ac813794f3d8c47acc867adb10b806e8979316ddbf6113999b6052efe4ba95c0fa9f6a568bddf60e8e5572d9254dbf3d533085e9153265623", "creation_date": "2012-04-09 14:22:27.075596"}}""")
    with open("%s/roles.json" % testdir, 'w') as f:
        f.write("""{"special": 200, "admin": 100, "user": 50}""")
    with open("%s/register.json" % testdir, 'w') as f:
        f.write("""{}""")
    with open("%s/views/registration_email.tpl" % testdir, 'w') as f:
        f.write("""Username:{{username}} Email:{{email_addr}} Code:{{registration_code}}""")
    with open("%s/views/password_reset_email.tpl" % testdir, 'w') as f:
        f.write("""Username:{{username}} Email:{{email_addr}} Code:{{reset_code}}""")
    print("setup done in %s" % testdir)


def setup_mockedadmin():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    setup_dir()
    aaa = MockedAdminCork(testdir, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None


def setup_mocked_unauthenticated():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    setup_dir()
    aaa = MockedUnauthenticatedCork(testdir)
    cookie_name = None


def teardown_dir():
    global cookie_name
    global testdir
    if testdir:
        shutil.rmtree(testdir)
        testdir = None
    cookie_name = None


@with_setup(setup_dir, teardown_dir)
def test_init():
    Cork(testdir)


@with_setup(setup_dir, teardown_dir)
def test_initialize_storage():
    jb = JsonBackend(testdir, initialize=True)
    Cork(backend=jb)
    with open("%s/users.json" % testdir) as f:
        assert f.readlines() == ['{}']
    with open("%s/roles.json" % testdir) as f:
        assert f.readlines() == ['{}']
    with open("%s/register.json" % testdir) as f:
        assert f.readlines() == ['{}']
    with open("%s/views/registration_email.tpl" % testdir) as f:
        assert f.readlines() == [
            'Username:{{username}} Email:{{email_addr}} Code:{{registration_code}}']
    with open("%s/views/password_reset_email.tpl" % testdir) as f:
        assert f.readlines() == [
            'Username:{{username}} Email:{{email_addr}} Code:{{reset_code}}']


@raises(BackendIOException)
@with_setup(setup_dir, teardown_dir)
def test_unable_to_save():
    bogus_dir = '/___inexisting_directory___'
    Cork(bogus_dir, initialize=True)


@with_setup(setup_mockedadmin, teardown_dir)
def test_mockedadmin():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    assert 'admin' in aaa._store.users, repr(aaa._store.users)

@raises(BackendIOException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_loadjson_missing_file():
    aaa._store._loadjson('nonexistent_file', {})

@raises(BackendIOException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_loadjson_broken_file():
    with open(testdir + '/broken_file.json', 'w') as f:
        f.write('-----')
    aaa._store._loadjson('broken_file', {})


@with_setup(setup_mockedadmin, teardown_dir)
def test_loadjson_unchanged():
    # By running _refresh with unchanged files the files should not be reloaded
    mtimes = aaa._store._mtimes
    aaa._store._refresh()
    # The test simply ensures that no mtimes have been updated
    assert mtimes == aaa._store._mtimes


# Test PBKDF2-based password hashing

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_known_hash():
    salt = 's' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    assert shash == 'cHNzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzax44AxQgK6uD9q1YWxLos1ispCe1Z7T7pOFK1PwdWEs='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_known_hash_2():
    salt = '\0' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    assert shash == 'cAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/8Uh4pyEOHoRz4j0lDzAmqb7Dvmo8GpeXwiKTDsuYFw='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_known_hash_3():
    salt = 'x' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    assert shash == 'cHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4MEaIU5Op97lmvwX5NpVSTBP8jg8OlrN7c2K8K8tnNks='

@raises(AssertionError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_incorrect_hash_len():
    salt = 'x' * 31 # Incorrect length
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt)

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_incorrect_hash_value():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_PBKDF2_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt)
    assert hash1 != hash2, "Hash collision"

# Test scrypt-based password hashing

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt():
    shash = aaa._hash('user_foo', 'bogus_pwd', algo='scrypt')
    assert len(shash) == 132, "hash length should be 132 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_known_hash():
    salt = 's' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    assert shash == 'c3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3NzeLt/2Ta8vJOVqimNpN9G1WWxN1hxlUOJDPgH+0wqPpG20XQHFHLlksDIUo2BL4P8BMLBZj7F+cq6UP6pc304LQ=='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_known_hash_2():
    salt = '\0' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    assert shash == 'cwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAmu5jQskr2/yX13Yxmc4TYL0MIuSxwo41SVJwn/QueiDdLGkNaEsxlKL37i98YofXxs8xJJAJlC3Xj/9Nx0RNBw=='

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_known_hash_3():
    salt = 'x' * 32
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    assert shash == 'c3h4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4yKuT1e8lovFZnaaOctivIvYBPkLoKDXX72kf5/nRuGIgyyhiKxxKE4LVYFKFCeVNPQM5m/+LulQkWhO0aB89lA=='

@raises(AssertionError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_incorrect_hash_len():
    salt = 'x' * 31 # Incorrect length
    shash = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')

@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_incorrect_hash_value():
    shash = aaa._hash('user_foo', 'bogus_pwd', algo='scrypt')
    assert len(shash) == 132, "hash length should be 132 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"


@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_scrypt_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt, algo='scrypt')
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt, algo='scrypt')
    assert hash1 != hash2, "Hash collision"

# Test password hashing for inexistent algorithms

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_bogus_algo():
    aaa._hash('user_foo', 'bogus_pwd', algo='bogus_algo')

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_password_hashing_bogus_algo_during_verify():
    # Incorrect hash type (starts with "X")
    shash = b64encode('X' + 'bogusstring')
    aaa._verify_password('user_foo', 'bogus_pwd', shash)

# End of password hashing tests


@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_create_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_role, 'user', 33)


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_existing_role():
    assert_raises(AAAException, aaa.create_role, 'user', 33)


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_create_role_with_incorrect_level():
    aaa.create_role('new_user', 'not_a_number')


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_role():
    assert len(aaa._store.roles) == 3, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._roles_fname)
    with open(fname) as f:
        data = f.read()
        assert 'user33' in data, repr(data)

@SkipTest
@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_create_empty_role():
    aaa.create_role('', 42)

@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_delete_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_role, 'user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_delete_nonexistent_role():
    assert_raises(AAAException, aaa.delete_role, 'user123')


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_delete_role():
    assert len(aaa._store.roles) == 3, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._roles_fname)
    with open(fname) as f:
        data = f.read()
        assert 'user33' in data, repr(data)
    assert aaa._store.roles['user33'] == 33
    aaa.delete_role('user33')
    assert len(aaa._store.roles) == 3, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, teardown_dir)
def test_list_roles():
    roles = list(aaa.list_roles())
    assert len(roles) == 3, "Incorrect. Users are: %s" % repr(aaa._store.roles)


@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_create_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_user, 'phil', 'user', 'hunter123')

@with_setup(setup_mockedadmin, teardown_dir)
def test_create_existing_user():
    assert_raises(AAAException, aaa.create_user, 'admin', 'admin', 'bogus')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_create_user_with_wrong_role():
    aaa.create_user('admin2', 'nonexistent_role', 'bogus')


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.create_user('phil', 'user', 'user')
    assert len(aaa._store.users) == 2, repr(aaa._store.users)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._users_fname)
    with open(fname) as f:
        data = f.read()
        assert 'phil' in data, repr(data)


@with_setup(setup_mockedadmin, teardown_dir)
def test_unauth_delete_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_user, 'phil')


@with_setup(setup_mockedadmin, teardown_dir)
def test_delete_nonexistent_user():
    assert_raises(AAAException, aaa.delete_user, 'not_an_user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_delete_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.delete_user('admin')
    assert len(aaa._store.users) == 0, repr(aaa._store.users)
    fname = "%s/%s.json" % (aaa._store._directory, aaa._store._users_fname)
    with open(fname) as f:
        data = f.read()
        assert 'admin' not in data, "'admin' must not be in %s" % repr(data)


@with_setup(setup_mockedadmin, teardown_dir)
def test_list_users():
    users = list(aaa.list_users())
    assert len(users) == 1, "Incorrect. Users are: %s" % repr(aaa._store.users)


@with_setup(setup_mockedadmin, teardown_dir)
def test_failing_login():
    login = aaa.login('phil', 'hunter123')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, teardown_dir)
def test_login_nonexistent_user_empty_password():
    login = aaa.login('IAmNotHome', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, teardown_dir)
def test_login_existing_user_empty_password():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, teardown_dir)
def test_create_and_validate_user():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    global cookie_name
    assert cookie_name == 'phil'


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_failing_username():
    # The user exists, but I'm 'admin'
    aaa.create_user('phil', 'user', 'hunter123')
    assert_raises(AuthException, aaa.require, username='phil')


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_nonexistent_username():
    assert_raises(AAAException, aaa.require, username='no_such_user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_failing_role_fixed():
    assert_raises(AuthException, aaa.require, role='user', fixed_role=True)


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_require_missing_parameter():
    aaa.require(fixed_role=True)


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_nonexistent_role():
    assert_raises(AAAException, aaa.require, role='clown')


@with_setup(setup_mockedadmin, teardown_dir)
def test_require_failing_role():
    # Requesting level >= 100
    assert_raises(AuthException, aaa.require, role='special')


@with_setup(setup_mockedadmin, teardown_dir)
def test_successful_require_role():
    aaa.require(username='admin')
    aaa.require(username='admin', role='admin')
    aaa.require(username='admin', role='admin', fixed_role=True)
    aaa.require(username='admin', role='user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_authenticated_is_not__anonymous():
    assert not aaa.user_is_anonymous


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_nonexistent_role():
    assert_raises(AAAException, aaa.current_user.update, role='clown')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_update_nonexistent_user():
    aaa._store.users.pop('admin')
    aaa.current_user.update(role='user')


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_role():
    aaa.current_user.update(role='user')
    assert aaa._store.users['admin']['role'] == 'user'


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_pwd():
    aaa.current_user.update(pwd='meow')


@with_setup(setup_mockedadmin, teardown_dir)
def test_update_email():
    aaa.current_user.update(email_addr='foo')
    assert aaa._store.users['admin']['email_addr'] == 'foo'


@raises(AAAException)
@with_setup(setup_mocked_unauthenticated, teardown_dir)
def test_get_current_user_unauth():
    aaa.current_user['username']


@with_setup(setup_mocked_unauthenticated, teardown_dir)
def test_unauth_is_anonymous():
    assert aaa.user_is_anonymous


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_get_current_user_nonexistent():
    # The current user 'admin' is not in the user table
    aaa._store.users.pop('admin')
    aaa.current_user


@with_setup(setup_mockedadmin, teardown_dir)
def test_get_nonexistent_user():
    assert aaa.user('nonexistent_user') is None


@with_setup(setup_mockedadmin, teardown_dir)
def test_get_user_description_field():
    admin = aaa.user('admin')
    for field in ['description', 'email_addr']:
        assert field in admin.__dict__


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_user():
    assert_raises(AssertionError, aaa.register, None, 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_pwd():
    assert_raises(AssertionError, aaa.register, 'foo', None, 'a@a.a')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_email():
    assert_raises(AssertionError, aaa.register, 'foo', 'pwd', None)


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_already_existing():
    assert_raises(AAAException, aaa.register, 'admin', 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_no_role():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='clown')


@with_setup(setup_mockedadmin, teardown_dir)
def test_register_role_too_high():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='admin')


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_register(mocked):
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('foo', 'pwd', 'a@a.a')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_1():
    c = aaa.mailer._parse_smtp_url('')
    assert c['proto'] == 'smtp'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == ''
    assert c['port'] == 25


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_2():
    c = aaa.mailer._parse_smtp_url('starttls://foo')
    assert c['proto'] == 'starttls'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == 'foo'
    assert c['port'] == 25

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_3():
    c = aaa.mailer._parse_smtp_url('foo:443')
    assert c['proto'] == 'smtp'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_4():
    c = aaa.mailer._parse_smtp_url('ssl://user:pass@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'user'
    assert c['pass'] == 'pass'
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_5():
    c = aaa.mailer._parse_smtp_url('smtp://smtp.magnet.ie')
    assert c['proto'] == 'smtp'
    assert c['user'] == None
    assert c['pass'] == None
    assert c['fqdn'] == 'smtp.magnet.ie'
    assert c['port'] == 25


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_email_as_username_no_password():
    # the username contains an at sign '@'
    c = aaa.mailer._parse_smtp_url('ssl://us.er@somewhere.net@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'us.er@somewhere.net', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == None
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_email_as_username():
    # the username contains an at sign '@'
    c = aaa.mailer._parse_smtp_url('ssl://us.er@somewhere.net:pass@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'us.er@somewhere.net', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == 'pass'
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_at_sign_in_password():
    # the password contains at signs '@'
    c = aaa.mailer._parse_smtp_url('ssl://username:pass@w@rd@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'username', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == 'pass@w@rd', \
        "Password is incorrectly parsed as '%s'" % c['pass']
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443


@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_email_as_username_2():
    # both the username and the password contains an at sign '@'
    c = aaa.mailer._parse_smtp_url('ssl://us.er@somewhere.net:pass@word@foo:443/')
    assert c['proto'] == 'ssl'
    assert c['user'] == 'us.er@somewhere.net', \
        "Username is incorrectly parsed as '%s'" % c['user']
    assert c['pass'] == 'pass@word', \
        "Password is incorrectly parsed as '%s'" % c['pass']
    assert c['fqdn'] == 'foo'
    assert c['port'] == 443

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_port():
    c = aaa.mailer._parse_smtp_url(':99999')

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_port_len():
    c = aaa.mailer._parse_smtp_url(':123456')

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_len():
    c = aaa.mailer._parse_smtp_url('a' * 256)

@raises(RuntimeError)
@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_incorrect_URL_syntax():
    c = aaa.mailer._parse_smtp_url('::')

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_IPv4():
    c = aaa.mailer._parse_smtp_url('127.0.0.1')
    assert c['fqdn'] == '127.0.0.1'

@with_setup(setup_mockedadmin, teardown_dir)
def test_smtp_url_parsing_IPv6():
    c = aaa.mailer._parse_smtp_url('[2001:0:0123:4567:89ab:cdef]')
    assert c['fqdn'] == '[2001:0:0123:4567:89ab:cdef]'


# Patch the SMTP class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP')
def test_send_email_SMTP(SMTP):
    SMTP.return_value = msession = mock.Mock() # session instance

    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP.assert_called_once_with('localhost', 25)
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 2

# Patch the SMTP_SSL class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP_SSL')
def test_send_email_SMTP_SSL(SMTP_SSL):
    SMTP_SSL.return_value = msession = mock.Mock() # session instance

    aaa.mailer._conf['proto'] = 'ssl'
    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP_SSL.assert_called_once_with('localhost', 25)
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 2

# Patch the SMTP_SSL class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP_SSL')
def test_send_email_SMTP_SSL_with_login(SMTP_SSL):
    SMTP_SSL.return_value = msession = mock.Mock() # session instance

    aaa.mailer._conf['proto'] = 'ssl'
    aaa.mailer._conf['user'] = 'username'
    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP_SSL.assert_called_once_with('localhost', 25)
    assert msession.login.call_count == 1
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 3

# Patch the SMTP_SSL class to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch('cork.cork.SMTP')
def test_send_email_SMTP_STARTTLS(SMTP):
    SMTP.return_value = msession = mock.Mock() # session instance

    aaa.mailer._conf['proto'] = 'starttls'
    aaa.mailer.send_email('address', ' sbj', 'text')
    aaa.mailer.join()

    SMTP.assert_called_once_with('localhost', 25)
    assert msession.ehlo.call_count == 2
    assert msession.starttls.call_count == 1
    assert msession.sendmail.call_count == 1
    assert msession.quit.call_count == 1
    assert len(msession.method_calls) == 5


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_do_not_send_email():
    aaa.mailer._conf['fqdn'] = None  # disable email delivery
    aaa.mailer.send_email('address', 'sbj', 'text')
    aaa.mailer.join()


@with_setup(setup_mockedadmin, teardown_dir)
def test_validate_registration_no_code():
    assert_raises(AAAException, aaa.validate_registration, 'not_a_valid_code')


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_validate_registration(mocked):
    # create registration
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('user_foo', 'pwd', 'a@a.a')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)
    # get the registration code, and run validate_registration
    code = aaa._store.pending_registrations.keys()[0]
    user_data = aaa._store.pending_registrations[code]
    aaa.validate_registration(code)
    assert user_data['username'] in aaa._store.users, "Account should have been added"
    # test login
    login = aaa.login('user_foo', 'pwd')
    assert login == True, "Login must succeed"
    # The registration should have been removed
    assert len(aaa._store.pending_registrations) == 0, repr(aaa._store.pending_registrations)


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_purge_expired_registration(mocked):
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('foo', 'pwd', 'a@a.a')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 1, "The registration should" \
        " be present"
    aaa._purge_expired_registrations()
    assert len(aaa._store.pending_registrations) == 1, "The registration should " \
        "be still there"
    aaa._purge_expired_registrations(exp_time=0)
    assert len(aaa._store.pending_registrations) == 0, "The registration should " \
        "have been removed"


# Patch the mailer _send() method to prevent network interactions
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_prevent_double_registration(mocked):
    # Create two registration requests, then validate them.
    # The first should succeed, the second one fail as the account has been created.

    # create first registration
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.register('user_foo', 'first_pwd', 'a@a.a')
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)
    first_registration_code = aaa._store.pending_registrations.keys()[0]

    # create second registration
    aaa.register('user_foo', 'second_pwd', 'b@b.b')
    os.chdir(old_dir)
    assert len(aaa._store.pending_registrations) == 2, repr(aaa._store.pending_registrations)
    registration_codes = aaa._store.pending_registrations.keys()
    if first_registration_code == registration_codes[0]:
        second_registration_code = registration_codes[1]
    else:
        second_registration_code = registration_codes[0]

    # Only the 'admin' account exists
    assert len(aaa._store.users) == 1

    # Run validate_registration with the first registration
    aaa.validate_registration(first_registration_code)
    assert 'user_foo' in aaa._store.users, "Account should have been added"
    assert len(aaa._store.users) == 2

    # After the first registration only one pending registration should be left
    # The registration having 'a@a.a' email address should be gone
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)
    pr_code, pr_data = aaa._store.pending_registrations.items()[0]
    assert pr_data['email_addr'] == 'b@b.b', "Incorrect registration in the datastore"

    # Logging in using the first login should succeed
    login = aaa.login('user_foo', 'first_pwd')
    assert login == True, "Login must succed"
    assert len(aaa._store.pending_registrations) == 1, repr(aaa._store.pending_registrations)

    # Run validate_registration with the second registration code
    # The second registration should fail as the user account exists
    assert_raises(AAAException, aaa.validate_registration, second_registration_code)
    # test login
    login = aaa.login('user_foo', 'second_pwd')
    assert login == False, "Login must fail"


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_no_params(mocked):
    aaa.send_password_reset_email()


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_incorrect_addr(mocked):
    aaa.send_password_reset_email(email_addr='incorrect_addr')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_incorrect_user(mocked):
    aaa.send_password_reset_email(username='bogus_name')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_missing_email_addr(mocked):
    aaa.send_password_reset_email(username='admin')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_incorrect_pair(mocked):
    aaa.send_password_reset_email(username='admin', email_addr='incorrect_addr')


@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_by_email_addr(mocked):
    aaa._store.users['admin']['email_addr'] = 'admin@localhost.local'
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa.send_password_reset_email(email_addr='admin@localhost.local')
    os.chdir(old_dir)
    #TODO: add UT


@with_setup(setup_mockedadmin, teardown_dir)
@mock.patch.object(Mailer, '_send')
def test_send_password_reset_email_by_username(mocked):
    old_dir = os.getcwd()
    os.chdir(testdir)
    aaa._store.users['admin']['email_addr'] = 'admin@localhost.local'
    assert not mocked.called
    aaa.send_password_reset_email(username='admin')
    aaa.mailer.join()
    os.chdir(old_dir)
    assert mocked.called
    assert mocked.call_args[0][0] == 'admin@localhost.local'


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_invalid():
    aaa.reset_password('bogus', 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_timed_out():
    aaa.password_reset_timeout = 0
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


@raises(AAAException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_nonexistent_user():
    token = aaa._reset_code('admin_bogus', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


# The following test should fail
# an user can change the password reset timestamp by b64-decoding the token,
# editing the field and b64-encoding it
@SkipTest
@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_mangled_timestamp():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    tstamp = str(int(tstamp) + 100)
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_mangled_username():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    username += "mangled_username"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset_mangled_email():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    email_addr += "mangled_email"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@with_setup(setup_mockedadmin, teardown_dir)
def test_perform_password_reset():
    old_dir = os.getcwd()
    os.chdir(testdir)
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')
    os.chdir(old_dir)

########NEW FILE########
__FILENAME__ = test_functional
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Functional test using Json backend
#
# Requires WebTest http://webtest.pythonpaste.org/
#
# Run as: nosetests functional_test.py
#

from nose import SkipTest
from time import time
from datetime import datetime
from webtest import TestApp
import glob
import json
import os
import shutil

import testutils
from cork import Cork

REDIR = '302 Found'

class Test(object):
    def __init__(self):
        self._tmpdir = None
        self._tmproot = None
        self._app = None
        self._starting_dir = os.getcwd()

    def populate_conf_directory(self):
        """Populate a directory with valid configuration files, to be run just once
        The files are not modified by each test
        """
        self._tmpdir = os.path.join(self._tmproot, "cork_functional_test_source")

        # only do this once, as advertised
        if os.path.exists(self._tmpdir):
            return

        os.mkdir(self._tmpdir)
        os.mkdir(self._tmpdir + "/example_conf")

        cork = Cork(os.path.join(self._tmpdir, "example_conf"), initialize=True)

        cork._store.roles['admin'] = 100
        cork._store.roles['editor'] = 60
        cork._store.roles['user'] = 50
        cork._store.save_roles()

        tstamp = str(datetime.utcnow())
        username = password = 'admin'
        cork._store.users[username] = {
            'role': 'admin',
            'hash': cork._hash(username, password),
            'email_addr': username + '@localhost.local',
            'desc': username + ' test user',
            'creation_date': tstamp
        }
        username = password = ''
        cork._store.users[username] = {
            'role': 'user',
            'hash': cork._hash(username, password),
            'email_addr': username + '@localhost.local',
            'desc': username + ' test user',
            'creation_date': tstamp
        }
        cork._store.save_users()

    def remove_temp_dir(self):
        p = os.path.join(self._tmproot, 'cork_functional_test_wd')
        for f in glob.glob('%s*' % p):
            #shutil.rmtree(f)
            pass

    @classmethod
    def setUpClass(cls):
        print("Setup class")

    def setup(self):
        # create test dir and populate it using the example files

        # save the directory where the unit testing has been run
        if self._starting_dir is None:
            self._starting_dir = os.getcwd()

        # create json files to be used by Cork
        self._tmproot = testutils.pick_temp_directory()
        assert self._tmproot is not None

        # purge the temporary test directory
        self.remove_temp_dir()

        self.populate_temp_dir()
        self.create_app_instance()
        self._app.reset()
        print("Reset done")
        print("Setup completed")

    def populate_temp_dir(self):
        """populate the temporary test dir"""
        assert self._tmproot is not None
        assert self._tmpdir is None

        tstamp = str(time())[5:]
        self._tmpdir = os.path.join(self._tmproot, "cork_functional_test_wd_%s" % tstamp)

        try:
            os.mkdir(self._tmpdir)
        except OSError:
            # The directory is already there, purge it
            print("Deleting %s" % self._tmpdir)
            shutil.rmtree(self._tmpdir)
            os.mkdir(self._tmpdir)

            #p = os.path.join(self._tmproot, 'cork_functional_test_wd')
            #for f in glob.glob('%s*' % p):
            #    shutil.rmtree(f)

        # copy the needed files
        shutil.copytree(
            os.path.join(self._starting_dir, 'tests/example_conf'),
            os.path.join(self._tmpdir, 'example_conf')
        )
        shutil.copytree(
            os.path.join(self._starting_dir, 'tests/views'),
            os.path.join(self._tmpdir, 'views')
        )

        # change to the temporary test directory
        # cork relies on this being the current directory
        os.chdir(self._tmpdir)

        print("Test directory set up")

    def create_app_instance(self):
        """create TestApp instance"""
        assert self._app is None
        import simple_webapp
        self._bottle_app = simple_webapp.app
        self._app = TestApp(self._bottle_app)
        print("Test App created")

    def teardown(self):
        print("Doing teardown")
        try:
            self._app.post('/logout')
        except:
            pass

        # drop the cookie
        self._app.reset()
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"
        # drop the cookie
        self._app.reset()

        #assert self._app.get('/admin').status != '200 OK'
        os.chdir(self._starting_dir)
        #if self._tmproot is not None:
        #    testutils.purge_temp_directory(self._tmproot)

        self._app.app.options['timeout'] = self._default_timeout
        self._app = None
        self._tmproot = None
        self._tmpdir = None
        print("Teardown done")

    def setup(self):
        # create test dir and populate it using the example files

        # save the directory where the unit testing has been run
        if self._starting_dir is None:
            self._starting_dir = os.getcwd()

        # create json files to be used by Cork
        self._tmproot = testutils.pick_temp_directory()
        assert self._tmproot is not None

        # purge the temporary test directory
        self.remove_temp_dir()

        self.populate_temp_dir()
        self.create_app_instance()
        self._app.reset()
        print("Reset done")
        self._default_timeout = self._app.app.options['timeout']
        print("Setup completed")

    def assert_200(self, path, match):
        """Assert that a page returns 200"""
        p = self._app.get(path)
        assert p.status_int == 200, "Status: %d, Location: %s" % \
            (p.status_int, p.location)

        if match is not None:
            assert match in p.body, "'%s' not found in body: '%s'" % (match, p.body)

        return p

    def assert_redirect(self, page, redir_page, post=None):
        """Assert that a page redirects to another one"""

        # perform GET or POST
        if post is None:
            p = self._app.get(page, status=302)
        else:
            assert isinstance(post, dict)
            p = self._app.post(page, post, status=302)

        dest = p.location.split(':80/')[-1]
        dest = "/%s" % dest
        assert dest == redir_page, "%s redirects to %s instead of %s" % \
            (page, dest, redir_page)

        return p

    def login_as_admin(self):
        """perform log in"""
        assert self._app is not None
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"

        self.assert_200('/login', 'Please insert your credentials')
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"

        self.assert_redirect('/admin', '/sorry_page')

        self.assert_200('/user_is_anonymous', 'True')
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"

        post = {'username': 'admin', 'password': 'admin'}
        self.assert_redirect('/login', '/', post=post)
        assert 'beaker.session.id' in self._app.cookies, "Cookie not found"

        import bottle
        session = bottle.request.environ.get('beaker.session')
        print("Session from func. test", repr(session))

        self.assert_200('/login', 'Please insert your credentials')


        p = self._app.get('/admin')
        assert 'Welcome' in p.body, repr(p)

        p = self._app.get('/my_role', status=200)
        assert p.status == '200 OK'
        assert p.body == 'admin', "Sta"

        print("Login performed")



    def test_functional_login(self):
        assert self._app
        self._app.get('/admin', status=302)
        self._app.get('/my_role', status=302)

        self.login_as_admin()

        # fetch a page successfully
        r = self._app.get('/admin')
        assert r.status == '200 OK', repr(r)

    def test_login_existing_user_none_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': None})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_nonexistent_user_none_password(self):
        p = self._app.post('/login', {'username': 'IAmNotHere', 'password': None})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_existing_user_empty_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': ''})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_nonexistent_user_empty_password(self):
        p = self._app.post('/login', {'username': 'IAmNotHere', 'password': ''})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_existing_user_wrong_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': 'BogusPassword'})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_functional_login_logout(self):
        # Incorrect login
        p = self._app.post('/login', {'username': 'admin', 'password': 'BogusPassword'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

        # log in and get a cookie
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # fetch a page successfully
        assert self._app.get('/admin').status == '200 OK', "Admin page should be served"

        # log out
        assert self._app.get('/logout').status == REDIR

        # drop the cookie
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # fetch the same page, unsuccessfully
        assert self._app.get('/admin').status == REDIR

    def test_functional_user_creation_login_deletion(self):
        assert self._app.cookies == {}, "The cookie should be not set"

        # Log in as Admin
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # Create new user
        username = 'BrandNewUser'
        password = '42IsTheAnswer'
        ret = self._app.post('/create_user', {
            'username': username,
            'password': password,
            'role': 'user'
        })
        retj = json.loads(ret.body)
        assert 'ok' in retj and retj['ok'] == True, "Failed user creation: %s" % \
            ret.body

        # log out
        assert self._app.get('/logout').status == REDIR
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # Log in as user
        p = self._app.post('/login', {'username': username, 'password': password})
        assert p.status == REDIR and p.location == 'http://localhost:80/', \
            "Failed user login"

        # log out
        assert self._app.get('/logout').status == REDIR
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # Log in as user with empty password
        p = self._app.post('/login', {'username': username, 'password': ''})
        assert p.status == REDIR and p.location == 'http://localhost:80/login', \
            "User login should fail"
        assert self._app.cookies == {}, "The cookie should not be set"

        # Log in as Admin, again
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # Delete the user
        ret = self._app.post('/delete_user', {
            'username': username,
        })
        retj = json.loads(ret.body)
        assert 'ok' in retj and retj['ok'] == True, "Failed user deletion: %s" % \
            ret.body

    #def test_functional_user_registration(self):
    #    assert self._app.cookies == {}, "The cookie should be not set"
    #
    #    # Register new user
    #    username = 'BrandNewUser'
    #    password = '42IsTheAnswer'
    #    ret = self._app.post('/register', {
    #        'username': username,
    #        'password': password,
    #        'email_address': 'test@localhost.local'
    #    })

    def test_functionalxxx(self):
        assert self._app is not None

    def test_functional_expiration(self):
        self.login_as_admin()
        r = self._app.get('/admin')
        assert r.status == '200 OK', repr(r)
        # change the cookie expiration in order to expire it
        self._app.app.options['timeout'] = 0
        assert self._app.get('/admin').status == REDIR, "The cookie should have expired"

########NEW FILE########
__FILENAME__ = test_functional_decorated
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Functional test for decorators-based webapp using Json backend
#
# Requires WebTest http://webtest.pythonpaste.org/
#
# Run as: nosetests tests/test_functional_decorated.py
#

from nose import SkipTest
from time import time
from datetime import datetime
from webtest import TestApp
import glob
import json
import os
import shutil

import testutils
from cork import Cork

REDIR = '302 Found'

class Test(object):
    def __init__(self):
        self._tmpdir = None
        self._tmproot = None
        self._app = None
        self._starting_dir = os.getcwd()

    def remove_temp_dir(self):
        p = os.path.join(self._tmproot, 'cork_functional_test_wd')
        for f in glob.glob('%s*' % p):
            #shutil.rmtree(f)
            pass

    @classmethod
    def setUpClass(cls):
        print("Setup class")

    def populate_temp_dir(self):
        """populate the temporary test dir"""
        assert self._tmproot is not None
        assert self._tmpdir is None

        tstamp = str(time())[5:]
        self._tmpdir = os.path.join(self._tmproot, "cork_functional_test_wd_%s" % tstamp)

        try:
            os.mkdir(self._tmpdir)
        except OSError:
            # The directory is already there, purge it
            print("Deleting %s" % self._tmpdir)
            shutil.rmtree(self._tmpdir)
            os.mkdir(self._tmpdir)

            #p = os.path.join(self._tmproot, 'cork_functional_test_wd')
            #for f in glob.glob('%s*' % p):
            #    shutil.rmtree(f)

        # copy the needed files
        shutil.copytree(
            os.path.join(self._starting_dir, 'tests/example_conf'),
            os.path.join(self._tmpdir, 'example_conf')
        )
        shutil.copytree(
            os.path.join(self._starting_dir, 'tests/views'),
            os.path.join(self._tmpdir, 'views')
        )

        # change to the temporary test directory
        # cork relies on this being the current directory
        os.chdir(self._tmpdir)

        print("Test directory set up")

    def create_app_instance(self):
        """create TestApp instance"""
        assert self._app is None
        import simple_webapp_decorated
        self._bottle_app = simple_webapp_decorated.app
        env = {'REMOTE_ADDR': '127.0.0.1'}
        self._app = TestApp(self._bottle_app, extra_environ=env)
        print("Test App created")

    def teardown(self):
        print("Doing teardown")
        try:
            self._app.post('/logout')
        except:
            pass

        # drop the cookie
        self._app.reset()
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"
        # drop the cookie
        self._app.reset()

        #assert self._app.get('/admin').status != '200 OK'
        os.chdir(self._starting_dir)
        #if self._tmproot is not None:
        #    testutils.purge_temp_directory(self._tmproot)

        self._app.app.options['timeout'] = self._default_timeout
        self._app = None
        self._tmproot = None
        self._tmpdir = None
        print("Teardown done")

    def setup(self):
        # create test dir and populate it using the example files

        # save the directory where the unit testing has been run
        if self._starting_dir is None:
            self._starting_dir = os.getcwd()

        # create json files to be used by Cork
        self._tmproot = testutils.pick_temp_directory()
        assert self._tmproot is not None

        # purge the temporary test directory
        self.remove_temp_dir()

        self.populate_temp_dir()
        self.create_app_instance()
        self._app.reset()
        print("Reset done")
        self._default_timeout = self._app.app.options['timeout']
        print("Setup completed")

    def assert_200(self, path, match):
        """Assert that a page returns 200"""
        p = self._app.get(path)
        assert p.status_int == 200, "Status: %d, Location: %s" % \
            (p.status_int, p.location)

        if match is not None:
            assert match in p.body, "'%s' not found in body: '%s'" % (match, p.body)

        return p

    def assert_redirect(self, page, redir_page, post=None):
        """Assert that a page redirects to another one"""

        # perform GET or POST
        if post is None:
            p = self._app.get(page, status=302)
        else:
            assert isinstance(post, dict)
            p = self._app.post(page, post, status=302)

        dest = p.location.split(':80/')[-1]
        dest = "/%s" % dest
        assert dest == redir_page, "%s redirects to %s instead of %s" % \
            (page, dest, redir_page)

        return p

    def login_as_admin(self):
        """perform log in"""
        assert self._app is not None
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"

        self.assert_200('/login', 'Please insert your credentials')
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"

        self.assert_redirect('/admin', '/sorry_page')

        self.assert_200('/user_is_anonymous', 'True')
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"

        post = {'username': 'admin', 'password': 'admin'}
        self.assert_redirect('/login', '/', post=post)
        assert 'beaker.session.id' in self._app.cookies, "Cookie not found"

        self.assert_200('/my_role', 'admin')
        assert 'beaker.session.id' in self._app.cookies, "Cookie not found"

        import bottle
        session = bottle.request.environ.get('beaker.session')
        print("Session from func. test", repr(session))

        self.assert_200('/login', 'Please insert your credentials')


        p = self._app.get('/admin')
        assert 'Welcome' in p.body, repr(p)

        p = self._app.get('/my_role', status=200)
        assert p.status == '200 OK'
        assert p.body == 'admin', "Sta"

        print("Login performed")



    def test_functional_login(self):
        assert self._app
        self._app.get('/admin', status=302)
        self._app.get('/my_role', status=302)

        self.login_as_admin()

        # fetch a page successfully
        r = self._app.get('/admin')
        assert r.status == '200 OK', repr(r)

    def test_login_existing_user_none_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': None})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_nonexistent_user_none_password(self):
        p = self._app.post('/login', {'username': 'IAmNotHere', 'password': None})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_existing_user_empty_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': ''})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_nonexistent_user_empty_password(self):
        p = self._app.post('/login', {'username': 'IAmNotHere', 'password': ''})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_existing_user_wrong_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': 'BogusPassword'})
        assert p.status == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_functional_login_logout(self):
        # Incorrect login
        p = self._app.post('/login', {'username': 'admin', 'password': 'BogusPassword'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

        # log in and get a cookie
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # fetch a page successfully
        assert self._app.get('/admin').status == '200 OK', "Admin page should be served"

        # log out
        assert self._app.get('/logout').status == REDIR

        # drop the cookie
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # fetch the same page, unsuccessfully
        assert self._app.get('/admin').status == REDIR

    def test_functional_user_creation_login_deletion(self):
        assert self._app.cookies == {}, "The cookie should be not set"

        # Log in as Admin
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # Create new user
        username = 'BrandNewUser'
        password = '42IsTheAnswer'
        ret = self._app.post('/create_user', {
            'username': username,
            'password': password,
            'role': 'user'
        })
        retj = json.loads(ret.body)
        assert 'ok' in retj and retj['ok'] == True, "Failed user creation: %s" % \
            ret.body

        # log out
        assert self._app.get('/logout').status == REDIR
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # Log in as user
        p = self._app.post('/login', {'username': username, 'password': password})
        assert p.status == REDIR and p.location == 'http://localhost:80/', \
            "Failed user login"

        # log out
        assert self._app.get('/logout').status == REDIR
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # Log in as user with empty password
        p = self._app.post('/login', {'username': username, 'password': ''})
        assert p.status == REDIR and p.location == 'http://localhost:80/login', \
            "User login should fail"
        assert self._app.cookies == {}, "The cookie should not be set"

        # Log in as Admin, again
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # Delete the user
        ret = self._app.post('/delete_user', {
            'username': username,
        })
        retj = json.loads(ret.body)
        assert 'ok' in retj and retj['ok'] == True, "Failed user deletion: %s" % \
            ret.body

    #def test_functional_user_registration(self):
    #    assert self._app.cookies == {}, "The cookie should be not set"
    #
    #    # Register new user
    #    username = 'BrandNewUser'
    #    password = '42IsTheAnswer'
    #    ret = self._app.post('/register', {
    #        'username': username,
    #        'password': password,
    #        'email_address': 'test@localhost.local'
    #    })

    def test_functionalxxx(self):
        assert self._app is not None

    def test_functional_expiration(self):
        self.login_as_admin()
        r = self._app.get('/admin')
        assert r.status == '200 OK', repr(r)
        # change the cookie expiration in order to expire it
        self._app.app.options['timeout'] = 0
        assert self._app.get('/admin').status == REDIR, "The cookie should have expired"

########NEW FILE########
__FILENAME__ = test_functional_flask
# Cork - Authentication module for the Flask web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Functional test using Json backend
#
# Requires WebTest http://webtest.pythonpaste.org/
#
# Run as: nosetests functional_test.py
#

from nose import SkipTest
from time import time
from datetime import datetime, timedelta
from webtest import TestApp
import glob
import json
import os
import shutil

import testutils
from cork import FlaskCork

REDIR = 302

class Test(object):
    def __init__(self):
        self._tmpdir = None
        self._tmproot = None
        self._app = None
        self._starting_dir = os.getcwd()

    def populate_conf_directory(self):
        """Populate a directory with valid configuration files, to be run just once
        The files are not modified by each test
        """
        self._tmpdir = os.path.join(self._tmproot, "cork_functional_test_source")

        # only do this once, as advertised
        if os.path.exists(self._tmpdir):
            return

        os.mkdir(self._tmpdir)
        os.mkdir(self._tmpdir + "/example_conf")

        cork = FlaskCork(os.path.join(self._tmpdir, "example_conf"), initialize=True)

        cork._store.roles['admin'] = 100
        cork._store.roles['editor'] = 60
        cork._store.roles['user'] = 50
        cork._store.save_roles()

        tstamp = str(datetime.utcnow())
        username = password = 'admin'
        cork._store.users[username] = {
            'role': 'admin',
            'hash': cork._hash(username, password),
            'email_addr': username + '@localhost.local',
            'desc': username + ' test user',
            'creation_date': tstamp
        }
        username = password = ''
        cork._store.users[username] = {
            'role': 'user',
            'hash': cork._hash(username, password),
            'email_addr': username + '@localhost.local',
            'desc': username + ' test user',
            'creation_date': tstamp
        }
        cork._store.save_users()

    def remove_temp_dir(self):
        p = os.path.join(self._tmproot, 'cork_functional_test_wd')
        for f in glob.glob('%s*' % p):
            #shutil.rmtree(f)
            pass

    @classmethod
    def setUpClass(cls):
        print("Setup class")

    def setup(self):
        # create test dir and populate it using the example files

        # save the directory where the unit testing has been run
        if self._starting_dir is None:
            self._starting_dir = os.getcwd()

        # create json files to be used by Cork
        self._tmproot = testutils.pick_temp_directory()
        assert self._tmproot is not None

        # purge the temporary test directory
        self.remove_temp_dir()

        self.populate_temp_dir()
        self.create_app_instance()
        self._app.reset()
        print("Reset done")
        print("Setup completed")

    def populate_temp_dir(self):
        """populate the temporary test dir"""
        assert self._tmproot is not None
        assert self._tmpdir is None

        tstamp = str(time())[5:]
        self._tmpdir = os.path.join(self._tmproot, "cork_functional_test_wd_%s" % tstamp)

        try:
            os.mkdir(self._tmpdir)
        except OSError:
            # The directory is already there, purge it
            print("Deleting %s" % self._tmpdir)
            shutil.rmtree(self._tmpdir)
            os.mkdir(self._tmpdir)

            #p = os.path.join(self._tmproot, 'cork_functional_test_wd')
            #for f in glob.glob('%s*' % p):
            #    shutil.rmtree(f)

        # copy the needed files
        shutil.copytree(
            os.path.join(self._starting_dir, 'tests/example_conf'),
            os.path.join(self._tmpdir, 'example_conf')
        )
        shutil.copytree(
            os.path.join(self._starting_dir, 'tests/views'),
            os.path.join(self._tmpdir, 'views')
        )

        # change to the temporary test directory
        # cork relies on this being the current directory
        os.chdir(self._tmpdir)

        print("Test directory set up")

    def create_app_instance(self):
        """create TestApp instance"""
        assert self._app is None
        import simple_webapp_flask
        self._bottle_app = simple_webapp_flask.app
        self._app = TestApp(self._bottle_app)
        #simple_webapp_flask.flask.session.secret_key = 'bogus'
        simple_webapp_flask.SECRET_KEY = 'bogus'
        print("Test App created")

    def teardown(self):
        print("Doing teardown")
        try:
            self._app.post('/logout')
        except:
            pass

        # drop the cookie
        self._app.reset()
        assert 'beaker.session.id' not in self._app.cookies, "Unexpected cookie found"
        # drop the cookie
        self._app.reset()

        #assert self._app.get('/admin').status != '200 OK'
        os.chdir(self._starting_dir)
        #if self._tmproot is not None:
        #    testutils.purge_temp_directory(self._tmproot)

        self._app.app.options['timeout'] = self._default_timeout
        self._app = None
        self._tmproot = None
        self._tmpdir = None
        print("Teardown done")

    def setup(self):
        # create test dir and populate it using the example files

        # save the directory where the unit testing has been run
        if self._starting_dir is None:
            self._starting_dir = os.getcwd()

        # create json files to be used by Cork
        self._tmproot = testutils.pick_temp_directory()
        assert self._tmproot is not None

        # purge the temporary test directory
        self.remove_temp_dir()

        self.populate_temp_dir()
        self.create_app_instance()
        self._app.reset()
        print("Reset done")
        #self._default_timeout = self._app.app.options['timeout']
        self._default_timeout = 30
        #FIXME: reset
        print("Setup completed")

    def assert_200(self, path, match):
        """Assert that a page returns 200"""
        p = self._app.get(path)
        assert p.status_int == 200, "Status: %d, Location: %s" % \
            (p.status_int, p.location)

        if match is not None:
            assert match in p.body, "'%s' not found in body: '%s'" % (match, p.body)

        return p

    def assert_redirect(self, page, redir_page, post=None):
        """Assert that a page redirects to another one"""

        # perform GET or POST
        if post is None:
            p = self._app.get(page, status=302)
        else:
            assert isinstance(post, dict)
            p = self._app.post(page, post, status=302)

        dest = p.location.split(':80/')[-1]
        dest = "/%s" % dest
        assert dest == redir_page, "%s redirects to %s instead of %s" % \
            (page, dest, redir_page)

        return p

    def login_as_admin(self):
        """perform log in"""
        assert self._app is not None
        assert 'session' not in self._app.cookies, "Unexpected cookie found"

        self.assert_200('/login', 'Please insert your credentials')
        assert 'session' not in self._app.cookies, "Unexpected cookie found"

        self.assert_redirect('/admin', '/sorry_page')

        self.assert_200('/user_is_anonymous', 'True')
        assert 'session' not in self._app.cookies, "Unexpected cookie found"

        post = {'username': 'admin', 'password': 'admin'}
        self.assert_redirect('/login', '/', post=post)
        assert 'session' in self._app.cookies, "Cookie not found"

        import bottle
        session = bottle.request.environ.get('beaker.session')
        print("Session from func. test", repr(session))

        self.assert_200('/login', 'Please insert your credentials')


        p = self._app.get('/admin')
        assert 'Welcome' in p.body, repr(p)

        p = self._app.get('/my_role', status=200)
        assert p.status_int == 200
        assert p.body == 'admin', "Sta"

        print("Login performed")



    def test_functional_login(self):
        assert self._app
        self._app.get('/admin', status=302)
        self._app.get('/my_role', status=302)

        self.login_as_admin()

        # fetch a page successfully
        r = self._app.get('/admin')
        assert r.status_int == 200, repr(r)

    def test_login_existing_user_none_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': None})
        assert p.status_int == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_nonexistent_user_none_password(self):
        p = self._app.post('/login', {'username': 'IAmNotHere', 'password': None})
        assert p.status_int == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_existing_user_empty_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': ''})
        assert p.status_int == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_nonexistent_user_empty_password(self):
        p = self._app.post('/login', {'username': 'IAmNotHere', 'password': ''})
        assert p.status_int == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_login_existing_user_wrong_password(self):
        p = self._app.post('/login', {'username': 'admin', 'password': 'BogusPassword'})
        assert p.status_int == REDIR, "Redirect expected"
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

    def test_functional_login_logout(self):
        # Incorrect login
        p = self._app.post('/login', {'username': 'admin', 'password': 'BogusPassword'})
        assert p.status_int == REDIR
        assert p.location == 'http://localhost:80/login', \
            "Incorrect redirect to %s" % p.location

        # log in and get a cookie
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status_int == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # fetch a page successfully
        assert self._app.get('/admin').status_int == 200, "Admin page should be served"

        # log out
        assert self._app.get('/logout').status_int == REDIR

        # drop the cookie
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # fetch the same page, unsuccessfully
        assert self._app.get('/admin').status_int == REDIR

    def test_functional_user_creation_login_deletion(self):
        assert self._app.cookies == {}, "The cookie should be not set"

        # Log in as Admin
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status_int == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # Create new user
        username = 'BrandNewUser'
        password = '42IsTheAnswer'
        ret = self._app.post('/create_user', {
            'username': username,
            'password': password,
            'role': 'user'
        })
        retj = json.loads(ret.body)
        assert 'ok' in retj and retj['ok'] == True, "Failed user creation: %s" % \
            ret.body

        # log out
        assert self._app.get('/logout').status_int == REDIR
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # Log in as user
        p = self._app.post('/login', {'username': username, 'password': password})
        assert p.status_int == REDIR and p.location == 'http://localhost:80/', \
            "Failed user login"

        # log out
        assert self._app.get('/logout').status_int == REDIR
        self._app.reset()
        assert self._app.cookies == {}, "The cookie should be gone"

        # Log in as user with empty password
        p = self._app.post('/login', {'username': username, 'password': ''})
        assert p.status_int == REDIR and p.location == 'http://localhost:80/login', \
            "User login should fail"
        assert self._app.cookies == {}, "The cookie should not be set"

        # Log in as Admin, again
        p = self._app.post('/login', {'username': 'admin', 'password': 'admin'})
        assert p.status_int == REDIR
        assert p.location == 'http://localhost:80/', \
            "Incorrect redirect to %s" % p.location

        self.assert_200('/my_role', 'admin')

        # Delete the user
        ret = self._app.post('/delete_user', {
            'username': username,
        })
        retj = json.loads(ret.body)
        assert 'ok' in retj and retj['ok'] == True, "Failed user deletion: %s" % \
            ret.body

    #def test_functional_user_registration(self):
    #    assert self._app.cookies == {}, "The cookie should be not set"
    #
    #    # Register new user
    #    username = 'BrandNewUser'
    #    password = '42IsTheAnswer'
    #    ret = self._app.post('/register', {
    #        'username': username,
    #        'password': password,
    #        'email_address': 'test@localhost.local'
    #    })

    def test_functionalxxx(self):
        assert self._app is not None

    def test_functional_expiration(self):
        self.login_as_admin()
        r = self._app.get('/admin')
        assert r.status_int == 200, repr(r)

        try:
            # change the cookie expiration in order to expire it
            saved = self._bottle_app.permanent_session_lifetime
            self._bottle_app.permanent_session_lifetime = timedelta(seconds=-1)
            assert self._app.get('/admin').status_int == REDIR, "The cookie should have expired"

        finally:
            self._bottle_app.permanent_session_lifetime = saved

########NEW FILE########
__FILENAME__ = test_functional_mongodb_instance
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Unit testing - test the Cork module against a real MongoDB instance
# running on localhost.

from base64 import b64encode, b64decode
from nose import SkipTest
from nose.tools import assert_raises, raises, with_setup
from time import time
import bottle
import mock
import os
import shutil

from cork import Cork, AAAException, AuthException
from cork.backends import MongoDBBackend
import testutils

testdir = None  # Test directory
aaa = None  # global Cork instance
cookie_name = None  # global variable to track cookie status

class RoAttrDict(dict):
    """Read-only attribute-accessed dictionary.
    Used to mock beaker's session objects
    """
    def __getattr__(self, name):
        return self[name]

    def delete(self):
        """Used during logout to delete the current session"""
        global cookie_name
        cookie_name = None



class MockedAdminCork(Cork):
    """Mocked module where the current user is always 'admin'"""
    @property
    def _beaker_session(self):
        return RoAttrDict(username='admin')

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


class MockedUnauthenticatedCork(Cork):
    """Mocked module where the current user not set"""
    @property
    def _beaker_session(self):
        return RoAttrDict()

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username

def setup_test_db():
    mb = MongoDBBackend(db_name='cork-functional-test', initialize=True)

    # Purge DB
    mb.users._coll.drop()
    mb.roles._coll.drop()
    mb.pending_registrations._coll.drop()

    # Create admin
    mb.users._coll.insert({
        "login": "admin",
        "email_addr": "admin@localhost.local",
        "desc": "admin test user",
        "role": "admin",
        "hash": "cLzRnzbEwehP6ZzTREh3A4MXJyNo+TV8Hs4//EEbPbiDoo+dmNg22f2RJC282aSwgyWv/O6s3h42qrA6iHx8yfw=",
        "creation_date": "2012-10-28 20:50:26.286723"
    })

    # Create users
    mb.roles._coll.insert({'role': 'special', 'val': 200})
    mb.roles._coll.insert({'role': 'admin', 'val': 100})
    mb.roles._coll.insert({'role': 'editor', 'val': 60})
    mb.roles._coll.insert({'role': 'user', 'val': 50})

    return mb

def purge_test_db():
    # Purge DB
    mb = MongoDBBackend(db_name='cork-functional-test', initialize=True)
    mb.users._coll.drop()
    mb.roles._coll.drop()
    mb.pending_registrations._coll.drop()

def setup_mockedadmin():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    mb = setup_test_db()
    aaa = MockedAdminCork(backend=mb, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None

def setup_mocked_unauthenticated():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    mb = setup_test_db()
    aaa = MockedUnauthenticatedCork(backend=mb, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None


@with_setup(setup_test_db, purge_test_db)
def test_initialize_storage():
    mb = MongoDBBackend(db_name='cork-functional-test', initialize=True)
    Cork(backend=mb)


@with_setup(setup_mockedadmin, purge_test_db)
def test_mockedadmin():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    assert 'admin' in aaa._store.users, repr(aaa._store.users)


@with_setup(setup_mockedadmin, purge_test_db)
def test_password_hashing():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"


@with_setup(setup_mockedadmin, purge_test_db)
def test_incorrect_password_hashing():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"


@with_setup(setup_mockedadmin, purge_test_db)
def test_password_hashing_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt)
    assert hash1 != hash2, "Hash collision"


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_create_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_role, 'user', 33)


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_existing_role():
    assert_raises(AAAException, aaa.create_role, 'user', 33)

@raises(KeyError)
@with_setup(setup_mockedadmin, purge_test_db)
def test_access_nonexisting_role():
    aaa._store.roles['NotThere']

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_create_role_with_incorrect_level():
    aaa.create_role('new_user', 'not_a_number')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_role():
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 5, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_delete_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_role, 'user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_nonexistent_role():
    assert_raises(AAAException, aaa.delete_role, 'user123')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_delete_role():
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 5, repr(aaa._store.roles)

    assert aaa._store.roles['user33'] == 33
    aaa.delete_role('user33')
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_list_roles():
    roles = list(aaa.list_roles())
    assert len(roles) == 4, "Incorrect. Users are: %s" % repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_create_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_user, 'phil', 'user', 'hunter123')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_existing_user():
    assert_raises(AAAException, aaa.create_user, 'admin', 'admin', 'bogus')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user_with_wrong_role():
    aaa.create_user('admin2', 'nonexistent_role', 'bogus')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.create_user('phil', 'user', 'user')
    assert len(aaa._store.users) == 2, repr(aaa._store.users)
    assert 'phil' in aaa._store.users


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_delete_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_user, 'phil')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_nonexistent_user():
    assert_raises(AAAException, aaa.delete_user, 'not_an_user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.delete_user('admin')
    assert len(aaa._store.users) == 0, repr(aaa._store.users)
    assert 'admin' not in aaa._store.users



@with_setup(setup_mockedadmin, purge_test_db)
def test_list_users():
    users = list(aaa.list_users())
    assert len(users) == 1, "Incorrect. Users are: %s" % repr(aaa._store.users)

@with_setup(setup_mockedadmin, purge_test_db)
def test_iteritems_on_users():
    for k, v in aaa._store.users.iteritems():
        assert isinstance(v, dict)
        expected_dkeys = set(('hash', 'email_addr', 'role', 'creation_date', 'desc'))
        dkeys = set(v.keys())

        extra = dkeys - expected_dkeys
        assert not extra, "Unexpected extra keys: %s" % repr(extra)

        missing = expected_dkeys - dkeys
        assert not missing, "Missing keys: %s" % repr(missing)


@with_setup(setup_mockedadmin, purge_test_db)
def test_failing_login():
    login = aaa.login('phil', 'hunter123')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_login_nonexistent_user_empty_password():
    login = aaa.login('IAmNotHome', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_login_existing_user_empty_password():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_and_validate_user():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    global cookie_name
    assert cookie_name == 'phil'

@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user_login_logout():
    global cookie_name
    assert 'phil' not in aaa._store.users
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    assert cookie_name == 'phil'
    try:
        aaa.logout(fail_redirect='/failed_logout')
    except bottle.HTTPResponse, e:
        testutils.assert_is_redirect(e, 'login')

    assert cookie_name == None

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user_using_overwrite():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    u = aaa._store.users['phil']
    u.update(role='fool')
    aaa._store.users['phil'] = u
    assert aaa._store.users['phil']['role'] == 'fool'

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user():
    aaa.create_user('phil', 'user', 'hunter123')
    aaa._store.users['phil']['role'] = 'fool'
    assert aaa._store.users['phil']['role'] == 'fool'

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user_using_local_change():
    aaa.create_user('phil', 'user', 'hunter123')
    u = aaa._store.users['phil']
    u['role'] = 'fool'
    assert u['role'] == 'fool', repr(u)
    assert aaa._store.users['phil']['role'] == 'fool'


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_username():
    # The user exists, but I'm 'admin'
    aaa.create_user('phil', 'user', 'hunter123')
    assert_raises(AuthException, aaa.require, username='phil')


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_nonexistent_username():
    assert_raises(AAAException, aaa.require, username='no_such_user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_role_fixed():
    assert_raises(AuthException, aaa.require, role='user', fixed_role=True)


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_require_missing_parameter():
    aaa.require(fixed_role=True)


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_nonexistent_role():
    assert_raises(AAAException, aaa.require, role='clown')

@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_role():
    # Requesting level >= 100
    aaa.require(role='special')


@with_setup(setup_mockedadmin, purge_test_db)
def test_successful_require_role():
    aaa.require(username='admin')
    aaa.require(username='admin', role='admin')
    aaa.require(username='admin', role='admin', fixed_role=True)
    aaa.require(username='admin', role='user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_authenticated_is_not__anonymous():
    assert not aaa.user_is_anonymous


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_nonexistent_role():
    assert_raises(AAAException, aaa.current_user.update, role='clown')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_update_nonexistent_user():
    aaa._store.users.pop('admin')
    aaa.current_user.update(role='user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_role():
    aaa.current_user.update(role='user')
    assert aaa._store.users['admin']['role'] == 'user'


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_pwd():
    aaa.current_user.update(pwd='meow')


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_email():
    print aaa._store.users['admin']
    aaa.current_user.update(email_addr='foo')
    assert aaa._store.users['admin']['email_addr'] == 'foo'


@raises(AAAException)
@with_setup(setup_mocked_unauthenticated, purge_test_db)
def test_get_current_user_unauth():
    aaa.current_user['username']


@with_setup(setup_mocked_unauthenticated, purge_test_db)
def test_unauth_is_anonymous():
    assert aaa.user_is_anonymous


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_get_current_user_nonexistent():
    # The current user 'admin' is not in the user table
    aaa._store.users.pop('admin')
    aaa.current_user


@with_setup(setup_mockedadmin, purge_test_db)
def test_get_nonexistent_user():
    assert aaa.user('nonexistent_user') is None


@with_setup(setup_mockedadmin, purge_test_db)
def test_get_user_description_field():
    admin = aaa.user('admin')
    for field in ['description', 'email_addr']:
        assert field in admin.__dict__


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_user():
    assert_raises(AssertionError, aaa.register, None, 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_pwd():
    assert_raises(AssertionError, aaa.register, 'foo', None, 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_email():
    assert_raises(AssertionError, aaa.register, 'foo', 'pwd', None)


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_already_existing():
    assert_raises(AAAException, aaa.register, 'admin', 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_role():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='clown')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_role_too_high():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='admin')

@with_setup(setup_mockedadmin, purge_test_db)
def test_register_valid():
    aaa.mailer.send_email = mock.Mock()
    aaa.register('foo', 'pwd', 'email@email.org', role='user',
        email_template='examples/views/registration_email.tpl'
    )
    assert aaa.mailer.send_email.called
    r = aaa._store.pending_registrations
    assert len(r) == 1
    reg_code = list(r)[0]
    assert r[reg_code]['username'] == 'foo'
    assert r[reg_code]['email_addr'] == 'email@email.org'
    assert r[reg_code]['role'] == 'user'


@with_setup(setup_mockedadmin, purge_test_db)
def test_validate_registration_no_code():
    assert_raises(AAAException, aaa.validate_registration, 'not_a_valid_code')

@with_setup(setup_mockedadmin, purge_test_db)
def test_validate_registration():
    aaa.mailer.send_email = mock.Mock()
    aaa.register('foo', 'pwd', 'email@email.org', role='user',
        email_template='examples/views/registration_email.tpl'
    )
    r = aaa._store.pending_registrations
    reg_code = list(r)[0]

    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa.validate_registration(reg_code)
    assert len(aaa._store.users) == 2, "The new user should be present"
    assert len(aaa._store.pending_registrations) == 0, \
        "The registration entry should be removed"



@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_no_data():
    aaa.send_password_reset_email()

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_incorrect_data():
    aaa.send_password_reset_email(username='NotThere', email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_incorrect_data2():
    # The username is valid but the email address is not matching
    aaa.send_password_reset_email(username='admin', email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_incorrect_email():
    aaa.send_password_reset_email(email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_incorrect_username():
    aaa.send_password_reset_email(username='NotThere')

@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_email():
    aaa.mailer.send_email = mock.Mock()
    aaa.send_password_reset_email(email_addr='admin@localhost.local',
        email_template='examples/views/password_reset_email')

@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_username():
    aaa.mailer.send_email = mock.Mock()
    aaa.send_password_reset_email(username='admin',
        email_template='examples/views/password_reset_email')



@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_invalid():
    aaa.reset_password('bogus', 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_timed_out():
    aaa.password_reset_timeout = 0
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_nonexistent_user():
    token = aaa._reset_code('admin_bogus', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


# The following test should fail
# an user can change the password reset timestamp by b64-decoding the token,
# editing the field and b64-encoding it
@SkipTest
@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_timestamp():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    tstamp = str(int(tstamp) + 100)
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_username():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    username += "mangled_username"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_email():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    email_addr += "mangled_email"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')




########NEW FILE########
__FILENAME__ = test_functional_mysql_instance
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Unit testing - test the Cork module against a real MySQL instance
# running on localhost.

from base64 import b64encode, b64decode
from nose import SkipTest
from nose.tools import assert_raises, raises, with_setup
from time import time
import bottle
import mock
import os
import shutil

from cork import Cork, AAAException, AuthException
from cork.backends import SqlAlchemyBackend
import testutils

testdir = None  # Test directory
aaa = None  # global Cork instance
cookie_name = None  # global variable to track cookie status

class RoAttrDict(dict):
    """Read-only attribute-accessed dictionary.
    Used to mock beaker's session objects
    """
    def __getattr__(self, name):
        return self[name]

    def delete(self):
        """Used during logout to delete the current session"""
        global cookie_name
        cookie_name = None



class MockedAdminCork(Cork):
    """Mocked module where the current user is always 'admin'"""
    @property
    def _beaker_session(self):
        return RoAttrDict(username='admin')

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


class MockedUnauthenticatedCork(Cork):
    """Mocked module where the current user not set"""
    @property
    def _beaker_session(self):
        return RoAttrDict()

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


def connect_to_test_db():

    if os.environ.get('TRAVIS', False):
        # Using Travis-CI - https://travis-ci.org/
        password = ''
        db_name = 'myapp_test'
    else:
        password = ''
        db_name = 'cork_functional_test'

    uri = "mysql://root:%s@localhost/%s" % (password, db_name)
    return SqlAlchemyBackend(uri, initialize=True)


def setup_test_db():

    mb = connect_to_test_db()

    ## Purge DB
    mb._drop_all_tables()
    #mb.users.empty_table()
    #mb.roles.empty_table()
    #mb.pending_registrations.empty_table()

    assert len(mb.roles) == 0
    assert len(mb.users) == 0

    # Create roles
    mb.roles.insert({'role': 'special', 'level': 200})
    mb.roles.insert({'role': 'admin', 'level': 100})
    mb.roles.insert({'role': 'editor', 'level': 60})
    mb.roles.insert({'role': 'user', 'level': 50})

    # Create admin
    mb.users.insert({
        "username": "admin",
        "email_addr": "admin@localhost.local",
        "desc": "admin test user",
        "role": "admin",
        "hash": "cLzRnzbEwehP6ZzTREh3A4MXJyNo+TV8Hs4//EEbPbiDoo+dmNg22f2RJC282aSwgyWv/O6s3h42qrA6iHx8yfw=",
        "creation_date": "2012-10-28 20:50:26.286723",
        "last_login": "2012-10-28 20:50:26.286723"
    })
    assert len(mb.roles) == 4
    assert len(mb.users) == 1

    return mb

def purge_test_db():
    # Purge DB
    mb = connect_to_test_db()
    mb._drop_all_tables()

def setup_mockedadmin():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    mb = setup_test_db()
    aaa = MockedAdminCork(backend=mb, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None

def setup_mocked_unauthenticated():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    mb = setup_test_db()
    aaa = MockedUnauthenticatedCork(backend=mb, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None


@with_setup(setup_test_db, purge_test_db)
def test_initialize_storage():
    mb = connect_to_test_db()
    Cork(backend=mb)


@with_setup(setup_mockedadmin, purge_test_db)
def test_mockedadmin():
    assert len(aaa._store.users) == 1,  len(aaa._store.users)
    assert 'admin' in aaa._store.users, repr(aaa._store.users)


@with_setup(setup_mockedadmin, purge_test_db)
def test_password_hashing():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"


@with_setup(setup_mockedadmin, purge_test_db)
def test_incorrect_password_hashing():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"


@with_setup(setup_mockedadmin, purge_test_db)
def test_password_hashing_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt)
    assert hash1 != hash2, "Hash collision"


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_create_role():
    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa._store.roles['admin'] = 10  # lower admin level
    assert aaa._store.roles['admin'] == 10, aaa._store.roles['admin']
    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    assert_raises(AuthException, aaa.create_role, 'user', 33)


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_existing_role():
    assert_raises(AAAException, aaa.create_role, 'user', 33)

@raises(KeyError)
@with_setup(setup_mockedadmin, purge_test_db)
def test_access_nonexisting_role():
    aaa._store.roles['NotThere']

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_create_role_with_incorrect_level():
    aaa.create_role('new_user', 'not_a_number')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_role():
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 5, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_delete_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_role, 'user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_nonexistent_role():
    assert_raises(AAAException, aaa.delete_role, 'user123')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_delete_role():
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 5, repr(aaa._store.roles)

    assert aaa._store.roles['user33'] == 33
    aaa.delete_role('user33')
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_list_roles():
    roles = list(aaa.list_roles())
    assert len(roles) == 4, "Incorrect. Users are: %s" % repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_create_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_user, 'phil', 'user', 'hunter123')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_existing_user():
    assert_raises(AAAException, aaa.create_user, 'admin', 'admin', 'bogus')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user_with_wrong_role():
    aaa.create_user('admin2', 'nonexistent_role', 'bogus')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.create_user('phil', 'user', 'user')
    assert len(aaa._store.users) == 2, repr(aaa._store.users)

    #aaa._store.users._dump() #FIXME
    assert 'phil' in aaa._store.users


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_delete_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_user, 'phil')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_nonexistent_user():
    assert_raises(AAAException, aaa.delete_user, 'not_an_user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.delete_user('admin')
    assert len(aaa._store.users) == 0, repr(aaa._store.users)
    assert 'admin' not in aaa._store.users



@with_setup(setup_mockedadmin, purge_test_db)
def test_list_users():
    users = list(aaa.list_users())
    assert len(users) == 1, "Incorrect. Users are: %s" % repr(aaa._store.users)

@with_setup(setup_mockedadmin, purge_test_db)
def test_iteritems_on_users():
    for k, v in aaa._store.users.iteritems():
        assert isinstance(k, str)
        assert isinstance(v, dict)
        expected_dkeys = set(('hash', 'email_addr', 'role', 'creation_date', 'desc', 'last_login'))
        dkeys = set(v.keys())

        extra = dkeys - expected_dkeys
        assert not extra, "Unexpected extra keys: %s" % repr(extra)

        missing = expected_dkeys - dkeys
        assert not missing, "Missing keys: %s" % repr(missing)


@with_setup(setup_mockedadmin, purge_test_db)
def test_failing_login():
    login = aaa.login('phil', 'hunter123')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_login_nonexistent_user_empty_password():
    login = aaa.login('IAmNotHome', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_login_existing_user_empty_password():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_and_validate_user():
    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa.create_user('phil', 'user', 'hunter123')
    assert len(aaa._store.users) == 2, "Two users should be present"
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    global cookie_name
    assert cookie_name == 'phil'

@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user_login_logout():
    global cookie_name
    assert 'phil' not in aaa._store.users
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    assert cookie_name == 'phil'
    try:
        aaa.logout(fail_redirect='/failed_logout')
    except bottle.HTTPResponse, e:
        testutils.assert_is_redirect(e, 'login')

    assert cookie_name == None

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user_using_overwrite():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    u = aaa._store.users['phil']
    u.update(role='editor')
    aaa._store.users['phil'] = u
    assert aaa._store.users['phil']['role'] == 'editor'

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user():
    aaa.create_user('phil', 'user', 'hunter123')
    aaa._store.users['phil']['role'] = 'editor'
    assert aaa._store.users['phil']['role'] == 'editor'

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user_using_local_change():
    aaa.create_user('phil', 'user', 'hunter123')
    u = aaa._store.users['phil']
    u['role'] = 'editor'
    assert u['role'] == 'editor', repr(u)
    assert aaa._store.users['phil']['role'] == 'editor'


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_username():
    # The user exists, but I'm 'admin'
    aaa.create_user('phil', 'user', 'hunter123')
    assert_raises(AuthException, aaa.require, username='phil')


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_nonexistent_username():
    assert_raises(AAAException, aaa.require, username='no_such_user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_role_fixed():
    assert_raises(AuthException, aaa.require, role='user', fixed_role=True)


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_require_missing_parameter():
    aaa.require(fixed_role=True)


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_nonexistent_role():
    assert_raises(AAAException, aaa.require, role='clown')

@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_role():
    # Requesting level >= 100
    assert_raises(AuthException, aaa.require, role='special')


@with_setup(setup_mockedadmin, purge_test_db)
def test_successful_require_role():
    aaa.require(username='admin')
    aaa.require(username='admin', role='admin')
    aaa.require(username='admin', role='admin', fixed_role=True)
    aaa.require(username='admin', role='user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_authenticated_is_not__anonymous():
    assert not aaa.user_is_anonymous


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_nonexistent_role():
    assert_raises(AAAException, aaa.current_user.update, role='clown')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_update_nonexistent_user():
    aaa._store.users.pop('admin')
    aaa.current_user.update(role='user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_role():
    aaa.current_user.update(role='user')
    assert aaa._store.users['admin']['role'] == 'user'


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_pwd():
    aaa.current_user.update(pwd='meow')


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_email():
    print aaa._store.users['admin']
    aaa.current_user.update(email_addr='foo')
    assert aaa._store.users['admin']['email_addr'] == 'foo'


@raises(AAAException)
@with_setup(setup_mocked_unauthenticated, purge_test_db)
def test_get_current_user_unauth():
    aaa.current_user['username']


@with_setup(setup_mocked_unauthenticated, purge_test_db)
def test_unauth_is_anonymous():
    assert aaa.user_is_anonymous


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_get_current_user_nonexistent():
    # The current user 'admin' is not in the user table
    aaa._store.users.pop('admin')
    aaa.current_user


@with_setup(setup_mockedadmin, purge_test_db)
def test_get_nonexistent_user():
    assert aaa.user('nonexistent_user') is None


@with_setup(setup_mockedadmin, purge_test_db)
def test_get_user_description_field():
    admin = aaa.user('admin')
    for field in ['description', 'email_addr']:
        assert field in admin.__dict__


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_user():
    assert_raises(AssertionError, aaa.register, None, 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_pwd():
    assert_raises(AssertionError, aaa.register, 'foo', None, 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_email():
    assert_raises(AssertionError, aaa.register, 'foo', 'pwd', None)


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_already_existing():
    assert_raises(AAAException, aaa.register, 'admin', 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_role():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='clown')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_role_too_high():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='admin')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_valid():
    aaa.mailer.send_email = mock.Mock()
    aaa.register('foo', 'pwd', 'email@email.org', role='user',
        email_template='examples/views/registration_email.tpl'
    )
    assert aaa.mailer.send_email.called
    r = aaa._store.pending_registrations
    assert len(r) == 1
    reg_code = list(r)[0]
    assert r[reg_code]['username'] == 'foo'
    assert r[reg_code]['email_addr'] == 'email@email.org'
    assert r[reg_code]['role'] == 'user'


@with_setup(setup_mockedadmin, purge_test_db)
def test_validate_registration_no_code():
    assert_raises(AAAException, aaa.validate_registration, 'not_a_valid_code')

@with_setup(setup_mockedadmin, purge_test_db)
def test_validate_registration():
    aaa.mailer.send_email = mock.Mock()
    aaa.register('foo', 'pwd', 'email@email.org', role='user',
        email_template='examples/views/registration_email.tpl'
    )
    r = aaa._store.pending_registrations
    reg_code = list(r)[0]

    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa.validate_registration(reg_code)
    assert len(aaa._store.users) == 2, "The new user should be present"
    assert len(aaa._store.pending_registrations) == 0, \
        "The registration entry should be removed"



@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_no_data():
    aaa.send_password_reset_email()

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_incorrect_data():
    aaa.send_password_reset_email(username='NotThere', email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_incorrect_data2():
    # The username is valid but the email address is not matching
    aaa.send_password_reset_email(username='admin', email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_incorrect_email():
    aaa.send_password_reset_email(email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_incorrect_username():
    aaa.send_password_reset_email(username='NotThere')

@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_email():
    aaa.mailer.send_email = mock.Mock()
    aaa.send_password_reset_email(email_addr='admin@localhost.local',
        email_template='examples/views/password_reset_email')

@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_username():
    aaa.mailer.send_email = mock.Mock()
    aaa.send_password_reset_email(username='admin',
        email_template='examples/views/password_reset_email')



@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_invalid():
    aaa.reset_password('bogus', 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_timed_out():
    aaa.password_reset_timeout = 0
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_nonexistent_user():
    token = aaa._reset_code('admin_bogus', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


# The following test should fail
# an user can change the password reset timestamp by b64-decoding the token,
# editing the field and b64-encoding it
@SkipTest
@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_timestamp():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    tstamp = str(int(tstamp) + 100)
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_username():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    username += "mangled_username"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_email():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    email_addr += "mangled_email"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


########NEW FILE########
__FILENAME__ = test_sqlite
# Cork - Authentication module for the Bottle web framework
# Copyright (C) 2013 Federico Ceratto and others, see AUTHORS file.
# Released under LGPLv3+ license, see LICENSE.txt
#
# Unit testing - test the Cork SQLite backend module.
#

from base64 import b64encode, b64decode
from nose import SkipTest
from nose.tools import assert_raises, raises, with_setup
from time import time
import bottle
import mock
import os
import shutil

from cork import Cork, AAAException, AuthException
from cork.backends import SQLiteBackend
import testutils

testdir = None  # Test directory
aaa = None  # global Cork instance
cookie_name = None  # global variable to track cookie status

class RoAttrDict(dict):
    """Read-only attribute-accessed dictionary.
    Used to mock beaker's session objects
    """
    def __getattr__(self, name):
        return self[name]

    def delete(self):
        """Used during logout to delete the current session"""
        global cookie_name
        cookie_name = None



class MockedAdminCork(Cork):
    """Mocked module where the current user is always 'admin'"""
    @property
    def _beaker_session(self):
        return RoAttrDict(username='admin')

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


class MockedUnauthenticatedCork(Cork):
    """Mocked module where the current user not set"""
    @property
    def _beaker_session(self):
        return RoAttrDict()

    def _setup_cookie(self, username):
        global cookie_name
        cookie_name = username


def setup_test_db():
    b = SQLiteBackend(':memory:', initialize=True)
    b.connection.executescript("""
        INSERT INTO users (username, email_addr, desc, role, hash, creation_date) VALUES
        (
            'admin',
            'admin@localhost.local',
            'admin test user',
            'admin',
            'cLzRnzbEwehP6ZzTREh3A4MXJyNo+TV8Hs4//EEbPbiDoo+dmNg22f2RJC282aSwgyWv/O6s3h42qrA6iHx8yfw=',
            '2012-10-28 20:50:26.286723'
        );
        INSERT INTO roles (role, level) VALUES ('special', 200);
        INSERT INTO roles (role, level) VALUES ('admin', 100);
        INSERT INTO roles (role, level) VALUES ('editor', 60);
        INSERT INTO roles (role, level) VALUES ('user', 50);
    """)
    return b

def setup_mockedadmin():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    mb = setup_test_db()
    aaa = MockedAdminCork(backend=mb, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None

def setup_mocked_unauthenticated():
    """Setup test directory and a MockedAdminCork instance"""
    global aaa
    global cookie_name
    mb = setup_test_db()
    aaa = MockedUnauthenticatedCork(backend=mb, smtp_server='localhost', email_sender='test@localhost')
    cookie_name = None

def purge_test_db():
    pass

@with_setup(setup_test_db, purge_test_db)
def test_initialize_storage():
    mb = setup_test_db()
    Cork(backend=mb)


@with_setup(setup_mockedadmin, purge_test_db)
def test_mockedadmin():
    assert len(aaa._store.users) == 1,  len(aaa._store.users)
    assert 'admin' in aaa._store.users, repr(aaa._store.users)


@with_setup(setup_mockedadmin, purge_test_db)
def test_password_hashing():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', 'bogus_pwd', shash) == True, \
        "Hashing verification should succeed"


@with_setup(setup_mockedadmin, purge_test_db)
def test_incorrect_password_hashing():
    shash = aaa._hash('user_foo', 'bogus_pwd')
    assert len(shash) == 88, "hash length should be 88 and is %d" % len(shash)
    assert shash.endswith('='), "hash should end with '='"
    assert aaa._verify_password('user_foo', '####', shash) == False, \
        "Hashing verification should fail"
    assert aaa._verify_password('###', 'bogus_pwd', shash) == False, \
        "Hashing verification should fail"


@with_setup(setup_mockedadmin, purge_test_db)
def test_password_hashing_collision():
    salt = 'S' * 32
    hash1 = aaa._hash('user_foo', 'bogus_pwd', salt=salt)
    hash2 = aaa._hash('user_foobogus', '_pwd', salt=salt)
    assert hash1 != hash2, "Hash collision"


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_create_role():
    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa._store.roles['admin'] = 10  # lower admin level
    assert aaa._store.roles['admin'] == 10, aaa._store.roles['admin']
    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    assert_raises(AuthException, aaa.create_role, 'user', 33)


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_existing_role():
    assert_raises(AAAException, aaa.create_role, 'user', 33)

@raises(KeyError)
@with_setup(setup_mockedadmin, purge_test_db)
def test_access_nonexisting_role():
    aaa._store.roles['NotThere']

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_create_role_with_incorrect_level():
    aaa.create_role('new_user', 'not_a_number')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_role():
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 5, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_delete_role():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_role, 'user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_nonexistent_role():
    assert_raises(AAAException, aaa.delete_role, 'user123')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_delete_role():
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)
    aaa.create_role('user33', 33)
    assert len(aaa._store.roles) == 5, repr(aaa._store.roles)

    assert aaa._store.roles['user33'] == 33
    aaa.delete_role('user33')
    assert len(aaa._store.roles) == 4, repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_list_roles():
    roles = list(aaa.list_roles())
    assert len(roles) == 4, "Incorrect. Users are: %s" % repr(aaa._store.roles)


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_create_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.create_user, 'phil', 'user', 'hunter123')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_existing_user():
    assert_raises(AAAException, aaa.create_user, 'admin', 'admin', 'bogus')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user_with_wrong_role():
    aaa.create_user('admin2', 'nonexistent_role', 'bogus')


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.create_user('phil', 'user', 'user')
    assert len(aaa._store.users) == 2, repr(aaa._store.users)

    #aaa._store.users._dump() #FIXME
    assert 'phil' in aaa._store.users


@with_setup(setup_mockedadmin, purge_test_db)
def test_unauth_delete_user():
    aaa._store.roles['admin'] = 10  # lower admin level
    assert_raises(AuthException, aaa.delete_user, 'phil')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_nonexistent_user():
    assert_raises(AAAException, aaa.delete_user, 'not_an_user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_delete_user():
    assert len(aaa._store.users) == 1, repr(aaa._store.users)
    aaa.delete_user('admin')
    assert len(aaa._store.users) == 0, repr(aaa._store.users)
    assert 'admin' not in aaa._store.users



@with_setup(setup_mockedadmin, purge_test_db)
def test_list_users():
    users = list(aaa.list_users())
    assert len(users) == 1, "Incorrect. Users are: %s" % repr(aaa._store.users)

@with_setup(setup_mockedadmin, purge_test_db)
def test_iteritems_on_users():
    for k, v in aaa._store.users.iteritems():
        assert isinstance(k, str)
        assert isinstance(v, dict)
        expected_dkeys = set(('hash', 'email_addr', 'role', 'creation_date',
            'desc', 'last_login'))
        dkeys = set(v.keys())

        extra = dkeys - expected_dkeys
        assert not extra, "Unexpected extra keys: %s" % repr(extra)

        missing = expected_dkeys - dkeys
        assert not missing, "Missing keys: %s" % repr(missing)


@with_setup(setup_mockedadmin, purge_test_db)
def test_failing_login():
    login = aaa.login('phil', 'hunter123')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_login_nonexistent_user_empty_password():
    login = aaa.login('IAmNotHome', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_login_existing_user_empty_password():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', '')
    assert login == False, "Login must fail"
    global cookie_name
    assert cookie_name == None


@with_setup(setup_mockedadmin, purge_test_db)
def test_create_and_validate_user():
    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa.create_user('phil', 'user', 'hunter123')
    assert len(aaa._store.users) == 2, "Two users should be present"
    assert 'phil' in aaa._store.users
    assert aaa._store.users['phil']['role'] == 'user'
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    global cookie_name
    assert cookie_name == 'phil'

@with_setup(setup_mockedadmin, purge_test_db)
def test_create_user_login_logout():
    global cookie_name
    assert 'phil' not in aaa._store.users
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    login = aaa.login('phil', 'hunter123')
    assert login == True, "Login must succeed"
    assert cookie_name == 'phil'
    try:
        aaa.logout(fail_redirect='/failed_logout')
    except bottle.HTTPResponse, e:
        testutils.assert_is_redirect(e, 'login')

    assert cookie_name == None

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user_using_overwrite():
    aaa.create_user('phil', 'user', 'hunter123')
    assert 'phil' in aaa._store.users
    u = aaa._store.users['phil']
    u.update(role='editor')
    aaa._store.users['phil'] = u
    assert aaa._store.users['phil']['role'] == 'editor'

@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user():
    aaa.create_user('phil', 'user', 'hunter123')
    aaa._store.users['phil']['role'] = 'editor'
    assert aaa._store.users['phil']['role'] == 'editor', aaa._store.users['phil']


@with_setup(setup_mockedadmin, purge_test_db)
def test_modify_user_using_local_change():
    aaa.create_user('phil', 'user', 'hunter123')
    u = aaa._store.users['phil']
    u['role'] = 'editor'
    assert u['role'] == 'editor', repr(u)
    assert aaa._store.users['phil']['role'] == 'editor'


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_username():
    # The user exists, but I'm 'admin'
    aaa.create_user('phil', 'user', 'hunter123')
    assert_raises(AuthException, aaa.require, username='phil')


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_nonexistent_username():
    assert_raises(AAAException, aaa.require, username='no_such_user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_role_fixed():
    assert_raises(AuthException, aaa.require, role='user', fixed_role=True)


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_require_missing_parameter():
    aaa.require(fixed_role=True)


@with_setup(setup_mockedadmin, purge_test_db)
def test_require_nonexistent_role():
    assert_raises(AAAException, aaa.require, role='clown')

@with_setup(setup_mockedadmin, purge_test_db)
def test_require_failing_role():
    # Requesting level >= 100
    assert_raises(AuthException, aaa.require, role='special')


@with_setup(setup_mockedadmin, purge_test_db)
def test_successful_require_role():
    aaa.require(username='admin')
    aaa.require(username='admin', role='admin')
    aaa.require(username='admin', role='admin', fixed_role=True)
    aaa.require(username='admin', role='user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_authenticated_is_not__anonymous():
    assert not aaa.user_is_anonymous


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_nonexistent_role():
    assert_raises(AAAException, aaa.current_user.update, role='clown')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_update_nonexistent_user():
    aaa._store.users.pop('admin')
    aaa.current_user.update(role='user')


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_role():
    aaa.current_user.update(role='user')
    assert aaa._store.users['admin']['role'] == 'user'


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_pwd():
    aaa.current_user.update(pwd='meow')


@with_setup(setup_mockedadmin, purge_test_db)
def test_update_email():
    print aaa._store.users['admin']
    aaa.current_user.update(email_addr='foo')
    assert aaa._store.users['admin']['email_addr'] == 'foo', aaa._store.users['admin']


@raises(AAAException)
@with_setup(setup_mocked_unauthenticated, purge_test_db)
def test_get_current_user_unauth():
    aaa.current_user['username']


@with_setup(setup_mocked_unauthenticated, purge_test_db)
def test_unauth_is_anonymous():
    assert aaa.user_is_anonymous


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_get_current_user_nonexistent():
    # The current user 'admin' is not in the user table
    aaa._store.users.pop('admin')
    aaa.current_user


@with_setup(setup_mockedadmin, purge_test_db)
def test_get_nonexistent_user():
    assert aaa.user('nonexistent_user') is None


@with_setup(setup_mockedadmin, purge_test_db)
def test_get_user_description_field():
    admin = aaa.user('admin')
    for field in ['description', 'email_addr']:
        assert field in admin.__dict__


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_user():
    assert_raises(AssertionError, aaa.register, None, 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_pwd():
    assert_raises(AssertionError, aaa.register, 'foo', None, 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_email():
    assert_raises(AssertionError, aaa.register, 'foo', 'pwd', None)


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_already_existing():
    assert_raises(AAAException, aaa.register, 'admin', 'pwd', 'a@a.a')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_no_role():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='clown')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_role_too_high():
    assert_raises(AAAException, aaa.register, 'foo', 'pwd', 'a@a.a', role='admin')


@with_setup(setup_mockedadmin, purge_test_db)
def test_register_valid():
    aaa.mailer.send_email = mock.Mock()
    aaa.register('foo', 'pwd', 'email@email.org', role='user',
        email_template='examples/views/registration_email.tpl'
    )
    assert aaa.mailer.send_email.called
    r = aaa._store.pending_registrations
    assert len(r) == 1
    reg_code = list(r)[0]
    assert r[reg_code]['username'] == 'foo'
    assert r[reg_code]['email_addr'] == 'email@email.org'
    assert r[reg_code]['role'] == 'user'


@with_setup(setup_mockedadmin, purge_test_db)
def test_validate_registration_no_code():
    assert_raises(AAAException, aaa.validate_registration, 'not_a_valid_code')

@with_setup(setup_mockedadmin, purge_test_db)
def test_validate_registration():
    aaa.mailer.send_email = mock.Mock()
    aaa.register('foo', 'pwd', 'email@email.org', role='user',
        email_template='examples/views/registration_email.tpl'
    )
    r = aaa._store.pending_registrations
    reg_code = list(r)[0]

    assert len(aaa._store.users) == 1, "Only the admin user should be present"
    aaa.validate_registration(reg_code)
    assert len(aaa._store.users) == 2, "The new user should be present"
    assert len(aaa._store.pending_registrations) == 0, \
        "The registration entry should be removed"



@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_no_data():
    aaa.send_password_reset_email()

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_incorrect_data():
    aaa.send_password_reset_email(username='NotThere', email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_incorrect_data2():
    # The username is valid but the email address is not matching
    aaa.send_password_reset_email(username='admin', email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_incorrect_email():
    aaa.send_password_reset_email(email_addr='NoEmail')

@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_incorrect_username():
    aaa.send_password_reset_email(username='NotThere')

@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_email():
    aaa.mailer.send_email = mock.Mock()
    aaa.send_password_reset_email(email_addr='admin@localhost.local',
        email_template='examples/views/password_reset_email')

@with_setup(setup_mockedadmin, purge_test_db)
def test_send_password_reset_email_only_username():
    aaa.mailer.send_email = mock.Mock()
    aaa.send_password_reset_email(username='admin',
        email_template='examples/views/password_reset_email')



@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_invalid():
    aaa.reset_password('bogus', 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_timed_out():
    aaa.password_reset_timeout = 0
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


@raises(AAAException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_nonexistent_user():
    token = aaa._reset_code('admin_bogus', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


# The following test should fail
# an user can change the password reset timestamp by b64-decoding the token,
# editing the field and b64-encoding it
@SkipTest
@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_timestamp():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    tstamp = str(int(tstamp) + 100)
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_username():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    username += "mangled_username"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@raises(AuthException)
@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset_mangled_email():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    username, email_addr, tstamp, h = b64decode(token).split(':', 3)
    email_addr += "mangled_email"
    mangled_token = ':'.join((username, email_addr, tstamp, h))
    mangled_token = b64encode(mangled_token)
    aaa.reset_password(mangled_token, 'newpassword')


@with_setup(setup_mockedadmin, purge_test_db)
def test_perform_password_reset():
    token = aaa._reset_code('admin', 'admin@localhost.local')
    aaa.reset_password(token, 'newpassword')


########NEW FILE########
