__FILENAME__ = lixian

__all__ = ['XunleiClient']

import urllib
import urllib2
import cookielib
import re
import time
import os.path
import json
from ast import literal_eval


def retry(f_or_arg, *args):
	#retry_sleeps = [1, 1, 1]
	retry_sleeps = [1, 2, 3, 5, 10, 20, 30, 60] + [60] * 60
	def decorator(f):
		def withretry(*args, **kwargs):
			for second in retry_sleeps:
				try:
					return f(*args, **kwargs)
				except:
					import traceback
					logger.debug("Exception happened. Retrying...")
					logger.debug(traceback.format_exc())
					time.sleep(second)
			raise
		return withretry
	if callable(f_or_arg) and not args:
		return decorator(f_or_arg)
	else:
		a = f_or_arg
		assert type(a) == int
		assert not args
		retry_sleeps = [1] * a
		return decorator

class Logger:
	def stdout(self, message):
		print message
	def info(self, message):
		print message
	def debug(self, message):
		pass
	def trace(self, message):
		pass

logger = Logger()

class WithAttrSnapshot:
	def __init__(self, object, **attrs):
		self.object = object
		self.attrs = attrs
	def __enter__(self):
		self.old_attrs = []
		for k in self.attrs:
			if hasattr(self.object, k):
				self.old_attrs.append((k, True, getattr(self.object, k)))
			else:
				self.old_attrs.append((k, False, None))
		for k in self.attrs:
			setattr(self.object, k, self.attrs[k])
	def __exit__(self, exc_type, exc_val, exc_tb):
		for k, has_old_attr, v in self.old_attrs:
			if has_old_attr:
				setattr(self.object, k, v)
			else:
				delattr(self.object, k)

class WithAttr:
	def __init__(self, object):
		self.object = object
	def __call__(self, **kwargs):
		return WithAttrSnapshot(self.object, **kwargs)
	def __getattr__(self, k):
		return lambda (v): WithAttrSnapshot(self.object, **{k:v})

# TODO: write unit test
class OnDemandTaskList:
	def __init__(self, fetch_page, page_size, limit):
		self.fetch_page = fetch_page
		if limit and page_size > limit:
			page_size = limit
		self.page_size = page_size
		self.limit = limit
		self.pages = {}
		self.max_task_number = None
		self.real_total_task_number = None
		self.total_pages = None

	def is_out_of_range(self, n):
		if self.limit:
			if n >= self.limit:
				return True
		if self.max_task_number:
			if n >= self.max_task_number:
				return True
		if self.real_total_task_number:
			if n >= self.real_total_task_number:
				return True

	def check_out_of_range(self, n):
		if self.is_out_of_range(n):
			raise IndexError('task index out of range')

	def is_out_of_page(self, page):
		raise NotImplementedError()

	def get_nth_task(self, n):
		self.check_out_of_range(n)
		page = n / self.page_size
		n_in_page = n - page * self.page_size
		return self.hit_page(page)[n_in_page]

	def touch(self):
		self.hit_page(0)

	def hit_page(self, page):
		if page in self.pages:
			return self.pages[page]
		info = self.fetch_page(page, self.page_size)
		tasks = info['tasks']
		if self.max_task_number is None:
			self.max_task_number = info['total_task_number']
			if self.limit and self.max_task_number > self.limit:
				self.max_task_number = self.limit
			self.total_pages = self.max_task_number / self.page_size
			if self.max_task_number % self.page_size != 0:
				self.total_pages += 1
			if self.max_task_number == 0:
				self.real_total_task_number = 0
		if page >= self.total_pages:
			tasks = []
		elif page == self.total_pages - 1:
			if self.page_size * page + len(tasks) > self.max_task_number:
				tasks = tasks[0:self.max_task_number - self.page_size * page]
			if len(tasks) > 0:
				self.real_total_task_number = self.page_size * page + len(tasks)
			else:
				self.max_task_number -= self.page_size
				self.total_pages -= 1
				if len(self.pages.get(page-1, [])) == self.page_size:
					self.real_total_task_number = self.max_task_number
		else:
			if len(tasks) == 0:
				self.max_task_number = self.page_size * page
				self.total_pages = page
				if len(self.pages.get(page-1, [])) == self.page_size:
					self.real_total_task_number = self.max_task_number
			elif len(tasks) < self.page_size:
				self.real_total_task_number = self.page_size * page + len(tasks)
				self.max_task_number = self.real_total_task_number
				self.total_pages = page
			else:
				pass
		for i, t in enumerate(tasks):
			t['#'] = self.page_size * page + i
		self.pages[page] = tasks
		return tasks

	def __getitem__(self, n):
		return self.get_nth_task(n)

	def __iter__(self):
		class Iterator:
			def __init__(self, container):
				self.container = container
				self.current = 0
			def next(self):
				self.container.touch()
				assert type(self.container.max_task_number) == int
				if self.container.real_total_task_number is None:
					if self.current < self.container.max_task_number:
						try:
							task = self.container[self.current]
						except IndexError:
							raise StopIteration()
					else:
						raise StopIteration()
				else:
					if self.current < self.container.real_total_task_number:
						task = self.container[self.current]
					else:
						raise StopIteration()
				self.current += 1
				return task
		return Iterator(self)

	def __len__(self):
		if self.real_total_task_number:
			return self.real_total_task_number
		self.touch()
		self.hit_page(self.total_pages-1)
		if self.real_total_task_number:
			return self.real_total_task_number
		count = 0
		for t in self:
			count += 1
		return count

class XunleiClient(object):
	default_page_size = 100
	default_bt_page_size = 9999
	def __init__(self, username=None, password=None, cookie_path=None, login=True, verification_code_reader=None):
		self.attr = WithAttr(self)

		self.username = username
		self.password = password
		self.cookie_path = cookie_path
		if cookie_path:
			self.cookiejar = cookielib.LWPCookieJar()
			if os.path.exists(cookie_path):
				self.load_cookies()
		else:
			self.cookiejar = cookielib.CookieJar()

		self.page_size = self.default_page_size
		self.bt_page_size = self.default_bt_page_size

		self.limit = None

		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
		self.verification_code_reader = verification_code_reader
		self.login_time = None
		if login:
			self.id = self.get_userid_or_none()
			if not self.id:
				self.login()
			self.id = self.get_userid()

	@property
	def page_size(self):
		return self._page_size
	@page_size.setter
	def page_size(self, size):
		self._page_size = size
		self.set_page_size(size)

	@retry
	def urlopen(self, url, **args):
		logger.debug(url)
#		import traceback
#		for line in traceback.format_stack():
#			print line.strip()
		if 'data' in args and type(args['data']) == dict:
			args['data'] = urlencode(args['data'])
		return self.opener.open(urllib2.Request(url, **args), timeout=60)

	def urlread1(self, url, **args):
		args.setdefault('headers', {})
		headers = args['headers']
		headers.setdefault('Accept-Encoding', 'gzip, deflate')
#		headers.setdefault('Referer', 'http://lixian.vip.xunlei.com/task.html')
#		headers.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:11.0) Gecko/20100101 Firefox/11.0')
#		headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
#		headers.setdefault('Accept-Language', 'zh-cn,zh;q=0.7,en-us;q=0.3')
		response = self.urlopen(url, **args)
		data = response.read()
		if response.info().get('Content-Encoding') == 'gzip':
			data = ungzip(data)
		elif response.info().get('Content-Encoding') == 'deflate':
			data = undeflate(data)
		return data

	def urlread(self, url, **args):
		data = self.urlread1(url, **args)
		if self.is_session_timeout(data):
			logger.debug('session timed out')
			self.login()
			data = self.urlread1(url, **args)
		return data

	def load_cookies(self):
		self.cookiejar.load(self.cookie_path, ignore_discard=True, ignore_expires=True)

	def save_cookies(self):
		if self.cookie_path:
			self.cookiejar.save(self.cookie_path, ignore_discard=True)

	def get_cookie(self, domain, k):
		if self.has_cookie(domain, k):
			return self.cookiejar._cookies[domain]['/'][k].value

	def has_cookie(self, domain, k):
		return domain in self.cookiejar._cookies and k in self.cookiejar._cookies[domain]['/']

	def get_userid(self):
		if self.has_cookie('.xunlei.com', 'userid'):
			return self.get_cookie('.xunlei.com', 'userid')
		else:
			raise Exception('Probably login failed')

	def get_userid_or_none(self):
		return self.get_cookie('.xunlei.com', 'userid')

	def get_username(self):
		return self.get_cookie('.xunlei.com', 'usernewno')

	def get_gdriveid(self):
		return self.get_cookie('.vip.xunlei.com', 'gdriveid')

	def has_gdriveid(self):
		return self.has_cookie('.vip.xunlei.com', 'gdriveid')

	def get_referer(self):
		return 'http://dynamic.cloud.vip.xunlei.com/user_task?userid=%s' % self.id

	def set_cookie(self, domain, k, v):
		c = cookielib.Cookie(version=0, name=k, value=v, port=None, port_specified=False, domain=domain, domain_specified=True, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={}, rfc2109=False)
		self.cookiejar.set_cookie(c)

	def del_cookie(self, domain, k):
		if self.has_cookie(domain, k):
			self.cookiejar.clear(domain=domain, path="/", name=k)

	def set_gdriveid(self, id):
		self.set_cookie('.vip.xunlei.com', 'gdriveid', id)

	def set_page_size(self, n):
		self.set_cookie('.vip.xunlei.com', 'pagenum', str(n))

	def get_cookie_header(self):
		def domain_header(domain):
			root = self.cookiejar._cookies[domain]['/']
			return '; '.join(k+'='+root[k].value for k in root)
		return  domain_header('.xunlei.com') + '; ' + domain_header('.vip.xunlei.com')

	def is_login_ok(self, html):
		return len(html) > 512

	def has_logged_in(self):
		id = self.get_userid_or_none()
		if not id:
			return False
		#print self.urlopen('http://dynamic.cloud.vip.xunlei.com/user_task?userid=%s&st=0' % id).read().decode('utf-8')
		with self.attr(page_size=1):
			url = 'http://dynamic.cloud.vip.xunlei.com/user_task?userid=%s&st=0' % id
			#url = 'http://dynamic.lixian.vip.xunlei.com/login?cachetime=%d' % current_timestamp()
			r = self.is_login_ok(self.urlread(url))
			return r

	def is_session_timeout(self, html):
		is_timeout = html == '''<script>document.cookie ="sessionid=; path=/; domain=xunlei.com"; document.cookie ="lx_sessionid=; path=/; domain=vip.xunlei.com";top.location='http://cloud.vip.xunlei.com/task.html?error=1'</script>''' or html == '''<script>document.cookie ="sessionid=; path=/; domain=xunlei.com"; document.cookie ="lsessionid=; path=/; domain=xunlei.com"; document.cookie ="lx_sessionid=; path=/; domain=vip.xunlei.com";top.location='http://cloud.vip.xunlei.com/task.html?error=2'</script>''' or html == '''<script>document.cookie ="sessionid=; path=/; domain=xunlei.com"; document.cookie ="lsessionid=; path=/; domain=xunlei.com"; document.cookie ="lx_sessionid=; path=/; domain=vip.xunlei.com";document.cookie ="lx_login=; path=/; domain=vip.xunlei.com";top.location='http://cloud.vip.xunlei.com/task.html?error=1'</script>'''
		if is_timeout:
			logger.trace(html)
			return True
		maybe_timeout = html == '''rebuild({"rtcode":-1,"list":[]})'''
		if maybe_timeout:
			if self.login_time and time.time() - self.login_time < 60 * 10: # 10 minutes
				return False
			else:
				logger.trace(html)
				return True
		return is_timeout

	def read_verification_code(self):
		if not self.verification_code_reader:
			raise NotImplementedError('Verification code required')
		else:
			verification_code_url = 'http://verify2.xunlei.com/image?t=MVA&cachetime=%s' % current_timestamp()
			image = self.urlopen(verification_code_url).read()
			return self.verification_code_reader(image)

	def login(self, username=None, password=None):
		username = self.username
		password = self.password
		if not username and self.has_cookie('.xunlei.com', 'usernewno'):
			username = self.get_username()
		if not username:
			# TODO: don't depend on lixian_config
			import lixian_config
			username = lixian_config.get_config('username')
#			if not username:
#				raise NotImplementedError('user is not logged in')
		if not password:
			raise NotImplementedError('user is not logged in')

		logger.debug('login')
		cachetime = current_timestamp()
		check_url = 'http://login.xunlei.com/check?u=%s&cachetime=%d' % (username, cachetime)
		login_page = self.urlopen(check_url).read()
		verification_code = self.get_cookie('.xunlei.com', 'check_result')[2:].upper()
		if not verification_code:
			verification_code = self.read_verification_code()
			if verification_code:
				verification_code = verification_code.upper()
		assert verification_code
		password = encypt_password(password)
		password = md5(password+verification_code)
		login_page = self.urlopen('http://login.xunlei.com/sec2login/', data={'u': username, 'p': password, 'verifycode': verification_code})
		self.id = self.get_userid()
		with self.attr(page_size=1):
			login_page = self.urlopen('http://dynamic.lixian.vip.xunlei.com/login?cachetime=%d&from=0'%current_timestamp()).read()
		if not self.is_login_ok(login_page):
			logger.trace(login_page)
			raise RuntimeError('login failed')
		self.save_cookies()
		self.login_time = time.time()

	def logout(self):
		logger.debug('logout')
		#session_id = self.get_cookie('.xunlei.com', 'sessionid')
		#timestamp = current_timestamp()
		#url = 'http://login.xunlei.com/unregister?sessionid=%s&cachetime=%s&noCacheIE=%s' % (session_id, timestamp, timestamp)
		#self.urlopen(url).read()
		#self.urlopen('http://dynamic.vip.xunlei.com/login/indexlogin_contr/logout/').read()
		ckeys = ["vip_isvip","lx_sessionid","vip_level","lx_login","dl_enable","in_xl","ucid","lixian_section"]
		ckeys1 = ["sessionid","usrname","nickname","usernewno","userid"]
		self.del_cookie('.vip.xunlei.com', 'gdriveid')
		for k in ckeys:
			self.set_cookie('.vip.xunlei.com', k, '')
		for k in ckeys1:
			self.set_cookie('.xunlei.com', k, '')
		self.save_cookies()
		self.login_time = None

	def to_page_url(self, type_id, page_index, page_size):
		# type_id: 1 for downloading, 2 for completed, 4 for downloading+completed+expired, 11 for deleted, 13 for expired
		if type_id == 0:
			type_id = 4
		page = page_index + 1
		p = 1 # XXX: what is it?
		# jsonp = 'jsonp%s' % current_timestamp()
		# url = 'http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh?type_id=%s&page=%s&tasknum=%s&p=%s&interfrom=task&callback=%s' % (type_id, page, page_size, p, jsonp)
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh?type_id=%s&page=%s&tasknum=%s&p=%s&interfrom=task' % (type_id, page, page_size, p)
		return url

	@retry(10)
	def read_task_page_info_by_url(self, url):
		page = self.urlread(url).decode('utf-8', 'ignore')
		data = parse_json_response(page)
		if not self.has_gdriveid():
			gdriveid = data['info']['user']['cookie']
			self.set_gdriveid(gdriveid)
			self.save_cookies()
		# tasks = parse_json_tasks(data)
		tasks = [t for t in parse_json_tasks(data) if not t['expired']]
		for t in tasks:
			t['client'] = self
		# current_page = int(re.search(r'page=(\d+)', url).group(1))
		total_tasks = int(data['info']['total_num'])
		# assert total_pages >= data['global_new']['page'].count('<li><a')
		return {'tasks': tasks, 'total_task_number': total_tasks}

	def read_task_page_info_by_page_index(self, type_id, page_index, page_size):
		return self.read_task_page_info_by_url(self.to_page_url(type_id, page_index, page_size))

	def read_tasks(self, type_id=0):
		'''read one page'''
		page_size = self.page_size
		limit = self.limit
		if limit and limit < page_size:
			page_size = limit
		first_page = self.read_task_page_info_by_page_index(type_id, 0, page_size)
		tasks = first_page['tasks']
		for i, task in enumerate(tasks):
			task['#'] = i
		return tasks

	def read_all_tasks_immediately(self, type_id):
		'''read all pages'''
		all_tasks = []
		page_size = self.page_size
		limit = self.limit
		if limit and limit < page_size:
			page_size = limit
		first_page = self.read_task_page_info_by_page_index(type_id, 0, page_size)
		all_tasks.extend(first_page['tasks'])
		total_tasks = first_page['total_task_number']
		if limit and limit < total_tasks:
			total_tasks = limit
		total_pages = total_tasks / page_size
		if total_tasks % page_size != 0:
			total_pages += 1
		if total_pages == 0:
			total_pages = 1
		for page_index in range(1, total_pages):
			current_page = self.read_task_page_info_by_page_index(type_id, 0, page_size)
			all_tasks.extend(current_page['tasks'])
		if limit:
			all_tasks = all_tasks[0:limit]
		for i, task in enumerate(all_tasks):
			task['#'] = i
		return all_tasks

	def read_all_tasks_on_demand(self, type_id):
		'''read all pages, lazily'''
		fetch_page = lambda page_index, page_size: self.read_task_page_info_by_page_index(type_id, page_index, page_size)
		return OnDemandTaskList(fetch_page, self.page_size, self.limit)

	def read_all_tasks(self, type_id=0):
		'''read all pages'''
		return self.read_all_tasks_on_demand(type_id)

	def read_completed(self):
		'''read first page of completed tasks'''
		return self.read_tasks(2)

	def read_all_completed(self):
		'''read all pages of completed tasks'''
		return self.read_all_tasks(2)

	@retry(10)
	def read_categories(self):
