__FILENAME__ = BFLMiner
from Miner import Miner
from Queue import Empty
from ioutil import find_udev, find_serial_by_id, find_com_ports
from log import say_line, say_exception
from serial.serialutil import SerialException
from struct import pack, unpack, error
from sys import maxint
from time import time, sleep
from util import Object, uint32, bytereverse
import serial

CHECK_INTERVAL = 0.01


def open_device(port):
	return serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

def is_good_init(response):
	return response and response[:31] == b'>>>ID: BitFORCE SHA256 Version ' and response[-4:] == b'>>>\n'

def init_device(device):
	return request(device, b'ZGX')

def request(device, message):
	if device:
		device.flushInput()
		device.write(message)
		return device.readline()

def check(port, likely=True):
	result = False
	try:
		device = open_device(port)
		response = init_device(device)
		device.close()
		result = is_good_init(response)
	except SerialException:
		if likely:
			say_exception()
	if not likely and result:
		say_line('Found BitFORCE on %s', port)
	elif likely and not result:
		say_line('No valid response from BitFORCE on %s', port)
	return result

def initialize(options):
	ports = find_udev(check, 'BitFORCE*SHA256') or find_serial_by_id(check, 'BitFORCE_SHA256') or find_com_ports(check)

	if not options.device and ports:
		print '\nBFL devices on ports:\n'
		for i in xrange(len(ports)):
			print '[%d]\t%s' % (i, ports[i])

	miners = [
		BFLMiner(i, ports[i], options)
		for i in xrange(len(ports))
		if (
			(not options.device) or
			(i in options.device)
		)
	]

	for i in xrange(len(miners)):
		miners[i].cutoff_temp = options.cutoff_temp[min(i, len(options.cutoff_temp) - 1)]
		miners[i].cutoff_interval = options.cutoff_interval[min(i, len(options.cutoff_interval) - 1)]
	return miners

class BFLMiner(Miner):
	def __init__(self, device_index, port, options):
		super(BFLMiner, self).__init__(device_index, options)
		self.port = port
		self.device_name = 'BFL:'+str(self.device_index)

		self.check_interval = CHECK_INTERVAL
		self.last_job = None
		self.min_interval = maxint

	def id(self):
		return self.device_name

	def is_ok(self, response):
		return response and response == b'OK\n'

	def put_job(self):
		if self.busy: return

		temperature = self.get_temperature()
		if temperature < self.cutoff_temp:
			response = request(self.device, b'ZDX')
			if self.is_ok(response):
				if self.switch.update_time:
					self.job.time = bytereverse(uint32(long(time())) - self.job.time_delta)
				data = b''.join([pack('<8I', *self.job.state), pack('<3I', self.job.merkle_end, self.job.time, self.job.difficulty)])
				response = request(self.device, b''.join([b'>>>>>>>>', data, b'>>>>>>>>']))
				if self.is_ok(response):
					self.busy = True
					self.job_started = time()

					self.last_job = Object()
					self.last_job.header = self.job.header
					self.last_job.merkle_end = self.job.merkle_end
					self.last_job.time = self.job.time
					self.last_job.difficulty = self.job.difficulty
					self.last_job.target = self.job.target
					self.last_job.state = self.job.state
					self.last_job.job_id = self.job.job_id
					self.last_job.extranonce2 = self.job.extranonce2
					self.last_job.server = self.job.server
					self.last_job.miner = self

					self.check_interval = CHECK_INTERVAL
					if not self.switch.update_time or bytereverse(self.job.time) - bytereverse(self.job.original_time) > 55:
						self.update = True
						self.job = None
				else:
					say_line('%s: bad response when sending block data: %s', (self.id(), response))
			else:
				say_line('%s: bad response when submitting job (ZDX): %s', (self.id(), response))
		else:
			say_line('%s: temperature exceeds cutoff, waiting...', self.id())

	def get_temperature(self):
		response = request(self.device, b'ZLX')
		if len(response) < 23 or response[0] != b'T' or response[-1:] != b'\n':
			say_line('%s: bad response for temperature: %s', (self.id(), response))
			return 0
		return float(response[23:-1])

	def check_result(self):
		response = request(self.device, b'ZFX')
		if response.startswith(b'B'): return False
		if response == b'NO-NONCE\n': return response
		if response[:12] != 'NONCE-FOUND:' or response[-1:] != '\n':
			say_line('%s: bad response checking result: %s', (self.id(), response))
			return None
		return response[12:-1]

	def nonce_generator(self, nonces):
		for nonce in nonces.split(b','):
			if len(nonce) != 8: continue
			try:
				yield unpack('<I', nonce.decode('hex')[::-1])[0]
			except error:
				pass

	def mining_thread(self):
		say_line('started BFL miner on %s', (self.id()))

		while not self.should_stop:
			try:
				self.device = open_device(self.port)
				response = init_device(self.device)
				if not is_good_init(response):
					say_line('Failed to initialize %s (response: %s), retrying...', (self.id(), response))
					self.device.close()
					self.device = None
					sleep(1)
					continue

				last_rated = time()
				iterations = 0
		
				self.job = None
				self.busy = False
				while not self.should_stop:
					if (not self.job) or (not self.work_queue.empty()):
						try:
							self.job = self.work_queue.get(True, 1)
						except Empty:
							if not self.busy:
								continue
						else:
							if not self.job and not self.busy:
								continue
							targetQ = self.job.targetQ
							self.job.original_time = self.job.time
							self.job.time_delta = uint32(long(time())) - bytereverse(self.job.time)

					if not self.busy:
						self.put_job()
					else:
						result = self.check_result()
						if result:
							now = time()
							
							self.busy = False
							r = self.last_job
							job_duration = now - self.job_started
							self.put_job()
	
							self.min_interval = min(self.min_interval, job_duration)
	
							iterations += 4294967296
							t = now - last_rated
							if t > self.options.rate:
								self.update_rate(now, iterations, t, targetQ)
								last_rated = now; iterations = 0

							if result != b'NO-NONCE\n':
								r.nonces = result
								self.switch.put(r)

							sleep(self.min_interval - (CHECK_INTERVAL * 2))
						else:
							if result is None:
								self.check_interval = min(self.check_interval * 2, 1)
	
					sleep(self.check_interval)
			except Exception:
				say_exception()
				if self.device:
					self.device.close()
					self.device = None
				sleep(1)
########NEW FILE########
__FILENAME__ = detect
from sys import platform

WINDOWS = LINUX = MACOSX = None

WINDOWS = platform.startswith('win')
LINUX = platform.startswith('linux')
MACOSX = (platform == 'darwin')

########NEW FILE########
__FILENAME__ = GetworkSource
from Source import Source
from base64 import b64encode
from httplib import HTTPException
from json import dumps, loads
from log import say_exception, say_line
from struct import pack
from threading import Thread
from time import sleep, time
from urlparse import urlsplit
import httplib
import socket
import socks





class NotAuthorized(Exception): pass
class RPCError(Exception): pass

