__FILENAME__ = Miners
import bitHopper.Database.Commands
import bitHopper.Database
import random
miners = None

def __patch():
    global miners
    if miners == None:
        miners = load_from_db()

def load_from_db():
    """
    Load miners from database
    """
    columns = [ 'Username TEXT',
                'Password TEXT']

    bitHopper.Database.Commands.Create_Table('Miners', columns)
    results = bitHopper.Database.execute('SELECT Username, Password FROM Miners')

    miners = set()

    for username, password in results:
        miners.add((username, password))

    return miners

def len_miners():
    """
    Returns the length of the worker table
    """
    __patch()
    return len(miners)

def get_miners():
    """
    Returns a list of workers
    """
    __patch()
    miners_l = list(miners)
    miners_l.sort()
    return miners_l

def valid(username, password):
    """
    Check if a username, password combination is valid
    """
    __patch()
    if len(miners) == 0:
        return True
    return (username, password) in miners

def add(username, password):
    """
    Adds a miner into the database and the local cache
    """
    __patch()
    if (username, password) not in miners:
        miners.add((username, password))
        bitHopper.Database.execute("INSERT INTO Miners VALUES ('%s','%s')" % (username, password))

def remove(username, password):
    """
    Removes a miner from the local cache and the database
    """
    __patch()
    if (username, password) not in miners:
        return
    miners.remove((username, password))
    bitHopper.Database.execute("DELETE FROM Miners WHERE Username = '%s' AND Password = '%s'" % (username, password))

########NEW FILE########
__FILENAME__ = Pools
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact:
# Colin Rice colin@daedrum.net

"""
File for configuring multiple pools
Things such as priority, percentage etc...
"""
import bitHopper.Database.Commands
import bitHopper.Database
import random
pools = None

def __patch():
    global pools
    if pools == None:
        pools = load_from_db()

def load_from_db():
    """
    Load pools from database
    """
    columns = [ 'Server TEXT',
                'Percentage INTEGER',
                'Priority INTEGER']

    bitHopper.Database.Commands.Create_Table('Pools', columns)
    results = bitHopper.Database.execute('SELECT Server, Percentage, Priority FROM Pools')

    pools = {}

    for server, percentage, priority in results:
        if server not in pools:
            pools[server]  = {'percentage':percentage, 'priority':priority}
        else:
            #Really should delete the duplicate entry
            pass

    return pools

def len_pools():
    """
    Return the number of pools with special things
    """
    __patch()
    return len(pools)

def set_priority(server, prio):
    """
    Sets pool priority, higher is better
    It also sets percentage if the server does not exist
    """
    __patch()
    if server not in pools:
        pools[server] = {'priority':0, 'percentage':0}
    pools[server]['priority'] = int(prio)
    bitHopper.Database.execute("INSERT INTO Pools VALUES ('%s',%s,%s)" % (server, int(prio), 0))

def get_priority(server):
    """
    Gets pool priority
    """
    __patch()
    if server not in pools:
        return 0
    return pools[server]['priority']

def set_percentage(server, perc):
    """
    Sets pool percentage, the amount of work we should always feed to the server
    It also sets priority if the server does not exist
    """
    __patch()
    if server not in pools:
        pools[server] = {'priority':0, 'percentage':0}
    pools[server]['percentage'] = int(perc)
    bitHopper.Database.execute("INSERT INTO Pools VALUES ('%s',%s,%s)" % (server, 0, int(perc)))

def get_percentage(server):
    """
    Gets pool percentage
    """
    __patch()
    if server not in pools:
        return 0
    return pools[server]['percentage']

def percentage_server():
    """
    Gets all server with a percentage
    """
    __patch()
    for server, info in pools.items():
        if info['percentage'] > 0:
            yield server, info['percentage']


########NEW FILE########
__FILENAME__ = Workers
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

"""
File for configuring multiple workers

TODO: FIX ALL THE SQL INJECTIONS. EVERYONE OF THESE THINGS IS FULL OF THEM
"""
import bitHopper.Database.Commands
import bitHopper.Database
import random
workers = None

def __patch():
    global workers
    if workers == None:
        workers = load_from_db()
        
def load_from_db():
    """
    Load workers from database
    """
    columns = [ 'Server TEXT',
                'Username TEXT',
                'Password TEXT']
    
    bitHopper.Database.Commands.Create_Table('Workers', columns)
    results = bitHopper.Database.execute('SELECT Server, Username, Password FROM Workers')
    
    workers = {}
    
    for server, username, password in results:
        if server not in workers:
            workers[server]  = set()
        workers[server].add((username, password))
        
    return workers
    
def len_workers():
    __patch()
    return sum(map(len, workers.values()))
        
    
def get_worker_from(pool):
    """
    Returns a list of workers in the given pool
    In the form of [(Username, Password), ... ]
    """
    __patch()
    if pool not in workers:
        return []
    return workers[pool]
    
def get_single_worker(pool):
    """
    Returns username, password or None, None
    """
    possible = get_worker_from(pool)
    if len(possible) == 0:
        return None, None
        
    return random.choice(list(possible))
    
def add(server, username, password):
    """
    Adds a worker into the database and the local cache
    """
    __patch()
    if server not in workers:
        workers[server] = set()
    if (username, password) not in workers[server]:
        workers[server].add((username, password))
        bitHopper.Database.execute("INSERT INTO Workers VALUES ('%s','%s','%s')" % (server, username, password))
    
def remove(server, username, password):
    """
    Removes a worker from the local cache and the database
    """
    __patch()
    if server not in workers:
        return
    if (username, password) not in workers[server]:
        return
    workers[server].remove((username, password))
    if workers[server] == set([]):
        del workers[server]
    bitHopper.Database.execute("DELETE FROM Workers WHERE Server = '%s' AND Username = '%s' AND Password = '%s'" % (server, username, password))
        

    
    

