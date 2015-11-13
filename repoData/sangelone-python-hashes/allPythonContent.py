__FILENAME__ = bloom
"""
Implementation of a Bloom filter in Python.

The Bloom filter is a space-efficient probabilistic data structure that is
used to test whether an element is a member of a set. False positives are
possible, but false negatives are not. Elements can be added to the set, but 
not removed. The more elements that are added to the set, the larger the
probability of false positives.

Uses SHA-1 from Python's hashlib, but you can swap that out with any other
160-bit hash function. Also keep in mind that it starts off very sparse and
become more dense (and false-positive-prone) as you add more elements.

Part of python-hashes by sangelone. See README and LICENSE.
"""

import math
import hashlib
from hashtype import hashtype


class bloomfilter(hashtype):
    def __init__(self, value='', capacity=3000, false_positive_rate=0.01):
        """
        'value' is the initial string or list of strings to hash,
        'capacity' is the expected upper limit on items inserted, and
        'false_positive_rate' is self-explanatory but the smaller it is, the larger your hashes!
        """
        self.create_hash(value, capacity, false_positive_rate)

    def create_hash(self, initial, capacity, error):
        """
        Calculates a Bloom filter with the specified parameters.
        Initalizes with a string or list/set/tuple of strings. No output.

        Reference material: http://bitworking.org/news/380/bloom-filter-resources
        """
        self.hash = 0L
        self.hashbits, self.num_hashes = self._optimal_size(capacity, error)

        if len(initial):
            if type(initial) == str:
                self.add(initial)
            else:
                for t in initial:
                    self.add(t)
    
    def _hashes(self, item):
      """
      To create the hash functions we use the SHA-1 hash of the
      string and chop that up into 20 bit values and then
      mod down to the length of the Bloom filter.
      """
      m = hashlib.sha1()
      m.update(item)
      digits = m.hexdigest()

      # Add another 160 bits for every 8 (20-bit long) hashes we need
      for i in range(self.num_hashes / 8):
          m.update(str(i))
          digits += m.hexdigest()

      hashes = [int(digits[i*5:i*5+5], 16) % self.hashbits for i in range(self.num_hashes)]
      return hashes  

    def _optimal_size(self, capacity, error):
        """Calculates minimum number of bits in filter array and
        number of hash functions given a number of enteries (maximum)
        and the desired error rate (falese positives).
        
        Example:
            m, k = self._optimal_size(3000, 0.01)   # m=28756, k=7
        """
        m = math.ceil((capacity * math.log(error)) / math.log(1.0 / (math.pow(2.0, math.log(2.0)))))
        k = math.ceil(math.log(2.0) * m / capacity)
        return (int(m), int(k))

    
    def add(self, item):
        "Add an item (string) to the filter. Cannot be removed later!"
        for pos in self._hashes(item):
            self.hash |= (2 ** pos)

    def __contains__(self, name):
        "This function is used by the 'in' keyword"
        retval = True
        for pos in self._hashes(name):
            retval = retval and bool(self.hash & (2 ** pos))
        return retval

########NEW FILE########
__FILENAME__ = geohash
"""
Geohash is a latitude/longitude geocode system invented by 
Gustavo Niemeyer when writing the web service at geohash.org, and put 
into the public domain.

It is a hierarchical spatial data structure which subdivides space 
into buckets of grid shape. Geohashes offer properties like 
arbitrary precision and the possibility of gradually removing 
characters from the end of the code to reduce its size (and 
gradually lose precision). As a consequence of the gradual 
precision degradation, nearby places will often (but not always) 
present similar prefixes. On the other side, the longer a shared 
prefix is, the closer the two places are.

Part of python-hashes by sangelone. See README and LICENSE.
Based on code by Hiroaki Kawai <kawai@iij.ad.jp> and geohash.org
"""

import math
from hashtype import hashtype


