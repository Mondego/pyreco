__FILENAME__ = crawl_proxies
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s-[%(asctime)s][%(module)s][%(funcName)s][%(lineno)d]: %(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

import argparse, pickle, os, json, sys, time
sys.path.append("..")

def crawl_spys_ru(page):

	import requests, re, lxml.html, cStringIO
	from lxml import etree
	url = 'http://spys.ru/en/http-proxy-list/%d/'%page

	# payload = {
	# 	'sto': 'View+150+per+page'
	# }
	r = requests.get(url)

	html = r.text.encode('utf8')

	# the port numbers are coded...
	coded = re.findall(r'<\/table><script type="text\/javascript">(.*?)<\/script>', html)[0]
	xx = coded.split(';')
	for x in xx:
		exec(x)

	proxies = []

	ms = re.findall(r'<tr\sclass=spy1x.*?<\/tr>', html)
	#logger.info(len(ms))
	for m in ms:
		#logger.info(m)
		tr = lxml.html.fragment_fromstring(m)
		tds = tr.findall("td")

		if (len(tds) > 1):

			proxy = None
			proxy_type = None
			country = None
			cnt = 0
		# logger.info(len(tds))
			for td in tds:
				text = td.text_content().encode("utf8")
				if (text == 'Proxy address:port'):
					break

				if cnt == 0:
					hh = lxml.html.tostring(td)
					ip = re.findall(r'<font\sclass="spy14">(.*?)<script', hh)[0]

					pp = re.findall(r'\(([^"]*?)\)', hh)
					
					port = ""
					for p in pp:
						port += str(eval(p))

					proxy = '%s:%s'%(ip, port)
					

				if cnt == 1:
					proxy_type = text.lower()

				if cnt == 3:
					hh = lxml.html.tostring(td)
					country = re.findall(r'<font class="spy14">(.*?)<\/font>', hh)[0]

				cnt += 1

				if cnt > 3:
					break

			if (proxy and proxy_type == 'http'):
				#proxies.append((proxy, proxy_type, country))
				proxies.append({proxy: proxy_type})

	return proxies
		

from tweetf0rm.proxies import proxy_checker

if __name__=="__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument('-o', '--output', help="define the location of the output;", default="proxies.json")
	args = parser.parse_args()
	
	proxies = []
	for i in range(5):
		proxies.extend(crawl_spys_ru(i))

	# check if there is a proxies.json locally, merge the check results rather than overwrite it
	if (os.path.exists(os.path.abspath(args.output))):
		with open(os.path.abspath(args.output), 'rb') as proxy_f:
			proxies.extend(json.load(proxy_f)['proxies'])


	ips = []
	proxy_list = []
	for proxy in proxies:
		ip = proxy.keys()[0]
		proxy_type = proxy.values()[0]

		if (ip not in ips):
			ips.append(ip)
			proxy_list.append({ip: proxy_type})


	proxies = [p['proxy'] for p in proxy_checker(proxy_list)]

	logger.info("number of proxies that are still alive: %d"%len(proxies))
	with open(os.path.abspath(args.output), 'wb') as proxy_f:
		json.dump({'proxies':proxies}, proxy_f)
	

			



########NEW FILE########
__FILENAME__ = trim_proxies
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s-[%(asctime)s][%(module)s][%(funcName)s][%(lineno)d]: %(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

import argparse, pickle, os, json, sys, time
sys.path.append("..")


from tweetf0rm.proxies import proxy_checker

if __name__=="__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--proxies', help="define the location of the output;", default="proxies.json")
	args = parser.parse_args()
	
	with open(os.path.abspath(args.proxies), 'rb') as proxy_f:
		proxies = json.load(proxy_f)['proxies']
		
		proxies = [proxy['proxy'] for proxy in proxy_checker(proxies)]

		logger.info('%d live proxies left'%(len(proxies)))

		with open(os.path.abspath(args.proxies), 'wb') as proxy_f:
			json.dump({'proxies':proxies}, proxy_f)
	

			



########NEW FILE########
__FILENAME__ = crawl_user_networks
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

import argparse, pickle, os, json, sys, time

MAX_RETRY_CNT = 5

sys.path.append("..")
from tweetf0rmer.user_farm import UserFarm

def farm_user_network(apikeys=None, seeds= [], depth=3, output_folder='./user_network', network_type='followers'):

	output_folder = os.path.abspath('%s/%s'%(output_folder, network_type))
	user_farm = UserFarm(apikeys=apikeys, verbose=False, output_folder=output_folder)
	
	progress = {}
	try:
		with open('progress.pickle', 'rb') as pf:
			progress = pickle.load(pf)
	except:
		pass

	try:
		depth = max(progress.keys())

		logger.info('resume from depth: %d'%(depth))
	except:
		pass

	try:
		
		#get user id first
		user_ids = user_farm.get_user_ids(seeds)

		progress[depth] = user_ids

		logger.info("number of seeds: %d"%len(user_ids))

		while depth > 0 and len(user_ids) > 0:
			time.sleep(5)
			progress[depth-1] = set()

			while len(progress[depth]) > 0:

				user_id = progress[depth].pop()

				logger.info("fetching %s of %d"%(network_type, user_id))

				if os.path.exists(os.path.abspath('%s/%s'%(output_folder, user_id))):
					logger.info("%d already fetched... pass"%user_id)
					continue

				retry = False
				retry_cnt = MAX_RETRY_CNT
				while True:
					try:
						if network_type == 'friends':
							f_ids = user_farm.find_all_friends(user_id)
						else:
							f_ids = user_farm.find_all_followers(user_id)

						retry = False
						retry_cnt = MAX_RETRY_CNT
						if depth - 1 > 0:
							progress[depth-1].update(f_ids)
					except:
						retry = True
						retry_cnt -= 1
						time.sleep(60)
						logger.info("retries remaining if failed %d"%(retry_cnt))

					if not retry or retry_cnt == 0:
						break

				# retry failed
				if retry and retry_cnt == 0:
					# add unprocessed back to the queue
					progress[depth].add(user_id)

			logger.info('finish depth: %d'%(depth))

			depth -= 1

	except KeyboardInterrupt:
		print()
		logger.error('You pressed Ctrl+C!')
		raise
	except:		
		raise
	finally:
		user_farm.close()
		with open('progress.pickle', 'wb') as pf:
			pickle.dump(progress, pf)


if __name__=="__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument('-a', '--apikeys', help="config file for twitter api keys (json format); twitter requires you to have an account to crawl;", required = True)
	parser.add_argument('-c', '--crawler', help="the crawler identifier; you can have multiple crawler accounts set in the apikeys.json; pick one", required = True)
	parser.add_argument('-s', '--seeds', help="the config file for defining seed users and depth; see crawl_user_networks.json as an example", required = True)
	parser.add_argument('-o', '--output', help="define the location of the output", required = True)
	parser.add_argument('-nt', '--network_type', help='either [friends] or [followers]; default to farm followers', default='followers')
	args = parser.parse_args()
	
	with open(os.path.abspath(args.apikeys), 'rb') as apikeys_f, open(os.path.abspath(args.seeds), 'rb') as config_f:
		import json, os
		apikeys_config = json.load(apikeys_f)
		apikeys = apikeys_config.get(args.crawler, None)
		config = json.load(config_f)

		seeds = config['seeds'] if 'seeds' in config else []
		depth = int(config.get('depth', 3)) # by default only fetch 3 layers

		farm_user_network(apikeys, seeds, depth, args.output, args.network_type)
			



########NEW FILE########
__FILENAME__ = crawl_user_timelines
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

import argparse, pickle, os, json, sys, time
sys.path.append("..")
from tweetf0rmer.user_farm import UserFarm
from tweetf0rmer.utils import full_stack

# there isn't much try and fail done yet
def farm_user_timelines(apikeys, seeds, output_folder):

	user_farm = UserFarm(apikeys=apikeys, verbose=False, output_folder=os.path.abspath(output_folder))

	try:
		#get user id first
		user_ids = user_farm.get_user_ids(seeds)

		for user_id in user_ids:
			# current it skips the user if the result file is already there. Obviously this is not reliable since the error could raise when only half of the tweets for an user is finished... this will mean losing the other half for this user... but my current use case doesn't really care... since I have millions of users to worry about, losing one isn't that big of deal... but certainly needs a better way to track progress
			if not os.path.exists(os.path.abspath('%s/%s'%(output_folder, user_id))):
				user_farm.user_timeline(user_id)
	except KeyboardInterrupt:
		logger.warn('You pressed Ctrl+C!')
		raise
	except:		
		raise
	finally:
		user_farm.close()

if __name__=="__main__":
	

	parser = argparse.ArgumentParser()
	parser.add_argument('-a', '--apikeys', help="config file for twitter api key (json format)", required = True)
	parser.add_argument('-c', '--crawler', help="the crawler identifier; you can have multiple crawler accounts set in the apikeys.json; pick one", required = True)
	parser.add_argument('-s', '--seeds', help="the list of users you want to crawl their timelines; see crawl_user_timelines.json as an example", required = True)
	parser.add_argument('-o', '--output', help="define the location of the output (each user's timeline will be in its own file under this output folder identified by the user id", required = True)
	args = parser.parse_args()
	
	with open(os.path.abspath(args.apikeys), 'rb') as apikeys_f, open(os.path.abspath(args.seeds), 'rb') as config_f:
		import json, os
		apikeys_config = json.load(apikeys_f)
		apikeys = apikeys_config.get(args.crawler, None)
		config = json.load(config_f)

		seeds = config['seeds'] if 'seeds' in config else []
		
		while True:				
			try:
				farm_user_timelines(apikeys, seeds, args.output)
			except KeyboardInterrupt:
				logger.warn('You pressed Ctrl+C!')
				sys.exit(0)
			except:
				logger.error(full_stack())
				logger.info('failed, retry')
				time.sleep(10)
		
			



########NEW FILE########
__FILENAME__ = track_keywords
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

import argparse, pickle, os, json, sys, time

sys.path.append("..")
from tweetf0rmer.stream import KeywordsStreamer
from tweetf0rmer.utils import full_stack

def track_keywords(apikeys, keywords, output):

	stream = KeywordsStreamer(apikeys=apikeys, verbose=True, output=os.path.abspath(output))

	try:
		stream.statuses.filter(track=keywords, language='en')
	except:
		raise
	finally:
		stream.close()

if __name__=="__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument('-a', '--apikeys', help="config file for twitter api keys (json format); twitter requires you to have an account to crawl;", required = True)
	parser.add_argument('-c', '--crawler', help="the crawler identifier; you can have multiple crawler accounts set in the apikeys.json; pick one", required = True)
	parser.add_argument('-k', '--keywords', help="define the location of the keywords.json file", required = True)
	parser.add_argument('-o', '--output', help="define the location of the output; crawled tweets are organized by timestamp in this folder;", required = True)
	args = parser.parse_args()
	
	with open(os.path.abspath(args.apikeys), 'rb') as apikeys_f, open(os.path.abspath(args.keywords), 'rb') as keywords_f:
		import json, os
		apikeys_config = json.load(apikeys_f)
		apikeys = apikeys_config.get(args.crawler, None)

		if not apikeys:
			raise Exception("what's the point? Make sure you have all the api keys set in the config file...")

		keywords = json.load(keywords_f)

		keywords = keywords['keywords']

		logger.info('tracking %d keywords'%(len(keywords)))
			
		while True:				
			try:
				track_keywords(apikeys, keywords, args.output)
			except KeyboardInterrupt:
				logger.error('You pressed Ctrl+C!')
				sys.exit(0)
			except:
				logger.error(full_stack())
				logger.info('failed, retry')
				time.sleep(10)

			



########NEW FILE########
__FILENAME__ = twitter_crawler
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
	This script automate the crawling of users, and their twitter timeline 
	It starts with a list of seed users, and crawl 3-layers (friends of a seed user are on the first level; and friends of the friends are on the second level)
	It's input is the:
		apikeys:
		config: config of the seed users as well as the config file for tracking the progress, if it's non-exist; it will start from the beginning and save its progress to this file
		output: the output folder of each run;

	The system can also generate a snapshot of the current progress if exceptions happens, and the system can resume from the config file (json) 
'''

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

import argparse, pickle, os, json, sys, multiprocessing, time, shutil

sys.path.append("..")
from tweetf0rmer.user_farm import UserFarm

MAX_QUEUE_SIZE = 32767 # On mac... 
MAX_RETRY = 10
RETRY_SLEEP = 60

def farm_user_timelines(apikeys, user_timeline_queue, output_folder='./farm/'):

	timelines_output_folder = os.path.abspath('%s/timelines/'%(output_folder)) # by user id

	user_timelines_farmer = UserFarm(apikeys=apikeys, verbose=False, output_folder=timelines_output_folder)

	current_user_id = 0

	retry = False

	problem_queue = []

	while current_user_id != -1:
		time.sleep(10)
		if retry and retry_cnt > 0:
			time.sleep(RETRY_SLEEP)
			user_timelines_farmer.write_to_handler.delete(current_user_id)
			retury = False
			retry_cnt -= 1
		else:
			current_user_id = user_timeline_queue.get(True) # will block and wait for the next user_id
			#logger.info("timeline queue size: %d"%(user_timeline_queue.qsize())) no qsize() function on mac os x
			if current_user_id == -1:
				if len(problem_queue) > 0: #have issues with a few user_id, we try to add them back to the queue to retry
					# add this point, the queue should be empty; so no need to worry about block on the put
					for uid in problem_queue:
						user_timeline_queue.put(uid, block=True)

					# get one to continue the process
					current_user_id = user_timeline_queue.get(True)
				else:
					break#continue

			logger.info('retrieving timeline for: %d'%(current_user_id))
			retry_cnt = MAX_RETRY

		try:
			if not os.path.exists(os.path.abspath('%s/%s'%(timelines_output_folder, current_user_id))):
				user_timelines_farmer.user_timeline(current_user_id)

		except:
			logger.warn("exception; retry: %d"%(retry_cnt))
			retry = True
			# note the problem, but don't die; move onto the next; and push this to the back of the current queue
			user_timeline_queue.put(user_id, block=True)
		finally:
			user_timelines_farmer.close()
			

	# notify -1
	user_timelines_farmer.close()

	return True

def farm_user_network(apikeys, config = {}, output_folder='./farm/', network_type="followers"):

	network_output_folder = os.path.abspath('%s/%s/'%(output_folder, network_type)) # by user id

	shutil.rmtree(network_output_folder, True)

	user_network_farmer = UserFarm(apikeys=apikeys, verbose=False, output_folder=network_output_folder)
	
	seeds = config['seeds'] if 'seeds' in config else []
	depth = int(config.get('depth', 3)) # by default only fetch 3 layers

	#progress = config.get('progress', {})

	#current_depth = progress.get('current_depth', 0) # start from the first layer
	#queue = progess.get('queue', {})
	#queue = queue if type(queue) is dict else raise Exception("the queue must be a dict, see twitter_crawler_config.json as an example")

	user_timeline_queue = multiprocessing.Queue(maxsize=MAX_QUEUE_SIZE)

	p = multiprocessing.Process(target=farm_user_timelines, args=(apikeys, user_timeline_queue, output_folder))
	p.start()
	# get user_ids for the seeds
	user_network_queue = user_network_farmer.get_user_ids(seeds)

	try:
		#get user id first 
		while depth > 0 and len(user_network_queue) > 0:
			temp_user_network_queue = set()

			for user_id in user_network_queue:
				time.sleep(5)
				if network_type == 'friends':
					f_ids = user_network_farmer.find_all_friends(user_id)
				else:
					f_ids = user_network_farmer.find_all_followers(user_id)

				logger.info('user_id: %d has %d friends'%(user_id, len(f_ids)))

				for f_id in f_ids:
					user_timeline_queue.put(f_id, block=True)
					temp_user_network_queue.add(f_id)
					user_network_farmer.close() # force flush once 

			logger.info('finish depth: %d'%(depth))

			depth -= 1
	 		user_network_queue = temp_user_network_queue

	except KeyboardInterrupt:
		print()
		logger.error('You pressed Ctrl+C!')
		raise
	except:		
		raise
	finally:
		user_network_farmer.close()

	user_timeline_queue.put_nowait(-1)

	p.join()

	logger.info('all done')

if __name__=="__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument('-a', '--apikeys', help="config file for twitter api keys (json format); twitter requires you to have an account to crawl;", required = True)
	parser.add_argument('-c', '--crawler', help="the crawler identifier; you can have multiple crawler accounts set in the apikeys.json; pick one", required = True)
	parser.add_argument('-s', '--seeds', help="the config file for defining seed users and depth; see twitter_crawler.json as an example", required = True)
	parser.add_argument('-o', '--output', help="define the location of the output", required = True)
	parser.add_argument('-nt', '--network_type', help="crawling [friends] or [followers]", default = 'followers')

	args = parser.parse_args()
	
	with open(os.path.abspath(args.apikeys), 'rb') as apikeys_f, open(os.path.abspath(args.seeds), 'rb') as config_f:
		import json, os
		apikeys_config = json.load(apikeys_f)
		apikeys = apikeys_config.get(args.crawler, None)
		
		config = json.load(config_f)
		
		farm_user_network(apikeys, config, args.output, args.network_type)
			



########NEW FILE########
__FILENAME__ = bootstrap_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

from nose.tools import nottest

import sys, os, json, exceptions, time
sys.path.append("..")

from tweetf0rm.utils import full_stack, hash_cmd, md5, get_keys_by_min_value
from tweetf0rm.proxies import proxy_checker
from tweetf0rm.redis_helper import NodeCoordinator, NodeQueue

class TestBootstrap:

	@classmethod
	def setup_class(cls):
		pass

	@classmethod
	def teardown_class(cls):
		pass

	def setup(self):
		import sys, os, json
		#sys.path.append("..")
		with open(os.path.abspath('../../config.json'), 'rb') as config_f, open(os.path.abspath('proxies.json'), 'rb') as proxy_f:
			self.config = json.load(config_f)
			self.proxies = json.load(proxy_f)

	def teardown(self):
		pass

	@nottest
	def test_distribute_to_local(self):
		def distribute_to(crawlers):

			current_qsize = None
			current_crawler_id = None
			for crawler_id in crawlers:
				qsize = len(crawlers[crawler_id]['queue'])
				if (current_qsize == None or current_qsize >= qsize):
					current_qsize = qsize
					current_crawler_id = crawler_id

			return current_crawler_id

		crawlers = {}

		crawlers[1] = {'queue': {1:'',2:'',3:'',4:'',5:''}}
		crawlers[2] = {'queue': {1:'',2:''}}
		crawlers[3]= {'queue': {1:'',2:'', 3:''}}

		for i in range(10, 20):
			crawler_id = distribute_to(crawlers)
			crawlers[crawler_id]['queue'][i] = ''

		logger.info(crawlers)

	@nottest
	def test_distribute_to(self):
		def distribute_to(qsizes):
			'''
			return a list of keys (crawler_ids) that have the minimum number of pending cmds
			'''

			min_v = min(qsizes.values())

			return [crawler_id for crawler_id in qsizes if qsizes[crawler_id] == min_v]

		qsizes = {
			"1": 5,
			"2": 5,
			"3": 2
			}

		for i in range(10):
			c_id = distribute_to(qsizes)[0]
			
			qsizes[c_id] += 1

		logger.info(qsizes)

	@nottest
	def test_get_user_id(self):
		from tweetf0rm.twitterapi.users import User
		from tweetf0rm.handler.inmemory_handler import InMemoryHandler

		apikeys = self.config["apikeys"]["i0mf0rmer03"]
		
		#inmemoryhandler = InMemoryHandler()
		user_api = User(apikeys=apikeys)
		userIds = user_api.get_user_ids_by_screen_names(["AmericanCance"])
		logger.info(userIds)

	@nottest
	def test_bootstrap(self):
		import tweetf0rm.bootstrap as bootstrap
		#apikeys = self.config["apikeys"]["i0mf0rmer03"]
		bootstrap.start_server(self.config, self.proxies["proxies"]) 
		# pass
		#from tweetf0rm.handler.inmemory_handler import InMemoryHandler
		#inmemory_handler = InMemoryHandler(verbose=False)

	@nottest
	def test_redis_connections(self):
		nodes = {}

		cnt = 0
		while True:
			nodes[cnt] = NodeQueue("node_id", redis_config=self.config['redis_config'])
			cnt += 1
			if (cnt % 5 == 0):
				nodes.clear()
			time.sleep(1)

	@nottest
	def test_split(self):

		def split(lst, n):
			lsize = {}
			results = {}
			for i in range(n):
				lsize[i] = 0
				results[i] = []

			
			for x in lst:
				idx = get_keys_by_min_value(lsize)[0]
				results[idx].append(x)
				lsize[idx] += 1

			for i in range(n):
				yield results[i]

			


		l = range(150)

		# logger.info({}.values())
		# n = iter(l)
		# logger.info(next(n))
		# logger.info(next(n))
		# logger.info(next(n))
		# logger.info(next(n))
		# logger.info(next(n))
		# logger.info(next(n))
		# try:
		# 	logger.info(next(n))
		# except Exception as exc:
		# 	try:
		# 		logger.info(type(exc))
		# 		logger.info(isinstance(exc, exceptions.StopIteration))
		# 		raise
		# 	except Exception as sss:
		# 		logger.info("again...%r"%(exc))
		# 		raise
			#raise
		p = split(l, 16)
		for i in range(16):
			logger.info(len(next(p)))
		# pp = next(p) if p else None
		# logger.info(pp)


		#logger.info(next(p))

	@nottest
	def test_proxy(self):
		proxies = proxy_checker(self.proxies['proxies'])
		#logger.info(proxies)
		logger.info('%d good proxies left'%len(proxies))

		# ps = []
		# for d in proxies:
		#  	ps.append(d['proxy'])

		# with open(os.path.abspath('proxy.json'), 'wb') as proxy_f:
		#  	json.dump({'proxies':ps}, proxy_f)

if __name__=="__main__":
	import nose
	#nose.main()
	result = nose.run(TestBootstrap)
########NEW FILE########
__FILENAME__ = client_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from nose.tools import nottest

import sys, time
sys.path.append("..")

from tweetf0rm.redis_helper import NodeQueue
from tweetf0rm.utils import full_stack, node_id, public_ip

class TestClient:

	@classmethod
	def setup_class(cls):
		pass

	@classmethod
	def teardown_class(cls):
		pass

	def setup(self):
		import sys, os, json
		#sys.path.append("..")
		with open(os.path.abspath('config.json'), 'rb') as config_f:
			self.config = json.load(config_f)

	def teardown(self):
		pass

	@nottest
	def test_client(self):
		nid = node_id()
		logger.info("sending to %s"%(nid))
		node_queue = NodeQueue(nid, redis_config=self.config['redis_config'])
		#redis_cmd_queue.clear()

		cmd = {
			"cmd": "CRAWL_FRIENDS",
			"user_id": 1948122342,
			"data_type": "ids",
			"depth": 2,
			"bucket":"friend_ids"
		}

		# cmd = {
		# 	"cmd": "CRAWL_USER_TIMELINE",
		# 	"user_id": 1948122342,#53039176,
		# 	"bucket": "timelines"
		# }

		node_queue.put(cmd)

		#cmd = {"cmd":"TERMINATE"}
		
		#node_queue.put(cmd)

		return True


if __name__=="__main__":
	import nose
	#nose.main()
	result = nose.run()
########NEW FILE########
__FILENAME__ = rate_limit_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.DEBUG)

from nose.tools import nottest

import sys, os, json, exceptions
sys.path.append("..")

from tweetf0rm.utils import full_stack
from tweetf0rm.proxies import proxy_checker

import multiprocessing as mp

from tweetf0rm.twitterapi.users import User

class Handler(object):

	def append(self,data, bucket=None, key=None):
		logger.info(data)
		pass

def call_user_api(apikeys, client_args):

	user_api = User(apikeys=apikeys, client_args=client_args)
	user_api.find_all_friend_ids(53039176, [Handler()])

			
class TestTwitterRateLimit:

	@classmethod
	def setup_class(cls):
		pass

	@classmethod
	def teardown_class(cls):
		pass

	def setup(self):
		import sys, os, json
		#sys.path.append("..")
		with open(os.path.abspath('rate_limit_test.json'), 'rb') as config_f, open(os.path.abspath('proxy.json'), 'rb') as proxy_f:
			self.config = json.load(config_f)
			self.proxies = json.load(proxy_f)

	def teardown(self):
		pass

	@nottest
	def test_china_proxy(self):
		apikeys = self.config['apikeys']['i0mf0rmer13']
			
		client_args = {
			"timeout": 300,
			"proxies": {'http':'203.156.207.249:8080'}#proxy_list[i]['proxy_dict']
		}

		call_user_api(apikeys, client_args)


	@nottest
	def test_rate_limit(self):
		from tweetf0rm.proxies import proxy_checker

		proxy_list = proxy_checker(self.proxies['proxies'])

		ps = []
		for i, twitter_user in enumerate(self.config['apikeys']):
			apikeys = self.config['apikeys'][twitter_user]
			

			client_args = {
				"timeout": 300,
				"proxies": {'http':'203.156.207.249:8080'}#proxy_list[i]['proxy_dict']
			}
			logger.info(client_args)

			p = mp.Process(target=call_user_api, args=(apikeys, client_args, ))
			ps.append(p)
			p.start()

		for p in ps:
			p.join()

if __name__=="__main__":
	import nose
	#nose.main()
	result = nose.run(TestTwitterRateLimit)
########NEW FILE########
__FILENAME__ = bootstrap
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s-[%(asctime)s][%(module)s][%(funcName)s][%(lineno)d]: %(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

import sys, time, argparse, json, os, pprint
sys.path.append(".")

import multiprocessing as mp
from tweetf0rm.exceptions import InvalidConfig
from tweetf0rm.redis_helper import NodeQueue, NodeCoordinator
from tweetf0rm.utils import full_stack, node_id, public_ip
from tweetf0rm.proxies import proxy_checker
from tweetf0rm.scheduler import Scheduler
import time, os, tarfile, futures

def check_config(config):
	if ('apikeys' not in config or 'redis_config' not in config):
		raise InvalidConfig("something is wrong with your config file... you have to have redis_config and apikeys")

def tarball_results(data_folder, bucket, output_tarball_foldler, timestamp):

	logger.info("archiving bucket: [%s] at %s"%(bucket, timestamp))
	data_folder = os.path.join(os.path.abspath(data_folder), bucket)

	if (not os.path.exists(data_folder)):
		os.makedirs(data_folder)

	output_tarball_foldler = os.path.join(os.path.abspath(output_tarball_foldler), bucket)

	if (not os.path.exists(output_tarball_foldler)):
		os.makedirs(output_tarball_foldler)

	gz_file = os.path.join(output_tarball_foldler, '%s.tar.gz'%timestamp) 
	ll = []
	
	ignores = ['.DS_Store']
	for root, dirs, files in os.walk(data_folder):
		if (len(files) > 0):
			with tarfile.open(gz_file, "w:gz") as tar:
				cnt = 0
				for f in files:
					if (f in ignores):
						continue
					f_abspath = os.path.join(root, f)
					(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(f_abspath)

					if (mtime <= timestamp):
						tar.add(f_abspath, '%s/%s'%(timestamp,f), recursive=False)
						ll.append(f_abspath)
						cnt += 1
						if (cnt % 1000 == 0):
							logger.info("processed %d files"%(cnt))
					else:
						pass
				#logger.debug(time.ctime(atime))


				tar.close()

				for f in ll:

					os.remove(f)

				return True, gz_file

	return False, gz_file


def start_server(config, proxies):
	import copy
	
	check_config(config)
	config = copy.copy(config)

	folders_to_create = []
	buckets = ["tweets", "followers", "follower_ids", "friends", "friend_ids", "timelines"]

	ouput_folder = os.path.abspath(config['output'])
	archive_output = os.path.abspath(config['archive_output']) if config['archive_output'] else ouput_folder
	archive_output = os.path.join(archive_output, 'archived')

	folders_to_create.append(ouput_folder)
	folders_to_create.append(archive_output)

	for bucket in buckets:
		folders_to_create.append(os.path.join(ouput_folder, bucket))
		folders_to_create.append(os.path.join(archive_output, bucket))

	for folder_to_create in folders_to_create:
		if (not os.path.exists(folder_to_create)):
			os.makedirs(folder_to_create)

	logger.info("output to %s"%(ouput_folder))
	logger.info("archived to %s"%(archive_output))

	this_node_id = node_id()
	node_queue = NodeQueue(this_node_id, redis_config=config['redis_config'])
	node_queue.clear()

	scheduler = Scheduler(this_node_id, config=config, proxies=proxies)

	logger.info('starting node_id: %s'%this_node_id)

	node_coordinator = NodeCoordinator(config['redis_config'])
	#node_coordinator.clear()
	
	#the main event loop, actually we don't need one, since we can just join on the crawlers and don't stop until a terminate command is issued to each crawler;
	#but we need one to report the status of each crawler and perform the tarball tashs...
	
	last_archive_ts = time.time() + 3600 # the first archive event starts 2 hrs later... 
	pre_time = time.time()
	last_load_balancing_task_ts = time.time()
	while True:
		
		if (time.time() - pre_time > 120):
			logger.info(pprint.pformat(scheduler.crawler_status()))
			pre_time = time.time()
			if (scheduler.is_alive()):
				cmd = {'cmd': 'CRAWLER_FLUSH'}
				scheduler.enqueue(cmd)

		if (time.time() - last_archive_ts > 3600):

			logger.info("start archive procedure...")
			with futures.ProcessPoolExecutor(max_workers=len(buckets)) as executor:

				future_proxies = {executor.submit(tarball_results, ouput_folder, bucket, archive_output, int(time.time()) - 3600): bucket for bucket in buckets}
		
				for future in future_proxies:
					future.add_done_callback(lambda f: logger.info("archive created? %s: [%s]"%f.result()))

			last_archive_ts = time.time()

		# block, the main process...for a command
		if(not scheduler.is_alive()):
			logger.info("no crawler is alive... waiting to recreate all crawlers...")
			time.sleep(120) # sleep for a minute and retry
			continue

		if (time.time() - last_load_balancing_task_ts > 1800): # try to balance the local queues every 30 mins
			last_load_balancing_task_ts = time.time()
			cmd = {'cmd': 'BALANCING_LOAD'}
			scheduler.enqueue(cmd)

		cmd = node_queue.get(block=True, timeout=360)

		if cmd:
			scheduler.enqueue(cmd)
				

if __name__=="__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config', help="config.json that contains a) twitter api keys; b) redis connection string;", required = True)
	parser.add_argument('-p', '--proxies', help="the proxies.json file")

	args = parser.parse_args()

	proxies = None
	if args.proxies:
		with open(os.path.abspath(args.proxies), 'rb') as proxy_f:
			proxies = json.load(proxy_f)['proxies']

	with open(os.path.abspath(args.config), 'rb') as config_f:
		config = json.load(config_f)	
		
		try:
			start_server(config, proxies)
		except KeyboardInterrupt:
			print()
			logger.error('You pressed Ctrl+C!')
			pass
		except Exception as exc:		
			logger.error(exc)
			logger.error(full_stack())
		finally:
			pass
########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s-[%(module)s][%(funcName)s]: %(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

import sys, time, argparse, random, copy, pprint
sys.path.append(".")
from tweetf0rm.redis_helper import NodeQueue, NodeCoordinator
from tweetf0rm.utils import node_id, public_ip, hash_cmd
from tweetf0rm.exceptions import NotImplemented

pp = pprint.PrettyPrinter(indent=4)

avaliable_cmds = {
	'CRAWL_FRIENDS': {
		'user_id' : {
			'value':0,
			'validation': lambda x: x > 0
		},
		'data_type' : {
		 	'value': 'ids',
		 	'validation': lambda x: x in ['ids', 'users']
		},
		'depth': {
			'value': 1,
		},
		'bucket': {
			'value': 'friend_ids'
		}
	},
	'BATCH_CRAWL_FRIENDS': {
		'user_id' : {
			'value':0,
			'validation': lambda x: x > 0
		},
		'data_type' : {
		 	'value': 'ids',
		 	'validation': lambda x: x in ['ids', 'users']
		},
		'depth': {
			'value': 1,
		},
		'bucket': {
			'value': 'friend_ids'
		}
	},
	'CRAWL_FOLLOWERS': {
		'user_id' : {
			'value':0,
			'validation': lambda x: x > 0
		},
		'data_type' : {
		 	'value': 'ids',
		 	'validation': lambda x: x in ['ids', 'users']
		},
		'depth': {
			'value': 1,
		},
		'bucket': {
			'value': 'follower_ids'
		}
	},
	'BATCH_CRAWL_FOLLOWERS': {
		'user_id' : {
			'value':0,
			'validation': lambda x: x > 0
		},
		'data_type' : {
		 	'value': 'ids',
		 	'validation': lambda x: x in ['ids', 'users']
		},
		'depth': {
			'value': 1,
		},
		'bucket': {
			'value': 'follower_ids'
		}
	}, 'CRAWL_USER_TIMELINE': {
		'user_id' : {
			'value':0,
			'validation': lambda x: x > 0
		},
		'bucket': {
			'value': 'timelines'
		}
	},'CRAWL_TWEET': {
		'tweet_id' : {
			'value':0
		},
		'bucket': {
			'value': 'tweets'
		}
	}, 'BATCH_CRAWL_TWEET': {
		'bucket': {
			'value': 'tweets'
		}
	}, 'BATCH_CRAWL_USER_TIMELINE': {
		'bucket': {
			'value': 'timelines'
		}
	}, 'GET_UIDS_FROM_SCREEN_NAMES': {

	}, 'GET_USERS_FROM_IDS': {

	}, 'LIST_NODES':{

	}, 'SHUTDOWN_NODE': {

	}, 'NODE_QSIZES': {

	}, 'CLEAR_NODE_QUEUES': {

	}
}

from tweetf0rm.twitterapi.users import User
import json, os

def new_cmd(command, args_dict):

	cmd_template = avaliable_cmds[command]
	cmd = {'cmd':command}
	for k in cmd_template:
		cmd[k] = args_dict[k] if k in args_dict else cmd_template[k]['value']
		if ('validation' in cmd_template[k] and cmd_template[k]['validation']):
			if (not cmd_template[k]['validation'](cmd[k])):
				raise Exception("%s: %s failed validation"%(k, cmd[k]))

	cmd['cmd_hash'] = hash_cmd(cmd)

	return cmd

def cmd(config, args):
	
	if (args.command not in avaliable_cmds):
		raise Exception("not a valid command...")

	nid = args.node_id
	
	logger.info("node_id: %s"%(nid))
	node_queue = NodeQueue(nid, redis_config=config['redis_config'])
	node_coordinator = NodeCoordinator(config['redis_config'])
	# this can be done locally without sending the command to the servers...
	if (args.command == 'GET_UIDS_FROM_SCREEN_NAMES'):
		apikeys = config["apikeys"].values()[0]
		if (not os.path.exists(args.json)):
			raise Exception("doesn't exist... ")
		with open(os.path.abspath(args.json), 'rb') as f, open(os.path.abspath(args.output), 'wb') as o_f:
			screen_names = json.load(f)
			user_api = User(apikeys=apikeys)
			user_ids = user_api.get_user_ids_by_screen_names(screen_names)
			json.dump(list(user_ids), o_f)
	elif (args.command == 'GET_USERS_FROM_IDS'):
		apikeys = config["apikeys"].values()[0]
		if (not os.path.exists(args.json)):
			raise Exception("doesn't exist... ")
		with open(os.path.abspath(args.json), 'rb') as f, open(os.path.abspath(args.output), 'wb') as o_f:
			user_ids = json.load(f)
			user_api = User(apikeys=apikeys)
			users = user_api.get_users(user_ids)
			json.dump(list(users), o_f)
	elif (args.command.startswith('BATCH_')):
		new_command = args.command.replace('BATCH_', '')
		args_dict = copy.copy(args.__dict__)
		if (not os.path.exists(args.json)):
			raise Exception("doesn't exist... ")
		with open(os.path.abspath(args.json), 'rb') as f:
			if ( args.command == 'BATCH_CRAWL_TWEET' ):
				tweet_ids = json.load(f)
				for tweet_id in tweet_ids:
					print "Loading Tweet ID: ", tweet_id
					args_dict['tweet_id'] = tweet_id
					cmd = new_cmd(new_command, args_dict)
					node_queue.put(cmd)
			else:
				user_ids = json.load(f)
				for user_id in user_ids:
					args_dict['user_id'] = user_id
					cmd = new_cmd(new_command, args_dict)
					node_queue.put(cmd)
	elif (args.command == 'LIST_NODES'):
		pp.pprint(node_coordinator.list_nodes())
	elif (args.command == 'NODE_QSIZES'):
		raise NotImplemented("NotImplemented yet...")
		#pp.pprint(node_coordinator.list_nodes())
	elif (args.command == 'SHUTDOWN_NODE'):
		#node_coordinator.remove_node(nid)
		#pp.pprint(node_coordinator.list_nodes())
		raise NotImplemented("NotImplemented yet...")
	elif (args.command == 'CLEAR_NODE_QUEUES'):
		node_queue.clear_all_queues()
	else:
		args_dict = copy.copy(args.__dict__)
		cmd = new_cmd(args.command, args_dict)
		node_queue.put(cmd)
		logger.info('sent [%s]'%(cmd))

	

def print_avaliable_cmd():
	dictionary = {
		'-uid/--user_id': 'the user id that you want to crawl his/her friends (who he/she is following) or followers',
		'-tid/--tweet_id': 'the tweet id that you want to fetch',
		#'-nt/--network_type': 'whether you want to crawl his/her friends or followers',
		'-dt/--data_type': '"ids" or "users" (default to ids) what the results are going to look like (either a list of twitter user ids or a list of user objects)',
		'-d/--depth': 'the depth of the network; e.g., if it is 2, it will give you his/her (indicated by the -uid) friends\' friends',
		'-j/--json': 'a json file that contains a list of screen_names or user_ids, depending on the command',
		'-o/--output': ' the output json file (for storing user_ids from screen_names)',
		'-nid/--node_id':'the node_id that you want to interact with; default to the current machine...'
	}
	cmds =  {'CRAWL_FRIENDS': {
		'-uid/--user_id': dictionary['-uid/--user_id'],
		#'-nt/--network_type': dictionary['-nt/--network_type'],
		'-dt/--data_type': dictionary['-dt/--data_type'],
		'-d/--depth': dictionary['-d/--depth']
	}, 'BATCH_CRAWL_FRIENDS':{
		'-j/--json': dictionary['-j/--json'],
		#'-nt/--network_type': dictionary['-nt/--network_type'],
		'-dt/--data_type': dictionary['-dt/--data_type'],
		'-d/--depth': dictionary['-d/--depth']
	}, 'CRAWL_FOLLOWERS':{
		'-uid/--user_id': dictionary['-uid/--user_id'],
		#'-nt/--network_type': dictionary['-nt/--network_type'],
		'-dt/--data_type': dictionary['-dt/--data_type'],
		'-d/--depth': dictionary['-d/--depth']
	}, 'BATCH_CRAWL_FOLLOWERS':{
		'-j/--json': dictionary['-j/--json'],
		#'-nt/--network_type': dictionary['-nt/--network_type'],
		'-dt/--data_type': dictionary['-dt/--data_type'],
		'-d/--depth': dictionary['-d/--depth']
	}, 'CRAWL_USER_TIMELINE': {
		'-uid/--user_id': dictionary['-uid/--user_id']
	}, 'CRAWL_TWEET': {
		'-tid/--tweet_id': dictionary['-tid/--tweet_id']
	}, 'BATCH_CRAWL_TWEET': {
		'-j/--json': dictionary['-j/--json']
	}, 'BATCH_CRAWL_USER_TIMELINE': {
		'-j/--json': dictionary['-j/--json']
	}, 'GET_UIDS_FROM_SCREEN_NAMES': {
		'-j/--json':  dictionary['-j/--json'],
		'-o/--output':  dictionary['-o/--output']
	}, 'GET_USERS_FROM_IDS': {
		'-j/--json':  dictionary['-j/--json'],
		'-o/--output':  dictionary['-o/--output']
	}, 'LIST_NODES': {
	}, 'SHUTDOWN_NODE': {
		'-nid/--node_id':  dictionary['-nid/--node_id']
	}, 'NODE_QSIZES':{
		'-nid/--node_id':  dictionary['-nid/--node_id']
	}, 'CLEAR_NODE_QUEUES':{
		'-nid/--node_id':  dictionary['-nid/--node_id']
	}}
	

	for k, v in cmds.iteritems():
		print('')
		print('\t%s:'%k)
		for kk, vv in v.iteritems():
			print('\t\t%s: %s'%(kk, vv))

	print('')


if __name__=="__main__":
	nid = node_id()
	import json, os
	
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config', help="config.json that contains a) twitter api keys; b) redis connection string;", required = True)
	parser.add_argument('-cmd', '--command', help="the cmd you want to run, e.g., \"CRAWL_FRIENDS\"", required=True)
	parser.add_argument('-uid', '--user_id', help="the user_id", default=0)
	parser.add_argument('-tid', '--tweet_id', help="the tweet_id", default=0)
	parser.add_argument('-dt', '--data_type', help="the data_type (e.g., 'ids' or 'users'", default='ids')
	parser.add_argument('-d', '--depth', help="the depth", default=1)
	parser.add_argument('-j', '--json', help="the location of the json file that has a list of user_ids or screen_names", required=False)
	parser.add_argument('-o', '--output', help="the location of the output json file for storing user_ids", default='user_ids.json')
	parser.add_argument('-nid', '--node_id', help="the node_id you want to interact with", default=nid)
	
	try:
		args = parser.parse_args()

		with open(os.path.abspath(args.config), 'rb') as config_f:
			config = json.load(config_f)

			cmd(config, args)
	except Exception as exc:
		logger.error(exc)
		print_avaliable_cmd()
########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @author: ji0ng.bi0n


class NotImplemented(Exception):
	pass

class MissingArgs(Exception):
	pass

class WrongArgs(Exception):
	pass

class InvalidConfig(Exception):
	pass

class MaxRetryReached(Exception):
	pass
########NEW FILE########
__FILENAME__ = base_handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
base_handler.py: handlers are the sinks of data
'''

import logging

logger = logging.getLogger(__name__)

from tweetf0rm.exceptions import WrongArgs
import json

class BaseHandler(object):

	def __init__(self):
		'''
			buckets: defines the sub-structure of the buffer; either ["tweets", "followers", "follower_ids", "friends", "friend_ids", "timelines"]
		'''
		self.buffer = dict()
		self.buckets = ["tweets", "followers", "follower_ids", "friends", "friend_ids", "timelines"]
		for bucket in self.buckets:
			self.buffer[bucket] = dict()
		self.futures = []

	def append(self, data=None, bucket=None, key='current_timestampe'):
		if (not data):
			raise WrongArgs("what's the point? not data coming in...")

		if (bucket not in self.buckets):
			raise WrongArgs("%s is not a valid buckets..."%bucket)

		logger.debug("adding new data -- into [%s][%s]"%(bucket, key))

		if (key not in self.buffer[bucket]):
			self.buffer[bucket][key] = list()
			
		self.buffer[bucket][key].append(data)

		need_flush = self.need_flush(bucket)
		logger.debug("flush? %s"%need_flush)
		if (need_flush):
			self.flush(bucket)


	def get(self, bucket, key):
		return self.buffer[bucket][key]

	def stat(self):
		stat = {}
		for bucket in self.buckets:
			stat[bucket] = {
				'count': len(self.buffer[bucket])
			}

			data = {}
			for k in self.buffer[bucket]:
				data[k] = len(self.buffer[bucket][k])
			
			stat[bucket]["data"] = data
		
		return stat

	def remove_key(self, bucket = None, key = None):
		del self.buffer[bucket][key]

	def clear(self, bucket = None):
		if (bucket):
			logger.debug("clear bucket: %s"%bucket)
			del self.buffer[bucket]
			self.buffer[bucket] = dict()

	def clear_all(self):
		for bucket in self.buckets:
			self.clear(bucket)

	def need_flush(self, bucket):
		'''
		sub-class determine when to flush and what to flush
		'''
		pass

	def flush(self, bucket):
		logger.info('calling the BaseHandler flush???')
		pass

	def flush_all(self, block=False):

		for bucket in self.buffer:
			self.flush(bucket)

		if (block):
			for f in self.futures:
				while(not f.done()):
					time.sleep(5)

		return True


########NEW FILE########
__FILENAME__ = crawl_user_relationship_command_handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
RedisCommandHandler: handler that generates new commands on the fly
'''

import logging

logger = logging.getLogger(__name__)

from .base_handler import BaseHandler
import multiprocessing as mp
import futures, json, copy, time
from tweetf0rm.redis_helper import NodeQueue, NodeCoordinator
from tweetf0rm.utils import full_stack, get_keys_by_min_value, hash_cmd
import json

def flush_cmd(bulk, data_type, template, redis_config):

	try:
		node_coordinator = NodeCoordinator(redis_config=redis_config)

		qsizes = node_coordinator.node_qsizes()

		logger.debug(qsizes)
		
		node_queues = {}

		for element in bulk:
			if data_type == "ids" and type(element) == int:
				user_id = element
			elif data_type =="users" and type(element) == dict and "id" in element:
				user_id = element['id']
			
			t = copy.copy(template)
			t["user_id"] = int(user_id)
			t["depth"] = int(t["depth"]) -1

			node_id = get_keys_by_min_value(qsizes)[0]

			if (node_id in node_queues):
				node_queue = node_queues[node_id]
			else:
				node_queue = NodeQueue(node_id, redis_config=redis_config)
				node_queues[node_id] = node_queue


			t['cmd_hash'] = hash_cmd(t)
			node_queue.put(t)
			qsizes[node_id] += 1

			logger.debug("send [%s] to node: %s"%(json.dumps(t),node_id))

		# intend to close all redis connections, but not sure yet...
		node_queues.clear()

		del node_coordinator

			
	except Exception as exc:
		logger.error('error during flush: %s'%exc)

	return True
		

class CrawlUserRelationshipCommandHandler(BaseHandler):

	def __init__(self, template=None, redis_config = None):
		'''
		A RedisCommandHandler is used to push new commands into the queue;
		this is helpful, in cases such as crawling a user's followers' followers to create a network
		some user has extremely large number of followers, it's impossible (and inefficient) to re-iterate through 
		the follower lists, after it's done... when it flush, it flush the commands to the redis channel
		'''
		super(CrawlUserRelationshipCommandHandler, self).__init__()
		self.template = template
		self.data_type = template["data_type"]
		self.redis_config = redis_config

	def need_flush(self, bucket):
		# flush every time there is new data comes in
		return True

	def flush(self, bucket):
		logger.debug("i'm getting flushed...")

		with futures.ProcessPoolExecutor(max_workers=1) as executor:
			for k, v in self.buffer[bucket].iteritems():
				for s in v:
					o = json.loads(s)

					f = executor.submit(flush_cmd, o[self.data_type], self.data_type, self.template, self.redis_config)

					self.futures.append(f)
					# while (f.running()):
					# 	time.sleep(5)
			
			# send to a different process to operate, clear the buffer
			self.clear(bucket)

		True


########NEW FILE########
__FILENAME__ = file_handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
file_handler.py: handler that's collects the data, and write to the disk on a separate thread; 

'''

import logging

logger = logging.getLogger(__name__)

from .base_handler import BaseHandler
import futures, os
from tweetf0rm.utils import full_stack

def flush_file(output_folder, bucket, items):
	try:
		bucket_folder = os.path.abspath('%s/%s'%(output_folder, bucket))

		for k, lines in items.iteritems():
			filename = os.path.abspath('%s/%s'%(bucket_folder, k))
			with open(filename, 'ab+') as f:
				for line in lines:
					f.write('%s\n'%line)
		
			logger.debug("flushed %d lines to %s"%(len(lines), filename))

	except:
		logger.error(full_stack())

	return True

FLUSH_SIZE = 100

class FileHandler(BaseHandler):

	def __init__(self, output_folder='./data'):
		super(FileHandler, self).__init__()
		self.output_folder = os.path.abspath(output_folder)
		if not os.path.exists(self.output_folder):
			os.makedirs(self.output_folder)

		for bucket in self.buckets:
			bucket_folder = os.path.abspath('%s/%s'%(self.output_folder, bucket))
			if not os.path.exists(bucket_folder):
				os.makedirs(bucket_folder)

	def need_flush(self, bucket):
		if (len(self.buffer[bucket]) >  FLUSH_SIZE):
			return True
		else:
			return False

	def flush(self, bucket):

		with futures.ProcessPoolExecutor(max_workers=3) as executor:
			# for each bucket it's a dict, where the key needs to be the file name; and the value is a list of json encoded value
			for bucket, items in self.buffer.iteritems():

				if (len(items) > 0):
					f = executor.submit(flush_file, self.output_folder, bucket, items)
				
					# send to a different process to operate, clear the buffer
					self.clear(bucket)

					#self.futures.append(f)
					

		return True

	
########NEW FILE########
__FILENAME__ = inmemory_handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
InMemoryHandler: handler that's collects the data in memory
'''

import logging

logger = logging.getLogger(__name__)

from .base_handler import BaseHandler

class InMemoryHandler(BaseHandler):
	'''
	inmemory_handler_config = {
		"name": "InMemoryHandler",
		"args": {}
	}
	inmemory_handler = create_handler(inmemory_handler_config)
	'''

	def __init__(self):
		super(InMemoryHandler, self).__init__()

########NEW FILE########
__FILENAME__ = mongodb_handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
write_to_handler.py: handler that's collects the data, and write to the disk on a separate thread; 

'''

import logging

logger = logging.getLogger(__name__)

from tweetf0rm.exceptions import NotImplemented

class MongoDBHandler(object):

	def __init__(self):
		raise NotImplemented("placeholder, not implemented yet...")

	
########NEW FILE########
__FILENAME__ = crawler_process
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import logging

logger = logging.getLogger(__name__)

import multiprocessing as mp

import tweetf0rm.handler
from tweetf0rm.redis_helper import CrawlerQueue

#MAX_QUEUE_SIZE = 32767 

class CrawlerProcess(mp.Process):

	def __init__(self, node_id, crawler_id, redis_config, handlers):
		super(CrawlerProcess, self).__init__()
		self.node_id = node_id
		self.crawler_id = crawler_id
		self.redis_config = redis_config
		#self.queue = mp.Queue(maxsize=MAX_QUEUE_SIZE)

		self.crawler_queue = CrawlerQueue(node_id, crawler_id, redis_config=redis_config)
		self.crawler_queue.clear()
		#self.lock = mp.Lock()
		self.handlers = handlers
		logger.debug("number of handlers attached: %d"%(len(handlers)))


	def get_crawler_id(self):
		return self.crawler_id

	def enqueue(self, request):
		#self.queue.put(request, block=True)
		self.crawler_queue.put(request)
		return True

	def get_cmd(self):
		#return  self.queue.get(block=True)
		return self.crawler_queue.get(block=True)

	def get_queue_size(self):
		self.crawler_queue.qsize()

	def run(self):
		pass
			
########NEW FILE########
__FILENAME__ = user_relationship_crawler
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import logging

logger = logging.getLogger(__name__)

from .crawler_process import CrawlerProcess
from tweetf0rm.twitterapi.users import User
from tweetf0rm.handler import create_handler
from tweetf0rm.handler.crawl_user_relationship_command_handler import CrawlUserRelationshipCommandHandler
from tweetf0rm.utils import full_stack, hash_cmd
from tweetf0rm.exceptions import MissingArgs, NotImplemented
from tweetf0rm.redis_helper import NodeQueue
import copy, json


class UserRelationshipCrawler(CrawlerProcess):

	def __init__(self, node_id, crawler_id, apikeys, handlers, redis_config, proxies=None):
		if (handlers == None):
			raise MissingArgs("you need a handler to write the data to...")

		super(UserRelationshipCrawler, self).__init__(node_id, crawler_id, redis_config, handlers)

		self.apikeys = copy.copy(apikeys)
		self.tasks = {
			"TERMINATE": "TERMINATE", 
			"CRAWL_FRIENDS" : {
				"users": "find_all_friends",
				"ids": "find_all_friend_ids",
				"network_type": "friends"
			},
			"CRAWL_FOLLOWERS" :{
				"users": "find_all_followers",
				"ids": "find_all_follower_ids",
				"network_type": "followers"
			}, 
			"CRAWL_USER_TIMELINE": "fetch_user_timeline",
			"CRAWL_TWEET": "fetch_tweet_by_id"
		}
		self.node_queue = NodeQueue(self.node_id, redis_config=redis_config)
		self.client_args = {"timeout": 300}
		self.proxies = iter(proxies) if proxies else None
		self.user_api = None

		self.init_user_api()

		#self.init_user_api()

	def init_user_api(self): # this will throw StopIteration if all proxies have been tried...
		if (self.proxies):
			try:
				self.client_args['proxies'] = next(self.proxies)['proxy_dict'] # this will throw out 
				#logger.info("client_args: %s"%json.dumps(self.client_args))
			except StopIteration as exc:
				raise
			except Exception as exc:
				self.init_user_api()

		if (self.user_api):
			del self.user_api

		#crawler_id=self.crawler_id, 
		self.user_api = User(apikeys=self.apikeys, client_args=self.client_args)


	def get_handlers(self):
		return self.handlers

	def avaliable_cmds(self):
		return self.tasks.keys()

	def run(self):
		while True:
			# cmd is in json format
			# cmd = {
			#	network_type: "followers", # or friends
			#	user_id: id,
			#	data_type: 'ids' # users
			#}
			cmd = self.get_cmd()

			command = cmd['cmd']

			logger.debug("new cmd: %s"%(cmd))

			redis_cmd_handler = None

			#maybe change this to a map will be less expressive, and easier to read... but well, not too many cases here yet...
			if (command == 'TERMINATE'):
				# make sure we need to flush all existing data in the handlers..
				for handler in self.handlers:
				 	handler.flush_all()
				break
			elif (command == 'CRAWLER_FLUSH'):
				for handler in self.handlers:
				 	handler.flush_all()
			else:

				args = {}
				if (command == 'CRAWL_TWEET'):
					args = {
						"tweet_id": cmd['tweet_id'],
						"write_to_handlers": self.handlers,
						"cmd_handlers" : []
					}
				else:
					args = {
						"user_id": cmd['user_id'],
						"write_to_handlers": self.handlers,
						"cmd_handlers" : []
					}

				bucket = cmd["bucket"] if "bucket" in cmd else None

				if (bucket):
					args["bucket"] = bucket
				
				func = None
				if  (command in ['CRAWL_USER_TIMELINE', 'CRAWL_TWEET']):
					func = getattr(self.user_api, self.tasks[command])
				elif (command in ['CRAWL_FRIENDS', 'CRAWL_FOLLOWERS']):
					data_type = cmd['data_type']
					
					try:
						depth = cmd["depth"] if "depth" in cmd else None
						depth = int(depth)
						# for handler in self.handlers:
						# 	if isinstance(handler, InMemoryHandler):
						# 		inmemory_handler = handler
						if (depth > 1):
							template = copy.copy(cmd)
							# template = {
							#	network_type: "followers", # or friends
							#	user_id: id,
							#	data_type: 'ids' # object
							#	depth: depth
							#}
							# will throw out exception if redis_config doesn't exist...
							args["cmd_handlers"].append(CrawlUserRelationshipCommandHandler(template=template, redis_config=self.redis_config))

							logger.info("depth: %d, # of cmd_handlers: %d"%(depth, len(args['cmd_handlers'])))

					except Exception as exc:
						logger.warn(exc)
					
					func = getattr(self.user_api, self.tasks[command][data_type])
				
				if func:
					try:
						func(**args)
						del args['cmd_handlers']						
					except Exception as exc:
						logger.error("%s"%exc)
						try:
							self.init_user_api()
						except StopIteration as init_user_api_exc:
							# import exceptions
							# if (isinstance(init_user_api_exc, exceptions.StopIteration)): # no more proxy to try... so kill myself...
							for handler in self.handlers:
			 					handler.flush_all()

			 				logger.warn('not enough proxy servers, kill me... %s'%(self.crawler_id))
			 				# flush first
							self.node_queue.put({
								'cmd':'CRAWLER_FAILED',
								'crawler_id': self.crawler_id
								})
							del self.node_queue
							return False
							#raise
						else:
							#put current task back to queue...
							logger.info('pushing current task back to the queue: %s'%(json.dumps(cmd)))
							self.enqueue(cmd)

						#logger.error(full_stack())
						
				else:
					logger.warn("whatever are you trying to do?")

		logger.info("looks like i'm done...")
			
		return True


			



			
########NEW FILE########
__FILENAME__ = proxies
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)

from tweetf0rm.utils import full_stack
import requests, futures

def check_proxy(proxy, timeout):
	url = "http://twitter.com"
	headers = {
		'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0',
		'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
		'Accept-Encoding': 'gzip, deflate',
		'Accept-Language': 'en-US,en;q=0.5'
	}
	proxy_ip = proxy.keys()[0]
	proxy_type = proxy.values()[0]

	p = {'proxy':proxy,'proxy_dict':{proxy_type: '%s://%s'%(proxy_type, proxy_ip)}}

	try:
		s = requests.Session()
		r = s.get(url,headers=headers, proxies=p['proxy_dict'], timeout=timeout, allow_redirects=True)

		if (r.status_code == requests.codes.ok):
			return True, p
		else:
			return False, None
	except Exception as exc:
		logger.info("proxy [%s] failed: %s"%(p['proxy'], exc))
		return False, None

def proxy_checker(proxies):
	'''
		proxies is a list of {key:value}, where the key is the ip of the proxy (including port), e.g., 192.168.1.1:8080, and the value is the type of the proxy (http/https)
	'''

	logger.info('%d proxies to check'%(len(proxies)))
	import multiprocessing as mp
	

	results = []
	with futures.ProcessPoolExecutor(max_workers=mp.cpu_count()*10) as executor:

		future_to_proxy = {executor.submit(check_proxy, proxy, 30): proxy for proxy in proxies if proxy.values()[0] == 'http'}

		for future in future_to_proxy:
			future.add_done_callback(lambda f: results.append(f.result()))
			
		logger.info('%d http proxies to check'%(len(future_to_proxy)))

		futures.wait(future_to_proxy)

		# for future in futures.as_completed(future_to_proxy):

		# 	proxy = future_to_proxy[future]
		# 	try:
		# 		good, proxy_dict = future.result()
		# 	except Exception as exc:
		# 		logger.info('%r generated an exception: %s'%(proxy, exc))
		# 	else:
		# 		if (good):
		# 			good_proxies.append(proxy_dict)
		
		return [p for (good, p) in results if good]






########NEW FILE########
__FILENAME__ = redis_helper
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)