class GetworkSource(Source):
	def __init__(self, switch):
		super(GetworkSource, self).__init__(switch)

		self.connection = self.lp_connection = None
		self.long_poll_timeout = 3600
		self.max_redirects = 3

		self.postdata = {'method': 'getwork', 'id': 'json'}
		self.headers = {"User-Agent": self.switch.user_agent, "Authorization": 'Basic ' + b64encode('%s:%s' % (self.server().user, self.server().pwd)), "X-Mining-Extensions": 'hostlist midstate rollntime'}
		self.long_poll_url = ''

		self.long_poll_active = False

		self.authorization_failed = False

	def loop(self):
		if self.authorization_failed: return
		super(GetworkSource, self).loop()

		thread = Thread(target=self.long_poll_thread)
		thread.daemon = True
		thread.start()

		while True:
			if self.should_stop: return

			if self.check_failback():
				return True

			try:
				with self.switch.lock:
					miner = self.switch.updatable_miner()
					while miner:
						work = self.getwork()
						self.queue_work(work, miner)
						miner = self.switch.updatable_miner()

				self.process_result_queue()
				sleep(1)
			except Exception:
				say_exception("Unexpected error:")
				break

	def ensure_connected(self, connection, proto, host):
		if connection != None and connection.sock != None:
			return connection, False

		if proto == 'https': connector = httplib.HTTPSConnection
		else: connector = httplib.HTTPConnection

		if not self.options.proxy:
			return connector(host, strict=True), True

		host, port = host.split(':')
		connection = connector(host, strict=True)
		connection.sock = socks.socksocket()
		p = self.options.proxy
		connection.sock.setproxy(p.type, p.host, p.port, True, p.user, p.pwd)
		try:
			connection.sock.connect((host, int(port)))
		except socks.Socks5AuthError:
			say_exception('Proxy error:')
			self.stop()
		return connection, True

	def request(self, connection, url, headers, data=None, timeout=0):
		result = response = None
		try:
			if data: connection.request('POST', url, data, headers)
			else: connection.request('GET', url, headers=headers)
			response = self.timeout_response(connection, timeout)
			if not response:
				return None
			if response.status == httplib.UNAUTHORIZED:
				say_line('Wrong username or password for %s', self.server().name)
				self.authorization_failed = True
				raise NotAuthorized()
			r = self.max_redirects
			while response.status == httplib.TEMPORARY_REDIRECT:
				response.read()
				url = response.getheader('Location', '')
				if r == 0 or url == '': raise HTTPException('Too much or bad redirects')
				connection.request('GET', url, headers=headers)
				response = self.timeout_response(connection, timeout)
				r -= 1
			self.long_poll_url = response.getheader('X-Long-Polling', '')
			self.switch.update_time = bool(response.getheader('X-Roll-NTime', ''))
			hostList = response.getheader('X-Host-List', '')
			self.stratum_header = response.getheader('x-stratum', '')
			if (not self.options.nsf) and hostList: self.switch.add_servers(loads(hostList))
			result = loads(response.read())
			if result['error']:
				say_line('server error: %s', result['error']['message'])
				raise RPCError(result['error']['message'])
			return (connection, result)
		finally:
			if not result or not response or (response.version == 10 and response.getheader('connection', '') != 'keep-alive') or response.getheader('connection', '') == 'close':
				connection.close()
				connection = None

	def timeout_response(self, connection, timeout):
		if timeout:
			start = time()
			connection.sock.settimeout(5)
			response = None
			while not response:
				if self.should_stop or time() - start > timeout: return
				try:
					response = connection.getresponse()
				except socket.timeout:
					pass
			connection.sock.settimeout(timeout)
			return response
		else:
			return connection.getresponse()

	def getwork(self, data=None):
		try:
			self.connection = self.ensure_connected(self.connection, self.server().proto, self.server().host)[0]
			self.postdata['params'] = [data] if data else []
			(self.connection, result) = self.request(self.connection, '/', self.headers, dumps(self.postdata))

			self.switch.connection_ok()

			return result['result']
		except (IOError, httplib.HTTPException, ValueError, socks.ProxyError, NotAuthorized, RPCError):
			self.stop()
		except Exception:
			say_exception()

	def send_internal(self, result, nonce):
		data = ''.join([result.header.encode('hex'), pack('<3I', long(result.time), long(result.difficulty), long(nonce)).encode('hex'), '000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'])
		accepted = self.getwork(data)
		if accepted != None:
			self.switch.report(result.miner, nonce, accepted)
			return True

	def long_poll_thread(self):
		last_host = None
		while True:
			if self.should_stop or self.authorization_failed:
				return

			url = self.long_poll_url
			if url != '':
				proto = self.server().proto
				host = self.server().host
				parsedUrl = urlsplit(url)
				if parsedUrl.scheme != '':
					proto = parsedUrl.scheme
				if parsedUrl.netloc != '':
					host = parsedUrl.netloc
					url = url[url.find(host) + len(host):]
					if url == '': url = '/'
				try:
					if host != last_host: self.close_lp_connection()
					self.lp_connection, changed = self.ensure_connected(self.lp_connection, proto, host)
					if changed:
						say_line("LP connected to %s", self.server().name)
						last_host = host

					self.long_poll_active = True
					response = self.request(self.lp_connection, url, self.headers, timeout=self.long_poll_timeout)
					self.long_poll_active = False
					if response:
						(self.lp_connection, result) = response
						self.queue_work(result['result'])
						if self.options.verbose:
							say_line('long poll: new block %s%s', (result['result']['data'][56:64], result['result']['data'][48:56]))
				except (IOError, httplib.HTTPException, ValueError, socks.ProxyError, NotAuthorized, RPCError):
					say_exception('long poll IO error')
					self.close_lp_connection()
					sleep(.5)
				except Exception:
					say_exception()

	def stop(self):
		self.should_stop = True
		self.close_lp_connection()
		self.close_connection()

	def close_connection(self):
		if self.connection:
			self.connection.close()
			self.connection = None

	def close_lp_connection(self):
		if self.lp_connection:
			self.lp_connection.close()
			self.lp_connection = None

	def queue_work(self, work, miner=None):
		if work:
			if not 'target' in work:
				work['target'] = '0000000000000000000000000000000000000000000000000000ffff00000000'

			self.switch.queue_work(self, work['data'], work['target'], miner=miner)

	def detect_stratum(self):
		work = self.getwork()
		if self.authorization_failed:
			return False

		if work:
			if self.stratum_header:
				host = self.stratum_header
				proto = host.find('://')
				if proto != -1:
					host = self.stratum_header[proto+3:]
				#this doesn't work in windows/python 2.6
				#host = urlparse.urlparse(self.stratum_header).netloc
				say_line('diverted to stratum on %s', host)
				return host
			else:
				say_line('using JSON-RPC (no stratum header)')
				self.queue_work(work)
				return False

		say_line('no response to getwork, using as stratum')
		return self.server().host
########NEW FILE########
__FILENAME__ = ioutil
from detect import LINUX, WINDOWS
from glob import glob


def find_udev(check, product_id):
	ports = []
	if LINUX:
		try:
			import pyudev

			context = pyudev.Context()
			for device in context.list_devices(subsystem='tty', ID_MODEL=product_id):
				if check(device.device_node):
					ports.append(device.device_node)
		except ImportError:
			pass		
	return ports

def find_serial_by_id(check, product_id):
	ports = []
	if LINUX:
		for port in glob('/dev/serial/by-id/*' + product_id + '*'):
			if check(port):
				ports.append(port)
	return ports

def find_com_ports(check):
	ports = []
	if WINDOWS:
		from serial.tools import list_ports
		com_ports = [p[0] for p in list_ports.comports()]
		com_ports.sort()
		for port in com_ports:
			if check(port, False):
				ports.append(port)
	else:
		for port in glob('/dev/ttyUSB*'):
			if check(port):
				ports.append(port)
	return ports
########NEW FILE########
__FILENAME__ = log
from datetime import datetime
from threading import RLock
import sys
import traceback

quiet = False
verbose = False
server = ''
lock = RLock()

TIME_FORMAT = '%d/%m/%Y %H:%M:%S'

def say(format_, args=(), say_quiet=False):
	if quiet and not say_quiet: return
	with lock:
		p = format_ % args
		if verbose:
			print '%s %s,' % (server, datetime.now().strftime(TIME_FORMAT)), p
		else:
			sys.stdout.write('\r%s\r%s %s' % (' '*80, server, p))
		sys.stdout.flush()

def say_line(format_, args=()):
	if not verbose:
		format_ = '%s, %s\n' % (datetime.now().strftime(TIME_FORMAT), format_)
	say(format_, args)

def say_exception(message=''):
	type_, value, tb = sys.exc_info()
	say_line(message + ' %s', str(value))
	if verbose:
		traceback.print_exception(type_, value, tb)

def say_quiet(format_, args=()):
	say(format_, args, True)

########NEW FILE########
__FILENAME__ = Miner
from Queue import Queue
from threading import Thread
from time import time


class Miner(object):
	def __init__(self, device_index, options):
		self.device_index = device_index
		self.options = options

		self.update_time_counter = 1
		self.share_count = [0, 0]
		self.work_queue = Queue()

		self.update = True

		self.accept_hist = []
		self.rate = self.estimated_rate = 0

	def start(self):
		self.should_stop = False
		Thread(target=self.mining_thread).start()
		self.start_time = time()

	def stop(self, message = None):
		if message: print '\n%s' % message
		self.should_stop = True

	def update_rate(self, now, iterations, t, targetQ, rate_divisor=1000):
		self.rate = int((iterations / t) / rate_divisor)
		self.rate = float(self.rate) / 1000
		if self.accept_hist:
			LAH = self.accept_hist.pop()
			if LAH[1] != self.share_count[1]:
				self.accept_hist.append(LAH)
		self.accept_hist.append((now, self.share_count[1]))
		while (self.accept_hist[0][0] < now - self.options.estimate):
			self.accept_hist.pop(0)
		new_accept = self.share_count[1] - self.accept_hist[0][1]
		self.estimated_rate = float(new_accept) * (targetQ) / min(int(now - self.start_time), self.options.estimate) / 1000
		self.estimated_rate = float(self.estimated_rate) / 1000

		self.switch.status_updated(self)
########NEW FILE########
__FILENAME__ = OpenCLMiner
from detect import MACOSX
from Miner import Miner
from Queue import Empty
from hashlib import md5
from log import say_line
from sha256 import partial, calculateF
from struct import pack, unpack, error
from threading import Lock
from time import sleep, time
from util import uint32, Object, bytereverse, tokenize, \
	bytearray_to_uint32
import sys


PYOPENCL = False
OPENCL = False
ADL = False


try:
	import pyopencl as cl
	PYOPENCL = True
except ImportError:
	print '\nNo PyOpenCL\n'

if PYOPENCL:
	try:
		platforms = cl.get_platforms()
		if len(platforms):
			OPENCL = True
		else:
			print '\nNo OpenCL platforms\n'
	except Exception:
		print '\nNo OpenCL\n'

def vectors_definition():
	if MACOSX:
		return '-D VECTORS'
	return '-DVECTORS'

def is_amd(platform):
	if 'amd' in platform.name.lower():
		return True
	return False

def has_amd():
	for platform in cl.get_platforms():
		if is_amd(platform):
			return True
	return False

