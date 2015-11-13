__FILENAME__ = config_sample
'''
This is example configuration for Stratum server.
Please rename it to config.py and fill correct values.

This is already setup with sane values for solomining.
You NEED to set the parameters in BASIC SETTINGS
'''
#********************* Config Version ***************
CONFIG_VERSION = 0.1
# ******************** BASIC SETTINGS ***************
# These are the MUST BE SET parameters!

CENTRAL_WALLET = 'set_valid_addresss_in_config!'                # Local coin address where money goes

COINDAEMON_TRUSTED_HOST = 'localhost'
COINDAEMON_TRUSTED_PORT = 8332
COINDAEMON_TRUSTED_USER = 'user'
COINDAEMON_TRUSTED_PASSWORD = 'somepassword'

COINDAEMON_ALGO = 'scrypt'    # The available options are:  scrypt, sha256d, scrypt-jane, skeinhash, and quark
SCRYPTJANE_NAME = 'vtc_scrypt'# Set this to the Scrypt jane module name e.g. yac_scrypt or vtc_scrypt
COINDAEMON_TX = False         # For Coins which support TX Messages please enter yes in the TX selection

# ******************** BASIC SETTINGS ***************
# Backup Coin Daemon address's (consider having at least 1 backup)
# You can have up to 99

#COINDAEMON_TRUSTED_HOST_1 = 'localhost'
#COINDAEMON_TRUSTED_PORT_1 = 8332
#COINDAEMON_TRUSTED_USER_1 = 'user'
#COINDAEMON_TRUSTED_PASSWORD_1 = 'somepassword'

#COINDAEMON_TRUSTED_HOST_2 = 'localhost'
#COINDAEMON_TRUSTED_PORT_2 = 8332
#COINDAEMON_TRUSTED_USER_2 = 'user'
#COINDAEMON_TRUSTED_PASSWORD_2 = 'somepassword'

# ******************** GENERAL SETTINGS ***************
# Set process name of twistd, much more comfortable if you run multiple processes on one machine
STRATUM_MINING_PROCESS_NAME= 'twistd-stratum-mining'


# Enable some verbose debug (logging requests and responses).
DEBUG = False

# Destination for application logs, files rotated once per day.
LOGDIR = 'log/'

# Main application log file.
LOGFILE = None      # eg. 'stratum.log'
LOGLEVEL = 'DEBUG'
# Logging Rotation can be enabled with the following settings
# It if not enabled here, you can set up logrotate to rotate the files. 
# For built in log rotation set LOG_ROTATION = True and configure the variables
LOG_ROTATION = True
LOG_SIZE = 10485760 # Rotate every 10M
LOG_RETENTION = 10 # Keep 10 Logs

# How many threads use for synchronous methods (services).
# 30 is enough for small installation, for real usage
# it should be slightly more, say 100-300.
THREAD_POOL_SIZE = 300

# ******************** TRANSPORTS *********************
# Hostname or external IP to expose
HOSTNAME = 'localhost'

# Disable the example service
ENABLE_EXAMPLE_SERVICE = False

# Port used for Socket transport. Use 'None' for disabling the transport.
LISTEN_SOCKET_TRANSPORT = 3333
# Port used for HTTP Poll transport. Use 'None' for disabling the transport
LISTEN_HTTP_TRANSPORT = None
# Port used for HTTPS Poll transport
LISTEN_HTTPS_TRANSPORT = None
# Port used for WebSocket transport, 'None' for disabling WS
LISTEN_WS_TRANSPORT = None
# Port used for secure WebSocket, 'None' for disabling WSS
LISTEN_WSS_TRANSPORT = None

# Salt used for Block Notify Password
PASSWORD_SALT = 'some_crazy_string'

# ******************** Database  *********************
DATABASE_DRIVER = 'mysql'       # Options: none, sqlite, postgresql or mysql
DATABASE_EXTEND = False         # SQLite and PGSQL Only!

# SQLite
DB_SQLITE_FILE = 'pooldb.sqlite'
# Postgresql
DB_PGSQL_HOST = 'localhost'
DB_PGSQL_DBNAME = 'pooldb'
DB_PGSQL_USER = 'pooldb'
DB_PGSQL_PASS = '**empty**'
DB_PGSQL_SCHEMA = 'public'
# MySQL
DB_MYSQL_HOST = 'localhost'
DB_MYSQL_DBNAME = 'pooldb'
DB_MYSQL_USER = 'pooldb'
DB_MYSQL_PASS = '**empty**'
DB_MYSQL_PORT = 3306            # Default port for MySQL

# ******************** Adv. DB Settings *********************
#  Don't change these unless you know what you are doing

DB_LOADER_CHECKTIME = 15        # How often we check to see if we should run the loader
DB_LOADER_REC_MIN = 10          # Min Records before the bulk loader fires
DB_LOADER_REC_MAX = 50          # Max Records the bulk loader will commit at a time
DB_LOADER_FORCE_TIME = 300      # How often the cache should be flushed into the DB regardless of size.
DB_STATS_AVG_TIME = 300         # When using the DATABASE_EXTEND option, average speed over X sec
                                # Note: this is also how often it updates
DB_USERCACHE_TIME = 600         # How long the usercache is good for before we refresh

# ******************** Pool Settings *********************

# User Auth Options
USERS_AUTOADD = False           # Automatically add users to database when they connect.
                                # This basically disables User Auth for the pool.
USERS_CHECK_PASSWORD = False    # Check the workers password? (Many pools don't)

# Transaction Settings
COINBASE_EXTRAS = '/stratumPool/'           # Extra Descriptive String to incorporate in solved blocks
ALLOW_NONLOCAL_WALLET = False               # Allow valid, but NON-Local wallet's

# Coin Daemon communication polling settings (In Seconds)
PREVHASH_REFRESH_INTERVAL = 5   # How often to check for new Blocks
                                #   If using the blocknotify script (recommended) set = to MERKLE_REFRESH_INTERVAL
                                #   (No reason to poll if we're getting pushed notifications)
MERKLE_REFRESH_INTERVAL = 60    # How often check memorypool
                                #   How often to check for new transactions to be added to the block
                                #   This effectively resets the template and incorporates new transactions.
                                #   This should be "slow"

INSTANCE_ID = 31                # Used for extranonce and needs to be 0-31

# ******************** Pool Difficulty Settings *********************
VDIFF_X2_TYPE = True            # Powers of 2 e.g. 2,4,8,16,32,64,128,256,512,1024
VDIFF_FLOAT = False             # Use float difficulty

# Pool Target (Base Difficulty)
POOL_TARGET = 32                # Pool-wide difficulty target int >= 1

# Variable Difficulty Enable
VARIABLE_DIFF = True            # Master variable difficulty enable

# Variable diff tuning variables
#VARDIFF will start at the POOL_TARGET. It can go as low as the VDIFF_MIN and as high as min(VDIFF_MAX or coindaemons difficulty)
USE_COINDAEMON_DIFF = False     # Set the maximum difficulty to the coindaemon difficulty. 
DIFF_UPDATE_FREQUENCY = 86400   # How often to check coindaemon difficulty. Should be less than coin difficulty retarget time
VDIFF_MIN_TARGET = 16           # Minimum target difficulty 
VDIFF_MAX_TARGET = 1024         # Maximum target difficulty 
VDIFF_MIN_CHANGE = 1            # Minimum change of worker's difficulty if VDIFF_X2_TYPE=False and the final difficulty will be within the boundaries (VDIFF_MIN_TARGET, VDIFF_MAX_TARGET)
VDIFF_TARGET_TIME = 15          # Target time per share (i.e. try to get 1 share per this many seconds)
VDIFF_RETARGET_TIME = 120       # How often the miners difficulty changes if appropriate
VDIFF_VARIANCE_PERCENT = 30     # Allow average time to very this % from target without retarget

# Allow external setting of worker difficulty, checks pool_worker table datarow[6] position for target difficulty
# if present or else defaults to pool target, over rides all other difficulty settings, no checks are made
# for min or max limits this should be done by your front end software
ALLOW_EXTERNAL_DIFFICULTY = False 

#### Advanced Option ##### 
# For backwards compatibility, we send the scrypt hash to the solutions column in the shares table 
# For block confirmation, we have an option to send the block hash in 
# Please make sure your front end is compatible with the block hash in the solutions table. 
# For People using the MPOS frontend enabling this is recommended. It allows the frontend to compare the block hash to the coin daemon reducing the likelihood of missing share error's for blocks
SOLUTION_BLOCK_HASH = True      # If enabled, enter the block hash. If false enter the scrypt/sha hash into the shares table 

#Pass scrypt hash to submit block check.
#Use if submit block is returning errors and marking submitted blocks invalid upstream, but the submitted blocks are being a accepted by the coin daemon into the block chain.
BLOCK_CHECK_SCRYPT_HASH = False

# ******************** Worker Ban Options *********************
ENABLE_WORKER_BANNING = True    # Enable/disable temporary worker banning 
WORKER_CACHE_TIME = 600         # How long the worker stats cache is good before we check and refresh
WORKER_BAN_TIME = 300           # How long we temporarily ban worker
INVALID_SHARES_PERCENT = 50     # Allow average invalid shares vary this % before we ban

# ******************** E-Mail Notification Settings *********************
NOTIFY_EMAIL_TO = ''                                            # Where to send Start/Found block notifications
NOTIFY_EMAIL_TO_DEADMINER = ''                                  # Where to send dead miner notifications
NOTIFY_EMAIL_FROM = 'root@localhost'                            # Sender address
NOTIFY_EMAIL_SERVER = 'localhost'                               # E-Mail sender
NOTIFY_EMAIL_USERNAME = ''                                      # E-Mail server SMTP logon
NOTIFY_EMAIL_PASSWORD = ''
NOTIFY_EMAIL_USETLS = True

# ******************** Memcache Settings *********************
# Memcahce is a requirement. Enter the settings below
MEMCACHE_HOST = "localhost"     # Hostname or IP that runs memcached
MEMCACHE_PORT = 11211           # Port
MEMCACHE_TIMEOUT = 900          # Key timeout
MEMCACHE_PREFIX = "stratum_"    # Prefix for keys

########NEW FILE########
__FILENAME__ = bitcoin_rpc
'''
    Implements simple interface to a coin daemon's RPC.
'''

import simplejson as json
import base64
from twisted.internet import defer
from twisted.web import client
import time

import lib.logger
log = lib.logger.get_logger('bitcoin_rpc')

class BitcoinRPC(object):
    
    def __init__(self, host, port, username, password):
        log.debug("Got to Bitcoin RPC")
        self.bitcoin_url = 'http://%s:%d' % (host, port)
        self.credentials = base64.b64encode("%s:%s" % (username, password))
        self.headers = {
            'Content-Type': 'text/json',
            'Authorization': 'Basic %s' % self.credentials,
        }
        client.HTTPClientFactory.noisy = False
	self.has_submitblock = False        

    def _call_raw(self, data):
        client.Headers
        return client.getPage(
            url=self.bitcoin_url,
            method='POST',
            headers=self.headers,
            postdata=data,
        )
           
    def _call(self, method, params):
        return self._call_raw(json.dumps({
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': '1',
            }))
    
    @defer.inlineCallbacks
    def check_submitblock(self):
        try:
            log.info("Checking for submitblock")
            resp = (yield self._call('submitblock', []))
	    self.has_submitblock = True
        except Exception as e:
            if (str(e) == "404 Not Found"):
                log.debug("No submitblock detected.")
		self.has_submitblock = False
            elif (str(e) == "500 Internal Server Error"):
                log.debug("submitblock detected.")
		self.has_submitblock = True
            else:
                log.debug("unknown submitblock check result.")
		self.has_submitblock = True
        finally:
              defer.returnValue(self.has_submitblock)

    
    @defer.inlineCallbacks
    def submitblock(self, block_hex, hash_hex, scrypt_hex):
  #try 5 times? 500 Internal Server Error could mean random error or that TX messages setting is wrong
        attempts = 0
        while True:
            attempts += 1
            if self.has_submitblock == True:
                try:
                    log.debug("Submitting Block with submitblock: attempt #"+str(attempts))
                    log.debug([block_hex,])
                    resp = (yield self._call('submitblock', [block_hex,]))
                    log.debug("SUBMITBLOCK RESULT: %s", resp)
                    break
                except Exception as e:
                    if attempts > 4:
                        log.exception("submitblock failed. Problem Submitting block %s" % str(e))
                        log.exception("Try Enabling TX Messages in config.py!")
                        raise
                    else:
                        continue
            elif self.has_submitblock == False:
                try:
                    log.debug("Submitting Block with getblocktemplate submit: attempt #"+str(attempts))
                    log.debug([block_hex,])
                    resp = (yield self._call('getblocktemplate', [{'mode': 'submit', 'data': block_hex}]))
                    break
                except Exception as e:
                    if attempts > 4:
                        log.exception("getblocktemplate submit failed. Problem Submitting block %s" % str(e))
                        log.exception("Try Enabling TX Messages in config.py!")
                        raise
                    else:
                        continue
            else:  # self.has_submitblock = None; unable to detect submitblock, try both
                try:
                    log.debug("Submitting Block with submitblock")
                    log.debug([block_hex,])
                    resp = (yield self._call('submitblock', [block_hex,]))
                    break
                except Exception as e:
                    try:
                        log.exception("submitblock Failed, does the coind have submitblock?")
                        log.exception("Trying GetBlockTemplate")
                        resp = (yield self._call('getblocktemplate', [{'mode': 'submit', 'data': block_hex}]))
                        break
                    except Exception as e:
                        if attempts > 4:
                            log.exception("submitblock failed. Problem Submitting block %s" % str(e))
                            log.exception("Try Enabling TX Messages in config.py!")
                            raise
                        else:
                            continue

        if json.loads(resp)['result'] == None:
            # make sure the block was created.
            log.info("CHECKING FOR BLOCK AFTER SUBMITBLOCK")
            defer.returnValue((yield self.blockexists(hash_hex, scrypt_hex)))
        else:
            defer.returnValue(False)

    @defer.inlineCallbacks
    def getinfo(self):
         resp = (yield self._call('getinfo', []))
         defer.returnValue(json.loads(resp)['result'])
    
    @defer.inlineCallbacks
    def getblocktemplate(self):
        try:
            resp = (yield self._call('getblocktemplate', [{}]))
            defer.returnValue(json.loads(resp)['result'])
        # if internal server error try getblocktemplate without empty {} # ppcoin
        except Exception as e:
            if (str(e) == "500 Internal Server Error"):
                resp = (yield self._call('getblocktemplate', []))
                defer.returnValue(json.loads(resp)['result'])
            else:
                raise
                                                  
    @defer.inlineCallbacks
    def prevhash(self):
        resp = (yield self._call('getwork', []))
        try:
            defer.returnValue(json.loads(resp)['result']['data'][8:72])
        except Exception as e:
            log.exception("Cannot decode prevhash %s" % str(e))
            raise
        
    @defer.inlineCallbacks
    def validateaddress(self, address):
        resp = (yield self._call('validateaddress', [address,]))
        defer.returnValue(json.loads(resp)['result'])

    @defer.inlineCallbacks
    def getdifficulty(self):
        resp = (yield self._call('getdifficulty', []))
        defer.returnValue(json.loads(resp)['result'])

    @defer.inlineCallbacks
    def blockexists(self, hash_hex, scrypt_hex):
        valid_hash = None
        blockheight = None
        # try both hash_hex and scrypt_hex to find block
        try:
            resp = (yield self._call('getblock', [hash_hex,]))
            result = json.loads(resp)['result']
            if "hash" in result and result['hash'] == hash_hex:
                log.debug("Block found: %s" % hash_hex)
                valid_hash = hash_hex
                if "height" in result:
                    blockheight = result['height']
                else:
                    defer.returnValue(True)
            else:
                log.info("Cannot find block for %s" % hash_hex)
                defer.returnValue(False)

        except Exception as e:
            try:
                resp = (yield self._call('getblock', [scrypt_hex,]))
                result = json.loads(resp)['result']
                if "hash" in result and result['hash'] == scrypt_hex:
                    valid_hash = scrypt_hex
                    log.debug("Block found: %s" % scrypt_hex)
                    if "height" in result:
                        blockheight = result['height']
                    else:
                        defer.returnValue(True)
                else:
                    log.info("Cannot find block for %s" % scrypt_hex)
                    defer.returnValue(False)

            except Exception as e:
                log.info("Cannot find block for hash_hex %s or scrypt_hex %s" % hash_hex, scrypt_hex)
                defer.returnValue(False)

        #after we've found the block, check the block with that height in the blockchain to see if hashes match
        try:
            log.debug("checking block hash against hash of block height: %s", blockheight)
            resp = (yield self._call('getblockhash', [blockheight,]))
            hash = json.loads(resp)['result']
            log.debug("hash of block of height %s: %s", blockheight, hash)
            if hash == valid_hash:
                log.debug("Block confirmed: hash of block matches hash of blockheight")
                defer.returnValue(True)
            else:
                log.debug("Block invisible: hash of block does not match hash of blockheight")
                defer.returnValue(False)

        except Exception as e:
            # cannot get blockhash from height; block was created, so return true
            defer.returnValue(True)
        else:
            log.info("Cannot find block for %s" % hash_hex)
            defer.returnValue(False)

########NEW FILE########
__FILENAME__ = bitcoin_rpc_manager
'''
    Implements simple interface to a coin daemon's RPC.
'''


import simplejson as json
from twisted.internet import defer

import settings

import time

import lib.logger
log = lib.logger.get_logger('bitcoin_rpc_manager')

from lib.bitcoin_rpc import BitcoinRPC


class BitcoinRPCManager(object):
    
    def __init__(self):
        log.debug("Got to Bitcoin RPC Manager")
        self.conns = {}
        self.conns[0] = BitcoinRPC(settings.COINDAEMON_TRUSTED_HOST,
                                 settings.COINDAEMON_TRUSTED_PORT,
                                 settings.COINDAEMON_TRUSTED_USER,
                                 settings.COINDAEMON_TRUSTED_PASSWORD)
        self.curr_conn = 0
        for x in range (1, 99):
            if hasattr(settings, 'COINDAEMON_TRUSTED_HOST_' + str(x)) and hasattr(settings, 'COINDAEMON_TRUSTED_PORT_' + str(x)) and hasattr(settings, 'COINDAEMON_TRUSTED_USER_' + str(x)) and hasattr(settings, 'COINDAEMON_TRUSTED_PASSWORD_' + str(x)):
                self.conns[len(self.conns)] = BitcoinRPC(settings.__dict__['COINDAEMON_TRUSTED_HOST_' + str(x)],
                                settings.__dict__['COINDAEMON_TRUSTED_PORT_' + str(x)],
                                settings.__dict__['COINDAEMON_TRUSTED_USER_' + str(x)],
                                settings.__dict__['COINDAEMON_TRUSTED_PASSWORD_' + str(x)])

    def add_connection(self, host, port, user, password):
        # TODO: Some string sanity checks
        self.conns[len(self.conns)] = BitcoinRPC(host, port, user, password)

    def next_connection(self):
        time.sleep(1)
        if len(self.conns) <= 1:
            log.error("Problem with Pool 0 -- NO ALTERNATE POOLS!!!")
            time.sleep(4)
	    self.curr_conn = 0
            return
        log.error("Problem with Pool %i Switching to Next!" % (self.curr_conn) )
        self.curr_conn = self.curr_conn + 1
        if self.curr_conn >= len(self.conns):
            self.curr_conn = 0

    @defer.inlineCallbacks
    def check_height(self):
        while True:
            try:
                resp = (yield self.conns[self.curr_conn]._call('getinfo', []))
                break
            except:
                log.error("Check Height -- Pool %i Down!" % (self.curr_conn) )
                self.next_connection()
        curr_height = json.loads(resp)['result']['blocks']
        log.debug("Check Height -- Current Pool %i : %i" % (self.curr_conn,curr_height) )
        for i in self.conns:
            if i == self.curr_conn:
                continue

            try:
                resp = (yield self.conns[i]._call('getinfo', []))
            except:
                log.error("Check Height -- Pool %i Down!" % (i,) )
                continue

            height = json.loads(resp)['result']['blocks']
            log.debug("Check Height -- Pool %i : %i" % (i,height) )
            if height > curr_height:
                self.curr_conn = i

        defer.returnValue(True)

    def _call_raw(self, data):
        while True:
            try:
                return self.conns[self.curr_conn]._call_raw(data)
            except:
                self.next_connection()

    def _call(self, method, params):
        while True:
            try:
                return self.conns[self.curr_conn]._call(method,params)
            except:
                self.next_connection()
    def check_submitblock(self):
        while True:
              try:
                  return self.conns[self.curr_conn].check_submitblock()
              except:
                  self.next_connection()

    def submitblock(self, block_hex, hash_hex, scrypt_hex):
        while True:
            try:
               return self.conns[self.curr_conn].submitblock(block_hex, hash_hex, scrypt_hex)
            except:
                self.next_connection()

    def getinfo(self):
        while True:
            try:
                return self.conns[self.curr_conn].getinfo()
            except:
                self.next_connection()
    
    def getblocktemplate(self):
        while True:
            try:
               return self.conns[self.curr_conn].getblocktemplate()
            except:
                self.next_connection()

    def prevhash(self):
        self.check_height()
        while True:
            try:
                return self.conns[self.curr_conn].prevhash()
            except:
                self.next_connection()
        
    def validateaddress(self, address):
        while True:
            try:
                return self.conns[self.curr_conn].validateaddress(address)
            except:
                self.next_connection()

    def getdifficulty(self):
        while True:
            try:
                return self.conns[self.curr_conn].getdifficulty()
            except:
                self.next_connection()

########NEW FILE########
__FILENAME__ = block_template
import StringIO
import binascii
import struct

import util
import merkletree
import halfnode
from coinbasetx import CoinbaseTransactionPOW
from coinbasetx import CoinbaseTransactionPOS
from coinbasetx import CoinbaseTransaction
import lib.logger
log = lib.logger.get_logger('block_template')

import lib.logger
log = lib.logger.get_logger('block_template')


# Remove dependency to settings, coinbase extras should be
# provided from coinbaser
import settings

