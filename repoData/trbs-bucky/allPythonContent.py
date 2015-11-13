__FILENAME__ = carbon
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import six
import sys
import time
import socket
import struct
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle

import bucky.client as client
import bucky.names as names


if six.PY3:
    xrange = range


log = logging.getLogger(__name__)


class DebugSocket(object):
    def sendall(self, data):
        sys.stdout.write(data)


class CarbonClient(client.Client):
    def __init__(self, cfg, pipe):
        super(CarbonClient, self).__init__(pipe)
        self.debug = cfg.debug
        self.ip = cfg.graphite_ip
        self.port = cfg.graphite_port
        self.max_reconnects = cfg.graphite_max_reconnects
        self.reconnect_delay = cfg.graphite_reconnect_delay
        if self.max_reconnects <= 0:
            self.max_reconnects = sys.maxint
        self.connect()

    def connect(self):
        if self.debug:
            log.debug("Connected the debug socket.")
            self.sock = DebugSocket()
            return
        for i in xrange(self.max_reconnects):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.connect((self.ip, self.port))
                log.info("Connected to Carbon at %s:%s", self.ip, self.port)
                return
            except socket.error as e:
                if i + 1 >= self.max_reconnects:
                    raise
                log.error("Failed to connect to %s:%s: %s", self.ip, self.port, e)
                if self.reconnect_delay > 0:
                    time.sleep(self.reconnect_delay)

    def reconnect(self):
        self.close()
        self.connect()

    def close(self):
        try:
            self.sock.close()
        except:
            pass

    def send(self, host, name, value, mtime):
        raise NotImplemented


class PlaintextClient(CarbonClient):
    def send(self, host, name, value, mtime):
        stat = names.statname(host, name)
        mesg = "%s %s %s\n" % (stat, value, mtime)
        for i in xrange(self.max_reconnects):
            try:
                self.sock.sendall(mesg)
                return
            except socket.error as err:
                if i + 1 >= self.max_reconnects:
                    raise
                log.error("Failed to send data to Carbon server: %s", err)
                self.reconnect()


class PickleClient(CarbonClient):
    def __init__(self, cfg, pipe):
        super(PickleClient, self).__init__(cfg, pipe)
        self.buffer_size = cfg.graphite_pickle_buffer_size
        self.buffer = []

    def send(self, host, name, value, mtime):
        stat = names.statname(host, name)
        self.buffer.append((stat, (mtime, value)))
        if len(self.buffer) >= self.buffer_size:
            self.transmit()

    def transmit(self):
        payload = pickle.dumps(self.buffer, protocol=-1)
        header = struct.pack("!L", len(payload))
        self.buffer = []
        for i in xrange(self.max_reconnects):
            try:
                self.sock.sendall(header + payload)
                return
            except socket.error as err:
                if i + 1 >= self.max_reconnects:
                    raise
                log.error("Failed to send data to Carbon server: %s", err)
                self.reconnect()

########NEW FILE########
__FILENAME__ = cfg

debug = False
log_level = "INFO"
nice = None
uid = None
gid = None

metricsd_ip = "127.0.0.1"
metricsd_port = 23632
metricsd_enabled = True
metricsd_default_interval = 10.0
metricsd_handlers = []

collectd_ip = "127.0.0.1"
collectd_port = 25826
collectd_enabled = True
collectd_types = []
collectd_converters = []
collectd_use_entry_points = True

collectd_security_level = 0
collectd_auth_file = None

statsd_ip = "127.0.0.1"
statsd_port = 8125
statsd_enabled = True
statsd_flush_time = 10.0
statsd_legacy_namespace = True
statsd_global_prefix = "stats"
statsd_prefix_counter = "counters"
statsd_prefix_timer = "timers"
statsd_prefix_gauge = "gauges"

graphite_ip = "127.0.0.1"
graphite_port = 2003
graphite_max_reconnects = 3
graphite_reconnect_delay = 5
graphite_pickle_enabled = False
graphite_pickle_buffer_size = 500

full_trace = False

name_prefix = None
name_prefix_parts = None
name_postfix = None
name_postfix_parts = None
name_replace_char = '_'
name_strip_duplicates = True
name_host_trim = []

custom_clients = []

processor = None
processor_drop_on_error = False

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2012 Cloudant, Inc.

import multiprocessing

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        pass


class Client(multiprocessing.Process):
    def __init__(self, pipe):
        super(Client, self).__init__()
        self.daemon = True
        self.pipe = pipe

    def run(self):
        setproctitle("bucky: %s" % self.__class__.__name__)
        while True:
            sample = self.pipe.recv()
            if sample is None:
                break
            self.send(*sample)

    def send(self, host, name, value, time):
        raise NotImplemented()

########NEW FILE########
__FILENAME__ = collectd
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import os
import six
import copy
import struct
import logging

import hmac
from hashlib import sha1
from hashlib import sha256
from Crypto.Cipher import AES

from bucky.errors import ConfigError, ProtocolError
from bucky.udpserver import UDPServer
from bucky.helpers import FileMonitor

log = logging.getLogger(__name__)


class CPUConverter(object):
    PRIORITY = -1

    def __call__(self, sample):
        return ["cpu", sample["plugin_instance"], sample["type_instance"]]


class InterfaceConverter(object):
    PRIORITY = -1

    def __call__(self, sample):
        return filter(None, [
            "interface",
            sample.get("plugin_instance", ""),
            sample.get("type_instance", ""),
            sample["type"],
            sample["value_name"]
        ])


class MemoryConverter(object):
    PRIORITY = -1

    def __call__(self, sample):
        return ["memory", sample["type_instance"]]


class DefaultConverter(object):
    PRIORITY = -1

    def __call__(self, sample):
        parts = []
        parts.append(sample["plugin"].strip())
        if sample.get("plugin_instance"):
            parts.append(sample["plugin_instance"].strip())
        stype = sample.get("type", "").strip()
        if stype and stype != "value":
            parts.append(stype)
        stypei = sample.get("type_instance", "").strip()
        if stypei:
            parts.append(stypei)
        vname = sample.get("value_name").strip()
        if vname and vname != "value":
            parts.append(vname)
        return parts


DEFAULT_CONVERTERS = {
    "cpu": CPUConverter(),
    "interface": InterfaceConverter(),
    "memory": MemoryConverter(),
    "_default": DefaultConverter(),
}


class CollectDTypes(object):
    def __init__(self, types_dbs=[]):
        self.types = {}
        self.type_ranges = {}
        if not types_dbs:
            types_dbs = filter(os.path.exists, [
                "/usr/share/collectd/types.db",
                "/usr/local/share/collectd/types.db",
            ])
            if not types_dbs:
                raise ConfigError("Unable to locate types.db")
        self.types_dbs = types_dbs
        self._load_types()

    def get(self, name):
        t = self.types.get(name)
        if t is None:
            raise ProtocolError("Invalid type name: %s" % name)
        return t

    def _load_types(self):
        for types_db in self.types_dbs:
            with open(types_db) as handle:
                for line in handle:
                    if line.lstrip()[:1] == "#":
                        continue
                    if not line.strip():
                        continue
                    self._add_type_line(line)
            log.info("Loaded collectd types from %s", types_db)

    def _add_type_line(self, line):
        types = {
            "COUNTER": 0,
            "GAUGE": 1,
            "DERIVE": 2,
            "ABSOLUTE": 3
        }
        name, spec = line.split(None, 1)
        self.types[name] = []
        self.type_ranges[name] = {}
        vals = spec.split(", ")
        for val in vals:
            vname, vtype, minv, maxv = val.strip().split(":")
            vtype = types.get(vtype)
            if vtype is None:
                raise ValueError("Invalid value type: %s" % vtype)
            minv = None if minv == "U" else float(minv)
            maxv = None if maxv == "U" else float(maxv)
            self.types[name].append((vname, vtype))
            self.type_ranges[name][vname] = (minv, maxv)


class CollectDParser(object):
    def __init__(self, types_dbs=[]):
        self.types = CollectDTypes(types_dbs=types_dbs)

    def parse(self, data):
        for sample in self.parse_samples(data):
            yield sample

    def parse_samples(self, data):
        types = {
            0x0000: self._parse_string("host"),
            0x0001: self._parse_time("time"),
            0x0008: self._parse_time_hires("time"),
            0x0002: self._parse_string("plugin"),
            0x0003: self._parse_string("plugin_instance"),
            0x0004: self._parse_string("type"),
            0x0005: self._parse_string("type_instance"),
            0x0006: None,  # handle specially
            0x0007: self._parse_time("interval"),
            0x0009: self._parse_time_hires("interval")
        }
        sample = {}
        for (ptype, data) in self.parse_data(data):
            if ptype not in types:
                log.debug("Ignoring part type: 0x%02x", ptype)
                continue
            if ptype != 0x0006:
                types[ptype](sample, data)
                continue
            for vname, vtype, val in self.parse_values(sample["type"], data):
                sample["value_name"] = vname
                sample["value_type"] = vtype
                sample["value"] = val
                yield copy.deepcopy(sample)

    def parse_data(self, data):
        types = set([
            0x0000, 0x0001, 0x0002, 0x0003, 0x0004,
            0x0005, 0x0006, 0x0007, 0x0008, 0x0009,
            0x0100, 0x0101, 0x0200, 0x0210
        ])
        while len(data) > 0:
            if len(data) < 4:
                raise ProtocolError("Truncated header.")
            (part_type, part_len) = struct.unpack("!HH", data[:4])
            data = data[4:]
            if part_type not in types:
                raise ProtocolError("Invalid part type: 0x%02x" % part_type)
            part_len -= 4  # includes four header bytes we just parsed
            if len(data) < part_len:
                raise ProtocolError("Truncated value.")
            part_data, data = data[:part_len], data[part_len:]
            yield (part_type, part_data)

    def parse_values(self, stype, data):
        types = {0: "!Q", 1: "<d", 2: "!q", 3: "!Q"}
        (nvals,) = struct.unpack("!H", data[:2])
        data = data[2:]
        if len(data) != 9 * nvals:
            raise ProtocolError("Invalid value structure length.")
        vtypes = self.types.get(stype)
        if nvals != len(vtypes):
            raise ProtocolError("Values different than types.db info.")
        for i in range(nvals):
            if six.PY3:
                vtype = data[i]
            else:
                (vtype,) = struct.unpack("B", data[i])
            if vtype != vtypes[i][1]:
                raise ProtocolError("Type mismatch with types.db")
        data = data[nvals:]
        for i in range(nvals):
            vdata, data = data[:8], data[8:]
            (val,) = struct.unpack(types[vtypes[i][1]], vdata)
            yield vtypes[i][0], vtypes[i][1], val

    def _parse_string(self, name):
        def _parser(sample, data):
            if six.PY3:
                data = data.decode()
            if data[-1] != '\0':
                raise ProtocolError("Invalid string detected.")
            sample[name] = data[:-1]
        return _parser

    def _parse_time(self, name):
        def _parser(sample, data):
            if len(data) != 8:
                raise ProtocolError("Invalid time data length.")
            (val,) = struct.unpack("!Q", data)
            sample[name] = float(val)
        return _parser

    def _parse_time_hires(self, name):
        def _parser(sample, data):
            if len(data) != 8:
                raise ProtocolError("Invalid hires time data length.")
            (val,) = struct.unpack("!Q", data)
            sample[name] = val * (2 ** -30)
        return _parser


