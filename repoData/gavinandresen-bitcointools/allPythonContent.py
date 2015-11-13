__FILENAME__ = address
#
# Code for parsing the addr.dat file
# NOTE: I think you have to shutdown the Bitcoin client to
# successfully read addr.dat...
#

from bsddb.db import *
import logging
from operator import itemgetter
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def dump_addresses(db_env):
  db = DB(db_env)
  try:
    r = db.open("addr.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open addr.dat/main. Try quitting Bitcoin and running this again.")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  for (key, value) in db.items():
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "addr":
      d = parse_CAddress(vds)
      print(deserialize_CAddress(d))

  db.close()

########NEW FILE########
__FILENAME__ = base58
#!/usr/bin/env python

"""encode/decode base58 in the same way that Bitcoin does"""

import math

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
  """ encode v, which is a string of bytes, to base58.    
  """

  long_value = 0L
  for (i, c) in enumerate(v[::-1]):
    long_value += ord(c) << (8*i) # 2x speedup vs. exponentiation

  result = ''
  while long_value >= __b58base:
    div, mod = divmod(long_value, __b58base)
    result = __b58chars[mod] + result
    long_value = div
  result = __b58chars[long_value] + result

  # Bitcoin does a little leading-zero-compression:
  # leading 0-bytes in the input become leading-1s
  nPad = 0
  for c in v:
    if c == '\0': nPad += 1
    else: break

  return (__b58chars[0]*nPad) + result

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

try:
  import hashlib
  hashlib.new('ripemd160')
  have_crypto = True
except ImportError:
  have_crypto = False

def hash_160(public_key):
  if not have_crypto:
    return ''
  h1 = hashlib.sha256(public_key).digest()
  r160 = hashlib.new('ripemd160')
  r160.update(h1)
  h2 = r160.digest()
  return h2

def public_key_to_bc_address(public_key, version="\x00"):
  if not have_crypto or public_key is None:
    return ''
  h160 = hash_160(public_key)
  return hash_160_to_bc_address(h160, version=version)

def hash_160_to_bc_address(h160, version="\x00"):
  if not have_crypto:
    return ''
  vh160 = version+h160
  h3=hashlib.sha256(hashlib.sha256(vh160).digest()).digest()
  addr=vh160+h3[0:4]
  return b58encode(addr)

def bc_address_to_hash_160(addr):
  bytes = b58decode(addr, 25)
  return bytes[1:21]

if __name__ == '__main__':
    x = '005cc87f4a3fdfe3a2346b6953267ca867282630d3f9b78e64'.decode('hex_codec')
    encoded = b58encode(x)
    print encoded, '19TbMSWwHvnxAKy12iNm3KdbGfzfaMFViT'
    print b58decode(encoded, len(x)).encode('hex_codec'), x.encode('hex_codec')

########NEW FILE########
__FILENAME__ = BCDataStream
#
# Workalike python implementation of Bitcoin's CDataStream class.
#
import struct
import StringIO
import mmap

class SerializationError(Exception):
  """ Thrown when there's a problem deserializing or serializing """

class BCDataStream(object):
  def __init__(self):
    self.input = None
    self.read_cursor = 0

  def clear(self):
    self.input = None
    self.read_cursor = 0

  def write(self, bytes):  # Initialize with string of bytes
    if self.input is None:
      self.input = bytes
    else:
      self.input += bytes

  def map_file(self, file, start):  # Initialize with bytes from file
    self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
    self.read_cursor = start
  def seek_file(self, position):
    self.read_cursor = position
  def close_file(self):
    self.input.close()

  def read_string(self):
    # Strings are encoded depending on length:
    # 0 to 252 :  1-byte-length followed by bytes (if any)
    # 253 to 65,535 : byte'253' 2-byte-length followed by bytes
    # 65,536 to 4,294,967,295 : byte '254' 4-byte-length followed by bytes
    # ... and the Bitcoin client is coded to understand:
    # greater than 4,294,967,295 : byte '255' 8-byte-length followed by bytes of string
    # ... but I don't think it actually handles any strings that big.
    if self.input is None:
      raise SerializationError("call write(bytes) before trying to deserialize")

    try:
      length = self.read_compact_size()
    except IndexError:
      raise SerializationError("attempt to read past end of buffer")

    return self.read_bytes(length)

  def write_string(self, string):
    # Length-encoded as with read-string
    self.write_compact_size(len(string))
    self.write(string)

  def read_bytes(self, length):
    try:
      result = self.input[self.read_cursor:self.read_cursor+length]
      self.read_cursor += length
      return result
    except IndexError:
      raise SerializationError("attempt to read past end of buffer")

    return ''

  def read_boolean(self): return self.read_bytes(1)[0] != chr(0)
  def read_int16(self): return self._read_num('<h')
  def read_uint16(self): return self._read_num('<H')
  def read_int32(self): return self._read_num('<i')
  def read_uint32(self): return self._read_num('<I')
  def read_int64(self): return self._read_num('<q')
  def read_uint64(self): return self._read_num('<Q')

  def write_boolean(self, val): return self.write(chr(1) if val else chr(0))
  def write_int16(self, val): return self._write_num('<h', val)
  def write_uint16(self, val): return self._write_num('<H', val)
  def write_int32(self, val): return self._write_num('<i', val)
  def write_uint32(self, val): return self._write_num('<I', val)
  def write_int64(self, val): return self._write_num('<q', val)
  def write_uint64(self, val): return self._write_num('<Q', val)

  def read_compact_size(self):
    size = ord(self.input[self.read_cursor])
    self.read_cursor += 1
    if size == 253:
      size = self._read_num('<H')
    elif size == 254:
      size = self._read_num('<I')
    elif size == 255:
      size = self._read_num('<Q')
    return size

  def write_compact_size(self, size):
    if size < 0:
      raise SerializationError("attempt to write size < 0")
    elif size < 253:
       self.write(chr(size))
    elif size < 2**16:
      self.write('\xfd')
      self._write_num('<H', size)
    elif size < 2**32:
      self.write('\xfe')
      self._write_num('<I', size)
    elif size < 2**64:
      self.write('\xff')
      self._write_num('<Q', size)

  def _read_num(self, format):
    (i,) = struct.unpack_from(format, self.input, self.read_cursor)
    self.read_cursor += struct.calcsize(format)
    return i

  def _write_num(self, format, num):
    s = struct.pack(format, num)
    self.write(s)

########NEW FILE########
__FILENAME__ = blkindex
#
# Code for parsing the blkindex.dat file
#

from bsddb.db import *
import logging
from operator import itemgetter
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def dump_blkindex_summary(db_env):
  db = DB(db_env)
  try:
    r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open blkindex.dat/main.  Try quitting any running Bitcoin apps.")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  n_tx = 0
  n_blockindex = 0

  print("blkindex file summary:")
  for (key, value) in db.items():
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "tx":
      n_tx += 1
    elif type == "blockindex":
      n_blockindex += 1
    elif type == "version":
      version = vds.read_int32()
      print(" Version: %d"%(version,))
    elif type == "hashBestChain":
      hash = vds.read_bytes(32)
      print(" HashBestChain: %s"%(hash.encode('hex_codec'),))
    else:
      logging.warn("blkindex: unknown type '%s'"%(type,))
      continue

  print(" %d transactions, %d blocks."%(n_tx, n_blockindex))
  db.close()

########NEW FILE########
__FILENAME__ = block
#
# Code for dumping a single block, given its ID (hash)
#

from bsddb.db import *
import logging
import os.path
import re
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex, long_hex
from deserialize import *

def _open_blkindex(db_env):
  db = DB(db_env)
  try:
    r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True
  if r is not None:
    logging.error("Couldn't open blkindex.dat/main.  Try quitting any running Bitcoin apps.")
    sys.exit(1)
  return db

def _read_CDiskTxPos(stream):
  n_file = stream.read_uint32()
  n_block_pos = stream.read_uint32()
  n_tx_pos = stream.read_uint32()
  return (n_file, n_block_pos, n_tx_pos)