class BlockTemplate(halfnode.CBlock):
    '''Template is used for generating new jobs for clients.
    Let's iterate extranonce1, extranonce2, ntime and nonce
    to find out valid coin block!'''
    
    coinbase_transaction_class = CoinbaseTransaction
    
    def __init__(self, timestamper, coinbaser, job_id):
        log.debug("Got To  Block_template.py")
        log.debug("Got To Block_template.py")
        super(BlockTemplate, self).__init__()
        
        self.job_id = job_id 
        self.timestamper = timestamper
        self.coinbaser = coinbaser
        
        self.prevhash_bin = '' # reversed binary form of prevhash
        self.prevhash_hex = ''
        self.timedelta = 0
        self.curtime = 0
        self.target = 0
        #self.coinbase_hex = None 
        self.merkletree = None
                
        self.broadcast_args = []
        
        # List of 4-tuples (extranonce1, extranonce2, ntime, nonce)
        # registers already submitted and checked shares
        # There may be registered also invalid shares inside!
        self.submits = [] 
                
    def fill_from_rpc(self, data):
        '''Convert getblocktemplate result into BlockTemplate instance'''
        
        #txhashes = [None] + [ binascii.unhexlify(t['hash']) for t in data['transactions'] ]
        txhashes = [None] + [ util.ser_uint256(int(t['hash'], 16)) for t in data['transactions'] ]
        mt = merkletree.MerkleTree(txhashes)
        if settings.COINDAEMON_Reward == 'POW':
            coinbase = CoinbaseTransactionPOW(self.timestamper, self.coinbaser, data['coinbasevalue'],
                                              data['coinbaseaux']['flags'], data['height'],
                                              settings.COINBASE_EXTRAS)
        else:
            coinbase = CoinbaseTransactionPOS(self.timestamper, self.coinbaser, data['coinbasevalue'],
                                              data['coinbaseaux']['flags'], data['height'],
                                              settings.COINBASE_EXTRAS, data['curtime'])

        self.height = data['height']
        self.nVersion = data['version']
        self.hashPrevBlock = int(data['previousblockhash'], 16)
        self.nBits = int(data['bits'], 16)
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nNonce = 0
        self.vtx = [ coinbase, ]
        
        for tx in data['transactions']:
            t = halfnode.CTransaction()
            t.deserialize(StringIO.StringIO(binascii.unhexlify(tx['data'])))
            self.vtx.append(t)
            
        self.curtime = data['curtime']
        self.timedelta = self.curtime - int(self.timestamper.time()) 
        self.merkletree = mt
        self.target = util.uint256_from_compact(self.nBits)
        
        # Reversed prevhash
        self.prevhash_bin = binascii.unhexlify(util.reverse_hash(data['previousblockhash']))
        self.prevhash_hex = "%064x" % self.hashPrevBlock
        
        self.broadcast_args = self.build_broadcast_args()
                
    def register_submit(self, extranonce1, extranonce2, ntime, nonce):
        '''Client submitted some solution. Let's register it to
        prevent double submissions.'''
        
        t = (extranonce1, extranonce2, ntime, nonce)
        if t not in self.submits:
            self.submits.append(t)
            return True
        return False
            
    def build_broadcast_args(self):
        '''Build parameters of mining.notify call. All clients
        may receive the same params, because they include
        their unique extranonce1 into the coinbase, so every
        coinbase_hash (and then merkle_root) will be unique as well.'''
        job_id = self.job_id
        prevhash = binascii.hexlify(self.prevhash_bin)
        (coinb1, coinb2) = [ binascii.hexlify(x) for x in self.vtx[0]._serialized ]
        merkle_branch = [ binascii.hexlify(x) for x in self.merkletree._steps ]
        version = binascii.hexlify(struct.pack(">i", self.nVersion))
        nbits = binascii.hexlify(struct.pack(">I", self.nBits))
        ntime = binascii.hexlify(struct.pack(">I", self.curtime))
        clean_jobs = True
        
        return (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)

    def serialize_coinbase(self, extranonce1, extranonce2):
        '''Serialize coinbase with given extranonce1 and extranonce2
        in binary form'''
        (part1, part2) = self.vtx[0]._serialized
        return part1 + extranonce1 + extranonce2 + part2
    
    def check_ntime(self, ntime):
        '''Check for ntime restrictions.'''
        if ntime < self.curtime:
            return False
        
        if ntime > (self.timestamper.time() + 7200):
            # Be strict on ntime into the near future
            # may be unnecessary
            return False
        
        return True

    def serialize_header(self, merkle_root_int, ntime_bin, nonce_bin):
        '''Serialize header for calculating block hash'''
        r  = struct.pack(">i", self.nVersion)
        r += self.prevhash_bin
        r += util.ser_uint256_be(merkle_root_int)
        r += ntime_bin
        r += struct.pack(">I", self.nBits)
        r += nonce_bin    
        return r       

    def finalize(self, merkle_root_int, extranonce1_bin, extranonce2_bin, ntime, nonce):
        '''Take all parameters required to compile block candidate.
        self.is_valid() should return True then...'''
        
        self.hashMerkleRoot = merkle_root_int
        self.nTime = ntime
        self.nNonce = nonce
        self.vtx[0].set_extranonce(extranonce1_bin + extranonce2_bin)        
        self.sha256 = None # We changed block parameters, let's reset sha256 cache

########NEW FILE########
__FILENAME__ = block_updater
from twisted.internet import reactor, defer
import settings

import util
from mining.interfaces import Interfaces

import lib.logger
log = lib.logger.get_logger('block_updater')

class BlockUpdater(object):
    '''
        Polls upstream's getinfo() and detecting new block on the network.
        This will call registry.update_block when new prevhash appear.
        
        This is just failback alternative when something
        with ./litecoind -blocknotify will go wrong. 
    '''
    
    def __init__(self, registry, bitcoin_rpc):
        log.debug("Got To Block Updater")
        self.bitcoin_rpc = bitcoin_rpc
        self.registry = registry
        self.clock = None
        self.schedule()
                        
    def schedule(self):
        when = self._get_next_time()
        log.debug("Next prevhash update in %.03f sec" % when)
        log.debug("Merkle update in next %.03f sec" % \
                  ((self.registry.last_update + settings.MERKLE_REFRESH_INTERVAL)-Interfaces.timestamper.time()))
        self.clock = reactor.callLater(when, self.run)
        
    def _get_next_time(self):
        when = settings.PREVHASH_REFRESH_INTERVAL - (Interfaces.timestamper.time() - self.registry.last_update) % \
               settings.PREVHASH_REFRESH_INTERVAL
        return when  
                     
    @defer.inlineCallbacks
    def run(self):
        update = False
       
        try:             
            if self.registry.last_block:
                current_prevhash = "%064x" % self.registry.last_block.hashPrevBlock
            else:
                current_prevhash = None
                
            log.info("Checking for new block.")
            prevhash = util.reverse_hash((yield self.bitcoin_rpc.prevhash()))
            if prevhash and prevhash != current_prevhash:
                log.info("New block! Prevhash: %s" % prevhash)
                update = True
            
            elif Interfaces.timestamper.time() - self.registry.last_update >= settings.MERKLE_REFRESH_INTERVAL:
                log.info("Merkle update! Prevhash: %s" % prevhash)
                update = True
                
            if update:
                self.registry.update_block()

        except Exception:
            log.exception("UpdateWatchdog.run failed")
        finally:
            self.schedule()

    

########NEW FILE########
__FILENAME__ = coinbaser
import util
from twisted.internet import defer

import settings

import lib.logger
log = lib.logger.get_logger('coinbaser')

# TODO: Add on_* hooks in the app
    
class SimpleCoinbaser(object):
    '''This very simple coinbaser uses constant bitcoin address
    for all generated blocks.'''
    
    def __init__(self, bitcoin_rpc, address):
        log.debug("Got to coinbaser")
        # Fire Callback when the coinbaser is ready
        self.on_load = defer.Deferred()

        self.address = address
        self.is_valid = False

        self.bitcoin_rpc = bitcoin_rpc
        self._validate()

    def _validate(self):
        d = self.bitcoin_rpc.validateaddress(self.address)
        d.addCallback(self.address_check)
        d.addErrback(self._failure)

    def address_check(self, result):
        if result['isvalid'] and result['ismine']:
            self.is_valid = True
            log.info("Coinbase address '%s' is valid" % self.address)
            if 'address' in result:
               log.debug("Address = %s " % result['address'])
               self.address = result['address']
            if 'pubkey' in result:
               log.debug("PubKey = %s " % result['pubkey'])
               self.pubkey = result['pubkey']
            if 'iscompressed' in result:
               log.debug("Is Compressed = %s " % result['iscompressed'])
            if 'account' in result:
               log.debug("Account = %s " % result['account'])
            if not self.on_load.called:
               self.address = result['address']
               self.on_load.callback(True)

        elif result['isvalid'] and settings.ALLOW_NONLOCAL_WALLET == True :
             self.is_valid = True
             log.warning("!!! Coinbase address '%s' is valid BUT it is not local" % self.address)
             if 'pubkey' in result:
               log.debug("PubKey = %s " % result['pubkey'])
               self.pubkey = result['pubkey']
             if 'account' in result:
               log.debug("Account = %s " % result['account'])
             if not self.on_load.called:
                    self.on_load.callback(True)

        else:
            self.is_valid = False
            log.error("Coinbase address '%s' is NOT valid!" % self.address)
        
        #def on_new_block(self):
    #    pass
    
    #def on_new_template(self):
    #    pass
    def _failure(self, failure):
           log.exception("Cannot validate Wallet address '%s'" % self.address)
           raise
    
    def get_script_pubkey(self):
        if settings.COINDAEMON_Reward == 'POW':
            self._validate()
            return util.script_to_address(self.address)
        else:
            return util.script_to_pubkey(self.pubkey)
                   
    def get_coinbase_data(self):
        return ''

########NEW FILE########
__FILENAME__ = coinbasetx
import binascii
import halfnode
import struct
import util
import settings
import lib.logger
log = lib.logger.get_logger('coinbasetx')

#if settings.COINDAEMON_Reward == 'POW':
class CoinbaseTransactionPOW(halfnode.CTransaction):
    '''Construct special transaction used for coinbase tx.
    It also implements quick serialization using pre-cached
    scriptSig template.'''
    
    extranonce_type = '>Q'
    extranonce_placeholder = struct.pack(extranonce_type, int('f000000ff111111f', 16))
    extranonce_size = struct.calcsize(extranonce_type)

    def __init__(self, timestamper, coinbaser, value, flags, height, data):
        super(CoinbaseTransactionPOW, self).__init__()
        log.debug("Got to CoinBaseTX")
        #self.extranonce = 0
        
        if len(self.extranonce_placeholder) != self.extranonce_size:
            raise Exception("Extranonce placeholder don't match expected length!")

        tx_in = halfnode.CTxIn()
        tx_in.prevout.hash = 0L
        tx_in.prevout.n = 2**32-1
        tx_in._scriptSig_template = (
            util.ser_number(height) + binascii.unhexlify(flags) + util.ser_number(int(timestamper.time())) + \
            chr(self.extranonce_size),
            util.ser_string(coinbaser.get_coinbase_data() + data)
        )
                
        tx_in.scriptSig = tx_in._scriptSig_template[0] + self.extranonce_placeholder + tx_in._scriptSig_template[1]
    
        tx_out = halfnode.CTxOut()
        tx_out.nValue = value
        tx_out.scriptPubKey = coinbaser.get_script_pubkey()

        if settings.COINDAEMON_TX != False:
            self.strTxComment = "http://github.com/ahmedbodi/stratum-mining"
        self.vin.append(tx_in)
        self.vout.append(tx_out)
        
        # Two parts of serialized coinbase, just put part1 + extranonce + part2 to have final serialized tx
        self._serialized = super(CoinbaseTransactionPOW, self).serialize().split(self.extranonce_placeholder)

    def set_extranonce(self, extranonce):
        if len(extranonce) != self.extranonce_size:
            raise Exception("Incorrect extranonce size")
        
        (part1, part2) = self.vin[0]._scriptSig_template
        self.vin[0].scriptSig = part1 + extranonce + part2
#elif settings.COINDAEMON_Reward == 'POS':
class CoinbaseTransactionPOS(halfnode.CTransaction):
    '''Construct special transaction used for coinbase tx.
    It also implements quick serialization using pre-cached
    scriptSig template.'''
    
    extranonce_type = '>Q'
    extranonce_placeholder = struct.pack(extranonce_type, int('f000000ff111111f', 16))
    extranonce_size = struct.calcsize(extranonce_type)

    def __init__(self, timestamper, coinbaser, value, flags, height, data, ntime):
        super(CoinbaseTransactionPOS, self).__init__()
        log.debug("Got to CoinBaseTX")
        #self.extranonce = 0
        
        if len(self.extranonce_placeholder) != self.extranonce_size:
            raise Exception("Extranonce placeholder don't match expected length!")

        tx_in = halfnode.CTxIn()
        tx_in.prevout.hash = 0L
        tx_in.prevout.n = 2**32-1
        tx_in._scriptSig_template = (
            util.ser_number(height) + binascii.unhexlify(flags) + util.ser_number(int(timestamper.time())) + \
            chr(self.extranonce_size),
            util.ser_string(coinbaser.get_coinbase_data() + data)
        )
                
        tx_in.scriptSig = tx_in._scriptSig_template[0] + self.extranonce_placeholder + tx_in._scriptSig_template[1]
    
        tx_out = halfnode.CTxOut()
        tx_out.nValue = value
        tx_out.scriptPubKey = coinbaser.get_script_pubkey()
       
        self.nTime = ntime 
        if settings.COINDAEMON_SHA256_TX != False:
            self.strTxComment = "http://github.com/ahmedbodi/stratum-mining"
        self.vin.append(tx_in)
        self.vout.append(tx_out)
        
        # Two parts of serialized coinbase, just put part1 + extranonce + part2 to have final serialized tx
        self._serialized = super(CoinbaseTransactionPOS, self).serialize().split(self.extranonce_placeholder)

    def set_extranonce(self, extranonce):
        if len(extranonce) != self.extranonce_size:
            raise Exception("Incorrect extranonce size")
        
        (part1, part2) = self.vin[0]._scriptSig_template
        self.vin[0].scriptSig = part1 + extranonce + part2
#else:
class CoinbaseTransaction(halfnode.CTransaction):
    '''Construct special transaction used for coinbase tx.
    It also implements quick serialization using pre-cached
    scriptSig template.'''
    
    extranonce_type = '>Q'
    extranonce_placeholder = struct.pack(extranonce_type, int('f000000ff111111f', 16))
    extranonce_size = struct.calcsize(extranonce_type)

    def __init__(self, timestamper, coinbaser, value, flags, height, data, ntime):
        super(CoinbaseTransaction, self).__init__()
        log.debug("Got to CoinBaseTX")
        #self.extranonce = 0
        
        if len(self.extranonce_placeholder) != self.extranonce_size:
            raise Exception("Extranonce placeholder don't match expected length!")

        tx_in = halfnode.CTxIn()
        tx_in.prevout.hash = 0L
        tx_in.prevout.n = 2**32-1
        tx_in._scriptSig_template = (
            util.ser_number(height) + binascii.unhexlify(flags) + util.ser_number(int(timestamper.time())) + \
            chr(self.extranonce_size),
            util.ser_string(coinbaser.get_coinbase_data() + data)
        )
                
        tx_in.scriptSig = tx_in._scriptSig_template[0] + self.extranonce_placeholder + tx_in._scriptSig_template[1]
    
        tx_out = halfnode.CTxOut()
        tx_out.nValue = value
        tx_out.scriptPubKey = coinbaser.get_script_pubkey()
       
        self.nTime = ntime 
        self.vin.append(tx_in)
        self.vout.append(tx_out)
        
        # Two parts of serialized coinbase, just put part1 + extranonce + part2 to have final serialized tx
        self._serialized = super(CoinbaseTransaction, self).serialize().split(self.extranonce_placeholder)

    def set_extranonce(self, extranonce):
        if len(extranonce) != self.extranonce_size:
            raise Exception("Incorrect extranonce size")
        
        (part1, part2) = self.vin[0]._scriptSig_template
        self.vin[0].scriptSig = part1 + extranonce + part2

########NEW FILE########
__FILENAME__ = config_default
'''
This is example configuration for Stratum server.
Please rename it to config.py and fill correct values.
'''

# ******************** GENERAL SETTINGS ***************

# Enable some verbose debug (logging requests and responses).
DEBUG = False

# Destination for application logs, files rotated once per day.
LOGDIR = 'log/'

# Main application log file.
LOGFILE = 'stratum.log' #'stratum.log'

# Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGLEVEL = 'DEBUG'

# Logging Rotation can be enabled with the following settings
# It if not enabled here, you can set up logrotate to rotate the files.
# For built in log rotation set LOG_ROTATION = True and configrue the variables
LOG_ROTATION = True
LOG_SIZE = 10485760 # Rotate every 10M
LOG_RETENTION = 10 # Keep 10 Logs

# How many threads use for synchronous methods (services).
# 30 is enough for small installation, for real usage
# it should be slightly more, say 100-300.
THREAD_POOL_SIZE = 300

# RPC call throws TimeoutServiceException once total time since request has been
# placed (time to delivery to client + time for processing on the client)
# crosses _TOTAL (in second).
# _TOTAL reflects the fact that not all transports deliver RPC requests to the clients
# instantly, so request can wait some time in the buffer on server side.
# NOT IMPLEMENTED YET
#RPC_TIMEOUT_TOTAL = 600

# RPC call throws TimeoutServiceException once client is processing request longer
# than _PROCESS (in second)
# NOT IMPLEMENTED YET
#RPC_TIMEOUT_PROCESS = 30

# Do you want to expose "example" service in server?
# Useful for learning the server,you probably want to disable
# Disable the example service
ENABLE_EXAMPLE_SERVICE = False

# Port used for Socket transport. Use 'None' for disabling the transport.
LISTEN_SOCKET_TRANSPORT = 3333
# Port used for HTTP Poll transport. Use 'None' for disabling the transport
LISTEN_HTTP_TRANSPORT = None
# Port used for HTTPS Poll transport
LISTEN_HTTPS_TRANSPORT = None
# Port used for WebSocket transport, 'None' for disabling WS
LISTEN_WS_TRANSPORT = None
# Port used for secure WebSocket, 'None' for disabling WSS
LISTEN_WSS_TRANSPORT = None
# ******************** SSL SETTINGS ******************

# Private key and certification file for SSL protected transports
# You can find howto for generating self-signed certificate in README file
SSL_PRIVKEY = 'server.key'
SSL_CACERT = 'server.crt'

# ******************** TCP SETTINGS ******************

# Enables support for socket encapsulation, which is compatible
# with haproxy 1.5+. By enabling this, first line of received
# data will represent some metadata about proxied stream:
# PROXY <TCP4 or TCP6> <source IP> <dest IP> <source port> </dest port>\n
#
# Full specification: http://haproxy.1wt.eu/download/1.5/doc/proxy-protocol.txt
TCP_PROXY_PROTOCOL = False

# ******************** HTTP SETTINGS *****************

# Keepalive for HTTP transport sessions (at this time for both poll and push)
# High value leads to higher memory usage (all sessions are stored in memory ATM).
# Low value leads to more frequent session reinitializing (like downloading address history).
HTTP_SESSION_TIMEOUT = 3600 # in seconds

# Maximum number of messages (notifications, responses) waiting to delivery to HTTP Poll clients.
# Buffer length is PER CONNECTION. High value will consume a lot of RAM,
# short history will cause that in some edge cases clients won't receive older events.
HTTP_BUFFER_LIMIT = 10000

# User agent used in HTTP requests (for both HTTP transports and for proxy calls from services)
USER_AGENT = 'Stratum/0.1'

# Provide human-friendly user interface on HTTP transports for browsing exposed services.
BROWSER_ENABLE = True

# ******************** *COIND SETTINGS ************

# Hostname and credentials for one trusted Bitcoin node ("Satoshi's client").
# Stratum uses both P2P port (which is 8333 everytime) and RPC port
COINDAEMON_TRUSTED_HOST = '127.0.0.1'
COINDAEMON_TRUSTED_PORT = 8332 # RPC port
COINDAEMON_TRUSTED_USER = 'stratum'
COINDAEMON_TRUSTED_PASSWORD = '***somepassword***'


# Coin Algorithm is the option used to determine the algortithm used by stratum
# This currently only works with POW SHA256 and Scrypt Coins
# The available options are scrypt and sha256d.
# If the option does not meet either of these criteria stratum defaults to scry$
# Until AutoReward Selecting Code has been implemented the below options are us$
# For Reward type there is POW and POS. please ensure you choose the currect ty$
# For SHA256 PoS Coins which support TX Messages please enter yes in the TX sel$
COINDAEMON_ALGO = 'scrypt'
COINDAEMON_Reward = 'POW'
COINDAEMON_SHA256_TX = 'yes'

# ******************** OTHER CORE SETTINGS *********************
# Use "echo -n '<yourpassword>' | sha256sum | cut -f1 -d' ' "
# for calculating SHA256 of your preferred password
ADMIN_PASSWORD_SHA256 = None # Admin functionality is disabled
#ADMIN_PASSWORD_SHA256 = '9e6c0c1db1e0dfb3fa5159deb4ecd9715b3c8cd6b06bd4a3ad77e9a8c5694219' # SHA256 of the password

# IP from which admin calls are allowed.
# Set None to allow admin calls from all IPs
ADMIN_RESTRICT_INTERFACE = '127.0.0.1'

# Use "./signature.py > signing_key.pem" to generate unique signing key for your server
SIGNING_KEY = None # Message signing is disabled
#SIGNING_KEY = 'signing_key.pem'

# Origin of signed messages. Provide some unique string,
# ideally URL where users can find some information about your identity
SIGNING_ID = None
#SIGNING_ID = 'stratum.somedomain.com' # Use custom string
#SIGNING_ID = HOSTNAME # Use hostname as the signing ID

# *********************** IRC / PEER CONFIGURATION *************

IRC_NICK =  "stratum%s" # Skip IRC registration
#IRC_NICK = "stratum" # Use nickname of your choice

# Which hostname / external IP expose in IRC room
# This should be official HOSTNAME for normal operation.
#IRC_HOSTNAME = HOSTNAME

# Don't change this unless you're creating private Stratum cloud.
#IRC_SERVER = 'irc.freenode.net'
#IRC_ROOM = '#stratum-mining-nodes'
#IRC_PORT = 6667

# Hardcoded list of Stratum nodes for clients to switch when this node is not available.
PEERS = [
    {
        'hostname': 'stratum.bitcoin.cz',
        'trusted': True, # This node is trustworthy
        'weight': -1, # Higher number means higher priority for selection.
                      # -1 will work mostly as a backup when other servers won't work.
                      # (IRC peers have weight=0 automatically).
    },
]


'''
DATABASE_DRIVER = 'MySQLdb'
DATABASE_HOST = 'palatinus.cz'
DATABASE_DBNAME = 'marekp_bitcointe'
DATABASE_USER = 'marekp_bitcointe'
DATABASE_PASSWORD = '**empty**'
'''

#VADRIFF
# Variable Difficulty Enable
VARIABLE_DIFF = False        # Master variable difficulty enable

# Variable diff tuning variables
#VARDIFF will start at the POOL_TARGET. It can go as low as the VDIFF_MIN and as high as min(VDIFF_MAX or the coin daemon's difficulty)
USE_COINDAEMON_DIFF = False   # Set the maximum difficulty to the *coin difficulty.
DIFF_UPDATE_FREQUENCY = 86400 # Update the *coin difficulty once a day for the VARDIFF maximum
VDIFF_MIN_TARGET = 15       #  Minimum Target difficulty
VDIFF_MAX_TARGET = 1000     # Maximum Target difficulty
VDIFF_MIN_CHANGE = 1        # Minimum change of worker's difficulty if VDIFF_X2_TYPE=False and the final difficulty will be within the boundaries (VDIFF_MIN_TARGET, VDIFF_MAX_TARGET)
VDIFF_TARGET_TIME = 30      # Target time per share (i.e. try to get 1 share per this many seconds)
VDIFF_RETARGET_TIME = 120       # Check to see if we should retarget this often
VDIFF_VARIANCE_PERCENT = 20 # Allow average time to very this % from target without retarget

#### Advanced Option #####
# For backwards compatibility, we send the scrypt hash to the solutions column in the shares table
# For block confirmation, we have an option to send the block hash in
# Please make sure your front end is compatible with the block hash in the solutions table.
SOLUTION_BLOCK_HASH = True # If enabled, send the block hash. If false send the scrypt hash in the shares table

# ******************** Adv. DB Settings *********************
#  Don't change these unless you know what you are doing

DB_LOADER_CHECKTIME = 15    # How often we check to see if we should run the loader
DB_LOADER_REC_MIN = 1       # Min Records before the bulk loader fires
DB_LOADER_REC_MAX = 50      # Max Records the bulk loader will commit at a time

DB_LOADER_FORCE_TIME = 300      # How often the cache should be flushed into the DB regardless of size.

DB_STATS_AVG_TIME = 300     # When using the DATABASE_EXTEND option, average speed over X sec
                #   Note: this is also how often it updates
DB_USERCACHE_TIME = 600     # How long the usercache is good for before we refresh



########NEW FILE########
__FILENAME__ = exceptions
from stratum.custom_exceptions import ServiceException

class SubmitException(ServiceException):
    pass
########NEW FILE########
__FILENAME__ = extranonce_counter
import struct
import lib.logger
log = lib.logger.get_logger('extronance')

class ExtranonceCounter(object):
    '''Implementation of a counter producing
       unique extranonce across all pool instances.
       This is just dumb "quick&dirty" solution,
       but it can be changed at any time without breaking anything.'''       

    def __init__(self, instance_id):
        log.debug("Got to Extronance Counter")
        if instance_id < 0 or instance_id > 31:
            raise Exception("Current ExtranonceCounter implementation needs an instance_id in <0, 31>.")
        log.debug("Got To Extronance")

        # Last 5 most-significant bits represents instance_id
        # The rest is just an iterator of jobs.
        self.counter = instance_id << 27
        self.size = struct.calcsize('>L')
        
    def get_size(self):
        '''Return expected size of generated extranonce in bytes'''
        return self.size
    
    def get_new_bin(self):
        self.counter += 1
        return struct.pack('>L', self.counter)
        

########NEW FILE########
__FILENAME__ = halfnode
#!/usr/bin/python
# Public Domain
# Original author: ArtForz
# Twisted integration: slush

import struct
import socket
import binascii
import time
import sys
import random
import cStringIO
from Crypto.Hash import SHA256

from twisted.internet.protocol import Protocol
from util import *
import settings

import lib.logger
log = lib.logger.get_logger('halfnode')
log.debug("Got to Halfnode")

if settings.COINDAEMON_ALGO == 'scrypt':
    log.debug("########################################### Loading LTC Scrypt #########################################################")
    import ltc_scrypt
