__FILENAME__ = abstract
"""
The interfaces for implementing asynchronous IO.
"""
import abc

class Protocol(metaclass=abc.ABCMeta):
    def connected(self, transport):
        """
        Called when the connection is established.
        """
        self.transport = transport

    @abc.abstractmethod
    def data_received(self, data):
        """
        Called when some data is received.
        """

    def disconnected(self, reason):
        """
        Called when the connection is closed.
        """
        self.transport = None

class Transport(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def write(self, data):
        """
        Write some data into the transport.

        The data must be buffer of bytes.
        """

    @abc.abstractmethod
    def write_sequence(self, sequence):
        """
        Write a sequence of data.

        The sequence must be a sequence of buffers of bytes.
        """

    @abc.abstractmethod
    def close(self):
        """
        Close the connection after sending queued data.
        """

    @abc.abstractmethod
    def abort(self):
        """
        Immediately close the connection without sending queued data.
        """

    @abc.abstractmethod 
    def half_close(self):
        """
        Close the connection after sending queued data.

        Incoming data will still be accepted. 
        """

########NEW FILE########
__FILENAME__ = chunks
"""
An example composable protocol for receiving chunks delimited by some byte
sequence.
"""
import io

from protocols import abstract

MODES = CHUNKED, RAW = object(), object()

class ChunkProtocol(abstract.Protocol):
    """
    A protocol consisting of chunks delimited by some fixed delimiter. Common
    examples include line-delimited protocols such as HTTP, IRC...
    """
    delimiter = b"\0"
    mode = CHUNKED

    def __init__(self):
        self._buffer = b""


    def data_received(self, data):
        if self.mode is RAW:
            return self.raw_data_received(data)

        self._buffer += data
        *chunks, rest = self._buffer.split(self.delimiter)

        if chunks:
            self._buffer = rest
            for chunk in chunks:
                self.chunk_received(chunk)

    def raw_data_received(self, data):
        """
        Some data was received while the protocol was in ``RAW`` mode.

        This is exactly the same as ``data_received`` on an ordinary protocol.
        """

    def chunk_received(self, chunk):
        """
        A single chunk of data has been received.
        """

    def send_chunk(self, chunk):
        """
        Sends ``chunk`` through the transport, followed by a delimiter.
        """
        self.transport.write_sequence([chunk, self.delimiter])

########NEW FILE########
__FILENAME__ = test_chunks
"""
Tests for chunk protocols.
"""
import unittest

from protocols import chunks

class LoggingChunkProtocol(chunks.ChunkProtocol):
    def __init__(self):
        super().__init__()
        self.raw, self.chunks = [], []

    def raw_data_received(self, data):
        self.raw.append(data)

    def chunk_received(self, chunk):
        self.chunks.append(chunk)


class ChunkProtocolTests(unittest.TestCase):
    def setUp(self):
        self.protocol = LoggingChunkProtocol()

    def test_whole(self):
        """
        Tests receiving a whole chunk with a delimiter.
        """
        self.protocol.data_received(b"a\0")
        self.assertEqual(self.protocol.chunks, [b"a"])

    def test_split(self):
        """
        Tests receiving some split chunks.
        """
        for piece in [b"abc", b"\0de", b"f\0g", b"hi\0"]:
            self.protocol.data_received(piece)
        self.assertEqual(self.protocol.chunks, [b"abc", b"def", b"ghi"])

    def test_raw(self):
        """
        Test receiving some raw data.
        """
        self.protocol.mode = chunks.RAW

        self.protocol.data_received(b"a")
        self.assertEqual(self.protocol.raw, [b"a"])

        self.protocol.data_received(b"b")
        self.assertEqual(self.protocol.raw, [b"a", b"b"])

########NEW FILE########