def _dump_block(datadir, nFile, nBlockPos, hash256, hashNext, do_print=True, print_raw_tx=False, print_json=False):
  blockfile = open(os.path.join(datadir, "blk%04d.dat"%(nFile,)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, nBlockPos)
  d = parse_Block(ds)
  block_string = deserialize_Block(d, print_raw_tx)
  ds.close_file()
  blockfile.close()
  if do_print:
    print "BLOCK "+long_hex(hash256[::-1])
    print "Next block: "+long_hex(hashNext[::-1])
    print block_string
  elif print_json:
    import json
    print json.dumps({
                        'version': d['version'],
                        'previousblockhash': d['hashPrev'][::-1].encode('hex'),
                        'transactions' : [ tx_hex['__data__'].encode('hex') for tx_hex in d['transactions'] ],
                        'time' : d['nTime'],
                        'bits' : hex(d['nBits']).lstrip("0x"),
                        'nonce' : d['nNonce']
                      })

  return block_string

def _parse_block_index(vds):
  d = {}
  d['version'] = vds.read_int32()
  d['hashNext'] = vds.read_bytes(32)
  d['nFile'] = vds.read_uint32()
  d['nBlockPos'] = vds.read_uint32()
  d['nHeight'] = vds.read_int32()

  header_start = vds.read_cursor
  d['b_version'] = vds.read_int32()
  d['hashPrev'] = vds.read_bytes(32)
  d['hashMerkle'] = vds.read_bytes(32)
  d['nTime'] = vds.read_int32()
  d['nBits'] = vds.read_int32()
  d['nNonce'] = vds.read_int32()
  header_end = vds.read_cursor
  d['__header__'] = vds.input[header_start:header_end]
  return d

def dump_block(datadir, db_env, block_hash, print_raw_tx=False, print_json=False):
  """ Dump a block, given hexadecimal hash-- either the full hash
      OR a short_hex version of the it.
  """
  db = _open_blkindex(db_env)

  kds = BCDataStream()
  vds = BCDataStream()

  n_blockindex = 0

  key_prefix = "\x0ablockindex"
  cursor = db.cursor()
  (key, value) = cursor.set_range(key_prefix)

  while key.startswith(key_prefix):
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()
    hash256 = kds.read_bytes(32)
    hash_hex = long_hex(hash256[::-1])
    block_data = _parse_block_index(vds)

    if (hash_hex.startswith(block_hash) or short_hex(hash256[::-1]).startswith(block_hash)):
      if print_json == False:
          print "Block height: "+str(block_data['nHeight'])
          _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], hash256, block_data['hashNext'], print_raw_tx=print_raw_tx)
      else:
          _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], hash256, block_data['hashNext'], print_json=print_json, do_print=False)

    (key, value) = cursor.next()

  db.close()

def read_block(db_cursor, hash):
  (key,value) = db_cursor.set_range("\x0ablockindex"+hash)
  vds = BCDataStream()
  vds.clear(); vds.write(value)
  block_data = _parse_block_index(vds)
  block_data['hash256'] = hash
  return block_data

def scan_blocks(datadir, db_env, callback_fn):
  """ Scan through blocks, from last through genesis block,
      calling callback_fn(block_data) for each.
      callback_fn should return False if scanning should
      stop, True if it should continue.
      Returns last block_data scanned.
  """
  db = _open_blkindex(db_env)

  kds = BCDataStream()
  vds = BCDataStream()
  
  # Read the hashBestChain record:
  cursor = db.cursor()
  (key, value) = cursor.set_range("\x0dhashBestChain")
  vds.write(value)
  hashBestChain = vds.read_bytes(32)

  block_data = read_block(cursor, hashBestChain)

  while callback_fn(block_data):
    if block_data['nHeight'] == 0:
      break;
    block_data = read_block(cursor, block_data['hashPrev'])
  return block_data


def dump_block_n(datadir, db_env, block_number, print_raw_tx=False, print_json=False):
  """ Dump a block given block number (== height, genesis block is 0)
  """
  def scan_callback(block_data):
    return not block_data['nHeight'] == block_number

  block_data = scan_blocks(datadir, db_env, scan_callback)
  
  if print_json == False:
    print "Block height: "+str(block_data['nHeight'])
    _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], block_data['hash256'], block_data['hashNext'], print_raw_tx=print_raw_tx, print_json=print_json)
  else:
    _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], block_data['hash256'], block_data['hashNext'], do_print=False, print_raw_tx=print_raw_tx, print_json=print_json)
    
def search_blocks(datadir, db_env, pattern):
  """ Dump a block given block number (== height, genesis block is 0)
  """
  db = _open_blkindex(db_env)
  kds = BCDataStream()
  vds = BCDataStream()
  
  # Read the hashBestChain record:
  cursor = db.cursor()
  (key, value) = cursor.set_range("\x0dhashBestChain")
  vds.write(value)
  hashBestChain = vds.read_bytes(32)
  block_data = read_block(cursor, hashBestChain)

  if pattern == "NONSTANDARD_CSCRIPTS": # Hack to look for non-standard transactions
    search_odd_scripts(datadir, cursor, block_data)
    return

  while True:
    block_string = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'],
                               block_data['hash256'], block_data['hashNext'], False)
    
    if re.search(pattern, block_string) is not None:
      print "MATCH: Block height: "+str(block_data['nHeight'])
      print block_string

    if block_data['nHeight'] == 0:
      break
    block_data = read_block(cursor, block_data['hashPrev'])
    
def search_odd_scripts(datadir, cursor, block_data):
  """ Look for non-standard transactions """
  while True:
    block_string = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'],
                               block_data['hash256'], block_data['hashNext'], False)
    
    found_nonstandard = False
    for m in re.finditer(r'TxIn:(.*?)$', block_string, re.MULTILINE):
      s = m.group(1)
      if re.match(r'\s*COIN GENERATED coinbase:\w+$', s): continue
      if re.match(r'.*sig: \d+:\w+...\w+ \d+:\w+...\w+$', s): continue
      if re.match(r'.*sig: \d+:\w+...\w+$', s): continue
      print "Nonstandard TxIn: "+s
      found_nonstandard = True
      break

    for m in re.finditer(r'TxOut:(.*?)$', block_string, re.MULTILINE):
      s = m.group(1)
      if re.match(r'.*Script: DUP HASH160 \d+:\w+...\w+ EQUALVERIFY CHECKSIG$', s): continue
      if re.match(r'.*Script: \d+:\w+...\w+ CHECKSIG$', s): continue
      print "Nonstandard TxOut: "+s
      found_nonstandard = True
      break

    if found_nonstandard:
      print "NONSTANDARD TXN: Block height: "+str(block_data['nHeight'])
      print block_string

    if block_data['nHeight'] == 0:
      break
    block_data = read_block(cursor, block_data['hashPrev'])
  
def check_block_chain(db_env):
  """ Make sure hashPrev/hashNext pointers are consistent through block chain """
  db = _open_blkindex(db_env)

  kds = BCDataStream()
  vds = BCDataStream()
  
  # Read the hashBestChain record:
  cursor = db.cursor()
  (key, value) = cursor.set_range("\x0dhashBestChain")
  vds.write(value)
  hashBestChain = vds.read_bytes(32)

  back_blocks = []

  block_data = read_block(cursor, hashBestChain)

  while block_data['nHeight'] > 0:
    back_blocks.append( (block_data['nHeight'], block_data['hashMerkle'], block_data['hashPrev'], block_data['hashNext']) )
    block_data = read_block(cursor, block_data['hashPrev'])

  back_blocks.append( (block_data['nHeight'], block_data['hashMerkle'], block_data['hashPrev'], block_data['hashNext']) )
  genesis_block = block_data
  
  print("check block chain: genesis block merkle hash is: %s"%(block_data['hashMerkle'][::-1].encode('hex_codec')))

  while block_data['hashNext'] != ('\0'*32):
    forward = (block_data['nHeight'], block_data['hashMerkle'], block_data['hashPrev'], block_data['hashNext'])
    back = back_blocks.pop()
    if forward != back:
      print("Forward/back block mismatch at height %d!"%(block_data['nHeight'],))
      print(" Forward: "+str(forward))
      print(" Back: "+str(back))
    block_data = read_block(cursor, block_data['hashNext'])