class CollectDCrypto(object):
    def __init__(self, cfg):
        sec_level = cfg.collectd_security_level
        if sec_level in ("sign", "SIGN", "Sign", 1):
            self.sec_level = 1
        elif sec_level in ("encrypt", "ENCRYPT", "Encrypt", 2):
            self.sec_level = 2
        else:
            self.sec_level = 0
        self.auth_file = cfg.collectd_auth_file
        self.auth_db = {}
        self.cfg_mon = None
        if self.auth_file:
            self.load_auth_file()
            self.cfg_mon = FileMonitor(self.auth_file)
        if self.sec_level:
            if not self.auth_file:
                raise ConfigError("Collectd security level configured but no "
                                  "auth file specified in configuration")
            if not self.auth_db:
                raise ConfigError("Collectd security level configured but no "
                                  "user/passwd entries loaded from auth file")

    def load_auth_file(self):
        try:
            f = open(self.auth_file)
        except IOError as exc:
            raise ConfigError("Unable to load collectd's auth file: %r", exc)
        self.auth_db.clear()
        for line in f:
            line = line.strip()
            if not line or line[0] == "#":
                continue
            user, passwd = line.split(":", 1)
            user = user.strip()
            passwd = passwd.strip()
            if not user or not passwd:
                log.warning("Found line with missing user or password")
                continue
            if user in self.auth_db:
                log.warning("Found multiple entries for single user")
            self.auth_db[user] = passwd
        f.close()
        log.info("Loaded collectd's auth file from %s", self.auth_file)

    def parse(self, data):
        if len(data) < 4:
            raise ProtocolError("Truncated header.")
        part_type, part_len = struct.unpack("!HH", data[:4])
        sec_level = {0x0200: 1, 0x0210: 2}.get(part_type, 0)
        if sec_level < self.sec_level:
            raise ProtocolError("Packet has lower security level than allowed")
        if not sec_level:
            return data
        if sec_level == 1 and not self.sec_level:
            return data[part_len:]
        data = data[4:]
        part_len -= 4
        if len(data) < part_len:
            raise ProtocolError("Truncated part payload.")
        if self.cfg_mon is not None and self.cfg_mon.modified():
            log.info("Collectd authfile modified, reloading")
            self.load_auth_file()
        if sec_level == 1:
            return self.parse_signed(part_len, data)
        if sec_level == 2:
            return self.parse_encrypted(part_len, data)

    def parse_signed(self, part_len, data):
        if part_len <= 32:
            raise ProtocolError("Truncated signed part.")
        sig, data = data[:32], data[32:]
        uname_len = part_len - 32
        uname = data[:uname_len].decode()
        if uname not in self.auth_db:
            raise ProtocolError("Signed packet, unknown user '%s'" % uname)
        password = self.auth_db[uname].encode()
        sig2 = hmac.new(password, msg=data, digestmod=sha256).digest()
        if not self._hashes_match(sig, sig2):
            raise ProtocolError("Bad signature from user '%s'" % uname)
        data = data[uname_len:]
        return data

    def parse_encrypted(self, part_len, data):
        if part_len != len(data):
            raise ProtocolError("Enc pkt size disaggrees with header.")
        if len(data) <= 38:
            raise ProtocolError("Truncated encrypted part.")
        uname_len, data = struct.unpack("!H", data[:2])[0], data[2:]
        if len(data) <= uname_len + 36:
            raise ProtocolError("Truncated encrypted part.")
        uname, data = data[:uname_len].decode(), data[uname_len:]
        if uname not in self.auth_db:
            raise ProtocolError("Couldn't decrypt, unknown user '%s'" % uname)
        iv, data = data[:16], data[16:]
        password = self.auth_db[uname].encode()
        key = sha256(password).digest()
        pad_bytes = 16 - (len(data) % 16)
        data += b'\0' * pad_bytes
        data = AES.new(key, IV=iv, mode=AES.MODE_OFB).decrypt(data)
        data = data[:-pad_bytes]
        tag, data = data[:20], data[20:]
        tag2 = sha1(data).digest()
        if not self._hashes_match(tag, tag2):
            raise ProtocolError("Bad checksum on enc pkt for '%s'" % uname)
        return data

    def _hashes_match(self, a, b):
        """Constant time comparison of bytes for py3, strings for py2"""
        if len(a) != len(b):
            return False
        diff = 0
        if six.PY2:
            a = bytearray(a)
            b = bytearray(b)
        for x, y in zip(a, b):
            diff |= x ^ y
        return not diff


class CollectDConverter(object):
    def __init__(self, cfg):
        self.converters = dict(DEFAULT_CONVERTERS)
        self._load_converters(cfg)

    def convert(self, sample):
        default = self.converters["_default"]
        handler = self.converters.get(sample["plugin"], default)
        try:
            name_parts = handler(sample)
            if name_parts is None:
                return  # treat None as "ignore sample"
            name = '.'.join(name_parts)
        except:
            log.exception("Exception in sample handler  %s (%s):", sample["plugin"], handler)
            return
        host = sample.get("host", "")
        return (
            host,
            name,
            sample["value_type"],
            sample["value"],
            int(sample["time"])
        )

    def _load_converters(self, cfg):
        cfg_conv = cfg.collectd_converters
        for conv in cfg_conv:
            self._add_converter(conv, cfg_conv[conv], source="config")
        if not cfg.collectd_use_entry_points:
            return
        import pkg_resources
        group = 'bucky.collectd.converters'
        for ep in pkg_resources.iter_entry_points(group):
            name, klass = ep.name, ep.load()
            self._add_converter(name, klass, source=ep.module_name)

    def _add_converter(self, name, inst, source="unknown"):
        if name not in self.converters:
            log.info("Converter: %s from %s", name, source)
            self.converters[name] = inst
            return
        kpriority = getattr(inst, "PRIORITY", 0)
        ipriority = getattr(self.converters[name], "PRIORITY", 0)
        if kpriority > ipriority:
            log.info("Replacing: %s", name)
            log.info("Converter: %s from %s", name, source)
            self.converters[name] = inst
            return
        log.info("Ignoring: %s (%s) from %s (priority: %s vs %s)",
                 name, inst, source, kpriority, ipriority)


class CollectDServer(UDPServer):
    def __init__(self, queue, cfg):
        super(CollectDServer, self).__init__(cfg.collectd_ip, cfg.collectd_port)
        self.queue = queue
        self.crypto = CollectDCrypto(cfg)
        self.parser = CollectDParser(cfg.collectd_types)
        self.converter = CollectDConverter(cfg)
        self.prev_samples = {}
        self.last_sample = None

    def handle(self, data, addr):
        try:
            data = self.crypto.parse(data)
        except ProtocolError as e:
            log.error("Protocol error in CollectDCrypto: %s", e)
            return True
        try:
            for sample in self.parser.parse(data):
                self.last_sample = sample
                stype = sample["type"]
                vname = sample["value_name"]
                sample = self.converter.convert(sample)
                if sample is None:
                    continue
                host, name, vtype, val, time = sample
                if not name.strip():
                    continue
                val = self.calculate(host, name, vtype, val, time)
                val = self.check_range(stype, vname, val)
                if val is not None:
                    self.queue.put((host, name, val, time))
        except ProtocolError as e:
            log.error("Protocol error: %s", e)
            if self.last_sample is not None:
                log.info("Last sample: %s", self.last_sample)
        return True

    def check_range(self, stype, vname, val):
        if val is None:
            return
        try:
            vmin, vmax = self.parser.types.type_ranges[stype][vname]
        except KeyError:
            log.error("Couldn't find vmin, vmax in CollectDTypes")
            return val
        if vmin is not None and val < vmin:
            log.debug("Invalid value %s (<%s) for %s", val, vmin, vname)
            log.debug("Last sample: %s", self.last_sample)
            return
        if vmax is not None and val > vmax:
            log.debug("Invalid value %s (>%s) for %s", val, vmax, vname)
            log.debug("Last sample: %s", self.last_sample)
            return
        return val

    def calculate(self, host, name, vtype, val, time):
        handlers = {
            0: self._calc_counter,  # counter
            1: lambda _host, _name, v, _time: v,  # gauge
            2: self._calc_derive,  # derive
            3: self._calc_absolute  # absolute
        }
        if vtype not in handlers:
            log.error("Invalid value type %s for %s", vtype, name)
            log.info("Last sample: %s", self.last_sample)
            return
        return handlers[vtype](host, name, val, time)

    def _calc_counter(self, host, name, val, time):
        key = (host, name)
        if key not in self.prev_samples:
            self.prev_samples[key] = (val, time)
            return
        pval, ptime = self.prev_samples[key]
        self.prev_samples[key] = (val, time)
        if time <= ptime:
            log.error("Invalid COUNTER update for: %s:%s" % key)
            log.info("Last sample: %s", self.last_sample)
            return
        if val < pval:
            # this is supposed to handle counter wrap around
            # see https://collectd.org/wiki/index.php/Data_source
            log.debug("COUNTER wrap-around for: %s:%s (%s -> %s)",
                      host, name, pval, val)
            if pval < 0x100000000:
                val += 0x100000000  # 2**32
            else:
                val += 0x10000000000000000  # 2**64
        return float(val - pval) / (time - ptime)

    def _calc_derive(self, host, name, val, time):
        key = (host, name)
        if key not in self.prev_samples:
            self.prev_samples[key] = (val, time)
            return
        pval, ptime = self.prev_samples[key]
        self.prev_samples[key] = (val, time)
        if time <= ptime:
            log.debug("Invalid DERIVE update for: %s:%s" % key)
            log.debug("Last sample: %s", self.last_sample)
            return
        return float(val - pval) / (time - ptime)

    def _calc_absolute(self, host, name, val, time):
        key = (host, name)
        if key not in self.prev_samples:
            self.prev_samples[key] = (val, time)
            return
        _pval, ptime = self.prev_samples[key]
        self.prev_samples[key] = (val, time)
        if time <= ptime:
            log.error("Invalid ABSOLUTE update for: %s:%s" % key)
            log.info("Last sample: %s", self.last_sample)
            return
        return float(val) / (time - ptime)

