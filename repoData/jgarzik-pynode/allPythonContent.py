__FILENAME__ = Cache

#
# Cache.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#


class Cache(object):
	def __init__(self, max=1000):
		self.d = {}
		self.l = []
		self.max = max

	def put(self, k, v):
		self.d[k] = v
		self.l.append(k)

		while (len(self.l) > self.max):
			kdel = self.l[0]
			del self.l[0]
			del self.d[kdel]

	def get(self, k):
		try:
			return self.d[k]
		except:
			return None

	def exists(self, k):
		return k in self.d


########NEW FILE########
__FILENAME__ = ChainDb

#
# ChainDb.py - Bitcoin blockchain database
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

import string
import cStringIO
import leveldb
import io
import os
import time
from decimal import Decimal
from Cache import Cache
from bitcoin.serialize import *
from bitcoin.core import *
from bitcoin.messages import msg_block, message_to_str, message_read
from bitcoin.coredefs import COIN
from bitcoin.scripteval import VerifySignature



def tx_blk_cmp(a, b):
	if a.dFeePerKB != b.dFeePerKB:
		return int(a.dFeePerKB - b.dFeePerKB)
	return int(a.dPriority - b.dPriority)

def block_value(height, fees):
	subsidy = 50 * COIN
	subsidy >>= (height / 210000)
	return subsidy + fees

class TxIdx(object):
	def __init__(self, blkhash=0L, spentmask=0L):
		self.blkhash = blkhash
		self.spentmask = spentmask


class BlkMeta(object):
	def __init__(self):
		self.height = -1
		self.work = 0L

	def deserialize(self, s):
		l = s.split()
		if len(l) < 2:
			raise RuntimeError
		self.height = int(l[0])
		self.work = long(l[1], 16)

	def serialize(self):
		r = str(self.height) + ' ' + hex(self.work)
		return r

	def __repr__(self):
		return "BlkMeta(height %d, work %x)" % (self.height, self.work)


class HeightIdx(object):
	def __init__(self):
		self.blocks = []

	def deserialize(self, s):
		self.blocks = []
		l = s.split()
		for hashstr in l:
			hash = long(hashstr, 16)
			self.blocks.append(hash)

	def serialize(self):
		l = []
		for blkhash in self.blocks:
			l.append(hex(blkhash))
		return ' '.join(l)

	def __repr__(self):
		return "HeightIdx(blocks=%s)" % (self.serialize(),)