if OPENCL:
	try:
		from adl3 import ADL_Main_Control_Create, ADL_Main_Memory_Alloc, ADL_Main_Control_Destroy, \
			ADLTemperature, ADL_Overdrive5_Temperature_Get, ADL_Adapter_NumberOfAdapters_Get, \
			AdapterInfo, LPAdapterInfo, ADL_Adapter_AdapterInfo_Get, ADL_Adapter_ID_Get, \
			ADL_OK
		from ctypes import sizeof, byref, c_int, cast
		from collections import namedtuple
		if ADL_Main_Control_Create(ADL_Main_Memory_Alloc, 1) != ADL_OK:
			print "\nCouldn't initialize ADL interface.\n"
		else:
			ADL = True
			adl_lock = Lock()
	except ImportError:
		if has_amd():
			print '\nWARNING: no adl3 module found (github.com/mjmvisser/adl3), temperature control is disabled\n'
	except OSError:# if no ADL is present i.e. no AMD platform
		print '\nWARNING: ADL missing (no AMD platform?), temperature control is disabled\n'
else:
	print "\nNot using OpenCL\n"

def shutdown():
	if ADL:
		ADL_Main_Control_Destroy()


def initialize(options):
	if not OPENCL:
		options.no_ocl = True
		return []

	options.worksize = tokenize(options.worksize, 'worksize')
	options.frames = tokenize(options.frames, 'frames', [30])
	options.frameSleep = tokenize(options.frameSleep, 'frameSleep', cast=float)
	options.vectors = [True] if options.old_vectors else tokenize(options.vectors, 'vectors', [False], bool)

	platforms = cl.get_platforms()

	if options.platform >= len(platforms) or (options.platform == -1 and len(platforms) > 1):
		print 'Wrong platform or more than one OpenCL platforms found, use --platform to select one of the following\n'
		for i in xrange(len(platforms)):
			print '[%d]\t%s' % (i, platforms[i].name)
		sys.exit()

	if options.platform == -1:
		options.platform = 0

	devices = platforms[options.platform].get_devices()

	if not options.device and devices:
		print '\nOpenCL devices:\n'
		for i in xrange(len(devices)):
			print '[%d]\t%s' % (i, devices[i].name)
		print '\nNo devices specified, using all GPU devices\n'

	miners = [
		OpenCLMiner(i, options)
		for i in xrange(len(devices))
		if (
			(not options.device and devices[i].type == cl.device_type.GPU) or
			(i in options.device)
		)
	]

	for i in xrange(len(miners)):
		miners[i].worksize = options.worksize[min(i, len(options.worksize) - 1)]
		miners[i].frames = options.frames[min(i, len(options.frames) - 1)]
		miners[i].frameSleep = options.frameSleep[min(i, len(options.frameSleep) - 1)]
		miners[i].vectors = options.vectors[min(i, len(options.vectors) - 1)]
		miners[i].cutoff_temp = options.cutoff_temp[min(i, len(options.cutoff_temp) - 1)]
		miners[i].cutoff_interval = options.cutoff_interval[min(i, len(options.cutoff_interval) - 1)]
	return miners


class OpenCLMiner(Miner):
	def __init__(self, device_index, options):
		super(OpenCLMiner, self).__init__(device_index, options)
		self.output_size = 0x100

		self.device = cl.get_platforms()[options.platform].get_devices()[device_index]
		self.device_name = self.device.name.strip('\r\n \x00\t')
		self.frames = 30

		self.worksize = self.frameSleep= self.rate = self.estimated_rate = 0
		self.vectors = False

		self.adapterIndex = None
		if ADL and is_amd(self.device.platform) and self.device.type == cl.device_type.GPU:
			with adl_lock:
				self.adapterIndex = self.get_adapter_info()
				if self.adapterIndex:
					self.adapterIndex = self.adapterIndex[self.device_index].iAdapterIndex

	def id(self):
		return str(self.options.platform) + ':' + str(self.device_index) + ':' + self.device_name

	def nonce_generator(self, nonces):
		for i in xrange(0, len(nonces) - 4, 4):
			nonce = bytearray_to_uint32(nonces[i:i+4])
			if nonce:
				yield nonce


	def mining_thread(self):
		say_line('started OpenCL miner on platform %d, device %d (%s)', (self.options.platform, self.device_index, self.device_name))

		(self.defines, rate_divisor, hashspace) = (vectors_definition(), 500, 0x7FFFFFFF) if self.vectors else ('', 1000, 0xFFFFFFFF)
		self.defines += (' -DOUTPUT_SIZE=' + str(self.output_size))
		self.defines += (' -DOUTPUT_MASK=' + str(self.output_size - 1))

		self.load_kernel()
		frame = 1.0 / max(self.frames, 3)
		unit = self.worksize * 256
		global_threads = unit * 10

		queue = cl.CommandQueue(self.context)

		last_rated_pace = last_rated = last_n_time = last_temperature = time()
		base = last_hash_rate = threads_run_pace = threads_run = 0
		output = bytearray((self.output_size + 1) * 4)
		output_buffer = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY | cl.mem_flags.USE_HOST_PTR, hostbuf=output)
		self.kernel.set_arg(20, output_buffer)

		work = None
		temperature = 0
		while True:
			if self.should_stop: return

			sleep(self.frameSleep)

			if (not work) or (not self.work_queue.empty()):
				try:
					work = self.work_queue.get(True, 1)
				except Empty: continue
				else:
					if not work: continue
					nonces_left = hashspace
					state = work.state
					f = [0] * 8
					state2 = partial(state, work.merkle_end, work.time, work.difficulty, f)
					calculateF(state, work.merkle_end, work.time, work.difficulty, f, state2)

					self.kernel.set_arg(0, pack('<I', state[0]))
					self.kernel.set_arg(1, pack('<I', state[1]))
					self.kernel.set_arg(2, pack('<I', state[2]))
					self.kernel.set_arg(3, pack('<I', state[3]))
					self.kernel.set_arg(4, pack('<I', state[4]))
					self.kernel.set_arg(5, pack('<I', state[5]))
					self.kernel.set_arg(6, pack('<I', state[6]))
					self.kernel.set_arg(7, pack('<I', state[7]))

					self.kernel.set_arg(8, pack('<I', state2[1]))
					self.kernel.set_arg(9, pack('<I', state2[2]))
					self.kernel.set_arg(10, pack('<I', state2[3]))
					self.kernel.set_arg(11, pack('<I', state2[5]))
					self.kernel.set_arg(12, pack('<I', state2[6]))
					self.kernel.set_arg(13, pack('<I', state2[7]))

					self.kernel.set_arg(15, pack('<I', f[0]))
					self.kernel.set_arg(16, pack('<I', f[1]))
					self.kernel.set_arg(17, pack('<I', f[2]))
					self.kernel.set_arg(18, pack('<I', f[3]))
					self.kernel.set_arg(19, pack('<I', f[4]))

			if temperature < self.cutoff_temp:
				self.kernel.set_arg(14, pack('<I', base))
				cl.enqueue_nd_range_kernel(queue, self.kernel, (global_threads,), (self.worksize,))

				nonces_left -= global_threads
				threads_run_pace += global_threads
				threads_run += global_threads
				base = uint32(base + global_threads)
			else:
				threads_run_pace = 0
				last_rated_pace = time()
				sleep(self.cutoff_interval)

			now = time()
			if self.adapterIndex != None:
				t = now - last_temperature
				if temperature >= self.cutoff_temp or t > 1:
					last_temperature = now
					with adl_lock:
						temperature = self.get_temperature()

			t = now - last_rated_pace
			if t > 1:
				rate = (threads_run_pace / t) / rate_divisor
				last_rated_pace = now; threads_run_pace = 0
				r = last_hash_rate / rate
				if r < 0.9 or r > 1.1:
					global_threads = max(unit * int((rate * frame * rate_divisor) / unit), unit)
					last_hash_rate = rate

			t = now - last_rated
			if t > self.options.rate:
				self.update_rate(now, threads_run, t, work.targetQ, rate_divisor)
				last_rated = now; threads_run = 0

			queue.finish()
			cl.enqueue_read_buffer(queue, output_buffer, output)
			queue.finish()

			if output[-1]:
				result = Object()
				result.header = work.header
				result.merkle_end = work.merkle_end
				result.time = work.time
				result.difficulty = work.difficulty
				result.target = work.target
				result.state = list(state)
				result.nonces = output[:]
				result.job_id = work.job_id
				result.extranonce2 = work.extranonce2
				result.server = work.server
				result.miner = self
				self.switch.put(result)
				output[:] = b'\x00' * len(output)
				cl.enqueue_write_buffer(queue, output_buffer, output)

			if not self.switch.update_time:
				if nonces_left < 3 * global_threads * self.frames:
					self.update = True
					nonces_left += 0xFFFFFFFFFFFF
				elif 0xFFFFFFFFFFF < nonces_left < 0xFFFFFFFFFFFF:
					say_line('warning: job finished, %s is idle', self.id()) 
					work = None
			elif now - last_n_time > 1:
				work.time = bytereverse(bytereverse(work.time) + 1)
				state2 = partial(state, work.merkle_end, work.time, work.difficulty, f)
				calculateF(state, work.merkle_end, work.time, work.difficulty, f, state2)
				self.kernel.set_arg(8, pack('<I', state2[1]))
				self.kernel.set_arg(9, pack('<I', state2[2]))
				self.kernel.set_arg(10, pack('<I', state2[3]))
				self.kernel.set_arg(11, pack('<I', state2[5]))
				self.kernel.set_arg(12, pack('<I', state2[6]))
				self.kernel.set_arg(13, pack('<I', state2[7]))
				self.kernel.set_arg(15, pack('<I', f[0]))
				self.kernel.set_arg(16, pack('<I', f[1]))
				self.kernel.set_arg(17, pack('<I', f[2]))
				self.kernel.set_arg(18, pack('<I', f[3]))
				self.kernel.set_arg(19, pack('<I', f[4]))
				last_n_time = now
				self.update_time_counter += 1
				if self.update_time_counter >= self.switch.max_update_time:
					self.update = True
					self.update_time_counter = 1

	def load_kernel(self):
		self.context = cl.Context([self.device], None, None)
		if (self.device.extensions.find('cl_amd_media_ops') != -1):
			self.defines += ' -DBITALIGN'
			if self.device_name in ['Cedar',
									'Redwood',
									'Juniper',
									'Cypress',
									'Hemlock',
									'Caicos',
									'Turks',
									'Barts',
									'Cayman',
									'Antilles',
									'Wrestler',
									'Zacate',
									'WinterPark',
									'BeaverCreek']:
				self.defines += ' -DBFI_INT'

		kernel_file = open('phatk.cl', 'r')
		kernel = kernel_file.read()
		kernel_file.close()
		m = md5(); m.update(''.join([self.device.platform.name, self.device.platform.version, self.device.name, self.defines, kernel]))
		cache_name = '%s.elf' % m.hexdigest()
		binary = None
		try:
			binary = open(cache_name, 'rb')
			self.program = cl.Program(self.context, [self.device], [binary.read()]).build(self.defines)
		except (IOError, cl.LogicError):
			self.program = cl.Program(self.context, kernel).build(self.defines)
			if (self.defines.find('-DBFI_INT') != -1):
				patchedBinary = self.patch(self.program.binaries[0])
				self.program = cl.Program(self.context, [self.device], [patchedBinary]).build(self.defines)
			binaryW = open(cache_name, 'wb')
			binaryW.write(self.program.binaries[0])
			binaryW.close()
		finally:
			if binary: binary.close()

		self.kernel = self.program.search

		if not self.worksize:
			self.worksize = self.kernel.get_work_group_info(cl.kernel_work_group_info.WORK_GROUP_SIZE, self.device)

	def get_temperature(self):
		temperature = ADLTemperature()
		temperature.iSize = sizeof(temperature)

		if ADL_Overdrive5_Temperature_Get(self.adapterIndex, 0, byref(temperature)) == ADL_OK:
			return temperature.iTemperature/1000.0
		return 0

	def get_adapter_info(self):
		adapter_info = []
		num_adapters = c_int(-1)
		if ADL_Adapter_NumberOfAdapters_Get(byref(num_adapters)) != ADL_OK:
			say_line("ADL_Adapter_NumberOfAdapters_Get failed, cutoff temperature disabled for %s", self.id())
			return

		AdapterInfoArray = (AdapterInfo * num_adapters.value)()

		if ADL_Adapter_AdapterInfo_Get(cast(AdapterInfoArray, LPAdapterInfo), sizeof(AdapterInfoArray)) != ADL_OK:
			say_line("ADL_Adapter_AdapterInfo_Get failed, cutoff temperature disabled for %s", self.id())
			return

		deviceAdapter = namedtuple('DeviceAdapter', ['AdapterIndex', 'AdapterID', 'BusNumber', 'UDID'])
		devices = []

		for adapter in AdapterInfoArray:
			index = adapter.iAdapterIndex
			busNum = adapter.iBusNumber
			udid = adapter.strUDID

			adapterID = c_int(-1)

			if ADL_Adapter_ID_Get(index, byref(adapterID)) != ADL_OK:
				say_line("ADL_Adapter_ID_Get failed, cutoff temperature disabled for %s", self.id())
				return

			found = False
			for device in devices:
				if (device.AdapterID.value == adapterID.value):
					found = True
					break

			if (found == False):
				devices.append(deviceAdapter(index, adapterID, busNum, udid))

		for device in devices:
			adapter_info.append(AdapterInfoArray[device.AdapterIndex])

		return adapter_info

	def patch(self, data):
		pos = data.find('\x7fELF', 1)
		if pos != -1 and data.find('\x7fELF', pos+1) == -1:
			data2 = data[pos:]
			try:
				(id, a, b, c, d, e, f, offset, g, h, i, j, entrySize, count, index) = unpack('QQHHIIIIIHHHHHH', data2[:52])
				if id == 0x64010101464c457f and offset != 0:
					(a, b, c, d, nameTableOffset, size, e, f, g, h) = unpack('IIIIIIIIII', data2[offset+index * entrySize : offset+(index+1) * entrySize])
					header = data2[offset : offset+count * entrySize]
					firstText = True
					for i in xrange(count):
						entry = header[i * entrySize : (i+1) * entrySize]
						(nameIndex, a, b, c, offset, size, d, e, f, g) = unpack('IIIIIIIIII', entry)
						nameOffset = nameTableOffset + nameIndex
						name = data2[nameOffset : data2.find('\x00', nameOffset)]
						if name == '.text':
							if firstText: firstText = False
							else:
								data2 = data2[offset : offset + size]
								patched = ''
								for i in xrange(len(data2) / 8):
									instruction, = unpack('Q', data2[i * 8 : i * 8 + 8])
									if (instruction&0x9003f00002001000) == 0x0001a00000000000:
										instruction ^= (0x0001a00000000000 ^ 0x0000c00000000000)
									patched += pack('Q', instruction)
								return ''.join([data[:pos+offset], patched, data[pos + offset + size:]])
			except error:
				pass
		return data