########NEW FILE########
__FILENAME__ = errors


class BuckyError(Exception):
    def __init__(self, mesg):
        self.mesg = mesg

    def __str__(self):
        return self.mesg


class ConnectError(BuckyError):
    pass


class ConfigError(BuckyError):
    pass


class ProtocolError(BuckyError):
    pass

########NEW FILE########
__FILENAME__ = helpers
import os
import multiprocessing

import watchdog.observers
import watchdog.events


class SingleFileEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, path, flag):
        super(SingleFileEventHandler, self).__init__()
        self.path = path
        self.flag = flag

    def on_modified(self, event):
        if event.src_path == self.path.encode():
            self.flag.value = 1


class FileMonitor(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.flag = multiprocessing.Value('i', 0)
        self.event_handler = SingleFileEventHandler(self.path, self.flag)
        self.observer = watchdog.observers.Observer()
        self.observer.schedule(self.event_handler, os.path.dirname(self.path))
        self.observer.start()

    def modified(self):
        if self.flag.value:
            self.flag.value = 0
            return True
        return False

    def stop(self):
        self.observer.stop()
        self.observer.join()

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import multiprocessing

import os
import six
import sys
import pwd
import grp
import signal
import logging
import optparse as op

try:
    import queue
except ImportError:
    import Queue as queue

import bucky
import bucky.cfg as cfg
import bucky.carbon as carbon
import bucky.collectd as collectd
import bucky.metricsd as metricsd
import bucky.statsd as statsd
import bucky.processor as processor
from bucky.errors import BuckyError


log = logging.getLogger(__name__)
levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}

__usage__ = "%prog [OPTIONS] [CONFIG_FILE]"
__version__ = "bucky %s" % bucky.__version__


def options():
    return [
        op.make_option(
            "--debug", dest="debug", default=False,
            action="store_true",
            help="Put server into debug mode. [%default]"
        ),
        op.make_option(
            "--metricsd-ip", dest="metricsd_ip", metavar="IP",
            default=cfg.metricsd_ip,
            help="IP address to bind for the MetricsD UDP socket [%default]"
        ),
        op.make_option(
            "--metricsd-port", dest="metricsd_port", metavar="INT",
            type="int", default=cfg.metricsd_port,
            help="Port to bind for the MetricsD UDP socket [%default]"
        ),
        op.make_option(
            "--disable-metricsd", dest="metricsd_enabled",
            default=cfg.metricsd_enabled, action="store_false",
            help="Disable the MetricsD UDP server"
        ),
        op.make_option(
            "--collectd-ip", dest="collectd_ip", metavar="IP",
            default=cfg.collectd_ip,
            help="IP address to bind for the CollectD UDP socket [%default]"
        ),
        op.make_option(
            "--collectd-port", dest="collectd_port", metavar="INT",
            type='int', default=cfg.collectd_port,
            help="Port to bind for the CollectD UDP socket [%default]"
        ),
        op.make_option(
            "--collectd-types", dest="collectd_types",
            metavar="FILE", action='append', default=cfg.collectd_types,
            help="Path to the collectd types.db file, can be specified multiple times"
        ),
        op.make_option(
            "--disable-collectd", dest="collectd_enabled",
            default=cfg.collectd_enabled, action="store_false",
            help="Disable the CollectD UDP server"
        ),
        op.make_option(
            "--statsd-ip", dest="statsd_ip", metavar="IP",
            default=cfg.statsd_ip,
            help="IP address to bind for the StatsD UDP socket [%default]"
        ),
        op.make_option(
            "--statsd-port", dest="statsd_port", metavar="INT",
            type="int", default=cfg.statsd_port,
            help="Port to bind for the StatsD UDP socket [%default]"
        ),
        op.make_option(
            "--disable-statsd", dest="statsd_enabled",
            default=cfg.statsd_enabled, action="store_false",
            help="Disable the StatsD server"
        ),
        op.make_option(
            "--graphite-ip", dest="graphite_ip", metavar="IP",
            default=cfg.graphite_ip,
            help="IP address of the Graphite/Carbon server [%default]"
        ),
        op.make_option(
            "--graphite-port", dest="graphite_port", metavar="INT",
            type="int", default=cfg.graphite_port,
            help="Port of the Graphite/Carbon server [%default]"
        ),
        op.make_option(
            "--full-trace", dest="full_trace",
            default=cfg.full_trace, action="store_true",
            help="Display full error if config file fails to load"
        ),
        op.make_option(
            "--log-level", dest="log_level",
            metavar="NAME", default="INFO",
            help="Logging output verbosity [%default]"
        ),
        op.make_option(
            "--nice", dest="nice",
            type="int", default=cfg.nice,
            help="Change default process priority"
        ),
        op.make_option(
            "--uid", dest="uid",
            type="str", default=cfg.uid,
            help="Drop privileges to this user"
        ),
        op.make_option(
            "--gid", dest="gid",
            type="str", default=cfg.gid,
            help="Drop privileges to this group"
        ),
    ]


def set_nice_level(priority):
    os.nice(priority)


def drop_privileges(user, group):
    if user is None:
        uid = os.getuid()
    elif user.lstrip("-").isdigit():
        uid = int(user)
    else:
        uid = pwd.getpwnam(user).pw_uid

    if group is None:
        gid = os.getgid()
    elif group.lstrip("-").isdigit():
        gid = int(group)
    else:
        gid = grp.getgrnam(group).gr_gid

    username = pwd.getpwuid(uid).pw_name
    # groupname = grp.getgrgid(gid).gr_name
    groups = [g for g in grp.getgrall() if username in g.gr_mem]

    os.setgroups(groups)
    if hasattr(os, 'setresgid'):
        os.setresgid(gid, gid, gid)
    else:
        os.setregid(gid, gid)
    if hasattr(os, 'setresuid'):
        os.setresuid(uid, uid, uid)
    else:
        os.setreuid(uid, uid)


def main():
    parser = op.OptionParser(
        usage=__usage__,
        version=__version__,
        option_list=options()
    )
    opts, args = parser.parse_args()

    # Logging have to be configured before load_config,
    # where it can (and should) be already used
    logfmt = "[%(levelname)s] %(module)s - %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(logfmt))
    handler.setLevel(logging.ERROR)  # Overridden by configuration
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.DEBUG)

    if args:
        try:
            cfgfile, = args
        except ValueError:
            parser.error("Too many arguments.")
    else:
        cfgfile = None
    load_config(cfgfile, full_trace=opts.full_trace)

    if cfg.debug:
        cfg.log_level = logging.DEBUG

    # Mandatory second commandline
    # processing pass to override values in cfg
    parser.parse_args(values=cfg)

    lvl = levels.get(cfg.log_level, cfg.log_level)
    handler.setLevel(lvl)

    if cfg.nice:
        set_nice_level(cfg.nice)

    if cfg.uid or cfg.gid:
        drop_privileges(cfg.uid, cfg.gid)

    bucky = Bucky(cfg)
    bucky.run()


class Bucky(object):
    def __init__(self, cfg):
        self.sampleq = multiprocessing.Queue()

        stypes = []
        if cfg.metricsd_enabled:
            stypes.append(metricsd.MetricsDServer)
        if cfg.collectd_enabled:
            stypes.append(collectd.CollectDServer)
        if cfg.statsd_enabled:
            stypes.append(statsd.StatsDServer)

        self.servers = []
        for stype in stypes:
            self.servers.append(stype(self.sampleq, cfg))

        if cfg.processor is not None:
            self.psampleq = multiprocessing.Queue()
            self.proc = processor.CustomProcessor(self.sampleq, self.psampleq,
                                                  cfg)
        else:
            self.proc = None
            self.psampleq = self.sampleq

        if cfg.graphite_pickle_enabled:
            carbon_client = carbon.PickleClient
        else:
            carbon_client = carbon.PlaintextClient

        self.clients = []
        for client in cfg.custom_clients + [carbon_client]:
            send, recv = multiprocessing.Pipe()
            instance = client(cfg, recv)
            self.clients.append((instance, send))

    def run(self):
        def sigterm_handler(signum, frame):
            log.info("Received SIGTERM")
            self.psampleq.put(None)

        for server in self.servers:
            server.start()
        if self.proc is not None:
            self.proc.start()
        for client, pipe in self.clients:
            client.start()

        signal.signal(signal.SIGTERM, sigterm_handler)

        while True:
            try:
                sample = self.psampleq.get(True, 1)
                if not sample:
                    break
                for instance, pipe in self.clients:
                    if not instance.is_alive():
                        self.shutdown("Client process died. Exiting.")
                    pipe.send(sample)
            except queue.Empty:
                pass
            except IOError as exc:
                # Probably due to interrupted system call by SIGTERM
                log.debug("Bucky IOError: %s", exc)
                continue
            for srv in self.servers:
                if not srv.is_alive():
                    self.shutdown("Server thread died. Exiting.")
            if self.proc is not None and not self.proc.is_alive():
                self.shutdown("Processor thread died. Exiting.")
        self.shutdown()

    def shutdown(self, err=''):
        log.info("Shutting down")
        for server in self.servers:
            log.info("Stopping server %s", server)
            server.close()
            server.join(1)
        if self.proc is not None:
            log.info("Stopping processor %s", self.proc)
            self.sampleq.put(None)
            self.proc.join(1)
        for client, pipe in self.clients:
            log.info("Stopping client %s", client)
            pipe.send(None)
            client.join(1)
        children = multiprocessing.active_children()
        for child in children:
            log.error("Child %s didn't die gracefully, terminating", child)
            child.terminate()
            child.join(1)
        if children and not err:
            err = "Not all children died gracefully"
        if err:
            raise BuckyError(err)


