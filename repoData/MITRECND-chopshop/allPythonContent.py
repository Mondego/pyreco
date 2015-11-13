__FILENAME__ = b64
# Base64 utilities

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import base64
import string

def b64decode(s, alpha='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/', padbyte='=', strict=True):
    '''
    Decode the given string with the given alphabet.
    If strict==False, tries modifying the input string in the following order:
    1. add pad byte(s) to end
    2. remove non-alphabet bytes at end
    3. remove 1-4 bytes at end (to make strlen % 4 == 0)
    4. remove non-alphabet bytes at beginning
    '''
    b64_alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    b64_pad = '='
    over = len(s) % 4
    if not strict:
        if over == 1:
            # three-character padding at end is worthless/illegal, so just remove one char
            s = s[:-1]
        else:
            # try padding end
            s += padbyte * (4 - over)
    if alpha != b64_alpha or padbyte != b64_pad:
        # translate, if needed
        translator = string.maketrans(alpha+padbyte,b64_alpha+b64_pad)
        #print "DEBUG: before:", s
        s = s.translate(translator)
        #print "DEBUG: after:", s
    if strict:
        return base64.b64decode(s)
    # not strict mode, so try a few things...
    try:
        return base64.b64decode(s)
    except TypeError:
        pass
    # check for illegal bytes at end and remove them
    i = 1
    c = s[-i]
    while c not in b64_alpha:
        i+=1
        c = s[-i]
    if i > 1:
        # illegal bytes found, remove 'em!
        i -= 1
        s = s[:-i]
        # add padding
        if len(s) % 4 != 0:
            s += b64_pad * (4 - (len(s) % 4))
        try:
            return base64.b64decode(s)
        except TypeError:
            pass
    else:
        # try removing the "over" bytes
        try:
            return base64.b64decode(s[:-4])
        except TypeError:
            pass
    # try removing bad chars from start of string
    i = 0
    c = s[i]
    while c not in b64_alpha:
        i+=1
        c = s[i]
    if i > 1:
        # illegal bytes found, remove 'em!
        s = s[i:]
        # add padding
        if len(s) % 4 != 0:
            s += b64_pad * (4 - (len(s) % 4))
        return base64.b64decode(s)

########NEW FILE########
__FILENAME__ = c2utils
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import struct
import binascii
from datetime import datetime
import time
import string
import math

#### UTILITIES #########################

def parse_addr(tcp):
    if tcp.server.count_new > 0:
        return tcp.addr
    elif tcp.client.count_new > 0:
        ((src, sport), (dst, dport)) = tcp.addr
        return ((dst, dport), (src, sport))

def winsizeize(hsize, lsize):
    return (hsize * (0xFFFFFFFF + 1)) + lsize

def pad_string(str, align=8, char=' '):
    new_str = str
    pad_chars = align - (len(str) % align)

    if pad_chars != 0:
        for x in range(pad_chars):
            new_str += char

    return new_str

def reflect(s):
    res = ''
    for char in s:
        if char in ['.', '/', '\\', '-', ' ', ':', ';']:
            res += char
        elif char in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            res += char
        elif char.isupper():
            res += chr(ord('Z') - ord(char) + ord('A'))
        else:
            res += chr(ord('z') - ord(char) + ord('a'))
    return res


def entropy(data):
    if not data:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(chr(x)))/len(data)
        if p_x > 0:
            entropy += - p_x*math.log(p_x, 2)
    return entropy

def one_byte_xor(data, key):
    return "".join([chr(ord(b) ^ key) for b in data])

def multibyte_xor(data, key):
    output = ""
    key_bytes = len(key) / 2
    for i, char in enumerate(data):
        byte = ord(char)
        key_offset = i % key_bytes * 2
        k = key[key_offset:key_offset + 2]
        #print "k = %s" % k
        key_byte = int(k, 16)
        #print "key_byte = %d, byte = %d" % (key_byte, byte)
        output += chr(byte ^ key_byte)
    return output

def sanitize_filename(inf, default='NONAME'):
    fname = ""
    bad = [ '/', '\\', ':', '~', '*' ]
    for c in inf:
        if c in bad:
            fname += '_'
        else:
            fname += c
    if not fname:
        fname = default
    return fname

def replace_nonascii(line, repl):
    clean_line = ""
    for c in line:
        if c in string.printable:
            clean_line += c
        else:
            clean_line += repl
    return clean_line

def strip_nonascii(line):
    clean_line = ""
    for c in line:
        if c in string.printable:
            clean_line += c
        else:
            continue
    return clean_line

def unpack_from(fmt, buf, offset=0):
    """Unpack binary data, using struct.unpack(...)"""
    slice = buffer(buf, offset, struct.calcsize(fmt))
    return struct.unpack(fmt, slice)

def b2a_printable(s):
    """Given a string of binary data, return a copy of that string
    with each non-printable ASCII character converted to a single
    period.
    """
    result = ""
    for c in map(ord, s):
        if c >= 0x20 and c <= 0x7e:
            result = result + chr(c)
        else:
            result = result + '.'
    return result

def packet_isodate(t):
    return packet_time(t, date=True, isodate=True)

def packet_timedate(t):
    return packet_time(t, date=True)

def packet_gmttimedate(t):
    return packet_time(t, date=True, utc=True)

def packet_gmttime(t):
    return packet_time(t, utc=True)

def packet_time(t, date=False, utc=False, isodate=False):
    """Given a unixtime (seconds since epoch) value, return a
    human-readable string describing that time.  if DATE is
    True, then also include the year, month, day, and timezone.
    If UTC is true, return the time in UTC instead of local
    """
    if utc:
        fmt = "%Y-%m-%d %H:%M:%S +0000"
        ts = time.gmtime(t)
    else:
        fmt = "%Y-%m-%d %H:%M:%S %z"
        ts = time.localtime(t)
    if date:
        if isodate:
            return datetime.fromtimestamp(time.mktime(ts))
        else:
            return time.strftime(fmt, ts).rstrip()
    return "%02d:%02d:%02d" % (ts[3], ts[4], ts[5])

def hexdump(data, tabs=0, spaces=0, show_offset=True):
    """Given a buffer of binary data, return a string with a hexdump
    of that data.  Optionally, indent each line by the given
    number of tabs and spaces.  Also, optionally, do not show the offset.
    """
    result = ''
    for i in range(0, len(data), 16):
        hexstring = ' '.join([binascii.hexlify(a) for a in data[i:i+16]])

        asciistring = b2a_printable(data[i:i+16])
        if show_offset:
                result += "%s%s%07x: %-48s |%-16s|\n" % (tabs * '\t', spaces * ' ', i, hexstring, asciistring)
        else:
            result += "%s%s%-48s |%-16s|\n" % (tabs * '\t', spaces * ' ', hexstring, asciistring)
    return result

########NEW FILE########
__FILENAME__ = chopring
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from collections import deque


class chopring(deque):
    """
    A chopring is a double ended queue.

    Chopring supports pretty printing, the ability to
    get a slice of the queue, and of course all of the functionality
    in collections.deque.

    """

    def __init__(self, size=1024 * 10, iterable=()):
        super(chopring, self).__init__(iterable, size)

    def __str__(self):
        return ''.join(self)

    def __getslice__(self, i, j):
        return ''.join(self)[i:j]

########NEW FILE########
__FILENAME__ = dbtools
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


import pymongo

class mongo_connector(object):
    def __init__(self, host, port, db, c):
        self.connection = pymongo.Connection(host, port)
        self.db = self.connection[db]
        self.collection = self.db[c]

    def insert(self, msg):
        ret = self.collection.insert(msg)
        # Need to remove _id because it is added to
        # msg{} by doing the above insert.
        del msg['_id']
        return ret