########NEW FILE########
__FILENAME__ = poclbm
#!/usr/bin/env python

from Switch import Switch
from optparse import OptionGroup, OptionParser
from time import sleep
from util import tokenize
from version import VERSION
import log
import socket


class LongPollingSocket(socket.socket):
	"""
	Socket wrapper to enable socket.TCP_NODELAY and KEEPALIVE
	"""
	def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
		super(LongPollingSocket, self).__init__(family, type, proto)
		if type == socket.SOCK_STREAM:
			self.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			self.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
		self.settimeout(5)

socket.socket = LongPollingSocket


usage = "usage: %prog [OPTION]... SERVER[#tag]...\nSERVER is one or more [http[s]|stratum://]user:pass@host:port          (required)\n[#tag] is a per SERVER user friendly name displayed in stats (optional)"
parser = OptionParser(version=VERSION, usage=usage)
parser.add_option('--verbose',        dest='verbose',        action='store_true', help='verbose output, suitable for redirection to log file')
parser.add_option('-q', '--quiet',    dest='quiet',          action='store_true', help='suppress all output except hash rate display')
parser.add_option('--proxy',          dest='proxy',          default='',          help='specify as [[socks4|socks5|http://]user:pass@]host:port (default proto is socks5)')
parser.add_option('--no-ocl',         dest='no_ocl',         action='store_true', help="don't use OpenCL")
parser.add_option('--no-bfl',         dest='no_bfl',         action='store_true', help="don't use Butterfly Labs")
parser.add_option('--stratum-proxies',dest='stratum_proxies',action='store_true', help="search for and use stratum proxies in subnet")
parser.add_option('-d', '--device',   dest='device',         default=[],          help='comma separated device IDs, by default will use all (for OpenCL - only GPU devices)')

group = OptionGroup(parser, "Miner Options")
group.add_option('-r', '--rate',          dest='rate',       default=1,       help='hash rate display interval in seconds, default=1 (60 with --verbose)', type='float')
group.add_option('-e', '--estimate',      dest='estimate',   default=900,     help='estimated rate time window in seconds, default 900 (15 minutes)', type='int')
group.add_option('-t', '--tolerance',     dest='tolerance',  default=2,       help='use fallback pool only after N consecutive connection errors, default 2', type='int')
group.add_option('-b', '--failback',      dest='failback',   default=60,      help='attempt to fail back to the primary pool after N seconds, default 60', type='int')
group.add_option('--cutoff-temp',         dest='cutoff_temp',default=[],      help='AMD GPUs, BFL only. For GPUs requires github.com/mjmvisser/adl3. Comma separated temperatures at which to skip kernel execution, in C, default=95')
group.add_option('--cutoff-interval',     dest='cutoff_interval',default=[],  help='how long to not execute calculations if CUTOFF_TEMP is reached, in seconds, default=0.01')
group.add_option('--no-server-failbacks', dest='nsf',        action='store_true', help='disable using failback hosts provided by server')
parser.add_option_group(group)

group = OptionGroup(parser,
	"OpenCL Options",
	"Every option except 'platform' and 'vectors' can be specified as a comma separated list. "
	"If there aren't enough entries specified, the last available is used. "
	"Use --vv to specify per-device vectors usage."
)
group.add_option('-p', '--platform', dest='platform',   default=-1,          help='use platform by id', type='int')
group.add_option('-w', '--worksize', dest='worksize',   default=[],          help='work group size, default is maximum returned by OpenCL')
group.add_option('-f', '--frames',   dest='frames',     default=[],          help='will try to bring single kernel execution to 1/frames seconds, default=30, increase this for less desktop lag')
group.add_option('-s', '--sleep',    dest='frameSleep', default=[],          help='sleep per frame in seconds, default 0')
group.add_option('--vv',             dest='vectors',    default=[],          help='use vectors, default false')
group.add_option('-v', '--vectors',  dest='old_vectors',action='store_true', help='use vectors')
parser.add_option_group(group)

(options, options.servers) = parser.parse_args()

log.verbose = options.verbose
log.quiet = options.quiet

options.rate = max(options.rate, 60) if options.verbose else max(options.rate, 0.1)

options.version = VERSION

options.max_update_time = 60

options.device = tokenize(options.device, 'device', [])

