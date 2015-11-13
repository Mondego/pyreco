__FILENAME__ = example_multicast
#!/usr/bin/env python
'''
    This is just an example script for miner developers.
    If you're end user, you don't need to use this script.

    Detector of Stratum mining proxies on local network
    Copyright (C) 2012 Marek Palatinus <slush@satoshilabs.com>
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor, defer

import json

class MulticastClient(DatagramProtocol):

    def startProtocol(self):
        self.transport.joinGroup("239.3.3.3")
        self.transport.write(json.dumps({"id": 0, "method": "mining.get_upstream", "params": []}), ('239.3.3.3', 3333))

    def datagramReceived(self, datagram, address):
        '''Some data from peers received.

           Example of valid datagram:
              {"id": 0, "result": [["api-stratum.bitcoin.cz", 3333], 3333, 8332], "error": null}

           First argument - (host, port) of upstream pool
           Second argument - Stratum port where proxy is listening
           Third parameter - Getwork port where proxy is listening
        '''
        #print "Datagram %s received from %s" % (datagram, address)

        try:
            data = json.loads(datagram)
        except:
            print "Unparsable datagram received"


        if data.get('id') != 0 or data.get('result') == None:
            return


        (proxy_host, proxy_port) = address
	(pool_host, pool_port) = data['result'][0]
        stratum_port = data['result'][1]
        getwork_port = data['result'][2]

        print "Found stratum proxy on %(proxy_host)s:%(stratum_port)d (stratum), "\
               "%(proxy_host)s:%(getwork_port)d (getwork), "\
               "mining for %(pool_host)s:%(pool_port)d" % \
              {'proxy_host': proxy_host,
               'pool_host': pool_host,
               'pool_port': pool_port,
               'stratum_port': stratum_port,
               'getwork_port': getwork_port}

def stop():
    print "Local discovery of Stratum proxies is finished."
    reactor.stop()

print "Listening for Stratum proxies on local network..."
reactor.listenMulticast(3333, MulticastClient(), listenMultiple=True)
reactor.callLater(5, stop)
reactor.run()

########NEW FILE########
__FILENAME__ = midstatec
# Original source: https://gitorious.org/midstate/midstate

import struct
import binascii
from midstate import SHA256

test_data = binascii.unhexlify("0000000293d5a732e749dbb3ea84318bd0219240a2e2945046015880000003f5000000008d8e2673e5a071a2c83c86e28033b1a0a4aac90dde7a0670827cd0c3ef8caf7d5076c7b91a057e0800000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000")
test_target_midstate = binascii.unhexlify("4c8226f95a31c9619f5197809270e4fa0a2d34c10215cf4456325e1237cb009d")


def midstate(data):
    reversed = struct.pack('>IIIIIIIIIIIIIIII', *struct.unpack('>IIIIIIIIIIIIIIII', data[:64])[::-1])[::-1]
    return struct.pack('<IIIIIIII', *SHA256(reversed))

def test():
    return midstate(test_data) == test_target_midstate

if __name__ == '__main__':
    print "target:  ", binascii.hexlify(test_target_midstate)
    print "computed:", binascii.hexlify(midstate(test_data))
    print "passed:  ", test()

########NEW FILE########
__FILENAME__ = client_service
from twisted.internet import reactor

from stratum.event_handler import GenericEventHandler
from jobs import Job
import utils
import version as _version

import stratum_listener

import stratum.logger
log = stratum.logger.get_logger('proxy')

class ClientMiningService(GenericEventHandler):
    job_registry = None # Reference to JobRegistry instance
    timeout = None # Reference to IReactorTime object
    
    @classmethod
    def reset_timeout(cls):
        if cls.timeout != None:
            if not cls.timeout.called:
                cls.timeout.cancel()
            cls.timeout = None
            
        cls.timeout = reactor.callLater(2*60, cls.on_timeout)

    @classmethod
    def on_timeout(cls):
        '''
            Try to reconnect to the pool after two minutes of no activity on the connection.
            It will also drop all Stratum connections to sub-miners
            to indicate connection issues.
        '''
        log.error("Connection to upstream pool timed out")
        cls.reset_timeout()
        cls.job_registry.f.reconnect()
                
    def handle_event(self, method, params, connection_ref):
        '''Handle RPC calls and notifications from the pool'''

        # Yay, we received something from the pool,
        # let's restart the timeout.
        self.reset_timeout()
        
        if method == 'mining.notify':
            '''Proxy just received information about new mining job'''
            
            (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs) = params[:9]
            #print len(str(params)), len(merkle_branch)
            
            '''
            log.debug("Received new job #%s" % job_id)
            log.debug("prevhash = %s" % prevhash)
            log.debug("version = %s" % version)
            log.debug("nbits = %s" % nbits)
            log.debug("ntime = %s" % ntime)
            log.debug("clean_jobs = %s" % clean_jobs)
            log.debug("coinb1 = %s" % coinb1)
            log.debug("coinb2 = %s" % coinb2)
            log.debug("merkle_branch = %s" % merkle_branch)
            '''
        
            # Broadcast to Stratum clients
            stratum_listener.MiningSubscription.on_template(
                            job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)
            
            # Broadcast to getwork clients
            job = Job.build_from_broadcast(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime)
            log.info("New job %s for prevhash %s, clean_jobs=%s" % \
                 (job.job_id, utils.format_hash(job.prevhash), clean_jobs))

            self.job_registry.add_template(job, clean_jobs)
            
            
            
        elif method == 'mining.set_difficulty':
            difficulty = params[0]
            log.info("Setting new difficulty: %s" % difficulty)
            
            stratum_listener.DifficultySubscription.on_new_difficulty(difficulty)
            self.job_registry.set_difficulty(difficulty)
                    
        elif method == 'client.reconnect':
            (hostname, port, wait) = params[:3]
            new = list(self.job_registry.f.main_host[::])
            if hostname: new[0] = hostname
            if port: new[1] = port

            log.info("Server asked us to reconnect to %s:%d" % tuple(new))
            self.job_registry.f.reconnect(new[0], new[1], wait)
            
        elif method == 'client.add_peers':
            '''New peers which can be used on connection failure'''
            return False
            '''
            peerlist = params[0] # TODO
            for peer in peerlist:
                self.job_registry.f.add_peer(peer)
            return True
            '''
        elif method == 'client.get_version':
            return "stratum-proxy/%s" % _version.VERSION

        elif method == 'client.show_message':
            
            # Displays message from the server to the terminal
            utils.show_message(params[0])
            return True
            
        elif method == 'mining.get_hashrate':
            return {} # TODO
        
        elif method == 'mining.get_temperature':
            return {} # TODO
        
        else:
            '''Pool just asked us for something which we don't support...'''
            log.error("Unhandled method %s with params %s" % (method, params))