def load_config(cfgfile, full_trace=False):
    cfg_mapping = vars(cfg)
    try:
        if cfgfile is not None:
            if six.PY3:
                with open(cfgfile, 'rb') as file:
                    exec(compile(file.read(), cfgfile, 'exec'), cfg_mapping)
            else:
                execfile(cfgfile, cfg_mapping)  # noqa
    except Exception as e:
        log.error("Failed to read config file: %s", cfgfile)
        if full_trace:
            log.exception("Reason: %s", e)
        else:
            log.error("Reason: %s", e)
        sys.exit(1)
    for name in dir(cfg):
        if name.startswith("_"):
            continue
        if name in cfg_mapping:
            setattr(cfg, name, cfg_mapping[name])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        raise

########NEW FILE########
__FILENAME__ = counter
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

from bucky.metrics.metric import Metric, MetricValue as MV


class Counter(Metric):
    def __init__(self, name):
        self.name = name
        self.count = 0

    def update(self, value):
        self.value += value

    def clear(self):
        self.value = 0

    def metrics(self):
        return [MV(self.name, self.count)]

########NEW FILE########
__FILENAME__ = gauge
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

from bucky.metrics.metric import Metric, MetricValue as MV


class Gauge(Metric):
    def __init__(self, name):
        self.name = name
        self.value = 0.0

    def update(self, value):
        self.value = value

    def clear(self):
        pass

    def metrics(self):
        return [MV(self.name, self.value)]

########NEW FILE########
__FILENAME__ = histogram
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import math

from bucky.metrics.metric import Metric, MetricValue as MV
from bucky.metrics.stats.expdec_sample import ExpDecSample
from bucky.metrics.stats.usample import UniformSample


class Histogram(Metric):
    def __init__(self, name, biased=True, percentiles=None):
        self.name = name
        if biased:
            self.sample = ExpDecSample(1028, 0.015)
        else:
            self.sample = UniformSample(1028)
        self.percentiles = self._fmt(percentiles or (75, 85, 90, 95, 99, 99.9))
        self.count = 0
        self.sum = 0
        self.minv = None
        self.maxv = None
        self.variance = (-1.0, 0.0)

    def clear(self):
        self.sample.clear()
        self.count = 0
        self.sum = 0
        self.minv = None
        self.maxv = None
        self.variance = (-1.0, 0.0)

    def update(self, value):
        self.count += 1
        self.sum += value
        self.sample.update(value)
        if self.minv is None or value < self.minv:
            self.minv = value
        if self.maxv is None or value > self.maxv:
            self.maxv = value
        self._update_variance(value)

    def metrics(self):
        ret = []
        ret.append(MV("%s.count" % self.name, self.count))
        ret.append(MV("%s.sum" % self.name, self.sum))
        ret.append(MV("%s.min" % self.name, self.minv))
        ret.append(MV("%s.max" % self.name, self.maxv))
        if self.count > 0:
            ret.append(MV("%s.mean" % self.name, self.sum / self.count))
            ret.append(MV("%s.stddev" % self.name, self._stddev()))
            for disp, val in self._percentiles():
                name = "%s.%s" % (self.name, disp)
                ret.append(MV(name, val))
        return ret

    def _stddev(self):
        if self.count <= 1:
            return 0.0
        return math.sqrt(self.variance[1] / (float(self.count) - 1.0))

    def _update_variance(self, value):
        oldm, olds = self.variance
        if oldm == -1.0:
            self.variance = (value, 0.0)
            return
        newm = oldm + ((value - oldm) / self.count)
        news = olds + ((value - oldm) * (value - newm))
        self.variance = (newm, news)

    def _percentiles(self):
        values = self.sample.values()
        values.sort()
        ret = []
        for (p, d) in self.percentiles:
            pos = p * len(values + 1)
            if pos < 1:
                ret.append((d, values[0]))
            elif pos >= len(values):
                ret.append((d, values[-1]))
            else:
                lower, upper = values[int(pos - 1)], values[int(pos)]
                percentile = lower + ((pos - math.floor(pos)) * (upper - lower))
                ret.append((d, percentile))
        return ret

    def _fmt(self, percentiles):
        ret = []
        for p in percentiles:
            d = "%0.1f" % p
            if d.endswith(".0"):
                d = p[:-2]
            d = "perc_%s" % d.replace(".", "_")
            ret.append((p, d))

########NEW FILE########
__FILENAME__ = meter
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import time

from bucky.metrics.metric import Metric, MetricValue as MV
from bucky.metrics.stats.ewma import EWMA


class Meter(Metric):
    def __init__(self, name):
        self.name = name
        self.count = 0
        self.m1_rate = EWMA.oneMinuteEWMA()
        self.m5_rate = EWMA.fiveMinuteEWMA()
        self.m15_rate = EWMA.fifteenMinuteEWMA()
        self.start_time = time.time()

    def update(self, value=1):
        self.count += value
        self.m1_rate.update(value)
        self.m5_rate.update(value)
        self.m15_rate.update(value)

    def metrics(self):
        for r in (self.m1_rate, self.m5_rate, self.m15_rate):
            r.tick()
        ret = []
        elapsed = time.time() - self.start_time
        ret.append(MV("%s.count" % self.name, self.count))
        ret.append(MV("%s.rate_avg" % self.name, float(self.count) / elapsed))
        ret.append(MV("%s.rate_1m" % self.name, self.m1_rate.rate()))
        ret.append(MV("%s.rate_5m" % self.name, self.m5_rate.rate()))
        ret.append(MV("%s.rate_15m" % self.name, self.m15_rate.rate()))
        return ret

########NEW FILE########
__FILENAME__ = metric
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import time


class MetricValue(object):
    def __init__(self, name, value, now=None):
        self.name = name
        self.value = value
        self.time = now or time.time()


class Metric(object):
    def update(self, value):
        raise NotImplemented()

    def clear(self, value):
        raise NotImplemented()

    def metrics(slef):
        raise NotImplemented()

########NEW FILE########
__FILENAME__ = ewma
import six
import math


if six.PY3:
    ZERO_LONG = 0
else:
    ZERO_LONG = long(0)  # noqa


class EWMA(object):
    """
    Exponentially-weighted moving avergage. Based on the
    implementation in Coda Hale's metrics library:

       https://github.com/codahale/metrics/blob/development/metrics-core/src/main/java/com/yammer/metrics/stats/EWMA.java
    """

    M1_ALPHA = 1 - math.exp(-5.0 / 60.0)
    M5_ALPHA = 1 - math.exp(-5.0 / 60.0 / 5.0)
    M15_ALPHA = 1 - math.exp(-5.0 / 60.0 / 15.0)

    @staticmethod
    def oneMinuteEWMA():
        return EWMA(EWMA.M1_ALPHA, 5.0)

    @staticmethod
    def fiveMinuteEWMA():
        return EWMA(EWMA.M5_ALPHA, 5.0)

    @staticmethod
    def fifteenMinuteEWMA():
        return EWMA(EWMA.M15_ALPHA, 5.0)

    def __init__(self, alpha, interval):
        self.alpha = alpha
        self.interval = interval
        self.curr_rate = None
        self.uncounted = ZERO_LONG

    def update(self, val):
        self.uncounted += val

    def rate(self):
        return self.curr_rate

    def tick(self):
        count = self.uncounted
        self.uncounted = ZERO_LONG
        instant_rate = count / self.interval
        if self.initialized:
            self.curr_rate += (self.alpha * (instant_rate - self.curr_rate))
        else:
            self.curr_rate = instant_rate


########NEW FILE########
__FILENAME__ = expdec_sample
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import six
import math
import time
import random
import heapq


class ExpDecSample(object):
    """
    An exponentially-decaying random sample of longs. Based
    on the implementation in Coda Hale's metrics library:

      https://github.com/codahale/metrics/blob/development/metrics-core/src/main/java/com/yammer/metrics/stats/ExponentiallyDecayingSample.java
    """

    RESCALE_THRESHOLD = 60 * 60 * 1000000000

    def __init__(self, reservoir_size, alpha):
        self.rsize = reservoir_size
        self.alpha = alpha
        self.values = []
        self.count = 0
        self.start_time = self.tick()
        self.next_rescale = self.start_time + self.RESCALE_THRESHOLD

    def clear(self):
        self.count = 0
        self.start_time = self.tick()
        self.next_rescale = self.start_time + self.RESCALE_THRESHOLD

    def size(self):
        return int(min(self.rsize, self.count))

    def update(self, val, when=None):
        if when is None:
            when = self.tick()
        priority = self.weight(when - self.start_time) / random.random()
        self.count += 1
        if self.count <= self.rsize:
            heapq.heappush(self.values, (priority, val))
        else:
            if priority > self.values[0][0]:
                heapq.heapreplace(self.values, (priority, val))
        now = self.tick()
        if now >= self.next_rescale:
            self.rescale(now, self.next_rescale)

    def rescale(self, now, next):
        # See the comment in the original Java implementation.
        self.next_rescale = now + self.RESCALE_THRESHOLD
        old_start = self.start_time
        self.start_time = self.tick()
        newvals = []
        factor = math.exp(-self.alpha * (self.start_time - old_start))
        for k, v in self.values:
            newvals.append((k * factor, v))
        self.values = newvals

    if six.PY3:
        def tick(self):
            return time.time() * 1000000000.0
    else:
        def tick(self):
            return long(time.time() * 1000000000.0)  # noqa

    def weight(self, t):
        return math.exp(self.alpha * t)

    def get_values(self):
        return [v for (_, v) in self.values]

########NEW FILE########
__FILENAME__ = usample

import random


