__FILENAME__ = courier
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2011 Henry-Nicolas Tourneur
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Courier-Authdaemon authentication.

"""

import sys
import socket

from .. import config, log


COURIER_SOCKET = config.get("auth", "courier_socket")


def is_authenticated(user, password):
    """Check if ``user``/``password`` couple is valid."""
    if not user or not password:
        return False

    line = "%s\nlogin\n%s\n%s" % (sys.argv[0], user, password)
    line = "AUTH %i\n%s" % (len(line), line)
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(COURIER_SOCKET)
        log.LOGGER.debug("Sending to Courier socket the request: %s" % line)
        sock.send(line)
        data = sock.recv(1024)
        sock.close()
    except socket.error as exception:
        log.LOGGER.debug(
            "Unable to communicate with Courier socket: %s" % exception)
        return False

    log.LOGGER.debug("Got Courier socket response: %r" % data)

    # Address, HOME, GID, and either UID or USERNAME are mandatory in resposne
    # see http://www.courier-mta.org/authlib/README_authlib.html#authpipeproto
    for line in data.split():
        if "GID" in line:
            return True

    # default is reject
    # this alleviates the problem of a possibly empty reply from authlib
    # see http://www.courier-mta.org/authlib/README_authlib.html#authpipeproto
    return False

########NEW FILE########
__FILENAME__ = htpasswd
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Htpasswd authentication.

Load the list of login/password couples according a the configuration file
created by Apache ``htpasswd`` command. Plain-text, crypt and sha1 are
supported, but md5 is not (see ``htpasswd`` man page to understand why).

"""

import base64
import hashlib

from .. import config


FILENAME = config.get("auth", "htpasswd_filename")
ENCRYPTION = config.get("auth", "htpasswd_encryption")


def _plain(hash_value, password):
    """Check if ``hash_value`` and ``password`` match using plain method."""
    return hash_value == password


def _crypt(hash_value, password):
    """Check if ``hash_value`` and ``password`` match using crypt method."""
    # The ``crypt`` module is only present on Unix, import if needed
    import crypt
    return crypt.crypt(password, hash_value) == hash_value


def _sha1(hash_value, password):
    """Check if ``hash_value`` and ``password`` match using sha1 method."""
    hash_value = hash_value.replace("{SHA}", "").encode("ascii")
    password = password.encode(config.get("encoding", "stock"))
    sha1 = hashlib.sha1()  # pylint: disable=E1101
    sha1.update(password)
    return sha1.digest() == base64.b64decode(hash_value)


def is_authenticated(user, password):
    """Check if ``user``/``password`` couple is valid."""
    for line in open(FILENAME).readlines():
        if line.strip():
            login, hash_value = line.strip().split(":")
            if login == user:
                return globals()["_%s" % ENCRYPTION](hash_value, password)
    return False

########NEW FILE########
__FILENAME__ = http
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012 Ehsanul Hoque
# Copyright © 2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
HTTP authentication.

Authentication based on the ``requests`` module.

Post a request to an authentication server with the username/password.
Anything other than a 200/201 response is considered auth failure.

"""

import requests

from .. import config, log

AUTH_URL = config.get("auth", "http_url")
USER_PARAM = config.get("auth", "http_user_parameter")
PASSWORD_PARAM = config.get("auth", "http_password_parameter")


def is_authenticated(user, password):
    """Check if ``user``/``password`` couple is valid."""
    log.LOGGER.debug("HTTP-based auth on %s." % AUTH_URL)
    payload = {USER_PARAM: user, PASSWORD_PARAM: password}
    return requests.post(AUTH_URL, data=payload).status_code in (200, 201)

########NEW FILE########
__FILENAME__ = IMAP
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012 Daniel Aleksandersen
# Copyright © 2013 Nikita Koshikov
# Copyright © 2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
IMAP authentication.

Secure authentication based on the ``imaplib`` module.

Validating users against a modern IMAP4rev1 server that awaits STARTTLS on
port 143. Legacy SSL (often on legacy port 993) is deprecated and thus
unsupported. STARTTLS is enforced except if host is ``localhost`` as
passwords are sent in PLAIN.

Python 3.2 or newer is required for TLS.

"""

import imaplib

from .. import config, log

IMAP_SERVER = config.get("auth", "imap_hostname")
IMAP_SERVER_PORT = config.getint("auth", "imap_port")
IMAP_USE_SSL = config.getboolean("auth", "imap_ssl")


def is_authenticated(user, password):
    """Check if ``user``/``password`` couple is valid."""
    if not user or not password:
        return False

    log.LOGGER.debug(
        "Connecting to IMAP server %s:%s." % (IMAP_SERVER, IMAP_SERVER_PORT,))

    connection_is_secure = False
    if IMAP_USE_SSL:
        connection = imaplib.IMAP4_SSL(host=IMAP_SERVER, port=IMAP_SERVER_PORT)
        connection_is_secure = True
    else:
        connection = imaplib.IMAP4(host=IMAP_SERVER, port=IMAP_SERVER_PORT)

    server_is_local = (IMAP_SERVER == "localhost")

    if not connection_is_secure:
        try:
            connection.starttls()
            log.LOGGER.debug("IMAP server connection changed to TLS.")
            connection_is_secure = True
        except AttributeError:
            if not server_is_local:
                log.LOGGER.error(
                    "Python 3.2 or newer is required for IMAP + TLS.")
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exception:
            log.LOGGER.warning(
                "IMAP server at %s failed to accept TLS connection "
                "because of: %s" % (IMAP_SERVER, exception))

    if server_is_local and not connection_is_secure:
        log.LOGGER.warning(
            "IMAP server is local. "
            "Will allow transmitting unencrypted credentials.")

    if connection_is_secure or server_is_local:
        try:
            connection.login(user, password)
            connection.logout()
            log.LOGGER.debug(
                "Authenticated IMAP user %s "
                "via %s." % (user, IMAP_SERVER))
            return True
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exception:
            log.LOGGER.error(
                "IMAP server could not authenticate user %s "
                "because of: %s" % (user, exception))
    else:
        log.LOGGER.critical(
            "IMAP server did not support TLS and is not ``localhost``. "
            "Refusing to transmit passwords under these conditions. "
            "Authentication attempt aborted.")
    return False  # authentication failed

########NEW FILE########
__FILENAME__ = LDAP
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2011 Corentin Le Bail
# Copyright © 2011-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
LDAP authentication.