class ChainDb(object):
	def __init__(self, settings, datadir, log, mempool, netmagic,
		     readonly=False, fast_dbm=False):
		self.settings = settings
		self.log = log
		self.mempool = mempool
		self.readonly = readonly
		self.netmagic = netmagic
		self.fast_dbm = fast_dbm
		self.blk_cache = Cache(500)
		self.orphans = {}
		self.orphan_deps = {}

		# LevelDB to hold:
		#    tx:*      transaction outputs
		#    misc:*    state
		#    height:*  list of blocks at height h
		#    blkmeta:* block metadata
		#    blocks:*  block seek point in stream
		self.blk_write = io.BufferedWriter(io.FileIO(datadir + '/blocks.dat','ab'))
		self.blk_read = io.BufferedReader(io.FileIO(datadir + '/blocks.dat','rb'))
		self.db = leveldb.LevelDB(datadir + '/leveldb')

		try:
			self.db.Get('misc:height')
		except KeyError:
			self.log.write("INITIALIZING EMPTY BLOCKCHAIN DATABASE")
			batch = leveldb.WriteBatch()
			batch.Put('misc:height', str(-1))
			batch.Put('misc:msg_start', self.netmagic.msg_start)
			batch.Put('misc:tophash', ser_uint256(0L))
			batch.Put('misc:total_work', hex(0L))
			self.db.Write(batch)

		try:
			start = self.db.Get('misc:msg_start')
			if start != self.netmagic.msg_start: raise KeyError
		except KeyError:
			self.log.write("Database magic number mismatch. Data corruption or incorrect network?")
			raise RuntimeError

	def puttxidx(self, txhash, txidx, batch=None):
		ser_txhash = ser_uint256(txhash)


		try:
			self.db.Get('tx:'+ser_txhash)
			old_txidx = self.gettxidx(txhash)
			self.log.write("WARNING: overwriting duplicate TX %064x, height %d, oldblk %064x, oldspent %x, newblk %064x" % (txhash, self.getheight(), old_txidx.blkhash, old_txidx.spentmask, txidx.blkhash))
		except KeyError:
			pass
		batch = self.db if batch is not None else batch
		batch.Put('tx:'+ser_txhash, hex(txidx.blkhash) + ' ' +
					       hex(txidx.spentmask))

		return True

	def gettxidx(self, txhash):
		ser_txhash = ser_uint256(txhash)
		try:
			ser_value = self.db.Get('tx:'+ser_txhash)
		except KeyError:
			return None

		pos = string.find(ser_value, ' ')

		txidx = TxIdx()
		txidx.blkhash = long(ser_value[:pos], 16)
		txidx.spentmask = long(ser_value[pos+1:], 16)

		return txidx

	def gettx(self, txhash):
		txidx = self.gettxidx(txhash)
		if txidx is None:
			return None

		block = self.getblock(txidx.blkhash)
		for tx in block.vtx:
			tx.calc_sha256()
			if tx.sha256 == txhash:
				return tx

		self.log.write("ERROR: Missing TX %064x in block %064x" % (txhash, txidx.blkhash))
		return None

	def haveblock(self, blkhash, checkorphans):
		if self.blk_cache.exists(blkhash):
			return True
		if checkorphans and blkhash in self.orphans:
			return True
		ser_hash = ser_uint256(blkhash)
		try: 
			self.db.Get('blocks:'+ser_hash)
			return True
		except KeyError:
			return False

	def have_prevblock(self, block):
		if self.getheight() < 0 and block.sha256 == self.netmagic.block0:
			return True
		if self.haveblock(block.hashPrevBlock, False):
			return True
		return False

	def getblock(self, blkhash):
		block = self.blk_cache.get(blkhash)
		if block is not None:
			return block

		ser_hash = ser_uint256(blkhash)
		try:
			# Lookup the block index, seek in the file
			fpos = long(self.db.Get('blocks:'+ser_hash))
			self.blk_read.seek(fpos)

			# read and decode "block" msg
			msg = message_read(self.netmagic, self.blk_read)
			if msg is None:
				return None
			block = msg.block
		except KeyError:
			return None

		self.blk_cache.put(blkhash, block)

		return block

	def spend_txout(self, txhash, n_idx, batch=None):
		txidx = self.gettxidx(txhash)
		if txidx is None:
			return False

		txidx.spentmask |= (1L << n_idx)
		self.puttxidx(txhash, txidx, batch)

		return True

	def clear_txout(self, txhash, n_idx, batch=None):
		txidx = self.gettxidx(txhash)
		if txidx is None:
			return False

		txidx.spentmask &= ~(1L << n_idx)
		self.puttxidx(txhash, txidx, batch)

		return True

	def unique_outpts(self, block):
		outpts = {}
		txmap = {}
		for tx in block.vtx:
			if tx.is_coinbase:
				continue
			txmap[tx.sha256] = tx
			for txin in tx.vin:
				v = (txin.prevout.hash, txin.prevout.n)
				if v in outs:
					return None

				outpts[v] = False

		return (outpts, txmap)

	def txout_spent(self, txout):
		txidx = self.gettxidx(txout.hash)
		if txidx is None:
			return None

		if txout.n > 100000:	# outpoint index sanity check
			return None

		if txidx.spentmask & (1L << txout.n):
			return True

		return False

	def spent_outpts(self, block):
		# list of outpoints this block wants to spend
		l = self.unique_outpts(block)
		if l is None:
			return None
		outpts = l[0]
		txmap = l[1]
		spendlist = {}

		# pass 1: if outpoint in db, make sure it is unspent
		for k in outpts.iterkeys():
			outpt = COutPoint()
			outpt.hash = k[0]
			outpt.n = k[1]
			rc = self.txout_spent(outpt)
			if rc is None:
				continue
			if rc:
				return None

			outpts[k] = True	# skip in pass 2

		# pass 2: remaining outpoints must exist in this block
		for k, v in outpts.iteritems():
			if v:
				continue

			if k[0] not in txmap:	# validate txout hash
				return None

			tx = txmap[k[0]]	# validate txout index (n)
			if k[1] >= len(tx.vout):
				return None

			# outpts[k] = True	# not strictly necessary

		return outpts.keys()

	def tx_signed(self, tx, block, check_mempool):
		tx.calc_sha256()

		for i in xrange(len(tx.vin)):
			txin = tx.vin[i]

			# search database for dependent TX
			txfrom = self.gettx(txin.prevout.hash)

			# search block for dependent TX
			if txfrom is None and block is not None:
				for blktx in block.vtx:
					blktx.calc_sha256()
					if blktx.sha256 == txin.prevout.hash:
						txfrom = blktx
						break

			# search mempool for dependent TX
			if txfrom is None and check_mempool:
				try:
					txfrom = self.mempool.pool[txin.prevout.hash]
				except:
					self.log.write("TX %064x/%d no-dep %064x" %
							(tx.sha256, i,
							 txin.prevout.hash))
					return False
			if txfrom is None:
				self.log.write("TX %064x/%d no-dep %064x" %
						(tx.sha256, i,
						 txin.prevout.hash))
				return False

			if not VerifySignature(txfrom, tx, i, 0):
				self.log.write("TX %064x/%d sigfail" %
						(tx.sha256, i))
				return False

		return True

	def tx_is_orphan(self, tx):
		if not tx.is_valid():
			return None

		for txin in tx.vin:
			rc = self.txout_spent(txin.prevout)
			if rc is None:		# not found: orphan
				try:
					txfrom = self.mempool.pool[txin.prevout.hash]
				except:
					return True
				if txin.prevout.n >= len(txfrom.vout):
					return None
			if rc is True:		# spent? strange
				return None

		return False

	def connect_block(self, ser_hash, block, blkmeta):
		# verify against checkpoint list
		try:
			chk_hash = self.netmagic.checkpoints[blkmeta.height]
			if chk_hash != block.sha256:
				self.log.write("Block %064x does not match checkpoint hash %064x, height %d" % (
					block.sha256, chk_hash, blkmeta.height))
				return False
		except KeyError:
			pass
			
		# check TX connectivity
		outpts = self.spent_outpts(block)
		if outpts is None:
			self.log.write("Unconnectable block %064x" % (block.sha256, ))
			return False

		# verify script signatures
		if ('nosig' not in self.settings and
		    ('forcesig' in self.settings or
		     blkmeta.height > self.netmagic.checkpoint_max)):
			for tx in block.vtx:
				tx.calc_sha256()

				if tx.is_coinbase():
					continue

				if not self.tx_signed(tx, block, False):
					self.log.write("Invalid signature in block %064x" % (block.sha256, ))
					return False

		# update database pointers for best chain
		batch = leveldb.WriteBatch()
		batch.Put('misc:total_work', hex(blkmeta.work))
		batch.Put('misc:height', str(blkmeta.height))
		batch.Put('misc:tophash', ser_hash)

		self.log.write("ChainDb: height %d, block %064x" % (
				blkmeta.height, block.sha256))

		# all TX's in block are connectable; index
		neverseen = 0
		for tx in block.vtx:
                        tx.calc_sha256()

			if not self.mempool.remove(tx.sha256):
				neverseen += 1

			txidx = TxIdx(block.sha256)
			if not self.puttxidx(tx.sha256, txidx, batch):
				self.log.write("TxIndex failed %064x" % (tx.sha256,))
				return False

		self.log.write("MemPool: blk.vtx.sz %d, neverseen %d, poolsz %d" % (len(block.vtx), neverseen, self.mempool.size()))

		# mark deps as spent
		for outpt in outpts:
			self.spend_txout(outpt[0], outpt[1], batch)

		self.db.Write(batch)
		return True

	def disconnect_block(self, block):
		ser_prevhash = ser_uint256(block.hashPrevBlock)
		prevmeta = BlkMeta()
		prevmeta.deserialize(self.db.Get('blkmeta:'+ser_prevhash))

		tup = self.unique_outpts(block)
		if tup is None:
			return False

		outpts = tup[0]

		# mark deps as unspent
		batch = leveldb.WriteBatch()
		for outpt in outpts:
			self.clear_txout(outpt[0], outpt[1], batch)

		# update tx index and memory pool
		for tx in block.vtx:
			tx.calc_sha256()
			ser_hash = ser_uint256(tx.sha256)
			try:
				batch.Delete('tx:'+ser_hash)
			except KeyError:
				pass

			if not tx.is_coinbase():
				self.mempool.add(tx)

		# update database pointers for best chain
		batch.Put('misc:total_work', hex(prevmeta.work))
		batch.Put('misc:height', str(prevmeta.height))
		batch.Put('misc:tophash', ser_prevhash)
		self.db.Write(batch)

		self.log.write("ChainDb(disconn): height %d, block %064x" % (
				prevmeta.height, block.hashPrevBlock))

		return True

	def getblockmeta(self, blkhash):
		ser_hash = ser_uint256(blkhash)
		try:
			meta = BlkMeta()
			meta.deserialize(self.db.Get('blkmeta:'+ser_hash))
		except KeyError:
			return None

		return meta
	
	def getblockheight(self, blkhash):
		meta = self.getblockmeta(blkhash)
		if meta is None:
			return -1

		return meta.height

	def reorganize(self, new_best_blkhash):
		self.log.write("REORGANIZE")

		conn = []
		disconn = []

		old_best_blkhash = self.gettophash()
		fork = old_best_blkhash
		longer = new_best_blkhash
		while fork != longer:
			while (self.getblockheight(longer) >
			       self.getblockheight(fork)):
				block = self.getblock(longer)
				block.calc_sha256()
				conn.append(block)

				longer = block.hashPrevBlock
				if longer == 0:
					return False

			if fork == longer:
				break

			block = self.getblock(fork)
			block.calc_sha256()
			disconn.append(block)

			fork = block.hashPrevBlock
			if fork == 0:
				return False

		self.log.write("REORG disconnecting top hash %064x" % (old_best_blkhash,))
		self.log.write("REORG connecting new top hash %064x" % (new_best_blkhash,))
		self.log.write("REORG chain union point %064x" % (fork,))
		self.log.write("REORG disconnecting %d blocks, connecting %d blocks" % (len(disconn), len(conn)))

		for block in disconn:
			if not self.disconnect_block(block):
				return False

		for block in conn:
			if not self.connect_block(ser_uint256(block.sha256),
				  block, self.getblockmeta(block.sha256)):
				return False

		self.log.write("REORGANIZE DONE")
		return True

	def set_best_chain(self, ser_prevhash, ser_hash, block, blkmeta):
		# the easy case, extending current best chain
		if (blkmeta.height == 0 or
		    self.db.Get('misc:tophash') == ser_prevhash):
			return self.connect_block(ser_hash, block, blkmeta)

		# switching from current chain to another, stronger chain
		return self.reorganize(block.sha256)

	def putoneblock(self, block):
		block.calc_sha256()

		if not block.is_valid():
			self.log.write("Invalid block %064x" % (block.sha256, ))
			return False

		if not self.have_prevblock(block):
			self.orphans[block.sha256] = True
			self.orphan_deps[block.hashPrevBlock] = block
			self.log.write("Orphan block %064x (%d orphans)" % (block.sha256, len(self.orphan_deps)))
			return False

		top_height = self.getheight()
		top_work = long(self.db.Get('misc:total_work'), 16)

		# read metadata for previous block
		prevmeta = BlkMeta()
		if top_height >= 0:
			ser_prevhash = ser_uint256(block.hashPrevBlock)
			prevmeta.deserialize(self.db.Get('blkmeta:'+ser_prevhash))
		else:
			ser_prevhash = ''

		batch = leveldb.WriteBatch()

		# build network "block" msg, as canonical disk storage form
		msg = msg_block()
		msg.block = block
		msg_data = message_to_str(self.netmagic, msg)

		# write "block" msg to storage
		fpos = self.blk_write.tell()
		self.blk_write.write(msg_data)
		self.blk_write.flush()

		# add index entry
		ser_hash = ser_uint256(block.sha256)
		batch.Put('blocks:'+ser_hash, str(fpos))

		# store metadata related to this block
		blkmeta = BlkMeta()
		blkmeta.height = prevmeta.height + 1
		blkmeta.work = (prevmeta.work +
				uint256_from_compact(block.nBits))
		batch.Put('blkmeta:'+ser_hash, blkmeta.serialize())

		# store list of blocks at this height
		heightidx = HeightIdx()
		heightstr = str(blkmeta.height)
		try:
			heightidx.deserialize(self.db.Get('height:'+heightstr))
		except KeyError:
			pass
		heightidx.blocks.append(block.sha256)

		batch.Put('height:'+heightstr, heightidx.serialize())
		self.db.Write(batch)

		# if chain is not best chain, proceed no further
		if (blkmeta.work <= top_work):
			self.log.write("ChainDb: height %d (weak), block %064x" % (blkmeta.height, block.sha256))
			return True

		# update global chain pointers
		if not self.set_best_chain(ser_prevhash, ser_hash,
					   block, blkmeta):
			return False

		return True

	def putblock(self, block):
		block.calc_sha256()
		if self.haveblock(block.sha256, True):
			self.log.write("Duplicate block %064x submitted" % (block.sha256, ))
			return False

		if not self.putoneblock(block):
			return False

		blkhash = block.sha256
		while blkhash in self.orphan_deps:
			block = self.orphan_deps[blkhash]
			if not self.putoneblock(block):
				return True

			del self.orphan_deps[blkhash]
			del self.orphans[block.sha256]

			blkhash = block.sha256

		return True

	def locate(self, locator):
		for hash in locator.vHave:
			ser_hash = ser_uint256(hash)
			if ser_hash in self.blkmeta:
				blkmeta = BlkMeta()
				blkmeta.deserialize(self.db.Get('blkmeta:'+ser_hash))
				return blkmeta
		return 0

	def getheight(self):
		return int(self.db.Get('misc:height'))

	def gettophash(self):
		return uint256_from_str(self.db.Get('misc:tophash'))

	def loadfile(self, filename):
		fd = os.open(filename, os.O_RDONLY)
		self.log.write("IMPORTING DATA FROM " + filename)
		buf = ''
		wanted = 4096
		while True:
			if wanted > 0:
				if wanted < 4096:
					wanted = 4096
				s = os.read(fd, wanted)
				if len(s) == 0:
					break

				buf += s
				wanted = 0

			buflen = len(buf)
			startpos = string.find(buf, self.netmagic.msg_start)
			if startpos < 0:
				wanted = 8
				continue

			sizepos = startpos + 4
			blkpos = startpos + 8
			if blkpos > buflen:
				wanted = 8
				continue

			blksize = struct.unpack("<i", buf[sizepos:blkpos])[0]
			if (blkpos + blksize) > buflen:
				wanted = 8 + blksize
				continue

			ser_blk = buf[blkpos:blkpos+blksize]
			buf = buf[blkpos+blksize:]

			f = cStringIO.StringIO(ser_blk)
			block = CBlock()
			block.deserialize(f)

			self.putblock(block)

	def newblock_txs(self):
		txlist = []
		for tx in self.mempool.pool.itervalues():

			# query finalized, non-coinbase mempool tx's
			if tx.is_coinbase() or not tx.is_final():
				continue

			# iterate through inputs, calculate total input value
			valid = True
			nValueIn = 0
			nValueOut = 0
			dPriority = Decimal(0)

			for tin in tx.vin:
				in_tx = self.gettx(tin.prevout.hash)
				if (in_tx is None or
				    tin.prevout.n >= len(in_tx.vout)):
					valid = False
				else:
					v = in_tx.vout[tin.prevout.n].nValue
					nValueIn += v
					dPriority += Decimal(v * 1)

			if not valid:
				continue

			# iterate through outputs, calculate total output value
			for txout in tx.vout:
				nValueOut += txout.nValue

			# calculate fees paid, if any
			tx.nFeesPaid = nValueIn - nValueOut
			if tx.nFeesPaid < 0:
				continue

			# calculate fee-per-KB and priority
			tx.ser_size = len(tx.serialize())

			dPriority /= Decimal(tx.ser_size)

			tx.dFeePerKB = (Decimal(tx.nFeesPaid) /
					(Decimal(tx.ser_size) / Decimal(1000)))
			if tx.dFeePerKB < Decimal(50000):
				tx.dFeePerKB = Decimal(0)
			tx.dPriority = dPriority

			txlist.append(tx)

		# sort list by fee-per-kb, then priority
		sorted_txlist = sorted(txlist, cmp=tx_blk_cmp, reverse=True)

		# build final list of transactions.  thanks to sort
		# order above, we add TX's to the block in the
		# highest-fee-first order.  free transactions are
		# then appended in order of priority, until
		# free_bytes is exhausted.
		txlist = []
		txlist_bytes = 0
		free_bytes = 50000
		while len(sorted_txlist) > 0:
			tx = sorted_txlist.pop()
			if txlist_bytes + tx.ser_size > (900 * 1000):
				continue

			if tx.dFeePerKB > 0:
				txlist.append(tx)
				txlist_bytes += tx.ser_size
			elif free_bytes >= tx.ser_size:
				txlist.append(tx)
				txlist_bytes += tx.ser_size
				free_bytes -= tx.ser_size
		
		return txlist

	def newblock(self):
		tophash = self.gettophash()
		prevblock = self.getblock(tophash)
		if prevblock is None:
			return None

		# obtain list of candidate transactions for a new block
		total_fees = 0
		txlist = self.newblock_txs()
		for tx in txlist:
			total_fees += tx.nFeesPaid

		#
		# build coinbase
		#
		txin = CTxIn()
		txin.prevout.set_null()
		# FIXME: txin.scriptSig

		txout = CTxOut()
		txout.nValue = block_value(self.getheight(), total_fees)
		# FIXME: txout.scriptPubKey

		coinbase = CTransaction()
		coinbase.vin.append(txin)
		coinbase.vout.append(txout)

		#
		# build block
		#
		block = CBlock()
		block.hashPrevBlock = tophash
		block.nTime = int(time.time())
		block.nBits = prevblock.nBits	# TODO: wrong
		block.vtx.append(coinbase)
		block.vtx.extend(txlist)
		block.hashMerkleRoot = block.calc_merkle()

		return block