elif settings.COINDAEMON_ALGO == 'scrypt-jane':
    __import__(settings.SCRYPTJANE_NAME)
    log.debug("########################################### LoadingScrypt jane #########################################################")
elif settings.COINDAEMON_ALGO == 'quark':
    log.debug("########################################### Loading Quark Support #########################################################")
    import quark_hash
elif settings.COINDAEMON_ALGO == 'skeinhash':
    import skeinhash

else: 
    log.debug("########################################### Loading SHA256 Support ######################################################")
if settings.COINDAEMON_TX != False:
    log.debug("########################################### Loading SHA256 Transaction Message Support #########################################################")
    pass
else:
    log.debug("########################################### NOT Loading SHA256 Transaction Message Support ######################################################")
    pass


MY_VERSION = 31402
MY_SUBVERSION = ".4"

class CAddress(object):
    def __init__(self):
        self.nTime = 0
        self.nServices = 1
        self.pchReserved = "\x00" * 10 + "\xff" * 2
        self.ip = "0.0.0.0"
        self.port = 0
    def deserialize(self, f):
        #self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nServices = struct.unpack("<Q", f.read(8))[0]
        self.pchReserved = f.read(12)
        self.ip = socket.inet_ntoa(f.read(4))
        self.port = struct.unpack(">H", f.read(2))[0]
    def serialize(self):
        r = ""
        #r += struct.pack("<I", self.nTime)
        r += struct.pack("<Q", self.nServices)
        r += self.pchReserved
        r += socket.inet_aton(self.ip)
        r += struct.pack(">H", self.port)
        return r
    def __repr__(self):
        return "CAddress(nServices=%i ip=%s port=%i)" % (self.nServices, self.ip, self.port)

class CInv(object):
    typemap = {
        0: "Error",
        1: "TX",
        2: "Block"}
    def __init__(self):
        self.type = 0
        self.hash = 0L
    def deserialize(self, f):
        self.type = struct.unpack("<i", f.read(4))[0]
        self.hash = deser_uint256(f)
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.type)
        r += ser_uint256(self.hash)
        return r
    def __repr__(self):
        return "CInv(type=%s hash=%064x)" % (self.typemap[self.type], self.hash)

class CBlockLocator(object):
    def __init__(self):
        self.nVersion = MY_VERSION
        self.vHave = []
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.vHave = deser_uint256_vector(f)
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.nVersion)
        r += ser_uint256_vector(self.vHave)
        return r
    def __repr__(self):
        return "CBlockLocator(nVersion=%i vHave=%s)" % (self.nVersion, repr(self.vHave))

class COutPoint(object):
    def __init__(self):
        self.hash = 0
        self.n = 0
    def deserialize(self, f):
        self.hash = deser_uint256(f)
        self.n = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += ser_uint256(self.hash)
        r += struct.pack("<I", self.n)
        return r
    def __repr__(self):
        return "COutPoint(hash=%064x n=%i)" % (self.hash, self.n)

class CTxIn(object):
    def __init__(self):
        self.prevout = COutPoint()
        self.scriptSig = ""
        self.nSequence = 0
    def deserialize(self, f):
        self.prevout = COutPoint()
        self.prevout.deserialize(f)
        self.scriptSig = deser_string(f)
        self.nSequence = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += self.prevout.serialize()
        r += ser_string(self.scriptSig)
        r += struct.pack("<I", self.nSequence)
        return r
    def __repr__(self):
        return "CTxIn(prevout=%s scriptSig=%s nSequence=%i)" % (repr(self.prevout), binascii.hexlify(self.scriptSig), self.nSequence)