class UniformSample(object):
    """
    A random sample of a stream of long's based on the
    implementation in Coda Hale's Metrics library:

        https://github.com/codahale/metrics/blob/development/metrics-core/src/main/java/com/yammer/metrics/stats/UniformSample.java
    """

    def __init__(self, size):
        self.count = 0
        self.values = [0] * size

    def clear(self):
        self.count = 0
        for i in range(len(self.values)):
            self.values[i] = 0

    def size(self):
        if self.count > len(self.values):
            return len(self.values)
        return self.count

    def update(self, val):
        self.count += 1
        if self.count <= len(self.values):
            self.values[self.count - 1] = val
        else:
            r = random.random(0, self.count - 1)
            if r < len(self.values):
                self.values[r] = val

    def get_values(self):
        return self.values[:]

########NEW FILE########
__FILENAME__ = timer
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

from bucky.metrics.histogram import Histogram
from bucky.metrics.meter import Meter
from bucky.metrics.metric import Metric


class Timer(Metric):
    def __init__(self, name):
        self.name = name
        self.meter = Meter("%s.calls" % name)
        self.histogram = Histogram("%s.histo" % name)

    def clear(self):
        self.histogram.clear()

    def update(self, value):
        self.meter.mark()
        self.histogram.update(value)

    def metrics(self):
        return self.meter.metrics() + self.histogram.metrics()

########NEW FILE########
__FILENAME__ = metricsd
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import re
import six
import struct
import time
import logging
import multiprocessing

try:
    import queue
except ImportError:
    import Queue as queue

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        pass

import bucky.names as names

from bucky.errors import ConfigError, ProtocolError
from bucky.metrics.counter import Counter
from bucky.metrics.gauge import Gauge
from bucky.metrics.histogram import Histogram
from bucky.metrics.meter import Meter
from bucky.metrics.timer import Timer
from bucky.udpserver import UDPServer


log = logging.getLogger(__name__)


class MetricsDCommand(object):
    UPDATE = object()
    CLEAR = object()
    DELETE = object()

    def __init__(self, name, mtype, action, value=None):
        self.name = name
        self.mtype = mtype
        self.action = action
        self.value = value
        if self.action is not self.UPDATE and self.value is not None:
            raise ValueError("Values are only valid for updates")


class MetricsDParser(object):
    NUMERIC_TYPES = {
        0x00: "!B", 0x01: "!b",
        0x10: "!H", 0x11: "!h",
        0x20: "!I", 0x21: "!i",
        0x30: "!Q", 0x31: "!q",
        0x40: "!f", 0x41: "!d"
    }

    METRIC_TYPES = {
        0x00: Counter,
        0x10: Gauge,
        0x20: Histogram,
        0x30: Meter,
        0x40: Timer
    }

    METRIC_ACTION = {
        0x00: MetricsDCommand.UPDATE,
        0x01: MetricsDCommand.CLEAR,
        0x02: MetricsDCommand.DELETE
    }

    def __init__(self):
        pass

    def parse(self, data):
        if data[0] != 0xAA:
            raise ProtocolError("Invalid magic byte")
        hostname, data = self.parse_string(data)
        while len(data):
            mc, data = self.parse_metric(hostname, data)
            yield mc

    def parse_metric(self, hostname, data):
        cmd, data = data[0], data[1:]
        mtype = cmd & 0xF0
        action = cmd & 0x0F
        if mtype not in self.METRIC_TYPES:
            raise ProtocolError("Invalid metric type")
        if action not in self.METRIC_ACTIONS:
            raise ProtocolError("Invalid metric action")
        name, data = self.parse_string(data)
        if action is MetricsDCommand.UPDATE:
            value, data = self.parse_number(data)
        else:
            value = None
        stat = names.statname(hostname, name.split("."))
        cmd = MetricsDCommand(stat, mtype, action, value)
        return cmd, data

    def parse_string(self, data):
        (length,) = struct.unpack("!H", data[:2])
        if length > len(data) - 2:
            raise ProtocolError("Truncated string value")
        if data[2 + length] != 0x00:
            raise ProtocolError("String missing null-byte terminator")
        try:
            ret = data[2:2 + length - 1].decode("utf-8")
            return ret, data[2 + length + 1:]
        except UnicodeDecodeError:
            raise ProtocolError("String is not value UTF-8")

    def parse_number(self, data):
        fmt = self.NUMERIC_TYPES.get(data[0])
        if fmt is None:
            raise ProtocolError("Invalid numeric type")
        sz = struct.calcsize(fmt)
        if sz > len(data) - 1:
            raise ProtocolError("Truncated numeric value")
        (val, ) = struct.unpack(data[1:1 + sz])
        return val, data[1 + sz:]


class MetricsDHandler(multiprocessing.Process):
    def __init__(self, outbox, interval):
        super(MetricsDHandler, self).__init__()
        self.daemon = True
        self.interval = interval
        self.outbox = outbox
        self.inbox = multiprocessing.Queue()
        self.next_update = time.time() + self.interval
        self.metrics = {}

    def enqueue(self, mc):
        self.inbox.put(mc)

    def update_metric(self, mc):
        if mc.action is MetricsDCommand.DELETE:
            self.metrics.pop(mc.name, None)
            return
        metric = self.metrics.get(mc.name)
        if mc.action is MetricsDCommand.CLEAR:
            if metric is not None:
                metric.clear()
            return
        assert mc.action is MetricsDCommand.UPDATE
        if metric is None:
            metric = mc.mtype(mc.name)
        metric.update(mc.value)

    def run(self):
        setproctitle("bucky: %s" % self.__class__.__name__)
        while True:
            to_sleep = self.next_update - time.time()
            if to_sleep <= 0:
                self.flush_updates()
            self.next_update = time.time() + self.interval
            to_sleep = self.interval
            try:
                mv = self.inbox.get(True, to_sleep)
                if mv is None:
                    log.info("Handler received None, %s exiting", self)
                    break
                self.update_metric(mv)
            except queue.Empty:
                continue

    def close(self):
        self.inbox.put(None)

    if six.PY3:
        def flush_updates(self):
            for _, metric in self.metrics.items():
                for v in metric.metrics():
                    self.outbox.put((v.name, v.value, v.time))
    else:
        def flush_updates(self):
            for _, metric in self.metrics.iteritems():
                for v in metric.metrics():
                    self.outbox.put((v.name, v.value, v.time))


class MetricsDServer(UDPServer):
    def __init__(self, queue, cfg):
        super(MetricsDServer, self).__init__(cfg.metricsd_ip, cfg.metricsd_port)
        self.parser = MetricsDParser()
        self.handlers = self._init_handlers(queue, cfg)

    def handle(self, data, addr):
        try:
            for mc in self.parser.parse(data):
                handler = self._get_handler(mc.name)
                handler.enqueue(mc)
        except ProtocolError:
            log.exception("Error from: %s:%s" % addr)

    def _init_handlers(self, queue, cfg):
        ret = []
        default = cfg.metricsd_default_interval
        handlers = cfg.metricsd_handlers
        if not len(handlers):
            ret = [(None, MetricsDHandler(queue, default))]
            ret[0][1].start()
            return ret
        for item in handlers:
            if len(item) == 2:
                pattern, interval, priority = item[0], item[1], 100
            elif len(item) == 3:
                pattern, interval, priority = item
            else:
                raise ConfigError("Invalid handler specification: %s" % item)
            try:
                pattern = re.compile(pattern)
            except:
                raise ConfigError("Invalid pattern: %s" % pattern)
            if interval < 0:
                raise ConfigError("Invalid interval: %s" % interval)
            ret.append((pattern, interval, priority))
        handlers.sort(key=lambda p: p[2])
        ret = [(p, MetricsDHandler(queue, i)) for (p, i, _) in ret]
        ret.append((None, MetricsDHandler(queue, default)))
        for _, h in ret:
            h.start()
        return ret

    def _get_handler(self, name):
        for (p, h) in self.handlers:
            if p is None:
                return h
            if p.match(name):
                return h

    def close(self):
        for pattern, handler in self.handlers:
            handler.close()
        super(MetricsDServer, self).close()

########NEW FILE########
__FILENAME__ = names
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import bucky.cfg as cfg


__host_trim__ = None


def _get_host_trim():
    global __host_trim__
    if __host_trim__ is not None:
        return __host_trim__
    host_trim = cfg.name_host_trim
    __host_trim__ = []
    for s in host_trim:
        s = list(reversed([p.strip() for p in s.split(".")]))
        __host_trim__.append(s)
    return __host_trim__


def hostname(host):
    host_trim = _get_host_trim()
    parts = host.split(".")
    parts = list(reversed([p.strip() for p in parts]))
    for s in host_trim:
        same = True
        for i, p in enumerate(s):
            if p != parts[i]:
                same = False
                break
        if same:
            parts = parts[len(s):]
            return parts
    return parts


def strip_duplicates(parts):
    ret = []
    for p in parts:
        if len(ret) == 0 or p != ret[-1]:
            ret.append(p)
    return ret


def statname(host, name):
    nameparts = name.split('.')
    parts = []
    if cfg.name_prefix:
        parts.append(cfg.name_prefix)
    if cfg.name_prefix_parts:
        parts.extend(cfg.name_prefix_parts)
    if host:
        parts.extend(hostname(host))
    parts.extend(nameparts)
    if cfg.name_postfix_parts:
        parts.append(cfg.name_postfix_parts)
    if cfg.name_postfix:
        parts.append(cfg.name_postfix)
    if cfg.name_replace_char is not None:
        parts = [p.replace(".", cfg.name_replace_char) for p in parts]
    if cfg.name_strip_duplicates:
        parts = strip_duplicates(parts)
    return ".".join(parts)

########NEW FILE########
__FILENAME__ = processor
import logging
import multiprocessing

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        pass

try:
    import queue
except ImportError:
    import Queue as queue


log = logging.getLogger(__name__)


class Processor(multiprocessing.Process):
    def __init__(self, in_queue, out_queue, cfg):
        super(Processor, self).__init__()
        self.daemon = True
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.drop_on_error = cfg.processor_drop_on_error

    def run(self):
        setproctitle("bucky: %s" % self.__class__.__name__)
        while True:
            try:
                sample = self.in_queue.get(True, 1)
                if sample is None:
                    break
            except queue.Empty:
                pass
            else:
                try:
                    sample = self.process(*sample)
                except Exception as exc:
                    log.error("Error processing sample %s: %r", sample, exc)
                    if self.drop_on_error:
                        sample = None
                if sample is not None:
                    self.out_queue.put(sample)

    def process(self, host, name, val, time):
        raise NotImplementedError()