########NEW FILE########
__FILENAME__ = Commands
from . import execute

def Create_Table(name, columns):
    """
    Checks for the existance of a table and creates it if it does not exist
    """
    
    column_string = ", ".join(columns)
    sql = 'CREATE TABLE IF NOT EXISTS %s ( %s )' % (name, column_string)
    execute(sql)

########NEW FILE########
__FILENAME__ = Unlag
"""
Deals with lagging logic for the system
"""

import btcnet_info
import gevent
import bitHopper.Network as Network
import bitHopper.LaggingLogic
import logging, traceback

def _unlag_fetcher(server, worker, password):
    """
    Actually fetches and unlags the server
    """
    try:
        url = btcnet_info.get_pool(server)['mine.address']
        work = Network.send_work(url, worker, password)
        if work:
            bitHopper.LaggingLogic.lagged.remove((server, worker, password))
            return
    except:
        logging.debug(traceback.format_exc())
        pass
   
def _unlag():
    """
    Function that checks for a server responding again
    """
    while True:
        for server, worker, password in bitHopper.LaggingLogic.lagged:
            gevent.spawn(_unlag_fetcher, server, worker, password)
               
        gevent.sleep(60)

gevent.spawn(_unlag)

########NEW FILE########
__FILENAME__ = ServerLogic
"""
File implementing the actuall logic for the business side
"""

import btcnet_info
import bitHopper.Configuration.Workers as Workers
import bitHopper.Configuration.Pools as Pools
import bitHopper.LaggingLogic
import logging, traceback, gevent, random

def _select(item):
    """
    Selection utility function
    """
    global i
    i = i + 1 if i < 10**10 else 0
    if len(item) == 0:
        raise ValueError("No valid pools")
    return item[i % len(item)]

def difficulty_cutoff(source):
    """
    returns the difficulty cut off for the pool
    """

    diff = btcnet_info.get_difficulty(source.coin)
    btc_diff = btcnet_info.get_difficulty(source.coin)
    if not diff:
        return 0
        #while not diff:
        #    gevent.sleep(0)
        #    diff = btcnet_info.get_difficulty(source.coin)

    diff = float(diff)
    btc_diff = float(btc_diff)

    #Propositional Hopping
    if source.payout_scheme in ['prop']:
        return diff * 0.435

    #Score Hopping
    if source.payout_scheme in ['score']:
        c = source.mine.c if source.mine and source.mine.c else 300
        c = float(c)
        hashrate = float(source.rate) / (10. ** 9) if source.rate else 1
        hopoff = btc_diff * (0.0164293 + 1.14254 / (1.8747 * (btc_diff / (c * hashrate)) + 2.71828))
        return hopoff

def highest_priority(source):
    """
    Filters pools by highest priority
    """
    max_prio = 0
    pools = list(source)
    for pool in pools:
        name = pool.name
        if not name:
            continue
        if Pools.get_priority(name)>max_prio:
            max_prio = Pools.get_priority(name)

    for pool in pools:
        name = pool.name
        if not name:
            continue
        if Pools.get_priority(name)>=max_prio:
            yield pool

def valid_scheme( source):
    """
    This is a generator that produces servers where the shares are hoppable or the method is secure(SMPPS etc...)
    """
    for site in source:

        #Check if we have a payout scheme
        scheme = site.payout_scheme
        if not scheme:
            continue

        #Check if this is a secure payout scheme
        if scheme.lower() in ['pps', 'smpps', 'pplns', 'dgm']:
            yield site

        if scheme.lower() in ['prop', 'score']:

            #Check if we have a share count
            shares = site.shares
            if not shares:
                continue

            shares = float(shares)
            if shares < difficulty_cutoff(site):
                yield site

def valid_credentials( source):
    """
    Only allows through sites with valid credentials
    """
    for site in source:

        #Pull Name
        name = site.name
        if not name:
            continue

        workers = Workers.get_worker_from(name)
        if not workers:
            continue

        for user, password in workers:
            if len(list(bitHopper.LaggingLogic.filter_lag([(name, user, password)]))):
                yield site


def filter_hoppable( source):
    """
    returns an iterator of hoppable pools
    """

    for pool in source:
        if not pool.payout_scheme:
            continue
        if pool.payout_scheme.lower() in ['prop','score']:
            yield pool

def filter_secure( source):
    """
    Returns an iterator of secure pools
    """

    for pool in source:
        if not pool.payout_scheme:
            continue
        if pool.payout_scheme.lower() in ['pplns', 'smpps', 'pps', 'dgm']:
            yield pool

def filter_best( source):
    """
    returns the best pool or pools we have
    """
    pools = [x for x in source]
    #See if we have a score or a prop pool
    hoppable = list(filter_hoppable( pools))

    if hoppable:
        pool_ratio = lambda pool: float(pool.shares) / difficulty_cutoff(pool)
        min_ratio = min( map(pool_ratio, hoppable))
        for pool in hoppable:
            if pool_ratio(pool) == min_ratio:
                yield pool
        return

    #Select a backup pool
    backup = list(filter_secure(pools))
    if backup:
        for x in backup:
            yield x
        return

    raise ValueError("No valid pools configured")

def generate_servers():
    """
    Method that generate the best server
    """
    while True:
        rebuild_servers()
        gevent.sleep(5)

filters = [valid_credentials, valid_scheme, highest_priority, filter_best]

def rebuild_servers():
    """
    The function the rebuilds the set of servers
    """
    try:
        global Servers
        servers = btcnet_info.get_pools().copy()
        for filter_f in filters:
            servers = filter_f(servers)
        Servers = list(servers)
    except ValueError as Error:
        logging.warn(Error)
    except Exception as Error:
        logging.error(traceback.format_exc())