########NEW FILE########
__FILENAME__ = jsonutils
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
JSON utilities including encoders, decoders, other parsers or handlers
"""

from types import NoneType 
from json import JSONEncoder


#JSON Encoder that attempts to take the represenational string or string 
#value of an object if it is not one of the default types recognized by 
#JSONEncoder. All default types are directly passed to the parent class
class jsonOrReprEncoder(JSONEncoder):
    def default(self,obj):
        #Check if it's a default type
        if not(
            isinstance(obj, dict)       or 
            isinstance(obj, list)       or 
            isinstance(obj, tuple)      or
            isinstance(obj, str)        or
            isinstance(obj, unicode)    or 
            isinstance(obj, int)        or 
            isinstance(obj, long)       or 
            isinstance(obj, float)      or 
            isinstance(obj, bool)       or
            isinstance(obj, NoneType)
           ) :
            try:
                return obj.__repr__()
            except:
                try:
                    return obj.__str__()
                except:
                    pass

        #If all else fails let the parent class throw an exception
        return JSONEncoder(self, obj) 

#JSON Encoder that attempts to take the string or representational value
#of an object if it not one of the default types recognized by
#JSONEncoder. All direct types are directly passed to parent class
class jsonOrStrEncoder(JSONEncoder):
    def default(self,obj):
        #Check if it's a default type
        if not(
            isinstance(obj, dict)       or 
            isinstance(obj, list)       or 
            isinstance(obj, tuple)      or
            isinstance(obj, str)        or
            isinstance(obj, unicode)    or 
            isinstance(obj, int)        or 
            isinstance(obj, long)       or 
            isinstance(obj, float)      or 
            isinstance(obj, bool)       or
            isinstance(obj, NoneType)
           ) :
            #Technically, this is probably the same as str(obj)
            try:
                return obj.__str__()
            except:
                try:
                    return obj.__repr__()
                except:
                    pass

        #If all else fails let the parent class throw an exception
        return JSONEncoder(self, obj) 


########NEW FILE########
__FILENAME__ = lznt1
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import struct
import sys
from c2utils import unpack_from

class lznt1Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def _dCompressBlock(x):
    size = len(x)
    u = ''
    while len(x):

        p = ord(x[0])
        ##print "BLOCK START ", hex(size - len(x)),hex(p),len(u)

        if p == 0: # These are symbol are tokens
            u += x[1:9]
            x = x[9:]
        else:  # There is a phrase token
            idx = 8
            x = x[1:]
            while idx and len(x):
                ustart = len(u)
                #print u[-250:]
                #print "======================================="
                #print "OFFSET ",hex(size - len(x)),ustart,p
                if not (p & 1):
                    u += x[0]
                    x = x[1:]
                else:
                    pt = unpack_from('H', x)[0]
                    pt = pt & 0xffff
                    #print "PT = %x" % pt
                    i = (len(u)-1)  # Current Pos
                    l_mask = 0xfff
                    p_shift = 12
                    while i >= 0x10:
                        ##print i,l_mask,p_shift
                        l_mask >>= 1
                        p_shift -= 1
                        i >>= 1
                    #print "LMASK %x SHIFT %x" % (l_mask,p_shift)

                    length = (pt & l_mask) + 3
                    bp = (pt  >> p_shift) + 1
                    #print "\n\n\n"
                    #print "BackPtr = %d Len = %d" % (bp,length)

                    if length >= bp:
                        tmp = u[-bp:]
                        while length >= len(tmp):
                            u += tmp
                            length -= len(tmp)
                        u += tmp[:length]
                    else:
                        insert = u[-bp : -bp + length]
                        #print "INSERT <%s>,%d,%d" % (insert,-bp,-bp+length)
                        u = u + insert

                    x = x[2:]
                p >>= 1
                idx -= 1
    return u

def dCompressBuf(blob):
    good = True
    unc = ''
    while good:
        try:
            hdr = blob[0:2]
            blob = blob[2:]

            length = struct.unpack('H', hdr)[0]
            length &= 0xfff
            length += 1
            if length > len(blob):
                raise lznt1Error("invalid block len")
                good = False
            else:
                y = blob[:length]
                blob = blob[length:]
                unc += _dCompressBlock(y)
        except:
            good = False

    return unc

########NEW FILE########
__FILENAME__ = mailutils
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import smtplib
import email.MIMEText
 
def send_alert(addresses, alert, server, msg_from=None):
    """Given a comma-separated string of e-mail addresses,
    an alert string, and an outgoing SMTP server,
    send an e-mail to those addresses stating that the
    backdoor is active. Optionally, provide an
    address stating from whom the e-mail originates.
    """
    if not msg_from:
        msg_from = "alert@organization.domain"

    msg = email.MIMEText.MIMEText("ALERT: %s is active" % alert)
    msg["Subject"] = "Status: Alert"
    msg["From"] = msg_from
    msg["To"] = addresses

    address_list = []
    for a in addresses.split(","):
        address_list.append(a)

    s = smtplib.SMTP(server)
    s.sendmail(msg_from, address_list, msg.as_string())
    s.quit()

########NEW FILE########
__FILENAME__ = sslim
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

# From a module authors perspective the API to SSLim is very minimal:
#  - Instantiate one sslim object for the lifetime of your module.
#  - Set your callback attributes right away. As soon as parsing starts you
#  will not be able to change the callbacks for that parser.
#  - Use the parse_to_client and parse_to_server methods of the sslim object to
#  parse the data. When data has been decrypted (and decompressed if necessary)
#  your callback will be called.
#  - When the session is in teardown delete your parser from the sslim object
#  (this is the done method).
# Quick note on internals:
# While the interface to SSLim is intentionally minimal there is a lot of work
# going on under the hood. The SSLim class is a very small class designed to do
# a couple of things:
#  - Instantiate parsers if the quad-tuple is new.
#  - Store the parsers using the quad-tuple as a key.
#  - Provide a way for parsers to be removed when the session is terminating.
#  - Provide a way for parsers to store the minimal amount of state necessary
#  to support session resuming. This is done with the check_sid and add_sid
#  methods in the sslim class. These are passed in to each parser as functions
#  that can be called as store_ms and check_sid. When a new session id is found
#  the master secret is stored in a dictionary by using the store_ms method.
#  The parser can use check_sid to grab the master secret that has been stored
#  for the old session when a new one is found to be resuming. Each parser
#  stores it's own state internally. This includes the necessary crypto
#  objects, the various descriptions of the cipher suites, the decompression
#  objects, the PRF, everything to do a full parse and decrypt.

import math
import zlib
import struct
import binascii

from M2Crypto import RC4, RSA, EVP

class sslimException(Exception):
    pass

class sslimUnknownCipher(sslimException):
    def __init__(self, msg, val=None):
        self.msg = msg
        self.val = val

    def __str__(self):
        if self.val:
            return "%s: 0x%x" % (self.msg, self.val)
        else:
            return "%s" % self.msg

class sslimUnknownCompression(sslimException):
    def __init__(self, msg, val=None):
        self.msg = msg
        self.val = val

    def __str__(self):
        if self.val:
            return "%s: 0x%x" % (self.msg, self.val)
        else:
            return "%s" % self.msg

class sslimBadValue(sslimException):
    def __init__(self, msg, val=None):
        self.msg = msg
        self.val = val

    def __str__(self):
        if self.val:
            return "%s: %s" % (self.msg, binascii.hexlify(self.val))
        else:
            return "%s" % self.msg

class sslimCryptoError(sslimException):
    def __init__(self):
        pass

    def __str__(self):
        return "Crypto failure"

class sslimCallbackError(sslimException):
    def __init__(self):
        pass

    def __str__(self):
        return "Callback error"

class sslimCallbackStop(sslimException):
    def __init__(self):
        pass

    def __str__(self):
        return "Callback stopped"

class sslim:
    # Constants for callback returns to raise appropriate exceptions
    OK = 1
    STOP = 2
    ERROR = 3

    def __init__(self, keyfile):
        # Only two callbacks for now. Request data and response data, called
        # whenever there is data that has been decrypted.
        self.req_callback = None
        self.res_callback = None
        self.callback_obj = None

        # XXX: Support callback?
        self.keypair = RSA.load_key(keyfile)

        self.CLIENT_TO_SERVER = 1
        self.SERVER_TO_CLIENT = 2

        self.parsers = {}
        self.sids = {}

    def add_sid(self, sid, ms):
        if sid == None or sid == 0:
            return
        self.sids[sid] = ms

    def check_sid(self, sid):
        if sid in self.sids:
            return self.sids[sid]
        else:
            return None

    def parse_to_client(self, data, addr):
        if addr in self.parsers:
            parser = self.parsers[addr]
        else:
            parser = self.parsers[addr] = sslim_parser(self.keypair, self.req_callback, self.res_callback, self.callback_obj, self.add_sid, self.check_sid)
        parser.parse(data, self.SERVER_TO_CLIENT)

    def parse_to_server(self, data, addr):
        if addr in self.parsers:
            parser = self.parsers[addr]
        else:
            parser = self.parsers[addr] = sslim_parser(self.keypair, self.req_callback, self.res_callback, self.callback_obj, self.add_sid, self.check_sid)
        parser.parse(data, self.CLIENT_TO_SERVER)

    def done(self, addr):
        self.callback_obj = None
        if addr in self.parsers:
            del self.parsers[addr]

class sslim_parser(sslim):
    def __init__(self, keypair, req_callback, res_callback, callback_obj, add_sid, check_sid):
        self.keypair = keypair

        # Since this object is tied to a session and sid's can go
        # across sessions when resuming we have to have a way to
        # track them.
        # store_ms is used when a new session ID is found.
        # check_sid returns the master secret or None.
        self.store_ms = add_sid
        self.check_sid = check_sid

        # Callbacks for after decryption and decompression.
        self.req_callback = req_callback
        self.res_callback = res_callback
        self.callback_obj = callback_obj

        # Various sizes for most of the things we parse.
        self.hdr_size = struct.calcsize('>BHH')
        self.hs_hdr_size = struct.calcsize('>B')
        self.hs_type_size = struct.calcsize('>B')
        self.sid_len_size = struct.calcsize('>B')
        self.cipher_suite_size = struct.calcsize('>H')
        self.compression_size = struct.calcsize('>B')
        self.hs_hello_size = struct.calcsize('>HBH')
        self.hs_key_exch_size = struct.calcsize('>HB')
        self.hs_pms_len_size = struct.calcsize('>H')
        self.hs_change_cipher_size = struct.calcsize('>H')

        # The bits needed to keep track of the stream state.
        self.ver = None
        self.c_rnd = None
        self.s_rnd = None
        self.c_sid = None
        self.s_sid = None
        self.ms = None
        self.client_ticket = None
        self.server_ticket = None
        self.c_cryptobj = None
        self.s_cryptobj = None
        self.c_zobj = None
        self.s_zobj = None
        self.c_gone_crypto = False
        self.s_gone_crypto = False
        self.CLIENT_TO_SERVER = 1
        self.SERVER_TO_CLIENT = 2

        # For the times when a record goes cross packet, buffer it up.
        self.buffer = ''

        # Version constants
        self.SSLv3_0 = 0x0300
        self.TLSv1_0 = 0x0301
        self.TLSv1_1 = 0x0302
        self.TLSv1_2 = 0x0303
        self.VERSIONS = [
                          self.SSLv3_0,
                          self.TLSv1_0,
                          self.TLSv1_1,
                          self.TLSv1_2
                        ]

        # Extensions we need to parse
        self.EXT_SESSIONTICKET_TYPE = 0x0023

        # Content type values we need to parse
        self.CHANGE_CIPHER_SPEC = 0x14
        self.ALERT = 0x15
        self.HANDSHAKE = 0x16
        self.APPLICATION_DATA = 0x17
        self.CONTENT_TYPES = [
                               self.CHANGE_CIPHER_SPEC,
                               self.ALERT, self.HANDSHAKE,
                               self.APPLICATION_DATA
                             ]

        # Handshake types (we don't parse all of these (yet?))
        self.HELLO_REQUEST = 0x00
        self.CLIENT_HELLO = 0x01
        self.SERVER_HELLO = 0x02
        self.EXT_SESSIONTICKET = 0x04
        self.CERTIFICATE = 0x0B
        self.SERVER_KEY_EXCHANGE = 0x0C
        self.CERTIFICATE_REQUEST = 0x0D
        self.SERVER_HELLO_DONE = 0x0E
        self.CERTIFICATE_VERIFY = 0x0F
        self.CLIENT_KEY_EXCHANGE = 0x10
        self.FINISHED = 0x14
        self.HANDSHAKE_TYPES = [
                                 self.HELLO_REQUEST,
                                 self.CLIENT_HELLO,
                                 self.EXT_SESSIONTICKET,
                                 self.SERVER_HELLO,
                                 self.CERTIFICATE,
                                 self.SERVER_KEY_EXCHANGE,
                                 self.CERTIFICATE_REQUEST,
                                 self.SERVER_HELLO_DONE,
                                 self.CERTIFICATE_VERIFY,
                                 self.CLIENT_KEY_EXCHANGE,
                                 self.FINISHED
                               ]

        # Supported compression algorithms
        self.DEFLATE_COMPRESSION = 0x01
        self.NULL_COMPRESSION = 0x00
        self.compressions = [
                              self.DEFLATE_COMPRESSION,
                              self.NULL_COMPRESSION
                            ]

        # Supported cipher suites
        self.TLS_RSA_WITH_RC4_128_MD5 = 0x0004
        self.TLS_RSA_WITH_RC4_128_SHA = 0x0005
        self.TLS_RSA_WITH_DES_CBC_SHA = 0x0009
        self.TLS_RSA_WITH_3DES_EDE_CBC_SHA = 0x000A
        self.TLS_RSA_WITH_AES_128_CBC_SHA = 0x002F
        self.TLS_RSA_WITH_AES_256_CBC_SHA = 0x0035
        # key_size, mac_size and block_size are in bytes!
        self.cipher_suites = {
            self.TLS_RSA_WITH_RC4_128_MD5: {
                'key_exch': 'RSA',
                'cipher': 'stream',
                'key_size': 16,
                'mac': 'MD5',
                'mac_size': 16,
                'km_len': 64
            },
            self.TLS_RSA_WITH_RC4_128_SHA: {
                'key_exch': 'RSA',
                'cipher': 'stream',
                'key_size': 16,
                'mac': 'SHA',
                'mac_size': 20,
                'km_len': 72
            },
            self.TLS_RSA_WITH_DES_CBC_SHA: {
                'key_exch': 'RSA',
                'algo': 'des_cbc',
                'cipher': 'block',
                'key_size': 8,
                'mac': 'SHA',
                'mac_size': 20,
                'km_len': 104,
                'block_size': 8
            },
            self.TLS_RSA_WITH_3DES_EDE_CBC_SHA: {
                'key_exch': 'RSA',
                'algo': 'des_ede3_cbc',
                'cipher': 'block',
                'key_size': 24,
                'mac': 'SHA',
                'mac_size': 20,
                'km_len': 104,
                'block_size': 8
            },
            self.TLS_RSA_WITH_AES_128_CBC_SHA: {
                'key_exch': 'RSA',
                'algo': 'aes_128_cbc',
                'cipher': 'block',
                'key_size': 16,
                'mac': 'SHA',
                'mac_size': 20,
                'km_len': 104,
                'block_size': 16
            },
            self.TLS_RSA_WITH_AES_256_CBC_SHA: {
                'key_exch': 'RSA',
                'algo': 'aes_256_cbc',
                'cipher': 'block',
                'key_size': 32,
                'mac': 'SHA',
                'mac_size': 20,
                'km_len': 136,
                'block_size': 16
            }
        }

        # Negotiated cipher suite and compression algorithm
        self.cipher_suite = None
        self.compression = self.NULL_COMPRESSION

    def parse(self, x, direction):
        # Not doing this causes unpack to complain about needing a str
        data = x

        if self.buffer:
            data = self.buffer + data
            self.buffer = ''

        if len(data) < self.hdr_size:
            self.buffer = data
            return

        # Support SSLv2 (http://www.homeport.org/~adam/ssl.html)
        # http://www.mozilla.org/projects/security/pki/nss/ssl/
        # http://www.mozilla.org/projects/security/pki/nss/ssl/draft02.html
        # If the high order bit is set this is an SSLv2 message who'se
        # header is 2 bytes. XXX: Handle 3 byte headers!
        (byte0, byte1) = struct.unpack('>BB', data[:2])
        if byte0 & 0x80:
            data = data[2:]
            # Check for 2 byte SSL v2 header.
            if (((byte0 & 0x7F) << 8) | byte1) == len(data):
                self.__parse_sslv2(data, direction)
            else:
                raise sslimBadValue("Bad SSLv2 length", ((byte0 & 0x7F) << 8) | byte1)
        else:
            # XXX: Determine if it's SSLv2 or TLS1.0?
            self.__parse_tlsv1(data, direction)

    def __parse_sslv2(self, x, direction):
        # Not doing this causes unpack to complain about needing a str
        data = x

        # First byte is the message type.
        # XXX: Only support CLIENT HELLO for now
        mt = struct.unpack('>B', data[:1])[0]
        data = data[1:]
        if mt == self.CLIENT_HELLO:
            # Skip the version (2 bytes), grab the cipher spec length.
            data = data[2:]
            cipher_len = struct.unpack('>H', data[:2])[0]
            data = data[2:]
            # Skip the SID length (XXX: Don't skip this to support resuming)
            data = data[2:]
            self.c_sid = 0 # XXX: Grab the c_sid for real
            # Grab the challenge length.
            challenge_len = struct.unpack('>H', data[:2])[0]
            data = data[2:]
            # Skip the cipher specs, grab the challenge
            data = data[cipher_len:]
            fmt_str = "%is" % challenge_len
            # The docs call this a challenge... :(
            self.c_rnd = struct.unpack(fmt_str, data[:challenge_len])[0]
        else:
            raise sslimBadValue("Bad MT (SSLV2)", mt)

    def __parse_tlsv1(self, x, direction):
        # Not doing this causes unpack to complain about needing a str
        data = x

        while len(data) > self.hdr_size:
            (ct, self.ver, l) = struct.unpack('>BHH', data[:self.hdr_size])
            if (len(data) - self.hdr_size) < l:
                self.buffer = data
                return
            data = data[self.hdr_size:]

            if direction == self.CLIENT_TO_SERVER and self.c_gone_crypto:
                self.__decrypt(data[:l], self.c_cryptobj, self.c_zobj, None)
                self.c_gone_crypto = False
                data = data[l:]
                continue
            elif direction == self.SERVER_TO_CLIENT and self.s_gone_crypto:
                self.__decrypt(data[:l], self.s_cryptobj, self.s_zobj, None)
                self.s_gone_crypto = False
                data = data[l:]
                continue

            self.__parse_record(ct, l, data[:l], direction)
            data = data[l:]

    def __parse_record(self, ct, l, data, direction):
        if ct not in self.CONTENT_TYPES:
            raise sslimBadValue("Bad ct value", ct)

        if self.ver not in self.VERSIONS:
            raise sslimBadValue("Bad ver value", self.ver)

        if ct == self.CHANGE_CIPHER_SPEC:
            # XXX: Change cipher spec messages are encrypted with the current
            # connection state. If a cipher spec is changed from NULL to
            # something this is fine. If it is changed from one cipher suite
            # to another we run the risk of screwing up here.
            # Don't do anything with the change cipher message, but we really
            # should!
            data = data[self.hs_change_cipher_size:]
            if direction == self.CLIENT_TO_SERVER:
                self.c_gone_crypto = True
            elif direction == self.SERVER_TO_CLIENT:
                self.s_gone_crypto = True
        elif ct == self.ALERT:
            self.__alert(data[:l], direction)
        elif ct == self.HANDSHAKE:
            self.__handshake(data[:l])
        elif ct == self.APPLICATION_DATA:
            self.__application_data(data[:l], direction)

    def __handshake(self, data):
        # The first byte is the hand-shake type.
        hst = struct.unpack('>B', data[:self.hs_type_size])[0]
        data = data[self.hs_type_size:]

        if hst not in self.HANDSHAKE_TYPES:
            raise sslimBadValue("Bad hst value", hst)

        # Client Hello (0x01) and Server Hello (0x02) have the 32 bytes
        # of random data in the same spot.
        if hst == self.CLIENT_HELLO:
            data = data[self.hs_hello_size:]
            (self.c_rnd, self.c_sid, sid_len) = self.__parse_rnd_and_sid(data)

            if self.ver != self.SSLv3_0:
                # Go looking for extensions.
                # Specifically for Session Tickets (RFC 5077).
                # Move past the random (32), sid_len (1) and SID (sid_len).
                data = data[32 + 1 + sid_len:]

                # We don't care what cipher suites or what compression method
                # the client supports.
                csl = struct.unpack('>H', data[:self.cipher_suite_size])[0]
                data = data[2 + csl:]
                cmpl = struct.unpack('>B', data[:self.compression_size])[0]
                data = data[1 + cmpl:]
                self.client_ticket = self.__find_extension(data, self.EXT_SESSIONTICKET_TYPE)
        elif hst == self.SERVER_HELLO:
            data = data[self.hs_hello_size:]
            (self.s_rnd, self.s_sid, sid_len) = self.__parse_rnd_and_sid(data)

            # Move past the random (32), sid_len (1) and SID (sid_len).
            data = data[32 + 1 + sid_len:]
            self.cipher_suite = struct.unpack('>H', data[:self.cipher_suite_size])[0]
            data = data[self.cipher_suite_size:]
            if self.cipher_suite not in self.cipher_suites:
                raise sslimUnknownCipher("Unknown cipher suite", self.cipher_suite)
            self.cipher_suite = self.cipher_suites[self.cipher_suite]

            self.compression = struct.unpack('>B', data[:self.compression_size])[0]
            data = data[self.compression_size:]
            if self.compression not in self.compressions:
                raise sslimUnknownCompression("Unknown compression", self.compression)

            # The only compression allowed in the RFCs is deflate. If that
            # ever changes we need to pay attention to the value here.
            if self.compression != self.NULL_COMPRESSION:
                self.c_zobj = zlib.decompressobj()
                self.s_zobj = zlib.decompressobj()

            if self.ver != self.SSLv3_0:
                # Go looking for extensions.
                # Specifically for Session Tickets (RFC 5077).
                self.server_ticket = self.__find_extension(data, self.EXT_SESSIONTICKET_TYPE)

            if (self.s_sid != 0 and self.c_sid == self.s_sid) or (self.client_ticket):
                # Session resuming.
                # First check the sid, then check the ticket.
                self.ms = self.check_sid(self.s_sid)
                if not self.ms:
                    self.ms = self.check_sid(self.client_ticket)
                    if not self.ms:
                        raise sslimBadValue("Bad resume value")

                km = self.__key_material(self.cipher_suite['km_len'], self.s_rnd + self.c_rnd, self.ms)
                keys = self.__split_key_material(km)
                self.cipher_suite['keys'] = keys
                if self.cipher_suite['cipher'] == 'stream':
                    self.c_cryptobj = RC4.RC4(keys['client_enc_key'])
                    self.s_cryptobj = RC4.RC4(keys['server_enc_key'])
                elif self.cipher_suite['cipher'] == 'block':
                    self.c_cryptobj = EVP.Cipher(self.cipher_suite['algo'], keys['client_enc_key'], keys['client_iv'], 0, padding=0)
                    self.s_cryptobj = EVP.Cipher(self.cipher_suite['algo'], keys['server_enc_key'], keys['server_iv'], 0, padding=0)

        elif hst == self.EXT_SESSIONTICKET:
            # The first three bytes are the length, which we can skip
            # because we already have the entire handshake message.
            # We can also skip the next 4 bytes which are the lifetime hint.
            data = data[7:]
            # The next two bytes are the length of the session ticket.
            ticket_len = struct.unpack('>H', data[:2])[0]
            data = data[2:]
            if ticket_len != len(data):
                raise sslimBadValue("Bad ticket length", ticket_len)
            ticket = struct.unpack('%ss' % ticket_len, data[:ticket_len])[0]
            self.store_ms(ticket, self.ms)
        elif hst == self.CLIENT_KEY_EXCHANGE:
            if self.check_sid(self.s_sid):
                # XXX: The fact that the server session ID is in
                # the dictionary already is a really bad thing.
                # There should be no client key exchange message
                # if the client and server agree to resume.
                raise sslimBadValue("SID found with client key exchange")

            data = data[self.hs_key_exch_size:]
            # Client Hello (0x01) and Server Hello (0x02) have a version field
            # here while Client Key Exchange (0x10) puts the length here.  We
            # are skipping the length. Older SSL implementations may not put
            # the length here (see section 7.4.7.1 of RFC5246) though. We
            # should check these two bytes and compare them with the modulus of
            # the private key.

            # XXX: The size of this is dependent upon the cipher suite chosen!
            # Section 7.4.7.1 of RFC5246 details what these bytes mean for
            # RSA authentication!
            if self.ver == self.SSLv3_0:
                if self.cipher_suite['key_exch'] != 'RSA':
                    raise sslimUnknownCipher("SSLv3 not RSA key exchange")
                pms = data
            else:
                # The first two bytes are the length of the key.
                pms_len = int(struct.unpack('>H', data[:self.hs_pms_len_size])[0])
                data = data[self.hs_pms_len_size:]
                pms = struct.unpack('%ss' % pms_len, data[:pms_len])[0]

            try:
                cpms = self.keypair.private_decrypt(pms, RSA.sslv23_padding)
            except:
                raise sslimCryptoError()

            seed = self.c_rnd + self.s_rnd
            self.ms = self.__PRF(cpms, "master secret", seed, 48)[:48]

            # Store the master secret in the sids dictionary
            self.store_ms(self.s_sid, self.ms)

            # From the master secret you generate the key material
            seed = self.s_rnd + self.c_rnd
            km = self.__key_material(self.cipher_suite['km_len'], self.s_rnd + self.c_rnd, self.ms)
            keys = self.__split_key_material(km)
            self.cipher_suite['keys'] = keys
            if self.cipher_suite['cipher'] == 'stream':
                self.c_cryptobj = RC4.RC4(keys['client_enc_key'])
                self.s_cryptobj = RC4.RC4(keys['server_enc_key'])
            elif self.cipher_suite['cipher'] == 'block':
                self.c_cryptobj = EVP.Cipher(self.cipher_suite['algo'], keys['client_enc_key'], keys['client_iv'], 0, padding=0)
                self.s_cryptobj = EVP.Cipher(self.cipher_suite['algo'], keys['server_enc_key'], keys['server_iv'], 0, padding=0)

    def __split_key_material(self, km):
        key_size = self.cipher_suite['key_size']
        mac_size = self.cipher_suite['mac_size']

        keys = {
            'client_mac_key': km[:mac_size],
            'server_mac_key': km[mac_size:mac_size * 2],
            'client_enc_key': km[mac_size * 2:(mac_size * 2) + key_size],
            'server_enc_key': km[(mac_size * 2) + key_size:(mac_size * 2) + (key_size * 2)]
        }

        # Provide the IVs if needed by the cipher suite
        if 'block_size' in self.cipher_suite:
            block_size = self.cipher_suite['block_size']
            keys['client_iv'] = km[(mac_size * 2) + (key_size * 2):(mac_size * 2) + (key_size * 2) + block_size]
            keys['server_iv'] = km[(mac_size * 2) + (key_size * 2) + block_size:(mac_size * 2) + (key_size * 2) + (block_size * 2)]

        return keys

    def __key_material(self, km_len, seed, ms):
        if self.ver == self.SSLv3_0:
            alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            i = 0
            km = ''
            sha_md = EVP.MessageDigest('sha1')
            md5_md = EVP.MessageDigest('md5')

            while len(km) < km_len:
                sha_md.update((alpha[i] * (i + 1)) + ms + seed)
                md5_md.update(ms + sha_md.digest())
                km += md5_md.digest()
                # Reset the message digests and increment the index.
                sha_md.__init__('sha1')
                md5_md.__init__('md5')
                i = (i + 1) % 26
            return km[:km_len]
        else:
            return self.__PRF(ms, "key expansion", seed, km_len)[:km_len]

    def __A(self, num, secret, seed, alg):
        if num == 0:
            return seed
        else:
            return EVP.hmac(secret, self.__A(num - 1, secret, seed, alg), algo=alg)

    # TLS1.0 defines the PRF as splitting the seed, hashing the first half
    # with MD5 and hashing th second half with SHA1, then XOR the two
    # halves to produce the final output.
    # TLS1.2 defines a different PRF - just use SHA256, but also states
    # a cipher suite can define it's own PRF if desired.
    def __PRF(self, secret, label, seed, size):
        if self.ver == self.SSLv3_0:
            alpha = 'ABC'
            i = 0
            out = ''
            sha_md = EVP.MessageDigest('sha1')
            md5_md = EVP.MessageDigest('md5')

            for i in range(len(alpha)):
                sha_md.update((alpha[i] * (i + 1)) + secret + seed)
                md5_md.update(secret + sha_md.digest())
                out += md5_md.digest()
                # Reset the message digests and increment the index.
                sha_md.__init__('sha1')
                md5_md.__init__('md5')
            return out
        elif self.ver == self.TLSv1_0:
            # Split the secret into two halves.
            ls1 = ls2 = int(math.ceil(len(secret) / 2))
            s1 = secret[:ls1]
            s2 = secret[ls2:]

            label_seed = label + seed

            # s1 is the MD5 half
            ret1 = self.__P_hash(s1, label_seed, size, 'md5')

            # s2 is the SHA1 half
            ret2 = self.__P_hash(s2, label_seed, size, 'sha1')

            # XOR the two halves to get the master secret
            return ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(ret1, ret2))
        elif self.ver == self.TLSv1_2:
            label_seed = label + seed
            return self.__P_hash(secret, label_seed, size, 'sha256')

    def __P_hash(self, secret, seed, size, alg):
        ret = ''
        x = 1
        while len(ret) < size:
            ret += EVP.hmac(secret, self.__A(x, secret, seed, alg) + seed, algo=alg)
            x += 1
        return ret

    def __find_extension(self, data, extension):
        # The first two bytes are the length of this blob.
        ext_len = struct.unpack('>H', data[:2])[0]
        data = data[2:]
        if ext_len != len(data):
            raise sslimBadValue("Bad extension length", ext_len)

        # Extensions are two bytes for type and two bytes for length.
        while len(data) >= 4:
            (ext_type, ext_len) = struct.unpack('>HH', data[:4])
            if ext_type == extension and ext_len != 0:
                return data[4:4 + ext_len]
            data = data[4 + ext_len:]

    def __parse_rnd_and_sid(self, data):
        # Grab the random bytes
        rnd = struct.unpack('32s', data[:32])[0]
        data = data[32:]
        # Grab the session ID
        sid_len = struct.unpack('>B', data[:self.sid_len_size])[0]
        if sid_len != 0:
            data = data[1:]
            fmt_str = "%is" % sid_len
            sid = struct.unpack(fmt_str, data[:sid_len])[0]
        else:
            sid = 0
        return (rnd, sid, sid_len)

    # This is used as a callback to handle the alert record after
    # it has been decrypted. The decryption is done in __decrypt
    # which is called from __alert.
    def __parse_clear_alert(self, clear, callback_obj):
        pass

    # Assume the alert is encrypted.
    def __alert(self, data, direction):
        if direction == self.CLIENT_TO_SERVER:
            self.__decrypt(data, self.c_cryptobj, self.c_zobj, self.__parse_clear_alert)
        else:
            self.__decrypt(data, self.s_cryptobj, self.s_zobj, self.__parse_clear_alert)

    def __application_data(self, data, direction):
        if direction == self.CLIENT_TO_SERVER:
            self.__decrypt(data, self.c_cryptobj, self.c_zobj, self.req_callback)
        else:
            self.__decrypt(data, self.s_cryptobj, self.s_zobj, self.res_callback)

    def __decrypt(self, data, cryptobj, zobj, callback):
        clear = cryptobj.update(data)
        if self.compression == self.DEFLATE_COMPRESSION:
            # Do not strip the MAC and padding because that
            # is done in the decompression step.
            clear = self.__decompress(clear, zobj)
        else:
            # Strip the MAC and padding.
            if 'block_size' in self.cipher_suite:
                pad = ord(clear[-1:]) + 1
            else:
                pad = 0
            clear = clear[:-(self.cipher_suite['mac_size'] + pad)]

        if len(clear) > 0 and callback != None:
            ret = callback(clear, self.callback_obj)
            # Do not need to handle OK for now in case we want to do something
            # with it later.
            if ret == self.STOP:
                raise sslimCallbackStop()
            elif ret == self.ERROR:
                raise sslimCallbackError()

    def __decompress(self, data, zobj):
        # Strip off the padding. For some reason M2Crypto is stripping off
        # more than half the MAC too. So do it manually.
        # The last byte is always the padding length.
        if 'block_size' in self.cipher_suite:
            pad = ord(data[-1:]) + 1
        else:
            pad = 0
        return zobj.decompress(data[:-(self.cipher_suite['mac_size'] + pad)])

########NEW FILE########
__FILENAME__ = chop_ssl
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from optparse import OptionParser

from sslim import sslim, sslimException
from c2utils import parse_addr

from ChopProtocol import ChopProtocol

moduleName="chop_ssl"
moduleVersion="1.0"
minimumChopLib="4.0"

def sslim_req_callback(data, chopp):
    # Have to append because of multiple SSL records in a single packet.
    chopp.setClientData(chopp.clientData + data)

def sslim_res_callback(data, chopp):
    # Have to append because of multiple SSL records in a single packet.
    chopp.setServerData(chopp.serverData + data)

def module_info():
    return "Decrypt SSL sessions from TCP and pass \"sslim\" out."

def init(module_data):
    module_options = { 'proto': [ { 'tcp': 'sslim' } ] }

    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="Be verbose about new flows and packets")
    parser.add_option("-k", "--keyfile", action="store", dest="keyfile",
                      default=None, help="Private key file (must be RSA)")

    (opts, lo) = parser.parse_args(module_data['args'])

    module_data['verbose'] = opts.verbose
    module_data['keyfile'] = opts.keyfile

    if module_data['keyfile'] == None:
        module_options['error'] = "Must provide a keyfile."
        return module_options

    module_data['sslim'] = sslim(module_data['keyfile'])
    module_data['sslim'].req_callback = sslim_req_callback
    module_data['sslim'].res_callback = sslim_res_callback

    return module_options

def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr
    if tcp.module_data['verbose']:
        chop.tsprnt("New session: %s:%i -> %s:%i" % (src, sport, dst, dport))
    tcp.stream_data['ssl'] = False
    return True

def handleStream(tcp):
    # Make sure this is really SSL. Sadly we can't do this in taste()
    # because there is no payload data available that early.
    data = ''
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    server_dlen = tcp.server.count - tcp.server.offset
    client_dlen = tcp.client.count - tcp.client.offset
    # If we haven't identified this as SSL yet
    if tcp.stream_data['ssl'] == False:
        # Do we have enough data for checks?
        if tcp.server.count_new > 0 and server_dlen > 7:
            # Check if proxy CONNECT
            if tcp.server.data[:8] == "CONNECT ":
                if tcp.module_data['verbose']:
                    chop.tsprnt("%s:%i -> %s:%i (%i) - CONNECT (ignored)" % (src, sport, dst, dport, server_dlen))
                tcp.discard(server_dlen)
                return
            # Otherwise, prepare to check if SSL handshake
            data = tcp.server.data[:3]
        # Do we have enough data for checks?
        elif tcp.client.count_new > 0 and client_dlen > 5:
            # Check if proxy CONNECT response
            if tcp.client.data[:6] == "HTTP/1":
                if tcp.module_data['verbose']:
                    chop.tsprnt("%s:%i -> %s:%i (%i) - HTTP/1 (ignored)" % (src, sport, dst, dport, client_dlen))
                tcp.discard(client_dlen)
                return
            # Otherwise, prepare to check if SSL handshake
            data = tcp.client.data[:3]
        else:
            # Need more data
            return

        # We have data, so check if it is SSL Handshake.
        # There's probably more to this, but this is good enough for now.
        if data in ('\x16\x03\x00', '\x16\x03\x01', '\x16\x03\x02', '\x16\x03\x03'):
            tcp.stream_data['ssl'] = True
            tcp.stream_data['chopp'] = ChopProtocol('sslim')
            tcp.module_data['sslim'].callback_obj = tcp.stream_data['chopp']
        else:
            chop.tsprnt("%s:%i -> %s:%i: Stopping collection, not really SSL!" % (src, sport, dst, dport))
            tcp.module_data['sslim'].done(tcp.addr)
            tcp.stop()
            return

    # Always clear out any existing data.
    tcp.stream_data['chopp'].clientData = '' 
    tcp.stream_data['chopp'].serverData = ''

    # We have identified this connection as SSL, so just process the packets
    if tcp.server.count_new > 0:
        if tcp.module_data['verbose']:
            chop.tsprnt("%s:%s -> %s:%s (%i)" % (src, sport, dst, dport, len(tcp.server.data[:tcp.server.count_new])))
        try:
            tcp.module_data['sslim'].parse_to_server(tcp.server.data[:tcp.server.count_new], tcp.addr)
        except sslimException as e:
            if tcp.module_data['verbose']:
                chop.prnt(e)
            tcp.module_data['sslim'].done(tcp.addr)
            tcp.stop()
            return
        tcp.discard(tcp.server.count_new)
    if tcp.client.count_new > 0:
        if tcp.module_data['verbose']:
            chop.tsprnt("%s:%s -> %s:%s (%i)" % (src, sport, dst, dport, len(tcp.client.data[:tcp.client.count_new])))
        try:
            tcp.module_data['sslim'].parse_to_client(tcp.client.data[:tcp.client.count_new], tcp.addr)
        except sslimException as e:
            if tcp.module_data['verbose']:
                chop.prnt(e)
            tcp.module_data['sslim'].done(tcp.addr)
            tcp.stop()
            return
        tcp.discard(tcp.client.count_new)

    if tcp.stream_data['chopp'].clientData or tcp.stream_data['chopp'].serverData:
        return tcp.stream_data['chopp']

    return

def teardown(tcp):
    return

def shutdown(module_data):
    return

########NEW FILE########
__FILENAME__ = dns
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from dnslib import DNSRecord, QR, OPCODE, RCODE, QTYPE, CLASS

from ChopProtocol import ChopProtocol

moduleName = "dns"
moduleVersion = '0.1'
minimumChopLib = '4.0'

def module_info():
    return "Parse DNS"

def init(module_data):
    module_options = { 'proto': [ { 'udp': 'dns' } ] }
    return module_options

def handleDatagram(udp):
    ((src, sport), (dst, dport)) = udp.addr
    if sport != 53 and dport != 53:
        #chop.tsprnt("STOP: %s:%s->%s:%s (%i:%i)" % (src, sport, dst, dport, len(udp.data), len(udp.ip)))
        udp.stop()
        return

    try:
        o = DNSRecord.parse(udp.data)
    except KeyError, e:
        chop.prnt("Key error: %s" % str(e))
        return

    chopp = ChopProtocol('dns')

    # Create the dictionary...
    f = [ o.header.aa and 'AA',
          o.header.tc and 'TC',
          o.header.rd and 'RD',
          o.header.ra and 'RA' ]
    d = { 'header': {
                      'id': o.header.id,
                      'type': QR[o.header.qr],
                      'opcode': OPCODE[o.header.opcode],
                      'flags': ",".join(filter(None, f)),
                      'rcode': RCODE[o.header.rcode],
                    },
          'questions': o.questions
        }
    if OPCODE[o.header.opcode] == 'UPDATE':
        f1 = 'zo'
        f2 = 'pr'
        f3 = 'up'
        f4 = 'ad'
    else:
        f1 = 'q'
        f2 = 'a'
        f3 = 'ns'
        f4 = 'ar'
    dhdr = d['header']
    dhdr[f1] = o.header.q
    dhdr[f2] = o.header.a
    dhdr[f3] = o.header.ns
    dhdr[f4]= o.header.ar
    d['questions'] = []
    for q in o.questions:
        dq = {
              'qname': str(q.qname),
              'qtype': QTYPE[q.qtype],
              'qclass': QTYPE[q.qclass]
            }
        d['questions'].append(dq)
    d['rr'] = []
    for r in o.rr:
        dr = {
              'rname': str(r.rname),
              'rtype': QTYPE.lookup(r.rtype,r.rtype),
              'rclass': CLASS[r.rclass],
              'ttl': r.ttl,
              'rdata': str(r.rdata)
            }
        d['rr'].append(dr)

    if sport == 53:
        chopp.serverData = d
        return chopp
    elif dport == 53:
        chopp.clientData = d
        return chopp

    return None
   
def shutdown(module_data):
    return

########NEW FILE########
__FILENAME__ = dns_extractor
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from dnslib import DNSRecord, QR, OPCODE, RCODE, QTYPE, CLASS
from c2utils import packet_timedate
from optparse import OptionParser
import json

moduleName = 'dns_extractor'
moduleVersion = '0.1'
minimumChopLib = '4.0'

class dns_to_dict(json.JSONEncoder):
    def default(self, d):
        return json.JSONEncoder().encode(d)

def module_info():
    return "Handle DNS messages and print or send to mongo"

def init(module_data):
    module_options = { 'proto': [ { 'dns': '' } ] }
    parser = OptionParser()

    parser.add_option("-M", "--mongo", action="store_true", dest="mongo",
        default=False, help="Send output to mongodb")
    parser.add_option("-H", "--host", action="store", dest="host",
        default="localhost", help="Host to connect to")
    parser.add_option("-P", "--port", action="store", dest="port",
        default=27017, help="Port to connect to")
    parser.add_option("-D", "--db", action="store", dest="db",
        default='pcaps', help="Database to use")
    parser.add_option("-C", "--collection", action="store", dest="col",
        default='dns', help="Collection to use")

    (options,lo) = parser.parse_args(module_data['args'])

    module_data['mongo'] = options.mongo

    if module_data['mongo']:
        try:
            from dbtools import mongo_connector
        except ImportError, e:
            module_options['error'] = str(e)
            return module_options

        module_data['db'] = mongo_connector(options.host, options.port, options.db, options.col)

    chop.set_custom_json_encoder(dns_to_dict)

    return module_options

def handleProtocol(chopp):
    ((src, sport), (dst, dport)) = chopp.addr
    if sport == 53:
        data = chopp.serverData
    elif dport == 53:
        data = chopp.clientData

    if chopp.module_data['mongo']:
        chopp.module_data['db'].insert(data)
    chop.prnt(data)
    chop.json(data)

def shutdown(module_data):
    return

########NEW FILE########
__FILENAME__ = gh0st_decode
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

# The purpose of this chopshop module is to decode commands and responses
# for Gh0st backboors.
#
# The typical format for a Gh0st packet is:
# <flag><compressed_size><uncompressed_size><zlib payload>
#
# - flag is a 5 character string
# - compressed size is the size of the entire packet, not just zlib payload
# - uncompressed size of zlib payload
# - zlib payload consists of zlib header ('\x78\x9c') and compressed payload

import zlib
import struct
import binascii
import os
import ntpath
from optparse import OptionParser
from c2utils import sanitize_filename, parse_addr, winsizeize, hexdump

moduleName = "gh0st_decode"

def init(module_data):
    parser = OptionParser()
    parser.add_option("-s", "--savefiles", action="store_true",
                      dest="savefiles", default=False, help="save carved files")
    parser.add_option("-w", "--wsize", action="store", dest="wsize",
                      default=20, help="window size")
    parser.add_option("-v", "--verbose", action="store_true",
                      dest="verbose", default=False, help="verbosity")

    (opts, lo) = parser.parse_args(module_data['args'])

    module_data['savefiles'] = opts.savefiles
    module_data['verbose'] = opts.verbose
    module_data['wsize'] = opts.wsize
    module_data['tokens'] = {
                              '\x00': command_actived,
                              '\x01': command_list_drive,
                              '\x02': command_list_files,
                              '\x03': command_down_files,
                              '\x04': command_file_size,
                              '\x05': command_file_data,
                              '\x06': command_exception,
                              '\x07': command_continue,
                              '\x08': command_stop,
                              '\x09': command_delete_file,
                              '\x0a': command_delete_directory,
                              '\x0b': command_set_transfer_mode,
                              '\x0c': command_create_folder,
                              '\x0d': command_rename_file,
                              '\x0e': command_open_file_show,
                              '\x0f': command_open_file_hide,
                              '\x10': command_screen_spy,
                              '\x11': command_screen_reset,
                              '\x12': command_algorithm_reset,
                              '\x13': command_screen_ctrl_alt_del,
                              '\x14': command_screen_control,
                              '\x15': command_screen_block_input,
                              '\x16': command_screen_blank,
                              '\x17': command_screen_capture_layer,
                              '\x18': command_screen_get_clipboard,
                              '\x19': command_screen_set_clipboard,
                              '\x1a': command_webcam,
                              '\x1b': command_webcam_enablecompress,
                              '\x1c': command_webcam_disablecompress,
                              '\x1d': command_webcam_resize,
                              '\x1e': command_next,
                              '\x1f': command_keyboard,
                              '\x20': command_keyboard_offline,
                              '\x21': command_keyboard_clear,
                              '\x22': command_audio,
                              '\x23': command_system,
                              '\x24': command_pslist,
                              '\x25': command_wslist,
                              '\x26': command_dialupass,
                              '\x27': command_killprocess,
                              '\x28': command_shell,
                              '\x29': command_session,
                              '\x2a': command_remove,
                              '\x2b': command_down_exec,
                              '\x2c': command_update_server,
                              '\x2d': command_clean_event,
                              '\x2e': command_open_url_hide,
                              '\x2f': command_open_url_show,
                              '\x30': command_rename_remark,
                              '\x31': command_replay_heartbeat,
                              '\x64': token_auth,
                              '\x65': token_heartbeat,
                              '\x66': token_login,
                              '\x67': token_drive_list,
                              '\x68': token_file_list,
                              '\x69': token_file_size,
                              '\x6a': token_file_data,
                              '\x6b': token_transfer_finish,
                              '\x6c': token_delete_finish,
                              '\x6d': token_get_transfer_mode,
                              '\x6e': token_get_filedata,
                              '\x6f': token_createfolder_finish,
                              '\x70': token_data_continue,
                              '\x71': token_rename_finish,
                              '\x72': token_exception,
                              '\x73': token_bitmapinfo,
                              '\x74': token_firstscreen,
                              '\x75': token_nextscreen,
                              '\x76': token_clipboard_text,
                              '\x77': token_webcam_bitmapinfo,
                              '\x78': token_webcam_dib,
                              '\x79': token_audio_start,
                              '\x7a': token_audio_data,
                              '\x7b': token_keyboard_start,
                              '\x7c': token_keyboard_data,
                              '\x7d': token_pslist,
                              '\x7e': token_wslist,
                              '\x7f': token_dialupass,
                              '\x80': token_shell_start
                            }

    if module_data['savefiles']:
        chop.prnt("Carving enabled.")

    module_options = {'proto':'tcp'}

    return module_options

def taste(tcp):
    tcp.stream_data['client_buf'] = ''
    tcp.stream_data['server_buf'] = ''
    tcp.stream_data['flag'] = ''
    tcp.stream_data['shell'] = False
    tcp.stream_data['compressed_len'] = 0
    return True

def handleStream(tcp):
    #((src, sport), (dst, dport)) = tcp.addr
    data = ''

    if tcp.server.count_new > 0:
        if not tcp.stream_data['flag'] and (len(tcp.stream_data['server_buf']) + tcp.server.count_new) < tcp.module_data['wsize']:
            tcp.stream_data['server_buf'] += tcp.server.data[:tcp.server.count_new]
            #chop.tsprnt("Buffered server: %i (total: %i)." % (tcp.server.count_new, len(tcp.stream_data['server_buf'])))
            tcp.discard(tcp.server.count_new)
            return

        data = tcp.stream_data['server_buf'] + tcp.server.data[:tcp.server.count_new]
        tcp.discard(tcp.server.count_new)

        if tcp.stream_data['flag'] and len(data) < (len(tcp.stream_data['flag']) + 4):
            tcp.stream_data['server_buf'] = data
            #chop.tsprnt("%s:%i->%s:%i Data too small. Buffered server: %i (total: %i)" % (src, sport, dst, dport, tcp.server.count_new, len(data)))
            return
    elif tcp.client.count_new > 0:
        if not tcp.stream_data['flag'] and (len(tcp.stream_data['client_buf']) + tcp.client.count_new) < tcp.module_data['wsize']:
            tcp.stream_data['client_buf'] += tcp.client.data[:tcp.client.count_new]
            #chop.tsprnt("Buffered client: %i (total: %i)." % (tcp.client.count_new, len(tcp.stream_data['client_buf'])))
            tcp.discard(tcp.client.count_new)
            return

        data = tcp.stream_data['client_buf'] + tcp.client.data[:tcp.client.count_new]
        tcp.discard(tcp.client.count_new)

        if tcp.stream_data['flag'] and len(data) < (len(tcp.stream_data['flag']) + 4):
            tcp.stream_data['client_buf'] = data
            #chop.tsprnt("%s:%i->%s:%i Data too small. Buffered client: %i (total: %i)" % (src, sport, dst, dport, tcp.client.count_new, len(data)))
            return

    if tcp.stream_data['flag']:
        while data:
            #chop.tsprnt("Handling blob: %s:%i->%s:%i (%i)" % (src, sport, dst, dport, len(data)))
            if tcp.stream_data['compressed_len'] == 0:
                compressed_len = struct.unpack('<I', data[len(tcp.stream_data['flag']):len(tcp.stream_data['flag']) + 4])[0]
                tcp.stream_data['compressed_len'] = compressed_len
            else:
                compressed_len = tcp.stream_data['compressed_len']

            if len(data) < compressed_len:
                if tcp.server.count_new > 0:
                    #chop.tsprnt("LEN DATA: (%i) COMPRESSED LEN: (%i) NEW BUFFER: %i" % (len(data), compressed_len, len(tcp.stream_data['server_buf']) + len(data)))
                    tcp.stream_data['server_buf'] = data
                elif tcp.client.count_new > 0:
                    #chop.tsprnt("LEN DATA: (%i) COMPRESSED LEN: (%i) NEW BUFFER: %i" % (len(data), compressed_len, len(tcp.stream_data['client_buf']) + len(data)))
                    tcp.stream_data['client_buf'] = data
                return

            #chop.tsprnt("COMPRESSED LEN MATCH, DECODING!")
            if tcp.stream_data['zlib']:
                msg = zlib.decompress(data[len(tcp.stream_data['flag']) + 8:len(tcp.stream_data['flag']) + 8 + compressed_len])
            else:
                msg = data[len(tcp.stream_data['flag'] + 8):]
            decode(msg, tcp)
            data = data[compressed_len:]
            tcp.stream_data['compressed_len'] = 0
            if tcp.server.count_new > 0:
                tcp.stream_data['server_buf'] = ''
            elif tcp.client.count_new > 0:
                tcp.stream_data['client_buf'] = ''
    else:
        #chop.tsprnt("Finding flag: %s:%i->%s:%i (%i)" % (src, sport, dst, dport, len(data)))
        # The first gh0st message fits in a single TCP payload,
        # unless you have MTU problems.
        tcp.stream_data['flag'] = find_flag(data, tcp)
        if not tcp.stream_data['flag']:
            #chop.tsprnt("No flag found, skipping stream.")
            tcp.stop()

def find_flag(data, tcp):
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    flag = ''
    module_data = tcp.module_data

    for i in range(tcp.module_data['wsize'] - 3):
        compressed_len = struct.unpack('<I', data[i:i + 4])[0]
        if compressed_len == len(data):
            flag = data[:i]
            i += 4
            uncompressed_len = struct.unpack('<I', data[i:i + 4])[0]
            i += 4
            if module_data['verbose']:
                chop.tsprnt("Gh0st found: %s:%i->%s:%i (%i)" % (src, sport, dst, dport, compressed_len))
                chop.tsprnt("\tFlag: %s (0x%s)" % (flag, binascii.hexlify(flag)))
                chop.tsprnt("\tUncompressed length: %i" % uncompressed_len)

            zlib_hdr = struct.unpack('>H', data[i:i + 2])[0]
            if zlib_hdr == 30876: # \x78\x9c
                tcp.stream_data['zlib'] = True
                if module_data['verbose']:
                    chop.tsprnt("\tzlib header found")
                if len(data) == compressed_len:
                    msg = zlib.decompress(data[i:])
                    # Sanity check
                    if len(msg) != uncompressed_len:
                        chop.tsprnt("Uncompressed size mismatch.")
                        tcp.stop()
                        return None
            else:
                tcp.stream_data['zlib'] = False
                if module_data['verbose']:
                    chop.tsprnt("\tno zlib header found")
                msg = data[i:]

            decode(msg, tcp)
            break

    return flag

# In the gh0st world there are commands and tokens.
# Commands are sent from controller to implant.
# Tokens are sent from implant to controller.
def decode(msg, tcp):
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    #chop.tsprnt("%s:%i->%s:%i" % (src, sport, dst, dport), None)

    # If this is a shell session, just dump the contents.
    if tcp.stream_data['shell'] == True:
        chop.prnt("\n%s" % msg)
        return

    # Grab the token and decode if possible.
    b = struct.unpack('c', msg[:1])[0]
    if b in tcp.module_data['tokens']:
        msg = msg[1:]
        tcp.module_data['tokens'][b](msg, tcp)
    else:
        chop.prnt("Unknown token: 0x%02x" % ord(b))
        chop.prnt("%s" % hexdump(msg))

def command_actived(msg, tcp):
    chop.prnt("COMMAND: ACTIVED")

def command_list_drive(msg, tcp):
    chop.prnt("COMMAND: LIST DRIVE")

def command_list_files(msg, tcp):
    chop.prnt("COMMAND: LIST FILES (%s)" % msg[:-1])

def command_down_files(msg, tcp):
    chop.prnt("COMMAND: DOWN FILES (%s)" % msg[:-1])

def command_file_size(msg, tcp):
    (fname, size) = get_name_and_size(msg, tcp)
    chop.prnt("COMMAND: FILE SIZE (%s: %i)" % (fname, size))

def command_file_data(msg, tcp):
    chop.prnt("COMMAND: FILE DATA (%i)" % len(msg[8:]))
    if tcp.module_data['savefiles']:
        carve_file(msg, tcp)

# These should only be sent in the case of problems with the
# controller or implant. As such, leave them in debugging mode.
def command_exception(msg, tcp):
    chop.prnt("command_exception\n%s" % hexdump(msg))

def command_continue(msg, tcp):
    # XXX: Sent with 8 bytes. The bytes are important, skip them.
    chop.prnt("COMMAND: CONTINUE")

def command_stop(msg, tcp):
    chop.prnt("COMMAND: STOP")

def command_delete_file(msg, tcp):
    chop.prnt("COMMAND: DELETE FILE (%s)" % msg[:-1])

def command_delete_directory(msg, tcp):
    chop.prnt("COMMAND: DELETE DIRECTORY (%s)" % msg[:-1])

def command_set_transfer_mode(msg, tcp):
    mode = struct.unpack('<I', msg[:4])[0]
    if mode == 0x00000000:
        msg = "NORMAL"
    elif mode == 0x00000001:
        msg = "ADDITION"
    elif mode == 0x00000002:
        msg = "ADDITION ALL"
    elif mode == 0x00000003:
        msg = "OVERWRITE"
    elif mode == 0x00000004:
        msg = "OVERWRITE ALL"
    elif mode == 0x00000005:
        msg = "JUMP"
    elif mode == 0x00000006:
        msg = "JUMP ALL"
    elif mode == 0x00000007:
        msg = "CANCEL"
    else:
        msg = "UNKNOWN"
    chop.prnt("COMMAND: SET TRANSFER MODE (%s)" % msg)

def command_create_folder(msg, tcp):
    chop.prnt("COMMAND: CREATE FOLDER (%s)" % msg[:-1])

def command_rename_file(msg, tcp):
    null = msg.find('\x00')
    chop.prnt("COMMAND: RENAME FILE (%s -> %s)" % (msg[:null], msg[null + 1:]))

def command_open_file_show(msg, tcp):
    chop.prnt("COMMAND: OPEN FILE SHOW (%s)" % msg[:-1])

def command_open_file_hide(msg, tcp):
    chop.prnt("COMMAND: OPEN FILE HIDE (%s)" % msg[:-1])

def command_screen_spy(msg, tcp):
    chop.prnt("COMMAND: SCREEN SPY")

def command_screen_reset(msg, tcp):
    b = struct.unpack('B', msg[0])[0]
    chop.prnt("COMMAND: SCREEN RESET (%i)" % b)

def command_algorithm_reset(msg, tcp):
    b = struct.unpack('B', msg[0])[0]
    chop.prnt("COMMAND: ALGORITHM RESET (%i)" % b)

def command_screen_ctrl_alt_del(msg, tcp):
    chop.prnt("COMMAND: SEND CTRL ALT DEL")

def command_screen_control(msg, tcp):
    # No need to parse this structure. It's just mouse movements
    # and button presses. They won't mean anything on their own.
    # You need the context of the screen on which they are happening.
    chop.prnt("COMMAND: SCREEN CONTROL")
    #chop.prnt("command_screen_control\n%s" % hexdump(msg))

def command_screen_block_input(msg, tcp):
    b = struct.unpack('B', msg)[0]
    if b == 0:
        status = "OFF"
    else:
        status = "ON"
    chop.prnt("COMMAND: SCREEN BLOCK INPUT (%s)" % status)

def command_screen_blank(msg, tcp):
    b = struct.unpack('B', msg)[0]
    if b == 0:
        status = "OFF"
    else:
        status = "ON"
    chop.prnt("COMMAND: SCREEN BLANK (%s)" % status)

def command_screen_capture_layer(msg, tcp):
    b = struct.unpack('B', msg)[0]
    if b == 0:
        status = "OFF"
    else:
        status = "ON"
    chop.prnt("COMMAND: SCREEN CAPTURE LAYER (%s)" % status)

def command_screen_get_clipboard(msg, tcp):
    chop.prnt("COMMAND: SCREEN GET CLIPBOARD\n%s" % msg[:-1])

def command_screen_set_clipboard(msg, tcp):
    chop.prnt("COMMAND: SCREEN SET CLIPBOARD\n%s" % msg[:-1])

# XXX
def command_webcam(msg, tcp):
    chop.prnt("COMMAND: WEBCAM")

# XXX
def command_webcam_enablecompress(msg, tcp):
    chop.prnt("command_webcam_enablecompress\n%s" % hexdump(msg))

def command_webcam_disablecompress(msg, tcp):
    chop.prnt("COMMAND: WEBCAM DISABLECOMPRESS")

# XXX
def command_webcam_resize(msg, tcp):
    chop.prnt("command_webcam_resize\n%s" % hexdump(msg))

def command_next(msg, tcp):
    chop.prnt("COMMAND: NEXT")

def command_keyboard(msg, tcp):
    chop.prnt("COMMAND: KEYBOARD")

def command_keyboard_offline(msg, tcp):
    chop.prnt("COMMAND: KEYBOARD OFFLINE")

def command_keyboard_clear(msg, tcp):
    chop.prnt("COMMAND: KEYBOARD CLEAR")

def command_audio(msg, tcp):
    chop.prnt("COMMAND: AUDIO")

def command_system(msg, tcp):
    chop.prnt("COMMAND: SYSTEM")

def command_pslist(msg, tcp):
    chop.prnt("COMMAND: PSLIST")

def command_wslist(msg, tcp):
    chop.prnt("COMMAND: WSLIST")

def command_dialupass(msg, tcp):
    chop.prnt("COMMAND: DIALUPASS")

def command_killprocess(msg, tcp):
    chop.prnt("COMMAND: KILLPROCESS (%i)" % struct.unpack('<I', msg[:4])[0])

def command_shell(msg, tcp):
    chop.prnt("COMMAND: SHELL")

def command_session(msg, tcp):
    # A one byte value indicates the kind of session control.
    # Values are documented in:
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa376868(v=vs.85).aspx 
    # All values are OR'ed with EWX_FORCE.
    b = struct.unpack('B', msg[0])[0]
    if b == 0x04:
        t = "LOGOFF"
    elif b == 0x05:
        t = "SHUTDOWN"
    elif b == 0x06:
        t = "REBOOT"
    chop.prnt("COMMAND: SESSION (%s)" % t)

def command_remove(msg, tcp):
    chop.prnt("COMMAND: REMOVE")

def command_down_exec(msg, tcp):
    chop.prnt("COMMAND: DOWN EXEC (%s)" % msg[:-1])

def command_update_server(msg, tcp):
    chop.prnt("COMMAND: UPDATE SERVER (%s)" % msg[:-1])

def command_clean_event(msg, tcp):
    chop.prnt("COMMAND: CLEAN EVENT")

def command_open_url_hide(msg, tcp):
    chop.prnt("COMMAND: OPEN URL HIDE (%s)" % msg[:-1])

def command_open_url_show(msg, tcp):
    chop.prnt("COMMAND: OPEN URL SHOW (%s)" % msg[:-1])

# I've never been able to get this command to send.
# Leave in for debugging reasons.
def command_rename_remark(msg, tcp):
    chop.prnt("command_rename_remark\n%s" % hexdump(msg))

# This is never sent either.
# Leave in for debugging reasons.
def command_replay_heartbeat(msg, tcp):
    chop.prnt("command_replay_heartbeat\n%s" % hexdump(msg))

# This token is never sent but leave in for debugging.
def token_auth(msg, tcp):
    chop.prnt("token_auth\n%s" % hexdump(msg))

# This token is never sent but leave in for debugging.
def token_heartbeat(msg, tcp):
    chop.prnt("token_heartbeat\n%s" % hexdump(msg))

def token_login(msg, tcp):
    # XXX: FIGURE OUT WHAT THESE BYTES ARE!
    msg = msg[3:]

    # The OsVerInfoEx structure is documented at:
    # http://msdn.microsoft.com/en-us/library/windows/desktop/ms724833(v=vs.85).aspx
    (osver_size, major, minor, build) = struct.unpack('<IIII', msg[:16])
    # Grab the rest after this structure, before we start messing with
    # the buffer.
    buf = msg[osver_size:]

    # Skip over the platform ID.
    msg = msg[20:]
    null = msg.find('\x00')
    sp = msg[:null]
    if len(sp) == 0:
        sp = "No service pack"
    # The service pack string is always 128 bytes long.
    # Skip service pack major and minor (each are 2 bytes).
    msg = msg[132:]
    (suite_mask, product_type) = struct.unpack('<HB', msg[:3])
    msg = msg[4:]
    os = "UNKNOWN OS (0x%08x.0x%08x SM: 0x%04x PT: 0x%02x)" % (major, minor, suite_mask, product_type)
    if major == 0x00000005:
        if minor == 0x00000000:
            os = "Windows 2000"
        elif minor == 0x00000001:
            os = "Windows XP"
        elif minor == 0x00000002:
            if product_type == 0x01:
                os = "Windows XP"
            elif suite_mask & 0x8000:
                os = "Windows Home Server"
            else:
                os = "Windows Server 2003"
    elif major == 0x00000006:
        if minor == 0x00000000:
            if product_type == 0x01:
                os = "Windows Vista"
            else:
                os = "Windows Server 2008"
        elif minor == 0x00000001:
            if product_type == 0x01:
                os = "Windows 7"
            else:
                os = "Windows Server 2008 R2"
        elif minor == 0x00000002:
            if product_type == 0x01:
                os = "Windows 8"
            else:
                os = "Windows Server 2012"

    # A true gh0st login will have 64 bytes left at this point.
    # There are variants that alter this and add other things.
    # Catch this...
    if len(msg) != 64:
        token = "TOKEN: LOGIN (IP AND WEBCAM MAY BE WRONG)"
    else:
        token = "TOKEN: LOGIN"

    # Parse the clock speed and IP (in case it's behind a NAT).
    (clock, ip) = struct.unpack('<iI', buf[:8])
    buf = buf[8:]
    null = buf.find('\x00')
    hostname = buf[:null]
    buf = buf[50:]
    # The webcam field is a bool. In my sample this is 2 bytes. May not
    # always be true depending upon compiler.
    if struct.unpack('<H', buf[:2])[0]:
        webcam = "yes"
    else:
        webcam = "no"

    # XXX: Use socket.inet_ntoa() to convert to dotted quad.
    chop.prnt("%s: %s: %s %s - Build: %i - Clock: %i Mhz - IP: %s.%s.%s.%s Webcam: %s" % (token, hostname, os, sp, build, clock, ip & 0x000000FF, (ip & 0x0000FF00) >> 8, (ip & 0x00FF0000) >> 16, (ip & 0xFF000000) >> 24, webcam))

def token_drive_list(msg, tcp):
    chop.prnt("TOKEN: DRIVE LIST")
    chop.prnt("DRIVE\tTOTAL\tFREE\tFILESYSTEM\tDESCRIPTION")
    while len(msg) > 9:
        drive = struct.unpack('c', msg[0])[0]
        # Skip drive type, single byte.
        msg = msg[2:]
        (total, free) = struct.unpack('<II', msg[:8])
        msg = msg[8:]
        null = msg.find('\x00')
        desc = msg[:null]
        msg = msg[null + 1:]
        null = msg.find('\x00')
        fs = msg[:null]
        chop.prnt("%s\t%i\t%i\t%s\t%s" % (drive, total, free, fs, desc))
        msg = msg[null + 1:]

def token_file_list(msg, tcp):
    if len(msg) == 0:
        chop.prnt("TOKEN: FILE LIST (INVALID HANDLE)")
        return
    chop.prnt("TOKEN: FILE LIST")
    chop.prnt("TYPE\tNAME\tSIZE\tWRITE TIME")
    while len(msg) >= 1:
        d = struct.unpack('B', msg[1])[0]
        if d & 0x10:
            d = "DIR"
        else:
            d = "FILE"
        msg = msg[1:]
        null = msg.find('\x00')
        name = msg[:null]
        msg = msg[null + 1:]
        (hsize, lsize, wtime) = struct.unpack('<IIQ', msg[:16])
        size = winsizeize(hsize, lsize)
        msg = msg[16:]
        chop.prnt("%s\t%s\t%i\t%i" % (d, name, size, wtime))

def token_file_size(msg, tcp):
    (fname, size) = get_name_and_size(msg, tcp)
    chop.prnt("TOKEN: FILE SIZE (%s: %i)" % (fname, size))

def token_file_data(msg, tcp):
    chop.prnt("TOKEN: FILE DATA (%i)" % len(msg[8:]))
    if tcp.module_data['savefiles']:
        carve_file(msg, tcp)

def token_transfer_finish(msg, tcp):
    chop.prnt("TOKEN: TRANSFER FINISH")

def token_delete_finish(msg, tcp):
    chop.prnt("TOKEN: DELETE FINISH")

def token_get_transfer_mode(msg, tcp):
    chop.prnt("TOKEN: GET TRANSFER MODE")

# XXX: This is never sent by the implant.
# Leave it in debugging state for now.
def token_get_filedata(msg, tcp):
    chop.prnt("token_get_filedata\n%s" % hexdump(msg))

def token_createfolder_finish(msg, tcp):
    chop.prnt("TOKEN: CREATEFOLDER FINISH")

def token_data_continue(msg, tcp):
    # XXX: Sent with 8 bytes. Appear to be transfer modes. Not important.
    chop.prnt("TOKEN: DATA CONTINUE")

def token_rename_finish(msg, tcp):
    chop.prnt("TOKEN: RENAME FINISH")

def token_exception(msg, tcp):
    chop.prnt("token_exception\n%s" % hexdump(msg))

def token_bitmapinfo(msg, tcp):
    #chop.prnt("token_bitmapinfo\n%s" % hexdump(msg))
    chop.prnt("TOKEN: BITMAPINFO")

# XXX
def token_firstscreen(msg, tcp):
    #chop.prnt("token_firstscreen\n%s" % hexdump(msg))
    chop.prnt("TOKEN: FIRST SCREEN")

# XXX
def token_nextscreen(msg, tcp):
    #chop.prnt("token_nextscreen\n%s" % hexdump(msg))
    chop.prnt("TOKEN: NEXT SCREEN")

def token_clipboard_text(msg, tcp):
    chop.prnt("TOKEN: CLIPBOARD TEXT\n%s" % msg[:-1])

# XXX
def token_webcam_bitmapinfo(msg, tcp):
    #chop.prnt("token_webcam_bitmapinfo\n%s" % hexdump(msg))
    chop.prnt("TOKEN: WEBCAM BITMAP INFO")

def token_webcam_dib(msg, tcp):
    #chop.prnt("token_webcam_dib\n%s" % hexdump(msg))
    chop.prnt("TOKEN: WEBCAM DIB")

def token_audio_start(msg, tcp):
    chop.prnt("TOKEN: AUDIO START")

# XXX
def token_audio_data(msg, tcp):
    #chop.prnt("token_audio_data\n%s" % hexdump(msg))
    chop.prnt("TOKEN: AUDIO DATA")

def token_keyboard_start(msg, tcp):
    b = struct.unpack('B', msg)[0]
    if b == 0:
        status = "OFFLINE"
    else:
        status = "ONLINE"
    chop.prnt("TOKEN: KEYBOARD START (%s)" % status)

def token_keyboard_data(msg, tcp):
    chop.prnt("TOKEN: KEYBOARD DATA\n%s" % msg)

def token_pslist(msg, tcp):
    chop.prnt("TOKEN: PSLIST")
    chop.prnt("PID\tEXE\t\tPROC NAME")
    while len(msg) >= 4:
        pid = struct.unpack('<I', msg[:4])[0]
        msg = msg[4:]
        null = msg.find('\x00')
        exe = msg[:null]
        msg = msg[null + 1:]
        null = msg.find('\x00')
        name = msg[:null]
        msg = msg[null + 1:]
        chop.prnt("%i\t%s\t\t%s" % (pid, exe, name))

def token_wslist(msg, tcp):
    chop.prnt("TOKEN: WSLIST")
    chop.prnt("PID\tTITLE")
    while len(msg) >= 4:
        pid = struct.unpack('<I', msg[:4])[0]
        msg = msg[4:]
        null = msg.find('\x00')
        title = msg[:null]
        msg = msg[null + 1:]
        chop.prnt("%i\t%s" % (pid, title))

def token_dialupass(msg, tcp):
    # XXX: HANDLE!
    chop.prnt("TOKEN: DIALUPASS")

def token_shell_start(msg, tcp):
    chop.prnt("TOKEN: SHELL START")
    tcp.stream_data['shell'] = True

def get_name_and_size(msg, tcp):
    (hsize, lsize) = struct.unpack('<II', msg[:8])
    size = winsizeize(hsize, lsize)
    fname = msg[8:-1]
    if tcp.module_data['savefiles']:
        tcp.stream_data['fsize'] = size
        tcp.stream_data['fname'] = sanitize_filename(fname)
        chop.prnt(tcp.stream_data['fname'])
        tcp.stream_data['byteswritten'] = 0
    return (fname, size)

def carve_file(msg, tcp):
    if tcp.stream_data['byteswritten'] == 0:
        chop.savefile(tcp.stream_data['fname'], msg[8:])
    else:
        chop.appendfile(tcp.stream_data['fname'], msg[8:])

    tcp.stream_data['byteswritten'] += len(msg[8:])

    if tcp.stream_data['byteswritten'] < tcp.stream_data['fsize']:
        chop.prnt("Wrote %i of %i to %s" % (tcp.stream_data['byteswritten'], tcp.stream_data['fsize'], tcp.stream_data['fname']))
    elif tcp.stream_data['byteswritten'] > tcp.stream_data['fsize']:
        chop.prnt("OVERFLOW: Wrote %i of %i to %s" % (tcp.stream_data['byteswritten'], tcp.stream_data['fsize'], tcp.stream_data['fname']))
        chop.finalizefile(tcp.stream_data['fname'])
        tcp.stream_data['fname'] = ''
        tcp.stream_data['fsize'] = 0
    else:
        chop.prnt("Wrote %i of %i to %s" % (tcp.stream_data['byteswritten'], tcp.stream_data['fsize'], tcp.stream_data['fname']))
        chop.finalizefile(tcp.stream_data['fname'])
        tcp.stream_data['fname'] = ''
        tcp.stream_data['fsize'] = 0

def teardown(tcp):
    pass

def module_info():
    return "Decode and display Gh0st backdoor commands and responses"

def shutdown(module_data):
    pass

########NEW FILE########
__FILENAME__ = heartbleed_payloads
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
A module to dump memory leaked from the OpenSSL Heartbleed vulnerability
https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-0160
"""