class CustomProcessor(Processor):
    def __init__(self, in_queue, out_queue, cfg):
        super(CustomProcessor, self).__init__(in_queue, out_queue, cfg)
        self.function = cfg.processor

    def process(self, host, name, val, time):
        return self.function(host, name, val, time)

########NEW FILE########
__FILENAME__ = statsd
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import re
import six
import math
import time
import logging
import threading

import bucky.udpserver as udpserver


log = logging.getLogger(__name__)


def make_name(parts):
    name = ""
    for part in parts:
        if part:
            name = name + part + "."
    return name


class StatsDHandler(threading.Thread):
    def __init__(self, queue, cfg):
        super(StatsDHandler, self).__init__()
        self.daemon = True
        self.queue = queue
        self.lock = threading.Lock()
        self.timers = {}
        self.gauges = {}
        self.counters = {}
        self.flush_time = cfg.statsd_flush_time
        self.legacy_namespace = cfg.statsd_legacy_namespace
        self.global_prefix = cfg.statsd_global_prefix
        self.prefix_counter = cfg.statsd_prefix_counter
        self.prefix_timer = cfg.statsd_prefix_timer
        self.prefix_gauge = cfg.statsd_prefix_gauge
        self.key_res = (
            (re.compile("\s+"), "_"),
            (re.compile("\/"), "-"),
            (re.compile("[^a-zA-Z_\-0-9\.]"), "")
        )

        if self.legacy_namespace:
            self.name_global = 'stats.'
            self.name_legacy_rate = 'stats.'
            self.name_legacy_count = 'stats_counts.'
            self.name_timer = 'stats.timers.'
            self.name_gauge = 'stats.gauges.'
        else:
            self.name_global = make_name([self.global_prefix])
            self.name_counter = make_name([self.global_prefix, self.prefix_counter])
            self.name_timer = make_name([self.global_prefix, self.prefix_timer])
            self.name_gauge = make_name([self.global_prefix, self.prefix_gauge])

    def run(self):
        name_global_numstats = self.name_global + "numStats"
        while True:
            time.sleep(self.flush_time)
            stime = int(time.time())
            with self.lock:
                num_stats = self.enqueue_timers(stime)
                num_stats += self.enqueue_counters(stime)
                num_stats += self.enqueue_gauges(stime)
                self.enqueue(name_global_numstats, num_stats, stime)

    def enqueue(self, name, stat, stime):
        # No hostnames on statsd
        self.queue.put((None, name, stat, stime))

    def enqueue_timers(self, stime):
        ret = 0
        iteritems = self.timers.items() if six.PY3 else self.timers.iteritems()
        for k, v in iteritems:
            # Skip timers that haven't collected any values
            if not v:
                continue
            v.sort()
            pct_thresh = 90
            count = len(v)
            vmin, vmax = v[0], v[-1]
            mean, vthresh = vmin, vmax

            if count > 1:
                thresh_idx = int(math.floor(pct_thresh / 100.0 * count))
                v = v[:thresh_idx]
                vthresh = v[-1]
                vsum = sum(v)
                mean = vsum / float(len(v))

            self.enqueue("%s%s.mean" % (self.name_timer, k), mean, stime)
            self.enqueue("%s%s.upper" % (self.name_timer, k), vmax, stime)
            t = int(pct_thresh)
            self.enqueue("%s%s.upper_%s" % (self.name_timer, k, t), vthresh, stime)
            self.enqueue("%s%s.lower" % (self.name_timer, k), vmin, stime)
            self.enqueue("%s%s.count" % (self.name_timer, k), count, stime)
            self.timers[k] = []
            ret += 1

        return ret

    def enqueue_gauges(self, stime):
        ret = 0
        iteritems = self.gauges.items() if six.PY3 else self.gauges.iteritems()
        for k, v in iteritems:
            self.enqueue("%s%s" % (self.name_gauge, k), v, stime)
            ret += 1
        return ret

    def enqueue_counters(self, stime):
        ret = 0
        iteritems = self.counters.items() if six.PY3 else self.counters.iteritems()
        for k, v in iteritems:
            if self.legacy_namespace:
                stat_rate = "%s%s" % (self.name_legacy_rate, k)
                stat_count = "%s%s" % (self.name_legacy_count, k)
            else:
                stat_rate = "%s%s.rate" % (self.name_counter, k)
                stat_count = "%s%s.count" % (self.name_counter, k)
            self.enqueue(stat_rate, v / self.flush_time, stime)
            self.enqueue(stat_count, v, stime)
            self.counters[k] = 0
            ret += 1
        return ret

    def handle(self, data):
        # Adding a bit of extra sauce so clients can
        # send multiple samples in a single UDP
        # packet.
        for line in data.splitlines():
            self.line = line
            if not line.strip():
                continue
            self.handle_line(line)

    def handle_line(self, line):
        bits = line.split(":")
        key = self.handle_key(bits.pop(0))

        if not bits:
            self.bad_line()
            return

        # I'm not sure if statsd is doing this on purpose
        # but the code allows for name:v1|t1:v2|t2 etc etc.
        # In the interest of compatibility, I'll maintain
        # the behavior.
        for sample in bits:
            if "|" not in sample:
                self.bad_line()
                continue
            fields = sample.split("|")
            if fields[1] == "ms":
                self.handle_timer(key, fields)
            elif fields[1] == "g":
                self.handle_gauge(key, fields)
            else:
                self.handle_counter(key, fields)

    def handle_key(self, key):
        for (rexp, repl) in self.key_res:
            key = rexp.sub(repl, key)
        return key

    def handle_timer(self, key, fields):
        try:
            val = float(fields[0] or 0)
            with self.lock:
                self.timers.setdefault(key, []).append(val)
        except:
            self.bad_line()

    def handle_gauge(self, key, fields):
        valstr = fields[0] or "0"
        try:
            val = float(valstr)
        except:
            self.bad_line()
            return
        delta = valstr[0] in ["+", "-"]
        with self.lock:
            if delta and key in self.gauges:
                self.gauges[key] = self.gauges[key] + val
            else:
                self.gauges[key] = val

    def handle_counter(self, key, fields):
        rate = 1.0
        if len(fields) > 2 and fields[2][:1] == "@":
            try:
                rate = float(fields[2][1:].strip())
            except:
                rate = 1.0
        try:
            val = int(float(fields[0] or 0) / rate)
        except:
            self.bad_line()
            return
        with self.lock:
            if key not in self.counters:
                self.counters[key] = 0
            self.counters[key] += val

    def bad_line(self):
        log.error("StatsD: Invalid line: '%s'", self.line.strip())


class StatsDServer(udpserver.UDPServer):
    def __init__(self, queue, cfg):
        super(StatsDServer, self).__init__(cfg.statsd_ip, cfg.statsd_port)
        self.handler = StatsDHandler(queue, cfg)

    def run(self):
        self.handler.start()
        super(StatsDServer, self).run()

    if six.PY3:
        def handle(self, data, addr):
            self.handler.handle(data.decode())
            if not self.handler.is_alive():
                return False
            return True
    else:
        def handle(self, data, addr):
            self.handler.handle(data)
            if not self.handler.is_alive():
                return False
            return True

########NEW FILE########
__FILENAME__ = udpserver
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import six
import sys
import socket
import logging
import multiprocessing

import bucky.cfg as cfg

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        pass


log = logging.getLogger(__name__)