class geohash(hashtype):
    # Not the actual RFC 4648 standard; a varation
    _base32 = '0123456789bcdefghjkmnpqrstuvwxyz'
    _base32_map = {}
    for i in range(len(_base32)):
        _base32_map[_base32[i]] = i

    def __init__(self, lat=0.0, long=0.0, precision=12):
        self.encode(lat, long, precision)

    def _encode_i2c(self, lat, lon, lat_length, lon_length):
        precision=(lat_length+lon_length)/5
        a, b = lat, lon
        if lat_length < lon_length:
            a, b = lon, lat
        
        boost = (0,1,4,5,16,17,20,21)
        ret = ''
        for i in range(precision):
                ret += self._base32[(boost[a&7]+(boost[b&3]<<1))&0x1F]
                t = a>>3
                a = b>>2
                b = t
        
        return ret[::-1]

    def encode(self, latitude, longitude, precision):
        self.latitude = latitude
        self.longitude = longitude

        if latitude >= 90.0 or latitude < -90.0:
                raise Exception("invalid latitude")
        while longitude < -180.0:
                longitude += 360.0
        while longitude >= 180.0:
                longitude -= 360.0
        
        lat = latitude / 180.0
        lon = longitude / 360.0
        
        lat_length = lon_length = precision * 5 / 2
        lon_length += precision & 1
        
        # Here is where we decide encoding based on quadrant..
        # points near the equator, for example, will have widely 
        # differing hashes because of this
        if lat>0:
                lat = int((1<<lat_length)*lat)+(1<<(lat_length-1))
        else:
                lat = (1<<lat_length-1)-int((1<<lat_length)*(-lat))
        
        if lon>0:
                lon = int((1<<lon_length)*lon)+(1<<(lon_length-1))
        else:
                lon = (1<<lon_length-1)-int((1<<lon_length)*(-lon))
        
        self.hash = self._encode_i2c(lat,lon,lat_length,lon_length)

    def _decode_c2i(self, hashcode):
        lon = 0
        lat = 0
        bit_length = 0
        lat_length = 0
        lon_length = 0

        # Unrolled for speed and clarity
        for i in hashcode:
                t = self._base32_map[i]
                if not (bit_length & 1):
                        lon = lon<<3
                        lat = lat<<2
                        lon += (t>>2)&4
                        lat += (t>>2)&2
                        lon += (t>>1)&2
                        lat += (t>>1)&1
                        lon += t&1
                        lon_length+=3
                        lat_length+=2
                else:
                        lon = lon<<2
                        lat = lat<<3
                        lat += (t>>2)&4
                        lon += (t>>2)&2
                        lat += (t>>1)&2
                        lon += (t>>1)&1
                        lat += t&1
                        lon_length+=2
                        lat_length+=3
                
                bit_length+=5
        
        return (lat,lon,lat_length,lon_length)

    def decode(self):
        (lat,lon,lat_length,lon_length) = self._decode_c2i(self.hash)
        
        lat = (lat<<1) + 1
        lon = (lon<<1) + 1
        lat_length += 1
        lon_length += 1
        
        latitude  = 180.0*(lat-(1<<(lat_length-1)))/(1<<lat_length)
        longitude = 360.0*(lon-(1<<(lon_length-1)))/(1<<lon_length)
        
        self.latitude = latitude
        self.longitude = longitude

        return latitude, longitude

    def __long__(self): pass

    def __float__(self): pass

    def hex(self): pass

    def unit_distance(self, lat1, long1, lat2, long2):
        degrees_to_radians = math.pi/180.0

        phi1 = (90.0 - lat1)*degrees_to_radians
        phi2 = (90.0 - lat2)*degrees_to_radians        
        theta1 = long1*degrees_to_radians
        theta2 = long2*degrees_to_radians
        
        # Compute spherical distance from spherical coordinates.        
        cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
               math.cos(phi1)*math.cos(phi2))
        return math.acos(cos)

    def distance_in_miles(self, other_hash):
        return self.unit_distance(self.latitude, self.longitude, other_hash.latitude, other_hash.longitude) * 3960

    def distance_in_km(self, other_hash):
        return self.unit_distance(self.latitude, self.longitude, other_hash.latitude, other_hash.longitude) * 6373


########NEW FILE########
__FILENAME__ = hashtype
"""
Base class from which hash types can be created.

Part of python-hashes by sangelone. See README and LICENSE.
"""

default_hashbits = 96

class hashtype(object):
    def __init__(self, value='', hashbits=default_hashbits, hash=None):
        "Relies on create_hash() provided by subclass"
        self.hashbits = hashbits
        if hash:
            self.hash = hash
        else:
            self.create_hash(value)

    def __trunc__(self):
        return self.hash

    def __str__(self):
        return str(self.hash)
    
    def __long__(self):
        return long(self.hash)

    def __float__(self):
        return float(self.hash)
        
    def __cmp__(self, other):
        if self.hash < long(other): return -1
        if self.hash > long(other): return 1
        return 0
    
    def hex(self):
        return hex(self.hash)

    def hamming_distance(self, other_hash):
        x = (self.hash ^ other_hash.hash) & ((1 << self.hashbits) - 1)
        tot = 0
        while x:
            tot += 1
            x &= x-1
        return tot

    def __hash__(self):
        return self.hash

    def __eq__(self, other):
        return self.hash == other.hash