class CachedBlockFile(object):
  def __init__(self, db_dir):
    self.datastream = None
    self.file = None
    self.n = None
    self.db_dir = db_dir

  def get_stream(self, n):
    if self.n == n:
      return self.datastream
    if self.datastream is not None:
      self.datastream.close_file()
      self.file.close()
    self.n = n
    self.file = open(os.path.join(self.db_dir, "blk%04d.dat"%(n,)), "rb")
    self.datastream = BCDataStream()
    self.datastream.map_file(self.file, 0)
    return self.datastream

########NEW FILE########
__FILENAME__ = blocks
#
# Code for parsing the blkindex.dat file
#

from bsddb.db import *
import logging
from operator import itemgetter
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def _read_CDiskTxPos(stream):
  n_file = stream.read_uint32()
  n_block_pos = stream.read_uint32()
  n_tx_pos = stream.read_uint32()
  return (n_file, n_block_pos, n_tx_pos)

def dump_blockindex(db_env, owner=None, n_to_dump=1000):
  db = DB(db_env)
  r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  if r is not None:
    logging.error("Couldn't open blkindex.dat/main")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  wallet_transactions = []

  for (i, (key, value)) in enumerate(db.items()):
    if i > n_to_dump:
      break

    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "tx":
      hash256 = kds.read_bytes(32)
      version = vds.read_uint32()
      tx_pos = _read_CDiskTxPos(vds)
      print("Tx(%s:%d %d %d)"%((short_hex(hash256),)+tx_pos))
      n_tx_out = vds.read_compact_size()
      for i in range(0,n_tx_out):
        tx_out = _read_CDiskTxPos(vds)
        if tx_out[0] != 0xffffffffL:  # UINT_MAX means no TxOuts (unspent)
          print("  ==> TxOut(%d %d %d)"%tx_out)
      
    else:
      logging.warn("blkindex: type %s"%(type,))
      continue

  db.close()


########NEW FILE########
__FILENAME__ = coinbase_integers
#!/usr/bin/env python
#
# Scan through coinbase transactions
# in the block database intepreting
# bytes 0-3 (and 1-4 if byte 0 is 0x04)
# as a block height, looking for plausible
# future heights.
#
from bsddb.db import *
from datetime import date, datetime
import logging
import os
import re
import sys

from BCDataStream import *
from block import scan_blocks, CachedBlockFile
from collections import defaultdict
from deserialize import parse_Block
from util import determine_db_dir, create_env

def approx_date(height):
  timestamp = 1231006505+height*10*60
  t = datetime.fromtimestamp(timestamp)
  return "%d-%.2d"%(t.year, t.month)

def main():
  import optparse
  parser = optparse.OptionParser(usage="%prog [options]")
  parser.add_option("--datadir", dest="datadir", default=None,
                    help="Look for files here (defaults to bitcoin default)")
  (options, args) = parser.parse_args()

  if options.datadir is None:
    db_dir = determine_db_dir()
  else:
    db_dir = options.datadir

  try:
    db_env = create_env(db_dir)
  except DBNoSuchFileError:
    logging.error("Couldn't open " + db_dir)
    sys.exit(1)

  blockfile = CachedBlockFile(db_dir)

  def gather(block_data):
    block_datastream = blockfile.get_stream(block_data['nFile'])
    block_datastream.seek_file(block_data['nBlockPos'])
    data = parse_Block(block_datastream)
    height = block_data['nHeight']
    coinbase = data['transactions'][0]
    scriptSig = coinbase['txIn'][0]['scriptSig']
    if len(scriptSig) < 4:
      return True
    (n,) = struct.unpack_from('<I', scriptSig[0:4])
    if n < 6*24*365.25*100:  # 200 years of blocks:
      print("%d: %d (%s) version: %d/%d"%(height, n, approx_date(n), block_data['b_version'],coinbase['version']))

    if ord(scriptSig[0]) == 0x03:
      (n,) = struct.unpack_from('<I', scriptSig[1:4]+'\0')
      if n < 6*24*365.25*100:  # 200 years of blocks:
        print("%d: PUSH %d (%s) version: %d/%d"%(height, n, approx_date(n), block_data['b_version'],coinbase['version']))

    return True

  scan_blocks(db_dir, db_env, gather)

  db_env.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dbdump
#!/usr/bin/env python
#
# Code for dumping the bitcoin Berkeley db files in a human-readable format
#
from bsddb.db import *
import logging
import sys

from address import dump_addresses
from wallet import dump_wallet, dump_accounts
from blkindex import dump_blkindex_summary
from transaction import dump_transaction
from block import dump_block, dump_block_n, search_blocks, check_block_chain
from util import determine_db_dir, create_env

def main():
  import optparse
  parser = optparse.OptionParser(usage="%prog [options]")
  parser.add_option("--datadir", dest="datadir", default=None,
                    help="Look for files here (defaults to bitcoin default)")
  parser.add_option("--wallet", action="store_true", dest="dump_wallet", default=False,
                    help="Print out contents of the wallet.dat file")
  parser.add_option("--wallet-tx", action="store_true", dest="dump_wallet_tx", default=False,
                    help="Print transactions in the wallet.dat file")
  parser.add_option("--wallet-tx-filter", action="store", dest="wallet_tx_filter", default="",
                    help="Only print transactions that match given string/regular expression")
  parser.add_option("--accounts", action="store_true", dest="dump_accounts", default="",
                    help="Print out account names, one per line")
  parser.add_option("--blkindex", action="store_true", dest="dump_blkindex", default=False,
                    help="Print out summary of blkindex.dat file")
  parser.add_option("--check-block-chain", action="store_true", dest="check_chain", default=False,
                    help="Scan back and forward through the block chain, looking for inconsistencies")
  parser.add_option("--address", action="store_true", dest="dump_addr", default=False,
                    help="Print addresses in the addr.dat file")
  parser.add_option("--transaction", action="store", dest="dump_transaction", default=None,
                    help="Dump a single transaction, given hex transaction id (or abbreviated id)")
  parser.add_option("--block", action="store", dest="dump_block", default=None,
                    help="Dump a single block, given its hex hash (or abbreviated hex hash) OR block height")
  parser.add_option("--search-blocks", action="store", dest="search_blocks", default=None,
                    help="Search the block chain for blocks containing given regex pattern")
  parser.add_option("--print-raw-tx", action="store_true", dest="print_raw_tx", default=False,
                    help="When dumping a block, print raw, hexadecimal transaction data for every transaction, in the same format that getmemorypool uses")
  parser.add_option("--print-json", action="store_true", dest="print_json", default=False,
                    help="When dumping a block, output it in JSON format (like output of RPC commands)")

  (options, args) = parser.parse_args()

  if options.datadir is None:
    db_dir = determine_db_dir()
  else:
    db_dir = options.datadir

  try:
    db_env = create_env(db_dir)
  except DBNoSuchFileError:
    logging.error("Couldn't open " + db_dir)
    sys.exit(1)

  dump_tx = options.dump_wallet_tx
  if len(options.wallet_tx_filter) > 0:
    dump_tx = True
  if options.dump_wallet or dump_tx:
    dump_wallet(db_env, options.dump_wallet, dump_tx, options.wallet_tx_filter)
  if options.dump_accounts:
    dump_accounts(db_env)

  if options.dump_addr:
    dump_addresses(db_env)

  if options.check_chain:
    check_block_chain(db_env)

  if options.dump_blkindex:
    dump_blkindex_summary(db_env)

  if options.dump_transaction is not None:
    dump_transaction(db_dir, db_env, options.dump_transaction)

  if options.dump_block is not None:
    if len(options.dump_block) < 7: # Probably an integer...
      try:
        dump_block_n(db_dir, db_env, int(options.dump_block), options.print_raw_tx, options.print_json)
      except ValueError:
        dump_block(db_dir, db_env, options.dump_block, options.print_raw_tx, options.print_json)
    else:
      dump_block(db_dir, db_env, options.dump_block, options.print_raw_tx, options.print_json)

  if options.search_blocks is not None:
    search_blocks(db_dir, db_env, options.search_blocks)

  db_env.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deserialize