def get_server():
    """
    Returns an iterator of valid servers
    """
    perc_map = []
    map_ods = 0.0
    percentage = Pools.percentage_server()
    for server, percentage in percentage:
        for perc in range(percentage):
            perc_map.append(server)
            map_ods += 0.01
    if random.random() < map_ods:
        return random.choice(perc_map)

    return _select(Servers).name

def get_current_servers():
    return Servers

i = 1
Servers = set()
gevent.spawn(generate_servers)
gevent.sleep(0)

########NEW FILE########
__FILENAME__ = LongPoll
"""
Simple module that blocks longpoll sockets until we get a longpoll back
"""

from gevent.event import AsyncResult

_event = AsyncResult()

def wait():
    """
    Gets the New Block work unit to send to clients
    """
    return _event.get()

def trigger(work):
    """
    Call to trigger a LP
    """
    global _event
    old = _event
    _event = AsyncResult()
    old.set(work)

########NEW FILE########
__FILENAME__ = Conversion
"""
Various usefull conversions for the LP system
"""


def bytereverse(value):
    """ 
    Byte reverses data
    """
    bytearray = []
    for i in xrange(0, len(value)):
        if i % 2 == 1:
            bytearray.append(value[i-1:i+1])
    return "".join(bytearray[::-1])

def wordreverse(in_buf):
    """
    Does a word based reverse
    """
    out_words = []
    for i in range(0, len(in_buf), 4):
        out_words.append(in_buf[i:i+4])
    out_words.reverse()
    out_buf = ""
    for word in out_words:
        out_buf += word
    return out_buf

def extract_block(response):
    """
    Extracts the block from the LP
    """
    data = response['result']['data']
    block = data.decode('hex')[0:64]
    block = wordreverse(block)
    block = block.encode('hex')[56:120]
    
    return block

########NEW FILE########
__FILENAME__ = Learning
import random
import btcnet_info
import gevent
import logging
import json
from collections import defaultdict

import bitHopper.Logic
import bitHopper.Network

try:
    import numpy as np
except ImportError:
    np = None

blocks_timing = {}
blocks_calculated = {}
blocks_actual = {}

#wait for these pools before calculating results
used_pools = ['deepbit']
weights = [-1, 0]

def set_neg(block):
    if block not in blocks_actual:
        blocks_actual[block] = 0

def learn_block(blocks, current_block):
    print 'learn_block called'
    #import block data
    for block in blocks:
        if block not in blocks_timing:
            blocks_timing[block] = blocks[block]
            gevent.spawn_later(60*60*1.5, set_neg, block)

    #update current_block
    if len(blocks[current_block]) < len(blocks_timing[current_block]):
        blocks_timing[current_block] = blocks[current_block]

    #determine if we should do a prediction
    if have_all_data(blocks[current_block]):
        calculate_block(current_block)

def have_all_data(block_info):
    for pool in used_pools:
        if pool not in block_info:
            return False
    return True

def vec_mult(a, b):
    return sum([i*j for i, j in zip(a,b)])

def extract_vector(current_block):
    result = [1]
    for pool in used_pools:
        result.append(blocks_timing[current_block][pool])
    return result

def calculate_block(current_block):
    print 'calculate block called'
    if vec_mult(weights, extract_vector(current_block)) > 0:
        print 'triggered'
        btcnet_info.get_pool('deepbit').namespace.get_node('shares').set_value(0)
        #Reset shares on deepbit
        blocks_calculated[current_block] = 1
    else:
        blocks_calculated[current_block] = 0

def check_learning():
    print 'Check learning started'
    while True:
        gevent.sleep(60)
        deepbit_blocks = set(json.loads(btcnet_info.get_pool('deepbit').blocks))
        for block in blocks_timing:
            if block in blocks_actual and blocks_actual[block] == 1:
                continue
            if block in deepbit_blocks:
                blocks_actual[block] = 1
                print 'Block %s has training value %s' % (block, blocks_actual[block])

#Connect to deepbit if possible    
def poke_deepbit():
    choices = list(bitHopper.Logic.generate_tuples('deepbit'))
    if len(choices) == 0:
        logging.info('No workers for deepbit. Disabling machine learning') 
        return
    server, username, password = random.choice(choices)
    url = btcnet_info.get_pool(server)['mine.address']
    bitHopper.Network.send_work_lp(url, username, password, 'deepbit')

def calc_good_servers():
    used_pools = set()
    used_pools.add('deepbit')

    def yield_timings_block(blocks):
        for block in blocks:
            for server in block:
                yield server
    times_found = list(yield_timings_block(block for name, block in blocks_timing.iteritems()))
    def make_count_map(servers):
        count = defaultdict(int)
        for server in servers:
            count[server] += 1
        return sorted(list(count.iteritems()), key=lambda x: -1 * x[1])

    counts = make_count_map(times_found)
    #Use the top level of info, plus deepbit
    if not counts:
        return used_pools
    cutoff = counts[0][1]
    for server, count in counts:
        if count >= cutoff:
            used_pools.add(server)

    return used_pools

def linreg(data):
    ydata = [p[-1] for p in data]
    xdata = [[1] + p[:-1] for p in data]
    l = 0.00001
    n = len(xdata[0])
    Z = np.matrix(xdata)
    wreg = (Z.T * Z + np.identity(n)*l).I*Z.T*np.matrix(ydata).T
    return [float(d) for d in list(wreg)]