########NEW FILE########
__FILENAME__ = nilsimsa
"""
Implementation of Nilsimsa hashes (signatures) in Python.

Most useful for filtering spam by creating signatures of documents to 
find near-duplicates. Charikar similarity hashes can be used on any 
datastream, whereas Nilsimsa is a digest ideal for documents (written 
in any language) because it uses histograms of [rolling] trigraphs 
instead of the usual bag-of-words model where order doesn't matter.

Related paper: http://spdp.dti.unimi.it/papers/pdcs04.pdf

Part of python-hashes by sangelone. See README and LICENSE.
"""

from hashtype import hashtype

TRAN = [ord(x) for x in 
    "\x02\xD6\x9E\x6F\xF9\x1D\x04\xAB\xD0\x22\x16\x1F\xD8\x73\xA1\xAC"\
    "\x3B\x70\x62\x96\x1E\x6E\x8F\x39\x9D\x05\x14\x4A\xA6\xBE\xAE\x0E"\
    "\xCF\xB9\x9C\x9A\xC7\x68\x13\xE1\x2D\xA4\xEB\x51\x8D\x64\x6B\x50"\
    "\x23\x80\x03\x41\xEC\xBB\x71\xCC\x7A\x86\x7F\x98\xF2\x36\x5E\xEE"\
    "\x8E\xCE\x4F\xB8\x32\xB6\x5F\x59\xDC\x1B\x31\x4C\x7B\xF0\x63\x01"\
    "\x6C\xBA\x07\xE8\x12\x77\x49\x3C\xDA\x46\xFE\x2F\x79\x1C\x9B\x30"\
    "\xE3\x00\x06\x7E\x2E\x0F\x38\x33\x21\xAD\xA5\x54\xCA\xA7\x29\xFC"\
    "\x5A\x47\x69\x7D\xC5\x95\xB5\xF4\x0B\x90\xA3\x81\x6D\x25\x55\x35"\
    "\xF5\x75\x74\x0A\x26\xBF\x19\x5C\x1A\xC6\xFF\x99\x5D\x84\xAA\x66"\
    "\x3E\xAF\x78\xB3\x20\x43\xC1\xED\x24\xEA\xE6\x3F\x18\xF3\xA0\x42"\
    "\x57\x08\x53\x60\xC3\xC0\x83\x40\x82\xD7\x09\xBD\x44\x2A\x67\xA8"\
    "\x93\xE0\xC2\x56\x9F\xD9\xDD\x85\x15\xB4\x8A\x27\x28\x92\x76\xDE"\
    "\xEF\xF8\xB2\xB7\xC9\x3D\x45\x94\x4B\x11\x0D\x65\xD5\x34\x8B\x91"\
    "\x0C\xFA\x87\xE9\x7C\x5B\xB1\x4D\xE5\xD4\xCB\x10\xA2\x17\x89\xBC"\
    "\xDB\xB0\xE2\x97\x88\x52\xF7\x48\xD3\x61\x2C\x3A\x2B\xD1\x8C\xFB"\
    "\xF1\xCD\xE4\x6A\xE7\xA9\xFD\xC4\x37\xC8\xD2\xF6\xDF\x58\x72\x4E"]