########NEW FILE########
__FILENAME__ = getwork_listener
import json
import time

from twisted.internet import defer
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

import stratum.logger
log = stratum.logger.get_logger('proxy')

class Root(Resource):
    isLeaf = True
    
    def __init__(self, job_registry, workers, stratum_host, stratum_port,
                 custom_stratum=None, custom_lp=None, custom_user=None, custom_password=''):
        Resource.__init__(self)
        self.job_registry = job_registry
        self.workers = workers
        self.stratum_host = stratum_host
        self.stratum_port = stratum_port
        self.custom_stratum = custom_stratum
        self.custom_lp = custom_lp
        self.custom_user = custom_user
        self.custom_password = custom_password
        
    def json_response(self, msg_id, result):
        resp = json.dumps({'id': msg_id, 'result': result, 'error': None})
        #print "RESPONSE", resp
        return resp
    
    def json_error(self, msg_id, code, message):
        resp = json.dumps({'id': msg_id, 'result': None, 'error': {'code': code, 'message': message}})
        #print "ERROR", resp
        return resp         
    
    def _on_submit(self, result, request, msg_id, blockheader, worker_name, start_time):
        response_time = (time.time() - start_time) * 1000
        if result == True:
            log.warning("[%dms] Share from '%s' accepted, diff %d" % (response_time, worker_name, self.job_registry.difficulty))
        else:
            log.warning("[%dms] Share from '%s' REJECTED" % (response_time, worker_name))
         
        try:   
            request.write(self.json_response(msg_id, result))
            request.finish()
        except RuntimeError:
            # RuntimeError is thrown by Request class when
            # client is disconnected already
            pass
        
    def _on_submit_failure(self, failure, request, msg_id, blockheader, worker_name, start_time):
        response_time = (time.time() - start_time) * 1000
        
        # Submit for some reason failed
        try:
            request.write(self.json_response(msg_id, False))
            request.finish()
        except RuntimeError:
            # RuntimeError is thrown by Request class when
            # client is disconnected already
            pass

        log.warning("[%dms] Share from '%s' REJECTED: %s" % \
                 (response_time, worker_name, failure.getErrorMessage()))
        
    def _on_authorized(self, is_authorized, request, worker_name):
        data = json.loads(request.content.read())
        
        if not is_authorized:
            request.write(self.json_error(data.get('id', 0), -1, "Bad worker credentials"))
            request.finish()
            return
                
        if not self.job_registry.last_job:
            log.warning('Getworkmaker is waiting for a job...')
            request.write(self.json_error(data.get('id', 0), -1, "Getworkmake is waiting for a job..."))
            request.finish()
            return

        if data['method'] == 'getwork':
            if 'params' not in data or not len(data['params']):
                                
                # getwork request
                log.info("Worker '%s' asks for new work" % worker_name)
                extensions = request.getHeader('x-mining-extensions')
                no_midstate =  extensions and 'midstate' in extensions
                request.write(self.json_response(data.get('id', 0), self.job_registry.getwork(no_midstate=no_midstate)))
                request.finish()
                return
            
            else:
                
                # submit
                d = defer.maybeDeferred(self.job_registry.submit, data['params'][0], worker_name)

                start_time = time.time()
                d.addCallback(self._on_submit, request, data.get('id', 0), data['params'][0][:160], worker_name, start_time)
                d.addErrback(self._on_submit_failure, request, data.get('id', 0), data['params'][0][:160], worker_name, start_time)
                return
            
        request.write(self.json_error(data.get('id'), -1, "Unsupported method '%s'" % data['method']))
        request.finish()
        
    def _on_failure(self, failure, request):
        request.write(self.json_error(0, -1, "Unexpected error during authorization"))
        request.finish()
        raise failure
        
    def _prepare_headers(self, request): 
        request.setHeader('content-type', 'application/json')
        
        if self.custom_stratum:
            request.setHeader('x-stratum', self.custom_stratum)    
        elif self.stratum_port:
            request.setHeader('x-stratum', 'stratum+tcp://%s:%d' % (request.getRequestHostname(), self.stratum_port))
        
        if self.custom_lp:
            request.setHeader('x-long-polling', self.custom_lp)
        else:
            request.setHeader('x-long-polling', '/lp')
            
        request.setHeader('x-roll-ntime', 1)
        
    def _on_lp_broadcast(self, _, request):        
        try:
            worker_name = request.getUser()
        except:
            worker_name = '<unknown>'
            
        log.info("LP broadcast for worker '%s'" % worker_name)
        extensions = request.getHeader('x-mining-extensions')
        no_midstate =  extensions and 'midstate' in extensions
        payload = self.json_response(0, self.job_registry.getwork(no_midstate=no_midstate))
        
        try:
            request.write(payload)
            request.finish()
        except RuntimeError:
            # RuntimeError is thrown by Request class when
            # client is disconnected already
            pass
        
    def render_POST(self, request):        
        self._prepare_headers(request)

        (worker_name, password) = (request.getUser(), request.getPassword())

        if self.custom_user:
            worker_name = self.custom_user
            password = self.custom_password
 
        if worker_name == '':
            log.warning("Authorization required")
            request.setResponseCode(401)
            request.setHeader('WWW-Authenticate', 'Basic realm="stratum-mining-proxy"')
            return "Authorization required"
        
        self._prepare_headers(request)
        
        if request.path.startswith('/lp'):
            log.info("Worker '%s' subscribed for LP" % worker_name)
            self.job_registry.on_block.addCallback(self._on_lp_broadcast, request)
            return NOT_DONE_YET
       
        d = defer.maybeDeferred(self.workers.authorize, worker_name, password)
        d.addCallback(self._on_authorized, request, worker_name)
        d.addErrback(self._on_failure, request)    
        return NOT_DONE_YET

    def render_GET(self, request):
        self._prepare_headers(request)
            
        try:
            worker_name = request.getUser()
        except:
            worker_name = '<unknown>'
                
        if self.custom_user:
            worker_name = self.custom_user
            password = self.custom_password                
                
        log.info("Worker '%s' subscribed for LP at %s" % (worker_name, request.path))
        self.job_registry.on_block.addCallback(self._on_lp_broadcast, request)
        return NOT_DONE_YET

