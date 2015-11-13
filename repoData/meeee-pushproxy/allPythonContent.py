__FILENAME__ = bag
#!/usr/bin/env python
import os
import sys
from plistlib import writePlistToString, Data

from OpenSSL import crypto


def der_cert_from_pem_file(cert_file):
    cert_pem = open(cert_file).read()
    cert = crypto.dump_certificate(crypto.FILETYPE_ASN1,
                crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem))
    return cert


def sign_bag(data, cert_file):
    private_key_pem = open(cert_file).read()
    private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key_pem)
    return crypto.sign(private_key, data, 'sha1')


def generate_bag(content, cert_file):
    content_plist = writePlistToString(content)
    bag = {
        'bag': Data(content_plist),
        'certs': [Data(der_cert_from_pem_file(cert_file))],
        'signature': Data(sign_bag(content_plist, cert_file)),
    }
    return writePlistToString(bag)


def generate_apsd_bag(host, cert_file):
    bag_content = {
        'APNSCourierHostcount': 50,
        'APNSCourierHostname': host,
        'APNSCourierStatus': True,
        'ClientConnectionRetryAttempts': 100}
    return generate_bag(bag_content, cert_file)


def serve_apsd_bag(hostname, cert_file):
    from flask import Flask
    app = Flask(__name__)
    app.debug = True

    @app.route("/bag")
    def bag():
        return generate_apsd_bag(hostname, cert_file)
    app.run(host='0.0.0.0', port=80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: %s <push hostname> <certificate> [-s]\n'
                         '  <certificate> must be a file containing a'
                         ' private-key and \n'
                         '                certificate in in PEM-encoding\n'
                         '  -s Serve bag instead of writing it to stdout\n'
                         '     Requires flask\n'
                         % sys.argv[0])
        exit(os.EX_USAGE)
    hostname = sys.argv[1]
    cert_file = sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3] == '-s':
        serve_apsd_bag(hostname, cert_file)
    else:
        sys.stdout.write(generate_apsd_bag(hostname, cert_file))

########NEW FILE########
__FILENAME__ = generate-hosts-file-ios5
#!/usr/bin/env python
import sys

try:
    ip = sys.argv[1]
except:
    ip = None

basic_hosts = [
    'push.apple.com',
    'courier.push.apple.com',
    'init-p01st.push.apple.com',  # bag for OS X 10.8/iOS 6
]

format_hosts = [
    ('%d-courier.push.apple.com', 250),
    ('%d.courier.push.apple.com', 250),
]


print '''
##
# Host Database
#
# localhost is used to configure the loopback interface
# when the system is booting.  Do not change this entry.
##
127.0.0.1       localhost
255.255.255.255 broadcasthost
::1             localhost
fe80::1%lo0     localhost

'''

if ip:
    for host in basic_hosts:
        print "%s %s" % (ip, host)

    for host, count in format_hosts:
        for i in xrange(0, count):
            print "%s %s" % (ip, host % i)

########NEW FILE########
__FILENAME__ = generate-hosts-file
#!/usr/bin/env python
import sys

try:
    ip = sys.argv[1]
except:
    ip = None

basic_hosts = [
    'init-p01st.push.apple.com',  # bag for OS X 10.8/iOS 6
]

localhost_hosts = [
    'push.apple.com',
    'courier.push.apple.com',
]

format_localhost_hosts = [
    ('%d-courier.push.apple.com', 250),
]


print '''
##
# Host Database
#
# localhost is used to configure the loopback interface
# when the system is booting.  Do not change this entry.
##
127.0.0.1       localhost
255.255.255.255 broadcasthost
::1             localhost
fe80::1%lo0     localhost

'''

if ip:
    for host in basic_hosts:
        print "%s %s" % (ip, host)

    for host in localhost_hosts:
        print "%s %s" % ('127.0.0.1', host)

    for host, count in format_localhost_hosts:
        for i in xrange(0, count):
            print "%s %s" % ('127.0.0.1', host % i)

########NEW FILE########
__FILENAME__ = bplist
#################################################################################
# Copyright (C) 2009-2011 Vladimir "Farcaller" Pouzanov <farcaller@gmail.com>   #
#                                                                               #
# Permission is hereby granted, free of charge, to any person obtaining a copy  #
# of this software and associated documentation files (the "Software"), to deal #
# in the Software without restriction, including without limitation the rights  #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell     #
# copies of the Software, and to permit persons to whom the Software is         #
# furnished to do so, subject to the following conditions:                      #
#                                                                               #
# The above copyright notice and this permission notice shall be included in    #
# all copies or substantial portions of the Software.                           #
#                                                                               #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR    #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,      #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE   #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER        #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN     #
# THE SOFTWARE.                                                                 #
#################################################################################

import struct
from datetime import datetime, timedelta

class BPListWriter(object):
    def __init__(self, objects):
        self.bplist = ""
        self.objects = objects
    
    def binary(self):
        '''binary -> string
        
        Generates bplist
        '''
        self.data = 'bplist00'
        
        # TODO: flatten objects and count max length size
        
        # TODO: write objects and save offsets
        
        # TODO: write offsets
        
        # TODO: write metadata
        
        return self.data
    
    def write(self, filename):
        '''
        
        Writes bplist to file
        '''
        if self.bplist != "":
            pass
            # TODO: save self.bplist to file
        else:
            raise Exception('BPlist not yet generated')

class BPlistReader(object):
    def __init__(self, s):
        self.data = s
        self.objects = []
        self.resolved = {}
    
    def __unpackIntStruct(self, sz, s):
        '''__unpackIntStruct(size, string) -> int
        
        Unpacks the integer of given size (1, 2 or 4 bytes) from string
        '''
        if   sz == 1:
            ot = '!B'
        elif sz == 2:
            ot = '!H'
        elif sz == 4:
            ot = '!I'
        elif sz == 8:
            ot = '!Q'
        else:
            raise Exception('int unpack size '+str(sz)+' unsupported')
        return struct.unpack(ot, s)[0]
    
    def __unpackInt(self, offset):
        '''__unpackInt(offset) -> int
        
        Unpacks int field from plist at given offset
        '''
        return self.__unpackIntMeta(offset)[1]

    def __unpackIntMeta(self, offset):
        '''__unpackIntMeta(offset) -> (size, int)
        
        Unpacks int field from plist at given offset and returns its size and value
        '''
        obj_header = struct.unpack('!B', self.data[offset])[0]
        obj_type, obj_info = (obj_header & 0xF0), (obj_header & 0x0F)
        int_sz = 2**obj_info
        return int_sz, self.__unpackIntStruct(int_sz, self.data[offset+1:offset+1+int_sz])

    def __resolveIntSize(self, obj_info, offset):
        '''__resolveIntSize(obj_info, offset) -> (count, offset)
        
        Calculates count of objref* array entries and returns count and offset to first element
        '''
        if obj_info == 0x0F:
            ofs, obj_count = self.__unpackIntMeta(offset+1)
            objref = offset+2+ofs
        else:
            obj_count = obj_info
            objref = offset+1
        return obj_count, objref

    def __unpackFloatStruct(self, sz, s):
        '''__unpackFloatStruct(size, string) -> float
        
        Unpacks the float of given size (4 or 8 bytes) from string
        '''
        if   sz == 4:
            ot = '!f'
        elif sz == 8:
            ot = '!d'
        else:
            raise Exception('float unpack size '+str(sz)+' unsupported')
        return struct.unpack(ot, s)[0]

    def __unpackFloat(self, offset):
        '''__unpackFloat(offset) -> float
        
        Unpacks float field from plist at given offset
        '''
        obj_header = struct.unpack('!B', self.data[offset])[0]
        obj_type, obj_info = (obj_header & 0xF0), (obj_header & 0x0F)
        int_sz = 2**obj_info
        return int_sz, self.__unpackFloatStruct(int_sz, self.data[offset+1:offset+1+int_sz])

    def __unpackDate(self, offset):
        td = int(struct.unpack(">d", self.data[offset+1:offset+9])[0])
        return datetime(year=2001,month=1,day=1) + timedelta(seconds=td)

    def __unpackItem(self, offset):
        '''__unpackItem(offset)
        
        Unpacks and returns an item from plist
        '''
        obj_header = struct.unpack('!B', self.data[offset])[0]
        obj_type, obj_info = (obj_header & 0xF0), (obj_header & 0x0F)
        if   obj_type == 0x00:
            if   obj_info == 0x00: # null   0000 0000
                return None
            elif obj_info == 0x08: # bool   0000 1000           // false
                return False
            elif obj_info == 0x09: # bool   0000 1001           // true
                return True
            elif obj_info == 0x0F: # fill   0000 1111           // fill byte
                raise Exception("0x0F Not Implemented") # this is really pad byte, FIXME
            else:
                raise Exception('unpack item type '+str(obj_header)+' at '+str(offset)+ 'failed')
        elif obj_type == 0x10: #     int    0001 nnnn   ...     // # of bytes is 2^nnnn, big-endian bytes
            return self.__unpackInt(offset)
        elif obj_type == 0x20: #    real    0010 nnnn   ...     // # of bytes is 2^nnnn, big-endian bytes
            return self.__unpackFloat(offset)
        elif obj_type == 0x30: #    date    0011 0011   ...     // 8 byte float follows, big-endian bytes
            return self.__unpackDate(offset)
        elif obj_type == 0x40: #    data    0100 nnnn   [int]   ... // nnnn is number of bytes unless 1111 then int count follows, followed by bytes
            obj_count, objref = self.__resolveIntSize(obj_info, offset)
            return self.data[objref:objref+obj_count] # XXX: we return data as str
        elif obj_type == 0x50: #    string  0101 nnnn   [int]   ... // ASCII string, nnnn is # of chars, else 1111 then int count, then bytes
            obj_count, objref = self.__resolveIntSize(obj_info, offset)
            return self.data[objref:objref+obj_count]
        elif obj_type == 0x60: #    string  0110 nnnn   [int]   ... // Unicode string, nnnn is # of chars, else 1111 then int count, then big-endian 2-byte uint16_t
            obj_count, objref = self.__resolveIntSize(obj_info, offset)
            return self.data[objref:objref+obj_count*2].decode('utf-16be')
        elif obj_type == 0x80: #    uid     1000 nnnn   ...     // nnnn+1 is # of bytes
            # FIXME: Accept as a string for now
            obj_count, objref = self.__resolveIntSize(obj_info, offset)
            return self.data[objref:objref+obj_count]
        elif obj_type == 0xA0: #    array   1010 nnnn   [int]   objref* // nnnn is count, unless '1111', then int count follows
            obj_count, objref = self.__resolveIntSize(obj_info, offset)
            arr = []
            for i in range(obj_count):
                arr.append(self.__unpackIntStruct(self.object_ref_size, self.data[objref+i*self.object_ref_size:objref+i*self.object_ref_size+self.object_ref_size]))
            return arr
        elif obj_type == 0xC0: #   set      1100 nnnn   [int]   objref* // nnnn is count, unless '1111', then int count follows
            # XXX: not serializable via apple implementation
            raise Exception("0xC0 Not Implemented") # FIXME: implement
        elif obj_type == 0xD0: #   dict     1101 nnnn   [int]   keyref* objref* // nnnn is count, unless '1111', then int count follows
            obj_count, objref = self.__resolveIntSize(obj_info, offset)
            keys = []
            for i in range(obj_count):
                keys.append(self.__unpackIntStruct(self.object_ref_size, self.data[objref+i*self.object_ref_size:objref+i*self.object_ref_size+self.object_ref_size]))
            values = []
            objref += obj_count*self.object_ref_size
            for i in range(obj_count):
                values.append(self.__unpackIntStruct(self.object_ref_size, self.data[objref+i*self.object_ref_size:objref+i*self.object_ref_size+self.object_ref_size]))
            dic = {}
            for i in range(obj_count):
                dic[keys[i]] = values[i]
            return dic
        else:
            raise Exception('don\'t know how to unpack obj type '+hex(obj_type)+' at '+str(offset))
    
    def __resolveObject(self, idx):
        try:
            return self.resolved[idx]
        except KeyError:
            obj = self.objects[idx]
            if type(obj) == list:
                newArr = []
                for i in obj:
                    newArr.append(self.__resolveObject(i))
                self.resolved[idx] = newArr
                return newArr
            if type(obj) == dict:
                newDic = {}
                for k,v in obj.iteritems():
                    rk = self.__resolveObject(k)
                    rv = self.__resolveObject(v)
                    newDic[rk] = rv
                self.resolved[idx] = newDic
                return newDic
            else:
                self.resolved[idx] = obj
                return obj
    
    def parse(self):
        # read header
        if self.data[:8] != 'bplist00':
            raise Exception('Bad magic')
        
        # read trailer
        self.offset_size, self.object_ref_size, self.number_of_objects, self.top_object, self.table_offset = struct.unpack('!6xBB4xI4xI4xI', self.data[-32:])
        #print "** plist offset_size:",self.offset_size,"objref_size:",self.object_ref_size,"num_objs:",self.number_of_objects,"top:",self.top_object,"table_ofs:",self.table_offset
        
        # read offset table
        self.offset_table = self.data[self.table_offset:-32]
        self.offsets = []
        ot = self.offset_table
        for i in range(self.number_of_objects):
            offset_entry = ot[:self.offset_size]
            ot = ot[self.offset_size:]
            self.offsets.append(self.__unpackIntStruct(self.offset_size, offset_entry))
        #print "** plist offsets:",self.offsets
        
        # read object table
        self.objects = []
        k = 0
        for i in self.offsets:
            obj = self.__unpackItem(i)
            #print "** plist unpacked",k,type(obj),obj,"at",i
            k += 1
            self.objects.append(obj)
        
        # rebuild object tree
        #for i in range(len(self.objects)):
        #    self.__resolveObject(i)
        
        # return root object
        return self.__resolveObject(self.top_object)
    
    @classmethod
    def plistWithString(cls, s):
        parser = cls(s)
        return parser.parse()