import redis, json
from tweetf0rm.utils import full_stack, hash_cmd, md5, get_keys_by_min_value

class RedisBase(object):

	def __init__(self, name, namespace='default', redis_config=None):
		if (not redis_config):
			redis_config = { 'host': 'localhost', 'port': 6379, 'db': 0}

		self.redis_config = redis_config
		self.__redis_connection = redis.StrictRedis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'])
		self.password = redis_config['password']
		self.namespace = namespace
		self.name = name
		self.key = '%s:%s'%(self.namespace, self.name)
		if (self.password):
			self.__auth()

	def get_key(self):
		return self.key

	def __auth(self):
		self.__redis_connection.execute_command("AUTH", self.password)

	def conn(self):
		self.__auth()
		return self.__redis_connection

class RedisQueue(RedisBase):
	
	def __init__(self, name, queue_type='lifo', namespace='queue', redis_config=None):
		super(RedisQueue, self).__init__(name, namespace=namespace, redis_config=redis_config)
		if (queue_type not in ['fifo', 'lifo']):
			raise Exception("queue_type has to be either fifo or lifo")
		self.queue_type = queue_type

	def qsize(self):
		"""Return the approximate size of the queue."""
		return self.conn().llen(self.key)

	def empty(self):
		"""Return True if the queue is empty, False otherwise."""
		return self.qsize() == 0

	def put(self, item):
		"""Put item into the queue."""
		self.conn().rpush(self.key, json.dumps(item))


	def get(self, block=True, timeout=None):
		"""Remove and return an item from the queue. 

		If optional args block is true and timeout is None (the default), block
		if necessary until an item is available."""
		if block:
			if (self.queue_type == 'fifo'):
				item = self.conn().blpop(self.key, timeout=timeout)
			elif (self.queue_type == 'lifo'):
				item = self.conn().brpop(self.key, timeout=timeout)
		else:
			if (self.queue_type == 'fifo'):
				item = self.conn().lpop(self.key)
			elif (self.queue_type == 'lifo'):
				item = self.conn().rpop(self.key)

		if item:
			item = json.loads(item[1])
		return item

	def get_nowait(self):
		"""Equivalent to get(False)."""
		return self.get(False)

	def clear(self):
		"""Clear out the queue"""
		self.conn().delete(self.key)