########NEW FILE########
__FILENAME__ = jobs
import binascii
import time
import struct
import subprocess
import weakref

from twisted.internet import defer

import utils

import stratum.logger
log = stratum.logger.get_logger('proxy')

# This fix py2exe issue with packaging the midstate module
from midstate import calculateMidstate as __unusedimport

try:
    from midstatec.midstatec import test as midstateTest, midstate as calculateMidstate
    if not midstateTest():
        log.warning("midstate library didn't passed self test!")
        raise ImportError("midstatec not usable")
    log.info("Using C extension for midstate speedup. Good!")
except ImportError:
    log.info("C extension for midstate not available. Using default implementation instead.")
    try:    
        from midstate import calculateMidstate
    except ImportError:
        calculateMidstate = None
        log.exception("No midstate generator available. Some old miners won't work properly.")

class Job(object):
    def __init__(self):
        self.job_id = None
        self.prevhash = ''
        self.coinb1_bin = ''
        self.coinb2_bin = ''
        self.merkle_branch = []
        self.version = 1
        self.nbits = 0
        self.ntime_delta = 0
        
        self.extranonce2 = 0
        self.merkle_to_extranonce2 = {} # Relation between merkle_hash and extranonce2

    @classmethod
    def build_from_broadcast(cls, job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime):
        '''Build job object from Stratum server broadcast'''
        job = Job()
        job.job_id = job_id
        job.prevhash = prevhash
        job.coinb1_bin = binascii.unhexlify(coinb1)
        job.coinb2_bin = binascii.unhexlify(coinb2)
        job.merkle_branch = [ binascii.unhexlify(tx) for tx in merkle_branch ]
        job.version = version
        job.nbits = nbits
        job.ntime_delta = int(ntime, 16) - int(time.time()) 
        return job

    def increase_extranonce2(self):
        self.extranonce2 += 1
        return self.extranonce2

    def build_coinbase(self, extranonce):
        return self.coinb1_bin + extranonce + self.coinb2_bin
    
    def build_merkle_root(self, coinbase_hash):
        merkle_root = coinbase_hash
        for h in self.merkle_branch:
            merkle_root = utils.doublesha(merkle_root + h)
        return merkle_root
    
    def serialize_header(self, merkle_root, ntime, nonce):
        r =  self.version
        r += self.prevhash
        r += merkle_root
        r += binascii.hexlify(struct.pack(">I", ntime))
        r += self.nbits
        r += binascii.hexlify(struct.pack(">I", nonce))
        r += '000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000' # padding    
        return r            
        