########NEW FILE########
__FILENAME__ = dbck
#!/usr/bin/python
#
# dbck.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#


import sys
import Log
import MemPool
import ChainDb
import cStringIO

from bitcoin.coredefs import NETWORKS
from bitcoin.core import CBlock
from bitcoin.scripteval import *

NET_SETTINGS = {
	'mainnet' : {
		'log' : '/spare/tmp/dbck.log',
		'db' : '/spare/tmp/chaindb'
	},
	'testnet3' : {
		'log' : '/spare/tmp/dbcktest.log',
		'db' : '/spare/tmp/chaintest'
	}
}

MY_NETWORK = 'mainnet'

SETTINGS = NET_SETTINGS[MY_NETWORK]

log = Log.Log(SETTINGS['log'])
mempool = MemPool.MemPool(log)
chaindb = ChainDb.ChainDb(SETTINGS['db'], log, mempool, NETWORKS[MY_NETWORK])

scanned = 0
failures = 0

for height in xrange(chaindb.getheight()):
	heightidx = ChainDb.HeightIdx()
	heightidx.deserialize(chaindb.height[str(height)])

	blkhash = heightidx.blocks[0]
	ser_hash = ser_uint256(blkhash)

	f = cStringIO.StringIO(chaindb.blocks[ser_hash])
	block = CBlock()
	block.deserialize(f)

	if not block.is_valid():
		log.write("block %064x failed" % (blkhash,))
		failures += 1

	scanned += 1
	if (scanned % 1000) == 0:
		log.write("Scanned height %d (%d failures)" % (
			height, failures))