options.cutoff_temp = tokenize(options.cutoff_temp, 'cutoff_temp', [95], float)
options.cutoff_interval = tokenize(options.cutoff_interval, 'cutoff_interval', [0.01], float)

switch = None
try:
	switch = Switch(options)

	if not options.no_ocl:
		import OpenCLMiner
		for miner in OpenCLMiner.initialize(options):
			switch.add_miner(miner)

	if not options.no_bfl:
		import BFLMiner
		for miner in BFLMiner.initialize(options):
			switch.add_miner(miner)

	if not switch.servers:
		print '\nAt least one server is required\n'
	elif not switch.miners:
		print '\nNothing to mine on, exiting\n'
	else:
		for miner in switch.miners:
			miner.start()
		switch.loop()
except KeyboardInterrupt:
	print '\nbye'
finally:
	for miner in switch.miners:
		miner.stop()
	if switch: switch.stop()

	if not options.no_ocl:
		OpenCLMiner.shutdown()
sleep(1.1)
########NEW FILE########
__FILENAME__ = sha256
from util import uint32


K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]

STATE = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]


def rotr(x, y):
	return (x>>y | x<<(32-y))

def rot(x, y):
	return (x<<y | x>>(32-y))

def R(x2, x7, x15, x16):
	return uint32((rot(x2,15)^rot(x2,13)^((x2)>>10)) + x7 + (rot(x15,25)^rot(x15,14)^((x15)>>3)) + x16)

def sharound(a,b,c,d,e,f,g,h,x,K):
	t1=h+(rot(e, 26)^rot(e, 21)^rot(e, 7))+(g^(e&(f^g)))+K+x
	t2=(rot(a, 30)^rot(a, 19)^rot(a, 10))+((a&b)|(c&(a|b)))
	return (uint32(d + t1), uint32(t1+t2))

def partial(state, merkle_end, time, difficulty, f):
	state2 = list(state)
	data = [merkle_end, time, difficulty]
	for i in xrange(3):
		(state2[~(i-4)&7], state2[~(i-8)&7]) = sharound(state2[(~(i-1)&7)],state2[~(i-2)&7],state2[~(i-3)&7],state2[~(i-4)&7],state2[~(i-5)&7],state2[~(i-6)&7],state2[~(i-7)&7],state2[~(i-8)&7],data[i],K[i])

	f[0] = uint32(data[0] + (rotr(data[1], 7) ^ rotr(data[1], 18) ^ (data[1] >> 3)))
	f[1] = uint32(data[1] + (rotr(data[2], 7) ^ rotr(data[2], 18) ^ (data[2] >> 3)) + 0x01100000)
	f[2] = uint32(data[2] + (rotr(f[0], 17) ^ rotr(f[0], 19) ^ (f[0] >> 10)))
	f[3] = uint32(0x11002000 + (rotr(f[1], 17) ^ rotr(f[1], 19) ^ (f[1] >> 10)))
	f[4] = uint32(0x00000280 + (rotr(f[0], 7) ^ rotr(f[0], 18) ^ (f[0] >> 3)))
	f[5] = uint32(f[0] + (rotr(f[1], 7) ^ rotr(f[1], 18) ^ (f[1] >> 3)))
	f[6] = uint32(state[4] + (rotr(state2[1], 6) ^ rotr(state2[1], 11) ^ rotr(state2[1], 25)) + (state2[3] ^ (state2[1] & (state2[2] ^ state2[3]))) + 0xe9b5dba5)
	f[7] = uint32((rotr(state2[5], 2) ^ rotr(state2[5], 13) ^ rotr(state2[5], 22)) + ((state2[5] & state2[6]) | (state2[7] & (state2[5] | state2[6]))))
	return state2

def calculateF(state, merkle_end, time, difficulty, f, state2):
		data = [merkle_end, time, difficulty]
		#W2
		f[0] = uint32(data[2])

		#W16
		f[1] = uint32(data[0] + (rotr(data[1], 7) ^ rotr(data[1], 18) ^
			(data[1] >> 3)))
		#W17
		f[2] = uint32(data[1] + (rotr(data[2], 7) ^ rotr(data[2], 18) ^
			(data[2] >> 3)) + 0x01100000)

		#2 parts of the first SHA round
		f[3] = uint32(state[4] + (rotr(state2[1], 6) ^
			rotr(state2[1], 11) ^ rotr(state2[1], 25)) +
			(state2[3] ^ (state2[1] & (state2[2] ^
			state2[3]))) + 0xe9b5dba5)
		f[4] = uint32((rotr(state2[5], 2) ^
			rotr(state2[5], 13) ^ rotr(state2[5], 22)) +
			((state2[5] & state2[6]) | (state2[7] &
			(state2[5] | state2[6]))))

def sha256(state, data):
	digest = list(state)
	for i in xrange(64):
		if i > 15:
			data[i] = R(data[i-2], data[i-7], data[i-15], data[i-16])
		(digest[~(i-4)&7], digest[~(i-8)&7]) = sharound(digest[(~(i-1)&7)],digest[~(i-2)&7],digest[~(i-3)&7],digest[~(i-4)&7],digest[~(i-5)&7],digest[~(i-6)&7],digest[~(i-7)&7],digest[~(i-8)&7],data[i],K[i])

	result = []
	result.append(uint32(digest[0] + state[0]))
	result.append(uint32(digest[1] + state[1]))
	result.append(uint32(digest[2] + state[2]))
	result.append(uint32(digest[3] + state[3]))
	result.append(uint32(digest[4] + state[4]))
	result.append(uint32(digest[5] + state[5]))
	result.append(uint32(digest[6] + state[6]))
	result.append(uint32(digest[7] + state[7]))

	return result

def hash(midstate, merkle_end, time, difficulty, nonce):
	work = [[0] * 64][0]
	work[0]=merkle_end; work[1]=time; work[2]=difficulty; work[3]=nonce
	work[4]=0x80000000; work[5]=0x00000000; work[6]=0x00000000; work[7]=0x00000000
	work[8]=0x00000000; work[9]=0x00000000; work[10]=0x00000000; work[11]=0x00000000
	work[12]=0x00000000; work[13]=0x00000000; work[14]=0x00000000; work[15]=0x00000280

	state = sha256(midstate, work)

	work[0]=state[0]; work[1]=state[1]; work[2]=state[2]; work[3]=state[3]
	work[4]=state[4]; work[5]=state[5]; work[6]=state[6]; work[7]=state[7]
	work[8]=0x80000000; work[15]=0x00000100

	return sha256(STATE, work)

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

