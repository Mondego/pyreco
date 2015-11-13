__FILENAME__ = echo
from twisted.python import log
from sys import stdout
log.startLogging(stdout)

from twisted.internet.protocol import Protocol, Factory
class EchoProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class EchoFactory(Factory):
    protocol = EchoProtocol

from txws import WebSocketFactory
from twisted.application.strports import listen

port = listen("tcp:5600", WebSocketFactory(EchoFactory()))

from twisted.internet import reactor
reactor.run()

########NEW FILE########
__FILENAME__ = tests
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.
import six
from twisted.trial import unittest

from txws import (is_hybi00, complete_hybi00, make_hybi00_frame,
                  parse_hybi00_frames, http_headers, make_accept, mask, CLOSE,
                  NORMAL, PING, PONG, parse_hybi07_frames)

class TestHTTPHeaders(unittest.TestCase):

    def test_single_header(self):
        raw = "Connection: Upgrade"
        headers = http_headers(raw)
        self.assertTrue("Connection" in headers)
        self.assertEqual(headers["Connection"], "Upgrade")

    def test_single_header_newline(self):
        raw = "Connection: Upgrade\r\n"
        headers = http_headers(raw)
        self.assertEqual(headers["Connection"], "Upgrade")

    def test_multiple_headers(self):
        raw = "Connection: Upgrade\r\nUpgrade: WebSocket"
        headers = http_headers(raw)
        self.assertEqual(headers["Connection"], "Upgrade")
        self.assertEqual(headers["Upgrade"], "WebSocket")

    def test_origin_colon(self):
        """
        Some headers have multiple colons in them.
        """

        raw = "Origin: http://example.com:8080"
        headers = http_headers(raw)
        self.assertEqual(headers["Origin"], "http://example.com:8080")

class TestKeys(unittest.TestCase):

    def test_make_accept_rfc(self):
        """
        Test ``make_accept()`` using the keys listed in the RFC for HyBi-07
        through HyBi-10.
        """

        key = "dGhlIHNhbXBsZSBub25jZQ=="

        self.assertEqual(make_accept(key), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_make_accept_wikipedia(self):
        """
        Test ``make_accept()`` using the keys listed on Wikipedia.
        """

        key = "x3JJHMbDL1EzLkh9GBhXDw=="

        self.assertEqual(make_accept(key), "HSmrc0sMlYUkAGmm5OPpG2HaGWk=")

class TestHyBi00(unittest.TestCase):

    def test_is_hybi00(self):
        headers = {
            "Sec-WebSocket-Key1": "hurp",
            "Sec-WebSocket-Key2": "derp",
        }
        self.assertTrue(is_hybi00(headers))

    def test_is_hybi00_false(self):
        headers = {
            "Sec-WebSocket-Key1": "hurp",
        }
        self.assertFalse(is_hybi00(headers))

    def test_complete_hybi00_wikipedia(self):
        """
        Test complete_hybi00() using the keys listed on Wikipedia's WebSockets
        page.
        """

        headers = {
            "Sec-WebSocket-Key1": "4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2": "12998 5 Y3 1  .P00",
        }
        challenge = "^n:ds[4U"

        self.assertEqual(complete_hybi00(headers, challenge),
                         six.b("8jKS'y:G*Co,Wxa-"))

    def test_make_hybi00(self):
        """
        HyBi-00 frames are really, *really* simple.
        """

        self.assertEqual(make_hybi00_frame("Test!"), six.b("\x00Test!\xff"))

    def test_parse_hybi00_single(self):
        frame = six.b("\x00Test\xff")

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (NORMAL, six.b("Test")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi00_multiple(self):
        frame = six.b("\x00Test\xff\x00Again\xff")

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0], (NORMAL, six.b("Test")))
        self.assertEqual(frames[1], (NORMAL, six.b("Again")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi00_incomplete(self):
        frame = six.b("\x00Test")

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 0)
        self.assertEqual(buf, six.b("\x00Test"))

    def test_parse_hybi00_garbage(self):
        frame = six.b("trash\x00Test\xff")

        frames, buf = parse_hybi00_frames(frame)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (NORMAL, six.b("Test")))
        self.assertEqual(buf, six.b(""))

    def test_socketio_crashers(self):
        """
        A series of snippets which crash other WebSockets implementations
        (specifically, Socket.IO) are harmless to this implementation.
        """

        frames = [
            """[{"length":1}]""",
            """{"messages":[{"length":1}]}""",
            "hello",
            "hello<script>alert(/xss/)</script>",
            "hello<img src=x:x onerror=alert(/xss.2/)>",
            "{",
            "~m~EVJLFDJP~",
        ]

        for frame in frames:
            prepared = make_hybi00_frame(frame)
            frames, buf = parse_hybi00_frames(prepared)

            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0], (NORMAL, frame.encode('utf-8')))
            self.assertEqual(buf, six.b(""))