class CrawlerQueue(RedisQueue):

	def __init__(self, node_id, crawler_id, redis_config=None):
		super(CrawlerQueue, self).__init__('%s:%s'%(node_id,crawler_id), redis_config=redis_config)

class NodeQueue(RedisQueue):

	def __init__(self, node_id, redis_config=None):
		super(NodeQueue, self).__init__(node_id, redis_config=redis_config)
		self.node_id = node_id

	def clear_all_queues(self):
		'''This will not only clear the node queue (mostly for control cmds); but also the crawlers' cmd queues to give you a fresh start'''
		#self.conn().delete('queue:%s*'%(self.node_id))
		for key in self.conn().keys('queue:%s:*'%self.node_id):
			self.conn().delete(key)

		self.conn().delete('queue:%s'%self.node_id)

class NodeCoordinator(RedisBase):
	'''
	Used to coordinate queues across multiple nodes
	'''
	def __init__(self, redis_config=None):
		super(NodeCoordinator, self).__init__("coordinator", namespace="node", redis_config=redis_config)
		self.nodes_key = '%s:nodes'%(self.key)
		self.nodes = {}

	def get_node(self, node_id):
		if (node_id in self.nodes):
			node = self.nodes[node_id]
		else:
			node = NodeQueue(node_id, redis_config=self.redis_config)
			self.nodes[node_id] = node

		return node

	def distribute_to_nodes(self, crawler_queue):

		qsizes = self.node_qsizes()		

		cmd = crawler_queue.get(timeout=60)
		while (cmd):

			node_id = get_keys_by_min_value(qsizes)[0]

			node = self.get_node(node_id)			

			node.put(cmd)
			qsizes[node_id] += 1

			cmd = crawler_queue.get(timeout=60)

	def clear(self):
		self.conn().delete('%s:*'%self.key)

	def add_node(self, node_id):
		self.conn().sadd(self.nodes_key, node_id)

	def remove_node(self, node_id):
		''' Only remove the node from the active list;'''
		self.conn().srem(self.nodes_key, node_id)

	def list_nodes(self):
		node_ids = self.conn().smembers(self.nodes_key)
		return node_ids


	def node_qsizes(self):
		'''
		List the size of all active nodes' queues
		'''
		node_ids = self.conn().smembers(self.nodes_key)

		qsizes = {}
		for node_id in node_ids:
			qsize = 0
			for crawler_queue_key in self.conn().keys('queue:%s:*'%node_id):
				qsize += self.conn().llen(crawler_queue_key)	

			qsizes[node_id] = qsize

		return qsizes