log.write("Scanned %d blocks (%d failures)" % (scanned, failures))


########NEW FILE########
__FILENAME__ = Log

#
# Log.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

import sys


class Log(object):
	def __init__(self, filename=None):
		if filename is not None:
			self.fh = open(filename, 'a+', 0)
		else:
			self.fh = sys.stdout

	def write(self, msg):
		line = "%s\n" % msg
		self.fh.write(line)


########NEW FILE########
__FILENAME__ = MemPool

#
# MemPool.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

from bitcoin.serialize import uint256_to_shortstr


class MemPool(object):
	def __init__(self, log):
		self.pool = {}
		self.log = log

	def add(self, tx):
		tx.calc_sha256()
		hash = tx.sha256
		hashstr = uint256_to_shortstr(hash)

		if hash in self.pool:
			self.log.write("MemPool.add(%s): already known" % (hashstr,))
			return False
		if not tx.is_valid():
			self.log.write("MemPool.add(%s): invalid TX" % (hashstr, ))
			return False

		self.pool[hash] = tx

		self.log.write("MemPool.add(%s), poolsz %d" % (hashstr, len(self.pool)))

		return True

	def remove(self, hash):
		if hash not in self.pool:
			return False

		del self.pool[hash]
		return True

	def size(self):
		return len(self.pool)



########NEW FILE########
__FILENAME__ = mkbootstrap
#!/usr/bin/python
#
# mkbootstrap.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#


import sys
import Log
import MemPool
import ChainDb
import cStringIO
import struct
import argparse

from bitcoin.coredefs import NETWORKS
from bitcoin.core import CBlock
from bitcoin.scripteval import *

NET_SETTINGS = {
	'mainnet' : {
		'log' : '/spare/tmp/mkbootstrap.log',
		'db' : '/spare/tmp/chaindb'
	},
	'testnet3' : {
		'log' : '/spare/tmp/mkbootstraptest.log',
		'db' : '/spare/tmp/chaintest'
	}
}

MY_NETWORK = 'mainnet'

SETTINGS = NET_SETTINGS[MY_NETWORK]

opts = argparse.ArgumentParser(description='Create blockchain datafile')
opts.add_argument('--latest', dest='latest', action='store_true')

args = opts.parse_args()

# to log to a file
# log = Log.Log(SETTINGS['log'])

# stdout logging
log = Log.Log()

mempool = MemPool.MemPool(log)
netmagic = NETWORKS[MY_NETWORK]
chaindb = ChainDb.ChainDb(SETTINGS, SETTINGS['db'], log, mempool, netmagic,
			  True)

if args.latest:
	scan_height = chaindb.getheight()
else:
	scan_height = 216116
	
out_fn = 'bootstrap.dat'
log.write("Outputting to %s, up to height %d" % (out_fn, scan_height))

outf = open(out_fn, 'wb')

scanned = 0
failures = 0

for height in xrange(scan_height+1):
	heightidx = ChainDb.HeightIdx()
	heightstr = str(height)
	try:
		heightidx.deserialize(chaindb.db.Get('height:'+heightstr))
	except KeyError:
		log.write("Height " + str(height) + " not found.")
		continue

	blkhash = heightidx.blocks[0]

	block = chaindb.getblock(blkhash)

	ser_block = block.serialize()

	outhdr = netmagic.msg_start
	outhdr += struct.pack("<i", len(ser_block))

	outf.write(outhdr)
	outf.write(ser_block)

	scanned += 1
	if (scanned % 1000) == 0:
		log.write("Scanned height %d (%d failures)" % (
			height, failures))

log.write("Scanned %d blocks (%d failures)" % (scanned, failures))


########NEW FILE########
__FILENAME__ = node
#!/usr/bin/python
#
# node.py - Bitcoin P2P network half-a-node
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

import gevent
import gevent.pywsgi
from gevent import Greenlet

import signal
import struct
import socket
import binascii
import time
import sys
import re
import random
import cStringIO
import copy
import re
import hashlib
import rpc

import ChainDb
import MemPool
import Log
from bitcoin.core import *
from bitcoin.serialize import *
from bitcoin.messages import *

MY_SUBVERSION = "/pynode:0.0.1/"

settings = {}
debugnet = False


def verbose_sendmsg(message):
	if debugnet:
		return True
	if message.command != 'getdata':
		return True
	return False


def verbose_recvmsg(message):
	skipmsg = {
		'tx',
		'block',
		'inv',
		'addr',
	}
	if debugnet:
		return True
	if message.command in skipmsg:
		return False
	return True