Authentication based on the ``python-ldap`` module
(http://www.python-ldap.org/).

"""

import ldap

from .. import config, log


BASE = config.get("auth", "ldap_base")
ATTRIBUTE = config.get("auth", "ldap_attribute")
FILTER = config.get("auth", "ldap_filter")
CONNEXION = ldap.initialize(config.get("auth", "ldap_url"))
BINDDN = config.get("auth", "ldap_binddn")
PASSWORD = config.get("auth", "ldap_password")
SCOPE = getattr(ldap, "SCOPE_%s" % config.get("auth", "ldap_scope").upper())


def is_authenticated(user, password):
    """Check if ``user``/``password`` couple is valid."""
    global CONNEXION

    try:
        CONNEXION.whoami_s()
    except:
        log.LOGGER.debug("Reconnecting the LDAP server")
        CONNEXION = ldap.initialize(config.get("auth", "ldap_url"))

    if BINDDN and PASSWORD:
        log.LOGGER.debug("Initial LDAP bind as %s" % BINDDN)
        CONNEXION.simple_bind_s(BINDDN, PASSWORD)

    distinguished_name = "%s=%s" % (ATTRIBUTE, ldap.dn.escape_dn_chars(user))
    log.LOGGER.debug(
        "LDAP bind for %s in base %s" % (distinguished_name, BASE))

    if FILTER:
        filter_string = "(&(%s)%s)" % (distinguished_name, FILTER)
    else:
        filter_string = distinguished_name
    log.LOGGER.debug("Used LDAP filter: %s" % filter_string)

    users = CONNEXION.search_s(BASE, SCOPE, filter_string)
    if users:
        log.LOGGER.debug("User %s found" % user)
        try:
            CONNEXION.simple_bind_s(users[0][0], password or "")
        except ldap.LDAPError:
            log.LOGGER.debug("Invalid credentials")
        else:
            log.LOGGER.debug("LDAP bind OK")
            return True
    else:
        log.LOGGER.debug("User %s not found" % user)

    log.LOGGER.debug("LDAP bind failed")
    return False

########NEW FILE########
__FILENAME__ = PAM
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2011 Henry-Nicolas Tourneur
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
PAM authentication.

Authentication based on the ``pam-python`` module.

"""

import grp
import pam
import pwd

from .. import config, log


GROUP_MEMBERSHIP = config.get("auth", "pam_group_membership")


def is_authenticated(user, password):
    """Check if ``user``/``password`` couple is valid."""
    if user is None or password is None:
        return False

    # Check whether the user exists in the PAM system
    try:
        pwd.getpwnam(user).pw_uid
    except KeyError:
        log.LOGGER.debug("User %s not found" % user)
        return False
    else:
        log.LOGGER.debug("User %s found" % user)

    # Check whether the group exists
    try:
        # Obtain supplementary groups
        members = grp.getgrnam(GROUP_MEMBERSHIP).gr_mem
    except KeyError:
        log.LOGGER.debug(
            "The PAM membership required group (%s) doesn't exist" %
            GROUP_MEMBERSHIP)
        return False

    # Check whether the user exists
    try:
        # Get user primary group
        primary_group = grp.getgrgid(pwd.getpwnam(user).pw_gid).gr_name
    except KeyError:
        log.LOGGER.debug("The PAM user (%s) doesn't exist" % user)
        return False

    # Check whether the user belongs to the required group
    # (primary or supplementary)
    if primary_group == GROUP_MEMBERSHIP or user in members:
        log.LOGGER.debug(
            "The PAM user belongs to the required group (%s)" %
            GROUP_MEMBERSHIP)
        # Check the password
        if pam.authenticate(user, password):
            return True
        else:
            log.LOGGER.debug("Wrong PAM password")
    else:
        log.LOGGER.debug(
            "The PAM user doesn't belong to the required group (%s)" %
            GROUP_MEMBERSHIP)

    return False

########NEW FILE########
__FILENAME__ = remote_user
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012 Ehsanul Hoque
# Copyright © 2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Trusting the HTTP server auth mechanism.

"""

from .. import log


def is_authenticated(user, password):
    """Check if ``user`` is defined and assuming it's valid."""
    log.LOGGER.debug("Got user %r from HTTP server." % user)
    return user is not None

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008-2013 Guillaume Ayoub
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale configuration module.

Give a configparser-like interface to read and write configuration.

"""

import os
import sys
# Manage Python2/3 different modules
# pylint: disable=F0401
try:
    from configparser import RawConfigParser as ConfigParser
except ImportError:
    from ConfigParser import RawConfigParser as ConfigParser
# pylint: enable=F0401


# Default configuration
INITIAL_CONFIG = {
    "server": {
        "hosts": "0.0.0.0:5232",
        "daemon": "False",
        "pid": "",
        "ssl": "False",
        "certificate": "/etc/apache2/ssl/server.crt",
        "key": "/etc/apache2/ssl/server.key",
        "protocol": "PROTOCOL_SSLv23",
        "ciphers": "",
        "dns_lookup": "True",
        "base_prefix": "/",
        "realm": "Radicale - Password Required"},
    "encoding": {
        "request": "utf-8",
        "stock": "utf-8"},
    "auth": {
        "type": "None",
        "custom_handler": "",
        "htpasswd_filename": "/etc/radicale/users",
        "htpasswd_encryption": "crypt",
        "imap_hostname": "localhost",
        "imap_port": "143",
        "imap_ssl": "False",
        "ldap_url": "ldap://localhost:389/",
        "ldap_base": "ou=users,dc=example,dc=com",
        "ldap_attribute": "uid",
        "ldap_filter": "",
        "ldap_binddn": "",
        "ldap_password": "",
        "ldap_scope": "OneLevel",
        "pam_group_membership": "",
        "courier_socket": "",
        "http_url": "",
        "http_user_parameter": "",
        "http_password_parameter": ""},
    "git": {
        "committer": "Radicale <radicale@example.com>"},
    "rights": {
        "type": "None",
        "custom_handler": "",
        "file": "~/.config/radicale/rights"},
    "storage": {
        "type": "filesystem",
        "custom_handler": "",
        "filesystem_folder": os.path.expanduser(
            "~/.config/radicale/collections"),
        "database_url": ""},
    "logging": {
        "config": "/etc/radicale/logging",
        "debug": "False",
        "full_environment": "False"}}

# Create a ConfigParser and configure it
_CONFIG_PARSER = ConfigParser()

for section, values in INITIAL_CONFIG.items():
    _CONFIG_PARSER.add_section(section)
    for key, value in values.items():
        _CONFIG_PARSER.set(section, key, value)

_CONFIG_PARSER.read("/etc/radicale/config")
_CONFIG_PARSER.read(os.path.expanduser("~/.config/radicale/config"))
if "RADICALE_CONFIG" in os.environ:
    _CONFIG_PARSER.read(os.environ["RADICALE_CONFIG"])

# Wrap config module into ConfigParser instance
sys.modules[__name__] = _CONFIG_PARSER

########NEW FILE########
__FILENAME__ = ical
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale collection classes.

Define the main classes of a collection as seen from the server.

"""

import os
import posixpath
import hashlib
from uuid import uuid4
from random import randint
from contextlib import contextmanager


def serialize(tag, headers=(), items=()):
    """Return a text corresponding to given collection ``tag``.

    The text may have the given ``headers`` and ``items`` added around the
    items if needed (ie. for calendars).

    """
    if tag == "VADDRESSBOOK":
        lines = [item.text for item in items]
    else:
        lines = ["BEGIN:%s" % tag]
        for part in (headers, items):
            if part:
                lines.append("\n".join(item.text for item in part))
        lines.append("END:%s\n" % tag)
    return "\n".join(lines)


def unfold(text):
    """Unfold multi-lines attributes.

    Read rfc5545-3.1 for info.

    """
    lines = []
    for line in text.splitlines():
        if lines and (line.startswith(" ") or line.startswith("\t")):
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


class Item(object):
    """Internal iCal item."""
    def __init__(self, text, name=None):
        """Initialize object from ``text`` and different ``kwargs``."""
        self.text = text
        self._name = name

        # We must synchronize the name in the text and in the object.
        # An item must have a name, determined in order by:
        #
        # - the ``name`` parameter
        # - the ``X-RADICALE-NAME`` iCal property (for Events, Todos, Journals)
        # - the ``UID`` iCal property (for Events, Todos, Journals)
        # - the ``TZID`` iCal property (for Timezones)
        if not self._name:
            for line in unfold(self.text):
                if line.startswith("X-RADICALE-NAME:"):
                    self._name = line.replace("X-RADICALE-NAME:", "").strip()
                    break
                elif line.startswith("TZID:"):
                    self._name = line.replace("TZID:", "").strip()
                    break
                elif line.startswith("UID:"):
                    self._name = line.replace("UID:", "").strip()
                    # Do not break, a ``X-RADICALE-NAME`` can appear next

        if self._name:
            # Remove brackets that may have been put by Outlook
            self._name = self._name.strip("{}")
            if "\nX-RADICALE-NAME:" in text:
                for line in unfold(self.text):
                    if line.startswith("X-RADICALE-NAME:"):
                        self.text = self.text.replace(
                            line, "X-RADICALE-NAME:%s" % self._name)
            else:
                self.text = self.text.replace(
                    "\nEND:", "\nX-RADICALE-NAME:%s\nEND:" % self._name)
        else:
            # workaround to get unicode on both python2 and 3
            self._name = uuid4().hex.encode("ascii").decode("ascii")
            self.text = self.text.replace(
                "\nEND:", "\nX-RADICALE-NAME:%s\nEND:" % self._name)

    def __hash__(self):
        return hash(self.text)

    def __eq__(self, item):
        return isinstance(item, Item) and self.text == item.text

    @property
    def etag(self):
        """Item etag.

        Etag is mainly used to know if an item has changed.

        """
        md5 = hashlib.md5()
        md5.update(self.text.encode("utf-8"))
        return '"%s"' % md5.hexdigest()

    @property
    def name(self):
        """Item name.

        Name is mainly used to give an URL to the item.

        """
        return self._name


class Header(Item):
    """Internal header class."""


class Timezone(Item):
    """Internal timezone class."""
    tag = "VTIMEZONE"


class Component(Item):
    """Internal main component of a collection."""


class Event(Component):
    """Internal event class."""
    tag = "VEVENT"
    mimetype = "text/calendar"


class Todo(Component):
    """Internal todo class."""
    tag = "VTODO"  # pylint: disable=W0511
    mimetype = "text/calendar"


class Journal(Component):
    """Internal journal class."""
    tag = "VJOURNAL"
    mimetype = "text/calendar"


class Card(Component):
    """Internal card class."""
    tag = "VCARD"
    mimetype = "text/vcard"


class Collection(object):
    """Internal collection item.

    This class must be overridden and replaced by a storage backend.

    """
    def __init__(self, path, principal=False):
        """Initialize the collection.

        ``path`` must be the normalized relative path of the collection, using
        the slash as the folder delimiter, with no leading nor trailing slash.

        """
        self.encoding = "utf-8"
        split_path = path.split("/")
        self.path = path if path != "." else ""
        if principal and split_path and self.is_node(self.path):
            # Already existing principal collection
            self.owner = split_path[0]
        elif len(split_path) > 1:
            # URL with at least one folder
            self.owner = split_path[0]
        else:
            self.owner = None
        self.is_principal = principal

    @classmethod
    def from_path(cls, path, depth="1", include_container=True):
        """Return a list of collections and items under the given ``path``.

        If ``depth`` is "0", only the actual object under ``path`` is
        returned.

        If ``depth`` is anything but "0", it is considered as "1" and direct
        children are included in the result. If ``include_container`` is
        ``True`` (the default), the containing object is included in the
        result.

        The ``path`` is relative.

        """
        # path == None means wrong URL
        if path is None:
            return []

        # First do normpath and then strip, to prevent access to FOLDER/../
        sane_path = posixpath.normpath(path.replace(os.sep, "/")).strip("/")
        attributes = sane_path.split("/")
        if not attributes:
            return []

        # Try to guess if the path leads to a collection or an item
        if (cls.is_leaf("/".join(attributes[:-1])) or not
                path.endswith(("/", "/caldav", "/carddav"))):
            attributes.pop()

        result = []
        path = "/".join(attributes)

        principal = len(attributes) <= 1
        if cls.is_node(path):
            if depth == "0":
                result.append(cls(path, principal))
            else:
                if include_container:
                    result.append(cls(path, principal))
                for child in cls.children(path):
                    result.append(child)
        else:
            if depth == "0":
                result.append(cls(path))
            else:
                collection = cls(path, principal)
                if include_container:
                    result.append(collection)
                result.extend(collection.components)
        return result

    def save(self, text):
        """Save the text into the collection."""
        raise NotImplementedError

    def delete(self):
        """Delete the collection."""
        raise NotImplementedError

    @property
    def text(self):
        """Collection as plain text."""
        raise NotImplementedError

    @classmethod
    def children(cls, path):
        """Yield the children of the collection at local ``path``."""
        raise NotImplementedError

    @classmethod
    def is_node(cls, path):
        """Return ``True`` if relative ``path`` is a node.

        A node is a WebDAV collection whose members are other collections.

        """
        raise NotImplementedError

    @classmethod
    def is_leaf(cls, path):
        """Return ``True`` if relative ``path`` is a leaf.

        A leaf is a WebDAV collection whose members are not collections.

        """
        raise NotImplementedError

    @property
    def last_modified(self):
        """Get the last time the collection has been modified.

        The date is formatted according to rfc1123-5.2.14.

        """
        raise NotImplementedError

    @property
    @contextmanager
    def props(self):
        """Get the collection properties."""
        raise NotImplementedError

    @property
    def exists(self):
        """``True`` if the collection exists on the storage, else ``False``."""
        return self.is_node(self.path) or self.is_leaf(self.path)

    @staticmethod
    def _parse(text, item_types, name=None):
        """Find items with type in ``item_types`` in ``text``.

        If ``name`` is given, give this name to new items in ``text``.

        Return a list of items.

        """
        item_tags = {}
        for item_type in item_types:
            item_tags[item_type.tag] = item_type

        items = {}

        lines = unfold(text)
        in_item = False

        for line in lines:
            if line.startswith("BEGIN:") and not in_item:
                item_tag = line.replace("BEGIN:", "").strip()
                if item_tag in item_tags:
                    in_item = True
                    item_lines = []

            if in_item:
                item_lines.append(line)
                if line.startswith("END:%s" % item_tag):
                    in_item = False
                    item_type = item_tags[item_tag]
                    item_text = "\n".join(item_lines)
                    item_name = None if item_tag == "VTIMEZONE" else name
                    item = item_type(item_text, item_name)
                    if item.name in items:
                        text = "\n".join((item.text, items[item.name].text))
                        items[item.name] = item_type(text, item.name)
                    else:
                        items[item.name] = item

        return list(items.values())

    def get_item(self, name):
        """Get collection item called ``name``."""
        for item in self.items:
            if item.name == name:
                return item

    def append(self, name, text):
        """Append items from ``text`` to collection.

        If ``name`` is given, give this name to new items in ``text``.

        """
        items = self.items

        for new_item in self._parse(
                text, (Timezone, Event, Todo, Journal, Card), name):
            if new_item.name not in (item.name for item in items):
                items.append(new_item)

        self.write(items=items)

    def remove(self, name):
        """Remove object named ``name`` from collection."""
        components = [
            component for component in self.components
            if component.name != name]

        items = self.timezones + components
        self.write(items=items)

    def replace(self, name, text):
        """Replace content by ``text`` in collection objet called ``name``."""
        self.remove(name)
        self.append(name, text)

    def write(self, headers=None, items=None):
        """Write collection with given parameters."""
        headers = headers or self.headers or (
            Header("PRODID:-//Radicale//NONSGML Radicale Server//EN"),
            Header("VERSION:%s" % self.version))
        items = items if items is not None else self.items

        text = serialize(self.tag, headers, items)
        self.save(text)

    def set_mimetype(self, mimetype):
        """Set the mimetype of the collection."""
        with self.props as props:
            if "tag" not in props:
                if mimetype == "text/vcard":
                    props["tag"] = "VADDRESSBOOK"
                else:
                    props["tag"] = "VCALENDAR"

    @property
    def tag(self):
        """Type of the collection."""
        with self.props as props:
            if "tag" not in props:
                try:
                    tag = open(self.path).readlines()[0][6:].rstrip()
                except IOError:
                    if self.path.endswith((".vcf", "/carddav")):
                        props["tag"] = "VADDRESSBOOK"
                    else:
                        props["tag"] = "VCALENDAR"
                else:
                    if tag in ("VADDRESSBOOK", "VCARD"):
                        props["tag"] = "VADDRESSBOOK"
                    else:
                        props["tag"] = "VCALENDAR"
            return props["tag"]

    @property
    def mimetype(self):
        """Mimetype of the collection."""
        if self.tag == "VADDRESSBOOK":
            return "text/vcard"
        elif self.tag == "VCALENDAR":
            return "text/calendar"

    @property
    def resource_type(self):
        """Resource type of the collection."""
        if self.tag == "VADDRESSBOOK":
            return "addressbook"
        elif self.tag == "VCALENDAR":
            return "calendar"

    @property
    def etag(self):
        """Etag from collection."""
        md5 = hashlib.md5()
        md5.update(self.text.encode("utf-8"))
        return '"%s"' % md5.hexdigest()

    @property
    def name(self):
        """Collection name."""
        with self.props as props:
            return props.get("D:displayname", self.path.split(os.path.sep)[-1])

    @property
    def color(self):
        """Collection color."""
        with self.props as props:
            if "A:calendar-color" not in props:
                props["A:calendar-color"] = "#%x" % randint(0, 255 ** 3 - 1)
            return props["A:calendar-color"]

    @property
    def headers(self):
        """Find headers items in collection."""
        header_lines = []

        lines = unfold(self.text)
        for header in ("PRODID", "VERSION"):
            for line in lines:
                if line.startswith("%s:" % header):
                    header_lines.append(Header(line))
                    break

        return header_lines

    @property
    def items(self):
        """Get list of all items in collection."""
        return self._parse(self.text, (Event, Todo, Journal, Card, Timezone))

    @property
    def components(self):
        """Get list of all components in collection."""
        return self._parse(self.text, (Event, Todo, Journal, Card))

    @property
    def events(self):
        """Get list of ``Event`` items in calendar."""
        return self._parse(self.text, (Event,))

    @property
    def todos(self):
        """Get list of ``Todo`` items in calendar."""
        return self._parse(self.text, (Todo,))

    @property
    def journals(self):
        """Get list of ``Journal`` items in calendar."""
        return self._parse(self.text, (Journal,))

    @property
    def timezones(self):
        """Get list of ``Timezone`` items in calendar."""
        return self._parse(self.text, (Timezone,))

    @property
    def cards(self):
        """Get list of ``Card`` items in address book."""
        return self._parse(self.text, (Card,))

    @property
    def owner_url(self):
        """Get the collection URL according to its owner."""
        return "/%s/" % self.owner if self.owner else None

    @property
    def url(self):
        """Get the standard collection URL."""
        return "%s/" % self.path

    @property
    def version(self):
        """Get the version of the collection type."""
        return "3.0" if self.tag == "VADDRESSBOOK" else "2.0"

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2011-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale logging module.

Manage logging from a configuration file. For more information, see:
http://docs.python.org/library/logging.config.html

"""

import os
import sys
import logging
import logging.config

from . import config


LOGGER = logging.getLogger()


def start():
    """Start the logging according to the configuration."""
    filename = os.path.expanduser(config.get("logging", "config"))
    debug = config.getboolean("logging", "debug")

    if os.path.exists(filename):
        # Configuration taken from file
        logging.config.fileConfig(filename)
        if debug:
            LOGGER.setLevel(logging.DEBUG)
            for handler in LOGGER.handlers:
                handler.setLevel(logging.DEBUG)
    else:
        # Default configuration, standard output
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
        if debug:
            LOGGER.setLevel(logging.DEBUG)
            LOGGER.debug(
                "Logging configuration file '%s' not found, using stdout." %
                filename)

########NEW FILE########
__FILENAME__ = regex
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Rights management.

Rights are based on a regex-based file whose name is specified in the config
(section "right", key "file").

Authentication login is matched against the "user" key, and collection's path
is matched against the "collection" key. You can use Python's ConfigParser
interpolation values %(login)s and %(path)s. You can also get groups from the
user regex in the collection with {0}, {1}, etc.

For example, for the "user" key, ".+" means "authenticated user" and ".*"
means "anybody" (including anonymous users).

Section names are only used for naming the rule.

Leading or ending slashes are trimmed from collection's path.

"""

import re
import os.path

from .. import config, log

# Manage Python2/3 different modules
# pylint: disable=F0401
try:
    from configparser import ConfigParser
    from io import StringIO
except ImportError:
    from ConfigParser import ConfigParser
    from StringIO import StringIO
# pylint: enable=F0401


DEFINED_RIGHTS = {
    "authenticated": "[rw]\nuser:.+\ncollection:.*\npermission:rw",
    "owner_write": "[r]\nuser:.+\ncollection:.*\npermission:r\n"
                   "[w]\nuser:.+\ncollection:^%(login)s/.+$\npermission:w",
    "owner_only": "[rw]\nuser:.+\ncollection:^%(login)s/.+$\npermission:rw",
}


def _read_from_sections(user, collection_url, permission):
    """Get regex sections."""
    filename = os.path.expanduser(config.get("rights", "file"))
    rights_type = config.get("rights", "type").lower()
    regex = ConfigParser({"login": user, "path": collection_url})
    if rights_type in DEFINED_RIGHTS:
        log.LOGGER.debug("Rights type '%s'" % rights_type)
        regex.readfp(StringIO(DEFINED_RIGHTS[rights_type]))
    elif rights_type == "from_file":
        log.LOGGER.debug("Reading rights from file %s" % filename)
        if not regex.read(filename):
            log.LOGGER.error("File '%s' not found for rights" % filename)
            return False
    else:
        log.LOGGER.error("Unknown rights type '%s'" % rights_type)
        return False

    for section in regex.sections():
        re_user = regex.get(section, "user")
        re_collection = regex.get(section, "collection")
        log.LOGGER.debug(
            "Test if '%s:%s' matches against '%s:%s' from section '%s'" % (
                user, collection_url, re_user, re_collection, section))
        user_match = re.match(re_user, user)
        if user_match:
            re_collection = re_collection.format(*user_match.groups())
            if re.match(re_collection, collection_url):
                log.LOGGER.debug("Section '%s' matches" % section)
                if permission in regex.get(section, "permission"):
                    return True
            else:
                log.LOGGER.debug("Section '%s' does not match" % section)
    return False


def authorized(user, collection, permission):
    """Check if the user is allowed to read or write the collection.

       If the user is empty it checks for anonymous rights
    """
    collection_url = collection.url.rstrip("/") or "/"
    if collection_url in (".well-known/carddav", ".well-known/caldav"):
        return permission == "r"
    rights_type = config.get("rights", "type").lower()
    return (
        rights_type == "none" or
        _read_from_sections(user or "", collection_url, permission))

########NEW FILE########
__FILENAME__ = database
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
SQLAlchemy storage backend.

"""

import time
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Unicode, Integer, ForeignKey
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

from .. import config, ical


# These are classes, not constants
# pylint: disable=C0103
Base = declarative_base()
Session = sessionmaker()
Session.configure(bind=create_engine(config.get("storage", "database_url")))
# pylint: enable=C0103


class DBCollection(Base):
    """Table of collections."""
    __tablename__ = "collection"

    path = Column(Unicode, primary_key=True)
    parent_path = Column(Unicode, ForeignKey("collection.path"))

    parent = relationship(
        "DBCollection", backref="children", remote_side=[path])


class DBItem(Base):
    """Table of collection's items."""
    __tablename__ = "item"

    name = Column(Unicode, primary_key=True)
    tag = Column(Unicode)
    collection_path = Column(Unicode, ForeignKey("collection.path"))

    collection = relationship("DBCollection", backref="items")


class DBHeader(Base):
    """Table of item's headers."""
    __tablename__ = "header"

    name = Column(Unicode, primary_key=True)
    value = Column(Unicode)
    collection_path = Column(
        Unicode, ForeignKey("collection.path"), primary_key=True)

    collection = relationship("DBCollection", backref="headers")


class DBLine(Base):
    """Table of item's lines."""
    __tablename__ = "line"

    name = Column(Unicode)
    value = Column(Unicode)
    item_name = Column(Unicode, ForeignKey("item.name"))
    timestamp = Column(
        Integer, default=lambda: time.time() * 10 ** 6, primary_key=True)

    item = relationship("DBItem", backref="lines", order_by=timestamp)


class DBProperty(Base):
    """Table of collection's properties."""
    __tablename__ = "property"

    name = Column(Unicode, primary_key=True)
    value = Column(Unicode)
    collection_path = Column(
        Unicode, ForeignKey("collection.path"), primary_key=True)

    collection = relationship(
        "DBCollection", backref="properties", cascade="delete")


class Collection(ical.Collection):
    """Collection stored in a database."""
    def __init__(self, path, principal=False):
        self.session = Session()
        super(Collection, self).__init__(path, principal)

    def __del__(self):
        self.session.commit()

    def _query(self, item_types):
        """Get collection's items matching ``item_types``."""
        item_objects = []
        for item_type in item_types:
            items = (
                self.session.query(DBItem)
                .filter_by(collection_path=self.path, tag=item_type.tag)
                .order_by(DBItem.name).all())
            for item in items:
                text = "\n".join(
                    "%s:%s" % (line.name, line.value) for line in item.lines)
                item_objects.append(item_type(text, item.name))
        return item_objects

    @property
    def _modification_time(self):
        """Collection's last modification time."""
        timestamp = (
            self.session.query(func.max(DBLine.timestamp))
            .join(DBItem).filter_by(collection_path=self.path).first()[0])
        if timestamp:
            return datetime.fromtimestamp(float(timestamp) / 10 ** 6)
        else:
            return datetime.now()

    @property
    def _db_collection(self):
        """Collection's object mapped to the table line."""
        return self.session.query(DBCollection).get(self.path)

    def write(self, headers=None, items=None):
        headers = headers or self.headers or (
            ical.Header("PRODID:-//Radicale//NONSGML Radicale Server//EN"),
            ical.Header("VERSION:%s" % self.version))
        items = items if items is not None else self.items

        if self._db_collection:
            for item in self._db_collection.items:
                for line in item.lines:
                    self.session.delete(line)
                self.session.delete(item)
            for header in self._db_collection.headers:
                self.session.delete(header)
        else:
            db_collection = DBCollection()
            db_collection.path = self.path
            db_collection.parent_path = "/".join(self.path.split("/")[:-1])
            self.session.add(db_collection)

        for header in headers:
            db_header = DBHeader()
            db_header.name, db_header.value = header.text.split(":", 1)
            db_header.collection_path = self.path
            self.session.add(db_header)

        for item in items:
            db_item = DBItem()
            db_item.name = item.name
            db_item.tag = item.tag
            db_item.collection_path = self.path
            self.session.add(db_item)

            for line in ical.unfold(item.text):
                db_line = DBLine()
                db_line.name, db_line.value = line.split(":", 1)
                db_line.item_name = item.name
                self.session.add(db_line)

    def delete(self):
        self.session.delete(self._db_collection)

    @property
    def text(self):
        return ical.serialize(self.tag, self.headers, self.items)

    @property
    def etag(self):
        return '"%s"' % hash(self._modification_time)

    @property
    def headers(self):
        headers = (
            self.session.query(DBHeader)
            .filter_by(collection_path=self.path)
            .order_by(DBHeader.name).all())
        return [
            ical.Header("%s:%s" % (header.name, header.value))
            for header in headers]

    @classmethod
    def children(cls, path):
        session = Session()
        children = (
            session.query(DBCollection)
            .filter_by(parent_path=path or "").all())
        collections = [cls(child.path) for child in children]
        session.close()
        return collections

    @classmethod
    def is_node(cls, path):
        if not path:
            return True
        session = Session()
        result = (
            session.query(DBCollection)
            .filter_by(parent_path=path or "").count() > 0)
        session.close()
        return result

    @classmethod
    def is_leaf(cls, path):
        if not path:
            return False
        session = Session()
        result = (
            session.query(DBItem)
            .filter_by(collection_path=path or "").count() > 0)
        session.close()
        return result

    @property
    def last_modified(self):
        return time.strftime(
            "%a, %d %b %Y %H:%M:%S +0000", self._modification_time.timetuple())

    @property
    @contextmanager
    def props(self):
        # On enter
        properties = {}
        db_properties = (
            self.session.query(DBProperty)
            .filter_by(collection_path=self.path).all())
        for prop in db_properties:
            properties[prop.name] = prop.value
        old_properties = properties.copy()
        yield properties
        # On exit
        if self._db_collection and old_properties != properties:
            for prop in db_properties:
                self.session.delete(prop)
            for name, value in properties.items():
                prop = DBProperty()
                prop.name = name
                prop.value = value
                prop.collection_path = self.path
                self.session.add(prop)

    @property
    def items(self):
        return self._query(
            (ical.Event, ical.Todo, ical.Journal, ical.Card, ical.Timezone))

    @property
    def components(self):
        return self._query((ical.Event, ical.Todo, ical.Journal, ical.Card))

    @property
    def events(self):
        return self._query((ical.Event,))

    @property
    def todos(self):
        return self._query((ical.Todo,))

    @property
    def journals(self):
        return self._query((ical.Journal,))

    @property
    def timezones(self):
        return self._query((ical.Timezone,))

    @property
    def cards(self):
        return self._query((ical.Card,))

    def save(self):
        """Save the text into the collection.

        This method is not used for databases.

        """

########NEW FILE########
__FILENAME__ = filesystem
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Filesystem storage backend.

"""

import codecs
import os
import posixpath
import json
import time
import sys
from contextlib import contextmanager
from .. import config, ical


FOLDER = os.path.expanduser(config.get("storage", "filesystem_folder"))
FILESYSTEM_ENCODING = sys.getfilesystemencoding()

try:
    from dulwich.repo import Repo
    GIT_REPOSITORY = Repo(FOLDER)
except:
    GIT_REPOSITORY = None


# This function overrides the builtin ``open`` function for this module
# pylint: disable=W0622
@contextmanager
def open(path, mode="r"):
    """Open a file at ``path`` with encoding set in the configuration."""
    # On enter
    abs_path = os.path.join(FOLDER, path.replace("/", os.sep))
    with codecs.open(abs_path, mode, config.get("encoding", "stock")) as fd:
        yield fd
    # On exit
    if GIT_REPOSITORY and mode == "w":
        path = os.path.relpath(abs_path, FOLDER)
        GIT_REPOSITORY.stage([path])
        committer = config.get("git", "committer")
        GIT_REPOSITORY.do_commit("Commit by Radicale", committer=committer)
# pylint: enable=W0622


class Collection(ical.Collection):
    """Collection stored in a flat ical file."""
    @property
    def _path(self):
        """Absolute path of the file at local ``path``."""
        return os.path.join(FOLDER, self.path.replace("/", os.sep))

    @property
    def _props_path(self):
        """Absolute path of the file storing the collection properties."""
        return self._path + ".props"

    def _create_dirs(self):
        """Create folder storing the collection if absent."""
        if not os.path.exists(os.path.dirname(self._path)):
            os.makedirs(os.path.dirname(self._path))

    def save(self, text):
        self._create_dirs()
        with open(self._path, "w") as fd:
            fd.write(text)

    def delete(self):
        os.remove(self._path)
        os.remove(self._props_path)

    @property
    def text(self):
        try:
            with open(self._path) as fd:
                return fd.read()
        except IOError:
            return ""

    @classmethod
    def children(cls, path):
        abs_path = os.path.join(FOLDER, path.replace("/", os.sep))
        _, directories, files = next(os.walk(abs_path))
        for filename in directories + files:
            rel_filename = posixpath.join(path, filename)
            if cls.is_node(rel_filename) or cls.is_leaf(rel_filename):
                yield cls(rel_filename)

    @classmethod
    def is_node(cls, path):
        abs_path = os.path.join(FOLDER, path.replace("/", os.sep))
        return os.path.isdir(abs_path)

    @classmethod
    def is_leaf(cls, path):
        abs_path = os.path.join(FOLDER, path.replace("/", os.sep))
        return os.path.isfile(abs_path) and not abs_path.endswith(".props")

    @property
    def last_modified(self):
        modification_time = time.gmtime(os.path.getmtime(self._path))
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", modification_time)

    @property
    @contextmanager
    def props(self):
        # On enter
        properties = {}
        if os.path.exists(self._props_path):
            with open(self._props_path) as prop_file:
                properties.update(json.load(prop_file))
        old_properties = properties.copy()
        yield properties
        # On exit
        self._create_dirs()
        if old_properties != properties:
            with open(self._props_path, "w") as prop_file:
                json.dump(properties, prop_file)

########NEW FILE########
__FILENAME__ = multifilesystem
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2013 Guillaume Ayoub
# Copyright © 2013 Jean-Marc Martins
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Multi files per calendar filesystem storage backend.

"""

import os
import shutil
import time
import sys

from . import filesystem
from .. import ical


class Collection(filesystem.Collection):
    """Collection stored in several files per calendar."""
    def _create_dirs(self):
        if not os.path.exists(self._path):
            os.makedirs(self._path)

    @property
    def headers(self):
        return (
            ical.Header("PRODID:-//Radicale//NONSGML Radicale Server//EN"),
            ical.Header("VERSION:%s" % self.version))

    def write(self, headers=None, items=None):
        self._create_dirs()
        headers = headers or self.headers
        items = items if items is not None else self.items
        timezones = list(set(i for i in items if isinstance(i, ical.Timezone)))
        components = [i for i in items if isinstance(i, ical.Component)]
        for component in components:
            text = ical.serialize(self.tag, headers, [component] + timezones)
            name = (
                component.name if sys.version_info[0] >= 3 else
                component.name.encode(filesystem.FILESYSTEM_ENCODING))
            path = os.path.join(self._path, name)
            with filesystem.open(path, "w") as fd:
                fd.write(text)

    def delete(self):
        shutil.rmtree(self._path)

    def remove(self, name):
        if os.path.exists(os.path.join(self._path, name)):
            os.remove(os.path.join(self._path, name))

    @property
    def text(self):
        components = (
            ical.Timezone, ical.Event, ical.Todo, ical.Journal, ical.Card)
        items = set()
        try:
            for filename in os.listdir(self._path):
                with filesystem.open(os.path.join(self._path, filename)) as fd:
                    items.update(self._parse(fd.read(), components))
        except IOError:
            return ""
        else:
            return ical.serialize(
                self.tag, self.headers, sorted(items, key=lambda x: x.name))

    @classmethod
    def is_node(cls, path):
        path = os.path.join(filesystem.FOLDER, path.replace("/", os.sep))
        return os.path.isdir(path) and not os.path.exists(path + ".props")

    @classmethod
    def is_leaf(cls, path):
        path = os.path.join(filesystem.FOLDER, path.replace("/", os.sep))
        return os.path.isdir(path) and os.path.exists(path + ".props")

    @property
    def last_modified(self):
        last = max([
            os.path.getmtime(os.path.join(self._path, filename))
            for filename in os.listdir(self._path)] or [0])
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(last))