########NEW FILE########
__FILENAME__ = scheduler
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
# requests_log = logging.getLogger("requests")
# requests_log.setLevel(logging.WARNING)

import json, copy, time
from tweetf0rm.utils import full_stack, hash_cmd, md5, get_keys_by_min_value
from tweetf0rm.proxies import proxy_checker
from process.user_relationship_crawler import UserRelationshipCrawler
#from handler.inmemory_handler import InMemoryHandler
from handler import create_handler
from tweetf0rm.redis_helper import NodeCoordinator, NodeQueue, CrawlerQueue
import twython, pprint
from operator import itemgetter

control_cmds = ['TERMINATE', 'CRAWLER_FLUSH', 'CRAWLER_FAILED']

class Scheduler(object):

	def __init__(self, node_id, config={}, proxies=[]):
		self.node_id = node_id
		self.config = config
		if (len(proxies) > 0):
			
			self.proxy_list = proxy_checker(proxies)

			logger.info("number of live proxies: %d"%(len(self.proxy_list)))

			# each process only get one apikey...  if there are more proxies than apikeys, each process can get more than one proxy that can be rotated when one fails. 
			number_of_processes = min(len(self.config['apikeys']), len(self.proxy_list))

			# if there are more proxies than apikeys, then each process will get a list of proxies, and the process will restart it self if a proxy failed, and try the next available proxy
			self.proxy_generator = self.split(self.proxy_list, number_of_processes)

		else:
			self.proxy_list = None
			self.proxy_generator = None
			number_of_processes = 1

		logger.info("number of crawlers: %d"%(number_of_processes))

		apikey_list = self.config['apikeys'].keys()


		self.crawlers = {}
		for idx in range(number_of_processes):
			try:
				self.new_crawler(self.node_id, self.config['apikeys'][apikey_list[idx]], config)
			except Exception as exc:
				logger.error(exc)
				pass


		self.node_coordinator = NodeCoordinator(config['redis_config'])
		self.node_coordinator.add_node(node_id)

		logger.info("number of crawlers: %d created"%(number_of_processes))

	def new_crawler(self, node_id, apikeys, config, crawler_proxies = None):
		file_handler_config = {
			"name": "FileHandler",
			"args": {
				"output_folder" : config["output"]
			}
		}

		# try:
			#crawler_id = md5('%s:%s'%(self.node_id, idx))
			#apikeys = self.config['apikeys'][apikey_list[idx]]
		crawler_id = apikeys['app_key']
		logger.debug('creating a new crawler: %s'%crawler_id)
		if (not crawler_proxies):
			crawler_proxies = next(self.proxy_generator) if self.proxy_generator else None

		crawler = UserRelationshipCrawler(node_id, crawler_id, copy.copy(apikeys), handlers=[create_handler(file_handler_config)], redis_config=copy.copy(config['redis_config']), proxies=crawler_proxies)
		
		if (crawler_id in self.crawlers):
			#self.crawlers[crawler_id].clear()
			del self.crawlers[crawler_id]

		self.crawlers[crawler_id] = {
			'apikeys': apikeys,
			'crawler': crawler,
			'crawler_queue': CrawlerQueue(self.node_id, crawler_id, redis_config=copy.copy(config['redis_config'])),
			'crawler_proxies': crawler_proxies
		}
		crawler.start()
		# except twython.exceptions.TwythonAuthError as exc:
		# 	logger.error('%s: %s'%(exc, apikeys))
		# except Exception as exc:
		# 	logger.error(exc)
		# 	raise


	def is_alive(self):
		a = [1 if self.crawlers[crawler_id]['crawler'].is_alive() else 0 for crawler_id in self.crawlers]
		return sum(a) > 0

	def crawler_status(self):
		status = []
		for crawler_id in self.crawlers:
			cc = self.crawlers[crawler_id]
			if ((not cc['crawler'].is_alive())): 
				
				if ('retry_timer_start_ts' in cc and (time.time() - cc['retry_timer_start_ts'] > 1800)):
					# retry 30 mins after the crawler dies... mostly the crawler died because "Twitter API returned a 503 (Service Unavailable), Over capacity"
					self.new_crawler(self.node_id, cc['apikeys'], self.config, cc['crawler_proxies'])
					cc = self.crawlers[crawler_id]
					logger.info('[%s] has been recrated...'%(crawler_id))
				else:
					if('retry_timer_start_ts' not in cc):
						cc['retry_timer_start_ts'] = int(time.time())
					else:
						logger.warn('[%s] failed; waiting to recreat in %f mins...'%(crawler_id, (time.time() + 1800 - cc['retry_timer_start_ts'])/float(60)))

			status.append({'crawler_id':crawler_id, 'alive?': cc['crawler'].is_alive(), 'qsize': cc['crawler_queue'].qsize(), 'crawler_queue_key': cc['crawler_queue'].get_key()})

		return status

	def balancing_load(self):
		'''
		Find the crawler that has the most load at this moment, and redistribut its item;
		Crawler is on a different subprocess, so we have to use redis to coordinate the redistribution...
		'''

		sorted_queues = self.sorted_local_queue(False)
		max_crawler_id, max_qsize = sorted_queues[-1]
		min_crawler_id, min_qsize = sorted_queues[0]
		logger.info("crawler with max_qsize: %s (%d)"%(max_crawler_id, max_qsize))
		logger.info("crawler with min_qsize: %s (%d)"%(min_crawler_id, min_qsize))
		logger.info("max_qsize - min_qsize > 0.5 * min_qsize ?: %r"%((max_qsize - min_qsize > 0.5 * min_qsize)))
		if (max_qsize - min_qsize > 0.5 * min_qsize):
			logger.info("load balancing process started...")
			cmds = []
			controls = []
			for i in range(int(0.3 * (max_qsize - min_qsize))):
				cmd = self.crawlers[max_crawler_id]['crawler_queue'].get()
				if (cmd['cmd'] in control_cmds):
					controls.append(cmd)
				else:
					cmds.append(cmd)

			# push control cmds back..
			for cmd in controls:
				self.crawlers[max_crawler_id]['crawler_queue'].put(cmd)

			logger.info("redistribute %d cmds"%len(cmds))
			for cmd in cmds:
				self.enqueue(cmd)

	def redistribute_crawler_queue(self, crawler_id):
		if (crawler_id in self.crawlers):
			logger.warn('%s just failed... redistributing its workload'%(crawler_id))
			try:
				self.node_coordinator.distribute_to_nodes(self.crawlers[crawler_id]['crawler_queue'])
				wait_timer = 180
				# wait until it dies (flushed all the data...)
				while(self.crawlers[crawler_id]['crawler'].is_alive() and wait_timer > 0):
					time.sleep(60)
					wait_timer -= 60

				self.crawlers[crawler_id]['retry_timer_start_ts'] = int(time.time())
			except Exception as exc:
				logger.error(full_stack())
		else:
			logger.warn("whatever are you trying to do? crawler_id: [%s] is not valid..."%(crawler_id))

	def enqueue(self, cmd):
		
		if (cmd['cmd'] == 'TERMINATE'):			
			[self.crawlers[crawler_id]['crawler_queue'].put(cmd) for crawler_id in self.crawlers]
		elif(cmd['cmd'] == 'CRAWLER_FLUSH'):
			[self.crawlers[crawler_id]['crawler_queue'].put(cmd) for crawler_id in self.crawlers]
		elif(cmd['cmd'] == 'BALANCING_LOAD'):
			self.balancing_load()
		elif(cmd['cmd'] == 'CRAWLER_FAILED'):
			crawler_id = cmd['crawler_id']
			self.redistribute_crawler_queue(crawler_id)
		else:
			'''distribute item to the local crawler that has the least tasks in queue'''
			for crawler_id, qsize in self.sorted_local_queue(False):
				if self.crawlers[crawler_id]['crawler'].is_alive():
					self.crawlers[crawler_id]['crawler_queue'].put(cmd)

					logger.debug("pushed %s to crawler: %s"%(cmd, crawler_id))
					break

	def check_crawler_qsizes(self):
		return {crawler_id:self.crawlers[crawler_id]['crawler_queue'].qsize() for crawler_id in self.crawlers}

	def sorted_local_queue(self, reverse=False):
		local_qsizes = self.check_crawler_qsizes()
		return sorted(local_qsizes.iteritems(), key=itemgetter(1), reverse=reverse)

	def split(self, lst, n):
		""" Yield successive n chunks of even sized sub-lists from lst."""
		lsize = {}
		results = {}
		for i in range(n):
			lsize[i] = 0
			results[i] = []

		
		for x in lst:
			idx = get_keys_by_min_value(lsize)[0]
			results[idx].append(x)
			lsize[idx] += 1

		for i in range(n):
			yield results[i]

		