class CTxOut(object):
    def __init__(self):
        self.nValue = 0
        self.scriptPubKey = ""
    def deserialize(self, f):
        self.nValue = struct.unpack("<q", f.read(8))[0]
        self.scriptPubKey = deser_string(f)
    def serialize(self):
        r = ""
        r += struct.pack("<q", self.nValue)
        r += ser_string(self.scriptPubKey)
        return r
    def __repr__(self):
        return "CTxOut(nValue=%i.%08i scriptPubKey=%s)" % (self.nValue // 100000000, self.nValue % 100000000, binascii.hexlify(self.scriptPubKey))

class CTransaction(object):
    def __init__(self):
        if settings.COINDAEMON_Reward == 'POW':
            self.nVersion = 1
            if settings.COINDAEMON_TX != False:
                self.nVersion = 2
            self.vin = []
            self.vout = []
            self.nLockTime = 0
            self.sha256 = None
        elif settings.COINDAEMON_Reward == 'POS':
            self.nVersion = 1
            if settings.COINDAEMON_TX != False:
                self.nVersion = 2
            self.nTime = 0
            self.vin = []
            self.vout = []
            self.nLockTime = 0
            self.sha256 = None
        if settings.COINDAEMON_TX != False: 
            self.strTxComment = ""

    def deserialize(self, f):
        if settings.COINDAEMON_Reward == 'POW':
            self.nVersion = struct.unpack("<i", f.read(4))[0]
            self.vin = deser_vector(f, CTxIn)
            self.vout = deser_vector(f, CTxOut)
            self.nLockTime = struct.unpack("<I", f.read(4))[0]
            self.sha256 = None
        elif settings.COINDAEMON_Reward == 'POS':
            self.nVersion = struct.unpack("<i", f.read(4))[0]
            self.nTime = struct.unpack("<i", f.read(4))[0]
            self.vin = deser_vector(f, CTxIn)
            self.vout = deser_vector(f, CTxOut)
            self.nLockTime = struct.unpack("<I", f.read(4))[0]
            self.sha256 = None
        if settings.COINDAEMON_TX != False:
            self.strTxComment = deser_string(f)

    def serialize(self):
        if settings.COINDAEMON_Reward == 'POW':
            r = ""
            r += struct.pack("<i", self.nVersion)
            r += ser_vector(self.vin)
            r += ser_vector(self.vout)
            r += struct.pack("<I", self.nLockTime)
        elif settings.COINDAEMON_Reward == 'POS':
            r = ""
            r += struct.pack("<i", self.nVersion)
            r += struct.pack("<i", self.nTime)
            r += ser_vector(self.vin)
            r += ser_vector(self.vout)
            r += struct.pack("<I", self.nLockTime)
        if settings.COINDAEMON_TX != False:
            r += ser_string(self.strTxComment)
        return r
 
    def calc_sha256(self):
        if self.sha256 is None:
            self.sha256 = uint256_from_str(SHA256.new(SHA256.new(self.serialize()).digest()).digest())
        return self.sha256
    
    def is_valid(self):
        self.calc_sha256()
        for tout in self.vout:
            if tout.nValue < 0 or tout.nValue > 21000000L * 100000000L:
                return False
        return True
    def __repr__(self):
        return "CTransaction(nVersion=%i vin=%s vout=%s nLockTime=%i)" % (self.nVersion, repr(self.vin), repr(self.vout), self.nLockTime)

class CBlock(object):
    def __init__(self):
        self.nVersion = 1
        self.hashPrevBlock = 0
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nBits = 0
        self.nNonce = 0
        self.vtx = []
        self.sha256 = None
        if settings.COINDAEMON_ALGO == 'scrypt':
            self.scrypt= None
        elif settings.COINDAEMON_ALGO == 'scrypt-jane':
            self.scryptjane = None
        elif settings.COINDAEMON_ALGO == 'quark':
            self.quark = None
        elif settings.COINDAEMON_ALGO == 'skein':
            self.skein = None
        if settings.COINDAEMON_Reward == 'POS':
            self.signature = b""
        else: pass

    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.hashPrevBlock = deser_uint256(f)
        self.hashMerkleRoot = deser_uint256(f)
        self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nBits = struct.unpack("<I", f.read(4))[0]
        self.nNonce = struct.unpack("<I", f.read(4))[0]
        self.vtx = deser_vector(f, CTransaction)
        if settings.COINDAEMON_Reward == 'POS':
            self.signature = deser_string(f)
        else: pass

    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(ser_uint256(self.hashPrevBlock))
        r.append(ser_uint256(self.hashMerkleRoot))
        r.append(struct.pack("<I", self.nTime))
        r.append(struct.pack("<I", self.nBits))
        r.append(struct.pack("<I", self.nNonce))
        r.append(ser_vector(self.vtx))
        if settings.COINDAEMON_Reward == 'POS':
            r.append(ser_string(self.signature))
        else: pass
        return ''.join(r)

    if settings.COINDAEMON_ALGO == 'scrypt':
       def calc_scrypt(self):
           if self.scrypt is None:
               r = []
               r.append(struct.pack("<i", self.nVersion))
               r.append(ser_uint256(self.hashPrevBlock))
               r.append(ser_uint256(self.hashMerkleRoot))
               r.append(struct.pack("<I", self.nTime))
               r.append(struct.pack("<I", self.nBits))
               r.append(struct.pack("<I", self.nNonce))
               self.scrypt = uint256_from_str(ltc_scrypt.getPoWHash(''.join(r)))
           return self.scrypt
    elif settings.COINDAEMON_ALGO == 'quark':
         def calc_quark(self):
             if self.quark is None:
                r = []
                r.append(struct.pack("<i", self.nVersion))
                r.append(ser_uint256(self.hashPrevBlock))
                r.append(ser_uint256(self.hashMerkleRoot))
                r.append(struct.pack("<I", self.nTime))
                r.append(struct.pack("<I", self.nBits))
                r.append(struct.pack("<I", self.nNonce))
                self.quark = uint256_from_str(quark_hash.getPoWHash(''.join(r)))
             return self.quark
    elif settings.COINDAEMON_ALGO == 'scrypt-jane':
        def calc_scryptjane(self):
             if self.scryptjane is None:
                r = []
                r.append(struct.pack("<i", self.nVersion))
                r.append(ser_uint256(self.hashPrevBlock))
                r.append(ser_uint256(self.hashMerkleRoot))
                r.append(struct.pack("<I", self.nTime))
                r.append(struct.pack("<I", self.nBits))
                r.append(struct.pack("<I", self.nNonce))
                self.scryptjane = uint256_from_str(settings.SCRYPTJANE_NAME.getPoWHash(''.join(r)))
             return self.scryptjane
    elif settings.COINDAEMON_ALGO == 'skein':
        def calc_skein(self):
             if self.skein is None:
                r = []
                r.append(struct.pack("<i", self.nVersion))
                r.append(ser_uint256(self.hashPrevBlock))
                r.append(ser_uint256(self.hashMerkleRoot))
                r.append(struct.pack("<I", self.nTime))
                r.append(struct.pack("<I", self.nBits))
                r.append(struct.pack("<I", self.nNonce))
                self.skein = uint256_from_str(skeinhash.skeinhash(''.join(r)))
             return self.skein
    else:
       def calc_sha256(self):
           if self.sha256 is None:
               r = []
               r.append(struct.pack("<i", self.nVersion))
               r.append(ser_uint256(self.hashPrevBlock))
               r.append(ser_uint256(self.hashMerkleRoot))
               r.append(struct.pack("<I", self.nTime))
               r.append(struct.pack("<I", self.nBits))
               r.append(struct.pack("<I", self.nNonce))
               self.sha256 = uint256_from_str(SHA256.new(SHA256.new(''.join(r)).digest()).digest())
           return self.sha256


    def is_valid(self):
        if settings.COINDAEMON_ALGO == 'scrypt':
            self.calc_scrypt()
        elif settings.COINDAEMON_ALGO == 'quark':
            self.calc_quark()
        elif settings.COINDAEMON_ALGO == 'scrypt-jane':
            self.calc_scryptjane
        elif settings.COINDAEMON_ALGO == 'skein':
            self.calc_skein
        else:
            self.calc_sha256()

        target = uint256_from_compact(self.nBits)

        if settings.COINDAEMON_ALGO == 'scrypt':
            if self.scrypt > target:
                return False
        elif settings.COINDAEMON_ALGO == 'quark':
            if self.quark > target:
                return False
        elif settings.COINDAEMON_ALGO == 'scrypt-jane':
            if self.scryptjane > target:
                return False
        elif settings.COINDAEMON_ALGO == 'skein':
            if self.skein > target:
                return False
        else:
           if self.sha256 > target:
                return False

        hashes = []
        for tx in self.vtx:
            tx.sha256 = None
            if not tx.is_valid():
                return False
            tx.calc_sha256()
            hashes.append(ser_uint256(tx.sha256))
        
        while len(hashes) > 1:
            newhashes = []
            for i in xrange(0, len(hashes), 2):
                i2 = min(i+1, len(hashes)-1)
                newhashes.append(SHA256.new(SHA256.new(hashes[i] + hashes[i2]).digest()).digest())
            hashes = newhashes
        
        if uint256_from_str(hashes[0]) != self.hashMerkleRoot:
            return False
        return True
    def __repr__(self):
        return "CBlock(nVersion=%i hashPrevBlock=%064x hashMerkleRoot=%064x nTime=%s nBits=%08x nNonce=%08x vtx=%s)" % (self.nVersion, self.hashPrevBlock, self.hashMerkleRoot, time.ctime(self.nTime), self.nBits, self.nNonce, repr(self.vtx))

class msg_version(object):
    command = "version"
    def __init__(self):
        self.nVersion = MY_VERSION
        self.nServices = 0
        self.nTime = time.time()
        self.addrTo = CAddress()
        self.addrFrom = CAddress()
        self.nNonce = random.getrandbits(64)
        self.strSubVer = MY_SUBVERSION
        self.nStartingHeight = 0
        
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        if self.nVersion == 10300:
            self.nVersion = 300
        self.nServices = struct.unpack("<Q", f.read(8))[0]
        self.nTime = struct.unpack("<q", f.read(8))[0]
        self.addrTo = CAddress()
        self.addrTo.deserialize(f)
        self.addrFrom = CAddress()
        self.addrFrom.deserialize(f)
        self.nNonce = struct.unpack("<Q", f.read(8))[0]
        self.strSubVer = deser_string(f)
        self.nStartingHeight = struct.unpack("<i", f.read(4))[0]
    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(struct.pack("<Q", self.nServices))
        r.append(struct.pack("<q", self.nTime))
        r.append(self.addrTo.serialize())
        r.append(self.addrFrom.serialize())
        r.append(struct.pack("<Q", self.nNonce))
        r.append(ser_string(self.strSubVer))
        r.append(struct.pack("<i", self.nStartingHeight))
        return ''.join(r)
    def __repr__(self):
        return "msg_version(nVersion=%i nServices=%i nTime=%s addrTo=%s addrFrom=%s nNonce=0x%016X strSubVer=%s nStartingHeight=%i)" % (self.nVersion, self.nServices, time.ctime(self.nTime), repr(self.addrTo), repr(self.addrFrom), self.nNonce, self.strSubVer, self.nStartingHeight)

class msg_verack(object):
    command = "verack"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_verack()"

class msg_addr(object):
    command = "addr"
    def __init__(self):
        self.addrs = []
    def deserialize(self, f):
        self.addrs = deser_vector(f, CAddress)
    def serialize(self):
        return ser_vector(self.addrs)
    def __repr__(self):
        return "msg_addr(addrs=%s)" % (repr(self.addrs))

class msg_inv(object):
    command = "inv"
    def __init__(self):
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_inv(inv=%s)" % (repr(self.inv))

class msg_getdata(object):
    command = "getdata"
    def __init__(self):
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_getdata(inv=%s)" % (repr(self.inv))

class msg_getblocks(object):
    command = "getblocks"
    def __init__(self):
        self.locator = CBlockLocator()
        self.hashstop = 0L
    def deserialize(self, f):
        self.locator = CBlockLocator()
        self.locator.deserialize(f)
        self.hashstop = deser_uint256(f)
    def serialize(self):
        r = []
        r.append(self.locator.serialize())
        r.append(ser_uint256(self.hashstop))
        return ''.join(r)
    def __repr__(self):
        return "msg_getblocks(locator=%s hashstop=%064x)" % (repr(self.locator), self.hashstop)

class msg_tx(object):
    command = "tx"
    def __init__(self):
        self.tx = CTransaction()
    def deserialize(self, f):
        self.tx.deserialize(f)
    def serialize(self):
        return self.tx.serialize()
    def __repr__(self):
        return "msg_tx(tx=%s)" % (repr(self.tx))

class msg_block(object):
    command = "block"
    def __init__(self):
        self.block = CBlock()
    def deserialize(self, f):
        self.block.deserialize(f)
    def serialize(self):
        return self.block.serialize()
    def __repr__(self):
        return "msg_block(block=%s)" % (repr(self.block))

class msg_getaddr(object):
    command = "getaddr"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_getaddr()"

class msg_ping(object):
    command = "ping"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_ping()"

class msg_alert(object):
    command = "alert"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_alert()"
    
class BitcoinP2PProtocol(Protocol):
    messagemap = {
        "version": msg_version,
        "verack": msg_verack,
        "addr": msg_addr,
        "inv": msg_inv,
        "getdata": msg_getdata,
        "getblocks": msg_getblocks,
        "tx": msg_tx,
        "block": msg_block,
        "getaddr": msg_getaddr,
        "ping": msg_ping,
        "alert": msg_alert,
    }
   
    def connectionMade(self):
        peer = self.transport.getPeer()
        self.dstaddr = peer.host
        self.dstport = peer.port
        self.recvbuf = ""
        self.last_sent = 0
 
        t = msg_version()
        t.nStartingHeight = getattr(self, 'nStartingHeight', 0)
        t.addrTo.ip = self.dstaddr
        t.addrTo.port = self.dstport
        t.addrTo.nTime = time.time()
        t.addrFrom.ip = "0.0.0.0"
        t.addrFrom.port = 0
        t.addrFrom.nTime = time.time()
        self.send_message(t)
        
    def dataReceived(self, data):
        self.recvbuf += data
        self.got_data()
        
    def got_data(self):
        while True:
            if len(self.recvbuf) < 4:
                return
            if self.recvbuf[:4] != "\xf9\xbe\xb4\xd9":
                raise ValueError("got garbage %s" % repr(self.recvbuf))

            if len(self.recvbuf) < 4 + 12 + 4 + 4:
                return
            command = self.recvbuf[4:4+12].split("\x00", 1)[0]
            msglen = struct.unpack("<i", self.recvbuf[4+12:4+12+4])[0]
            checksum = self.recvbuf[4+12+4:4+12+4+4]
            if len(self.recvbuf) < 4 + 12 + 4 + 4 + msglen:
                return
            msg = self.recvbuf[4+12+4+4:4+12+4+4+msglen]
            th = SHA256.new(msg).digest()
            h = SHA256.new(th).digest()
            if checksum != h[:4]:
                raise ValueError("got bad checksum %s" % repr(self.recvbuf))
            self.recvbuf = self.recvbuf[4+12+4+4+msglen:]

            if command in self.messagemap:
                f = cStringIO.StringIO(msg)
                t = self.messagemap[command]()
                t.deserialize(f)
                self.got_message(t)
            else:
                print "UNKNOWN COMMAND", command, repr(msg)
                
    def prepare_message(self, message):       
        command = message.command
        data = message.serialize()
        tmsg = "\xf9\xbe\xb4\xd9"
        tmsg += command
        tmsg += "\x00" * (12 - len(command))
        tmsg += struct.pack("<I", len(data))
        th = SHA256.new(data).digest()
        h = SHA256.new(th).digest()
        tmsg += h[:4]
        tmsg += data
        return tmsg
    
    def send_serialized_message(self, tmsg):
        if not self.connected:
            return
        
        self.transport.write(tmsg)
        self.last_sent = time.time()       
        
    def send_message(self, message):
        if not self.connected:
            return
        
        #print message.command
        
        #print "send %s" % repr(message)
        command = message.command
        data = message.serialize()
        tmsg = "\xf9\xbe\xb4\xd9"
        tmsg += command
        tmsg += "\x00" * (12 - len(command))
        tmsg += struct.pack("<I", len(data))
        th = SHA256.new(data).digest()
        h = SHA256.new(th).digest()
        tmsg += h[:4]
        tmsg += data
        
        #print tmsg, len(tmsg)
        self.transport.write(tmsg)
        self.last_sent = time.time()
        
    def got_message(self, message):
        if self.last_sent + 30 * 60 < time.time():
            self.send_message(msg_ping())

        mname = 'do_' + message.command
        #print mname
        if not hasattr(self, mname):
            return

        method = getattr(self, mname)
        method(message)

#        if message.command == "tx":
#            message.tx.calc_sha256()
#            sha256 = message.tx.sha256
#            pubkey = binascii.hexlify(message.tx.vout[0].scriptPubKey)
#            txlock.acquire()
#            tx.append([str(sha256), str(time.time()), str(self.dstaddr), pubkey])
#            txlock.release()

    def do_version(self, message):
        #print message
        self.send_message(msg_verack())

    def do_inv(self, message):
        want = msg_getdata()
        for i in message.inv:
            if i.type == 1:
                want.inv.append(i)
            if i.type == 2:
                want.inv.append(i)
        if len(want.inv):
            self.send_message(want)

########NEW FILE########
__FILENAME__ = logger
'''Simple wrapper around python's logging package'''

import os
import logging
from logging import handlers
from twisted.python import log as twisted_log

import settings

'''
class Logger(object):
    def debug(self, msg):
        twisted_log.msg(msg)

    def info(self, msg):
        twisted_log.msg(msg)

    def warning(self, msg):
        twisted_log.msg(msg)
        
    def error(self, msg):
        twisted_log.msg(msg)
        
    def critical(self, msg):
        twisted_log.msg(msg)
'''

def get_logger(name):    
    logger = logging.getLogger(name)
    logger.addHandler(stream_handler)
    logger.setLevel(getattr(logging, settings.LOGLEVEL))
    
    if settings.LOGFILE != None:
        logger.addHandler(file_handler)
    
    logger.debug("Logging initialized")
    return logger
    #return Logger()

if settings.DEBUG:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(module)s.%(funcName)s # %(message)s")
else:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s # %(message)s")
    
if settings.LOGFILE != None:
    # Create the log folder if it does not exist
    try:
        os.makedirs(os.path.join(os.getcwd(), settings.LOGDIR))
    except OSError:
        pass

    # Setup log rotation if specified in the config
    if settings.LOG_ROTATION:
        file_handler = logging.handlers.RotatingFileHandler(os.path.join(settings.LOGDIR, settings.LOGFILE),'a', settings.LOG_SIZE,settings.LOG_RETENTION)
    else:
        file_handler = logging.handlers.WatchedFileHandler(os.path.join(settings.LOGDIR, settings.LOGFILE))
    file_handler.setFormatter(fmt)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(fmt)

########NEW FILE########
__FILENAME__ = merkletree
# Eloipool - Python Bitcoin pool server
# Copyright (C) 2011-2012  Luke Dashjr <luke-jr+eloipool@utopios.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from hashlib import sha256
from util import doublesha

class MerkleTree:
    def __init__(self, data, detailed=False):
        self.data = data
        self.recalculate(detailed)
        self._hash_steps = None
    
    def recalculate(self, detailed=False):
        L = self.data
        steps = []
        if detailed:
            detail = []
            PreL = []
            StartL = 0
        else:
            detail = None
            PreL = [None]
            StartL = 2
        Ll = len(L)
        if detailed or Ll > 1:
            while True:
                if detailed:
                    detail += L
                if Ll == 1:
                    break
                steps.append(L[1])
                if Ll % 2:
                    L += [L[-1]]
                L = PreL + [doublesha(L[i] + L[i + 1]) for i in range(StartL, Ll, 2)]
                Ll = len(L)
        self._steps = steps
        self.detail = detail
    
    def hash_steps(self):
        if self._hash_steps == None:
            self._hash_steps = doublesha(''.join(self._steps))
        return self._hash_steps
        
    def withFirst(self, f):
        steps = self._steps
        for s in steps:
            f = doublesha(f + s)
        return f
    
    def merkleRoot(self):
        return self.withFirst(self.data[0])

# MerkleTree tests
def _test():
    import binascii
    import time    
        
    mt = MerkleTree([None] + [binascii.unhexlify(a) for a in [
        '999d2c8bb6bda0bf784d9ebeb631d711dbbbfe1bc006ea13d6ad0d6a2649a971',
        '3f92594d5a3d7b4df29d7dd7c46a0dac39a96e751ba0fc9bab5435ea5e22a19d',
        'a5633f03855f541d8e60a6340fc491d49709dc821f3acb571956a856637adcb6',
        '28d97c850eaf917a4c76c02474b05b70a197eaefb468d21c22ed110afe8ec9e0',
    ]])
    assert(
        b'82293f182d5db07d08acf334a5a907012bbb9990851557ac0ec028116081bd5a' ==
        binascii.b2a_hex(mt.withFirst(binascii.unhexlify('d43b669fb42cfa84695b844c0402d410213faa4f3e66cb7248f688ff19d5e5f7')))
    )
    
    print '82293f182d5db07d08acf334a5a907012bbb9990851557ac0ec028116081bd5a'
    txes = [binascii.unhexlify(a) for a in [
        'd43b669fb42cfa84695b844c0402d410213faa4f3e66cb7248f688ff19d5e5f7',
        '999d2c8bb6bda0bf784d9ebeb631d711dbbbfe1bc006ea13d6ad0d6a2649a971',
        '3f92594d5a3d7b4df29d7dd7c46a0dac39a96e751ba0fc9bab5435ea5e22a19d',
        'a5633f03855f541d8e60a6340fc491d49709dc821f3acb571956a856637adcb6',
        '28d97c850eaf917a4c76c02474b05b70a197eaefb468d21c22ed110afe8ec9e0',
    ]]
             
    s = time.time()
    mt = MerkleTree(txes)
    for x in range(100):
        y = int('d43b669fb42cfa84695b844c0402d410213faa4f3e66cb7248f688ff19d5e5f7', 16)
        #y += x
        coinbasehash = binascii.unhexlify("%x" % y)
        x = binascii.b2a_hex(mt.withFirst(coinbasehash))

    print x
    print time.time() - s

if __name__ == '__main__':
    _test()

########NEW FILE########
__FILENAME__ = notify_email
import smtplib
from email.mime.text import MIMEText

from stratum import settings

import stratum.logger
log = stratum.logger.get_logger('Notify_Email')

class NOTIFY_EMAIL():

    def notify_start(self):
        if settings.NOTIFY_EMAIL_TO != '':
            self.send_email(settings.NOTIFY_EMAIL_TO,'Stratum Server Started','Stratum server has started!')
    
    def notify_found_block(self,worker_name):
        if settings.NOTIFY_EMAIL_TO != '':
            text = '%s on Stratum server found a block!' % worker_name
            self.send_email(settings.NOTIFY_EMAIL_TO,'Stratum Server Found Block',text)

    def notify_dead_coindaemon(self,worker_name):
        if settings.NOTIFY_EMAIL_TO != '':
            text = 'Coin Daemon Has Crashed Please Report' % worker_name
            self.send_email(settings.NOTIFY_EMAIL_TO,'Coin Daemon Crashed!',text)

    def send_email(self,to,subject,message):
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = settings.NOTIFY_EMAIL_FROM
        msg['To'] = to
        try:
            s = smtplib.SMTP(settings.NOTIFY_EMAIL_SERVER)
            if settings.NOTIFY_EMAIL_USERNAME != '':
                if settings.NOTIFY_EMAIL_USETLS:
                    s.ehlo()
                    s.starttls()
                s.ehlo()
                s.login(settings.NOTIFY_EMAIL_USERNAME, settings.NOTIFY_EMAIL_PASSWORD)
            s.sendmail(settings.NOTIFY_EMAIL_FROM,to,msg.as_string())
            s.quit()
        except smtplib.SMTPAuthenticationError as e:
            log.error('Error sending Email: %s' % e[1])
        except Exception as e:
            log.error('Error sending Email: %s' % e[0])

########NEW FILE########
__FILENAME__ = settings
def setup():
    '''
        This will import modules config_default and config and move their variables
        into current module (variables in config have higher priority than config_default).
        Thanks to this, you can import settings anywhere in the application and you'll get
        actual application settings.
        
        This config is related to server side. You don't need config.py if you
        want to use client part only.
    '''
    
    def read_values(cfg):
        for varname in cfg.__dict__.keys():
            if varname.startswith('__'):
                continue
            
            value = getattr(cfg, varname)
            yield (varname, value)

    import config_default
    
    try:
        import conf.config as config
    except ImportError:
        # Custom config not presented, but we can still use defaults
        config = None
            
    import sys
    module = sys.modules[__name__]
    
    for name,value in read_values(config_default):
        module.__dict__[name] = value

    changes = {}
    if config:
        for name,value in read_values(config):
            if value != module.__dict__.get(name, None):
                changes[name] = value
            module.__dict__[name] = value

    if module.__dict__['DEBUG'] and changes:
        print "----------------"
        print "Custom settings:"
        for k, v in changes.items():
            if 'passw' in k.lower():
                print k, ": ********"
            else:
                print k, ":", v
        print "----------------"
        
setup()

########NEW FILE########
__FILENAME__ = skein
# /usr/bin/env python
# coding=utf-8

#  Copyright 2010 Jonathan Bowman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Pure Python implementation of the Skein 512-bit hashing algorithm"""

import array
import binascii
import os
import struct

from threefish import (add64, bigint, bytes2words, Threefish512, words,
                        words2bytes, words_format, xrange,
                        zero_bytes, zero_words)

# An empty bytestring that behaves itself whether in Python 2 or 3
empty_bytes = array.array('B').tostring()

class Skein512(object):
    """Skein 512-bit hashing algorithm

    The message to be hashed may be set as `msg` when initialized, or
    passed in later using the ``update`` method.

    Use `key` (a bytestring with arbitrary length) for MAC
    functionality.

    `block_type` will typically be "msg", but may also be one of:
    "key", "nonce", "cfg_final", or "out_final". These will affect the
    tweak value passed to the underlying Threefish block cipher. Again,
    if you don't know which one to choose, "msg" is probably what you
    want.

    Example:

    >>> Skein512("Hello, world!").hexdigest()
    '8449f597f1764274f8bf4a03ead22e0404ea2dc63c8737629e6e282303aebfd5dd96f07e21ae2e7a8b2bdfadd445bd1d71dfdd9745c95b0eb05dc01f289ad765'

    """
    block_size = 64
    block_bits = 512
    block_type = {'key':       0,
                  'nonce':     0x5400000000000000,
                  'msg':       0x7000000000000000,
                  'cfg_final': 0xc400000000000000,
                  'out_final': 0xff00000000000000}

    def __init__(self, msg='', digest_bits=512, key=None,
                 block_type='msg'):
        self.tf = Threefish512()
        if key:
            self.digest_bits = 512
            self._start_new_type('key')
            self.update(key)
            self.tf.key = bytes2words(self.final(False))
        self.digest_bits = digest_bits
        self.digest_size = (digest_bits + 7) >> 3
        self._start_new_type('cfg_final')
        b = words2bytes((0x133414853,digest_bits,0,0,0,0,0,0))
        self._process_block(b,32)
        self._start_new_type(block_type)
        if msg:
            self.update(msg)

    def _start_new_type(self, block_type):
        """Setup new tweak values and internal buffer.

        Primarily for internal use.

        """
        self.buf = empty_bytes
        self.tf.tweak = words([0, self.block_type[block_type]])

    def _process_block(self, block, byte_count_add):
        """Encrypt internal state using Threefish.

        Primarily for internal use.

        """
        block_len = len(block)
        for i in xrange(0,block_len,64):
            w = bytes2words(block[i:i+64])
            self.tf.tweak[0] = add64(self.tf.tweak[0], byte_count_add)
            self.tf.prepare_tweak()
            self.tf.prepare_key()
            self.tf.key = self.tf.encrypt_block(w)
            self.tf._feed_forward(self.tf.key, w)
            # set second tweak value to ~SKEIN_T1_FLAG_FIRST:
            self.tf.tweak[1] &= bigint(0xbfffffffffffffff)

    def update(self, msg):
        """Update internal state with new data to be hashed.

        `msg` is a bytestring, and should be a bytes object in Python 3
        and up, or simply a string in Python 2.5 and 2.6.

        """
        self.buf += msg
        buflen = len(self.buf)
        if buflen > 64:
            end = -(buflen % 64) or (buflen-64)
            data = self.buf[0:end]
            self.buf = self.buf[end:]
            try:
                self._process_block(data, 64)
            except:
                print(len(data))
                print(binascii.b2a_hex(data))

    def final(self, output=True):
        """Return hashed data as bytestring.

        `output` is primarily for internal use. It should only be False
        if you have a clear reason for doing so.

        This function can be called as either ``final`` or ``digest``.

        """
        self.tf.tweak[1] |= bigint(0x8000000000000000) # SKEIN_T1_FLAG_FINAL
        buflen = len(self.buf)
        self.buf += zero_bytes[:64-buflen]

        self._process_block(self.buf, buflen)

        if not output:
            hash_val = words2bytes(self.tf.key)
        else:
            hash_val = empty_bytes
            self.buf = zero_bytes[:]
            key = self.tf.key[:] # temporary copy
            i=0
            while i*64 < self.digest_size:
                self.buf = words_format[1].pack(i) + self.buf[8:]
                self.tf.tweak = [0, self.block_type['out_final']]
                self._process_block(self.buf, 8)
                n = self.digest_size - i*64
                if n >= 64:
                    n = 64
                hash_val += words2bytes(self.tf.key)[0:n]
                self.tf.key = key
                i+=1
        return hash_val

    digest = final

    def hexdigest(self):
        """Return a hexadecimal representation of the hashed data"""
        return binascii.b2a_hex(self.digest())

class Skein512Random(Skein512):
    """A Skein-based pseudo-random bytestring generator.

    If `seed` is unspecified, ``os.urandom`` will be used to provide the
    seed.

    In case you are using this as an iterator, rather than generating
    new data at each iteration, a pool of length `queue_size` is
    generated periodically.

    """
    def __init__(self, seed=None, queue_size=512):
        Skein512.__init__(self, block_type='nonce')
        self.queue = []
        self.queue_size = queue_size
        self.tf.key = zero_words[:]
        if not seed:
          seed = os.urandom(100)
        self.reseed(seed)

    def reseed(self, seed):
        """(Re)seed the generator."""
        self.digest_size = 64
        self.update(words2bytes(self.tf.key) + seed)
        self.tf.key = bytes2words(self.final())

    def getbytes(self, request_bytes):
        """Return random bytestring of length `request_bytes`."""
        self.digest_size = 64 + request_bytes
        self.update(words2bytes(self.tf.key))
        output = self.final()
        self.tf.key = bytes2words(output[0:64])
        return output[64:]

    def __iter__(self):
      return self

    def next(self):
      if not self.queue:
        self.queue = array.array('B', self.getbytes(self.queue_size))
      return self.queue.pop()

if __name__ == '__main__':
    print Skein512('123').hexdigest()
########NEW FILE########
__FILENAME__ = skeinhash
import hashlib
import struct
import skein

def skeinhash(msg):
    return hashlib.sha256(skein.Skein512(msg[:80]).digest()).digest()

def skeinhashmid(msg):
    s = skein.Skein512(msg[:64] + '\x00') # hack to force Skein512.update()
    return struct.pack('<8Q', *s.tf.key.tolist())

if __name__ == '__main__':
    mesg = "dissociative1234dissociative4567dissociative1234dissociative4567dissociative1234"
    h = skeinhashmid(mesg)
    print h.encode('hex')
    print 'ad0d423b18b47f57724e519c42c9d5623308feac3df37aca964f2aa869f170bdf23e97f644e81511df49c59c5962887d17e277e7e8513345137638334c8e59a4' == h.encode('hex')

    h = skeinhash(mesg)
    print h.encode('hex')
    print '764da2e768811e91c6c0c649b052b7109a9bc786bce136a59c8d5a0547cddc54' == h.encode('hex')

########NEW FILE########
__FILENAME__ = template_registry
import weakref
import binascii
import util
import StringIO
import settings
if settings.COINDAEMON_ALGO == 'scrypt':
    import ltc_scrypt
elif settings.COINDAEMON_ALGO  == 'scrypt-jane':
    scryptjane = __import__(settings.SCRYPTJANE_NAME) 
elif settings.COINDAEMON_ALGO == 'quark':
    import quark_hash
elif settings.COINDAEMON_ALGO == 'skeinhash':
    import skeinhash
else: pass
from twisted.internet import defer
from lib.exceptions import SubmitException

import lib.logger
log = lib.logger.get_logger('template_registry')
log.debug("Got to Template Registry")
from mining.interfaces import Interfaces
from extranonce_counter import ExtranonceCounter
import lib.settings as settings


class JobIdGenerator(object):
    '''Generate pseudo-unique job_id. It does not need to be absolutely unique,
    because pool sends "clean_jobs" flag to clients and they should drop all previous jobs.'''
    counter = 0
    
    @classmethod
    def get_new_id(cls):
        cls.counter += 1
        if cls.counter % 0xffff == 0:
            cls.counter = 1
        return "%x" % cls.counter
                
class TemplateRegistry(object):
    '''Implements the main logic of the pool. Keep track
    on valid block templates, provide internal interface for stratum
    service and implements block validation and submits.'''
    
    def __init__(self, block_template_class, coinbaser, bitcoin_rpc, instance_id,
                 on_template_callback, on_block_callback):
        self.prevhashes = {}
        self.jobs = weakref.WeakValueDictionary()
        
        self.extranonce_counter = ExtranonceCounter(instance_id)
        self.extranonce2_size = block_template_class.coinbase_transaction_class.extranonce_size \
                - self.extranonce_counter.get_size()
        log.debug("Got to Template Registry")
        self.coinbaser = coinbaser
        self.block_template_class = block_template_class
        self.bitcoin_rpc = bitcoin_rpc
        self.on_block_callback = on_block_callback
        self.on_template_callback = on_template_callback
        
        self.last_block = None
        self.update_in_progress = False
        self.last_update = None
        
        # Create first block template on startup
        self.update_block()
        
    def get_new_extranonce1(self):
        '''Generates unique extranonce1 (e.g. for newly
        subscribed connection.'''
        log.debug("Getting Unique Extronance")
        return self.extranonce_counter.get_new_bin()
    
    def get_last_broadcast_args(self):
        '''Returns arguments for mining.notify
        from last known template.'''
        log.debug("Getting Laat Template")
        return self.last_block.broadcast_args
        
    def add_template(self, block,block_height):
        '''Adds new template to the registry.
        It also clean up templates which should
        not be used anymore.'''
        
        prevhash = block.prevhash_hex

        if prevhash in self.prevhashes.keys():
            new_block = False
        else:
            new_block = True
            self.prevhashes[prevhash] = []
               
        # Blocks sorted by prevhash, so it's easy to drop
        # them on blockchain update
        self.prevhashes[prevhash].append(block)
        
        # Weak reference for fast lookup using job_id
        self.jobs[block.job_id] = block
        
        # Use this template for every new request
        self.last_block = block
        
        # Drop templates of obsolete blocks
        for ph in self.prevhashes.keys():
            if ph != prevhash:
                del self.prevhashes[ph]
                
        log.info("New template for %s" % prevhash)

        if new_block:
            # Tell the system about new block
            # It is mostly important for share manager
            self.on_block_callback(prevhash, block_height)

        # Everything is ready, let's broadcast jobs!
        self.on_template_callback(new_block)
        

        #from twisted.internet import reactor
        #reactor.callLater(10, self.on_block_callback, new_block) 
              
    def update_block(self):
        '''Registry calls the getblocktemplate() RPC
        and build new block template.'''
        
        if self.update_in_progress:
            # Block has been already detected
            return
        
        self.update_in_progress = True
        self.last_update = Interfaces.timestamper.time()
        
        d = self.bitcoin_rpc.getblocktemplate()
        d.addCallback(self._update_block)
        d.addErrback(self._update_block_failed)
        
    def _update_block_failed(self, failure):
        log.error(str(failure))
        self.update_in_progress = False
        
    def _update_block(self, data):
        start = Interfaces.timestamper.time()
                
        template = self.block_template_class(Interfaces.timestamper, self.coinbaser, JobIdGenerator.get_new_id())
        log.info(template.fill_from_rpc(data))
        self.add_template(template,data['height'])

        log.info("Update finished, %.03f sec, %d txes" % \
                    (Interfaces.timestamper.time() - start, len(template.vtx)))
        
        self.update_in_progress = False        
        return data
    
    def diff_to_target(self, difficulty):
        '''Converts difficulty to target'''
        if settings.COINDAEMON_ALGO == 'scrypt' or 'scrypt-jane':
            diff1 = 0x0000ffff00000000000000000000000000000000000000000000000000000000
        elif settings.COINDAEMON_ALGO == 'quark':
            diff1 = 0x000000ffff000000000000000000000000000000000000000000000000000000
        else:
            diff1 = 0x00000000ffff0000000000000000000000000000000000000000000000000000

        return diff1 / difficulty
    
    def get_job(self, job_id, worker_name, ip=False):
        '''For given job_id returns BlockTemplate instance or None'''
        try:
            j = self.jobs[job_id]
        except:
            log.info("Job id '%s' not found, worker_name: '%s'" % (job_id, worker_name))

            if ip:
                log.info("Worker submited invalid Job id: IP %s", str(ip))

            return None
        
        # Now we have to check if job is still valid.
        # Unfortunately weak references are not bulletproof and
        # old reference can be found until next run of garbage collector.
        if j.prevhash_hex not in self.prevhashes:
            log.info("Prevhash of job '%s' is unknown" % job_id)
            return None
        
        if j not in self.prevhashes[j.prevhash_hex]:
            log.info("Job %s is unknown" % job_id)
            return None
        
        return j
        
    def submit_share(self, job_id, worker_name, session, extranonce1_bin, extranonce2, ntime, nonce,
                     difficulty, ip=False):
        '''Check parameters and finalize block template. If it leads
           to valid block candidate, asynchronously submits the block
           back to the bitcoin network.
        
            - extranonce1_bin is binary. No checks performed, it should be from session data
            - job_id, extranonce2, ntime, nonce - in hex form sent by the client
            - difficulty - decimal number from session
            - submitblock_callback - reference to method which receive result of submitblock()
            - difficulty is checked to see if its lower than the vardiff minimum target or pool target
              from conf/config.py and if it is the share is rejected due to it not meeting the requirements for a share
              
        '''
        if settings.VARIABLE_DIFF == True:
            # Share Diff Should never be 0 
            if difficulty < settings.VDIFF_MIN_TARGET :
        	log.exception("Worker %s @ IP: %s seems to be submitting Fake Shares"%(worker_name,ip))
        	raise SubmitException("Diff is %s Share Rejected Reporting to Admin"%(difficulty))
        else:
             if difficulty < settings.POOL_TARGET:
             	log.exception("Worker %s @ IP: %s seems to be submitting Fake Shares"%(worker_name,ip))
        	raise SubmitException("Diff is %s Share Rejected Reporting to Admin"%(difficulty))
        	
        # Check if extranonce2 looks correctly. extranonce2 is in hex form...
        if len(extranonce2) != self.extranonce2_size * 2:
            raise SubmitException("Incorrect size of extranonce2. Expected %d chars" % (self.extranonce2_size*2))
        
        # Check for job
        job = self.get_job(job_id, worker_name, ip)
        if job == None:
            raise SubmitException("Job '%s' not found" % job_id)
                
        # Check if ntime looks correct
        if len(ntime) != 8:
            raise SubmitException("Incorrect size of ntime. Expected 8 chars")

        if not job.check_ntime(int(ntime, 16)):
            raise SubmitException("Ntime out of range")
        
        # Check nonce        
        if len(nonce) != 8:
            raise SubmitException("Incorrect size of nonce. Expected 8 chars")
        
        # Check for duplicated submit
        if not job.register_submit(extranonce1_bin, extranonce2, ntime, nonce):
            log.info("Duplicate from %s, (%s %s %s %s)" % \
                    (worker_name, binascii.hexlify(extranonce1_bin), extranonce2, ntime, nonce))
            raise SubmitException("Duplicate share")
        
        # Now let's do the hard work!
        # ---------------------------
        
        # 0. Some sugar
        extranonce2_bin = binascii.unhexlify(extranonce2)
        ntime_bin = binascii.unhexlify(ntime)
        nonce_bin = binascii.unhexlify(nonce)
                
        # 1. Build coinbase
        coinbase_bin = job.serialize_coinbase(extranonce1_bin, extranonce2_bin)
        coinbase_hash = util.doublesha(coinbase_bin)
        
        # 2. Calculate merkle root
        merkle_root_bin = job.merkletree.withFirst(coinbase_hash)
        merkle_root_int = util.uint256_from_str(merkle_root_bin)
                
        # 3. Serialize header with given merkle, ntime and nonce
        header_bin = job.serialize_header(merkle_root_int, ntime_bin, nonce_bin)
    
        # 4. Reverse header and compare it with target of the user
        if settings.COINDAEMON_ALGO == 'scrypt':
            hash_bin = ltc_scrypt.getPoWHash(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
        elif settings.COINDAEMON_ALGO  == 'scrypt-jane':
        	if settings.SCRYPTJANE_NAME == 'vtc_scrypt':
            	     hash_bin = scryptjane.getPoWHash(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
      		else: 
      		     hash_bin = scryptjane.getPoWHash(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]), int(ntime, 16))
        elif settings.COINDAEMON_ALGO == 'quark':
            hash_bin = quark_hash.getPoWHash(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
	elif settings.COINDAEMON_ALGO == 'skeinhash':
            hash_bin = skeinhash.skeinhash(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
        else:
            hash_bin = util.doublesha(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))

        hash_int = util.uint256_from_str(hash_bin)
        scrypt_hash_hex = "%064x" % hash_int
        header_hex = binascii.hexlify(header_bin)
        if settings.COINDAEMON_ALGO == 'scrypt' or settings.COINDAEMON_ALGO == 'scrypt-jane':
            header_hex = header_hex+"000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000"
        elif settings.COINDAEMON_ALGO == 'quark':
            header_hex = header_hex+"000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000"
        else: pass
                 
        target_user = self.diff_to_target(difficulty)
        if hash_int > target_user:
            raise SubmitException("Share is above target")

        # Mostly for debugging purposes
        target_info = self.diff_to_target(100000)
        if hash_int <= target_info:
            log.info("Yay, share with diff above 100000")

        # Algebra tells us the diff_to_target is the same as hash_to_diff
        share_diff = int(self.diff_to_target(hash_int))

        # 5. Compare hash with target of the network
        if hash_int <= job.target:
            # Yay! It is block candidate! 
            log.info("We found a block candidate! %s" % scrypt_hash_hex)

            # Reverse the header and get the potential block hash (for scrypt only) 
            #if settings.COINDAEMON_ALGO == 'scrypt' or settings.COINDAEMON_ALGO == 'sha256d':
            #   if settings.COINDAEMON_Reward == 'POW':
            block_hash_bin = util.doublesha(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
            block_hash_hex = block_hash_bin[::-1].encode('hex_codec')
            #else:   block_hash_hex = hash_bin[::-1].encode('hex_codec')
            #else:  block_hash_hex = hash_bin[::-1].encode('hex_codec')
            # 6. Finalize and serialize block object 
            job.finalize(merkle_root_int, extranonce1_bin, extranonce2_bin, int(ntime, 16), int(nonce, 16))
            
            if not job.is_valid():
                # Should not happen
                log.exception("FINAL JOB VALIDATION FAILED!(Try enabling/disabling tx messages)")
                            
            # 7. Submit block to the network
            serialized = binascii.hexlify(job.serialize())
	    on_submit = self.bitcoin_rpc.submitblock(serialized, block_hash_hex, scrypt_hash_hex)
            if on_submit:
                self.update_block()

            if settings.SOLUTION_BLOCK_HASH:
                return (header_hex, block_hash_hex, share_diff, on_submit)
            else:
                return (header_hex, scrypt_hash_hex, share_diff, on_submit)
        
        if settings.SOLUTION_BLOCK_HASH:
        # Reverse the header and get the potential block hash (for scrypt only) only do this if we want to send in the block hash to the shares table
            block_hash_bin = util.doublesha(''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ]))
            block_hash_hex = block_hash_bin[::-1].encode('hex_codec')
            return (header_hex, block_hash_hex, share_diff, None)
        else:
            return (header_hex, scrypt_hash_hex, share_diff, None)

########NEW FILE########
__FILENAME__ = threefish
# /usr/bin/env python
# coding=utf-8

#  Copyright 2010 Jonathan Bowman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Pure Python implementation of the Threefish block cipher

The core of the Skein 512-bit hashing algorithm

"""
from util_numpy import add64, bigint, bytelist, bytes2words, imap, izip, sub64, \
    SKEIN_KS_PARITY, words, words2bytes, words_format, xrange, zero_bytes, zero_words, RotL_64, RotR_64, xor

from itertools import cycle

ROT = bytelist((46, 36, 19, 37,
                33, 27, 14, 42,
                17, 49, 36, 39,
                44,  9, 54, 56,
                39, 30, 34, 24,
                13, 50, 10, 17,
                25, 29, 39, 43,
                 8, 35, 56, 22))

PERM = bytelist(((0,1),(2,3),(4,5),(6,7),
                 (2,1),(4,7),(6,5),(0,3),
                 (4,1),(6,3),(0,5),(2,7),
                 (6,1),(0,7),(2,5),(4,3)))

class Threefish512(object):
    """The Threefish 512-bit block cipher.

    The key and tweak may be set when initialized (as
    bytestrings) or after initialization using the ``tweak`` or
    ``key`` properties. When choosing the latter, be sure to call
    the ``prepare_key`` and ``prepare_tweak`` methods.

    """
    def __init__(self, key=None, tweak=None):
        """Set key and tweak.

        The key and the tweak will be lists of 8 64-bit words
        converted from `key` and `tweak` bytestrings, or all
        zeroes if not specified.

        """
        if key:
            self.key = bytes2words(key)
            self.prepare_key()
        else:
            self.key = words(zero_words[:] + [0])
        if tweak:
            self.tweak = bytes2words(tweak, 2)
            self.prepare_tweak()
        else:
            self.tweak = zero_words[:3]

    def prepare_key(self):
        """Compute key."""
        final = reduce(xor, self.key[:8]) ^ SKEIN_KS_PARITY
        try:
            self.key[8] = final
        except IndexError:
            #self.key.append(final)
            self.key = words(list(self.key) + [final])

    def prepare_tweak(self):
        """Compute tweak."""
        final =  self.tweak[0] ^ self.tweak[1]
        try:
            self.tweak[2] = final
        except IndexError:
            #self.tweak.append(final)
            self.tweak = words(list(self.tweak) + [final])

    def encrypt_block(self, plaintext):
        """Return 8-word ciphertext, encrypted from plaintext.

        `plaintext` must be a list of 8 64-bit words.

        """
        key = self.key
        tweak = self.tweak
        state = words(list(imap(add64, plaintext, key[:8])))
        state[5] = add64(state[5], tweak[0])
        state[6] = add64(state[6], tweak[1])

        for r,s in izip(xrange(1,19),cycle((0,16))):
            for i in xrange(16):
                m,n = PERM[i]
                state[m] = add64(state[m], state[n])
                state[n] = RotL_64(state[n], ROT[i+s])
                state[n] = state[n] ^ state[m]
            for y in xrange(8):
                     state[y] = add64(state[y], key[(r+y) % 9])
            state[5] = add64(state[5], tweak[r % 3])
            state[6] = add64(state[6], tweak[(r+1) % 3])
            state[7] = add64(state[7], r)

        return state

    def _feed_forward(self, state, plaintext):
        """Compute additional step required when hashing.

        Primarily for internal use.

        """
        state[:] = list(imap(xor, state, plaintext))

    def decrypt_block(self, ciphertext):
        """Return 8-word plaintext, decrypted from plaintext.

        `ciphertext` must be a list of 8 64-bit words.

        """
        key = self.key
        tweak = self.tweak
        state = ciphertext[:]

        for r,s in izip(xrange(18,0,-1),cycle((16,0))):
            for y in xrange(8):
                 state[y] = sub64(state[y], key[(r+y) % 9])
            state[5] = sub64(state[5], tweak[r % 3])
            state[6] = sub64(state[6], tweak[(r+1) % 3])
            state[7] = sub64(state[7], r)

            for i in xrange(15,-1,-1):
                m,n = PERM[i]
                state[n] = RotR_64(state[m] ^ state[n], ROT[i+s])
                state[m] = sub64(state[m], state[n])

        result = list(imap(sub64, state, key))
        result[5] = sub64(result[5], tweak[0])
        result[6] = sub64(result[6], tweak[1])
        return result

########NEW FILE########
__FILENAME__ = util
'''Various helper methods. It probably needs some cleanup.'''

import struct
import StringIO
import binascii
import settings
import bitcoin_rpc
from hashlib import sha256

def deser_string(f):
    nit = struct.unpack("<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack("<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack("<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack("<Q", f.read(8))[0]
    return f.read(nit)

def ser_string(s):
    if len(s) < 253:
        return chr(len(s)) + s
    elif len(s) < 0x10000:
        return chr(253) + struct.pack("<H", len(s)) + s
    elif len(s) < 0x100000000L:
        return chr(254) + struct.pack("<I", len(s)) + s
    return chr(255) + struct.pack("<Q", len(s)) + s

def deser_uint256(f):
    r = 0L
    for i in xrange(8):
        t = struct.unpack("<I", f.read(4))[0]
        r += t << (i * 32)
    return r

def ser_uint256(u):
    rs = ""
    for i in xrange(8):
        rs += struct.pack("<I", u & 0xFFFFFFFFL)
        u >>= 32
    return rs

def uint256_from_str(s):
    r = 0L
    t = struct.unpack("<IIIIIIII", s[:32])
    for i in xrange(8):
        r += t[i] << (i * 32)
    return r

def uint256_from_str_be(s):
    r = 0L
    t = struct.unpack(">IIIIIIII", s[:32])
    for i in xrange(8):
        r += t[i] << (i * 32)
    return r

def uint256_from_compact(c):
    nbytes = (c >> 24) & 0xFF
    v = (c & 0xFFFFFFL) << (8 * (nbytes - 3))
    return v

def deser_vector(f, c):
    nit = struct.unpack("<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack("<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack("<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack("<Q", f.read(8))[0]
    r = []
    for i in xrange(nit):
        t = c()
        t.deserialize(f)
        r.append(t)
    return r

def ser_vector(l):
    r = ""
    if len(l) < 253:
        r = chr(len(l))
    elif len(l) < 0x10000:
        r = chr(253) + struct.pack("<H", len(l))
    elif len(l) < 0x100000000L:
        r = chr(254) + struct.pack("<I", len(l))
    else:
        r = chr(255) + struct.pack("<Q", len(l))
    for i in l:
        r += i.serialize()
    return r

def deser_uint256_vector(f):
    nit = struct.unpack("<B", f.read(1))[0]
    if nit == 253:
        nit = struct.unpack("<H", f.read(2))[0]
    elif nit == 254:
        nit = struct.unpack("<I", f.read(4))[0]
    elif nit == 255:
        nit = struct.unpack("<Q", f.read(8))[0]
    r = []
    for i in xrange(nit):
        t = deser_uint256(f)
        r.append(t)
    return r

def ser_uint256_vector(l):
    r = ""
    if len(l) < 253:
        r = chr(len(l))
    elif len(l) < 0x10000:
        r = chr(253) + struct.pack("<H", len(l))
    elif len(l) < 0x100000000L:
        r = chr(254) + struct.pack("<I", len(l))
    else:
        r = chr(255) + struct.pack("<Q", len(l))
    for i in l:
        r += ser_uint256(i)
    return r

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None
    
    return result

def b58encode(value):
    """ encode integer 'value' as a base58 string; returns string
    """
    encoded = ''
    while value >= __b58base:
        div, mod = divmod(value, __b58base)
        encoded = __b58chars[mod] + encoded # add to left
        value = div
    encoded = __b58chars[value] + encoded # most significant remainder
    return encoded

def reverse_hash(h):
    # This only revert byte order, nothing more
    if len(h) != 64:
        raise Exception('hash must have 64 hexa chars')
    
    return ''.join([ h[56-i:64-i] for i in range(0, 64, 8) ])

def doublesha(b):
    return sha256(sha256(b).digest()).digest()

def bits_to_target(bits):
    return struct.unpack('<L', bits[:3] + b'\0')[0] * 2**(8*(int(bits[3], 16) - 3))

def address_to_pubkeyhash(addr):
    try:
        addr = b58decode(addr, 25)
    except:
        return None

    if addr is None:
        return None
    
    ver = addr[0]
    cksumA = addr[-4:]
    cksumB = doublesha(addr[:-4])[:4]
    
    if cksumA != cksumB:
        return None
    
    return (ver, addr[1:-4])

def ser_uint256_be(u):
    '''ser_uint256 to big endian'''
    rs = ""
    for i in xrange(8):
        rs += struct.pack(">I", u & 0xFFFFFFFFL)
        u >>= 32
    return rs    

def deser_uint256_be(f):
    r = 0L
    for i in xrange(8):
        t = struct.unpack(">I", f.read(4))[0]
        r += t << (i * 32)
    return r

def ser_number(n):
    # For encoding nHeight into coinbase
    s = bytearray(b'\1')
    while n > 127:
        s[0] += 1
        s.append(n % 256)
        n //= 256
    s.append(n)
    return bytes(s)

#if settings.COINDAEMON_Reward == 'POW':
def script_to_address(addr):
    d = address_to_pubkeyhash(addr)
    if not d:
        raise ValueError('invalid address')
    (ver, pubkeyhash) = d
    return b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'
#else:
def script_to_pubkey(key):
    if len(key) == 66: key = binascii.unhexlify(key)
    if len(key) != 33: raise Exception('Invalid Address')
    return b'\x21' + key + b'\xac'

########NEW FILE########
__FILENAME__ = util_numpy
# /usr/bin/env python
# coding=utf-8

#  Copyright 2010 Jonathan Bowman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Various helper functions for handling arrays, etc. using numpy"""

import struct
from operator import xor, add as add64, sub as sub64
import numpy as np

words = np.uint64
bytelist = np.uint8
bigint = np.uint64

# working out some differences between Python 2 and 3
try:
    from itertools import imap, izip
except ImportError:
    imap = map
    izip = zip
try:
    xrange = xrange
except:
    xrange = range

SKEIN_KS_PARITY = np.uint64(0x1BD11BDAA9FC1A22)

# zeroed out byte string and list for convenience and performance
zero_bytes = struct.pack('64B', *[0] * 64)
zero_words = np.zeros(8, dtype=np.uint64)

# Build structs for conversion appropriate to this system, favoring
# native formats if possible for slight performance benefit
words_format_tpl = "%dQ"
if struct.pack('2B', 0, 1) == struct.pack('=H', 1): # big endian?
    words_format_tpl = "<" + words_format_tpl # force little endian
else:
    try: # is 64-bit integer native?
        struct.unpack(words_format_tpl % 2, zero_bytes[:16])
    except(struct.error): # Use standard instead of native
        words_format_tpl = "=" + words_format_tpl

# build structs for one-, two- and eight-word sequences
words_format = dict(
    (i,struct.Struct(words_format_tpl % i)) for i in (1,2,8))

def bytes2words(data, length=8):
    """Return a list of `length` 64-bit words from `data`.

    `data` must consist of `length` * 8 bytes.
    `length` must be 1, 2, or 8.

    """
    return(np.fromstring(data, dtype=np.uint64))

def words2bytes(data, length=8):
    """Return a `length` * 8 byte string from `data`.


    `data` must be a list of `length` 64-bit words
    `length` must be 1, 2, or 8.

    """
    try:
        return(data.tostring())
    except AttributeError:
        return(np.uint64(data).tostring())

def RotL_64(x, N):
    """Return `x` rotated left by `N`."""
    #return (x << np.uint64(N & 63)) | (x >> np.uint64((64-N) & 63))
    return(np.left_shift(x, (N & 63), dtype=np.uint64) |
           np.right_shift(x, ((64-N) & 63), dtype=np.uint64))

def RotR_64(x, N):
    """Return `x` rotated right by `N`."""
    return(np.right_shift(x, (N & 63), dtype=np.uint64) |
           np.left_shift(x, ((64-N) & 63), dtype=np.uint64))

def add64(a,b):
    """Return a 64-bit integer sum of `a` and `b`."""
    return(np.add(a, b, dtype=np.uint64))

def sub64(a,b):
    """Return a 64-bit integer difference of `a` and `b`."""
    return(np.subtract(a, b, dtype=np.uint64))


########NEW FILE########
__FILENAME__ = basic_share_limiter
import lib.settings as settings

import lib.logger
log = lib.logger.get_logger('BasicShareLimiter')

import DBInterface
dbi = DBInterface.DBInterface()
dbi.clear_worker_diff()

from twisted.internet import defer
from mining.interfaces import Interfaces
import time

''' This is just a customized ring buffer '''
class SpeedBuffer:
    def __init__(self, size_max):
        self.max = size_max
        self.data = []
        self.cur = 0
        
    def append(self, x):
        self.data.append(x)
        self.cur += 1
        if len(self.data) == self.max:
            self.cur = 0
            self.__class__ = SpeedBufferFull
            
    def avg(self):
        return sum(self.data) / self.cur
       
    def pos(self):
        return self.cur
           
    def clear(self):
        self.data = []
        self.cur = 0
            
    def size(self):
        return self.cur

class SpeedBufferFull:
    def __init__(self, n):
        raise "you should use SpeedBuffer"
           
    def append(self, x):                
        self.data[self.cur] = x
        self.cur = (self.cur + 1) % self.max
            
    def avg(self):
        return sum(self.data) / self.max
           
    def pos(self):
        return self.cur
           
    def clear(self):
        self.data = []
        self.cur = 0
        self.__class__ = SpeedBuffer
            
    def size(self):
        return self.max

class BasicShareLimiter(object):
    def __init__(self):
        self.worker_stats = {}
        self.target = settings.VDIFF_TARGET_TIME
        self.retarget = settings.VDIFF_RETARGET_TIME
        self.variance = self.target * (float(settings.VDIFF_VARIANCE_PERCENT) / float(100))
        self.tmin = self.target - self.variance
        self.tmax = self.target + self.variance
        self.buffersize = self.retarget / self.target * 4
        self.litecoin = {}
        self.litecoin_diff = 100000000 # TODO: Set this to VARDIFF_MAX
        # TODO: trim the hash of inactive workers

    @defer.inlineCallbacks
    def update_litecoin_difficulty(self):
        # Cache the litecoin difficulty so we do not have to query it on every submit
        # Update the difficulty  if it is out of date or not set
        if 'timestamp' not in self.litecoin or self.litecoin['timestamp'] < int(time.time()) - settings.DIFF_UPDATE_FREQUENCY:
            self.litecoin['timestamp'] = time.time()
            self.litecoin['difficulty'] = (yield Interfaces.template_registry.bitcoin_rpc.getdifficulty())
            log.debug("Updated litecoin difficulty to %s" %  (self.litecoin['difficulty']))
        self.litecoin_diff = self.litecoin['difficulty']

    def submit(self, connection_ref, job_id, current_difficulty, timestamp, worker_name):
        ts = int(timestamp)

        # Init the stats for this worker if it isn't set.        
        if worker_name not in self.worker_stats or self.worker_stats[worker_name]['last_ts'] < ts - settings.DB_USERCACHE_TIME :
            self.worker_stats[worker_name] = {'last_rtc': (ts - self.retarget / 2), 'last_ts': ts, 'buffer': SpeedBuffer(self.buffersize) }
            dbi.update_worker_diff(worker_name, settings.POOL_TARGET)
            return
        
        # Standard share update of data
        self.worker_stats[worker_name]['buffer'].append(ts - self.worker_stats[worker_name]['last_ts'])
        self.worker_stats[worker_name]['last_ts'] = ts

        # Do We retarget? If not, we're done.
        if ts - self.worker_stats[worker_name]['last_rtc'] < self.retarget and self.worker_stats[worker_name]['buffer'].size() > 0:
            return

        # Set up and log our check
        self.worker_stats[worker_name]['last_rtc'] = ts
        avg = self.worker_stats[worker_name]['buffer'].avg()
        log.debug("Checking Retarget for %s (%i) avg. %i target %i+-%i" % (worker_name, current_difficulty, avg,
                self.target, self.variance))
        
        if avg < 1:
            log.warning("Reseting avg = 1 since it's SOOO low")
            avg = 1

        # Figure out our Delta-Diff
        if settings.VDIFF_FLOAT:
            ddiff = float((float(current_difficulty) * (float(self.target) / float(avg))) - current_difficulty)
        else:
            ddiff = int((float(current_difficulty) * (float(self.target) / float(avg))) - current_difficulty)

        if avg > self.tmax:
            # For fractional -0.1 ddiff's just drop by 1
            if settings.VDIFF_X2_TYPE:
                ddiff = 0.5
                # Don't drop below POOL_TARGET
                if (ddiff * current_difficulty) < settings.VDIFF_MIN_TARGET:
                    ddiff = settings.VDIFF_MIN_TARGET / current_difficulty
            else:
                if ddiff > -settings.VDIFF_MIN_CHANGE:
                    ddiff = -settings.VDIFF_MIN_CHANGE
                # Don't drop below POOL_TARGET
                if (ddiff + current_difficulty) < settings.VDIFF_MIN_TARGET:
                    ddiff = settings.VDIFF_MIN_TARGET - current_difficulty
        elif avg < self.tmin:
            # For fractional 0.1 ddiff's just up by 1
            if settings.VDIFF_X2_TYPE:
                ddiff = 2
                # Don't go above LITECOIN or VDIFF_MAX_TARGET            
                if settings.USE_COINDAEMON_DIFF:
                    self.update_litecoin_difficulty()
                    diff_max = min([settings.VDIFF_MAX_TARGET, self.litecoin_diff])
                else:
                    diff_max = settings.VDIFF_MAX_TARGET

                if (ddiff * current_difficulty) > diff_max:
                    ddiff = diff_max / current_difficulty
            else:
                if ddiff < settings.VDIFF_MIN_CHANGE:
                   ddiff = settings.VDIFF_MIN_CHANGE
                # Don't go above LITECOIN or VDIFF_MAX_TARGET
                if settings.USE_COINDAEMON_DIFF:
                   self.update_litecoin_difficulty()
                   diff_max = min([settings.VDIFF_MAX_TARGET, self.litecoin_diff])
                else:
                   diff_max = settings.VDIFF_MAX_TARGET

                if (ddiff + current_difficulty) > diff_max:
                    ddiff = diff_max - current_difficulty
            
        else:  # If we are here, then we should not be retargeting.
            return

        # At this point we are retargeting this worker
        if settings.VDIFF_X2_TYPE:
            new_diff = current_difficulty * ddiff
        else:
            new_diff = current_difficulty + ddiff
        log.debug("Retarget for %s %i old: %i new: %i" % (worker_name, ddiff, current_difficulty, new_diff))

        self.worker_stats[worker_name]['buffer'].clear()
        session = connection_ref().get_session()

        (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _) = \
            Interfaces.template_registry.get_last_broadcast_args()
        work_id = Interfaces.worker_manager.register_work(worker_name, job_id, new_diff)
        
        session['difficulty'] = new_diff
        connection_ref().rpc('mining.set_difficulty', [new_diff, ], is_notification=True)
        log.debug("Notified of New Difficulty")
        connection_ref().rpc('mining.notify', [work_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, False, ], is_notification=True)
        log.debug("Sent new work")
        dbi.update_worker_diff(worker_name, new_diff)


########NEW FILE########
__FILENAME__ = Cache
''' A simple wrapper for pylibmc. It can be overwritten with simple hashing if necessary '''
import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('Cache')

import pylibmc
                
class Cache():
    def __init__(self):
        # Open a new connection
        self.mc = pylibmc.Client([settings.MEMCACHE_HOST + ":" + str(settings.MEMCACHE_PORT)], binary=True)
        log.info("Caching initialized")

    def set(self, key, value, time=settings.MEMCACHE_TIMEOUT):
        return self.mc.set(settings.MEMCACHE_PREFIX + str(key), value, time)

    def get(self, key):
        return self.mc.get(settings.MEMCACHE_PREFIX + str(key))

    def delete(self, key):
        return self.mc.delete(settings.MEMCACHE_PREFIX + str(key))

    def exists(self, key):
        return str(key) in self.mc.get(settings.MEMCACHE_PREFIX + str(key))

########NEW FILE########
__FILENAME__ = DBInterface
from twisted.internet import reactor, defer
import time
from datetime import datetime
import Queue
import signal
import Cache
from sets import Set

import lib.settings as settings

import lib.logger
log = lib.logger.get_logger('DBInterface')

class DBInterface():
    def __init__(self):
        self.dbi = self.connectDB()

    def init_main(self):
        self.dbi.check_tables()
 
        self.q = Queue.Queue()
        self.queueclock = None

        self.cache = Cache.Cache()

        self.nextStatsUpdate = 0

        self.scheduleImport()
        
        self.next_force_import_time = time.time() + settings.DB_LOADER_FORCE_TIME
    
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signal, frame):
        log.warning("SIGINT Detected, shutting down")
        self.do_import(self.dbi, True)
        reactor.stop()

    def set_bitcoinrpc(self, bitcoinrpc):
        self.bitcoinrpc = bitcoinrpc

    def connectDB(self):
        if settings.DATABASE_DRIVER == "sqlite":
            log.debug('DB_Sqlite INIT')
            import DB_Sqlite
            return DB_Sqlite.DB_Sqlite()
        elif settings.DATABASE_DRIVER == "mysql":
             if settings.VARIABLE_DIFF:
                log.debug("DB_Mysql_Vardiff INIT")
                import DB_Mysql_Vardiff
                return DB_Mysql_Vardiff.DB_Mysql_Vardiff()
             else:  
                log.debug('DB_Mysql INIT')
                import DB_Mysql
                return DB_Mysql.DB_Mysql()
        elif settings.DATABASE_DRIVER == "postgresql":
            log.debug('DB_Postgresql INIT')
            import DB_Postgresql
            return DB_Postgresql.DB_Postgresql()
        elif settings.DATABASE_DRIVER == "none":
            log.debug('DB_None INIT')
            import DB_None
            return DB_None.DB_None()
        else:
            log.error('Invalid DATABASE_DRIVER -- using NONE')
            log.debug('DB_None INIT')
            import DB_None
            return DB_None.DB_None()

    def scheduleImport(self):
        # This schedule's the Import
        self.queueclock = reactor.callLater(settings.DB_LOADER_CHECKTIME , self.run_import_schedule)

    def run_import_schedule(self):
        log.debug("DBInterface.run_import_schedule called")
        
        if self.q.qsize() >= settings.DB_LOADER_REC_MIN or time.time() >= self.next_force_import_time:
            self.run_import()
        
        self.scheduleImport()
    
    def run_import(self, force=False):
        log.debug("DBInterface.run_import called")
        if settings.DATABASE_DRIVER == "sqlite":
            use_thread = False
        else:
            use_thread = True
        
        if use_thread:
            reactor.callInThread(self.import_thread, force)
        else:
            self.do_import(self.dbi, force)

    def import_thread(self, force=False):
        # Here we are in the thread.
        dbi = self.connectDB()
        self.do_import(dbi, force)
        
        dbi.close()

    def _update_pool_info(self, data):
        self.dbi.update_pool_info({ 'blocks' : data['blocks'], 'balance' : data['balance'],
            'connections' : data['connections'], 'difficulty' : data['difficulty'] })

    def do_import(self, dbi, force):
        log.debug("DBInterface.do_import called. force: %s, queue size: %s", 'yes' if force == True else 'no', self.q.qsize())
        
        # Flush the whole queue on force
        forcesize = 0
        if force == True:
            forcesize = self.q.qsize()

        # Only run if we have data
        while self.q.empty() == False and (force == True or self.q.qsize() >= settings.DB_LOADER_REC_MIN or time.time() >= self.next_force_import_time or forcesize > 0):
            self.next_force_import_time = time.time() + settings.DB_LOADER_FORCE_TIME
            
            force = False
            # Put together the data we want to import
            sqldata = []
            datacnt = 0
            
            while self.q.empty() == False and datacnt < settings.DB_LOADER_REC_MAX:
                datacnt += 1
                try:
                    data = self.q.get(timeout=1)
                    sqldata.append(data)
                    self.q.task_done()
                except Queue.Empty:
                    log.warning("Share Records Queue is empty!")

            forcesize -= datacnt
                
            # try to do the import, if we fail, log the error and put the data back in the queue
            try:
                log.info("Inserting %s Share Records", datacnt)
                dbi.import_shares(sqldata)
            except Exception as e:
                log.error("Insert Share Records Failed: %s", e.args[0])
                for k, v in enumerate(sqldata):
                    self.q.put(v)
                break  # Allows us to sleep a little

    def queue_share(self, data):
        self.q.put(data)

    def found_block(self, data):
        try:
            log.info("Updating Found Block Share Record")
            self.do_import(self.dbi, True)  # We can't Update if the record is not there.
            self.dbi.found_block(data)
        except Exception as e:
            log.error("Update Found Block Share Record Failed: %s", e.args[0])

    def check_password(self, username, password):
        if username == "":
            log.info("Rejected worker for blank username")
            return False
        allowed_chars = Set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-.')
        if Set(username).issubset(allowed_chars) != True:
            log.info("Username contains bad arguments")
            return False
        if username.count('.') > 1:
            log.info("Username contains multiple . ")
            return False
        
        # Force username and password to be strings
        username = str(username)
        password = str(password)
        if not settings.USERS_CHECK_PASSWORD and self.user_exists(username): 
            return True
        elif self.cache.get(username) == password:
            return True
        elif self.dbi.check_password(username, password):
            self.cache.set(username, password)
            return True
        elif settings.USERS_AUTOADD == True:
            if self.dbi.get_uid(username) != False:
                uid = self.dbi.get_uid(username)
                self.dbi.insert_worker(uid, username, password)
                self.cache.set(username, password)
                return True
        
        log.info("Authentication for %s failed" % username)
        return False
    
    def list_users(self):
        return self.dbi.list_users()
    
    def get_user(self, id):
        if self.cache.get(id) is None:
            self.cache.set(id,self.dbi.get_user(id))
        return self.cache.get(id)
 

    def user_exists(self, username):
        if self.cache.get(username) is not None:
            return True
        user = self.get_user(username)
        return user is not None 

    def insert_user(self, username, password):        
        return self.dbi.insert_user(username, password)

    def delete_user(self, username):
        self.mc.delete(username)
        self.usercache = {}
        return self.dbi.delete_user(username)
        
    def update_user(self, username, password):
        self.mc.delete(username)
        self.mc.set(username, password)
        return self.dbi.update_user(username, password)

    def update_worker_diff(self, username, diff):
        return self.dbi.update_worker_diff(username, diff)

    def get_pool_stats(self):
        return self.dbi.get_pool_stats()
    
    def get_workers_stats(self):
        return self.dbi.get_workers_stats()
    def get_worker_diff(self,username):
     	return self.dbi.get_worker_diff(username)

    def clear_worker_diff(self):
        return self.dbi.clear_worker_diff()