########NEW FILE########
__FILENAME__ = xmlutils
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
XML and iCal requests manager.

Note that all these functions need to receive unicode objects for full
iCal requests (PUT) and string objects with charset correctly defined
in them for XML requests (all but PUT).

"""

try:
    from collections import OrderedDict
except ImportError:
    # Python 2.6 has no OrderedDict, use a dict instead
    OrderedDict = dict  # pylint: disable=C0103

# Manage Python2/3 different modules
# pylint: disable=F0401,E0611
try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote
# pylint: enable=F0401,E0611

import re
import xml.etree.ElementTree as ET

from . import client, config, ical


NAMESPACES = {
    "A": "http://apple.com/ns/ical/",
    "C": "urn:ietf:params:xml:ns:caldav",
    "CR": "urn:ietf:params:xml:ns:carddav",
    "D": "DAV:",
    "CS": "http://calendarserver.org/ns/",
    "ICAL": "http://apple.com/ns/ical/",
    "ME": "http://me.com/_namespace/"}


NAMESPACES_REV = {}


for short, url in NAMESPACES.items():
    NAMESPACES_REV[url] = short
    if hasattr(ET, "register_namespace"):
        # Register namespaces cleanly with Python 2.7+ and 3.2+ ...
        ET.register_namespace("" if short == "D" else short, url)
    else:
        # ... and badly with Python 2.6 and 3.1
        ET._namespace_map[url] = short  # pylint: disable=W0212


CLARK_TAG_REGEX = re.compile(r"""
    {                        # {
    (?P<namespace>[^}]*)     # namespace URL
    }                        # }
    (?P<tag>.*)              # short tag name
    """, re.VERBOSE)


def _pretty_xml(element, level=0):
    """Indent an ElementTree ``element`` and its children."""
    i = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = i + "  "
        if not element.tail or not element.tail.strip():
            element.tail = i
        for sub_element in element:
            _pretty_xml(sub_element, level + 1)
        # ``sub_element`` is always defined as len(element) > 0
        # pylint: disable=W0631
        if not sub_element.tail or not sub_element.tail.strip():
            sub_element.tail = i
        # pylint: enable=W0631
    else:
        if level and (not element.tail or not element.tail.strip()):
            element.tail = i
    if not level:
        output_encoding = config.get("encoding", "request")
        return ('<?xml version="1.0"?>\n' + ET.tostring(
            element, "utf-8").decode("utf-8")).encode(output_encoding)


def _tag(short_name, local):
    """Get XML Clark notation {uri(``short_name``)}``local``."""
    return "{%s}%s" % (NAMESPACES[short_name], local)


def _tag_from_clark(name):
    """Get a human-readable variant of the XML Clark notation tag ``name``.

    For a given name using the XML Clark notation, return a human-readable
    variant of the tag name for known namespaces. Otherwise, return the name as
    is.

    """
    match = CLARK_TAG_REGEX.match(name)
    if match and match.group("namespace") in NAMESPACES_REV:
        args = {
            "ns": NAMESPACES_REV[match.group("namespace")],
            "tag": match.group("tag")}
        return "%(ns)s:%(tag)s" % args
    return name


def _response(code):
    """Return full W3C names from HTTP status codes."""
    return "HTTP/1.1 %i %s" % (code, client.responses[code])


def _href(href):
    """Return prefixed href."""
    return "%s%s" % (config.get("server", "base_prefix"), href.lstrip("/"))


def name_from_path(path, collection):
    """Return Radicale item name from ``path``."""
    collection_parts = collection.path.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if (len(path_parts) - len(collection_parts)):
        return path_parts[-1]


def props_from_request(root, actions=("set", "remove")):
    """Return a list of properties as a dictionary."""
    result = OrderedDict()
    if not hasattr(root, "tag"):
        root = ET.fromstring(root.encode("utf8"))

    for action in actions:
        action_element = root.find(_tag("D", action))
        if action_element is not None:
            break
    else:
        action_element = root

    prop_element = action_element.find(_tag("D", "prop"))
    if prop_element is not None:
        for prop in prop_element:
            if prop.tag == _tag("D", "resourcetype"):
                for resource_type in prop:
                    if resource_type.tag == _tag("C", "calendar"):
                        result["tag"] = "VCALENDAR"
                        break
                    elif resource_type.tag == _tag("CR", "addressbook"):
                        result["tag"] = "VADDRESSBOOK"
                        break
            elif prop.tag == _tag("C", "supported-calendar-component-set"):
                result[_tag_from_clark(prop.tag)] = ",".join(
                    supported_comp.attrib["name"]
                    for supported_comp in prop
                    if supported_comp.tag == _tag("C", "comp"))
            else:
                result[_tag_from_clark(prop.tag)] = prop.text

    return result


def delete(path, collection):
    """Read and answer DELETE requests.

    Read rfc4918-9.6 for info.

    """
    # Reading request
    if collection.path == path.strip("/"):
        # Delete the whole collection
        collection.delete()
    else:
        # Remove an item from the collection
        collection.remove(name_from_path(path, collection))

    # Writing answer
    multistatus = ET.Element(_tag("D", "multistatus"))
    response = ET.Element(_tag("D", "response"))
    multistatus.append(response)

    href = ET.Element(_tag("D", "href"))
    href.text = _href(path)
    response.append(href)

    status = ET.Element(_tag("D", "status"))
    status.text = _response(200)
    response.append(status)

    return _pretty_xml(multistatus)


def propfind(path, xml_request, collections, user=None):
    """Read and answer PROPFIND requests.

    Read rfc4918-9.1 for info.

    The collections parameter is a list of collections that are
    to be included in the output. Rights checking has to be done
    by the caller.

    """
    # Reading request
    if xml_request:
        root = ET.fromstring(xml_request.encode("utf8"))
        props = [prop.tag for prop in root.find(_tag("D", "prop"))]
    else:
        props = [_tag("D", "getcontenttype"),
                 _tag("D", "resourcetype"),
                 _tag("D", "displayname"),
                 _tag("D", "owner"),
                 _tag("D", "getetag"),
                 _tag("D", "current-user-principal"),
                 _tag("A", "calendar-color"),
                 _tag("CS", "getctag")]

    # Writing answer
    multistatus = ET.Element(_tag("D", "multistatus"))

    if collections:
        for collection in collections:
            response = _propfind_response(path, collection, props, user)
            multistatus.append(response)
    else:
        response = _propfind_response(path, None, props, user)
        multistatus.append(response)

    return _pretty_xml(multistatus)


def _propfind_response(path, item, props, user):
    """Build and return a PROPFIND response."""
    is_collection = isinstance(item, ical.Collection)
    if is_collection:
        with item.props as properties:
            collection_props = properties

    response = ET.Element(_tag("D", "response"))

    href = ET.Element(_tag("D", "href"))
    if item:
        uri = item.url if is_collection else "%s/%s" % (path, item.name)
        href.text = _href(uri.replace("//", "/"))
    else:
        href.text = _href(path)
    response.append(href)

    propstat404 = ET.Element(_tag("D", "propstat"))
    propstat200 = ET.Element(_tag("D", "propstat"))
    response.append(propstat200)

    prop200 = ET.Element(_tag("D", "prop"))
    propstat200.append(prop200)

    prop404 = ET.Element(_tag("D", "prop"))
    propstat404.append(prop404)

    for tag in props:
        element = ET.Element(tag)
        is404 = False
        if tag in (_tag("D", "principal-URL"),
                   _tag("D", "current-user-principal")):
            if user:
                tag = ET.Element(_tag("D", "href"))
                tag.text = _href("%s/" % user)
            else:
                is404 = True
                tag = ET.Element(_tag("D", "unauthenticated"))
            element.append(tag)
        elif tag == _tag("D", "principal-collection-set"):
            tag = ET.Element(_tag("D", "href"))
            tag.text = _href("/")
            element.append(tag)
        elif tag in (_tag("C", "calendar-home-set"),
                     _tag("CR", "addressbook-home-set")):
            if user and path == "/%s/" % user:
                tag = ET.Element(_tag("D", "href"))
                tag.text = _href(path)
                element.append(tag)
            else:
                is404 = True
        elif tag == _tag("C", "calendar-user-address-set"):
            tag = ET.Element(_tag("D", "href"))
            tag.text = _href(path)
            element.append(tag)
        elif tag == _tag("C", "supported-calendar-component-set"):
            # This is not a Todo
            # pylint: disable=W0511
            human_tag = _tag_from_clark(tag)
            if is_collection and human_tag in collection_props:
                # TODO: what do we have to do if it's not a collection?
                components = collection_props[human_tag].split(",")
            else:
                components = ("VTODO", "VEVENT", "VJOURNAL")
            for component in components:
                comp = ET.Element(_tag("C", "comp"))
                comp.set("name", component)
                element.append(comp)
            # pylint: enable=W0511
        elif tag == _tag("D", "current-user-privilege-set"):
            privilege = ET.Element(_tag("D", "privilege"))
            privilege.append(ET.Element(_tag("D", "all")))
            privilege.append(ET.Element(_tag("D", "read")))
            privilege.append(ET.Element(_tag("D", "write")))
            privilege.append(ET.Element(_tag("D", "write-properties")))
            privilege.append(ET.Element(_tag("D", "write-content")))
            element.append(privilege)
        elif tag == _tag("D", "supported-report-set"):
            for report_name in (
                    "principal-property-search", "sync-collection",
                    "expand-property", "principal-search-property-set"):
                supported = ET.Element(_tag("D", "supported-report"))
                report_tag = ET.Element(_tag("D", "report"))
                report_tag.text = report_name
                supported.append(report_tag)
                element.append(supported)
        # item related properties
        elif item:
            if tag == _tag("D", "getetag"):
                element.text = item.etag
            elif is_collection:
                if tag == _tag("D", "getcontenttype"):
                    element.text = item.mimetype
                elif tag == _tag("D", "resourcetype"):
                    if item.is_principal:
                        tag = ET.Element(_tag("D", "principal"))
                        element.append(tag)
                    if item.is_leaf(item.path) or (
                            not item.exists and item.resource_type):
                        # 2nd case happens when the collection is not stored yet,
                        # but the resource type is guessed
                        if item.resource_type == "addressbook":
                            tag = ET.Element(_tag("CR", item.resource_type))
                        else:
                            tag = ET.Element(_tag("C", item.resource_type))
                        element.append(tag)
                    tag = ET.Element(_tag("D", "collection"))
                    element.append(tag)
                elif tag == _tag("D", "owner") and item.owner_url:
                    element.text = item.owner_url
                elif tag == _tag("CS", "getctag"):
                    element.text = item.etag
                elif tag == _tag("C", "calendar-timezone"):
                    element.text = ical.serialize(
                        item.tag, item.headers, item.timezones)
                elif tag == _tag("D", "displayname"):
                    element.text = item.name
                elif tag == _tag("A", "calendar-color"):
                    element.text = item.color
                else:
                    human_tag = _tag_from_clark(tag)
                    if human_tag in collection_props:
                        element.text = collection_props[human_tag]
                    else:
                        is404 = True
            # Not for collections
            elif tag == _tag("D", "getcontenttype"):
                element.text = "%s; component=%s" % (
                    item.mimetype, item.tag.lower())
            elif tag == _tag("D", "resourcetype"):
                # resourcetype must be returned empty for non-collection elements
                pass
            else:
                is404 = True
        # Not for items
        elif tag == _tag("D", "resourcetype"):
            # resourcetype must be returned empty for non-collection elements
            pass
        else:
            is404 = True

        if is404:
            prop404.append(element)
        else:
            prop200.append(element)

    status200 = ET.Element(_tag("D", "status"))
    status200.text = _response(200)
    propstat200.append(status200)

    status404 = ET.Element(_tag("D", "status"))
    status404.text = _response(404)
    propstat404.append(status404)
    if len(prop404):
        response.append(propstat404)

    return response


def _add_propstat_to(element, tag, status_number):
    """Add a PROPSTAT response structure to an element.

    The PROPSTAT answer structure is defined in rfc4918-9.1. It is added to the
    given ``element``, for the following ``tag`` with the given
    ``status_number``.

    """
    propstat = ET.Element(_tag("D", "propstat"))
    element.append(propstat)

    prop = ET.Element(_tag("D", "prop"))
    propstat.append(prop)

    if "{" in tag:
        clark_tag = tag
    else:
        clark_tag = _tag(*tag.split(":", 1))
    prop_tag = ET.Element(clark_tag)
    prop.append(prop_tag)

    status = ET.Element(_tag("D", "status"))
    status.text = _response(status_number)
    propstat.append(status)


def proppatch(path, xml_request, collection):
    """Read and answer PROPPATCH requests.

    Read rfc4918-9.2 for info.

    """
    # Reading request
    root = ET.fromstring(xml_request.encode("utf8"))
    props_to_set = props_from_request(root, actions=("set",))
    props_to_remove = props_from_request(root, actions=("remove",))

    # Writing answer
    multistatus = ET.Element(_tag("D", "multistatus"))

    response = ET.Element(_tag("D", "response"))
    multistatus.append(response)

    href = ET.Element(_tag("D", "href"))
    href.text = _href(path)
    response.append(href)

    with collection.props as collection_props:
        for short_name, value in props_to_set.items():
            if short_name.split(":")[-1] == "calendar-timezone":
                collection.replace(None, value)
            collection_props[short_name] = value
            _add_propstat_to(response, short_name, 200)
        for short_name in props_to_remove:
            try:
                del collection_props[short_name]
            except KeyError:
                _add_propstat_to(response, short_name, 412)
            else:
                _add_propstat_to(response, short_name, 200)

    return _pretty_xml(multistatus)


def put(path, ical_request, collection):
    """Read PUT requests."""
    name = name_from_path(path, collection)
    if name in (item.name for item in collection.items):
        # PUT is modifying an existing item
        collection.replace(name, ical_request)
    else:
        # PUT is adding a new item
        collection.append(name, ical_request)


def report(path, xml_request, collection):
    """Read and answer REPORT requests.

    Read rfc3253-3.6 for info.

    """
    # Reading request
    root = ET.fromstring(xml_request.encode("utf8"))

    prop_element = root.find(_tag("D", "prop"))
    props = [prop.tag for prop in prop_element]

    if collection:
        if root.tag in (_tag("C", "calendar-multiget"),
                        _tag("CR", "addressbook-multiget")):
            # Read rfc4791-7.9 for info
            base_prefix = config.get("server", "base_prefix")
            hreferences = set(
                unquote(href_element.text)[len(base_prefix):] for href_element
                in root.findall(_tag("D", "href"))
                if unquote(href_element.text).startswith(base_prefix))
        else:
            hreferences = (path,)
        # TODO: handle other filters
        # TODO: handle the nested comp-filters correctly
        # Read rfc4791-9.7.1 for info
        tag_filters = set(
            element.get("name") for element
            in root.findall(".//%s" % _tag("C", "comp-filter")))
    else:
        hreferences = ()
        tag_filters = None

    # Writing answer
    multistatus = ET.Element(_tag("D", "multistatus"))

    collection_tag = collection.tag
    collection_items = collection.items
    collection_headers = collection.headers
    collection_timezones = collection.timezones

    for hreference in hreferences:
        # Check if the reference is an item or a collection
        name = name_from_path(hreference, collection)
        if name:
            # Reference is an item
            path = "/".join(hreference.split("/")[:-1]) + "/"
            items = (item for item in collection_items if item.name == name)
        else:
            # Reference is a collection
            path = hreference
            items = collection.components

        for item in items:
            if tag_filters and item.tag not in tag_filters:
                continue

            response = ET.Element(_tag("D", "response"))
            multistatus.append(response)

            href = ET.Element(_tag("D", "href"))
            href.text = _href("%s/%s" % (path.rstrip("/"), item.name))
            response.append(href)

            propstat = ET.Element(_tag("D", "propstat"))
            response.append(propstat)

            prop = ET.Element(_tag("D", "prop"))
            propstat.append(prop)

            for tag in props:
                element = ET.Element(tag)
                if tag == _tag("D", "getetag"):
                    element.text = item.etag
                elif tag == _tag("D", "getcontenttype"):
                    element.text = "%s; component=%s" % (
                        item.mimetype, item.tag.lower())
                elif tag in (_tag("C", "calendar-data"),
                             _tag("CR", "address-data")):
                    if isinstance(item, ical.Component):
                        element.text = ical.serialize(
                            collection_tag, collection_headers,
                            collection_timezones + [item])
                prop.append(element)

            status = ET.Element(_tag("D", "status"))
            status.text = _response(200)
            propstat.append(status)

    return _pretty_xml(multistatus)

########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2011-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale executable module.

This module can be executed from a command line with ``$python -m radicale`` or
from a python programme with ``radicale.__main__.run()``.

"""

