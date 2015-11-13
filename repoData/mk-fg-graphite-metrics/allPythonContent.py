__FILENAME__ = cgacct
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from collections import deque
from contextlib import contextmanager
from io import open
import os, re, dbus, fcntl, stat

from . import Collector, Datapoint, user_hz, dev_resolve

import logging
log = logging.getLogger(__name__)


class CGAcct(Collector):


	def __init__(self, *argz, **kwz):
		super(CGAcct, self).__init__(*argz, **kwz)

		self.stuck_list = os.path.join(self.conf.cg_root, 'sticky.cgacct')

		# Check which info is available, if any
		self.rc_collectors = list()
		for rc in self.conf.resource_controllers:
			try: rc_collector = getattr(self, rc)
			except AttributeError:
				log.warn( 'Unable to find processor'
					' method for rc {!r} metrics, skipping it'.format(rc) )
				continue
			rc_path = os.path.join(self.conf.cg_root, rc)
			if not os.path.ismount(rc_path + '/'):
				log.warn(( 'Specified rc path ({}) does not'
					' seem to be a mountpoint, skipping it' ).format(rc_path))
				continue
			log.debug('Using cgacct collector for rc: {}'.format(rc))
			self.rc_collectors.append(rc_collector)

		if not self.rc_collectors: # no point doing anything else
			log.info('No cgroup rcs to poll (rc_collectors), disabling collector')
			self.conf.enabled = False
			return

		# List of cgroup sticky bits, set by this service
		self._stuck_list_file = open(self.stuck_list, 'ab+')
		self._stuck_list = dict()
		fcntl.lockf(self._stuck_list_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
		self._stuck_list_file.seek(0)
		for line in self._stuck_list_file:
			rc, svc = line.strip().split()
			if rc not in self._stuck_list: self._stuck_list[rc] = set()
			self._stuck_list[rc].add(svc)


	def _cg_svc_dir(self, rc, svc=None):
		path = os.path.join(self.conf.cg_root, rc)
		if not svc: return path
		svc = svc.rsplit('@', 1)
		return os.path.join(path, 'system/{}.service'.format(svc[0] + '@'), svc[1])\
			if len(svc) > 1 else os.path.join(path, 'system/{}.service'.format(svc[0]))

	def _cg_svc_metrics(self, rc, metric, svc_instances):
		return (os.path.join( self._cg_svc_dir(rc, svc),
			'{}.{}'.format(rc, metric) ) for svc in svc_instances)

	@contextmanager
	def _cg_metric(self, path, **kwz):
		try:
			with open(path, mode='rb', **kwz) as src: yield src
		except (OSError, IOError) as err:
			log.debug('Failed to open cgroup metric: {}'.format(path, err))
			raise

	@staticmethod
	def _svc_name(svc): return svc.replace('@', '').replace('.', '_')


	@staticmethod
	def _systemd_services():
		for unit in dbus.Interface( dbus.SystemBus().get_object(
					'org.freedesktop.systemd1', '/org/freedesktop/systemd1' ),
				'org.freedesktop.systemd1.Manager' ).ListUnits():
			name, state = it.imap(str, op.itemgetter(0, 4)(unit))
			if name.endswith('.service') and state in ('running', 'start'): yield name[:-8]

	def _systemd_cg_stick(self, rc, services):
		if rc not in self._stuck_list: self._stuck_list[rc] = set()
		stuck_update, stuck = False, set(self._stuck_list[rc])
		services = set(services) # will be filtered and returned
		# Process services, make their cgroups persistent
		for svc in list(services):
			if svc not in stuck:
				svc_tasks = os.path.join(self._cg_svc_dir(rc, svc), 'tasks')
				try:
					os.chmod( svc_tasks,
						stat.S_IMODE(os.stat(svc_tasks).st_mode) | stat.S_ISVTX )
				except OSError: services.discard(svc) # not running
				else:
					self._stuck_list[rc].add(svc)
					stuck_update = True
			else: stuck.remove(svc) # to exclude it from the cleanup loop
		# Process stuck cgroups for removed services,
		#  try dropping these, otherwise just unstick and forget
		for svc in stuck:
			svc_dir = self._cg_svc_dir(rc, svc)
			try: os.rmdir(svc_dir)
			except OSError:
				log.debug( 'Non-empty cgroup for'
					' not-running service ({}): {}'.format(svc, svc_dir) )
				svc_tasks = os.path.join(svc_dir, 'tasks')
				try:
					os.chmod( svc_tasks,
						stat.S_IMODE(os.stat(svc_tasks).st_mode) & ~stat.S_ISVTX )
				except OSError:
					log.debug('Failed to unstick cgroup tasks file: {}'.format(svc_tasks))
			self._stuck_list[rc].remove(svc)
			stuck_update = True
		# Save list updates, if any
		if stuck_update:
			self._stuck_list_file.seek(0)
			self._stuck_list_file.truncate()
			for rc, stuck in self._stuck_list.viewitems():
				for svc in stuck: self._stuck_list_file.write('{} {}\n'.format(rc, svc))
			self._stuck_list_file.flush()
		return services

	_systemd_sticky_instances = lambda self, rc, services: (
		(self._svc_name(svc), list(svc_instances))
		for svc, svc_instances in it.groupby(
			sorted(set(services).intersection(self._systemd_cg_stick(rc, services))),
			key=lambda k: (k.rsplit('@', 1)[0]+'@' if '@' in k else k) ) )


	def cpuacct( self, services,
			_name = 'processes.services.{}.cpu.{}'.format,
			_stats=('user', 'system') ):
		## "stats" counters (user/system) are reported in USER_HZ - 1/Xth of second
		##  yielded values are in seconds, so counter should have 0-1 range,
		##  when divided by the interval
		## Not parsed: usage (should be sum of percpu)
		for svc, svc_instances in self._systemd_sticky_instances('cpuacct', services):
			if svc == 'total':
				log.warn('Detected service name conflict with "total" aggregation')
				continue
			# user/system jiffies
			stat = dict()
			for path in self._cg_svc_metrics('cpuacct', 'stat', svc_instances):
				try:
					with self._cg_metric(path) as src:
						for name, val in (line.strip().split() for line in src):
							if name not in _stats: continue
							try: stat[name] += int(val)
							except KeyError: stat[name] = int(val)
				except (OSError, IOError): pass
			for name in _stats:
				if name not in stat: continue
				yield Datapoint( _name(svc, name),
					'counter', float(stat[name]) / user_hz, None )
			# usage clicks
			usage = None
			for path in self._cg_svc_metrics('cpuacct', 'usage', svc_instances):
				try:
					with self._cg_metric(path) as src:
						usage = (0 if usage is None else usage) + int(src.read().strip())
				except (OSError, IOError): pass
			if usage is not None:
				yield Datapoint(_name(svc, 'usage'), 'counter', usage, None)


	@staticmethod
	def _iostat(pid, _conv=dict( read_bytes=('r', 1),
			write_bytes=('w', 1), cancelled_write_bytes=('w', -1),
			syscr=('rc', 1), syscw=('wc', 1) )):
		res = dict()
		for line in open('/proc/{}/io'.format(pid), 'rb'):
			line = line.strip()
			if not line: continue
			try: name, val = line.split(':', 1)
			except ValueError:
				log.warn('Unrecognized line format in proc/{}/io: {!r}'.format(pid, line))
				continue
			try: k,m = _conv[name]
			except KeyError: continue
			if k not in res: res[k] = 0
			res[k] += int(val.strip()) * m
		try: res = op.itemgetter('r', 'w', 'rc', 'wc')(res)
		except KeyError:
			raise OSError('Incomplete IO data for pid {}'.format(pid))
		# comm is used to make sure it's the same process
		return open('/proc/{}/comm'.format(pid), 'rb').read(), res

	@staticmethod
	def _read_ids(src):
		return set(it.imap(int, it.ifilter( None,
			it.imap(str.strip, src.readlines()) )))

	def blkio( self, services,
			_caches=deque([dict()], maxlen=2),
			_re_line = re.compile( r'^(?P<dev>\d+:\d+)\s+'
				r'(?P<iotype>Read|Write)\s+(?P<count>\d+)$' ),
			_name = 'processes.services.{}.io.{}'.format ):
		# Caches are for syscall io
		cache_prev = _caches[-1]
		cache_update = dict()

		for svc, svc_instances in self._systemd_sticky_instances('blkio', services):

			## Block IO
			## Only reads/writes are accounted, sync/async is meaningless now,
			##  because only sync ops are counted anyway
			svc_io = dict()
			for metric, src in [ ('bytes', 'io_service_bytes'),
					('time', 'io_service_time'), ('ops', 'io_serviced') ]:
				dst = svc_io.setdefault(metric, dict())
				for path in self._cg_svc_metrics('blkio', src, svc_instances):
					try:
						with self._cg_metric(path) as src:
							for line in src:
								match = _re_line.search(line.strip())
								if not match: continue # "Total" line, empty line
								dev = dev_resolve(*map(int, match.group('dev').split(':')))
								if dev is None: continue
								dev = dst.setdefault(dev, dict())
								iotype, val = match.group('iotype').lower(), int(match.group('count'))
								if iotype not in dev: dev[iotype] = val
								else: dev[iotype] += val
					except (OSError, IOError): pass
			for metric, devs in svc_io.viewitems():
				for dev, vals in devs.viewitems():
					if {'read', 'write'} != frozenset(vals):
						log.warn('Unexpected IO counter types: {}'.format(vals))
						continue
					for k,v in vals.viewitems():
						if not v: continue # no point writing always-zeroes for most devices
						yield Datapoint(_name( svc,
							'blkio.{}.{}_{}'.format(dev, metric, k) ), 'counter', v, None)

			## Syscall IO
			## Counters from blkio seem to be less useful in general,
			##  so /proc/*/io stats are collected for all processes in cgroup
			## Should be very inaccurate if pids are respawning
			tids, pids = set(), set()
			for base in it.imap(ft.partial(
					self._cg_svc_dir, 'blkio' ), svc_instances):
				try:
					with self._cg_metric(os.path.join(base, 'tasks')) as src:
						tids.update(self._read_ids(src)) # just to count them
					with self._cg_metric(os.path.join(base, 'cgroup.procs')) as src:
						pids.update(self._read_ids(src))
				except (OSError, IOError): continue
			# Process/thread count - only collected here
			yield Datapoint( 'processes.services.'
				'{}.threads'.format(svc), 'gauge', len(tids), None)
			yield Datapoint( 'processes.services.'
				'{}.processes'.format(svc), 'gauge', len(pids), None )

			# Actual io metrics
			svc_update = list()
			for pid in pids:
				try: comm, res = self._iostat(pid)
				except (OSError, IOError): continue
				svc_update.append(((svc, pid, comm), res))
			delta_total = list(it.repeat(0, 4))
			for k,res in svc_update:
				try: delta = map(op.sub, res, cache_prev[k])
				except KeyError: continue
				delta_total = map(op.add, delta, delta_total)
			for k,v in it.izip(['bytes_read', 'bytes_write', 'ops_read', 'ops_write'], delta_total):
				yield Datapoint(_name(svc, k), 'gauge', v, None)
			cache_update.update(svc_update)
		_caches.append(cache_update)


	def memory( self, services,
			_name = 'processes.services.{}.memory.{}'.format ):
		for svc, svc_instances in self._systemd_sticky_instances('memory', services):
			vals = dict()

			for path in self._cg_svc_metrics('memory', 'stat', svc_instances):
				try:
					with self._cg_metric(path) as src:
						for line in src:
							name, val = line.strip().split()
							if not name.startswith('total_'): continue
							name = name[6:]
							val, k = int(val), ( _name(svc, name),
								'gauge' if not name.startswith('pg') else 'counter' )
							if k not in vals: vals[k] = val
							else: vals[k] += val
				except (OSError, IOError): pass

			for prefix in None, 'kmem', 'memsw':
				k = '{}.usage_in_bytes' if prefix else 'usage_in_bytes'
				name = 'usage'
				if prefix: name += '_' + prefix
				for path in self._cg_svc_metrics('memory', k, svc_instances):
					try:
						with self._cg_metric(path) as src:
							vals[_name(svc, name), 'gauge'] = int(src.read().strip())
					except (OSError, IOError): pass

			for (name, val_type), val in vals.viewitems():
				yield Datapoint(name, val_type, val, None)


	def read(self):
		services = list(self._systemd_services())
		for dp in it.chain.from_iterable(
			func(services) for func in self.rc_collectors ): yield dp


collector = CGAcct

########NEW FILE########
__FILENAME__ = cjdns_peer_stats
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from io import open
from hashlib import sha256, sha512
from base64 import b32decode
from collections import defaultdict
import os, sys, json, socket, time, types
from . import Collector, Datapoint

from bencode import bencode, bdecode

import logging
log = logging.getLogger(__name__)


def pubkey_to_ipv6(key,
		_cjdns_b32_map = [ # directly from util/Base32.h
			99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,
			99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,
			99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,
			0, 1, 2, 3, 4, 5, 6, 7, 8, 9,99,99,99,99,99,99,
			99,99,10,11,12,99,13,14,15,99,16,17,18,19,20,99,
			21,22,23,24,25,26,27,28,29,30,31,99,99,99,99,99,
			99,99,10,11,12,99,13,14,15,99,16,17,18,19,20,99,
			21,22,23,24,25,26,27,28,29,30,31,99,99,99,99,99 ]):
	if key.endswith('.k'): key = key[:-2]

	bits, byte, res = 0, 0, list()
	for c in key:
		n = _cjdns_b32_map[ord(c)]
		if n > 31: raise ValueError('Invalid key: {!r}, char: {!r}'.format(key, n))
		byte |= n << bits
		bits += 5
		if bits >= 8:
			bits -= 8
			res.append(chr(byte & 0xff))
			byte >>= 8
	if bits >= 5 or byte:
		raise ValueError('Invalid key length: {!r} (leftover bits: {})'.format(key, bits))
	res = ''.join(res)

	addr = sha512(sha512(res).digest()).hexdigest()[:32]
	if addr[:2] != 'fc':
		raise ValueError( 'Invalid cjdns key (first'
			' addr byte is not 0xfc, addr: {!r}): {!r}'.format(addr, key) )
	return addr


class PeerStatsFailure(Exception):

	def __init__(self, msg, err=None):
		if err is not None: msg += ': {} {}'.format(type(err), err)
		super(PeerStatsFailure, self).__init__(msg)

	def __hash__(self):
		return hash(self.message)


class CjdnsPeerStats(Collector):

	last_err = None
	last_err_count = None # None (pre-init), True (shut-up mode) or int
	last_err_count_max = 3 # max repeated errors to report

	def __init__(self, *argz, **kwz):
		super(CjdnsPeerStats, self).__init__(*argz, **kwz)

		assert self.conf.filter.direction in\
			['any', 'incoming', 'outgoing'], self.conf.filter.direction

		if isinstance(self.conf.peer_id, types.StringTypes):
			self.conf.peer_id = [self.conf.peer_id]

		conf_admin, conf_admin_path = None,\
			os.path.expanduser(self.conf.cjdnsadmin_conf)
		try:
			with open(conf_admin_path) as src: conf_admin = json.load(src)
		except (OSError, IOError) as err:
			log.warn('Unable to open cjdnsadmin config: %s', err)
		except ValueError as err:
			log.warn('Unable to process cjdnsadmin config: %s', err)
		if conf_admin is None:
			log.error('Failed to process cjdnsadmin config, disabling collector')
			self.conf.enabled = False
			return

		sock_addr = conf_admin['addr'], conf_admin['port']
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.settimeout(self.conf.timeout)
		log.debug('Using cjdns socket: {}:{}'.format(*sock_addr))
		self.sock.connect(sock_addr)

		self.admin_password = conf_admin['password']
		self.peer_ipv6_cache = dict()

	def get_stats_page(self, page, password, bs=2**30):
		try:
			self.sock.send(bencode(dict(q='cookie')))
			cookie = bdecode(self.sock.recv(bs))['cookie']
		except Exception as err:
			raise PeerStatsFailure('Failed to get auth cookie', err)

		req = dict( q='auth',
			aq='InterfaceController_peerStats',
			args=dict(page=page),
			hash=sha256('{}{}'.format(password, cookie)).hexdigest(),
			cookie=cookie, txid=os.urandom(5).encode('hex') )
		req['hash'] = sha256(bencode(req)).hexdigest()

		try:
			self.sock.send(bencode(req))
			resp = bdecode(self.sock.recv(bs))
			assert resp.get('txid') == req['txid'], [req, resp]
			return resp['peers'], resp.get('more', False)
		except Exception as err:
			raise PeerStatsFailure('Failure communicating with cjdns', err)

	def get_peer_stats(self):
		peers, page, more = list(), 0, True
		while more:
			stats, more = self.get_stats_page(page, self.admin_password)
			peers.extend(stats)
			page += 1
		return peers

	def read(self):
		try: peers = self.get_peer_stats()
		# PeerStatsFailure errors' reporting is rate-limited
		except PeerStatsFailure as err:
			if hash(err) == hash(self.last_err):
				if self.last_err_count is True: return
				elif self.last_err_count < self.last_err_count_max: self.last_err_count += 1
				else:
					log.warn( 'Failed getting cjdns peer stats:'
						' {} -- disabling reporting of recurring errors'.format(err) )
					self.last_err_count = True
					return
			else: self.last_err, self.last_err_count = err, 1
			log.warn('Failed getting cjdns peer stats: {}'.format(err))
			return
		else:
			if self.last_err_count is True:
				log.warn('Previous recurring failure ({}) was resolved'.format(self.last_err))
				self.last_err = self.last_err_count = None

		# Detect peers with 2 links having different isIncoming
		peers_bidir = dict()
		for peer in peers:
			val = peers_bidir.get(peer['publicKey'])
			if val is False: peers_bidir[peer['publicKey']] = True
			elif val is None: peers_bidir[peer['publicKey']] = False

		ts, peer_states = time.time(), defaultdict(int)
		for peer in peers:
			state = peer['state'].lower()
			peer_states[state] += 1

			# Check filters
			if self.conf.filter.established_only and state != 'established': continue
			if self.conf.filter.direction != 'any':
				if self.conf.filter.direction == 'incoming' and not peer['isIncoming']: continue
				elif self.conf.filter.direction == 'outgoing' and peer['isIncoming']: continue
				else: raise ValueError(self.conf.filter.direction)

			# Generate metric name
			pubkey = peer['publicKey']
			if pubkey.endswith('.k'): pubkey = pubkey[:-2]
			peer['pubkey'] = pubkey
			if 'ipv6' in self.conf.peer_id:
				if pubkey not in self.peer_ipv6_cache:
					self.peer_ipv6_cache[pubkey] = pubkey_to_ipv6(pubkey)
				peer['ipv6'] = self.peer_ipv6_cache[pubkey]
			for k in self.conf.peer_id:
				if k in peer:
					peer_id = peer[k]
					break
			else: raise KeyError(self.conf.peer_id, peer)
			name = '{}.{}.{{}}'.format(self.conf.prefix, peer_id)
			if peers_bidir[peer['publicKey']]:
				name = name.format('incoming_{}' if peer['isIncoming'] else 'outgoing_{}')

			# Per-peer metrics
			name_bytes = name.format('bytes_{}')
			for k, d in [('bytesIn', 'in'), ('bytesOut', 'out')]:
				yield Datapoint(name_bytes.format(d), 'counter', peer[k], ts)
			if self.conf.special_metrics.peer_link:
				link = 1 if state == 'established' else 0
				yield Datapoint(name.format(self.conf.special_metrics.peer_link), 'gauge', link, ts)

		# Common metrics
		if self.conf.special_metrics.count:
			yield Datapoint(self.conf.special_metrics.count, 'gauge', len(peers), ts)
		if self.conf.special_metrics.count_state:
			for k, v in peer_states.viewitems():
				name = '{}.{}'.format(self.conf.special_metrics.count_state, k)
				yield Datapoint(name, 'gauge', v, ts)


collector = CjdnsPeerStats

########NEW FILE########
__FILENAME__ = cron_log
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
import re, iso8601, calendar

from . import Collector, Datapoint

import logging
log = logging.getLogger(__name__)


def file_follow( src, open_tail=True,
		read_interval_min=0.1,
			read_interval_max=20, read_interval_mul=1.1,
		rotation_check_interval=20, yield_file=False, **open_kwz ):
	from time import time, sleep
	from io import open
	import os, types

	open_tail = open_tail and isinstance(src, types.StringTypes)
	src_open = lambda: open(path, mode='rb', **open_kwz)
	stat = lambda f: (os.fstat(f) if isinstance(f, int) else os.stat(f))
	sanity_chk_stats = lambda stat: (stat.st_ino, stat.st_dev)
	sanity_chk_ts = lambda ts=None: (ts or time()) + rotation_check_interval

	if isinstance(src, types.StringTypes): src, path = None, src
	else:
		path = src.name
		src_inode, src_inode_ts =\
			sanity_chk_stats(stat(src.fileno())), sanity_chk_ts()
	line, read_chk = '', read_interval_min

	while True:

		if not src: # (re)open
			src = src_open()
			if open_tail:
				src.seek(0, os.SEEK_END)
				open_tail = False
			src_inode, src_inode_ts =\
				sanity_chk_stats(stat(src.fileno())), sanity_chk_ts()
			src_inode_chk = None

		ts = time()
		if ts > src_inode_ts: # rotation check
			src_inode_chk, src_inode_ts =\
				sanity_chk_stats(stat(path)), sanity_chk_ts(ts)
			if stat(src.fileno()).st_size < src.tell(): src.seek(0) # truncated
		else: src_inode_chk = None

		buff = src.readline()
		if not buff: # eof
			if src_inode_chk and src_inode_chk != src_inode: # rotated
				src.close()
				src, line = None, ''
				continue
			if read_chk is None:
				yield (buff if not yield_file else (buff, src))
			else:
				sleep(read_chk)
				read_chk *= read_interval_mul
				if read_chk > read_interval_max:
					read_chk = read_interval_max
		else:
			line += buff
			read_chk = read_interval_min

		if line and line[-1] == '\n': # complete line
			try:
				val = yield (line if not yield_file else (line, src))
				if val is not None: raise KeyboardInterrupt
			except KeyboardInterrupt: break
			line = ''

	src.close()


def file_follow_durable( path,
		min_dump_interval=10,
		xattr_name='user.collectd.logtail.pos', xattr_update=True,
		**follow_kwz ):
	'''Records log position into xattrs after reading line every
			min_dump_interval seconds.
		Checksum of the last line at the position
			is also recorded (so line itself don't have to fit into xattr) to make sure
			file wasn't truncated between last xattr dump and re-open.'''

	from xattr import xattr
	from io import open
	from hashlib import sha1
	from time import time
	import struct

	# Try to restore position
	src = open(path, mode='rb')
	src_xattr = xattr(src)
	try:
		if not xattr_name: raise KeyError
		pos = src_xattr[xattr_name]
	except KeyError: pos = None
	if pos:
		data_len = struct.calcsize('=I')
		(pos,), chksum = struct.unpack('=I', pos[:data_len]), pos[data_len:]
		(data_len,), chksum = struct.unpack('=I', chksum[:data_len]), chksum[data_len:]
		try:
			src.seek(pos - data_len)
			if sha1(src.read(data_len)).digest() != chksum:
				raise IOError('Last log line doesnt match checksum')
		except (OSError, IOError) as err:
			collectd.info('Failed to restore log position: {}'.format(err))
			src.seek(0)
	tailer = file_follow(src, yield_file=True, **follow_kwz)

	# ...and keep it updated
	pos_dump_ts_get = lambda ts=None: (ts or time()) + min_dump_interval
	pos_dump_ts = pos_dump_ts_get()
	while True:
		line, src_chk = next(tailer)
		if not line: pos_dump_ts = 0 # force-write xattr
		ts = time()
		if ts > pos_dump_ts:
			if src is not src_chk:
				src, src_xattr = src_chk, xattr(src_chk)
			pos_new = src.tell()
			if pos != pos_new:
				pos = pos_new
				if xattr_update:
					src_xattr[xattr_name] =\
						struct.pack('=I', pos)\
						+ struct.pack('=I', len(line))\
						+ sha1(line).digest()
			pos_dump_ts = pos_dump_ts_get(ts)
		if (yield line.decode('utf-8', 'replace')):
			tailer.send(StopIteration)
			break


class CronJobs(Collector):

	lines, aliases = dict(), list()

	def __init__(self, *argz, **kwz):
		super(CronJobs, self).__init__(*argz, **kwz)

		try:
			src, self.lines, self.aliases =\
				op.attrgetter('source', 'lines', 'aliases')(self.conf)
			if not (src and self.lines and self.aliases): raise KeyError()
		except KeyError as err:
			if err.args:
				log.error('Failed to get required config parameter "{}"'.format(err.args[0]))
			else:
				log.warn( 'Collector requires all of "source",'
					' "lines" and "aliases" specified to work properly' )
			self.conf.enabled = False
			return

		for k,v in self.lines.viewitems(): self.lines[k] = re.compile(v)
		for idx,(k,v) in enumerate(self.aliases): self.aliases[idx] = k, re.compile(v)
		self.log_tailer = file_follow_durable( src, read_interval_min=None,
			xattr_name=self.conf.xattr_name, xattr_update=not self.conf.debug.dry_run )

	def read(self, _re_sanitize=re.compile('\s+|-')):
		# Cron
		if self.log_tailer:
			for line in iter(self.log_tailer.next, u''):
				# log.debug('LINE: {!r}'.format(line))
				ts, line = line.strip().split(None, 1)
				ts = calendar.timegm(iso8601.parse_date(ts).utctimetuple())
				matched = False
				for ev, regex in self.lines.viewitems():
					if not regex: continue
					match = regex.search(line)
					if match:
						matched = True
						job = match.group('job')
						for alias, regex in self.aliases:
							group = alias[1:] if alias.startswith('_') else None
							alias_match = regex.search(job)
							if alias_match:
								if group is not None:
									job = _re_sanitize.sub('_', alias_match.group(group))
								else: job = alias
								break
						else:
							log.warn('No alias for cron job: {!r}, skipping'.format(line))
							continue
						try: value = float(match.group('val'))
						except IndexError: value = 1
						# log.debug('TS: {}, EV: {}, JOB: {}'.format(ts, ev, job))
						yield Datapoint('cron.tasks.{}.{}'.format(job, ev), 'gauge', value, ts)
				if not matched:
					log.debug('Failed to match line: {!r}'.format(line))


collector = CronJobs

########NEW FILE########
__FILENAME__ = iptables_counts
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from subprocess import Popen, PIPE
from collections import namedtuple, defaultdict
from io import open
import os, errno

from . import Collector, Datapoint

import logging
log = logging.getLogger(__name__)


class IPTables(Collector):

	iptables = dict(ipv4='iptables-save', ipv6='ip6tables-save') # binaries
	metric_units = metric_tpl = None

	def __init__(self, *argz, **kwz):
		super(IPTables, self).__init__(*argz, **kwz)

		if not self.conf.rule_metrics_path.ipv4\
				and not self.conf.rule_metrics_path.ipv6:
			log.info('No paths for rule_metrics_path specified, disabling collector')
			self.conf.enabled = False

		assert self.conf.units in ['pkt', 'bytes', 'both', 'both_flat']
		if self.conf.units.startswith('both'):
			self.metric_units = ['pkt', 'bytes']
			self.metric_tpl = '{}.{}' if self.conf.units == 'both' else '{}_{}'
		else: self.metric_units, self.metric_tpl = self.conf.units, '{}'


	_rule_metrics = namedtuple('RuleMetrics', 'table path mtime')
	_rule_metrics_cache = dict()

	@property
	def rule_metrics(self):
		rule_metrics = dict()
		for v in 'ipv4', 'ipv6':
			path = self.conf.rule_metrics_path[v]
			try:
				if not path: raise OSError()
				mtime = os.stat(path).st_mtime
			except (OSError, IOError) as err:
				if err.args and err.errno != errno.ENOENT: raise # to raise EPERM, EACCES and such
				self._rule_metrics_cache[v] = None
				continue
			cache = self._rule_metrics_cache.get(v)
			if not cache or path != cache.path or mtime != cache.mtime:
				log.debug('Detected rule_metrics file update: {} (cached: {})'.format(path, cache))
				metrics_table = dict()
				with open(path, 'rb') as src:
					for line in it.imap(op.methodcaller('strip'), src):
						if not line: continue
						table, chain, rule, metric = line.split(None, 3)
						metrics_table[table, chain, int(rule)] = metric
				cache = self._rule_metrics_cache[v]\
					= self._rule_metrics(metrics_table, path, mtime)
			rule_metrics[v] = cache
		return rule_metrics


	_table_hash = dict()

	def read(self):
		metric_counts = dict()
		hashes = defaultdict(lambda: defaultdict(list))

		for v, metrics in self.rule_metrics.viewitems():
			if not metrics: continue

			# Used to detect rule changes
			try:
				hash_old, metrics_old, warnings = self._table_hash[v]
				if metrics is not metrics_old: raise KeyError
			except KeyError: hash_old, warnings = None, dict()
			hash_new = hashes[v]

			# iptables-save invocation and output processing loop
			proc = Popen([self.iptables[v], '-c'], stdout=PIPE)
			chain_counts = defaultdict(int)
			for line in it.imap(op.methodcaller('strip'), proc.stdout):
				if line[0] != '[': # chain/table spec or comment
					if line[0] == '*': table = line[1:]
					continue
				counts, append, chain, rule = line.split(None, 3)
				assert append == '-A'

				rule_key = table, chain
				chain_counts[rule_key] += 1 # iptables rules are 1-indexed
				chain_count = chain_counts[rule_key]
				# log.debug('{}, Rule: {}'.format([table, chain, chain_count], rule))
				hash_new[rule_key].append(rule) # but py lists are 0-indexed
				try: metric = metrics.table[table, chain, chain_count]
				except KeyError: continue # no point checking rules w/o metrics attached
				# log.debug('Metric: {} ({}), rule: {}'.format(
				# 	metric, [table, chain, chain_count], rule ))

				# Check for changed rules
				try: rule_chk = hash_old and hash_old[rule_key][chain_count - 1]
				except (KeyError, IndexError): rule_chk = None
				if hash_old and rule_chk != rule:
					if chain_count not in warnings:
						log.warn(
							( 'Detected changed netfilter rule (chain: {}, pos: {})'
								' without corresponding rule_metrics file update: {}' )\
							.format(chain, chain_count, rule) )
						warnings[chain_count] = True
					if self.conf.discard_changed_rules: continue

				counts = map(int, counts.strip('[]').split(':', 1))
				try:
					metric_counts[metric] = list(it.starmap(
						op.add, it.izip(metric_counts[metric], counts) ))
				except KeyError: metric_counts[metric] = counts
			proc.wait()

			# Detect if there are any changes in the table,
			#  possibly messing the metrics, even if corresponding rules are the same
			hash_new = dict( (rule_key, tuple(rules))
				for rule_key, rules in hash_new.viewitems() )
			if hash_old\
					and frozenset(hash_old.viewitems()) != frozenset(hash_new.viewitems()):
				log.warn('Detected iptables changes without changes to rule_metrics file')
				hash_old = None
			if not hash_old: self._table_hash[v] = hash_new, metrics, dict()

		# Dispatch collected metrics
		for metric, counts in metric_counts.viewitems():
			for unit, count in it.izip(['pkt', 'bytes'], counts):
				if unit not in self.metric_units: continue
				yield Datapoint(self.metric_tpl.format(metric, unit), 'counter', count, None)


collector = IPTables

########NEW FILE########
__FILENAME__ = irq
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from io import open

from . import Collector, Datapoint

import logging
log = logging.getLogger(__name__)


class IRQ(Collector):

	@staticmethod
	def _parse_irq_table(table):
		irqs = dict()
		bindings = map(bytes.lower, table.readline().strip().split())
		bindings_cnt = len(bindings)
		for line in it.imap(bytes.strip, table):
			irq, line = line.split(None, 1)
			irq = irq.rstrip(':').lower()
			if irq in irqs:
				log.warn('Conflicting irq name/id: {!r}, skipping'.format(irq))
				continue
			irqs[irq] = map(int, line.split(None, bindings_cnt)[:bindings_cnt])
		return bindings, irqs

	def read(self):
		irq_tables = list()
		# /proc/interrupts
		with open('/proc/interrupts', 'rb') as table:
			irq_tables.append(self._parse_irq_table(table))
		# /proc/softirqs
		with open('/proc/softirqs', 'rb') as table:
			irq_tables.append(self._parse_irq_table(table))
		# dispatch
		for bindings, irqs in irq_tables:
			for irq, counts in irqs.viewitems():
				if sum(counts) == 0: continue
				for bind, count in it.izip(bindings, counts):
					yield Datapoint('irq.{}.{}'.format(irq, bind), 'counter', count, None)


collector = IRQ

########NEW FILE########
__FILENAME__ = memfrag
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from io import open
import re

from . import Collector, Datapoint, page_size_kb

import logging
log = logging.getLogger(__name__)


class MemFrag(Collector):

	def read( self,
			_re_buddyinfo=re.compile(r'^\s*Node\s+(?P<node>\d+)'
				r',\s+zone\s+(?P<zone>\S+)\s+(?P<counts>.*)$'),
			_re_ptinfo=re.compile(r'^\s*Node\s+(?P<node>\d+)'
				r',\s+zone\s+(?P<zone>\S+),\s+type\s+(?P<mtype>\S+)\s+(?P<counts>.*)$') ):
		mmap, pskb = dict(), page_size_kb

		# /proc/buddyinfo
		with open('/proc/buddyinfo', 'rb') as table:
			for line in it.imap(bytes.strip, table):
				match = _re_buddyinfo.search(line)
				if not match:
					log.warn('Unrecognized line in /proc/buddyinfo, skipping: {!r}'.format(line))
					continue
				node, zone = int(match.group('node')), match.group('zone').lower()
				counts = dict( ('{}k'.format(pskb*2**order),count)
					for order,count in enumerate(it.imap(int, match.group('counts').strip().split())) )
				if node not in mmap: mmap[node] = dict()
				if zone not in mmap[node]: mmap[node][zone] = dict()
				mmap[node][zone]['available'] = counts

		# /proc/pagetypeinfo
		with open('/proc/pagetypeinfo', 'rb') as table:
			page_counts_found = False
			while True:
				line = table.readline()
				if not line: break
				elif 'Free pages count' not in line:
					while line.strip(): line = table.readline()
					continue
				elif page_counts_found:
					log.warn( 'More than one free pages'
						' counters section found in /proc/pagetypeinfo' )
					continue
				else:
					page_counts_found = True
					for line in it.imap(bytes.strip, table):
						if not line: break
						match = _re_ptinfo.search(line)
						if not match:
							log.warn( 'Unrecognized line'
								' in /proc/pagetypeinfo, skipping: {!r}'.format(line) )
							continue
						node, zone, mtype = int(match.group('node')),\
							match.group('zone').lower(), match.group('mtype').lower()
						counts = dict( ('{}k'.format(pskb*2**order),count)
							for order,count in enumerate(it.imap(int, match.group('counts').strip().split())) )
						if node not in mmap: mmap[node] = dict()
						if zone not in mmap[node]: mmap[node][zone] = dict()
						mmap[node][zone][mtype] = counts
			if not page_counts_found:
				log.warn('Failed to find free pages counters in /proc/pagetypeinfo')

		# Dispatch values from mmap
		for node,zones in mmap.viewitems():
			for zone,mtypes in zones.viewitems():
				for mtype,counts in mtypes.viewitems():
					if sum(counts.viewvalues()) == 0: continue
					for size,count in counts.viewitems():
						yield Datapoint( 'memory.fragmentation.{}'\
								.format('.'.join(it.imap( bytes,
									['node_{}'.format(node),zone,mtype,size] ))),
							'gauge', count, None )


collector = MemFrag

########NEW FILE########
__FILENAME__ = memstats
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
import re

from . import Collector, Datapoint

import logging
log = logging.getLogger(__name__)


class MemStats(Collector):

	_warn_hp = True

	@staticmethod
	def _camelcase_fix( name,
			_re1=re.compile(r'(.)([A-Z][a-z]+)'),
			_re2=re.compile(r'([a-z0-9])([A-Z])'),
			_re3=re.compile(r'_+') ):
		return _re3.sub('_', _re2.sub(
			r'\1_\2', _re1.sub(r'\1_\2', name) )).lower()

	def read(self):
		# /proc/vmstat
		with open('/proc/vmstat', 'rb') as table:
			for line in table:
				metric, val = line.strip().split(None, 1)
				val = int(val)
				if metric.startswith('nr_'):
					yield Datapoint( 'memory.pages.allocation.{}'\
						.format(metric[3:]), 'gauge', val, None )
				else:
					yield Datapoint( 'memory.pages.activity.{}'\
						.format(metric), 'gauge', val, None )
		# /proc/meminfo
		with open('/proc/meminfo', 'rb') as table:
			table = dict(line.strip().split(None, 1) for line in table)
		hp_size = table.pop('Hugepagesize:', None)
		if hp_size and not hp_size.endswith(' kB'): hp_size = None
		if hp_size: hp_size = int(hp_size[:-3])
		elif self._warn_hp:
			log.warn('Unable to get hugepage size from /proc/meminfo')
			self._warn_hp = False
		for metric, val in table.viewitems():
			if metric.startswith('DirectMap'): continue # static info
			# Name mangling
			metric = self._camelcase_fix(
				metric.rstrip(':').replace('(', '_').replace(')', '') )
			if metric.startswith('s_'): metric = 'slab_{}'.format(metric[2:])
			elif metric.startswith('mem_'): metric = metric[4:]
			elif metric == 'slab': metric = 'slab_total'
			# Value processing
			try: val, val_unit = val.split()
			except ValueError: # no units assumed as number of pages
				if not metric.startswith('huge_pages_'):
					log.warn( 'Unhandled page-measured'
						' metric in /etc/meminfo: {}'.format(metric) )
					continue
				val = int(val) * hp_size
			else:
				if val_unit != 'kB':
					log.warn('Unhandled unit type in /etc/meminfo: {}'.format(unit))
					continue
				val = int(val)
			yield Datapoint( 'memory.allocation.{}'\
				.format(metric), 'gauge', val * 1024, None )


collector = MemStats

########NEW FILE########
__FILENAME__ = ping
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from subprocess import Popen, PIPE
from io import open
import os, signal

from . import Collector, Datapoint

import logging
log = logging.getLogger(__name__)


class PingerInterface(Collector):

	def __init__(self, *argz, **kwz):
		super(PingerInterface, self).__init__(*argz, **kwz)
		self.hosts = dict(it.chain(
			( ('v4:{}'.format(spec), name)
				for name, spec in (self.conf.hosts.ipv4 or dict()).viewitems() ),
			( ('v6:{}'.format(spec), name)
				for name, spec in (self.conf.hosts.ipv6 or dict()).viewitems() ) ))
		if not self.hosts:
			log.info('No valid hosts to ping specified, disabling collector')
			self.conf.enabled = False
		else: self.spawn_pinger()

	def spawn_pinger(self):
		cmd = (
			['python', os.path.join(os.path.dirname(__file__), '_ping.py')]
				+ map(bytes, [ self.conf.interval,
					self.conf.resolve.no_reply or 0, self.conf.resolve.time or 0,
					self.conf.ewma_factor, os.getpid(), self.conf.resolve.max_retries ])
				+ self.hosts.keys() )
		log.debug('Starting pinger subprocess: {}'.format(' '.join(cmd)))
		self.proc = Popen(cmd, stdout=PIPE)
		self.proc.stdout.readline() # wait until it's initialized

	def read(self):
		err = self.proc.poll()
		if err is not None:
			log.warn( 'Pinger subprocess has failed'
				' (exit code: {}), restarting it'.format(err) )
			self.spawn_pinger()
		else:
			self.proc.send_signal(signal.SIGQUIT)
			for line in iter(self.proc.stdout.readline, ''):
				line = line.strip()
				if not line: break
				host, ts_offset, rtt, lost = line.split()
				host = self.hosts[host]
				yield Datapoint('network.ping.{}.ping'.format(host), 'gauge', float(rtt), None)
				yield Datapoint('network.ping.{}.droprate'.format(host), 'counter', int(lost), None)


collector = PingerInterface

########NEW FILE########
__FILENAME__ = slabinfo
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from collections import namedtuple
from io import open

from . import Collector, Datapoint, page_size

import logging
log = logging.getLogger(__name__)


class SlabInfo(Collector):

	version_check = '2.1'

	def __init__(self, *argz, **kwz):
		super(SlabInfo, self).__init__(*argz, **kwz)

		for k in 'include_prefixes', 'exclude_prefixes':
			if not self.conf.get(k): self.conf[k] = list()

		with open('/proc/slabinfo', 'rb') as table:
			line = table.readline()
			self.version = line.split(':')[-1].strip()
			if self.version_check\
					and self.version != self.version_check:
				log.warn( 'Slabinfo header indicates'
						' different schema version (expecting: {}): {}'\
					.format(self.version_check, line) )
			line = table.readline().strip().split()
			if line[0] != '#' or line[1] != 'name':
				log.error('Unexpected slabinfo format, not processing it')
				return
			headers = dict(name=0)
			for idx,header in enumerate(line[2:], 1):
				if header[0] == '<' and header[-1] == '>': headers[header[1:-1]] = idx
			pick = 'name', 'active_objs', 'objsize', 'pagesperslab', 'active_slabs', 'num_slabs'
			picker = op.itemgetter(*op.itemgetter(*pick)(headers))
			record = namedtuple('slabinfo_record', ' '.join(pick))
			self.parse_line = lambda line: record(*( (int(val) if idx else val)
					for idx,val in enumerate(picker(line.strip().split())) ))

	# http://elinux.org/Slab_allocator
	def read(self):
		parse_line, ps = self.parse_line, page_size
		with open('/proc/slabinfo', 'rb') as table:
			table.readline(), table.readline() # header
			for line in table:
				info = parse_line(line)
				for prefix in self.conf.include_prefixes:
					if info.name.startswith(prefix): break # force-include
				else:
					for prefix in self.conf.exclude_prefixes:
						if info.name.startswith(prefix):
							info = None
							break
				if info:
					vals = [
						('obj_active', info.active_objs * info.objsize),
						('slab_active', info.active_slabs * info.pagesperslab * ps),
						('slab_allocated', info.num_slabs * info.pagesperslab * ps) ]
					if self.conf.pass_zeroes or sum(it.imap(op.itemgetter(1), vals)) != 0:
						for val_name, val in vals:
							yield Datapoint( 'memory.slabs.{}.bytes_{}'\
								.format(info.name, val_name), 'gauge', val, None )


collector = SlabInfo

########NEW FILE########
__FILENAME__ = stats
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from io import open

from . import Collector, Datapoint

import logging
log = logging.getLogger(__name__)


class Stats(Collector):

	def read(self):
		with open('/proc/stat', 'rb') as table:
			for line in table:
				label, vals = line.split(None, 1)
				total = int(vals.split(None, 1)[0])
				if label == 'intr': name = 'irq.total.hard'
				elif label == 'softirq': name = 'irq.total.soft'
				elif label == 'processes': name = 'processes.forks'
				else: continue # no more useful data here
				yield Datapoint(name, 'counter', total, None)


collector = Stats

########NEW FILE########
__FILENAME__ = sysstat
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from subprocess import Popen, PIPE, STDOUT
from time import time, sleep, strptime, mktime
from calendar import timegm
from datetime import datetime, timedelta
from xattr import xattr
import os, sys, socket, struct

from . import Collector, Datapoint, dev_resolve, sector_bytes, rate_limit

try: from simplejson import loads, dumps, JSONDecodeError
except ImportError:
	from json import loads, dumps
	JSONDecodeError = ValueError

import logging
log = logging.getLogger(__name__)


class SADF(Collector):


	def __init__(self, *argz, **kwz):
		super(SADF, self).__init__(*argz, **kwz)

		# Set force_interval margins, if used
		if self.conf.force_interval:
			try:
				from . import cfg
				interval = cfg.loop.interval
			except (ImportError, KeyError, AttributeError):
				log.warn( 'Failed to apply force_interval option'
					' - unable to access global configuration to get data collection interval' )
				self.force_interval = None
			else:
				if self.conf.force_interval_fuzz:
					fuzz = interval * self.conf.force_interval_fuzz / 100.0
				else: fuzz = 0
				self.force_interval = interval - fuzz, interval + fuzz
		else: self.force_interval = None

		self.rate_limit = rate_limit(
				max_interval=self.conf.rate.max_interval,
				sampling=self.conf.rate.sampling )\
			if self.conf.rate.limiting_enabled else None


	def process_entry(self, entry):

		# Timestamp
		try: ts = entry.pop('timestamp')
		except KeyError:
			log.info( 'Detected sysstat entry'
				' without timestamp, skipping: {!r}'.format(entry) )
			return # happens, no idea what to do with these
		interval = ts['interval']
		for fmt in '%Y-%m-%d %H-%M-%S', '%Y-%m-%d %H:%M:%S':
			try:
				ts = (mktime if not ts['utc'] else timegm)\
					(strptime('{} {}'.format(ts['date'], ts['time']), fmt))
			except ValueError: pass
			else: break
		else:
			raise ValueError( 'Unable to process'
				' sysstat timestamp: {!r} {!r}'.format(ts['date'], ts['time']) )

		# Metrics
		metrics = list()

		if self.conf.skip.sections:
			for k in self.conf.skip.sections:
				if k in entry: del entry[k]
				else: log.debug('Section-to-skip {!r} not found in sysstat entry'.format(k))
		process_redundant = not self.conf.skip.redundant

		if 'cpu-load-all' in entry:
			for stats in entry.pop('cpu-load-all'):
				prefix = stats.pop('cpu')
				if prefix == 'all': continue # can be derived by aggregator/webapp
				prefix = ['cpu', prefix]
				metrics.extend((prefix + [k], v) for k,v in stats.viewitems())

		if 'process-and-context-switch' in entry:
			stats = entry.pop('process-and-context-switch')
			metrics.append((['misc', 'contextswitch'], stats['cswch']))
			if process_redundant: # also processed in "stats"
				metrics.append((['processes', 'forks'], stats['proc']))

		if process_redundant:
			if 'interrupts' in entry: # with "irq"
				for stats in entry.pop('interrupts'):
					if stats['intr'] == 'sum': continue # can be derived by aggregator/webapp
					metrics.append((['irq', stats['intr'], 'sum'], stats['value']))
			if 'swap-pages' in entry: # with "memstats"
				for k,v in entry.pop('swap-pages').viewitems():
					metrics.append((['memory', 'pages', 'activity', k], v))
			# if 'memory' in entry: # with "memstats"
			# if 'hugepages' in entry: # with "memstats"

		if 'disk' in entry:
			for disk in entry.pop('disk'):
				dev_sadf = disk['disk-device']
				if not dev_sadf.startswith('dev'):
					log.warn('Unknown device name format: {}, skipping'.format(dev_sadf))
					continue
				dev = dev_resolve(*it.imap(int, dev_sadf[3:].split('-')), log_fails=False)
				if dev is None:
					log.warn('Unable to resolve name for device {!r}, skipping'.format(dev_sadf))
					continue
				prefix = ['disk', 'load', dev]
				metrics.extend([
					(prefix + ['utilization'], disk['util-percent']),
					(prefix + ['req_size'], disk['avgrq-sz']),
					(prefix + ['queue_len'], disk['avgqu-sz']),
					(prefix + ['bytes_read'], sector_bytes * disk['rd_sec']),
					(prefix + ['bytes_write'], sector_bytes * disk['wr_sec']),
					(prefix + ['serve_time'], disk['await']),
					(prefix + ['tps'], disk['tps']) ])
		# if 'io' in entry: # can be derived by aggregator/webapp

		if 'paging' in entry:
			metrics.append((
				['memory', 'pages', 'vm_efficiency'],
				entry.pop('paging')['vmeff-percent'] ))
			# XXX: lots of redundant metrics here

		if 'queue' in entry:
			stats = entry.pop('queue')
			for n in 1, 5, 15:
				k = 'ldavg-{}'.format(n)
				metrics.append((['load', k], stats[k]))
			metrics.extend(
				(['processes', 'state', k], stats[k])
				for k in ['runq-sz', 'plist-sz', 'blocked'] )

		if 'kernel' in entry:
			stats = entry.pop('kernel')
			metrics.extend([
				(['misc', 'dent_unused'], stats['dentunusd']),
				(['misc', 'file_handles'], stats['file-nr']),
				(['misc', 'inode_handles'], stats['inode-nr']),
				(['misc', 'pty'], stats['pty-nr']) ])

		if 'network' in entry:
			stats = entry.pop('network')
			iface_stats = stats.get('net-dev', list())
			for iface in iface_stats:
				prefix = ['network', 'interfaces', iface['iface']]
				metrics.extend([
					(prefix + ['rx', 'bytes'], iface['rxkB'] * 2**10),
					(prefix + ['rx', 'packets', 'total'], iface['rxpck']),
					(prefix + ['rx', 'packets', 'compressed'], iface['rxcmp']),
					(prefix + ['rx', 'packets', 'multicast'], iface['rxmcst']),
					(prefix + ['tx', 'bytes'], iface['txkB'] * 2**10),
					(prefix + ['tx', 'packets', 'total'], iface['txpck']),
					(prefix + ['tx', 'packets', 'compressed'], iface['txpck']) ])
			iface_stats = stats.get('net-edev', list())
			iface_errs_common = [('err', 'total'), ('fifo', 'overflow_fifo'), ('drop', 'overflow_kbuff')]
			for iface in iface_stats:
				prefix = ['network', 'interfaces', iface['iface']]
				for src,dst in iface_errs_common + [('fram', 'frame_alignment')]:
					metrics.append((prefix + ['rx', 'errors', dst], iface['rx{}'.format(src)]))
				for src,dst in iface_errs_common + [('carr', 'carrier')]:
					metrics.append((prefix + ['tx', 'errors', dst], iface['tx{}'.format(src)]))
				metrics.append((prefix + ['tx', 'errors', 'collision'], iface['coll']))
			if 'net-nfs' in stats:
				for k,v in stats['net-nfs'].viewitems():
					metrics.append((['network', 'nfs', 'client', k], v))
				for k,v in stats['net-nfsd'].viewitems():
					metrics.append((['network', 'nfs', 'server', k], v))
			if 'net-sock' in stats:
				for k,v in stats['net-sock'].viewitems():
					if k.endswith('sck'):
						k = k[:-3]
						if k == 'tot': k = 'total'
						metrics.append((['network', 'sockets', k], v))

		if 'power-management' in entry:
			stats = entry.pop('power-management')
			for metric in stats.get('temperature', list()):
				name = ['sensors', 'temperature', metric['device'].replace('.', '_')]
				if 'number' in metric: name.append(bytes(metric['number']))
				metrics.append((name, metric['degC']))

		return ts, interval, metrics


	def _read(self, ts_to=None):
		if not ts_to: ts_to = datetime.now()

		sa_days = dict( (ts.day, ts)
			for ts in ((ts_to - timedelta(i))
			for i in xrange(self.conf.skip.older_than_days+1)) )
		sa_files = sorted(it.ifilter(
			op.methodcaller('startswith', 'sa'), os.listdir(self.conf.sa_path) ))
		host = os.uname()[1] # to check vs nodename in data
		log.debug('SA files to process: {}'.format(sa_files))

		for sa in sa_files:
			sa_day = int(sa[2:])
			try: sa_day = sa_days[sa_day]
			except KeyError: continue # too old or new

			sa = os.path.join(self.conf.sa_path, sa)
			log.debug('Processing file: {}'.format(sa))

			# Read xattr timestamp
			sa_xattr = xattr(sa)
			try: sa_ts_from = sa_xattr[self.conf.xattr_name]
			except KeyError: sa_ts_from = None
			if sa_ts_from:
				sa_ts_from = datetime.fromtimestamp(
					struct.unpack('=I', sa_ts_from)[0] )
				if sa_day - sa_ts_from > timedelta(1) + timedelta(seconds=60):
					log.debug( 'Discarding xattr timestamp, because'
						' it doesnt seem to belong to the same date as file'
						' (day: {}, xattr: {})'.format(sa_day, sa_ts_from) )
					sa_ts_from = None
				if sa_ts_from and sa_ts_from.date() != sa_day.date():
					log.debug('File xattr timestamp points to the next day, skipping file')
					continue
			if not self.conf.max_dump_span: sa_ts_to = None
			else:
				# Use 00:00 of sa_day + max_dump_span if there's no xattr
				ts = sa_ts_from or datetime(sa_day.year, sa_day.month, sa_day.day)
				sa_ts_to = ts + timedelta(0, self.conf.max_dump_span)
				# Avoid adding restrictions, if they make no sense anyway
				if sa_ts_to >= datetime.now(): sa_ts_to = None

			# Get data from sadf
			sa_cmd = ['sadf', '-jt']
			if sa_ts_from: sa_cmd.extend(['-s', sa_ts_from.strftime('%H:%M:%S')])
			if sa_ts_to: sa_cmd.extend(['-e', sa_ts_to.strftime('%H:%M:%S')])
			sa_cmd.extend(['--', '-A'])
			sa_cmd.append(sa)
			log.debug('sadf command: {}'.format(sa_cmd))
			sa_proc = Popen(sa_cmd, stdout=PIPE)
			try: data = loads(sa_proc.stdout.read())
			except JSONDecodeError as err:
				log.exception(( 'Failed to process sadf (file:'
					' {}, command: {}) output: {}' ).format(sa, sa_cmd, err))
				data = None
			if sa_proc.wait():
				log.error('sadf (command: {}) exited with error'.format(sa_cmd))
				data = None
			if not data:
				log.warn('Skipping processing of sa file: {}'.format(sa))
				continue

			# Process and dispatch the datapoints
			sa_ts_max = 0
			for data in data['sysstat']['hosts']:
				if data['nodename'] != host:
					log.warn( 'Mismatching hostname in sa data:'
						' {} (uname: {}), skipping'.format(data['nodename'], host) )
					continue
				sa_day_ts = mktime(sa_day.timetuple())
				# Read the data
				for ts, interval, metrics in it.ifilter(
						None, it.imap(self.process_entry, data['statistics']) ):
					if ts - 1 > sa_ts_max:
						# has to be *before* beginning of the next interval
						sa_ts_max = ts - 1
					if abs(ts - sa_day_ts) > 24*3600 + interval + 1:
						log.warn( 'Dropping sample because of timestamp mismatch'
							' (timestamp: {}, expected date: {})'.format(ts, sa_day_ts) )
						continue
					if self.force_interval and (
							interval < self.force_interval[0]
							or interval > self.force_interval[1] ):
						log.warn( 'Dropping sample because of interval mismatch'
							' (file: {sa}, interval: {interval},'
							' required: {margins[0]}-{margins[1]}, timestamp: {ts})'\
								.format(sa=sa, interval=interval, ts=ts, margins=self.force_interval) )
						continue
					ts_val = int(ts)
					for name, val in metrics:
						yield Datapoint('.'.join(name), 'gauge', val, ts_val)

			# Update xattr timestamp, if any entries were processed
			if sa_ts_max:
				log.debug('Updating xattr timestamp to {}'.format(sa_ts_max))
				if not self.conf.debug.dry_run:
					sa_xattr[self.conf.xattr_name] = struct.pack('=I', int(sa_ts_max))


	def read(self):
		if not self.rate_limit or next(self.rate_limit):
			log.debug('Running sysstat data processing cycle')
			return self._read()
		else: return list()


collector = SADF

########NEW FILE########
__FILENAME__ = _ping
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import itertools as it, operator as op, functools as ft
from contextlib import closing
from select import epoll, EPOLLIN, EPOLLOUT
from time import time, sleep
import os, sys, socket, struct, random, signal, re, logging


class LinkError(Exception): pass

class Pinger(object):

	@staticmethod
	def calculate_checksum(src):
		shift, src = sys.byteorder != 'little', bytearray(src)
		chksum = 0
		for c in src:
			chksum += (c << 8) if shift else c
			shift = not shift
		chksum = (chksum & 0xffff) + (chksum >> 16)
		chksum += chksum >> 16
		chksum = ~chksum & 0xffff
		return struct.pack('!H', socket.htons(chksum))


	def resolve(self, host, family=0, socktype=0, proto=0, flags=0):
		try: f, host = host.split(':', 1)
		except ValueError: pass
		else:
			assert f in ['v4', 'v6'], f
			if f == 'v4':
				family, sock = socket.AF_INET, self.ipv4
			elif f == 'v6':
				family, sock = socket.AF_INET6, self.ipv6
				match = re.search(r'^\[([0-9:a-fA-F]+)\]$', host)
				if match: host = match.group(1)
		addrs = set( addrinfo[-1] for addrinfo in
			socket.getaddrinfo(host, 0, family, socktype, proto, flags) )
		return sock, random.choice(list(addrs))

	def test_link(self, addrinfo, ping_id=0xffff, seq=0):
		'Test if it is possible to send packets out at all (i.e. link is not down).'
		try: self.pkt_send(addrinfo, ping_id, seq)
		except IOError as err: raise LinkError(str(err))

	def pkt_send(self, addrinfo, ping_id, seq):
		sock, addr = addrinfo
		if sock is self.ipv4: icmp_type = 0x08
		elif sock is self.ipv6: icmp_type = 0x80
		else: raise ValueError(sock)
		ts = time()
		ts_secs = int(ts)
		ts_usecs = int((ts - ts_secs) * 1e6)
		# Timestamp is packed in wireshark-friendly format
		# Using time.clock() would probably be better here,
		#  as it should work better with time corrections (by e.g. ntpd)
		pkt = bytearray(struct.pack( '!BBHHHII',
			icmp_type, 0, 0, ping_id, seq, ts_secs, ts_usecs ))
		pkt[2:4] = self.calculate_checksum(pkt)
		sock.sendto(bytes(pkt), addr)

	def pkt_recv(self, sock):
		# None gets returned in cases when we get whatever other icmp thing
		pkt, src = sock.recvfrom(2048)
		if sock is self.ipv4: start = 20
		elif sock is self.ipv6: start = 0
		else: raise ValueError(sock)
		try: pkt = struct.unpack('!BBHHHII', pkt[start:start + 16])
		except struct.error: return
		if sock is self.ipv4 and (pkt[0] != 0 or pkt[1] != 0): return
		elif sock is self.ipv6 and (pkt[0] != 0x81 or pkt[1] != 0): return
		return src[0], pkt[3], pkt[4], pkt[5] + (pkt[6] / 1e6) # addr, ping_id, seq, ts


	def start(self, *args, **kws):
		with\
				closing(socket.socket( socket.AF_INET,
					socket.SOCK_RAW, socket.getprotobyname('icmp') )) as self.ipv4,\
				closing(socket.socket( socket.AF_INET6,
					socket.SOCK_RAW, socket.getprotobyname('ipv6-icmp') )) as self.ipv6:
			return self._start(*args, **kws)

	def _start( self, host_specs, interval,
			resolve_no_reply, resolve_fixed, ewma_factor, ping_pid, log=None,
			warn_tries=5, warn_repeat=None, warn_delay_k=5, warn_delay_min=5 ):
		ts = time()
		seq_gen = it.chain.from_iterable(it.imap(xrange, it.repeat(2**15)))
		resolve_fixed_deadline = ts + resolve_fixed
		resolve_retry = dict()
		self.discard_rtts = False
		if not log: log = logging.getLogger(__name__)

		### First resolve all hosts, waiting for it, if necessary
		hosts, host_ids = dict(), dict()
		for host in host_specs:
			while True:
				ping_id = random.randint(0, 0xfffe)
				if ping_id not in host_ids: break
			warn = warn_ts = 0
			while True:
				try:
					addrinfo = self.resolve(host)
					self.test_link(addrinfo)

				except (socket.gaierror, socket.error, LinkError) as err:
					ts = time()
					if warn < warn_tries:
						warn_force, warn_chk = False, True
					else:
						warn_force, warn_chk = True, warn_repeat\
							and (warn_repeat is True or ts - warn_ts > warn_repeat)
					if warn_chk: warn_ts = ts
					err_info = type(err).__name__
					if str(err): err_info += ': {}'.format(err)
					(log.warn if warn_chk else log.info)\
						( '{}Unable to resolve/send-to name spec: {} ({})'\
							.format('' if not warn_force else '(STILL) ', host, err_info) )
					warn += 1
					if warn_repeat is not True and warn == warn_tries:
						log.warn( 'Disabling name-resolver/link-test warnings (failures: {},'
							' name spec: {}) until next successful attempt'.format(warn, host) )
					sleep(max(interval / float(warn_delay_k), warn_delay_min))

				else:
					hosts[host] = host_ids[ping_id] = dict(
						ping_id=ping_id, addrinfo=addrinfo,
						last_reply=0, rtt=0, sent=0, recv=0 )
					if warn >= warn_tries:
						log.warn('Was able to resolve host spec: {} (attempts: {})'.format(host, warn))
					break

		### Handler to emit results on-demand
		def dump(sig, frm):
			self.discard_rtts = True # make sure results won't be tainted by this delay
			ts = time()
			try:
				for spec, host in hosts.viewitems():
					sys.stdout.write('{} {:.10f} {:.10f} {:010d}\n'.format(
						spec, ts - host['last_reply'], host['rtt'],
						max(host['sent'] - host['recv'] - 1, 0) )) # 1 pkt can be in-transit
					if host['sent'] > 2**30: host['sent'] = host['recv'] = 0
				sys.stdout.write('\n')
				sys.stdout.flush()
			except IOError: sys.exit()
		signal.signal(signal.SIGQUIT, dump)

		### Actual ping-loop
		poller, sockets = epoll(), dict()
		for sock in self.ipv4, self.ipv6:
			sockets[sock.fileno()] = sock
			poller.register(sock, EPOLLIN)
		sys.stdout.write('\n')
		sys.stdout.flush()

		ts_send = 0 # when last packet(s) were sent out
		while True:
			while True:
				poll_time = max(0, ts_send + interval - time())
				try:
					poll_res = poller.poll(poll_time)
					if not poll_res or not poll_res[0][1] & EPOLLIN: break
					pkt = self.pkt_recv(sockets[poll_res[0][0]])
					if not pkt: continue
					addr, ping_id, seq, ts_pkt = pkt
				except IOError: continue
				if not ts_send: continue
				ts = time()
				try: host = host_ids[ping_id]
				except KeyError: pass
				else:
					host['last_reply'] = ts
					host['recv'] += 1
					if not self.discard_rtts:
						host['rtt'] = host['rtt'] + ewma_factor * (ts - ts_pkt - host['rtt'])

			if resolve_retry:
				for spec, host in resolve_retry.items():
					try: host['addrinfo'] = self.resolve(spec)
					except socket.gaierror as err:
						log.warn('Failed to resolve spec: {} (host: {}): {}'.format(spec, host, err))
						host['resolve_fails'] = host.get('resolve_fails', 0) + 1
						if host['resolve_fails'] >= warn_tries:
							log.error(( 'Failed to resolve host spec {} (host: {}) after {} attempts,'
								' exiting (so subprocess can be restarted)' ).format(spec, host, warn_tries))
							# More complex "retry until forever" logic is used on process start,
							#  so exit here should be performed only once per major (non-transient) failure
							sys.exit(0)
					else:
						host['resolve_fails'] = 0
						del resolve_retry[spec]

			if time() > resolve_fixed_deadline:
				for spec,host in hosts.viewitems():
					try: host['addrinfo'] = self.resolve(spec)
					except socket.gaierror: resolve_retry[spec] = host
				resolve_fixed_deadline = ts + resolve_fixed

			if ping_pid:
				try: os.kill(ping_pid, 0)
				except OSError: sys.exit()

			resolve_reply_deadline = time() - resolve_no_reply
			self.discard_rtts, seq = False, next(seq_gen)
			for spec, host in hosts.viewitems():
				if host['last_reply'] < resolve_reply_deadline:
					try: host['addrinfo'] = self.resolve(spec)
					except socket.gaierror: resolve_retry[spec] = host
				send_retries = 30
				while True:
					try: self.pkt_send(host['addrinfo'], host['ping_id'], seq)
					except IOError as err:
						send_retries -= 1
						if send_retries == 0:
							log.error(( 'Failed sending pings from socket to host spec {}'
									' (host: {}) attempts ({}), killing pinger (so it can be restarted).' )\
								.format(spec, host, err))
							sys.exit(0) # same idea as with resolver errors above
						continue
					else: break
					host['sent'] += 1
			ts_send = time() # used to calculate when to send next batch of pings


if __name__ == '__main__':
	signal.signal(signal.SIGQUIT, signal.SIG_IGN)
	logging.basicConfig()
	# Inputs
	Pinger().start( sys.argv[7:], interval=float(sys.argv[1]),
		resolve_no_reply=float(sys.argv[2]), resolve_fixed=float(sys.argv[3]),
		ewma_factor=float(sys.argv[4]), ping_pid=int(sys.argv[5]),
		warn_tries=int(sys.argv[6]), log=logging.getLogger('pinger'),
		warn_repeat=8 * 3600, warn_delay_k=5, warn_delay_min=5 )
	# Output on SIGQUIT: "host_spec time_since_last_reply rtt_median pkt_lost"
	#  pkt_lost is a counter ("sent - received" for whole runtime)

########NEW FILE########
__FILENAME__ = harvestd
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from lya import AttrDict, configure_logging
from collections import OrderedDict
import os, sys


def main():
	import argparse
	parser = argparse.ArgumentParser(
		description='Collect and dispatch various metrics to destinations.')
	parser.add_argument('-t', '--destination', metavar='host[:port]',
		help='host[:port] (default port: 2003, can be overidden'
			' via config file) of sink destination endpoint (e.g. carbon'
			' linereceiver tcp port, by default).')
	parser.add_argument('-i', '--interval', type=int, metavar='seconds',
		help='Interval between collecting and sending the datapoints.')

	parser.add_argument('-e', '--collector-enable',
		action='append', metavar='collector', default=list(),
		help='Enable only the specified metric collectors,'
				' can be specified multiple times.')
	parser.add_argument('-d', '--collector-disable',
		action='append', metavar='collector', default=list(),
		help='Explicitly disable specified metric collectors,'
			' can be specified multiple times. Overrides --collector-enable.')

	parser.add_argument('-s', '--sink-enable',
		action='append', metavar='sink', default=list(),
		help='Enable only the specified datapoint sinks,'
				' can be specified multiple times.')
	parser.add_argument('-x', '--sink-disable',
		action='append', metavar='sink', default=list(),
		help='Explicitly disable specified datapoint sinks,'
			' can be specified multiple times. Overrides --sink-enable.')

	parser.add_argument('-p', '--processor-enable',
		action='append', metavar='processor', default=list(),
		help='Enable only the specified datapoint processors,'
				' can be specified multiple times.')
	parser.add_argument('-z', '--processor-disable',
		action='append', metavar='processor', default=list(),
		help='Explicitly disable specified datapoint processors,'
			' can be specified multiple times. Overrides --processor-enable.')

	parser.add_argument('-c', '--config',
		action='append', metavar='path', default=list(),
		help='Configuration files to process.'
			' Can be specified more than once.'
			' Values from the latter ones override values in the former.'
			' Available CLI options override the values in any config.')

	parser.add_argument('-a', '--xattr-emulation', metavar='db-path',
		help='Emulate filesystem extended attributes (used in'
			' some collectors like sysstat or cron_log), storing per-path'
			' data in a simple shelve db.')
	parser.add_argument('-n', '--dry-run',
		action='store_true', help='Do not actually send data.')
	parser.add_argument('--debug-memleaks', action='store_true',
		help='Import guppy and enable its manhole to debug memleaks (requires guppy module).')
	parser.add_argument('--debug',
		action='store_true', help='Verbose operation mode.')
	optz = parser.parse_args()

	# Read configuration files
	cfg = AttrDict.from_yaml('{}.yaml'.format(
		os.path.splitext(os.path.realpath(__file__))[0] ))
	for k in optz.config: cfg.update_yaml(k)

	# Logging
	import logging
	configure_logging( cfg.logging,
		logging.DEBUG if optz.debug else logging.WARNING )
	if not cfg.logging.tracebacks:
		class NoTBLogger(logging.Logger):
			def exception(self, *argz, **kwz): self.error(*argz, **kwz)
		logging.setLoggerClass(NoTBLogger)
	log = logging.getLogger(__name__)

	# Manholes
	if optz.debug_memleaks:
		import guppy
		from guppy.heapy import Remote
		Remote.on()

	# Fill "auto-detected" blanks in the configuration, CLI overrides
	try:
		if optz.destination: cfg.sinks._default.host = optz.destination
		cfg.sinks._default.host = cfg.sinks._default.host.rsplit(':', 1)
		if len(cfg.sinks._default.host) == 1:
			cfg.sinks._default.host =\
				cfg.sinks._default.host[0], cfg.sinks._default.default_port
		else: cfg.sinks._default.host[1] = int(cfg.sinks._default.host[1])
	except KeyError: pass
	if optz.interval: cfg.loop.interval = optz.interval
	if optz.dry_run: cfg.debug.dry_run = optz.dry_run
	if optz.xattr_emulation: cfg.core.xattr_emulation = optz.xattr_emulation

	# Fake "xattr" module, if requested
	if cfg.core.xattr_emulation:
		import shelve
		xattr_db = shelve.open(cfg.core.xattr_emulation, 'c')
		class xattr_path(object):
			def __init__(self, base):
				assert isinstance(base, str)
				self.base = base
			def key(self, k): return '{}\0{}'.format(self.base, k)
			def __setitem__(self, k, v): xattr_db[self.key(k)] = v
			def __getitem__(self, k): return xattr_db[self.key(k)]
			def __del__(self): xattr_db.sync()
		class xattr_module(object): xattr = xattr_path
		sys.modules['xattr'] = xattr_module

	# Override "enabled" collector/sink parameters, based on CLI
	ep_conf = dict()
	for ep, enabled, disabled in\
			[ ('collectors', optz.collector_enable, optz.collector_disable),
				('processors', optz.processor_enable, optz.processor_disable),
				('sinks', optz.sink_enable, optz.sink_disable) ]:
		conf = cfg[ep]
		conf_base = conf.pop('_default')
		if 'debug' not in conf_base: conf_base['debug'] = cfg.debug
		ep_conf[ep] = conf_base, conf, OrderedDict(), enabled, disabled

	# Init global cfg for collectors/sinks' usage
	from graphite_metrics import collectors, sinks, loops
	collectors.cfg = sinks.cfg = loops.cfg = cfg

	# Init pluggable components
	import pkg_resources

	for ep_type in 'collector', 'processor', 'sink':
		ep_key = '{}s'.format(ep_type) # a bit of a hack
		conf_base, conf, objects, enabled, disabled = ep_conf[ep_key]
		ep_dict = dict( (ep.name, ep) for ep in
			pkg_resources.iter_entry_points('graphite_metrics.{}'.format(ep_key)) )
		eps = OrderedDict(
			(name, (ep_dict.pop(name), subconf or AttrDict()))
			for name, subconf in conf.viewitems() if name in ep_dict )
		eps.update( (name, (module, conf_base))
			for name, module in ep_dict.viewitems() )
		for ep_name, (ep_module, subconf) in eps.viewitems():
			if ep_name[0] == '_':
				log.debug( 'Skipping {} enty point,'
					' prefixed by underscore: {}'.format(ep_type, ep_name) )
			subconf.rebase(conf_base) # fill in "_default" collector parameters
			if enabled:
				if ep_name in enabled: subconf['enabled'] = True
				else: subconf['enabled'] = False
			if disabled and ep_name in disabled: subconf['enabled'] = False
			if subconf.get('enabled', True):
				log.debug('Loading {}: {}'.format(ep_type, ep_name))
				try: obj = getattr(ep_module.load(), ep_type)(subconf)
				except Exception as err:
					log.exception('Failed to load/init {} ({}): {}'.format(ep_type, ep_name, err))
					subconf.enabled = False
					obj = None
				if subconf.get('enabled', True): objects[ep_name] = obj
				else:
					log.debug(( '{} {} (entry point: {})'
						' was disabled after init' ).format(ep_type.title(), obj, ep_name))
		if ep_type != 'processor' and not objects:
			log.fatal('No {}s were properly enabled/loaded, bailing out'.format(ep_type))
			sys.exit(1)
		log.debug('{}: {}'.format(ep_key.title(), objects))

	loop = dict( (ep.name, ep) for ep in
		pkg_resources.iter_entry_points('graphite_metrics.loops') )
	conf = AttrDict(**cfg.loop)
	if 'debug' not in conf: conf.debug = cfg.debug
	loop = loop[cfg.loop.name].load().loop(conf)

	collectors, processors, sinks = it.imap( op.itemgetter(2),
		op.itemgetter('collectors', 'processors', 'sinks')(ep_conf) )
	log.debug(
		'Starting main loop: {} ({} collectors, {} processors, {} sinks)'\
		.format(loop, len(collectors), len(processors), len(sinks)) )
	loop.start(collectors, processors, sinks)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = basic
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft

from . import Loop

import logging
log = logging.getLogger(__name__)


class BasicLoop(Loop):

	'Simple synchronous "while True: fetch && process && send" loop.'

	def start(self, collectors, processors, sinks):
		from time import time, sleep

		ts = self.time_func()
		while True:
			data = list()
			for name, collector in collectors.viewitems():
				log.debug('Polling data from a collector (name: {}): {}'.format(name, collector))
				try: data.extend(collector.read())
				except Exception as err:
					log.exception( 'Failed to poll collector'
						' (name: {}, obj: {}): {}'.format(name, collector, err) )

			ts_now = self.time_func()
			sink_data = dict() # to batch datapoints on per-sink basis

			log.debug('Processing {} datapoints'.format(len(data)))
			for dp in it.ifilter(None, (dp.get(ts=ts_now) for dp in data)):
				proc_sinks = sinks.copy()
				for name, proc in processors.viewitems():
					if dp is None: break
					try: dp, sinks = proc.process(dp, sinks)
					except Exception as err:
						log.exception(( 'Failed to process datapoint (data: {},'
							' processor: {}, obj: {}): {}, discarding' ).format(dp, name, proc, err))
						break
				else:
					if dp is None: continue
					for name, sink in proc_sinks.viewitems():
						try: sink_data[name].append(dp)
						except KeyError: sink_data[name] = [dp]

			log.debug('Dispatching data to {} sink(s)'.format(len(sink_data)))
			if not self.conf.debug.dry_run:
				for name, tuples in sink_data.viewitems():
					log.debug(( 'Sending {} datapoints to sink'
						' (name: {}): {}' ).format(len(tuples), name, sink))
					try: sinks[name].dispatch(*tuples)
					except Exception as err:
						log.exception( 'Failed to dispatch data to sink'
							' (name: {}, obj: {}): {}'.format(name, sink, err) )

			while ts < ts_now: ts += self.conf.interval
			ts_sleep = max(0, ts - self.time_func())
			log.debug('Sleep: {}s'.format(ts_sleep))
			sleep(ts_sleep)


loop = BasicLoop

########NEW FILE########
__FILENAME__ = hostname_prefix
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
import os

from . import Processor

import logging
log = logging.getLogger(__name__)


class HostnamePrefix(Processor):

	'Adds a hostname as a prefix to metric name.'

	def __init__(self, *argz, **kwz):
		super(HostnamePrefix, self).__init__(*argz, **kwz)
		self.prefix = self.conf.hostname
		if self.prefix is None: self.prefix = os.uname()[1]
		if not self.prefix.endswith('.'): self.prefix += '.'

	def process(self, dp_tuple, sinks):
		name, value, ts_dp = dp_tuple
		return (self.prefix + name, value, ts_dp), sinks


processor = HostnamePrefix

########NEW FILE########
__FILENAME__ = carbon_socket
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from time import sleep
import socket

from . import Sink

import logging
log = logging.getLogger(__name__)


class CarbonSocket(Sink):

	'''Simple blocking non-buffering sender
		to graphite carbon tcp linereceiver interface.'''

	def __init__(self, conf):
		super(CarbonSocket, self).__init__(conf)
		if not self.conf.debug.dry_run: self.connect()

	def connect(self, send=None):
		host, port = self.conf.host
		reconnects = self.conf.max_reconnects
		while True:
			try:
				try:
					addrinfo = list(reversed(socket.getaddrinfo(
						host, port, socket.AF_UNSPEC, socket.SOCK_STREAM )))
				except socket.error as err:
					raise socket.gaierror(err.message)
				assert addrinfo, addrinfo
				while addrinfo:
					# Try connecting to all of the returned addresses
					af, socktype, proto, canonname, sa = addrinfo.pop()
					try:
						self.sock = socket.socket(af, socktype, proto)
						self.sock.connect(sa)
					except socket.error:
						if not addrinfo: raise
				log.debug('Connected to Carbon at {}:{}'.format(*sa))
				if send: self.sock.sendall(send)

			except (socket.error, socket.gaierror) as err:
				if reconnects is not None:
					reconnects -= 1
					if reconnects <= 0: raise
				if isinstance(err, socket.gaierror):
					log.info('Failed to resolve host ({!r}): {}'.format(host, err))
				else: log.info('Failed to connect to {}:{}: {}'.format(host, port, err))
				if self.conf.reconnect_delay:
					sleep(max(0, self.conf.reconnect_delay))

			else: break

	def close(self):
		try: self.sock.close()
		except: pass

	def reconnect(self, send=None):
		self.close()
		self.connect(send=send)

	def dispatch(self, *tuples):
		reconnects = self.conf.max_reconnects
		packet = ''.join(it.starmap('{} {} {}\n'.format, tuples))
		try: self.sock.sendall(packet)
		except socket.error as err:
			log.error('Failed to send data to Carbon server: {}'.format(err))
			self.reconnect(send=packet)


sink = CarbonSocket

########NEW FILE########
__FILENAME__ = dump
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft

from . import Sink

import logging
log = logging.getLogger(__name__)


class Dumper(Sink):

	'Just dumps the data to log. Useful for debugging.'

	def dispatch(self, *tuples):
		log.info('--- dump of {} datapoints'.format(len(tuples)))
		for name, value, ts_dp in tuples:
			log.info('Datapoint: {} {} {}'.format(name, value, ts_dp))
		log.info('--- dump end')


sink = Dumper

########NEW FILE########
__FILENAME__ = librato_metrics
# -*- coding: utf-8 -*-

import itertools as it, operator as op, functools as ft
from time import time
import types

from requests.auth import HTTPBasicAuth
import requests

try: from simplejson import dumps
except ImportError: from json import dumps

from . import Sink

import logging
log = logging.getLogger(__name__)


class LibratoMetrics(Sink):

	'''Interface to a Librato Metrics API v1. Uses JSON Array format.
		Relevant part of the docs: http://dev.librato.com/v1/post/metrics'''

	def __init__(self, *argz, **kwz):
		super(LibratoMetrics, self).__init__(*argz, **kwz)

		# Try to set reasonable defaults
		if self.conf.http_parameters.timeout is None:
			try:
				from . import cfg
				self.conf.http_parameters.timeout = cfg.loop.interval / 2
			except (ImportError, KeyError): self.conf.http_parameters.timeout = 30
		self.conf.http_parameters.auth = HTTPBasicAuth(*self.conf.http_parameters.auth)

		requests.defaults.keep_alive = True
		requests.defaults.max_retries = max(3, self.conf.http_parameters.timeout / 5)

		# Try to init concurrent (async) dispatcher
		self.send = lambda chunk, **kwz: requests.post(data=chunk, **kwz)
		if self.conf.chunk_data.enabled or self.conf.chunk_data.enabled is None:
			try: from requests import async
			except RuntimeError as err:
				if self.conf.chunk_data.enabled: raise
				else:
					log.warn(( 'Failed to initialize requests.async'
						' engine (gevent module missing?): {}, concurrent'
						' (chunked) measurements submission will be disabled' ).format(err))
					self.conf.chunk_data.enabled = False
			else:
				self.conf.chunk_data.enabled = True
				if not self.conf.chunk_data.max_concurrent_requests\
						or self.conf.chunk_data.max_concurrent_requests <= 0:
					self.conf.chunk_data.max_concurrent_requests = None
				self.send = lambda *chunks, **kwz:\
					map( op.methodcaller('raise_for_status'),
						async.map(
							list(async.post(data=chunk, **kwz) for chunk in chunks),
							size=self.conf.chunk_data.max_concurrent_requests ) )

	def measurement(self, name, value, ts_dp=None):
		measurement = dict()
		if self.conf.source_from_prefix:
			measurement['source'], name = name.split('.', 1)
		elif self.conf.source: measurement['source'] = self.conf.source
		if ts_dp: measurement['measure_time'] = ts_dp
		measurement.update(name=name, value=value)
		return measurement

	def dispatch(self, *tuples):
		data = dict()
		if self.conf.unified_measure_time:
			data['measure_time'] = int(time())
			tuples = list((name, value, None) for name, value, ts_dp in tuples)
		if self.conf.chunk_data.enabled\
				and len(tuples) > self.conf.chunk_data.max_chunk_size:
			chunks, n = list(), 0
			while n < len(tuples):
				n_to = n + self.conf.chunk_data.max_chunk_size
				chunk = data.copy()
				chunk['gauges'] = list(it.starmap(self.measurement, tuples[n:n_to]))
				chunks.append(chunk)
				n = n_to
			log.debug(( 'Splitting {} measurements'
				' into {} concurrent requests' ).format(len(tuples), len(chunks)))
			data = map(dumps, chunks)
			del tuples, chunk, chunks # to gc ram from this corpus of data
		else: # single chunk
			data['gauges'] = list(it.starmap(self.measurement, tuples))
			data = [dumps(data)]
			del tuples
		self.send(*data, headers={
			'content-type': 'application/json' }, **self.conf.http_parameters)


sink = LibratoMetrics

########NEW FILE########