########NEW FILE########
__FILENAME__ = streams
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
stream.py: 

KeywordsStreamer: straightforward class that tracks a list of keywords; most of the jobs are done by TwythonStreamer; the only thing this is just attach a WriteToHandler so results will be saved

'''

import logging

logger = logging.getLogger(__name__)

from twython import TwythonStreamer
import os, copy, datetime, json

class KeywordsStreamer(TwythonStreamer):

	def __init__(self, *args, **kwargs):
		"""
		Constructor with some extra params:


		For other params see: TwythonStreamer
		"""
		from write_to_handler import WriteToHandler
		import copy

		self.write_to_handler = WriteToHandler(kwargs.pop('output', '.'))
		self.counter = 0
		apikeys = copy.copy(kwargs.pop('apikeys', None))

		if not apikeys:
			raise Exception('apikeys is missing')
		#print(kwargs)
		self.apikeys = copy.copy(apikeys) # keep a copy

		kwargs.update(apikeys)

		super(KeywordsStreamer, self).__init__(*args, **kwargs)


	def on_success(self, data):
		if 'text' in data:
			self.counter += 1
			if self.counter % 1000 == 0:
				logger.info("received: %d"%self.counter)
			#logger.debug(data['text'].encode('utf-8'))
			self.write_to_handler.append(json.dumps(data))

			
	def on_error(self, status_code, data):
		 logger.warn(status_code)

		
	def close(self):
		self.disconnect()
		self.write_to_handler.close()
		
########NEW FILE########
__FILENAME__ = users
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Users.py: all user related farming; friends, followers, user objects; etc.
You can use this raw class, but normally you will use a script in the scripts folder
'''