import sys
import struct
import time
from base64 import b64encode
from optparse import OptionParser
from c2utils import multibyte_xor, hexdump, parse_addr, entropy

moduleName = 'heartbleed_payloads'
moduleVersion = '2.0'
minimumChopLib = '4.0'


def parse_args(module_data):
    parser = OptionParser()

    parser.add_option("-b", "--base64", action="store_true",
        dest="base64", default=False,
        help="Base64 encode payloads (useful for JSON handling) (TCP)")
    parser.add_option("-v", "--verbose", action="store_true",
        dest="verbose", default=False, help="print all information")
    parser.add_option("-x", "--hexdump", action="store_true",
        dest="hexdump", default=False, help="print hexdump output")
    
    (opts,lo) = parser.parse_args(module_data['args'])

    module_data['verbose'] = opts.verbose
    module_data['hexdump'] = opts.hexdump

    return opts

def init(module_data):
    opts = parse_args(module_data)

    module_options = {'proto': []}

    tcp = {'tcp' : ''}

    module_options['proto'].append(tcp)

    return module_options

def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr

    if tcp.module_data['verbose']:
        chop.tsprnt("Start Session %s:%s -> %s:%s"  % (src, sport, dst, dport))

    tcp.stream_data['dump'] = False

    return True

def handleStream(tcp):
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    if tcp.client.count_new > 0:
        data = tcp.client.data[:tcp.client.count_new]
        count = tcp.client.count_new
        if tcp.stream_data['dump']:
            chop.tsprnt("%s:%s -> %s:%s %i bytes" % (src, sport, dst, dport, count,))
            chop.prnt(hexdump(data))
        if data[:3] in ['\x18\x03\x00', '\x18\x03\x01', '\x18\x03\x02', '\x18\x03\x03']:
            chop.tsprnt("%s:%s -> %s:%s %i bytes" % (src, sport, dst, dport, count,))
            chop.prnt(hexdump(data[8:]))
            tcp.stream_data['dump'] = True

    tcp.discard(count)

def teardown(tcp):
	pass

def module_info():
    return "A module to dump memory leaks from PCAPs of the OpenSSL Heartbleed vulnerability" 

########NEW FILE########
__FILENAME__ = http
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from c2utils import packet_timedate, sanitize_filename, parse_addr
from optparse import OptionParser
from base64 import b64encode
import json
import htpy
import hashlib

import sys
import os
import Queue

from ChopProtocol import ChopProtocol


#TODO
# Add more error checking
# See if any useful information is missing

moduleName ="http"
moduleVersion ='0.1'
minimumChopLib ='4.0'

__hash_function__ = None

def log(cp, msg, level, obj):
    if level == htpy.HTP_LOG_ERROR:
        elog = cp.get_last_error()
        if elog == None:
            return htpy.HTP_ERROR
        chop.prnt("%s:%i - %s (%i)" % (elog['file'], elog['line'], elog['msg'], elog['level']))
    else:
        chop.prnt("%i - %s" % (level, msg))
    return htpy.HTP_OK

# The request and response body callbacks are treated identical with one
# exception: the location in the output dictionary where the data is stored.
# Because they are otherwise identical each body callback is a thin wrapper
# around the real callback.
def request_body(data, length, obj):
    return body(data, length, obj, 'request')

def response_body(data, length, obj):
    return body(data, length, obj, 'response')

def body(data, length, obj, direction):
    trans = obj['temp']

    trans[direction]['body_len'] += length

    if length == 0:
        return htpy.HTP_OK

    trans[direction]['tmp_hash'].update(data)

    if trans[direction]['truncated'] == True:
        return htpy.HTP_OK

    if obj['options']['no-body']:
        trans[direction]['body']  = ''
        trans[direction]['truncated'] = True
        return htpy.HTP_OK

    if trans[direction]['body'] is not None:
        trans[direction]['body'] += data
    else:
        trans[direction]['body'] = data

    #Truncate to Maximum Length
    if obj['options']['length'] > 0 and len(trans[direction]['body']) > obj['options']['length']:
        trans[direction]['body'] = trans[direction]['body'][:(obj['options']['length'])]
        trans[direction]['truncated'] = True

    return htpy.HTP_OK

def request_headers(cp, obj):
    trans = obj['temp']
    trans['start'] = obj['timestamp']
    trans['request'] = {}
    trans['request']['truncated'] = False #Has the body been truncated?
    trans['request']['body'] = None
    trans['request']['body_len'] = 0

    trans['request']['hash_fn'] = obj['options']['hash_function']
    trans['request']['tmp_hash'] = __hash_function__()

    trans['request']['headers'] = cp.get_all_request_headers()
    trans['request']['uri'] = cp.get_uri()
    trans['request']['method'] = cp.get_method()

    protocol = cp.get_request_protocol_number()
    proto = "HTTP/"

    if protocol == htpy.HTP_PROTOCOL_UNKNOWN:
        proto = "UNKNOWN"
    elif protocol == htpy.HTP_PROTOCOL_0_9:
        proto += "0.9"
    elif protocol == htpy.HTP_PROTOCOL_1_0:
        proto += "1.0"
    elif protocol == htpy.HTP_PROTOCOL_1_1:
        proto += "1.1"
    else:
        proto = "Error"

    trans['request']['protocol'] = proto

    return htpy.HTP_OK

def request_complete(cp, obj):
    #Move request data to the lines queue
    trans = obj['temp']
    if trans['request']['body_len'] > 0:
        trans['request']['body_hash'] = trans['request']['tmp_hash'].hexdigest()
    else:
        trans['request']['body_hash'] = ""
    del trans['request']['tmp_hash']

    obj['lines'].put(obj['temp']['request'])
    obj['temp']['request'] = {}

    return htpy.HTP_OK

def response_headers(cp, obj):
    trans = obj['temp']
    trans['response'] = {}
    trans['response']['headers'] = cp.get_all_response_headers()
    trans['response']['status'] = cp.get_response_status()

    trans['response']['hash_fn'] = obj['options']['hash_function']
    trans['response']['tmp_hash'] = __hash_function__()

    trans['response']['truncated'] = False
    trans['response']['body'] = None
    trans['response']['body_len'] = 0

    return htpy.HTP_OK

def response_complete(cp, obj):
    trans = obj['temp']

    if trans['response']['body_len'] > 0:
        trans['response']['body_hash'] = trans['response']['tmp_hash'].hexdigest()
    else:
        trans['response']['body_hash'] = ""
    del trans['response']['tmp_hash']

    try:
        req = obj['lines'].get(False) #Do not block
    except Queue.Empty:
        pass
        #TODO error

    obj['transaction'] = {
                'request': req,
                'response' : trans['response'],
                'timestamp' : trans['start'],
                }

    obj['ready'] = True

    return htpy.HTP_OK

def register_connparser():
    connparser = htpy.init()
    connparser.register_log(log)
    connparser.register_request_headers(request_headers)
    connparser.register_response_headers(response_headers)
    connparser.register_request_body_data(request_body)
    connparser.register_response_body_data(response_body)
    connparser.register_request_complete(request_complete)
    connparser.register_response_complete(response_complete)
    return connparser


def module_info():
    return "Takes in TCP traffic and outputs parsed HTTP traffic for use by secondary modules. Refer to the docs for output format"

def init(module_data):
    module_options = { 'proto': [ {'tcp': 'http'}, { 'sslim': 'http' } ] }
    parser = OptionParser()

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Be verbose about incoming packets")
    parser.add_option("-b", "--no-body", action="store_true", dest="nobody",
        default=False, help="Do not store http bodies")
    parser.add_option("-l", "--length", action="store", dest="length", type="int",
        default=5242880, help="Maximum length of bodies in bytes (Default: 5MB, set to 0 to process all body data)")
    parser.add_option("-a", "--hash-function", action="store", dest="hash_function",
        default="md5", help="Hash Function to use on bodies (default 'md5', available: 'sha1', 'sha256', 'sha512')")
    parser.add_option("-p", "--ports", action="store", dest="ports",
        default="80", help="List of ports to check comma separated, e.g., \"80,8080\", pass an empty string \"\" to scan all ports (default '80')")

    (options,lo) = parser.parse_args(module_data['args'])

    global __hash_function__
    if options.hash_function == 'sha1':
        __hash_function__ = hashlib.sha1
    elif options.hash_function == 'sha256':
        __hash_function__ = hashlib.sha256
    elif options.hash_function == 'sha512':
        __hash_function__ = hashlib.sha512
    else:
        options.hash_function = 'md5'
        __hash_function__ = hashlib.md5

    ports = options.ports.split(",")
    try: #This will except if ports is empty or malformed
        ports = [int(port) for port in ports]
    except:
        ports = []

    module_data['counter'] = 0
    module_data['options'] = {
                                'verbose' : options.verbose,
                                'no-body' : options.nobody,
                                'length' : options.length,
                                'hash_function' : options.hash_function,
                                'ports' : ports
                             }

    return module_options

def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr
    if len(tcp.module_data['options']['ports']):
        ports = tcp.module_data['options']['ports']
        if sport not in ports and dport not in ports:
            return False

    if tcp.module_data['options']['verbose']:
        chop.tsprnt("New session: %s:%s->%s:%s" % (src, sport, dst, dport))


    tcp.stream_data['htpy_obj'] = {
                                    'options': tcp.module_data['options'],
                                    'timestamp': None,
                                    'temp': {},
                                    'transaction': {},
                                    'lines': Queue.Queue(),
                                    'ready': False,
                                    'flowStart': tcp.timestamp
                                   }
    tcp.stream_data['connparser'] = register_connparser()
    tcp.stream_data['connparser'].set_obj(tcp.stream_data['htpy_obj'])
    return True

def handleStream(tcp):
    chopp = ChopProtocol('http')
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    tcp.stream_data['htpy_obj']['timestamp'] = tcp.timestamp
    if tcp.server.count_new > 0:
        if tcp.module_data['options']['verbose']:
            chop.tsprnt("%s:%s->%s:%s (%i)" % (src, sport, dst, dport, tcp.server.count_new))
        try:
            tcp.stream_data['connparser'].req_data(tcp.server.data[:tcp.server.count_new])
        except htpy.stop:
            tcp.stop()
        except htpy.error:
            chop.prnt("Stream error in htpy.")
            tcp.stop()
        tcp.discard(tcp.server.count_new)
    elif tcp.client.count_new > 0:
        if tcp.module_data['options']['verbose']:
            chop.tsprnt("%s:%s->%s:%s (%i)" % (src, sport, dst, dport, tcp.client.count_new))
        try:
            tcp.stream_data['connparser'].res_data(tcp.client.data[:tcp.client.count_new])
        except htpy.stop:
            tcp.stop()
        except htpy.error:
            chop.prnt("Stream error in htpy.")
            tcp.stop()
        tcp.discard(tcp.client.count_new)

    if tcp.stream_data['htpy_obj']['ready']:
        trans = tcp.stream_data['htpy_obj']['transaction']
        chopp.setClientData(trans['request'])
        chopp.setServerData(trans['response'])
        chopp.setTimeStamp(trans['timestamp'])
        chopp.setAddr(tcp.addr)
        chopp.flowStart = tcp.stream_data['htpy_obj']['flowStart']
        tcp.stream_data['htpy_obj']['ready'] = False
        return chopp

    return None

def teardown(tcp):
    return

def shutdown(module_data):
    return

def handleProtocol(chopp):
    if chopp.type != 'sslim':
        return

    stream_data = chopp.stream_data

    if 'htpy_obj' not in stream_data:
        stream_data['htpy_obj'] = {
                                    'options': chopp.module_data['options'],
                                    'timestamp': None,
                                    'temp': {},
                                    'transaction': {},
                                    'lines': Queue.Queue(),
                                    'ready': False,
                                    'flowStart': chopp.timestamp
                                  }
        stream_data['connparser'] = register_connparser()
        stream_data['connparser'].set_obj(stream_data['htpy_obj'])

    ((src, sport),(dst,dport)) = chopp.addr
    stream_data['htpy_obj']['timestamp'] = chopp.timestamp

    if chopp.clientData:
        if chopp.module_data['options']['verbose']:
            chop.tsprnt("%s:%s->%s:%s" % (src, sport, dst, dport))
        try:
            stream_data['connparser'].req_data(chopp.clientData)
        except htpy.stop:
            chopp.stop()
        except htpy.error:
            chop.prnt("Stream error in htpy.")
            chopp.stop()
            return

    if chopp.serverData:
        if chopp.module_data['options']['verbose']:
            chop.tsprnt("%s:%s->%s:%s" % (dst, dport, src, sport))
        try:
            stream_data['connparser'].res_data(chopp.serverData)
        except htpy.stop:
            chopp.stop()
        except htpy.error:
            chop.prnt("Stream error in htpy.")
            chopp.stop()
            return

    if stream_data['htpy_obj']['ready']:
        new_chopp = ChopProtocol('http')
        trans = stream_data['htpy_obj']['transaction']
        new_chopp.setClientData(trans['request'])
        new_chopp.setServerData(trans['response'])
        new_chopp.setTimeStamp(trans['timestamp'])
        new_chopp.setAddr(chopp.addr)
        new_chopp.flowStart = stream_data['htpy_obj']['flowStart']
        stream_data['htpy_obj']['ready'] = False
        return new_chopp

########NEW FILE########
__FILENAME__ = http_extractor
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from c2utils import packet_timedate, sanitize_filename, parse_addr
from optparse import OptionParser
from base64 import b64encode

moduleName="http_extractor"
moduleVersion="2.0"
minimumChopLib="4.0"

def module_info():
    return "Extract HTTP information. Requires 'http' parent module. Print or generate JSON"

def init(module_data):
    module_options = { 'proto': [{'http':''}]}
    parser = OptionParser()

    parser.add_option("-s", "--carve_response_body", action="store_true",
        dest="carve_response", default=False, help="Save response body")
    parser.add_option("-S", "--carve_request_body", action="store_true",
        dest="carve_request", default=False, help="Save request body")
    parser.add_option("-f", "--fields", action="store", dest="fields",
        default=[], help="Comma separated list of fields to extract")
    parser.add_option("-m", "--hash_body", action="store_true", dest="hash_body",
        default=False, help="Save hash of body and throw contents away")


    (options,lo) = parser.parse_args(module_data['args'])

    module_data['counter'] = 0
    module_data['carve_request'] = options.carve_request
    module_data['carve_response'] = options.carve_response
    module_data['hash_body'] = options.hash_body
    module_data['fields'] = []

    if options.fields:
        fields = options.fields.split(',')
        for field in fields:
            chop.prnt("Extracting field: %s" % field)
        module_data['fields'] = fields

    return module_options

def handleProtocol(protocol):
    if protocol.type != 'http':
        chop.prnt("Error")
        return

    module_data = protocol.module_data
    data = {'request': protocol.clientData, 'response': protocol.serverData}

    if data['request']['body'] is None:
        del data['request']['body']
        del data['request']['body_hash']
    elif module_data['hash_body']:
        del data['request']['body']

    if data['response']['body'] is None:
        del data['response']['body']
        del data['response']['body_hash']
    elif module_data['hash_body']:
        del data['response']['body']

    del data['request']['truncated']
    del data['request']['body_len']
    del data['request']['hash_fn']

    del data['response']['truncated']
    del data['response']['body_len']
    del data['response']['hash_fn']

    fields = module_data['fields']
    if fields:
        req_fields = fields + ['uri', 'method']
        new_headers = {}
        for header in data['request']['headers']:
            if header in req_fields:
               new_headers[header] = data['request']['headers'][header] 

        for element in data['request'].keys():
            if element not in req_fields:
                del data['request'][element]

        #Set the new headers dictionary
        data['request']['headers'] = new_headers

        res_fields = fields + ['status']
        new_headers = {}
        for header in data['response']['headers']:
            if header in res_fields:
                new_headers[header] = data['response']['headers'][header]

        for element in data['response'].keys():
            if element not in res_fields:
                del data['response'][element]

        data['response']['headers'] = new_headers
            
    if module_data['carve_request'] and 'body' in data['request']:
        fname = sanitize_filename(data['request']['uri']['path'][1:]) + '.request.' + str(module_data['counter'])
        chop.prnt("DUMPING REQUEST: %s (%i)" % (fname, len(data['request']['body'])))
        chop.savefile(fname, data['request']['body'])
        module_data['counter'] += 1

    if module_data['carve_response'] and 'body' in data['response']:
        fname = sanitize_filename(data['request']['uri']['path'][1:]) + '.response.' + str(module_data['counter'])
        chop.prnt("DUMPING RESPONSE: %s (%i)" % (fname, len(data['response']['body'])))
        chop.savefile(fname, data['response']['body'])
        module_data['counter'] += 1

    # Convert the body to base64 encoded data, if it exists.
    if 'body' in data['request']:
        data['request']['body'] = b64encode(data['request']['body'])
        data['request']['body_encoding'] = 'base64'
    if 'body' in data['response']:
        data['response']['body'] = b64encode(data['response']['body'])
        data['response']['body_encoding'] = 'base64'

    chop.prnt(data)
    chop.json(data)
    
    return

def shutdown(module_data):
    return

########NEW FILE########
__FILENAME__ = icmp
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from optparse import OptionParser
import struct
from ChopProtocol import ChopProtocol

moduleName="icmp"
moduleVersion="0.1"
minimumChopLib="4.0"

class icmp_message:
    pass

def module_info():
    return "Processes IP data and returns 'icmp' data"

def init(module_data):
    module_options = { 'proto': [{'ip': 'icmp'}]}

    return module_options

def handlePacket(ip):
    if ip.protocol != 1:
        return None

    #Okay so we have traffic labeled as ICMP
    icmp = ChopProtocol('icmp')
    ip_offset = 4 * ip.ihl
    icmp_raw = ip.raw[ip_offset:] #separate the icmp data
    header = struct.unpack('<BBH', icmp_raw[0:4])

    #Since this doesn't fit a client server model
    #Created a new 'data' field in the ChopProtocol object
    #Note that the _clone method in ChopProtocol uses deepcopy
    #so we should be okay
    icmp.data = icmp_message()
    icmp.data.type = header[0]
    icmp.data.code = header[1]
    icmp.data.checksum = header[2]
    icmp.data.raw = icmp_raw
    
    return icmp

def shutdown(module_data):
    return


########NEW FILE########
__FILENAME__ = metacap
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
A module to extract metadata from a PCAP.
"""

from optparse import OptionParser
from c2utils import parse_addr, packet_isodate, packet_timedate, entropy
from jsonutils import jsonOrReprEncoder

moduleName = 'metacap'

def init(module_data):
    module_options = {'proto':'tcp'}
    parser = OptionParser()

    parser.add_option("-i", "--isodate", action="store_true",
        dest="isodate", default=False, help="convert dates to ISODate")
    parser.add_option("-b", "--bulk", action="store_true",
        dest="bulk", default=False,
        help="output only after all input has been processed")
    parser.add_option("-q", "--quiet", action="store_true",
        dest="quiet", default=False,
        help="only print summary information (json not affected)")

    (opts,lo) = parser.parse_args(module_data['args'])

    module_data['isodate'] = opts.isodate
    module_data['bulk'] = opts.bulk
    module_data['quiet'] = opts.quiet

    module_data['pcap_summary'] = {
                                    'type': 'pcap',
                                    'data': {
                                        'total_packets': 0,
                                        'total_streams': 0,
                                        'end_time': '',
                                        'total_data_transfer': 0,
                                    }
                                  }
    module_data['streams'] = {}

    #This allows json to handle datetime
    chop.set_custom_json_encoder(jsonOrReprEncoder)

    return module_options

def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr
    if tcp.module_data['isodate']:
        timestamp = packet_isodate(tcp.timestamp)
    else:
        timestamp = packet_timedate(tcp.timestamp)

    tcp.module_data['streams'][str(tcp.addr)] = {
                                   'type' : 'stream',
                                   'data' : {
                                       'comm_order': [],
                                       'start_time': timestamp,
                                       'end_time': timestamp,
                                       'src': src,
                                       'sport': sport,
                                       'dst': dst,
                                       'dport': dport,
                                       'client_data_transfer': 0,
                                       'server_data_transfer': 0,
                                       'total_packets': 0
                                   }
                                }

    if 'start_time' not in tcp.module_data['pcap_summary']['data']:
        tcp.module_data['pcap_summary']['data']['start_time'] = timestamp
    tcp.module_data['pcap_summary']['data']['total_streams'] += 1

    return True

def handleStream(tcp):
    key = str(tcp.addr)
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    if tcp.module_data['isodate']:
        timestamp = packet_isodate(tcp.timestamp)
    else:
        timestamp = packet_timedate(tcp.timestamp)

    ps = tcp.module_data['pcap_summary']['data']
    cs = tcp.module_data['streams'][key]['data']
    if tcp.server.count_new > 0:
        comm = { 'data_to': 'S',
                 'data_len': tcp.server.count_new,
                 'entropy': entropy(tcp.server.data[:tcp.server.count_new])
               }
        cs['comm_order'].append(comm)
        cs['server_data_transfer'] += tcp.server.count_new
        ps['total_data_transfer'] += tcp.server.count_new
        tcp.discard(tcp.server.count_new)
    else:
        comm = { 'data_to': 'C',
                 'data_len': tcp.client.count_new,
                 'entropy': entropy(tcp.client.data[:tcp.client.count_new])
               }
        cs['comm_order'].append(comm)
        cs['client_data_transfer'] += tcp.client.count_new
        ps['total_data_transfer'] += tcp.client.count_new
        tcp.discard(tcp.client.count_new)
    cs['end_time'] = timestamp
    cs['total_packets'] += 1
    ps['total_packets'] += 1
    ps['end_time'] = timestamp

    return

def teardown(tcp):
    if not tcp.module_data['bulk']:
        key = str(tcp.addr)
        my_stream = tcp.module_data['streams'][key]
        chop.json(my_stream)

        if not tcp.module_data['quiet']: __print_stream_data(my_stream['data'])

        del tcp.module_data['streams'][key]
    return

def shutdown(module_data):
    if not module_data['bulk']:
        #Any Streams that didn't teardown remove them now
        for stream, metadata in module_data['streams'].iteritems():
            chop.json(metadata)

            if not module_data['quiet']: __print_stream_data(metadata['data'])

        chop.json(module_data['pcap_summary'])

    else:
        output = []
        for stream, metadata in module_data['streams'].iteritems():
            output.append(metadata)
            if not module_data['quiet']: __print_stream_data(metadata['data'])

        output.append(module_data['pcap_summary'])
        chop.json(output)

    chop.prettyprnt("YELLOW", "Summary:")
    chop.prettyprnt("CYAN", "\tStart Time: %s  -> End Time: %s" %
                (module_data['pcap_summary']['data']['start_time'],
                 module_data['pcap_summary']['data']['end_time']))
    chop.prettyprnt("CYAN", "\tTotal Packets: %s\n\tTotal Streams: %s" %
                (module_data['pcap_summary']['data']['total_packets'],
                 module_data['pcap_summary']['data']['total_streams']))
    chop.prettyprnt("CYAN", "\tTotal Data Transfered: %s " %
                (module_data['pcap_summary']['data']['total_data_transfer']))
    chop.prnt("")


def module_info():
    return "A module to extract metadata from a PCAP."


def __print_stream_data(data):
    chop.prettyprnt("YELLOW", "%s:%s -> %s:%s -- %s -> %s" %
                (data['src'],
                 data['sport'],
                 data['dst'],
                 data['dport'],
                 data['start_time'],
                 data['end_time']
                )
             )
    chop.prettyprnt("CYAN", "\tTotal Packets: %s" % data['total_packets'])
    chop.prettyprnt("CYAN", "\tClient Data: %s" % data['client_data_transfer'])
    chop.prettyprnt("CYAN", "\tServer Data: %s" % data['server_data_transfer'])

    if len(data['comm_order']) > 0:
        chop.prettyprnt("MAGENTA",
                        "\tComm Order:\tTo\tLength\tEntropy\n",
                        None)
    for comm_dict in data['comm_order']:
        chop.prettyprnt("MAGENTA",
                        '\t\t\t%s' % comm_dict['data_to'],
                        None)
        chop.prettyprnt("MAGENTA",
                        '\t%s' % comm_dict['data_len'],
                        None)
        chop.prettyprnt("MAGENTA",
                        '\t%s\n' % comm_dict['entropy'],
                        None)
    if len(data['comm_order']) > 0:
        chop.prnt("")

    chop.prnt("")

########NEW FILE########
__FILENAME__ = payloads
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
A module to dump raw packet payloads from a stream.
Meant to be used to watch netcat reverse shells and other plaintext
backdoors.
"""

import sys
import struct
import time
from base64 import b64encode
from optparse import OptionParser
from c2utils import multibyte_xor, hexdump, parse_addr, entropy

moduleName = 'payloads'
moduleVersion = '2.1'
minimumChopLib = '4.0'

def parse_args(module_data):
    parser = OptionParser()

    parser.add_option("-b", "--base64", action="store_true",
        dest="base64", default=False,
        help="Base64 encode payloads (useful for JSON handling) (TCP)")
    parser.add_option("-v", "--verbose", action="store_true",
        dest="verbose", default=False, help="print all information")
    parser.add_option("-x", "--hexdump", action="store_true",
        dest="hexdump", default=False, help="print hexdump output")
    parser.add_option("-o", "--xor", action="store",
        dest="xor_key", default=None, help="XOR packet payloads with this key")
    parser.add_option("-O", "--oneshot", action="store_true",
        dest="oneshot", default=False,
        help="Buffer entire flow until teardown (TCP)")
    parser.add_option("-S", "--oneshot_split", action="store_true",
        dest="oneshot_split", default=False,
        help="Buffer each side of flow until teardown (TCP)")
    parser.add_option("-u", "--udp-disable", action="store_true",
        dest="disable_udp", default=False, help="Disable UDP support")
    parser.add_option("-t", "--tcp-disable", action="store_true",
        dest="disable_tcp", default=False, help="Disable TCP support")
    parser.add_option("-s", "--sslim-disable", action="store_true",
        dest="disable_sslim", default=False, help="Disable sslim support")

    (opts,lo) = parser.parse_args(module_data['args'])

    module_data['base64'] = opts.base64
    module_data['verbose'] = opts.verbose
    module_data['hexdump'] = opts.hexdump
    module_data['oneshot'] = opts.oneshot
    module_data['oneshot_split'] = opts.oneshot_split

    if opts.xor_key:
        if opts.xor_key.startswith('0x'):
            module_data['xor_key'] = opts.xor_key[2:]
        else:
            module_data['xor_key'] = opts.xor_key

    return opts

def init(module_data):
    opts = parse_args(module_data)

    module_options = {'proto': []}

    tcp = {'tcp': ''}
    udp = {'udp': ''}
    sslim = {'sslim': ''}

    if not opts.disable_tcp:
        module_options['proto'].append(tcp)

    if not opts.disable_udp:
        module_options['proto'].append(udp)

    if not opts.disable_sslim:
        module_options['proto'].append(sslim)

    if len(module_options['proto']) == 0: # They disabled all?
        module_options['error'] = "Must leave one protocol enabled."

    return module_options

# TCP
def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr

    if tcp.module_data['verbose']:
        chop.tsprnt("Start Session %s:%s -> %s:%s"  % (src, sport, dst, dport))

    # Used for oneshot, just concat both directions into a giant blob.
    tcp.stream_data['data'] = ''
    # Used for oneshot_split, concat each direction into it's own blob.
    tcp.stream_data['to_server'] = ''
    tcp.stream_data['to_client'] = ''

    return True

def handleStream(tcp):
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    if tcp.server.count_new > 0:
        data = tcp.server.data[:tcp.server.count_new]
        count = tcp.server.count_new
        direction = 'to_server'
        color = "RED"
    else:
        data = tcp.client.data[:tcp.client.count_new]
        count = tcp.client.count_new
        direction = 'to_client'
        color = "GREEN"

    if tcp.module_data['verbose']:
        chop.tsprettyprnt(color, "%s:%s -> %s:%s %i bytes (H = %0.2f)" % (src, sport, dst, dport, count, entropy(data)))

    if tcp.module_data['oneshot']:
        tcp.stream_data['data'] += data

    if tcp.module_data['oneshot_split']:
        tcp.stream_data[direction] += data

    if tcp.module_data['oneshot'] or tcp.module_data['oneshot_split']:
        return

    handle_bytes(data, color, direction, tcp.module_data)
    tcp.discard(count)

# sslim
def handleProtocol(chopp):
    if chopp.type != 'sslim':
        return

    if chopp.clientData:
        handle_bytes(chopp.clientData, 'GREEN', 'to_client', chopp.module_data)
    if chopp.serverData:
        handle_bytes(chopp.serverData, 'RED', 'to_server', chopp.module_data)

def handle_bytes(data, color, direction, module_data):
    if 'xor_key' in module_data:
        data = multibyte_xor(data, module_data['xor_key'])

    if module_data['hexdump']:
        data = hexdump(data)

    if module_data['base64']:
        data = b64encode(data)

    chop.prettyprnt(color, data)
    chop.json({'payload': data, 'direction': direction})

def teardown(tcp):
    if not tcp.module_data['oneshot'] and not tcp.module_data['oneshot_split']:
        return

    if tcp.module_data['oneshot']:
        data = (alert_data, tcp.module_data, tcp.stream_data['data'])
        chop.prnt(data)
        chop.json({'payload': data, 'direction': 'combined'})

    if tcp.module_data['oneshot_split']:
        for direction in ['to_client', 'to_server']:
            data = alter_data(tcp.module_data, tcp.stream_data[direction])
            chop.prnt(data)
            chop.json({'payload': data, 'direction': direction})

def alter_data(module_data, data):
    if 'xor_key' in module_data:
        data = multibyte_xor(data, module_data['xor_key'])

    if module_data['hexdump']:
        data = hexdump(data)

    if module_data['base64']:
        data = b64encode(data)

    return data

# UDP
def handleDatagram(udp):
	# collect time and IP metadata
	((src, sport), (dst, dport)) = udp.addr
	# handle client system packets
        if udp.module_data['verbose']:
            chop.tsprettyprnt("RED", "%s:%s -> %s:%s 0x%04X bytes" % (src, sport, dst, dport, len(udp.data)))
        if 'xor_key' in udp.module_data:
            data = multibyte_xor(udp.data, udp.module_data['xor_key'])
        else:
            data = udp.data
        if udp.module_data['hexdump']:
            data = hexdump(data)
        chop.prettyprnt("RED", data)

def module_info():
    return "A module to dump raw packet payloads from a stream.\nMeant to be used to watch netcat reverse shells and other plaintext\nbackdoors."

########NEW FILE########
__FILENAME__ = poisonivy_23x
# Copyright (c) 2014 FireEye, Inc. All rights reserved.
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import re
import os
import camcrypt
import binascii
import string
import socket

from optparse import OptionParser
from struct import *

from c2utils import *
import lznt1

moduleName="poisonivy_23x"

def portlist(data, tcp):
    statuses = {2 : 'LISTENING', 5 : 'ESTABLISHED'}
    chop.tsprnt("*** Active Ports Listing Sent ***")
    #big endian short, UDP == 1, TCP == 0
    #if UDP, carry on but skip remote pair
    #4 bytes - local IP
    #big endian short local port
    #2 null bytes
    # remote IP
    # remort port
    #2 null bytes
    #1 byte status
    # little endian int PID
    #1 byte proc name length
    chop.prnt("Protocol\tLocal IP\tLocal Port\tRemote IP\tRemote Port\tStatus\tPID\tProc Name")
    #chop.prnt("data len: %d" % len(data))
    while data != "":
        (proto, localip, localport) = unpack('>H4sH', data[:8])
        if proto == 1:
            proto = "UDP"
        else:
            proto = "TCP"
        #localip = socket.inet_ntoa(data[:4])
        localip = socket.inet_ntoa(localip)
        data = data[10:] # Skipping 2 bytes
        if proto == "TCP":
            (remoteip, remoteport, status) = unpack('>4sHxxB', data[:9])
            remoteip = socket.inet_ntoa(remoteip)
            data = data[9:]
            if remoteip == "0.0.0.0":
                remoteport = "*"
                remoteip = "*"
        (pid, proclen) = unpack("<IB", data[:5])
        data = data[5:]
        procname = data[:proclen]
        procname = string.strip(procname, "\x00")
        data = data[proclen:]
        if proto == "TCP":
            chop.prnt("%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s" % (proto,
                       localip,
                       localport,
                       remoteip,
                       remoteport,
                       statuses.get(status, "UNKNOWN: 0x%x" % status),
                       pid,
                       procname))
        else:
            chop.prnt("%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s\t\t%s" % (proto,
                       localip,
                       localport,
                       "*",
                       "*",
                       "*",
                       pid,
                       procname))