class JobRegistry(object):   
    def __init__(self, f, cmd, no_midstate, real_target, use_old_target=False, scrypt_target=False):
        self.f = f
        self.cmd = cmd # execute this command on new block
        self.scrypt_target = scrypt_target # calculate target for scrypt algorithm instead of sha256
        self.no_midstate = no_midstate # Indicates if calculate midstate for getwork
        self.real_target = real_target # Indicates if real stratum target will be propagated to miners
        self.use_old_target = use_old_target # Use 00000000fffffff...f instead of correct 00000000ffffffff...0 target for really old miners
        self.jobs = []        
        self.last_job = None
        self.extranonce1 = None
        self.extranonce1_bin = None
        self.extranonce2_size = None
        
        self.target = 0
        self.target_hex = ''
        self.difficulty = 1
        self.set_difficulty(1)
        self.target1_hex = self.target_hex
        
        # Relation between merkle and job
        self.merkle_to_job= weakref.WeakValueDictionary()
        
        # Hook for LP broadcasts
        self.on_block = defer.Deferred()

    def execute_cmd(self, prevhash):
        if self.cmd:
            return subprocess.Popen(self.cmd.replace('%s', prevhash), shell=True)

    def set_extranonce(self, extranonce1, extranonce2_size):
        self.extranonce2_size = extranonce2_size
        self.extranonce1_bin = binascii.unhexlify(extranonce1)
        
    def set_difficulty(self, new_difficulty):
        if self.scrypt_target:
            dif1 = 0x0000ffff00000000000000000000000000000000000000000000000000000000
        else:
            dif1 = 0x00000000ffff0000000000000000000000000000000000000000000000000000
        self.target = int(dif1 / new_difficulty)
        self.target_hex = binascii.hexlify(utils.uint256_to_str(self.target))
        self.difficulty = new_difficulty
        
    def build_full_extranonce(self, extranonce2):
        '''Join extranonce1 and extranonce2 together while padding
        extranonce2 length to extranonce2_size (provided by server).'''        
        return self.extranonce1_bin + self.extranonce2_padding(extranonce2)

    def extranonce2_padding(self, extranonce2):
        '''Return extranonce2 with padding bytes'''

        if not self.extranonce2_size:
            raise Exception("Extranonce2_size isn't set yet")
        
        extranonce2_bin = struct.pack('>I', extranonce2)
        missing_len = self.extranonce2_size - len(extranonce2_bin)
        
        if missing_len < 0:
            # extranonce2 is too long, we should print warning on console,
            # but try to shorten extranonce2 
            log.info("Extranonce size mismatch. Please report this error to pool operator!")
            return extranonce2_bin[abs(missing_len):]

        # This is probably more common situation, but it is perfectly
        # safe to add whitespaces
        return '\x00' * missing_len + extranonce2_bin 
    
    def add_template(self, template, clean_jobs):
        if clean_jobs:
            # Pool asked us to stop submitting shares from previous jobs
            self.jobs = []
            
        self.jobs.append(template)
        self.last_job = template
                
        if clean_jobs:
            # Force miners to reload jobs
            on_block = self.on_block
            self.on_block = defer.Deferred()
            on_block.callback(True)
    
            # blocknotify-compatible call
            self.execute_cmd(template.prevhash)
          
    def register_merkle(self, job, merkle_hash, extranonce2):
        # merkle_to_job is weak-ref, so it is cleaned up automatically
        # when job is dropped
        self.merkle_to_job[merkle_hash] = job
        job.merkle_to_extranonce2[merkle_hash] = extranonce2
        
    def get_job_from_header(self, header):
        '''Lookup for job and extranonce2 used for given blockheader (in hex)'''
        merkle_hash = header[72:136].lower()
        job = self.merkle_to_job[merkle_hash]
        extranonce2 = job.merkle_to_extranonce2[merkle_hash]
        return (job, extranonce2)
        
    def getwork(self, no_midstate=True):
        '''Miner requests for new getwork'''
        
        job = self.last_job # Pick the latest job from pool

        # 1. Increase extranonce2
        extranonce2 = job.increase_extranonce2()
        
        # 2. Build final extranonce
        extranonce = self.build_full_extranonce(extranonce2)
        
        # 3. Put coinbase transaction together
        coinbase_bin = job.build_coinbase(extranonce)
        
        # 4. Calculate coinbase hash
        coinbase_hash = utils.doublesha(coinbase_bin)
        
        # 5. Calculate merkle root
        merkle_root = binascii.hexlify(utils.reverse_hash(job.build_merkle_root(coinbase_hash)))
                
        # 6. Generate current ntime
        ntime = int(time.time()) + job.ntime_delta
        
        # 7. Serialize header
        block_header = job.serialize_header(merkle_root, ntime, 0)

        # 8. Register job params
        self.register_merkle(job, merkle_root, extranonce2)
        
        # 9. Prepare hash1, calculate midstate and fill the response object
        header_bin = binascii.unhexlify(block_header)[:64]
        hash1 = "00000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000010000"

        result = {'data': block_header,
                'hash1': hash1}
        
        if self.use_old_target:
            result['target'] = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000'
        elif self.real_target:
            result['target'] = self.target_hex
        else:
            result['target'] = self.target1_hex
    
        if calculateMidstate and not (no_midstate or self.no_midstate):
            # Midstate module not found or disabled
            result['midstate'] = binascii.hexlify(calculateMidstate(header_bin))
            
        return result            
        
    def submit(self, header, worker_name):            
        # Drop unused padding
        header = header[:160]

        # 1. Check if blockheader meets requested difficulty
        header_bin = binascii.unhexlify(header[:160])
        rev = ''.join([ header_bin[i*4:i*4+4][::-1] for i in range(0, 20) ])
        hash_bin = utils.doublesha(rev)
        block_hash = ''.join([ hash_bin[i*4:i*4+4][::-1] for i in range(0, 8) ])
        
        #log.info('!!! %s' % header[:160])
        log.info("Submitting %s" % utils.format_hash(binascii.hexlify(block_hash)))
        
        if utils.uint256_from_str(hash_bin) > self.target:
            log.debug("Share is below expected target")
            return True
        
        # 2. Lookup for job and extranonce used for creating given block header
        try:
            (job, extranonce2) = self.get_job_from_header(header)
        except KeyError:
            log.info("Job not found")
            return False

        # 3. Format extranonce2 to hex string
        extranonce2_hex = binascii.hexlify(self.extranonce2_padding(extranonce2))

        # 4. Parse ntime and nonce from header
        ntimepos = 17*8 # 17th integer in datastring
        noncepos = 19*8 # 19th integer in datastring       
        ntime = header[ntimepos:ntimepos+8] 
        nonce = header[noncepos:noncepos+8]
            
        # 5. Submit share to the pool
        return self.f.rpc('mining.submit', [worker_name, job.job_id, extranonce2_hex, ntime, nonce])

########NEW FILE########
__FILENAME__ = midstate
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

# Some SHA-256 constants...
K = [
     0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
     0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
     0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
     0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
     0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
     0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
     0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
     0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
     0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
     0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
     0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ]

A0 = 0x6a09e667
B0 = 0xbb67ae85
C0 = 0x3c6ef372
D0 = 0xa54ff53a
E0 = 0x510e527f
F0 = 0x9b05688c
G0 = 0x1f83d9ab
H0 = 0x5be0cd19

def rotateright(i,p):
    """i>>>p"""
    p &= 0x1F # p mod 32
    return i>>p | ((i<<(32-p)) & 0xFFFFFFFF)

def addu32(*i):
    return sum(list(i))&0xFFFFFFFF

def calculateMidstate(data, state=None, rounds=None):
    """Given a 512-bit (64-byte) block of (little-endian byteswapped) data,
    calculate a Bitcoin-style midstate. (That is, if SHA-256 were little-endian
    and only hashed the first block of input.)
    """
    if len(data) != 64:
        raise ValueError('data must be 64 bytes long')

    w = list(struct.unpack('<IIIIIIIIIIIIIIII', data))

    if state is not None:
        if len(state) != 32:
            raise ValueError('state must be 32 bytes long')
        a,b,c,d,e,f,g,h = struct.unpack('<IIIIIIII', state)
    else:
        a = A0
        b = B0
        c = C0
        d = D0
        e = E0
        f = F0
        g = G0
        h = H0

    consts = K if rounds is None else K[:rounds]
    for k in consts:
        s0 = rotateright(a,2) ^ rotateright(a,13) ^ rotateright(a,22)
        s1 = rotateright(e,6) ^ rotateright(e,11) ^ rotateright(e,25)
        ma = (a&b) ^ (a&c) ^ (b&c)
        ch = (e&f) ^ ((~e)&g)

        h = addu32(h,w[0],k,ch,s1)
        d = addu32(d,h)
        h = addu32(h,ma,s0)

        a,b,c,d,e,f,g,h = h,a,b,c,d,e,f,g

        s0 = rotateright(w[1],7) ^ rotateright(w[1],18) ^ (w[1] >> 3)
        s1 = rotateright(w[14],17) ^ rotateright(w[14],19) ^ (w[14] >> 10)
        w.append(addu32(w[0], s0, w[9], s1))
        w.pop(0)

    if rounds is None:
        a = addu32(a, A0)
        b = addu32(b, B0)
        c = addu32(c, C0)
        d = addu32(d, D0)
        e = addu32(e, E0)
        f = addu32(f, F0)
        g = addu32(g, G0)
        h = addu32(h, H0)

    return struct.pack('<IIIIIIII', a, b, c, d, e, f, g, h)