# helpers for testing
def plist(obj):
    from Foundation import NSPropertyListSerialization, NSPropertyListBinaryFormat_v1_0
    b = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(obj,  NSPropertyListBinaryFormat_v1_0, 0, None)
    return str(b.bytes())

def unplist(s):
    from Foundation import NSData, NSPropertyListSerialization
    d = NSData.dataWithBytes_length_(s, len(s))
    return NSPropertyListSerialization.propertyListWithData_options_format_error_(d, 0, None, None)

########NEW FILE########
__FILENAME__ = extractkeychain
#!/usr/bin/python

# This program will dump the secrets out of an Apple keychain. Obviously you
# need to know the keychain's password - the keychain format seems quite
# secure. To avoid having to parse the keychain files too extensively, Apple's
# "security" commandline utility is executed. Unfortunately this means that
# this program really only works on OS X (or you could modify it to accept the
# output of "security dump-keychain" as input).

# Beware that this program makes no attempts to avoid swapping memory or
# clearing memory after use.

# Details for this were gleaned from looking at Apple's Security-177
# package (www.opensource.apple.com), and looking at some raw keychain files,
# with appropriate debugging statements added to a modifed Security.framework

# (c) 2004 Matt Johnston <matt @ ucc asn au>
# This code may be freely used and modified for any purpose.

# How it works:
#
# The parts of the keychain we're interested in are "blobs" (see ssblob.h in
# Apple's code). There are two types - DbBlobs and KeyBlobs.
#
# Each blob starts with the magic hex string FA DE 07 11 - so we search for
# that. There's only one DbBlob (at the end of the file), and that contains the
# file encryption key (amongst other things), encrypted with the master key.
# The master key is derived purely from the user's password, and a salt, also
# found in the DbBlob. PKCS #5 2 pbkdf2 is used for deriving the master key.
#
# Once we have the file encryption key, we can get the keys for each item. Each
# item is identified by a 20-byte label, starting with 'ssgp' (at least for
# normal items). The KeyBlob has the item encryption key encrypted with the
# file encryption key which we extracted earlier. Note that the Key encryption
# key has been further wrapped using the file encryption key, but a different
# IV (magicCmsIV), so we unencrypt it, reverse some bytes (woo magic, see
# perhaps rfc2630), then unencrypt it again, this time using the IV in the
# KeyBlob. (see getitemkey() for the details)
#
# Once we've got the map of labels->keys, we just parse the "security
# dump-keychain -r" output, and replace the raw ciphertext with what we decrypt
# using the item keys.

from sys import argv, exit, stdout, stderr
from string import split

from struct import unpack
from binascii import hexlify, unhexlify
from popen2 import popen4
from os.path import realpath
from getpass import getpass

from pbkdf2 import pbkdf2

from pyDes import triple_des, CBC

# If you want to use pycrypto (which is faster but requires a package to be
# installed and compiled), swap pyDes for pycrypto, here and in the
# kcdecrypt() function

# from Crypto.Cipher import DES3


keys = {}

dbkey = ""
dbblobpos = -1

magic = unhexlify( 'fade0711' )

magicCmsIV = unhexlify( '4adda22c79e82105' )


SALTLEN = 20
KEYLEN = 24
IVLEN = 8
LABELLEN = 20
BLOCKSIZE = 8

def getitemkeys( f ):

	f.seek(0)


	while f.tell() < dbblobpos: # we stop at the dbblob, since that's last

		str = f.read(4)
		if not str or len(str) == 0:
			# eof
			break
		if str == magic:
			getitemkey( f )


# gets a single key
def getitemkey( f ):
	global keys

#   0 0xfade0711 - magic number
#   4 version
#   8 crypto-offset - offset of the interesting data
#  12 total len
#  16 iv (8 bytes)
#  24 CSSM header (large, we don't care)
#  ... stuff here not used for now
# 156 the name of the key (ends null-terminated, there's probably another way
#     to figure the length, we don't care)
#  ...
# ??? 'ssgp................' - 20 byte label, starting with 'ssgp'. Use this
#     to match up the later record - this is at totallen + 8

	pos = f.tell() - 4

	# IV
	f.seek( pos + 16 )
	iv = f.read( IVLEN )

	# total len
	f.seek( pos + 12 )
	str = f.read(4)
	totallen = unpack(">I", str)[0]

	# label
	f.seek( pos + totallen + 8 )
	label = f.read( LABELLEN )

	if label[0:4] == 'SYSK':
		# don't care about system keys
		return

	if label[0:4] != 'ssgp':
		# TODO - we mightn't care about this, but warn during testing
		print "Unknown label %s after %d" % ( hexlify(label), pos)

	# ciphertext offset
	f.seek( pos + 8 )
	str = f.read(4)
	cipheroff = unpack(">I", str)[0]

	cipherlen = totallen - cipheroff
	if cipherlen % BLOCKSIZE != 0:
		raise "Bad ciphertext len after %d" % pos

	# ciphertext
	f.seek( pos + cipheroff )
	ciphertext = f.read( cipherlen )
	import pdb; pdb.set_trace()


	# we're unwrapping it, so there's a magic IV we use.
	plain = kcdecrypt( dbkey, magicCmsIV, ciphertext )

	# now we handle the unwrapping. we need to take the first 32 bytes,
	# and reverse them.
	revplain = ''
	for i in range(32):
		revplain += plain[31-i]

	# now the real key gets found. */
	plain = kcdecrypt( dbkey, iv, revplain )

	itemkey = plain[4:]

	if len(itemkey) != KEYLEN:
		raise Exception("Bad decrypted keylen!")

	keys[label] = itemkey


def getdbkey( f, pw ):
	global dbblobpos, dbkey

# DbBlob format:
#   The offsets from the start of the blob are as follows:
#   0 0xfade0711 - magic number
#   4 version
#   8 crypto-offset - offset of the encryption and signing key
#  12 total len
#  16 signature (16 bytes)
#  32 sequence
#  36 idletimeout
#  40 lockonsleep flag
#  44 salt (20 bytes)
#  64 iv (8 bytes)
#  72 blob signature (20)

	f.seek(-4, 2)

	while 1:
		f.seek(-8, 1) # back 4
		str = f.read(4)

		if not str or len(str) == 0:
			print>>stderr, "Couldn't find db key. Is a keychain file?"
			exit(1)

		if str == magic:
			break

	pos = f.tell() - 4
	dbblobpos = pos

	# ciphertext offset
	f.seek( pos + 8 )
	str = f.read(4)
	cipheroff = unpack(">I", str)[0]

	# salt
	f.seek( pos + 44 )
	salt = f.read( SALTLEN )

	# IV
	f.seek( pos + 64 )
	iv = f.read( IVLEN )

	# ciphertext
	f.seek( pos + cipheroff )
	ciphertext = f.read( 48 )


	# derive the key
	master = pbkdf2( pw, salt, 1000, KEYLEN )

	# decrypt the key
	plain = kcdecrypt( master, iv, ciphertext )

	dbkey = plain[0:KEYLEN]

	return dbkey
	# and now we're done


def kcdecrypt( key, iv, data ):

	if len(data) % BLOCKSIZE != 0:
		raise "Bad decryption data len isn't a blocksize multiple"

	cipher = triple_des( key, CBC, iv )
	# the line below is for pycrypto instead
	#cipher = DES3.new( key, DES3.MODE_CBC, iv )

	plain = cipher.decrypt( data )

	# now check padding
	pad = ord(plain[-1])
	if pad > 8:
		print>>stderr, "Bad padding byte. You probably have a wrong password"
		exit(1)

	for z in plain[-pad:]:
		if ord(z) != pad:
			print>>stderr, "Bad padding. You probably have a wrong password"
			exit(1)

	plain = plain[:-pad]

	return plain

def parseinput( kcfile ):

	# For some reason 'security dump-keychain' fails with non-absolute paths
	# sometimes.
	realfile = realpath( kcfile )
	cmd = 'security dump-keychain -r "%s"' % realfile

	progpipe = popen4( cmd )

	if not progpipe:
		print>>stderr, "Failed to run command '%s'" % cmd

	p = progpipe[0]

	while 1:
		l = p.readline()
		if not l:
			# EOF
			break


		if len(l) < 9:
			stdout.write( l )
			continue

		if l[0:9] == "raw data:":
			continue

		if l[0:2] != '0x':
			stdout.write( l )
			continue

		# it was some encrypted data, we get the hex format
		hexdata = split(l)[0][2:]

		data = unhexlify( hexdata )

		# format is
		# LABEL || IV || CIPHERTEXT
		# LABEL is 20 bytes, 'ssgp....'
		# IV is 8 bytes
		# CIPHERTEXT is a multiple of blocklen

		if len(data) < LABELLEN + IVLEN + BLOCKSIZE:
			stdout.write( "Couldn't decrypt data - malformed?\n" )
			continue

		label = data[0:LABELLEN]
		iv = data[LABELLEN:LABELLEN+IVLEN]
		ciphertext = data[LABELLEN+IVLEN:]

		if len(ciphertext) % BLOCKSIZE != 0:
			stdout.write( "Couldn't decrypt data - bad ciphertext len\n" )
			continue

		if not keys.has_key( label ):
			stdout.write( "Couldn't find matching decryption key\n" )
			continue

		key = keys[ label ]

		plaintext = kcdecrypt( key, iv, ciphertext )

		stdout.write( "decrypted secret:\n%s\n" % plaintext)

	return


def main():

	if len(argv) != 2:
		print>>stderr, "Usage: extractkeychain <keychain file>"
		exit(1)

	kcfile = argv[1]

	try:
		f = open(kcfile, "r")
	except IOError, e:
		print>>stderr, e
		exit(1)

	print "This will dump keychain items _and secrets_ to standard output."

	pw = getpass( "Keychain password: " )

	getdbkey( f, pw )

	getitemkeys( f )
	parseinput( kcfile )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = pbkdf2
#!/usr/bin/python

# A simple implementation of pbkdf2 using stock python modules. See RFC2898
# for details. Basically, it derives a key from a password and salt.

# (c) 2004 Matt Johnston <matt @ ucc asn au>
# This code may be freely used and modified for any purpose.

import sha
import hmac

from binascii import hexlify, unhexlify
from struct import pack

BLOCKLEN = 20

# this is what you want to call.
def pbkdf2( password, salt, itercount, keylen, hashfn = sha ):

	
	# l - number of output blocks to produce
	l = keylen / BLOCKLEN
	if keylen % BLOCKLEN != 0:
		l += 1

	h = hmac.new( password, None, hashfn )

	T = ""
	for i in range(1, l+1):
		T += pbkdf2_F( h, salt, itercount, i )

	return T[: -( BLOCKLEN - keylen%BLOCKLEN) ]

def xorstr( a, b ):
	
	if len(a) != len(b):
		raise "xorstr(): lengths differ"

	ret = ''
	for i in range(len(a)):
		ret += chr(ord(a[i]) ^ ord(b[i]))

	return ret

def prf( h, data ):
	hm = h.copy()
	hm.update( data )
	return hm.digest()

# Helper as per the spec. h is a hmac which has been created seeded with the
# password, it will be copy()ed and not modified.
def pbkdf2_F( h, salt, itercount, blocknum ):

	U = prf( h, salt + pack('>i',blocknum ) )
	T = U

	for i in range(2, itercount+1):
		U = prf( h, U )
		T = xorstr( T, U )

	return T

		
def test():
	# test vector from rfc3211
	password = 'password'
	salt = unhexlify( '1234567878563412' )
	password = 'All n-entities must communicate with other n-entities via n-1 entiteeheehees'
	itercount = 500
	keylen = 16
	ret = pbkdf2( password, salt, itercount, keylen )
	print "key:      %s" % hexlify( ret )
	print "expected: 6A 89 70 BF 68 C9 2C AE A8 4A 8D F2 85 10 85 86"

if __name__ == '__main__':
	test()

########NEW FILE########
__FILENAME__ = pyDes
#############################################################################
# 				Documentation				    #
#############################################################################

# Author:   Todd Whiteman
# Date:     7th May, 2003
# Verion:   1.1
# Homepage: http://home.pacific.net.au/~twhitema/des.html
#
# Modifications to 3des CBC code by Matt Johnston 2004 <matt at ucc asn au>
#
# This algorithm is a pure python implementation of the DES algorithm.
# It is in pure python to avoid portability issues, since most DES 
# implementations are programmed in C (for performance reasons).
#
# Triple DES class is also implemented, utilising the DES base. Triple DES
# is either DES-EDE3 with a 24 byte key, or DES-EDE2 with a 16 byte key.
#
# See the README.txt that should come with this python module for the
# implementation methods used.

"""A pure python implementation of the DES and TRIPLE DES encryption algorithms

pyDes.des(key, [mode], [IV])
pyDes.triple_des(key, [mode], [IV])

key  -> String containing the encryption key. 8 bytes for DES, 16 or 24 bytes
	for Triple DES
mode -> Optional argument for encryption type, can be either
        pyDes.ECB (Electronic Code Book) or pyDes.CBC (Cypher Block Chaining)
IV   -> Optional argument, must be supplied if using CBC mode. Must be 8 bytes


Example:
from pyDes import *

data = "Please encrypt my string"
k = des("DESCRYPT", " ", CBC, "\0\0\0\0\0\0\0\0")
d = k.encrypt(data)
print "Encypted string: " + d
print "Decypted string: " + k.decrypt(d)

See the module source (pyDes.py) for more examples of use.
You can slo run the pyDes.py file without and arguments to see a simple test.

Note: This code was not written for high-end systems needing a fast
      implementation, but rather a handy portable solution with small usage.

"""


# Modes of crypting / cyphering
ECB =	0
CBC =	1