class NodeConn(Greenlet):
	def __init__(self, dstaddr, dstport, log, peermgr,
			 mempool, chaindb, netmagic):
		Greenlet.__init__(self)
		self.log = log
		self.peermgr = peermgr
		self.mempool = mempool
		self.chaindb = chaindb
		self.netmagic = netmagic
		self.dstaddr = dstaddr
		self.dstport = dstport
		self.sock = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.recvbuf = ""
		self.ver_send = MIN_PROTO_VERSION
		self.ver_recv = MIN_PROTO_VERSION
		self.last_sent = 0
		self.getblocks_ok = True
		self.last_block_rx = time.time()
		self.last_getblocks = 0
		self.remote_height = -1

		self.hash_continue = None

		self.log.write("connecting")
		try:
			self.sock.connect((dstaddr, dstport))
		except:
			self.handle_close()

		#stuff version msg into sendbuf
		vt = msg_version()
		vt.addrTo.ip = self.dstaddr
		vt.addrTo.port = self.dstport
		vt.addrFrom.ip = "0.0.0.0"
		vt.addrFrom.port = 0
		vt.nStartingHeight = self.chaindb.getheight()
		vt.strSubVer = MY_SUBVERSION
		self.send_message(vt)

	def _run(self):
		self.log.write(self.dstaddr + " connected")
		while True:
			try:
				t = self.sock.recv(8192)
				if len(t) <= 0: raise ValueError
			except (IOError, ValueError):
				self.handle_close()
				return
			self.recvbuf += t
			self.got_data()

	def handle_close(self):
		self.log.write(self.dstaddr + " close")
		self.recvbuf = ""
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.close()
		except:
			pass

	def got_data(self):
		while True:
			if len(self.recvbuf) < 4:
				return
			if self.recvbuf[:4] != self.netmagic.msg_start:
				raise ValueError("got garbage %s" % repr(self.recvbuf))
			# check checksum
			if len(self.recvbuf) < 4 + 12 + 4 + 4:
				return
			command = self.recvbuf[4:4+12].split("\x00", 1)[0]
			msglen = struct.unpack("<i", self.recvbuf[4+12:4+12+4])[0]
			checksum = self.recvbuf[4+12+4:4+12+4+4]
			if len(self.recvbuf) < 4 + 12 + 4 + 4 + msglen:
				return
			msg = self.recvbuf[4+12+4+4:4+12+4+4+msglen]
			th = hashlib.sha256(msg).digest()
			h = hashlib.sha256(th).digest()
			if checksum != h[:4]:
				raise ValueError("got bad checksum %s" % repr(self.recvbuf))
			self.recvbuf = self.recvbuf[4+12+4+4+msglen:]

			if command in messagemap:
				f = cStringIO.StringIO(msg)
				t = messagemap[command](self.ver_recv)
				t.deserialize(f)
				self.got_message(t)
			else:
				self.log.write("UNKNOWN COMMAND %s %s" % (command, repr(msg)))

	def send_message(self, message):
		if verbose_sendmsg(message):
			self.log.write("send %s" % repr(message))

		tmsg = message_to_str(self.netmagic, message)

		try:
			self.sock.sendall(tmsg)
			self.last_sent = time.time()
		except:
			self.handle_close()

	def send_getblocks(self, timecheck=True):
		if not self.getblocks_ok:
			return
		now = time.time()
		if timecheck and (now - self.last_getblocks) < 5:
			return
		self.last_getblocks = now

		our_height = self.chaindb.getheight()
		if our_height < 0:
			gd = msg_getdata(self.ver_send)
			inv = CInv()
			inv.type = 2
			inv.hash = self.netmagic.block0
			gd.inv.append(inv)
			self.send_message(gd)
		elif our_height < self.remote_height:
			gb = msg_getblocks(self.ver_send)
			if our_height >= 0:
				gb.locator.vHave.append(self.chaindb.gettophash())
			self.send_message(gb)

	def got_message(self, message):
		gevent.sleep()

		if self.last_sent + 30 * 60 < time.time():
			self.send_message(msg_ping(self.ver_send))

		if verbose_recvmsg(message):
			self.log.write("recv %s" % repr(message))

		if message.command == "version":
			self.ver_send = min(PROTO_VERSION, message.nVersion)
			if self.ver_send < MIN_PROTO_VERSION:
				self.log.write("Obsolete version %d, closing" % (self.ver_send,))
				self.handle_close()
				return

			if (self.ver_send >= NOBLKS_VERSION_START and
			    self.ver_send <= NOBLKS_VERSION_END):
				self.getblocks_ok = False

			self.remote_height = message.nStartingHeight
			self.send_message(msg_verack(self.ver_send))
			if self.ver_send >= CADDR_TIME_VERSION:
				self.send_message(msg_getaddr(self.ver_send))
			self.send_getblocks()

		elif message.command == "verack":
			self.ver_recv = self.ver_send

#			if self.ver_send >= MEMPOOL_GD_VERSION:
#				self.send_message(msg_mempool())

		elif message.command == "ping":
			if self.ver_send > BIP0031_VERSION:
				self.send_message(msg_pong(self.ver_send))

		elif message.command == "addr":
			peermgr.new_addrs(message.addrs)

		elif message.command == "inv":

			# special message sent to kick getblocks
			if (len(message.inv) == 1 and
			    message.inv[0].type == MSG_BLOCK and
			    self.chaindb.haveblock(message.inv[0].hash, True)):
				self.send_getblocks(False)
				return

			want = msg_getdata(self.ver_send)
			for i in message.inv:
				if i.type == 1:
					want.inv.append(i)
				elif i.type == 2:
					want.inv.append(i)
			if len(want.inv):
				self.send_message(want)

		elif message.command == "tx":
			if self.chaindb.tx_is_orphan(message.tx):
				self.log.write("MemPool: Ignoring orphan TX %064x" % (message.tx.sha256,))
			elif not self.chaindb.tx_signed(message.tx, None, True):
				self.log.write("MemPool: Ignoring failed-sig TX %064x" % (message.tx.sha256,))
			else:
				self.mempool.add(message.tx)

		elif message.command == "block":
			self.chaindb.putblock(message.block)
			self.last_block_rx = time.time()

		elif message.command == "getdata":
			self.getdata(message)

		elif message.command == "getblocks":
			self.getblocks(message)

		elif message.command == "getheaders":
			self.getheaders(message)

		elif message.command == "getaddr":
			msg = msg_addr()
			msg.addrs = peermgr.random_addrs()

			self.send_message(msg)

		elif message.command == "mempool":
			msg = msg_inv()
			for k in self.mempool.pool.iterkeys():
				inv = CInv()
				inv.type = MSG_TX
				inv.hash = k
				msg.inv.append(inv)

				if len(msg.inv) == 50000:
					break

			self.send_message(msg)

		# if we haven't seen a 'block' message in a little while,
		# and we're still not caught up, send another getblocks
		last_blkmsg = time.time() - self.last_block_rx
		if last_blkmsg > 5:
			self.send_getblocks()

	def getdata_tx(self, txhash):
		if txhash in self.mempool.pool:
			tx = self.mempool.pool[txhash]
		else:
			tx = self.chaindb.gettx(txhash)
			if tx is None:
				return

		msg = msg_tx()
		msg.tx = tx

		self.send_message(msg)

	def getdata_block(self, blkhash):
		block = self.chaindb.getblock(blkhash)
		if block is None:
			return

		msg = msg_block()
		msg.block = block

		self.send_message(msg)

		if blkhash == self.hash_continue:
			self.hash_continue = None

			inv = CInv()
			inv.type = MSG_BLOCK
			inv.hash = self.chaindb.gettophash()

			msg = msg_inv()
			msg.inv.append(inv)

			self.send_message(msg)

	def getdata(self, message):
		if len(message.inv) > 50000:
			self.handle_close()
			return
		for inv in message.inv:
			if inv.type == MSG_TX:
				self.getdata_tx(inv.hash)
			elif inv.type == MSG_BLOCK:
				self.getdata_block(inv.hash)

	def getblocks(self, message):
		blkmeta = self.chaindb.locate(message.locator)
		height = blkmeta.height
		top_height = self.getheight()
		end_height = height + 500
		if end_height > top_height:
			end_height = top_height

		msg = msg_inv()
		while height <= end_height:
			hash = long(self.chaindb.height[str(height)])
			if hash == message.hashstop:
				break

			inv = CInv()
			inv.type = MSG_BLOCK
			inv.hash = hash
			msg.inv.append(inv)

			height += 1

		if len(msg.inv) > 0:
			self.send_message(msg)
			if height <= top_height:
				self.hash_continue = msg.inv[-1].hash

	def getheaders(self, message):
		blkmeta = self.chaindb.locate(message.locator)
		height = blkmeta.height
		top_height = self.getheight()
		end_height = height + 2000
		if end_height > top_height:
			end_height = top_height

		msg = msg_headers()
		while height <= end_height:
			blkhash = long(self.chaindb.height[str(height)])
			if blkhash == message.hashstop:
				break

			db_block = self.chaindb.getblock(blkhash)
			block = copy.copy(db_block)
			block.vtx = []

			msg.headers.append(block)

			height += 1

		self.send_message(msg)