#		url = 'http://dynamic.cloud.vip.xunlei.com/interface/menu_get?callback=jsonp%s&interfrom=task' % current_timestamp()
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/menu_get'
		html = self.urlread(url).decode('utf-8', 'ignore')
		result = parse_json_response(html)
		return dict((x['name'], int(x['id'])) for x in result['info'])

	def get_category_id(self, category):
		return self.read_categories()[category]

	def read_all_tasks_by_category(self, category):
		category_id = self.get_category_id(category)
		jsonp = 'jsonp%s' % current_timestamp()
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/show_class?callback=%s&type_id=%d' % (jsonp, category_id)
		html = self.urlread(url)
		response = json.loads(re.match(r'^%s\((.+)\)$' % jsonp, html).group(1))
		assert response['rtcode'] == '0', response['rtcode']
		info = response['info']
		tasks = map(convert_task, info['tasks'])
		for i, task in enumerate(tasks):
			task['client'] = self
			task['#'] = i
		return tasks

	def read_history_page_url(self, url):
		self.set_cookie('.vip.xunlei.com', 'lx_nf_all', urllib.quote('page_check_all=history&fltask_all_guoqi=1&class_check=0&page_check=task&fl_page_id=0&class_check_new=0&set_tab_status=11'))
		page = self.urlread(url).decode('utf-8', 'ignore')
		if not self.has_gdriveid():
			gdriveid = re.search(r'id="cok" value="([^"]+)"', page).group(1)
			self.set_gdriveid(gdriveid)
			self.save_cookies()
		tasks = parse_history(page)
		for t in tasks:
			t['client'] = self
		pginfo = re.search(r'<div class="pginfo">.*?</div>', page)
		match_next_page = re.search(r'<li class="next"><a href="([^"]+)">[^<>]*</a></li>', page)
		return tasks, match_next_page and 'http://dynamic.cloud.vip.xunlei.com'+match_next_page.group(1)

	def read_history_page(self, type=0, pg=None):
		if pg is None:
			url = 'http://dynamic.cloud.vip.xunlei.com/user_history?userid=%s&type=%d' % (self.id, type)
		else:
			url = 'http://dynamic.cloud.vip.xunlei.com/user_history?userid=%s&p=%d&type=%d' % (self.id, pg, type)
		return self.read_history_page_url(url)

	def read_history(self, type=0):
		'''read one page'''
		tasks = self.read_history_page(type)[0]
		for i, task in enumerate(tasks):
			task['#'] = i
		return tasks

	def read_all_history(self, type=0):
		'''read all pages of deleted/expired tasks'''
		all_tasks = []
		tasks, next_link = self.read_history_page(type)
		all_tasks.extend(tasks)
		while next_link:
			if self.limit and len(all_tasks) > self.limit:
				break
			tasks, next_link = self.read_history_page_url(next_link)
			all_tasks.extend(tasks)
		if self.limit:
			all_tasks = all_tasks[0:self.limit]
		for i, task in enumerate(all_tasks):
			task['#'] = i
		return all_tasks

	def read_deleted(self):
		return self.read_history()

	def read_all_deleted(self):
		return self.read_all_history()

	def read_expired(self):
		return self.read_history(1)

	def read_all_expired(self):
		return self.read_all_history(1)

	def list_bt(self, task):
		assert task['type'] == 'bt'
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/fill_bt_list?callback=fill_bt_list&tid=%s&infoid=%s&g_net=1&p=1&uid=%s&noCacheIE=%s' % (task['id'], task['bt_hash'], self.id, current_timestamp())
		with self.attr(page_size=self.bt_page_size):
			html = remove_bom(self.urlread(url)).decode('utf-8')
		sub_tasks = parse_bt_list(html)
		for t in sub_tasks:
			t['date'] = task['date']
		return sub_tasks

	def get_torrent_file_by_info_hash(self, info_hash):
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/get_torrent?userid=%s&infoid=%s' % (self.id, info_hash.upper())
		response = self.urlopen(url)
		torrent = response.read()
		if torrent == "<meta http-equiv='Content-Type' content='text/html; charset=utf-8' /><script>alert('\xe5\xaf\xb9\xe4\xb8\x8d\xe8\xb5\xb7\xef\xbc\x8c\xe6\xb2\xa1\xe6\x9c\x89\xe6\x89\xbe\xe5\x88\xb0\xe5\xaf\xb9\xe5\xba\x94\xe7\x9a\x84\xe7\xa7\x8d\xe5\xad\x90\xe6\x96\x87\xe4\xbb\xb6!');</script>":
			raise Exception('Torrent file not found on xunlei cloud: '+info_hash)
		assert response.headers['content-type'] == 'application/octet-stream'
		return torrent

	def get_torrent_file(self, task):
		return self.get_torrent_file_by_info_hash(task['bt_hash'])

	def add_task(self, url):
		protocol = parse_url_protocol(url)
		assert protocol in ('ed2k', 'http', 'https', 'ftp', 'thunder', 'Flashget', 'qqdl', 'bt', 'magnet'), 'protocol "%s" is not suppoted' % protocol

		from lixian_url import url_unmask
		url = url_unmask(url)
		protocol = parse_url_protocol(url)
		assert protocol in ('ed2k', 'http', 'https', 'ftp', 'bt', 'magnet'), 'protocol "%s" is not suppoted' % protocol

		if protocol == 'bt':
			return self.add_torrent_task_by_info_hash(url[5:])
		elif protocol == 'magnet':
			return self.add_magnet_task(url)

		random = current_random()
		check_url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_check?callback=queryCid&url=%s&random=%s&tcache=%s' % (urllib.quote(url), random, current_timestamp())
		js = self.urlread(check_url).decode('utf-8')
		qcid = re.match(r'^queryCid(\(.+\))\s*$', js).group(1)
		qcid = literal_eval(qcid)
		if len(qcid) == 8:
			cid, gcid, size_required, filename, goldbean_need, silverbean_need, is_full, random = qcid
		elif len(qcid) == 9:
			cid, gcid, size_required, filename, goldbean_need, silverbean_need, is_full, random, ext = qcid
		elif len(qcid) == 10:
			cid, gcid, size_required, some_key, filename, goldbean_need, silverbean_need, is_full, random, ext = qcid
		else:
			raise NotImplementedError(qcid)
		assert goldbean_need == 0
		assert silverbean_need == 0

		if url.startswith('http://') or url.startswith('ftp://'):
			task_type = 0
		elif url.startswith('ed2k://'):
			task_type = 2
		else:
			raise NotImplementedError()
		task_url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_commit?'+urlencode(
		   {'callback': 'ret_task',
		    'uid': self.id,
		    'cid': cid,
		    'gcid': gcid,
		    'size': size_required,
		    'goldbean': goldbean_need,
		    'silverbean': silverbean_need,
		    't': filename,
		    'url': url,
			'type': task_type,
		    'o_page': 'task',
		    'o_taskid': '0',
		    })

		response = self.urlread(task_url)
		assert response == 'ret_task(Array)', response

	def add_batch_tasks(self, urls, old_task_ids=None):
		assert urls
		urls = list(urls)
		for url in urls:
			if parse_url_protocol(url) not in ('http', 'https', 'ftp', 'ed2k', 'bt', 'thunder', 'magnet'):
				raise NotImplementedError('Unsupported: '+url)
		urls = filter(lambda u: parse_url_protocol(u) in ('http', 'https', 'ftp', 'ed2k', 'thunder'), urls)
		if not urls:
			return
		#self.urlopen('http://dynamic.cloud.vip.xunlei.com/interface/batch_task_check', data={'url':'\r\n'.join(urls), 'random':current_random()})
		jsonp = 'jsonp%s' % current_timestamp()
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/batch_task_commit?callback=%s' % jsonp
		if old_task_ids:
			batch_old_taskid = ','.join(old_task_ids)
		else:
			batch_old_taskid = '0' + ',' * (len(urls) - 1) # XXX: what is it?
		data = {}
		for i in range(len(urls)):
			data['cid[%d]' % i] = ''
			data['url[%d]' % i] = urllib.quote(to_utf_8(urls[i])) # fix per request #98
		data['batch_old_taskid'] = batch_old_taskid
		data['verify_code'] = ''
		response = self.urlread(url, data=data)

		code = get_response_code(response, jsonp)
		while code == -12 or code == -11:
			verification_code = self.read_verification_code()
			assert verification_code
			data['verify_code'] = verification_code
			response = self.urlread(url, data=data)
			code = get_response_code(response, jsonp)
		if code == len(urls):
			return
		else:
			assert code == len(urls), 'invalid response code: %s' % code

	def commit_torrent_task(self, data):
		jsonp = 'jsonp%s' % current_timestamp()
		commit_url = 'http://dynamic.cloud.vip.xunlei.com/interface/bt_task_commit?callback=%s' % jsonp
		response = self.urlread(commit_url, data=data)
		code = get_response_code(response, jsonp)['progress']
		while code == -12 or code == -11:
			verification_code = self.read_verification_code()
			assert verification_code
			data['verify_code'] = verification_code
			response = self.urlread(commit_url, data=data)
			code = get_response_code(response, jsonp)['progress']

	def add_torrent_task_by_content(self, content, path='attachment.torrent'):
		assert re.match(r'd\d+:', content), 'Probably not a valid content file [%s...]' % repr(content[:17])
		upload_url = 'http://dynamic.cloud.vip.xunlei.com/interface/torrent_upload'
		content_type, body = encode_multipart_formdata([], [('filepath', path, content)])
		response = self.urlread(upload_url, data=body, headers={'Content-Type': content_type}).decode('utf-8')

		upload_success = re.search(r'<script>document\.domain="xunlei\.com";var btResult =(\{.*\});</script>', response, flags=re.S)
		if upload_success:
			bt = json.loads(upload_success.group(1))
			bt_hash = bt['infoid']
			bt_name = bt['ftitle']
			bt_size = bt['btsize']
			data = {'uid':self.id, 'btname':bt_name, 'cid':bt_hash, 'tsize':bt_size,
					'findex':''.join(f['id']+'_' for f in bt['filelist']),
					'size':''.join(f['subsize']+'_' for f in bt['filelist']),
					'from':'0'}
			self.commit_torrent_task(data)
			return bt_hash
		already_exists = re.search(r"parent\.edit_bt_list\((\{.*\}),'','0'\)", response, flags=re.S)
		if already_exists:
			bt = json.loads(already_exists.group(1))
			bt_hash = bt['infoid']
			return bt_hash
		raise NotImplementedError(response)

	def add_torrent_task_by_info_hash(self, sha1):
		return self.add_torrent_task_by_content(self.get_torrent_file_by_info_hash(sha1), sha1.upper()+'.torrent')

	def add_torrent_task(self, path):
		with open(path, 'rb') as x:
			return self.add_torrent_task_by_content(x.read(), os.path.basename(path))

	def add_torrent_task_by_info_hash2(self, sha1, old_task_id=None):
		'''similar to add_torrent_task_by_info_hash, but faster. I may delete current add_torrent_task_by_info_hash completely in future'''
		link = 'http://dynamic.cloud.vip.xunlei.com/interface/get_torrent?userid=%s&infoid=%s' % (self.id, sha1.upper())
		return self.add_torrent_task_by_link(link, old_task_id=old_task_id)

	def add_magnet_task(self, link):
		return self.add_torrent_task_by_link(link)

	def add_torrent_task_by_link(self, link, old_task_id=None):
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/url_query?callback=queryUrl&u=%s&random=%s' % (urllib.quote(link), current_timestamp())
		response = self.urlread(url)
		success = re.search(r'queryUrl(\(1,.*\))\s*$', response, flags=re.S) # XXX: sometimes it returns queryUrl(0,...)?
		if not success:
			already_exists = re.search(r"queryUrl\(-1,'([^']{40})", response, flags=re.S)
			if already_exists:
				return already_exists.group(1)
			raise NotImplementedError(repr(response))
		args = success.group(1).decode('utf-8')
		args = literal_eval(args.replace('new Array', ''))
		_, cid, tsize, btname, _, names, sizes_, sizes, _, types, findexes, timestamp, _ = args
		def toList(x):
			if type(x) in (list, tuple):
				return x
			else:
				return [x]
		data = {'uid':self.id, 'btname':btname, 'cid':cid, 'tsize':tsize,
				'findex':''.join(x+'_' for x in toList(findexes)),
				'size':''.join(x+'_' for x in toList(sizes)),
				'from':'0'}
		if old_task_id:
			data['o_taskid'] = old_task_id
			data['o_page'] = 'history'
		self.commit_torrent_task(data)
		return cid

	def readd_all_expired_tasks(self):
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/delay_once?callback=anything'
		response = self.urlread(url)

	def delete_tasks_by_id(self, ids):
		jsonp = 'jsonp%s' % current_timestamp()
		data = {'taskids': ','.join(ids)+',', 'databases': '0,'}
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_delete?callback=%s&type=%s&noCacheIE=%s' % (jsonp, 2, current_timestamp()) # XXX: what is 'type'?
		response = self.urlread(url, data=data)
		response = remove_bom(response)
		assert_response(response, jsonp, '{"result":1,"type":2}')

	def delete_task_by_id(self, id):
		self.delete_tasks_by_id([id])

	def delete_task(self, task):
		self.delete_task_by_id(task['id'])

	def delete_tasks(self, tasks):
		self.delete_tasks_by_id([t['id'] for t in tasks])

	def pause_tasks_by_id(self, ids):
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_pause?tid=%s&uid=%s&noCacheIE=%s' % (','.join(ids)+',', self.id, current_timestamp())
		assert self.urlread(url) == 'pause_task_resp()'

	def pause_task_by_id(self, id):
		self.pause_tasks_by_id([id])

	def pause_task(self, task):
		self.pause_task_by_id(task['id'])

	def pause_tasks(self, tasks):
		self.pause_tasks_by_id(t['id'] for t in tasks)

	def restart_tasks(self, tasks):
		jsonp = 'jsonp%s' % current_timestamp()
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/redownload?callback=%s' % jsonp
		form = []
		for task in tasks:
			assert task['type'] in ('ed2k', 'http', 'https', 'ftp', 'https', 'bt'), "'%s' is not tested" % task['type']
			data = {'id[]': task['id'],
					'cid[]': '', # XXX: should I set this?
					'url[]': task['original_url'],
					'download_status[]': task['status']}
			if task['type'] == 'ed2k':
				data['taskname[]'] = task['name'].encode('utf-8') # XXX: shouldn't I set this for other task types?
			form.append(urlencode(data))
		form.append(urlencode({'type':1}))
		data = '&'.join(form)
		response = self.urlread(url, data=data)
		assert_response(response, jsonp)

	def rename_task(self, task, new_name):
		assert type(new_name) == unicode
		url = 'http://dynamic.cloud.vip.xunlei.com/interface/rename'
		taskid = task['id']
		bt = '1' if task['type'] == 'bt' else '0'
		url = url+'?'+urlencode({'taskid':taskid, 'bt':bt, 'filename':new_name.encode('utf-8')})
		response = self.urlread(url)
		assert '"result":0' in response, response

	def restart_task(self, task):
		self.restart_tasks([task])

	def get_task_by_id(self, id):
		tasks = self.read_all_tasks(0)
		for x in tasks:
			if x['id'] == id:
				return x
		raise Exception('No task found for id '+id)


def current_timestamp():
	return int(time.time()*1000)

def current_random():
	from random import randint
	return '%s%06d.%s' % (current_timestamp(), randint(0, 999999), randint(100000000, 9999999999))

def convert_task(data):
	expired = {'0':False, '4': True}[data['flag']]
	task = {'id': data['id'],
			'type': re.match(r'[^:]+', data['url']).group().lower(),
			'name': unescape_html(data['taskname']),
			'status': int(data['download_status']),
			'status_text': {'0':'waiting', '1':'downloading', '2':'completed', '3':'failed', '5':'pending'}[data['download_status']],
			'expired': expired,
			'size': int(data['ysfilesize']),
			'original_url': unescape_html(data['url']),
			'xunlei_url': data['lixian_url'] or None,
			'bt_hash': data['cid'],
			'dcid': data['cid'],
			'gcid': data['gcid'],
			'date': data['dt_committed'][:10].replace('-', '.'),
			'progress': '%s%%' % data['progress'],
			'speed': '%s' % data['speed'],
			}
	return task

def parse_json_response(html):
	m = re.match(ur'^\ufeff?rebuild\((\{.*\})\)$', html)
	if not m:
		logger.trace(html)
		raise RuntimeError('Invalid response')
	return json.loads(m.group(1))

def parse_json_tasks(result):
	tasks = result['info']['tasks']
	return map(convert_task, tasks)

def parse_task(html):
	inputs = re.findall(r'<input[^<>]+/>', html)
	def parse_attrs(html):
		return dict((k, v1 or v2) for k, v1, v2 in re.findall(r'''\b(\w+)=(?:'([^']*)'|"([^"]*)")''', html))
	info = dict((x['id'], unescape_html(x['value'])) for x in map(parse_attrs, inputs))
	mini_info = {}
	mini_map = {}
	#mini_info = dict((re.sub(r'\d+$', '', k), info[k]) for k in info)
	for k in info:
		mini_key = re.sub(r'\d+$', '', k)
		mini_info[mini_key] = info[k]
		mini_map[mini_key] = k
	taskid = mini_map['taskname'][8:]
	url = mini_info['f_url']
	task_type = re.match(r'[^:]+', url).group().lower()
	task = {'id': taskid,
	        'type': task_type,
	        'name': mini_info['taskname'],
	        'status': int(mini_info['d_status']),
	        'status_text': {'0':'waiting', '1':'downloading', '2':'completed', '3':'failed', '5':'pending'}[mini_info['d_status']],
	        'size': int(mini_info.get('ysfilesize', 0)),
	        'original_url': mini_info['f_url'],
	        'xunlei_url': mini_info.get('dl_url', None),
	        'bt_hash': mini_info['dcid'],
	        'dcid': mini_info['dcid'],
	        'gcid': parse_gcid(mini_info.get('dl_url', None)),
	        }

	m = re.search(r'<em class="loadnum"[^<>]*>([^<>]*)</em>', html)
	task['progress'] = m and m.group(1) or ''
	m = re.search(r'<em [^<>]*id="speed\d+">([^<>]*)</em>', html)
	task['speed'] = m and m.group(1).replace('&nbsp;', '') or ''
	m = re.search(r'<span class="c_addtime">([^<>]*)</span>', html)
	task['date'] = m and m.group(1) or ''

	return task

def parse_history(html):
	rwbox = re.search(r'<div class="rwbox" id="rowbox_list".*?<!--rwbox-->', html, re.S).group()
	rw_lists = re.findall(r'<div class="rw_list".*?<input id="d_tasktype\d+"[^<>]*/>', rwbox, re.S)
	return map(parse_task, rw_lists)

def parse_bt_list(js):
	result = json.loads(re.match(r'^fill_bt_list\((.+)\)\s*$', js).group(1))['Result']
	files = []
	for record in result['Record']:
		files.append({
			'id': record['taskid'],
			'index': record['id'],
			'type': 'bt',
			'name': record['title'], # TODO: support folder
			'status': int(record['download_status']),
			'status_text': {'0':'waiting', '1':'downloading', '2':'completed', '3':'failed', '5':'pending'}[record['download_status']],
			'size': int(record['filesize']),
			'original_url': record['url'],
			'xunlei_url': record['downurl'],
			'dcid': record['cid'],
			'gcid': parse_gcid(record['downurl']),
			'speed': '',
			'progress': '%s%%' % record['percent'],
			'date': '',
			})
	return files

def parse_gcid(url):
	if not url:
		return
	m = re.search(r'&g=([A-F0-9]{40})&', url)
	if not m:
		return
	return m.group(1)

def urlencode(x):
	def unif8(u):
		if type(u) == unicode:
			u = u.encode('utf-8')
		return u
	return urllib.urlencode([(unif8(k), unif8(v)) for k, v in x.items()])

def encode_multipart_formdata(fields, files):
	#http://code.activestate.com/recipes/146306/
	"""
	fields is a sequence of (name, value) elements for regular form fields.
	files is a sequence of (name, filename, value) elements for data to be uploaded as files
	Return (content_type, body) ready for httplib.HTTP instance
	"""
	BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
	CRLF = '\r\n'
	L = []
	for (key, value) in fields:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"' % key)
		L.append('')
		L.append(value)
	for (key, filename, value) in files:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
		L.append('Content-Type: %s' % get_content_type(filename))
		L.append('')
		L.append(value)
	L.append('--' + BOUNDARY + '--')
	L.append('')
	body = CRLF.join(L)
	content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
	return content_type, body

def get_content_type(filename):
	import mimetypes
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def assert_default_page(response, id):
	#assert response == "<script>top.location='http://dynamic.cloud.vip.xunlei.com/user_task?userid=%s&st=0'</script>" % id
	assert re.match(r"^<script>top\.location='http://dynamic\.cloud\.vip\.xunlei\.com/user_task\?userid=%s&st=0(&cache=\d+)?'</script>$" % id, response), response

def remove_bom(response):
	if response.startswith('\xef\xbb\xbf'):
		response = response[3:]
	return response

def assert_response(response, jsonp, value=1):
	response = remove_bom(response)
	assert response == '%s(%s)' % (jsonp, value), repr(response)

def get_response_code(response, jsonp):
	response = remove_bom(response)
	m = re.match(r'^%s\((.+)\)$' % jsonp, response)
	assert m, 'invalid jsonp response: %s' % response
	return json.loads(m.group(1))

def parse_url_protocol(url):
	m = re.match(r'([^:]+)://', url)
	if m:
		return m.group(1)
	elif url.startswith('magnet:'):
		return 'magnet'
	else:
		return url

def unescape_html(html):
	import xml.sax.saxutils
	return xml.sax.saxutils.unescape(html)

def to_utf_8(s):
	if type(s) == unicode:
		return s.encode('utf-8')
	else:
		return s

def md5(s):
	import hashlib
	return hashlib.md5(s).hexdigest().lower()

def encypt_password(password):
	if not re.match(r'^[0-9a-f]{32}$', password):
		password = md5(md5(password))
	return password

def ungzip(s):
	from StringIO import StringIO
	import gzip
	buffer = StringIO(s)
	f = gzip.GzipFile(fileobj=buffer)
	return f.read()

def undeflate(s):
	import zlib
	return zlib.decompress(s, -zlib.MAX_WBITS)



########NEW FILE########
__FILENAME__ = lixian_alias


__all__ = ['register_alias', 'to_alias']

aliases = {'d': 'download', 'l': 'list', 'a': 'add', 'x': 'delete'}

def register_alias(alias, command):
	aliases[alias] = command

def get_aliases():
	return aliases

def get_alias(a):
	aliases = get_aliases()
	if a in aliases:
		return aliases[a]

def to_alias(a):
	return get_alias(a) or a


########NEW FILE########
__FILENAME__ = lixian_batch
#!/usr/bin/env python

import sys
import os.path
import lixian_cli

def download_batch(files):
	for f in map(os.path.abspath, files):
		print 'Downloading', f, '...'
		os.chdir(os.path.dirname(f))
		lixian_cli.execute_command(['download', '--input', f, '--delete', '--continue'])

if __name__ == '__main__':
	download_batch(sys.argv[1:])


########NEW FILE########
__FILENAME__ = lixian_cli
#!/usr/bin/env python

from lixian_commands.util import *
import lixian_help
import sys

from lixian_commands.login import login
from lixian_commands.logout import logout
from lixian_commands.download import download_task
from lixian_commands.list import list_task
from lixian_commands.add import add_task
from lixian_commands.delete import delete_task
from lixian_commands.pause import pause_task
from lixian_commands.restart import restart_task
from lixian_commands.rename import rename_task
from lixian_commands.readd import readd_task
from lixian_commands.info import lixian_info
from lixian_commands.config import lx_config
from lixian_commands.help import lx_help


def execute_command(args=sys.argv[1:]):
	import lixian_plugins # load plugins at import
	if not args:
		usage()
		sys.exit(1)
	command = args[0]
	if command.startswith('-'):
		if command in ('-h', '--help'):
			usage(lixian_help.welcome_help)
		elif command in ('-v', '--version'):
			print '0.0.x'
		else:
			usage()
			sys.exit(1)
		sys.exit(0)
	import lixian_alias
	command = lixian_alias.to_alias(command)
	commands = {'login': login,
	            'logout': logout,
	            'download': download_task,
	            'list': list_task,
	            'add': add_task,
	            'delete': delete_task,
	            'pause': pause_task,
	            'restart': restart_task,
	            'rename': rename_task,
	            'readd': readd_task,
	            'info': lixian_info,
	            'config': lx_config,
	            'help': lx_help}
	import lixian_plugins.commands
	commands.update(lixian_plugins.commands.commands)
	if command not in commands:
		usage()
		sys.exit(1)
	if '-h' in args or '--help' in args:
		lx_help([command])
	else:
		commands[command](args[1:])

if __name__ == '__main__':
	execute_command()



########NEW FILE########
__FILENAME__ = lixian_cli_parser

__all__ = ['expand_command_line', 'parse_command_line', 'Parser', 'command_line_parse', 'command_line_option', 'command_line_value', 'command_line_parser', 'with_parser']

def expand_windows_command_line(args):
	from glob import glob
	expanded = []
	for x in args:
		try:
			xx = glob(x)
		except:
			xx = None
		if xx:
			expanded += xx
		else:
			expanded.append(x)
	return expanded

def expand_command_line(args):
	import platform
	return expand_windows_command_line(args) if platform.system() == 'Windows' else args

def parse_command_line(args, keys=[], bools=[], alias={}, default={}, help=None):
	args = expand_command_line(args)
	options = {}
	for k in keys:
		options[k] = None
	for k in bools:
		options[k] = None
	left = []
	args = args[:]
	while args:
		x = args.pop(0)
		if x == '--':
			left.extend(args)
			break
		if x.startswith('-') and len(x) > 1:
			k = x.lstrip('-')
			if k in bools:
				options[k] = True
			elif k.startswith('no-') and k[3:] in bools:
				options[k[3:]] = False
			elif k in keys:
				options[k] = args.pop(0)
			elif '=' in k and k[:k.index('=')] in keys:
				options[k[:k.index('=')]] = k[k.index('=')+1:]
			elif k in alias:
				k = alias[k]
				if k in bools:
					options[k] = True
				else:
					options[k] = args.pop(0)
			elif '=' in k and k[:k.index('=')] in alias:
				k, v = k[:k.index('=')], k[k.index('=')+1:]
				k = alias[k]
				if k not in keys:
					raise RuntimeError('Invalid boolean option '+x)
				options[k] = v
			else:
				if help:
					print 'Unknown option ' + x
					print
					print help
					exit(1)
				else:
					raise RuntimeError('Unknown option '+x)
		else:
			left.append(x)

	for k in default:
		if options[k] is None:
			options[k] = default[k]

	class Args(object):
		def __init__(self, args, left):
			self.__dict__['_args'] = args
			self.__dict__['_left'] = left
		def __getattr__(self, k):
			v = self._args.get(k, None)
			if v:
				return v
			if '_' in k:
				return self._args.get(k.replace('_', '-'), None)
		def __setattr__(self, k, v):
			self._args[k] = v
		def __getitem__(self, i):
			if type(i) == int:
				return self._left[i]
			else:
				return self._args[i]
		def __setitem__(self, i, v):
			if type(i) == int:
				self._left[i] = v
			else:
				self._args[i] = v
		def __len__(self):
			return len(self._left)
		def __str__(self):
			return '<Args%s%s>' % (self._args, self._left)
	return Args(options, left)

class Stack:
	def __init__(self, **args):
		self.__dict__.update(args)

