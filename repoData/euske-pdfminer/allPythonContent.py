__FILENAME__ = arcfour
#!/usr/bin/env python

""" Python implementation of Arcfour encryption algorithm.

This code is in the public domain.

"""


##  Arcfour
##
class Arcfour(object):

    """
    >>> Arcfour('Key').process('Plaintext').encode('hex')
    'bbf316e8d940af0ad3'
    >>> Arcfour('Wiki').process('pedia').encode('hex')
    '1021bf0420'
    >>> Arcfour('Secret').process('Attack at dawn').encode('hex')
    '45a01f645fc35b383552544b9bf5'
    """

    def __init__(self, key):
        s = range(256)
        j = 0
        klen = len(key)
        for i in xrange(256):
            j = (j + s[i] + ord(key[i % klen])) % 256
            (s[i], s[j]) = (s[j], s[i])
        self.s = s
        (self.i, self.j) = (0, 0)
        return

    def process(self, data):
        (i, j) = (self.i, self.j)
        s = self.s
        r = ''
        for c in data:
            i = (i+1) % 256
            j = (j+s[i]) % 256
            (s[i], s[j]) = (s[j], s[i])
            k = s[(s[i]+s[j]) % 256]
            r += chr(ord(c) ^ k)
        (self.i, self.j) = (i, j)
        return r
    
    encrypt = decrypt = process

new = Arcfour

# test
if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = ascii85
#!/usr/bin/env python

""" Python implementation of ASCII85/ASCIIHex decoder (Adobe version).

This code is in the public domain.

"""

import re
import struct


# ascii85decode(data)
def ascii85decode(data):
    """
    In ASCII85 encoding, every four bytes are encoded with five ASCII
    letters, using 85 different types of characters (as 256**4 < 85**5).
    When the length of the original bytes is not a multiple of 4, a special
    rule is used for round up.

    The Adobe's ASCII85 implementation is slightly different from
    its original in handling the last characters.

    The sample string is taken from:
      http://en.wikipedia.org/w/index.php?title=Ascii85

    >>> ascii85decode('9jqo^BlbD-BleB1DJ+*+F(f,q')
    'Man is distinguished'
    >>> ascii85decode('E,9)oF*2M7/c~>')
    'pleasure.'
    """
    n = b = 0
    out = ''
    for c in data:
        if '!' <= c and c <= 'u':
            n += 1
            b = b*85+(ord(c)-33)
            if n == 5:
                out += struct.pack('>L', b)
                n = b = 0
        elif c == 'z':
            assert n == 0
            out += '\0\0\0\0'
        elif c == '~':
            if n:
                for _ in range(5-n):
                    b = b*85+84
                out += struct.pack('>L', b)[:n-1]
            break
    return out

# asciihexdecode(data)
hex_re = re.compile(r'([a-f\d]{2})', re.IGNORECASE)
trail_re = re.compile(r'^(?:[a-f\d]{2}|\s)*([a-f\d])[\s>]*$', re.IGNORECASE)


def asciihexdecode(data):
    """
    ASCIIHexDecode filter: PDFReference v1.4 section 3.3.1
    For each pair of ASCII hexadecimal digits (0-9 and A-F or a-f), the
    ASCIIHexDecode filter produces one byte of binary data. All white-space
    characters are ignored. A right angle bracket character (>) indicates
    EOD. Any other characters will cause an error. If the filter encounters
    the EOD marker after reading an odd number of hexadecimal digits, it
    will behave as if a 0 followed the last digit.

    >>> asciihexdecode('61 62 2e6364   65')
    'ab.cde'
    >>> asciihexdecode('61 62 2e6364   657>')
    'ab.cdep'
    >>> asciihexdecode('7>')
    'p'
    """
    decode = (lambda hx: chr(int(hx, 16)))
    out = map(decode, hex_re.findall(data))
    m = trail_re.search(data)
    if m:
        out.append(decode("%c0" % m.group(1)))
    return ''.join(out)


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = ccitt
#!/usr/bin/env python
# CCITT Fax decoder
#
# Bugs: uncompressed mode untested.
#
#  cf.
#   ITU-T Recommendation T.4
#     "Standardization of Group 3 facsimile terminals for document transmission"
#   ITU-T Recommendation T.6
#     "FACSIMILE CODING SCHEMES AND CODING CONTROL FUNCTIONS FOR GROUP 4 FACSIMILE APPARATUS"


import sys
import array


##  BitParser
##
class BitParser(object):

    def __init__(self):
        self._pos = 0
        return

    @classmethod
    def add(klass, root, v, bits):
        p = root
        b = None
        for i in xrange(len(bits)):
            if 0 < i:
                if p[b] is None:
                    p[b] = [None, None]
                p = p[b]
            if bits[i] == '1':
                b = 1
            else:
                b = 0
        p[b] = v
        return

    def feedbytes(self, data):
        for c in data:
            b = ord(c)
            for m in (128, 64, 32, 16, 8, 4, 2, 1):
                self._parse_bit(b & m)
        return

    def _parse_bit(self, x):
        if x:
            v = self._state[1]
        else:
            v = self._state[0]
        self._pos += 1
        if isinstance(v, list):
            self._state = v
        else:
            self._state = self._accept(v)
        return


##  CCITTG4Parser
##
class CCITTG4Parser(BitParser):

    MODE = [None, None]
    BitParser.add(MODE, 0,   '1')
    BitParser.add(MODE, +1,  '011')
    BitParser.add(MODE, -1,  '010')
    BitParser.add(MODE, 'h', '001')
    BitParser.add(MODE, 'p', '0001')
    BitParser.add(MODE, +2,  '000011')
    BitParser.add(MODE, -2,  '000010')
    BitParser.add(MODE, +3,  '0000011')
    BitParser.add(MODE, -3,  '0000010')
    BitParser.add(MODE, 'u', '0000001111')
    BitParser.add(MODE, 'x1', '0000001000')
    BitParser.add(MODE, 'x2', '0000001001')
    BitParser.add(MODE, 'x3', '0000001010')
    BitParser.add(MODE, 'x4', '0000001011')
    BitParser.add(MODE, 'x5', '0000001100')
    BitParser.add(MODE, 'x6', '0000001101')
    BitParser.add(MODE, 'x7', '0000001110')
    BitParser.add(MODE, 'e', '000000000001000000000001')

    WHITE = [None, None]
    BitParser.add(WHITE, 0   , '00110101')
    BitParser.add(WHITE, 1   , '000111')
    BitParser.add(WHITE, 2   , '0111')
    BitParser.add(WHITE, 3   , '1000')
    BitParser.add(WHITE, 4   , '1011')
    BitParser.add(WHITE, 5   , '1100')
    BitParser.add(WHITE, 6   , '1110')
    BitParser.add(WHITE, 7   , '1111')
    BitParser.add(WHITE, 8   , '10011')
    BitParser.add(WHITE, 9   , '10100')
    BitParser.add(WHITE, 10  , '00111')
    BitParser.add(WHITE, 11  , '01000')
    BitParser.add(WHITE, 12  , '001000')
    BitParser.add(WHITE, 13  , '000011')
    BitParser.add(WHITE, 14  , '110100')
    BitParser.add(WHITE, 15  , '110101')
    BitParser.add(WHITE, 16  , '101010')
    BitParser.add(WHITE, 17  , '101011')
    BitParser.add(WHITE, 18  , '0100111')
    BitParser.add(WHITE, 19  , '0001100')
    BitParser.add(WHITE, 20  , '0001000')
    BitParser.add(WHITE, 21  , '0010111')
    BitParser.add(WHITE, 22  , '0000011')
    BitParser.add(WHITE, 23  , '0000100')
    BitParser.add(WHITE, 24  , '0101000')
    BitParser.add(WHITE, 25  , '0101011')
    BitParser.add(WHITE, 26  , '0010011')
    BitParser.add(WHITE, 27  , '0100100')
    BitParser.add(WHITE, 28  , '0011000')
    BitParser.add(WHITE, 29  , '00000010')
    BitParser.add(WHITE, 30  , '00000011')
    BitParser.add(WHITE, 31  , '00011010')
    BitParser.add(WHITE, 32  , '00011011')
    BitParser.add(WHITE, 33  , '00010010')
    BitParser.add(WHITE, 34  , '00010011')
    BitParser.add(WHITE, 35  , '00010100')
    BitParser.add(WHITE, 36  , '00010101')
    BitParser.add(WHITE, 37  , '00010110')
    BitParser.add(WHITE, 38  , '00010111')
    BitParser.add(WHITE, 39  , '00101000')
    BitParser.add(WHITE, 40  , '00101001')
    BitParser.add(WHITE, 41  , '00101010')
    BitParser.add(WHITE, 42  , '00101011')
    BitParser.add(WHITE, 43  , '00101100')
    BitParser.add(WHITE, 44  , '00101101')
    BitParser.add(WHITE, 45  , '00000100')
    BitParser.add(WHITE, 46  , '00000101')
    BitParser.add(WHITE, 47  , '00001010')
    BitParser.add(WHITE, 48  , '00001011')
    BitParser.add(WHITE, 49  , '01010010')
    BitParser.add(WHITE, 50  , '01010011')
    BitParser.add(WHITE, 51  , '01010100')
    BitParser.add(WHITE, 52  , '01010101')
    BitParser.add(WHITE, 53  , '00100100')
    BitParser.add(WHITE, 54  , '00100101')
    BitParser.add(WHITE, 55  , '01011000')
    BitParser.add(WHITE, 56  , '01011001')
    BitParser.add(WHITE, 57  , '01011010')
    BitParser.add(WHITE, 58  , '01011011')
    BitParser.add(WHITE, 59  , '01001010')
    BitParser.add(WHITE, 60  , '01001011')
    BitParser.add(WHITE, 61  , '00110010')
    BitParser.add(WHITE, 62  , '00110011')
    BitParser.add(WHITE, 63  , '00110100')
    BitParser.add(WHITE, 64  , '11011')
    BitParser.add(WHITE, 128 , '10010')
    BitParser.add(WHITE, 192 , '010111')
    BitParser.add(WHITE, 256 , '0110111')
    BitParser.add(WHITE, 320 , '00110110')
    BitParser.add(WHITE, 384 , '00110111')
    BitParser.add(WHITE, 448 , '01100100')
    BitParser.add(WHITE, 512 , '01100101')
    BitParser.add(WHITE, 576 , '01101000')
    BitParser.add(WHITE, 640 , '01100111')
    BitParser.add(WHITE, 704 , '011001100')
    BitParser.add(WHITE, 768 , '011001101')
    BitParser.add(WHITE, 832 , '011010010')
    BitParser.add(WHITE, 896 , '011010011')
    BitParser.add(WHITE, 960 , '011010100')
    BitParser.add(WHITE, 1024, '011010101')
    BitParser.add(WHITE, 1088, '011010110')
    BitParser.add(WHITE, 1152, '011010111')
    BitParser.add(WHITE, 1216, '011011000')
    BitParser.add(WHITE, 1280, '011011001')
    BitParser.add(WHITE, 1344, '011011010')
    BitParser.add(WHITE, 1408, '011011011')
    BitParser.add(WHITE, 1472, '010011000')
    BitParser.add(WHITE, 1536, '010011001')
    BitParser.add(WHITE, 1600, '010011010')
    BitParser.add(WHITE, 1664, '011000')
    BitParser.add(WHITE, 1728, '010011011')
    BitParser.add(WHITE, 1792, '00000001000')
    BitParser.add(WHITE, 1856, '00000001100')
    BitParser.add(WHITE, 1920, '00000001101')
    BitParser.add(WHITE, 1984, '000000010010')
    BitParser.add(WHITE, 2048, '000000010011')
    BitParser.add(WHITE, 2112, '000000010100')
    BitParser.add(WHITE, 2176, '000000010101')
    BitParser.add(WHITE, 2240, '000000010110')
    BitParser.add(WHITE, 2304, '000000010111')
    BitParser.add(WHITE, 2368, '000000011100')
    BitParser.add(WHITE, 2432, '000000011101')
    BitParser.add(WHITE, 2496, '000000011110')
    BitParser.add(WHITE, 2560, '000000011111')

    BLACK = [None, None]
    BitParser.add(BLACK, 0   , '0000110111')
    BitParser.add(BLACK, 1   , '010')
    BitParser.add(BLACK, 2   , '11')
    BitParser.add(BLACK, 3   , '10')
    BitParser.add(BLACK, 4   , '011')
    BitParser.add(BLACK, 5   , '0011')
    BitParser.add(BLACK, 6   , '0010')
    BitParser.add(BLACK, 7   , '00011')
    BitParser.add(BLACK, 8   , '000101')
    BitParser.add(BLACK, 9   , '000100')
    BitParser.add(BLACK, 10  , '0000100')
    BitParser.add(BLACK, 11  , '0000101')
    BitParser.add(BLACK, 12  , '0000111')
    BitParser.add(BLACK, 13  , '00000100')
    BitParser.add(BLACK, 14  , '00000111')
    BitParser.add(BLACK, 15  , '000011000')
    BitParser.add(BLACK, 16  , '0000010111')
    BitParser.add(BLACK, 17  , '0000011000')
    BitParser.add(BLACK, 18  , '0000001000')
    BitParser.add(BLACK, 19  , '00001100111')
    BitParser.add(BLACK, 20  , '00001101000')
    BitParser.add(BLACK, 21  , '00001101100')
    BitParser.add(BLACK, 22  , '00000110111')
    BitParser.add(BLACK, 23  , '00000101000')
    BitParser.add(BLACK, 24  , '00000010111')
    BitParser.add(BLACK, 25  , '00000011000')
    BitParser.add(BLACK, 26  , '000011001010')
    BitParser.add(BLACK, 27  , '000011001011')
    BitParser.add(BLACK, 28  , '000011001100')
    BitParser.add(BLACK, 29  , '000011001101')
    BitParser.add(BLACK, 30  , '000001101000')
    BitParser.add(BLACK, 31  , '000001101001')
    BitParser.add(BLACK, 32  , '000001101010')
    BitParser.add(BLACK, 33  , '000001101011')
    BitParser.add(BLACK, 34  , '000011010010')
    BitParser.add(BLACK, 35  , '000011010011')
    BitParser.add(BLACK, 36  , '000011010100')
    BitParser.add(BLACK, 37  , '000011010101')
    BitParser.add(BLACK, 38  , '000011010110')
    BitParser.add(BLACK, 39  , '000011010111')
    BitParser.add(BLACK, 40  , '000001101100')
    BitParser.add(BLACK, 41  , '000001101101')
    BitParser.add(BLACK, 42  , '000011011010')
    BitParser.add(BLACK, 43  , '000011011011')
    BitParser.add(BLACK, 44  , '000001010100')
    BitParser.add(BLACK, 45  , '000001010101')
    BitParser.add(BLACK, 46  , '000001010110')
    BitParser.add(BLACK, 47  , '000001010111')
    BitParser.add(BLACK, 48  , '000001100100')
    BitParser.add(BLACK, 49  , '000001100101')
    BitParser.add(BLACK, 50  , '000001010010')
    BitParser.add(BLACK, 51  , '000001010011')
    BitParser.add(BLACK, 52  , '000000100100')
    BitParser.add(BLACK, 53  , '000000110111')
    BitParser.add(BLACK, 54  , '000000111000')
    BitParser.add(BLACK, 55  , '000000100111')
    BitParser.add(BLACK, 56  , '000000101000')
    BitParser.add(BLACK, 57  , '000001011000')
    BitParser.add(BLACK, 58  , '000001011001')
    BitParser.add(BLACK, 59  , '000000101011')
    BitParser.add(BLACK, 60  , '000000101100')
    BitParser.add(BLACK, 61  , '000001011010')
    BitParser.add(BLACK, 62  , '000001100110')
    BitParser.add(BLACK, 63  , '000001100111')
    BitParser.add(BLACK, 64  , '0000001111')
    BitParser.add(BLACK, 128 , '000011001000')
    BitParser.add(BLACK, 192 , '000011001001')
    BitParser.add(BLACK, 256 , '000001011011')
    BitParser.add(BLACK, 320 , '000000110011')
    BitParser.add(BLACK, 384 , '000000110100')
    BitParser.add(BLACK, 448 , '000000110101')
    BitParser.add(BLACK, 512 , '0000001101100')
    BitParser.add(BLACK, 576 , '0000001101101')
    BitParser.add(BLACK, 640 , '0000001001010')
    BitParser.add(BLACK, 704 , '0000001001011')
    BitParser.add(BLACK, 768 , '0000001001100')
    BitParser.add(BLACK, 832 , '0000001001101')
    BitParser.add(BLACK, 896 , '0000001110010')
    BitParser.add(BLACK, 960 , '0000001110011')
    BitParser.add(BLACK, 1024, '0000001110100')
    BitParser.add(BLACK, 1088, '0000001110101')
    BitParser.add(BLACK, 1152, '0000001110110')
    BitParser.add(BLACK, 1216, '0000001110111')
    BitParser.add(BLACK, 1280, '0000001010010')
    BitParser.add(BLACK, 1344, '0000001010011')
    BitParser.add(BLACK, 1408, '0000001010100')
    BitParser.add(BLACK, 1472, '0000001010101')
    BitParser.add(BLACK, 1536, '0000001011010')
    BitParser.add(BLACK, 1600, '0000001011011')
    BitParser.add(BLACK, 1664, '0000001100100')
    BitParser.add(BLACK, 1728, '0000001100101')
    BitParser.add(BLACK, 1792, '00000001000')
    BitParser.add(BLACK, 1856, '00000001100')
    BitParser.add(BLACK, 1920, '00000001101')
    BitParser.add(BLACK, 1984, '000000010010')
    BitParser.add(BLACK, 2048, '000000010011')
    BitParser.add(BLACK, 2112, '000000010100')
    BitParser.add(BLACK, 2176, '000000010101')
    BitParser.add(BLACK, 2240, '000000010110')
    BitParser.add(BLACK, 2304, '000000010111')
    BitParser.add(BLACK, 2368, '000000011100')
    BitParser.add(BLACK, 2432, '000000011101')
    BitParser.add(BLACK, 2496, '000000011110')
    BitParser.add(BLACK, 2560, '000000011111')

    UNCOMPRESSED = [None, None]
    BitParser.add(UNCOMPRESSED, '1', '1')
    BitParser.add(UNCOMPRESSED, '01', '01')
    BitParser.add(UNCOMPRESSED, '001', '001')
    BitParser.add(UNCOMPRESSED, '0001', '0001')
    BitParser.add(UNCOMPRESSED, '00001', '00001')
    BitParser.add(UNCOMPRESSED, '00000', '000001')
    BitParser.add(UNCOMPRESSED, 'T00', '00000011')
    BitParser.add(UNCOMPRESSED, 'T10', '00000010')
    BitParser.add(UNCOMPRESSED, 'T000', '000000011')
    BitParser.add(UNCOMPRESSED, 'T100', '000000010')
    BitParser.add(UNCOMPRESSED, 'T0000', '0000000011')
    BitParser.add(UNCOMPRESSED, 'T1000', '0000000010')
    BitParser.add(UNCOMPRESSED, 'T00000', '00000000011')
    BitParser.add(UNCOMPRESSED, 'T10000', '00000000010')

    class EOFB(Exception):
        pass

    class InvalidData(Exception):
        pass

    class ByteSkip(Exception):
        pass

    def __init__(self, width, bytealign=False):
        BitParser.__init__(self)
        self.width = width
        self.bytealign = bytealign
        self.reset()
        return

    def feedbytes(self, data):
        for c in data:
            b = ord(c)
            try:
                for m in (128, 64, 32, 16, 8, 4, 2, 1):
                    self._parse_bit(b & m)
            except self.ByteSkip:
                self._accept = self._parse_mode
                self._state = self.MODE
            except self.EOFB:
                break
        return

    def _parse_mode(self, mode):
        if mode == 'p':
            self._do_pass()
            self._flush_line()
            return self.MODE
        elif mode == 'h':
            self._n1 = 0
            self._accept = self._parse_horiz1
            if self._color:
                return self.WHITE
            else:
                return self.BLACK
        elif mode == 'u':
            self._accept = self._parse_uncompressed
            return self.UNCOMPRESSED
        elif mode == 'e':
            raise self.EOFB
        elif isinstance(mode, int):
            self._do_vertical(mode)
            self._flush_line()
            return self.MODE
        else:
            raise self.InvalidData(mode)

    def _parse_horiz1(self, n):
        if n is None:
            raise self.InvalidData
        self._n1 += n
        if n < 64:
            self._n2 = 0
            self._color = 1-self._color
            self._accept = self._parse_horiz2
        if self._color:
            return self.WHITE
        else:
            return self.BLACK

    def _parse_horiz2(self, n):
        if n is None:
            raise self.InvalidData
        self._n2 += n
        if n < 64:
            self._color = 1-self._color
            self._accept = self._parse_mode
            self._do_horizontal(self._n1, self._n2)
            self._flush_line()
            return self.MODE
        elif self._color:
            return self.WHITE
        else:
            return self.BLACK

    def _parse_uncompressed(self, bits):
        if not bits:
            raise self.InvalidData
        if bits.startswith('T'):
            self._accept = self._parse_mode
            self._color = int(bits[1])
            self._do_uncompressed(bits[2:])
            return self.MODE
        else:
            self._do_uncompressed(bits)
            return self.UNCOMPRESSED

    def _get_bits(self):
        return ''.join(str(b) for b in self._curline[:self._curpos])

    def _get_refline(self, i):
        if i < 0:
            return '[]'+''.join(str(b) for b in self._refline)
        elif len(self._refline) <= i:
            return ''.join(str(b) for b in self._refline)+'[]'
        else:
            return (''.join(str(b) for b in self._refline[:i]) +
                    '['+str(self._refline[i])+']' +
                    ''.join(str(b) for b in self._refline[i+1:]))

    def reset(self):
        self._y = 0
        self._curline = array.array('b', [1]*self.width)
        self._reset_line()
        self._accept = self._parse_mode
        self._state = self.MODE
        return

    def output_line(self, y, bits):
        print y, ''.join(str(b) for b in bits)
        return

    def _reset_line(self):
        self._refline = self._curline
        self._curline = array.array('b', [1]*self.width)
        self._curpos = -1
        self._color = 1
        return

    def _flush_line(self):
        if self.width <= self._curpos:
            self.output_line(self._y, self._curline)
            self._y += 1
            self._reset_line()
            if self.bytealign:
                raise self.ByteSkip
        return

    def _do_vertical(self, dx):
        #print '* vertical(%d): curpos=%r, color=%r' % (dx, self._curpos, self._color)
        #print '  refline:', self._get_refline(self._curpos+1)
        x1 = self._curpos+1
        while 1:
            if x1 == 0:
                if (self._color == 1 and self._refline[x1] != self._color):
                    break
            elif x1 == len(self._refline):
                break
            elif (self._refline[x1-1] == self._color and
                  self._refline[x1] != self._color):
                break
            x1 += 1
        x1 += dx
        x0 = max(0, self._curpos)
        x1 = max(0, min(self.width, x1))
        if x1 < x0:
            for x in xrange(x1, x0):
                self._curline[x] = self._color
        elif x0 < x1:
            for x in xrange(x0, x1):
                self._curline[x] = self._color
        self._curpos = x1
        self._color = 1-self._color
        return

    def _do_pass(self):
        #print '* pass: curpos=%r, color=%r' % (self._curpos, self._color)
        #print '  refline:', self._get_refline(self._curpos+1)
        x1 = self._curpos+1
        while 1:
            if x1 == 0:
                if (self._color == 1 and self._refline[x1] != self._color):
                    break
            elif x1 == len(self._refline):
                break
            elif (self._refline[x1-1] == self._color and
                  self._refline[x1] != self._color):
                break
            x1 += 1
        while 1:
            if x1 == 0:
                if (self._color == 0 and self._refline[x1] == self._color):
                    break
            elif x1 == len(self._refline):
                break
            elif (self._refline[x1-1] != self._color and
                  self._refline[x1] == self._color):
                break
            x1 += 1
        for x in xrange(self._curpos, x1):
            self._curline[x] = self._color
        self._curpos = x1
        return

    def _do_horizontal(self, n1, n2):
        #print '* horizontal(%d,%d): curpos=%r, color=%r' % (n1, n2, self._curpos, self._color)
        if self._curpos < 0:
            self._curpos = 0
        x = self._curpos
        for _ in xrange(n1):
            if len(self._curline) <= x:
                break
            self._curline[x] = self._color
            x += 1
        for _ in xrange(n2):
            if len(self._curline) <= x:
                break
            self._curline[x] = 1-self._color
            x += 1
        self._curpos = x
        return

    def _do_uncompressed(self, bits):
        #print '* uncompressed(%r): curpos=%r' % (bits, self._curpos)
        for c in bits:
            self._curline[self._curpos] = int(c)
            self._curpos += 1
            self._flush_line()
        return

import unittest


##  Test cases
##
class TestCCITTG4Parser(unittest.TestCase):

    def get_parser(self, bits):
        parser = CCITTG4Parser(len(bits))
        parser._curline = [int(c) for c in bits]
        parser._reset_line()
        return parser

    def test_b1(self):
        parser = self.get_parser('00000')
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 0)
        return

    def test_b2(self):
        parser = self.get_parser('10000')
        parser._do_vertical(-1)
        self.assertEqual(parser._curpos, 0)
        return

    def test_b3(self):
        parser = self.get_parser('000111')
        parser._do_pass()
        self.assertEqual(parser._curpos, 3)
        self.assertEqual(parser._get_bits(), '111')
        return

    def test_b4(self):
        parser = self.get_parser('00000')
        parser._do_vertical(+2)
        self.assertEqual(parser._curpos, 2)
        self.assertEqual(parser._get_bits(), '11')
        return

    def test_b5(self):
        parser = self.get_parser('11111111100')
        parser._do_horizontal(0, 3)
        self.assertEqual(parser._curpos, 3)
        parser._do_vertical(1)
        self.assertEqual(parser._curpos, 10)
        self.assertEqual(parser._get_bits(), '0001111111')
        return

    def test_e1(self):
        parser = self.get_parser('10000')
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 1)
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 5)
        self.assertEqual(parser._get_bits(), '10000')
        return

    def test_e2(self):
        parser = self.get_parser('10011')
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 1)
        parser._do_vertical(2)
        self.assertEqual(parser._curpos, 5)
        self.assertEqual(parser._get_bits(), '10000')
        return

    def test_e3(self):
        parser = self.get_parser('011111')
        parser._color = 0
        parser._do_vertical(0)
        self.assertEqual(parser._color, 1)
        self.assertEqual(parser._curpos, 1)
        parser._do_vertical(-2)
        self.assertEqual(parser._color, 0)
        self.assertEqual(parser._curpos, 4)
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 6)
        self.assertEqual(parser._get_bits(), '011100')
        return

    def test_e4(self):
        parser = self.get_parser('10000')
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 1)
        parser._do_vertical(-2)
        self.assertEqual(parser._curpos, 3)
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 5)
        self.assertEqual(parser._get_bits(), '10011')
        return

    def test_e5(self):
        parser = self.get_parser('011000')
        parser._color = 0
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 1)
        parser._do_vertical(3)
        self.assertEqual(parser._curpos, 6)
        self.assertEqual(parser._get_bits(), '011111')
        return

    def test_e6(self):
        parser = self.get_parser('11001')
        parser._do_pass()
        self.assertEqual(parser._curpos, 4)
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 5)
        self.assertEqual(parser._get_bits(), '11111')
        return

    def test_e7(self):
        parser = self.get_parser('0000000000')
        parser._curpos = 2
        parser._color = 1
        parser._do_horizontal(2, 6)
        self.assertEqual(parser._curpos, 10)
        self.assertEqual(parser._get_bits(), '1111000000')
        return

    def test_e8(self):
        parser = self.get_parser('001100000')
        parser._curpos = 1
        parser._color = 0
        parser._do_vertical(0)
        self.assertEqual(parser._curpos, 2)
        parser._do_horizontal(7, 0)
        self.assertEqual(parser._curpos, 9)
        self.assertEqual(parser._get_bits(), '101111111')
        return

    def test_m1(self):
        parser = self.get_parser('10101')
        parser._do_pass()
        self.assertEqual(parser._curpos, 2)
        parser._do_pass()
        self.assertEqual(parser._curpos, 4)
        self.assertEqual(parser._get_bits(), '1111')
        return

    def test_m2(self):
        parser = self.get_parser('101011')
        parser._do_vertical(-1)
        parser._do_vertical(-1)
        parser._do_vertical(1)
        parser._do_horizontal(1, 1)
        self.assertEqual(parser._get_bits(), '011101')
        return

    def test_m3(self):
        parser = self.get_parser('10111011')
        parser._do_vertical(-1)
        parser._do_pass()
        parser._do_vertical(1)
        parser._do_vertical(1)
        self.assertEqual(parser._get_bits(), '00000001')
        return


##  CCITTFaxDecoder
##
class CCITTFaxDecoder(CCITTG4Parser):

    def __init__(self, width, bytealign=False, reversed=False):
        CCITTG4Parser.__init__(self, width, bytealign=bytealign)
        self.reversed = reversed
        self._buf = ''
        return

    def close(self):
        return self._buf

    def output_line(self, y, bits):
        bytes = array.array('B', [0]*((len(bits)+7)//8))
        if self.reversed:
            bits = [1-b for b in bits]
        for (i, b) in enumerate(bits):
            if b:
                bytes[i//8] += (128, 64, 32, 16, 8, 4, 2, 1)[i % 8]
        self._buf += bytes.tostring()
        return


def ccittfaxdecode(data, params):
    K = params.get('K')
    cols = params.get('Columns')
    bytealign = params.get('EncodedByteAlign')
    reversed = params.get('BlackIs1')
    if K == -1:
        parser = CCITTFaxDecoder(cols, bytealign=bytealign, reversed=reversed)
    else:
        raise ValueError(K)
    parser.feedbytes(data)
    return parser.close()


# test
def main(argv):
    import pygame
    if not argv[1:]:
        return unittest.main()

    class Parser(CCITTG4Parser):
        def __init__(self, width, bytealign=False):
            CCITTG4Parser.__init__(self, width, bytealign=bytealign)
            self.img = pygame.Surface((self.width, 1000))
            return

        def output_line(self, y, bits):
            for (x, b) in enumerate(bits):
                if b:
                    self.img.set_at((x, y), (255, 255, 255))
                else:
                    self.img.set_at((x, y), (0, 0, 0))
            return

        def close(self):
            pygame.image.save(self.img, 'out.bmp')
            return
    for path in argv[1:]:
        fp = file(path, 'rb')
        (_, _, k, w, h, _) = path.split('.')
        parser = Parser(int(w))
        parser.feedbytes(fp.read())
        parser.close()
        fp.close()
    return

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = cmapdb
#!/usr/bin/env python

""" Adobe character mapping (CMap) support.

CMaps provide the mapping between character codes and Unicode
code-points to character ids (CIDs).

More information is available on the Adobe website:

  http://opensource.adobe.com/wiki/display/cmap/CMap+Resources

"""

import sys
import os
import os.path
import gzip
import cPickle as pickle
import struct
from psparser import PSStackParser
from psparser import PSSyntaxError, PSEOF
from psparser import PSLiteral
from psparser import literal_name
from encodingdb import name2unicode
from utils import choplist, nunpack


class CMapError(Exception):
    pass


##  CMapBase
##
class CMapBase(object):

    debug = 0

    def __init__(self, **kwargs):
        self.attrs = kwargs.copy()
        return

    def is_vertical(self):
        return self.attrs.get('WMode', 0) != 0

    def set_attr(self, k, v):
        self.attrs[k] = v
        return

    def add_code2cid(self, code, cid):
        return

    def add_cid2unichr(self, cid, code):
        return

    def use_cmap(self, cmap):
        return


##  CMap
##
class CMap(CMapBase):

    def __init__(self, **kwargs):
        CMapBase.__init__(self, **kwargs)
        self.code2cid = {}
        return

    def __repr__(self):
        return '<CMap: %s>' % self.attrs.get('CMapName')

    def use_cmap(self, cmap):
        assert isinstance(cmap, CMap)

        def copy(dst, src):
            for (k, v) in src.iteritems():
                if isinstance(v, dict):
                    d = {}
                    dst[k] = d
                    copy(d, v)
                else:
                    dst[k] = v
        copy(self.code2cid, cmap.code2cid)
        return

    def decode(self, code):
        if self.debug:
            print >>sys.stderr, 'decode: %r, %r' % (self, code)
        d = self.code2cid
        for c in code:
            c = ord(c)
            if c in d:
                d = d[c]
                if isinstance(d, int):
                    yield d
                    d = self.code2cid
            else:
                d = self.code2cid
        return

    def dump(self, out=sys.stdout, code2cid=None, code=None):
        if code2cid is None:
            code2cid = self.code2cid
            code = ()
        for (k, v) in sorted(code2cid.iteritems()):
            c = code+(k,)
            if isinstance(v, int):
                out.write('code %r = cid %d\n' % (c, v))
            else:
                self.dump(out=out, code2cid=v, code=c)
        return


##  IdentityCMap
##
class IdentityCMap(CMapBase):

    def decode(self, code):
        n = len(code)//2
        if n:
            return struct.unpack('>%dH' % n, code)
        else:
            return ()


##  UnicodeMap
##
class UnicodeMap(CMapBase):

    def __init__(self, **kwargs):
        CMapBase.__init__(self, **kwargs)
        self.cid2unichr = {}
        return

    def __repr__(self):
        return '<UnicodeMap: %s>' % self.attrs.get('CMapName')

    def get_unichr(self, cid):
        if self.debug:
            print >>sys.stderr, 'get_unichr: %r, %r' % (self, cid)
        return self.cid2unichr[cid]

    def dump(self, out=sys.stdout):
        for (k, v) in sorted(self.cid2unichr.iteritems()):
            out.write('cid %d = unicode %r\n' % (k, v))
        return


##  FileCMap
##
class FileCMap(CMap):

    def add_code2cid(self, code, cid):
        assert isinstance(code, str) and isinstance(cid, int)
        d = self.code2cid
        for c in code[:-1]:
            c = ord(c)
            if c in d:
                d = d[c]
            else:
                t = {}
                d[c] = t
                d = t
        c = ord(code[-1])
        d[c] = cid
        return


##  FileUnicodeMap
##
class FileUnicodeMap(UnicodeMap):

    def add_cid2unichr(self, cid, code):
        assert isinstance(cid, int)
        if isinstance(code, PSLiteral):
            # Interpret as an Adobe glyph name.
            self.cid2unichr[cid] = name2unicode(code.name)
        elif isinstance(code, str):
            # Interpret as UTF-16BE.
            self.cid2unichr[cid] = unicode(code, 'UTF-16BE', 'ignore')
        elif isinstance(code, int):
            self.cid2unichr[cid] = unichr(code)
        else:
            raise TypeError(code)
        return


##  PyCMap
##
class PyCMap(CMap):

    def __init__(self, name, module):
        CMap.__init__(self, CMapName=name)
        self.code2cid = module.CODE2CID
        if module.IS_VERTICAL:
            self.attrs['WMode'] = 1
        return


##  PyUnicodeMap
##
class PyUnicodeMap(UnicodeMap):

    def __init__(self, name, module, vertical):
        UnicodeMap.__init__(self, CMapName=name)
        if vertical:
            self.cid2unichr = module.CID2UNICHR_V
            self.attrs['WMode'] = 1
        else:
            self.cid2unichr = module.CID2UNICHR_H
        return


##  CMapDB
##
class CMapDB(object):

    debug = 0
    _cmap_cache = {}
    _umap_cache = {}

    class CMapNotFound(CMapError):
        pass

    @classmethod
    def _load_data(klass, name):
        filename = '%s.pickle.gz' % name
        if klass.debug:
            print >>sys.stderr, 'loading:', name
        cmap_paths = (os.environ.get('CMAP_PATH', '/usr/share/pdfminer/'),
                      os.path.join(os.path.dirname(__file__), 'cmap'),)
        for directory in cmap_paths:
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                gzfile = gzip.open(path)
                try:
                    return type(name, (), pickle.loads(gzfile.read()))
                finally:
                    gzfile.close()
        else:
            raise CMapDB.CMapNotFound(name)

    @classmethod
    def get_cmap(klass, name):
        if name == 'Identity-H':
            return IdentityCMap(WMode=0)
        elif name == 'Identity-V':
            return IdentityCMap(WMode=1)
        try:
            return klass._cmap_cache[name]
        except KeyError:
            pass
        data = klass._load_data(name)
        klass._cmap_cache[name] = cmap = PyCMap(name, data)
        return cmap

    @classmethod
    def get_unicode_map(klass, name, vertical=False):
        try:
            return klass._umap_cache[name][vertical]
        except KeyError:
            pass
        data = klass._load_data('to-unicode-%s' % name)
        klass._umap_cache[name] = umaps = [PyUnicodeMap(name, data, v) for v in (False, True)]
        return umaps[vertical]


##  CMapParser
##
class CMapParser(PSStackParser):

    def __init__(self, cmap, fp):
        PSStackParser.__init__(self, fp)
        self.cmap = cmap
        # some ToUnicode maps don't have "begincmap" keyword.
        self._in_cmap = True
        return

    def run(self):
        try:
            self.nextobject()
        except PSEOF:
            pass
        return

    def do_keyword(self, pos, token):
        name = token.name
        if name == 'begincmap':
            self._in_cmap = True
            self.popall()
            return
        elif name == 'endcmap':
            self._in_cmap = False
            return
        if not self._in_cmap:
            return
        #
        if name == 'def':
            try:
                ((_, k), (_, v)) = self.pop(2)
                self.cmap.set_attr(literal_name(k), v)
            except PSSyntaxError:
                pass
            return

        if name == 'usecmap':
            try:
                ((_, cmapname),) = self.pop(1)
                self.cmap.use_cmap(CMapDB.get_cmap(literal_name(cmapname)))
            except PSSyntaxError:
                pass
            except CMapDB.CMapNotFound:
                pass
            return

        if name == 'begincodespacerange':
            self.popall()
            return
        if name == 'endcodespacerange':
            self.popall()
            return

        if name == 'begincidrange':
            self.popall()
            return
        if name == 'endcidrange':
            objs = [obj for (__, obj) in self.popall()]
            for (s, e, cid) in choplist(3, objs):
                if (not isinstance(s, str) or not isinstance(e, str) or
                   not isinstance(cid, int) or len(s) != len(e)):
                    continue
                sprefix = s[:-4]
                eprefix = e[:-4]
                if sprefix != eprefix:
                    continue
                svar = s[-4:]
                evar = e[-4:]
                s1 = nunpack(svar)
                e1 = nunpack(evar)
                vlen = len(svar)
                #assert s1 <= e1
                for i in xrange(e1-s1+1):
                    x = sprefix+struct.pack('>L', s1+i)[-vlen:]
                    self.cmap.add_code2cid(x, cid+i)
            return

        if name == 'begincidchar':
            self.popall()
            return
        if name == 'endcidchar':
            objs = [obj for (__, obj) in self.popall()]
            for (cid, code) in choplist(2, objs):
                if isinstance(code, str) and isinstance(cid, str):
                    self.cmap.add_code2cid(code, nunpack(cid))
            return

        if name == 'beginbfrange':
            self.popall()
            return
        if name == 'endbfrange':
            objs = [obj for (__, obj) in self.popall()]
            for (s, e, code) in choplist(3, objs):
                if (not isinstance(s, str) or not isinstance(e, str) or
                   len(s) != len(e)):
                        continue
                s1 = nunpack(s)
                e1 = nunpack(e)
                #assert s1 <= e1
                if isinstance(code, list):
                    for i in xrange(e1-s1+1):
                        self.cmap.add_cid2unichr(s1+i, code[i])
                else:
                    var = code[-4:]
                    base = nunpack(var)
                    prefix = code[:-4]
                    vlen = len(var)
                    for i in xrange(e1-s1+1):
                        x = prefix+struct.pack('>L', base+i)[-vlen:]
                        self.cmap.add_cid2unichr(s1+i, x)
            return

        if name == 'beginbfchar':
            self.popall()
            return
        if name == 'endbfchar':
            objs = [obj for (__, obj) in self.popall()]
            for (cid, code) in choplist(2, objs):
                if isinstance(cid, str) and isinstance(code, str):
                    self.cmap.add_cid2unichr(nunpack(cid), code)
            return

        if name == 'beginnotdefrange':
            self.popall()
            return
        if name == 'endnotdefrange':
            self.popall()
            return

        self.push((pos, token))
        return


# test
def main(argv):
    args = argv[1:]
    for fname in args:
        fp = file(fname, 'rb')
        cmap = FileUnicodeMap()
        #cmap = FileCMap()
        CMapParser(cmap, fp).run()
        fp.close()
        cmap.dump()
    return

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = converter
#!/usr/bin/env python
import sys
from pdfdevice import PDFTextDevice
from pdffont import PDFUnicodeNotDefined
from layout import LTContainer, LTPage, LTText, LTLine, LTRect, LTCurve
from layout import LTFigure, LTImage, LTChar, LTTextLine
from layout import LTTextBox, LTTextBoxVertical, LTTextGroup
from utils import apply_matrix_pt, mult_matrix
from utils import enc, bbox2str


##  PDFLayoutAnalyzer
##
class PDFLayoutAnalyzer(PDFTextDevice):

    def __init__(self, rsrcmgr, pageno=1, laparams=None):
        PDFTextDevice.__init__(self, rsrcmgr)
        self.pageno = pageno
        self.laparams = laparams
        self._stack = []
        return

    def begin_page(self, page, ctm):
        (x0, y0, x1, y1) = page.mediabox
        (x0, y0) = apply_matrix_pt(ctm, (x0, y0))
        (x1, y1) = apply_matrix_pt(ctm, (x1, y1))
        mediabox = (0, 0, abs(x0-x1), abs(y0-y1))
        self.cur_item = LTPage(self.pageno, mediabox)
        return

    def end_page(self, page):
        assert not self._stack
        assert isinstance(self.cur_item, LTPage)
        if self.laparams is not None:
            self.cur_item.analyze(self.laparams)
        self.pageno += 1
        self.receive_layout(self.cur_item)
        return

    def begin_figure(self, name, bbox, matrix):
        self._stack.append(self.cur_item)
        self.cur_item = LTFigure(name, bbox, mult_matrix(matrix, self.ctm))
        return

    def end_figure(self, _):
        fig = self.cur_item
        assert isinstance(self.cur_item, LTFigure)
        self.cur_item = self._stack.pop()
        self.cur_item.add(fig)
        return

    def render_image(self, name, stream):
        assert isinstance(self.cur_item, LTFigure)
        item = LTImage(name, stream,
                       (self.cur_item.x0, self.cur_item.y0,
                        self.cur_item.x1, self.cur_item.y1))
        self.cur_item.add(item)
        return

    def paint_path(self, gstate, stroke, fill, evenodd, path):
        shape = ''.join(x[0] for x in path)
        if shape == 'ml':
            # horizontal/vertical line
            (_, x0, y0) = path[0]
            (_, x1, y1) = path[1]
            (x0, y0) = apply_matrix_pt(self.ctm, (x0, y0))
            (x1, y1) = apply_matrix_pt(self.ctm, (x1, y1))
            if x0 == x1 or y0 == y1:
                self.cur_item.add(LTLine(gstate.linewidth, (x0, y0), (x1, y1)))
                return
        if shape == 'mlllh':
            # rectangle
            (_, x0, y0) = path[0]
            (_, x1, y1) = path[1]
            (_, x2, y2) = path[2]
            (_, x3, y3) = path[3]
            (x0, y0) = apply_matrix_pt(self.ctm, (x0, y0))
            (x1, y1) = apply_matrix_pt(self.ctm, (x1, y1))
            (x2, y2) = apply_matrix_pt(self.ctm, (x2, y2))
            (x3, y3) = apply_matrix_pt(self.ctm, (x3, y3))
            if ((x0 == x1 and y1 == y2 and x2 == x3 and y3 == y0) or
                (y0 == y1 and x1 == x2 and y2 == y3 and x3 == x0)):
                self.cur_item.add(LTRect(gstate.linewidth, (x0, y0, x2, y2)))
                return
        # other shapes
        pts = []
        for p in path:
            for i in xrange(1, len(p), 2):
                pts.append(apply_matrix_pt(self.ctm, (p[i], p[i+1])))
        self.cur_item.add(LTCurve(gstate.linewidth, pts))
        return

    def render_char(self, matrix, font, fontsize, scaling, rise, cid):
        try:
            text = font.to_unichr(cid)
            assert isinstance(text, unicode), text
        except PDFUnicodeNotDefined:
            text = self.handle_undefined_char(font, cid)
        textwidth = font.char_width(cid)
        textdisp = font.char_disp(cid)
        item = LTChar(matrix, font, fontsize, scaling, rise, text, textwidth, textdisp)
        self.cur_item.add(item)
        return item.adv

    def handle_undefined_char(self, font, cid):
        if self.debug:
            print >>sys.stderr, 'undefined: %r, %r' % (font, cid)
        return '(cid:%d)' % cid

    def receive_layout(self, ltpage):
        return


##  PDFPageAggregator
##
class PDFPageAggregator(PDFLayoutAnalyzer):

    def __init__(self, rsrcmgr, pageno=1, laparams=None):
        PDFLayoutAnalyzer.__init__(self, rsrcmgr, pageno=pageno, laparams=laparams)
        self.result = None
        return

    def receive_layout(self, ltpage):
        self.result = ltpage
        return

    def get_result(self):
        return self.result


##  PDFConverter
##
class PDFConverter(PDFLayoutAnalyzer):

    def __init__(self, rsrcmgr, outfp, codec='utf-8', pageno=1, laparams=None):
        PDFLayoutAnalyzer.__init__(self, rsrcmgr, pageno=pageno, laparams=laparams)
        self.outfp = outfp
        self.codec = codec
        return


##  TextConverter
##
class TextConverter(PDFConverter):

    def __init__(self, rsrcmgr, outfp, codec='utf-8', pageno=1, laparams=None,
                 showpageno=False, imagewriter=None):
        PDFConverter.__init__(self, rsrcmgr, outfp, codec=codec, pageno=pageno, laparams=laparams)
        self.showpageno = showpageno
        self.imagewriter = imagewriter
        return

    def write_text(self, text):
        self.outfp.write(text.encode(self.codec, 'ignore'))
        return

    def receive_layout(self, ltpage):
        def render(item):
            if isinstance(item, LTContainer):
                for child in item:
                    render(child)
            elif isinstance(item, LTText):
                self.write_text(item.get_text())
            if isinstance(item, LTTextBox):
                self.write_text('\n')
            elif isinstance(item, LTImage):
                if self.imagewriter is not None:
                    self.imagewriter.export_image(item)
        if self.showpageno:
            self.write_text('Page %s\n' % ltpage.pageid)
        render(ltpage)
        self.write_text('\f')
        return

    # Some dummy functions to save memory/CPU when all that is wanted
    # is text.  This stops all the image and drawing ouput from being
    # recorded and taking up RAM.
    def render_image(self, name, stream):
        if self.imagewriter is None:
            return
        PDFConverter.render_image(self, name, stream)
        return

    def paint_path(self, gstate, stroke, fill, evenodd, path):
        return


##  HTMLConverter
##
class HTMLConverter(PDFConverter):

    RECT_COLORS = {
        #'char': 'green',
        'figure': 'yellow',
        'textline': 'magenta',
        'textbox': 'cyan',
        'textgroup': 'red',
        'curve': 'black',
        'page': 'gray',
    }

    TEXT_COLORS = {
        'textbox': 'blue',
        'char': 'black',
    }

    def __init__(self, rsrcmgr, outfp, codec='utf-8', pageno=1, laparams=None,
                 scale=1, fontscale=1.0, layoutmode='normal', showpageno=True,
                 pagemargin=50, imagewriter=None,
                 rect_colors={'curve': 'black', 'page': 'gray'},
                 text_colors={'char': 'black'}):
        PDFConverter.__init__(self, rsrcmgr, outfp, codec=codec, pageno=pageno, laparams=laparams)
        self.scale = scale
        self.fontscale = fontscale
        self.layoutmode = layoutmode
        self.showpageno = showpageno
        self.pagemargin = pagemargin
        self.imagewriter = imagewriter
        self.rect_colors = rect_colors
        self.text_colors = text_colors
        if self.debug:
            self.rect_colors.update(self.RECT_COLORS)
            self.text_colors.update(self.TEXT_COLORS)
        self._yoffset = self.pagemargin
        self._font = None
        self._fontstack = []
        self.write_header()
        return

    def write(self, text):
        self.outfp.write(text)
        return

    def write_header(self):
        self.write('<html><head>\n')
        self.write('<meta http-equiv="Content-Type" content="text/html; charset=%s">\n' % self.codec)
        self.write('</head><body>\n')
        return

    def write_footer(self):
        self.write('<div style="position:absolute; top:0px;">Page: %s</div>\n' %
                   ', '.join('<a href="#%s">%s</a>' % (i, i) for i in xrange(1, self.pageno)))
        self.write('</body></html>\n')
        return

    def write_text(self, text):
        self.write(enc(text, self.codec))
        return

    def place_rect(self, color, borderwidth, x, y, w, h):
        color = self.rect_colors.get(color)
        if color is not None:
            self.write('<span style="position:absolute; border: %s %dpx solid; '
                       'left:%dpx; top:%dpx; width:%dpx; height:%dpx;"></span>\n' %
                       (color, borderwidth,
                        x*self.scale, (self._yoffset-y)*self.scale,
                        w*self.scale, h*self.scale))
        return

    def place_border(self, color, borderwidth, item):
        self.place_rect(color, borderwidth, item.x0, item.y1, item.width, item.height)
        return

    def place_image(self, item, borderwidth, x, y, w, h):
        if self.imagewriter is not None:
            name = self.imagewriter.export_image(item)
            self.write('<img src="%s" border="%d" style="position:absolute; left:%dpx; top:%dpx;" '
                       'width="%d" height="%d" />\n' %
                       (enc(name), borderwidth,
                        x*self.scale, (self._yoffset-y)*self.scale,
                        w*self.scale, h*self.scale))
        return

    def place_text(self, color, text, x, y, size):
        color = self.text_colors.get(color)
        if color is not None:
            self.write('<span style="position:absolute; color:%s; left:%dpx; top:%dpx; font-size:%dpx;">' %
                       (color, x*self.scale, (self._yoffset-y)*self.scale, size*self.scale*self.fontscale))
            self.write_text(text)
            self.write('</span>\n')
        return

    def begin_div(self, color, borderwidth, x, y, w, h, writing_mode=False):
        self._fontstack.append(self._font)
        self._font = None
        self.write('<div style="position:absolute; border: %s %dpx solid; writing-mode:%s; '
                   'left:%dpx; top:%dpx; width:%dpx; height:%dpx;">' %
                   (color, borderwidth, writing_mode,
                    x*self.scale, (self._yoffset-y)*self.scale,
                    w*self.scale, h*self.scale))
        return

    def end_div(self, color):
        if self._font is not None:
            self.write('</span>')
        self._font = self._fontstack.pop()
        self.write('</div>')
        return

    def put_text(self, text, fontname, fontsize):
        font = (fontname, fontsize)
        if font != self._font:
            if self._font is not None:
                self.write('</span>')
            self.write('<span style="font-family: %s; font-size:%dpx">' %
                       (fontname, fontsize * self.scale * self.fontscale))
            self._font = font
        self.write_text(text)
        return

    def put_newline(self):
        self.write('<br>')
        return

    def receive_layout(self, ltpage):
        def show_group(item):
            if isinstance(item, LTTextGroup):
                self.place_border('textgroup', 1, item)
                for child in item:
                    show_group(child)
            return

        def render(item):
            if isinstance(item, LTPage):
                self._yoffset += item.y1
                self.place_border('page', 1, item)
                if self.showpageno:
                    self.write('<div style="position:absolute; top:%dpx;">' %
                               ((self._yoffset-item.y1)*self.scale))
                    self.write('<a name="%s">Page %s</a></div>\n' % (item.pageid, item.pageid))
                for child in item:
                    render(child)
                if item.groups is not None:
                    for group in item.groups:
                        show_group(group)
            elif isinstance(item, LTCurve):
                self.place_border('curve', 1, item)
            elif isinstance(item, LTFigure):
                self.begin_div('figure', 1, item.x0, item.y1, item.width, item.height)
                for child in item:
                    render(child)
                self.end_div('figure')
            elif isinstance(item, LTImage):
                self.place_image(item, 1, item.x0, item.y1, item.width, item.height)
            else:
                if self.layoutmode == 'exact':
                    if isinstance(item, LTTextLine):
                        self.place_border('textline', 1, item)
                        for child in item:
                            render(child)
                    elif isinstance(item, LTTextBox):
                        self.place_border('textbox', 1, item)
                        self.place_text('textbox', str(item.index+1), item.x0, item.y1, 20)
                        for child in item:
                            render(child)
                    elif isinstance(item, LTChar):
                        self.place_border('char', 1, item)
                        self.place_text('char', item.get_text(), item.x0, item.y1, item.size)
                else:
                    if isinstance(item, LTTextLine):
                        for child in item:
                            render(child)
                        if self.layoutmode != 'loose':
                            self.put_newline()
                    elif isinstance(item, LTTextBox):
                        self.begin_div('textbox', 1, item.x0, item.y1, item.width, item.height,
                                       item.get_writing_mode())
                        for child in item:
                            render(child)
                        self.end_div('textbox')
                    elif isinstance(item, LTChar):
                        self.put_text(item.get_text(), item.fontname, item.size)
                    elif isinstance(item, LTText):
                        self.write_text(item.get_text())
            return
        render(ltpage)
        self._yoffset += self.pagemargin
        return

    def close(self):
        self.write_footer()
        return


##  XMLConverter
##
class XMLConverter(PDFConverter):

    def __init__(self, rsrcmgr, outfp, codec='utf-8', pageno=1,
                 laparams=None, imagewriter=None):
        PDFConverter.__init__(self, rsrcmgr, outfp, codec=codec, pageno=pageno, laparams=laparams)
        self.imagewriter = imagewriter
        self.write_header()
        return

    def write_header(self):
        self.outfp.write('<?xml version="1.0" encoding="%s" ?>\n' % self.codec)
        self.outfp.write('<pages>\n')
        return

    def write_footer(self):
        self.outfp.write('</pages>\n')
        return

    def write_text(self, text):
        self.outfp.write(enc(text, self.codec))
        return

    def receive_layout(self, ltpage):
        def show_group(item):
            if isinstance(item, LTTextBox):
                self.outfp.write('<textbox id="%d" bbox="%s" />\n' %
                                 (item.index, bbox2str(item.bbox)))
            elif isinstance(item, LTTextGroup):
                self.outfp.write('<textgroup bbox="%s">\n' % bbox2str(item.bbox))
                for child in item:
                    show_group(child)
                self.outfp.write('</textgroup>\n')
            return

        def render(item):
            if isinstance(item, LTPage):
                self.outfp.write('<page id="%s" bbox="%s" rotate="%d">\n' %
                                 (item.pageid, bbox2str(item.bbox), item.rotate))
                for child in item:
                    render(child)
                if item.groups is not None:
                    self.outfp.write('<layout>\n')
                    for group in item.groups:
                        show_group(group)
                    self.outfp.write('</layout>\n')
                self.outfp.write('</page>\n')
            elif isinstance(item, LTLine):
                self.outfp.write('<line linewidth="%d" bbox="%s" />\n' %
                                 (item.linewidth, bbox2str(item.bbox)))
            elif isinstance(item, LTRect):
                self.outfp.write('<rect linewidth="%d" bbox="%s" />\n' %
                                 (item.linewidth, bbox2str(item.bbox)))
            elif isinstance(item, LTCurve):
                self.outfp.write('<curve linewidth="%d" bbox="%s" pts="%s"/>\n' %
                                 (item.linewidth, bbox2str(item.bbox), item.get_pts()))
            elif isinstance(item, LTFigure):
                self.outfp.write('<figure name="%s" bbox="%s">\n' %
                                 (item.name, bbox2str(item.bbox)))
                for child in item:
                    render(child)
                self.outfp.write('</figure>\n')
            elif isinstance(item, LTTextLine):
                self.outfp.write('<textline bbox="%s">\n' % bbox2str(item.bbox))
                for child in item:
                    render(child)
                self.outfp.write('</textline>\n')
            elif isinstance(item, LTTextBox):
                wmode = ''
                if isinstance(item, LTTextBoxVertical):
                    wmode = ' wmode="vertical"'
                self.outfp.write('<textbox id="%d" bbox="%s"%s>\n' %
                                 (item.index, bbox2str(item.bbox), wmode))
                for child in item:
                    render(child)
                self.outfp.write('</textbox>\n')
            elif isinstance(item, LTChar):
                self.outfp.write('<text font="%s" bbox="%s" size="%.3f">' %
                                 (enc(item.fontname), bbox2str(item.bbox), item.size))
                self.write_text(item.get_text())
                self.outfp.write('</text>\n')
            elif isinstance(item, LTText):
                self.outfp.write('<text>%s</text>\n' % item.get_text())
            elif isinstance(item, LTImage):
                if self.imagewriter is not None:
                    name = self.imagewriter.export_image(item)
                    self.outfp.write('<image src="%s" width="%d" height="%d" />\n' %
                                     (enc(name), item.width, item.height))
                else:
                    self.outfp.write('<image width="%d" height="%d" />\n' %
                                     (item.width, item.height))
            else:
                assert 0, item
            return
        render(ltpage)
        return

    def close(self):
        self.write_footer()
        return

########NEW FILE########
__FILENAME__ = encodingdb
#!/usr/bin/env python

import re
from psparser import PSLiteral
from glyphlist import glyphname2unicode
from latin_enc import ENCODING


STRIP_NAME = re.compile(r'[0-9]+')


##  name2unicode
##
def name2unicode(name):
    """Converts Adobe glyph names to Unicode numbers."""
    if name in glyphname2unicode:
        return glyphname2unicode[name]
    m = STRIP_NAME.search(name)
    if not m:
        raise KeyError(name)
    return unichr(int(m.group(0)))


##  EncodingDB
##
class EncodingDB(object):

    std2unicode = {}
    mac2unicode = {}
    win2unicode = {}
    pdf2unicode = {}
    for (name, std, mac, win, pdf) in ENCODING:
        c = name2unicode(name)
        if std:
            std2unicode[std] = c
        if mac:
            mac2unicode[mac] = c
        if win:
            win2unicode[win] = c
        if pdf:
            pdf2unicode[pdf] = c

    encodings = {
        'StandardEncoding': std2unicode,
        'MacRomanEncoding': mac2unicode,
        'WinAnsiEncoding': win2unicode,
        'PDFDocEncoding': pdf2unicode,
    }

    @classmethod
    def get_encoding(klass, name, diff=None):
        cid2unicode = klass.encodings.get(name, klass.std2unicode)
        if diff:
            cid2unicode = cid2unicode.copy()
            cid = 0
            for x in diff:
                if isinstance(x, int):
                    cid = x
                elif isinstance(x, PSLiteral):
                    try:
                        cid2unicode[cid] = name2unicode(x.name)
                    except KeyError:
                        pass
                    cid += 1
        return cid2unicode

########NEW FILE########
__FILENAME__ = fontmetrics
#!/usr/bin/env python

""" Font metrics for the Adobe core 14 fonts.

Font metrics are used to compute the boundary of each character
written with a proportional font.

The following data were extracted from the AFM files:

  http://www.ctan.org/tex-archive/fonts/adobe/afm/

"""

###  BEGIN Verbatim copy of the license part

#
# Adobe Core 35 AFM Files with 314 Glyph Entries - ReadMe
#
# This file and the 35 PostScript(R) AFM files it accompanies may be
# used, copied, and distributed for any purpose and without charge,
# with or without modification, provided that all copyright notices
# are retained; that the AFM files are not distributed without this
# file; that all modifications to this file or any of the AFM files
# are prominently noted in the modified file(s); and that this
# paragraph is not modified. Adobe Systems has no responsibility or
# obligation to support the use of the AFM files.
#

###  END Verbatim copy of the license part

FONT_METRICS = {
 'Courier': ({'FontName': 'Courier', 'Descent': -194.0, 'FontBBox': (-6.0, -249.0, 639.0, 803.0), 'FontWeight': 'Medium', 'CapHeight': 572.0, 'FontFamily': 'Courier', 'Flags': 64, 'XHeight': 434.0, 'ItalicAngle': 0.0, 'Ascent': 627.0}, {u' ': 600, u'!': 600, u'"': 600, u'#': 600, u'$': 600, u'%': 600, u'&': 600, u"'": 600, u'(': 600, u')': 600, u'*': 600, u'+': 600, u',': 600, u'-': 600, u'.': 600, u'/': 600, u'0': 600, u'1': 600, u'2': 600, u'3': 600, u'4': 600, u'5': 600, u'6': 600, u'7': 600, u'8': 600, u'9': 600, u':': 600, u';': 600, u'<': 600, u'=': 600, u'>': 600, u'?': 600, u'@': 600, u'A': 600, u'B': 600, u'C': 600, u'D': 600, u'E': 600, u'F': 600, u'G': 600, u'H': 600, u'I': 600, u'J': 600, u'K': 600, u'L': 600, u'M': 600, u'N': 600, u'O': 600, u'P': 600, u'Q': 600, u'R': 600, u'S': 600, u'T': 600, u'U': 600, u'V': 600, u'W': 600, u'X': 600, u'Y': 600, u'Z': 600, u'[': 600, u'\\': 600, u']': 600, u'^': 600, u'_': 600, u'`': 600, u'a': 600, u'b': 600, u'c': 600, u'd': 600, u'e': 600, u'f': 600, u'g': 600, u'h': 600, u'i': 600, u'j': 600, u'k': 600, u'l': 600, u'm': 600, u'n': 600, u'o': 600, u'p': 600, u'q': 600, u'r': 600, u's': 600, u't': 600, u'u': 600, u'v': 600, u'w': 600, u'x': 600, u'y': 600, u'z': 600, u'{': 600, u'|': 600, u'}': 600, u'~': 600, u'\xa1': 600, u'\xa2': 600, u'\xa3': 600, u'\xa4': 600, u'\xa5': 600, u'\xa6': 600, u'\xa7': 600, u'\xa8': 600, u'\xa9': 600, u'\xaa': 600, u'\xab': 600, u'\xac': 600, u'\xae': 600, u'\xaf': 600, u'\xb0': 600, u'\xb1': 600, u'\xb2': 600, u'\xb3': 600, u'\xb4': 600, u'\xb5': 600, u'\xb6': 600, u'\xb7': 600, u'\xb8': 600, u'\xb9': 600, u'\xba': 600, u'\xbb': 600, u'\xbc': 600, u'\xbd': 600, u'\xbe': 600, u'\xbf': 600, u'\xc0': 600, u'\xc1': 600, u'\xc2': 600, u'\xc3': 600, u'\xc4': 600, u'\xc5': 600, u'\xc6': 600, u'\xc7': 600, u'\xc8': 600, u'\xc9': 600, u'\xca': 600, u'\xcb': 600, u'\xcc': 600, u'\xcd': 600, u'\xce': 600, u'\xcf': 600, u'\xd0': 600, u'\xd1': 600, u'\xd2': 600, u'\xd3': 600, u'\xd4': 600, u'\xd5': 600, u'\xd6': 600, u'\xd7': 600, u'\xd8': 600, u'\xd9': 600, u'\xda': 600, u'\xdb': 600, u'\xdc': 600, u'\xdd': 600, u'\xde': 600, u'\xdf': 600, u'\xe0': 600, u'\xe1': 600, u'\xe2': 600, u'\xe3': 600, u'\xe4': 600, u'\xe5': 600, u'\xe6': 600, u'\xe7': 600, u'\xe8': 600, u'\xe9': 600, u'\xea': 600, u'\xeb': 600, u'\xec': 600, u'\xed': 600, u'\xee': 600, u'\xef': 600, u'\xf0': 600, u'\xf1': 600, u'\xf2': 600, u'\xf3': 600, u'\xf4': 600, u'\xf5': 600, u'\xf6': 600, u'\xf7': 600, u'\xf8': 600, u'\xf9': 600, u'\xfa': 600, u'\xfb': 600, u'\xfc': 600, u'\xfd': 600, u'\xfe': 600, u'\xff': 600, u'\u0100': 600, u'\u0101': 600, u'\u0102': 600, u'\u0103': 600, u'\u0104': 600, u'\u0105': 600, u'\u0106': 600, u'\u0107': 600, u'\u010c': 600, u'\u010d': 600, u'\u010e': 600, u'\u010f': 600, u'\u0110': 600, u'\u0111': 600, u'\u0112': 600, u'\u0113': 600, u'\u0116': 600, u'\u0117': 600, u'\u0118': 600, u'\u0119': 600, u'\u011a': 600, u'\u011b': 600, u'\u011e': 600, u'\u011f': 600, u'\u0122': 600, u'\u0123': 600, u'\u012a': 600, u'\u012b': 600, u'\u012e': 600, u'\u012f': 600, u'\u0130': 600, u'\u0131': 600, u'\u0136': 600, u'\u0137': 600, u'\u0139': 600, u'\u013a': 600, u'\u013b': 600, u'\u013c': 600, u'\u013d': 600, u'\u013e': 600, u'\u0141': 600, u'\u0142': 600, u'\u0143': 600, u'\u0144': 600, u'\u0145': 600, u'\u0146': 600, u'\u0147': 600, u'\u0148': 600, u'\u014c': 600, u'\u014d': 600, u'\u0150': 600, u'\u0151': 600, u'\u0152': 600, u'\u0153': 600, u'\u0154': 600, u'\u0155': 600, u'\u0156': 600, u'\u0157': 600, u'\u0158': 600, u'\u0159': 600, u'\u015a': 600, u'\u015b': 600, u'\u015e': 600, u'\u015f': 600, u'\u0160': 600, u'\u0161': 600, u'\u0162': 600, u'\u0163': 600, u'\u0164': 600, u'\u0165': 600, u'\u016a': 600, u'\u016b': 600, u'\u016e': 600, u'\u016f': 600, u'\u0170': 600, u'\u0171': 600, u'\u0172': 600, u'\u0173': 600, u'\u0178': 600, u'\u0179': 600, u'\u017a': 600, u'\u017b': 600, u'\u017c': 600, u'\u017d': 600, u'\u017e': 600, u'\u0192': 600, u'\u0218': 600, u'\u0219': 600, u'\u02c6': 600, u'\u02c7': 600, u'\u02d8': 600, u'\u02d9': 600, u'\u02da': 600, u'\u02db': 600, u'\u02dc': 600, u'\u02dd': 600, u'\u2013': 600, u'\u2014': 600, u'\u2018': 600, u'\u2019': 600, u'\u201a': 600, u'\u201c': 600, u'\u201d': 600, u'\u201e': 600, u'\u2020': 600, u'\u2021': 600, u'\u2022': 600, u'\u2026': 600, u'\u2030': 600, u'\u2039': 600, u'\u203a': 600, u'\u2044': 600, u'\u2122': 600, u'\u2202': 600, u'\u2206': 600, u'\u2211': 600, u'\u2212': 600, u'\u221a': 600, u'\u2260': 600, u'\u2264': 600, u'\u2265': 600, u'\u25ca': 600, u'\uf6c3': 600, u'\ufb01': 600, u'\ufb02': 600}),
 'Courier-Bold': ({'FontName': 'Courier-Bold', 'Descent': -194.0, 'FontBBox': (-88.0, -249.0, 697.0, 811.0), 'FontWeight': 'Bold', 'CapHeight': 572.0, 'FontFamily': 'Courier', 'Flags': 64, 'XHeight': 434.0, 'ItalicAngle': 0.0, 'Ascent': 627.0}, {u' ': 600, u'!': 600, u'"': 600, u'#': 600, u'$': 600, u'%': 600, u'&': 600, u"'": 600, u'(': 600, u')': 600, u'*': 600, u'+': 600, u',': 600, u'-': 600, u'.': 600, u'/': 600, u'0': 600, u'1': 600, u'2': 600, u'3': 600, u'4': 600, u'5': 600, u'6': 600, u'7': 600, u'8': 600, u'9': 600, u':': 600, u';': 600, u'<': 600, u'=': 600, u'>': 600, u'?': 600, u'@': 600, u'A': 600, u'B': 600, u'C': 600, u'D': 600, u'E': 600, u'F': 600, u'G': 600, u'H': 600, u'I': 600, u'J': 600, u'K': 600, u'L': 600, u'M': 600, u'N': 600, u'O': 600, u'P': 600, u'Q': 600, u'R': 600, u'S': 600, u'T': 600, u'U': 600, u'V': 600, u'W': 600, u'X': 600, u'Y': 600, u'Z': 600, u'[': 600, u'\\': 600, u']': 600, u'^': 600, u'_': 600, u'`': 600, u'a': 600, u'b': 600, u'c': 600, u'd': 600, u'e': 600, u'f': 600, u'g': 600, u'h': 600, u'i': 600, u'j': 600, u'k': 600, u'l': 600, u'm': 600, u'n': 600, u'o': 600, u'p': 600, u'q': 600, u'r': 600, u's': 600, u't': 600, u'u': 600, u'v': 600, u'w': 600, u'x': 600, u'y': 600, u'z': 600, u'{': 600, u'|': 600, u'}': 600, u'~': 600, u'\xa1': 600, u'\xa2': 600, u'\xa3': 600, u'\xa4': 600, u'\xa5': 600, u'\xa6': 600, u'\xa7': 600, u'\xa8': 600, u'\xa9': 600, u'\xaa': 600, u'\xab': 600, u'\xac': 600, u'\xae': 600, u'\xaf': 600, u'\xb0': 600, u'\xb1': 600, u'\xb2': 600, u'\xb3': 600, u'\xb4': 600, u'\xb5': 600, u'\xb6': 600, u'\xb7': 600, u'\xb8': 600, u'\xb9': 600, u'\xba': 600, u'\xbb': 600, u'\xbc': 600, u'\xbd': 600, u'\xbe': 600, u'\xbf': 600, u'\xc0': 600, u'\xc1': 600, u'\xc2': 600, u'\xc3': 600, u'\xc4': 600, u'\xc5': 600, u'\xc6': 600, u'\xc7': 600, u'\xc8': 600, u'\xc9': 600, u'\xca': 600, u'\xcb': 600, u'\xcc': 600, u'\xcd': 600, u'\xce': 600, u'\xcf': 600, u'\xd0': 600, u'\xd1': 600, u'\xd2': 600, u'\xd3': 600, u'\xd4': 600, u'\xd5': 600, u'\xd6': 600, u'\xd7': 600, u'\xd8': 600, u'\xd9': 600, u'\xda': 600, u'\xdb': 600, u'\xdc': 600, u'\xdd': 600, u'\xde': 600, u'\xdf': 600, u'\xe0': 600, u'\xe1': 600, u'\xe2': 600, u'\xe3': 600, u'\xe4': 600, u'\xe5': 600, u'\xe6': 600, u'\xe7': 600, u'\xe8': 600, u'\xe9': 600, u'\xea': 600, u'\xeb': 600, u'\xec': 600, u'\xed': 600, u'\xee': 600, u'\xef': 600, u'\xf0': 600, u'\xf1': 600, u'\xf2': 600, u'\xf3': 600, u'\xf4': 600, u'\xf5': 600, u'\xf6': 600, u'\xf7': 600, u'\xf8': 600, u'\xf9': 600, u'\xfa': 600, u'\xfb': 600, u'\xfc': 600, u'\xfd': 600, u'\xfe': 600, u'\xff': 600, u'\u0100': 600, u'\u0101': 600, u'\u0102': 600, u'\u0103': 600, u'\u0104': 600, u'\u0105': 600, u'\u0106': 600, u'\u0107': 600, u'\u010c': 600, u'\u010d': 600, u'\u010e': 600, u'\u010f': 600, u'\u0110': 600, u'\u0111': 600, u'\u0112': 600, u'\u0113': 600, u'\u0116': 600, u'\u0117': 600, u'\u0118': 600, u'\u0119': 600, u'\u011a': 600, u'\u011b': 600, u'\u011e': 600, u'\u011f': 600, u'\u0122': 600, u'\u0123': 600, u'\u012a': 600, u'\u012b': 600, u'\u012e': 600, u'\u012f': 600, u'\u0130': 600, u'\u0131': 600, u'\u0136': 600, u'\u0137': 600, u'\u0139': 600, u'\u013a': 600, u'\u013b': 600, u'\u013c': 600, u'\u013d': 600, u'\u013e': 600, u'\u0141': 600, u'\u0142': 600, u'\u0143': 600, u'\u0144': 600, u'\u0145': 600, u'\u0146': 600, u'\u0147': 600, u'\u0148': 600, u'\u014c': 600, u'\u014d': 600, u'\u0150': 600, u'\u0151': 600, u'\u0152': 600, u'\u0153': 600, u'\u0154': 600, u'\u0155': 600, u'\u0156': 600, u'\u0157': 600, u'\u0158': 600, u'\u0159': 600, u'\u015a': 600, u'\u015b': 600, u'\u015e': 600, u'\u015f': 600, u'\u0160': 600, u'\u0161': 600, u'\u0162': 600, u'\u0163': 600, u'\u0164': 600, u'\u0165': 600, u'\u016a': 600, u'\u016b': 600, u'\u016e': 600, u'\u016f': 600, u'\u0170': 600, u'\u0171': 600, u'\u0172': 600, u'\u0173': 600, u'\u0178': 600, u'\u0179': 600, u'\u017a': 600, u'\u017b': 600, u'\u017c': 600, u'\u017d': 600, u'\u017e': 600, u'\u0192': 600, u'\u0218': 600, u'\u0219': 600, u'\u02c6': 600, u'\u02c7': 600, u'\u02d8': 600, u'\u02d9': 600, u'\u02da': 600, u'\u02db': 600, u'\u02dc': 600, u'\u02dd': 600, u'\u2013': 600, u'\u2014': 600, u'\u2018': 600, u'\u2019': 600, u'\u201a': 600, u'\u201c': 600, u'\u201d': 600, u'\u201e': 600, u'\u2020': 600, u'\u2021': 600, u'\u2022': 600, u'\u2026': 600, u'\u2030': 600, u'\u2039': 600, u'\u203a': 600, u'\u2044': 600, u'\u2122': 600, u'\u2202': 600, u'\u2206': 600, u'\u2211': 600, u'\u2212': 600, u'\u221a': 600, u'\u2260': 600, u'\u2264': 600, u'\u2265': 600, u'\u25ca': 600, u'\uf6c3': 600, u'\ufb01': 600, u'\ufb02': 600}),
 'Courier-BoldOblique': ({'FontName': 'Courier-BoldOblique', 'Descent': -194.0, 'FontBBox': (-49.0, -249.0, 758.0, 811.0), 'FontWeight': 'Bold', 'CapHeight': 572.0, 'FontFamily': 'Courier', 'Flags': 64, 'XHeight': 434.0, 'ItalicAngle': -11.0, 'Ascent': 627.0}, {u' ': 600, u'!': 600, u'"': 600, u'#': 600, u'$': 600, u'%': 600, u'&': 600, u"'": 600, u'(': 600, u')': 600, u'*': 600, u'+': 600, u',': 600, u'-': 600, u'.': 600, u'/': 600, u'0': 600, u'1': 600, u'2': 600, u'3': 600, u'4': 600, u'5': 600, u'6': 600, u'7': 600, u'8': 600, u'9': 600, u':': 600, u';': 600, u'<': 600, u'=': 600, u'>': 600, u'?': 600, u'@': 600, u'A': 600, u'B': 600, u'C': 600, u'D': 600, u'E': 600, u'F': 600, u'G': 600, u'H': 600, u'I': 600, u'J': 600, u'K': 600, u'L': 600, u'M': 600, u'N': 600, u'O': 600, u'P': 600, u'Q': 600, u'R': 600, u'S': 600, u'T': 600, u'U': 600, u'V': 600, u'W': 600, u'X': 600, u'Y': 600, u'Z': 600, u'[': 600, u'\\': 600, u']': 600, u'^': 600, u'_': 600, u'`': 600, u'a': 600, u'b': 600, u'c': 600, u'd': 600, u'e': 600, u'f': 600, u'g': 600, u'h': 600, u'i': 600, u'j': 600, u'k': 600, u'l': 600, u'm': 600, u'n': 600, u'o': 600, u'p': 600, u'q': 600, u'r': 600, u's': 600, u't': 600, u'u': 600, u'v': 600, u'w': 600, u'x': 600, u'y': 600, u'z': 600, u'{': 600, u'|': 600, u'}': 600, u'~': 600, u'\xa1': 600, u'\xa2': 600, u'\xa3': 600, u'\xa4': 600, u'\xa5': 600, u'\xa6': 600, u'\xa7': 600, u'\xa8': 600, u'\xa9': 600, u'\xaa': 600, u'\xab': 600, u'\xac': 600, u'\xae': 600, u'\xaf': 600, u'\xb0': 600, u'\xb1': 600, u'\xb2': 600, u'\xb3': 600, u'\xb4': 600, u'\xb5': 600, u'\xb6': 600, u'\xb7': 600, u'\xb8': 600, u'\xb9': 600, u'\xba': 600, u'\xbb': 600, u'\xbc': 600, u'\xbd': 600, u'\xbe': 600, u'\xbf': 600, u'\xc0': 600, u'\xc1': 600, u'\xc2': 600, u'\xc3': 600, u'\xc4': 600, u'\xc5': 600, u'\xc6': 600, u'\xc7': 600, u'\xc8': 600, u'\xc9': 600, u'\xca': 600, u'\xcb': 600, u'\xcc': 600, u'\xcd': 600, u'\xce': 600, u'\xcf': 600, u'\xd0': 600, u'\xd1': 600, u'\xd2': 600, u'\xd3': 600, u'\xd4': 600, u'\xd5': 600, u'\xd6': 600, u'\xd7': 600, u'\xd8': 600, u'\xd9': 600, u'\xda': 600, u'\xdb': 600, u'\xdc': 600, u'\xdd': 600, u'\xde': 600, u'\xdf': 600, u'\xe0': 600, u'\xe1': 600, u'\xe2': 600, u'\xe3': 600, u'\xe4': 600, u'\xe5': 600, u'\xe6': 600, u'\xe7': 600, u'\xe8': 600, u'\xe9': 600, u'\xea': 600, u'\xeb': 600, u'\xec': 600, u'\xed': 600, u'\xee': 600, u'\xef': 600, u'\xf0': 600, u'\xf1': 600, u'\xf2': 600, u'\xf3': 600, u'\xf4': 600, u'\xf5': 600, u'\xf6': 600, u'\xf7': 600, u'\xf8': 600, u'\xf9': 600, u'\xfa': 600, u'\xfb': 600, u'\xfc': 600, u'\xfd': 600, u'\xfe': 600, u'\xff': 600, u'\u0100': 600, u'\u0101': 600, u'\u0102': 600, u'\u0103': 600, u'\u0104': 600, u'\u0105': 600, u'\u0106': 600, u'\u0107': 600, u'\u010c': 600, u'\u010d': 600, u'\u010e': 600, u'\u010f': 600, u'\u0110': 600, u'\u0111': 600, u'\u0112': 600, u'\u0113': 600, u'\u0116': 600, u'\u0117': 600, u'\u0118': 600, u'\u0119': 600, u'\u011a': 600, u'\u011b': 600, u'\u011e': 600, u'\u011f': 600, u'\u0122': 600, u'\u0123': 600, u'\u012a': 600, u'\u012b': 600, u'\u012e': 600, u'\u012f': 600, u'\u0130': 600, u'\u0131': 600, u'\u0136': 600, u'\u0137': 600, u'\u0139': 600, u'\u013a': 600, u'\u013b': 600, u'\u013c': 600, u'\u013d': 600, u'\u013e': 600, u'\u0141': 600, u'\u0142': 600, u'\u0143': 600, u'\u0144': 600, u'\u0145': 600, u'\u0146': 600, u'\u0147': 600, u'\u0148': 600, u'\u014c': 600, u'\u014d': 600, u'\u0150': 600, u'\u0151': 600, u'\u0152': 600, u'\u0153': 600, u'\u0154': 600, u'\u0155': 600, u'\u0156': 600, u'\u0157': 600, u'\u0158': 600, u'\u0159': 600, u'\u015a': 600, u'\u015b': 600, u'\u015e': 600, u'\u015f': 600, u'\u0160': 600, u'\u0161': 600, u'\u0162': 600, u'\u0163': 600, u'\u0164': 600, u'\u0165': 600, u'\u016a': 600, u'\u016b': 600, u'\u016e': 600, u'\u016f': 600, u'\u0170': 600, u'\u0171': 600, u'\u0172': 600, u'\u0173': 600, u'\u0178': 600, u'\u0179': 600, u'\u017a': 600, u'\u017b': 600, u'\u017c': 600, u'\u017d': 600, u'\u017e': 600, u'\u0192': 600, u'\u0218': 600, u'\u0219': 600, u'\u02c6': 600, u'\u02c7': 600, u'\u02d8': 600, u'\u02d9': 600, u'\u02da': 600, u'\u02db': 600, u'\u02dc': 600, u'\u02dd': 600, u'\u2013': 600, u'\u2014': 600, u'\u2018': 600, u'\u2019': 600, u'\u201a': 600, u'\u201c': 600, u'\u201d': 600, u'\u201e': 600, u'\u2020': 600, u'\u2021': 600, u'\u2022': 600, u'\u2026': 600, u'\u2030': 600, u'\u2039': 600, u'\u203a': 600, u'\u2044': 600, u'\u2122': 600, u'\u2202': 600, u'\u2206': 600, u'\u2211': 600, u'\u2212': 600, u'\u221a': 600, u'\u2260': 600, u'\u2264': 600, u'\u2265': 600, u'\u25ca': 600, u'\uf6c3': 600, u'\ufb01': 600, u'\ufb02': 600}),
 'Courier-Oblique': ({'FontName': 'Courier-Oblique', 'Descent': -194.0, 'FontBBox': (-49.0, -249.0, 749.0, 803.0), 'FontWeight': 'Medium', 'CapHeight': 572.0, 'FontFamily': 'Courier', 'Flags': 64, 'XHeight': 434.0, 'ItalicAngle': -11.0, 'Ascent': 627.0}, {u' ': 600, u'!': 600, u'"': 600, u'#': 600, u'$': 600, u'%': 600, u'&': 600, u"'": 600, u'(': 600, u')': 600, u'*': 600, u'+': 600, u',': 600, u'-': 600, u'.': 600, u'/': 600, u'0': 600, u'1': 600, u'2': 600, u'3': 600, u'4': 600, u'5': 600, u'6': 600, u'7': 600, u'8': 600, u'9': 600, u':': 600, u';': 600, u'<': 600, u'=': 600, u'>': 600, u'?': 600, u'@': 600, u'A': 600, u'B': 600, u'C': 600, u'D': 600, u'E': 600, u'F': 600, u'G': 600, u'H': 600, u'I': 600, u'J': 600, u'K': 600, u'L': 600, u'M': 600, u'N': 600, u'O': 600, u'P': 600, u'Q': 600, u'R': 600, u'S': 600, u'T': 600, u'U': 600, u'V': 600, u'W': 600, u'X': 600, u'Y': 600, u'Z': 600, u'[': 600, u'\\': 600, u']': 600, u'^': 600, u'_': 600, u'`': 600, u'a': 600, u'b': 600, u'c': 600, u'd': 600, u'e': 600, u'f': 600, u'g': 600, u'h': 600, u'i': 600, u'j': 600, u'k': 600, u'l': 600, u'm': 600, u'n': 600, u'o': 600, u'p': 600, u'q': 600, u'r': 600, u's': 600, u't': 600, u'u': 600, u'v': 600, u'w': 600, u'x': 600, u'y': 600, u'z': 600, u'{': 600, u'|': 600, u'}': 600, u'~': 600, u'\xa1': 600, u'\xa2': 600, u'\xa3': 600, u'\xa4': 600, u'\xa5': 600, u'\xa6': 600, u'\xa7': 600, u'\xa8': 600, u'\xa9': 600, u'\xaa': 600, u'\xab': 600, u'\xac': 600, u'\xae': 600, u'\xaf': 600, u'\xb0': 600, u'\xb1': 600, u'\xb2': 600, u'\xb3': 600, u'\xb4': 600, u'\xb5': 600, u'\xb6': 600, u'\xb7': 600, u'\xb8': 600, u'\xb9': 600, u'\xba': 600, u'\xbb': 600, u'\xbc': 600, u'\xbd': 600, u'\xbe': 600, u'\xbf': 600, u'\xc0': 600, u'\xc1': 600, u'\xc2': 600, u'\xc3': 600, u'\xc4': 600, u'\xc5': 600, u'\xc6': 600, u'\xc7': 600, u'\xc8': 600, u'\xc9': 600, u'\xca': 600, u'\xcb': 600, u'\xcc': 600, u'\xcd': 600, u'\xce': 600, u'\xcf': 600, u'\xd0': 600, u'\xd1': 600, u'\xd2': 600, u'\xd3': 600, u'\xd4': 600, u'\xd5': 600, u'\xd6': 600, u'\xd7': 600, u'\xd8': 600, u'\xd9': 600, u'\xda': 600, u'\xdb': 600, u'\xdc': 600, u'\xdd': 600, u'\xde': 600, u'\xdf': 600, u'\xe0': 600, u'\xe1': 600, u'\xe2': 600, u'\xe3': 600, u'\xe4': 600, u'\xe5': 600, u'\xe6': 600, u'\xe7': 600, u'\xe8': 600, u'\xe9': 600, u'\xea': 600, u'\xeb': 600, u'\xec': 600, u'\xed': 600, u'\xee': 600, u'\xef': 600, u'\xf0': 600, u'\xf1': 600, u'\xf2': 600, u'\xf3': 600, u'\xf4': 600, u'\xf5': 600, u'\xf6': 600, u'\xf7': 600, u'\xf8': 600, u'\xf9': 600, u'\xfa': 600, u'\xfb': 600, u'\xfc': 600, u'\xfd': 600, u'\xfe': 600, u'\xff': 600, u'\u0100': 600, u'\u0101': 600, u'\u0102': 600, u'\u0103': 600, u'\u0104': 600, u'\u0105': 600, u'\u0106': 600, u'\u0107': 600, u'\u010c': 600, u'\u010d': 600, u'\u010e': 600, u'\u010f': 600, u'\u0110': 600, u'\u0111': 600, u'\u0112': 600, u'\u0113': 600, u'\u0116': 600, u'\u0117': 600, u'\u0118': 600, u'\u0119': 600, u'\u011a': 600, u'\u011b': 600, u'\u011e': 600, u'\u011f': 600, u'\u0122': 600, u'\u0123': 600, u'\u012a': 600, u'\u012b': 600, u'\u012e': 600, u'\u012f': 600, u'\u0130': 600, u'\u0131': 600, u'\u0136': 600, u'\u0137': 600, u'\u0139': 600, u'\u013a': 600, u'\u013b': 600, u'\u013c': 600, u'\u013d': 600, u'\u013e': 600, u'\u0141': 600, u'\u0142': 600, u'\u0143': 600, u'\u0144': 600, u'\u0145': 600, u'\u0146': 600, u'\u0147': 600, u'\u0148': 600, u'\u014c': 600, u'\u014d': 600, u'\u0150': 600, u'\u0151': 600, u'\u0152': 600, u'\u0153': 600, u'\u0154': 600, u'\u0155': 600, u'\u0156': 600, u'\u0157': 600, u'\u0158': 600, u'\u0159': 600, u'\u015a': 600, u'\u015b': 600, u'\u015e': 600, u'\u015f': 600, u'\u0160': 600, u'\u0161': 600, u'\u0162': 600, u'\u0163': 600, u'\u0164': 600, u'\u0165': 600, u'\u016a': 600, u'\u016b': 600, u'\u016e': 600, u'\u016f': 600, u'\u0170': 600, u'\u0171': 600, u'\u0172': 600, u'\u0173': 600, u'\u0178': 600, u'\u0179': 600, u'\u017a': 600, u'\u017b': 600, u'\u017c': 600, u'\u017d': 600, u'\u017e': 600, u'\u0192': 600, u'\u0218': 600, u'\u0219': 600, u'\u02c6': 600, u'\u02c7': 600, u'\u02d8': 600, u'\u02d9': 600, u'\u02da': 600, u'\u02db': 600, u'\u02dc': 600, u'\u02dd': 600, u'\u2013': 600, u'\u2014': 600, u'\u2018': 600, u'\u2019': 600, u'\u201a': 600, u'\u201c': 600, u'\u201d': 600, u'\u201e': 600, u'\u2020': 600, u'\u2021': 600, u'\u2022': 600, u'\u2026': 600, u'\u2030': 600, u'\u2039': 600, u'\u203a': 600, u'\u2044': 600, u'\u2122': 600, u'\u2202': 600, u'\u2206': 600, u'\u2211': 600, u'\u2212': 600, u'\u221a': 600, u'\u2260': 600, u'\u2264': 600, u'\u2265': 600, u'\u25ca': 600, u'\uf6c3': 600, u'\ufb01': 600, u'\ufb02': 600}),
 'Helvetica': ({'FontName': 'Helvetica', 'Descent': -207.0, 'FontBBox': (-166.0, -225.0, 1000.0, 931.0), 'FontWeight': 'Medium', 'CapHeight': 718.0, 'FontFamily': 'Helvetica', 'Flags': 0, 'XHeight': 523.0, 'ItalicAngle': 0.0, 'Ascent': 718.0}, {u' ': 278, u'!': 278, u'"': 355, u'#': 556, u'$': 556, u'%': 889, u'&': 667, u"'": 191, u'(': 333, u')': 333, u'*': 389, u'+': 584, u',': 278, u'-': 333, u'.': 278, u'/': 278, u'0': 556, u'1': 556, u'2': 556, u'3': 556, u'4': 556, u'5': 556, u'6': 556, u'7': 556, u'8': 556, u'9': 556, u':': 278, u';': 278, u'<': 584, u'=': 584, u'>': 584, u'?': 556, u'@': 1015, u'A': 667, u'B': 667, u'C': 722, u'D': 722, u'E': 667, u'F': 611, u'G': 778, u'H': 722, u'I': 278, u'J': 500, u'K': 667, u'L': 556, u'M': 833, u'N': 722, u'O': 778, u'P': 667, u'Q': 778, u'R': 722, u'S': 667, u'T': 611, u'U': 722, u'V': 667, u'W': 944, u'X': 667, u'Y': 667, u'Z': 611, u'[': 278, u'\\': 278, u']': 278, u'^': 469, u'_': 556, u'`': 333, u'a': 556, u'b': 556, u'c': 500, u'd': 556, u'e': 556, u'f': 278, u'g': 556, u'h': 556, u'i': 222, u'j': 222, u'k': 500, u'l': 222, u'm': 833, u'n': 556, u'o': 556, u'p': 556, u'q': 556, u'r': 333, u's': 500, u't': 278, u'u': 556, u'v': 500, u'w': 722, u'x': 500, u'y': 500, u'z': 500, u'{': 334, u'|': 260, u'}': 334, u'~': 584, u'\xa1': 333, u'\xa2': 556, u'\xa3': 556, u'\xa4': 556, u'\xa5': 556, u'\xa6': 260, u'\xa7': 556, u'\xa8': 333, u'\xa9': 737, u'\xaa': 370, u'\xab': 556, u'\xac': 584, u'\xae': 737, u'\xaf': 333, u'\xb0': 400, u'\xb1': 584, u'\xb2': 333, u'\xb3': 333, u'\xb4': 333, u'\xb5': 556, u'\xb6': 537, u'\xb7': 278, u'\xb8': 333, u'\xb9': 333, u'\xba': 365, u'\xbb': 556, u'\xbc': 834, u'\xbd': 834, u'\xbe': 834, u'\xbf': 611, u'\xc0': 667, u'\xc1': 667, u'\xc2': 667, u'\xc3': 667, u'\xc4': 667, u'\xc5': 667, u'\xc6': 1000, u'\xc7': 722, u'\xc8': 667, u'\xc9': 667, u'\xca': 667, u'\xcb': 667, u'\xcc': 278, u'\xcd': 278, u'\xce': 278, u'\xcf': 278, u'\xd0': 722, u'\xd1': 722, u'\xd2': 778, u'\xd3': 778, u'\xd4': 778, u'\xd5': 778, u'\xd6': 778, u'\xd7': 584, u'\xd8': 778, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 667, u'\xde': 667, u'\xdf': 611, u'\xe0': 556, u'\xe1': 556, u'\xe2': 556, u'\xe3': 556, u'\xe4': 556, u'\xe5': 556, u'\xe6': 889, u'\xe7': 500, u'\xe8': 556, u'\xe9': 556, u'\xea': 556, u'\xeb': 556, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 556, u'\xf1': 556, u'\xf2': 556, u'\xf3': 556, u'\xf4': 556, u'\xf5': 556, u'\xf6': 556, u'\xf7': 584, u'\xf8': 611, u'\xf9': 556, u'\xfa': 556, u'\xfb': 556, u'\xfc': 556, u'\xfd': 500, u'\xfe': 556, u'\xff': 500, u'\u0100': 667, u'\u0101': 556, u'\u0102': 667, u'\u0103': 556, u'\u0104': 667, u'\u0105': 556, u'\u0106': 722, u'\u0107': 500, u'\u010c': 722, u'\u010d': 500, u'\u010e': 722, u'\u010f': 643, u'\u0110': 722, u'\u0111': 556, u'\u0112': 667, u'\u0113': 556, u'\u0116': 667, u'\u0117': 556, u'\u0118': 667, u'\u0119': 556, u'\u011a': 667, u'\u011b': 556, u'\u011e': 778, u'\u011f': 556, u'\u0122': 778, u'\u0123': 556, u'\u012a': 278, u'\u012b': 278, u'\u012e': 278, u'\u012f': 222, u'\u0130': 278, u'\u0131': 278, u'\u0136': 667, u'\u0137': 500, u'\u0139': 556, u'\u013a': 222, u'\u013b': 556, u'\u013c': 222, u'\u013d': 556, u'\u013e': 299, u'\u0141': 556, u'\u0142': 222, u'\u0143': 722, u'\u0144': 556, u'\u0145': 722, u'\u0146': 556, u'\u0147': 722, u'\u0148': 556, u'\u014c': 778, u'\u014d': 556, u'\u0150': 778, u'\u0151': 556, u'\u0152': 1000, u'\u0153': 944, u'\u0154': 722, u'\u0155': 333, u'\u0156': 722, u'\u0157': 333, u'\u0158': 722, u'\u0159': 333, u'\u015a': 667, u'\u015b': 500, u'\u015e': 667, u'\u015f': 500, u'\u0160': 667, u'\u0161': 500, u'\u0162': 611, u'\u0163': 278, u'\u0164': 611, u'\u0165': 317, u'\u016a': 722, u'\u016b': 556, u'\u016e': 722, u'\u016f': 556, u'\u0170': 722, u'\u0171': 556, u'\u0172': 722, u'\u0173': 556, u'\u0178': 667, u'\u0179': 611, u'\u017a': 500, u'\u017b': 611, u'\u017c': 500, u'\u017d': 611, u'\u017e': 500, u'\u0192': 556, u'\u0218': 667, u'\u0219': 500, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 556, u'\u2014': 1000, u'\u2018': 222, u'\u2019': 222, u'\u201a': 222, u'\u201c': 333, u'\u201d': 333, u'\u201e': 333, u'\u2020': 556, u'\u2021': 556, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 1000, u'\u2202': 476, u'\u2206': 612, u'\u2211': 600, u'\u2212': 584, u'\u221a': 453, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 471, u'\uf6c3': 250, u'\ufb01': 500, u'\ufb02': 500}),
 'Helvetica-Bold': ({'FontName': 'Helvetica-Bold', 'Descent': -207.0, 'FontBBox': (-170.0, -228.0, 1003.0, 962.0), 'FontWeight': 'Bold', 'CapHeight': 718.0, 'FontFamily': 'Helvetica', 'Flags': 0, 'XHeight': 532.0, 'ItalicAngle': 0.0, 'Ascent': 718.0}, {u' ': 278, u'!': 333, u'"': 474, u'#': 556, u'$': 556, u'%': 889, u'&': 722, u"'": 238, u'(': 333, u')': 333, u'*': 389, u'+': 584, u',': 278, u'-': 333, u'.': 278, u'/': 278, u'0': 556, u'1': 556, u'2': 556, u'3': 556, u'4': 556, u'5': 556, u'6': 556, u'7': 556, u'8': 556, u'9': 556, u':': 333, u';': 333, u'<': 584, u'=': 584, u'>': 584, u'?': 611, u'@': 975, u'A': 722, u'B': 722, u'C': 722, u'D': 722, u'E': 667, u'F': 611, u'G': 778, u'H': 722, u'I': 278, u'J': 556, u'K': 722, u'L': 611, u'M': 833, u'N': 722, u'O': 778, u'P': 667, u'Q': 778, u'R': 722, u'S': 667, u'T': 611, u'U': 722, u'V': 667, u'W': 944, u'X': 667, u'Y': 667, u'Z': 611, u'[': 333, u'\\': 278, u']': 333, u'^': 584, u'_': 556, u'`': 333, u'a': 556, u'b': 611, u'c': 556, u'd': 611, u'e': 556, u'f': 333, u'g': 611, u'h': 611, u'i': 278, u'j': 278, u'k': 556, u'l': 278, u'm': 889, u'n': 611, u'o': 611, u'p': 611, u'q': 611, u'r': 389, u's': 556, u't': 333, u'u': 611, u'v': 556, u'w': 778, u'x': 556, u'y': 556, u'z': 500, u'{': 389, u'|': 280, u'}': 389, u'~': 584, u'\xa1': 333, u'\xa2': 556, u'\xa3': 556, u'\xa4': 556, u'\xa5': 556, u'\xa6': 280, u'\xa7': 556, u'\xa8': 333, u'\xa9': 737, u'\xaa': 370, u'\xab': 556, u'\xac': 584, u'\xae': 737, u'\xaf': 333, u'\xb0': 400, u'\xb1': 584, u'\xb2': 333, u'\xb3': 333, u'\xb4': 333, u'\xb5': 611, u'\xb6': 556, u'\xb7': 278, u'\xb8': 333, u'\xb9': 333, u'\xba': 365, u'\xbb': 556, u'\xbc': 834, u'\xbd': 834, u'\xbe': 834, u'\xbf': 611, u'\xc0': 722, u'\xc1': 722, u'\xc2': 722, u'\xc3': 722, u'\xc4': 722, u'\xc5': 722, u'\xc6': 1000, u'\xc7': 722, u'\xc8': 667, u'\xc9': 667, u'\xca': 667, u'\xcb': 667, u'\xcc': 278, u'\xcd': 278, u'\xce': 278, u'\xcf': 278, u'\xd0': 722, u'\xd1': 722, u'\xd2': 778, u'\xd3': 778, u'\xd4': 778, u'\xd5': 778, u'\xd6': 778, u'\xd7': 584, u'\xd8': 778, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 667, u'\xde': 667, u'\xdf': 611, u'\xe0': 556, u'\xe1': 556, u'\xe2': 556, u'\xe3': 556, u'\xe4': 556, u'\xe5': 556, u'\xe6': 889, u'\xe7': 556, u'\xe8': 556, u'\xe9': 556, u'\xea': 556, u'\xeb': 556, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 611, u'\xf1': 611, u'\xf2': 611, u'\xf3': 611, u'\xf4': 611, u'\xf5': 611, u'\xf6': 611, u'\xf7': 584, u'\xf8': 611, u'\xf9': 611, u'\xfa': 611, u'\xfb': 611, u'\xfc': 611, u'\xfd': 556, u'\xfe': 611, u'\xff': 556, u'\u0100': 722, u'\u0101': 556, u'\u0102': 722, u'\u0103': 556, u'\u0104': 722, u'\u0105': 556, u'\u0106': 722, u'\u0107': 556, u'\u010c': 722, u'\u010d': 556, u'\u010e': 722, u'\u010f': 743, u'\u0110': 722, u'\u0111': 611, u'\u0112': 667, u'\u0113': 556, u'\u0116': 667, u'\u0117': 556, u'\u0118': 667, u'\u0119': 556, u'\u011a': 667, u'\u011b': 556, u'\u011e': 778, u'\u011f': 611, u'\u0122': 778, u'\u0123': 611, u'\u012a': 278, u'\u012b': 278, u'\u012e': 278, u'\u012f': 278, u'\u0130': 278, u'\u0131': 278, u'\u0136': 722, u'\u0137': 556, u'\u0139': 611, u'\u013a': 278, u'\u013b': 611, u'\u013c': 278, u'\u013d': 611, u'\u013e': 400, u'\u0141': 611, u'\u0142': 278, u'\u0143': 722, u'\u0144': 611, u'\u0145': 722, u'\u0146': 611, u'\u0147': 722, u'\u0148': 611, u'\u014c': 778, u'\u014d': 611, u'\u0150': 778, u'\u0151': 611, u'\u0152': 1000, u'\u0153': 944, u'\u0154': 722, u'\u0155': 389, u'\u0156': 722, u'\u0157': 389, u'\u0158': 722, u'\u0159': 389, u'\u015a': 667, u'\u015b': 556, u'\u015e': 667, u'\u015f': 556, u'\u0160': 667, u'\u0161': 556, u'\u0162': 611, u'\u0163': 333, u'\u0164': 611, u'\u0165': 389, u'\u016a': 722, u'\u016b': 611, u'\u016e': 722, u'\u016f': 611, u'\u0170': 722, u'\u0171': 611, u'\u0172': 722, u'\u0173': 611, u'\u0178': 667, u'\u0179': 611, u'\u017a': 500, u'\u017b': 611, u'\u017c': 500, u'\u017d': 611, u'\u017e': 500, u'\u0192': 556, u'\u0218': 667, u'\u0219': 556, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 556, u'\u2014': 1000, u'\u2018': 278, u'\u2019': 278, u'\u201a': 278, u'\u201c': 500, u'\u201d': 500, u'\u201e': 500, u'\u2020': 556, u'\u2021': 556, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 1000, u'\u2202': 494, u'\u2206': 612, u'\u2211': 600, u'\u2212': 584, u'\u221a': 549, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 494, u'\uf6c3': 250, u'\ufb01': 611, u'\ufb02': 611}),
 'Helvetica-BoldOblique': ({'FontName': 'Helvetica-BoldOblique', 'Descent': -207.0, 'FontBBox': (-175.0, -228.0, 1114.0, 962.0), 'FontWeight': 'Bold', 'CapHeight': 718.0, 'FontFamily': 'Helvetica', 'Flags': 0, 'XHeight': 532.0, 'ItalicAngle': -12.0, 'Ascent': 718.0}, {u' ': 278, u'!': 333, u'"': 474, u'#': 556, u'$': 556, u'%': 889, u'&': 722, u"'": 238, u'(': 333, u')': 333, u'*': 389, u'+': 584, u',': 278, u'-': 333, u'.': 278, u'/': 278, u'0': 556, u'1': 556, u'2': 556, u'3': 556, u'4': 556, u'5': 556, u'6': 556, u'7': 556, u'8': 556, u'9': 556, u':': 333, u';': 333, u'<': 584, u'=': 584, u'>': 584, u'?': 611, u'@': 975, u'A': 722, u'B': 722, u'C': 722, u'D': 722, u'E': 667, u'F': 611, u'G': 778, u'H': 722, u'I': 278, u'J': 556, u'K': 722, u'L': 611, u'M': 833, u'N': 722, u'O': 778, u'P': 667, u'Q': 778, u'R': 722, u'S': 667, u'T': 611, u'U': 722, u'V': 667, u'W': 944, u'X': 667, u'Y': 667, u'Z': 611, u'[': 333, u'\\': 278, u']': 333, u'^': 584, u'_': 556, u'`': 333, u'a': 556, u'b': 611, u'c': 556, u'd': 611, u'e': 556, u'f': 333, u'g': 611, u'h': 611, u'i': 278, u'j': 278, u'k': 556, u'l': 278, u'm': 889, u'n': 611, u'o': 611, u'p': 611, u'q': 611, u'r': 389, u's': 556, u't': 333, u'u': 611, u'v': 556, u'w': 778, u'x': 556, u'y': 556, u'z': 500, u'{': 389, u'|': 280, u'}': 389, u'~': 584, u'\xa1': 333, u'\xa2': 556, u'\xa3': 556, u'\xa4': 556, u'\xa5': 556, u'\xa6': 280, u'\xa7': 556, u'\xa8': 333, u'\xa9': 737, u'\xaa': 370, u'\xab': 556, u'\xac': 584, u'\xae': 737, u'\xaf': 333, u'\xb0': 400, u'\xb1': 584, u'\xb2': 333, u'\xb3': 333, u'\xb4': 333, u'\xb5': 611, u'\xb6': 556, u'\xb7': 278, u'\xb8': 333, u'\xb9': 333, u'\xba': 365, u'\xbb': 556, u'\xbc': 834, u'\xbd': 834, u'\xbe': 834, u'\xbf': 611, u'\xc0': 722, u'\xc1': 722, u'\xc2': 722, u'\xc3': 722, u'\xc4': 722, u'\xc5': 722, u'\xc6': 1000, u'\xc7': 722, u'\xc8': 667, u'\xc9': 667, u'\xca': 667, u'\xcb': 667, u'\xcc': 278, u'\xcd': 278, u'\xce': 278, u'\xcf': 278, u'\xd0': 722, u'\xd1': 722, u'\xd2': 778, u'\xd3': 778, u'\xd4': 778, u'\xd5': 778, u'\xd6': 778, u'\xd7': 584, u'\xd8': 778, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 667, u'\xde': 667, u'\xdf': 611, u'\xe0': 556, u'\xe1': 556, u'\xe2': 556, u'\xe3': 556, u'\xe4': 556, u'\xe5': 556, u'\xe6': 889, u'\xe7': 556, u'\xe8': 556, u'\xe9': 556, u'\xea': 556, u'\xeb': 556, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 611, u'\xf1': 611, u'\xf2': 611, u'\xf3': 611, u'\xf4': 611, u'\xf5': 611, u'\xf6': 611, u'\xf7': 584, u'\xf8': 611, u'\xf9': 611, u'\xfa': 611, u'\xfb': 611, u'\xfc': 611, u'\xfd': 556, u'\xfe': 611, u'\xff': 556, u'\u0100': 722, u'\u0101': 556, u'\u0102': 722, u'\u0103': 556, u'\u0104': 722, u'\u0105': 556, u'\u0106': 722, u'\u0107': 556, u'\u010c': 722, u'\u010d': 556, u'\u010e': 722, u'\u010f': 743, u'\u0110': 722, u'\u0111': 611, u'\u0112': 667, u'\u0113': 556, u'\u0116': 667, u'\u0117': 556, u'\u0118': 667, u'\u0119': 556, u'\u011a': 667, u'\u011b': 556, u'\u011e': 778, u'\u011f': 611, u'\u0122': 778, u'\u0123': 611, u'\u012a': 278, u'\u012b': 278, u'\u012e': 278, u'\u012f': 278, u'\u0130': 278, u'\u0131': 278, u'\u0136': 722, u'\u0137': 556, u'\u0139': 611, u'\u013a': 278, u'\u013b': 611, u'\u013c': 278, u'\u013d': 611, u'\u013e': 400, u'\u0141': 611, u'\u0142': 278, u'\u0143': 722, u'\u0144': 611, u'\u0145': 722, u'\u0146': 611, u'\u0147': 722, u'\u0148': 611, u'\u014c': 778, u'\u014d': 611, u'\u0150': 778, u'\u0151': 611, u'\u0152': 1000, u'\u0153': 944, u'\u0154': 722, u'\u0155': 389, u'\u0156': 722, u'\u0157': 389, u'\u0158': 722, u'\u0159': 389, u'\u015a': 667, u'\u015b': 556, u'\u015e': 667, u'\u015f': 556, u'\u0160': 667, u'\u0161': 556, u'\u0162': 611, u'\u0163': 333, u'\u0164': 611, u'\u0165': 389, u'\u016a': 722, u'\u016b': 611, u'\u016e': 722, u'\u016f': 611, u'\u0170': 722, u'\u0171': 611, u'\u0172': 722, u'\u0173': 611, u'\u0178': 667, u'\u0179': 611, u'\u017a': 500, u'\u017b': 611, u'\u017c': 500, u'\u017d': 611, u'\u017e': 500, u'\u0192': 556, u'\u0218': 667, u'\u0219': 556, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 556, u'\u2014': 1000, u'\u2018': 278, u'\u2019': 278, u'\u201a': 278, u'\u201c': 500, u'\u201d': 500, u'\u201e': 500, u'\u2020': 556, u'\u2021': 556, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 1000, u'\u2202': 494, u'\u2206': 612, u'\u2211': 600, u'\u2212': 584, u'\u221a': 549, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 494, u'\uf6c3': 250, u'\ufb01': 611, u'\ufb02': 611}),
 'Helvetica-Oblique': ({'FontName': 'Helvetica-Oblique', 'Descent': -207.0, 'FontBBox': (-171.0, -225.0, 1116.0, 931.0), 'FontWeight': 'Medium', 'CapHeight': 718.0, 'FontFamily': 'Helvetica', 'Flags': 0, 'XHeight': 523.0, 'ItalicAngle': -12.0, 'Ascent': 718.0}, {u' ': 278, u'!': 278, u'"': 355, u'#': 556, u'$': 556, u'%': 889, u'&': 667, u"'": 191, u'(': 333, u')': 333, u'*': 389, u'+': 584, u',': 278, u'-': 333, u'.': 278, u'/': 278, u'0': 556, u'1': 556, u'2': 556, u'3': 556, u'4': 556, u'5': 556, u'6': 556, u'7': 556, u'8': 556, u'9': 556, u':': 278, u';': 278, u'<': 584, u'=': 584, u'>': 584, u'?': 556, u'@': 1015, u'A': 667, u'B': 667, u'C': 722, u'D': 722, u'E': 667, u'F': 611, u'G': 778, u'H': 722, u'I': 278, u'J': 500, u'K': 667, u'L': 556, u'M': 833, u'N': 722, u'O': 778, u'P': 667, u'Q': 778, u'R': 722, u'S': 667, u'T': 611, u'U': 722, u'V': 667, u'W': 944, u'X': 667, u'Y': 667, u'Z': 611, u'[': 278, u'\\': 278, u']': 278, u'^': 469, u'_': 556, u'`': 333, u'a': 556, u'b': 556, u'c': 500, u'd': 556, u'e': 556, u'f': 278, u'g': 556, u'h': 556, u'i': 222, u'j': 222, u'k': 500, u'l': 222, u'm': 833, u'n': 556, u'o': 556, u'p': 556, u'q': 556, u'r': 333, u's': 500, u't': 278, u'u': 556, u'v': 500, u'w': 722, u'x': 500, u'y': 500, u'z': 500, u'{': 334, u'|': 260, u'}': 334, u'~': 584, u'\xa1': 333, u'\xa2': 556, u'\xa3': 556, u'\xa4': 556, u'\xa5': 556, u'\xa6': 260, u'\xa7': 556, u'\xa8': 333, u'\xa9': 737, u'\xaa': 370, u'\xab': 556, u'\xac': 584, u'\xae': 737, u'\xaf': 333, u'\xb0': 400, u'\xb1': 584, u'\xb2': 333, u'\xb3': 333, u'\xb4': 333, u'\xb5': 556, u'\xb6': 537, u'\xb7': 278, u'\xb8': 333, u'\xb9': 333, u'\xba': 365, u'\xbb': 556, u'\xbc': 834, u'\xbd': 834, u'\xbe': 834, u'\xbf': 611, u'\xc0': 667, u'\xc1': 667, u'\xc2': 667, u'\xc3': 667, u'\xc4': 667, u'\xc5': 667, u'\xc6': 1000, u'\xc7': 722, u'\xc8': 667, u'\xc9': 667, u'\xca': 667, u'\xcb': 667, u'\xcc': 278, u'\xcd': 278, u'\xce': 278, u'\xcf': 278, u'\xd0': 722, u'\xd1': 722, u'\xd2': 778, u'\xd3': 778, u'\xd4': 778, u'\xd5': 778, u'\xd6': 778, u'\xd7': 584, u'\xd8': 778, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 667, u'\xde': 667, u'\xdf': 611, u'\xe0': 556, u'\xe1': 556, u'\xe2': 556, u'\xe3': 556, u'\xe4': 556, u'\xe5': 556, u'\xe6': 889, u'\xe7': 500, u'\xe8': 556, u'\xe9': 556, u'\xea': 556, u'\xeb': 556, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 556, u'\xf1': 556, u'\xf2': 556, u'\xf3': 556, u'\xf4': 556, u'\xf5': 556, u'\xf6': 556, u'\xf7': 584, u'\xf8': 611, u'\xf9': 556, u'\xfa': 556, u'\xfb': 556, u'\xfc': 556, u'\xfd': 500, u'\xfe': 556, u'\xff': 500, u'\u0100': 667, u'\u0101': 556, u'\u0102': 667, u'\u0103': 556, u'\u0104': 667, u'\u0105': 556, u'\u0106': 722, u'\u0107': 500, u'\u010c': 722, u'\u010d': 500, u'\u010e': 722, u'\u010f': 643, u'\u0110': 722, u'\u0111': 556, u'\u0112': 667, u'\u0113': 556, u'\u0116': 667, u'\u0117': 556, u'\u0118': 667, u'\u0119': 556, u'\u011a': 667, u'\u011b': 556, u'\u011e': 778, u'\u011f': 556, u'\u0122': 778, u'\u0123': 556, u'\u012a': 278, u'\u012b': 278, u'\u012e': 278, u'\u012f': 222, u'\u0130': 278, u'\u0131': 278, u'\u0136': 667, u'\u0137': 500, u'\u0139': 556, u'\u013a': 222, u'\u013b': 556, u'\u013c': 222, u'\u013d': 556, u'\u013e': 299, u'\u0141': 556, u'\u0142': 222, u'\u0143': 722, u'\u0144': 556, u'\u0145': 722, u'\u0146': 556, u'\u0147': 722, u'\u0148': 556, u'\u014c': 778, u'\u014d': 556, u'\u0150': 778, u'\u0151': 556, u'\u0152': 1000, u'\u0153': 944, u'\u0154': 722, u'\u0155': 333, u'\u0156': 722, u'\u0157': 333, u'\u0158': 722, u'\u0159': 333, u'\u015a': 667, u'\u015b': 500, u'\u015e': 667, u'\u015f': 500, u'\u0160': 667, u'\u0161': 500, u'\u0162': 611, u'\u0163': 278, u'\u0164': 611, u'\u0165': 317, u'\u016a': 722, u'\u016b': 556, u'\u016e': 722, u'\u016f': 556, u'\u0170': 722, u'\u0171': 556, u'\u0172': 722, u'\u0173': 556, u'\u0178': 667, u'\u0179': 611, u'\u017a': 500, u'\u017b': 611, u'\u017c': 500, u'\u017d': 611, u'\u017e': 500, u'\u0192': 556, u'\u0218': 667, u'\u0219': 500, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 556, u'\u2014': 1000, u'\u2018': 222, u'\u2019': 222, u'\u201a': 222, u'\u201c': 333, u'\u201d': 333, u'\u201e': 333, u'\u2020': 556, u'\u2021': 556, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 1000, u'\u2202': 476, u'\u2206': 612, u'\u2211': 600, u'\u2212': 584, u'\u221a': 453, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 471, u'\uf6c3': 250, u'\ufb01': 500, u'\ufb02': 500}),
 'Symbol': ({'FontName': 'Symbol', 'FontBBox': (-180.0, -293.0, 1090.0, 1010.0), 'FontWeight': 'Medium', 'FontFamily': 'Symbol', 'Flags': 0, 'ItalicAngle': 0.0}, {u' ': 250, u'!': 333, u'#': 500, u'%': 833, u'&': 778, u'(': 333, u')': 333, u'+': 549, u',': 250, u'.': 250, u'/': 278, u'0': 500, u'1': 500, u'2': 500, u'3': 500, u'4': 500, u'5': 500, u'6': 500, u'7': 500, u'8': 500, u'9': 500, u':': 278, u';': 278, u'<': 549, u'=': 549, u'>': 549, u'?': 444, u'[': 333, u']': 333, u'_': 500, u'{': 480, u'|': 200, u'}': 480, u'\xac': 713, u'\xb0': 400, u'\xb1': 549, u'\xb5': 576, u'\xd7': 549, u'\xf7': 549, u'\u0192': 500, u'\u0391': 722, u'\u0392': 667, u'\u0393': 603, u'\u0395': 611, u'\u0396': 611, u'\u0397': 722, u'\u0398': 741, u'\u0399': 333, u'\u039a': 722, u'\u039b': 686, u'\u039c': 889, u'\u039d': 722, u'\u039e': 645, u'\u039f': 722, u'\u03a0': 768, u'\u03a1': 556, u'\u03a3': 592, u'\u03a4': 611, u'\u03a5': 690, u'\u03a6': 763, u'\u03a7': 722, u'\u03a8': 795, u'\u03b1': 631, u'\u03b2': 549, u'\u03b3': 411, u'\u03b4': 494, u'\u03b5': 439, u'\u03b6': 494, u'\u03b7': 603, u'\u03b8': 521, u'\u03b9': 329, u'\u03ba': 549, u'\u03bb': 549, u'\u03bd': 521, u'\u03be': 493, u'\u03bf': 549, u'\u03c0': 549, u'\u03c1': 549, u'\u03c2': 439, u'\u03c3': 603, u'\u03c4': 439, u'\u03c5': 576, u'\u03c6': 521, u'\u03c7': 549, u'\u03c8': 686, u'\u03c9': 686, u'\u03d1': 631, u'\u03d2': 620, u'\u03d5': 603, u'\u03d6': 713, u'\u2022': 460, u'\u2026': 1000, u'\u2032': 247, u'\u2033': 411, u'\u2044': 167, u'\u20ac': 750, u'\u2111': 686, u'\u2118': 987, u'\u211c': 795, u'\u2126': 768, u'\u2135': 823, u'\u2190': 987, u'\u2191': 603, u'\u2192': 987, u'\u2193': 603, u'\u2194': 1042, u'\u21b5': 658, u'\u21d0': 987, u'\u21d1': 603, u'\u21d2': 987, u'\u21d3': 603, u'\u21d4': 1042, u'\u2200': 713, u'\u2202': 494, u'\u2203': 549, u'\u2205': 823, u'\u2206': 612, u'\u2207': 713, u'\u2208': 713, u'\u2209': 713, u'\u220b': 439, u'\u220f': 823, u'\u2211': 713, u'\u2212': 549, u'\u2217': 500, u'\u221a': 549, u'\u221d': 713, u'\u221e': 713, u'\u2220': 768, u'\u2227': 603, u'\u2228': 603, u'\u2229': 768, u'\u222a': 768, u'\u222b': 274, u'\u2234': 863, u'\u223c': 549, u'\u2245': 549, u'\u2248': 549, u'\u2260': 549, u'\u2261': 549, u'\u2264': 549, u'\u2265': 549, u'\u2282': 713, u'\u2283': 713, u'\u2284': 713, u'\u2286': 713, u'\u2287': 713, u'\u2295': 768, u'\u2297': 768, u'\u22a5': 658, u'\u22c5': 250, u'\u2320': 686, u'\u2321': 686, u'\u2329': 329, u'\u232a': 329, u'\u25ca': 494, u'\u2660': 753, u'\u2663': 753, u'\u2665': 753, u'\u2666': 753, u'\uf6d9': 790, u'\uf6da': 790, u'\uf6db': 890, u'\uf8e5': 500, u'\uf8e6': 603, u'\uf8e7': 1000, u'\uf8e8': 790, u'\uf8e9': 790, u'\uf8ea': 786, u'\uf8eb': 384, u'\uf8ec': 384, u'\uf8ed': 384, u'\uf8ee': 384, u'\uf8ef': 384, u'\uf8f0': 384, u'\uf8f1': 494, u'\uf8f2': 494, u'\uf8f3': 494, u'\uf8f4': 494, u'\uf8f5': 686, u'\uf8f6': 384, u'\uf8f7': 384, u'\uf8f8': 384, u'\uf8f9': 384, u'\uf8fa': 384, u'\uf8fb': 384, u'\uf8fc': 494, u'\uf8fd': 494, u'\uf8fe': 494, u'\uf8ff': 790}),
 'Times-Bold': ({'FontName': 'Times-Bold', 'Descent': -217.0, 'FontBBox': (-168.0, -218.0, 1000.0, 935.0), 'FontWeight': 'Bold', 'CapHeight': 676.0, 'FontFamily': 'Times', 'Flags': 0, 'XHeight': 461.0, 'ItalicAngle': 0.0, 'Ascent': 683.0}, {u' ': 250, u'!': 333, u'"': 555, u'#': 500, u'$': 500, u'%': 1000, u'&': 833, u"'": 278, u'(': 333, u')': 333, u'*': 500, u'+': 570, u',': 250, u'-': 333, u'.': 250, u'/': 278, u'0': 500, u'1': 500, u'2': 500, u'3': 500, u'4': 500, u'5': 500, u'6': 500, u'7': 500, u'8': 500, u'9': 500, u':': 333, u';': 333, u'<': 570, u'=': 570, u'>': 570, u'?': 500, u'@': 930, u'A': 722, u'B': 667, u'C': 722, u'D': 722, u'E': 667, u'F': 611, u'G': 778, u'H': 778, u'I': 389, u'J': 500, u'K': 778, u'L': 667, u'M': 944, u'N': 722, u'O': 778, u'P': 611, u'Q': 778, u'R': 722, u'S': 556, u'T': 667, u'U': 722, u'V': 722, u'W': 1000, u'X': 722, u'Y': 722, u'Z': 667, u'[': 333, u'\\': 278, u']': 333, u'^': 581, u'_': 500, u'`': 333, u'a': 500, u'b': 556, u'c': 444, u'd': 556, u'e': 444, u'f': 333, u'g': 500, u'h': 556, u'i': 278, u'j': 333, u'k': 556, u'l': 278, u'm': 833, u'n': 556, u'o': 500, u'p': 556, u'q': 556, u'r': 444, u's': 389, u't': 333, u'u': 556, u'v': 500, u'w': 722, u'x': 500, u'y': 500, u'z': 444, u'{': 394, u'|': 220, u'}': 394, u'~': 520, u'\xa1': 333, u'\xa2': 500, u'\xa3': 500, u'\xa4': 500, u'\xa5': 500, u'\xa6': 220, u'\xa7': 500, u'\xa8': 333, u'\xa9': 747, u'\xaa': 300, u'\xab': 500, u'\xac': 570, u'\xae': 747, u'\xaf': 333, u'\xb0': 400, u'\xb1': 570, u'\xb2': 300, u'\xb3': 300, u'\xb4': 333, u'\xb5': 556, u'\xb6': 540, u'\xb7': 250, u'\xb8': 333, u'\xb9': 300, u'\xba': 330, u'\xbb': 500, u'\xbc': 750, u'\xbd': 750, u'\xbe': 750, u'\xbf': 500, u'\xc0': 722, u'\xc1': 722, u'\xc2': 722, u'\xc3': 722, u'\xc4': 722, u'\xc5': 722, u'\xc6': 1000, u'\xc7': 722, u'\xc8': 667, u'\xc9': 667, u'\xca': 667, u'\xcb': 667, u'\xcc': 389, u'\xcd': 389, u'\xce': 389, u'\xcf': 389, u'\xd0': 722, u'\xd1': 722, u'\xd2': 778, u'\xd3': 778, u'\xd4': 778, u'\xd5': 778, u'\xd6': 778, u'\xd7': 570, u'\xd8': 778, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 722, u'\xde': 611, u'\xdf': 556, u'\xe0': 500, u'\xe1': 500, u'\xe2': 500, u'\xe3': 500, u'\xe4': 500, u'\xe5': 500, u'\xe6': 722, u'\xe7': 444, u'\xe8': 444, u'\xe9': 444, u'\xea': 444, u'\xeb': 444, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 500, u'\xf1': 556, u'\xf2': 500, u'\xf3': 500, u'\xf4': 500, u'\xf5': 500, u'\xf6': 500, u'\xf7': 570, u'\xf8': 500, u'\xf9': 556, u'\xfa': 556, u'\xfb': 556, u'\xfc': 556, u'\xfd': 500, u'\xfe': 556, u'\xff': 500, u'\u0100': 722, u'\u0101': 500, u'\u0102': 722, u'\u0103': 500, u'\u0104': 722, u'\u0105': 500, u'\u0106': 722, u'\u0107': 444, u'\u010c': 722, u'\u010d': 444, u'\u010e': 722, u'\u010f': 672, u'\u0110': 722, u'\u0111': 556, u'\u0112': 667, u'\u0113': 444, u'\u0116': 667, u'\u0117': 444, u'\u0118': 667, u'\u0119': 444, u'\u011a': 667, u'\u011b': 444, u'\u011e': 778, u'\u011f': 500, u'\u0122': 778, u'\u0123': 500, u'\u012a': 389, u'\u012b': 278, u'\u012e': 389, u'\u012f': 278, u'\u0130': 389, u'\u0131': 278, u'\u0136': 778, u'\u0137': 556, u'\u0139': 667, u'\u013a': 278, u'\u013b': 667, u'\u013c': 278, u'\u013d': 667, u'\u013e': 394, u'\u0141': 667, u'\u0142': 278, u'\u0143': 722, u'\u0144': 556, u'\u0145': 722, u'\u0146': 556, u'\u0147': 722, u'\u0148': 556, u'\u014c': 778, u'\u014d': 500, u'\u0150': 778, u'\u0151': 500, u'\u0152': 1000, u'\u0153': 722, u'\u0154': 722, u'\u0155': 444, u'\u0156': 722, u'\u0157': 444, u'\u0158': 722, u'\u0159': 444, u'\u015a': 556, u'\u015b': 389, u'\u015e': 556, u'\u015f': 389, u'\u0160': 556, u'\u0161': 389, u'\u0162': 667, u'\u0163': 333, u'\u0164': 667, u'\u0165': 416, u'\u016a': 722, u'\u016b': 556, u'\u016e': 722, u'\u016f': 556, u'\u0170': 722, u'\u0171': 556, u'\u0172': 722, u'\u0173': 556, u'\u0178': 722, u'\u0179': 667, u'\u017a': 444, u'\u017b': 667, u'\u017c': 444, u'\u017d': 667, u'\u017e': 444, u'\u0192': 500, u'\u0218': 556, u'\u0219': 389, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 500, u'\u2014': 1000, u'\u2018': 333, u'\u2019': 333, u'\u201a': 333, u'\u201c': 500, u'\u201d': 500, u'\u201e': 500, u'\u2020': 500, u'\u2021': 500, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 1000, u'\u2202': 494, u'\u2206': 612, u'\u2211': 600, u'\u2212': 570, u'\u221a': 549, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 494, u'\uf6c3': 250, u'\ufb01': 556, u'\ufb02': 556}),
 'Times-BoldItalic': ({'FontName': 'Times-BoldItalic', 'Descent': -217.0, 'FontBBox': (-200.0, -218.0, 996.0, 921.0), 'FontWeight': 'Bold', 'CapHeight': 669.0, 'FontFamily': 'Times', 'Flags': 0, 'XHeight': 462.0, 'ItalicAngle': -15.0, 'Ascent': 683.0}, {u' ': 250, u'!': 389, u'"': 555, u'#': 500, u'$': 500, u'%': 833, u'&': 778, u"'": 278, u'(': 333, u')': 333, u'*': 500, u'+': 570, u',': 250, u'-': 333, u'.': 250, u'/': 278, u'0': 500, u'1': 500, u'2': 500, u'3': 500, u'4': 500, u'5': 500, u'6': 500, u'7': 500, u'8': 500, u'9': 500, u':': 333, u';': 333, u'<': 570, u'=': 570, u'>': 570, u'?': 500, u'@': 832, u'A': 667, u'B': 667, u'C': 667, u'D': 722, u'E': 667, u'F': 667, u'G': 722, u'H': 778, u'I': 389, u'J': 500, u'K': 667, u'L': 611, u'M': 889, u'N': 722, u'O': 722, u'P': 611, u'Q': 722, u'R': 667, u'S': 556, u'T': 611, u'U': 722, u'V': 667, u'W': 889, u'X': 667, u'Y': 611, u'Z': 611, u'[': 333, u'\\': 278, u']': 333, u'^': 570, u'_': 500, u'`': 333, u'a': 500, u'b': 500, u'c': 444, u'd': 500, u'e': 444, u'f': 333, u'g': 500, u'h': 556, u'i': 278, u'j': 278, u'k': 500, u'l': 278, u'm': 778, u'n': 556, u'o': 500, u'p': 500, u'q': 500, u'r': 389, u's': 389, u't': 278, u'u': 556, u'v': 444, u'w': 667, u'x': 500, u'y': 444, u'z': 389, u'{': 348, u'|': 220, u'}': 348, u'~': 570, u'\xa1': 389, u'\xa2': 500, u'\xa3': 500, u'\xa4': 500, u'\xa5': 500, u'\xa6': 220, u'\xa7': 500, u'\xa8': 333, u'\xa9': 747, u'\xaa': 266, u'\xab': 500, u'\xac': 606, u'\xae': 747, u'\xaf': 333, u'\xb0': 400, u'\xb1': 570, u'\xb2': 300, u'\xb3': 300, u'\xb4': 333, u'\xb5': 576, u'\xb6': 500, u'\xb7': 250, u'\xb8': 333, u'\xb9': 300, u'\xba': 300, u'\xbb': 500, u'\xbc': 750, u'\xbd': 750, u'\xbe': 750, u'\xbf': 500, u'\xc0': 667, u'\xc1': 667, u'\xc2': 667, u'\xc3': 667, u'\xc4': 667, u'\xc5': 667, u'\xc6': 944, u'\xc7': 667, u'\xc8': 667, u'\xc9': 667, u'\xca': 667, u'\xcb': 667, u'\xcc': 389, u'\xcd': 389, u'\xce': 389, u'\xcf': 389, u'\xd0': 722, u'\xd1': 722, u'\xd2': 722, u'\xd3': 722, u'\xd4': 722, u'\xd5': 722, u'\xd6': 722, u'\xd7': 570, u'\xd8': 722, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 611, u'\xde': 611, u'\xdf': 500, u'\xe0': 500, u'\xe1': 500, u'\xe2': 500, u'\xe3': 500, u'\xe4': 500, u'\xe5': 500, u'\xe6': 722, u'\xe7': 444, u'\xe8': 444, u'\xe9': 444, u'\xea': 444, u'\xeb': 444, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 500, u'\xf1': 556, u'\xf2': 500, u'\xf3': 500, u'\xf4': 500, u'\xf5': 500, u'\xf6': 500, u'\xf7': 570, u'\xf8': 500, u'\xf9': 556, u'\xfa': 556, u'\xfb': 556, u'\xfc': 556, u'\xfd': 444, u'\xfe': 500, u'\xff': 444, u'\u0100': 667, u'\u0101': 500, u'\u0102': 667, u'\u0103': 500, u'\u0104': 667, u'\u0105': 500, u'\u0106': 667, u'\u0107': 444, u'\u010c': 667, u'\u010d': 444, u'\u010e': 722, u'\u010f': 608, u'\u0110': 722, u'\u0111': 500, u'\u0112': 667, u'\u0113': 444, u'\u0116': 667, u'\u0117': 444, u'\u0118': 667, u'\u0119': 444, u'\u011a': 667, u'\u011b': 444, u'\u011e': 722, u'\u011f': 500, u'\u0122': 722, u'\u0123': 500, u'\u012a': 389, u'\u012b': 278, u'\u012e': 389, u'\u012f': 278, u'\u0130': 389, u'\u0131': 278, u'\u0136': 667, u'\u0137': 500, u'\u0139': 611, u'\u013a': 278, u'\u013b': 611, u'\u013c': 278, u'\u013d': 611, u'\u013e': 382, u'\u0141': 611, u'\u0142': 278, u'\u0143': 722, u'\u0144': 556, u'\u0145': 722, u'\u0146': 556, u'\u0147': 722, u'\u0148': 556, u'\u014c': 722, u'\u014d': 500, u'\u0150': 722, u'\u0151': 500, u'\u0152': 944, u'\u0153': 722, u'\u0154': 667, u'\u0155': 389, u'\u0156': 667, u'\u0157': 389, u'\u0158': 667, u'\u0159': 389, u'\u015a': 556, u'\u015b': 389, u'\u015e': 556, u'\u015f': 389, u'\u0160': 556, u'\u0161': 389, u'\u0162': 611, u'\u0163': 278, u'\u0164': 611, u'\u0165': 366, u'\u016a': 722, u'\u016b': 556, u'\u016e': 722, u'\u016f': 556, u'\u0170': 722, u'\u0171': 556, u'\u0172': 722, u'\u0173': 556, u'\u0178': 611, u'\u0179': 611, u'\u017a': 389, u'\u017b': 611, u'\u017c': 389, u'\u017d': 611, u'\u017e': 389, u'\u0192': 500, u'\u0218': 556, u'\u0219': 389, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 500, u'\u2014': 1000, u'\u2018': 333, u'\u2019': 333, u'\u201a': 333, u'\u201c': 500, u'\u201d': 500, u'\u201e': 500, u'\u2020': 500, u'\u2021': 500, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 1000, u'\u2202': 494, u'\u2206': 612, u'\u2211': 600, u'\u2212': 606, u'\u221a': 549, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 494, u'\uf6c3': 250, u'\ufb01': 556, u'\ufb02': 556}),
 'Times-Italic': ({'FontName': 'Times-Italic', 'Descent': -217.0, 'FontBBox': (-169.0, -217.0, 1010.0, 883.0), 'FontWeight': 'Medium', 'CapHeight': 653.0, 'FontFamily': 'Times', 'Flags': 0, 'XHeight': 441.0, 'ItalicAngle': -15.5, 'Ascent': 683.0}, {u' ': 250, u'!': 333, u'"': 420, u'#': 500, u'$': 500, u'%': 833, u'&': 778, u"'": 214, u'(': 333, u')': 333, u'*': 500, u'+': 675, u',': 250, u'-': 333, u'.': 250, u'/': 278, u'0': 500, u'1': 500, u'2': 500, u'3': 500, u'4': 500, u'5': 500, u'6': 500, u'7': 500, u'8': 500, u'9': 500, u':': 333, u';': 333, u'<': 675, u'=': 675, u'>': 675, u'?': 500, u'@': 920, u'A': 611, u'B': 611, u'C': 667, u'D': 722, u'E': 611, u'F': 611, u'G': 722, u'H': 722, u'I': 333, u'J': 444, u'K': 667, u'L': 556, u'M': 833, u'N': 667, u'O': 722, u'P': 611, u'Q': 722, u'R': 611, u'S': 500, u'T': 556, u'U': 722, u'V': 611, u'W': 833, u'X': 611, u'Y': 556, u'Z': 556, u'[': 389, u'\\': 278, u']': 389, u'^': 422, u'_': 500, u'`': 333, u'a': 500, u'b': 500, u'c': 444, u'd': 500, u'e': 444, u'f': 278, u'g': 500, u'h': 500, u'i': 278, u'j': 278, u'k': 444, u'l': 278, u'm': 722, u'n': 500, u'o': 500, u'p': 500, u'q': 500, u'r': 389, u's': 389, u't': 278, u'u': 500, u'v': 444, u'w': 667, u'x': 444, u'y': 444, u'z': 389, u'{': 400, u'|': 275, u'}': 400, u'~': 541, u'\xa1': 389, u'\xa2': 500, u'\xa3': 500, u'\xa4': 500, u'\xa5': 500, u'\xa6': 275, u'\xa7': 500, u'\xa8': 333, u'\xa9': 760, u'\xaa': 276, u'\xab': 500, u'\xac': 675, u'\xae': 760, u'\xaf': 333, u'\xb0': 400, u'\xb1': 675, u'\xb2': 300, u'\xb3': 300, u'\xb4': 333, u'\xb5': 500, u'\xb6': 523, u'\xb7': 250, u'\xb8': 333, u'\xb9': 300, u'\xba': 310, u'\xbb': 500, u'\xbc': 750, u'\xbd': 750, u'\xbe': 750, u'\xbf': 500, u'\xc0': 611, u'\xc1': 611, u'\xc2': 611, u'\xc3': 611, u'\xc4': 611, u'\xc5': 611, u'\xc6': 889, u'\xc7': 667, u'\xc8': 611, u'\xc9': 611, u'\xca': 611, u'\xcb': 611, u'\xcc': 333, u'\xcd': 333, u'\xce': 333, u'\xcf': 333, u'\xd0': 722, u'\xd1': 667, u'\xd2': 722, u'\xd3': 722, u'\xd4': 722, u'\xd5': 722, u'\xd6': 722, u'\xd7': 675, u'\xd8': 722, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 556, u'\xde': 611, u'\xdf': 500, u'\xe0': 500, u'\xe1': 500, u'\xe2': 500, u'\xe3': 500, u'\xe4': 500, u'\xe5': 500, u'\xe6': 667, u'\xe7': 444, u'\xe8': 444, u'\xe9': 444, u'\xea': 444, u'\xeb': 444, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 500, u'\xf1': 500, u'\xf2': 500, u'\xf3': 500, u'\xf4': 500, u'\xf5': 500, u'\xf6': 500, u'\xf7': 675, u'\xf8': 500, u'\xf9': 500, u'\xfa': 500, u'\xfb': 500, u'\xfc': 500, u'\xfd': 444, u'\xfe': 500, u'\xff': 444, u'\u0100': 611, u'\u0101': 500, u'\u0102': 611, u'\u0103': 500, u'\u0104': 611, u'\u0105': 500, u'\u0106': 667, u'\u0107': 444, u'\u010c': 667, u'\u010d': 444, u'\u010e': 722, u'\u010f': 544, u'\u0110': 722, u'\u0111': 500, u'\u0112': 611, u'\u0113': 444, u'\u0116': 611, u'\u0117': 444, u'\u0118': 611, u'\u0119': 444, u'\u011a': 611, u'\u011b': 444, u'\u011e': 722, u'\u011f': 500, u'\u0122': 722, u'\u0123': 500, u'\u012a': 333, u'\u012b': 278, u'\u012e': 333, u'\u012f': 278, u'\u0130': 333, u'\u0131': 278, u'\u0136': 667, u'\u0137': 444, u'\u0139': 556, u'\u013a': 278, u'\u013b': 556, u'\u013c': 278, u'\u013d': 611, u'\u013e': 300, u'\u0141': 556, u'\u0142': 278, u'\u0143': 667, u'\u0144': 500, u'\u0145': 667, u'\u0146': 500, u'\u0147': 667, u'\u0148': 500, u'\u014c': 722, u'\u014d': 500, u'\u0150': 722, u'\u0151': 500, u'\u0152': 944, u'\u0153': 667, u'\u0154': 611, u'\u0155': 389, u'\u0156': 611, u'\u0157': 389, u'\u0158': 611, u'\u0159': 389, u'\u015a': 500, u'\u015b': 389, u'\u015e': 500, u'\u015f': 389, u'\u0160': 500, u'\u0161': 389, u'\u0162': 556, u'\u0163': 278, u'\u0164': 556, u'\u0165': 300, u'\u016a': 722, u'\u016b': 500, u'\u016e': 722, u'\u016f': 500, u'\u0170': 722, u'\u0171': 500, u'\u0172': 722, u'\u0173': 500, u'\u0178': 556, u'\u0179': 556, u'\u017a': 389, u'\u017b': 556, u'\u017c': 389, u'\u017d': 556, u'\u017e': 389, u'\u0192': 500, u'\u0218': 500, u'\u0219': 389, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 500, u'\u2014': 889, u'\u2018': 333, u'\u2019': 333, u'\u201a': 333, u'\u201c': 556, u'\u201d': 556, u'\u201e': 556, u'\u2020': 500, u'\u2021': 500, u'\u2022': 350, u'\u2026': 889, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 980, u'\u2202': 476, u'\u2206': 612, u'\u2211': 600, u'\u2212': 675, u'\u221a': 453, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 471, u'\uf6c3': 250, u'\ufb01': 500, u'\ufb02': 500}),
 'Times-Roman': ({'FontName': 'Times-Roman', 'Descent': -217.0, 'FontBBox': (-168.0, -218.0, 1000.0, 898.0), 'FontWeight': 'Roman', 'CapHeight': 662.0, 'FontFamily': 'Times', 'Flags': 0, 'XHeight': 450.0, 'ItalicAngle': 0.0, 'Ascent': 683.0}, {u' ': 250, u'!': 333, u'"': 408, u'#': 500, u'$': 500, u'%': 833, u'&': 778, u"'": 180, u'(': 333, u')': 333, u'*': 500, u'+': 564, u',': 250, u'-': 333, u'.': 250, u'/': 278, u'0': 500, u'1': 500, u'2': 500, u'3': 500, u'4': 500, u'5': 500, u'6': 500, u'7': 500, u'8': 500, u'9': 500, u':': 278, u';': 278, u'<': 564, u'=': 564, u'>': 564, u'?': 444, u'@': 921, u'A': 722, u'B': 667, u'C': 667, u'D': 722, u'E': 611, u'F': 556, u'G': 722, u'H': 722, u'I': 333, u'J': 389, u'K': 722, u'L': 611, u'M': 889, u'N': 722, u'O': 722, u'P': 556, u'Q': 722, u'R': 667, u'S': 556, u'T': 611, u'U': 722, u'V': 722, u'W': 944, u'X': 722, u'Y': 722, u'Z': 611, u'[': 333, u'\\': 278, u']': 333, u'^': 469, u'_': 500, u'`': 333, u'a': 444, u'b': 500, u'c': 444, u'd': 500, u'e': 444, u'f': 333, u'g': 500, u'h': 500, u'i': 278, u'j': 278, u'k': 500, u'l': 278, u'm': 778, u'n': 500, u'o': 500, u'p': 500, u'q': 500, u'r': 333, u's': 389, u't': 278, u'u': 500, u'v': 500, u'w': 722, u'x': 500, u'y': 500, u'z': 444, u'{': 480, u'|': 200, u'}': 480, u'~': 541, u'\xa1': 333, u'\xa2': 500, u'\xa3': 500, u'\xa4': 500, u'\xa5': 500, u'\xa6': 200, u'\xa7': 500, u'\xa8': 333, u'\xa9': 760, u'\xaa': 276, u'\xab': 500, u'\xac': 564, u'\xae': 760, u'\xaf': 333, u'\xb0': 400, u'\xb1': 564, u'\xb2': 300, u'\xb3': 300, u'\xb4': 333, u'\xb5': 500, u'\xb6': 453, u'\xb7': 250, u'\xb8': 333, u'\xb9': 300, u'\xba': 310, u'\xbb': 500, u'\xbc': 750, u'\xbd': 750, u'\xbe': 750, u'\xbf': 444, u'\xc0': 722, u'\xc1': 722, u'\xc2': 722, u'\xc3': 722, u'\xc4': 722, u'\xc5': 722, u'\xc6': 889, u'\xc7': 667, u'\xc8': 611, u'\xc9': 611, u'\xca': 611, u'\xcb': 611, u'\xcc': 333, u'\xcd': 333, u'\xce': 333, u'\xcf': 333, u'\xd0': 722, u'\xd1': 722, u'\xd2': 722, u'\xd3': 722, u'\xd4': 722, u'\xd5': 722, u'\xd6': 722, u'\xd7': 564, u'\xd8': 722, u'\xd9': 722, u'\xda': 722, u'\xdb': 722, u'\xdc': 722, u'\xdd': 722, u'\xde': 556, u'\xdf': 500, u'\xe0': 444, u'\xe1': 444, u'\xe2': 444, u'\xe3': 444, u'\xe4': 444, u'\xe5': 444, u'\xe6': 667, u'\xe7': 444, u'\xe8': 444, u'\xe9': 444, u'\xea': 444, u'\xeb': 444, u'\xec': 278, u'\xed': 278, u'\xee': 278, u'\xef': 278, u'\xf0': 500, u'\xf1': 500, u'\xf2': 500, u'\xf3': 500, u'\xf4': 500, u'\xf5': 500, u'\xf6': 500, u'\xf7': 564, u'\xf8': 500, u'\xf9': 500, u'\xfa': 500, u'\xfb': 500, u'\xfc': 500, u'\xfd': 500, u'\xfe': 500, u'\xff': 500, u'\u0100': 722, u'\u0101': 444, u'\u0102': 722, u'\u0103': 444, u'\u0104': 722, u'\u0105': 444, u'\u0106': 667, u'\u0107': 444, u'\u010c': 667, u'\u010d': 444, u'\u010e': 722, u'\u010f': 588, u'\u0110': 722, u'\u0111': 500, u'\u0112': 611, u'\u0113': 444, u'\u0116': 611, u'\u0117': 444, u'\u0118': 611, u'\u0119': 444, u'\u011a': 611, u'\u011b': 444, u'\u011e': 722, u'\u011f': 500, u'\u0122': 722, u'\u0123': 500, u'\u012a': 333, u'\u012b': 278, u'\u012e': 333, u'\u012f': 278, u'\u0130': 333, u'\u0131': 278, u'\u0136': 722, u'\u0137': 500, u'\u0139': 611, u'\u013a': 278, u'\u013b': 611, u'\u013c': 278, u'\u013d': 611, u'\u013e': 344, u'\u0141': 611, u'\u0142': 278, u'\u0143': 722, u'\u0144': 500, u'\u0145': 722, u'\u0146': 500, u'\u0147': 722, u'\u0148': 500, u'\u014c': 722, u'\u014d': 500, u'\u0150': 722, u'\u0151': 500, u'\u0152': 889, u'\u0153': 722, u'\u0154': 667, u'\u0155': 333, u'\u0156': 667, u'\u0157': 333, u'\u0158': 667, u'\u0159': 333, u'\u015a': 556, u'\u015b': 389, u'\u015e': 556, u'\u015f': 389, u'\u0160': 556, u'\u0161': 389, u'\u0162': 611, u'\u0163': 278, u'\u0164': 611, u'\u0165': 326, u'\u016a': 722, u'\u016b': 500, u'\u016e': 722, u'\u016f': 500, u'\u0170': 722, u'\u0171': 500, u'\u0172': 722, u'\u0173': 500, u'\u0178': 722, u'\u0179': 611, u'\u017a': 444, u'\u017b': 611, u'\u017c': 444, u'\u017d': 611, u'\u017e': 444, u'\u0192': 500, u'\u0218': 556, u'\u0219': 389, u'\u02c6': 333, u'\u02c7': 333, u'\u02d8': 333, u'\u02d9': 333, u'\u02da': 333, u'\u02db': 333, u'\u02dc': 333, u'\u02dd': 333, u'\u2013': 500, u'\u2014': 1000, u'\u2018': 333, u'\u2019': 333, u'\u201a': 333, u'\u201c': 444, u'\u201d': 444, u'\u201e': 444, u'\u2020': 500, u'\u2021': 500, u'\u2022': 350, u'\u2026': 1000, u'\u2030': 1000, u'\u2039': 333, u'\u203a': 333, u'\u2044': 167, u'\u2122': 980, u'\u2202': 476, u'\u2206': 612, u'\u2211': 600, u'\u2212': 564, u'\u221a': 453, u'\u2260': 549, u'\u2264': 549, u'\u2265': 549, u'\u25ca': 471, u'\uf6c3': 250, u'\ufb01': 556, u'\ufb02': 556}),
 'ZapfDingbats': ({'FontName': 'ZapfDingbats', 'FontBBox': (-1.0, -143.0, 981.0, 820.0), 'FontWeight': 'Medium', 'FontFamily': 'ITC', 'Flags': 0, 'ItalicAngle': 0.0}, {u'\x01': 974, u'\x02': 961, u'\x03': 980, u'\x04': 719, u'\x05': 789, u'\x06': 494, u'\x07': 552, u'\x08': 537, u'\t': 577, u'\n': 692, u'\x0b': 960, u'\x0c': 939, u'\r': 549, u'\x0e': 855, u'\x0f': 911, u'\x10': 933, u'\x11': 945, u'\x12': 974, u'\x13': 755, u'\x14': 846, u'\x15': 762, u'\x16': 761, u'\x17': 571, u'\x18': 677, u'\x19': 763, u'\x1a': 760, u'\x1b': 759, u'\x1c': 754, u'\x1d': 786, u'\x1e': 788, u'\x1f': 788, u' ': 790, u'!': 793, u'"': 794, u'#': 816, u'$': 823, u'%': 789, u'&': 841, u"'": 823, u'(': 833, u')': 816, u'*': 831, u'+': 923, u',': 744, u'-': 723, u'.': 749, u'/': 790, u'0': 792, u'1': 695, u'2': 776, u'3': 768, u'4': 792, u'5': 759, u'6': 707, u'7': 708, u'8': 682, u'9': 701, u':': 826, u';': 815, u'<': 789, u'=': 789, u'>': 707, u'?': 687, u'@': 696, u'A': 689, u'B': 786, u'C': 787, u'D': 713, u'E': 791, u'F': 785, u'G': 791, u'H': 873, u'I': 761, u'J': 762, u'K': 759, u'L': 892, u'M': 892, u'N': 788, u'O': 784, u'Q': 438, u'R': 138, u'S': 277, u'T': 415, u'U': 509, u'V': 410, u'W': 234, u'X': 234, u'Y': 390, u'Z': 390, u'[': 276, u'\\': 276, u']': 317, u'^': 317, u'_': 334, u'`': 334, u'a': 392, u'b': 392, u'c': 668, u'd': 668, u'e': 732, u'f': 544, u'g': 544, u'h': 910, u'i': 911, u'j': 667, u'k': 760, u'l': 760, u'm': 626, u'n': 694, u'o': 595, u'p': 776, u'u': 690, u'v': 791, u'w': 790, u'x': 788, u'y': 788, u'z': 788, u'{': 788, u'|': 788, u'}': 788, u'~': 788, u'\x7f': 788, u'\x80': 788, u'\x81': 788, u'\x82': 788, u'\x83': 788, u'\x84': 788, u'\x85': 788, u'\x86': 788, u'\x87': 788, u'\x88': 788, u'\x89': 788, u'\x8a': 788, u'\x8b': 788, u'\x8c': 788, u'\x8d': 788, u'\x8e': 788, u'\x8f': 788, u'\x90': 788, u'\x91': 788, u'\x92': 788, u'\x93': 788, u'\x94': 788, u'\x95': 788, u'\x96': 788, u'\x97': 788, u'\x98': 788, u'\x99': 788, u'\x9a': 788, u'\x9b': 788, u'\x9c': 788, u'\x9d': 788, u'\x9e': 788, u'\x9f': 788, u'\xa0': 894, u'\xa1': 838, u'\xa2': 924, u'\xa3': 1016, u'\xa4': 458, u'\xa5': 924, u'\xa6': 918, u'\xa7': 927, u'\xa8': 928, u'\xa9': 928, u'\xaa': 834, u'\xab': 873, u'\xac': 828, u'\xad': 924, u'\xae': 917, u'\xaf': 930, u'\xb0': 931, u'\xb1': 463, u'\xb2': 883, u'\xb3': 836, u'\xb4': 867, u'\xb5': 696, u'\xb6': 874, u'\xb7': 760, u'\xb8': 946, u'\xb9': 865, u'\xba': 967, u'\xbb': 831, u'\xbc': 873, u'\xbd': 927, u'\xbe': 970, u'\xbf': 918, u'\xc0': 748, u'\xc1': 836, u'\xc2': 771, u'\xc3': 888, u'\xc4': 748, u'\xc5': 771, u'\xc6': 888, u'\xc7': 867, u'\xc8': 696, u'\xc9': 874, u'\xca': 974, u'\xcb': 762, u'\xcc': 759, u'\xcd': 509, u'\xce': 410}),
}

########NEW FILE########
__FILENAME__ = glyphlist
#!/usr/bin/env python

""" Mappings from Adobe glyph names to Unicode characters.

In some CMap tables, Adobe glyph names are used for specifying
Unicode characters instead of using decimal/hex character code.

The following data was taken by

  $ wget http://www.adobe.com/devnet/opentype/archives/glyphlist.txt
  $ python tools/conv_glyphlist.py glyphlist.txt > glyphlist.py

"""

# ###################################################################################
# Copyright (c) 1997,1998,2002,2007 Adobe Systems Incorporated
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this documentation file to use, copy, publish, distribute,
# sublicense, and/or sell copies of the documentation, and to permit
# others to do the same, provided that:
# - No modification, editing or other alteration of this document is
# allowed; and
# - The above copyright notice and this permission notice shall be
# included in all copies of the documentation.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this documentation file, to create their own derivative works
# from the content of this document to use, copy, publish, distribute,
# sublicense, and/or sell the derivative works, and to permit others to do
# the same, provided that the derived work is not represented as being a
# copy or version of this document.
#
# Adobe shall not be liable to any party for any loss of revenue or profit
# or for indirect, incidental, special, consequential, or other similar
# damages, whether based on tort (including without limitation negligence
# or strict liability), contract or other legal or equitable grounds even
# if Adobe has been advised or had reason to know of the possibility of
# such damages. The Adobe materials are provided on an "AS IS" basis.
# Adobe specifically disclaims all express, statutory, or implied
# warranties relating to the Adobe materials, including but not limited to
# those concerning merchantability or fitness for a particular purpose or
# non-infringement of any third party rights regarding the Adobe
# materials.
# ###################################################################################
# Name:          Adobe Glyph List
# Table version: 2.0
# Date:          September 20, 2002
#
# See http://partners.adobe.com/asn/developer/typeforum/unicodegn.html
#
# Format: Semicolon-delimited fields:
#            (1) glyph name
#            (2) Unicode scalar value

glyphname2unicode = {
 'A': u'\u0041',
 'AE': u'\u00C6',
 'AEacute': u'\u01FC',
 'AEmacron': u'\u01E2',
 'AEsmall': u'\uF7E6',
 'Aacute': u'\u00C1',
 'Aacutesmall': u'\uF7E1',
 'Abreve': u'\u0102',
 'Abreveacute': u'\u1EAE',
 'Abrevecyrillic': u'\u04D0',
 'Abrevedotbelow': u'\u1EB6',
 'Abrevegrave': u'\u1EB0',
 'Abrevehookabove': u'\u1EB2',
 'Abrevetilde': u'\u1EB4',
 'Acaron': u'\u01CD',
 'Acircle': u'\u24B6',
 'Acircumflex': u'\u00C2',
 'Acircumflexacute': u'\u1EA4',
 'Acircumflexdotbelow': u'\u1EAC',
 'Acircumflexgrave': u'\u1EA6',
 'Acircumflexhookabove': u'\u1EA8',
 'Acircumflexsmall': u'\uF7E2',
 'Acircumflextilde': u'\u1EAA',
 'Acute': u'\uF6C9',
 'Acutesmall': u'\uF7B4',
 'Acyrillic': u'\u0410',
 'Adblgrave': u'\u0200',
 'Adieresis': u'\u00C4',
 'Adieresiscyrillic': u'\u04D2',
 'Adieresismacron': u'\u01DE',
 'Adieresissmall': u'\uF7E4',
 'Adotbelow': u'\u1EA0',
 'Adotmacron': u'\u01E0',
 'Agrave': u'\u00C0',
 'Agravesmall': u'\uF7E0',
 'Ahookabove': u'\u1EA2',
 'Aiecyrillic': u'\u04D4',
 'Ainvertedbreve': u'\u0202',
 'Alpha': u'\u0391',
 'Alphatonos': u'\u0386',
 'Amacron': u'\u0100',
 'Amonospace': u'\uFF21',
 'Aogonek': u'\u0104',
 'Aring': u'\u00C5',
 'Aringacute': u'\u01FA',
 'Aringbelow': u'\u1E00',
 'Aringsmall': u'\uF7E5',
 'Asmall': u'\uF761',
 'Atilde': u'\u00C3',
 'Atildesmall': u'\uF7E3',
 'Aybarmenian': u'\u0531',
 'B': u'\u0042',
 'Bcircle': u'\u24B7',
 'Bdotaccent': u'\u1E02',
 'Bdotbelow': u'\u1E04',
 'Becyrillic': u'\u0411',
 'Benarmenian': u'\u0532',
 'Beta': u'\u0392',
 'Bhook': u'\u0181',
 'Blinebelow': u'\u1E06',
 'Bmonospace': u'\uFF22',
 'Brevesmall': u'\uF6F4',
 'Bsmall': u'\uF762',
 'Btopbar': u'\u0182',
 'C': u'\u0043',
 'Caarmenian': u'\u053E',
 'Cacute': u'\u0106',
 'Caron': u'\uF6CA',
 'Caronsmall': u'\uF6F5',
 'Ccaron': u'\u010C',
 'Ccedilla': u'\u00C7',
 'Ccedillaacute': u'\u1E08',
 'Ccedillasmall': u'\uF7E7',
 'Ccircle': u'\u24B8',
 'Ccircumflex': u'\u0108',
 'Cdot': u'\u010A',
 'Cdotaccent': u'\u010A',
 'Cedillasmall': u'\uF7B8',
 'Chaarmenian': u'\u0549',
 'Cheabkhasiancyrillic': u'\u04BC',
 'Checyrillic': u'\u0427',
 'Chedescenderabkhasiancyrillic': u'\u04BE',
 'Chedescendercyrillic': u'\u04B6',
 'Chedieresiscyrillic': u'\u04F4',
 'Cheharmenian': u'\u0543',
 'Chekhakassiancyrillic': u'\u04CB',
 'Cheverticalstrokecyrillic': u'\u04B8',
 'Chi': u'\u03A7',
 'Chook': u'\u0187',
 'Circumflexsmall': u'\uF6F6',
 'Cmonospace': u'\uFF23',
 'Coarmenian': u'\u0551',
 'Csmall': u'\uF763',
 'D': u'\u0044',
 'DZ': u'\u01F1',
 'DZcaron': u'\u01C4',
 'Daarmenian': u'\u0534',
 'Dafrican': u'\u0189',
 'Dcaron': u'\u010E',
 'Dcedilla': u'\u1E10',
 'Dcircle': u'\u24B9',
 'Dcircumflexbelow': u'\u1E12',
 'Dcroat': u'\u0110',
 'Ddotaccent': u'\u1E0A',
 'Ddotbelow': u'\u1E0C',
 'Decyrillic': u'\u0414',
 'Deicoptic': u'\u03EE',
 'Delta': u'\u2206',
 'Deltagreek': u'\u0394',
 'Dhook': u'\u018A',
 'Dieresis': u'\uF6CB',
 'DieresisAcute': u'\uF6CC',
 'DieresisGrave': u'\uF6CD',
 'Dieresissmall': u'\uF7A8',
 'Digammagreek': u'\u03DC',
 'Djecyrillic': u'\u0402',
 'Dlinebelow': u'\u1E0E',
 'Dmonospace': u'\uFF24',
 'Dotaccentsmall': u'\uF6F7',
 'Dslash': u'\u0110',
 'Dsmall': u'\uF764',
 'Dtopbar': u'\u018B',
 'Dz': u'\u01F2',
 'Dzcaron': u'\u01C5',
 'Dzeabkhasiancyrillic': u'\u04E0',
 'Dzecyrillic': u'\u0405',
 'Dzhecyrillic': u'\u040F',
 'E': u'\u0045',
 'Eacute': u'\u00C9',
 'Eacutesmall': u'\uF7E9',
 'Ebreve': u'\u0114',
 'Ecaron': u'\u011A',
 'Ecedillabreve': u'\u1E1C',
 'Echarmenian': u'\u0535',
 'Ecircle': u'\u24BA',
 'Ecircumflex': u'\u00CA',
 'Ecircumflexacute': u'\u1EBE',
 'Ecircumflexbelow': u'\u1E18',
 'Ecircumflexdotbelow': u'\u1EC6',
 'Ecircumflexgrave': u'\u1EC0',
 'Ecircumflexhookabove': u'\u1EC2',
 'Ecircumflexsmall': u'\uF7EA',
 'Ecircumflextilde': u'\u1EC4',
 'Ecyrillic': u'\u0404',
 'Edblgrave': u'\u0204',
 'Edieresis': u'\u00CB',
 'Edieresissmall': u'\uF7EB',
 'Edot': u'\u0116',
 'Edotaccent': u'\u0116',
 'Edotbelow': u'\u1EB8',
 'Efcyrillic': u'\u0424',
 'Egrave': u'\u00C8',
 'Egravesmall': u'\uF7E8',
 'Eharmenian': u'\u0537',
 'Ehookabove': u'\u1EBA',
 'Eightroman': u'\u2167',
 'Einvertedbreve': u'\u0206',
 'Eiotifiedcyrillic': u'\u0464',
 'Elcyrillic': u'\u041B',
 'Elevenroman': u'\u216A',
 'Emacron': u'\u0112',
 'Emacronacute': u'\u1E16',
 'Emacrongrave': u'\u1E14',
 'Emcyrillic': u'\u041C',
 'Emonospace': u'\uFF25',
 'Encyrillic': u'\u041D',
 'Endescendercyrillic': u'\u04A2',
 'Eng': u'\u014A',
 'Enghecyrillic': u'\u04A4',
 'Enhookcyrillic': u'\u04C7',
 'Eogonek': u'\u0118',
 'Eopen': u'\u0190',
 'Epsilon': u'\u0395',
 'Epsilontonos': u'\u0388',
 'Ercyrillic': u'\u0420',
 'Ereversed': u'\u018E',
 'Ereversedcyrillic': u'\u042D',
 'Escyrillic': u'\u0421',
 'Esdescendercyrillic': u'\u04AA',
 'Esh': u'\u01A9',
 'Esmall': u'\uF765',
 'Eta': u'\u0397',
 'Etarmenian': u'\u0538',
 'Etatonos': u'\u0389',
 'Eth': u'\u00D0',
 'Ethsmall': u'\uF7F0',
 'Etilde': u'\u1EBC',
 'Etildebelow': u'\u1E1A',
 'Euro': u'\u20AC',
 'Ezh': u'\u01B7',
 'Ezhcaron': u'\u01EE',
 'Ezhreversed': u'\u01B8',
 'F': u'\u0046',
 'Fcircle': u'\u24BB',
 'Fdotaccent': u'\u1E1E',
 'Feharmenian': u'\u0556',
 'Feicoptic': u'\u03E4',
 'Fhook': u'\u0191',
 'Fitacyrillic': u'\u0472',
 'Fiveroman': u'\u2164',
 'Fmonospace': u'\uFF26',
 'Fourroman': u'\u2163',
 'Fsmall': u'\uF766',
 'G': u'\u0047',
 'GBsquare': u'\u3387',
 'Gacute': u'\u01F4',
 'Gamma': u'\u0393',
 'Gammaafrican': u'\u0194',
 'Gangiacoptic': u'\u03EA',
 'Gbreve': u'\u011E',
 'Gcaron': u'\u01E6',
 'Gcedilla': u'\u0122',
 'Gcircle': u'\u24BC',
 'Gcircumflex': u'\u011C',
 'Gcommaaccent': u'\u0122',
 'Gdot': u'\u0120',
 'Gdotaccent': u'\u0120',
 'Gecyrillic': u'\u0413',
 'Ghadarmenian': u'\u0542',
 'Ghemiddlehookcyrillic': u'\u0494',
 'Ghestrokecyrillic': u'\u0492',
 'Gheupturncyrillic': u'\u0490',
 'Ghook': u'\u0193',
 'Gimarmenian': u'\u0533',
 'Gjecyrillic': u'\u0403',
 'Gmacron': u'\u1E20',
 'Gmonospace': u'\uFF27',
 'Grave': u'\uF6CE',
 'Gravesmall': u'\uF760',
 'Gsmall': u'\uF767',
 'Gsmallhook': u'\u029B',
 'Gstroke': u'\u01E4',
 'H': u'\u0048',
 'H18533': u'\u25CF',
 'H18543': u'\u25AA',
 'H18551': u'\u25AB',
 'H22073': u'\u25A1',
 'HPsquare': u'\u33CB',
 'Haabkhasiancyrillic': u'\u04A8',
 'Hadescendercyrillic': u'\u04B2',
 'Hardsigncyrillic': u'\u042A',
 'Hbar': u'\u0126',
 'Hbrevebelow': u'\u1E2A',
 'Hcedilla': u'\u1E28',
 'Hcircle': u'\u24BD',
 'Hcircumflex': u'\u0124',
 'Hdieresis': u'\u1E26',
 'Hdotaccent': u'\u1E22',
 'Hdotbelow': u'\u1E24',
 'Hmonospace': u'\uFF28',
 'Hoarmenian': u'\u0540',
 'Horicoptic': u'\u03E8',
 'Hsmall': u'\uF768',
 'Hungarumlaut': u'\uF6CF',
 'Hungarumlautsmall': u'\uF6F8',
 'Hzsquare': u'\u3390',
 'I': u'\u0049',
 'IAcyrillic': u'\u042F',
 'IJ': u'\u0132',
 'IUcyrillic': u'\u042E',
 'Iacute': u'\u00CD',
 'Iacutesmall': u'\uF7ED',
 'Ibreve': u'\u012C',
 'Icaron': u'\u01CF',
 'Icircle': u'\u24BE',
 'Icircumflex': u'\u00CE',
 'Icircumflexsmall': u'\uF7EE',
 'Icyrillic': u'\u0406',
 'Idblgrave': u'\u0208',
 'Idieresis': u'\u00CF',
 'Idieresisacute': u'\u1E2E',
 'Idieresiscyrillic': u'\u04E4',
 'Idieresissmall': u'\uF7EF',
 'Idot': u'\u0130',
 'Idotaccent': u'\u0130',
 'Idotbelow': u'\u1ECA',
 'Iebrevecyrillic': u'\u04D6',
 'Iecyrillic': u'\u0415',
 'Ifraktur': u'\u2111',
 'Igrave': u'\u00CC',
 'Igravesmall': u'\uF7EC',
 'Ihookabove': u'\u1EC8',
 'Iicyrillic': u'\u0418',
 'Iinvertedbreve': u'\u020A',
 'Iishortcyrillic': u'\u0419',
 'Imacron': u'\u012A',
 'Imacroncyrillic': u'\u04E2',
 'Imonospace': u'\uFF29',
 'Iniarmenian': u'\u053B',
 'Iocyrillic': u'\u0401',
 'Iogonek': u'\u012E',
 'Iota': u'\u0399',
 'Iotaafrican': u'\u0196',
 'Iotadieresis': u'\u03AA',
 'Iotatonos': u'\u038A',
 'Ismall': u'\uF769',
 'Istroke': u'\u0197',
 'Itilde': u'\u0128',
 'Itildebelow': u'\u1E2C',
 'Izhitsacyrillic': u'\u0474',
 'Izhitsadblgravecyrillic': u'\u0476',
 'J': u'\u004A',
 'Jaarmenian': u'\u0541',
 'Jcircle': u'\u24BF',
 'Jcircumflex': u'\u0134',
 'Jecyrillic': u'\u0408',
 'Jheharmenian': u'\u054B',
 'Jmonospace': u'\uFF2A',
 'Jsmall': u'\uF76A',
 'K': u'\u004B',
 'KBsquare': u'\u3385',
 'KKsquare': u'\u33CD',
 'Kabashkircyrillic': u'\u04A0',
 'Kacute': u'\u1E30',
 'Kacyrillic': u'\u041A',
 'Kadescendercyrillic': u'\u049A',
 'Kahookcyrillic': u'\u04C3',
 'Kappa': u'\u039A',
 'Kastrokecyrillic': u'\u049E',
 'Kaverticalstrokecyrillic': u'\u049C',
 'Kcaron': u'\u01E8',
 'Kcedilla': u'\u0136',
 'Kcircle': u'\u24C0',
 'Kcommaaccent': u'\u0136',
 'Kdotbelow': u'\u1E32',
 'Keharmenian': u'\u0554',
 'Kenarmenian': u'\u053F',
 'Khacyrillic': u'\u0425',
 'Kheicoptic': u'\u03E6',
 'Khook': u'\u0198',
 'Kjecyrillic': u'\u040C',
 'Klinebelow': u'\u1E34',
 'Kmonospace': u'\uFF2B',
 'Koppacyrillic': u'\u0480',
 'Koppagreek': u'\u03DE',
 'Ksicyrillic': u'\u046E',
 'Ksmall': u'\uF76B',
 'L': u'\u004C',
 'LJ': u'\u01C7',
 'LL': u'\uF6BF',
 'Lacute': u'\u0139',
 'Lambda': u'\u039B',
 'Lcaron': u'\u013D',
 'Lcedilla': u'\u013B',
 'Lcircle': u'\u24C1',
 'Lcircumflexbelow': u'\u1E3C',
 'Lcommaaccent': u'\u013B',
 'Ldot': u'\u013F',
 'Ldotaccent': u'\u013F',
 'Ldotbelow': u'\u1E36',
 'Ldotbelowmacron': u'\u1E38',
 'Liwnarmenian': u'\u053C',
 'Lj': u'\u01C8',
 'Ljecyrillic': u'\u0409',
 'Llinebelow': u'\u1E3A',
 'Lmonospace': u'\uFF2C',
 'Lslash': u'\u0141',
 'Lslashsmall': u'\uF6F9',
 'Lsmall': u'\uF76C',
 'M': u'\u004D',
 'MBsquare': u'\u3386',
 'Macron': u'\uF6D0',
 'Macronsmall': u'\uF7AF',
 'Macute': u'\u1E3E',
 'Mcircle': u'\u24C2',
 'Mdotaccent': u'\u1E40',
 'Mdotbelow': u'\u1E42',
 'Menarmenian': u'\u0544',
 'Mmonospace': u'\uFF2D',
 'Msmall': u'\uF76D',
 'Mturned': u'\u019C',
 'Mu': u'\u039C',
 'N': u'\u004E',
 'NJ': u'\u01CA',
 'Nacute': u'\u0143',
 'Ncaron': u'\u0147',
 'Ncedilla': u'\u0145',
 'Ncircle': u'\u24C3',
 'Ncircumflexbelow': u'\u1E4A',
 'Ncommaaccent': u'\u0145',
 'Ndotaccent': u'\u1E44',
 'Ndotbelow': u'\u1E46',
 'Nhookleft': u'\u019D',
 'Nineroman': u'\u2168',
 'Nj': u'\u01CB',
 'Njecyrillic': u'\u040A',
 'Nlinebelow': u'\u1E48',
 'Nmonospace': u'\uFF2E',
 'Nowarmenian': u'\u0546',
 'Nsmall': u'\uF76E',
 'Ntilde': u'\u00D1',
 'Ntildesmall': u'\uF7F1',
 'Nu': u'\u039D',
 'O': u'\u004F',
 'OE': u'\u0152',
 'OEsmall': u'\uF6FA',
 'Oacute': u'\u00D3',
 'Oacutesmall': u'\uF7F3',
 'Obarredcyrillic': u'\u04E8',
 'Obarreddieresiscyrillic': u'\u04EA',
 'Obreve': u'\u014E',
 'Ocaron': u'\u01D1',
 'Ocenteredtilde': u'\u019F',
 'Ocircle': u'\u24C4',
 'Ocircumflex': u'\u00D4',
 'Ocircumflexacute': u'\u1ED0',
 'Ocircumflexdotbelow': u'\u1ED8',
 'Ocircumflexgrave': u'\u1ED2',
 'Ocircumflexhookabove': u'\u1ED4',
 'Ocircumflexsmall': u'\uF7F4',
 'Ocircumflextilde': u'\u1ED6',
 'Ocyrillic': u'\u041E',
 'Odblacute': u'\u0150',
 'Odblgrave': u'\u020C',
 'Odieresis': u'\u00D6',
 'Odieresiscyrillic': u'\u04E6',
 'Odieresissmall': u'\uF7F6',
 'Odotbelow': u'\u1ECC',
 'Ogoneksmall': u'\uF6FB',
 'Ograve': u'\u00D2',
 'Ogravesmall': u'\uF7F2',
 'Oharmenian': u'\u0555',
 'Ohm': u'\u2126',
 'Ohookabove': u'\u1ECE',
 'Ohorn': u'\u01A0',
 'Ohornacute': u'\u1EDA',
 'Ohorndotbelow': u'\u1EE2',
 'Ohorngrave': u'\u1EDC',
 'Ohornhookabove': u'\u1EDE',
 'Ohorntilde': u'\u1EE0',
 'Ohungarumlaut': u'\u0150',
 'Oi': u'\u01A2',
 'Oinvertedbreve': u'\u020E',
 'Omacron': u'\u014C',
 'Omacronacute': u'\u1E52',
 'Omacrongrave': u'\u1E50',
 'Omega': u'\u2126',
 'Omegacyrillic': u'\u0460',
 'Omegagreek': u'\u03A9',
 'Omegaroundcyrillic': u'\u047A',
 'Omegatitlocyrillic': u'\u047C',
 'Omegatonos': u'\u038F',
 'Omicron': u'\u039F',
 'Omicrontonos': u'\u038C',
 'Omonospace': u'\uFF2F',
 'Oneroman': u'\u2160',
 'Oogonek': u'\u01EA',
 'Oogonekmacron': u'\u01EC',
 'Oopen': u'\u0186',
 'Oslash': u'\u00D8',
 'Oslashacute': u'\u01FE',
 'Oslashsmall': u'\uF7F8',
 'Osmall': u'\uF76F',
 'Ostrokeacute': u'\u01FE',
 'Otcyrillic': u'\u047E',
 'Otilde': u'\u00D5',
 'Otildeacute': u'\u1E4C',
 'Otildedieresis': u'\u1E4E',
 'Otildesmall': u'\uF7F5',
 'P': u'\u0050',
 'Pacute': u'\u1E54',
 'Pcircle': u'\u24C5',
 'Pdotaccent': u'\u1E56',
 'Pecyrillic': u'\u041F',
 'Peharmenian': u'\u054A',
 'Pemiddlehookcyrillic': u'\u04A6',
 'Phi': u'\u03A6',
 'Phook': u'\u01A4',
 'Pi': u'\u03A0',
 'Piwrarmenian': u'\u0553',
 'Pmonospace': u'\uFF30',
 'Psi': u'\u03A8',
 'Psicyrillic': u'\u0470',
 'Psmall': u'\uF770',
 'Q': u'\u0051',
 'Qcircle': u'\u24C6',
 'Qmonospace': u'\uFF31',
 'Qsmall': u'\uF771',
 'R': u'\u0052',
 'Raarmenian': u'\u054C',
 'Racute': u'\u0154',
 'Rcaron': u'\u0158',
 'Rcedilla': u'\u0156',
 'Rcircle': u'\u24C7',
 'Rcommaaccent': u'\u0156',
 'Rdblgrave': u'\u0210',
 'Rdotaccent': u'\u1E58',
 'Rdotbelow': u'\u1E5A',
 'Rdotbelowmacron': u'\u1E5C',
 'Reharmenian': u'\u0550',
 'Rfraktur': u'\u211C',
 'Rho': u'\u03A1',
 'Ringsmall': u'\uF6FC',
 'Rinvertedbreve': u'\u0212',
 'Rlinebelow': u'\u1E5E',
 'Rmonospace': u'\uFF32',
 'Rsmall': u'\uF772',
 'Rsmallinverted': u'\u0281',
 'Rsmallinvertedsuperior': u'\u02B6',
 'S': u'\u0053',
 'SF010000': u'\u250C',
 'SF020000': u'\u2514',
 'SF030000': u'\u2510',
 'SF040000': u'\u2518',
 'SF050000': u'\u253C',
 'SF060000': u'\u252C',
 'SF070000': u'\u2534',
 'SF080000': u'\u251C',
 'SF090000': u'\u2524',
 'SF100000': u'\u2500',
 'SF110000': u'\u2502',
 'SF190000': u'\u2561',
 'SF200000': u'\u2562',
 'SF210000': u'\u2556',
 'SF220000': u'\u2555',
 'SF230000': u'\u2563',
 'SF240000': u'\u2551',
 'SF250000': u'\u2557',
 'SF260000': u'\u255D',
 'SF270000': u'\u255C',
 'SF280000': u'\u255B',
 'SF360000': u'\u255E',
 'SF370000': u'\u255F',
 'SF380000': u'\u255A',
 'SF390000': u'\u2554',
 'SF400000': u'\u2569',
 'SF410000': u'\u2566',
 'SF420000': u'\u2560',
 'SF430000': u'\u2550',
 'SF440000': u'\u256C',
 'SF450000': u'\u2567',
 'SF460000': u'\u2568',
 'SF470000': u'\u2564',
 'SF480000': u'\u2565',
 'SF490000': u'\u2559',
 'SF500000': u'\u2558',
 'SF510000': u'\u2552',
 'SF520000': u'\u2553',
 'SF530000': u'\u256B',
 'SF540000': u'\u256A',
 'Sacute': u'\u015A',
 'Sacutedotaccent': u'\u1E64',
 'Sampigreek': u'\u03E0',
 'Scaron': u'\u0160',
 'Scarondotaccent': u'\u1E66',
 'Scaronsmall': u'\uF6FD',
 'Scedilla': u'\u015E',
 'Schwa': u'\u018F',
 'Schwacyrillic': u'\u04D8',
 'Schwadieresiscyrillic': u'\u04DA',
 'Scircle': u'\u24C8',
 'Scircumflex': u'\u015C',
 'Scommaaccent': u'\u0218',
 'Sdotaccent': u'\u1E60',
 'Sdotbelow': u'\u1E62',
 'Sdotbelowdotaccent': u'\u1E68',
 'Seharmenian': u'\u054D',
 'Sevenroman': u'\u2166',
 'Shaarmenian': u'\u0547',
 'Shacyrillic': u'\u0428',
 'Shchacyrillic': u'\u0429',
 'Sheicoptic': u'\u03E2',
 'Shhacyrillic': u'\u04BA',
 'Shimacoptic': u'\u03EC',
 'Sigma': u'\u03A3',
 'Sixroman': u'\u2165',
 'Smonospace': u'\uFF33',
 'Softsigncyrillic': u'\u042C',
 'Ssmall': u'\uF773',
 'Stigmagreek': u'\u03DA',
 'T': u'\u0054',
 'Tau': u'\u03A4',
 'Tbar': u'\u0166',
 'Tcaron': u'\u0164',
 'Tcedilla': u'\u0162',
 'Tcircle': u'\u24C9',
 'Tcircumflexbelow': u'\u1E70',
 'Tcommaaccent': u'\u0162',
 'Tdotaccent': u'\u1E6A',
 'Tdotbelow': u'\u1E6C',
 'Tecyrillic': u'\u0422',
 'Tedescendercyrillic': u'\u04AC',
 'Tenroman': u'\u2169',
 'Tetsecyrillic': u'\u04B4',
 'Theta': u'\u0398',
 'Thook': u'\u01AC',
 'Thorn': u'\u00DE',
 'Thornsmall': u'\uF7FE',
 'Threeroman': u'\u2162',
 'Tildesmall': u'\uF6FE',
 'Tiwnarmenian': u'\u054F',
 'Tlinebelow': u'\u1E6E',
 'Tmonospace': u'\uFF34',
 'Toarmenian': u'\u0539',
 'Tonefive': u'\u01BC',
 'Tonesix': u'\u0184',
 'Tonetwo': u'\u01A7',
 'Tretroflexhook': u'\u01AE',
 'Tsecyrillic': u'\u0426',
 'Tshecyrillic': u'\u040B',
 'Tsmall': u'\uF774',
 'Twelveroman': u'\u216B',
 'Tworoman': u'\u2161',
 'U': u'\u0055',
 'Uacute': u'\u00DA',
 'Uacutesmall': u'\uF7FA',
 'Ubreve': u'\u016C',
 'Ucaron': u'\u01D3',
 'Ucircle': u'\u24CA',
 'Ucircumflex': u'\u00DB',
 'Ucircumflexbelow': u'\u1E76',
 'Ucircumflexsmall': u'\uF7FB',
 'Ucyrillic': u'\u0423',
 'Udblacute': u'\u0170',
 'Udblgrave': u'\u0214',
 'Udieresis': u'\u00DC',
 'Udieresisacute': u'\u01D7',
 'Udieresisbelow': u'\u1E72',
 'Udieresiscaron': u'\u01D9',
 'Udieresiscyrillic': u'\u04F0',
 'Udieresisgrave': u'\u01DB',
 'Udieresismacron': u'\u01D5',
 'Udieresissmall': u'\uF7FC',
 'Udotbelow': u'\u1EE4',
 'Ugrave': u'\u00D9',
 'Ugravesmall': u'\uF7F9',
 'Uhookabove': u'\u1EE6',
 'Uhorn': u'\u01AF',
 'Uhornacute': u'\u1EE8',
 'Uhorndotbelow': u'\u1EF0',
 'Uhorngrave': u'\u1EEA',
 'Uhornhookabove': u'\u1EEC',
 'Uhorntilde': u'\u1EEE',
 'Uhungarumlaut': u'\u0170',
 'Uhungarumlautcyrillic': u'\u04F2',
 'Uinvertedbreve': u'\u0216',
 'Ukcyrillic': u'\u0478',
 'Umacron': u'\u016A',
 'Umacroncyrillic': u'\u04EE',
 'Umacrondieresis': u'\u1E7A',
 'Umonospace': u'\uFF35',
 'Uogonek': u'\u0172',
 'Upsilon': u'\u03A5',
 'Upsilon1': u'\u03D2',
 'Upsilonacutehooksymbolgreek': u'\u03D3',
 'Upsilonafrican': u'\u01B1',
 'Upsilondieresis': u'\u03AB',
 'Upsilondieresishooksymbolgreek': u'\u03D4',
 'Upsilonhooksymbol': u'\u03D2',
 'Upsilontonos': u'\u038E',
 'Uring': u'\u016E',
 'Ushortcyrillic': u'\u040E',
 'Usmall': u'\uF775',
 'Ustraightcyrillic': u'\u04AE',
 'Ustraightstrokecyrillic': u'\u04B0',
 'Utilde': u'\u0168',
 'Utildeacute': u'\u1E78',
 'Utildebelow': u'\u1E74',
 'V': u'\u0056',
 'Vcircle': u'\u24CB',
 'Vdotbelow': u'\u1E7E',
 'Vecyrillic': u'\u0412',
 'Vewarmenian': u'\u054E',
 'Vhook': u'\u01B2',
 'Vmonospace': u'\uFF36',
 'Voarmenian': u'\u0548',
 'Vsmall': u'\uF776',
 'Vtilde': u'\u1E7C',
 'W': u'\u0057',
 'Wacute': u'\u1E82',
 'Wcircle': u'\u24CC',
 'Wcircumflex': u'\u0174',
 'Wdieresis': u'\u1E84',
 'Wdotaccent': u'\u1E86',
 'Wdotbelow': u'\u1E88',
 'Wgrave': u'\u1E80',
 'Wmonospace': u'\uFF37',
 'Wsmall': u'\uF777',
 'X': u'\u0058',
 'Xcircle': u'\u24CD',
 'Xdieresis': u'\u1E8C',
 'Xdotaccent': u'\u1E8A',
 'Xeharmenian': u'\u053D',
 'Xi': u'\u039E',
 'Xmonospace': u'\uFF38',
 'Xsmall': u'\uF778',
 'Y': u'\u0059',
 'Yacute': u'\u00DD',
 'Yacutesmall': u'\uF7FD',
 'Yatcyrillic': u'\u0462',
 'Ycircle': u'\u24CE',
 'Ycircumflex': u'\u0176',
 'Ydieresis': u'\u0178',
 'Ydieresissmall': u'\uF7FF',
 'Ydotaccent': u'\u1E8E',
 'Ydotbelow': u'\u1EF4',
 'Yericyrillic': u'\u042B',
 'Yerudieresiscyrillic': u'\u04F8',
 'Ygrave': u'\u1EF2',
 'Yhook': u'\u01B3',
 'Yhookabove': u'\u1EF6',
 'Yiarmenian': u'\u0545',
 'Yicyrillic': u'\u0407',
 'Yiwnarmenian': u'\u0552',
 'Ymonospace': u'\uFF39',
 'Ysmall': u'\uF779',
 'Ytilde': u'\u1EF8',
 'Yusbigcyrillic': u'\u046A',
 'Yusbigiotifiedcyrillic': u'\u046C',
 'Yuslittlecyrillic': u'\u0466',
 'Yuslittleiotifiedcyrillic': u'\u0468',
 'Z': u'\u005A',
 'Zaarmenian': u'\u0536',
 'Zacute': u'\u0179',
 'Zcaron': u'\u017D',
 'Zcaronsmall': u'\uF6FF',
 'Zcircle': u'\u24CF',
 'Zcircumflex': u'\u1E90',
 'Zdot': u'\u017B',
 'Zdotaccent': u'\u017B',
 'Zdotbelow': u'\u1E92',
 'Zecyrillic': u'\u0417',
 'Zedescendercyrillic': u'\u0498',
 'Zedieresiscyrillic': u'\u04DE',
 'Zeta': u'\u0396',
 'Zhearmenian': u'\u053A',
 'Zhebrevecyrillic': u'\u04C1',
 'Zhecyrillic': u'\u0416',
 'Zhedescendercyrillic': u'\u0496',
 'Zhedieresiscyrillic': u'\u04DC',
 'Zlinebelow': u'\u1E94',
 'Zmonospace': u'\uFF3A',
 'Zsmall': u'\uF77A',
 'Zstroke': u'\u01B5',
 'a': u'\u0061',
 'aabengali': u'\u0986',
 'aacute': u'\u00E1',
 'aadeva': u'\u0906',
 'aagujarati': u'\u0A86',
 'aagurmukhi': u'\u0A06',
 'aamatragurmukhi': u'\u0A3E',
 'aarusquare': u'\u3303',
 'aavowelsignbengali': u'\u09BE',
 'aavowelsigndeva': u'\u093E',
 'aavowelsigngujarati': u'\u0ABE',
 'abbreviationmarkarmenian': u'\u055F',
 'abbreviationsigndeva': u'\u0970',
 'abengali': u'\u0985',
 'abopomofo': u'\u311A',
 'abreve': u'\u0103',
 'abreveacute': u'\u1EAF',
 'abrevecyrillic': u'\u04D1',
 'abrevedotbelow': u'\u1EB7',
 'abrevegrave': u'\u1EB1',
 'abrevehookabove': u'\u1EB3',
 'abrevetilde': u'\u1EB5',
 'acaron': u'\u01CE',
 'acircle': u'\u24D0',
 'acircumflex': u'\u00E2',
 'acircumflexacute': u'\u1EA5',
 'acircumflexdotbelow': u'\u1EAD',
 'acircumflexgrave': u'\u1EA7',
 'acircumflexhookabove': u'\u1EA9',
 'acircumflextilde': u'\u1EAB',
 'acute': u'\u00B4',
 'acutebelowcmb': u'\u0317',
 'acutecmb': u'\u0301',
 'acutecomb': u'\u0301',
 'acutedeva': u'\u0954',
 'acutelowmod': u'\u02CF',
 'acutetonecmb': u'\u0341',
 'acyrillic': u'\u0430',
 'adblgrave': u'\u0201',
 'addakgurmukhi': u'\u0A71',
 'adeva': u'\u0905',
 'adieresis': u'\u00E4',
 'adieresiscyrillic': u'\u04D3',
 'adieresismacron': u'\u01DF',
 'adotbelow': u'\u1EA1',
 'adotmacron': u'\u01E1',
 'ae': u'\u00E6',
 'aeacute': u'\u01FD',
 'aekorean': u'\u3150',
 'aemacron': u'\u01E3',
 'afii00208': u'\u2015',
 'afii08941': u'\u20A4',
 'afii10017': u'\u0410',
 'afii10018': u'\u0411',
 'afii10019': u'\u0412',
 'afii10020': u'\u0413',
 'afii10021': u'\u0414',
 'afii10022': u'\u0415',
 'afii10023': u'\u0401',
 'afii10024': u'\u0416',
 'afii10025': u'\u0417',
 'afii10026': u'\u0418',
 'afii10027': u'\u0419',
 'afii10028': u'\u041A',
 'afii10029': u'\u041B',
 'afii10030': u'\u041C',
 'afii10031': u'\u041D',
 'afii10032': u'\u041E',
 'afii10033': u'\u041F',
 'afii10034': u'\u0420',
 'afii10035': u'\u0421',
 'afii10036': u'\u0422',
 'afii10037': u'\u0423',
 'afii10038': u'\u0424',
 'afii10039': u'\u0425',
 'afii10040': u'\u0426',
 'afii10041': u'\u0427',
 'afii10042': u'\u0428',
 'afii10043': u'\u0429',
 'afii10044': u'\u042A',
 'afii10045': u'\u042B',
 'afii10046': u'\u042C',
 'afii10047': u'\u042D',
 'afii10048': u'\u042E',
 'afii10049': u'\u042F',
 'afii10050': u'\u0490',
 'afii10051': u'\u0402',
 'afii10052': u'\u0403',
 'afii10053': u'\u0404',
 'afii10054': u'\u0405',
 'afii10055': u'\u0406',
 'afii10056': u'\u0407',
 'afii10057': u'\u0408',
 'afii10058': u'\u0409',
 'afii10059': u'\u040A',
 'afii10060': u'\u040B',
 'afii10061': u'\u040C',
 'afii10062': u'\u040E',
 'afii10063': u'\uF6C4',
 'afii10064': u'\uF6C5',
 'afii10065': u'\u0430',
 'afii10066': u'\u0431',
 'afii10067': u'\u0432',
 'afii10068': u'\u0433',
 'afii10069': u'\u0434',
 'afii10070': u'\u0435',
 'afii10071': u'\u0451',
 'afii10072': u'\u0436',
 'afii10073': u'\u0437',
 'afii10074': u'\u0438',
 'afii10075': u'\u0439',
 'afii10076': u'\u043A',
 'afii10077': u'\u043B',
 'afii10078': u'\u043C',
 'afii10079': u'\u043D',
 'afii10080': u'\u043E',
 'afii10081': u'\u043F',
 'afii10082': u'\u0440',
 'afii10083': u'\u0441',
 'afii10084': u'\u0442',
 'afii10085': u'\u0443',
 'afii10086': u'\u0444',
 'afii10087': u'\u0445',
 'afii10088': u'\u0446',
 'afii10089': u'\u0447',
 'afii10090': u'\u0448',
 'afii10091': u'\u0449',
 'afii10092': u'\u044A',
 'afii10093': u'\u044B',
 'afii10094': u'\u044C',
 'afii10095': u'\u044D',
 'afii10096': u'\u044E',
 'afii10097': u'\u044F',
 'afii10098': u'\u0491',
 'afii10099': u'\u0452',
 'afii10100': u'\u0453',
 'afii10101': u'\u0454',
 'afii10102': u'\u0455',
 'afii10103': u'\u0456',
 'afii10104': u'\u0457',
 'afii10105': u'\u0458',
 'afii10106': u'\u0459',
 'afii10107': u'\u045A',
 'afii10108': u'\u045B',
 'afii10109': u'\u045C',
 'afii10110': u'\u045E',
 'afii10145': u'\u040F',
 'afii10146': u'\u0462',
 'afii10147': u'\u0472',
 'afii10148': u'\u0474',
 'afii10192': u'\uF6C6',
 'afii10193': u'\u045F',
 'afii10194': u'\u0463',
 'afii10195': u'\u0473',
 'afii10196': u'\u0475',
 'afii10831': u'\uF6C7',
 'afii10832': u'\uF6C8',
 'afii10846': u'\u04D9',
 'afii299': u'\u200E',
 'afii300': u'\u200F',
 'afii301': u'\u200D',
 'afii57381': u'\u066A',
 'afii57388': u'\u060C',
 'afii57392': u'\u0660',
 'afii57393': u'\u0661',
 'afii57394': u'\u0662',
 'afii57395': u'\u0663',
 'afii57396': u'\u0664',
 'afii57397': u'\u0665',
 'afii57398': u'\u0666',
 'afii57399': u'\u0667',
 'afii57400': u'\u0668',
 'afii57401': u'\u0669',
 'afii57403': u'\u061B',
 'afii57407': u'\u061F',
 'afii57409': u'\u0621',
 'afii57410': u'\u0622',
 'afii57411': u'\u0623',
 'afii57412': u'\u0624',
 'afii57413': u'\u0625',
 'afii57414': u'\u0626',
 'afii57415': u'\u0627',
 'afii57416': u'\u0628',
 'afii57417': u'\u0629',
 'afii57418': u'\u062A',
 'afii57419': u'\u062B',
 'afii57420': u'\u062C',
 'afii57421': u'\u062D',
 'afii57422': u'\u062E',
 'afii57423': u'\u062F',
 'afii57424': u'\u0630',
 'afii57425': u'\u0631',
 'afii57426': u'\u0632',
 'afii57427': u'\u0633',
 'afii57428': u'\u0634',
 'afii57429': u'\u0635',
 'afii57430': u'\u0636',
 'afii57431': u'\u0637',
 'afii57432': u'\u0638',
 'afii57433': u'\u0639',
 'afii57434': u'\u063A',
 'afii57440': u'\u0640',
 'afii57441': u'\u0641',
 'afii57442': u'\u0642',
 'afii57443': u'\u0643',
 'afii57444': u'\u0644',
 'afii57445': u'\u0645',
 'afii57446': u'\u0646',
 'afii57448': u'\u0648',
 'afii57449': u'\u0649',
 'afii57450': u'\u064A',
 'afii57451': u'\u064B',
 'afii57452': u'\u064C',
 'afii57453': u'\u064D',
 'afii57454': u'\u064E',
 'afii57455': u'\u064F',
 'afii57456': u'\u0650',
 'afii57457': u'\u0651',
 'afii57458': u'\u0652',
 'afii57470': u'\u0647',
 'afii57505': u'\u06A4',
 'afii57506': u'\u067E',
 'afii57507': u'\u0686',
 'afii57508': u'\u0698',
 'afii57509': u'\u06AF',
 'afii57511': u'\u0679',
 'afii57512': u'\u0688',
 'afii57513': u'\u0691',
 'afii57514': u'\u06BA',
 'afii57519': u'\u06D2',
 'afii57534': u'\u06D5',
 'afii57636': u'\u20AA',
 'afii57645': u'\u05BE',
 'afii57658': u'\u05C3',
 'afii57664': u'\u05D0',
 'afii57665': u'\u05D1',
 'afii57666': u'\u05D2',
 'afii57667': u'\u05D3',
 'afii57668': u'\u05D4',
 'afii57669': u'\u05D5',
 'afii57670': u'\u05D6',
 'afii57671': u'\u05D7',
 'afii57672': u'\u05D8',
 'afii57673': u'\u05D9',
 'afii57674': u'\u05DA',
 'afii57675': u'\u05DB',
 'afii57676': u'\u05DC',
 'afii57677': u'\u05DD',
 'afii57678': u'\u05DE',
 'afii57679': u'\u05DF',
 'afii57680': u'\u05E0',
 'afii57681': u'\u05E1',
 'afii57682': u'\u05E2',
 'afii57683': u'\u05E3',
 'afii57684': u'\u05E4',
 'afii57685': u'\u05E5',
 'afii57686': u'\u05E6',
 'afii57687': u'\u05E7',
 'afii57688': u'\u05E8',
 'afii57689': u'\u05E9',
 'afii57690': u'\u05EA',
 'afii57694': u'\uFB2A',
 'afii57695': u'\uFB2B',
 'afii57700': u'\uFB4B',
 'afii57705': u'\uFB1F',
 'afii57716': u'\u05F0',
 'afii57717': u'\u05F1',
 'afii57718': u'\u05F2',
 'afii57723': u'\uFB35',
 'afii57793': u'\u05B4',
 'afii57794': u'\u05B5',
 'afii57795': u'\u05B6',
 'afii57796': u'\u05BB',
 'afii57797': u'\u05B8',
 'afii57798': u'\u05B7',
 'afii57799': u'\u05B0',
 'afii57800': u'\u05B2',
 'afii57801': u'\u05B1',
 'afii57802': u'\u05B3',
 'afii57803': u'\u05C2',
 'afii57804': u'\u05C1',
 'afii57806': u'\u05B9',
 'afii57807': u'\u05BC',
 'afii57839': u'\u05BD',
 'afii57841': u'\u05BF',
 'afii57842': u'\u05C0',
 'afii57929': u'\u02BC',
 'afii61248': u'\u2105',
 'afii61289': u'\u2113',
 'afii61352': u'\u2116',
 'afii61573': u'\u202C',
 'afii61574': u'\u202D',
 'afii61575': u'\u202E',
 'afii61664': u'\u200C',
 'afii63167': u'\u066D',
 'afii64937': u'\u02BD',
 'agrave': u'\u00E0',
 'agujarati': u'\u0A85',
 'agurmukhi': u'\u0A05',
 'ahiragana': u'\u3042',
 'ahookabove': u'\u1EA3',
 'aibengali': u'\u0990',
 'aibopomofo': u'\u311E',
 'aideva': u'\u0910',
 'aiecyrillic': u'\u04D5',
 'aigujarati': u'\u0A90',
 'aigurmukhi': u'\u0A10',
 'aimatragurmukhi': u'\u0A48',
 'ainarabic': u'\u0639',
 'ainfinalarabic': u'\uFECA',
 'aininitialarabic': u'\uFECB',
 'ainmedialarabic': u'\uFECC',
 'ainvertedbreve': u'\u0203',
 'aivowelsignbengali': u'\u09C8',
 'aivowelsigndeva': u'\u0948',
 'aivowelsigngujarati': u'\u0AC8',
 'akatakana': u'\u30A2',
 'akatakanahalfwidth': u'\uFF71',
 'akorean': u'\u314F',
 'alef': u'\u05D0',
 'alefarabic': u'\u0627',
 'alefdageshhebrew': u'\uFB30',
 'aleffinalarabic': u'\uFE8E',
 'alefhamzaabovearabic': u'\u0623',
 'alefhamzaabovefinalarabic': u'\uFE84',
 'alefhamzabelowarabic': u'\u0625',
 'alefhamzabelowfinalarabic': u'\uFE88',
 'alefhebrew': u'\u05D0',
 'aleflamedhebrew': u'\uFB4F',
 'alefmaddaabovearabic': u'\u0622',
 'alefmaddaabovefinalarabic': u'\uFE82',
 'alefmaksuraarabic': u'\u0649',
 'alefmaksurafinalarabic': u'\uFEF0',
 'alefmaksurainitialarabic': u'\uFEF3',
 'alefmaksuramedialarabic': u'\uFEF4',
 'alefpatahhebrew': u'\uFB2E',
 'alefqamatshebrew': u'\uFB2F',
 'aleph': u'\u2135',
 'allequal': u'\u224C',
 'alpha': u'\u03B1',
 'alphatonos': u'\u03AC',
 'amacron': u'\u0101',
 'amonospace': u'\uFF41',
 'ampersand': u'\u0026',
 'ampersandmonospace': u'\uFF06',
 'ampersandsmall': u'\uF726',
 'amsquare': u'\u33C2',
 'anbopomofo': u'\u3122',
 'angbopomofo': u'\u3124',
 'angkhankhuthai': u'\u0E5A',
 'angle': u'\u2220',
 'anglebracketleft': u'\u3008',
 'anglebracketleftvertical': u'\uFE3F',
 'anglebracketright': u'\u3009',
 'anglebracketrightvertical': u'\uFE40',
 'angleleft': u'\u2329',
 'angleright': u'\u232A',
 'angstrom': u'\u212B',
 'anoteleia': u'\u0387',
 'anudattadeva': u'\u0952',
 'anusvarabengali': u'\u0982',
 'anusvaradeva': u'\u0902',
 'anusvaragujarati': u'\u0A82',
 'aogonek': u'\u0105',
 'apaatosquare': u'\u3300',
 'aparen': u'\u249C',
 'apostrophearmenian': u'\u055A',
 'apostrophemod': u'\u02BC',
 'apple': u'\uF8FF',
 'approaches': u'\u2250',
 'approxequal': u'\u2248',
 'approxequalorimage': u'\u2252',
 'approximatelyequal': u'\u2245',
 'araeaekorean': u'\u318E',
 'araeakorean': u'\u318D',
 'arc': u'\u2312',
 'arighthalfring': u'\u1E9A',
 'aring': u'\u00E5',
 'aringacute': u'\u01FB',
 'aringbelow': u'\u1E01',
 'arrowboth': u'\u2194',
 'arrowdashdown': u'\u21E3',
 'arrowdashleft': u'\u21E0',
 'arrowdashright': u'\u21E2',
 'arrowdashup': u'\u21E1',
 'arrowdblboth': u'\u21D4',
 'arrowdbldown': u'\u21D3',
 'arrowdblleft': u'\u21D0',
 'arrowdblright': u'\u21D2',
 'arrowdblup': u'\u21D1',
 'arrowdown': u'\u2193',
 'arrowdownleft': u'\u2199',
 'arrowdownright': u'\u2198',
 'arrowdownwhite': u'\u21E9',
 'arrowheaddownmod': u'\u02C5',
 'arrowheadleftmod': u'\u02C2',
 'arrowheadrightmod': u'\u02C3',
 'arrowheadupmod': u'\u02C4',
 'arrowhorizex': u'\uF8E7',
 'arrowleft': u'\u2190',
 'arrowleftdbl': u'\u21D0',
 'arrowleftdblstroke': u'\u21CD',
 'arrowleftoverright': u'\u21C6',
 'arrowleftwhite': u'\u21E6',
 'arrowright': u'\u2192',
 'arrowrightdblstroke': u'\u21CF',
 'arrowrightheavy': u'\u279E',
 'arrowrightoverleft': u'\u21C4',
 'arrowrightwhite': u'\u21E8',
 'arrowtableft': u'\u21E4',
 'arrowtabright': u'\u21E5',
 'arrowup': u'\u2191',
 'arrowupdn': u'\u2195',
 'arrowupdnbse': u'\u21A8',
 'arrowupdownbase': u'\u21A8',
 'arrowupleft': u'\u2196',
 'arrowupleftofdown': u'\u21C5',
 'arrowupright': u'\u2197',
 'arrowupwhite': u'\u21E7',
 'arrowvertex': u'\uF8E6',
 'asciicircum': u'\u005E',
 'asciicircummonospace': u'\uFF3E',
 'asciitilde': u'\u007E',
 'asciitildemonospace': u'\uFF5E',
 'ascript': u'\u0251',
 'ascriptturned': u'\u0252',
 'asmallhiragana': u'\u3041',
 'asmallkatakana': u'\u30A1',
 'asmallkatakanahalfwidth': u'\uFF67',
 'asterisk': u'\u002A',
 'asteriskaltonearabic': u'\u066D',
 'asteriskarabic': u'\u066D',
 'asteriskmath': u'\u2217',
 'asteriskmonospace': u'\uFF0A',
 'asterisksmall': u'\uFE61',
 'asterism': u'\u2042',
 'asuperior': u'\uF6E9',
 'asymptoticallyequal': u'\u2243',
 'at': u'\u0040',
 'atilde': u'\u00E3',
 'atmonospace': u'\uFF20',
 'atsmall': u'\uFE6B',
 'aturned': u'\u0250',
 'aubengali': u'\u0994',
 'aubopomofo': u'\u3120',
 'audeva': u'\u0914',
 'augujarati': u'\u0A94',
 'augurmukhi': u'\u0A14',
 'aulengthmarkbengali': u'\u09D7',
 'aumatragurmukhi': u'\u0A4C',
 'auvowelsignbengali': u'\u09CC',
 'auvowelsigndeva': u'\u094C',
 'auvowelsigngujarati': u'\u0ACC',
 'avagrahadeva': u'\u093D',
 'aybarmenian': u'\u0561',
 'ayin': u'\u05E2',
 'ayinaltonehebrew': u'\uFB20',
 'ayinhebrew': u'\u05E2',
 'b': u'\u0062',
 'babengali': u'\u09AC',
 'backslash': u'\u005C',
 'backslashmonospace': u'\uFF3C',
 'badeva': u'\u092C',
 'bagujarati': u'\u0AAC',
 'bagurmukhi': u'\u0A2C',
 'bahiragana': u'\u3070',
 'bahtthai': u'\u0E3F',
 'bakatakana': u'\u30D0',
 'bar': u'\u007C',
 'barmonospace': u'\uFF5C',
 'bbopomofo': u'\u3105',
 'bcircle': u'\u24D1',
 'bdotaccent': u'\u1E03',
 'bdotbelow': u'\u1E05',
 'beamedsixteenthnotes': u'\u266C',
 'because': u'\u2235',
 'becyrillic': u'\u0431',
 'beharabic': u'\u0628',
 'behfinalarabic': u'\uFE90',
 'behinitialarabic': u'\uFE91',
 'behiragana': u'\u3079',
 'behmedialarabic': u'\uFE92',
 'behmeeminitialarabic': u'\uFC9F',
 'behmeemisolatedarabic': u'\uFC08',
 'behnoonfinalarabic': u'\uFC6D',
 'bekatakana': u'\u30D9',
 'benarmenian': u'\u0562',
 'bet': u'\u05D1',
 'beta': u'\u03B2',
 'betasymbolgreek': u'\u03D0',
 'betdagesh': u'\uFB31',
 'betdageshhebrew': u'\uFB31',
 'bethebrew': u'\u05D1',
 'betrafehebrew': u'\uFB4C',
 'bhabengali': u'\u09AD',
 'bhadeva': u'\u092D',
 'bhagujarati': u'\u0AAD',
 'bhagurmukhi': u'\u0A2D',
 'bhook': u'\u0253',
 'bihiragana': u'\u3073',
 'bikatakana': u'\u30D3',
 'bilabialclick': u'\u0298',
 'bindigurmukhi': u'\u0A02',
 'birusquare': u'\u3331',
 'blackcircle': u'\u25CF',
 'blackdiamond': u'\u25C6',
 'blackdownpointingtriangle': u'\u25BC',
 'blackleftpointingpointer': u'\u25C4',
 'blackleftpointingtriangle': u'\u25C0',
 'blacklenticularbracketleft': u'\u3010',
 'blacklenticularbracketleftvertical': u'\uFE3B',
 'blacklenticularbracketright': u'\u3011',
 'blacklenticularbracketrightvertical': u'\uFE3C',
 'blacklowerlefttriangle': u'\u25E3',
 'blacklowerrighttriangle': u'\u25E2',
 'blackrectangle': u'\u25AC',
 'blackrightpointingpointer': u'\u25BA',
 'blackrightpointingtriangle': u'\u25B6',
 'blacksmallsquare': u'\u25AA',
 'blacksmilingface': u'\u263B',
 'blacksquare': u'\u25A0',
 'blackstar': u'\u2605',
 'blackupperlefttriangle': u'\u25E4',
 'blackupperrighttriangle': u'\u25E5',
 'blackuppointingsmalltriangle': u'\u25B4',
 'blackuppointingtriangle': u'\u25B2',
 'blank': u'\u2423',
 'blinebelow': u'\u1E07',
 'block': u'\u2588',
 'bmonospace': u'\uFF42',
 'bobaimaithai': u'\u0E1A',
 'bohiragana': u'\u307C',
 'bokatakana': u'\u30DC',
 'bparen': u'\u249D',
 'bqsquare': u'\u33C3',
 'braceex': u'\uF8F4',
 'braceleft': u'\u007B',
 'braceleftbt': u'\uF8F3',
 'braceleftmid': u'\uF8F2',
 'braceleftmonospace': u'\uFF5B',
 'braceleftsmall': u'\uFE5B',
 'bracelefttp': u'\uF8F1',
 'braceleftvertical': u'\uFE37',
 'braceright': u'\u007D',
 'bracerightbt': u'\uF8FE',
 'bracerightmid': u'\uF8FD',
 'bracerightmonospace': u'\uFF5D',
 'bracerightsmall': u'\uFE5C',
 'bracerighttp': u'\uF8FC',
 'bracerightvertical': u'\uFE38',
 'bracketleft': u'\u005B',
 'bracketleftbt': u'\uF8F0',
 'bracketleftex': u'\uF8EF',
 'bracketleftmonospace': u'\uFF3B',
 'bracketlefttp': u'\uF8EE',
 'bracketright': u'\u005D',
 'bracketrightbt': u'\uF8FB',
 'bracketrightex': u'\uF8FA',
 'bracketrightmonospace': u'\uFF3D',
 'bracketrighttp': u'\uF8F9',
 'breve': u'\u02D8',
 'brevebelowcmb': u'\u032E',
 'brevecmb': u'\u0306',
 'breveinvertedbelowcmb': u'\u032F',
 'breveinvertedcmb': u'\u0311',
 'breveinverteddoublecmb': u'\u0361',
 'bridgebelowcmb': u'\u032A',
 'bridgeinvertedbelowcmb': u'\u033A',
 'brokenbar': u'\u00A6',
 'bstroke': u'\u0180',
 'bsuperior': u'\uF6EA',
 'btopbar': u'\u0183',
 'buhiragana': u'\u3076',
 'bukatakana': u'\u30D6',
 'bullet': u'\u2022',
 'bulletinverse': u'\u25D8',
 'bulletoperator': u'\u2219',
 'bullseye': u'\u25CE',
 'c': u'\u0063',
 'caarmenian': u'\u056E',
 'cabengali': u'\u099A',
 'cacute': u'\u0107',
 'cadeva': u'\u091A',
 'cagujarati': u'\u0A9A',
 'cagurmukhi': u'\u0A1A',
 'calsquare': u'\u3388',
 'candrabindubengali': u'\u0981',
 'candrabinducmb': u'\u0310',
 'candrabindudeva': u'\u0901',
 'candrabindugujarati': u'\u0A81',
 'capslock': u'\u21EA',
 'careof': u'\u2105',
 'caron': u'\u02C7',
 'caronbelowcmb': u'\u032C',
 'caroncmb': u'\u030C',
 'carriagereturn': u'\u21B5',
 'cbopomofo': u'\u3118',
 'ccaron': u'\u010D',
 'ccedilla': u'\u00E7',
 'ccedillaacute': u'\u1E09',
 'ccircle': u'\u24D2',
 'ccircumflex': u'\u0109',
 'ccurl': u'\u0255',
 'cdot': u'\u010B',
 'cdotaccent': u'\u010B',
 'cdsquare': u'\u33C5',
 'cedilla': u'\u00B8',
 'cedillacmb': u'\u0327',
 'cent': u'\u00A2',
 'centigrade': u'\u2103',
 'centinferior': u'\uF6DF',
 'centmonospace': u'\uFFE0',
 'centoldstyle': u'\uF7A2',
 'centsuperior': u'\uF6E0',
 'chaarmenian': u'\u0579',
 'chabengali': u'\u099B',
 'chadeva': u'\u091B',
 'chagujarati': u'\u0A9B',
 'chagurmukhi': u'\u0A1B',
 'chbopomofo': u'\u3114',
 'cheabkhasiancyrillic': u'\u04BD',
 'checkmark': u'\u2713',
 'checyrillic': u'\u0447',
 'chedescenderabkhasiancyrillic': u'\u04BF',
 'chedescendercyrillic': u'\u04B7',
 'chedieresiscyrillic': u'\u04F5',
 'cheharmenian': u'\u0573',
 'chekhakassiancyrillic': u'\u04CC',
 'cheverticalstrokecyrillic': u'\u04B9',
 'chi': u'\u03C7',
 'chieuchacirclekorean': u'\u3277',
 'chieuchaparenkorean': u'\u3217',
 'chieuchcirclekorean': u'\u3269',
 'chieuchkorean': u'\u314A',
 'chieuchparenkorean': u'\u3209',
 'chochangthai': u'\u0E0A',
 'chochanthai': u'\u0E08',
 'chochingthai': u'\u0E09',
 'chochoethai': u'\u0E0C',
 'chook': u'\u0188',
 'cieucacirclekorean': u'\u3276',
 'cieucaparenkorean': u'\u3216',
 'cieuccirclekorean': u'\u3268',
 'cieuckorean': u'\u3148',
 'cieucparenkorean': u'\u3208',
 'cieucuparenkorean': u'\u321C',
 'circle': u'\u25CB',
 'circlemultiply': u'\u2297',
 'circleot': u'\u2299',
 'circleplus': u'\u2295',
 'circlepostalmark': u'\u3036',
 'circlewithlefthalfblack': u'\u25D0',
 'circlewithrighthalfblack': u'\u25D1',
 'circumflex': u'\u02C6',
 'circumflexbelowcmb': u'\u032D',
 'circumflexcmb': u'\u0302',
 'clear': u'\u2327',
 'clickalveolar': u'\u01C2',
 'clickdental': u'\u01C0',
 'clicklateral': u'\u01C1',
 'clickretroflex': u'\u01C3',
 'club': u'\u2663',
 'clubsuitblack': u'\u2663',
 'clubsuitwhite': u'\u2667',
 'cmcubedsquare': u'\u33A4',
 'cmonospace': u'\uFF43',
 'cmsquaredsquare': u'\u33A0',
 'coarmenian': u'\u0581',
 'colon': u'\u003A',
 'colonmonetary': u'\u20A1',
 'colonmonospace': u'\uFF1A',
 'colonsign': u'\u20A1',
 'colonsmall': u'\uFE55',
 'colontriangularhalfmod': u'\u02D1',
 'colontriangularmod': u'\u02D0',
 'comma': u'\u002C',
 'commaabovecmb': u'\u0313',
 'commaaboverightcmb': u'\u0315',
 'commaaccent': u'\uF6C3',
 'commaarabic': u'\u060C',
 'commaarmenian': u'\u055D',
 'commainferior': u'\uF6E1',
 'commamonospace': u'\uFF0C',
 'commareversedabovecmb': u'\u0314',
 'commareversedmod': u'\u02BD',
 'commasmall': u'\uFE50',
 'commasuperior': u'\uF6E2',
 'commaturnedabovecmb': u'\u0312',
 'commaturnedmod': u'\u02BB',
 'compass': u'\u263C',
 'congruent': u'\u2245',
 'contourintegral': u'\u222E',
 'control': u'\u2303',
 'controlACK': u'\u0006',
 'controlBEL': u'\u0007',
 'controlBS': u'\u0008',
 'controlCAN': u'\u0018',
 'controlCR': u'\u000D',
 'controlDC1': u'\u0011',
 'controlDC2': u'\u0012',
 'controlDC3': u'\u0013',
 'controlDC4': u'\u0014',
 'controlDEL': u'\u007F',
 'controlDLE': u'\u0010',
 'controlEM': u'\u0019',
 'controlENQ': u'\u0005',
 'controlEOT': u'\u0004',
 'controlESC': u'\u001B',
 'controlETB': u'\u0017',
 'controlETX': u'\u0003',
 'controlFF': u'\u000C',
 'controlFS': u'\u001C',
 'controlGS': u'\u001D',
 'controlHT': u'\u0009',
 'controlLF': u'\u000A',
 'controlNAK': u'\u0015',
 'controlRS': u'\u001E',
 'controlSI': u'\u000F',
 'controlSO': u'\u000E',
 'controlSOT': u'\u0002',
 'controlSTX': u'\u0001',
 'controlSUB': u'\u001A',
 'controlSYN': u'\u0016',
 'controlUS': u'\u001F',
 'controlVT': u'\u000B',
 'copyright': u'\u00A9',
 'copyrightsans': u'\uF8E9',
 'copyrightserif': u'\uF6D9',
 'cornerbracketleft': u'\u300C',
 'cornerbracketlefthalfwidth': u'\uFF62',
 'cornerbracketleftvertical': u'\uFE41',
 'cornerbracketright': u'\u300D',
 'cornerbracketrighthalfwidth': u'\uFF63',
 'cornerbracketrightvertical': u'\uFE42',
 'corporationsquare': u'\u337F',
 'cosquare': u'\u33C7',
 'coverkgsquare': u'\u33C6',
 'cparen': u'\u249E',
 'cruzeiro': u'\u20A2',
 'cstretched': u'\u0297',
 'curlyand': u'\u22CF',
 'curlyor': u'\u22CE',
 'currency': u'\u00A4',
 'cyrBreve': u'\uF6D1',
 'cyrFlex': u'\uF6D2',
 'cyrbreve': u'\uF6D4',
 'cyrflex': u'\uF6D5',
 'd': u'\u0064',
 'daarmenian': u'\u0564',
 'dabengali': u'\u09A6',
 'dadarabic': u'\u0636',
 'dadeva': u'\u0926',
 'dadfinalarabic': u'\uFEBE',
 'dadinitialarabic': u'\uFEBF',
 'dadmedialarabic': u'\uFEC0',
 'dagesh': u'\u05BC',
 'dageshhebrew': u'\u05BC',
 'dagger': u'\u2020',
 'daggerdbl': u'\u2021',
 'dagujarati': u'\u0AA6',
 'dagurmukhi': u'\u0A26',
 'dahiragana': u'\u3060',
 'dakatakana': u'\u30C0',
 'dalarabic': u'\u062F',
 'dalet': u'\u05D3',
 'daletdagesh': u'\uFB33',
 'daletdageshhebrew': u'\uFB33',
 'dalethatafpatah': u'\u05D3\u05B2',
 'dalethatafpatahhebrew': u'\u05D3\u05B2',
 'dalethatafsegol': u'\u05D3\u05B1',
 'dalethatafsegolhebrew': u'\u05D3\u05B1',
 'dalethebrew': u'\u05D3',
 'dalethiriq': u'\u05D3\u05B4',
 'dalethiriqhebrew': u'\u05D3\u05B4',
 'daletholam': u'\u05D3\u05B9',
 'daletholamhebrew': u'\u05D3\u05B9',
 'daletpatah': u'\u05D3\u05B7',
 'daletpatahhebrew': u'\u05D3\u05B7',
 'daletqamats': u'\u05D3\u05B8',
 'daletqamatshebrew': u'\u05D3\u05B8',
 'daletqubuts': u'\u05D3\u05BB',
 'daletqubutshebrew': u'\u05D3\u05BB',
 'daletsegol': u'\u05D3\u05B6',
 'daletsegolhebrew': u'\u05D3\u05B6',
 'daletsheva': u'\u05D3\u05B0',
 'daletshevahebrew': u'\u05D3\u05B0',
 'dalettsere': u'\u05D3\u05B5',
 'dalettserehebrew': u'\u05D3\u05B5',
 'dalfinalarabic': u'\uFEAA',
 'dammaarabic': u'\u064F',
 'dammalowarabic': u'\u064F',
 'dammatanaltonearabic': u'\u064C',
 'dammatanarabic': u'\u064C',
 'danda': u'\u0964',
 'dargahebrew': u'\u05A7',
 'dargalefthebrew': u'\u05A7',
 'dasiapneumatacyrilliccmb': u'\u0485',
 'dblGrave': u'\uF6D3',
 'dblanglebracketleft': u'\u300A',
 'dblanglebracketleftvertical': u'\uFE3D',
 'dblanglebracketright': u'\u300B',
 'dblanglebracketrightvertical': u'\uFE3E',
 'dblarchinvertedbelowcmb': u'\u032B',
 'dblarrowleft': u'\u21D4',
 'dblarrowright': u'\u21D2',
 'dbldanda': u'\u0965',
 'dblgrave': u'\uF6D6',
 'dblgravecmb': u'\u030F',
 'dblintegral': u'\u222C',
 'dbllowline': u'\u2017',
 'dbllowlinecmb': u'\u0333',
 'dbloverlinecmb': u'\u033F',
 'dblprimemod': u'\u02BA',
 'dblverticalbar': u'\u2016',
 'dblverticallineabovecmb': u'\u030E',
 'dbopomofo': u'\u3109',
 'dbsquare': u'\u33C8',
 'dcaron': u'\u010F',
 'dcedilla': u'\u1E11',
 'dcircle': u'\u24D3',
 'dcircumflexbelow': u'\u1E13',
 'dcroat': u'\u0111',
 'ddabengali': u'\u09A1',
 'ddadeva': u'\u0921',
 'ddagujarati': u'\u0AA1',
 'ddagurmukhi': u'\u0A21',
 'ddalarabic': u'\u0688',
 'ddalfinalarabic': u'\uFB89',
 'dddhadeva': u'\u095C',
 'ddhabengali': u'\u09A2',
 'ddhadeva': u'\u0922',
 'ddhagujarati': u'\u0AA2',
 'ddhagurmukhi': u'\u0A22',
 'ddotaccent': u'\u1E0B',
 'ddotbelow': u'\u1E0D',
 'decimalseparatorarabic': u'\u066B',
 'decimalseparatorpersian': u'\u066B',
 'decyrillic': u'\u0434',
 'degree': u'\u00B0',
 'dehihebrew': u'\u05AD',
 'dehiragana': u'\u3067',
 'deicoptic': u'\u03EF',
 'dekatakana': u'\u30C7',
 'deleteleft': u'\u232B',
 'deleteright': u'\u2326',
 'delta': u'\u03B4',
 'deltaturned': u'\u018D',
 'denominatorminusonenumeratorbengali': u'\u09F8',
 'dezh': u'\u02A4',
 'dhabengali': u'\u09A7',
 'dhadeva': u'\u0927',
 'dhagujarati': u'\u0AA7',
 'dhagurmukhi': u'\u0A27',
 'dhook': u'\u0257',
 'dialytikatonos': u'\u0385',
 'dialytikatonoscmb': u'\u0344',
 'diamond': u'\u2666',
 'diamondsuitwhite': u'\u2662',
 'dieresis': u'\u00A8',
 'dieresisacute': u'\uF6D7',
 'dieresisbelowcmb': u'\u0324',
 'dieresiscmb': u'\u0308',
 'dieresisgrave': u'\uF6D8',
 'dieresistonos': u'\u0385',
 'dihiragana': u'\u3062',
 'dikatakana': u'\u30C2',
 'dittomark': u'\u3003',
 'divide': u'\u00F7',
 'divides': u'\u2223',
 'divisionslash': u'\u2215',
 'djecyrillic': u'\u0452',
 'dkshade': u'\u2593',
 'dlinebelow': u'\u1E0F',
 'dlsquare': u'\u3397',
 'dmacron': u'\u0111',
 'dmonospace': u'\uFF44',
 'dnblock': u'\u2584',
 'dochadathai': u'\u0E0E',
 'dodekthai': u'\u0E14',
 'dohiragana': u'\u3069',
 'dokatakana': u'\u30C9',
 'dollar': u'\u0024',
 'dollarinferior': u'\uF6E3',
 'dollarmonospace': u'\uFF04',
 'dollaroldstyle': u'\uF724',
 'dollarsmall': u'\uFE69',
 'dollarsuperior': u'\uF6E4',
 'dong': u'\u20AB',
 'dorusquare': u'\u3326',
 'dotaccent': u'\u02D9',
 'dotaccentcmb': u'\u0307',
 'dotbelowcmb': u'\u0323',
 'dotbelowcomb': u'\u0323',
 'dotkatakana': u'\u30FB',
 'dotlessi': u'\u0131',
 'dotlessj': u'\uF6BE',
 'dotlessjstrokehook': u'\u0284',
 'dotmath': u'\u22C5',
 'dottedcircle': u'\u25CC',
 'doubleyodpatah': u'\uFB1F',
 'doubleyodpatahhebrew': u'\uFB1F',
 'downtackbelowcmb': u'\u031E',
 'downtackmod': u'\u02D5',
 'dparen': u'\u249F',
 'dsuperior': u'\uF6EB',
 'dtail': u'\u0256',
 'dtopbar': u'\u018C',
 'duhiragana': u'\u3065',
 'dukatakana': u'\u30C5',
 'dz': u'\u01F3',
 'dzaltone': u'\u02A3',
 'dzcaron': u'\u01C6',
 'dzcurl': u'\u02A5',
 'dzeabkhasiancyrillic': u'\u04E1',
 'dzecyrillic': u'\u0455',
 'dzhecyrillic': u'\u045F',
 'e': u'\u0065',
 'eacute': u'\u00E9',
 'earth': u'\u2641',
 'ebengali': u'\u098F',
 'ebopomofo': u'\u311C',
 'ebreve': u'\u0115',
 'ecandradeva': u'\u090D',
 'ecandragujarati': u'\u0A8D',
 'ecandravowelsigndeva': u'\u0945',
 'ecandravowelsigngujarati': u'\u0AC5',
 'ecaron': u'\u011B',
 'ecedillabreve': u'\u1E1D',
 'echarmenian': u'\u0565',
 'echyiwnarmenian': u'\u0587',
 'ecircle': u'\u24D4',
 'ecircumflex': u'\u00EA',
 'ecircumflexacute': u'\u1EBF',
 'ecircumflexbelow': u'\u1E19',
 'ecircumflexdotbelow': u'\u1EC7',
 'ecircumflexgrave': u'\u1EC1',
 'ecircumflexhookabove': u'\u1EC3',
 'ecircumflextilde': u'\u1EC5',
 'ecyrillic': u'\u0454',
 'edblgrave': u'\u0205',
 'edeva': u'\u090F',
 'edieresis': u'\u00EB',
 'edot': u'\u0117',
 'edotaccent': u'\u0117',
 'edotbelow': u'\u1EB9',
 'eegurmukhi': u'\u0A0F',
 'eematragurmukhi': u'\u0A47',
 'efcyrillic': u'\u0444',
 'egrave': u'\u00E8',
 'egujarati': u'\u0A8F',
 'eharmenian': u'\u0567',
 'ehbopomofo': u'\u311D',
 'ehiragana': u'\u3048',
 'ehookabove': u'\u1EBB',
 'eibopomofo': u'\u311F',
 'eight': u'\u0038',
 'eightarabic': u'\u0668',
 'eightbengali': u'\u09EE',
 'eightcircle': u'\u2467',
 'eightcircleinversesansserif': u'\u2791',
 'eightdeva': u'\u096E',
 'eighteencircle': u'\u2471',
 'eighteenparen': u'\u2485',
 'eighteenperiod': u'\u2499',
 'eightgujarati': u'\u0AEE',
 'eightgurmukhi': u'\u0A6E',
 'eighthackarabic': u'\u0668',
 'eighthangzhou': u'\u3028',
 'eighthnotebeamed': u'\u266B',
 'eightideographicparen': u'\u3227',
 'eightinferior': u'\u2088',
 'eightmonospace': u'\uFF18',
 'eightoldstyle': u'\uF738',
 'eightparen': u'\u247B',
 'eightperiod': u'\u248F',
 'eightpersian': u'\u06F8',
 'eightroman': u'\u2177',
 'eightsuperior': u'\u2078',
 'eightthai': u'\u0E58',
 'einvertedbreve': u'\u0207',
 'eiotifiedcyrillic': u'\u0465',
 'ekatakana': u'\u30A8',
 'ekatakanahalfwidth': u'\uFF74',
 'ekonkargurmukhi': u'\u0A74',
 'ekorean': u'\u3154',
 'elcyrillic': u'\u043B',
 'element': u'\u2208',
 'elevencircle': u'\u246A',
 'elevenparen': u'\u247E',
 'elevenperiod': u'\u2492',
 'elevenroman': u'\u217A',
 'ellipsis': u'\u2026',
 'ellipsisvertical': u'\u22EE',
 'emacron': u'\u0113',
 'emacronacute': u'\u1E17',
 'emacrongrave': u'\u1E15',
 'emcyrillic': u'\u043C',
 'emdash': u'\u2014',
 'emdashvertical': u'\uFE31',
 'emonospace': u'\uFF45',
 'emphasismarkarmenian': u'\u055B',
 'emptyset': u'\u2205',
 'enbopomofo': u'\u3123',
 'encyrillic': u'\u043D',
 'endash': u'\u2013',
 'endashvertical': u'\uFE32',
 'endescendercyrillic': u'\u04A3',
 'eng': u'\u014B',
 'engbopomofo': u'\u3125',
 'enghecyrillic': u'\u04A5',
 'enhookcyrillic': u'\u04C8',
 'enspace': u'\u2002',
 'eogonek': u'\u0119',
 'eokorean': u'\u3153',
 'eopen': u'\u025B',
 'eopenclosed': u'\u029A',
 'eopenreversed': u'\u025C',
 'eopenreversedclosed': u'\u025E',
 'eopenreversedhook': u'\u025D',
 'eparen': u'\u24A0',
 'epsilon': u'\u03B5',
 'epsilontonos': u'\u03AD',
 'equal': u'\u003D',
 'equalmonospace': u'\uFF1D',
 'equalsmall': u'\uFE66',
 'equalsuperior': u'\u207C',
 'equivalence': u'\u2261',
 'erbopomofo': u'\u3126',
 'ercyrillic': u'\u0440',
 'ereversed': u'\u0258',
 'ereversedcyrillic': u'\u044D',
 'escyrillic': u'\u0441',
 'esdescendercyrillic': u'\u04AB',
 'esh': u'\u0283',
 'eshcurl': u'\u0286',
 'eshortdeva': u'\u090E',
 'eshortvowelsigndeva': u'\u0946',
 'eshreversedloop': u'\u01AA',
 'eshsquatreversed': u'\u0285',
 'esmallhiragana': u'\u3047',
 'esmallkatakana': u'\u30A7',
 'esmallkatakanahalfwidth': u'\uFF6A',
 'estimated': u'\u212E',
 'esuperior': u'\uF6EC',
 'eta': u'\u03B7',
 'etarmenian': u'\u0568',
 'etatonos': u'\u03AE',
 'eth': u'\u00F0',
 'etilde': u'\u1EBD',
 'etildebelow': u'\u1E1B',
 'etnahtafoukhhebrew': u'\u0591',
 'etnahtafoukhlefthebrew': u'\u0591',
 'etnahtahebrew': u'\u0591',
 'etnahtalefthebrew': u'\u0591',
 'eturned': u'\u01DD',
 'eukorean': u'\u3161',
 'euro': u'\u20AC',
 'evowelsignbengali': u'\u09C7',
 'evowelsigndeva': u'\u0947',
 'evowelsigngujarati': u'\u0AC7',
 'exclam': u'\u0021',
 'exclamarmenian': u'\u055C',
 'exclamdbl': u'\u203C',
 'exclamdown': u'\u00A1',
 'exclamdownsmall': u'\uF7A1',
 'exclammonospace': u'\uFF01',
 'exclamsmall': u'\uF721',
 'existential': u'\u2203',
 'ezh': u'\u0292',
 'ezhcaron': u'\u01EF',
 'ezhcurl': u'\u0293',
 'ezhreversed': u'\u01B9',
 'ezhtail': u'\u01BA',
 'f': u'\u0066',
 'fadeva': u'\u095E',
 'fagurmukhi': u'\u0A5E',
 'fahrenheit': u'\u2109',
 'fathaarabic': u'\u064E',
 'fathalowarabic': u'\u064E',
 'fathatanarabic': u'\u064B',
 'fbopomofo': u'\u3108',
 'fcircle': u'\u24D5',
 'fdotaccent': u'\u1E1F',
 'feharabic': u'\u0641',
 'feharmenian': u'\u0586',
 'fehfinalarabic': u'\uFED2',
 'fehinitialarabic': u'\uFED3',
 'fehmedialarabic': u'\uFED4',
 'feicoptic': u'\u03E5',
 'female': u'\u2640',
 'ff': u'\uFB00',
 'ffi': u'\uFB03',
 'ffl': u'\uFB04',
 'fi': u'\uFB01',
 'fifteencircle': u'\u246E',
 'fifteenparen': u'\u2482',
 'fifteenperiod': u'\u2496',
 'figuredash': u'\u2012',
 'filledbox': u'\u25A0',
 'filledrect': u'\u25AC',
 'finalkaf': u'\u05DA',
 'finalkafdagesh': u'\uFB3A',
 'finalkafdageshhebrew': u'\uFB3A',
 'finalkafhebrew': u'\u05DA',
 'finalkafqamats': u'\u05DA\u05B8',
 'finalkafqamatshebrew': u'\u05DA\u05B8',
 'finalkafsheva': u'\u05DA\u05B0',
 'finalkafshevahebrew': u'\u05DA\u05B0',
 'finalmem': u'\u05DD',
 'finalmemhebrew': u'\u05DD',
 'finalnun': u'\u05DF',
 'finalnunhebrew': u'\u05DF',
 'finalpe': u'\u05E3',
 'finalpehebrew': u'\u05E3',
 'finaltsadi': u'\u05E5',
 'finaltsadihebrew': u'\u05E5',
 'firsttonechinese': u'\u02C9',
 'fisheye': u'\u25C9',
 'fitacyrillic': u'\u0473',
 'five': u'\u0035',
 'fivearabic': u'\u0665',
 'fivebengali': u'\u09EB',
 'fivecircle': u'\u2464',
 'fivecircleinversesansserif': u'\u278E',
 'fivedeva': u'\u096B',
 'fiveeighths': u'\u215D',
 'fivegujarati': u'\u0AEB',
 'fivegurmukhi': u'\u0A6B',
 'fivehackarabic': u'\u0665',
 'fivehangzhou': u'\u3025',
 'fiveideographicparen': u'\u3224',
 'fiveinferior': u'\u2085',
 'fivemonospace': u'\uFF15',
 'fiveoldstyle': u'\uF735',
 'fiveparen': u'\u2478',
 'fiveperiod': u'\u248C',
 'fivepersian': u'\u06F5',
 'fiveroman': u'\u2174',
 'fivesuperior': u'\u2075',
 'fivethai': u'\u0E55',
 'fl': u'\uFB02',
 'florin': u'\u0192',
 'fmonospace': u'\uFF46',
 'fmsquare': u'\u3399',
 'fofanthai': u'\u0E1F',
 'fofathai': u'\u0E1D',
 'fongmanthai': u'\u0E4F',
 'forall': u'\u2200',
 'four': u'\u0034',
 'fourarabic': u'\u0664',
 'fourbengali': u'\u09EA',
 'fourcircle': u'\u2463',
 'fourcircleinversesansserif': u'\u278D',
 'fourdeva': u'\u096A',
 'fourgujarati': u'\u0AEA',
 'fourgurmukhi': u'\u0A6A',
 'fourhackarabic': u'\u0664',
 'fourhangzhou': u'\u3024',
 'fourideographicparen': u'\u3223',
 'fourinferior': u'\u2084',
 'fourmonospace': u'\uFF14',
 'fournumeratorbengali': u'\u09F7',
 'fouroldstyle': u'\uF734',
 'fourparen': u'\u2477',
 'fourperiod': u'\u248B',
 'fourpersian': u'\u06F4',
 'fourroman': u'\u2173',
 'foursuperior': u'\u2074',
 'fourteencircle': u'\u246D',
 'fourteenparen': u'\u2481',
 'fourteenperiod': u'\u2495',
 'fourthai': u'\u0E54',
 'fourthtonechinese': u'\u02CB',
 'fparen': u'\u24A1',
 'fraction': u'\u2044',
 'franc': u'\u20A3',
 'g': u'\u0067',
 'gabengali': u'\u0997',
 'gacute': u'\u01F5',
 'gadeva': u'\u0917',
 'gafarabic': u'\u06AF',
 'gaffinalarabic': u'\uFB93',
 'gafinitialarabic': u'\uFB94',
 'gafmedialarabic': u'\uFB95',
 'gagujarati': u'\u0A97',
 'gagurmukhi': u'\u0A17',
 'gahiragana': u'\u304C',
 'gakatakana': u'\u30AC',
 'gamma': u'\u03B3',
 'gammalatinsmall': u'\u0263',
 'gammasuperior': u'\u02E0',
 'gangiacoptic': u'\u03EB',
 'gbopomofo': u'\u310D',
 'gbreve': u'\u011F',
 'gcaron': u'\u01E7',
 'gcedilla': u'\u0123',
 'gcircle': u'\u24D6',
 'gcircumflex': u'\u011D',
 'gcommaaccent': u'\u0123',
 'gdot': u'\u0121',
 'gdotaccent': u'\u0121',
 'gecyrillic': u'\u0433',
 'gehiragana': u'\u3052',
 'gekatakana': u'\u30B2',
 'geometricallyequal': u'\u2251',
 'gereshaccenthebrew': u'\u059C',
 'gereshhebrew': u'\u05F3',
 'gereshmuqdamhebrew': u'\u059D',
 'germandbls': u'\u00DF',
 'gershayimaccenthebrew': u'\u059E',
 'gershayimhebrew': u'\u05F4',
 'getamark': u'\u3013',
 'ghabengali': u'\u0998',
 'ghadarmenian': u'\u0572',
 'ghadeva': u'\u0918',
 'ghagujarati': u'\u0A98',
 'ghagurmukhi': u'\u0A18',
 'ghainarabic': u'\u063A',
 'ghainfinalarabic': u'\uFECE',
 'ghaininitialarabic': u'\uFECF',
 'ghainmedialarabic': u'\uFED0',
 'ghemiddlehookcyrillic': u'\u0495',
 'ghestrokecyrillic': u'\u0493',
 'gheupturncyrillic': u'\u0491',
 'ghhadeva': u'\u095A',
 'ghhagurmukhi': u'\u0A5A',
 'ghook': u'\u0260',
 'ghzsquare': u'\u3393',
 'gihiragana': u'\u304E',
 'gikatakana': u'\u30AE',
 'gimarmenian': u'\u0563',
 'gimel': u'\u05D2',
 'gimeldagesh': u'\uFB32',
 'gimeldageshhebrew': u'\uFB32',
 'gimelhebrew': u'\u05D2',
 'gjecyrillic': u'\u0453',
 'glottalinvertedstroke': u'\u01BE',
 'glottalstop': u'\u0294',
 'glottalstopinverted': u'\u0296',
 'glottalstopmod': u'\u02C0',
 'glottalstopreversed': u'\u0295',
 'glottalstopreversedmod': u'\u02C1',
 'glottalstopreversedsuperior': u'\u02E4',
 'glottalstopstroke': u'\u02A1',
 'glottalstopstrokereversed': u'\u02A2',
 'gmacron': u'\u1E21',
 'gmonospace': u'\uFF47',
 'gohiragana': u'\u3054',
 'gokatakana': u'\u30B4',
 'gparen': u'\u24A2',
 'gpasquare': u'\u33AC',
 'gradient': u'\u2207',
 'grave': u'\u0060',
 'gravebelowcmb': u'\u0316',
 'gravecmb': u'\u0300',
 'gravecomb': u'\u0300',
 'gravedeva': u'\u0953',
 'gravelowmod': u'\u02CE',
 'gravemonospace': u'\uFF40',
 'gravetonecmb': u'\u0340',
 'greater': u'\u003E',
 'greaterequal': u'\u2265',
 'greaterequalorless': u'\u22DB',
 'greatermonospace': u'\uFF1E',
 'greaterorequivalent': u'\u2273',
 'greaterorless': u'\u2277',
 'greateroverequal': u'\u2267',
 'greatersmall': u'\uFE65',
 'gscript': u'\u0261',
 'gstroke': u'\u01E5',
 'guhiragana': u'\u3050',
 'guillemotleft': u'\u00AB',
 'guillemotright': u'\u00BB',
 'guilsinglleft': u'\u2039',
 'guilsinglright': u'\u203A',
 'gukatakana': u'\u30B0',
 'guramusquare': u'\u3318',
 'gysquare': u'\u33C9',
 'h': u'\u0068',
 'haabkhasiancyrillic': u'\u04A9',
 'haaltonearabic': u'\u06C1',
 'habengali': u'\u09B9',
 'hadescendercyrillic': u'\u04B3',
 'hadeva': u'\u0939',
 'hagujarati': u'\u0AB9',
 'hagurmukhi': u'\u0A39',
 'haharabic': u'\u062D',
 'hahfinalarabic': u'\uFEA2',
 'hahinitialarabic': u'\uFEA3',
 'hahiragana': u'\u306F',
 'hahmedialarabic': u'\uFEA4',
 'haitusquare': u'\u332A',
 'hakatakana': u'\u30CF',
 'hakatakanahalfwidth': u'\uFF8A',
 'halantgurmukhi': u'\u0A4D',
 'hamzaarabic': u'\u0621',
 'hamzadammaarabic': u'\u0621\u064F',
 'hamzadammatanarabic': u'\u0621\u064C',
 'hamzafathaarabic': u'\u0621\u064E',
 'hamzafathatanarabic': u'\u0621\u064B',
 'hamzalowarabic': u'\u0621',
 'hamzalowkasraarabic': u'\u0621\u0650',
 'hamzalowkasratanarabic': u'\u0621\u064D',
 'hamzasukunarabic': u'\u0621\u0652',
 'hangulfiller': u'\u3164',
 'hardsigncyrillic': u'\u044A',
 'harpoonleftbarbup': u'\u21BC',
 'harpoonrightbarbup': u'\u21C0',
 'hasquare': u'\u33CA',
 'hatafpatah': u'\u05B2',
 'hatafpatah16': u'\u05B2',
 'hatafpatah23': u'\u05B2',
 'hatafpatah2f': u'\u05B2',
 'hatafpatahhebrew': u'\u05B2',
 'hatafpatahnarrowhebrew': u'\u05B2',
 'hatafpatahquarterhebrew': u'\u05B2',
 'hatafpatahwidehebrew': u'\u05B2',
 'hatafqamats': u'\u05B3',
 'hatafqamats1b': u'\u05B3',
 'hatafqamats28': u'\u05B3',
 'hatafqamats34': u'\u05B3',
 'hatafqamatshebrew': u'\u05B3',
 'hatafqamatsnarrowhebrew': u'\u05B3',
 'hatafqamatsquarterhebrew': u'\u05B3',
 'hatafqamatswidehebrew': u'\u05B3',
 'hatafsegol': u'\u05B1',
 'hatafsegol17': u'\u05B1',
 'hatafsegol24': u'\u05B1',
 'hatafsegol30': u'\u05B1',
 'hatafsegolhebrew': u'\u05B1',
 'hatafsegolnarrowhebrew': u'\u05B1',
 'hatafsegolquarterhebrew': u'\u05B1',
 'hatafsegolwidehebrew': u'\u05B1',
 'hbar': u'\u0127',
 'hbopomofo': u'\u310F',
 'hbrevebelow': u'\u1E2B',
 'hcedilla': u'\u1E29',
 'hcircle': u'\u24D7',
 'hcircumflex': u'\u0125',
 'hdieresis': u'\u1E27',
 'hdotaccent': u'\u1E23',
 'hdotbelow': u'\u1E25',
 'he': u'\u05D4',
 'heart': u'\u2665',
 'heartsuitblack': u'\u2665',
 'heartsuitwhite': u'\u2661',
 'hedagesh': u'\uFB34',
 'hedageshhebrew': u'\uFB34',
 'hehaltonearabic': u'\u06C1',
 'heharabic': u'\u0647',
 'hehebrew': u'\u05D4',
 'hehfinalaltonearabic': u'\uFBA7',
 'hehfinalalttwoarabic': u'\uFEEA',
 'hehfinalarabic': u'\uFEEA',
 'hehhamzaabovefinalarabic': u'\uFBA5',
 'hehhamzaaboveisolatedarabic': u'\uFBA4',
 'hehinitialaltonearabic': u'\uFBA8',
 'hehinitialarabic': u'\uFEEB',
 'hehiragana': u'\u3078',
 'hehmedialaltonearabic': u'\uFBA9',
 'hehmedialarabic': u'\uFEEC',
 'heiseierasquare': u'\u337B',
 'hekatakana': u'\u30D8',
 'hekatakanahalfwidth': u'\uFF8D',
 'hekutaarusquare': u'\u3336',
 'henghook': u'\u0267',
 'herutusquare': u'\u3339',
 'het': u'\u05D7',
 'hethebrew': u'\u05D7',
 'hhook': u'\u0266',
 'hhooksuperior': u'\u02B1',
 'hieuhacirclekorean': u'\u327B',
 'hieuhaparenkorean': u'\u321B',
 'hieuhcirclekorean': u'\u326D',
 'hieuhkorean': u'\u314E',
 'hieuhparenkorean': u'\u320D',
 'hihiragana': u'\u3072',
 'hikatakana': u'\u30D2',
 'hikatakanahalfwidth': u'\uFF8B',
 'hiriq': u'\u05B4',
 'hiriq14': u'\u05B4',
 'hiriq21': u'\u05B4',
 'hiriq2d': u'\u05B4',
 'hiriqhebrew': u'\u05B4',
 'hiriqnarrowhebrew': u'\u05B4',
 'hiriqquarterhebrew': u'\u05B4',
 'hiriqwidehebrew': u'\u05B4',
 'hlinebelow': u'\u1E96',
 'hmonospace': u'\uFF48',
 'hoarmenian': u'\u0570',
 'hohipthai': u'\u0E2B',
 'hohiragana': u'\u307B',
 'hokatakana': u'\u30DB',
 'hokatakanahalfwidth': u'\uFF8E',
 'holam': u'\u05B9',
 'holam19': u'\u05B9',
 'holam26': u'\u05B9',
 'holam32': u'\u05B9',
 'holamhebrew': u'\u05B9',
 'holamnarrowhebrew': u'\u05B9',
 'holamquarterhebrew': u'\u05B9',
 'holamwidehebrew': u'\u05B9',
 'honokhukthai': u'\u0E2E',
 'hookabovecomb': u'\u0309',
 'hookcmb': u'\u0309',
 'hookpalatalizedbelowcmb': u'\u0321',
 'hookretroflexbelowcmb': u'\u0322',
 'hoonsquare': u'\u3342',
 'horicoptic': u'\u03E9',
 'horizontalbar': u'\u2015',
 'horncmb': u'\u031B',
 'hotsprings': u'\u2668',
 'house': u'\u2302',
 'hparen': u'\u24A3',
 'hsuperior': u'\u02B0',
 'hturned': u'\u0265',
 'huhiragana': u'\u3075',
 'huiitosquare': u'\u3333',
 'hukatakana': u'\u30D5',
 'hukatakanahalfwidth': u'\uFF8C',
 'hungarumlaut': u'\u02DD',
 'hungarumlautcmb': u'\u030B',
 'hv': u'\u0195',
 'hyphen': u'\u002D',
 'hypheninferior': u'\uF6E5',
 'hyphenmonospace': u'\uFF0D',
 'hyphensmall': u'\uFE63',
 'hyphensuperior': u'\uF6E6',
 'hyphentwo': u'\u2010',
 'i': u'\u0069',
 'iacute': u'\u00ED',
 'iacyrillic': u'\u044F',
 'ibengali': u'\u0987',
 'ibopomofo': u'\u3127',
 'ibreve': u'\u012D',
 'icaron': u'\u01D0',
 'icircle': u'\u24D8',
 'icircumflex': u'\u00EE',
 'icyrillic': u'\u0456',
 'idblgrave': u'\u0209',
 'ideographearthcircle': u'\u328F',
 'ideographfirecircle': u'\u328B',
 'ideographicallianceparen': u'\u323F',
 'ideographiccallparen': u'\u323A',
 'ideographiccentrecircle': u'\u32A5',
 'ideographicclose': u'\u3006',
 'ideographiccomma': u'\u3001',
 'ideographiccommaleft': u'\uFF64',
 'ideographiccongratulationparen': u'\u3237',
 'ideographiccorrectcircle': u'\u32A3',
 'ideographicearthparen': u'\u322F',
 'ideographicenterpriseparen': u'\u323D',
 'ideographicexcellentcircle': u'\u329D',
 'ideographicfestivalparen': u'\u3240',
 'ideographicfinancialcircle': u'\u3296',
 'ideographicfinancialparen': u'\u3236',
 'ideographicfireparen': u'\u322B',
 'ideographichaveparen': u'\u3232',
 'ideographichighcircle': u'\u32A4',
 'ideographiciterationmark': u'\u3005',
 'ideographiclaborcircle': u'\u3298',
 'ideographiclaborparen': u'\u3238',
 'ideographicleftcircle': u'\u32A7',
 'ideographiclowcircle': u'\u32A6',
 'ideographicmedicinecircle': u'\u32A9',
 'ideographicmetalparen': u'\u322E',
 'ideographicmoonparen': u'\u322A',
 'ideographicnameparen': u'\u3234',
 'ideographicperiod': u'\u3002',
 'ideographicprintcircle': u'\u329E',
 'ideographicreachparen': u'\u3243',
 'ideographicrepresentparen': u'\u3239',
 'ideographicresourceparen': u'\u323E',
 'ideographicrightcircle': u'\u32A8',
 'ideographicsecretcircle': u'\u3299',
 'ideographicselfparen': u'\u3242',
 'ideographicsocietyparen': u'\u3233',
 'ideographicspace': u'\u3000',
 'ideographicspecialparen': u'\u3235',
 'ideographicstockparen': u'\u3231',
 'ideographicstudyparen': u'\u323B',
 'ideographicsunparen': u'\u3230',
 'ideographicsuperviseparen': u'\u323C',
 'ideographicwaterparen': u'\u322C',
 'ideographicwoodparen': u'\u322D',
 'ideographiczero': u'\u3007',
 'ideographmetalcircle': u'\u328E',
 'ideographmooncircle': u'\u328A',
 'ideographnamecircle': u'\u3294',
 'ideographsuncircle': u'\u3290',
 'ideographwatercircle': u'\u328C',
 'ideographwoodcircle': u'\u328D',
 'ideva': u'\u0907',
 'idieresis': u'\u00EF',
 'idieresisacute': u'\u1E2F',
 'idieresiscyrillic': u'\u04E5',
 'idotbelow': u'\u1ECB',
 'iebrevecyrillic': u'\u04D7',
 'iecyrillic': u'\u0435',
 'ieungacirclekorean': u'\u3275',
 'ieungaparenkorean': u'\u3215',
 'ieungcirclekorean': u'\u3267',
 'ieungkorean': u'\u3147',
 'ieungparenkorean': u'\u3207',
 'igrave': u'\u00EC',
 'igujarati': u'\u0A87',
 'igurmukhi': u'\u0A07',
 'ihiragana': u'\u3044',
 'ihookabove': u'\u1EC9',
 'iibengali': u'\u0988',
 'iicyrillic': u'\u0438',
 'iideva': u'\u0908',
 'iigujarati': u'\u0A88',
 'iigurmukhi': u'\u0A08',
 'iimatragurmukhi': u'\u0A40',
 'iinvertedbreve': u'\u020B',
 'iishortcyrillic': u'\u0439',
 'iivowelsignbengali': u'\u09C0',
 'iivowelsigndeva': u'\u0940',
 'iivowelsigngujarati': u'\u0AC0',
 'ij': u'\u0133',
 'ikatakana': u'\u30A4',
 'ikatakanahalfwidth': u'\uFF72',
 'ikorean': u'\u3163',
 'ilde': u'\u02DC',
 'iluyhebrew': u'\u05AC',
 'imacron': u'\u012B',
 'imacroncyrillic': u'\u04E3',
 'imageorapproximatelyequal': u'\u2253',
 'imatragurmukhi': u'\u0A3F',
 'imonospace': u'\uFF49',
 'increment': u'\u2206',
 'infinity': u'\u221E',
 'iniarmenian': u'\u056B',
 'integral': u'\u222B',
 'integralbottom': u'\u2321',
 'integralbt': u'\u2321',
 'integralex': u'\uF8F5',
 'integraltop': u'\u2320',
 'integraltp': u'\u2320',
 'intersection': u'\u2229',
 'intisquare': u'\u3305',
 'invbullet': u'\u25D8',
 'invcircle': u'\u25D9',
 'invsmileface': u'\u263B',
 'iocyrillic': u'\u0451',
 'iogonek': u'\u012F',
 'iota': u'\u03B9',
 'iotadieresis': u'\u03CA',
 'iotadieresistonos': u'\u0390',
 'iotalatin': u'\u0269',
 'iotatonos': u'\u03AF',
 'iparen': u'\u24A4',
 'irigurmukhi': u'\u0A72',
 'ismallhiragana': u'\u3043',
 'ismallkatakana': u'\u30A3',
 'ismallkatakanahalfwidth': u'\uFF68',
 'issharbengali': u'\u09FA',
 'istroke': u'\u0268',
 'isuperior': u'\uF6ED',
 'iterationhiragana': u'\u309D',
 'iterationkatakana': u'\u30FD',
 'itilde': u'\u0129',
 'itildebelow': u'\u1E2D',
 'iubopomofo': u'\u3129',
 'iucyrillic': u'\u044E',
 'ivowelsignbengali': u'\u09BF',
 'ivowelsigndeva': u'\u093F',
 'ivowelsigngujarati': u'\u0ABF',
 'izhitsacyrillic': u'\u0475',
 'izhitsadblgravecyrillic': u'\u0477',
 'j': u'\u006A',
 'jaarmenian': u'\u0571',
 'jabengali': u'\u099C',
 'jadeva': u'\u091C',
 'jagujarati': u'\u0A9C',
 'jagurmukhi': u'\u0A1C',
 'jbopomofo': u'\u3110',
 'jcaron': u'\u01F0',
 'jcircle': u'\u24D9',
 'jcircumflex': u'\u0135',
 'jcrossedtail': u'\u029D',
 'jdotlessstroke': u'\u025F',
 'jecyrillic': u'\u0458',
 'jeemarabic': u'\u062C',
 'jeemfinalarabic': u'\uFE9E',
 'jeeminitialarabic': u'\uFE9F',
 'jeemmedialarabic': u'\uFEA0',
 'jeharabic': u'\u0698',
 'jehfinalarabic': u'\uFB8B',
 'jhabengali': u'\u099D',
 'jhadeva': u'\u091D',
 'jhagujarati': u'\u0A9D',
 'jhagurmukhi': u'\u0A1D',
 'jheharmenian': u'\u057B',
 'jis': u'\u3004',
 'jmonospace': u'\uFF4A',
 'jparen': u'\u24A5',
 'jsuperior': u'\u02B2',
 'k': u'\u006B',
 'kabashkircyrillic': u'\u04A1',
 'kabengali': u'\u0995',
 'kacute': u'\u1E31',
 'kacyrillic': u'\u043A',
 'kadescendercyrillic': u'\u049B',
 'kadeva': u'\u0915',
 'kaf': u'\u05DB',
 'kafarabic': u'\u0643',
 'kafdagesh': u'\uFB3B',
 'kafdageshhebrew': u'\uFB3B',
 'kaffinalarabic': u'\uFEDA',
 'kafhebrew': u'\u05DB',
 'kafinitialarabic': u'\uFEDB',
 'kafmedialarabic': u'\uFEDC',
 'kafrafehebrew': u'\uFB4D',
 'kagujarati': u'\u0A95',
 'kagurmukhi': u'\u0A15',
 'kahiragana': u'\u304B',
 'kahookcyrillic': u'\u04C4',
 'kakatakana': u'\u30AB',
 'kakatakanahalfwidth': u'\uFF76',
 'kappa': u'\u03BA',
 'kappasymbolgreek': u'\u03F0',
 'kapyeounmieumkorean': u'\u3171',
 'kapyeounphieuphkorean': u'\u3184',
 'kapyeounpieupkorean': u'\u3178',
 'kapyeounssangpieupkorean': u'\u3179',
 'karoriisquare': u'\u330D',
 'kashidaautoarabic': u'\u0640',
 'kashidaautonosidebearingarabic': u'\u0640',
 'kasmallkatakana': u'\u30F5',
 'kasquare': u'\u3384',
 'kasraarabic': u'\u0650',
 'kasratanarabic': u'\u064D',
 'kastrokecyrillic': u'\u049F',
 'katahiraprolongmarkhalfwidth': u'\uFF70',
 'kaverticalstrokecyrillic': u'\u049D',
 'kbopomofo': u'\u310E',
 'kcalsquare': u'\u3389',
 'kcaron': u'\u01E9',
 'kcedilla': u'\u0137',
 'kcircle': u'\u24DA',
 'kcommaaccent': u'\u0137',
 'kdotbelow': u'\u1E33',
 'keharmenian': u'\u0584',
 'kehiragana': u'\u3051',
 'kekatakana': u'\u30B1',
 'kekatakanahalfwidth': u'\uFF79',
 'kenarmenian': u'\u056F',
 'kesmallkatakana': u'\u30F6',
 'kgreenlandic': u'\u0138',
 'khabengali': u'\u0996',
 'khacyrillic': u'\u0445',
 'khadeva': u'\u0916',
 'khagujarati': u'\u0A96',
 'khagurmukhi': u'\u0A16',
 'khaharabic': u'\u062E',
 'khahfinalarabic': u'\uFEA6',
 'khahinitialarabic': u'\uFEA7',
 'khahmedialarabic': u'\uFEA8',
 'kheicoptic': u'\u03E7',
 'khhadeva': u'\u0959',
 'khhagurmukhi': u'\u0A59',
 'khieukhacirclekorean': u'\u3278',
 'khieukhaparenkorean': u'\u3218',
 'khieukhcirclekorean': u'\u326A',
 'khieukhkorean': u'\u314B',
 'khieukhparenkorean': u'\u320A',
 'khokhaithai': u'\u0E02',
 'khokhonthai': u'\u0E05',
 'khokhuatthai': u'\u0E03',
 'khokhwaithai': u'\u0E04',
 'khomutthai': u'\u0E5B',
 'khook': u'\u0199',
 'khorakhangthai': u'\u0E06',
 'khzsquare': u'\u3391',
 'kihiragana': u'\u304D',
 'kikatakana': u'\u30AD',
 'kikatakanahalfwidth': u'\uFF77',
 'kiroguramusquare': u'\u3315',
 'kiromeetorusquare': u'\u3316',
 'kirosquare': u'\u3314',
 'kiyeokacirclekorean': u'\u326E',
 'kiyeokaparenkorean': u'\u320E',
 'kiyeokcirclekorean': u'\u3260',
 'kiyeokkorean': u'\u3131',
 'kiyeokparenkorean': u'\u3200',
 'kiyeoksioskorean': u'\u3133',
 'kjecyrillic': u'\u045C',
 'klinebelow': u'\u1E35',
 'klsquare': u'\u3398',
 'kmcubedsquare': u'\u33A6',
 'kmonospace': u'\uFF4B',
 'kmsquaredsquare': u'\u33A2',
 'kohiragana': u'\u3053',
 'kohmsquare': u'\u33C0',
 'kokaithai': u'\u0E01',
 'kokatakana': u'\u30B3',
 'kokatakanahalfwidth': u'\uFF7A',
 'kooposquare': u'\u331E',
 'koppacyrillic': u'\u0481',
 'koreanstandardsymbol': u'\u327F',
 'koroniscmb': u'\u0343',
 'kparen': u'\u24A6',
 'kpasquare': u'\u33AA',
 'ksicyrillic': u'\u046F',
 'ktsquare': u'\u33CF',
 'kturned': u'\u029E',
 'kuhiragana': u'\u304F',
 'kukatakana': u'\u30AF',
 'kukatakanahalfwidth': u'\uFF78',
 'kvsquare': u'\u33B8',
 'kwsquare': u'\u33BE',
 'l': u'\u006C',
 'labengali': u'\u09B2',
 'lacute': u'\u013A',
 'ladeva': u'\u0932',
 'lagujarati': u'\u0AB2',
 'lagurmukhi': u'\u0A32',
 'lakkhangyaothai': u'\u0E45',
 'lamaleffinalarabic': u'\uFEFC',
 'lamalefhamzaabovefinalarabic': u'\uFEF8',
 'lamalefhamzaaboveisolatedarabic': u'\uFEF7',
 'lamalefhamzabelowfinalarabic': u'\uFEFA',
 'lamalefhamzabelowisolatedarabic': u'\uFEF9',
 'lamalefisolatedarabic': u'\uFEFB',
 'lamalefmaddaabovefinalarabic': u'\uFEF6',
 'lamalefmaddaaboveisolatedarabic': u'\uFEF5',
 'lamarabic': u'\u0644',
 'lambda': u'\u03BB',
 'lambdastroke': u'\u019B',
 'lamed': u'\u05DC',
 'lameddagesh': u'\uFB3C',
 'lameddageshhebrew': u'\uFB3C',
 'lamedhebrew': u'\u05DC',
 'lamedholam': u'\u05DC\u05B9',
 'lamedholamdagesh': u'\u05DC\u05B9\u05BC',
 'lamedholamdageshhebrew': u'\u05DC\u05B9\u05BC',
 'lamedholamhebrew': u'\u05DC\u05B9',
 'lamfinalarabic': u'\uFEDE',
 'lamhahinitialarabic': u'\uFCCA',
 'laminitialarabic': u'\uFEDF',
 'lamjeeminitialarabic': u'\uFCC9',
 'lamkhahinitialarabic': u'\uFCCB',
 'lamlamhehisolatedarabic': u'\uFDF2',
 'lammedialarabic': u'\uFEE0',
 'lammeemhahinitialarabic': u'\uFD88',
 'lammeeminitialarabic': u'\uFCCC',
 'lammeemjeeminitialarabic': u'\uFEDF\uFEE4\uFEA0',
 'lammeemkhahinitialarabic': u'\uFEDF\uFEE4\uFEA8',
 'largecircle': u'\u25EF',
 'lbar': u'\u019A',
 'lbelt': u'\u026C',
 'lbopomofo': u'\u310C',
 'lcaron': u'\u013E',
 'lcedilla': u'\u013C',
 'lcircle': u'\u24DB',
 'lcircumflexbelow': u'\u1E3D',
 'lcommaaccent': u'\u013C',
 'ldot': u'\u0140',
 'ldotaccent': u'\u0140',
 'ldotbelow': u'\u1E37',
 'ldotbelowmacron': u'\u1E39',
 'leftangleabovecmb': u'\u031A',
 'lefttackbelowcmb': u'\u0318',
 'less': u'\u003C',
 'lessequal': u'\u2264',
 'lessequalorgreater': u'\u22DA',
 'lessmonospace': u'\uFF1C',
 'lessorequivalent': u'\u2272',
 'lessorgreater': u'\u2276',
 'lessoverequal': u'\u2266',
 'lesssmall': u'\uFE64',
 'lezh': u'\u026E',
 'lfblock': u'\u258C',
 'lhookretroflex': u'\u026D',
 'lira': u'\u20A4',
 'liwnarmenian': u'\u056C',
 'lj': u'\u01C9',
 'ljecyrillic': u'\u0459',
 'll': u'\uF6C0',
 'lladeva': u'\u0933',
 'llagujarati': u'\u0AB3',
 'llinebelow': u'\u1E3B',
 'llladeva': u'\u0934',
 'llvocalicbengali': u'\u09E1',
 'llvocalicdeva': u'\u0961',
 'llvocalicvowelsignbengali': u'\u09E3',
 'llvocalicvowelsigndeva': u'\u0963',
 'lmiddletilde': u'\u026B',
 'lmonospace': u'\uFF4C',
 'lmsquare': u'\u33D0',
 'lochulathai': u'\u0E2C',
 'logicaland': u'\u2227',
 'logicalnot': u'\u00AC',
 'logicalnotreversed': u'\u2310',
 'logicalor': u'\u2228',
 'lolingthai': u'\u0E25',
 'longs': u'\u017F',
 'lowlinecenterline': u'\uFE4E',
 'lowlinecmb': u'\u0332',
 'lowlinedashed': u'\uFE4D',
 'lozenge': u'\u25CA',
 'lparen': u'\u24A7',
 'lslash': u'\u0142',
 'lsquare': u'\u2113',
 'lsuperior': u'\uF6EE',
 'ltshade': u'\u2591',
 'luthai': u'\u0E26',
 'lvocalicbengali': u'\u098C',
 'lvocalicdeva': u'\u090C',
 'lvocalicvowelsignbengali': u'\u09E2',
 'lvocalicvowelsigndeva': u'\u0962',
 'lxsquare': u'\u33D3',
 'm': u'\u006D',
 'mabengali': u'\u09AE',
 'macron': u'\u00AF',
 'macronbelowcmb': u'\u0331',
 'macroncmb': u'\u0304',
 'macronlowmod': u'\u02CD',
 'macronmonospace': u'\uFFE3',
 'macute': u'\u1E3F',
 'madeva': u'\u092E',
 'magujarati': u'\u0AAE',
 'magurmukhi': u'\u0A2E',
 'mahapakhhebrew': u'\u05A4',
 'mahapakhlefthebrew': u'\u05A4',
 'mahiragana': u'\u307E',
 'maichattawalowleftthai': u'\uF895',
 'maichattawalowrightthai': u'\uF894',
 'maichattawathai': u'\u0E4B',
 'maichattawaupperleftthai': u'\uF893',
 'maieklowleftthai': u'\uF88C',
 'maieklowrightthai': u'\uF88B',
 'maiekthai': u'\u0E48',
 'maiekupperleftthai': u'\uF88A',
 'maihanakatleftthai': u'\uF884',
 'maihanakatthai': u'\u0E31',
 'maitaikhuleftthai': u'\uF889',
 'maitaikhuthai': u'\u0E47',
 'maitholowleftthai': u'\uF88F',
 'maitholowrightthai': u'\uF88E',
 'maithothai': u'\u0E49',
 'maithoupperleftthai': u'\uF88D',
 'maitrilowleftthai': u'\uF892',
 'maitrilowrightthai': u'\uF891',
 'maitrithai': u'\u0E4A',
 'maitriupperleftthai': u'\uF890',
 'maiyamokthai': u'\u0E46',
 'makatakana': u'\u30DE',
 'makatakanahalfwidth': u'\uFF8F',
 'male': u'\u2642',
 'mansyonsquare': u'\u3347',
 'maqafhebrew': u'\u05BE',
 'mars': u'\u2642',
 'masoracirclehebrew': u'\u05AF',
 'masquare': u'\u3383',
 'mbopomofo': u'\u3107',
 'mbsquare': u'\u33D4',
 'mcircle': u'\u24DC',
 'mcubedsquare': u'\u33A5',
 'mdotaccent': u'\u1E41',
 'mdotbelow': u'\u1E43',
 'meemarabic': u'\u0645',
 'meemfinalarabic': u'\uFEE2',
 'meeminitialarabic': u'\uFEE3',
 'meemmedialarabic': u'\uFEE4',
 'meemmeeminitialarabic': u'\uFCD1',
 'meemmeemisolatedarabic': u'\uFC48',
 'meetorusquare': u'\u334D',
 'mehiragana': u'\u3081',
 'meizierasquare': u'\u337E',
 'mekatakana': u'\u30E1',
 'mekatakanahalfwidth': u'\uFF92',
 'mem': u'\u05DE',
 'memdagesh': u'\uFB3E',
 'memdageshhebrew': u'\uFB3E',
 'memhebrew': u'\u05DE',
 'menarmenian': u'\u0574',
 'merkhahebrew': u'\u05A5',
 'merkhakefulahebrew': u'\u05A6',
 'merkhakefulalefthebrew': u'\u05A6',
 'merkhalefthebrew': u'\u05A5',
 'mhook': u'\u0271',
 'mhzsquare': u'\u3392',
 'middledotkatakanahalfwidth': u'\uFF65',
 'middot': u'\u00B7',
 'mieumacirclekorean': u'\u3272',
 'mieumaparenkorean': u'\u3212',
 'mieumcirclekorean': u'\u3264',
 'mieumkorean': u'\u3141',
 'mieumpansioskorean': u'\u3170',
 'mieumparenkorean': u'\u3204',
 'mieumpieupkorean': u'\u316E',
 'mieumsioskorean': u'\u316F',
 'mihiragana': u'\u307F',
 'mikatakana': u'\u30DF',
 'mikatakanahalfwidth': u'\uFF90',
 'minus': u'\u2212',
 'minusbelowcmb': u'\u0320',
 'minuscircle': u'\u2296',
 'minusmod': u'\u02D7',
 'minusplus': u'\u2213',
 'minute': u'\u2032',
 'miribaarusquare': u'\u334A',
 'mirisquare': u'\u3349',
 'mlonglegturned': u'\u0270',
 'mlsquare': u'\u3396',
 'mmcubedsquare': u'\u33A3',
 'mmonospace': u'\uFF4D',
 'mmsquaredsquare': u'\u339F',
 'mohiragana': u'\u3082',
 'mohmsquare': u'\u33C1',
 'mokatakana': u'\u30E2',
 'mokatakanahalfwidth': u'\uFF93',
 'molsquare': u'\u33D6',
 'momathai': u'\u0E21',
 'moverssquare': u'\u33A7',
 'moverssquaredsquare': u'\u33A8',
 'mparen': u'\u24A8',
 'mpasquare': u'\u33AB',
 'mssquare': u'\u33B3',
 'msuperior': u'\uF6EF',
 'mturned': u'\u026F',
 'mu': u'\u00B5',
 'mu1': u'\u00B5',
 'muasquare': u'\u3382',
 'muchgreater': u'\u226B',
 'muchless': u'\u226A',
 'mufsquare': u'\u338C',
 'mugreek': u'\u03BC',
 'mugsquare': u'\u338D',
 'muhiragana': u'\u3080',
 'mukatakana': u'\u30E0',
 'mukatakanahalfwidth': u'\uFF91',
 'mulsquare': u'\u3395',
 'multiply': u'\u00D7',
 'mumsquare': u'\u339B',
 'munahhebrew': u'\u05A3',
 'munahlefthebrew': u'\u05A3',
 'musicalnote': u'\u266A',
 'musicalnotedbl': u'\u266B',
 'musicflatsign': u'\u266D',
 'musicsharpsign': u'\u266F',
 'mussquare': u'\u33B2',
 'muvsquare': u'\u33B6',
 'muwsquare': u'\u33BC',
 'mvmegasquare': u'\u33B9',
 'mvsquare': u'\u33B7',
 'mwmegasquare': u'\u33BF',
 'mwsquare': u'\u33BD',
 'n': u'\u006E',
 'nabengali': u'\u09A8',
 'nabla': u'\u2207',
 'nacute': u'\u0144',
 'nadeva': u'\u0928',
 'nagujarati': u'\u0AA8',
 'nagurmukhi': u'\u0A28',
 'nahiragana': u'\u306A',
 'nakatakana': u'\u30CA',
 'nakatakanahalfwidth': u'\uFF85',
 'napostrophe': u'\u0149',
 'nasquare': u'\u3381',
 'nbopomofo': u'\u310B',
 'nbspace': u'\u00A0',
 'ncaron': u'\u0148',
 'ncedilla': u'\u0146',
 'ncircle': u'\u24DD',
 'ncircumflexbelow': u'\u1E4B',
 'ncommaaccent': u'\u0146',
 'ndotaccent': u'\u1E45',
 'ndotbelow': u'\u1E47',
 'nehiragana': u'\u306D',
 'nekatakana': u'\u30CD',
 'nekatakanahalfwidth': u'\uFF88',
 'newsheqelsign': u'\u20AA',
 'nfsquare': u'\u338B',
 'ngabengali': u'\u0999',
 'ngadeva': u'\u0919',
 'ngagujarati': u'\u0A99',
 'ngagurmukhi': u'\u0A19',
 'ngonguthai': u'\u0E07',
 'nhiragana': u'\u3093',
 'nhookleft': u'\u0272',
 'nhookretroflex': u'\u0273',
 'nieunacirclekorean': u'\u326F',
 'nieunaparenkorean': u'\u320F',
 'nieuncieuckorean': u'\u3135',
 'nieuncirclekorean': u'\u3261',
 'nieunhieuhkorean': u'\u3136',
 'nieunkorean': u'\u3134',
 'nieunpansioskorean': u'\u3168',
 'nieunparenkorean': u'\u3201',
 'nieunsioskorean': u'\u3167',
 'nieuntikeutkorean': u'\u3166',
 'nihiragana': u'\u306B',
 'nikatakana': u'\u30CB',
 'nikatakanahalfwidth': u'\uFF86',
 'nikhahitleftthai': u'\uF899',
 'nikhahitthai': u'\u0E4D',
 'nine': u'\u0039',
 'ninearabic': u'\u0669',
 'ninebengali': u'\u09EF',
 'ninecircle': u'\u2468',
 'ninecircleinversesansserif': u'\u2792',
 'ninedeva': u'\u096F',
 'ninegujarati': u'\u0AEF',
 'ninegurmukhi': u'\u0A6F',
 'ninehackarabic': u'\u0669',
 'ninehangzhou': u'\u3029',
 'nineideographicparen': u'\u3228',
 'nineinferior': u'\u2089',
 'ninemonospace': u'\uFF19',
 'nineoldstyle': u'\uF739',
 'nineparen': u'\u247C',
 'nineperiod': u'\u2490',
 'ninepersian': u'\u06F9',
 'nineroman': u'\u2178',
 'ninesuperior': u'\u2079',
 'nineteencircle': u'\u2472',
 'nineteenparen': u'\u2486',
 'nineteenperiod': u'\u249A',
 'ninethai': u'\u0E59',
 'nj': u'\u01CC',
 'njecyrillic': u'\u045A',
 'nkatakana': u'\u30F3',
 'nkatakanahalfwidth': u'\uFF9D',
 'nlegrightlong': u'\u019E',
 'nlinebelow': u'\u1E49',
 'nmonospace': u'\uFF4E',
 'nmsquare': u'\u339A',
 'nnabengali': u'\u09A3',
 'nnadeva': u'\u0923',
 'nnagujarati': u'\u0AA3',
 'nnagurmukhi': u'\u0A23',
 'nnnadeva': u'\u0929',
 'nohiragana': u'\u306E',
 'nokatakana': u'\u30CE',
 'nokatakanahalfwidth': u'\uFF89',
 'nonbreakingspace': u'\u00A0',
 'nonenthai': u'\u0E13',
 'nonuthai': u'\u0E19',
 'noonarabic': u'\u0646',
 'noonfinalarabic': u'\uFEE6',
 'noonghunnaarabic': u'\u06BA',
 'noonghunnafinalarabic': u'\uFB9F',
 'noonhehinitialarabic': u'\uFEE7\uFEEC',
 'nooninitialarabic': u'\uFEE7',
 'noonjeeminitialarabic': u'\uFCD2',
 'noonjeemisolatedarabic': u'\uFC4B',
 'noonmedialarabic': u'\uFEE8',
 'noonmeeminitialarabic': u'\uFCD5',
 'noonmeemisolatedarabic': u'\uFC4E',
 'noonnoonfinalarabic': u'\uFC8D',
 'notcontains': u'\u220C',
 'notelement': u'\u2209',
 'notelementof': u'\u2209',
 'notequal': u'\u2260',
 'notgreater': u'\u226F',
 'notgreaternorequal': u'\u2271',
 'notgreaternorless': u'\u2279',
 'notidentical': u'\u2262',
 'notless': u'\u226E',
 'notlessnorequal': u'\u2270',
 'notparallel': u'\u2226',
 'notprecedes': u'\u2280',
 'notsubset': u'\u2284',
 'notsucceeds': u'\u2281',
 'notsuperset': u'\u2285',
 'nowarmenian': u'\u0576',
 'nparen': u'\u24A9',
 'nssquare': u'\u33B1',
 'nsuperior': u'\u207F',
 'ntilde': u'\u00F1',
 'nu': u'\u03BD',
 'nuhiragana': u'\u306C',
 'nukatakana': u'\u30CC',
 'nukatakanahalfwidth': u'\uFF87',
 'nuktabengali': u'\u09BC',
 'nuktadeva': u'\u093C',
 'nuktagujarati': u'\u0ABC',
 'nuktagurmukhi': u'\u0A3C',
 'numbersign': u'\u0023',
 'numbersignmonospace': u'\uFF03',
 'numbersignsmall': u'\uFE5F',
 'numeralsigngreek': u'\u0374',
 'numeralsignlowergreek': u'\u0375',
 'numero': u'\u2116',
 'nun': u'\u05E0',
 'nundagesh': u'\uFB40',
 'nundageshhebrew': u'\uFB40',
 'nunhebrew': u'\u05E0',
 'nvsquare': u'\u33B5',
 'nwsquare': u'\u33BB',
 'nyabengali': u'\u099E',
 'nyadeva': u'\u091E',
 'nyagujarati': u'\u0A9E',
 'nyagurmukhi': u'\u0A1E',
 'o': u'\u006F',
 'oacute': u'\u00F3',
 'oangthai': u'\u0E2D',
 'obarred': u'\u0275',
 'obarredcyrillic': u'\u04E9',
 'obarreddieresiscyrillic': u'\u04EB',
 'obengali': u'\u0993',
 'obopomofo': u'\u311B',
 'obreve': u'\u014F',
 'ocandradeva': u'\u0911',
 'ocandragujarati': u'\u0A91',
 'ocandravowelsigndeva': u'\u0949',
 'ocandravowelsigngujarati': u'\u0AC9',
 'ocaron': u'\u01D2',
 'ocircle': u'\u24DE',
 'ocircumflex': u'\u00F4',
 'ocircumflexacute': u'\u1ED1',
 'ocircumflexdotbelow': u'\u1ED9',
 'ocircumflexgrave': u'\u1ED3',
 'ocircumflexhookabove': u'\u1ED5',
 'ocircumflextilde': u'\u1ED7',
 'ocyrillic': u'\u043E',
 'odblacute': u'\u0151',
 'odblgrave': u'\u020D',
 'odeva': u'\u0913',
 'odieresis': u'\u00F6',
 'odieresiscyrillic': u'\u04E7',
 'odotbelow': u'\u1ECD',
 'oe': u'\u0153',
 'oekorean': u'\u315A',
 'ogonek': u'\u02DB',
 'ogonekcmb': u'\u0328',
 'ograve': u'\u00F2',
 'ogujarati': u'\u0A93',
 'oharmenian': u'\u0585',
 'ohiragana': u'\u304A',
 'ohookabove': u'\u1ECF',
 'ohorn': u'\u01A1',
 'ohornacute': u'\u1EDB',
 'ohorndotbelow': u'\u1EE3',
 'ohorngrave': u'\u1EDD',
 'ohornhookabove': u'\u1EDF',
 'ohorntilde': u'\u1EE1',
 'ohungarumlaut': u'\u0151',
 'oi': u'\u01A3',
 'oinvertedbreve': u'\u020F',
 'okatakana': u'\u30AA',
 'okatakanahalfwidth': u'\uFF75',
 'okorean': u'\u3157',
 'olehebrew': u'\u05AB',
 'omacron': u'\u014D',
 'omacronacute': u'\u1E53',
 'omacrongrave': u'\u1E51',
 'omdeva': u'\u0950',
 'omega': u'\u03C9',
 'omega1': u'\u03D6',
 'omegacyrillic': u'\u0461',
 'omegalatinclosed': u'\u0277',
 'omegaroundcyrillic': u'\u047B',
 'omegatitlocyrillic': u'\u047D',
 'omegatonos': u'\u03CE',
 'omgujarati': u'\u0AD0',
 'omicron': u'\u03BF',
 'omicrontonos': u'\u03CC',
 'omonospace': u'\uFF4F',
 'one': u'\u0031',
 'onearabic': u'\u0661',
 'onebengali': u'\u09E7',
 'onecircle': u'\u2460',
 'onecircleinversesansserif': u'\u278A',
 'onedeva': u'\u0967',
 'onedotenleader': u'\u2024',
 'oneeighth': u'\u215B',
 'onefitted': u'\uF6DC',
 'onegujarati': u'\u0AE7',
 'onegurmukhi': u'\u0A67',
 'onehackarabic': u'\u0661',
 'onehalf': u'\u00BD',
 'onehangzhou': u'\u3021',
 'oneideographicparen': u'\u3220',
 'oneinferior': u'\u2081',
 'onemonospace': u'\uFF11',
 'onenumeratorbengali': u'\u09F4',
 'oneoldstyle': u'\uF731',
 'oneparen': u'\u2474',
 'oneperiod': u'\u2488',
 'onepersian': u'\u06F1',
 'onequarter': u'\u00BC',
 'oneroman': u'\u2170',
 'onesuperior': u'\u00B9',
 'onethai': u'\u0E51',
 'onethird': u'\u2153',
 'oogonek': u'\u01EB',
 'oogonekmacron': u'\u01ED',
 'oogurmukhi': u'\u0A13',
 'oomatragurmukhi': u'\u0A4B',
 'oopen': u'\u0254',
 'oparen': u'\u24AA',
 'openbullet': u'\u25E6',
 'option': u'\u2325',
 'ordfeminine': u'\u00AA',
 'ordmasculine': u'\u00BA',
 'orthogonal': u'\u221F',
 'oshortdeva': u'\u0912',
 'oshortvowelsigndeva': u'\u094A',
 'oslash': u'\u00F8',
 'oslashacute': u'\u01FF',
 'osmallhiragana': u'\u3049',
 'osmallkatakana': u'\u30A9',
 'osmallkatakanahalfwidth': u'\uFF6B',
 'ostrokeacute': u'\u01FF',
 'osuperior': u'\uF6F0',
 'otcyrillic': u'\u047F',
 'otilde': u'\u00F5',
 'otildeacute': u'\u1E4D',
 'otildedieresis': u'\u1E4F',
 'oubopomofo': u'\u3121',
 'overline': u'\u203E',
 'overlinecenterline': u'\uFE4A',
 'overlinecmb': u'\u0305',
 'overlinedashed': u'\uFE49',
 'overlinedblwavy': u'\uFE4C',
 'overlinewavy': u'\uFE4B',
 'overscore': u'\u00AF',
 'ovowelsignbengali': u'\u09CB',
 'ovowelsigndeva': u'\u094B',
 'ovowelsigngujarati': u'\u0ACB',
 'p': u'\u0070',
 'paampssquare': u'\u3380',
 'paasentosquare': u'\u332B',
 'pabengali': u'\u09AA',
 'pacute': u'\u1E55',
 'padeva': u'\u092A',
 'pagedown': u'\u21DF',
 'pageup': u'\u21DE',
 'pagujarati': u'\u0AAA',
 'pagurmukhi': u'\u0A2A',
 'pahiragana': u'\u3071',
 'paiyannoithai': u'\u0E2F',
 'pakatakana': u'\u30D1',
 'palatalizationcyrilliccmb': u'\u0484',
 'palochkacyrillic': u'\u04C0',
 'pansioskorean': u'\u317F',
 'paragraph': u'\u00B6',
 'parallel': u'\u2225',
 'parenleft': u'\u0028',
 'parenleftaltonearabic': u'\uFD3E',
 'parenleftbt': u'\uF8ED',
 'parenleftex': u'\uF8EC',
 'parenleftinferior': u'\u208D',
 'parenleftmonospace': u'\uFF08',
 'parenleftsmall': u'\uFE59',
 'parenleftsuperior': u'\u207D',
 'parenlefttp': u'\uF8EB',
 'parenleftvertical': u'\uFE35',
 'parenright': u'\u0029',
 'parenrightaltonearabic': u'\uFD3F',
 'parenrightbt': u'\uF8F8',
 'parenrightex': u'\uF8F7',
 'parenrightinferior': u'\u208E',
 'parenrightmonospace': u'\uFF09',
 'parenrightsmall': u'\uFE5A',
 'parenrightsuperior': u'\u207E',
 'parenrighttp': u'\uF8F6',
 'parenrightvertical': u'\uFE36',
 'partialdiff': u'\u2202',
 'paseqhebrew': u'\u05C0',
 'pashtahebrew': u'\u0599',
 'pasquare': u'\u33A9',
 'patah': u'\u05B7',
 'patah11': u'\u05B7',
 'patah1d': u'\u05B7',
 'patah2a': u'\u05B7',
 'patahhebrew': u'\u05B7',
 'patahnarrowhebrew': u'\u05B7',
 'patahquarterhebrew': u'\u05B7',
 'patahwidehebrew': u'\u05B7',
 'pazerhebrew': u'\u05A1',
 'pbopomofo': u'\u3106',
 'pcircle': u'\u24DF',
 'pdotaccent': u'\u1E57',
 'pe': u'\u05E4',
 'pecyrillic': u'\u043F',
 'pedagesh': u'\uFB44',
 'pedageshhebrew': u'\uFB44',
 'peezisquare': u'\u333B',
 'pefinaldageshhebrew': u'\uFB43',
 'peharabic': u'\u067E',
 'peharmenian': u'\u057A',
 'pehebrew': u'\u05E4',
 'pehfinalarabic': u'\uFB57',
 'pehinitialarabic': u'\uFB58',
 'pehiragana': u'\u307A',
 'pehmedialarabic': u'\uFB59',
 'pekatakana': u'\u30DA',
 'pemiddlehookcyrillic': u'\u04A7',
 'perafehebrew': u'\uFB4E',
 'percent': u'\u0025',
 'percentarabic': u'\u066A',
 'percentmonospace': u'\uFF05',
 'percentsmall': u'\uFE6A',
 'period': u'\u002E',
 'periodarmenian': u'\u0589',
 'periodcentered': u'\u00B7',
 'periodhalfwidth': u'\uFF61',
 'periodinferior': u'\uF6E7',
 'periodmonospace': u'\uFF0E',
 'periodsmall': u'\uFE52',
 'periodsuperior': u'\uF6E8',
 'perispomenigreekcmb': u'\u0342',
 'perpendicular': u'\u22A5',
 'perthousand': u'\u2030',
 'peseta': u'\u20A7',
 'pfsquare': u'\u338A',
 'phabengali': u'\u09AB',
 'phadeva': u'\u092B',
 'phagujarati': u'\u0AAB',
 'phagurmukhi': u'\u0A2B',
 'phi': u'\u03C6',
 'phi1': u'\u03D5',
 'phieuphacirclekorean': u'\u327A',
 'phieuphaparenkorean': u'\u321A',
 'phieuphcirclekorean': u'\u326C',
 'phieuphkorean': u'\u314D',
 'phieuphparenkorean': u'\u320C',
 'philatin': u'\u0278',
 'phinthuthai': u'\u0E3A',
 'phisymbolgreek': u'\u03D5',
 'phook': u'\u01A5',
 'phophanthai': u'\u0E1E',
 'phophungthai': u'\u0E1C',
 'phosamphaothai': u'\u0E20',
 'pi': u'\u03C0',
 'pieupacirclekorean': u'\u3273',
 'pieupaparenkorean': u'\u3213',
 'pieupcieuckorean': u'\u3176',
 'pieupcirclekorean': u'\u3265',
 'pieupkiyeokkorean': u'\u3172',
 'pieupkorean': u'\u3142',
 'pieupparenkorean': u'\u3205',
 'pieupsioskiyeokkorean': u'\u3174',
 'pieupsioskorean': u'\u3144',
 'pieupsiostikeutkorean': u'\u3175',
 'pieupthieuthkorean': u'\u3177',
 'pieuptikeutkorean': u'\u3173',
 'pihiragana': u'\u3074',
 'pikatakana': u'\u30D4',
 'pisymbolgreek': u'\u03D6',
 'piwrarmenian': u'\u0583',
 'plus': u'\u002B',
 'plusbelowcmb': u'\u031F',
 'pluscircle': u'\u2295',
 'plusminus': u'\u00B1',
 'plusmod': u'\u02D6',
 'plusmonospace': u'\uFF0B',
 'plussmall': u'\uFE62',
 'plussuperior': u'\u207A',
 'pmonospace': u'\uFF50',
 'pmsquare': u'\u33D8',
 'pohiragana': u'\u307D',
 'pointingindexdownwhite': u'\u261F',
 'pointingindexleftwhite': u'\u261C',
 'pointingindexrightwhite': u'\u261E',
 'pointingindexupwhite': u'\u261D',
 'pokatakana': u'\u30DD',
 'poplathai': u'\u0E1B',
 'postalmark': u'\u3012',
 'postalmarkface': u'\u3020',
 'pparen': u'\u24AB',
 'precedes': u'\u227A',
 'prescription': u'\u211E',
 'primemod': u'\u02B9',
 'primereversed': u'\u2035',
 'product': u'\u220F',
 'projective': u'\u2305',
 'prolongedkana': u'\u30FC',
 'propellor': u'\u2318',
 'propersubset': u'\u2282',
 'propersuperset': u'\u2283',
 'proportion': u'\u2237',
 'proportional': u'\u221D',
 'psi': u'\u03C8',
 'psicyrillic': u'\u0471',
 'psilipneumatacyrilliccmb': u'\u0486',
 'pssquare': u'\u33B0',
 'puhiragana': u'\u3077',
 'pukatakana': u'\u30D7',
 'pvsquare': u'\u33B4',
 'pwsquare': u'\u33BA',
 'q': u'\u0071',
 'qadeva': u'\u0958',
 'qadmahebrew': u'\u05A8',
 'qafarabic': u'\u0642',
 'qaffinalarabic': u'\uFED6',
 'qafinitialarabic': u'\uFED7',
 'qafmedialarabic': u'\uFED8',
 'qamats': u'\u05B8',
 'qamats10': u'\u05B8',
 'qamats1a': u'\u05B8',
 'qamats1c': u'\u05B8',
 'qamats27': u'\u05B8',
 'qamats29': u'\u05B8',
 'qamats33': u'\u05B8',
 'qamatsde': u'\u05B8',
 'qamatshebrew': u'\u05B8',
 'qamatsnarrowhebrew': u'\u05B8',
 'qamatsqatanhebrew': u'\u05B8',
 'qamatsqatannarrowhebrew': u'\u05B8',
 'qamatsqatanquarterhebrew': u'\u05B8',
 'qamatsqatanwidehebrew': u'\u05B8',
 'qamatsquarterhebrew': u'\u05B8',
 'qamatswidehebrew': u'\u05B8',
 'qarneyparahebrew': u'\u059F',
 'qbopomofo': u'\u3111',
 'qcircle': u'\u24E0',
 'qhook': u'\u02A0',
 'qmonospace': u'\uFF51',
 'qof': u'\u05E7',
 'qofdagesh': u'\uFB47',
 'qofdageshhebrew': u'\uFB47',
 'qofhatafpatah': u'\u05E7\u05B2',
 'qofhatafpatahhebrew': u'\u05E7\u05B2',
 'qofhatafsegol': u'\u05E7\u05B1',
 'qofhatafsegolhebrew': u'\u05E7\u05B1',
 'qofhebrew': u'\u05E7',
 'qofhiriq': u'\u05E7\u05B4',
 'qofhiriqhebrew': u'\u05E7\u05B4',
 'qofholam': u'\u05E7\u05B9',
 'qofholamhebrew': u'\u05E7\u05B9',
 'qofpatah': u'\u05E7\u05B7',
 'qofpatahhebrew': u'\u05E7\u05B7',
 'qofqamats': u'\u05E7\u05B8',
 'qofqamatshebrew': u'\u05E7\u05B8',
 'qofqubuts': u'\u05E7\u05BB',
 'qofqubutshebrew': u'\u05E7\u05BB',
 'qofsegol': u'\u05E7\u05B6',
 'qofsegolhebrew': u'\u05E7\u05B6',
 'qofsheva': u'\u05E7\u05B0',
 'qofshevahebrew': u'\u05E7\u05B0',
 'qoftsere': u'\u05E7\u05B5',
 'qoftserehebrew': u'\u05E7\u05B5',
 'qparen': u'\u24AC',
 'quarternote': u'\u2669',
 'qubuts': u'\u05BB',
 'qubuts18': u'\u05BB',
 'qubuts25': u'\u05BB',
 'qubuts31': u'\u05BB',
 'qubutshebrew': u'\u05BB',
 'qubutsnarrowhebrew': u'\u05BB',
 'qubutsquarterhebrew': u'\u05BB',
 'qubutswidehebrew': u'\u05BB',
 'question': u'\u003F',
 'questionarabic': u'\u061F',
 'questionarmenian': u'\u055E',
 'questiondown': u'\u00BF',
 'questiondownsmall': u'\uF7BF',
 'questiongreek': u'\u037E',
 'questionmonospace': u'\uFF1F',
 'questionsmall': u'\uF73F',
 'quotedbl': u'\u0022',
 'quotedblbase': u'\u201E',
 'quotedblleft': u'\u201C',
 'quotedblmonospace': u'\uFF02',
 'quotedblprime': u'\u301E',
 'quotedblprimereversed': u'\u301D',
 'quotedblright': u'\u201D',
 'quoteleft': u'\u2018',
 'quoteleftreversed': u'\u201B',
 'quotereversed': u'\u201B',
 'quoteright': u'\u2019',
 'quoterightn': u'\u0149',
 'quotesinglbase': u'\u201A',
 'quotesingle': u'\u0027',
 'quotesinglemonospace': u'\uFF07',
 'r': u'\u0072',
 'raarmenian': u'\u057C',
 'rabengali': u'\u09B0',
 'racute': u'\u0155',
 'radeva': u'\u0930',
 'radical': u'\u221A',
 'radicalex': u'\uF8E5',
 'radoverssquare': u'\u33AE',
 'radoverssquaredsquare': u'\u33AF',
 'radsquare': u'\u33AD',
 'rafe': u'\u05BF',
 'rafehebrew': u'\u05BF',
 'ragujarati': u'\u0AB0',
 'ragurmukhi': u'\u0A30',
 'rahiragana': u'\u3089',
 'rakatakana': u'\u30E9',
 'rakatakanahalfwidth': u'\uFF97',
 'ralowerdiagonalbengali': u'\u09F1',
 'ramiddlediagonalbengali': u'\u09F0',
 'ramshorn': u'\u0264',
 'ratio': u'\u2236',
 'rbopomofo': u'\u3116',
 'rcaron': u'\u0159',
 'rcedilla': u'\u0157',
 'rcircle': u'\u24E1',
 'rcommaaccent': u'\u0157',
 'rdblgrave': u'\u0211',
 'rdotaccent': u'\u1E59',
 'rdotbelow': u'\u1E5B',
 'rdotbelowmacron': u'\u1E5D',
 'referencemark': u'\u203B',
 'reflexsubset': u'\u2286',
 'reflexsuperset': u'\u2287',
 'registered': u'\u00AE',
 'registersans': u'\uF8E8',
 'registerserif': u'\uF6DA',
 'reharabic': u'\u0631',
 'reharmenian': u'\u0580',
 'rehfinalarabic': u'\uFEAE',
 'rehiragana': u'\u308C',
 'rehyehaleflamarabic': u'\u0631\uFEF3\uFE8E\u0644',
 'rekatakana': u'\u30EC',
 'rekatakanahalfwidth': u'\uFF9A',
 'resh': u'\u05E8',
 'reshdageshhebrew': u'\uFB48',
 'reshhatafpatah': u'\u05E8\u05B2',
 'reshhatafpatahhebrew': u'\u05E8\u05B2',
 'reshhatafsegol': u'\u05E8\u05B1',
 'reshhatafsegolhebrew': u'\u05E8\u05B1',
 'reshhebrew': u'\u05E8',
 'reshhiriq': u'\u05E8\u05B4',
 'reshhiriqhebrew': u'\u05E8\u05B4',
 'reshholam': u'\u05E8\u05B9',
 'reshholamhebrew': u'\u05E8\u05B9',
 'reshpatah': u'\u05E8\u05B7',
 'reshpatahhebrew': u'\u05E8\u05B7',
 'reshqamats': u'\u05E8\u05B8',
 'reshqamatshebrew': u'\u05E8\u05B8',
 'reshqubuts': u'\u05E8\u05BB',
 'reshqubutshebrew': u'\u05E8\u05BB',
 'reshsegol': u'\u05E8\u05B6',
 'reshsegolhebrew': u'\u05E8\u05B6',
 'reshsheva': u'\u05E8\u05B0',
 'reshshevahebrew': u'\u05E8\u05B0',
 'reshtsere': u'\u05E8\u05B5',
 'reshtserehebrew': u'\u05E8\u05B5',
 'reversedtilde': u'\u223D',
 'reviahebrew': u'\u0597',
 'reviamugrashhebrew': u'\u0597',
 'revlogicalnot': u'\u2310',
 'rfishhook': u'\u027E',
 'rfishhookreversed': u'\u027F',
 'rhabengali': u'\u09DD',
 'rhadeva': u'\u095D',
 'rho': u'\u03C1',
 'rhook': u'\u027D',
 'rhookturned': u'\u027B',
 'rhookturnedsuperior': u'\u02B5',
 'rhosymbolgreek': u'\u03F1',
 'rhotichookmod': u'\u02DE',
 'rieulacirclekorean': u'\u3271',
 'rieulaparenkorean': u'\u3211',
 'rieulcirclekorean': u'\u3263',
 'rieulhieuhkorean': u'\u3140',
 'rieulkiyeokkorean': u'\u313A',
 'rieulkiyeoksioskorean': u'\u3169',
 'rieulkorean': u'\u3139',
 'rieulmieumkorean': u'\u313B',
 'rieulpansioskorean': u'\u316C',
 'rieulparenkorean': u'\u3203',
 'rieulphieuphkorean': u'\u313F',
 'rieulpieupkorean': u'\u313C',
 'rieulpieupsioskorean': u'\u316B',
 'rieulsioskorean': u'\u313D',
 'rieulthieuthkorean': u'\u313E',
 'rieultikeutkorean': u'\u316A',
 'rieulyeorinhieuhkorean': u'\u316D',
 'rightangle': u'\u221F',
 'righttackbelowcmb': u'\u0319',
 'righttriangle': u'\u22BF',
 'rihiragana': u'\u308A',
 'rikatakana': u'\u30EA',
 'rikatakanahalfwidth': u'\uFF98',
 'ring': u'\u02DA',
 'ringbelowcmb': u'\u0325',
 'ringcmb': u'\u030A',
 'ringhalfleft': u'\u02BF',
 'ringhalfleftarmenian': u'\u0559',
 'ringhalfleftbelowcmb': u'\u031C',
 'ringhalfleftcentered': u'\u02D3',
 'ringhalfright': u'\u02BE',
 'ringhalfrightbelowcmb': u'\u0339',
 'ringhalfrightcentered': u'\u02D2',
 'rinvertedbreve': u'\u0213',
 'rittorusquare': u'\u3351',
 'rlinebelow': u'\u1E5F',
 'rlongleg': u'\u027C',
 'rlonglegturned': u'\u027A',
 'rmonospace': u'\uFF52',
 'rohiragana': u'\u308D',
 'rokatakana': u'\u30ED',
 'rokatakanahalfwidth': u'\uFF9B',
 'roruathai': u'\u0E23',
 'rparen': u'\u24AD',
 'rrabengali': u'\u09DC',
 'rradeva': u'\u0931',
 'rragurmukhi': u'\u0A5C',
 'rreharabic': u'\u0691',
 'rrehfinalarabic': u'\uFB8D',
 'rrvocalicbengali': u'\u09E0',
 'rrvocalicdeva': u'\u0960',
 'rrvocalicgujarati': u'\u0AE0',
 'rrvocalicvowelsignbengali': u'\u09C4',
 'rrvocalicvowelsigndeva': u'\u0944',
 'rrvocalicvowelsigngujarati': u'\u0AC4',
 'rsuperior': u'\uF6F1',
 'rtblock': u'\u2590',
 'rturned': u'\u0279',
 'rturnedsuperior': u'\u02B4',
 'ruhiragana': u'\u308B',
 'rukatakana': u'\u30EB',
 'rukatakanahalfwidth': u'\uFF99',
 'rupeemarkbengali': u'\u09F2',
 'rupeesignbengali': u'\u09F3',
 'rupiah': u'\uF6DD',
 'ruthai': u'\u0E24',
 'rvocalicbengali': u'\u098B',
 'rvocalicdeva': u'\u090B',
 'rvocalicgujarati': u'\u0A8B',
 'rvocalicvowelsignbengali': u'\u09C3',
 'rvocalicvowelsigndeva': u'\u0943',
 'rvocalicvowelsigngujarati': u'\u0AC3',
 's': u'\u0073',
 'sabengali': u'\u09B8',
 'sacute': u'\u015B',
 'sacutedotaccent': u'\u1E65',
 'sadarabic': u'\u0635',
 'sadeva': u'\u0938',
 'sadfinalarabic': u'\uFEBA',
 'sadinitialarabic': u'\uFEBB',
 'sadmedialarabic': u'\uFEBC',
 'sagujarati': u'\u0AB8',
 'sagurmukhi': u'\u0A38',
 'sahiragana': u'\u3055',
 'sakatakana': u'\u30B5',
 'sakatakanahalfwidth': u'\uFF7B',
 'sallallahoualayhewasallamarabic': u'\uFDFA',
 'samekh': u'\u05E1',
 'samekhdagesh': u'\uFB41',
 'samekhdageshhebrew': u'\uFB41',
 'samekhhebrew': u'\u05E1',
 'saraaathai': u'\u0E32',
 'saraaethai': u'\u0E41',
 'saraaimaimalaithai': u'\u0E44',
 'saraaimaimuanthai': u'\u0E43',
 'saraamthai': u'\u0E33',
 'saraathai': u'\u0E30',
 'saraethai': u'\u0E40',
 'saraiileftthai': u'\uF886',
 'saraiithai': u'\u0E35',
 'saraileftthai': u'\uF885',
 'saraithai': u'\u0E34',
 'saraothai': u'\u0E42',
 'saraueeleftthai': u'\uF888',
 'saraueethai': u'\u0E37',
 'saraueleftthai': u'\uF887',
 'sarauethai': u'\u0E36',
 'sarauthai': u'\u0E38',
 'sarauuthai': u'\u0E39',
 'sbopomofo': u'\u3119',
 'scaron': u'\u0161',
 'scarondotaccent': u'\u1E67',
 'scedilla': u'\u015F',
 'schwa': u'\u0259',
 'schwacyrillic': u'\u04D9',
 'schwadieresiscyrillic': u'\u04DB',
 'schwahook': u'\u025A',
 'scircle': u'\u24E2',
 'scircumflex': u'\u015D',
 'scommaaccent': u'\u0219',
 'sdotaccent': u'\u1E61',
 'sdotbelow': u'\u1E63',
 'sdotbelowdotaccent': u'\u1E69',
 'seagullbelowcmb': u'\u033C',
 'second': u'\u2033',
 'secondtonechinese': u'\u02CA',
 'section': u'\u00A7',
 'seenarabic': u'\u0633',
 'seenfinalarabic': u'\uFEB2',
 'seeninitialarabic': u'\uFEB3',
 'seenmedialarabic': u'\uFEB4',
 'segol': u'\u05B6',
 'segol13': u'\u05B6',
 'segol1f': u'\u05B6',
 'segol2c': u'\u05B6',
 'segolhebrew': u'\u05B6',
 'segolnarrowhebrew': u'\u05B6',
 'segolquarterhebrew': u'\u05B6',
 'segoltahebrew': u'\u0592',
 'segolwidehebrew': u'\u05B6',
 'seharmenian': u'\u057D',
 'sehiragana': u'\u305B',
 'sekatakana': u'\u30BB',
 'sekatakanahalfwidth': u'\uFF7E',
 'semicolon': u'\u003B',
 'semicolonarabic': u'\u061B',
 'semicolonmonospace': u'\uFF1B',
 'semicolonsmall': u'\uFE54',
 'semivoicedmarkkana': u'\u309C',
 'semivoicedmarkkanahalfwidth': u'\uFF9F',
 'sentisquare': u'\u3322',
 'sentosquare': u'\u3323',
 'seven': u'\u0037',
 'sevenarabic': u'\u0667',
 'sevenbengali': u'\u09ED',
 'sevencircle': u'\u2466',
 'sevencircleinversesansserif': u'\u2790',
 'sevendeva': u'\u096D',
 'seveneighths': u'\u215E',
 'sevengujarati': u'\u0AED',
 'sevengurmukhi': u'\u0A6D',
 'sevenhackarabic': u'\u0667',
 'sevenhangzhou': u'\u3027',
 'sevenideographicparen': u'\u3226',
 'seveninferior': u'\u2087',
 'sevenmonospace': u'\uFF17',
 'sevenoldstyle': u'\uF737',
 'sevenparen': u'\u247A',
 'sevenperiod': u'\u248E',
 'sevenpersian': u'\u06F7',
 'sevenroman': u'\u2176',
 'sevensuperior': u'\u2077',
 'seventeencircle': u'\u2470',
 'seventeenparen': u'\u2484',
 'seventeenperiod': u'\u2498',
 'seventhai': u'\u0E57',
 'sfthyphen': u'\u00AD',
 'shaarmenian': u'\u0577',
 'shabengali': u'\u09B6',
 'shacyrillic': u'\u0448',
 'shaddaarabic': u'\u0651',
 'shaddadammaarabic': u'\uFC61',
 'shaddadammatanarabic': u'\uFC5E',
 'shaddafathaarabic': u'\uFC60',
 'shaddafathatanarabic': u'\u0651\u064B',
 'shaddakasraarabic': u'\uFC62',
 'shaddakasratanarabic': u'\uFC5F',
 'shade': u'\u2592',
 'shadedark': u'\u2593',
 'shadelight': u'\u2591',
 'shademedium': u'\u2592',
 'shadeva': u'\u0936',
 'shagujarati': u'\u0AB6',
 'shagurmukhi': u'\u0A36',
 'shalshelethebrew': u'\u0593',
 'shbopomofo': u'\u3115',
 'shchacyrillic': u'\u0449',
 'sheenarabic': u'\u0634',
 'sheenfinalarabic': u'\uFEB6',
 'sheeninitialarabic': u'\uFEB7',
 'sheenmedialarabic': u'\uFEB8',
 'sheicoptic': u'\u03E3',
 'sheqel': u'\u20AA',
 'sheqelhebrew': u'\u20AA',
 'sheva': u'\u05B0',
 'sheva115': u'\u05B0',
 'sheva15': u'\u05B0',
 'sheva22': u'\u05B0',
 'sheva2e': u'\u05B0',
 'shevahebrew': u'\u05B0',
 'shevanarrowhebrew': u'\u05B0',
 'shevaquarterhebrew': u'\u05B0',
 'shevawidehebrew': u'\u05B0',
 'shhacyrillic': u'\u04BB',
 'shimacoptic': u'\u03ED',
 'shin': u'\u05E9',
 'shindagesh': u'\uFB49',
 'shindageshhebrew': u'\uFB49',
 'shindageshshindot': u'\uFB2C',
 'shindageshshindothebrew': u'\uFB2C',
 'shindageshsindot': u'\uFB2D',
 'shindageshsindothebrew': u'\uFB2D',
 'shindothebrew': u'\u05C1',
 'shinhebrew': u'\u05E9',
 'shinshindot': u'\uFB2A',
 'shinshindothebrew': u'\uFB2A',
 'shinsindot': u'\uFB2B',
 'shinsindothebrew': u'\uFB2B',
 'shook': u'\u0282',
 'sigma': u'\u03C3',
 'sigma1': u'\u03C2',
 'sigmafinal': u'\u03C2',
 'sigmalunatesymbolgreek': u'\u03F2',
 'sihiragana': u'\u3057',
 'sikatakana': u'\u30B7',
 'sikatakanahalfwidth': u'\uFF7C',
 'siluqhebrew': u'\u05BD',
 'siluqlefthebrew': u'\u05BD',
 'similar': u'\u223C',
 'sindothebrew': u'\u05C2',
 'siosacirclekorean': u'\u3274',
 'siosaparenkorean': u'\u3214',
 'sioscieuckorean': u'\u317E',
 'sioscirclekorean': u'\u3266',
 'sioskiyeokkorean': u'\u317A',
 'sioskorean': u'\u3145',
 'siosnieunkorean': u'\u317B',
 'siosparenkorean': u'\u3206',
 'siospieupkorean': u'\u317D',
 'siostikeutkorean': u'\u317C',
 'six': u'\u0036',
 'sixarabic': u'\u0666',
 'sixbengali': u'\u09EC',
 'sixcircle': u'\u2465',
 'sixcircleinversesansserif': u'\u278F',
 'sixdeva': u'\u096C',
 'sixgujarati': u'\u0AEC',
 'sixgurmukhi': u'\u0A6C',
 'sixhackarabic': u'\u0666',
 'sixhangzhou': u'\u3026',
 'sixideographicparen': u'\u3225',
 'sixinferior': u'\u2086',
 'sixmonospace': u'\uFF16',
 'sixoldstyle': u'\uF736',
 'sixparen': u'\u2479',
 'sixperiod': u'\u248D',
 'sixpersian': u'\u06F6',
 'sixroman': u'\u2175',
 'sixsuperior': u'\u2076',
 'sixteencircle': u'\u246F',
 'sixteencurrencydenominatorbengali': u'\u09F9',
 'sixteenparen': u'\u2483',
 'sixteenperiod': u'\u2497',
 'sixthai': u'\u0E56',
 'slash': u'\u002F',
 'slashmonospace': u'\uFF0F',
 'slong': u'\u017F',
 'slongdotaccent': u'\u1E9B',
 'smileface': u'\u263A',
 'smonospace': u'\uFF53',
 'sofpasuqhebrew': u'\u05C3',
 'softhyphen': u'\u00AD',
 'softsigncyrillic': u'\u044C',
 'sohiragana': u'\u305D',
 'sokatakana': u'\u30BD',
 'sokatakanahalfwidth': u'\uFF7F',
 'soliduslongoverlaycmb': u'\u0338',
 'solidusshortoverlaycmb': u'\u0337',
 'sorusithai': u'\u0E29',
 'sosalathai': u'\u0E28',
 'sosothai': u'\u0E0B',
 'sosuathai': u'\u0E2A',
 'space': u'\u0020',
 'spacehackarabic': u'\u0020',
 'spade': u'\u2660',
 'spadesuitblack': u'\u2660',
 'spadesuitwhite': u'\u2664',
 'sparen': u'\u24AE',
 'squarebelowcmb': u'\u033B',
 'squarecc': u'\u33C4',
 'squarecm': u'\u339D',
 'squarediagonalcrosshatchfill': u'\u25A9',
 'squarehorizontalfill': u'\u25A4',
 'squarekg': u'\u338F',
 'squarekm': u'\u339E',
 'squarekmcapital': u'\u33CE',
 'squareln': u'\u33D1',
 'squarelog': u'\u33D2',
 'squaremg': u'\u338E',
 'squaremil': u'\u33D5',
 'squaremm': u'\u339C',
 'squaremsquared': u'\u33A1',
 'squareorthogonalcrosshatchfill': u'\u25A6',
 'squareupperlefttolowerrightfill': u'\u25A7',
 'squareupperrighttolowerleftfill': u'\u25A8',
 'squareverticalfill': u'\u25A5',
 'squarewhitewithsmallblack': u'\u25A3',
 'srsquare': u'\u33DB',
 'ssabengali': u'\u09B7',
 'ssadeva': u'\u0937',
 'ssagujarati': u'\u0AB7',
 'ssangcieuckorean': u'\u3149',
 'ssanghieuhkorean': u'\u3185',
 'ssangieungkorean': u'\u3180',
 'ssangkiyeokkorean': u'\u3132',
 'ssangnieunkorean': u'\u3165',
 'ssangpieupkorean': u'\u3143',
 'ssangsioskorean': u'\u3146',
 'ssangtikeutkorean': u'\u3138',
 'ssuperior': u'\uF6F2',
 'sterling': u'\u00A3',
 'sterlingmonospace': u'\uFFE1',
 'strokelongoverlaycmb': u'\u0336',
 'strokeshortoverlaycmb': u'\u0335',
 'subset': u'\u2282',
 'subsetnotequal': u'\u228A',
 'subsetorequal': u'\u2286',
 'succeeds': u'\u227B',
 'suchthat': u'\u220B',
 'suhiragana': u'\u3059',
 'sukatakana': u'\u30B9',
 'sukatakanahalfwidth': u'\uFF7D',
 'sukunarabic': u'\u0652',
 'summation': u'\u2211',
 'sun': u'\u263C',
 'superset': u'\u2283',
 'supersetnotequal': u'\u228B',
 'supersetorequal': u'\u2287',
 'svsquare': u'\u33DC',
 'syouwaerasquare': u'\u337C',
 't': u'\u0074',
 'tabengali': u'\u09A4',
 'tackdown': u'\u22A4',
 'tackleft': u'\u22A3',
 'tadeva': u'\u0924',
 'tagujarati': u'\u0AA4',
 'tagurmukhi': u'\u0A24',
 'taharabic': u'\u0637',
 'tahfinalarabic': u'\uFEC2',
 'tahinitialarabic': u'\uFEC3',
 'tahiragana': u'\u305F',
 'tahmedialarabic': u'\uFEC4',
 'taisyouerasquare': u'\u337D',
 'takatakana': u'\u30BF',
 'takatakanahalfwidth': u'\uFF80',
 'tatweelarabic': u'\u0640',
 'tau': u'\u03C4',
 'tav': u'\u05EA',
 'tavdages': u'\uFB4A',
 'tavdagesh': u'\uFB4A',
 'tavdageshhebrew': u'\uFB4A',
 'tavhebrew': u'\u05EA',
 'tbar': u'\u0167',
 'tbopomofo': u'\u310A',
 'tcaron': u'\u0165',
 'tccurl': u'\u02A8',
 'tcedilla': u'\u0163',
 'tcheharabic': u'\u0686',
 'tchehfinalarabic': u'\uFB7B',
 'tchehinitialarabic': u'\uFB7C',
 'tchehmedialarabic': u'\uFB7D',
 'tchehmeeminitialarabic': u'\uFB7C\uFEE4',
 'tcircle': u'\u24E3',
 'tcircumflexbelow': u'\u1E71',
 'tcommaaccent': u'\u0163',
 'tdieresis': u'\u1E97',
 'tdotaccent': u'\u1E6B',
 'tdotbelow': u'\u1E6D',
 'tecyrillic': u'\u0442',
 'tedescendercyrillic': u'\u04AD',
 'teharabic': u'\u062A',
 'tehfinalarabic': u'\uFE96',
 'tehhahinitialarabic': u'\uFCA2',
 'tehhahisolatedarabic': u'\uFC0C',
 'tehinitialarabic': u'\uFE97',
 'tehiragana': u'\u3066',
 'tehjeeminitialarabic': u'\uFCA1',
 'tehjeemisolatedarabic': u'\uFC0B',
 'tehmarbutaarabic': u'\u0629',
 'tehmarbutafinalarabic': u'\uFE94',
 'tehmedialarabic': u'\uFE98',
 'tehmeeminitialarabic': u'\uFCA4',
 'tehmeemisolatedarabic': u'\uFC0E',
 'tehnoonfinalarabic': u'\uFC73',
 'tekatakana': u'\u30C6',
 'tekatakanahalfwidth': u'\uFF83',
 'telephone': u'\u2121',
 'telephoneblack': u'\u260E',
 'telishagedolahebrew': u'\u05A0',
 'telishaqetanahebrew': u'\u05A9',
 'tencircle': u'\u2469',
 'tenideographicparen': u'\u3229',
 'tenparen': u'\u247D',
 'tenperiod': u'\u2491',
 'tenroman': u'\u2179',
 'tesh': u'\u02A7',
 'tet': u'\u05D8',
 'tetdagesh': u'\uFB38',
 'tetdageshhebrew': u'\uFB38',
 'tethebrew': u'\u05D8',
 'tetsecyrillic': u'\u04B5',
 'tevirhebrew': u'\u059B',
 'tevirlefthebrew': u'\u059B',
 'thabengali': u'\u09A5',
 'thadeva': u'\u0925',
 'thagujarati': u'\u0AA5',
 'thagurmukhi': u'\u0A25',
 'thalarabic': u'\u0630',
 'thalfinalarabic': u'\uFEAC',
 'thanthakhatlowleftthai': u'\uF898',
 'thanthakhatlowrightthai': u'\uF897',
 'thanthakhatthai': u'\u0E4C',
 'thanthakhatupperleftthai': u'\uF896',
 'theharabic': u'\u062B',
 'thehfinalarabic': u'\uFE9A',
 'thehinitialarabic': u'\uFE9B',
 'thehmedialarabic': u'\uFE9C',
 'thereexists': u'\u2203',
 'therefore': u'\u2234',
 'theta': u'\u03B8',
 'theta1': u'\u03D1',
 'thetasymbolgreek': u'\u03D1',
 'thieuthacirclekorean': u'\u3279',
 'thieuthaparenkorean': u'\u3219',
 'thieuthcirclekorean': u'\u326B',
 'thieuthkorean': u'\u314C',
 'thieuthparenkorean': u'\u320B',
 'thirteencircle': u'\u246C',
 'thirteenparen': u'\u2480',
 'thirteenperiod': u'\u2494',
 'thonangmonthothai': u'\u0E11',
 'thook': u'\u01AD',
 'thophuthaothai': u'\u0E12',
 'thorn': u'\u00FE',
 'thothahanthai': u'\u0E17',
 'thothanthai': u'\u0E10',
 'thothongthai': u'\u0E18',
 'thothungthai': u'\u0E16',
 'thousandcyrillic': u'\u0482',
 'thousandsseparatorarabic': u'\u066C',
 'thousandsseparatorpersian': u'\u066C',
 'three': u'\u0033',
 'threearabic': u'\u0663',
 'threebengali': u'\u09E9',
 'threecircle': u'\u2462',
 'threecircleinversesansserif': u'\u278C',
 'threedeva': u'\u0969',
 'threeeighths': u'\u215C',
 'threegujarati': u'\u0AE9',
 'threegurmukhi': u'\u0A69',
 'threehackarabic': u'\u0663',
 'threehangzhou': u'\u3023',
 'threeideographicparen': u'\u3222',
 'threeinferior': u'\u2083',
 'threemonospace': u'\uFF13',
 'threenumeratorbengali': u'\u09F6',
 'threeoldstyle': u'\uF733',
 'threeparen': u'\u2476',
 'threeperiod': u'\u248A',
 'threepersian': u'\u06F3',
 'threequarters': u'\u00BE',
 'threequartersemdash': u'\uF6DE',
 'threeroman': u'\u2172',
 'threesuperior': u'\u00B3',
 'threethai': u'\u0E53',
 'thzsquare': u'\u3394',
 'tihiragana': u'\u3061',
 'tikatakana': u'\u30C1',
 'tikatakanahalfwidth': u'\uFF81',
 'tikeutacirclekorean': u'\u3270',
 'tikeutaparenkorean': u'\u3210',
 'tikeutcirclekorean': u'\u3262',
 'tikeutkorean': u'\u3137',
 'tikeutparenkorean': u'\u3202',
 'tilde': u'\u02DC',
 'tildebelowcmb': u'\u0330',
 'tildecmb': u'\u0303',
 'tildecomb': u'\u0303',
 'tildedoublecmb': u'\u0360',
 'tildeoperator': u'\u223C',
 'tildeoverlaycmb': u'\u0334',
 'tildeverticalcmb': u'\u033E',
 'timescircle': u'\u2297',
 'tipehahebrew': u'\u0596',
 'tipehalefthebrew': u'\u0596',
 'tippigurmukhi': u'\u0A70',
 'titlocyrilliccmb': u'\u0483',
 'tiwnarmenian': u'\u057F',
 'tlinebelow': u'\u1E6F',
 'tmonospace': u'\uFF54',
 'toarmenian': u'\u0569',
 'tohiragana': u'\u3068',
 'tokatakana': u'\u30C8',
 'tokatakanahalfwidth': u'\uFF84',
 'tonebarextrahighmod': u'\u02E5',
 'tonebarextralowmod': u'\u02E9',
 'tonebarhighmod': u'\u02E6',
 'tonebarlowmod': u'\u02E8',
 'tonebarmidmod': u'\u02E7',
 'tonefive': u'\u01BD',
 'tonesix': u'\u0185',
 'tonetwo': u'\u01A8',
 'tonos': u'\u0384',
 'tonsquare': u'\u3327',
 'topatakthai': u'\u0E0F',
 'tortoiseshellbracketleft': u'\u3014',
 'tortoiseshellbracketleftsmall': u'\uFE5D',
 'tortoiseshellbracketleftvertical': u'\uFE39',
 'tortoiseshellbracketright': u'\u3015',
 'tortoiseshellbracketrightsmall': u'\uFE5E',
 'tortoiseshellbracketrightvertical': u'\uFE3A',
 'totaothai': u'\u0E15',
 'tpalatalhook': u'\u01AB',
 'tparen': u'\u24AF',
 'trademark': u'\u2122',
 'trademarksans': u'\uF8EA',
 'trademarkserif': u'\uF6DB',
 'tretroflexhook': u'\u0288',
 'triagdn': u'\u25BC',
 'triaglf': u'\u25C4',
 'triagrt': u'\u25BA',
 'triagup': u'\u25B2',
 'ts': u'\u02A6',
 'tsadi': u'\u05E6',
 'tsadidagesh': u'\uFB46',
 'tsadidageshhebrew': u'\uFB46',
 'tsadihebrew': u'\u05E6',
 'tsecyrillic': u'\u0446',
 'tsere': u'\u05B5',
 'tsere12': u'\u05B5',
 'tsere1e': u'\u05B5',
 'tsere2b': u'\u05B5',
 'tserehebrew': u'\u05B5',
 'tserenarrowhebrew': u'\u05B5',
 'tserequarterhebrew': u'\u05B5',
 'tserewidehebrew': u'\u05B5',
 'tshecyrillic': u'\u045B',
 'tsuperior': u'\uF6F3',
 'ttabengali': u'\u099F',
 'ttadeva': u'\u091F',
 'ttagujarati': u'\u0A9F',
 'ttagurmukhi': u'\u0A1F',
 'tteharabic': u'\u0679',
 'ttehfinalarabic': u'\uFB67',
 'ttehinitialarabic': u'\uFB68',
 'ttehmedialarabic': u'\uFB69',
 'tthabengali': u'\u09A0',
 'tthadeva': u'\u0920',
 'tthagujarati': u'\u0AA0',
 'tthagurmukhi': u'\u0A20',
 'tturned': u'\u0287',
 'tuhiragana': u'\u3064',
 'tukatakana': u'\u30C4',
 'tukatakanahalfwidth': u'\uFF82',
 'tusmallhiragana': u'\u3063',
 'tusmallkatakana': u'\u30C3',
 'tusmallkatakanahalfwidth': u'\uFF6F',
 'twelvecircle': u'\u246B',
 'twelveparen': u'\u247F',
 'twelveperiod': u'\u2493',
 'twelveroman': u'\u217B',
 'twentycircle': u'\u2473',
 'twentyhangzhou': u'\u5344',
 'twentyparen': u'\u2487',
 'twentyperiod': u'\u249B',
 'two': u'\u0032',
 'twoarabic': u'\u0662',
 'twobengali': u'\u09E8',
 'twocircle': u'\u2461',
 'twocircleinversesansserif': u'\u278B',
 'twodeva': u'\u0968',
 'twodotenleader': u'\u2025',
 'twodotleader': u'\u2025',
 'twodotleadervertical': u'\uFE30',
 'twogujarati': u'\u0AE8',
 'twogurmukhi': u'\u0A68',
 'twohackarabic': u'\u0662',
 'twohangzhou': u'\u3022',
 'twoideographicparen': u'\u3221',
 'twoinferior': u'\u2082',
 'twomonospace': u'\uFF12',
 'twonumeratorbengali': u'\u09F5',
 'twooldstyle': u'\uF732',
 'twoparen': u'\u2475',
 'twoperiod': u'\u2489',
 'twopersian': u'\u06F2',
 'tworoman': u'\u2171',
 'twostroke': u'\u01BB',
 'twosuperior': u'\u00B2',
 'twothai': u'\u0E52',
 'twothirds': u'\u2154',
 'u': u'\u0075',
 'uacute': u'\u00FA',
 'ubar': u'\u0289',
 'ubengali': u'\u0989',
 'ubopomofo': u'\u3128',
 'ubreve': u'\u016D',
 'ucaron': u'\u01D4',
 'ucircle': u'\u24E4',
 'ucircumflex': u'\u00FB',
 'ucircumflexbelow': u'\u1E77',
 'ucyrillic': u'\u0443',
 'udattadeva': u'\u0951',
 'udblacute': u'\u0171',
 'udblgrave': u'\u0215',
 'udeva': u'\u0909',
 'udieresis': u'\u00FC',
 'udieresisacute': u'\u01D8',
 'udieresisbelow': u'\u1E73',
 'udieresiscaron': u'\u01DA',
 'udieresiscyrillic': u'\u04F1',
 'udieresisgrave': u'\u01DC',
 'udieresismacron': u'\u01D6',
 'udotbelow': u'\u1EE5',
 'ugrave': u'\u00F9',
 'ugujarati': u'\u0A89',
 'ugurmukhi': u'\u0A09',
 'uhiragana': u'\u3046',
 'uhookabove': u'\u1EE7',
 'uhorn': u'\u01B0',
 'uhornacute': u'\u1EE9',
 'uhorndotbelow': u'\u1EF1',
 'uhorngrave': u'\u1EEB',
 'uhornhookabove': u'\u1EED',
 'uhorntilde': u'\u1EEF',
 'uhungarumlaut': u'\u0171',
 'uhungarumlautcyrillic': u'\u04F3',
 'uinvertedbreve': u'\u0217',
 'ukatakana': u'\u30A6',
 'ukatakanahalfwidth': u'\uFF73',
 'ukcyrillic': u'\u0479',
 'ukorean': u'\u315C',
 'umacron': u'\u016B',
 'umacroncyrillic': u'\u04EF',
 'umacrondieresis': u'\u1E7B',
 'umatragurmukhi': u'\u0A41',
 'umonospace': u'\uFF55',
 'underscore': u'\u005F',
 'underscoredbl': u'\u2017',
 'underscoremonospace': u'\uFF3F',
 'underscorevertical': u'\uFE33',
 'underscorewavy': u'\uFE4F',
 'union': u'\u222A',
 'universal': u'\u2200',
 'uogonek': u'\u0173',
 'uparen': u'\u24B0',
 'upblock': u'\u2580',
 'upperdothebrew': u'\u05C4',
 'upsilon': u'\u03C5',
 'upsilondieresis': u'\u03CB',
 'upsilondieresistonos': u'\u03B0',
 'upsilonlatin': u'\u028A',
 'upsilontonos': u'\u03CD',
 'uptackbelowcmb': u'\u031D',
 'uptackmod': u'\u02D4',
 'uragurmukhi': u'\u0A73',
 'uring': u'\u016F',
 'ushortcyrillic': u'\u045E',
 'usmallhiragana': u'\u3045',
 'usmallkatakana': u'\u30A5',
 'usmallkatakanahalfwidth': u'\uFF69',
 'ustraightcyrillic': u'\u04AF',
 'ustraightstrokecyrillic': u'\u04B1',
 'utilde': u'\u0169',
 'utildeacute': u'\u1E79',
 'utildebelow': u'\u1E75',
 'uubengali': u'\u098A',
 'uudeva': u'\u090A',
 'uugujarati': u'\u0A8A',
 'uugurmukhi': u'\u0A0A',
 'uumatragurmukhi': u'\u0A42',
 'uuvowelsignbengali': u'\u09C2',
 'uuvowelsigndeva': u'\u0942',
 'uuvowelsigngujarati': u'\u0AC2',
 'uvowelsignbengali': u'\u09C1',
 'uvowelsigndeva': u'\u0941',
 'uvowelsigngujarati': u'\u0AC1',
 'v': u'\u0076',
 'vadeva': u'\u0935',
 'vagujarati': u'\u0AB5',
 'vagurmukhi': u'\u0A35',
 'vakatakana': u'\u30F7',
 'vav': u'\u05D5',
 'vavdagesh': u'\uFB35',
 'vavdagesh65': u'\uFB35',
 'vavdageshhebrew': u'\uFB35',
 'vavhebrew': u'\u05D5',
 'vavholam': u'\uFB4B',
 'vavholamhebrew': u'\uFB4B',
 'vavvavhebrew': u'\u05F0',
 'vavyodhebrew': u'\u05F1',
 'vcircle': u'\u24E5',
 'vdotbelow': u'\u1E7F',
 'vecyrillic': u'\u0432',
 'veharabic': u'\u06A4',
 'vehfinalarabic': u'\uFB6B',
 'vehinitialarabic': u'\uFB6C',
 'vehmedialarabic': u'\uFB6D',
 'vekatakana': u'\u30F9',
 'venus': u'\u2640',
 'verticalbar': u'\u007C',
 'verticallineabovecmb': u'\u030D',
 'verticallinebelowcmb': u'\u0329',
 'verticallinelowmod': u'\u02CC',
 'verticallinemod': u'\u02C8',
 'vewarmenian': u'\u057E',
 'vhook': u'\u028B',
 'vikatakana': u'\u30F8',
 'viramabengali': u'\u09CD',
 'viramadeva': u'\u094D',
 'viramagujarati': u'\u0ACD',
 'visargabengali': u'\u0983',
 'visargadeva': u'\u0903',
 'visargagujarati': u'\u0A83',
 'vmonospace': u'\uFF56',
 'voarmenian': u'\u0578',
 'voicediterationhiragana': u'\u309E',
 'voicediterationkatakana': u'\u30FE',
 'voicedmarkkana': u'\u309B',
 'voicedmarkkanahalfwidth': u'\uFF9E',
 'vokatakana': u'\u30FA',
 'vparen': u'\u24B1',
 'vtilde': u'\u1E7D',
 'vturned': u'\u028C',
 'vuhiragana': u'\u3094',
 'vukatakana': u'\u30F4',
 'w': u'\u0077',
 'wacute': u'\u1E83',
 'waekorean': u'\u3159',
 'wahiragana': u'\u308F',
 'wakatakana': u'\u30EF',
 'wakatakanahalfwidth': u'\uFF9C',
 'wakorean': u'\u3158',
 'wasmallhiragana': u'\u308E',
 'wasmallkatakana': u'\u30EE',
 'wattosquare': u'\u3357',
 'wavedash': u'\u301C',
 'wavyunderscorevertical': u'\uFE34',
 'wawarabic': u'\u0648',
 'wawfinalarabic': u'\uFEEE',
 'wawhamzaabovearabic': u'\u0624',
 'wawhamzaabovefinalarabic': u'\uFE86',
 'wbsquare': u'\u33DD',
 'wcircle': u'\u24E6',
 'wcircumflex': u'\u0175',
 'wdieresis': u'\u1E85',
 'wdotaccent': u'\u1E87',
 'wdotbelow': u'\u1E89',
 'wehiragana': u'\u3091',
 'weierstrass': u'\u2118',
 'wekatakana': u'\u30F1',
 'wekorean': u'\u315E',
 'weokorean': u'\u315D',
 'wgrave': u'\u1E81',
 'whitebullet': u'\u25E6',
 'whitecircle': u'\u25CB',
 'whitecircleinverse': u'\u25D9',
 'whitecornerbracketleft': u'\u300E',
 'whitecornerbracketleftvertical': u'\uFE43',
 'whitecornerbracketright': u'\u300F',
 'whitecornerbracketrightvertical': u'\uFE44',
 'whitediamond': u'\u25C7',
 'whitediamondcontainingblacksmalldiamond': u'\u25C8',
 'whitedownpointingsmalltriangle': u'\u25BF',
 'whitedownpointingtriangle': u'\u25BD',
 'whiteleftpointingsmalltriangle': u'\u25C3',
 'whiteleftpointingtriangle': u'\u25C1',
 'whitelenticularbracketleft': u'\u3016',
 'whitelenticularbracketright': u'\u3017',
 'whiterightpointingsmalltriangle': u'\u25B9',
 'whiterightpointingtriangle': u'\u25B7',
 'whitesmallsquare': u'\u25AB',
 'whitesmilingface': u'\u263A',
 'whitesquare': u'\u25A1',
 'whitestar': u'\u2606',
 'whitetelephone': u'\u260F',
 'whitetortoiseshellbracketleft': u'\u3018',
 'whitetortoiseshellbracketright': u'\u3019',
 'whiteuppointingsmalltriangle': u'\u25B5',
 'whiteuppointingtriangle': u'\u25B3',
 'wihiragana': u'\u3090',
 'wikatakana': u'\u30F0',
 'wikorean': u'\u315F',
 'wmonospace': u'\uFF57',
 'wohiragana': u'\u3092',
 'wokatakana': u'\u30F2',
 'wokatakanahalfwidth': u'\uFF66',
 'won': u'\u20A9',
 'wonmonospace': u'\uFFE6',
 'wowaenthai': u'\u0E27',
 'wparen': u'\u24B2',
 'wring': u'\u1E98',
 'wsuperior': u'\u02B7',
 'wturned': u'\u028D',
 'wynn': u'\u01BF',
 'x': u'\u0078',
 'xabovecmb': u'\u033D',
 'xbopomofo': u'\u3112',
 'xcircle': u'\u24E7',
 'xdieresis': u'\u1E8D',
 'xdotaccent': u'\u1E8B',
 'xeharmenian': u'\u056D',
 'xi': u'\u03BE',
 'xmonospace': u'\uFF58',
 'xparen': u'\u24B3',
 'xsuperior': u'\u02E3',
 'y': u'\u0079',
 'yaadosquare': u'\u334E',
 'yabengali': u'\u09AF',
 'yacute': u'\u00FD',
 'yadeva': u'\u092F',
 'yaekorean': u'\u3152',
 'yagujarati': u'\u0AAF',
 'yagurmukhi': u'\u0A2F',
 'yahiragana': u'\u3084',
 'yakatakana': u'\u30E4',
 'yakatakanahalfwidth': u'\uFF94',
 'yakorean': u'\u3151',
 'yamakkanthai': u'\u0E4E',
 'yasmallhiragana': u'\u3083',
 'yasmallkatakana': u'\u30E3',
 'yasmallkatakanahalfwidth': u'\uFF6C',
 'yatcyrillic': u'\u0463',
 'ycircle': u'\u24E8',
 'ycircumflex': u'\u0177',
 'ydieresis': u'\u00FF',
 'ydotaccent': u'\u1E8F',
 'ydotbelow': u'\u1EF5',
 'yeharabic': u'\u064A',
 'yehbarreearabic': u'\u06D2',
 'yehbarreefinalarabic': u'\uFBAF',
 'yehfinalarabic': u'\uFEF2',
 'yehhamzaabovearabic': u'\u0626',
 'yehhamzaabovefinalarabic': u'\uFE8A',
 'yehhamzaaboveinitialarabic': u'\uFE8B',
 'yehhamzaabovemedialarabic': u'\uFE8C',
 'yehinitialarabic': u'\uFEF3',
 'yehmedialarabic': u'\uFEF4',
 'yehmeeminitialarabic': u'\uFCDD',
 'yehmeemisolatedarabic': u'\uFC58',
 'yehnoonfinalarabic': u'\uFC94',
 'yehthreedotsbelowarabic': u'\u06D1',
 'yekorean': u'\u3156',
 'yen': u'\u00A5',
 'yenmonospace': u'\uFFE5',
 'yeokorean': u'\u3155',
 'yeorinhieuhkorean': u'\u3186',
 'yerahbenyomohebrew': u'\u05AA',
 'yerahbenyomolefthebrew': u'\u05AA',
 'yericyrillic': u'\u044B',
 'yerudieresiscyrillic': u'\u04F9',
 'yesieungkorean': u'\u3181',
 'yesieungpansioskorean': u'\u3183',
 'yesieungsioskorean': u'\u3182',
 'yetivhebrew': u'\u059A',
 'ygrave': u'\u1EF3',
 'yhook': u'\u01B4',
 'yhookabove': u'\u1EF7',
 'yiarmenian': u'\u0575',
 'yicyrillic': u'\u0457',
 'yikorean': u'\u3162',
 'yinyang': u'\u262F',
 'yiwnarmenian': u'\u0582',
 'ymonospace': u'\uFF59',
 'yod': u'\u05D9',
 'yoddagesh': u'\uFB39',
 'yoddageshhebrew': u'\uFB39',
 'yodhebrew': u'\u05D9',
 'yodyodhebrew': u'\u05F2',
 'yodyodpatahhebrew': u'\uFB1F',
 'yohiragana': u'\u3088',
 'yoikorean': u'\u3189',
 'yokatakana': u'\u30E8',
 'yokatakanahalfwidth': u'\uFF96',
 'yokorean': u'\u315B',
 'yosmallhiragana': u'\u3087',
 'yosmallkatakana': u'\u30E7',
 'yosmallkatakanahalfwidth': u'\uFF6E',
 'yotgreek': u'\u03F3',
 'yoyaekorean': u'\u3188',
 'yoyakorean': u'\u3187',
 'yoyakthai': u'\u0E22',
 'yoyingthai': u'\u0E0D',
 'yparen': u'\u24B4',
 'ypogegrammeni': u'\u037A',
 'ypogegrammenigreekcmb': u'\u0345',
 'yr': u'\u01A6',
 'yring': u'\u1E99',
 'ysuperior': u'\u02B8',
 'ytilde': u'\u1EF9',
 'yturned': u'\u028E',
 'yuhiragana': u'\u3086',
 'yuikorean': u'\u318C',
 'yukatakana': u'\u30E6',
 'yukatakanahalfwidth': u'\uFF95',
 'yukorean': u'\u3160',
 'yusbigcyrillic': u'\u046B',
 'yusbigiotifiedcyrillic': u'\u046D',
 'yuslittlecyrillic': u'\u0467',
 'yuslittleiotifiedcyrillic': u'\u0469',
 'yusmallhiragana': u'\u3085',
 'yusmallkatakana': u'\u30E5',
 'yusmallkatakanahalfwidth': u'\uFF6D',
 'yuyekorean': u'\u318B',
 'yuyeokorean': u'\u318A',
 'yyabengali': u'\u09DF',
 'yyadeva': u'\u095F',
 'z': u'\u007A',
 'zaarmenian': u'\u0566',
 'zacute': u'\u017A',
 'zadeva': u'\u095B',
 'zagurmukhi': u'\u0A5B',
 'zaharabic': u'\u0638',
 'zahfinalarabic': u'\uFEC6',
 'zahinitialarabic': u'\uFEC7',
 'zahiragana': u'\u3056',
 'zahmedialarabic': u'\uFEC8',
 'zainarabic': u'\u0632',
 'zainfinalarabic': u'\uFEB0',
 'zakatakana': u'\u30B6',
 'zaqefgadolhebrew': u'\u0595',
 'zaqefqatanhebrew': u'\u0594',
 'zarqahebrew': u'\u0598',
 'zayin': u'\u05D6',
 'zayindagesh': u'\uFB36',
 'zayindageshhebrew': u'\uFB36',
 'zayinhebrew': u'\u05D6',
 'zbopomofo': u'\u3117',
 'zcaron': u'\u017E',
 'zcircle': u'\u24E9',
 'zcircumflex': u'\u1E91',
 'zcurl': u'\u0291',
 'zdot': u'\u017C',
 'zdotaccent': u'\u017C',
 'zdotbelow': u'\u1E93',
 'zecyrillic': u'\u0437',
 'zedescendercyrillic': u'\u0499',
 'zedieresiscyrillic': u'\u04DF',
 'zehiragana': u'\u305C',
 'zekatakana': u'\u30BC',
 'zero': u'\u0030',
 'zeroarabic': u'\u0660',
 'zerobengali': u'\u09E6',
 'zerodeva': u'\u0966',
 'zerogujarati': u'\u0AE6',
 'zerogurmukhi': u'\u0A66',
 'zerohackarabic': u'\u0660',
 'zeroinferior': u'\u2080',
 'zeromonospace': u'\uFF10',
 'zerooldstyle': u'\uF730',
 'zeropersian': u'\u06F0',
 'zerosuperior': u'\u2070',
 'zerothai': u'\u0E50',
 'zerowidthjoiner': u'\uFEFF',
 'zerowidthnonjoiner': u'\u200C',
 'zerowidthspace': u'\u200B',
 'zeta': u'\u03B6',
 'zhbopomofo': u'\u3113',
 'zhearmenian': u'\u056A',
 'zhebrevecyrillic': u'\u04C2',
 'zhecyrillic': u'\u0436',
 'zhedescendercyrillic': u'\u0497',
 'zhedieresiscyrillic': u'\u04DD',
 'zihiragana': u'\u3058',
 'zikatakana': u'\u30B8',
 'zinorhebrew': u'\u05AE',
 'zlinebelow': u'\u1E95',
 'zmonospace': u'\uFF5A',
 'zohiragana': u'\u305E',
 'zokatakana': u'\u30BE',
 'zparen': u'\u24B5',
 'zretroflexhook': u'\u0290',
 'zstroke': u'\u01B6',
 'zuhiragana': u'\u305A',
 'zukatakana': u'\u30BA',
}
#--end

########NEW FILE########
__FILENAME__ = image
#!/usr/bin/env python
import cStringIO
import struct
import os, os.path
from pdftypes import LITERALS_DCT_DECODE
from pdfcolor import LITERAL_DEVICE_GRAY, LITERAL_DEVICE_RGB, LITERAL_DEVICE_CMYK


def align32(x):
    return ((x+3)//4)*4


##  BMPWriter
##
class BMPWriter(object):

    def __init__(self, fp, bits, width, height):
        self.fp = fp
        self.bits = bits
        self.width = width
        self.height = height
        if bits == 1:
            ncols = 2
        elif bits == 8:
            ncols = 256
        elif bits == 24:
            ncols = 0
        else:
            raise ValueError(bits)
        self.linesize = align32((self.width*self.bits+7)//8)
        self.datasize = self.linesize * self.height
        headersize = 14+40+ncols*4
        info = struct.pack('<IiiHHIIIIII', 40, self.width, self.height, 1, self.bits, 0, self.datasize, 0, 0, ncols, 0)
        assert len(info) == 40, len(info)
        header = struct.pack('<ccIHHI', 'B', 'M', headersize+self.datasize, 0, 0, headersize)
        assert len(header) == 14, len(header)
        self.fp.write(header)
        self.fp.write(info)
        if ncols == 2:
            # B&W color table
            for i in (0, 255):
                self.fp.write(struct.pack('BBBx', i, i, i))
        elif ncols == 256:
            # grayscale color table
            for i in xrange(256):
                self.fp.write(struct.pack('BBBx', i, i, i))
        self.pos0 = self.fp.tell()
        self.pos1 = self.pos0 + self.datasize
        return

    def write_line(self, y, data):
        self.fp.seek(self.pos1 - (y+1)*self.linesize)
        self.fp.write(data)
        return


##  ImageWriter
##
class ImageWriter(object):

    def __init__(self, outdir):
        self.outdir = outdir
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        return

    def export_image(self, image):
        stream = image.stream
        filters = stream.get_filters()
        (width, height) = image.srcsize
        if len(filters) == 1 and filters[0] in LITERALS_DCT_DECODE:
            ext = '.jpg'
        elif (image.bits == 1 or
              image.bits == 8 and image.colorspace in (LITERAL_DEVICE_RGB, LITERAL_DEVICE_GRAY)):
            ext = '.%dx%d.bmp' % (width, height)
        else:
            ext = '.%d.%dx%d.img' % (image.bits, width, height)
        name = image.name+ext
        path = os.path.join(self.outdir, name)
        fp = file(path, 'wb')
        if ext == '.jpg':
            raw_data = stream.get_rawdata()
            if LITERAL_DEVICE_CMYK in image.colorspace:
                from PIL import Image
                from PIL import ImageChops
                ifp = cStringIO.StringIO(raw_data)
                i = Image.open(ifp)
                i = ImageChops.invert(i)
                i = i.convert('RGB')
                i.save(fp, 'JPEG')
            else:
                fp.write(raw_data)
        elif image.bits == 1:
            bmp = BMPWriter(fp, 1, width, height)
            data = stream.get_data()
            i = 0
            width = (width+7)//8
            for y in xrange(height):
                bmp.write_line(y, data[i:i+width])
                i += width
        elif image.bits == 8 and image.colorspace is LITERAL_DEVICE_RGB:
            bmp = BMPWriter(fp, 24, width, height)
            data = stream.get_data()
            i = 0
            width = width*3
            for y in xrange(height):
                bmp.write_line(y, data[i:i+width])
                i += width
        elif image.bits == 8 and image.colorspace is LITERAL_DEVICE_GRAY:
            bmp = BMPWriter(fp, 8, width, height)
            data = stream.get_data()
            i = 0
            for y in xrange(height):
                bmp.write_line(y, data[i:i+width])
                i += width
        else:
            fp.write(stream.get_data())
        fp.close()
        return name

########NEW FILE########
__FILENAME__ = latin_enc
#!/usr/bin/env python

""" Standard encoding tables used in PDF.

This table is extracted from PDF Reference Manual 1.6, pp.925
  "D.1 Latin Character Set and Encodings"

"""

ENCODING = [
  # (name, std, mac, win, pdf)
  ('A', 65, 65, 65, 65),
  ('AE', 225, 174, 198, 198),
  ('Aacute', None, 231, 193, 193),
  ('Acircumflex', None, 229, 194, 194),
  ('Adieresis', None, 128, 196, 196),
  ('Agrave', None, 203, 192, 192),
  ('Aring', None, 129, 197, 197),
  ('Atilde', None, 204, 195, 195),
  ('B', 66, 66, 66, 66),
  ('C', 67, 67, 67, 67),
  ('Ccedilla', None, 130, 199, 199),
  ('D', 68, 68, 68, 68),
  ('E', 69, 69, 69, 69),
  ('Eacute', None, 131, 201, 201),
  ('Ecircumflex', None, 230, 202, 202),
  ('Edieresis', None, 232, 203, 203),
  ('Egrave', None, 233, 200, 200),
  ('Eth', None, None, 208, 208),
  ('Euro', None, None, 128, 160),
  ('F', 70, 70, 70, 70),
  ('G', 71, 71, 71, 71),
  ('H', 72, 72, 72, 72),
  ('I', 73, 73, 73, 73),
  ('Iacute', None, 234, 205, 205),
  ('Icircumflex', None, 235, 206, 206),
  ('Idieresis', None, 236, 207, 207),
  ('Igrave', None, 237, 204, 204),
  ('J', 74, 74, 74, 74),
  ('K', 75, 75, 75, 75),
  ('L', 76, 76, 76, 76),
  ('Lslash', 232, None, None, 149),
  ('M', 77, 77, 77, 77),
  ('N', 78, 78, 78, 78),
  ('Ntilde', None, 132, 209, 209),
  ('O', 79, 79, 79, 79),
  ('OE', 234, 206, 140, 150),
  ('Oacute', None, 238, 211, 211),
  ('Ocircumflex', None, 239, 212, 212),
  ('Odieresis', None, 133, 214, 214),
  ('Ograve', None, 241, 210, 210),
  ('Oslash', 233, 175, 216, 216),
  ('Otilde', None, 205, 213, 213),
  ('P', 80, 80, 80, 80),
  ('Q', 81, 81, 81, 81),
  ('R', 82, 82, 82, 82),
  ('S', 83, 83, 83, 83),
  ('Scaron', None, None, 138, 151),
  ('T', 84, 84, 84, 84),
  ('Thorn', None, None, 222, 222),
  ('U', 85, 85, 85, 85),
  ('Uacute', None, 242, 218, 218),
  ('Ucircumflex', None, 243, 219, 219),
  ('Udieresis', None, 134, 220, 220),
  ('Ugrave', None, 244, 217, 217),
  ('V', 86, 86, 86, 86),
  ('W', 87, 87, 87, 87),
  ('X', 88, 88, 88, 88),
  ('Y', 89, 89, 89, 89),
  ('Yacute', None, None, 221, 221),
  ('Ydieresis', None, 217, 159, 152),
  ('Z', 90, 90, 90, 90),
  ('Zcaron', None, None, 142, 153),
  ('a', 97, 97, 97, 97),
  ('aacute', None, 135, 225, 225),
  ('acircumflex', None, 137, 226, 226),
  ('acute', 194, 171, 180, 180),
  ('adieresis', None, 138, 228, 228),
  ('ae', 241, 190, 230, 230),
  ('agrave', None, 136, 224, 224),
  ('ampersand', 38, 38, 38, 38),
  ('aring', None, 140, 229, 229),
  ('asciicircum', 94, 94, 94, 94),
  ('asciitilde', 126, 126, 126, 126),
  ('asterisk', 42, 42, 42, 42),
  ('at', 64, 64, 64, 64),
  ('atilde', None, 139, 227, 227),
  ('b', 98, 98, 98, 98),
  ('backslash', 92, 92, 92, 92),
  ('bar', 124, 124, 124, 124),
  ('braceleft', 123, 123, 123, 123),
  ('braceright', 125, 125, 125, 125),
  ('bracketleft', 91, 91, 91, 91),
  ('bracketright', 93, 93, 93, 93),
  ('breve', 198, 249, None, 24),
  ('brokenbar', None, None, 166, 166),
  ('bullet', 183, 165, 149, 128),
  ('c', 99, 99, 99, 99),
  ('caron', 207, 255, None, 25),
  ('ccedilla', None, 141, 231, 231),
  ('cedilla', 203, 252, 184, 184),
  ('cent', 162, 162, 162, 162),
  ('circumflex', 195, 246, 136, 26),
  ('colon', 58, 58, 58, 58),
  ('comma', 44, 44, 44, 44),
  ('copyright', None, 169, 169, 169),
  ('currency', 168, 219, 164, 164),
  ('d', 100, 100, 100, 100),
  ('dagger', 178, 160, 134, 129),
  ('daggerdbl', 179, 224, 135, 130),
  ('degree', None, 161, 176, 176),
  ('dieresis', 200, 172, 168, 168),
  ('divide', None, 214, 247, 247),
  ('dollar', 36, 36, 36, 36),
  ('dotaccent', 199, 250, None, 27),
  ('dotlessi', 245, 245, None, 154),
  ('e', 101, 101, 101, 101),
  ('eacute', None, 142, 233, 233),
  ('ecircumflex', None, 144, 234, 234),
  ('edieresis', None, 145, 235, 235),
  ('egrave', None, 143, 232, 232),
  ('eight', 56, 56, 56, 56),
  ('ellipsis', 188, 201, 133, 131),
  ('emdash', 208, 209, 151, 132),
  ('endash', 177, 208, 150, 133),
  ('equal', 61, 61, 61, 61),
  ('eth', None, None, 240, 240),
  ('exclam', 33, 33, 33, 33),
  ('exclamdown', 161, 193, 161, 161),
  ('f', 102, 102, 102, 102),
  ('fi', 174, 222, None, 147),
  ('five', 53, 53, 53, 53),
  ('fl', 175, 223, None, 148),
  ('florin', 166, 196, 131, 134),
  ('four', 52, 52, 52, 52),
  ('fraction', 164, 218, None, 135),
  ('g', 103, 103, 103, 103),
  ('germandbls', 251, 167, 223, 223),
  ('grave', 193, 96, 96, 96),
  ('greater', 62, 62, 62, 62),
  ('guillemotleft', 171, 199, 171, 171),
  ('guillemotright', 187, 200, 187, 187),
  ('guilsinglleft', 172, 220, 139, 136),
  ('guilsinglright', 173, 221, 155, 137),
  ('h', 104, 104, 104, 104),
  ('hungarumlaut', 205, 253, None, 28),
  ('hyphen', 45, 45, 45, 45),
  ('i', 105, 105, 105, 105),
  ('iacute', None, 146, 237, 237),
  ('icircumflex', None, 148, 238, 238),
  ('idieresis', None, 149, 239, 239),
  ('igrave', None, 147, 236, 236),
  ('j', 106, 106, 106, 106),
  ('k', 107, 107, 107, 107),
  ('l', 108, 108, 108, 108),
  ('less', 60, 60, 60, 60),
  ('logicalnot', None, 194, 172, 172),
  ('lslash', 248, None, None, 155),
  ('m', 109, 109, 109, 109),
  ('macron', 197, 248, 175, 175),
  ('minus', None, None, None, 138),
  ('mu', None, 181, 181, 181),
  ('multiply', None, None, 215, 215),
  ('n', 110, 110, 110, 110),
  ('nine', 57, 57, 57, 57),
  ('ntilde', None, 150, 241, 241),
  ('numbersign', 35, 35, 35, 35),
  ('o', 111, 111, 111, 111),
  ('oacute', None, 151, 243, 243),
  ('ocircumflex', None, 153, 244, 244),
  ('odieresis', None, 154, 246, 246),
  ('oe', 250, 207, 156, 156),
  ('ogonek', 206, 254, None, 29),
  ('ograve', None, 152, 242, 242),
  ('one', 49, 49, 49, 49),
  ('onehalf', None, None, 189, 189),
  ('onequarter', None, None, 188, 188),
  ('onesuperior', None, None, 185, 185),
  ('ordfeminine', 227, 187, 170, 170),
  ('ordmasculine', 235, 188, 186, 186),
  ('oslash', 249, 191, 248, 248),
  ('otilde', None, 155, 245, 245),
  ('p', 112, 112, 112, 112),
  ('paragraph', 182, 166, 182, 182),
  ('parenleft', 40, 40, 40, 40),
  ('parenright', 41, 41, 41, 41),
  ('percent', 37, 37, 37, 37),
  ('period', 46, 46, 46, 46),
  ('periodcentered', 180, 225, 183, 183),
  ('perthousand', 189, 228, 137, 139),
  ('plus', 43, 43, 43, 43),
  ('plusminus', None, 177, 177, 177),
  ('q', 113, 113, 113, 113),
  ('question', 63, 63, 63, 63),
  ('questiondown', 191, 192, 191, 191),
  ('quotedbl', 34, 34, 34, 34),
  ('quotedblbase', 185, 227, 132, 140),
  ('quotedblleft', 170, 210, 147, 141),
  ('quotedblright', 186, 211, 148, 142),
  ('quoteleft', 96, 212, 145, 143),
  ('quoteright', 39, 213, 146, 144),
  ('quotesinglbase', 184, 226, 130, 145),
  ('quotesingle', 169, 39, 39, 39),
  ('r', 114, 114, 114, 114),
  ('registered', None, 168, 174, 174),
  ('ring', 202, 251, None, 30),
  ('s', 115, 115, 115, 115),
  ('scaron', None, None, 154, 157),
  ('section', 167, 164, 167, 167),
  ('semicolon', 59, 59, 59, 59),
  ('seven', 55, 55, 55, 55),
  ('six', 54, 54, 54, 54),
  ('slash', 47, 47, 47, 47),
  ('space', 32, 32, 32, 32),
  ('sterling', 163, 163, 163, 163),
  ('t', 116, 116, 116, 116),
  ('thorn', None, None, 254, 254),
  ('three', 51, 51, 51, 51),
  ('threequarters', None, None, 190, 190),
  ('threesuperior', None, None, 179, 179),
  ('tilde', 196, 247, 152, 31),
  ('trademark', None, 170, 153, 146),
  ('two', 50, 50, 50, 50),
  ('twosuperior', None, None, 178, 178),
  ('u', 117, 117, 117, 117),
  ('uacute', None, 156, 250, 250),
  ('ucircumflex', None, 158, 251, 251),
  ('udieresis', None, 159, 252, 252),
  ('ugrave', None, 157, 249, 249),
  ('underscore', 95, 95, 95, 95),
  ('v', 118, 118, 118, 118),
  ('w', 119, 119, 119, 119),
  ('x', 120, 120, 120, 120),
  ('y', 121, 121, 121, 121),
  ('yacute', None, None, 253, 253),
  ('ydieresis', None, 216, 255, 255),
  ('yen', 165, 180, 165, 165),
  ('z', 122, 122, 122, 122),
  ('zcaron', None, None, 158, 158),
  ('zero', 48, 48, 48, 48),
]

########NEW FILE########
__FILENAME__ = layout
#!/usr/bin/env python
from utils import INF, Plane, get_bound, uniq, csort, fsplit
from utils import bbox2str, matrix2str, apply_matrix_pt


##  IndexAssigner
##
class IndexAssigner(object):

    def __init__(self, index=0):
        self.index = index
        return

    def run(self, obj):
        if isinstance(obj, LTTextBox):
            obj.index = self.index
            self.index += 1
        elif isinstance(obj, LTTextGroup):
            for x in obj:
                self.run(x)
        return


##  LAParams
##
class LAParams(object):

    def __init__(self,
                 line_overlap=0.5,
                 char_margin=2.0,
                 line_margin=0.5,
                 word_margin=0.1,
                 boxes_flow=0.5,
                 detect_vertical=False,
                 all_texts=False):
        self.line_overlap = line_overlap
        self.char_margin = char_margin
        self.line_margin = line_margin
        self.word_margin = word_margin
        self.boxes_flow = boxes_flow
        self.detect_vertical = detect_vertical
        self.all_texts = all_texts
        return

    def __repr__(self):
        return ('<LAParams: char_margin=%.1f, line_margin=%.1f, word_margin=%.1f all_texts=%r>' %
                (self.char_margin, self.line_margin, self.word_margin, self.all_texts))


##  LTItem
##
class LTItem(object):

    def analyze(self, laparams):
        """Perform the layout analysis."""
        return


##  LTText
##
class LTText(object):

    def __repr__(self):
        return ('<%s %r>' %
                (self.__class__.__name__, self.get_text()))

    def get_text(self):
        raise NotImplementedError


##  LTComponent
##
class LTComponent(LTItem):

    def __init__(self, bbox):
        LTItem.__init__(self)
        self.set_bbox(bbox)
        return

    def __repr__(self):
        return ('<%s %s>' %
                (self.__class__.__name__, bbox2str(self.bbox)))

    def set_bbox(self, (x0, y0, x1, y1)):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.width = x1-x0
        self.height = y1-y0
        self.bbox = (x0, y0, x1, y1)
        return

    def is_empty(self):
        return self.width <= 0 or self.height <= 0

    def is_hoverlap(self, obj):
        assert isinstance(obj, LTComponent)
        return obj.x0 <= self.x1 and self.x0 <= obj.x1

    def hdistance(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_hoverlap(obj):
            return 0
        else:
            return min(abs(self.x0-obj.x1), abs(self.x1-obj.x0))

    def hoverlap(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_hoverlap(obj):
            return min(abs(self.x0-obj.x1), abs(self.x1-obj.x0))
        else:
            return 0

    def is_voverlap(self, obj):
        assert isinstance(obj, LTComponent)
        return obj.y0 <= self.y1 and self.y0 <= obj.y1

    def vdistance(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_voverlap(obj):
            return 0
        else:
            return min(abs(self.y0-obj.y1), abs(self.y1-obj.y0))

    def voverlap(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_voverlap(obj):
            return min(abs(self.y0-obj.y1), abs(self.y1-obj.y0))
        else:
            return 0


##  LTCurve
##
class LTCurve(LTComponent):

    def __init__(self, linewidth, pts):
        LTComponent.__init__(self, get_bound(pts))
        self.pts = pts
        self.linewidth = linewidth
        return

    def get_pts(self):
        return ','.join('%.3f,%.3f' % p for p in self.pts)


##  LTLine
##
class LTLine(LTCurve):

    def __init__(self, linewidth, p0, p1):
        LTCurve.__init__(self, linewidth, [p0, p1])
        return


##  LTRect
##
class LTRect(LTCurve):

    def __init__(self, linewidth, (x0, y0, x1, y1)):
        LTCurve.__init__(self, linewidth, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        return


##  LTImage
##
class LTImage(LTComponent):

    def __init__(self, name, stream, bbox):
        LTComponent.__init__(self, bbox)
        self.name = name
        self.stream = stream
        self.srcsize = (stream.get_any(('W', 'Width')),
                        stream.get_any(('H', 'Height')))
        self.imagemask = stream.get_any(('IM', 'ImageMask'))
        self.bits = stream.get_any(('BPC', 'BitsPerComponent'), 1)
        self.colorspace = stream.get_any(('CS', 'ColorSpace'))
        if not isinstance(self.colorspace, list):
            self.colorspace = [self.colorspace]
        return

    def __repr__(self):
        return ('<%s(%s) %s %r>' %
                (self.__class__.__name__, self.name,
                 bbox2str(self.bbox), self.srcsize))


##  LTAnno
##
class LTAnno(LTItem, LTText):

    def __init__(self, text):
        self._text = text
        return

    def get_text(self):
        return self._text


##  LTChar
##
class LTChar(LTComponent, LTText):

    def __init__(self, matrix, font, fontsize, scaling, rise,
                 text, textwidth, textdisp):
        LTText.__init__(self)
        self._text = text
        self.matrix = matrix
        self.fontname = font.fontname
        self.adv = textwidth * fontsize * scaling
        # compute the boundary rectangle.
        if font.is_vertical():
            # vertical
            width = font.get_width() * fontsize
            (vx, vy) = textdisp
            if vx is None:
                vx = width//2
            else:
                vx = vx * fontsize * .001
            vy = (1000 - vy) * fontsize * .001
            tx = -vx
            ty = vy + rise
            bll = (tx, ty+self.adv)
            bur = (tx+width, ty)
        else:
            # horizontal
            height = font.get_height() * fontsize
            descent = font.get_descent() * fontsize
            ty = descent + rise
            bll = (0, ty)
            bur = (self.adv, ty+height)
        (a, b, c, d, e, f) = self.matrix
        self.upright = (0 < a*d*scaling and b*c <= 0)
        (x0, y0) = apply_matrix_pt(self.matrix, bll)
        (x1, y1) = apply_matrix_pt(self.matrix, bur)
        if x1 < x0:
            (x0, x1) = (x1, x0)
        if y1 < y0:
            (y0, y1) = (y1, y0)
        LTComponent.__init__(self, (x0, y0, x1, y1))
        if font.is_vertical():
            self.size = self.width
        else:
            self.size = self.height
        return

    def __repr__(self):
        return ('<%s %s matrix=%s font=%r adv=%s text=%r>' %
                (self.__class__.__name__, bbox2str(self.bbox),
                 matrix2str(self.matrix), self.fontname, self.adv,
                 self.get_text()))

    def get_text(self):
        return self._text

    def is_compatible(self, obj):
        """Returns True if two characters can coexist in the same line."""
        return True


##  LTContainer
##
class LTContainer(LTComponent):

    def __init__(self, bbox):
        LTComponent.__init__(self, bbox)
        self._objs = []
        return

    def __iter__(self):
        return iter(self._objs)

    def __len__(self):
        return len(self._objs)

    def add(self, obj):
        self._objs.append(obj)
        return

    def extend(self, objs):
        for obj in objs:
            self.add(obj)
        return

    def analyze(self, laparams):
        for obj in self._objs:
            obj.analyze(laparams)
        return


##  LTExpandableContainer
##
class LTExpandableContainer(LTContainer):

    def __init__(self):
        LTContainer.__init__(self, (+INF, +INF, -INF, -INF))
        return

    def add(self, obj):
        LTContainer.add(self, obj)
        self.set_bbox((min(self.x0, obj.x0), min(self.y0, obj.y0),
                       max(self.x1, obj.x1), max(self.y1, obj.y1)))
        return


##  LTTextContainer
##
class LTTextContainer(LTExpandableContainer, LTText):

    def __init__(self):
        LTText.__init__(self)
        LTExpandableContainer.__init__(self)
        return

    def get_text(self):
        return ''.join(obj.get_text() for obj in self if isinstance(obj, LTText))


##  LTTextLine
##
class LTTextLine(LTTextContainer):

    def __init__(self, word_margin):
        LTTextContainer.__init__(self)
        self.word_margin = word_margin
        return

    def __repr__(self):
        return ('<%s %s %r>' %
                (self.__class__.__name__, bbox2str(self.bbox),
                 self.get_text()))

    def analyze(self, laparams):
        LTTextContainer.analyze(self, laparams)
        LTContainer.add(self, LTAnno('\n'))
        return

    def find_neighbors(self, plane, ratio):
        raise NotImplementedError


class LTTextLineHorizontal(LTTextLine):

    def __init__(self, word_margin):
        LTTextLine.__init__(self, word_margin)
        self._x1 = +INF
        return

    def add(self, obj):
        if isinstance(obj, LTChar) and self.word_margin:
            margin = self.word_margin * max(obj.width, obj.height)
            if self._x1 < obj.x0-margin:
                LTContainer.add(self, LTAnno(' '))
        self._x1 = obj.x1
        LTTextLine.add(self, obj)
        return

    def find_neighbors(self, plane, ratio):
        d = ratio*self.height
        objs = plane.find((self.x0, self.y0-d, self.x1, self.y1+d))
        return [obj for obj in objs
                if (isinstance(obj, LTTextLineHorizontal) and
                    abs(obj.height-self.height) < d and
                    (abs(obj.x0-self.x0) < d or
                     abs(obj.x1-self.x1) < d))]


class LTTextLineVertical(LTTextLine):

    def __init__(self, word_margin):
        LTTextLine.__init__(self, word_margin)
        self._y0 = -INF
        return

    def add(self, obj):
        if isinstance(obj, LTChar) and self.word_margin:
            margin = self.word_margin * max(obj.width, obj.height)
            if obj.y1+margin < self._y0:
                LTContainer.add(self, LTAnno(' '))
        self._y0 = obj.y0
        LTTextLine.add(self, obj)
        return

    def find_neighbors(self, plane, ratio):
        d = ratio*self.width
        objs = plane.find((self.x0-d, self.y0, self.x1+d, self.y1))
        return [obj for obj in objs
                if (isinstance(obj, LTTextLineVertical) and
                    abs(obj.width-self.width) < d and
                    (abs(obj.y0-self.y0) < d or
                     abs(obj.y1-self.y1) < d))]


##  LTTextBox
##
##  A set of text objects that are grouped within
##  a certain rectangular area.
##
class LTTextBox(LTTextContainer):

    def __init__(self):
        LTTextContainer.__init__(self)
        self.index = -1
        return

    def __repr__(self):
        return ('<%s(%s) %s %r>' %
                (self.__class__.__name__,
                 self.index, bbox2str(self.bbox), self.get_text()))


class LTTextBoxHorizontal(LTTextBox):

    def analyze(self, laparams):
        LTTextBox.analyze(self, laparams)
        self._objs = csort(self._objs, key=lambda obj: -obj.y1)
        return

    def get_writing_mode(self):
        return 'lr-tb'


class LTTextBoxVertical(LTTextBox):

    def analyze(self, laparams):
        LTTextBox.analyze(self, laparams)
        self._objs = csort(self._objs, key=lambda obj: -obj.x1)
        return

    def get_writing_mode(self):
        return 'tb-rl'


##  LTTextGroup
##
class LTTextGroup(LTTextContainer):

    def __init__(self, objs):
        LTTextContainer.__init__(self)
        self.extend(objs)
        return


class LTTextGroupLRTB(LTTextGroup):

    def analyze(self, laparams):
        LTTextGroup.analyze(self, laparams)
        # reorder the objects from top-left to bottom-right.
        self._objs = csort(self._objs, key=lambda obj:
                           (1-laparams.boxes_flow)*(obj.x0) -
                           (1+laparams.boxes_flow)*(obj.y0+obj.y1))
        return


class LTTextGroupTBRL(LTTextGroup):

    def analyze(self, laparams):
        LTTextGroup.analyze(self, laparams)
        # reorder the objects from top-right to bottom-left.
        self._objs = csort(self._objs, key=lambda obj:
                           -(1+laparams.boxes_flow)*(obj.x0+obj.x1)
                           - (1-laparams.boxes_flow)*(obj.y1))
        return


##  LTLayoutContainer
##
class LTLayoutContainer(LTContainer):

    def __init__(self, bbox):
        LTContainer.__init__(self, bbox)
        self.groups = None
        return

    # group_objects: group text object to textlines.
    def group_objects(self, laparams, objs):
        obj0 = None
        line = None
        for obj1 in objs:
            if obj0 is not None:
                # halign: obj0 and obj1 is horizontally aligned.
                #
                #   +------+ - - -
                #   | obj0 | - - +------+   -
                #   |      |     | obj1 |   | (line_overlap)
                #   +------+ - - |      |   -
                #          - - - +------+
                #
                #          |<--->|
                #        (char_margin)
                halign = (obj0.is_compatible(obj1) and
                          obj0.is_voverlap(obj1) and
                          (min(obj0.height, obj1.height) * laparams.line_overlap <
                           obj0.voverlap(obj1)) and
                          (obj0.hdistance(obj1) <
                           max(obj0.width, obj1.width) * laparams.char_margin))
                
                # valign: obj0 and obj1 is vertically aligned.
                #
                #   +------+
                #   | obj0 |
                #   |      |
                #   +------+ - - -
                #     |    |     | (char_margin)
                #     +------+ - -
                #     | obj1 |
                #     |      |
                #     +------+
                #
                #     |<-->|
                #   (line_overlap)
                valign = (laparams.detect_vertical and
                          obj0.is_compatible(obj1) and
                          obj0.is_hoverlap(obj1) and
                          (min(obj0.width, obj1.width) * laparams.line_overlap <
                           obj0.hoverlap(obj1)) and
                          (obj0.vdistance(obj1) <
                           max(obj0.height, obj1.height) * laparams.char_margin))
                
                if ((halign and isinstance(line, LTTextLineHorizontal)) or
                    (valign and isinstance(line, LTTextLineVertical))):
                    line.add(obj1)
                elif line is not None:
                    yield line
                    line = None
                else:
                    if valign and not halign:
                        line = LTTextLineVertical(laparams.word_margin)
                        line.add(obj0)
                        line.add(obj1)
                    elif halign and not valign:
                        line = LTTextLineHorizontal(laparams.word_margin)
                        line.add(obj0)
                        line.add(obj1)
                    else:
                        line = LTTextLineHorizontal(laparams.word_margin)
                        line.add(obj0)
                        yield line
                        line = None
            obj0 = obj1
        if line is None:
            line = LTTextLineHorizontal(laparams.word_margin)
            line.add(obj0)
        yield line
        return

    # group_textlines: group neighboring lines to textboxes.
    def group_textlines(self, laparams, lines):
        plane = Plane(self.bbox)
        plane.extend(lines)
        boxes = {}
        for line in lines:
            neighbors = line.find_neighbors(plane, laparams.line_margin)
            if line not in neighbors: continue
            members = []
            for obj1 in neighbors:
                members.append(obj1)
                if obj1 in boxes:
                    members.extend(boxes.pop(obj1))
            if isinstance(line, LTTextLineHorizontal):
                box = LTTextBoxHorizontal()
            else:
                box = LTTextBoxVertical()
            for obj in uniq(members):
                box.add(obj)
                boxes[obj] = box
        done = set()
        for line in lines:
            if line not in boxes: continue
            box = boxes[line]
            if box in done:
                continue
            done.add(box)
            if not box.is_empty():
                yield box
        return

    # group_textboxes: group textboxes hierarchically.
    def group_textboxes(self, laparams, boxes):
        assert boxes

        def dist(obj1, obj2):
            """A distance function between two TextBoxes.

            Consider the bounding rectangle for obj1 and obj2.
            Return its area less the areas of obj1 and obj2,
            shown as 'www' below. This value may be negative.
                    +------+..........+ (x1, y1)
                    | obj1 |wwwwwwwwww:
                    +------+www+------+
                    :wwwwwwwwww| obj2 |
            (x0, y0) +..........+------+
            """
            x0 = min(obj1.x0, obj2.x0)
            y0 = min(obj1.y0, obj2.y0)
            x1 = max(obj1.x1, obj2.x1)
            y1 = max(obj1.y1, obj2.y1)
            return ((x1-x0)*(y1-y0) - obj1.width*obj1.height - obj2.width*obj2.height)

        def isany(obj1, obj2):
            """Check if there's any other object between obj1 and obj2.
            """
            x0 = min(obj1.x0, obj2.x0)
            y0 = min(obj1.y0, obj2.y0)
            x1 = max(obj1.x1, obj2.x1)
            y1 = max(obj1.y1, obj2.y1)
            objs = set(plane.find((x0, y0, x1, y1)))
            return objs.difference((obj1, obj2))
        # XXX this still takes O(n^2)  :(
        dists = []
        for i in xrange(len(boxes)):
            obj1 = boxes[i]
            for j in xrange(i+1, len(boxes)):
                obj2 = boxes[j]
                dists.append((0, dist(obj1, obj2), obj1, obj2))
        dists.sort()
        plane = Plane(self.bbox)
        plane.extend(boxes)
        while dists:
            (c, d, obj1, obj2) = dists.pop(0)
            if c == 0 and isany(obj1, obj2):
                dists.append((1, d, obj1, obj2))
                continue
            if (isinstance(obj1, (LTTextBoxVertical, LTTextGroupTBRL)) or
                isinstance(obj2, (LTTextBoxVertical, LTTextGroupTBRL))):
                group = LTTextGroupTBRL([obj1, obj2])
            else:
                group = LTTextGroupLRTB([obj1, obj2])
            plane.remove(obj1)
            plane.remove(obj2)
            # this line is optimized -- don't change without profiling
            dists = [n for n in dists if n[2] in plane._objs and n[3] in plane._objs]
            for other in plane:
                dists.append((0, dist(group, other), group, other))
            dists.sort()
            plane.add(group)
        assert len(plane) == 1
        return list(plane)

    def analyze(self, laparams):
        # textobjs is a list of LTChar objects, i.e.
        # it has all the individual characters in the page.
        (textobjs, otherobjs) = fsplit(lambda obj: isinstance(obj, LTChar), self)
        for obj in otherobjs:
            obj.analyze(laparams)
        if not textobjs:
            return
        textlines = list(self.group_objects(laparams, textobjs))
        (empties, textlines) = fsplit(lambda obj: obj.is_empty(), textlines)
        for obj in empties:
            obj.analyze(laparams)
        textboxes = list(self.group_textlines(laparams, textlines))
        if textboxes:
            self.groups = self.group_textboxes(laparams, textboxes)
            assigner = IndexAssigner()
            for group in self.groups:
                group.analyze(laparams)
                assigner.run(group)
            textboxes.sort(key=lambda box: box.index)
        self._objs = textboxes + otherobjs + empties
        return


##  LTFigure
##
class LTFigure(LTLayoutContainer):

    def __init__(self, name, bbox, matrix):
        self.name = name
        self.matrix = matrix
        (x, y, w, h) = bbox
        bbox = get_bound(apply_matrix_pt(matrix, (p, q))
                         for (p, q) in ((x, y), (x+w, y), (x, y+h), (x+w, y+h)))
        LTLayoutContainer.__init__(self, bbox)
        return

    def __repr__(self):
        return ('<%s(%s) %s matrix=%s>' %
                (self.__class__.__name__, self.name,
                 bbox2str(self.bbox), matrix2str(self.matrix)))

    def analyze(self, laparams):
        if not laparams.all_texts:
            return
        LTLayoutContainer.analyze(self, laparams)
        return


##  LTPage
##
class LTPage(LTLayoutContainer):

    def __init__(self, pageid, bbox, rotate=0):
        LTLayoutContainer.__init__(self, bbox)
        self.pageid = pageid
        self.rotate = rotate
        return

    def __repr__(self):
        return ('<%s(%r) %s rotate=%r>' %
                (self.__class__.__name__, self.pageid,
                 bbox2str(self.bbox), self.rotate))

########NEW FILE########
__FILENAME__ = lzw
#!/usr/bin/env python
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class CorruptDataError(Exception):
    pass


##  LZWDecoder
##
class LZWDecoder(object):

    debug = 0

    def __init__(self, fp):
        self.fp = fp
        self.buff = 0
        self.bpos = 8
        self.nbits = 9
        self.table = None
        self.prevbuf = None
        return

    def readbits(self, bits):
        v = 0
        while 1:
            # the number of remaining bits we can get from the current buffer.
            r = 8-self.bpos
            if bits <= r:
                # |-----8-bits-----|
                # |-bpos-|-bits-|  |
                # |      |----r----|
                v = (v << bits) | ((self.buff >> (r-bits)) & ((1 << bits)-1))
                self.bpos += bits
                break
            else:
                # |-----8-bits-----|
                # |-bpos-|---bits----...
                # |      |----r----|
                v = (v << r) | (self.buff & ((1 << r)-1))
                bits -= r
                x = self.fp.read(1)
                if not x:
                    raise EOFError
                self.buff = ord(x)
                self.bpos = 0
        return v

    def feed(self, code):
        x = ''
        if code == 256:
            self.table = [chr(c) for c in xrange(256)]  # 0-255
            self.table.append(None)  # 256
            self.table.append(None)  # 257
            self.prevbuf = ''
            self.nbits = 9
        elif code == 257:
            pass
        elif not self.prevbuf:
            x = self.prevbuf = self.table[code]
        else:
            if code < len(self.table):
                x = self.table[code]
                self.table.append(self.prevbuf+x[:1])
            elif code == len(self.table):
                self.table.append(self.prevbuf+self.prevbuf[:1])
                x = self.table[code]
            else:
                raise CorruptDataError
            l = len(self.table)
            if l == 511:
                self.nbits = 10
            elif l == 1023:
                self.nbits = 11
            elif l == 2047:
                self.nbits = 12
            self.prevbuf = x
        return x

    def run(self):
        while 1:
            try:
                code = self.readbits(self.nbits)
            except EOFError:
                break
            try:
                x = self.feed(code)
            except CorruptDataError:
                # just ignore corrupt data and stop yielding there
                break
            yield x
            if self.debug:
                print >>sys.stderr, ('nbits=%d, code=%d, output=%r, table=%r' %
                                     (self.nbits, code, x, self.table[258:]))
        return


# lzwdecode
def lzwdecode(data):
    """
    >>> lzwdecode('\x80\x0b\x60\x50\x22\x0c\x0c\x85\x01')
    '\x2d\x2d\x2d\x2d\x2d\x41\x2d\x2d\x2d\x42'
    """
    fp = StringIO(data)
    return ''.join(LZWDecoder(fp).run())

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = pdfcolor
#!/usr/bin/env python
from psparser import LIT


##  PDFColorSpace
##
LITERAL_DEVICE_GRAY = LIT('DeviceGray')
LITERAL_DEVICE_RGB = LIT('DeviceRGB')
LITERAL_DEVICE_CMYK = LIT('DeviceCMYK')


class PDFColorSpace(object):

    def __init__(self, name, ncomponents):
        self.name = name
        self.ncomponents = ncomponents
        return

    def __repr__(self):
        return '<PDFColorSpace: %s, ncomponents=%d>' % (self.name, self.ncomponents)


PREDEFINED_COLORSPACE = dict(
    (name, PDFColorSpace(name, n)) for (name, n) in {
        'CalRGB': 3,
        'CalGray': 1,
        'Lab': 3,
        'DeviceRGB': 3,
        'DeviceCMYK': 4,
        'DeviceGray': 1,
        'Separation': 1,
        'Indexed': 1,
        'Pattern': 1,
    }.iteritems())

########NEW FILE########
__FILENAME__ = pdfdevice
#!/usr/bin/env python
from utils import mult_matrix, translate_matrix
from utils import enc, bbox2str, isnumber
from pdffont import PDFUnicodeNotDefined


##  PDFDevice
##
class PDFDevice(object):

    debug = 0

    def __init__(self, rsrcmgr):
        self.rsrcmgr = rsrcmgr
        self.ctm = None
        return

    def __repr__(self):
        return '<PDFDevice>'

    def close(self):
        return

    def set_ctm(self, ctm):
        self.ctm = ctm
        return

    def begin_tag(self, tag, props=None):
        return

    def end_tag(self):
        return

    def do_tag(self, tag, props=None):
        return

    def begin_page(self, page, ctm):
        return

    def end_page(self, page):
        return

    def begin_figure(self, name, bbox, matrix):
        return

    def end_figure(self, name):
        return

    def paint_path(self, graphicstate, stroke, fill, evenodd, path):
        return

    def render_image(self, name, stream):
        return

    def render_string(self, textstate, seq):
        return


##  PDFTextDevice
##
class PDFTextDevice(PDFDevice):

    def render_string(self, textstate, seq):
        matrix = mult_matrix(textstate.matrix, self.ctm)
        font = textstate.font
        fontsize = textstate.fontsize
        scaling = textstate.scaling * .01
        charspace = textstate.charspace * scaling
        wordspace = textstate.wordspace * scaling
        rise = textstate.rise
        if font.is_multibyte():
            wordspace = 0
        dxscale = .001 * fontsize * scaling
        if font.is_vertical():
            textstate.linematrix = self.render_string_vertical(
                seq, matrix, textstate.linematrix, font, fontsize,
                scaling, charspace, wordspace, rise, dxscale)
        else:
            textstate.linematrix = self.render_string_horizontal(
                seq, matrix, textstate.linematrix, font, fontsize,
                scaling, charspace, wordspace, rise, dxscale)
        return

    def render_string_horizontal(self, seq, matrix, (x, y),
                                 font, fontsize, scaling, charspace, wordspace, rise, dxscale):
        needcharspace = False
        for obj in seq:
            if isnumber(obj):
                x -= obj*dxscale
                needcharspace = True
            else:
                for cid in font.decode(obj):
                    if needcharspace:
                        x += charspace
                    x += self.render_char(translate_matrix(matrix, (x, y)),
                                          font, fontsize, scaling, rise, cid)
                    if cid == 32 and wordspace:
                        x += wordspace
                    needcharspace = True
        return (x, y)

    def render_string_vertical(self, seq, matrix, (x, y),
                               font, fontsize, scaling, charspace, wordspace, rise, dxscale):
        needcharspace = False
        for obj in seq:
            if isnumber(obj):
                y -= obj*dxscale
                needcharspace = True
            else:
                for cid in font.decode(obj):
                    if needcharspace:
                        y += charspace
                    y += self.render_char(translate_matrix(matrix, (x, y)),
                                          font, fontsize, scaling, rise, cid)
                    if cid == 32 and wordspace:
                        y += wordspace
                    needcharspace = True
        return (x, y)

    def render_char(self, matrix, font, fontsize, scaling, rise, cid):
        return 0


##  TagExtractor
##
class TagExtractor(PDFDevice):

    def __init__(self, rsrcmgr, outfp, codec='utf-8', debug=0):
        PDFDevice.__init__(self, rsrcmgr)
        self.outfp = outfp
        self.codec = codec
        self.debug = debug
        self.pageno = 0
        self._stack = []
        return

    def render_string(self, textstate, seq):
        font = textstate.font
        text = ''
        for obj in seq:
            if not isinstance(obj, str):
                continue
            chars = font.decode(obj)
            for cid in chars:
                try:
                    char = font.to_unichr(cid)
                    text += char
                except PDFUnicodeNotDefined:
                    pass
        self.outfp.write(enc(text, self.codec))
        return

    def begin_page(self, page, ctm):
        self.outfp.write('<page id="%s" bbox="%s" rotate="%d">' %
                         (self.pageno, bbox2str(page.mediabox), page.rotate))
        return

    def end_page(self, page):
        self.outfp.write('</page>\n')
        self.pageno += 1
        return

    def begin_tag(self, tag, props=None):
        s = ''
        if isinstance(props, dict):
            s = ''.join(' %s="%s"' % (enc(k), enc(str(v))) for (k, v)
                        in sorted(props.iteritems()))
        self.outfp.write('<%s%s>' % (enc(tag.name), s))
        self._stack.append(tag)
        return

    def end_tag(self):
        assert self._stack
        tag = self._stack.pop(-1)
        self.outfp.write('</%s>' % enc(tag.name))
        return

    def do_tag(self, tag, props=None):
        self.begin_tag(tag, props)
        self._stack.pop(-1)
        return

########NEW FILE########
__FILENAME__ = pdfdocument
#!/usr/bin/env python
import sys
import re
import struct
try:
    import hashlib as md5
except ImportError:
    import md5
try:
    from Crypto.Cipher import ARC4
    from Crypto.Cipher import AES
    from Crypto.Hash import SHA256
except ImportError:
    AES = SHA256 = None
    import arcfour as ARC4

from psparser import PSEOF
from psparser import literal_name
from psparser import LIT, KWD, STRICT
from pdftypes import PDFException, PDFTypeError, PDFNotImplementedError
from pdftypes import PDFObjectNotFound, PDFStream
from pdftypes import decipher_all
from pdftypes import int_value
from pdftypes import str_value, list_value, dict_value, stream_value
from pdfparser import PDFSyntaxError
from pdfparser import PDFStreamParser
from utils import choplist, nunpack
from utils import decode_text


##  Exceptions
##
class PDFNoValidXRef(PDFSyntaxError):
    pass

class PDFNoOutlines(PDFException):
    pass

class PDFDestinationNotFound(PDFException):
    pass

class PDFEncryptionError(PDFException):
    pass

class PDFPasswordIncorrect(PDFEncryptionError):
    pass

class PDFTextExtractionNotAllowed(PDFEncryptionError):
    pass

# some predefined literals and keywords.
LITERAL_OBJSTM = LIT('ObjStm')
LITERAL_XREF = LIT('XRef')
LITERAL_CATALOG = LIT('Catalog')


##  XRefs
##
class PDFBaseXRef(object):

    def get_trailer(self):
        raise NotImplementedError

    def get_objids(self):
        return []

    # Must return
    #     (strmid, index, genno)
    #  or (None, pos, genno)
    def get_pos(self, objid):
        raise KeyError(objid)


##  PDFXRef
##
class PDFXRef(PDFBaseXRef):

    def __init__(self):
        self.offsets = {}
        self.trailer = {}
        return

    def __repr__(self):
        return '<PDFXRef: offsets=%r>' % (self.offsets.keys())

    def load(self, parser, debug=0):
        while 1:
            try:
                (pos, line) = parser.nextline()
                if not line.strip():
                    continue
            except PSEOF:
                raise PDFNoValidXRef('Unexpected EOF - file corrupted?')
            if not line:
                raise PDFNoValidXRef('Premature eof: %r' % parser)
            if line.startswith('trailer'):
                parser.seek(pos)
                break
            f = line.strip().split(' ')
            if len(f) != 2:
                raise PDFNoValidXRef('Trailer not found: %r: line=%r' % (parser, line))
            try:
                (start, nobjs) = map(long, f)
            except ValueError:
                raise PDFNoValidXRef('Invalid line: %r: line=%r' % (parser, line))
            for objid in xrange(start, start+nobjs):
                try:
                    (_, line) = parser.nextline()
                except PSEOF:
                    raise PDFNoValidXRef('Unexpected EOF - file corrupted?')
                f = line.strip().split(' ')
                if len(f) != 3:
                    raise PDFNoValidXRef('Invalid XRef format: %r, line=%r' % (parser, line))
                (pos, genno, use) = f
                if use != 'n':
                    continue
                self.offsets[objid] = (None, long(pos), int(genno))
        if 1 <= debug:
            print >>sys.stderr, 'xref objects:', self.offsets
        self.load_trailer(parser)
        return

    KEYWORD_TRAILER = KWD('trailer')

    def load_trailer(self, parser):
        try:
            (_, kwd) = parser.nexttoken()
            assert kwd is self.KEYWORD_TRAILER
            (_, dic) = parser.nextobject()
        except PSEOF:
            x = parser.pop(1)
            if not x:
                raise PDFNoValidXRef('Unexpected EOF - file corrupted')
            (_, dic) = x[0]
        self.trailer.update(dict_value(dic))
        return

    def get_trailer(self):
        return self.trailer

    def get_objids(self):
        return self.offsets.iterkeys()

    def get_pos(self, objid):
        try:
            return self.offsets[objid]
        except KeyError:
            raise


##  PDFXRefFallback
##
class PDFXRefFallback(PDFXRef):

    def __repr__(self):
        return '<PDFXRefFallback: offsets=%r>' % (self.offsets.keys())

    PDFOBJ_CUE = re.compile(r'^(\d+)\s+(\d+)\s+obj\b')

    def load(self, parser, debug=0):
        parser.seek(0)
        while 1:
            try:
                (pos, line) = parser.nextline()
            except PSEOF:
                break
            if line.startswith('trailer'):
                parser.seek(pos)
                self.load_trailer(parser)
                if 1 <= debug:
                    print >>sys.stderr, 'trailer: %r' % self.get_trailer()
                break
            m = self.PDFOBJ_CUE.match(line)
            if not m:
                continue
            (objid, genno) = m.groups()
            objid = int(objid)
            genno = int(genno)
            self.offsets[objid] = (None, pos, genno)
            # expand ObjStm.
            parser.seek(pos)
            (_, obj) = parser.nextobject()
            if isinstance(obj, PDFStream) and obj.get('Type') is LITERAL_OBJSTM:
                stream = stream_value(obj)
                try:
                    n = stream['N']
                except KeyError:
                    if STRICT:
                        raise PDFSyntaxError('N is not defined: %r' % stream)
                    n = 0
                parser1 = PDFStreamParser(stream.get_data())
                objs = []
                try:
                    while 1:
                        (_, obj) = parser1.nextobject()
                        objs.append(obj)
                except PSEOF:
                    pass
                n = min(n, len(objs)//2)
                for index in xrange(n):
                    objid1 = objs[index*2]
                    self.offsets[objid1] = (objid, index, 0)
        return


##  PDFXRefStream
##
class PDFXRefStream(PDFBaseXRef):

    def __init__(self):
        self.data = None
        self.entlen = None
        self.fl1 = self.fl2 = self.fl3 = None
        self.ranges = []
        return

    def __repr__(self):
        return '<PDFXRefStream: ranges=%r>' % (self.ranges)

    def load(self, parser, debug=0):
        (_, objid) = parser.nexttoken()  # ignored
        (_, genno) = parser.nexttoken()  # ignored
        (_, kwd) = parser.nexttoken()
        (_, stream) = parser.nextobject()
        if not isinstance(stream, PDFStream) or stream['Type'] is not LITERAL_XREF:
            raise PDFNoValidXRef('Invalid PDF stream spec.')
        size = stream['Size']
        index_array = stream.get('Index', (0, size))
        if len(index_array) % 2 != 0:
            raise PDFSyntaxError('Invalid index number')
        self.ranges.extend(choplist(2, index_array))
        (self.fl1, self.fl2, self.fl3) = stream['W']
        self.data = stream.get_data()
        self.entlen = self.fl1+self.fl2+self.fl3
        self.trailer = stream.attrs
        if 1 <= debug:
            print >>sys.stderr, ('xref stream: objid=%s, fields=%d,%d,%d' %
                                 (', '.join(map(repr, self.ranges)),
                                 self.fl1, self.fl2, self.fl3))
        return

    def get_trailer(self):
        return self.trailer

    def get_objids(self):
        for (start, nobjs) in self.ranges:
            for i in xrange(nobjs):
                offset = self.entlen * i
                ent = self.data[offset:offset+self.entlen]
                f1 = nunpack(ent[:self.fl1], 1)
                if f1 == 1 or f1 == 2:
                    yield start+i
        return

    def get_pos(self, objid):
        index = 0
        for (start, nobjs) in self.ranges:
            if start <= objid and objid < start+nobjs:
                index += objid - start
                break
            else:
                index += nobjs
        else:
            raise KeyError(objid)
        offset = self.entlen * index
        ent = self.data[offset:offset+self.entlen]
        f1 = nunpack(ent[:self.fl1], 1)
        f2 = nunpack(ent[self.fl1:self.fl1+self.fl2])
        f3 = nunpack(ent[self.fl1+self.fl2:])
        if f1 == 1:
            return (None, f2, f3)
        elif f1 == 2:
            return (f2, f3, 0)
        else:
            # this is a free object
            raise KeyError(objid)


##  PDFSecurityHandler
##
class PDFStandardSecurityHandler(object):

    PASSWORD_PADDING = '(\xbfN^Nu\x8aAd\x00NV\xff\xfa\x01\x08..\x00\xb6\xd0h>\x80/\x0c\xa9\xfedSiz'
    supported_revisions = (2, 3)

    def __init__(self, docid, param, password=''):
        self.docid = docid
        self.param = param
        self.password = password
        self.init()

    def init(self):
        self.init_params()
        if self.r not in self.supported_revisions:
            raise PDFEncryptionError('Unsupported revision: param=%r' % self.param)
        self.init_key()

    def init_params(self):
        self.v = int_value(self.param.get('V', 0))
        self.r = int_value(self.param['R'])
        self.p = int_value(self.param['P'])
        self.o = str_value(self.param['O'])
        self.u = str_value(self.param['U'])
        self.length = int_value(self.param.get('Length', 40))

    def init_key(self):
        self.key = self.authenticate(self.password)
        if self.key is None:
            raise PDFPasswordIncorrect

    def is_printable(self):
        return bool(self.p & 4)

    def is_modifiable(self):
        return bool(self.p & 8)

    def is_extractable(self):
        return bool(self.p & 16)

    def compute_u(self, key):
        if self.r == 2:
            # Algorithm 3.4
            return ARC4.new(key).encrypt(self.PASSWORD_PADDING)  # 2
        else:
            # Algorithm 3.5
            hash = md5.md5(self.PASSWORD_PADDING)  # 2
            hash.update(self.docid[0])  # 3
            result = ARC4.new(key).encrypt(hash.digest())  # 4
            for i in range(1, 20):  # 5
                k = ''.join(chr(ord(c) ^ i) for c in key)
                result = ARC4.new(k).encrypt(result)
            result += result  # 6
            return result

    def compute_encryption_key(self, password):
        # Algorithm 3.2
        password = (password + self.PASSWORD_PADDING)[:32]  # 1
        hash = md5.md5(password)  # 2
        hash.update(self.o)  # 3
        hash.update(struct.pack('<l', self.p))  # 4
        hash.update(self.docid[0])  # 5
        if self.r >= 4:
            if not self.encrypt_metadata:
                hash.update('\xff\xff\xff\xff')
        result = hash.digest()
        n = 5
        if self.r >= 3:
            n = self.length // 8
            for _ in range(50):
                result = md5.md5(result[:n]).digest()
        return result[:n]

    def authenticate(self, password):
        key = self.authenticate_user_password(password)
        if key is None:
            key = self.authenticate_owner_password(password)
        return key

    def authenticate_user_password(self, password):
        key = self.compute_encryption_key(password)
        if self.verify_encryption_key(key):
            return key

    def verify_encryption_key(self, key):
        # Algorithm 3.6
        u = self.compute_u(key)
        if self.r == 2:
            return u == self.u
        return u[:16] == self.u[:16]

    def authenticate_owner_password(self, password):
        # Algorithm 3.7
        password = (password + self.PASSWORD_PADDING)[:32]
        hash = md5.md5(password)
        if self.r >= 3:
            for _ in range(50):
                hash = md5.md5(hash.digest())
        n = 5
        if self.r >= 3:
            n = self.length // 8
        key = hash.digest()[:n]
        if self.r == 2:
            user_password = ARC4.new(key).decrypt(self.o)
        else:
            user_password = self.o
            for i in range(19, -1, -1):
                k = ''.join(chr(ord(c) ^ i) for c in key)
                user_password = ARC4.new(k).decrypt(user_password)
        return self.authenticate_user_password(user_password)

    def decrypt(self, objid, genno, data, attrs=None):
        return self.decrypt_rc4(objid, genno, data)

    def decrypt_rc4(self, objid, genno, data):
        key = self.key + struct.pack('<L', objid)[:3] + struct.pack('<L', genno)[:2]
        hash = md5.md5(key)
        key = hash.digest()[:min(len(key), 16)]
        return ARC4.new(key).decrypt(data)


class PDFStandardSecurityHandlerV4(PDFStandardSecurityHandler):

    supported_revisions = (4,)

    def init_params(self):
        super(PDFStandardSecurityHandlerV4, self).init_params()
        self.length = 128
        self.cf = dict_value(self.param.get('CF'))
        self.stmf = literal_name(self.param['StmF'])
        self.strf = literal_name(self.param['StrF'])
        self.encrypt_metadata = bool(self.param.get('EncryptMetadata', True))
        if self.stmf != self.strf:
            raise PDFEncryptionError('Unsupported crypt filter: param=%r' % self.param)
        self.cfm = {}
        for k, v in self.cf.items():
            f = self.get_cfm(literal_name(v['CFM']))
            if f is None:
                raise PDFEncryptionError('Unknown crypt filter method: param=%r' % self.param)
            self.cfm[k] = f
        self.cfm['Identity'] = self.decrypt_identity
        if self.strf not in self.cfm:
            raise PDFEncryptionError('Undefined crypt filter: param=%r' % self.param)

    def get_cfm(self, name):
        if name == 'V2':
            return self.decrypt_rc4
        elif name == 'AESV2':
            return self.decrypt_aes128

    def decrypt(self, objid, genno, data, attrs=None, name=None):
        if not self.encrypt_metadata and attrs is not None:
            t = attrs.get('Type')
            if t is not None and literal_name(t) == 'Metadata':
                return data
        if name is None:
            name = self.strf
        return self.cfm[name](objid, genno, data)

    def decrypt_identity(self, objid, genno, data):
        return data

    def decrypt_aes128(self, objid, genno, data):
        key = self.key + struct.pack('<L', objid)[:3] + struct.pack('<L', genno)[:2] + "sAlT"
        hash = md5.md5(key)
        key = hash.digest()[:min(len(key), 16)]
        return AES.new(key, mode=AES.MODE_CBC, IV=data[:16]).decrypt(data[16:])


class PDFStandardSecurityHandlerV5(PDFStandardSecurityHandlerV4):

    supported_revisions = (5,)

    def init_params(self):
        super(PDFStandardSecurityHandlerV5, self).init_params()
        self.length = 256
        self.oe = str_value(self.param['OE'])
        self.ue = str_value(self.param['UE'])
        self.o_hash = self.o[:32]
        self.o_validation_salt = self.o[32:40]
        self.o_key_salt = self.o[40:]
        self.u_hash = self.u[:32]
        self.u_validation_salt = self.u[32:40]
        self.u_key_salt = self.u[40:]

    def get_cfm(self, name):
        if name == 'AESV3':
            return self.decrypt_aes256

    def authenticate(self, password):
        password = password.encode('utf-8')[:127]
        hash = SHA256.new(password)
        hash.update(self.o_validation_salt)
        hash.update(self.u)
        if hash.digest() == self.o_hash:
            hash = SHA256.new(password)
            hash.update(self.o_key_salt)
            hash.update(self.u)
            return AES.new(hash.digest(), mode=AES.MODE_CBC, IV='\x00' * 16).decrypt(self.oe)
        hash = SHA256.new(password)
        hash.update(self.u_validation_salt)
        if hash.digest() == self.u_hash:
            hash = SHA256.new(password)
            hash.update(self.u_key_salt)
            return AES.new(hash.digest(), mode=AES.MODE_CBC, IV='\x00' * 16).decrypt(self.ue)

    def decrypt_aes256(self, objid, genno, data):
        return AES.new(self.key, mode=AES.MODE_CBC, IV=data[:16]).decrypt(data[16:])


##  PDFDocument
##
class PDFDocument(object):

    """PDFDocument object represents a PDF document.

    Since a PDF file can be very big, normally it is not loaded at
    once. So PDF document has to cooperate with a PDF parser in order to
    dynamically import the data as processing goes.

    Typical usage:
      doc = PDFDocument(parser, password)
      obj = doc.getobj(objid)

    """

    security_handler_registry = {
        1: PDFStandardSecurityHandler,
        2: PDFStandardSecurityHandler,
    }
    if AES is not None:
        security_handler_registry[4] = PDFStandardSecurityHandlerV4
        if SHA256 is not None:
            security_handler_registry[5] = PDFStandardSecurityHandlerV5
    debug = 0

    def __init__(self, parser, password='', caching=True, fallback=True):
        "Set the document to use a given PDFParser object."
        self.caching = caching
        self.xrefs = []
        self.info = []
        self.catalog = None
        self.encryption = None
        self.decipher = None
        self._parser = None
        self._cached_objs = {}
        self._parsed_objs = {}
        self._parser = parser
        self._parser.set_document(self)
        self.is_printable = self.is_modifiable = self.is_extractable = True
        # Retrieve the information of each header that was appended
        # (maybe multiple times) at the end of the document.
        try:
            pos = self.find_xref(parser)
            self.read_xref_from(parser, pos, self.xrefs)
        except PDFNoValidXRef:
            fallback = True
        if fallback:
            parser.fallback = True
            xref = PDFXRefFallback()
            xref.load(parser)
            self.xrefs.append(xref)
        for xref in self.xrefs:
            trailer = xref.get_trailer()
            if not trailer:
                continue
            # If there's an encryption info, remember it.
            if 'Encrypt' in trailer:
                #assert not self.encryption
                self.encryption = (list_value(trailer['ID']),
                                   dict_value(trailer['Encrypt']))
                self._initialize_password(password)
            if 'Info' in trailer:
                self.info.append(dict_value(trailer['Info']))
            if 'Root' in trailer:
                # Every PDF file must have exactly one /Root dictionary.
                self.catalog = dict_value(trailer['Root'])
                break
        else:
            raise PDFSyntaxError('No /Root object! - Is this really a PDF?')
        if self.catalog.get('Type') is not LITERAL_CATALOG:
            if STRICT:
                raise PDFSyntaxError('Catalog not found!')
        return

    # _initialize_password(password='')
    #   Perform the initialization with a given password.
    def _initialize_password(self, password=''):
        (docid, param) = self.encryption
        if literal_name(param.get('Filter')) != 'Standard':
            raise PDFEncryptionError('Unknown filter: param=%r' % param)
        v = int_value(param.get('V', 0))
        factory = self.security_handler_registry.get(v)
        if factory is None:
            raise PDFEncryptionError('Unknown algorithm: param=%r' % param)
        handler = factory(docid, param, password)
        self.decipher = handler.decrypt
        self.is_printable = handler.is_printable()
        self.is_modifiable = handler.is_modifiable()
        self.is_extractable = handler.is_extractable()
        self._parser.fallback = False # need to read streams with exact length
        return

    def _getobj_objstm(self, stream, index, objid):
        if stream.objid in self._parsed_objs:
            (objs, n) = self._parsed_objs[stream.objid]
        else:
            (objs, n) = self._get_objects(stream)
            if self.caching:
                self._parsed_objs[stream.objid] = (objs, n)
        i = n*2+index
        try:
            obj = objs[i]
        except IndexError:
            raise PDFSyntaxError('index too big: %r' % index)
        return obj

    def _get_objects(self, stream):
        if stream.get('Type') is not LITERAL_OBJSTM:
            if STRICT:
                raise PDFSyntaxError('Not a stream object: %r' % stream)
        try:
            n = stream['N']
        except KeyError:
            if STRICT:
                raise PDFSyntaxError('N is not defined: %r' % stream)
            n = 0
        parser = PDFStreamParser(stream.get_data())
        parser.set_document(self)
        objs = []
        try:
            while 1:
                (_, obj) = parser.nextobject()
                objs.append(obj)
        except PSEOF:
            pass
        return (objs, n)

    KEYWORD_OBJ = KWD('obj')

    def _getobj_parse(self, pos, objid):
        self._parser.seek(pos)
        (_, objid1) = self._parser.nexttoken()  # objid
        if objid1 != objid:
            raise PDFSyntaxError('objid mismatch: %r=%r' % (objid1, objid))
        (_, genno) = self._parser.nexttoken()  # genno
        (_, kwd) = self._parser.nexttoken()
        if kwd is not self.KEYWORD_OBJ:
            raise PDFSyntaxError('Invalid object spec: offset=%r' % pos)
        (_, obj) = self._parser.nextobject()
        return obj

    # can raise PDFObjectNotFound
    def getobj(self, objid):
        assert objid != 0
        if not self.xrefs:
            raise PDFException('PDFDocument is not initialized')
        if 2 <= self.debug:
            print >>sys.stderr, 'getobj: objid=%r' % (objid)
        if objid in self._cached_objs:
            (obj, genno) = self._cached_objs[objid]
        else:
            for xref in self.xrefs:
                try:
                    (strmid, index, genno) = xref.get_pos(objid)
                except KeyError:
                    continue
                try:
                    if strmid is not None:
                        stream = stream_value(self.getobj(strmid))
                        obj = self._getobj_objstm(stream, index, objid)
                    else:
                        obj = self._getobj_parse(index, objid)
                        if self.decipher:
                            obj = decipher_all(self.decipher, objid, genno, obj)

                    if isinstance(obj, PDFStream):
                        obj.set_objid(objid, genno)
                    break
                except (PSEOF, PDFSyntaxError):
                    continue
            else:
                raise PDFObjectNotFound(objid)
            if 2 <= self.debug:
                print >>sys.stderr, 'register: objid=%r: %r' % (objid, obj)
            if self.caching:
                self._cached_objs[objid] = (obj, genno)
        return obj

    def get_outlines(self):
        if 'Outlines' not in self.catalog:
            raise PDFNoOutlines

        def search(entry, level):
            entry = dict_value(entry)
            if 'Title' in entry:
                if 'A' in entry or 'Dest' in entry:
                    title = decode_text(str_value(entry['Title']))
                    dest = entry.get('Dest')
                    action = entry.get('A')
                    se = entry.get('SE')
                    yield (level, title, dest, action, se)
            if 'First' in entry and 'Last' in entry:
                for x in search(entry['First'], level+1):
                    yield x
            if 'Next' in entry:
                for x in search(entry['Next'], level):
                    yield x
            return
        return search(self.catalog['Outlines'], 0)

    def lookup_name(self, cat, key):
        try:
            names = dict_value(self.catalog['Names'])
        except (PDFTypeError, KeyError):
            raise KeyError((cat, key))
        # may raise KeyError
        d0 = dict_value(names[cat])

        def lookup(d):
            if 'Limits' in d:
                (k1, k2) = list_value(d['Limits'])
                if key < k1 or k2 < key:
                    return None
            if 'Names' in d:
                objs = list_value(d['Names'])
                names = dict(choplist(2, objs))
                return names[key]
            if 'Kids' in d:
                for c in list_value(d['Kids']):
                    v = lookup(dict_value(c))
                    if v:
                        return v
            raise KeyError((cat, key))
        return lookup(d0)

    def get_dest(self, name):
        try:
            # PDF-1.2 or later
            obj = self.lookup_name('Dests', name)
        except KeyError:
            # PDF-1.1 or prior
            if 'Dests' not in self.catalog:
                raise PDFDestinationNotFound(name)
            d0 = dict_value(self.catalog['Dests'])
            if name not in d0:
                raise PDFDestinationNotFound(name)
            obj = d0[name]
        return obj

    # find_xref
    def find_xref(self, parser):
        """Internal function used to locate the first XRef."""
        # search the last xref table by scanning the file backwards.
        prev = None
        for line in parser.revreadlines():
            line = line.strip()
            if 2 <= self.debug:
                print >>sys.stderr, 'find_xref: %r' % line
            if line == 'startxref':
                break
            if line:
                prev = line
        else:
            raise PDFNoValidXRef('Unexpected EOF')
        if 1 <= self.debug:
            print >>sys.stderr, 'xref found: pos=%r' % prev
        return long(prev)

    # read xref table
    def read_xref_from(self, parser, start, xrefs):
        """Reads XRefs from the given location."""
        parser.seek(start)
        parser.reset()
        try:
            (pos, token) = parser.nexttoken()
        except PSEOF:
            raise PDFNoValidXRef('Unexpected EOF')
        if 2 <= self.debug:
            print >>sys.stderr, 'read_xref_from: start=%d, token=%r' % (start, token)
        if isinstance(token, int):
            # XRefStream: PDF-1.5
            parser.seek(pos)
            parser.reset()
            xref = PDFXRefStream()
            xref.load(parser, debug=self.debug)
        else:
            if token is parser.KEYWORD_XREF:
                parser.nextline()
            xref = PDFXRef()
            xref.load(parser, debug=self.debug)
        xrefs.append(xref)
        trailer = xref.get_trailer()
        if 1 <= self.debug:
            print >>sys.stderr, 'trailer: %r' % trailer
        if 'XRefStm' in trailer:
            pos = int_value(trailer['XRefStm'])
            self.read_xref_from(parser, pos, xrefs)
        if 'Prev' in trailer:
            # find previous xref
            pos = int_value(trailer['Prev'])
            self.read_xref_from(parser, pos, xrefs)
        return

########NEW FILE########
__FILENAME__ = pdffont
#!/usr/bin/env python
import sys
import struct
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from cmapdb import CMapDB, CMapParser, FileUnicodeMap, CMap
from encodingdb import EncodingDB, name2unicode
from psparser import PSStackParser
from psparser import PSEOF
from psparser import LIT, KWD, STRICT
from psparser import PSLiteral, literal_name
from pdftypes import PDFException, resolve1
from pdftypes import int_value, num_value
from pdftypes import list_value, dict_value, stream_value
from fontmetrics import FONT_METRICS
from utils import apply_matrix_norm, nunpack, choplist, isnumber


def get_widths(seq):
    widths = {}
    r = []
    for v in seq:
        if isinstance(v, list):
            if r:
                char1 = r[-1]
                for (i, w) in enumerate(v):
                    widths[char1+i] = w
                r = []
        elif isnumber(v):
            r.append(v)
            if len(r) == 3:
                (char1, char2, w) = r
                for i in xrange(char1, char2+1):
                    widths[i] = w
                r = []
    return widths
#assert get_widths([1]) == {}
#assert get_widths([1,2,3]) == {1:3, 2:3}
#assert get_widths([1,[2,3],6,[7,8]]) == {1:2,2:3, 6:7,7:8}


def get_widths2(seq):
    widths = {}
    r = []
    for v in seq:
        if isinstance(v, list):
            if r:
                char1 = r[-1]
                for (i, (w, vx, vy)) in enumerate(choplist(3, v)):
                    widths[char1+i] = (w, (vx, vy))
                r = []
        elif isnumber(v):
            r.append(v)
            if len(r) == 5:
                (char1, char2, w, vx, vy) = r
                for i in xrange(char1, char2+1):
                    widths[i] = (w, (vx, vy))
                r = []
    return widths
#assert get_widths2([1]) == {}
#assert get_widths2([1,2,3,4,5]) == {1:(3, (4,5)), 2:(3, (4,5))}
#assert get_widths2([1,[2,3,4,5],6,[7,8,9]]) == {1:(2, (3,4)), 6:(7, (8,9))}


##  FontMetricsDB
##
class FontMetricsDB(object):

    @classmethod
    def get_metrics(klass, fontname):
        return FONT_METRICS[fontname]


##  Type1FontHeaderParser
##
class Type1FontHeaderParser(PSStackParser):

    KEYWORD_BEGIN = KWD('begin')
    KEYWORD_END = KWD('end')
    KEYWORD_DEF = KWD('def')
    KEYWORD_PUT = KWD('put')
    KEYWORD_DICT = KWD('dict')
    KEYWORD_ARRAY = KWD('array')
    KEYWORD_READONLY = KWD('readonly')
    KEYWORD_FOR = KWD('for')
    KEYWORD_FOR = KWD('for')

    def __init__(self, data):
        PSStackParser.__init__(self, data)
        self._cid2unicode = {}
        return

    def get_encoding(self):
        while 1:
            try:
                (cid, name) = self.nextobject()
            except PSEOF:
                break
            try:
                self._cid2unicode[cid] = name2unicode(name)
            except KeyError:
                pass
        return self._cid2unicode

    def do_keyword(self, pos, token):
        if token is self.KEYWORD_PUT:
            ((_, key), (_, value)) = self.pop(2)
            if (isinstance(key, int) and
                isinstance(value, PSLiteral)):
                self.add_results((key, literal_name(value)))
        return


NIBBLES = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', 'e', 'e-', None, '-')


##  CFFFont
##  (Format specified in Adobe Technical Note: #5176
##   "The Compact Font Format Specification")
##
def getdict(data):
    d = {}
    fp = StringIO(data)
    stack = []
    while 1:
        c = fp.read(1)
        if not c:
            break
        b0 = ord(c)
        if b0 <= 21:
            d[b0] = stack
            stack = []
            continue
        if b0 == 30:
            s = ''
            loop = True
            while loop:
                b = ord(fp.read(1))
                for n in (b >> 4, b & 15):
                    if n == 15:
                        loop = False
                    else:
                        s += NIBBLES[n]
            value = float(s)
        elif 32 <= b0 and b0 <= 246:
            value = b0-139
        else:
            b1 = ord(fp.read(1))
            if 247 <= b0 and b0 <= 250:
                value = ((b0-247) << 8)+b1+108
            elif 251 <= b0 and b0 <= 254:
                value = -((b0-251) << 8)-b1-108
            else:
                b2 = ord(fp.read(1))
                if 128 <= b1:
                    b1 -= 256
                if b0 == 28:
                    value = b1 << 8 | b2
                else:
                    value = b1 << 24 | b2 << 16 | struct.unpack('>H', fp.read(2))[0]
        stack.append(value)
    return d


class CFFFont(object):

    STANDARD_STRINGS = (
      '.notdef', 'space', 'exclam', 'quotedbl', 'numbersign',
      'dollar', 'percent', 'ampersand', 'quoteright', 'parenleft',
      'parenright', 'asterisk', 'plus', 'comma', 'hyphen', 'period',
      'slash', 'zero', 'one', 'two', 'three', 'four', 'five', 'six',
      'seven', 'eight', 'nine', 'colon', 'semicolon', 'less', 'equal',
      'greater', 'question', 'at', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
      'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
      'U', 'V', 'W', 'X', 'Y', 'Z', 'bracketleft', 'backslash',
      'bracketright', 'asciicircum', 'underscore', 'quoteleft', 'a',
      'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
      'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
      'braceleft', 'bar', 'braceright', 'asciitilde', 'exclamdown',
      'cent', 'sterling', 'fraction', 'yen', 'florin', 'section',
      'currency', 'quotesingle', 'quotedblleft', 'guillemotleft',
      'guilsinglleft', 'guilsinglright', 'fi', 'fl', 'endash',
      'dagger', 'daggerdbl', 'periodcentered', 'paragraph', 'bullet',
      'quotesinglbase', 'quotedblbase', 'quotedblright',
      'guillemotright', 'ellipsis', 'perthousand', 'questiondown',
      'grave', 'acute', 'circumflex', 'tilde', 'macron', 'breve',
      'dotaccent', 'dieresis', 'ring', 'cedilla', 'hungarumlaut',
      'ogonek', 'caron', 'emdash', 'AE', 'ordfeminine', 'Lslash',
      'Oslash', 'OE', 'ordmasculine', 'ae', 'dotlessi', 'lslash',
      'oslash', 'oe', 'germandbls', 'onesuperior', 'logicalnot', 'mu',
      'trademark', 'Eth', 'onehalf', 'plusminus', 'Thorn',
      'onequarter', 'divide', 'brokenbar', 'degree', 'thorn',
      'threequarters', 'twosuperior', 'registered', 'minus', 'eth',
      'multiply', 'threesuperior', 'copyright', 'Aacute',
      'Acircumflex', 'Adieresis', 'Agrave', 'Aring', 'Atilde',
      'Ccedilla', 'Eacute', 'Ecircumflex', 'Edieresis', 'Egrave',
      'Iacute', 'Icircumflex', 'Idieresis', 'Igrave', 'Ntilde',
      'Oacute', 'Ocircumflex', 'Odieresis', 'Ograve', 'Otilde',
      'Scaron', 'Uacute', 'Ucircumflex', 'Udieresis', 'Ugrave',
      'Yacute', 'Ydieresis', 'Zcaron', 'aacute', 'acircumflex',
      'adieresis', 'agrave', 'aring', 'atilde', 'ccedilla', 'eacute',
      'ecircumflex', 'edieresis', 'egrave', 'iacute', 'icircumflex',
      'idieresis', 'igrave', 'ntilde', 'oacute', 'ocircumflex',
      'odieresis', 'ograve', 'otilde', 'scaron', 'uacute',
      'ucircumflex', 'udieresis', 'ugrave', 'yacute', 'ydieresis',
      'zcaron', 'exclamsmall', 'Hungarumlautsmall', 'dollaroldstyle',
      'dollarsuperior', 'ampersandsmall', 'Acutesmall',
      'parenleftsuperior', 'parenrightsuperior', 'twodotenleader',
      'onedotenleader', 'zerooldstyle', 'oneoldstyle', 'twooldstyle',
      'threeoldstyle', 'fouroldstyle', 'fiveoldstyle', 'sixoldstyle',
      'sevenoldstyle', 'eightoldstyle', 'nineoldstyle',
      'commasuperior', 'threequartersemdash', 'periodsuperior',
      'questionsmall', 'asuperior', 'bsuperior', 'centsuperior',
      'dsuperior', 'esuperior', 'isuperior', 'lsuperior', 'msuperior',
      'nsuperior', 'osuperior', 'rsuperior', 'ssuperior', 'tsuperior',
      'ff', 'ffi', 'ffl', 'parenleftinferior', 'parenrightinferior',
      'Circumflexsmall', 'hyphensuperior', 'Gravesmall', 'Asmall',
      'Bsmall', 'Csmall', 'Dsmall', 'Esmall', 'Fsmall', 'Gsmall',
      'Hsmall', 'Ismall', 'Jsmall', 'Ksmall', 'Lsmall', 'Msmall',
      'Nsmall', 'Osmall', 'Psmall', 'Qsmall', 'Rsmall', 'Ssmall',
      'Tsmall', 'Usmall', 'Vsmall', 'Wsmall', 'Xsmall', 'Ysmall',
      'Zsmall', 'colonmonetary', 'onefitted', 'rupiah', 'Tildesmall',
      'exclamdownsmall', 'centoldstyle', 'Lslashsmall', 'Scaronsmall',
      'Zcaronsmall', 'Dieresissmall', 'Brevesmall', 'Caronsmall',
      'Dotaccentsmall', 'Macronsmall', 'figuredash', 'hypheninferior',
      'Ogoneksmall', 'Ringsmall', 'Cedillasmall', 'questiondownsmall',
      'oneeighth', 'threeeighths', 'fiveeighths', 'seveneighths',
      'onethird', 'twothirds', 'zerosuperior', 'foursuperior',
      'fivesuperior', 'sixsuperior', 'sevensuperior', 'eightsuperior',
      'ninesuperior', 'zeroinferior', 'oneinferior', 'twoinferior',
      'threeinferior', 'fourinferior', 'fiveinferior', 'sixinferior',
      'seveninferior', 'eightinferior', 'nineinferior',
      'centinferior', 'dollarinferior', 'periodinferior',
      'commainferior', 'Agravesmall', 'Aacutesmall',
      'Acircumflexsmall', 'Atildesmall', 'Adieresissmall',
      'Aringsmall', 'AEsmall', 'Ccedillasmall', 'Egravesmall',
      'Eacutesmall', 'Ecircumflexsmall', 'Edieresissmall',
      'Igravesmall', 'Iacutesmall', 'Icircumflexsmall',
      'Idieresissmall', 'Ethsmall', 'Ntildesmall', 'Ogravesmall',
      'Oacutesmall', 'Ocircumflexsmall', 'Otildesmall',
      'Odieresissmall', 'OEsmall', 'Oslashsmall', 'Ugravesmall',
      'Uacutesmall', 'Ucircumflexsmall', 'Udieresissmall',
      'Yacutesmall', 'Thornsmall', 'Ydieresissmall', '001.000',
      '001.001', '001.002', '001.003', 'Black', 'Bold', 'Book',
      'Light', 'Medium', 'Regular', 'Roman', 'Semibold',
    )

    class INDEX(object):

        def __init__(self, fp):
            self.fp = fp
            self.offsets = []
            (count, offsize) = struct.unpack('>HB', self.fp.read(3))
            for i in xrange(count+1):
                self.offsets.append(nunpack(self.fp.read(offsize)))
            self.base = self.fp.tell()-1
            self.fp.seek(self.base+self.offsets[-1])
            return

        def __repr__(self):
            return '<INDEX: size=%d>' % len(self)

        def __len__(self):
            return len(self.offsets)-1

        def __getitem__(self, i):
            self.fp.seek(self.base+self.offsets[i])
            return self.fp.read(self.offsets[i+1]-self.offsets[i])

        def __iter__(self):
            return iter(self[i] for i in xrange(len(self)))

    def __init__(self, name, fp):
        self.name = name
        self.fp = fp
        # Header
        (_major, _minor, hdrsize, offsize) = struct.unpack('BBBB', self.fp.read(4))
        self.fp.read(hdrsize-4)
        # Name INDEX
        self.name_index = self.INDEX(self.fp)
        # Top DICT INDEX
        self.dict_index = self.INDEX(self.fp)
        # String INDEX
        self.string_index = self.INDEX(self.fp)
        # Global Subr INDEX
        self.subr_index = self.INDEX(self.fp)
        # Top DICT DATA
        self.top_dict = getdict(self.dict_index[0])
        (charset_pos,) = self.top_dict.get(15, [0])
        (encoding_pos,) = self.top_dict.get(16, [0])
        (charstring_pos,) = self.top_dict.get(17, [0])
        # CharStrings
        self.fp.seek(charstring_pos)
        self.charstring = self.INDEX(self.fp)
        self.nglyphs = len(self.charstring)
        # Encodings
        self.code2gid = {}
        self.gid2code = {}
        self.fp.seek(encoding_pos)
        format = self.fp.read(1)
        if format == '\x00':
            # Format 0
            (n,) = struct.unpack('B', self.fp.read(1))
            for (code, gid) in enumerate(struct.unpack('B'*n, self.fp.read(n))):
                self.code2gid[code] = gid
                self.gid2code[gid] = code
        elif format == '\x01':
            # Format 1
            (n,) = struct.unpack('B', self.fp.read(1))
            code = 0
            for i in xrange(n):
                (first, nleft) = struct.unpack('BB', self.fp.read(2))
                for gid in xrange(first, first+nleft+1):
                    self.code2gid[code] = gid
                    self.gid2code[gid] = code
                    code += 1
        else:
            raise ValueError('unsupported encoding format: %r' % format)
        # Charsets
        self.name2gid = {}
        self.gid2name = {}
        self.fp.seek(charset_pos)
        format = self.fp.read(1)
        if format == '\x00':
            # Format 0
            n = self.nglyphs-1
            for (gid, sid) in enumerate(struct.unpack('>'+'H'*n, self.fp.read(2*n))):
                gid += 1
                name = self.getstr(sid)
                self.name2gid[name] = gid
                self.gid2name[gid] = name
        elif format == '\x01':
            # Format 1
            (n,) = struct.unpack('B', self.fp.read(1))
            sid = 0
            for i in xrange(n):
                (first, nleft) = struct.unpack('BB', self.fp.read(2))
                for gid in xrange(first, first+nleft+1):
                    name = self.getstr(sid)
                    self.name2gid[name] = gid
                    self.gid2name[gid] = name
                    sid += 1
        elif format == '\x02':
            # Format 2
            assert 0
        else:
            raise ValueError('unsupported charset format: %r' % format)
        #print self.code2gid
        #print self.name2gid
        #assert 0
        return

    def getstr(self, sid):
        if sid < len(self.STANDARD_STRINGS):
            return self.STANDARD_STRINGS[sid]
        return self.string_index[sid-len(self.STANDARD_STRINGS)]


##  TrueTypeFont
##
class TrueTypeFont(object):

    class CMapNotFound(Exception):
        pass

    def __init__(self, name, fp):
        self.name = name
        self.fp = fp
        self.tables = {}
        self.fonttype = fp.read(4)
        (ntables, _1, _2, _3) = struct.unpack('>HHHH', fp.read(8))
        for _ in xrange(ntables):
            (name, tsum, offset, length) = struct.unpack('>4sLLL', fp.read(16))
            self.tables[name] = (offset, length)
        return

    def create_unicode_map(self):
        if 'cmap' not in self.tables:
            raise TrueTypeFont.CMapNotFound
        (base_offset, length) = self.tables['cmap']
        fp = self.fp
        fp.seek(base_offset)
        (version, nsubtables) = struct.unpack('>HH', fp.read(4))
        subtables = []
        for i in xrange(nsubtables):
            subtables.append(struct.unpack('>HHL', fp.read(8)))
        char2gid = {}
        # Only supports subtable type 0, 2 and 4.
        for (_1, _2, st_offset) in subtables:
            fp.seek(base_offset+st_offset)
            (fmttype, fmtlen, fmtlang) = struct.unpack('>HHH', fp.read(6))
            if fmttype == 0:
                char2gid.update(enumerate(struct.unpack('>256B', fp.read(256))))
            elif fmttype == 2:
                subheaderkeys = struct.unpack('>256H', fp.read(512))
                firstbytes = [0]*8192
                for (i, k) in enumerate(subheaderkeys):
                    firstbytes[k//8] = i
                nhdrs = max(subheaderkeys)//8 + 1
                hdrs = []
                for i in xrange(nhdrs):
                    (firstcode, entcount, delta, offset) = struct.unpack('>HHhH', fp.read(8))
                    hdrs.append((i, firstcode, entcount, delta, fp.tell()-2+offset))
                for (i, firstcode, entcount, delta, pos) in hdrs:
                    if not entcount:
                        continue
                    first = firstcode + (firstbytes[i] << 8)
                    fp.seek(pos)
                    for c in xrange(entcount):
                        gid = struct.unpack('>H', fp.read(2))
                        if gid:
                            gid += delta
                        char2gid[first+c] = gid
            elif fmttype == 4:
                (segcount, _1, _2, _3) = struct.unpack('>HHHH', fp.read(8))
                segcount //= 2
                ecs = struct.unpack('>%dH' % segcount, fp.read(2*segcount))
                fp.read(2)
                scs = struct.unpack('>%dH' % segcount, fp.read(2*segcount))
                idds = struct.unpack('>%dh' % segcount, fp.read(2*segcount))
                pos = fp.tell()
                idrs = struct.unpack('>%dH' % segcount, fp.read(2*segcount))
                for (ec, sc, idd, idr) in zip(ecs, scs, idds, idrs):
                    if idr:
                        fp.seek(pos+idr)
                        for c in xrange(sc, ec+1):
                            char2gid[c] = (struct.unpack('>H', fp.read(2))[0] + idd) & 0xffff
                    else:
                        for c in xrange(sc, ec+1):
                            char2gid[c] = (c + idd) & 0xffff
            else:
                assert 0
        # create unicode map
        unicode_map = FileUnicodeMap()
        for (char, gid) in char2gid.iteritems():
            unicode_map.add_cid2unichr(gid, char)
        return unicode_map


##  Fonts
##
class PDFFontError(PDFException):
    pass


class PDFUnicodeNotDefined(PDFFontError):
    pass

LITERAL_STANDARD_ENCODING = LIT('StandardEncoding')
LITERAL_TYPE1C = LIT('Type1C')


# PDFFont
class PDFFont(object):

    def __init__(self, descriptor, widths, default_width=None):
        self.descriptor = descriptor
        self.widths = widths
        self.fontname = resolve1(descriptor.get('FontName', 'unknown'))
        if isinstance(self.fontname, PSLiteral):
            self.fontname = literal_name(self.fontname)
        self.flags = int_value(descriptor.get('Flags', 0))
        self.ascent = num_value(descriptor.get('Ascent', 0))
        self.descent = num_value(descriptor.get('Descent', 0))
        self.italic_angle = num_value(descriptor.get('ItalicAngle', 0))
        self.default_width = default_width or num_value(descriptor.get('MissingWidth', 0))
        self.leading = num_value(descriptor.get('Leading', 0))
        self.bbox = list_value(descriptor.get('FontBBox', (0, 0, 0, 0)))
        self.hscale = self.vscale = .001
        return

    def __repr__(self):
        return '<PDFFont>'

    def is_vertical(self):
        return False

    def is_multibyte(self):
        return False

    def decode(self, bytes):
        return map(ord, bytes)

    def get_ascent(self):
        return self.ascent * self.vscale

    def get_descent(self):
        return self.descent * self.vscale

    def get_width(self):
        w = self.bbox[2]-self.bbox[0]
        if w == 0:
            w = -self.default_width
        return w * self.hscale

    def get_height(self):
        h = self.bbox[3]-self.bbox[1]
        if h == 0:
            h = self.ascent - self.descent
        return h * self.vscale

    def char_width(self, cid):
        try:
            return self.widths[cid] * self.hscale
        except KeyError:
            try:
                return self.widths[self.to_unichr(cid)] * self.hscale
            except (KeyError, PDFUnicodeNotDefined):
                return self.default_width * self.hscale

    def char_disp(self, cid):
        return 0

    def string_width(self, s):
        return sum(self.char_width(cid) for cid in self.decode(s))


# PDFSimpleFont
class PDFSimpleFont(PDFFont):

    def __init__(self, descriptor, widths, spec):
        # Font encoding is specified either by a name of
        # built-in encoding or a dictionary that describes
        # the differences.
        if 'Encoding' in spec:
            encoding = resolve1(spec['Encoding'])
        else:
            encoding = LITERAL_STANDARD_ENCODING
        if isinstance(encoding, dict):
            name = literal_name(encoding.get('BaseEncoding', LITERAL_STANDARD_ENCODING))
            diff = list_value(encoding.get('Differences', None))
            self.cid2unicode = EncodingDB.get_encoding(name, diff)
        else:
            self.cid2unicode = EncodingDB.get_encoding(literal_name(encoding))
        self.unicode_map = None
        if 'ToUnicode' in spec:
            strm = stream_value(spec['ToUnicode'])
            self.unicode_map = FileUnicodeMap()
            CMapParser(self.unicode_map, StringIO(strm.get_data())).run()
        PDFFont.__init__(self, descriptor, widths)
        return

    def to_unichr(self, cid):
        if self.unicode_map:
            try:
                return self.unicode_map.get_unichr(cid)
            except KeyError:
                pass
        try:
            return self.cid2unicode[cid]
        except KeyError:
            raise PDFUnicodeNotDefined(None, cid)


# PDFType1Font
class PDFType1Font(PDFSimpleFont):

    def __init__(self, rsrcmgr, spec):
        try:
            self.basefont = literal_name(spec['BaseFont'])
        except KeyError:
            if STRICT:
                raise PDFFontError('BaseFont is missing')
            self.basefont = 'unknown'
        try:
            (descriptor, widths) = FontMetricsDB.get_metrics(self.basefont)
        except KeyError:
            descriptor = dict_value(spec.get('FontDescriptor', {}))
            firstchar = int_value(spec.get('FirstChar', 0))
            lastchar = int_value(spec.get('LastChar', 255))
            widths = list_value(spec.get('Widths', [0]*256))
            widths = dict((i+firstchar, w) for (i, w) in enumerate(widths))
        PDFSimpleFont.__init__(self, descriptor, widths, spec)
        if 'Encoding' not in spec and 'FontFile' in descriptor:
            # try to recover the missing encoding info from the font file.
            self.fontfile = stream_value(descriptor.get('FontFile'))
            length1 = int_value(self.fontfile['Length1'])
            data = self.fontfile.get_data()[:length1]
            parser = Type1FontHeaderParser(StringIO(data))
            self.cid2unicode = parser.get_encoding()
        return

    def __repr__(self):
        return '<PDFType1Font: basefont=%r>' % self.basefont


# PDFTrueTypeFont
class PDFTrueTypeFont(PDFType1Font):

    def __repr__(self):
        return '<PDFTrueTypeFont: basefont=%r>' % self.basefont


# PDFType3Font
class PDFType3Font(PDFSimpleFont):

    def __init__(self, rsrcmgr, spec):
        firstchar = int_value(spec.get('FirstChar', 0))
        lastchar = int_value(spec.get('LastChar', 0))
        widths = list_value(spec.get('Widths', [0]*256))
        widths = dict((i+firstchar, w) for (i, w) in enumerate(widths))
        if 'FontDescriptor' in spec:
            descriptor = dict_value(spec['FontDescriptor'])
        else:
            descriptor = {'Ascent': 0, 'Descent': 0,
                          'FontBBox': spec['FontBBox']}
        PDFSimpleFont.__init__(self, descriptor, widths, spec)
        self.matrix = tuple(list_value(spec.get('FontMatrix')))
        (_, self.descent, _, self.ascent) = self.bbox
        (self.hscale, self.vscale) = apply_matrix_norm(self.matrix, (1, 1))
        return

    def __repr__(self):
        return '<PDFType3Font>'


# PDFCIDFont
class PDFCIDFont(PDFFont):

    def __init__(self, rsrcmgr, spec):
        try:
            self.basefont = literal_name(spec['BaseFont'])
        except KeyError:
            if STRICT:
                raise PDFFontError('BaseFont is missing')
            self.basefont = 'unknown'
        self.cidsysteminfo = dict_value(spec.get('CIDSystemInfo', {}))
        self.cidcoding = '%s-%s' % (self.cidsysteminfo.get('Registry', 'unknown'),
                                    self.cidsysteminfo.get('Ordering', 'unknown'))
        try:
            name = literal_name(spec['Encoding'])
        except KeyError:
            if STRICT:
                raise PDFFontError('Encoding is unspecified')
            name = 'unknown'
        try:
            self.cmap = CMapDB.get_cmap(name)
        except CMapDB.CMapNotFound, e:
            if STRICT:
                raise PDFFontError(e)
            self.cmap = CMap()
        try:
            descriptor = dict_value(spec['FontDescriptor'])
        except KeyError:
            if STRICT:
                raise PDFFontError('FontDescriptor is missing')
            descriptor = {}
        ttf = None
        if 'FontFile2' in descriptor:
            self.fontfile = stream_value(descriptor.get('FontFile2'))
            ttf = TrueTypeFont(self.basefont,
                               StringIO(self.fontfile.get_data()))
        self.unicode_map = None
        if 'ToUnicode' in spec:
            strm = stream_value(spec['ToUnicode'])
            self.unicode_map = FileUnicodeMap()
            CMapParser(self.unicode_map, StringIO(strm.get_data())).run()
        elif self.cidcoding in ('Adobe-Identity', 'Adobe-UCS'):
            if ttf:
                try:
                    self.unicode_map = ttf.create_unicode_map()
                except TrueTypeFont.CMapNotFound:
                    pass
        else:
            try:
                self.unicode_map = CMapDB.get_unicode_map(self.cidcoding, self.cmap.is_vertical())
            except CMapDB.CMapNotFound, e:
                pass

        self.vertical = self.cmap.is_vertical()
        if self.vertical:
            # writing mode: vertical
            widths = get_widths2(list_value(spec.get('W2', [])))
            self.disps = dict((cid, (vx, vy)) for (cid, (_, (vx, vy))) in widths.iteritems())
            (vy, w) = spec.get('DW2', [880, -1000])
            self.default_disp = (None, vy)
            widths = dict((cid, w) for (cid, (w, _)) in widths.iteritems())
            default_width = w
        else:
            # writing mode: horizontal
            self.disps = {}
            self.default_disp = 0
            widths = get_widths(list_value(spec.get('W', [])))
            default_width = spec.get('DW', 1000)
        PDFFont.__init__(self, descriptor, widths, default_width=default_width)
        return

    def __repr__(self):
        return '<PDFCIDFont: basefont=%r, cidcoding=%r>' % (self.basefont, self.cidcoding)

    def is_vertical(self):
        return self.vertical

    def is_multibyte(self):
        return True

    def decode(self, bytes):
        return self.cmap.decode(bytes)

    def char_disp(self, cid):
        "Returns an integer for horizontal fonts, a tuple for vertical fonts."
        return self.disps.get(cid, self.default_disp)

    def to_unichr(self, cid):
        try:
            if not self.unicode_map:
                raise KeyError(cid)
            return self.unicode_map.get_unichr(cid)
        except KeyError:
            raise PDFUnicodeNotDefined(self.cidcoding, cid)


# main
def main(argv):
    for fname in argv[1:]:
        fp = file(fname, 'rb')
        #font = TrueTypeFont(fname, fp)
        font = CFFFont(fname, fp)
        print font
        fp.close()
    return

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = pdfinterp
#!/usr/bin/env python
import sys
import re
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from cmapdb import CMapDB, CMap
from psparser import PSTypeError, PSEOF
from psparser import PSKeyword, literal_name, keyword_name
from psparser import PSStackParser
from psparser import LIT, KWD, STRICT
from pdftypes import PDFException, PDFStream, PDFObjRef
from pdftypes import resolve1
from pdftypes import list_value, dict_value, stream_value
from pdffont import PDFFontError
from pdffont import PDFType1Font, PDFTrueTypeFont, PDFType3Font
from pdffont import PDFCIDFont
from pdfcolor import PDFColorSpace
from pdfcolor import PREDEFINED_COLORSPACE
from pdfcolor import LITERAL_DEVICE_GRAY, LITERAL_DEVICE_RGB
from pdfcolor import LITERAL_DEVICE_CMYK
from utils import choplist
from utils import mult_matrix, MATRIX_IDENTITY


##  Exceptions
##
class PDFResourceError(PDFException):
    pass

class PDFInterpreterError(PDFException):
    pass


##  Constants
##
LITERAL_PDF = LIT('PDF')
LITERAL_TEXT = LIT('Text')
LITERAL_FONT = LIT('Font')
LITERAL_FORM = LIT('Form')
LITERAL_IMAGE = LIT('Image')


##  PDFTextState
##
class PDFTextState(object):

    def __init__(self):
        self.font = None
        self.fontsize = 0
        self.charspace = 0
        self.wordspace = 0
        self.scaling = 100
        self.leading = 0
        self.render = 0
        self.rise = 0
        self.reset()
        # self.matrix is set
        # self.linematrix is set
        return

    def __repr__(self):
        return ('<PDFTextState: font=%r, fontsize=%r, charspace=%r, wordspace=%r, '
                ' scaling=%r, leading=%r, render=%r, rise=%r, '
                ' matrix=%r, linematrix=%r>' %
                (self.font, self.fontsize, self.charspace, self.wordspace,
                 self.scaling, self.leading, self.render, self.rise,
                 self.matrix, self.linematrix))

    def copy(self):
        obj = PDFTextState()
        obj.font = self.font
        obj.fontsize = self.fontsize
        obj.charspace = self.charspace
        obj.wordspace = self.wordspace
        obj.scaling = self.scaling
        obj.leading = self.leading
        obj.render = self.render
        obj.rise = self.rise
        obj.matrix = self.matrix
        obj.linematrix = self.linematrix
        return obj

    def reset(self):
        self.matrix = MATRIX_IDENTITY
        self.linematrix = (0, 0)
        return


##  PDFGraphicState
##
class PDFGraphicState(object):

    def __init__(self):
        self.linewidth = 0
        self.linecap = None
        self.linejoin = None
        self.miterlimit = None
        self.dash = None
        self.intent = None
        self.flatness = None
        return

    def copy(self):
        obj = PDFGraphicState()
        obj.linewidth = self.linewidth
        obj.linecap = self.linecap
        obj.linejoin = self.linejoin
        obj.miterlimit = self.miterlimit
        obj.dash = self.dash
        obj.intent = self.intent
        obj.flatness = self.flatness
        return obj

    def __repr__(self):
        return ('<PDFGraphicState: linewidth=%r, linecap=%r, linejoin=%r, '
                ' miterlimit=%r, dash=%r, intent=%r, flatness=%r>' %
                (self.linewidth, self.linecap, self.linejoin,
                 self.miterlimit, self.dash, self.intent, self.flatness))


##  Resource Manager
##
class PDFResourceManager(object):

    """Repository of shared resources.

    ResourceManager facilitates reuse of shared resources
    such as fonts and images so that large objects are not
    allocated multiple times.
    """
    debug = 0

    def __init__(self, caching=True):
        self.caching = caching
        self._cached_fonts = {}
        return

    def get_procset(self, procs):
        for proc in procs:
            if proc is LITERAL_PDF:
                pass
            elif proc is LITERAL_TEXT:
                pass
            else:
                #raise PDFResourceError('ProcSet %r is not supported.' % proc)
                pass
        return

    def get_cmap(self, cmapname, strict=False):
        try:
            return CMapDB.get_cmap(cmapname)
        except CMapDB.CMapNotFound:
            if strict:
                raise
            return CMap()

    def get_font(self, objid, spec):
        if objid and objid in self._cached_fonts:
            font = self._cached_fonts[objid]
        else:
            if 2 <= self.debug:
                print >>sys.stderr, 'get_font: create: objid=%r, spec=%r' % (objid, spec)
            if STRICT:
                if spec['Type'] is not LITERAL_FONT:
                    raise PDFFontError('Type is not /Font')
            # Create a Font object.
            if 'Subtype' in spec:
                subtype = literal_name(spec['Subtype'])
            else:
                if STRICT:
                    raise PDFFontError('Font Subtype is not specified.')
                subtype = 'Type1'
            if subtype in ('Type1', 'MMType1'):
                # Type1 Font
                font = PDFType1Font(self, spec)
            elif subtype == 'TrueType':
                # TrueType Font
                font = PDFTrueTypeFont(self, spec)
            elif subtype == 'Type3':
                # Type3 Font
                font = PDFType3Font(self, spec)
            elif subtype in ('CIDFontType0', 'CIDFontType2'):
                # CID Font
                font = PDFCIDFont(self, spec)
            elif subtype == 'Type0':
                # Type0 Font
                dfonts = list_value(spec['DescendantFonts'])
                assert dfonts
                subspec = dict_value(dfonts[0]).copy()
                for k in ('Encoding', 'ToUnicode'):
                    if k in spec:
                        subspec[k] = resolve1(spec[k])
                font = self.get_font(None, subspec)
            else:
                if STRICT:
                    raise PDFFontError('Invalid Font spec: %r' % spec)
                font = PDFType1Font(self, spec)  # this is so wrong!
            if objid and self.caching:
                self._cached_fonts[objid] = font
        return font


##  PDFContentParser
##
class PDFContentParser(PSStackParser):

    def __init__(self, streams):
        self.streams = streams
        self.istream = 0
        PSStackParser.__init__(self, None)
        return

    def fillfp(self):
        if not self.fp:
            if self.istream < len(self.streams):
                strm = stream_value(self.streams[self.istream])
                self.istream += 1
            else:
                raise PSEOF('Unexpected EOF, file truncated?')
            self.fp = StringIO(strm.get_data())
        return

    def seek(self, pos):
        self.fillfp()
        PSStackParser.seek(self, pos)
        return

    def fillbuf(self):
        if self.charpos < len(self.buf):
            return
        while 1:
            self.fillfp()
            self.bufpos = self.fp.tell()
            self.buf = self.fp.read(self.BUFSIZ)
            if self.buf:
                break
            self.fp = None
        self.charpos = 0
        return

    def get_inline_data(self, pos, target='EI'):
        self.seek(pos)
        i = 0
        data = ''
        while i <= len(target):
            self.fillbuf()
            if i:
                c = self.buf[self.charpos]
                data += c
                self.charpos += 1
                if len(target) <= i and c.isspace():
                    i += 1
                elif i < len(target) and c == target[i]:
                    i += 1
                else:
                    i = 0
            else:
                try:
                    j = self.buf.index(target[0], self.charpos)
                    #print 'found', (0, self.buf[j:j+10])
                    data += self.buf[self.charpos:j+1]
                    self.charpos = j+1
                    i = 1
                except ValueError:
                    data += self.buf[self.charpos:]
                    self.charpos = len(self.buf)
        data = data[:-(len(target)+1)]  # strip the last part
        data = re.sub(r'(\x0d\x0a|[\x0d\x0a])$', '', data)
        return (pos, data)

    def flush(self):
        self.add_results(*self.popall())
        return

    KEYWORD_BI = KWD('BI')
    KEYWORD_ID = KWD('ID')
    KEYWORD_EI = KWD('EI')

    def do_keyword(self, pos, token):
        if token is self.KEYWORD_BI:
            # inline image within a content stream
            self.start_type(pos, 'inline')
        elif token is self.KEYWORD_ID:
            try:
                (_, objs) = self.end_type('inline')
                if len(objs) % 2 != 0:
                    raise PSTypeError('Invalid dictionary construct: %r' % objs)
                d = dict((literal_name(k), v) for (k, v) in choplist(2, objs))
                (pos, data) = self.get_inline_data(pos+len('ID '))
                obj = PDFStream(d, data)
                self.push((pos, obj))
                self.push((pos, self.KEYWORD_EI))
            except PSTypeError:
                if STRICT:
                    raise
        else:
            self.push((pos, token))
        return


##  Interpreter
##
class PDFPageInterpreter(object):

    debug = 0

    def __init__(self, rsrcmgr, device):
        self.rsrcmgr = rsrcmgr
        self.device = device
        return

    def dup(self):
        return self.__class__(self.rsrcmgr, self.device)

    # init_resources(resources):
    #   Prepare the fonts and XObjects listed in the Resource attribute.
    def init_resources(self, resources):
        self.resources = resources
        self.fontmap = {}
        self.xobjmap = {}
        self.csmap = PREDEFINED_COLORSPACE.copy()
        if not resources:
            return

        def get_colorspace(spec):
            if isinstance(spec, list):
                name = literal_name(spec[0])
            else:
                name = literal_name(spec)
            if name == 'ICCBased' and isinstance(spec, list) and 2 <= len(spec):
                return PDFColorSpace(name, stream_value(spec[1])['N'])
            elif name == 'DeviceN' and isinstance(spec, list) and 2 <= len(spec):
                return PDFColorSpace(name, len(list_value(spec[1])))
            else:
                return PREDEFINED_COLORSPACE.get(name)
        for (k, v) in dict_value(resources).iteritems():
            if 2 <= self.debug:
                print >>sys.stderr, 'Resource: %r: %r' % (k, v)
            if k == 'Font':
                for (fontid, spec) in dict_value(v).iteritems():
                    objid = None
                    if isinstance(spec, PDFObjRef):
                        objid = spec.objid
                    spec = dict_value(spec)
                    self.fontmap[fontid] = self.rsrcmgr.get_font(objid, spec)
            elif k == 'ColorSpace':
                for (csid, spec) in dict_value(v).iteritems():
                    self.csmap[csid] = get_colorspace(resolve1(spec))
            elif k == 'ProcSet':
                self.rsrcmgr.get_procset(list_value(v))
            elif k == 'XObject':
                for (xobjid, xobjstrm) in dict_value(v).iteritems():
                    self.xobjmap[xobjid] = xobjstrm
        return

    # init_state(ctm)
    #   Initialize the text and graphic states for rendering a page.
    def init_state(self, ctm):
        # gstack: stack for graphical states.
        self.gstack = []
        self.ctm = ctm
        self.device.set_ctm(self.ctm)
        self.textstate = PDFTextState()
        self.graphicstate = PDFGraphicState()
        self.curpath = []
        # argstack: stack for command arguments.
        self.argstack = []
        # set some global states.
        self.scs = self.ncs = None
        if self.csmap:
            self.scs = self.ncs = self.csmap.values()[0]
        return

    def push(self, obj):
        self.argstack.append(obj)
        return

    def pop(self, n):
        if n == 0:
            return []
        x = self.argstack[-n:]
        self.argstack = self.argstack[:-n]
        return x

    def get_current_state(self):
        return (self.ctm, self.textstate.copy(), self.graphicstate.copy())

    def set_current_state(self, state):
        (self.ctm, self.textstate, self.graphicstate) = state
        self.device.set_ctm(self.ctm)
        return

    # gsave
    def do_q(self):
        self.gstack.append(self.get_current_state())
        return

    # grestore
    def do_Q(self):
        if self.gstack:
            self.set_current_state(self.gstack.pop())
        return

    # concat-matrix
    def do_cm(self, a1, b1, c1, d1, e1, f1):
        self.ctm = mult_matrix((a1, b1, c1, d1, e1, f1), self.ctm)
        self.device.set_ctm(self.ctm)
        return

    # setlinewidth
    def do_w(self, linewidth):
        self.graphicstate.linewidth = linewidth
        return

    # setlinecap
    def do_J(self, linecap):
        self.graphicstate.linecap = linecap
        return

    # setlinejoin
    def do_j(self, linejoin):
        self.graphicstate.linejoin = linejoin
        return

    # setmiterlimit
    def do_M(self, miterlimit):
        self.graphicstate.miterlimit = miterlimit
        return

    # setdash
    def do_d(self, dash, phase):
        self.graphicstate.dash = (dash, phase)
        return

    # setintent
    def do_ri(self, intent):
        self.graphicstate.intent = intent
        return

    # setflatness
    def do_i(self, flatness):
        self.graphicstate.flatness = flatness
        return

    # load-gstate
    def do_gs(self, name):
        #XXX
        return

    # moveto
    def do_m(self, x, y):
        self.curpath.append(('m', x, y))
        return

    # lineto
    def do_l(self, x, y):
        self.curpath.append(('l', x, y))
        return

    # curveto
    def do_c(self, x1, y1, x2, y2, x3, y3):
        self.curpath.append(('c', x1, y1, x2, y2, x3, y3))
        return

    # urveto
    def do_v(self, x2, y2, x3, y3):
        self.curpath.append(('v', x2, y2, x3, y3))
        return

    # rveto
    def do_y(self, x1, y1, x3, y3):
        self.curpath.append(('y', x1, y1, x3, y3))
        return

    # closepath
    def do_h(self):
        self.curpath.append(('h',))
        return

    # rectangle
    def do_re(self, x, y, w, h):
        self.curpath.append(('m', x, y))
        self.curpath.append(('l', x+w, y))
        self.curpath.append(('l', x+w, y+h))
        self.curpath.append(('l', x, y+h))
        self.curpath.append(('h',))
        return

    # stroke
    def do_S(self):
        self.device.paint_path(self.graphicstate, True, False, False, self.curpath)
        self.curpath = []
        return

    # close-and-stroke
    def do_s(self):
        self.do_h()
        self.do_S()
        return

    # fill
    def do_f(self):
        self.device.paint_path(self.graphicstate, False, True, False, self.curpath)
        self.curpath = []
        return
    # fill (obsolete)
    do_F = do_f

    # fill-even-odd
    def do_f_a(self):
        self.device.paint_path(self.graphicstate, False, True, True, self.curpath)
        self.curpath = []
        return

    # fill-and-stroke
    def do_B(self):
        self.device.paint_path(self.graphicstate, True, True, False, self.curpath)
        self.curpath = []
        return

    # fill-and-stroke-even-odd
    def do_B_a(self):
        self.device.paint_path(self.graphicstate, True, True, True, self.curpath)
        self.curpath = []
        return

    # close-fill-and-stroke
    def do_b(self):
        self.do_h()
        self.do_B()
        return

    # close-fill-and-stroke-even-odd
    def do_b_a(self):
        self.do_h()
        self.do_B_a()
        return

    # close-only
    def do_n(self):
        self.curpath = []
        return

    # clip
    def do_W(self):
        return

    # clip-even-odd
    def do_W_a(self):
        return

    # setcolorspace-stroking
    def do_CS(self, name):
        try:
            self.scs = self.csmap[literal_name(name)]
        except KeyError:
            if STRICT:
                raise PDFInterpreterError('Undefined ColorSpace: %r' % name)
        return

    # setcolorspace-non-strokine
    def do_cs(self, name):
        try:
            self.ncs = self.csmap[literal_name(name)]
        except KeyError:
            if STRICT:
                raise PDFInterpreterError('Undefined ColorSpace: %r' % name)
        return

    # setgray-stroking
    def do_G(self, gray):
        #self.do_CS(LITERAL_DEVICE_GRAY)
        return

    # setgray-non-stroking
    def do_g(self, gray):
        #self.do_cs(LITERAL_DEVICE_GRAY)
        return

    # setrgb-stroking
    def do_RG(self, r, g, b):
        #self.do_CS(LITERAL_DEVICE_RGB)
        return

    # setrgb-non-stroking
    def do_rg(self, r, g, b):
        #self.do_cs(LITERAL_DEVICE_RGB)
        return

    # setcmyk-stroking
    def do_K(self, c, m, y, k):
        #self.do_CS(LITERAL_DEVICE_CMYK)
        return

    # setcmyk-non-stroking
    def do_k(self, c, m, y, k):
        #self.do_cs(LITERAL_DEVICE_CMYK)
        return

    # setcolor
    def do_SCN(self):
        if self.scs:
            n = self.scs.ncomponents
        else:
            if STRICT:
                raise PDFInterpreterError('No colorspace specified!')
            n = 1
        self.pop(n)
        return

    def do_scn(self):
        if self.ncs:
            n = self.ncs.ncomponents
        else:
            if STRICT:
                raise PDFInterpreterError('No colorspace specified!')
            n = 1
        self.pop(n)
        return

    def do_SC(self):
        self.do_SCN()
        return

    def do_sc(self):
        self.do_scn()
        return

    # sharing-name
    def do_sh(self, name):
        return

    # begin-text
    def do_BT(self):
        self.textstate.reset()
        return

    # end-text
    def do_ET(self):
        return

    # begin-compat
    def do_BX(self):
        return

    # end-compat
    def do_EX(self):
        return

    # marked content operators
    def do_MP(self, tag):
        self.device.do_tag(tag)
        return

    def do_DP(self, tag, props):
        self.device.do_tag(tag, props)
        return

    def do_BMC(self, tag):
        self.device.begin_tag(tag)
        return

    def do_BDC(self, tag, props):
        self.device.begin_tag(tag, props)
        return

    def do_EMC(self):
        self.device.end_tag()
        return

    # setcharspace
    def do_Tc(self, space):
        self.textstate.charspace = space
        return

    # setwordspace
    def do_Tw(self, space):
        self.textstate.wordspace = space
        return

    # textscale
    def do_Tz(self, scale):
        self.textstate.scaling = scale
        return

    # setleading
    def do_TL(self, leading):
        self.textstate.leading = -leading
        return

    # selectfont
    def do_Tf(self, fontid, fontsize):
        try:
            self.textstate.font = self.fontmap[literal_name(fontid)]
        except KeyError:
            if STRICT:
                raise PDFInterpreterError('Undefined Font id: %r' % fontid)
            self.textstate.font = self.rsrcmgr.get_font(None, {})
        self.textstate.fontsize = fontsize
        return

    # setrendering
    def do_Tr(self, render):
        self.textstate.render = render
        return

    # settextrise
    def do_Ts(self, rise):
        self.textstate.rise = rise
        return

    # text-move
    def do_Td(self, tx, ty):
        (a, b, c, d, e, f) = self.textstate.matrix
        self.textstate.matrix = (a, b, c, d, tx*a+ty*c+e, tx*b+ty*d+f)
        self.textstate.linematrix = (0, 0)
        #print >>sys.stderr, 'Td(%r,%r): %r' % (tx, ty, self.textstate)
        return

    # text-move
    def do_TD(self, tx, ty):
        (a, b, c, d, e, f) = self.textstate.matrix
        self.textstate.matrix = (a, b, c, d, tx*a+ty*c+e, tx*b+ty*d+f)
        self.textstate.leading = ty
        self.textstate.linematrix = (0, 0)
        #print >>sys.stderr, 'TD(%r,%r): %r' % (tx, ty, self.textstate)
        return

    # textmatrix
    def do_Tm(self, a, b, c, d, e, f):
        self.textstate.matrix = (a, b, c, d, e, f)
        self.textstate.linematrix = (0, 0)
        return

    # nextline
    def do_T_a(self):
        (a, b, c, d, e, f) = self.textstate.matrix
        self.textstate.matrix = (a, b, c, d, self.textstate.leading*c+e, self.textstate.leading*d+f)
        self.textstate.linematrix = (0, 0)
        return

    # show-pos
    def do_TJ(self, seq):
        #print >>sys.stderr, 'TJ(%r): %r' % (seq, self.textstate)
        if self.textstate.font is None:
            if STRICT:
                raise PDFInterpreterError('No font specified!')
            return
        self.device.render_string(self.textstate, seq)
        return

    # show
    def do_Tj(self, s):
        self.do_TJ([s])
        return

    # quote
    def do__q(self, s):
        self.do_T_a()
        self.do_TJ([s])
        return

    # doublequote
    def do__w(self, aw, ac, s):
        self.do_Tw(aw)
        self.do_Tc(ac)
        self.do_TJ([s])
        return

    # inline image
    def do_BI(self):  # never called
        return

    def do_ID(self):  # never called
        return

    def do_EI(self, obj):
        if 'W' in obj and 'H' in obj:
            iobjid = str(id(obj))
            self.device.begin_figure(iobjid, (0, 0, 1, 1), MATRIX_IDENTITY)
            self.device.render_image(iobjid, obj)
            self.device.end_figure(iobjid)
        return

    # invoke an XObject
    def do_Do(self, xobjid):
        xobjid = literal_name(xobjid)
        try:
            xobj = stream_value(self.xobjmap[xobjid])
        except KeyError:
            if STRICT:
                raise PDFInterpreterError('Undefined xobject id: %r' % xobjid)
            return
        if 1 <= self.debug:
            print >>sys.stderr, 'Processing xobj: %r' % xobj
        subtype = xobj.get('Subtype')
        if subtype is LITERAL_FORM and 'BBox' in xobj:
            interpreter = self.dup()
            bbox = list_value(xobj['BBox'])
            matrix = list_value(xobj.get('Matrix', MATRIX_IDENTITY))
            # According to PDF reference 1.7 section 4.9.1, XObjects in
            # earlier PDFs (prior to v1.2) use the page's Resources entry
            # instead of having their own Resources entry.
            resources = dict_value(xobj.get('Resources')) or self.resources.copy()
            self.device.begin_figure(xobjid, bbox, matrix)
            interpreter.render_contents(resources, [xobj], ctm=mult_matrix(matrix, self.ctm))
            self.device.end_figure(xobjid)
        elif subtype is LITERAL_IMAGE and 'Width' in xobj and 'Height' in xobj:
            self.device.begin_figure(xobjid, (0, 0, 1, 1), MATRIX_IDENTITY)
            self.device.render_image(xobjid, xobj)
            self.device.end_figure(xobjid)
        else:
            # unsupported xobject type.
            pass
        return

    def process_page(self, page):
        if 1 <= self.debug:
            print >>sys.stderr, 'Processing page: %r' % page
        (x0, y0, x1, y1) = page.mediabox
        if page.rotate == 90:
            ctm = (0, -1, 1, 0, -y0, x1)
        elif page.rotate == 180:
            ctm = (-1, 0, 0, -1, x1, y1)
        elif page.rotate == 270:
            ctm = (0, 1, -1, 0, y1, -x0)
        else:
            ctm = (1, 0, 0, 1, -x0, -y0)
        self.device.begin_page(page, ctm)
        self.render_contents(page.resources, page.contents, ctm=ctm)
        self.device.end_page(page)
        return

    # render_contents(resources, streams, ctm)
    #   Render the content streams.
    #   This method may be called recursively.
    def render_contents(self, resources, streams, ctm=MATRIX_IDENTITY):
        if 1 <= self.debug:
            print >>sys.stderr, ('render_contents: resources=%r, streams=%r, ctm=%r' %
                                 (resources, streams, ctm))
        self.init_resources(resources)
        self.init_state(ctm)
        self.execute(list_value(streams))
        return

    def execute(self, streams):
        try:
            parser = PDFContentParser(streams)
        except PSEOF:
            # empty page
            return
        while 1:
            try:
                (_, obj) = parser.nextobject()
            except PSEOF:
                break
            if isinstance(obj, PSKeyword):
                name = keyword_name(obj)
                method = 'do_%s' % name.replace('*', '_a').replace('"', '_w').replace("'", '_q')
                if hasattr(self, method):
                    func = getattr(self, method)
                    nargs = func.func_code.co_argcount-1
                    if nargs:
                        args = self.pop(nargs)
                        if 2 <= self.debug:
                            print >>sys.stderr, 'exec: %s %r' % (name, args)
                        if len(args) == nargs:
                            func(*args)
                    else:
                        if 2 <= self.debug:
                            print >>sys.stderr, 'exec: %s' % (name)
                        func()
                else:
                    if STRICT:
                        raise PDFInterpreterError('Unknown operator: %r' % name)
            else:
                self.push(obj)
        return

########NEW FILE########
__FILENAME__ = pdfpage
#!/usr/bin/env python
import sys
from psparser import LIT
from pdftypes import PDFObjectNotFound
from pdftypes import resolve1
from pdftypes import int_value, list_value, dict_value
from pdfparser import PDFParser
from pdfdocument import PDFDocument
from pdfdocument import PDFEncryptionError
from pdfdocument import PDFTextExtractionNotAllowed

# some predefined literals and keywords.
LITERAL_PAGE = LIT('Page')
LITERAL_PAGES = LIT('Pages')


##  PDFPage
##
class PDFPage(object):

    """An object that holds the information about a page.

    A PDFPage object is merely a convenience class that has a set
    of keys and values, which describe the properties of a page
    and point to its contents.

    Attributes:
      doc: a PDFDocument object.
      pageid: any Python object that can uniquely identify the page.
      attrs: a dictionary of page attributes.
      contents: a list of PDFStream objects that represents the page content.
      lastmod: the last modified time of the page.
      resources: a list of resources used by the page.
      mediabox: the physical size of the page.
      cropbox: the crop rectangle of the page.
      rotate: the page rotation (in degree).
      annots: the page annotations.
      beads: a chain that represents natural reading order.
    """

    def __init__(self, doc, pageid, attrs):
        """Initialize a page object.

        doc: a PDFDocument object.
        pageid: any Python object that can uniquely identify the page.
        attrs: a dictionary of page attributes.
        """
        self.doc = doc
        self.pageid = pageid
        self.attrs = dict_value(attrs)
        self.lastmod = resolve1(self.attrs.get('LastModified'))
        self.resources = resolve1(self.attrs['Resources'])
        self.mediabox = resolve1(self.attrs['MediaBox'])
        if 'CropBox' in self.attrs:
            self.cropbox = resolve1(self.attrs['CropBox'])
        else:
            self.cropbox = self.mediabox
        self.rotate = (int_value(self.attrs.get('Rotate', 0))+360) % 360
        self.annots = self.attrs.get('Annots')
        self.beads = self.attrs.get('B')
        if 'Contents' in self.attrs:
            contents = resolve1(self.attrs['Contents'])
        else:
            contents = []
        if not isinstance(contents, list):
            contents = [contents]
        self.contents = contents
        return

    def __repr__(self):
        return '<PDFPage: Resources=%r, MediaBox=%r>' % (self.resources, self.mediabox)

    INHERITABLE_ATTRS = set(['Resources', 'MediaBox', 'CropBox', 'Rotate'])

    @classmethod
    def create_pages(klass, document, debug=0):
        def search(obj, parent):
            if isinstance(obj, int):
                objid = obj
                tree = dict_value(document.getobj(objid)).copy()
            else:
                objid = obj.objid
                tree = dict_value(obj).copy()
            for (k, v) in parent.iteritems():
                if k in klass.INHERITABLE_ATTRS and k not in tree:
                    tree[k] = v
            if tree.get('Type') is LITERAL_PAGES and 'Kids' in tree:
                if 1 <= debug:
                    print >>sys.stderr, 'Pages: Kids=%r' % tree['Kids']
                for c in list_value(tree['Kids']):
                    for x in search(c, tree):
                        yield x
            elif tree.get('Type') is LITERAL_PAGE:
                if 1 <= debug:
                    print >>sys.stderr, 'Page: %r' % tree
                yield (objid, tree)
        pages = False
        if 'Pages' in document.catalog:
            for (objid, tree) in search(document.catalog['Pages'], document.catalog):
                yield klass(document, objid, tree)
                pages = True
        if not pages:
            # fallback when /Pages is missing.
            for xref in document.xrefs:
                for objid in xref.get_objids():
                    try:
                        obj = document.getobj(objid)
                        if isinstance(obj, dict) and obj.get('Type') is LITERAL_PAGE:
                            yield klass(document, objid, obj)
                    except PDFObjectNotFound:
                        pass
        return

    @classmethod
    def get_pages(klass, fp,
                  pagenos=None, maxpages=0, password='',
                  caching=True, check_extractable=True):
        # Create a PDF parser object associated with the file object.
        parser = PDFParser(fp)
        # Create a PDF document object that stores the document structure.
        doc = PDFDocument(parser, password=password, caching=caching)
        # Check if the document allows text extraction. If not, abort.
        if check_extractable and not doc.is_extractable:
            raise PDFTextExtractionNotAllowed('Text extraction is not allowed: %r' % fp)
        # Process each page contained in the document.
        for (pageno, page) in enumerate(klass.create_pages(doc)):
            if pagenos and (pageno not in pagenos):
                continue
            yield page
            if maxpages and maxpages <= pageno+1:
                break
        return

########NEW FILE########
__FILENAME__ = pdfparser
#!/usr/bin/env python
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from psparser import PSStackParser
from psparser import PSSyntaxError, PSEOF
from psparser import KWD, STRICT
from pdftypes import PDFException
from pdftypes import PDFStream, PDFObjRef
from pdftypes import int_value
from pdftypes import dict_value


##  Exceptions
##
class PDFSyntaxError(PDFException):
    pass


##  PDFParser
##
class PDFParser(PSStackParser):

    """
    PDFParser fetch PDF objects from a file stream.
    It can handle indirect references by referring to
    a PDF document set by set_document method.
    It also reads XRefs at the end of every PDF file.

    Typical usage:
      parser = PDFParser(fp)
      parser.read_xref()
      parser.read_xref(fallback=True) # optional
      parser.set_document(doc)
      parser.seek(offset)
      parser.nextobject()

    """

    def __init__(self, fp):
        PSStackParser.__init__(self, fp)
        self.doc = None
        self.fallback = False
        return

    def set_document(self, doc):
        """Associates the parser with a PDFDocument object."""
        self.doc = doc
        return

    KEYWORD_R = KWD('R')
    KEYWORD_NULL = KWD('null')
    KEYWORD_ENDOBJ = KWD('endobj')
    KEYWORD_STREAM = KWD('stream')
    KEYWORD_XREF = KWD('xref')
    KEYWORD_STARTXREF = KWD('startxref')

    def do_keyword(self, pos, token):
        """Handles PDF-related keywords."""

        if token in (self.KEYWORD_XREF, self.KEYWORD_STARTXREF):
            self.add_results(*self.pop(1))

        elif token is self.KEYWORD_ENDOBJ:
            self.add_results(*self.pop(4))

        elif token is self.KEYWORD_NULL:
            # null object
            self.push((pos, None))

        elif token is self.KEYWORD_R:
            # reference to indirect object
            try:
                ((_, objid), (_, genno)) = self.pop(2)
                (objid, genno) = (int(objid), int(genno))
                obj = PDFObjRef(self.doc, objid, genno)
                self.push((pos, obj))
            except PSSyntaxError:
                pass

        elif token is self.KEYWORD_STREAM:
            # stream object
            ((_, dic),) = self.pop(1)
            dic = dict_value(dic)
            objlen = 0
            if not self.fallback:
                try:
                    objlen = int_value(dic['Length'])
                except KeyError:
                    if STRICT:
                        raise PDFSyntaxError('/Length is undefined: %r' % dic)
            self.seek(pos)
            try:
                (_, line) = self.nextline()  # 'stream'
            except PSEOF:
                if STRICT:
                    raise PDFSyntaxError('Unexpected EOF')
                return
            pos += len(line)
            self.fp.seek(pos)
            data = self.fp.read(objlen)
            self.seek(pos+objlen)
            while 1:
                try:
                    (linepos, line) = self.nextline()
                except PSEOF:
                    if STRICT:
                        raise PDFSyntaxError('Unexpected EOF')
                    break
                if 'endstream' in line:
                    i = line.index('endstream')
                    objlen += i
                    if self.fallback:
                        data += line[:i]
                    break
                objlen += len(line)
                if self.fallback:
                    data += line
            self.seek(pos+objlen)
            # XXX limit objlen not to exceed object boundary
            if 2 <= self.debug:
                print >>sys.stderr, 'Stream: pos=%d, objlen=%d, dic=%r, data=%r...' % \
                                    (pos, objlen, dic, data[:10])
            obj = PDFStream(dic, data, self.doc.decipher)
            self.push((pos, obj))

        else:
            # others
            self.push((pos, token))

        return


##  PDFStreamParser
##
class PDFStreamParser(PDFParser):

    """
    PDFStreamParser is used to parse PDF content streams
    that is contained in each page and has instructions
    for rendering the page. A reference to a PDF document is
    needed because a PDF content stream can also have
    indirect references to other objects in the same document.
    """

    def __init__(self, data):
        PDFParser.__init__(self, StringIO(data))
        return

    def flush(self):
        self.add_results(*self.popall())
        return

    KEYWORD_OBJ = KWD('obj')
    def do_keyword(self, pos, token):
        if token is self.KEYWORD_R:
            # reference to indirect object
            try:
                ((_, objid), (_, genno)) = self.pop(2)
                (objid, genno) = (int(objid), int(genno))
                obj = PDFObjRef(self.doc, objid, genno)
                self.push((pos, obj))
            except PSSyntaxError:
                pass
            return
        elif token in (self.KEYWORD_OBJ, self.KEYWORD_ENDOBJ):
            if STRICT:
                # See PDF Spec 3.4.6: Only the object values are stored in the
                # stream; the obj and endobj keywords are not used.
                raise PDFSyntaxError("Keyword endobj found in stream")
            return
        # others
        self.push((pos, token))
        return

########NEW FILE########
__FILENAME__ = pdftypes
#!/usr/bin/env python
import zlib
from lzw import lzwdecode
from ascii85 import ascii85decode, asciihexdecode
from runlength import rldecode
from ccitt import ccittfaxdecode
from psparser import PSException, PSObject
from psparser import LIT, STRICT
from utils import apply_png_predictor, isnumber

LITERAL_CRYPT = LIT('Crypt')

# Abbreviation of Filter names in PDF 4.8.6. "Inline Images"
LITERALS_FLATE_DECODE = (LIT('FlateDecode'), LIT('Fl'))
LITERALS_LZW_DECODE = (LIT('LZWDecode'), LIT('LZW'))
LITERALS_ASCII85_DECODE = (LIT('ASCII85Decode'), LIT('A85'))
LITERALS_ASCIIHEX_DECODE = (LIT('ASCIIHexDecode'), LIT('AHx'))
LITERALS_RUNLENGTH_DECODE = (LIT('RunLengthDecode'), LIT('RL'))
LITERALS_CCITTFAX_DECODE = (LIT('CCITTFaxDecode'), LIT('CCF'))
LITERALS_DCT_DECODE = (LIT('DCTDecode'), LIT('DCT'))


##  PDF Objects
##
class PDFObject(PSObject):
    pass

class PDFException(PSException):
    pass

class PDFTypeError(PDFException):
    pass

class PDFValueError(PDFException):
    pass

class PDFObjectNotFound(PDFException):
    pass

class PDFNotImplementedError(PDFException):
    pass


##  PDFObjRef
##
class PDFObjRef(PDFObject):

    def __init__(self, doc, objid, _):
        if objid == 0:
            if STRICT:
                raise PDFValueError('PDF object id cannot be 0.')
        self.doc = doc
        self.objid = objid
        #self.genno = genno  # Never used.
        return

    def __repr__(self):
        return '<PDFObjRef:%d>' % (self.objid)

    def resolve(self, default=None):
        try:
            return self.doc.getobj(self.objid)
        except PDFObjectNotFound:
            return default


# resolve
def resolve1(x, default=None):
    """Resolves an object.

    If this is an array or dictionary, it may still contains
    some indirect objects inside.
    """
    while isinstance(x, PDFObjRef):
        x = x.resolve(default=default)
    return x


def resolve_all(x, default=None):
    """Recursively resolves the given object and all the internals.

    Make sure there is no indirect reference within the nested object.
    This procedure might be slow.
    """
    while isinstance(x, PDFObjRef):
        x = x.resolve(default=default)
    if isinstance(x, list):
        x = [resolve_all(v, default=default) for v in x]
    elif isinstance(x, dict):
        for (k, v) in x.iteritems():
            x[k] = resolve_all(v, default=default)
    return x


def decipher_all(decipher, objid, genno, x):
    """Recursively deciphers the given object.
    """
    if isinstance(x, str):
        return decipher(objid, genno, x)
    if isinstance(x, list):
        x = [decipher_all(decipher, objid, genno, v) for v in x]
    elif isinstance(x, dict):
        for (k, v) in x.iteritems():
            x[k] = decipher_all(decipher, objid, genno, v)
    return x


# Type cheking
def int_value(x):
    x = resolve1(x)
    if not isinstance(x, int):
        if STRICT:
            raise PDFTypeError('Integer required: %r' % x)
        return 0
    return x


def float_value(x):
    x = resolve1(x)
    if not isinstance(x, float):
        if STRICT:
            raise PDFTypeError('Float required: %r' % x)
        return 0.0
    return x


def num_value(x):
    x = resolve1(x)
    if not isnumber(x):
        if STRICT:
            raise PDFTypeError('Int or Float required: %r' % x)
        return 0
    return x


def str_value(x):
    x = resolve1(x)
    if not isinstance(x, str):
        if STRICT:
            raise PDFTypeError('String required: %r' % x)
        return ''
    return x


def list_value(x):
    x = resolve1(x)
    if not isinstance(x, (list, tuple)):
        if STRICT:
            raise PDFTypeError('List required: %r' % x)
        return []
    return x


def dict_value(x):
    x = resolve1(x)
    if not isinstance(x, dict):
        if STRICT:
            raise PDFTypeError('Dict required: %r' % x)
        return {}
    return x


def stream_value(x):
    x = resolve1(x)
    if not isinstance(x, PDFStream):
        if STRICT:
            raise PDFTypeError('PDFStream required: %r' % x)
        return PDFStream({}, '')
    return x


##  PDFStream type
##
class PDFStream(PDFObject):

    def __init__(self, attrs, rawdata, decipher=None):
        assert isinstance(attrs, dict)
        self.attrs = attrs
        self.rawdata = rawdata
        self.decipher = decipher
        self.data = None
        self.objid = None
        self.genno = None
        return

    def set_objid(self, objid, genno):
        self.objid = objid
        self.genno = genno
        return

    def __repr__(self):
        if self.data is None:
            assert self.rawdata is not None
            return '<PDFStream(%r): raw=%d, %r>' % (self.objid, len(self.rawdata), self.attrs)
        else:
            assert self.data is not None
            return '<PDFStream(%r): len=%d, %r>' % (self.objid, len(self.data), self.attrs)

    def __contains__(self, name):
        return name in self.attrs

    def __getitem__(self, name):
        return self.attrs[name]

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    def get_any(self, names, default=None):
        for name in names:
            if name in self.attrs:
                return self.attrs[name]
        return default

    def get_filters(self):
        filters = self.get_any(('F', 'Filter'))
        if not filters:
            return []
        if isinstance(filters, list):
            return filters
        return [filters]

    def decode(self):
        assert self.data is None and self.rawdata is not None
        data = self.rawdata
        if self.decipher:
            # Handle encryption
            data = self.decipher(self.objid, self.genno, data, self.attrs)
        filters = self.get_filters()
        if not filters:
            self.data = data
            self.rawdata = None
            return
        for f in filters:
            params = self.get_any(('DP', 'DecodeParms', 'FDecodeParms'), {})
            if f in LITERALS_FLATE_DECODE:
                # will get errors if the document is encrypted.
                try:
                    data = zlib.decompress(data)
                except zlib.error, e:
                    if STRICT:
                        raise PDFException('Invalid zlib bytes: %r, %r' % (e, data))
                    data = ''
            elif f in LITERALS_LZW_DECODE:
                data = lzwdecode(data)
            elif f in LITERALS_ASCII85_DECODE:
                data = ascii85decode(data)
            elif f in LITERALS_ASCIIHEX_DECODE:
                data = asciihexdecode(data)
            elif f in LITERALS_RUNLENGTH_DECODE:
                data = rldecode(data)
            elif f in LITERALS_CCITTFAX_DECODE:
                data = ccittfaxdecode(data, params)
            elif f in LITERALS_DCT_DECODE:
                # This is probably a JPG stream - it does not need to be decoded twice.
                # Just return the stream to the user.
                pass
            elif f == LITERAL_CRYPT:
                # not yet..
                raise PDFNotImplementedError('/Crypt filter is unsupported')
            else:
                raise PDFNotImplementedError('Unsupported filter: %r' % f)
            # apply predictors
            if 'Predictor' in params:
                pred = int_value(params['Predictor'])
                if pred == 1:
                    # no predictor
                    pass
                elif 10 <= pred:
                    # PNG predictor
                    colors = int_value(params.get('Colors', 1))
                    columns = int_value(params.get('Columns', 1))
                    bitspercomponent = int_value(params.get('BitsPerComponent', 8))
                    data = apply_png_predictor(pred, colors, columns, bitspercomponent, data)
                else:
                    raise PDFNotImplementedError('Unsupported predictor: %r' % pred)
        self.data = data
        self.rawdata = None
        return

    def get_data(self):
        if self.data is None:
            self.decode()
        return self.data

    def get_rawdata(self):
        return self.rawdata

########NEW FILE########
__FILENAME__ = psparser
#!/usr/bin/env python
import sys
import re
from utils import choplist

STRICT = 0


##  PS Exceptions
##
class PSException(Exception):
    pass


class PSEOF(PSException):
    pass


class PSSyntaxError(PSException):
    pass


class PSTypeError(PSException):
    pass


class PSValueError(PSException):
    pass


##  Basic PostScript Types
##

##  PSObject
##
class PSObject(object):

    """Base class for all PS or PDF-related data types."""

    pass


##  PSLiteral
##
class PSLiteral(PSObject):

    """A class that represents a PostScript literal.

    Postscript literals are used as identifiers, such as
    variable names, property names and dictionary keys.
    Literals are case sensitive and denoted by a preceding
    slash sign (e.g. "/Name")

    Note: Do not create an instance of PSLiteral directly.
    Always use PSLiteralTable.intern().
    """

    def __init__(self, name):
        self.name = name
        return

    def __repr__(self):
        return '/%s' % self.name


##  PSKeyword
##
class PSKeyword(PSObject):

    """A class that represents a PostScript keyword.

    PostScript keywords are a dozen of predefined words.
    Commands and directives in PostScript are expressed by keywords.
    They are also used to denote the content boundaries.

    Note: Do not create an instance of PSKeyword directly.
    Always use PSKeywordTable.intern().
    """

    def __init__(self, name):
        self.name = name
        return

    def __repr__(self):
        return self.name


##  PSSymbolTable
##
class PSSymbolTable(object):

    """A utility class for storing PSLiteral/PSKeyword objects.

    Interned objects can be checked its identity with "is" operator.
    """

    def __init__(self, klass):
        self.dict = {}
        self.klass = klass
        return

    def intern(self, name):
        if name in self.dict:
            lit = self.dict[name]
        else:
            lit = self.klass(name)
            self.dict[name] = lit
        return lit

PSLiteralTable = PSSymbolTable(PSLiteral)
PSKeywordTable = PSSymbolTable(PSKeyword)
LIT = PSLiteralTable.intern
KWD = PSKeywordTable.intern
KEYWORD_PROC_BEGIN = KWD('{')
KEYWORD_PROC_END = KWD('}')
KEYWORD_ARRAY_BEGIN = KWD('[')
KEYWORD_ARRAY_END = KWD(']')
KEYWORD_DICT_BEGIN = KWD('<<')
KEYWORD_DICT_END = KWD('>>')


def literal_name(x):
    if not isinstance(x, PSLiteral):
        if STRICT:
            raise PSTypeError('Literal required: %r' % x)
        else:
            return str(x)
    return x.name


def keyword_name(x):
    if not isinstance(x, PSKeyword):
        if STRICT:
            raise PSTypeError('Keyword required: %r' % x)
        else:
            return str(x)
    return x.name


##  PSBaseParser
##
EOL = re.compile(r'[\r\n]')
SPC = re.compile(r'\s')
NONSPC = re.compile(r'\S')
HEX = re.compile(r'[0-9a-fA-F]')
END_LITERAL = re.compile(r'[#/%\[\]()<>{}\s]')
END_HEX_STRING = re.compile(r'[^\s0-9a-fA-F]')
HEX_PAIR = re.compile(r'[0-9a-fA-F]{2}|.')
END_NUMBER = re.compile(r'[^0-9]')
END_KEYWORD = re.compile(r'[#/%\[\]()<>{}\s]')
END_STRING = re.compile(r'[()\134]')
OCT_STRING = re.compile(r'[0-7]')
ESC_STRING = {'b': 8, 't': 9, 'n': 10, 'f': 12, 'r': 13, '(': 40, ')': 41, '\\': 92}


class PSBaseParser(object):

    """Most basic PostScript parser that performs only tokenization.
    """
    BUFSIZ = 4096

    debug = 0

    def __init__(self, fp):
        self.fp = fp
        self.seek(0)
        return

    def __repr__(self):
        return '<%s: %r, bufpos=%d>' % (self.__class__.__name__, self.fp, self.bufpos)

    def flush(self):
        return

    def close(self):
        self.flush()
        return

    def tell(self):
        return self.bufpos+self.charpos

    def poll(self, pos=None, n=80):
        pos0 = self.fp.tell()
        if not pos:
            pos = self.bufpos+self.charpos
        self.fp.seek(pos)
        print >>sys.stderr, 'poll(%d): %r' % (pos, self.fp.read(n))
        self.fp.seek(pos0)
        return

    def seek(self, pos):
        """Seeks the parser to the given position.
        """
        if 2 <= self.debug:
            print >>sys.stderr, 'seek: %r' % pos
        self.fp.seek(pos)
        # reset the status for nextline()
        self.bufpos = pos
        self.buf = ''
        self.charpos = 0
        # reset the status for nexttoken()
        self._parse1 = self._parse_main
        self._curtoken = ''
        self._curtokenpos = 0
        self._tokens = []
        return

    def fillbuf(self):
        if self.charpos < len(self.buf):
            return
        # fetch next chunk.
        self.bufpos = self.fp.tell()
        self.buf = self.fp.read(self.BUFSIZ)
        if not self.buf:
            raise PSEOF('Unexpected EOF')
        self.charpos = 0
        return

    def nextline(self):
        """Fetches a next line that ends either with \\r or \\n.
        """
        linebuf = ''
        linepos = self.bufpos + self.charpos
        eol = False
        while 1:
            self.fillbuf()
            if eol:
                c = self.buf[self.charpos]
                # handle '\r\n'
                if c == '\n':
                    linebuf += c
                    self.charpos += 1
                break
            m = EOL.search(self.buf, self.charpos)
            if m:
                linebuf += self.buf[self.charpos:m.end(0)]
                self.charpos = m.end(0)
                if linebuf[-1] == '\r':
                    eol = True
                else:
                    break
            else:
                linebuf += self.buf[self.charpos:]
                self.charpos = len(self.buf)
        if 2 <= self.debug:
            print >>sys.stderr, 'nextline: %r' % ((linepos, linebuf),)
        return (linepos, linebuf)

    def revreadlines(self):
        """Fetches a next line backword.

        This is used to locate the trailers at the end of a file.
        """
        self.fp.seek(0, 2)
        pos = self.fp.tell()
        buf = ''
        while 0 < pos:
            prevpos = pos
            pos = max(0, pos-self.BUFSIZ)
            self.fp.seek(pos)
            s = self.fp.read(prevpos-pos)
            if not s:
                break
            while 1:
                n = max(s.rfind('\r'), s.rfind('\n'))
                if n == -1:
                    buf = s + buf
                    break
                yield s[n:]+buf
                s = s[:n]
                buf = ''
        return

    def _parse_main(self, s, i):
        m = NONSPC.search(s, i)
        if not m:
            return len(s)
        j = m.start(0)
        c = s[j]
        self._curtokenpos = self.bufpos+j
        if c == '%':
            self._curtoken = '%'
            self._parse1 = self._parse_comment
            return j+1
        elif c == '/':
            self._curtoken = ''
            self._parse1 = self._parse_literal
            return j+1
        elif c in '-+' or c.isdigit():
            self._curtoken = c
            self._parse1 = self._parse_number
            return j+1
        elif c == '.':
            self._curtoken = c
            self._parse1 = self._parse_float
            return j+1
        elif c.isalpha():
            self._curtoken = c
            self._parse1 = self._parse_keyword
            return j+1
        elif c == '(':
            self._curtoken = ''
            self.paren = 1
            self._parse1 = self._parse_string
            return j+1
        elif c == '<':
            self._curtoken = ''
            self._parse1 = self._parse_wopen
            return j+1
        elif c == '>':
            self._curtoken = ''
            self._parse1 = self._parse_wclose
            return j+1
        else:
            self._add_token(KWD(c))
            return j+1

    def _add_token(self, obj):
        self._tokens.append((self._curtokenpos, obj))
        return

    def _parse_comment(self, s, i):
        m = EOL.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return (self._parse_comment, len(s))
        j = m.start(0)
        self._curtoken += s[i:j]
        self._parse1 = self._parse_main
        # We ignore comments.
        #self._tokens.append(self._curtoken)
        return j

    def _parse_literal(self, s, i):
        m = END_LITERAL.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return len(s)
        j = m.start(0)
        self._curtoken += s[i:j]
        c = s[j]
        if c == '#':
            self.hex = ''
            self._parse1 = self._parse_literal_hex
            return j+1
        self._add_token(LIT(self._curtoken))
        self._parse1 = self._parse_main
        return j

    def _parse_literal_hex(self, s, i):
        c = s[i]
        if HEX.match(c) and len(self.hex) < 2:
            self.hex += c
            return i+1
        if self.hex:
            self._curtoken += chr(int(self.hex, 16))
        self._parse1 = self._parse_literal
        return i

    def _parse_number(self, s, i):
        m = END_NUMBER.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return len(s)
        j = m.start(0)
        self._curtoken += s[i:j]
        c = s[j]
        if c == '.':
            self._curtoken += c
            self._parse1 = self._parse_float
            return j+1
        try:
            self._add_token(int(self._curtoken))
        except ValueError:
            pass
        self._parse1 = self._parse_main
        return j

    def _parse_float(self, s, i):
        m = END_NUMBER.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return len(s)
        j = m.start(0)
        self._curtoken += s[i:j]
        try:
            self._add_token(float(self._curtoken))
        except ValueError:
            pass
        self._parse1 = self._parse_main
        return j

    def _parse_keyword(self, s, i):
        m = END_KEYWORD.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return len(s)
        j = m.start(0)
        self._curtoken += s[i:j]
        if self._curtoken == 'true':
            token = True
        elif self._curtoken == 'false':
            token = False
        else:
            token = KWD(self._curtoken)
        self._add_token(token)
        self._parse1 = self._parse_main
        return j

    def _parse_string(self, s, i):
        m = END_STRING.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return len(s)
        j = m.start(0)
        self._curtoken += s[i:j]
        c = s[j]
        if c == '\\':
            self.oct = ''
            self._parse1 = self._parse_string_1
            return j+1
        if c == '(':
            self.paren += 1
            self._curtoken += c
            return j+1
        if c == ')':
            self.paren -= 1
            if self.paren:  # WTF, they said balanced parens need no special treatment.
                self._curtoken += c
                return j+1
        self._add_token(self._curtoken)
        self._parse1 = self._parse_main
        return j+1

    def _parse_string_1(self, s, i):
        c = s[i]
        if OCT_STRING.match(c) and len(self.oct) < 3:
            self.oct += c
            return i+1
        if self.oct:
            self._curtoken += chr(int(self.oct, 8))
            self._parse1 = self._parse_string
            return i
        if c in ESC_STRING:
            self._curtoken += chr(ESC_STRING[c])
        self._parse1 = self._parse_string
        return i+1

    def _parse_wopen(self, s, i):
        c = s[i]
        if c == '<':
            self._add_token(KEYWORD_DICT_BEGIN)
            self._parse1 = self._parse_main
            i += 1
        else:
            self._parse1 = self._parse_hexstring
        return i

    def _parse_wclose(self, s, i):
        c = s[i]
        if c == '>':
            self._add_token(KEYWORD_DICT_END)
            i += 1
        self._parse1 = self._parse_main
        return i

    def _parse_hexstring(self, s, i):
        m = END_HEX_STRING.search(s, i)
        if not m:
            self._curtoken += s[i:]
            return len(s)
        j = m.start(0)
        self._curtoken += s[i:j]
        token = HEX_PAIR.sub(lambda m: chr(int(m.group(0), 16)),
                             SPC.sub('', self._curtoken))
        self._add_token(token)
        self._parse1 = self._parse_main
        return j

    def nexttoken(self):
        while not self._tokens:
            self.fillbuf()
            self.charpos = self._parse1(self.buf, self.charpos)
        token = self._tokens.pop(0)
        if 2 <= self.debug:
            print >>sys.stderr, 'nexttoken: %r' % (token,)
        return token


##  PSStackParser
##
class PSStackParser(PSBaseParser):

    def __init__(self, fp):
        PSBaseParser.__init__(self, fp)
        self.reset()
        return

    def reset(self):
        self.context = []
        self.curtype = None
        self.curstack = []
        self.results = []
        return

    def seek(self, pos):
        PSBaseParser.seek(self, pos)
        self.reset()
        return

    def push(self, *objs):
        self.curstack.extend(objs)
        return

    def pop(self, n):
        objs = self.curstack[-n:]
        self.curstack[-n:] = []
        return objs

    def popall(self):
        objs = self.curstack
        self.curstack = []
        return objs

    def add_results(self, *objs):
        if 2 <= self.debug:
            print >>sys.stderr, 'add_results: %r' % (objs,)
        self.results.extend(objs)
        return

    def start_type(self, pos, type):
        self.context.append((pos, self.curtype, self.curstack))
        (self.curtype, self.curstack) = (type, [])
        if 2 <= self.debug:
            print >>sys.stderr, 'start_type: pos=%r, type=%r' % (pos, type)
        return

    def end_type(self, type):
        if self.curtype != type:
            raise PSTypeError('Type mismatch: %r != %r' % (self.curtype, type))
        objs = [obj for (_, obj) in self.curstack]
        (pos, self.curtype, self.curstack) = self.context.pop()
        if 2 <= self.debug:
            print >>sys.stderr, 'end_type: pos=%r, type=%r, objs=%r' % (pos, type, objs)
        return (pos, objs)

    def do_keyword(self, pos, token):
        return

    def nextobject(self):
        """Yields a list of objects.

        Returns keywords, literals, strings, numbers, arrays and dictionaries.
        Arrays and dictionaries are represented as Python lists and dictionaries.
        """
        while not self.results:
            (pos, token) = self.nexttoken()
            #print (pos,token), (self.curtype, self.curstack)
            if isinstance(token, (int, long, float, bool, str, PSLiteral)):
                # normal token
                self.push((pos, token))
            elif token == KEYWORD_ARRAY_BEGIN:
                # begin array
                self.start_type(pos, 'a')
            elif token == KEYWORD_ARRAY_END:
                # end array
                try:
                    self.push(self.end_type('a'))
                except PSTypeError:
                    if STRICT:
                        raise
            elif token == KEYWORD_DICT_BEGIN:
                # begin dictionary
                self.start_type(pos, 'd')
            elif token == KEYWORD_DICT_END:
                # end dictionary
                try:
                    (pos, objs) = self.end_type('d')
                    if len(objs) % 2 != 0:
                        raise PSSyntaxError('Invalid dictionary construct: %r' % objs)
                    # construct a Python dictionary.
                    d = dict((literal_name(k), v) for (k, v) in choplist(2, objs) if v is not None)
                    self.push((pos, d))
                except PSTypeError:
                    if STRICT:
                        raise
            elif token == KEYWORD_PROC_BEGIN:
                # begin proc
                self.start_type(pos, 'p')
            elif token == KEYWORD_PROC_END:
                # end proc
                try:
                    self.push(self.end_type('p'))
                except PSTypeError:
                    if STRICT:
                        raise
            else:
                if 2 <= self.debug:
                    print >>sys.stderr, 'do_keyword: pos=%r, token=%r, stack=%r' % \
                          (pos, token, self.curstack)
                self.do_keyword(pos, token)
            if self.context:
                continue
            else:
                self.flush()
        obj = self.results.pop(0)
        if 2 <= self.debug:
            print >>sys.stderr, 'nextobject: %r' % (obj,)
        return obj


import unittest


##  Simplistic Test cases
##
class TestPSBaseParser(unittest.TestCase):

    TESTDATA = r'''%!PS
begin end
 "  @ #
/a/BCD /Some_Name /foo#5f#xbaa
0 +1 -2 .5 1.234
(abc) () (abc ( def ) ghi)
(def\040\0\0404ghi) (bach\\slask) (foo\nbaa)
(this % is not a comment.)
(foo
baa)
(foo\
baa)
<> <20> < 40 4020 >
<abcd00
12345>
func/a/b{(c)do*}def
[ 1 (z) ! ]
<< /foo (bar) >>
'''

    TOKENS = [
      (5, KWD('begin')), (11, KWD('end')), (16, KWD('"')), (19, KWD('@')),
      (21, KWD('#')), (23, LIT('a')), (25, LIT('BCD')), (30, LIT('Some_Name')),
      (41, LIT('foo_xbaa')), (54, 0), (56, 1), (59, -2), (62, 0.5),
      (65, 1.234), (71, 'abc'), (77, ''), (80, 'abc ( def ) ghi'),
      (98, 'def \x00 4ghi'), (118, 'bach\\slask'), (132, 'foo\nbaa'),
      (143, 'this % is not a comment.'), (170, 'foo\nbaa'), (180, 'foobaa'),
      (191, ''), (194, ' '), (199, '@@ '), (211, '\xab\xcd\x00\x124\x05'),
      (226, KWD('func')), (230, LIT('a')), (232, LIT('b')),
      (234, KWD('{')), (235, 'c'), (238, KWD('do*')), (241, KWD('}')),
      (242, KWD('def')), (246, KWD('[')), (248, 1), (250, 'z'), (254, KWD('!')),
      (256, KWD(']')), (258, KWD('<<')), (261, LIT('foo')), (266, 'bar'),
      (272, KWD('>>'))
    ]

    OBJS = [
      (23, LIT('a')), (25, LIT('BCD')), (30, LIT('Some_Name')),
      (41, LIT('foo_xbaa')), (54, 0), (56, 1), (59, -2), (62, 0.5),
      (65, 1.234), (71, 'abc'), (77, ''), (80, 'abc ( def ) ghi'),
      (98, 'def \x00 4ghi'), (118, 'bach\\slask'), (132, 'foo\nbaa'),
      (143, 'this % is not a comment.'), (170, 'foo\nbaa'), (180, 'foobaa'),
      (191, ''), (194, ' '), (199, '@@ '), (211, '\xab\xcd\x00\x124\x05'),
      (230, LIT('a')), (232, LIT('b')), (234, ['c']), (246, [1, 'z']),
      (258, {'foo': 'bar'}),
    ]

    def get_tokens(self, s):
        import StringIO

        class MyParser(PSBaseParser):
            def flush(self):
                self.add_results(*self.popall())
        parser = MyParser(StringIO.StringIO(s))
        r = []
        try:
            while 1:
                r.append(parser.nexttoken())
        except PSEOF:
            pass
        return r

    def get_objects(self, s):
        import StringIO

        class MyParser(PSStackParser):
            def flush(self):
                self.add_results(*self.popall())
        parser = MyParser(StringIO.StringIO(s))
        r = []
        try:
            while 1:
                r.append(parser.nextobject())
        except PSEOF:
            pass
        return r

    def test_1(self):
        tokens = self.get_tokens(self.TESTDATA)
        print tokens
        self.assertEqual(tokens, self.TOKENS)
        return

    def test_2(self):
        objs = self.get_objects(self.TESTDATA)
        print objs
        self.assertEqual(objs, self.OBJS)
        return

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = rijndael
#!/usr/bin/env python

""" Python implementation of Rijndael encryption algorithm.

This code is in the public domain.

This code is based on a public domain C implementation
by Philip J. Erdelsky:
  http://www.efgh.com/software/rijndael.htm

"""

import struct


def KEYLENGTH(keybits):
    return (keybits)//8


def RKLENGTH(keybits):
    return (keybits)//8+28


def NROUNDS(keybits):
    return (keybits)//32+6

Te0 = [
    0xc66363a5L, 0xf87c7c84L, 0xee777799L, 0xf67b7b8dL,
    0xfff2f20dL, 0xd66b6bbdL, 0xde6f6fb1L, 0x91c5c554L,
    0x60303050L, 0x02010103L, 0xce6767a9L, 0x562b2b7dL,
    0xe7fefe19L, 0xb5d7d762L, 0x4dababe6L, 0xec76769aL,
    0x8fcaca45L, 0x1f82829dL, 0x89c9c940L, 0xfa7d7d87L,
    0xeffafa15L, 0xb25959ebL, 0x8e4747c9L, 0xfbf0f00bL,
    0x41adadecL, 0xb3d4d467L, 0x5fa2a2fdL, 0x45afafeaL,
    0x239c9cbfL, 0x53a4a4f7L, 0xe4727296L, 0x9bc0c05bL,
    0x75b7b7c2L, 0xe1fdfd1cL, 0x3d9393aeL, 0x4c26266aL,
    0x6c36365aL, 0x7e3f3f41L, 0xf5f7f702L, 0x83cccc4fL,
    0x6834345cL, 0x51a5a5f4L, 0xd1e5e534L, 0xf9f1f108L,
    0xe2717193L, 0xabd8d873L, 0x62313153L, 0x2a15153fL,
    0x0804040cL, 0x95c7c752L, 0x46232365L, 0x9dc3c35eL,
    0x30181828L, 0x379696a1L, 0x0a05050fL, 0x2f9a9ab5L,
    0x0e070709L, 0x24121236L, 0x1b80809bL, 0xdfe2e23dL,
    0xcdebeb26L, 0x4e272769L, 0x7fb2b2cdL, 0xea75759fL,
    0x1209091bL, 0x1d83839eL, 0x582c2c74L, 0x341a1a2eL,
    0x361b1b2dL, 0xdc6e6eb2L, 0xb45a5aeeL, 0x5ba0a0fbL,
    0xa45252f6L, 0x763b3b4dL, 0xb7d6d661L, 0x7db3b3ceL,
    0x5229297bL, 0xdde3e33eL, 0x5e2f2f71L, 0x13848497L,
    0xa65353f5L, 0xb9d1d168L, 0x00000000L, 0xc1eded2cL,
    0x40202060L, 0xe3fcfc1fL, 0x79b1b1c8L, 0xb65b5bedL,
    0xd46a6abeL, 0x8dcbcb46L, 0x67bebed9L, 0x7239394bL,
    0x944a4adeL, 0x984c4cd4L, 0xb05858e8L, 0x85cfcf4aL,
    0xbbd0d06bL, 0xc5efef2aL, 0x4faaaae5L, 0xedfbfb16L,
    0x864343c5L, 0x9a4d4dd7L, 0x66333355L, 0x11858594L,
    0x8a4545cfL, 0xe9f9f910L, 0x04020206L, 0xfe7f7f81L,
    0xa05050f0L, 0x783c3c44L, 0x259f9fbaL, 0x4ba8a8e3L,
    0xa25151f3L, 0x5da3a3feL, 0x804040c0L, 0x058f8f8aL,
    0x3f9292adL, 0x219d9dbcL, 0x70383848L, 0xf1f5f504L,
    0x63bcbcdfL, 0x77b6b6c1L, 0xafdada75L, 0x42212163L,
    0x20101030L, 0xe5ffff1aL, 0xfdf3f30eL, 0xbfd2d26dL,
    0x81cdcd4cL, 0x180c0c14L, 0x26131335L, 0xc3ecec2fL,
    0xbe5f5fe1L, 0x359797a2L, 0x884444ccL, 0x2e171739L,
    0x93c4c457L, 0x55a7a7f2L, 0xfc7e7e82L, 0x7a3d3d47L,
    0xc86464acL, 0xba5d5de7L, 0x3219192bL, 0xe6737395L,
    0xc06060a0L, 0x19818198L, 0x9e4f4fd1L, 0xa3dcdc7fL,
    0x44222266L, 0x542a2a7eL, 0x3b9090abL, 0x0b888883L,
    0x8c4646caL, 0xc7eeee29L, 0x6bb8b8d3L, 0x2814143cL,
    0xa7dede79L, 0xbc5e5ee2L, 0x160b0b1dL, 0xaddbdb76L,
    0xdbe0e03bL, 0x64323256L, 0x743a3a4eL, 0x140a0a1eL,
    0x924949dbL, 0x0c06060aL, 0x4824246cL, 0xb85c5ce4L,
    0x9fc2c25dL, 0xbdd3d36eL, 0x43acacefL, 0xc46262a6L,
    0x399191a8L, 0x319595a4L, 0xd3e4e437L, 0xf279798bL,
    0xd5e7e732L, 0x8bc8c843L, 0x6e373759L, 0xda6d6db7L,
    0x018d8d8cL, 0xb1d5d564L, 0x9c4e4ed2L, 0x49a9a9e0L,
    0xd86c6cb4L, 0xac5656faL, 0xf3f4f407L, 0xcfeaea25L,
    0xca6565afL, 0xf47a7a8eL, 0x47aeaee9L, 0x10080818L,
    0x6fbabad5L, 0xf0787888L, 0x4a25256fL, 0x5c2e2e72L,
    0x381c1c24L, 0x57a6a6f1L, 0x73b4b4c7L, 0x97c6c651L,
    0xcbe8e823L, 0xa1dddd7cL, 0xe874749cL, 0x3e1f1f21L,
    0x964b4bddL, 0x61bdbddcL, 0x0d8b8b86L, 0x0f8a8a85L,
    0xe0707090L, 0x7c3e3e42L, 0x71b5b5c4L, 0xcc6666aaL,
    0x904848d8L, 0x06030305L, 0xf7f6f601L, 0x1c0e0e12L,
    0xc26161a3L, 0x6a35355fL, 0xae5757f9L, 0x69b9b9d0L,
    0x17868691L, 0x99c1c158L, 0x3a1d1d27L, 0x279e9eb9L,
    0xd9e1e138L, 0xebf8f813L, 0x2b9898b3L, 0x22111133L,
    0xd26969bbL, 0xa9d9d970L, 0x078e8e89L, 0x339494a7L,
    0x2d9b9bb6L, 0x3c1e1e22L, 0x15878792L, 0xc9e9e920L,
    0x87cece49L, 0xaa5555ffL, 0x50282878L, 0xa5dfdf7aL,
    0x038c8c8fL, 0x59a1a1f8L, 0x09898980L, 0x1a0d0d17L,
    0x65bfbfdaL, 0xd7e6e631L, 0x844242c6L, 0xd06868b8L,
    0x824141c3L, 0x299999b0L, 0x5a2d2d77L, 0x1e0f0f11L,
    0x7bb0b0cbL, 0xa85454fcL, 0x6dbbbbd6L, 0x2c16163aL,
]

Te1 = [
    0xa5c66363L, 0x84f87c7cL, 0x99ee7777L, 0x8df67b7bL,
    0x0dfff2f2L, 0xbdd66b6bL, 0xb1de6f6fL, 0x5491c5c5L,
    0x50603030L, 0x03020101L, 0xa9ce6767L, 0x7d562b2bL,
    0x19e7fefeL, 0x62b5d7d7L, 0xe64dababL, 0x9aec7676L,
    0x458fcacaL, 0x9d1f8282L, 0x4089c9c9L, 0x87fa7d7dL,
    0x15effafaL, 0xebb25959L, 0xc98e4747L, 0x0bfbf0f0L,
    0xec41adadL, 0x67b3d4d4L, 0xfd5fa2a2L, 0xea45afafL,
    0xbf239c9cL, 0xf753a4a4L, 0x96e47272L, 0x5b9bc0c0L,
    0xc275b7b7L, 0x1ce1fdfdL, 0xae3d9393L, 0x6a4c2626L,
    0x5a6c3636L, 0x417e3f3fL, 0x02f5f7f7L, 0x4f83ccccL,
    0x5c683434L, 0xf451a5a5L, 0x34d1e5e5L, 0x08f9f1f1L,
    0x93e27171L, 0x73abd8d8L, 0x53623131L, 0x3f2a1515L,
    0x0c080404L, 0x5295c7c7L, 0x65462323L, 0x5e9dc3c3L,
    0x28301818L, 0xa1379696L, 0x0f0a0505L, 0xb52f9a9aL,
    0x090e0707L, 0x36241212L, 0x9b1b8080L, 0x3ddfe2e2L,
    0x26cdebebL, 0x694e2727L, 0xcd7fb2b2L, 0x9fea7575L,
    0x1b120909L, 0x9e1d8383L, 0x74582c2cL, 0x2e341a1aL,
    0x2d361b1bL, 0xb2dc6e6eL, 0xeeb45a5aL, 0xfb5ba0a0L,
    0xf6a45252L, 0x4d763b3bL, 0x61b7d6d6L, 0xce7db3b3L,
    0x7b522929L, 0x3edde3e3L, 0x715e2f2fL, 0x97138484L,
    0xf5a65353L, 0x68b9d1d1L, 0x00000000L, 0x2cc1ededL,
    0x60402020L, 0x1fe3fcfcL, 0xc879b1b1L, 0xedb65b5bL,
    0xbed46a6aL, 0x468dcbcbL, 0xd967bebeL, 0x4b723939L,
    0xde944a4aL, 0xd4984c4cL, 0xe8b05858L, 0x4a85cfcfL,
    0x6bbbd0d0L, 0x2ac5efefL, 0xe54faaaaL, 0x16edfbfbL,
    0xc5864343L, 0xd79a4d4dL, 0x55663333L, 0x94118585L,
    0xcf8a4545L, 0x10e9f9f9L, 0x06040202L, 0x81fe7f7fL,
    0xf0a05050L, 0x44783c3cL, 0xba259f9fL, 0xe34ba8a8L,
    0xf3a25151L, 0xfe5da3a3L, 0xc0804040L, 0x8a058f8fL,
    0xad3f9292L, 0xbc219d9dL, 0x48703838L, 0x04f1f5f5L,
    0xdf63bcbcL, 0xc177b6b6L, 0x75afdadaL, 0x63422121L,
    0x30201010L, 0x1ae5ffffL, 0x0efdf3f3L, 0x6dbfd2d2L,
    0x4c81cdcdL, 0x14180c0cL, 0x35261313L, 0x2fc3ececL,
    0xe1be5f5fL, 0xa2359797L, 0xcc884444L, 0x392e1717L,
    0x5793c4c4L, 0xf255a7a7L, 0x82fc7e7eL, 0x477a3d3dL,
    0xacc86464L, 0xe7ba5d5dL, 0x2b321919L, 0x95e67373L,
    0xa0c06060L, 0x98198181L, 0xd19e4f4fL, 0x7fa3dcdcL,
    0x66442222L, 0x7e542a2aL, 0xab3b9090L, 0x830b8888L,
    0xca8c4646L, 0x29c7eeeeL, 0xd36bb8b8L, 0x3c281414L,
    0x79a7dedeL, 0xe2bc5e5eL, 0x1d160b0bL, 0x76addbdbL,
    0x3bdbe0e0L, 0x56643232L, 0x4e743a3aL, 0x1e140a0aL,
    0xdb924949L, 0x0a0c0606L, 0x6c482424L, 0xe4b85c5cL,
    0x5d9fc2c2L, 0x6ebdd3d3L, 0xef43acacL, 0xa6c46262L,
    0xa8399191L, 0xa4319595L, 0x37d3e4e4L, 0x8bf27979L,
    0x32d5e7e7L, 0x438bc8c8L, 0x596e3737L, 0xb7da6d6dL,
    0x8c018d8dL, 0x64b1d5d5L, 0xd29c4e4eL, 0xe049a9a9L,
    0xb4d86c6cL, 0xfaac5656L, 0x07f3f4f4L, 0x25cfeaeaL,
    0xafca6565L, 0x8ef47a7aL, 0xe947aeaeL, 0x18100808L,
    0xd56fbabaL, 0x88f07878L, 0x6f4a2525L, 0x725c2e2eL,
    0x24381c1cL, 0xf157a6a6L, 0xc773b4b4L, 0x5197c6c6L,
    0x23cbe8e8L, 0x7ca1ddddL, 0x9ce87474L, 0x213e1f1fL,
    0xdd964b4bL, 0xdc61bdbdL, 0x860d8b8bL, 0x850f8a8aL,
    0x90e07070L, 0x427c3e3eL, 0xc471b5b5L, 0xaacc6666L,
    0xd8904848L, 0x05060303L, 0x01f7f6f6L, 0x121c0e0eL,
    0xa3c26161L, 0x5f6a3535L, 0xf9ae5757L, 0xd069b9b9L,
    0x91178686L, 0x5899c1c1L, 0x273a1d1dL, 0xb9279e9eL,
    0x38d9e1e1L, 0x13ebf8f8L, 0xb32b9898L, 0x33221111L,
    0xbbd26969L, 0x70a9d9d9L, 0x89078e8eL, 0xa7339494L,
    0xb62d9b9bL, 0x223c1e1eL, 0x92158787L, 0x20c9e9e9L,
    0x4987ceceL, 0xffaa5555L, 0x78502828L, 0x7aa5dfdfL,
    0x8f038c8cL, 0xf859a1a1L, 0x80098989L, 0x171a0d0dL,
    0xda65bfbfL, 0x31d7e6e6L, 0xc6844242L, 0xb8d06868L,
    0xc3824141L, 0xb0299999L, 0x775a2d2dL, 0x111e0f0fL,
    0xcb7bb0b0L, 0xfca85454L, 0xd66dbbbbL, 0x3a2c1616L,
]

Te2 = [
    0x63a5c663L, 0x7c84f87cL, 0x7799ee77L, 0x7b8df67bL,
    0xf20dfff2L, 0x6bbdd66bL, 0x6fb1de6fL, 0xc55491c5L,
    0x30506030L, 0x01030201L, 0x67a9ce67L, 0x2b7d562bL,
    0xfe19e7feL, 0xd762b5d7L, 0xabe64dabL, 0x769aec76L,
    0xca458fcaL, 0x829d1f82L, 0xc94089c9L, 0x7d87fa7dL,
    0xfa15effaL, 0x59ebb259L, 0x47c98e47L, 0xf00bfbf0L,
    0xadec41adL, 0xd467b3d4L, 0xa2fd5fa2L, 0xafea45afL,
    0x9cbf239cL, 0xa4f753a4L, 0x7296e472L, 0xc05b9bc0L,
    0xb7c275b7L, 0xfd1ce1fdL, 0x93ae3d93L, 0x266a4c26L,
    0x365a6c36L, 0x3f417e3fL, 0xf702f5f7L, 0xcc4f83ccL,
    0x345c6834L, 0xa5f451a5L, 0xe534d1e5L, 0xf108f9f1L,
    0x7193e271L, 0xd873abd8L, 0x31536231L, 0x153f2a15L,
    0x040c0804L, 0xc75295c7L, 0x23654623L, 0xc35e9dc3L,
    0x18283018L, 0x96a13796L, 0x050f0a05L, 0x9ab52f9aL,
    0x07090e07L, 0x12362412L, 0x809b1b80L, 0xe23ddfe2L,
    0xeb26cdebL, 0x27694e27L, 0xb2cd7fb2L, 0x759fea75L,
    0x091b1209L, 0x839e1d83L, 0x2c74582cL, 0x1a2e341aL,
    0x1b2d361bL, 0x6eb2dc6eL, 0x5aeeb45aL, 0xa0fb5ba0L,
    0x52f6a452L, 0x3b4d763bL, 0xd661b7d6L, 0xb3ce7db3L,
    0x297b5229L, 0xe33edde3L, 0x2f715e2fL, 0x84971384L,
    0x53f5a653L, 0xd168b9d1L, 0x00000000L, 0xed2cc1edL,
    0x20604020L, 0xfc1fe3fcL, 0xb1c879b1L, 0x5bedb65bL,
    0x6abed46aL, 0xcb468dcbL, 0xbed967beL, 0x394b7239L,
    0x4ade944aL, 0x4cd4984cL, 0x58e8b058L, 0xcf4a85cfL,
    0xd06bbbd0L, 0xef2ac5efL, 0xaae54faaL, 0xfb16edfbL,
    0x43c58643L, 0x4dd79a4dL, 0x33556633L, 0x85941185L,
    0x45cf8a45L, 0xf910e9f9L, 0x02060402L, 0x7f81fe7fL,
    0x50f0a050L, 0x3c44783cL, 0x9fba259fL, 0xa8e34ba8L,
    0x51f3a251L, 0xa3fe5da3L, 0x40c08040L, 0x8f8a058fL,
    0x92ad3f92L, 0x9dbc219dL, 0x38487038L, 0xf504f1f5L,
    0xbcdf63bcL, 0xb6c177b6L, 0xda75afdaL, 0x21634221L,
    0x10302010L, 0xff1ae5ffL, 0xf30efdf3L, 0xd26dbfd2L,
    0xcd4c81cdL, 0x0c14180cL, 0x13352613L, 0xec2fc3ecL,
    0x5fe1be5fL, 0x97a23597L, 0x44cc8844L, 0x17392e17L,
    0xc45793c4L, 0xa7f255a7L, 0x7e82fc7eL, 0x3d477a3dL,
    0x64acc864L, 0x5de7ba5dL, 0x192b3219L, 0x7395e673L,
    0x60a0c060L, 0x81981981L, 0x4fd19e4fL, 0xdc7fa3dcL,
    0x22664422L, 0x2a7e542aL, 0x90ab3b90L, 0x88830b88L,
    0x46ca8c46L, 0xee29c7eeL, 0xb8d36bb8L, 0x143c2814L,
    0xde79a7deL, 0x5ee2bc5eL, 0x0b1d160bL, 0xdb76addbL,
    0xe03bdbe0L, 0x32566432L, 0x3a4e743aL, 0x0a1e140aL,
    0x49db9249L, 0x060a0c06L, 0x246c4824L, 0x5ce4b85cL,
    0xc25d9fc2L, 0xd36ebdd3L, 0xacef43acL, 0x62a6c462L,
    0x91a83991L, 0x95a43195L, 0xe437d3e4L, 0x798bf279L,
    0xe732d5e7L, 0xc8438bc8L, 0x37596e37L, 0x6db7da6dL,
    0x8d8c018dL, 0xd564b1d5L, 0x4ed29c4eL, 0xa9e049a9L,
    0x6cb4d86cL, 0x56faac56L, 0xf407f3f4L, 0xea25cfeaL,
    0x65afca65L, 0x7a8ef47aL, 0xaee947aeL, 0x08181008L,
    0xbad56fbaL, 0x7888f078L, 0x256f4a25L, 0x2e725c2eL,
    0x1c24381cL, 0xa6f157a6L, 0xb4c773b4L, 0xc65197c6L,
    0xe823cbe8L, 0xdd7ca1ddL, 0x749ce874L, 0x1f213e1fL,
    0x4bdd964bL, 0xbddc61bdL, 0x8b860d8bL, 0x8a850f8aL,
    0x7090e070L, 0x3e427c3eL, 0xb5c471b5L, 0x66aacc66L,
    0x48d89048L, 0x03050603L, 0xf601f7f6L, 0x0e121c0eL,
    0x61a3c261L, 0x355f6a35L, 0x57f9ae57L, 0xb9d069b9L,
    0x86911786L, 0xc15899c1L, 0x1d273a1dL, 0x9eb9279eL,
    0xe138d9e1L, 0xf813ebf8L, 0x98b32b98L, 0x11332211L,
    0x69bbd269L, 0xd970a9d9L, 0x8e89078eL, 0x94a73394L,
    0x9bb62d9bL, 0x1e223c1eL, 0x87921587L, 0xe920c9e9L,
    0xce4987ceL, 0x55ffaa55L, 0x28785028L, 0xdf7aa5dfL,
    0x8c8f038cL, 0xa1f859a1L, 0x89800989L, 0x0d171a0dL,
    0xbfda65bfL, 0xe631d7e6L, 0x42c68442L, 0x68b8d068L,
    0x41c38241L, 0x99b02999L, 0x2d775a2dL, 0x0f111e0fL,
    0xb0cb7bb0L, 0x54fca854L, 0xbbd66dbbL, 0x163a2c16L,
]

Te3 = [
    0x6363a5c6L, 0x7c7c84f8L, 0x777799eeL, 0x7b7b8df6L,
    0xf2f20dffL, 0x6b6bbdd6L, 0x6f6fb1deL, 0xc5c55491L,
    0x30305060L, 0x01010302L, 0x6767a9ceL, 0x2b2b7d56L,
    0xfefe19e7L, 0xd7d762b5L, 0xababe64dL, 0x76769aecL,
    0xcaca458fL, 0x82829d1fL, 0xc9c94089L, 0x7d7d87faL,
    0xfafa15efL, 0x5959ebb2L, 0x4747c98eL, 0xf0f00bfbL,
    0xadadec41L, 0xd4d467b3L, 0xa2a2fd5fL, 0xafafea45L,
    0x9c9cbf23L, 0xa4a4f753L, 0x727296e4L, 0xc0c05b9bL,
    0xb7b7c275L, 0xfdfd1ce1L, 0x9393ae3dL, 0x26266a4cL,
    0x36365a6cL, 0x3f3f417eL, 0xf7f702f5L, 0xcccc4f83L,
    0x34345c68L, 0xa5a5f451L, 0xe5e534d1L, 0xf1f108f9L,
    0x717193e2L, 0xd8d873abL, 0x31315362L, 0x15153f2aL,
    0x04040c08L, 0xc7c75295L, 0x23236546L, 0xc3c35e9dL,
    0x18182830L, 0x9696a137L, 0x05050f0aL, 0x9a9ab52fL,
    0x0707090eL, 0x12123624L, 0x80809b1bL, 0xe2e23ddfL,
    0xebeb26cdL, 0x2727694eL, 0xb2b2cd7fL, 0x75759feaL,
    0x09091b12L, 0x83839e1dL, 0x2c2c7458L, 0x1a1a2e34L,
    0x1b1b2d36L, 0x6e6eb2dcL, 0x5a5aeeb4L, 0xa0a0fb5bL,
    0x5252f6a4L, 0x3b3b4d76L, 0xd6d661b7L, 0xb3b3ce7dL,
    0x29297b52L, 0xe3e33eddL, 0x2f2f715eL, 0x84849713L,
    0x5353f5a6L, 0xd1d168b9L, 0x00000000L, 0xeded2cc1L,
    0x20206040L, 0xfcfc1fe3L, 0xb1b1c879L, 0x5b5bedb6L,
    0x6a6abed4L, 0xcbcb468dL, 0xbebed967L, 0x39394b72L,
    0x4a4ade94L, 0x4c4cd498L, 0x5858e8b0L, 0xcfcf4a85L,
    0xd0d06bbbL, 0xefef2ac5L, 0xaaaae54fL, 0xfbfb16edL,
    0x4343c586L, 0x4d4dd79aL, 0x33335566L, 0x85859411L,
    0x4545cf8aL, 0xf9f910e9L, 0x02020604L, 0x7f7f81feL,
    0x5050f0a0L, 0x3c3c4478L, 0x9f9fba25L, 0xa8a8e34bL,
    0x5151f3a2L, 0xa3a3fe5dL, 0x4040c080L, 0x8f8f8a05L,
    0x9292ad3fL, 0x9d9dbc21L, 0x38384870L, 0xf5f504f1L,
    0xbcbcdf63L, 0xb6b6c177L, 0xdada75afL, 0x21216342L,
    0x10103020L, 0xffff1ae5L, 0xf3f30efdL, 0xd2d26dbfL,
    0xcdcd4c81L, 0x0c0c1418L, 0x13133526L, 0xecec2fc3L,
    0x5f5fe1beL, 0x9797a235L, 0x4444cc88L, 0x1717392eL,
    0xc4c45793L, 0xa7a7f255L, 0x7e7e82fcL, 0x3d3d477aL,
    0x6464acc8L, 0x5d5de7baL, 0x19192b32L, 0x737395e6L,
    0x6060a0c0L, 0x81819819L, 0x4f4fd19eL, 0xdcdc7fa3L,
    0x22226644L, 0x2a2a7e54L, 0x9090ab3bL, 0x8888830bL,
    0x4646ca8cL, 0xeeee29c7L, 0xb8b8d36bL, 0x14143c28L,
    0xdede79a7L, 0x5e5ee2bcL, 0x0b0b1d16L, 0xdbdb76adL,
    0xe0e03bdbL, 0x32325664L, 0x3a3a4e74L, 0x0a0a1e14L,
    0x4949db92L, 0x06060a0cL, 0x24246c48L, 0x5c5ce4b8L,
    0xc2c25d9fL, 0xd3d36ebdL, 0xacacef43L, 0x6262a6c4L,
    0x9191a839L, 0x9595a431L, 0xe4e437d3L, 0x79798bf2L,
    0xe7e732d5L, 0xc8c8438bL, 0x3737596eL, 0x6d6db7daL,
    0x8d8d8c01L, 0xd5d564b1L, 0x4e4ed29cL, 0xa9a9e049L,
    0x6c6cb4d8L, 0x5656faacL, 0xf4f407f3L, 0xeaea25cfL,
    0x6565afcaL, 0x7a7a8ef4L, 0xaeaee947L, 0x08081810L,
    0xbabad56fL, 0x787888f0L, 0x25256f4aL, 0x2e2e725cL,
    0x1c1c2438L, 0xa6a6f157L, 0xb4b4c773L, 0xc6c65197L,
    0xe8e823cbL, 0xdddd7ca1L, 0x74749ce8L, 0x1f1f213eL,
    0x4b4bdd96L, 0xbdbddc61L, 0x8b8b860dL, 0x8a8a850fL,
    0x707090e0L, 0x3e3e427cL, 0xb5b5c471L, 0x6666aaccL,
    0x4848d890L, 0x03030506L, 0xf6f601f7L, 0x0e0e121cL,
    0x6161a3c2L, 0x35355f6aL, 0x5757f9aeL, 0xb9b9d069L,
    0x86869117L, 0xc1c15899L, 0x1d1d273aL, 0x9e9eb927L,
    0xe1e138d9L, 0xf8f813ebL, 0x9898b32bL, 0x11113322L,
    0x6969bbd2L, 0xd9d970a9L, 0x8e8e8907L, 0x9494a733L,
    0x9b9bb62dL, 0x1e1e223cL, 0x87879215L, 0xe9e920c9L,
    0xcece4987L, 0x5555ffaaL, 0x28287850L, 0xdfdf7aa5L,
    0x8c8c8f03L, 0xa1a1f859L, 0x89898009L, 0x0d0d171aL,
    0xbfbfda65L, 0xe6e631d7L, 0x4242c684L, 0x6868b8d0L,
    0x4141c382L, 0x9999b029L, 0x2d2d775aL, 0x0f0f111eL,
    0xb0b0cb7bL, 0x5454fca8L, 0xbbbbd66dL, 0x16163a2cL,
]

Te4 = [
    0x63636363L, 0x7c7c7c7cL, 0x77777777L, 0x7b7b7b7bL,
    0xf2f2f2f2L, 0x6b6b6b6bL, 0x6f6f6f6fL, 0xc5c5c5c5L,
    0x30303030L, 0x01010101L, 0x67676767L, 0x2b2b2b2bL,
    0xfefefefeL, 0xd7d7d7d7L, 0xababababL, 0x76767676L,
    0xcacacacaL, 0x82828282L, 0xc9c9c9c9L, 0x7d7d7d7dL,
    0xfafafafaL, 0x59595959L, 0x47474747L, 0xf0f0f0f0L,
    0xadadadadL, 0xd4d4d4d4L, 0xa2a2a2a2L, 0xafafafafL,
    0x9c9c9c9cL, 0xa4a4a4a4L, 0x72727272L, 0xc0c0c0c0L,
    0xb7b7b7b7L, 0xfdfdfdfdL, 0x93939393L, 0x26262626L,
    0x36363636L, 0x3f3f3f3fL, 0xf7f7f7f7L, 0xccccccccL,
    0x34343434L, 0xa5a5a5a5L, 0xe5e5e5e5L, 0xf1f1f1f1L,
    0x71717171L, 0xd8d8d8d8L, 0x31313131L, 0x15151515L,
    0x04040404L, 0xc7c7c7c7L, 0x23232323L, 0xc3c3c3c3L,
    0x18181818L, 0x96969696L, 0x05050505L, 0x9a9a9a9aL,
    0x07070707L, 0x12121212L, 0x80808080L, 0xe2e2e2e2L,
    0xebebebebL, 0x27272727L, 0xb2b2b2b2L, 0x75757575L,
    0x09090909L, 0x83838383L, 0x2c2c2c2cL, 0x1a1a1a1aL,
    0x1b1b1b1bL, 0x6e6e6e6eL, 0x5a5a5a5aL, 0xa0a0a0a0L,
    0x52525252L, 0x3b3b3b3bL, 0xd6d6d6d6L, 0xb3b3b3b3L,
    0x29292929L, 0xe3e3e3e3L, 0x2f2f2f2fL, 0x84848484L,
    0x53535353L, 0xd1d1d1d1L, 0x00000000L, 0xededededL,
    0x20202020L, 0xfcfcfcfcL, 0xb1b1b1b1L, 0x5b5b5b5bL,
    0x6a6a6a6aL, 0xcbcbcbcbL, 0xbebebebeL, 0x39393939L,
    0x4a4a4a4aL, 0x4c4c4c4cL, 0x58585858L, 0xcfcfcfcfL,
    0xd0d0d0d0L, 0xefefefefL, 0xaaaaaaaaL, 0xfbfbfbfbL,
    0x43434343L, 0x4d4d4d4dL, 0x33333333L, 0x85858585L,
    0x45454545L, 0xf9f9f9f9L, 0x02020202L, 0x7f7f7f7fL,
    0x50505050L, 0x3c3c3c3cL, 0x9f9f9f9fL, 0xa8a8a8a8L,
    0x51515151L, 0xa3a3a3a3L, 0x40404040L, 0x8f8f8f8fL,
    0x92929292L, 0x9d9d9d9dL, 0x38383838L, 0xf5f5f5f5L,
    0xbcbcbcbcL, 0xb6b6b6b6L, 0xdadadadaL, 0x21212121L,
    0x10101010L, 0xffffffffL, 0xf3f3f3f3L, 0xd2d2d2d2L,
    0xcdcdcdcdL, 0x0c0c0c0cL, 0x13131313L, 0xececececL,
    0x5f5f5f5fL, 0x97979797L, 0x44444444L, 0x17171717L,
    0xc4c4c4c4L, 0xa7a7a7a7L, 0x7e7e7e7eL, 0x3d3d3d3dL,
    0x64646464L, 0x5d5d5d5dL, 0x19191919L, 0x73737373L,
    0x60606060L, 0x81818181L, 0x4f4f4f4fL, 0xdcdcdcdcL,
    0x22222222L, 0x2a2a2a2aL, 0x90909090L, 0x88888888L,
    0x46464646L, 0xeeeeeeeeL, 0xb8b8b8b8L, 0x14141414L,
    0xdedededeL, 0x5e5e5e5eL, 0x0b0b0b0bL, 0xdbdbdbdbL,
    0xe0e0e0e0L, 0x32323232L, 0x3a3a3a3aL, 0x0a0a0a0aL,
    0x49494949L, 0x06060606L, 0x24242424L, 0x5c5c5c5cL,
    0xc2c2c2c2L, 0xd3d3d3d3L, 0xacacacacL, 0x62626262L,
    0x91919191L, 0x95959595L, 0xe4e4e4e4L, 0x79797979L,
    0xe7e7e7e7L, 0xc8c8c8c8L, 0x37373737L, 0x6d6d6d6dL,
    0x8d8d8d8dL, 0xd5d5d5d5L, 0x4e4e4e4eL, 0xa9a9a9a9L,
    0x6c6c6c6cL, 0x56565656L, 0xf4f4f4f4L, 0xeaeaeaeaL,
    0x65656565L, 0x7a7a7a7aL, 0xaeaeaeaeL, 0x08080808L,
    0xbabababaL, 0x78787878L, 0x25252525L, 0x2e2e2e2eL,
    0x1c1c1c1cL, 0xa6a6a6a6L, 0xb4b4b4b4L, 0xc6c6c6c6L,
    0xe8e8e8e8L, 0xddddddddL, 0x74747474L, 0x1f1f1f1fL,
    0x4b4b4b4bL, 0xbdbdbdbdL, 0x8b8b8b8bL, 0x8a8a8a8aL,
    0x70707070L, 0x3e3e3e3eL, 0xb5b5b5b5L, 0x66666666L,
    0x48484848L, 0x03030303L, 0xf6f6f6f6L, 0x0e0e0e0eL,
    0x61616161L, 0x35353535L, 0x57575757L, 0xb9b9b9b9L,
    0x86868686L, 0xc1c1c1c1L, 0x1d1d1d1dL, 0x9e9e9e9eL,
    0xe1e1e1e1L, 0xf8f8f8f8L, 0x98989898L, 0x11111111L,
    0x69696969L, 0xd9d9d9d9L, 0x8e8e8e8eL, 0x94949494L,
    0x9b9b9b9bL, 0x1e1e1e1eL, 0x87878787L, 0xe9e9e9e9L,
    0xcecececeL, 0x55555555L, 0x28282828L, 0xdfdfdfdfL,
    0x8c8c8c8cL, 0xa1a1a1a1L, 0x89898989L, 0x0d0d0d0dL,
    0xbfbfbfbfL, 0xe6e6e6e6L, 0x42424242L, 0x68686868L,
    0x41414141L, 0x99999999L, 0x2d2d2d2dL, 0x0f0f0f0fL,
    0xb0b0b0b0L, 0x54545454L, 0xbbbbbbbbL, 0x16161616L,
]

Td0 = [
    0x51f4a750L, 0x7e416553L, 0x1a17a4c3L, 0x3a275e96L,
    0x3bab6bcbL, 0x1f9d45f1L, 0xacfa58abL, 0x4be30393L,
    0x2030fa55L, 0xad766df6L, 0x88cc7691L, 0xf5024c25L,
    0x4fe5d7fcL, 0xc52acbd7L, 0x26354480L, 0xb562a38fL,
    0xdeb15a49L, 0x25ba1b67L, 0x45ea0e98L, 0x5dfec0e1L,
    0xc32f7502L, 0x814cf012L, 0x8d4697a3L, 0x6bd3f9c6L,
    0x038f5fe7L, 0x15929c95L, 0xbf6d7aebL, 0x955259daL,
    0xd4be832dL, 0x587421d3L, 0x49e06929L, 0x8ec9c844L,
    0x75c2896aL, 0xf48e7978L, 0x99583e6bL, 0x27b971ddL,
    0xbee14fb6L, 0xf088ad17L, 0xc920ac66L, 0x7dce3ab4L,
    0x63df4a18L, 0xe51a3182L, 0x97513360L, 0x62537f45L,
    0xb16477e0L, 0xbb6bae84L, 0xfe81a01cL, 0xf9082b94L,
    0x70486858L, 0x8f45fd19L, 0x94de6c87L, 0x527bf8b7L,
    0xab73d323L, 0x724b02e2L, 0xe31f8f57L, 0x6655ab2aL,
    0xb2eb2807L, 0x2fb5c203L, 0x86c57b9aL, 0xd33708a5L,
    0x302887f2L, 0x23bfa5b2L, 0x02036abaL, 0xed16825cL,
    0x8acf1c2bL, 0xa779b492L, 0xf307f2f0L, 0x4e69e2a1L,
    0x65daf4cdL, 0x0605bed5L, 0xd134621fL, 0xc4a6fe8aL,
    0x342e539dL, 0xa2f355a0L, 0x058ae132L, 0xa4f6eb75L,
    0x0b83ec39L, 0x4060efaaL, 0x5e719f06L, 0xbd6e1051L,
    0x3e218af9L, 0x96dd063dL, 0xdd3e05aeL, 0x4de6bd46L,
    0x91548db5L, 0x71c45d05L, 0x0406d46fL, 0x605015ffL,
    0x1998fb24L, 0xd6bde997L, 0x894043ccL, 0x67d99e77L,
    0xb0e842bdL, 0x07898b88L, 0xe7195b38L, 0x79c8eedbL,
    0xa17c0a47L, 0x7c420fe9L, 0xf8841ec9L, 0x00000000L,
    0x09808683L, 0x322bed48L, 0x1e1170acL, 0x6c5a724eL,
    0xfd0efffbL, 0x0f853856L, 0x3daed51eL, 0x362d3927L,
    0x0a0fd964L, 0x685ca621L, 0x9b5b54d1L, 0x24362e3aL,
    0x0c0a67b1L, 0x9357e70fL, 0xb4ee96d2L, 0x1b9b919eL,
    0x80c0c54fL, 0x61dc20a2L, 0x5a774b69L, 0x1c121a16L,
    0xe293ba0aL, 0xc0a02ae5L, 0x3c22e043L, 0x121b171dL,
    0x0e090d0bL, 0xf28bc7adL, 0x2db6a8b9L, 0x141ea9c8L,
    0x57f11985L, 0xaf75074cL, 0xee99ddbbL, 0xa37f60fdL,
    0xf701269fL, 0x5c72f5bcL, 0x44663bc5L, 0x5bfb7e34L,
    0x8b432976L, 0xcb23c6dcL, 0xb6edfc68L, 0xb8e4f163L,
    0xd731dccaL, 0x42638510L, 0x13972240L, 0x84c61120L,
    0x854a247dL, 0xd2bb3df8L, 0xaef93211L, 0xc729a16dL,
    0x1d9e2f4bL, 0xdcb230f3L, 0x0d8652ecL, 0x77c1e3d0L,
    0x2bb3166cL, 0xa970b999L, 0x119448faL, 0x47e96422L,
    0xa8fc8cc4L, 0xa0f03f1aL, 0x567d2cd8L, 0x223390efL,
    0x87494ec7L, 0xd938d1c1L, 0x8ccaa2feL, 0x98d40b36L,
    0xa6f581cfL, 0xa57ade28L, 0xdab78e26L, 0x3fadbfa4L,
    0x2c3a9de4L, 0x5078920dL, 0x6a5fcc9bL, 0x547e4662L,
    0xf68d13c2L, 0x90d8b8e8L, 0x2e39f75eL, 0x82c3aff5L,
    0x9f5d80beL, 0x69d0937cL, 0x6fd52da9L, 0xcf2512b3L,
    0xc8ac993bL, 0x10187da7L, 0xe89c636eL, 0xdb3bbb7bL,
    0xcd267809L, 0x6e5918f4L, 0xec9ab701L, 0x834f9aa8L,
    0xe6956e65L, 0xaaffe67eL, 0x21bccf08L, 0xef15e8e6L,
    0xbae79bd9L, 0x4a6f36ceL, 0xea9f09d4L, 0x29b07cd6L,
    0x31a4b2afL, 0x2a3f2331L, 0xc6a59430L, 0x35a266c0L,
    0x744ebc37L, 0xfc82caa6L, 0xe090d0b0L, 0x33a7d815L,
    0xf104984aL, 0x41ecdaf7L, 0x7fcd500eL, 0x1791f62fL,
    0x764dd68dL, 0x43efb04dL, 0xccaa4d54L, 0xe49604dfL,
    0x9ed1b5e3L, 0x4c6a881bL, 0xc12c1fb8L, 0x4665517fL,
    0x9d5eea04L, 0x018c355dL, 0xfa877473L, 0xfb0b412eL,
    0xb3671d5aL, 0x92dbd252L, 0xe9105633L, 0x6dd64713L,
    0x9ad7618cL, 0x37a10c7aL, 0x59f8148eL, 0xeb133c89L,
    0xcea927eeL, 0xb761c935L, 0xe11ce5edL, 0x7a47b13cL,
    0x9cd2df59L, 0x55f2733fL, 0x1814ce79L, 0x73c737bfL,
    0x53f7cdeaL, 0x5ffdaa5bL, 0xdf3d6f14L, 0x7844db86L,
    0xcaaff381L, 0xb968c43eL, 0x3824342cL, 0xc2a3405fL,
    0x161dc372L, 0xbce2250cL, 0x283c498bL, 0xff0d9541L,
    0x39a80171L, 0x080cb3deL, 0xd8b4e49cL, 0x6456c190L,
    0x7bcb8461L, 0xd532b670L, 0x486c5c74L, 0xd0b85742L,
]

Td1 = [
    0x5051f4a7L, 0x537e4165L, 0xc31a17a4L, 0x963a275eL,
    0xcb3bab6bL, 0xf11f9d45L, 0xabacfa58L, 0x934be303L,
    0x552030faL, 0xf6ad766dL, 0x9188cc76L, 0x25f5024cL,
    0xfc4fe5d7L, 0xd7c52acbL, 0x80263544L, 0x8fb562a3L,
    0x49deb15aL, 0x6725ba1bL, 0x9845ea0eL, 0xe15dfec0L,
    0x02c32f75L, 0x12814cf0L, 0xa38d4697L, 0xc66bd3f9L,
    0xe7038f5fL, 0x9515929cL, 0xebbf6d7aL, 0xda955259L,
    0x2dd4be83L, 0xd3587421L, 0x2949e069L, 0x448ec9c8L,
    0x6a75c289L, 0x78f48e79L, 0x6b99583eL, 0xdd27b971L,
    0xb6bee14fL, 0x17f088adL, 0x66c920acL, 0xb47dce3aL,
    0x1863df4aL, 0x82e51a31L, 0x60975133L, 0x4562537fL,
    0xe0b16477L, 0x84bb6baeL, 0x1cfe81a0L, 0x94f9082bL,
    0x58704868L, 0x198f45fdL, 0x8794de6cL, 0xb7527bf8L,
    0x23ab73d3L, 0xe2724b02L, 0x57e31f8fL, 0x2a6655abL,
    0x07b2eb28L, 0x032fb5c2L, 0x9a86c57bL, 0xa5d33708L,
    0xf2302887L, 0xb223bfa5L, 0xba02036aL, 0x5ced1682L,
    0x2b8acf1cL, 0x92a779b4L, 0xf0f307f2L, 0xa14e69e2L,
    0xcd65daf4L, 0xd50605beL, 0x1fd13462L, 0x8ac4a6feL,
    0x9d342e53L, 0xa0a2f355L, 0x32058ae1L, 0x75a4f6ebL,
    0x390b83ecL, 0xaa4060efL, 0x065e719fL, 0x51bd6e10L,
    0xf93e218aL, 0x3d96dd06L, 0xaedd3e05L, 0x464de6bdL,
    0xb591548dL, 0x0571c45dL, 0x6f0406d4L, 0xff605015L,
    0x241998fbL, 0x97d6bde9L, 0xcc894043L, 0x7767d99eL,
    0xbdb0e842L, 0x8807898bL, 0x38e7195bL, 0xdb79c8eeL,
    0x47a17c0aL, 0xe97c420fL, 0xc9f8841eL, 0x00000000L,
    0x83098086L, 0x48322bedL, 0xac1e1170L, 0x4e6c5a72L,
    0xfbfd0effL, 0x560f8538L, 0x1e3daed5L, 0x27362d39L,
    0x640a0fd9L, 0x21685ca6L, 0xd19b5b54L, 0x3a24362eL,
    0xb10c0a67L, 0x0f9357e7L, 0xd2b4ee96L, 0x9e1b9b91L,
    0x4f80c0c5L, 0xa261dc20L, 0x695a774bL, 0x161c121aL,
    0x0ae293baL, 0xe5c0a02aL, 0x433c22e0L, 0x1d121b17L,
    0x0b0e090dL, 0xadf28bc7L, 0xb92db6a8L, 0xc8141ea9L,
    0x8557f119L, 0x4caf7507L, 0xbbee99ddL, 0xfda37f60L,
    0x9ff70126L, 0xbc5c72f5L, 0xc544663bL, 0x345bfb7eL,
    0x768b4329L, 0xdccb23c6L, 0x68b6edfcL, 0x63b8e4f1L,
    0xcad731dcL, 0x10426385L, 0x40139722L, 0x2084c611L,
    0x7d854a24L, 0xf8d2bb3dL, 0x11aef932L, 0x6dc729a1L,
    0x4b1d9e2fL, 0xf3dcb230L, 0xec0d8652L, 0xd077c1e3L,
    0x6c2bb316L, 0x99a970b9L, 0xfa119448L, 0x2247e964L,
    0xc4a8fc8cL, 0x1aa0f03fL, 0xd8567d2cL, 0xef223390L,
    0xc787494eL, 0xc1d938d1L, 0xfe8ccaa2L, 0x3698d40bL,
    0xcfa6f581L, 0x28a57adeL, 0x26dab78eL, 0xa43fadbfL,
    0xe42c3a9dL, 0x0d507892L, 0x9b6a5fccL, 0x62547e46L,
    0xc2f68d13L, 0xe890d8b8L, 0x5e2e39f7L, 0xf582c3afL,
    0xbe9f5d80L, 0x7c69d093L, 0xa96fd52dL, 0xb3cf2512L,
    0x3bc8ac99L, 0xa710187dL, 0x6ee89c63L, 0x7bdb3bbbL,
    0x09cd2678L, 0xf46e5918L, 0x01ec9ab7L, 0xa8834f9aL,
    0x65e6956eL, 0x7eaaffe6L, 0x0821bccfL, 0xe6ef15e8L,
    0xd9bae79bL, 0xce4a6f36L, 0xd4ea9f09L, 0xd629b07cL,
    0xaf31a4b2L, 0x312a3f23L, 0x30c6a594L, 0xc035a266L,
    0x37744ebcL, 0xa6fc82caL, 0xb0e090d0L, 0x1533a7d8L,
    0x4af10498L, 0xf741ecdaL, 0x0e7fcd50L, 0x2f1791f6L,
    0x8d764dd6L, 0x4d43efb0L, 0x54ccaa4dL, 0xdfe49604L,
    0xe39ed1b5L, 0x1b4c6a88L, 0xb8c12c1fL, 0x7f466551L,
    0x049d5eeaL, 0x5d018c35L, 0x73fa8774L, 0x2efb0b41L,
    0x5ab3671dL, 0x5292dbd2L, 0x33e91056L, 0x136dd647L,
    0x8c9ad761L, 0x7a37a10cL, 0x8e59f814L, 0x89eb133cL,
    0xeecea927L, 0x35b761c9L, 0xede11ce5L, 0x3c7a47b1L,
    0x599cd2dfL, 0x3f55f273L, 0x791814ceL, 0xbf73c737L,
    0xea53f7cdL, 0x5b5ffdaaL, 0x14df3d6fL, 0x867844dbL,
    0x81caaff3L, 0x3eb968c4L, 0x2c382434L, 0x5fc2a340L,
    0x72161dc3L, 0x0cbce225L, 0x8b283c49L, 0x41ff0d95L,
    0x7139a801L, 0xde080cb3L, 0x9cd8b4e4L, 0x906456c1L,
    0x617bcb84L, 0x70d532b6L, 0x74486c5cL, 0x42d0b857L,
]

Td2 = [
    0xa75051f4L, 0x65537e41L, 0xa4c31a17L, 0x5e963a27L,
    0x6bcb3babL, 0x45f11f9dL, 0x58abacfaL, 0x03934be3L,
    0xfa552030L, 0x6df6ad76L, 0x769188ccL, 0x4c25f502L,
    0xd7fc4fe5L, 0xcbd7c52aL, 0x44802635L, 0xa38fb562L,
    0x5a49deb1L, 0x1b6725baL, 0x0e9845eaL, 0xc0e15dfeL,
    0x7502c32fL, 0xf012814cL, 0x97a38d46L, 0xf9c66bd3L,
    0x5fe7038fL, 0x9c951592L, 0x7aebbf6dL, 0x59da9552L,
    0x832dd4beL, 0x21d35874L, 0x692949e0L, 0xc8448ec9L,
    0x896a75c2L, 0x7978f48eL, 0x3e6b9958L, 0x71dd27b9L,
    0x4fb6bee1L, 0xad17f088L, 0xac66c920L, 0x3ab47dceL,
    0x4a1863dfL, 0x3182e51aL, 0x33609751L, 0x7f456253L,
    0x77e0b164L, 0xae84bb6bL, 0xa01cfe81L, 0x2b94f908L,
    0x68587048L, 0xfd198f45L, 0x6c8794deL, 0xf8b7527bL,
    0xd323ab73L, 0x02e2724bL, 0x8f57e31fL, 0xab2a6655L,
    0x2807b2ebL, 0xc2032fb5L, 0x7b9a86c5L, 0x08a5d337L,
    0x87f23028L, 0xa5b223bfL, 0x6aba0203L, 0x825ced16L,
    0x1c2b8acfL, 0xb492a779L, 0xf2f0f307L, 0xe2a14e69L,
    0xf4cd65daL, 0xbed50605L, 0x621fd134L, 0xfe8ac4a6L,
    0x539d342eL, 0x55a0a2f3L, 0xe132058aL, 0xeb75a4f6L,
    0xec390b83L, 0xefaa4060L, 0x9f065e71L, 0x1051bd6eL,
    0x8af93e21L, 0x063d96ddL, 0x05aedd3eL, 0xbd464de6L,
    0x8db59154L, 0x5d0571c4L, 0xd46f0406L, 0x15ff6050L,
    0xfb241998L, 0xe997d6bdL, 0x43cc8940L, 0x9e7767d9L,
    0x42bdb0e8L, 0x8b880789L, 0x5b38e719L, 0xeedb79c8L,
    0x0a47a17cL, 0x0fe97c42L, 0x1ec9f884L, 0x00000000L,
    0x86830980L, 0xed48322bL, 0x70ac1e11L, 0x724e6c5aL,
    0xfffbfd0eL, 0x38560f85L, 0xd51e3daeL, 0x3927362dL,
    0xd9640a0fL, 0xa621685cL, 0x54d19b5bL, 0x2e3a2436L,
    0x67b10c0aL, 0xe70f9357L, 0x96d2b4eeL, 0x919e1b9bL,
    0xc54f80c0L, 0x20a261dcL, 0x4b695a77L, 0x1a161c12L,
    0xba0ae293L, 0x2ae5c0a0L, 0xe0433c22L, 0x171d121bL,
    0x0d0b0e09L, 0xc7adf28bL, 0xa8b92db6L, 0xa9c8141eL,
    0x198557f1L, 0x074caf75L, 0xddbbee99L, 0x60fda37fL,
    0x269ff701L, 0xf5bc5c72L, 0x3bc54466L, 0x7e345bfbL,
    0x29768b43L, 0xc6dccb23L, 0xfc68b6edL, 0xf163b8e4L,
    0xdccad731L, 0x85104263L, 0x22401397L, 0x112084c6L,
    0x247d854aL, 0x3df8d2bbL, 0x3211aef9L, 0xa16dc729L,
    0x2f4b1d9eL, 0x30f3dcb2L, 0x52ec0d86L, 0xe3d077c1L,
    0x166c2bb3L, 0xb999a970L, 0x48fa1194L, 0x642247e9L,
    0x8cc4a8fcL, 0x3f1aa0f0L, 0x2cd8567dL, 0x90ef2233L,
    0x4ec78749L, 0xd1c1d938L, 0xa2fe8ccaL, 0x0b3698d4L,
    0x81cfa6f5L, 0xde28a57aL, 0x8e26dab7L, 0xbfa43fadL,
    0x9de42c3aL, 0x920d5078L, 0xcc9b6a5fL, 0x4662547eL,
    0x13c2f68dL, 0xb8e890d8L, 0xf75e2e39L, 0xaff582c3L,
    0x80be9f5dL, 0x937c69d0L, 0x2da96fd5L, 0x12b3cf25L,
    0x993bc8acL, 0x7da71018L, 0x636ee89cL, 0xbb7bdb3bL,
    0x7809cd26L, 0x18f46e59L, 0xb701ec9aL, 0x9aa8834fL,
    0x6e65e695L, 0xe67eaaffL, 0xcf0821bcL, 0xe8e6ef15L,
    0x9bd9bae7L, 0x36ce4a6fL, 0x09d4ea9fL, 0x7cd629b0L,
    0xb2af31a4L, 0x23312a3fL, 0x9430c6a5L, 0x66c035a2L,
    0xbc37744eL, 0xcaa6fc82L, 0xd0b0e090L, 0xd81533a7L,
    0x984af104L, 0xdaf741ecL, 0x500e7fcdL, 0xf62f1791L,
    0xd68d764dL, 0xb04d43efL, 0x4d54ccaaL, 0x04dfe496L,
    0xb5e39ed1L, 0x881b4c6aL, 0x1fb8c12cL, 0x517f4665L,
    0xea049d5eL, 0x355d018cL, 0x7473fa87L, 0x412efb0bL,
    0x1d5ab367L, 0xd25292dbL, 0x5633e910L, 0x47136dd6L,
    0x618c9ad7L, 0x0c7a37a1L, 0x148e59f8L, 0x3c89eb13L,
    0x27eecea9L, 0xc935b761L, 0xe5ede11cL, 0xb13c7a47L,
    0xdf599cd2L, 0x733f55f2L, 0xce791814L, 0x37bf73c7L,
    0xcdea53f7L, 0xaa5b5ffdL, 0x6f14df3dL, 0xdb867844L,
    0xf381caafL, 0xc43eb968L, 0x342c3824L, 0x405fc2a3L,
    0xc372161dL, 0x250cbce2L, 0x498b283cL, 0x9541ff0dL,
    0x017139a8L, 0xb3de080cL, 0xe49cd8b4L, 0xc1906456L,
    0x84617bcbL, 0xb670d532L, 0x5c74486cL, 0x5742d0b8L,
]

Td3 = [
    0xf4a75051L, 0x4165537eL, 0x17a4c31aL, 0x275e963aL,
    0xab6bcb3bL, 0x9d45f11fL, 0xfa58abacL, 0xe303934bL,
    0x30fa5520L, 0x766df6adL, 0xcc769188L, 0x024c25f5L,
    0xe5d7fc4fL, 0x2acbd7c5L, 0x35448026L, 0x62a38fb5L,
    0xb15a49deL, 0xba1b6725L, 0xea0e9845L, 0xfec0e15dL,
    0x2f7502c3L, 0x4cf01281L, 0x4697a38dL, 0xd3f9c66bL,
    0x8f5fe703L, 0x929c9515L, 0x6d7aebbfL, 0x5259da95L,
    0xbe832dd4L, 0x7421d358L, 0xe0692949L, 0xc9c8448eL,
    0xc2896a75L, 0x8e7978f4L, 0x583e6b99L, 0xb971dd27L,
    0xe14fb6beL, 0x88ad17f0L, 0x20ac66c9L, 0xce3ab47dL,
    0xdf4a1863L, 0x1a3182e5L, 0x51336097L, 0x537f4562L,
    0x6477e0b1L, 0x6bae84bbL, 0x81a01cfeL, 0x082b94f9L,
    0x48685870L, 0x45fd198fL, 0xde6c8794L, 0x7bf8b752L,
    0x73d323abL, 0x4b02e272L, 0x1f8f57e3L, 0x55ab2a66L,
    0xeb2807b2L, 0xb5c2032fL, 0xc57b9a86L, 0x3708a5d3L,
    0x2887f230L, 0xbfa5b223L, 0x036aba02L, 0x16825cedL,
    0xcf1c2b8aL, 0x79b492a7L, 0x07f2f0f3L, 0x69e2a14eL,
    0xdaf4cd65L, 0x05bed506L, 0x34621fd1L, 0xa6fe8ac4L,
    0x2e539d34L, 0xf355a0a2L, 0x8ae13205L, 0xf6eb75a4L,
    0x83ec390bL, 0x60efaa40L, 0x719f065eL, 0x6e1051bdL,
    0x218af93eL, 0xdd063d96L, 0x3e05aeddL, 0xe6bd464dL,
    0x548db591L, 0xc45d0571L, 0x06d46f04L, 0x5015ff60L,
    0x98fb2419L, 0xbde997d6L, 0x4043cc89L, 0xd99e7767L,
    0xe842bdb0L, 0x898b8807L, 0x195b38e7L, 0xc8eedb79L,
    0x7c0a47a1L, 0x420fe97cL, 0x841ec9f8L, 0x00000000L,
    0x80868309L, 0x2bed4832L, 0x1170ac1eL, 0x5a724e6cL,
    0x0efffbfdL, 0x8538560fL, 0xaed51e3dL, 0x2d392736L,
    0x0fd9640aL, 0x5ca62168L, 0x5b54d19bL, 0x362e3a24L,
    0x0a67b10cL, 0x57e70f93L, 0xee96d2b4L, 0x9b919e1bL,
    0xc0c54f80L, 0xdc20a261L, 0x774b695aL, 0x121a161cL,
    0x93ba0ae2L, 0xa02ae5c0L, 0x22e0433cL, 0x1b171d12L,
    0x090d0b0eL, 0x8bc7adf2L, 0xb6a8b92dL, 0x1ea9c814L,
    0xf1198557L, 0x75074cafL, 0x99ddbbeeL, 0x7f60fda3L,
    0x01269ff7L, 0x72f5bc5cL, 0x663bc544L, 0xfb7e345bL,
    0x4329768bL, 0x23c6dccbL, 0xedfc68b6L, 0xe4f163b8L,
    0x31dccad7L, 0x63851042L, 0x97224013L, 0xc6112084L,
    0x4a247d85L, 0xbb3df8d2L, 0xf93211aeL, 0x29a16dc7L,
    0x9e2f4b1dL, 0xb230f3dcL, 0x8652ec0dL, 0xc1e3d077L,
    0xb3166c2bL, 0x70b999a9L, 0x9448fa11L, 0xe9642247L,
    0xfc8cc4a8L, 0xf03f1aa0L, 0x7d2cd856L, 0x3390ef22L,
    0x494ec787L, 0x38d1c1d9L, 0xcaa2fe8cL, 0xd40b3698L,
    0xf581cfa6L, 0x7ade28a5L, 0xb78e26daL, 0xadbfa43fL,
    0x3a9de42cL, 0x78920d50L, 0x5fcc9b6aL, 0x7e466254L,
    0x8d13c2f6L, 0xd8b8e890L, 0x39f75e2eL, 0xc3aff582L,
    0x5d80be9fL, 0xd0937c69L, 0xd52da96fL, 0x2512b3cfL,
    0xac993bc8L, 0x187da710L, 0x9c636ee8L, 0x3bbb7bdbL,
    0x267809cdL, 0x5918f46eL, 0x9ab701ecL, 0x4f9aa883L,
    0x956e65e6L, 0xffe67eaaL, 0xbccf0821L, 0x15e8e6efL,
    0xe79bd9baL, 0x6f36ce4aL, 0x9f09d4eaL, 0xb07cd629L,
    0xa4b2af31L, 0x3f23312aL, 0xa59430c6L, 0xa266c035L,
    0x4ebc3774L, 0x82caa6fcL, 0x90d0b0e0L, 0xa7d81533L,
    0x04984af1L, 0xecdaf741L, 0xcd500e7fL, 0x91f62f17L,
    0x4dd68d76L, 0xefb04d43L, 0xaa4d54ccL, 0x9604dfe4L,
    0xd1b5e39eL, 0x6a881b4cL, 0x2c1fb8c1L, 0x65517f46L,
    0x5eea049dL, 0x8c355d01L, 0x877473faL, 0x0b412efbL,
    0x671d5ab3L, 0xdbd25292L, 0x105633e9L, 0xd647136dL,
    0xd7618c9aL, 0xa10c7a37L, 0xf8148e59L, 0x133c89ebL,
    0xa927eeceL, 0x61c935b7L, 0x1ce5ede1L, 0x47b13c7aL,
    0xd2df599cL, 0xf2733f55L, 0x14ce7918L, 0xc737bf73L,
    0xf7cdea53L, 0xfdaa5b5fL, 0x3d6f14dfL, 0x44db8678L,
    0xaff381caL, 0x68c43eb9L, 0x24342c38L, 0xa3405fc2L,
    0x1dc37216L, 0xe2250cbcL, 0x3c498b28L, 0x0d9541ffL,
    0xa8017139L, 0x0cb3de08L, 0xb4e49cd8L, 0x56c19064L,
    0xcb84617bL, 0x32b670d5L, 0x6c5c7448L, 0xb85742d0L,
]

Td4 = [
    0x52525252L, 0x09090909L, 0x6a6a6a6aL, 0xd5d5d5d5L,
    0x30303030L, 0x36363636L, 0xa5a5a5a5L, 0x38383838L,
    0xbfbfbfbfL, 0x40404040L, 0xa3a3a3a3L, 0x9e9e9e9eL,
    0x81818181L, 0xf3f3f3f3L, 0xd7d7d7d7L, 0xfbfbfbfbL,
    0x7c7c7c7cL, 0xe3e3e3e3L, 0x39393939L, 0x82828282L,
    0x9b9b9b9bL, 0x2f2f2f2fL, 0xffffffffL, 0x87878787L,
    0x34343434L, 0x8e8e8e8eL, 0x43434343L, 0x44444444L,
    0xc4c4c4c4L, 0xdedededeL, 0xe9e9e9e9L, 0xcbcbcbcbL,
    0x54545454L, 0x7b7b7b7bL, 0x94949494L, 0x32323232L,
    0xa6a6a6a6L, 0xc2c2c2c2L, 0x23232323L, 0x3d3d3d3dL,
    0xeeeeeeeeL, 0x4c4c4c4cL, 0x95959595L, 0x0b0b0b0bL,
    0x42424242L, 0xfafafafaL, 0xc3c3c3c3L, 0x4e4e4e4eL,
    0x08080808L, 0x2e2e2e2eL, 0xa1a1a1a1L, 0x66666666L,
    0x28282828L, 0xd9d9d9d9L, 0x24242424L, 0xb2b2b2b2L,
    0x76767676L, 0x5b5b5b5bL, 0xa2a2a2a2L, 0x49494949L,
    0x6d6d6d6dL, 0x8b8b8b8bL, 0xd1d1d1d1L, 0x25252525L,
    0x72727272L, 0xf8f8f8f8L, 0xf6f6f6f6L, 0x64646464L,
    0x86868686L, 0x68686868L, 0x98989898L, 0x16161616L,
    0xd4d4d4d4L, 0xa4a4a4a4L, 0x5c5c5c5cL, 0xccccccccL,
    0x5d5d5d5dL, 0x65656565L, 0xb6b6b6b6L, 0x92929292L,
    0x6c6c6c6cL, 0x70707070L, 0x48484848L, 0x50505050L,
    0xfdfdfdfdL, 0xededededL, 0xb9b9b9b9L, 0xdadadadaL,
    0x5e5e5e5eL, 0x15151515L, 0x46464646L, 0x57575757L,
    0xa7a7a7a7L, 0x8d8d8d8dL, 0x9d9d9d9dL, 0x84848484L,
    0x90909090L, 0xd8d8d8d8L, 0xababababL, 0x00000000L,
    0x8c8c8c8cL, 0xbcbcbcbcL, 0xd3d3d3d3L, 0x0a0a0a0aL,
    0xf7f7f7f7L, 0xe4e4e4e4L, 0x58585858L, 0x05050505L,
    0xb8b8b8b8L, 0xb3b3b3b3L, 0x45454545L, 0x06060606L,
    0xd0d0d0d0L, 0x2c2c2c2cL, 0x1e1e1e1eL, 0x8f8f8f8fL,
    0xcacacacaL, 0x3f3f3f3fL, 0x0f0f0f0fL, 0x02020202L,
    0xc1c1c1c1L, 0xafafafafL, 0xbdbdbdbdL, 0x03030303L,
    0x01010101L, 0x13131313L, 0x8a8a8a8aL, 0x6b6b6b6bL,
    0x3a3a3a3aL, 0x91919191L, 0x11111111L, 0x41414141L,
    0x4f4f4f4fL, 0x67676767L, 0xdcdcdcdcL, 0xeaeaeaeaL,
    0x97979797L, 0xf2f2f2f2L, 0xcfcfcfcfL, 0xcecececeL,
    0xf0f0f0f0L, 0xb4b4b4b4L, 0xe6e6e6e6L, 0x73737373L,
    0x96969696L, 0xacacacacL, 0x74747474L, 0x22222222L,
    0xe7e7e7e7L, 0xadadadadL, 0x35353535L, 0x85858585L,
    0xe2e2e2e2L, 0xf9f9f9f9L, 0x37373737L, 0xe8e8e8e8L,
    0x1c1c1c1cL, 0x75757575L, 0xdfdfdfdfL, 0x6e6e6e6eL,
    0x47474747L, 0xf1f1f1f1L, 0x1a1a1a1aL, 0x71717171L,
    0x1d1d1d1dL, 0x29292929L, 0xc5c5c5c5L, 0x89898989L,
    0x6f6f6f6fL, 0xb7b7b7b7L, 0x62626262L, 0x0e0e0e0eL,
    0xaaaaaaaaL, 0x18181818L, 0xbebebebeL, 0x1b1b1b1bL,
    0xfcfcfcfcL, 0x56565656L, 0x3e3e3e3eL, 0x4b4b4b4bL,
    0xc6c6c6c6L, 0xd2d2d2d2L, 0x79797979L, 0x20202020L,
    0x9a9a9a9aL, 0xdbdbdbdbL, 0xc0c0c0c0L, 0xfefefefeL,
    0x78787878L, 0xcdcdcdcdL, 0x5a5a5a5aL, 0xf4f4f4f4L,
    0x1f1f1f1fL, 0xddddddddL, 0xa8a8a8a8L, 0x33333333L,
    0x88888888L, 0x07070707L, 0xc7c7c7c7L, 0x31313131L,
    0xb1b1b1b1L, 0x12121212L, 0x10101010L, 0x59595959L,
    0x27272727L, 0x80808080L, 0xececececL, 0x5f5f5f5fL,
    0x60606060L, 0x51515151L, 0x7f7f7f7fL, 0xa9a9a9a9L,
    0x19191919L, 0xb5b5b5b5L, 0x4a4a4a4aL, 0x0d0d0d0dL,
    0x2d2d2d2dL, 0xe5e5e5e5L, 0x7a7a7a7aL, 0x9f9f9f9fL,
    0x93939393L, 0xc9c9c9c9L, 0x9c9c9c9cL, 0xefefefefL,
    0xa0a0a0a0L, 0xe0e0e0e0L, 0x3b3b3b3bL, 0x4d4d4d4dL,
    0xaeaeaeaeL, 0x2a2a2a2aL, 0xf5f5f5f5L, 0xb0b0b0b0L,
    0xc8c8c8c8L, 0xebebebebL, 0xbbbbbbbbL, 0x3c3c3c3cL,
    0x83838383L, 0x53535353L, 0x99999999L, 0x61616161L,
    0x17171717L, 0x2b2b2b2bL, 0x04040404L, 0x7e7e7e7eL,
    0xbabababaL, 0x77777777L, 0xd6d6d6d6L, 0x26262626L,
    0xe1e1e1e1L, 0x69696969L, 0x14141414L, 0x63636363L,
    0x55555555L, 0x21212121L, 0x0c0c0c0cL, 0x7d7d7d7dL,
]

rcon = [
    0x01000000, 0x02000000, 0x04000000, 0x08000000,
    0x10000000, 0x20000000, 0x40000000, 0x80000000,
    0x1B000000, 0x36000000,
    # 128-bit blocks, Rijndael never uses more than 10 rcon values
]

if len(struct.pack('L',0)) == 4:
    # 32bit
    def GETU32(x): return struct.unpack('>L', x)[0]
    def PUTU32(x): return struct.pack('>L', x)
else:
    # 64bit
    def GETU32(x): return struct.unpack('>I', x)[0]
    def PUTU32(x): return struct.pack('>I', x)


# Expand the cipher key into the encryption key schedule.
#
# @return the number of rounds for the given cipher key size.
def rijndaelSetupEncrypt(key, keybits):
    i = p = 0
    rk = [0]*RKLENGTH(keybits)
    rk[0] = GETU32(key[0:4])
    rk[1] = GETU32(key[4:8])
    rk[2] = GETU32(key[8:12])
    rk[3] = GETU32(key[12:16])
    if keybits == 128:
        while 1:
            temp = rk[p+3]
            rk[p+4] = (rk[p+0] ^
                       (Te4[(temp >> 16) & 0xff] & 0xff000000) ^
                       (Te4[(temp >>  8) & 0xff] & 0x00ff0000) ^
                       (Te4[(temp      ) & 0xff] & 0x0000ff00) ^
                       (Te4[(temp >> 24)       ] & 0x000000ff) ^
                       rcon[i])
            rk[p+5] = rk[p+1] ^ rk[p+4]
            rk[p+6] = rk[p+2] ^ rk[p+5]
            rk[p+7] = rk[p+3] ^ rk[p+6]
            i += 1
            if i == 10: return (rk, 10)
            p += 4

    rk[4] = GETU32(key[16:20])
    rk[5] = GETU32(key[20:24])
    if keybits == 192:
        while 1:
            temp = rk[p+5]
            rk[p+6] = (rk[p+0] ^
                       (Te4[(temp >> 16) & 0xff] & 0xff000000) ^
                       (Te4[(temp >>  8) & 0xff] & 0x00ff0000) ^
                       (Te4[(temp      ) & 0xff] & 0x0000ff00) ^
                       (Te4[(temp >> 24)       ] & 0x000000ff) ^
                       rcon[i])
            rk[p+7] = rk[p+1] ^ rk[p+6]
            rk[p+8] = rk[p+2] ^ rk[p+7]
            rk[p+9] = rk[p+3] ^ rk[p+8]
            i += 1
            if i == 8: return (rk, 12)
            rk[p+10] = rk[p+4] ^ rk[p+9]
            rk[p+11] = rk[p+5] ^ rk[p+10]
            p += 6

    rk[6] = GETU32(key[24:28])
    rk[7] = GETU32(key[28:32])
    if keybits == 256:
        while 1:
            temp = rk[p+7]
            rk[p+8] = (rk[p+0] ^
                       (Te4[(temp >> 16) & 0xff] & 0xff000000) ^
                       (Te4[(temp >>  8) & 0xff] & 0x00ff0000) ^
                       (Te4[(temp      ) & 0xff] & 0x0000ff00) ^
                       (Te4[(temp >> 24)       ] & 0x000000ff) ^
                       rcon[i])
            rk[p+9] = rk[p+1] ^ rk[p+8]
            rk[p+10] = rk[p+2] ^ rk[p+9]
            rk[p+11] = rk[p+3] ^ rk[p+10]
            i += 1
            if i == 7: return (rk, 14)
            temp = rk[p+11]
            rk[p+12] = (rk[p+4] ^
                        (Te4[(temp >> 24)       ] & 0xff000000) ^
                        (Te4[(temp >> 16) & 0xff] & 0x00ff0000) ^
                        (Te4[(temp >>  8) & 0xff] & 0x0000ff00) ^
                        (Te4[(temp      ) & 0xff] & 0x000000ff))
            rk[p+13] = rk[p+5] ^ rk[p+12]
            rk[p+14] = rk[p+6] ^ rk[p+13]
            rk[p+15] = rk[p+7] ^ rk[p+14]
            p += 8

    raise ValueError(keybits)


# Expand the cipher key into the decryption key schedule.
#
# @return the number of rounds for the given cipher key size.
def rijndaelSetupDecrypt(key, keybits):

    # expand the cipher key:
    (rk, nrounds) = rijndaelSetupEncrypt(key, keybits)
    # invert the order of the round keys:
    i = 0
    j = 4*nrounds
    while i < j:
        temp = rk[i    ]; rk[i    ] = rk[j    ]; rk[j    ] = temp
        temp = rk[i + 1]; rk[i + 1] = rk[j + 1]; rk[j + 1] = temp
        temp = rk[i + 2]; rk[i + 2] = rk[j + 2]; rk[j + 2] = temp
        temp = rk[i + 3]; rk[i + 3] = rk[j + 3]; rk[j + 3] = temp
        i += 4
        j -= 4
    # apply the inverse MixColumn transform to all round keys but the first and the last:
    p = 0
    for i in xrange(1, nrounds):
        p += 4
        rk[p+0] = (
          Td0[Te4[(rk[p+0] >> 24)       ] & 0xff] ^
          Td1[Te4[(rk[p+0] >> 16) & 0xff] & 0xff] ^
          Td2[Te4[(rk[p+0] >>  8) & 0xff] & 0xff] ^
          Td3[Te4[(rk[p+0]      ) & 0xff] & 0xff])
        rk[p+1] = (
          Td0[Te4[(rk[p+1] >> 24)       ] & 0xff] ^
          Td1[Te4[(rk[p+1] >> 16) & 0xff] & 0xff] ^
          Td2[Te4[(rk[p+1] >>  8) & 0xff] & 0xff] ^
          Td3[Te4[(rk[p+1]      ) & 0xff] & 0xff])
        rk[p+2] = (
          Td0[Te4[(rk[p+2] >> 24)       ] & 0xff] ^
          Td1[Te4[(rk[p+2] >> 16) & 0xff] & 0xff] ^
          Td2[Te4[(rk[p+2] >>  8) & 0xff] & 0xff] ^
          Td3[Te4[(rk[p+2]      ) & 0xff] & 0xff])
        rk[p+3] = (
          Td0[Te4[(rk[p+3] >> 24)       ] & 0xff] ^
          Td1[Te4[(rk[p+3] >> 16) & 0xff] & 0xff] ^
          Td2[Te4[(rk[p+3] >>  8) & 0xff] & 0xff] ^
          Td3[Te4[(rk[p+3]      ) & 0xff] & 0xff])

    return (rk, nrounds)


def rijndaelEncrypt(rk, nrounds, plaintext):
    assert len(plaintext) == 16

    # map byte array block to cipher state
    # and add initial round key:
    s0 = GETU32(plaintext[0:4]) ^ rk[0]
    s1 = GETU32(plaintext[4:8]) ^ rk[1]
    s2 = GETU32(plaintext[8:12]) ^ rk[2]
    s3 = GETU32(plaintext[12:16]) ^ rk[3]

    # nrounds - 1 full rounds:
    r = nrounds >> 1
    p = 0
    while 1:
        t0 = (
          Te0[(s0 >> 24)       ] ^
          Te1[(s1 >> 16) & 0xff] ^
          Te2[(s2 >>  8) & 0xff] ^
          Te3[(s3      ) & 0xff] ^
          rk[p+4])
        t1 = (
          Te0[(s1 >> 24)       ] ^
          Te1[(s2 >> 16) & 0xff] ^
          Te2[(s3 >>  8) & 0xff] ^
          Te3[(s0      ) & 0xff] ^
          rk[p+5])
        t2 = (
          Te0[(s2 >> 24)       ] ^
          Te1[(s3 >> 16) & 0xff] ^
          Te2[(s0 >>  8) & 0xff] ^
          Te3[(s1      ) & 0xff] ^
          rk[p+6])
        t3 = (
          Te0[(s3 >> 24)       ] ^
          Te1[(s0 >> 16) & 0xff] ^
          Te2[(s1 >>  8) & 0xff] ^
          Te3[(s2      ) & 0xff] ^
          rk[p+7])
        p += 8
        r -= 1
        if r == 0: break
        s0 = (
          Te0[(t0 >> 24)       ] ^
          Te1[(t1 >> 16) & 0xff] ^
          Te2[(t2 >>  8) & 0xff] ^
          Te3[(t3      ) & 0xff] ^
          rk[p+0])
        s1 = (
          Te0[(t1 >> 24)       ] ^
          Te1[(t2 >> 16) & 0xff] ^
          Te2[(t3 >>  8) & 0xff] ^
          Te3[(t0      ) & 0xff] ^
          rk[p+1])
        s2 = (
          Te0[(t2 >> 24)       ] ^
          Te1[(t3 >> 16) & 0xff] ^
          Te2[(t0 >>  8) & 0xff] ^
          Te3[(t1      ) & 0xff] ^
          rk[p+2])
        s3 = (
          Te0[(t3 >> 24)       ] ^
          Te1[(t0 >> 16) & 0xff] ^
          Te2[(t1 >>  8) & 0xff] ^
          Te3[(t2      ) & 0xff] ^
          rk[p+3])

    ciphertext = ''

    # apply last round and
    # map cipher state to byte array block:
    s0 = (
      (Te4[(t0 >> 24)       ] & 0xff000000) ^
      (Te4[(t1 >> 16) & 0xff] & 0x00ff0000) ^
      (Te4[(t2 >>  8) & 0xff] & 0x0000ff00) ^
      (Te4[(t3      ) & 0xff] & 0x000000ff) ^
      rk[p+0])
    ciphertext += PUTU32(s0)
    s1 = (
      (Te4[(t1 >> 24)       ] & 0xff000000) ^
      (Te4[(t2 >> 16) & 0xff] & 0x00ff0000) ^
      (Te4[(t3 >>  8) & 0xff] & 0x0000ff00) ^
      (Te4[(t0      ) & 0xff] & 0x000000ff) ^
      rk[p+1])
    ciphertext += PUTU32(s1)
    s2 = (
      (Te4[(t2 >> 24)       ] & 0xff000000) ^
      (Te4[(t3 >> 16) & 0xff] & 0x00ff0000) ^
      (Te4[(t0 >>  8) & 0xff] & 0x0000ff00) ^
      (Te4[(t1      ) & 0xff] & 0x000000ff) ^
      rk[p+2])
    ciphertext += PUTU32(s2)
    s3 = (
      (Te4[(t3 >> 24)       ] & 0xff000000) ^
      (Te4[(t0 >> 16) & 0xff] & 0x00ff0000) ^
      (Te4[(t1 >>  8) & 0xff] & 0x0000ff00) ^
      (Te4[(t2      ) & 0xff] & 0x000000ff) ^
      rk[p+3])
    ciphertext += PUTU32(s3)

    assert len(ciphertext) == 16
    return ciphertext


def rijndaelDecrypt(rk, nrounds, ciphertext):
    assert len(ciphertext) == 16

    # map byte array block to cipher state
    # and add initial round key:
    s0 = GETU32(ciphertext[0:4]) ^ rk[0]
    s1 = GETU32(ciphertext[4:8]) ^ rk[1]
    s2 = GETU32(ciphertext[8:12]) ^ rk[2]
    s3 = GETU32(ciphertext[12:16]) ^ rk[3]

    # nrounds - 1 full rounds:
    r = nrounds >> 1
    p = 0
    while 1:
        t0 = (
          Td0[(s0 >> 24)       ] ^
          Td1[(s3 >> 16) & 0xff] ^
          Td2[(s2 >>  8) & 0xff] ^
          Td3[(s1      ) & 0xff] ^
          rk[p+4])
        t1 = (
          Td0[(s1 >> 24)       ] ^
          Td1[(s0 >> 16) & 0xff] ^
          Td2[(s3 >>  8) & 0xff] ^
          Td3[(s2      ) & 0xff] ^
          rk[p+5])
        t2 = (
          Td0[(s2 >> 24)       ] ^
          Td1[(s1 >> 16) & 0xff] ^
          Td2[(s0 >>  8) & 0xff] ^
          Td3[(s3      ) & 0xff] ^
          rk[p+6])
        t3 = (
          Td0[(s3 >> 24)       ] ^
          Td1[(s2 >> 16) & 0xff] ^
          Td2[(s1 >>  8) & 0xff] ^
          Td3[(s0      ) & 0xff] ^
          rk[p+7])
        p += 8
        r -= 1
        if r == 0: break
        s0 = (
          Td0[(t0 >> 24)       ] ^
          Td1[(t3 >> 16) & 0xff] ^
          Td2[(t2 >>  8) & 0xff] ^
          Td3[(t1      ) & 0xff] ^
          rk[p+0])
        s1 = (
          Td0[(t1 >> 24)       ] ^
          Td1[(t0 >> 16) & 0xff] ^
          Td2[(t3 >>  8) & 0xff] ^
          Td3[(t2      ) & 0xff] ^
          rk[p+1])
        s2 = (
          Td0[(t2 >> 24)       ] ^
          Td1[(t1 >> 16) & 0xff] ^
          Td2[(t0 >>  8) & 0xff] ^
          Td3[(t3      ) & 0xff] ^
          rk[p+2])
        s3 = (
          Td0[(t3 >> 24)       ] ^
          Td1[(t2 >> 16) & 0xff] ^
          Td2[(t1 >>  8) & 0xff] ^
          Td3[(t0      ) & 0xff] ^
          rk[p+3])

    plaintext = ''

    # apply last round and
    # map cipher state to byte array block:
    s0 = (
      (Td4[(t0 >> 24)       ] & 0xff000000) ^
      (Td4[(t3 >> 16) & 0xff] & 0x00ff0000) ^
      (Td4[(t2 >>  8) & 0xff] & 0x0000ff00) ^
      (Td4[(t1      ) & 0xff] & 0x000000ff) ^
      rk[p+0])
    plaintext += PUTU32(s0)
    s1 = (
      (Td4[(t1 >> 24)       ] & 0xff000000) ^
      (Td4[(t0 >> 16) & 0xff] & 0x00ff0000) ^
      (Td4[(t3 >>  8) & 0xff] & 0x0000ff00) ^
      (Td4[(t2      ) & 0xff] & 0x000000ff) ^
      rk[p+1])
    plaintext += PUTU32(s1)
    s2 = (
      (Td4[(t2 >> 24)       ] & 0xff000000) ^
      (Td4[(t1 >> 16) & 0xff] & 0x00ff0000) ^
      (Td4[(t0 >>  8) & 0xff] & 0x0000ff00) ^
      (Td4[(t3      ) & 0xff] & 0x000000ff) ^
      rk[p+2])
    plaintext += PUTU32(s2)
    s3 = (
      (Td4[(t3 >> 24)       ] & 0xff000000) ^
      (Td4[(t2 >> 16) & 0xff] & 0x00ff0000) ^
      (Td4[(t1 >>  8) & 0xff] & 0x0000ff00) ^
      (Td4[(t0      ) & 0xff] & 0x000000ff) ^
      rk[p+3])
    plaintext += PUTU32(s3)

    assert len(plaintext) == 16
    return plaintext


# decrypt(key, fin, fout, keybits=256)
class RijndaelDecryptor(object):

    """
    >>> key = '00010203050607080a0b0c0d0f101112'.decode('hex')
    >>> ciphertext = 'd8f532538289ef7d06b506a4fd5be9c9'.decode('hex')
    >>> RijndaelDecryptor(key, 128).decrypt(ciphertext).encode('hex')
    '506812a45f08c889b97f5980038b8359'
    """

    def __init__(self, key, keybits=256):
        assert len(key) == KEYLENGTH(keybits)
        (self.rk, self.nrounds) = rijndaelSetupDecrypt(key, keybits)
        assert len(self.rk) == RKLENGTH(keybits)
        assert self.nrounds == NROUNDS(keybits)
        return

    def decrypt(self, ciphertext):
        assert len(ciphertext) == 16
        return rijndaelDecrypt(self.rk, self.nrounds, ciphertext)


# encrypt(key, fin, fout, keybits=256)
class RijndaelEncryptor(object):

    """
    >>> key = '00010203050607080a0b0c0d0f101112'.decode('hex')
    >>> plaintext = '506812a45f08c889b97f5980038b8359'.decode('hex')
    >>> RijndaelEncryptor(key, 128).encrypt(plaintext).encode('hex')
    'd8f532538289ef7d06b506a4fd5be9c9'
    """

    def __init__(self, key, keybits=256):
        assert len(key) == KEYLENGTH(keybits)
        (self.rk, self.nrounds) = rijndaelSetupEncrypt(key, keybits)
        assert len(self.rk) == RKLENGTH(keybits)
        assert self.nrounds == NROUNDS(keybits)
        return

    def encrypt(self, plaintext):
        assert len(plaintext) == 16
        return rijndaelEncrypt(self.rk, self.nrounds, plaintext)


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = runlength
#!/usr/bin/env python
#
# RunLength decoder (Adobe version) implementation based on PDF Reference
# version 1.4 section 3.3.4.
#
#  * public domain *
#

def rldecode(data):
    """
    RunLength decoder (Adobe version) implementation based on PDF Reference
    version 1.4 section 3.3.4:
        The RunLengthDecode filter decodes data that has been encoded in a
        simple byte-oriented format based on run length. The encoded data
        is a sequence of runs, where each run consists of a length byte
        followed by 1 to 128 bytes of data. If the length byte is in the
        range 0 to 127, the following length + 1 (1 to 128) bytes are
        copied literally during decompression. If length is in the range
        129 to 255, the following single byte is to be copied 257 - length
        (2 to 128) times during decompression. A length value of 128
        denotes EOD.
    >>> s = "\x05123456\xfa7\x04abcde\x80junk"
    >>> rldecode(s)
    '1234567777777abcde'
    """
    decoded = []
    i = 0
    while i < len(data):
        #print "data[%d]=:%d:" % (i,ord(data[i]))
        length = ord(data[i])
        if length == 128:
            break
        if length >= 0 and length < 128:
            run = data[i+1:(i+1)+(length+1)]
            #print "length=%d, run=%s" % (length+1,run)
            decoded.append(run)
            i = (i+1) + (length+1)
        if length > 128:
            run = data[i+1]*(257-length)
            #print "length=%d, run=%s" % (257-length,run)
            decoded.append(run)
            i = (i+1) + 1
    return ''.join(decoded)


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
"""
Miscellaneous Routines.
"""
import struct
from sys import maxint as INF


##  PNG Predictor
##
def apply_png_predictor(pred, colors, columns, bitspercomponent, data):
    if bitspercomponent != 8:
        # unsupported
        raise ValueError(bitspercomponent)
    nbytes = colors*columns*bitspercomponent//8
    i = 0
    buf = ''
    line0 = '\x00' * columns
    for i in xrange(0, len(data), nbytes+1):
        ft = data[i]
        i += 1
        line1 = data[i:i+nbytes]
        line2 = ''
        if ft == '\x00':
            # PNG none
            line2 += line1
        elif ft == '\x01':
            # PNG sub (UNTESTED)
            c = 0
            for b in line1:
                c = (c+ord(b)) & 255
                line2 += chr(c)
        elif ft == '\x02':
            # PNG up
            for (a, b) in zip(line0, line1):
                c = (ord(a)+ord(b)) & 255
                line2 += chr(c)
        elif ft == '\x03':
            # PNG average (UNTESTED)
            c = 0
            for (a, b) in zip(line0, line1):
                c = ((c+ord(a)+ord(b))//2) & 255
                line2 += chr(c)
        else:
            # unsupported
            raise ValueError(ft)
        buf += line2
        line0 = line2
    return buf


##  Matrix operations
##
MATRIX_IDENTITY = (1, 0, 0, 1, 0, 0)


def mult_matrix((a1, b1, c1, d1, e1, f1), (a0, b0, c0, d0, e0, f0)):
    """Returns the multiplication of two matrices."""
    return (a0*a1+c0*b1,    b0*a1+d0*b1,
            a0*c1+c0*d1,    b0*c1+d0*d1,
            a0*e1+c0*f1+e0, b0*e1+d0*f1+f0)


def translate_matrix((a, b, c, d, e, f), (x, y)):
    """Translates a matrix by (x, y)."""
    return (a, b, c, d, x*a+y*c+e, x*b+y*d+f)


def apply_matrix_pt((a, b, c, d, e, f), (x, y)):
    """Applies a matrix to a point."""
    return (a*x+c*y+e, b*x+d*y+f)


def apply_matrix_norm((a, b, c, d, e, f), (p, q)):
    """Equivalent to apply_matrix_pt(M, (p,q)) - apply_matrix_pt(M, (0,0))"""
    return (a*p+c*q, b*p+d*q)


##  Utility functions
##

# isnumber
def isnumber(x):
    return isinstance(x, (int, long, float))

# uniq
def uniq(objs):
    """Eliminates duplicated elements."""
    done = set()
    for obj in objs:
        if obj in done:
            continue
        done.add(obj)
        yield obj
    return


# csort
def csort(objs, key=lambda x: x):
    """Order-preserving sorting function."""
    idxs = dict((obj, i) for (i, obj) in enumerate(objs))
    return sorted(objs, key=lambda obj: (key(obj), idxs[obj]))


# fsplit
def fsplit(pred, objs):
    """Split a list into two classes according to the predicate."""
    t = []
    f = []
    for obj in objs:
        if pred(obj):
            t.append(obj)
        else:
            f.append(obj)
    return (t, f)


# drange
def drange(v0, v1, d):
    """Returns a discrete range."""
    assert v0 < v1
    return xrange(int(v0)//d, int(v1+d)//d)


# get_bound
def get_bound(pts):
    """Compute a minimal rectangle that covers all the points."""
    (x0, y0, x1, y1) = (INF, INF, -INF, -INF)
    for (x, y) in pts:
        x0 = min(x0, x)
        y0 = min(y0, y)
        x1 = max(x1, x)
        y1 = max(y1, y)
    return (x0, y0, x1, y1)


# pick
def pick(seq, func, maxobj=None):
    """Picks the object obj where func(obj) has the highest value."""
    maxscore = None
    for obj in seq:
        score = func(obj)
        if maxscore is None or maxscore < score:
            (maxscore, maxobj) = (score, obj)
    return maxobj


# choplist
def choplist(n, seq):
    """Groups every n elements of the list."""
    r = []
    for x in seq:
        r.append(x)
        if len(r) == n:
            yield tuple(r)
            r = []
    return


# nunpack
def nunpack(s, default=0):
    """Unpacks 1 to 4 byte integers (big endian)."""
    l = len(s)
    if not l:
        return default
    elif l == 1:
        return ord(s)
    elif l == 2:
        return struct.unpack('>H', s)[0]
    elif l == 3:
        return struct.unpack('>L', '\x00'+s)[0]
    elif l == 4:
        return struct.unpack('>L', s)[0]
    else:
        raise TypeError('invalid length: %d' % l)


# decode_text
PDFDocEncoding = ''.join(unichr(x) for x in (
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007,
    0x0008, 0x0009, 0x000a, 0x000b, 0x000c, 0x000d, 0x000e, 0x000f,
    0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0017, 0x0017,
    0x02d8, 0x02c7, 0x02c6, 0x02d9, 0x02dd, 0x02db, 0x02da, 0x02dc,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f,
    0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
    0x0060, 0x0061, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067,
    0x0068, 0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x006f,
    0x0070, 0x0071, 0x0072, 0x0073, 0x0074, 0x0075, 0x0076, 0x0077,
    0x0078, 0x0079, 0x007a, 0x007b, 0x007c, 0x007d, 0x007e, 0x0000,
    0x2022, 0x2020, 0x2021, 0x2026, 0x2014, 0x2013, 0x0192, 0x2044,
    0x2039, 0x203a, 0x2212, 0x2030, 0x201e, 0x201c, 0x201d, 0x2018,
    0x2019, 0x201a, 0x2122, 0xfb01, 0xfb02, 0x0141, 0x0152, 0x0160,
    0x0178, 0x017d, 0x0131, 0x0142, 0x0153, 0x0161, 0x017e, 0x0000,
    0x20ac, 0x00a1, 0x00a2, 0x00a3, 0x00a4, 0x00a5, 0x00a6, 0x00a7,
    0x00a8, 0x00a9, 0x00aa, 0x00ab, 0x00ac, 0x0000, 0x00ae, 0x00af,
    0x00b0, 0x00b1, 0x00b2, 0x00b3, 0x00b4, 0x00b5, 0x00b6, 0x00b7,
    0x00b8, 0x00b9, 0x00ba, 0x00bb, 0x00bc, 0x00bd, 0x00be, 0x00bf,
    0x00c0, 0x00c1, 0x00c2, 0x00c3, 0x00c4, 0x00c5, 0x00c6, 0x00c7,
    0x00c8, 0x00c9, 0x00ca, 0x00cb, 0x00cc, 0x00cd, 0x00ce, 0x00cf,
    0x00d0, 0x00d1, 0x00d2, 0x00d3, 0x00d4, 0x00d5, 0x00d6, 0x00d7,
    0x00d8, 0x00d9, 0x00da, 0x00db, 0x00dc, 0x00dd, 0x00de, 0x00df,
    0x00e0, 0x00e1, 0x00e2, 0x00e3, 0x00e4, 0x00e5, 0x00e6, 0x00e7,
    0x00e8, 0x00e9, 0x00ea, 0x00eb, 0x00ec, 0x00ed, 0x00ee, 0x00ef,
    0x00f0, 0x00f1, 0x00f2, 0x00f3, 0x00f4, 0x00f5, 0x00f6, 0x00f7,
    0x00f8, 0x00f9, 0x00fa, 0x00fb, 0x00fc, 0x00fd, 0x00fe, 0x00ff,
))


def decode_text(s):
    """Decodes a PDFDocEncoding string to Unicode."""
    if s.startswith('\xfe\xff'):
        return unicode(s[2:], 'utf-16be', 'ignore')
    else:
        return ''.join(PDFDocEncoding[ord(c)] for c in s)


# enc
def enc(x, codec='ascii'):
    """Encodes a string for SGML/XML/HTML"""
    x = x.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt;').replace('"', '&quot;')
    return x.encode(codec, 'xmlcharrefreplace')


def bbox2str((x0, y0, x1, y1)):
    return '%.3f,%.3f,%.3f,%.3f' % (x0, y0, x1, y1)


def matrix2str((a, b, c, d, e, f)):
    return '[%.2f,%.2f,%.2f,%.2f, (%.2f,%.2f)]' % (a, b, c, d, e, f)


##  Plane
##
##  A set-like data structure for objects placed on a plane.
##  Can efficiently find objects in a certain rectangular area.
##  It maintains two parallel lists of objects, each of
##  which is sorted by its x or y coordinate.
##
class Plane(object):

    def __init__(self, bbox, gridsize=50):
        self._objs = set()
        self._grid = {}
        self.gridsize = gridsize
        (self.x0, self.y0, self.x1, self.y1) = bbox
        return

    def __repr__(self):
        return ('<Plane objs=%r>' % list(self))

    def __iter__(self):
        return iter(self._objs)

    def __len__(self):
        return len(self._objs)

    def __contains__(self, obj):
        return obj in self._objs

    def _getrange(self, (x0, y0, x1, y1)):
        if (x1 <= self.x0 or self.x1 <= x0 or
            y1 <= self.y0 or self.y1 <= y0): return
        x0 = max(self.x0, x0)
        y0 = max(self.y0, y0)
        x1 = min(self.x1, x1)
        y1 = min(self.y1, y1)
        for y in drange(y0, y1, self.gridsize):
            for x in drange(x0, x1, self.gridsize):
                yield (x, y)
        return

    # extend(objs)
    def extend(self, objs):
        for obj in objs:
            self.add(obj)
        return

    # add(obj): place an object.
    def add(self, obj):
        for k in self._getrange((obj.x0, obj.y0, obj.x1, obj.y1)):
            if k not in self._grid:
                r = []
                self._grid[k] = r
            else:
                r = self._grid[k]
            r.append(obj)
        self._objs.add(obj)
        return

    # remove(obj): displace an object.
    def remove(self, obj):
        for k in self._getrange((obj.x0, obj.y0, obj.x1, obj.y1)):
            try:
                self._grid[k].remove(obj)
            except (KeyError, ValueError):
                pass
        self._objs.remove(obj)
        return

    # find(): finds objects that are in a certain area.
    def find(self, (x0, y0, x1, y1)):
        done = set()
        for k in self._getrange((x0, y0, x1, y1)):
            if k not in self._grid:
                continue
            for obj in self._grid[k]:
                if obj in done:
                    continue
                done.add(obj)
                if (obj.x1 <= x0 or x1 <= obj.x0 or
                    obj.y1 <= y0 or y1 <= obj.y0):
                    continue
                yield obj
        return

########NEW FILE########
__FILENAME__ = conv_afm
#!/usr/bin/env python
import sys
import fileinput

def main(argv):
    fonts = {}
    for line in fileinput.input():
        f = line.strip().split(' ')
        if not f: continue
        k = f[0]
        if k == 'FontName':
            fontname = f[1]
            props = {'FontName': fontname, 'Flags': 0}
            chars = {}
            fonts[fontname] = (props, chars)
        elif k == 'C':
            cid = int(f[1])
            if 0 <= cid and cid <= 255:
                width = int(f[4])
                chars[cid] = width
        elif k in ('CapHeight', 'XHeight', 'ItalicAngle',
                   'Ascender', 'Descender'):
            k = {'Ascender':'Ascent', 'Descender':'Descent'}.get(k,k)
            props[k] = float(f[1])
        elif k in ('FontName', 'FamilyName', 'Weight'):
            k = {'FamilyName':'FontFamily', 'Weight':'FontWeight'}.get(k,k)
            props[k] = f[1]
        elif k == 'IsFixedPitch':
            if f[1].lower() == 'true':
                props['Flags'] = 64
        elif k == 'FontBBox':
            props[k] = tuple(map(float, f[1:5]))
    print '# -*- python -*-'
    print 'FONT_METRICS = {'
    for (fontname,(props,chars)) in fonts.iteritems():
        print ' %r: %r,' % (fontname, (props,chars))
    print '}'
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conv_cmap
#!/usr/bin/env python
import sys
import cPickle as pickle


##  CMapConverter
##
class CMapConverter(object):

    def __init__(self, enc2codec={}):
        self.enc2codec = enc2codec
        self.code2cid = {} # {'cmapname': ...}
        self.is_vertical = {}
        self.cid2unichr_h = {} # {cid: unichr}
        self.cid2unichr_v = {} # {cid: unichr}
        return

    def get_encs(self):
        return self.code2cid.keys()

    def get_maps(self, enc):
        if enc.endswith('-H'):
            (hmapenc, vmapenc) = (enc, None)
        elif enc == 'H':
            (hmapenc, vmapenc) = ('H', 'V')
        else:
            (hmapenc, vmapenc) = (enc+'-H', enc+'-V')
        if hmapenc in self.code2cid:
            hmap = self.code2cid[hmapenc]
        else:
            hmap = {}
            self.code2cid[hmapenc] = hmap
        vmap = None
        if vmapenc:
            self.is_vertical[vmapenc] = True
            if vmapenc in self.code2cid:
                vmap = self.code2cid[vmapenc]
            else:
                vmap = {}
                self.code2cid[vmapenc] = vmap
        return (hmap, vmap)

    def load(self, fp):
        encs = None
        for line in fp:
            (line,_,_) = line.strip().partition('#')
            if not line: continue
            values = line.split('\t')
            if encs is None:
                assert values[0] == 'CID'
                encs = values
                continue

            def put(dmap, code, cid, force=False):
                for b in code[:-1]:
                    b = ord(b)
                    if b in dmap:
                        dmap = dmap[b]
                    else:
                        d = {}
                        dmap[b] = d
                        dmap = d
                b = ord(code[-1])
                if force or ((b not in dmap) or dmap[b] == cid):
                    dmap[b] = cid
                return

            def add(unimap, enc, code):
                try:
                    codec = self.enc2codec[enc]
                    c = code.decode(codec, 'strict')
                    if len(c) == 1:
                        if c not in unimap:
                            unimap[c] = 0
                        unimap[c] += 1
                except KeyError:
                    pass
                except UnicodeError:
                    pass
                return

            def pick(unimap):
                chars = unimap.items()
                chars.sort(key=(lambda (c,n):(n,-ord(c))), reverse=True)
                (c,_) = chars[0]
                return c

            cid = int(values[0])
            unimap_h = {}
            unimap_v = {}
            for (enc,value) in zip(encs, values):
                if enc == 'CID': continue
                if value == '*': continue

                # hcodes, vcodes: encoded bytes for each writing mode.
                hcodes = []
                vcodes = []
                for code in value.split(','):
                    vertical = code.endswith('v')
                    if vertical:
                        code = code[:-1]
                    try:
                        code = code.decode('hex')
                    except:
                        code = chr(int(code, 16))
                    if vertical:
                        vcodes.append(code)
                        add(unimap_v, enc, code)
                    else:
                        hcodes.append(code)
                        add(unimap_h, enc, code)
                # add cid to each map.
                (hmap, vmap) = self.get_maps(enc)
                if vcodes:
                    assert vmap is not None
                    for code in vcodes:
                        put(vmap, code, cid, True)
                    for code in hcodes:
                        put(hmap, code, cid, True)
                else:
                    for code in hcodes:
                        put(hmap, code, cid)
                        put(vmap, code, cid)

            # Determine the "most popular" candidate.
            if unimap_h:
                self.cid2unichr_h[cid] = pick(unimap_h)
            if unimap_v or unimap_h:
                self.cid2unichr_v[cid] = pick(unimap_v or unimap_h)

        return

    def dump_cmap(self, fp, enc):
        data = dict(
            IS_VERTICAL=self.is_vertical.get(enc, False),
            CODE2CID=self.code2cid.get(enc),
        )
        fp.write(pickle.dumps(data))
        return

    def dump_unicodemap(self, fp):
        data = dict(
            CID2UNICHR_H=self.cid2unichr_h,
            CID2UNICHR_V=self.cid2unichr_v,
        )
        fp.write(pickle.dumps(data))
        return

# main
def main(argv):
    import getopt
    import gzip
    import os.path

    def usage():
        print 'usage: %s [-c enc=codec] output_dir regname [cid2code.txt ...]' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'c:')
    except getopt.GetoptError:
        return usage()
    enc2codec = {}
    for (k, v) in opts:
        if k == '-c':
            (enc,_,codec) = v.partition('=')
            enc2codec[enc] = codec
    if not args: return usage()
    outdir = args.pop(0)
    if not args: return usage()
    regname = args.pop(0)

    converter = CMapConverter(enc2codec)
    for path in args:
        print >>sys.stderr, 'reading: %r...' % path
        fp = file(path)
        converter.load(fp)
        fp.close()

    for enc in converter.get_encs():
        fname = '%s.pickle.gz' % enc
        path = os.path.join(outdir, fname)
        print >>sys.stderr, 'writing: %r...' % path
        fp = gzip.open(path, 'wb')
        converter.dump_cmap(fp, enc)
        fp.close()

    fname = 'to-unicode-%s.pickle.gz' % regname
    path = os.path.join(outdir, fname)
    print >>sys.stderr, 'writing: %r...' % path
    fp = gzip.open(path, 'wb')
    converter.dump_unicodemap(fp)
    fp.close()
    return

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conv_glyphlist
#!/usr/bin/env python
import sys
import fileinput

def main(argv):
    state = 0
    for line in fileinput.input():
        line = line.strip()
        if not line or line.startswith('#'):
            if state == 1:
                state = 2
                print '}'
                print
            print line
            continue
        if state == 0:
            print
            print 'glyphname2unicode = {'
            state = 1
        (name,x) = line.split(';')
        codes = x.split(' ')
        print ' %r: u\'%s\',' % (name, ''.join( '\\u%s' % code for code in codes ))

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = dumppdf
#!/usr/bin/env python
#
# dumppdf.py - dump pdf contents in XML format.
#
#  usage: dumppdf.py [options] [files ...]
#  options:
#    -i objid : object id
#
import sys, os.path, re
from pdfminer.psparser import PSKeyword, PSLiteral, LIT
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument, PDFNoOutlines
from pdfminer.pdftypes import PDFObjectNotFound, PDFValueError
from pdfminer.pdftypes import PDFStream, PDFObjRef, resolve1, stream_value
from pdfminer.pdfpage import PDFPage
from pdfminer.utils import isnumber


ESC_PAT = re.compile(r'[\000-\037&<>()"\042\047\134\177-\377]')
def e(s):
    return ESC_PAT.sub(lambda m:'&#%d;' % ord(m.group(0)), s)


# dumpxml
def dumpxml(out, obj, codec=None):
    if obj is None:
        out.write('<null />')
        return

    if isinstance(obj, dict):
        out.write('<dict size="%d">\n' % len(obj))
        for (k,v) in obj.iteritems():
            out.write('<key>%s</key>\n' % k)
            out.write('<value>')
            dumpxml(out, v)
            out.write('</value>\n')
        out.write('</dict>')
        return

    if isinstance(obj, list):
        out.write('<list size="%d">\n' % len(obj))
        for v in obj:
            dumpxml(out, v)
            out.write('\n')
        out.write('</list>')
        return

    if isinstance(obj, str):
        out.write('<string size="%d">%s</string>' % (len(obj), e(obj)))
        return

    if isinstance(obj, PDFStream):
        if codec == 'raw':
            out.write(obj.get_rawdata())
        elif codec == 'binary':
            out.write(obj.get_data())
        else:
            out.write('<stream>\n<props>\n')
            dumpxml(out, obj.attrs)
            out.write('\n</props>\n')
            if codec == 'text':
                data = obj.get_data()
                out.write('<data size="%d">%s</data>\n' % (len(data), e(data)))
            out.write('</stream>')
        return

    if isinstance(obj, PDFObjRef):
        out.write('<ref id="%d" />' % obj.objid)
        return

    if isinstance(obj, PSKeyword):
        out.write('<keyword>%s</keyword>' % obj.name)
        return

    if isinstance(obj, PSLiteral):
        out.write('<literal>%s</literal>' % obj.name)
        return

    if isnumber(obj):
        out.write('<number>%s</number>' % obj)
        return

    raise TypeError(obj)

# dumptrailers
def dumptrailers(out, doc):
    for xref in doc.xrefs:
        out.write('<trailer>\n')
        dumpxml(out, xref.trailer)
        out.write('\n</trailer>\n\n')
    return

# dumpallobjs
def dumpallobjs(out, doc, codec=None):
    visited = set()
    out.write('<pdf>')
    for xref in doc.xrefs:
        for objid in xref.get_objids():
            if objid in visited: continue
            visited.add(objid)
            try:
                obj = doc.getobj(objid)
                if obj is None: continue
                out.write('<object id="%d">\n' % objid)
                dumpxml(out, obj, codec=codec)
                out.write('\n</object>\n\n')
            except PDFObjectNotFound, e:
                print >>sys.stderr, 'not found: %r' % e
    dumptrailers(out, doc)
    out.write('</pdf>')
    return

# dumpoutline
def dumpoutline(outfp, fname, objids, pagenos, password='',
                dumpall=False, codec=None, extractdir=None):
    fp = file(fname, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument(parser, password)
    pages = dict( (page.pageid, pageno) for (pageno,page)
                  in enumerate(PDFPage.create_pages(doc)) )
    def resolve_dest(dest):
        if isinstance(dest, str):
            dest = resolve1(doc.get_dest(dest))
        elif isinstance(dest, PSLiteral):
            dest = resolve1(doc.get_dest(dest.name))
        if isinstance(dest, dict):
            dest = dest['D']
        return dest
    try:
        outlines = doc.get_outlines()
        outfp.write('<outlines>\n')
        for (level,title,dest,a,se) in outlines:
            pageno = None
            if dest:
                dest = resolve_dest(dest)
                pageno = pages[dest[0].objid]
            elif a:
                action = a.resolve()
                if isinstance(action, dict):
                    subtype = action.get('S')
                    if subtype and repr(subtype) == '/GoTo' and action.get('D'):
                        dest = resolve_dest(action['D'])
                        pageno = pages[dest[0].objid]
            s = e(title).encode('utf-8', 'xmlcharrefreplace')
            outfp.write('<outline level="%r" title="%s">\n' % (level, s))
            if dest is not None:
                outfp.write('<dest>')
                dumpxml(outfp, dest)
                outfp.write('</dest>\n')
            if pageno is not None:
                outfp.write('<pageno>%r</pageno>\n' % pageno)
            outfp.write('</outline>\n')
        outfp.write('</outlines>\n')
    except PDFNoOutlines:
        pass
    parser.close()
    fp.close()
    return

# extractembedded
LITERAL_FILESPEC = LIT('Filespec')
LITERAL_EMBEDDEDFILE = LIT('EmbeddedFile')
def extractembedded(outfp, fname, objids, pagenos, password='',
                    dumpall=False, codec=None, extractdir=None):
    def extract1(obj):
        filename = os.path.basename(obj['UF'] or obj['F'])
        fileref = obj['EF']['F']
        fileobj = doc.getobj(fileref.objid)
        if not isinstance(fileobj, PDFStream):
            raise PDFValueError(
                'unable to process PDF: reference for %r is not a PDFStream' %
                (filename))
        if fileobj.get('Type') is not LITERAL_EMBEDDEDFILE:
            raise PDFValueError(
                'unable to process PDF: reference for %r is not an EmbeddedFile' %
                (filename))
        path = os.path.join(extractdir, filename)
        if os.path.exists(path):
            raise IOError('file exists: %r' % path)
        print >>sys.stderr, 'extracting: %r' % path
        out = file(path, 'wb')
        out.write(fileobj.get_data())
        out.close()
        return

    fp = file(fname, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument(parser, password)
    for xref in doc.xrefs:
        for objid in xref.get_objids():
            obj = doc.getobj(objid)
            if isinstance(obj, dict) and obj.get('Type') is LITERAL_FILESPEC:
                extract1(obj)
    return

# dumppdf
def dumppdf(outfp, fname, objids, pagenos, password='',
            dumpall=False, codec=None, extractdir=None):
    fp = file(fname, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument(parser, password)
    if objids:
        for objid in objids:
            obj = doc.getobj(objid)
            dumpxml(outfp, obj, codec=codec)
    if pagenos:
        for (pageno,page) in enumerate(PDFPage.create_pages(doc)):
            if pageno in pagenos:
                if codec:
                    for obj in page.contents:
                        obj = stream_value(obj)
                        dumpxml(outfp, obj, codec=codec)
                else:
                    dumpxml(outfp, page.attrs)
    if dumpall:
        dumpallobjs(outfp, doc, codec=codec)
    if (not objids) and (not pagenos) and (not dumpall):
        dumptrailers(outfp, doc)
    fp.close()
    if codec not in ('raw','binary'):
        outfp.write('\n')
    return


# main
def main(argv):
    import getopt
    def usage():
        print 'usage: %s [-d] [-a] [-p pageid] [-P password] [-r|-b|-t] [-T] [-E directory] [-i objid] file ...' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dap:P:rbtTE:i:')
    except getopt.GetoptError:
        return usage()
    if not args: return usage()
    debug = 0
    objids = []
    pagenos = set()
    codec = None
    password = ''
    dumpall = False
    proc = dumppdf
    outfp = sys.stdout
    extractdir = None
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-o': outfp = file(v, 'wb')
        elif k == '-i': objids.extend( int(x) for x in v.split(',') )
        elif k == '-p': pagenos.update( int(x)-1 for x in v.split(',') )
        elif k == '-P': password = v
        elif k == '-a': dumpall = True
        elif k == '-r': codec = 'raw'
        elif k == '-b': codec = 'binary'
        elif k == '-t': codec = 'text'
        elif k == '-T': proc = dumpoutline
        elif k == '-E':
            extractdir = v
            proc = extractembedded
    #
    PDFDocument.debug = debug
    PDFParser.debug = debug
    #
    for fname in args:
        proc(outfp, fname, objids, pagenos, password=password,
             dumpall=dumpall, codec=codec, extractdir=extractdir)
    return

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = latin2ascii
#!/usr/bin/env python
#
#  latin2ascii.py - converts latin1 characters into ascii.
#

import sys

""" Mappings from Latin-1 characters to ASCII.

This is an in-house mapping table for some Latin-1 characters
(acutes, umlauts, etc.) to ASCII strings.
"""

LATIN2ASCII = {
  #0x00a0: '',
  #0x00a7: '',

  # iso-8859-1
  0x00c0: 'A`',
  0x00c1: "A'",
  0x00c2: 'A^',
  0x00c3: 'A~',
  0x00c4: 'A:',
  0x00c5: 'A%',
  0x00c6: 'AE',
  0x00c7: 'C,',
  0x00c8: 'E`',
  0x00c9: "E'",
  0x00ca: 'E^',
  0x00cb: 'E:',
  0x00cc: 'I`',
  0x00cd: "I'",
  0x00ce: 'I^',
  0x00cf: 'I:',
  0x00d0: "D'",
  0x00d1: 'N~',
  0x00d2: 'O`',
  0x00d3: "O'",
  0x00d4: 'O^',
  0x00d5: 'O~',
  0x00d6: 'O:',
  0x00d8: 'O/',
  0x00d9: 'U`',
  0x00da: "U'",
  0x00db: 'U~',
  0x00dc: 'U:',
  0x00dd: "Y'",
  0x00df: 'ss',

  0x00e0: 'a`',
  0x00e1: "a'",
  0x00e2: 'a^',
  0x00e3: 'a~',
  0x00e4: 'a:',
  0x00e5: 'a%',
  0x00e6: 'ae',
  0x00e7: 'c,',
  0x00e8: 'e`',
  0x00e9: "e'",
  0x00ea: 'e^',
  0x00eb: 'e:',
  0x00ec: 'i`',
  0x00ed: "i'",
  0x00ee: 'i^',
  0x00ef: 'i:',
  0x00f0: "d'",
  0x00f1: 'n~',
  0x00f2: 'o`',
  0x00f3: "o'",
  0x00f4: 'o^',
  0x00f5: 'o~',
  0x00f6: 'o:',
  0x00f8: 'o/',
  0x00f9: 'o`',
  0x00fa: "u'",
  0x00fb: 'u~',
  0x00fc: 'u:',
  0x00fd: "y'",
  0x00ff: 'y:',

  # Ligatures
  0x0152: 'OE',
  0x0153: 'oe',
  0x0132: 'IJ',
  0x0133: 'ij',
  0x1d6b: 'ue',
  0xfb00: 'ff',
  0xfb01: 'fi',
  0xfb02: 'fl',
  0xfb03: 'ffi',
  0xfb04: 'ffl',
  0xfb05: 'ft',
  0xfb06: 'st',

  # Symbols
  #0x2013: '',
  0x2014: '--',
  0x2015: '||',
  0x2018: '`',
  0x2019: "'",
  0x201c: '``',
  0x201d: "''",
  #0x2022: '',
  #0x2212: '',

}

def latin2ascii(s):
    return ''.join( LATIN2ASCII.get(ord(c),c) for c in s )


def main(argv):
    import getopt, fileinput
    def usage():
        print 'usage: %s [-c codec] file ...' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'c')
    except getopt.GetoptError:
        return usage()
    if not args: return usage()
    codec = 'utf-8'
    for (k, v) in opts:
        if k == '-c': codec = v
    for line in fileinput.input(args):
        line = latin2ascii(unicode(line, codec, 'ignore'))
        sys.stdout.write(line.encode('ascii', 'replace'))
    return

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = pdf2txt
#!/usr/bin/env python
import sys
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams
from pdfminer.image import ImageWriter

# main
def main(argv):
    import getopt
    def usage():
        print ('usage: %s [-d] [-p pagenos] [-m maxpages] [-P password] [-o output]'
               ' [-C] [-n] [-A] [-V] [-M char_margin] [-L line_margin] [-W word_margin]'
               ' [-F boxes_flow] [-Y layout_mode] [-O output_dir] [-R rotation]'
               ' [-t text|html|xml|tag] [-c codec] [-s scale]'
               ' file ...' % argv[0])
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dp:m:P:o:CnAVM:L:W:F:Y:O:R:t:c:s:')
    except getopt.GetoptError:
        return usage()
    if not args: return usage()
    # debug option
    debug = 0
    # input option
    password = ''
    pagenos = set()
    maxpages = 0
    # output option
    outfile = None
    outtype = None
    imagewriter = None
    rotation = 0
    layoutmode = 'normal'
    codec = 'utf-8'
    pageno = 1
    scale = 1
    caching = True
    showpageno = True
    laparams = LAParams()
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-p': pagenos.update( int(x)-1 for x in v.split(',') )
        elif k == '-m': maxpages = int(v)
        elif k == '-P': password = v
        elif k == '-o': outfile = v
        elif k == '-C': caching = False
        elif k == '-n': laparams = None
        elif k == '-A': laparams.all_texts = True
        elif k == '-V': laparams.detect_vertical = True
        elif k == '-M': laparams.char_margin = float(v)
        elif k == '-L': laparams.line_margin = float(v)
        elif k == '-W': laparams.word_margin = float(v)
        elif k == '-F': laparams.boxes_flow = float(v)
        elif k == '-Y': layoutmode = v
        elif k == '-O': imagewriter = ImageWriter(v)
        elif k == '-R': rotation = int(v)
        elif k == '-t': outtype = v
        elif k == '-c': codec = v
        elif k == '-s': scale = float(v)
    #
    PDFDocument.debug = debug
    PDFParser.debug = debug
    CMapDB.debug = debug
    PDFResourceManager.debug = debug
    PDFPageInterpreter.debug = debug
    PDFDevice.debug = debug
    #
    rsrcmgr = PDFResourceManager(caching=caching)
    if not outtype:
        outtype = 'text'
        if outfile:
            if outfile.endswith('.htm') or outfile.endswith('.html'):
                outtype = 'html'
            elif outfile.endswith('.xml'):
                outtype = 'xml'
            elif outfile.endswith('.tag'):
                outtype = 'tag'
    if outfile:
        outfp = file(outfile, 'w')
    else:
        outfp = sys.stdout
    if outtype == 'text':
        device = TextConverter(rsrcmgr, outfp, codec=codec, laparams=laparams,
                               imagewriter=imagewriter)
    elif outtype == 'xml':
        device = XMLConverter(rsrcmgr, outfp, codec=codec, laparams=laparams,
                              imagewriter=imagewriter)
    elif outtype == 'html':
        device = HTMLConverter(rsrcmgr, outfp, codec=codec, scale=scale,
                               layoutmode=layoutmode, laparams=laparams,
                               imagewriter=imagewriter)
    elif outtype == 'tag':
        device = TagExtractor(rsrcmgr, outfp, codec=codec)
    else:
        return usage()
    for fname in args:
        fp = file(fname, 'rb')
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.get_pages(fp, pagenos,
                                      maxpages=maxpages, password=password,
                                      caching=caching, check_extractable=True):
            page.rotate = (page.rotate+rotation) % 360
            interpreter.process_page(page)
        fp.close()
    device.close()
    outfp.close()
    return

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = prof
#!/usr/bin/env python
import sys

def prof_main(argv):
    import hotshot, hotshot.stats
    def usage():
        print 'usage: %s module.function [args ...]' % argv[0]
        return 100
    args = argv[1:]
    if len(args) < 1: return usage()
    name = args.pop(0)
    prof = name+'.prof'
    i = name.rindex('.')
    (modname, funcname) = (name[:i], name[i+1:])
    module = __import__(modname, fromlist=1)
    func = getattr(module, funcname)
    if args:
        args.insert(0, argv[0])
        prof = hotshot.Profile(prof)
        prof.runcall(lambda : func(args))
        prof.close()
    else:
        stats = hotshot.stats.load(prof)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(1000)
    return

if __name__ == '__main__': sys.exit(prof_main(sys.argv))

########NEW FILE########
__FILENAME__ = runapp
#!/usr/bin/env python
##
##  WebApp class runner
##
##  usage:
##    $ runapp.py pdf2html.cgi
##

import sys
import urllib
from httplib import responses
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

##  WebAppHandler
##
class WebAppHandler(SimpleHTTPRequestHandler):

    APP_CLASS = None

    def do_POST(self):
        return self.run_cgi()

    def send_head(self):
        return self.run_cgi()

    def run_cgi(self):
        rest = self.path
        i = rest.rfind('?')
        if i >= 0:
            rest, query = rest[:i], rest[i+1:]
        else:
            query = ''
        i = rest.find('/')
        if i >= 0:
            script, rest = rest[:i], rest[i:]
        else:
            script, rest = rest, ''
        scriptname = '/' + script
        scriptfile = self.translate_path(scriptname)
        env = {}
        env['SERVER_SOFTWARE'] = self.version_string()
        env['SERVER_NAME'] = self.server.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PROTOCOL'] = self.protocol_version
        env['SERVER_PORT'] = str(self.server.server_port)
        env['REQUEST_METHOD'] = self.command
        uqrest = urllib.unquote(rest)
        env['PATH_INFO'] = uqrest
        env['PATH_TRANSLATED'] = self.translate_path(uqrest)
        env['SCRIPT_NAME'] = scriptname
        if query:
            env['QUERY_STRING'] = query
        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
        env['REMOTE_ADDR'] = self.client_address[0]
        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        accept = []
        for line in self.headers.getallmatchingheaders('accept'):
            if line[:1] in "\t\n\r ":
                accept.append(line.strip())
            else:
                accept = accept + line[7:].split(',')
        env['HTTP_ACCEPT'] = ','.join(accept)
        ua = self.headers.getheader('user-agent')
        if ua:
            env['HTTP_USER_AGENT'] = ua
        co = filter(None, self.headers.getheaders('cookie'))
        if co:
            env['HTTP_COOKIE'] = ', '.join(co)
        for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH',
                  'HTTP_USER_AGENT', 'HTTP_COOKIE'):
            env.setdefault(k, "")
        app = self.APP_CLASS(infp=self.rfile, outfp=self.wfile, environ=env)
        status = app.setup()
        self.send_response(status, responses[status])
        app.run()
        return

# main
def main(argv):
    import getopt, imp
    def usage():
        print 'usage: %s [-h host] [-p port] [-n name] module.class' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'h:p:n:')
    except getopt.GetoptError:
        return usage()
    host = ''
    port = 8080
    name = 'WebApp'
    for (k, v) in opts:
        if k == '-h': host = v
        elif k == '-p': port = int(v)
        elif k == '-n': name = v
    if not args: return usage()
    path = args.pop(0)
    module = imp.load_source('app', path)
    WebAppHandler.APP_CLASS = getattr(module, name)
    print 'Listening %s:%d...' % (host,port)
    httpd = HTTPServer((host,port), WebAppHandler)
    httpd.serve_forever()
    return

if __name__ == '__main__': sys.exit(main(sys.argv))

########NEW FILE########