def dirEnt(data, tcp):
    # Print either the directory name (if) or it's contents (else)
    if data[:10] == '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01':
        chop.prnt("%s" % data[10:])
    else:
        l = ord(data[0])
        data = data[1:]
        if data[0] == '\x00':
            return

        chop.prnt("\t%s"  % (data[:l]))
        data = data[l:]
        #l =ord(data[0])

        data = data[24:]

        if len(data):
            dirEnt(data)
    return

def heartbeat(data, tcp):
    return

def shell(data, tcp):
    chop.tsprnt("*** Shell Session ***")
    chop.prnt(data)
    return

def dirlist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Directory Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-directory-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    dirEnt(data)
    return

def hostinfo(data, tcp):
    chop.tsprnt("*** Host Information ***")
    str_regex = r"^([\w\x20\t\\\:\-\.\&\%\$\#\@\!\(\)\*]+)$"
    profilegroup = ""
    #grab profile id string, not in fixed position
    for i in range(len(data)):
        if ord(data[i]) == 0:
            continue
        match = re.match(str_regex, data[i + 1:i + 1 + ord(data[i])])
        if match is not None:
            profileid = match.group(1)
            #move past profile string
            i = i + 1 + ord(data[i])
            break

    #check for profile group string
    if ord(data[i]) != 0:
        groupend = i + 1 + ord(data[i])
        profilegroup = data[i + 1:groupend]
        i = groupend
    else:
        i += 1

    ip = socket.inet_ntoa(data[i:i + 4])
    i += 4
    hostname = data[i + 1:i + 1 + ord(data[i])]
    i = i + 1 + ord(data[i])
    username = data[i + 1:i + 1 + ord(data[i])]
    i = i + 1 + ord(data[i])
    producttype = ord(data[i])
    i += 5
    (majorver, minorver, build) = unpack("<III", data[i:i + 12])
    i += 16 # Not sure why skipping another 4 bytes
    csd = ""
    if (ord(data[i]) >= 32 and ord(data[i]) <= 126):
        for i in range(i, len(data[i:])):
            if ord(data[i]) == 0:
                break
            csd += data[i]

    if majorver == 5 and minorver == 0:
        osver = "Windows 2000"
    elif majorver == 5 and minorver == 1:
        osver = "Windows XP"
    elif majorver == 5 and minorver == 2 and build == 2600:
        osver = "Windows XP Professional x64 Edition"
    elif majorver == 5 and minorver == 2:
        osver = "Windows Server 2003"
    elif majorver == 6 and minorver == 0 and build == 6000:
        osver = "Windows Vista"
    elif majorver == 6 and minorver == 0:
        osver = "Windows Server 2008"
    elif majorver == 6 and minorver == 1 and build == 7600:
        osver = "Windows 7"
    elif majorver == 6 and minorver == 1:
        osver = "Windows Server 2008 R2"
    elif majorver == 6 and minorver == 2 and build == 9200:
        osver = "Windows 8"
    elif majorver == 6 and minorver == 2:
        osver = "Windows Server 2012"

    chop.prnt("PI profile ID: %s" % profileid)
    if profilegroup != "":
        chop.prnt("PI profile group: %s" % profilegroup)
    chop.prnt("IP address: %s" % ip)
    chop.prnt("Hostname: %s" % hostname)
    chop.prnt("Windows User: %s" % username)
    chop.prnt("Windows Version: %s" % osver)
    chop.prnt("Windows Build: %d" % build)
    if csd != "":
        chop.prnt("Service Pack: %s" % csd)

    return