#############################################################################
# 				    DES					    #
#############################################################################
class des:
	"""DES encryption/decrytpion class

	Supports ECB (Electronic Code Book) and CBC (Cypher Block Chaining) modes.

	pyDes.des(key,[mode], [IV])

	key  -> The encryption key string, must be exactly 8 bytes
	mode -> Optional argument for encryption type, can be either pyDes.ECB
		(Electronic Code Book), pyDes.CBC (Cypher Block Chaining)
	IV   -> Optional string argument, must be supplied if using CBC mode.
		Must be 8 bytes in length.
	"""


	# Permutation and translation tables for DES
	__pc1 = [56, 48, 40, 32, 24, 16,  8,
		  0, 57, 49, 41, 33, 25, 17,
		  9,  1, 58, 50, 42, 34, 26,
		 18, 10,  2, 59, 51, 43, 35,
		 62, 54, 46, 38, 30, 22, 14,
		  6, 61, 53, 45, 37, 29, 21,
		 13,  5, 60, 52, 44, 36, 28,
		 20, 12,  4, 27, 19, 11,  3
	]

	# number left rotations of pc1
	__left_rotations = [
		1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1
	]

	# permuted choice key (table 2)
	__pc2 = [
		13, 16, 10, 23,  0,  4,
		 2, 27, 14,  5, 20,  9,
		22, 18, 11,  3, 25,  7,
		15,  6, 26, 19, 12,  1,
		40, 51, 30, 36, 46, 54,
		29, 39, 50, 44, 32, 47,
		43, 48, 38, 55, 33, 52,
		45, 41, 49, 35, 28, 31
	]

	# initial permutation IP
	__ip = [57, 49, 41, 33, 25, 17, 9,  1,
		59, 51, 43, 35, 27, 19, 11, 3,
		61, 53, 45, 37, 29, 21, 13, 5,
		63, 55, 47, 39, 31, 23, 15, 7,
		56, 48, 40, 32, 24, 16, 8,  0,
		58, 50, 42, 34, 26, 18, 10, 2,
		60, 52, 44, 36, 28, 20, 12, 4,
		62, 54, 46, 38, 30, 22, 14, 6
	]

	# Expansion table for turning 32 bit blocks into 48 bits
	__expansion_table = [
		31,  0,  1,  2,  3,  4,
		 3,  4,  5,  6,  7,  8,
		 7,  8,  9, 10, 11, 12,
		11, 12, 13, 14, 15, 16,
		15, 16, 17, 18, 19, 20,
		19, 20, 21, 22, 23, 24,
		23, 24, 25, 26, 27, 28,
		27, 28, 29, 30, 31,  0
	]

	# The (in)famous S-boxes
	__sbox = [
		# S1
		[14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
		 0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
		 4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
		 15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],

		# S2
		[15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
		 3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
		 0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
		 13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],

		# S3
		[10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
		 13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
		 13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
		 1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],

		# S4
		[7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
		 13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
		 10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
		 3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],

		# S5
		[2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
		 14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
		 4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
		 11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],

		# S6
		[12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
		 10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
		 9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
		 4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],

		# S7
		[4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
		 13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
		 1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
		 6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],

		# S8
		[13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
		 1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
		 7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
		 2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
	]


	# 32-bit permutation function P used on the output of the S-boxes
	__p = [
		15, 6, 19, 20, 28, 11,
		27, 16, 0, 14, 22, 25,
		4, 17, 30, 9, 1, 7,
		23,13, 31, 26, 2, 8,
		18, 12, 29, 5, 21, 10,
		3, 24
	]

	# final permutation IP^-1
	__fp = [
		39,  7, 47, 15, 55, 23, 63, 31,
		38,  6, 46, 14, 54, 22, 62, 30,
		37,  5, 45, 13, 53, 21, 61, 29,
		36,  4, 44, 12, 52, 20, 60, 28,
		35,  3, 43, 11, 51, 19, 59, 27,
		34,  2, 42, 10, 50, 18, 58, 26,
		33,  1, 41,  9, 49, 17, 57, 25,
		32,  0, 40,  8, 48, 16, 56, 24
	]

	# Type of crypting being done
	ENCRYPT =	0x00
	DECRYPT =	0x01

	# Initialisation
	def __init__(self, key, mode=ECB, IV=None):
		if len(key) != 8:
			raise ValueError("Invalid DES key size. Key must be exactly 8 bytes long.")
		self.block_size = 8
		self.key_size = 8
		self.__padding = ''

		# Set the passed in variables
		self.setMode(mode)
		if IV:
			self.setIV(IV)

		self.L = []
		self.R = []
		self.Kn = [ [0] * 48 ] * 16	# 16 48-bit keys (K1 - K16)
		self.final = []

		self.setKey(key)


	def getKey(self):
		"""getKey() -> string"""
		return self.__key

	def setKey(self, key):
		"""Will set the crypting key for this object. Must be 8 bytes."""
		self.__key = key
		self.__create_sub_keys()

	def getMode(self):
		"""getMode() -> pyDes.ECB or pyDes.CBC"""
		return self.__mode

	def setMode(self, mode):
		"""Sets the type of crypting mode, pyDes.ECB or pyDes.CBC"""
		self.__mode = mode

	def getIV(self):
		"""getIV() -> string"""
		return self.__iv

	def setIV(self, IV):
		"""Will set the Initial Value, used in conjunction with CBC mode"""
		if not IV or len(IV) != self.block_size:
			raise ValueError("Invalid Initial Value (IV), must be a multiple of " + str(self.block_size) + " bytes")
		self.__iv = IV

	def getPadding(self):
		"""getPadding() -> string of length 1. Padding character."""
		return self.__padding

	def __String_to_BitList(self, data):
		"""Turn the string data, into a list of bits (1, 0)'s"""
		l = len(data) * 8
		result = [0] * l
		pos = 0
		for c in data:
			i = 7
			ch = ord(c)
			while i >= 0:
				if ch & (1 << i) != 0:
					result[pos] = 1
				else:
					result[pos] = 0
				pos += 1
				i -= 1

		return result

	def __BitList_to_String(self, data):
		"""Turn the list of bits -> data, into a string"""
		result = ''
		pos = 0
		c = 0
		while pos < len(data):
			c += data[pos] << (7 - (pos % 8))
			if (pos % 8) == 7:
				result += chr(c)
				c = 0
			pos += 1

		return result

	def __permutate(self, table, block):
		"""Permutate this block with the specified table"""
		return map(lambda x: block[x], table)
			
	# Transform the secret key, so that it is ready for data processing
	# Create the 16 subkeys, K[1] - K[16]
	def __create_sub_keys(self):
		"""Create the 16 subkeys K[1] to K[16] from the given key"""
		key = self.__permutate(des.__pc1, self.__String_to_BitList(self.getKey()))
		i = 0
		# Split into Left and Right sections
		self.L = key[:28]
		self.R = key[28:]
		while i < 16:
			j = 0
			# Perform circular left shifts
			while j < des.__left_rotations[i]:
				self.L.append(self.L[0])
				del self.L[0]

				self.R.append(self.R[0])
				del self.R[0]

				j += 1

			# Create one of the 16 subkeys through pc2 permutation
			self.Kn[i] = self.__permutate(des.__pc2, self.L + self.R)

			i += 1

	# Main part of the encryption algorithm, the number cruncher :)
	def __des_crypt(self, block, crypt_type):
		"""Crypt the block of data through DES bit-manipulation"""
		block = self.__permutate(des.__ip, block)
		self.L = block[:32]
		self.R = block[32:]

		# Encryption starts from Kn[1] through to Kn[16]
		if crypt_type == des.ENCRYPT:
			iteration = 0
			iteration_adjustment = 1
		# Decryption starts from Kn[16] down to Kn[1]
		else:
			iteration = 15
			iteration_adjustment = -1

		i = 0
		while i < 16:
			# Make a copy of R[i-1], this will later become L[i]
			tempR = self.R[:]

			# Permutate R[i - 1] to start creating R[i]
			self.R = self.__permutate(des.__expansion_table, self.R)

			# Exclusive or R[i - 1] with K[i], create B[1] to B[8] whilst here
			self.R = map(lambda x, y: x ^ y, self.R, self.Kn[iteration])
			B = [self.R[:6], self.R[6:12], self.R[12:18], self.R[18:24], self.R[24:30], self.R[30:36], self.R[36:42], self.R[42:]]
			# Optimization: Replaced below commented code with above
			#j = 0
			#B = []
			#while j < len(self.R):
			#	self.R[j] = self.R[j] ^ self.Kn[iteration][j]
			#	j += 1
			#	if j % 6 == 0:
			#		B.append(self.R[j-6:j])

			# Permutate B[1] to B[8] using the S-Boxes
			j = 0
			Bn = [0] * 32
			pos = 0
			while j < 8:
				# Work out the offsets
				m = (B[j][0] << 1) + B[j][5]
				n = (B[j][1] << 3) + (B[j][2] << 2) + (B[j][3] << 1) + B[j][4]

				# Find the permutation value
				v = des.__sbox[j][(m << 4) + n]

				# Turn value into bits, add it to result: Bn
				Bn[pos] = (v & 8) >> 3
				Bn[pos + 1] = (v & 4) >> 2
				Bn[pos + 2] = (v & 2) >> 1
				Bn[pos + 3] = v & 1

				pos += 4
				j += 1

			# Permutate the concatination of B[1] to B[8] (Bn)
			self.R = self.__permutate(des.__p, Bn)

			# Xor with L[i - 1]
			self.R = map(lambda x, y: x ^ y, self.R, self.L)
			# Optimization: This now replaces the below commented code
			#j = 0
			#while j < len(self.R):
			#	self.R[j] = self.R[j] ^ self.L[j]
			#	j += 1

			# L[i] becomes R[i - 1]
			self.L = tempR

			i += 1
			iteration += iteration_adjustment
		
		# Final permutation of R[16]L[16]
		self.final = self.__permutate(des.__fp, self.R + self.L)
		return self.final


	# Data to be encrypted/decrypted
	def crypt(self, data, crypt_type):
		"""Crypt the data in blocks, running it through des_crypt()"""

		# Error check the data
		if not data:
			return ''
		if len(data) % self.block_size != 0:
			if crypt_type == des.DECRYPT: # Decryption must work on 8 byte blocks
				raise ValueError("Invalid data length, data must be a multiple of " + str(self.block_size) + " bytes\n.")
			if not self.getPadding():
				raise ValueError("Invalid data length, data must be a multiple of " + str(self.block_size) + " bytes\n. Try setting the optional padding character")
			else:
				data += (self.block_size - (len(data) % self.block_size)) * self.getPadding()
			# print "Len of data: %f" % (len(data) / self.block_size)

		if self.getMode() == CBC:
			if self.getIV():
				iv = self.__String_to_BitList(self.getIV())
			else:
				raise ValueError("For CBC mode, you must supply the Initial Value (IV) for ciphering")

		# Split the data into blocks, crypting each one seperately
		i = 0
		dict = {}
		result = []
		#cached = 0
		#lines = 0
		while i < len(data):
			# Test code for caching encryption results
			#lines += 1
			#if dict.has_key(data[i:i+8]):
				#print "Cached result for: %s" % data[i:i+8]
			#	cached += 1
			#	result.append(dict[data[i:i+8]])
			#	i += 8
			#	continue
				
			block = self.__String_to_BitList(data[i:i+8])

			# Xor with IV if using CBC mode
			if self.getMode() == CBC:
				if crypt_type == des.ENCRYPT:
					block = map(lambda x, y: x ^ y, block, iv)
					#j = 0
					#while j < len(block):
					#	block[j] = block[j] ^ iv[j]
					#	j += 1

				processed_block = self.__des_crypt(block, crypt_type)

				if crypt_type == des.DECRYPT:
					processed_block = map(lambda x, y: x ^ y, processed_block, iv)
					#j = 0
					#while j < len(processed_block):
					#	processed_block[j] = processed_block[j] ^ iv[j]
					#	j += 1
					iv = block
				else:
					iv = processed_block
			else:
				processed_block = self.__des_crypt(block, crypt_type)


			# Add the resulting crypted block to our list
			#d = self.__BitList_to_String(processed_block)
			#result.append(d)
			result.append(self.__BitList_to_String(processed_block))
			#dict[data[i:i+8]] = d
			i += 8

		# print "Lines: %d, cached: %d" % (lines, cached)

		# Remove the padding from the last block
		if crypt_type == des.DECRYPT and self.getPadding():
			#print "Removing decrypt pad"
			s = result[-1]
			while s[-1] == self.getPadding():
				s = s[:-1]
			result[-1] = s

		# Return the full crypted string
		return ''.join(result)

	def encrypt(self, data, pad=''):
		"""encrypt(data, [pad]) -> string

		data : String to be encrypted
		pad  : Optional argument for encryption padding. Must only be one byte

		The data must be a multiple of 8 bytes and will be encrypted
		with the already specified key. Data does not have to be a
		multiple of 8 bytes if the padding character is supplied, the
		data will then be padded to a multiple of 8 bytes with this
		pad character.
		"""
		self.__padding = pad
		return self.crypt(data, des.ENCRYPT)

	def decrypt(self, data, pad=''):
		"""decrypt(data, [pad]) -> string

		data : String to be encrypted
		pad  : Optional argument for decryption padding. Must only be one byte

		The data must be a multiple of 8 bytes and will be decrypted
		with the already specified key. If the optional padding character
		is supplied, then the un-encypted data will have the padding characters
		removed from the end of the string. This pad removal only occurs on the
		last 8 bytes of the data (last data block).
		"""
		self.__padding = pad
		return self.crypt(data, des.DECRYPT)


#############################################################################
# 				Triple DES				    #
#############################################################################
class triple_des:
	"""Triple DES encryption/decrytpion class

	This algorithm uses the DES-EDE3 (when a 24 byte key is supplied) or
	the DES-EDE2 (when a 16 byte key is supplied) encryption methods.
	Supports ECB (Electronic Code Book) and CBC (Cypher Block Chaining) modes.

	pyDes.des(key, [mode], [IV])

	key  -> The encryption key string, must be either 16 or 24 bytes long
	mode -> Optional argument for encryption type, can be either pyDes.ECB
		(Electronic Code Book), pyDes.CBC (Cypher Block Chaining)
	IV   -> Optional string argument, must be supplied if using CBC mode.
		Must be 8 bytes in length.
	"""
	def __init__(self, key, mode=ECB, IV=None):
		self.block_size = 8
		self.setMode(mode)
		self.__padding = ''
		self.__iv = IV
		self.setKey(key)

	def getKey(self):
		"""getKey() -> string"""
		return self.__key

	def setKey(self, key):
		"""Will set the crypting key for this object. Either 16 or 24 bytes long."""
		self.key_size = 24  # Use DES-EDE3 mode
		if len(key) != self.key_size:
			if len(key) == 16: # Use DES-EDE2 mode
				self.key_size = 16
			else:
				raise ValueError("Invalid triple DES key size. Key must be either 16 or 24 bytes long")
		if self.getMode() == CBC and (not self.getIV() or len(self.getIV()) != self.block_size):
			raise ValueError("Invalid IV, must be 8 bytes in length") ## TODO: Check this
		# modes get handled later, since CBC goes on top of the triple-des
		self.__key1 = des(key[:8])
		self.__key2 = des(key[8:16])
		if self.key_size == 16:
			self.__key3 = self.__key1
		else:
			self.__key3 = des(key[16:])
		self.__key = key

	def getMode(self):
		"""getMode() -> pyDes.ECB or pyDes.CBC"""
		return self.__mode

	def setMode(self, mode):
		"""Sets the type of crypting mode, pyDes.ECB or pyDes.CBC"""
		self.__mode = mode

	def getIV(self):
		"""getIV() -> string"""
		return self.__iv

	def setIV(self, IV):
		"""Will set the Initial Value, used in conjunction with CBC mode"""
		self.__iv = IV

	def xorstr( self, x, y ):
		"""Returns the bitwise xor of the bytes in two strings"""
		if len(x) != len(y):
			raise "string lengths differ %d %d" % (len(x), len(y))

		ret = ''
		for i in range(len(x)):
			ret += chr(ord(x[i]) ^ ord(y[i]))

		return ret

	def encrypt(self, data, pad=''):
		"""encrypt(data, [pad]) -> string

		data : String to be encrypted
		pad  : Optional argument for encryption padding. Must only be one byte

		The data must be a multiple of 8 bytes and will be encrypted
		with the already specified key. Data does not have to be a
		multiple of 8 bytes if the padding character is supplied, the
		data will then be padded to a multiple of 8 bytes with this
		pad character.
		"""
		if self.getMode() == ECB:
			# simple
			data = self.__key1.encrypt(data, pad)
			data = self.__key2.decrypt(data)
			return self.__key3.encrypt(data)

		if self.getMode() == CBC:
			raise "This code hasn't been tested yet"
			if len(data) % self.block_size != 0:
				raise "CBC mode needs datalen to be a multiple of blocksize (ignoring padding for now)"

			# simple
			lastblock = self.getIV()
			retdata = ''
			for i in range( 0, len(data), self.block_size ):
				thisblock = data[ i:i+self.block_size ]
				# the XOR for CBC
				thisblock = self.xorstr( lastblock, thisblock )
				thisblock = self.__key1.encrypt(thisblock)
				thisblock = self.__key2.decrypt(thisblock)
				lastblock = self.__key3.encrypt(thisblock)
				retdata += lastblock
			return retdata

		raise "Not reached"

	def decrypt(self, data, pad=''):
		"""decrypt(data, [pad]) -> string

		data : String to be encrypted
		pad  : Optional argument for decryption padding. Must only be one byte

		The data must be a multiple of 8 bytes and will be decrypted
		with the already specified key. If the optional padding character
		is supplied, then the un-encypted data will have the padding characters
		removed from the end of the string. This pad removal only occurs on the
		last 8 bytes of the data (last data block).
		"""
		if self.getMode() == ECB:
			# simple
			data = self.__key3.decrypt(data)
			data = self.__key2.encrypt(data)
			return self.__key1.decrypt(data, pad)

		if self.getMode() == CBC:
			if len(data) % self.block_size != 0:
				raise "Can only decrypt multiples of blocksize"

			lastblock = self.getIV()
			retdata = ''
			for i in range( 0, len(data), self.block_size ):
				# can I arrange this better? probably...
				cipherchunk = data[ i:i+self.block_size ]
				thisblock = self.__key3.decrypt(cipherchunk)
				thisblock = self.__key2.encrypt(thisblock)
				thisblock = self.__key1.decrypt(thisblock)
				retdata += self.xorstr( lastblock, thisblock )
				lastblock = cipherchunk
			return retdata

		raise "Not reached"

#############################################################################
# 				Examples				    #
#############################################################################
def example_triple_des():
	from time import time

	# Utility module
	from binascii import unhexlify as unhex

	# example shows triple-des encryption using the des class
	print "Example of triple DES encryption in default ECB mode (DES-EDE3)\n"

	print "Triple des using the des class (3 times)"
	t = time()
	k1 = des(unhex("133457799BBCDFF1"))
	k2 = des(unhex("1122334455667788"))
	k3 = des(unhex("77661100DD223311"))
	d = "Triple DES test string, to be encrypted and decrypted..."
	print "Key1:      %s" % k1.getKey()
	print "Key2:      %s" % k2.getKey()
	print "Key3:      %s" % k3.getKey()
	print "Data:      %s" % d

	e1 = k1.encrypt(d)
	e2 = k2.decrypt(e1)
	e3 = k3.encrypt(e2)
	print "Encrypted: " + e3

	d3 = k3.decrypt(e3)
	d2 = k2.encrypt(d3)
	d1 = k1.decrypt(d2)
	print "Decrypted: " + d1
	print "DES time taken: %f (%d crypt operations)" % (time() - t, 6 * (len(d) / 8))
	print ""

	# Example below uses the triple-des class to achieve the same as above
	print "Now using triple des class"
	t = time()
	t1 = triple_des(unhex("133457799BBCDFF1112233445566778877661100DD223311"))
	print "Key:       %s" % t1.getKey()
	print "Data:      %s" % d

	td1 = t1.encrypt(d)
	print "Encrypted: " + td1

	td2 = t1.decrypt(td1)
	print "Decrypted: " + td2

	print "Triple DES time taken: %f (%d crypt operations)" % (time() - t, 6 * (len(d) / 8))

def example_des():
	from time import time

	# example of DES encrypting in CBC mode with the IV of "\0\0\0\0\0\0\0\0"
	print "Example of DES encryption using CBC mode\n"
	t = time()
	k = des("DESCRYPT", CBC, "\0\0\0\0\0\0\0\0")
	data = "DES encryption algorithm"
	print "Key      : " + k.getKey()
	print "Data     : " + data

	d = k.encrypt(data)
	print "Encrypted: " + d

	d = k.decrypt(d)
	print "Decrypted: " + d
	print "DES time taken: %f (6 crypt operations)" % (time() - t)
	print ""

def __test__():
	example_des()
	example_triple_des()


def __fulltest__():
	# This should not produce any unexpected errors or exceptions
	from binascii import unhexlify as unhex
	from binascii import hexlify as dohex

	__test__()
	print ""

	k = des("\0\0\0\0\0\0\0\0", CBC, "\0\0\0\0\0\0\0\0")
	d = k.encrypt("DES encryption algorithm")
	if k.decrypt(d) != "DES encryption algorithm":
		print "Test 1 Error: Unencypted data block does not match start data"
	
	k = des("\0\0\0\0\0\0\0\0", CBC, "\0\0\0\0\0\0\0\0")
	d = k.encrypt("Default string of text", '*')
	if k.decrypt(d, "*") != "Default string of text":
		print "Test 2 Error: Unencypted data block does not match start data"

	k = des("\r\n\tABC\r\n")
	d = k.encrypt("String to Pad", '*')
	if k.decrypt(d) != "String to Pad***":
		print "'%s'" % k.decrypt(d)
		print "Test 3 Error: Unencypted data block does not match start data"

	k = des("\r\n\tABC\r\n")
	d = k.encrypt(unhex("000102030405060708FF8FDCB04080"), unhex("44"))
	if k.decrypt(d, unhex("44")) != unhex("000102030405060708FF8FDCB04080"):
		print "Test 4a Error: Unencypted data block does not match start data"
	if k.decrypt(d) != unhex("000102030405060708FF8FDCB0408044"):
		print "Test 4b Error: Unencypted data block does not match start data"

	k = triple_des("MyDesKey\r\n\tABC\r\n0987*543")
	d = k.encrypt(unhex("000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080"))
	if k.decrypt(d) != unhex("000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080"):
		print "Test 5 Error: Unencypted data block does not match start data"

	k = triple_des("\r\n\tABC\r\n0987*543")
	d = k.encrypt(unhex("000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080"))
	if k.decrypt(d) != unhex("000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080000102030405060708FF8FDCB04080"):
		print "Test 6 Error: Unencypted data block does not match start data"

def __filetest__():
	from time import time

	f = open("pyDes.py", "rb+")
	d = f.read()
	f.close()

	t = time()
	k = des("MyDESKey")

	d = k.encrypt(d, " ")
	f = open("pyDes.py.enc", "wb+")
	f.write(d)
	f.close()
	
	d = k.decrypt(d, " ")
	f = open("pyDes.py.dec", "wb+")
	f.write(d)
	f.close()
	print "DES file test time: %f" % (time() - t)
	
def __profile__():
	import profile
	profile.run('__fulltest__()')
	#profile.run('__filetest__()')

if __name__ == '__main__':
	__test__()
	#__fulltest__()
	#__filetest__()
	#__profile__()

########NEW FILE########
__FILENAME__ = extract_certificate
#!/usr/bin/env python
import platform
import sys
from collections import namedtuple
from os.path import dirname, join, realpath
from subprocess import Popen, PIPE

from bplist.bplist import BPlistReader
from extractkeychain.extractkeychain import getdbkey

from keychain import Keychain
from keys import decrypt_rsa_key, rsa_key_der_to_pem


OSX_SETUP_PATH = realpath(dirname(realpath(__file__)))
sys.path.append(OSX_SETUP_PATH)
CERT_PATH = realpath(join(dirname(realpath(__file__)), '../../certs/device'))


def normalize_version(version):
    return [int(x) for x in version.split(".")]


ApsdConfiguration = namedtuple('ApsdConfiguration', 'preferences keychain')


def get_apsd_configuration():
    version = platform.mac_ver()[0]
    if normalize_version(version) < [10, 8]:
        apsd_name = 'applepushserviced'
    else:
        apsd_name = 'apsd'
    return ApsdConfiguration(
        preferences='/Library/Preferences/com.apple.%s.plist' % apsd_name,
        keychain='/Library/Keychains/%s.keychain' % apsd_name,
    )


def get_apsd_preferences(prefs_file=None):
    if not prefs_file:
        prefs_file = get_apsd_configuration().preferences
    prefs = BPlistReader.plistWithString(open(prefs_file).read())
    return prefs


def calculate_apsd_keychain_password(apsd_prefs):
    storage_id = apsd_prefs['StorageId']

    key = [0xa7, 0x98, 0x51, 0x5A, 0xCD, 0xA6, 0xC5, 0x2E,
           0x8F, 0x51, 0xD8, 0xBA, 0xBC, 0x4B, 0xD1, 0xAA]

    password = ''
    for i in range(0, len(storage_id)):
        v = ord(storage_id[i])
        password += chr(v ^ key[i])

    return password


def extract_certificate(keychain_file):
    """
        Extract certificate from keychain using security utility

        Return certificate in PEM encoding. Behaviour is unknown if the
        keychain contains multiple certificates.
    """
    cmd = ['security', 'export', '-k', keychain_file, '-t', 'certs', '-p']
    process = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception("extract_certificate: command failed: '%s' stdout: %s" %
                        (cmd, stdout))
    return stdout


def main():
    keychain_file = get_apsd_configuration().keychain
    fh = open(keychain_file)
    apsd_prefs = get_apsd_preferences()
    password = calculate_apsd_keychain_password(apsd_prefs)
    master_key = getdbkey(fh, password)
    keychain = Keychain(fh)
    # record type 16 - private keys
    # see CSSM_DL_DB_RECORD_PRIVATE_KEY in cssmtype.h (libsecurity_cssm)
    table = keychain.table_by_record_type(16)
    record = table.find_record_by_attribute('PrintName',
                                            apsd_prefs['CertificateName'])

    key = decrypt_rsa_key(record.data, master_key)
    key_pem = rsa_key_der_to_pem(key)
    certificate_pem = extract_certificate(keychain_file)

    push_cert_file = join(CERT_PATH, apsd_prefs['CertificateName'] + '.pem')

    cert_fh = sys.stdout
    if len(sys.argv) > 1 and sys.argv[1] == '-f':
        cert_fh = open(push_cert_file, 'wb')
        sys.stderr.write('Writing private key and certificate to %s\n' %
                         push_cert_file)

    cert_fh.write(key_pem)
    cert_fh.write(certificate_pem)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = keychain
from collections import defaultdict, namedtuple
from itertools import izip
from pprint import pformat
from struct import unpack, unpack_from


class Keychain(object):
    def __init__(self, fh):
        self.fh = fh
        self.header = self.read_header()
        self.schema = self.read_schema_header(self.header.schema_offset)
        tables = self.read_tables(self.header.schema_offset, self.schema)
        schema_attributes = parse_schema_attribute_table(tables[2])
        for table in tables:
            if table.header.id in schema_attributes:
                table.apply_schema(schema_attributes[table.header.id])
        self.tables = tables

    def table_by_record_type(self, record_type):
        for table in self.tables:
            if table.header.id == record_type:
                return table

    KeychainHeader = namedtuple('KeychainHeader',
                                'magic version auth_offset schema_offset')

    def read_header(self):
        self.fh.seek(0)
        header = Keychain.KeychainHeader(*unpack('!4sIII', self.fh.read(16)))
        if header.magic != 'kych':
            raise ValueError('Wrong magic: ' + header.magic)
        return header

    SchemaHeader = namedtuple('SchemaHeader',
                              'size table_count table_offsets')

    def read_schema_header(self, offset):
        self.fh.seek(offset)
        size, table_count = unpack('!II', self.fh.read(8))
        table_offsets = unpack('!' + 'I' * table_count,
                               self.fh.read(4 * table_count))
        return Keychain.SchemaHeader(size, table_count, table_offsets)

    def read_tables(self, base_offset, schema):
        return [Table(self.fh, base_offset + offset, schema)
                for offset in schema.table_offsets]


class Table(object):
    attributes = None

    def __init__(self, fh, offset, schema):
        self.fh = fh
        self.header = self.read_table_header(offset)
        self.base_offset = offset

    def __len__(self):
        return self.header.record_numbers_count

    def __getitem__(self, key):
        offset = self.base_offset + self.header.record_offsets[key]
        return Record(self.fh, offset, self.attributes)

    def __repr__(self):
        return ('<Table size=%d, id=%d, records_count=%d, '
                    'record_numbers_count=%d>' %
                (self.header.size, self.header.id, self.header.records_count,
                    self.header.record_numbers_count))

    Header = namedtuple('TableHeader',
                        'size id records_count records_offset'
                        ' indexes_offset free_list_head'
                        ' record_numbers_count record_offsets')

    def read_table_header(self, offset):
        self.fh.seek(offset)
        fields = list(unpack('!' + 'I' * 7, self.fh.read(28)))
        record_numbers_count = fields[6]
        record_offsets = unpack('!' + 'I' * record_numbers_count,
                                self.fh.read(4 * record_numbers_count))
        fields.append(record_offsets)
        return Table.Header(*fields)

    def apply_schema(self, attributes):
        self.attributes = attributes

    def find_record_by_attribute(self, key, value):
        for record in self:
            if record.attributes[key] == value:
                return record
        raise KeyError('Record not found with %s = %s', repr(key), repr(value))


class Record(object):
    OFFSET_ATTRIBUTE_OFFSETS = 24

    def __init__(self, fh, offset, attribute_schema):
        self.base_offset = offset
        self.fh = fh
        self.header = self.read_record_header(offset)
        self.attribute_schema = attribute_schema
        self.attributes = {}

        self.read_attributes()

    def __repr__(self):
        return repr(self.header) + pformat(self.attributes)

    Header = namedtuple('RecordHeader',
                        'size number create_version record_version'
                        ' data_size semantic_information')

    def read_record_header(self, offset):
        self.fh.seek(offset)
        fields = unpack('!' + 'I' * 6, self.fh.read(6 * 4))
        return Record.Header(*fields)

    def attributes_and_data(self):
        self.fh.seek(self.base_offset + 24)
        return self.fh.read(self.header.size - 24)

    @property
    def data(self):
        begin = self.base_offset + \
                self.OFFSET_ATTRIBUTE_OFFSETS + \
                len(self.attribute_schema) * 4
        self.fh.seek(begin)

        return self.fh.read(self.header.data_size)

    # def read_record_attributes(self, count):
    #     self.fh.seek(self.base_offset + 24)  # begin of attribute offsets
    #     data = self.fh.read(count * 4)
    #     offsets = unpack_from('!' + 'I' * count, data)
    #     ends = list(offsets)
    #     del ends[0]
    #     ends.append(self.header.size)
    #     attrs = []
    #     for begin, end in zip(offsets, ends):
    #         self.fh.seek(self.base_offset + begin - 1)  # TODO why -1?
    #         attrs.append(self.fh.read(end - begin))
    #     return attrs

    def read_attribute_data(self):
        count = len(self.attribute_schema)
        self.fh.seek(self.base_offset + 24)  # begin of index offsets
        data = self.fh.read(count * 4)
        offsets = unpack_from('!' + 'I' * count, data)
        ends = list(offsets)
        del ends[0]
        ends.append(self.header.size + 1)
        attrs = []
        for begin, end in zip(offsets, ends):
            self.fh.seek(self.base_offset + begin - 1)  # TODO why -1?
            attrs.append(self.fh.read(end - begin))
        return attrs

    def read_attributes(self):
        if not self.attribute_schema:
            return
        data = self.read_attribute_data()
        for info, value in izip(self.attribute_schema, data):
            name = info.name
            self.attributes[name] = self.decode_attribute(info, value)

    def decode_attribute(self, info, value):
        funcs = {
            2: lambda value: unpack('!I', value)[0],
            6: lambda value: unpack_from(
                                '!I%is' % unpack_from('!I', value)[0],
                                value)[1],
        }
        return funcs.get(info.type, lambda x: x)(value)


Attribute2Record = namedtuple('Attribute2Record',
                              'u1 u2 u3 u4 u5 table_id u7 type u9'
                              ' name_length name u10')


def parse_attribute_record(data):
    fields = list(unpack_from('!IIIIIII4sII', data))
    if fields[3] == 61:   # no idea what this means, but in this case there
                          # are additional fields
        name_length = fields[9]
        format = '!%ds%dsI' % (name_length, (4 - (name_length % 4)) % 4)
        name, padding, u10 = unpack_from(format, data[40:])
    else:
        name, u10 = None, None
    fields += [name, u10]
    return Attribute2Record(*fields)

IndexAttributeRecord = namedtuple('Attribute2Record',
                                  'u1 u2 u3 u4 u5 u6 table_id u8 u9'
                                  ' name_length name type')


def parse_schema_attribute_record(data):
    fields = list(unpack_from('!IIIIIII4sII', data))
    if fields[3] == 61:   # no idea what this means, but in this case there
                          # are additional fields
        name_length = fields[9]
        format = '!%ds%dsI' % (name_length, (4 - (name_length % 4)) % 4)
        name, padding, u10 = unpack_from(format, data[40:])
    else:
        name, u10 = None, None
    fields += [name, u10]
    return IndexAttributeRecord(*fields)


def parse_schema_attribute_table(table):
    attributes = [parse_schema_attribute_record(
                        record.attributes_and_data())
                    for record in table]
    table_schemas = defaultdict(list)
    for attribute in attributes:
        table_schemas[attribute.table_id].append(attribute)
    return dict(table_schemas)

########NEW FILE########
__FILENAME__ = keys
from collections import namedtuple
from struct import unpack, unpack_from
from subprocess import Popen, PIPE

from extractkeychain.extractkeychain import kcdecrypt, \
                                            magicCmsIV as magic_cms_iv


# see ssblob.h KeyBlob, 24 bytes encoded
KeyBlobHeader = namedtuple('KeyBlobHeader', 'magic version start_crypto_blob'
                                            ' total_length iv')
# see cssmtype.h CSSM_KEYHEADER, 80 bytes encoded
CssmKeyHeader = namedtuple('CssmKeyHeader', 'header_version csp_id blob_type'
                                            ' format algorithm_id key_class'
                                            ' logical_key_size_in_bits'
                                            ' key_attr key_usage start_date'
                                            ' end_date wrap_algorithm_id'
                                            ' wrap_mode reserved')


 #(4208854801, 256, 1032, '\x00\x00\x06\x98\x9e6\xc6\xe5')
def parse_key_blob(data):
    """Parse a KeyBlob, see ssblob.h"""
    key_blob_header = KeyBlobHeader(*unpack('!IIII8s', data[:24]))
    cssm_values = unpack('!I16sIIIIIII8s8sIIII', data[24:104])
    cssm_values = list(cssm_values)[:14]

    cssm_key_header = CssmKeyHeader(*cssm_values)
    return (key_blob_header, cssm_key_header)


def decrypt_key(data, master_key):
    """
        Decrypt key in a KeyBlob, see wrapKeyCms.cpp (libsecurity_apple_csp)

        Return tuple (description, plain_key)
    """
    key_header, cssm_header = parse_key_blob(data)
    blob_offset = key_header.start_crypto_blob
    temp3 = kcdecrypt(master_key, magic_cms_iv, data[blob_offset:])
    temp2 = temp3[::-1]  # reverse
    temp1 = temp2[8:]
    iv2 = temp2[:8]
    plain = kcdecrypt(master_key, iv2, temp1)
    description_length = unpack_from('!I', plain)[0]
    return (plain[4:4 + description_length], plain[4 + description_length:])


def decrypt_rsa_key(data, master_key):
    """Decrypt an RSA key, return it in DER encoding"""
    description, plain_key = decrypt_key(data, master_key)
    cmd = 'openssl asn1parse -inform DER |grep "HEX DUMP"'
    pipe = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = pipe.communicate(plain_key)
    if pipe.returncode != 0:
        raise Exception("decrypt_rsa_key: command failed: " + cmd)

    return stdout.rsplit(':', 1)[1].strip().decode('hex')


def rsa_key_der_to_pem(der_key):
    cmd = 'openssl rsa -inform DER'.split(' ')
    process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    pem_key, stderr = process.communicate(der_key)
    if process.returncode != 0:
        raise Exception('rsa_key_der_to_pem: command failed: "' + cmd
                         + '" stderr: ' + stderr)
    return pem_key

########NEW FILE########
__FILENAME__ = patch_apsd
#!/usr/bin/env python
import os
import stat
import subprocess
import sys
from struct import pack


def main():
    if len(sys.argv) != 4:
        sys.stderr.write('Usage: %s <apsd binary path> ' % sys.argv[0] +
                         '<root ca path> <codesign identity name>\n\n')
        sys.exit(1)

    apsd_path = sys.argv[1]
    certificate_path = sys.argv[2]
    codesign_identity = sys.argv[3]

    certificate = read_file(certificate_path)
    root_cert_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '../../certs/entrust/entrust-root.der')
    root_certificate = read_file(root_cert_path)

    if len(root_certificate) < len(certificate):
        raise ValueError('Root certificate is shorter than replacement')

    padding = '\x00' * (len(root_certificate) - len(certificate))

    replacements = {
        '\xb9\x60\x04\x00\x00': '\xb9' + pack('<i', len(certificate)),
        root_certificate: certificate + padding
    }

    output_path = apsd_path + '-patched'

    patch(apsd_path, replacements, output_path)

    if not codesign(output_path, codesign_identity):
        raise Exception('Error: codesign failed.')

    make_executable(output_path)
    print 'Success! Patched file written to %s' % output_path