class PeerManager(object):
	def __init__(self, log, mempool, chaindb, netmagic):
		self.log = log
		self.mempool = mempool
		self.chaindb = chaindb
		self.netmagic = netmagic
		self.peers = []
		self.addrs = {}
		self.tried = {}

	def add(self, host, port):
		self.log.write("PeerManager: connecting to %s:%d" %
			       (host, port))
		self.tried[host] = True
		c = NodeConn(host, port, self.log, self, self.mempool,
			     self.chaindb, self.netmagic)
		self.peers.append(c)
		return c

	def new_addrs(self, addrs):
		for addr in addrs:
			if addr.ip in self.addrs:
				continue
			self.addrs[addr.ip] = addr

		self.log.write("PeerManager: Received %d new addresses (%d addrs, %d tried)" %
				(len(addrs), len(self.addrs),
				 len(self.tried)))

	def random_addrs(self):
		ips = self.addrs.keys()
		random.shuffle(ips)
		if len(ips) > 1000:
			del ips[1000:]

		vaddr = []
		for ip in ips:
			vaddr.append(self.addrs[ip])

		return vaddr

	def closeall(self):
		for peer in self.peers:
			peer.handle_close()
		self.peers = []


if __name__ == '__main__':
	if len(sys.argv) != 2:
		print("Usage: node.py CONFIG-FILE")
		sys.exit(1)

	f = open(sys.argv[1])
	for line in f:
		m = re.search('^(\w+)\s*=\s*(\S.*)$', line)
		if m is None:
			continue
		settings[m.group(1)] = m.group(2)
	f.close()

	if 'host' not in settings:
		settings['host'] = '127.0.0.1'
	if 'port' not in settings:
		settings['port'] = 8333
	if 'rpcport' not in settings:
		settings['rpcport'] = 9332
	if 'db' not in settings:
		settings['db'] = '/tmp/chaindb'
	if 'chain' not in settings:
		settings['chain'] = 'mainnet'
	chain = settings['chain']
	if 'log' not in settings or (settings['log'] == '-'):
		settings['log'] = None

	if ('rpcuser' not in settings or
	    'rpcpass' not in settings):
		print("You must set the following in config: rpcuser, rpcpass")
		sys.exit(1)

	settings['port'] = int(settings['port'])
	settings['rpcport'] = int(settings['rpcport'])

	log = Log.Log(settings['log'])

	log.write("\n\n\n\n")

	if chain not in NETWORKS:
		log.write("invalid network")
		sys.exit(1)

	netmagic = NETWORKS[chain]

	mempool = MemPool.MemPool(log)
	chaindb = ChainDb.ChainDb(settings, settings['db'], log, mempool,
				  netmagic, False, False)
	peermgr = PeerManager(log, mempool, chaindb, netmagic)

	if 'loadblock' in settings:
		chaindb.loadfile(settings['loadblock'])

	threads = []

	# start HTTP server for JSON-RPC
	rpcexec = rpc.RPCExec(peermgr, mempool, chaindb, log,
				  settings['rpcuser'], settings['rpcpass'])
	rpcserver = gevent.pywsgi.WSGIServer(('', settings['rpcport']), rpcexec.handle_request)
	t = gevent.Greenlet(rpcserver.serve_forever)
	threads.append(t)

	# connect to specified remote node
	c = peermgr.add(settings['host'], settings['port'])
	threads.append(c)
	
	if 'addnodes' in settings and settings['addnodes']:
                for node in settings['addnodes'].split():
                        c = peermgr.add(node, settings['port'])
                        threads.append(c)
                        time.sleep(2)

	# program main loop
	def start(timeout=None):
		for t in threads: t.start()
		try:
			gevent.joinall(threads,timeout=timeout,
				       raise_error=True)
		finally:
			for t in threads: t.kill()
			gevent.joinall(threads)
			log.write('Flushing database...')
			del chaindb.db
			chaindb.blk_write.close()
			log.write('OK')

	start()


########NEW FILE########
__FILENAME__ = q_avg_size
#!/usr/bin/python
#
# q_avg_size.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#


import sys
import Log
import MemPool
import ChainDb
import cStringIO
import struct

from bitcoin.coredefs import NETWORKS
from bitcoin.core import CBlock
from bitcoin.scripteval import *

NET_SETTINGS = {
	'mainnet' : {
		'log' : '/spare/tmp/q_avg_size.log',
		'db' : '/spare/tmp/chaindb'
	},
	'testnet3' : {
		'log' : '/spare/tmp/q_avg_sizetest.log',
		'db' : '/spare/tmp/chaintest'
	}
}

MY_NETWORK = 'mainnet'

SETTINGS = NET_SETTINGS[MY_NETWORK]

log = Log.Log(SETTINGS['log'])
mempool = MemPool.MemPool(log)
netmagic = NETWORKS[MY_NETWORK]
chaindb = ChainDb.ChainDb(SETTINGS, SETTINGS['db'], log, mempool, netmagic,
			  True)

scanned = 0
failures = 0

n_sizes = 0
size_total = 0

for height in xrange(chaindb.getheight()+1):
	if height < 200000:
		continue

	heightidx = ChainDb.HeightIdx()
	heightstr = str(height)
	try:
		heightidx.deserialize(chaindb.db.Get('height:'+heightstr))
	except KeyError:
		log.write("Height " + str(height) + " not found.")
		continue

	blkhash = heightidx.blocks[0]

	block = chaindb.getblock(blkhash)

	byte_size = 80 + (len(block.vtx) * 32)
	n_sizes += 1
	size_total += byte_size

	scanned += 1
	if (scanned % 1000) == 0:
		log.write("Scanned height %d (%d failures)" % (
			height, failures))

