__FILENAME__ = arnetwork
# Copyright (c) 2011 Bastian Venthur
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


"""
This module provides access to the data provided by the AR.Drone.
"""

import select
import socket
import threading
import multiprocessing

import libardrone
import arvideo


class ARDroneNetworkProcess(multiprocessing.Process):
    """ARDrone Network Process.

    This process collects data from the video and navdata port, converts the
    data and sends it to the IPCThread.
    """

    def __init__(self, nav_pipe, video_pipe, com_pipe):
        multiprocessing.Process.__init__(self)
        self.nav_pipe = nav_pipe
        self.video_pipe = video_pipe
        self.com_pipe = com_pipe

    def run(self):
        video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        video_socket.setblocking(0)
        video_socket.bind(('', libardrone.ARDRONE_VIDEO_PORT))
        video_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', libardrone.ARDRONE_VIDEO_PORT))

        nav_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        nav_socket.setblocking(0)
        nav_socket.bind(('', libardrone.ARDRONE_NAVDATA_PORT))
        nav_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', libardrone.ARDRONE_NAVDATA_PORT))

        stopping = False
        while not stopping:
            inputready, outputready, exceptready = select.select([nav_socket, video_socket, self.com_pipe], [], [])
            for i in inputready:
                if i == video_socket:
                    while 1:
                        try:
                            data = video_socket.recv(65535)
                        except IOError:
                            # we consumed every packet from the socket and
                            # continue with the last one
                            break
                    w, h, image, t = arvideo.read_picture(data)
                    self.video_pipe.send(image)
                elif i == nav_socket:
                    while 1:
                        try:
                            data = nav_socket.recv(65535)
                        except IOError:
                            # we consumed every packet from the socket and
                            # continue with the last one
                            break
                    navdata = libardrone.decode_navdata(data)
                    self.nav_pipe.send(navdata)
                elif i == self.com_pipe:
                    _ = self.com_pipe.recv()
                    stopping = True
                    break
        video_socket.close()
        nav_socket.close()


class IPCThread(threading.Thread):
    """Inter Process Communication Thread.

    This thread collects the data from the ARDroneNetworkProcess and forwards
    it to the ARDreone.
    """

    def __init__(self, drone):
        threading.Thread.__init__(self)
        self.drone = drone
        self.stopping = False

    def run(self):
        while not self.stopping:
            inputready, outputready, exceptready = select.select([self.drone.video_pipe, self.drone.nav_pipe], [], [], 1)
            for i in inputready:
                if i == self.drone.video_pipe:
                    while self.drone.video_pipe.poll():
                        image = self.drone.video_pipe.recv()
                    self.drone.image = image
                elif i == self.drone.nav_pipe:
                    while self.drone.nav_pipe.poll():
                        navdata = self.drone.nav_pipe.recv()
                    self.drone.navdata = navdata

    def stop(self):
        """Stop the IPCThread activity."""
        self.stopping = True


########NEW FILE########
__FILENAME__ = arvideo
#!/usr/bin/env python

# Copyright (c) 2011 Bastian Venthur
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


"""
Video decoding for the AR.Drone.

This library uses psyco to speed-up the decoding process. It is however written
in a way that it works also without psyco installed. On the author's
development machine the speed up is from 2FPS w/o psyco to > 20 FPS w/ psyco.
"""


import array
import cProfile
import datetime
import struct
import sys

try:
    import psyco
except ImportError:
    print "Please install psyco for better video decoding performance."


# from zig-zag back to normal
ZIG_ZAG_POSITIONS = array.array('B',
    ( 0,  1,  8, 16,  9,  2, 3, 10,
     17, 24, 32, 25, 18, 11, 4,  5,
     12, 19, 26, 33, 40, 48, 41, 34,
     27, 20, 13,  6,  7, 14, 21, 28,
     35, 42, 49, 56, 57, 50, 43, 36,
     29, 22, 15, 23, 30, 37, 44, 51,
     58, 59, 52, 45, 38, 31, 39, 46,
     53, 60, 61, 54, 47, 55, 62, 63))

# Inverse quantization
IQUANT_TAB = array.array('B',
    ( 3,  5,  7,  9, 11, 13, 15, 17,
      5,  7,  9, 11, 13, 15, 17, 19,
      7,  9, 11, 13, 15, 17, 19, 21,
      9, 11, 13, 15, 17, 19, 21, 23,
     11, 13, 15, 17, 19, 21, 23, 25,
     13, 15, 17, 19, 21, 23, 25, 27,
     15, 17, 19, 21, 23, 25, 27, 29,
     17, 19, 21, 23, 25, 27, 29, 31))