def train_data():
    if np == None:
        return
    while True:
        servers = calc_good_servers()

        global used_pools
        used_pools = servers

        data = []
        for block in blocks_timing:
            if not blocks_actual.get(block, None):
                continue
            point = [block.get(server, 10000) for server in servers]
            point.append(blocks_actual.get(block))
            data.append(point)

        global weights
        if data:
            weights = linreg(data)

        gevent.sleep(60*5)

gevent.spawn(train_data)
gevent.spawn(poke_deepbit)
gevent.spawn(check_learning)

########NEW FILE########
__FILENAME__ = headers
"""
Functions for manipulating headers for bitHopper
"""


def clean_headers_client(header):
    """
    Only allows through headers which are safe to pass to the server
    """
    valid = ['user_agent', 'x-mining-extensions', 'x-mining-hashrate']
    for name, value in header.items():
        if name.lower() not in valid:
            del header[name]
        else:
            del header[name]
            header[name.lower()] = value
        if name.lower() == 'x-mining-extensions':
            allowed_extensions=['midstate', 'rollntime']
            header[name.lower()] = ' '.join([
                x for x in header[name.lower()].split(' ') if
                x in allowed_extensions])
    return header
    
def clean_headers_server(header):
    """
    Only allows through headers which are safe to pass to the client
    """
    valid = ['content-length', 'content-type', 'x-roll-ntime', 
             'x-reject-reason', 'noncerange']
    for name, value in header.items():
        if name.lower() not in valid:
            del header[name]
        else:
            del header[name]
            header[name.lower()] = value
    return header
        
    
def get_headers(environ):
    """
    Returns headers from the environ
    """
    headers = {}
    for name in environ:
        if name[0:5] == "HTTP_":
            headers[name[5:]] = environ[name]
    return headers

########NEW FILE########
__FILENAME__ = getwork_store
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact:
# Colin Rice colin@daedrum.net

import gevent, time, logging

class Getwork_Store:
    """
    Class that stores getworks so we can figure out the server again
    """

    def __init__(self):
        self.data = {}
        gevent.spawn(self.prune)

    def add(self, merkle_root, data):
        """
        Adds a merkle_root and a data value
        """
        self.data[merkle_root] = (data, time.time())

    def get(self, merkle_root):
        ""
        if self.data.has_key(merkle_root):
            return self.data[merkle_root][0]
        logging.debug('Merkle Root Not Found %s', merkle_root)
        return None

    def drop_roots(self):
        """
        Resets the merkle_root database
        Very crude.
        Should probably have an invalidate block function instead
        """
        self.data = {}

    def prune(self):
        """
        Running greenlet that prunes old merkle_roots
        """
        while True:
            for key, work in self.data.items():
                if work[1] < (time.time() - (60*20)):
                    del self.data[key]
            gevent.sleep(60)

########NEW FILE########
__FILENAME__ = speed
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import gevent
import time, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Speed():
    """
    This class keeps track of the number of shares and
    tracks a running rate in self.rate
    
    Add shares with
    a = Speed()
    a.add_shares(1)
    
    Get the rate with 
    a.get_rate()
    
    Note rates are tallied once per minute.
    
    """
    def __init__(self):
        self.shares = 0
        gevent.spawn(self.update_rate)
        self.rate = 0
        self.old_time = time.time()

    def add_shares(self, share):
        self.shares += share

    def update_rate(self, loop=True):
        while True:
            now = time.time()
            diff = now -self.old_time
            if diff <= 0:
                diff = 1e-10
            self.old_time = now
            self.rate = int((float(self.shares) * (2**32)) / (diff * 1000000))
            self.shares = 0
            
            if loop:
                gevent.sleep(60)
            else:
                return
            

    def get_rate(self):
        return self.rate

########NEW FILE########
__FILENAME__ = Tracking
import bitHopper.Database
import bitHopper.Database.Commands
import btcnet_info
import logging, time, traceback, gevent
import bitHopper.Configuration.Pools
from speed import Speed

def get_diff(pool):
    coin = btcnet_info.get_pool(pool)
    if coin:
        coin = coin.coin
    else:
        coin = 'btc'
    return float(btcnet_info.get_difficulty(coin))

getworks = None
accepted = None
rejected = None
hashrate = Speed()

def build_dict():
    """
    Returns a dict with tuples of getworks, accepted, reject, priority, percentage
    """
    __patch()
    res = {}
    for key in getworks:
        server, username, password, diff = key
        if key not in accepted:
            accepted[key] = 0
        if key not in rejected:
            rejected[key] = 0
        if server not in res:
            res[server] = {}
        name = ":".join([shorten(username), password])
        if name not in res[server]:
            res[server][name] = [0, 0, 0, 0, 0]
        res[server][name][0] += getworks[key]
        res[server][name][1] += accepted[key]
        res[server][name][2] += rejected[key]
        res[server][name] = map(int, res[server][name])
    return res

def __patch():
    global getworks, accepted, rejected
    
    if getworks == None:
        getworks, accepted, rejected = load_from_db()
        gevent.spawn(looping_store)
        
def shorten(name):
    """
    Shortens a name and adds some ellipses
    """
    if len(name) > 10:
        name = name[:10] + '...'
    return name
    
def looping_store():
    """
    repeatedly calls store_current and sleep in between
    """
    while True:
        gevent.sleep(30)
        try:
            store_current()
        except:
            logging.error(traceback.format_exc())
    