import atexit
import os
import sys
import optparse
import signal
import threading
from wsgiref.simple_server import make_server

from . import (
    Application, config, HTTPServer, HTTPSServer, log, RequestHandler, VERSION)


# This is a script, many branches and variables
# pylint: disable=R0912,R0914

def run():
    """Run Radicale as a standalone server."""
    # Get command-line options
    parser = optparse.OptionParser(version=VERSION)
    parser.add_option(
        "-d", "--daemon", action="store_true",
        help="launch as daemon")
    parser.add_option(
        "-p", "--pid",
        help="set PID filename for daemon mode")
    parser.add_option(
        "-f", "--foreground", action="store_false", dest="daemon",
        help="launch in foreground (opposite of --daemon)")
    parser.add_option(
        "-H", "--hosts",
        help="set server hostnames and ports")
    parser.add_option(
        "-s", "--ssl", action="store_true",
        help="use SSL connection")
    parser.add_option(
        "-S", "--no-ssl", action="store_false", dest="ssl",
        help="do not use SSL connection (opposite of --ssl)")
    parser.add_option(
        "-k", "--key",
        help="set private key file")
    parser.add_option(
        "-c", "--certificate",
        help="set certificate file")
    parser.add_option(
        "-D", "--debug", action="store_true",
        help="print debug information")
    parser.add_option(
        "-C", "--config",
        help="use a specific configuration file")

    options = parser.parse_args()[0]

    # Read in the configuration specified by the command line (if specified)
    configuration_found = (
        config.read(options.config) if options.config else True)

    # Update Radicale configuration according to options
    for option in parser.option_list:
        key = option.dest
        if key:
            section = "logging" if key == "debug" else "server"
            value = getattr(options, key)
            if value is not None:
                config.set(section, key, str(value))

    # Start logging
    log.start()

    # Log a warning if the configuration file of the command line is not found
    if not configuration_found:
        log.LOGGER.warning(
            "Configuration file '%s' not found" % options.config)

    # Fork if Radicale is launched as daemon
    if config.getboolean("server", "daemon"):
        if os.path.exists(config.get("server", "pid")):
            raise OSError("PID file exists: %s" % config.get("server", "pid"))
        pid = os.fork()
        if pid:
            try:
                if config.get("server", "pid"):
                    open(config.get("server", "pid"), "w").write(str(pid))
            finally:
                sys.exit()
        sys.stdout = sys.stderr = open(os.devnull, "w")

    # Register exit function
    def cleanup():
        """Remove the PID files."""
        log.LOGGER.debug("Cleaning up")
        # Remove PID file
        if (config.get("server", "pid") and
                config.getboolean("server", "daemon")):
            os.unlink(config.get("server", "pid"))

    atexit.register(cleanup)
    log.LOGGER.info("Starting Radicale")

    # Create collection servers
    servers = []
    server_class = (
        HTTPSServer if config.getboolean("server", "ssl") else HTTPServer)
    shutdown_program = threading.Event()

    for host in config.get("server", "hosts").split(","):
        address, port = host.strip().rsplit(":", 1)
        address, port = address.strip("[] "), int(port)
        servers.append(
            make_server(address, port, Application(),
                        server_class, RequestHandler))

    # SIGTERM and SIGINT (aka KeyboardInterrupt) should just mark this for
    # shutdown
    signal.signal(signal.SIGTERM, lambda *_: shutdown_program.set())
    signal.signal(signal.SIGINT, lambda *_: shutdown_program.set())

    def serve_forever(server):
        """Serve a server forever, cleanly shutdown when things go wrong."""
        try:
            server.serve_forever()
        finally:
            shutdown_program.set()

    log.LOGGER.debug(
        "Base URL prefix: %s" % config.get("server", "base_prefix"))

    # Start the servers in a different loop to avoid possible race-conditions,
    # when a server exists but another server is added to the list at the same
    # time
    for server in servers:
        log.LOGGER.debug(
            "Listening to %s port %s" % (
                server.server_name, server.server_port))
        if config.getboolean("server", "ssl"):
            log.LOGGER.debug("Using SSL")
        threading.Thread(target=serve_forever, args=(server,)).start()

    log.LOGGER.debug("Radicale server ready")

    # Main loop: wait until all servers are exited
    try:
        # We must do the busy-waiting here, as all ``.join()`` calls completly
        # block the thread, such that signals are not received
        while True:
            # The number is irrelevant, it only needs to be greater than 0.05
            # due to python implementing its own busy-waiting logic
            shutdown_program.wait(5.0)
            if shutdown_program.is_set():
                break
    finally:
        # Ignore signals, so that they cannot interfere
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        log.LOGGER.info("Stopping Radicale")

        for server in servers:
            log.LOGGER.debug(
                "Closing server listening to %s port %s" % (
                    server.server_name, server.server_port))
            server.shutdown()