def reglist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Registry Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-registry-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def servicelist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Service Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-service-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def proclist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Process Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-process-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def devicelist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Device Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-device-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def windowlist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Window Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-window-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def installedlist(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Installed Application Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-installed-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def passwordlist(data, tcp):
    module_data = tcp.module_data
    if len(data) == 0:
        chop.tsprnt("*** Password Listing Request - Nothing Found ***")
        return

    chop.tsprnt("*** Password Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-password-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def nofilesearchresults(data, tcp):
    chop.tsprnt("*** End of File Search Results ***")
    return

def noregsearchresults(data, tcp):
    chop.tsprnt("*** End of Registry Search Results ***")
    return

def filesearchresults(data, tcp):
    chop.tsprnt("*** File Search Results ***")
    dirlen = ord(data[0])
    endofdir = 1 + dirlen
    directory = data[1:endofdir]
    chop.prnt("Directory: %s" % directory)
    data = data[endofdir:]
    while data != "":
        filelen = ord(data[0])
        endoffile = 1 + filelen
        filename = data[1:endoffile]
        chop.prnt("File Name: %s" % filename)
        data = data[endoffile+20:]
    return

def regsearchresults(data, tcp):
    chop.tsprnt("*** Registry Search Results ***")
    keylen = ord(data[0])
    endofkey = 1 + keylen
    keyroot = data[1:endofkey]
    data = data[endofkey:]

    while data != "":
        if ord(data[0]) == 0:
            root = "HKEY_CLASSES_ROOT"
        elif ord(data[0]) == 1:
            root = "HKEY_CURRENT_USER"
        elif ord(data[0]) == 2:
            root = "HKEY_LOCAL_MACHINE"
        elif ord(data[0]) == 3:
            root = "HKEY_USERS"
        elif ord(data[0]) == 5:
            root = "HKEY_CURRENT_CONFIG"
        else:
            root = "??"

        #TODO: find the other types
        if ord(data[1]) == 1:
            type = "REG_SZ"
        elif ord(data[1]) == 4:
            type = "REG_DWORD"
        elif ord(data[1]) == 11:
            type = "KEY"
        else:
            type = "??"

        data = data[2:]
        chop.prnt("Root: %s" % root)
        if type == "KEY":
            strlen = ord(data[0])
            data = data[1:]
            key = keyroot + data[:strlen]
        else:
            key = keyroot
            if ord(data[0]) == 0:
                valname = "(default)"
                data = data[1:]
            else:
                valnamelen = ord(data[0])
                endofvalname = 1 + valnamelen
                valname = data[1:endofvalname]
                data = data[endofvalname:]

            strlen = unpack("<I", data[0:4])[0]
            data = data[4:]
            value = data[:strlen - 1]

        data = data[strlen:]

        chop.prnt("Key: %s" % key)
        chop.prnt("Type: %s" % type)
        chop.prnt("Value Name: %s" % valname)
        if type in ["REG_DWORD", "REG_BINARY"]:
            chop.prnt("Value (hex): %s" % binascii.hexlify(value))
        else:
            chop.prnt("Value: %s" % value)

    return

def skip(data, tcp):
    return

def remotedesktop(data, tcp):
    chop.tsprnt("*** Remote Desktop Session ***")
    return

def webcam(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Web Cam Capture Sent ***")
    if module_data['savecaptures']:
        filename = "PI-extracted-file-%d-webcam.bmp" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def audio(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Audio Capture Sent ***")
    if module_data['savecaptures']:
        filename = "PI-extracted-file-%d-audio.raw" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("audio capture was saved in RAW format as %s" % filename)
    return

def screenshot(data, tcp):
    module_data = tcp.module_data
    chop.tsprnt("*** Screen Capture Sent ***")
    if module_data['savecaptures']:
        filename = "PI-extracted-file-%d-screenshot.bmp" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def keylog(data, tcp):
    module_data = tcp.module_data
    if len(data) == 0:
        chop.tsprnt("*** Keystroke Data Request - Nothing Found ***")
        return

    chop.tsprnt("*** Keystroke Data Sent ***")
    if module_data['savecaptures'] and len(data) > 0:
        filename = "PI-extracted-file-%d-keystrokes.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def cachedpwlist(data, tcp):
    module_data = tcp.module_data
    if len(data) == 0:
        chop.tsprnt("*** Cached Password Request - Nothing Found ***")
        return

    chop.tsprnt("*** Cached Password Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-cachedpw-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def ntlmhashlist(data, tcp):
    if len(data) == 0:
        chop.tsprnt("*** NT/NTLM Hash Listing Request - Nothing Found ***")
        return

    chop.tsprnt("*** NT/NTLM Hash Listing Sent ***")
    while data != "":
        nthash = binascii.hexlify(data[:16])
        lmhash = binascii.hexlify(data[16:32])
        userlen = unpack("<I", data[32:36])[0]
        username = data[36:36 + userlen]
        chop.prnt("User Name: %s" % username)
        chop.prnt("LM Hash: %s" % lmhash)
        chop.prnt("NT Hash: %s" % nthash)
        chop.prnt("*" * 41)
        data = data[36 + userlen:]
    return

def wirelesspwlist(data, tcp):
    module_data = tcp.module_data
    if len(data) == 0:
        chop.tsprnt("*** Wireless Listing Request - Nothing Found ***")
        return
    chop.tsprnt("*** Wireless Listing Sent ***")
    if module_data['savelistings']:
        filename = "PI-wireless-listing-%d.txt" % module_data['filecount']
        module_data['filecount'] += 1
        chop.savefile(filename, data)
        chop.prnt("%s saved.." % filename)
    return

def analyzeCode(code, type, tcp=None):
    module_data = tcp.module_data
    if module_data['debug']:
        chop.tsprnt("code:\n%s" % hexdump(code))

    if type == 0x5c:
        #look for audio data parameters at the end of the code
        audioparams = code[-32:]
        chan = {1 : "Mono", 2: "Stereo"}
        # mono / 8 bits
        p = string.rfind(audioparams, "\x00\x00\x01\x00\x08\x00")

        # stereo / 8 bits
        if p == -1:
            p = string.rfind(audioparams, "\x00\x00\x02\x00\x08\x00")

        # mono / 16 bits
        if p == -1:
            p = string.rfind(audioparams, "\x00\x00\x01\x00\x10\x00")

        # stereo / 16 bits
        if p == -1:
            p = string.rfind(audioparams, "\x00\x00\x02\x00\x10\x00")

        if p != -1:
            p -= 2 # Back up 2 bytes
            try:
                (sample, channels, bits) = unpack("<IHH", audioparams[p:p + 8])
                chop.tsprnt("*** Audio Sample Settings ***")
                chop.prnt("Sample Rate: %0.3f kHz" % (sample / 1000.00))
                chop.prnt("Channels: %s" % chan[channels])
                chop.prnt("Bits: %d" % bits)
            except:
                pass
    elif type == 0x05:
        chop.tsprnt("*** File Search Initiated ***")

        #find start of data
        #look for function epilogue
        p = string.rfind(code, "\x8b\xe5\x5d\xc3")
        if p == -1:
            p = 10
        else:
            p += 4

        if code[p + ord(code[p])] == "\\":
            dirend = p + 1 + ord(code[p])
            dirstart = p + 1
        else:
            chop.prnt("Unable to find dirend and dirstart.")
            return

        chop.prnt("Search Directory: %s" % code[dirstart:dirend])

        p = dirend
        if code[p] == "\x00":
            p += 1
            type = "word in file"
            termend = p + 1 + ord(code[p])
            term = code[p+1:termend]
        else:
            type = "file name"
            termend = p + 1 + ord(code[p])
            term = code[p+1:termend]
            termend += 1

        options = ""
        if code[termend] == "\x01":
            options += "Include subdirectories\n"
        if code[termend+1] == "\x01":
            options += "Fuzzy matching (wildcards prepended and appended to search term)\n"
        if code[termend+2] == "\x01":
            options += "Case sensitive\n"
        else:
            options += "Case insensitive\n"

        chop.prnt("Search Term: %s" % term)
        chop.prnt("Search Type: %s" % type)
        chop.prnt("Options: %s" % options)
    elif type == 0x36:
        chop.tsprnt("*** Registry Search Initiated ***")
        #chop.prnt(hexdump(code))

        #find start of data
        #look for function epilogue
        p = string.rfind(code[:-11], "\x8b\xe5\x5d\xc3")
        if p == -1:
            p = 6
        p += 4
        if ord(code[p]) == 0:
            root = "HKEY_CLASSES_ROOT"
        elif ord(code[p]) == 1:
            root = "HKEY_CURRENT_USER"
        elif ord(code[p]) == 2:
            root = "HKEY_LOCAL_MACHINE"
        elif ord(code[p]) == 3:
            root = "HKEY_USERS"
        elif ord(code[p]) == 5:
            root = "HKEY_CURRENT_CONFIG"
        else:
            root = "??"
        p += 4

        if code[p + ord(code[p])] == "\\":
            keyend = p + 1 + ord(code[p])
            keystart = p + 1
        else:
            chop.prnt("unrecognizable format..")
            return

        key = code[keystart:keyend]
        p = keyend + 4

        termend = p + 1 + ord(code[p])
        term = code[p+1:termend]

        options = ""
        if code[termend] == "\x01":
            options += "Look at keys\n"
        if code[termend+1] == "\x01":
            options += "Look at values\n"
        if code[termend+3] == "\x01":
            options += "Look at REG_SZ data\n"
        if code[termend+4] == "\x01":
            options += "Look at REG_BINARY data\n"
        if code[termend+5] == "\x01":
            options += "Look at REG_DWORD data\n"
        if code[termend+6] == "\x01":
            options += "Look at REG_MULTI_SZ data\n"
        if code[termend+7] == "\x01":
            options += "Look at REG_EXPAND_SZ data\n"
        if code[termend+8] == "\x01":
            options += "Include subkeys\n"
        if code[termend+9] == "\x01":
            options += "Fuzzy matching (wildcards prepended and appended to search term)\n"
        if code[termend+10] == "\x01":
            options += "Case sensitive\n"
        else:
            options += "Case insensitive\n"

        chop.prnt("Search Root: %s" % root)
        chop.prnt("Search Key: %s" % key)
        chop.prnt("Search Term: %s" % term)
        chop.prnt("Options: %s" % options)

    elif type == 2:
        chop.tsprnt("*** Directory Listing Initiated ***")
        p = string.rfind(code, ":\\")
        if p == -1:
            chop.prnt("unrecognizable format..")
            return
        chop.prnt("Directory: %s" % code[p-1:])

    elif type == 0x1e:
        chop.tsprnt("*** Registry Listing Initiated ***")

        if string.rfind(code, "\x90\x90") == -1:
            if ord(code[10]) == 0:
                root = "HKEY_CLASSES_ROOT"
            elif ord(code[10]) == 1:
                root = "HKEY_CURRENT_USER"
            elif ord(code[10]) == 2:
                root = "HKEY_LOCAL_MACHINE"
            elif ord(code[10]) == 3:
                root = "HKEY_USERS"
            elif ord(code[10]) == 5:
                root = "HKEY_CURRENT_CONFIG"
            else:
                root = "??"
            reg = code[14:]
            chop.prnt("Root: %s" % root)
            chop.prnt("Registry Key: %s" % reg)
    elif type == 0x47 or type == 0x43:
        chop.tsprnt("*** Relay Service Started ***")
        if type == 0x43:
            type = "Socks4"
        else:
            type = "Socks5"

        #find start of data
        #look for function epilogue
        p = string.rfind(code, "\x8b\xe5\x5d\xc3")
        if p == -1:
            p = 10
        else:
            p += 4

        relayport = unpack("<H", code[p:p + 2])[0]
        p += 2
        user = ""
        pw = ""
        if ord(code[p]) == 1:
            p += 1
            userend = p + 1 + ord(code[p])
            user = code[p + 1:userend]
            pwend = userend + 1 + ord(code[userend])
            pw = code[userend + 1:pwend]
            srcipend = pwend + 1 + ord(code[pwend])
            srcip = code[pwend + 1:srcipend]
            dstipend = srcipend + 1 + ord(code[srcipend])
            dstip = code[srcipend + 1:dstipend]
            dstport = unpack("<H", code[dstipend:dstipend + 2])[0]

        elif ord(code[p]) != 0:
            userend = p + 1 + ord(code[p])
            user = code[p + 1:userend]
            srcipend = userend + 1 + ord(code[userend])
            srcip = code[userend + 1:srcipend]
            dstipend = srcipend + 1 + ord(code[srcipend])
            dstip = code[srcipend + 1:dstipend]
            dstport = unpack("<H", code[dstipend:dstipend + 2])[0]

        chop.prnt("Relay Type: %s" % type)
        chop.prnt("Relay Port: %d" % relayport)
        if user != "":
            chop.prnt("User: %s" % user)
            if pw != "":
                chop.prnt("Password: %s" % pw)
            chop.prnt("Source IP: %s" % srcip)
            chop.prnt("Destination IP: %s" % dstip)
            chop.prnt("Destination Port: %d" % dstport)
    elif type == 0x46:
        chop.tsprnt("*** Relay Service Stopped ***")
    elif type == 0x4c:
        chop.tsprnt("*** Gateway Service Started ***")
        #find start of data
        #look for function epilogue
        p = string.rfind(code, "\x8b\xe5\x5d\xc3")
        if p == -1:
            p = 10
        else:
            p += 4
        srcip = ""
        relayport = unpack("<H", code[p:p + 2])[0]
        p += 2
        dstipend = p + 1 + ord(code[p])
        dstip = code[p+1:dstipend]
        dstport = unpack("<H", code[dstipend:dstipend+2])[0]
        if ord(code[dstipend+2]) != 0:
            srcipend = dstipend + 3 + ord(code[dstipend+2])
            srcip = code[dstipend+3:srcipend]

        chop.prnt("Relay Port: %d" % relayport)
        if srcip != "":
            chop.prnt("Source IP: %s" % srcip)
        chop.prnt("Destination IP: %s" % dstip)
        chop.prnt("Destination Port: %d" % dstport)
    return

#returns listid and bool for new PI stream
def getHeaders(direction, buf, tcp):
    sd = tcp.stream_data
    md = tcp.module_data
    buf = CamelliaDecrypt(buf, md['camcrypt'], sd.get('xor', None))
    (type, listid) = unpack("<II", buf[0:8])
    newstream = False
    if md['debug']:
        chop.tsprnt("%s headers:\n%s" % (direction, hexdump(buf)))
    if direction == "in":
        if sd['inbound_type'].get(listid, -1) != type:
            newstream = True
        sd['inbound_type'][listid] = type
        (sd['inbound_chunk_size'][listid],
         sd['inbound_unpadded_chunk_size'][listid],
         sd['inbound_decompressed_chunk_size'][listid],
         sd['inbound_total_size'][listid]) = unpack("<IIIq", buf[8:28])
        if sd['client_collect_buffer'].get(listid) == None:
            sd['client_collect_buffer'][listid] = ""

    else:
        if sd['outbound_type'].get(listid, -1) != type:
            newstream = True
        sd['outbound_type'][listid] = type
        (sd['outbound_chunk_size'][listid],
         sd['outbound_unpadded_chunk_size'][listid],
         sd['outbound_decompressed_chunk_size'][listid],
         sd['outbound_total_size'][listid]) = unpack("<IIIq", buf[8:28])
        if sd['server_collect_buffer'].get(listid) == None:
            sd['server_collect_buffer'][listid] = ""

    return (listid, newstream)

def pad(buf):
    size = len(buf)
    next = size
    while next % 16 != 0:
        next += 1

    pad = next - size
    buf += "\x00" * pad

    return buf

def CamelliaEncrypt(buf, camobj, xor=None):
    out = ""
    for i in range(0, len(buf), 16):
        out += camobj.encrypt(buf[i:i+16])

    if xor is not None:
        out = one_byte_xor(out, xor)

    return out

def CamelliaDecrypt(buf, camobj, xor=None):
    out = ""
    if xor is not None:
        buf = one_byte_xor(buf, xor)

    for i in range(0, len(buf), 16):
        out += camobj.decrypt(buf[i:i+16])

    return out

def TryKeyList(keylist, challenge, response, camobj, xor=None):
    #just in case admin is not included in the list
    camobj.keygen(256, "admin" + "\x00" * 27)
    if response == CamelliaEncrypt(challenge, camobj, xor):
        chop.prnt("Key found: admin")
        return True

    with open(keylist, 'r') as f:
        for line in f:
            line = string.strip(line)
            key = line
            if key[:2] == "0x":
                key = binascii.unhexlify(key[2:])

            if len(key) > 32:
                continue

            #pad to 256 bits
            if len(key) < 32:
                key += "\x00" * (32 - len(key))
            camobj.keygen(256, key)
            if response == CamelliaEncrypt(challenge, camobj, xor):
                chop.prnt("Key found: %s" % line)
                return True

        return False

def init(module_data):
    module_options = { 'proto': 'tcp' }
    parser = OptionParser()
    parser.add_option("-f", "--save-files", action="store_true",
                      dest="savefiles", default=False, help="save transferred files")
    parser.add_option("-l", "--save-listings", action="store_true",
                      dest="savelistings", default=False, help="save reg/dir/proc/etc listings to files")
    parser.add_option("-c", "--save-captures", action="store_true",
                      dest="savecaptures", default=False, help="save screen/webcam/audio/key captures to files")
    parser.add_option("-v", "--verbose", action="store_true",
                      dest="verbose", default=False, help="verbosity")
    parser.add_option("-d", "--debug", action="store_true",
                      dest="debug", default=False, help="debug output")
    parser.add_option('-p', '--lib-path', dest='libpath', default="", help='the path to the required lib file (camellia.so)')
    parser.add_option('-w', '--password', dest='pw', default="admin", help='the password used to build the encryption key (optional, a default key will be used if not provided)')
    parser.add_option('-x', '--hex-pw', dest='asciihexpw', help='the hex-encoded password used to build the encryption key (with or without spaces)')
    parser.add_option('-t', '--try-pw-list', dest='pwlist', help='a file containing a line delimited list of passwords used to build the encryption key. each password will be tried during the challenge phase until the proper password is found or all passwords have been tried. ascii hex passwords should be prepended with \'0x\'')

    (opts, lo) = parser.parse_args(module_data['args'])

    module_data['cmdhandler'] = {0x27 : heartbeat,
                                 0x17 : shell,
                                 0x0b : dirlist,
                                 0x02 : dirlist,
                                 0x01 : hostinfo,
                                 0x1e : reglist,
                                 0x2b : servicelist,
                                 0x14 : proclist,
                                 0x68 : devicelist,
                                 0x53 : skip,
                                 0x44 : skip,
                                 0x2a : nofilesearchresults,
                                 0x05 : filesearchresults,
                                 0x1c : webcam,
                                 0x5c : audio,
                                 0x58 : installedlist,
                                 0x49 : keylog,
                                 0x19 : screenshot,
                                 0x39 : remotedesktop,
                                 0x3c : cachedpwlist,
                                 0x5b : ntlmhashlist,
                                 0x5a : wirelesspwlist,
                                 0x36 : regsearchresults,
                                 0x37 : noregsearchresults,
                                 0x0d : windowlist,
                                 0x38 : portlist}

    module_data['savefiles'] = opts.savefiles
    module_data['savelistings'] = opts.savelistings
    module_data['savecaptures'] = opts.savecaptures
    module_data['verbose'] = opts.verbose
    module_data['pwlist'] = opts.pwlist
    module_data['debug'] = opts.debug

    try:
        if opts.libpath != "":
            module_data['camcrypt'] = camcrypt.CamCrypt(opts.libpath)
        else:
            module_data['camcrypt'] = camcrypt.CamCrypt("camellia.so")
    except:
        module_options['error'] = "Couldn't locate camellia.so"
        return module_options

    if not module_data['pwlist']:
        if opts.asciihexpw:
            module_data['key'] = binascii.unhexlify(string.replace(opts.asciihexpw, " ", ""))
        else:
            module_data['key'] = opts.pw

        if len(module_data['key']) > 32:
            module_options['error'] = "Password must be 32 bytes long or less."
            return module_options
        elif len(module_data['key']) < 32:
            #pad key to 256 bits
            for i in range(32 - len(module_data['key'])):
                module_data['key']+="\x00"

        module_data['camcrypt'].keygen(256, module_data['key'])

    elif not os.path.exists(module_data['pwlist']):
        module_options['error'] = "Supplied password list does not exist.."
        return module_options

    module_data['filecount'] = 1
    return module_options

def handleStream(tcp):
    sd = tcp.stream_data
    md = tcp.module_data

    if tcp.client.count_new > 0:
        sd['client_buffer'] += tcp.client.data[:tcp.client.count_new]
        if sd['client_state'] == "challenged":
            if len(sd['client_buffer']) >= 256:
                challenge_resp = sd['client_buffer'][:256]
                sd['client_buffer'] = sd['client_buffer'][256:]
                if md['pwlist']:
                    if TryKeyList(md['pwlist'], sd['challenge'], challenge_resp, md['camcrypt']):
                        if md['verbose'] or md['debug']:
                            chop.tsprnt("PI challenge response accepted..")
                        sd['client_state'] = "challenge_accepted"
                        tcp.discard(tcp.client.count_new)
                        return
                if challenge_resp == CamelliaEncrypt(sd['challenge'], md['camcrypt']):
                    if md['verbose'] or md['debug']:
                        chop.tsprnt("PI challenge response accepted..")
                    sd['client_state'] = "challenge_accepted"
                    tcp.discard(tcp.client.count_new)
                    return
                else:
                    sd['client_state'] = "challenge_failed"
                    if md['verbose'] or md['debug']:
                        chop.tsprnt("PI challenge response not valid for supplied passwords(s), skipping stream..")
                    #sd['challenge_accepted'] = True
                    tcp.stop()
                    return

        if sd['client_state'] == "double_challenged":
            if len(sd['client_buffer']) >= 260:
                challenge_resp = sd['client_buffer'][:256]
                sd['client_buffer'] = sd['client_buffer'][256:]
                (a, b) = struct.unpack('>HH', tcp.client.data[:4])
                a ^= 0xd015
                if a != b:
                    sd['client_state'] = "challenge_failed"
                    if md['verbose'] or md['debug']:
                        chop.tsprnt("PI challenge not valid, skipping stream..")
                    tcp.stop()
                    return
                sd['xor'] = a & 0xFF
                chop.tsprnt("PI double nonce xor variant, xor key: %02X" % sd['xor'])
                if md['pwlist']:
                    if TryKeyList(md['pwlist'], sd['challenge'], challenge_resp, md['camcrypt'], sd['xor']):
                        if md['verbose'] or md['debug']:
                            chop.tsprnt("PI challenge response accepted..")
                        sd['client_state'] = "challenge_accepted"
                        tcp.discard(tcp.client.count_new)
                        return
                if challenge_resp == CamelliaEncrypt(one_byte_xor(sd['challenge'], sd['xor']), md['camcrypt'], sd['xor']):
                    if md['verbose'] or md['debug']:
                        chop.tsprnt("PI challenge response accepted..")
                    sd['client_state'] = "challenge_accepted"
                    tcp.discard(tcp.client.count_new)
                    return
                else:
                    sd['client_state'] = "challenge_failed"
                    if md['verbose'] or md['debug']:
                        chop.tsprnt("PI double challenge response not valid for supplied passwords(s), skipping stream..")
                    #sd['challenge_accepted'] = True
                    tcp.stop()
                    return

        if sd['client_state'] == "challenge_accepted":
            if len(sd['client_buffer']) >= 4:
                if 'xor' in sd:
                    sd['init_size'] = unpack("<I", one_byte_xor(sd['client_buffer'][:4], sd['xor']))[0]
                else:
                    sd['init_size'] = unpack("<I", sd['client_buffer'][:4])[0]
                sd['client_state'] = "init_code_collection"
                sd['client_buffer'] = sd['client_buffer'][4:]


        if sd['client_state'] == "init_code_collection":
            if sd['init_size'] <= len(sd['client_buffer']):
                sd['client_state'] = "init_code_collected"
                #decrypted = CamelliaDecrypt(sd['client_buffer'][:sd['init_size']], md['camcrypt'])
                if md['debug']:
                    chop.tsprnt("init code size: %08X" % sd['init_size'])
                sd['client_buffer'] = sd['client_buffer'][sd['init_size']:]

        if sd['client_state'] == "init_code_collected":
            if len(sd['client_buffer']) >= 4:
                if 'xor' in sd:
                    sd['version'] = unpack("<I", one_byte_xor(sd['client_buffer'][:4], sd['xor']))[0]
                else:
                    sd['version'] = unpack("<I", sd['client_buffer'][:4])[0]
                sd['client_buffer'] = sd['client_buffer'][4:]
                sd['client_state'] = "version_collected"
                chop.tsprnt("Poison Ivy Version: %0.2f" % (sd['version'] / 100.00))

        if sd['client_state'] == "version_collected":
            if len(sd['client_buffer']) >= 4:
                if 'xor' in sd:
                    sd['init_size'] = unpack("<I", one_byte_xor(sd['client_buffer'][:4], sd['xor']))[0]
                else:
                    sd['init_size'] = unpack("<I", sd['client_buffer'][:4])[0]
                sd['client_buffer'] = sd['client_buffer'][4:]
                sd['client_state'] = "stub_code_collection"
                if md['debug']:
                    chop.tsprnt("stub code size: %08X" % sd['init_size'])

        if sd['client_state'] == "stub_code_collection":
            if sd['init_size'] <= len(sd['client_buffer']):
                sd['client_state'] = "stub_code_collected"
                if md['debug']:
                    chop.tsprnt("stub code collected..")
                sd['client_buffer'] = sd['client_buffer'][sd['init_size']:]

        if sd['client_state'] == "stub_code_collected":
            #initialization complete
            if md['debug']:
                chop.tsprnt("init complete..")
            sd['client_state'] = "read_header"
            sd['server_state'] = "read_header"
            sd['server_buffer'] = ""


        if sd['client_state'] == "read_header":
            listid = sd['client_cur_listid']
            if len(sd['client_buffer']) >= 32:
                (sd['client_cur_listid'], newstream) = getHeaders("in", sd['client_buffer'][:32], tcp)
                listid = sd['client_cur_listid']
                sd['client_state'] = "recv_chunk"
                sd['client_buffer'] = sd['client_buffer'][32:]
                if newstream:
                    if sd['inbound_type'].get(listid) == 6:
                        #handle file data
                        decrypted = CamelliaDecrypt(sd['client_buffer'][:sd['inbound_chunk_size'].get(listid)], md['camcrypt'], sd.get('xor', None))
                        sd['client_buffer'] = sd['client_buffer'][sd['inbound_chunk_size'].get(listid):]
                        if sd['inbound_unpadded_chunk_size'].get(listid) != sd['inbound_decompressed_chunk_size'].get(listid):
                            buf = lznt1.dCompressBuf(decrypted[:sd['inbound_unpadded_chunk_size'].get(listid)])
                            if buf == None:
                                chop.tsprnt("decompression error:\n%s" % hexdump(decrypted))
                                tcp.stop()
                        else:
                            buf = decrypted[:sd['inbound_unpadded_chunk_size'].get(listid)]
                        #decompressed = lznt1.dCompressBuf(decrypted[:sd['inbound_unpadded_chunk_size']])
                        filename = string.strip(buf, "\x00")
                        sd['inbound_filename'][listid] = "PI-extracted-inbound-file-%d-%s" % (md['filecount'], filename[string.rfind(filename, "\\")+1:])
                        md['filecount'] += 1
                        chop.tsprnt("inbound file %s " % filename)

                        sd['client_state'] = "read_header"

                    sd['inbound_size_left'][listid] = sd['inbound_total_size'].get(listid)

            if sd['inbound_size_left'].get(listid) == 0:
                    sd['inbound_size_left'][listid] = sd['inbound_total_size'].get(listid)


        if sd['client_state'] == "recv_chunk":
            listid = sd['client_cur_listid']
            if sd['inbound_chunk_size'].get(listid) <= len(sd['client_buffer']):
                if md['debug']:
                    chop.tsprnt("handling inbound chunk.. %d bytes to go" % sd['inbound_size_left'].get(listid))
                sd['client_state'] = "read_header"
                decrypted = CamelliaDecrypt(sd['client_buffer'][:sd['inbound_chunk_size'].get(listid)], md['camcrypt'], sd.get('xor', None))
                decrypted = decrypted[:sd['inbound_unpadded_chunk_size'].get(listid)]
                buf = decrypted
                if sd['inbound_unpadded_chunk_size'].get(listid) != sd['inbound_decompressed_chunk_size'].get(listid):
                    buf = lznt1.dCompressBuf(decrypted)
                    if buf == None:
                        chop.tsprnt("decompression error:\n%s" % hexdump(decrypted))
                        tcp.stop()
                sd['client_collect_buffer'][listid] += buf
                sd['client_buffer'] = sd['client_buffer'][sd['inbound_chunk_size'].get(listid):]
                sd['inbound_size_left'][listid] -= sd['inbound_decompressed_chunk_size'].get(listid)
                if sd['inbound_type'].get(listid) == 6 and md['savefiles']:
                        #inbound file
                        chop.savefile(sd['inbound_filename'].get(listid), buf, False)

                if sd['inbound_size_left'].get(listid) == 0:
                    if sd['inbound_type'].get(listid) == 6:
                        if md['savefiles']:
                            #inbound file
                            chop.finalizefile(sd['inbound_filename'].get(listid))
                            chop.tsprnt("saved %s.." % sd['inbound_filename'].get(listid))
                    else:
                        analyzeCode(sd['client_collect_buffer'].get(listid), sd['inbound_type'].get(listid), tcp)
                        if md['debug']:
                            chop.tsprnt("analyzing code..")

                    sd['client_collect_buffer'][listid] = ""


        #chop.tsprnt("to client:%d" % tcp.client.count_new)
        tcp.discard(tcp.client.count_new)
        return

    elif tcp.server.count_new > 0:
        sd['server_buffer'] += tcp.server.data[:tcp.server.count_new]
        if sd['client_state'] == "unauthenticated":
            if len(sd['server_buffer']) >= 256:
                sd['client_state'] = "challenged"
                #chop.tsprnt(hexdump(tcp.server.data[:tcp.server.count_new]))
                sd['challenge'] = sd['server_buffer'][:256]
                sd['server_buffer'] = sd['server_buffer'][256:]
                #chop.tsprnt(hexdump(sd['challenge']))
        elif sd['client_state'] == "challenged":
            if len(sd['server_buffer']) >= 256:
                sd['client_state'] = "double_challenged"
                sd['challenge'] = sd['server_buffer'][:256]
                sd['server_buffer'] = sd['server_buffer'][256:]
        elif sd['client_state'] == "double_challenged":
            if md['verbose'] or md['debug']:
                chop.tsprnt("PI challenge not found, skipping stream..")
            tcp.stop()

        if sd['server_state'] == "read_header":
            listid = sd['server_cur_listid']
            if len(sd['server_buffer']) >= 32:
                (sd['server_cur_listid'], newstream) = getHeaders("out", sd['server_buffer'][:32], tcp)
                listid = sd['server_cur_listid']
                sd['server_state'] = "recv_chunk"
                sd['server_buffer'] = sd['server_buffer'][32:]
                if newstream:
                    if sd['outbound_type'].get(listid) == 4:
                        #handle file data
                        decrypted = CamelliaDecrypt(sd['server_buffer'][:sd['outbound_chunk_size'].get(listid)], md['camcrypt'], sd.get('xor', None))
                        if sd['outbound_unpadded_chunk_size'].get(listid) != sd['outbound_decompressed_chunk_size'].get(listid):
                            buf = lznt1.dCompressBuf(decrypted[:sd['outbound_unpadded_chunk_size'].get(listid)])
                            if buf == None:
                                chop.tsprnt("decompression error:\n%s" % hexdump(decrypted))
                                tcp.stop()
                        else:
                            buf = decrypted[:sd['outbound_unpadded_chunk_size'].get(listid)]

                        sd['server_buffer'] = sd['server_buffer'][sd['outbound_chunk_size'].get(listid):]
                        filename = string.strip(buf, "\x00")
                        sd['outbound_filename'][listid] = "PI-extracted-outbound-file-%d-%s" % (md['filecount'], filename[string.rfind(filename, "\\")+1:])
                        md['filecount'] += 1
                        chop.tsprnt("outbound file %s " % filename)

                        sd['server_state'] = "read_header"

                    sd['outbound_size_left'][listid] = sd['outbound_total_size'].get(listid)


                if sd['outbound_size_left'].get(listid) == 0:
                    sd['outbound_size_left'][listid] = sd['outbound_total_size'].get(listid)

        if sd['server_state'] == "recv_chunk":
            listid = sd['server_cur_listid']
            if sd['outbound_chunk_size'].get(listid) <= len(sd['server_buffer']):
                if md['debug']:
                    chop.tsprnt("handling outbound chunk.. %d bytes to go" % sd['outbound_size_left'].get(listid))
                sd['server_state'] = "read_header"
                decrypted = CamelliaDecrypt(sd['server_buffer'][:sd['outbound_chunk_size'].get(listid)], md['camcrypt'], sd.get('xor', None))
                decrypted = decrypted[:sd['outbound_unpadded_chunk_size'].get(listid)]
                buf = decrypted
                if sd['outbound_unpadded_chunk_size'].get(listid) != sd['outbound_decompressed_chunk_size'].get(listid):
                    buf = lznt1.dCompressBuf(decrypted)
                    if buf == None:
                        chop.tsprnt("decompression error:\n%s" % hexdump(decrypted))
                        tcp.stop()
                sd['server_collect_buffer'][listid] += buf
                sd['server_buffer'] = sd['server_buffer'][sd['outbound_chunk_size'].get(listid):]
                sd['outbound_size_left'][listid] -= sd['outbound_decompressed_chunk_size'].get(listid)
                if sd['outbound_type'].get(listid) == 4 and md['savefiles']:
                        #outbound file
                        chop.savefile(sd['outbound_filename'].get(listid), buf, False)

                if sd['outbound_size_left'].get(listid) == 0:
                    if sd['outbound_type'].get(listid) == 4:
                        if md['savefiles']:
                            #outbound file
                            chop.finalizefile(sd['outbound_filename'].get(listid))
                            chop.tsprnt("saved %s.." % sd['outbound_filename'].get(listid))
                    else:
                        if md['debug']:
                            chop.tsprnt("outbound data:\n%s" % hexdump(sd['server_collect_buffer'].get(listid)))

                        try:
                            md['cmdhandler'][sd['outbound_type'].get(listid)](sd['server_collect_buffer'].get(listid), tcp)
                        except:
                            if md['verbose'] or md['debug']:
                                chop.tsprnt("unrecognized command..")

                    sd['server_collect_buffer'][listid] = ""

        tcp.discard(tcp.server.count_new)
        return

    tcp.discard(tcp.server.count_new)
    return

def taste(tcp):
    tcp.stream_data['challenge'] = ''
    tcp.stream_data['version'] = 0
    tcp.stream_data['server_buffer'] = ''
    tcp.stream_data['client_buffer'] = ''
    tcp.stream_data['server_cur_listid'] = 0
    tcp.stream_data['client_cur_listid'] = 0
    tcp.stream_data['server_collect_buffer'] = {}
    tcp.stream_data['client_collect_buffer'] = {}
    tcp.stream_data['init_size'] = 0
    tcp.stream_data['inbound_type'] = {}
    tcp.stream_data['inbound_filename'] = {}
    tcp.stream_data['inbound_chunk_size'] = {}
    tcp.stream_data['inbound_total_size'] = {}
    tcp.stream_data['inbound_size_left'] = {}
    tcp.stream_data['inbound_unpadded_chunk_size'] = {}
    tcp.stream_data['inbound_decompressed_chunk_size'] = {}
    tcp.stream_data['outbound_type'] = {}
    tcp.stream_data['outbound_filename'] = {}
    tcp.stream_data['outbound_chunk_size'] = {}
    tcp.stream_data['outbound_total_size'] = {}
    tcp.stream_data['outbound_size_left'] = {}
    tcp.stream_data['outbound_unpadded_chunk_size'] = {}
    tcp.stream_data['outbound_decompressed_chunk_size'] = {}
    tcp.stream_data['client_state'] = "unauthenticated"
    tcp.stream_data['server_state'] = ""
    return True

def teardown(tcp):
    pass

def module_info():
    return "Poison Ivy 2.3.X network protocol decoder"

def shutdown(module_data):
    pass
########NEW FILE########
__FILENAME__ = shellcode_detector
# Copyright (c) 2014, Ankur Tyagi. All rights reserved.
# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


"""
A module to extract TCP streams and UDP datagrams from network traffic.
Extracted buffer is passed on to Libemu for shellcode detection.
"""

from optparse import OptionParser
from c2utils import hexdump

moduleName = 'shellcode_detector'
moduleVersion = '0.1'
minimumChopLib = '4.0'


def init(module_data):
    module_options = { 'proto': [{'tcp': ''}, {'udp': ''}] }

    module_data['emu'] = None
    module_data['cliargs'] = { 'shellprofile': False, 'hexdump': False }

    parse_args(module_data)

    try:
        import pylibemu
        module_data['emu'] = pylibemu.Emulator()
    except ImportError, e:
        module_options['error'] = str(e)

    return module_options


def parse_args(module_data):
    parser = OptionParser()

    parser.add_option("-p", "--profile", action="store_true", dest="shellprofile", default=False, help="Enable shellcode profile output")
    parser.add_option("-x", "--hexdump", action="store_true", dest="hexdump", default=False, help="Enable hexdump output")

    (options, lo) = parser.parse_args(module_data['args'])

    if options.shellprofile:
        module_data['cliargs']['shellprofile'] = True

    if options.hexdump:
        module_data['cliargs']['hexdump'] = True


def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr

    chop.tsprnt("TCP %s:%s - %s:%s [NEW]" % (src, sport, dst, dport))
    return True


def handleStream(tcp):
    ((src, sport), (dst, dport)) = tcp.addr

    direction = "NA"
    count = 0

    if tcp.server.count_new > 0:
        buffer = tcp.server.data[:tcp.server.count_new]
        server_count = tcp.server.count_new
        chop.tsprnt("TCP %s:%s -> %s:%s (CTS: %dB)" % (src, sport, dst, dport, server_count))
        tcp.discard(server_count)
        direction = "CTS"
        count = server_count
    else:
        buffer = tcp.client.data[:tcp.client.count_new]
        client_count = tcp.client.count_new
        chop.tsprnt("TCP %s:%s <- %s:%s (STC: %dB)" % (src, sport, dst, dport, client_count))
        tcp.discard(client_count)
        direction = "STC"
        count = client_count

    offset = tcp.module_data['emu'].shellcode_getpc_test(buffer)
    if offset >= 0:
        tcp.stop()
        tcp.module_data['emu'].prepare(buffer, offset)
        tcp.module_data['emu'].test()
        chop.tsprnt("TCP %s:%s - %s:%s contains shellcode in %s[0:%d] @ offset %d" % (src, sport, dst, dport, direction, count, offset))

        if tcp.module_data['cliargs']['hexdump']:
            data = hexdump(buffer[offset:])
            chop.prnt("\n" + data)

        if tcp.module_data['cliargs']['shellprofile']:
            buffer_profile = tcp.module_data['emu'].emu_profile_output
            chop.prnt("\n" + buffer_profile)

    tcp.module_data['emu'].free()


def teardown(tcp):
    ((src, sport), (dst, dport)) = tcp.addr

    chop.tsprnt("TCP %s:%s - %s:%s [CLOSE]" % (src, sport, dst, dport))

    return True


def handleDatagram(udp):
    ((src, sport), (dst, dport)) = udp.addr

    chop.tsprnt("UDP %s:%s - %s:%s (%dB)" % (src, sport, dst, dport, len(udp.data)))

    buffer = udp.data
    offset = udp.module_data['emu'].shellcode_getpc_test(buffer)
    if offset >= 0:
        udp.stop
        udp.module_data['emu'].prepare(buffer, offset)
        udp.module_data['emu'].test()
        chop.tsprnt("UDP %s:%s - %s:%s contains shellcode in [0:%d] @ offset %d" % (src, sport, dst, dport, len(udp.data), offset))

        if udp.module_data['cliargs']['hexdump']:
            data = hexdump(buffer[offset:])
            chop.prnt("\n" + data)

        if udp.module_data['cliargs']['shellprofile']:
            buffer_profile = udp.module_data['emu'].emu_profile_output
            chop.prnt("\n" + buffer_profile)

    udp.module_data['emu'].free()


def module_info():
    return "A module to detect presence of shellcode in network streams."


########NEW FILE########
__FILENAME__ = tcplot
moduleName="TCPlot"

import sys
import struct
import time
import datetime
import math
import numpy as np
import matplotlib.pyplot as plt
import pickle
from optparse import OptionParser

def parse_args(module_data):
    parser = OptionParser()

    parser.add_option("-d", "--dump", action="store_true",
        dest="dump", default=False, help="Dump traffic summary to text file")
    parser.add_option("-o", "--output", action="store_true",
        dest="output", default=False, help="Print traffic to stdout")
    parser.add_option("-u", "--unified", action="store_true",
        dest="unified", default=False, help="Create a pickled pyplot representing the traffic data as one series")
    parser.add_option("-c", "--comparison", action="store_true",
        dest="comparison", default=False, help="Create a pickled pyplot representing the traffic data in distinct series for client and server.")
    parser.add_option("-n", "--nolines", action="store_true",
        dest="nolines", default=False, help="When creating plots, do not use lines")
    parser.add_option("-l", "--hyphenlines", action="store_true",
        dest="dashedlines", default=False, help="When creating plots, use dashes for lines")
    parser.add_option("-a", "--absolute", action="store_true",
        dest="absolute", default=False, help="When creating comparison plot,represent both client and server using positive byte counts")
        
    (opts,lo) = parser.parse_args(module_data['args'])

    module_data['dump'] = opts.dump
    module_data['output'] = opts.output
    module_data['unified'] = opts.unified
    module_data['comparison'] = opts.comparison
    module_data['absolute'] = opts.absolute
    module_data['nolines'] = opts.nolines
    module_data['dashedlines'] = opts.dashedlines and not module_data['nolines']
    module_data['plot'] = module_data['unified'] or module_data['comparison']

def init(module_data):
    module_options = {'proto':'tcp'}
    parse_args(module_data)
    module_data['bytes'] = {}
    module_data['timestamps'] = {}
    return module_options
    
def module_info():
    return "Parse input into scatter plots of TCP traffic, separated by stream."

def handleStream(tcp):
    if tcp.server.count_new > 0:
        count = tcp.server.count_new
        from_client = True
        color = "RED"
    else:
        count = tcp.client.count_new
        from_client = False
        color = "GREEN"
        
    if not tcp.stream_data['start']:
        tcp.stream_data['start'] = datetime.datetime.utcfromtimestamp(tcp.timestamp)
    time_since_start = datetime.datetime.utcfromtimestamp(tcp.timestamp) - tcp.stream_data['start']
    
    if tcp.module_data['dump']: # dump info to text file
        path = tcp.stream_data['file']
        chop.appendfile("%s.txt" % path, "(%s%i, %.9f)\n" % ("" if from_client else "-", count, time_since_start.total_seconds()))
    
    if tcp.module_data["output"]: # dump to stdout or gui out
        chop.prettyprnt(color, "(%i, %.9f)" % (count, time_since_start.total_seconds()))
    
    if tcp.module_data['plot']: # create plot
        if not tcp.module_data['bytes'].get(tcp.stream_data['file']):
            tcp.module_data['bytes'][tcp.stream_data['file']] = []
            tcp.module_data['timestamps'][tcp.stream_data['file']] = []
        tcp.module_data['bytes'][tcp.stream_data['file']].append(count if from_client else -count)
        tcp.module_data['timestamps'][tcp.stream_data['file']].append(time_since_start.total_seconds())

def taste(tcp):
    ((src, sport), (dst, dport)) = tcp.addr
    tcp.stream_data['file'] = "%s_to_%s_%i" % (src, dst, len(tcp.module_data['bytes']))
    tcp.stream_data['start'] = ''
    return True

def teardown(tcp):
    return
    
def shutdown(module_data):
    if module_data['plot']:
        for key in module_data['bytes']:
            if module_data['unified']:
                dump_unified(key, module_data)
            if module_data['comparison']:
                dump_comparison(key, module_data)
    return
    
def dump_unified(key, module_data):
    tstmps = module_data['timestamps'].get(key)
    byte_arr = module_data['bytes'].get(key)
            
    x = np.linspace(0, tstmps[len(tstmps) - 1])

    ax = plt.subplot(111)
    plt.plot(tstmps, byte_arr, get_linestyle(True, module_data['nolines'], module_data['dashedlines'], True), marker=".")
    plt.ylabel("Bytes Sent (- = from server, + = from client)")
    plt.xlabel("Seconds Elapsed")
    plt.grid(True)
    pickle.dump(ax, file("%s_unified.pickle" % key, 'w'))
    plt.clf()
    
def dump_comparison(key, module_data):
    tstmps = module_data['timestamps'].get(key)
    byte_arr = module_data['bytes'].get(key)
    
    client_byte_arr = []
    client_tsmpt_arr = []
    server_byte_arr = []
    server_tsmpt_arr = []
    for (counter, item) in enumerate(byte_arr):
        if item > 0:
            client_byte_arr.append(item)
            client_tsmpt_arr.append(tstmps[counter])
        else:
            server_byte_arr.append(abs(item) if module_data['absolute'] else item)
            server_tsmpt_arr.append(tstmps[counter])
            
    x = np.linspace(0, tstmps[len(tstmps) - 1])

    ax = plt.subplot(111)
    plt.plot(client_tsmpt_arr, client_byte_arr, get_linestyle(True, module_data['nolines'], module_data['dashedlines']), label="Client", marker=".")
    plt.plot(server_tsmpt_arr, server_byte_arr, get_linestyle(False, module_data['nolines'], module_data['dashedlines']), label="Server", marker=".")
    ax.legend()
    plt.ylabel("Bytes Sent = abs(y)")
    plt.xlabel("Seconds Elapsed")
    plt.grid(True)
    
    pickle.dump(ax, file("%s_comparison.pickle" % key, 'w'))
    plt.clf()
    
def get_linestyle(primary, nolines, dashlines, unified=False):
    color = "b" if unified else "g" if primary else "r"
    return "%s%s%s" % ("--" if dashlines else "", color, "o" if nolines or dashlines else "")

def load_plot(file_path):
    """
    Load the pickled plot at the given path. Example of how to open pickle files created by this module
    """
    ax = pickle.load(file(file_path))
    plt.show()
########NEW FILE########
__FILENAME__ = yarashop
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

"""
A module to scan TCP session data with Yara.

Usage: yarashop ...
"""

import argparse

from c2utils import parse_addr, hexdump
import chopring
import yaraprocessor

moduleName = "yarashop"


def module_info():
    return "Process TCP session payloads with Yara."


def init(module_data):
    """Initialize chopshop module."""
    module_options = {'proto': 'tcp'}
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-r', '--rules',
        nargs='+',
        type=str,
        help='One or more rule files to load into Yara, \
              seperated by spaces.')

    parser.add_argument(
        '-m', '--mode',
        default='session',
        choices=['session', 'packet', 'fixed_buffer', 'sliding_window'],
        help='Analyze entire sessions, individual packets, \
              or size based buffers of data with Yara. If analyzing \
              buffers, see "--size" option.')

    parser.add_argument(
        '-s', '--size',
        type=int,
        default=100,
        help='The size of the data buffer in bytes to be passed \
              to yara for analysis.')

    parser.add_argument(
        '-i', '--step',
        type=int,
        default=100,
        help='Amount to increment the window.')

    parser.add_argument(
        '-S', '--save',
        type=str,
        default='',
        help='If Yara matches are found, save the stream to file.')

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        default=False,
        help='Print all information.')

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        dest='quiet',
        default=False,
        help='Supress printing matches.')

    args = parser.parse_args(module_data['args'])

    module_data['rules'] = args.rules
    module_data['mode'] = args.mode
    module_data['size'] = args.size
    module_data['step'] = args.step
    module_data['save'] = args.save
    module_data['verbose'] = args.verbose
    module_data['quiet'] = args.quiet

    return module_options


def taste(tcp):
    """Called at the start of each new session."""
    # Analyzing all sessions in a capture
    ((src, sport), (dst, dport)) = tcp.addr
    if tcp.module_data['verbose']:
        chop.tsprnt("Start Session %s:%s -> %s:%s" % (src, sport, dst, dport))

    # Session and packet modes map to a raw processor
    if tcp.module_data['mode'] == 'session' or tcp.module_data['mode'] == 'packet':
        server_processor = yaraprocessor.Processor(tcp.module_data['rules'],
                                                    processing_mode='raw',
                                                    buffer_size=tcp.module_data['size'],
                                                    window_step=tcp.module_data['step'])

        client_processor = yaraprocessor.Processor(tcp.module_data['rules'],
                                                    processing_mode='raw',
                                                    buffer_size=tcp.module_data['size'],
                                                    window_step=tcp.module_data['step'])

    # Otherwise we should be able to use what is in 'mode'
    else:
        server_processor = yaraprocessor.Processor(tcp.module_data['rules'],
                                                    processing_mode=tcp.module_data['mode'],
                                                    buffer_size=tcp.module_data['size'],
                                                    window_step=tcp.module_data['step'])

        client_processor = yaraprocessor.Processor(tcp.module_data['rules'],
                                                    processing_mode=tcp.module_data['mode'],
                                                    buffer_size=tcp.module_data['size'],
                                                    window_step=tcp.module_data['step'])

    # Two processors, two lists for results, and two buffers
    tcp.stream_data['server_processor'] = server_processor
    tcp.stream_data['client_processor'] = client_processor
    tcp.stream_data['server_results'] = []
    tcp.stream_data['client_results'] = []
    tcp.stream_data['server_buffer'] = chopring.chopring()
    tcp.stream_data['client_buffer'] = chopring.chopring()

    return True


def handleStream(tcp):
    """
    Analyze payloads with Yara.

    handleStream behaves differently based upon processing mode.
    If mode is set to 'packet', each packet's payload is individually analyzed
    with yara. If mode is set to 'fixed_buffer' or 'sliding_window', packet
    payloads are appended to the analysis buffer. The 'session' mode is not
    handled inside of handleStream.

    """
    ((src, sport), (dst, dport)) = parse_addr(tcp)

    # Check for new packets received by the server
    if tcp.server.count_new:
        tcp.stream_data['server_buffer'] += tcp.server.data[:tcp.server.count_new]

        if tcp.module_data['verbose']:
            chop.tsprettyprnt("RED", "%s:%s -> %s:%s %i bytes" %
                              (src, sport, dst, dport, tcp.server.count_new))

        if tcp.module_data['mode'] == 'packet':
            tcp.stream_data['server_processor'].data = tcp.server.data[:tcp.server.count_new]
            results = tcp.stream_data['server_processor'].analyze()
            tcp.stream_data['server_results'] += results

        elif tcp.module_data['mode'] in ['fixed_buffer', 'sliding_window']:
            tcp.stream_data['server_processor'].data += tcp.server.data[:tcp.server.count_new]

    # Check for new packets received by the client
    if tcp.client.count_new:
        tcp.stream_data['client_buffer'] += tcp.client.data[:tcp.client.count_new]

        if tcp.module_data['verbose']:
            chop.tsprettyprnt("RED", "%s:%s -> %s:%s %i bytes" %
                              (dst, dport, src, sport, tcp.client.count_new))

        if tcp.module_data['mode'] == 'packet':
            tcp.stream_data['client_processor'].data = tcp.client.data[:tcp.client.count_new]
            results = tcp.stream_data['client_processor'].analyze()
            tcp.stream_data['client_results'] += results

        elif tcp.module_data['mode'] in ['fixed_buffer', 'sliding_window']:
            tcp.stream_data['client_processor'].data += tcp.client.data[:tcp.client.count_new]

    # if we are analyzing whole sessions, discard 0 bytes
    if tcp.module_data['mode'] == 'session':
        tcp.discard(0)

    # Handle printing and optionally saving results to file
    handle_results(tcp)


def shutdown(module_data):
    """Called upon chopshop shutdown."""
    return


def teardown(tcp):
    """Called at the end of each network session."""
    ((src, sport), (dst, dport)) = tcp.addr

    if tcp.module_data['mode'] == 'session':
        tcp.stream_data['server_processor'].data = tcp.server.data
        tcp.stream_data['server_results'] = tcp.stream_data['server_processor'].analyze()

        tcp.stream_data['client_processor'].data = tcp.client.data
        tcp.stream_data['client_results'] = tcp.stream_data['client_processor'].analyze()

        # Handle printing and optionally saving results to file
        handle_results(tcp)

    else:
        tcp.stream_data['server_results'] = tcp.stream_data['server_processor'].results
        tcp.stream_data['client_results'] = tcp.stream_data['client_processor'].results


def handle_results(tcp):
    """Print and save results."""
    ((src, sport), (dst, dport)) = parse_addr(tcp)
    # print results
    for match in tcp.stream_data['server_processor'].results:
        if not module_data['quiet']:
            chop.tsprnt('Stream: Match found; %s:%s --> %s:%s' % (src, sport, dst, dport))
            chop.prnt(match)

        # Save results
        if tcp.module_data['save']:
            output = 'Match found in server stream; src=%s; sport=%s; dst=%s; dport=%s\n' \
                      % (src, sport, dst, dport)
            output += str(match) + '\n\n'
            output += hexdump(tcp.stream_data['server_buffer']) + '\n'
            chop.appendfile(tcp.module_data['save'], output)

        chop.json(match)
    tcp.stream_data['server_processor'].clear_results()

    # print results
    for match in tcp.stream_data['client_processor'].results:
        if not module_data['quiet']:
            chop.tsprnt('Stream: Match found; %s:%s --> %s:%s' % (dst, dport, src, sport))
            chop.tsprnt(match)

        # Save results
        if tcp.module_data['save']:
            output = 'Match found in client stream; src=%s; sport=%s; dst=%s; dport=%s\n' \
                      % (dst, dport, src, sport)
            output += str(match) + '\n\n'
            output += hexdump(tcp.stream_data['client_buffer']) + '\n'
            chop.appendfile(tcp.module_data['save'], output)

        chop.json(match)
    tcp.stream_data['client_processor'].clear_results()

########NEW FILE########
__FILENAME__ = ChopConfig
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


import ConfigParser
import sys
import os

from pprint import pformat

from ChopException import ChopConfigException

CHOPSHOP_WD = os.path.realpath(os.path.dirname(sys.argv[0]))

if CHOPSHOP_WD + '/shop' not in sys.path:
    sys.path.append(CHOPSHOP_WD + '/shop')

"""
    ChopConfig handles parsing configuration options which can be leveraged by
    different parts of ChopShop.
"""

DEFAULT_MODULE_DIRECTORY = CHOPSHOP_WD + '/modules/'
DEFAULT_EXTLIB_DIRECTORY = CHOPSHOP_WD + '/ext_libs/'

class ChopOption(object):
    def __init__(self, type, parent = None, default = None):
        self.type = type
        self.parent = parent
        self.value = default 

class ChopConfig(object):


    def __init__(self):
        self.options = {
                            #Config related options
                            'configfile' :  ChopOption('string'),
                            'saveconfig' :  ChopOption('string'),

                            #ChopLib options
                            'mod_dir' :     ChopOption('list', 'Directories'),
                            'ext_dir' :     ChopOption('list', 'Directories'),
                            'base_dir' :    ChopOption('list', 'Directories'), 
                            'filename' :    ChopOption('string', 'General'),
                            'filelist' :    ChopOption('string', 'General'),
                            'bpf' :         ChopOption('string', 'General'),
                            'aslist' :      ChopOption('bool', 'General'),
                            'longrun' :     ChopOption('bool', 'General'),
                            'interface' :   ChopOption('string', 'General'),
                            'modinfo' :     ChopOption('bool', 'General'),
                            'modtree' :     ChopOption('bool', 'General'),
                            'GMT' :         ChopOption('bool', 'General'),
                            'text' :        ChopOption('bool', 'General'),
                            'modules' :     ChopOption('string', 'General'),

                            #Shared options
                            'savedir' :     ChopOption('string', 'Directories'),
                            'jsonout' :     ChopOption('string', 'General'),
                            'pyobjout' :    ChopOption('bool', 'General'),

                            #UI options
                            'stdout' :      ChopOption('bool', 'General'),
                            'gui' :         ChopOption('bool', 'General'),
                            'fileout' :     ChopOption('string', 'General'),
                            'host' :        ChopOption('string', 'General'),
                            'port' :        ChopOption('int', 'General'),
                       }

    @property
    def configfile(self):
        return self.options['configfile'].value

    @configfile.setter
    def configfile(self, v):
        self.options['configfile'].value = v

    @property
    def mod_dir(self):
        """Directory to load modules from."""
        return self.options['mod_dir'].value

    @mod_dir.setter
    def mod_dir(self, v):
        self.options['mod_dir'].value = v

    @property
    def ext_dir(self):
        """Directory to load external libraries from."""
        return self.options['ext_dir'].value

    @ext_dir.setter
    def ext_dir(self, v):
        self.options['ext_dir'].value = v

    @property
    def base_dir(self):
        """Base directory to load modules and external libraries."""
        return self.options['base_dir'].value

    @base_dir.setter
    def base_dir(self, v):
        self.options['base_dir'].value = v

    @property
    def filename(self):
        """input pcap file."""
        return self.options['filename'].value

    @filename.setter
    def filename(self, v):
        self.options['filename'].value = v

    @property
    def filelist(self):
        """list of files to process"""
        return self.options['filelist'].value

    @filelist.setter
    def filelist(self, v):
        self.options['filelist'].value = v

    @property
    def aslist(self):
        """Treat filename as a file containing a list of files."""
        return self.options['aslist'].value

    @aslist.setter
    def aslist(self, v):
        self.options['aslist'].value = v

    @property
    def longrun(self):
        """Read from filename forever even if there's no more pcap data."""
        return self.options['longrun'].value

    @longrun.setter
    def longrun(self, v):
        self.options['longrun'].value = v

    @property
    def interface(self):
        """interface to listen on."""
        return self.options['interface'].value

    @interface.setter
    def interface(self, v):
        self.options['interface'].value = v

    @property
    def modinfo(self):
        """print information about module(s) and exit."""
        return self.options['modinfo'].value

    @modinfo.setter
    def modinfo(self, v):
        self.options['modinfo'].value = v

    @property
    def modtree(self):
        """print information about module tree and exit."""
        return self.options['modtree'].value

    @modtree.setter
    def modtree(self, v):
        self.options['modtree'].value = v

    @property
    def GMT(self):
        """timestamps in GMT (tsprnt and tsprettyprnt only)."""
        return self.options['GMT'].value

    @GMT.setter
    def GMT(self, v):
        self.options['GMT'].value = v

    @property
    def text(self):
        """Handle text/printable output. """
        return self.options['text'].value

    @text.setter
    def text(self, v):
        self.options['text'].value = v

    @property
    def pyobjout(self):
        """Handle raw python objects"""
        return self.options['pyobjout'].value

    @pyobjout.setter
    def pyobjout(self, v):
        self.options['pyobjout'].value = v

    @property
    def jsonout(self):
        """Handle JSON Data (chop.json)."""
        return self.options['jsonout'].value

    @jsonout.setter
    def jsonout(self, v):
        self.options['jsonout'].value = v

    @property
    def savedir(self):
        """Location to save carved files."""
        return self.options['savedir'].value

    @savedir.setter
    def savedir(self, v):
        self.options['savedir'].value = v

    @property
    def modules(self):
        """String of Modules to execute"""
        return self.options['modules'].value

    @modules.setter
    def modules(self, v):
        self.options['modules'].value = v

    @property
    def bpf(self):
        """BPF string to pass to Nids"""
        return self.options['bpf'].value

    @bpf.setter
    def bpf(self, v):
        self.options['bpf'].value = v

    @property
    def stdout(self):
        return self.options['stdout'].value

    @stdout.setter
    def stdout(self, v):
        self.options['stdout'].value = v

    @property
    def gui(self):
        return self.options['gui'].value

    @gui.setter
    def gui(self, v):
        self.options['gui'].value = v

    @property
    def fileout(self):
        return self.options['fileout'].value

    @fileout.setter
    def fileout(self, v):
        self.options['fileout'].value = v

    @property
    def host(self):
        return self.options['host'].value

    @host.setter
    def host(self, v):
        self.options['host'].value = v

    @property
    def port(self):
        return self.options['port'].value

    @port.setter
    def port(self, v):
        self.options['port'].value = v


    def __str__(self):
        flat  = {}
        for key in self.options.keys():
            flat[key] = self.options[key].value
        return pformat(flat)


    def parse_opts(self, options, args=[]):
        global CHOPSHOP_WD
        global DEFAULT_MODULE_DIRECTORY
        global DEFAULT_EXTLIB_DIRECTORY

        #Parse config file first
        if options.configfile:
            self.parse_config(options.configfile)

        #Commandline options should override config file options
        for opt, val in options.__dict__.items():
            if opt in self.options and val is not None:
                self.options[opt].value = val
        
        if self.base_dir is not None and CHOPSHOP_WD not in self.base_dir:
            self.base_dir.append(CHOPSHOP_WD)

        if self.mod_dir is not None and DEFAULT_MODULE_DIRECTORY not in self.mod_dir:
            self.mod_dir.append(DEFAULT_MODULE_DIRECTORY)
        elif self.base_dir is None and self.mod_dir is None:
            self.mod_dir = [DEFAULT_MODULE_DIRECTORY]

        if self.ext_dir is not None and DEFAULT_EXTLIB_DIRECTORY not in self.ext_dir:
            self.ext_dir.append(DEFAULT_EXTLIB_DIRECTORY)
        elif self.base_dir is None and self.ext_dir is None:
            self.ext_dir = [DEFAULT_EXTLIB_DIRECTORY]

        if len(args) <= 0 and not options.configfile and not options.saveconfig:
            raise ChopConfigException("Module List Required")
        elif len(args) == 1:
            self.modules = args[0]
        elif len(args) > 1:
            if len(args[0]) > 0 and args[0] != 'None':
                self.bpf = args[0]

            if args[1] == 'None':
                raise ChopConfigException("module list required")
            elif len(args[1]) > 0:
                self.modules = args[1]

        return


    def parse_config(self, configfile):
        if not os.path.exists(configfile):
            raise ChopConfigException("could not find configuration file: %s" % configfile)
        cfg = ConfigParser.ConfigParser()        
        cfg.read(configfile)
        cfg.optionxform = str

        for opts in self.options.keys():
            try:
                if self.options[opts].parent is None:
                    continue

                if self.options[opts].type == "bool":
                    self.options[opts].value = cfg.getboolean(self.options[opts].parent, opts)
                elif self.options[opts].type == "list":
                    self.options[opts].value = cfg.get(self.options[opts].parent, opts).split(',')
                else: #assume string for now
                    self.options[opts].value = cfg.get(self.options[opts].parent, opts)
            except:
                pass
    
        return


    def save_config(self, filepath):
        try:
            fp = open(filepath, 'w')
            cfg = ConfigParser.ConfigParser()
            cfg.optionxform = str

            cfg.add_section('Directories')
            cfg.add_section('General')

            for opts in self.options.keys():
                if self.options[opts].value is not None and self.options[opts].parent is not None:
                    if self.options[opts].type == "list":
                        cfg.set(self.options[opts].parent, opts, ','.join(self.options[opts].value))
                    else:
                        cfg.set(self.options[opts].parent, opts, self.options[opts].value)

            cfg.write(fp)
            fp.close()
        except IOError, e:
            raise ChopConfigException(e)
        return

########NEW FILE########
__FILENAME__ = ChopException
#! /usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

class ChopException(BaseException):
    def __init__(self, value = ""):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ChopConfigException(ChopException):
    pass


class ChopUiException(ChopException):
    pass

class ChopUiStdOutException(ChopUiException):
    pass

class ChopUiGuiException(ChopUiException):
    pass

class ChopUiFileOutException(ChopUiException):
    pass

class ChopUiJsonException(ChopUiException):
    pass

class ChopUiFileSaveException(ChopUiException):
    pass

class ChopUiPyObjException(ChopUiException):
    pass

class ChopLibException(ChopException):
    pass

########NEW FILE########
__FILENAME__ = ChopGrammar
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


import sys
import os
import imp
import traceback
import time
from threading import Thread, Lock
import re
from cStringIO import StringIO

CHOPSHOP_WD = os.path.realpath(os.path.dirname(sys.argv[0]))

if CHOPSHOP_WD + '/shop' not in sys.path: 
    sys.path.append(CHOPSHOP_WD + '/shop')

from ChopException import ChopLibException


#Grammar:
#Chains = Chain [SEMICOLON Chain]*
#Chain = [Invocation | Tee] [PIPE [Invocation | Tee]]*
#Invocation = STRING [OPTION [QUOTED | STRING]?]* [QUOTED | STRING]?
#Tee = BTEE Chain [COMMA Chain]+ ETEE

class __ChopModule__:
    def __init__(self, mstr):
        self.children = []
        self.parents = []
        self.name = mstr
        self.arguments = []
        self.legacy = False
        self.inputs = {}
        self.outputs = []


class ChopGrammar:

    #TODO Add support for escaped sequences?
    scanner=re.Scanner([
        (r'"((?:[^\t\n\r\f\v"])*)"',               lambda scanner, token:("QUOTED", token)),
        (r"'((?:[^\t\n\r\f\v'])*)'",               lambda scanner, token:("QUOTED", token)),
        (r"[ ]",                                lambda scanner, token:("SPACE", token)),
        (r"\;",                                 lambda scanner, token:("SEMICOLON", token)),
        (r"\(",                                 lambda scanner, token:("BTEE", token)),
        (r"\)",                                 lambda scanner, token:("ETEE", token)),
        (r"\|",                                 lambda scanner, token:("PIPE", token)),
        (r"\,",                                 lambda scanner, token:("COMMA", token)),
        (r"[^\t\n\r\f\v'\";()|,-][^ \t\n\r\f\v'\";()|,]*",
                                                lambda scanner, token:("STRING", token)),
        (r"--[a-zA-Z0-9_-]+",                   lambda scanner, token:("OPTION", token)),
        (r"-[a-zA-Z0-9]+",                      lambda scanner, token:("OPTION", token)),
        (r"-",                                  lambda scanner, token:("STRING", token)),
    ])


    def __init__(self):
        self.top_modules = []
        self.all_modules = []
        self.strbuff = None

    def parseGrammar(self, grammar_string):
        results, remainder = self.scanner.scan(grammar_string)

        if remainder:
            return (None, None)

        nresults = []
        for token in results:
            if token[0] != "SPACE":
                nresults.append(token)
        results = nresults

        self.verify_chains(results)

        return self.all_modules


    def find_tee_end(self, chain, left):
        btee_stack = [True]
        #Assume left is the position of BTEE
        right = left + 1
        while right < len(chain):
            if chain[right][0] == "BTEE":
                btee_stack.append(True)
            elif chain[right][0] == "ETEE":
                if not len(btee_stack): #there's no cooresponding BTEE
                    raise Exception("Unexpected End Tee token ')'")
                    #return left #error
                if len(btee_stack) == 1: #this is the ETEE we're looking for
                    return right
                btee_stack.pop()
            right += 1
        raise Exception("Unable to find end of Tee")
        #return left #error
            


    def verify_chains(self, chains):
        left = 0
        right= 0
        flows = []

        #get chain
        #pdb.set_trace()
        while right < len(chains):
            while right < len(chains) and chains[right][0] != "SEMICOLON":
                right += 1
            chain = chains[left:right]
            right += 1
            left = right
            (ancestors, children) = self.verify_chain(chain)
            flows.extend(ancestors)

        self.top_modules = flows
        return True
            
    def verify_chain(self, chain):
        left = 0
        right= 0

        ancestors = []
        parents = []
        
        #get chain

        while right < len(chain):
            while right < len(chain) and (chain[right][0] != "PIPE" and chain[right][0] != "BTEE"):
                right += 1

            if right >= len(chain) or chain[right][0] == "PIPE": #Assume Invocation
                invocation = chain[left:right]
                mod = self.verify_invocation(invocation)
                if len(parents) == 0:
                    parents.append(mod)
                    ancestors.append(mod)
                else:
                    for parent in parents:
                        parent.children.append(mod)
                        mod.parents.append(parent)
                    parents = [mod]

            elif chain[right][0] == "BTEE": #Must find end of TEE
                if left != right:
                    raise Exception("Unexpected Tee")
                #left = right
                right = self.find_tee_end(chain, left)
                tee = chain[left + 1: right] #Remove the TEE elements
                
                if (right + 1) < len(chain): #There's more tokens after the end of the tee
                    if chain[right + 1][0] != "PIPE":
                        raise Exception('Unexpected token after TEE', chain[right + 1][0])
                    else:
                        right += 1
                (tparents, tchildren) = self.verify_tee(tee)
                if len(parents) == 0:
                    parents = tchildren
                    ancestors = tparents
                else:
                    for parent in parents:
                        for tparent in tparents:
                            parent.children.append(tparent)
                            tparent.parents.append(parent)
                    parents = tchildren
        
            right += 1
            left = right

        #return True
        return (ancestors,parents)

    def verify_tee(self, tee):
        left = 0
        right = 0
        comma = False

        parents = []
        children = []

        while right < len(tee):
            while right < len(tee) and (tee[right][0] != "COMMA" and tee[right][0] != "BTEE"):
                right += 1

            if right >= len(tee) or tee[right][0] == "COMMA": #Element of TEE, i.e., a chain
                if right < len(tee) and tee[right][0] == 'COMMA':
                    comma = True
                chain = tee[left:right]
                (cparents, cchildren) = self.verify_chain(chain)
                for cparent in cparents:
                    parents.append(cparent)
                for cchild in cchildren:
                    children.append(cchild)

            elif tee[right][0] == "BTEE": #TEE in the Chain, need to skip it to find the comma
                right = self.find_tee_end(tee,right)
                continue

            right += 1
            left = right

        if not comma:
            raise Exception('Usage of a Tee requires at least two elements')

        return (parents, children)
            

    def verify_invocation(self, invocation):
        right = 1
        if invocation[0][0] != "STRING":
            raise Exception("Invocation must begin with a 'STRING' token, not a %s token" % invocation[0][0])

        mymod = __ChopModule__(invocation[0][1].rstrip())

        while right < len(invocation):
            if invocation[right][0] == "OPTION":
                mymod.arguments.append(invocation[right][1].rstrip())
                if (right + 1) < len(invocation): #Check if the next element is the argument to the option
                    if invocation[right + 1][0] == "QUOTED":
                        #Need to strip the quotes
                        mymod.arguments.append(invocation[right + 1][1].rstrip()[1:-1])
                        right += 1 #skip the parameter
                    elif invocation[right + 1][0] == "STRING":
                        mymod.arguments.append(invocation[right + 1][1].rstrip())
                        right += 1 #skip the parameter
                    #If not, just skip it and let it be parsed out
            elif (invocation[right][0] == "QUOTED"):
                if (right + 1) < len(invocation):
                    raise Exception("QUOTED token must be last element of invocation or following a OPTION token")
                #Need to remove the quotes from the quoted string
                mymod.arguments.append(invocation[right][1].rstrip()[1:-1])
            elif (invocation[right][0] == "STRING"):
                if (right + 1) < len(invocation):
                    raise Exception("STRING token must be last element of invocation or following a OPTION token")
                mymod.arguments.append(invocation[right][1].rstrip())
            else:
                raise Exception("Unexpected %s token %s" % (invocation[right][0], invocation[right][1]))
            right += 1

        self.all_modules.append(mymod)
        return mymod

    def get_family_(self, top, tabs = 0):
        for i in range(0, tabs):
            self.strbuff.write("\t")

        self.strbuff.write("%s -->\n" % top.name)

        if len(top.children):
            for child in top.children:
                self.get_family_(child, tabs + 1)

    def get_family(self, top):
        if self.strbuff is not None:
            self.strbuff.close()

        self.strbuff = StringIO()
        self.get_family_(top)
        output = self.strbuff.getvalue()
        self.strbuff.close()
        return output
        

    def get_tree(self):
        output = ""
        for t in self.top_modules:
            output += self.get_family(t) + "\n"
        return output
        
    def print_family(self, top, tabs = 0):
        #print Self
        for i in range (0, tabs):
            print "\t",

        print top.name, "-->"

        if len(top.children):
            for child in top.children:
                self.print_family(child, tabs + 1)

    def print_tree(self):
        for t in self.top_modules:
            self.print_family(t)

        

########NEW FILE########
__FILENAME__ = ChopHelper
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

#shop/ChopHelper

import sys
import os
import time
import json
from datetime import datetime

from threading import Thread
from threading import Lock
import Queue

#from multiprocessing import Queue as mQueue
import ChopShopDebug as CSD


"""
    The chops class is the interface for ChopShop and modules to send output properly. Each module is given a reference
    to it's own chops class called "chop" -- this allows them to use function calls like chop.prnt("foo") in their module
    without having to do too much else to send output to the proper channel based on the user's settings

    chops provides four (4) main "channels" of output currently, which are:
    
    1. prnt -- basic print functionality, "print" is a keyword in python and so could not be reused
        should accept the same syntax as a call to print
        depending on what the user has set (out to stdout, out to ui, etc.) this function will route the output to the
        desired location
    2. debug -- DEPRECATED -- noone was using this, so this has been deprecated
    3. json -- json output to file
        outputs json data to a json specific file
        a module can specify a custom json encoder by calling set_custom_json_encoder and passing a function
    4. output files -- allow a module writer to output files carved from their module in a respectable manner, the following
       commands are avaialble:
        savefile -- save carved or other files from within a module, takes a filename, the data, and an optional "finalize" variable (default True)
        if finalize is set to false, chops will keep the file open, otherwise will close the file, also note that this will open the file
        with the 'w' flag so it will overwrite existing files
        appendfile -- same as savefile except it opens files in 'a' mode which will not overwrite existing files, also defaults its 'finalize'
        to False, so it keeps the handle open until explicitly closed
        finalizefile -- given a filename will close the handle to it (if open). If the file is not open, this is a noop

"""


class chops:
    GMT = False
    to_outs = None

    def __init__(self, id, name, dataq, core = None):
        self.id = id
        self.name = name
        self.dataq = dataq
        self.core = core
        self.cls = None
        self.tsformatshort = False

    def debug(self, *fmtstring):
        self.prnt(*fmtstring)

    def tsprnt(self, *fmtstring):
        self.tsprettyprnt(None, *fmtstring)

    def tsprettyprnt(self, color, *fmtstring):
        if self.to_outs['text']:
            if self.core is not None:
                ptime = ""
                ts = self.core.getptime()
                if self.GMT:
                    fmt = "%Y-%m-%d %H:%M:%S +0000"
                    ts = time.gmtime(ts)
                else:
                    fmt = "%Y-%m-%d %H:%M:%S %Z"
                    ts = time.localtime(ts)

                if self.tsformatshort:
                    ptime = "[%02d:%02d:%02d]" % (ts[3], ts[4], ts[5])
                else:
                    ptime = time.strftime(fmt, ts).rstrip()
                    ptime = "[%s] " % (str(ptime))
                fmtstring = (ptime,) + fmtstring

            self.prettyprnt(color, *fmtstring)

    def prnt(self, *fmtstring):
        self.prettyprnt(None, *fmtstring)

    def prettyprnt(self, color, *fmtstring):
        if self.to_outs['text']:
            mystring = ''

            supress = False 
            extents = None 
            if fmtstring[-1] is None:
                extents = -1
                supress = True

            for strn in fmtstring[0:extents]:
                strn = str(strn)
                if mystring != '':
                    mystring += ' '
                mystring += strn

            message = self.__get_message_template__()
            message['type'] = 'text'
            message['data'] = {'data' : mystring, 
                               'suppress' : supress,
                               'color' : color,
                              }

            self.dataq.put(message)

    def savefile(self, filename, data, finalize = True, prepend_timestamp = False):
        if prepend_timestamp:
            if self.core is not None:
                ts = self.core.getptime()
                if self.GMT:
                    fmt = "%Y%m%d%H%M%SZ"
                    ts = time.gmtime(ts)
                else:
                    fmt = "%Y%m%d%H%M%S%Z"
                    ts = time.localtime(ts)
                filename = "%s-%s" % (time.strftime(fmt, ts).strip(), filename)
        self.appendfile(filename,data,finalize,'w')
        return filename


    #mode should not be used by chop users -- 
    #it is meant to be used by savefile
    def appendfile(self, filename, data, finalize = False, mode = 'a'):
        if self.to_outs['savefiles']:
            message = self.__get_message_template__()
            message['type'] = 'filedata'
            message['data'] = { 'filename': filename, 
                                'data' : data,
                                'mode' : mode,
                                'finalize': finalize
                              }

            self.dataq.put(message)

    def finalizefile(self, filename):
        if self.to_outs['savefiles']:
            self.appendfile(filename, "", True)

    def tsjson(self, obj, key = 'timestamp'):
        if self.core is not None:
            ptime = ""
            ts = self.core.getptime()
            if self.GMT:
                fmt = "%Y-%m-%d %H:%M:%S +0000"
                ts = time.gmtime(ts)
            else:
                fmt = "%Y-%m-%d %H:%M:%S %Z"
                ts = time.localtime(ts)

            ptime = time.strftime(fmt, ts).rstrip()
            obj[key] = ptime

        self.json(obj)
        
    def json(self, obj):
        if self.to_outs['json']:

            try:
                if self.cls is not None:
                    jdout = json.dumps(obj, cls=self.cls)
                else:
                    jdout = json.dumps(obj)
            except Exception, e:
                msg = "FATAL ERROR in chop.json"
                if self.cls is not None:
                    msg = msg + " with custom json encoder"
                self.prettyprnt("RED", msg, e)
                return #don't put anything onto the queue
           
            message = self.__get_message_template__()
            message['type'] = 'json'
            message['data'] = {'data': jdout}

            self.dataq.put(message)

    def pyobj(self, obj):
        if self.to_outs['pyobj']:
            message = self.__get_message_template__()
            message['type'] = 'pyobj'
            message['data'] = obj

            try:
                self.dataq.put(message)
            except Exception, e:
                msg = "FATAL ERROR in chop.pyobj"
                self.prettyprnt("RED", msg, e)

    def pyjson(self, obj):
        self.pyobj(obj)
        self.json(obj)

    def set_custom_json_encoder(self, cls):
        self.cls = cls

    def set_ts_format_short(self, on = False):
        self.tsformatshort = on


    def __get_message_template__(self):
        message = { 'module' : self.name,
                    'id'  : self.id,
                    'time'   : '',
                    'addr'   : { 'src' : '',
                                 'dst' : '',
                                 'sport': '',
                                 'dport': ''
                               },
                    'proto'  : ''
                  }

        if self.core is not None:
            metadata = self.core.getmeta()

            if 'proto' in metadata:
            #if proto is in metadata it was filled out
                message['proto'] = metadata['proto']
                message['time'] = metadata['time']
                message['addr'] = {  'src' : metadata['addr']['src'],
                                     'dst' : metadata['addr']['dst'],
                                     'sport':metadata['addr']['sport'],
                                     'dport':metadata['addr']['dport'] 
                                   }
        return message
        


"""
     ChopHelper keeps track of all of the "chops" instances and provides an easy to use interface to obtain an instance.
     It also informs the caller that a new module has been added
"""

class ChopHelper:
    def __init__(self, tocaller, options):
        self.tocaller = tocaller
        self.to_outs = {'text': False,
                        'json': False,
                        'savefiles': False,
                        'pyobj': False
                       }
        self.choplist = []
        self.core = None


        if options['text']:
            self.to_outs['text'] = True 

        if options['jsonout']:
            self.to_outs['json'] = True

        if options['savefiles']:
            self.to_outs['savefiles'] = True

        if options['pyobjout']:
            self.to_outs['pyobj'] = True

        chops.GMT = options['GMT']
        chops.to_outs = self.to_outs

    #TODO add capability to modify to_outs on the fly

    def set_core(self, core):
        self.core = core

    def setup_main(self):
        return self.setup_module("ChopShop")

    def setup_module(self, name, id = 0):
        if id == 0:
            id = len(self.choplist)

        chop = chops(id, name, self.tocaller, self.core)
        self.choplist.append({'chop' : chop, 'id' : id})

        #Inform the caller that we are adding a module
        message = { 'type' : 'ctrl',
                    'data' : { 'msg'  : 'addmod',
                               'name' : name,
                               'id': id
                             }
                  }

        self.tocaller.put(message)
        return chop 

    def setup_dummy(self):
        chop = chops(-1, 'dummy', self.tocaller, self.core)
        chop.to_outs = {'text': False,
                        'json': False,
                        'savefiles': False,
                        'pyobj': False
                       }
        return chop


########NEW FILE########
__FILENAME__ = ChopLib
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


VERSION = 4.1 

import ConfigParser
import sys
import os
import imp
import traceback
import time
from threading import Thread, Lock
import re
from cStringIO import StringIO

CHOPSHOP_WD = os.path.realpath(os.path.dirname(sys.argv[0]))

if CHOPSHOP_WD + '/shop' not in sys.path:
    sys.path.append(CHOPSHOP_WD + '/shop')

DEFAULT_MODULE_DIRECTORY = CHOPSHOP_WD + '/modules/'
DEFAULT_EXTLIB_DIRECTORY = CHOPSHOP_WD + '/ext_libs/'

from ChopNids import ChopCore
from ChopHelper import ChopHelper
from ChopSurgeon import Surgeon
from ChopException import ChopLibException
from ChopGrammar import ChopGrammar
"""
    ChopLib is the core functionality of ChopShop. It provides a library interface to the processing side of chopshop
    Any output/UI functionality has been extracted and is not done by this class. ChopLib will output all output onto queue
    which can be used by the calling party to display information to the user
"""

class ChopLib(Thread):
    daemon = True
    def __init__(self):
        Thread.__init__(self, name = 'ChopLib')
        global DEFAULT_MODULE_DIRECTORY
        global DEFAULT_EXTLIB_DIRECTORY

        pyversion = sys.version_info
        pyversion = float(str(pyversion[0]) + "." + str(pyversion[1]))

        if pyversion < 2.6:
            raise ChopLibException("Minimum Python Version 2.6 Required")

        global Queue
        global Process
        from multiprocessing import Process, Queue
        from Queue import Empty
        Queue.Empty = Empty #I'd prefer to keep this scoped to Queue

        self.options = { 'mod_dir': [DEFAULT_MODULE_DIRECTORY],
                         'ext_dir': [DEFAULT_EXTLIB_DIRECTORY],
                         'base_dir': None,
                         'filename': '',
                         'filelist': None,
                         'bpf': None,
                         'aslist': False,
                         'longrun': False,
                         'interface': '',
                         'modinfo': False,
                         'modtree': False,
                         'GMT': False,
                         'savefiles': False, #Should ChopShop handle the saving of files?
                         'text': False,
                         'pyobjout': False,
                         'jsonout': False,
                         'modules': ''
                       }

        self.stopped = False

        #Setup Interaction Queues
        self.tocaller = Queue() #output directly to caller
        self.fromnids = Queue() #input queue from nids process
        self.tonids = Queue() #output queue to nids process

        #Start up Process 2 (Nids Process)
        self.nidsp = Process(target=self.__nids_core_runner_, args=(self.tonids, self.fromnids, self.tocaller))
        self.nidsp.daemon = True
        self.nidsp.start()

        self.chop = None
        self.surgeon = None

        self.kill_lock = Lock()

    @property
    def mod_dir(self):
        """Directory to load modules from."""
        return self.options['mod_dir']

    @mod_dir.setter
    def mod_dir(self, v):
        if isinstance(v, basestring):
            self.options['mod_dir'] = [v]
        else:
            self.options['mod_dir'] = v

    @property
    def ext_dir(self):
        """Directory to load external libraries from."""
        return self.options['ext_dir']

    @ext_dir.setter
    def ext_dir(self, v):
        if isinstance(v, basestring):
            self.options['ext_dir'] = [v]
        else:
            self.options['ext_dir'] = v

    @property
    def base_dir(self):
        """Base directory to load modules and external libraries."""
        return self.options['base_dir']

    @base_dir.setter
    def base_dir(self, v):
        if isinstance(v, basestring):
            self.options['base_dir'] = [v]
        else:
            self.options['base_dir'] = v

    @property
    def filename(self):
        """input pcap file."""
        return self.options['filename']

    @filename.setter
    def filename(self, v):
        self.options['filename'] = v

    @property
    def filelist(self):
        """list of files to process"""
        return self.options['filelist']

    @filelist.setter
    def filelist(self, v):
        self.options['filelist'] = v

    @property
    def aslist(self):
        """Treat filename as a file containing a list of files."""
        return self.options['aslist']

    @aslist.setter
    def aslist(self, v):
        self.options['aslist'] = v

    @property
    def longrun(self):
        """Read from filename forever even if there's no more pcap data."""
        return self.options['longrun']

    @longrun.setter
    def longrun(self, v):
        self.options['longrun'] = v

    @property
    def interface(self):
        """interface to listen on."""
        return self.options['interface']

    @interface.setter
    def interface(self, v):
        self.options['interface'] = v

    @property
    def modinfo(self):
        """print information about module(s) and exit."""
        return self.options['modinfo']

    @modinfo.setter
    def modinfo(self, v):
        self.options['modinfo'] = v

    @property
    def modtree(self):
        """print information about module tree and exit."""
        return self.options['modtree']

    @modtree.setter
    def modtree(self, v):
        self.options['modtree'] = v

    @property
    def GMT(self):
        """timestamps in GMT (tsprnt and tsprettyprnt only)."""
        return self.options['GMT']

    @GMT.setter
    def GMT(self, v):
        self.options['GMT'] = v

    @property
    def savefiles(self):
        """Handle the saving of files. """
        return self.options['savefiles']

    @savefiles.setter
    def savefiles(self, v):
        self.options['savefiles'] = v

    @property
    def text(self):
        """Handle text/printable output. """
        return self.options['text']

    @text.setter
    def text(self, v):
        self.options['text'] = v

    @property
    def pyobjout(self):
        """Handle raw python objects"""
        return self.options['pyobjout']

    @pyobjout.setter
    def pyobjout(self, v):
        self.options['pyobjout'] = v

    @property
    def jsonout(self):
        """Handle JSON Data (chop.json)."""
        return self.options['jsonout']

    @jsonout.setter
    def jsonout(self, v):
        self.options['jsonout'] = v

    @property
    def modules(self):
        """String of Modules to execute"""
        return self.options['modules']

    @modules.setter
    def modules(self, v):
        self.options['modules'] = v

    @property
    def bpf(self):
        """BPF string to pass to Nids"""
        return self.options['bpf']

    @bpf.setter
    def bpf(self, v):
        self.options['bpf'] = v

    def get_message_queue(self):
        return self.tocaller

    def get_stop_fn(self):
        return self.stop

    def version(self):
        global VERSION
        return VERSION

    def abort(self):
        self.tonids.put(['abort'])
        self.surgeon.abort()

    def stop(self):
        self.stopped = True
        if self.surgeon:
            self.surgeon.stop()

    def setup_local_chop(self, name = "ChopShop", pid = -1):
        #This allows Process 1 to access Chops, note that it has
        #a hardcoded id of -1 since otherwise it might overlap
        #with the other chops, only use a custom id if you know
        #what you're doing
        chophelper = ChopHelper(self.tocaller, self.options)
        self.chop = chophelper.setup_module(name, pid)

    def send_finished_msg(self, data = {}, stop_seq = False):
        message = { 'type' : 'ctrl',
                    'data' : {'msg' : 'finished',
                              'status': 'ok' #default to ok
                            }
                  }

        for key,val in data.iteritems():
            message['data'][key] = val

        self.kill_lock.acquire()
        try:
            self.tocaller.put(message)

            if stop_seq:
                self.tonids.put(['stop'])
                self.nidsp.join()
        except AttributeError:
            pass
        finally:
            self.kill_lock.release()

    def run(self):
        if not self.options['modinfo'] and not self.options['modtree']: #No point in doing surgery if it's modinfo or modtree
            # Figure out where we're reading packets from
            if not self.options['interface']:
                if not self.options['filename']:
                    if not self.options['filelist']:
                        self.send_finished_msg({'status':'error','errors': 'No input Specified'}, True)
                        return
                    else:
                        self.surgeon = Surgeon(self.options['filelist'])
                        self.options['filename'] = self.surgeon.create_fifo()
                        self.surgeon.operate()
                else:
                    if not os.path.exists(self.options['filename']):
                        self.send_finished_msg({'status':'error','errors':"Unable to find file '%s'" % self.options['filename']}, True)
                        return

                    if self.options['aslist']:
                        #input file is a listing of files to process
                        self.surgeon = Surgeon([self.options['filename']], self.options['longrun'])
                        self.options['filename'] = self.surgeon.create_fifo()
                        #TODO operate right away or later?
                        self.surgeon.operate(True)

        #Send options to Process 2 and tell it to setup
        self.kill_lock.acquire()
        try:
            self.tonids.put(['init', self.options])
        except AttributeError:
            #usually means tonids is None
            #possibly being killed?
            pass
        except Exception, e:
            raise ChopLibException(e)
        finally:
            self.kill_lock.release()

        #Wait for a reponse
        self.kill_lock.acquire()
        try:
            resp = self.fromnids.get()
        except AttributeError:
            resp = "notok" #probably means fromnids is None, which should only happen when being killed
        except Exception, e:
            raise ChopLibException(e)
        finally:
            self.kill_lock.release()

        if resp != 'ok':
            self.send_finished_msg({'status':'error','errors':resp}, True)
            return

        if self.options['modinfo']:
            self.kill_lock.acquire()
            try:
                self.tonids.put(['mod_info'])
                resp = self.fromnids.get() #really just to make sure the functions finish
            except AttributeError:
                pass
            finally:
                self.kill_lock.release()

            #Process 2 will quit after doing its job

            #Inform caller that the process is done
            self.send_finished_msg()
            #Surgeon should not be invoked so only need
            #to cleanup nidsp
            self.nidsp.join()
            return
        elif self.options['modtree']:
            self.kill_lock.acquire()
            try:
                self.tonids.put(['mod_tree'])
                resp = self.fromnids.get()
            except AttributeError:
                pass
            finally:
                self.kill_lock.release()

            self.send_finished_msg()
            self.nidsp.join()
            return
        else:
            self.kill_lock.acquire()
            try:
                self.tonids.put(['cont'])
            except AttributeError:
                pass
            except Exception, e:
                raise ChopLibException(e)
            finally:
                self.kill_lock.release()

        #Processing loop
        while True:
            self.kill_lock.acquire()
            try:
                data = self.fromnids.get(True, .1)
            except Queue.Empty, e:
                if not self.nidsp.is_alive():
                    break
                if self.stopped:
                    self.nidsp.terminate()
                continue
            except AttributeError:
                break
            finally:
                self.kill_lock.release()

            if data[0] == "stop":
                #Send the message to caller that we need to stop
                message = { 'type' : 'ctrl',
                            'data' : {'msg'  : 'stop'}
                          }
                self.kill_lock.acquire()
                try:
                    self.tocaller.put(message)
                finally:
                    self.kill_lock.release()

                self.nidsp.join(1)
                #Force Terminate if nids process is non-compliant
                if self.nidsp.is_alive():
                    self.nidsp.terminate()
                break

            time.sleep(.1)

        ###Teardown of the program
        #Join with Surgeon
        if self.surgeon is not None:
            self.surgeon.stop()

        #Join with Nids Process
        self.nidsp.join()

        #Inform caller that we are now finished
        self.send_finished_msg()

    #This must be torn down safely after who need it have cleaned up
    def finish(self):
        self.kill_lock.acquire()
        try:
            self.stop()
            if self.nidsp.is_alive():
                self.nidsp.terminate()
            self.nidsp.join(.1)

            try:
                self.tonids.close()
                self.fromnids.close()
                self.tocaller.close()

                self.tonids = None
                self.fromnids = None
                self.tocaller = None
                time.sleep(.1)

            except:
                pass
        finally:
            self.kill_lock.release()


#######Process 2 Functions######

    def __loadModules_(self, name, path):
        try:
            (file, pathname, description) = imp.find_module(name, path)
            loaded_mod = imp.load_module(name, file, pathname, description)
        except Exception, e:
            tb = traceback.format_exc()
            raise Exception(tb)

        return loaded_mod


    #Process 2 "main" process
    def __nids_core_runner_(self, inq, outq, dataq, autostart = True):
        #Note that even though this is within the class it is being used irrespective
        #of the Process 1 class, so 'self' is never used for data

        os.setpgrp()

        #Responsible for creating "chop" classes and
        #keeping track of the individual output handlers
        chophelper = None
        chop = None

        options = None
        module_list = []
        ccore = None
        mod_dir = []
        ext_dir = []
        chopgram = None
        abort = False

        #Initialization
        while (True):
            try:
                data = inq.get(True, .1)
            except Queue.Empty, e:
                continue

            if data[0] == 'init':

                try:
                    f = open('/dev/null', 'w')
                    os.dup2(f.fileno(), 1)
                    g = open('/dev/null', 'r')
                    os.dup2(g.fileno(), 0)
                except:
                    outq.put("Unable to assign /dev/null as stdin/stdout")
                    sys.exit(-1)

                options = data[1]

                #Set up the module directory and the external libraries directory
                if options['base_dir'] is not None:
                    for base in options['base_dir']:
                        real_base = os.path.realpath(base)
                        mod_dir.append(real_base + "/modules/")
                        ext_dir.append(real_base + "/ext_libs")
                else:
                    mod_dir = options['mod_dir']
                    ext_dir = options['ext_dir']

                for ed_path in ext_dir:
                    sys.path.append(os.path.realpath(ed_path))

                #Setup the chophelper
                chophelper = ChopHelper(dataq, options)
                chop = chophelper.setup_main()

                #Setup the modules
                chopgram = ChopGrammar()
                try:
                    all_modules = chopgram.parseGrammar(options['modules'])
                except Exception, e:
                    outq.put(traceback.format_exc())
                    sys.exit(1)


                if len(all_modules) == 0:
                    outq.put('Zero Length Module List')
                    sys.exit(1)

                try:
                    for mod in all_modules:
                        mod.code = self.__loadModules_(mod.name, mod_dir)
                        minchop = '0'
                        try:
                            mod_version = mod.code.moduleVersion
                            minchop = mod.code.minimumChopLib

                        except: #Legacy Module
                            mod.legacy = True
                            chop.prnt("Warning Legacy Module %s!" % mod.code.moduleName)
                    
                        try:
                            #TODO more robust version checking
                            if str(minchop) > str(VERSION):
                                raise Exception("Module requires ChopLib Version %s or greater" % minchop)
                        except Exception, e:
                            outq.put(e.args)
                            sys.exit(1)

                except Exception, e:
                    outq.put(e)
                    sys.exit(1)

                module_list = all_modules

                #It got this far, everything should be okay
                outq.put('ok')

            elif data[0] == 'mod_info':
                #Hijack stdout to support modules that use print
                orig_stdout = sys.stdout #We don't know what the original stdout might have been (__stdout__)
                                         #Although it should be /dev/null
                for mod in module_list:
                    try:
                        modinf = "%s (%s) -- requires ChopLib %s or greater:\n" % (mod.code.moduleName, mod.code.moduleVersion, mod.code.minimumChopLib)
                    except:
                        modinf = "%s (Legacy Module) -- pre ChopLib 4.0:\n" % mod.code.moduleName

                    modtxt = None

                    try:
                        modtxt = mod.code.module_info()
                        if modtxt is not None:
                            modtxt = modtxt + "\n"
                        else:
                            raise Exception
                    except Exception, e:
                        modtxt = "Missing module information for %s\n" % mod.name

                    sys.stdout = strbuff = StringIO()

                    try:
                        #Instantiate a dummy 'chop' accessor for each module in case
                        #they use it in init
                        mod.code.chop = chophelper.setup_dummy()
                        sys.argv[0] = mod.code.moduleName
                        mod.code.init({'args': ['-h']})
                    except SystemExit, e:
                        #OptParse will except as it ends
                        modtxt = modtxt + strbuff.getvalue() 
                        pass

                    #Close and free contents
                    strbuff.close()

                    chop.prnt("%s%s----------\n" % (modinf, modtxt))

                #Restore stdout
                sys.stdout = orig_stdout
                outq.put('fini')
                sys.exit(0)

            elif data[0] == 'mod_tree':
                tree = chopgram.get_tree()
                chop.prnt(tree)


                outq.put('fini')
                sys.exit(0)
            elif data[0] == 'cont':
                break
            elif data[0] == 'stop': #Some error must have occurred
                sys.exit(0)
            elif data[0] == 'abort': #Process any data we have
                abort = True
                break
            else:
                #FIXME custom exception?
                raise Exception("Unknown message")


        chop.prettyprnt("RED", "Starting ChopShop")

        #Initialize the ChopShop Core
        ccore = ChopCore(options, module_list, chop, chophelper)

        #Setup Core and its modules
        ccore.prep_modules()


        if autostart:
            ccore.start()

        #If received abort during init, this is true
        ccore.abort = abort

        while (True):
            if ccore.complete:
                break

            try:
                data = inq.get(True, .1)
            except Queue.Empty, e:
                continue

            if data[0] == 'start':
                ccore.start()
            elif data[0] == 'stop':
                ccore.stop()
            elif data[0] == 'abort':
                ccore.abort = True

        ccore.join()

        chop.prettyprnt("RED", "ChopShop Complete")




########NEW FILE########
__FILENAME__ = ChopNids
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import sys
import os
import imp
import nids
import shlex
import traceback
from threading import Thread
from threading import Lock
from multiprocessing import Process, Manager, Queue as mQueue
import Queue
import time
import copy

import struct
import socket

import ChopShopDebug as CSD
from ChopProtocol import ChopProtocol


tcp_modules = []
ip_modules = []
udp_modules = []
all_modules = []

ptimestamp = 0
metadata = {}

class udpdata:
    def __init__(self):
        self.sval = False
    def stop(self):
        self.sval = True

class tcpdata:
    def __init__(self):
        self.dval = 0
        self.sval = False
    def discard(self,dv):
        self.dval = dv
    def stop(self):
        self.sval = True

class ipdata:
    def __init__(self):
        pass

class hstream:
    pass

class stream_meta:
    def __init__(self,of=0,os=0):
        self.stream_data = {}
        self.offset_client = of
        self.offset_server = os


def process_ip_data(ip):
    iplocal = ipdata()

    data = struct.unpack('<BBHHHBBH', ip[0:12])
    iplocal.version = data[0] >> 4
    iplocal.ihl = data[0] & 0x0f # 0b1111
    iplocal.dscp = data[1] >> 2
    iplocal.ecn = data[1] & 0x03 # 0b0011
    iplocal.length = data[2]
    iplocal.identification = data[3]
    iplocal.flags = data[4] >> 13
    iplocal.frag_offset = data[4] & 0x1fff # 0b0001111111111111
    iplocal.ttl = data[5]
    iplocal.protocol = data[6]
    iplocal.checksum = data[7]
    iplocal.src = socket.inet_ntoa(ip[12:16])
    iplocal.dst = socket.inet_ntoa(ip[16:20])
    iplocal.raw = ip

    iplocal.addr = ((iplocal.src, ''), (iplocal.dst, ''))

    return iplocal


# Differences between UDP and TCP:
#
# There is no discard function for udp objects.
#
# In UDP we don't have the concept of client and server objects.
# We can't possibly know which is which.
#
# We don't have the concept of states, though we implement our own
# crude taste functionality anyways.
#
# Because of the lack of states, calling stop() causes that entire
# quad-tuple to be ignored. This can have unintended consequences so
# be careful.
#
# Because of the lack of states there is no teardown() for UDP. We can't
# possibly know this is the last UDP packet for that tuple.
def copy_udp_data(addr, data, ip):
    udplocal = udpdata()
    udplocal.addr = addr
    udplocal.data = data
    udplocal.ip = ip
    return udplocal

def copy_tcp_data(tcp,offset_info,client_direction):
    tcplocal = tcpdata()
    tcplocal.addr = tcp.addr
    tcplocal.nids_state = tcp.nids_state
    tcplocal.client = hstream()
    tcplocal.server = hstream()


    tcplocal.client.state = tcp.client.state
    tcplocal.client.data = tcp.client.data[offset_info.offset_client:]
    tcplocal.client.urgdata = tcp.client.urgdata
    tcplocal.client.count = tcp.client.count
    tcplocal.client.offset = tcp.client.offset + offset_info.offset_client
    tcplocal.client.count_new = tcp.client.count_new
    tcplocal.client.count_new_urg = tcp.client.count_new_urg

    tcplocal.server.state = tcp.server.state
    tcplocal.server.data = tcp.server.data[offset_info.offset_server:]
    tcplocal.server.urgdata = tcp.server.urgdata
    tcplocal.server.count = tcp.server.count
    tcplocal.server.offset = tcp.server.offset + offset_info.offset_server
    tcplocal.server.count_new = tcp.server.count_new
    tcplocal.server.count_new_urg = tcp.server.count_new_urg


    if client_direction:
        tcplocal.dval = tcplocal.client.count_new
    else:
        tcplocal.dval = tcplocal.server.count_new

    return tcplocal

class ChopCore(Thread):
    def __init__(self,options, module_list, chp, chophelper):
        Thread.__init__(self)
        self.options = options
        self.module_list = module_list
        self.chophelper = chophelper
        self.stopped = False
        self.complete = False
        self.abort = False

        global chop
        chop = chp

    def stop(self):
        self.complete = True
        self.stopped = True

    def iscomplete(self):
        return self.complete

    def getptime(self):
        global ptimestamp
        return ptimestamp

    def getmeta(self):
        global metadata
        return metadata

    def prep_modules(self):
        self.chophelper.set_core(self)
        modules = self.module_list
        for module in modules:
            code = module.code
            code.chop = self.chophelper.setup_module(code.moduleName)

    def run(self):
        global chop
        #Initialize modules to be run
        options = self.options
        modules = self.module_list#module_list
        module_options = {}

        chop.prettyprnt("RED", "Initializing Modules ...")

        for module in modules:
            name = module.name
            arguments = module.arguments #shlex.split(module[1])
            code = module.code #module[0]
            #Create module_data for all modules
            module.module_data = {'args': arguments}
            module.streaminfo = {}

            chop.prettyprnt("CYAN", "\tInitializing module '" + name + "'")
            try:
                module_options = code.init(module.module_data)
            except Exception, e:
                chop.prnt("Error Initializing Module", code.moduleName + ":", e)
                self.complete = True
                return

            if 'error' in module_options:
                chop.prettyprnt("GREEN", "\t\t%s init failure: %s" % (code.moduleName, module_options['error']))
                continue

            if module.legacy:
                if module_options['proto'] == 'tcp' :
                    tcp_modules.append(module)
                    all_modules.append(module)
                    module.streaminfo['tcp'] = {}
                elif module_options['proto'] == 'ip' :
                    ip_modules.append(module)
                    all_modules.append(module)
                    module.streaminfo['ip'] = {}
                elif module_options['proto'] == 'udp' :
                    udp_modules.append(module)
                    all_modules.append(module)
                    module.streaminfo['udp'] = {}
                else:
                    chop.prnt("Undefined Module Type\n")
                    self.complete = True
                    return
            else:
                all_modules.append(module)
                #Proto is an array of dictionaries
                if not isinstance(module_options['proto'], list): #Malformed
                    chop.prnt("%s has malformed proto list" % module.code.moduleName)
                    self.complete = True
                    return

                for proto in module_options['proto']:
                    #Right now (4.0) each dictionary only has one key
                    #This might change in the future but should be easy
                    #since it's already a separate dictionary
                    if type(proto) is not dict:
                        chop.prnt("%s has malformed proto list" % module.code.moduleName)
                        self.complete = True
                        return
 
                    for input in proto.keys():
                        if input not in module.inputs:
                            module.inputs[input] = []

                        if proto[input] != '':
                            module.inputs[input].append(proto[input])
                            module.outputs.append(proto[input])

                        #Initialize the streaminfo array by type
                        if input != 'any' and input != 'ip':
                            module.streaminfo[input] = {}

                        if input == 'tcp':
                            tcp_modules.append(module)
                        elif input == 'udp':
                            udp_modules.append(module)
                        elif input == 'ip':
                            ip_modules.append(module)
                        elif input == 'any': #Special input that catches all non-core types
                            #Initialize the streaminfo for all parents of the 'any' module
                            if not len(module.parents):
                                chop.prettyprnt("GREEN", "WARNING: No Parent for %s to provide data" % (module.code.moduleName))
                            else:
                                for parent in module.parents:
                                    for output in parent.outputs:
                                        module.streaminfo[output] = {}
                        else: # non-core types, e.g., 'http' or 'dns'
                            if len(module.parents): #Make sure parents give it what it wants
                                for parent in module.parents:
                                    if input not in parent.outputs:
                                        chop.prettyprnt("GREEN", "WARNING: Parent to %s not providing %s data" % (module.code.moduleName, input))
                            else:
                                chop.prettyprnt("GREEN", "WARNING: No Parent for %s providing %s data" % (module.code.moduleName, input))


        if not all_modules:
            chop.prnt("No modules")
            self.complete = True
            return

        chop.prettyprnt("RED", "Running Modules ...")

        #Actually run the modules
        if options['interface']:
            nids.param("scan_num_hosts",0)
            nids.param("device",options['interface'])
            if options['bpf'] is not None:
                nids.param("pcap_filter", options['bpf'])

            try:
                nids.init()
            except Exception, e:
                chop.prnt("Error initting on interface: ", e)
                self.complete = True
                return

            nids.chksum_ctl([('0.0.0.0/0',False),])
            nids.register_tcp(handleTcpStreams)
            nids.register_udp(handleUdpDatagrams)
            nids.register_ip(handleIpPackets)

            while(True): #This overall while prevents exceptions from halting the processing of packets
                if self.stopped:
                    break
                try:
                    while not self.stopped:
                        nids.next()
                        time.sleep(.001) #XXX is this enough or too much?
                except Exception, e:
                    chop.prnt("Error processing packets", e)
                    #no need to exit
        else:
            if options['filename'] is "":
                chop.prnt("Empty Filename")
                self.complete = True
                return

            nids.param("scan_num_hosts",0)
            nids.param("filename",options['filename'])
            if options['bpf'] is not None:
                nids.param("pcap_filter", options['bpf'])

            try:
                nids.init()
            except Exception, e:
                self.complete = True
                chop.prnt("Error initting: ", e)
                return

            nids.chksum_ctl([('0.0.0.0/0',False),])
            nids.register_tcp(handleTcpStreams)
            nids.register_udp(handleUdpDatagrams)
            nids.register_ip(handleIpPackets)

            while(not self.stopped): #This overall while prevents exceptions from halting the long running reading
                try:
                    if options['longrun']: #long running don't stop until the proces is killed externally
                        while not self.stopped:
                            if not nids.next():
                                if self.abort: #exit if sigabrt if no other data
                                    break
                                time.sleep(.001)
                    else:
                        while not self.stopped and nids.next():
                            pass
                    self.stopped = True #Force it to true and exit
                except Exception, e:
                    chop.prnt("Error processing packets", e)
                    if not options['longrun']:
                        self.stopped = True #Force it to true and exit
                        raise # only raise if not in longrun

        chop.prettyprnt("RED", "Shutting Down Modules ...")

        #Call modules shutdown functions to do last-minute actions
        for module in all_modules:
            try:
                chop.prettyprnt("CYAN","\tShutting Down " + module.code.moduleName)
                module.code.shutdown(module.module_data)
            except Exception,e:
                pass

        chop.prettyprnt("RED", "Module Shutdown Complete ...")
        self.complete = True

def handleIpPackets(pkt):
    global timestamp
    global metadata
    global once

    ptimestamp = nids.get_pkt_ts()


    if len(pkt) >= 20:#packets should have at least a 20 byte header
                      #nids should take care of this, but better safe than sorry, I guess
        ip = process_ip_data(pkt)

        metadata['proto'] = 'ip'
        metadata['time'] = ptimestamp
        metadata['addr'] = { 'src': ip.src,
                             'dst': ip.dst,
                             'dport': '',
                             'sport': ''
                            }

        for module in ip_modules:
            code = module.code
            #TODO do we need a shallow or deep copy?
            ipd = copy.copy(ip)        
            ipd.timestamp = ptimestamp
            ipd.module_data = module.module_data

            try:
                output = code.handlePacket(ipd)
            except Exception, e:
                exc = traceback.format_exc()
                chop.prettyprnt("YELLOW", "Exception in module %s -- Traceback: \n%s" % (code.moduleName, exc))
                sys.exit(-1)

            module.module_data = ipd.module_data

            #Handle Children
            if not module.legacy:
                if output is not None:
                    ipd.unique = ipd.src + "-" + ipd.dst
                    ipd.type = 'ip'
                    handleChildren(module, ipd, output)


            del ipd            


    else: #some error?
        chop.prnt("Malformed ip data received from nids ... skipping")

def handleUdpDatagrams(addr, data, ip):
    global ptimestamp
    global metadata
    ptimestamp = nids.get_pkt_ts()
    ((src,sport),(dst,dport)) = addr
    if src < dst:
        f_string = src + ":" + str(sport) + "-" + dst + ":" + str(dport)
    else:
        f_string = dst + ":" + str(dport) + "-" + src + ":" + str(sport)


    metadata['proto'] = 'udp'
    metadata['time'] = ptimestamp
    metadata['addr'] = { 'src' : src,
                         'dst' : dst,
                         'sport' : sport,
                         'dport' : dport
                       }

    stopped = False
    for module in udp_modules:
        code = module.code
        if f_string in module.streaminfo['udp'] and module.streaminfo['udp'][f_string] == None:
            # This module called udp.stop() for this f_string
            continue

        # Create new udp object
        udpd = copy_udp_data(addr, data, ip)
        udpd.timestamp = ptimestamp
        udpd.module_data = module.module_data

        if f_string not in module.streaminfo['udp']:
            # First time this module has seen this f_string.
            # Create a new stream_data object. Will save it later.
            module.streaminfo['udp'][f_string] = stream_meta()
            udpd.stream_data = stream_meta().stream_data
        else:
            udpd.stream_data = module.streaminfo['udp'][f_string].stream_data

        try:
            output = code.handleDatagram(udpd)
        except Exception, e:
            exc = traceback.format_exc()
            chop.prettyprnt("YELLOW", "Exception in module %s -- Traceback: \n%s" % (code.moduleName, exc))
            sys.exit(-1)

        #Have to copy the information back now
        module.module_data = udpd.module_data

        #Handle Children
        if not module.legacy:
            if output is not None:
                udpd.unique = f_string
                udpd.type = "udp"
                handleChildren(module, udpd, output) 

        if udpd.sval: #we were told by this module to stop collecting
            del udpd
            module.streaminfo['udp'][f_string] = None
            stopped = True
            continue
        #else we continue on since this module is still collecting
        module.streaminfo['udp'][f_string].stream_data = udpd.stream_data
        del udpd

def handleTcpStreams(tcp):
    end_states = (nids.NIDS_CLOSE, nids.NIDS_TIMEOUT, nids.NIDS_RESET)
    client_direction = False
    if tcp.server.count_new == 0:
        smallest_discard = tcp.client.count_new
        client_direction = True
    else:
        smallest_discard = tcp.server.count_new

    global ptimestamp
    global metadata
    ptimestamp = nids.get_pkt_ts()
    ((src,sport),(dst,dport)) = tcp.addr
    f_string = src + ":" + str(sport) + "-" + dst + ":" + str(dport)

    metadata['proto'] = 'tcp'
    metadata['time'] = ptimestamp
    metadata['addr'] = { 'src' : src,
                         'dst' : dst,
                         'sport' : sport,
                         'dport' : dport
                       }

    if tcp.nids_state == nids.NIDS_JUST_EST: #Implement tasting
        for module in tcp_modules:
            code = module.code
            collecting = False
            try:
                temp_info = stream_meta(0,0)

                tcpd = copy_tcp_data(tcp,temp_info,0)
                tcpd.timestamp = ptimestamp
                tcpd.module_data = module.module_data
                #Create a temporary stream_data in case the module needs it -- it'll be saved if the module decides to collect
                tcpd.stream_data = stream_meta().stream_data #Yes I could probably do = {} but this is more descriptive
                collecting = code.taste(tcpd)

            except Exception, e:
                chop.prettyprnt("YELLOW", "Module %s error in taste function: %s" % (code.moduleName, str(e)))
                sys.exit(-1)

            module.module_data = tcpd.module_data

            if collecting:
                module.streaminfo['tcp'][f_string] = stream_meta() 
                module.streaminfo['tcp'][f_string].stream_data = tcpd.stream_data
                tcp.client.collect = 1
                tcp.server.collect = 1

            del tcpd


    elif tcp.nids_state == nids.NIDS_DATA:#Implement data processing portion
        stopped = False
        for module in tcp_modules:
            code = module.code
            if f_string in module.streaminfo['tcp']: #If this module is collecting on this stream

                #Create a copy of the data customized for this module
                tcpd = copy_tcp_data(tcp, module.streaminfo['tcp'][f_string], client_direction) 
                tcpd.timestamp = ptimestamp
                tcpd.stream_data = module.streaminfo['tcp'][f_string].stream_data
                tcpd.module_data = module.module_data


                try:
                    output = code.handleStream(tcpd)
                except Exception, e:
                    exc = traceback.format_exc()
                    chop.prettyprnt("YELLOW", "Exception in module %s -- Traceback: \n%s" % (code.moduleName, exc))
                    sys.exit(1)

                #Have to copy the information back now
                module.module_data = tcpd.module_data


                if not module.legacy:
                    if output is not None:
                        tcpd.unique = f_string
                        tcpd.type = "tcp"
                        handleChildren(module, tcpd, output)

                if tcpd.sval: #we were told by this module to stop collecting
                    del tcpd
                    del module.streaminfo['tcp'][f_string]
                    stopped = True

                    #TODO check for potential over deletion? -- Also should we be deleting children here?
                    #TODO add deletion sequence from teardown below for children
                    continue
                #else we continue on since this module is still collecting
                module.streaminfo['tcp'][f_string].stream_data = tcpd.stream_data
                module.streaminfo['tcp'][f_string].last_discard = tcpd.dval

                if tcpd.dval < smallest_discard:
                    smallest_discard = tcpd.dval

                del tcpd


        #TODO collapse this with the lower for loop
        #Cleanup in case no more modules are collecting on this stream
        if stopped:
            found = False
            for module in tcp_modules:
                if f_string in module.streaminfo['tcp']:
                    found = True
                    continue

            if not found:
                tcp.client.collect = 0
                tcp.server.collect = 0


        for module in tcp_modules:
            code = module.code
            if f_string in module.streaminfo['tcp']:
                if module.streaminfo['tcp'][f_string].last_discard > smallest_discard:
                    diff = module.streaminfo['tcp'][f_string].last_discard - smallest_discard
                    if client_direction:
                        module.streaminfo['tcp'][f_string].offset_client += diff
                    else:
                        module.streaminfo['tcp'][f_string].offset_server += diff

        tcp.discard(smallest_discard)


    elif tcp.nids_state in end_states: #Teardown portion of code
        for module in tcp_modules:
            code = module.code
            if f_string in module.streaminfo['tcp']:
                try:
                    tcpd = copy_tcp_data(tcp, module.streaminfo['tcp'][f_string], client_direction) 
                    tcpd.timestamp = ptimestamp
                    tcpd.stream_data = module.streaminfo['tcp'][f_string].stream_data
                    tcpd.module_data = module.module_data
                    code.teardown(tcpd)
                except Exception, e:
                    exc = traceback.format_exc()
                    chop.prettyprnt("YELLOW", "Exception in module %s -- Traceback: \n%s" % (code.moduleName, exc))

                #delete the entry in the streaminfo dict
                del tcpd
                del module.streaminfo['tcp'][f_string]

                #TODO check for potential over deletion?
                if not module.legacy:
                    for outtype in module.inputs['tcp']: #For every output from tcp
                        for child in module.children:
                            if outtype not in child.inputs: #Check if this child accepts this type
                                continue
                            #This assumes unique has not been changed in the child
                            if f_string in child.streaminfo[outtype]:
                                del child.streaminfo[outtype][f_string]


def handleProtocol(module, protocol, pp): #pp is parent protocol
    code = module.code

    #unique should be set for all parents, including the standard tcp/udp types
    if protocol.unique is None:
        protocol.unique = pp.unique

    try:
        #If this excepts it's probably because protocol.type is not in streaminfo which should
        #have been created earlier -- this is an error on the part of the module author then

        #Initialize the object -- the pp.unique parent dictionary should have been initialized by parent function
        if protocol.unique not in module.streaminfo[protocol.type]:
            module.streaminfo[protocol.type][protocol.unique] = stream_meta()

        if module.streaminfo[protocol.type][protocol.unique] is None: #module has called stop
            return

        protocol.stream_data = module.streaminfo[protocol.type][protocol.unique].stream_data

    except KeyError, e:
        chop.prettyprnt("YELLOW", "Error attempting to lookup stream_data")
        sys.exit(1)
    except Exception, e:
        chop.prettyprnt("YELLOW", "Error attempting to set stream_data: %s" % str(e))
        sys.exit(1)

    #Add module_data to protocol object
    protocol.module_data = module.module_data

    #Elements that are common between tcp/udp and ChopProtocol
    if protocol.addr is None:
        protocol.setAddr(pp.addr)

    if protocol.timestamp is None:
        protocol.setTimeStamp(pp.timestamp)


    #TODO figure out if this is necessary and remove if not
    if isinstance(pp, ChopProtocol): #This is a 3rd level module (parent is not tcp or udp)
        pass
    else: #This is a 2nd level module (parent is tcp or udp)
        pass


    try:
        output = code.handleProtocol(protocol) 
    except Exception, e:
        exc = traceback.format_exc()
        chop.prettyprnt("YELLOW", "Exception in module %s -- Traceback: \n%s" % (code.moduleName, exc))
        sys.exit(1)


    #Copy it back just in case
    module.module_data = protocol.module_data


    #Handle any potential children
    if output is not None:
        handleChildren(module, protocol, output)

    if protocol.sval:
        module.streaminfo[protocol.type][protocol.unique] = None
        #Reset sval so it doesn't affect other children
        protocol.sval = False
        return

    module.streaminfo[protocol.type][protocol.unique].stream_data = protocol.stream_data


def handleChildren(module, protocol, output):
    #Handle any potential children
    if isinstance(output, ChopProtocol):
        output = [output]
    elif not isinstance(output, list):
        chop.prettyprnt("YELLOW", "Module %s returned an invalid type" % code.moduleName)
        sys.exit(1)

    for outp in output:
        if not isinstance(outp, ChopProtocol):
            chop.prettyprnt("YELLOW", "Module %s returned an invalid type" % code.moduleName)
            sys.exit(1)

        if outp.type not in module.inputs[protocol.type]:
            chop.prettyprnt("YELLOW", "Module %s returning unregistered type %s" % (code.moduleName, outp.type))
            sys.exit(1)

        for child in module.children:
            if outp.type in child.inputs or 'any' in child.inputs:
                #This ensure each child gets a copy that it can muck with
                child_copy = outp._clone() 
                handleProtocol(child, child_copy, protocol)

########NEW FILE########
__FILENAME__ = ChopProtocol
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


import copy

class ChopProtocol(object):

    def __init__(self, type):
        self.addr = None
        self.timestamp = None
        self.clientData = None
        self.serverData = None

        #These should not be modified on the fly
        #or directly touched by module authors
        self.type = type
        self.sval = False
        self.unique = None

    #If your data is complex enough
    #you MUST inherit from ChopProtocol and redefine _clone
    def _clone(self):
        return copy.deepcopy(self)

    def setUniqueId(self, unique):
        self.unique = unique

    def setAddr(self, addr):
        self.addr = addr

    def setTimeStamp(self, timestamp):
        self.timestamp = timestamp

    def setClientData(self, data):
        self.clientData = data

    def setServerData(self, data):
        self.serverData = data

    def stop(self):
        self.sval = True


########NEW FILE########
__FILENAME__ = ChopShopCurses
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import sys
from threading import Thread
import curses
from curses import ascii
import binascii
import time
import os
import fcntl
import termios
import struct


import ChopShopDebug as CSD

BUFFER_SIZE = 10000

class Color:
    YELLOW = curses.A_NORMAL
    CYAN = curses.A_NORMAL 
    MAGENTA = curses.A_NORMAL 
    GREEN = curses.A_NORMAL 
    RED = curses.A_NORMAL
    BLUE = curses.A_NORMAL 
    BLACK = curses.A_NORMAL
    WHITE = curses.A_NORMAL

    def __init__(self):
        pass

    def define_colors(self, has_colors):
        if not has_colors:
            return

        curses.init_pair(1, 3, 0) #Yellow on Black
        curses.init_pair(2, 6, 0) #Cyan on Black
        curses.init_pair(3, 5, 0) #Magenta on Black
        curses.init_pair(4, 2, 0) #Green on Black
        curses.init_pair(5, 1, 0) #Red on Black
        curses.init_pair(6, 4, 0) #Blue on Black
        curses.init_pair(7, 0, 7) #Black on White

        self.YELLOW = curses.color_pair(1)
        self.CYAN = curses.color_pair(2)
        self.MAGENTA = curses.color_pair(3)
        self.GREEN = curses.color_pair(4)
        self.RED = curses.color_pair(5)
        self.BLUE = curses.color_pair(6)
        self.BLACK = curses.color_pair(7)
        self.WHITE = curses.color_pair(0)

    def get_color(self, color):
        if color == "YELLOW":
            return self.YELLOW
        elif color == "CYAN":
            return self.CYAN
        elif color == "MAGENTA":
            return self.MAGENTA
        elif color == "GREEN":
            return self.GREEN
        elif color == "RED":
            return self.RED
        elif color == "BLUE":
            return self.BLUE
        elif color == "BLACK":
            return self.BLACK
        elif color == "WHITE":
            return self.WHITE
        else:
            return curses.A_NORMAL

Colors = Color()

"""
    vpanel is a "virtual" data panel and stores the data for a given window, it also keeps
    track of where the panel is.

"""

class vpanel:
    panel_id = 0

    def __init__(self,wn):
        self.position = 0
        self.data = []
        self.autoscroll = True
        self.windowname = wn
        self.evencolor = True
        vpanel.panel_id += 1

    def add_data(self, data, color = None):
        global Colors
        newdata = ""
        for ch in str(data):
            #printable characters and \t \n and are output to the screen
            #all others are hexlified
            if ascii.isprint(ch) or  ch == "\t" or ch == "\n":
                newdata += ch
            else:
                newdata +=  "\\" +  str(hex(ord(ch)))[1:]

        if color is None:
            dcolor = Colors.YELLOW
            if self.evencolor:
                dcolor = Colors.CYAN
            self.evencolor = not self.evencolor
        else:
            dcolor = Colors.get_color(color) 
            

        self.data.append([newdata, dcolor])

    def resize(self):
        #Removes the top 1/4 of the data elements in the panel
        start = len(self.data)/4
        self.data = self.data[start:]


"""
    ChopShopCurses is an abstracted interface to the curses-based ui -- it is the class that is used by ChopUiStd
    and its corresponding gui function. This class exists to abstract out the threaded nature of the curses class

"""

class ChopShopCurses:
    def __init__(self, ui_stop_fn, lib_stop_fn):
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)


        self.nui = ChopCurses(self.stdscr, ui_stop_fn, lib_stop_fn)    
    
    def add_panel(self, panel_id, name):
        self.nui.add_panel(panel_id,name)

    def add_data(self, panel_id, data, color):
        self.nui.add_data(panel_id, data, color)

    def teardown(self):
        self.stdscr.keypad(0)
        curses.nocbreak() 
        curses.echo() 
        curses.endwin()

    def join(self):
        while self.nui.is_alive(): #loop so signals still work
            self.nui.join(.1)
        self.teardown()
        CSD.debug_out("ChopShopCurses join complete\n")

    def stop(self):
        CSD.debug_out("ChopShopCurses stop called\n")
        self.nui.stop()#should run once more then quit
        self.nui.join()
        self.teardown()
        CSD.debug_out("ChopShopCurses stop complete\n")

 
    def go(self):
        self.nui.start()

"""
    This is the actual ui implementation and it utilizes ncurses to display a terminal GUI.

    As it stands the UI displays a title window at the top, a left-hand side navigation window and the rest of the space
    is used to display the data for a given "window" or "panel"

    The following keys are supported:
   
    Left  or h: Cycles to the "left" window (the window above in the navigation window)
    Right or l: Cycles to the "right" window (the window below in the navigation window)
    Up    or k: Moves up one line in the data display window
    Down  or j: Moves down one line in the data display window
    PgDwn or J: Moves down 10 lines in the data display window
    PgUp  or K: Moves up 10 lines in the data display window
             b: Moves to the beginning line in the data display window
             n: Moves to the end line in the data display window 
             s: Toggles autoscroll for the given data display window -- default is True
             q: Quits the UI -- also halts execution of the core
             Q: Quits the core -- leaves the UI up and running

"""


class ChopCurses(Thread):
    dlines = 0
    dcols = 0
    dyval = 0
    dxval = 0

    nlines = 0
    ncols = 0
    nyval = 0
    nxval = 0

    stdscr = 0

    panels = {} #Since ids are not just positive integers need a dictionary
    panel_id_list = [] #A list of ordered panel ids -- to make it easier to switch
    current_win = 0 #The index in panel_id_list
    
    title_window = 0
    nav_window = 0
    data_window = 0

    #Seed to termios.TIOCCWINSZ to get H,W
    seed = struct.pack("HH", 0,0) 

    def __init__(self, stdscr, ui_stop_fn, lib_stop_fn):
        Thread.__init__(self)
        #self.started = False
        self.colors = False
        self.stopped = False
        self.stdscr = stdscr
        self.ui_stop_fn = ui_stop_fn
        self.lib_stop_fn = lib_stop_fn

        global Colors

        if curses.has_colors():
            self.colors = True
            Colors.define_colors(True)

        #Colors is color safe, if colors are not available it will be equal to
        #curses.A_NORMAL
        self.titlecolor = Colors.RED
        self.navcolor = Colors.MAGENTA 

    def __current_panel__(self):
        if len(self.panel_id_list) == 0:
            return vpanel("dummy")

        return self.panels[self.panel_id_list[self.current_win]]

    def stop(self):
        self.stopped = True

    def run(self):
        self.calculate_dimensions()
        self.windowH = curses.LINES
        self.windowW = curses.COLS

        self.title_window = curses.newwin(1,0,0,0)
        self.nav_window = curses.newwin(self.nlines, self.ncols, self.nyval, self.nxval)
        #Create the pad window
        self.data_window = curses.newpad(BUFFER_SIZE, self.dcols)
        self.data_window.keypad(1)
        self.data_window.timeout(100) #100 ms

        self.update_title()
        self.update_windows()

        counter = time.time()
        #self.started = True
        while not self.stopped:
            c = self.data_window.getch()

            self.check_resize_ui()
            #Update every 1 seconds
            newtime = time.time()
            if newtime - counter >= 1 :
                counter = newtime
                if self.__current_panel__().autoscroll:
                    self.scroll_end()

                #check to see if window has been resized
                if not self.check_resize_ui():
                    self.update_windows()

            if not self.handle_input(c):
                break

    def handle_input(self, c):
        if (c == -1): #means the timeout was reached and no key was received
            return True
        if (c == curses.KEY_RESIZE):#Due to timeout and whatnot this event is not always received
            self.resize_ui(False)
        elif (c == curses.KEY_LEFT or c == ord('h')):
            if self.current_win != 0:
                self.current_win -= 1
                self.update_windows()
        elif (c == curses.KEY_RIGHT or c == ord('l')):
            if self.current_win != len(self.panel_id_list) - 1:
                self.current_win += 1
                self.update_windows()
        elif (c == curses.KEY_UP or c == ord('k')):
            if self.__current_panel__().position > 0:
                self.__current_panel__().position -= 1
                self.update_pad_simple()
        elif (c == curses.KEY_DOWN or c == ord('j')):
            if self.__current_panel__().position < BUFFER_SIZE:
                self.__current_panel__().position += 1
                self.update_pad_simple()
        elif (c == curses.KEY_NPAGE or c == ord('J')):
            if self.__current_panel__().position >= BUFFER_SIZE - 10:
                self.__current_panel__().position = BUFFER_SIZE
            else:
                self.__current_panel__().position += 10
            self.update_pad_simple()
        elif (c == curses.KEY_PPAGE or c == ord('K')):
            if self.__current_panel__().position <= 10:
                self.__current_panel__().position = 0
            else:
                self.__current_panel__().position -= 10
            self.update_pad_simple()
        elif (c == ord('b')): #scroll to the beginning
            self.__current_panel__().position = 0
            self.update_pad_simple()
        elif (c == ord('n')): #scroll to the end
            self.scroll_end()
            self.update_pad_simple()
        elif (c == ord('s')):#Toggles autoscrolling -- by default this is enabled
            if self.__current_panel__().autoscroll:
                self.__current_panel__().autoscroll = False
            else:
                self.__current_panel__().autoscroll = True
        elif (c == ord('q')):
            try:
                self.lib_stop_fn()
            except Exception, e:
                pass

            try:
                self.ui_stop_fn()
            except Exception, e:
                #TODO
                pass
            return False
        elif (c == ord('Q')):
            #Stop the Core
            try:
                self.lib_stop_fn()
            except:
                pass
        else:
            if c != -1:
                CSD.debug_out("Unknown Key\n")

        return True

    def add_panel(self, panel_id, name):
        ndvwin = vpanel(name)
        self.panels[panel_id] = ndvwin

        current_key = None
        if len(self.panel_id_list) > self.current_win:
            current_key = self.panel_id_list[self.current_win]
            
        self.panel_id_list = []
        for j in self.panels.iterkeys():
            self.panel_id_list.append(j)

        self.panel_id_list = sorted(self.panel_id_list)
            
        if current_key is not None: #Need to update the key
            for i in range(len(self.panel_id_list)):
                if self.panel_id_list[i] == current_key:
                    self.current_win = i
        

        #self.update_navigation()
        #self.update_windows()
       
        #if self.started:
        #    self.update_navigation() 

        #return ndvwin


    def add_data(self, panel_id, data, color):
        self.panels[panel_id].add_data(data, color)

    def check_resize_ui(self):
        try:
            (h,w) = self.check_term_size()
        except:
            CSD.debug_out("Exception in check_term_size\n")
            raise

        if (w != self.windowW) or (h != self.windowH):
            self.windowW = w
            self.windowH = h
            self.resize_ui(True)
            return True

        return False
        

    def resize_ui(self, use_self, attempts = 0):

        CSD.debug_out("Resize Called (" + `attempts` +") -\n\t" + `curses.LINES` + " " + `curses.COLS` + "\n")

        if use_self: #there's no need to do another lookup if called by check_resize_ui
            (w,h) = (self.windowW, self.windowH)
        else:
            try:
                (h,w) = self.check_term_size()
            except:
                CSD.debug_out("Exception in check_term_size\n")
                raise

        CSD.debug_out("\t" + `h` + " " +`w` + "\n")

        if(curses.COLS == w and curses.LINES == h):
            return

        (curses.COLS, self.windowW) = (w,w)
        (curses.LINES,self.windowH) = (h,h)

        #clear all of the windows
        self.stdscr.clear()
        self.nav_window.clear()
        self.title_window.clear()
        self.data_window.clear()

        #Need to refresh to remove extraneous characters that might be leftover
        self.nav_window.nooutrefresh()
        self.title_window.nooutrefresh()
        self.stdscr.nooutrefresh()

        #Get the new dimensions of the navigation and data windows
        self.calculate_dimensions()

        CSD.debug_out("Resizing Nav - " + `curses.LINES - 2` + " " + `curses.COLS/8` + "\n")

        #Resize Windows
        self.title_window.resize(1,curses.COLS)
        self.nav_window.resize(self.nlines, self.ncols)
        self.data_window.resize(BUFFER_SIZE, self.dcols)

        self.update_title()
            
        #Reset autoscroll on all panels
        for key in self.panel_id_list:
            self.panels[key].autoscroll = True

        #Attempt to refresh the windows
        #if it fails, retry up to 5 times -- haven't seen it make it higher than 3
        try:
            self.update_windows()
        except curses.error:
            if(attempts > 5):
                raise 
            self.resize_ui(False, attempts + 1)

    def calculate_dimensions(self):
        self.dlines = curses.LINES - 3
        self.dcols = ((curses.COLS/8) * 7) - 3
        self.dyval = 2
        self.dxval = (curses.COLS/8) + 2

        self.nlines = curses.LINES - 2
        self.ncols = curses.COLS/8
        self.nyval = 1
        self.nxval = 0

    def scroll_end(self): #scrolls to the end of the data_window
        #Scrolls to the "end"
        CSD.debug_out("Window positions Y,X: %u, %u\n" % self.data_window.getyx())
        (y, x) = self.data_window.getyx() # get current position of cursor

        end = y
        end_pos = 0
        if end - self.dlines > 0:
            end_pos = end - ((self.dlines/16) * 15) #arbitrarily 15/16 of the screen

        if end_pos > BUFFER_SIZE:
            end_pos = BUFFER_SIZE

        CSD.debug_out("Setting end position to: " + str(end_pos) + "\n")

        self.__current_panel__().position = end_pos

    def update_windows(self):
        CSD.debug_out("Updating Window\n")
        self.update_navigation()
        self.update_pad()

    def update_title(self):
        self.title_window.addstr("ChopShop", self.titlecolor)
        self.title_window.nooutrefresh()
    
    def update_navigation(self):
        self.nav_window.erase()
        self.nav_window.addstr(1,1, "Navigation Window\n\n", self.navcolor)

        for i in range(len(self.panel_id_list)):
            standout = curses.A_NORMAL
            if i == self.current_win and self.colors:
                standout = Colors.BLACK

            self.nav_window.addstr(" " + self.panels[self.panel_id_list[i]].windowname + "\n", standout)
        
        self.nav_window.border()

        try:
            self.nav_window.refresh()
        except:
            pass

    def update_pad_simple(self): #updates the view of the pad instead of the entire contents
        try:
            self.data_window.refresh(self.__current_panel__().position, 0, self.dyval, self.dxval, self.dlines, self.dxval + self.dcols)
        except:
            pass #get it on the next go


    def update_pad(self):
        self.data_window.erase()

        for data in self.__current_panel__().data:
            try:
                self.data_window.addstr(data[0], data[1])
            except:
                self.__current_panel__().resize()
                self.update_pad()
                return

        try:
            self.data_window.nooutrefresh(self.__current_panel__().position,0, self.dyval, self.dxval, self.dlines , self.dxval + self.dcols) 
            curses.doupdate()
        except:
            pass #get it on the next go


    def check_term_size(self):
        def check_term(tid):
            try:
                #Format should be Height, Width, X Pixels and Y Pixels
                #Can't figure out why, but TIOCGWINSZ requires an argument the size of what it's going to return
                #but doesn't actually modify it (which is how I'd write it)-- so if you want the (H) you give it 
                #one short, (H,W) two shorts (H,W,X) three shorts and (H,W,X,Y) four shorts 

                #Since I only care about the H,W I created a seed of two shorts
                hw = struct.unpack("HH", fcntl.ioctl(tid, termios.TIOCGWINSZ, self.seed))
            except:
                return None
            return hw 
        
        #Check the standard i/o's first
        hw = check_term(sys.stdin) or check_term(sys.stdout) or check_term(sys.stderr)
        
        if hw is None:
            try:
                #Try the controlling terminal
                tid = os.open(os.ctermid(), os.O_RDONLY)
                hw = check_term(tid)
                os.close(tid)    
            except:
                try:
                    #Try the env
                    hw = (os.environ['LINES'], os.environ['COLUMNS'])
                except:
                    #My default local windows size is 80x24 -- good enough for me!
                    #I mean either way this is a pretty last ditch effort case
                    #and hopefully shouldn't happen
                    hw = (24, 80) 

        return hw

########NEW FILE########
__FILENAME__ = ChopShopDebug
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from threading import Lock, Thread
import threading
import time

""" 
    ChopShop Debug Helper DO NOT MODIFY -- DO NOT TOUCH -- DO NOT USE
    This code should not be used in day to day and should not be used by any modules
    It's sole usage is for debugging the core of ChopShop where exception handling can get
    tricky (mainly with threads)

"""

DEBUG = False

def enable_debug(output = None):
    global DEBUG
    global df
    global dbglock

    DEBUG = True
    debugfile = 'debugout'
    dbglock = Lock()

    if output is not None:
        debugfile = output

    df = open(debugfile, 'w')

def debug_out(output):
    global DEBUG

    if DEBUG:
        global df
        global dbglock
        dbglock.acquire()
        try:
            df.write(output)
            df.flush()
        finally:
            dbglock.release()

class ThreadWatcher(Thread):
    daemon = True
    def __init__(self, interval):
        Thread.__init__(self, name="Watcher")
        self.interval = interval

    def run(self):
        while True:
            thread_list = []
            for thread in threading.enumerate():
                thread_list.append(thread.name)
            print("%d active threads: %s" % (threading.active_count(), ', '.join(thread_list)))
            time.sleep(self.interval)
         

########NEW FILE########
__FILENAME__ = ChopSurgeon
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

#shop/ChopSurgeon


import sys
import os
import time
import tempfile
from multiprocessing import Process, Queue
from ChopSuture import Suture

import ChopShopDebug as CSD

class Surgeon:
    def __init__(self, files, long = False):
        self.files = files
        self.fifo = None
        self.tdir = None
        self.fname = None
        self.long = long
        self.tosurgeon = Queue()

    def __del__(self):
        self.cleanup_fifo()
        try:
            self.tosurgeon.close()
        except:
            pass

    def create_fifo(self):
        self.tdir = tempfile.mkdtemp()
        self.fname = os.path.join(self.tdir, 'chopfifo')

        try:
            os.mkfifo(self.fname)
        except OSError, e:
            print "Unable to create fifo: " + str(e)
            sys.exit(-1)

       
        return self.fname 

    def cleanup_fifo(self):
        if self.fifo is not None:
            self.fifo.close()
        if self.fname is not None:
            os.remove(self.fname)
        if self.tdir is not None:
            os.rmdir(self.tdir)


    def stop(self):
        #Forcefully Terminate since otherwise this might hang unnecessarily
        try:
            self.tosurgeon.put('kill')
            self.p.terminate()
            self.p.join()
        except Exception, e:
            pass

    def abort(self):
        try:
            self.tosurgeon.put('abort')
        except Exception, e:
            pass

    def operate(self, flist = False):
        if flist:
            self.p = Process(target=self.__surgeon_proc_list_, args = (self.files[0], self.fname, self.long, self.tosurgeon,)) 
        else:
            self.p = Process(target=self.__surgeon_proc_, args = (self.files, self.fname,))
        self.p.start()

    def __surgeon_proc_(self, files, fname):
        os.setpgrp()
        suture = Suture(files, False, fname)
        suture.process_files()

    def __surgeon_proc_list_(self, file, fname, long, inq):
        os.setpgrp()
        self.stopread = False
        self.long = long

        try:
            flist = open(file, 'r')
        except:
            return

        suture = Suture([], False, fname)
        suture.prepare_bunch()
        while(not self.stopread):
            files = []
            while(True):
                data = None
                try:
                    data = inq.get(True, .01)
                except Queue.Empty:
                    pass

                if data == 'abort':
                    self.long = False
                elif data == 'kill':
                    self.stopread = True

                line = flist.readline()
                if line == "":
                    break
                files.append(line[0:-1])

            if len(files) > 0:
                suture.process_bunch(files)

            if not self.long:
                break
            time.sleep(.1)

        flist.close()
        suture.end_bunch()

########NEW FILE########
__FILENAME__ = ChopSuture
#! /usr/bin/python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

#shop/ChopSuture


import sys
import os
import struct
import time

	

class Suture:
    def __init__(self,files,verbose, output):
        self.filelist = []
        self.verbose = verbose
        self.outfile = None
        self.output = output
        self.halt = False
        self.first = False
        self.linktype = -1
        self.native = None


        for file in files:
            file = file.rstrip()
            self.filelist.append(file)

        if self.output != '-': #outputting to a file
            if verbose:
                vstring = "Writing to file: " + self.output + "\n"
                sys.stderr.write(vstring)

    
    def stop(self):
        self.halt = True
    
    def process_file(self, file):
        if self.halt: #Stop processing 
            return
        swap_bytes = False
        if self.verbose:
            vstring = "Reading file " + file + "\n"
            sys.stderr.write(vstring)

        infile = open(file,'rb')

        indata = ""
        
        #Read in Global Header - 24 bytes
        hdrinfo = infile.read(24)
        if len(hdrinfo) != 24:
            if self.verbose:
                vstring = "Skipping file " + file + " due to small header\n"
                sys.stderr.write(vstring)
            infile.close()
            return
        #Figure out what endian this file's headers are in
        #Try out little endian
        mn_little = struct.unpack('<I',hdrinfo[0:4])[0]

        if mn_little == 0xa1b2c3d4: #It's little endian
            file_order = '<'
        elif mn_little == 0xd4c3b2a1: #it's big endian
            file_order = '>'
        else: # It's neither
            if self.verbose:
                vstring = "Skipping file " + file + ". Appears to not be pcap\n"
                sys.stderr.write(vstring)
            infile.close()
            return

        if self.native == None: #first file
            self.native = file_order
        else: #we need to see if subsequent fields need to be switched
            if self.native != file_order: #the order of the file is not the order of the first file
                swap_bytes = True #we'll have to swap the packet header fields for subsequent packets


        #Check the link layer type and skip the file if not the same
        hdr_nw = struct.unpack( file_order + 'I',hdrinfo[20:24])[0]

        if not self.first:
            self.first = True
            indata = hdrinfo
            self.linktype = hdr_nw
        else:
            if hdr_nw != self.linktype:
                if self.verbose:
                    vstring = "Skipping file " + file + " due to link type\n"
                    sys.stderr.write(vstring)
                infile.close()
                return 

        #For Reference
        #hdr_mn = struct.unpack('I',hdrinfo[0:4])[0]
        #hdr_vs = struct.unpack('I',hdrinfo[4:8])[0]
        #hdr_tz = struct.unpack('I',hdrinfo[8:12])[0]
        #hdr_sf = struct.unpack('I',hdrinfo[12:16])[0]
        #hdr_sl = struct.unpack('I',hdrinfo[16:20])[0]
        #hdr_nw = struct.unpack('I',hdrinfo[20:24])[0]

        try:
            if self.output == '-':
                sys.stdout.write(indata)
            else:
                self.outfile.write(indata)
        except Exception, e:
            if self.verbose:
                vstring = "Exception writing header: %s\n" % str(e)
                sys.stderr.write(vstring)
            sys.exit(-1)

        #Now let's process each packet in the file
        while True:
            #First read in the packet header - 16 bytes
            phdr = infile.read(16)
            if len(phdr) < 16:
                break

            #Let's get the header into the same endian the first file was using
            if swap_bytes:
                nhdr = self.swapbytes(phdr[0:4]) + self.swapbytes(phdr[4:8]) + self.swapbytes(phdr[8:12]) + self.swapbytes(phdr[12:16])
                phdr = nhdr

            #After we swap bytes the header should be in our "native" order

            phd_inc = struct.unpack(self.native + 'I',phdr[8:12])[0]

            #For Reference
            #phd_tss = struct.unpack('I',phdr[0:4])[0]
            #phd_tsu = struct.unpack('I',phdr[4:8])[0]
            #phd_inc = struct.unpack('I',phdr[8:12])[0]
            #phd_orl = struct.unpack('I',phdr[12:16])[0]

            pdata = infile.read(phd_inc)
            #If there's not enough data in the file then more than likely this pcap is truncated
            if len(pdata) < phd_inc:
                break

            indata = (phdr + pdata)

            try:
                if self.output == '-':
                    sys.stdout.write(indata)
                else:
                    self.outfile.write(indata)
            except Exception, e:
                if self.verbose:
                    vstring = "Exception writing header: %s\n" % str(e)
                    sys.stderr.write(vstring)
                infile.close()
                sys.exit(-1)

        infile.close()

    def process_files(self):
        if self.output != '-':
            self.outfile = open(self.output,'w')

        for file in self.filelist:
            self.process_file(file)

        if self.output != '-':
            self.outfile.close


    def prepare_bunch(self):
        if self.output != '-':
            self.outfile = open(self.output, 'w')

    def process_bunch(self, filelist):
        for file in filelist:
            file = file.rstrip()
            self.process_file(file) 


    def end_bunch(self):
        if self.output != '-':
            self.outfile.close


    def swapbytes(self, byte_arr):
        #we're swapping endians, easiest way is to unpack in any endian
        #and repack with the opposite endian -- assumed 4 bytes

        temp = struct.unpack('>I',byte_arr)[0]
        out = struct.pack('<I',temp)

        return out


########NEW FILE########
__FILENAME__ = ChopUi
#! /usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import sys
import os
from threading import Thread, Lock
import Queue

CHOPSHOP_WD = os.path.realpath(os.path.dirname(sys.argv[0]))

if CHOPSHOP_WD + '/shop' not in sys.path:
    sys.path.append(CHOPSHOP_WD + '/shop')

from ChopException import * 
from ChopUiStd import *
import ChopShopDebug as CSD

"""
    ChopUi is the ui library interface to allow for automated data output from ChopLib
    It relies on a queue of information that it can use and parse to determine where output needs to go
    ChopUi instatiates a class for every output capability. For example, output to stdout is handled by ChopStdout
    which is located in ChopUiStd. This allows for the usage of output capabilites to be modular. If for example,
    you would like to replace the Stdout functionality, but do not want to rewrite this library, you can pass in the class
    you would like to replace stdout with and ChopUi will use that instead
"""

class ChopUi(Thread):
    def __init__(self):
        Thread.__init__(self, name = 'ChopUi')


        self.options = { 'stdout'   : False,
                         'gui'      : False,
                         'fileout'  : False,
                         'filedir'  : None,
                         'savedir'  : None,
                         'savefiles': False,
                         'jsonout'  : False,
                         'jsondir'  : None,
                         'pyobjout' : False
                       }

        self.stopped = False
        self.isrunning = False
        self.message_queue = None
        self.lib_stop_fn = None
        self.stdclass = None
        self.uiclass = None
        self.fileoclass = None
        self.jsonclass = None
        self.filesclass = None
        self.pyobjclass = None

    @property
    def stdout(self):
        """Output to stdout"""
        return self.options['stdout']

    @stdout.setter
    def stdout(self, v):
        self.options['stdout'] = v

    @property
    def pyobjout(self):
        return self.options['pyobjout']

    @pyobjout.setter
    def pyobjout(self, v):
        self.options['pyobjout'] = v

    @property
    def gui(self):
        """Output to a gui"""
        return self.options['gui']

    @gui.setter
    def gui(self, v):
        self.options['gui'] = v

    @property
    def fileout(self):
        """Output to files"""
        return self.options['fileout']

    @fileout.setter
    def fileout(self, v):
        self.options['fileout'] = v

    @property
    def filedir(self):
        """Directory format string to save files to"""
        return self.options['filedir']

    @filedir.setter
    def filedir(self, v):
        self.options['filedir'] = v


    @property
    def savedir(self):
        """Directory format string to save output files to"""
        return self.options['savedir']

    @savedir.setter
    def savedir(self, v):
        self.options['savedir'] = v


    @property
    def savefiles(self):
        """Handle the saving of files"""
        return self.options['savefiles']

    @savefiles.setter
    def savefiles(self, v):
        self.options['savefiles'] = v

    @property
    def jsonout(self):
        """Handle the output of JSON data"""
        return self.options['jsonout']

    @jsonout.setter
    def jsonout(self, v):
        self.options['jsonout'] = v

    @property
    def jsondir(self):
        """Directory format string to save json to"""
        return self.options['jsondir']

    @jsondir.setter
    def jsondir(self, v):
        self.options['jsondir'] = v

    def set_message_queue(self, message_queue):
        self.message_queue = message_queue

    def set_library_stop_fn(self, lib_stop_fn):
        self.lib_stop_fn = lib_stop_fn

    def bind(self, cl_instance):
        #TODO exception
        self.set_message_queue(cl_instance.get_message_queue())
        self.set_library_stop_fn(cl_instance.get_stop_fn())

    def stop(self):
        CSD.debug_out("ChopUi stop called\n")
        self.stopped = True
        #if self.lib_stop_fn is not None:
        #    self.lib_stop_fn()

    def run(self):
        try:
            if self.options['stdout'] == True:
                self.stdclass = ChopStdout()
                #Assign the default stdout handler
            elif self.options['stdout'] != False:
                self.stdclass = self.options['stdout']()
                #Override the default handler with this one

            if self.options['gui'] == True:
                self.uiclass = ChopGui(self.stop, self.lib_stop_fn)
            elif self.options['gui'] != False:
                self.uiclass = self.options['gui'](self.stop, self.lib_stop_fn)

            if self.options['fileout'] == True:
                self.fileoclass = ChopFileout(format_string = self.options['filedir'])
            elif self.options['fileout'] != False:
                self.fileoclass = self.options['fileout'](format_string = self.options['filedir'])

            if self.options['jsonout'] == True:
                self.jsonclass = ChopJson(format_string = self.options['jsondir'])
            elif self.options['jsonout'] != False:
                self.jsonclass = self.options['jsonout'](format_string = self.options['jsondir'])

            if self.options['savefiles'] == True:
                self.filesclass = ChopFilesave(format_string = self.options['savedir'])
            elif self.options['savefiles'] != False:
                self.filesclass = self.options['savefiles'](format_string = self.options['savedir'])

            if self.options['pyobjout'] == True:
                self.pyobjclass = None #No default handler Should throw exception
            elif self.options['pyobjout'] != False:
                self.pyobjclass = self.options['pyobjout']()
        except Exception, e:
            raise ChopUiException(e)

        while not self.stopped:

            try:
                message = self.message_queue.get(True, .1)
            except Queue.Empty, e:
                continue


            try:
                if message['type'] == 'ctrl':
                    try:
                        if self.stdclass is not None:
                            self.stdclass.handle_ctrl(message)
                    except Exception, e:
                        raise ChopUiStdOutException(e)
                    try:
                        if self.uiclass is not None:
                            self.uiclass.handle_ctrl(message)
                    except Exception, e:
                        raise ChopUiGuiException(e)
                    try:
                        if self.fileoclass is not None:
                            self.fileoclass.handle_ctrl(message)
                    except Exception, e:
                        raise ChopUiFileOutException(e)
                    try:
                        if self.jsonclass is not None:
                            self.jsonclass.handle_ctrl(message)
                    except Exception, e:
                        raise ChopUiJsonException(e)
                    try:
                        if self.filesclass is not None:
                            self.filesclass.handle_ctrl(message)
                    except Exception, e:
                        raise ChopUiFileSaveException(e)
                    try:
                        if self.pyobjclass is not None:
                            self.pyobjclass.handle_ctrl(message)
                    except Exception, e:
                        raise ChopUiPyObjException(e)

                    #The GUI is the only thing that doesn't care if the core is no
                    #longer running
                    if message['data']['msg'] == 'finished' and self.uiclass is None:
                        self.stop()
                        continue

            except ChopUiException:
                raise
            except Exception, e:
                raise ChopUiException(e)

            try:
                if message['type'] == 'text':
                    try:
                        if self.stdclass is not None:
                            self.stdclass.handle_message(message)
                    except Exception, e:
                        raise ChopUiStdOutException(e)
                    try:
                        if self.uiclass is not None:
                            self.uiclass.handle_message(message)
                    except Exception, e:
                        raise ChopUiGuiException(e)
                    try:
                        if self.fileoclass is not None:
                            self.fileoclass.handle_message(message)
                    except Exception, e:
                        raise ChopUiFileOutException(e)

                if message['type'] == 'json':
                    try:
                        if self.jsonclass is not None:  
                            self.jsonclass.handle_message(message)
                    except Exception, e:
                        raise ChopUiJsonException(e)
                
                if message['type'] == 'filedata':
                    try:
                        if self.filesclass is not None:
                            self.filesclass.handle_message(message) 
                    except Exception, e:
                        raise ChopUiFileSaveException(e)

                if message['type'] == 'pyobj':
                    try:
                        if self.pyobjclass is not None:
                            self.pyobjclass.handle_message(message)
                    except Exception, e:
                        raise ChopUiPyObjException(e)

            except ChopUiException:
                raise
            except Exception, e:
                raise ChopUiException(e)

        if self.stdclass is not None:
            self.stdclass.stop()
        if self.uiclass is not None:
            self.uiclass.stop()
        if self.fileoclass is not None:
            self.fileoclass.stop()
        if self.jsonclass is not None:
            self.jsonclass.stop()
        if self.filesclass is not None:
            self.filesclass.stop()
        if self.pyobjclass is not None:
            self.pyobjclass.stop()


########NEW FILE########
__FILENAME__ = ChopUiStd
#!/usr/bin/env python

# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.


import time
import os
import sys

CHOPSHOP_WD = os.path.realpath(os.path.dirname(sys.argv[0]))

if CHOPSHOP_WD + '/shop' not in sys.path:
    sys.path.append(CHOPSHOP_WD + '/shop')


import ChopShopDebug as CSD
from ChopException import ChopLibException

"""
        __parse_filepath__ parses a pseudo format-string passed on the commandline to figure out
        what the output filepath should be. It currently support the following variables:

        %N - The name of the module
        %T - The current unix timestamp
        %% - A literal '%'

        This function, when given a path string will replace any variables with the current local value
        and create a static path string that can be used to create a file or directory to output data

        For example if the user passes in "output/%N/%T.txt" and the name of the module is "foobar"
        and the current timestamp is 123456789 the resultant output would be:

        "output/foobar/123456789.txt"

        Or if used with the save file functionality if the user passes in "/tmp/%N/" and the module is named "foobar"
        the output directory would be:

        "/tmp/foobar/"

        It takes an optional fname paramter which is the literal filename to append to the crafted filepath
"""


def __parse_filepath__(format, modname, fname = None): #the format, the module name, the requested filename
    default_path = "./" #default to local working directory
    default_filename = modname + "-" + str(int(time.time())) + ".txt"

    filename = ""

    if format == "": #If they passed in an empty string use defaults
        #default filename
        filename = default_path
        if fname is None:
            filename += default_filename

    else:#let's go through the format and craft the path
        start = 0
        while True:
            #ind is the index where we find '%'
            ind = format.find('%',start)

            if ind == -1: #no ind found, just copy the rest of the string
                filename += format[start:]
                break

            #copy everything before the % straight in
            filename += format[start:ind]

            #Now let's process the flag if there is one
            if (ind + 1) > (len(format) - 1): #the % is the last element
                return None #improper formatting so let's return None
            else:

                flag = format[ind + 1]# the next character is the flag
                if flag == 'N':
                    filename += modname
                elif flag == 'T':
                    filename += str(int(time.time()))
                elif flag == '%':
                    filename += '%' #put in a literal %
                else:
                    return None #unknown or unsupported flag

            #move past the % and the flag
            start = ind + 2

        #if passed in an explicit filename concat it with what we've crafted
        #XXX Should we worry about directory traversal?
        if fname is not None:
            if filename[-1] != '/': #add a slash to the filepath if not already there
                filename += '/'
            filename += fname
   
    return filename 


#XXX Add the capability to disable the creation of directories (or the flipside
#### don't create by default and add the capability to create)

def __get_open_file__(modname, format, create, fname=None, mode = 'w'):
    filename = __parse_filepath__(format, modname, fname)
    fdval = None
    error = ""

    if create:
        dname = os.path.dirname(filename)
        if dname and not os.path.exists(dname):
            try:
                os.makedirs(dname, 0775)
            except Exception, e:
                error = "Directory Creation Error: %s " % e
    
    try:
        fd = open(filename, mode)
        fdval = fd
    except IOError, e:
        if error == "":
            error = "File Creation Error: %s " % e

    return (fdval,error)


class ChopStdout:

    prepend_module_name     = False
    prepend_proto           = False
    prepend_address         = False

    def __init__(self, ui_stop_fn = None, lib_stop_fn = None):
        #Stdout doesn't need the two functions
        pass

    def handle_message(self, message):
        outstring = ""
        
        if self.prepend_module_name:
            outstring = outstring + message['module'] + " "

        if self.prepend_proto and message['proto'] != '':
            outstring = outstring + message['proto'] + " "

        if self.prepend_address and message['addr']['src'] != '':
            outstring = outstring + message['addr']['src'] + ":" + message['addr']['sport'] + "->" + message['addr']['dst'] + ":" + message['addr']['dport'] + " "

        outstring = outstring + message['data']['data']
        suppress = message['data']['suppress']
        if suppress:
            print outstring,
        else:
            print outstring

    def handle_ctrl(self, message):
        if message['data']['msg'] == 'finished' and message['data']['status'] == 'error':
            print message['data']['errors']
            raise ChopLibException("Error Shown Above")

    def stop(self):
        pass

class ChopGui:
    def __init__(self, ui_stop_fn = None, lib_stop_fn = None):
        from ChopShopCurses import ChopShopCurses

        self.cui = ChopShopCurses(ui_stop_fn, lib_stop_fn)
        self.cui.go()

    def handle_message(self, message):
        if message['data']['suppress']:
            newline = ""
        else:
            newline = "\n"

        self.cui.add_data(message['id'], message['data']['data'] + newline, message['data']['color'])         

    def handle_ctrl(self, message):
        if message['data']['msg'] == 'addmod':
            self.cui.add_panel(message['data']['id'],message['data']['name'])

        if message['data']['msg'] == 'finished' and message['data']['status'] == 'error':
            self.stop()
            raise ChopLibException(message['data']['errors'])
    
    def stop(self):
        CSD.debug_out("ChopGui stop called\n")
        self.cui.stop()
        self.cui.join()

class ChopFileout:
    
    format_string = None

    def __init__(self, ui_stop_fn = None, lib_stop_fn = None, format_string = None):
        self.filelist = {}
        if format_string is not None:
            self.format_string = format_string

        if format_string[0] == '-':
            raise Exception("Ambiguous file format: '" + format_string + "' -- please fix and run again\n")
        
        if __parse_filepath__(format_string, "placeholder") is None:
            raise Exception("Invald syntax for file output\n")
        
         
    def handle_message(self, message):
        if message['id'] not in self.filelist:
            (fd, error) = __get_open_file__(message['module'], self.format_string, True)
            if fd is not None:
                self.filelist[message['id']] = fd
            else:
                #TODO exception
                pass

        self.filelist[message['id']].write(message['data']['data'])
        if not message['data']['suppress']:
            self.filelist[message['id']].write("\n")
        self.filelist[message['id']].flush()

    def handle_ctrl(self, message):
        pass

    def stop(self):
        pass

class ChopJson:

    format_string = None

    def __init__(self, ui_stop_fn = None, lib_stop_fn = None, format_string = None):
        self.filelist = {}
        if format_string is not None:
            self.format_string = format_string

        if format_string[0] == '-':
            raise Exception("Ambiguous file format: '" + format_string + "' -- please fix and run again\n")
        
        if __parse_filepath__(format_string, "placeholder") is None:
            raise Exception("Invald syntax for json output\n")

        pass

    def handle_message(self, message):
        if message['id'] not in self.filelist: #not already created
            (jd,error) = __get_open_file__(message['module'], self.format_string, True)
            if jd is not None:
                self.filelist[message['id']] = jd
            else:
                #TODO except or otherwise?
                pass

        self.filelist[message['id']].write(message['data']['data'] + "\n")
        self.filelist[message['id']].flush()

    def handle_ctrl(self, message):
        pass

    def stop(self):
        #Cleanup and close any files
        for j,k in self.filelist.iteritems():
            k.close()

class ChopFilesave:
    def __init__(self, ui_stop_fn = None, lib_stop_fn = None, format_string = None):
        self.format_string = format_string
        self.savedfiles = {}
        
        if format_string[0] == '-':
            raise Exception("Ambiguous file format: '" + format_string + "' -- please fix and run again\n")
        
        if __parse_filepath__(format_string, "placeholder") is None:
            raise Exception("Invald syntax for savedir\n")

        pass
   
    def handle_message(self, message):
        filename = message['data']['filename']

        if message['data']['data'] != "":
            #Only if there's data to write
            if not self.savedfiles.has_key(filename):
                try:
                    (self.savedfiles[filename], error) = __get_open_file__(message['module'], self.format_string,
                                                                            True, filename, 
                                                                            message['data']['mode'])

                finally:
                    pass

            if self.savedfiles[filename] is None:
                #TODO error
                del self.savedfiles[filename]
                return
                #pass

            self.savedfiles[filename].write(message['data']['data'])
            self.savedfiles[filename].flush()

        if message['data']['finalize'] and self.savedfiles.has_key(filename):
            self.savedfiles[filename].close()
            del self.savedfiles[filename]
            

    def handle_ctrl(self, message):
        pass

    def stop(self):
        for j,k in self.savedfiles.iteritems():
            k.close()

########NEW FILE########
__FILENAME__ = ChopWebServer
#!/usr/bin/env python
#
# Copyright (c) 2014 The MITRE Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
#WebServer/WebSocket Code taken from mod_pywebsocket available from
#http://code.google.com/p/pywebsocket/
#That code falls under the following copyright/license:
#
# Copyright 2012, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import BaseHTTPServer
import CGIHTTPServer
import SimpleHTTPServer
import SocketServer
import ConfigParser
import base64
import httplib
import logging
import logging.handlers
import optparse
import os
import re
import select
import socket
import sys
import threading
import traceback
from threading import Thread, Lock
import Queue
import time
import json
import cgi

from mod_pywebsocket import common
from mod_pywebsocket import dispatch
from mod_pywebsocket import handshake
from mod_pywebsocket import http_header_util
from mod_pywebsocket import memorizingfile
from mod_pywebsocket import util
from mod_pywebsocket import msgutil
from mod_pywebsocket import stream
from mod_pywebsocket import standalone

_DEFAULT_LOG_MAX_BYTES = 1024 * 256
_DEFAULT_LOG_BACKUP_COUNT = 5

_DEFAULT_REQUEST_QUEUE_SIZE = 128
_TRANSFER_DATA_HANDLER_NAME = 'web_socket_transfer_data'

# 1024 is practically large enough to contain WebSocket handshake lines.
_MAX_MEMORIZED_LINES = 1024

CHOPSHOP_WD = os.path.realpath(os.path.dirname(sys.argv[0]))

if CHOPSHOP_WD + '/shop' not in sys.path:
    sys.path.append(CHOPSHOP_WD + '/shop')

from ChopLib import ChopLib
from ChopConfig import ChopConfig
from ChopException import ChopUiException


class _Options():
    pass

class _ChopQueueTracker(Thread):
    def __init__(self):
        Thread.__init__(self, name = 'QueueTracker')
        self.queues = []
        self.message_queue = None
        self.stopped = False

        self.idlist = {}
        self.idcount = 0

        #Check queue type  
        #Throw exception if queue is not working


    def unset_queue(self):
        self.message_queue = None

    def set_queue(self, message_queue):
        if self.message_queue is not None:
            pass #there is already a message queue register
        self.message_queue = message_queue
    
    def get_new_queue(self):
        new_queue = Queue.Queue() 
        queue_id = len(self.queues)
        self.queues.append(new_queue)
        return (queue_id, new_queue)

    def remove_queue(self, queue_id):
        self.queues.remove(self.queues[queue_id])
        return

    def stop(self):
        self.stopped = True

    def run(self):
        while not self.stopped:
            if self.message_queue is None: #hasn't been set yet
                time.sleep(.2)
                continue

            try:
                message = self.message_queue.get(True, .1)
            except Queue.Empty, e:
                continue             

            
            try:
                #Since this can run choplib multiple times, need to
                #give each module a web unique id to use which won't overlap
                #across instantiations of choplib
                if message['type'] == 'ctrl' and message['data']['msg'] == 'addmod':
                    if message['data']['name'] not in self.idlist: #Hasn't been seen before
                        self.idlist[message['data']['name']] = self.idcount
                        self.idcount += 1
                    else: #It is, must update it
                        message['data']['id'] = int(self.idlist[message['data']['name']])


                if not(message['type'] == 'ctrl'):
                    message['id'] = int(self.idlist[message['module']])

                for qu in self.queues:
                    qu.put(message) 
            except Exception, e:
                raise ChopUiException(e)



class ChopWebUi(Thread):
    def __init__(self):
        Thread.__init__(self, name = 'ChopWebUi')

        self.options = _Options()

        self.options.server_host= ''
        self.options.validation_host = None
        self.options.port = 8080
        self.options.validation_port = None
        self.options.document_root = CHOPSHOP_WD + '/webroot/'
        self.options.request_queue_size = _DEFAULT_REQUEST_QUEUE_SIZE
        self.options.log_level = 'critical'
        self.options.log_file = ''
        self.options.deflate_log_level = 'warn'
        self.options.thread_monitor_interval_in_sec = -1
        self.options.allow_draft75 = False
        self.options.strict = False
        self.options.use_tls = False

        self.stopped = False
        self.message_queue = None
        self.queuetracker = None

    @property
    def server_host(self):
        """Address to listen on"""
        return self.options.server_host

    @server_host.setter
    def server_host(self, v):
        self.options.server_host= v


    @property
    def port(self):
        """Port to listen on"""
        return self.options.port

    @port.setter
    def port(self, v):
        self.options.port = v

    @property
    def document_root(self):
        return self.options.document_root

    @document_root.setter
    def document_root(self,v):
        self.options.document_root= v

    def stop(self):
        self.stopped = True
        self.server.shutdown()
        self.queuetracker.stop()
        self.choplibshell.stop()

    def run(self):
        #Based on mod_pywebsocket/standalone.py main function

        #Start the queue tracker
        self.queuetracker = _ChopQueueTracker()
        self.queuetracker.start()
        self.options.queuetracker = self.queuetracker

        self.choplibshell = _ChopLibShell(self.queuetracker)
        self.choplibshell.start()
        self.options.choplibshell = self.choplibshell

        _configure_logging(self.options)

        os.chdir(self.options.document_root)
        self.options.cgi_directories = []
        self.options.is_executable_method = None
        try:
            if self.options.thread_monitor_interval_in_sec > 0:
                # Run a thread monitor to show the status of server threads for
                # debugging.
                ThreadMonitor(self.options.thread_monitor_interval_in_sec).start()

            self.server = ChopWebSocketServer(self.options)
            self.server.serve_forever()
        except Exception, e:
            logging.critical('mod_pywebsocket: %s' % e)
            logging.critical('mod_pywebsocket: %s' % util.get_stack_trace())

class _ChopDataParser(object):
    def __init__(self, request, queuetracker):
        if queuetracker is None:
            raise Exception

        self.queuetracker = queuetracker
        (self.qid, self.my_queue) = queuetracker.get_new_queue()
        #TODO throw exceptions?

        self.request = request

    def send(self,message):
        self.request.ws_stream.send_message(message, binary = False)

    def go(self):
        while True:
            try:
                message = self.my_queue.get(True, .1)
            except Queue.Empty, e:
                continue

                    

            #TODO more efficient way of sanitization?
            if message['type'] == 'text':
                #message['data']['data'] = base64.urlsafe_b64encode(message['data']['data'])
                message['data']['data'] = message['data']['data'].replace("\"","\\\"")
                message['data']['data'] = message['data']['data'].replace("<","&lt;")
                message['data']['data'] = message['data']['data'].replace(">","&gt;")
                #message['data']['data'] = cgi.escape(message['data']['data'], quote = True)

            try:
                output = json.dumps(message)
            except:
                if message['type'] == 'text':
                    message['data']['data'] = "Parsing Error! -- Received non-character data"
                    output = json.dumps(message)
                else:
                    raise


            self.send(output)

    def cleanup(self):
        if self.qid is not None:
            self.queuetracker.remove_queue(self.qid)

    def __del__(self):
        self.cleanup()
         

class _ChopLibShellLiason(object):
    def __init__(self, request, choplibshell):
        self.request = request
        self.choplibshell = choplibshell
        self.associated = False

    def deassociate(self):
        self.associated = False

    def go(self):
        self.choplibshell.associate(self, self.request) 
        self.associated = True

        while self.associated:
            time.sleep(.1)


    def __del__(self):
        self.choplibshell.deassociate(self, self.request)


class _ChopLibShell(Thread):
    def __init__(self, queuetracker):
        Thread.__init__(self, name = 'ChopLibShell')
        self.request = None 
        self.liason = None
        self.queuetracker = queuetracker

        self.choplib = None
        self.stopped = False


    def associate(self, liason, request):
        if self.liason is not None:
            try:
                self.request = None
                self.liason.deassociate()
            except:
                pass

        self.liason = liason
        self.request = request

    def deassociate(self, liason, request):
        if self.liason == liason:
            self.request = None
            self.liason = None
   
    def _force_deassociate(self):
        if self.liason is not None:
            self.request = None
            self.liason = None

    def stop(self):
        if self.liason is not None:
            try:
                self.liason.deassociate()
            except:
                pass
        self.stopped = True

    def send_message(self, message):
        self.request.ws_stream.send_message(message, binary = False)

    def setup_choplib(self):
        if self.choplib is not None:
            self.destroy_choplib()

        self.choplib = ChopLib()
        self.choplib.text = True

        if self.queuetracker is None:
            raise Exception #queuetracker is managed by the the webui
        self.queuetracker.set_queue(self.choplib.get_message_queue())

    def setup_choplib_from_config(self, chopconfig):
        if self.choplib is not None:
            self.destroy_choplib()

        self.choplib = ChopLib()
        self.choplib.text = True

        if not os.path.exists(chopconfig.filename):
            raise ValueError("Unable to find file '%s'" % chopconfig.filename)
        self.choplib.filename = chopconfig.filename
        self.choplib.base_dir = chopconfig.base_dir
        self.choplib.mod_dir = chopconfig.mod_dir
        self.choplib.ext_dir = chopconfig.ext_dir
        self.choplib.aslist = chopconfig.aslist
        self.choplib.longrun = chopconfig.longrun
        self.choplib.modinfo = chopconfig.modinfo
        self.choplib.GMT = chopconfig.GMT
        self.choplib.bpf = chopconfig.bpf
        self.choplib.modules = chopconfig.modules
        #if chopconfig.savedir:
            #pass
            #chopui.savefiles = True
            #chopui.savedir = chopconfig.savedir
            #self.choplib.savefiles = True

        if self.queuetracker is None:
            raise Exception #queuetracker is managed by the the webui
        self.queuetracker.set_queue(self.choplib.get_message_queue())

    def destroy_choplib(self):
        self.queuetracker.unset_queue()
        if self.choplib is not None:
            self.choplib.stop()
            self.choplib = None

    def reset_choplib(self):
        options = self.choplib.options
        self.destroy_choplib()
        self.setup_choplib()
        self.choplib.options = options

    def run_module_info(self, modules):
        clib = ChopLib()
        clib.text = True
        clib.modules = modules
        clib.modinfo = True
        clib.start()

        stopped = False
        message_queue = clib.get_message_queue()

        while not stopped and clib.is_alive():
            try:
                message = message_queue.get(True, .1)
            except Queue.Empty, e:
                continue

            #clean up messages
            if message['type'] == 'ctrl':
                #self.send_message(message['data']['msg'] )
                if message['data']['msg'] == 'finished':
                    stopped = True
            elif message['type'] == 'text':
                self.send_message(message['data']['data'])

        clib.join()         
        del clib
        
    def help_message(self):
        output = ("Available Commands: \n" +
                "\tnew\n"+
                "\tnew_from_file\n"
                "\tdestroy\n"+
                "\trenew\n"+
                "\tset\n"+
                "\tget\n"+
                "\tlist_params\n" + 
                "\trun\n" +
                "\tstop\n"+ 
                "\tdisconnect\n")
                #"\tshutdown\n")
        return output
    
    def params_message(self):
        params_string = ("Avaiable params: \n" +
                    "\t base_dir \n"  +
                    "\t mod_dir \n" +
                    "\t ext_dir \n" +
                    "\t aslist \n" +
                    "\t longrun \n" +
                    "\t GMT \n" +
                    "\t modules \n" +
                    "\t interface \n" + 
                    "\t filename \n" +
                    "\t bpf \n" +
                    "\t filelist\n" )
        return params_string

    def choplib_get(self, param):
        if param == "all":
            outstring = ""
            for option,value in self.choplib.options.iteritems():
                outstring += option + ": " + str(value) + "\n"

            self.send_message(outstring)
        elif param == "base_dir":
            if self.choplib.base_dir is None:
                self.send_message("base_dir not set")
            else:
                self.send_message(self.choplib.base_dir)
        elif param == "mod_dir":
            self.send_message(self.choplib.mod_dir)
        elif param == "ext_dir":
            self.send_message(self.choplib.ext_dir)
        elif param == "aslist":
            self.send_message(str(self.choplib.aslist))
        elif param == "longrun":
            self.send_message(str(self.choplib.longrun))
        elif param == "GMT":
            self.send_message(str(self.choplib.GMT))
        elif param == "modules":
            self.send_message(self.choplib.modules)
        elif param == "interface":
            self.send_message(self.choplib.interface)
        elif param == "filename":
            self.send_message(self.choplib.filename)
        elif param == "bpf":
            if self.choplib.bpf is not None:
                self.send_message(self.choplib.bpf)
            else:
                self.send_message("bpf not set")
        elif param == "filelist":
            if not self.choplib.filelist:
                self.send_message("filelist not set")
            else:
                outstring = "["
                for f in self.choplib.filelist:
                    outstring += (f + ",")
                outstring = outstring[0:-1] + "]"
                self.send_message(outstring)
        
        
        else:
            self.send_message("Unknown Parameter")


    def choplib_set(self, param, value):
        error = False

        if param == "base_dir":
            self.choplib.base_dir = value
        elif param == "mod_dir":
            self.choplib.mod_dir = value
        elif param == "ext_dir":
            self.choplib.ext_dir = value
        elif param == "aslist":
            bval = False
            if value == 'True':
                bval = True

            self.choplib.aslist = bval
        elif param == "longrun":
            bval = False
            if value == 'True':
                bval = True

            self.choplib.longrun = bval
        elif param == "GMT":
            bval = False
            if value == 'True':
                bval = True
            self.choplib.GMT = bval
        elif param == "modules":
            self.choplib.modules = value
        elif param == "interface":
            self.choplib.interface = value
        elif param == "filename":
            self.choplib.filename = value
        elif param == "bpf":
            self.choplib.bpf = value
        elif param == "filelist":
            self.send_message("TBD")
        else:
            error = True
            self.send_message("Unknown Parameter")

        self.send_message('ok')

    def process_message(self, line):
        line = line.encode('ascii', 'ignore')

        #self.send_message("Echo: " + line)
        commands = line.split(' ', 1)
        if commands[0] == 'new':
            self.setup_choplib()
            self.send_message("Created new choplib instance")
        elif commands[0] == 'new_from_file':
            try:
                config = ChopConfig()
                config.parse_config(commands[1])
                self.setup_choplib_from_config(config)
                self.send_message("Created new choplib instance from %s" % commands[1])
            except Exception, e:
                traceback.print_exc()
                self.send_message("Unable to create choplib instance: %s" % e)
        elif commands[0] == 'destroy':
            self.destroy_choplib()
            self.send_message("Destroyed choplib instance") 
        elif commands[0] == 'renew':
            self.reset_choplib()
            self.send_message("Renewed choplib instance") 
        elif commands[0] == 'set':
            if self.choplib is None:
                self.send_message("Please run 'new' first")
            elif len(commands) < 2:
                self.send_message("set requires a parameter and value")
            else:
                params,value = commands[1].split(' ', 1)
                self.choplib_set(params, value)
        elif commands[0] == 'get':
            if self.choplib is None:
                self.send_message("Please 'new' first")
            elif len(commands) < 2:
                self.send_message("get requires parameter")
            else:
                self.choplib_get(commands[1])
        elif commands[0] == 'list_params':
            self.send_message(self.params_message())


        elif commands[0] == 'module_info':
            if(len(commands) < 2):
                self.send_message("module_info requires a module string")
            else:
                self.run_module_info(commands[1])
        elif commands[0] == 'run':
            if self.choplib is None:
                self.send_message("Must run 'new' first")
            else:
                try:
                    self.choplib.start()
                except RuntimeError, e:
                    self.send_message("Must 'renew' to run again")
        elif commands[0] == 'stop':
            if self.choplib is not None:
                self.choplib.stop()
                #self.choplib = None
        elif commands[0] == 'disconnect':
            self.liason.deassociate()
            self._force_deassociate()
        #elif commands[0] == 'shutdown':
        #    pass
        #    #TBD
        elif commands[0] == 'help':
            self.send_message(self.help_message())
        else:
                self.send_message("Unknown Command: " + commands[0])

    def run(self):
        while not self.stopped:
            if self.request is None:
                time.sleep(.1)
                continue

            self.request.ws_stream.send_message("Shell Connected", binary = False) 
            while (self.request is not None) and (not self.stopped):
                try:
                    line = self.request.ws_stream.receive_message()

                    if line is None:
                        continue

                    self.process_message(line)

                except:
                    #Something broke -- need to deassociate
                    liason = self.liason
                    request = self.request
                    self.liason.deassociate()
                    self.deassociate(liason, request)                    
                    break


class _HandshakeDispatcher(object):
    def do_extra_handshake(self, request):
        pass


class ChopWebSocketServer(standalone.WebSocketServer):
    def __init__(self, options):
        options.dispatcher = _HandshakeDispatcher()

        self._logger = util.get_class_logger(self)

        self.request_queue_size = options.request_queue_size
        self._WebSocketServer__ws_is_shut_down = threading.Event()
        self._WebSocketServer__ws_serving = False

        SocketServer.BaseServer.__init__(
            self, (options.server_host, options.port), ChopWebSocketRequestHandler)

        # Expose the options object to allow handler objects access it. We name
        # it with websocket_ prefix to avoid conflict.
        self.websocket_server_options = options

        self._create_sockets()
        self.server_bind()
        self.server_activate()


class ChopWebSocketRequestHandler(standalone.WebSocketRequestHandler):
    def parse_request(self):
        """Override BaseHTTPServer.BaseHTTPRequestHandler.parse_request.

        Return True to continue processing for HTTP(S), False otherwise.

        See BaseHTTPRequestHandler.handle_one_request method which calls
        this method to understand how the return value will be handled.
        """

        # We hook parse_request method, but also call the original
        # CGIHTTPRequestHandler.parse_request since when we return False,
        # CGIHTTPRequestHandler.handle_one_request continues processing and
        # it needs variables set by CGIHTTPRequestHandler.parse_request.
        #
        # Variables set by this method will be also used by WebSocket request
        # handling (self.path, self.command, self.requestline, etc. See also
        # how _StandaloneRequest's members are implemented using these
        # attributes).
        if not CGIHTTPServer.CGIHTTPRequestHandler.parse_request(self):
            return False

        host, port, resource = http_header_util.parse_uri(self.path)
        if resource is None:
            self._logger.info('Invalid URI: %r', self.path)
            self._logger.info('Fallback to CGIHTTPRequestHandler')
            return True
        server_options = self.server.websocket_server_options
        if host is not None:
            validation_host = server_options.validation_host
            if validation_host is not None and host != validation_host:
                self._logger.info('Invalid host: %r (expected: %r)',
                                  host,
                                  validation_host)
                self._logger.info('Fallback to CGIHTTPRequestHandler')
                return True
        if port is not None:
            validation_port = server_options.validation_port
            if validation_port is not None and port != validation_port:
                self._logger.info('Invalid port: %r (expected: %r)',
                                  port,
                                  validation_port)
                self._logger.info('Fallback to CGIHTTPRequestHandler')
                return True
        self.path = resource

        request = standalone._StandaloneRequest(self, self._options.use_tls)

        try:
            # Fallback to default http handler for request paths for which
            # we don't have request handlers.
            #TODO fill in path determination for static files and this
            #if not self._options.dispatcher.get_handler_suite(self.path):
            self._logger.debug("Path : %r", self.path)
            if self.path != "/data" and self.path != "/shell":
                return True
        except dispatch.DispatchException, e:
            self._logger.info('%s', e)
            self.send_error(e.status)
            return False

        # If any Exceptions without except clause setup (including
        # DispatchException) is raised below this point, it will be caught
        # and logged by WebSocketServer.

        try:
            try:
                handshake.do_handshake(
                    request,
                    self._options.dispatcher, #This should now be custom dispatcher
                    allowDraft75=self._options.allow_draft75,
                    strict=self._options.strict)
            except handshake.VersionException, e:
                self._logger.info('%s', e)
                self.send_response(common.HTTP_STATUS_BAD_REQUEST)
                self.send_header(common.SEC_WEBSOCKET_VERSION_HEADER,
                                 e.supported_versions)
                self.end_headers()
                return False
            except handshake.HandshakeException, e:
                # Handshake for ws(s) failed.
                self._logger.info('%s', e)
                self.send_error(e.status)
                return False

                
            try:
                if self.path == "/data":
                    dataparser = _ChopDataParser(request, server_options.queuetracker)
                    dataparser.go()

                elif self.path == "/shell":
                    #request.ws_stream.send_message("Welcome", binary=False)
                    shell = _ChopLibShellLiason(request, server_options.choplibshell)
                    shell.go()

                if not request.server_terminated:
                    request.ws_stream.close_connection()
            # Catch non-critical exceptions the handler didn't handle.
            except handshake.AbortedByUserException, e:
                self._logger.debug('%s', e)
                raise
            except msgutil.BadOperationException, e:
                self._logger.debug('%s', e)
                request.ws_stream.close_connection(common.STATUS_ABNORMAL_CLOSURE)
            except msgutil.InvalidFrameException, e:
                # InvalidFrameException must be caught before
                # ConnectionTerminatedException that catches InvalidFrameException.
                self._logger.debug('%s', e)
                request.ws_stream.close_connection(common.STATUS_PROTOCOL_ERROR)
            except msgutil.UnsupportedFrameException, e:
                self._logger.debug('%s', e)
                request.ws_stream.close_connection(common.STATUS_UNSUPPORTED_DATA)
            except stream.InvalidUTF8Exception, e:
                self._logger.debug('%s', e)
                request.ws_stream.close_connection(
                    common.STATUS_INVALID_FRAME_PAYLOAD_DATA)
            except msgutil.ConnectionTerminatedException, e:
                self._logger.debug('%s', e)
            except Exception, e:
                util.prepend_message_to_exception(
                    '%s raised exception for %s: ' % (
                        _TRANSFER_DATA_HANDLER_NAME, request.ws_resource),
                    e)
                raise

        except handshake.AbortedByUserException, e:
            self._logger.info('%s', e)
        return False



def _get_logger_from_class(c):
    return logging.getLogger('%s.%s' % (c.__module__, c.__name__))


def _configure_logging(options):
    logging.addLevelName(common.LOGLEVEL_FINE, 'FINE')

    logger = logging.getLogger()
    logger.setLevel(logging.getLevelName(options.log_level.upper()))
    if options.log_file:
        handler = logging.handlers.RotatingFileHandler(
                options.log_file, 'a', options.log_max, options.log_count)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    deflate_log_level_name = logging.getLevelName(
        options.deflate_log_level.upper())
    _get_logger_from_class(util._Deflater).setLevel(
        deflate_log_level_name)
    _get_logger_from_class(util._Inflater).setLevel(
        deflate_log_level_name)


class ThreadMonitor(threading.Thread):
    daemon = True

    def __init__(self, interval_in_sec):
        threading.Thread.__init__(self, name='ThreadMonitor')

        self._logger = util.get_class_logger(self)

        self._interval_in_sec = interval_in_sec

    def run(self):
        while True:
            thread_name_list = []
            for thread in threading.enumerate():
                thread_name_list.append(thread.name)
            self._logger.info(
                "%d active threads: %s",
                threading.active_count(),
                ', '.join(thread_name_list))
            time.sleep(self._interval_in_sec)


# vi:sts=4 sw=4 et

########NEW FILE########