def codesign(path, identity):
    return not subprocess.call(['codesign', '-f', '-s', identity, path],
                               stdout=sys.stdout,
                               stderr=sys.stderr)


def make_executable(path):
    mode = os.stat(path).st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR
    os.chmod(path, mode)


def patch(path, replacements, output_path):
    binary = read_file(path)

    for needle, replacement in replacements.iteritems():
        if binary.count(needle) != 1:
            raise ValueError(
                "Source binary doesn't contain replacement key " +
                " or it occurs multiple times: %s" % repr(needle))

        binary = binary.replace(needle, replacement)

    with open(output_path, 'wb') as output:
        output.write(binary)


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = logger
import sys

from twisted.python import log, logfile, util


class PushLogObserver(log.FileLogObserver):
    """Logger that doesn't output system context"""
    def emit(self, eventDict):
        text = log.textFromEventDict(eventDict)
        if text is None:
            text = '<no text>'

        timeStr = self.formatTime(eventDict['time'])
        fmtDict = {'time': timeStr, 'text': text}
        output = log._safeFormat('%(time)s %(text)s\n', fmtDict)
        util.untilConcludes(self.write, output)
        util.untilConcludes(self.flush)


def stdoutLogger():
    # catch sys.stdout before twisted overwrites it
    return PushLogObserver(sys.stdout).emit