#
#
#

from BCDataStream import *
from enumeration import Enumeration
from base58 import public_key_to_bc_address, hash_160_to_bc_address
import logging
import socket
import time
from util import short_hex, long_hex
import struct

def parse_CAddress(vds):
  d = {}
  d['nVersion'] = vds.read_int32()
  d['nTime'] = vds.read_uint32()
  d['nServices'] = vds.read_uint64()
  d['pchReserved'] = vds.read_bytes(12)
  d['ip'] = socket.inet_ntoa(vds.read_bytes(4))
  d['port'] = socket.htons(vds.read_uint16())
  return d

def deserialize_CAddress(d):
  return d['ip']+":"+str(d['port'])+" (lastseen: %s)"%(time.ctime(d['nTime']),)

def parse_setting(setting, vds):
  if setting[0] == "f":  # flag (boolean) settings
    return str(vds.read_boolean())
  elif setting == "addrIncoming":
    return "" # bitcoin 0.4 purposely breaks addrIncoming setting in encrypted wallets.
  elif setting[0:4] == "addr": # CAddress
    d = parse_CAddress(vds)
    return deserialize_CAddress(d)
  elif setting == "nTransactionFee":
    return vds.read_int64()
  elif setting == "nLimitProcessors":
    return vds.read_int32()
  return 'unknown setting'

def parse_TxIn(vds):
  d = {}
  d['prevout_hash'] = vds.read_bytes(32)
  d['prevout_n'] = vds.read_uint32()
  d['scriptSig'] = vds.read_bytes(vds.read_compact_size())
  d['sequence'] = vds.read_uint32()
  return d

def deserialize_TxIn(d, transaction_index=None, owner_keys=None):
  if d['prevout_hash'] == "\x00"*32:
    result = "TxIn: COIN GENERATED"
    result += " coinbase:"+d['scriptSig'].encode('hex_codec')
  elif transaction_index is not None and d['prevout_hash'] in transaction_index:
    p = transaction_index[d['prevout_hash']]['txOut'][d['prevout_n']]
    result = "TxIn: value: %f"%(p['value']/1.0e8,)
    result += " prev("+long_hex(d['prevout_hash'][::-1])+":"+str(d['prevout_n'])+")"
  else:
    result = "TxIn: prev("+long_hex(d['prevout_hash'][::-1])+":"+str(d['prevout_n'])+")"
    pk = extract_public_key(d['scriptSig'])
    result += " pubkey: "+pk
    result += " sig: "+decode_script(d['scriptSig'])
  if d['sequence'] < 0xffffffff: result += " sequence: "+hex(d['sequence'])
  return result

def parse_TxOut(vds):
  d = {}
  d['value'] = vds.read_int64()
  d['scriptPubKey'] = vds.read_bytes(vds.read_compact_size())
  return d

def deserialize_TxOut(d, owner_keys=None):
  result =  "TxOut: value: %f"%(d['value']/1.0e8,)
  pk = extract_public_key(d['scriptPubKey'])
  result += " pubkey: "+pk
  result += " Script: "+decode_script(d['scriptPubKey'])
  if owner_keys is not None:
    if pk in owner_keys: result += " Own: True"
    else: result += " Own: False"
  return result

def parse_Transaction(vds):
  d = {}
  start_pos = vds.read_cursor
  d['version'] = vds.read_int32()
  n_vin = vds.read_compact_size()
  d['txIn'] = []
  for i in xrange(n_vin):
    d['txIn'].append(parse_TxIn(vds))
  n_vout = vds.read_compact_size()
  d['txOut'] = []
  for i in xrange(n_vout):
    d['txOut'].append(parse_TxOut(vds))
  d['lockTime'] = vds.read_uint32()
  d['__data__'] = vds.input[start_pos:vds.read_cursor]
  return d

def deserialize_Transaction(d, transaction_index=None, owner_keys=None, print_raw_tx=False):
  result = "%d tx in, %d out\n"%(len(d['txIn']), len(d['txOut']))
  for txIn in d['txIn']:
    result += deserialize_TxIn(txIn, transaction_index) + "\n"
  for txOut in d['txOut']:
    result += deserialize_TxOut(txOut, owner_keys) + "\n"
  if print_raw_tx == True:
      result += "Transaction hex value: " + d['__data__'].encode('hex') + "\n"
  
  return result

def parse_MerkleTx(vds):
  d = parse_Transaction(vds)
  d['hashBlock'] = vds.read_bytes(32)
  n_merkleBranch = vds.read_compact_size()
  d['merkleBranch'] = vds.read_bytes(32*n_merkleBranch)
  d['nIndex'] = vds.read_int32()
  return d

def deserialize_MerkleTx(d, transaction_index=None, owner_keys=None):
  tx = deserialize_Transaction(d, transaction_index, owner_keys)
  result = "block: "+(d['hashBlock'][::-1]).encode('hex_codec')
  result += " %d hashes in merkle branch\n"%(len(d['merkleBranch'])/32,)
  return result+tx

def parse_WalletTx(vds):
  d = parse_MerkleTx(vds)
  n_vtxPrev = vds.read_compact_size()
  d['vtxPrev'] = []
  for i in xrange(n_vtxPrev):
    d['vtxPrev'].append(parse_MerkleTx(vds))

  d['mapValue'] = {}
  n_mapValue = vds.read_compact_size()
  for i in xrange(n_mapValue):
    key = vds.read_string()
    value = vds.read_string()
    d['mapValue'][key] = value
  n_orderForm = vds.read_compact_size()
  d['orderForm'] = []
  for i in xrange(n_orderForm):
    first = vds.read_string()
    second = vds.read_string()
    d['orderForm'].append( (first, second) )
  d['fTimeReceivedIsTxTime'] = vds.read_uint32()
  d['timeReceived'] = vds.read_uint32()
  d['fromMe'] = vds.read_boolean()
  d['spent'] = vds.read_boolean()

  return d

def deserialize_WalletTx(d, transaction_index=None, owner_keys=None):
  result = deserialize_MerkleTx(d, transaction_index, owner_keys)
  result += "%d vtxPrev txns\n"%(len(d['vtxPrev']),)
  result += "mapValue:"+str(d['mapValue'])
  if len(d['orderForm']) > 0:
    result += "\n"+" orderForm:"+str(d['orderForm'])
  result += "\n"+"timeReceived:"+time.ctime(d['timeReceived'])
  result += " fromMe:"+str(d['fromMe'])+" spent:"+str(d['spent'])
  return result

# The CAuxPow (auxiliary proof of work) structure supports merged mining.
# A flag in the block version field indicates the structure's presence.
# As of 8/2011, the Original Bitcoin Client does not use it.  CAuxPow
# originated in Namecoin; see
# https://github.com/vinced/namecoin/blob/mergedmine/doc/README_merged-mining.md.
def parse_AuxPow(vds):
  d = parse_MerkleTx(vds)
  n_chainMerkleBranch = vds.read_compact_size()
  d['chainMerkleBranch'] = vds.read_bytes(32*n_chainMerkleBranch)
  d['chainIndex'] = vds.read_int32()
  d['parentBlock'] = parse_BlockHeader(vds)
  return d

def parse_BlockHeader(vds):
  d = {}
  header_start = vds.read_cursor
  d['version'] = vds.read_int32()
  d['hashPrev'] = vds.read_bytes(32)
  d['hashMerkleRoot'] = vds.read_bytes(32)
  d['nTime'] = vds.read_uint32()
  d['nBits'] = vds.read_uint32()
  d['nNonce'] = vds.read_uint32()
  header_end = vds.read_cursor
  d['__header__'] = vds.input[header_start:header_end]
  return d