def store_current():
    """
    Stores the current logs in the database
    """
    for key, getwork_c in getworks.items():
        accepted_c = accepted.get(key, 0)
        rejected_c = rejected.get(key, 0)
        #Extract key information
        server = key[0]
        username = key[1]
        password = key[2]
        difficulty = key[3]
        timestamp = time.asctime(time.gmtime())
        
        #If this isn't the current difficulty we are not responsible for storing it
        try:
            if get_diff(server) != difficulty:
                continue
        except:
            logging.error(traceback.format_exc())
            continue
            
        #Do an update
        sql = "UPDATE Statistics SET Getworks = %s, Accepted = %s, Rejected = %s, Timestamp = '%s' WHERE Server = '%s' AND Username = '%s' AND Password = '%s' AND Difficulty = %s" % (getwork_c, accepted_c, rejected_c, timestamp, server, username, password, difficulty)
        bitHopper.Database.execute(sql)
        
        #Check if we actually updated something
        result = bitHopper.Database.execute('SELECT Getworks from Statistics WHERE Server = "%s" AND Username = "%s" AND Password = "%s" AND Difficulty = %s' % (server, username, password, difficulty))
        result = list(result)
        
        #If we didn't do an insert
        if len(result) == 0:
            sql = "INSERT INTO Statistics (Server, Username, Password, Difficulty, Timestamp, Getworks, Accepted, Rejected) VALUES ('%s', '%s', '%s', %s, '%s', %s, %s, %s)" % (server, username, password, difficulty, timestamp, getwork_c, accepted_c, rejected_c)
            bitHopper.Database.execute(sql)
        
            
        
def load_from_db():
    """
    Load workers from database
    """
    columns = [ 'Server TEXT',
                'Username TEXT',
                'Password TEXT', 
                'Difficulty REAL',
                'Timestamp TEXT',
                'Getworks REAL',
                'Accepted REAL',
                'Rejected REAL']
    
    bitHopper.Database.Commands.Create_Table('Statistics', columns)
    results = bitHopper.Database.execute('Select Server, Username, Password, Difficulty, Getworks, Accepted, Rejected FROM Statistics')
    
    getworks = {}
    accepted = {}
    rejected = {}
    
    for server, username, password, difficulty, getworks_v, accepted_v, rejected_v in results:
        key = (server, username, password, difficulty)
        getworks[key] = getworks_v
        accepted[key] = accepted_v
        rejected[key] = rejected_v
        
    return getworks, accepted, rejected

def get_key(server, username, password):
    """
    Builds a key to access the dictionaries
    """
    difficulty = get_diff(server)
    key = (server, username, password, difficulty)
    return key
    
def add_getwork(server, username, password):
    """
    Adds a getwork to the database
    """
    __patch()
    key = get_key(server, username, password)
    if key not in getworks:
        getworks[key] = 0
    getworks[key] += 1
    username = shorten(username)
    logging.info('Getwork: %s:%s@%s' % (username, password, server))
    

def add_accepted(server, username, password):
    """
    Adds an accepted result to the database
    """
    __patch()
    key = get_key(server, username, password)
    if key not in accepted:
        accepted[key] = 0
    accepted[key] += 1
    username = shorten(username)
    hashrate.add_shares(1) 
    logging.info('Accepted: %s:%s@%s' % (username, password, server))
    
def add_rejected(server, username, password):
    """
    Adds a rejected result to the database
    """
    __patch()
    key = get_key(server, username, password)
    if key not in rejected:
        rejected[key] = 0
    rejected[key] += 1
    username = shorten(username)
    hashrate.add_shares(1)
    logging.info('Rejected: %s:%s@%s' % (username, password, server))

def get_hashrate():
    return hashrate.get_rate()

########NEW FILE########
__FILENAME__ = util
"""
Utility functions for bitHopper
"""

import json, logging

def validate_rpc(content):
    """
    Validates that this is a valid rpc message for our purposes
    """
    if type(content) != type({}):
        return False
    required = {'params':None, 'id':None, 'method':'getwork'}
    for key, value in required.items():
        if key not in content:
            return False
        if value and content[key] != value:
            return False
    
    return True
    
def validate_rpc_recieved(content):
    """
    Validates that this is a valid rpc message for our purposes
    """
    required = {'result':None, 'id':None, 'error':None}
    for key, value in required.items():
        if key not in content:
            return False
        if value and content[key] != value:
            return False
    
    return True
    
def extract_merkle(content):
    """
    extracts the merkle root
    """
    if 'params' not in content:
        logging.info('Malformed sendwork')
        return None
    if len(content['params']) != 1:
        logging.info('Malformed sendwork')
        return None
    if len(content['params'][0])<136:
        logging.info('Malformed sendwork')
        return None
        
    merkle = content['params'][0][72:136]
    return merkle

def extract_merkle_recieved(content):
    """
    extracts the merkle root for a message we recieved
    """
    if not validate_rpc_recieved(content):
        return None
    merkle = content['result']['data'][72:136]
    return merkle
    
def extract_result(content):
    """
    extracts the result
    """
    result = content['result']
    return result
    

def rpc_error(message = 'Invalid Request'):
    """
    Generates an rpc error message
    """
    return json.dumps({"result":None, 'error':{'message':message}, 'id':1})


########NEW FILE########
__FILENAME__ = Data_Page
from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
from bitHopper.Logic.ServerLogic import get_current_servers, valid_scheme
from bitHopper.Tracking.Tracking import get_hashrate
import logging
import json
import btcnet_info
from flask import Response
 
def transform_data(servers):
    for server in servers:
        item = {}
        for value in ['name', 'shares', 'coin']:
            if getattr(server, value) != None:
                item[value] = getattr(server, value)
            else:
                item[value] = 'undefined'
        item['shares'] = float(item.get('shares',0)) if item['shares'] != 'undefined' else 'undefined'
        item['payout'] = 0.0
        item['expected_payout'] = 0.0
        item['role'] = 'mine/backup' if server in valid_scheme([server]) else 'info'
        yield item
   