def fileLogger():
    logFile = logfile.LogFile.fromFullPath('data/push.log',
                                           rotateLength=10000000)  # 10 MB
    return PushLogObserver(logFile).emit

########NEW FILE########
__FILENAME__ = dispatch
import traceback

from twisted.python import log

from icl0ud.utils.hexdump import hexdump


class BaseDispatch(object):
    """Message dispatching mix-in"""

    @property
    def handlers(self):
        if not hasattr(self, '_handlers'):
            self._handlers = set()
        return self._handlers

    def addHandlers(self, handlers):
        map(self.addHandler, handlers)

    def addHandler(self, handler):
        self.handlers.add(handler)

    def removeHandlers(self, handlers):
        map(self.removeHandler, handlers)

    def removeHandler(self, handler):
        self.handlers.pop(handler)

    def dispatch(self, source, message):
        forwardMessage = True

        for handler in self.handlers:
            try:
                deviceProtocol = self.getDeviceProtocol()
                result = handler.handle(source, message, deviceProtocol)
                if not result in (True, None):
                    log.msg('BaseDispatch: Skipping message forward ' +
                            'due to %s' % handler.__class__.__name__)
                    forwardMessage = False
            except Exception:
                log.err(handler.__class__.__name__ + ': ' + \
                        traceback.format_exc())
                log.err(source)
                log.err(message)
                forwardMessage = False
        return forwardMessage


class BaseHandler(object):
    def handle(self, source, *args, **kwargs):
        raise NotImplementedError()


class LoggingHandler(BaseHandler):
    sourcePrefixMap = {'server': '<-', 'device': '->'}

    def handle(self, source, msg, deviceProtocol):
        direction = self.sourcePrefixMap[source]
        deviceProtocol.log(direction + ' ' + str(msg))