class UDPServer(multiprocessing.Process):
    def __init__(self, ip, port):
        super(UDPServer, self).__init__()
        self.daemon = True
        addrinfo = socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_DGRAM)
        af, socktype, proto, canonname, addr = addrinfo[0]
        ip, port = addr[:2]
        self.ip = ip
        self.port = port
        self.sock = socket.socket(af, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((ip, port))
            log.info("Bound socket socket %s:%s", ip, port)
        except Exception:
            log.exception("Error binding socket %s:%s.", ip, port)
            sys.exit(1)

        self.sock_recvfrom = self.sock.recvfrom
        if cfg.debug:
            # When in debug mode replace the send and recvfrom functions to include
            # debug logging. In production mode these calls have quite a lot of overhead
            # for statements that will never do anything.
            import functools

            def debugsend(f):
                @functools.wraps(f)
                def wrapper(*args, **kwargs):
                    log.debug("Sending UDP packet to %s:%s", self.ip, self.port)
                    return f(*args, **kwargs)
                return wrapper
            self.send = debugsend(self.send)

            def debugrecvfrom(*args, **kwargs):
                data, addr = self.sock.recvfrom(65535)
                log.debug("Received UDP packet from %s:%s" % addr)
                return data, addr
            self.sock_recvfrom = debugrecvfrom

    def run(self):
        setproctitle("bucky: %s" % self.__class__.__name__)
        recvfrom = self.sock_recvfrom
        while True:
            data, addr = recvfrom(65535)
            addr = addr[:2]  # for compatibility with longer ipv6 tuples
            if data == b'EXIT':
                return
            if not self.handle(data, addr):
                return

    def handle(self, data, addr):
        raise NotImplemented()

    def close(self):
        self.send('EXIT')

    if six.PY3:
        def send(self, data):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if not isinstance(data, bytes):
                data = data.encode()
            sock.sendto(data, 0, (self.ip, self.port))
    else:
        def send(self, data):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(data, 0, (self.ip, self.port))

########NEW FILE########
__FILENAME__ = bucky
#!/usr/bin/env python

import bucky.main

if __name__ == '__main__':
    bucky.main.main()


########NEW FILE########
__FILENAME__ = 000-test-bucky
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import os
import threading

import t

from bucky import cfg
from bucky.main import Bucky
from bucky.errors import BuckyError


def test_version_number():
    from bucky import version_info, __version__
    t.eq(__version__, ".".join(map(str, version_info)))


def test_sigterm_handling():
    alarm_thread = threading.Timer(2, os.kill, (os.getpid(), 15))
    alarm_thread.start()
    bucky = Bucky(cfg)
    t.not_raises(BuckyError, bucky.run)

########NEW FILE########
__FILENAME__ = 001-test-statsd
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import t
import bucky.statsd


def test_make_name():
    assert bucky.statsd.make_name(["these", "are", "some", "parts"]) == "these.are.some.parts."
    assert bucky.statsd.make_name(["these", "are", None, "parts"]) == "these.are.parts."
    assert bucky.statsd.make_name(["these", "are", None, ""]) == "these.are."


@t.set_cfg("statsd_flush_time", 0.5)
@t.set_cfg("statsd_port", 8126)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_simple_counter(q, s):
    s.send("gorm:1|c")
    t.same_stat(None, "stats.gorm", 2, q.get())
    t.same_stat(None, "stats_counts.gorm", 1, q.get())
    t.same_stat(None, "stats.numStats", 1, q.get())


@t.set_cfg("statsd_flush_time", 0.5)
@t.set_cfg("statsd_port", 8127)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_multiple_messages(q, s):
    s.send("gorm:1|c")
    s.send("gorm:1|c")
    t.same_stat(None, "stats.gorm", 4, q.get())
    t.same_stat(None, "stats_counts.gorm", 2, q.get())
    t.same_stat(None, "stats.numStats", 1, q.get())


@t.set_cfg("statsd_flush_time", 0.5)
@t.set_cfg("statsd_port", 8128)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_larger_count(q, s):
    s.send("gorm:5|c")
    t.same_stat(None, "stats.gorm", 10, q.get())
    t.same_stat(None, "stats_counts.gorm", 5, q.get())
    t.same_stat(None, "stats.numStats", 1, q.get())


@t.set_cfg("statsd_flush_time", 0.5)
@t.set_cfg("statsd_port", 8129)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_multiple_counters(q, s):
    s.send("gorm:1|c")
    s.send("gurm:1|c")
    stats = {
        "stats.gorm": 2,
        "stats_counts.gorm": 1,
        "stats.gurm": 2,
        "stats_counts.gurm": 1
    }
    for i in range(4):
        stat = q.get()
        t.isin(stat[1], stats)
        t.eq(stats[stat[1]], stat[2])
        t.gt(stat[2], 0)
        stats.pop(stat[1])
    t.same_stat(None, "stats.numStats", 2, q.get())


@t.set_cfg("statsd_flush_time", 0.5)
@t.set_cfg("statsd_port", 8130)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_simple_timer(q, s):
    for i in range(9):
        s.send("gorm:1|ms")
    s.send("gorm:2|ms")
    t.same_stat(None, "stats.timers.gorm.mean", 1, q.get())
    t.same_stat(None, "stats.timers.gorm.upper", 2, q.get())
    t.same_stat(None, "stats.timers.gorm.upper_90", 1, q.get())
    t.same_stat(None, "stats.timers.gorm.lower", 1, q.get())
    t.same_stat(None, "stats.timers.gorm.count", 10, q.get())
    t.same_stat(None, "stats.numStats", 1, q.get())


@t.set_cfg("statsd_flush_time", 0.5)
@t.set_cfg("statsd_port", 8131)
@t.set_cfg("statsd_legacy_namespace", False)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_simple_counter_not_legacy_namespace(q, s):
    s.send("gorm:1|c")
    t.same_stat(None, "stats.counters.gorm.rate", 2, q.get())
    t.same_stat(None, "stats.counters.gorm.count", 1, q.get())
    t.same_stat(None, "stats.numStats", 1, q.get())


@t.set_cfg("statsd_flush_time", 0.5)
@t.udp_srv(bucky.statsd.StatsDServer)
def test_simple_gauge(q, s):
    s.send("gorm:5|g")
    t.same_stat(None, "stats.gauges.gorm", 5, q.get())
    t.same_stat(None, "stats.numStats", 1, q.get())

########NEW FILE########
__FILENAME__ = 002-test-collectd
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import os
import time
import struct
try:
    import queue
except ImportError:
    import Queue as queue

import t
import bucky.collectd
from bucky import cfg
from bucky.errors import ProtocolError, ConfigError


def pkts(rfname):
    fname = os.path.join(os.path.dirname(__file__), rfname)
    with open(fname, 'rb') as handle:
        length = handle.read(2)
        while length:
            (dlen,) = struct.unpack("!H", length)
            yield handle.read(dlen)
            length = handle.read(2)


def test_pkt_reader():
    for pkt in pkts("collectd.pkts"):
        t.ne(len(pkt), 0)


@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_counter_old(q, s):
    s.send(next(pkts("collectd.pkts")))
    time.sleep(.1)
    s = q.get(True, .1)
    while s:
        print(s)
        try:
            s = q.get(True, .1)
        except queue.Empty:
            break


def cdtypes(typesdb):
    def types_dec(func):
        filename = t.temp_file(typesdb)
        return t.set_cfg("collectd_types", [filename])(func)
    return types_dec


def authfile(data):
    def authfile_dec(func):
        filename = t.temp_file(data)
        return t.set_cfg("collectd_auth_file", filename)(func)
    return authfile_dec


def send_get_data(q, s, datafile):
    for pkt in pkts(datafile):
        s.send(pkt)
    time.sleep(.1)
    while True:
        try:
            sample = q.get(True, .1)
        except queue.Empty:
            break
        yield sample


def check_samples(samples, seq_function, count, name):
    i = 0
    for sample in samples:
        if sample[1] != name:
            continue
        t.eq(sample[2], seq_function(i))
        i += 1
    t.eq(i, count)


TDB_GAUGE = "gauge value:GAUGE:U:U\n"
TDB_DERIVE = "derive value:DERIVE:U:U\n"
TDB_COUNTER = "counter value:COUNTER:U:U\n"
TDB_ABSOLUTE = "absolute value:ABSOLUTE:U:U\n"
TYPESDB = TDB_GAUGE + TDB_DERIVE + TDB_COUNTER + TDB_ABSOLUTE


@cdtypes(TYPESDB)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_gauge(q, s):
    # raw values sent are i^2 for i in [0, 9]
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: i ** 2
    check_samples(samples, seq, 10, 'test.squares.gauge')


@cdtypes(TYPESDB)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_derive(q, s):
    # raw values sent are i^2 for i in [0, 9]
    # (i+1)^2-i^2=2*i+1, devided by 2 (time interval)
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: (2 * i + 1) / 2.
    check_samples(samples, seq, 9, 'test.squares.derive')


@cdtypes(TYPESDB)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_counter(q, s):
    # raw values sent are i^2 for i in [0, 9]
    # (i+1)^2-i^2=2*i+1, devided by 2 (time interval)
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: (2 * i + 1) / 2.
    check_samples(samples, seq, 9, 'test.squares.counter')


@cdtypes("counters a:COUNTER:0:U, b:COUNTER:0:U\n")
@t.udp_srv(bucky.collectd.CollectDServer)
def test_counter_wrap_32(q, s):
    # counter growing 1024 per measurement, 2 seconds interval, expecting
    # 9 measurements with value 512
    samples = send_get_data(q, s, 'collectd-counter-wraps.pkts')
    seq = lambda i: 512
    check_samples(samples, seq, 9, 'test.counter-wraps.counters.a')


@cdtypes("counters a:COUNTER:0:U, b:COUNTER:0:U\n")
@t.udp_srv(bucky.collectd.CollectDServer)
def test_counter_wrap_64(q, s):
    # counter growing 1024 per measurement, 2 seconds interval, expecting
    # 9 measurements with value 512
    samples = send_get_data(q, s, 'collectd-counter-wraps.pkts')
    seq = lambda i: 512
    check_samples(samples, seq, 9, 'test.counter-wraps.counters.b')


@cdtypes(TYPESDB)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_absolute(q, s):
    # raw values sent are i^2 for i in [0, 9], devided by 2 (time interval)
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: (i + 1) ** 2 / 2.
    check_samples(samples, seq, 9, 'test.squares.absolute')


@cdtypes("gauge value:GAUGE:5:50\n" + TDB_DERIVE + TDB_COUNTER + TDB_ABSOLUTE)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_gauge_bounds(q, s):
    # raw values sent are i^2 for i in [0, 9]
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: (i + 3) ** 2
    check_samples(samples, seq, 5, 'test.squares.gauge')


@cdtypes("derive value:DERIVE:3:8\n" + TDB_GAUGE + TDB_COUNTER + TDB_ABSOLUTE)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_derive_bounds(q, s):
    # raw values sent are i^2 for i in [0, 9]
    # (i+1)^2-i^2=2*i+1, devided by 2 (time interval)
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: 3 + (2 * i + 1) / 2.
    check_samples(samples, seq, 5, 'test.squares.derive')


@cdtypes("counter value:COUNTER:3:8\n" + TDB_GAUGE + TDB_DERIVE + TDB_ABSOLUTE)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_counter_bounds(q, s):
    # raw values sent are i^2 for i in [0, 9]
    # (i+1)^2-i^2=2*i+1, devided by 2 (time interval)
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: 3 + (2 * i + 1) / 2.
    check_samples(samples, seq, 5, 'test.squares.counter')


@cdtypes("absolute value:ABSOLUTE:5:35\n" + TDB_GAUGE + TDB_DERIVE + TDB_COUNTER)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_simple_absolute_bounds(q, s):
    # raw values sent are i^2 for i in [0, 9], devided by 2 (time interval)
    samples = send_get_data(q, s, 'collectd-squares.pkts')
    seq = lambda i: (i + 4) ** 2 / 2.
    check_samples(samples, seq, 5, 'test.squares.absolute')


@t.set_cfg("collectd_security_level", 1)
@authfile("alice: 12345678")
@cdtypes(TYPESDB)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_net_auth(q, s):
    samples = send_get_data(q, s, 'collectd-squares-signed.pkts')
    seq = lambda i: (i ** 2)
    check_samples(samples, seq, 10, 'test.squares.gauge')


@t.set_cfg("collectd_security_level", 2)
@authfile("alice: 12345678")
@cdtypes(TYPESDB)
@t.udp_srv(bucky.collectd.CollectDServer)
def test_net_enc(q, s):
    samples = send_get_data(q, s, 'collectd-squares-encrypted.pkts')
    seq = lambda i: (i ** 2)
    check_samples(samples, seq, 10, 'test.squares.gauge')


def cfg_crypto(sec_level, auth_file):
    sec_level_dec = t.set_cfg('collectd_security_level', sec_level)
    auth_file_dec = authfile(auth_file)
    return sec_level_dec(auth_file_dec(bucky.collectd.CollectDCrypto))(cfg)


def assert_crypto(state, testfile, sec_level, auth_file):
    crypto = cfg_crypto(sec_level, auth_file)
    i = 0
    if state:
        for data in pkts(testfile):
            data = crypto.parse(data)
            t.eq(bool(data), True)
            i += 1
    else:
        for data in pkts(testfile):
            t.raises(ProtocolError, crypto.parse, data)
            i += 1
    t.eq(i, 2)


def test_crypto_sec_level_0():
    assert_crypto(True, 'collectd-squares.pkts', 0, "")
    assert_crypto(True, 'collectd-squares-signed.pkts', 0, "")
    assert_crypto(False, 'collectd-squares-encrypted.pkts', 0, "")
    assert_crypto(True, 'collectd-squares.pkts', 0, "alice: 12345678")
    assert_crypto(True, 'collectd-squares-signed.pkts', 0, "alice: 12345678")
    assert_crypto(True, 'collectd-squares-encrypted.pkts', 0, "alice: 12345678")


def test_crypto_sec_level_1():
    t.raises(ConfigError, cfg_crypto, 1, "")
    assert_crypto(False, 'collectd-squares.pkts', 1, "bob: 123")
    assert_crypto(False, 'collectd-squares-signed.pkts', 1, "bob: 123")
    assert_crypto(False, 'collectd-squares-encrypted.pkts', 1, "bob: 123")
    assert_crypto(False, 'collectd-squares.pkts', 1, "alice: 12345678")
    assert_crypto(True, 'collectd-squares-signed.pkts', 1, "alice: 12345678")
    assert_crypto(True, 'collectd-squares-encrypted.pkts', 1, "alice: 12345678")


def test_crypto_sec_level_2():
    t.raises(ConfigError, cfg_crypto, 2, "")
    assert_crypto(False, 'collectd-squares.pkts', 2, "bob: 123")
    assert_crypto(False, 'collectd-squares-signed.pkts', 2, "bob: 123")
    assert_crypto(False, 'collectd-squares-encrypted.pkts', 2, "bob: 123")
    assert_crypto(False, 'collectd-squares.pkts', 2, "alice: 12345678")
    assert_crypto(False, 'collectd-squares-signed.pkts', 2, "alice: 12345678")
    assert_crypto(True, 'collectd-squares-encrypted.pkts', 2, "alice: 12345678")


def test_crypto_auth_load():
    auth_file = "alice: 123\nbob:456  \n\n  charlie  :  789"
    crypto = cfg_crypto(2, auth_file)
    db = {"alice": "123", "bob": "456", "charlie": "789"}
    t.eq(crypto.auth_db, db)


def test_crypto_auth_reload():
    crypto = cfg_crypto(1, "bob: 123\n")
    signed_pkt = next(pkts('collectd-squares-signed.pkts'))
    enc_pkt = next(pkts('collectd-squares-encrypted.pkts'))
    t.raises(ProtocolError, crypto.parse, signed_pkt)
    t.raises(ProtocolError, crypto.parse, enc_pkt)
    with open(crypto.auth_file, "a") as f:
        f.write("alice: 12345678\n")
    time.sleep(.1)
    t.eq(bool(crypto.parse(signed_pkt)), True)
    t.eq(bool(crypto.parse(enc_pkt)), True)

########NEW FILE########
__FILENAME__ = 003-test-processor
import time
import multiprocessing
from functools import wraps

try:
    import queue
except ImportError:
    import Queue as queue

import t
import bucky.processor
import bucky.cfg as cfg
cfg.debug = True


def processor(func):
    @wraps(func)
    def run():
        inq = multiprocessing.Queue()
        outq = multiprocessing.Queue()
        proc = bucky.processor.CustomProcessor(inq, outq, cfg)
        proc.start()
        try:
            func(inq, outq, proc)
        finally:
            inq.put(None)
            dead = False
            for i in range(5):
                if not proc.is_alive():
                    dead = True
                    break
                time.sleep(0.1)
            if not dead:
                proc.terminate()
    return run


def get_simple_data(times=100):
    data = []
    for i in range(times):
        host = "tests.host-%d" % i
        name = "metric-%d" % i
        value = i
        timestamp = int(time.time() + i)
        data.append((host, name, value, timestamp))
    return data


def send_get_data(indata, inq, outq):
    for sample in indata:
        inq.put(sample)
    while True:
        try:
            sample = outq.get(True, 1.5)
        except queue.Empty:
            break
        yield sample


def identity(host, name, val, time):
    return host, name, val, time


@t.set_cfg("processor", identity)
@processor
def test_start_stop(inq, outq, proc):
    t.eq(proc.is_alive(), True)
    inq.put(None)
    time.sleep(0.5)
    t.eq(proc.is_alive(), False)


@t.set_cfg("processor", identity)
@processor
def test_plumbing(inq, outq, proc):
    data = get_simple_data(100)
    i = 0
    for sample in send_get_data(data, inq, outq):
        t.eq(sample, data[i])
        i += 1
    t.eq(i, 100)


def filter_even(host, name, val, timestamp):
    if not val % 2:
        return None
    return host, name, val, timestamp


@t.set_cfg("processor", filter_even)
@processor
def test_filter(inq, outq, proc):
    data = get_simple_data(100)
    i = 0
    for sample in send_get_data(data, inq, outq):
        t.eq(sample[2] % 2, 1)
        i += 1
    t.eq(i, 50)


def raise_error(host, name, val, timestamp):
    raise Exception()


@t.set_cfg("processor", raise_error)
@processor
def test_function_error(inq, outq, proc):
    data = get_simple_data(100)
    i = 0
    for sample in send_get_data(data, inq, outq):
        t.eq(sample, data[i])
        i += 1
    t.eq(proc.is_alive(), True)
    t.eq(i, 100)


@t.set_cfg("processor", raise_error)
@t.set_cfg("processor_drop_on_error", True)
@processor
def test_function_error_drop(inq, outq, proc):
    data = get_simple_data(100)
    samples = list(send_get_data(data, inq, outq))
    t.eq(proc.is_alive(), True)
    t.eq(len(samples), 0)

########NEW FILE########
__FILENAME__ = 004-test-helpers
import time

import t
import bucky.helpers


def test_file_monitor():
    path = t.temp_file('asd')
    monitor = bucky.helpers.FileMonitor(path)
    t.eq(monitor.modified(), False)
    with open(path, 'w') as f:
        f.write('bbbb')
    time.sleep(.1)
    t.eq(monitor.modified(), True)
    t.eq(monitor.modified(), False)

########NEW FILE########
__FILENAME__ = collectd-collector
#!/usr/bin/env python
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.
#
# A simple script to collect some UDP packets from collectd for
# testing.

import socket
import struct
import sys


class LoggingServer(object):
    def __init__(self, ip, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))

    def close(self):
        self.sock.close()

    def run(self, fname):
        with open(fname, "wb") as handle:
            for i in range(25):
                data, addr = self.sock.recvfrom(65535)
                self.write(handle, data)

    def write(self, dst, data):
        length = struct.pack("!H", len(data))
        dst.write(length)
        dst.write(data)