class Parser:
	def __init__(self):
		self.stack = []
	def with_parser(self, parser):
		self.stack.append(parser)
		return self
	def __call__(self, args, keys=[], bools=[], alias={}, default={}, help=None):
		stack = Stack(keys=list(keys), bools=list(bools), alias=dict(alias), default=dict(default))
		keys = []
		bools = []
		alias = {}
		default = {}
		for stack in [x.args_stack for x in self.stack] + [stack]:
			keys += stack.keys
			bools += stack.bools
			alias.update(stack.alias)
			default.update(stack.default)
		args = parse_command_line(args, keys=keys, bools=bools, alias=alias, default=default, help=help)
		for fn in self.stack:
			new_args = fn(args)
			if new_args:
				args = new_args
		return args

def command_line_parse(keys=[], bools=[], alias={}, default={}):
	def wrapper(fn):
		if hasattr(fn, 'args_stack'):
			stack = fn.args_stack
			stack.keys += keys
			stack.bools += bools
			stack.alias.update(alias)
			stack.default.update(default)
		else:
			fn.args_stack = Stack(keys=list(keys), bools=list(bools), alias=dict(alias), default=dict(default))
		return fn
	return wrapper

def command_line_option(name, alias=None, default=None):
	alias = {alias:name} if alias else {}
	default = {name:default} if default is not None else {}
	return command_line_parse(bools=[name], alias=alias, default=default)

def command_line_value(name, alias=None, default=None):
	alias = {alias:name} if alias else {}
	default = {name:default} if default else {}
	return command_line_parse(keys=[name], alias=alias, default=default)

def command_line_parser(*args, **kwargs):
	def wrapper(f):
		parser = Parser()
		for x in reversed(getattr(f, 'args_parsers', [])):
			parser = parser.with_parser(x)
		if hasattr(f, 'args_stack'):
			def parse_no_body(args):
				pass
			parse_no_body.args_stack = f.args_stack
			parser = parser.with_parser(parse_no_body)
		import functools
		@functools.wraps(f)
		def parse(args_list):
			return f(parser(args_list, *args, **kwargs))
		return parse
	return wrapper

def with_parser(parser):
	def wrapper(f):
		if hasattr(f, 'args_parsers'):
			f.args_parsers.append(parser)
		else:
			f.args_parsers = [parser]
		return f
	return wrapper



########NEW FILE########
__FILENAME__ = lixian_colors

import os
import sys

def get_console_type(use_colors=True):
	if use_colors and sys.stdout.isatty() and sys.stderr.isatty():
		import platform
		if platform.system() == 'Windows':
			import lixian_colors_win32
			return lixian_colors_win32.WinConsole
		else:
			import lixian_colors_linux
			return lixian_colors_linux.AnsiConsole
	else:
		import lixian_colors_console
		return lixian_colors_console.Console

console_type = get_console_type()
raw_console_type = get_console_type(False)

def Console(use_colors=True):
	return get_console_type(use_colors)()

def get_softspace(output):
	if hasattr(output, 'softspace'):
		return output.softspace
	import lixian_colors_console
	if isinstance(output, lixian_colors_console.Console):
		return get_softspace(output.output)
	return 0

class ScopedColors(console_type):
	def __init__(self, *args):
		console_type.__init__(self, *args)
	def __call__(self):
		console = self
		class Scoped:
			def __enter__(self):
				self.stdout = sys.stdout
				softspace = get_softspace(sys.stdout)
				sys.stdout = console
				sys.stdout.softspace = softspace
			def __exit__(self, type, value, traceback):
				softspace = get_softspace(sys.stdout)
				sys.stdout = self.stdout
				sys.stdout.softspace = softspace
		return Scoped()

class RawScopedColors(raw_console_type):
	def __init__(self, *args):
		raw_console_type.__init__(self, *args)
	def __call__(self):
		class Scoped:
			def __enter__(self):
				pass
			def __exit__(self, type, value, traceback):
				pass
		return Scoped()

class RootColors:
	def __init__(self, use_colors=True):
		self.use_colors = use_colors
	def __getattr__(self, name):
		return getattr(ScopedColors() if self.use_colors else RawScopedColors(), name)
	def __call__(self, use_colors):
		assert use_colors in (True, False, None), use_colors
		return RootColors(use_colors)

colors = RootColors()


########NEW FILE########
__FILENAME__ = lixian_colors_console

__all__ = ['Console']

import sys

styles = [
	'black',
	'blue',
	'green',
	'red',
	'cyan',
	'yellow',
	'purple',
	'white',

	'bold',
	'italic',
	'underline',
	'inverse',
]


class Console:
	def __init__(self, output=None, styles=[]):
		output = output or sys.stdout
		if isinstance(output, Console):
			self.output = output.output
			self.styles = output.styles + styles
		else:
			self.output = output
			self.styles = styles
		assert not isinstance(self.output, Console)
	def __getattr__(self, name):
		if name in styles:
			return self.ansi(name)
		else:
			raise AttributeError(name)
	def ansi(self, code):
		return self.__class__(self.output, self.styles + [code]) if code not in (None, '') else self
	def __call__(self, s):
		self.write(s)
	def write(self, s):
		self.output.write(s)
	def flush(self, *args):
		self.output.flush(*args)


########NEW FILE########
__FILENAME__ = lixian_colors_linux

__all__ = ['AnsiConsole']

from lixian_colors_console import Console

import sys

colors = {
	'bold' : [1, 22],
	'italic' : [3, 23],
	'underline' : [4, 24],
	'inverse' : [7, 27],
	'white' : [37, 39],
	'grey' : [90, 39],
	'black' : [30, 39],
	'blue' : [34, 39],
	'cyan' : [36, 39],
	'green' : [32, 39],
	'purple' : [35, 39],
	'magenta' : [35, 39],
	'red' : [31, 39],
	'yellow' : [33, 39]
}

class Render:
	def __init__(self, output, code):
		self.output = output
		self.left, self.right = code
	def __enter__(self):
		self.output.write(self.left)
		self.output.flush()
	def __exit__(self, type, value, traceback):
		self.output.write(self.right)
		self.output.flush()

def mix_styles(styles):
	left = []
	right = []
	for style in styles:
		if style in colors:
			color = colors[style]
			left.append(color[0])
			right.append(color[1])
	right.reverse()
	return [''.join('\033[%dm' % n for n in left), ''.join('\033[%dm' % n for n in right)]

class AnsiConsole(Console):
	def __init__(self, output=None, styles=[]):
		Console.__init__(self, output, styles)

	def write(self, s):
		if self.styles:
			with self.render(mix_styles(self.styles)):
				self.output.write(s)
				self.output.flush()
		else:
			self.output.write(s)
			self.output.flush()

	def render(self, code):
		return Render(self.output, code)


########NEW FILE########
__FILENAME__ = lixian_colors_win32

__all__ = ['WinConsole']

from lixian_colors_console import Console

import ctypes
from ctypes import windll, byref, Structure
from ctypes.wintypes import SHORT, WORD

import sys

INVALID_HANDLE_VALUE = -1
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

class COORD(Structure):
	_fields_ = (('X',  SHORT),
	            ('Y',  SHORT),)

class SMALL_RECT(Structure):
	_fields_ = (('Left',  SHORT),
	            ('Top',  SHORT),
	            ('Right',  SHORT),
	            ('Bottom',  SHORT),)

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
	_fields_ = (('dwSize',  COORD),
	            ('dwCursorPosition',  COORD),
	            ('wAttributes',  WORD),
	            ('srWindow',  SMALL_RECT),
	            ('dwMaximumWindowSize',  COORD),)


def GetWinError():
	code = ctypes.GetLastError()
	message = ctypes.FormatError(code)
	return '[Error %s] %s' % (code, message)

def GetStdHandle(handle):
	h = windll.kernel32.GetStdHandle(handle)
	if h == INVALID_HANDLE_VALUE:
		raise OSError(GetWinError())
	return h

def GetConsoleScreenBufferInfo(handle):
	info = CONSOLE_SCREEN_BUFFER_INFO()
	if not windll.kernel32.GetConsoleScreenBufferInfo(handle, byref(info)):
		raise OSError(GetWinError())
	return info

def SetConsoleTextAttribute(handle, attributes):
	if not windll.Kernel32.SetConsoleTextAttribute(handle, attributes):
		raise OSError(GetWinError())


FOREGROUND_BLUE            = 0x0001
FOREGROUND_GREEN           = 0x0002
FOREGROUND_RED             = 0x0004
FOREGROUND_INTENSITY       = 0x0008
BACKGROUND_BLUE            = 0x0010
BACKGROUND_GREEN           = 0x0020
BACKGROUND_RED             = 0x0040
BACKGROUND_INTENSITY       = 0x0080
COMMON_LVB_LEADING_BYTE    = 0x0100
COMMON_LVB_TRAILING_BYTE   = 0x0200
COMMON_LVB_GRID_HORIZONTAL = 0x0400
COMMON_LVB_GRID_LVERTICAL  = 0x0800
COMMON_LVB_GRID_RVERTICAL  = 0x1000
COMMON_LVB_REVERSE_VIDEO   = 0x4000
COMMON_LVB_UNDERSCORE      = 0x8000

colors = {
	'black'  : 0b000,
	'blue'   : 0b001,
	'green'  : 0b010,
	'red'    : 0b100,
	'cyan'   : 0b011,
	'yellow' : 0b110,
	'purple' : 0b101,
	'magenta': 0b101,
	'white'  : 0b111,
}

def mix_styles(styles, attributes):
	fg_color = -1
	bg_color = -1
	fg_bright = -1
	bg_bright = -1
	reverse = -1
	underscore = -1
	for style in styles:
		if style == 0:
			# reset mode
			raise NotImplementedError()
		elif style == 1:
			# foreground bright on
			fg_bright = 1
		elif style == 2:
			# both bright off
			fg_bright = 0
			bg_bright = 0
		elif style == 4 or style == 'underline':
			# Underscore
			underscore = 1
		elif style == 5:
			# background bright on
			bg_bright = 1
		elif style == 7 or style == 'inverse':
			# Reverse foreground and background attributes.
			reverse = 1
		elif style == 21 or style == 22:
			# foreground bright off
			fg_bright = 0
		elif style == 24:
			# Underscore: no
			underscore = 0
		elif style == 25:
			# background bright off
			bg_bright = 0
		elif style == 27:
			# Reverse: no
			reverse = 0
		elif 30 <= style <= 37:
			# set foreground color
			fg_color = style - 30
		elif style == 39:
			# default text color
			fg_color = 7
			fg_bright = 0
		elif 40 <= style <= 47:
			# set background color
			bg_color = style - 40
		elif style == 49:
			# default background color
			bg_color = 0
		elif 90 <= style <= 97:
			# set bold foreground color
			fg_bright = 1
			fg_color = style - 90
		elif 100 <= style <= 107:
			# set bold background color
			bg_bright = 1
			bg_color = style - 100
		elif style == 'bold':
			fg_bright = 1
		elif style in colors:
			fg_color = colors[style]

	if fg_color != -1:
		attributes &= ~ 0b111
		attributes |= fg_color
	if fg_bright != -1:
		attributes &= ~ 0b1000
		attributes |= fg_bright << 3
	if bg_color != -1:
		attributes &= ~ 0b1110000
		attributes |= bg_color << 4
	if bg_bright != -1:
		attributes &= ~ 0b10000000
		attributes |= bg_bright << 7
	if reverse != -1:
		attributes &= ~ COMMON_LVB_REVERSE_VIDEO
		attributes |= reverse << 14
		# XXX: COMMON_LVB_REVERSE_VIDEO doesn't work...
		if reverse:
			attributes = (attributes & ~(0b11111111 | COMMON_LVB_REVERSE_VIDEO)) | ((attributes & 0b11110000) >> 4) | ((attributes & 0b1111) << 4)
	if underscore != -1:
		attributes &= ~ COMMON_LVB_UNDERSCORE
		attributes |= underscore << 15

	return attributes

class Render:
	def __init__(self, handle, default, attributes):
		self.handle = handle
		self.default = default
		self.attributes = attributes
	def __enter__(self):
		SetConsoleTextAttribute(self.handle, self.attributes)
	def __exit__(self, type, value, traceback):
		SetConsoleTextAttribute(self.handle, self.default)

class WinConsole(Console):
	def __init__(self, output=None, styles=[], handle=STD_OUTPUT_HANDLE):
		Console.__init__(self, output, styles)
		self.handle = GetStdHandle(handle)
		self.default = GetConsoleScreenBufferInfo(self.handle).wAttributes

	def write(self, s):
		if self.styles:
			with self.render(mix_styles(self.styles, self.default)):
				self.output.write(s)
				self.output.flush()
		else:
			self.output.write(s)
			self.output.flush()

	def render(self, attributes):
		return Render(self.handle, self.default, attributes)



########NEW FILE########
__FILENAME__ = add

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import get_config
import lixian_help
import lixian_query

@command_line_parser(help=lixian_help.add)
@with_parser(parse_login)
@with_parser(parse_colors)
@with_parser(parse_logging)
@with_parser(parse_size)
@command_line_value('limit', default=get_config('limit'))
@command_line_value('page-size', default=get_config('page-size'))
@command_line_value('input', alias='i')
@command_line_option('torrent', alias='bt')
def add_task(args):
	assert len(args) or args.input
	client = create_client(args)
	tasks = lixian_query.find_tasks_to_download(client, args)
	print 'All tasks added. Checking status...'
	columns = ['id', 'status', 'name']
	if get_config('n'):
		columns.insert(0, 'n')
	if args.size:
		columns.append('size')
	output_tasks(tasks, columns, args)

########NEW FILE########
__FILENAME__ = config


from lixian import encypt_password
from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import *
import lixian_help
from getpass import getpass

@command_line_parser(help=lixian_help.config)
@command_line_option('print')
@command_line_option('delete')
def lx_config(args):
	if args.delete:
		assert len(args) == 1
		delete_config(args[0])
	elif args['print'] or not len(args):
		if len(args):
			assert len(args) == 1
			print get_config(args[0])
		else:
			print 'Loading', global_config.path, '...\n'
			print source_config()
			print global_config
	else:
		assert len(args) in (1, 2)
		if args[0] == 'password':
			if len(args) == 1 or args[1] == '-':
				password = getpass('Password: ')
			else:
				password = args[1]
			print 'Saving password (encrypted) to', global_config.path
			put_config('password', encypt_password(password))
		else:
			print 'Saving configuration to', global_config.path
			put_config(*args)

########NEW FILE########
__FILENAME__ = delete

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import get_config
from lixian_encoding import default_encoding
from lixian_colors import colors
import lixian_help
import lixian_query

@command_line_parser(help=lixian_help.delete)
@with_parser(parse_login)
@with_parser(parse_colors)
@with_parser(parse_logging)
@command_line_option('i')
@command_line_option('all')
@command_line_option('failed')
@command_line_value('limit', default=get_config('limit'))
@command_line_value('page-size', default=get_config('page-size'))
def delete_task(args):
	client = create_client(args)
	to_delete = lixian_query.search_tasks(client, args)
	if not to_delete:
		print 'Nothing to delete'
		return
	with colors(args.colors).red.bold():
		print "Below files are going to be deleted:"
		for x in to_delete:
			print x['name'].encode(default_encoding)
	if args.i:
		yes_or_no = raw_input('Are your sure to delete them from Xunlei cloud? (y/n) ')
		while yes_or_no.lower() not in ('y', 'yes', 'n', 'no'):
			yes_or_no = raw_input('yes or no? ')
		if yes_or_no.lower() in ('y', 'yes'):
			pass
		elif yes_or_no.lower() in ('n', 'no'):
			print 'Deletion abort per user request.'
			return
	client.delete_tasks(to_delete)

########NEW FILE########
__FILENAME__ = download

import lixian_download_tools
import lixian_nodes
from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import *
from lixian_encoding import default_encoding
from lixian_colors import colors
import lixian_help
import lixian_query
import lixian_hash
import lixian_hash_bt
import lixian_hash_ed2k

import os
import os.path
import re

def ensure_dir_exists(dirname):
	if dirname and not os.path.exists(dirname):
		try:
			os.makedirs(dirname)
		except os.error:
			if not os.path.exists(dirname):
				raise

def escape_filename(name):
	amp = re.compile(r'&(amp;)+', flags=re.I)
	name = re.sub(amp, '&', name)
	name = re.sub(r'[\\/:*?"<>|]', '-', name)
	return name

def safe_encode_native_path(path):
	return path.encode(default_encoding).decode(default_encoding).replace('?', '-').encode(default_encoding)

def verify_basic_hash(path, task):
	if os.path.getsize(path) != task['size']:
		print 'hash error: incorrect file size (%s != %s)' % (os.path.getsize(path), task['size'])
		return False
	return lixian_hash.verify_dcid(path, task['dcid'])

def verify_hash(path, task):
	if verify_basic_hash(path, task):
		if task['type'] == 'ed2k':
			return lixian_hash_ed2k.verify_ed2k_link(path, task['original_url'])
		else:
			return True

def verify_mini_hash(path, task):
	return os.path.exists(path) and os.path.getsize(path) == task['size'] and lixian_hash.verify_dcid(path, task['dcid'])

def verify_mini_bt_hash(dirname, files):
	for f in files:
		name = f['name'].encode(default_encoding)
		path = os.path.join(dirname, *name.split('\\'))
		if not verify_mini_hash(path, f):
			return False
	return True

def download_file(client, path, task, options):
	download_tool = lixian_download_tools.get_tool(options['tool'])

	resuming = options.get('resuming')
	overwrite = options.get('overwrite')
	mini_hash = options.get('mini_hash')
	no_hash = options.get('no_hash')

	url = str(task['xunlei_url'])
	if options['node']:
		if options['node'] == 'best' or options['node'] == 'fastest':
			from lixian_util import parse_size
			if task['size'] >= parse_size(options['node_detection_threshold']):
				url = lixian_nodes.use_fastest_node(url, options['vod_nodes'], client.get_gdriveid())
		elif options['node'] == 'fast':
			from lixian_util import parse_size
			if task['size'] >= parse_size(options['node_detection_threshold']):
				url = lixian_nodes.use_fast_node(url, options['vod_nodes'], parse_size(options['node_detection_acceptable']), client.get_gdriveid())
		else:
			url = lixian_nodes.switch_node(url, options['node'], client.get_gdriveid())

	def download1(download, path):
		if not os.path.exists(path):
			download()
		elif not resuming:
			if overwrite:
				download()
			else:
				raise Exception('%s already exists. Please try --continue or --overwrite' % path)
		else:
			if download.finished():
				pass
			else:
				download()

	def download1_checked(client, url, path, size):
		download = download_tool(client=client, url=url, path=path, size=size, resuming=resuming)
		checked = 0
		while checked < 10:
			download1(download, path)
			if download.finished():
				break
			else:
				checked += 1
		assert os.path.getsize(path) == size, 'incorrect downloaded file size (%s != %s)' % (os.path.getsize(path), size)

	def download2(client, url, path, task):
		size = task['size']
		if mini_hash and resuming and verify_mini_hash(path, task):
			return
		download1_checked(client, url, path, size)
		verify = verify_basic_hash if no_hash else verify_hash
		if not verify(path, task):
			with colors(options.get('colors')).yellow():
				print 'hash error, redownloading...'
			os.rename(path, path + '.error')
			download1_checked(client, url, path, size)
			if not verify(path, task):
				raise Exception('hash check failed')

	download2(client, url, path, task)


def download_single_task(client, task, options):
	output = options.get('output')
	output = output and os.path.expanduser(output)
	output_dir = options.get('output_dir')
	output_dir = output_dir and os.path.expanduser(output_dir)
	delete = options.get('delete')
	resuming = options.get('resuming')
	overwrite = options.get('overwrite')
	mini_hash = options.get('mini_hash')
	no_hash = options.get('no_hash')
	no_bt_dir = options.get('no_bt_dir')
	save_torrent_file = options.get('save_torrent_file')

	assert client.get_gdriveid()
	if task['status_text'] != 'completed':
		if 'files' not in task:
			with colors(options.get('colors')).yellow():
				print 'skip task %s as the status is %s' % (task['name'].encode(default_encoding), task['status_text'])
			return

	if output:
		output_path = output
		output_dir = os.path.dirname(output)
		output_name = os.path.basename(output)
	else:
		output_name = safe_encode_native_path(escape_filename(task['name']))
		output_dir = output_dir or '.'
		output_path = os.path.join(output_dir, output_name)

	if task['type'] == 'bt':
		files, skipped, single_file = lixian_query.expand_bt_sub_tasks(task)
		if single_file:
			dirname = output_dir
		else:
			if no_bt_dir:
				output_path = os.path.dirname(output_path)
			dirname = output_path
		assert dirname # dirname must be non-empty, otherwise dirname + os.path.sep + ... might be dangerous
		ensure_dir_exists(dirname)
		for t in skipped:
			with colors(options.get('colors')).yellow():
				print 'skip task %s/%s (%s) as the status is %s' % (str(t['id']), t['index'], t['name'].encode(default_encoding), t['status_text'])
		if mini_hash and resuming and verify_mini_bt_hash(dirname, files):
			print task['name'].encode(default_encoding), 'is already done'
			if delete and 'files' not in task:
				client.delete_task(task)
			return
		if not single_file:
			with colors(options.get('colors')).green():
				print output_name + '/'
		for f in files:
			name = f['name']
			if f['status_text'] != 'completed':
				print 'Skipped %s file %s ...' % (f['status_text'], name.encode(default_encoding))
				continue
			if not single_file:
				print name.encode(default_encoding), '...'
			else:
				with colors(options.get('colors')).green():
					print name.encode(default_encoding), '...'
			# XXX: if file name is escaped, hashing bt won't get correct file
			splitted_path = map(escape_filename, name.split('\\'))
			name = safe_encode_native_path(os.path.join(*splitted_path))
			path = dirname + os.path.sep + name # fix issue #82
			if splitted_path[:-1]:
				subdir = safe_encode_native_path(os.path.join(*splitted_path[:-1]))
				subdir = dirname + os.path.sep + subdir # fix issue #82
				ensure_dir_exists(subdir)
			download_file(client, path, f, options)
		if save_torrent_file:
			info_hash = str(task['bt_hash'])
			if single_file:
				torrent = os.path.join(dirname, escape_filename(task['name']).encode(default_encoding) + '.torrent')
			else:
				torrent = os.path.join(dirname, info_hash + '.torrent')
			if os.path.exists(torrent):
				pass
			else:
				content = client.get_torrent_file_by_info_hash(info_hash)
				with open(torrent, 'wb') as ouput_stream:
					ouput_stream.write(content)
		if not no_hash:
			torrent_file = client.get_torrent_file(task)
			print 'Hashing bt ...'
			from lixian_progress import SimpleProgressBar
			bar = SimpleProgressBar()
			file_set = [f['name'].encode('utf-8').split('\\') for f in files] if 'files' in task else None
			verified = lixian_hash_bt.verify_bt(output_path, lixian_hash_bt.bdecode(torrent_file)['info'], file_set=file_set, progress_callback=bar.update)
			bar.done()
			if not verified:
				# note that we don't delete bt download folder if hash failed
				raise Exception('bt hash check failed')
	else:
		ensure_dir_exists(output_dir)

		with colors(options.get('colors')).green():
			print output_name, '...'
		download_file(client, output_path, task, options)

	if delete and 'files' not in task:
		client.delete_task(task)

