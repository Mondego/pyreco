__FILENAME__ = attack_session
# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging
import uuid

from datetime import datetime

logger = logging.getLogger(__name__)


# one instance per connection
class AttackSession(object):
    def __init__(self, protocol, source_ip, source_port, databus, log_queue):
        self.log_queue = log_queue
        self.id = uuid.uuid4()
        logger.info('New {0} session from {1} ({2})'.format(protocol, source_ip, self.id))
        self.protocol = protocol
        self.source_ip = source_ip
        self.source_port = source_port
        self.timestamp = datetime.utcnow()
        self.databus = databus
        self.public_ip = None
        self.data = dict()

    def _dump_event(self, event_data):
        data = {
            "id": self.id,
            "remote": (self.source_ip, self.source_port),
            "data_type": self.protocol,
            "timestamp": self.timestamp,
            "public_ip": self.public_ip,
            "data": event_data
        }
        return data

    def add_event(self, event_data):
        sec_elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        elapse_ms = int(sec_elapsed * 1000)
        while elapse_ms in self.data:
            elapse_ms += 1
        self.data[elapse_ms] = event_data
        # We should only log the session when we finish it
        self.log_queue.put(self._dump_event(event_data))

    def dump(self):
        data = {
            "id": self.id,
            "remote": (self.source_ip, self.source_port),
            "data_type": self.protocol,
            "timestamp": self.timestamp,
            "public_ip": self.public_ip,
            "data": self.data
        }
        return data

########NEW FILE########
__FILENAME__ = databus
# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging
import json
import inspect
# this is needed because we use it in the xml.
import random

import gevent
from lxml import etree


logger = logging.getLogger(__name__)


class Databus(object):
    def __init__(self):
        self._data = {}
        self._observer_map = {}

    # the idea here is that we can store both values and functions in the key value store
    # functions could be used if a profile wants to simulate a sensor, or the function
    # could interface with a real sensor
    def get_value(self, key):
        logger.debug('DataBus: Get value from key: [{0}]'.format(key))
        assert key in self._data
        item = self._data[key]
        if getattr(item, "get_value", None):
            # this could potentially generate a context switch, but as long the called method
            # does not "callback" the databus we should be fine
            return item.get_value()
        else:
            # guaranteed to not generate context switch
            return item

    def set_value(self, key, value):
        logger.debug('DataBus: Storing key: [{0}] value: [{1}]'.format(key, value))
        self._data[key] = value
        # notify observers
        if key in self._observer_map:
            gevent.spawn(self.notify_observers, key)

    def notify_observers(self, key):
        for cb in self._observer_map:
            cb(key)

    def observe_value(self, key, callback):
        assert hasattr(callback, '__call__')
        assert len(inspect.getargspec(callback)[0])
        if key not in self._observer_map:
            self._observer_map = []
        self._observer_map[key].append(callback)

    def initialize(self, config_file):
        self._reset()
        logger.debug('Initializing databus using {0}.'.format(config_file))
        dom = etree.parse(config_file)
        entries = dom.xpath('//conpot_template/core/databus/key_value_mappings/*')
        for entry in entries:
            key = entry.attrib['name']
            value = entry.xpath('./value/text()')[0]
            value_type = str(entry.xpath('./value/@type')[0])
            assert key not in self._data
            logging.debug('Initializing {0} with {1} as a {2}.'.format(key, value, value_type))
            if value_type == 'value':
                self.set_value(key, eval(value))
            elif value_type == 'function':
                namespace, _classname = value.rsplit('.', 1)
                params = entry.xpath('./value/@param')
                module = __import__(namespace, fromlist=[_classname])
                _class = getattr(module, _classname)
                if len(params) > 0:
                    self.set_value(key, _class(*(tuple(params))))
                else:
                    self.set_value(key, _class())
            else:
                raise Exception('Unknown value type: {0}'.format(value_type))

    def get_shapshot(self):
        # takes a snapshot of the internal honeypot state and returns it as json.
        snapsnot = {}
        for key in self._data.keys():
            snapsnot[key] = self.get_value(key)
        return json.dumps(snapsnot)

    def _reset(self):
        logger.debug('Resetting databus.')
        self._data.clear()
        self._observer_map.clear()

########NEW FILE########
__FILENAME__ = hpfriends
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import hpfeeds
import gevent


class HPFriendsLogger(object):

    def __init__(self, host, port, ident, secret, channels):
        self.channels = channels
        try:
            with gevent.Timeout(2):
                self.hpc = hpfeeds.new(host, port, ident, secret)
        except:
            raise Exception("Connection to HPFriends timed out")

    def log(self, data):
        # hpfeed lib supports passing list of channels
        self.hpc.publish(self.channels, data)
        error_msg = self.hpc.wait()
        return error_msg


########NEW FILE########
__FILENAME__ = log_worker
#!/usr/bin/env python
# Copyright (C) 2014 Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json
import logging
import uuid
import time

from datetime import datetime

import ConfigParser
from gevent.queue import Empty

from conpot.core.loggers.sqlite_log import SQLiteLogger
from conpot.core.loggers.hpfriends import HPFriendsLogger
from conpot.core.loggers.syslog import SysLogger
from conpot.core.loggers.taxii_log import TaxiiLogger

logger = logging.getLogger(__name__)


class LogWorker(object):
    def __init__(self, config, dom, session_manager, public_ip):
        self.config = config
        self.log_queue = session_manager.log_queue
        self.session_manager = session_manager
        self.sqlite_logger = None
        self.friends_feeder = None
        self.syslog_client = None
        self.public_ip = public_ip
        self.taxii_logger = None

        if config.getboolean('sqlite', 'enabled'):
            self.sqlite_logger = SQLiteLogger()

        if config.getboolean('hpfriends', 'enabled'):
            host = config.get('hpfriends', 'host')
            port = config.getint('hpfriends', 'port')
            ident = config.get('hpfriends', 'ident')
            secret = config.get('hpfriends', 'secret')
            channels = eval(config.get('hpfriends', 'channels'))
            try:
                self.friends_feeder = HPFriendsLogger(host, port, ident, secret, channels)
            except Exception as e:
                logger.exception(e.message)
                self.friends_feeder = None

        if config.getboolean('syslog', 'enabled'):
            host = config.get('syslog', 'host')
            port = config.getint('syslog', 'port')
            facility = config.get('syslog', 'facility')
            logdevice = config.get('syslog', 'device')
            logsocket = config.get('syslog', 'socket')
            self.syslog_client = SysLogger(host, port, facility, logdevice, logsocket)

        if config.getboolean('taxii', 'enabled'):
            # TODO: support for certificates
            self.taxii_logger = TaxiiLogger(config, dom)

        self.enabled = True

    def _json_default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return None

    def _process_sessions(self):
        sessions = self.session_manager._sessions
        try:
            session_timeout = self.config.get("session", "timeout")
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            session_timeout = 5
        for session in sessions:
            if len(session.data) > 0:
                sec_last_event = max(session.data) / 1000
            else:
                sec_last_event = 0
            sec_session_start = time.mktime(session.timestamp.timetuple())
            sec_now = time.mktime(datetime.utcnow().timetuple())
            if (sec_now - (sec_session_start + sec_last_event)) >= session_timeout:
                logger.info("Session timed out: {0}".format(session.id))
                sessions.remove(session)

    def start(self):
        self.enabled = True
        while self.enabled:
            try:
                event = self.log_queue.get(timeout=2)
            except Empty:
                self._process_sessions()
            else:
                if self.public_ip:
                    event["public_ip"] = self.public_ip

                if self.friends_feeder:
                    self.friends_feeder.log(json.dumps(event, default=self._json_default))

                if self.sqlite_logger:
                    self.sqlite_logger.log(event)

                if self.syslog_client:
                    self.syslog_client.log(event)

                if self.taxii_logger:
                    self.taxii_logger.log(event)

    def stop(self):
        self.enabled = False

########NEW FILE########
__FILENAME__ = sqlite_log
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import sqlite3
import pwd
import os
import platform
import grp