class HexdumpHandler(LoggingHandler):
    def __init__(self, fd, *args, **kwargs):
        self.fd = fd
        super(HexdumpHandler, self).__init__()

    def handle(self, source, msg, *args, **kwargs):
        self.fd.write(self.sourcePrefixMap[source] + '\n')
        hexdump(msg.rawData, write_to_fd=self.fd)
        self.fd.flush()

########NEW FILE########
__FILENAME__ = intercept
import os
import random
import traceback
from uuid import UUID

from OpenSSL import SSL
from twisted.internet import reactor, ssl, protocol
from twisted.python import log

from icl0ud.push.dispatch import BaseDispatch
from icl0ud.push.parser import APSParser


class MessageProxy(protocol.Protocol, BaseDispatch, object):
    peer = None
    peer_type = None  # device or server

    def __init__(self):
        self._parser = APSParser()
        self._source = None
        self._buffer = b''

    def setPeer(self, peer):
        self.peer = peer

    def dataReceived(self, data):
        buff = self._buffer + data

        while self._parser.isMessageComplete(buff):
            message, length = self._parser.parseMessage(buff)
            messageData = buff[:length]
            buff = buff[length:]
            self.handleMessage(message, messageData)

        self._buffer = buff

    def handleMessage(self, message, data):
        forward = self.dispatch(self.peer_type, message)
        if forward:
            self.sendToPeer(data)

    def sendToPeer(self, data):
        self.peer.transport.write(data)

    def connectionLost(self, reason):
        # TODO notify handlers
        # FIXME fix this shutdown
        if self.peer is not None:
            self.peer.transport.loseConnection()
            self.peer = None
        else:
            log.msg("Unable to connect to peer: %s" % (reason,))


class InterceptClient(MessageProxy):
    """Proxy Client, captures iCloud-to-client traffic."""
    peer_type = 'server'

    def connectionMade(self):
        self.peer.connectedToServer(self)

    def getDeviceProtocol(self):
        return self.factory.deviceProtocol


class InterceptClientFactory(protocol.ClientFactory):

    protocol = InterceptClient

    def __init__(self, deviceProtocol):
        self.deviceProtocol = deviceProtocol

    def buildProtocol(self, *args, **kw):
        prot = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        prot.setPeer(self.deviceProtocol)
        prot.addHandlers(self.dispatchHandlers)
        return prot

    def clientConnectionFailed(self, connector, reason):
        self.deviceProtocol.transport.loseConnection()

    def setDispatchHandlers(self, handlers):
        self.dispatchHandlers = handlers


class InterceptClientContextFactory(ssl.ClientContextFactory):

    def __init__(self, cert, chain):
        self.cert = cert
        self.chain = chain
        self.method = SSL.SSLv23_METHOD

    def _verifyCallback(self, conn, cert, errno, depth, preverifyOk):
        # FIXME we should check the server common name
        if not preverifyOk:
            log.err("Certificate validation failed.")
        return preverifyOk

    def getContext(self):
        ctx = ssl.ClientContextFactory.getContext(self)
        ctx.load_verify_locations(self.chain)
        ctx.use_certificate_file(self.cert)
        ctx.use_privatekey_file(self.cert)
        ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
            self._verifyCallback)
        return ctx


class InterceptServer(MessageProxy):
    """Proxy Server, captures client-to-iCloud traffic."""

    clientProtocolFactory = InterceptClientFactory
    peer_type = 'device'

    def __init__(self, *args, **kwargs):
        super(InterceptServer, self).__init__(*args, **kwargs)
        self.clientContextFactory = None
        self.deviceCommonName = None
        self._peerSendBuffer = b''

    def SSLInfoCallback(self, conn, where, ret):
        # TODO check why this callback is called two times with HANDSHAKE_DONE
        # - do not attempt to connect to server twice
        # SSL.SSL_CB_HANDSHAKE_DONE(0x20) is missing in old pyOpenSSL releases
        if where & 0x20:
            try:   # Catch exceptions since this function does not throw them
                try:
                    # Twisted < 11.1
                    cert = self.transport.socket.get_peer_certificate()
                except AttributeError:
                    # Twisted >= 11.1
                    cert = self.transport.getPeerCertificate()
                subject = dict(cert.get_subject().get_components())
                self.deviceCommonName = subject['CN']
                self.log('SSL handshake done: Device: %s' %
                         self.deviceCommonName)
                self.connectToServer()
            except Exception:
                log.err('[#%d] SSLInfoCallback Exception:' %
                        self.transport.sessionno)
                log.err(traceback.format_exc())

    def connectionMade(self):
        try:
            # Twisted < 11.1
            sslContext = self.transport.socket.get_context()
        except AttributeError:
            # Twisted >= 11.1
            # TODO Don't use private attribute _tlsConnection
            sslContext = self.transport._tlsConnection.get_context()
        sslContext.set_info_callback(self.SSLInfoCallback)
        peer = self.transport.getPeer()
        self.log('New connection from %s:%d' % (peer.host, peer.port))

    def connectToServer(self):
        # Don't read anything from the connecting client until we have
        # somewhere to send it to.
        self.transport.pauseProducing()
        clientFactory = self.getClientFactory()
        host = random.choice(self.factory.hosts)
        self.log('Connecting to push server: %s:%d' %
                 (host, self.factory.port))
        reactor.connectSSL(host,
                           self.factory.port,
                           clientFactory,
                           self.getClientContextFactory())

    def connectedToServer(self, peer):
        self.setPeer(peer)
        self.flushSendBuffer()
        self.transport.resumeProducing()

    def getDeviceProtocol(self):
        return self

    def sendToPeer(self, data):
        # This happens if connectToserver is not called fast enough to stop
        # the transport from producing. We send the buffer once the client
        # connection is established.
        if self.peer is None:
            self._peerSendBuffer += data
        else:
            super(InterceptServer, self).sendToPeer(data)

    def flushSendBuffer(self):
        self.sendToPeer(self._peerSendBuffer)
        self._peerSendBuffer = b''

    def getClientFactory(self, ):
        f = self.clientProtocolFactory(deviceProtocol=self)
        f.setDispatchHandlers(self.factory.dispatchHandlers)
        return f

    def getClientContextFactory(self):
        certDir = self.factory.clientCertDir
        # ensure this is a valid UUID, if not this throws an exception
        UUID(self.deviceCommonName)

        cert = os.path.join(certDir, self.deviceCommonName + '.pem')
        if not os.path.isfile(cert):
            raise Exception('Device certificate is missing: %s' % cert)

        if self.clientContextFactory is None:
            self.clientContextFactory = InterceptClientContextFactory(
                cert=cert,
                chain=self.factory.caCertChain,
            )
        return self.clientContextFactory

    def log(self, msg):
        prefix = '[#%d] ' % self.transport.sessionno
        log.msg(prefix + msg)


class InterceptServerFactory(protocol.Factory):

    protocol = InterceptServer
    serverContextFactory = None

    def __init__(self, hosts, port, serverCert, clientCertDir, caCertChain,
        serverChain, dispatchHandlers=[]):
        self.hosts = hosts
        self.port = port
        # Passing through the complete configuration seems quite ugly. Maybe
        # implement a Service?
        # The courier.push.apple.com server certificate
        self.serverCert = serverCert
        # Directory containing device certificates
        self.clientCertDir = clientCertDir
        # The cert chain for verifying Apple's server certificate
        self.caCertChain = caCertChain
        # The cert chain for verifying device certificates
        self.serverChain = serverChain

        self.dispatchHandlers = dispatchHandlers

    def buildProtocol(self, *args):
        p = protocol.Factory.buildProtocol(self, *args)
        p.addHandlers(self.dispatchHandlers)
        return p

    def getServerContextFactory(self):
        if self.serverContextFactory is None:
            self.serverContextFactory = InterceptServerContextFactory(
                self.serverCert,
                self.serverChain
            )
        return self.serverContextFactory


class InterceptServerContextFactory(ssl.DefaultOpenSSLContextFactory):
    def __init__(self, cert, chain):
        self.chain = chain
        self.cert = cert
        ssl.DefaultOpenSSLContextFactory.__init__(self, cert, cert)

    def getContext(self):
        ctx = ssl.DefaultOpenSSLContextFactory.getContext(self)
        ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
            self._verifyCallback)
        ctx.load_verify_locations(self.chain)
        ctx.use_certificate_chain_file(self.cert)
        return ctx

    def _verifyCallback(self, conn, cert, errno, depth, preverifyOk):
        return preverifyOk

########NEW FILE########
__FILENAME__ = messages
import json
import time
from collections import namedtuple
from datetime import datetime, timedelta
from pprint import pformat
from struct import pack, unpack
from StringIO import StringIO

import biplist
from twisted.python import log

from topics import topicForHash


FIELD_INDENTATION = ' ' * 35
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT_MICROSECOND = DATE_FORMAT + '.%f'


FieldT = namedtuple('Field', 'name type')
def Field(name, typ=None):
    return FieldT(name, typ)


def indentLines(string):
    return '\n'.join(map(lambda s: FIELD_INDENTATION + s, string.split('\n')))


class APSMessage(object):
    type = None
    knownValues = {}
    fieldMapping = {}

    def __init__(self, type_=None, source=None, **kwargs):
        if type_ is None and self.type is None:
            raise Exception("APSMessage without type created. " +
                            "Either use subclass or type_ argument.")
        if type_ is not None:
            self.type = type_
        self.fields = []
        self.source = source
        self.rawData = None
        for fieldType, fieldInfo in self.fieldMapping.iteritems():
            value = kwargs.get(fieldInfo.name, None)
            setattr(self, fieldInfo.name, value)
            setattr(self, fieldInfo.name + '_fieldInfo', fieldInfo)

    def __str__(self):
        return self.__repr__()

    def __repr__(self, fields=None):
        # TODO implement version that can be passed to eval
        if not fields:
            if self.fieldMapping:
                fields = self.fieldsAsDict()
            else:
                fields = self.fields

        return '<%s type: %x fields: \n%s>' % \
               (self.__class__.__name__,
                self.type,
                pformat(fields, indent=4))

    def addField(self, type_, content):
        self.fields.append((type_, content))
        if type_ in self.fieldMapping:
            fieldInfo = self.fieldMapping[type_]
            if fieldInfo.type:
                content = self.unmarshalType(fieldInfo.type, content)
                setattr(self, fieldInfo.name + '_marshalled', content)
            setattr(self, fieldInfo.name, content)
        self.checkKnownValues(type_, content)

    def unmarshalType(self, typ, content):
        if typ == 'datetime64':
            integer = unpack('!q', content)[0]
            base = datetime.fromtimestamp(int(integer / 1e9))
            # This reduces accuracy from nanoseconds to microseconds
            microseconds = timedelta(microseconds=(integer % 1e9) / 1000)
            return base + microseconds
        elif typ == 'datetime32':
            return datetime.fromtimestamp(unpack('!l', content)[0])
        elif typ == 'hex':
            return content
        else:
            print 'Warning: {}: Unknown type: {}'.format(
                                                    self.__class__.__name__,
                                                    typ)
            return content

    def parsingFinished(self):
        pass

    def fieldsAsDict(self):
        return dict([(fieldInfo.name, getattr(self, fieldInfo.name))
                     for fieldType, fieldInfo
                     in self.fieldMapping.iteritems()])

    def checkKnownValues(self, type_, value):
        """
        Check whether a field has an unknown value.

        For reverse engineering purposes.
        """
        if not type_ in self.knownValues:
            if type_ in self.fieldMapping:
                return
            log.err('%s: unknown field: %x value: %s' %
                    (self.__class__.__name__,
                     type_,
                     value.encode('hex')))
            return
        if not value in self.knownValues[type_]:
            log.err('%s: unknown value for field: %x value %s' % (
                    self.__class__.__name__,
                    type_,
                    value.encode('hex')))

    def marshal(self):
        marshalledFields = []
        length = 0
        for type_, fieldInfo in self.fieldMapping.iteritems():
            fieldValue = getattr(self, fieldInfo.name)
            if fieldValue is None:  # ignore fields set to None
                continue
            if not fieldInfo.type or fieldInfo.type in ('str', 'hex'):
                content = fieldValue
            elif fieldInfo.type in('datetime32', 'datetime64'):
                if type(fieldValue) == str:
                    content = fieldValue
                elif fieldInfo.type == 'datetime32':
                    content = pack('!I', int(time.mktime(fieldValue.timetuple())))
                elif fieldInfo.type == 'datetime64':
                    content = pack('!Q', int(time.mktime(fieldValue.timetuple()))
                                         * 1e9 + fieldValue.microsecond * 1000)
            fieldLength = len(content)
            marshalledFields.append(chr(type_) +
                                    pack('!H', fieldLength) +
                                    content)
            length += fieldLength + 3

        return chr(self.type) + pack('!I', length) + ''.join(marshalledFields)

    def fieldInfo(self, name):
        return getattr(self, name + '_fieldInfo')

    FIELD_FORMATTERS = {
        'datetime32': lambda v: v.strftime(DATE_FORMAT),
        'datetime64': lambda v: v.strftime(DATE_FORMAT_MICROSECOND),
        'hex': lambda v: v.encode('hex'),
    }

    def formatField(self, name):
        field = self.fieldInfo(name)
        value = getattr(self, name)
        if value is None:
            return '<none>'
        formatter = self.FIELD_FORMATTERS.get(field.type, lambda v: repr(v))
        return formatter(value)


class APSConnectBase(APSMessage):
    """Base class for APSConnect and APSConnectResponse

    Used by pushtoken_handler to filter messages which define push tokens
    for a connection.
    """
    pass