def download_multiple_tasks(client, tasks, options):
	for task in tasks:
		download_single_task(client, task, options)
	skipped = filter(lambda t: t['status_text'] != 'completed', tasks)
	if skipped:
		with colors(options.get('colors')).yellow():
			print "Below tasks were skipped as they were not ready:"
		for task in skipped:
			print task['id'], task['status_text'], task['name'].encode(default_encoding)

@command_line_parser(help=lixian_help.download)
@with_parser(parse_login)
@with_parser(parse_colors)
@with_parser(parse_logging)
@command_line_value('tool', default=get_config('tool', 'wget'))
@command_line_value('input', alias='i')
@command_line_value('output', alias='o')
@command_line_value('output-dir', default=get_config('output-dir'))
@command_line_option('torrent', alias='bt')
@command_line_option('all')
@command_line_value('category')
@command_line_value('limit', default=get_config('limit'))
@command_line_value('page-size', default=get_config('page-size'))
@command_line_option('delete', default=get_config('delete'))
@command_line_option('continue', alias='c', default=get_config('continue'))
@command_line_option('overwrite')
@command_line_option('mini-hash', default=get_config('mini-hash'))
@command_line_option('hash', default=get_config('hash', True))
@command_line_option('bt-dir', default=True)
@command_line_option('save-torrent-file')
@command_line_option('watch')
@command_line_option('watch-present')
@command_line_value('watch-interval', default=get_config('watch-interval', '3m'))
@command_line_value('node', default=get_config('node'))
@command_line_value('node-detection-threshold', default=get_config('node-detection-threshold', '100M'))
@command_line_value('node-detection-acceptable', default=get_config('node-detection-acceptable', '1M'))
@command_line_value('vod-nodes', default=get_config('vod-nodes', lixian_nodes.VOD_RANGE))
def download_task(args):
	assert len(args) or args.input or args.all or args.category, 'Not enough arguments'
	lixian_download_tools.get_tool(args.tool) # check tool
	download_args = {'tool': args.tool,
	                 'output': args.output,
	                 'output_dir': args.output_dir,
	                 'delete': args.delete,
	                 'resuming': args._args['continue'],
	                 'overwrite': args.overwrite,
	                 'mini_hash': args.mini_hash,
	                 'no_hash': not args.hash,
	                 'no_bt_dir': not args.bt_dir,
	                 'save_torrent_file': args.save_torrent_file,
	                 'node': args.node,
	                 'node_detection_threshold': args.node_detection_threshold,
	                 'node_detection_acceptable': args.node_detection_acceptable,
	                 'vod_nodes': args.vod_nodes,
	                 'colors': args.colors}
	client = create_client(args)
	query = lixian_query.build_query(client, args)
	query.query_once()

	def sleep(n):
		assert isinstance(n, (int, basestring)), repr(n)
		import time
		if isinstance(n, basestring):
			n, u = re.match(r'^(\d+)([smh])?$', n.lower()).groups()
			n = int(n) * {None: 1, 's': 1, 'm': 60, 'h': 3600}[u]
		time.sleep(n)

	if args.watch_present:
		assert not args.output, 'not supported with watch option yet'
		tasks = query.pull_completed()
		while True:
			if tasks:
				download_multiple_tasks(client, tasks, download_args)
			if not query.download_jobs:
				break
			if not tasks:
				sleep(args.watch_interval)
			query.refresh_status()
			tasks = query.pull_completed()

	elif args.watch:
		assert not args.output, 'not supported with watch option yet'
		tasks = query.pull_completed()
		while True:
			if tasks:
				download_multiple_tasks(client, tasks, download_args)
			if (not query.download_jobs) and (not query.queries):
				break
			if not tasks:
				sleep(args.watch_interval)
			query.refresh_status()
			query.query_search()
			tasks = query.pull_completed()

	else:
		tasks = query.peek_download_jobs()
		if args.output:
			assert len(tasks) == 1
			download_single_task(client, tasks[0], download_args)
		else:
			download_multiple_tasks(client, tasks, download_args)

########NEW FILE########
__FILENAME__ = help

from lixian_commands.util import *
import lixian_help

def lx_help(args):
	if len(args) == 1:
		helper = getattr(lixian_help, args[0].lower(), lixian_help.help)
		usage(helper)
	elif len(args) == 0:
		usage(lixian_help.welcome_help)
	else:
		usage(lixian_help.help)

########NEW FILE########
__FILENAME__ = info


from lixian import XunleiClient
from lixian_commands.util import *
from lixian_cli_parser import *
import lixian_help

@command_line_parser(help=lixian_help.info)
@with_parser(parse_login)
@command_line_option('id', alias='i')
def lixian_info(args):
	client = XunleiClient(args.username, args.password, args.cookies, login=False)
	if args.id:
		print client.get_username()
	else:
		print 'id:', client.get_username()
		print 'internalid:', client.get_userid()
		print 'gdriveid:', client.get_gdriveid() or ''


########NEW FILE########
__FILENAME__ = list

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import get_config
import lixian_help
import lixian_query
import re

@command_line_parser(help=lixian_help.list)
@with_parser(parse_login)
@with_parser(parse_colors)
@with_parser(parse_logging)
@with_parser(parse_size)
@command_line_option('all', default=True)
@command_line_option('completed')
@command_line_option('failed')
@command_line_option('deleted')
@command_line_option('expired')
@command_line_value('category')
@command_line_value('limit', default=get_config('limit'))
@command_line_value('page-size', default=get_config('page-size'))
@command_line_option('id', default=get_config('id', True))
@command_line_option('name', default=True)
@command_line_option('status', default=True)
@command_line_option('dcid')
@command_line_option('gcid')
@command_line_option('original-url')
@command_line_option('download-url')
@command_line_option('speed')
@command_line_option('progress')
@command_line_option('date')
@command_line_option('n', default=get_config('n'))
def list_task(args):

	parent_ids = [a[:-1] for a in args if re.match(r'^#?\d+/$', a)]
	if parent_ids and not all(re.match(r'^#?\d+/$', a) for a in args):
		raise NotImplementedError("Can't mix 'id/' with others")
	assert len(parent_ids) <= 1, "sub-tasks listing only supports single task id"
	ids = [a[:-1] if re.match(r'^#?\d+/$', a) else a for a in args]

	client = create_client(args)
	if parent_ids:
		args[0] = args[0][:-1]
		tasks = lixian_query.search_tasks(client, args)
		assert len(tasks) == 1
		tasks = client.list_bt(tasks[0])
		#tasks = client.list_bt(client.get_task_by_id(parent_ids[0]))
		tasks.sort(key=lambda x: int(x['index']))
	else:
		tasks = lixian_query.search_tasks(client, args)
		if len(args) == 1 and re.match(r'\d+/', args[0]) and len(tasks) == 1 and 'files' in tasks[0]:
			parent_ids = [tasks[0]['id']]
			tasks = tasks[0]['files']
	columns = ['n', 'id', 'name', 'status', 'size', 'progress', 'speed', 'date', 'dcid', 'gcid', 'original-url', 'download-url']
	columns = filter(lambda k: getattr(args, k), columns)

	output_tasks(tasks, columns, args, not parent_ids)

########NEW FILE########
__FILENAME__ = login


from lixian import XunleiClient
from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import get_config
import lixian_help
from getpass import getpass

@command_line_parser(help=lixian_help.login)
@with_parser(parse_login)
@with_parser(parse_logging)
def login(args):
	if args.cookies == '-':
		args._args['cookies'] = None
	if len(args) < 1:
		args.username = args.username or XunleiClient(cookie_path=args.cookies, login=False).get_username() or get_config('username') or raw_input('ID: ')
		args.password = args.password or get_config('password') or getpass('Password: ')
	elif len(args) == 1:
		args.username = args.username or XunleiClient(cookie_path=args.cookies, login=False).get_username() or get_config('username')
		args.password = args[0]
		if args.password == '-':
			args.password = getpass('Password: ')
	elif len(args) == 2:
		args.username, args.password = list(args)
		if args.password == '-':
			args.password = getpass('Password: ')
	elif len(args) == 3:
		args.username, args.password, args.cookies = list(args)
		if args.password == '-':
			args.password = getpass('Password: ')
	elif len(args) > 3:
		raise RuntimeError('Too many arguments')
	if not args.username:
		raise RuntimeError("What's your name?")
	if args.cookies:
		print 'Saving login session to', args.cookies
	else:
		print 'Testing login without saving session'
	import lixian_verification_code
	verification_code_reader = lixian_verification_code.default_verification_code_reader(args)
	XunleiClient(args.username, args.password, args.cookies, login=True, verification_code_reader=verification_code_reader)

########NEW FILE########
__FILENAME__ = logout

from lixian import XunleiClient
from lixian_commands.util import *
from lixian_cli_parser import *
import lixian_config
import lixian_help

@command_line_parser(help=lixian_help.logout)
@with_parser(parse_logging)
@command_line_value('cookies', default=lixian_config.LIXIAN_DEFAULT_COOKIES)
def logout(args):
	if len(args):
		raise RuntimeError('Too many arguments')
	print 'logging out from', args.cookies
	assert args.cookies
	client = XunleiClient(cookie_path=args.cookies, login=False)
	client.logout()


########NEW FILE########
__FILENAME__ = pause

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import get_config
from lixian_encoding import default_encoding
import lixian_help
import lixian_query

@command_line_parser(help=lixian_help.pause)
@with_parser(parse_login)
@with_parser(parse_colors)
@with_parser(parse_logging)
@command_line_option('i')
@command_line_option('all')
@command_line_value('limit', default=get_config('limit'))
@command_line_value('page-size', default=get_config('page-size'))
def pause_task(args):
	client = create_client(args)
	to_pause = lixian_query.search_tasks(client, args)
	print "Below files are going to be paused:"
	for x in to_pause:
		print x['name'].encode(default_encoding)
	client.pause_tasks(to_pause)

########NEW FILE########
__FILENAME__ = readd

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_encoding import default_encoding
import lixian_help
import lixian_query

@command_line_parser(help=lixian_help.readd)
@with_parser(parse_login)
@with_parser(parse_logging)
@command_line_option('deleted')
@command_line_option('expired')
@command_line_option('all')
def readd_task(args):
	if args.deleted:
		status = 'deleted'
	elif args.expired:
		status = 'expired'
	else:
		raise NotImplementedError('Please use --expired or --deleted')
	client = create_client(args)
	if status == 'expired' and args.all:
		return client.readd_all_expired_tasks()
	to_readd = lixian_query.search_tasks(client, args)
	non_bt = []
	bt = []
	if not to_readd:
		return
	print "Below files are going to be re-added:"
	for x in to_readd:
		print x['name'].encode(default_encoding)
		if x['type'] == 'bt':
			bt.append((x['bt_hash'], x['id']))
		else:
			non_bt.append((x['original_url'], x['id']))
	if non_bt:
		urls, ids = zip(*non_bt)
		client.add_batch_tasks(urls, ids)
	for hash, id in bt:
		client.add_torrent_task_by_info_hash2(hash, id)

########NEW FILE########
__FILENAME__ = rename

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_encoding import from_native
import lixian_help
import re
import sys

@command_line_parser(help=lixian_help.rename)
@with_parser(parse_login)
@with_parser(parse_logging)
def rename_task(args):
	if len(args) != 2 or not re.match(r'\d+$', args[0]):
		usage(lixian_help.rename, 'Incorrect arguments')
		sys.exit(1)
	client = create_client(args)
	taskid, new_name = args
	task = client.get_task_by_id(taskid)
	client.rename_task(task, from_native(new_name))

########NEW FILE########
__FILENAME__ = restart

from lixian_commands.util import *
from lixian_cli_parser import *
from lixian_config import get_config
from lixian_encoding import default_encoding
import lixian_help
import lixian_query

@command_line_parser(help=lixian_help.restart)
@with_parser(parse_login)
@with_parser(parse_colors)
@with_parser(parse_logging)
@command_line_option('i')
@command_line_option('all')
@command_line_value('limit', default=get_config('limit'))
@command_line_value('page-size', default=get_config('page-size'))
def restart_task(args):
	client = create_client(args)
	to_restart = lixian_query.search_tasks(client, args)
	print "Below files are going to be restarted:"
	for x in to_restart:
		print x['name'].encode(default_encoding)
	client.restart_tasks(to_restart)

########NEW FILE########
__FILENAME__ = util

__all__ = ['parse_login', 'parse_colors', 'parse_logging', 'parse_size', 'create_client', 'output_tasks', 'usage']

from lixian_cli_parser import *
from lixian_config import get_config
from lixian_config import LIXIAN_DEFAULT_COOKIES
from lixian_encoding import default_encoding, to_native
from lixian_colors import colors
from getpass import getpass
import lixian_help

@command_line_value('username', default=get_config('username'))
@command_line_value('password', default=get_config('password'))
@command_line_value('cookies', default=LIXIAN_DEFAULT_COOKIES)
@command_line_value('verification-code-path', default=get_config('verification-code-path'))
def parse_login(args):
	if args.password == '-':
		args.password = getpass('Password: ')
	if args.cookies == '-':
		args._args['cookies'] = None
	return args

@command_line_option('colors', default=get_config('colors', True))
def parse_colors(args):
	pass

@command_line_value('log-level', default=get_config('log-level'))
@command_line_value('log-path', default=get_config('log-path'))
@command_line_option('debug')
@command_line_option('trace')
def parse_logging(args):
	path = args.log_path
	level = args.log_level
	if args.trace:
		level = 'trace'
	elif args.debug:
		level = 'debug'
	if path or level:
		import lixian_logging
		level = level or 'info'
		lixian_logging.init_logger(use_colors=args.colors, level=level, path=path)
		logger = lixian_logging.get_logger()
		import lixian
		# inject logger to lixian (this makes lixian.py zero-dependency)
		lixian.logger = logger

@command_line_option('size', default=get_config('size'))
@command_line_option('format-size', default=get_config('format-size'))
def parse_size(args):
	pass

def create_client(args):
	from lixian import XunleiClient
	import lixian_verification_code
	verification_code_reader = lixian_verification_code.default_verification_code_reader(args)
	client = XunleiClient(args.username, args.password, args.cookies, verification_code_reader=verification_code_reader)
	if args.page_size:
		client.page_size = int(args.page_size)
	return client

def output_tasks(tasks, columns, args, top=True):
	for i, t in enumerate(tasks):
		status_colors = {
		'waiting': 'yellow',
		'downloading': 'magenta',
		'completed':'green',
		'pending':'cyan',
		'failed':'red',
		}
		c = status_colors[t['status_text']]
		with colors(args.colors).ansi(c)():
			for k in columns:
				if k == 'n':
					if top:
						print '#%d' % t['#'],
				elif k == 'id':
					print t.get('index', t['id']),
				elif k == 'name':
					print t['name'].encode(default_encoding),
				elif k == 'status':
					with colors(args.colors).bold():
						print t['status_text'],
				elif k == 'size':
					if args.format_size:
						from lixian_util import format_size
						print format_size(t['size']),
					else:
						print t['size'],
				elif k == 'progress':
					print t['progress'],
				elif k == 'speed':
					print t['speed'],
				elif k == 'date':
					print t['date'],
				elif k == 'dcid':
					print t['dcid'],
				elif k == 'gcid':
					print t['gcid'],
				elif k == 'original-url':
					print t['original_url'],
				elif k == 'download-url':
					print t['xunlei_url'],
				else:
					raise NotImplementedError(k)
			print

def usage(doc=lixian_help.usage, message=None):
	if hasattr(doc, '__call__'):
		doc = doc()
	if message:
		print to_native(message)
	print to_native(doc).strip()

########NEW FILE########
__FILENAME__ = lixian_config

import os
import os.path

def get_config_path(filename):
	if os.path.exists(filename):
		return filename
	import sys
	local_path = os.path.join(sys.path[0], filename)
	if os.path.exists(local_path):
		return local_path
	user_home = os.getenv('USERPROFILE') or os.getenv('HOME')
	lixian_home = os.getenv('LIXIAN_HOME') or user_home
	return os.path.join(lixian_home, filename)

LIXIAN_DEFAULT_CONFIG = get_config_path('.xunlei.lixian.config')
LIXIAN_DEFAULT_COOKIES = get_config_path('.xunlei.lixian.cookies')

def load_config(path):
	values = {}
	if os.path.exists(path):
		with open(path) as x:
			for line in x.readlines():
				line = line.strip()
				if line:
					if line.startswith('--'):
						line = line.lstrip('-')
						if line.startswith('no-'):
							values[line[3:]] = False
						elif '=' in line:
							k, v = line.split('=', 1)
							values[k] = v
						else:
							values[line] = True
					else:
						raise NotImplementedError(line)
	return values

def dump_config(path, values):
	with open(path, 'w') as x:
		for k in values:
			v = values[k]
			if v is True:
				x.write('--%s\n'%k)
			elif v is False:
				x.write('--no-%s\n'%k)
			else:
				x.write('--%s=%s\n'%(k, v))

class Config:
	def __init__(self, path=LIXIAN_DEFAULT_CONFIG):
		self.path = path
		self.values = load_config(path)
	def put(self, k, v=True):
		self.values[k] = v
		dump_config(self.path, self.values)
	def get(self, k, v=None):
		return self.values.get(k, v)
	def delete(self, k):
		if k in self.values:
			del self.values[k]
			dump_config(self.path, self.values)
	def source(self):
		if os.path.exists(self.path):
			with open(self.path) as x:
				return x.read()
	def __str__(self):
		return '<Config{%s}>' % self.values

global_config = Config()

def put_config(k, v=True):
	if k.startswith('no-') and v is True:
		k = k[3:]
		v = False
	global_config.put(k, v)

def get_config(k, v=None):
	return global_config.get(k, v)

def delete_config(k):
	return global_config.delete(k)

def source_config():
	return global_config.source()


########NEW FILE########
__FILENAME__ = lixian_download_asyn

import asyncore
import asynchat
import socket
import re
#from cStringIO import StringIO
from time import time, sleep
import sys
import os

#asynchat.async_chat.ac_out_buffer_size = 1024*1024

class http_client(asynchat.async_chat):

	def __init__(self, url, headers=None, start_from=0):
		asynchat.async_chat.__init__(self)

		self.args = {'headers': headers, 'start_from': start_from}

		m = re.match(r'http://([^/:]+)(?::(\d+))?(/.*)?$', url)
		assert m, 'Invalid url: %s' % url
		host, port, path = m.groups()
		port = int(port or 80)
		path = path or '/'

		def resolve_host(host):
			try:
				return socket.gethostbyname(host)
			except:
				pass
		host_ip = resolve_host(host)
		if not host_ip:
			self.log_error("host can't be resolved: " + host)
			self.size = None
			return
		if host_ip == '180.168.41.175':
			# fuck shanghai dian DNS
			self.log_error('gethostbyname failed')
			self.size = None
			return


		request_headers = {'host': host, 'connection': 'close'}
		if start_from:
			request_headers['RANGE'] = 'bytes=%d-' % start_from
		if headers:
			request_headers.update(headers)
		headers = request_headers
		self.request = 'GET %s HTTP/1.1\r\n%s\r\n\r\n' % (path, '\r\n'.join('%s: %s' % (k, headers[k]) for k in headers))
		self.op = 'GET'

		self.headers = {} # for response headers

		#self.buffer = StringIO()
		self.buffer = []
		self.buffer_size = 0
		self.cache_size = 1024*1024
		self.size = None
		self.completed = 0
		self.set_terminator("\r\n\r\n")
		self.reading_headers = True

		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.connect((host, port))
		except:
			self.close()
			self.log_error('connect_failed')

	def handle_connect(self):
		self.start_time = time()
		self.push(self.request)

	def handle_close(self):
		asynchat.async_chat.handle_close(self)
		self.flush_data()
		if self.reading_headers:
			self.log_error('incomplete http response')
			return
		self.handle_status_update(self.size, self.completed, force_update=True)
		self.handle_speed_update(self.completed, self.start_time, force_update=True)
		if self.size is not None and self.completed < self.size:
			self.log_error('incomplete download')

	def handle_connection_error(self):
		self.handle_error()

	def handle_error(self):
		self.close()
		self.flush_data()
		error_message = sys.exc_info()[1]
		self.log_error('there is some error: %s' % error_message)
		#raise

	def collect_incoming_data(self, data):
		if self.reading_headers:
			#self.buffer.write(data)
			self.buffer.append(data)
			self.buffer_size += len(data)
			return
		elif self.cache_size:
			#self.buffer.write(data)
			self.buffer.append(data)
			self.buffer_size += len(data)
			#if self.buffer.tell() > self.cache_size:
			if self.buffer_size > self.cache_size:
				#self.handle_data(self.buffer.getvalue())
				self.handle_data(''.join(self.buffer))
				#self.buffer.truncate(0)
				#self.buffer.clear()
				del self.buffer[:]
				self.buffer_size = 0
		else:
			self.handle_data(data)

		self.completed += len(data)
		self.handle_status_update(self.size, self.completed)
		self.handle_speed_update(self.completed, self.start_time)
		if self.size == self.completed:
			self.close()
			self.flush_data()
			self.handle_status_update(self.size, self.completed, force_update=True)
			self.handle_speed_update(self.completed, self.start_time, force_update=True)

	def handle_data(self, data):
		print len(data)
		pass

	def flush_data(self):
		#if self.buffer.tell():
		if self.buffer_size:
			#self.handle_data(self.buffer.getvalue())
			self.handle_data(''.join(self.buffer))
			#self.buffer.truncate(0)
			del self.buffer[:]
			self.buffer_size = 0

	def parse_headers(self, header):
		lines = header.split('\r\n')
		status_line = lines.pop(0)
		#print status_line
		protocal, status_code, status_text = re.match(r'^HTTP/([\d.]+) (\d+) (.+)$', status_line).groups()
		status_code = int(status_code)
		self.status_code = status_code
		self.status_text = status_text
		#headers = dict(h.split(': ', 1) for h in lines)
		for k, v in (h.split(': ', 1) for h in lines):
			self.headers[k.lower()] = v

		if status_code in (200, 206):
			pass
		elif status_code == 302:
			return self.handle_http_relocate(self.headers['location'])
		else:
			return self.handle_http_status_error()

		self.size = self.headers.get('content-length', None)
		if self.size is not None:
			self.size = int(self.size)
		self.handle_http_headers()

	def found_terminator(self):
		if self.reading_headers:
			self.reading_headers = False
			#self.parse_headers("".join(self.buffer.getvalue()))
			self.parse_headers("".join(self.buffer))
			#self.buffer.truncate(0)
			del self.buffer[:]
			self.buffer_size = 0
			self.set_terminator(None)
		else:
			raise NotImplementedError()

	def handle_http_headers(self):
		pass

	def handle_http_status_error(self):
		self.close()

	def handle_http_relocate(self, location):
		self.close()
		relocate_times = getattr(self, 'relocate_times', 0)
		max_relocate_times = getattr(self, 'max_relocate_times', 2)
		if relocate_times >= max_relocate_times:
			raise Exception('too many relocate times')
		new_client = self.__class__(location, **self.args)
		new_client.relocate_times = relocate_times + 1
		new_client.max_relocate_times = max_relocate_times
		self.next_client = new_client

	def handle_status_update(self, total, completed, force_update=False):
		pass

	def handle_speed_update(self, completed, start_time, force_update=False):
		pass

	def log_error(self, message):
		print 'log_error', message
		self.error_message = message