def parse_Block(vds):
  d = parse_BlockHeader(vds)
  d['transactions'] = []
#  if d['version'] & (1 << 8):
#    d['auxpow'] = parse_AuxPow(vds)
  nTransactions = vds.read_compact_size()
  for i in xrange(nTransactions):
    d['transactions'].append(parse_Transaction(vds))

  return d
  
def deserialize_Block(d, print_raw_tx=False):
  result = "Time: "+time.ctime(d['nTime'])+" Nonce: "+str(d['nNonce'])
  result += "\nnBits: 0x"+hex(d['nBits'])
  result += "\nhashMerkleRoot: 0x"+d['hashMerkleRoot'][::-1].encode('hex_codec')
  result += "\nPrevious block: "+d['hashPrev'][::-1].encode('hex_codec')
  result += "\n%d transactions:\n"%len(d['transactions'])
  for t in d['transactions']:
    result += deserialize_Transaction(t, print_raw_tx=print_raw_tx)+"\n"
  result += "\nRaw block header: "+d['__header__'].encode('hex_codec')
  return result

def parse_BlockLocator(vds):
  d = { 'hashes' : [] }
  nHashes = vds.read_compact_size()
  for i in xrange(nHashes):
    d['hashes'].append(vds.read_bytes(32))
  return d

def deserialize_BlockLocator(d):
  result = "Block Locator top: "+d['hashes'][0][::-1].encode('hex_codec')
  return result

opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1",76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
    "OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_7",
    "OP_8", "OP_9", "OP_10", "OP_11", "OP_12", "OP_13", "OP_14", "OP_15", "OP_16",
    "OP_NOP", "OP_VER", "OP_IF", "OP_NOTIF", "OP_VERIF", "OP_VERNOTIF", "OP_ELSE", "OP_ENDIF", "OP_VERIFY",
    "OP_RETURN", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_2DROP", "OP_2DUP", "OP_3DUP", "OP_2OVER", "OP_2ROT", "OP_2SWAP",
    "OP_IFDUP", "OP_DEPTH", "OP_DROP", "OP_DUP", "OP_NIP", "OP_OVER", "OP_PICK", "OP_ROLL", "OP_ROT",
    "OP_SWAP", "OP_TUCK", "OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_SIZE", "OP_INVERT", "OP_AND",
    "OP_OR", "OP_XOR", "OP_EQUAL", "OP_EQUALVERIFY", "OP_RESERVED1", "OP_RESERVED2", "OP_1ADD", "OP_1SUB", "OP_2MUL",
    "OP_2DIV", "OP_NEGATE", "OP_ABS", "OP_NOT", "OP_0NOTEQUAL", "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
    "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR",
    "OP_NUMEQUAL", "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN",
    "OP_GREATERTHAN", "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX",
    "OP_WITHIN", "OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160",
    "OP_HASH256", "OP_CODESEPARATOR", "OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG",
    "OP_CHECKMULTISIGVERIFY",
    "OP_NOP1", "OP_NOP2", "OP_NOP3", "OP_NOP4", "OP_NOP5", "OP_NOP6", "OP_NOP7", "OP_NOP8", "OP_NOP9", "OP_NOP10",
    ("OP_INVALIDOPCODE", 0xFF),
])

def script_GetOp(bytes):
  i = 0
  while i < len(bytes):
    vch = None
    opcode = ord(bytes[i])
    i += 1

    if opcode <= opcodes.OP_PUSHDATA4:
      nSize = opcode
      if opcode == opcodes.OP_PUSHDATA1:
        if i + 1 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          nSize = ord(bytes[i])
          i += 1
      elif opcode == opcodes.OP_PUSHDATA2:
        if i + 2 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          (nSize,) = struct.unpack_from('<H', bytes, i)
          i += 2
      elif opcode == opcodes.OP_PUSHDATA4:
        if i + 4 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          (nSize,) = struct.unpack_from('<I', bytes, i)
          i += 4
      if i+nSize > len(bytes):
        vch = "_INVALID_"+bytes[i:]
        i = len(bytes)
      else:
        vch = bytes[i:i+nSize]
        i += nSize

    yield (opcode, vch)

def script_GetOpName(opcode):
  try:
    return (opcodes.whatis(opcode)).replace("OP_", "")
  except KeyError:
    return "InvalidOp_"+str(opcode)

def decode_script(bytes):
  result = ''
  for (opcode, vch) in script_GetOp(bytes):
    if len(result) > 0: result += " "
    if opcode <= opcodes.OP_PUSHDATA4:
      result += "%d:"%(opcode,)
      result += short_hex(vch)
    else:
      result += script_GetOpName(opcode)
  return result

def match_decoded(decoded, to_match):
  if len(decoded) != len(to_match):
    return False;
  for i in range(len(decoded)):
    if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4:
      continue  # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
    if to_match[i] != decoded[i][0]:
      return False
  return True