########NEW FILE########
__FILENAME__ = multicast_responder
import json
from twisted.internet.protocol import DatagramProtocol

import stratum.logger
log = stratum.logger.get_logger('proxy')

class MulticastResponder(DatagramProtocol):
    def __init__(self, pool_host, stratum_port, getwork_port):
        # Upstream Stratum host/port
        # Used for identifying the pool which we're connected to.
        # Some load balancing strategies can change the host/port
        # during the mining session (by mining.reconnect()), but this points
        # to initial host/port provided by user on cmdline or by X-Stratum 
        self.pool_host = pool_host
        
        self.stratum_port = stratum_port
        self.getwork_port = getwork_port
        
    def startProtocol(self):        
        # 239.0.0.0/8 are for private use within an organization
        self.transport.joinGroup("239.3.3.3")
        self.transport.setTTL(5)

    def writeResponse(self, address, msg_id, result, error=None):
        self.transport.write(json.dumps({"id": msg_id, "result": result, "error": error}), address)
        
    def datagramReceived(self, datagram, address):
        log.info("Received local discovery request from %s:%d" % address)
        
        try:
            data = json.loads(datagram)
        except:
            # Skip response if datagram is not parsable
            log.error("Unparsable datagram")
            return
        
        msg_id = data.get('id')
        msg_method = data.get('method')
        #msg_params = data.get('params')
        
        if msg_method == 'mining.get_upstream':
            self.writeResponse(address, msg_id, (self.pool_host, self.stratum_port, self.getwork_port))
########NEW FILE########
__FILENAME__ = stratum_listener
import time
import binascii
import struct

from twisted.internet import defer

from stratum.services import GenericService
from stratum.pubsub import Pubsub, Subscription
from stratum.custom_exceptions import ServiceException, RemoteServiceException

from jobs import JobRegistry

import stratum.logger
log = stratum.logger.get_logger('proxy')

def var_int(i):
    if i <= 0xff:
        return struct.pack('>B', i)
    elif i <= 0xffff:
        return struct.pack('>H', i)
    raise Exception("number is too big")

class UpstreamServiceException(ServiceException):
    code = -2

class SubmitException(ServiceException):
    code = -2

class DifficultySubscription(Subscription):
    event = 'mining.set_difficulty'
    difficulty = 1
    
    @classmethod
    def on_new_difficulty(cls, new_difficulty):
        cls.difficulty = new_difficulty
        cls.emit(new_difficulty)
    
    def after_subscribe(self, *args):
        self.emit_single(self.difficulty)
        
class MiningSubscription(Subscription):
    '''This subscription object implements
    logic for broadcasting new jobs to the clients.'''
    
    event = 'mining.notify'
    
    last_broadcast = None
    
    @classmethod
    def disconnect_all(cls):
        for subs in Pubsub.iterate_subscribers(cls.event):
            if subs.connection_ref().transport != None:
                subs.connection_ref().transport.loseConnection()
        
    @classmethod
    def on_template(cls, job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs):
        '''Push new job to subscribed clients'''
        cls.last_broadcast = (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)
        cls.emit(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)
        
    def _finish_after_subscribe(self, result):
        '''Send new job to newly subscribed client'''
        try:        
            (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _) = self.last_broadcast
        except Exception:
            log.error("Template not ready yet")
            return result
        
        self.emit_single(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, True)
        return result
             
    def after_subscribe(self, *args):
        '''This will send new job to the client *after* he receive subscription details.
        on_finish callback solve the issue that job is broadcasted *during*
        the subscription request and client receive messages in wrong order.'''
        self.connection_ref().on_finish.addCallback(self._finish_after_subscribe)
        