class TestHyBi07Helpers(unittest.TestCase):
    """
    HyBi-07 is best understood as a large family of helper functions which
    work together, somewhat dysfunctionally, to produce a mediocre
    Thanksgiving every other year.
    """

    def test_mask_noop(self):
        key = six.b("\x00\x00\x00\x00")
        self.assertEqual(mask(six.b("Test"), key), six.b("Test"))

    def test_mask_noop_long(self):
        key = six.b("\x00\x00\x00\x00")
        self.assertEqual(mask(six.b("LongTest"), key), six.b("LongTest"))

    def test_parse_hybi07_unmasked_text(self):
        """
        From HyBi-10, 4.7.
        """

        frame = six.b("\x81\x05Hello")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (NORMAL, six.b("Hello")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_masked_text(self):
        """
        From HyBi-10, 4.7.
        """

        frame = six.b("\x81\x857\xfa!=\x7f\x9fMQX")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (NORMAL, six.b("Hello")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_unmasked_text_fragments(self):
        """
        We don't care about fragments. We are totally unfazed.

        From HyBi-10, 4.7.
        """

        frame = six.b("\x01\x03Hel\x80\x02lo")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0], (NORMAL, six.b("Hel")))
        self.assertEqual(frames[1], (NORMAL, six.b("lo")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_ping(self):
        """
        From HyBi-10, 4.7.
        """

        frame = six.b("\x89\x05Hello")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (PING, six.b("Hello")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_pong(self):
        """
        From HyBi-10, 4.7.
        """

        frame = six.b("\x8a\x05Hello")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (PONG, six.b("Hello")))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_close_empty(self):
        """
        A HyBi-07 close packet may have no body. In that case, it should use
        the generic error code 1000, and have no reason.
        """

        frame = six.b("\x88\x00")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (CLOSE, (1000, six.b("No reason given"))))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_close_reason(self):
        """
        A HyBi-07 close packet must have its first two bytes be a numeric
        error code, and may optionally include trailing text explaining why
        the connection was closed.
        """

        frame = six.b("\x88\x0b\x03\xe8No reason")
        frames, buf = parse_hybi07_frames(frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], (CLOSE, (1000, six.b("No reason"))))
        self.assertEqual(buf, six.b(""))

    def test_parse_hybi07_partial_no_length(self):
        frame = six.b("\x81")
        frames, buf = parse_hybi07_frames(frame)
        self.assertFalse(frames)
        self.assertEqual(buf, six.b("\x81"))

    def test_parse_hybi07_partial_truncated_length_int(self):
        frame = six.b("\x81\xfe")
        frames, buf = parse_hybi07_frames(frame)
        self.assertFalse(frames)
        self.assertEqual(buf, six.b("\x81\xfe"))

    def test_parse_hybi07_partial_truncated_length_double(self):
        frame = six.b("\x81\xff")
        frames, buf = parse_hybi07_frames(frame)
        self.assertFalse(frames)
        self.assertEqual(buf, six.b("\x81\xff"))

    def test_parse_hybi07_partial_no_data(self):
        frame = six.b("\x81\x05")
        frames, buf = parse_hybi07_frames(frame)
        self.assertFalse(frames)
        self.assertEqual(buf, six.b("\x81\x05"))

    def test_parse_hybi07_partial_truncated_data(self):
        frame = six.b("\x81\x05Hel")
        frames, buf = parse_hybi07_frames(frame)
        self.assertFalse(frames)
        self.assertEqual(buf, six.b("\x81\x05Hel"))