def extract_public_key(bytes, version='\x00'):
  try:
    decoded = [ x for x in script_GetOp(bytes) ]
  except struct.error:
    return "(None)"

  # non-generated TxIn transactions push a signature
  # (seventy-something bytes) and then their public key
  # (33 or 65 bytes) onto the stack:
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[1][1], version=version)

  # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
  # 65 BYTES:... CHECKSIG
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[0][1], version=version)

  # Pay-by-Bitcoin-address TxOuts look like:
  # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
  match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[2][1], version=version)

  # BIP11 TxOuts look like one of these:
  # Note that match_decoded is dumb, so OP_1 actually matches OP_1/2/3/etc:
  multisigs = [
    [ opcodes.OP_1, opcodes.OP_PUSHDATA4, opcodes.OP_1, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_3, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
  ]
  for match in multisigs:
    if match_decoded(decoded, match):
      return "["+','.join([public_key_to_bc_address(decoded[i][1]) for i in range(1,len(decoded)-1)])+"]"

  # BIP16 TxOuts look like:
  # HASH160 20 BYTES:... EQUAL
  match = [ opcodes.OP_HASH160, 0x14, opcodes.OP_EQUAL ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[1][1], version="\x05")

  return "(None)"

########NEW FILE########
__FILENAME__ = enumeration
#
# enum-like type
# From the Python Cookbook, downloaded from http://code.activestate.com/recipes/67107/
#
import types, string, exceptions

class EnumException(exceptions.Exception):
    pass

class Enumeration:
    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = { }
        reverseLookup = { }
        i = 0
        uniqueNames = [ ]
        uniqueValues = [ ]
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException, "enum name is not a string: " + x
            if type(i) != types.IntType:
                raise EnumException, "enum value is not an integer: " + i
            if x in uniqueNames:
                raise EnumException, "enum name is not unique: " + x
            if i in uniqueValues:
                raise EnumException, "enum value is not unique for " + x
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            raise AttributeError
        return self.lookup[attr]
    def whatis(self, value):
        return self.reverseLookup[value]

########NEW FILE########
__FILENAME__ = fixwallet
#!/usr/bin/env python
#
# Recover from a semi-corrupt wallet
#
from bsddb.db import *
import logging
import sys

from wallet import rewrite_wallet, trim_wallet
from util import determine_db_dir, create_env

def main():
  import optparse
  parser = optparse.OptionParser(usage="%prog [options]")
  parser.add_option("--datadir", dest="datadir", default=None,
                    help="Look for files here (defaults to bitcoin default)")
  parser.add_option("--out", dest="outfile", default="walletNEW.dat",
                    help="Name of output file (default: walletNEW.dat)")
  parser.add_option("--clean", action="store_true", dest="clean", default=False,
                    help="Clean out old, spent change addresses and transactions")
  parser.add_option("--skipkey", dest="skipkey",
                    help="Skip entries with keys that contain given string")
  parser.add_option("--tweakspent", dest="tweakspent",
                    help="Tweak transaction to mark unspent")
  parser.add_option("--noaccounts", action="store_true", dest="noaccounts", default=False,
                    help="Drops all accounts from the old wallet")
  parser.add_option("--nosettings", action="store_true", dest="nosettings", default=False,
                    help="Drops all settings from the old wallet")
  parser.add_option("--notxes", action="store_true", dest="notxes", default=False,
                    help="Drops transactions from the old wallet, open Bitcoin with -rescan after this")
  parser.add_option("--noaddresses", action="store_true", dest="nopubkeys", default=False,
                    help="Drops addresses from the old wallet, this will clear your address book leaving only one address\
                          WARNING: Make sure to refill your keypool after using this (by simply unlocking the wallet)")
  (options, args) = parser.parse_args()

  if options.datadir is None:
    db_dir = determine_db_dir()
  else:
    db_dir = options.datadir

  skip_types = []
  if options.nosettings:
    skip_types.append("version")
    skip_types.append("setting")
    skip_types.append("defaultkey")
  if options.noaccounts:
    skip_types.append("acc")
    skip_types.append("acentry")
  if options.notxes:
    skip_types.append("tx")
    skip_types.append("bestblock")
  if options.nopubkeys:
    skip_types.append("name")
    skip_types.append("pool")

  try:
    db_env = create_env(db_dir)
  except DBNoSuchFileError:
    logging.error("Couldn't open " + db_dir)
    sys.exit(1)

  if options.clean:
    trim_wallet(db_env, options.outfile)

  elif options.skipkey:
    def pre_put_callback(type, data):
      if options.skipkey in data['__key__']:
        return False
      return True
    rewrite_wallet(db_env, options.outfile, pre_put_callback)
  elif options.tweakspent:
    txid = options.tweakspent.decode('hex_codec')[::-1]
    def tweak_spent_callback(type, data):
      if txid in data['__key__']:
        data['__value__'] = data['__value__'][:-1]+'\0'
      return True
    rewrite_wallet(db_env, options.outfile, tweak_spent_callback)
    pass
  elif len(skip_types) > 0:
    def pre_put_callback(type, data):
      if skip_types.count(type) > 0:
        return False
      return True
    rewrite_wallet(db_env, options.outfile, pre_put_callback)
  else:
    rewrite_wallet(db_env, options.outfile)

  db_env.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = jsonToCSV
#!/usr/bin/env python
#
# Reads an array of JSON objects and writes out CSV-format,
# with key names in first row.
# Columns will be union of all keys in the objects.
#

import csv
import json
import sys

json_string = sys.stdin.read()
json_array = json.loads(json_string)

columns = set()
for item in json_array:
  columns.update(set(item))

writer = csv.writer(sys.stdout)
writer.writerow(list(columns))
for item in json_array:
  row = []
  for c in columns:
    if c in item: row.append(str(item[c]))
    else: row.append('')
  writer.writerow(row)
  

########NEW FILE########
__FILENAME__ = search_coinbases
#!/usr/bin/env python
#
# Scan through coinbase transactions
# in the block database and report on
# how many blocks match a regex
#
from bsddb.db import *
from datetime import date
import logging
import os
import re
import sys

from BCDataStream import *
from block import scan_blocks, CachedBlockFile
from collections import defaultdict
from deserialize import parse_Block
from util import determine_db_dir, create_env

def main():
  import optparse
  parser = optparse.OptionParser(usage="%prog [options]")
  parser.add_option("--datadir", dest="datadir", default=None,
                    help="Look for files here (defaults to bitcoin default)")
  parser.add_option("--regex", dest="lookfor", default="/P2SH/",
                    help="Look for string/regular expression (default: %default)")
  parser.add_option("--n", dest="howmany", default=999999, type="int",
                    help="Look back this many blocks (default: all)")
  parser.add_option("--start", dest="start", default=0, type="int",
                    help="Skip this many blocks to start (default: 0)")
  parser.add_option("--verbose", dest="verbose", default=False, action="store_true",
                    help="Print blocks that match")
  (options, args) = parser.parse_args()

  if options.datadir is None:
    db_dir = determine_db_dir()
  else:
    db_dir = options.datadir

  try:
    db_env = create_env(db_dir)
  except DBNoSuchFileError:
    logging.error("Couldn't open " + db_dir)
    sys.exit(1)

  blockfile = CachedBlockFile(db_dir)

  results = defaultdict(int)

  def count_matches(block_data):
    block_datastream = blockfile.get_stream(block_data['nFile'])
    block_datastream.seek_file(block_data['nBlockPos'])
    data = parse_Block(block_datastream)
    coinbase = data['transactions'][0]
    scriptSig = coinbase['txIn'][0]['scriptSig']
    if results['skipped'] < options.start:
      results['skipped'] += 1
    else:
      results['checked'] += 1
      if re.search(options.lookfor, scriptSig) is not None:
        results['matched'] += 1
        if options.verbose: print("Block %d : %s"%(block_data['nHeight'], scriptSig.encode('string_escape')) )

    results['searched'] += 1
    return results['searched'] < options.howmany

  scan_blocks(db_dir, db_env, count_matches)

  db_env.close()

  percent = (100.0*results['matched'])/results['checked']
  print("Found %d matches in %d blocks (%.1f percent)"%(results['matched'], results['checked'], percent))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = statistics
#!/usr/bin/env python
#
# Read the block database, generate monthly statistics and dump out
# a CSV file.
#
from bsddb.db import *
from datetime import date
import logging
import os
import sys

from BCDataStream import *
from block import scan_blocks, CachedBlockFile
from collections import defaultdict
from deserialize import parse_Block
from util import determine_db_dir, create_env

def main():
  import optparse
  parser = optparse.OptionParser(usage="%prog [options]")
  parser.add_option("--datadir", dest="datadir", default=None,
                    help="Look for files here (defaults to bitcoin default)")
  parser.add_option("--week", dest="week", default=False,
                    action="store_true",
                    help="Dump day-by-day for the last week's worth of blocks")
  (options, args) = parser.parse_args()

  if options.datadir is None:
    db_dir = determine_db_dir()
  else:
    db_dir = options.datadir

  try:
    db_env = create_env(db_dir)
  except DBNoSuchFileError:
    logging.error("Couldn't open " + db_dir)
    sys.exit(1)

  blockfile = CachedBlockFile(db_dir)

  n_transactions = defaultdict(int)
  v_transactions = defaultdict(float)
  v_transactions_min = defaultdict(float)
  v_transactions_max = defaultdict(float)

  def gather_stats(block_data):
    block_datastream = blockfile.get_stream(block_data['nFile'])
    block_datastream.seek_file(block_data['nBlockPos'])
    data = parse_Block(block_datastream)
    block_date = date.fromtimestamp(data['nTime'])
    key = "%d-%02d"%(block_date.year, block_date.month)
    for txn in data['transactions'][1:]:
      values = []
      for txout in txn['txOut']:
        n_transactions[key] += 1
        v_transactions[key] += txout['value'] 
        values.append(txout['value'])
      v_transactions_min[key] += min(values)
      v_transactions_max[key] += max(values)
    return True

  def gather_stats_week(block_data, lastDate):
    block_datastream = blockfile.get_stream(block_data['nFile'])
    block_datastream.seek_file(block_data['nBlockPos'])
    data = parse_Block(block_datastream)
    block_date = date.fromtimestamp(data['nTime'])
    if block_date < lastDate:
      return False
    key = "%d-%02d-%02d"%(block_date.year, block_date.month, block_date.day)
    for txn in data['transactions'][1:]:
      values = []
      for txout in txn['txOut']:
        n_transactions[key] += 1
        v_transactions[key] += txout['value'] 
        values.append(txout['value'])
      v_transactions_min[key] += min(values)
      v_transactions_max[key] += max(values)
    return True

  if options.week:
    lastDate = date.fromordinal(date.today().toordinal()-7)
    scan_blocks(db_dir, db_env, lambda x: gather_stats_week(x, lastDate) )
  else:
    scan_blocks(db_dir, db_env, gather_stats)

  db_env.close()

  print "date,nTransactions,minBTC,maxBTC,totalBTC"

  keys = n_transactions.keys()
  keys.sort()
  for k in keys:
    v = v_transactions[k]/1.0e8
    v_min = v_transactions_min[k]/1.0e8
    v_max = v_transactions_max[k]/1.0e8
    # Columns are:
    # month n_transactions min max total
    # ... where min and max add up just the smallest or largest
    # output in each transaction; the true value of bitcoins
    # transferred will be somewhere between min and max.
    # We don't know how many are transfers-to-self, though, and
    # this will undercount multi-txout-transactions (which is good
    # right now, because they're mostly used for mining pool
    # payouts that arguably shouldn't count).
    print "%s,%d,%.2f,%.2f,%.2f"%(k, n_transactions[k], v_min, v_max, v)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = testBCDataStream
#
# Unit tests for BCDataStream class
#

import unittest

import BCDataStream

class Tests(unittest.TestCase):
  def setUp(self):
    self.ds = BCDataStream.BCDataStream()

  def testString(self):
    t = {
      "\x07setting" : "setting",
      "\xfd\x00\x07setting" : "setting",
      "\xfe\x00\x00\x00\x07setting" : "setting",
      }
    for (input, output) in t.iteritems():
      self.ds.clear()
      self.ds.write(input)
      got = self.ds.read_string()
      self.assertEqual(output, got)

if __name__ == "__main__":
  unittest.main()

########NEW FILE########
__FILENAME__ = transaction
#
# Code for dumping a single transaction, given its ID
#

from bsddb.db import *
import logging
import os.path
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def _read_CDiskTxPos(stream):
  n_file = stream.read_uint32()
  n_block_pos = stream.read_uint32()
  n_tx_pos = stream.read_uint32()
  return (n_file, n_block_pos, n_tx_pos)

def _dump_tx(datadir, tx_hash, tx_pos):
  blockfile = open(os.path.join(datadir, "blk%04d.dat"%(tx_pos[0],)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, tx_pos[2])
  d = parse_Transaction(ds)
  print deserialize_Transaction(d)
  ds.close_file()
  blockfile.close()

def dump_transaction(datadir, db_env, tx_id):
  """ Dump a transaction, given hexadecimal tx_id-- either the full ID
      OR a short_hex version of the id.
  """
  db = DB(db_env)
  try:
    r = db.open("blkindex.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open blkindex.dat/main.  Try quitting any running Bitcoin apps.")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  n_tx = 0
  n_blockindex = 0

  key_prefix = "\x02tx"+(tx_id[-4:].decode('hex_codec')[::-1])
  cursor = db.cursor()
  (key, value) = cursor.set_range(key_prefix)

  while key.startswith(key_prefix):
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()
    hash256 = (kds.read_bytes(32))
    hash_hex = long_hex(hash256[::-1])
    version = vds.read_uint32()
    tx_pos = _read_CDiskTxPos(vds)
    if (hash_hex.startswith(tx_id) or short_hex(hash256[::-1]).startswith(tx_id)):
      _dump_tx(datadir, hash256, tx_pos)

    (key, value) = cursor.next()

  db.close()


########NEW FILE########
__FILENAME__ = util
#
# Misc util routines
#

try:
  from bsddb.db import *
except:
  pass

def long_hex(bytes):
  return bytes.encode('hex_codec')

def short_hex(bytes):
  t = bytes.encode('hex_codec')
  if len(t) < 11:
    return t
  return t[0:4]+"..."+t[-4:]

def determine_db_dir():
  import os
  import os.path
  import platform
  if platform.system() == "Darwin":
    return os.path.expanduser("~/Library/Application Support/Bitcoin/")
  elif platform.system() == "Windows":
    return os.path.join(os.environ['APPDATA'], "Bitcoin")
  return os.path.expanduser("~/.bitcoin")

def create_env(db_dir=None):
  if db_dir is None:
    db_dir = determine_db_dir()
  db_env = DBEnv(0)
  r = db_env.open(db_dir,
                  (DB_CREATE|DB_INIT_LOCK|DB_INIT_LOG|DB_INIT_MPOOL|
                   DB_INIT_TXN|DB_THREAD|DB_RECOVER))
  return db_env

########NEW FILE########
__FILENAME__ = wallet
#
# Code for parsing the wallet.dat file
#

from bsddb.db import *
import logging
import re
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address, bc_address_to_hash_160, hash_160
from util import short_hex, long_hex
from deserialize import *

def open_wallet(db_env, writable=False):
  db = DB(db_env)
  flags = DB_THREAD | (DB_CREATE if writable else DB_RDONLY)
  try:
    r = db.open("wallet.dat", "main", DB_BTREE, flags)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open wallet.dat/main. Try quitting Bitcoin and running this again.")
    sys.exit(1)
  
  return db

def parse_wallet(db, item_callback):
  kds = BCDataStream()
  vds = BCDataStream()

  for (key, value) in db.items():
    d = { }

    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    try:
      type = kds.read_string()

      d["__key__"] = key
      d["__value__"] = value
      d["__type__"] = type

    except Exception, e:
      print("ERROR attempting to read data from wallet.dat, type %s"%type)
      continue

    try:
      if type == "tx":
        d["tx_id"] = kds.read_bytes(32)
        d.update(parse_WalletTx(vds))
      elif type == "name":
        d['hash'] = kds.read_string()
        d['name'] = vds.read_string()
      elif type == "version":
        d['version'] = vds.read_uint32()
      elif type == "setting":
        d['setting'] = kds.read_string()
        d['value'] = parse_setting(d['setting'], vds)
      elif type == "key":
        d['public_key'] = kds.read_bytes(kds.read_compact_size())
        d['private_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "wkey":
        d['public_key'] = kds.read_bytes(kds.read_compact_size())
        d['private_key'] = vds.read_bytes(vds.read_compact_size())
        d['created'] = vds.read_int64()
        d['expires'] = vds.read_int64()
        d['comment'] = vds.read_string()
      elif type == "ckey":
        d['public_key'] = kds.read_bytes(kds.read_compact_size())
        d['crypted_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "mkey":
        d['nID'] = kds.read_int32()
        d['crypted_key'] = vds.read_bytes(vds.read_compact_size())
        d['salt'] = vds.read_bytes(vds.read_compact_size())
        d['nDerivationMethod'] = vds.read_int32()
        d['nDeriveIterations'] = vds.read_int32()
        d['vchOtherDerivationParameters'] = vds.read_bytes(vds.read_compact_size())
      elif type == "defaultkey":
        d['key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "pool":
        d['n'] = kds.read_int64()
        d['nVersion'] = vds.read_int32()
        d['nTime'] = vds.read_int64()
        d['public_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "acc":
        d['account'] = kds.read_string()
        d['nVersion'] = vds.read_int32()
        d['public_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "acentry":
        d['account'] = kds.read_string()
        d['n'] = kds.read_uint64()
        d['nVersion'] = vds.read_int32()
        d['nCreditDebit'] = vds.read_int64()
        d['nTime'] = vds.read_int64()
        d['otherAccount'] = vds.read_string()
        d['comment'] = vds.read_string()
      elif type == "bestblock":
        d['nVersion'] = vds.read_int32()
        d.update(parse_BlockLocator(vds))
      elif type == "cscript":
        d['scriptHash'] = kds.read_bytes(20)
        d['script'] = vds.read_bytes(vds.read_compact_size())
      else:
        print "Skipping item of type "+type
        continue
      
      item_callback(type, d)

    except Exception, e:
      print("ERROR parsing wallet.dat, type %s"%type)
      print("key data in hex: %s"%key.encode('hex_codec'))
      print("value data in hex: %s"%value.encode('hex_codec'))
  
def update_wallet(db, type, data):
  """Write a single item to the wallet.
  db must be open with writable=True.
  type and data are the type code and data dictionary as parse_wallet would
  give to item_callback.
  data's __key__, __value__ and __type__ are ignored; only the primary data
  fields are used.
  """
  d = data
  kds = BCDataStream()
  vds = BCDataStream()

  # Write the type code to the key
  kds.write_string(type)
  vds.write("")             # Ensure there is something

  try:
    if type == "tx":
      raise NotImplementedError("Writing items of type 'tx'")
      kds.write(d['tx_id'])
      #d.update(parse_WalletTx(vds))
    elif type == "name":
      kds.write(d['hash'])
      vds.write(d['name'])
    elif type == "version":
      vds.write_uint32(d['version'])
    elif type == "setting":
      raise NotImplementedError("Writing items of type 'setting'")
      kds.write_string(d['setting'])
      #d['value'] = parse_setting(d['setting'], vds)
    elif type == "key":
      kds.write_string(d['public_key'])
      vds.write_string(d['private_key'])
    elif type == "wkey":
      kds.write_string(d['public_key'])
      vds.write_string(d['private_key'])
      vds.write_int64(d['created'])
      vds.write_int64(d['expires'])
      vds.write_string(d['comment'])
    elif type == "ckey":
      kds.write_string(d['public_key'])
      kds.write_string(d['crypted_key'])
    elif type == "mkey":
      kds.write_int32(d['nID'])
      vds.write_string(d['crypted_key'])
      vds.write_string(d['salt'])
      vds.write_int32(d['nDeriveIterations'])
      vds.write_int32(d['nDerivationMethod'])
      vds.write_string(d['vchOtherDerivationParameters'])
    elif type == "defaultkey":
      vds.write_string(d['key'])
    elif type == "pool":
      kds.write_int64(d['n'])
      vds.write_int32(d['nVersion'])
      vds.write_int64(d['nTime'])
      vds.write_string(d['public_key'])
    elif type == "acc":
      kds.write_string(d['account'])
      vds.write_int32(d['nVersion'])
      vds.write_string(d['public_key'])
    elif type == "acentry":
      kds.write_string(d['account'])
      kds.write_uint64(d['n'])
      vds.write_int32(d['nVersion'])
      vds.write_int64(d['nCreditDebit'])
      vds.write_int64(d['nTime'])
      vds.write_string(d['otherAccount'])
      vds.write_string(d['comment'])
    elif type == "bestblock":
      vds.write_int32(d['nVersion'])
      vds.write_compact_size(len(d['hashes']))
      for h in d['hashes']:
        vds.write(h)
    else:
      print "Unknown key type: "+type

    # Write the key/value pair to the database
    db.put(kds.input, vds.input)

  except Exception, e:
    print("ERROR writing to wallet.dat, type %s"%type)
    print("data dictionary: %r"%data)

def dump_wallet(db_env, print_wallet, print_wallet_transactions, transaction_filter):
  db = open_wallet(db_env)

  wallet_transactions = []
  transaction_index = { }
  owner_keys = { }

  def item_callback(type, d):
    if type == "tx":
      wallet_transactions.append( d )
      transaction_index[d['tx_id']] = d
    elif type == "key":
      owner_keys[public_key_to_bc_address(d['public_key'])] = d['private_key']
    elif type == "ckey":
      owner_keys[public_key_to_bc_address(d['public_key'])] = d['crypted_key']

    if not print_wallet:
      return
    if type == "tx":
      return
    elif type == "name":
      print("ADDRESS "+d['hash']+" : "+d['name'])
    elif type == "version":
      print("Version: %d"%(d['version'],))
    elif type == "setting":
      print(d['setting']+": "+str(d['value']))
    elif type == "key":
      print("PubKey "+ short_hex(d['public_key']) + " " + public_key_to_bc_address(d['public_key']) +
            ": PriKey "+ short_hex(d['private_key']))
    elif type == "wkey":
      print("WPubKey 0x"+ short_hex(d['public_key']) + " " + public_key_to_bc_address(d['public_key']) +
            ": WPriKey 0x"+ short_hex(d['crypted_key']))
      print(" Created: "+time.ctime(d['created'])+" Expires: "+time.ctime(d['expires'])+" Comment: "+d['comment'])
    elif type == "ckey":
      print("PubKey "+ short_hex(d['public_key']) + " " + public_key_to_bc_address(d['public_key']) +
            ": Encrypted PriKey "+ short_hex(d['crypted_key']))
    elif type == "mkey":
      print("Master Key %d"%(d['nID']) + ": 0x"+ short_hex(d['crypted_key']) +
            ", Salt: 0x"+ short_hex(d['salt']) +
            ". Passphrase hashed %d times with method %d with other parameters 0x"%(d['nDeriveIterations'], d['nDerivationMethod']) +
            long_hex(d['vchOtherDerivationParameters']))
    elif type == "defaultkey":
      print("Default Key: 0x"+ short_hex(d['key']) + " " + public_key_to_bc_address(d['key']))
    elif type == "pool":
      print("Change Pool key %d: %s (Time: %s)"% (d['n'], public_key_to_bc_address(d['public_key']), time.ctime(d['nTime'])))
    elif type == "acc":
      print("Account %s (current key: %s)"%(d['account'], public_key_to_bc_address(d['public_key'])))
    elif type == "acentry":
      print("Move '%s' %d (other: '%s', time: %s, entry %d) %s"%
            (d['account'], d['nCreditDebit'], d['otherAccount'], time.ctime(d['nTime']), d['n'], d['comment']))
    elif type == "bestblock":
      print deserialize_BlockLocator(d)
    elif type == "cscript":
      print("CScript: %s : %s"%(public_key_to_bc_address(d['scriptHash'], "\x01"), long_hex(d['script'])))
    else:
      print "Unknown key type: "+type

  parse_wallet(db, item_callback)

  if print_wallet_transactions:
    keyfunc = lambda i: i['timeReceived']
    for d in sorted(wallet_transactions, key=keyfunc):
      tx_value = deserialize_WalletTx(d, transaction_index, owner_keys)
      if len(transaction_filter) > 0 and re.search(transaction_filter, tx_value) is None: continue

      print("==WalletTransaction== "+long_hex(d['tx_id'][::-1]))
      print(tx_value)

  db.close()

def dump_accounts(db_env):
  db = open_wallet(db_env)

  kds = BCDataStream()
  vds = BCDataStream()

  accounts = set()

  for (key, value) in db.items():
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "acc":
      accounts.add(kds.read_string())
    elif type == "name":
      accounts.add(vds.read_string())
    elif type == "acentry":
      accounts.add(kds.read_string())
      # Note: don't need to add otheraccount, because moves are
      # always double-entry

  for name in sorted(accounts):
    print(name)

  db.close()

def rewrite_wallet(db_env, destFileName, pre_put_callback=None):
  db = open_wallet(db_env)

  db_out = DB(db_env)
  try:
    r = db_out.open(destFileName, "main", DB_BTREE, DB_CREATE)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open %s."%destFileName)
    sys.exit(1)

  def item_callback(type, d):
    if (pre_put_callback is None or pre_put_callback(type, d)):
      db_out.put(d["__key__"], d["__value__"])

  parse_wallet(db, item_callback)

  db_out.close()
  db.close()

def trim_wallet(db_env, destFileName, pre_put_callback=None):
  """Write out ONLY address book public/private keys
     THIS WILL NOT WRITE OUT 'change' KEYS-- you should
     send all of your bitcoins to one of your public addresses
     before calling this.
  """
  db = open_wallet(db_env)
  
  pubkeys = []
  def gather_pubkeys(type, d):
    if type == "name":
      pubkeys.append(bc_address_to_hash_160(d['hash']))
  
  parse_wallet(db, gather_pubkeys)

  db_out = DB(db_env)
  try:
    r = db_out.open(destFileName, "main", DB_BTREE, DB_CREATE)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open %s."%destFileName)
    sys.exit(1)

  def item_callback(type, d):
    should_write = False
    if type in [ 'version', 'name', 'acc' ]:
      should_write = True
    if type in [ 'key', 'wkey', 'ckey' ] and hash_160(d['public_key']) in pubkeys:
      should_write = True
    if pre_put_callback is not None:
      should_write = pre_put_callback(type, d, pubkeys)
    if should_write:
      db_out.put(d["__key__"], d["__value__"])

  parse_wallet(db, item_callback)

  db_out.close()
  db.close()

########NEW FILE########