class APSConnect(APSConnectBase):
    type = 0x07
    fieldMapping = {
        1: Field('pushToken', 'hex'),
        2: Field('state', 'hex'),
        5: Field('presenceFlags', 'hex'),
    }
    knownValues = {
        2: ('\x01', '\x02'),
        5: ('\x00\x00\x00\x01', '\x00\x00\x00\x02'),
    }

    def __str__(self):
        s = '{cls} presenceFlags: {presenceFlags} state: {state}'.format(
                cls=self.__class__.__name__,
                presenceFlags=self.formatField('presenceFlags'),
                state=self.formatField('state'))
        if self.pushToken is not None:
            s += '\n' + FIELD_INDENTATION + 'push token: ' + \
                      self.formatField('pushToken')
        return s


class APSConnectResponse(APSConnectBase):
    type = 0x08
    fieldMapping = {
        1: Field('connectedResponse', 'hex'),
        2: Field('serverMetadata'),
        3: Field('pushToken', 'hex'),  # TODO rename to token
        4: Field('messageSize'),
        5: Field('unknown5', 'hex'),
    }
    knownValues = {
        1: ('\x00',  # ok
            '\x02',  # some error, connection closed, immediate reconnect
                     #  - first try client sends push token, second try: no push
                     #    token in client hello - status for invalid push token?
            ),
        4: ('\x10\x00',),
        5: ('\x00\x02',),
    }

    def __str__(self):
        messageSize = str(unpack('!H', self.messageSize)[0]) \
                      if self.messageSize is not None \
                      else '<none>'
        string = '%s %s messageSize: %s unknown5: %s' % (
                    self.__class__.__name__,
                    self.formatField('connectedResponse'),
                    messageSize,
                    self.formatField('unknown5'))
        if self.pushToken is not None:
            string += '\n' + FIELD_INDENTATION + 'push token: ' + \
                      self.formatField('pushToken')
        if self.serverMetadata is not None:
            string += '\nserver metadata: ' + self.formatField('serverMetadata')
        return string


class APSTopics(APSMessage):
    type = 0x09
    fieldMapping = {
        1: Field('pushToken', 'hex'),
        2: Field('enabledTopics'),
        3: Field('disabledTopics'),
    }

    def __init__(self, *args, **kwargs):
        super(APSTopics, self).__init__(*args, **kwargs)
        self.enabledTopics = []
        self.disabledTopics = []

    def addField(self, type_, content):
        if type_ == 2:
            self.enabledTopics.append(content)
        elif type_ == 3:
            self.disabledTopics.append(content)
        else:
            super(APSTopics, self).addField(type_, content)

    def __str__(self):
        return ('%s for token %s\n' % (self.__class__.__name__,
                                       self.formatField('pushToken')) +
                self.formatTopics(self.enabledTopics, 'enabled topics: ') +
                '\n' +
                self.formatTopics(self.disabledTopics, 'disabled topics:'))

    def formatTopics(self, topicHashes, prefix):
        topics = [topicForHash(hash) for hash in topicHashes]
        string = prefix + ', '.join(topics)
        if len(string) <= 80:
            return FIELD_INDENTATION + string
        string = FIELD_INDENTATION + prefix + '\n'
        for topic in topics:
            string += FIELD_INDENTATION + '  ' + topic + '\n'
        return string[:-1]  # remove last \n


class APSNotification(APSMessage):
    type = 0x0a
    fieldMapping = {
        1: Field('recipientPushToken'),
        2: Field('topic'),  # TODO rename to topicHash
        3: Field('payload'),
        4: Field('messageId', 'hex'),
        5: Field('expires', 'datetime32'),  # TODO rename to expiry
        6: Field('timestamp', 'datetime64'),
        7: Field('storageFlags', 'hex'),
          # seems to indicate whether the server has additional messages
          # stored
          # flags:  0x01: fromStorage
          #         0x02: lastMessageFromStorage
        9: Field('unknown9'),  # ignored
    }

    def __init__(self, *args, **kwargs):
        super(APSNotification, self).__init__(*args, **kwargs)
        self.biplist = None

    def parsingFinished(self):
        # decode iMessage biplist payload
        iMessageTopic = 'e4e6d952954168d0a5db02dbaf27cc35fc18d159' \
                         .decode('hex')
        if self.topic == iMessageTopic \
            or self.recipientPushToken == iMessageTopic:

            self.biplist = biplist.readPlist(StringIO(self.payload))

    def __str__(self):
        return ('{name} {topic}\n' +
                '{ind}timestamp: {timestamp:<26} expiry: {expiry}\n' +
                '{ind}messageId: {messageId:<26} storageFlags: {storageFlags}\n' +
                '{ind}unknown9:  {unknown9!r:<26} {payload}').format(
                    name=self.__class__.__name__,
                    topic=topicForHash(self.topic) if self.topic else '<no topic>',
                    timestamp=self.formatField('timestamp'),
                    expiry=self.formatField('expires'),
                    messageId=self.formatField('messageId'),
                    storageFlags=self.formatField('storageFlags'),
                    unknown9=self.unknown9,
                    payload=self.formatPayload(),
                    ind=FIELD_INDENTATION)

    def formatPayload(self):
        if self.biplist:
            return 'payload decoded (biplist)\n' + \
                   indentLines(pformat(self.biplist))
        try:
            payload = 'payload decoded (json)\n' + \
                      indentLines(pformat(json.loads(self.payload)))
        except ValueError:
            payload = '\n' + FIELD_INDENTATION + repr(self.payload)
        return payload


class APSNotificationResponse(APSMessage):
    type = 0x0b
    fieldMapping = {
        4: Field('messageId', 'hex'),
        8: Field('deliveryStatus', 'hex'),
    }
    knownValues = {
        8: ('\x00',  # 'Message acknowledged by server'
            '\x02',  # error like in ConnectResponse?
            '\x03',  # 'Server rejected message as invalid'
           ),
    }

    def __str__(self):
        return '%s message: %s status: %s' % (
                    self.__class__.__name__,
                    self.formatField('messageId'),
                    self.formatField('deliveryStatus'))


class APSKeepAlive(APSMessage):
    type = 0x0c
    fieldMapping = {
        1: Field('carrier'),
        2: Field('softwareVersion'),
        3: Field('softwareBuild'),
        4: Field('hardwareVersion'),
        5: Field('keepAliveInterval'),  # in minutes, as string
    }

    def __str__(self):
        return '%s %smin carrier: %s %s/%s/%s' % (self.__class__.__name__,
                                                  self.keepAliveInterval,
                                                  self.carrier,
                                                  self.hardwareVersion,
                                                  self.softwareVersion,
                                                  self.softwareBuild)


class APSKeepAliveResponse(APSMessage):
    type = 0x0d

    def __str__(self):
        return self.__class__.__name__


class APSNoStorage(APSMessage):
    type = 0x0e
    fieldMapping = {
        1: Field('destination', 'hex'),
    }

    def __str__(self):
        return '%s destination: %s' % (self.__class__.__name__,
                                       self.formatField('destination'))


class APSFlush(APSMessage):
    type = 0x0f
    fieldMapping = {
        1: Field('flushWantPadding'),
        2: Field('padding'),
    }

    def __str__(self):
        return '%s flushWantPadding: %d\npadding(%d byte): %s' % (
                self.__class__.__name__,
                unpack('!H', self.flushWantPadding)[0],
                len(self.padding),
                self.padding.encode('hex'))

########NEW FILE########
__FILENAME__ = notification_sender
import random
from datetime import datetime, timedelta
from struct import pack

from twisted.spread import pb

from icl0ud.push.dispatch import BaseHandler
from icl0ud.push.messages import APSNotification, APSNotificationResponse

# FIXME rename this module


class PushNotificationSender(BaseHandler, pb.Root):
    def __init__(self, tokenHandler):
        self._tokenHandler = tokenHandler
        self._messageIds = {}

    def handle(self, source, message, deviceProtocol):
        if not isinstance(message, APSNotificationResponse):
            return True
        if message.messageId in self._messageIds:
            deviceProtocol.log('PushNotificationSender: Found message with ' +
                               'self-issued response token: %s'
                                % repr(message))
            del self._messageIds[message.messageId]
            return False
        return True

    def sendMessageToDevice(self, pushToken, message):
        deviceProtocol = self._tokenHandler.deviceProtocolForToken(pushToken)
        data = message.marshal()
        deviceProtocol.log('PushNotificationSender: Sending to device: ' +
                           str(message))
        deviceProtocol.transport.write(data)

    def generatemessageId(self):
        token = None
        while token in self._messageIds or token is None:
            token = pack("!L", random.randint(0, 2 ** 32 - 1))
        self._messageIds[token] = True
        return token

    def remote_sendNotification(self, pushToken, topic, payload):
        notification = APSNotification(
            recipientPushToken=pushToken,
            topic=topic,
            payload=payload,
            messageId=self.generatemessageId(),
            expires=datetime.now() + timedelta(days=1),
            timestamp=datetime.now(),
            storageFlags='\x00',
        )
        self.sendMessageToDevice(pushToken, notification)
        return 'notification sent'

########NEW FILE########
__FILENAME__ = parser
import inspect
from struct import unpack
from StringIO import StringIO


from icl0ud.push import messages


# TODO rename parser to a more appropriate description
# TODO merge this with messages? - should be implemented analogue to marshalling
class APSParser(object):
    def __init__(self):
        self._typeCache = None

    def isMessageComplete(self, data):
        # print 'isMessageComplete: data: %s' % data.encode('hex')
        if len(data) < 5:
            return False

        messageLength = self.messageLength(data)
        dataLength = len(data)

        if dataLength >= messageLength:
            return True
        return False

    def messageLength(self, data):
        return unpack('!L', data[1:5])[0] + 5

    def messageClassForType(self, type_):
        if not self._typeCache:
            self._typeCache = dict([(cls.type, cls)
                                    for name, cls in inspect.getmembers(messages)
                                    if inspect.isclass(cls)
                                    and issubclass(cls, messages.APSMessage)
                                    and cls.type])
        return self._typeCache.get(type_, messages.APSMessage)

    # TODO decide whether to move this to APSMessage
    # - messages also must be marshalled
    def parseMessage(self, data):
        length = self.messageLength(data)
        stream = StringIO(data[0:length])
        messageType = ord(stream.read(1))
        stream.read(4)  # skip length

        message = self.messageClassForType(messageType)(messageType)
        while stream.tell() < length:
            message.addField(*self.parseField(stream))
        message.parsingFinished()
        message.rawData = data

        return (message, length)

    def parseField(self, stream):
        type_ = ord(stream.read(1))
        length = unpack('!H', stream.read(2))[0]
        return (type_, stream.read(length))

########NEW FILE########
__FILENAME__ = pushtoken_handler
from icl0ud.push.dispatch import BaseHandler
from icl0ud.push.messages import APSConnectBase


class PushTokenHandler(BaseHandler):
    _debug = False

    def __init__(self):
        self.tokenProtocolMap = {}

    def handle(self, source, message, deviceProtocol):
        if not isinstance(message, APSConnectBase):
            return
        self.updatePushToken(deviceProtocol, message.pushToken)

    def updatePushToken(self, deviceProtocol, pushToken):
        # FIXME check whether all of this works for multiple users on one Mac
        # see applepushserviced log, e.g. sending filter message ...
        # with token ... for user ...
        # - there is one device/root token and another for each user
        # - multiple APSConnect/-Response messages, one for each token
        # - multiple APSTopics messages, one for each token
        # We need to remove old tokens at some point.
        # TODO limit tokens per device?
        if pushToken is None:
            return

        if self._debug and not pushToken in self.tokenProtocolMap:
            msg = 'New push token: %s' % pushToken.encode('hex')
            deviceProtocol.log(self.__class__.__name__ + ': ' + msg)

        self.tokenProtocolMap[pushToken] = deviceProtocol

    def deviceProtocolForToken(self, pushToken):
        return self.tokenProtocolMap[pushToken]

########NEW FILE########
__FILENAME__ = topics
from hashlib import sha1

TOPICS = [
    'com.apple.ess',
    'com.apple.gamed',
    'com.apple.itunesstored',
    'com.apple.itunesu',
    'com.apple.jalisco',
    'com.apple.madrid',  # iMessage
    'com.apple.maspushagent',
    'com.apple.mediastream.subscription.push',
    'com.apple.mobileme.fmf1',  # Find My Friends
    'com.apple.mobileme.fmip',  # Find My iPhone/Mac
    'com.apple.private.ac',
    'com.apple.private.alloy.maps',
    'com.apple.private.ids',
    'com.apple.sagad',
    'com.apple.sharedstreams',
    'com.apple.store.Jolly',
    'com.me.bookmarks',
    'com.me.btmm',  # Back To My Mac
    'com.me.cal',
    'com.me.contacts',
    'com.me.keyvalueservice',
    'com.me.setupservice',
    'com.me.ubiquity',
    'com.me.ubiquity.system',
]

TOPIC_HASHES = dict([(sha1(topic).digest(), topic) for topic in TOPICS])


def topicForHash(hash):
    return TOPIC_HASHES.get(hash, hash.encode('hex'))

########NEW FILE########
__FILENAME__ = sample_messages
from datetime import datetime

NOTIFICATION_MARSHALLED = (
                  '\n\x00\x00\x00V\x01\x00\tfakeToken\x02\x00\x14E' +
                  '\xd4\xa8\xf8\xd8?\xdc{\xa9b3\x01\x8f\xe1\xaaG_\xbc' +
                  '\xcdn\x03\x00\x13{"fake": "payload"}\x04\x00\x04\xde' +
                  '\xad\xbe\xef\x05\x00\x04N\xadd\xa4\x06\x00\x08\x12' +
                  'Q6\xbaz\t>\x00\x07\x00\x01\x00')

NOTIFICATION_DICT = {
    'recipientPushToken': 'fakeToken',
    'topic': '45d4a8f8d83fdc7ba96233018fe1aa475fbccd6e'.decode('hex'),
    'payload': '{"fake": "payload"}',
    'messageId': '\xde\xad\xbe\xef',
    'expires': datetime(2011, 10, 30, 15, 52, 20),
    'timestamp': datetime(2011, 10, 29, 15, 52, 20, 335509),
    'storageFlags': '\x00',
}