log.write("Scanned %d blocks (%d failures)" % (scanned, failures))

avg_size = 1.0 * size_total / n_sizes

log.write("Average block summary size: %.2f" % (avg_size,))


########NEW FILE########
__FILENAME__ = rpc

#
# rpc.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#

import re
import base64
import json
import cStringIO
import struct
import sys
import itertools

import ChainDb
import bitcoin.coredefs
from bitcoin.serialize import uint256_from_compact

VALID_RPCS = {
	"getblockcount",
	"getblock",
	"getblockhash",
	"getconnectioncount",
	"getinfo",
	"getrawmempool",
	"getrawtransaction",
	"getwork",
	"submitblock",
	"help",
	"stop",
}

class RPCException(Exception):
	def __init__(self, status, message):
		self.status = status
		self.message = message

def uint32(x):
	return x & 0xffffffffL

def bytereverse(x):
	return uint32(( ((x) << 24) | (((x) << 8) & 0x00ff0000) |
			(((x) >> 8) & 0x0000ff00) | ((x) >> 24) ))

def bufreverse(in_buf):
	out_words = []
	for i in range(0, len(in_buf), 4):
		word = struct.unpack('@I', in_buf[i:i+4])[0]
		out_words.append(struct.pack('@I', bytereverse(word)))
	return ''.join(out_words)

def blockToJSON(block, blkmeta, cur_height):
	block.calc_sha256()
	res = {}

	res['hash'] = "%064x" % (block.sha256,)
	res['confirmations'] = cur_height - blkmeta.height + 1
	res['size'] = len(block.serialize())
	res['height'] = blkmeta.height
	res['version'] = block.nVersion
	res['merkleroot'] = "%064x" % (block.hashMerkleRoot,)
	res['time'] = block.nTime
	res['nonce'] = block.nNonce
	res['bits'] = "%x" % (block.nBits,)
	res['previousblockhash'] = "%064x" % (block.hashPrevBlock,)

	txs = []
	for tx in block.vtx:
		tx.calc_sha256()
		txs.append("%064x" % (tx.sha256,))
	
	res['tx'] = txs

	return res

class RPCExec(object):
	def __init__(self, peermgr, mempool, chaindb, log, rpcuser, rpcpass):
		self.peermgr = peermgr
		self.mempool = mempool
		self.chaindb = chaindb
		self.rpcuser = rpcuser
		self.rpcpass = rpcpass
		self.log = log

		self.work_tophash = None
		self.work_blocks = {}

	def help(self, params):
		s = "Available RPC calls:\n"
		s += "getblock <hash> - Return block header and list of transactions\n"
		s += "getblockcount - number of blocks in the longest block chain\n"
		s += "getblockhash <index> - Returns hash of block in best-block-chain at <index>\n"
		s += "getconnectioncount - get P2P peer count\n"
		s += "getinfo - misc. node info\n"
		s += "getrawmempool - list mempool contents\n"
		s += "getrawtransaction <txid> - Get serialized bytes for transaction <txid>\n"
		s += "getwork [data] - get mining work\n"
		s += "submitblock <data>\n"
		s += "help - this message\n"
		s += "stop - stop node\n"
		return (s, None)

	def getblock(self, params):
		err = { "code" : -1, "message" : "invalid params" }
		if (len(params) != 1 or
		    (not isinstance(params[0], str) and
		     not isinstance(params[0], unicode))):
			return (None, err)

		blkhash = long(params[0], 16)
		block = self.chaindb.getblock(blkhash)
		blkmeta = self.chaindb.getblockmeta(blkhash)
		cur_height = self.chaindb.getheight()
		if block is None or blkmeta is None or cur_height < 0:
			err = { "code" : -4, "message" : "block hash not found"}
			return (None, err)

		res = blockToJSON(block, blkmeta, cur_height)

		return (res, None)

	def getblockcount(self, params):
		return (self.chaindb.getheight(), None)

	def getblockhash(self, params):
		err = { "code" : -1, "message" : "invalid params" }
		if (len(params) != 1 or
			not isinstance(params[0], int)):
			return (None, err)

		index = params[0]
		heightstr = str(index)
		if heightstr not in self.chaindb.height:
			err = { "code" : -2, "message" : "invalid height" }
			return (None, err)

		heightidx = ChainDb.HeightIdx()
		heightidx.deserialize(self.chaindb.height[str(index)])

		return ("%064x" % (heightidx.blocks[0],), None)

	def getconnectioncount(self, params):
		return (len(self.peermgr.peers), None)

	def getinfo(self, params):
		d = {}
		d['protocolversion'] = bitcoin.coredefs.PROTO_VERSION
		d['blocks'] = self.chaindb.getheight()
		if self.chaindb.netmagic.block0 == 0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26fL:
			d['testnet'] = False
		else:
			d['testnet'] = True
		return (d, None)

	def getrawmempool(self, params):
		l = []
		for k in self.mempool.pool.iterkeys():
			l.append("%064x" % (k,))
		return (l, None)

	def getrawtransaction(self, params):
		err = { "code" : -1, "message" : "invalid params" }
		if (len(params) != 1 or
			(not isinstance(params[0], str) and
			 not isinstance(params[0], unicode))):
			return (None, err)
		m = re.search('\s*([\dA-Fa-f]+)\s*', params[0])
		if m is None:
			err = { "code" : -1, "message" : "invalid txid param" }
			return (None, err)

		txhash = long(m.group(1), 16)
		tx = self.chaindb.gettx(txhash)
		if tx is None:
			err = { "code" : -3, "message" : "txid not found" }
			return (None, err)

		ser_tx = tx.serialize()
		return (ser_tx.encode('hex'), None)

	def getwork_new(self):
		err = { "code" : -6, "message" : "internal error" }
		tmp_top = self.chaindb.gettophash()
		if self.work_tophash != tmp_top:
			self.work_tophash = tmp_top
			self.work_blocks = {}

		block = self.chaindb.newblock()
		if block is None:
			return (None, err)
		self.work_blocks[block.hashMerkleRoot] = block

		res = {}

		target = uint256_from_compact(block.nBits)
		res['target'] = "%064x" % (target,)

		data = block.serialize()
		data = data[:80]
		data += "\x00" * 48

		data = bufreverse(data)
		res['data'] = data.encode('hex')

		return (res, None)

	def getwork_submit(self, hexstr):
		data = hexstr.decode('hex')
		if len(data) != 128:
			err = { "code" : -5, "message" : "invalid data" }
			return (None, err)

		data = bufreverse(data)
		blkhdr = data[:80]
		f = cStringIO.StringIO(blkhdr)
		block_tmp = CBlock()
		block_tmp.deserialize(f)

		if block_tmp.hashMerkleRoot not in self.work_blocks:
			return (False, None)

		block = self.work_blocks[block_tmp.hashMerkleRoot]
		block.nTime = block_tmp.nTime
		block.nNonce = block_tmp.nNonce

		res = self.chaindb.putblock(block)

		return (res, None)

	def getwork(self, params):
		err = { "code" : -1, "message" : "invalid params" }
		if len(params) == 1:
			if (not isinstance(params[0], str) and
			    not isinstance(params[0], unicode)):
				return (None, err)
			return self.getwork_submit(params[0])
		elif len(params) == 0:
			return self.getwork_new()
		else:
			return (None, err)

	def submitblock(self, params):
		err = { "code" : -1, "message" : "invalid params" }
		if (len(params) != 1 or
		    (not isinstance(params[0], str) and
		     not isinstance(params[0], unicode))):
			return (None, err)

		data = params[0].decode('hex')
		f = cStringIO.StringIO(data)
		block = CBlock()
		block.deserialize(f)

		res = self.chaindb.putblock(block)
		if not res:
			return ("rejected", None)

		return (None, None)

	def stop(self, params):
		self.peermgr.closeall()
		return (True, None)

	def handle_request(self, environ, start_response):
		try:
			# Posts only
			if environ['REQUEST_METHOD'] != 'POST':
				raise RPCException('501', "Unsupported method (%s)" % environ['REQUEST_METHOD'])

			# Only accept default path
			if environ['PATH_INFO'] + environ['SCRIPT_NAME'] != '/':
				raise RPCException('404', "Path not found")

			# RPC authentication
			username = self.check_auth(environ['HTTP_AUTHORIZATION'])
			if username is None:
				raise RPCException('401', 'Forbidden')

			# Dispatch the RPC call
			length = environ['CONTENT_LENGTH']
			body = environ['wsgi.input'].read(length)
			try:
				rpcreq = json.loads(body)
			except ValueError:
				raise RPCException('400', "Unable to decode JSON data")

			if isinstance(rpcreq, dict):
				start_response('200 OK', [('Content-Type', 'application/json')])
				resp = self.handle_rpc(rpcreq)
				respstr = json.dumps(resp) + "\n"
				yield respstr

			elif isinstance(rpcreq, list):
				start_response('200 OK', [('Content-Type', 'application/json')])
				for resp in itertools.imap(self.handle_rpc, repcreq_list):
					respstr = json.dumps(resp) + "\n"
					yield respstr
			else:
				raise RPCException('400', "Not a valid JSON-RPC request")

		except RPCException, e:
			start_response(e.status, [('Content-Type', 'text/plain')], sys.exc_info())
			yield e.message


	def check_auth(self, hdr):
		if hdr is None:
			return None

		m = re.search('\s*(\w+)\s+(\S+)', hdr)
		if m is None or m.group(0) is None:
			return None
		if m.group(1) != 'Basic':
			return None

		unpw = base64.b64decode(m.group(2))
		if unpw is None:
			return None

		m = re.search('^([^:]+):(.*)$', unpw)
		if m is None:
			return None

		un = m.group(1)
		pw = m.group(2)
		if (un != self.rpcuser or
			pw != self.rpcpass):
			return None

		return un


	def handle_rpc(self, rpcreq):
		id = None
		if 'id' in rpcreq:
			id = rpcreq['id']
		if ('method' not in rpcreq or
			(not isinstance(rpcreq['method'], str) and
			 not isinstance(rpcreq['method'], unicode))):
			resp = { "id" : id, "error" :
				  { "code" : -1,
					"message" : "method not specified" } }
			return resp
		if ('params' not in rpcreq or
			not isinstance(rpcreq['params'], list)):
			resp = { "id" : id, "error" :
				  { "code" : -2,
					"message" : "invalid/missing params" } }
			return resp

		(res, err) = self.jsonrpc(rpcreq['method'], rpcreq['params'])

		if err is None:
			resp = { "result" : res, "error" : None, "id" : id }
		else:
			resp = { "error" : err, "id" : id }

		return resp

	def json_response(self, resp):
		pass

	def jsonrpc(self, method, params):
		if method not in VALID_RPCS:
			return (None, { "code" : -32601,
					"message" : "method not found" })
		rpcfunc = getattr(self, method)
		return rpcfunc(params)

	def log_message(self, format, *args):
		self.log.write("HTTP %s - - [%s] %s \"%s\" \"%s\"" %
			(self.address_string(),
			 self.log_date_time_string(),
			 format%args,
			 self.headers.get('referer', ''),
			 self.headers.get('user-agent', '')
			 ))