# Used for upscaling the 8x8 b- and r-blocks to 16x16
SCALE_TAB = array.array('B', 
    ( 0,  0,  1,  1,  2,  2,  3,  3,
      0,  0,  1,  1,  2,  2,  3,  3,
      8,  8,  9,  9, 10, 10, 11, 11,
      8,  8,  9,  9, 10, 10, 11, 11,
     16, 16, 17, 17, 18, 18, 19, 19,
     16, 16, 17, 17, 18, 18, 19, 19,
     24, 24, 25, 25, 26, 26, 27, 27,
     24, 24, 25, 25, 26, 26, 27, 27,

      4,  4,  5,  5,  6,  6,  7,  7,
      4,  4,  5,  5,  6,  6,  7,  7,
     12, 12, 13, 13, 14, 14, 15, 15,
     12, 12, 13, 13, 14, 14, 15, 15,
     20, 20, 21, 21, 22, 22, 23, 23,
     20, 20, 21, 21, 22, 22, 23, 23,
     28, 28, 29, 29, 30, 30, 31, 31,
     28, 28, 29, 29, 30, 30, 31, 31,

     32, 32, 33, 33, 34, 34, 35, 35,
     32, 32, 33, 33, 34, 34, 35, 35,
     40, 40, 41, 41, 42, 42, 43, 43,
     40, 40, 41, 41, 42, 42, 43, 43,
     48, 48, 49, 49, 50, 50, 51, 51,
     48, 48, 49, 49, 50, 50, 51, 51,
     56, 56, 57, 57, 58, 58, 59, 59,
     56, 56, 57, 57, 58, 58, 59, 59,

     36, 36, 37, 37, 38, 38, 39, 39,
     36, 36, 37, 37, 38, 38, 39, 39,
     44, 44, 45, 45, 46, 46, 47, 47,
     44, 44, 45, 45, 46, 46, 47, 47,
     52, 52, 53, 53, 54, 54, 55, 55,
     52, 52, 53, 53, 54, 54, 55, 55,
     60, 60, 61, 61, 62, 62, 63, 63,
     60, 60, 61, 61, 62, 62, 63, 63))