class ProgressBar:
	def __init__(self, total=0):
		self.total = total
		self.completed = 0
		self.start = time()
		self.speed = 0
		self.bar_width = 0
		self.displayed = False
	def update(self):
		self.displayed = True
		bar_size = 40
		if self.total:
			percent = self.completed * 100.0 / self.total
			if percent > 100:
				percent = 100.0
			dots = int(bar_size * percent / 100)
			plus = percent / 100 * bar_size - dots
			if plus > 0.8:
				plus = '='
			elif plus > 0.4:
				plus = '-'
			else:
				plus = ''
			bar = '=' * dots + plus
			percent = int(percent)
		else:
			percent = 0
			bar = '-'
		speed = self.speed
		if speed < 1000:
			speed = '%sB/s' % int(speed)
		elif speed < 1000*10:
			speed = '%.1fK/s' % (speed/1000.0)
		elif speed < 1000*1000:
			speed = '%dK/s' % int(speed/1000)
		elif speed < 1000*1000*100:
			speed = '%.1fM/s' % (speed/1000.0/1000.0)
		else:
			speed = '%dM/s' % int(speed/1000/1000)
		seconds = time() - self.start
		if seconds < 10:
			seconds = '%.1fs' % seconds
		elif seconds < 60:
			seconds = '%ds' % int(seconds)
		elif seconds < 60*60:
			seconds = '%dm%ds' % (int(seconds/60), int(seconds)%60)
		elif seconds < 60*60*24:
			seconds = '%dh%dm%ds' % (int(seconds)/60/60, (int(seconds)/60)%60, int(seconds)%60)
		else:
			seconds = int(seconds)
			days = seconds/60/60/24
			seconds -= days*60*60*24
			hours = seconds/60/60
			seconds -= hours*60*60
			minutes = seconds/60
			seconds -= minutes*60
			seconds = '%dd%dh%dm%ds' % (days, hours, minutes, seconds)
		completed = ','.join((x[::-1] for x in reversed(re.findall('..?.?', str(self.completed)[::-1]))))
		bar = '{0:>3}%[{1:<40}] {2:<12} {3:>4} in {4:>6s}'.format(percent, bar, completed, speed, seconds)
		new_bar_width = len(bar)
		bar = bar.ljust(self.bar_width)
		self.bar_width = new_bar_width
		sys.stdout.write('\r'+bar)
		sys.stdout.flush()
	def update_status(self, total, completed):
		self.total = total
		self.completed = completed
		self.update()
	def update_speed(self, start, speed):
		self.start = start
		self.speed = speed
		self.update()
	def done(self):
		if self.displayed:
			print
			self.displayed = False

def download(url, path, headers=None, resuming=False):
	class download_client(http_client):
		def __init__(self, url, headers=headers, start_from=0):
			self.output = None
			self.bar = ProgressBar()
			http_client.__init__(self, url, headers=headers, start_from=start_from)
			self.start_from = start_from
			self.last_status_time = time()
			self.last_speed_time = time()
			self.last_size = 0
			self.path = path
		def handle_close(self):
			http_client.handle_close(self)
			if self.output:
				self.output.close()
				self.output = None
		def handle_http_status_error(self):
			http_client.handle_http_status_error(self)
			self.log_error('http status error: %s, %s' % (self.status_code, self.status_text))
		def handle_data(self, data):
			if not self.output:
				if self.start_from:
					self.output = open(path, 'ab')
				else:
					self.output = open(path, 'wb')
			self.output.write(data)
		def handle_status_update(self, total, completed, force_update=False):
			if total is None:
				return
			if time() - self.last_status_time > 1 or force_update:
				#print '%.02f' % (completed*100.0/total)
				self.bar.update_status(total+start_from, completed+start_from)
				self.last_status_time = time()
		def handle_speed_update(self, completed, start_time, force_update=False):
			now = time()
			period = now - self.last_speed_time
			if period > 1 or force_update:
				#print '%.02f, %.02f' % ((completed-self.last_size)/period, completed/(now-start_time))
				self.bar.update_speed(start_time, (completed-self.last_size)/period)
				self.last_speed_time = time()
				self.last_size = completed
		def log_error(self, message):
			self.bar.done()
			http_client.log_error(self, message)
		def __del__(self): # XXX: sometimes handle_close() is not called, don't know why...
			#http_client.__del__(self)
			if self.output:
				self.output.close()
				self.output = None
	
	max_retry_times = 25
	retry_times = 0
	start_from = 0
	if resuming and os.path.exists(path):
		start_from = os.path.getsize(path)
		# TODO: fix status bar for resuming
	while True:
		client = download_client(url, start_from=start_from)
		asyncore.loop()
		while hasattr(client, 'next_client'):
			client = client.next_client
		client.bar.done()
		if getattr(client, 'error_message', None):
			retry_times += 1
			if retry_times >= max_retry_times:
				raise Exception(client.error_message)
			if client.size and client.completed:
				start_from = os.path.getsize(path)
			print 'retry', retry_times
			sleep(retry_times)
		else:
			break


def main():
	url, path = sys.argv[1:]
	download(url, path)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = lixian_download_tools

__all__ = ['download_tool', 'get_tool']

from lixian_config import *
import subprocess
import urllib2
import os.path

download_tools = {}

def download_tool(name):
	def register(tool):
		download_tools[name] = tool_adaptor(tool)
		return tool
	return register

class DownloadToolAdaptor:
	def __init__(self, tool, **kwargs):
		self.tool = tool
		self.client = kwargs['client']
		self.url = kwargs['url']
		self.path = kwargs['path']
		self.resuming = kwargs.get('resuming')
		self.size = kwargs['size']
	def finished(self):
		assert os.path.getsize(self.path) <= self.size, 'existing file (%s) bigger than expected (%s)' % (os.path.getsize(self.path), self.size)
		return os.path.getsize(self.path) == self.size
	def __call__(self):
		self.tool(self.client, self.url, self.path, self.resuming)

def tool_adaptor(tool):
	import types
	if type(tool) == types.FunctionType:
		def adaptor(**kwargs):
			return DownloadToolAdaptor(tool, **kwargs)
		return adaptor
	else:
		return tool


def check_bin(bin):
	import distutils.spawn
	assert distutils.spawn.find_executable(bin), "Can't find %s" % bin

@download_tool('urllib2')
def urllib2_download(client, download_url, filename, resuming=False):
	'''In the case you don't even have wget...'''
	assert not resuming
	print 'Downloading', download_url, 'to', filename, '...'
	request = urllib2.Request(download_url, headers={'Cookie': 'gdriveid='+client.get_gdriveid()})
	response = urllib2.urlopen(request)
	import shutil
	with open(filename, 'wb') as output:
		shutil.copyfileobj(response, output)

@download_tool('asyn')
def asyn_download(client, download_url, filename, resuming=False):
	import lixian_download_asyn
	lixian_download_asyn.download(download_url, filename, headers={'Cookie': 'gdriveid='+str(client.get_gdriveid())}, resuming=resuming)

@download_tool('wget')
def wget_download(client, download_url, filename, resuming=False):
	gdriveid = str(client.get_gdriveid())
	wget_opts = ['wget', '--header=Cookie: gdriveid='+gdriveid, download_url, '-O', filename]
	if resuming:
		wget_opts.append('-c')
	wget_opts.extend(get_config('wget-opts', '').split())
	check_bin(wget_opts[0])
	exit_code = subprocess.call(wget_opts)
	if exit_code != 0:
		raise Exception('wget exited abnormally')

@download_tool('curl')
def curl_download(client, download_url, filename, resuming=False):
	gdriveid = str(client.get_gdriveid())
	curl_opts = ['curl', '-L', download_url, '--cookie', 'gdriveid='+gdriveid, '--output', filename]
	if resuming:
		curl_opts += ['--continue-at', '-']
	curl_opts.extend(get_config('curl-opts', '').split())
	check_bin(curl_opts[0])
	exit_code = subprocess.call(curl_opts)
	if exit_code != 0:
		raise Exception('curl exited abnormally')

@download_tool('aria2')
@download_tool('aria2c')
class Aria2DownloadTool:
	def __init__(self, **kwargs):
		self.gdriveid = str(kwargs['client'].get_gdriveid())
		self.url = kwargs['url']
		self.path = kwargs['path']
		self.size = kwargs['size']
		self.resuming = kwargs.get('resuming')
	def finished(self):
		assert os.path.getsize(self.path) <= self.size, 'existing file (%s) bigger than expected (%s)' % (os.path.getsize(self.path), self.size)
		return os.path.getsize(self.path) == self.size and not os.path.exists(self.path + '.aria2')
	def __call__(self):
		gdriveid = self.gdriveid
		download_url = self.url
		path = self.path
		resuming = self.resuming
		dir = os.path.dirname(path)
		filename = os.path.basename(path)
		aria2_opts = ['aria2c', '--header=Cookie: gdriveid='+gdriveid, download_url, '--out', filename, '--file-allocation=none']
		if dir:
			aria2_opts.extend(('--dir', dir))
		if resuming:
			aria2_opts.append('-c')
		aria2_opts.extend(get_config('aria2-opts', '').split())
		check_bin(aria2_opts[0])
		exit_code = subprocess.call(aria2_opts)
		if exit_code != 0:
			raise Exception('aria2c exited abnormally')

@download_tool('axel')
def axel_download(client, download_url, path, resuming=False):
	gdriveid = str(client.get_gdriveid())
	axel_opts = ['axel', '--header=Cookie: gdriveid='+gdriveid, download_url, '--output', path]
	axel_opts.extend(get_config('axel-opts', '').split())
	check_bin(axel_opts[0])
	exit_code = subprocess.call(axel_opts)
	if exit_code != 0:
		raise Exception('axel exited abnormally')

def get_tool(name):
	return download_tools[name]



########NEW FILE########
__FILENAME__ = lixian_encoding

from lixian_config import get_config
import sys

default_encoding = get_config('encoding', sys.getfilesystemencoding())
if default_encoding is None or default_encoding.lower() == 'ascii':
	default_encoding = 'utf-8'


def to_native(s):
	if type(s) == unicode:
		return s.encode(default_encoding)
	else:
		return s

def from_native(s):
	if type(s) == str:
		return s.decode(default_encoding)
	else:
		return s

def try_native_to_utf_8(url):
	try:
		return url.decode(default_encoding).encode('utf-8')
	except:
		return url


########NEW FILE########
__FILENAME__ = lixian_filter_expr

__all__ = ['filter_expr']

import re

def get_name(x):
	assert isinstance(x, (basestring, dict))
	if type(x) == dict:
		return x['name']
	else:
		return x

def filter_expr1(links, p):
	if not links:
		return links
	if re.match(r'^\[[^][]+\]$', p):
		matched = []
		for p in re.split(r'\s*,\s*', p[1:-1]):
			assert re.match(r'^\d+(-\d+)?|\.\w+$', p), p
			if re.match(r'^\d+$', p):
				i = int(p)
				matched.append((i, links[i]))
			elif '-' in p:
				start, end = p.split('-')
				if not start:
					start = 0
				if not end:
					end = len(links) - 1
				start = int(start)
				end = int(end)
				assert 0 <= start < len(links)
				assert 0 <= end < len(links)
				if start <= end:
					matched += list(enumerate(links))[start:end+1]
				else:
					matched += reversed(list(enumerate(links))[end:start+1])
			elif p.startswith('.'):
				matched += filter(lambda (i, x): get_name(x).lower().endswith(p.lower()), enumerate(links))
			else:
				raise NotImplementedError(p)
		indexes = []
		for i, _ in matched:
			if i not in indexes:
				indexes.append(i)
		return [links[x] for x in indexes]
	elif re.match(r'^\d+$', p):
		n = int(p)
		if 0 <= n < len(links):
			return [links[int(p)]]
		else:
			return filter(lambda x: re.search(p, get_name(x), re.I), links)
	elif p == '*':
		return links
	elif re.match(r'\.\w+$', p):
		return filter(lambda x: get_name(x).lower().endswith(p.lower()), links)
	else:
		import lixian_plugins.filters
		filter_results = lixian_plugins.filters.filter_things(links, p)
		if filter_results is None:
			return filter(lambda x: re.search(p, get_name(x), re.I), links)
		else:
			return filter_results

def filter_expr(links, expr):
	for p in expr.split('/'):
		links = filter_expr1(links, p)
	return links



########NEW FILE########
__FILENAME__ = lixian_hash
#!/usr/bin/env python

import hashlib
import lixian_hash_ed2k
import lixian_hash_bt
import os

def lib_hash_file(h, path):
	with open(path, 'rb') as stream:
		while True:
			bytes = stream.read(1024*1024)
			if not bytes:
				break
			h.update(bytes)
	return h.hexdigest()

def sha1_hash_file(path):
	return lib_hash_file(hashlib.sha1(), path)

def verify_sha1(path, sha1):
	return sha1_hash_file(path).lower() == sha1.lower()

def md5_hash_file(path):
	return lib_hash_file(hashlib.md5(), path)

def verify_md5(path, md5):
	return md5_hash_file(path).lower() == md5.lower()

def md4_hash_file(path):
	return lib_hash_file(hashlib.new('md4'), path)

def verify_md4(path, md4):
	return md4_hash_file(path).lower() == md4.lower()

def dcid_hash_file(path):
	h = hashlib.sha1()
	size = os.path.getsize(path)
	with open(path, 'rb') as stream:
		if size < 0xF000:
			h.update(stream.read())
		else:
			h.update(stream.read(0x5000))
			stream.seek(size/3)
			h.update(stream.read(0x5000))
			stream.seek(size-0x5000)
			h.update(stream.read(0x5000))
	return h.hexdigest()

def verify_dcid(path, dcid):
	return dcid_hash_file(path).lower() == dcid.lower()

def main(args):
	option = args.pop(0)
	def verify_bt(f, t):
		from lixian_progress import SimpleProgressBar
		bar = SimpleProgressBar()
		result = lixian_hash_bt.verify_bt_file(t, f, progress_callback=bar.update)
		bar.done()
		return result
	if option.startswith('--verify'):
		hash_fun = {'--verify-sha1':verify_sha1,
					'--verify-md5':verify_md5,
					'--verify-md4':verify_md4,
					'--verify-dcid':verify_dcid,
					'--verify-ed2k':lixian_hash_ed2k.verify_ed2k_link,
					'--verify-bt': verify_bt,
				   }[option]
		assert len(args) == 2
		hash, path = args
		if hash_fun(path, hash):
			print 'looks good...'
		else:
			print 'failed...'
	else:
		hash_fun = {'--sha1':sha1_hash_file,
					'--md5':md5_hash_file,
					'--md4':md4_hash_file,
					'--dcid':dcid_hash_file,
					'--ed2k':lixian_hash_ed2k.generate_ed2k_link,
					'--info-hash':lixian_hash_bt.info_hash,
				   }[option]
		for f in args:
			h = hash_fun(f)
			print '%s *%s' % (h, f)

if __name__ == '__main__':
	import sys
	args = sys.argv[1:]
	main(args)


########NEW FILE########
__FILENAME__ = lixian_hash_bt

import os.path
import sys
import hashlib
from cStringIO import StringIO
import re

from lixian_encoding import default_encoding

def magnet_to_infohash(magnet):
	import re
	import base64
	m = re.match(r'magnet:\?xt=urn:btih:(\w+)', magnet)
	assert m, magnet
	code = m.group(1)
	if re.match(r'^[a-zA-Z0-9]{40}$', code):
		return code.decode('hex')
	else:
		return base64.b32decode(code)

class decoder:
	def __init__(self, bytes):
		self.bytes = bytes
		self.i = 0
	def decode_value(self):
		x = self.bytes[self.i]
		if x.isdigit():
			return self.decode_string()
		self.i += 1
		if x == 'd':
			v = {}
			while self.peek() != 'e':
				k = self.decode_string()
				v[k] = self.decode_value()
			self.i += 1
			return v
		elif x == 'l':
			v = []
			while self.peek() != 'e':
				v.append(self.decode_value())
			self.i += 1
			return v
		elif x == 'i':
			return self.decode_int()
		else:
			raise NotImplementedError(x)
	def decode_string(self):
		i = self.bytes.index(':', self.i)
		n = int(self.bytes[self.i:i])
		s = self.bytes[i+1:i+1+n]
		self.i = i + 1 + n
		return s
	def decode_int(self):
		e = self.bytes.index('e', self.i)
		n = int(self.bytes[self.i:e])
		self.i = e + 1
		return n
	def peek(self):
		return self.bytes[self.i]

class encoder:
	def __init__(self, stream):
		self.stream = stream
	def encode(self, v):
		if type(v) == str:
			self.stream.write(str(len(v)))
			self.stream.write(':')
			self.stream.write(v)
		elif type(v) == dict:
			self.stream.write('d')
			for k in sorted(v):
				self.encode(k)
				self.encode(v[k])
			self.stream.write('e')
		elif type(v) == list:
			self.stream.write('l')
			for x in v:
				self.encode(x)
			self.stream.write('e')
		elif type(v) in (int, long):
			self.stream.write('i')
			self.stream.write(str(v))
			self.stream.write('e')
		else:
			raise NotImplementedError(type(v))

def bdecode(bytes):
	return decoder(bytes).decode_value()

def bencode(v):
	from cStringIO import StringIO
	stream = StringIO()
	encoder(stream).encode(v)
	return stream.getvalue()

def assert_content(content):
	assert re.match(r'd\d+:', content), 'Probably not a valid content file [%s...]' % repr(content[:17])

def info_hash_from_content(content):
	assert_content(content)
	return hashlib.sha1(bencode(bdecode(content)['info'])).hexdigest()

def info_hash(path):
	if not path.lower().endswith('.torrent'):
		print '[WARN] Is it really a .torrent file? '+path
	if os.path.getsize(path) > 3*1000*1000:
		raise NotImplementedError('Torrent file too big')
	with open(path, 'rb') as stream:
		return info_hash_from_content(stream.read())

def encode_path(path):
	return path.decode('utf-8').encode(default_encoding)

class sha1_reader:
	def __init__(self, pieces, progress_callback=None):
		assert pieces
		assert len(pieces) % 20 == 0
		self.total = len(pieces)/20
		self.processed = 0
		self.stream = StringIO(pieces)
		self.progress_callback = progress_callback
	def next_sha1(self):
		self.processed += 1
		if self.progress_callback:
			self.progress_callback(float(self.processed)/self.total)
		return self.stream.read(20)

def sha1_update_stream(sha1, stream, n):
	while n > 0:
		readn = min(n, 1024*1024)
		bytes = stream.read(readn)
		assert len(bytes) == readn
		n -= readn
		sha1.update(bytes)
	assert n == 0

def verify_bt_single_file(path, info, progress_callback=None):
	# TODO: check md5sum if available
	if os.path.getsize(path) != info['length']:
		return False
	piece_length = info['piece length']
	assert piece_length > 0
	sha1_stream = sha1_reader(info['pieces'], progress_callback=progress_callback)
	size = info['length']
	with open(path, 'rb') as stream:
		while size > 0:
			n = min(size, piece_length)
			size -= n
			sha1sum = hashlib.sha1()
			sha1_update_stream(sha1sum, stream, n)
			if sha1sum.digest() != sha1_stream.next_sha1():
				return False
		assert size == 0
		assert stream.read(1) == ''
		assert sha1_stream.next_sha1() == ''
	return True

def verify_bt_multiple(folder, info, file_set=None, progress_callback=None):
	# TODO: check md5sum if available
	piece_length = info['piece length']
	assert piece_length > 0

	path_encoding = info.get('encoding', 'utf-8')
	files = []
	for x in info['files']:
		if 'path.utf-8' in x:
			unicode_path = [p.decode('utf-8') for p in x['path.utf-8']]
		else:
			unicode_path = [p.decode(path_encoding) for p in x['path']]
		native_path = [p.encode(default_encoding) for p in unicode_path]
		utf8_path = [p.encode('utf-8') for p in unicode_path]
		files.append({'path':os.path.join(folder, apply(os.path.join, native_path)), 'length':x['length'], 'file':utf8_path})

	sha1_stream = sha1_reader(info['pieces'], progress_callback=progress_callback)
	sha1sum = hashlib.sha1()

	piece_left = piece_length
	complete_piece = True

	while files:
		f = files.pop(0)
		path = f['path']
		size = f['length']
		if os.path.exists(path) and ((not file_set) or (f['file'] in file_set)):
			if os.path.getsize(path) != size:
				return False
			if size <= piece_left:
				with open(path, 'rb') as stream:
					sha1_update_stream(sha1sum, stream, size)
					assert stream.read(1) == ''
				piece_left -= size
				if not piece_left:
					if sha1sum.digest() != sha1_stream.next_sha1() and complete_piece:
						return False
					complete_piece = True
					sha1sum = hashlib.sha1()
					piece_left = piece_length
			else:
				with open(path, 'rb') as stream:
					while size >= piece_left:
						size -= piece_left
						sha1_update_stream(sha1sum, stream, piece_left)
						if sha1sum.digest() != sha1_stream.next_sha1() and complete_piece:
							return False
						complete_piece = True
						sha1sum = hashlib.sha1()
						piece_left = piece_length
					if size:
						sha1_update_stream(sha1sum, stream, size)
						piece_left -= size
		else:
			if size:
				while size >= piece_left:
					size -= piece_left
					sha1_stream.next_sha1()
					sha1sum = hashlib.sha1()
					piece_left = piece_length
				if size:
					complete_piece = False
					piece_left -= size
				else:
					complete_piece = True

	if piece_left < piece_length:
		if complete_piece:
			if sha1sum.digest() != sha1_stream.next_sha1():
				return False
		else:
			sha1_stream.next_sha1()
	assert sha1_stream.next_sha1() == ''

	return True