########NEW FILE########
__FILENAME__ = txws
# Copyright (c) 2011 Oregon State University Open Source Lab
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included
#    in all copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
#    NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#    OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
#    USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Blind reimplementation of WebSockets as a standalone wrapper for Twisted
protocols.
"""

from __future__ import division

__version__ = "0.7.1"

import six

import array

from base64 import b64encode, b64decode
from hashlib import md5, sha1
from string import digits
from struct import pack, unpack

from twisted.internet.interfaces import ISSLTransport
from twisted.protocols.policies import ProtocolWrapper, WrappingFactory
from twisted.python import log
from twisted.web.http import datetimeToString

class WSException(Exception):
    """
    Something stupid happened here.

    If this class escapes txWS, then something stupid happened in multiple
    places.
    """

# Flavors of WS supported here.
# HYBI00  - Hixie-76, HyBi-00. Challenge/response after headers, very minimal
#           framing. Tricky to start up, but very smooth sailing afterwards.
# HYBI07  - HyBi-07. Modern "standard" handshake. Bizarre masked frames, lots
#           of binary data packing.
# HYBI10  - HyBi-10. Just like HyBi-07. No, seriously. *Exactly* the same,
#           except for the protocol number.
# RFC6455 - RFC 6455. The official WebSocket protocol standard. The protocol
#           number is 13, but otherwise it is identical to HyBi-07.

HYBI00, HYBI07, HYBI10, RFC6455 = range(4)

# States of the state machine. Because there are no reliable byte counts for
# any of this, we don't use StatefulProtocol; instead, we use custom state
# enumerations. Yay!

REQUEST, NEGOTIATING, CHALLENGE, FRAMES = range(4)

# Control frame specifiers. Some versions of WS have control signals sent
# in-band. Adorable, right?

NORMAL, CLOSE, PING, PONG = range(4)

opcode_types = {
    0x0: NORMAL,
    0x1: NORMAL,
    0x2: NORMAL,
    0x8: CLOSE,
    0x9: PING,
    0xa: PONG,
}

encoders = {
    "base64": b64encode,
}

decoders = {
    "base64": b64decode,
}

# Fake HTTP stuff, and a couple convenience methods for examining fake HTTP
# headers.

def http_headers(s):
    """
    Create a dictionary of data from raw HTTP headers.
    """

    d = {}

    for line in s.split("\r\n"):
        try:
            key, value = [i.strip() for i in line.split(":", 1)]
            d[key] = value
        except ValueError:
            pass

    return d

def is_websocket(headers):
    """
    Determine whether a given set of headers is asking for WebSockets.
    """

    return ("upgrade" in headers.get("Connection", "").lower()
            and headers.get("Upgrade").lower() == "websocket")

def is_hybi00(headers):
    """
    Determine whether a given set of headers is HyBi-00-compliant.

    Hixie-76 and HyBi-00 use a pair of keys in the headers to handshake with
    servers.
    """

    return "Sec-WebSocket-Key1" in headers and "Sec-WebSocket-Key2" in headers

# Authentication for WS.

def complete_hybi00(headers, challenge):
    """
    Generate the response for a HyBi-00 challenge.
    """

    key1 = headers["Sec-WebSocket-Key1"]
    key2 = headers["Sec-WebSocket-Key2"]

    first = int("".join(i for i in key1 if i in digits)) // key1.count(" ")
    second = int("".join(i for i in key2 if i in digits)) // key2.count(" ")

    nonce = pack(">II8s", first, second, six.b(challenge))

    return md5(nonce).digest()

def make_accept(key):
    """
    Create an "accept" response for a given key.

    This dance is expected to somehow magically make WebSockets secure.
    """

    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    accept = "%s%s" % (key, guid)
    hashed_bytes = sha1(accept.encode('utf-8')).digest()

    return b64encode(hashed_bytes).strip().decode('utf-8')

# Frame helpers.
# Separated out to make unit testing a lot easier.
# Frames are bonghits in newer WS versions, so helpers are appreciated.

def make_hybi00_frame(buf):
    """
    Make a HyBi-00 frame from some data.

    This function does exactly zero checks to make sure that the data is safe
    and valid text without any 0xff bytes.
    """

    if isinstance(buf, six.text_type):
        buf = buf.encode('utf-8')

    return six.b("\x00") + buf + six.b("\xff")

def parse_hybi00_frames(buf):
    """
    Parse HyBi-00 frames, returning unwrapped frames and any unmatched data.

    This function does not care about garbage data on the wire between frames,
    and will actively ignore it.
    """

    start = buf.find(six.b("\x00"))
    tail = 0
    frames = []

    while start != -1:
        end = buf.find(six.b("\xff"), start + 1)
        if end == -1:
            # Incomplete frame, try again later.
            break
        else:
            # Found a frame, put it in the list.
            frame = buf[start + 1:end]
            frames.append((NORMAL, frame))
            tail = end + 1
        start = buf.find(six.b("\x00"), end + 1)

    # Adjust the buffer and return.
    buf = buf[tail:]
    return frames, buf

def mask(buf, key):
    """
    Mask or unmask a buffer of bytes with a masking key.

    The key must be exactly four bytes long.
    """

    # This is super-duper-secure, I promise~
    key = array.array("B", key)
    buf = array.array("B", buf)
    for i in range(len(buf)):
        buf[i] ^= key[i % 4]
    return buf.tostring()

def make_hybi07_frame(buf, opcode=0x1):
    """
    Make a HyBi-07 frame.

    This function always creates unmasked frames, and attempts to use the
    smallest possible lengths.
    """

    if len(buf) > 0xffff:
        length = "\x7f%s" % pack(">Q", len(buf))
    elif len(buf) > 0x7d:
        length = "\x7e%s" % pack(">H", len(buf))
    else:
        length = chr(len(buf))

    if isinstance(buf, six.text_type):
        buf = buf.encode('utf-8')

    # Always make a normal packet.
    header = chr(0x80 | opcode)
    return six.b(header + length) + buf

def make_hybi07_frame_dwim(buf):
    """
    Make a HyBi-07 frame with binary or text data according to the type of buf.
    """

    # TODO: eliminate magic numbers.
    if isinstance(buf, six.binary_type):
        return make_hybi07_frame(buf, opcode=0x2)
    elif isinstance(buf, six.text_type):
        return make_hybi07_frame(buf.encode("utf-8"), opcode=0x1)
    else:
        raise TypeError("In binary support mode, frame data must be either str or unicode")

def parse_hybi07_frames(buf):
    """
    Parse HyBi-07 frames in a highly compliant manner.
    """

    start = 0
    frames = []

    while True:
        # If there's not at least two bytes in the buffer, bail.
        if len(buf) - start < 2:
            break

        # Grab the header. This single byte holds some flags nobody cares
        # about, and an opcode which nobody cares about.
        header = buf[start]

        if six.PY2:
            header = ord(header)

        if header & 0x70:
            # At least one of the reserved flags is set. Pork chop sandwiches!
            raise WSException("Reserved flag in HyBi-07 frame (%d)" % header)
            frames.append(("", CLOSE))
            return frames, buf

        # Get the opcode, and translate it to a local enum which we actually
        # care about.
        opcode = header & 0xf
        try:
            opcode = opcode_types[opcode]
        except KeyError:
            raise WSException("Unknown opcode %d in HyBi-07 frame" % opcode)

        # Get the payload length and determine whether we need to look for an
        # extra length.
        length = buf[start + 1]

        if six.PY2:
            length = ord(length)

        masked = length & 0x80
        length &= 0x7f

        # The offset we're gonna be using to walk through the frame. We use
        # this because the offset is variable depending on the length and
        # mask.
        offset = 2

        # Extra length fields.
        if length == 0x7e:
            if len(buf) - start < 4:
                break

            length = buf[start + 2:start + 4]
            length = unpack(">H", length)[0]
            offset += 2
        elif length == 0x7f:
            if len(buf) - start < 10:
                break

            # Protocol bug: The top bit of this long long *must* be cleared;
            # that is, it is expected to be interpreted as signed. That's
            # fucking stupid, if you don't mind me saying so, and so we're
            # interpreting it as unsigned anyway. If you wanna send exabytes
            # of data down the wire, then go ahead!
            length = buf[start + 2:start + 10]
            length = unpack(">Q", length)[0]
            offset += 8

        if masked:
            if len(buf) - (start + offset) < 4:
                break

            key = buf[start + offset:start + offset + 4]
            offset += 4

        if len(buf) - (start + offset) < length:
            break

        data = buf[start + offset:start + offset + length]

        if masked:
            data = mask(data, key)

        if opcode == CLOSE:
            if len(data) >= 2:
                # Gotta unpack the opcode and return usable data here.
                data = unpack(">H", data[:2])[0], data[2:]
            else:
                # No reason given; use generic data.
                data = 1000, six.b("No reason given")

        frames.append((opcode, data))
        start += offset + length

    return frames, buf[start:]

class WebSocketProtocol(ProtocolWrapper):
    """
    Protocol which wraps another protocol to provide a WebSockets transport
    layer.
    """

    buf = six.b("")
    codec = None
    location = "/"
    host = "example.com"
    origin = "http://example.com"
    state = REQUEST
    flavor = None
    do_binary_frames = False

    def __init__(self, *args, **kwargs):
        ProtocolWrapper.__init__(self, *args, **kwargs)
        self.pending_frames = []

    def setBinaryMode(self, mode):
        """
        If True, send str as binary and unicode as text.

        Defaults to false for backwards compatibility.
        """
        self.do_binary_frames = bool(mode)

    def isSecure(self):
        """
        Borrowed technique for determining whether this connection is over
        SSL/TLS.
        """

        return ISSLTransport(self.transport, None) is not None

    def writeEncoded(self, data):
        if isinstance(data, six.text_type):
            data = data.encode('utf-8')
        self.transport.write(data)

    def writeEncodedSequence(self, sequence):
        self.transport.writeSequence([ele.encode('utf-8') for ele in sequence])

    def sendCommonPreamble(self):
        """
        Send the preamble common to all WebSockets connections.

        This might go away in the future if WebSockets continue to diverge.
        """

        self.writeEncodedSequence([
            "HTTP/1.1 101 FYI I am not a webserver\r\n",
            "Server: TwistedWebSocketWrapper/1.0\r\n",
            "Date: %s\r\n" % datetimeToString(),
            "Upgrade: WebSocket\r\n",
            "Connection: Upgrade\r\n",
        ])

    def sendHyBi00Preamble(self):
        """
        Send a HyBi-00 preamble.
        """

        protocol = "wss" if self.isSecure() else "ws"

        self.sendCommonPreamble()

        self.writeEncodedSequence([
            "Sec-WebSocket-Origin: %s\r\n" % self.origin,
            "Sec-WebSocket-Location: %s://%s%s\r\n" % (protocol, self.host,
                                                       self.location),
            "WebSocket-Protocol: %s\r\n" % self.codec,
            "Sec-WebSocket-Protocol: %s\r\n" % self.codec,
            "\r\n",
        ])

    def sendHyBi07Preamble(self):
        """
        Send a HyBi-07 preamble.
        """

        self.sendCommonPreamble()

        if self.codec:
            self.writeEncoded("Sec-WebSocket-Protocol: %s\r\n" % self.codec)

        challenge = self.headers["Sec-WebSocket-Key"]
        response = make_accept(challenge)

        self.writeEncoded("Sec-WebSocket-Accept: %s\r\n\r\n" % response)

    def parseFrames(self):
        """
        Find frames in incoming data and pass them to the underlying protocol.
        """

        if self.flavor == HYBI00:
            parser = parse_hybi00_frames
        elif self.flavor in (HYBI07, HYBI10, RFC6455):
            parser = parse_hybi07_frames
        else:
            raise WSException("Unknown flavor %r" % self.flavor)

        try:
            frames, self.buf = parser(self.buf)
        except WSException as wse:
            # Couldn't parse all the frames, something went wrong, let's bail.
            self.close(wse.args[0])
            return

        for frame in frames:
            opcode, data = frame
            if opcode == NORMAL:
                # Business as usual. Decode the frame, if we have a decoder.
                if self.codec:
                    data = decoders[self.codec](data)
                # Pass the frame to the underlying protocol.
                ProtocolWrapper.dataReceived(self, data)
            elif opcode == CLOSE:
                # The other side wants us to close. I wonder why?
                reason, text = data
                log.msg("Closing connection: %r (%d)" % (text, reason))

                # Close the connection.
                self.close()

    def sendFrames(self):
        """
        Send all pending frames.
        """

        if self.state != FRAMES:
            return

        if self.flavor == HYBI00:
            maker = make_hybi00_frame
        elif self.flavor in (HYBI07, HYBI10, RFC6455):
            if self.do_binary_frames:
                maker = make_hybi07_frame_dwim
            else:
                maker = make_hybi07_frame
        else:
            raise WSException("Unknown flavor %r" % self.flavor)

        for frame in self.pending_frames:
            # Encode the frame before sending it.
            if self.codec:
                frame = encoders[self.codec](frame)
            packet = maker(frame)
            self.writeEncoded(packet)
        self.pending_frames = []

    def validateHeaders(self):
        """
        Check received headers for sanity and correctness, and stash any data
        from them which will be required later.
        """

        # Obvious but necessary.
        if not is_websocket(self.headers):
            log.msg("Not handling non-WS request")
            return False

        # Stash host and origin for those browsers that care about it.
        if "Host" in self.headers:
            self.host = self.headers["Host"]
        if "Origin" in self.headers:
            self.origin = self.headers["Origin"]

        # Check whether a codec is needed. WS calls this a "protocol" for
        # reasons I cannot fathom. Newer versions of noVNC (0.4+) sets
        # multiple comma-separated codecs, handle this by chosing first one
        # we can encode/decode.
        protocols = None
        if "WebSocket-Protocol" in self.headers:
            protocols = self.headers["WebSocket-Protocol"]
        elif "Sec-WebSocket-Protocol" in self.headers:
            protocols = self.headers["Sec-WebSocket-Protocol"]

        if isinstance(protocols, six.string_types):
            protocols = [p.strip() for p in protocols.split(',')]

            for protocol in protocols:
                if protocol in encoders or protocol in decoders:
                    log.msg("Using WS protocol %s!" % protocol)
                    self.codec = protocol
                    break

                log.msg("Couldn't handle WS protocol %s!" % protocol)

            if not self.codec:
                return False

        # Start the next phase of the handshake for HyBi-00.
        if is_hybi00(self.headers):
            log.msg("Starting HyBi-00/Hixie-76 handshake")
            self.flavor = HYBI00
            self.state = CHALLENGE

        # Start the next phase of the handshake for HyBi-07+.
        if "Sec-WebSocket-Version" in self.headers:
            version = self.headers["Sec-WebSocket-Version"]
            if version == "7":
                log.msg("Starting HyBi-07 conversation")
                self.sendHyBi07Preamble()
                self.flavor = HYBI07
                self.state = FRAMES
            elif version == "8":
                log.msg("Starting HyBi-10 conversation")
                self.sendHyBi07Preamble()
                self.flavor = HYBI10
                self.state = FRAMES
            elif version == "13":
                log.msg("Starting RFC 6455 conversation")
                self.sendHyBi07Preamble()
                self.flavor = RFC6455
                self.state = FRAMES
            else:
                log.msg("Can't support protocol version %s!" % version)
                return False

        return True

    def dataReceived(self, data):
        self.buf += data

        oldstate = None

        while oldstate != self.state:
            oldstate = self.state

            # Handle initial requests. These look very much like HTTP
            # requests, but aren't. We need to capture the request path for
            # those browsers which want us to echo it back to them (Chrome,
            # mainly.)
            # These lines look like:
            # GET /some/path/to/a/websocket/resource HTTP/1.1
            if self.state == REQUEST:
                separator = six.b("\r\n")
                if separator in self.buf:
                    request, chaff, self.buf = self.buf.partition(separator)
                    request = request.decode('utf-8')

                    try:
                        verb, self.location, version = request.split(" ")
                    except ValueError:
                        self.loseConnection()
                    else:
                        self.state = NEGOTIATING

            elif self.state == NEGOTIATING:
                # Check to see if we've got a complete set of headers yet.
                separator = six.b("\r\n\r\n")
                if separator in self.buf:
                    head, chaff, self.buf = self.buf.partition(separator)
                    head = head.decode('utf-8')

                    self.headers = http_headers(head)
                    # Validate headers. This will cause a state change.
                    if not self.validateHeaders():
                        self.loseConnection()

            elif self.state == CHALLENGE:
                # Handle the challenge. This is completely exclusive to
                # HyBi-00/Hixie-76.
                if len(self.buf) >= 8:
                    challenge, self.buf = self.buf[:8], self.buf[8:]
                    challenge = challenge.decode('utf-8')

                    response = complete_hybi00(self.headers, challenge)
                    self.sendHyBi00Preamble()
                    self.writeEncoded(response)
                    log.msg("Completed HyBi-00/Hixie-76 handshake")
                    # We're all finished here; start sending frames.
                    self.state = FRAMES

            elif self.state == FRAMES:
                self.parseFrames()

        # Kick any pending frames. This is needed because frames might have
        # started piling up early; we can get write()s from our protocol above
        # when they makeConnection() immediately, before our browser client
        # actually sends any data. In those cases, we need to manually kick
        # pending frames.
        if self.pending_frames:
            self.sendFrames()

    def write(self, data):
        """
        Write to the transport.

        This method will only be called by the underlying protocol.
        """

        self.pending_frames.append(data)
        self.sendFrames()

    def writeSequence(self, data):
        """
        Write a sequence of data to the transport.

        This method will only be called by the underlying protocol.
        """

        self.pending_frames.extend(data)
        self.sendFrames()

    def close(self, reason=""):
        """
        Close the connection.

        This includes telling the other side we're closing the connection.

        If the other side didn't signal that the connection is being closed,
        then we might not see their last message, but since their last message
        should, according to the spec, be a simple acknowledgement, it
        shouldn't be a problem.
        """

        # Send a closing frame. It's only polite. (And might keep the browser
        # from hanging.)
        if self.flavor in (HYBI07, HYBI10, RFC6455):
            frame = make_hybi07_frame(reason, opcode=0x8)
            self.writeEncoded(frame)

        self.loseConnection()

class WebSocketFactory(WrappingFactory):
    """
    Factory which wraps another factory to provide WebSockets transports for
    all of its protocols.
    """

    protocol = WebSocketProtocol

########NEW FILE########