def main():
    ip, port = "127.0.0.1", 25826
    fname = "tests/collectd.pkts"
    if len(sys.argv) >= 2:
        ip = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    if len(sys.argv) >= 4:
        fname = sys.argv[3]
    server = LoggingServer(ip, port)
    try:
        server.run(fname)
    finally:
        server.close()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = t
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

# flake8: noqa

import time
import multiprocessing
from functools import wraps
import tempfile

import bucky.cfg as cfg
cfg.debug = True


class set_cfg(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self, func):
        @wraps(func)
        def run(*args, **kwargs):
            curr = getattr(cfg, self.name)
            try:
                setattr(cfg, self.name, self.value)
                return func(*args, **kwargs)
            finally:
                setattr(cfg, self.name, curr)
        return run


class udp_srv(object):
    def __init__(self, stype):
        self.stype = stype

    def __call__(self, func):
        @wraps(func)
        def run():
            q = multiprocessing.Queue()
            s = self.stype(q, cfg)
            s.start()
            try:
                func(q, s)
            finally:
                s.close()
                if not self.closed(s):
                    raise RuntimeError("Server didn't die.")
        return run

    def closed(self, s):
        for i in range(5):
            if not s.is_alive():
                return True
            time.sleep(0.1)
        return False


def same_stat(host, name, value, stat):
    eq(name, stat[1])
    eq(value, stat[2])
    gt(stat[3], 0)


def eq(a, b):
    assert a == b, "%r != %r" % (a, b)


def ne(a, b):
    assert a != b, "%r == %r" % (a, b)


def lt(a, b):
    assert a < b, "%r >= %r" % (a, b)


def gt(a, b):
    assert a > b, "%r <= %r" % (a, b)


def isin(a, b):
    assert a in b, "%r is not in %r" % (a, b)


def isnotin(a, b):
    assert a not in b, "%r is in %r" % (a, b)


def has(a, b):
    assert hasattr(a, b), "%r has no attribute %r" % (a, b)


def hasnot(a, b):
    assert not hasattr(a, b), "%r has an attribute %r" % (a, b)


def istype(a, b):
    assert isinstance(a, b), "%r is not an instance of %r" % (a, b)


def raises(exctype, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exctype:
        return
    func_name = getattr(func, "__name__", "<builtin_function>")
    raise AssertionError("Function %s did not raise %s" % (func_name, exctype.__name__))


def not_raises(exctype, func, *args, **kwargs):
    try:
        ret = func(*args, **kwargs)
    except exctype as exc:
        func_name = getattr(func, "__name__", "<builtin_function>")
        raise AssertionError("Function %s raised %s: %s" % (func_name,
                                                            exctype.__name__,
                                                            exc))


def temp_file(data):
    f = tempfile.NamedTemporaryFile(delete=False)
    filename = f.name
    f.write(data.encode('utf-8'))
    f.close()
    return filename

########NEW FILE########