def verify_bt(path, info, file_set=None, progress_callback=None):
	if not os.path.exists(path):
		raise Exception("File doesn't exist: %s" % path)
	if 'files' not in info:
		if os.path.isfile(path):
			return verify_bt_single_file(path, info, progress_callback=progress_callback)
		else:
			path = os.path.join(path, encode_path(info['name']))
			return verify_bt_single_file(path, info, progress_callback=progress_callback)
	else:
		return verify_bt_multiple(path, info, file_set=file_set, progress_callback=progress_callback)

def verify_bt_file(path, torrent_path, file_set=None, progress_callback=None):
	with open(torrent_path, 'rb') as x:
		return verify_bt(path, bdecode(x.read())['info'], file_set, progress_callback)


########NEW FILE########
__FILENAME__ = lixian_hash_ed2k

import hashlib

chunk_size = 9728000
buffer_size = 1024*1024

def md4():
	return hashlib.new('md4')

def hash_stream(stream):
	total_md4 = None
	while True:
		chunk_md4 = md4()
		chunk_left = chunk_size
		while chunk_left:
			n = min(chunk_left, buffer_size)
			part = stream.read(n)
			chunk_md4.update(part)
			if len(part) < n:
				if total_md4:
					total_md4.update(chunk_md4.digest())
					return total_md4.hexdigest()
				else:
					return chunk_md4.hexdigest()
			chunk_left -= n
		if total_md4 is None:
			total_md4 = md4()
		total_md4.update(chunk_md4.digest())
	raise NotImplementedError()

def hash_string(s):
	from cStringIO import StringIO
	return hash_stream(StringIO(s))

def hash_file(path):
	with open(path, 'rb') as stream:
		return hash_stream(stream)

def parse_ed2k_link(link):
	import re, urllib
	ed2k_re = r'ed2k://\|file\|([^|]*)\|(\d+)\|([a-fA-F0-9]{32})\|'
	m = re.match(ed2k_re, link) or re.match(ed2k_re, urllib.unquote(link))
	if not m:
		raise Exception('not an acceptable ed2k link: '+link)
	name, file_size, hash_hex = m.groups()
	from lixian_url import unquote_url
	return unquote_url(name), hash_hex.lower(), int(file_size)

def parse_ed2k_id(link):
	return parse_ed2k_link(link)[1:]

def parse_ed2k_file(link):
	return parse_ed2k_link(link)[0]

def verify_ed2k_link(path, link):
	hash_hex, file_size = parse_ed2k_id(link)
	import os.path
	if os.path.getsize(path) != file_size:
		return False
	return hash_file(path).lower() == hash_hex.lower()

def generate_ed2k_link(path):
	import sys, os.path, urllib
	filename = os.path.basename(path)
	encoding = sys.getfilesystemencoding()
	if encoding.lower() != 'ascii':
		filename = filename.decode(encoding).encode('utf-8')
	return 'ed2k://|file|%s|%d|%s|/' % (urllib.quote(filename), os.path.getsize(path), hash_file(path))

def test_md4():
	assert hash_string("") == '31d6cfe0d16ae931b73c59d7e0c089c0'
	assert hash_string("a") == 'bde52cb31de33e46245e05fbdbd6fb24'
	assert hash_string("abc") == 'a448017aaf21d8525fc10ae87aa6729d'
	assert hash_string("message digest") == 'd9130a8164549fe818874806e1c7014b'
	assert hash_string("abcdefghijklmnopqrstuvwxyz") == 'd79e1c308aa5bbcdeea8ed63df412da9'
	assert hash_string("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") == '043f8582f241db351ce627e153e7f0e4'
	assert hash_string("12345678901234567890123456789012345678901234567890123456789012345678901234567890") == 'e33b4ddc9c38f2199c3e7b164fcc0536'



########NEW FILE########
__FILENAME__ = lixian_help

basic_commands = [
 ('help',       "try this help..."),
 ('login',      "login Xunlei cloud"),
 ('download',   "download tasks from Xunlei cloud"),
 ('list',       "list tasks on Xunlei cloud"),
 ('add',        "add tasks to Xunlei cloud"),
 ('delete',     "delete tasks from Xunlei cloud"),
 ('pause',      "pause tasks on Xunlei cloud"),
 ('restart',    "restart tasks on Xunlei cloud"),
 ('rename',     "rename task"),
 ('readd',      "re-add tasks"),
 ('config',     "save configuration so you don't have to repeat it"),
 ('info',       "print user id, internal user id, and gdriveid"),
 ('logout',     "logout from Xunlei cloud"),
]

def join_commands(commands):
	n = max(len(x[0]) for x in commands)
	n = max(n, 10)
	return ''.join(' %%-%ds %%s\n' % n % (k, h) for (k, h) in commands)

basic_usage = '''python lixian_cli.py <command> [<args>]

Basic commands:
''' + join_commands(basic_commands)

extended_usage = ''

# lx
def usage():
	return basic_usage + '''
Use 'python lixian_cli.py help' for details.
Use 'python lixian_cli.py help <command>' for more information on a specific command.
Check https://github.com/iambus/xunlei-lixian for detailed (and Chinese) doc.'''

# lx xxx
# lx help help
help_help = '''Get helps:
 python lixian_cli.py help help
 python lixian_cli.py help examples
 python lixian_cli.py help readme
 python lixian_cli.py help <command>'''

# lx xxx
# lx help help
help = help_help

# lx help
# lx -h
def welcome_help():
	return '''Python script for Xunlei cloud.

Basic usage:
''' + basic_usage + extended_usage + '\n' + help_help

def examples():
	return '''python lixian_cli.py login "Your Xunlei account" "Your password"
python lixian_cli.py login "Your password"
python lixian_cli.py login

python lixian_cli.py config username "Your Xunlei account"
python lixian_cli.py config password "Your password"

python lixian_cli.py list
python lixian_cli.py list --completed
python lixian_cli.py list --completed --name --original-url --download-url --no-status --no-id
python lixian_cli.py list --deleted
python lixian_cli.py list --expired
python lixian_cli.py list id1 id2
python lixian_cli.py list zip rar
python lixian_cli.py list 2012.04.04 2012.04.05

python lixian_cli.py download task-id
python lixian_cli.py download ed2k-url
python lixian_cli.py download --tool=wget ed2k-url
python lixian_cli.py download --tool=asyn ed2k-url
python lixian_cli.py download ed2k-url --output "file to save"
python lixian_cli.py download id1 id2 id3
python lixian_cli.py download url1 url2 url3
python lixian_cli.py download --input download-urls-file
python lixian_cli.py download --input download-urls-file --delete
python lixian_cli.py download --input download-urls-file --output-dir root-dir-to-save-files
python lixian_cli.py download bt://torrent-info-hash
python lixian_cli.py download 1.torrent
python lixian_cli.py download torrent-info-hash
python lixian_cli.py download --bt http://xxx/xxx.torrent
python lixian_cli.py download bt-task-id/file-id
python lixian_cli.py download --all
python lixian_cli.py download mkv
python lixian_cli.py download 2012.04.04
python lixian_cli.py download 0 1 2
python lixian_cli.py download 0-2

python lixian_cli.py add url
python lixian_cli.py add 1.torrent
python lixian_cli.py add torrent-info-hash
python lixian_cli.py add --bt http://xxx/xxx.torrent

python lixian_cli.py delete task-id
python lixian_cli.py delete url
python lixian_cli.py delete file-name-on-cloud-to-delete

python lixian_cli.py pause id

python lixian_cli.py restart id

python lixian_cli.py rename id name

python lixian_cli.py logout

Please check https://github.com/iambus/xunlei-lixian for detailed (and Chinese) doc.
'''

def readme():
	import sys
	import os.path
	doc = os.path.join(sys.path[0], 'README.md')
	with open(doc) as txt:
		return txt.read().decode('utf-8')


login    = '''python lixian_cli.py login <username> <password>

login Xunlei cloud

Examples:
 python lixian_cli.py login "Your Xunlei account" "Your password"
 python lixian_cli.py login "Your password"
 python lixian_cli.py login
'''

download = '''python lixian_cli.py download [options] [id|url]...

download tasks from Xunlei cloud

Options:
 --input=[file]    -i            Download URLs found in file.
 --output=[file]   -o            Download task to file.
 --output-dir=[dir]              Download task to dir.
 --tool=[wget|asyn|aria2|curl]   Choose download tool.
                                 Default: wget
 --continue        -c            Continue downloading a partially downloaded file.
                                 Default: false.
 --overwrite                     Overwrite partially downloaded file.
                                 Default: false.
 --delete                        Delete task from Xunlei cloud after download is finished.
                                 Default: false.
 --torrent         --bt          Treat URLs as torrent files
                                 Default: false.
 --all                           Download all tasks. This option will be ignored if specific download URLs or task ids can be found. 
                                 Default: false.
 --hash                          When this option is false (--no-hash), never do full hash, but a minimal hash will be performed (supposed to be very fast).
                                 Default: true.
 --mini-hash                     If the target file already exists, and the file size is complete, do a minimal hash (instead of full hash, which would be much more expensive). This is useful when you are resuming a batch download, in this case the previously downloaded and verified files won't be re-verified.
                                 Default: false.

Examples:
 python lixian_cli.py download task-id
 python lixian_cli.py download ed2k-url
 python lixian_cli.py download --tool=wget ed2k-url
 python lixian_cli.py download --tool=asyn ed2k-url
 python lixian_cli.py download ed2k-url --output "file to save"
 python lixian_cli.py download id1 id2 id3
 python lixian_cli.py download url1 url2 url3
 python lixian_cli.py download --input download-urls-file
 python lixian_cli.py download --input download-urls-file --delete
 python lixian_cli.py download --input download-urls-file --output-dir root-dir-to-save-files
 python lixian_cli.py download bt://torrent-info-hash
 python lixian_cli.py download 1.torrent
 python lixian_cli.py download torrent-info-hash
 python lixian_cli.py download --bt http://xxx/xxx.torrent
 python lixian_cli.py download bt-task-id/file-id
 python lixian_cli.py download --all
 python lixian_cli.py download mkv
 python lixian_cli.py download 2012.04.04
 python lixian_cli.py download 0 1 2
 python lixian_cli.py download 0-2
'''

list     = '''python lixian_cli.py list

list tasks on Xunlei cloud

Options:
 --completed          Print only completed tasks. Default: no
 --deleted            Print only deleted tasks. Default: no
 --expired            Print only expired tasks. Default: no
 --[no]-n             Print task sequence number. Default: no
 --[no]-id            Print task id. Default: yes
 --[no]-name          Print task name. Default: yes
 --[no]-status        Print task status. Default: yes
 --[no]-size          Print task size. Default: no
 --[no]-progress      Print task progress (in percent). Default: no
 --[no]-speed         Print task speed. Default: no
 --[no]-date          Print the date task added. Default: no
 --[no]-original-url  Print the original URL. Default: no
 --[no]-download-url  Print the download URL used to download from Xunlei cloud. Default: no
 --[no]-format-size   Print file size in human readable format. Default: no
 --[no]-colors        Colorful output. Default: yes

Examples:
 python lixian_cli.py list
 python lixian_cli.py list id
 python lixian_cli.py list bt-task-id/
 python lixian_cli.py list --completed
 python lixian_cli.py list --completed --name --original-url --download-url --no-status --no-id
 python lixian_cli.py list --deleted
 python lixian_cli.py list --expired
 python lixian_cli.py list id1 id2
 python lixian_cli.py list zip rar
 python lixian_cli.py list 2012.04.04 2012.04.05
'''

add      = '''python lixian_cli.py add [options] url...

add tasks to Xunlei cloud

Options:
 --input=[file]                  Download URLs found in file.
 --torrent       --bt            Treat all arguments as torrent files (e.g. local torrent file, torrent http url, torrent info hash)
                                 Default: false.

Examples:
 python lixian_cli.py add url
 python lixian_cli.py add 1.torrent
 python lixian_cli.py add torrent-info-hash
 python lixian_cli.py add --bt http://xxx/xxx.torrent
'''

delete   = '''python lixian_cli.py delete [options] [id|url|filename|keyword|date]...

delete tasks from Xunlei cloud

Options:
 -i     prompt before delete
 --all  delete all tasks if there are multiple matches

Examples:
 python lixian_cli.py delete task-id
 python lixian_cli.py delete url
 python lixian_cli.py delete file-name-on-cloud-to-delete
'''

pause    = '''python lixian_cli.py pause [options] [id|url|filename|keyword|date]...

pause tasks on Xunlei cloud

Options:
 -i     prompt before pausing tasks
 --all  pause all tasks if there are multiple matches
'''

restart  = '''python lixian_cli.py restart [id|url|filename|keyword|date]...

restart tasks on Xunlei cloud

Options:
 -i     prompt before restart
 --all  restart all tasks if there are multiple matches
'''

rename   = '''python lixian_cli.py rename task-id task-name

rename task
'''

readd   = '''python lixian_cli.py readd [--deleted|--expired] task-id...

re-add deleted/expired tasks

Options:
 --deleted  re-add deleted tasks
 --expired  re-add expired tasks
'''

config   = '''python lixian_cli.py config key [value]

save configuration so you don't have to repeat it

Examples:
 python lixian_cli.py config username "your xunlei id"
 python lixian_cli.py config password "your xunlei password"
 python lixian_cli.py config continue
'''

info     = '''python lixian_cli.py info

print user id, internal user id, and gdriveid

Options:
 --id    -i  print user id only
'''

logout   = '''python lixian_cli.py logout

logout from Xunlei cloud
'''



########NEW FILE########
__FILENAME__ = lixian_logging

__all__ = ['init_logger', 'get_logger']

import logging

INFO = logging.INFO
DEBUG = logging.DEBUG
TRACE = 1

def file_logger(path, level):
	import os.path
	path = os.path.expanduser(path)

	logger = logging.getLogger('lixian')
	logger.setLevel(min(level, DEBUG)) # if file log is enabled, always log debug message

	handler = logging.FileHandler(filename=path, )
	handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

	logger.addHandler(handler)

	return logger

class ConsoleLogger:
	def __init__(self, level=INFO):
		self.level = level
	def stdout(self, message):
		print message
	def info(self, message):
		if self.level <= INFO:
			print message
	def debug(self, message):
		if self.level <= DEBUG:
			print message
	def trace(self, message):
		pass

class FileLogger:
	def __init__(self, path, level=INFO, file_level=None, console_level=None):
		console_level = console_level or level
		file_level = file_level or level
		self.console = ConsoleLogger(console_level)
		self.logger = file_logger(path, file_level)
	def stdout(self, message):
		self.console.stdout(message)
	def info(self, message):
		self.console.info(message)
		self.logger.info(message)
	def debug(self, message):
		self.console.debug(message)
		self.logger.debug(message)
	def trace(self, message):
		self.logger.log(level=TRACE, msg=message)

default_logger = None

def init_logger(use_colors=True, level=INFO, path=None):
	global default_logger
	if not default_logger:
		if isinstance(level, int):
			assert level in (INFO, DEBUG, TRACE)
			console_level = level
			file_level = level
		elif isinstance(level, basestring):
			level = level.lower()
			if level in ('info', 'debug', 'trace'):
				level = {'info': INFO, 'debug': DEBUG, 'trace': TRACE}[level]
				console_level = level
				file_level = level
			else:
				console_level = INFO
				file_level = DEBUG
				for level in level.split(','):
					device, level = level.split(':')
					if device == 'console':
						console_level = {'info': INFO, 'debug': DEBUG, 'trace': TRACE}[level]
					elif device == 'file':
						file_level = {'info': INFO, 'debug': DEBUG, 'trace': TRACE}[level]
					else:
						raise NotImplementedError('Invalid logging level: ' + device)
		else:
			raise NotImplementedError(type(level))
		if path:
			default_logger = FileLogger(path, console_level=console_level, file_level=file_level)
		else:
			default_logger = ConsoleLogger(console_level)

def get_logger():
	init_logger()
	return default_logger


########NEW FILE########
__FILENAME__ = lixian_nodes

import lixian_logging

import urllib2
import re

VOD_RANGE = '0-50'

def resolve_node_url(url, gdriveid, timeout=60):
	request = urllib2.Request(url, headers={'Cookie': 'gdriveid=' + gdriveid})
	response = urllib2.urlopen(request, timeout=timeout)
	response.close()
	return response.geturl()

def switch_node_in_url(node_url, node):
	return re.sub(r'(http://)(vod\d+)(\.t\d+\.lixian\.vip\.xunlei\.com)', r'\1%s\3' % node, node_url)


def switch_node(url, node, gdriveid):
	assert re.match(r'^vod\d+$', node)
	logger = lixian_logging.get_logger()
	logger.debug('Download URL: ' + url)
	try:
		url = resolve_node_url(url, gdriveid, timeout=60)
		logger.debug('Resolved URL: ' + url)
	except:
		import traceback
		logger.debug(traceback.format_exc())
		return url
	url = switch_node_in_url(url, node)
	logger.debug('Switch to node URL: ' + url)
	return url

def test_response_speed(response, max_size, max_duration):
	import time
	current_duration = 0
	current_size = 0
	start = time.clock()
	while current_duration < max_duration and current_size < max_size:
		data = response.read(max_size - current_size)
		if not data:
			# print "End of file"
			break
		current_size += len(data)
		end = time.clock()
		current_duration = end - start
	if current_size < 1024:
		raise Exception("Sample too small: %d" % current_size)
	return current_size / current_duration, current_size, current_duration


def get_node_url_speed(url, gdriveid):
	request = urllib2.Request(url, headers={'Cookie': 'gdriveid=' + gdriveid})
	response = urllib2.urlopen(request, timeout=3)
	speed, size, duration = test_response_speed(response, 2*1000*1000, 3)
	response.close()
	return speed


def parse_vod_nodes(vod_nodes):
	if vod_nodes == 'all' or not vod_nodes:
		vod_nodes = VOD_RANGE
	nodes = []
	# remove duplicate nodes
	seen = set()
	def add(node):
		if node not in seen:
			nodes.append(node)
			seen.add(node)
	for expr in re.split(r'\s*,\s*', vod_nodes):
		if re.match(r'^\d+-\d+$', expr):
			start, end = map(int, expr.split('-'))
			if start <= end:
				for i in range(start, end + 1):
					add("vod%d" % i)
			else:
				for i in range(start, end - 1, -1):
					add("vod%d" % i)
		elif re.match(r'^\d+$', expr):
			add('vod'+expr)
		else:
			raise Exception("Invalid vod expr: " + expr)
	return nodes

def get_best_node_url_from(node_url, nodes, gdriveid):
	best = None
	best_speed = 0
	logger = lixian_logging.get_logger()
	for node in nodes:
		url = switch_node_in_url(node_url, node)
		try:
			speed = get_node_url_speed(url, gdriveid)
			logger.debug("%s speed: %s" % (node, speed))
			if speed > best_speed:
				best_speed = speed
				best = url
		except Exception, e:
			logger.debug("%s error: %s" % (node, e))
	return best

def get_good_node_url_from(node_url, nodes, acceptable_speed, gdriveid):
	best = None
	best_speed = 0
	logger = lixian_logging.get_logger()
	for node in nodes:
		url = switch_node_in_url(node_url, node)
		try:
			speed = get_node_url_speed(url, gdriveid)
			logger.debug("%s speed: %s" % (node, speed))
			if speed > acceptable_speed:
				return url
			elif speed > best_speed:
				best_speed = speed
				best = url
		except Exception, e:
			logger.debug("%s error: %s" % (node, e))
	return best

def use_node_by_policy(url, vod_nodes, gdriveid, policy):
	nodes = parse_vod_nodes(vod_nodes)
	assert nodes
	logger = lixian_logging.get_logger()
	logger.debug('Download URL: ' + url)
	try:
		node_url = resolve_node_url(url, gdriveid, timeout=60)
		logger.debug('Resolved URL: ' + node_url)
	except:
		import traceback
		logger.debug(traceback.format_exc())
		return url
	default_node = re.match(r'http://(vod\d+)\.', node_url).group(1)
	if default_node not in nodes:
		nodes.insert(0, default_node)
	chosen = policy(node_url, nodes, gdriveid)
	if chosen:
		logger.debug('Switch to URL: ' + chosen)
		return chosen
	else:
		return node_url


def use_fastest_node(url, vod_nodes, gdriveid):
	return use_node_by_policy(url, vod_nodes, gdriveid, get_best_node_url_from)

def use_fast_node(url, vod_nodes, acceptable_speed, gdriveid):
	def policy(url, vod_nodes, gdriveid):
		return get_good_node_url_from(url, vod_nodes, acceptable_speed, gdriveid)
	return use_node_by_policy(url, vod_nodes, gdriveid, policy)


########NEW FILE########
__FILENAME__ = aria2

from lixian_plugins.api import command

from lixian_config import *
from lixian_encoding import default_encoding
from lixian_cli_parser import command_line_parser
from lixian_cli_parser import with_parser
from lixian_cli_parser import command_line_option, command_line_value
from lixian_commands.util import parse_login, create_client

def export_aria2_conf(args):
	client = create_client(args)
	import lixian_query
	tasks = lixian_query.search_tasks(client, args)
	files = []
	for task in tasks:
		if task['type'] == 'bt':
			subs, skipped, single_file = lixian_query.expand_bt_sub_tasks(task)
			if not subs:
				continue
			if single_file:
				files.append((subs[0]['xunlei_url'], subs[0]['name'], None))
			else:
				for f in subs:
					files.append((f['xunlei_url'], f['name'], task['name']))
		else:
			files.append((task['xunlei_url'], task['name'], None))
	output = ''
	for url, name, dir in files:
		if type(url) == unicode:
			url = url.encode(default_encoding)
		output += url + '\n'
		output += '  out=' + name.encode(default_encoding) + '\n'
		if dir:
			output += '  dir=' + dir.encode(default_encoding) + '\n'
		output += '  header=Cookie: gdriveid=' + client.get_gdriveid() + '\n'
	return output

@command(usage='export task download urls as aria2 format')
@command_line_parser()
@with_parser(parse_login)
@command_line_option('all')
def export_aria2(args):
	'''
	usage: lx export-aria2 [id|name]...
	'''
	print export_aria2_conf(args)

def download_aria2_stdin(aria2_conf, j):
	aria2_opts = ['aria2c', '-i', '-', '-j', j]
	aria2_opts.extend(get_config('aria2-opts', '').split())
	from subprocess import Popen, PIPE
	sub = Popen(aria2_opts, stdin=PIPE, bufsize=1, shell=True)
	sub.communicate(aria2_conf)
	sub.stdin.close()
	exit_code = sub.wait()
	if exit_code != 0:
		raise Exception('aria2c exited abnormaly')

def download_aria2_temp(aria2_conf, j):
	import tempfile
	temp = tempfile.NamedTemporaryFile('w', delete=False)
	temp.file.write(aria2_conf)
	temp.file.close()
	try:
		aria2_opts = ['aria2c', '-i', temp.name, '-j', j]
		aria2_opts.extend(get_config('aria2-opts', '').split())
		import subprocess
		exit_code = subprocess.call(aria2_opts)
	finally:
		import os
		os.unlink(temp.name)
	if exit_code != 0:
		raise Exception('aria2c exited abnormaly')