@app.route("/data", methods=['POST', 'GET'])
def data():
    response = {}
    response['current'] = ', '.join([s.name for s in get_current_servers()])
    response['mhash'] = get_hashrate() 
    response['diffs'] = dict([(coin.name, float(coin.difficulty)) for coin in btcnet_info.get_coins() if coin.difficulty])
    response['sliceinfo'] = None
    response['servers'] = list(transform_data(btcnet_info.get_pools())) 
    response['user'] = None
    
    return Response(json.dumps(response), mimetype='text/json') 

########NEW FILE########
__FILENAME__ = Miner_Page
from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Miners
    
@app.route("/miners", methods=['POST', 'GET'])
def miner():

    #Check if this is a form submission
    handle_miner_post(flask.request.form)
    
    #Get a list of currently configured miners
    miners = bitHopper.Configuration.Miners.get_miners()    
    return flask.render_template('miner.html', miners=miners) 
    
def handle_miner_post(post):
    for item in ['method','username','password']: 
        if item not in post:
            return
    
    if post['method'] == 'remove':
        bitHopper.Configuration.Miners.remove(
                post['username'], post['password'])
                
    elif post['method'] == 'add':
        bitHopper.Configuration.Miners.add(
                post['username'], post['password'])

########NEW FILE########
__FILENAME__ = Pool_Page
from bitHopper.Website import app, flask
import bitHopper.Tracking.Tracking
import bitHopper.Configuration.Pools

@app.route("/pool", methods=['POST', 'GET'])
def pool():

    handle_worker_post(flask.request.form)

    pools = bitHopper.Tracking.Tracking.build_dict()
        
    percentage = {}
    priority = {}
    for pool in pools:
        priority[pool] = bitHopper.Configuration.Pools.get_priority(pool)
        percentage[pool] = bitHopper.Configuration.Pools.get_percentage(pool)
        
    return flask.render_template('pool.html', pools = pools, percentage=percentage, priority=priority)
    
def handle_worker_post(post):
    """
    Handles worker priority and percentage change operations
    """
    
    for item in ['method','server','percentage', 'priority']:
        if item not in post:
            return
    
    if post['method'] == 'set':
        pool = post['server']
        percentage = float(post['percentage'])
        priority = float(post['priority'])
        bitHopper.Configuration.Pools.set_percentage(
                pool, percentage)
        bitHopper.Configuration.Pools.set_priority(
                pool, priority)
                

########NEW FILE########
__FILENAME__ = Stats_Page
from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Miners
    
@app.route("/stats", methods=['POST', 'GET'])
def stats():
    return flask.render_template('stats.html') 

########NEW FILE########
__FILENAME__ = Worker_Page
from bitHopper.Website import app, flask
import btcnet_info
import bitHopper.Configuration.Workers
import logging
    
@app.route("/worker", methods=['POST', 'GET'])
def worker():

    #Check if this is a form submission
    handle_worker_post(flask.request.form)
    
    #Get a list of currently configured workers
    pools_workers = {}
    for pool in btcnet_info.get_pools():
        if pool.name is None:
            logging.debug('Ignoring a Pool. If no pools apear on /worker please update your version of btcnet_info')
            continue
        pools_workers[pool.name] = bitHopper.Configuration.Workers.get_worker_from(pool.name)
        
    return flask.render_template('worker.html', pools = pools_workers)
    
def handle_worker_post(post):
    for item in ['method','username','password', 'pool']:
        if item not in post:
            return
    
    if post['method'] == 'remove':
        bitHopper.Configuration.Workers.remove(
                post['pool'], post['username'], post['password'])
                
    elif post['method'] == 'add':
        bitHopper.Configuration.Workers.add(
                post['pool'], post['username'], post['password'])

########NEW FILE########
__FILENAME__ = profile
"""
Starts up with a gevent based profiler. Probably superfluous and
the profiler doesn't work
"""

import bitHopper
import gevent
import argparse
import logging

def parse_config():
    """
    Parses the low level bitHopper configuration
    """
    parser = argparse.ArgumentParser(
            description='Process bitHopper CommandLine Arguments')
    parser.add_argument('--mine_port', metavar='mp', type=int, 
                    default=8337, help='Mining Port Number')
                   
    parser.add_argument('--config_port', metavar='cp', type=int, 
                    default=8339, help='Configuration Port Number')
                    
    parser.add_argument('--mine_localname', metavar='cp', type=str, 
                    default='', help='Dns name to bind to')
                    
    parser.add_argument('--config_localname', metavar='cp', type=str, 
                    default='', help='Dns name to bind to')
                    
    parser.add_argument('--debug', action="store_true", default=False)
                    
    args = parser.parse_args()
    return args
    
def run():
    """Main driver function"""
    args = parse_config()
    
    #Setup debugging output
    bitHopper.setup_logging(logging.DEBUG if args.debug else logging.INFO)
        
    #Setup mining port
    bitHopper.setup_miner(port = args.mine_port, host=args.mine_localname)
    
    #Set up the control website
    bitHopper.setup_control(port = args.config_port, host=args.config_localname)
    
    #Setup Custom Pools
    bitHopper.custom_pools()

    while True:
        gevent.sleep(100)


if __name__ == "__main__":
    import gevent_profiler
    gevent_profiler.attach()
    run()

########NEW FILE########
__FILENAME__ = run
"""
Main command line interface for bitHopper
Parses arguments and start bitHopper up
"""

import bitHopper
import gevent
import argparse
import logging

def parse_config():
    """
    Parses the low level bitHopper configuration
    """
    parser = argparse.ArgumentParser(
                    description='Process bitHopper CommandLine Arguments')
    parser.add_argument('--mine_port', metavar='mp', type=int, 
                    default=8337, help='Mining Port Number')
                   
    parser.add_argument('--config_port', metavar='cp', type=int, 
                    default=8339, help='Configuration Port Number')
                    
    parser.add_argument('--mine_localname', metavar='cp', type=str, 
                    default='', help='Mining IP address to bind to')
                    
    parser.add_argument('--config_localname', metavar='cp', type=str, 
                    default='', help='Configuration IP address to bind to')
                    
    parser.add_argument('--debug', action="store_true", default=False)
                    
    return parser.parse_args()