import socket
import struct

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class GeneralProxyError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks5AuthError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks5Error(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks4Error(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class HTTPError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

_generalerrors = ("success",
		   "invalid data",
		   "not connected",
		   "not available",
		   "bad proxy type",
		   "bad input")

_socks5errors = ("succeeded",
		  "general SOCKS server failure",
		  "connection not allowed by ruleset",
		  "Network unreachable",
		  "Host unreachable",
		  "Connection refused",
		  "TTL expired",
		  "Command not supported",
		  "Address type not supported",
		  "Unknown error")

_socks5autherrors = ("succeeded",
		      "authentication is required",
		      "all offered authentication methods were rejected",
		      "unknown username or invalid password",
		      "unknown error")

_socks4errors = ("request granted",
		  "request rejected or failed",
		  "request rejected because SOCKS server cannot connect to identd on the client",
		  "request rejected because the client program and identd report different user-ids",
		  "unknown error")

def setdefaultproxy(proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
	"""setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
	Sets a default proxy which all further socksocket objects will use,
	unless explicitly changed.
	"""
	global _defaultproxy
	_defaultproxy = (proxytype,addr,port,rdns,username,password)
	
class socksocket(socket.socket):
	"""socksocket([family[, type[, proto]]]) -> socket object
	
	Open a SOCKS enabled socket. The parameters are the same as
	those of the standard socket init. In order for SOCKS to work,
	you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
	"""
	
	def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
		_orgsocket.__init__(self,family,type,proto,_sock)
		if _defaultproxy != None:
			self.__proxy = _defaultproxy
		else:
			self.__proxy = (None, None, None, None, None, None)
		self.__proxysockname = None
		self.__proxypeername = None
	
	def __recvall(self, bytes):
		"""__recvall(bytes) -> data
		Receive EXACTLY the number of bytes requested from the socket.
		Blocks until the required number of bytes have been received.
		"""
		data = ""
		while len(data) < bytes:
			data = data + self.recv(bytes-len(data))
		return data
	
	def setproxy(self,proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
		"""setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
		Sets the proxy to be used.
		proxytype -	The type of the proxy to be used. Three types
				are supported: PROXY_TYPE_SOCKS4 (including socks4a),
				PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
		addr -		The address of the server (IP or DNS).
		port -		The port of the server. Defaults to 1080 for SOCKS
				servers and 8080 for HTTP proxy servers.
		rdns -		Should DNS queries be preformed on the remote side
				(rather than the local side). The default is True.
				Note: This has no effect with SOCKS4 servers.
		username -	Username to authenticate with to the server.
				The default is no authentication.
		password -	Password to authenticate with to the server.
				Only relevant when username is also provided.
		"""
		self.__proxy = (proxytype,addr,port,rdns,username,password)
	
	def __negotiatesocks5(self,destaddr,destport):
		"""__negotiatesocks5(self,destaddr,destport)
		Negotiates a connection through a SOCKS5 server.
		"""
		# First we'll send the authentication packages we support.
		if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
			# The username/password details were supplied to the
			# setproxy method so we support the USERNAME/PASSWORD
			# authentication (in addition to the standard none).
			self.sendall("\x05\x02\x00\x02")
		else:
			# No username/password were entered, therefore we
			# only support connections with no authentication.
			self.sendall("\x05\x01\x00")
		# We'll receive the server's response to determine which
		# method was selected
		chosenauth = self.__recvall(2)
		if chosenauth[0] != "\x05":
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		# Check the chosen authentication method
		if chosenauth[1] == "\x00":
			# No authentication is required
			pass
		elif chosenauth[1] == "\x02":
			# Okay, we need to perform a basic username/password
			# authentication.
			self.sendall("\x01" + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
			authstat = self.__recvall(2)
			if authstat[0] != "\x01":
				# Bad response
				self.close()
				raise GeneralProxyError((1,_generalerrors[1]))
			if authstat[1] != "\x00":
				# Authentication failed
				self.close()
				raise Socks5AuthError((3,_socks5autherrors[3]))
			# Authentication succeeded
		else:
			# Reaching here is always bad
			self.close()
			if chosenauth[1] == "\xFF":
				raise Socks5AuthError((2,_socks5autherrors[2]))
			else:
				raise GeneralProxyError((1,_generalerrors[1]))
		# Now we can request the actual connection
		req = "\x05\x01\x00"
		# If the given destination address is an IP address, we'll
		# use the IPv4 address request even if remote resolving was specified.
		try:
			ipaddr = socket.inet_aton(destaddr)
			req = req + "\x01" + ipaddr
		except socket.error:
			# Well it's not an IP number,  so it's probably a DNS name.
			if self.__proxy[3]==True:
				# Resolve remotely
				ipaddr = None
				req = req + "\x03" + chr(len(destaddr)) + destaddr
			else:
				# Resolve locally
				ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
				req = req + "\x01" + ipaddr
		req = req + struct.pack(">H",destport)
		self.sendall(req)
		# Get the response
		resp = self.__recvall(4)
		if resp[0] != "\x05":
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		elif resp[1] != "\x00":
			# Connection failed
			self.close()
			if ord(resp[1])<=8:
				raise Socks5Error(ord(resp[1]),_socks5errors[ord(resp[1])])
			else:
				raise Socks5Error(9,_socks5errors[9])
		# Get the bound address/port
		elif resp[3] == "\x01":
			boundaddr = self.__recvall(4)
		elif resp[3] == "\x03":
			resp = resp + self.recv(1)
			boundaddr = self.__recvall(resp[4])
		else:
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		boundport = struct.unpack(">H",self.__recvall(2))[0]
		self.__proxysockname = (boundaddr,boundport)
		if ipaddr != None:
			self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
		else:
			self.__proxypeername = (destaddr,destport)
	
	def getproxysockname(self):
		"""getsockname() -> address info
		Returns the bound IP address and port number at the proxy.
		"""
		return self.__proxysockname
	
	def getproxypeername(self):
		"""getproxypeername() -> address info
		Returns the IP and port number of the proxy.
		"""
		return _orgsocket.getpeername(self)
	
	def getpeername(self):
		"""getpeername() -> address info
		Returns the IP address and port number of the destination
		machine (note: getproxypeername returns the proxy)
		"""
		return self.__proxypeername
	
	def __negotiatesocks4(self,destaddr,destport):
		"""__negotiatesocks4(self,destaddr,destport)
		Negotiates a connection through a SOCKS4 server.
		"""
		# Check if the destination address provided is an IP address
		rmtrslv = False
		try:
			ipaddr = socket.inet_aton(destaddr)
		except socket.error:
			# It's a DNS name. Check where it should be resolved.
			if self.__proxy[3]==True:
				ipaddr = "\x00\x00\x00\x01"
				rmtrslv = True
			else:
				ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
		# Construct the request packet
		req = "\x04\x01" + struct.pack(">H",destport) + ipaddr
		# The username parameter is considered userid for SOCKS4
		if self.__proxy[4] != None:
			req = req + self.__proxy[4]
		req = req + "\x00"
		# DNS name if remote resolving is required
		# NOTE: This is actually an extension to the SOCKS4 protocol
		# called SOCKS4A and may not be supported in all cases.
		if rmtrslv==True:
			req = req + destaddr + "\x00"
		self.sendall(req)
		# Get the response from the server
		resp = self.__recvall(8)
		if resp[0] != "\x00":
			# Bad data
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		if resp[1] != "\x5A":
			# Server returned an error
			self.close()
			if ord(resp[1]) in (91,92,93):
				self.close()
				raise Socks4Error((ord(resp[1]),_socks4errors[ord(resp[1])-90]))
			else:
				raise Socks4Error((94,_socks4errors[4]))
		# Get the bound address/port
		self.__proxysockname = (socket.inet_ntoa(resp[4:]),struct.unpack(">H",resp[2:4])[0])
		if rmtrslv != None:
			self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
		else:
			self.__proxypeername = (destaddr,destport)
	
	def __negotiatehttp(self,destaddr,destport):
		"""__negotiatehttp(self,destaddr,destport)
		Negotiates a connection through an HTTP server.
		"""
		# If we need to resolve locally, we do this now
		if self.__proxy[3] == False:
			addr = socket.gethostbyname(destaddr)
		else:
			addr = destaddr
		self.sendall("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n")
		# We read the response until we get the string "\r\n\r\n"
		resp = self.recv(1)
		while resp.find("\r\n\r\n")==-1:
			resp = resp + self.recv(1)
		# We just need the first line to check if the connection
		# was successful
		statusline = resp.splitlines()[0].split(" ",2)
		if statusline[0] not in ("HTTP/1.0","HTTP/1.1"):
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		try:
			statuscode = int(statusline[1])
		except ValueError:
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		if statuscode != 200:
			self.close()
			raise HTTPError((statuscode,statusline[2]))
		self.__proxysockname = ("0.0.0.0",0)
		self.__proxypeername = (addr,destport)
	
	def connect(self,destpair):
		"""connect(self,despair)
		Connects to the specified destination through a proxy.
		destpar - A tuple of the IP/DNS address and the port number.
		(identical to socket's connect).
		To select the proxy server use setproxy().
		"""
		# Do a minimal input check first
		if (type(destpair) in (list,tuple)==False) or (len(destpair)<2) or (type(destpair[0])!=str) or (type(destpair[1])!=int):
			raise GeneralProxyError((5,_generalerrors[5]))
		if self.__proxy[0] == PROXY_TYPE_SOCKS5:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 1080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatesocks5(destpair[0],destpair[1])
		elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 1080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatesocks4(destpair[0],destpair[1])
		elif self.__proxy[0] == PROXY_TYPE_HTTP:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 8080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatehttp(destpair[0],destpair[1])
		elif self.__proxy[0] == None:
			_orgsocket.connect(self,(destpair[0],destpair[1]))
		else:
			raise GeneralProxyError((4,_generalerrors[4]))

########NEW FILE########
__FILENAME__ = Source
from Queue import Queue
from time import time


class Source(object):
	def __init__(self, switch):
		self.switch = switch
		self.result_queue = Queue()
		self.options = switch.options

	def server(self):
		return self.switch.server()

	def loop(self):
		self.should_stop = False
		self.last_failback = time()

	def check_failback(self):
		if self.switch.server_index != 0 and time() - self.last_failback > self.options.failback:
			self.stop()
			return True

	def process_result_queue(self):
		while not self.result_queue.empty():
			result = self.result_queue.get(False)
			with self.switch.lock:
				if not self.switch.send(result, self.send_internal):
					self.result_queue.put(result)
					self.stop()
					break
########NEW FILE########
__FILENAME__ = StratumSource
from Source import Source
from binascii import hexlify, unhexlify
from hashlib import sha256
from json import dumps, loads
from log import say_exception, say_line
from struct import pack
from threading import Thread, Lock, Timer
from time import sleep, time
from util import chunks, Object
import asynchat
import asyncore
import socket
import socks


#import ssl


BASE_DIFFICULTY = 0x00000000FFFF0000000000000000000000000000000000000000000000000000

def detect_stratum_proxy(host):
	s = None
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
		s.sendto(dumps({"id": 0, "method": "mining.get_upstream", "params": []}), ('239.3.3.3', 3333))

		say_line('Searching stratum proxy for %s', host)

		s.settimeout(2)

		try:
			while True:
				response, address = s.recvfrom(128)
				try:
					response = loads(response)
					response_host = response['result'][0][0] + ':' + str(response['result'][0][1])
					if response_host == host:
						proxy_address = address[0] + ':' + str(response['result'][1])
						say_line('Using stratum proxy at %s', proxy_address)
						return proxy_address
				except ValueError:
					pass
		except socket.timeout:
			pass

	finally:
		if s != None:
			s.close()


class StratumSource(Source):
	def __init__(self, switch):
		super(StratumSource, self).__init__(switch)
		self.handler = None
		self.socket = None
		self.channel_map = {}
		self.subscribed = False
		self.authorized = None
		self.submits = {}
		self.last_submits_cleanup = time()
		self.server_difficulty = BASE_DIFFICULTY
		self.jobs = {}
		self.current_job = None
		self.extranonce = ''
		self.extranonce2_size = 4
		self.send_lock = Lock()

	def loop(self):
		super(StratumSource, self).loop()

		self.switch.update_time = True

		while True:
			if self.should_stop: return

			if self.current_job:
				miner = self.switch.updatable_miner()
				while miner:
					self.current_job = self.refresh_job(self.current_job)
					self.queue_work(self.current_job, miner)
					miner = self.switch.updatable_miner()

			if self.check_failback():
				return True

			if not self.handler:
				try:
					#socket = ssl.wrap_socket(socket)
					address, port = self.server().host.split(':', 1)


					if not self.options.proxy:
						self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						self.socket.connect((address, int(port)))
					else:
						self.socket = socks.socksocket()
						p = self.options.proxy
						self.socket.setproxy(p.type, p.host, p.port, True, p.user, p.pwd)
						try:
							self.socket.connect((address, int(port)))
						except socks.Socks5AuthError:
							say_exception('Proxy error:')
							self.stop()

					self.handler = Handler(self.socket, self.channel_map, self)
					thread = Thread(target=self.asyncore_thread)
					thread.daemon = True
					thread.start()

					if not self.subscribe():
						say_line('Failed to subscribe')
						self.stop()
					elif not self.authorize():
						self.stop()

				except socket.error:
					say_exception()
					self.stop()
					continue

			with self.send_lock:
				self.process_result_queue()
			sleep(1)

	def asyncore_thread(self):
		asyncore.loop(map=self.channel_map)

	def stop(self):
		self.should_stop = True
		if self.handler:
			self.handler.close()

	def refresh_job(self, j):
		j.extranonce2 = self.increment_nonce(j.extranonce2)
		coinbase = j.coinbase1 + self.extranonce + j.extranonce2 + j.coinbase2
		merkle_root = sha256(sha256(unhexlify(coinbase)).digest()).digest()

		for hash_ in j.merkle_branch:
			merkle_root = sha256(sha256(merkle_root + unhexlify(hash_)).digest()).digest()
		merkle_root_reversed = ''
		for word in chunks(merkle_root, 4):
			merkle_root_reversed += word[::-1]
		merkle_root = hexlify(merkle_root_reversed)

		j.block_header = ''.join([j.version, j.prevhash, merkle_root, j.ntime, j.nbits])
		j.time = time()
		return j

	def increment_nonce(self, nonce):
		next_nonce = long(nonce, 16) + 1
		if len('%x' % next_nonce) > (self.extranonce2_size * 2):
			return '00' * self.extranonce2_size
		return ('%0' + str(self.extranonce2_size * 2) +'x') % next_nonce

	def handle_message(self, message):

		#Miner API
		if 'method' in message:

			#mining.notify
			if message['method'] == 'mining.notify':
				params = message['params']

				j = Object()

				j.job_id = params[0]
				j.prevhash = params[1]
				j.coinbase1 = params[2]
				j.coinbase2 = params[3]
				j.merkle_branch = params[4]
				j.version = params[5]
				j.nbits = params[6]
				j.ntime = params[7]
				clear_jobs = params[8]
				if clear_jobs:
					self.jobs.clear()
				j.extranonce2 = self.extranonce2_size * '00'

				j = self.refresh_job(j)

				self.jobs[j.job_id] = j
				self.current_job = j

				self.queue_work(j)
				self.switch.connection_ok()

			#mining.get_version
			if message['method'] == 'mining.get_version':
				with self.send_lock:
					self.send_message({"error": None, "id": message['id'], "result": self.user_agent})

			#mining.set_difficulty
			elif message['method'] == 'mining.set_difficulty':
				say_line("Setting new difficulty: %s", message['params'][0])
				self.server_difficulty = BASE_DIFFICULTY / message['params'][0]

			#client.reconnect
			elif message['method'] == 'client.reconnect':
				address, port = self.server().host.split(':', 1)
				(new_address, new_port, timeout) = message['params'][:3]
				if new_address: address = new_address
				if new_port != None: port = new_port
				say_line("%s asked us to reconnect to %s:%d in %d seconds", (self.server().name, address, port, timeout))
				self.server().host = address + ':' + str(port)
				Timer(timeout, self.reconnect).start()

			#client.add_peers
			elif message['method'] == 'client.add_peers':
				hosts = [{'host': host[0], 'port': host[1]} for host in message['params'][0]]
				self.switch.add_servers(hosts)

		#responses to server API requests
		elif 'result' in message:

			#response to mining.subscribe
			#store extranonce and extranonce2_size
			if message['id'] == 's':
				self.extranonce = message['result'][1]
				self.extranonce2_size = message['result'][2]
				self.subscribed = True

			#check if this is submit confirmation (message id should be in submits dictionary)
			#cleanup if necessary
			elif message['id'] in self.submits:
				miner, nonce = self.submits[message['id']][:2]
				accepted = message['result']
				self.switch.report(miner, nonce, accepted)
				del self.submits[message['id']]
				if time() - self.last_submits_cleanup > 3600:
					now = time()
					for key, value in self.submits.items():
						if now - value[2] > 3600:
							del self.submits[key]
					self.last_submits_cleanup = now

			#response to mining.authorize
			elif message['id'] == self.server().user:
				if not message['result']:
					say_line('authorization failed with %s:%s@%s', (self.server().user, self.server().pwd, self.server().host))
					self.authorized = False
				else:
					self.authorized = True

	def reconnect(self):
		say_line("%s reconnecting to %s", (self.server().name, self.server().host))
		self.handler.close()

	def subscribe(self):
		self.send_message({'id': 's', 'method': 'mining.subscribe', 'params': []})
		for i in xrange(10):
			sleep(1)
			if self.subscribed: break
		return self.subscribed

	def authorize(self):
		self.send_message({'id': self.server().user, 'method': 'mining.authorize', 'params': [self.server().user, self.server().pwd]})
		for i in xrange(10):
			sleep(1)
			if self.authorized != None: break
		return self.authorized

	def send_internal(self, result, nonce):
		job_id = result.job_id
		if not job_id in self.jobs:
			return True
		extranonce2 = result.extranonce2
		ntime = pack('<I', long(result.time)).encode('hex')
		hex_nonce = pack('<I', long(nonce)).encode('hex')
		id_ = job_id + hex_nonce
		self.submits[id_] = (result.miner, nonce, time())
		return self.send_message({'params': [self.server().user, job_id, extranonce2, ntime, hex_nonce], 'id': id_, 'method': u'mining.submit'})

	def send_message(self, message):
		data = dumps(message) + '\n'
		try:
			#self.handler.push(data)

			#there is some bug with asyncore's send mechanism
			#so we send data 'manually'
			#note that this is not thread safe
			if not self.handler:
				return False
			while data:
				sent = self.handler.send(data)
				data = data[sent:]
			return True
		except AttributeError:
			self.stop()
		except Exception:
			say_exception()
			self.stop()

	def queue_work(self, work, miner=None):
		target = ''.join(list(chunks('%064x' % self.server_difficulty, 2))[::-1])
		self.switch.queue_work(self, work.block_header, target, work.job_id, work.extranonce2, miner)

class Handler(asynchat.async_chat):
	def __init__(self, socket, map_, parent):
		asynchat.async_chat.__init__(self, socket, map_)
		self.parent = parent
		self.data = ''
		self.set_terminator('\n')

	def handle_close(self):
		self.close()
		self.parent.handler = None
		self.parent.socket = None

	def handle_error(self):
		say_exception()
		self.parent.stop()

	def collect_incoming_data(self, data):
		self.data += data

	def found_terminator(self):
		message = loads(self.data)
		self.parent.handle_message(message)
		self.data = ''

########NEW FILE########
__FILENAME__ = Switch
from copy import copy
from log import say_exception, say_line, say_quiet
from sha256 import hash, sha256, STATE
from struct import pack, unpack
from threading import RLock
from time import time, sleep
from util import Object, chunks, bytereverse, belowOrEquals, uint32
import StratumSource
import log
import socks


class Switch(object):
	def __init__(self, options):
		self.lock = RLock()
		self.miners = []
		self.options = options
		self.last_work = 0
		self.update_time = True
		self.max_update_time = options.max_update_time

		self.backup_server_index = 1
		self.errors = 0
		self.failback_attempt_count = 0
		self.server_index = -1
		self.last_server = None
		self.server_map = {}

		self.user_agent = 'poclbm/' + options.version

		self.difficulty = 0
		self.true_target = None
		self.last_block = ''

		self.sent = {}

		if self.options.proxy:
			self.options.proxy = self.parse_server(self.options.proxy, False)
			self.parse_proxy(self.options.proxy)

		self.servers = []
		for server in self.options.servers:
			try:
				self.servers.append(self.parse_server(server))
			except ValueError:
				if self.options.verbose:
					say_exception()
				say_line("Ignored invalid server entry: %s", server)
				continue

	def parse_server(self, server, mailAsUser=True):
		s = Object()
		temp = server.split('://', 1)
		if len(temp) == 1:
			s.proto = ''; temp = temp[0]
		else: s.proto = temp[0]; temp = temp[1]
		if mailAsUser:
			s.user, temp = temp.split(':', 1)
			s.pwd, s.host = temp.split('@')
		else:
			temp = temp.split('@', 1)
			if len(temp) == 1:
				s.user = ''
				s.pwd = ''
				s.host = temp[0]
			else:
				if temp[0].find(':') <> -1:
					s.user, s.pwd = temp[0].split(':')
				else:
					s.user = temp[0]
					s.pwd = ''
				s.host = temp[1]

		if s.host.find('#') != -1:
			s.host, s.name = s.host.split('#')
		else: s.name = s.host

		return s

	def parse_proxy(self, proxy):
		proxy.port = 9050
		proxy.host = proxy.host.split(':')
		if len(proxy.host) > 1:
			proxy.port = int(proxy.host[1]); proxy.host = proxy.host[0]

		proxy.type = socks.PROXY_TYPE_SOCKS5
		if proxy.proto == 'http':
			proxy.type = socks.PROXY_TYPE_HTTP
		elif proxy.proto == 'socks4':
			proxy.type = socks.PROXY_TYPE_SOCKS4

	def add_miner(self, miner):
		self.miners.append(miner)
		miner.switch = self

	def updatable_miner(self):
		for miner in self.miners:
			if miner.update:
				miner.update = False
				return miner

	def loop(self):
		self.should_stop = False
		self.set_server_index(0)

		while True:
			if self.should_stop: return

			failback = self.server_source().loop()

			sleep(1)

			if failback:
				say_line("Attempting to fail back to primary server")
				self.last_server = self.server_index
				self.set_server_index(0)
				continue

			if self.last_server:
				self.failback_attempt_count += 1
				self.set_server_index(self.last_server)
				say_line('Still unable to reconnect to primary server (attempt %s), failing over', self.failback_attempt_count)
				self.last_server = None
				continue

			self.errors += 1
			say_line('IO errors - %s, tolerance %s', (self.errors, self.options.tolerance))

			if self.errors > self.options.tolerance:
				self.errors = 0
				if self.backup_server_index >= len(self.servers):
					say_line("No more backup servers left. Using primary and starting over.")
					new_server_index = 0
					self.backup_server_index = 1
				else:
					new_server_index = self.backup_server_index
					self.backup_server_index += 1
				self.set_server_index(new_server_index)

	def connection_ok(self):
		self.errors = 0
		if self.server_index == 0:
			self.backup_server_index = 1
			self.failback_attempt_count = 0

	def stop(self):
		self.should_stop = True
		if self.server_index != -1:
			self.server_source().stop()

	#callers must provide hex encoded block header and target
	def decode(self, server, block_header, target, job_id = None, extranonce2 = None):
		if block_header:
			job = Object()

			binary_data = block_header.decode('hex')
			data0 = list(unpack('<16I', binary_data[:64])) + ([0] * 48)

			job.target		= unpack('<8I', target.decode('hex'))
			job.header		= binary_data[:68]
			job.merkle_end	= uint32(unpack('<I', binary_data[64:68])[0])
			job.time		= uint32(unpack('<I', binary_data[68:72])[0])
			job.difficulty	= uint32(unpack('<I', binary_data[72:76])[0])
			job.state		= sha256(STATE, data0)
			job.targetQ		= 2**256 / int(''.join(list(chunks(target, 2))[::-1]), 16)
			job.job_id		= job_id
			job.extranonce2	= extranonce2
			job.server		= server

			if job.difficulty != self.difficulty:
				self.set_difficulty(job.difficulty)
	
			return job

	def set_difficulty(self, difficulty):
		self.difficulty = difficulty
		bits = '%08x' % bytereverse(difficulty)
		true_target = '%064x' % (int(bits[2:], 16) * 2 ** (8 * (int(bits[:2], 16) - 3)),)
		true_target = ''.join(list(chunks(true_target, 2))[::-1])
		self.true_target = unpack('<8I', true_target.decode('hex'))

	def send(self, result, send_callback):
		for nonce in result.miner.nonce_generator(result.nonces):
			h = hash(result.state, result.merkle_end, result.time, result.difficulty, nonce)
			if h[7] != 0:
				hash6 = pack('<I', long(h[6])).encode('hex')
				say_line('Verification failed, check hardware! (%s, %s)', (result.miner.id(), hash6))
				return True # consume this particular result
			else:
				self.diff1_found(bytereverse(h[6]), result.target[6])
				if belowOrEquals(h[:7], result.target[:7]):
					is_block = belowOrEquals(h[:7], self.true_target[:7])
					hash6 = pack('<I', long(h[6])).encode('hex')
					hash5 = pack('<I', long(h[5])).encode('hex')
					self.sent[nonce] = (is_block, hash6, hash5)
					if not send_callback(result, nonce):
						return False
		return True

	def diff1_found(self, hash_, target):
		if self.options.verbose and target < 0xFFFF0000L:
			say_line('checking %s <= %s', (hash_, target))

	def status_updated(self, miner):
		verbose = self.options.verbose
		rate = miner.rate if verbose else sum([m.rate for m in self.miners])
		estimated_rate = miner.estimated_rate if verbose else sum([m.estimated_rate for m in self.miners])
		rejected_shares = miner.share_count[0] if verbose else sum([m.share_count[0] for m in self.miners])
		total_shares = rejected_shares + miner.share_count[1] if verbose else sum([m.share_count[1] for m in self.miners])
		total_shares_estimator = max(total_shares, 1)
		say_quiet('%s[%.03f MH/s (~%d MH/s)] [Rej: %d/%d (%.02f%%)]', (miner.id()+' ' if verbose else '', rate, round(estimated_rate), rejected_shares, total_shares, float(rejected_shares) * 100 / total_shares_estimator))

	def report(self, miner, nonce, accepted):
		is_block, hash6, hash5 = self.sent[nonce]
		miner.share_count[1 if accepted else 0] += 1
		hash_ = hash6 + hash5 if is_block else hash6
		if self.options.verbose or is_block:
			say_line('%s %s%s, %s', (miner.id(), 'block ' if is_block else '', hash_, 'accepted' if accepted else '_rejected_'))
		del self.sent[nonce]

	def set_server_index(self, server_index):
		self.server_index = server_index
		user = self.servers[server_index].user
		name = self.servers[server_index].name
		#say_line('Setting server %s (%s @ %s)', (name, user, host))
		say_line('Setting server (%s @ %s)', (user, name))
		log.server = name
		

	def add_servers(self, hosts):
		for host in hosts[::-1]:
			port = str(host['port'])
			if not self.has_server(self.server().user, host['host'], port):
				server = copy(self.server())
				server.host = ''.join([host['host'], ':', port])
				server.source = None
				self.servers.insert(self.backup_server_index, server)

	def has_server(self, user, host, port):
		for server in self.servers:
			server_host, server_port = self.server().host.split(':', 1)
			if server.user == user and server_host == host and server_port == port:
				return True
		return False

	def queue_work(self, server, block_header, target = None, job_id = None, extranonce2 = None, miner=None):
		work = self.decode(server, block_header, target, job_id, extranonce2)
		with self.lock:
			if not miner:
				miner = self.miners[0]
				for i in xrange(1, len(self.miners)):
					self.miners[i].update = True
			miner.work_queue.put(work)
			if work:
				miner.update = False; self.last_work = time()
				if self.last_block != work.header[25:29]:
					self.last_block = work.header[25:29]
					self.clear_result_queue(server)

	def clear_result_queue(self, server):
		while not server.result_queue.empty():
			server.result_queue.get(False)

	def server_source(self):
		if not hasattr(self.server(), 'source'):
			if self.server().proto == 'http':
				import GetworkSource
				getwork_source = GetworkSource.GetworkSource(self)
				say_line('checking for stratum...')

				stratum_host = getwork_source.detect_stratum()
				if stratum_host:
					getwork_source.close_connection()
					self.server().proto = 'stratum'
					self.server().host = stratum_host
					self.add_stratum_source()
				else:
					self.server().source = getwork_source
			else:
				self.add_stratum_source()

		return self.server().source

	def add_stratum_source(self):
		if self.options.stratum_proxies:
			stratum_proxy = StratumSource.detect_stratum_proxy(self.server().host)
			if stratum_proxy:
				original_server = copy(self.server())
				original_server.source = StratumSource.StratumSource(self)
				self.servers.insert(self.backup_server_index, original_server)
				self.server().host = stratum_proxy
				self.server().name += '(p)'
				log.server = self.server().name
			else:
				say_line('No proxy found')
		self.server().source = StratumSource.StratumSource(self)
	
	def server(self):
		return self.servers[self.server_index]

	def put(self, result):
		result.server.result_queue.put(result)

########NEW FILE########
__FILENAME__ = util
from log import say_exception
import sys

class Object(object):
	pass

def uint32(x):
	return x & 0xffffffffL

def bytereverse(x):
	return uint32(( ((x) << 24) | (((x) << 8) & 0x00ff0000) | (((x) >> 8) & 0x0000ff00) | ((x) >> 24) ))

def bytearray_to_uint32(x):
	return uint32(((x[3]) << 24) | ((x[2]) << 16)  | ((x[1]) << 8) | x[0])

def belowOrEquals(hash_, target):
	for i in xrange(len(hash_) - 1, -1, -1):
		reversed_ = bytereverse(hash_[i])
		if reversed_ < target[i]:
			return True
		elif reversed_ > target[i]:
			return False
	return True

def chunks(l, n):
	for i in xrange(0, len(l), n):
		yield l[i:i+n]

def tokenize(option, name, default=[0], cast=int):
	if option:
		try:
			return [cast(x) for x in option.split(',')]
		except ValueError:
			say_exception('Invalid %s(s) specified: %s\n\n' % (name, option))
			sys.exit()
	return default

########NEW FILE########
__FILENAME__ = version
VERSION = '12.10'
########NEW FILE########
