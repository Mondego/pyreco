__FILENAME__ = autoretry
def autoretry_datastore_timeouts(attempts=5.0, interval=0.1, exponent=2.0):
    """
    Copyright (C)  2009  twitter.com/rcb
    
    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use,
    copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
    
    ======================================================================
    
    This function wraps the AppEngine Datastore API to autoretry 
    datastore timeouts at the lowest accessible level.  

    The benefits of this approach are:

    1. Small Footprint:  Does not monkey with Model internals 
                         which may break in future releases.
    2. Max Performance:  Retrying at this lowest level means 
                         serialization and key formatting is not 
                         needlessly repeated on each retry.
    At initialization time, execute this:
    
    >>> autoretry_datastore_timeouts()
    
    Should only be called once, subsequent calls have no effect.
    
    >>> autoretry_datastore_timeouts() # no effect
    
    Default (5) attempts: .1, .2, .4, .8, 1.6 seconds
    
    Parameters can each be specified as floats.
    
    :param attempts: maximum number of times to retry.
    :param interval: base seconds to sleep between retries.
    :param exponent: rate of exponential back-off.
    """
    
    import time, logging
    from google.appengine.api import apiproxy_stub_map
    from google.appengine.runtime import apiproxy_errors
    from google.appengine.datastore import datastore_pb
    
    attempts = float(attempts)
    interval = float(interval)
    exponent = float(exponent)
    wrapped = apiproxy_stub_map.MakeSyncCall
    errors = {datastore_pb.Error.TIMEOUT:'Timeout',
        datastore_pb.Error.CONCURRENT_TRANSACTION:'TransactionFailedError'}
    
    def wrapper(*args, **kwargs):
        count = 0.0
        while True:
            try:
                return wrapped(*args, **kwargs)
            except apiproxy_errors.ApplicationError, err:
                errno = err.application_error
                if errno not in errors: raise
                sleep = (exponent ** count) * interval
                count += 1.0
                if count > attempts: raise
                msg = "Datastore %s: retry #%d in %s seconds.\n%s"
                vals = ''
                if count == 1.0:
                    vals = '\n'.join([str(a) for a in args])
                logging.warning(msg % (errors[errno], count, sleep, vals))
                time.sleep(sleep)

    setattr(wrapper, '_autoretry_datastore_timeouts', False)
    if getattr(wrapped, '_autoretry_datastore_timeouts', True):
        apiproxy_stub_map.MakeSyncCall = wrapper
########NEW FILE########
__FILENAME__ = django-gae
"""
Running Django on GAE, as per
http://code.google.com/appengine/articles/django.html

Ben Adida
ben@adida.net
2009-07-11
"""

import logging, os

# Django 1.0
from google.appengine.dist import use_library
use_library('django', '1.0')

# Appengine Django Helper
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Force Django to reload its settings.
from django.conf import settings
settings._target = None

# Must set this env var before importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import logging
import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher

def main():
  # Create a Django application for WSGI.
  application = django.core.handlers.wsgi.WSGIHandler()
  
  # if there's initialiation, run it
  import initialization

  # Run the WSGI CGI handler with that application.
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
########NEW FILE########
__FILENAME__ = email_debug
import smtpd
import asyncore
server = smtpd.DebuggingServer(('127.0.0.1', 1025), None)
asyncore.loop()

########NEW FILE########
__FILENAME__ = extract-passwords-for-email
#
# extract voter_id and passwords for a particular email address
# may return many rows, if they all have the same email address
#
# python extract-passwords-for-email.py <election_uuid> <email_address>
#

from django.core.management import setup_environ
import settings, sys, csv

setup_environ(settings)

from helios.models import *

election_uuid = sys.argv[1]
email = sys.argv[2]

csv_output = csv.writer(sys.stdout)

voters = Election.objects.get(uuid=election_uuid).voter_set.filter(voter_email=email)

for voter in voters:
    csv_output.writerow([voter.voter_login_id, voter.voter_password])


########NEW FILE########
__FILENAME__ = fabfile
"""
Deployment Fabric file

A fabric deployment script for Helios that assumes the following:
- locally, development is /web/helios-server
- remotely, a number of production setups 
- remotely, a number of staging setups
- all of these directories are git checkouts that have a proper origin pointer

Other assumptions that should probably change:
- both staging and production run under the same apache instance

Deployment is git and tag based, so:

fab staging_deploy:tag=v3.0.4,hosts="vote.heliosvoting.org"
fab production_deploy:tag=v3.0.5,hosts="vote.heliosvoting.org"

also to get the latest

fab production_deploy:tag=latest,hosts="vote.heliosvoting.org"

IMPORTANT: settings file may need to be tweaked manually
"""

from fabric.api import local, settings, abort, cd, run, sudo
from fabric.contrib.console import confirm

STAGING_SETUP = {
    'root' : "/web/staging/helios-server",
    'celery' : "/etc/init.d/staging-celeryd",
    'dbname' : "helios-staging"
    }

PRODUCTION_SETUPS = [
    {
        'root' : "/web/production/helios-server",
        'celery' : "/etc/init.d/celeryd",
        'dbname' : "helios"
        },
    {
        'root' : "/web/princeton/helios-server",
        'celery' : "/etc/init.d/princeton-celeryd",
        'dbname' : "princeton-helios"
        }
]
        
def run_tests():
    result = local("python manage.py test", capture=False)
    if result.failed:
        abort("tests failed, will not deploy.")

def check_tag(tag, path):
    result = local('git tag')
    if tag not in result.split("\n"):
        abort("no local tag %s" % tag)

    with cd(path):
        run('git pull origin master')
        run('git fetch --tags')
        result = run('git tag')
        if tag not in result.split("\n"):
            abort("no remote tag %s" % tag)

def get_latest(path):
    with cd(path):
        result = run('git pull')
        if result.failed:
            abort("on remote: could not get latest")

        result = run('git submodule init')
        if result.failed:
            abort("on remote: could not init submodules")

        result = run('git submodule update')
        if result.failed:
            abort("on remote: could not update submodules")
    
def checkout_tag(tag, path):
    with cd(path):
        result = run('git checkout %s' % tag)
        if result.failed:
            abort("on remote: could not check out tag %s" % tag)

        result = run('git submodule init')
        if result.failed:
            abort("on remote: could not init submodules")

        result = run('git submodule update')
        if result.failed:
            abort("on remote: could not update submodules")

def migrate_db(path):
    with cd(path):
        result = run('python manage.py migrate')
        if result.failed:
            abort("could not migrate")

def restart_apache():
    result = sudo('/etc/init.d/apache2 restart')
    if result.failed:
        abort("could not restart apache")

def restart_celeryd(path):
    result = sudo('%s restart' % path)
    if result.failed:
        abort("could not restart celeryd - %s " % path)

def deploy(tag, path):
    if tag == 'latest':
        get_latest(path=path)
    else:
        check_tag(tag, path=path)
        checkout_tag(tag, path=path)
    migrate_db(path=path)
    restart_apache()
    
def staging_deploy(tag):
    deploy(tag, path=STAGING_SETUP['root'])
    restart_celeryd(path = STAGING_SETUP['celery'])

def production_deploy(tag):
    production_roots = ",".join([p['root'] for p in PRODUCTION_SETUPS])
    if not confirm("Ready to deploy %s to %s?" % (tag, production_roots)):
        return
    run_tests()
    for prod_setup in PRODUCTION_SETUPS:
        deploy(tag, path = prod_setup['root'])
        restart_celeryd(path = prod_setup['celery'])

########NEW FILE########
__FILENAME__ = counters
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from google.appengine.api import memcache 
from google.appengine.ext import db
from google.appengine.api.datastore import _CurrentTransactionKey
import random

class GeneralCounterShardConfig(db.Model):
  """Tracks the number of shards for each named counter."""
  name = db.StringProperty(required=True)
  num_shards = db.IntegerProperty(required=True, default=20)


class GeneralCounterShard(db.Model):
  """Shards for each named counter"""
  name = db.StringProperty(required=True)
  count = db.IntegerProperty(required=True, default=0)
  
def get_config(name):
  if _CurrentTransactionKey():
    config = GeneralCounterShardConfig.get_by_key_name(name)
    if not config:
      config = GeneralCounterShardConfig(name=name)
      config.put()
    return config
  else:
    return GeneralCounterShardConfig.get_or_insert(name, name=name)
  
def get_count(name):
  """Retrieve the value for a given sharded counter.
  
  Parameters:
    name - The name of the counter  
  """
  total = memcache.get(name)
  if total is None:
    total = 0
    for counter in GeneralCounterShard.all().filter('name = ', name):
      total += counter.count
    memcache.add(name, str(total), 60)
  return total

  
def increment(name):
  """Increment the value for a given sharded counter.
  
  Parameters:
    name - The name of the counter  
  """
  config = get_config(name)
  def txn():
    index = random.randint(0, config.num_shards - 1)
    shard_name = name + str(index)
    counter = GeneralCounterShard.get_by_key_name(shard_name)
    if counter is None:
      counter = GeneralCounterShard(key_name=shard_name, name=name)
    counter.count += 1
    counter.put()
  
  if _CurrentTransactionKey():
    txn()
  else:
    db.run_in_transaction(txn)
    
  memcache.incr(name)

  
def increase_shards(name, num):  
  """Increase the number of shards for a given sharded counter.
  Will never decrease the number of shards.
  
  Parameters:
    name - The name of the counter
    num - How many shards to use
    
  """
  config = get_config(name)
  def txn():
    if config.num_shards < num:
      config.num_shards = num
      config.put()

  if _CurrentTransactionKey():
    txn()
  else:
    db.run_in_transaction(txn)


########NEW FILE########
__FILENAME__ = algs
"""
Crypto Algorithms for the Helios Voting System

FIXME: improve random number generation.

Ben Adida
ben@adida.net
"""

import math, hashlib, logging
import randpool, number

import numtheory

# some utilities
class Utils:
    RAND = randpool.RandomPool()
    
    @classmethod
    def random_seed(cls, data):
        cls.RAND.add_event(data)
    
    @classmethod
    def random_mpz(cls, n_bits):
        low = 2**(n_bits-1)
        high = low * 2
        
        # increment and find a prime
        # return randrange(low, high)

        return number.getRandomNumber(n_bits, cls.RAND.get_bytes)
    
    @classmethod
    def random_mpz_lt(cls, max):
        # return randrange(0, max)
        n_bits = int(math.floor(math.log(max, 2)))
        return (number.getRandomNumber(n_bits, cls.RAND.get_bytes) % max)
    
    @classmethod
    def random_prime(cls, n_bits):
        return number.getPrime(n_bits, cls.RAND.get_bytes)
    
    @classmethod
    def is_prime(cls, mpz):
        #return numtheory.miller_rabin(mpz)
        return number.isPrime(mpz)

    @classmethod
    def xgcd(cls, a, b):
        """
        Euclid's Extended GCD algorithm
        """
        mod = a%b

        if mod == 0:
            return 0,1
        else:
            x,y = cls.xgcd(b, mod)
            return y, x-(y*(a/b))

    @classmethod
    def inverse(cls, mpz, mod):
        # return cls.xgcd(mpz,mod)[0]
        return number.inverse(mpz, mod)
  
    @classmethod
    def random_safe_prime(cls, n_bits):
      p = None
      q = None
      
      while True:
        p = cls.random_prime(n_bits)
        q = (p-1)/2
        if cls.is_prime(q):
          return p

    @classmethod
    def random_special_prime(cls, q_n_bits, p_n_bits):
        p = None
        q = None

        z_n_bits = p_n_bits - q_n_bits

        q = cls.random_prime(q_n_bits)
        
        while True:
            z = cls.random_mpz(z_n_bits)
            p = q*z + 1
            if cls.is_prime(p):
                return p, q, z


class ElGamal:
    def __init__(self):
      self.p = None
      self.q = None
      self.g = None

    @classmethod
    def generate(cls, n_bits):
      """
      generate an El-Gamal environment. Returns an instance
      of ElGamal(), with prime p, group size q, and generator g
      """
      
      EG = ElGamal()
      
      # find a prime p such that (p-1)/2 is prime q
      EG.p = Utils.random_safe_prime(n_bits)

      # q is the order of the group
      # FIXME: not always p-1/2
      EG.q = (EG.p-1)/2
  
      # find g that generates the q-order subgroup
      while True:
        EG.g = Utils.random_mpz_lt(EG.p)
        if pow(EG.g, EG.q, EG.p) == 1:
          break

      return EG

    def generate_keypair(self):
      """
      generates a keypair in the setting
      """
      
      keypair = EGKeyPair()
      keypair.generate(self.p, self.q, self.g)
  
      return keypair
      
    def toJSONDict(self):
      return {'p': str(self.p), 'q': str(self.q), 'g': str(self.g)}
      
    @classmethod
    def fromJSONDict(cls, d):
      eg = cls()
      eg.p = int(d['p'])
      eg.q = int(d['q'])
      eg.g = int(d['g'])
      return eg

class EGKeyPair:
    def __init__(self):
      self.pk = EGPublicKey()
      self.sk = EGSecretKey()

    def generate(self, p, q, g):
      """
      Generate an ElGamal keypair
      """
      self.pk.g = g
      self.pk.p = p
      self.pk.q = q
      
      self.sk.x = Utils.random_mpz_lt(q)
      self.pk.y = pow(g, self.sk.x, p)
      
      self.sk.pk = self.pk

class EGPublicKey:
    def __init__(self):
        self.y = None
        self.p = None
        self.g = None
        self.q = None

    def encrypt_with_r(self, plaintext, r, encode_message= False):
        """
        expecting plaintext.m to be a big integer
        """
        ciphertext = EGCiphertext()
        ciphertext.pk = self

        # make sure m is in the right subgroup
        if encode_message:
          y = plaintext.m + 1
          if pow(y, self.q, self.p) == 1:
            m = y
          else:
            m = -y % self.p
        else:
          m = plaintext.m
        
        ciphertext.alpha = pow(self.g, r, self.p)
        ciphertext.beta = (m * pow(self.y, r, self.p)) % self.p
        
        return ciphertext

    def encrypt_return_r(self, plaintext):
        """
        Encrypt a plaintext and return the randomness just generated and used.
        """
        r = Utils.random_mpz_lt(self.q)
        ciphertext = self.encrypt_with_r(plaintext, r)
        
        return [ciphertext, r]

    def encrypt(self, plaintext):
        """
        Encrypt a plaintext, obscure the randomness.
        """
        return self.encrypt_return_r(plaintext)[0]
        
    def to_dict(self):
        """
        Serialize to dictionary.
        """
        return {'y' : str(self.y), 'p' : str(self.p), 'g' : str(self.g) , 'q' : str(self.q)}

    toJSONDict = to_dict
    
    # quick hack FIXME
    def toJSON(self):
      import utils
      return utils.to_json(self.toJSONDict())
    
    def __mul__(self,other):
      if other == 0 or other == 1:
        return self
        
      # check p and q
      if self.p != other.p or self.q != other.q or self.g != other.g:
        raise Exception("incompatible public keys")
        
      result = EGPublicKey()
      result.p = self.p
      result.q = self.q
      result.g = self.g
      result.y = (self.y * other.y) % result.p
      return result
      
    def verify_sk_proof(self, dlog_proof, challenge_generator = None):
      """
      verify the proof of knowledge of the secret key
      g^response = commitment * y^challenge
      """
      left_side = pow(self.g, dlog_proof.response, self.p)
      right_side = (dlog_proof.commitment * pow(self.y, dlog_proof.challenge, self.p)) % self.p
      
      expected_challenge = challenge_generator(dlog_proof.commitment) % self.q
      
      return ((left_side == right_side) and (dlog_proof.challenge == expected_challenge))

    @classmethod
    def from_dict(cls, d):
        """
        Deserialize from dictionary.
        """
        pk = cls()
        pk.y = int(d['y'])
        pk.p = int(d['p'])
        pk.g = int(d['g'])
        pk.q = int(d['q'])
        return pk
        
    fromJSONDict = from_dict

class EGSecretKey:
    def __init__(self):
        self.x = None
        self.pk = None
    
    def decryption_factor(self, ciphertext):
        """
        provide the decryption factor, not yet inverted because of needed proof
        """
        return pow(ciphertext.alpha, self.x, self.pk.p)

    def decryption_factor_and_proof(self, ciphertext, challenge_generator=None):
        """
        challenge generator is almost certainly
        EG_fiatshamir_challenge_generator
        """
        if not challenge_generator:
            challenge_generator = EG_fiatshamir_challenge_generator

        dec_factor = self.decryption_factor(ciphertext)

        proof = EGZKProof.generate(self.pk.g, ciphertext.alpha, self.x, self.pk.p, self.pk.q, challenge_generator)

        return dec_factor, proof

    def decrypt(self, ciphertext, dec_factor = None, decode_m=False):
        """
        Decrypt a ciphertext. Optional parameter decides whether to encode the message into the proper subgroup.
        """
        if not dec_factor:
            dec_factor = self.decryption_factor(ciphertext)

        m = (Utils.inverse(dec_factor, self.pk.p) * ciphertext.beta) % self.pk.p

        if decode_m:
          # get m back from the q-order subgroup
          if m < self.pk.q:
            y = m
          else:
            y = -m % self.pk.p

          return EGPlaintext(y-1, self.pk)
        else:
          return EGPlaintext(m, self.pk)

    def prove_decryption(self, ciphertext):
        """
        given g, y, alpha, beta/(encoded m), prove equality of discrete log
        with Chaum Pedersen, and that discrete log is x, the secret key.

        Prover sends a=g^w, b=alpha^w for random w
        Challenge c = sha1(a,b) with and b in decimal form
        Prover sends t = w + xc

        Verifier will check that g^t = a * y^c
        and alpha^t = b * beta/m ^ c
        """
        
        m = (Utils.inverse(pow(ciphertext.alpha, self.x, self.pk.p), self.pk.p) * ciphertext.beta) % self.pk.p
        beta_over_m = (ciphertext.beta * Utils.inverse(m, self.pk.p)) % self.pk.p

        # pick a random w
        w = Utils.random_mpz_lt(self.pk.q)
        a = pow(self.pk.g, w, self.pk.p)
        b = pow(ciphertext.alpha, w, self.pk.p)

        c = int(hashlib.sha1(str(a) + "," + str(b)).hexdigest(),16)

        t = (w + self.x * c) % self.pk.q

        return m, {
            'commitment' : {'A' : str(a), 'B': str(b)},
            'challenge' : str(c),
            'response' : str(t)
          }

    def to_dict(self):
        return {'x' : str(self.x), 'public_key' : self.pk.to_dict()}
        
    toJSONDict = to_dict

    def prove_sk(self, challenge_generator):
      """
      Generate a PoK of the secret key
      Prover generates w, a random integer modulo q, and computes commitment = g^w mod p.
      Verifier provides challenge modulo q.
      Prover computes response = w + x*challenge mod q, where x is the secret key.
      """
      w = Utils.random_mpz_lt(self.pk.q)
      commitment = pow(self.pk.g, w, self.pk.p)
      challenge = challenge_generator(commitment) % self.pk.q
      response = (w + (self.x * challenge)) % self.pk.q
      
      return DLogProof(commitment, challenge, response)
      

    @classmethod
    def from_dict(cls, d):
        if not d:
          return None
          
        sk = cls()
        sk.x = int(d['x'])
        if d.has_key('public_key'):
          sk.pk = EGPublicKey.from_dict(d['public_key'])
        else:
          sk.pk = None
        return sk
        
    fromJSONDict = from_dict

class EGPlaintext:
    def __init__(self, m = None, pk = None):
        self.m = m
        self.pk = pk
        
    def to_dict(self):
        return {'m' : self.m}

    @classmethod
    def from_dict(cls, d):
        r = cls()
        r.m = d['m']
        return r
   

class EGCiphertext:
    def __init__(self, alpha=None, beta=None, pk=None):
        self.pk = pk
        self.alpha = alpha
        self.beta = beta

    def __mul__(self,other):
        """
        Homomorphic Multiplication of ciphertexts.
        """
        if type(other) == int and (other == 0 or other == 1):
          return self
          
        if self.pk != other.pk:
          logging.info(self.pk)
          logging.info(other.pk)
          raise Exception('different PKs!')
        
        new = EGCiphertext()
        
        new.pk = self.pk
        new.alpha = (self.alpha * other.alpha) % self.pk.p
        new.beta = (self.beta * other.beta) % self.pk.p

        return new
  
    def reenc_with_r(self, r):
        """
        We would do this homomorphically, except
        that's no good when we do plaintext encoding of 1.
        """
        new_c = EGCiphertext()
        new_c.alpha = (self.alpha * pow(self.pk.g, r, self.pk.p)) % self.pk.p
        new_c.beta = (self.beta * pow(self.pk.y, r, self.pk.p)) % self.pk.p
        new_c.pk = self.pk

        return new_c
    
    def reenc_return_r(self):
        """
        Reencryption with fresh randomness, which is returned.
        """
        r = Utils.random_mpz_lt(self.pk.q)
        new_c = self.reenc_with_r(r)
        return [new_c, r]
    
    def reenc(self):
        """
        Reencryption with fresh randomness, which is kept obscured (unlikely to be useful.)
        """
        return self.reenc_return_r()[0]
    
    def __eq__(self, other):
      """
      Check for ciphertext equality.
      """
      if other == None:
        return False
        
      return (self.alpha == other.alpha and self.beta == other.beta)
    
    def generate_encryption_proof(self, plaintext, randomness, challenge_generator):
      """
      Generate the disjunctive encryption proof of encryption
      """
      # random W
      w = Utils.random_mpz_lt(self.pk.q)

      # build the proof
      proof = EGZKProof()

      # compute A=g^w, B=y^w
      proof.commitment['A'] = pow(self.pk.g, w, self.pk.p)
      proof.commitment['B'] = pow(self.pk.y, w, self.pk.p)

      # generate challenge
      proof.challenge = challenge_generator(proof.commitment);

      # Compute response = w + randomness * challenge
      proof.response = (w + (randomness * proof.challenge)) % self.pk.q;

      return proof;
      
    def simulate_encryption_proof(self, plaintext, challenge=None):
      # generate a random challenge if not provided
      if not challenge:
        challenge = Utils.random_mpz_lt(self.pk.q)
        
      proof = EGZKProof()
      proof.challenge = challenge

      # compute beta/plaintext, the completion of the DH tuple
      beta_over_plaintext =  (self.beta * Utils.inverse(plaintext.m, self.pk.p)) % self.pk.p
      
      # random response, does not even need to depend on the challenge
      proof.response = Utils.random_mpz_lt(self.pk.q);

      # now we compute A and B
      proof.commitment['A'] = (Utils.inverse(pow(self.alpha, proof.challenge, self.pk.p), self.pk.p) * pow(self.pk.g, proof.response, self.pk.p)) % self.pk.p
      proof.commitment['B'] = (Utils.inverse(pow(beta_over_plaintext, proof.challenge, self.pk.p), self.pk.p) * pow(self.pk.y, proof.response, self.pk.p)) % self.pk.p

      return proof
    
    def generate_disjunctive_encryption_proof(self, plaintexts, real_index, randomness, challenge_generator):
      # note how the interface is as such so that the result does not reveal which is the real proof.

      proofs = [None for p in plaintexts]

      # go through all plaintexts and simulate the ones that must be simulated.
      for p_num in range(len(plaintexts)):
        if p_num != real_index:
          proofs[p_num] = self.simulate_encryption_proof(plaintexts[p_num])

      # the function that generates the challenge
      def real_challenge_generator(commitment):
        # set up the partial real proof so we're ready to get the hash
        proofs[real_index] = EGZKProof()
        proofs[real_index].commitment = commitment

        # get the commitments in a list and generate the whole disjunctive challenge
        commitments = [p.commitment for p in proofs]
        disjunctive_challenge = challenge_generator(commitments);

        # now we must subtract all of the other challenges from this challenge.
        real_challenge = disjunctive_challenge
        for p_num in range(len(proofs)):
          if p_num != real_index:
            real_challenge = real_challenge - proofs[p_num].challenge

        # make sure we mod q, the exponent modulus
        return real_challenge % self.pk.q
        
      # do the real proof
      real_proof = self.generate_encryption_proof(plaintexts[real_index], randomness, real_challenge_generator)

      # set the real proof
      proofs[real_index] = real_proof

      return EGZKDisjunctiveProof(proofs)
      
    def verify_encryption_proof(self, plaintext, proof):
      """
      Checks for the DDH tuple g, y, alpha, beta/plaintext.
      (PoK of randomness r.)
      
      Proof contains commitment = {A, B}, challenge, response
      """
      
      # check that g^response = A * alpha^challenge
      first_check = (pow(self.pk.g, proof.response, self.pk.p) == ((pow(self.alpha, proof.challenge, self.pk.p) * proof.commitment['A']) % self.pk.p))
      
      # check that y^response = B * (beta/m)^challenge
      beta_over_m = (self.beta * Utils.inverse(plaintext.m, self.pk.p)) % self.pk.p
      second_check = (pow(self.pk.y, proof.response, self.pk.p) == ((pow(beta_over_m, proof.challenge, self.pk.p) * proof.commitment['B']) % self.pk.p))
      
      # print "1,2: %s %s " % (first_check, second_check)
      return (first_check and second_check)
    
    def verify_disjunctive_encryption_proof(self, plaintexts, proof, challenge_generator):
      """
      plaintexts and proofs are all lists of equal length, with matching.
      
      overall_challenge is what all of the challenges combined should yield.
      """
      if len(plaintexts) != len(proof.proofs):
        print("bad number of proofs (expected %s, found %s)" % (len(plaintexts), len(proof.proofs)))
        return False

      for i in range(len(plaintexts)):
        # if a proof fails, stop right there
        if not self.verify_encryption_proof(plaintexts[i], proof.proofs[i]):
          print "bad proof %s, %s, %s" % (i, plaintexts[i], proof.proofs[i])
          return False
          
      # logging.info("made it past the two encryption proofs")
          
      # check the overall challenge
      return (challenge_generator([p.commitment for p in proof.proofs]) == (sum([p.challenge for p in proof.proofs]) % self.pk.q))
      
    def verify_decryption_proof(self, plaintext, proof):
      """
      Checks for the DDH tuple g, alpha, y, beta/plaintext
      (PoK of secret key x.)
      """
      return False
      
    def verify_decryption_factor(self, dec_factor, dec_proof, public_key):
      """
      when a ciphertext is decrypted by a dec factor, the proof needs to be checked
      """
      pass
      
    def decrypt(self, decryption_factors, public_key):
      """
      decrypt a ciphertext given a list of decryption factors (from multiple trustees)
      For now, no support for threshold
      """
      running_decryption = self.beta
      for dec_factor in decryption_factors:
        running_decryption = (running_decryption * Utils.inverse(dec_factor, public_key.p)) % public_key.p
        
      return running_decryption

    def to_dict(self):
        return {'alpha': str(self.alpha), 'beta': str(self.beta)}

    toJSONDict= to_dict

    def to_string(self):
        return "%s,%s" % (self.alpha, self.beta)
    
    @classmethod
    def from_dict(cls, d, pk = None):
        result = cls()
        result.alpha = int(d['alpha'])
        result.beta = int(d['beta'])
        result.pk = pk
        return result
        
    fromJSONDict = from_dict
    
    @classmethod
    def from_string(cls, str):
        """
        expects alpha,beta
        """
        split = str.split(",")
        return cls.from_dict({'alpha' : split[0], 'beta' : split[1]})

class EGZKProof(object):
  def __init__(self):
    self.commitment = {'A':None, 'B':None}
    self.challenge = None
    self.response = None
  
  @classmethod
  def generate(cls, little_g, little_h, x, p, q, challenge_generator):
      """
      generate a DDH tuple proof, where challenge generator is
      almost certainly EG_fiatshamir_challenge_generator
      """

      # generate random w
      w = Utils.random_mpz_lt(q)
      
      # create proof instance
      proof = cls()

      # compute A = little_g^w, B=little_h^w
      proof.commitment['A'] = pow(little_g, w, p)
      proof.commitment['B'] = pow(little_h, w, p)

      # get challenge
      proof.challenge = challenge_generator(proof.commitment)

      # compute response
      proof.response = (w + (x * proof.challenge)) % q

      # return proof
      return proof
      
  @classmethod
  def from_dict(cls, d):
    p = cls()
    p.commitment = {'A': int(d['commitment']['A']), 'B': int(d['commitment']['B'])}
    p.challenge = int(d['challenge'])
    p.response = int(d['response'])
    return p
    
  fromJSONDict = from_dict
    
  def to_dict(self):
    return {
      'commitment' : {'A' : str(self.commitment['A']), 'B' : str(self.commitment['B'])},
      'challenge': str(self.challenge),
      'response': str(self.response)
    }

  def verify(self, little_g, little_h, big_g, big_h, p, q, challenge_generator=None):
    """
    Verify a DH tuple proof
    """
    # check that little_g^response = A * big_g^challenge
    first_check = (pow(little_g, self.response, p) == ((pow(big_g, self.challenge, p) * self.commitment['A']) % p))
    
    # check that little_h^response = B * big_h^challenge
    second_check = (pow(little_h, self.response, p) == ((pow(big_h, self.challenge, p) * self.commitment['B']) % p))

    # check the challenge?
    third_check = True
    
    if challenge_generator:
      third_check = (self.challenge == challenge_generator(self.commitment))

    return (first_check and second_check and third_check)
  
  toJSONDict = to_dict
  
class EGZKDisjunctiveProof:
  def __init__(self, proofs = None):
    self.proofs = proofs
  
  @classmethod
  def from_dict(cls, d):
    dp = cls()
    dp.proofs = [EGZKProof.from_dict(p) for p in d]
    return dp
    
  def to_dict(self):
    return [p.to_dict() for p in self.proofs]
  
  toJSONDict = to_dict

class DLogProof(object):
  def __init__(self, commitment, challenge, response):
    self.commitment = commitment
    self.challenge = challenge
    self.response = response
    
  def to_dict(self):
    return {'challenge': str(self.challenge), 'commitment': str(self.commitment), 'response' : str(self.response)}
  
  toJSONDict = to_dict
  
  @classmethod
  def from_dict(cls, d):
    dlp = cls(int(d['commitment']), int(d['challenge']), int(d['response']))
    return dlp
    
  fromJSONDict = from_dict

def EG_disjunctive_challenge_generator(commitments):
  array_to_hash = []
  for commitment in commitments:
    array_to_hash.append(str(commitment['A']))
    array_to_hash.append(str(commitment['B']))

  string_to_hash = ",".join(array_to_hash)
  return int(hashlib.sha1(string_to_hash).hexdigest(),16)
  
# a challenge generator for Fiat-Shamir with A,B commitment
def EG_fiatshamir_challenge_generator(commitment):
  return EG_disjunctive_challenge_generator([commitment])

def DLog_challenge_generator(commitment):
  string_to_hash = str(commitment)
  return int(hashlib.sha1(string_to_hash).hexdigest(),16)


########NEW FILE########
__FILENAME__ = electionalgs
"""
Election-specific algorithms for Helios

Ben Adida
2008-08-30
"""

import algs
import logging
import utils
import uuid
import datetime

class HeliosObject(object):
  """
  A base class to ease serialization and de-serialization
  crypto objects are kept as full-blown crypto objects, serialized to jsonobjects on the way out
  and deserialized from jsonobjects on the way in
  """
  FIELDS = []
  JSON_FIELDS = None

  def __init__(self, **kwargs):
    self.set_from_args(**kwargs)
    
    # generate uuid if need be
    if 'uuid' in self.FIELDS and (not hasattr(self, 'uuid') or self.uuid == None):
      self.uuid = str(uuid.uuid4())
      
  def set_from_args(self, **kwargs):
    for f in self.FIELDS:
      if kwargs.has_key(f):
        new_val = self.process_value_in(f, kwargs[f])
        setattr(self, f, new_val)
      else:
        setattr(self, f, None)
        
  def set_from_other_object(self, o):
    for f in self.FIELDS:
      if hasattr(o, f):
        setattr(self, f, self.process_value_in(f, getattr(o,f)))
      else:
        setattr(self, f, None)
    
  def toJSON(self):
    return utils.to_json(self.toJSONDict())
    
  def toJSONDict(self, alternate_fields=None):
    val = {}
    for f in (alternate_fields or self.JSON_FIELDS or self.FIELDS):
      val[f] = self.process_value_out(f, getattr(self, f))
    return val
    
  @classmethod
  def fromJSONDict(cls, d):
    # go through the keys and fix them
    new_d = {}
    for k in d.keys():
      new_d[str(k)] = d[k]
      
    return cls(**new_d)
    
  @classmethod
  def fromOtherObject(cls, o):
    obj = cls()
    obj.set_from_other_object(o)
    return obj
  
  def toOtherObject(self, o):
    for f in self.FIELDS:
      # FIXME: why isn't this working?
      if hasattr(o, f):
        # BIG HAMMER
        try:
          setattr(o, f, self.process_value_out(f, getattr(self,f)))    
        except:
          pass

  @property
  def hash(self):
    s = utils.to_json(self.toJSONDict())
    return utils.hash_b64(s)
    
  def process_value_in(self, field_name, field_value):
    """
    process some fields on the way into the object
    """
    if field_value == None:
      return None
      
    val = self._process_value_in(field_name, field_value)
    if val != None:
      return val
    else:
      return field_value
    
  def _process_value_in(self, field_name, field_value):
    return None

  def process_value_out(self, field_name, field_value):
    """
    process some fields on the way out of the object
    """
    if field_value == None:
      return None
      
    val = self._process_value_out(field_name, field_value)
    if val != None:
      return val
    else:
      return field_value
  
  def _process_value_out(self, field_name, field_value):
    return None
    
  def __eq__(self, other):
    if not hasattr(self, 'uuid'):
      return super(HeliosObject,self) == other
    
    return other != None and self.uuid == other.uuid
  
class EncryptedAnswer(HeliosObject):
  """
  An encrypted answer to a single election question
  """

  FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']

  # FIXME: remove this constructor and use only named-var constructor from HeliosObject
  def __init__(self, choices=None, individual_proofs=None, overall_proof=None, randomness=None, answer=None):
    self.choices = choices
    self.individual_proofs = individual_proofs
    self.overall_proof = overall_proof
    self.randomness = randomness
    self.answer = answer
    
  @classmethod
  def generate_plaintexts(cls, pk, min=0, max=1):
    plaintexts = []
    running_product = 1
    
    # run the product up to the min
    for i in range(max+1):
      # if we're in the range, add it to the array
      if i >= min:
        plaintexts.append(algs.EGPlaintext(running_product, pk))
        
      # next value in running product
      running_product = (running_product * pk.g) % pk.p
      
    return plaintexts

  def verify_plaintexts_and_randomness(self, pk):
    """
    this applies only if the explicit answers and randomness factors are given
    we do not verify the proofs here, that is the verify() method
    """
    if not hasattr(self, 'answer'):
      return False
    
    for choice_num in range(len(self.choices)):
      choice = self.choices[choice_num]
      choice.pk = pk
      
      # redo the encryption
      # WORK HERE (paste from below encryption)
    
    return False
    
  def verify(self, pk, min=0, max=1):
    possible_plaintexts = self.generate_plaintexts(pk)
    homomorphic_sum = 0
      
    for choice_num in range(len(self.choices)):
      choice = self.choices[choice_num]
      choice.pk = pk
      individual_proof = self.individual_proofs[choice_num]
      
      # verify the proof on the encryption of that choice
      if not choice.verify_disjunctive_encryption_proof(possible_plaintexts, individual_proof, algs.EG_disjunctive_challenge_generator):
        return False

      # compute homomorphic sum if needed
      if max != None:
        homomorphic_sum = choice * homomorphic_sum
    
    if max != None:
      # determine possible plaintexts for the sum
      sum_possible_plaintexts = self.generate_plaintexts(pk, min=min, max=max)

      # verify the sum
      return homomorphic_sum.verify_disjunctive_encryption_proof(sum_possible_plaintexts, self.overall_proof, algs.EG_disjunctive_challenge_generator)
    else:
      # approval voting, no need for overall proof verification
      return True
        
  def toJSONDict(self, with_randomness=False):
    value = {
      'choices': [c.to_dict() for c in self.choices],
      'individual_proofs' : [p.to_dict() for p in self.individual_proofs]
    }
    
    if self.overall_proof:
      value['overall_proof'] = self.overall_proof.to_dict()
    else:
      value['overall_proof'] = None

    if with_randomness:
      value['randomness'] = [str(r) for r in self.randomness]
      value['answer'] = self.answer
    
    return value
    
  @classmethod
  def fromJSONDict(cls, d, pk=None):
    ea = cls()

    ea.choices = [algs.EGCiphertext.from_dict(c, pk) for c in d['choices']]
    ea.individual_proofs = [algs.EGZKDisjunctiveProof.from_dict(p) for p in d['individual_proofs']]
    
    if d['overall_proof']:
      ea.overall_proof = algs.EGZKDisjunctiveProof.from_dict(d['overall_proof'])
    else:
      ea.overall_proof = None

    if d.has_key('randomness'):
      ea.randomness = [int(r) for r in d['randomness']]
      ea.answer = d['answer']
      
    return ea

  @classmethod
  def fromElectionAndAnswer(cls, election, question_num, answer_indexes):
    """
    Given an election, a question number, and a list of answers to that question
    in the form of an array of 0-based indexes into the answer array,
    produce an EncryptedAnswer that works.
    """
    question = election.questions[question_num]
    answers = question['answers']
    pk = election.public_key
    
    # initialize choices, individual proofs, randomness and overall proof
    choices = [None for a in range(len(answers))]
    individual_proofs = [None for a in range(len(answers))]
    overall_proof = None
    randomness = [None for a in range(len(answers))]
    
    # possible plaintexts [0, 1]
    plaintexts = cls.generate_plaintexts(pk)
    
    # keep track of number of options selected.
    num_selected_answers = 0;
    
    # homomorphic sum of all
    homomorphic_sum = 0
    randomness_sum = 0

    # min and max for number of answers, useful later
    min_answers = 0
    if question.has_key('min'):
      min_answers = question['min']
    max_answers = question['max']

    # go through each possible answer and encrypt either a g^0 or a g^1.
    for answer_num in range(len(answers)):
      plaintext_index = 0
      
      # assuming a list of answers
      if answer_num in answer_indexes:
        plaintext_index = 1
        num_selected_answers += 1

      # randomness and encryption
      randomness[answer_num] = algs.Utils.random_mpz_lt(pk.q)
      choices[answer_num] = pk.encrypt_with_r(plaintexts[plaintext_index], randomness[answer_num])
      
      # generate proof
      individual_proofs[answer_num] = choices[answer_num].generate_disjunctive_encryption_proof(plaintexts, plaintext_index, 
                                                randomness[answer_num], algs.EG_disjunctive_challenge_generator)
                                                
      # sum things up homomorphically if needed
      if max_answers != None:
        homomorphic_sum = choices[answer_num] * homomorphic_sum
        randomness_sum = (randomness_sum + randomness[answer_num]) % pk.q

    # prove that the sum is 0 or 1 (can be "blank vote" for this answer)
    # num_selected_answers is 0 or 1, which is the index into the plaintext that is actually encoded
    
    if num_selected_answers < min_answers:
      raise Exception("Need to select at least %s answer(s)" % min_answers)
    
    if max_answers != None:
      sum_plaintexts = cls.generate_plaintexts(pk, min=min_answers, max=max_answers)
    
      # need to subtract the min from the offset
      overall_proof = homomorphic_sum.generate_disjunctive_encryption_proof(sum_plaintexts, num_selected_answers - min_answers, randomness_sum, algs.EG_disjunctive_challenge_generator);
    else:
      # approval voting
      overall_proof = None
    
    return cls(choices, individual_proofs, overall_proof, randomness, answer_indexes)
    
class EncryptedVote(HeliosObject):
  """
  An encrypted ballot
  """
  FIELDS = ['encrypted_answers', 'election_hash', 'election_uuid']
  
  def verify(self, election):
    # right number of answers
    if len(self.encrypted_answers) != len(election.questions):
      return False
    
    # check hash
    if self.election_hash != election.hash:
      # print "%s / %s " % (self.election_hash, election.hash)
      return False
      
    # check ID
    if self.election_uuid != election.uuid:
      return False
      
    # check proofs on all of answers
    for question_num in range(len(election.questions)):
      ea = self.encrypted_answers[question_num]

      question = election.questions[question_num]
      min_answers = 0
      if question.has_key('min'):
        min_answers = question['min']
        
      if not ea.verify(election.public_key, min=min_answers, max=question['max']):
        return False
        
    return True
    
  def get_hash(self):
    return utils.hash_b64(utils.to_json(self.toJSONDict()))
    
  def toJSONDict(self, with_randomness=False):
    return {
      'answers': [a.toJSONDict(with_randomness) for a in self.encrypted_answers],
      'election_hash': self.election_hash,
      'election_uuid': self.election_uuid
    }
    
  @classmethod
  def fromJSONDict(cls, d, pk=None):
    ev = cls()

    ev.encrypted_answers = [EncryptedAnswer.fromJSONDict(ea, pk) for ea in d['answers']]
    ev.election_hash = d['election_hash']
    ev.election_uuid = d['election_uuid']

    return ev
    
  @classmethod
  def fromElectionAndAnswers(cls, election, answers):
    pk = election.public_key

    # each answer is an index into the answer array
    encrypted_answers = [EncryptedAnswer.fromElectionAndAnswer(election, answer_num, answers[answer_num]) for answer_num in range(len(answers))]
    return cls(encrypted_answers=encrypted_answers, election_hash=election.hash, election_uuid = election.uuid)
    

def one_question_winner(question, result, num_cast_votes):
  """
  determining the winner for one question
  """
  # sort the answers , keep track of the index
  counts = sorted(enumerate(result), key=lambda(x): x[1])
  counts.reverse()

  # if there's a max > 1, we assume that the top MAX win
  if question['max'] > 1:
    return [c[0] for c in counts[:question['max']]]

  # if max = 1, then depends on absolute or relative
  if question['result_type'] == 'absolute':
    if counts[0][1] >=  (num_cast_votes/2 + 1):
      return [counts[0][0]]
    else:
      return []

  if question['result_type'] == 'relative':
    return [counts[0][0]]    

class Election(HeliosObject):
  
  FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
      'frozen_at', 'public_key', 'private_key', 'cast_url', 'result', 'result_proof', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at', 'election_type']

  JSON_FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
      'frozen_at', 'public_key', 'cast_url', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']

  # need to add in v3.1: use_advanced_audit_features, election_type, and probably more

  def init_tally(self):
    return Tally(election=self)
        
  def _process_value_in(self, field_name, field_value):
    if field_name == 'frozen_at' or field_name == 'voting_starts_at' or field_name == 'voting_ends_at':
      if type(field_value) == str or type(field_value) == unicode:
        return datetime.datetime.strptime(field_value, '%Y-%m-%d %H:%M:%S')
      
    if field_name == 'public_key':
      return algs.EGPublicKey.fromJSONDict(field_value)
      
    if field_name == 'private_key':
      return algs.EGSecretKey.fromJSONDict(field_value)
    
  def _process_value_out(self, field_name, field_value):
    # the date
    if field_name == 'frozen_at' or field_name == 'voting_starts_at' or field_name == 'voting_ends_at':
      return str(field_value)

    if field_name == 'public_key' or field_name == 'private_key':
      return field_value.toJSONDict()
    
  @property
  def registration_status_pretty(self):
    if self.openreg:
      return "Open"
    else:
      return "Closed"
    
  @property
  def winners(self):
    """
    Depending on the type of each question, determine the winners
    returns an array of winners for each question, aka an array of arrays.
    assumes that if there is a max to the question, that's how many winners there are.
    """
    return [one_question_winner(self.questions[i], self.result[i], self.num_cast_votes) for i in range(len(self.questions))]
    
  @property
  def pretty_result(self):
    if not self.result:
      return None
    
    # get the winners
    winners = self.winners

    raw_result = self.result
    prettified_result = []

    # loop through questions
    for i in range(len(self.questions)):
      q = self.questions[i]
      pretty_question = []
      
      # go through answers
      for j in range(len(q['answers'])):
        a = q['answers'][j]
        count = raw_result[i][j]
        pretty_question.append({'answer': a, 'count': count, 'winner': (j in winners[i])})
        
      prettified_result.append({'question': q['short_name'], 'answers': pretty_question})

    return prettified_result

    
class Voter(HeliosObject):
  """
  A voter in an election
  """
  FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id', 'name', 'alias']
  JSON_FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']
  
  # alternative, for when the voter is aliased
  ALIASED_VOTER_JSON_FIELDS = ['election_uuid', 'uuid', 'alias']
  
  def toJSONDict(self):
    fields = None
    if self.alias != None:
      return super(Voter, self).toJSONDict(self.ALIASED_VOTER_JSON_FIELDS)
    else:
      return super(Voter,self).toJSONDict()

  @property
  def voter_id_hash(self):
    if self.voter_login_id:
      # for backwards compatibility with v3.0, and since it doesn't matter
      # too much if we hash the email or the unique login ID here.
      return utils.hash_b64(self.voter_login_id)
    else:
      return utils.hash_b64(self.voter_id)

class Trustee(HeliosObject):
  """
  a trustee
  """
  FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']

  def _process_value_in(self, field_name, field_value):
    if field_name == 'public_key':
      return algs.EGPublicKey.fromJSONDict(field_value)
      
    if field_name == 'pok':
      return algs.DLogProof.fromJSONDict(field_value)
    
  def _process_value_out(self, field_name, field_value):
    if field_name == 'public_key' or field_name == 'pok':
      return field_value.toJSONDict()
          
class CastVote(HeliosObject):
  """
  A cast vote, which includes an encrypted vote and some cast metadata
  """
  FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
  
  def __init__(self, *args, **kwargs):
    super(CastVote, self).__init__(*args, **kwargs)
    self.election = None
  
  @classmethod
  def fromJSONDict(cls, d, election=None):
    o = cls()
    o.election = election
    o.set_from_args(**d)
    return o
    
  def toJSONDict(self, include_vote=True):
    result = super(CastVote,self).toJSONDict()
    if not include_vote:
      del result['vote']
    return result

  @classmethod
  def fromOtherObject(cls, o, election):
    obj = cls()
    obj.election = election
    obj.set_from_other_object(o)
    return obj
  
  def _process_value_in(self, field_name, field_value):
    if field_name == 'cast_at':
      if type(field_value) == str:
        return datetime.datetime.strptime(field_value, '%Y-%m-%d %H:%M:%S')
      
    if field_name == 'vote':
      return EncryptedVote.fromJSONDict(field_value, self.election.public_key)
      
  def _process_value_out(self, field_name, field_value):
    # the date
    if field_name == 'cast_at':
      return str(field_value)

    if field_name == 'vote':
      return field_value.toJSONDict()
      
  def issues(self, election):
    """
    Look for consistency problems
    """
    issues = []
    
    # check the election
    if self.vote.election_uuid != election.uuid:
      issues.append("the vote's election UUID does not match the election for which this vote is being cast")
    
    return issues

class DLogTable(object):
  """
  Keeping track of discrete logs
  """
  
  def __init__(self, base, modulus):
    self.dlogs = {}
    self.dlogs[1] = 0
    self.last_dlog_result = 1
    self.counter = 0
    
    self.base = base
    self.modulus = modulus
    
  def increment(self):
    self.counter += 1
    
    # new value
    new_value = (self.last_dlog_result * self.base) % self.modulus
    
    # record the discrete log
    self.dlogs[new_value] = self.counter
    
    # record the last value
    self.last_dlog_result = new_value
    
  def precompute(self, up_to):
    while self.counter < up_to:
      self.increment()
  
  def lookup(self, value):
    return self.dlogs.get(value, None)
      
    
class Tally(HeliosObject):
  """
  A running homomorphic tally
  """
  
  FIELDS = ['num_tallied', 'tally']
  JSON_FIELDS = ['num_tallied', 'tally']
  
  def __init__(self, *args, **kwargs):
    super(Tally, self).__init__(*args, **kwargs)

    self.election = kwargs.get('election',None)

    if self.election:
      self.init_election(self.election)
    else:
      self.questions = None
      self.public_key = None
      
      if not self.tally:
        self.tally = None
      
    # initialize
    if self.num_tallied == None:
      self.num_tallied = 0    

  def init_election(self, election):
    """
    given the election, initialize some params
    """
    self.questions = election.questions
    self.public_key = election.public_key
    
    if not self.tally:
      self.tally = [[0 for a in q['answers']] for q in self.questions]
    
  def add_vote_batch(self, encrypted_votes, verify_p=True):
    """
    Add a batch of votes. Eventually, this will be optimized to do an aggregate proof verification
    rather than a whole proof verif for each vote.
    """
    for vote in encrypted_votes:
      self.add_vote(vote, verify_p)
    
  def add_vote(self, encrypted_vote, verify_p=True):
    # do we verify?
    if verify_p:
      if not encrypted_vote.verify(self.election):
        raise Exception('Bad Vote')

    # for each question
    for question_num in range(len(self.questions)):
      question = self.questions[question_num]
      answers = question['answers']
      
      # for each possible answer to each question
      for answer_num in range(len(answers)):
        # do the homomorphic addition into the tally
        enc_vote_choice = encrypted_vote.encrypted_answers[question_num].choices[answer_num]
        enc_vote_choice.pk = self.public_key
        self.tally[question_num][answer_num] = encrypted_vote.encrypted_answers[question_num].choices[answer_num] * self.tally[question_num][answer_num]

    self.num_tallied += 1

  def decryption_factors_and_proofs(self, sk):
    """
    returns an array of decryption factors and a corresponding array of decryption proofs.
    makes the decryption factors into strings, for general Helios / JS compatibility.
    """
    # for all choices of all questions (double list comprehension)
    decryption_factors = []
    decryption_proof = []
    
    for question_num, question in enumerate(self.questions):
      answers = question['answers']
      question_factors = []
      question_proof = []

      for answer_num, answer in enumerate(answers):
        # do decryption and proof of it
        dec_factor, proof = sk.decryption_factor_and_proof(self.tally[question_num][answer_num])

        # look up appropriate discrete log
        # this is the string conversion
        question_factors.append(str(dec_factor))
        question_proof.append(proof.toJSONDict())
        
      decryption_factors.append(question_factors)
      decryption_proof.append(question_proof)
    
    return decryption_factors, decryption_proof
    
  def decrypt_and_prove(self, sk, discrete_logs=None):
    """
    returns an array of tallies and a corresponding array of decryption proofs.
    """
    
    # who's keeping track of discrete logs?
    if not discrete_logs:
      discrete_logs = self.discrete_logs
      
    # for all choices of all questions (double list comprehension)
    decrypted_tally = []
    decryption_proof = []
    
    for question_num in range(len(self.questions)):
      question = self.questions[question_num]
      answers = question['answers']
      question_tally = []
      question_proof = []

      for answer_num in range(len(answers)):
        # do decryption and proof of it
        plaintext, proof = sk.prove_decryption(self.tally[question_num][answer_num])

        # look up appropriate discrete log
        question_tally.append(discrete_logs[plaintext])
        question_proof.append(proof)
        
      decrypted_tally.append(question_tally)
      decryption_proof.append(question_proof)
    
    return decrypted_tally, decryption_proof
  
  def verify_decryption_proofs(self, decryption_factors, decryption_proofs, public_key, challenge_generator):
    """
    decryption_factors is a list of lists of dec factors
    decryption_proofs are the corresponding proofs
    public_key is, of course, the public key of the trustee
    """
    
    # go through each one
    for q_num, q in enumerate(self.tally):
      for a_num, answer_tally in enumerate(q):
        # parse the proof
        proof = algs.EGZKProof.fromJSONDict(decryption_proofs[q_num][a_num])
        
        # check that g, alpha, y, dec_factor is a DH tuple
        if not proof.verify(public_key.g, answer_tally.alpha, public_key.y, int(decryption_factors[q_num][a_num]), public_key.p, public_key.q, challenge_generator):
          return False
    
    return True
    
  def decrypt_from_factors(self, decryption_factors, public_key):
    """
    decrypt a tally given decryption factors
    
    The decryption factors are a list of decryption factor sets, for each trustee.
    Each decryption factor set is a list of lists of decryption factors (questions/answers).
    """
    
    # pre-compute a dlog table
    dlog_table = DLogTable(base = public_key.g, modulus = public_key.p)
    dlog_table.precompute(self.num_tallied)
    
    result = []
    
    # go through each one
    for q_num, q in enumerate(self.tally):
      q_result = []

      for a_num, a in enumerate(q):
        # coalesce the decryption factors into one list
        dec_factor_list = [df[q_num][a_num] for df in decryption_factors]
        raw_value = self.tally[q_num][a_num].decrypt(dec_factor_list, public_key)
        
        q_result.append(dlog_table.lookup(raw_value))

      result.append(q_result)
    
    return result

  def _process_value_in(self, field_name, field_value):
    if field_name == 'tally':
      return [[algs.EGCiphertext.fromJSONDict(a) for a in q] for q in field_value]
      
  def _process_value_out(self, field_name, field_value):
    if field_name == 'tally':
      return [[a.toJSONDict() for a in q] for q in field_value]    
        

########NEW FILE########
__FILENAME__ = elgamal
"""
ElGamal Algorithms for the Helios Voting System

This is a copy of algs.py now made more El-Gamal specific in naming,
for modularity purposes.

Ben Adida
ben@adida.net
"""

import math, hashlib, logging
import randpool, number

import numtheory

from algs import Utils

class Cryptosystem(object):
    def __init__(self):
      self.p = None
      self.q = None
      self.g = None

    @classmethod
    def generate(cls, n_bits):
      """
      generate an El-Gamal environment. Returns an instance
      of ElGamal(), with prime p, group size q, and generator g
      """
      
      EG = cls()
      
      # find a prime p such that (p-1)/2 is prime q
      EG.p = Utils.random_safe_prime(n_bits)

      # q is the order of the group
      # FIXME: not always p-1/2
      EG.q = (EG.p-1)/2
  
      # find g that generates the q-order subgroup
      while True:
        EG.g = Utils.random_mpz_lt(EG.p)
        if pow(EG.g, EG.q, EG.p) == 1:
          break

      return EG

    def generate_keypair(self):
      """
      generates a keypair in the setting
      """
      
      keypair = KeyPair()
      keypair.generate(self.p, self.q, self.g)
  
      return keypair
      
class KeyPair(object):
    def __init__(self):
      self.pk = PublicKey()
      self.sk = SecretKey()

    def generate(self, p, q, g):
      """
      Generate an ElGamal keypair
      """
      self.pk.g = g
      self.pk.p = p
      self.pk.q = q
      
      self.sk.x = Utils.random_mpz_lt(q)
      self.pk.y = pow(g, self.sk.x, p)
      
      self.sk.public_key = self.pk

class PublicKey:
    def __init__(self):
        self.y = None
        self.p = None
        self.g = None
        self.q = None

    def encrypt_with_r(self, plaintext, r, encode_message= False):
        """
        expecting plaintext.m to be a big integer
        """
        ciphertext = Ciphertext()
        ciphertext.pk = self

        # make sure m is in the right subgroup
        if encode_message:
          y = plaintext.m + 1
          if pow(y, self.q, self.p) == 1:
            m = y
          else:
            m = -y % self.p
        else:
          m = plaintext.m
        
        ciphertext.alpha = pow(self.g, r, self.p)
        ciphertext.beta = (m * pow(self.y, r, self.p)) % self.p
        
        return ciphertext

    def encrypt_return_r(self, plaintext):
        """
        Encrypt a plaintext and return the randomness just generated and used.
        """
        r = Utils.random_mpz_lt(self.q)
        ciphertext = self.encrypt_with_r(plaintext, r)
        
        return [ciphertext, r]

    def encrypt(self, plaintext):
        """
        Encrypt a plaintext, obscure the randomness.
        """
        return self.encrypt_return_r(plaintext)[0]
        
    def __mul__(self,other):
      if other == 0 or other == 1:
        return self
        
      # check p and q
      if self.p != other.p or self.q != other.q or self.g != other.g:
        raise Exception("incompatible public keys")
        
      result = PublicKey()
      result.p = self.p
      result.q = self.q
      result.g = self.g
      result.y = (self.y * other.y) % result.p
      return result
      
    def verify_sk_proof(self, dlog_proof, challenge_generator = None):
      """
      verify the proof of knowledge of the secret key
      g^response = commitment * y^challenge
      """
      left_side = pow(self.g, dlog_proof.response, self.p)
      right_side = (dlog_proof.commitment * pow(self.y, dlog_proof.challenge, self.p)) % self.p
      
      expected_challenge = challenge_generator(dlog_proof.commitment) % self.q
      
      return ((left_side == right_side) and (dlog_proof.challenge == expected_challenge))


class SecretKey:
    def __init__(self):
        self.x = None
        self.public_key = None

    @property
    def pk(self):
        return self.public_key

    def decryption_factor(self, ciphertext):
        """
        provide the decryption factor, not yet inverted because of needed proof
        """
        return pow(ciphertext.alpha, self.x, self.pk.p)

    def decryption_factor_and_proof(self, ciphertext, challenge_generator=None):
        """
        challenge generator is almost certainly
        EG_fiatshamir_challenge_generator
        """
        if not challenge_generator:
            challenge_generator = fiatshamir_challenge_generator

        dec_factor = self.decryption_factor(ciphertext)

        proof = ZKProof.generate(self.pk.g, ciphertext.alpha, self.x, self.pk.p, self.pk.q, challenge_generator)

        return dec_factor, proof

    def decrypt(self, ciphertext, dec_factor = None, decode_m=False):
        """
        Decrypt a ciphertext. Optional parameter decides whether to encode the message into the proper subgroup.
        """
        if not dec_factor:
            dec_factor = self.decryption_factor(ciphertext)

        m = (Utils.inverse(dec_factor, self.pk.p) * ciphertext.beta) % self.pk.p

        if decode_m:
          # get m back from the q-order subgroup
          if m < self.pk.q:
            y = m
          else:
            y = -m % self.pk.p

          return Plaintext(y-1, self.pk)
        else:
          return Plaintext(m, self.pk)

    def prove_decryption(self, ciphertext):
        """
        given g, y, alpha, beta/(encoded m), prove equality of discrete log
        with Chaum Pedersen, and that discrete log is x, the secret key.

        Prover sends a=g^w, b=alpha^w for random w
        Challenge c = sha1(a,b) with and b in decimal form
        Prover sends t = w + xc

        Verifier will check that g^t = a * y^c
        and alpha^t = b * beta/m ^ c
        """
        
        m = (Utils.inverse(pow(ciphertext.alpha, self.x, self.pk.p), self.pk.p) * ciphertext.beta) % self.pk.p
        beta_over_m = (ciphertext.beta * Utils.inverse(m, self.pk.p)) % self.pk.p

        # pick a random w
        w = Utils.random_mpz_lt(self.pk.q)
        a = pow(self.pk.g, w, self.pk.p)
        b = pow(ciphertext.alpha, w, self.pk.p)

        c = int(hashlib.sha1(str(a) + "," + str(b)).hexdigest(),16)

        t = (w + self.x * c) % self.pk.q

        return m, {
            'commitment' : {'A' : str(a), 'B': str(b)},
            'challenge' : str(c),
            'response' : str(t)
          }

    def prove_sk(self, challenge_generator):
      """
      Generate a PoK of the secret key
      Prover generates w, a random integer modulo q, and computes commitment = g^w mod p.
      Verifier provides challenge modulo q.
      Prover computes response = w + x*challenge mod q, where x is the secret key.
      """
      w = Utils.random_mpz_lt(self.pk.q)
      commitment = pow(self.pk.g, w, self.pk.p)
      challenge = challenge_generator(commitment) % self.pk.q
      response = (w + (self.x * challenge)) % self.pk.q
      
      return DLogProof(commitment, challenge, response)
      

class Plaintext:
    def __init__(self, m = None, pk = None):
        self.m = m
        self.pk = pk
        
class Ciphertext:
    def __init__(self, alpha=None, beta=None, pk=None):
        self.pk = pk
        self.alpha = alpha
        self.beta = beta

    def __mul__(self,other):
        """
        Homomorphic Multiplication of ciphertexts.
        """
        if type(other) == int and (other == 0 or other == 1):
          return self
          
        if self.pk != other.pk:
          logging.info(self.pk)
          logging.info(other.pk)
          raise Exception('different PKs!')
        
        new = Ciphertext()
        
        new.pk = self.pk
        new.alpha = (self.alpha * other.alpha) % self.pk.p
        new.beta = (self.beta * other.beta) % self.pk.p

        return new
  
    def reenc_with_r(self, r):
        """
        We would do this homomorphically, except
        that's no good when we do plaintext encoding of 1.
        """
        new_c = Ciphertext()
        new_c.alpha = (self.alpha * pow(self.pk.g, r, self.pk.p)) % self.pk.p
        new_c.beta = (self.beta * pow(self.pk.y, r, self.pk.p)) % self.pk.p
        new_c.pk = self.pk

        return new_c
    
    def reenc_return_r(self):
        """
        Reencryption with fresh randomness, which is returned.
        """
        r = Utils.random_mpz_lt(self.pk.q)
        new_c = self.reenc_with_r(r)
        return [new_c, r]
    
    def reenc(self):
        """
        Reencryption with fresh randomness, which is kept obscured (unlikely to be useful.)
        """
        return self.reenc_return_r()[0]
    
    def __eq__(self, other):
      """
      Check for ciphertext equality.
      """
      if other == None:
        return False
        
      return (self.alpha == other.alpha and self.beta == other.beta)
    
    def generate_encryption_proof(self, plaintext, randomness, challenge_generator):
      """
      Generate the disjunctive encryption proof of encryption
      """
      # random W
      w = Utils.random_mpz_lt(self.pk.q)

      # build the proof
      proof = ZKProof()

      # compute A=g^w, B=y^w
      proof.commitment['A'] = pow(self.pk.g, w, self.pk.p)
      proof.commitment['B'] = pow(self.pk.y, w, self.pk.p)

      # generate challenge
      proof.challenge = challenge_generator(proof.commitment);

      # Compute response = w + randomness * challenge
      proof.response = (w + (randomness * proof.challenge)) % self.pk.q;

      return proof;
      
    def simulate_encryption_proof(self, plaintext, challenge=None):
      # generate a random challenge if not provided
      if not challenge:
        challenge = Utils.random_mpz_lt(self.pk.q)
        
      proof = ZKProof()
      proof.challenge = challenge

      # compute beta/plaintext, the completion of the DH tuple
      beta_over_plaintext =  (self.beta * Utils.inverse(plaintext.m, self.pk.p)) % self.pk.p
      
      # random response, does not even need to depend on the challenge
      proof.response = Utils.random_mpz_lt(self.pk.q);

      # now we compute A and B
      proof.commitment['A'] = (Utils.inverse(pow(self.alpha, proof.challenge, self.pk.p), self.pk.p) * pow(self.pk.g, proof.response, self.pk.p)) % self.pk.p
      proof.commitment['B'] = (Utils.inverse(pow(beta_over_plaintext, proof.challenge, self.pk.p), self.pk.p) * pow(self.pk.y, proof.response, self.pk.p)) % self.pk.p

      return proof
    
    def generate_disjunctive_encryption_proof(self, plaintexts, real_index, randomness, challenge_generator):
      # note how the interface is as such so that the result does not reveal which is the real proof.

      proofs = [None for p in plaintexts]

      # go through all plaintexts and simulate the ones that must be simulated.
      for p_num in range(len(plaintexts)):
        if p_num != real_index:
          proofs[p_num] = self.simulate_encryption_proof(plaintexts[p_num])

      # the function that generates the challenge
      def real_challenge_generator(commitment):
        # set up the partial real proof so we're ready to get the hash
        proofs[real_index] = ZKProof()
        proofs[real_index].commitment = commitment

        # get the commitments in a list and generate the whole disjunctive challenge
        commitments = [p.commitment for p in proofs]
        disjunctive_challenge = challenge_generator(commitments);

        # now we must subtract all of the other challenges from this challenge.
        real_challenge = disjunctive_challenge
        for p_num in range(len(proofs)):
          if p_num != real_index:
            real_challenge = real_challenge - proofs[p_num].challenge

        # make sure we mod q, the exponent modulus
        return real_challenge % self.pk.q
        
      # do the real proof
      real_proof = self.generate_encryption_proof(plaintexts[real_index], randomness, real_challenge_generator)

      # set the real proof
      proofs[real_index] = real_proof

      return ZKDisjunctiveProof(proofs)
      
    def verify_encryption_proof(self, plaintext, proof):
      """
      Checks for the DDH tuple g, y, alpha, beta/plaintext.
      (PoK of randomness r.)
      
      Proof contains commitment = {A, B}, challenge, response
      """
      
      # check that g^response = A * alpha^challenge
      first_check = (pow(self.pk.g, proof.response, self.pk.p) == ((pow(self.alpha, proof.challenge, self.pk.p) * proof.commitment['A']) % self.pk.p))
      
      # check that y^response = B * (beta/m)^challenge
      beta_over_m = (self.beta * Utils.inverse(plaintext.m, self.pk.p)) % self.pk.p
      second_check = (pow(self.pk.y, proof.response, self.pk.p) == ((pow(beta_over_m, proof.challenge, self.pk.p) * proof.commitment['B']) % self.pk.p))
      
      # print "1,2: %s %s " % (first_check, second_check)
      return (first_check and second_check)
    
    def verify_disjunctive_encryption_proof(self, plaintexts, proof, challenge_generator):
      """
      plaintexts and proofs are all lists of equal length, with matching.
      
      overall_challenge is what all of the challenges combined should yield.
      """
      if len(plaintexts) != len(proof.proofs):
        print("bad number of proofs (expected %s, found %s)" % (len(plaintexts), len(proof.proofs)))
        return False

      for i in range(len(plaintexts)):
        # if a proof fails, stop right there
        if not self.verify_encryption_proof(plaintexts[i], proof.proofs[i]):
          print "bad proof %s, %s, %s" % (i, plaintexts[i], proof.proofs[i])
          return False
          
      # logging.info("made it past the two encryption proofs")
          
      # check the overall challenge
      return (challenge_generator([p.commitment for p in proof.proofs]) == (sum([p.challenge for p in proof.proofs]) % self.pk.q))
      
    def verify_decryption_proof(self, plaintext, proof):
      """
      Checks for the DDH tuple g, alpha, y, beta/plaintext
      (PoK of secret key x.)
      """
      return False
      
    def verify_decryption_factor(self, dec_factor, dec_proof, public_key):
      """
      when a ciphertext is decrypted by a dec factor, the proof needs to be checked
      """
      pass
      
    def decrypt(self, decryption_factors, public_key):
      """
      decrypt a ciphertext given a list of decryption factors (from multiple trustees)
      For now, no support for threshold
      """
      running_decryption = self.beta
      for dec_factor in decryption_factors:
        running_decryption = (running_decryption * Utils.inverse(dec_factor, public_key.p)) % public_key.p
        
      return running_decryption

    def to_string(self):
        return "%s,%s" % (self.alpha, self.beta)
    
    @classmethod
    def from_string(cls, str):
        """
        expects alpha,beta
        """
        split = str.split(",")
        return cls.from_dict({'alpha' : split[0], 'beta' : split[1]})

class ZKProof(object):
  def __init__(self):
    self.commitment = {'A':None, 'B':None}
    self.challenge = None
    self.response = None
  
  @classmethod
  def generate(cls, little_g, little_h, x, p, q, challenge_generator):
      """
      generate a DDH tuple proof, where challenge generator is
      almost certainly EG_fiatshamir_challenge_generator
      """

      # generate random w
      w = Utils.random_mpz_lt(q)
      
      # create proof instance
      proof = cls()

      # compute A = little_g^w, B=little_h^w
      proof.commitment['A'] = pow(little_g, w, p)
      proof.commitment['B'] = pow(little_h, w, p)

      # get challenge
      proof.challenge = challenge_generator(proof.commitment)

      # compute response
      proof.response = (w + (x * proof.challenge)) % q

      # return proof
      return proof
      
  def verify(self, little_g, little_h, big_g, big_h, p, q, challenge_generator=None):
    """
    Verify a DH tuple proof
    """
    # check that little_g^response = A * big_g^challenge
    first_check = (pow(little_g, self.response, p) == ((pow(big_g, self.challenge, p) * self.commitment['A']) % p))
    
    # check that little_h^response = B * big_h^challenge
    second_check = (pow(little_h, self.response, p) == ((pow(big_h, self.challenge, p) * self.commitment['B']) % p))

    # check the challenge?
    third_check = True
    
    if challenge_generator:
      third_check = (self.challenge == challenge_generator(self.commitment))

    return (first_check and second_check and third_check)
  
class ZKDisjunctiveProof:
  def __init__(self, proofs = None):
    self.proofs = proofs  

class DLogProof(object):
  def __init__(self, commitment=None, challenge=None, response=None):
    self.commitment = commitment
    self.challenge = challenge
    self.response = response
    
def disjunctive_challenge_generator(commitments):
  array_to_hash = []
  for commitment in commitments:
    array_to_hash.append(str(commitment['A']))
    array_to_hash.append(str(commitment['B']))

  string_to_hash = ",".join(array_to_hash)
  return int(hashlib.sha1(string_to_hash).hexdigest(),16)
  
# a challenge generator for Fiat-Shamir with A,B commitment
def fiatshamir_challenge_generator(commitment):
  return disjunctive_challenge_generator([commitment])

def DLog_challenge_generator(commitment):
  string_to_hash = str(commitment)
  return int(hashlib.sha1(string_to_hash).hexdigest(),16)


########NEW FILE########
__FILENAME__ = number
#
#   number.py : Number-theoretic functions
#
#  Part of the Python Cryptography Toolkit
#
# Distribute and use freely; there are no restrictions on further
# dissemination and usage except those imposed by the laws of your
# country of residence.  This software is provided "as is" without
# warranty of fitness for use or suitability for any purpose, express
# or implied. Use at your own risk or not at all.
#

__revision__ = "$Id: number.py,v 1.13 2003/04/04 18:21:07 akuchling Exp $"

bignum = long
try:
    from Crypto.PublicKey import _fastmath
except ImportError:
    _fastmath = None

# Commented out and replaced with faster versions below
## def long2str(n):
##     s=''
##     while n>0:
##         s=chr(n & 255)+s
##         n=n>>8
##     return s

## import types
## def str2long(s):
##     if type(s)!=types.StringType: return s   # Integers will be left alone
##     return reduce(lambda x,y : x*256+ord(y), s, 0L)

def size (N):
    """size(N:long) : int
    Returns the size of the number N in bits.
    """
    bits, power = 0,1L
    while N >= power:
        bits += 1
        power = power << 1
    return bits

def getRandomNumber(N, randfunc):
    """getRandomNumber(N:int, randfunc:callable):long
    Return an N-bit random number."""

    S = randfunc(N/8)
    odd_bits = N % 8
    if odd_bits != 0:
        char = ord(randfunc(1)) >> (8-odd_bits)
        S = chr(char) + S
    value = bytes_to_long(S)
    value |= 2L ** (N-1)                # Ensure high bit is set
    assert size(value) >= N
    return value

def GCD(x,y):
    """GCD(x:long, y:long): long
    Return the GCD of x and y.
    """
    x = abs(x) ; y = abs(y)
    while x > 0:
        x, y = y % x, x
    return y

def inverse(u, v):
    """inverse(u:long, u:long):long
    Return the inverse of u mod v.
    """
    u3, v3 = long(u), long(v)
    u1, v1 = 1L, 0L
    while v3 > 0:
        q=u3 / v3
        u1, v1 = v1, u1 - v1*q
        u3, v3 = v3, u3 - v3*q
    while u1<0:
        u1 = u1 + v
    return u1

# Given a number of bits to generate and a random generation function,
# find a prime number of the appropriate size.

def getPrime(N, randfunc):
    """getPrime(N:int, randfunc:callable):long
    Return a random N-bit prime number.
    """

    number=getRandomNumber(N, randfunc) | 1
    while (not isPrime(number)):
        number=number+2
    return number

def isPrime(N):
    """isPrime(N:long):bool
    Return true if N is prime.
    """
    if N == 1:
        return 0
    if N in sieve:
        return 1
    for i in sieve:
        if (N % i)==0:
            return 0

    # Use the accelerator if available
    if _fastmath is not None:
        return _fastmath.isPrime(N)

    # Compute the highest bit that's set in N
    N1 = N - 1L
    n = 1L
    while (n<N):
        n=n<<1L
    n = n >> 1L

    # Rabin-Miller test
    for c in sieve[:7]:
        a=long(c) ; d=1L ; t=n
        while (t):  # Iterate over the bits in N1
            x=(d*d) % N
            if x==1L and d!=1L and d!=N1:
                return 0  # Square root of 1 found
            if N1 & t:
                d=(x*a) % N
            else:
                d=x
            t = t >> 1L
        if d!=1L:
            return 0
    return 1

# Small primes used for checking primality; these are all the primes
# less than 256.  This should be enough to eliminate most of the odd
# numbers before needing to do a Rabin-Miller test at all.

sieve=[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59,
       61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127,
       131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193,
       197, 199, 211, 223, 227, 229, 233, 239, 241, 251]

# Improved conversion functions contributed by Barry Warsaw, after
# careful benchmarking

import struct

def long_to_bytes(n, blocksize=0):
    """long_to_bytes(n:long, blocksize:int) : string
    Convert a long integer to a byte string.

    If optional blocksize is given and greater than zero, pad the front of the
    byte string with binary zeros so that the length is a multiple of
    blocksize.
    """
    # after much testing, this algorithm was deemed to be the fastest
    s = ''
    n = long(n)
    pack = struct.pack
    while n > 0:
        s = pack('>I', n & 0xffffffffL) + s
        n = n >> 32
    # strip off leading zeros
    for i in range(len(s)):
        if s[i] != '\000':
            break
    else:
        # only happens when n == 0
        s = '\000'
        i = 0
    s = s[i:]
    # add back some pad bytes.  this could be done more efficiently w.r.t. the
    # de-padding being done above, but sigh...
    if blocksize > 0 and len(s) % blocksize:
        s = (blocksize - len(s) % blocksize) * '\000' + s
    return s

def bytes_to_long(s):
    """bytes_to_long(string) : long
    Convert a byte string to a long integer.

    This is (essentially) the inverse of long_to_bytes().
    """
    acc = 0L
    unpack = struct.unpack
    length = len(s)
    if length % 4:
        extra = (4 - length % 4)
        s = '\000' * extra + s
        length = length + extra
    for i in range(0, length, 4):
        acc = (acc << 32) + unpack('>I', s[i:i+4])[0]
    return acc

# For backwards compatibility...
import warnings
def long2str(n, blocksize=0):
    warnings.warn("long2str() has been replaced by long_to_bytes()")
    return long_to_bytes(n, blocksize)
def str2long(s):
    warnings.warn("str2long() has been replaced by bytes_to_long()")
    return bytes_to_long(s)

########NEW FILE########
__FILENAME__ = numtheory
##################################################
# ent.py -- Element Number Theory 
# (c) William Stein, 2004
##################################################




from random import randrange
from math import log, sqrt




##################################################
## Greatest Common Divisors
##################################################

def gcd(a, b):                                        # (1)
    """
    Returns the greatest commond divisor of a and b.
    Input:
        a -- an integer
        b -- an integer
    Output:
        an integer, the gcd of a and b
    Examples:
    >>> gcd(97,100)
    1
    >>> gcd(97 * 10**15, 19**20 * 97**2)              # (2)
    97L
    """
    if a < 0:  a = -a
    if b < 0:  b = -b
    if a == 0: return b
    if b == 0: return a
    while b != 0: 
        (a, b) = (b, a%b)
    return a



##################################################
## Enumerating Primes
##################################################

def primes(n):
    """
    Returns a list of the primes up to n, computed 
    using the Sieve of Eratosthenes.
    Input:
        n -- a positive integer
    Output:
        list -- a list of the primes up to n
    Examples:
    >>> primes(10)
    [2, 3, 5, 7]
    >>> primes(45)
    [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]
    """
    if n <= 1: return []
    X = [i for i in range(3,n+1) if i%2 != 0]     # (1)
    P = [2]                                       # (2)
    sqrt_n = sqrt(n)                              # (3)
    while len(X) > 0 and X[0] <= sqrt_n:          # (4)
        p = X[0]                                  # (5)
        P.append(p)                               # (6)
        X = [a for a in X if a%p != 0]            # (7)
    return P + X                                  # (8)




##################################################
## Integer Factorization
##################################################

def trial_division(n, bound=None):
    """
    Return the smallest prime divisor <= bound of the 
    positive integer n, or n if there is no such prime.  
    If the optional argument bound is omitted, then bound=n.
    Input:
        n -- a positive integer
        bound - (optional) a positive integer
    Output:
        int -- a prime p<=bound that divides n, or n if
               there is no such prime.
    Examples:
    >>> trial_division(15)
    3
    >>> trial_division(91)
    7
    >>> trial_division(11)
    11
    >>> trial_division(387833, 300)   
    387833
    >>> # 300 is not big enough to split off a 
    >>> # factor, but 400 is.
    >>> trial_division(387833, 400)  
    389
    """
    if n == 1: return 1
    for p in [2, 3, 5]:
        if n%p == 0: return p
    if bound == None: bound = n
    dif = [6, 4, 2, 4, 2, 4, 6, 2]
    m = 7; i = 1
    while m <= bound and m*m <= n:
        if n%m == 0:
            return m
        m += dif[i%8]
        i += 1
    return n

def factor(n):
    """
    Returns the factorization of the integer n as 
    a sorted list of tuples (p,e), where the integers p
    are output by the split algorithm.  
    Input:
        n -- an integer
    Output:
        list -- factorization of n
    Examples:
    >>> factor(500)
    [(2, 2), (5, 3)]
    >>> factor(-20)
    [(2, 2), (5, 1)]
    >>> factor(1)
    []
    >>> factor(2004)
    [(2, 2), (3, 1), (167, 1)]
    """
    if n in [-1, 0, 1]: return []
    if n < 0: n = -n
    F = []
    while n != 1:
        p = trial_division(n)
        e = 1
        n /= p
        while n%p == 0:
            e += 1; n /= p
        F.append((p,e))
    F.sort()
    return F



##################################################
## Linear Equations Modulo $n$
##################################################

def xgcd(a, b):
    """
    Returns g, x, y such that g = x*a + y*b = gcd(a,b).
    Input:
        a -- an integer
        b -- an integer
    Output:
        g -- an integer, the gcd of a and b
        x -- an integer
        y -- an integer
    Examples:
    >>> xgcd(2,3)
    (1, -1, 1)
    >>> xgcd(10, 12)
    (2, -1, 1)
    >>> g, x, y = xgcd(100, 2004)
    >>> print g, x, y
    4 -20 1
    >>> print x*100 + y*2004
    4
    """
    if a == 0 and b == 0: return (0, 0, 1)
    if a == 0: return (abs(b), 0, b/abs(b))
    if b == 0: return (abs(a), a/abs(a), 0)
    x_sign = 1; y_sign = 1
    if a < 0: a = -a; x_sign = -1
    if b < 0: b = -b; y_sign = -1
    x = 1; y = 0; r = 0; s = 1
    while b != 0:
        (c, q) = (a%b, a/b)
        (a, b, r, s, x, y) = (b, c, x-q*r, y-q*s, r, s)
    return (a, x*x_sign, y*y_sign)

def inversemod(a, n):
    """
    Returns the inverse of a modulo n, normalized to
    lie between 0 and n-1.  If a is not coprime to n,
    raise an exception (this will be useful later for 
    the elliptic curve factorization method).
    Input:
        a -- an integer coprime to n
        n -- a positive integer
    Output:
        an integer between 0 and n-1.
    Examples:
    >>> inversemod(1,1)
    0
    >>> inversemod(2,5)
    3
    >>> inversemod(5,8)
    5
    >>> inversemod(37,100)
    73
    """
    g, x, y = xgcd(a, n)
    if g != 1:
        raise ZeroDivisionError, (a,n)
    assert g == 1, "a must be coprime to n."
    return x%n

def solve_linear(a,b,n):
    """
    If the equation ax = b (mod n) has a solution, return a 
    solution normalized to lie between 0 and n-1, otherwise
    returns None.
    Input:
        a -- an integer
        b -- an integer
        n -- an integer
    Output:
        an integer or None
    Examples:
    >>> solve_linear(4, 2, 10)
    8
    >>> solve_linear(2, 1, 4) == None
    True
    """
    g, c, _ = xgcd(a,n)                 # (1)
    if b%g != 0: return None
    return ((b/g)*c) % n                

def crt(a, b, m, n):
    """
    Return the unique integer between 0 and m*n - 1 
    that reduces to a modulo n and b modulo m, where
    the integers m and n are coprime. 
    Input:
        a, b, m, n -- integers, with m and n coprime
    Output:
        int -- an integer between 0 and m*n - 1.
    Examples:
    >>> crt(1, 2, 3, 4)
    10
    >>> crt(4, 5, 10, 3)
    14
    >>> crt(-1, -1, 100, 101)
    10099
    """
    g, c, _ = xgcd(m, n)                       
    assert g == 1, "m and n must be coprime."
    return (a + (b-a)*c*m) % (m*n)


##################################################
## Computation of Powers
##################################################

def powermod(a, m, n):
    """
    The m-th power of a modulo n.
    Input:
        a -- an integer
        m -- a nonnegative integer
        n -- a positive integer
    Output:
        int -- an integer between 0 and n-1
    Examples:
    >>> powermod(2,25,30)
    2
    >>> powermod(19,12345,100)
    99
    """
    assert m >= 0, "m must be nonnegative."   # (1)
    assert n >= 1, "n must be positive."      # (2)
    ans = 1
    apow = a
    while m != 0:
        if m%2 != 0:
            ans = (ans * apow) % n            # (3)
        apow = (apow * apow) % n              # (4)
        m /= 2   
    return ans % n


##################################################
## Finding a Primitive Root
##################################################

def primitive_root(p):
    """
    Returns first primitive root modulo the prime p.
    (If p is not prime, this return value of this function
    is not meaningful.)
    Input:
        p -- an integer that is assumed prime
    Output:
        int -- a primitive root modulo p
    Examples:
    >>> primitive_root(7)
    3
    >>> primitive_root(389)
    2
    >>> primitive_root(5881)
    31
    """
    if p == 2: return 1
    F = factor(p-1)
    a = 2
    while a < p:
        generates = True
        for q, _ in F:
            if powermod(a, (p-1)/q, p) == 1:
                generates = False
                break
        if generates: return a
        a += 1
    assert False, "p must be prime."


##################################################
## Determining Whether a Number is Prime
##################################################

def is_pseudoprime(n, bases = [2,3,5,7]):
    """
    Returns True if n is a pseudoprime to the given bases,
    in the sense that n>1 and b**(n-1) = 1 (mod n) for each 
    elements b of bases, with b not a multiple of n, and 
    False otherwise.   
    Input:
        n -- an integer
        bases -- a list of integers
    Output:
        bool 
    Examples:
    >>> is_pseudoprime(91)
    False
    >>> is_pseudoprime(97)
    True
    >>> is_pseudoprime(1)
    False
    >>> is_pseudoprime(-2)
    True
    >>> s = [x for x in range(10000) if is_pseudoprime(x)]
    >>> t = primes(10000)
    >>> s == t 
    True
    >>> is_pseudoprime(29341) # first non-prime pseudoprime
    True
    >>> factor(29341)
    [(13, 1), (37, 1), (61, 1)]
    """
    if n < 0: n = -n                                
    if n <= 1: return False
    for b in bases:                       
        if b%n != 0 and powermod(b, n-1, n) != 1:       
            return False
    return True


def miller_rabin(n, num_trials=4):
    """
    True if n is likely prime, and False if n 
    is definitely not prime.  Increasing num_trials
    increases the probability of correctness.
    (One can prove that the probability that this 
    function returns True when it should return
    False is at most (1/4)**num_trials.)
    Input:
        n -- an integer
        num_trials -- the number of trials with the 
                      primality test.   
    Output:
        bool -- whether or not n is probably prime.
    Examples:    
    >>> miller_rabin(91)
    False                         #rand
    >>> miller_rabin(97)
    True                          #rand
    >>> s = [x for x in range(1000) if miller_rabin(x, 1)]
    >>> t = primes(1000)
    >>> print len(s), len(t)  # so 1 in 25 wrong
    175 168                       #rand
    >>> s = [x for x in range(1000) if miller_rabin(x)]
    >>> s == t                    
    True                          #rand
    """
    if n < 0: n = -n
    if n in [2,3]: return True
    if n <= 4: return False
    m = n - 1
    k = 0
    while m%2 == 0:
        k += 1; m /= 2
    # Now n - 1 = (2**k) * m with m odd
    for i in range(num_trials):
        a = randrange(2,n-1)                  # (1)
        apow = powermod(a, m, n)
        if not (apow in [1, n-1]):            
            some_minus_one = False
            for r in range(k-1):              # (2)
                apow = (apow**2)%n
                if apow == n-1:
                    some_minus_one = True
                    break                     # (3)
        if (apow in [1, n-1]) or some_minus_one:
            prob_prime = True
        else:
            return False
    return True


##################################################
## The Diffie-Hellman Key Exchange
##################################################

def random_prime(num_digits, is_prime = miller_rabin):
    """
    Returns a random prime with num_digits digits.
    Input:
        num_digits -- a positive integer
        is_prime -- (optional argment)
                    a function of one argument n that
                    returns either True if n is (probably)
                    prime and False otherwise.
    Output:
        int -- an integer
    Examples:
    >>> random_prime(10)
    8599796717L              #rand
    >>> random_prime(40)
    1311696770583281776596904119734399028761L  #rand
    """ 
    n = randrange(10**(num_digits-1), 10**num_digits)
    if n%2 == 0: n += 1
    while not is_prime(n): n += 2
    return n

def dh_init(p):
    """
    Generates and returns a random positive
    integer n < p and the power 2^n (mod p). 
    Input:
        p -- an integer that is prime
    Output:
        int -- a positive integer < p,  a secret
        int -- 2^n (mod p), send to other user
    Examples:
    >>> p = random_prime(20)
    >>> dh_init(p)
    (15299007531923218813L, 4715333264598442112L)   #rand
    """
    n = randrange(2,p)
    return n, powermod(2,n,p)

def dh_secret(p, n, mpow):
    """
    Computes the shared Diffie-Hellman secret key.
    Input:
        p -- an integer that is prime
        n -- an integer: output by dh_init for this user
        mpow-- an integer: output by dh_init for other user
    Output:
        int -- the shared secret key.
    Examples:
    >>> p = random_prime(20)
    >>> n, npow = dh_init(p)    
    >>> m, mpow = dh_init(p)
    >>> dh_secret(p, n, mpow) 
    15695503407570180188L      #rand
    >>> dh_secret(p, m, npow)    
    15695503407570180188L      #rand
    """
    return powermod(mpow,n,p)






##################################################
## Encoding Strings as Lists of Integers
##################################################

def str_to_numlist(s, bound):
    """
    Returns a sequence of integers between 0 and bound-1 
    that encodes the string s.   Randomization is included, 
    so the same string is very likely to encode differently 
    each time this function is called. 
    Input:
        s -- a string
        bound -- an integer >= 256
    Output:
        list -- encoding of s as a list of integers 
    Examples:
    >>> str_to_numlist("Run!", 1000)
    [82, 117, 110, 33]               #rand
    >>> str_to_numlist("TOP SECRET", 10**20)
    [4995371940984439512L, 92656709616492L]   #rand
    """
    assert bound >= 256, "bound must be at least 256."
    n = int(log(bound) / log(256))          # (1)
    salt = min(int(n/8) + 1, n-1)           # (2)
    i = 0; v = []
    while i < len(s):                       # (3)
        c = 0; pow = 1
        for j in range(n):                  # (4)
            if j < salt:
                c += randrange(1,256)*pow   # (5)
            else:
                if i >= len(s): break 
                c += ord(s[i])*pow          # (6)
                i += 1
            pow *= 256                      
        v.append(c)
    return v

def numlist_to_str(v, bound):
    """
    Returns the string that the sequence v of 
    integers encodes. 
    Input:
        v -- list of integers between 0 and bound-1
        bound -- an integer >= 256
    Output:
        str -- decoding of v as a string
    Examples:
    >>> print numlist_to_str([82, 117, 110, 33], 1000)
    Run!
    >>> x = str_to_numlist("TOP SECRET MESSAGE", 10**20)
    >>> print numlist_to_str(x, 10**20)
    TOP SECRET MESSAGE
    """
    assert bound >= 256, "bound must be at least 256."
    n = int(log(bound) / log(256))
    s = ""
    salt = min(int(n/8) + 1, n-1)
    for x in v:
        for j in range(n):
            y = x%256
            if y > 0 and j >= salt:
                s += chr(y)
            x /= 256
    return s


##################################################
## The RSA Cryptosystem
##################################################

def rsa_init(p, q):
    """
    Returns defining parameters (e, d, n) for the RSA
    cryptosystem defined by primes p and q.  The
    primes p and q may be computed using the 
    random_prime functions.
    Input:
        p -- a prime integer
        q -- a prime integer
    Output:
        Let m be (p-1)*(q-1). 
        e -- an encryption key, which is a randomly
             chosen integer between 2 and m-1
        d -- the inverse of e modulo eulerphi(p*q), 
             as an integer between 2 and m-1
        n -- the product p*q.
    Examples:
    >>> p = random_prime(20); q = random_prime(20)
    >>> print p, q
    37999414403893878907L 25910385856444296437L #rand
    >>> e, d, n = rsa_init(p, q)
    >>> e
    5                                           #rand
    >>> d
    787663591619054108576589014764921103213L    #rand
    >>> n
    984579489523817635784646068716489554359L    #rand
    """
    m = (p-1)*(q-1)
    e = 3
    while gcd(e, m) != 1: e += 1
    d = inversemod(e, m)                  
    return e, d, p*q

def rsa_encrypt(plain_text, e, n):
    """
    Encrypt plain_text using the encrypt
    exponent e and modulus n.  
    Input:
        plain_text -- arbitrary string
        e -- an integer, the encryption exponent
        n -- an integer, the modulus
    Output:
        str -- the encrypted cipher text
    Examples:
    >>> e = 1413636032234706267861856804566528506075
    >>> n = 2109029637390047474920932660992586706589
    >>> rsa_encrypt("Run Nikita!", e, n)
    [78151883112572478169375308975376279129L]    #rand
    >>> rsa_encrypt("Run Nikita!", e, n)
    [1136438061748322881798487546474756875373L]  #rand
    """
    plain = str_to_numlist(plain_text, n)
    return [powermod(x, e, n) for x in plain]

def rsa_decrypt(cipher, d, n):
    """
    Decrypt the cipher_text using the decryption
    exponent d and modulus n.
    Input:
        cipher_text -- list of integers output 
                       by rsa_encrypt
    Output:
        str -- the unencrypted plain text
    Examples:
    >>> d = 938164637865370078346033914094246201579
    >>> n = 2109029637390047474920932660992586706589
    >>> msg1 = [1071099761433836971832061585353925961069]
    >>> msg2 = [1336506586627416245118258421225335020977]
    >>> rsa_decrypt(msg1, d, n)
    'Run Nikita!'
    >>> rsa_decrypt(msg2, d, n)
    'Run Nikita!'
    """
    plain = [powermod(x, d, n) for x in cipher]
    return numlist_to_str(plain, n)


##################################################
## Computing the Legendre Symbol
##################################################

def legendre(a, p):
    """
    Returns the Legendre symbol a over p, where
    p is an odd prime.
    Input:
        a -- an integer
        p -- an odd prime (primality not checked)
    Output:
        int: -1 if a is not a square mod p,
              0 if gcd(a,p) is not 1
              1 if a is a square mod p.
    Examples:
    >>> legendre(2, 5)
    -1
    >>> legendre(3, 3)
    0
    >>> legendre(7, 2003)
    -1
    """
    assert p%2 == 1, "p must be an odd prime."
    b = powermod(a, (p-1)/2, p)
    if b == 1: return 1
    elif b == p-1: return -1
    return 0


##################################################
## In this section we implement the algorithm
##################################################

def sqrtmod(a, p):
    """
    Returns a square root of a modulo p.
    Input:
        a -- an integer that is a perfect 
             square modulo p (this is checked)
        p -- a prime
    Output:
        int -- a square root of a, as an integer
               between 0 and p-1.
    Examples:
    >>> sqrtmod(4, 5)              # p == 1 (mod 4)
    3              #rand
    >>> sqrtmod(13, 23)            # p == 3 (mod 4)
    6              #rand
    >>> sqrtmod(997, 7304723089)   # p == 1 (mod 4)
    761044645L     #rand
    """
    a %= p
    if p == 2: return a 
    assert legendre(a, p) == 1, "a must be a square mod p."
    if p%4 == 3: return powermod(a, (p+1)/4, p)

    def mul(x, y):   # multiplication in R       # (1)
        return ((x[0]*y[0] + a*y[1]*x[1]) % p, \
                (x[0]*y[1] + x[1]*y[0]) % p)
    def pow(x, n):   # exponentiation in R       # (2)
        ans = (1,0)
        xpow = x
        while n != 0:
           if n%2 != 0: ans = mul(ans, xpow)
           xpow = mul(xpow, xpow)
           n /= 2
        return ans

    while True:
        z = randrange(2,p)
        u, v = pow((1,z), (p-1)/2)
        if v != 0:
            vinv = inversemod(v, p)
            for x in [-u*vinv, (1-u)*vinv, (-1-u)*vinv]:
                if (x*x)%p == a: return x%p
            assert False, "Bug in sqrtmod."


##################################################
## Continued Fractions
##################################################

def convergents(v):
    """
    Returns the partial convergents of the continued 
    fraction v.
    Input:
        v -- list of integers [a0, a1, a2, ..., am]
    Output:
        list -- list [(p0,q0), (p1,q1), ...] 
                of pairs (pm,qm) such that the mth 
                convergent of v is pm/qm.
    Examples:
    >>> convergents([1, 2])
    [(1, 1), (3, 2)]
    >>> convergents([3, 7, 15, 1, 292])
    [(3, 1), (22, 7), (333, 106), (355, 113), (103993, 33102)]
    """
    w = [(0,1), (1,0)]
    for n in range(len(v)):
        pn = v[n]*w[n+1][0] + w[n][0]
        qn = v[n]*w[n+1][1] + w[n][1]
        w.append((pn, qn))
    del w[0]; del w[0]  # remove first entries of w
    return w

def contfrac_rat(numer, denom):
    """
    Returns the continued fraction of the rational 
    number numer/denom.
    Input:
        numer -- an integer
        denom -- a positive integer coprime to num
    Output
        list -- the continued fraction [a0, a1, ..., am]
                of the rational number num/denom.
    Examples:
    >>> contfrac_rat(3, 2)
    [1, 2]
    >>> contfrac_rat(103993, 33102)
    [3, 7, 15, 1, 292]
    """
    assert denom > 0, "denom must be positive"
    a = numer; b = denom
    v = []
    while b != 0:
        v.append(a/b)
        (a, b) = (b, a%b)
    return v

def contfrac_float(x):
    """
    Returns the continued fraction of the floating
    point number x, computed using the continued
    fraction procedure, and the sequence of partial
    convergents.
    Input:
        x -- a floating point number (decimal)
    Output:
        list -- the continued fraction [a0, a1, ...]
                obtained by applying the continued 
                fraction procedure to x to the 
                precision of this computer.
        list -- the list [(p0,q0), (p1,q1), ...] 
                of pairs (pm,qm) such that the mth 
                convergent of continued fraction 
                is pm/qm.
    Examples:
    >>> v, w = contfrac_float(3.14159); print v
    [3, 7, 15, 1, 25, 1, 7, 4]
    >>> v, w = contfrac_float(2.718); print v
    [2, 1, 2, 1, 1, 4, 1, 12]
    >>> contfrac_float(0.3)
    ([0, 3, 2, 1], [(0, 1), (1, 3), (2, 7), (3, 10)])
    """
    v = []
    w = [(0,1), (1,0)] # keep track of convergents
    start = x
    while True:
        a = int(x)                                  # (1)
        v.append(a)
        n = len(v)-1
        pn = v[n]*w[n+1][0] + w[n][0]
        qn = v[n]*w[n+1][1] + w[n][1]
        w.append((pn, qn))
        x -= a
        if abs(start - float(pn)/float(qn)) == 0:    # (2)
            del w[0]; del w[0]                       # (3)
            return v, w
        x = 1/x

def sum_of_two_squares(p):
    """
    Uses continued fractions to efficiently compute 
    a representation of the prime p as a sum of
    two squares.   The prime p must be 1 modulo 4.
    Input:
        p -- a prime congruent 1 modulo 4.
    Output:
        integers a, b such that p is a*a + b*b
    Examples:
    >>> sum_of_two_squares(5)
    (1, 2)
    >>> sum_of_two_squares(389)
    (10, 17)
    >>> sum_of_two_squares(86295641057493119033)
    (789006548L, 9255976973L)
    """
    assert p%4 == 1, "p must be 1 modulo 4"
    r = sqrtmod(-1, p)                                # (1)
    v = contfrac_rat(-r, p)                           # (2)
    n = int(sqrt(p))                          
    for a, b in convergents(v):                       # (3)
        c = r*b + p*a                                 # (4)
        if -n <= c and c <= n: return (abs(b),abs(c))
    assert False, "Bug in sum_of_two_squares."        # (5)


##################################################
## Arithmetic
##################################################

def ellcurve_add(E, P1, P2):
    """
    Returns the sum of P1 and P2 on the elliptic 
    curve E.
    Input:
         E -- an elliptic curve over Z/pZ, given by a 
              triple of integers (a, b, p), with p odd.
         P1 --a pair of integers (x, y) or the 
              string "Identity".
         P2 -- same type as P1
    Output:
         R -- same type as P1
    Examples:
    >>> E = (1, 0, 7)   # y**2 = x**3 + x over Z/7Z
    >>> P1 = (1, 3); P2 = (3, 3)
    >>> ellcurve_add(E, P1, P2)
    (3, 4)
    >>> ellcurve_add(E, P1, (1, 4))
    'Identity'
    >>> ellcurve_add(E, "Identity", P2)
    (3, 3)
    """ 
    a, b, p = E
    assert p > 2, "p must be odd."
    if P1 == "Identity": return P2
    if P2 == "Identity": return P1
    x1, y1 = P1; x2, y2 = P2
    x1 %= p; y1 %= p; x2 %= p; y2 %= p
    if x1 == x2 and y1 == p-y2: return "Identity"
    if P1 == P2:
        if y1 == 0: return "Identity"
        lam = (3*x1**2+a) * inversemod(2*y1,p)
    else:
        lam = (y1 - y2) * inversemod(x1 - x2, p)
    x3 = lam**2 - x1 - x2
    y3 = -lam*x3 - y1 + lam*x1
    return (x3%p, y3%p)

def ellcurve_mul(E, m, P):
    """
    Returns the multiple m*P of the point P on 
    the elliptic curve E.
    Input:
        E -- an elliptic curve over Z/pZ, given by a 
             triple (a, b, p).
        m -- an integer
        P -- a pair of integers (x, y) or the 
             string "Identity"
    Output:
        A pair of integers or the string "Identity".
    Examples:
    >>> E = (1, 0, 7)
    >>> P = (1, 3)
    >>> ellcurve_mul(E, 5, P)
    (1, 3)
    >>> ellcurve_mul(E, 9999, P)
    (1, 4)
    """   
    assert m >= 0, "m must be nonnegative."
    power = P
    mP = "Identity"
    while m != 0:
        if m%2 != 0: mP = ellcurve_add(E, mP, power)
        power = ellcurve_add(E, power, power)
        m /= 2
    return mP


##################################################
## Integer Factorization
##################################################

def lcm_to(B):
    """
    Returns the least common multiple of all 
    integers up to B.
    Input:
        B -- an integer
    Output:
        an integer
    Examples:
    >>> lcm_to(5)
    60
    >>> lcm_to(20)
    232792560
    >>> lcm_to(100)
    69720375229712477164533808935312303556800L
    """
    ans = 1
    logB = log(B)
    for p in primes(B):
        ans *= p**int(logB/log(p))
    return ans

def pollard(N, m):
    """
    Use Pollard's (p-1)-method to try to find a
    nontrivial divisor of N.
    Input:
        N -- a positive integer
        m -- a positive integer, the least common
             multiple of the integers up to some 
             bound, computed using lcm_to.
    Output:
        int -- an integer divisor of n
    Examples:
    >>> pollard(5917, lcm_to(5))
    61
    >>> pollard(779167, lcm_to(5))
    779167
    >>> pollard(779167, lcm_to(15))
    2003L
    >>> pollard(187, lcm_to(15))
    11
    >>> n = random_prime(5)*random_prime(5)*random_prime(5)
    >>> pollard(n, lcm_to(100))
    315873129119929L     #rand
    >>> pollard(n, lcm_to(1000))
    3672986071L          #rand
    """
    for a in [2, 3]:
        x = powermod(a, m, N) - 1
        g = gcd(x, N)
        if g != 1 and g != N:
            return g
    return N

def randcurve(p):
    """
    Construct a somewhat random elliptic curve 
    over Z/pZ and a random point on that curve.
    Input:
        p -- a positive integer
    Output:
        tuple -- a triple E = (a, b, p) 
        P -- a tuple (x,y) on E
    Examples:
    >>> p = random_prime(20); p
    17758176404715800329L    #rand
    >>> E, P = randcurve(p)
    >>> print E
    (15299007531923218813L, 1, 17758176404715800329L)  #rand
    >>> print P
    (0, 1)
    """
    assert p > 2, "p must be > 2."
    a = randrange(p)
    while gcd(4*a**3 + 27, p) != 1:
        a = randrange(p)
    return (a, 1, p), (0,1)

def elliptic_curve_method(N, m, tries=5):
    """
    Use the elliptic curve method to try to find a
    nontrivial divisor of N.
    Input:
        N -- a positive integer
        m -- a positive integer, the least common
             multiple of the integers up to some
             bound, computed using lcm_to.
        tries -- a positive integer, the number of
             different elliptic curves to try
    Output:
        int -- a divisor of n
    Examples:
    >>> elliptic_curve_method(5959, lcm_to(20))
    59L       #rand
    >>> elliptic_curve_method(10007*20011, lcm_to(100))
    10007L   #rand
    >>> p = random_prime(9); q = random_prime(9)
    >>> n = p*q; n
    117775675640754751L   #rand
    >>> elliptic_curve_method(n, lcm_to(100))
    117775675640754751L   #rand
    >>> elliptic_curve_method(n, lcm_to(500))
    117775675640754751L   #rand
    """
    for _ in range(tries):                     # (1)
        E, P = randcurve(N)                    # (2)
        try:                                   # (3)
            Q = ellcurve_mul(E, m, P)          # (4)
        except ZeroDivisionError, x:           # (5)
            g = gcd(x[0],N)                    # (6)
            if g != 1 or g != N: return g      # (7)
    return N             


##################################################
## ElGamal Elliptic Curve Cryptosystem
##################################################

def elgamal_init(p):
    """
    Constructs an ElGamal cryptosystem over Z/pZ, by
    choosing a random elliptic curve E over Z/pZ, a 
    point B in E(Z/pZ), and a random integer n.  This
    function returns the public key as a 4-tuple 
    (E, B, n*B) and the private key n.
    Input:
        p -- a prime number
    Output:
        tuple -- the public key as a 3-tuple
                 (E, B, n*B), where E = (a, b, p) is an 
                 elliptic curve over Z/pZ, B = (x, y) is
                 a point on E, and n*B = (x',y') is
                 the sum of B with itself n times.
        int -- the private key, which is the pair (E, n)
    Examples:
    >>> p = random_prime(20); p
    17758176404715800329L    #rand
    >>> public, private = elgamal_init(p)
    >>> print "E =", public[0]
    E = (15299007531923218813L, 1, 17758176404715800329L)   #rand
    >>> print "B =", public[1]
    B = (0, 1)
    >>> print "nB =", public[2]
    nB = (5619048157825840473L, 151469105238517573L)   #rand
    >>> print "n =", private[1]
    n = 12608319787599446459    #rand
    """
    E, B = randcurve(p)
    n = randrange(2,p)    
    nB = ellcurve_mul(E, n, B)
    return (E, B, nB), (E, n)

def elgamal_encrypt(plain_text, public_key):
    """
    Encrypt a message using the ElGamal cryptosystem
    with given public_key = (E, B, n*B).
    Input:
       plain_text -- a string
       public_key -- a triple (E, B, n*B), as output
                     by elgamal_init.
    Output:
       list -- a list of pairs of points on E that 
               represent the encrypted message
    Examples:
    >>> public, private = elgamal_init(random_prime(20))
    >>> elgamal_encrypt("RUN", public)
    [((6004308617723068486L, 15578511190582849677L), \ #rand
     (7064405129585539806L, 8318592816457841619L))]    #rand
    """
    E, B, nB = public_key
    a, b, p = E 
    assert p > 10000, "p must be at least 10000."
    v = [1000*x for x in \
           str_to_numlist(plain_text, p/1000)]       # (1)
    cipher = []
    for x in v:
        while not legendre(x**3+a*x+b, p)==1:        # (2)
            x = (x+1)%p  
        y = sqrtmod(x**3+a*x+b, p)                   # (3)
        P = (x,y)    
        r = randrange(1,p)
        encrypted = (ellcurve_mul(E, r, B), \
                ellcurve_add(E, P, ellcurve_mul(E,r,nB)))
        cipher.append(encrypted)
    return cipher   

def elgamal_decrypt(cipher_text, private_key):
    """
    Encrypt a message using the ElGamal cryptosystem
    with given public_key = (E, B, n*B).
    Input:
        cipher_text -- list of pairs of points on E output
                       by elgamal_encrypt.
    Output:
        str -- the unencrypted plain text
    Examples:
    >>> public, private = elgamal_init(random_prime(20))
    >>> v = elgamal_encrypt("TOP SECRET MESSAGE!", public)
    >>> print elgamal_decrypt(v, private)
    TOP SECRET MESSAGE!
    """
    E, n = private_key
    p = E[2]
    plain = []
    for rB, P_plus_rnB in cipher_text:
        nrB = ellcurve_mul(E, n, rB)
        minus_nrB = (nrB[0], -nrB[1])
        P = ellcurve_add(E, minus_nrB, P_plus_rnB)
        plain.append(P[0]/1000)
    return numlist_to_str(plain, p/1000)


##################################################
## Associativity of the Group Law
##################################################

# The variable order is x1, x2, x3, y1, y2, y3, a, b
class Poly:                                     # (1)
    def __init__(self, d):                      # (2)
        self.v = dict(d)                        
    def __cmp__(self, other):                   # (3)
        self.normalize(); other.normalize()     # (4)
        if self.v == other.v: return 0
        return -1

    def __add__(self, other):                   # (5)
        w = Poly(self.v)
        for m in other.monomials():
            w[m] += other[m]
        return w
    def __sub__(self, other):
        w = Poly(self.v)
        for m in other.monomials():
            w[m] -= other[m]
        return w
    def __mul__(self, other):
        if len(self.v) == 0 or len(other.v) == 0: 
            return Poly([])
        m1 = self.monomials(); m2 = other.monomials()
        r = Poly([])
        for m1 in self.monomials():
            for m2 in other.monomials():
                z = [m1[i] + m2[i] for i in range(8)]
                r[z] += self[m1]*other[m2]
        return r
    def __neg__(self):
        v = {}
        for m in self.v.keys():
            v[m] = -self.v[m]
        return Poly(v)
    def __div__(self, other):
        return Frac(self, other)

    def __getitem__(self, m):                   # (6)
        m = tuple(m)
        if not self.v.has_key(m): self.v[m] = 0
        return self.v[m]
    def __setitem__(self, m, c):
        self.v[tuple(m)] = c
    def __delitem__(self, m):
        del self.v[tuple(m)]

    def monomials(self):                        # (7)
        return self.v.keys()
    def normalize(self):                        # (8)
        while True:
            finished = True
            for m in self.monomials():
                if self[m] == 0:
                    del self[m]
                    continue
                for i in range(3):
                    if m[3+i] >= 2:  
                        finished = False
                        nx0 = list(m); nx0[3+i] -= 2; 
                        nx0[7] += 1
                        nx1 = list(m); nx1[3+i] -= 2; 
                        nx1[i] += 1; nx1[6] += 1
                        nx3 = list(m); nx3[3+i] -= 2; 
                        nx3[i] += 3
                        c = self[m]
                        del self[m]
                        self[nx0] += c; 
                        self[nx1] += c; 
                        self[nx3] += c
                # end for
            # end for
            if finished: return
        # end while

one = Poly({(0,0,0,0,0,0,0,0):1})               # (9)

class Frac:                                     # (10)
    def __init__(self, num, denom=one):         
        self.num = num; self.denom = denom
    def __cmp__(self, other):                   # (11)
        if self.num * other.denom == self.denom * other.num:
            return 0
        return -1

    def __add__(self, other):                   # (12)
        return Frac(self.num*other.denom + \
                    self.denom*other.num, 
                    self.denom*other.denom)
    def __sub__(self, other):
        return Frac(self.num*other.denom - \
                    self.denom*other.num,
                    self.denom*other.denom)
    def __mul__(self, other):
        return Frac(self.num*other.num, \
                    self.denom*other.denom)
    def __div__(self, other):
        return Frac(self.num*other.denom, \
                    self.denom*other.num)
    def __neg__(self):
        return Frac(-self.num,self.denom)

def var(i):                                     # (14)
    v = [0,0,0,0,0,0,0,0]; v[i]=1; 
    return Frac(Poly({tuple(v):1}))

def prove_associative():                        # (15)
    x1 = var(0); x2 = var(1); x3 = var(2)
    y1 = var(3); y2 = var(4); y3 = var(5)
    a  = var(6); b  = var(7)
    
    lambda12 = (y1 - y2)/(x1 - x2)              
    x4       = lambda12*lambda12 - x1 - x2
    nu12     = y1 - lambda12*x1   
    y4       = -lambda12*x4 - nu12
    lambda23 = (y2 - y3)/(x2 - x3)
    x5       = lambda23*lambda23 - x2 - x3
    nu23     = y2 - lambda23*x2
    y5       = -lambda23*x5 - nu23
    s1 = (x1 - x5)*(x1 - x5)*((y3 - y4)*(y3 - y4) \
                   - (x3 + x4)*(x3 - x4)*(x3 - x4))
    s2 = (x3 - x4)*(x3 - x4)*((y1 - y5)*(y1 - y5) \
                   - (x1 + x5)*(x1 - x5)*(x1 - x5))
    print "Associative?"
    print s1 == s2                              # (17)















##########################################################
# The following are all the examples not in functions.   #
##########################################################

def examples():
    """
    >>> from ent import *
    >>> 7/5
    1
    >>> -2/3
    -1
    >>> 1.0/3
    0.33333333333333331
    >>> float(2)/3
    0.66666666666666663
    >>> 100**2
    10000
    >>> 10**20
    100000000000000000000L
    >>> range(10)            # range(n) is from 0 to n-1       
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> range(3,10)          # range(a,b) is from a to b-1
    [3, 4, 5, 6, 7, 8, 9]
    >>> [x**2 for x in range(10)]
    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
    >>> [x**2 for x in range(10) if x%4 == 1]
    [1, 25, 81]
    >>> [1,2,3] + [5,6,7]    # concatenation
    [1, 2, 3, 5, 6, 7]
    >>> len([1,2,3,4,5])     # length of a list
    5
    >>> x = [4,7,10,'gcd']   # mixing types is fine
    >>> x[0]                 # 0-based indexing
    4
    >>> x[3]
    'gcd'
    >>> x[3] = 'lagrange'    # assignment
    >>> x.append("fermat")   # append to end of list
    >>> x
    [4, 7, 10, 'lagrange', 'fermat']
    >>> del x[3]             # delete entry 3 from list
    >>> x
    [4, 7, 10, 'fermat']
    >>> v = primes(10000)
    >>> len(v)    # this is pi(10000)
    1229
    >>> len([x for x in v if x < 1000])   # pi(1000)
    168
    >>> len([x for x in v if x < 5000])   # pi(5000)
    669
    >>> x=(1, 2, 3)       # creation
    >>> x[1]
    2
    >>> (1, 2, 3) + (4, 5, 6)  # concatenation
    (1, 2, 3, 4, 5, 6)
    >>> (a, b) = (1, 2)        # assignment assigns to each member
    >>> print a, b
    1 2
    >>> for (c, d) in [(1,2), (5,6)]:   
    ...     print c, d
    1 2
    5 6
    >>> x = 1, 2          # parentheses optional in creation
    >>> x
    (1, 2)
    >>> c, d = x          # parentheses also optional 
    >>> print c, d
    1 2
    >>> P = [p for p in range(200000) if is_pseudoprime(p)]
    >>> Q = primes(200000)
    >>> R = [x for x in P if not (x in Q)]; print R
    [29341, 46657, 75361, 115921, 162401]
    >>> [n for n in R if is_pseudoprime(n,[2,3,5,7,11,13])]
    [162401]
    >>> factor(162401)
    [(17, 1), (41, 1), (233, 1)]
    >>> p = random_prime(50)
    >>> p
    13537669335668960267902317758600526039222634416221L #rand
    >>> n, npow = dh_init(p)
    >>> n
    8520467863827253595224582066095474547602956490963L  #rand
    >>> npow
    3206478875002439975737792666147199399141965887602L  #rand
    >>> m, mpow = dh_init(p)
    >>> m
    3533715181946048754332697897996834077726943413544L  #rand
    >>> mpow
    3465862701820513569217254081716392362462604355024L  #rand
    >>> dh_secret(p, n, mpow)
    12931853037327712933053975672241775629043437267478L #rand
    >>> dh_secret(p, m, npow)
    12931853037327712933053975672241775629043437267478L #rand
    >>> prove_associative()
    Associative?
    True
    >>> len(primes(10000))
    1229
    >>> 10000/log(10000)
    1085.73620476
    >>> powermod(3,45,100)
    43
    >>> inversemod(37, 112)
    109
    >>> powermod(102, 70, 113)
    98
    >>> powermod(99, 109, 113)
    60
    >>> P = primes(1000)
    >>> Q = [p for p in P if primitive_root(p) == 2]
    >>> print len(Q), len(P)
    67 168
    >>> P = primes(50000)
    >>> Q = [primitive_root(p) for p in P]
    >>> Q.index(37)
    3893
    >>> P[3893]
    36721
    >>> for n in range(97):
    ...     if powermod(5,n,97)==3: print n
    70
    >>> factor(5352381469067)
    [(141307, 1), (37877681L, 1)]
    >>> d=inversemod(4240501142039, (141307-1)*(37877681-1))
    >>> d
    5195621988839L
    >>> convergents([-3,1,1,1,1,3])
    [(-3, 1), (-2, 1), (-5, 2), (-7, 3), \
              (-12, 5), (-43, 18)]
    >>> convergents([0,2,4,1,8,2])
    [(0, 1), (1, 2), (4, 9), (5, 11), \
              (44, 97), (93, 205)]
    >>> import math
    >>> e = math.exp(1)
    >>> v, convs = contfrac_float(e)
    >>> [(a,b) for a, b in convs if \
           abs(e - a*1.0/b) < 1/(math.sqrt(5)*b**2)]
    [(3, 1), (19, 7), (193, 71), (2721, 1001),\
     (49171, 18089), (1084483, 398959),\
     (28245729, 10391023), (325368125, 119696244)]
    >>> factor(12345)
    [(3, 1), (5, 1), (823, 1)]
    >>> factor(729)
    [(3, 6)]
    >>> factor(5809961789)
    [(5809961789L, 1)]
    >>> 5809961789 % 4
    1L
    >>> sum_of_two_squares(5809961789)
    (51542L, 56155L)
    >>> N = [60 + s for s in range(-15,16)]
    >>> def is_powersmooth(B, x):
    ...     for p, e in factor(x):
    ...         if p**e > B: return False
    ...     return True
    >>> Ns = [x for x in N if is_powersmooth(20, x)]
    >>> print len(Ns), len(N), len(Ns)*1.0/len(N)
    14 31 0.451612903226
    >>> P = [x for x in range(10**12, 10**12+1000)\
             if miller_rabin(x)]
    >>> Ps = [x for x in P if \
             is_powersmooth(10000, x-1)]  
    >>> print len(Ps), len(P), len(Ps)*1.0/len(P)
    2 37 0.0540540540541
    
    """


if __name__ ==  '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])

########NEW FILE########
__FILENAME__ = randpool
#
#  randpool.py : Cryptographically strong random number generation
#
# Part of the Python Cryptography Toolkit
#
# Distribute and use freely; there are no restrictions on further
# dissemination and usage except those imposed by the laws of your
# country of residence.  This software is provided "as is" without
# warranty of fitness for use or suitability for any purpose, express
# or implied. Use at your own risk or not at all.
#

__revision__ = "$Id: randpool.py,v 1.14 2004/05/06 12:56:54 akuchling Exp $"

import time, array, types, warnings, os.path
from number import long_to_bytes
try:
    import Crypto.Util.winrandom as winrandom
except:
    winrandom = None

STIRNUM = 3

class RandomPool:
    """randpool.py : Cryptographically strong random number generation.

    The implementation here is similar to the one in PGP.  To be
    cryptographically strong, it must be difficult to determine the RNG's
    output, whether in the future or the past.  This is done by using
    a cryptographic hash function to "stir" the random data.

    Entropy is gathered in the same fashion as PGP; the highest-resolution
    clock around is read and the data is added to the random number pool.
    A conservative estimate of the entropy is then kept.

    If a cryptographically secure random source is available (/dev/urandom
    on many Unixes, Windows CryptGenRandom on most Windows), then use
    it.

    Instance Attributes:
    bits : int
      Maximum size of pool in bits
    bytes : int
      Maximum size of pool in bytes
    entropy : int
      Number of bits of entropy in this pool.

    Methods:
    add_event([s]) : add some entropy to the pool
    get_bytes(int) : get N bytes of random data
    randomize([N]) : get N bytes of randomness from external source
    """


    def __init__(self, numbytes = 160, cipher=None, hash=None):
        if hash is None:
            from hashlib import sha1 as hash

        # The cipher argument is vestigial; it was removed from
        # version 1.1 so RandomPool would work even in the limited
        # exportable subset of the code
        if cipher is not None:
            warnings.warn("'cipher' parameter is no longer used")

        if isinstance(hash, types.StringType):
            # ugly hack to force __import__ to give us the end-path module
            hash = __import__('Crypto.Hash.'+hash,
                              None, None, ['new'])
            warnings.warn("'hash' parameter should now be a hashing module")

        self.bytes = numbytes
        self.bits = self.bytes*8
        self.entropy = 0
        self._hash = hash

        # Construct an array to hold the random pool,
        # initializing it to 0.
        self._randpool = array.array('B', [0]*self.bytes)

        self._event1 = self._event2 = 0
        self._addPos = 0
        self._getPos = hash().digest_size
        self._lastcounter=time.time()
        self.__counter = 0

        self._measureTickSize()        # Estimate timer resolution
        self._randomize()

    def _updateEntropyEstimate(self, nbits):
        self.entropy += nbits
        if self.entropy < 0:
            self.entropy = 0
        elif self.entropy > self.bits:
            self.entropy = self.bits

    def _randomize(self, N = 0, devname = '/dev/urandom'):
        """_randomize(N, DEVNAME:device-filepath)
        collects N bits of randomness from some entropy source (e.g.,
        /dev/urandom on Unixes that have it, Windows CryptoAPI
        CryptGenRandom, etc)
        DEVNAME is optional, defaults to /dev/urandom.  You can change it
        to /dev/random if you want to block till you get enough
        entropy.
        """
        data = ''
        if N <= 0:
            nbytes = int((self.bits - self.entropy)/8+0.5)
        else:
            nbytes = int(N/8+0.5)
        if winrandom:
            # Windows CryptGenRandom provides random data.
            data = winrandom.new().get_bytes(nbytes)
        # GAE fix, benadida
        #elif os.path.exists(devname):
        #    # Many OSes support a /dev/urandom device
        #    try:
        #        f=open(devname)
        #        data=f.read(nbytes)
        #        f.close()
        #    except IOError, (num, msg):
        #        if num!=2: raise IOError, (num, msg)
        #        # If the file wasn't found, ignore the error
        if data:
            self._addBytes(data)
            # Entropy estimate: The number of bits of
            # data obtained from the random source.
            self._updateEntropyEstimate(8*len(data))
        self.stir_n()                   # Wash the random pool

    def randomize(self, N=0):
        """randomize(N:int)
        use the class entropy source to get some entropy data.
        This is overridden by KeyboardRandomize().
        """
        return self._randomize(N)

    def stir_n(self, N = STIRNUM):
        """stir_n(N)
        stirs the random pool N times
        """
        for i in xrange(N):
            self.stir()

    def stir (self, s = ''):
        """stir(s:string)
        Mix up the randomness pool.  This will call add_event() twice,
        but out of paranoia the entropy attribute will not be
        increased.  The optional 's' parameter is a string that will
        be hashed with the randomness pool.
        """

        entropy=self.entropy            # Save inital entropy value
        self.add_event()

        # Loop over the randomness pool: hash its contents
        # along with a counter, and add the resulting digest
        # back into the pool.
        for i in range(self.bytes / self._hash().digest_size):
            h = self._hash(self._randpool)
            h.update(str(self.__counter) + str(i) + str(self._addPos) + s)
            self._addBytes( h.digest() )
            self.__counter = (self.__counter + 1) & 0xFFFFffffL

        self._addPos, self._getPos = 0, self._hash().digest_size
        self.add_event()

        # Restore the old value of the entropy.
        self.entropy=entropy


    def get_bytes (self, N):
        """get_bytes(N:int) : string
        Return N bytes of random data.
        """

        s=''
        i, pool = self._getPos, self._randpool
        h=self._hash()
        dsize = self._hash().digest_size
        num = N
        while num > 0:
            h.update( self._randpool[i:i+dsize] )
            s = s + h.digest()
            num = num - dsize
            i = (i + dsize) % self.bytes
            if i<dsize:
                self.stir()
                i=self._getPos

        self._getPos = i
        self._updateEntropyEstimate(- 8*N)
        return s[:N]


    def add_event(self, s=''):
        """add_event(s:string)
        Add an event to the random pool.  The current time is stored
        between calls and used to estimate the entropy.  The optional
        's' parameter is a string that will also be XORed into the pool.
        Returns the estimated number of additional bits of entropy gain.
        """
        event = time.time()*1000
        delta = self._noise()
        s = (s + long_to_bytes(event) +
             4*chr(0xaa) + long_to_bytes(delta) )
        self._addBytes(s)
        if event==self._event1 and event==self._event2:
            # If events are coming too closely together, assume there's
            # no effective entropy being added.
            bits=0
        else:
            # Count the number of bits in delta, and assume that's the entropy.
            bits=0
            while delta:
                delta, bits = delta>>1, bits+1
            if bits>8: bits=8

        self._event1, self._event2 = event, self._event1

        self._updateEntropyEstimate(bits)
        return bits

    # Private functions
    def _noise(self):
        # Adds a bit of noise to the random pool, by adding in the
        # current time and CPU usage of this process.
        # The difference from the previous call to _noise() is taken
        # in an effort to estimate the entropy.
        t=time.time()
        delta = (t - self._lastcounter)/self._ticksize*1e6
        self._lastcounter = t
        self._addBytes(long_to_bytes(long(1000*time.time())))
        self._addBytes(long_to_bytes(long(1000*time.clock())))
        self._addBytes(long_to_bytes(long(1000*time.time())))
        self._addBytes(long_to_bytes(long(delta)))

        # Reduce delta to a maximum of 8 bits so we don't add too much
        # entropy as a result of this call.
        delta=delta % 0xff
        return int(delta)


    def _measureTickSize(self):
        # _measureTickSize() tries to estimate a rough average of the
        # resolution of time that you can see from Python.  It does
        # this by measuring the time 100 times, computing the delay
        # between measurements, and taking the median of the resulting
        # list.  (We also hash all the times and add them to the pool)
        interval = [None] * 100
        h = self._hash(`(id(self),id(interval))`)

        # Compute 100 differences
        t=time.time()
        h.update(`t`)
        i = 0
        j = 0
        while i < 100:
            t2=time.time()
            h.update(`(i,j,t2)`)
            j += 1
            delta=int((t2-t)*1e6)
            if delta:
                interval[i] = delta
                i += 1
                t=t2

        # Take the median of the array of intervals
        interval.sort()
        self._ticksize=interval[len(interval)/2]
        h.update(`(interval,self._ticksize)`)
        # mix in the measurement times and wash the random pool
        self.stir(h.digest())

    def _addBytes(self, s):
        "XOR the contents of the string S into the random pool"
        i, pool = self._addPos, self._randpool
        for j in range(0, len(s)):
            pool[i]=pool[i] ^ ord(s[j])
            i=(i+1) % self.bytes
        self._addPos = i

    # Deprecated method names: remove in PCT 2.1 or later.
    def getBytes(self, N):
        warnings.warn("getBytes() method replaced by get_bytes()",
                      DeprecationWarning)
        return self.get_bytes(N)

    def addEvent (self, event, s=""):
        warnings.warn("addEvent() method replaced by add_event()",
                      DeprecationWarning)
        return self.add_event(s + str(event))

class PersistentRandomPool (RandomPool):
    def __init__ (self, filename=None, *args, **kwargs):
        RandomPool.__init__(self, *args, **kwargs)
        self.filename = filename
        if filename:
            try:
                # the time taken to open and read the file might have
                # a little disk variability, modulo disk/kernel caching...
                f=open(filename, 'rb')
                self.add_event()
                data = f.read()
                self.add_event()
                # mix in the data from the file and wash the random pool
                self.stir(data)
                f.close()
            except IOError:
                # Oh, well; the file doesn't exist or is unreadable, so
                # we'll just ignore it.
                pass

    def save(self):
        if self.filename == "":
            raise ValueError, "No filename set for this object"
        # wash the random pool before save, provides some forward secrecy for
        # old values of the pool.
        self.stir_n()
        f=open(self.filename, 'wb')
        self.add_event()
        f.write(self._randpool.tostring())
        f.close()
        self.add_event()
        # wash the pool again, provide some protection for future values
        self.stir()

# non-echoing Windows keyboard entry
_kb = 0
if not _kb:
    try:
        import msvcrt
        class KeyboardEntry:
            def getch(self):
                c = msvcrt.getch()
                if c in ('\000', '\xe0'):
                    # function key
                    c += msvcrt.getch()
                return c
            def close(self, delay = 0):
                if delay:
                    time.sleep(delay)
                    while msvcrt.kbhit():
                        msvcrt.getch()
        _kb = 1
    except:
        pass

# non-echoing Posix keyboard entry
if not _kb:
    try:
        import termios
        class KeyboardEntry:
            def __init__(self, fd = 0):
                self._fd = fd
                self._old = termios.tcgetattr(fd)
                new = termios.tcgetattr(fd)
                new[3]=new[3] & ~termios.ICANON & ~termios.ECHO
                termios.tcsetattr(fd, termios.TCSANOW, new)
            def getch(self):
                termios.tcflush(0, termios.TCIFLUSH) # XXX Leave this in?
                return os.read(self._fd, 1)
            def close(self, delay = 0):
                if delay:
                    time.sleep(delay)
                    termios.tcflush(self._fd, termios.TCIFLUSH)
                termios.tcsetattr(self._fd, termios.TCSAFLUSH, self._old)
        _kb = 1
    except:
        pass

class KeyboardRandomPool (PersistentRandomPool):
    def __init__(self, *args, **kwargs):
        PersistentRandomPool.__init__(self, *args, **kwargs)

    def randomize(self, N = 0):
        "Adds N bits of entropy to random pool.  If N is 0, fill up pool."
        import os, string, time
        if N <= 0:
            bits = self.bits - self.entropy
        else:
            bits = N*8
        if bits == 0:
            return
        print bits,'bits of entropy are now required.  Please type on the keyboard'
        print 'until enough randomness has been accumulated.'
        kb = KeyboardEntry()
        s=''    # We'll save the characters typed and add them to the pool.
        hash = self._hash
        e = 0
        try:
            while e < bits:
                temp=str(bits-e).rjust(6)
                os.write(1, temp)
                s=s+kb.getch()
                e += self.add_event(s)
                os.write(1, 6*chr(8))
            self.add_event(s+hash.new(s).digest() )
        finally:
            kb.close()
        print '\n\007 Enough.  Please wait a moment.\n'
        self.stir_n()   # wash the random pool.
        kb.close(4)

if __name__ == '__main__':
    pool = RandomPool()
    print 'random pool entropy', pool.entropy, 'bits'
    pool.add_event('something')
    print `pool.get_bytes(100)`
    import tempfile, os
    fname = tempfile.mktemp()
    pool = KeyboardRandomPool(filename=fname)
    print 'keyboard random pool entropy', pool.entropy, 'bits'
    pool.randomize()
    print 'keyboard random pool entropy', pool.entropy, 'bits'
    pool.randomize(128)
    pool.save()
    saved = open(fname, 'rb').read()
    print 'saved', `saved`
    print 'pool ', `pool._randpool.tostring()`
    newpool = PersistentRandomPool(fname)
    print 'persistent random pool entropy', pool.entropy, 'bits'
    os.remove(fname)

########NEW FILE########
__FILENAME__ = utils
"""
Crypto Utils
"""

import hmac, base64

from django.utils import simplejson

from hashlib import sha256
  
def hash_b64(s):
  """
  hash the string using sha1 and produce a base64 output
  removes the trailing "="
  """
  hasher = sha256(s)
  result= base64.b64encode(hasher.digest())[:-1]
  return result

def to_json(d):
  return simplejson.dumps(d, sort_keys=True)

def from_json(json_str):
  if not json_str: return None
  return simplejson.loads(json_str)

########NEW FILE########
__FILENAME__ = 01
"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject, arrayOf, DictObject, ListObject

class Trustee(LDObject):
  """
  a trustee
  """
  
  FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']
  STRUCTURED_FIELDS = {
    'pok' : 'pkc/elgamal/DiscreteLogProof',
    'public_key' : 'pkc/elgamal/PublicKey'
    }

  # removed some public key processing for now
 
class Election(LDObject):
  FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
            'frozen_at', 'public_key', 'cast_url', 'use_advanced_audit_features', 
            'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']
  
  STRUCTURED_FIELDS = {
    'public_key' : 'pkc/elgamal/PublicKey',
    'voting_starts_at': 'core/Timestamp',
    'voting_ends_at': 'core/Timestamp',
    'frozen_at': 'core/Timestamp',
    'questions': '2011/01/Questions',
    }

class Voter(LDObject):
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']

class EncryptedAnswer(LDObject):
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('pkc/elgamal/EGCiphertext'),
        'individual_proofs': arrayOf('pkc/elgamal/DisjunctiveProof'),
        'overall_proof' : 'pkc/elgamal/DisjunctiveProof',
        'randomness' : 'core/BigInteger'
        # answer is not a structured field, it's an as-is integer
        }


class Questions(ListObject, LDObject):
    WRAPPED_OBJ = list


########NEW FILE########
__FILENAME__ = core
"""
core data types
"""

from helios.datatypes import LDObject

class BigInteger(LDObject):
    """
    A big integer is an integer serialized as a string.
    We may want to b64 encode here soon.    
    """
    WRAPPED_OBJ_CLASS = int

    def toDict(self, complete=False):
        if self.wrapped_obj:
            return str(self.wrapped_obj)
        else:
            return None

    def loadDataFromDict(self, d):
        "take a string and cast it to an int -- which is a big int too"
        self.wrapped_obj = int(d)

class Timestamp(LDObject):
    def toDict(self, complete=False):
        if self.wrapped_obj:
            return str(self.wrapped_obj)
        else:
            return None
    

########NEW FILE########
__FILENAME__ = djangofield
"""
taken from

http://www.djangosnippets.org/snippets/377/

and adapted to LDObject
"""

import datetime
from django.db import models
from django.db.models import signals
from django.conf import settings
from django.utils import simplejson as json
from django.core.serializers.json import DjangoJSONEncoder

from . import LDObject

class LDObjectField(models.TextField):
    """
    LDObject is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    
    deserialization_params added on 2011-01-09 to provide additional hints at deserialization time
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def __init__(self, type_hint=None, **kwargs):
        self.type_hint = type_hint
        super(LDObjectField, self).__init__(**kwargs)

    def to_python(self, value):
        """Convert our string value to LDObject after we load it from the DB"""

        # did we already convert this?
        if not isinstance(value, basestring):
            return value

        if  value == None:
            return None

        # in some cases, we're loading an existing array or dict,
        # we skip this part but instantiate the LD object
        if isinstance(value, basestring):
            try:
                parsed_value = json.loads(value)
            except:
                raise Exception("value is not JSON parseable, that's bad news")
        else:
            parsed_value = value

        if parsed_value != None:
            "we give the wrapped object back because we're not dealing with serialization types"            
            return_val = LDObject.fromDict(parsed_value, type_hint = self.type_hint).wrapped_obj
            return return_val
        else:
            return None

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        if isinstance(value, basestring):
            return value

        if value == None:
            return None

        # instantiate the proper LDObject to dump it appropriately
        ld_object = LDObject.instantiate(value, datatype=self.type_hint)
        return ld_object.serialize()

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

##
## for schema migration, we have to tell South about JSONField
## basically that it's the same as its parent class
##
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^helios\.datatypes\.djangofield.LDObjectField"])

########NEW FILE########
__FILENAME__ = legacy
"""
Legacy datatypes for Helios (v3.0)
"""

from helios.datatypes import LDObject, arrayOf, DictObject, ListObject
from helios.crypto import elgamal as crypto_elgamal
from helios.workflows import homomorphic
from helios import models

##
##

class LegacyObject(LDObject):
    WRAPPED_OBJ_CLASS = dict
    USE_JSON_LD = False

class Election(LegacyObject):
    WRAPPED_OBJ_CLASS = models.Election
    FIELDS = ['uuid', 'questions', 'name', 'short_name', 'description', 'voters_hash', 'openreg',
              'frozen_at', 'public_key', 'cast_url', 'use_voter_aliases', 'voting_starts_at', 'voting_ends_at']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'voting_starts_at': 'core/Timestamp',
        'voting_ends_at': 'core/Timestamp',
        'frozen_at': 'core/Timestamp'
        }

class EncryptedAnswer(LegacyObject):
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedAnswer
    FIELDS = ['choices', 'individual_proofs', 'overall_proof']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'individual_proofs': arrayOf('legacy/EGZKDisjunctiveProof'),
        'overall_proof' : 'legacy/EGZKDisjunctiveProof'
        }

class EncryptedAnswerWithRandomness(LegacyObject):
    FIELDS = ['choices', 'individual_proofs', 'overall_proof', 'randomness', 'answer']
    STRUCTURED_FIELDS = {
        'choices': arrayOf('legacy/EGCiphertext'),
        'individual_proofs': arrayOf('legacy/EGZKDisjunctiveProof'),
        'overall_proof' : 'legacy/EGZKDisjunctiveProof',
        'randomness' : arrayOf('core/BigInteger')
        }

class EncryptedVote(LegacyObject):
    """
    An encrypted ballot
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers' : arrayOf('legacy/EncryptedAnswer')
        }

    def includeRandomness(self):
        return self.instantiate(self.wrapped_obj, datatype='legacy/EncryptedVoteWithRandomness')

class EncryptedVoteWithRandomness(LegacyObject):
    """
    An encrypted ballot with randomness for answers
    """
    WRAPPED_OBJ_CLASS = homomorphic.EncryptedVote
    FIELDS = ['answers', 'election_hash', 'election_uuid']
    STRUCTURED_FIELDS = {
        'answers' : arrayOf('legacy/EncryptedAnswerWithRandomness')
        }
    

class Voter(LegacyObject):
    FIELDS = ['election_uuid', 'uuid', 'voter_type', 'voter_id_hash', 'name']

    ALIASED_VOTER_FIELDS = ['election_uuid', 'uuid', 'alias']

    def toDict(self, complete=False):
        """
        depending on whether the voter is aliased, use different fields
        """
        if self.wrapped_obj.alias != None:
            return super(Voter, self).toDict(self.ALIASED_VOTER_FIELDS, complete = complete)
        else:
            return super(Voter,self).toDict(complete = complete)


class ShortCastVote(LegacyObject):
    FIELDS = ['cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {'cast_at' : 'core/Timestamp'}

class CastVote(LegacyObject):
    FIELDS = ['vote', 'cast_at', 'voter_uuid', 'voter_hash', 'vote_hash']
    STRUCTURED_FIELDS = {
        'cast_at' : 'core/Timestamp',
        'vote' : 'legacy/EncryptedVote'}

    @property
    def short(self):
        return self.instantiate(self.wrapped_obj, datatype='legacy/ShortCastVote')

class Trustee(LegacyObject):
    FIELDS = ['uuid', 'public_key', 'public_key_hash', 'pok', 'decryption_factors', 'decryption_proofs', 'email']

    STRUCTURED_FIELDS = {
        'public_key' : 'legacy/EGPublicKey',
        'pok': 'legacy/DLogProof',
        'decryption_factors': arrayOf(arrayOf('core/BigInteger')),
        'decryption_proofs' : arrayOf(arrayOf('legacy/EGZKProof'))}

class EGParams(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.Cryptosystem
    FIELDS = ['p', 'q', 'g']
    STRUCTURED_FIELDS = {
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'}

class EGPublicKey(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.PublicKey
    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y': 'core/BigInteger',
        'p': 'core/BigInteger',
        'q': 'core/BigInteger',
        'g': 'core/BigInteger'}

class EGSecretKey(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.SecretKey
    FIELDS = ['x','public_key']
    STRUCTURED_FIELDS = {
        'x': 'core/BigInteger',
        'public_key': 'legacy/EGPublicKey'}

class EGCiphertext(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.Ciphertext
    FIELDS = ['alpha','beta']
    STRUCTURED_FIELDS = {
        'alpha': 'core/BigInteger',
        'beta' : 'core/BigInteger'}

class EGZKProofCommitment(DictObject, LegacyObject):
    FIELDS = ['A', 'B']
    STRUCTURED_FIELDS = {
        'A' : 'core/BigInteger',
        'B' : 'core/BigInteger'}

    
class EGZKProof(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.ZKProof
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment': 'legacy/EGZKProofCommitment',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
        
class EGZKDisjunctiveProof(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.ZKDisjunctiveProof
    FIELDS = ['proofs']
    STRUCTURED_FIELDS = {
        'proofs': arrayOf('legacy/EGZKProof')}

    def loadDataFromDict(self, d):
        "hijack and make sure we add the proofs name back on"
        return super(EGZKDisjunctiveProof, self).loadDataFromDict({'proofs': d})

    def toDict(self, complete = False):
        "hijack toDict and make it return the proofs array only, since that's the spec for legacy"
        return super(EGZKDisjunctiveProof, self).toDict(complete=complete)['proofs']

class DLogProof(LegacyObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.DLogProof
    FIELDS = ['commitment', 'challenge', 'response']
    STRUCTURED_FIELDS = {
        'commitment' : 'core/BigInteger',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}

    def __init__(self, wrapped_obj):
        if isinstance(wrapped_obj, dict):
            import pdb; pdb.set_trace()

        super(DLogProof,self).__init__(wrapped_obj)

class Result(LegacyObject):
    WRAPPED_OBJ = list

    def loadDataFromDict(self, d):
        self.wrapped_obj = d

    def toDict(self, complete=False):
        return self.wrapped_obj

class Questions(ListObject, LegacyObject):
    WRAPPED_OBJ = list

class Tally(LegacyObject):
    WRAPPED_OBJ_CLASS = homomorphic.Tally
    FIELDS = ['tally', 'num_tallied']
    STRUCTURED_FIELDS = {
        'tally': arrayOf(arrayOf('legacy/EGCiphertext'))}

class Eligibility(ListObject, LegacyObject):
    WRAPPED_OBJ = list

########NEW FILE########
__FILENAME__ = elgamal
"""
data types for 2011/01 Helios
"""

from helios.datatypes import LDObject
from helios.crypto import elgamal as crypto_elgamal

class DiscreteLogProof(LDObject):
    FIELDS = ['challenge', 'commitment', 'response']
    STRUCTURED_FIELDS = {
        'challenge' : 'core/BigInteger',
        'commitment' : 'core/BigInteger',
        'response' : 'core/BigInteger'}
    
class PublicKey(LDObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.PublicKey

    FIELDS = ['y', 'p', 'g', 'q']
    STRUCTURED_FIELDS = {
        'y' : 'core/BigInteger',
        'p' : 'core/BigInteger',
        'g' : 'core/BigInteger',
        'q' : 'core/BigInteger'}


class SecretKey(LDObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.SecretKey

    FIELDS = ['public_key', 'x']
    STRUCTURED_FIELDS = {
        'public_key' : 'pkc/elgamal/PublicKey',
        'x' : 'core/BigInteger'
        }

class DLogProof(LDObject):
    WRAPPED_OBJ_CLASS = crypto_elgamal.DLogProof
    FIELDS = ['commitment', 'challenge', 'response']

    STRUCTURED_FIELDS = {
        'commitment' : 'core/BigInteger',
        'challenge' : 'core/BigInteger',
        'response' : 'core/BigInteger'}

########NEW FILE########
__FILENAME__ = datetimewidget
# -*- coding: utf-8 -*-
# utils/widgets.py

'''
DateTimeWidget using JSCal2 from http://www.dynarch.com/projects/calendar/

django snippets 1629
'''

from django.utils.encoding import force_unicode
from django.conf import settings
from django import forms
import datetime, time
from django.utils.safestring import mark_safe

# DATETIMEWIDGET
calbtn = u'''<img src="%smedia/admin/img/admin/icon_calendar.gif" alt="calendar" id="%s_btn" style="cursor: pointer;" title="Select date" />
<script type="text/javascript">
    Calendar.setup({
        inputField     :    "%s",
        dateFormat     :    "%s",
        trigger        :    "%s_btn",
        showTime: true
    });
</script>'''

class DateTimeWidget(forms.widgets.TextInput):
    class Media:
        css = {
            'all': (
                    '/static/helios/jscal/css/jscal2.css',
                    '/static/helios/jscal/css/border-radius.css',
                    '/static/helios/jscal/css/win2k/win2k.css',
                    )
        }
        js = (
              '/static/helios/jscal/js/jscal2.js',
              '/static/helios/jscal/js/lang/en.js',
        )

    dformat = '%Y-%m-%d %H:%M'
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            try:
                final_attrs['value'] = \
                                   force_unicode(value.strftime(self.dformat))
            except:
                final_attrs['value'] = \
                                   force_unicode(value)
        if not final_attrs.has_key('id'):
            final_attrs['id'] = u'%s_id' % (name)
        id = final_attrs['id']

        jsdformat = self.dformat #.replace('%', '%%')
        cal = calbtn % (settings.MEDIA_URL, id, id, jsdformat, id)
        a = u'<input%s />%s%s' % (forms.util.flatatt(final_attrs), self.media, cal)
        return mark_safe(a)

    def value_from_datadict(self, data, files, name):
        dtf = forms.fields.DEFAULT_DATETIME_INPUT_FORMATS
        empty_values = forms.fields.EMPTY_VALUES

        value = data.get(name, None)
        if value in empty_values:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in dtf:
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
        return None

    def _has_changed(self, initial, data):
        """
        Return True if data differs from initial.
        Copy of parent's method, but modify value with strftime function before final comparsion
        """
        if data is None:
            data_value = u''
        else:
            data_value = data

        if initial is None:
            initial_value = u''
        else:
            initial_value = initial

        try:
            if force_unicode(initial_value.strftime(self.dformat)) != force_unicode(data_value.strftime(self.dformat)):
                return True
        except:
            if force_unicode(initial_value) != force_unicode(data_value):
                return True

        return False

########NEW FILE########
__FILENAME__ = election_urls
"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls.defaults import *

from helios.views import *

urlpatterns = patterns('',
    # election data that is cryptographically verified
    (r'^$', one_election),

    # metadata that need not be verified
    (r'^/meta$', one_election_meta),
    
    # edit election params
    (r'^/edit$', one_election_edit),
    (r'^/schedule$', one_election_schedule),
    (r'^/archive$', one_election_archive),

    # badge
    (r'^/badge$', election_badge),

    # adding trustees
    (r'^/trustees/$', list_trustees),
    (r'^/trustees/view$', list_trustees_view),
    (r'^/trustees/new$', new_trustee),
    (r'^/trustees/add-helios$', new_trustee_helios),
    (r'^/trustees/delete$', delete_trustee),
    
    # trustee pages
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/home$', trustee_home),
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/sendurl$', trustee_send_url),
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/keygenerator$', trustee_keygenerator),
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/check-sk$', trustee_check_sk),
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/upoad-pk$', trustee_upload_pk),
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/decrypt-and-prove$', trustee_decrypt_and_prove),
    (r'^/trustees/(?P<trustee_uuid>[^/]+)/upload-decryption$', trustee_upload_decryption),
    
    # election voting-process actions
    (r'^/view$', one_election_view),
    (r'^/result$', one_election_result),
    (r'^/result_proof$', one_election_result_proof),
    # (r'^/bboard$', one_election_bboard),
    (r'^/audited-ballots/$', one_election_audited_ballots),

    # get randomness
    (r'^/get-randomness$', get_randomness),

    # server-side encryption
    (r'^/encrypt-ballot$', encrypt_ballot),

    # construct election
    (r'^/questions$', one_election_questions),
    (r'^/set_reg$', one_election_set_reg),
    (r'^/set_featured$', one_election_set_featured),
    (r'^/save_questions$', one_election_save_questions),
    (r'^/register$', one_election_register),
    (r'^/freeze$', one_election_freeze), # includes freeze_2 as POST target
    
    # computing tally
    (r'^/compute_tally$', one_election_compute_tally),
    (r'^/combine_decryptions$', combine_decryptions),
    (r'^/release_result$', release_result),
    
    # casting a ballot before we know who the voter is
    (r'^/cast$', one_election_cast),
    (r'^/cast_confirm$', one_election_cast_confirm),
    (r'^/password_voter_login$', password_voter_login),
    (r'^/cast_done$', one_election_cast_done),
    
    # post audited ballot
    (r'^/post-audited-ballot', post_audited_ballot),
    
    # managing voters
    (r'^/voters/$', voter_list),
    (r'^/voters/upload$', voters_upload),
    (r'^/voters/upload-cancel$', voters_upload_cancel),
    (r'^/voters/list$', voters_list_pretty),
    (r'^/voters/eligibility$', voters_eligibility),
    (r'^/voters/email$', voters_email),
    (r'^/voters/(?P<voter_uuid>[^/]+)$', one_voter),
    (r'^/voters/(?P<voter_uuid>[^/]+)/delete$', voter_delete),
    
    # ballots
    (r'^/ballots/$', ballot_list),
    (r'^/ballots/(?P<voter_uuid>[^/]+)/all$', voter_votes),
    (r'^/ballots/(?P<voter_uuid>[^/]+)/last$', voter_last_vote),

)

########NEW FILE########
__FILENAME__ = fields
from time import strptime, strftime
import datetime
from django import forms
from django.db import models
from django.forms import fields
from widgets import SplitSelectDateTimeWidget

class SplitDateTimeField(fields.MultiValueField):
    widget = SplitSelectDateTimeWidget

    def __init__(self, *args, **kwargs):
        """
        Have to pass a list of field types to the constructor, else we
        won't get any data to our compress method.
        """
        all_fields = (fields.DateField(), fields.TimeField())
        super(SplitDateTimeField, self).__init__(all_fields, *args, **kwargs)

    def compress(self, data_list):
        """
        Takes the values from the MultiWidget and passes them as a
        list to this function. This function needs to compress the
        list into a single object to save.
        """
        if data_list:
            if not (data_list[0] and data_list[1]):
                raise forms.ValidationError("Field is missing data.")
            return datetime.datetime.combine(*data_list)
        return None


########NEW FILE########
__FILENAME__ = forms
"""
Forms for Helios
"""

from django import forms
from models import Election
from widgets import *
from fields import *
from django.conf import settings


class ElectionForm(forms.Form):
  short_name = forms.SlugField(max_length=25, help_text='no spaces, will be part of the URL for your election, e.g. my-club-2010')
  name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size':60}), help_text='the pretty name for your election, e.g. My Club 2010 Election')
  description = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={'cols': 70, 'wrap': 'soft'}), required=False)
  election_type = forms.ChoiceField(label="type", choices = Election.ELECTION_TYPES)
  use_voter_aliases = forms.BooleanField(required=False, initial=False, help_text='If selected, voter identities will be replaced with aliases, e.g. "V12", in the ballot tracking center')
  #use_advanced_audit_features = forms.BooleanField(required=False, initial=True, help_text='disable this only if you want a simple election with reduced security but a simpler user interface')
  randomize_answer_order = forms.BooleanField(required=False, initial=False, help_text='enable this if you want the answers to questions to appear in random order for each voter')
  private_p = forms.BooleanField(required=False, initial=False, label="Private?", help_text='A private election is only visible to registered voters.')
  help_email = forms.CharField(required=False, initial="", label="Help Email Address", help_text='An email address voters should contact if they need help.')
  
  if settings.ALLOW_ELECTION_INFO_URL:
    election_info_url = forms.CharField(required=False, initial="", label="Election Info Download URL", help_text="the URL of a PDF document that contains extra election information, e.g. candidate bios and statements")
  

class ElectionTimesForm(forms.Form):
  # times
  voting_starts_at = SplitDateTimeField(help_text = 'UTC date and time when voting begins',
                                   widget=SplitSelectDateTimeWidget)
  voting_ends_at = SplitDateTimeField(help_text = 'UTC date and time when voting ends',
                                   widget=SplitSelectDateTimeWidget)

  
class EmailVotersForm(forms.Form):
  subject = forms.CharField(max_length=80)
  body = forms.CharField(max_length=4000, widget=forms.Textarea)
  send_to = forms.ChoiceField(label="Send To", initial="all", choices= [('all', 'all voters'), ('voted', 'voters who have cast a ballot'), ('not-voted', 'voters who have not yet cast a ballot')])

class TallyNotificationEmailForm(forms.Form):
  subject = forms.CharField(max_length=80)
  body = forms.CharField(max_length=2000, widget=forms.Textarea, required=False)
  send_to = forms.ChoiceField(label="Send To", choices= [('all', 'all voters'), ('voted', 'only voters who cast a ballot'), ('none', 'no one -- are you sure about this?')])

class VoterPasswordForm(forms.Form):
  voter_id = forms.CharField(max_length=50, label="Voter ID")
  password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


########NEW FILE########
__FILENAME__ = helios_trustee_decrypt
"""
decrypt elections where Helios is trustee

DEPRECATED

Ben Adida
ben@adida.net
2010-05-22
"""

from django.core.management.base import BaseCommand, CommandError
import csv, datetime

from helios import utils as helios_utils

from helios.models import *

class Command(BaseCommand):
    args = ''
    help = 'decrypt elections where helios is the trustee'
    
    def handle(self, *args, **options):
        # query for elections where decryption is ready to go and Helios is the trustee
        active_helios_trustees = Trustee.objects.exclude(secret_key = None).exclude(election__encrypted_tally = None).filter(decryption_factors = None)

        # for each one, do the decryption
        for t in active_helios_trustees:
            tally = t.election.encrypted_tally

            # FIXME: this should probably be in the encrypted_tally getter
            tally.init_election(t.election)

            factors, proof = tally.decryption_factors_and_proofs(t.secret_key)
            t.decryption_factors = factors
            t.decryption_proofs = proof
            t.save()
            

########NEW FILE########
__FILENAME__ = load_voter_files
"""
parse and set up voters from uploaded voter files

DEPRECATED

Ben Adida
ben@adida.net
2010-05-22
"""

from django.core.management.base import BaseCommand, CommandError
import csv, datetime

from helios import utils as helios_utils

from helios.models import *

##
## UTF8 craziness for CSV
##

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')
  
def process_csv_file(election, f):
    reader = unicode_csv_reader(f)
    
    num_voters = 0
    for voter in reader:
      # bad line
      if len(voter) < 1:
        continue
    
      num_voters += 1
      voter_id = voter[0]
      name = voter_id
      email = voter_id
    
      if len(voter) > 1:
        email = voter[1]
    
      if len(voter) > 2:
        name = voter[2]
    
      # create the user
      user = User.update_or_create(user_type='password', user_id=voter_id, info = {'password': helios_utils.random_string(10), 'email': email, 'name': name})
      user.save()
    
      # does voter for this user already exist
      voter = Voter.get_by_election_and_user(election, user)
    
      # create the voter
      if not voter:
        voter_uuid = str(uuid.uuid1())
        voter = Voter(uuid= voter_uuid, voter_type = 'password', voter_id = voter_id, name = name, election = election)
        voter.save()

    return num_voters


class Command(BaseCommand):
    args = ''
    help = 'load up voters from unprocessed voter files'
    
    def handle(self, *args, **options):
        # load up the voter files in order of last uploaded
        files_to_process = VoterFile.objects.filter(processing_started_at=None).order_by('uploaded_at')

        for file_to_process in files_to_process:
            # mark processing begins
            file_to_process.processing_started_at = datetime.datetime.utcnow()
            file_to_process.save()

            num_voters = process_csv_file(file_to_process.election, file_to_process.voter_file)

            # mark processing done
            file_to_process.processing_finished_at = datetime.datetime.utcnow()
            file_to_process.num_voters = num_voters
            file_to_process.save()
            
            

########NEW FILE########
__FILENAME__ = verify_cast_votes
"""
verify cast votes that have not yet been verified

Ben Adida
ben@adida.net
2010-05-22
"""

from django.core.management.base import BaseCommand, CommandError
import csv, datetime

from helios import utils as helios_utils

from helios.models import *

def get_cast_vote_to_verify():
    # fixme: add "select for update" functionality here
    votes = CastVote.objects.filter(verified_at=None, invalidated_at=None).order_by('-cast_at')
    if len(votes) > 0:
        return votes[0]
    else:
        return None

class Command(BaseCommand):
    args = ''
    help = 'verify votes that were cast'
    
    def handle(self, *args, **options):
        while True:
            cast_vote = get_cast_vote_to_verify()
            if not cast_vote:
                break

            cast_vote.verify_and_store()

        # once broken out of the while loop, quit and wait for next invocation
        # this happens when there are no votes left to verify
            

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Election'
        db.create_table('helios_election', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('admin', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios_auth.User'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('public_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('private_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('questions', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('eligibility', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('openreg', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('featured_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('use_voter_aliases', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cast_url', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('frozen_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('archived_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('registration_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_ends_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallying_starts_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_extended_until', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voting_ended_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallying_started_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallying_finished_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('tallies_combined_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('voters_hash', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('encrypted_tally', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('result', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('result_proof', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
        ))
        db.send_create_signal('helios', ['Election'])

        # Adding model 'ElectionLog'
        db.create_table('helios_electionlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('log', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('helios', ['ElectionLog'])

        # Adding model 'VoterFile'
        db.create_table('helios_voterfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('voter_file', self.gf('django.db.models.fields.files.FileField')(max_length=250)),
            ('uploaded_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('processing_started_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('processing_finished_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('num_voters', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('helios', ['VoterFile'])

        # Adding model 'Voter'
        db.create_table('helios_voter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('voter_type', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('voter_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('vote', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
            ('cast_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('helios', ['Voter'])

        # Adding model 'CastVote'
        db.create_table('helios_castvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('voter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Voter'])),
            ('vote', self.gf('helios_auth.jsonfield.JSONField')()),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('cast_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('verified_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('invalidated_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('helios', ['CastVote'])

        # Adding model 'AuditedBallot'
        db.create_table('helios_auditedballot', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('raw_vote', self.gf('django.db.models.fields.TextField')()),
            ('vote_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('added_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('helios', ['AuditedBallot'])

        # Adding model 'Trustee'
        db.create_table('helios_trustee', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios.Election'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('public_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('public_key_hash', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('secret_key', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('pok', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('decryption_factors', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('decryption_proofs', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
        ))
        db.send_create_signal('helios', ['Trustee'])


    def backwards(self, orm):
        
        # Deleting model 'Election'
        db.delete_table('helios_election')

        # Deleting model 'ElectionLog'
        db.delete_table('helios_electionlog')

        # Deleting model 'VoterFile'
        db.delete_table('helios_voterfile')

        # Deleting model 'Voter'
        db.delete_table('helios_voter')

        # Deleting model 'CastVote'
        db.delete_table('helios_castvote')

        # Deleting model 'AuditedBallot'
        db.delete_table('helios_auditedballot')

        # Deleting model 'Trustee'
        db.delete_table('helios_trustee')


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'eligibility': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'encrypted_tally': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'questions': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'decryption_proofs': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter_type': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0002_v3_1_new_election_and_voter_fields
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Voter.user'
        db.add_column('helios_voter', 'user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['helios_auth.User'], null=True), keep_default=False)

        # Adding field 'Voter.voter_login_id'
        db.add_column('helios_voter', 'voter_login_id', self.gf('django.db.models.fields.CharField')(max_length=100, null=True), keep_default=False)

        # Adding field 'Voter.voter_password'
        db.add_column('helios_voter', 'voter_password', self.gf('django.db.models.fields.CharField')(max_length=100, null=True), keep_default=False)

        # Adding field 'Voter.voter_name'
        db.add_column('helios_voter', 'voter_name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True), keep_default=False)

        # Adding field 'Voter.voter_email'
        db.add_column('helios_voter', 'voter_email', self.gf('django.db.models.fields.CharField')(max_length=250, null=True), keep_default=False)

        # Adding field 'Election.datatype'
        db.add_column('helios_election', 'datatype', self.gf('django.db.models.fields.CharField')(default='legacy/Election', max_length=250), keep_default=False)

        # Adding field 'Election.election_type'
        db.add_column('helios_election', 'election_type', self.gf('django.db.models.fields.CharField')(default='election', max_length=250), keep_default=False)

        # Adding field 'Election.private_p'
        db.add_column('helios_election', 'private_p', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Adding field 'Election.use_advanced_audit_features'
        db.add_column('helios_election', 'use_advanced_audit_features', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Adding field 'CastVote.vote_tinyhash'
        db.add_column('helios_castvote', 'vote_tinyhash', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Voter.user'
        db.delete_column('helios_voter', 'user_id')

        # Deleting field 'Voter.voter_login_id'
        db.delete_column('helios_voter', 'voter_login_id')

        # Deleting field 'Voter.voter_password'
        db.delete_column('helios_voter', 'voter_password')

        # Deleting field 'Voter.voter_name'
        db.delete_column('helios_voter', 'voter_name')

        # Deleting field 'Voter.voter_email'
        db.delete_column('helios_voter', 'voter_email')

        # Deleting field 'Election.datatype'
        db.delete_column('helios_election', 'datatype')

        # Deleting field 'Election.election_type'
        db.delete_column('helios_election', 'election_type')

        # Deleting field 'Election.private_p'
        db.delete_column('helios_election', 'private_p')

        # Deleting field 'Election.use_advanced_audit_features'
        db.delete_column('helios_election', 'use_advanced_audit_features')

        # Deleting field 'CastVote.vote_tinyhash'
        db.delete_column('helios_castvote', 'vote_tinyhash')


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'encrypted_tally': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'questions': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'decryption_proofs': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_type': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0003_v3_1_election_specific_voters_with_passwords
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        """
        update the voters data objects to point to users when it makes sense,
        and otherwise to copy the data needed from the users table.
        make all elections legacy, because before now they are.
        """
        for e in orm.Election.objects.all():
            e.datatype = 'legacy/Election'
            e.save()

        # use the .iterator() call to reduce caching and make this more efficient
        # so as not to trigger a memory error
        for v in orm.Voter.objects.all().iterator():
            user = orm['helios_auth.User'].objects.get(user_type = v.voter_type, user_id = v.voter_id)

            if v.voter_type == 'password':
                v.voter_login_id = v.voter_id
                v.voter_name = v.name

                v.voter_email = user.info['email']
                v.voter_password = user.info['password']
            else:
                v.user = user

            v.save()

        # also, update tinyhash for all votes
        for cv in orm.CastVote.objects.all().iterator():
            safe_hash = cv.vote_hash
            for c in ['/', '+']:
                safe_hash = safe_hash.replace(c,'')
    
            length = 8
            while True:
                vote_tinyhash = safe_hash[:length]
                if orm.CastVote.objects.filter(vote_tinyhash = vote_tinyhash).count() == 0:
                    break
                length += 1
      
            cv.vote_tinyhash = vote_tinyhash
            cv.save()


    def backwards(self, orm):
        "Write your backwards methods here."
        raise Exception("can't revert to system-wide user passwords, rather than election specific")


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'encrypted_tally': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'questions': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'decryption_proofs': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_type': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0004_v3_1_remove_voter_fields
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Voter.name'
        db.delete_column('helios_voter', 'name')

        # Deleting field 'Voter.voter_id'
        db.delete_column('helios_voter', 'voter_id')

        # Deleting field 'Voter.voter_type'
        db.delete_column('helios_voter', 'voter_type')


    def backwards(self, orm):
        
        # Adding field 'Voter.name'
        db.add_column('helios_voter', 'name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True), keep_default=False)

        # We cannot add back in field 'Voter.voter_id'
        raise RuntimeError(
            "Cannot reverse this migration. 'Voter.voter_id' and its values cannot be restored.")

        # We cannot add back in field 'Voter.voter_type'
        raise RuntimeError(
            "Cannot reverse this migration. 'Voter.voter_type' and its values cannot be restored.")


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'encrypted_tally': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'questions': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'decryption_proofs': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0005_add_quarantine_fields
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Election.complaint_period_ends_at'
        db.add_column('helios_election', 'complaint_period_ends_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True), keep_default=False)

        # Adding field 'CastVote.quarantined_p'
        db.add_column('helios_castvote', 'quarantined_p', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Adding field 'CastVote.released_from_quarantine_at'
        db.add_column('helios_castvote', 'released_from_quarantine_at', self.gf('django.db.models.fields.DateTimeField')(null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Election.complaint_period_ends_at'
        db.delete_column('helios_election', 'complaint_period_ends_at')

        # Deleting field 'CastVote.quarantined_p'
        db.delete_column('helios_castvote', 'quarantined_p')

        # Deleting field 'CastVote.released_from_quarantine_at'
        db.delete_column('helios_castvote', 'released_from_quarantine_at')


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'encrypted_tally': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'questions': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'decryption_proofs': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0006_auto__chg_field_voter_vote__add_unique_voter_voter_login_id_election__
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Voter.vote'
        db.alter_column('helios_voter', 'vote', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Adding unique constraint on 'Voter', fields ['voter_login_id', 'election']
        db.create_unique('helios_voter', ['voter_login_id', 'election_id'])

        # Changing field 'Election.result'
        db.alter_column('helios_election', 'result', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Election.questions'
        db.alter_column('helios_election', 'questions', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Election.encrypted_tally'
        db.alter_column('helios_election', 'encrypted_tally', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Election.eligibility'
        db.alter_column('helios_election', 'eligibility', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Election.private_key'
        db.alter_column('helios_election', 'private_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Election.public_key'
        db.alter_column('helios_election', 'public_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Trustee.public_key'
        db.alter_column('helios_trustee', 'public_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Trustee.decryption_proofs'
        db.alter_column('helios_trustee', 'decryption_proofs', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Trustee.pok'
        db.alter_column('helios_trustee', 'pok', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Trustee.secret_key'
        db.alter_column('helios_trustee', 'secret_key', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'Trustee.decryption_factors'
        db.alter_column('helios_trustee', 'decryption_factors', self.gf('helios.datatypes.djangofield.LDObjectField')(null=True))

        # Changing field 'CastVote.vote'
        db.alter_column('helios_castvote', 'vote', self.gf('helios.datatypes.djangofield.LDObjectField')())


    def backwards(self, orm):
        
        # Removing unique constraint on 'Voter', fields ['voter_login_id', 'election']
        db.delete_unique('helios_voter', ['voter_login_id', 'election_id'])

        # Changing field 'Voter.vote'
        db.alter_column('helios_voter', 'vote', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Election.result'
        db.alter_column('helios_election', 'result', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Election.questions'
        db.alter_column('helios_election', 'questions', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Election.encrypted_tally'
        db.alter_column('helios_election', 'encrypted_tally', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Election.eligibility'
        db.alter_column('helios_election', 'eligibility', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Election.private_key'
        db.alter_column('helios_election', 'private_key', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Election.public_key'
        db.alter_column('helios_election', 'public_key', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Trustee.public_key'
        db.alter_column('helios_trustee', 'public_key', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Trustee.decryption_proofs'
        db.alter_column('helios_trustee', 'decryption_proofs', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Trustee.pok'
        db.alter_column('helios_trustee', 'pok', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Trustee.secret_key'
        db.alter_column('helios_trustee', 'secret_key', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'Trustee.decryption_factors'
        db.alter_column('helios_trustee', 'decryption_factors', self.gf('helios_auth.jsonfield.JSONField')(null=True))

        # Changing field 'CastVote.vote'
        db.alter_column('helios_castvote', 'vote', self.gf('helios_auth.jsonfield.JSONField')())


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_voterfile_voter_file_content__chg_field_voterfile_vote
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'VoterFile.voter_file_content'
        db.add_column('helios_voterfile', 'voter_file_content', self.gf('django.db.models.fields.TextField')(null=True), keep_default=False)

        # Changing field 'VoterFile.voter_file'
        db.alter_column('helios_voterfile', 'voter_file', self.gf('django.db.models.fields.files.FileField')(max_length=250, null=True))


    def backwards(self, orm):
        
        # Deleting field 'VoterFile.voter_file_content'
        db.delete_column('helios_voterfile', 'voter_file_content')

        # User chose to not deal with backwards NULL issues for 'VoterFile.voter_file'
        raise RuntimeError("Cannot reverse this migration. 'VoterFile.voter_file' and its values cannot be restored.")


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0008_auto__add_unique_trustee_election_email
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Trustee', fields ['election', 'email']
        db.create_unique('helios_trustee', ['election_id', 'email'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Trustee', fields ['election', 'email']
        db.delete_unique('helios_trustee', ['election_id', 'email'])


    models = {
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'unique_together': "(('election', 'email'),)", 'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_election_help_email
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Election.help_email'
        db.add_column('helios_election', 'help_email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Election.help_email'
        db.delete_column('helios_election', 'help_email')


    models = {
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'help_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'unique_together': "(('election', 'email'),)", 'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['helios']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_election_randomize_answer_order
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Election.randomize_answer_order'
        db.add_column('helios_election', 'randomize_answer_order',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Election.randomize_answer_order'
        db.delete_column('helios_election', 'randomize_answer_order')


    models = {
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'help_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'randomize_answer_order': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'unique_together': "(('election', 'email'),)", 'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['helios']
########NEW FILE########
__FILENAME__ = 0011_auto__add_field_election_election_info_url
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Election.election_info_url'
        db.add_column('helios_election', 'election_info_url',
                      self.gf('django.db.models.fields.CharField')(max_length=300, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Election.election_info_url'
        db.delete_column('helios_election', 'election_info_url')


    models = {
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_info_url': ('django.db.models.fields.CharField', [], {'max_length': '300', 'null': 'True'}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'help_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'randomize_answer_order': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'unique_together': "(('election', 'email'),)", 'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['helios']
########NEW FILE########
__FILENAME__ = 0012_auto__add_field_election_result_released_at
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Election.result_released_at'
        db.add_column('helios_election', 'result_released_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=None, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Election.result_released_at'
        db.delete_column('helios_election', 'result_released_at')


    models = {
        'helios.auditedballot': {
            'Meta': {'object_name': 'AuditedBallot'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_vote': ('django.db.models.fields.TextField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'helios.castvote': {
            'Meta': {'object_name': 'CastVote'},
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'quarantined_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'released_from_quarantine_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'vote_tinyhash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Voter']"})
        },
        'helios.election': {
            'Meta': {'object_name': 'Election'},
            'admin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']"}),
            'archived_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'cast_url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'complaint_period_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'legacy/Election'", 'max_length': '250'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_info_url': ('django.db.models.fields.CharField', [], {'max_length': '300', 'null': 'True'}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'election'", 'max_length': '250'}),
            'eligibility': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'encrypted_tally': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'featured_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frozen_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'help_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openreg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'private_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'private_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'questions': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'randomize_answer_order': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'registration_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'result': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'result_proof': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'result_released_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tallies_combined_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_finished_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'tallying_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'use_advanced_audit_features': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_voter_aliases': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'voters_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voting_ended_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_extended_until': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'})
        },
        'helios.electionlog': {
            'Meta': {'object_name': 'ElectionLog'},
            'at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'helios.trustee': {
            'Meta': {'unique_together': "(('election', 'email'),)", 'object_name': 'Trustee'},
            'decryption_factors': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'decryption_proofs': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'pok': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'public_key_hash': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'helios.voter': {
            'Meta': {'unique_together': "(('election', 'voter_login_id'),)", 'object_name': 'Voter'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'cast_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios_auth.User']", 'null': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('helios.datatypes.djangofield.LDObjectField', [], {'null': 'True'}),
            'vote_hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True'}),
            'voter_login_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'voter_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'voter_password': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'})
        },
        'helios.voterfile': {
            'Meta': {'object_name': 'VoterFile'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['helios.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_voters': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'processing_finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'processing_started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'voter_file': ('django.db.models.fields.files.FileField', [], {'max_length': '250', 'null': 'True'}),
            'voter_file_content': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['helios']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
Data Objects for Helios.

Ben Adida
(ben@adida.net)
"""

from django.db import models, transaction
from django.utils import simplejson
from django.conf import settings
from django.core.mail import send_mail

import datetime, logging, uuid, random, io
import bleach

from crypto import electionalgs, algs, utils
from helios import utils as heliosutils
import helios.views

from helios import datatypes


# useful stuff in helios_auth
from helios_auth.models import User, AUTH_SYSTEMS
from helios_auth.jsonfield import JSONField
from helios.datatypes.djangofield import LDObjectField

import csv, copy
import unicodecsv

class HeliosModel(models.Model, datatypes.LDObjectContainer):
  class Meta:
    abstract = True

class Election(HeliosModel):
  admin = models.ForeignKey(User)
  
  uuid = models.CharField(max_length=50, null=False)

  # keep track of the type and version of election, which will help dispatch to the right
  # code, both for crypto and serialization
  # v3 and prior have a datatype of "legacy/Election"
  # v3.1 will still use legacy/Election
  # later versions, at some point will upgrade to "2011/01/Election"
  datatype = models.CharField(max_length=250, null=False, default="legacy/Election")
  
  short_name = models.CharField(max_length=100)
  name = models.CharField(max_length=250)
  
  ELECTION_TYPES = (
    ('election', 'Election'),
    ('referendum', 'Referendum')
    )

  election_type = models.CharField(max_length=250, null=False, default='election', choices = ELECTION_TYPES)
  private_p = models.BooleanField(default=False, null=False)

  description = models.TextField()
  public_key = LDObjectField(type_hint = 'legacy/EGPublicKey',
                             null=True)
  private_key = LDObjectField(type_hint = 'legacy/EGSecretKey',
                              null=True)
  
  questions = LDObjectField(type_hint = 'legacy/Questions',
                            null=True)
  
  # eligibility is a JSON field, which lists auth_systems and eligibility details for that auth_system, e.g.
  # [{'auth_system': 'cas', 'constraint': [{'year': 'u12'}, {'year':'u13'}]}, {'auth_system' : 'password'}, {'auth_system' : 'openid', 'constraint': [{'host':'http://myopenid.com'}]}]
  eligibility = LDObjectField(type_hint = 'legacy/Eligibility',
                              null=True)

  # open registration?
  # this is now used to indicate the state of registration,
  # whether or not the election is frozen
  openreg = models.BooleanField(default=False)
  
  # featured election?
  featured_p = models.BooleanField(default=False)
    
  # voter aliases?
  use_voter_aliases = models.BooleanField(default=False)

  # auditing is not for everyone
  use_advanced_audit_features = models.BooleanField(default=True, null=False)

  # randomize candidate order?
  randomize_answer_order = models.BooleanField(default=False, null=False)
  
  # where votes should be cast
  cast_url = models.CharField(max_length = 500)

  # dates at which this was touched
  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now_add=True)
  
  # dates at which things happen for the election
  frozen_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  archived_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  
  # dates for the election steps, as scheduled
  # these are always UTC
  registration_starts_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_starts_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_ends_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # if this is non-null, then a complaint period, where people can cast a quarantined ballot.
  # we do NOT call this a "provisional" ballot, since provisional implies that the voter has not
  # been qualified. We may eventually add this, but it can't be in the same CastVote table, which
  # is tied to a voter.
  complaint_period_ends_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  tallying_starts_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  
  # dates when things were forced to be performed
  voting_started_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_extended_until = models.DateTimeField(auto_now_add=False, default=None, null=True)
  voting_ended_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  tallying_started_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  tallying_finished_at = models.DateTimeField(auto_now_add=False, default=None, null=True)
  tallies_combined_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # we want to explicitly release results
  result_released_at = models.DateTimeField(auto_now_add=False, default=None, null=True)

  # the hash of all voters (stored for large numbers)
  voters_hash = models.CharField(max_length=100, null=True)
  
  # encrypted tally, each a JSON string
  # used only for homomorphic tallies
  encrypted_tally = LDObjectField(type_hint = 'legacy/Tally',
                                  null=True)

  # results of the election
  result = LDObjectField(type_hint = 'legacy/Result',
                         null=True)

  # decryption proof, a JSON object
  # no longer needed since it's all trustees
  result_proof = JSONField(null=True)

  # help email
  help_email = models.EmailField(null=True)

  # downloadable election info
  election_info_url = models.CharField(max_length=300, null=True)

  # metadata for the election
  @property
  def metadata(self):
    return {
      'help_email': self.help_email or 'help@heliosvoting.org',
      'private_p': self.private_p,
      'use_advanced_audit_features': self.use_advanced_audit_features,
      'randomize_answer_order': self.randomize_answer_order
      }

  @property
  def pretty_type(self):
    return dict(self.ELECTION_TYPES)[self.election_type]

  @property
  def num_cast_votes(self):
    return self.voter_set.exclude(vote=None).count()

  @property
  def num_voters(self):
    return self.voter_set.count()

  @property
  def num_trustees(self):
    return self.trustee_set.count()

  @property
  def last_alias_num(self):
    """
    FIXME: we should be tracking alias number, not the V* alias which then
    makes things a lot harder
    """
    if not self.use_voter_aliases:
      return None
    
    return heliosutils.one_val_raw_sql("select max(cast(substring(alias, 2) as integer)) from " + Voter._meta.db_table + " where election_id = %s", [self.id]) or 0

  @property
  def encrypted_tally_hash(self):
    if not self.encrypted_tally:
      return None

    return utils.hash_b64(self.encrypted_tally.toJSON())

  @property
  def is_archived(self):
    return self.archived_at != None

  @property
  def description_bleached(self):
    return bleach.clean(self.description, tags = bleach.ALLOWED_TAGS + ['p', 'h4', 'h5', 'h3', 'h2', 'br', 'u'])

  @classmethod
  def get_featured(cls):
    return cls.objects.filter(featured_p = True).order_by('short_name')
    
  @classmethod
  def get_or_create(cls, **kwargs):
    return cls.objects.get_or_create(short_name = kwargs['short_name'], defaults=kwargs)

  @classmethod
  def get_by_user_as_admin(cls, user, archived_p=None, limit=None):
    query = cls.objects.filter(admin = user)
    if archived_p == True:
      query = query.exclude(archived_at= None)
    if archived_p == False:
      query = query.filter(archived_at= None)
    query = query.order_by('-created_at')
    if limit:
      return query[:limit]
    else:
      return query
    
  @classmethod
  def get_by_user_as_voter(cls, user, archived_p=None, limit=None):
    query = cls.objects.filter(voter__user = user)
    if archived_p == True:
      query = query.exclude(archived_at= None)
    if archived_p == False:
      query = query.filter(archived_at= None)
    query = query.order_by('-created_at')
    if limit:
      return query[:limit]
    else:
      return query
    
  @classmethod
  def get_by_uuid(cls, uuid):
    try:
      return cls.objects.select_related().get(uuid=uuid)
    except cls.DoesNotExist:
      return None
  
  @classmethod
  def get_by_short_name(cls, short_name):
    try:
      return cls.objects.get(short_name=short_name)
    except cls.DoesNotExist:
      return None

  def add_voters_file(self, uploaded_file):
    """
    expects a django uploaded_file data structure, which has filename, content, size...
    """
    # now we're just storing the content
    # random_filename = str(uuid.uuid4())
    # new_voter_file.voter_file.save(random_filename, uploaded_file)

    new_voter_file = VoterFile(election = self, voter_file_content = uploaded_file.read())
    new_voter_file.save()
    
    self.append_log(ElectionLog.VOTER_FILE_ADDED)
    return new_voter_file
  
  def user_eligible_p(self, user):
    """
    Checks if a user is eligible for this election.
    """
    # registration closed, then eligibility doesn't come into play
    if not self.openreg:
      return False
    
    if self.eligibility == None:
      return True
      
    # is the user eligible for one of these cases?
    for eligibility_case in self.eligibility:
      if user.is_eligible_for(eligibility_case):
        return True
        
    return False

  def eligibility_constraint_for(self, user_type):
    if not self.eligibility:
      return []

    # constraints that are relevant
    relevant_constraints = [constraint['constraint'] for constraint in self.eligibility if constraint['auth_system'] == user_type and constraint.has_key('constraint')]
    if len(relevant_constraints) > 0:
      return relevant_constraints[0]
    else:
      return []

  def eligibility_category_id(self, user_type):
    "when eligibility is by category, this returns the category_id"
    if not self.eligibility:
      return None
    
    constraint_for = self.eligibility_constraint_for(user_type)
    if len(constraint_for) > 0:
      constraint = constraint_for[0]
      return AUTH_SYSTEMS[user_type].eligibility_category_id(constraint)
    else:
      return None
    
  @property
  def pretty_eligibility(self):
    if not self.eligibility:
      return "Anyone can vote."
    else:
      return_val = "<ul>"
      
      for constraint in self.eligibility:
        if constraint.has_key('constraint'):
          for one_constraint in constraint['constraint']:
            return_val += "<li>%s</li>" % AUTH_SYSTEMS[constraint['auth_system']].pretty_eligibility(one_constraint)
        else:
          return_val += "<li> any %s user</li>" % constraint['auth_system']

      return_val += "</ul>"

      return return_val
  
  def voting_has_started(self):
    """
    has voting begun? voting begins if the election is frozen, at the prescribed date or at the date that voting was forced to start
    """
    return self.frozen_at != None and (self.voting_starts_at == None or (datetime.datetime.utcnow() >= (self.voting_started_at or self.voting_starts_at)))
    
  def voting_has_stopped(self):
    """
    has voting stopped? if tally computed, yes, otherwise if we have passed the date voting was manually stopped at,
    or failing that the date voting was extended until, or failing that the date voting is scheduled to end at.
    """
    voting_end = self.voting_ended_at or self.voting_extended_until or self.voting_ends_at
    return (voting_end != None and datetime.datetime.utcnow() >= voting_end) or self.encrypted_tally

  @property
  def issues_before_freeze(self):
    issues = []
    if self.questions == None or len(self.questions) == 0:
      issues.append(
        {'type': 'questions',
         'action': "add questions to the ballot"}
        )
  
    trustees = Trustee.get_by_election(self)
    if len(trustees) == 0:
      issues.append({
          'type': 'trustees',
          'action': "add at least one trustee"
          })

    for t in trustees:
      if t.public_key == None:
        issues.append({
            'type': 'trustee keypairs',
            'action': 'have trustee %s generate a keypair' % t.name
            })

    if self.voter_set.count() == 0 and not self.openreg:
      issues.append({
          "type" : "voters",
          "action" : 'enter your voter list (or open registration to the public)'
          })

    return issues    

  def ready_for_tallying(self):
    return datetime.datetime.utcnow() >= self.tallying_starts_at

  def compute_tally(self):
    """
    tally the election, assuming votes already verified
    """
    tally = self.init_tally()
    for voter in self.voter_set.exclude(vote=None):
      tally.add_vote(voter.vote, verify_p=False)

    self.encrypted_tally = tally
    self.save()    
  
  def ready_for_decryption(self):
    return self.encrypted_tally != None
    
  def ready_for_decryption_combination(self):
    """
    do we have a tally from all trustees?
    """
    for t in Trustee.get_by_election(self):
      if not t.decryption_factors:
        return False
    
    return True
    
  def release_result(self):
    """
    release the result that should already be computed
    """
    if not self.result:
      return

    self.result_released_at = datetime.datetime.utcnow()
  
  def combine_decryptions(self):
    """
    combine all of the decryption results
    """
    
    # gather the decryption factors
    trustees = Trustee.get_by_election(self)
    decryption_factors = [t.decryption_factors for t in trustees]
    
    self.result = self.encrypted_tally.decrypt_from_factors(decryption_factors, self.public_key)

    self.append_log(ElectionLog.DECRYPTIONS_COMBINED)

    self.save()
  
  def generate_voters_hash(self):
    """
    look up the list of voters, make a big file, and hash it
    """

    # FIXME: for now we don't generate this voters hash:
    return

    if self.openreg:
      self.voters_hash = None
    else:
      voters = Voter.get_by_election(self)
      voters_json = utils.to_json([v.toJSONDict() for v in voters])
      self.voters_hash = utils.hash_b64(voters_json)
    
  def increment_voters(self):
    ## FIXME
    return 0
    
  def increment_cast_votes(self):
    ## FIXME
    return 0
        
  def set_eligibility(self):
    """
    if registration is closed and eligibility has not been
    already set, then this call sets the eligibility criteria
    based on the actual list of voters who are already there.

    This helps ensure that the login box shows the proper options.

    If registration is open but no voters have been added with password,
    then that option is also canceled out to prevent confusion, since
    those elections usually just use the existing login systems.
    """

    # don't override existing eligibility
    if self.eligibility != None:
      return

    # enable this ONLY once the cast_confirm screen makes sense
    #if self.voter_set.count() == 0:
    #  return

    auth_systems = copy.copy(settings.AUTH_ENABLED_AUTH_SYSTEMS)
    voter_types = [r['user__user_type'] for r in self.voter_set.values('user__user_type').distinct() if r['user__user_type'] != None]

    # password is now separate, not an explicit voter type
    if self.voter_set.filter(user=None).count() > 0:
      voter_types.append('password')
    else:
      # no password users, remove password from the possible auth systems
      if 'password' in auth_systems:
        auth_systems.remove('password')        

    # closed registration: limit the auth_systems to just the ones
    # that have registered voters
    if not self.openreg:
      auth_systems = [vt for vt in voter_types if vt in auth_systems]

    self.eligibility = [{'auth_system': auth_system} for auth_system in auth_systems]
    self.save()    
    
  def freeze(self):
    """
    election is frozen when the voter registration, questions, and trustees are finalized
    """
    if len(self.issues_before_freeze) > 0:
      raise Exception("cannot freeze an election that has issues")

    self.frozen_at = datetime.datetime.utcnow()
    
    # voters hash
    self.generate_voters_hash()

    self.set_eligibility()
    
    # public key for trustees
    trustees = Trustee.get_by_election(self)
    combined_pk = trustees[0].public_key
    for t in trustees[1:]:
      combined_pk = combined_pk * t.public_key
      
    self.public_key = combined_pk
    
    # log it
    self.append_log(ElectionLog.FROZEN)

    self.save()

  def generate_trustee(self, params):
    """
    generate a trustee including the secret key,
    thus a helios-based trustee
    """
    # FIXME: generate the keypair
    keypair = params.generate_keypair()

    # create the trustee
    trustee = Trustee(election = self)
    trustee.uuid = str(uuid.uuid4())
    trustee.name = settings.DEFAULT_FROM_NAME
    trustee.email = settings.DEFAULT_FROM_EMAIL
    trustee.public_key = keypair.pk
    trustee.secret_key = keypair.sk
    
    # FIXME: is this at the right level of abstraction?
    trustee.public_key_hash = datatypes.LDObject.instantiate(trustee.public_key, datatype='legacy/EGPublicKey').hash

    trustee.pok = trustee.secret_key.prove_sk(algs.DLog_challenge_generator)

    trustee.save()

  def get_helios_trustee(self):
    trustees_with_sk = self.trustee_set.exclude(secret_key = None)
    if len(trustees_with_sk) > 0:
      return trustees_with_sk[0]
    else:
      return None
    
  def has_helios_trustee(self):
    return self.get_helios_trustee() != None

  def helios_trustee_decrypt(self):
    tally = self.encrypted_tally
    tally.init_election(self)

    trustee = self.get_helios_trustee()
    factors, proof = tally.decryption_factors_and_proofs(trustee.secret_key)

    trustee.decryption_factors = factors
    trustee.decryption_proofs = proof
    trustee.save()

  def append_log(self, text):
    item = ElectionLog(election = self, log=text, at=datetime.datetime.utcnow())
    item.save()
    return item

  def get_log(self):
    return self.electionlog_set.order_by('-at')

  @property
  def url(self):
    return helios.views.get_election_url(self)

  def init_tally(self):
    # FIXME: create the right kind of tally
    from helios.workflows import homomorphic
    return homomorphic.Tally(election=self)
        
  @property
  def registration_status_pretty(self):
    if self.openreg:
      return "Open"
    else:
      return "Closed"

  @classmethod
  def one_question_winner(cls, question, result, num_cast_votes):
    """
    determining the winner for one question
    """
    # sort the answers , keep track of the index
    counts = sorted(enumerate(result), key=lambda(x): x[1])
    counts.reverse()
    
    the_max = question['max'] or 1
    the_min = question['min'] or 0

    # if there's a max > 1, we assume that the top MAX win
    if the_max > 1:
      return [c[0] for c in counts[:the_max]]

    # if max = 1, then depends on absolute or relative
    if question['result_type'] == 'absolute':
      if counts[0][1] >=  (num_cast_votes/2 + 1):
        return [counts[0][0]]
      else:
        return []
    else:
      # assumes that anything non-absolute is relative
      return [counts[0][0]]    

  @property
  def winners(self):
    """
    Depending on the type of each question, determine the winners
    returns an array of winners for each question, aka an array of arrays.
    assumes that if there is a max to the question, that's how many winners there are.
    """
    return [self.one_question_winner(self.questions[i], self.result[i], self.num_cast_votes) for i in range(len(self.questions))]
    
  @property
  def pretty_result(self):
    if not self.result:
      return None
    
    # get the winners
    winners = self.winners

    raw_result = self.result
    prettified_result = []

    # loop through questions
    for i in range(len(self.questions)):
      q = self.questions[i]
      pretty_question = []
      
      # go through answers
      for j in range(len(q['answers'])):
        a = q['answers'][j]
        count = raw_result[i][j]
        pretty_question.append({'answer': a, 'count': count, 'winner': (j in winners[i])})
        
      prettified_result.append({'question': q['short_name'], 'answers': pretty_question})

    return prettified_result
    
class ElectionLog(models.Model):
  """
  a log of events for an election
  """

  FROZEN = "frozen"
  VOTER_FILE_ADDED = "voter file added"
  DECRYPTIONS_COMBINED = "decryptions combined"

  election = models.ForeignKey(Election)
  log = models.CharField(max_length=500)
  at = models.DateTimeField(auto_now_add=True)

##
## UTF8 craziness for CSV
##

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
      # decode UTF-8 back to Unicode, cell by cell:
      try:
        yield [unicode(cell, 'utf-8') for cell in row]
      except:
        yield [unicode(cell, 'latin-1') for cell in row]        

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
      # FIXME: this used to be line.encode('utf-8'),
      # need to figure out why this isn't consistent
      yield line
  
class VoterFile(models.Model):
  """
  A model to store files that are lists of voters to be processed
  """
  # path where we store voter upload 
  PATH = settings.VOTER_UPLOAD_REL_PATH

  election = models.ForeignKey(Election)

  # we move to storing the content in the DB
  voter_file = models.FileField(upload_to=PATH, max_length=250,null=True)
  voter_file_content = models.TextField(null=True)

  uploaded_at = models.DateTimeField(auto_now_add=True)
  processing_started_at = models.DateTimeField(auto_now_add=False, null=True)
  processing_finished_at = models.DateTimeField(auto_now_add=False, null=True)
  num_voters = models.IntegerField(null=True)

  def itervoters(self):
    if self.voter_file_content:
      if type(self.voter_file_content) == unicode:
        content = self.voter_file_content.encode('utf-8')
      else:
        content = self.voter_file_content

      # now we have to handle non-universal-newline stuff
      # we do this in a simple way: replace all \r with \n
      # then, replace all double \n with single \n
      # this should leave us with only \n
      content = content.replace('\r','\n').replace('\n\n','\n')

      voter_stream = io.BytesIO(content)
    else:
      voter_stream = open(self.voter_file.path, "rU")

    #reader = unicode_csv_reader(voter_stream)
    reader = unicodecsv.reader(voter_stream, encoding='utf-8')

    for voter_fields in reader:
      # bad line
      if len(voter_fields) < 1:
        continue
    
      return_dict = {'voter_id': voter_fields[0].strip()}

      if len(voter_fields) > 1:
        return_dict['email'] = voter_fields[1].strip()
      else:
        # assume single field means the email is the same field
        return_dict['email'] = voter_fields[0].strip()

      if len(voter_fields) > 2:
        return_dict['name'] = voter_fields[2].strip()
      else:
        return_dict['name'] = return_dict['email']

      yield return_dict
    
  def process(self):
    self.processing_started_at = datetime.datetime.utcnow()
    self.save()

    election = self.election    
    last_alias_num = election.last_alias_num

    num_voters = 0
    new_voters = []
    for voter in self.itervoters():
      num_voters += 1
    
      # does voter for this user already exist
      existing_voter = Voter.get_by_election_and_voter_id(election, voter['voter_id'])
    
      # create the voter
      if not existing_voter:
        voter_uuid = str(uuid.uuid4())
        existing_voter = Voter(uuid= voter_uuid, user = None, voter_login_id = voter['voter_id'],
                      voter_name = voter['name'], voter_email = voter['email'], election = election)
        existing_voter.generate_password()
        new_voters.append(existing_voter)
        existing_voter.save()

    if election.use_voter_aliases:
      voter_alias_integers = range(last_alias_num+1, last_alias_num+1+num_voters)
      random.shuffle(voter_alias_integers)
      for i, voter in enumerate(new_voters):
        voter.alias = 'V%s' % voter_alias_integers[i]
        voter.save()

    self.num_voters = num_voters
    self.processing_finished_at = datetime.datetime.utcnow()
    self.save()

    return num_voters


    
class Voter(HeliosModel):
  election = models.ForeignKey(Election)
  
  # let's link directly to the user now
  # FIXME: delete this as soon as migrations are set up
  #name = models.CharField(max_length = 200, null=True)
  #voter_type = models.CharField(max_length = 100)
  #voter_id = models.CharField(max_length = 100)

  uuid = models.CharField(max_length = 50)

  # for users of type password, no user object is created
  # but a dynamic user object is created automatically
  user = models.ForeignKey('helios_auth.User', null=True)

  # if user is null, then you need a voter login ID and password
  voter_login_id = models.CharField(max_length = 100, null=True)
  voter_password = models.CharField(max_length = 100, null=True)
  voter_name = models.CharField(max_length = 200, null=True)
  voter_email = models.CharField(max_length = 250, null=True)
  
  # if election uses aliases
  alias = models.CharField(max_length = 100, null=True)
  
  # we keep a copy here for easy tallying
  vote = LDObjectField(type_hint = 'legacy/EncryptedVote',
                       null=True)
  vote_hash = models.CharField(max_length = 100, null=True)
  cast_at = models.DateTimeField(auto_now_add=False, null=True)

  class Meta:
    unique_together = (('election', 'voter_login_id'))

  def __init__(self, *args, **kwargs):
    super(Voter, self).__init__(*args, **kwargs)

    # stub the user so code is not full of IF statements
    if not self.user:
      self.user = User(user_type='password', user_id=self.voter_email, name=self.voter_name)

  @classmethod
  @transaction.commit_on_success
  def register_user_in_election(cls, user, election):
    voter_uuid = str(uuid.uuid4())
    voter = Voter(uuid= voter_uuid, user = user, election = election)

    # do we need to generate an alias?
    if election.use_voter_aliases:
      heliosutils.lock_row(Election, election.id)
      alias_num = election.last_alias_num + 1
      voter.alias = "V%s" % alias_num

    voter.save()
    return voter

  @classmethod
  def get_by_election(cls, election, cast=None, order_by='voter_login_id', after=None, limit=None):
    """
    FIXME: review this for non-GAE?
    """
    query = cls.objects.filter(election = election)
    
    # the boolean check is not stupid, this is ternary logic
    # none means don't care if it's cast or not
    if cast == True:
      query = query.exclude(cast_at = None)
    elif cast == False:
      query = query.filter(cast_at = None)

    # little trick to get around GAE limitation
    # order by uuid only when no inequality has been added
    if cast == None or order_by == 'cast_at' or order_by =='-cast_at':
      query = query.order_by(order_by)
      
      # if we want the list after a certain UUID, add the inequality here
      if after:
        if order_by[0] == '-':
          field_name = "%s__gt" % order_by[1:]
        else:
          field_name = "%s__gt" % order_by
        conditions = {field_name : after}
        query = query.filter (**conditions)
    
    if limit:
      query = query[:limit]
      
    return query
  
  @classmethod
  def get_all_by_election_in_chunks(cls, election, cast=None, chunk=100):
    return cls.get_by_election(election)

  @classmethod
  def get_by_election_and_voter_id(cls, election, voter_id):
    try:
      return cls.objects.get(election = election, voter_login_id = voter_id)
    except cls.DoesNotExist:
      return None
    
  @classmethod
  def get_by_election_and_user(cls, election, user):
    try:
      return cls.objects.get(election = election, user = user)
    except cls.DoesNotExist:
      return None
      
  @classmethod
  def get_by_election_and_uuid(cls, election, uuid):
    query = cls.objects.filter(election = election, uuid = uuid)

    try:
      return query[0]
    except:
      return None

  @classmethod
  def get_by_user(cls, user):
    return cls.objects.select_related().filter(user = user).order_by('-cast_at')

  @property
  def datatype(self):
    return self.election.datatype.replace('Election', 'Voter')

  @property
  def vote_tinyhash(self):
    """
    get the tinyhash of the latest castvote
    """
    if not self.vote_hash:
      return None
    
    return CastVote.objects.get(vote_hash = self.vote_hash).vote_tinyhash

  @property
  def election_uuid(self):
    return self.election.uuid

  @property
  def name(self):
    return self.user.name

  @property
  def voter_id(self):
    return self.user.user_id

  @property
  def voter_id_hash(self):
    if self.voter_login_id:
      # for backwards compatibility with v3.0, and since it doesn't matter
      # too much if we hash the email or the unique login ID here.
      value_to_hash = self.voter_login_id
    else:
      value_to_hash = self.voter_id

    try:
      return utils.hash_b64(value_to_hash)
    except:
      try:
        return utils.hash_b64(value_to_hash.encode('latin-1'))
      except:
        return utils.hash_b64(value_to_hash.encode('utf-8'))        

  @property
  def voter_type(self):
    return self.user.user_type

  @property
  def display_html_big(self):
    return self.user.display_html_big
      
  def send_message(self, subject, body):
    self.user.send_message(subject, body)

  def generate_password(self, length=10):
    if self.voter_password:
      raise Exception("password already exists")
    
    self.voter_password = heliosutils.random_string(length, alphabet='abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789')

  def store_vote(self, cast_vote):
    # only store the vote if it's cast later than the current one
    if self.cast_at and cast_vote.cast_at < self.cast_at:
      return

    self.vote = cast_vote.vote
    self.vote_hash = cast_vote.vote_hash
    self.cast_at = cast_vote.cast_at
    self.save()
  
  def last_cast_vote(self):
    return CastVote(vote = self.vote, vote_hash = self.vote_hash, cast_at = self.cast_at, voter=self)
    
  
class CastVote(HeliosModel):
  # the reference to the voter provides the voter_uuid
  voter = models.ForeignKey(Voter)
  
  # the actual encrypted vote
  vote = LDObjectField(type_hint = 'legacy/EncryptedVote')

  # cache the hash of the vote
  vote_hash = models.CharField(max_length=100)

  # a tiny version of the hash to enable short URLs
  vote_tinyhash = models.CharField(max_length=50, null=True, unique=True)

  cast_at = models.DateTimeField(auto_now_add=True)

  # some ballots can be quarantined (this is not the same thing as provisional)
  quarantined_p = models.BooleanField(default=False, null=False)
  released_from_quarantine_at = models.DateTimeField(auto_now_add=False, null=True)

  # when is the vote verified?
  verified_at = models.DateTimeField(null=True)
  invalidated_at = models.DateTimeField(null=True)
  
  @property
  def datatype(self):
    return self.voter.datatype.replace('Voter', 'CastVote')

  @property
  def voter_uuid(self):
    return self.voter.uuid  
    
  @property
  def voter_hash(self):
    return self.voter.hash

  @property
  def is_quarantined(self):
    return self.quarantined_p and not self.released_from_quarantine_at

  def set_tinyhash(self):
    """
    find a tiny version of the hash for a URL slug.
    """
    safe_hash = self.vote_hash
    for c in ['/', '+']:
      safe_hash = safe_hash.replace(c,'')
    
    length = 8
    while True:
      vote_tinyhash = safe_hash[:length]
      if CastVote.objects.filter(vote_tinyhash = vote_tinyhash).count() == 0:
        break
      length += 1
      
    self.vote_tinyhash = vote_tinyhash

  def save(self, *args, **kwargs):
    """
    override this just to get a hook
    """
    # not saved yet? then we generate a tiny hash
    if not self.vote_tinyhash:
      self.set_tinyhash()

    super(CastVote, self).save(*args, **kwargs)
  
  @classmethod
  def get_by_voter(cls, voter):
    return cls.objects.filter(voter = voter).order_by('-cast_at')

  def verify_and_store(self):
    # if it's quarantined, don't let this go through
    if self.is_quarantined:
      raise Exception("cast vote is quarantined, verification and storage is delayed.")

    result = self.vote.verify(self.voter.election)

    if result:
      self.verified_at = datetime.datetime.utcnow()
    else:
      self.invalidated_at = datetime.datetime.utcnow()
      
    # save and store the vote as the voter's last cast vote
    self.save()

    if result:
      self.voter.store_vote(self)
    
    return result

  def issues(self, election):
    """
    Look for consistency problems
    """
    issues = []
    
    # check the election
    if self.vote.election_uuid != election.uuid:
      issues.append("the vote's election UUID does not match the election for which this vote is being cast")
    
    return issues
    
class AuditedBallot(models.Model):
  """
  ballots for auditing
  """
  election = models.ForeignKey(Election)
  raw_vote = models.TextField()
  vote_hash = models.CharField(max_length=100)
  added_at = models.DateTimeField(auto_now_add=True)

  @classmethod
  def get(cls, election, vote_hash):
    return cls.objects.get(election = election, vote_hash = vote_hash)

  @classmethod
  def get_by_election(cls, election, after=None, limit=None):
    query = cls.objects.filter(election = election).order_by('vote_hash')

    # if we want the list after a certain UUID, add the inequality here
    if after:
      query = query.filter(vote_hash__gt = after)

    if limit:
      query = query[:limit]

    return query
    
class Trustee(HeliosModel):
  election = models.ForeignKey(Election)
  
  uuid = models.CharField(max_length=50)
  name = models.CharField(max_length=200)
  email = models.EmailField()
  secret = models.CharField(max_length=100)
  
  # public key
  public_key = LDObjectField(type_hint = 'legacy/EGPublicKey',
                             null=True)
  public_key_hash = models.CharField(max_length=100)

  # secret key
  # if the secret key is present, this means
  # Helios is playing the role of the trustee.
  secret_key = LDObjectField(type_hint = 'legacy/EGSecretKey',
                             null=True)
  
  # proof of knowledge of secret key
  pok = LDObjectField(type_hint = 'legacy/DLogProof',
                      null=True)
  
  # decryption factors
  decryption_factors = LDObjectField(type_hint = datatypes.arrayOf(datatypes.arrayOf('core/BigInteger')),
                                     null=True)

  decryption_proofs = LDObjectField(type_hint = datatypes.arrayOf(datatypes.arrayOf('legacy/EGZKProof')),
                                    null=True)

  class Meta:
    unique_together = (('election', 'email'))
    
  def save(self, *args, **kwargs):
    """
    override this just to get a hook
    """
    # not saved yet?
    if not self.secret:
      self.secret = heliosutils.random_string(12)
      self.election.append_log("Trustee %s added" % self.name)
      
    super(Trustee, self).save(*args, **kwargs)
  
  @classmethod
  def get_by_election(cls, election):
    return cls.objects.filter(election = election)

  @classmethod
  def get_by_uuid(cls, uuid):
    return cls.objects.get(uuid = uuid)
    
  @classmethod
  def get_by_election_and_uuid(cls, election, uuid):
    return cls.objects.get(election = election, uuid = uuid)

  @classmethod
  def get_by_election_and_email(cls, election, email):
    try:
      return cls.objects.get(election = election, email = email)
    except cls.DoesNotExist:
      return None

  @property
  def datatype(self):
    return self.election.datatype.replace('Election', 'Trustee')    
    
  def verify_decryption_proofs(self):
    """
    verify that the decryption proofs match the tally for the election
    """
    # verify_decryption_proofs(self, decryption_factors, decryption_proofs, public_key, challenge_generator):
    return self.election.encrypted_tally.verify_decryption_proofs(self.decryption_factors, self.decryption_proofs, self.public_key, algs.EG_fiatshamir_challenge_generator)
    

########NEW FILE########
__FILENAME__ = security
"""
Helios Security -- mostly access control

Ben Adida (ben@adida.net)
"""

# nicely update the wrapper function
from functools import update_wrapper

from django.core.urlresolvers import reverse
from django.core.exceptions import *
from django.http import *
from django.conf import settings

from models import *
from helios_auth.security import get_user

from django.http import HttpResponseRedirect
import urllib

import helios

# current voter
def get_voter(request, user, election):
  """
  return the current voter
  """
  voter = None
  if request.session.has_key('CURRENT_VOTER'):
    voter = request.session['CURRENT_VOTER']
    if voter.election != election:
      voter = None

  if not voter:
    if user:
      voter = Voter.get_by_election_and_user(election, user)
  
  return voter

# a function to check if the current user is a trustee
HELIOS_TRUSTEE_UUID = 'helios_trustee_uuid'
def get_logged_in_trustee(request):
  if request.session.has_key(HELIOS_TRUSTEE_UUID):
    return Trustee.get_by_uuid(request.session[HELIOS_TRUSTEE_UUID])
  else:
    return None

def set_logged_in_trustee(request, trustee):
  request.session[HELIOS_TRUSTEE_UUID] = trustee.uuid

#
# some common election checks
#
def do_election_checks(election, props):
  # frozen
  if props.has_key('frozen'):
    frozen = props['frozen']
  else:
    frozen = None
  
  # newvoters (open for registration)
  if props.has_key('newvoters'):
    newvoters = props['newvoters']
  else:
    newvoters = None
  
  # frozen check
  if frozen != None:
    if frozen and not election.frozen_at:
      raise PermissionDenied()
    if not frozen and election.frozen_at:
      raise PermissionDenied()
    
  # open for new voters check
  if newvoters != None:
    if election.can_add_voters() != newvoters:
      raise PermissionDenied()

  
def get_election_by_uuid(uuid):
  if not uuid:
    raise Exception("no election ID")
      
  return Election.get_by_uuid(uuid)
  
# decorator for views that pertain to an election
# takes parameters:
# frozen - is the election frozen
# newvoters - does the election accept new voters
def election_view(**checks):
  
  def election_view_decorator(func):
    def election_view_wrapper(request, election_uuid=None, *args, **kw):
      election = get_election_by_uuid(election_uuid)

      if not election:
        raise Http404

      # do checks
      do_election_checks(election, checks)

      # if private election, only logged in voters
      if election.private_p and not checks.get('allow_logins',False):
        from views import password_voter_login
        if not user_can_see_election(request, election):
          return_url = request.get_full_path()
          return HttpResponseRedirect("%s?%s" % (reverse(password_voter_login, args=[election.uuid]), urllib.urlencode({
                  'return_url' : return_url
                  })))
    
      return func(request, election, *args, **kw)

    return update_wrapper(election_view_wrapper, func)
    
  return election_view_decorator

def user_can_admin_election(user, election):
  if not user:
    return False

  # election or site administrator
  return election.admin == user or user.admin_p
  
def user_can_see_election(request, election):
  user = get_user(request)

  if not election.private_p:
    return True

  # election is private
  
  # but maybe this user is the administrator?
  if user_can_admin_election(user, election):
    return True

  # or maybe this is a trustee of the election?
  trustee = get_logged_in_trustee(request)
  if trustee and trustee.election.uuid == election.uuid:
    return True

  # then this user has to be a voter
  return (get_voter(request, user, election) != None)

def api_client_can_admin_election(api_client, election):
  return election.api_client == api_client and api_client != None
  
# decorator for checking election admin access, and some properties of the election
# frozen - is the election frozen
# newvoters - does the election accept new voters
def election_admin(**checks):
  
  def election_admin_decorator(func):
    def election_admin_wrapper(request, election_uuid=None, *args, **kw):
      election = get_election_by_uuid(election_uuid)

      user = get_user(request)
      if not user_can_admin_election(user, election):
        raise PermissionDenied()
        
      # do checks
      do_election_checks(election, checks)
        
      return func(request, election, *args, **kw)

    return update_wrapper(election_admin_wrapper, func)
    
  return election_admin_decorator
  
def trustee_check(func):
  def trustee_check_wrapper(request, election_uuid, trustee_uuid, *args, **kwargs):
    election = get_election_by_uuid(election_uuid)
    
    trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)
    
    if trustee == get_logged_in_trustee(request):
      return func(request, election, trustee, *args, **kwargs)
    else:
      raise PermissionDenied()
  
  return update_wrapper(trustee_check_wrapper, func)

def can_create_election(request):
  user = get_user(request)
  if not user:
    return False
    
  if helios.ADMIN_ONLY:
    return user.admin_p
  else:
    return user != None
  
def user_can_feature_election(user, election):
  if not user:
    return False
    
  return user.admin_p
  

########NEW FILE########
__FILENAME__ = signals
"""
Helios Signals

Effectively callbacks that other apps can wait and be notified about
"""

import django.dispatch

# when an election is created
election_created = django.dispatch.Signal(providing_args=["election"])

# when a vote is cast
vote_cast = django.dispatch.Signal(providing_args=["user", "voter", "election", "cast_vote"])

# when an election is tallied
election_tallied = django.dispatch.Signal(providing_args=["election"])
########NEW FILE########
__FILENAME__ = stats_urls
"""
Helios URLs for Election related stuff

Ben Adida (ben@adida.net)
"""

from django.conf.urls.defaults import *

from helios.stats_views import *

urlpatterns = patterns(
    '',
    (r'^$', home),
    (r'^force-queue$', force_queue),
    (r'^elections$', elections),
    (r'^problem-elections$', recent_problem_elections),
    (r'^recent-votes$', recent_votes),
)

########NEW FILE########
__FILENAME__ = stats_views
"""
Helios stats views
"""

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import *
from django.db import transaction
from django.db.models import *

from security import *
from helios_auth.security import get_user, save_in_session_across_logouts
from view_utils import *

from helios import tasks

def require_admin(request):
  user = get_user(request)
  if not user or not user.admin_p:
    raise PermissionDenied()

  return user

def home(request):
  user = require_admin(request)
  num_votes_in_queue = CastVote.objects.filter(invalidated_at=None, verified_at=None).count()
  return render_template(request, 'stats', {'num_votes_in_queue': num_votes_in_queue})

def force_queue(request):
  user = require_admin(request)
  votes_in_queue = CastVote.objects.filter(invalidated_at=None, verified_at=None)
  for cv in votes_in_queue:
    tasks.cast_vote_verify_and_store.delay(cv.id)

  return HttpResponseRedirect(reverse(home))

def elections(request):
  user = require_admin(request)

  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 25))

  elections = Election.objects.all().order_by('-created_at')
  elections_paginator = Paginator(elections, limit)
  elections_page = elections_paginator.page(page)

  return render_template(request, "stats_elections", {'elections' : elections_page.object_list, 'elections_page': elections_page,
                                                      'limit' : limit})
    
def recent_votes(request):
  user = require_admin(request)
  
  # elections with a vote in the last 24 hours, ordered by most recent cast vote time
  # also annotated with number of votes cast in last 24 hours
  elections_with_votes_in_24hours = Election.objects.filter(voter__castvote__cast_at__gt= datetime.datetime.utcnow() - datetime.timedelta(days=1)).annotate(last_cast_vote = Max('voter__castvote__cast_at'), num_recent_cast_votes = Count('voter__castvote')).order_by('-last_cast_vote')

  return render_template(request, "stats_recent_votes", {'elections' : elections_with_votes_in_24hours})

def recent_problem_elections(request):
  user = require_admin(request)

  # elections left unfrozen older than 1 day old (and younger than 10 days old, so we don't go back too far)
  elections_with_problems = Election.objects.filter(frozen_at = None, created_at__gt = datetime.datetime.utcnow() - datetime.timedelta(days=10), created_at__lt = datetime.datetime.utcnow() - datetime.timedelta(days=1) )

  return render_template(request, "stats_problem_elections", {'elections' : elections_with_problems})

########NEW FILE########
__FILENAME__ = tasks
"""
Celery queued tasks for Helios

2010-08-01
ben@adida.net
"""

from celery.decorators import task

from models import *
from view_utils import render_template_raw
import signals

import copy

from django.conf import settings

@task()
def cast_vote_verify_and_store(cast_vote_id, status_update_message=None, **kwargs):
    cast_vote = CastVote.objects.get(id = cast_vote_id)
    result = cast_vote.verify_and_store()

    voter = cast_vote.voter
    election = voter.election
    user = voter.user

    if result:
        # send the signal
        signals.vote_cast.send(sender=election, election=election, user=user, voter=voter, cast_vote=cast_vote)
        
        if status_update_message and user.can_update_status():
            from views import get_election_url

            user.update_status(status_update_message)
    else:
        logger = cast_vote_verify_and_store.get_logger(**kwargs)
        logger.error("Failed to verify and store %d" % cast_vote_id)
    
@task()
def voters_email(election_id, subject_template, body_template, extra_vars={},
                 voter_constraints_include=None, voter_constraints_exclude=None):
    """
    voter_constraints_include are conditions on including voters
    voter_constraints_exclude are conditions on excluding voters
    """
    election = Election.objects.get(id = election_id)

    # select the right list of voters
    voters = election.voter_set.all()
    if voter_constraints_include:
        voters = voters.filter(**voter_constraints_include)
    if voter_constraints_exclude:
        voters = voters.exclude(**voter_constraints_exclude)

    for voter in voters:
        single_voter_email.delay(voter.uuid, subject_template, body_template, extra_vars)            

@task()
def voters_notify(election_id, notification_template, extra_vars={}):
    election = Election.objects.get(id = election_id)
    for voter in election.voter_set.all():
        single_voter_notify.delay(voter.uuid, notification_template, extra_vars)

@task()
def single_voter_email(voter_uuid, subject_template, body_template, extra_vars={}):
    voter = Voter.objects.get(uuid = voter_uuid)

    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter' : voter})

    subject = render_template_raw(None, subject_template, the_vars)
    body = render_template_raw(None, body_template, the_vars)

    voter.user.send_message(subject, body)

@task()
def single_voter_notify(voter_uuid, notification_template, extra_vars={}):
    voter = Voter.objects.get(uuid = voter_uuid)

    the_vars = copy.copy(extra_vars)
    the_vars.update({'voter' : voter})

    notification = render_template_raw(None, notification_template, the_vars)

    voter.user.send_notification(notification)

@task()
def election_compute_tally(election_id):
    election = Election.objects.get(id = election_id)
    election.compute_tally()

    election_notify_admin.delay(election_id = election_id,
                                subject = "encrypted tally computed",
                                body = """
The encrypted tally for election %s has been computed.

--
Helios
""" % election.name)
                                
    if election.has_helios_trustee():
        tally_helios_decrypt.delay(election_id = election.id)

@task()
def tally_helios_decrypt(election_id):
    election = Election.objects.get(id = election_id)
    election.helios_trustee_decrypt()
    election_notify_admin.delay(election_id = election_id,
                                subject = 'Helios Decrypt',
                                body = """
Helios has decrypted its portion of the tally
for election %s.

--
Helios
""" % election.name)

@task()
def voter_file_process(voter_file_id):
    voter_file = VoterFile.objects.get(id = voter_file_id)
    voter_file.process()
    election_notify_admin.delay(election_id = voter_file.election.id, 
                                subject = 'voter file processed',
                                body = """
Your voter file upload for election %s
has been processed.

%s voters have been created.

--
Helios
""" % (voter_file.election.name, voter_file.num_voters))

@task()
def election_notify_admin(election_id, subject, body):
    election = Election.objects.get(id = election_id)
    election.admin.send_message(subject, body)

########NEW FILE########
__FILENAME__ = test
"""
Testing Helios Features
"""

from helios.models import *
from helios_auth.models import *
import uuid

def generate_voters(election, num_voters = 1000, start_with = 1):
  # generate the user
  for v_num in range(start_with, start_with + num_voters):
    user = User(user_type='password', user_id='testuser%s' % v_num, name='Test User %s' % v_num)
    user.put()
    voter = Voter(uuid=str(uuid.uuid1()), election = election, voter_type=user.user_type, voter_id = user.user_id)
    voter.put()

def delete_voters(election):
  for v in Voter.get_by_election(election):
    v.delete()
########NEW FILE########
__FILENAME__ = tests
"""
Unit Tests for Helios
"""

import unittest, datetime, re, urllib
import django_webtest

import models
import datatypes

from helios_auth import models as auth_models
from views import ELGAMAL_PARAMS
import views
import utils

from django.db import IntegrityError, transaction
from django.test.client import Client
from django.test import TestCase
from django.utils.html import escape as html_escape

from django.core import mail
from django.core.files import File
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.exceptions import PermissionDenied

import uuid

class ElectionModelTests(TestCase):
    fixtures = ['users.json']

    def create_election(self):
        return models.Election.get_or_create(
            short_name='demo',
            name='Demo Election',
            description='Demo Election Description',
            admin=self.user)

    def setup_questions(self):
        QUESTIONS = [{"answer_urls": [None, None, None], "answers": ["a", "b", "c"], "choice_type": "approval", "max": 1, "min": 0, "question": "w?", "result_type": "absolute", "short_name": "w?", "tally_type": "homomorphic"}]
        self.election.questions = QUESTIONS

    def setup_trustee(self):
        self.election.generate_trustee(ELGAMAL_PARAMS)

    def setup_openreg(self):
        self.election.openreg=True
        self.election.save()
    
    def setUp(self):
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')
        self.fb_user = auth_models.User.objects.get(user_type='facebook')
        self.election, self.created_p = self.create_election()

    def test_create_election(self):
        # election should be created
        self.assertTrue(self.created_p)

        # should have a creation time
        self.assertNotEquals(self.election.created_at, None)
        self.assertTrue(self.election.created_at < datetime.datetime.utcnow())

    def test_find_election(self):
        election = models.Election.get_by_user_as_admin(self.user)[0]
        self.assertEquals(self.election, election)

        election = models.Election.get_by_uuid(self.election.uuid)
        self.assertEquals(self.election, election)

        election = models.Election.get_by_short_name(self.election.short_name)
        self.assertEquals(self.election, election)
        
    def test_setup_trustee(self):
        self.setup_trustee()
        self.assertEquals(self.election.num_trustees, 1)

    def test_add_voters_file(self):
        election = self.election

        FILE = "helios/fixtures/voter-file.csv"
        vf = models.VoterFile.objects.create(election = election, voter_file = File(open(FILE), "voter_file.css"))
        vf.process()

        # make sure that we stripped things correctly
        voter = election.voter_set.get(voter_login_id = 'benadida5')
        self.assertEquals(voter.voter_email, 'ben5@adida.net')
        self.assertEquals(voter.voter_name, 'Ben5 Adida')

    def test_check_issues_before_freeze(self):
        # should be three issues: no trustees, and no questions, and no voters
        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 3)

        self.setup_questions()

        # should be two issues: no trustees, and no voters
        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 2)

        self.election.questions = None

        self.setup_trustee()

        # should be two issues: no questions, and no voters
        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 2)
        
        self.setup_questions()

        # move to open reg
        self.setup_openreg()

        issues = self.election.issues_before_freeze
        self.assertEquals(len(issues), 0)
        
    def test_helios_trustee(self):
        self.election.generate_trustee(ELGAMAL_PARAMS)

        self.assertTrue(self.election.has_helios_trustee())

        trustee = self.election.get_helios_trustee()
        self.assertNotEquals(trustee, None)

    def test_log(self):
        LOGS = ["testing 1", "testing 2", "testing 3"]

        for l in LOGS:
            self.election.append_log(l)

        pulled_logs = [l.log for l in self.election.get_log().all()]
        pulled_logs.reverse()

        self.assertEquals(LOGS,pulled_logs)

    def test_eligibility(self):
        self.election.eligibility = [{'auth_system': self.user.user_type}]

        # without openreg, this should be false
        self.assertFalse(self.election.user_eligible_p(self.user))
        
        # what about after saving?
        self.election.save()
        e = models.Election.objects.get(uuid = self.election.uuid)
        self.assertEquals(e.eligibility, [{'auth_system': self.user.user_type}])

        self.election.openreg = True

        # without openreg, and now true
        self.assertTrue(self.election.user_eligible_p(self.user))

        # try getting pretty eligibility, make sure it doesn't throw an exception
        assert self.user.user_type in self.election.pretty_eligibility

    def test_facebook_eligibility(self):
        self.election.eligibility = [{'auth_system': 'facebook', 'constraint':[{'group': {'id': '123', 'name':'Fake Group'}}]}]

        # without openreg, this should be false
        self.assertFalse(self.election.user_eligible_p(self.fb_user))
        
        self.election.openreg = True

        # fake out the facebook constraint checking, since
        # our access_token is obviously wrong
        from helios_auth.auth_systems import facebook

        def fake_check_constraint(constraint, user):
            return constraint == {'group': {'id': '123', 'name':'Fake Group'}} and user == self.fb_user                
        facebook.check_constraint = fake_check_constraint

        self.assertTrue(self.election.user_eligible_p(self.fb_user))

        # also check that eligibility_category_id does the right thing
        self.assertEquals(self.election.eligibility_category_id('facebook'), '123')

    def test_freeze(self):
        # freezing without trustees and questions, no good
        def try_freeze():
            self.election.freeze()
        self.assertRaises(Exception, try_freeze)
        
        self.setup_questions()
        self.setup_trustee()
        self.setup_openreg()

        # this time it should work
        try_freeze()
        
        # make sure it logged something
        self.assertTrue(len(self.election.get_log().all()) > 0)

    def test_archive(self):
        self.election.archived_at = datetime.datetime.utcnow()
        self.assertTrue(self.election.is_archived)

        self.election.archived_at = None
        self.assertFalse(self.election.is_archived)

    def test_voter_registration(self):
        # before adding a voter
        voters = models.Voter.get_by_election(self.election)
        self.assertTrue(len(voters) == 0)

        # make sure no voter yet
        voter = models.Voter.get_by_election_and_user(self.election, self.user)
        self.assertTrue(voter == None)

        # make sure no voter at all across all elections
        voters = models.Voter.get_by_user(self.user)
        self.assertTrue(len(voters) == 0)

        # register the voter
        voter = models.Voter.register_user_in_election(self.user, self.election)
        
        # make sure voter is there now
        voter_2 = models.Voter.get_by_election_and_user(self.election, self.user)

        self.assertFalse(voter == None)
        self.assertFalse(voter_2 == None)
        self.assertEquals(voter, voter_2)

        # make sure voter is there in this call too
        voters = models.Voter.get_by_user(self.user)
        self.assertTrue(len(voters) == 1)
        self.assertEquals(voter, voters[0])

        voter_2 = models.Voter.get_by_election_and_uuid(self.election, voter.uuid)
        self.assertEquals(voter, voter_2)

        self.assertEquals(voter.user, self.user)



class VoterModelTests(TestCase):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.get(short_name='test')

    def test_create_password_voter(self):
        v = models.Voter(uuid = str(uuid.uuid1()), election = self.election, voter_login_id = 'voter_test_1', voter_name = 'Voter Test 1', voter_email='foobar@acme.com')

        v.generate_password()

        v.save()
        
        # password has been generated!
        self.assertFalse(v.voter_password == None)

        # can't generate passwords twice
        self.assertRaises(Exception, lambda: v.generate_password())
        
        # check that you can get at the voter user structure
        self.assertEquals(v.user.user_id, v.voter_email)


class CastVoteModelTests(TestCase):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.get(short_name='test')
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

        # register the voter
        self.voter = models.Voter.register_user_in_election(self.user, self.election)

    def test_cast_vote(self):
        pass

class DatatypeTests(TestCase):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.election.generate_trustee(ELGAMAL_PARAMS)

    def test_instantiate(self):
        ld_obj = datatypes.LDObject.instantiate(self.election.get_helios_trustee(), '2011/01/Trustee')
        foo = ld_obj.serialize()

    def test_from_dict(self):
        ld_obj = datatypes.LDObject.fromDict({
                'y' : '1234',
                'p' : '23434',
                'g' : '2343243242',
                'q' : '2343242343434'}, type_hint = 'pkc/elgamal/PublicKey')

    def test_dictobject_from_dict(self):
        original_dict = {
            'A' : '35423432',
            'B' : '234324243'}
        ld_obj = datatypes.LDObject.fromDict(original_dict, type_hint = 'legacy/EGZKProofCommitment')

        self.assertEquals(original_dict, ld_obj.toDict())
        
        
        

##
## Black box tests
##

class DataFormatBlackboxTests(object):
    def setUp(self):
        self.election = models.Election.objects.all()[0]

    def assertEqualsToFile(self, response, file_path):
        expected = open(file_path)
        self.assertEquals(response.content, expected.read())
        expected.close()

    def test_election(self):
        response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_ELECTION_FILE)

    def test_election_metadata(self):
        response = self.client.get("/helios/elections/%s/meta" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_ELECTION_METADATA_FILE)

    def test_voters_list(self):
        response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_VOTERS_FILE)

    def test_trustees_list(self):
        response = self.client.get("/helios/elections/%s/trustees/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_TRUSTEES_FILE)

    def test_ballots_list(self):
        response = self.client.get("/helios/elections/%s/ballots/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_BALLOTS_FILE)

## now we have a set of fixtures and expected results for various formats
## note how TestCase is used as a "mixin" here, so that the generic DataFormatBlackboxTests
## does not register as a set of test cases to run, but each concrete data format does.

class LegacyElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
    fixtures = ['legacy-data.json']
    EXPECTED_ELECTION_FILE = 'helios/fixtures/legacy-election-expected.json'
    EXPECTED_ELECTION_METADATA_FILE = 'helios/fixtures/legacy-election-metadata-expected.json'
    EXPECTED_VOTERS_FILE = 'helios/fixtures/legacy-election-voters-expected.json'
    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/legacy-trustees-expected.json'
    EXPECTED_BALLOTS_FILE = 'helios/fixtures/legacy-ballots-expected.json'

#class V3_1_ElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
#    fixtures = ['v3.1-data.json']
#    EXPECTED_ELECTION_FILE = 'helios/fixtures/v3.1-election-expected.json'
#    EXPECTED_VOTERS_FILE = 'helios/fixtures/v3.1-election-voters-expected.json'
#    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/v3.1-trustees-expected.json'
#    EXPECTED_BALLOTS_FILE = 'helios/fixtures/v3.1-ballots-expected.json'

class WebTest(django_webtest.WebTest):
    def assertRedirects(self, response, url):
        """
        reimplement this in case it's a WebOp response
        and it seems to be screwing up in a few places too
        thus the localhost exception
        """
        if hasattr(response, 'location'):
            assert url in response.location
        else:
            assert url in response._headers['location'][1]

        if hasattr(response, 'status_code'):
            assert response.status_code == 302
        else:
            assert response.status_int == 302

        #self.assertEqual(response.status_code, 302)

        #return super(django_webtest.WebTest, self).assertRedirects(response, url)
        #if hasattr(response, 'status_code') and hasattr(response, 'location'):


        #assert url in response.location, "redirected to %s instead of %s" % (response.location, url)

    def assertContains(self, response, text):
        if hasattr(response, 'status_code'):
            assert response.status_code == 200
#            return super(django_webtest.WebTest, self).assertContains(response, text)
        else:
            assert response.status_int == 200

        
        if hasattr(response, "testbody"):
            assert text in response.testbody, "missing text %s" % text
        else:
            if hasattr(response, "body"):
                assert text in response.body, "missing text %s" % text        
            else:
                assert text in response.content, "missing text %s" % text


##
## overall operation of the system
##

class ElectionBlackboxTests(WebTest):
    fixtures = ['users.json', 'election.json']

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

    def assertContains(self, response, text):
        if hasattr(response, 'status_code'):
            assert response.status_code == 200
#            return super(django_webtest.WebTest, self).assertContains(response, text)
        else:
            assert response.status_int == 200

        
        if hasattr(response, "testbody"):
            assert text in response.testbody, "missing text %s" % text
        else:
            if hasattr(response, "body"):
                assert text in response.body, "missing text %s" % text        
            else:
                assert text in response.content, "missing text %s" % text

    def setup_login(self):
        # set up the session
        session = self.client.session
        session['user'] = {'type': self.user.user_type, 'user_id': self.user.user_id}
        session.save()

        # set up the app, too
        # this does not appear to work, boohoo
        session = self.app.session
        session['user'] = {'type': self.user.user_type, 'user_id': self.user.user_id}

    def clear_login(self):
        session = self.client.session
        del session['user']
        session.save()        

    def test_election_params(self):
        response = self.client.get("/helios/elections/params")
        self.assertEquals(response.content, views.ELGAMAL_PARAMS_LD_OBJECT.serialize())

    def test_election_404(self):
        response = self.client.get("/helios/elections/foobar")
        self.assertEquals(response.status_code, 404)

    def test_election_bad_trustee(self):
        response = self.client.get("/helios/t/%s/foobar@bar.com/badsecret" % self.election.short_name)
        self.assertEquals(response.status_code, 404)

    def test_get_election_shortcut(self):
        response = self.client.get("/helios/e/%s" % self.election.short_name, follow=True)
        self.assertContains(response, self.election.description)
        
    def test_get_election_raw(self):
        response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
        self.assertEquals(response.content, self.election.toJSON())
    
    def test_get_election(self):
        response = self.client.get("/helios/elections/%s/view" % self.election.uuid, follow=False)
        self.assertContains(response, self.election.description)

    def test_get_election_questions(self):
        response = self.client.get("/helios/elections/%s/questions" % self.election.uuid, follow=False)
        for q in self.election.questions:
            self.assertContains(response, q['question'])
    
    def test_get_election_trustees(self):
        response = self.client.get("/helios/elections/%s/trustees" % self.election.uuid, follow=False)
        for t in self.election.trustee_set.all():
            self.assertContains(response, t.name)

    def test_get_election_voters(self):
        response = self.client.get("/helios/elections/%s/voters/list" % self.election.uuid, follow=False)
        # check total count of voters
        if self.election.num_voters == 0:
            self.assertContains(response, "no voters")
        else:
            self.assertContains(response, "(of %s)" % self.election.num_voters)

    def test_get_election_voters_raw(self):
        response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
        self.assertEquals(len(utils.from_json(response.content)), self.election.num_voters)
        
    def test_election_creation_not_logged_in(self):
        response = self.client.post("/helios/elections/new", {
                "short_name" : "test-complete",
                "name" : "Test Complete",
                "description" : "A complete election test",
                "election_type" : "referendum",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p" : "0"})

        self.assertRedirects(response, "/auth/?return_url=/helios/elections/new")
    
    def test_election_edit(self):
        # a bogus call to set up the session
        self.client.get("/")

        self.setup_login()
        response = self.client.get("/helios/elections/%s/edit" % self.election.uuid)
        response = self.client.post("/helios/elections/%s/edit" % self.election.uuid, {
                "short_name" : self.election.short_name + "-2",
                "name" : self.election.name,
                "description" : self.election.description,
                "election_type" : self.election.election_type,
                "use_voter_aliases": self.election.use_voter_aliases,
                'csrf_token': self.client.session['csrf_token']
                })

        self.assertRedirects(response, "/helios/elections/%s/view" % self.election.uuid)

        new_election = models.Election.objects.get(uuid = self.election.uuid)
        self.assertEquals(new_election.short_name, self.election.short_name + "-2")

    def _setup_complete_election(self, election_params={}):
        "do the setup part of a whole election"

        # a bogus call to set up the session
        self.client.get("/")

        # REPLACE with params?
        self.setup_login()

        # create the election
        full_election_params = {
            "short_name" : "test-complete",
            "name" : "Test Complete",
            "description" : "A complete election test",
            "election_type" : "referendum",
            "use_voter_aliases": "0",
            "use_advanced_audit_features": "1",
            "private_p" : "0"}

        # override with the given
        full_election_params.update(election_params)

        response = self.client.post("/helios/elections/new", full_election_params)

        # we are redirected to the election, let's extract the ID out of the URL
        election_id = re.search('/elections/([^/]+)/', str(response['Location'])).group(1)

        # helios is automatically added as a trustee

        # check that helios is indeed a trustee
        response = self.client.get("/helios/elections/%s/trustees/view" % election_id)
        self.assertContains(response, "Trustee #1")

        # add a few voters with an improperly placed email address
        FILE = "helios/fixtures/voter-badfile.csv"
        voters_file = open(FILE)
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'voters_file': voters_file})
        voters_file.close()
        self.assertContains(response, "HOLD ON")

        # add a few voters, via file upload
        # this file now includes a UTF-8 encoded unicode character
        # yes I know that's not how you spell Ernesto.
        # I just needed some unicode quickly.
        FILE = "helios/fixtures/voter-file.csv"
        voters_file = open(FILE)
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'voters_file': voters_file})
        voters_file.close()
        self.assertContains(response, "first few rows of this file")

        # now we confirm the upload
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'confirm_p': "1"})
        self.assertRedirects(response, "/helios/elections/%s/voters/list" % election_id)

        # and we want to check that there are now voters
        response = self.client.get("/helios/elections/%s/voters/" % election_id)
        NUM_VOTERS = 4
        self.assertEquals(len(utils.from_json(response.content)), NUM_VOTERS)

        # let's get a single voter
        single_voter = models.Election.objects.get(uuid = election_id).voter_set.all()[0]
        response = self.client.get("/helios/elections/%s/voters/%s" % (election_id, single_voter.uuid))
        self.assertContains(response, '"uuid": "%s"' % single_voter.uuid)

        response = self.client.get("/helios/elections/%s/voters/foobar" % election_id)
        self.assertEquals(response.status_code, 404)
        
        # add questions
        response = self.client.post("/helios/elections/%s/save_questions" % election_id, {
                'questions_json': utils.to_json([{"answer_urls": [None,None], "answers": ["Alice", "Bob"], "choice_type": "approval", "max": 1, "min": 0, "question": "Who should be president?", "result_type": "absolute", "short_name": "Who should be president?", "tally_type": "homomorphic"}]),
                'csrf_token': self.client.session['csrf_token']})

        self.assertContains(response, "SUCCESS")

        # freeze election
        response = self.client.post("/helios/elections/%s/freeze" % election_id, {
                "csrf_token" : self.client.session['csrf_token']})
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        # email the voters
        num_messages_before = len(mail.outbox)
        response = self.client.post("/helios/elections/%s/voters/email" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                "subject" : "your password",
                "body" : "time to vote",
                "suppress_election_links" : "0",
                "send_to" : "all"
                })
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)
        num_messages_after = len(mail.outbox)
        self.assertEquals(num_messages_after - num_messages_before, NUM_VOTERS)

        email_message = mail.outbox[num_messages_before]
        assert "your password" in email_message.subject, "bad subject in email"

        # get the username and password
        username = re.search('voter ID: (.*)', email_message.body).group(1)
        password = re.search('password: (.*)', email_message.body).group(1)

        # now log out as administrator
        self.clear_login()
        self.assertEquals(self.client.session.has_key('user'), False)

        # return the voter username and password to vote
        return election_id, username, password

    def _cast_ballot(self, election_id, username, password, need_login=True, check_user_logged_in=False):
        """
        check_user_logged_in looks for the "you're already logged" message
        """
        # vote by preparing a ballot via the server-side encryption
        response = self.app.post("/helios/elections/%s/encrypt-ballot" % election_id, {
                'answers_json': utils.to_json([[1]])})
        self.assertContains(response, "answers")

        # parse it as an encrypted vote with randomness, and make sure randomness is there
        the_ballot = utils.from_json(response.testbody)
        assert the_ballot['answers'][0].has_key('randomness'), "no randomness"
        assert len(the_ballot['answers'][0]['randomness']) == 2, "not enough randomness"
        
        # parse it as an encrypted vote, and re-serialize it
        ballot = datatypes.LDObject.fromDict(utils.from_json(response.testbody), type_hint='legacy/EncryptedVote')
        encrypted_vote = ballot.serialize()
        
        # cast the ballot
        response = self.app.post("/helios/elections/%s/cast" % election_id, {
                'encrypted_vote': encrypted_vote})
        self.assertRedirects(response, "%s/helios/elections/%s/cast_confirm" % (settings.SECURE_URL_HOST, election_id))

        cast_confirm_page = response.follow()

        if need_login:
            if check_user_logged_in:
                self.assertContains(cast_confirm_page, "You are logged in as")
                self.assertContains(cast_confirm_page, "requires election-specific credentials")

            # set the form
            login_form = cast_confirm_page.form
            login_form['voter_id'] = username
            login_form['password'] = password

            # we skip that intermediary page now
            # cast_confirm_page = login_form.submit()
            response = login_form.submit()

            # self.assertRedirects(cast_confirm_page, "/helios/elections/%s/cast_confirm" % election_id)
            # cast_confirm_page = cast_confirm_page.follow()
        else:
            # here we should be at the cast-confirm page and logged in
            self.assertContains(cast_confirm_page, "CAST this ballot")

            # confirm the vote, now with the actual form
            cast_form = cast_confirm_page.form
        
            if 'status_update' in cast_form.fields.keys():
                cast_form['status_update'] = False
            response = cast_form.submit()

        self.assertRedirects(response, "%s/helios/elections/%s/cast_done" % (settings.URL_HOST, election_id))

        # at this point an email should have gone out to the user
        # at position num_messages after, since that was the len() before we cast this ballot
        email_message = mail.outbox[len(mail.outbox) - 1]
        url = re.search('http://[^/]+(/[^ \n]*)', email_message.body).group(1)

        # check that we can get at that URL
        if not need_login:
            # confusing piece: if need_login is True, that means it was a public election
            # that required login before casting a ballot.
            # so if need_login is False, it was a private election, and we do need to re-login here
            # we need to re-login if it's a private election, because all data, including ballots
            # is otherwise private
            login_page = self.app.get("/helios/elections/%s/password_voter_login" % election_id)

            # if we redirected, that's because we can see the page, I think
            if login_page.status_int != 302:
                login_form = login_page.form
                
                # try with extra spaces
                login_form['voter_id'] = '  ' + username + '   '
                login_form['password'] = '  ' + password + '      '
                login_form.submit()
            
        response = self.app.get(url)
        self.assertContains(response, ballot.hash)
        self.assertContains(response, html_escape(encrypted_vote))

        # if we request the redirect to cast_done, the voter should be logged out, but not the user
        response = self.app.get("/helios/elections/%s/cast_done" % election_id)

        # FIXME: how to check this? We can't do it by checking session that we're doign webtes
        # assert not self.client.session.has_key('CURRENT_VOTER')

    def _do_tally(self, election_id):
        # log back in as administrator
        self.setup_login()

        # encrypted tally
        response = self.client.post("/helios/elections/%s/compute_tally" % election_id, {
                "csrf_token" : self.client.session['csrf_token']                
                })
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        # should trigger helios decryption automatically
        self.assertNotEquals(models.Election.objects.get(uuid=election_id).get_helios_trustee().decryption_proofs, None)

        # combine decryptions
        response = self.client.post("/helios/elections/%s/combine_decryptions" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                })

        # after tallying, we now go back to election_view
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        # check that we can't get the tally yet
        response = self.client.get("/helios/elections/%s/result" % election_id)
        self.assertEquals(response.status_code, 403)

        # release
        response = self.client.post("/helios/elections/%s/release_result" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                })

        # check that tally matches
        response = self.client.get("/helios/elections/%s/result" % election_id)
        self.assertEquals(utils.from_json(response.content), [[0,1]])
        
    def test_do_complete_election(self):
        election_id, username, password = self._setup_complete_election()
        
        # cast a ballot while not logged in
        self._cast_ballot(election_id, username, password, check_user_logged_in=False)

        # cast a ballot while logged in as a user (not a voter)
        self.setup_login()

        ## for now the above does not work, it's a testing problem
        ## where the cookie isn't properly set. We'll have to figure this out.
        ## FIXME FIXME FIXME 
        # self._cast_ballot(election_id, username, password, check_user_logged_in=True)
        self._cast_ballot(election_id, username, password, check_user_logged_in=False)
        self.clear_login()

        self._do_tally(election_id)

    def test_do_complete_election_private(self):
        # private election
        election_id, username, password = self._setup_complete_election({'private_p' : "1"})

        # get the password_voter_login_form via the front page
        # (which will test that redirects are doing the right thing)
        response = self.app.get("/helios/elections/%s/view" % election_id)

        # ensure it redirects
        self.assertRedirects(response, "/helios/elections/%s/password_voter_login?%s" % (election_id, urllib.urlencode({"return_url": "/helios/elections/%s/view" % election_id})))

        login_form = response.follow().form

        login_form['voter_id'] = username
        login_form['password'] = password

        response = login_form.submit()
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        self._cast_ballot(election_id, username, password, need_login = False)
        self._do_tally(election_id)

    def test_election_voters_eligibility(self):
        # create the election
        self.client.get("/")
        self.setup_login()
        response = self.client.post("/helios/elections/new", {
                "short_name" : "test-eligibility",
                "name" : "Test Eligibility",
                "description" : "An election test for voter eligibility",
                "election_type" : "election",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p" : "0"})

        election_id = re.match("(.*)/elections/(.*)/view", response['Location']).group(2)
        
        # update eligiblity
        response = self.client.post("/helios/elections/%s/voters/eligibility" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                "eligibility": "openreg"})

        self.clear_login()
        response = self.client.get("/helios/elections/%s/voters/list" % election_id)
        self.assertContains(response, "Anyone can vote")

        self.setup_login()
        response = self.client.post("/helios/elections/%s/voters/eligibility" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                "eligibility": "closedreg"})

        self.clear_login()
        response = self.client.get("/helios/elections/%s/voters/list" % election_id)
        self.assertContains(response, "Only the voters listed here")

    def test_do_complete_election_with_trustees(self):
        """
        FIXME: do the this test
        """
        pass

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *

from django.conf import settings

from views import *

urlpatterns = None

urlpatterns = patterns('',
  (r'^autologin$', admin_autologin),
  (r'^testcookie$', test_cookie),
  (r'^testcookie_2$', test_cookie_2),
  (r'^nocookies$', nocookies),
  (r'^stats/', include('helios.stats_urls')),
  (r'^socialbuttons$', socialbuttons),

  # election shortcut by shortname
  (r'^e/(?P<election_short_name>[^/]+)$', election_shortcut),
  (r'^e/(?P<election_short_name>[^/]+)/vote$', election_vote_shortcut),

  # vote shortcut
  (r'^v/(?P<vote_tinyhash>[^/]+)$', castvote_shortcut),
  
  # trustee login
  (r'^t/(?P<election_short_name>[^/]+)/(?P<trustee_email>[^/]+)/(?P<trustee_secret>[^/]+)$', trustee_login),
  
  # election
  (r'^elections/params$', election_params),
  (r'^elections/verifier$', election_verifier),
  (r'^elections/single_ballot_verifier$', election_single_ballot_verifier),
  (r'^elections/new$', election_new),
  (r'^elections/administered$', elections_administered),
  (r'^elections/voted$', elections_voted),
  
  (r'^elections/(?P<election_uuid>[^/]+)', include('helios.election_urls')),
  
)



########NEW FILE########
__FILENAME__ = utils
"""
Utilities.

Ben Adida - ben@adida.net
2005-04-11
"""

import urllib, re, sys, datetime, urlparse, string

import boto.ses

# utils from helios_auth, too
from helios_auth.utils import *

from django.conf import settings
  
import random, logging
import hashlib, hmac, base64

def do_hmac(k,s):
  """
  HMAC a value with a key, hex output
  """
  mac = hmac.new(k, s, hashlib.sha1)
  return mac.hexdigest()


def split_by_length(str, length, rejoin_with=None):
  """
  split a string by a given length
  """
  str_arr = []
  counter = 0
  while counter<len(str):
    str_arr.append(str[counter:counter+length])
    counter += length

  if rejoin_with:
    return rejoin_with.join(str_arr)
  else:
    return str_arr
    

def urlencode(str):
    """
    URL encode
    """
    if not str:
        return ""

    return urllib.quote(str)

def urlencodeall(str):
    """
    URL encode everything even unresreved chars
    """
    if not str:
        return ""

    return string.join(['%' + s.encode('hex') for s in str], '')

def urldecode(str):
    if not str:
        return ""

    return urllib.unquote(str)

def dictToURLParams(d):
  if d:
    return '&'.join([i + '=' + urlencode(v) for i,v in d.items()])
  else:
    return None
##
## XML escaping and unescaping
## 

def xml_escape(s):
    raise Exception('not implemented yet')

def xml_unescape(s):
    new_s = s.replace('&lt;','<').replace('&gt;','>')
    return new_s
    
##
## XSS attack prevention
##

def xss_strip_all_tags(s):
    """
    Strips out all HTML.
    """
    return s
    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
            import htmlentitydefs
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
        
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, s)
    
 
random.seed()

def random_string(length=20, alphabet=None):
    random.seed()
    ALPHABET = alphabet or 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    r_string = ''
    for i in range(length):
        r_string += random.choice(ALPHABET)

    return r_string

def get_host():
  return settings.SERVER_HOST
  
def get_prefix():
  return settings.SERVER_PREFIX
  

##
## Datetime utilities
##

def string_to_datetime(str, fmt="%Y-%m-%d %H:%M"):
  if str == None:
    return None

  return datetime.datetime.strptime(str, fmt)
  
##
## email
##

from django.core import mail as django_mail

def send_email(sender, recpt_lst, subject, body):
  # subject up until the first newline
  subject = subject.split("\n")[0]

  django_mail.send_mail(subject, body, sender, recpt_lst, fail_silently=True)

  
##
## raw SQL and locking
##

def one_val_raw_sql(raw_sql, values=[]):
  """
  for a simple aggregate
  """
  from django.db import connection, transaction
  cursor = connection.cursor()

  cursor.execute(raw_sql, values)
  return cursor.fetchone()[0]

def lock_row(model, pk):
  """
  you almost certainly want to use lock_row inside a commit_on_success function
  Eventually, in Django 1.2, this should move to the .for_update() support
  """

  from django.db import connection, transaction
  cursor = connection.cursor()

  cursor.execute("select * from " + model._meta.db_table + " where id = %s for update", [pk])
  row = cursor.fetchone()

  # if this is under transaction management control, mark the transaction dirty
  try:
    transaction.set_dirty()
  except:
    pass

  return row

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
Helios Django Views

Ben Adida (ben@adida.net)
"""

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.http import *
from django.db import transaction

from mimetypes import guess_type

from validate_email import validate_email

import csv, urllib, os, base64

from crypto import algs, electionalgs, elgamal
from crypto import utils as cryptoutils
from workflows import homomorphic
from helios import utils as helios_utils
from view_utils import *

from helios_auth.security import *
from helios_auth.auth_systems import AUTH_SYSTEMS, can_list_categories
from helios_auth.models import AuthenticationExpired

from helios import security
from helios_auth import views as auth_views

import tasks

from security import *
from helios_auth.security import get_user, save_in_session_across_logouts

import uuid, datetime

from models import *

import forms, signals

# Parameters for everything
ELGAMAL_PARAMS = elgamal.Cryptosystem()

# trying new ones from OlivierP
ELGAMAL_PARAMS.p = 16328632084933010002384055033805457329601614771185955389739167309086214800406465799038583634953752941675645562182498120750264980492381375579367675648771293800310370964745767014243638518442553823973482995267304044326777047662957480269391322789378384619428596446446984694306187644767462460965622580087564339212631775817895958409016676398975671266179637898557687317076177218843233150695157881061257053019133078545928983562221396313169622475509818442661047018436264806901023966236718367204710755935899013750306107738002364137917426595737403871114187750804346564731250609196846638183903982387884578266136503697493474682071L
ELGAMAL_PARAMS.q = 61329566248342901292543872769978950870633559608669337131139375508370458778917L
ELGAMAL_PARAMS.g = 14887492224963187634282421537186040801304008017743492304481737382571933937568724473847106029915040150784031882206090286938661464458896494215273989547889201144857352611058572236578734319505128042602372864570426550855201448111746579871811249114781674309062693442442368697449970648232621880001709535143047913661432883287150003429802392229361583608686643243349727791976247247948618930423866180410558458272606627111270040091203073580238905303994472202930783207472394578498507764703191288249547659899997131166130259700604433891232298182348403175947450284433411265966789131024573629546048637848902243503970966798589660808533L

# object ready for serialization
ELGAMAL_PARAMS_LD_OBJECT = datatypes.LDObject.instantiate(ELGAMAL_PARAMS, datatype='legacy/EGParams')

# single election server? Load the single electionfrom models import Election
from django.conf import settings

def get_election_url(election):
  return settings.URL_HOST + reverse(election_shortcut, args=[election.short_name])  

def get_election_badge_url(election):
  return settings.URL_HOST + reverse(election_badge, args=[election.uuid])  

def get_election_govote_url(election):
  return settings.URL_HOST + reverse(election_vote_shortcut, args=[election.short_name])  

def get_castvote_url(cast_vote):
  return settings.URL_HOST + reverse(castvote_shortcut, args=[cast_vote.vote_tinyhash])

# social buttons
def get_socialbuttons_url(url, text):
  if not text:
    return None
  
  return "%s%s?%s" % (settings.SOCIALBUTTONS_URL_HOST,
                      reverse(socialbuttons),
                      urllib.urlencode({
        'url' : url,
        'text': text.encode('utf-8')
        }))
  

##
## remote auth utils

def user_reauth(request, user):
  # FIXME: should we be wary of infinite redirects here, and
  # add a parameter to prevent it? Maybe.
  login_url = "%s%s?%s" % (settings.SECURE_URL_HOST,
                           reverse(auth_views.start, args=[user.user_type]),
                           urllib.urlencode({'return_url':
                                               request.get_full_path()}))
  return HttpResponseRedirect(login_url)

## 
## simple admin for development
##
def admin_autologin(request):
  if "localhost" not in settings.URL_HOST and "127.0.0.1" not in settings.URL_HOST:
    raise Http404
  
  users = User.objects.filter(admin_p=True)
  if len(users) == 0:
    return HttpResponse("no admin users!")

  if len(users) == 0:
    return HttpResponse("no users!")

  user = users[0]
  request.session['user'] = {'type' : user.user_type, 'user_id' : user.user_id}
  return HttpResponseRedirect("/")

##
## General election features
##

@json
def election_params(request):
  return ELGAMAL_PARAMS_LD_OBJECT.toJSONDict()

def election_verifier(request):
  return render_template(request, "tally_verifier")

def election_single_ballot_verifier(request):
  return render_template(request, "ballot_verifier")

def election_shortcut(request, election_short_name):
  election = Election.get_by_short_name(election_short_name)
  if election:
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
  else:
    raise Http404

# a hidden view behind the shortcut that performs the actual perm check
@election_view()
def _election_vote_shortcut(request, election):
  vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode({'election_url' : reverse(one_election, args=[election.uuid])}))
  
  test_cookie_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : vote_url}))

  return HttpResponseRedirect(test_cookie_url)
  
def election_vote_shortcut(request, election_short_name):
  election = Election.get_by_short_name(election_short_name)
  if election:
    return _election_vote_shortcut(request, election_uuid=election.uuid)
  else:
    raise Http404

@election_view()
def _castvote_shortcut_by_election(request, election, cast_vote):
  return render_template(request, 'castvote', {'cast_vote' : cast_vote, 'vote_content': cast_vote.vote.toJSON(), 'the_voter': cast_vote.voter, 'election': election})
  
def castvote_shortcut(request, vote_tinyhash):
  try:
    cast_vote = CastVote.objects.get(vote_tinyhash = vote_tinyhash)
  except CastVote.DoesNotExist:
    raise Http404

  return _castvote_shortcut_by_election(request, election_uuid = cast_vote.voter.election.uuid, cast_vote=cast_vote)

@trustee_check
def trustee_keygenerator(request, election, trustee):
  """
  A key generator with the current params, like the trustee home but without a specific election.
  """
  eg_params_json = utils.to_json(ELGAMAL_PARAMS_LD_OBJECT.toJSONDict())

  return render_template(request, "election_keygenerator", {'eg_params_json': eg_params_json, 'election': election, 'trustee': trustee})

@login_required
def elections_administered(request):
  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator has elections to administer')
  
  user = get_user(request)
  elections = Election.get_by_user_as_admin(user)
  
  return render_template(request, "elections_administered", {'elections': elections})

@login_required
def elections_voted(request):
  user = get_user(request)
  elections = Election.get_by_user_as_voter(user)
  
  return render_template(request, "elections_voted", {'elections': elections})
    

@login_required
def election_new(request):
  if not can_create_election(request):
    return HttpResponseForbidden('only an administrator can create an election')
    
  error = None
  
  if request.method == "GET":
    election_form = forms.ElectionForm(initial={'private_p': settings.HELIOS_PRIVATE_DEFAULT})
  else:
    election_form = forms.ElectionForm(request.POST)
    
    if election_form.is_valid():
      # create the election obj
      election_params = dict(election_form.cleaned_data)
      
      # is the short name valid
      if helios_utils.urlencode(election_params['short_name']) == election_params['short_name']:      
        election_params['uuid'] = str(uuid.uuid1())
        election_params['cast_url'] = settings.SECURE_URL_HOST + reverse(one_election_cast, args=[election_params['uuid']])
      
        # registration starts closed
        election_params['openreg'] = False

        user = get_user(request)
        election_params['admin'] = user
        
        election, created_p = Election.get_or_create(**election_params)
      
        if created_p:
          # add Helios as a trustee by default
          election.generate_trustee(ELGAMAL_PARAMS)
          
          return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
        else:
          error = "An election with short name %s already exists" % election_params['short_name']
      else:
        error = "No special characters allowed in the short name."
    
  return render_template(request, "election_new", {'election_form': election_form, 'error': error})
  
@election_admin(frozen=False)
def one_election_edit(request, election):

  error = None
  RELEVANT_FIELDS = ['short_name', 'name', 'description', 'use_voter_aliases', 'election_type', 'private_p', 'help_email', 'randomize_answer_order']
  # RELEVANT_FIELDS += ['use_advanced_audit_features']

  if settings.ALLOW_ELECTION_INFO_URL:
    RELEVANT_FIELDS += ['election_info_url']
  
  if request.method == "GET":
    values = {}
    for attr_name in RELEVANT_FIELDS:
      values[attr_name] = getattr(election, attr_name)
    election_form = forms.ElectionForm(values)
  else:
    election_form = forms.ElectionForm(request.POST)
    
    if election_form.is_valid():
      clean_data = election_form.cleaned_data
      for attr_name in RELEVANT_FIELDS:
        setattr(election, attr_name, clean_data[attr_name])

      election.save()
        
      return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
  
  return render_template(request, "election_edit", {'election_form' : election_form, 'election' : election, 'error': error})

@election_admin(frozen=False)
def one_election_schedule(request, election):
  return HttpResponse("foo")

@election_view()
@json
def one_election(request, election):
  if not election:
    raise Http404
  return election.toJSONDict(complete=True)

@election_view()
@json
def one_election_meta(request, election):
  if not election:
    raise Http404
  return election.metadata

@election_view()
def election_badge(request, election):
  election_url = get_election_url(election)
  params = {'election': election, 'election_url': election_url}
  for option_name in ['show_title', 'show_vote_link']:
    params[option_name] = (request.GET.get(option_name, '1') == '1')
  return render_template(request, "election_badge", params)

@election_view()
def one_election_view(request, election):
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  can_feature_p = security.user_can_feature_election(user, election)
  
  notregistered = False
  eligible_p = True
  
  election_url = get_election_url(election)
  election_badge_url = get_election_badge_url(election)
  status_update_message = None

  vote_url = "%s/booth/vote.html?%s" % (settings.SECURE_URL_HOST, urllib.urlencode({'election_url' : reverse(one_election, args=[election.uuid])}))

  test_cookie_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : vote_url}))
  
  if user:
    voter = Voter.get_by_election_and_user(election, user)
    
    if not voter:
      try:
        eligible_p = _check_eligibility(election, user)
      except AuthenticationExpired:
        return user_reauth(request, user)
      notregistered = True
  else:
    voter = get_voter(request, user, election)

  if voter:
    # cast any votes?
    votes = CastVote.get_by_voter(voter)
  else:
    votes = None

  # status update message?
  if election.openreg:
    if election.voting_has_started:
      status_update_message = u"Vote in %s" % election.name
    else:
      status_update_message = u"Register to vote in %s" % election.name

  # result!
  if election.result:
    status_update_message = u"Results are in for %s" % election.name
  
  # a URL for the social buttons
  socialbuttons_url = get_socialbuttons_url(election_url, status_update_message)

  trustees = Trustee.get_by_election(election)

  # should we show the result?
  show_result = election.result_released_at or (election.result and admin_p)

  return render_template(request, 'election_view',
                         {'election' : election, 'trustees': trustees, 'admin_p': admin_p, 'user': user,
                          'voter': voter, 'votes': votes, 'notregistered': notregistered, 'eligible_p': eligible_p,
                          'can_feature_p': can_feature_p, 'election_url' : election_url, 
                          'vote_url': vote_url, 'election_badge_url' : election_badge_url,
                          'show_result': show_result,
                          'test_cookie_url': test_cookie_url, 'socialbuttons_url' : socialbuttons_url})

def test_cookie(request):
  continue_url = request.GET['continue_url']
  request.session.set_test_cookie()
  next_url = "%s?%s" % (reverse(test_cookie_2), urllib.urlencode({'continue_url': continue_url}))
  return HttpResponseRedirect(settings.SECURE_URL_HOST + next_url)  

def test_cookie_2(request):
  continue_url = request.GET['continue_url']

  if not request.session.test_cookie_worked():
    return HttpResponseRedirect(settings.SECURE_URL_HOST + ("%s?%s" % (reverse(nocookies), urllib.urlencode({'continue_url': continue_url}))))

  request.session.delete_test_cookie()
  return HttpResponseRedirect(continue_url)  

def nocookies(request):
  retest_url = "%s?%s" % (reverse(test_cookie), urllib.urlencode({'continue_url' : request.GET['continue_url']}))
  return render_template(request, 'nocookies', {'retest_url': retest_url})

def socialbuttons(request):
  """
  just render the social buttons for sharing a URL
  expecting "url" and "text" in request.GET
  """
  return render_template(request, 'socialbuttons',
                         {'url': request.GET['url'], 'text':request.GET['text']})

##
## Trustees and Public Key
##
## As of July 2009, there are always trustees for a Helios election: one trustee is acceptable, for simple elections.
##
@election_view()
@json
def list_trustees(request, election):
  trustees = Trustee.get_by_election(election)
  return [t.toJSONDict(complete=True) for t in trustees]
  
@election_view()
def list_trustees_view(request, election):
  trustees = Trustee.get_by_election(election)
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)
  
  return render_template(request, 'list_trustees', {'election': election, 'trustees': trustees, 'admin_p':admin_p})
  
@election_admin(frozen=False)
def new_trustee(request, election):
  if request.method == "GET":
    return render_template(request, 'new_trustee', {'election' : election})
  else:
    # get the public key and the hash, and add it
    name = request.POST['name']
    email = request.POST['email']
    
    trustee = Trustee(uuid = str(uuid.uuid1()), election = election, name=name, email=email)
    trustee.save()
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(list_trustees_view, args=[election.uuid]))

@election_admin(frozen=False)
def new_trustee_helios(request, election):
  """
  Make Helios a trustee of the election
  """
  election.generate_trustee(ELGAMAL_PARAMS)
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(list_trustees_view, args=[election.uuid]))
  
@election_admin(frozen=False)
def delete_trustee(request, election):
  trustee = Trustee.get_by_election_and_uuid(election, request.GET['uuid'])
  trustee.delete()
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(list_trustees_view, args=[election.uuid]))
  
def trustee_login(request, election_short_name, trustee_email, trustee_secret):
  election = Election.get_by_short_name(election_short_name)
  if election:
    trustee = Trustee.get_by_election_and_email(election, trustee_email)
    
    if trustee:
      if trustee.secret == trustee_secret:
        set_logged_in_trustee(request, trustee)
        return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustee_home, args=[election.uuid, trustee.uuid]))
      else:
        # bad secret, we'll let that redirect to the front page
        pass
    else:
      # no such trustee
      raise Http404

  return HttpResponseRedirect(settings.SECURE_URL_HOST + "/")

@election_admin()
def trustee_send_url(request, election, trustee_uuid):
  trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)
  
  url = settings.SECURE_URL_HOST + reverse(trustee_login, args=[election.short_name, trustee.email, trustee.secret])
  
  body = """

You are a trustee for %s.

Your trustee dashboard is at

  %s
  
--
Helios  
""" % (election.name, url)

  helios_utils.send_email(settings.SERVER_EMAIL, ["%s <%s>" % (trustee.name, trustee.email)], 'your trustee homepage for %s' % election.name, body)

  logging.info("URL %s " % url)
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(list_trustees_view, args = [election.uuid]))

@trustee_check
def trustee_home(request, election, trustee):
  return render_template(request, 'trustee_home', {'election': election, 'trustee':trustee})
  
@trustee_check
def trustee_check_sk(request, election, trustee):
  return render_template(request, 'trustee_check_sk', {'election': election, 'trustee':trustee})
  
@trustee_check
def trustee_upload_pk(request, election, trustee):
  if request.method == "POST":
    # get the public key and the hash, and add it
    public_key_and_proof = utils.from_json(request.POST['public_key_json'])
    trustee.public_key = algs.EGPublicKey.fromJSONDict(public_key_and_proof['public_key'])
    trustee.pok = algs.DLogProof.fromJSONDict(public_key_and_proof['pok'])
    
    # verify the pok
    if not trustee.public_key.verify_sk_proof(trustee.pok, algs.DLog_challenge_generator):
      raise Exception("bad pok for this public key")
    
    trustee.public_key_hash = utils.hash_b64(utils.to_json(trustee.public_key.toJSONDict()))

    trustee.save()
    
    # send a note to admin
    try:
      election.admin.send_message("%s - trustee pk upload" % election.name, "trustee %s (%s) uploaded a pk." % (trustee.name, trustee.email))
    except:
      # oh well, no message sent
      pass
    
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(trustee_home, args=[election.uuid, trustee.uuid]))

##
## Ballot Management
##

@election_view()
@json
def get_randomness(request, election):
  """
  get some randomness to sprinkle into the sjcl entropy pool
  """
  return {
    # back to urandom, it's fine
    "randomness" : base64.b64encode(os.urandom(32))
    #"randomness" : base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
    }

@election_view(frozen=True)
@json
def encrypt_ballot(request, election):
  """
  perform the ballot encryption given answers_json, a JSON'ified list of list of answers
  (list of list because each question could have a list of answers if more than one.)
  """
  # FIXME: maybe make this just request.POST at some point?
  answers = utils.from_json(request.REQUEST['answers_json'])
  ev = homomorphic.EncryptedVote.fromElectionAndAnswers(election, answers)
  return ev.ld_object.includeRandomness().toJSONDict()
    
@election_view(frozen=True)
def post_audited_ballot(request, election):
  if request.method == "POST":
    raw_vote = request.POST['audited_ballot']
    encrypted_vote = electionalgs.EncryptedVote.fromJSONDict(utils.from_json(raw_vote))
    vote_hash = encrypted_vote.get_hash()
    audited_ballot = AuditedBallot(raw_vote = raw_vote, vote_hash = vote_hash, election = election)
    audited_ballot.save()
    
    return SUCCESS
    

# we don't require frozen election to allow for ballot preview
@election_view()
def one_election_cast(request, election):
  """
  on a GET, this is a cancellation, on a POST it's a cast
  """
  if request.method == "GET":
    return HttpResponseRedirect("%s%s" % (settings.SECURE_URL_HOST, reverse(one_election_view, args = [election.uuid])))
    
  user = get_user(request)    
  encrypted_vote = request.POST['encrypted_vote']

  save_in_session_across_logouts(request, 'encrypted_vote', encrypted_vote)

  return HttpResponseRedirect("%s%s" % (settings.SECURE_URL_HOST, reverse(one_election_cast_confirm, args=[election.uuid])))

@election_view(allow_logins=True)
def password_voter_login(request, election):
  """
  This is used to log in as a voter for a particular election
  """

  # the URL to send the user to after they've logged in
  return_url = request.REQUEST.get('return_url', reverse(one_election_cast_confirm, args=[election.uuid]))
  bad_voter_login = (request.GET.get('bad_voter_login', "0") == "1")

  if request.method == "GET":
    # if user logged in somehow in the interim, e.g. using the login link for administration,
    # then go!
    if user_can_see_election(request, election):
      return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args = [election.uuid]))

    password_login_form = forms.VoterPasswordForm()
    return render_template(request, 'password_voter_login',
                           {'election': election, 
                            'return_url' : return_url,
                            'password_login_form': password_login_form,
                            'bad_voter_login' : bad_voter_login})
  
  login_url = request.REQUEST.get('login_url', None)

  if not login_url:
    # login depending on whether this is a private election
    # cause if it's private the login is happening on the front page
    if election.private_p:
      login_url = reverse(password_voter_login, args=[election.uuid])
    else:
      login_url = reverse(one_election_cast_confirm, args=[election.uuid])

  password_login_form = forms.VoterPasswordForm(request.POST)

  if password_login_form.is_valid():
    try:
      voter = election.voter_set.get(voter_login_id = password_login_form.cleaned_data['voter_id'].strip(),
                                     voter_password = password_login_form.cleaned_data['password'].strip())

      request.session['CURRENT_VOTER'] = voter

      # if we're asked to cast, let's do it
      if request.POST.get('cast_ballot') == "1":
        return one_election_cast_confirm(request, election.uuid)
      
    except Voter.DoesNotExist:
      redirect_url = login_url + "?" + urllib.urlencode({
          'bad_voter_login' : '1',
          'return_url' : return_url
          })

      return HttpResponseRedirect(settings.SECURE_URL_HOST + redirect_url)
  
  return HttpResponseRedirect(settings.SECURE_URL_HOST + return_url)

@election_view()
def one_election_cast_confirm(request, election):
  user = get_user(request)    

  # if no encrypted vote, the user is reloading this page or otherwise getting here in a bad way
  if not request.session.has_key('encrypted_vote'):
    return HttpResponseRedirect(settings.URL_HOST)

  # election not frozen or started
  if not election.voting_has_started():
    return render_template(request, 'election_not_started', {'election': election})

  voter = get_voter(request, user, election)

  # auto-register this person if the election is openreg
  if user and not voter and election.openreg:
    voter = _register_voter(election, user)
    
  # tallied election, no vote casting
  if election.encrypted_tally or election.result:
    return render_template(request, 'election_tallied', {'election': election})
    
  encrypted_vote = request.session['encrypted_vote']
  vote_fingerprint = cryptoutils.hash_b64(encrypted_vote)

  # if this user is a voter, prepare some stuff
  if voter:
    vote = datatypes.LDObject.fromDict(utils.from_json(encrypted_vote), type_hint='legacy/EncryptedVote').wrapped_obj

    # prepare the vote to cast
    cast_vote_params = {
      'vote' : vote,
      'voter' : voter,
      'vote_hash': vote_fingerprint,
      'cast_at': datetime.datetime.utcnow()
    }

    cast_vote = CastVote(**cast_vote_params)
  else:
    cast_vote = None
    
  if request.method == "GET":
    if voter:
      past_votes = CastVote.get_by_voter(voter)
      if len(past_votes) == 0:
        past_votes = None
    else:
      past_votes = None

    if cast_vote:
      # check for issues
      issues = cast_vote.issues(election)
    else:
      issues = None

    bad_voter_login = (request.GET.get('bad_voter_login', "0") == "1")

    # status update this vote
    if voter and voter.user.can_update_status():
      status_update_label = voter.user.update_status_template() % "your smart ballot tracker"
      status_update_message = "I voted in %s - my smart tracker is %s.. #heliosvoting" % (get_election_url(election),cast_vote.vote_hash[:10])
    else:
      status_update_label = None
      status_update_message = None

    # do we need to constrain the auth_systems?
    if election.eligibility:
      auth_systems = [e['auth_system'] for e in election.eligibility]
    else:
      auth_systems = None

    password_only = False

    if auth_systems == None or 'password' in auth_systems:
      show_password = True
      password_login_form = forms.VoterPasswordForm()

      if auth_systems == ['password']:
        password_only = True
    else:
      show_password = False
      password_login_form = None

    return_url = reverse(one_election_cast_confirm, args=[election.uuid])
    login_box = auth_views.login_box_raw(request, return_url=return_url, auth_systems = auth_systems)

    return render_template(request, 'election_cast_confirm', {
        'login_box': login_box, 'election' : election, 'vote_fingerprint': vote_fingerprint,
        'past_votes': past_votes, 'issues': issues, 'voter' : voter,
        'return_url': return_url,
        'status_update_label': status_update_label, 'status_update_message': status_update_message,
        'show_password': show_password, 'password_only': password_only, 'password_login_form': password_login_form,
        'bad_voter_login': bad_voter_login})
      
  if request.method == "POST":
    check_csrf(request)
    
    # voting has not started or has ended
    if (not election.voting_has_started()) or election.voting_has_stopped():
      return HttpResponseRedirect(settings.URL_HOST)
            
    # if user is not logged in
    # bring back to the confirmation page to let him know
    if not voter:
      return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_cast_confirm, args=[election.uuid]))
    
    # don't store the vote in the voter's data structure until verification
    cast_vote.save()

    # status update?
    if request.POST.get('status_update', False):
      status_update_message = request.POST.get('status_update_message')
    else:
      status_update_message = None

    # launch the verification task
    tasks.cast_vote_verify_and_store.delay(
      cast_vote_id = cast_vote.id,
      status_update_message = status_update_message)
    
    # remove the vote from the store
    del request.session['encrypted_vote']
    
    return HttpResponseRedirect("%s%s" % (settings.URL_HOST, reverse(one_election_cast_done, args=[election.uuid])))
  
@election_view()
def one_election_cast_done(request, election):
  """
  This view needs to be loaded because of the IFRAME, but then this causes 
  problems if someone clicks "reload". So we need a strategy.
  We store the ballot hash in the session
  """
  user = get_user(request)
  voter = get_voter(request, user, election)

  if voter:
    votes = CastVote.get_by_voter(voter)
    vote_hash = votes[0].vote_hash
    cv_url = get_castvote_url(votes[0])

    # only log out if the setting says so *and* we're dealing
    # with a site-wide voter. Definitely remove current_voter
    if voter.user == user:
      logout = settings.LOGOUT_ON_CONFIRMATION
    else:
      logout = False
      del request.session['CURRENT_VOTER']

    save_in_session_across_logouts(request, 'last_vote_hash', vote_hash)
    save_in_session_across_logouts(request, 'last_vote_cv_url', cv_url)
  else:
    vote_hash = request.session['last_vote_hash']
    cv_url = request.session['last_vote_cv_url']
    logout = False
  
  # local logout ensures that there's no more
  # user locally
  # WHY DO WE COMMENT THIS OUT? because we want to force a full logout via the iframe, including
  # from remote systems, just in case, i.e. CAS
  # if logout:
  #   auth_views.do_local_logout(request)
  
  # tweet/fb your vote
  socialbuttons_url = get_socialbuttons_url(cv_url, 'I cast a vote in %s' % election.name) 
  
  # remote logout is happening asynchronously in an iframe to be modular given the logout mechanism
  # include_user is set to False if logout is happening
  return render_template(request, 'cast_done', {'election': election,
                                                'vote_hash': vote_hash, 'logout': logout,
                                                'socialbuttons_url': socialbuttons_url},
                         include_user=(not logout))

@election_view()
@json
def one_election_result(request, election):
  if not election.result_released_at:
    raise PermissionDenied
  return election.result

@election_view()
@json
def one_election_result_proof(request, election):
  if not election.result_released_at:
    raise PermissionDenied
  return election.result_proof
  
@election_view(frozen=True)
def one_election_bboard(request, election):
  """
  UI to show election bboard
  """
  after = request.GET.get('after', None)
  offset= int(request.GET.get('offset', 0))
  limit = int(request.GET.get('limit', 50))
  
  order_by = 'voter_id'
  
  # unless it's by alias, in which case we better go by UUID
  if election.use_voter_aliases:
    order_by = 'alias'

  # if there's a specific voter
  if request.GET.has_key('q'):
    # FIXME: figure out the voter by voter_id
    voters = []
  else:
    # load a bunch of voters
    voters = Voter.get_by_election(election, after=after, limit=limit+1, order_by=order_by)
    
  more_p = len(voters) > limit
  if more_p:
    voters = voters[0:limit]
    next_after = getattr(voters[limit-1], order_by)
  else:
    next_after = None
    
  return render_template(request, 'election_bboard', {'election': election, 'voters': voters, 'next_after': next_after,
                'offset': offset, 'limit': limit, 'offset_plus_one': offset+1, 'offset_plus_limit': offset+limit,
                'voter_id': request.GET.get('voter_id', '')})

@election_view(frozen=True)
def one_election_audited_ballots(request, election):
  """
  UI to show election audited ballots
  """
  
  if request.GET.has_key('vote_hash'):
    b = AuditedBallot.get(election, request.GET['vote_hash'])
    return HttpResponse(b.raw_vote, mimetype="text/plain")
    
  after = request.GET.get('after', None)
  offset= int(request.GET.get('offset', 0))
  limit = int(request.GET.get('limit', 50))
  
  audited_ballots = AuditedBallot.get_by_election(election, after=after, limit=limit+1)
    
  more_p = len(audited_ballots) > limit
  if more_p:
    audited_ballots = audited_ballots[0:limit]
    next_after = audited_ballots[limit-1].vote_hash
  else:
    next_after = None
    
  return render_template(request, 'election_audited_ballots', {'election': election, 'audited_ballots': audited_ballots, 'next_after': next_after,
                'offset': offset, 'limit': limit, 'offset_plus_one': offset+1, 'offset_plus_limit': offset+limit})

@election_admin()
def voter_delete(request, election, voter_uuid):
  """
  Two conditions under which a voter can be deleted:
  - election is not frozen or
  - election is open reg
  """
  ## FOR NOW we allow this to see if we can redefine the meaning of "closed reg" to be more flexible
  # if election is frozen and has closed registration
  #if election.frozen_at and (not election.openreg):
  #  raise PermissionDenied()

  if election.encrypted_tally:
    raise PermissionDenied()

  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if voter:
    voter.delete()

  if election.frozen_at:
    # log it
    election.append_log("Voter %s/%s removed after election frozen" % (voter.voter_type,voter.voter_id))
    
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))

@election_admin(frozen=False)
def one_election_set_reg(request, election):
  """
  Set whether this is open registration or not
  """
  # only allow this for public elections
  if not election.private_p:
    open_p = bool(int(request.GET['open_p']))
    election.openreg = open_p
    election.save()
  
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))

@election_admin()
def one_election_set_featured(request, election):
  """
  Set whether this is a featured election or not
  """

  user = get_user(request)
  if not security.user_can_feature_election(user, election):
    raise PermissionDenied()

  featured_p = bool(int(request.GET['featured_p']))
  election.featured_p = featured_p
  election.save()
  
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

@election_admin()
def one_election_archive(request, election):
  
  archive_p = request.GET.get('archive_p', True)
  
  if bool(int(archive_p)):
    election.archived_at = datetime.datetime.utcnow()
  else:
    election.archived_at = None
    
  election.save()

  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

# changed from admin to view because 
# anyone can see the questions, the administration aspect is now
# built into the page
@election_view()
def one_election_questions(request, election):
  questions_json = utils.to_json(election.questions)
  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  return render_template(request, 'election_questions', {'election': election, 'questions_json' : questions_json, 'admin_p': admin_p})

def _check_eligibility(election, user):
  # prevent password-users from signing up willy-nilly for other elections, doesn't make sense
  if user.user_type == 'password':
    return False

  return election.user_eligible_p(user)

def _register_voter(election, user):
  if not _check_eligibility(election, user):
    return None
    
  return Voter.register_user_in_election(user, election)
    
@election_view()
def one_election_register(request, election):
  if not election.openreg:
    return HttpResponseForbidden('registration is closed for this election')
    
  check_csrf(request)
    
  user = get_user(request)
  voter = Voter.get_by_election_and_user(election, user)
  
  if not voter:
    voter = _register_voter(election, user)
    
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

@election_admin(frozen=False)
def one_election_save_questions(request, election):
  check_csrf(request)
  
  election.questions = utils.from_json(request.POST['questions_json'])
  election.save()

  # always a machine API
  return SUCCESS

@transaction.commit_on_success
@election_admin(frozen=False)
def one_election_freeze(request, election):
  # figure out the number of questions and trustees
  issues = election.issues_before_freeze

  if request.method == "GET":
    return render_template(request, 'election_freeze', {'election': election, 'issues' : issues, 'issues_p' : len(issues) > 0})
  else:
    check_csrf(request)
    
    election.freeze()

    if get_user(request):
      return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
    else:
      return SUCCESS    

def _check_election_tally_type(election):
  for q in election.questions:
    if q['tally_type'] != "homomorphic":
      return False
  return True

@election_admin(frozen=True)
def one_election_compute_tally(request, election):
  """
  tallying is done all at a time now
  """
  if not _check_election_tally_type(election):
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view,args=[election.election_id]))

  if request.method == "GET":
    return render_template(request, 'election_compute_tally', {'election': election})
  
  check_csrf(request)

  if not election.voting_ended_at:
    election.voting_ended_at = datetime.datetime.utcnow()

  election.tallying_started_at = datetime.datetime.utcnow()
  election.save()

  tasks.election_compute_tally.delay(election_id = election.id)

  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view,args=[election.uuid]))

@trustee_check
def trustee_decrypt_and_prove(request, election, trustee):
  if not _check_election_tally_type(election) or election.encrypted_tally == None:
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view,args=[election.uuid]))
    
  return render_template(request, 'trustee_decrypt_and_prove', {'election': election, 'trustee': trustee})
  
@election_view(frozen=True)
def trustee_upload_decryption(request, election, trustee_uuid):
  if not _check_election_tally_type(election) or election.encrypted_tally == None:
    return FAILURE

  trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)

  factors_and_proofs = utils.from_json(request.POST['factors_and_proofs'])

  # verify the decryption factors
  trustee.decryption_factors = [[datatypes.LDObject.fromDict(factor, type_hint='core/BigInteger').wrapped_obj for factor in one_q_factors] for one_q_factors in factors_and_proofs['decryption_factors']]

  # each proof needs to be deserialized
  trustee.decryption_proofs = [[datatypes.LDObject.fromDict(proof, type_hint='legacy/EGZKProof').wrapped_obj for proof in one_q_proofs] for one_q_proofs in factors_and_proofs['decryption_proofs']]

  if trustee.verify_decryption_proofs():
    trustee.save()
    
    try:
      # send a note to admin
      election.admin.send_message("%s - trustee partial decryption" % election.name, "trustee %s (%s) did their partial decryption." % (trustee.name, trustee.email))
    except:
      # ah well
      pass
    
    return SUCCESS
  else:
    return FAILURE

@election_admin(frozen=True)
def release_result(request, election):
  """
  result is computed and now it's time to release the result
  """
  election_url = get_election_url(election)

  if request.method == "POST":
    check_csrf(request)

    election.release_result()
    election.save()

    return HttpResponseRedirect("%s" % (settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid])))

  # if just viewing the form or the form is not valid
  return render_template(request, 'release_result', {'election': election})

@election_admin(frozen=True)
def combine_decryptions(request, election):
  """
  combine trustee decryptions
  """

  election_url = get_election_url(election)

  if request.method == "POST":
    check_csrf(request)

    election.combine_decryptions()
    election.save()

    return HttpResponseRedirect("%s" % (settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid])))

  # if just viewing the form or the form is not valid
  return render_template(request, 'combine_decryptions', {'election': election})

@election_admin(frozen=True)
def one_election_set_result_and_proof(request, election):
  if election.tally_type != "homomorphic" or election.encrypted_tally == None:
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view,args=[election.election_id]))

  # FIXME: check csrf
  
  election.result = utils.from_json(request.POST['result'])
  election.result_proof = utils.from_json(request.POST['result_proof'])
  election.save()

  if get_user(request):
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
  else:
    return SUCCESS
  
  
@election_view()
def voters_list_pretty(request, election):
  """
  Show the list of voters
  now using Django pagination
  """

  # for django pagination support
  page = int(request.GET.get('page', 1))
  limit = int(request.GET.get('limit', 50))
  q = request.GET.get('q','')
  
  order_by = 'user__user_id'

  # unless it's by alias, in which case we better go by UUID
  if election.use_voter_aliases:
    order_by = 'alias'

  user = get_user(request)
  admin_p = security.user_can_admin_election(user, election)

  categories = None
  eligibility_category_id = None

  try:
    if admin_p and can_list_categories(user.user_type):
      categories = AUTH_SYSTEMS[user.user_type].list_categories(user)
      eligibility_category_id = election.eligibility_category_id(user.user_type)
  except AuthenticationExpired:
    return user_reauth(request, user)
  
  # files being processed
  voter_files = election.voterfile_set.all()

  # load a bunch of voters
  # voters = Voter.get_by_election(election, order_by=order_by)
  voters = Voter.objects.filter(election = election).order_by(order_by).defer('vote')

  if q != '':
    if election.use_voter_aliases:
      voters = voters.filter(alias__icontains = q)
    else:
      voters = voters.filter(voter_name__icontains = q)

  voter_paginator = Paginator(voters, limit)
  voters_page = voter_paginator.page(page)

  total_voters = voter_paginator.count
    
  return render_template(request, 'voters_list', 
                         {'election': election, 'voters_page': voters_page,
                          'voters': voters_page.object_list, 'admin_p': admin_p, 
                          'email_voters': helios.VOTERS_EMAIL,
                          'limit': limit, 'total_voters': total_voters,
                          'upload_p': helios.VOTERS_UPLOAD, 'q' : q,
                          'voter_files': voter_files,
                          'categories': categories,
                          'eligibility_category_id' : eligibility_category_id})

@election_admin()
def voters_eligibility(request, election):
  """
  set eligibility for voters
  """
  user = get_user(request)

  if request.method == "GET":
    # this shouldn't happen, only POSTs
    return HttpResponseRedirect("/")

  # for now, private elections cannot change eligibility
  if election.private_p:
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))

  # eligibility
  eligibility = request.POST['eligibility']

  if eligibility in ['openreg', 'limitedreg']:
    election.openreg= True

  if eligibility == 'closedreg':
    election.openreg= False

  if eligibility == 'limitedreg':
    # now process the constraint
    category_id = request.POST['category_id']

    constraint = AUTH_SYSTEMS[user.user_type].generate_constraint(category_id, user)
    election.eligibility = [{'auth_system': user.user_type, 'constraint': [constraint]}]
  else:
    election.eligibility = None

  election.save()
  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))
  
@election_admin()
def voters_upload(request, election):
  """
  Upload a CSV of password-based voters with
  voter_id, email, name
  
  name and email are needed only if voter_type is static
  """

  ## TRYING this: allowing voters upload by admin when election is frozen
  #if election.frozen_at and not election.openreg:
  #  raise PermissionDenied()

  if request.method == "GET":
    return render_template(request, 'voters_upload', {'election': election, 'error': request.GET.get('e',None)})
    
  if request.method == "POST":
    if bool(request.POST.get('confirm_p', 0)):
      # launch the background task to parse that file
      tasks.voter_file_process.delay(voter_file_id = request.session['voter_file_id'])
      del request.session['voter_file_id']

      return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(voters_list_pretty, args=[election.uuid]))
    else:
      # we need to confirm
      if request.FILES.has_key('voters_file'):
        voters_file = request.FILES['voters_file']
        voter_file_obj = election.add_voters_file(voters_file)

        request.session['voter_file_id'] = voter_file_obj.id

        problems = []

        # import the first few lines to check
        try:
          voters = [v for v in voter_file_obj.itervoters()][:5]
        except:
          voters = []
          problems.append("your CSV file could not be processed. Please check that it is a proper CSV file.")

        # check if voter emails look like emails
        if False in [validate_email(v['email']) for v in voters]:
          problems.append("those don't look like correct email addresses. Are you sure you uploaded a file with email address as second field?")

        return render_template(request, 'voters_upload_confirm', {'election': election, 'voters': voters, 'problems': problems})
      else:
        return HttpResponseRedirect("%s?%s" % (settings.SECURE_URL_HOST + reverse(voters_upload, args=[election.uuid]), urllib.urlencode({'e':'no voter file specified, try again'})))

@election_admin()
def voters_upload_cancel(request, election):
  """
  cancel upload of CSV file
  """
  voter_file_id = request.session.get('voter_file_id', None)
  if voter_file_id:
    vf = VoterFile.objects.get(id = voter_file_id)
    vf.delete()
  del request.session['voter_file_id']

  return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))

@election_admin(frozen=True)
def voters_email(request, election):
  if not helios.VOTERS_EMAIL:
    return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
  TEMPLATES = [
    ('vote', 'Time to Vote'),
    ('simple', 'Simple'),
    ('info', 'Additional Info'),
    ('result', 'Election Result')
    ]

  template = request.REQUEST.get('template', 'vote')
  if not template in [t[0] for t in TEMPLATES]:
    raise Exception("bad template")

  voter_id = request.REQUEST.get('voter_id', None)

  if voter_id:
    voter = Voter.get_by_election_and_voter_id(election, voter_id)
  else:
    voter = None
  
  election_url = get_election_url(election)
  election_vote_url = get_election_govote_url(election)

  default_subject = render_template_raw(None, 'email/%s_subject.txt' % template, {
      'custom_subject': "&lt;SUBJECT&gt;"
})
  default_body = render_template_raw(None, 'email/%s_body.txt' % template, {
      'election' : election,
      'election_url' : election_url,
      'election_vote_url' : election_vote_url,
      'custom_subject' : default_subject,
      'custom_message': '&lt;BODY&gt;',
      'voter': {'vote_hash' : '<SMART_TRACKER>',
                'name': '<VOTER_NAME>',
                'voter_login_id': '<VOTER_LOGIN_ID>',
                'voter_password': '<VOTER_PASSWORD>',
                'voter_type' : election.voter_set.all()[0].voter_type,
                'election' : election}
      })

  if request.method == "GET":
    email_form = forms.EmailVotersForm()
    if voter:
      email_form.fields['send_to'].widget = email_form.fields['send_to'].hidden_widget()
  else:
    email_form = forms.EmailVotersForm(request.POST)
    
    if email_form.is_valid():
      
      # the client knows to submit only once with a specific voter_id
      subject_template = 'email/%s_subject.txt' % template
      body_template = 'email/%s_body.txt' % template

      extra_vars = {
        'custom_subject' : email_form.cleaned_data['subject'],
        'custom_message' : email_form.cleaned_data['body'],
        'election_vote_url' : election_vote_url,
        'election_url' : election_url,
        'election' : election
        }
        
      voter_constraints_include = None
      voter_constraints_exclude = None

      if voter:
        tasks.single_voter_email.delay(voter_uuid = voter.uuid, subject_template = subject_template, body_template = body_template, extra_vars = extra_vars)
      else:
        # exclude those who have not voted
        if email_form.cleaned_data['send_to'] == 'voted':
          voter_constraints_exclude = {'vote_hash' : None}
          
        # include only those who have not voted
        if email_form.cleaned_data['send_to'] == 'not-voted':
          voter_constraints_include = {'vote_hash': None}

        tasks.voters_email.delay(election_id = election.id, subject_template = subject_template, body_template = body_template, extra_vars = extra_vars, voter_constraints_include = voter_constraints_include, voter_constraints_exclude = voter_constraints_exclude)

      # this batch process is all async, so we can return a nice note
      return HttpResponseRedirect(settings.SECURE_URL_HOST + reverse(one_election_view, args=[election.uuid]))
    
  return render_template(request, "voters_email", {
      'email_form': email_form, 'election': election,
      'voter': voter,
      'default_subject': default_subject,
      'default_body' : default_body,
      'template' : template,
      'templates' : TEMPLATES})    

# Individual Voters
@election_view()
@json
def voter_list(request, election):
  # normalize limit
  limit = int(request.GET.get('limit', 500))
  if limit > 500: limit = 500
    
  voters = Voter.get_by_election(election, order_by='uuid', after=request.GET.get('after',None), limit= limit)
  return [v.ld_object.toDict() for v in voters]
  
@election_view()
@json
def one_voter(request, election, voter_uuid):
  """
  View a single voter's info as JSON.
  """
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  if not voter:
    raise Http404
  return voter.toJSONDict()  

@election_view()
@json
def voter_votes(request, election, voter_uuid):
  """
  all cast votes by a voter
  """
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  votes = CastVote.get_by_voter(voter)
  return [v.toJSONDict()  for v in votes]

@election_view()
@json
def voter_last_vote(request, election, voter_uuid):
  """
  all cast votes by a voter
  """
  voter = Voter.get_by_election_and_uuid(election, voter_uuid)
  return voter.last_cast_vote().toJSONDict()

##
## cast ballots
##

@election_view()
@json
def ballot_list(request, election):
  """
  this will order the ballots from most recent to oldest.
  and optionally take a after parameter.
  """
  limit = after = None
  if request.GET.has_key('limit'):
    limit = int(request.GET['limit'])
  if request.GET.has_key('after'):
    after = datetime.datetime.strptime(request.GET['after'], '%Y-%m-%d %H:%M:%S')
    
  voters = Voter.get_by_election(election, cast=True, order_by='cast_at', limit=limit, after=after)

  # we explicitly cast this to a short cast vote
  return [v.last_cast_vote().ld_object.short.toDict(complete=True) for v in voters]





########NEW FILE########
__FILENAME__ = view_utils
"""
Utilities for all views

Ben Adida (12-30-2008)
"""

from django.template import Context, Template, loader
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response

import utils

from helios import datatypes

# nicely update the wrapper function
from functools import update_wrapper

from helios_auth.security import get_user

import helios

from django.conf import settings

##
## BASICS
##

SUCCESS = HttpResponse("SUCCESS")

# FIXME: error code
FAILURE = HttpResponse("FAILURE")

##
## template abstraction
##
def prepare_vars(request, vars):
  vars_with_user = vars.copy()
  vars_with_user['user'] = get_user(request)
  
  # csrf protection
  if request.session.has_key('csrf_token'):
    vars_with_user['csrf_token'] = request.session['csrf_token']
    
  vars_with_user['utils'] = utils
  vars_with_user['settings'] = settings
  vars_with_user['HELIOS_STATIC'] = '/static/helios/helios'
  vars_with_user['TEMPLATE_BASE'] = helios.TEMPLATE_BASE
  vars_with_user['CURRENT_URL'] = request.path
  vars_with_user['SECURE_URL_HOST'] = settings.SECURE_URL_HOST

  return vars_with_user

def render_template(request, template_name, vars = {}, include_user=True):
  t = loader.get_template(template_name + '.html')
  
  vars_with_user = prepare_vars(request, vars)
  
  if not include_user:
    del vars_with_user['user']
  
  return render_to_response('helios/templates/%s.html' % template_name, vars_with_user)
  
def render_template_raw(request, template_name, vars={}):
  t = loader.get_template(template_name)
  
  # if there's a request, prep the vars, otherwise can't do it.
  if request:
    full_vars = prepare_vars(request, vars)
  else:
    full_vars = vars

  c = Context(full_vars)  
  return t.render(c)


def render_json(json_txt):
  return HttpResponse(json_txt, "application/json")

# decorator
def json(func):
    """
    A decorator that serializes the output to JSON before returning to the
    web client.
    """
    def convert_to_json(self, *args, **kwargs):
      return_val = func(self, *args, **kwargs)
      try:
        return render_json(utils.to_json(return_val))
      except Exception, e:
        import logging
        logging.error("problem with serialization: " + str(return_val) + " / " + str(e))
        raise e

    return update_wrapper(convert_to_json,func)
    

########NEW FILE########
__FILENAME__ = widgets
"""
Widget for datetime split, with calendar for date, and drop-downs for times.
"""

from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.forms.widgets import Select, MultiWidget, DateInput, TextInput, Widget
from django.forms.extras.widgets import SelectDateWidget
from time import strftime

import re
from django.utils.safestring import mark_safe

__all__ = ('SelectTimeWidget', 'SplitSelectDateTimeWidget')

# Attempt to match many time formats:
# Example: "12:34:56 P.M."  matches:
# ('12', '34', ':56', '56', 'P.M.', 'P', '.', 'M', '.')
# ('12', '34', ':56', '56', 'P.M.')
# Note that the colon ":" before seconds is optional, but only if seconds are omitted
time_pattern = r'(\d\d?):(\d\d)(:(\d\d))? *([aApP]\.?[mM]\.?)?$'

RE_TIME = re.compile(time_pattern)
# The following are just more readable ways to access re.matched groups:
HOURS = 0
MINUTES = 1
SECONDS = 3
MERIDIEM = 4

class SelectTimeWidget(Widget):
    """
    A Widget that splits time input into <select> elements.
    Allows form to show as 24hr: <hour>:<minute>:<second>, (default)
    or as 12hr: <hour>:<minute>:<second> <am|pm> 
    
    Also allows user-defined increments for minutes/seconds
    """
    hour_field = '%s_hour'
    minute_field = '%s_minute'
    meridiem_field = '%s_meridiem'
    twelve_hr = False # Default to 24hr.
    
    def __init__(self, attrs=None, hour_step=None, minute_step=None, twelve_hr=False):
        """
        hour_step, minute_step, second_step are optional step values for
        for the range of values for the associated select element
        twelve_hr: If True, forces the output to be in 12-hr format (rather than 24-hr)
        """
        self.attrs = attrs or {}
        
        if twelve_hr:
            self.twelve_hr = True # Do 12hr (rather than 24hr)
            self.meridiem_val = 'a.m.' # Default to Morning (A.M.)
        
        if hour_step and twelve_hr:
            self.hours = range(1,13,hour_step) 
        elif hour_step: # 24hr, with stepping.
            self.hours = range(0,24,hour_step)
        elif twelve_hr: # 12hr, no stepping
            self.hours = range(1,13)
        else: # 24hr, no stepping
            self.hours = range(0,24) 

        if minute_step:
            self.minutes = range(0,60,minute_step)
        else:
            self.minutes = range(0,60)

    def render(self, name, value, attrs=None):
        try: # try to get time values from a datetime.time object (value)
            hour_val, minute_val = value.hour, value.minute
            if self.twelve_hr:
                if hour_val >= 12:
                    self.meridiem_val = 'p.m.'
                else:
                    self.meridiem_val = 'a.m.'
        except AttributeError:
            hour_val = minute_val = 0
            if isinstance(value, basestring):
                match = RE_TIME.match(value)
                if match:
                    time_groups = match.groups();
                    hour_val = int(time_groups[HOURS]) % 24 # force to range(0-24)
                    minute_val = int(time_groups[MINUTES]) 
                    
                    # check to see if meridiem was passed in
                    if time_groups[MERIDIEM] is not None:
                        self.meridiem_val = time_groups[MERIDIEM]
                    else: # otherwise, set the meridiem based on the time
                        if self.twelve_hr:
                            if hour_val >= 12:
                                self.meridiem_val = 'p.m.'
                            else:
                                self.meridiem_val = 'a.m.'
                        else:
                            self.meridiem_val = None
                    

        # If we're doing a 12-hr clock, there will be a meridiem value, so make sure the
        # hours get printed correctly
        if self.twelve_hr and self.meridiem_val:
            if self.meridiem_val.lower().startswith('p') and hour_val > 12 and hour_val < 24:
                hour_val = hour_val % 12
        elif hour_val == 0:
            hour_val = 12
            
        output = []
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name

        # For times to get displayed correctly, the values MUST be converted to unicode
        # When Select builds a list of options, it checks against Unicode values
        hour_val = u"%.2d" % hour_val
        minute_val = u"%.2d" % minute_val

        hour_choices = [("%.2d"%i, "%.2d"%i) for i in self.hours]
        local_attrs = self.build_attrs(id=self.hour_field % id_)
        select_html = Select(choices=hour_choices).render(self.hour_field % name, hour_val, local_attrs)
        output.append(select_html)

        minute_choices = [("%.2d"%i, "%.2d"%i) for i in self.minutes]
        local_attrs['id'] = self.minute_field % id_
        select_html = Select(choices=minute_choices).render(self.minute_field % name, minute_val, local_attrs)
        output.append(select_html)

        if self.twelve_hr:
            #  If we were given an initial value, make sure the correct meridiem gets selected.
            if self.meridiem_val is not None and  self.meridiem_val.startswith('p'):
                    meridiem_choices = [('p.m.','p.m.'), ('a.m.','a.m.')]
            else:
                meridiem_choices = [('a.m.','a.m.'), ('p.m.','p.m.')]

            local_attrs['id'] = local_attrs['id'] = self.meridiem_field % id_
            select_html = Select(choices=meridiem_choices).render(self.meridiem_field % name, self.meridiem_val, local_attrs)
            output.append(select_html)

        return mark_safe(u'\n'.join(output))

    def id_for_label(self, id_):
        return '%s_hour' % id_
    id_for_label = classmethod(id_for_label)

    def value_from_datadict(self, data, files, name):
        # if there's not h:m:s data, assume zero:
        h = data.get(self.hour_field % name, 0) # hour
        m = data.get(self.minute_field % name, 0) # minute 

        meridiem = data.get(self.meridiem_field % name, None)

        #NOTE: if meridiem is None, assume 24-hr
        if meridiem is not None:
            if meridiem.lower().startswith('p') and int(h) != 12:
                h = (int(h)+12)%24 
            elif meridiem.lower().startswith('a') and int(h) == 12:
                h = 0
        
        if (int(h) == 0 or h) and m and s:
            return '%s:%s:%s' % (h, m, s)

        return data.get(name, None)

class SplitSelectDateTimeWidget(MultiWidget):
    """
    MultiWidget = A widget that is composed of multiple widgets.

    This class combines SelectTimeWidget and SelectDateWidget so we have something 
    like SpliteDateTimeWidget (in django.forms.widgets), but with Select elements.
    """
    def __init__(self, attrs=None, hour_step=None, minute_step=None, twelve_hr=None, years=None):
        """ pass all these parameters to their respective widget constructors..."""
        widgets = (SelectDateWidget(attrs=attrs, years=years), SelectTimeWidget(attrs=attrs, hour_step=hour_step, minute_step=minute_step, twelve_hr=twelve_hr))
        super(SplitSelectDateTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]

    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), it inserts an HTML
        linebreak between them.
        
        Returns a Unicode string representing the HTML for the whole lot.
        """
        rendered_widgets.insert(-1, '<br/>')
        return u''.join(rendered_widgets)


########NEW FILE########
__FILENAME__ = homomorphic
"""
homomorphic workflow and algorithms for Helios

Ben Adida
2008-08-30
reworked 2011-01-09
"""

from helios.crypto import algs, utils
import logging
import uuid
import datetime
from helios import models
from . import WorkflowObject

class EncryptedAnswer(WorkflowObject):
  """
  An encrypted answer to a single election question
  """

  def __init__(self, choices=None, individual_proofs=None, overall_proof=None, randomness=None, answer=None):
    self.choices = choices
    self.individual_proofs = individual_proofs
    self.overall_proof = overall_proof
    self.randomness = randomness
    self.answer = answer
    
  @classmethod
  def generate_plaintexts(cls, pk, min=0, max=1):
    plaintexts = []
    running_product = 1
    
    # run the product up to the min
    for i in range(max+1):
      # if we're in the range, add it to the array
      if i >= min:
        plaintexts.append(algs.EGPlaintext(running_product, pk))
        
      # next value in running product
      running_product = (running_product * pk.g) % pk.p
      
    return plaintexts

  def verify_plaintexts_and_randomness(self, pk):
    """
    this applies only if the explicit answers and randomness factors are given
    we do not verify the proofs here, that is the verify() method
    """
    if not hasattr(self, 'answer'):
      return False
    
    for choice_num in range(len(self.choices)):
      choice = self.choices[choice_num]
      choice.pk = pk
      
      # redo the encryption
      # WORK HERE (paste from below encryption)
    
    return False
    
  def verify(self, pk, min=0, max=1):
    possible_plaintexts = self.generate_plaintexts(pk)
    homomorphic_sum = 0
      
    for choice_num in range(len(self.choices)):
      choice = self.choices[choice_num]
      choice.pk = pk
      individual_proof = self.individual_proofs[choice_num]
      
      # verify the proof on the encryption of that choice
      if not choice.verify_disjunctive_encryption_proof(possible_plaintexts, individual_proof, algs.EG_disjunctive_challenge_generator):
        return False

      # compute homomorphic sum if needed
      if max != None:
        homomorphic_sum = choice * homomorphic_sum
    
    if max != None:
      # determine possible plaintexts for the sum
      sum_possible_plaintexts = self.generate_plaintexts(pk, min=min, max=max)

      # verify the sum
      return homomorphic_sum.verify_disjunctive_encryption_proof(sum_possible_plaintexts, self.overall_proof, algs.EG_disjunctive_challenge_generator)
    else:
      # approval voting, no need for overall proof verification
      return True
        
  @classmethod
  def fromElectionAndAnswer(cls, election, question_num, answer_indexes):
    """
    Given an election, a question number, and a list of answers to that question
    in the form of an array of 0-based indexes into the answer array,
    produce an EncryptedAnswer that works.
    """
    question = election.questions[question_num]
    answers = question['answers']
    pk = election.public_key
    
    # initialize choices, individual proofs, randomness and overall proof
    choices = [None for a in range(len(answers))]
    individual_proofs = [None for a in range(len(answers))]
    overall_proof = None
    randomness = [None for a in range(len(answers))]
    
    # possible plaintexts [0, 1]
    plaintexts = cls.generate_plaintexts(pk)
    
    # keep track of number of options selected.
    num_selected_answers = 0;
    
    # homomorphic sum of all
    homomorphic_sum = 0
    randomness_sum = 0

    # min and max for number of answers, useful later
    min_answers = 0
    if question.has_key('min'):
      min_answers = question['min']
    max_answers = question['max']

    # go through each possible answer and encrypt either a g^0 or a g^1.
    for answer_num in range(len(answers)):
      plaintext_index = 0
      
      # assuming a list of answers
      if answer_num in answer_indexes:
        plaintext_index = 1
        num_selected_answers += 1

      # randomness and encryption
      randomness[answer_num] = algs.Utils.random_mpz_lt(pk.q)
      choices[answer_num] = pk.encrypt_with_r(plaintexts[plaintext_index], randomness[answer_num])
      
      # generate proof
      individual_proofs[answer_num] = choices[answer_num].generate_disjunctive_encryption_proof(plaintexts, plaintext_index, 
                                                randomness[answer_num], algs.EG_disjunctive_challenge_generator)
                                                
      # sum things up homomorphically if needed
      if max_answers != None:
        homomorphic_sum = choices[answer_num] * homomorphic_sum
        randomness_sum = (randomness_sum + randomness[answer_num]) % pk.q

    # prove that the sum is 0 or 1 (can be "blank vote" for this answer)
    # num_selected_answers is 0 or 1, which is the index into the plaintext that is actually encoded
    
    if num_selected_answers < min_answers:
      raise Exception("Need to select at least %s answer(s)" % min_answers)
    
    if max_answers != None:
      sum_plaintexts = cls.generate_plaintexts(pk, min=min_answers, max=max_answers)
    
      # need to subtract the min from the offset
      overall_proof = homomorphic_sum.generate_disjunctive_encryption_proof(sum_plaintexts, num_selected_answers - min_answers, randomness_sum, algs.EG_disjunctive_challenge_generator);
    else:
      # approval voting
      overall_proof = None
    
    return cls(choices, individual_proofs, overall_proof, randomness, answer_indexes)
    
# WORK HERE

class EncryptedVote(WorkflowObject):
  """
  An encrypted ballot
  """
  def __init__(self):
    self.encrypted_answers = None

  @property
  def datatype(self):
    # FIXME
    return "legacy/EncryptedVote"

  def _answers_get(self):
    return self.encrypted_answers

  def _answers_set(self, value):
    self.encrypted_answers = value

  answers = property(_answers_get, _answers_set)

  def verify(self, election):
    # right number of answers
    if len(self.encrypted_answers) != len(election.questions):
      return False
    
    # check hash
    if self.election_hash != election.hash:
      # print "%s / %s " % (self.election_hash, election.hash)
      return False
      
    # check ID
    if self.election_uuid != election.uuid:
      return False
      
    # check proofs on all of answers
    for question_num in range(len(election.questions)):
      ea = self.encrypted_answers[question_num]

      question = election.questions[question_num]
      min_answers = 0
      if question.has_key('min'):
        min_answers = question['min']
        
      if not ea.verify(election.public_key, min=min_answers, max=question['max']):
        return False
        
    return True
    
  @classmethod
  def fromElectionAndAnswers(cls, election, answers):
    pk = election.public_key

    # each answer is an index into the answer array
    encrypted_answers = [EncryptedAnswer.fromElectionAndAnswer(election, answer_num, answers[answer_num]) for answer_num in range(len(answers))]
    return_val = cls()
    return_val.encrypted_answers = encrypted_answers
    return_val.election_hash = election.hash
    return_val.election_uuid = election.uuid

    return return_val
    

class DLogTable(object):
  """
  Keeping track of discrete logs
  """
  
  def __init__(self, base, modulus):
    self.dlogs = {}
    self.dlogs[1] = 0
    self.last_dlog_result = 1
    self.counter = 0
    
    self.base = base
    self.modulus = modulus
    
  def increment(self):
    self.counter += 1
    
    # new value
    new_value = (self.last_dlog_result * self.base) % self.modulus
    
    # record the discrete log
    self.dlogs[new_value] = self.counter
    
    # record the last value
    self.last_dlog_result = new_value
    
  def precompute(self, up_to):
    while self.counter < up_to:
      self.increment()
  
  def lookup(self, value):
    return self.dlogs.get(value, None)
      
    
class Tally(WorkflowObject):
  """
  A running homomorphic tally
  """

  @property
  def datatype(self):
    return "legacy/Tally"
  
  def __init__(self, *args, **kwargs):
    super(Tally, self).__init__()
    
    election = kwargs.get('election',None)
    self.tally = None
    self.num_tallied = 0    

    if election:
      self.init_election(election)
      self.tally = [[0 for a in q['answers']] for q in self.questions]
    else:
      self.questions = None
      self.public_key = None
      self.tally = None

  def init_election(self, election):
    """
    given the election, initialize some params
    """
    self.election = election
    self.questions = election.questions
    self.public_key = election.public_key
    
  def add_vote_batch(self, encrypted_votes, verify_p=True):
    """
    Add a batch of votes. Eventually, this will be optimized to do an aggregate proof verification
    rather than a whole proof verif for each vote.
    """
    for vote in encrypted_votes:
      self.add_vote(vote, verify_p)
    
  def add_vote(self, encrypted_vote, verify_p=True):
    # do we verify?
    if verify_p:
      if not encrypted_vote.verify(self.election):
        raise Exception('Bad Vote')

    # for each question
    for question_num in range(len(self.questions)):
      question = self.questions[question_num]
      answers = question['answers']
      
      # for each possible answer to each question
      for answer_num in range(len(answers)):
        # do the homomorphic addition into the tally
        enc_vote_choice = encrypted_vote.encrypted_answers[question_num].choices[answer_num]
        enc_vote_choice.pk = self.public_key
        self.tally[question_num][answer_num] = encrypted_vote.encrypted_answers[question_num].choices[answer_num] * self.tally[question_num][answer_num]

    self.num_tallied += 1

  def decryption_factors_and_proofs(self, sk):
    """
    returns an array of decryption factors and a corresponding array of decryption proofs.
    makes the decryption factors into strings, for general Helios / JS compatibility.
    """
    # for all choices of all questions (double list comprehension)
    decryption_factors = []
    decryption_proof = []
    
    for question_num, question in enumerate(self.questions):
      answers = question['answers']
      question_factors = []
      question_proof = []

      for answer_num, answer in enumerate(answers):
        # do decryption and proof of it
        dec_factor, proof = sk.decryption_factor_and_proof(self.tally[question_num][answer_num])

        # look up appropriate discrete log
        # this is the string conversion
        question_factors.append(dec_factor)
        question_proof.append(proof)
        
      decryption_factors.append(question_factors)
      decryption_proof.append(question_proof)
    
    return decryption_factors, decryption_proof
    
  def decrypt_and_prove(self, sk, discrete_logs=None):
    """
    returns an array of tallies and a corresponding array of decryption proofs.
    """
    
    # who's keeping track of discrete logs?
    if not discrete_logs:
      discrete_logs = self.discrete_logs
      
    # for all choices of all questions (double list comprehension)
    decrypted_tally = []
    decryption_proof = []
    
    for question_num in range(len(self.questions)):
      question = self.questions[question_num]
      answers = question['answers']
      question_tally = []
      question_proof = []

      for answer_num in range(len(answers)):
        # do decryption and proof of it
        plaintext, proof = sk.prove_decryption(self.tally[question_num][answer_num])

        # look up appropriate discrete log
        question_tally.append(discrete_logs[plaintext])
        question_proof.append(proof)
        
      decrypted_tally.append(question_tally)
      decryption_proof.append(question_proof)
    
    return decrypted_tally, decryption_proof
  
  def verify_decryption_proofs(self, decryption_factors, decryption_proofs, public_key, challenge_generator):
    """
    decryption_factors is a list of lists of dec factors
    decryption_proofs are the corresponding proofs
    public_key is, of course, the public key of the trustee
    """

    # go through each one
    for q_num, q in enumerate(self.tally):
      for a_num, answer_tally in enumerate(q):
        # parse the proof
        #proof = algs.EGZKProof.fromJSONDict(decryption_proofs[q_num][a_num])
        proof = decryption_proofs[q_num][a_num]
        
        # check that g, alpha, y, dec_factor is a DH tuple
        if not proof.verify(public_key.g, answer_tally.alpha, public_key.y, int(decryption_factors[q_num][a_num]), public_key.p, public_key.q, challenge_generator):
          return False
    
    return True
    
  def decrypt_from_factors(self, decryption_factors, public_key):
    """
    decrypt a tally given decryption factors
    
    The decryption factors are a list of decryption factor sets, for each trustee.
    Each decryption factor set is a list of lists of decryption factors (questions/answers).
    """
    
    # pre-compute a dlog table
    dlog_table = DLogTable(base = public_key.g, modulus = public_key.p)
    dlog_table.precompute(self.num_tallied)
    
    result = []
    
    # go through each one
    for q_num, q in enumerate(self.tally):
      q_result = []

      for a_num, a in enumerate(q):
        # coalesce the decryption factors into one list
        dec_factor_list = [df[q_num][a_num] for df in decryption_factors]
        raw_value = self.tally[q_num][a_num].decrypt(dec_factor_list, public_key)
        
        q_result.append(dlog_table.lookup(raw_value))

      result.append(q_result)
    
    return result

  def _process_value_in(self, field_name, field_value):
    if field_name == 'tally':
      return [[algs.EGCiphertext.fromJSONDict(a) for a in q] for q in field_value]
      
  def _process_value_out(self, field_name, field_value):
    if field_name == 'tally':
      return [[a.toJSONDict() for a in q] for q in field_value]    
        

########NEW FILE########
__FILENAME__ = cas
"""
CAS (Princeton) Authentication

Some code borrowed from
https://sp.princeton.edu/oit/sdp/CAS/Wiki%20Pages/Python.aspx
"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import sys, os, cgi, urllib, urllib2, re, uuid, datetime
from xml.etree import ElementTree

CAS_EMAIL_DOMAIN = "princeton.edu"
CAS_URL= 'https://fed.princeton.edu/cas/'
CAS_LOGOUT_URL = 'https://fed.princeton.edu/cas/logout?service=%s'
CAS_SAML_VALIDATE_URL = 'https://fed.princeton.edu/cas/samlValidate?TARGET=%s'

# eligibility checking
if hasattr(settings, 'CAS_USERNAME'):
  CAS_USERNAME = settings.CAS_USERNAME
  CAS_PASSWORD = settings.CAS_PASSWORD
  CAS_ELIGIBILITY_URL = settings.CAS_ELIGIBILITY_URL
  CAS_ELIGIBILITY_REALM = settings.CAS_ELIGIBILITY_REALM

# display tweaks
LOGIN_MESSAGE = "Log in with my NetID"
STATUS_UPDATES = False


def _get_service_url():
  # FIXME current URL
  from helios_auth.views import after
  from django.conf import settings
  from django.core.urlresolvers import reverse
  
  return settings.SECURE_URL_HOST + reverse(after)
  
def get_auth_url(request, redirect_url):
  request.session['cas_redirect_url'] = redirect_url
  return CAS_URL + 'login?service=' + urllib.quote(_get_service_url())

def get_user_category(user_id):
  theurl = CAS_ELIGIBILITY_URL % user_id

  auth_handler = urllib2.HTTPBasicAuthHandler()
  auth_handler.add_password(realm=CAS_ELIGIBILITY_REALM, uri= theurl, user= CAS_USERNAME, passwd = CAS_PASSWORD)
  opener = urllib2.build_opener(auth_handler)
  urllib2.install_opener(opener)
  
  result = urllib2.urlopen(CAS_ELIGIBILITY_URL % user_id).read().strip()
  parsed_result = ElementTree.fromstring(result)
  return parsed_result.text
  
def get_saml_info(ticket):
  """
  Using SAML, get all of the information needed
  """

  import logging

  saml_request = """<?xml version='1.0' encoding='UTF-8'?> 
  <soap-env:Envelope 
     xmlns:soap-env='http://schemas.xmlsoap.org/soap/envelope/'> 
     <soap-env:Header />
     <soap-env:Body> 
       <samlp:Request xmlns:samlp="urn:oasis:names:tc:SAML:1.0:protocol"
                      MajorVersion="1" MinorVersion="1"
                      RequestID="%s"
                      IssueInstant="%sZ">
           <samlp:AssertionArtifact>%s</samlp:AssertionArtifact>
       </samlp:Request>
     </soap-env:Body> 
  </soap-env:Envelope>
""" % (uuid.uuid1(), datetime.datetime.utcnow().isoformat(), ticket)

  url = CAS_SAML_VALIDATE_URL % urllib.quote(_get_service_url())

  # by virtue of having a body, this is a POST
  req = urllib2.Request(url, saml_request)
  raw_response = urllib2.urlopen(req).read()

  logging.info("RESP:\n%s\n\n" % raw_response)

  response = ElementTree.fromstring(raw_response)

  # ugly path down the tree of attributes
  attributes = response.findall('{http://schemas.xmlsoap.org/soap/envelope/}Body/{urn:oasis:names:tc:SAML:1.0:protocol}Response/{urn:oasis:names:tc:SAML:1.0:assertion}Assertion/{urn:oasis:names:tc:SAML:1.0:assertion}AttributeStatement/{urn:oasis:names:tc:SAML:1.0:assertion}Attribute')

  values = {}
  for attribute in attributes:
    values[str(attribute.attrib['AttributeName'])] = attribute.findtext('{urn:oasis:names:tc:SAML:1.0:assertion}AttributeValue')
  
  # parse response for netid, display name, and employee type (category)
  return {'user_id': values.get('mail',None), 'name': values.get('displayName', None), 'category': values.get('employeeType',None)}
  
def get_user_info(user_id):
  url = 'http://dsml.princeton.edu/'
  headers = {'SOAPAction': "#searchRequest", 'Content-Type': 'text/xml'}
  
  request_body = """<?xml version='1.0' encoding='UTF-8'?> 
  <soap-env:Envelope 
     xmlns:xsd='http://www.w3.org/2001/XMLSchema'
     xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
     xmlns:soap-env='http://schemas.xmlsoap.org/soap/envelope/'> 
     <soap-env:Body> 
        <batchRequest xmlns='urn:oasis:names:tc:DSML:2:0:core'
  requestID='searching'>
        <searchRequest 
           dn='o=Princeton University, c=US'
           scope='wholeSubtree'
           derefAliases='neverDerefAliases'
           sizeLimit='200'> 
              <filter>
                   <equalityMatch name='uid'>
                            <value>%s</value>
                    </equalityMatch>
               </filter>
               <attributes>
                       <attribute name="displayName"/>
                       <attribute name="pustatus"/>
               </attributes>
        </searchRequest>
       </batchRequest>
     </soap-env:Body> 
  </soap-env:Envelope>
""" % user_id

  req = urllib2.Request(url, request_body, headers)
  response = urllib2.urlopen(req).read()
  
  # parse the result
  from xml.dom.minidom import parseString
  
  response_doc = parseString(response)
  
  # get the value elements (a bit of a hack but no big deal)
  values = response_doc.getElementsByTagName('value')
  
  if len(values)>0:
    return {'name' : values[0].firstChild.wholeText, 'category' : values[1].firstChild.wholeText}
  else:
    return None
  
def get_user_info_special(ticket):
  # fetch the information from the CAS server
  val_url = CAS_URL + "validate" + \
     '?service=' + urllib.quote(_get_service_url()) + \
     '&ticket=' + urllib.quote(ticket)
  r = urllib.urlopen(val_url).readlines() # returns 2 lines

  # success
  if len(r) == 2 and re.match("yes", r[0]) != None:
    netid = r[1].strip()
    
    category = get_user_category(netid)
    
    #try:
    #  user_info = get_user_info(netid)
    #except:
    #  user_info = None

    # for now, no need to wait for this request to finish
    user_info = None

    if user_info:
      info = {'name': user_info['name'], 'category': category}
    else:
      info = {'name': netid, 'category': category}
      
    return {'user_id': netid, 'name': info['name'], 'info': info, 'token': None}
  else:
    return None

def get_user_info_after_auth(request):
  ticket = request.GET.get('ticket', None)
  
  # if no ticket, this is a logout
  if not ticket:
    return None

  #user_info = get_saml_info(ticket)
  user_info = get_user_info_special(ticket)

  user_info['type'] = 'cas'  

  return user_info
    
def do_logout(user):
  """
  Perform logout of CAS by redirecting to the CAS logout URL
  """
  return HttpResponseRedirect(CAS_LOGOUT_URL % _get_service_url())
  
def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, name, user_info, subject, body):
  """
  send email, for now just to Princeton
  """
  # if the user_id contains an @ sign already
  if "@" in user_id:
    email = user_id
  else:
    email = "%s@%s" % (user_id, CAS_EMAIL_DOMAIN)
    
  if user_info.has_key('name'):
    name = user_info["name"]
  else:
    name = email
    
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, email)], fail_silently=False)

#
# eligibility
#

def check_constraint(constraint, user):
  if not user.info.has_key('category'):
    return False
  return constraint['year'] == user.info['category']

def generate_constraint(category_id, user):
  """
  generate the proper basic data structure to express a constraint
  based on the category string
  """
  return {'year': category_id}

def list_categories(user):
  current_year = datetime.datetime.now().year
  return [{'id': str(y), 'name': 'Class of %s' % y} for y 
          in range(current_year, current_year+5)]

def eligibility_category_id(constraint):
  return constraint['year']

def pretty_eligibility(constraint):
  return "Members of the Class of %s" % constraint['year']

########NEW FILE########
__FILENAME__ = facebook
"""
Facebook Authentication
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

APP_ID = settings.FACEBOOK_APP_ID
API_KEY = settings.FACEBOOK_API_KEY
API_SECRET = settings.FACEBOOK_API_SECRET
  
#from facebookclient import Facebook
import urllib, urllib2, cgi

# some parameters to indicate that status updating is possible
STATUS_UPDATES = True
STATUS_UPDATE_WORDING_TEMPLATE = "Send %s to your facebook status"

from helios_auth import utils

def facebook_url(url, params):
  if params:
    return "https://graph.facebook.com%s?%s" % (url, urllib.urlencode(params))
  else:
    return "https://graph.facebook.com%s" % url

def facebook_get(url, params):
  full_url = facebook_url(url,params)
  try:
    return urllib2.urlopen(full_url).read()
  except urllib2.HTTPError:
    from helios_auth.models import AuthenticationExpired
    raise AuthenticationExpired()

def facebook_post(url, params):
  full_url = facebook_url(url, None)
  return urllib2.urlopen(full_url, urllib.urlencode(params)).read()

def get_auth_url(request, redirect_url):
  request.session['fb_redirect_uri'] = redirect_url
  return facebook_url('/oauth/authorize', {
      'client_id': APP_ID,
      'redirect_uri': redirect_url,
      'scope': 'publish_stream,email,user_groups'})
    
def get_user_info_after_auth(request):
  args = facebook_get('/oauth/access_token', {
      'client_id' : APP_ID,
      'redirect_uri' : request.session['fb_redirect_uri'],
      'client_secret' : API_SECRET,
      'code' : request.GET['code']
      })

  access_token = cgi.parse_qs(args)['access_token'][0]

  info = utils.from_json(facebook_get('/me', {'access_token':access_token}))

  return {'type': 'facebook', 'user_id' : info['id'], 'name': info.get('name'), 'email': info.get('email'), 'info': info, 'token': {'access_token': access_token}}
    
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  result = facebook_post('/me/feed', {
      'access_token': token['access_token'],
      'message': message
      })

def send_message(user_id, user_name, user_info, subject, body):
  if user_info.has_key('email'):
    send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (user_name, user_info['email'])], fail_silently=False)    


##
## eligibility checking
##

# a constraint looks like
# {'group' : {'id': 123, 'name': 'asdfsdf'}}
#
# only the ID matters for checking, the name of the group is cached
# here for ease of display so it doesn't have to be re-queried.

def get_user_groups(user):
  groups_raw = utils.from_json(facebook_get('/me/groups', {'access_token':user.token['access_token']}))
  return groups_raw['data']    

def check_constraint(constraint, user):
  # get the groups for the user
  groups = [group['id'] for group in get_user_groups(user)]

  # check if one of them is the group in the constraint
  try:
    return constraint['group']['id'] in groups
  except:
    # FIXME: be more specific about exception catching
    return False

def generate_constraint(category_id, user):
  """
  generate the proper basic data structure to express a constraint
  based on the category string
  """
  groups = get_user_groups(user)
  the_group = [g for g in groups if g['id'] == category_id][0]

  return {'group': the_group}

def list_categories(user):
  return get_user_groups(user)

def eligibility_category_id(constraint):
  return constraint['group']['id']

def pretty_eligibility(constraint):
  return "Facebook users who are members of the \"%s\" group" % constraint['group']['name']

########NEW FILE########
__FILENAME__ = context_processors
def messages(request):
    """Returns messages similar to ``django.core.context_processors.auth``."""
    if hasattr(request, 'facebook') and request.facebook.uid is not None:
        from models import Message
        messages = Message.objects.get_and_delete_all(uid=request.facebook.uid)
    return {'messages': messages}
########NEW FILE########
__FILENAME__ = models
from django.db import models

# get_facebook_client lets us get the current Facebook object
# from outside of a view, which lets us have cleaner code
from facebook.djangofb import get_facebook_client

class UserManager(models.Manager):
    """Custom manager for a Facebook User."""
    
    def get_current(self):
        """Gets a User object for the logged-in Facebook user."""
        facebook = get_facebook_client()
        user, created = self.get_or_create(id=int(facebook.uid))
        if created:
            # we could do some custom actions for new users here...
            pass
        return user

class User(models.Model):
    """A simple User model for Facebook users."""

    # We use the user's UID as the primary key in our database.
    id = models.IntegerField(primary_key=True)

    # TODO: The data that you want to store for each user would go here.
    # For this sample, we let users let people know their favorite progamming
    # language, in the spirit of Extended Info.
    language = models.CharField(maxlength=64, default='Python')

    # Add the custom manager
    objects = UserManager()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('{{ project }}.{{ app }}.views',
    (r'^$', 'canvas'),
    # Define other pages you want to create here
)


########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.views.generic.simple import direct_to_template
#uncomment the following two lines and the one below
#if you dont want to use a decorator instead of the middleware
#from django.utils.decorators import decorator_from_middleware
#from facebook.djangofb import FacebookMiddleware

# Import the Django helpers
import facebook.djangofb as facebook

# The User model defined in models.py
from models import User

# We'll require login for our canvas page. This
# isn't necessarily a good idea, as we might want
# to let users see the page without granting our app
# access to their info. See the wiki for details on how
# to do this.
#@decorator_from_middleware(FacebookMiddleware)
@facebook.require_login()
def canvas(request):
    # Get the User object for the currently logged in user
    user = User.objects.get_current()

    # Check if we were POSTed the user's new language of choice
    if 'language' in request.POST:
        user.language = request.POST['language'][:64]
        user.save()

    # User is guaranteed to be logged in, so pass canvas.fbml
    # an extra 'fbuser' parameter that is the User object for
    # the currently logged in user.
    return direct_to_template(request, 'canvas.fbml', extra_context={'fbuser': user})

@facebook.require_login()
def ajax(request):
    return HttpResponse('hello world')

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.html import escape
from django.utils.safestring import mark_safe

FB_MESSAGE_STATUS = (
    (0, 'Explanation'),
    (1, 'Error'),
    (2, 'Success'),
)

class MessageManager(models.Manager):
    def get_and_delete_all(self, uid):
        messages = []
        for m in self.filter(uid=uid):
            messages.append(m)
            m.delete()
        return messages

class Message(models.Model):
    """Represents a message for a Facebook user."""
    uid = models.CharField(max_length=25)
    status = models.IntegerField(choices=FB_MESSAGE_STATUS)
    message = models.CharField(max_length=300)
    objects = MessageManager()

    def __unicode__(self):
        return self.message

    def _fb_tag(self):
        return self.get_status_display().lower()

    def as_fbml(self):
        return mark_safe(u'<fb:%s message="%s" />' % (
            self._fb_tag(),
            escape(self.message),
        ))

########NEW FILE########
__FILENAME__ = webappfb
#
# webappfb - Facebook tools for Google's AppEngine "webapp" Framework
#
# Copyright (c) 2009, Max Battcher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from google.appengine.api import memcache
from google.appengine.ext.webapp import RequestHandler
from facebook import Facebook
import yaml

"""
Facebook tools for Google AppEngine's object-oriented "webapp" framework.
"""

# This global configuration dictionary is for configuration variables
# for Facebook requests such as the application's API key and secret
# key. Defaults to loading a 'facebook.yaml' YAML file. This should be
# useful and familiar for most AppEngine development.
FACEBOOK_CONFIG = yaml.load(file('facebook.yaml', 'r'))

class FacebookRequestHandler(RequestHandler):
    """
    Base class for request handlers for Facebook apps, providing useful
    Facebook-related tools: a local 
    """

    def _fbconfig_value(self, name, default=None):
        """
        Checks the global config dictionary and then for a class/instance
        variable, using a provided default if no value is found.
        """
        if name in FACEBOOK_CONFIG:
            default = FACEBOOK_CONFIG[name]
            
        return getattr(self, name, default)

    def initialize(self, request, response):
        """
        Initialize's this request's Facebook client.
        """
        super(FacebookRequestHandler, self).initialize(request, response)

        app_name = self._fbconfig_value('app_name', '')
        api_key = self._fbconfig_value('api_key', None)
        secret_key = self._fbconfig_value('secret_key', None)

        self.facebook = Facebook(api_key, secret_key,
            app_name=app_name)

        require_app = self._fbconfig_value('require_app', False)
        require_login = self._fbconfig_value('require_login', False)
        need_session = self._fbconfig_value('need_session', False)
        check_session = self._fbconfig_value('check_session', True)

        self._messages = None
        self.redirecting = False

        if require_app or require_login:
            if not self.facebook.check_session(request):
                self.redirect(self.facebook.get_login_url(next=request.path))
                self.redirecting = True
                return
        elif check_session:
            self.facebook.check_session(request) # ignore response

        # NOTE: require_app is deprecated according to modern Facebook login
        #       policies. Included for completeness, but unnecessary.
        if require_app and not self.facebook.added:
            self.redirect(self.facebook.get_add_url(next=request.path))
            self.redirecting = True
            return

        if not (require_app or require_login) and need_session:
            self.facebook.auth.getSession()

    def redirect(self, url, **kwargs):
        """
        For Facebook canvas pages we should use <fb:redirect /> instead of
        a normal redirect.
        """
        if self.facebook.in_canvas:
            self.response.clear()
            self.response.out.write('<fb:redirect url="%s" />' % (url, ))
        else:
            super(FacebookRequestHandler, self).redirect(url, **kwargs)

    def add_user_message(self, kind, msg, detail='', time=15 * 60):
        """
        Add a message to the current user to memcache.
        """
        if self.facebook.uid:
            key = 'messages:%s' % self.facebook.uid
            self._messages = memcache.get(key)
            message = {
                'kind': kind,
                'message': msg,
                'detail': detail,
            }
            if self._messages is not None:
                self._messages.append(message)
            else:
                self._messages = [message]
            memcache.set(key, self._messages, time=time)

    def get_and_delete_user_messages(self):
        """
        Get all of the messages for the current user; removing them.
        """
        if self.facebook.uid:
            key = 'messages:%s' % self.facebook.uid
            if not hasattr(self, '_messages') or self._messages is None:
                self._messages = memcache.get(key)
            memcache.delete(key)
            return self._messages
        return None

class FacebookCanvasHandler(FacebookRequestHandler):
    """
    Request handler for Facebook canvas (FBML application) requests.
    """

    def canvas(self, *args, **kwargs):
        """
        This will be your handler to deal with Canvas requests.
        """
        raise NotImplementedError()

    def get(self, *args):
        """
        All valid canvas views are POSTS.
        """
        # TODO: Attempt to auto-redirect to Facebook canvas?
        self.error(404)

    def post(self, *args, **kwargs):
        """
        Check a couple of simple safety checks and then call the canvas
        handler.
        """
        if self.redirecting: return

        if not self.facebook.in_canvas:
            self.error(404)
            return

        self.canvas(*args, **kwargs)

# vim: ai et ts=4 sts=4 sw=4

########NEW FILE########
__FILENAME__ = wsgi
"""This is some simple helper code to bridge the Pylons / PyFacebook gap.

There's some generic WSGI middleware, some Paste stuff, and some Pylons
stuff.  Once you put FacebookWSGIMiddleware into your middleware stack,
you'll have access to ``environ["pyfacebook.facebook"]``, which is a
``facebook.Facebook`` object.  If you're using Paste (which includes
Pylons users), you can also access this directly using the facebook
global in this module.

"""

# Be careful what you import.  Don't expect everyone to have Pylons,
# Paste, etc. installed.  Degrade gracefully.

from facebook import Facebook

__docformat__ = "restructuredtext"


# Setup Paste, if available.  This needs to stay in the same module as
# FacebookWSGIMiddleware below.

try:
    from paste.registry import StackedObjectProxy
    from webob.exc import _HTTPMove
    from paste.util.quoting import strip_html, html_quote, no_quote
except ImportError:
    pass
else:
    facebook = StackedObjectProxy(name="PyFacebook Facebook Connection")


    class CanvasRedirect(_HTTPMove):

        """This is for canvas redirects."""

        title = "See Other"
        code = 200
        template = '<fb:redirect url="%(location)s" />'

        def html(self, environ):
            """ text/html representation of the exception """
            body = self.make_body(environ, self.template, html_quote, no_quote)
            return body

class FacebookWSGIMiddleware(object):

    """This is WSGI middleware for Facebook."""

    def __init__(self, app, config, facebook_class=Facebook):
        """Initialize the Facebook middleware.

        ``app``
            This is the WSGI application being wrapped.

        ``config``
            This is a dict containing the keys "pyfacebook.apikey" and
            "pyfacebook.secret".

        ``facebook_class``
            If you want to subclass the Facebook class, you can pass in
            your replacement here.  Pylons users will want to use
            PylonsFacebook.

        """
        self.app = app
        self.config = config
        self.facebook_class = facebook_class

    def __call__(self, environ, start_response):
        config = self.config
        real_facebook = self.facebook_class(config["pyfacebook.apikey"],
                                            config["pyfacebook.secret"])
        registry = environ.get('paste.registry')
        if registry:
            registry.register(facebook, real_facebook)
        environ['pyfacebook.facebook'] = real_facebook
        return self.app(environ, start_response)


# The remainder is Pylons specific.

try:
    import pylons
    from pylons.controllers.util import redirect_to as pylons_redirect_to
    from routes import url_for
except ImportError:
    pass
else:


    class PylonsFacebook(Facebook):

        """Subclass Facebook to add Pylons goodies."""

        def check_session(self, request=None):
            """The request parameter is now optional."""
            if request is None:
                request = pylons.request
            return Facebook.check_session(self, request)

        # The Django request object is similar enough to the Paste
        # request object that check_session and validate_signature
        # should *just work*.

        def redirect_to(self, url):
            """Wrap Pylons' redirect_to function so that it works in_canvas.

            By the way, this won't work until after you call
            check_session().

            """
            if self.in_canvas:
                raise CanvasRedirect(url)
            pylons_redirect_to(url)

        def apps_url_for(self, *args, **kargs):
            """Like url_for, but starts with "http://apps.facebook.com"."""
            return "http://apps.facebook.com" + url_for(*args, **kargs)


    def create_pylons_facebook_middleware(app, config):
        """This is a simple wrapper for FacebookWSGIMiddleware.

        It passes the correct facebook_class.

        """
        return FacebookWSGIMiddleware(app, config,
                                      facebook_class=PylonsFacebook)

########NEW FILE########
__FILENAME__ = google
"""
Google Authentication

"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import sys, os, cgi, urllib, urllib2, re
from xml.etree import ElementTree

from openid import view_helpers

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with my Google Account"
OPENID_ENDPOINT = 'https://www.google.com/accounts/o8/id'

# FIXME!
# TRUST_ROOT = 'http://localhost:8000'
# RETURN_TO = 'http://localhost:8000/auth/after'

def get_auth_url(request, redirect_url):
  # FIXME?? TRUST_ROOT should be diff than return_url?
  request.session['google_redirect_url'] = redirect_url
  url = view_helpers.start_openid(request.session, OPENID_ENDPOINT, redirect_url, redirect_url)
  return url

def get_user_info_after_auth(request):
  data = view_helpers.finish_openid(request.session, request.GET, request.session['google_redirect_url'])

  if not data.has_key('ax'):
    return None

  email = data['ax']['email'][0]

  # do we have a firstname/lastname?
  if data['ax'].has_key('firstname') and data['ax'].has_key('lastname'):
    name = "%s %s" % (data['ax']['firstname'][0], data['ax']['lastname'][0])
  else:
    name = email

  return {'type' : 'google', 'user_id': email, 'name': name , 'info': {'email': email}, 'token':{}}
    
def do_logout(user):
  """
  logout of Google
  """
  return None
  
def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, name, user_info, subject, body):
  """
  send email to google users. user_id is the email for google.
  """
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (name, user_id)], fail_silently=False)
  
def check_constraint(constraint, user_info):
  """
  for eligibility
  """
  pass

########NEW FILE########
__FILENAME__ = linkedin
"""
LinkedIn Authentication
"""

from oauthclient import client

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from helios_auth import utils

from xml.etree import ElementTree

import logging

from django.conf import settings
API_KEY = settings.LINKEDIN_API_KEY
API_SECRET = settings.LINKEDIN_API_SECRET

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False
STATUS_UPDATE_WORDING_TEMPLATE = "Tweet %s"

OAUTH_PARAMS = {
  'root_url' : 'https://api.linkedin.com/uas',
  'request_token_path' : '/oauth/requestToken',
  'authorize_path' : '/oauth/authorize',
  'authenticate_path' : '/oauth/authenticate',
  'access_token_path': '/oauth/accessToken'
}

def _get_new_client(token=None, token_secret=None):
  if token:
    return client.LoginOAuthClient(API_KEY, API_SECRET, OAUTH_PARAMS, token, token_secret)
  else:
    return client.LoginOAuthClient(API_KEY, API_SECRET, OAUTH_PARAMS)

def _get_client_by_token(token):
  return _get_new_client(token['oauth_token'], token['oauth_token_secret'])

def get_auth_url(request, redirect_url):
  client = _get_new_client()
  try:
    tok = client.get_request_token()
  except:
    return None
  
  request.session['request_token'] = tok
  url = client.get_authenticate_url(tok['oauth_token']) 
  return url
    
def get_user_info_after_auth(request):
  tok = request.session['request_token']
  login_client = _get_client_by_token(tok)
  access_token = login_client.get_access_token(verifier = request.GET.get('oauth_verifier', None))
  request.session['access_token'] = access_token
    
  user_info_xml = ElementTree.fromstring(login_client.oauth_request('http://api.linkedin.com/v1/people/~:(id,first-name,last-name)', args={}, method='GET'))
  
  user_id = user_info_xml.findtext('id')
  first_name = user_info_xml.findtext('first-name')
  last_name = user_info_xml.findtext('last-name')

  return {'type': 'linkedin', 'user_id' : user_id, 'name': "%s %s" % (first_name, last_name), 'info': {}, 'token': access_token}
    

def user_needs_intervention(user_id, user_info, token):
  """
  check to see if user is following the users we need
  """
  return None

def _get_client_by_request(request):
  access_token = request.session['access_token']
  return _get_client_by_token(access_token)
  
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  return
  #twitter_client = _get_client_by_token(token)
  #result = twitter_client.oauth_request('http://api.twitter.com/1/statuses/update.json', args={'status': message}, method='POST')

def send_message(user_id, user_name, user_info, subject, body):
  pass

def send_notification(user_id, user_info, message):
  pass



########NEW FILE########
__FILENAME__ = live
"""
Windows Live Authentication using oAuth WRAP,
so much like Facebook

# NOT WORKING YET because Windows Live documentation and status is unclear. Is it in beta? I think it is.
"""

import logging

from django.conf import settings
APP_ID = settings.LIVE_APP_ID
APP_SECRET = settings.LIVE_APP_SECRET
  
import urllib, urllib2, cgi

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False
# STATUS_UPDATE_WORDING_TEMPLATE = "Send %s to your facebook status"

from helios_auth import utils

def live_url(url, params):
  if params:
    return "https://graph.facebook.com%s?%s" % (url, urllib.urlencode(params))
  else:
    return "https://graph.facebook.com%s" % url

def live_get(url, params):
  full_url = live_url(url,params)
  return urllib2.urlopen(full_url).read()

def live_post(url, params):
  full_url = live_url(url, None)
  return urllib2.urlopen(full_url, urllib.urlencode(params)).read()

def get_auth_url(request, redirect_url):
  request.session['live_redirect_uri'] = redirect_url
  return live_url('/oauth/authorize', {
      'client_id': APP_ID,
      'redirect_uri': redirect_url,
      'scope': 'publish_stream'})
    
def get_user_info_after_auth(request):
  args = facebook_get('/oauth/access_token', {
      'client_id' : APP_ID,
      'redirect_uri' : request.session['fb_redirect_uri'],
      'client_secret' : API_SECRET,
      'code' : request.GET['code']
      })

  access_token = cgi.parse_qs(args)['access_token'][0]

  info = utils.from_json(facebook_get('/me', {'access_token':access_token}))

  return {'type': 'facebook', 'user_id' : info['id'], 'name': info['name'], 'info': info, 'token': {'access_token': access_token}}
    
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  result = facebook_post('/me/feed', {
      'access_token': token['access_token'],
      'message': message
      })

def send_message(user_id, user_name, user_info, subject, body):
  pass

########NEW FILE########
__FILENAME__ = client
'''
Python Oauth client for Twitter
modified to work with other oAuth logins like LinkedIn (Ben Adida)

Used the SampleClient from the OAUTH.org example python client as basis.

props to leahculver for making a very hard to use but in the end usable oauth lib.

'''
import httplib
import urllib, urllib2
import time
import webbrowser
import oauth as oauth
from urlparse import urlparse

class LoginOAuthClient(oauth.OAuthClient):

    #set api urls
    def request_token_url(self):
        return self.server_params['root_url'] + self.server_params['request_token_path']
    def authorize_url(self):
        return self.server_params['root_url'] + self.server_params['authorize_path']
    def authenticate_url(self):
        return self.server_params['root_url'] + self.server_params['authenticate_path']
    def access_token_url(self):
        return self.server_params['root_url'] + self.server_params['access_token_path']

    #oauth object
    def __init__(self, consumer_key, consumer_secret, server_params, oauth_token=None, oauth_token_secret=None):
        """
        params should be a dictionary including
        root_url, request_token_path, authorize_path, authenticate_path, access_token_path
        """
        self.server_params = server_params

        self.sha1_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        if ((oauth_token != None) and (oauth_token_secret!=None)):
            self.token = oauth.OAuthConsumer(oauth_token, oauth_token_secret)
        else:
            self.token = None

    def oauth_request(self,url, args = {}, method=None):
        if (method==None):
            if args=={}:
                method = "GET"
            else:
                method = "POST"
        req = oauth.OAuthRequest.from_consumer_and_token(self.consumer, self.token, method, url, args)
        req.sign_request(self.sha1_method, self.consumer,self.token)
        if (method=="GET"):
            return self.http_wrapper(req.to_url())
        elif (method == "POST"):
            return self.http_wrapper(req.get_normalized_http_url(),req.to_postdata())

    #this is barely working. (i think. mostly it is that everyone else is using httplib) 
    def http_wrapper(self, url, postdata={}): 
        try:
            if (postdata != {}): 
                f = urllib.urlopen(url, postdata) 
            else: 
                f = urllib.urlopen(url) 
            response = f.read()
        except:
            import traceback
            import logging, sys
            cla, exc, tb = sys.exc_info()
            logging.error(url)
            if postdata:
              logging.error("with post data")
            else:
              logging.error("without post data")
            logging.error(exc.args)
            logging.error(traceback.format_tb(tb))
            response = ""
        return response 
    

    def get_request_token(self):
        response = self.oauth_request(self.request_token_url())
        token = self.oauth_parse_response(response)
        try:
            self.token = oauth.OAuthConsumer(token['oauth_token'],token['oauth_token_secret'])
            return token
        except:
            raise oauth.OAuthError('Invalid oauth_token')

    def oauth_parse_response(self, response_string):
        r = {}
        for param in response_string.split("&"):
            pair = param.split("=")
            if (len(pair)!=2):
                break
                
            r[pair[0]]=pair[1]
        return r

    def get_authorize_url(self, token):
        return self.authorize_url() + '?oauth_token=' +token

    def get_authenticate_url(self, token):
        return self.authenticate_url() + '?oauth_token=' +token

    def get_access_token(self,token=None,verifier=None):
        if verifier:
            r = self.oauth_request(self.access_token_url(), args={'oauth_verifier': verifier})
        else:
            r = self.oauth_request(self.access_token_url())
        token = self.oauth_parse_response(r)
        self.token = oauth.OAuthConsumer(token['oauth_token'],token['oauth_token_secret'])
        return token

    def oauth_request(self, url, args={}, method=None):
        if (method==None):
            if args=={}:
                method = "GET"
            else:
                method = "POST"
        req = oauth.OAuthRequest.from_consumer_and_token(self.consumer, self.token, method, url, args)
        req.sign_request(self.sha1_method, self.consumer,self.token)
        if (method=="GET"):
            return self.http_wrapper(req.to_url())
        elif (method == "POST"):
            return self.http_wrapper(req.get_normalized_http_url(),req.to_postdata())

        
##
## the code below needs to be updated to take into account not just Twitter
##

if __name__ == '__main__':
    consumer_key = ''
    consumer_secret = ''
    while not consumer_key:
        consumer_key = raw_input('Please enter consumer key: ')
    while not consumer_secret:
        consumer_secret = raw_input('Please enter consumer secret: ')
    auth_client = LoginOAuthClient(consumer_key,consumer_secret)
    tok = auth_client.get_request_token()
    token = tok['oauth_token']
    token_secret = tok['oauth_token_secret']
    url = auth_client.get_authorize_url(token) 
    webbrowser.open(url)
    print "Visit this URL to authorize your app: " + url
    response_token = raw_input('What is the oauth_token from twitter: ')
    response_client = LoginOAuthClient(consumer_key, consumer_secret,token, token_secret, server_params={})
    tok = response_client.get_access_token()
    print "Making signed request"
    #verify user access
    content = response_client.oauth_request('https://twitter.com/account/verify_credentials.json', method='POST')
    #make an update
    #content = response_client.oauth_request('https://twitter.com/statuses/update.xml', {'status':'Updated from a python oauth client. awesome.'}, method='POST')
    print content
   
    print 'Done.'



########NEW FILE########
__FILENAME__ = rsa
#!/usr/bin/python

"""
requires tlslite - http://trevp.net/tlslite/

"""

import binascii

from gdata.tlslite.utils import keyfactory
from gdata.tlslite.utils import cryptomath

# XXX andy: ugly local import due to module name, oauth.oauth
import gdata.oauth as oauth

class OAuthSignatureMethod_RSA_SHA1(oauth.OAuthSignatureMethod):
  def get_name(self):
    return "RSA-SHA1"

  def _fetch_public_cert(self, oauth_request):
    # not implemented yet, ideas are:
    # (1) do a lookup in a table of trusted certs keyed off of consumer
    # (2) fetch via http using a url provided by the requester
    # (3) some sort of specific discovery code based on request
    #
    # either way should return a string representation of the certificate
    raise NotImplementedError

  def _fetch_private_cert(self, oauth_request):
    # not implemented yet, ideas are:
    # (1) do a lookup in a table of trusted certs keyed off of consumer
    #
    # either way should return a string representation of the certificate
    raise NotImplementedError

  def build_signature_base_string(self, oauth_request, consumer, token):
      sig = (
          oauth.escape(oauth_request.get_normalized_http_method()),
          oauth.escape(oauth_request.get_normalized_http_url()),
          oauth.escape(oauth_request.get_normalized_parameters()),
      )
      key = ''
      raw = '&'.join(sig)
      return key, raw

  def build_signature(self, oauth_request, consumer, token):
    key, base_string = self.build_signature_base_string(oauth_request,
                                                        consumer,
                                                        token)

    # Fetch the private key cert based on the request
    cert = self._fetch_private_cert(oauth_request)

    # Pull the private key from the certificate
    privatekey = keyfactory.parsePrivateKey(cert)
    
    # Convert base_string to bytes
    #base_string_bytes = cryptomath.createByteArraySequence(base_string)
    
    # Sign using the key
    signed = privatekey.hashAndSign(base_string)
  
    return binascii.b2a_base64(signed)[:-1]
  
  def check_signature(self, oauth_request, consumer, token, signature):
    decoded_sig = base64.b64decode(signature);

    key, base_string = self.build_signature_base_string(oauth_request,
                                                        consumer,
                                                        token)

    # Fetch the public key cert based on the request
    cert = self._fetch_public_cert(oauth_request)

    # Pull the public key from the certificate
    publickey = keyfactory.parsePEMKey(cert, public=True)

    # Check the signature
    ok = publickey.hashAndVerify(decoded_sig, base_string)

    return ok


class TestOAuthSignatureMethod_RSA_SHA1(OAuthSignatureMethod_RSA_SHA1):
  def _fetch_public_cert(self, oauth_request):
    cert = """
-----BEGIN CERTIFICATE-----
MIIBpjCCAQ+gAwIBAgIBATANBgkqhkiG9w0BAQUFADAZMRcwFQYDVQQDDA5UZXN0
IFByaW5jaXBhbDAeFw03MDAxMDEwODAwMDBaFw0zODEyMzEwODAwMDBaMBkxFzAV
BgNVBAMMDlRlc3QgUHJpbmNpcGFsMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKB
gQC0YjCwIfYoprq/FQO6lb3asXrxLlJFuCvtinTF5p0GxvQGu5O3gYytUvtC2JlY
zypSRjVxwxrsuRcP3e641SdASwfrmzyvIgP08N4S0IFzEURkV1wp/IpH7kH41Etb
mUmrXSwfNZsnQRE5SYSOhh+LcK2wyQkdgcMv11l4KoBkcwIDAQABMA0GCSqGSIb3
DQEBBQUAA4GBAGZLPEuJ5SiJ2ryq+CmEGOXfvlTtEL2nuGtr9PewxkgnOjZpUy+d
4TvuXJbNQc8f4AMWL/tO9w0Fk80rWKp9ea8/df4qMq5qlFWlx6yOLQxumNOmECKb
WpkUQDIDJEoFUzKMVuJf4KO/FJ345+BNLGgbJ6WujreoM1X/gYfdnJ/J
-----END CERTIFICATE-----
"""
    return cert

  def _fetch_private_cert(self, oauth_request):
    cert = """
-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALRiMLAh9iimur8V
A7qVvdqxevEuUkW4K+2KdMXmnQbG9Aa7k7eBjK1S+0LYmVjPKlJGNXHDGuy5Fw/d
7rjVJ0BLB+ubPK8iA/Tw3hLQgXMRRGRXXCn8ikfuQfjUS1uZSatdLB81mydBETlJ
hI6GH4twrbDJCR2Bwy/XWXgqgGRzAgMBAAECgYBYWVtleUzavkbrPjy0T5FMou8H
X9u2AC2ry8vD/l7cqedtwMPp9k7TubgNFo+NGvKsl2ynyprOZR1xjQ7WgrgVB+mm
uScOM/5HVceFuGRDhYTCObE+y1kxRloNYXnx3ei1zbeYLPCHdhxRYW7T0qcynNmw
rn05/KO2RLjgQNalsQJBANeA3Q4Nugqy4QBUCEC09SqylT2K9FrrItqL2QKc9v0Z
zO2uwllCbg0dwpVuYPYXYvikNHHg+aCWF+VXsb9rpPsCQQDWR9TT4ORdzoj+Nccn
qkMsDmzt0EfNaAOwHOmVJ2RVBspPcxt5iN4HI7HNeG6U5YsFBb+/GZbgfBT3kpNG
WPTpAkBI+gFhjfJvRw38n3g/+UeAkwMI2TJQS4n8+hid0uus3/zOjDySH3XHCUno
cn1xOJAyZODBo47E+67R4jV1/gzbAkEAklJaspRPXP877NssM5nAZMU0/O/NGCZ+
3jPgDUno6WbJn5cqm8MqWhW1xGkImgRk+fkDBquiq4gPiT898jusgQJAd5Zrr6Q8
AO/0isr/3aa6O6NLQxISLKcPDk2NOccAfS/xOtfOz4sJYM3+Bs4Io9+dZGSDCA54
Lw03eHTNQghS0A==
-----END PRIVATE KEY-----
"""
    return cert

########NEW FILE########
__FILENAME__ = util

"""
Utility code for the Django example consumer and server.
"""

from urlparse import urljoin

from django.db import connection
from django.template.context import RequestContext
from django.template import loader
from django import http
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse as reverseURL
from django.views.generic.simple import direct_to_template

from django.conf import settings

from openid.store.filestore import FileOpenIDStore
from openid.store import sqlstore
from openid.yadis.constants import YADIS_CONTENT_TYPE

def getOpenIDStore(filestore_path, table_prefix):
    """
    Returns an OpenID association store object based on the database
    engine chosen for this Django application.

    * If no database engine is chosen, a filesystem-based store will
      be used whose path is filestore_path.

    * If a database engine is chosen, a store object for that database
      type will be returned.

    * If the chosen engine is not supported by the OpenID library,
      raise ImproperlyConfigured.

    * If a database store is used, this will create the tables
      necessary to use it.  The table names will be prefixed with
      table_prefix.  DO NOT use the same table prefix for both an
      OpenID consumer and an OpenID server in the same database.

    The result of this function should be passed to the Consumer
    constructor as the store parameter.
    """

    db_engine = settings.DATABASES['default']['ENGINE']
    if not db_engine:
        return FileOpenIDStore(filestore_path)

    # get the suffix
    db_engine = db_engine.split('.')[-1]

    # Possible side-effect: create a database connection if one isn't
    # already open.
    connection.cursor()

    # Create table names to specify for SQL-backed stores.
    tablenames = {
        'associations_table': table_prefix + 'openid_associations',
        'nonces_table': table_prefix + 'openid_nonces',
        }

    types = {
        'postgresql': sqlstore.PostgreSQLStore,
        'postgresql_psycopg2': sqlstore.PostgreSQLStore,
        'mysql': sqlstore.MySQLStore,
        'sqlite3': sqlstore.SQLiteStore,
        }

    try:
        s = types[db_engine](connection.connection,
                                            **tablenames)
    except KeyError:
        raise ImproperlyConfigured, \
              "Database engine %s not supported by OpenID library" % \
              (db_engine,)

    try:
        s.createTables()
    except (SystemExit, KeyboardInterrupt, MemoryError), e:
        raise
    except:
        # XXX This is not the Right Way to do this, but because the
        # underlying database implementation might differ in behavior
        # at this point, we can't reliably catch the right
        # exception(s) here.  Ideally, the SQL store in the OpenID
        # library would catch exceptions that it expects and fail
        # silently, but that could be bad, too.  More ideally, the SQL
        # store would not attempt to create tables it knows already
        # exists.
        pass

    return s

def getViewURL(req, view_name_or_obj, args=None, kwargs=None):
    relative_url = reverseURL(view_name_or_obj, args=args, kwargs=kwargs)
    full_path = req.META.get('SCRIPT_NAME', '') + relative_url
    return urljoin(getBaseURL(req), full_path)

def getBaseURL(req):
    """
    Given a Django web request object, returns the OpenID 'trust root'
    for that request; namely, the absolute URL to the site root which
    is serving the Django request.  The trust root will include the
    proper scheme and authority.  It will lack a port if the port is
    standard (80, 443).
    """
    name = req.META['HTTP_HOST']
    try:
        name = name[:name.index(':')]
    except:
        pass

    try:
        port = int(req.META['SERVER_PORT'])
    except:
        port = 80

    proto = req.META['SERVER_PROTOCOL']

    if 'HTTPS' in proto:
        proto = 'https'
    else:
        proto = 'http'

    if port in [80, 443] or not port:
        port = ''
    else:
        port = ':%s' % (port,)

    url = "%s://%s%s/" % (proto, name, port)
    return url

def normalDict(request_data):
    """
    Converts a django request MutliValueDict (e.g., request.GET,
    request.POST) into a standard python dict whose values are the
    first value from each of the MultiValueDict's value lists.  This
    avoids the OpenID library's refusal to deal with dicts whose
    values are lists, because in OpenID, each key in the query arg set
    can have at most one value.
    """
    return dict((k, v[0]) for k, v in request_data.iteritems())

def renderXRDS(request, type_uris, endpoint_urls):
    """Render an XRDS page with the specified type URIs and endpoint
    URLs in one service block, and return a response with the
    appropriate content-type.
    """
    response = direct_to_template(
        request, 'xrds.xml',
        {'type_uris':type_uris, 'endpoint_urls':endpoint_urls,})
    response['Content-Type'] = YADIS_CONTENT_TYPE
    return response

########NEW FILE########
__FILENAME__ = view_helpers

from django import http
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template

from openid.consumer import consumer
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import ax, pape, sreg
from openid.yadis.constants import YADIS_HEADER_NAME, YADIS_CONTENT_TYPE
from openid.server.trustroot import RP_RETURN_TO_URL_TYPE

import util

PAPE_POLICIES = [
    'AUTH_PHISHING_RESISTANT',
    'AUTH_MULTI_FACTOR',
    'AUTH_MULTI_FACTOR_PHYSICAL',
    ]

AX_REQUIRED_FIELDS = {
    'firstname' : 'http://axschema.org/namePerson/first',
    'lastname' : 'http://axschema.org/namePerson/last',
    'fullname' : 'http://axschema.org/namePerson',
    'email' : 'http://axschema.org/contact/email'
}

# List of (name, uri) for use in generating the request form.
POLICY_PAIRS = [(p, getattr(pape, p))
                for p in PAPE_POLICIES]

def getOpenIDStore():
    """
    Return an OpenID store object fit for the currently-chosen
    database backend, if any.
    """
    return util.getOpenIDStore('/tmp/djopenid_c_store', 'c_')

def get_consumer(session):
    """
    Get a Consumer object to perform OpenID authentication.
    """
    return consumer.Consumer(session, getOpenIDStore())

def start_openid(session, openid_url, trust_root, return_to):
    """
    Start the OpenID authentication process.

    * Requests some Simple Registration data using the OpenID
      library's Simple Registration machinery

    * Generates the appropriate trust root and return URL values for
      this application (tweak where appropriate)

    * Generates the appropriate redirect based on the OpenID protocol
      version.
    """

    # Start OpenID authentication.
    c = get_consumer(session)
    error = None

    try:
        auth_request = c.begin(openid_url)
    except DiscoveryFailure, e:
        # Some other protocol-level failure occurred.
        error = "OpenID discovery error: %s" % (str(e),)

    if error:
        import pdb; pdb.set_trace()
        raise Exception("error in openid")

    # Add Simple Registration request information.  Some fields
    # are optional, some are required.  It's possible that the
    # server doesn't support sreg or won't return any of the
    # fields.
    sreg_request = sreg.SRegRequest(required=['email'],
                                    optional=[])
    auth_request.addExtension(sreg_request)

    # Add Attribute Exchange request information.
    ax_request = ax.FetchRequest()
    # XXX - uses myOpenID-compatible schema values, which are
    # not those listed at axschema.org.

    for k, v in AX_REQUIRED_FIELDS.iteritems():
        ax_request.add(ax.AttrInfo(v, required=True))

    auth_request.addExtension(ax_request)
                
    # Compute the trust root and return URL values to build the
    # redirect information.
    # trust_root = util.getViewURL(request, startOpenID)
    # return_to = util.getViewURL(request, finishOpenID)

    # Send the browser to the server either by sending a redirect
    # URL or by generating a POST form.
    url = auth_request.redirectURL(trust_root, return_to)
    return url

def finish_openid(session, request_args, return_to):
    """
    Finish the OpenID authentication process.  Invoke the OpenID
    library with the response from the OpenID server and render a page
    detailing the result.
    """
    result = {}

    # Because the object containing the query parameters is a
    # MultiValueDict and the OpenID library doesn't allow that, we'll
    # convert it to a normal dict.

    if request_args:
        c = get_consumer(session)

        # Get a response object indicating the result of the OpenID
        # protocol.
        response = c.complete(request_args, return_to)

        # Get a Simple Registration response object if response
        # information was included in the OpenID response.
        sreg_response = {}
        ax_items = {}
        if response.status == consumer.SUCCESS:
            sreg_response = sreg.SRegResponse.fromSuccessResponse(response)

            ax_response = ax.FetchResponse.fromSuccessResponse(response)
            if ax_response:
                for k, v in AX_REQUIRED_FIELDS.iteritems():
                    """
                    the values are the URIs, they are the key into the data
                    the key is the shortname
                    """
                    if ax_response.data.has_key(v):
                        ax_items[k] = ax_response.get(v)

        # Map different consumer status codes to template contexts.
        results = {
            consumer.CANCEL:
            {'message': 'OpenID authentication cancelled.'},

            consumer.FAILURE:
            {'error': 'OpenID authentication failed.'},

            consumer.SUCCESS:
            {'url': response.getDisplayIdentifier(),
             'sreg': sreg_response and sreg_response.items(),
             'ax': ax_items}
            }

        result = results[response.status]

        if isinstance(response, consumer.FailureResponse):
            # In a real application, this information should be
            # written to a log for debugging/tracking OpenID
            # authentication failures. In general, the messages are
            # not user-friendly, but intended for developers.
            result['failure_reason'] = response.message

    return result


########NEW FILE########
__FILENAME__ = password
"""
Username/Password Authentication
"""

from django.core.urlresolvers import reverse
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect

import logging

# some parameters to indicate that status updating is possible
STATUS_UPDATES = False


def create_user(username, password, name = None):
  from helios_auth.models import User
  
  user = User.get_by_type_and_id('password', username)
  if user:
    raise Exception('user exists')
  
  info = {'password' : password, 'name': name}
  user = User.update_or_create(user_type='password', user_id=username, info = info)
  user.save()

class LoginForm(forms.Form):
  username = forms.CharField(max_length=50)
  password = forms.CharField(widget=forms.PasswordInput(), max_length=100)

def password_check(user, password):
  return (user and user.info['password'] == password)
  
# the view for logging in
def password_login_view(request):
  from helios_auth.view_utils import render_template
  from helios_auth.views import after
  from helios_auth.models import User

  error = None
  
  if request.method == "GET":
    form = LoginForm()
  else:
    form = LoginForm(request.POST)

    # set this in case we came here straight from the multi-login chooser
    # and thus did not have a chance to hit the "start/password" URL
    request.session['auth_system_name'] = 'password'
    if request.POST.has_key('return_url'):
      request.session['auth_return_url'] = request.POST.get('return_url')

    if form.is_valid():
      username = form.cleaned_data['username'].strip()
      password = form.cleaned_data['password'].strip()
      try:
        user = User.get_by_type_and_id('password', username)
        if password_check(user, password):
          request.session['password_user'] = user
          return HttpResponseRedirect(reverse(after))
      except User.DoesNotExist:
        pass
      error = 'Bad Username or Password'
  
  return render_template(request, 'password/login', {'form': form, 'error': error})
    
def password_forgotten_view(request):
  """
  forgotten password view and submit.
  includes return_url
  """
  from helios_auth.view_utils import render_template
  from helios_auth.models import User

  if request.method == "GET":
    return render_template(request, 'password/forgot', {'return_url': request.GET.get('return_url', '')})
  else:
    username = request.POST['username']
    return_url = request.POST['return_url']
    
    try:
      user = User.get_by_type_and_id('password', username)
    except User.DoesNotExist:
      return render_template(request, 'password/forgot', {'return_url': request.GET.get('return_url', ''), 'error': 'no such username'})
    
    body = """

This is a password reminder:

Your username: %s
Your password: %s

--
%s
""" % (user.user_id, user.info['password'], settings.SITE_TITLE)

    # FIXME: make this a task
    send_mail('password reminder', body, settings.SERVER_EMAIL, ["%s <%s>" % (user.info['name'], user.info['email'])], fail_silently=False)
    
    return HttpResponseRedirect(return_url)
  
def get_auth_url(request, redirect_url = None):
  return reverse(password_login_view)
    
def get_user_info_after_auth(request):
  user = request.session['password_user']
  del request.session['password_user']
  user_info = user.info
  
  return {'type': 'password', 'user_id' : user.user_id, 'name': user.name, 'info': user.info, 'token': None}
    
def update_status(token, message):
  pass
  
def send_message(user_id, user_name, user_info, subject, body):
  email = user_id
  name = user_name or user_info.get('name', email)
  send_mail(subject, body, settings.SERVER_EMAIL, ["\"%s\" <%s>" % (name, email)], fail_silently=False)    

########NEW FILE########
__FILENAME__ = twitter
"""
Twitter Authentication
"""

from oauthclient import client

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from helios_auth import utils

import logging

from django.conf import settings
API_KEY = settings.TWITTER_API_KEY
API_SECRET = settings.TWITTER_API_SECRET
USER_TO_FOLLOW = settings.TWITTER_USER_TO_FOLLOW
REASON_TO_FOLLOW = settings.TWITTER_REASON_TO_FOLLOW
DM_TOKEN = settings.TWITTER_DM_TOKEN

# some parameters to indicate that status updating is possible
STATUS_UPDATES = True
STATUS_UPDATE_WORDING_TEMPLATE = "Tweet %s"

OAUTH_PARAMS = {
  'root_url' : 'https://twitter.com',
  'request_token_path' : '/oauth/request_token',
  'authorize_path' : '/oauth/authorize',
  'authenticate_path' : '/oauth/authenticate',
  'access_token_path': '/oauth/access_token'
}

def _get_new_client(token=None, token_secret=None):
  if token:
    return client.LoginOAuthClient(API_KEY, API_SECRET, OAUTH_PARAMS, token, token_secret)
  else:
    return client.LoginOAuthClient(API_KEY, API_SECRET, OAUTH_PARAMS)

def _get_client_by_token(token):
  return _get_new_client(token['oauth_token'], token['oauth_token_secret'])

def get_auth_url(request, redirect_url):
  client = _get_new_client()
  try:
    tok = client.get_request_token()
  except:
    return None
  
  request.session['request_token'] = tok
  url = client.get_authenticate_url(tok['oauth_token']) 
  return url
    
def get_user_info_after_auth(request):
  tok = request.session['request_token']
  twitter_client = _get_client_by_token(tok)
  access_token = twitter_client.get_access_token()
  request.session['access_token'] = access_token
    
  user_info = utils.from_json(twitter_client.oauth_request('http://api.twitter.com/1/account/verify_credentials.json', args={}, method='GET'))
  
  return {'type': 'twitter', 'user_id' : user_info['screen_name'], 'name': user_info['name'], 'info': user_info, 'token': access_token}
    

def user_needs_intervention(user_id, user_info, token):
  """
  check to see if user is following the users we need
  """
  twitter_client = _get_client_by_token(token)
  friendship = utils.from_json(twitter_client.oauth_request('http://api.twitter.com/1/friendships/exists.json', args={'user_a': user_id, 'user_b': USER_TO_FOLLOW}, method='GET'))
  if friendship:
    return None

  return HttpResponseRedirect(reverse(follow_view))

def _get_client_by_request(request):
  access_token = request.session['access_token']
  return _get_client_by_token(access_token)
  
def update_status(user_id, user_info, token, message):
  """
  post a message to the auth system's update stream, e.g. twitter stream
  """
  twitter_client = _get_client_by_token(token)
  result = twitter_client.oauth_request('http://api.twitter.com/1/statuses/update.json', args={'status': message}, method='POST')

def send_message(user_id, user_name, user_info, subject, body):
  pass

def public_url(user_id):
  return "http://twitter.com/%s" % user_id

def send_notification(user_id, user_info, message):
  twitter_client = _get_client_by_token(DM_TOKEN)
  result = twitter_client.oauth_request('http://api.twitter.com/1/direct_messages/new.json', args={'screen_name': user_id, 'text': message}, method='POST')

##
## views
##

def follow_view(request):
  if request.method == "GET":
    from helios_auth.view_utils import render_template
    from helios_auth.views import after
    
    return render_template(request, 'twitter/follow', {'user_to_follow': USER_TO_FOLLOW, 'reason_to_follow' : REASON_TO_FOLLOW})

  if request.method == "POST":
    follow_p = bool(request.POST.get('follow_p',False))
    
    if follow_p:
      from helios_auth.security import get_user

      user = get_user(request)
      twitter_client = _get_client_by_token(user.token)
      result = twitter_client.oauth_request('http://api.twitter.com/1/friendships/create.json', args={'screen_name': USER_TO_FOLLOW}, method='POST')

    from helios_auth.views import after_intervention
    return HttpResponseRedirect(reverse(after_intervention))



########NEW FILE########
__FILENAME__ = yahoo
"""
Yahoo Authentication

"""

from django.http import *
from django.core.mail import send_mail
from django.conf import settings

import sys, os, cgi, urllib, urllib2, re
from xml.etree import ElementTree

from openid import view_helpers

# some parameters to indicate that status updating is not possible
STATUS_UPDATES = False

# display tweaks
LOGIN_MESSAGE = "Log in with my Yahoo Account"
OPENID_ENDPOINT = 'yahoo.com'

def get_auth_url(request, redirect_url):
  request.session['yahoo_redirect_url'] = redirect_url
  url = view_helpers.start_openid(request.session, OPENID_ENDPOINT, redirect_url, redirect_url)
  return url

def get_user_info_after_auth(request):
  data = view_helpers.finish_openid(request.session, request.GET, request.session['yahoo_redirect_url'])

  return {'type' : 'yahoo', 'user_id': data['ax']['email'][0], 'name': data['ax']['fullname'][0], 'info': {'email': data['ax']['email'][0]}, 'token':{}}
    
def do_logout(user):
  """
  logout of Yahoo
  """
  return None
  
def update_status(token, message):
  """
  simple update
  """
  pass

def send_message(user_id, user_name, user_info, subject, body):
  """
  send email to yahoo user, user_id is email for yahoo and other openID logins.
  """
  send_mail(subject, body, settings.SERVER_EMAIL, ["%s <%s>" % (user_name, user_id)], fail_silently=False)
  
def check_constraint(constraint, user_info):
  """
  for eligibility
  """
  pass

########NEW FILE########
__FILENAME__ = jsonfield
"""
taken from

http://www.djangosnippets.org/snippets/377/
"""

import datetime
from django.db import models
from django.db.models import signals
from django.conf import settings
from django.utils import simplejson as json
from django.core.serializers.json import DjangoJSONEncoder

class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    
    deserialization_params added on 2011-01-09 to provide additional hints at deserialization time
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def __init__(self, json_type=None, deserialization_params=None, **kwargs):
        self.json_type = json_type
        self.deserialization_params = deserialization_params
        super(JSONField, self).__init__(**kwargs)

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if self.json_type:
            if isinstance(value, self.json_type):
                return value

        if isinstance(value, dict) or isinstance(value, list):
            return value

        if value == "" or value == None:
            return None

        try:
            parsed_value = json.loads(value)
        except:
            raise Exception("not JSON")

        if self.json_type and parsed_value:
            parsed_value = self.json_type.fromJSONDict(parsed_value, **self.deserialization_params)
                
        return parsed_value

    # we should never look up by JSON field anyways.
    # def get_prep_lookup(self, lookup_type, value)

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        if isinstance(value, basestring):
            return value

        if value == None:
            return None

        if self.json_type and isinstance(value, self.json_type):
            the_dict = value.toJSONDict()
        else:
            the_dict = value

        return json.dumps(the_dict, cls=DjangoJSONEncoder)


    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)        

##
## for schema migration, we have to tell South about JSONField
## basically that it's the same as its parent class
##
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^helios_auth\.jsonfield\.JSONField"])

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'User'
        db.create_table('helios_auth_user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('user_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('info', self.gf('helios_auth.jsonfield.JSONField')()),
            ('token', self.gf('helios_auth.jsonfield.JSONField')(null=True)),
            ('admin_p', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('helios_auth', ['User'])

        # Adding unique constraint on 'User', fields ['user_type', 'user_id']
        db.create_unique('helios_auth_user', ['user_type', 'user_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'User', fields ['user_type', 'user_id']
        db.delete_unique('helios_auth_user', ['user_type', 'user_id'])

        # Deleting model 'User'
        db.delete_table('helios_auth_user')


    models = {
        'helios_auth.user': {
            'Meta': {'unique_together': "(('user_type', 'user_id'),)", 'object_name': 'User'},
            'admin_p': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('helios_auth.jsonfield.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'token': ('helios_auth.jsonfield.JSONField', [], {'null': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['helios_auth']

########NEW FILE########
__FILENAME__ = models
"""
Data Objects for user authentication

GAE

Ben Adida
(ben@adida.net)
"""

from django.db import models
from jsonfield import JSONField

import datetime, logging

from auth_systems import AUTH_SYSTEMS, can_check_constraint, can_list_categories

# an exception to catch when a user is no longer authenticated
class AuthenticationExpired(Exception):
  pass

class User(models.Model):
  user_type = models.CharField(max_length=50)
  user_id = models.CharField(max_length=100)
    
  name = models.CharField(max_length=200, null=True)
  
  # other properties
  info = JSONField()
  
  # access token information
  token = JSONField(null = True)
  
  # administrator
  admin_p = models.BooleanField(default=False)

  class Meta:
    unique_together = (('user_type', 'user_id'),)
    
  @classmethod
  def _get_type_and_id(cls, user_type, user_id):
    return "%s:%s" % (user_type, user_id)    
    
  @property
  def type_and_id(self):
    return self._get_type_and_id(self.user_type, self.user_id)
    
  @classmethod
  def get_by_type_and_id(cls, user_type, user_id):
    return cls.objects.get(user_type = user_type, user_id = user_id)
  
  @classmethod
  def update_or_create(cls, user_type, user_id, name=None, info=None, token=None):
    obj, created_p = cls.objects.get_or_create(user_type = user_type, user_id = user_id, defaults = {'name': name, 'info':info, 'token':token})
    
    if not created_p:
      # special case the password: don't replace it if it exists
      if obj.info.has_key('password'):
        info['password'] = obj.info['password']

      obj.info = info
      obj.name = name
      obj.token = token
      obj.save()

    return obj
    
  def can_update_status(self):
    if not AUTH_SYSTEMS.has_key(self.user_type):
      return False

    return AUTH_SYSTEMS[self.user_type].STATUS_UPDATES

  def update_status_template(self):
    if not self.can_update_status():
      return None

    return AUTH_SYSTEMS[self.user_type].STATUS_UPDATE_WORDING_TEMPLATE

  def update_status(self, status):
    if AUTH_SYSTEMS.has_key(self.user_type):
      AUTH_SYSTEMS[self.user_type].update_status(self.user_id, self.info, self.token, status)
      
  def send_message(self, subject, body):
    if AUTH_SYSTEMS.has_key(self.user_type):
      subject = subject.split("\n")[0]
      AUTH_SYSTEMS[self.user_type].send_message(self.user_id, self.name, self.info, subject, body)

  def send_notification(self, message):
    if AUTH_SYSTEMS.has_key(self.user_type):
      if hasattr(AUTH_SYSTEMS[self.user_type], 'send_notification'):
        AUTH_SYSTEMS[self.user_type].send_notification(self.user_id, self.info, message)
  
  def is_eligible_for(self, eligibility_case):
    """
    Check if this user is eligible for this particular eligibility case, which looks like
    {'auth_system': 'cas', 'constraint': [{}, {}, {}]}
    and the constraints are OR'ed together
    """
    
    if eligibility_case['auth_system'] != self.user_type:
      return False
      
    # no constraint? Then eligible!
    if not eligibility_case.has_key('constraint'):
      return True
    
    # from here on we know we match the auth system, but do we match one of the constraints?  

    auth_system = AUTH_SYSTEMS[self.user_type]

    # does the auth system allow for checking a constraint?
    if not hasattr(auth_system, 'check_constraint'):
      return False
      
    for constraint in eligibility_case['constraint']:
      # do we match on this constraint?
      if auth_system.check_constraint(constraint=constraint, user = self):
        return True
  
    # no luck
    return False
    
  def __eq__(self, other):
    if other:
      return self.type_and_id == other.type_and_id
    else:
      return False
  

  @property
  def pretty_name(self):
    if self.name:
      return self.name

    if self.info.has_key('name'):
      return self.info['name']

    return self.user_id
  
  @property
  def public_url(self):
    if AUTH_SYSTEMS.has_key(self.user_type):
      if hasattr(AUTH_SYSTEMS[self.user_type], 'public_url'):
        return AUTH_SYSTEMS[self.user_type].public_url(self.user_id)

    return None
    
  def _display_html(self, size):
    public_url = self.public_url
    
    if public_url:
      name_display = '<a href="%s">%s</a>' % (public_url, self.pretty_name)
    else:
      name_display = self.pretty_name

    return """<img class="%s-logo" src="/static/auth/login-icons/%s.png" alt="%s" /> %s""" % (
      size, self.user_type, self.user_type, name_display)

  @property
  def display_html_small(self):
    return self._display_html('small')

  @property
  def display_html_big(self):
    return self._display_html('big')

########NEW FILE########
__FILENAME__ = oauth
"""
Initially downlaoded from
http://oauth.googlecode.com/svn/code/python/oauth/

Hacked a bit by Ben Adida (ben@adida.net) so that:
- access tokens are looked up with an extra param of consumer
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import base64
import logging
import hashlib

VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'

# Generic exception class
class OAuthError(RuntimeError):
    def __init__(self, message='OAuth error occured.'):
        self.message = message

# optional WWW-Authenticate header (401 error)
def build_authenticate_header(realm=''):
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

# url escape
def escape(s):
    # escape '/' too
    return urllib.quote(s, safe='~')

# util function: current timestamp
# seconds since epoch (UTC)
def generate_timestamp():
    return int(time.time())

# util function: nonce
# pseudorandom number
def generate_nonce(length=8):
    return ''.join(str(random.randint(0, 9)) for i in range(length))

# OAuthConsumer is a data type that represents the identity of the Consumer
# via its shared secret with the Service Provider.
class OAuthConsumer(object):
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

# OAuthToken is a data type that represents an End User via either an access
# or request token.     
class OAuthToken(object):
    # access tokens and request tokens
    key = None
    secret = None

    '''
    key = the token
    secret = the token secret
    '''
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def to_string(self):
        return urllib.urlencode({'oauth_token': self.key, 'oauth_token_secret': self.secret})

    # return a token from something like:
    # oauth_token_secret=digg&oauth_token=digg
    @staticmethod   
    def from_string(s):
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        return OAuthToken(key, secret)

    def __str__(self):
        return self.to_string()

# OAuthRequest represents the request and can be serialized
class OAuthRequest(object):
    '''
    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        ... any additional parameters, as defined by the Service Provider.
    '''
    parameters = None # oauth parameters
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION
    
    # added by Ben to filter out extra params from header
    OAUTH_PARAMS = ['oauth_consumer_key', 'oauth_token', 'oauth_signature_method', 'oauth_signature', 'oauth_timestamp', 'oauth_nonce', 'oauth_version']

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter('oauth_nonce')

    # get any non-oauth parameters
    def get_nonoauth_parameters(self):
        parameters = {}
        for k, v in self.parameters.iteritems():
            # ignore oauth parameters
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    # serialize as a header for an HTTPAuth request
    def to_header(self, realm=''):
        auth_header = 'OAuth realm="%s"' % realm
        # add the oauth parameters
        if self.parameters:
            for k, v in self.parameters.iteritems():
              # only if it's a standard OAUTH param (Ben)
              if k in self.OAUTH_PARAMS:
                auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    # serialize as post data for a POST request
    def to_postdata(self):
        return '&'.join('%s=%s' % (escape(str(k)), escape(str(v))) for k, v in self.parameters.iteritems())

    # serialize as a url for a GET request
    def to_url(self):
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    # return a string that consists of all the parameters that need to be signed
    def get_normalized_parameters(self):
        params = self.parameters
        try:
            # exclude the signature if it exists
            del params['oauth_signature']
        except:
            pass
        key_values = params.items()
        # sort lexicographically, first after key, then after value
        key_values.sort()
        # combine key value pairs in string and escape
        return '&'.join('%s=%s' % (escape(str(k)), escape(str(v))) for k, v in key_values)

    # just uppercases the http method
    def get_normalized_http_method(self):
        return self.http_method.upper()

    # parses the url and rebuilds it to be scheme://host/path
    def get_normalized_http_url(self):
        parts = urlparse.urlparse(self.http_url)
        url_string = '%s://%s%s' % (parts[0], parts[1], parts[2]) # scheme, netloc, path
        return url_string
        
    # set the signature parameter to the result of build_signature
    def sign_request(self, signature_method, consumer, token):
        # set the signature method
        self.set_parameter('oauth_signature_method', signature_method.get_name())
        # set the signature
        self.set_parameter('oauth_signature', self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        # call the build signature method within the signature method
        return signature_method.build_signature(self, consumer, token)

    @staticmethod
    def from_request(http_method, http_url, headers=None, parameters=None, query_string=None):
        # combine multiple parameter sources
        if parameters is None:
            parameters = {}

        # headers
        if headers and 'HTTP_AUTHORIZATION' in headers:
            auth_header = headers['HTTP_AUTHORIZATION']
            # check that the authorization header is OAuth
            if auth_header.index('OAuth') > -1:
                try:
                    # get the parameters from the header
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from Authorization header.')

        # GET or POST query string
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None

    @staticmethod
    def from_consumer_and_token(oauth_consumer, token=None, http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key

        return OAuthRequest(http_method, http_url, parameters)

    @staticmethod
    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = escape(callback)

        return OAuthRequest(http_method, http_url, parameters)

    # util function: turn Authorization: header into parameters, has to do some unescaping
    @staticmethod
    def _split_header(header):
        params = {}
        parts = header.split(',')
        for param in parts:
            # ignore realm parameter
            if param.find('OAuth realm') > -1:
                continue
            # remove whitespace
            param = param.strip()
            # split key-value
            param_parts = param.split('=', 1)
            # remove quotes and unescape the value
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    
    # util function: turn url string into parameters, has to do some unescaping
    @staticmethod
    def _split_url_string(param_str):
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters

# OAuthServer is a worker to check a requests validity against a data store
class OAuthServer(object):
    timestamp_threshold = 300 # in seconds, five minutes
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, oauth_data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    # process a request_token request
    # returns the request token on success
    def fetch_request_token(self, oauth_request):
        try:
            # get the request token for authorization
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # no token required for the initial token request
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            self._check_signature(oauth_request, consumer, None)
            # fetch a new token
            token = self.data_store.fetch_request_token(consumer)
        return token

    # process an access_token request
    # returns the access token on success
    def fetch_access_token(self, oauth_request):
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # get the request token
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token)
        return new_token

    # verify an api call, checks all the parameters
    def verify_request(self, oauth_request):
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # get the access token
        token = self._get_token(oauth_request, consumer, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    # authorize a request token
    def authorize_token(self, token, user):
        return self.data_store.authorize_request_token(token, user)
    
    # get the callback url
    def get_callback(self, oauth_request):
        return oauth_request.get_parameter('oauth_callback')

    # optional support for the authenticate header   
    def build_authenticate_header(self, realm=''):
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    # verify the correct version request for this server
    def _get_version(self, oauth_request):
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    # figure out the signature with some defaults
    def _get_signature_method(self, oauth_request):
        try:
            signature_method = oauth_request.get_parameter('oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # get the signature method object
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        if not consumer_key:
            raise OAuthError('Invalid consumer key.')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    # try to find the token for the provided request token key
    def _get_token(self, oauth_request, consumer, token_type='access'):
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(consumer, token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # validate the signature
        valid_sig = signature_method.check_signature(oauth_request, consumer, token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        # verify that timestamp is recentish
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a greater difference than threshold %d' % (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        # verify that the nonce is uniqueish
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))

# OAuthClient is a worker to attempt to execute a request
class OAuthClient(object):
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        # -> OAuthToken
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        # -> OAuthToken
        raise NotImplementedError

    def access_resource(self, oauth_request):
        # -> some protected resource
        raise NotImplementedError

# OAuthDataStore is a database abstraction used to lookup consumers and tokens
class OAuthDataStore(object):

    def lookup_consumer(self, key):
        # -> OAuthConsumer
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        # -> OAuthToken
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce, timestamp):
        # -> OAuthToken
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer):
        # -> OAuthToken
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token):
        # -> OAuthToken
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        # -> OAuthToken
        raise NotImplementedError

# OAuthSignatureMethod is a strategy class that implements a signature method
class OAuthSignatureMethod(object):
    def get_name(self):
        # -> str
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        # -> str key, str raw
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        # -> str
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        logging.info("built %s" % built)
        logging.info("signature %s" % signature)
        return built == signature

class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        # build the base signature string
        key, raw = self.build_signature_base_string(oauth_request, consumer, token)

        # hmac object
        hashed = hmac.new(key, raw, hashlib.sha1)

        # calculate the digest base 64
        return base64.b64encode(hashed.digest())

class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        # concatenate the consumer key and secret
        sig = escape(consumer.secret) + '&'
        if token:
            sig = sig + escape(token.secret)
        return sig

    def build_signature(self, oauth_request, consumer, token):
        return self.build_signature_base_string(oauth_request, consumer, token)

########NEW FILE########
__FILENAME__ = tests
"""
Unit Tests for Auth Systems
"""

import unittest
import models

from django.db import IntegrityError, transaction

from django.test.client import Client
from django.test import TestCase

from django.core import mail

from auth_systems import AUTH_SYSTEMS

class UserModelTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_unique_users(self):
        """
        there should not be two users with the same user_type and user_id
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            models.User.objects.create(user_type = auth_system, user_id = 'foobar', info={'name':'Foo Bar'})
            
            def double_insert():
                models.User.objects.create(user_type = auth_system, user_id = 'foobar', info={'name': 'Foo2 Bar'})
                
            self.assertRaises(IntegrityError, double_insert)
            transaction.rollback()

    def test_create_or_update(self):
        """
        shouldn't create two users, and should reset the password
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_cou', info={'name':'Foo Bar'})

            def double_update_or_create():
                new_name = 'Foo2 Bar'
                u2 = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_cou', info={'name': new_name})

                self.assertEquals(u.id, u2.id)
                self.assertEquals(u2.info['name'], new_name)


    def test_status_update(self):
        """
        check that a user set up with status update ability reports it as such,
        and otherwise does not report it
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_status_update', info={'name':'Foo Bar Status Update'})

            if hasattr(auth_system_module, 'send_message'):
                self.assertNotEquals(u.update_status_template, None)
            else:
                self.assertEquals(u.update_status_template, None)

    def test_eligibility(self):
        """
        test that users are reported as eligible for something

        FIXME: also test constraints on eligibility
        """
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_status_update', info={'name':'Foo Bar Status Update'})

            self.assertTrue(u.is_eligible_for({'auth_system': auth_system}))

    def test_eq(self):
        for auth_system, auth_system_module in AUTH_SYSTEMS.iteritems():
            u = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_eq', info={'name':'Foo Bar Status Update'})
            u2 = models.User.update_or_create(user_type = auth_system, user_id = 'foobar_eq', info={'name':'Foo Bar Status Update'})

            self.assertEquals(u, u2)


import views
import auth_systems.password as password_views
from django.core.urlresolvers import reverse

# FIXME: login CSRF should make these tests more complicated
# and should be tested for

class UserBlackboxTests(TestCase):

    def setUp(self):
        # create a bogus user
        self.test_user = models.User.objects.create(user_type='password',user_id='foobar-test@adida.net',name="Foobar User", info={'password':'foobaz'})

    def test_password_login(self):
        ## we can't test this anymore until it's election specific
        pass

        # get to the login page
        # login_page_response = self.client.get(reverse(views.start, kwargs={'system_name':'password'}), follow=True)

        # log in and follow all redirects
        # response = self.client.post(reverse(password_views.password_login_view), {'username' : 'foobar_user', 'password': 'foobaz'}, follow=True)

        # self.assertContains(response, "logged in as")
        # self.assertContains(response, "Foobar User")

    def test_logout(self):
        response = self.client.post(reverse(views.logout), follow=True)
        
        self.assertContains(response, "not logged in")
        self.assertNotContains(response, "Foobar User")

    def test_email(self):
        """using the test email backend"""
        self.test_user.send_message("testing subject", "testing body")

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, "testing subject")
        self.assertEquals(mail.outbox[0].to[0], "\"Foobar User\" <foobar-test@adida.net>")

########NEW FILE########
__FILENAME__ = urls
"""
Authentication URLs

Ben Adida (ben@adida.net)
"""

from django.conf.urls.defaults import *

from views import *
from auth_systems.password import password_login_view, password_forgotten_view
from auth_systems.twitter import follow_view

urlpatterns = patterns('',
    # basic static stuff
    (r'^$', index),
    (r'^logout$', logout),
    (r'^start/(?P<system_name>.*)$', start),
    # weird facebook constraint for trailing slash
    (r'^after/$', after),
    (r'^why$', perms_why),
    (r'^after_intervention$', after_intervention),
    
    ## should make the following modular

    # password auth
    (r'^password/login', password_login_view),
    (r'^password/forgot', password_forgotten_view),

    # twitter
    (r'^twitter/follow', follow_view),
)

########NEW FILE########
__FILENAME__ = utils
"""
Some basic utils 
(previously were in helios module, but making things less interdependent

2010-08-17
"""

from django.utils import simplejson

## JSON
def to_json(d):
  return simplejson.dumps(d, sort_keys=True)
  
def from_json(json_str):
  if not json_str: return None
  return simplejson.loads(json_str)
  
def JSONtoDict(json):
    x=simplejson.loads(json)
    return x
    
def JSONFiletoDict(filename):
  f = open(filename, 'r')
  content = f.read()
  f.close()
  return JSONtoDict(content)
    



########NEW FILE########
__FILENAME__ = views
"""
Views for authentication

Ben Adida
2009-07-05
"""

from django.http import *
from django.core.urlresolvers import reverse

from view_utils import *
from helios_auth.security import get_user

import auth_systems
from auth_systems import AUTH_SYSTEMS
from auth_systems import password
import helios_auth

import copy, urllib

from models import User

from security import FIELDS_TO_SAVE

def index(request):
  """
  the page from which one chooses how to log in.
  """
  
  user = get_user(request)

  # single auth system?
  if len(helios_auth.ENABLED_AUTH_SYSTEMS) == 1 and not user:
    return HttpResponseRedirect(reverse(start, args=[helios_auth.ENABLED_AUTH_SYSTEMS[0]])+ '?return_url=' + request.GET.get('return_url', ''))

  #if helios_auth.DEFAULT_AUTH_SYSTEM and not user:
  #  return HttpResponseRedirect(reverse(start, args=[helios_auth.DEFAULT_AUTH_SYSTEM])+ '?return_url=' + request.GET.get('return_url', ''))
  
  default_auth_system_obj = None
  if helios_auth.DEFAULT_AUTH_SYSTEM:
    default_auth_system_obj = AUTH_SYSTEMS[helios_auth.DEFAULT_AUTH_SYSTEM]

  #form = password.LoginForm()

  return render_template(request,'index', {'return_url' : request.GET.get('return_url', '/'),
                                           'enabled_auth_systems' : helios_auth.ENABLED_AUTH_SYSTEMS,
                                           'default_auth_system': helios_auth.DEFAULT_AUTH_SYSTEM,
                                           'default_auth_system_obj': default_auth_system_obj})

def login_box_raw(request, return_url='/', auth_systems = None):
  """
  a chunk of HTML that shows the various login options
  """
  default_auth_system_obj = None
  if helios_auth.DEFAULT_AUTH_SYSTEM:
    default_auth_system_obj = AUTH_SYSTEMS[helios_auth.DEFAULT_AUTH_SYSTEM]

  # make sure that auth_systems includes only available and enabled auth systems
  if auth_systems != None:
    enabled_auth_systems = set(auth_systems).intersection(set(helios_auth.ENABLED_AUTH_SYSTEMS)).intersection(set(AUTH_SYSTEMS.keys()))
  else:
    enabled_auth_systems = set(helios_auth.ENABLED_AUTH_SYSTEMS).intersection(set(AUTH_SYSTEMS.keys()))

  form = password.LoginForm()

  return render_template_raw(request, 'login_box', {
      'enabled_auth_systems': enabled_auth_systems, 'return_url': return_url,
      'default_auth_system': helios_auth.DEFAULT_AUTH_SYSTEM, 'default_auth_system_obj': default_auth_system_obj,
      'form' : form})
  
def do_local_logout(request):
  """
  if there is a logged-in user, it is saved in the new session's "user_for_remote_logout"
  variable.
  """

  user = None

  if request.session.has_key('user'):
    user = request.session['user']
    
  # 2010-08-14 be much more aggressive here
  # we save a few fields across session renewals,
  # but we definitely kill the session and renew
  # the cookie
  field_names_to_save = request.session.get(FIELDS_TO_SAVE, [])

  # let's clean up the self-referential issue:
  field_names_to_save = set(field_names_to_save)
  field_names_to_save = field_names_to_save - set([FIELDS_TO_SAVE])
  field_names_to_save = list(field_names_to_save)

  fields_to_save = dict([(name, request.session.get(name, None)) for name in field_names_to_save])

  # let's not forget to save the list of fields to save
  fields_to_save[FIELDS_TO_SAVE] = field_names_to_save

  request.session.flush()

  for name in field_names_to_save:
    request.session[name] = fields_to_save[name]

  # copy the list of fields to save
  request.session[FIELDS_TO_SAVE] = fields_to_save[FIELDS_TO_SAVE]

  request.session['user_for_remote_logout'] = user

def do_remote_logout(request, user, return_url="/"):
  # FIXME: do something with return_url
  auth_system = AUTH_SYSTEMS[user['type']]
  
  # does the auth system have a special logout procedure?
  user_for_remote_logout = request.session.get('user_for_remote_logout', None)
  del request.session['user_for_remote_logout']
  if hasattr(auth_system, 'do_logout'):
    response = auth_system.do_logout(user_for_remote_logout)
    return response

def do_complete_logout(request, return_url="/"):
  do_local_logout(request)
  user_for_remote_logout = request.session.get('user_for_remote_logout', None)
  if user_for_remote_logout:
    response = do_remote_logout(request, user_for_remote_logout, return_url)
    return response
  return None
  
def logout(request):
  """
  logout
  """

  return_url = request.GET.get('return_url',"/")
  response = do_complete_logout(request, return_url)
  if response:
    return response
  
  return HttpResponseRedirect(return_url)

def _do_auth(request):
  # the session has the system name
  system_name = request.session['auth_system_name']

  # get the system
  system = AUTH_SYSTEMS[system_name]
  
  # where to send the user to?
  redirect_url = "%s%s" % (settings.SECURE_URL_HOST,reverse(after))
  auth_url = system.get_auth_url(request, redirect_url=redirect_url)
  
  if auth_url:
    return HttpResponseRedirect(auth_url)
  else:
    return HttpResponse("an error occurred trying to contact " + system_name +", try again later")
  
def start(request, system_name):
  if not (system_name in helios_auth.ENABLED_AUTH_SYSTEMS):
    return HttpResponseRedirect(reverse(index))
  
  # why is this here? Let's try without it
  # request.session.save()
  
  # store in the session the name of the system used for auth
  request.session['auth_system_name'] = system_name
  
  # where to return to when done
  request.session['auth_return_url'] = request.GET.get('return_url', '/')

  return _do_auth(request)

def perms_why(request):
  if request.method == "GET":
    return render_template(request, "perms_why")

  return _do_auth(request)

def after(request):
  # which auth system were we using?
  if not request.session.has_key('auth_system_name'):
    do_local_logout(request)
    return HttpResponseRedirect("/")
    
  system = AUTH_SYSTEMS[request.session['auth_system_name']]
  
  # get the user info
  user = system.get_user_info_after_auth(request)

  if user:
    # get the user and store any new data about him
    user_obj = User.update_or_create(user['type'], user['user_id'], user['name'], user['info'], user['token'])
    
    request.session['user'] = user
  else:
    return HttpResponseRedirect("%s?%s" % (reverse(perms_why), urllib.urlencode({'system_name' : request.session['auth_system_name']})))

  # does the auth system want to present an additional view?
  # this is, for example, to prompt the user to follow @heliosvoting
  # so they can hear about election results
  if hasattr(system, 'user_needs_intervention'):
    intervention_response = system.user_needs_intervention(user['user_id'], user['info'], user['token'])
    if intervention_response:
      return intervention_response

  # go to the after intervention page. This is for modularity
  return HttpResponseRedirect(reverse(after_intervention))

def after_intervention(request):
  return_url = "/"
  if request.session.has_key('auth_return_url'):
    return_url = request.session['auth_return_url']
    del request.session['auth_return_url']
  return HttpResponseRedirect("%s%s" % (settings.URL_HOST, return_url))


########NEW FILE########
__FILENAME__ = view_utils
"""
Utilities for all views

Ben Adida (12-30-2008)
"""

from django.template import Context, Template, loader
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response

from helios_auth.security import get_user

import helios_auth

from django.conf import settings

##
## BASICS
##

SUCCESS = HttpResponse("SUCCESS")

##
## template abstraction
##

def prepare_vars(request, vars):
  vars_with_user = vars.copy()
  
  if request:
    vars_with_user['user'] = get_user(request)
    vars_with_user['csrf_token'] = request.session['csrf_token']
    vars_with_user['SECURE_URL_HOST'] = settings.SECURE_URL_HOST
    
  vars_with_user['STATIC'] = '/static/auth'
  vars_with_user['MEDIA_URL'] = '/static/auth/'
  vars_with_user['TEMPLATE_BASE'] = helios_auth.TEMPLATE_BASE
  
  vars_with_user['settings'] = settings
  
  return vars_with_user
  
def render_template(request, template_name, vars = {}):
  t = loader.get_template(template_name + '.html')
  
  vars_with_user = prepare_vars(request, vars)
  
  return render_to_response('helios_auth/templates/%s.html' % template_name, vars_with_user)

def render_template_raw(request, template_name, vars={}):
  t = loader.get_template(template_name + '.html')
  
  vars_with_user = prepare_vars(request, vars)
  c = Context(vars_with_user)  
  return t.render(c)

def render_json(json_txt):
  return HttpResponse(json_txt)



########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = glue
"""
Glue some events together 
"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django.conf import settings
import helios.views, helios.signals

import views

def vote_cast_send_message(user, voter, election, cast_vote, **kwargs):
  ## FIXME: this doesn't work for voters that are not also users
  # prepare the message
  subject = "%s - vote cast" % election.name
  
  body = """
You have successfully cast a vote in

  %s
  
Your ballot is archived at:

  %s
""" % (election.name, helios.views.get_castvote_url(cast_vote))
  
  if election.use_voter_aliases:
    body += """

This election uses voter aliases to protect your privacy.
Your voter alias is : %s    
""" % voter.alias

  body += """

--
%s
""" % settings.SITE_TITLE  
  
  # send it via the notification system associated with the auth system
  user.send_message(subject, body)

helios.signals.vote_cast.connect(vote_cast_send_message)

def election_tallied(election, **kwargs):
  pass

helios.signals.election_tallied.connect(election_tallied)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
  (r'^$', home),
  (r'^about$', about),
  (r'^docs$', docs),
  (r'^faq$', faq),
  (r'^privacy$', privacy),
)

########NEW FILE########
__FILENAME__ = views
"""
server_ui specific views
"""

from helios.models import *
from helios_auth.security import *
from view_utils import *

import helios.views
import helios
from helios.crypto import utils as cryptoutils
from helios_auth.security import *
from helios.security import can_create_election

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed

from django.conf import settings

import copy
import helios_auth.views as auth_views

def get_election():
  return None
  
def home(request):
  # load the featured elections
  featured_elections = Election.get_featured()
  
  user = get_user(request)
  create_p = can_create_election(request)

  if create_p:
    elections_administered = Election.get_by_user_as_admin(user, archived_p=False, limit=5)
  else:
    elections_administered = None

  if user:
    elections_voted = Election.get_by_user_as_voter(user, limit=5)
  else:
    elections_voted = None
 
  auth_systems = copy.copy(settings.AUTH_ENABLED_AUTH_SYSTEMS)
  try:
    auth_systems.remove('password')
  except: pass

  login_box = auth_views.login_box_raw(request, return_url="/", auth_systems=auth_systems)

  return render_template(request, "index", {'elections': featured_elections,
                                            'elections_administered' : elections_administered,
                                            'elections_voted' : elections_voted,
                                            'create_p':create_p,
                                            'login_box' : login_box})
  
def about(request):
  return render_template(request, "about")

def docs(request):
  return render_template(request, "docs")

def faq(request):
  return render_template(request, "faq")

def privacy(request):
  return render_template(request, "privacy")
    

########NEW FILE########
__FILENAME__ = view_utils
"""
Utilities for single election views

Ben Adida (2009-07-18)
"""

from django.template import Context, Template, loader
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response

from helios_auth.security import get_user

from django.conf import settings

##
## template abstraction
##
def render_template(request, template_name, vars = {}):
  t = loader.get_template(template_name + '.html')
  
  vars_with_user = vars.copy()
  vars_with_user['user'] = get_user(request)
  vars_with_user['settings'] = settings
  vars_with_user['CURRENT_URL'] = request.path
  
  # csrf protection
  if request.session.has_key('csrf_token'):
    vars_with_user['csrf_token'] = request.session['csrf_token']
  
  return render_to_response('server_ui/templates/%s.html' % template_name, vars_with_user)
  

########NEW FILE########
__FILENAME__ = settings

import os, json

# go through environment variables and override them
def get_from_env(var, default):
    if os.environ.has_key(var):
        return os.environ[var]
    else:
        return default

DEBUG = (get_from_env('DEBUG', '1') == '1')
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Ben Adida', 'ben@adida.net'),
)

MANAGERS = ADMINS

# is this the master Helios web site?
MASTER_HELIOS = (get_from_env('MASTER_HELIOS', '0') == '1')

# show ability to log in? (for example, if the site is mostly used by voters)
# if turned off, the admin will need to know to go to /auth/login manually
SHOW_LOGIN_OPTIONS = (get_from_env('SHOW_LOGIN_OPTIONS', '1') == '1')

# sometimes, when the site is not that social, it's not helpful
# to display who created the election
SHOW_USER_INFO = (get_from_env('SHOW_USER_INFO', '1') == '1')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'helios'
    }
}

SOUTH_DATABASE_ADAPTERS = {'default':'south.db.postgresql_psycopg2'}

# override if we have an env variable
if get_from_env('DATABASE_URL', None):
    import dj_database_url
    DATABASES['default'] =  dj_database_url.config()
    DATABASES['default']['ENGINE'] = 'dbpool.db.backends.postgresql_psycopg2'
    DATABASES['default']['OPTIONS'] = {'MAX_CONNS': 1}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
STATIC_URL = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = get_from_env('SECRET_KEY', 'replaceme')

# Secure Stuff
if (get_from_env('SSL', '0') == '1'):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True

    # tuned for Heroku
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_HTTPONLY = True

# one week HSTS seems like a good balance for MITM prevention
if (get_from_env('HSTS', '0') == '1'):
    SECURE_HSTS_SECONDS = 3600 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

MIDDLEWARE_CLASSES = (
    # make all things SSL
    #'sslify.middleware.SSLifyMiddleware',

    # secure a bunch of things
    'djangosecure.middleware.SecurityMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware'
)

ROOT_URLCONF = 'urls'

ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    ROOT_PATH,
    os.path.join(ROOT_PATH, 'templates')
)

INSTALLED_APPS = (
#    'django.contrib.auth',
#    'django.contrib.contenttypes',
    'djangosecure',
    'django.contrib.sessions',
    'django.contrib.sites',
    ## needed for queues
    'djcelery',
    'kombu.transport.django',
    ## needed for schema migration
    'south',
    ## HELIOS stuff
    'helios_auth',
    'helios',
    'server_ui',
)

##
## HELIOS
##


MEDIA_ROOT = ROOT_PATH + "media/"

# a relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = "voters/%Y/%m/%d"


# Change your email settings
DEFAULT_FROM_EMAIL = get_from_env('DEFAULT_FROM_EMAIL', 'ben@adida.net')
DEFAULT_FROM_NAME = get_from_env('DEFAULT_FROM_NAME', 'Ben for Helios')
SERVER_EMAIL = '%s <%s>' % (DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL)

LOGIN_URL = '/auth/'
LOGOUT_ON_CONFIRMATION = True

# The two hosts are here so the main site can be over plain HTTP
# while the voting URLs are served over SSL.
URL_HOST = get_from_env("URL_HOST", "http://localhost:8000")

# IMPORTANT: you should not change this setting once you've created
# elections, as your elections' cast_url will then be incorrect.
# SECURE_URL_HOST = "https://localhost:8443"
SECURE_URL_HOST = get_from_env("SECURE_URL_HOST", "http://localhost:8000")

# this additional host is used to iframe-isolate the social buttons,
# which usually involve hooking in remote JavaScript, which could be
# a security issue. Plus, if there's a loading issue, it blocks the whole
# page. Not cool.
SOCIALBUTTONS_URL_HOST= get_from_env("SOCIALBUTTONS_URL_HOST", "http://localhost:8000")

# election stuff
SITE_TITLE = get_from_env('SITE_TITLE', 'Helios Voting')
MAIN_LOGO_URL = get_from_env('MAIN_LOGO_URL', '/static/logo.png')
ALLOW_ELECTION_INFO_URL = (get_from_env('ALLOW_ELECTION_INFO_URL', '0') == '1')

# FOOTER links
FOOTER_LINKS = json.loads(get_from_env('FOOTER_LINKS', '[]'))
FOOTER_LOGO_URL = get_from_env('FOOTER_LOGO_URL', None)

WELCOME_MESSAGE = get_from_env('WELCOME_MESSAGE', "This is the default message")

HELP_EMAIL_ADDRESS = get_from_env('HELP_EMAIL_ADDRESS', 'help@heliosvoting.org')

AUTH_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_ADMIN_ONLY = False
HELIOS_VOTERS_UPLOAD = True
HELIOS_VOTERS_EMAIL = True

# are elections private by default?
HELIOS_PRIVATE_DEFAULT = False

# authentication systems enabled
#AUTH_ENABLED_AUTH_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_AUTH_SYSTEMS = get_from_env('AUTH_ENABLED_AUTH_SYSTEMS', 'google').split(",")
AUTH_DEFAULT_AUTH_SYSTEM = get_from_env('AUTH_DEFAULT_AUTH_SYSTEM', None)

# facebook
FACEBOOK_APP_ID = get_from_env('FACEBOOK_APP_ID','')
FACEBOOK_API_KEY = get_from_env('FACEBOOK_API_KEY','')
FACEBOOK_API_SECRET = get_from_env('FACEBOOK_API_SECRET','')

# twitter
TWITTER_API_KEY = ''
TWITTER_API_SECRET = ''
TWITTER_USER_TO_FOLLOW = 'heliosvoting'
TWITTER_REASON_TO_FOLLOW = "we can direct-message you when the result has been computed in an election in which you participated"

# the token for Helios to do direct messaging
TWITTER_DM_TOKEN = {"oauth_token": "", "oauth_token_secret": "", "user_id": "", "screen_name": ""}

# LinkedIn
LINKEDIN_API_KEY = ''
LINKEDIN_API_SECRET = ''

# CAS (for universities)
CAS_USERNAME = get_from_env('CAS_USERNAME', "")
CAS_PASSWORD = get_from_env('CAS_PASSWORD', "")
CAS_ELIGIBILITY_URL = get_from_env('CAS_ELIGIBILITY_URL', "")
CAS_ELIGIBILITY_REALM = get_from_env('CAS_ELIGIBILITY_REALM', "")

# email server
EMAIL_HOST = get_from_env('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(get_from_env('EMAIL_PORT', "2525"))
EMAIL_HOST_USER = get_from_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_from_env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = (get_from_env('EMAIL_USE_TLS', '0') == '1')

# to use AWS Simple Email Service
# in which case environment should contain
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
if get_from_env('EMAIL_USE_AWS', '0') == '1':
    EMAIL_BACKEND = 'django_ses.SESBackend'

# set up logging
import logging
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s'
)


# set up django-celery
# BROKER_BACKEND = "kombu.transport.DatabaseTransport"
BROKER_URL = "django://"
CELERY_RESULT_DBURI = DATABASES['default']
import djcelery
djcelery.setup_loader()


# for testing
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
# this effectively does CELERY_ALWAYS_EAGER = True

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

urlpatterns = patterns(
    '',
    (r'^auth/', include('helios_auth.urls')),
    (r'^helios/', include('helios.urls')),

    # SHOULD BE REPLACED BY APACHE STATIC PATH
    (r'booth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),
    (r'verifier/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/heliosverifier'}),

    (r'static/auth/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/helios_auth/media'}),
    (r'static/helios/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/helios/media'}),
    (r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/server_ui/media'}),

    (r'^', include('server_ui.urls')),

    )

########NEW FILE########
__FILENAME__ = wsgi
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