class SQLiteLogger(object):

    def _chown_db(self, path, uid_name='nobody', gid_name='nogroup'):
        path = path.rpartition("/")[0]
        if not os.path.isdir(path):
            os.mkdir(path)
        # TODO: Have this in a central place
        wanted_uid = pwd.getpwnam(uid_name)[2]
        # special handling for os x. (getgrname has trouble with gid below 0)
        if platform.mac_ver()[0]:
            wanted_gid = -2
        else:
            wanted_gid = grp.getgrnam(gid_name)[2]
        os.chown(path, wanted_uid, wanted_gid)

    def __init__(self, db_path="logs/conpot.db"):
        self._chown_db(db_path)
        self.conn = sqlite3.connect(db_path)
        self._create_db()

    def _create_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS events
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                remote TEXT,
                protocol TEXT,
                request TEXT,
                response TEXT
            )""")

    def log(self, event):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO events(session, remote, protocol, request, response) VALUES (?, ?, ?, ?, ?)",
                       (str(event["id"]), str(event["remote"]), event['data_type'],
                        event["data"].get('request'), event["data"].get('response'))
        )
        self.conn.commit()
        return cursor.lastrowid

    def log_session(self, session):
        pass

    def select_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events")
        print cursor.fetchall()

########NEW FILE########
__FILENAME__ = stix_transform
# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import uuid
import os
import json
import ast

from datetime import datetime

import jinja2

import conpot


class StixTransformer(object):
    def __init__(self, config, dom):
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
        template_env = jinja2.Environment(loader=template_loader)
        self.config = config._sections['taxii']
        modbus_port = ast.literal_eval(dom.xpath('//conpot_template/protocols/modbus/@port')[0])
        snmp_port = ast.literal_eval(dom.xpath('//conpot_template/protocols/snmp/@port')[0])
        http_port = ast.literal_eval(dom.xpath('//conpot_template/protocols/http/@port')[0])
        s7_port = ast.literal_eval(dom.xpath('//conpot_template/protocols/s7comm/@port')[0])
        self.protocol_to_port_mapping = {'modbus': modbus_port,
                                         'http': http_port,
                                         's7comm': s7_port,
                                         'snmp': snmp_port}
        self.template = template_env.get_template('stix_template.xml')

    def transform(self, event):
        data = {'package_id': str(uuid.uuid4()),
                'namespace': 'ConPot',
                'namespace_uri': 'http://conpot.org/stix-1',
                'package_timestamp': datetime.utcnow().isoformat(),
                'incident_id': event['session_id'],
                'incident_timestamp': event['timestamp'].isoformat(),
                'conpotlog_observable_id': str(uuid.uuid4()),
                'network_observable_id': str(uuid.uuid4()),
                'source_ip': event['remote'][0],
                'source_port': event['remote'][1],
                'l7_protocol': event['data_type'],
                'conpot_version': conpot.__version__,
                'session_log': json.dumps(event['data']),
                'include_contact_info': self.config['include_contact_info'],
                'contact_name': self.config['contact_name'],
                'contact_mail': self.config['contact_email']}

        if 'public_ip' in event:
            data['destination_ip'] = event['public_ip']

        if event['data_type'] in self.protocol_to_port_mapping:
            data['destination_port'] = self.protocol_to_port_mapping[event['data_type']]
        else:
            raise Exception('No port mapping could be found for {0}'.format(event['data_type']))

        return self.template.render(data)

########NEW FILE########
__FILENAME__ = syslog
# Copyright (C) 2013  Daniel creo Haslinger <creo-conpot@blackmesa.at>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from logging.handlers import SysLogHandler
import logging
import socket


class SysLogger(object):
    def __init__(self, host, port, facility, logdevice, logsocket):
        logger = logging.getLogger()

        if str(logsocket).lower() == 'udp':
            logger.addHandler(SysLogHandler(address=(host, port),
                                            facility=getattr(SysLogHandler, 'LOG_' + str(facility).upper()),
                                            socktype=socket.SOCK_DGRAM))
        elif str(logsocket).lower() == 'dev':
            logger.addHandler(SysLogHandler(logdevice))

    def log(self, data):
        # stub function since the additional handler has been added to the root loggers instance.
        pass

########NEW FILE########
__FILENAME__ = taxii_log
# Copyright (C) 2013  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging

import libtaxii
from libtaxii.messages_11 import ContentBlock, InboxMessage, generate_message_id
from libtaxii.clients import HttpClient

from conpot.core.loggers.stix_transform import StixTransformer

logger = logging.getLogger(__name__)


class TaxiiLogger(object):
    def __init__(self, config, dom):
        self.host = config.get('taxii', 'host')
        self.port = config.getint('taxii', 'port')
        self.inbox_path = config.get('taxii', 'inbox_path')
        self.use_https = config.getboolean('taxii', 'use_https')

        self.client = HttpClient()
        self.client.setProxy('noproxy')
        self.stix_transformer = StixTransformer(config, dom)

    def log(self, event):
        # converts from conpot log format to STIX compatible xml
        stix_package = self.stix_transformer.transform(event)

        # wrapping the stix message in a TAXII envelope
        content_block = ContentBlock(libtaxii.CB_STIX_XML_11, stix_package.encode('utf-8'))
        inbox_message = InboxMessage(message_id=generate_message_id(), content_blocks=[content_block])
        inbox_xml = inbox_message.to_xml()

        # the actual call to the TAXII web service
        response = self.client.callTaxiiService2(self.host, self.inbox_path, libtaxii.VID_TAXII_XML_11, inbox_xml, self.port)
        response_message = libtaxii.get_message_from_http_response(response, '0')

        if response_message.status_type != libtaxii.messages.ST_SUCCESS:
            logger.error('Error while transmitting message to TAXII server: {0}'.format(response_message.message))
            return False
        else:
            return True


########NEW FILE########
__FILENAME__ = session_manager
# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from gevent.queue import Queue

from conpot.core.attack_session import AttackSession
from conpot.core.databus import Databus


# one instance only
class SessionManager(object):
    def __init__(self):
        self._sessions = []
        self._databus = Databus()
        self.log_queue = Queue()

    def _find_sessions(self, protocol, source_ip):
        for session in self._sessions:
            if session.protocol == protocol:
                if session.source_ip == source_ip:
                    return session
        return None

    def get_session(self, protocol, source_ip, source_port):
        # around here we would inject dependencies into the attack session
        attack_session = self._find_sessions(protocol, source_ip)
        if not attack_session:
            attack_session = AttackSession(protocol, source_ip, source_port, self._databus, self.log_queue)
            self._sessions.append(attack_session)
        return attack_session

    def get_session_count(self, protocol):
        count = 0
        for session in self._sessions:
            if session.protocol == protocol:
                count += 1
        return count

    def get_session_count(self):
        return len(self._sessions)

    def purge_sessions(self):
        # there is no native purge/clear mechanism for gevent queues, so...
        self.log_queue = Queue()

    def initialize_databus(self, config_file):
        self._databus.initialize(config_file)

########NEW FILE########
__FILENAME__ = uptime
# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import time
import calendar


class Uptime(object):
    def __init__(self, started=-1):
        if started >= 0:
            initial = started
        else:
            initial = calendar.timegm(time.gmtime())
        self.started = calendar.timegm(time.gmtime(initial))

    def get_value(self):
        return calendar.timegm(time.gmtime()) - self.started

########NEW FILE########
__FILENAME__ = proxy
# Copyright (C) 2014  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging
import select
import socket as _socket

import gevent
from gevent.socket import socket
from gevent.ssl import wrap_socket
from gevent.server import StreamServer

import conpot.core as conpot_core


logger = logging.getLogger(__name__)


class Proxy(object):
    def __init__(self, name, proxy_host, proxy_port, decoder=None, keyfile=None, certfile=None):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.name = name
        self.proxy_id = self.name.lower().replace(' ', '_')
        self.host = None
        self.port = None
        self.keyfile = keyfile
        self.certfile = certfile
        if decoder:
            namespace, _classname = decoder.rsplit('.', 1)
            module = __import__(namespace, fromlist=[_classname])
            _class = getattr(module, _classname)
            self.decoder = _class()
        else:
            self.decoder = None

    def get_server(self, host, port):
        self.host = host
        connection = (host, port)
        if self.keyfile and self.certfile:
            server = StreamServer(connection, self.handle, keyfile=self.keyfile, certfile=self.certfile)
        else:
            server = StreamServer(connection, self.handle)
        self.port = server.server_port
        logger.info('{0} proxy server started, listening on {1}, proxy for: ({2}, {3}) using {4} decoder.'
                    .format(self.name, connection, self.proxy_host, self.proxy_port, self.decoder))
        return server

    def handle(self, sock, address):
        session = conpot_core.get_session(self.proxy_id, address[0], address[1])
        logger.info('New connection from {0}:{1} on {2} proxy. ({3})'.format(address[0], address[1],
                                                                             self.proxy_id, session.id))
        proxy_socket = socket()

        if self.keyfile and self.certfile:
            proxy_socket = wrap_socket(proxy_socket, self.keyfile, self.certfile)

        try:
            proxy_socket.connect((self.proxy_host, self.proxy_port))
        except _socket.error as ex:
            logger.error('Error while connecting to proxied service at ({0}, {1}): {2}'
                         .format(self.proxy_host, self.proxy_port, ex))
            self._close([proxy_socket, sock])
            return

        sockets = [proxy_socket, sock]
        while len(sockets) == 2:
            gevent.sleep()
            sockets_read, _, sockets_err = select.select(sockets, [], sockets, 10)

            if len(sockets_err) > 0:
                self._close([proxy_socket, sock])
                break

            for s in sockets_read:
                data = s.recv(1024)
                if len(data) is 0:
                    self._close([proxy_socket, sock])
                    if s is proxy_socket:
                        logging.info('Closing proxy connection because the proxied socket closed.')
                        sockets = []
                        break
                    elif s is sock:
                        logging.info('Closing proxy connection because the remote socket closed')
                        sockets = []
                        break
                    else:
                        assert False
                if s is proxy_socket:
                    self.handle_out_data(data, sock, session)
                elif s is sock:
                    self.handle_in_data(data, proxy_socket, session)
                else:
                    assert False

        proxy_socket.close()
        sock.close()

    def handle_in_data(self, data, sock, session):
        hex_data = data.encode('hex_codec')
        session.add_event({'raw_request': hex_data, 'raw_response': ''})
        logger.debug('Received {0} bytes from outside to proxied service: {1}'.format(len(data), hex_data))
        if self.decoder:
            decoded = self.decoder.decode_in(data)
            session.add_event({'request': decoded, 'raw_response': ''})
        sock.send(data)

    def handle_out_data(self, data, sock, session):
        hex_data = data.encode('hex_codec')
        session.add_event({'raw_request': '', 'raw_response': hex_data})
        logger.debug('Received {0} bytes from proxied service: {1}'.format(len(data), hex_data))
        if self.decoder:
            decoded = self.decoder.decode_out(data)
            session.add_event({'request': '', 'raw_response': decoded})
        sock.send(data)

    def _close(self, sockets):
        for s in sockets:
            s.close()

    def stop(self):
        # TODO: Keep active sockets in list and close them on stop()
        return

########NEW FILE########
__FILENAME__ = command_responder
# Copyright (C) 2013  Daniel creo Haslinger <creo-conpot@blackmesa.at>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging
import time
import random

from datetime import datetime

from HTMLParser import HTMLParser
from SocketServer import ThreadingMixIn
import gevent.monkey
gevent.monkey.patch_all()

import BaseHTTPServer
import httplib
import os
from lxml import etree

import conpot.core as conpot_core


logger = logging.getLogger()


class HTTPServer(BaseHTTPServer.BaseHTTPRequestHandler):

    def log(self, version, request_type, addr, request, response=None):

        session = conpot_core.get_session('http', addr[0], addr[1])

        log_dict = {'remote': addr,
                    'timestamp': datetime.utcnow(),
                    'data_type': 'http',
                    'data': {0: {'request': '{0} {1}: {2}'.format(version, request_type, request)}}}

        logger.info('{0} {1} request from {2}: {3}. {4}'.format(version, request_type, addr, request, session.id))

        if response:
            logger.info('{0} response to {1}: {2}. {3}'.format(version, addr, response, session.id))
            log_dict['data'][0]['response'] = '{0} response: {1}'.format(version, response)
            session.add_event({'request': str(request), 'response': str(response)})
        else:
            session.add_event({'request': str(request)})

        # FIXME: Proper logging

    def get_entity_headers(self, rqfilename, headers, configuration):

        xml_headers = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/headers/*'
        )

        if xml_headers:

            # retrieve all headers assigned to this entity
            for header in xml_headers:
                headers.append((header.attrib['name'], header.text))

        return headers

    def get_trigger_appendix(self, rqfilename, rqparams, configuration):

        xml_triggers = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/triggers/*'
        )

        if xml_triggers:
            paramlist = rqparams.split('&')

            # retrieve all subselect triggers assigned to this entity
            for triggers in xml_triggers:

                triggerlist = triggers.text.split(';')
                trigger_missed = False

                for trigger in triggerlist:
                    if not trigger in paramlist:
                        trigger_missed = True

                if not trigger_missed:
                    return triggers.attrib['appendix']

        return None

    def get_entity_trailers(self, rqfilename, configuration):

        trailers = []
        xml_trailers = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/trailers/*'
        )

        if xml_trailers:

            # retrieve all headers assigned to this entity
            for trailer in xml_trailers:
                trailers.append((trailer.attrib['name'], trailer.text))

        return trailers

    def get_status_headers(self, status, headers, configuration):

        xml_headers = configuration.xpath('//conpot_template/protocols/http/statuscodes/status[@name="' +
                                          str(status) + '"]/headers/*')

        if xml_headers:

            # retrieve all headers assigned to this status
            for header in xml_headers:
                headers.append((header.attrib['name'], header.text))

        return headers

    def get_status_trailers(self, status, configuration):

        trailers = []
        xml_trailers = configuration.xpath(
            '//conpot_template/protocols/http/statuscodes/status[@name="' + str(status) + '"]/trailers/*'
        )

        if xml_trailers:

            # retrieve all trailers assigned to this status
            for trailer in xml_trailers:
                trailers.append((trailer.attrib['name'], trailer.text))

        return trailers

    def send_response(self, code, message=None):
        """Send the response header and log the response code.
        This function is overloaded to change the behaviour when
        loggers and sending default headers.
        """

        # replace integrated loggers with conpot logger..
        # self.log_request(code)

        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''

        if self.request_version != 'HTTP/0.9':
            self.wfile.write("%s %d %s\r\n" %
                             (self.protocol_version, code, message))

        # the following two headers are omitted, which is why we override
        # send_response() at all. We do this one on our own...

        # - self.send_header('Server', self.version_string())
        # - self.send_header('Date', self.date_time_string())

    def substitute_template_fields(self, payload):

        # initialize parser with our payload
        parser = TemplateParser(payload)

        # triggers the parser, just in case of open / incomplete tags..
        parser.close()

        # retrieve and return (substituted) payload
        return parser.payload

    def load_status(self, status, requeststring, headers, configuration, docpath):
        """Retrieves headers and payload for a given status code.
           Certain status codes can be configured to forward the
           request to a remote system. If not available, generate
           a minimal response"""

        # handle PROXY tag
        entity_proxy = configuration.xpath('//conpot_template/protocols/http/statuscodes/status[@name="' +
                                           str(status) +
                                           '"]/proxy')

        if entity_proxy:
            source = 'proxy'
            target = entity_proxy[0].xpath('./text()')[0]
        else:
            source = 'filesystem'

        # handle TARPIT tag
        entity_tarpit = configuration.xpath(
            '//conpot_template/protocols/http/statuscodes/status[@name="' + str(status) + '"]/tarpit'
        )

        if entity_tarpit:
            tarpit = self.server.config_sanitize_tarpit(entity_tarpit[0].xpath('./text()')[0])
        else:
            tarpit = None

        # check if we have to delay further actions due to global or local TARPIT configuration
        if tarpit is not None:
            # this node has its own delay configuration
            self.server.do_tarpit(tarpit)
        else:
            # no delay configuration for this node. check for global latency
            if self.server.tarpit is not None:
                # fall back to the globally configured latency
                self.server.do_tarpit(self.server.tarpit)

        # If the requested resource resides on our filesystem,
        # we try retrieve all metadata and the resource itself from there.
        if source == 'filesystem':

            # retrieve headers from entities configuration block
            headers = self.get_status_headers(status, headers, configuration)

            # retrieve headers from entities configuration block
            trailers = self.get_status_trailers(status, configuration)

            # retrieve payload directly from filesystem, if possible.
            # If this is not possible, return an empty, zero sized string.
            try:
                with open(docpath + 'statuscodes/' + str(status) + '.status', 'rb') as f:
                    payload = f.read()

            except IOError, e:
                logger.error('{0}'.format(e))
                payload = ''

            # there might be template data that can be substituted within the
            # payload. We only substitute data that is going to be displayed
            # by the browser:

            # perform template substitution on payload
            payload = self.substitute_template_fields(payload)

            # How do we transport the content?
            chunked_transfer = configuration.xpath('//conpot_template/protocols/http/htdocs/node[@name="' +
                                                   str(status) + '"]/chunks')

            if chunked_transfer:
                # Append a chunked transfer encoding header
                headers.append(('Transfer-Encoding', 'chunked'))
                chunks = str(chunked_transfer[0].xpath('./text()')[0])
            else:
                # Calculate and append a content length header
                headers.append(('Content-Length', payload.__len__()))
                chunks = '0'

            return status, headers, trailers, payload, chunks

        # the requested status code is configured to forward the
        # originally targeted resource to a remote system.

        elif source == 'proxy':

            # open a connection to the remote system.
            # If something goes wrong, fall back to 503.

            # NOTE: we use try:except here because there is no perfect
            # platform independent way to check file accessibility.

            trailers = []

            try:

                conn = httplib.HTTPConnection(target)
                conn.request("GET", requeststring)
                response = conn.getresponse()

                status = int(response.status)
                headers = response.getheaders()   # We REPLACE the headers to avoid duplicates!
                payload = response.read()

                # WORKAROUND: to get around a strange httplib-behaviour when it comes
                # to chunked transfer encoding, we replace the chunked-header with a
                # valid Content-Length header:

                for i, header in enumerate(headers):

                    if header[0].lower() == 'transfer-encoding' and header[1].lower() == 'chunked':
                        del headers[i]
                        chunks = '0'
                        break

            except:

                # before falling back to 503, we check if we are ALREADY dealing with a 503
                # to prevent an infinite request handling loop...

                if status != 503:

                    # we're handling another error here.
                    # generate a 503 response from configuration.
                    (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                                    requeststring,
                                                                                    headers,
                                                                                    configuration,
                                                                                    docpath)

                else:

                    # oops, we're heading towards an infinite loop here,
                    # generate a minimal 503 response regardless of the configuration.
                    status = 503
                    payload = ''
                    chunks = '0'
                    headers.append(('Content-Length', 0))

            return status, headers, trailers, payload, chunks

    def load_entity(self, requeststring, headers, configuration, docpath):
        """
        Retrieves status, headers and payload for a given entity, that
        can be stored either local or on a remote system
        """

        # extract filename and GET parameters from request string
        rqfilename = requeststring.partition('?')[0]
        rqparams = requeststring.partition('?')[2]

        # handle ALIAS tag
        entity_alias = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/alias'
        )
        if entity_alias:
            rqfilename = entity_alias[0].xpath('./text()')[0]

        # handle SUBSELECT tag
        rqfilename_appendix = self.get_trigger_appendix(rqfilename, rqparams, configuration)
        if rqfilename_appendix:
            rqfilename += '_' + rqfilename_appendix

        # handle PROXY tag
        entity_proxy = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/proxy'
        )
        if entity_proxy:
            source = 'proxy'
            target = entity_proxy[0].xpath('./text()')[0]
        else:
            source = 'filesystem'

        # handle TARPIT tag
        entity_tarpit = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/tarpit'
        )
        if entity_tarpit:
            tarpit = self.server.config_sanitize_tarpit(entity_tarpit[0].xpath('./text()')[0])
        else:
            tarpit = None

        # check if we have to delay further actions due to global or local TARPIT configuration
        if tarpit is not None:
            # this node has its own delay configuration
            self.server.do_tarpit(tarpit)
        else:
            # no delay configuration for this node. check for global latency
            if self.server.tarpit is not None:
                # fall back to the globally configured latency
                self.server.do_tarpit(self.server.tarpit)

        # If the requested resource resides on our filesystem,
        # we try retrieve all metadata and the resource itself from there.
        if source == 'filesystem':

            # handle STATUS tag
            # ( filesystem only, since proxied requests come with their own status )
            entity_status = configuration.xpath(
                '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/status'
            )
            if entity_status:
                status = int(entity_status[0].xpath('./text()')[0])
            else:
                status = 200

            # retrieve headers from entities configuration block
            headers = self.get_entity_headers(rqfilename, headers, configuration)

            # retrieve trailers from entities configuration block
            trailers = self.get_entity_trailers(rqfilename, configuration)

            # retrieve payload directly from filesystem, if possible.
            # If this is not possible, return an empty, zero sized string.
            try:
                with open(docpath + 'htdocs' + rqfilename, 'rb') as f:
                    payload = f.read()

            except IOError as e:
                if not os.path.isdir(docpath + 'htdocs' + rqfilename):
                    logger.error('Failed to get template content: {0}'.format(e))
                payload = ''

            # there might be template data that can be substituted within the
            # payload. We only substitute data that is going to be displayed
            # by the browser:

            templated = False
            for header in headers:
                if header[0].lower() == 'content-type' and header[1].lower() == 'text/html':
                    templated = True

            if templated:
                # perform template substitution on payload
                payload = self.substitute_template_fields(payload)

            # How do we transport the content?
            chunked_transfer = configuration.xpath(
                '//conpot_template/protocols/http/htdocs/node[@name="' + rqfilename + '"]/chunks'
            )

            if chunked_transfer:
                # Calculate and append a chunked transfer encoding header
                headers.append(('Transfer-Encoding', 'chunked'))
                chunks = str(chunked_transfer[0].xpath('./text()')[0])
            else:
                # Calculate and append a content length header
                headers.append(('Content-Length', payload.__len__()))
                chunks = '0'

            return status, headers, trailers, payload, chunks

        # the requested resource resides on another server,
        # so we act as a proxy between client and target system

        elif source == 'proxy':

            # open a connection to the remote system.
            # If something goes wrong, fall back to 503

            trailers = []

            try:
                conn = httplib.HTTPConnection(target)
                conn.request("GET", requeststring)
                response = conn.getresponse()

                status = int(response.status)
                headers = response.getheaders()    # We REPLACE the headers to avoid duplicates!
                payload = response.read()
                chunks = '0'

            except:
                status = 503
                (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                                requeststring,
                                                                                headers,
                                                                                configuration,
                                                                                docpath)

            return status, headers, trailers, payload, chunks

    def send_chunked(self, chunks, payload, trailers):
        """Send payload via chunked transfer encoding to the
        client, followed by eventual trailers."""

        chunk_list = chunks.split(',')
        pointer = 0
        for cwidth in chunk_list:
            cwidth = int(cwidth)
            # send chunk length indicator
            self.wfile.write(format(cwidth, 'x').upper() + "\r\n")
            # send chunk payload
            self.wfile.write(payload[pointer:pointer + cwidth] + "\r\n")
            pointer += cwidth

        # is there another chunk that has not been configured? Send it anyway for the sake of completeness..
        if len(payload) > pointer:
            # send chunk length indicator
            self.wfile.write(format(len(payload) - pointer, 'x').upper() + "\r\n")
            # send chunk payload
            self.wfile.write(payload[pointer:] + "\r\n")

        # we're done with the payload. Send a zero chunk as EOF indicator
        self.wfile.write('0'+"\r\n")

        # if there are trailing headers :-) we send them now..
        for trailer in trailers:
            self.wfile.write("%s: %s\r\n" % (trailer[0], trailer[1]))

        # and finally, the closing ceremony...
        self.wfile.write("\r\n")

    def send_error(self, code, message=None):
        """Send and log an error reply.
        This method is overloaded to make use of load_status()
        to allow handling of "Unsupported Method" errors.
        """

        headers = []
        headers.extend(self.server.global_headers)
        configuration = self.server.configuration
        docpath = self.server.docpath

        if not hasattr(self, 'headers'):
            self.headers = self.MessageClass(self.rfile, 0)

        trace_data_length = self.headers.getheader('content-length')
        unsupported_request_data = None

        if trace_data_length:
            unsupported_request_data = self.rfile.read(int(trace_data_length))

        # there are certain situations where variables are (not yet) registered
        # ( e.g. corrupted request syntax ). In this case, we set them manually.
        if hasattr(self, 'path'):
            requeststring = self.path
        else:
            requeststring = ''
            self.path = None
            if message is not None:
                logger.info(message)

        # generate the appropriate status code, header and payload
        (status, headers, trailers, payload, chunks) = self.load_status(code,
                                                                        requeststring.partition('?')[0],
                                                                        headers,
                                                                        configuration,
                                                                        docpath)

        # send http status to client
        self.send_response(status)

        # send all headers to client
        for header in headers:
            self.send_header(header[0], header[1])

        self.end_headers()

        # decide upon sending content as a whole or chunked
        if chunks == '0':
            # send payload as a whole to the client
            self.wfile.write(payload)
        else:
            # send payload in chunks to the client
            self.send_chunked(chunks, payload, trailers)

        # loggers
        self.log(self.request_version, self.command, self.client_address, (self.path,
                                                                           self.headers.headers,
                                                                           unsupported_request_data), status)

    def do_TRACE(self):
        """Handle TRACE requests."""

        # fetch configuration dependent variables from server instance
        headers = []
        headers.extend(self.server.global_headers)
        configuration = self.server.configuration
        docpath = self.server.docpath

        # retrieve TRACE body data
        # ( sticking to the HTTP protocol, there should not be any body in TRACE requests,
        #   an attacker could though use the body to inject data if not flushed correctly,
        #   which is done by accessing the data like we do now - just to be secure.. )

        trace_data_length = self.headers.getheader('content-length')
        trace_data = None

        if trace_data_length:
            trace_data = self.rfile.read(int(trace_data_length))

        # check configuration: are we allowed to use this method?
        if self.server.disable_method_trace is True:

            # Method disabled by configuration. Fall back to 501.
            status = 501
            (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                            self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        else:

            # Method is enabled
            status = 200
            payload = ''
            headers.append(('Content-Type', 'message/http'))

            # Gather all request data and return it to sender..
            for rqheader in self.headers:
                payload = payload + str(rqheader) + ': ' + self.headers.get(rqheader) + "\n"

        # send initial HTTP status line to client
        self.send_response(status)

        # send all headers to client
        for header in headers:
            self.send_header(header[0], header[1])

        self.end_headers()

        # send payload (the actual content) to client
        self.wfile.write(payload)

        # loggers
        self.log(self.request_version,
                 self.command,
                 self.client_address,
                 (self.path, self.headers.headers, trace_data),
                 status)

    def do_HEAD(self):
        """Handle HEAD requests."""

        # fetch configuration dependent variables from server instance
        headers = []
        headers.extend(self.server.global_headers)
        configuration = self.server.configuration
        docpath = self.server.docpath

        # retrieve HEAD body data
        # ( sticking to the HTTP protocol, there should not be any body in HEAD requests,
        #   an attacker could though use the body to inject data if not flushed correctly,
        #   which is done by accessing the data like we do now - just to be secure.. )

        head_data_length = self.headers.getheader('content-length')
        head_data = None

        if head_data_length:
            head_data = self.rfile.read(int(head_data_length))

        # check configuration: are we allowed to use this method?
        if self.server.disable_method_head is True:

            # Method disabled by configuration. Fall back to 501.
            status = 501
            (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                            self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        else:

            # try to find a configuration item for this GET request
            entity_xml = configuration.xpath(
                '//conpot_template/protocols/http/htdocs/node[@name="'
                + self.path.partition('?')[0].decode('utf8') + '"]'
            )

            if entity_xml:
                # A config item exists for this entity. Handle it..
                (status, headers, trailers, payload, chunks) = self.load_entity(self.path,
                                                                                headers,
                                                                                configuration,
                                                                                docpath)

            else:
                # No config item could be found. Fall back to a standard 404..
                status = 404
                (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                                self.path,
                                                                                headers,
                                                                                configuration,
                                                                                docpath)

        # send initial HTTP status line to client
        self.send_response(status)

        # send all headers to client
        for header in headers:
            self.send_header(header[0], header[1])

        self.end_headers()

        # loggers
        self.log(self.request_version,
                 self.command,
                 self.client_address,
                 (self.path, self.headers.headers, head_data),
                 status)

    def do_OPTIONS(self):
        """Handle OPTIONS requests."""

        # fetch configuration dependent variables from server instance
        headers = []
        headers.extend(self.server.global_headers)
        configuration = self.server.configuration
        docpath = self.server.docpath

        # retrieve OPTIONS body data
        # ( sticking to the HTTP protocol, there should not be any body in HEAD requests,
        #   an attacker could though use the body to inject data if not flushed correctly,
        #   which is done by accessing the data like we do now - just to be secure.. )

        options_data_length = self.headers.getheader('content-length')
        options_data = None

        if options_data_length:
            options_data = self.rfile.read(int(options_data_length))

        # check configuration: are we allowed to use this method?
        if self.server.disable_method_options is True:

            # Method disabled by configuration. Fall back to 501.
            status = 501
            (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                            self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        else:

            status = 200
            payload = ''

            # Add ALLOW header to response. GET, POST and OPTIONS are static, HEAD and TRACE are dynamic
            allowed_methods = 'GET'

            if self.server.disable_method_head is False:
                # add head to list of allowed methods
                allowed_methods += ',HEAD'

            allowed_methods += ',POST,OPTIONS'

            if self.server.disable_method_trace is False:
                allowed_methods += ',TRACE'

            headers.append(('Allow', allowed_methods))

            # Calculate and append a content length header
            headers.append(('Content-Length', payload.__len__()))

            # Append CC header
            headers.append(('Connection', 'close'))

            # Append CT header
            headers.append(('Content-Type', 'text/html'))

        # send initial HTTP status line to client
        self.send_response(status)

        # send all headers to client
        for header in headers:
            self.send_header(header[0], header[1])

        self.end_headers()

        # loggers
        self.log(self.request_version,
                 self.command,
                 self.client_address,
                 (self.path, self.headers.headers, options_data),
                 status)

    def do_GET(self):
        """Handle GET requests"""

        # fetch configuration dependent variables from server instance
        headers = []
        headers.extend(self.server.global_headers)
        configuration = self.server.configuration
        docpath = self.server.docpath

        # retrieve GET body data
        # ( sticking to the HTTP protocol, there should not be any body in GET requests,
        #   an attacker could though use the body to inject data if not flushed correctly,
        #   which is done by accessing the data like we do now - just to be secure.. )

        get_data_length = self.headers.getheader('content-length')
        get_data = None

        if get_data_length:
            get_data = self.rfile.read(int(get_data_length))

        # try to find a configuration item for this GET request
        entity_xml = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + self.path.partition('?')[0].decode('utf8') + '"]'
        )

        if entity_xml:
            # A config item exists for this entity. Handle it..
            (status, headers, trailers, payload, chunks) = self.load_entity(self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        else:
            # No config item could be found. Fall back to a standard 404..
            status = 404
            (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                            self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        # send initial HTTP status line to client
        self.send_response(status)

        # send all headers to client
        for header in headers:
            self.send_header(header[0], header[1])

        self.end_headers()

        # decide upon sending content as a whole or chunked
        if chunks == '0':
            # send payload as a whole to the client
            self.wfile.write(payload)
        else:
            # send payload in chunks to the client
            self.send_chunked(chunks, payload, trailers)

        # loggers
        self.log(self.request_version,
                 self.command,
                 self.client_address,
                 (self.path, self.headers.headers, get_data),
                 status)

    def do_POST(self):
        """Handle POST requests"""

        # fetch configuration dependent variables from server instance
        headers = []
        headers.extend(self.server.global_headers)
        configuration = self.server.configuration
        docpath = self.server.docpath

        # retrieve POST data ( important to flush request buffers )
        post_data_length = self.headers.getheader('content-length')
        post_data = None

        if post_data_length:
            post_data = self.rfile.read(int(post_data_length))

        # try to find a configuration item for this POST request
        entity_xml = configuration.xpath(
            '//conpot_template/protocols/http/htdocs/node[@name="' + self.path.partition('?')[0].decode('utf8') + '"]'
        )

        if entity_xml:
            # A config item exists for this entity. Handle it..
            (status, headers, trailers, payload, chunks) = self.load_entity(self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        else:
            # No config item could be found. Fall back to a standard 404..
            status = 404
            (status, headers, trailers, payload, chunks) = self.load_status(status,
                                                                            self.path,
                                                                            headers,
                                                                            configuration,
                                                                            docpath)

        # send initial HTTP status line to client
        self.send_response(status)

        # send all headers to client
        for header in headers:
            self.send_header(header[0], header[1])

        self.end_headers()

        # decide upon sending content as a whole or chunked
        if chunks == '0':
            # send payload as a whole to the client
            self.wfile.write(payload)
        else:
            # send payload in chunks to the client
            self.send_chunked(chunks, payload, trailers)

        # loggers
        self.log(self.request_version,
                 self.command,
                 self.client_address,
                 (self.path, self.headers.headers, post_data),
                 status)


class TemplateParser(HTMLParser):
    def __init__(self, data):
        self.databus = conpot_core.get_databus()
        HTMLParser.__init__(self)
        self.payload = data
        self.feed(data)

    def handle_startendtag(self, tag, attrs):
        """ handles template tags provided in XHTML notation.

            Expected format:    <condata source="(engine)" key="(descriptor)" />
            Example:            <condata source="databus" key="SystemDescription" />

            at the moment, the parser is space- and case-sensitive(!),
            this could be improved by using REGEX for replacing the template tags
            with actual values.
        """

        source = ''
        key = ''

        # only parse tags that are conpot template tags ( <condata /> )
        if tag == 'condata':

            # initialize original tag (needed for value replacement)
            origin = '<' + tag

            for attribute in attrs:

                # extend original tag
                origin = origin + ' ' + attribute[0] + '="' + attribute[1] + '"'

                # fill variables with all meta information needed to
                # gather actual data from the other engines (databus, modbus, ..)
                if attribute[0] == 'source':
                    source = attribute[1]
                elif attribute[0] == 'key':
                    key = attribute[1]

            # finalize original tag
            origin += ' />'

            # we really need a key in order to do our work..
            if key:
                # deal with databus powered tags:
                if source == 'databus':
                    self.result = self.databus.get_value(key)
                    self.payload = self.payload.replace(origin, str(self.result))

                # deal with eval powered tags:
                elif source == 'eval':
                    result = ''
                    # evaluate key
                    try:
                        result = eval(key)
                    except Exception as e:
                        logger.exception(e)
                    self.payload = self.payload.replace(origin, result)


class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""


class SubHTTPServer(ThreadedHTTPServer):
    """this class is necessary to allow passing custom request handler into
       the RequestHandlerClass"""

    def __init__(self, server_address, RequestHandlerClass, template, docpath):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)

        self.docpath = docpath

        # default configuration
        self.update_header_date = True             # this preserves authenticity
        self.disable_method_head = False
        self.disable_method_trace = False
        self.disable_method_options = False
        self.tarpit = '0'

        # load the configuration from template and parse it
        # for the first time in order to reduce further handling..
        self.configuration = etree.parse(template)

        xml_config = self.configuration.xpath('//conpot_template/protocols/http/global/config/*')
        if xml_config:

            # retrieve all global configuration entities
            for entity in xml_config:

                if entity.attrib['name'] == 'protocol_version':
                    RequestHandlerClass.protocol_version = entity.text

                elif entity.attrib['name'] == 'update_header_date':
                    if entity.text.lower() == 'false':
                        # DATE header auto update disabled by configuration
                        self.update_header_date = False
                    elif entity.text.lower() == 'true':
                        # DATE header auto update enabled by configuration
                        self.update_header_date = True

                elif entity.attrib['name'] == 'disable_method_head':
                    if entity.text.lower() == 'false':
                        # HEAD method enabled by configuration
                        self.disable_method_head = False
                    elif entity.text.lower() == 'true':
                        # HEAD method disabled by configuration
                        self.disable_method_head = True

                elif entity.attrib['name'] == 'disable_method_trace':
                    if entity.text.lower() == 'false':
                        # TRACE method enabled by configuration
                        self.disable_method_trace = False
                    elif entity.text.lower() == 'true':
                        # TRACE method disabled by configuration
                        self.disable_method_trace = True

                elif entity.attrib['name'] == 'disable_method_options':
                    if entity.text.lower() == 'false':
                        # OPTIONS method enabled by configuration
                        self.disable_method_options = False
                    elif entity.text.lower() == 'true':
                        # OPTIONS method disabled by configuration
                        self.disable_method_options = True

                elif entity.attrib['name'] == 'tarpit':
                    if entity.text:
                        self.tarpit = self.config_sanitize_tarpit(entity.text)

        # load global headers from XML
        self.global_headers = []
        xml_headers = self.configuration.xpath('//conpot_template/protocols/http/global/headers/*')
        if xml_headers:

            # retrieve all headers assigned to this status code
            for header in xml_headers:
                if header.attrib['name'].lower() == 'date' and self.update_header_date is True:
                    # All HTTP date/time stamps MUST be represented in Greenwich Mean Time (GMT),
                    # without exception ( RFC-2616 )
                    self.global_headers.append((header.attrib['name'],
                                                time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())))
                else:
                    self.global_headers.append((header.attrib['name'], header.text))

    def config_sanitize_tarpit(self, value):

        # checks tarpit value for being either a single int or float,
        # or a series of two concatenated integers and/or floats seperated by semicolon and returns
        # either the (sanitized) value or zero.

        if value is not None:

            x, _, y = value.partition(';')

            try:
                _ = float(x)
            except ValueError:
                # first value is invalid, ignore the whole setting.
                logger.error("Invalid tarpit value: '{0}'. Assuming no latency.".format(value))
                return '0;0'

            try:
                _ = float(y)
                # both values are fine.
                return value
            except ValueError:
                # second value is invalid, use the first one.
                return x

        else:
            return '0;0'

    def do_tarpit(self, delay):

        # sleeps the thread for $delay ( should be either 1 float to apply a static period of time to sleep,
        # or 2 floats seperated by semicolon to sleep a randomized period of time determined by ( rand[x;y] )

        lbound, _, ubound = delay.partition(";")

        if not lbound or lbound is None:
            # no lower boundary found. Assume zero latency
            pass
        elif not ubound or ubound is None:
            # no upper boundary found. Assume static latency
            gevent.sleep(float(lbound))
        else:
            # both boundaries found. Assume random latency between lbound and ubound
            gevent.sleep(random.uniform(float(lbound), float(ubound)))


class CommandResponder(object):

    def __init__(self, host, port, template, docpath):

        # Create HTTP server class
        self.httpd = SubHTTPServer((host, port), HTTPServer, template, docpath)
        self.server_port = self.httpd.server_port

    def serve_forever(self):
        self.httpd.serve_forever()

    def stop(self):
        logging.info("HTTP server will shut down gracefully as soon as all connections are closed.")
        self.httpd.shutdown()

########NEW FILE########
__FILENAME__ = web_server
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging

from conpot.protocols.http.command_responder import CommandResponder


logger = logging.getLogger()


class HTTPServer(object):

    def __init__(self, host, port, template, docpath):
        self.host = host
        self.port = port
        self.docpath = docpath

        self.cmd_responder = CommandResponder(host, port, template, docpath)
        self.cmd_responder.httpd.allow_reuse_address = True
        self.server_port = self.cmd_responder.server_port

    def start(self):
        if self.cmd_responder:
            logger.info('HTTP server started on: {0}'.format((self.host, self.port)))
            self.cmd_responder.serve_forever()

    def stop(self):
        if self.cmd_responder:
            self.cmd_responder.stop()

    def shutdown(self):
        if self.cmd_responder:
            self.cmd_responder.httpd.shutdown()

########NEW FILE########
__FILENAME__ = decoder_382
# Copyright (C) 2014  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging

import crc16


logger = logging.getLogger(__name__)


class Decoder(object):
    REQUEST_MAGIC = 0x80
    RESPONSE_MAGIC = 0x40
    EOT_MAGIC = 0x0d

    # Following constants has been taken from pykamstrup, thanks to PHK/Erik Jensen!
    # I owe beer...
    # ----------------------------------------------------------------------------
    # "THE BEER-WARE LICENSE" (Revision 42):
    # <phk@FreeBSD.ORG> wrote this file.  As long as you retain this notice you
    # can do whatever you want with this stuff. If we meet some day, and you think
    # this stuff is worth it, you can buy me a beer in return.   Poul-Henning Kamp
    # ----------------------------------------------------------------------------
    UNITS = {
        0: '', 1: 'Wh', 2: 'kWh', 3: 'MWh', 4: 'GWh', 5: 'j', 6: 'kj', 7: 'Mj',
        8: 'Gj', 9: 'Cal', 10: 'kCal', 11: 'Mcal', 12: 'Gcal', 13: 'varh',
        14: 'kvarh', 15: 'Mvarh', 16: 'Gvarh', 17: 'VAh', 18: 'kVAh',
        19: 'MVAh', 20: 'GVAh', 21: 'kW', 22: 'kW', 23: 'MW', 24: 'GW',
        25: 'kvar', 26: 'kvar', 27: 'Mvar', 28: 'Gvar', 29: 'VA', 30: 'kVA',
        31: 'MVA', 32: 'GVA', 33: 'V', 34: 'A', 35: 'kV', 36: 'kA', 37: 'C',
        38: 'K', 39: 'l', 40: 'm3', 41: 'l/h', 42: 'm3/h', 43: 'm3xC',
        44: 'ton', 45: 'ton/h', 46: 'h', 47: 'hh:mm:ss', 48: 'yy:mm:dd',
        49: 'yyyy:mm:dd', 50: 'mm:dd', 51: '', 52: 'bar', 53: 'RTC',
        54: 'ASCII', 55: 'm3 x 10', 56: 'ton x 10', 57: 'GJ x 10',
        58: 'minutes', 59: 'Bitfield', 60: 's', 61: 'ms', 62: 'days',
        63: 'RTC-Q', 64: 'Datetime'
    }

    ESCAPES = [0x06, 0x0d, 0x1b, 0x40, 0x80]

    KAMSTRUP_382_REGISTERS = {

        0x0001: "Energy in",
        0x0002: "Energy out",

        0x000d: "Energy in hi-res",
        0x000e: "Energy out hi-res",

        0x041e: "Voltage p1",
        0x041f: "Voltage p2",
        0x0420: "Voltage p3",

        0x0434: "Current p1",
        0x0435: "Current p2",
        0x0436: "Current p3",

        0x0438: "Power p1",
        0x0439: "Power p2",
        0x043a: "Power p3",
    }

    def __init__(self):
        self.in_data = []
        self.in_parsing = False
        self.out_data = []
        self.out_parsing = False
        self.command_map = {0x01: self._decode_cmd_get_type,
                            0x10: self._decode_cmd_get_register,
                            0x92: self._decode_cmd_login}

    def decode_in(self, data):
        for d in data:
            if not self.in_parsing and d != Decoder.REQUEST_MAGIC:
                logger.debug('No kamstrup request magic received, got: {0}'.format(d.encode('hex-codec')))
            else:
                self.in_parsing = True
                if d is 0x0d:
                    if not self.valid_crc(self.in_data[1:]):
                        self.in_parsing = False
                        # TODO: Log discarded bytes?
                        return 'Request discarded due to invalid CRC.'
                    # now we expect (0x80, 0x3f, 0x10) =>
                    # (request magic, unknown byte, command byte)
                    if self.in_data[2] in self.command_map:
                        return self.command_map[self.in_data[2]]()
                    else:
                        return 'Expected request magic but got: {0}, ignoring request.' \
                            .format(self.in_data[2].encode('hex-codec'))
                else:
                    self.in_data.append(d)

    def _decode_cmd_get_register(self):
        assert (self.in_data[2] == 0x10)
        unknown_byte = self.in_data[1]
        cmd = self.in_data[2]
        register_count = self.in_data[3]
        message = 'Request for {0} register(s): '.format(register_count)
        for count in range(register_count):
            register = self.in_data[4 + count] * 256 + self.in_data[5 + count]
            if register in Decoder.KAMSTRUP_382_REGISTERS:
                message += '{0} ({1})'.format(register, Decoder.KAMSTRUP_382_REGISTERS[register])
            else:
                message += 'Unknown ({1})'.format(register)
            if count + 1 < register_count:
                message += ', '
        self.in_data = []
        return message

    # meter type
    def _decode_cmd_get_type(self):
        assert (self.in_data[2] == 0x01)
        return 'Request for GetType'

    def _decode_cmd_login(self):
        assert (self.in_data[2] == 0x92)
        unknown_byte = self.in_data[1]
        pin_code = self.in_data[3] * 256 + self.in_data[4]
        return 'Login command with pin_code: {0}'.format(pin_code)

    def decode_out(self, data):
        for d in data:
            if not self.out_parsing and d != Decoder.RESPONSE_MAGIC:
                logger.debug('Expected response magic but got got: {0}'.format(d.encode('hex-codec')))
            else:
                self.out_parsing = True
                if d is 0x0d:
                    if not self.valid_crc(self.out_data[1:]):
                        self.out_parsing = False
                        # TODO: Log discarded bytes?
                        return 'Response discarded due to invalid CRC.'
                    return self._decode_req()
                else:
                    self.out_data.append(d)

    # supplied message should be stripped of leading and trailing magic
    def valid_crc(self, message):
        supplied_crc = message[-2] * 256 + message[-1]
        calculated_crc = crc16.crc16xmodem(''.join([chr(item) for item in message[:-2]]))
        return supplied_crc == calculated_crc

    def _decode_response(self):
        return 'Decoding of this response has not been implemented yet.'




########NEW FILE########
__FILENAME__ = modbus_block_databus_mediator

from modbus_tk.hooks import call_hooks
import conpot.core as conpot_core


class ModbusBlockDatabusMediator:
    """This class represents the values for a range of addresses"""

    def __init__(self, databus_key, starting_address, size):
        """
        Constructor: defines the address range and creates the array of values
        """
        self.starting_address = starting_address
        # self._data = [0]*size
        self.databus_key = databus_key
        self.size = len(conpot_core.get_databus().get_value(self.databus_key))

    def is_in(self, starting_address, size):
        """
        Returns true if a block with the given address and size
        would overlap this block
        """
        if starting_address > self.starting_address:
            return (self.starting_address+self.size) > starting_address
        elif starting_address < self.starting_address:
            return (starting_address + size) > self.starting_address
        return True

    def __getitem__(self, r):
        """"""
        return conpot_core.get_databus().get_value(self.databus_key).__getitem__(r)

    def __setitem__(self, r, v):
        """"""
        call_hooks("modbus.ModbusBlock.setitem", (self, r, v))
        obj = conpot_core.get_databus().get_value(self.databus_key)
        return obj.__setitem__(r, v)

########NEW FILE########
__FILENAME__ = modbus_server
import struct
import socket
import time
import logging

from lxml import etree
from gevent.server import StreamServer

import modbus_tk.modbus_tcp as modbus_tcp
from modbus_tk import modbus
# Following imports are required for modbus template evaluation
import modbus_tk.defines as mdef
import random

from conpot.protocols.modbus import slave_db
import conpot.core as conpot_core

logger = logging.getLogger(__name__)


class ModbusServer(modbus.Server):

    def __init__(self, template, timeout=5):

        self.timeout = timeout
        databank = slave_db.SlaveBase(template)

        # Constructor: initializes the server settings
        modbus.Server.__init__(self, databank if databank else modbus.Databank())

        # not sure how this class remember slave configuration across instance creation, i guess there are some
        # well hidden away class variables somewhere.
        self.remove_all_slaves()
        self._configure_slaves(template)

    def _configure_slaves(self, template):
        dom = etree.parse(template)
        slaves = dom.xpath('//conpot_template/protocols/modbus/slaves/*')
        for s in slaves:
            slave_id = int(s.attrib['id'])
            slave = self.add_slave(slave_id)
            logger.debug('Added slave with id {0}.'.format(slave_id))
            for b in s.xpath('./blocks/*'):
                name = b.attrib['name']
                request_type = eval('mdef.' + b.xpath('./type/text()')[0])
                start_addr = int(b.xpath('./starting_address/text()')[0])
                size = int(b.xpath('./size/text()')[0])
                slave.add_block(name, request_type, start_addr, size)
                logger.debug('Added block {0} to slave {1}. (type={2}, start={3}, size={4})'.format(
                    name, slave_id, request_type, start_addr, size
                ))
        template_name = dom.xpath('//conpot_template/@name')[0]
        logger.info('Conpot modbus initialized using the {0} template.'.format(template_name))

    def handle(self, sock, address):
        sock.settimeout(self.timeout)

        session = conpot_core.get_session('modbus', address[0], address[1])

        self.start_time = time.time()
        logger.info('New connection from {0}:{1}. ({2})'.format(address[0], address[1], session.id))

        try:
            while True:
                request = sock.recv(7)
                if not request:
                    logger.info('Client disconnected. ({0})'.format(session.id))
                    break
                if request.strip().lower() == 'quit.':
                    logger.info('Client quit. ({0})'.format(session.id))
                    break
                tr_id, pr_id, length = struct.unpack(">HHH", request[:6])
                while len(request) < (length + 6):
                    new_byte = sock.recv(1)
                    request += new_byte
                query = modbus_tcp.TcpQuery()

                # logdata is a dictionary containing request, slave_id, function_code and response
                response, logdata = self._databank.handle_request(query, request)
                logdata['request'] = request.encode('hex')
                session.add_event(logdata)

                logger.debug('Modbus traffic from {0}: {1} ({2})'.format(address[0], logdata, session.id))

                if response:
                    sock.sendall(response)
        except socket.timeout:
            logger.debug('Socket timeout, remote: {0}. ({1})'.format(address[0], session.id))

    def get_server(self, host, port):
        connection = (host, port)
        server = StreamServer(connection, self.handle)
        logger.info('Modbus server started on: {0}'.format(connection))
        return server
########NEW FILE########
__FILENAME__ = slave
import struct
import logging

from modbus_tk.modbus import Slave, ModbusError, ModbusInvalidRequestError, InvalidArgumentError, DuplicatedKeyError,\
                             InvalidModbusBlockError, OverlapModbusBlockError
from modbus_tk import defines, utils

from modbus_block_databus_mediator import ModbusBlockDatabusMediator

logger = logging.getLogger(__name__)


class MBSlave(Slave):

    def __init__(self, slave_id, dom):
        Slave.__init__(self, slave_id)
        self._fn_code_map = {defines.READ_COILS: self._read_coils,
                             defines.READ_DISCRETE_INPUTS: self._read_discrete_inputs,
                             defines.READ_INPUT_REGISTERS: self._read_input_registers,
                             defines.READ_HOLDING_REGISTERS: self._read_holding_registers,
                             defines.WRITE_SINGLE_COIL: self._write_single_coil,
                             defines.WRITE_SINGLE_REGISTER: self._write_single_register,
                             defines.WRITE_MULTIPLE_COILS: self._write_multiple_coils,
                             defines.WRITE_MULTIPLE_REGISTERS: self._write_multiple_registers,
                             defines.DEVICE_INFO: self._device_info,
                             }
        self.dom = dom

    def _device_info(self, request_pdu):
        info_root = self.dom.xpath('//conpot_template/protocols/modbus/device_info')[0]
        vendor_name = info_root.xpath('./VendorName/text()')[0]
        product_code = info_root.xpath('./ProductCode/text()')[0]
        major_minor_revision = info_root.xpath('./MajorMinorRevision/text()')[0]

        (req_device_id, req_object_id) = struct.unpack(">BB", request_pdu[2:4])
        device_info = {
            0: vendor_name,
            1: product_code,
            2: major_minor_revision
        }

        # MEI type
        response = struct.pack(">B", 0x0E)
        # requested device id
        response += struct.pack(">B", req_device_id)
        # conformity level
        response += struct.pack(">B", 0x01)
        # followup data 0x00 is False
        response += struct.pack(">B", 0x00)
        # No next object id
        response += struct.pack(">B", 0x00)
        # Number of objects
        response += struct.pack(">B", len(device_info))
        for i in range(len(device_info)):
            # Object id
            response += struct.pack(">B", i)
            # Object length
            response += struct.pack(">B", len(device_info[i]))
            response += device_info[i]
        return response

    def handle_request(self, request_pdu, broadcast=False):
        """
        parse the request pdu, makes the corresponding action
        and returns the response pdu
        """
        with self._data_lock:  # thread-safe
            try:
                # get the function code
                (self.function_code, ) = struct.unpack(">B", request_pdu[0])

                # check if the function code is valid. If not returns error response
                if not self.function_code in self._fn_code_map:
                    raise ModbusError(defines.ILLEGAL_FUNCTION)

                can_broadcast = [defines.WRITE_MULTIPLE_COILS, defines.WRITE_MULTIPLE_REGISTERS,
                                 defines.WRITE_SINGLE_COIL, defines.WRITE_SINGLE_REGISTER]
                if broadcast and (self.function_code not in can_broadcast):
                    raise ModbusInvalidRequestError("Function %d can not be broadcasted" % self.function_code)

                # execute the corresponding function
                response_pdu = self._fn_code_map[self.function_code](request_pdu)
                if response_pdu:
                    if broadcast:
                        # not really sure whats going on here - better log it!
                        logger.info("broadcast: %s" % (utils.get_log_buffer("!!", response_pdu)))
                        return ""
                    else:
                        return struct.pack(">B", self.function_code) + response_pdu
                raise Exception("No response for function %d" % self.function_code)

            except ModbusError as e:
                logger.error('Exception caught: {0}. (A proper response will be sent to the peer)'.format(e))
                return struct.pack(">BB", self.function_code + 128, e.get_exception_code())

    def add_block(self, block_name, block_type, starting_address, size):
        """Add a new block identified by its name"""
        with self._data_lock: # thread-safe
            if size <= 0:
                raise InvalidArgumentError, "size must be a positive number"
            if starting_address < 0:
                raise InvalidArgumentError, "starting address must be zero or positive number"
            if self._blocks.has_key(block_name):
                raise DuplicatedKeyError, "Block %s already exists. " % (block_name)

            if not self._memory.has_key(block_type):
                raise InvalidModbusBlockError, "Invalid block type %d" % (block_type)

            # check that the new block doesn't overlap an existing block
            # it means that only 1 block per type must correspond to a given address
            # for example: it must not have 2 holding registers at address 100
            index = 0
            for i in xrange(len(self._memory[block_type])):
                block = self._memory[block_type][i]
                if block.is_in(starting_address, size):
                    raise OverlapModbusBlockError, "Overlap block at %d size %d" % (block.starting_address, block.size)
                if block.starting_address > starting_address:
                    index = i
                    break

            # if the block is ok: register it
            self._blocks[block_name] = (block_type, starting_address)
            # add it in the 'per type' shortcut
            self._memory[block_type].insert(index, ModbusBlockDatabusMediator(block_name, starting_address, size))

########NEW FILE########
__FILENAME__ = slave_db
import struct
from lxml import etree

from modbus_tk.modbus import Databank, DuplicatedKeyError, MissingKeyError
from modbus_tk import defines

from conpot.protocols.modbus.slave import MBSlave


class SlaveBase(Databank):
    """
    Database keeping track of the slaves.
    """

    def __init__(self, template):
        Databank.__init__(self)
        self.dom = etree.parse(template)

    def add_slave(self, slave_id):
        """
        Add a new slave with the given id
        """
        if (slave_id <= 0) or (slave_id > 255):
            raise Exception("Invalid slave id %d" % slave_id)
        if not slave_id in self._slaves:
            self._slaves[slave_id] = MBSlave(slave_id, self.dom)
            return self._slaves[slave_id]
        else:
            raise DuplicatedKeyError("Slave %d already exists" % slave_id)

    def handle_request(self, query, request):
        """
        Handles a request. Return value is a tuple where element 0 is the response object and element 1 is a dictionary
        of items to log.
        """
        request_pdu = None
        response_pdu = ""
        slave_id = None
        function_code = None
        func_code = None
        slave = None
        response = None

        try:
            # extract the pdu and the slave id
            slave_id, request_pdu = query.parse_request(request)
            if len(request_pdu) > 0:
                (func_code, ) = struct.unpack(">B", request_pdu[0])
            # 43 is Device Information
            if func_code == 43:
                # except will throw MissingKeyError
                slave = self.get_slave(slave_id)
                response_pdu = slave.handle_request(request_pdu)
                # make the full response
                response = query.build_response(response_pdu)
            # get the slave and let him execute the action
            elif slave_id == 0:
                # broadcast
                for key in self._slaves:
                    response_pdu = self._slaves[key].handle_request(request_pdu, broadcast=True)
                    response = query.build_response(response_pdu)
            elif slave_id == 255:
                r = struct.pack(">BB", func_code + 0x80, 0x0B)
                response = query.build_response(r)
            else:
                slave = self.get_slave(slave_id)
                response_pdu = slave.handle_request(request_pdu)
                # make the full response
                response = query.build_response(response_pdu)
        except (IOError, MissingKeyError) as e:
            # If the request was not handled correctly, return a server error response
            r = struct.pack(">BB", func_code + 0x80, defines.SLAVE_DEVICE_FAILURE)
            response = query.build_response(r)

        if slave:
            function_code = slave.function_code

        return (response, {'request': request_pdu.encode('hex'),
                           'slave_id': slave_id,
                           'function_code': function_code,
                           'response': response_pdu.encode('hex')})

########NEW FILE########
__FILENAME__ = cotp
# This implementation of the S7 protocol is highly inspired
# by the amazing plcscan work by the ScadaStrangeLove group.
# https://code.google.com/p/plcscan/source/browse/trunk/s7.py

from struct import *
import struct

from conpot.protocols.s7comm.exceptions import ParseException


class COTP(object):
    def __init__(self, tpdu_type=0, opt_field=0, payload='', trailer=''):
        self.tpdu_type = tpdu_type
        self.opt_field = opt_field
        self.payload = payload
        self.trailer = trailer

        if self.tpdu_type == 240:
            self.packet_length = 2
        else:
            self.packet_length = 1 + len(self.payload)

            # COTP BASE PACKET FORMAT:
            # -------------------------------------
            #           1 byte      LENGTH (=n + 1)
            #           1 byte      TPDU TYPE
            #           1 byte      OPT FIELD (optional!), bitmask!
            #           n bytes     TPDU PAYLOAD
            #           x bytes     TRAILER (optional!), most probably containing S7.

    def pack(self):

        if self.tpdu_type == 0xf0:
            return pack('!BBB', self.packet_length, self.tpdu_type, self.opt_field) + str(self.payload) + \
                   str(self.trailer)
        else:
            return pack('!BB', self.packet_length, self.tpdu_type) + str(self.payload) + str(self.trailer)

    def parse(self, packet):

        try:
            header = unpack('!BBB', packet[:3])
        except struct.error:
            raise ParseException('s7comm', 'malformed packet header structure')

        self.packet_length = header[0]
        self.tpdu_type = int(header[1])
        self.trailer = packet[1 + self.packet_length:]

        if self.tpdu_type == 0xf0:
            # the DT DATA TPDU features another header byte that shifts our structure
            self.opt_field = header[2]
            self.payload = packet[3:1 + self.packet_length]
        else:
            self.payload = packet[2:1 + self.packet_length]

        return self


# COTP Connection Request or Connection Confirm packet (ISO on TCP). RFC 1006
class COTPConnectionPacket(object):
    def __init__(self, dst_ref=0, src_ref=0, opt_field=0, src_tsap=0, dst_tsap=0, tpdu_size=0):
        self.dst_ref = dst_ref
        self.src_ref = src_ref
        self.opt_field = opt_field
        self.src_tsap = src_tsap
        self.dst_tsap = dst_tsap
        self.tpdu_size = tpdu_size

        # COTP CR PACKET FORMAT:
        # -------------------------------------
        #           2 bytes     DST REFERENCE
        #           2 bytes     SRC REFERENCE
        #           1 byte      OPTION FIELD (bitmask!)
        #          ---------------------------------------
        #           n bytes     1 byte  PARAM CODE
        #                       1 byte  PARAM LENGTH (n)
        #                       n bytes PARAM DATA
        #          ---------------------------------------
        #           "n" Block repeats until end of packet

    def dissect(self, packet):

        # dissect fixed header
        try:
            fixed_header = unpack('!HHB', packet[:5])
        except struct.error:
            raise ParseException('s7comm', 'malformed fixed header structure')

        self.dst_ref = fixed_header[0]
        self.src_ref = fixed_header[1]
        self.opt_field = fixed_header[2]

        # dissect variable header
        chunk = packet[5:]
        while len(chunk) > 0:
            chunk_param_header = unpack('!BB', chunk[:2])
            chunk_param_code = int(chunk_param_header[0])
            chunk_param_length = chunk_param_header[1]

            if chunk_param_length == 1:
                param_unpack_structure = '!B'
            elif chunk_param_length == 2:
                param_unpack_structure = '!H'
            else:
                raise ParseException('s7comm', 'malformed variable header structure')

            chunk_param_data = unpack(param_unpack_structure, chunk[2:2 + chunk_param_length])

            if chunk_param_code == 0xc1:
                self.src_tsap = chunk_param_data[0]
            elif chunk_param_code == 0xc2:
                self.dst_tsap = chunk_param_data[0]
            elif chunk_param_code == 0xc0:
                self.tpdu_size = chunk_param_data[0]
            else:
                raise ParseException('s7comm', 'unknown parameter code')

            # remove this part of the chunk
            chunk = chunk[2 + chunk_param_length:]

        return self


class COTP_ConnectionConfirm(COTPConnectionPacket):
    def __init__(self, dst_ref=0, src_ref=0, opt_field=0, src_tsap=0, dst_tsap=0, tpdu_size=0):
        self.dst_ref = dst_ref
        self.src_ref = src_ref
        self.opt_field = opt_field
        self.src_tsap = src_tsap
        self.dst_tsap = dst_tsap
        self.tpdu_size = tpdu_size

    def assemble(self):
        return pack('!HHBBBHBBH', self.dst_ref, self.src_ref, self.opt_field,
                    0xc1,  # param code:   src-tsap
                    0x02,  # param length: 2 bytes
                    self.src_tsap,
                    0xc2,  # param code:   dst-tsap
                    0x02,  # param length: 2 bytes
                    self.dst_tsap)


class COTP_ConnectionRequest(COTPConnectionPacket):
    def __init__(self, dst_ref=0, src_ref=0, opt_field=0, src_tsap=0, dst_tsap=0, tpdu_size=0):
        self.dst_ref = dst_ref
        self.src_ref = src_ref
        self.opt_field = opt_field
        self.src_tsap = src_tsap
        self.dst_tsap = dst_tsap
        self.tpdu_size = tpdu_size

    def assemble(self):
        return pack('!HHBBBHBBHBBB', self.dst_ref, self.src_ref, self.opt_field,
                    0xc1,  # param code:   src-tsap
                    0x02,  # param length: 2 bytes
                    self.src_tsap,
                    0xc2,  # param code:   dst-tsap
                    0x02,  # param length: 2 bytes
                    self.dst_tsap,
                    0xc0,  # param code:   tpdu-size
                    0x01,  # param length: 1 byte
                    self.tpdu_size)

########NEW FILE########
__FILENAME__ = exceptions
class ParseException(Exception):

    def __init__(self, protocol, reason, payload=''):
        self.proto = protocol
        self.reason = reason
        self.payload = payload

    def __str__(self):
        return "DissectException: proto:{0} reason:{1}".format(self.proto, self.reason)


class AssembleException(Exception):

    def __init__(self, protocol, reason, payload=''):
        self.proto = protocol
        self.reason = reason
        self.payload = payload

    def __str__(self):
        return "AssembleException: proto:{0} reason:{1}".format(self.proto, self.reason)

########NEW FILE########
__FILENAME__ = s7
# References: S7_300-400_full_reference_handbook_ENGLISH.pdf
#             http://www.bj-ig.de/147.html
#             https://code.google.com/p/plcscan/source/browse/trunk/s7.py


from struct import *

import struct
import conpot.core as conpot_core

from conpot.protocols.s7comm.exceptions import AssembleException, ParseException


# S7 packet
class S7(object):

    ssl_lists = {}

    def __init__(self, pdu_type=0, reserved=0, request_id=0, result_info=0, parameters='', data=''):
        self.magic = 0x32
        self.pdu_type = pdu_type
        self.reserved = reserved
        self.request_id = request_id
        self.param_length = len(parameters)
        self.data_length = len(data)
        self.result_info = result_info
        self.parameters = parameters
        self.data = data

        # param codes (http://www.bj-ig.de/147.html):
        # maps request types to methods
        self.param_mapping = {0x00: ('diagnostics', self.request_diagnostics),
                              0x04: ('read', self.request_not_implemented),
                              0x05: ('write', self.request_not_implemented),
                              0x1a: ('request_download', self.request_not_implemented),
                              0x1b: ('download_block', self.request_not_implemented),
                              0x1c: ('end_download', self.request_not_implemented),
                              0x1d: ('start_upload', self.request_not_implemented),
                              0x1e: ('upload', self.request_not_implemented),
                              0x1f: ('end_upload', self.request_not_implemented),
                              0x28: ('insert_block', self.request_not_implemented)}

        # maps valid pdu codes to name
        self.pdu_mapping = {0x01: set('request_pdu'),
                            0x02: set('know_but_unindentified_pdu'),
                            0x03: set('response_pdu'),
                            0x07: set('system_status_list')}

        self.data_bus = conpot_core.get_databus()

    def __len__(self):

        if self.pdu_type in (2, 3):
            return 12 + int(self.param_length) + int(self.data_length)
        else:
            return 10 + int(self.param_length) + int(self.data_length)

    def handle(self):
        if self.param in self.param_mapping:
            # direct execution to the correct method based on the param
            return self.param_mapping[self.param][1]()

    def request_not_implemented(self):
        raise ParseException('s7comm', 'request not implemented in honeypot yet.')

    def pack(self):

        if self.pdu_type not in self.pdu_mapping:
            raise AssembleException('s7comm', 'invalid or unsupported pdu type')
        elif self.pdu_type in (2, 3):
            # type 2 and 3 feature an additional RESULT INFORMATION header
            return pack('!BBHHHHH', self.magic, self.pdu_type, self.reserved, self.request_id, self.param_length,
                        self.data_length, self.result_info) + self.parameters + self.data
        else:
            return pack('!BBHHHH', self.magic, self.pdu_type, self.reserved, self.request_id, self.param_length,
                        self.data_length) + self.parameters + self.data

    def parse(self, packet):

        # dissect fixed header
        try:
            fixed_header = unpack('!BBHHHH', packet[:10])
        except struct.error:
            raise ParseException('s7comm', 'malformed fixed packet header structure')

        self.magic = int(fixed_header[0])

        if self.magic != 0x32:
            raise ParseException('s7comm', 'bad magic number, expected 0x32 but got {0}.'.format(self.magic))

        self.pdu_type = fixed_header[1]
        self.reserved = fixed_header[2]
        self.request_id = fixed_header[3]
        self.param_length = fixed_header[4]
        self.data_length = fixed_header[5]

        # dissect variable header

        if self.pdu_type in (2, 3):
            # type 2 and 3 feature an additional RESULT INFORMATION header
            self.result_info = unpack('!H', packet[10:12])
            header_offset = 2
        else:
            header_offset = 0

        self.parameters = packet[10 + header_offset:10 + header_offset + self.param_length]
        self.data = packet[10 + header_offset + self.param_length:10 + header_offset + self.param_length +
                           self.data_length]

        try:
            self.param = unpack('!B', self.parameters[:1])[0]
        except:
            raise ParseException('s7comm', 'invalid packet')

        return self

    # SSL/SZL System Status List/Systemzustandsliste
    def request_diagnostics(self):

        # semi-check
        try:
            unpack('!BBBBBBBB', self.parameters[:8])
        except struct.error:
            raise ParseException('s7comm', 'malformed SSL/SZL parameter structure')

        chunk = self.data
        chunk_id = 0

        while chunk:
            try:
                ssl_chunk_header = unpack('!BBH', chunk[:4])
            except struct.error:
                raise ParseException('s7comm', 'malformed SSL/SZL data structure')

            # dissect data blocks

            data_error_code = ssl_chunk_header[0]
            data_data_type = ssl_chunk_header[1]
            data_next_bytes = ssl_chunk_header[2]
            data_ssl_id = ''
            data_ssl_index = ''
            data_ssl_unknown = ''

            if data_next_bytes > 0:
                data_ssl_id = unpack('!H', chunk[4:6])[0]

            if data_next_bytes > 1:
                data_ssl_index = unpack('!H', chunk[6:8])[0]

            if data_next_bytes > 2:
                data_ssl_unknown = chunk[8:4 + data_next_bytes]

            # map request ssl to method
            if hasattr(self, 'request_ssl_{0}'.format(data_ssl_id)):
                m = getattr(self, 'request_ssl_{0}'.format(data_ssl_id))
                description, params, data = m(data_ssl_index)
                return params, data

            chunk = chunk[4 + data_next_bytes:]
            chunk_id += 1

        return 0x00, 0x00

    # W#16#xy11 - module identification
    def request_ssl_17(self, data_ssl_index):

        # just for convenience
        current_ssl = S7.ssl_lists['W#16#xy11']

        if data_ssl_index == 1:    # 0x0001 - component identification

            ssl_index_description = 'Component identification'

            ssl_resp_data = pack('!HHHHH20sHHH',
                                 17,  # 1  WORD   ( ID )
                                 data_ssl_index,  # 1  WORD   ( Index )
                                 28,  # 1  WORD   ( Length of payload after element count )
                                 0x01,  # 1  WORD   ( 1 element follows )
                                 data_ssl_index,  # 1  WORD   ( Data Index )
                                 self.data_bus.get_value(current_ssl['W#16#0001']),
                                 # 10 WORDS  ( MLFB of component: 20 bytes => 19 chars + 1 blank (0x20) )
                                 0x0,  # 1  WORD   ( RESERVED )
                                 0x0,  # 1  WORD   ( Output state of component )
                                 0x0)                       # 1  WORD   ( RESERVED )

            ssl_resp_head = pack('!BBH',
                                 0xff,  # 1  BYTE   ( Data Error Code. 0xFF = OK )
                                 0x09,  # 1  BYTE   ( Data Type. 0x09 = Char/String )
                                 len(ssl_resp_data))        # 1  WORD   ( Length of following data )

        elif data_ssl_index == 6:  # 0x0006 - hardware identification

            ssl_index_description = 'Hardware identification'

            ssl_resp_data = pack('!HHHHH20sHHH',
                                 17,  # 1  WORD   ( ID )
                                 data_ssl_index,  # 1  WORD   ( Index )
                                 28,  # 1  WORD   ( Length of payload after element count )
                                 0x01,  # 1  WORD   ( 1 element follows )
                                 data_ssl_index,  # 1  WORD   ( Data Index )
                                 self.data_bus.get_value(current_ssl['W#16#0006']),
                                 # 10 WORDS  ( MLFB of component: 20 bytes => 19 chars + 1 blank (0x20) )
                                 0x0,  # 1  WORD   ( RESERVED )
                                 'V3',  # 1  WORD   ( 'V' and first digit of version number )
                                 0x539)                     # 1  WORD   ( remaining digits of version number )

            ssl_resp_head = pack('!BBH',
                                 0xff,  # 1  BYTE   ( Data Error Code. 0xFF = OK )
                                 0x09,  # 1  BYTE   ( Data Type. 0x09 = Char/String )
                                 len(ssl_resp_data))  # 1  WORD   ( Length of following data )

        elif data_ssl_index == 7:  # 0x0007 - firmware identification

            ssl_index_description = 'Firmware identification'

            ssl_resp_data = pack('!HHHHH20sHHH',
                                 17,  # 1  WORD   ( ID )
                                 data_ssl_index,  # 1  WORD   ( Index )
                                 28,  # 1  WORD   ( Length of payload after element count )
                                 0x01,  # 1  WORD   ( 1 element follows )
                                 data_ssl_index,  # 1  WORD   ( Data Index )
                                 0x0,  # 10 WORDS  ( RESERVED )
                                 0x0,  # 1  WORD   ( RESERVED )
                                 'V3',  # 1  WORD   ( 'V' and first digit of version number )
                                 0x53A)  # 1  WORD   ( remaining digits of version number )

            ssl_resp_head = pack('!BBH',
                                 0xff,  # 1  BYTE   ( Data Error Code. 0xFF = OK )
                                 0x09,  # 1  BYTE   ( Data Type. 0x09 = Char/String )
                                 len(ssl_resp_data))  # 1  WORD   ( Length of following data )

        else:
            ssl_index_description = 'UNKNOWN / UNDEFINED / RESERVED {0}'.format(hex(data_ssl_index))
            ssl_resp_data = ''
            ssl_resp_head = ''

        ssl_resp_params = pack('!BBBBBBBB',
                               0x00,  # SSL DIAG
                               0x01,  # unknown
                               0x12,  # unknown
                               0x08,  # bytes following
                               0x12,  # unknown, maybe 0x11 + 1
                               0x84,  # function; response to 0x44
                               0x01,  # subfunction; readszl
                               0x01)  # sequence ( = sequence + 1 )
        return ssl_index_description, ssl_resp_params, ssl_resp_head + ssl_resp_data

    # W#16#011C
    def request_ssl_28(self, data_ssl_index):

        # just for convenience
        current_ssl = S7.ssl_lists['W#16#xy1C']
        # initiate header for mass component block
        ssl_resp_data = pack('!HHHH',
                             28,  # 1  WORD   ( ID )
                             data_ssl_index,  # 1  WORD   ( Index )
                             34,  # 1  WORD   ( Length of payload after element count )
                             0x08)  # 1  WORD   ( 2 elements follow )

        # craft module data 0x0001 - automation system name
        ssl_resp_data += pack('!H24s8s',
                              0x01,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#0001']),  # TODO: PADDING
                              # 'System Name             ', # 12 WORDS  ( Name of automation system, padded with (0x00) )
                              '')  # 4  WORDS  ( RESERVED )

        # craft module data 0x0002 - component name
        ssl_resp_data += pack('!H24s8s',
                              0x02,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#0002']),  # 12 WORDS  ( Name of component, padded with (0x00) )
                              '')  # 4  WORDS  ( RESERVED )

        # craft module data 0x0003 - plant identification
        ssl_resp_data += pack('!H32s',
                              0x03,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#0003']),)  # 16 WORDS  ( Name of plant, padded with (0x00) )

        # craft module data 0x0004 - copyright
        ssl_resp_data += pack('!H26s6s',
                              0x04,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#0004']),  # 13 WORDS  ( CONSTANT )
                              '')  # 3  WORDS  ( RESERVED )

        # craft module data 0x0005 - module serial number
        ssl_resp_data += pack('!H24s8s',
                              0x05,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#0005']),  # 12 WORDS  ( Unique Serial Number )
                              '')  # 4  WORDS  ( RESERVED )

        # craft module data 0x0007 - module type name
        ssl_resp_data += pack('!H32s',
                              0x07,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#0007']),)   # 16 WORDS  ( CPU type name, padded wit (0x00) )

        # craft module data 0x000a - OEM ID of module
        ssl_resp_data += pack('!H20s6s2s4s',
                              0x0a,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#000A']),  # 10 WORDS  ( OEM-Copyright Text, padded with (0x00) )
                              '',  # 3  WORDS  ( OEM Copyright Text padding to 26 characters )
                              '',  # 1  WORD   ( OEM ID provided by Siemens )
                              '')  # 2  WORDS  ( OEM user defined ID )

        # craft module data 0x000b - location
        ssl_resp_data += pack('!H32s',
                              0x0b,  # 1  WORD   ( Data Index )
                              self.data_bus.get_value(current_ssl['W#16#000B']),)  # 16 WORDS  ( Location String, padded with (0x00) )

        # craft leading response header
        ssl_resp_head = pack('!BBH',
                             0xff,  # 1  BYTE   ( Data Error Code. 0xFF = OK )
                             0x09,  # 1  BYTE   ( Data Type. 0x09 = Char/String )
                             len(ssl_resp_data))  # 1  WORD   ( Length of following data )

        ssl_resp_packet = ssl_resp_head + ssl_resp_data
        ssl_resp_params = pack('!BBBBBBBB',
                               0x00,  # SSL DIAG
                               0x01,  # unknown
                               0x12,  # unknown
                               0x08,  # bytes following
                               0x12,  # unknown, maybe 0x11 + 1
                               0x84,  # function; response to 0x44
                               0x01,  # subfunction; readszl
                               0x01)  # sequence ( = sequence + 1 )

        return '', ssl_resp_params, ssl_resp_packet

########NEW FILE########
__FILENAME__ = s7_server
# Copyright (C) 2013  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import time

from gevent.server import StreamServer
import gevent.monkey

gevent.monkey.patch_all()
import socket
from struct import unpack
from conpot.protocols.s7comm.tpkt import TPKT
from conpot.protocols.s7comm.cotp import COTP as COTP_BASE_packet
from conpot.protocols.s7comm.cotp import COTP_ConnectionRequest
from conpot.protocols.s7comm.cotp import COTP_ConnectionConfirm
from conpot.protocols.s7comm.s7 import S7
import conpot.core as conpot_core

import logging
from lxml import etree

logger = logging.getLogger(__name__)


class S7Server(object):
    def __init__(self, template):

        self.timeout = 5
        self.ssl_lists = {}
        S7.ssl_lists = self.ssl_lists

        dom = etree.parse(template)
        template_name = dom.xpath('//conpot_template/@name')[0]

        system_status_lists = dom.xpath('//conpot_template/protocols/s7comm/system_status_lists/*')
        for ssl in system_status_lists:
            ssl_id = ssl.attrib['id']
            ssl_dict = {}
            self.ssl_lists[ssl_id] = ssl_dict
            items = ssl.xpath('./*')
            for item in items:
                item_id = item.attrib['id']
                databus_key = item.xpath('./text()')[0] if len(item.xpath('./text()')) else ''
                ssl_dict[item_id] = databus_key

        logger.debug('Conpot debug info: S7 SSL/SZL: {0}'.format(self.ssl_lists))
        logger.info('Conpot S7Comm initialized using the {0} template.'.format(template_name))


    def handle(self, sock, address):
        sock.settimeout(self.timeout)
        session = conpot_core.get_session('s7comm', address[0], address[1])

        self.start_time = time.time()
        logger.info('New connection from {0}:{1}. ({2})'.format(address[0], address[1], session.id))

        try:
            while True:

                data = sock.recv(4, socket.MSG_WAITALL)
                if len(data) == 0:
                    break

                _, _, length = unpack('!BBH', data[:4])
                data += sock.recv(length - 4, socket.MSG_WAITALL)

                tpkt_packet = TPKT().parse(data)
                cotp_base_packet = COTP_BASE_packet().parse(tpkt_packet.payload)
                if cotp_base_packet.tpdu_type == 0xe0:

                    # connection request
                    cotp_cr_request = COTP_ConnectionRequest().dissect(cotp_base_packet.payload)
                    logger.debug('Received COTP Connection Request: dst-ref:{0} src-ref:{1} dst-tsap:{2} src-tsap:{3} '
                                 'tpdu-size:{4}. ({5})'.format(cotp_cr_request.dst_ref, cotp_cr_request.src_ref,
                                                               cotp_cr_request.dst_tsap, cotp_cr_request.src_tsap,
                                                               cotp_cr_request.tpdu_size, session.id))

                    # confirm connection response
                    cotp_cc_response = COTP_ConnectionConfirm(cotp_cr_request.src_ref, cotp_cr_request.dst_ref, 0,
                                                              cotp_cr_request.src_tsap, cotp_cr_request.dst_tsap,
                                                              0x0a).assemble()

                    # encapsulate and transmit
                    cotp_resp_base_packet = COTP_BASE_packet(0xd0, 0, cotp_cc_response).pack()
                    tpkt_resp_packet = TPKT(3, cotp_resp_base_packet).pack()
                    sock.send(tpkt_resp_packet)

                    session.add_event({'request': data.encode('hex'), 'response': tpkt_resp_packet.encode('hex')})

                    data = sock.recv(1024)

                    # another round of parsing payloads
                    tpkt_packet = TPKT().parse(data)
                    cotp_base_packet = COTP_BASE_packet().parse(tpkt_packet.payload)

                    if cotp_base_packet.tpdu_type == 0xf0:
                        logger.debug('Received known COTP TPDU: {0}. ({1})'.format(cotp_base_packet.tpdu_type,
                                                                                   session.id))

                        # will throw exception if the packet does not contain the S7 magic number (0x32)
                        S7_packet = S7().parse(cotp_base_packet.trailer)
                        logger.debug('Received S7 packet: magic:{0} pdu_type:{1} reserved:{2} req_id:{3} param_len:{4} '
                                     'data_len:{5} result_inf:{6}'.format(
                            S7_packet.magic, S7_packet.pdu_type,
                            S7_packet.reserved, S7_packet.request_id,
                            S7_packet.param_length, S7_packet.data_length,
                            S7_packet.result_info, session.id))

                        # request pdu
                        if S7_packet.pdu_type == 1:

                            # 0xf0 == Request for connect / pdu negotiate
                            if S7_packet.param == 0xf0:

                                # create S7 response packet
                                s7_resp_negotiate_packet = S7(3, 0, S7_packet.request_id, 0,
                                                              S7_packet.parameters).pack()
                                # wrap s7 the packet in cotp
                                cotp_resp_negotiate_packet = COTP_BASE_packet(0xf0, 0x80,
                                                                              s7_resp_negotiate_packet).pack()
                                # wrap the cotp packet
                                tpkt_resp_packet = TPKT(3, cotp_resp_negotiate_packet).pack()
                                sock.send(tpkt_resp_packet)

                                session.add_event({'request': data.encode('hex'), 'response': tpkt_resp_packet.encode('hex')})

                                # handshake done, give some more data.
                                data = sock.recv(1024)

                                while data:
                                    tpkt_packet = TPKT().parse(data)
                                    cotp_base_packet = COTP_BASE_packet().parse(tpkt_packet.payload)

                                    if cotp_base_packet.tpdu_type == 0xf0:
                                        S7_packet = S7().parse(cotp_base_packet.trailer)
                                        logger.debug('Received S7 packet: magic:{0} pdu_type:{1} reserved:{2} '
                                                     'req_id:{3} param_len:{4} data_len:{5} result_inf:{6}'.format(
                                            S7_packet.magic, S7_packet.pdu_type,
                                            S7_packet.reserved, S7_packet.request_id,
                                            S7_packet.param_length, S7_packet.data_length,
                                            S7_packet.result_info, session.id))

                                        response_param, response_data = S7_packet.handle()
                                        s7_resp_ssl_packet = S7(7, 0, S7_packet.request_id, 0, response_param,
                                                                response_data).pack()
                                        cotp_resp_ssl_packet = COTP_BASE_packet(0xf0, 0x80, s7_resp_ssl_packet).pack()
                                        tpkt_resp_packet = TPKT(3, cotp_resp_ssl_packet).pack()
                                        sock.send(tpkt_resp_packet)

                                        session.add_event({'request': data.encode('hex'), 'response': tpkt_resp_packet.encode('hex')})

                                    data = sock.recv(1024)
                    else:
                        logger.debug(
                            'Received unknown COTP TPDU after handshake: {0}'.format(cotp_base_packet.tpdu_type))
                else:
                    logger.debug('Received unknown COTP TPDU before handshake: {0}'.format(cotp_base_packet.tpdu_type))

        except socket.timeout:
            logger.debug('Socket timeout, remote: {0}. ({1})'.format(address[0], session.id))

    def get_server(self, host, port):
        connection = (host, port)
        server = StreamServer(connection, self.handle)
        logger.info('S7Comm server started on: {0}'.format(connection))
        return server

########NEW FILE########
__FILENAME__ = tpkt
from struct import *
import struct

from conpot.protocols.s7comm.exceptions import ParseException


class TPKT:
    # References: rfc2126 section-4.3, rfc1006# section-6
    # Packet format:
    # +--------+--------+----------------+-----------....---------------+
    # |version |reserved| packet length  |             TPDU             |
    # +----------------------------------------------....---------------+
    # <8 bits> <8 bits> <   16 bits    > <       variable length       >

    def __init__(self, version=3, payload=''):
        self.payload = payload
        self.version = version
        self.reserved = 0
        self.packet_length = len(payload) + 4

    def pack(self):

        return pack('!BBH', self.version, self.reserved, self.packet_length) + str(self.payload)

    def parse(self, packet):

        try:
            # try to extract the header by pattern to find malformed header data
            header = unpack('!BBH', packet[:4])
        except struct.error:
            raise ParseException('s7comm', 'malformed packet header structure')

        # extract header data and payload
        self.version = header[0]
        self.reserved = header[1]
        self.packet_length = header[2]
        self.payload = packet[4:4 + header[2]]

        return self

########NEW FILE########
__FILENAME__ = build_pysnmp_mib_wrapper
# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from gevent import subprocess
import logging
import os
import re


logger = logging.getLogger(__name__)

BUILD_SCRIPT = 'build-pysnmp-mib'

# dict of lists, where the list contain the dependency names for the given dict key
mib_dependency_map = {}
compiled_mibs = []
# key = mib name, value = full path to the file
file_map = {}


def mib2pysnmp(mib_file):
    """
    Wraps the 'build-pysnmp-mib' script.
    :param mib_file: Path to the MIB file.
    :return: A string representation of the compiled MIB file (string).
    """
    logger.debug('Compiling mib file: {0}'.format(mib_file))
    try:
        proc = subprocess.Popen([BUILD_SCRIPT, mib_file], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return_code = proc.returncode
    # subprocess throws OSError if the file to be executed is not found.
    except OSError:
        logger.critical('The script ({0}) used for building MIB files could not be found. Please ensure that you have '
                        'pysnmp installed.'.format(BUILD_SCRIPT))
        raise Exception('{0} could not be found in path.'.format(BUILD_SCRIPT))

    # if smidump is missing the build script will return 0 instead of failing hence the second check.
    if return_code != 0 or 'Autogenerated from smidump' not in stdout:
        logger.critical('Error while parsing processing MIB file using {0}. STDERR: {1}, STDOUT: {2}'
                        .format(BUILD_SCRIPT, stderr, stdout))
        raise Exception(stderr)
    else:
        logger.debug('Successfully compiled MIB file: {0}'.format(mib_file))
        return stdout


def _get_files(raw_mibs_dir, recursive):
    for dir_path, dirs, files in os.walk(raw_mibs_dir, followlinks=True):
        for file_name in files:
            yield os.path.join(dir_path, file_name)
        if not recursive:
            break


def generate_dependencies(data, mib_name):
    """
    Parses a MIB for dependencies and populates an internal dependency map.
    :param data: A string representing an entire MIB file (string).
    :param mib_name: Name of the MIB (string).
    """
    if mib_name not in mib_dependency_map:
        mib_dependency_map[mib_name] = []
    imports_section_search = re.search('IMPORTS(?P<imports_section>.*?);', data, re.DOTALL)
    if imports_section_search:
        imports_section = imports_section_search.group('imports_section')
        for dependency in re.finditer('FROM (?P<mib_name>[\w-]+)', imports_section):
            dependency_name = dependency.group('mib_name')
            if dependency_name not in mib_dependency_map:
                mib_dependency_map[dependency_name] = []
            mib_dependency_map[mib_name].append(dependency_name)


def find_mibs(raw_mibs_dirs, recursive=True):
    """
    Scans for MIB files and populates an internal MIB->path mapping.
    :param raw_mibs_dirs: Directories to search for MIB files (list of strings).
    :param recursive:  If True raw_mibs_dirs will be scanned recursively.
    :return: A list of found MIB names (list of strings).
    """
    files_scanned = 0
    for raw_mibs_dir in raw_mibs_dirs:
        for _file in _get_files(raw_mibs_dir, recursive):
            files_scanned += 1
            # making sure we don't start parsing some epic file
            if os.path.getsize(_file) > '1048576':
                continue
            data = open(_file).read()
            # 2048 - just like a rock star.
            mib_search = re.search('(?P<mib_name>[\w-]+) DEFINITIONS ::= BEGIN', data[0:2048], re.IGNORECASE)
            if mib_search:
                mib_name = mib_search.group('mib_name')
                file_map[mib_name] = _file
                generate_dependencies(data, mib_name)
    logging.debug('Done scanning for mib files, recursive scan was initiated from {0} directories and found {1} '
                  'MIB files of {2} scanned files.'
                  .format(len(raw_mibs_dirs), len(file_map), files_scanned))
    return file_map.keys()


def compile_mib(mib_name, output_dir):
    """
    Compiles the given mib_name if it is found in the internal MIB file map. If the MIB depends on other MIBs,
    these will get compiled automatically.
    :param mib_name: Name of mib to compile (string).
    :param output_dir: Output directory (string).
    """
    # resolve dependencies recursively
    for dependency in mib_dependency_map[mib_name]:
        if dependency not in compiled_mibs and dependency in file_map:
            compile_mib(dependency, output_dir)
    _compile_mib(mib_name, output_dir)


def _compile_mib(mib_name, output_dir):
    pysnmp_str_obj = mib2pysnmp(file_map[mib_name])
    output_filename = os.path.basename(os.path.splitext(mib_name)[0]) + '.py'
    with open(os.path.join(output_dir, output_filename), 'w') as output:
        output.write(pysnmp_str_obj)
        compiled_mibs.append(mib_name)

########NEW FILE########
__FILENAME__ = command_responder
# Command Responder (GET/GETNEXT)
# Based on examples from http://pysnmp.sourceforge.net/

import logging

from pysnmp.entity import config
from pysnmp.entity.rfc3413 import context
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.entity import engine
from pysnmp.smi import builder
import gevent
from gevent import socket

from conpot.protocols.snmp import conpot_cmdrsp
from conpot.protocols.snmp.databus_mediator import DatabusMediator
from gevent.server import DatagramServer

logger = logging.getLogger(__name__)


class SNMPDispatcher(DatagramServer):
    def __init__(self):
        self.__timerResolution = 0.5

    def registerRecvCbFun(self, recvCbFun, recvId=None):
        self.recvCbFun = recvCbFun

    def handle(self, msg, address):
        self.recvCbFun(self, self.transportDomain, address, msg)

    def registerTransport(self, tDomain, transport):
        DatagramServer.__init__(self, transport, self.handle)
        self.transportDomain = tDomain

    def registerTimerCbFun(self, timerCbFun, tickInterval=None):
        pass

    def sendMessage(self, outgoingMessage, transportDomain, transportAddress):
        self.socket.sendto(outgoingMessage, transportAddress)

    def getTimerResolution(self):
        return self.__timerResolution


class CommandResponder(object):
    def __init__(self, host, port, mibpaths):

        self.oid_mapping = {}
        self.databus_mediator = DatabusMediator(self.oid_mapping)
        # mapping between OID and databus keys

        # Create SNMP engine
        self.snmpEngine = engine.SnmpEngine()

        # path to custom mibs
        mibBuilder = self.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder
        mibSources = mibBuilder.getMibSources()

        for mibpath in mibpaths:
            mibSources += (builder.DirMibSource(mibpath),)
        mibBuilder.setMibSources(*mibSources)

        # Transport setup
        udp_sock = gevent.socket.socket(gevent.socket.AF_INET, gevent.socket.SOCK_DGRAM)
        udp_sock.setsockopt(gevent.socket.SOL_SOCKET, gevent.socket.SO_BROADCAST, 1)
        udp_sock.bind((host, port))
        self.server_port = udp_sock.getsockname()[1]
        # UDP over IPv4
        self.addSocketTransport(
            self.snmpEngine,
            udp.domainName,
            udp_sock
        )

        # SNMPv1
        config.addV1System(self.snmpEngine, 'public-read', 'public')

        # SNMPv3/USM setup
        # user: usr-md5-des, auth: MD5, priv DES
        config.addV3User(
            self.snmpEngine, 'usr-md5-des',
            config.usmHMACMD5AuthProtocol, 'authkey1',
            config.usmDESPrivProtocol, 'privkey1'
        )
        # user: usr-sha-none, auth: SHA, priv NONE
        config.addV3User(
            self.snmpEngine, 'usr-sha-none',
            config.usmHMACSHAAuthProtocol, 'authkey1'
        )
        # user: usr-sha-aes128, auth: SHA, priv AES/128
        config.addV3User(
            self.snmpEngine, 'usr-sha-aes128',
            config.usmHMACSHAAuthProtocol, 'authkey1',
            config.usmAesCfb128Protocol, 'privkey1'
        )

        # Allow full MIB access for each user at VACM
        config.addVacmUser(self.snmpEngine, 1, 'public-read', 'noAuthNoPriv',
                           readSubTree=(1, 3, 6, 1, 2, 1), writeSubTree=(1, 3, 6, 1, 2, 1))
        config.addVacmUser(self.snmpEngine, 3, 'usr-md5-des', 'authPriv',
                           readSubTree=(1, 3, 6, 1, 2, 1), writeSubTree=(1, 3, 6, 1, 2, 1))
        config.addVacmUser(self.snmpEngine, 3, 'usr-sha-none', 'authNoPriv',
                           readSubTree=(1, 3, 6, 1, 2, 1), writeSubTree=(1, 3, 6, 1, 2, 1))
        config.addVacmUser(self.snmpEngine, 3, 'usr-sha-aes128', 'authPriv',
                           readSubTree=(1, 3, 6, 1, 2, 1), writeSubTree=(1, 3, 6, 1, 2, 1))

        # Get default SNMP context this SNMP engine serves
        snmpContext = context.SnmpContext(self.snmpEngine)

        # Register SNMP Applications at the SNMP engine for particular SNMP context
        self.resp_app_get = conpot_cmdrsp.c_GetCommandResponder(self.snmpEngine, snmpContext, self.databus_mediator)
        self.resp_app_set = conpot_cmdrsp.c_SetCommandResponder(self.snmpEngine, snmpContext, self.databus_mediator)
        self.resp_app_next = conpot_cmdrsp.c_NextCommandResponder(self.snmpEngine, snmpContext, self.databus_mediator)
        self.resp_app_bulk = conpot_cmdrsp.c_BulkCommandResponder(self.snmpEngine, snmpContext, self.databus_mediator)

    def addSocketTransport(self, snmpEngine, transportDomain, transport):
        """Add transport object to socket dispatcher of snmpEngine"""
        if not snmpEngine.transportDispatcher:
            snmpEngine.registerTransportDispatcher(SNMPDispatcher())
        snmpEngine.transportDispatcher.registerTransport(transportDomain, transport)

    def register(self, mibname, symbolname, instance, value, profile_map_name):
        """Register OID"""
        self.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder.loadModules(mibname)
        s = self._get_mibSymbol(mibname, symbolname)

        if s:
            self.oid_mapping[s.name+instance] = profile_map_name

            MibScalarInstance, = self.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder.importSymbols('SNMPv2-SMI',
                                                                                                            'MibScalarInstance')
            x = MibScalarInstance(s.name, instance, s.syntax.clone(value))
            self.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder.exportSymbols(mibname, x)

            logger.debug('Registered: OID {0} Instance {1} ASN.1 ({2} @ {3}) value {4} dynrsp.'.format(s.name, instance, s.label, mibname, value))

        else:
            logger.debug('Skipped: OID for symbol {0} not found in MIB {1}'.format(symbolname, mibname))

    def _get_mibSymbol(self, mibname, symbolname):
        modules = self.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder.mibSymbols
        if mibname in modules:
            if symbolname in modules[mibname]:
                return modules[mibname][symbolname]

    def has_mib(self, mibname):
        modules = self.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder.mibSymbols
        return mibname in modules

    def serve_forever(self):
        self.snmpEngine.transportDispatcher.serve_forever()

    def stop(self):
        self.snmpEngine.transportDispatcher.stop_accepting()


if __name__ == "__main__":
    server = CommandResponder()
    print 'Starting echo server on port 161'
    server.serve_forever()

########NEW FILE########
__FILENAME__ = conpot_cmdrsp
import sys
import logging
import random
from datetime import datetime

from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.proto import error
from pysnmp.proto.api import v2c
import pysnmp.smi.error
from pysnmp import debug
import gevent
import conpot.core as conpot_core

logger = logging.getLogger(__name__)


class conpot_extension(object):
    def _getStateInfo(self, snmpEngine, stateReference):
        for k, v in snmpEngine.messageProcessingSubsystems.items():
            if stateReference in v._cache.__dict__['_Cache__stateReferenceIndex']:
                state_dict = v._cache.__dict__['_Cache__stateReferenceIndex'][stateReference][0]

        addr = state_dict['transportAddress']

        # msgVersion 0/1 to SNMPv1/2, msgversion 3 corresponds to SNMPv3
        if state_dict['msgVersion'] < 3:
            snmp_version = state_dict['msgVersion'] + 1
        else:
            snmp_version = state_dict['msgVersion']

        return addr, snmp_version

    def log(self, version, msg_type, addr, req_varBinds, res_varBinds=None):
        session = conpot_core.get_session('snmp', addr[0], addr[1])
        req_oid = req_varBinds[0][0]
        req_val = req_varBinds[0][1]
        log_dict = {'remote': addr,
                    'timestamp': datetime.utcnow(),
                    'data_type': 'snmp',
                    'data': {0: {'request': 'SNMPv{0} {1}: {2} {3}'.format(version, msg_type, req_oid, req_val)}}}

        logger.info('SNMPv{0} {1} request from {2}: {3} {4}'.format(version, msg_type, addr, req_oid, req_val))

        if res_varBinds:
            res_oid = ".".join(map(str, res_varBinds[0][0]))
            res_val = res_varBinds[0][1]
            logger.info('SNMPv{0} response to {1}: {2} {3}'.format(version, addr, res_oid, res_val))
            log_dict['data'][0]['response'] = 'SNMPv{0} response: {1} {2}'.format(version, res_oid, res_val)
        # log here...

    def do_tarpit(self, delay):

        # sleeps the thread for $delay ( should be either 1 float to apply a static period of time to sleep,
        # or 2 floats seperated by semicolon to sleep a randomized period of time determined by ( rand[x;y] )

        lbound, _, ubound = delay.partition(";")

        if not lbound or lbound is None:
            # no lower boundary found. Assume zero latency
            pass
        elif not ubound or ubound is None:
            # no upper boundary found. Assume static latency
            gevent.sleep(float(lbound))
        else:
            # both boundaries found. Assume random latency between lbound and ubound
            gevent.sleep(random.uniform(float(lbound), float(ubound)))

    def check_evasive(self, state, threshold, addr, cmd):

        # checks if current states are > thresholds and returns True if the request
        # is considered to be a DoS request.

        state_individual, state_overall = state
        threshold_individual, _, threshold_overall = threshold.partition(';')

        if int(threshold_individual) > 0:
            if int(state_individual) > int(threshold_individual):
                logger.warning('SNMPv{0}: DoS threshold for {1} exceeded ({2}/{3}).'.format(cmd,
                                                                                            addr,
                                                                                            state_individual,
                                                                                            threshold_individual))
                # DoS threshold exceeded.
                return True

        if int(threshold_overall) > 0:
            if int(state_overall) > int(threshold_overall):
                logger.warning('SNMPv{0}: DDoS threshold exceeded ({1}/{2}).'.format(cmd,
                                                                                     state_individual,
                                                                                     threshold_overall))
                # DDoS threshold exceeded
                return True

        # This request will be answered
        return False


class c_GetCommandResponder(cmdrsp.GetCommandResponder, conpot_extension):
    def __init__(self, snmpEngine, snmpContext, databus_mediator):
        self.databus_mediator = databus_mediator
        self.tarpit = '0;0'
        self.threshold = '0;0'

        cmdrsp.GetCommandResponder.__init__(self, snmpEngine, snmpContext)
        conpot_extension.__init__(self)

    def handleMgmtOperation(
            self, snmpEngine, stateReference, contextName, PDU, acInfo):
        (acFun, acCtx) = acInfo
        # rfc1905: 4.2.1.1
        mgmtFun = self.snmpContext.getMibInstrum(contextName).readVars

        varBinds = v2c.apiPDU.getVarBinds(PDU)
        addr, snmp_version = self._getStateInfo(snmpEngine, stateReference)

        evasion_state = self.databus_mediator.update_evasion_table(addr)
        if self.check_evasive(evasion_state, self.threshold, addr, str(snmp_version)+' Get'):
            return None

        rspVarBinds = None
        try:
            # generate response
            rspVarBinds = mgmtFun(v2c.apiPDU.getVarBinds(PDU), (acFun, acCtx))

            # determine the correct response class and update the dynamic value table
            reference_class = rspVarBinds[0][1].__class__.__name__
            reference_value = rspVarBinds[0][1]

            response = self.databus_mediator.get_response(reference_class, tuple(rspVarBinds[0][0]))
            if response:
                rspModBinds = [(tuple(rspVarBinds[0][0]), response)]
                rspVarBinds = rspModBinds
        
        finally:
            self.log(snmp_version, 'Get', addr, varBinds, rspVarBinds)

        # apply tarpit delay
        if self.tarpit is not 0:
            self.do_tarpit(self.tarpit)

        # send response
        self.sendRsp(snmpEngine, stateReference, 0, 0, rspVarBinds)
        self.releaseStateInformation(stateReference)


class c_NextCommandResponder(cmdrsp.NextCommandResponder, conpot_extension):
    def __init__(self, snmpEngine, snmpContext, databus_mediator):
        self.databus_mediator = databus_mediator
        self.tarpit = '0;0'
        self.threshold = '0;0'

        cmdrsp.NextCommandResponder.__init__(self, snmpEngine, snmpContext)
        conpot_extension.__init__(self)

    def handleMgmtOperation(self, snmpEngine, stateReference, contextName, PDU, acInfo):
        (acFun, acCtx) = acInfo
        # rfc1905: 4.2.2.1

        mgmtFun = self.snmpContext.getMibInstrum(contextName).readNextVars
        varBinds = v2c.apiPDU.getVarBinds(PDU)

        addr, snmp_version = self._getStateInfo(snmpEngine, stateReference)

        evasion_state = self.databus_mediator.update_evasion_table(addr)
        if self.check_evasive(evasion_state, self.threshold, addr, str(snmp_version)+' GetNext'):
            return None

        rspVarBinds = None
        try:
            while 1:
                rspVarBinds = mgmtFun(varBinds, (acFun, acCtx))

                # determine the correct response class and update the dynamic value table
                reference_class = rspVarBinds[0][1].__class__.__name__
                reference_value = rspVarBinds[0][1]

                response = self.databus_mediator.get_response(reference_class, tuple(rspVarBinds[0][0]))
                if response:
                    rspModBinds = [(tuple(rspVarBinds[0][0]), response)]
                    rspVarBinds = rspModBinds

                # apply tarpit delay
                if self.tarpit is not 0:
                    self.do_tarpit(self.tarpit)

                # send response
                try:
                    self.sendRsp(snmpEngine, stateReference, 0, 0, rspVarBinds)
                except error.StatusInformation:
                    idx = sys.exc_info()[1]['idx']
                    varBinds[idx] = (rspVarBinds[idx][0], varBinds[idx][1])
                else:
                    break

        finally:
            self.log(snmp_version, 'GetNext', addr, varBinds, rspVarBinds)

        self.releaseStateInformation(stateReference)


class c_BulkCommandResponder(cmdrsp.BulkCommandResponder, conpot_extension):
    def __init__(self, snmpEngine, snmpContext, databus_mediator):
        self.databus_mediator = databus_mediator
        self.tarpit = '0;0'
        self.threshold = '0;0'

        cmdrsp.BulkCommandResponder.__init__(self, snmpEngine, snmpContext)
        conpot_extension.__init__(self)

    def handleMgmtOperation(self, snmpEngine, stateReference, contextName, PDU, acInfo):
        (acFun, acCtx) = acInfo
        nonRepeaters = v2c.apiBulkPDU.getNonRepeaters(PDU)
        if nonRepeaters < 0:
            nonRepeaters = 0
        maxRepetitions = v2c.apiBulkPDU.getMaxRepetitions(PDU)
        if maxRepetitions < 0:
            maxRepetitions = 0

        reqVarBinds = v2c.apiPDU.getVarBinds(PDU)
        addr, snmp_version = self._getStateInfo(snmpEngine, stateReference)

        evasion_state = self.databus_mediator.update_evasion_table(addr)
        if self.check_evasive(evasion_state, self.threshold, addr, str(snmp_version)+' Bulk'):
            return None
        raise Exception('This class is not converted to new architecture')
        try:
            N = min(int(nonRepeaters), len(reqVarBinds))
            M = int(maxRepetitions)
            R = max(len(reqVarBinds) - N, 0)

            if R: M = min(M, self.maxVarBinds / R)

            debug.logger & debug.flagApp and debug.logger('handleMgmtOperation: N %d, M %d, R %d' % (N, M, R))

            mgmtFun = self.snmpContext.getMibInstrum(contextName).readNextVars

            if N:
                rspVarBinds = mgmtFun(reqVarBinds[:N], (acFun, acCtx))
            else:
                rspVarBinds = []

            varBinds = reqVarBinds[-R:]
            while M and R:
                rspVarBinds.extend(
                    mgmtFun(varBinds, (acFun, acCtx))
                )
                varBinds = rspVarBinds[-R:]
                M = M - 1
        finally:
            self.log(snmp_version, 'Bulk', addr, varBinds, rspVarBinds)

        # apply tarpit delay
        if self.tarpit is not 0:
            self.do_tarpit(self.tarpit)

        # send response
        if len(rspVarBinds):
            self.sendRsp(snmpEngine, stateReference, 0, 0, rspVarBinds)
            self.releaseStateInformation(stateReference)
        else:
            raise pysnmp.smi.error.SmiError()

class c_SetCommandResponder(cmdrsp.SetCommandResponder, conpot_extension):
    def __init__(self, snmpEngine, snmpContext, databus_mediator):
        self.databus_mediator = databus_mediator
        self.tarpit = '0;0'
        self.threshold = '0;0'

        conpot_extension.__init__(self)
        cmdrsp.SetCommandResponder.__init__(self, snmpEngine, snmpContext)

    def handleMgmtOperation(self, snmpEngine, stateReference, contextName, PDU, acInfo):
        (acFun, acCtx) = acInfo

        mgmtFun = self.snmpContext.getMibInstrum(contextName).writeVars

        varBinds = v2c.apiPDU.getVarBinds(PDU)
        addr, snmp_version = self._getStateInfo(snmpEngine, stateReference)

        evasion_state = self.databus_mediator.update_evasion_table(addr)
        if self.check_evasive(evasion_state, self.threshold, addr, str(snmp_version)+' Set'):
            return None

        # rfc1905: 4.2.5.1-13
        rspVarBinds = None

        # apply tarpit delay
        if self.tarpit is not 0:
            self.do_tarpit(self.tarpit)

        try:
            rspVarBinds = mgmtFun(v2c.apiPDU.getVarBinds(PDU), (acFun, acCtx))

            # generate response
            self.sendRsp(snmpEngine, stateReference, 0, 0, rspVarBinds)
            self.releaseStateInformation(stateReference)

            oid = tuple(rspVarBinds[0][0])
            self.databus_mediator.set_value(oid, rspVarBinds[0][1])

        except (pysnmp.smi.error.NoSuchObjectError,
                pysnmp.smi.error.NoSuchInstanceError):
            e = pysnmp.smi.error.NotWritableError()
            e.update(sys.exc_info()[1])
            raise e
        finally:
            self.log(snmp_version, 'Set', addr, varBinds, rspVarBinds)

########NEW FILE########
__FILENAME__ = databus_mediator
# Copyright (C) 2013  Daniel creo Haslinger <creo-conpot@blackmesa.at>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# this class mediates between the SNMP attack surface and conpots databus
# furthermore it keeps request statistics iot evade being used as a DOS
# reflection tool
  
from pysnmp.smi import builder
from datetime import datetime
import conpot.core as conpot_core


class DatabusMediator(object):
    def __init__(self, oid_mappings):
        """ initiate variables """

        self.evasion_table = {}             # stores the number of requests
        self.start_time = datetime.now()
        self.oid_map = oid_mappings         # mapping between OIDs and databus keys
        self.databus = conpot_core.get_databus()

    def get_response(self, reference_class, OID):
        if OID in self.oid_map:
            if reference_class == 'DisplayString':
                (response_class,) = builder.MibBuilder().importSymbols("SNMPv2-TC", "DisplayString")

            elif reference_class == 'OctetString':
                (response_class,) = builder.MibBuilder().importSymbols("ASN1", "OctetString")

            elif reference_class == 'Integer32':
                (response_class,) = builder.MibBuilder().importSymbols("SNMPv2-SMI", "Integer32")

            elif reference_class == 'Counter32':
                (response_class,) = builder.MibBuilder().importSymbols("SNMPv2-SMI", "Counter32")

            elif reference_class == 'Gauge32':
                (response_class,) = builder.MibBuilder().importSymbols("SNMPv2-SMI", "Gauge32")

            elif reference_class == 'TimeTicks':
                (response_class,) = builder.MibBuilder().importSymbols("SNMPv2-SMI", "TimeTicks")
            # TODO: All mode classes - or autodetect'ish?
            else:
                # dynamic responses are not supported for this class (yet)
                return False
            response_value = self.databus.get_value(self.oid_map[OID])
            return response_class(response_value)
        else:
            return None

    def set_value(self, OID, value):
        # TODO: Access control. The profile shold indicate which OIDs are writable
        self.databus.set_value(self.oid_map[OID], value)

    def update_evasion_table(self, client_ip):
        """ updates dynamic evasion table """

        # get current minute as epoch..
        now = datetime.now()
        epoch_minute = int((datetime(now.year, now.month, now.day, now.hour, now.minute) -
                          datetime(1970, 1, 1)).total_seconds())

        # if this is a new minute, re-initialize the evasion table
        if epoch_minute not in self.evasion_table:
            self.evasion_table.clear()                              # purge previous entries
            self.evasion_table[epoch_minute] = {}                   # create current minute
            self.evasion_table[epoch_minute]['overall'] = 0         # prepare overall request count

        # if this is a new client, add him to the evasion table
        if client_ip[0] not in self.evasion_table[epoch_minute]:
            self.evasion_table[epoch_minute][client_ip[0]] = 0

        # increment number of requests..
        self.evasion_table[epoch_minute][client_ip[0]] += 1
        self.evasion_table[epoch_minute]['overall'] += 1

        current_numreq = self.evasion_table[epoch_minute][client_ip[0]]
        overall_numreq = self.evasion_table[epoch_minute]['overall']

        # return numreq(per_ip) and numreq(overall)
        return current_numreq, overall_numreq

########NEW FILE########
__FILENAME__ = snmp_server
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging
import tempfile
import shutil

from lxml import etree

from conpot.protocols.snmp.command_responder import CommandResponder
from conpot.protocols.snmp.build_pysnmp_mib_wrapper import find_mibs, compile_mib
import conpot.core as conpot_core


logger = logging.getLogger()


class SNMPServer(object):
    def __init__(self, host, port, template, mibpaths, rawmibs_dirs):
        """
        :param host:        hostname or ip address on which to server the snmp service (string).
        :param port:        listen port (integer).
        :param template:    path to conpot xml configuration file (string).
        :param log_queue:   shared log queue (list).
        :param mibpaths:    collection of paths to search for COMPILED mib files (iterable collection of strings).
        :param rawmibs_dir: collection of paths to search for raw mib files, these files will get compiled by conpot (string).
        """
        self.host = host
        self.port = port

        dom = etree.parse(template)

        self.cmd_responder = CommandResponder(self.host, self.port, mibpaths)
        self.xml_general_config(dom)
        self.xml_mib_config(dom, mibpaths, rawmibs_dirs)

    def xml_general_config(self, dom):
        snmp_config = dom.xpath('//conpot_template/protocols/snmp/config/*')
        if snmp_config:
            for entity in snmp_config:

                # TARPIT: individual response delays
                if entity.attrib['name'].lower() == 'tarpit':

                    if entity.attrib['command'].lower() == 'get':
                        self.cmd_responder.resp_app_get.tarpit = self.config_sanitize_tarpit(entity.text)
                    elif entity.attrib['command'].lower() == 'set':
                        self.cmd_responder.resp_app_set.tarpit = self.config_sanitize_tarpit(entity.text)
                    elif entity.attrib['command'].lower() == 'next':
                        self.cmd_responder.resp_app_next.tarpit = self.config_sanitize_tarpit(entity.text)
                    elif entity.attrib['command'].lower() == 'bulk':
                        self.cmd_responder.resp_app_bulk.tarpit = self.config_sanitize_tarpit(entity.text)

                # EVASION: response thresholds
                if entity.attrib['name'].lower() == 'evasion':

                    if entity.attrib['command'].lower() == 'get':
                        self.cmd_responder.resp_app_get.threshold = self.config_sanitize_threshold(entity.text)
                    elif entity.attrib['command'].lower() == 'set':
                        self.cmd_responder.resp_app_set.threshold = self.config_sanitize_threshold(entity.text)
                    elif entity.attrib['command'].lower() == 'next':
                        self.cmd_responder.resp_app_next.threshold = self.config_sanitize_threshold(entity.text)
                    elif entity.attrib['command'].lower() == 'bulk':
                        self.cmd_responder.resp_app_bulk.threshold = self.config_sanitize_threshold(entity.text)

    def xml_mib_config(self, dom, mibpaths, rawmibs_dirs):
        try:
            mibs = dom.xpath('//conpot_template/protocols/snmp/mibs/*')
            tmp_mib_dir = tempfile.mkdtemp()
            mibpaths.append(tmp_mib_dir)
            available_mibs = find_mibs(rawmibs_dirs)

            databus = conpot_core.get_databus()
            # parse mibs and oid tables
            for mib in mibs:
                mib_name = mib.attrib['name']
                # compile the mib file if it is found and not already loaded.
                if mib_name in available_mibs and not self.cmd_responder.has_mib(mib_name):
                    compile_mib(mib_name, tmp_mib_dir)
                for symbol in mib:
                    symbol_name = symbol.attrib['name']

                    # retrieve instance from template
                    if 'instance' in symbol.attrib:
                        # convert instance to (int-)tuple
                        symbol_instance = symbol.attrib['instance'].split('.')
                        symbol_instance = tuple(map(int, symbol_instance))
                    else:
                        # use default instance (0)
                        symbol_instance = (0,)


                    # retrieve value from databus
                    value = databus.get_value(symbol.xpath('./value/text()')[0])
                    profile_map_name = symbol.xpath('./value/text()')[0]

                    # register this MIB instance to the command responder
                    self.cmd_responder.register(mib_name,
                                                symbol_name,
                                                symbol_instance,
                                                value,
                                                profile_map_name)
        finally:
            # cleanup compiled mib files
            shutil.rmtree(tmp_mib_dir)

    def config_sanitize_tarpit(self, value):

        # checks tarpit value for being either a single int or float,
        # or a series of two concatenated integers and/or floats separated by semicolon and returns
        # either the (sanitized) value or zero.

        if value is not None:

            x, _, y = value.partition(';')

            try:
                _ = float(x)
            except ValueError:
                logger.error("Invalid tarpit value: '{0}'. Assuming no latency.".format(value))
                # first value is invalid, ignore the whole setting.
                return '0;0'

            try:
                _ = float(y)
                # both values are fine.
                return value
            except ValueError:
                # second value is invalid, use the first one.
                return x

        else:
            return '0;0'

    def config_sanitize_threshold(self, value):

        # checks DoS thresholds for being either a single int or a series of two concatenated integers
        # separated by semicolon and returns either the (sanitized) value or zero.

        if value is not None:

            x, _, y = value.partition(';')

            try:
                _ = int(x)
            except ValueError:
                logger.error("Invalid evasion threshold: '{0}'. Assuming no DoS evasion.".format(value))
                # first value is invalid, ignore the whole setting.
                return '0;0'

            try:
                _ = int(y)
                # both values are fine.
                return value
            except ValueError:
                # second value is invalid, use the first and ignore the second.
                return str(x) + ';0'

        else:
            return '0;0'

    def start(self):
        if self.cmd_responder:
            logger.info('SNMP server started on: {0}'.format((self.host, self.get_port())))
            self.cmd_responder.serve_forever()

    def stop(self):
        if self.cmd_responder:
            self.cmd_responder.stop()

    def get_port(self):
        if self.cmd_responder:
            return self.cmd_responder.server_port
        else:
            return None

########NEW FILE########
__FILENAME__ = mitre_stix_validator
# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# See LICENSE.txt for complete terms.

import os
import re
from collections import defaultdict
from StringIO import StringIO
from lxml import etree
from lxml import isoschematron
import xlrd

class XmlValidator(object):
    NS_XML_SCHEMA_INSTANCE = "http://www.w3.org/2001/XMLSchema-instance"
    NS_XML_SCHEMA = "http://www.w3.org/2001/XMLSchema"
    
    def __init__(self, schema_dir=None, use_schemaloc=False):
        self.__imports = self._build_imports(schema_dir)
        self.__use_schemaloc = use_schemaloc
    
    def _get_target_ns(self, fp):
        '''Returns the target namespace for a schema file
        
        Keyword Arguments
        fp - the path to the schema file
        '''
        tree = etree.parse(fp)
        root = tree.getroot()
        return root.attrib['targetNamespace'] # throw an error if it doesn't exist...we can't validate
        
    def _get_include_base_schema(self, list_schemas):
        '''Returns the root schema which defines a namespace.
        
        Certain schemas, such as OASIS CIQ use xs:include statements in their schemas, where two schemas
        define a namespace (e.g., XAL.xsd and XAL-types.xsd). This makes validation difficult, when we
        must refer to one schema for a given namespace.
        
        To fix this, we attempt to find the root schema which includes the others. We do this by seeing
        if a schema has an xs:include element, and if it does we assume that it is the parent. This is
        totally wrong and needs to be fixed. Ideally this would build a tree of includes and return the
        root node.
        
        Keyword Arguments:
        list_schemas - a list of schema file paths that all belong to the same namespace
        '''
        parent_schema = None
        tag_include = "{%s}include" % (self.NS_XML_SCHEMA)
        
        for fn in list_schemas:
            tree = etree.parse(fn)
            root = tree.getroot()
            includes = root.findall(tag_include)
            
            if len(includes) > 0: # this is a hack that assumes if the schema includes others, it is the base schema for the namespace
                return fn
                
        return parent_schema
    
    def _build_imports(self, schema_dir):
        '''Given a directory of schemas, this builds a dictionary of schemas that need to be imported
        under a wrapper schema in order to enable validation. This returns a dictionary of the form
        {namespace : path to schema}.
        
        Keyword Arguments
        schema_dir - a directory of schema files
        '''
        if not schema_dir:
            return None
        
        imports = defaultdict(list)
        for top, dirs, files in os.walk(schema_dir):
            for f in files:
                if f.endswith('.xsd'):
                    fp = os.path.join(top, f)
                    target_ns = self._get_target_ns(fp)
                    imports[target_ns].append(fp)
        
        for k,v in imports.iteritems():
            if len(v) > 1:
                base_schema = self._get_include_base_schema(v)
                imports[k] = base_schema
            else:
                imports[k] = v[0]
    
        return imports
    
    def _build_wrapper_schema(self, import_dict):
        '''Creates a wrapper schema that imports all namespaces defined by the input dictionary. This enables
        validation of instance documents that refer to multiple namespaces and schemas
        
        Keyword Arguments
        import_dict - a dictionary of the form {namespace : path to schema} that will be used to build the list of xs:import statements
        '''
        schema_txt = '''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://stix.mitre.org/tools/validator" elementFormDefault="qualified" attributeFormDefault="qualified"/>'''
        root = etree.fromstring(schema_txt)
        
        tag_import = "{%s}import" % (self.NS_XML_SCHEMA)
        for ns, list_schemaloc in import_dict.iteritems():
            schemaloc = list_schemaloc
            schemaloc = schemaloc.replace("\\", "/")
            attrib = {'namespace' : ns, 'schemaLocation' : schemaloc}
            el_import = etree.Element(tag_import, attrib=attrib)
            root.append(el_import)
    
        return root

    def _extract_schema_locations(self, root):
        schemaloc_dict = {}
        
        tag_schemaloc = "{%s}schemaLocation" % (self.NS_XML_SCHEMA_INSTANCE)
        schemaloc = root.attrib[tag_schemaloc].split()
        schemaloc_pairs = zip(schemaloc[::2], schemaloc[1::2])
        
        for ns, loc in schemaloc_pairs:
            schemaloc_dict[ns] = loc
        
        return schemaloc_dict
    
    def _build_result_dict(self, result, errors=None):
        d = {}
        d['result'] = result
        if errors: 
            if not hasattr(errors, "__iter__"):
                errors = [errors]
            d['errors'] = errors
        return d
    
    def validate(self, instance_doc):
        '''Validates an instance documents.
        
        Returns a tuple of where the first item is the boolean validation
        result and the second is the validation error if there was one.
        
        Keyword Arguments
        instance_doc - a filename, file-like object, etree._Element, or etree._ElementTree to be validated
        '''
        if not(self.__use_schemaloc or self.__imports):
            return (False, "No schemas to validate against! Try instantiating XmlValidator with use_schemaloc=True or setting the schema_dir")
        
        if isinstance(instance_doc, etree._Element):
            instance_root = instance_doc
        elif isinstance(instance_doc, etree._ElementTree):
            instance_root = instance_doc.getroot()
        else:
            try:
                et = etree.parse(instance_doc)
                instance_root = et.getroot()
            except etree.XMLSyntaxError as e:
                return self._build_result_dict(False, str(e))
            
        if self.__use_schemaloc:
            try:
                required_imports = self._extract_schema_locations(instance_root)
            except KeyError as e:
                return (False, "No schemaLocation attribute set on instance document. Unable to validate")
        else:
            required_imports = {}
            for prefix, ns in instance_root.nsmap.iteritems():
                schemaloc = self.__imports.get(ns)
                if schemaloc:
                    required_imports[ns] = schemaloc

        if not required_imports:
            return (False, "Unable to determine schemas to validate against")

        wrapper_schema_doc = self._build_wrapper_schema(import_dict=required_imports)
        xmlschema = etree.XMLSchema(wrapper_schema_doc)
        
        isvalid = xmlschema.validate(instance_root)
        if isvalid:
            return self._build_result_dict(True)
        else:
            return self._build_result_dict(False, [str(x) for x in xmlschema.error_log])
            

class STIXValidator(XmlValidator):
    '''Schema validates STIX v1.1 documents and checks best practice guidance'''
    __stix_version__ = "1.1"
    
    PREFIX_STIX_CORE = 'stix'
    PREFIX_CYBOX_CORE = 'cybox'
    PREFIX_STIX_INDICATOR = 'indicator'
    
    NS_STIX_CORE = "http://stix.mitre.org/stix-1"
    NS_STIX_INDICATOR = "http://stix.mitre.org/Indicator-2"
    NS_CYBOX_CORE = "http://cybox.mitre.org/cybox-2"
    
    NS_MAP = {PREFIX_CYBOX_CORE : NS_CYBOX_CORE,
              PREFIX_STIX_CORE : NS_STIX_CORE,
              PREFIX_STIX_INDICATOR : NS_STIX_INDICATOR}
    
    def __init__(self, schema_dir=None, use_schemaloc=False, best_practices=False):
        super(STIXValidator, self).__init__(schema_dir, use_schemaloc)
        self.best_practices = best_practices
        
    def _check_id_presence_and_format(self, instance_doc):
        '''Checks that the core STIX/CybOX constructs in the STIX instance document
        have ids and that each id is formatted as [ns_prefix]:[object-type]-[GUID].
        
        Returns a dictionary of lists. Each dictionary has the following keys:
        no_id - a list of etree Element objects for all nodes without ids
        format - a list of etree Element objects with ids not formatted as [ns_prefix]:[object-type]-[GUID]
    
        Keyword Arguments
        instance_doc - an etree Element object for a STIX instance document
        '''
        return_dict = {'no_id' : [],
                       'format' : []}
        
        elements_to_check = ['stix:Campaign',
                             'stix:Course_Of_Action',
                             'stix:Exploit_Target',
                             'stix:Incident',
                             'stix:Indicator',
                             'stix:STIX_Package',
                             'stix:Threat_Actor',
                             'stix:TTP',
                             'cybox:Observable',
                             'cybox:Object',
                             'cybox:Event',
                             'cybox:Action']
    
        for tag in elements_to_check:
            xpath = ".//%s" % (tag)
            elements = instance_doc.xpath(xpath, namespaces=self.NS_MAP)
            
            for e in elements:
                try:
                    if not re.match(r'\w+:\w+-', e.attrib['id']): # not the best regex
                        return_dict['format'].append({'tag':e.tag, 'id':e.attrib['id'], 'line_number':e.sourceline})
                except KeyError as ex:
                    return_dict['no_id'].append({'tag':e.tag, 'line_number':e.sourceline})
            
        return return_dict
    
    def _check_duplicate_ids(self, instance_doc):
        '''Looks for duplicate ids in a STIX instance document. 
        
        Returns a dictionary of lists. Each dictionary uses the offending
        id as a key, which points to a list of etree Element nodes which
        use that id.
        
        Keyword Arguments
        instance_doc - an etree.Element object for a STIX instance document
        '''
        dict_id_nodes = defaultdict(list)
        dup_dict = {}
        xpath_all_nodes_with_ids = "//*[@id]"
        
        all_nodes_with_ids = instance_doc.xpath(xpath_all_nodes_with_ids)
        for node in all_nodes_with_ids:
            dict_id_nodes[node.attrib['id']].append(node)
        
        for id,node_list in dict_id_nodes.iteritems():
            if len(node_list) > 1:
                dup_dict[id] = [{'tag':node.tag, 'line_number':node.sourceline} for node in node_list]
        
        return dup_dict
    
    def _check_idref_resolution(self, instance_doc):
        '''Checks that all idref attributes in the input document resolve to a local element.
        Returns a list etree.Element nodes with unresolveable idrefs.
        
        Keyword Arguments
        instance_doc - an etree.Element object for a STIX instance document
        '''
        list_unresolved_ids = []
        xpath_all_idrefs = "//*[@idref]"
        xpath_all_ids = "//@id"
        
        all_idrefs = instance_doc.xpath(xpath_all_idrefs)
        all_ids = instance_doc.xpath(xpath_all_ids)
        
        for node in all_idrefs:
            if node.attrib['idref'] not in all_ids:
                d = {'tag': node.tag,
                     'idref': node.attrib['idref'],
                     'line_number' : node.sourceline}
                list_unresolved_ids.append(d)
                
        return list_unresolved_ids
                
    def _check_idref_with_content(self, instance_doc):
        '''Looks for elements that have an idref attribute set, but also have content.
        Returns a list of etree.Element nodes.
        
        Keyword Arguments:
        instance_doc - an etree.Element object for a STIX instance document
        '''
        list_nodes = []
        xpath = "//*[@idref]"
        nodes = instance_doc.xpath(xpath)
        
        for node in nodes:
            if node.text or len(node) > 0:
                d = {'tag' : node.tag,
                     'idref' : node.attrib['idref'],
                     'line_number' : node.sourceline}
                list_nodes.append(node)
                
        return list_nodes
    
    def _check_indicator_practices(self, instance_doc):
        '''Looks for STIX Indicators that are missing a Title, Description, Type, Valid_Time_Position, 
        Indicated_TTP, and/or Confidence
        
        Returns a list of dictionaries. Each dictionary has the following keys:
        id - the id of the indicator
        node - the etree.Element object for the indicator
        missing - a list of constructs missing from the indicator
        
        Keyword Arguments
        instance_doc - etree Element for a STIX sinstance document
        '''
        list_indicators = []
        xpath = "//%s:Indicator | %s:Indicator" % (self.PREFIX_STIX_CORE, self.PREFIX_STIX_INDICATOR)
        
        nodes = instance_doc.xpath(xpath, namespaces=self.NS_MAP)
        for node in nodes:
            dict_indicator = defaultdict(list)
            if not node.attrib.get('idref'): # if this is not an idref node, look at its content
                if node.find('{%s}Title' % (self.NS_STIX_INDICATOR)) is None:
                    dict_indicator['missing'].append('Title')
                if node.find('{%s}Description' % (self.NS_STIX_INDICATOR)) is None:
                    dict_indicator['missing'].append('Description')
                if node.find('{%s}Type' % (self.NS_STIX_INDICATOR)) is None:
                    dict_indicator['missing'].append('Type')
                if node.find('{%s}Valid_Time_Position' % (self.NS_STIX_INDICATOR)) is None:
                    dict_indicator['missing'].append('Valid_Time_Position')
                if node.find('{%s}Indicated_TTP' % (self.NS_STIX_INDICATOR)) is None:
                    dict_indicator['missing'].append('TTP')
                if node.find('{%s}Confidence' % (self.NS_STIX_INDICATOR)) is None:
                    dict_indicator['missing'].append('Confidence')
                
                if dict_indicator:
                    dict_indicator['id'] = node.attrib.get('id')
                    dict_indicator['line_number'] = node.sourceline
                    list_indicators.append(dict_indicator)
                
        return list_indicators
 
    def _check_root_element(self, instance_doc):
        d = {}
        if instance_doc.tag != "{%s}STIX_Package" % (self.NS_STIX_CORE):
            d['tag'] = instance_doc.tag
            d['line_number'] = instance_doc.sourceline
        return d
            
 
    def check_best_practices(self, instance_doc):
        '''Checks that a STIX instance document is following best practice guidance.
        
        Looks for the following:
        + idrefs that do not resolve locally
        + elements with duplicate ids
        + elements without ids
        + elements with ids not formatted as [ns_prefix]:[object-type]-[GUID]
        + indicators missing a Title, Description, Type, Valid_Time_Position, Indicated_TTP, and/or Confidence
        
        Returns a dictionary of lists and other dictionaries. This is maybe not ideal but workable.
        
        Keyword Arguments
        instance_doc - a filename, file-like object, etree._Element or etree.ElementTree for a STIX instance document
        '''
        
        if isinstance(instance_doc, etree._Element):
            root = instance_doc
        elif isinstance(instance_doc, etree._ElementTree):
            root = instance_doc.getroot()
        elif isinstance(instance_doc, basestring):
            tree = etree.parse(instance_doc)
            root = tree.getroot()
        else:
            instance_doc.seek(0)
            tree = etree.parse(instance_doc)
            root = tree.getroot()
        
        root_element = self._check_root_element(root)
        list_unresolved_idrefs = self._check_idref_resolution(root)
        dict_duplicate_ids = self._check_duplicate_ids(root)
        dict_presence_and_format = self._check_id_presence_and_format(root)
        list_idref_with_content = self._check_idref_with_content(root)
        list_indicators = self._check_indicator_practices(root)
        
        d = {}
        if root_element:
            d['root_element'] = root_element
        if list_unresolved_idrefs:
            d['unresolved_idrefs'] = list_unresolved_idrefs
        if dict_duplicate_ids:
            d['duplicate_ids'] = dict_duplicate_ids
        if dict_presence_and_format:
            if dict_presence_and_format.get('no_id'):
                d['missing_ids'] = dict_presence_and_format['no_id']
            if dict_presence_and_format.get('format'):
                d['id_format'] = dict_presence_and_format['format']
        if list_idref_with_content:
            d['idref_with_content'] = list_idref_with_content
        if list_indicators:
            d['indicator_suggestions'] = list_indicators
        
        return d
    
    def validate(self, instance_doc):
        '''Validates a STIX document and checks best practice guidance if STIXValidator
        was initialized with best_practices=True.
        
        Best practices will not be checked if the document is schema-invalid.
        
        Keyword Arguments
        instance_doc - a filename, file-like object, etree._Element or etree.ElementTree for a STIX instance document
        '''
        result_dict = super(STIXValidator, self).validate(instance_doc)
        
        isvalid = result_dict['result']
        if self.best_practices and isvalid:
            best_practice_warnings = self.check_best_practices(instance_doc)
        else:
            best_practice_warnings = None
        
        if best_practice_warnings:
            result_dict['best_practice_warnings'] = best_practice_warnings
             
        return result_dict

class SchematronValidator(object):
    NS_SVRL = "http://purl.oclc.org/dsdl/svrl"
    NS_SCHEMATRON = "http://purl.oclc.org/dsdl/schematron"
    NS_SAXON = "http://icl.com/saxon" # libxml2 requires this namespace instead of http://saxon.sf.net/
    NS_SAXON_SF_NET = "http://saxon.sf.net/"
    
    def __init__(self, schematron=None):
        self.schematron = None # isoschematron.Schematron instance
        self._init_schematron(schematron)
        
    def _init_schematron(self, schematron):
        '''Returns an instance of lxml.isoschematron.Schematron'''
        if schematron is None:
            self.schematron = None
            return
        elif not (isinstance(schematron, etree._Element) or isinstance(schematron, etree._ElementTree)):
            tree = etree.parse(schematron)
        else:
            tree = schematron
            
        self.schematron = isoschematron.Schematron(tree, store_report=True, store_xslt=True, store_schematron=True)
        
    def get_xslt(self):
        if not self.schematron:
            return None
        return self.schematron.validator_xslt
      
    def get_schematron(self):
        if not self.schematron:
            return None 
        return self.schematron.schematron
    
    def _build_result_dict(self, result, report=None):
        '''Creates a dictionary to be returned by the validate() method.'''
        d = {}
        d['result'] = result
        if report:
                d['report'] = report
        return d
    
    def _get_schematron_errors(self, validation_report):
        '''Returns a list of SVRL failed-assert and successful-report elements.'''
        xpath = "//svrl:failed-assert | //svrl:successful-report"
        errors = validation_report.xpath(xpath, namespaces={'svrl':self.NS_SVRL})
        return errors
    
    def _get_error_line_numbers(self, d_error, tree):
        '''Returns a sorted list of line numbers for a given Schematron error.'''
        locations = d_error['locations']
        nsmap = d_error['nsmap']
        
        line_numbers = []
        for location in locations:
            ctx_node = tree.xpath(location, namespaces=nsmap)[0]
            if ctx_node.sourceline not in line_numbers: 
                line_numbers.append(ctx_node.sourceline)
        
        line_numbers.sort()
        return line_numbers
    
    def _build_error_dict(self, errors, instance_tree, report_line_numbers=True):
        '''Returns a dictionary representation of the SVRL validation report:
        d0 = { <Schemtron error message> : d1 }
        
        d1 = { "locations" : A list of XPaths to context nodes,
               "line_numbers" : A list of line numbers where the error occurred,
               "test" : The Schematron evaluation expression used,
               "text" : The Schematron error message }
        
        '''
        d_errors = {}
        
        for error in errors:
            text = error.find("{%s}text" % self.NS_SVRL).text
            location = error.attrib.get('location')
            test = error.attrib.get('test') 
            if text in d_errors:
                d_errors[text]['locations'].append(location)
            else:
                d_errors[text] = {'locations':[location], 'test':test, 'nsmap':error.nsmap, 'text':text}
        
        if report_line_numbers:
            for d_error in d_errors.itervalues():
                line_numbers = self._get_error_line_numbers(d_error, instance_tree)
                d_error['line_numbers'] = line_numbers
        
        return d_errors
    
    def _build_error_report_dict(self, validation_report, instance_tree, report_line_numbers=True): 
        errors = self._get_schematron_errors(validation_report)
        d_errors = self._build_error_dict(errors, instance_tree, report_line_numbers)
        report_dict = defaultdict(list)
        for msg, d in d_errors.iteritems():
            d_error = {'error' : msg}
            if 'line_numbers' in d:
                d_error['line_numbers'] = d['line_numbers']
            report_dict['errors'].append(d_error)
            
        return report_dict
    
    def validate(self, instance, report_line_numbers=True):
        '''Validates an XML instance document.
        
        Arguments:
        report_line_numbers : Includes error line numbers in the returned dictionary.
                              This may slow performance.
                              
        '''
        if not self.schematron:
            raise Exception('Schematron document not set. Cannot validate. Call init_schematron(...) and retry.')
        try:
            if isinstance(instance, etree._Element):
                tree = etree.ElementTree(instance)
            elif isinstance(instance, etree._ElementTree):
                tree = instance
            else:
                tree = etree.parse(instance)
            
            result = self.schematron.validate(tree)
            report = self._build_error_report_dict(self.schematron.validation_report, tree, report_line_numbers)

            if len(report['errors']) > 0:
                report = self._build_error_report_dict(self.schematron.validation_report, tree, report_line_numbers)
                return self._build_result_dict(result, report)
            else:
                return self._build_result_dict(result)
            
        except etree.ParseError as e:
            return self._build_result_dict(False, [str(e)])    

class ProfileValidator(SchematronValidator):
    NS_STIX = "http://stix.mitre.org/stix-1"
    
    def __init__(self, profile_fn):
        '''Initializes an instance of ProfileValidator.'''
        profile = self._open_profile(profile_fn)
        schema = self._parse_profile(profile)
        super(ProfileValidator, self).__init__(schematron=schema)
    
    def _build_rule_dict(self, worksheet):
        '''Builds a dictionary representation of the rules defined by a STIX profile document.'''
        d = defaultdict(list)
        for i in xrange(1, worksheet.nrows):
            if not any(self._get_cell_value(worksheet, i, x) for x in xrange(0, worksheet.ncols)): # empty row
                continue
            if not self._get_cell_value(worksheet, i, 1): # assume this is a label row
                context = self._get_cell_value(worksheet, i, 0)
                continue

            field = self._get_cell_value(worksheet, i, 0)
            occurrence = self._get_cell_value(worksheet, i, 1).lower()
            xsi_types = self._get_cell_value(worksheet, i, 3)
            allowed_values = self._get_cell_value(worksheet, i, 4)
            
            list_xsi_types = [x.strip() for x in xsi_types.split(',')] if xsi_types else []
            list_allowed_values = [x.strip() for x in allowed_values.split(',')] if allowed_values else []
            
            
            if occurrence in ('required', 'prohibited') or len(list_xsi_types) > 0 or len(list_allowed_values) > 0: # ignore rows with no rules
                d[context].append({'field' : field,
                                   'occurrence' : occurrence,
                                   'xsi_types' : list_xsi_types,
                                   'allowed_values' : list_allowed_values})
        return d
    
    def _add_root_test(self, pattern, nsmap):
        '''Adds a root-level test that requires the root element of a STIX
        document be a STIX_Package'''
        ns_stix = "http://stix.mitre.org/stix-1"
        rule_element = self._add_element(pattern, "rule", context="/")
        text = "The root element must be a STIX_Package instance"
        test = "%s:STIX_Package" % nsmap.get(ns_stix, 'stix')
        element = etree.XML('''<assert xmlns="%s" test="%s" role="error">%s [<value-of select="saxon:line-number()"/>]</assert> ''' % (self.NS_SCHEMATRON, test, text))
        rule_element.append(element)

    def _add_required_test(self, rule_element, entity_name, context):
        '''Adds a test to the rule element checking for the presence of a required STIX field.'''
        entity_path = "%s/%s" % (context, entity_name)
        text = "%s is required by this profile" % (entity_path)
        test = entity_name
        element = etree.XML('''<assert xmlns="%s" test="%s" role="error">%s [<value-of select="saxon:line-number()"/>]</assert> ''' % (self.NS_SCHEMATRON, test, text))
        rule_element.append(element)
    
    def _add_prohibited_test(self, rule_element, entity_name, context):
        '''Adds a test to the rule element checking for the presence of a prohibited STIX field.'''
        entity_path = "%s/%s" % (context, entity_name) if entity_name.startswith("@") else context
        text = "%s is prohibited by this profile" % (entity_path)
        test_field = entity_name if entity_name.startswith("@") else "true()"
        element = etree.XML('''<report xmlns="%s" test="%s" role="error">%s [<value-of select="saxon:line-number()"/>]</report> ''' % (self.NS_SCHEMATRON, test_field, text))
        rule_element.append(element)
    
    def _add_allowed_xsi_types_test(self, rule_element, context, entity_name, allowed_xsi_types):
        '''Adds a test to the rule element which corresponds to values found in the Allowed Implementations
        column of a STIX profile document.'''
        entity_path = "%s/%s" % (context, entity_name)
                
        if allowed_xsi_types:
            test = " or ".join("@xsi:type='%s'" % (x) for x in allowed_xsi_types)
            text = 'The allowed xsi:types for %s are %s' % (entity_path, allowed_xsi_types)
            element = etree.XML('''<assert xmlns="%s" test="%s" role="error">%s [<value-of select="saxon:line-number()"/>]</assert> ''' % (self.NS_SCHEMATRON, test, text))
            rule_element.append(element)
    
    def _add_allowed_values_test(self, rule_element, context, entity_name, allowed_values):
        '''Adds a test to the rule element corresponding to values found in the Allowed Values
        column of a STIX profile document.
        
        '''
        entity_path = "%s/%s" % (context, entity_name)
        text = "The allowed values for %s are %s" % (entity_path, allowed_values)
        
        if entity_name.startswith('@'):
            test = " or ".join("%s='%s'" % (entity_name, x) for x in allowed_values)
        else:
            test = " or ".join(".='%s'" % (x) for x in allowed_values)
        
        element = etree.XML('''<assert xmlns="%s" test="%s" role="error">%s [<value-of select="saxon:line-number()"/>]</assert> ''' % (self.NS_SCHEMATRON, test, text))
        rule_element.append(element)
    
    def _create_rule_element(self, context):
        '''Returns an etree._Element representation of a Schematron rule element.'''
        rule = etree.Element("{%s}rule" % self.NS_SCHEMATRON)
        rule.set('context', context)
        return rule
    
    def _add_rules(self, pattern_element, selectors, field_ns, tests):
        '''Adds all Schematron rules and tests to the overarching Schematron
        <pattern> element. Each rule and test corresponds to entries found
        in the STIX profile document.
        
        '''
        d_rules = {} # context : rule_element
        for selector in selectors:
            for d_test in tests:
                field = d_test['field']
                occurrence = d_test['occurrence']
                allowed_values = d_test['allowed_values']
                allowed_xsi_types = d_test['xsi_types']
                
                if field.startswith("@"):
                    entity_name = field
                else:
                    entity_name = "%s:%s" % (field_ns, field)
                
                if occurrence == "required":
                    ctx = selector
                    rule = d_rules.setdefault(ctx, self._create_rule_element(ctx))
                    self._add_required_test(rule, entity_name, ctx)
                elif occurrence == "prohibited":
                    if entity_name.startswith("@"):
                        ctx = selector
                    else:
                        ctx = "%s/%s" % (selector, entity_name)
                    
                    rule = d_rules.setdefault(ctx, self._create_rule_element(ctx))
                    self._add_prohibited_test(rule, entity_name, ctx)
                
                if allowed_values or allowed_xsi_types:
                    if entity_name.startswith('@'):
                        ctx = selector
                    else:
                        ctx = "%s/%s" % (selector, entity_name)
                        
                    rule = d_rules.setdefault(ctx, self._create_rule_element(ctx))
                    if allowed_values:
                        self._add_allowed_values_test(rule, selector, entity_name, allowed_values)
                    if allowed_xsi_types:
                        self._add_allowed_xsi_types_test(rule, selector, entity_name, allowed_xsi_types)
        
        for rule in d_rules.itervalues():            
            pattern_element.append(rule)
    
    def _build_schematron_xml(self, rules, nsmap, instance_map):
        '''Returns an etree._Element instance representation of the STIX profile'''
        root = etree.Element("{%s}schema" % self.NS_SCHEMATRON, nsmap={None:self.NS_SCHEMATRON})
        pattern = self._add_element(root, "pattern", id="STIX_Schematron_Profile")
        self._add_root_test(pattern, nsmap) # check the root element of the document
        
        for label, tests in rules.iteritems():
            d_instances = instance_map[label]
            selectors = d_instances['selectors']
            field_ns_alias = d_instances['ns_alias']
            self._add_rules(pattern, selectors, field_ns_alias, tests)
        
        self._map_ns(root, nsmap) # add namespaces to the schematron document
        return root
    
    def _parse_namespace_worksheet(self, worksheet):
        '''Parses the Namespaces worksheet of the profile. Returns a dictionary representation:
        
        d = { <namespace> : <namespace alias> }
        
        By default, entries for http://stix.mitre.org/stix-1 and http://icl.com/saxon are added.
        
        '''
        nsmap = {self.NS_STIX : 'stix',
                 self.NS_SAXON : 'saxon'}
        for i in xrange(1, worksheet.nrows): # skip the first row
            if not any(self._get_cell_value(worksheet, i, x) for x in xrange(0, worksheet.ncols)): # empty row
                continue
            
            ns = self._get_cell_value(worksheet, i, 0)
            alias = self._get_cell_value(worksheet, i, 1)

            if not (ns or alias):
                raise Exception("Missing namespace or alias: unable to parse Namespaces worksheet")
            
            nsmap[ns] = alias
        return nsmap      
    
    def _parse_instance_mapping_worksheet(self, worksheet, nsmap):
        '''Parses the supplied Instance Mapping worksheet and returns a dictionary representation.
        
        d0  = { <STIX type label> : d1 }
        d1  = { 'selectors' : XPath selectors to instances of the XML datatype',
                'ns' : The namespace where the STIX type is defined,
                'ns_alias' : The namespace alias associated with the namespace }
                
        '''
        instance_map = {}
        for i in xrange(1, worksheet.nrows):
            if not any(self._get_cell_value(worksheet, i, x) for x in xrange(0, worksheet.ncols)): # empty row
                continue
            
            label = self._get_cell_value(worksheet, i, 0)
            selectors = [x.strip() for x in self._get_cell_value(worksheet, i, 1).split(",")]
            ns = self._get_cell_value(worksheet, i, 2)
            ns_alias = nsmap[ns]
            
            if not (label or selectors or ns):
                raise Exception("Missing label, instance selector and/or namespace for %s in Instance Mapping worksheet" % label)
            
            instance_map[label] = {'selectors':selectors, 'ns':ns, 'ns_alias':ns_alias}
        return instance_map
    
    def _parse_profile(self, profile):
        '''Converts the supplied STIX profile into a Schematron representation. The
        Schematron schema is returned as a etree._Element instance.
        
        '''
        overview_ws = profile.sheet_by_name("Overview")
        namespace_ws = profile.sheet_by_name("Namespaces")
        instance_mapping_ws = profile.sheet_by_name("Instance Mapping")
                
        all_rules = defaultdict(list)
        for worksheet in profile.sheets():
            if worksheet.name not in ("Overview", "Namespaces", "Instance Mapping"):
                rules = self._build_rule_dict(worksheet)
                for context,d in rules.iteritems():
                    all_rules[context].extend(d)

        namespaces = self._parse_namespace_worksheet(namespace_ws)
        instance_mapping = self._parse_instance_mapping_worksheet(instance_mapping_ws, namespaces)
        schema = self._build_schematron_xml(all_rules, namespaces, instance_mapping)
        
        self._unload_workbook(profile)
        return schema
            
    def _map_ns(self, schematron, nsmap):
        '''Adds <ns> nodes to the supplied schematron document for each entry
        supplied by the nsmap.
        
        '''
        for ns, prefix in nsmap.iteritems():
            ns_element = etree.Element("{%s}ns" % self.NS_SCHEMATRON)
            ns_element.set("prefix", prefix)
            ns_element.set("uri", ns)
            schematron.insert(0, ns_element)
            
    def _add_element(self, node, name, text=None, **kwargs):
        '''Adds an etree._Element child to the supplied node. The child node is returned'''
        child = etree.SubElement(node, "{%s}%s" % (self.NS_SCHEMATRON, name))
        if text:
            child.text = text
        for k,v in kwargs.iteritems():
            child.set(k, v)
        return child
    
    def _unload_workbook(self, workbook):
        '''Unloads the xlrd workbook.'''
        for worksheet in workbook.sheets():
            workbook.unload_sheet(worksheet.name)
            
    def _get_cell_value(self, worksheet, row, col):
        '''Returns the worksheet cell value found at (row,col).'''
        if not worksheet:
            raise Exception("worksheet value was NoneType")
        value = str(worksheet.cell_value(row, col))
        return value
    
    def _convert_to_string(self, value):
        '''Returns the str(value) or an 8-bit string version of value encoded as UTF-8.'''
        if isinstance(value, unicode):
            return value.encode("UTF-8")
        else:
            return str(value)
    
    def _open_profile(self, filename):
        '''Returns xlrd.open_workbook(filename) or raises an Exception if the
        filename extension is not .xlsx or the open_workbook() call fails.
        
        '''
        if not filename.lower().endswith(".xlsx"):
            raise Exception("File must have .XLSX extension. Filename provided: %s" % filename)
        try:
            return xlrd.open_workbook(filename)
        except:
            raise Exception("File does not seem to be valid XLSX.")
    
    def validate(self, instance_doc):
        '''Validates an XML instance document against a STIX profile.'''
        return super(ProfileValidator, self).validate(instance_doc, report_line_numbers=False)
    
    def _build_error_dict(self, errors, instance_doc, report_line_numbers=False):
        '''Overrides SchematronValidator._build_error_dict(...).
        
        Returns a dictionary representation of the SVRL validation report:
        d0 = { <Schemtron error message> : d1 }
        
        d1 = { "locations" : A list of XPaths to context nodes,
               "line_numbers" : A list of line numbers where the error occurred,
               "test" : The Schematron evaluation expression used,
               "text" : The Schematron error message }
        
        '''
        d_errors = {}
        for error in errors:
            text = error.find("{%s}text" % self.NS_SVRL).text
            location = error.attrib.get('location')
            test = error.attrib.get('test')
             
            line_number = text.split(" ")[-1][1:-1]
            text = text[:text.rfind(' [')]
             
            if text in d_errors:
                d_errors[text]['locations'].append(location)
                d_errors[text]['line_numbers'].append(line_number)
            else:
                d_errors[text] = {'locations':[location], 'test':test, 'nsmap':error.nsmap, 'text':text, 'line_numbers':[line_number]}
        return d_errors
    
    def get_xslt(self):
        '''Overrides SchematronValidator.get_xslt()
        
        Returns an lxml.etree._ElementTree representation of the ISO Schematron skeleton generated
        XSLT translation of a STIX profile.
        
        The ProfileValidator uses the extension function saxon:line-number() for reporting line numbers.
        This function is stripped along with any references to the Saxon namespace from the exported
        XSLT. This is due to compatibility issues between Schematron/XSLT processing libraries. For
        example, SaxonPE/EE expects the Saxon namespace to be "http://saxon.sf.net/" while libxslt 
        expects it to be "http://icl.com/saxon". The freely distributed SaxonHE library does not support 
        Saxon extension functions at all.
        
        '''
        if not self.schematron:
            return None
        
        s = etree.tostring(self.schematron.validator_xslt)
        s = s.replace(' [<axsl:text/><axsl:value-of select="saxon:line-number()"/><axsl:text/>]', '')
        s = s.replace('xmlns:saxon="http://icl.com/saxon"', '')
        s = s.replace('<svrl:ns-prefix-in-attribute-values uri="http://icl.com/saxon" prefix="saxon"/>', '')
        return etree.ElementTree(etree.fromstring(s))
      
    def get_schematron(self):
        '''Overrides SchematronValidator.get_schematron()
        
        Returns an lxml.etree._ElementTree representation of the ISO Schematron translation of a STIX profile.
        
        The ProfileValidator uses the extension function saxon:line-number() for reporting line numbers.
        This function is stripped along with any references to the Saxon namespace from the exported
        XSLT. This is due to compatibility issues between Schematron/XSLT processing libraries. For
        example, SaxonPE/EE expects the Saxon namespace to be "http://saxon.sf.net/" while libxslt 
        expects it to be "http://icl.com/saxon". The freely distributed SaxonHE library does not support 
        Saxon extension functions at all.
        
        '''
        if not self.schematron:
            return None
        
        s = etree.tostring(self.schematron.schematron)
        s = s.replace(' [<value-of select="saxon:line-number()"/>]', '')
        s = s.replace('<ns prefix="saxon" uri="http://icl.com/saxon"/>', '')
        return etree.ElementTree(etree.fromstring(s))
########NEW FILE########
__FILENAME__ = s7comm_client
# Copyright (C) 2013  Daniel creo Haslinger <creo-conpot@blackmesa.at>
# Derived from plcscan by Dmitry Efanov (Positive Research)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from struct import *
from optparse import OptionGroup

import struct
import socket
import string

__FILTER = "".join([' '] + [' ' if chr(x) not in string.printable or chr(x) in string.whitespace else chr(x) for x in range(1, 256)])
def StripUnprintable(msg):
    return msg.translate(__FILTER)


class TPKTPacket:
    """ TPKT packet. RFC 1006
    """
    def __init__(self, data=''):
        self.data = str(data)

    def pack(self):
        return pack('!BBH',
                    3,                  # version
                    0,                  # reserved
                    len(self.data)+4    # packet size
                    ) + str(self.data)

    def unpack(self, packet):
        try:
            header = unpack('!BBH', packet[:4])
        except struct.error:
            raise S7ProtocolError("Unknown TPKT format")

        self.data = packet[4:4+header[2]]
        return self


class COTPConnectionPacket:
    """ COTP Connection Request or Connection Confirm packet (ISO on TCP). RFC 1006
    """
    def __init__(self, dst_ref=0, src_ref=0, dst_tsap=0, src_tsap=0, tpdu_size=0):
        self.dst_ref = dst_ref
        self.src_ref = src_ref
        self.dst_tsap = dst_tsap
        self.src_tsap = src_tsap
        self.tpdu_size = tpdu_size

    def pack(self):
        """ make Connection Request Packet
        """
        return pack('!BBHHBBBHBBHBBB',
                    17,             # size
                    0xe0,           # pdu type: CR
                    self.dst_ref,
                    self.src_ref,
                    0,              # flag
                    0xc1, 2, self.src_tsap,
                    0xc2, 2, self.dst_tsap,
                    0xc0, 1, self.tpdu_size)

    def __str__(self):
        return self.pack()

    def unpack(self, packet):
        """ parse Connection Confirm Packet (header only)
        """
        try:
            size, pdu_type, self.dst_ref, self.src_ref, flags = unpack('!BBHHB', packet[:7])
        except struct.error:
            raise S7ProtocolError("Wrong CC packet format")
        if len(packet) != size + 1:
            raise S7ProtocolError("Wrong CC packet size")
        if pdu_type != 0xd0:
            raise S7ProtocolError("Not a CC packet")

        return self


class COTPDataPacket:
    """ COTP Data packet (ISO on TCP). RFC 1006
    """
    def __init__(self, data=''):
        self.data = data

    def pack(self):
        return pack('!BBB',
                    2,                      # header len
                    0xf0,                   # data packet
                    0x80) + str(self.data)

    def unpack(self, packet):
        self.data = packet[ord(packet[0])+1:]
        return self

    def __str__(self):
        return self.pack()


class S7Packet:
    """ S7 packet
    """
    def __init__(self, _type=1, req_id=0, parameters='', data=''):
        self.type = _type
        self.req_id = req_id
        self.parameters = parameters
        self.data = data
        self.error = 0

    def pack(self):
        if self.type not in [1, 7]:
            raise S7ProtocolError("Unknown pdu type")
        return (pack('!BBHHHH',
                     0x32,                   # protocol s7 magic
                     self.type,              # pdu-type
                     0,                      # reserved
                     self.req_id,            # request id
                     len(self.parameters),   # parameters length
                     len(self.data)) +       # data length
                self.parameters +
                self.data)

    def unpack(self, packet):
        try:
            if ord(packet[1]) in [3, 2]:   # pdu-type = response
                header_size = 12
                magic0x32, self.type, reserved, self.req_id, parameters_length, data_length, self.error = \
                    unpack('!BBHHHHH', packet[:header_size])
                if self.error:
                    raise S7Error(self.error)
            elif ord(packet[1]) in [1, 7]:
                header_size = 10
                magic0x32, self.type, reserved, self.req_id, parameters_length, data_length = \
                    unpack('!BBHHHH', packet[:header_size])
            else:
                raise S7ProtocolError("Unknown pdu type (%d)" % ord(packet[1]))
        except struct.error:
            raise S7ProtocolError("Wrong S7 packet format")

        self.parameters = packet[header_size:header_size+parameters_length]
        self.data = packet[header_size+parameters_length:header_size+parameters_length+data_length]

        return self

    def __str__(self):
        return self.pack()


class S7ProtocolError(Exception):
    def __init__(self, message, packet=''):
        self.message = message
        self.packet = packet

    def __str__(self):
        return "[ERROR][S7Protocol] %s" % self.message


class S7Error(Exception):
    _errors = {
        # s7 data errors
        0x05: 'Address Error',
        0x0a: 'Item not available',
        # s7 header errors
        0x8104: 'Context not supported',
        0x8500: 'Wrong PDU size'
    }

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in S7Error._errors:
            message = S7Error._errors[self.code]
        else:
            message = 'Unknown error'
        return "[ERROR][S7][0x%x] %s" % (self.code, message)


def Split(ar, size):
    """ split sequence into blocks of given size
    """
    return [ar[i:i + size] for i in range(0, len(ar), size)]


class s7:
    def __init__(self, ip, port, src_tsap=0x200, dst_tsap=0x201, timeout=8):
        self.ip = ip
        self.port = port
        self.req_id = 0
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.dst_ref = 0
        self.src_ref = 0x04
        self.dst_tsap = dst_tsap
        self.src_tsap = src_tsap
        self.timeout = timeout

    def Connect(self):
        """ Establish ISO on TCP connection and negotiate PDU
        """
        #sleep(1)
        #self.src_ref = randint(1, 20)
        self.src_ref = 10
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(self.timeout)
        self.s.connect((self.ip, self.port))
        self.s.send(TPKTPacket(COTPConnectionPacket(self.dst_ref,
                                                    self.src_ref,
                                                    self.dst_tsap,
                                                    self.src_tsap,
                                                    0x0a)).pack())
        reply = self.s.recv(1024)
        _ = COTPConnectionPacket().unpack(TPKTPacket().unpack(reply).data)

        self.NegotiatePDU()

    def Request(self, _type, parameters='', data=''):
        """ Send s7 request and receive response
        """
        packet = TPKTPacket(COTPDataPacket(S7Packet(_type, self.req_id, parameters, data))).pack()
        self.s.send(packet)
        reply = self.s.recv(1024)
        response = S7Packet().unpack(COTPDataPacket().unpack(TPKTPacket().unpack(reply).data).data)
        if self.req_id != response.req_id:
            raise S7ProtocolError('Sequence ID not correct')
        return response

    def NegotiatePDU(self, pdu=480):
        """ Send negotiate pdu request and receive response. Reply no matter
        """
        response = self.Request(0x01, pack('!BBHHH',
                                           0xf0,       # function NegotiatePDU
                                           0x00,       # unknown
                                           0x01,       # max number of parallel jobs
                                           0x01,       # max number of parallel jobs
                                           pdu))      # pdu length

        func, unknown, pj1, pj2, pdu = unpack('!BBHHH', response.parameters)
        return pdu

    def Function(self, _type, group, function, data=''):
        parameters = pack('!LBBBB',
                          0x00011200 +            # parameter head (magic)
                          0x04,                   # parameter length
                          0x11,                   # unknown
                          _type*0x10+group,        # type, function group
                          function,               # function
                          0x00)                  # sequence

        data = pack('!BBH', 0xFF, 0x09, len(data)) + data
        response = self.Request(0x07, parameters, data)

        code, transport_size, data_len = unpack('!BBH', response.data[:4])
        if code != 0xFF:
            raise S7Error(code)
        return response.data[4:]

    def ReadSZL(self, szl_id):
        szl_data = self.Function(
            0x04,                   # request
            0x04,                   # szl-functions
            0x01,                   # read szl
            pack('!HH',
                 szl_id,             # szl id
                 1))                 # szl index

        szl_id, szl_index, element_size, element_count = unpack('!HHHH', szl_data[:8])

        return Split(szl_data[8:], element_size)


def BruteTsap(ip, port, src_tsaps=(0x100, 0x200), dst_tsaps=(0x102, 0x200, 0x201)):
    for src_tsap in src_tsaps:
        for dst_tsap in dst_tsaps:
            try:
                con = s7(ip, port)
                con.src_tsap = src_tsap
                con.dst_tsap = dst_tsap
                con.Connect()
                return src_tsap, dst_tsap

            except S7ProtocolError:
                pass

    return None


def GetIdentity(ip, port, src_tsap, dst_tsap):
    res = []

    szl_dict = {
        0x11: {
            'title': 'Module Identification',
            'indexes': {
                1: 'Module',
                6: 'Basic Hardware',
                7: 'Basic Firmware'
            },
            'packer': {
                (1, 6): lambda(packet): "{0:s} v.{2:d}.{3:d}".format(*unpack('!20sHBBH', packet)),
                (7,): lambda(packet): "{0:s} v.{3:d}.{4:d}.{5:d}".format(*unpack('!20sHBBBB', packet))
            }
        },
        0x1c: {
            'title': 'Component Identification',
            'indexes': {
                1: 'Name of the PLC',
                2: 'Name of the module',
                3: 'Plant identification',
                4: 'Copyright',
                5: 'Serial number of module',
                6: 'Reserved for operating system',
                7: 'Module type name',
                8: 'Serial number of memory card',
                9: 'Manufacturer and profile of a CPU module',
                10: 'OEM ID of a module',
                11: 'Location designation of a module'
            },
            'packer': {
                (1, 2, 5): lambda(packet): "%s" % packet[:24],
                (3, 7, 8): lambda(packet): "%s" % packet[:32],
                (4,): lambda(packet): "%s" % packet[:26]
            }
        }
    }

    con = s7(ip, port, src_tsap, dst_tsap)
    con.Connect()

    for szl_id in szl_dict.keys():
        try:
            entities = con.ReadSZL(szl_id)
        except S7Error:
            continue

        indexes = szl_dict[szl_id]['indexes']
        packers = szl_dict[szl_id]['packer']

        for item in entities:
            if len(item) > 2:
                n, = unpack('!H', item[:2])
                item = item[2:]

                try:
                    packers_keys = [i for i in packers.keys() if n in i]
                    formated_item = packers[packers_keys[0]](item).strip('\x00')
                except (struct.error, IndexError):
                    formated_item = StripUnprintable(item).strip('\x00')

                res.append("%s;%s;%s" % (szl_id, n, formated_item))

    return res


def Scan(ip, port):
    res = ()
    try:
        res = BruteTsap(ip, port)
    except socket.error as e:
        print "%s:%d %s" % (ip, port, e)

    if not res:
        print " MEH!"
        return False

    print "%s:%d S7comm (src_tsap=0x%x, dst_tsap=0x%x)" % (ip, port, res[0], res[1])

    # sometimes unexpected exceptions occur, so try to get identity several time
    identities = []
    for attempt in [0, 1]:
        try:
            identities = GetIdentity(ip, port, res[0], res[1])
            break
        except (S7ProtocolError, socket.error) as e:
            print "Attempt {0}:  {1}".format(attempt, e)

    return identities


def AddOptions(parser):
    group = OptionGroup(parser, "S7 scanner options")
    group.add_option("--src-tsap", help="Try this src-tsap (list) (default: 0x100,0x200)",
                     type="string", metavar="LIST")
    group.add_option("--dst-tsap", help="Try this dst-tsap (list) (default: 0x102,0x200,0x201)",
                     type="string", metavar="LIST")
    parser.add_option_group(group)

########NEW FILE########
__FILENAME__ = snmp_client
# Command Responder (GET/GETNEXT)
# Based on examples from http://pysnmp.sourceforge.net/

from pysnmp.entity import engine, config
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.proto import rfc1902


class SNMPClient(object):
    def __init__(self, host, port):

        # Create SNMP engine instance
        self.snmpEngine = engine.SnmpEngine()

        # user: usr-sha-aes, auth: SHA, priv AES
        config.addV3User(
            self.snmpEngine, 'usr-sha-aes128',
            config.usmHMACSHAAuthProtocol, 'authkey1',
            config.usmAesCfb128Protocol, 'privkey1'
        )
        config.addTargetParams(self.snmpEngine, 'my-creds', 'usr-sha-aes128', 'authPriv')

        # Setup transport endpoint and bind it with security settings yielding
        # a target name (choose one entry depending of the transport needed).

        # UDP/IPv4
        config.addSocketTransport(
            self.snmpEngine,
            udp.domainName,
            udp.UdpSocketTransport().openClientMode()
        )
        config.addTargetAddr(
            self.snmpEngine, 'my-router',
            udp.domainName, (host, port),
            'my-creds'
        )

    # Error/response receiver
    def cbFun(self, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx):
        if errorIndication:
            print(errorIndication)
        elif errorStatus:
            print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBindTable[-1][int(errorIndex) - 1] or '?')
            )
        else:
            for oid, val in varBindTable:
                print('%s = %s' % (oid.prettyPrint(), val.prettyPrint()))

    def get_command(self, OID=((1, 3, 6, 1, 2, 1, 1, 1, 0), None), callback=None):
        if not callback:
            callback = self.cbFun
            # Prepare and send a request message
        cmdgen.GetCommandGenerator().sendReq(
            self.snmpEngine,
            'my-router',
            (OID,),
            callback,
        )
        self.snmpEngine.transportDispatcher.runDispatcher()
        # Run I/O dispatcher which would send pending queries and process responses
        self.snmpEngine.transportDispatcher.runDispatcher()

    def set_command(self, OID, callback=None):
        if not callback:
            callback = self.cbFun
        cmdgen.SetCommandGenerator().sendReq(
            self.snmpEngine,
            'my-router',
            (OID,),
            callback,
        )
        self.snmpEngine.transportDispatcher.runDispatcher()

    def walk_command(self, OID, callback=None):
        if not callback:
            callback = self.cbFun
        cmdgen.NextCommandGenerator().sendReq(
            self.snmpEngine,
            'my-router',
            (OID,),
            callback,
        )


if __name__ == "__main__":
    snmp_client = SNMPClient('127.0.0.1', 161)
    OID = ((1, 3, 6, 1, 2, 1, 1, 1, 0), None)
    snmp_client.get_command(OID)

########NEW FILE########
__FILENAME__ = test_base
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import unittest


class TestBase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_base(self):
        return True
########NEW FILE########
__FILENAME__ = test_docs
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import unittest
import subprocess


class TestMakeDocs(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_make_docs(self):
        cmd = "make -C docs/ html"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        self.assertIn("Build finished. The HTML pages are in build/html.", output)
########NEW FILE########
__FILENAME__ = test_ext_ip_util
# Copyright (C) 2014  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import unittest
import conpot.utils.ext_ip

from gevent.wsgi import WSGIServer
import gevent
import gevent.monkey
gevent.monkey.patch_all()


class TestExtIPUtil(unittest.TestCase):

    def setUp(self):
        def application(environ, start_response):
            headers = [('Content-Type', 'text/html')]
            start_response('200 OK', headers)
            return ['127.0.0.1']

        self.server = WSGIServer(('localhost', 8000), application)
        gevent.spawn(self.server.serve_forever)

    def tearDown(self):
        self.server.stop()

    def test_ip_verify(self):
        self.assertTrue(conpot.utils.ext_ip._verify_address("127.0.0.1") is True)

    def test_ext_util(self):
        ip_address = conpot.utils.ext_ip._fetch_data(urls=["http://127.0.0.1:8000", ])
        self.assertTrue(conpot.utils.ext_ip._verify_address(ip_address) is True)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_hpfriends
# Copyright (C) 2013  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import unittest

from conpot.core.loggers.hpfriends import HPFriendsLogger


class Test_HPFriends(unittest.TestCase):

    def test_hpfriends(self):
        """
        Objective: Test if data can be published to hpfriends without errors.
        """

        host = 'hpfriends.honeycloud.net'
        port = 20000
        ident = 'HBmU08rR'
        secret = 'XDNNuMGYUuWFaWyi'
        channels = ["test.test", ]
        hpf = HPFriendsLogger(host, port, ident, secret, channels)

        error_message = hpf.log('some some test data')
        self.assertIsNone(error_message, 'Unexpected error message: {0}'.format(error_message))

########NEW FILE########
__FILENAME__ = test_http_server
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import unittest
import datetime

from lxml import etree
import gevent
import requests
import gevent.monkey
gevent.monkey.patch_all()

from conpot.protocols.http import web_server
import conpot.core as conpot_core


class TestBase(unittest.TestCase):

    def setUp(self):

        # clean up before we start...
        conpot_core.get_sessionManager().purge_sessions()

        self.http_server = web_server.HTTPServer('127.0.0.1',
                                                 0,
                                                 'conpot/templates/default.xml',
                                                 'conpot/templates/www/default/',)
        # get the assigned ephemeral port for http
        self.http_port = self.http_server.server_port
        self.http_worker = gevent.spawn(self.http_server.start)

        # initialize the databus
        self.databus = conpot_core.get_databus()
        self.databus.initialize('conpot/templates/default.xml')

    def tearDown(self):
        self.http_server.cmd_responder.httpd.shutdown()
        self.http_server.cmd_responder.httpd.server_close()

        # tidy up (again)...
        conpot_core.get_sessionManager().purge_sessions()

    def test_http_request_base(self):
        """
        Objective: Test if http service delivers data on request
        """
        ret = requests.get("http://127.0.0.1:{0}/tests/unittest_base.html".format(self.http_port))
        self.assertIn('ONLINE', ret.text, "Could not retrieve expected data from test output.")

    def test_http_backend_databus(self):
        """
        Objective: Test if http backend is able to retrieve data from databus
        """
        # retrieve configuration from xml
        dom = etree.parse('conpot/templates/default.xml')

        # retrieve reference value from configuration
        sysName = dom.xpath('//conpot_template/core/databus/key_value_mappings/key[@name="sysName"]/value')
        if sysName:
            print sysName
            assert_reference = sysName[0].xpath('./text()')[0][1:-1]
        else:
            assert_reference = None
        if assert_reference is not None:
            ret = requests.get("http://127.0.0.1:{0}/tests/unittest_databus.html".format(self.http_port))
            self.assertIn(assert_reference, ret.text,
                          "Could not find databus entity 'sysName' (value '{0}') in output.".format(assert_reference))
        else:
            raise Exception("Assertion failed. Key 'sysName' not found in databus definition table.")

    def test_http_backend_tarpit(self):
        """
        Objective: Test if http tarpit delays responses properly
        """
        # retrieve configuration from xml
        dom = etree.parse('conpot/templates/default.xml')

        # check for proper tarpit support
        tarpit = dom.xpath('//conpot_template/protocols/http/htdocs/node[@name="/tests/unittest_tarpit.html"]/tarpit')

        if tarpit:
            tarpit_delay = tarpit[0].xpath('./text()')[0]

            # requesting file via HTTP along with measuring the timedelta
            dt_req_start = datetime.datetime.now()
            requests.get("http://127.0.0.1:{0}/tests/unittest_tarpit.html".format(self.http_port))
            dt_req_delta = datetime.datetime.now() - dt_req_start

            # check if the request took at least the expected delay to be processed
            self.assertLessEqual(
                int(tarpit_delay),
                dt_req_delta.seconds,
                "Expected delay: >= {0} seconds. Actual delay: {1} seconds".format(tarpit_delay, dt_req_delta.seconds)
            )
        else:
            raise Exception("Assertion failed. Tarpit delay not found in HTTP template.")

    def test_http_subselect_trigger(self):
        """
        Objective: Test if http subselect triggers work correctly
        """
        ret = requests.get("http://127.0.0.1:{0}/tests/unittest_subselects.html?action=unit&subaction=test".format(self.http_port))
        self.assertIn('SUCCESSFUL', ret.text, "Trigger missed. An unexpected page was delivered.")
########NEW FILE########
__FILENAME__ = test_kamstrup_decoder
# Copyright (C) 2014  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import unittest

from conpot.protocols.kamstrup.decoder_382 import Decoder


class TestKamstrupDecoder(unittest.TestCase):
    # TODO: Rename functions when i figure out the actual meaning of the requests / responses
    def test_request_one(self):
        request = "803f1001041e7abb0d"
        decoder = Decoder()
        result = decoder.decode_in(bytearray.fromhex(request))
        self.assertEqual(result, 'Request for 1 register(s): 1054 (Voltage p1)')

    def test_invalid_crc(self):
        invalid_sequences = ['803f1002000155a10d', '803f1001000265cf0d']

        for seq in invalid_sequences:
            decoder = Decoder()
            result = decoder.decode_in(bytearray.fromhex(seq))
            self.assertEqual(result, 'Request discarded due to invalid CRC.',
                             'Invalid CRC {0} tested valid'.format(seq))

            # def test_request_two(self):
            #     request = "803f1001000265c20d".encode('hex-codec')
            #     decoder = Decoder()
            #     result = decoder.decode_in(request)
            #
            # def test_response_one(self):
            #     response = "403f1000010204000000008be1900d".encode('hex-codec')
            #     decoder = Decoder()
            #     result = decoder.decode_in(response)
            #
            # def test_response_two(self):
            #     response = "403f10000202040000000000091bf90d".encode('hex-codec')
            #     decoder = Decoder()
            #     result = decoder.decode_in(response)
########NEW FILE########
__FILENAME__ = test_modbus_server
# Copyright (C) 2013  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import unittest
from datetime import datetime

from gevent.queue import Queue
from gevent.server import StreamServer
from gevent import monkey
from modbus_tk.modbus import ModbusError
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp

#we need to monkey patch for modbus_tcp.TcpMaster
from conpot.protocols.modbus import modbus_server
import conpot.core as conpot_core

monkey.patch_all()


class TestBase(unittest.TestCase):
    def setUp(self):

        # clean up before we start...
        conpot_core.get_sessionManager().purge_sessions()

        self.databus = conpot_core.get_databus()
        self.databus.initialize('conpot/templates/default.xml')
        modbus = modbus_server.ModbusServer('conpot/templates/default.xml', timeout=2)
        self.modbus_server = StreamServer(('127.0.0.1', 0), modbus.handle)
        self.modbus_server.start()

    def tearDown(self):
        self.modbus_server.stop()

        # tidy up (again)...
        conpot_core.get_sessionManager().purge_sessions()

    def test_read_coils(self):
        """
        Objective: Test if we can extract the expected bits from a slave using the modbus protocol.
        """
        self.databus.set_value('memoryModbusSlave1BlockA', [1 for b in range(0, 128)])

        master = modbus_tcp.TcpMaster(host='127.0.0.1', port=self.modbus_server.server_port)
        master.set_timeout(1.0)
        actual_bits = master.execute(slave=1, function_code=cst.READ_COILS, starting_address=1, quantity_of_x=128)
        #the test template sets all bits to 1 in the range 1-128
        expected_bits = [1 for b in range(0, 128)]
        self.assertSequenceEqual(actual_bits, expected_bits)

    def test_write_read_coils(self):
        """
        Objective: Test if we can change values using the modbus protocol.
        """
        master = modbus_tcp.TcpMaster(host='127.0.0.1', port=self.modbus_server.server_port)
        master.set_timeout(1.0)
        set_bits = [1, 0, 0, 1, 0, 0, 1, 1]
        #write 8 bits
        master.execute(1, cst.WRITE_MULTIPLE_COILS, 1, output_value=set_bits)
        #read 8 bit
        actual_bit = master.execute(slave=1, function_code=cst.READ_COILS, starting_address=1, quantity_of_x=8)
        self.assertSequenceEqual(set_bits, actual_bit)

    def test_read_nonexistent_slave(self):
        """
        Objective: Test if the correct exception is raised when trying to read from nonexistent slave.
        """
        master = modbus_tcp.TcpMaster(host='127.0.0.1', port=self.modbus_server.server_port)
        master.set_timeout(1.0)
        with self.assertRaises(ModbusError) as cm:
            master.execute(slave=5, function_code=cst.READ_COILS, starting_address=1, quantity_of_x=1)

        self.assertEqual(cm.exception.get_exception_code(), cst.SLAVE_DEVICE_FAILURE)

    def test_modbus_logging(self):
        """
        Objective: Test if modbus generates log messages as expected.
        Expected output is a dictionary with the following structure:
        {'timestamp': datetime.datetime(2013, 4, 23, 18, 47, 38, 532960),
         'remote': ('127.0.0.1', 60991),
         'data_type': 'modbus',
         'id': '01bd90d6-76f4-43cb-874f-5c8f254367f5',
         'data': {'function_code': 1, 'slave_id': 1, 'request': '0100010080', 'response': '0110ffffffffffffffffffffffffffffffff'}}

        """

        self.databus.set_value('memoryModbusSlave1BlockA', [1 for b in range(0,128)])

        master = modbus_tcp.TcpMaster(host='127.0.0.1', port=self.modbus_server.server_port)
        master.set_timeout(1.0)
        #issue request to modbus server
        master.execute(slave=1, function_code=cst.READ_COILS, starting_address=1, quantity_of_x=128)

        #extract the generated logentry
        log_queue = conpot_core.get_sessionManager().log_queue
        log_item = log_queue.get(True, 2)

        self.assertIsInstance(log_item['timestamp'], datetime)
        self.assertTrue('data' in log_item)
        # we expect session_id to be 36 characters long (32 x char, 4 x dashes)
        self.assertTrue(len(str(log_item['id'])), log_item)
        self.assertEqual('127.0.0.1', log_item['remote'][0])
        self.assertEquals('modbus', log_item['data_type'])
        #testing the actual modbus data
        expected_payload = {'function_code': 1, 'slave_id': 1,'request': '000100000006010100010080',
                            'response': '0110ffffffffffffffffffffffffffffffff'}
        self.assertDictEqual(expected_payload, log_item['data'])
########NEW FILE########
__FILENAME__ = test_proxy
# Copyright (C) 2014  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import unittest
import os

import gevent
from gevent.server import StreamServer
from gevent.socket import socket
from gevent.ssl import wrap_socket

import conpot
from conpot.emulators.proxy import Proxy

gevent.monkey.patch_all()

package_directory = os.path.dirname(os.path.abspath(conpot.__file__))


class TestProxy(unittest.TestCase):
    def test_proxy(self):
        self.test_input = 'Hiya, this is a test'
        mock_service = StreamServer(('127.0.0.1', 0), self.echo_server)
        gevent.spawn(mock_service.start)
        gevent.sleep(1)

        proxy = Proxy('proxy', '127.0.0.1', mock_service.server_port)
        server = proxy.get_server('127.0.0.1', 0)
        gevent.spawn(server.start)
        gevent.sleep(1)

        s = socket()
        s.connect(('127.0.0.1', server.server_port))
        s.sendall(self.test_input)
        received = s.recv(len(self.test_input))
        self.assertEqual(self.test_input, received)
        mock_service.stop(1)

    def test_ssl_proxy(self):
        self.test_input = 'Hiya, this is a test'
        keyfile = os.path.join(package_directory, 'templates/example_ssl.key')
        certfile = os.path.join(package_directory, 'templates/example_ssl.crt')

        mock_service = StreamServer(('127.0.0.1', 0), self.echo_server, keyfile=keyfile, certfile=certfile)
        gevent.spawn(mock_service.start)
        gevent.sleep(1)

        proxy = Proxy('proxy', '127.0.0.1', mock_service.server_port, keyfile=keyfile, certfile=certfile)
        server = proxy.get_server('127.0.0.1', 0)
        gevent.spawn(server.start)
        gevent.sleep(1)

        s = wrap_socket(socket(), keyfile, certfile)
        s.connect(('127.0.0.1', server.server_port))
        s.sendall(self.test_input)
        received = s.recv(len(self.test_input))
        self.assertEqual(self.test_input, received)
        mock_service.stop(1)

    def echo_server(self, sock, address):
        r = sock.recv(len(self.test_input))
        sock.send(r)

########NEW FILE########
__FILENAME__ = test_pysnmp_wrapper
# Copyright (C) 2013  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import unittest
import tempfile
import shutil
import os

from conpot.protocols.snmp.build_pysnmp_mib_wrapper import mib2pysnmp, find_mibs, compile_mib
from conpot.protocols.snmp import command_responder


class TestBase(unittest.TestCase):
    def test_wrapper_processing(self):
        """
        Tests that the wrapper can process a valid mib file without errors.
        """
        result = mib2pysnmp('conpot/tests/data/VOGON-POEM-MIB.mib')
        self.assertTrue('mibBuilder.exportSymbols("VOGON-POEM-MIB"' in result,
                        'mib2pysnmp did not generate the expected output. Output: {0}'.format(result))

    def test_wrapper_output(self):
        """
        Tests that the wrapper generates output that can be consumed by the command responder.
        """
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp()
            result = mib2pysnmp('conpot/tests/data/VOGON-POEM-MIB.mib')

            with open(os.path.join(tmpdir, 'VOGON-POEM-MIB' + '.py'), 'w') as output_file:
                output_file.write(result)

            cmd_responder = command_responder.CommandResponder('', 0, [tmpdir])
            cmd_responder.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder.loadModules('VOGON-POEM-MIB')
            result = cmd_responder._get_mibSymbol('VOGON-POEM-MIB', 'poemNumber')

            self.assertIsNotNone(result, 'The expected MIB (VOGON-POEM-MIB) could not be loaded.')
        finally:
            shutil.rmtree(tmpdir)

    def test_find(self):
        """
        Tests that the wrapper can find mib files.
        """
        input_dir = None
        try:
            input_dir = tempfile.mkdtemp()
            input_file = 'conpot/tests/data/VOGON-POEM-MIB.mib'
            shutil.copy(input_file, input_dir)
            available_mibs = find_mibs([input_dir])
            self.assertIn('VOGON-POEM-MIB', available_mibs)
        finally:
            shutil.rmtree(input_dir)

    def test_compile(self):
        """
        Tests that the wrapper can output mib files.
        """
        input_dir = None
        output_dir = None
        try:
            input_dir = tempfile.mkdtemp()
            output_dir = tempfile.mkdtemp()
            shutil.copy('conpot/tests/data/VOGON-POEM-MIB.mib', input_dir)
            find_mibs([input_dir])
            compile_mib('VOGON-POEM-MIB', output_dir)
            self.assertIn('VOGON-POEM-MIB.py', os.listdir(output_dir))
        finally:
            shutil.rmtree(input_dir)
            shutil.rmtree(output_dir)

########NEW FILE########
__FILENAME__ = test_s7_server
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import unittest

from conpot.protocols.s7comm.s7_server import S7Server
from conpot.tests.helpers import s7comm_client

import conpot.core as conpot_core

from gevent import monkey
monkey.patch_all()


class TestBase(unittest.TestCase):

    def setUp(self):
        self.databus = conpot_core.get_databus()
        self.databus.initialize('conpot/templates/default.xml')
        S7_instance = S7Server('conpot/templates/default.xml')
        self.S7_server = S7_instance.get_server('localhost', 0)
        self.S7_server.start()
        self.server_port = self.S7_server.server_port

    def tearDown(self):
        self.S7_server.stop()

    def test_s7(self):
        """
        Objective: Test if the S7 server returns the values expected.
        """
        src_tsaps = (0x100, 0x200)
        dst_tsaps = (0x102, 0x200, 0x201)
        s7_con = s7comm_client.s7('127.0.0.1', self.server_port)
        res = None
        for src_tsap in src_tsaps:
            for dst_tsap in dst_tsaps:
                try:
                    s7_con.src_tsap = src_tsap
                    s7_con.dst_tsap = dst_tsap
                    res = src_tsap, dst_tsap
                    break
                except s7comm_client.S7ProtocolError:
                    continue
            if res:
                break
        s7_con.src_ref = 10
        s7_con.s.settimeout(s7_con.timeout)
        s7_con.s.connect((s7_con.ip, s7_con.port))
        s7_con.Connect()
        identities = s7comm_client.GetIdentity('127.0.0.1', self.server_port, res[0], res[1])

        dic = {
            17: {1: "v.0.0"},
            28: {
                1: "Technodrome",
                2: "Siemens, SIMATIC, S7-200",
                3: "Mouser Factory",
                4: "Original Siemens Equipment",
                5: "88111222",
                7: "IM151-8 PN/DP CPU",
                10: "",
                11: ""
            }
        }

        for line in identities:
            sec, item, val = line.split(";")
            try:
                self.assertTrue(dic[int(sec)][int(item)] == val.strip())
            except AssertionError:
                print sec, item, val
                raise

########NEW FILE########
__FILENAME__ = test_snmp_server
# Copyright (C) 2013  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import unittest
import tempfile
import shutil

import gevent
from gevent import monkey

monkey.patch_all()

from pysnmp.proto import rfc1902

import conpot.core as conpot_core
from conpot.tests.helpers import snmp_client
from conpot.protocols.snmp.snmp_server import SNMPServer

class TestBase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.host = '127.0.0.1'
        databus = conpot_core.get_databus()
        databus.initialize('conpot/templates/default.xml')
        self.snmp_server = SNMPServer(self.host, 0, 'conpot/templates/default.xml', [self.tmp_dir], [self.tmp_dir])
        self.port = self.snmp_server.get_port()
        self.server_greenlet = gevent.spawn(self.snmp_server.start)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_snmp_get(self):
        """
        Objective: Test if we can get data via snmp_get
        """
        client = snmp_client.SNMPClient(self.host, self.port)
        OID = ((1, 3, 6, 1, 2, 1, 1, 1, 0), None)
        client.get_command(OID, callback=self.mock_callback)
        self.assertEqual("Siemens, SIMATIC, S7-200", self.result)

    def test_snmp_set(self):
        """
        Objective: Test if we can set data via snmp_set
        """
        client = snmp_client.SNMPClient(self.host, self.port)
        # syslocation
        OID = ((1, 3, 6, 1, 2, 1, 1, 6, 0), rfc1902.OctetString('TESTVALUE'))
        client.set_command(OID, callback=self.mock_callback)
        databus = conpot_core.get_databus()
        self.assertEqual('TESTVALUE', databus.get_value('sysLocation'))

    def mock_callback(self, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx):
        self.result = None
        if errorIndication:
            self.result = errorIndication
        elif errorStatus:
            self.result = errorStatus.prettyPrint()
        else:
            for oid, val in varBindTable:
                self.result = val.prettyPrint()

########NEW FILE########
__FILENAME__ = test_taxii
# Copyright (C) 2013  Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import os
from datetime import datetime
from StringIO import StringIO

import unittest
from ConfigParser import ConfigParser
from lxml import etree

from conpot.core.loggers.taxii_log import TaxiiLogger
from conpot.core.loggers.stix_transform import StixTransformer
from conpot.tests.helpers.mitre_stix_validator import STIXValidator


class Test_Loggers(unittest.TestCase):

    @unittest.skip("disabled")
    def test_stix_transform(self):
        """
        Objective: Test if our STIX xml can be validated.
        """
        config = ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), '../conpot.cfg')
        config.read(config_file)
        config.set('taxii', 'enabled', True)
        config.set('taxii', 'use_contact_info', True)
        config.set('taxii', 'contact_name', 'James Bond')
        config.set('taxii', 'contact_mail', 'a@b.c')

        test_event = {'remote': ('127.0.0.1', 54872), 'data_type': 's7comm',
                      'public_ip': '111.222.111.222',
                      'timestamp': datetime.now(),
                      'session_id': '101d9884-b695-4d8b-bf24-343c7dda1b68',
                      'data': {0: {'request': 'who are you', 'response': 'mr. blue'},
                               1: {'request': 'give me apples', 'response': 'no way'}}}
        dom = etree.parse('conpot/templates/default.xml')
        stixTransformer = StixTransformer(config, dom)
        stix_package_xml = stixTransformer.transform(test_event)
        xmlValidator = STIXValidator(None, True, False)

        result_dict = xmlValidator.validate(StringIO(stix_package_xml.encode('utf-8')))
        errors = ''
        if 'errors' in result_dict:
            errors = ', '.join(result_dict['errors'])
        self.assertTrue(result_dict['result'], 'Error while validations STIX xml: {0}'. format(errors))

    def test_taxii(self):
        """
        Objective: Test if we can transmit data to MITRE's TAXII test server.
        Note: This actually also tests the StixTransformer since the event is parsed by the transformer
        before transmission.
        """
        config = ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), '../conpot.cfg')
        config.read(config_file)
        config.set('taxii', 'enabled', True)

        test_event = {'remote': ('127.0.0.1', 54872), 'data_type': 's7comm',
                      'timestamp': datetime.now(),
                      'session_id': '101d9884-b695-4d8b-bf24-343c7dda1b68',
                      'data': {0: {'request': 'who are you', 'response': 'mr. blue'},
                               1: {'request': 'give me apples', 'response': 'no way'}}}
        dom = etree.parse('conpot/templates/default.xml')
        taxiiLogger = TaxiiLogger(config, dom)
        taxii_result = taxiiLogger.log(test_event)
        # TaxiiLogger returns false if the message could not be delivered
        self.assertTrue(taxii_result)

########NEW FILE########
__FILENAME__ = ext_ip
# Copyright (C) 2014  Lukas Rist <glaslos@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json
import logging
import socket

import requests
from requests.exceptions import Timeout, ConnectionError


logger = logging.getLogger(__name__)


def _verify_address(addr):
    try:
        socket.inet_aton(addr)
        return True
    except (socket.error, UnicodeEncodeError, TypeError):
        return False


def _fetch_data(urls):
    # we only want warning+ messages from the requests module
    logging.getLogger("requests").setLevel(logging.WARNING)
    for url in urls:
        try:
            req = requests.get(url)
            if req.status_code == 200:
                data = req.text.strip()
                if data is None or not _verify_address(data):
                    continue
                else:
                    return data
            else:
                raise ConnectionError
        except (Timeout, ConnectionError) as e:
            logger.warning('Could not fetch public ip from {0}'.format(url))
    return None


def get_ext_ip(config=None, urls=None):
    if config:
        urls = json.loads(config.get('fetch_public_ip', 'urls'))
    public_ip = _fetch_data(urls)
    if public_ip:
        logger.info('Fetched {0} as external ip.'.format(public_ip))
    else:
        logger.warning('Could not fetch public ip: {0}'.format(public_ip))
    return public_ip


if __name__ == "__main__":
    print get_ext_ip(urls=["http://www.telize.com/ip", "http://queryip.net/ip/", "http://ifconfig.me/ip"])

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Conpot documentation build configuration file, created by
# sphinx-quickstart on Sat Apr 20 14:00:03 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__)))
import conpot_version

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#   sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#   needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#  source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Conpot'
copyright = u'2013, Glastopf Developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

# The short X.Y version.
version = conpot_version.__version__
# The full version, including alpha/beta/rc tags.
release = conpot_version.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#  language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#  today = ''
# Else, today_fmt is used as the format for a strftime call.
#t  oday_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#  default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#  add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#  add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#  show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#  modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#  keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#  html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#  html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#  html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#  html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#  html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#  html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#  html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#  html_additional_pages = {}

# If false, no module index is generated.
#  html_domain_indices = True

# If false, no index is generated.
#  html_use_index = True

# If true, the index is split into individual pages for each letter.
#  html_split_index = False

# If true, links to the reST sources are added to the pages.
#  html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#  html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#  html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#  html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#  html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Conpotdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#  'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#  'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#  'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Conpot.tex', u'Conpot Documentation',
   u'Glastopf Developers', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#  latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#  latex_use_parts = False

# If true, show page references after internal links.
#  latex_show_pagerefs = False

# If true, show URL addresses after external links.
#  latex_show_urls = False

# Documents to append as an appendix to all manuals.
#  latex_appendices = []

# If false, no module index is generated.
#  latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'conpot', u'Conpot Documentation',
     [u'Glastopf Developers'], 1)
]

# If true, show URL addresses after external links.
#  man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Conpot', u'Conpot Documentation',
   u'Glastopf Developers', 'Conpot', 'ICS/SCADA honeypot.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#  texinfo_appendices = []

# If false, no module index is generated.
#  texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#  texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#  texinfo_no_detailmenu = False

########NEW FILE########