# pylint: enable=R0912,R0914


if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = radicale
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale CalDAV Server.

Launch the server according to configuration and command-line options.

"""

import radicale.__main__


radicale.__main__.run()

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Custom authentication.

Just check username for testing

"""


def is_authenticated(user, password):
    return user == 'tmp'

########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Custom storage backend.

Copy of filesystem storage backend for testing

"""

from radicale.storage import filesystem


class Collection(filesystem.Collection):
    """Collection stored in a flat ical file."""

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
# Copyright © 2008-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale Helpers module.

This module offers helpers to use in tests.

"""

import os

EXAMPLES_FOLDER = os.path.join(os.path.dirname(__file__), "static")


def get_file_content(file_name):
    try:
        with open(os.path.join(EXAMPLES_FOLDER, file_name)) as fd:
            return fd.read()
    except IOError:
        print("Couldn't open the file %s" % file_name)

########NEW FILE########
__FILENAME__ = test_auth
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012-2013 Guillaume Ayoub
# Copyright © 2012-2013 Jean-Marc Martins
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale tests with simple requests and authentication.

"""

import base64
import hashlib
import os
import radicale
import tempfile
from radicale import config
from radicale.auth import htpasswd
from tests import BaseTest


class TestBaseAuthRequests(BaseTest):
    """
    Tests basic requests with auth.

    We should setup auth for each type before create Application object
    """

    def setup(self):
        self.userpass = "dG1wOmJlcG8="

    def teardown(self):
        config.set("auth", "type", "None")
        radicale.auth.is_authenticated = lambda *_: True

    def test_root(self):
        self.colpath = tempfile.mkdtemp()
        htpasswd_file_path = os.path.join(self.colpath, ".htpasswd")
        with open(htpasswd_file_path, "wb") as fd:
            fd.write(b"tmp:{SHA}" + base64.b64encode(
                hashlib.sha1(b"bepo").digest()))
        config.set("auth", "type", "htpasswd")

        htpasswd.FILENAME = htpasswd_file_path
        htpasswd.ENCRYPTION = "sha1"

        self.application = radicale.Application()

        status, headers, answer = self.request(
            "GET", "/", HTTP_AUTHORIZATION=self.userpass)
        assert status == 200
        assert "Radicale works!" in answer

    def test_custom(self):
        config.set("auth", "type", "custom")
        config.set("auth", "custom_handler", "tests.custom.auth")
        self.application = radicale.Application()
        status, headers, answer = self.request(
            "GET", "/", HTTP_AUTHORIZATION=self.userpass)
        assert status == 200
        assert "Radicale works!" in answer

########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-
#
# This file is part of Radicale Server - Calendar Server
# Copyright © 2012-2013 Guillaume Ayoub
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radicale.  If not, see <http://www.gnu.org/licenses/>.

"""
Radicale tests with simple requests.