########NEW FILE########
__FILENAME__ = DB_Mysql
import time
import hashlib
import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('DB_Mysql')

import MySQLdb
                
class DB_Mysql():
    def __init__(self):
        log.debug("Connecting to DB")
        
        required_settings = ['PASSWORD_SALT', 'DB_MYSQL_HOST', 
                             'DB_MYSQL_USER', 'DB_MYSQL_PASS', 
                             'DB_MYSQL_DBNAME','DB_MYSQL_PORT']
        
        for setting_name in required_settings:
            if not hasattr(settings, setting_name):
                raise ValueError("%s isn't set, please set in config.py" % setting_name)
        
        self.salt = getattr(settings, 'PASSWORD_SALT')
        self.connect()
        
    def connect(self):
        self.dbh = MySQLdb.connect(
            getattr(settings, 'DB_MYSQL_HOST'), 
            getattr(settings, 'DB_MYSQL_USER'),
            getattr(settings, 'DB_MYSQL_PASS'), 
            getattr(settings, 'DB_MYSQL_DBNAME'),
            getattr(settings, 'DB_MYSQL_PORT')
        )
        self.dbc = self.dbh.cursor()
        self.dbh.autocommit(True)
            
    def execute(self, query, args=None):
        try:
            self.dbc.execute(query, args)
        except MySQLdb.OperationalError:
            log.debug("MySQL connection lost during execute, attempting reconnect")
            self.connect()
            self.dbc = self.dbh.cursor()
            
            self.dbc.execute(query, args)
            
    def executemany(self, query, args=None):
        try:
            self.dbc.executemany(query, args)
        except MySQLdb.OperationalError:
            log.debug("MySQL connection lost during executemany, attempting reconnect")
            self.connect()
            self.dbc = self.dbh.cursor()
            
            self.dbc.executemany(query, args)
    
    def import_shares(self, data):
        # Data layout
        # 0: worker_name, 
        # 1: block_header, 
        # 2: block_hash, 
        # 3: difficulty, 
        # 4: timestamp, 
        # 5: is_valid, 
        # 6: ip, 
        # 7: self.block_height, 
        # 8: self.prev_hash,
        # 9: invalid_reason, 
        # 10: share_diff

        log.debug("Importing Shares")
        checkin_times = {}
        total_shares = 0
        best_diff = 0
        
        for k, v in enumerate(data):
            # for database compatibility we are converting our_worker to Y/N format
            if v[5]:
                v[5] = 'Y'
            else:
                v[5] = 'N'

            self.execute(
                """
                INSERT INTO `shares`
                (time, rem_host, username, our_result, 
                  upstream_result, reason, solution, difficulty)
                VALUES 
                (FROM_UNIXTIME(%(time)s), %(host)s, 
                  %(uname)s, 
                  %(lres)s, 'N', %(reason)s, %(solution)s, %(difficulty)s)
                """,
                {
                    "time": v[4], 
                    "host": v[6], 
                    "uname": v[0], 
                    "lres": v[5], 
                    "reason": v[9],
                    "solution": v[2],
                    "difficulty": v[3]
                }
            )

            self.dbh.commit()


    def found_block(self, data):
        # for database compatibility we are converting our_worker to Y/N format
        if data[5]:
            data[5] = 'Y'
        else:
            data[5] = 'N'

        # Check for the share in the database before updating it
        # Note: We can't use DUPLICATE KEY because solution is not a key

        self.execute(
            """
            Select `id` from `shares`
            WHERE `solution` = %(solution)s
            LIMIT 1
            """,
            {
                "solution": data[2]
            }
        )

        shareid = self.dbc.fetchone()

        if shareid and shareid[0] > 0:
            # Note: difficulty = -1 here
            self.execute(
                """
                UPDATE `shares`
                SET `upstream_result` = %(result)s
                WHERE `solution` = %(solution)s
                AND `id` = %(id)s
                LIMIT 1
                """,
                {
                    "result": data[5], 
                    "solution": data[2],
                    "id": shareid[0]
                }
            )
            
            self.dbh.commit()
        else:
            self.execute(
                """
                INSERT INTO `shares`
                (time, rem_host, username, our_result, 
                  upstream_result, reason, solution)
                VALUES 
                (FROM_UNIXTIME(%(time)s), %(host)s, 
                  %(uname)s, 
                  %(lres)s, %(result)s, %(reason)s, %(solution)s)
                """,
                {
                    "time": data[4],
                    "host": data[6],
                    "uname": data[0],
                    "lres": data[5],
                    "result": data[5],
                    "reason": data[9],
                    "solution": data[2]
                }
            )

            self.dbh.commit()

        
    def list_users(self):
        self.execute(
            """
            SELECT *
            FROM `pool_worker`
            WHERE `id`> 0
            """
        )
        
        while True:
            results = self.dbc.fetchmany()
            if not results:
                break
            
            for result in results:
                yield result
                
                
    def get_user(self, id_or_username):
        log.debug("Finding user with id or username of %s", id_or_username)
        
        self.execute(
            """
            SELECT *
            FROM `pool_worker`
            WHERE `id` = %(id)s
              OR `username` = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        user = self.dbc.fetchone()
        return user

    def get_uid(self, id_or_username):
        log.debug("Finding user id of %s", id_or_username)
        uname = id_or_username.split(".", 1)[0]
        self.execute("SELECT id FROM accounts where username = %s", (uname,))
        row = self.dbc.fetchone()

        if row is None:
            return False
        else:
            uid = row[0]
            return uid

    def insert_worker(self, account_id, username, password):
        log.debug("Adding new worker %s", username)
        query = "INSERT INTO pool_worker"
        self.execute(query + '(account_id, username, password) VALUES (%s, %s, %s);', (account_id, username, password))
        self.dbh.commit()
        return str(username)
        

    def delete_user(self, id_or_username):
        if id_or_username.isdigit() and id_or_username == '0':
            raise Exception('You cannot delete that user')
        
        log.debug("Deleting user with id or username of %s", id_or_username)
        
        self.execute(
            """
            UPDATE `shares`
            SET `username` = 0
            WHERE `username` = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        self.execute(
            """
            DELETE FROM `pool_worker`
            WHERE `id` = %(id)s
              OR `username` = %(uname)s
            """, 
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        self.dbh.commit()

    def insert_user(self, username, password):
        log.debug("Adding new user %s", username)
        
        self.execute(
            """
            INSERT INTO `pool_worker`
            (`username`, `password`)
            VALUES
            (%(uname)s, %(pass)s)
            """,
            {
                "uname": username, 
                "pass": password
            }
        )
        
        self.dbh.commit()
        
        return str(username)

    def update_user(self, id_or_username, password):
        log.debug("Updating password for user %s", id_or_username);
        
        self.execute(
            """
            UPDATE `pool_worker`
            SET `password` = %(pass)s
            WHERE `id` = %(id)s
              OR `username` = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username,
                "pass": password
            }
        )
        
        self.dbh.commit()

    def check_password(self, username, password):
        log.debug("Checking username/password for %s", username)
        
        self.execute(
            """
            SELECT COUNT(*) 
            FROM `pool_worker`
            WHERE `username` = %(uname)s
              AND `password` = %(pass)s
            """,
            {
                "uname": username, 
                "pass": password
            }
        )
        
        data = self.dbc.fetchone()
        if data[0] > 0:
            return True
        
        return False

    def get_workers_stats(self):
        self.execute(
            """
            SELECT `username`, `speed`, `last_checkin`, `total_shares`,
              `total_rejects`, `total_found`, `alive`
            FROM `pool_worker`
            WHERE `id` > 0
            """
        )
        
        ret = {}
        
        for data in self.dbc.fetchall():
            ret[data[0]] = {
                "username": data[0],
                "speed": int(data[1]),
                "last_checkin": time.mktime(data[2].timetuple()),
                "total_shares": int(data[3]),
                "total_rejects": int(data[4]),
                "total_found": int(data[5]),
                "alive": True if data[6] is 1 else False,
            }
            
        return ret

    def insert_worker(self, account_id, username, password):
        log.debug("Adding new worker %s", username)
        query = "INSERT INTO pool_worker"
        self.execute(query + '(account_id, username, password) VALUES (%s, %s, %s);', (account_id, username, password))
        self.dbh.commit()
        return str(username)

    def close(self):
        self.dbh.close()
        
    def get_worker_diff(self,username):
        self.dbc.execute("select difficulty from pool_worker where username = %s",(username))
        data = self.dbc.fetchone()
        if data[0] > 0 :
           return data[0]
        return settings.POOL_TARGET

    def set_worker_diff(self,username, difficulty):
        self.execute("UPDATE `pool_worker` SET `difficulty` = %s WHERE `username` = %s",(difficulty,username))
        self.dbh.commit()

    def check_tables(self):
        log.debug("Checking Database")
        
        self.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE `table_schema` = %(schema)s
              AND `table_name` = 'shares'
            """,
            {
                "schema": getattr(settings, 'DB_MYSQL_DBNAME')
            }
        )
        
        data = self.dbc.fetchone()
        
        if data[0] <= 0:
           raise Exception("There is no shares table. Have you imported the schema?")
 


########NEW FILE########
__FILENAME__ = DB_Mysql_Extended
import time
import hashlib
import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('DB_Mysql')

import MySQLdb
import DB_Mysql
                
class DB_Mysql_Extended(DB_Mysql.DB_Mysql):
    def __init__(self):
        DB_Mysql.DB_Mysql.__init__(self)

    def updateStats(self, averageOverTime):
        log.debug("Updating Stats")
        # Note: we are using transactions... so we can set the speed = 0 and it doesn't take affect until we are commited.
        self.execute(
            """
            UPDATE `pool_worker`
            SET `speed` = 0, 
              `alive` = 0
            """
        );
        
        stime = '%.0f' % (time.time() - averageOverTime);
        
        self.execute(
            """
            UPDATE `pool_worker` pw
            LEFT JOIN (
                SELECT `worker`, ROUND(ROUND(SUM(`difficulty`)) * 4294967296) / %(average)s AS 'speed'
                FROM `shares`
                WHERE `time` > FROM_UNIXTIME(%(time)s)
                GROUP BY `worker`
            ) AS leJoin
            ON leJoin.`worker` = pw.`id`
            SET pw.`alive` = 1, 
              pw.`speed` = leJoin.`speed`
            WHERE pw.`id` = leJoin.`worker`
            """,
            {
                "time": stime,
                "average": int(averageOverTime) * 1000000
            }
        )
            
        self.execute(
            """
            UPDATE `pool`
            SET `value` = (
                SELECT IFNULL(SUM(`speed`), 0)
                FROM `pool_worker`
                WHERE `alive` = 1
            )
            WHERE `parameter` = 'pool_speed'
            """
        )
        
        self.dbh.commit()
    
    def archive_check(self):
        # Check for found shares to archive
        self.execute(
            """
            SELECT `time`
            FROM `shares` 
            WHERE `upstream_result` = 1
            ORDER BY `time` 
            LIMIT 1
            """
        )
        
        data = self.dbc.fetchone()
        
        if data is None or (data[0] + getattr(settings, 'ARCHIVE_DELAY')) > time.time():
            return False
        
        return data[0]

    def archive_found(self, found_time):
        self.execute(
            """
            INSERT INTO `shares_archive_found`
            SELECT s.`id`, s.`time`, s.`rem_host`, pw.`id`, s.`our_result`, 
              s.`upstream_result`, s.`reason`, s.`solution`, s.`block_num`, 
              s.`prev_block_hash`, s.`useragent`, s.`difficulty`
            FROM `shares` s 
            LEFT JOIN `pool_worker` pw
              ON s.`worker` = pw.`id`
            WHERE `upstream_result` = 1
              AND `time` <= FROM_UNIXTIME(%(time)s)
            """,
            {
                "time": found_time
            }
        )
        
        self.dbh.commit()

    def archive_to_db(self, found_time):
        self.execute(
            """
            INSERT INTO `shares_archive`
            SELECT s.`id`, s.`time`, s.`rem_host`, pw.`id`, s.`our_result`, 
              s.`upstream_result`, s.`reason`, s.`solution`, s.`block_num`, 
              s.`prev_block_hash`, s.`useragent`, s.`difficulty`
            FROM `shares` s 
            LEFT JOIN `pool_worker` pw
              ON s.`worker` = pw.`id`
            WHERE `time` <= FROM_UNIXTIME(%(time)s)
            """,
            {
                "time": found_time
            }
        )
        
        self.dbh.commit()

    def archive_cleanup(self, found_time):
        self.execute(
            """
            DELETE FROM `shares` 
            WHERE `time` <= FROM_UNIXTIME(%(time)s)
            """,
            {
                "time": found_time
            }
        )
        
        self.dbh.commit()

    def archive_get_shares(self, found_time):
        self.execute(
            """
            SELECT *
            FROM `shares` 
            WHERE `time` <= FROM_UNIXTIME(%(time)s)
            """,
            {
                "time": found_time
            }
        )
        
        return self.dbc

    def import_shares(self, data):
        # Data layout
        # 0: worker_name, 
        # 1: block_header, 
        # 2: block_hash, 
        # 3: difficulty, 
        # 4: timestamp, 
        # 5: is_valid, 
        # 6: ip, 
        # 7: self.block_height, 
        # 8: self.prev_hash,
        # 9: invalid_reason, 
        # 10: share_diff

        log.debug("Importing Shares")
        checkin_times = {}
        total_shares = 0
        best_diff = 0
        
        for k, v in enumerate(data):
            total_shares += v[3]
            
            if v[0] in checkin_times:
                if v[4] > checkin_times[v[0]]:
                    checkin_times[v[0]]["time"] = v[4]
            else:
                checkin_times[v[0]] = {
                    "time": v[4], 
                    "shares": 0, 
                    "rejects": 0
                }

            if v[5] == True:
                checkin_times[v[0]]["shares"] += v[3]
            else:
                checkin_times[v[0]]["rejects"] += v[3]

            if v[10] > best_diff:
                best_diff = v[10]

            self.execute(
                """
                INSERT INTO `shares` 
                (time, rem_host, worker, our_result, upstream_result, 
                  reason, solution, block_num, prev_block_hash, 
                  useragent, difficulty) 
                VALUES
                (FROM_UNIXTIME(%(time)s), %(host)s, 
                  (SELECT `id` FROM `pool_worker` WHERE `username` = %(uname)s),
                  %(lres)s, 0, %(reason)s, %(solution)s, 
                  %(blocknum)s, %(hash)s, '', %(difficulty)s)
                """,
                {
                    "time": v[4],
                    "host": v[6],
                    "uname": v[0],
                    "lres": v[5],
                    "reason": v[9],
                    "solution": v[2],
                    "blocknum": v[7],
                    "hash": v[8],
                    "difficulty": v[3]
                }
            )

        self.execute(
            """
            SELECT `parameter`, `value` 
            FROM `pool` 
            WHERE `parameter` = 'round_best_share'
              OR `parameter` = 'round_shares'
              OR `parameter` = 'bitcoin_difficulty'
              OR `parameter` = 'round_progress'
            """
        )
            
        current_parameters = {}
        
        for data in self.dbc.fetchall():
            current_parameters[data[0]] = data[1]
        
        round_best_share = int(current_parameters['round_best_share'])
        difficulty = float(current_parameters['bitcoin_difficulty'])
        round_shares = int(current_parameters['round_shares']) + total_shares
            
        updates = [
            {
                "param": "round_shares",
                "value": round_shares
            },
            {
                "param": "round_progress",
                "value": 0 if difficulty == 0 else (round_shares / difficulty) * 100
            }
        ]
            
        if best_diff > round_best_share:
            updates.append({
                "param": "round_best_share",
                "value": best_diff
            })
        
        self.executemany(
            """
            UPDATE `pool` 
            SET `value` = %(value)s
            WHERE `parameter` = %(param)s
            """,
            updates
        )
    
        for k, v in checkin_times.items():
            self.execute(
                """
                UPDATE `pool_worker`
                SET `last_checkin` = FROM_UNIXTIME(%(time)s), 
                  `total_shares` = `total_shares` + %(shares)s,
                  `total_rejects` = `total_rejects` + %(rejects)s
                WHERE `username` = %(uname)s
                """,
                {
                    "time": v["time"],
                    "shares": v["shares"],
                    "rejects": v["rejects"], 
                    "uname": k
                }
            )
        
        self.dbh.commit()


    def found_block(self, data):
        # for database compatibility we are converting our_worker to Y/N format
        #if data[5]:
        #    data[5] = 'Y'
        #else:
        #    data[5] = 'N'
        # Note: difficulty = -1 here
        self.execute(
            """
            UPDATE `shares`
            SET `upstream_result` = %(result)s,
              `solution` = %(solution)s
            WHERE `time` = FROM_UNIXTIME(%(time)s)
              AND `worker` =  (SELECT id 
                FROM `pool_worker` 
                WHERE `username` = %(uname)s)
            LIMIT 1
            """,
            {
                "result": data[5], 
                "solution": data[2], 
                "time": data[4], 
                "uname": data[0]
            }
        )
        
        if data[5] == True:
            self.execute(
                """
                UPDATE `pool_worker`
                SET `total_found` = `total_found` + 1
                WHERE `username` = %(uname)s
                """,
                {
                    "uname": data[0]
                }
            )
            self.execute(
                """
                SELECT `value`
                FROM `pool`
                WHERE `parameter` = 'pool_total_found'
                """
            )
            total_found = int(self.dbc.fetchone()[0]) + 1
            
            self.executemany(
                """
                UPDATE `pool`
                SET `value` = %(value)s
                WHERE `parameter` = %(param)s
                """,
                [
                    {
                        "param": "round_shares",
                        "value": "0"
                    },
                    {
                        "param": "round_progress",
                        "value": "0"
                    },
                    {
                        "param": "round_best_share",
                        "value": "0"
                    },
                    {
                        "param": "round_start",
                        "value": time.time()
                    },
                    {
                        "param": "pool_total_found",
                        "value": total_found
                    }
                ]
            )
            
        self.dbh.commit()
        
    def update_pool_info(self, pi):
        self.executemany(
            """
            UPDATE `pool`
            SET `value` = %(value)s
            WHERE `parameter` = %(param)s
            """,
            [
                {
                    "param": "bitcoin_blocks",
                    "value": pi['blocks']
                },
                {
                    "param": "bitcoin_balance",
                    "value": pi['balance']
                },
                {
                    "param": "bitcoin_connections",
                    "value": pi['connections']
                },
                {
                    "param": "bitcoin_difficulty",
                    "value": pi['difficulty']
                },
                {
                    "param": "bitcoin_infotime",
                    "value": time.time()
                }
            ]
        )
        
        self.dbh.commit()

    def get_pool_stats(self):
        self.execute(
            """
            SELECT * FROM `pool`
            """
        )
        
        ret = {}
        
        for data in self.dbc.fetchall():
            ret[data[0]] = data[1]
            
        return ret

    def get_workers_stats(self):
        self.execute(
            """
            SELECT `username`, `speed`, `last_checkin`, `total_shares`,
              `total_rejects`, `total_found`, `alive`, `difficulty`
            FROM `pool_worker`
            WHERE `id` > 0
            """
        )
        
        ret = {}
        
        for data in self.dbc.fetchall():
            ret[data[0]] = {
                "username": data[0],
                "speed": int(data[1]),
                "last_checkin": time.mktime(data[2].timetuple()),
                "total_shares": int(data[3]),
                "total_rejects": int(data[4]),
                "total_found": int(data[5]),
                "alive": True if data[6] is 1 else False,
                "difficulty": int(data[7])
            }
            
        return ret

########NEW FILE########
__FILENAME__ = DB_Mysql_Vardiff
import time
import hashlib
import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('DB_Mysql')

import MySQLdb
import DB_Mysql
                
class DB_Mysql_Vardiff(DB_Mysql.DB_Mysql):
    def __init__(self):
        DB_Mysql.DB_Mysql.__init__(self)
    
    def import_shares(self, data):
        # Data layout
        # 0: worker_name, 
        # 1: block_header, 
        # 2: block_hash, 
        # 3: difficulty, 
        # 4: timestamp, 
        # 5: is_valid, 
        # 6: ip, 
        # 7: self.block_height, 
        # 8: self.prev_hash,
        # 9: invalid_reason, 
        # 10: share_diff

        log.debug("Importing Shares")
        checkin_times = {}
        total_shares = 0
        best_diff = 0
        
        for k, v in enumerate(data):
            # for database compatibility we are converting our_worker to Y/N format
            if v[5]:
                v[5] = 'Y'
            else:
                v[5] = 'N'

            self.execute(
                """
                INSERT INTO `shares`
                (time, rem_host, username, our_result, 
                  upstream_result, reason, solution, difficulty)
                VALUES 
                (FROM_UNIXTIME(%(time)s), %(host)s, 
                  %(uname)s, 
                  %(lres)s, 'N', %(reason)s, %(solution)s, %(difficulty)s)
                """,
                {
                    "time": v[4], 
                    "host": v[6], 
                    "uname": v[0], 
                    "lres": v[5], 
                    "reason": v[9],
                    "solution": v[2],
                    "difficulty": v[3]
                }
            )

            self.dbh.commit()
    
    def found_block(self, data):
        # for database compatibility we are converting our_worker to Y/N format
        if data[5]:
            data[5] = 'Y'
        else:
            data[5] = 'N'

        # Check for the share in the database before updating it
        # Note: We can't use DUPLICATE KEY because solution is not a key

        self.execute(
            """
            Select `id` from `shares`
            WHERE `solution` = %(solution)s
            LIMIT 1
            """,
            {
                "solution": data[2]
            }
        )

        shareid = self.dbc.fetchone()

        if shareid and shareid[0] > 0:
            # Note: difficulty = -1 here
            self.execute(
                """
                UPDATE `shares`
                SET `upstream_result` = %(result)s
                WHERE `solution` = %(solution)s
                AND `id` = %(id)s
                LIMIT 1
                """,
                {
                    "result": data[5], 
                    "solution": data[2],
                    "id": shareid[0]
                }
            )
            
            self.dbh.commit()
        else:
            self.execute(
                """
                INSERT INTO `shares`
                (time, rem_host, username, our_result, 
                  upstream_result, reason, solution)
                VALUES 
                (FROM_UNIXTIME(%(time)s), %(host)s, 
                  %(uname)s, 
                  %(lres)s, %(result)s, %(reason)s, %(solution)s)
                """,
                {
                    "time": data[4],
                    "host": data[6],
                    "uname": data[0],
                    "lres": data[5],
                    "result": data[5],
                    "reason": data[9],
                    "solution": data[2]
                }
            )
            self.dbh.commit()


    def update_worker_diff(self, username, diff):
        log.debug("Setting difficulty for %s to %s", username, diff)
        
        self.execute(
            """
            UPDATE `pool_worker`
            SET `difficulty` = %(diff)s
            WHERE `username` = %(uname)s
            """,
            {
                "uname": username, 
                "diff": diff
            }
        )
        
        self.dbh.commit()
    
    def clear_worker_diff(self):
        log.debug("Resetting difficulty for all workers")
        
        self.execute(
            """
            UPDATE `pool_worker`
            SET `difficulty` = 0
            """
        )
        
        self.dbh.commit()


    def get_workers_stats(self):
        self.execute(
            """
            SELECT `username`, `speed`, `last_checkin`, `total_shares`,
              `total_rejects`, `total_found`, `alive`, `difficulty`
            FROM `pool_worker`
            WHERE `id` > 0
            """
        )
        
        ret = {}
        
        for data in self.dbc.fetchall():
            ret[data[0]] = {
                "username": data[0],
                "speed": int(data[1]),
                "last_checkin": time.mktime(data[2].timetuple()),
                "total_shares": int(data[3]),
                "total_rejects": int(data[4]),
                "total_found": int(data[5]),
                "alive": True if data[6] is 1 else False,
                "difficulty": float(data[7])
            }
            
        return ret



########NEW FILE########
__FILENAME__ = DB_None
import stratum.logger
log = stratum.logger.get_logger('None')
                
class DB_None():
    def __init__(self):
        log.debug("Connecting to DB")

    def updateStats(self,averageOverTime):
        log.debug("Updating Stats")

    def import_shares(self,data):
        log.debug("Importing Shares")

    def found_block(self,data):
        log.debug("Found Block")
    
    def get_user(self, id_or_username):
        log.debug("Get User")

    def list_users(self):
        log.debug("List Users")

    def delete_user(self,username):
        log.debug("Deleting Username")

    def insert_user(self,username,password):
        log.debug("Adding Username/Password")

    def update_user(self,username,password):
        log.debug("Updating Username/Password")

    def check_password(self,username,password):
        log.debug("Checking Username/Password")
        return True
    
    def update_pool_info(self,pi):
        log.debug("Update Pool Info")

    def clear_worker_diff(self):
        log.debug("Clear Worker Diff")

    def get_pool_stats(self):
        log.debug("Get Pool Stats")
        ret = {}
        return ret

    def get_workers_stats(self):
        log.debug("Get Workers Stats")
        ret = {}
        return ret

    def check_tables(self):
        log.debug("Checking Tables")

    def close(self):
        log.debug("Close Connection")

########NEW FILE########
__FILENAME__ = DB_Postgresql
import time
import hashlib
from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('DB_Postgresql')

import psycopg2
from psycopg2 import extras
                
class DB_Postgresql():
    def __init__(self):
        log.debug("Connecting to DB")
        self.dbh = psycopg2.connect("host='"+settings.DB_PGSQL_HOST+"' dbname='"+settings.DB_PGSQL_DBNAME+"' user='"+settings.DB_PGSQL_USER+\
                "' password='"+settings.DB_PGSQL_PASS+"'")
        # TODO -- set the schema
        self.dbc = self.dbh.cursor()
        
        if hasattr(settings, 'PASSWORD_SALT'):
            self.salt = settings.PASSWORD_SALT
        else:
            raise ValueError("PASSWORD_SALT isn't set, please set in config.py")

    def updateStats(self,averageOverTime):
        log.debug("Updating Stats")
        # Note: we are using transactions... so we can set the speed = 0 and it doesn't take affect until we are commited.
        self.dbc.execute("update pool_worker set speed = 0, alive = 'f'");
        stime = '%.2f' % ( time.time() - averageOverTime );
        self.dbc.execute("select username,SUM(difficulty) from shares where time > to_timestamp(%s) group by username", [stime])
        total_speed = 0
        for name,shares in self.dbc.fetchall():
            speed = int(int(shares) * pow(2,32)) / ( int(averageOverTime) * 1000 * 1000)
            total_speed += speed
            self.dbc.execute("update pool_worker set speed = %s, alive = 't' where username = %s", (speed,name))
        self.dbc.execute("update pool set value = %s where parameter = 'pool_speed'",[total_speed])
        self.dbh.commit()
    
    def archive_check(self):
        # Check for found shares to archive
        self.dbc.execute("select time from shares where upstream_result = true order by time limit 1")
        data = self.dbc.fetchone()
        if data is None or (data[0] + settings.ARCHIVE_DELAY) > time.time() :
            return False
        return data[0]

    def archive_found(self,found_time):
        self.dbc.execute("insert into shares_archive_found select * from shares where upstream_result = true and time <= to_timestamp(%s)", [found_time])
        self.dbh.commit()

    def archive_to_db(self,found_time):
        self.dbc.execute("insert into shares_archive select * from shares where time <= to_timestamp(%s)",[found_time])        
        self.dbh.commit()

    def archive_cleanup(self,found_time):
        self.dbc.execute("delete from shares where time <= to_timestamp(%s)",[found_time])
        self.dbh.commit()

    def archive_get_shares(self,found_time):
        self.dbc.execute("select * from shares where time <= to_timestamp(%s)",[found_time])
        return self.dbc

    def import_shares(self,data):
        log.debug("Importing Shares")
#               0           1            2          3          4         5        6  7            8         9              10
#        data: [worker_name,block_header,block_hash,difficulty,timestamp,is_valid,ip,block_height,prev_hash,invalid_reason,best_diff]
        checkin_times = {}
        total_shares = 0
        best_diff = 0
        for k,v in enumerate(data):
            if settings.DATABASE_EXTEND :
                total_shares += v[3]
                if v[0] in checkin_times:
                    if v[4] > checkin_times[v[0]] :
                        checkin_times[v[0]]["time"] = v[4]
                else:
                    checkin_times[v[0]] = {"time": v[4], "shares": 0, "rejects": 0 }

                if v[5] == True :
                    checkin_times[v[0]]["shares"] += v[3]
                else :
                    checkin_times[v[0]]["rejects"] += v[3]

                if v[10] > best_diff:
                    best_diff = v[10]

                self.dbc.execute("insert into shares " +\
                        "(time,rem_host,username,our_result,upstream_result,reason,solution,block_num,prev_block_hash,useragent,difficulty) " +\
                        "VALUES (to_timestamp(%s),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (v[4],v[6],v[0],bool(v[5]),False,v[9],'',v[7],v[8],'',v[3]) )
            else :
                self.dbc.execute("insert into shares (time,rem_host,username,our_result,upstream_result,reason,solution) VALUES " +\
                        "(to_timestamp(%s),%s,%s,%s,%s,%s,%s)",
                        (v[4],v[6],v[0],bool(v[5]),False,v[9],'') )

        if settings.DATABASE_EXTEND :
            self.dbc.execute("select value from pool where parameter = 'round_shares'")
            round_shares = int(self.dbc.fetchone()[0]) + total_shares
            self.dbc.execute("update pool set value = %s where parameter = 'round_shares'",[round_shares])

            self.dbc.execute("select value from pool where parameter = 'round_best_share'")
            round_best_share = int(self.dbc.fetchone()[0])
            if best_diff > round_best_share:
                self.dbc.execute("update pool set value = %s where parameter = 'round_best_share'",[best_diff])

            self.dbc.execute("select value from pool where parameter = 'bitcoin_difficulty'")
            difficulty = float(self.dbc.fetchone()[0])

            if difficulty == 0:
                progress = 0
            else:
                    progress = (round_shares/difficulty)*100
            self.dbc.execute("update pool set value = %s where parameter = 'round_progress'",[progress])
        
            for k,v in checkin_times.items():
                self.dbc.execute("update pool_worker set last_checkin = to_timestamp(%s), total_shares = total_shares + %s, total_rejects = total_rejects + %s where username = %s",
                        (v["time"],v["shares"],v["rejects"],k))

        self.dbh.commit()


    def found_block(self,data):
        # Note: difficulty = -1 here
        self.dbc.execute("update shares set upstream_result = %s, solution = %s where id in (select id from shares where time = to_timestamp(%s) and username = %s limit 1)",
                (bool(data[5]),data[2],data[4],data[0]))
        if settings.DATABASE_EXTEND and data[5] == True :
            self.dbc.execute("update pool_worker set total_found = total_found + 1 where username = %s",(data[0],))
            self.dbc.execute("select value from pool where parameter = 'pool_total_found'")
            total_found = int(self.dbc.fetchone()[0]) + 1
            self.dbc.executemany("update pool set value = %s where parameter = %s",[(0,'round_shares'),
                (0,'round_progress'),
                (0,'round_best_share'),
                (time.time(),'round_start'),
                (total_found,'pool_total_found')
                ])
        self.dbh.commit()
                
    def get_user(self, id_or_username):
        log.debug("Finding user with id or username of %s", id_or_username)
        cursor = self.dbh.cursor(cursor_factory=extras.DictCursor)
        
        cursor.execute(
            """
            SELECT *
            FROM pool_worker
            WHERE id = %(id)s
              OR username = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        user = cursor.fetchone()
        cursor.close()
        return user
        
    def list_users(self):
        cursor = self.dbh.cursor(cursor_factory=extras.DictCursor)
        cursor.execute(
            """
            SELECT *
            FROM pool_worker
            WHERE id > 0
            """
        )
        
        while True:
            results = cursor.fetchmany()
            if not results:
                break
            
            for result in results:
                yield result

    def delete_user(self, id_or_username):
        log.debug("Deleting Username")
        self.dbc.execute(
            """
            delete from pool_worker where id = %(id)s or username = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        self.dbh.commit()

    def insert_user(self,username,password):
        log.debug("Adding Username/Password")
        m = hashlib.sha1()
        m.update(password)
        m.update(self.salt)
        self.dbc.execute("insert into pool_worker (username,password) VALUES (%s,%s)",
                (username, m.hexdigest() ))
        self.dbh.commit()
        
        return str(username)

    def update_user(self, id_or_username, password):
        log.debug("Updating Username/Password")
        m = hashlib.sha1()
        m.update(password)
        m.update(self.salt)
        self.dbc.execute(
            """
            update pool_worker set password = %(pass)s where id = %(id)s or username = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username,
                "pass": m.hexdigest()
            }
        )
        self.dbh.commit()

    def update_worker_diff(self,username,diff):
        self.dbc.execute("update pool_worker set difficulty = %s where username = %s",(diff,username))
        self.dbh.commit()
    
    def clear_worker_diff(self):
        if settings.DATABASE_EXTEND == True :
            self.dbc.execute("update pool_worker set difficulty = 0")
            self.dbh.commit()

    def check_password(self,username,password):
        log.debug("Checking Username/Password")
        m = hashlib.sha1()
        m.update(password)
        m.update(self.salt)
        self.dbc.execute("select COUNT(*) from pool_worker where username = %s and password = %s",
                (username, m.hexdigest() ))
        data = self.dbc.fetchone()
        if data[0] > 0 :
            return True
        return False

    def update_pool_info(self,pi):
        self.dbc.executemany("update pool set value = %s where parameter = %s",[(pi['blocks'],"bitcoin_blocks"),
                (pi['balance'],"bitcoin_balance"),
                (pi['connections'],"bitcoin_connections"),
                (pi['difficulty'],"bitcoin_difficulty"),
                (time.time(),"bitcoin_infotime")
                ])
        self.dbh.commit()

    def get_pool_stats(self):
        self.dbc.execute("select * from pool")
        ret = {}
        for data in self.dbc.fetchall():
            ret[data[0]] = data[1]
        return ret

    def get_workers_stats(self):
        self.dbc.execute("select username,speed,last_checkin,total_shares,total_rejects,total_found,alive,difficulty from pool_worker")
        ret = {}
        for data in self.dbc.fetchall():
            ret[data[0]] = { "username" : data[0],
                "speed" : data[1],
                "last_checkin" : time.mktime(data[2].timetuple()),
                "total_shares" : data[3],
                "total_rejects" : data[4],
                "total_found" : data[5],
                "alive" : data[6],
                "difficulty" : data[7] }
        return ret

    def close(self):
        self.dbh.close()

    def check_tables(self):
        log.debug("Checking Tables")

        shares_exist = False
        self.dbc.execute("select COUNT(*) from pg_catalog.pg_tables where schemaname = %(schema)s and tablename = 'shares'",
                {"schema": settings.DB_PGSQL_SCHEMA })
        data = self.dbc.fetchone()
        if data[0] <= 0 :
            self.update_version_1()
        
        if settings.DATABASE_EXTEND == True :
            self.update_tables()

        
    def update_tables(self):
        version = 0
        current_version = 7
        while version < current_version :
            self.dbc.execute("select value from pool where parameter = 'DB Version'")
            data = self.dbc.fetchone()
            version = int(data[0])
            if version < current_version :
                log.info("Updating Database from %i to %i" % (version, version +1))
                getattr(self, 'update_version_' + str(version) )()
                    
    def update_version_1(self):
        if settings.DATABASE_EXTEND == True :
            self.dbc.execute("create table shares" +\
                "(id serial primary key,time timestamp,rem_host TEXT, username TEXT, our_result BOOLEAN, upstream_result BOOLEAN, reason TEXT, solution TEXT, " +\
                "block_num INTEGER, prev_block_hash TEXT, useragent TEXT, difficulty INTEGER)")
            self.dbc.execute("create index shares_username ON shares(username)")
            self.dbc.execute("create table pool_worker" +\
                        "(id serial primary key,username TEXT, password TEXT, speed INTEGER, last_checkin timestamp)")
            self.dbc.execute("create index pool_worker_username ON pool_worker(username)")
            self.dbc.execute("alter table pool_worker add total_shares INTEGER default 0")
            self.dbc.execute("alter table pool_worker add total_rejects INTEGER default 0")
            self.dbc.execute("alter table pool_worker add total_found INTEGER default 0")
            self.dbc.execute("create table pool(parameter TEXT, value TEXT)")
            self.dbc.execute("insert into pool (parameter,value) VALUES ('DB Version',2)")
        else :
            self.dbc.execute("create table shares" + \
                "(id serial,time timestamp,rem_host TEXT, username TEXT, our_result BOOLEAN, upstream_result BOOLEAN, reason TEXT, solution TEXT)")
            self.dbc.execute("create index shares_username ON shares(username)")
            self.dbc.execute("create table pool_worker(id serial,username TEXT, password TEXT)")
            self.dbc.execute("create index pool_worker_username ON pool_worker(username)")
        self.dbh.commit()

    def update_version_2(self):
        log.info("running update 2")
        self.dbc.executemany("insert into pool (parameter,value) VALUES (%s,%s)",[('bitcoin_blocks',0),
                ('bitcoin_balance',0),
                ('bitcoin_connections',0),
                ('bitcoin_difficulty',0),
                ('pool_speed',0),
                ('pool_total_found',0),
                ('round_shares',0),
                ('round_progress',0),
                ('round_start',time.time())
                ])
        self.dbc.execute("update pool set value = 3 where parameter = 'DB Version'")
        self.dbh.commit()
        
    def update_version_3(self):
        log.info("running update 3")
        self.dbc.executemany("insert into pool (parameter,value) VALUES (%s,%s)",[
                ('round_best_share',0),
                ('bitcoin_infotime',0)
                ])
        self.dbc.execute("alter table pool_worker add alive BOOLEAN")
        self.dbc.execute("update pool set value = 4 where parameter = 'DB Version'")
        self.dbh.commit()
        
    def update_version_4(self):
        log.info("running update 4")
        self.dbc.execute("alter table pool_worker add difficulty INTEGER default 0")
        self.dbc.execute("create table shares_archive" +\
                "(id serial primary key,time timestamp,rem_host TEXT, username TEXT, our_result BOOLEAN, upstream_result BOOLEAN, reason TEXT, solution TEXT, " +\
                "block_num INTEGER, prev_block_hash TEXT, useragent TEXT, difficulty INTEGER)")
        self.dbc.execute("create table shares_archive_found" +\
                "(id serial primary key,time timestamp,rem_host TEXT, username TEXT, our_result BOOLEAN, upstream_result BOOLEAN, reason TEXT, solution TEXT, " +\
                "block_num INTEGER, prev_block_hash TEXT, useragent TEXT, difficulty INTEGER)")
        self.dbc.execute("update pool set value = 5 where parameter = 'DB Version'")
        self.dbh.commit()
        
    def update_version_5(self):
        log.info("running update 5")
        # Adding Primary key to table: pool
        self.dbc.execute("alter table pool add primary key (parameter)")
        self.dbh.commit()
        # Adjusting indicies on table: shares
        self.dbc.execute("DROP INDEX shares_username")
        self.dbc.execute("CREATE INDEX shares_time_username ON shares(time,username)")
        self.dbc.execute("CREATE INDEX shares_upstreamresult ON shares(upstream_result)")
        self.dbh.commit()
        
        self.dbc.execute("update pool set value = 6 where parameter = 'DB Version'")
        self.dbh.commit()
        
    def update_version_6(self):
        log.info("running update 6")
        
        try:
            self.dbc.execute("CREATE EXTENSION pgcrypto")
        except psycopg2.ProgrammingError:
            log.info("pgcrypto already added to database")
        except psycopg2.OperationalError:
            raise Exception("Could not add pgcrypto extension to database. Have you got it installed? Ubuntu is postgresql-contrib")
        self.dbh.commit()
        
        # Optimising table layout
        self.dbc.execute("ALTER TABLE pool " +\
            "ALTER COLUMN parameter TYPE character varying(128), ALTER COLUMN value TYPE character varying(512);")
        self.dbh.commit()
        
        self.dbc.execute("UPDATE pool_worker SET password = encode(digest(concat(password, %s), 'sha1'), 'hex') WHERE id > 0", [self.salt])
        self.dbh.commit()
        
        self.dbc.execute("ALTER TABLE pool_worker " +\
            "ALTER COLUMN username TYPE character varying(512), ALTER COLUMN password TYPE character(40), " +\
            "ADD CONSTRAINT username UNIQUE (username)")
        self.dbh.commit()
        
        self.dbc.execute("update pool set value = 7 where parameter = 'DB Version'")
        self.dbh.commit()


########NEW FILE########
__FILENAME__ = DB_Sqlite
import time
from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('DB_Sqlite')

import sqlite3
               
class DB_Sqlite():
    def __init__(self):
        log.debug("Connecting to DB")
        self.dbh = sqlite3.connect(settings.DB_SQLITE_FILE)
        self.dbc = self.dbh.cursor()

    def updateStats(self,averageOverTime):
        log.debug("Updating Stats")
        # Note: we are using transactions... so we can set the speed = 0 and it doesn't take affect until we are commited.
        self.dbc.execute("update pool_worker set speed = 0, alive = 0");
        stime = '%.2f' % ( time.time() - averageOverTime );
        self.dbc.execute("select username,SUM(difficulty) from shares where time > :time group by username", {'time':stime})
        total_speed = 0
        sqldata = []
        for name,shares in self.dbc.fetchall():
            speed = int(int(shares) * pow(2,32)) / ( int(averageOverTime) * 1000 * 1000)
            total_speed += speed
            sqldata.append({'speed':speed,'user':name})
        self.dbc.executemany("update pool_worker set speed = :speed, alive = 1 where username = :user",sqldata)
        self.dbc.execute("update pool set value = :val where parameter = 'pool_speed'",{'val':total_speed})
        self.dbh.commit()

    def archive_check(self):
        # Check for found shares to archive
        self.dbc.execute("select time from shares where upstream_result = 1 order by time limit 1")
        data = self.dbc.fetchone()
        if data is None or (data[0] + settings.ARCHIVE_DELAY) > time.time() :
            return False
        return data[0]

    def archive_found(self,found_time):
        self.dbc.execute("insert into shares_archive_found select * from shares where upstream_result = 1 and time <= :time",{'time':found_time})
        self.dbh.commit()

    def archive_to_db(self,found_time):
        self.dbc.execute("insert into shares_archive select * from shares where time <= :time",{'time':found_time})
        self.dbh.commit()

    def archive_cleanup(self,found_time):
        self.dbc.execute("delete from shares where time <= :time",{'time':found_time})
        self.dbc.execute("vacuum")
        self.dbh.commit()

    def archive_get_shares(self,found_time):
        self.dbc.execute("select * from shares where time <= :time",{'time':found_time})
        return self.dbc

    def import_shares(self,data):
        log.debug("Importing Shares")
#               0           1            2          3          4         5        6  7            8         9              10
#        data: [worker_name,block_header,block_hash,difficulty,timestamp,is_valid,ip,block_height,prev_hash,invalid_reason,share_diff]
        checkin_times = {}
        total_shares = 0
        best_diff = 0
        sqldata = []
        for k,v in enumerate(data):
            if settings.DATABASE_EXTEND :
                total_shares += v[3]
                if v[0] in checkin_times:
                    if v[4] > checkin_times[v[0]] :
                        checkin_times[v[0]]["time"] = v[4]
                else:
                    checkin_times[v[0]] = {"time": v[4], "shares": 0, "rejects": 0 }

                if v[5] == True :
                    checkin_times[v[0]]["shares"] += v[3]
                else :
                    checkin_times[v[0]]["rejects"] += v[3]

                if v[10] > best_diff:
                    best_diff = v[10]

                sqldata.append({'time':v[4],'rem_host':v[6],'username':v[0],'our_result':v[5],'upstream_result':0,'reason':v[9],'solution':'',
                                'block_num':v[7],'prev_block_hash':v[8],'ua':'','diff':v[3]} )
            else :
                sqldata.append({'time':v[4],'rem_host':v[6],'username':v[0],'our_result':v[5],'upstream_result':0,'reason':v[9],'solution':''} )

        if settings.DATABASE_EXTEND :
            self.dbc.executemany("insert into shares " +\
                "(time,rem_host,username,our_result,upstream_result,reason,solution,block_num,prev_block_hash,useragent,difficulty) " +\
                "VALUES (:time,:rem_host,:username,:our_result,:upstream_result,:reason,:solution,:block_num,:prev_block_hash,:ua,:diff)",sqldata)


            self.dbc.execute("select value from pool where parameter = 'round_shares'")
            round_shares = int(self.dbc.fetchone()[0]) + total_shares
            self.dbc.execute("update pool set value = :val where parameter = 'round_shares'",{'val':round_shares})

            self.dbc.execute("select value from pool where parameter = 'round_best_share'")
            round_best_share = int(self.dbc.fetchone()[0])
            if best_diff > round_best_share:
                self.dbc.execute("update pool set value = :val where parameter = 'round_best_share'",{'val':best_diff})

            self.dbc.execute("select value from pool where parameter = 'bitcoin_difficulty'")
            difficulty = float(self.dbc.fetchone()[0])

            if difficulty == 0:
                progress = 0
            else:
                progress = (round_shares/difficulty)*100
            self.dbc.execute("update pool set value = :val where parameter = 'round_progress'",{'val':progress})

            sqldata = []
            for k,v in checkin_times.items():
                sqldata.append({'last_checkin':v["time"],'addshares':v["shares"],'addrejects':v["rejects"],'user':k})

            self.dbc.executemany("update pool_worker set last_checkin = :last_checkin, total_shares = total_shares + :addshares, " +\
                        "total_rejects = total_rejects + :addrejects where username = :user",sqldata)
        else:
            self.dbc.executemany("insert into shares (time,rem_host,username,our_result,upstream_result,reason,solution) " +\
                "VALUES (:time,:rem_host,:username,:our_result,:upstream_result,:reason,:solution)",sqldata)

        self.dbh.commit()

    def found_block(self,data):
        # Note: difficulty = -1 here
        self.dbc.execute("update shares set upstream_result = :usr, solution = :sol where time = :time and username = :user",
                {'usr':data[5],'sol':data[2],'time':data[4],'user':data[0]})
        if settings.DATABASE_EXTEND and data[5] == True :
            self.dbc.execute("update pool_worker set total_found = total_found + 1 where username = :user",{'user':data[0]})
            self.dbc.execute("select value from pool where parameter = 'pool_total_found'")
            total_found = int(self.dbc.fetchone()[0]) + 1
            self.dbc.executemany("update pool set value = :val where parameter = :parm", [{'val':0,'parm':'round_shares'},
                {'val':0,'parm':'round_progress'},
                {'val':0,'parm':'round_best_share'},
                {'val':time.time(),'parm':'round_start'},
                {'val':total_found,'parm':'pool_total_found'}
                ])
        self.dbh.commit()
                
    def get_user(self, id_or_username):
        raise NotImplementedError('Not implemented for SQLite')
        
    def list_users(self):
        raise NotImplementedError('Not implemented for SQLite')

    def delete_user(self,id_or_username):
        raise NotImplementedError('Not implemented for SQLite')

    def insert_user(self,username,password):
        log.debug("Adding Username/Password")
        self.dbc.execute("insert into pool_worker (username,password) VALUES (:user,:pass)", {'user':username,'pass':password})
        self.dbh.commit()

    def update_user(self,username,password):
        raise NotImplementedError('Not implemented for SQLite')

    def check_password(self,username,password):
        log.debug("Checking Username/Password")
        self.dbc.execute("select COUNT(*) from pool_worker where username = :user and password = :pass", {'user':username,'pass':password})
        data = self.dbc.fetchone()
        if data[0] > 0 :
            return True
        return False

    def update_worker_diff(self,username,diff):
        self.dbc.execute("update pool_worker set difficulty = :diff where username = :user",{'diff':diff,'user':username})
        self.dbh.commit()
    
    def clear_worker_diff(self):
        if settings.DATABASE_EXTEND == True :
            self.dbc.execute("update pool_worker set difficulty = 0")
            self.dbh.commit()

    def update_pool_info(self,pi):
        self.dbc.executemany("update pool set value = :val where parameter = :parm",[{'val':pi['blocks'],'parm':"bitcoin_blocks"},
                {'val':pi['balance'],'parm':"bitcoin_balance"},
                {'val':pi['connections'],'parm':"bitcoin_connections"},
                {'val':pi['difficulty'],'parm':"bitcoin_difficulty"},
                {'val':time.time(),'parm':"bitcoin_infotime"}
                ])
        self.dbh.commit()

    def get_pool_stats(self):
        self.dbc.execute("select * from pool")
        ret = {}
        for data in self.dbc.fetchall():
            ret[data[0]] = data[1]
        return ret

    def get_workers_stats(self):
        self.dbc.execute("select username,speed,last_checkin,total_shares,total_rejects,total_found,alive,difficulty from pool_worker")
        ret = {}
        for data in self.dbc.fetchall():
            ret[data[0]] = { "username" : data[0],
                "speed" : data[1],
                "last_checkin" : data[2],
                "total_shares" : data[3],
                "total_rejects" : data[4],
                "total_found" : data[5],
                "alive" : data[6],
                "difficulty" : data[7] }
        return ret

    def close(self):
        self.dbh.close()

    def check_tables(self):
        log.debug("Checking Tables")
        if settings.DATABASE_EXTEND == True :
                self.dbc.execute("create table if not exists shares" +\
                        "(time DATETIME,rem_host TEXT, username TEXT, our_result INTEGER, upstream_result INTEGER, reason TEXT, solution TEXT, " +\
                        "block_num INTEGER, prev_block_hash TEXT, useragent TEXT, difficulty INTEGER)")
                self.dbc.execute("create table if not exists pool_worker" +\
                        "(username TEXT, password TEXT, speed INTEGER, last_checkin DATETIME)")
                self.dbc.execute("create table if not exists pool(parameter TEXT, value TEXT)")

                self.dbc.execute("select COUNT(*) from pool where parameter = 'DB Version'")
                data = self.dbc.fetchone()
                if data[0] <= 0:
                    self.dbc.execute("alter table pool_worker add total_shares INTEGER default 0")
                    self.dbc.execute("alter table pool_worker add total_rejects INTEGER default 0")
                    self.dbc.execute("alter table pool_worker add total_found INTEGER default 0")
                    self.dbc.execute("insert into pool (parameter,value) VALUES ('DB Version',2)")
                self.update_tables()
        else :
                self.dbc.execute("create table if not exists shares" + \
                        "(time DATETIME,rem_host TEXT, username TEXT, our_result INTEGER, upstream_result INTEGER, reason TEXT, solution TEXT)")
                self.dbc.execute("create table if not exists pool_worker(username TEXT, password TEXT)")
                self.dbc.execute("create index if not exists pool_worker_username ON pool_worker(username)")

    def update_tables(self):
        version = 0
        current_version = 6
        while version < current_version :
            self.dbc.execute("select value from pool where parameter = 'DB Version'")
            data = self.dbc.fetchone()
            version = int(data[0])
            if version < current_version :
                log.info("Updating Database from %i to %i" % (version, version +1))
                getattr(self, 'update_version_' + str(version) )()


    def update_version_2(self):
        log.info("running update 2")
        self.dbc.executemany("insert into pool (parameter,value) VALUES (?,?)",[('bitcoin_blocks',0),
                ('bitcoin_balance',0),
                ('bitcoin_connections',0),
                ('bitcoin_difficulty',0),
                ('pool_speed',0),
                ('pool_total_found',0),
                ('round_shares',0),
                ('round_progress',0),
                ('round_start',time.time())
                ])
        self.dbc.execute("create index if not exists shares_username ON shares(username)")
        self.dbc.execute("create index if not exists pool_worker_username ON pool_worker(username)")
        self.dbc.execute("update pool set value = 3 where parameter = 'DB Version'")
        self.dbh.commit()
    
    def update_version_3(self):
        log.info("running update 3")
        self.dbc.executemany("insert into pool (parameter,value) VALUES (?,?)",[
                ('round_best_share',0),
                ('bitcoin_infotime',0),
                ])
        self.dbc.execute("alter table pool_worker add alive INTEGER default 0")
        self.dbc.execute("update pool set value = 4 where parameter = 'DB Version'")
        self.dbh.commit()

    def update_version_4(self):
        log.info("running update 4")
        self.dbc.execute("alter table pool_worker add difficulty INTEGER default 0")
        self.dbc.execute("create table if not exists shares_archive" +\
                "(time DATETIME,rem_host TEXT, username TEXT, our_result INTEGER, upstream_result INTEGER, reason TEXT, solution TEXT, " +\
                "block_num INTEGER, prev_block_hash TEXT, useragent TEXT, difficulty INTEGER)")
        self.dbc.execute("create table if not exists shares_archive_found" +\
                "(time DATETIME,rem_host TEXT, username TEXT, our_result INTEGER, upstream_result INTEGER, reason TEXT, solution TEXT, " +\
                "block_num INTEGER, prev_block_hash TEXT, useragent TEXT, difficulty INTEGER)")
        self.dbc.execute("update pool set value = 5 where parameter = 'DB Version'")
        self.dbh.commit()

    def update_version_5(self):
        log.info("running update 5")
        # Adding Primary key to table: pool
        self.dbc.execute("alter table pool rename to pool_old")
        self.dbc.execute("create table if not exists pool(parameter TEXT, value TEXT, primary key(parameter))")
        self.dbc.execute("insert into pool select * from pool_old")
        self.dbc.execute("drop table pool_old")
        self.dbh.commit()
        # Adding Primary key to table: pool_worker
        self.dbc.execute("alter table pool_worker rename to pool_worker_old")
        self.dbc.execute("CREATE TABLE pool_worker(username TEXT, password TEXT, speed INTEGER, last_checkin DATETIME, total_shares INTEGER default 0, total_rejects INTEGER default 0, total_found INTEGER default 0, alive INTEGER default 0, difficulty INTEGER default 0, primary key(username))")
        self.dbc.execute("insert into pool_worker select * from pool_worker_old")
        self.dbc.execute("drop table pool_worker_old")
        self.dbh.commit()
        # Adjusting indicies on table: shares
        self.dbc.execute("DROP INDEX shares_username")
        self.dbc.execute("CREATE INDEX shares_time_username ON shares(time,username)")
        self.dbc.execute("CREATE INDEX shares_upstreamresult ON shares(upstream_result)")
        self.dbh.commit()

        self.dbc.execute("update pool set value = 6 where parameter = 'DB Version'")
        self.dbh.commit()

########NEW FILE########
__FILENAME__ = interfaces
'''This module contains classes used by pool core to interact with the rest of the pool.
   Default implementation do almost nothing, you probably want to override these classes
   and customize references to interface instances in your launcher.
   (see launcher_demo.tac for an example).
''' 
import time
from twisted.internet import reactor, defer
from lib.util import b58encode

import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('interfaces')

import DBInterface
dbi = DBInterface.DBInterface()
dbi.init_main()

class WorkerManagerInterface(object):
    def __init__(self):
        self.worker_log = {}
        self.worker_log.setdefault('authorized', {})
        self.job_log = {}
        self.job_log.setdefault('None', {})
        return
        
    def authorize(self, worker_name, worker_password):
        # Important NOTE: This is called on EVERY submitted share. So you'll need caching!!!
        return dbi.check_password(worker_name, worker_password)
 
    def get_user_difficulty(self, worker_name):
        wd = dbi.get_user(worker_name)
        if len(wd) > 6:
            if wd[6] != 0:
                return (True, wd[6])
                #dbi.update_worker_diff(worker_name, wd[6])
        return (False, settings.POOL_TARGET)

    def register_work(self, worker_name, job_id, difficulty):
        now = Interfaces.timestamper.time()
        work_id = WorkIdGenerator.get_new_id()
        self.job_log.setdefault(worker_name, {})[work_id] = (job_id, difficulty, now)
        return work_id

class WorkIdGenerator(object):
    counter = 1000
    
    @classmethod
    def get_new_id(cls):
        cls.counter += 1
        if cls.counter % 0xffff == 0:
            cls.counter = 1
        return "%x" % cls.counter

class ShareLimiterInterface(object):
    '''Implement difficulty adjustments here'''
    
    def submit(self, connection_ref, job_id, current_difficulty, timestamp, worker_name):
        '''connection - weak reference to Protocol instance
           current_difficulty - difficulty of the connection
           timestamp - submission time of current share
           
           - raise SubmitException for stop processing this request
           - call mining.set_difficulty on connection to adjust the difficulty'''
        new_diff = dbi.get_worker_diff(worker_name)
        session = connection_ref().get_session()
        session['prev_diff'] = session['difficulty']
        session['prev_jobid'] = job_id
        session['difficulty'] = new_diff
        connection_ref().rpc('mining.set_difficulty', [new_diff,], is_notification=True)
        #return dbi.update_worker_diff(worker_name, settings.POOL_TARGET)
        return
 
class ShareManagerInterface(object):
    def __init__(self):
        self.block_height = 0
        self.prev_hash = 0
    
    def on_network_block(self, prevhash, block_height):
        '''Prints when there's new block coming from the network (possibly new round)'''
        self.block_height = block_height        
        self.prev_hash = b58encode(int(prevhash, 16))
        pass
    
    def on_submit_share(self, worker_name, block_header, block_hash, difficulty, timestamp, is_valid, ip, invalid_reason, share_diff):
        log.debug("%s (%s) %s %s" % (block_hash, share_diff, 'valid' if is_valid else 'INVALID', worker_name))
        dbi.queue_share([worker_name, block_header, block_hash, difficulty, timestamp, is_valid, ip, self.block_height, self.prev_hash,
                invalid_reason, share_diff ])
 
    def on_submit_block(self, is_accepted, worker_name, block_header, block_hash, timestamp, ip, share_diff):
        log.info("Block %s %s" % (block_hash, 'ACCEPTED' if is_accepted else 'REJECTED'))
        #dbi.run_import(dbi, Force=True)
        dbi.found_block([worker_name, block_header, block_hash, -1, timestamp, is_accepted, ip, self.block_height, self.prev_hash, share_diff ])
        
class TimestamperInterface(object):
    '''This is the only source for current time in the application.
    Override this for generating unix timestamp in different way.'''
    def time(self):
        return time.time()

class PredictableTimestamperInterface(TimestamperInterface):
    '''Predictable timestamper may be useful for unit testing.'''
    start_time = 1345678900  # Some day in year 2012
    delta = 0
    
    def time(self):
        self.delta += 1
        return self.start_time + self.delta

class Interfaces(object):
    worker_manager = None
    share_manager = None
    share_limiter = None
    timestamper = None
    template_registry = None

    @classmethod
    def set_worker_manager(cls, manager):
        cls.worker_manager = manager    
    
    @classmethod        
    def set_share_manager(cls, manager):
        cls.share_manager = manager

    @classmethod        
    def set_share_limiter(cls, limiter):
        cls.share_limiter = limiter
    
    @classmethod
    def set_timestamper(cls, manager):
        cls.timestamper = manager
        
    @classmethod
    def set_template_registry(cls, registry):
        dbi.set_bitcoinrpc(registry.bitcoin_rpc)
        cls.template_registry = registry

########NEW FILE########
__FILENAME__ = service
import binascii
from twisted.internet import defer

import lib.settings as settings
from stratum.services import GenericService, admin
from stratum.pubsub import Pubsub
from interfaces import Interfaces
from subscription import MiningSubscription
from lib.exceptions import SubmitException
import json
import lib.logger
log = lib.logger.get_logger('mining')
                
class MiningService(GenericService):
    '''This service provides public API for Stratum mining proxy
    or any Stratum-compatible miner software.
    
    Warning - any callable argument of this class will be propagated
    over Stratum protocol for public audience!'''
    
    service_type = 'mining'
    service_vendor = 'stratum'
    is_default = True
    event = 'mining.notify'

    @admin
    def get_server_stats(self):
        serialized = '' 
        for subscription in Pubsub.iterate_subscribers(self.event):
            try:
                if subscription != None:
                    session = subscription.connection_ref().get_session()
                    session.setdefault('authorized', {})
                    if session['authorized'].keys():
                        worker_name = session['authorized'].keys()[0]
                        difficulty = session['difficulty']
                        ip = subscription.connection_ref()._get_ip()
                        serialized += json.dumps({'worker_name': worker_name, 'ip': ip, 'difficulty': difficulty})
                    else:
                        pass
            except Exception as e:
                log.exception("Error getting subscriptions %s" % str(e))
                pass

        log.debug("Server stats request: %s" % serialized)
        return '%s' % serialized

    @admin
    def update_block(self):
        '''Connect this RPC call to 'litecoind -blocknotify' for 
        instant notification about new block on the network.
        See blocknotify.sh in /scripts/ for more info.'''
        
        log.info("New block notification received")
        Interfaces.template_registry.update_block()
        return True 

    @admin
    def add_litecoind(self, *args):
        ''' Function to add a litecoind instance live '''
        if len(args) != 4:
            raise SubmitException("Incorrect number of parameters sent")

        #(host, port, user, password) = args
        Interfaces.template_registry.bitcoin_rpc.add_connection(args[0], args[1], args[2], args[3])
        log.info("New litecoind connection added %s:%s" % (args[0], args[1]))
        return True 
    
    @admin
    def refresh_config(self):
        settings.setup()
        log.info("Updated Config")
        return True
        
    def authorize(self, worker_name, worker_password):
        '''Let authorize worker on this connection.'''
        
        session = self.connection_ref().get_session()
        session.setdefault('authorized', {})
        
        if Interfaces.worker_manager.authorize(worker_name, worker_password):
            session['authorized'][worker_name] = worker_password
            is_ext_diff = False
            if settings.ALLOW_EXTERNAL_DIFFICULTY:
                (is_ext_diff, session['difficulty']) = Interfaces.worker_manager.get_user_difficulty(worker_name)
                self.connection_ref().rpc('mining.set_difficulty', [session['difficulty'], ], is_notification=True)
            else:
                session['difficulty'] = settings.POOL_TARGET
            # worker_log = (valid, invalid, is_banned, diff, is_ext_diff, timestamp)
            Interfaces.worker_manager.worker_log['authorized'][worker_name] = (0, 0, False, session['difficulty'], is_ext_diff, Interfaces.timestamper.time())            
            return True
        else:
            ip = self.connection_ref()._get_ip()
            log.info("Failed worker authorization: IP %s", str(ip))
            if worker_name in session['authorized']:
                del session['authorized'][worker_name]
            if worker_name in Interfaces.worker_manager.worker_log['authorized']:
                del Interfaces.worker_manager.worker_log['authorized'][worker_name]
            return False
        
    def subscribe(self, *args):
        '''Subscribe for receiving mining jobs. This will
        return subscription details, extranonce1_hex and extranonce2_size'''
        
        extranonce1 = Interfaces.template_registry.get_new_extranonce1()
        extranonce2_size = Interfaces.template_registry.extranonce2_size
        extranonce1_hex = binascii.hexlify(extranonce1)
        
        session = self.connection_ref().get_session()
        session['extranonce1'] = extranonce1
        session['difficulty'] = settings.POOL_TARGET  # Following protocol specs, default diff is 1
        return Pubsub.subscribe(self.connection_ref(), MiningSubscription()) + (extranonce1_hex, extranonce2_size)
        
    def submit(self, worker_name, work_id, extranonce2, ntime, nonce):
        '''Try to solve block candidate using given parameters.'''
        
        session = self.connection_ref().get_session()
        session.setdefault('authorized', {})
        
        # Check if worker is authorized to submit shares
        ip = self.connection_ref()._get_ip()
        if not Interfaces.worker_manager.authorize(worker_name, session['authorized'].get(worker_name)):
            log.info("Worker is not authorized: IP %s", str(ip))
            raise SubmitException("Worker is not authorized")

        # Check if extranonce1 is in connection session
        extranonce1_bin = session.get('extranonce1', None)
        
        if not extranonce1_bin:
            log.info("Connection is not subscribed for mining: IP %s", str(ip))
            raise SubmitException("Connection is not subscribed for mining")
        
        # Get current block job_id
        difficulty = session['difficulty']
        if worker_name in Interfaces.worker_manager.job_log and work_id in Interfaces.worker_manager.job_log[worker_name]:
            (job_id, difficulty, job_ts) = Interfaces.worker_manager.job_log[worker_name][work_id]
        else:
            job_ts = Interfaces.timestamper.time()
            Interfaces.worker_manager.job_log.setdefault(worker_name, {})[work_id] = (work_id, difficulty, job_ts)
            job_id = work_id
        #log.debug("worker_job_log: %s" % repr(Interfaces.worker_manager.job_log))

        submit_time = Interfaces.timestamper.time()

        (valid, invalid, is_banned, diff, is_ext_diff, last_ts) = Interfaces.worker_manager.worker_log['authorized'][worker_name]
        percent = float(float(invalid) / (float(valid) if valid else 1) * 100)

        if is_banned and submit_time - last_ts > settings.WORKER_BAN_TIME:
            if percent > settings.INVALID_SHARES_PERCENT:
                log.debug("Worker invalid percent: %0.2f %s STILL BANNED!" % (percent, worker_name))
            else: 
                is_banned = False
                log.debug("Clearing ban for worker: %s UNBANNED" % worker_name)
            (valid, invalid, is_banned, last_ts) = (0, 0, is_banned, Interfaces.timestamper.time())

        if submit_time - last_ts > settings.WORKER_CACHE_TIME and not is_banned:
            if percent > settings.INVALID_SHARES_PERCENT and settings.ENABLE_WORKER_BANNING:
                is_banned = True
                log.debug("Worker invalid percent: %0.2f %s BANNED!" % (percent, worker_name))
            else:
                log.debug("Clearing worker stats for: %s" % worker_name)
            (valid, invalid, is_banned, last_ts) = (0, 0, is_banned, Interfaces.timestamper.time())

        log.debug("%s (%d, %d, %s, %s, %d) %0.2f%% work_id(%s) job_id(%s) diff(%f)" % (worker_name, valid, invalid, is_banned, is_ext_diff, last_ts, percent, work_id, job_id, difficulty))
        if not is_ext_diff:    
            Interfaces.share_limiter.submit(self.connection_ref, job_id, difficulty, submit_time, worker_name)
            
        # This checks if submitted share meet all requirements
        # and it is valid proof of work.
        try:
            (block_header, block_hash, share_diff, on_submit) = Interfaces.template_registry.submit_share(job_id,
                worker_name, session, extranonce1_bin, extranonce2, ntime, nonce, difficulty, ip)
        except SubmitException as e:
            # block_header and block_hash are None when submitted data are corrupted
            invalid += 1
            Interfaces.worker_manager.worker_log['authorized'][worker_name] = (valid, invalid, is_banned, difficulty, is_ext_diff, last_ts)

            if is_banned:
                raise SubmitException("Worker is temporarily banned")
 
            Interfaces.share_manager.on_submit_share(worker_name, False, False, difficulty,
                submit_time, False, ip, e[0], 0)   
            raise

        valid += 1
        Interfaces.worker_manager.worker_log['authorized'][worker_name] = (valid, invalid, is_banned, difficulty, is_ext_diff, last_ts)

        if is_banned:
            raise SubmitException("Worker is temporarily banned")
 
        Interfaces.share_manager.on_submit_share(worker_name, block_header,
            block_hash, difficulty, submit_time, True, ip, '', share_diff)

        if on_submit != None:
            # Pool performs submitblock() to litecoind. Let's hook
            # to result and report it to share manager
            on_submit.addCallback(Interfaces.share_manager.on_submit_block,
                worker_name, block_header, block_hash, submit_time, ip, share_diff)

        return True
            
    # Service documentation for remote discovery
    update_block.help_text = "Notify Stratum server about new block on the network."
    update_block.params = [('password', 'string', 'Administrator password'), ]
    
    authorize.help_text = "Authorize worker for submitting shares on this connection."
    authorize.params = [('worker_name', 'string', 'Name of the worker, usually in the form of user_login.worker_id.'),
                        ('worker_password', 'string', 'Worker password'), ]
    
    subscribe.help_text = "Subscribes current connection for receiving new mining jobs."
    subscribe.params = []
    
    submit.help_text = "Submit solved share back to the server. Excessive sending of invalid shares "\
                       "or shares above indicated target (see Stratum mining docs for set_target()) may lead "\
                       "to temporary or permanent ban of user,worker or IP address."
    submit.params = [('worker_name', 'string', 'Name of the worker, usually in the form of user_login.worker_id.'),
                     ('job_id', 'string', 'ID of job (received by mining.notify) which the current solution is based on.'),
                     ('extranonce2', 'string', 'hex-encoded big-endian extranonce2, length depends on extranonce2_size from mining.notify.'),
                     ('ntime', 'string', 'UNIX timestamp (32bit integer, big-endian, hex-encoded), must be >= ntime provided by mining,notify and <= current time'),
                     ('nonce', 'string', '32bit integer, hex-encoded, big-endian'), ]
        

########NEW FILE########
__FILENAME__ = subscription
from stratum.pubsub import Pubsub, Subscription
from mining.interfaces import Interfaces

import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('subscription')

class MiningSubscription(Subscription):
    '''This subscription object implements
    logic for broadcasting new jobs to the clients.'''
    
    event = 'mining.notify'
    
    @classmethod
    def on_template(cls, is_new_block):
        '''This is called when TemplateRegistry registers
           new block which we have to broadcast clients.'''
        
        start = Interfaces.timestamper.time()
        clean_jobs = is_new_block
        
        (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _) = \
            Interfaces.template_registry.get_last_broadcast_args()

        # Push new job to subscribed clients
        for subscription in Pubsub.iterate_subscribers(cls.event):
            try:
                if subscription != None:
                    session = subscription.connection_ref().get_session()
                    session.setdefault('authorized', {})
                    if session['authorized'].keys():
                        worker_name = session['authorized'].keys()[0]
                        difficulty = session['difficulty']
                        work_id = Interfaces.worker_manager.register_work(worker_name, job_id, difficulty)             
                        subscription.emit_single(work_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)
                    else:
                        subscription.emit_single(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)
            except Exception as e:
                log.exception("Error broadcasting work to client %s" % str(e))
                pass
        
        cnt = Pubsub.get_subscription_count(cls.event)
        log.info("BROADCASTED to %d connections in %.03f sec" % (cnt, (Interfaces.timestamper.time() - start)))
        
    def _finish_after_subscribe(self, result):
        '''Send new job to newly subscribed client'''
        try:        
            (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _) = \
                        Interfaces.template_registry.get_last_broadcast_args()
        except Exception:
            log.error("Template not ready yet")
            return result
        
        # Force set higher difficulty
        self.connection_ref().rpc('mining.set_difficulty', [settings.POOL_TARGET, ], is_notification=True)
        # self.connection_ref().rpc('client.get_version', [])
        
        # Force client to remove previous jobs if any (eg. from previous connection)
        clean_jobs = True
        self.emit_single(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, True)
        
        return result
                
    def after_subscribe(self, *args):
        '''This will send new job to the client *after* he receive subscription details.
        on_finish callback solve the issue that job is broadcasted *during*
        the subscription request and client receive messages in wrong order.'''
        self.connection_ref().on_finish.addCallback(self._finish_after_subscribe)


########NEW FILE########
__FILENAME__ = work_log_pruner
from time import sleep, time
import traceback
import lib.logger
log = lib.logger.get_logger('work_log_pruner')

def _WorkLogPruner_I(wl):
    now = time()
    pruned = 0
    for username in wl:
        userwork = wl[username]
        for wli in tuple(userwork.keys()):
            if now > userwork[wli][2] + 120:
                del userwork[wli]
                pruned += 1
    log.info('Pruned %d jobs' % (pruned,))

def WorkLogPruner(wl):
    while True:
        try:
            sleep(60)
            _WorkLogPruner_I(wl)
        except:
            log.debug(traceback.format_exc())

########NEW FILE########