# Count leading zeros look up table
CLZLUT = array.array('B',
    (8, 7, 6, 6, 5, 5, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4,
     3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
     2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
     2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
     1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
     1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
     1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
     1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

# Map pixels from four 8x8 blocks to one 16x16
MB_TO_GOB_MAP = array.array('B',
    [  0,   1,   2,   3,   4,   5,   6,   7,
      16,  17,  18,  19,  20,  21,  22,  23,
      32,  33,  34,  35,  36,  37,  38,  39,
      48,  49,  50,  51,  52,  53,  54,  55,
      64,  65,  66,  67,  68,  69,  70,  71,
      80,  81,  82,  83,  84,  85,  86,  87,
      96,  97,  98,  99, 100, 101, 102, 103,
     112, 113, 114, 115, 116, 117, 118, 119,
       8,   9,  10,  11,  12,  13,  14,  15,
      24,  25,  26,  27,  28,  29,  30,  31,
      40,  41,  42,  43,  44,  45,  46,  47,
      56,  57,  58,  59,  60,  61,  62,  63,
      72,  73,  74,  75,  76,  77,  78,  79,
      88,  89,  90,  91,  92,  93,  94,  95,
     104, 105, 106, 107, 108, 109, 110, 111,
     120, 121, 122, 123, 124, 125, 126, 127,
     128, 129, 130, 131, 132, 133, 134, 135,
     144, 145, 146, 147, 148, 149, 150, 151,
     160, 161, 162, 163, 164, 165, 166, 167,
     176, 177, 178, 179, 180, 181, 182, 183,
     192, 193, 194, 195, 196, 197, 198, 199,
     208, 209, 210, 211, 212, 213, 214, 215,
     224, 225, 226, 227, 228, 229, 230, 231,
     240, 241, 242, 243, 244, 245, 246, 247,
     136, 137, 138, 139, 140, 141, 142, 143,
     152, 153, 154, 155, 156, 157, 158, 159,
     168, 169, 170, 171, 172, 173, 174, 175,
     184, 185, 186, 187, 188, 189, 190, 191,
     200, 201, 202, 203, 204, 205, 206, 207,
     216, 217, 218, 219, 220, 221, 222, 223,
     232, 233, 234, 235, 236, 237, 238, 239,
     248, 249, 250, 251, 252, 253, 254, 255])
MB_ROW_MAP = array.array('B', [i / 16 for i in MB_TO_GOB_MAP])
MB_COL_MAP = array.array('B', [i % 16 for i in MB_TO_GOB_MAP])

# An array of zeros. It is much faster to take the zeros from here than to
# generate a new list when needed.
ZEROS = array.array('i', [0 for i in range(256)])

# Constants needed for the inverse discrete cosine transform.
FIX_0_298631336 = 2446
FIX_0_390180644 = 3196
FIX_0_541196100 = 4433
FIX_0_765366865 = 6270
FIX_0_899976223 = 7373
FIX_1_175875602 = 9633
FIX_1_501321110 = 12299
FIX_1_847759065 = 15137
FIX_1_961570560 = 16069
FIX_2_053119869 = 16819
FIX_2_562915447 = 20995
FIX_3_072711026 = 25172
CONST_BITS = 13
PASS1_BITS = 1
F1 = CONST_BITS - PASS1_BITS - 1
F2 = CONST_BITS - PASS1_BITS
F3 = CONST_BITS + PASS1_BITS + 3

# tuning parameter for get_block
TRIES = 16
MASK = 2**(TRIES*32)-1
SHIFT = 32*(TRIES-1)


def _first_half(data):
    """Helper function used to precompute the zero values in a 12 bit datum.
    """
    # data has to be 12 bits wide
    streamlen = 0
    # count the zeros
    zerocount = CLZLUT[data >> 4];
    data = (data << (zerocount + 1)) & 0b111111111111
    streamlen += zerocount + 1
    # get number of remaining bits to read
    toread = 0 if zerocount <= 1 else zerocount - 1
    additional = data >> (12 - toread)
    data = (data << toread) & 0b111111111111
    streamlen += toread
    # add as many zeros to out_list as indicated by additional bits
    # if zerocount is 0, tmp = 0 else the 1 merged with additional bits
    tmp = 0 if zerocount == 0 else (1 << toread) | additional
    return [streamlen, tmp]


def _second_half(data):
    """Helper function to precompute the nonzeror values in a 15 bit datum.
    """
    # data has to be 15 bits wide
    streamlen = 0
    zerocount = CLZLUT[data >> 7]
    data = (data << (zerocount + 1)) & 0b111111111111111
    streamlen += zerocount + 1
    # 01 == EOB
    eob = False
    if zerocount == 1:
        eob = True
        return [streamlen, None, eob]
    # get number of remaining bits to read
    toread = 0 if zerocount == 0 else zerocount - 1
    additional = data >> (15 - toread)
    data = (data << toread) & 0b111111111111111
    streamlen += toread
    tmp = (1 << toread) | additional
    # get one more bit for the sign
    tmp = -tmp if data >> (15 - 1) else tmp
    tmp = int(tmp)
    streamlen += 1
    return [streamlen, tmp, eob]


# Precompute all 12 and 15 bit values for the entropy decoding process
FH = [_first_half(i) for i in range(2**12)]
SH = [_second_half(i) for i in range(2**15)]


class BitReader(object):
    """Bitreader. Given a stream of data, it allows to read it bitwise."""

    def __init__(self, packet):
        self.packet = packet
        self.offset = 0
        self.bits_left = 0
        self.chunk = 0
        self.read_bits = 0

    def read(self, nbits, consume=True):
        """Read nbits and return the integervalue of the read bits.

        If consume is False, it behaves like a 'peek' method (ie it reads the
        bits but does not consume them.
        """
        # Read enough bits into chunk so we have at least nbits available
        while nbits > self.bits_left:
            try:
                self.chunk = (self.chunk << 32) | struct.unpack_from('<I', self.packet, self.offset)[0]
            except struct.error:
                self.chunk <<= 32
            self.offset += 4
            self.bits_left += 32
        # Get the first nbits bits from chunk (and remove them from chunk)
        shift = self.bits_left - nbits
        res = self.chunk >> shift
        if consume:
            self.chunk -= res << shift
            self.bits_left -= nbits
            self.read_bits += nbits
        return res

    def align(self):
        """Byte align the data stream."""
        shift = (8 - self.read_bits) % 8
        self.read(shift)


def inverse_dct(block):
    """Inverse discrete cosine transform.
    """
    workspace = ZEROS[0:64]
    data = ZEROS[0:64]
    for pointer in range(8):
        if (block[pointer + 8] == 0 and block[pointer + 16] == 0 and
            block[pointer + 24] == 0 and block[pointer + 32] == 0 and
            block[pointer + 40] == 0 and block[pointer + 48] == 0 and
            block[pointer + 56] == 0):
            dcval = block[pointer] << PASS1_BITS
            for i in range(8):
                workspace[pointer + i*8] = dcval
            continue

        z2 = block[pointer + 16]
        z3 = block[pointer + 48]
        z1 = (z2 + z3) * FIX_0_541196100
        tmp2 = z1 + z3 * -FIX_1_847759065
        tmp3 = z1 + z2 * FIX_0_765366865
        z2 = block[pointer]
        z3 = block[pointer + 32]
        tmp0 = (z2 + z3) << CONST_BITS
        tmp1 = (z2 - z3) << CONST_BITS
        tmp10 = tmp0 + tmp3
        tmp13 = tmp0 - tmp3
        tmp11 = tmp1 + tmp2
        tmp12 = tmp1 - tmp2
        tmp0 = block[pointer + 56]
        tmp1 = block[pointer + 40]
        tmp2 = block[pointer + 24]
        tmp3 = block[pointer + 8]
        z1 = tmp0 + tmp3
        z2 = tmp1 + tmp2
        z3 = tmp0 + tmp2
        z4 = tmp1 + tmp3
        z5 = (z3 + z4) * FIX_1_175875602
        tmp0 *= FIX_0_298631336
        tmp1 *= FIX_2_053119869
        tmp2 *= FIX_3_072711026
        tmp3 *= FIX_1_501321110
        z1 *= -FIX_0_899976223
        z2 *= -FIX_2_562915447
        z3 *= -FIX_1_961570560
        z4 *= -FIX_0_390180644
        z3 += z5
        z4 += z5
        tmp0 += z1 + z3
        tmp1 += z2 + z4
        tmp2 += z2 + z3
        tmp3 += z1 + z4
        workspace[pointer + 0] = ((tmp10 + tmp3 + (1 << F1)) >> F2)
        workspace[pointer + 56] = ((tmp10 - tmp3 + (1 << F1)) >> F2)
        workspace[pointer + 8] = ((tmp11 + tmp2 + (1 << F1)) >> F2)
        workspace[pointer + 48] = ((tmp11 - tmp2 + (1 << F1)) >> F2)
        workspace[pointer + 16] = ((tmp12 + tmp1 + (1 << F1)) >> F2)
        workspace[pointer + 40] = ((tmp12 - tmp1 + (1 << F1)) >> F2)
        workspace[pointer + 24] = ((tmp13 + tmp0 + (1 << F1)) >> F2)
        workspace[pointer + 32] = ((tmp13 - tmp0 + (1 << F1)) >> F2)

    for pointer in range(0, 64, 8):
        z2 = workspace[pointer + 2]
        z3 = workspace[pointer + 6]
        z1 = (z2 + z3) * FIX_0_541196100
        tmp2 = z1 + z3 * -FIX_1_847759065
        tmp3 = z1 + z2 * FIX_0_765366865
        tmp0 = (workspace[pointer] + workspace[pointer + 4]) << CONST_BITS
        tmp1 = (workspace[pointer] - workspace[pointer + 4]) << CONST_BITS
        tmp10 = tmp0 + tmp3
        tmp13 = tmp0 - tmp3
        tmp11 = tmp1 + tmp2
        tmp12 = tmp1 - tmp2
        tmp0 = workspace[pointer + 7]
        tmp1 = workspace[pointer + 5]
        tmp2 = workspace[pointer + 3]
        tmp3 = workspace[pointer + 1]
        z1 = tmp0 + tmp3
        z2 = tmp1 + tmp2
        z3 = tmp0 + tmp2
        z4 = tmp1 + tmp3
        z5 = (z3 + z4) * FIX_1_175875602
        tmp0 *= FIX_0_298631336
        tmp1 *= FIX_2_053119869
        tmp2 *= FIX_3_072711026
        tmp3 *= FIX_1_501321110
        z1 *= -FIX_0_899976223
        z2 *= -FIX_2_562915447
        z3 *= -FIX_1_961570560
        z4 *= -FIX_0_390180644
        z3 += z5
        z4 += z5
        tmp0 += z1 + z3
        tmp1 += z2 + z4
        tmp2 += z2 + z3
        tmp3 += z1 + z4
        data[pointer + 0] = (tmp10 + tmp3) >> F3
        data[pointer + 7] = (tmp10 - tmp3) >> F3
        data[pointer + 1] = (tmp11 + tmp2) >> F3
        data[pointer + 6] = (tmp11 - tmp2) >> F3
        data[pointer + 2] = (tmp12 + tmp1) >> F3
        data[pointer + 5] = (tmp12 - tmp1) >> F3
        data[pointer + 3] = (tmp13 + tmp0) >> F3
        data[pointer + 4] = (tmp13 - tmp0) >> F3

    return data


def get_pheader(bitreader):
    """Read the picture header.

    Returns the width and height of the image.
    """
    bitreader.align()
    psc = bitreader.read(22)
    assert(psc == 0b0000000000000000100000)
    pformat = bitreader.read(2)
    assert(pformat != 0b00)
    if pformat == 1:
        # CIF
        width, height = 88, 72
    else:
        # VGA
        width, height = 160, 120
    presolution = bitreader.read(3)
    assert(presolution != 0b000)
    # double resolution presolution-1 times
    width = width << presolution - 1
    height = height << presolution - 1
    #print "width/height:", width, height
    ptype = bitreader.read(3)
    pquant = bitreader.read(5)
    pframe = bitreader.read(32)
    return width, height


def get_mb(bitreader, picture, width, offset):
    """Get macro block.

    This method does not return data but modifies the picture parameter in
    place.
    """
    mbc = bitreader.read(1)
    if mbc == 0:
        mbdesc = bitreader.read(8)
        assert(mbdesc >> 7 & 1)
        if mbdesc >> 6 & 1:
            mbdiff = bitreader.read(2)
        y = get_block(bitreader, mbdesc & 1)
        y.extend(get_block(bitreader, mbdesc >> 1 & 1))
        y.extend(get_block(bitreader, mbdesc >> 2 & 1))
        y.extend(get_block(bitreader, mbdesc >> 3 & 1))
        cb = get_block(bitreader, mbdesc >> 4 & 1)
        cr = get_block(bitreader, mbdesc >> 5 & 1)
        # ycbcr to rgb
        for i in range(256):
            j = SCALE_TAB[i]
            Y = y[i] - 16
            B = cb[j] - 128
            R = cr[j] - 128
            r = (298 * Y           + 409 * R + 128) >> 8
            g = (298 * Y - 100 * B - 208 * R + 128) >> 8
            b = (298 * Y + 516 * B           + 128) >> 8
            r = 0 if r < 0 else r
            r = 255 if r > 255 else r
            g = 0 if g < 0 else g
            g = 255 if g > 255 else g
            b = 0 if b < 0 else b
            b = 255 if b > 255 else b
            # re-order the pixels
            row = MB_ROW_MAP[i]
            col = MB_COL_MAP[i]
            picture[offset + row*width + col] = ''.join((chr(r), chr(g), chr(b)))
    else:
        print "mbc was not zero"


def get_block(bitreader, has_coeff):
    """Read a 8x8 block from the data stream.

    This method takes care of the huffman-, RLE, zig-zag and idct and returns a
    list of 64 ints.
    """
    # read the first 10 bits in a 16 bit datum
    out_list = ZEROS[0:64]
    out_list[0] = int(bitreader.read(10)) * IQUANT_TAB[0]
    if not has_coeff:
        return inverse_dct(out_list)
    i = 1
    while 1:
        _ = bitreader.read(32*TRIES, False)
        streamlen = 0
        #######################################################################
        for j in range(TRIES):
            data = (_ << streamlen) & MASK
            data >>= SHIFT

            l, tmp = FH[data >> 20]
            streamlen += l
            data = (data << l) & 0xffffffff
            i += tmp

            l, tmp, eob = SH[data >> 17]
            streamlen += l
            if eob:
                bitreader.read(streamlen)
                return inverse_dct(out_list)
            j = ZIG_ZAG_POSITIONS[i]
            out_list[j] = tmp*IQUANT_TAB[j]
            i += 1
        #######################################################################
        bitreader.read(streamlen)
    return inverse_dct(out_list)


def get_gob(bitreader, picture, slicenr, width):
    """Read a group of blocks.

    The method does not return data, the picture parameter is modified in place
    instead.
    """
    # the first gob has a special header
    if slicenr > 0:
        bitreader.align()
        gobsc = bitreader.read(22)
        if gobsc == 0b0000000000000000111111:
            print "weeeee"
            return False
        elif (not (gobsc & 0b0000000000000000100000) or
             (gobsc & 0b1111111111111111000000)):
            print "Got wrong GOBSC, aborting.", bin(gobsc)
            return False
        _ = bitreader.read(5)
    offset = slicenr*16*width
    for i in range(width / 16):
        get_mb(bitreader, picture, width, offset+16*i)


def read_picture(data):
    """Convert an AR.Drone image packet to rgb-string.

    Returns: width, height, image and time to decode the image
    """
    bitreader = BitReader(data)
    t = datetime.datetime.now()
    width, height = get_pheader(bitreader)
    slices = height / 16
    blocks = width / 16
    image = [0 for i in range(width*height)]
    for i in range(0, slices):
        get_gob(bitreader, image, i, width)
    bitreader.align()
    eos = bitreader.read(22)
    assert(eos == 0b0000000000000000111111)
    t2 = datetime.datetime.now()
    return width, height, ''.join(image), (t2 - t).microseconds / 1000000.


try:
    psyco.bind(BitReader)
    psyco.bind(get_block)
    psyco.bind(get_gob)
    psyco.bind(get_mb)
    psyco.bind(inverse_dct)
    psyco.bind(read_picture)
except NameError:
    print "Unable to bind video decoding methods with psyco. Proceeding anyways, but video decoding will be slow!"


def main():
    fh = open('framewireshark.raw', 'r')
    #fh = open('videoframe.raw', 'r')
    data = fh.read()
    fh.close()
    runs = 20
    t = 0
    for i in range(runs):
        print '.',
        width, height, image, ti = read_picture(data)
        #show_image(image, width, height)
        t += ti
    print
    print 'avg time:\t', t / runs, 'sec'
    print 'avg fps:\t', 1 / (t / runs), 'fps'
    if 'image' in sys.argv:
        import pygame
        pygame.init()
        W, H = 320, 240
        screen = pygame.display.set_mode((W, H))
        surface = pygame.image.fromstring(image, (width, height), 'RGB')
        screen.blit(surface, (0, 0))
        pygame.display.flip()
        raw_input()


if __name__ == '__main__':
    if 'profile' in sys.argv:
        cProfile.run('main()')
    else:
        main()


########NEW FILE########
__FILENAME__ = demo
#!/usr/bin/env python

# Copyright (c) 2011 Bastian Venthur
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


"""Demo app for the AR.Drone.

This simple application allows to control the drone and see the drone's video
stream.
"""


import pygame

import libardrone


def main():
    pygame.init()
    W, H = 320, 240
    screen = pygame.display.set_mode((W, H))
    drone = libardrone.ARDrone()
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False 
            elif event.type == pygame.KEYUP:
                drone.hover()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    drone.reset()
                    running = False
                # takeoff / land
                elif event.key == pygame.K_RETURN:
                    drone.takeoff()
                elif event.key == pygame.K_SPACE:
                    drone.land()
                # emergency
                elif event.key == pygame.K_BACKSPACE:
                    drone.reset()
                # forward / backward
                elif event.key == pygame.K_w:
                    drone.move_forward()
                elif event.key == pygame.K_s:
                    drone.move_backward()
                # left / right
                elif event.key == pygame.K_a:
                    drone.move_left()
                elif event.key == pygame.K_d:
                    drone.move_right()
                # up / down
                elif event.key == pygame.K_UP:
                    drone.move_up()
                elif event.key == pygame.K_DOWN:
                    drone.move_down()
                # turn left / turn right
                elif event.key == pygame.K_LEFT:
                    drone.turn_left()
                elif event.key == pygame.K_RIGHT:
                    drone.turn_right()
                # speed
                elif event.key == pygame.K_1:
                    drone.speed = 0.1
                elif event.key == pygame.K_2:
                    drone.speed = 0.2
                elif event.key == pygame.K_3:
                    drone.speed = 0.3
                elif event.key == pygame.K_4:
                    drone.speed = 0.4
                elif event.key == pygame.K_5:
                    drone.speed = 0.5
                elif event.key == pygame.K_6:
                    drone.speed = 0.6
                elif event.key == pygame.K_7:
                    drone.speed = 0.7
                elif event.key == pygame.K_8:
                    drone.speed = 0.8
                elif event.key == pygame.K_9:
                    drone.speed = 0.9
                elif event.key == pygame.K_0:
                    drone.speed = 1.0

        try:
            surface = pygame.image.fromstring(drone.image, (W, H), 'RGB')
            # battery status
            hud_color = (255, 0, 0) if drone.navdata.get('drone_state', dict()).get('emergency_mask', 1) else (10, 10, 255)
            bat = drone.navdata.get(0, dict()).get('battery', 0)
            f = pygame.font.Font(None, 20)
            hud = f.render('Battery: %i%%' % bat, True, hud_color)
            screen.blit(surface, (0, 0))
            screen.blit(hud, (10, 10))
        except:
            pass

        pygame.display.flip()
        clock.tick(50)
        pygame.display.set_caption("FPS: %.2f" % clock.get_fps())

    print "Shutting down...",
    drone.halt()
    print "Ok."

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = libardrone
# Copyright (c) 2011 Bastian Venthur
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


"""
Python library for the AR.Drone.

This module was tested with Python 2.6.6 and AR.Drone vanilla firmware 1.5.1.
"""


import socket
import struct
import sys
import threading
import multiprocessing

import arnetwork


__author__ = "Bastian Venthur"


ARDRONE_NAVDATA_PORT = 5554
ARDRONE_VIDEO_PORT = 5555
ARDRONE_COMMAND_PORT = 5556


class ARDrone(object):
    """ARDrone Class.

    Instanciate this class to control your drone and receive decoded video and
    navdata.
    """

    def __init__(self):
        self.seq_nr = 1
        self.timer_t = 0.2
        self.com_watchdog_timer = threading.Timer(self.timer_t, self.commwdg)
        self.lock = threading.Lock()
        self.speed = 0.2
        self.at(at_config, "general:navdata_demo", "TRUE")
        self.video_pipe, video_pipe_other = multiprocessing.Pipe()
        self.nav_pipe, nav_pipe_other = multiprocessing.Pipe()
        self.com_pipe, com_pipe_other = multiprocessing.Pipe()
        self.network_process = arnetwork.ARDroneNetworkProcess(nav_pipe_other, video_pipe_other, com_pipe_other)
        self.network_process.start()
        self.ipc_thread = arnetwork.IPCThread(self)
        self.ipc_thread.start()
        self.image = ""
        self.navdata = dict()
        self.time = 0

    def takeoff(self):
        """Make the drone takeoff."""
        self.at(at_ftrim)
        self.at(at_config, "control:altitude_max", "20000")
        self.at(at_ref, True)

    def land(self):
        """Make the drone land."""
        self.at(at_ref, False)

    def hover(self):
        """Make the drone hover."""
        self.at(at_pcmd, False, 0, 0, 0, 0)

    def move_left(self):
        """Make the drone move left."""
        self.at(at_pcmd, True, -self.speed, 0, 0, 0)

    def move_right(self):
        """Make the drone move right."""
        self.at(at_pcmd, True, self.speed, 0, 0, 0)

    def move_up(self):
        """Make the drone rise upwards."""
        self.at(at_pcmd, True, 0, 0, self.speed, 0)

    def move_down(self):
        """Make the drone decent downwards."""
        self.at(at_pcmd, True, 0, 0, -self.speed, 0)

    def move_forward(self):
        """Make the drone move forward."""
        self.at(at_pcmd, True, 0, -self.speed, 0, 0)

    def move_backward(self):
        """Make the drone move backwards."""
        self.at(at_pcmd, True, 0, self.speed, 0, 0)

    def turn_left(self):
        """Make the drone rotate left."""
        self.at(at_pcmd, True, 0, 0, 0, -self.speed)

    def turn_right(self):
        """Make the drone rotate right."""
        self.at(at_pcmd, True, 0, 0, 0, self.speed)

    def reset(self):
        """Toggle the drone's emergency state."""
        self.at(at_ref, False, True)
        self.at(at_ref, False, False)

    def trim(self):
        """Flat trim the drone."""
        self.at(at_ftrim)

    def set_speed(self, speed):
        """Set the drone's speed.

        Valid values are floats from [0..1]
        """
        self.speed = speed

    def at(self, cmd, *args, **kwargs):
        """Wrapper for the low level at commands.

        This method takes care that the sequence number is increased after each
        at command and the watchdog timer is started to make sure the drone
        receives a command at least every second.
        """
        self.lock.acquire()
        self.com_watchdog_timer.cancel()
        cmd(self.seq_nr, *args, **kwargs)
        self.seq_nr += 1
        self.com_watchdog_timer = threading.Timer(self.timer_t, self.commwdg)
        self.com_watchdog_timer.start()
        self.lock.release()

    def commwdg(self):
        """Communication watchdog signal.

        This needs to be send regulary to keep the communication w/ the drone
        alive.
        """
        self.at(at_comwdg)

    def halt(self):
        """Shutdown the drone.

        This method does not land or halt the actual drone, but the
        communication with the drone. You should call it at the end of your
        application to close all sockets, pipes, processes and threads related
        with this object.
        """
        self.lock.acquire()
        self.com_watchdog_timer.cancel()
        self.com_pipe.send('die!')
        self.network_process.terminate()
        self.network_process.join()
        self.ipc_thread.stop()
        self.ipc_thread.join()
        self.lock.release()


###############################################################################
### Low level AT Commands
###############################################################################

def at_ref(seq, takeoff, emergency=False):
    """
    Basic behaviour of the drone: take-off/landing, emergency stop/reset)

    Parameters:
    seq -- sequence number
    takeoff -- True: Takeoff / False: Land
    emergency -- True: Turn of the engines
    """
    p = 0b10001010101000000000000000000
    if takeoff:
        p += 0b1000000000
    if emergency:
        p += 0b0100000000
    at("REF", seq, [p])

def at_pcmd(seq, progressive, lr, fb, vv, va):
    """
    Makes the drone move (translate/rotate).

    Parameters:
    seq -- sequence number
    progressive -- True: enable progressive commands, False: disable (i.e.
        enable hovering mode)
    lr -- left-right tilt: float [-1..1] negative: left, positive: right
    rb -- front-back tilt: float [-1..1] negative: forwards, positive:
        backwards
    vv -- vertical speed: float [-1..1] negative: go down, positive: rise
    va -- angular speed: float [-1..1] negative: spin left, positive: spin 
        right

    The above float values are a percentage of the maximum speed.
    """
    p = 1 if progressive else 0
    at("PCMD", seq, [p, float(lr), float(fb), float(vv), float(va)])

def at_ftrim(seq):
    """
    Tell the drone it's lying horizontally.

    Parameters:
    seq -- sequence number
    """
    at("FTRIM", seq, [])

def at_zap(seq, stream):
    """
    Selects which video stream to send on the video UDP port.

    Parameters:
    seq -- sequence number
    stream -- Integer: video stream to broadcast
    """
    # FIXME: improve parameters to select the modes directly
    at("ZAP", seq, [stream])

def at_config(seq, option, value):
    """Set configuration parameters of the drone."""
    at("CONFIG", seq, [str(option), str(value)])

def at_comwdg(seq):
    """
    Reset communication watchdog.
    """
    # FIXME: no sequence number
    at("COMWDG", seq, [])

def at_aflight(seq, flag):
    """
    Makes the drone fly autonomously.

    Parameters:
    seq -- sequence number
    flag -- Integer: 1: start flight, 0: stop flight
    """
    at("AFLIGHT", seq, [flag])

def at_pwm(seq, m1, m2, m3, m4):
    """
    Sends control values directly to the engines, overriding control loops.

    Parameters:
    seq -- sequence number
    m1 -- front left command
    m2 -- fright right command
    m3 -- back right command
    m4 -- back left command
    """
    # FIXME: what type do mx have?
    pass

def at_led(seq, anim, f, d):
    """
    Control the drones LED.

    Parameters:
    seq -- sequence number
    anim -- Integer: animation to play
    f -- ?: frequence in HZ of the animation
    d -- Integer: total duration in seconds of the animation
    """
    pass

def at_anim(seq, anim, d):
    """
    Makes the drone execute a predefined movement (animation).

    Parameters:
    seq -- sequcence number
    anim -- Integer: animation to play
    d -- Integer: total duration in sections of the animation
    """
    at("ANIM", seq, [anim, d])

def at(command, seq, params):
    """
    Parameters:
    command -- the command
    seq -- the sequence number
    params -- a list of elements which can be either int, float or string
    """
    param_str = ''
    for p in params:
        if type(p) == int:
            param_str += ",%d" % p
        elif type(p) == float:
            param_str += ",%d" % f2i(p)
        elif type(p) == str:
            param_str += ',"'+p+'"'
    msg = "AT*%s=%i%s\r" % (command, seq, param_str)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, ("192.168.1.1", ARDRONE_COMMAND_PORT))

def f2i(f):
    """Interpret IEEE-754 floating-point value as signed integer.

    Arguments:
    f -- floating point value
    """
    return struct.unpack('i', struct.pack('f', f))[0]

###############################################################################
### navdata
###############################################################################
def decode_navdata(packet):
    """Decode a navdata packet."""
    offset = 0
    _ =  struct.unpack_from("IIII", packet, offset)
    drone_state = dict()
    drone_state['fly_mask']             = _[1]       & 1 # FLY MASK : (0) ardrone is landed, (1) ardrone is flying
    drone_state['video_mask']           = _[1] >>  1 & 1 # VIDEO MASK : (0) video disable, (1) video enable
    drone_state['vision_mask']          = _[1] >>  2 & 1 # VISION MASK : (0) vision disable, (1) vision enable */
    drone_state['control_mask']         = _[1] >>  3 & 1 # CONTROL ALGO (0) euler angles control, (1) angular speed control */
    drone_state['altitude_mask']        = _[1] >>  4 & 1 # ALTITUDE CONTROL ALGO : (0) altitude control inactive (1) altitude control active */
    drone_state['user_feedback_start']  = _[1] >>  5 & 1 # USER feedback : Start button state */
    drone_state['command_mask']         = _[1] >>  6 & 1 # Control command ACK : (0) None, (1) one received */
    drone_state['fw_file_mask']         = _[1] >>  7 & 1 # Firmware file is good (1) */
    drone_state['fw_ver_mask']          = _[1] >>  8 & 1 # Firmware update is newer (1) */
    drone_state['fw_upd_mask']          = _[1] >>  9 & 1 # Firmware update is ongoing (1) */
    drone_state['navdata_demo_mask']    = _[1] >> 10 & 1 # Navdata demo : (0) All navdata, (1) only navdata demo */
    drone_state['navdata_bootstrap']    = _[1] >> 11 & 1 # Navdata bootstrap : (0) options sent in all or demo mode, (1) no navdata options sent */
    drone_state['motors_mask']          = _[1] >> 12 & 1 # Motor status : (0) Ok, (1) Motors problem */
    drone_state['com_lost_mask']        = _[1] >> 13 & 1 # Communication lost : (1) com problem, (0) Com is ok */
    drone_state['vbat_low']             = _[1] >> 15 & 1 # VBat low : (1) too low, (0) Ok */
    drone_state['user_el']              = _[1] >> 16 & 1 # User Emergency Landing : (1) User EL is ON, (0) User EL is OFF*/
    drone_state['timer_elapsed']        = _[1] >> 17 & 1 # Timer elapsed : (1) elapsed, (0) not elapsed */
    drone_state['angles_out_of_range']  = _[1] >> 19 & 1 # Angles : (0) Ok, (1) out of range */
    drone_state['ultrasound_mask']      = _[1] >> 21 & 1 # Ultrasonic sensor : (0) Ok, (1) deaf */
    drone_state['cutout_mask']          = _[1] >> 22 & 1 # Cutout system detection : (0) Not detected, (1) detected */
    drone_state['pic_version_mask']     = _[1] >> 23 & 1 # PIC Version number OK : (0) a bad version number, (1) version number is OK */
    drone_state['atcodec_thread_on']    = _[1] >> 24 & 1 # ATCodec thread ON : (0) thread OFF (1) thread ON */
    drone_state['navdata_thread_on']    = _[1] >> 25 & 1 # Navdata thread ON : (0) thread OFF (1) thread ON */
    drone_state['video_thread_on']      = _[1] >> 26 & 1 # Video thread ON : (0) thread OFF (1) thread ON */
    drone_state['acq_thread_on']        = _[1] >> 27 & 1 # Acquisition thread ON : (0) thread OFF (1) thread ON */
    drone_state['ctrl_watchdog_mask']   = _[1] >> 28 & 1 # CTRL watchdog : (1) delay in control execution (> 5ms), (0) control is well scheduled */
    drone_state['adc_watchdog_mask']    = _[1] >> 29 & 1 # ADC Watchdog : (1) delay in uart2 dsr (> 5ms), (0) uart2 is good */
    drone_state['com_watchdog_mask']    = _[1] >> 30 & 1 # Communication Watchdog : (1) com problem, (0) Com is ok */
    drone_state['emergency_mask']       = _[1] >> 31 & 1 # Emergency landing : (0) no emergency, (1) emergency */
    data = dict()
    data['drone_state'] = drone_state
    data['header'] = _[0]
    data['seq_nr'] = _[2]
    data['vision_flag'] = _[3]
    offset += struct.calcsize("IIII")
    while 1:
        try:
            id_nr, size =  struct.unpack_from("HH", packet, offset)
            offset += struct.calcsize("HH")
        except struct.error:
            break
        values = []
        for i in range(size-struct.calcsize("HH")):
            values.append(struct.unpack_from("c", packet, offset)[0])
            offset += struct.calcsize("c")
        # navdata_tag_t in navdata-common.h
        if id_nr == 0:
            values = struct.unpack_from("IIfffIfffI", "".join(values))
            values = dict(zip(['ctrl_state', 'battery', 'theta', 'phi', 'psi', 'altitude', 'vx', 'vy', 'vz', 'num_frames'], values))
            # convert the millidegrees into degrees and round to int, as they
            # are not so precise anyways
            for i in 'theta', 'phi', 'psi':
                values[i] = int(values[i] / 1000)
                #values[i] /= 1000
        data[id_nr] = values
    return data


if __name__ == "__main__":

    import termios
    import fcntl
    import os
    
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    drone = ARDrone()

    try:
        while 1:
            try:
                c = sys.stdin.read(1)
                c = c.lower()
                print "Got character", c
                if c == 'a':
                    drone.move_left()
                if c == 'd':
                    drone.move_right()
                if c == 'w':
                    drone.move_forward()
                if c == 's':
                    drone.move_backward()
                if c == ' ':
                    drone.land()
                if c == '\n':
                    drone.takeoff()
                if c == 'q':
                    drone.turn_left()
                if c == 'e':
                    drone.turn_right()
                if c == '1':
                    drone.move_up()
                if c == '2':
                    drone.hover()
                if c == '3':
                    drone.move_down()
                if c == 't':
                    drone.reset()
                if c == 'x':
                    drone.hover()
                if c == 'y':
                    drone.trim()
            except IOError:
                pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
        drone.halt()


########NEW FILE########
__FILENAME__ = test_libardrone
# Copyright (c) 2011 Bastian Venthur
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


import unittest

import libardrone

class LibardroneTestCase(unittest.TestCase):
    def test_f2i(self):
        self.assertEqual(libardrone.f2i(-0.8,), -1085485875)

if __name__ == "__main__":
    unittest.main()


########NEW FILE########