@command(usage='concurrently download tasks in aria2')
@command_line_parser()
@with_parser(parse_login)
@command_line_option('all')
@command_line_value('max-concurrent-downloads', alias='j', default=get_config('aria2-j', '5'))
def download_aria2(args):
	'''
	usage: lx download-aria2 -j 5 [id|name]...
	'''
	aria2_conf = export_aria2_conf(args)
	import platform
	if platform.system() == 'Windows':
		download_aria2_temp(aria2_conf, args.max_concurrent_downloads)
	else:
		download_aria2_stdin(aria2_conf, args.max_concurrent_downloads)


########NEW FILE########
__FILENAME__ = decode_url

from lixian_plugins.api import command

@command(usage='convert thunder:// (and more) to normal url')
def decode_url(args):
	'''
	usage: lx decode-url thunder://...
	'''
	from lixian_url import url_unmask
	for x in args:
		print url_unmask(x)


########NEW FILE########
__FILENAME__ = diagnostics

from lixian_plugins.api import command

@command(name='diagnostics', usage='print helpful information for diagnostics')
def lx_diagnostics(args):
	'''
	usage: lx diagnostics
	'''
	from lixian_encoding import default_encoding
	print 'default_encoding ->', default_encoding
	import sys
	print 'sys.getdefaultencoding() ->', sys.getdefaultencoding()
	print 'sys.getfilesystemencoding() ->', sys.getfilesystemencoding()
	print r"print u'\u4e2d\u6587'.encode('utf-8') ->", u'\u4e2d\u6587'.encode('utf-8')
	print r"print u'\u4e2d\u6587'.encode('gbk') ->", u'\u4e2d\u6587'.encode('gbk')


########NEW FILE########
__FILENAME__ = echo

from lixian_plugins.api import command

@command(usage='echo arguments')
def echo(args):
	'''
	lx echo ...
	'''
	import lixian_cli_parser
	print ' '.join(lixian_cli_parser.expand_command_line(args))


########NEW FILE########
__FILENAME__ = export_download_urls

from lixian_plugins.api import command


from lixian_cli_parser import command_line_parser
from lixian_cli_parser import with_parser
from lixian_cli_parser import command_line_option, command_line_value
from lixian_commands.util import parse_login, create_client

@command(usage='export task download urls')
@command_line_parser()
@with_parser(parse_login)
@command_line_option('all')
@command_line_value('category')
def export_download_urls(args):
	'''
	usage: lx export-download-urls [id|name]...
	'''
	assert len(args) or args.all or args.category, 'Not enough arguments'
	client = create_client(args)
	import lixian_query
	tasks = lixian_query.search_tasks(client, args)
	urls = []
	for task in tasks:
		if task['type'] == 'bt':
			subs, skipped, single_file = lixian_query.expand_bt_sub_tasks(task)
			if not subs:
				continue
			if single_file:
				urls.append((subs[0]['xunlei_url'], subs[0]['name'], None))
			else:
				for f in subs:
					urls.append((f['xunlei_url'], f['name'], task['name']))
		else:
			urls.append((task['xunlei_url'], task['name'], None))
	for url, _, _ in urls:
		print url

########NEW FILE########
__FILENAME__ = extend_links

from lixian_plugins.api import command

@command(usage='parse links')
def extend_links(args):
	'''
	usage: lx extend-links http://kuai.xunlei.com/d/... http://www.verycd.com/topics/...

	parse and print links from pages

	lx extend-links urls...
	lx extend-links --name urls...
	'''

	from lixian_cli_parser import parse_command_line
	from lixian_encoding import default_encoding

	args = parse_command_line(args, [], ['name'])
	import lixian_plugins.parsers
	if args.name:
		for x in lixian_plugins.parsers.extend_links_name(args):
			print x.encode(default_encoding)
	else:
		for x in lixian_plugins.parsers.extend_links(args):
			print x


########NEW FILE########
__FILENAME__ = get_torrent

from lixian_plugins.api import command

from lixian_cli_parser import command_line_parser
from lixian_cli_parser import with_parser
from lixian_cli import parse_login
from lixian_commands.util import create_client

@command(name='get-torrent', usage='get .torrent by task id or info hash')
@command_line_parser()
@with_parser(parse_login)
def get_torrent(args):
	'''
	usage: lx get-torrent [info-hash|task-id]...
	'''
	client = create_client(args)
	for id in args:
		id = id.lower()
		import re
		if re.match(r'[a-fA-F0-9]{40}$', id):
			torrent = client.get_torrent_file_by_info_hash(id)
		elif re.match(r'\d+$', id):
			import lixian_query
			task = lixian_query.get_task_by_id(client, id)
			id = task['bt_hash']
			id = id.lower()
			torrent = client.get_torrent_file_by_info_hash(id)
		else:
			raise NotImplementedError()
		path = id + '.torrent'
		print path
		with open(path, 'wb') as output:
			output.write(torrent)


########NEW FILE########
__FILENAME__ = hash

from lixian_plugins.api import command

@command(name='hash', usage='compute hashes')
def print_hash(args):
	'''
	lx hash --sha1 file...
	lx hash --md5 file...
	lx hash --md4 file...
	lx hash --dcid file...
	lx hash --ed2k file...
	lx hash --info-hash xxx.torrent...
	lx hash --verify-sha1 file hash
	lx hash --verify-md5 file hash
	lx hash --verify-md4 file hash
	lx hash --verify-dcid file hash
	lx hash --verify-ed2k file ed2k://...
	lx hash --verify-bt file xxx.torrent
	'''
	#assert len(args) == 1
	import lixian_hash
	#import lixian_hash_ed2k
	#print 'ed2k:', lixian_hash_ed2k.hash_file(args[0])
	#print 'dcid:', lixian_hash.dcid_hash_file(args[0])
	import lixian_cli_parser
	lixian_hash.main(lixian_cli_parser.expand_command_line(args))


########NEW FILE########
__FILENAME__ = kuai

from lixian_plugins.api import command

@command(usage='parse links from kuai.xunlei.com')
def kuai(args):
	'''
	usage: lx kuai http://kuai.xunlei.com/d/xxx...

	Note that you can simply use:
	 lx add http://kuai.xunlei.com/d/xxx...
	or:
	 lx download http://kuai.xunlei.com/d/xxx...
	'''
	import lixian_kuai
	lixian_kuai.main(args)


########NEW FILE########
__FILENAME__ = list_torrent

from lixian_plugins.api import command

from lixian_cli_parser import parse_command_line
from lixian_config import get_config
from lixian_encoding import default_encoding

def b_encoding(b):
	if 'encoding' in b:
		return b['encoding']
	if 'codepage' in b:
		return 'cp' + str(b['codepage'])
	return 'utf-8'

def b_name(info, encoding='utf-8'):
	if 'name.utf-8' in info:
		return info['name.utf-8'].decode('utf-8')
	return info['name'].decode(encoding)

def b_path(f, encoding='utf-8'):
	if 'path.utf-8' in f:
		return [p.decode('utf-8') for p in f['path.utf-8']]
	return [p.decode(encoding) for p in f['path']]

@command(usage='list files in local .torrent')
def list_torrent(args):
	'''
	usage: lx list-torrent [--size] xxx.torrent...
	'''
	args = parse_command_line(args, [], ['size'], default={'size':get_config('size')})
	torrents = args
	if not torrents:
		from glob import glob
		torrents = glob('*.torrent')
	if not torrents:
		raise Exception('No .torrent file found')
	for p in torrents:
		with open(p, 'rb') as stream:
			from lixian_hash_bt import bdecode
			b = bdecode(stream.read())
			encoding = b_encoding(b)
			info = b['info']
			from lixian_util import format_size
			if args.size:
				size = sum(f['length'] for f in info['files']) if 'files' in info else info['length']
				print '*', b_name(info, encoding).encode(default_encoding), format_size(size)
			else:
				print '*', b_name(info, encoding).encode(default_encoding)
			if 'files' in info:
				for f in info['files']:
					if f['path'][0].startswith('_____padding_file_'):
						continue
					path = '/'.join(b_path(f, encoding)).encode(default_encoding)
					if args.size:
						print '%s (%s)' % (path, format_size(f['length']))
					else:
						print path
			else:
				path = b_name(info, encoding).encode(default_encoding)
				if args.size:
					from lixian_util import format_size
					print '%s (%s)' % (path, format_size(info['length']))
				else:
					print path


########NEW FILE########
__FILENAME__ = speed_test
from lixian_plugins.api import command


from lixian_cli_parser import command_line_parser
from lixian_cli_parser import with_parser
from lixian_cli_parser import command_line_option, command_line_value
from lixian_commands.util import parse_login, parse_colors, create_client
from lixian_config import get_config

from lixian_encoding import default_encoding
from lixian_colors import colors

import lixian_nodes

@command(usage='test download speed from multiple vod nodes')
@command_line_parser()
@with_parser(parse_login)
@with_parser(parse_colors)
@command_line_value('vod-nodes', default=get_config('vod-nodes', lixian_nodes.VOD_RANGE))
def speed_test(args):
	'''
	usage: lx speed_test [--vod-nodes=0-50] [id|name]
	'''
	assert len(args)
	client = create_client(args)
	import lixian_query
	tasks = lixian_query.search_tasks(client, args)
	if not tasks:
		raise Exception('No task found')
	task = tasks[0]
	urls = []
	if task['type'] == 'bt':
		subs, skipped, single_file = lixian_query.expand_bt_sub_tasks(task)
		if not subs:
			raise Exception('No files found')
		subs = [f for f in subs if f['size'] > 1000*1000] or subs # skip files with length < 1M
		if single_file:
			urls.append((subs[0]['xunlei_url'], subs[0]['name'], None))
		else:
			for f in subs:
				urls.append((f['xunlei_url'], f['name'], task['name']))
	else:
		urls.append((task['xunlei_url'], task['name'], None))
	url, filename, dirname = urls[0]
	name = dirname + '/' + filename if dirname else filename
	test_file(client, url, name, args)

def test_file(client, url, name, options):
	with colors(options.colors).cyan():
		print name.encode(default_encoding)
	# print 'File:', name.encode(default_encoding)
	# print 'Address:', url
	node_url = lixian_nodes.resolve_node_url(url, client.get_gdriveid(), timeout=3)
	# print 'Node:', node_url
	test_nodes(node_url, client.get_gdriveid(), options)

def test_nodes(node_url, gdriveid, options):
	nodes = lixian_nodes.parse_vod_nodes(options.vod_nodes)
	best = None
	best_speed = 0
	for node in nodes:
		# print 'Node:', node
		url = lixian_nodes.switch_node_in_url(node_url, node)
		try:
			speed = lixian_nodes.get_node_url_speed(url, gdriveid)
			if best_speed < speed:
				best = node
				best_speed = speed
			kb = int(speed/1000)
			# print 'Speed: %dKB/s' % kb, '.' * (kb /100)
			show_node_speed(node, kb, options)
		except Exception, e:
			show_node_error(node, e, options)
	if best:
		with colors(options.colors).green():
			print best,
		print "is the fastest node!"

def show_node_speed(node, kb, options):
	node = "%-5s " % node
	speed = '%dKB/s' % kb
	bar = '.' * (kb /100)
	whitespaces = ' ' * (79 - len(node) - len(bar) - len(speed))
	if kb >= 1000:
		with colors(options.colors).green():
			# print node + bar + whitespaces + speed
			with colors(options.colors).bold():
				print node[:-1],
			print bar + whitespaces + speed
	else:
		print node + bar + whitespaces + speed

def show_node_error(node, e, options):
	with colors(options.colors).red():
		print "%-5s %s" % (node, e)


########NEW FILE########
__FILENAME__ = date

from lixian_plugins.api import task_filter

@task_filter(pattern=r'^\d{4}[-.]\d{2}[-.]\d{2}$')
def filter_by_date(keyword, task):
	return task['date'] == keyword.replace('-', '.')


########NEW FILE########
__FILENAME__ = name

from lixian_plugins.api import name_filter

@name_filter(protocol='name')
def filter_by_raw_text(keyword, name):
	return keyword.lower() in name.lower()


########NEW FILE########
__FILENAME__ = raw

from lixian_plugins.api import name_filter

@name_filter(protocol='raw')
def filter_by_raw_text(keyword, name):
	return keyword.lower() in name.lower()


########NEW FILE########
__FILENAME__ = regexp

from lixian_plugins.api import name_filter

import re

@name_filter(protocol='regexp')
def filter_by_regexp(keyword, name):
	return re.search(keyword, name)

########NEW FILE########
__FILENAME__ = size

from lixian_plugins.api import task_filter

import re

@task_filter(protocol='size')
def filter_by_size(keyword, task):
	'''
	Example:
	lx download size:10m-
	lx download size:1G+
	lx download 0/size:1g-
	'''
	m = re.match(r'^([<>])?(\d+(?:\.\d+)?)([GM])?([+-])?$', keyword, flags=re.I)
	assert m, keyword
	less_or_great, n, u, less_or_more = m.groups()
	assert bool(less_or_great) ^ bool(less_or_more), 'must bt <size, >size, size-, or size+'
	size = float(n) * {None: 1, 'G': 1000**3, 'g': 1000**3, 'M': 1000**2, 'm': 1000**2}[u]
	if less_or_great == '<' or less_or_more == '-':
		return task['size'] < size
	else:
		return task['size'] > size


########NEW FILE########
__FILENAME__ = sort

from lixian_plugins.api import task_filter

@task_filter(protocol='sort', batch=True)
def sort_by_name(keyword, tasks):
	'''
	Example:
	lx list sort:
	lx download 0/sort:/[0-1]
	'''
	return sorted(tasks, key=lambda x: x['name'])

########NEW FILE########
__FILENAME__ = total_size

from lixian_plugins.api import task_filter

import re

@task_filter(protocol='total-size', batch=True)
def fetch_by_total_size(keyword, tasks):
	'''
	Example:
	lx download total_size:1g
	lx download 0/total_size:1g
	lx list total_size:1g
	'''
	m = re.match(r'^(\d+(?:\.\d+)?)([GM])?$', keyword, flags=re.I)
	assert m, keyword
	n, u = m.groups()
	limit = float(n) * {None: 1, 'G': 1000**3, 'g': 1000**3, 'M': 1000**2, 'm': 1000**2}[u]
	total = 0
	results = []
	for t in tasks:
		total += t['size']
		if total <= limit:
			results.append(t)
		else:
			return results
	return results


########NEW FILE########
__FILENAME__ = icili

from lixian_plugins.api import page_parser

import urllib2
import re

def icili_links(url):
	assert url.startswith('http://www.icili.com/emule/download/'), url
	html = urllib2.urlopen(url).read()
	table = re.search(r'<table id="emuleFile">.*?</table>', html, flags=re.S).group()
	links = re.findall(r'value="(ed2k://[^"]+)"', table)
	return links

@page_parser('http://www.icili.com/emule/download/')
def extend_link(url):
	links = icili_links(url)
	from lixian_hash_ed2k import parse_ed2k_file
	return [{'url':x, 'name':parse_ed2k_file(x)} for x in links]


########NEW FILE########
__FILENAME__ = kuai

from lixian_plugins.api import page_parser

import urllib
import re

def generate_lixian_url(info):
	print info['url']
	info = dict(info)
	info['namehex'] = '0102'
	info['fid'] = re.search(r'fid=([^&]+)', info['url']).group(1)
	info['tid'] = re.search(r'tid=([^&]+)', info['url']).group(1)
	info['internalid'] = '111'
	info['taskid'] = 'xxx'
	return 'http://gdl.lixian.vip.xunlei.com/download?fid=%(fid)s&mid=666&threshold=150&tid=%(tid)s&srcid=4&verno=1&g=%(gcid)s&scn=t16&i=%(gcid)s&t=1&ui=%(internalid)s&ti=%(taskid)s&s=%(size)s&m=0&n=%(namehex)s' % info

def parse_link(html):
	attrs = dict(re.findall(r'(\w+)="([^"]+)"', html))
	if 'file_url' not in attrs:
		return
	keys = {'url': 'file_url', 'name':'file_name', 'size':'file_size', 'gcid':'gcid', 'cid':'cid', 'gcid_resid':'gcid_resid'}
	info = {}
	for k in keys:
		info[k] = attrs[keys[k]]
	#info['name'] = urllib.unquote(info['name'])
	return info

@page_parser('http://kuai.xunlei.com/d/')
def kuai_links(url):
	assert url.startswith('http://kuai.xunlei.com/d/'), url
	html = urllib.urlopen(url).read().decode('utf-8')
	#return re.findall(r'file_url="([^"]+)"', html)
	#return map(parse_link, re.findall(r'<span class="f_w".*?</li>', html, flags=re.S))
	return filter(bool, map(parse_link, re.findall(r'<span class="c_1">.*?</span>', html, flags=re.S)))

extend_link = kuai_links

def main(args):
	from lixian_cli_parser import parse_command_line
	args = parse_command_line(args, [], ['name'])
	for x in args:
		for v in kuai_links(x):
			if args.name:
				print v['name']
			else:
				print v['url']


if __name__ == '__main__':
	import sys
	main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = qjwm

from lixian_plugins.api import page_parser

import urllib2
import re

def qjwm_link(url):
	assert re.match(r'http://.*\.qjwm\.com/down(load)?_\d+.html', url)
	url = url.replace('/down_', '/download_')
	html = urllib2.urlopen(url).read()
	m = re.search(r'var thunder_url = "([^"]+)";', html)
	if m:
		url = m.group(1)
		url = url.decode('gbk')
		return url


@page_parser('http://*.qjwm.com/*')
def extend_link(url):
	url = qjwm_link(url)
	return url and [url] or []


########NEW FILE########
__FILENAME__ = simplecd

from lixian_plugins.api import page_parser

import urllib2
import re


def simplecd_links(url):
	m = re.match(r'(http://(?:www\.)?s[ia]mplecd\.\w+/)(id|entry)/', url)
	assert m, url
	site = m.group(1)
	html = urllib2.urlopen(url).read()
	ids = re.findall(r'value="(\w+)"\s+name="selectemule"', html)
	form = '&'.join('rid=' + id for id in ids)
	q = 'mode=copy&' + form
	html = urllib2.urlopen(site + 'download/?' + q).read()
	table = re.search(r'<table id="showall" .*?</table>', html, flags=re.S).group()
	links = re.findall(r'ed2k://[^\s<>]+', table)
	import lixian_url
	return map(lixian_url.normalize_unicode_link, links)

@page_parser(['http://simplecd.*/',
              'http://www.simplecd.*/',
              'http://samplecd.*/',
              'http://www.samplecd.*/'])
def extend_link(url):
	links = simplecd_links(url)
	from lixian_hash_ed2k import parse_ed2k_file
	return [{'url':x, 'name':parse_ed2k_file(x)} for x in links]


########NEW FILE########
__FILENAME__ = verycd

from lixian_plugins.api import page_parser

import urllib2
import re

def parse_links(html):
	html = re.search(r'<!--eMule begin-->.*?<!--eMule end-->', html, re.S).group()
	links = re.findall(r'value="([^"]+)"', html)
	return [x for x in links if x.startswith('ed2k://')]

def verycd_links(url):
	assert url.startswith('http://www.verycd.com/topics/'), url
	return parse_links(urllib2.urlopen(url).read())

@page_parser('http://www.verycd.com/topics/')
def extend_link(url):
	links = verycd_links(url)
	from lixian_hash_ed2k import parse_ed2k_file
	return [{'url':x, 'name':parse_ed2k_file(x)} for x in links]


########NEW FILE########
__FILENAME__ = torrentz

from lixian_plugins.api import extract_info_hash_from_url

extract_info_hash_from_url(r'^http://torrentz.eu/([0-9a-f]{40})$')


########NEW FILE########
__FILENAME__ = lixian_progress

import sys

class SimpleProgressBar:
	def __init__(self):
		self.displayed = False
	def update(self, percent):
		self.displayed = True
		bar_size = 40
		percent *= 100.0
		if percent > 100:
			percent = 100.0
		dots = int(bar_size * percent / 100)
		plus = percent / 100 * bar_size - dots
		if plus > 0.8:
			plus = '='
		elif plus > 0.4:
			plus = '-'
		else:
			plus = ''
		percent = int(percent)
		bar = '=' * dots + plus
		bar = '{0:>3}%[{1:<40}]'.format(percent, bar)
		sys.stdout.write('\r'+bar)
		sys.stdout.flush()
	def done(self):
		if self.displayed:
			print
			self.displayed = False


########NEW FILE########
__FILENAME__ = lixian_queries

from lixian_query import ExactQuery
from lixian_query import SearchQuery
from lixian_query import query
from lixian_query import bt_query

import lixian_hash_bt
import lixian_url
import lixian_encoding

import re

##################################################
# queries
##################################################

class SingleTaskQuery(ExactQuery):
	def __init__(self, base, t):
		super(SingleTaskQuery, self).__init__(base)
		self.id = t['id']

	def query_once(self):
		return [self.base.get_task_by_id(self.id)]

	def query_search(self):
		t = self.base.find_task_by_id(self.id)
		return [t] if t else []


@query(priority=1)
@bt_query(priority=1)
def single_id_processor(base, x):
	if not re.match(r'^\d+/?$', x):
		return
	n = x.rstrip('/')
	t = base.find_task_by_id(n)
	if t:
		return SingleTaskQuery(base, t)

##################################################

class MultipleTasksQuery(ExactQuery):
	def __init__(self, base, tasks):
		super(MultipleTasksQuery, self).__init__(base)
		self.tasks = tasks

	def query_once(self):
		return map(self.base.get_task_by_id, (t['id'] for t in self.tasks))

	def query_search(self):
		return filter(bool, map(self.base.find_task_by_id, (t['id'] for t in self.tasks)))

@query(priority=1)
@bt_query(priority=1)
def range_id_processor(base, x):
	m = re.match(r'^(\d+)-(\d+)$', x)
	if not m:
		return
	begin = int(m.group(1))
	end = int(m.group(2))
	tasks = base.get_tasks()
	if begin <= end:
		found = filter(lambda x: begin <= x['#'] <= end, tasks)
	else:
		found = reversed(filter(lambda x: end <= x['#'] <= begin, tasks))
	if found:
		return MultipleTasksQuery(base, found)

##################################################

class SubTaskQuery(ExactQuery):
	def __init__(self, base, t, subs):
		super(SubTaskQuery, self).__init__(base)
		self.task = t
		self.subs = subs

	def query_once(self):
		task = dict(self.base.get_task_by_id(self.task['id']))
		files = self.base.get_files(task)
		task['files'] = self.subs
		return [task]

	def query_search(self):
		task = self.base.find_task_by_id(self.task['id'])
		if not task:
			return []
		task = dict(task)
		files = self.base.get_files(task)
		task['files'] = self.subs
		return [task]