"""

from .helpers import get_file_content
import radicale
import shutil
import tempfile
from dulwich.repo import Repo
from radicale import config
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from tests import BaseTest


class BaseRequests(object):
    """Tests with simple requests."""

    def test_root(self):
        """Test a GET request at "/"."""
        status, headers, answer = self.request("GET", "/")
        assert status == 200
        assert "Radicale works!" in answer
        # Test the creation of the collection
        status, headers, answer = self.request("GET", "/calendar.ics/")
        assert "BEGIN:VCALENDAR" in answer
        assert "VERSION:2.0" in answer
        assert "END:VCALENDAR" in answer
        assert "PRODID:-//Radicale//NONSGML Radicale Server//EN" in answer

    def test_add_event_todo(self):
        """Tests the add of an event and todo."""
        self.request("GET", "/calendar.ics/")
        #VEVENT test
        event = get_file_content("put.ics")
        path = "/calendar.ics/02805f81-4cc2-4d68-8d39-72768ffa02d9.ics"
        status, headers, answer = self.request("PUT", path, event)
        assert status == 201
        assert "ETag" in headers.keys()
        status, headers, answer = self.request("GET", path)
        assert status == 200
        assert "VEVENT" in answer
        assert b"Nouvel \xc3\xa9v\xc3\xa8nement".decode("utf-8") in answer
        assert "UID:02805f81-4cc2-4d68-8d39-72768ffa02d9" in answer
        # VTODO test
        todo = get_file_content("putvtodo.ics")
        path = "/calendar.ics/40f8cf9b-0e62-4624-89a2-24c5e68850f5.ics"
        status, headers, answer = self.request("PUT", path, todo)
        assert status == 201
        assert "ETag" in headers.keys()
        status, headers, answer = self.request("GET", path)
        assert "VTODO" in answer
        assert b"Nouvelle t\xc3\xa2che".decode("utf-8") in answer
        assert "UID:40f8cf9b-0e62-4624-89a2-24c5e68850f5" in answer

    def test_delete(self):
        """Tests the deletion of an event"""
        self.request("GET", "/calendar.ics/")
        # Adds a VEVENT to be deleted
        event = get_file_content("put.ics")
        path = "/calendar.ics/02805f81-4cc2-4d68-8d39-72768ffa02d9.ics"
        status, headers, answer = self.request("PUT", path, event)
        # Then we send a DELETE request
        status, headers, answer = self.request("DELETE", path)
        assert status == 200
        assert "href>%s</" % path in answer
        status, headers, answer = self.request("GET", "/calendar.ics/")
        assert "VEVENT" not in answer


class TestFileSystem(BaseRequests, BaseTest):
    """Base class for filesystem tests."""
    storage_type = "filesystem"

    def setup(self):
        """Setup function for each test."""
        self.colpath = tempfile.mkdtemp()
        config.set("storage", "type", self.storage_type)
        from radicale.storage import filesystem
        filesystem.FOLDER = self.colpath
        filesystem.GIT_REPOSITORY = None
        self.application = radicale.Application()

    def teardown(self):
        """Teardown function for each test."""
        shutil.rmtree(self.colpath)


class TestMultiFileSystem(TestFileSystem):
    """Base class for multifilesystem tests."""
    storage_type = "multifilesystem"


class TestDataBaseSystem(BaseRequests, BaseTest):
    """Base class for database tests"""
    def setup(self):
        config.set("storage", "type", "database")
        config.set("storage", "database_url", "sqlite://")
        from radicale.storage import database
        database.Session = sessionmaker()
        database.Session.configure(bind=create_engine("sqlite://"))
        session = database.Session()
        for st in get_file_content("schema.sql").split(";"):
            session.execute(st)
        session.commit()
        self.application = radicale.Application()


class TestGitFileSystem(TestFileSystem):
    """Base class for filesystem tests using Git"""
    def setup(self):
        super(TestGitFileSystem, self).setup()
        Repo.init(self.colpath)
        from radicale.storage import filesystem
        filesystem.GIT_REPOSITORY = Repo(self.colpath)


class TestGitMultiFileSystem(TestGitFileSystem, TestMultiFileSystem):
    """Base class for multifilesystem tests using Git"""


class TestCustomStorageSystem(BaseRequests, BaseTest):
    """Base class for custom backend tests."""
    storage_type = "custom"

    def setup(self):
        """Setup function for each test."""
        self.colpath = tempfile.mkdtemp()
        config.set("storage", "type", self.storage_type)
        config.set("storage", "custom_handler", "tests.custom.storage")
        from tests.custom import storage
        storage.FOLDER = self.colpath
        storage.GIT_REPOSITORY = None
        self.application = radicale.Application()

    def teardown(self):
        """Teardown function for each test."""
        shutil.rmtree(self.colpath)
########NEW FILE########