########NEW FILE########
__FILENAME__ = test_formatting
from twisted.trial import unittest
from copy import deepcopy

import biplist

from icl0ud.push import messages
from icl0ud.test.sample_messages import NOTIFICATION_DICT


class TestNotificationFormatting(unittest.TestCase):
    def setUp(self):
        self.dict = deepcopy(NOTIFICATION_DICT)

    def test_notification_with_json_payload(self):
        notification = messages.APSNotification(**self.dict)
        formatted = str(notification)
        self.assertEquals(formatted,
                            '''APSNotification com.apple.mediastream.subscription.push
                                   timestamp: 2011-10-29 15:52:20.335509 expiry: 2011-10-30 15:52:20
                                   messageId: deadbeef                   storageFlags: 00
                                   unknown9:  None                       payload decoded (json)
                                   {u'fake': u'payload'}''')

    def test_notification_with_biplist_payload(self):
        imessage_hash = 'e4e6d952954168d0a5db02dbaf27cc35fc18d159'
        self.dict['topic'] = imessage_hash.decode('hex')
        self.dict['payload'] = biplist.writePlistToString({'int': 160})

        notification = messages.APSNotification(**self.dict)
        notification.parsingFinished()
        formatted = str(notification)
        self.assertEquals(formatted,
                            '''APSNotification com.apple.madrid
                                   timestamp: 2011-10-29 15:52:20.335509 expiry: 2011-10-30 15:52:20
                                   messageId: deadbeef                   storageFlags: 00
                                   unknown9:  None                       payload decoded (biplist)
                                   {'int': 160}''')

    def test_notification_with_unknown_payload_and_topic(self):
        self.dict['payload'] = '\x12\x34\x56\x78some payload'
        self.dict['topic'] = '\x12\x34\x56\x78some topic'
        notification = messages.APSNotification(**self.dict)
        formatted = str(notification)
        self.assertEquals(formatted,
                                """APSNotification 12345678736f6d6520746f706963
                                   timestamp: 2011-10-29 15:52:20.335509 expiry: 2011-10-30 15:52:20
                                   messageId: deadbeef                   storageFlags: 00
                                   unknown9:  None                       
                                   '\\x124Vxsome payload'""")

    def test_notification_with_missing_fields(self):
        self.dict['topic'] = None
        self.dict['messageId'] = None
        self.dict['storageFlags'] = None
        self.dict['timestamp'] = None
        self.dict['expires'] = None
        notification = messages.APSNotification(**self.dict)
        notification.parsingFinished()
        formatted = str(notification)
        self.assertEquals(formatted, '''APSNotification <no topic>
                                   timestamp: <none>                     expiry: <none>
                                   messageId: <none>                     storageFlags: <none>
                                   unknown9:  None                       payload decoded (json)
                                   {u'fake': u'payload'}''')


class TestConnectFormatting(unittest.TestCase):
    def test_connect(self):
        connect = messages.APSConnect(pushToken='\x12push token',
                                      state='\x01',
                                      presenceFlags='\x00\x00\x00\x01')
        formatted = str(connect)
        self.assertEquals(formatted,
                            '''APSConnect presenceFlags: 00000001 state: 01
                                   push token: 127075736820746f6b656e''')


class TestConnectResponseFormatting(unittest.TestCase):
    def test_connect_response(self):
        msg = messages.APSConnectResponse(connectedResponse='\x00',
                                          serverMetadata=None,
                                          pushToken='\x12push token',
                                          messageSize='\x10\x00',
                                          unknown5='\x00\x02')
        formatted = str(msg)
        self.assertEquals(formatted,
                            '''APSConnectResponse 00 messageSize: 4096 unknown5: 0002
                                   push token: 127075736820746f6b656e''')




########NEW FILE########
__FILENAME__ = test_marshalling
from twisted.trial import unittest

from icl0ud.push import messages
from icl0ud.push.parser import APSParser
from icl0ud.test.sample_messages import (NOTIFICATION_MARSHALLED,
                                              NOTIFICATION_DICT)


class TestMessages(unittest.TestCase):
    def test_marshal_notification(self):
        notification = messages.APSNotification(**NOTIFICATION_DICT)
        marshalled = notification.marshal()

        self.assertEquals(NOTIFICATION_MARSHALLED, marshalled)

    def test_parse_notification(self):
        parser = APSParser()
        message, rest = parser.parseMessage(NOTIFICATION_MARSHALLED)

        self.assertEquals(message.recipientPushToken,
                          NOTIFICATION_DICT['recipientPushToken'])
        self.assertEquals(message.topic,
                          NOTIFICATION_DICT['topic'])
        self.assertEquals(message.payload,
                          NOTIFICATION_DICT['payload'])
        self.assertEquals(message.messageId,
                          NOTIFICATION_DICT['messageId'])
        self.assertEquals(message.expires,
                          NOTIFICATION_DICT['expires'])
        self.assertEquals(message.timestamp,
                          NOTIFICATION_DICT['timestamp'])
        self.assertEquals(message.storageFlags,
                          NOTIFICATION_DICT['storageFlags'])

########NEW FILE########
__FILENAME__ = hexdump
#! /usr/bin/python
"""hexdump.py - hex dump

Ned Batchelder
http://nedbatchelder.com
"""

# Broadly adapted from: http://www.kitebird.com/mysql-cookbook/

__version__ = "20080424"    # Change history at end of file.

import getopt, sys
from StringIO import StringIO

def ascii(x):
    """Determine how to show a byte in ascii."""
    if 32 <= x <= 126:
        return chr(x)
    elif 160 <= x <= 255:
        return '.'
    else:
        return '.'

def hexdump(f, width=16, verbose=0, start=0, write_to_fd=None):
    if not write_to_fd:
        import sys
        write_to_fd = sys.stdout

    if type(f) is str:
        f = StringIO(f)

    pos = 0

    ascmap = [ ascii(x) for x in range(256) ]
    
    lastbuf = ''
    lastline = ''
    nStarLen = 0

    if width > 4:
        spaceCol = width//2
    else:
        spaceCol = -1

    hexwidth = 3 * width 
    if spaceCol != -1:
        hexwidth += 1                

    if start:
        f.seek(start)
        pos = start
        
    while 1:
        buf = f.read(width)

        length = len(buf)
        if length == 0:
            if nStarLen:
                if nStarLen > 1:
                    write_to_fd.write("* %d" % (nStarLen-1) + "\n")
                write_to_fd.write(lastline + "\n")
            return

        bShowBuf = 1
        
        if not verbose and buf == lastbuf:
            nStarLen += 1
            bShowBuf = 0
        else:
            if nStarLen:
                if nStarLen == 1:
                    write_to_fd.write(lastline + "\n")
                else:
                    write_to_fd.write("* %d" % nStarLen + "\n")
            nStarLen = 0

        # Compose output line           
        hex = ""
        asc = ""
        for i in range(length):
            c = buf[i]
            if i == spaceCol:
                hex = hex + " "
            hex = hex + ("%02x" % ord(c)) + " "
            asc = asc + ascmap[ord(c)]
        line = "%06x: %-*s %s" % (pos, hexwidth, hex, asc)

        if bShowBuf:
            write_to_fd.write(line + "\n")
            
        pos = pos + length
        lastbuf = buf
        lastline = line

def main(args):

    def usage():
        for l in [
            "hexdump: display data in hex",
            "hexdump [opts] [file ...]",
            "opts:",
            " -s offset   start dumping from this offset",
            " -v          show all data (else collapse duplicate lines)",
            " -w width    show data this many bytes at a time (default 16)",
            ]: print l
        sys.exit()
        
    try:
        opts, args = getopt.getopt(args, "vw:s:")
    except getopt.GetoptError:
        # print help information and exit:
        usage()

    options = {}
    
    for o, a in opts:
        if o == '-s':
            start = eval(a)
            if type(start) != type(1) or start < 0:
                usage()
            options['start'] = start
        elif o == '-v':
            options['verbose'] = 1
        elif o == '-w':
            width = eval(a)
            if type(width) != type(1) or not (1 <= width <= 100):
                usage()
            options['width'] = width
        else:
            usage()
        
    # Read stdin if no files were named, otherwise read each named file

    if len(args) == 0:
        hexdump(sys.stdin, **options)
    else:
        for name in args:
            try:
                f = open(name, "rb")
            except IOError:
                print >>sys.stderr, "Couldn't open %s" % name
                continue
            hexdump(f, **options)
            f.close()

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print '\n-- interrupted --'
    except IOError:
        print '\n-- broken pipe --'
        
# Change history:
# 20070722:
#   Use integer division.
#   Better error trapping, thanks Tim Hatch.
# 20080424:
#   Remove magic constant 49 for width of hex values as it only works correctly for default width 16.
#   Fix duplicated last line when repetitions near end of file.
########NEW FILE########
__FILENAME__ = pushserver
import os.path
import sys

from twisted.application import internet, service
from twisted.python import log
from twisted.spread import pb

from icl0ud.push.dispatch import LoggingHandler, HexdumpHandler
from icl0ud.push.notification_sender import PushNotificationSender
from icl0ud.push.pushtoken_handler import PushTokenHandler
from icl0ud.push.intercept import InterceptServerFactory


SERVER_CERT_PATH = os.path.join(os.path.curdir,
                   '../certs/courier.push.apple.com/server.pem')
APPLE_CERT_CHAIN_PATH = os.path.join(os.path.curdir,
                                     '../certs/apple/apple-cert-chain.pem')
CLIENT_CERT_DIR = os.path.join(os.path.curdir, '../certs/device/')
CA_CERT_CHAIN_PATH = os.path.join(os.path.curdir,
                                  '../certs/entrust/entrust-roots.pem')

# log_file = open('data/error.log', 'a')
pushTokenHandler = PushTokenHandler()
pushNotificationSender = PushNotificationSender(pushTokenHandler)
DISPATCH_HANDLERS = [LoggingHandler(),
                     pushTokenHandler,
                     pushNotificationSender,
                     # HexdumpHandler(sys.stdout),
                     ]


APPLE_PUSH_IPS = (
        '17.172.232.218',
        '17.172.232.59',
        '17.172.232.134',
        '17.172.232.135',
        '17.172.232.145',
        '17.172.232.216',
        '17.172.232.142',
        '17.172.232.212')

factory = InterceptServerFactory(
    hosts=APPLE_PUSH_IPS,
    port=5223,
    serverCert=SERVER_CERT_PATH,
    clientCertDir=CLIENT_CERT_DIR,
    caCertChain=CA_CERT_CHAIN_PATH,
    serverChain=APPLE_CERT_CHAIN_PATH,
    dispatchHandlers=DISPATCH_HANDLERS,
)
contextFactory = factory.getServerContextFactory()

application = service.Application('i4d-push')
serviceCollection = service.IServiceCollection(application)
internet.SSLServer(5223, factory, contextFactory) \
                  .setServiceParent(serviceCollection)

internet.TCPServer(1234,
                   pb.PBServerFactory(pushNotificationSender),
                   interface='127.0.0.1') \
                  .setServiceParent(serviceCollection)

########NEW FILE########
__FILENAME__ = find_certs
# Find X.509 certificates in DER-encoding with
# length >= 256 and <= 65535 bytes and beginning with two nested sequences.
#
# Requires pyOpenSSL (tested with 0.13,
#                     might be installed by default on OS X)


from __future__ import print_function
import argparse
import re
import struct
import sys

from OpenSSL import crypto

def main():
    args = parse_args()

    with open(args.file, 'rb') as f:
        contents = f.read()

    find_certs(contents, dump_certs=args.dump)

def parse_args():
    parser = argparse.ArgumentParser(description=
        'Find X.509 certificates in DER-encoding with \n' \
        'length >= 256 and <= 65535 bytes and beginning with ' \
        'two nested sequences.')
    parser.add_argument('file', metavar='FILE', type=str,
                       help='file to look for certificates in')
    parser.add_argument('-d', '--dump',
        action='store_true',
        help='Dump the found certificates in PEM-encoding to stdout')

    return parser.parse_args()


def find_cert_candidate_positions(data):
    # Certificate usually begin with an ASN.1 sequence. A sequence begins with
    # 0x30 followed by a length. Ignoring lengths < 128 bytes.
    #
    # Long form: Two to 127 octets. Bit 8 of first octet has value "1" and
    # bits 7-1 give the number of additional length octets. Second and
    # following octets give the length, base 256, most significant digit first.
    # See http://luca.ntop.org/Teaching/Appunti/asn1.html
    return [m.start() for m in re.finditer("\x30\x82..\x30", data)]

def sequence_length(data, position):
    return struct.unpack_from('!H', data, position+2)[0]

def parse_cert(data, position, length):
    # add 1 for sequence type
    # add 3 for length 0x82 0xXX 0xXX
    cert_data = data[position:position+1+3+length]

    return crypto.load_certificate(crypto.FILETYPE_ASN1, cert_data)

def dump_cert(cert):
    print(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

def find_certs(data, dump_certs=False):
    last_end = 0
    certs = []

    for position in find_cert_candidate_positions(data):
        if position < last_end:
            # nested sequence from previous certificate
            continue
        length = sequence_length(data, position)

        try:
            cert = parse_cert(data, position, length)
        except Exception, e:
            print('- %d Failed to parse cert (length %d): %s' %
                  (position, length, e), file=sys.stderr)
            continue

        print('+ %d Found cert with CN "%s" and serial "%s"' %
              (position, cert.get_subject().commonName, cert.get_serial_number()),
              file=sys.stderr)

        if dump_certs:
            dump_cert(cert)

        certs.append(cert)

        last_end = position + length

    return certs


if __name__ == "__main__":
    main()
########NEW FILE########