class nilsimsa(hashtype):
    def __init__(self, value='', hashbits=256):
        self.hashbits = hashbits
        self.count = 0          # num characters seen
        self.acc = [0]*256      # accumulators for computing digest
        self.lastch = [-1]*4    # last four seen characters (-1 until set)
        self.create_hash(value)

    def create_hash(self, data):
        """Calculates a Nilsimsa signature with appropriate bitlength.        
        Input must be a string. Returns nothing.
        Reference: http://ixazon.dynip.com/~cmeclax/nilsimsa.html
        """
        if type(data) != str:
            raise Exception('Nilsimsa hashes can only be created on strings')
        self.hash = 0L
        self.add(data)

    def add(self, data):
        """Add data to running digest, increasing the accumulators for 0-8
           triplets formed by this char and the previous 0-3 chars."""
        for character in data:
            ch = ord(character)
            self.count += 1

            # incr accumulators for triplets
            if self.lastch[1] > -1:
                self.acc[self._tran3(ch, self.lastch[0], self.lastch[1], 0)] +=1
            if self.lastch[2] > -1:
                self.acc[self._tran3(ch, self.lastch[0], self.lastch[2], 1)] +=1
                self.acc[self._tran3(ch, self.lastch[1], self.lastch[2], 2)] +=1
            if self.lastch[3] > -1:
                self.acc[self._tran3(ch, self.lastch[0], self.lastch[3], 3)] +=1
                self.acc[self._tran3(ch, self.lastch[1], self.lastch[3], 4)] +=1
                self.acc[self._tran3(ch, self.lastch[2], self.lastch[3], 5)] +=1
                self.acc[self._tran3(self.lastch[3], self.lastch[0], ch, 6)] +=1
                self.acc[self._tran3(self.lastch[3], self.lastch[2], ch, 7)] +=1

            # adjust last seen chars
            self.lastch = [ch] + self.lastch[:3]
        self.hash = self._digest()

    def _tran3(self, a, b, c, n):
        """Get accumulator for a transition n between chars a, b, c."""
        return (((TRAN[(a+n)&255]^TRAN[b]*(n+n+1))+TRAN[(c)^TRAN[n]])&255)

    def _digest(self):
        """Get digest of data seen thus far as a list of bytes."""
        total = 0                           # number of triplets seen
        if self.count == 3:                 # 3 chars = 1 triplet
            total = 1
        elif self.count == 4:               # 4 chars = 4 triplets
            total = 4
        elif self.count > 4:                # otherwise 8 triplets/char less
            total = 8 * self.count - 28     # 28 'missed' during 'ramp-up'

        threshold = total / 256             # threshold for accumulators

        code = [0]*self.hashbits            # start with all zero bits
        for i in range(256):                # for all 256 accumulators
            if self.acc[i] > threshold:     # if it meets the threshold
                code[i >> 3] += 1 << (i&7)  # set corresponding digest bit

        code = code[::-1]                   # reverse the byte order

        out = 0
        for i in xrange(self.hashbits):     # turn bit list into real bits
            if code[i] :
                out += 1 << i

        return out
                            
    def similarity(self, other_hash):
        """Calculate how different this hash is from another Nilsimsa.
        Returns a float from 0.0 to 1.0 (inclusive)
        """
        if type(other_hash) != nilsimsa:
            raise Exception('Hashes must be of same type to find similarity')
        b = self.hashbits
        if b != other_hash.hashbits:
            raise Exception('Hashes must be of equal size to find similarity')
        return float(b - self.hamming_distance(other_hash)) / b

########NEW FILE########
__FILENAME__ = simhash
"""
Implementation of Charikar similarity hashes in Python.

Most useful for creating 'fingerprints' of documents or metadata
so you can quickly find duplicates or cluster items.

Part of python-hashes by sangelone. See README and LICENSE.
"""

from hashtype import hashtype

class simhash(hashtype):
    def create_hash(self, tokens):
        """Calculates a Charikar simhash with appropriate bitlength.
        
        Input can be any iterable, but for strings it will automatically
        break it into words first, assuming you don't want to iterate
        over the individual characters. Returns nothing.
        
        Reference used: http://dsrg.mff.cuni.cz/~holub/sw/shash
        """
        if type(tokens) == str:
            tokens = tokens.split()
        v = [0]*self.hashbits    
        for t in [self._string_hash(x) for x in tokens]:
            bitmask = 0
            for i in xrange(self.hashbits):
                bitmask = 1 << i
                if t & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in xrange(self.hashbits):
            if v[i] >= 0:
                fingerprint += 1 << i        
        self.hash = fingerprint

    def _string_hash(self, v):
        "A variable-length version of Python's builtin hash. Neat!"
        if v == "":
            return 0
        else:
            x = ord(v[0])<<7
            m = 1000003
            mask = 2**self.hashbits-1
            for c in v:
                x = ((x*m)^ord(c)) & mask
            x ^= len(v)
            if x == -1: 
                x = -2
            return x

    def similarity(self, other_hash):
        """Calculate how similar this hash is from another simhash.
        Returns a float from 0.0 to 1.0 (linear distribution, inclusive)
        """
        if type(other_hash) != simhash:
            raise Exception('Hashes must be of same type to find similarity')
        b = self.hashbits
        if b!= other_hash.hashbits:
            raise Exception('Hashes must be of equal size to find similarity')
        return float(b - self.hamming_distance(other_hash)) / b

########NEW FILE########