if __name__ == "__main__":

    args = parse_config()
    
    #Setup debugging output
    bitHopper.setup_logging(logging.DEBUG if args.debug else logging.INFO)
        
    #Setup mining port
    bitHopper.setup_miner(port = args.mine_port, host=args.mine_localname)
    
    #Set up the control website
    bitHopper.setup_control(port = args.config_port, host=args.config_localname)
    
    #Setup Custom Pools
    bitHopper.custom_pools()

    while True:
        gevent.sleep(100)


########NEW FILE########
__FILENAME__ = tests
import unittest, json, bitHopper, btcnet_info, httplib2, json

import bitHopper
import bitHopper.Logic
import bitHopper.Configuration.Workers
import bitHopper.Configuration.Pools
import bitHopper.Tracking.speed

import gevent

import bitHopper
bitHopper.setup_logging()

class FakePool():
    """Class for faking pool information from btnet"""    
    def __init__(self):
        self.payout_scheme = 'prop'
        self.coin = 'btc'
        self.shares = "123"
        
    def __getitem__(self, key):
        return getattr(self, key, None)   
        
import btcnet_info

class CustomPools(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import fake_pool
        #fake_pool.initialize()
        gevent.sleep(0)
        import bitHopper.Configuration.Workers
        bitHopper.Configuration.Workers.add('test_pool', 'test', 'test')
        import bitHopper.Configuration.Pools
        #bitHopper.Configuration.Pools.set_priority('test_pool', 1)
        gevent.sleep(0)
        bitHopper.custom_pools()
        gevent.sleep(0)
        bitHopper.Logic.ServerLogic.rebuild_servers()
        gevent.sleep(0)
        
    def testName(self):
        found = False
        for item in btcnet_info.get_pools():
            if item.name == 'test_pool':
                found = True
        
        self.assertTrue(found)
        
    def testCredentials(Self):
        import bitHopper.Configuration.Workers as Workers
        workers = Workers.get_worker_from('test_pool')
        if not workers:
            assert False
        assert True
        
    
    def testValid(self):
        def test_in_list(list_s):
            for item in list_s:
                if item.name == 'test_pool':
                    return True
            return False
    
        from bitHopper.Logic.ServerLogic import filters
        import btcnet_info
        servers = list(btcnet_info.get_pools())
        assert test_in_list(servers)
        for filter_f in bitHopper.Logic.ServerLogic.filters:
            servers = list(filter_f(servers))
            assert test_in_list(servers)
            
        
    def testAdded(self):
        import bitHopper.Logic.ServerLogic
          
class ServerLogicTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.logic = bitHopper.Logic.ServerLogic
        gevent.sleep(0)

    def testdiff_cutoff(self):
        example = FakePool()
        self.assertEqual(self.logic.difficulty_cutoff(example), 
            float(btcnet_info.get_difficulty(example.coin)) * 0.435)
            
            
    def testvalid_scheme(self):
        a = [FakePool(), FakePool(), FakePool(), FakePool()]
        a[0].payout_scheme = 'pps'
        a[1].payout_scheme = 'smpps'
        a[2].payout_scheme = 'prop'
        a[2].shares = str(10**10)
        a[3].payout_scheme = 'dgm'
        
        self.assertEqual(len(list(self.logic.valid_scheme(a))),
            3)
            
    def testfilter_hoppable(self):
        a = [FakePool(), FakePool(), FakePool(), FakePool()]
        a[0].payout_scheme = 'pps'
        a[1].payout_scheme = 'score'
        a[2].payout_scheme = 'prop'
        a[2].shares = str(10**10)
        a[3].payout_scheme = 'dgm'
        
        self.assertEqual(len(list(self.logic.filter_hoppable(a))), 2)
        
    def testfilter_secure(self):
    
        a = [FakePool(), FakePool(), FakePool(), FakePool()]
        a[0].payout_scheme = 'pps'
        a[1].payout_scheme = 'score'
        a[2].payout_scheme = 'prop'
        a[2].shares = str(10**10)
        a[3].payout_scheme = 'dgm'
        
        self.assertEqual(len(list(self.logic.filter_secure(a))), 2)
        
class UtilTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.util = bitHopper.util
        
    def valid_rpc(self, item, expect):
        #item = json.dumps(item)
        self.assertEqual(self.util.validate_rpc(item), expect)

    def testvalidate(self):
        self.valid_rpc({'hahaha':1}, False)
        self.valid_rpc({'params':[], 'method':'getwork', 'id':1}, True)
        
class MiningTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import bitHopper
        bitHopper.setup_miner()
        gevent.sleep(0)
        import fake_pool
        fake_pool.initialize()
        gevent.sleep(0)
        import bitHopper.Configuration.Workers
        bitHopper.Configuration.Workers.add('test_pool', 'test', 'test')
        import bitHopper.Configuration.Pools
        bitHopper.Configuration.Pools.set_priority('test_pool', 1)
        gevent.sleep(0)
        bitHopper.custom_pools()
        gevent.sleep(0)
        bitHopper.Logic.ServerLogic.rebuild_servers()
        gevent.sleep(0)
        
        
    def testImport(self):
        self.assertTrue(True)
        
    def testGetWorkers(self):
        self.assertTrue(bitHopper.Logic.get_server() != None)
        
    def testMining(self):
        
        http = httplib2.Http()
        headers = {'Authorization':'Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='}
        body = json.dumps({'params':[], 'id':1, 'method':'getwork'})
        headers, content = http.request('http://localhost:8337/','POST', body=body, headers=headers)
        try:
            response = json.loads(content) 
        except:
            self.assertFalse(content)
        self.assertTrue('result' in response)
        self.assertTrue('id' in response)
        self.assertTrue('error' in response)
        self.assertTrue(response['error'] == None)
        
    def testSubmit(self):
        http = httplib2.Http()
        headers = {'Authorization':'Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='}
        body = json.dumps({'params':['0000000141eb2ea2dff39b792c3c4112408b930de8fb7e3aef8a75f400000709000000001d716842411d0488da0d1ccd34e8f3e7d5f0682632efec00b80c7e3f84e175854fb7bead1a09ae0200000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'], 'id':1, 'method':'getwork'})
        headers, content = http.request('http://localhost:8337/','POST', body=body, headers=headers)
        try:
            response = json.loads(content)
            #print response 
        except:
            self.assertFalse(content)
        self.assertTrue('result' in response)
        self.assertTrue('id' in response)
        self.assertTrue('error' in response)
        self.assertTrue(response['error'] == None)
        self.assertTrue(response['result'] == True)
        
    
        
class LongPollingTestCase(unittest.TestCase):
    def testBlocking(self):
        import bitHopper.LongPoll as lp
        import gevent
        def trigger():
            lp.wait()
        gevent.spawn(trigger)
        lp.trigger('Not used right now')
        gevent.sleep(0)
        self.assertTrue(True)
         
                
class ControlTestCase(unittest.TestCase):
        
    @classmethod
    def setUpClass(self):
        import bitHopper
        bitHopper.setup_control()
        
    def testImport(self):
        self.assertTrue(True)
        
    def testStatic(self):
        import httplib2
        http = httplib2.Http()
        import os
        items = os.listdir('./bitHopper/static/')
        for item in items:
            headers, content = http.request('http://localhost:8339/static/' + item)
            self.assertTrue('Not Found' not in content)
            
    def testDynamic(self):
        import httplib2
        http = httplib2.Http()
        import os
        items = ['/worker', '/', '/miners']
        for item in items:
            headers, content = http.request('http://localhost:8339' + item)
            self.assertTrue('Not Found' not in content)
            
    def testWorkers(self):
        workers = bitHopper.Configuration.Workers
        before = workers.len_workers()
        import mechanize
        br = mechanize.Browser()
        br.open('http://localhost:8339/worker')
        br.select_form(name="add")
        br["username"] = 'test_worker'
        br["password"] = 'test'
        response = br.submit()
        #self.assertTrue(workers.len_workers() > before)
        for pool in workers.workers.keys():
            for username, password in workers.workers[pool]:
                if (username, password) == ('test_worker','test'):
                    workers.remove(pool, username, password)
                    break
        self.assertTrue(workers.len_workers() == before)
        
        #Commented out because it doesn't test correctly
        #And it deletes too many workers
        """
        br = mechanize.Browser()
        br.open('http://localhost:8339/worker')
        br.select_form(name="remove")
        response = br.submit()
        print '%s is before %s after remove ' % (before, workers.len_workers())
        
        """
        
class WorkersTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.workers = bitHopper.Configuration.Workers
        
    def testInsertandGet(self):
        
        before = len(self.workers.get_worker_from('test'))
        self.workers.add('test','test','test')
        self.assertTrue(len(self.workers.get_worker_from('test')) > 0)
        self.workers.remove('test','test','test')
        self.assertTrue(len(self.workers.get_worker_from('test')) == before)


class MinersTestCase(unittest.TestCase):

    def testnormal(self):
        import bitHopper.Configuration.Miners
        miners = bitHopper.Configuration.Miners
        miners.remove('Test', 'Test')
        a = miners.len_miners()
        miners.add('Test','Test')
        assert miners.len_miners() == a+1
        miners.remove('Test', 'Test')
        assert miners.len_miners() == a   
        
    def testWeb(self):
        miners = bitHopper.Configuration.Miners
        before = miners.len_miners()
        import mechanize
        br = mechanize.Browser()
        br.open('http://localhost:8339/miners')
        br.select_form(name="add")
        br["username"] = 'test'
        br["password"] = 'test'
        response = br.submit()
        #self.assertTrue(workers.len_workers() > before)
        miners.remove('test', 'test')
        self.assertTrue(miners.len_miners() == before)

        
class PoolsTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.pools = bitHopper.Configuration.Pools
        
    def testSetandGet(self):
        
        self.pools.set_priority('test',0)
        self.pools.set_percentage('test', 1)
        per = self.pools.get_percentage('test')
        self.assertEqual(per, 1)
        self.assertTrue(len(list(self.pools.percentage_server()))>0)
        prio = self.pools.get_priority('test')
        self.assertEqual(prio, 0)
        self.pools.set_priority('test',1)
        prio = self.pools.get_priority('test')
        self.assertEqual(prio, 1)
        self.assertTrue(self.pools.len_pools() > 0)
        self.pools.set_priority('test',0)
        self.pools.set_percentage('test', 0)
        prio = self.pools.get_priority('test')
        per = self.pools.get_percentage('test')
        self.assertTrue(prio == per == 0)
        
class TestSpeed(unittest.TestCase):

    def setUp(self):
        self.speed = bitHopper.Tracking.speed.Speed()

    def test_shares_add(self):
        self.speed.add_shares(100)
        self.speed.update_rate(loop=False)
        self.assertTrue(self.speed.get_rate() > 0)
   
    def test_shares_zero(self):
        self.speed.update_rate(loop=False)
        self.assertTrue(self.speed.get_rate() == 0)
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