@query(priority=2)
@bt_query(priority=2)
def sub_id_processor(base, x):
	x = lixian_encoding.from_native(x)

	m = re.match(r'^(\d+)/(.+)$', x)
	if not m:
		return
	task_id, sub_id = m.groups()
	task = base.find_task_by_id(task_id)
	if not task:
		return

	assert task['type'] == 'bt', 'task %s is not a bt task' % lixian_encoding.to_native(task['name'])
	files = base.get_files(task)
	import lixian_filter_expr
	files = lixian_filter_expr.filter_expr(files, sub_id)
	subs = [x for x in files]
	return SubTaskQuery(base, task, subs)

##################################################

class BtHashQuery(ExactQuery):
	def __init__(self, base, x):
		super(BtHashQuery, self).__init__(base)
		self.hash = re.match(r'^(?:bt://)?([0-9a-f]{40})$', x, flags=re.I).group(1).lower()
		self.task = self.base.find_task_by_hash(self.hash)

	def prepare(self):
		if not self.task:
			self.base.add_bt_task_by_hash(self.hash)

	def query_once(self):
		t = self.base.find_task_by_hash(self.hash)
		assert t, 'Task not found: bt://' + self.hash
		return [t]

	def query_search(self):
		t = self.base.find_task_by_hash(self.hash)
		return [t] if t else []

@query(priority=1)
@bt_query(priority=1)
def bt_hash_processor(base, x):
	if re.match(r'^(bt://)?[0-9a-f]{40}$', x, flags=re.I):
		return BtHashQuery(base, x)

##################################################

class LocalBtQuery(ExactQuery):
	def __init__(self, base, x):
		super(LocalBtQuery, self).__init__(base)
		self.path = x
		self.hash = lixian_hash_bt.info_hash(self.path)
		self.task = self.base.find_task_by_hash(self.hash)
		with open(self.path, 'rb') as stream:
			self.torrent = stream.read()

	def prepare(self):
		if not self.task:
			self.base.add_bt_task_by_content(self.torrent, self.path)

	def query_once(self):
		t = self.base.find_task_by_hash(self.hash)
		assert t, 'Task not found: bt://' + self.hash
		return [t]

	def query_search(self):
		t = self.base.find_task_by_hash(self.hash)
		return [t] if t else []

@query(priority=1)
@bt_query(priority=1)
def local_bt_processor(base, x):
	import os.path
	if x.lower().endswith('.torrent') and os.path.exists(x):
		return LocalBtQuery(base, x)

##################################################

class MagnetQuery(ExactQuery):
	def __init__(self, base, x):
		super(MagnetQuery, self).__init__(base)
		self.url = x
		self.hash = lixian_hash_bt.magnet_to_infohash(x).encode('hex').lower()
		self.task = self.base.find_task_by_hash(self.hash)

	def prepare(self):
		if not self.task:
			self.base.add_magnet_task(self.url)

	def query_once(self):
		t = self.base.find_task_by_hash(self.hash)
		assert t, 'Task not found: bt://' + self.hash
		return [t]

	def query_search(self):
		t = self.base.find_task_by_hash(self.hash)
		return [t] if t else []

@query(priority=4)
@bt_query(priority=4)
def magnet_processor(base, url):
	if re.match(r'magnet:', url):
		return MagnetQuery(base, url)

##################################################

class BatchUrlsQuery(ExactQuery):
	def __init__(self, base, urls):
		super(BatchUrlsQuery, self).__init__(base)
		self.urls = urls

	def prepare(self):
		for url in self.urls:
			if not self.base.find_task_by_url(url):
				self.base.add_url_task(url)

	def query_once(self):
		return map(self.base.get_task_by_url, self.urls)

	def query_search(self):
		return filter(bool, map(self.base.find_task_by_url, self.urls))

@query(priority=6)
@bt_query(priority=6)
def url_extend_processor(base, url):
	import lixian_plugins.parsers
	extended = lixian_plugins.parsers.try_to_extend_link(url)
	if extended:
		extended = map(lixian_plugins.parsers.to_url, extended)
		return BatchUrlsQuery(base, extended)

##################################################

class UrlQuery(ExactQuery):
	def __init__(self, base, x):
		super(UrlQuery, self).__init__(base)
		self.url = lixian_url.url_unmask(x)
		self.task = self.base.find_task_by_url(self.url)

	def prepare(self):
		if not self.task:
			self.base.add_url_task(self.url)

	def query_once(self):
		t = self.base.find_task_by_url(self.url)
		assert t, 'Task not found: ' + self.url
		return [t]

	def query_search(self):
		t = self.base.find_task_by_url(self.url)
		return [t] if t else []

@query(priority=7)
def url_processor(base, url):
	if re.match(r'\w+://', url):
		return UrlQuery(base, url)

##################################################

class BtUrlQuery(ExactQuery):
	def __init__(self, base, url, torrent):
		super(BtUrlQuery, self).__init__(base)
		self.url = url
		self.torrent = torrent
		self.hash = lixian_hash_bt.info_hash_from_content(self.torrent)
		self.task = self.base.find_task_by_hash(self.hash)

	def prepare(self):
		if not self.task:
			self.base.add_bt_task_by_content(self.torrent, self.url)

	def query_once(self):
		t = self.base.find_task_by_hash(self.hash)
		assert t, 'Task not found: bt://' + self.hash
		return [t]

	def query_search(self):
		t = self.base.find_task_by_hash(self.hash)
		return [t] if t else []

@bt_query(priority=7)
def bt_url_processor(base, url):
	if not re.match(r'http://', url):
		return
	print 'Downloading torrent file from', url
	import urllib2
	response = urllib2.urlopen(url, timeout=60)
	torrent = response.read()
	if response.info().get('Content-Encoding') == 'gzip':
		def ungzip(s):
			from StringIO import StringIO
			import gzip
			buffer = StringIO(s)
			f = gzip.GzipFile(fileobj=buffer)
			return f.read()
		torrent = ungzip(torrent)
	return BtUrlQuery(base, url, torrent)

##################################################

class FilterQuery(SearchQuery):
	def __init__(self, base, x):
		super(FilterQuery, self).__init__(base)
		self.keyword = x

	def query_search(self):
		import lixian_plugins.filters
		tasks = lixian_plugins.filters.filter_tasks(self.base.get_tasks(), self.keyword)
		assert tasks is not None
		return tasks

@query(priority=8)
@bt_query(priority=8)
def filter_processor(base, x):
	import lixian_plugins.filters
	if lixian_plugins.filters.has_task_filter(x):
		return FilterQuery(base, x)

##################################################

class DefaultQuery(SearchQuery):
	def __init__(self, base, x):
		super(DefaultQuery, self).__init__(base)
		self.text = lixian_encoding.from_native(x)

	def query_search(self):
		return filter(lambda t: t['name'].lower().find(self.text.lower()) != -1, self.base.get_tasks())

@query(priority=9)
@bt_query(priority=9)
def default_processor(base, x):
	return DefaultQuery(base, x)


########NEW FILE########
__FILENAME__ = lixian_query

__all__ = ['query', 'bt_query', 'user_query', 'Query', 'ExactQuery', 'SearchQuery',
           'build_query', 'find_tasks_to_download', 'search_tasks', 'expand_bt_sub_tasks']

import lixian_hash_bt
import lixian_hash_ed2k
import lixian_encoding


def link_normalize(url):
	from lixian_url import url_unmask, normalize_unicode_link
	url = url_unmask(url)
	if url.startswith('magnet:'):
		return 'bt://'+lixian_hash_bt.magnet_to_infohash(url).encode('hex')
	elif url.startswith('ed2k://'):
		return lixian_hash_ed2k.parse_ed2k_id(url)
	elif url.startswith('bt://'):
		return url.lower()
	elif url.startswith('http://') or url.startswith('ftp://'):
		return normalize_unicode_link(url)
	return url

def link_equals(x1, x2):
	return link_normalize(x1) == link_normalize(x2)


class TaskBase(object):
	def __init__(self, client, list_tasks, limit=None):
		self.client = client
		self.fetch_tasks_unlimited = list_tasks
		self.limit = limit

		self.queries = []

		self.tasks = None
		self.files = {}

		self.commit_jobs = [[], []]

		self.download_jobs = []

	def fetch_tasks(self):
		if self.limit:
			with self.client.attr(limit=self.limit):
				return self.fetch_tasks_unlimited()
		else:
			return self.fetch_tasks_unlimited()

	def register_queries(self, queries):
		self.queries += queries

	def unregister_query(self, query):
		self.queries.remove(query)

	def get_tasks(self):
		if self.tasks is None:
			self.tasks = self.fetch_tasks()
		return self.tasks

	def refresh_tasks(self):
		self.tasks = self.fetch_tasks()
		return self.tasks

	def get_files(self, task):
		assert isinstance(task, dict), task
		id = task['id']
		if id in self.files:
			return self.files[id]
		self.files[id] = self.client.list_bt(task)
		return self.files[id]

	def find_task_by_id(self, id):
		assert isinstance(id, basestring), repr(id)
		for t in self.get_tasks():
			if t['id'] == str(id) or t['#'] == int(id):
				return t

	def get_task_by_id(self, id):
		t = self.find_task_by_id(id)
		if not t:
			raise Exception('No task found for id '+id)
		return t

	def find_task_by_hash(self, hash):
		for t in self.get_tasks():
			if t['type'] == 'bt' and t['bt_hash'].lower() == hash:
				return t

	def find_task_by_url(self, url):
		for t in self.get_tasks():
			if link_equals(t['original_url'], url):
				return t

	def get_task_by_url(self, url):
		t = self.find_task_by_url(url)
		if not t:
			raise Exception('No task found for ' + lixian_encoding.to_native(url))
		return t

	def add_url_task(self, url):
		self.commit_jobs[0].append(url)

	def add_bt_task_by_hash(self, hash):
		self.commit_jobs[1].append(['hash', hash])

	def add_bt_task_by_content(self, content, name):
		self.commit_jobs[1].append(['content', (content, name)])

	def add_magnet_task(self, hash):
		self.commit_jobs[1].append(['magnet', hash])

	def commit(self):
		urls, bts = self.commit_jobs
		if urls:
			self.client.add_batch_tasks(map(lixian_encoding.try_native_to_utf_8, urls))
		for bt_type, value in bts:
			if bt_type == 'hash':
				print 'Adding bt task', value # TODO: print the thing user inputs (may be not hash)
				self.client.add_torrent_task_by_info_hash(value)
			elif bt_type == 'content':
				content, name = value
				print 'Adding bt task', name
				self.client.add_torrent_task_by_content(content)
			elif bt_type == 'magnet':
				print 'Adding magnet task', value # TODO: print the thing user inputs (may be not hash)
				self.client.add_task(value)
			else:
				raise NotImplementedError(bt_type)
		self.commit_jobs = [[], []]
		self.refresh_tasks()

	def prepare(self):
		# prepare actions (e.g. add tasks)
		for query in self.queries:
			query.prepare()
		# commit and refresh task list
		self.commit()

	def query_complete(self):
		for query in list(self.queries):
			query.query_complete()

	def merge_results(self):
		tasks = merge_tasks(self.download_jobs)
		for t in tasks:
			if t['type'] == 'bt':
				# XXX: a dirty trick to cache requests
				t['base'] = self
		self.download_jobs = tasks

	def query_once(self):
		self.prepare()
		# merge results
		for query in self.queries:
			self.download_jobs += query.query_once()
		self.query_complete()
		self.merge_results()

	def query_search(self):
		for query in self.queries:
			self.download_jobs += query.query_search()
		self.merge_results()

	def peek_download_jobs(self):
		return self.download_jobs

	def pull_completed(self):
		completed = []
		waiting = []
		for t in self.download_jobs:
			if t['status_text'] == 'completed':
				completed.append(t)
			elif t['type'] != 'bt':
				waiting.append(t)
			elif 'files' not in t:
				waiting.append(t)
			else:
				i_completed = []
				i_waiting = []
				for f in t['files']:
					if f['status_text'] == 'completed':
						i_completed.append(f)
					else:
						i_waiting.append(f)
				if i_completed:
					tt = dict(t)
					tt['files'] = i_completed
					completed.append(tt)
				if i_waiting:
					tt = dict(t)
					tt['files'] = i_waiting
					waiting.append(tt)
		self.download_jobs = waiting
		return completed

	def refresh_status(self):
		self.refresh_tasks()
		self.files = {}
		tasks = []
		for old_task in self.download_jobs:
			new_task = dict(self.get_task_by_id(old_task['id']))
			if 'files' in old_task:
				files = self.get_files(new_task)
				new_task['files'] = [files[f['index']] for f in old_task['files']]
			tasks.append(new_task)
		self.download_jobs = tasks

class Query(object):
	def __init__(self, base):
		self.bind(base)

	def bind(self, base):
		self.base = base
		self.client = base.client
		return self

	def unregister(self):
		self.base.unregister_query(self)

	def prepare(self):
		pass

	def query_once(self):
		raise NotImplementedError()

	def query_complete(self):
		raise NotImplementedError()

	def query_search(self):
		raise NotImplementedError()

class ExactQuery(Query):
	def __init__(self, base):
		super(ExactQuery, self).__init__(base)

	def query_once(self):
		raise NotImplementedError()

	def query_complete(self):
		self.unregister()

	def query_search(self):
		raise NotImplementedError()

class SearchQuery(Query):
	def __init__(self, base):
		super(SearchQuery, self).__init__(base)

	def query_once(self):
		return self.query_search()

	def query_complete(self):
		pass

	def query_search(self):
		raise NotImplementedError()

##################################################
# register
##################################################

processors = []

bt_processors = []

# 0
# 1 -- builtin -- most
# 2 -- subs -- 0/[0-9]
# 4 -- magnet
# 5 -- user
# 6 -- extend url
# 7 -- plain url, bt url
# 8 -- filter
# 9 -- default -- text search

def query(priority):
	assert isinstance(priority, (int, float))
	def register(processor):
		processors.append((priority, processor))
		return processor
	return register

def bt_query(priority):
	assert isinstance(priority, (int, float))
	def register(processor):
		bt_processors.append((priority, processor))
		return processor
	return register

def user_query(processor):
	return query(priority=5)(processor)

def load_default_queries():
	import lixian_queries


##################################################
# query
##################################################

def to_list_tasks(client, args):
	if args.category:
		return lambda: client.read_all_tasks_by_category(args.category)
	elif args.deleted:
		return client.read_all_deleted
	elif args.expired:
		return client.read_all_expired
	elif args.completed:
		return client.read_all_tasks
	elif args.failed:
		return client.read_all_tasks
	elif args.all:
		return client.read_all_tasks
	else:
		return client.read_all_tasks

def to_query(base, arg, processors):
	for _, process in sorted(processors):
		q = process(base, arg)
		if q:
			return q
	raise NotImplementedError('No proper query process found for: ' + arg)

def merge_files(files1, files2):
	ids = []
	files = []
	for f in files1 + files2:
		if f['id'] not in ids:
			files.append(f)
			ids.append(f['id'])
	return files

def merge_tasks(tasks):
	result_tasks = []
	task_mapping = {}
	for task in tasks:
		assert type(task) == dict, repr(type)
		id = task['id']
		assert 'index' not in task
		if id in task_mapping:
			if 'files' in task and 'files' in task_mapping[id]:
				task_mapping[id]['files'] = merge_files(task_mapping[id]['files'], task['files'])
		else:
			if 'files' in task:
				t = dict(task)
				result_tasks.append(t)
				task_mapping[id] = t
			else:
				result_tasks.append(task)
				task_mapping[id] = task
	return result_tasks

class AllQuery(SearchQuery):
	def __init__(self, base):
		super(AllQuery, self).__init__(base)
	def query_search(self):
		return self.base.get_tasks()

class CompletedQuery(SearchQuery):
	def __init__(self, base):
		super(CompletedQuery, self).__init__(base)
	def query_search(self):
		return filter(lambda x: x['status_text'] == 'completed', self.base.get_tasks())

class FailedQuery(SearchQuery):
	def __init__(self, base):
		super(FailedQuery, self).__init__(base)
	def query_search(self):
		return filter(lambda x: x['status_text'] == 'failed', self.base.get_tasks())

class NoneQuery(SearchQuery):
	def __init__(self, base):
		super(NoneQuery, self).__init__(base)
	def query_search(self):
		return []

def default_query(options):
	if options.category:
		return AllQuery
	elif options.deleted:
		return AllQuery
	elif options.expired:
		return AllQuery
	elif options.completed:
		return CompletedQuery
	elif options.failed:
		return FailedQuery
	elif options.all:
		return AllQuery
	else:
		return NoneQuery

def parse_queries(base, args):
	return [to_query(base, arg, bt_processors if args.torrent else processors) for arg in args] or [default_query(args)(base)]

def parse_limit(args):
	limit = args.limit
	if limit:
		limit = int(limit)
	ids = []
	for x in args:
		import re
		if re.match(r'^\d+$', x):
			ids.append(int(x))
		elif re.match(r'^(\d+)/', x):
			ids.append(int(x.split('/')[0]))
		elif re.match(r'^(\d+)-(\d+)$', x):
			ids.extend(map(int, x.split('-')))
		else:
			return limit
	if ids and limit:
		return min(max(ids)+1, limit)
	elif ids:
		return max(ids)+1
	else:
		return limit

def build_query(client, args):
	if args.input:
		import fileinput
		args._left.extend(line.strip() for line in fileinput.input(args.input) if line.strip())
	load_default_queries() # IMPORTANT: init default queries
	limit = parse_limit(args)
	base = TaskBase(client, to_list_tasks(client, args), limit)
	base.register_queries(parse_queries(base, args))
	return base

##################################################
# compatible APIs
##################################################

def find_tasks_to_download(client, args):
	base = build_query(client, args)
	base.query_once()
	return base.peek_download_jobs()

def search_tasks(client, args):
	base = build_query(client, args)
	base.query_search()
	return base.peek_download_jobs()

def expand_bt_sub_tasks(task):
	files = task['base'].get_files(task) # XXX: a dirty trick to cache requests
	not_ready = []
	single_file = False
	if len(files) == 1 and files[0]['name'] == task['name']:
		single_file = True
	if 'files' in task:
		ordered_files = []
		for t in task['files']:
			assert isinstance(t, dict)
			if t['status_text'] != 'completed':
				not_ready.append(t)
			else:
				ordered_files.append(t)
		files = ordered_files
	return files, not_ready, single_file


##################################################
# simple helpers
##################################################

def get_task_by_id(client, id):
	base = TaskBase(client, client.read_all_tasks)
	return base.get_task_by_id(id)

def get_task_by_any(client, arg):
	import lixian_cli_parser
	tasks = search_tasks(client, lixian_cli_parser.parse_command_line([arg]))
	if not tasks:
		raise LookupError(arg)
	if len(tasks) > 1:
		raise LookupError('Too many results for ' + arg)
	return tasks[0]


########NEW FILE########
__FILENAME__ = lixian_url

import base64
import urllib

def xunlei_url_encode(url):
	return 'thunder://'+base64.encodestring('AA'+url+'ZZ').replace('\n', '')

def xunlei_url_decode(url):
	assert url.startswith('thunder://')
	url = base64.decodestring(url[10:])
	assert url.startswith('AA') and url.endswith('ZZ')
	return url[2:-2]

def flashget_url_encode(url):
	return 'Flashget://'+base64.encodestring('[FLASHGET]'+url+'[FLASHGET]').replace('\n', '')

def flashget_url_decode(url):
	assert url.startswith('Flashget://')
	url = base64.decodestring(url[11:])
	assert url.startswith('[FLASHGET]') and url.endswith('[FLASHGET]')
	return url.replace('[FLASHGET]', '')

def flashgetx_url_decode(url):
	assert url.startswith('flashgetx://|mhts|')
	name, size, hash, end = url.split('|')[2:]
	assert end == '/'
	return 'ed2k://|file|'+base64.decodestring(name)+'|'+size+'|'+hash+'/'

def qqdl_url_encode(url):
	return 'qqdl://' + base64.encodestring(url).replace('\n', '')

def qqdl_url_decode(url):
	assert url.startswith('qqdl://')
	return base64.decodestring(url[7:])

def url_unmask(url):
	if url.startswith('thunder://'):
		return normalize_unicode_link(xunlei_url_decode(url))
	elif url.startswith('Flashget://'):
		return flashget_url_decode(url)
	elif url.startswith('flashgetx://'):
		return flashgetx_url_decode(url)
	elif url.startswith('qqdl://'):
		return qqdl_url_decode(url)
	else:
		return url

def normalize_unicode_link(url):
	import re
	def escape_unicode(m):
		c = m.group()
		if ord(c) < 0x80:
			return c
		else:
			return urllib.quote(c.encode('utf-8'))
	def escape_str(m):
		c = m.group()
		if ord(c) < 0x80:
			return c
		else:
			return urllib.quote(c)
	if type(url) == unicode:
		return re.sub(r'.', escape_unicode, url)
	else:
		return re.sub(r'.', escape_str, url)

def unquote_url(x):
	x = urllib.unquote(x)
	if type(x) != str:
		return x
	try:
		return x.decode('utf-8')
	except UnicodeDecodeError:
		return x.decode('gbk') # can't decode in utf-8 and gbk


########NEW FILE########
__FILENAME__ = lixian_util

__all__ = []

import re

def format_1d(n):
	return re.sub(r'\.0*$', '', '%.1f' % n)

def format_size(n):
	if n < 1000:
		return '%sB' % n
	elif n < 1000**2:
		return '%sK' % format_1d(n/1000.)
	elif n < 1000**3:
		return '%sM' % format_1d(n/1000.**2)
	elif n < 1000**4:
		return '%sG' % format_1d(n/1000.**3)


def parse_size(size):
	size = str(size)
	if re.match('^\d+$', size):
		return int(size)
	m = re.match(r'^(\d+(?:\.\d+)?)(K|M|G)B?$', size, flags=re.I)
	if not m:
		raise Exception("Invalid size format: %s" % size)
	return int(float(m.group(1)) * {'K': 1000, 'M': 1000*1000, 'G': 1000*1000*1000}[m.group(2).upper()])



########NEW FILE########
__FILENAME__ = lixian_verification_code

def file_path_verification_code_reader(path):
	def reader(image):
		with open(path, 'wb') as output:
			output.write(image)
		print 'Verification code picture is saved to %s, please open it manually and enter what you see.' % path
		code = raw_input('Verification code: ')
		return code
	return reader

def default_verification_code_reader(args):
	if args.verification_code_path:
		return file_path_verification_code_reader(args.verification_code_path)

########NEW FILE########