class StratumProxyService(GenericService):
    service_type = 'mining'
    service_vendor = 'mining_proxy'
    is_default = True
    
    _f = None # Factory of upstream Stratum connection
    custom_user = None
    custom_password = None
    extranonce1 = None
    extranonce2_size = None
    tail_iterator = 0
    registered_tails= []
    
    @classmethod
    def _set_upstream_factory(cls, f):
        cls._f = f

    @classmethod
    def _set_custom_user(cls, custom_user, custom_password):
        cls.custom_user = custom_user
        cls.custom_password = custom_password
        
    @classmethod
    def _set_extranonce(cls, extranonce1, extranonce2_size):
        cls.extranonce1 = extranonce1
        cls.extranonce2_size = extranonce2_size
        
    @classmethod
    def _get_unused_tail(cls):
        '''Currently adds up to two bytes to extranonce1,
        limiting proxy for up to 65535 connected clients.'''
        
        for _ in range(0, 0xffff):  # 0-65535
            cls.tail_iterator += 1
            cls.tail_iterator %= 0xffff

            # Zero extranonce is reserved for getwork connections
            if cls.tail_iterator == 0:
                cls.tail_iterator += 1

            # var_int throws an exception when input is >= 0xffff
            tail = var_int(cls.tail_iterator)
            tail_len = len(tail)

            if tail not in cls.registered_tails:
                cls.registered_tails.append(tail)
                return (binascii.hexlify(tail), cls.extranonce2_size - tail_len)
            
        raise Exception("Extranonce slots are full, please disconnect some miners!")
    
    def _drop_tail(self, result, tail):
        tail = binascii.unhexlify(tail)
        if tail in self.registered_tails:
            self.registered_tails.remove(tail)
        else:
            log.error("Given extranonce is not registered1")
        return result
            
    @defer.inlineCallbacks
    def authorize(self, worker_name, worker_password, *args):
        if self._f.client == None or not self._f.client.connected:
            yield self._f.on_connect

        if self.custom_user != None:
            # Already subscribed by main()
            defer.returnValue(True)
                        
        result = (yield self._f.rpc('mining.authorize', [worker_name, worker_password]))
        defer.returnValue(result)
    
    @defer.inlineCallbacks
    def subscribe(self, *args):    
        if self._f.client == None or not self._f.client.connected:
            yield self._f.on_connect
            
        if self._f.client == None or not self._f.client.connected:
            raise UpstreamServiceException("Upstream not connected")
         
        if self.extranonce1 == None:
            # This should never happen, because _f.on_connect is fired *after*
            # connection receive mining.subscribe response
            raise UpstreamServiceException("Not subscribed on upstream yet")
        
        (tail, extranonce2_size) = self._get_unused_tail()
        
        session = self.connection_ref().get_session()
        session['tail'] = tail
                
        # Remove extranonce from registry when client disconnect
        self.connection_ref().on_disconnect.addCallback(self._drop_tail, tail)

        subs1 = Pubsub.subscribe(self.connection_ref(), DifficultySubscription())[0]
        subs2 = Pubsub.subscribe(self.connection_ref(), MiningSubscription())[0]            
        defer.returnValue(((subs1, subs2),) + (self.extranonce1+tail, extranonce2_size))
            
    @defer.inlineCallbacks
    def submit(self, worker_name, job_id, extranonce2, ntime, nonce, *args):
        if self._f.client == None or not self._f.client.connected:
            raise SubmitException("Upstream not connected")

        session = self.connection_ref().get_session()
        tail = session.get('tail')
        if tail == None:
            raise SubmitException("Connection is not subscribed")

        if self.custom_user:
            worker_name = self.custom_user

        start = time.time()
        
        try:
            result = (yield self._f.rpc('mining.submit', [worker_name, job_id, tail+extranonce2, ntime, nonce]))
        except RemoteServiceException as exc:
            response_time = (time.time() - start) * 1000
            log.info("[%dms] Share from '%s' REJECTED: %s" % (response_time, worker_name, str(exc)))
            raise SubmitException(*exc.args)

        response_time = (time.time() - start) * 1000
        log.info("[%dms] Share from '%s' accepted, diff %d" % (response_time, worker_name, DifficultySubscription.difficulty))
        defer.returnValue(result)

    def get_transactions(self, *args):
        log.warn("mining.get_transactions isn't supported by proxy")
        return []

########NEW FILE########
__FILENAME__ = utils
import hashlib
import struct

from twisted.internet import defer, reactor
from twisted.web import client

import stratum.logger
log = stratum.logger.get_logger('proxy')

def show_message(msg):
    '''Repeatedly displays the message received from
    the server.'''
    log.warning("MESSAGE FROM THE SERVER OPERATOR: %s" % msg)
    log.warning("Restart proxy to discard the message")
    reactor.callLater(10, show_message, msg)

def format_hash(h):
    # For printing hashes to console
    return "%s" % h[:8]
  
def uint256_from_str(s):
    r = 0L
    t = struct.unpack("<IIIIIIII", s[:32])
    for i in xrange(8):
        r += t[i] << (i * 32)
    return r

def uint256_to_str(u):
    rs = ""
    for i in xrange(8):
        rs += struct.pack("<I", u & 0xFFFFFFFFL)
        u >>= 32
    return rs  

def reverse_hash(h):
    return struct.pack('>IIIIIIII', *struct.unpack('>IIIIIIII', h)[::-1])[::-1]
     
def doublesha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

@defer.inlineCallbacks
def detect_stratum(host, port):
    '''Perform getwork request to given
    host/port. If server respond, it will
    try to parse X-Stratum header.
    Not the most elegant code, but it works,
    because Stratum server should close the connection
    when client uses unknown payload.'''
        
    def get_raw_page(url, *args, **kwargs):
        scheme, host, port, path = client._parse(url)
        factory = client.HTTPClientFactory(url, *args, **kwargs)
        reactor.connectTCP(host, port, factory)
        return factory

    def _on_callback(_, d):d.callback(True)
    def _on_errback(_, d): d.callback(True)
    f = get_raw_page('http://%s:%d' % (host, port))
    
    d = defer.Deferred()
    f.deferred.addCallback(_on_callback, d)
    f.deferred.addErrback(_on_errback, d)
    (yield d)
    
    if not f.response_headers:
        # Most likely we're already connecting to Stratum
        defer.returnValue((host, port))
    
    header = f.response_headers.get('x-stratum', None)[0]
    if not header:
        # Looks like pool doesn't support stratum
        defer.returnValue(None) 
    
    if 'stratum+tcp://' not in header:
        # Invalid header or unsupported transport
        defer.returnValue(None)
    
    header = header.replace('stratum+tcp://', '').strip()
    host = header.split(':')    
    
    if len(host) == 1:
        # Port is not specified
        defer.returnValue((host[0], 3333))
    elif len(host) == 2:
        defer.returnValue((host[0], int(host[1])))
    
    defer.returnValue(None)
########NEW FILE########
__FILENAME__ = version
# last stable: 1.5.5
VERSION='1.5.6'

########NEW FILE########
__FILENAME__ = worker_registry
import time

import stratum.logger
log = stratum.logger.get_logger('proxy')

class WorkerRegistry(object):
    def __init__(self, f):
        self.f = f # Factory of Stratum client
        self.clear_authorizations()
        
    def clear_authorizations(self):
        self.authorized = []
        self.unauthorized = []
        self.last_failure = 0
    
    def _on_authorized(self, result, worker_name):
        if result == True:
            self.authorized.append(worker_name)
        else:
            self.unauthorized.append(worker_name)
        return result
    
    def _on_failure(self, failure, worker_name):
        log.exception("Cannot authorize worker '%s'" % worker_name)
        self.last_failure = time.time()
                        
    def authorize(self, worker_name, password):
        if worker_name in self.authorized:
            return True
            
        if worker_name in self.unauthorized and time.time() - self.last_failure < 60:
            # Prevent flooding of mining.authorize() requests 
            log.warning("Authentication of worker '%s' with password '%s' failed, next attempt in few seconds..." % \
                    (worker_name, password))
            return False
        
        d = self.f.rpc('mining.authorize', [worker_name, password])
        d.addCallback(self._on_authorized, worker_name)
        d.addErrback(self._on_failure, worker_name)
        return d
         
    def is_authorized(self, worker_name):
        return (worker_name in self.authorized)
    
    def is_unauthorized(self, worker_name):
        return (worker_name in self.unauthorized)  