import logging

logger = logging.getLogger(__name__)

import twython
import json, os, time
from tweetf0rm.exceptions import NotImplemented, MissingArgs, WrongArgs

MAX_RETRY_CNT = 5
class User(twython.Twython):

	def __init__(self, *args, **kwargs):
		"""
		Constructor with apikeys, and output folder

		* apikeys: apikeys
		"""
		logger.info(kwargs)
		import copy

		apikeys = copy.copy(kwargs.pop('apikeys', None))
		
		if not apikeys:
			raise MissingArgs('apikeys is missing')

		self.apikeys = copy.copy(apikeys) # keep a copy
		#self.crawler_id = kwargs.pop('crawler_id', None)

		oauth2 = kwargs.pop('oauth2', True) # default to use oauth2 (application level access, read-only)

		if oauth2:
			apikeys.pop('oauth_token')
			apikeys.pop('oauth_token_secret')
			twitter = twython.Twython(apikeys['app_key'], apikeys['app_secret'], oauth_version=2)
			access_token = twitter.obtain_access_token()
			kwargs['access_token'] = access_token
			apikeys.pop('app_secret')
		
		kwargs.update(apikeys)

		super(User, self).__init__(*args, **kwargs)

		

	def rate_limit_error_occured(self, resource, api):
		rate_limits = self.get_application_rate_limit_status(resources=[resource])

		#e.g., ['resources']['followers']['/followers/list']['reset']

		wait_for = int(rate_limits['resources'][resource][api]['reset']) - time.time() + 10

		#logger.debug(rate_limits)
		logger.warn('[%s] rate limit reached, sleep for %d'%(rate_limits['rate_limit_context'], wait_for))
		if wait_for < 0:
			wait_for = 60

		time.sleep(wait_for)

	def find_all_followers(self, user_id=None, write_to_handlers = [], cmd_handlers=[], bucket="followers"):

		if (not user_id):
			raise MissingArgs("user_id cannot be None")

		retry_cnt = MAX_RETRY_CNT
		cursor = -1
		while cursor != 0 and retry_cnt > 1:
			try:
				followers = self.get_followers_list(user_id=user_id, cursor=cursor, count=200)

				for handler in write_to_handlers:
					handler.append(json.dumps(followers), bucket=bucket, key=user_id) 
				
				for handler in cmd_handlers:
					handler.append(json.dumps(followers), bucket=bucket, key=user_id) 

				cursor = int(followers['next_cursor'])
				
				logger.debug("find #%d followers... NEXT_CURSOR: %d"%(len(followers["users"]), cursor))
				time.sleep(2)
			except twython.exceptions.TwythonRateLimitError:
				self.rate_limit_error_occured('followers', '/followers/list')
			except Exception as exc:
				time.sleep(10)
				logger.debug("exception: %s"%exc)
				retry_cnt -= 1
				if (retry_cnt == 0):
					raise MaxRetryReached("max retry reached due to %s"%(exc))
				

		logger.debug("finished find_all_followers for %s..."%(user_id))


	def find_all_follower_ids(self, user_id=None, write_to_handlers = [], cmd_handlers=[], bucket = "follower_ids"):

		if (not user_id):
			raise MissingArgs("user_id cannot be None")

		retry_cnt = MAX_RETRY_CNT
		cursor = -1
		while cursor != 0 and retry_cnt > 1:
			try:
				follower_ids = self.get_followers_ids(user_id=user_id, cursor=cursor, count=200)

				for handler in write_to_handlers:
					handler.append(json.dumps(follower_ids), bucket=bucket, key=user_id)

				for handler in cmd_handlers:
					handler.append(json.dumps(follower_ids), bucket=bucket, key=user_id) 

				cursor = int(follower_ids['next_cursor'])

				logger.debug("find #%d followers... NEXT_CURSOR: %d"%(len(follower_ids["ids"]), cursor))
				time.sleep(2)
			except twython.exceptions.TwythonRateLimitError:
				self.rate_limit_error_occured('followers', '/followers/ids')
			except Exception as exc:
				time.sleep(10)
				logger.debug("exception: %s"%exc)
				retry_cnt -= 1
				if (retry_cnt == 0):
					raise MaxRetryReached("max retry reached due to %s"%(exc))


		logger.debug("finished find_all_follower_ids for %s..."%(user_id))


	def find_all_friends(self, user_id=None, write_to_handlers=[], cmd_handlers=[], bucket="friends"):

		if (not user_id):
			raise MissingArgs("user_id cannot be None")

		retry_cnt = MAX_RETRY_CNT
		cursor = -1
		while cursor != 0 and retry_cnt > 1:
			try:
				friends = self.get_friends_list(user_id=user_id, cursor=cursor, count=200)

				for handler in write_to_handlers:
					handler.append(json.dumps(friends), bucket=bucket, key=user_id)

				for handler in cmd_handlers:
					handler.append(json.dumps(friends), bucket=bucket, key=user_id) 

				cursor = int(friends['next_cursor'])

				logger.debug("find #%d friends... NEXT_CURSOR: %d"%(len(friends["users"]), cursor))

				time.sleep(2)
			except twython.exceptions.TwythonRateLimitError:
				self.rate_limit_error_occured('friends', '/friends/list')
			except Exception as exc:
				time.sleep(10)
				logger.debug("exception: %s"%exc)
				retry_cnt -= 1
				if (retry_cnt == 0):
					raise MaxRetryReached("max retry reached due to %s"%(exc))

		logger.debug("finished find_all_friends for %s..."%(user_id))


	def find_all_friend_ids(self, user_id=None, write_to_handlers=[], cmd_handlers=[], bucket="friend_ids"):

		if (not user_id):
			raise MissingArgs("user_id cannot be None")

		retry_cnt = MAX_RETRY_CNT
		cursor = -1
		while cursor != 0 and retry_cnt > 1:
			try:
				friend_ids = self.get_friends_ids(user_id=user_id, cursor=cursor, count=200)

				for handler in write_to_handlers:
					handler.append(json.dumps(friend_ids), bucket=bucket, key=user_id) 

				for handler in cmd_handlers:
					handler.append(json.dumps(friend_ids), bucket=bucket, key=user_id) 

				cursor = int(friend_ids['next_cursor'])

				logger.debug("find #%d friend_ids... NEXT_CURSOR: %d"%(len(friend_ids["ids"]), cursor))

				time.sleep(2)
			except twython.exceptions.TwythonRateLimitError:
				self.rate_limit_error_occured('friends', '/friends/ids')
			except Exception as exc:
				time.sleep(10)
				logger.debug("exception: %s"%exc)
				retry_cnt -= 1
				if (retry_cnt == 0):
					raise MaxRetryReached("max retry reached due to %s"%(exc))

		logger.debug("finished find_all_friend_ids for %s..."%(user_id))


	def fetch_user_timeline(self, user_id = None, write_to_handlers=[], cmd_handlers=[], bucket="timelines"):

		if not user_id:
			raise Exception("user_timeline: user_id cannot be None")


		prev_max_id = -1
		current_max_id = 0
		last_lowest_id = current_max_id # used to workaround users who has less than 200 tweets, 1 loop is enough...
		cnt = 0
		
		retry_cnt = MAX_RETRY_CNT
		timeline = [] # holder tweets in memory... you won't get more than 3,200 tweets per user, so I guess this is fine...
		while current_max_id != prev_max_id and retry_cnt > 1:
			try:
				if current_max_id > 0:
					tweets = self.get_user_timeline(user_id=user_id, max_id=current_max_id, count=200)
				else:
					tweets = self.get_user_timeline(user_id=user_id, count=200)

				prev_max_id = current_max_id # if no new tweets are found, the prev_max_id will be the same as current_max_id

				for tweet in tweets:
					if current_max_id == 0 or current_max_id > int(tweet['id']):
						current_max_id = int(tweet['id'])

				#no new tweets found
				if (prev_max_id == current_max_id):
					break;

				timeline.extend(tweets)

				cnt += len(tweets)

				logger.debug('%d > %d ? %s'%(prev_max_id, current_max_id, bool(prev_max_id > current_max_id)))

				time.sleep(1)

			except twython.exceptions.TwythonRateLimitError:
				self.rate_limit_error_occured('statuses', '/statuses/user_timeline')
			except Exception as exc:
				time.sleep(10)
				logger.debug("exception: %s"%exc)
				retry_cnt -= 1
				if (retry_cnt == 0):
					raise MaxRetryReached("max retry reached due to %s"%(exc))

		if (len(timeline) > 0):
			for tweet in timeline:
				for handler in write_to_handlers:
					handler.append(json.dumps(tweet), bucket=bucket, key=user_id)

				for handler in cmd_handlers:
					handler.append(json.dumps(tweet), bucket=bucket, key=user_id)
		else:
			for handler in write_to_handlers:
				handler.append(json.dumps({}), bucket=bucket, key=user_id)

		logger.debug("[%s] total tweets: %d "%(user_id, cnt))		

	def fetch_tweet_by_id(self, tweet_id = None, write_to_handlers=[], cmd_handlers=[], bucket="tweets"):

		if not tweet_id:
			raise Exception("show_status: tweet_id cannot be None")

		tweet = None
		retry_cnt = MAX_RETRY_CNT
		while retry_cnt > 1:
			try:
				tweet = self.show_status(id=tweet_id)

				# logger.debug('%d > %d ? %s'%(prev_max_id, current_max_id, bool(prev_max_id > current_max_id)))
				logger.info("Fetched tweet [%s]" % (tweet_id))

				break

			except twython.exceptions.TwythonRateLimitError:
				self.rate_limit_error_occured('statuses', '/statuses/show')
			except twython.exceptions.TwythonError as te:
				if ( te.error_code == 404 or te.error_code == 403 ):
					logger.info("Tweet [%s] unavailable. Error code: %d" % (tweet_id, te.error_code))

					break
				else:
					time.sleep(10)
					logger.error("exception: %s"%(te))
					retry_cnt -= 1
					if (retry_cnt == 0):
						raise MaxRetryReached("max retry reached due to %s"%(te))
			except Exception as exc:
				time.sleep(10)
				logger.error("exception: %s, %s"%(exc, type(exc)))
				retry_cnt -= 1
				if (retry_cnt == 0):
					raise MaxRetryReached("max retry reached due to %s"%(exc))

		if (tweet != None):
			for handler in write_to_handlers:
				handler.append(json.dumps(tweet), bucket=bucket, key="tweetList")
		else:
			for handler in write_to_handlers:
				handler.append(json.dumps({"id":tweet_id}), bucket=bucket, key="tweetList")

		logger.debug("[%s] tweet fetched..." % tweet_id)


	def get_user_ids_by_screen_names(self, seeds):
		#get user id first
		screen_names = list(set(seeds))
		user_ids = set()		

		if len(screen_names) > 0:
			users = self.lookup_user(screen_name=screen_names)

			for user in users:
				user_ids.add(user['id'])

		return user_ids

	def get_users(self, seeds):
		#get user id first
		user_ids = list(set(seeds))
		users = set()
	

		if len(user_ids) > 0:
			users = self.lookup_user(user_id=user_ids)

		return users


		
########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Singleton(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

import requests, json, traceback, sys

def get_keys_by_min_value(qsizes):
	'''
	return a list of keys (crawler_ids) that have the minimum number of pending cmds
	'''

	min_v = min(qsizes.values())

	return [node_id for node_id in qsizes if qsizes[node_id] == min_v]
	
def full_stack():
	exc = sys.exc_info()[0]
	stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
	if not exc is None:  # i.e. if an exception is present
		del stack[-1]       # remove call of full_stack, the printed exception
							# will contain the caught exception caller instead
	trc = 'Traceback (most recent call last):\n'
	stackstr = trc + ''.join(traceback.format_list(stack))
	if not exc is None:
		 stackstr += '  ' + traceback.format_exc().lstrip(trc)
	return stackstr


def public_ip():
	r = requests.get('http://httpbin.org/ip')
	return r.json()['origin']

import hashlib
def md5(data):
	return hashlib.md5(data).hexdigest()

def hash_cmd(cmd):
	return md5(json.dumps(cmd))

def node_id():
	ip = public_ip()
	return md5(ip)

########NEW FILE########