########NEW FILE########
__FILENAME__ = testscript
#!/usr/bin/python
#
# testscript.py
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#


import sys
import time
import Log
import MemPool
import ChainDb
import cStringIO

from bitcoin.coredefs import NETWORKS
from bitcoin.core import CBlock
from bitcoin.serialize import ser_uint256
from bitcoin.scripteval import VerifySignature

NET_SETTINGS = {
	'mainnet' : {
		'log' : '/spare/tmp/testscript.log',
		'db' : '/spare/tmp/chaindb'
	},
	'testnet3' : {
		'log' : '/spare/tmp/testtestscript.log',
		'db' : '/spare/tmp/chaintest'
	}
}

MY_NETWORK = 'mainnet'

SETTINGS = NET_SETTINGS[MY_NETWORK]

start_height = 0
end_height = -1
if len(sys.argv) > 1:
	start_height = int(sys.argv[1])
if len(sys.argv) > 2:
	end_height = int(sys.argv[2])
if len(sys.argv) > 3:
	SETTINGS['log'] = sys.argv[3]

log = Log.Log(SETTINGS['log'])
mempool = MemPool.MemPool(log)
chaindb = ChainDb.ChainDb(SETTINGS['db'], log, mempool,
			  NETWORKS[MY_NETWORK], True)
chaindb.blk_cache.max = 500

if end_height < 0 or end_height > chaindb.getheight():
	end_height = chaindb.getheight()

scanned = 0
scanned_tx = 0
failures = 0
opcount = {}

SKIP_TX = {
}


def scan_tx(tx):
	tx.calc_sha256()

	if tx.sha256 in SKIP_TX:
		return True

#	log.write("...Scanning TX %064x" % (tx.sha256,))
	for i in xrange(len(tx.vin)):
		txin = tx.vin[i]
		txfrom = chaindb.gettx(txin.prevout.hash)
		if not VerifySignature(txfrom, tx, i, 0):
			log.write("TX %064x/%d failed" % (tx.sha256, i))
			log.write("FROMTX %064x" % (txfrom.sha256,))
			log.write(txfrom.__repr__())
			log.write("TOTX %064x" % (tx.sha256,))
			log.write(tx.__repr__())
			return False
	return True

for height in xrange(end_height):
	if height < start_height:
		continue
	heightidx = ChainDb.HeightIdx()
	heightidx.deserialize(chaindb.height[str(height)])

	blkhash = heightidx.blocks[0]
	ser_hash = ser_uint256(blkhash)

	f = cStringIO.StringIO(chaindb.blocks[ser_hash])
	block = CBlock()
	block.deserialize(f)

	start_time = time.time()

	for tx_tmp in block.vtx:
		if tx_tmp.is_coinbase():
			continue

		scanned_tx += 1

		if not scan_tx(tx_tmp):
			failures += 1
			sys.exit(1)

	end_time = time.time()

	scanned += 1
#	if (scanned % 1000) == 0:
	log.write("Scanned %d tx, height %d (%d failures), %.2f sec" % (
		scanned_tx, height, failures, end_time - start_time))


log.write("Scanned %d tx, %d blocks (%d failures)" % (
	scanned_tx, scanned, failures))

#for k,v in opcount.iteritems():
#	print k, v


########NEW FILE########