########NEW FILE########
__FILENAME__ = mining_proxy
#!/usr/bin/env python
'''
    Stratum mining proxy
    Copyright (C) 2012 Marek Palatinus <slush@satoshilabs.com>
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import argparse
import time
import os
import socket

def parse_args():
    parser = argparse.ArgumentParser(description='This proxy allows you to run getwork-based miners against Stratum mining pool.')
    parser.add_argument('-o', '--host', dest='host', type=str, default='stratum.bitcoin.cz', help='Hostname of Stratum mining pool')
    parser.add_argument('-p', '--port', dest='port', type=int, default=3333, help='Port of Stratum mining pool')
    parser.add_argument('-sh', '--stratum-host', dest='stratum_host', type=str, default='0.0.0.0', help='On which network interface listen for stratum miners. Use "localhost" for listening on internal IP only.')
    parser.add_argument('-sp', '--stratum-port', dest='stratum_port', type=int, default=3333, help='Port on which port listen for stratum miners.')
    parser.add_argument('-oh', '--getwork-host', dest='getwork_host', type=str, default='0.0.0.0', help='On which network interface listen for getwork miners. Use "localhost" for listening on internal IP only.')
    parser.add_argument('-gp', '--getwork-port', dest='getwork_port', type=int, default=8332, help='Port on which port listen for getwork miners. Use another port if you have bitcoind RPC running on this machine already.')
    parser.add_argument('-nm', '--no-midstate', dest='no_midstate', action='store_true', help="Don't compute midstate for getwork. This has outstanding performance boost, but some old miners like Diablo don't work without midstate.")
    parser.add_argument('-rt', '--real-target', dest='real_target', action='store_true', help="Propagate >diff1 target to getwork miners. Some miners work incorrectly with higher difficulty.")
    parser.add_argument('-cl', '--custom-lp', dest='custom_lp', type=str, help='Override URL provided in X-Long-Polling header')
    parser.add_argument('-cs', '--custom-stratum', dest='custom_stratum', type=str, help='Override URL provided in X-Stratum header')
    parser.add_argument('-cu', '--custom-user', dest='custom_user', type=str, help='Use this username for submitting shares')
    parser.add_argument('-cp', '--custom-password', dest='custom_password', type=str, help='Use this password for submitting shares')
    parser.add_argument('--old-target', dest='old_target', action='store_true', help='Provides backward compatible targets for some deprecated getwork miners.')    
    parser.add_argument('--blocknotify', dest='blocknotify_cmd', type=str, default='', help='Execute command when the best block changes (%%s in BLOCKNOTIFY_CMD is replaced by block hash)')
    parser.add_argument('--socks', dest='proxy', type=str, default='', help='Use socks5 proxy for upstream Stratum connection, specify as host:port')
    parser.add_argument('--tor', dest='tor', action='store_true', help='Configure proxy to mine over Tor (requires Tor running on local machine)')
    parser.add_argument('-t', '--test', dest='test', action='store_true', help='Run performance test on startup')    
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Enable low-level debugging messages')
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help='Make output more quiet')
    parser.add_argument('-i', '--pid-file', dest='pid_file', type=str, help='Store process pid to the file')
    parser.add_argument('-l', '--log-file', dest='log_file', type=str, help='Log to specified file')
    parser.add_argument('-st', '--scrypt-target', dest='scrypt_target', action='store_true', help='Calculate targets for scrypt algorithm')
    return parser.parse_args()

from stratum import settings
settings.LOGLEVEL='INFO'

if __name__ == '__main__':
    # We need to parse args & setup Stratum environment
    # before any other imports
    args = parse_args()
    if args.quiet:
        settings.DEBUG = False
        settings.LOGLEVEL = 'WARNING'
    elif args.verbose:
        settings.DEBUG = True
        settings.LOGLEVEL = 'DEBUG'
    if args.log_file:
        settings.LOGFILE = args.log_file
            
from twisted.internet import reactor, defer
from stratum.socket_transport import SocketTransportFactory, SocketTransportClientFactory
from stratum.services import ServiceEventHandler
from twisted.web.server import Site

from mining_libs import stratum_listener
from mining_libs import getwork_listener
from mining_libs import client_service
from mining_libs import jobs
from mining_libs import worker_registry
from mining_libs import multicast_responder
from mining_libs import version
from mining_libs import utils

import stratum.logger
log = stratum.logger.get_logger('proxy')

def on_shutdown(f):
    '''Clean environment properly'''
    log.info("Shutting down proxy...")
    f.is_reconnecting = False # Don't let stratum factory to reconnect again
    
@defer.inlineCallbacks
def on_connect(f, workers, job_registry):
    '''Callback when proxy get connected to the pool'''
    log.info("Connected to Stratum pool at %s:%d" % f.main_host)
    #reactor.callLater(30, f.client.transport.loseConnection)
    
    # Hook to on_connect again
    f.on_connect.addCallback(on_connect, workers, job_registry)
    
    # Every worker have to re-autorize
    workers.clear_authorizations() 
       
    # Subscribe for receiving jobs
    log.info("Subscribing for mining jobs")
    (_, extranonce1, extranonce2_size) = (yield f.rpc('mining.subscribe', []))[:3]
    job_registry.set_extranonce(extranonce1, extranonce2_size)
    stratum_listener.StratumProxyService._set_extranonce(extranonce1, extranonce2_size)
    
    if args.custom_user:
        log.warning("Authorizing custom user %s, password %s" % (args.custom_user, args.custom_password))
        workers.authorize(args.custom_user, args.custom_password)

    defer.returnValue(f)
     
def on_disconnect(f, workers, job_registry):
    '''Callback when proxy get disconnected from the pool'''
    log.info("Disconnected from Stratum pool at %s:%d" % f.main_host)
    f.on_disconnect.addCallback(on_disconnect, workers, job_registry)
    
    stratum_listener.MiningSubscription.disconnect_all()
    
    # Reject miners because we don't give a *job :-)
    workers.clear_authorizations() 
    
    return f              

def test_launcher(result, job_registry):
    def run_test():
        log.info("Running performance self-test...")
        for m in (True, False):
            log.info("Generating with midstate: %s" % m)
            log.info("Example getwork:")
            log.info(job_registry.getwork(no_midstate=not m))

            start = time.time()
            n = 10000
            
            for x in range(n):
                job_registry.getwork(no_midstate=not m)
                
            log.info("%d getworks generated in %.03f sec, %d gw/s" % \
                     (n, time.time() - start, n / (time.time()-start)))
            
        log.info("Test done")
    reactor.callLater(1, run_test)
    return result

def print_deprecation_warning():
    '''Once new version is detected, this method prints deprecation warning every 30 seconds.'''

    log.warning("New proxy version available! Please update!")
    reactor.callLater(30, print_deprecation_warning)

def test_update():
    '''Perform lookup for newer proxy version, on startup and then once a day.
    When new version is found, it starts printing warning message and turned off next checks.'''
 
    GIT_URL='https://raw.github.com/slush0/stratum-mining-proxy/master/mining_libs/version.py'

    import urllib2
    log.warning("Checking for updates...")
    try:
        if version.VERSION not in urllib2.urlopen(GIT_URL).read():
            print_deprecation_warning()
            return # New version already detected, stop periodic checks
    except:
        log.warning("Check failed.")
        
    reactor.callLater(3600*24, test_update)

@defer.inlineCallbacks
def main(args):
    if args.pid_file:
        fp = file(args.pid_file, 'w')
        fp.write(str(os.getpid()))
        fp.close()
    
    if args.port != 3333:
        '''User most likely provided host/port
        for getwork interface. Let's try to detect
        Stratum host/port of given getwork pool.'''
        
        try:
            new_host = (yield utils.detect_stratum(args.host, args.port))
        except:
            log.exception("Stratum host/port autodetection failed")
            new_host = None
            
        if new_host != None:
            args.host = new_host[0]
            args.port = new_host[1]

    log.warning("Stratum proxy version: %s" % version.VERSION)
    # Setup periodic checks for a new version
    test_update()
    
    if args.tor:
        log.warning("Configuring Tor connection")
        args.proxy = '127.0.0.1:9050'
        args.host = 'pool57wkuu5yuhzb.onion'
        args.port = 3333
        
    if args.proxy:
        proxy = args.proxy.split(':')
        if len(proxy) < 2:
            proxy = (proxy, 9050)
        else:
            proxy = (proxy[0], int(proxy[1]))
        log.warning("Using proxy %s:%d" % proxy)
    else:
        proxy = None

    log.warning("Trying to connect to Stratum pool at %s:%d" % (args.host, args.port))        
        
    # Connect to Stratum pool
    f = SocketTransportClientFactory(args.host, args.port,
                debug=args.verbose, proxy=proxy,
                event_handler=client_service.ClientMiningService)
    
    
    job_registry = jobs.JobRegistry(f, cmd=args.blocknotify_cmd, scrypt_target=args.scrypt_target,
                   no_midstate=args.no_midstate, real_target=args.real_target, use_old_target=args.old_target)
    client_service.ClientMiningService.job_registry = job_registry
    client_service.ClientMiningService.reset_timeout()
    
    workers = worker_registry.WorkerRegistry(f)
    f.on_connect.addCallback(on_connect, workers, job_registry)
    f.on_disconnect.addCallback(on_disconnect, workers, job_registry)

    if args.test:
        f.on_connect.addCallback(test_launcher, job_registry)
    
    # Cleanup properly on shutdown
    reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f)

    # Block until proxy connect to the pool
    yield f.on_connect
    
    # Setup getwork listener
    if args.getwork_port > 0:
        conn = reactor.listenTCP(args.getwork_port, Site(getwork_listener.Root(job_registry, workers,
                                                    stratum_host=args.stratum_host, stratum_port=args.stratum_port,
                                                    custom_lp=args.custom_lp, custom_stratum=args.custom_stratum,
                                                    custom_user=args.custom_user, custom_password=args.custom_password)),
                                                    interface=args.getwork_host)

        try:
            conn.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # Enable keepalive packets
            conn.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 60) # Seconds before sending keepalive probes
            conn.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1) # Interval in seconds between keepalive probes
            conn.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 5) # Failed keepalive probles before declaring other end dead
        except:
            pass # Some socket features are not available on all platforms (you can guess which one)
    
    # Setup stratum listener
    if args.stratum_port > 0:
        stratum_listener.StratumProxyService._set_upstream_factory(f)
        stratum_listener.StratumProxyService._set_custom_user(args.custom_user, args.custom_password)
        reactor.listenTCP(args.stratum_port, SocketTransportFactory(debug=False, event_handler=ServiceEventHandler), interface=args.stratum_host)

    # Setup multicast responder
    reactor.listenMulticast(3333, multicast_responder.MulticastResponder((args.host, args.port), args.stratum_port, args.getwork_port), listenMultiple=True)
    
    log.warning("-----------------------------------------------------------------------")
    if args.getwork_host == '0.0.0.0' and args.stratum_host == '0.0.0.0':
        log.warning("PROXY IS LISTENING ON ALL IPs ON PORT %d (stratum) AND %d (getwork)" % (args.stratum_port, args.getwork_port))
    else:
        log.warning("LISTENING FOR MINERS ON http://%s:%d (getwork) and stratum+tcp://%s:%d (stratum)" % \
                 (args.getwork_host, args.getwork_port, args.stratum_host, args.stratum_port))
    log.warning("-----------------------------------------------------------------------")

if __name__ == '__main__':
    main(args)
    reactor.run()

########NEW FILE########
